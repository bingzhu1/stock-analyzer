"""services/replay_validation_record_adapter.py — pure read-only replay → records adapter.

Step 3R-4.3A implementation per Step 3R-4.3 design (commit ``9da5e57``)
+ checkpoint (``2ce8230``). Converts replay rows (W4 jsonl shape +
W1/W2/W3 same-schema) plus a caller-injected candidate dict into a
``replay_validation_records.v1`` payload. The downstream evaluator
(in ``services.regime_validation_helper``) is intentionally NOT
referenced from this module: caller wires the two stages.

This module is **read-only diagnostics**:
- never reads DB / files / network; never imports ``yfinance`` /
  ``requests`` / trading APIs / ``services.prediction_store`` /
  ``predict`` / ``scanner`` / ``streamlit`` / the validation evaluator
- never mutates input ``replay_rows`` or ``w4_manifest``
- never raises (always returns a dict; missing data → record skipped
  + warning string)
  ⤷ exception: invalid ``candidate_threshold`` raises ``ValueError``
    at API entry (caller-bug shielding, not data error)
- 2026 final-test cutoff: any row with ``analysis_date >=
  final_test_cutoff`` → record skipped + ``final_test_refusal=True`` +
  warning
- W4 manifest gate (when ``require_w4_manifest=True``): manifest must
  satisfy 8 checks; failure → ``records=[]`` + warnings explaining
  failure + final_test_refusal mirrors manifest's final_test_touched
- adapter only assembles the record list; it does NOT compute metrics,
  gates, or pass/fail outcomes (those belong to the downstream evaluator)

Public API:
    build_replay_validation_records(
        replay_rows,
        *,
        candidate_threshold,         # REQUIRED, no default
        candidate_name="continuous_smoothing_v1",
        final_test_cutoff="2026-01-01",
        require_w4_manifest=True,
        w4_manifest=None,
    ) -> dict
"""
from __future__ import annotations

from typing import Any


SCHEMA_VERSION = "replay_validation_records.v1"
DEFAULT_CANDIDATE_NAME = "continuous_smoothing_v1"
DEFAULT_FINAL_TEST_CUTOFF = "2026-01-01"

DEFAULT_WINDOWS: dict[str, dict[str, str]] = {
    "W1": {"start": "2023-01-03", "end": "2023-08-31"},
    "W2": {"start": "2023-09-01", "end": "2024-02-29"},
    "W3": {"start": "2024-03-01", "end": "2024-08-02"},
    "W4": {"start": "2024-08-03", "end": "2025-12-31"},
}

W4_MANIFEST_SCHEMA_VERSION = "w4_replay_manifest.v1"
W4_REQUIRED_START = "2024-08-03"
W4_REQUIRED_END = "2025-12-31"
W4_REQUIRED_CUTOFF = "2026-01-01"
W4_MIN_PAIRED = 20


# ── helpers ──────────────────────────────────────────────────────────────


def _validate_threshold(value: Any) -> float:
    if value is None:
        raise ValueError("candidate_threshold is required (no default)")
    if isinstance(value, bool):
        raise ValueError(
            f"candidate_threshold must be a float in [0, 1]; got bool {value}"
        )
    if isinstance(value, str):
        raise ValueError(
            f"candidate_threshold must be a float in [0, 1]; got str {value!r}"
        )
    if not isinstance(value, (int, float)):
        raise ValueError(
            f"candidate_threshold must be a float in [0, 1]; got {type(value).__name__}"
        )
    v = float(value)
    if v != v:  # NaN
        raise ValueError("candidate_threshold must be finite; got NaN")
    if v < 0.0 or v > 1.0:
        raise ValueError(
            f"candidate_threshold must be in [0, 1]; got {v}"
        )
    return v


def _validate_w4_manifest_dict(
    manifest: Any,
) -> tuple[bool, list[str], bool]:
    """Validate a W4 manifest dict (provided by caller; not loaded from disk).

    Returns (ok, warnings, final_test_touched_flag).
    """
    warnings: list[str] = []
    if manifest is None:
        warnings.append("w4_manifest_missing")
        return False, warnings, False
    if not isinstance(manifest, dict):
        warnings.append("w4_manifest_not_object")
        return False, warnings, False

    ok = True
    final_test_touched = bool(manifest.get("final_test_touched"))

    if manifest.get("schema_version") != W4_MANIFEST_SCHEMA_VERSION:
        warnings.append("w4_manifest_schema_mismatch")
        ok = False
    if final_test_touched is not False:
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
    if not isinstance(window, dict):
        window = {}
    if window.get("start") != W4_REQUIRED_START:
        warnings.append("w4_replay_window_start_mismatch")
        ok = False
    if window.get("end") != W4_REQUIRED_END:
        warnings.append("w4_replay_window_end_mismatch")
        ok = False
    if manifest.get("final_test_cutoff") != W4_REQUIRED_CUTOFF:
        warnings.append("w4_final_test_cutoff_mismatch")
        ok = False

    return ok, warnings, final_test_touched


def _resolve_window(
    date_str: str, windows: dict[str, dict[str, str]]
) -> str | None:
    for name, span in windows.items():
        start = span.get("start")
        end = span.get("end")
        if not isinstance(start, str) or not isinstance(end, str):
            continue
        if start <= date_str <= end:
            return name
    return None


