"""services/regime_validation_helper.py — pure 4-fold validation helper.

Step 3R-4.2 implementation per Step 3R-4 cross-window validation
protocol design (commit ``a58aad4``) + checkpoint (``abe3ba2``) +
Step 3R-4.1 4-fold validation helper design (``8e27254``) +
checkpoint (``295ccdd``). Computes ``regime_validation_report.v1``
from a list of caller-prepared replay records.

This module is **read-only diagnostics**:
- never reads DB / CSV / network; never imports ``yfinance`` /
  ``requests`` / trading APIs / ``services.prediction_store`` /
  ``predict`` / ``scanner`` / ``streamlit``
- never mutates input ``records``
- never raises (always returns a dict; missing data → record is
  skipped + warning string; manifest fail → ``overall_status="error"``)
- 2026 final-test cutoff: any record with ``analysis_date >=
  final_test_cutoff`` → ``final_test_refusal=True`` + report void
- gate thresholds are **fixed** by Step 3R-4 §6 / 3R-4 checkpoint §6;
  the helper APPLIES the protocol and does NOT expose threshold
  parameters

Public API:
    build_regime_validation_report(
        records,
        *,
        candidate_name,
        candidate_kind="label_assignment",
        windows=None,
        final_test_cutoff="2026-01-01",
        require_w4_manifest=True,
        w4_manifest_path=None,
    ) -> dict
"""
from __future__ import annotations

import json
from typing import Any


SCHEMA_VERSION = "regime_validation_report.v1"
DEFAULT_FINAL_TEST_CUTOFF = "2026-01-01"
W4_MANIFEST_SCHEMA_VERSION = "w4_replay_manifest.v1"

DEFAULT_WINDOWS: dict[str, dict[str, str]] = {
    "W1": {"start": "2023-01-03", "end": "2023-08-31"},
    "W2": {"start": "2023-09-01", "end": "2024-02-29"},
    "W3": {"start": "2024-03-01", "end": "2024-08-02"},
    "W4": {"start": "2024-08-03", "end": "2025-12-31"},
}

W4_REQUIRED_START = "2024-08-03"
W4_REQUIRED_END = "2025-12-31"
W4_REQUIRED_CUTOFF = "2026-01-01"
W4_MIN_PAIRED = 20

# Step 3R-4 §6 / 3R-4 checkpoint §6 — fixed protocol thresholds.
GATE_MIN_WINDOW_SAMPLE = 20
GATE_FER_MAX = 0.10
GATE_NB_MIN = 0.05
GATE_VARIANCE_MAX = 0.10
GATE_SURVIVAL_MIN = 0.80
GATE_ACC_DELTA_MIN = 0.02
COLLAPSE_FER_THRESHOLD = 0.20
COLLAPSE_NB_THRESHOLD = 0.0

_REQUIRED_RECORD_FIELDS: tuple[str, ...] = (
    "analysis_date",
    "candidate_triggered",
    "prediction_correct",
    "baseline_correct",
    "exclusion_would_block",
    "survival_case",
)

_GATE_KEYS: tuple[str, ...] = (
    "minimum_window_sample_size",
    "false_exclusion_rate",
    "net_benefit",
    "accuracy_delta_vs_baseline",
    "cross_window_variance",
    "survival_case_preservation",
    "no_single_window_collapse",
)


# ── helpers ──────────────────────────────────────────────────────────────


def _coerce_bool(value: Any) -> bool | None:
    if value is True or value is False:
        return value
    return None


