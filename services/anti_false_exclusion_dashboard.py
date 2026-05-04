"""services/anti_false_exclusion_dashboard.py — read-only aggregate diagnostics.

Step 2G-7C aggregate dashboard: rolls up the soft_metadata baseline
(R4 / residual historical metrics + survival counts) and the 6-item
hard gate pass/fail status into a single read-only dict, ready for
dashboard rendering or CLI inspection.

Design contract (Step 2G-7 / 2G-7A/7B / 2G-7C):
- read-only: only delegates to ``services.soft_metadata_simulator.build_soft_metadata_baseline``
  (SELECT-only); never writes DB / files / network
- never imports trading APIs / yfinance / requests / v1 stub trio
- ``hard_exclusion_allowed`` returned here is **derived** from the
  6-gate logic; spec invariant requires ``hard_exclusion_allowed`` to
  be ``False`` until ALL six gates pass — currently
  ``protection_layer_connected`` is hard-coded ``"fail"`` until a real
  protection-layer module is wired into the main pipeline (Step 2G-8+),
  so the derived value is always ``False`` in v1
- never raises; status surfaced via the returned dict

Public API:
    summarize_anti_false_exclusion_dashboard(
        db_path=None, *, symbol="AVGO", limit=450,
    ) -> dict
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from services.soft_metadata_simulator import build_soft_metadata_baseline


# Hard-gate thresholds (mirror Step 2G-3 / 2G-4.5 / 2G-7 / 2G-7A).
_TOTAL_PAIRED_GATE = 90
_CANDIDATE_PAIRED_GATE = 30
_FE_GATE = 0.10
_NB_GATE = 0.05

# Step 2G-7 §6.5: 4 candidate anti-false-exclusion modules
# (anti_false_exclusion_audit / big_up_contradiction_card /
# big_down_tail_warning / exclusion_reliability_review) are all
# offline. v1 keeps this gate hard-coded as "fail" until at least
# one module is wired into the main pipeline (Step 2G-8+).
_PROTECTION_LAYER_CONNECTED = False


# ── helpers ──────────────────────────────────────────────────────────────

def _is_real_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    return isinstance(value, (int, float))


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _derive_correct(metrics: dict) -> int | None:
    """``correct = round(accuracy × paired)`` for bullish slices."""
    paired = metrics.get("paired")
    acc = metrics.get("accuracy")
    if not _is_real_number(paired) or not _is_real_number(acc):
        return None
    return round(float(acc) * int(paired))


def _summarize_candidate(metrics: dict | None) -> dict[str, Any] | None:
    """Add ``correct_when_triggered`` / ``wrong_when_triggered`` to a
    raw baseline candidate dict. Returns ``None`` when the input is
    missing (so the dashboard surfaces it explicitly via warnings).
    """
    if not isinstance(metrics, dict):
        return None
    correct = _derive_correct(metrics)
    paired = metrics.get("paired")
    wrong = (
        int(paired) - int(correct)
        if _is_real_number(paired) and _is_real_number(correct)
        else None
    )
    return {
        "samples": metrics.get("samples"),
        "paired": paired,
        "correct_when_triggered": correct,
        "wrong_when_triggered": wrong,
        "accuracy": metrics.get("accuracy"),
        "false_exclusion_rate": metrics.get("false_exclusion_rate"),
        "net_benefit": metrics.get("net_benefit"),
        "bias_gap": metrics.get("bias_gap"),
        # holdout_status is at baseline-top-level (shared across all
        # candidates), but we surface it per-candidate for downstream
        # convenience; both R4 and residual share the same FAIL state.
        "holdout_status": metrics.get("holdout_status"),
    }


# ── hard-gate logic (Step 2G-3 / 2G-4.5 / 2G-7 §3) ──────────────────────

def _gate_status(passed: bool) -> str:
    return "pass" if passed else "fail"


def _build_hard_gate_status(
    *,
    paired_total: Any,
    r4_metrics: dict | None,
    holdout_status: Any,
) -> dict[str, str]:
    """Compute the 6-item hard gate pass/fail map.

    Each gate maps to ``"pass"`` / ``"fail"`` strings so the dashboard
    can render them uniformly. Missing data → ``"fail"`` (defensive:
    we don't allow hard exclusion when data is absent).
    """
    total_paired_pass = (
        _is_real_number(paired_total) and int(paired_total) >= _TOTAL_PAIRED_GATE
    )

    cand_paired = (
        r4_metrics.get("paired") if isinstance(r4_metrics, dict) else None
    )
    candidate_paired_pass = (
        _is_real_number(cand_paired) and int(cand_paired) >= _CANDIDATE_PAIRED_GATE
    )

    fer = r4_metrics.get("false_exclusion_rate") if isinstance(r4_metrics, dict) else None
    fer_pass = _is_real_number(fer) and float(fer) <= _FE_GATE

    nb = r4_metrics.get("net_benefit") if isinstance(r4_metrics, dict) else None
    nb_pass = _is_real_number(nb) and float(nb) >= _NB_GATE

    holdout_pass = (holdout_status == "PASS")

    return {
        "total_paired_ge_90": _gate_status(total_paired_pass),
        "candidate_paired_ge_30": _gate_status(candidate_paired_pass),
        "false_exclusion_rate_lte_0_10": _gate_status(fer_pass),
        "net_benefit_gte_0_05": _gate_status(nb_pass),
        "protection_layer_connected": _gate_status(_PROTECTION_LAYER_CONNECTED),
        "cross_window_holdout_pass": _gate_status(holdout_pass),
    }


def _pick_primary_blocker(gate_status: dict[str, str]) -> str | None:
    """Step 2G-7 §7 — pick the most-actionable blocker label.

    Priority:
      1. ``false_exclusion_rate_too_high`` if that gate fails
      2. first failing non-protection-layer gate
      3. ``missing_protection_layer`` (always fails in v1)
      4. None when every gate passes
    """
    if gate_status.get("false_exclusion_rate_lte_0_10") == "fail":
        return "false_exclusion_rate_too_high"
    for gate, mapping in (
        ("net_benefit_gte_0_05", "net_benefit_insufficient"),
        ("cross_window_holdout_pass", "soft_metadata_holdout_fail"),
        ("total_paired_ge_90", "insufficient_total_paired"),
        ("candidate_paired_ge_30", "insufficient_candidate_paired"),
    ):
        if gate_status.get(gate) == "fail":
            return mapping
    if gate_status.get("protection_layer_connected") == "fail":
        return "missing_protection_layer"
    return None


# ── public API ──────────────────────────────────────────────────────────

def summarize_anti_false_exclusion_dashboard(
    db_path: str | Path | None = None,
    *,
    symbol: str = "AVGO",
    limit: int = 450,
) -> dict[str, Any]:
    """Build the read-only aggregate dashboard dict.

    Delegates baseline loading to ``build_soft_metadata_baseline`` (SELECT-
    only). Always returns a dict; never raises.
    """
    warnings: list[str] = []
    try:
        baseline = build_soft_metadata_baseline(
            db_path=db_path, symbol=symbol, limit=limit,
        )
    except Exception as exc:  # noqa: BLE001 — never propagate
        return {
            "status": "error",
            "error": f"baseline_load_failed: {exc}",
            "symbol": symbol,
            "warnings": [f"baseline_load_failed: {exc}"],
            "hard_exclusion_allowed": False,
        }

    baseline = _safe_dict(baseline)
    metrics_window = _safe_dict(baseline.get("metrics_window"))
    paired_total = metrics_window.get("paired_total") or 0

    r4_raw = baseline.get("r4_overextension")
    residual_raw = baseline.get("bullish_high_pos20_residual")
    holdout_status = baseline.get("holdout_status")

    # carry baseline warnings forward + add our own when fields missing
    for w in _safe_list(baseline.get("warnings")):
        if isinstance(w, str):
            warnings.append(w)
    if r4_raw is None:
        warnings.append("r4_overextension_unavailable")
    if residual_raw is None:
        warnings.append("bullish_high_pos20_residual_unavailable")

    # Inject holdout_status into per-candidate dict so _summarize_candidate
    # can pass it through (it lives at baseline top-level by default).
    if isinstance(r4_raw, dict) and r4_raw.get("holdout_status") is None:
        r4_raw = {**r4_raw, "holdout_status": holdout_status}
    if isinstance(residual_raw, dict) and residual_raw.get("holdout_status") is None:
        residual_raw = {**residual_raw, "holdout_status": holdout_status}

    soft_metadata_summary: dict[str, Any] = {
        "r4_overextension": _summarize_candidate(r4_raw),
        "bullish_high_pos20_residual": _summarize_candidate(residual_raw),
    }

    r4_summary = soft_metadata_summary["r4_overextension"]
    survival_count = (
        r4_summary.get("correct_when_triggered")
        if isinstance(r4_summary, dict) else None
    )
    survival_rate = (
        r4_summary.get("accuracy")
        if isinstance(r4_summary, dict) else None
    )
    survival_cases = {
        "r4_survival_count": survival_count,
        "r4_survival_rate": survival_rate,
    }

    gate_status = _build_hard_gate_status(
        paired_total=paired_total,
        r4_metrics=r4_raw,
        holdout_status=holdout_status,
    )

    hard_exclusion_allowed = all(v == "pass" for v in gate_status.values())
    primary_blocker = _pick_primary_blocker(gate_status)

    # status: "ok" by default. We also surface "no_records" /
    # "baseline_partial" via warnings only; no need to flag at top
    # level unless baseline itself errored (handled above).
    status = "ok"
    if r4_summary is None:
        status = "no_records"

    return {
        "status": status,
        "symbol": symbol,
        "records_scanned": metrics_window.get("paired_total", 0),
        "paired_outcomes": paired_total,
        "calibration_ready": (
            _is_real_number(paired_total) and int(paired_total) >= _TOTAL_PAIRED_GATE
        ),
        "metrics_window": metrics_window,
        "metrics_computed_at": baseline.get("metrics_computed_at"),
        "soft_metadata_summary": soft_metadata_summary,
        "survival_cases": survival_cases,
        "hard_gate_status": gate_status,
        "hard_exclusion_allowed": hard_exclusion_allowed,
        "primary_blocker": primary_blocker,
        "warnings": warnings,
    }