def _is_valid_iso_date(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 10:
        return False
    if value[4] != "-" or value[7] != "-":
        return False
    y, m, d = value[:4], value[5:7], value[8:10]
    return y.isdigit() and m.isdigit() and d.isdigit()


def _actual_direction(row: dict[str, Any]) -> str:
    state = row.get("actual_state")
    if isinstance(state, str):
        if state in ("大涨", "小涨"):
            return "up"
        if state in ("大跌", "小跌"):
            return "down"
        if state == "震荡":
            return "flat"
    change = row.get("actual_close_change")
    if isinstance(change, (int, float)) and not isinstance(change, bool):
        if change > 0:
            return "up"
        if change < 0:
            return "down"
        if change == 0:
            return "flat"
    return "unknown"


def _candidate_state(
    row: dict[str, Any], threshold: float
) -> tuple[bool, list[str], dict[str, Any] | None]:
    """Return (candidate_triggered, warnings, candidate_dict_for_record)."""
    warnings: list[str] = []
    candidate = row.get("candidate")
    if candidate is None:
        warnings.append("missing_candidate")
        return False, warnings, None
    if not isinstance(candidate, dict):
        warnings.append("missing_candidate")
        return False, warnings, None
    if candidate.get("final_test_refusal") is True:
        warnings.append("candidate_final_test_refusal")
        return False, warnings, dict(candidate)
    risk_score = candidate.get("risk_score")
    if risk_score is None:
        warnings.append("candidate_unavailable")
        return False, warnings, dict(candidate)
    if not isinstance(risk_score, (int, float)) or isinstance(risk_score, bool):
        warnings.append("candidate_unavailable")
        return False, warnings, dict(candidate)
    triggered = float(risk_score) >= threshold
    return triggered, warnings, dict(candidate)


def _empty_payload(
    *,
    candidate_threshold: float,
    candidate_name: str,
    final_test_refusal: bool,
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "candidate_name": candidate_name,
        "candidate_threshold": candidate_threshold,
        "records": [],
        "windows": {
            name: {"start": span["start"], "end": span["end"]}
            for name, span in DEFAULT_WINDOWS.items()
        },
        "source_files": [],
        "final_test_refusal": bool(final_test_refusal),
        "warnings": list(warnings),
    }


# ── public API ───────────────────────────────────────────────────────────


def build_replay_validation_records(
    replay_rows: list[dict[str, Any]],
    *,
    candidate_threshold: float,
    candidate_name: str = DEFAULT_CANDIDATE_NAME,
    final_test_cutoff: str = DEFAULT_FINAL_TEST_CUTOFF,
    require_w4_manifest: bool = True,
    w4_manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Adapt replay rows + caller-injected candidate dicts into
    ``replay_validation_records.v1`` for the validation helper.

    Pure read-only — see module docstring for full constraints.
    """
    threshold = _validate_threshold(candidate_threshold)
    warnings: list[str] = []

    # ── 1. W4 manifest gate ────────────────────────────────────────────
    if require_w4_manifest:
        ok, manifest_warnings, final_test_touched = _validate_w4_manifest_dict(
            w4_manifest
        )
        warnings.extend(manifest_warnings)
        if not ok:
            return _empty_payload(
                candidate_threshold=threshold,
                candidate_name=candidate_name,
                final_test_refusal=final_test_touched,
                warnings=warnings,
            )
    else:
        warnings.append("w4_manifest_not_required")

    # ── 2. iterate rows ────────────────────────────────────────────────
    records: list[dict[str, Any]] = []
    final_test_refusal = False

    for row in replay_rows:
        if not isinstance(row, dict):
            warnings.append("record_skipped:row_not_dict")
            continue

        analysis_date = row.get("as_of_date")
        if not _is_valid_iso_date(analysis_date):
            warnings.append("record_skipped:invalid_analysis_date")
            continue

        if analysis_date >= final_test_cutoff:
            final_test_refusal = True
            warnings.append(
                f"final_test_range_refusal:{analysis_date}"
            )
            continue

        prediction_for_date = row.get("prediction_for_date")
        if not _is_valid_iso_date(prediction_for_date):
            warnings.append(
                f"record_skipped:invalid_prediction_for_date:{analysis_date}"
            )
            continue

        # Defense-in-depth: also enforce cutoff on prediction_for_date.
        if prediction_for_date >= final_test_cutoff:
            final_test_refusal = True
            warnings.append(
                f"final_test_range_refusal:prediction_for_date={prediction_for_date}"
            )
            continue

        window = _resolve_window(analysis_date, DEFAULT_WINDOWS)
        if window is None:
            warnings.append(
                f"record_skipped:outside_validation_windows:{analysis_date}"
            )
            continue

        direction_correct = row.get("direction_correct")
        if direction_correct is None or not isinstance(direction_correct, bool):
            warnings.append(
                f"record_skipped:missing_or_invalid_direction_correct:{analysis_date}"
            )
            continue

        triggered, candidate_warnings, candidate_dict = _candidate_state(
            row, threshold
        )

        record_warnings: list[str] = list(candidate_warnings)

        labels = row.get("labels")
        if isinstance(labels, dict):
            labels_for_record: dict[str, Any] | None = dict(labels)
        else:
            labels_for_record = None

        record = {
            "analysis_date": analysis_date,
            "prediction_for_date": prediction_for_date,
            "candidate_triggered": bool(triggered),
            "prediction_correct": bool(direction_correct),
            "baseline_correct": bool(direction_correct),
            "exclusion_would_block": bool(triggered),
            "survival_case": bool(triggered) and bool(direction_correct),
            "actual_direction": _actual_direction(row),
            "labels": labels_for_record,
            "candidate": candidate_dict,
            "window": window,
            "warnings": record_warnings,
        }
        records.append(record)

    return {
        "schema_version": SCHEMA_VERSION,
        "candidate_name": candidate_name,
        "candidate_threshold": threshold,
        "records": records,
        "windows": {
            name: {"start": span["start"], "end": span["end"]}
            for name, span in DEFAULT_WINDOWS.items()
        },
        "source_files": [],
        "final_test_refusal": bool(final_test_refusal),
        "warnings": warnings,
    }