def _coerce_str(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    return None


def _resolve_window(date_str: str, windows: dict[str, dict[str, str]]) -> str | None:
    for name, span in windows.items():
        start = span.get("start")
        end = span.get("end")
        if not isinstance(start, str) or not isinstance(end, str):
            continue
        if start <= date_str <= end:
            return name
    return None


def _empty_per_window_metrics() -> dict[str, Any]:
    return {
        "minimum_window_sample_size": 0,
        "false_exclusion_rate": None,
        "net_benefit": None,
        "accuracy_delta_vs_baseline": None,
        "survival_case_preservation": None,
        "triggered_paired": 0,
        "blocked_paired": 0,
    }


def _per_window_compute(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute the 6 metrics for one held-out window from its records."""
    metrics = _empty_per_window_metrics()
    if not records:
        return metrics

    paired_total = 0
    baseline_correct_total = 0
    candidate_adjusted_correct = 0

    blocked: list[dict[str, Any]] = []
    triggered: list[dict[str, Any]] = []
    survival_total = 0
    survival_preserved = 0

    for r in records:
        prediction_correct = _coerce_bool(r.get("prediction_correct"))
        baseline_correct = _coerce_bool(r.get("baseline_correct"))
        if prediction_correct is None or baseline_correct is None:
            continue
        paired_total += 1
        baseline_correct_total += 1 if baseline_correct else 0

        triggered_flag = _coerce_bool(r.get("candidate_triggered")) is True
        block_flag = (
            _coerce_bool(r.get("exclusion_would_block")) is True
            and triggered_flag
        )
        survival_flag = _coerce_bool(r.get("survival_case")) is True

        if triggered_flag:
            triggered.append(r)
        if block_flag:
            blocked.append(r)
            # exclusion treats this case as "removed" — outcome no longer
            # contributes to candidate-adjusted accuracy
        else:
            candidate_adjusted_correct += 1 if prediction_correct else 0

        if survival_flag:
            survival_total += 1
            if not block_flag:
                survival_preserved += 1

    metrics["triggered_paired"] = len(triggered)
    metrics["blocked_paired"] = len(blocked)
    metrics["minimum_window_sample_size"] = len(blocked)

    if blocked:
        false_exclusions = sum(
            1 for r in blocked if _coerce_bool(r.get("prediction_correct")) is True
        )
        metrics["false_exclusion_rate"] = false_exclusions / len(blocked)

    if paired_total > 0:
        baseline_acc = baseline_correct_total / paired_total
        non_blocked_paired = paired_total - len(blocked)
        if non_blocked_paired > 0:
            candidate_acc = candidate_adjusted_correct / non_blocked_paired
            metrics["net_benefit"] = candidate_acc - baseline_acc
            metrics["accuracy_delta_vs_baseline"] = candidate_acc - baseline_acc
        else:
            metrics["net_benefit"] = None
            metrics["accuracy_delta_vs_baseline"] = None

    if survival_total > 0:
        metrics["survival_case_preservation"] = survival_preserved / survival_total
    else:
        # No survival cases observed — preservation is vacuously 1.0.
        metrics["survival_case_preservation"] = 1.0

    return metrics


def _pooled_compute(records: list[dict[str, Any]]) -> dict[str, Any]:
    return _per_window_compute(records)


def _cross_window_variance(per_window: dict[str, dict[str, Any]]) -> dict[str, Any]:
    fers = [
        m.get("false_exclusion_rate")
        for m in per_window.values()
        if m.get("false_exclusion_rate") is not None
    ]
    nbs = [
        m.get("net_benefit")
        for m in per_window.values()
        if m.get("net_benefit") is not None
    ]
    out: dict[str, Any] = {
        "false_exclusion_rate": None,
        "net_benefit": None,
    }
    if len(fers) >= 2:
        out["false_exclusion_rate"] = max(fers) - min(fers)
    if len(nbs) >= 2:
        out["net_benefit"] = max(nbs) - min(nbs)
    return out


def _select_worst_window(
    per_window: dict[str, dict[str, Any]],
) -> tuple[str | None, str | None]:
    """Return (worst_window_name, reason). Priority per design §9."""
    if not per_window:
        return None, None

    over_fer = [
        (name, m["false_exclusion_rate"])
        for name, m in per_window.items()
        if m.get("false_exclusion_rate") is not None
        and m["false_exclusion_rate"] > GATE_FER_MAX
    ]
    if over_fer:
        worst_name, worst_val = max(over_fer, key=lambda x: x[1])
        return (
            worst_name,
            f"false_exclusion_rate={worst_val:.4f}_above_{GATE_FER_MAX}",
        )

    under_nb = [
        (name, m["net_benefit"])
        for name, m in per_window.items()
        if m.get("net_benefit") is not None and m["net_benefit"] < GATE_NB_MIN
    ]
    if under_nb:
        worst_name, worst_val = min(under_nb, key=lambda x: x[1])
        return (
            worst_name,
            f"net_benefit={worst_val:.4f}_below_{GATE_NB_MIN}",
        )

    under_sample = [
        (name, m["minimum_window_sample_size"])
        for name, m in per_window.items()
        if m.get("minimum_window_sample_size", 0) < GATE_MIN_WINDOW_SAMPLE
    ]
    if under_sample:
        worst_name, worst_val = min(under_sample, key=lambda x: x[1])
        return (
            worst_name,
            f"minimum_window_sample_size={worst_val}_below_{GATE_MIN_WINDOW_SAMPLE}",
        )

    under_surv = [
        (name, m["survival_case_preservation"])
        for name, m in per_window.items()
        if m.get("survival_case_preservation") is not None
        and m["survival_case_preservation"] < GATE_SURVIVAL_MIN
    ]
    if under_surv:
        worst_name, worst_val = min(under_surv, key=lambda x: x[1])
        return (
            worst_name,
            f"survival_case_preservation={worst_val:.4f}_below_{GATE_SURVIVAL_MIN}",
        )

    fers = [
        (name, m["false_exclusion_rate"])
        for name, m in per_window.items()
        if m.get("false_exclusion_rate") is not None
    ]
    if fers:
        worst_name, worst_val = max(fers, key=lambda x: x[1])
        return worst_name, f"highest_false_exclusion_rate={worst_val:.4f}"

    # Fall back to lexical name.
    return sorted(per_window.keys())[0], "no_metrics_emitted"


def _gate_status(
    per_window: dict[str, dict[str, Any]],
    variance: dict[str, Any],
) -> dict[str, str]:
    status = {key: "pass" for key in _GATE_KEYS}

    for m in per_window.values():
        if m.get("minimum_window_sample_size", 0) < GATE_MIN_WINDOW_SAMPLE:
            status["minimum_window_sample_size"] = "fail"
        fer = m.get("false_exclusion_rate")
        if fer is None or fer > GATE_FER_MAX:
            status["false_exclusion_rate"] = "fail"
        nb = m.get("net_benefit")
        if nb is None or nb < GATE_NB_MIN:
            status["net_benefit"] = "fail"
        delta = m.get("accuracy_delta_vs_baseline")
        if delta is None or delta < GATE_ACC_DELTA_MIN:
            status["accuracy_delta_vs_baseline"] = "fail"
        surv = m.get("survival_case_preservation")
        if surv is None or surv < GATE_SURVIVAL_MIN:
            status["survival_case_preservation"] = "fail"
        if (fer is not None and fer >= COLLAPSE_FER_THRESHOLD) or (
            nb is not None and nb <= COLLAPSE_NB_THRESHOLD
        ):
            status["no_single_window_collapse"] = "fail"

    var_fer = variance.get("false_exclusion_rate")
    if var_fer is None or var_fer > GATE_VARIANCE_MAX:
        status["cross_window_variance"] = "fail"

    return status


def _build_leave_one_window_out(
    per_window: dict[str, dict[str, Any]],
    gate_status: dict[str, str],
) -> dict[str, str]:
    """Per-fold pass/fail mirrors per-window thresholds.

    The "train" side of each fold is informational (this helper does not
    fit anything); pass/fail uses the held-out window's per_window_metrics.
    """
    folds: dict[str, str] = {}
    names = sorted(per_window.keys())
    for held_out in names:
        train = [n for n in names if n != held_out]
        key = f"F_train_{'_'.join(train)}_validate_{held_out}"
        m = per_window[held_out]
        sample = m.get("minimum_window_sample_size", 0)
        fer = m.get("false_exclusion_rate")
        nb = m.get("net_benefit")
        delta = m.get("accuracy_delta_vs_baseline")
        surv = m.get("survival_case_preservation")
        per_window_pass = (
            sample >= GATE_MIN_WINDOW_SAMPLE
            and fer is not None
            and fer <= GATE_FER_MAX
            and nb is not None
            and nb >= GATE_NB_MIN
            and delta is not None
            and delta >= GATE_ACC_DELTA_MIN
            and surv is not None
            and surv >= GATE_SURVIVAL_MIN
            and not (
                (fer is not None and fer >= COLLAPSE_FER_THRESHOLD)
                or (nb is not None and nb <= COLLAPSE_NB_THRESHOLD)
            )
        )
        folds[key] = "pass" if per_window_pass else "fail"
    return folds


def _validate_w4_manifest(
    path: str | None,
) -> tuple[bool, list[str], dict[str, Any] | None]:
    """Read + validate a w4_replay_manifest.v1 JSON file.

    Returns (ok, warnings, manifest_dict). On missing path / unreadable
    file / schema mismatch / final_test_touched=True, ok=False.
    """
    warnings: list[str] = []
    if not path:
        warnings.append("w4_manifest_path_missing")
        return False, warnings, None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            manifest = json.load(fh)
    except FileNotFoundError:
        warnings.append("w4_manifest_file_not_found")
        return False, warnings, None
    except (OSError, json.JSONDecodeError) as exc:
        warnings.append(f"w4_manifest_read_error:{type(exc).__name__}")
        return False, warnings, None

    if not isinstance(manifest, dict):
        warnings.append("w4_manifest_not_object")
        return False, warnings, None

    ok = True
    if manifest.get("schema_version") != W4_MANIFEST_SCHEMA_VERSION:
        warnings.append("w4_manifest_schema_mismatch")
        ok = False
    if manifest.get("final_test_touched") is not False:
        warnings.append("w4_final_test_touched_true_report_void")
        ok = False
    if manifest.get("status") != "ok":
        warnings.append("w4_manifest_status_not_ok")
        ok = False
    paired = manifest.get("paired_outcomes")
    if not isinstance(paired, int) or paired < W4_MIN_PAIRED:
        warnings.append("w4_paired_below_minimum")
        ok = False
    window = manifest.get("replay_window") or {}
    if window.get("start") != W4_REQUIRED_START:
        warnings.append("w4_replay_window_start_mismatch")
        ok = False
    if window.get("end") != W4_REQUIRED_END:
        warnings.append("w4_replay_window_end_mismatch")
        ok = False
    if manifest.get("final_test_cutoff") != W4_REQUIRED_CUTOFF:
        warnings.append("w4_final_test_cutoff_mismatch")
        ok = False

    return ok, warnings, manifest


def _empty_report(
    *,
    candidate_name: str,
    candidate_kind: str,
    windows: dict[str, dict[str, str]],
    final_test_cutoff: str,
    fold_count: int,
    overall_status: str,
    final_test_refusal: bool,
    warnings: list[str],
    fail_reason: str | None = None,
) -> dict[str, Any]:
    windows_out = {
        name: {
            "start": span.get("start"),
            "end": span.get("end"),
            "paired": 0,
        }
        for name, span in windows.items()
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "candidate_name": candidate_name,
        "candidate_kind": candidate_kind,
        "fold_count": fold_count,
        "windows": windows_out,
        "per_window_metrics": {},
        "pooled_metrics": {},
        "worst_window": None,
        "worst_window_metrics": {},
        "worst_window_reason": None,
        "cross_window_variance": {
            "false_exclusion_rate": None,
            "net_benefit": None,
        },
        "leave_one_window_out": {},
        "gate_status": {key: "fail" for key in _GATE_KEYS},
        "overall_status": overall_status,
        "fail_reason": fail_reason,
        "final_test_refusal": bool(final_test_refusal),
        "data_cutoff_used": final_test_cutoff,
        "warnings": list(warnings),
    }


# ── public API ───────────────────────────────────────────────────────────


def build_regime_validation_report(
    records: list[dict[str, Any]],
    *,
    candidate_name: str,
    candidate_kind: str = "label_assignment",
    windows: dict[str, dict[str, str]] | None = None,
    final_test_cutoff: str = DEFAULT_FINAL_TEST_CUTOFF,
    require_w4_manifest: bool = True,
    w4_manifest_path: str | None = None,
) -> dict[str, Any]:
    """Build a `regime_validation_report.v1` dict for one candidate.

    Pure read-only — see module docstring for full constraints.
    """
    warnings: list[str] = []
    active_windows = dict(windows) if windows else dict(DEFAULT_WINDOWS)
    fold_count = len(active_windows)

    # ── 1. W4 manifest gate ────────────────────────────────────────────
    if require_w4_manifest:
        ok, manifest_warnings, _manifest = _validate_w4_manifest(w4_manifest_path)
        warnings.extend(manifest_warnings)
        if not ok:
            return _empty_report(
                candidate_name=candidate_name,
                candidate_kind=candidate_kind,
                windows=active_windows,
                final_test_cutoff=final_test_cutoff,
                fold_count=fold_count,
                overall_status="error",
                final_test_refusal=any(
                    "final_test" in w for w in manifest_warnings
                ),
                warnings=warnings,
                fail_reason=f"w4_manifest_gate_fail:{','.join(manifest_warnings)}",
            )
    else:
        warnings.append("w4_manifest_not_required")

    # ── 2. record-level filter / 2026 refusal / window assignment ──────
    bucketed: dict[str, list[dict[str, Any]]] = {n: [] for n in active_windows}
    pooled_records: list[dict[str, Any]] = []
    final_test_refusal = False

    for r in records:
        analysis_date = _coerce_str(r.get("analysis_date"))
        if not analysis_date:
            warnings.append("record_skipped:missing_analysis_date")
            continue
        if analysis_date >= final_test_cutoff:
            warnings.append(
                f"record_with_2026_date_seen:{analysis_date}"
            )
            final_test_refusal = True
            continue
        # Required field presence check (full type validation deferred to
        # _per_window_compute, which silently skips coerce-failures).
        missing = [k for k in _REQUIRED_RECORD_FIELDS if k not in r]
        if missing:
            warnings.append(
                f"record_skipped:missing_field:{','.join(missing)}"
            )
            continue
        win = _resolve_window(analysis_date, active_windows)
        if win is None:
            warnings.append(f"record_skipped:out_of_window:{analysis_date}")
            continue
        bucketed[win].append(r)
        pooled_records.append(r)

    if final_test_refusal:
        return _empty_report(
            candidate_name=candidate_name,
            candidate_kind=candidate_kind,
            windows=active_windows,
            final_test_cutoff=final_test_cutoff,
            fold_count=fold_count,
            overall_status="error",
            final_test_refusal=True,
            warnings=warnings,
            fail_reason="record_with_date_at_or_after_final_test_cutoff",
        )

    # ── 3. per-window + pooled metrics ────────────────────────────────
    per_window: dict[str, dict[str, Any]] = {}
    for name in active_windows:
        per_window[name] = _per_window_compute(bucketed[name])

    pooled_metrics = _pooled_compute(pooled_records)
    pooled_metrics_out = {
        "false_exclusion_rate": pooled_metrics["false_exclusion_rate"],
        "net_benefit": pooled_metrics["net_benefit"],
        "accuracy_delta_vs_baseline": pooled_metrics["accuracy_delta_vs_baseline"],
    }

    variance = _cross_window_variance(per_window)

    # ── 4. worst-window + gate status + folds ─────────────────────────
    worst_window, worst_reason = _select_worst_window(per_window)
    worst_metrics = (
        per_window[worst_window] if worst_window in per_window else {}
    )
    gate_status = _gate_status(per_window, variance)
    folds = _build_leave_one_window_out(per_window, gate_status)

    overall_status = (
        "pass" if all(v == "pass" for v in gate_status.values()) else "fail"
    )

    fail_reason = None
    if overall_status == "fail":
        failing = [k for k, v in gate_status.items() if v == "fail"]
        if worst_window:
            fail_reason = f"{','.join(failing)} at {worst_window}: {worst_reason}"
        else:
            fail_reason = ",".join(failing)

    # ── 5. assemble report ────────────────────────────────────────────
    windows_out = {
        name: {
            "start": span.get("start"),
            "end": span.get("end"),
            "paired": sum(
                1
                for r in bucketed[name]
                if _coerce_bool(r.get("prediction_correct")) is not None
                and _coerce_bool(r.get("baseline_correct")) is not None
            ),
        }
        for name, span in active_windows.items()
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "candidate_name": candidate_name,
        "candidate_kind": candidate_kind,
        "fold_count": fold_count,
        "windows": windows_out,
        "per_window_metrics": per_window,
        "pooled_metrics": pooled_metrics_out,
        "worst_window": worst_window,
        "worst_window_metrics": dict(worst_metrics),
        "worst_window_reason": worst_reason,
        "cross_window_variance": variance,
        "leave_one_window_out": folds,
        "gate_status": gate_status,
        "overall_status": overall_status,
        "fail_reason": fail_reason,
        "final_test_refusal": False,
        "data_cutoff_used": final_test_cutoff,
        "warnings": warnings,
    }
