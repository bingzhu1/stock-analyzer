"""services/contract_calibration_inputs.py — read-only calibration-inputs diagnostic.

Reports the inputs that any future confidence-calibration step would need:
per-prediction extras-derived fields, the joined ``outcome_log`` direction
flag, a confidence-level × outcome accuracy summary, ``primary_score_raw``
distribution stats, and a data-gap report that flags missing samples.

This is a **diagnostic** tool — NOT a calibration engine. The four 0.0
score fields in ``confidence_system`` (``historical_score`` /
``structure_score`` / ``peer_score`` / ``exclusion_penalty``) and
``event_score = None`` are NOT changed by this module. ``primary_score_raw``
is reported raw (un-normalized); turning it into ``structure_score``
requires calibration data that this tool's ``data_gap_report`` is
specifically designed to surface as missing.

Public API:
    summarize_confidence_calibration_inputs(
        db_path=None, limit=50, symbol="AVGO"
    ) -> dict

Status values:
    "ok"                  — at least one valid contract payload was scanned
    "no_records"          — no rows under the symbol filter
    "no_valid_payloads"   — every scanned prediction was skipped (missing /
                            invalid_json / validation_failed)
    "error"               — internal failure (e.g. DB unreadable)

Read-only guarantees:
- never writes the DB; only ``SELECT`` (no ``init_db`` / ``INSERT`` / ``UPDATE``)
- never mutates inputs; never raises (status surfaced via the dict)
- never imports ``confidence_engine.py`` or any trading API
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import services.prediction_store as _ps
from services.projection_output_contract import validate_projection_output


_DEFAULT_LIMIT = 50

# Conservative gating threshold for "calibration-ready". Picked to give
# 30/30/30 coverage of the high/medium/low confidence buckets when split
# evenly. The number is a heuristic — not a guarantee of statistical
# adequacy. ``data_gap_report`` only labels readiness; nothing in the
# pipeline acts on it.
_MIN_RECOMMENDED_PAIRS = 90


def _resolve_db_path(db_path: str | Path | None) -> Path:
    if db_path is None:
        return Path(_ps.DB_PATH)
    return Path(db_path)


def _resolve_limit(limit: Any) -> int:
    """Coerce caller-provided limit to a positive int, else default."""
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        return _DEFAULT_LIMIT
    return limit


def _resolve_symbol(symbol: Any) -> str:
    """Mirror of contract_outcome_correlation._resolve_symbol."""
    if symbol is None:
        return "ALL"
    if not isinstance(symbol, str):
        return "AVGO"
    stripped = symbol.strip().upper()
    if not stripped:
        return "AVGO"
    return stripped


def _fetch_recent_with_outcome(
    db_path: Path, limit: int, symbol_filter: str
) -> list[dict[str, Any]]:
    """Read-only fetch joining each prediction's latest outcome flag.

    Mirrors ``contract_outcome_correlation._fetch_recent_with_outcome``: the
    outcome is selected via a correlated subquery so each prediction
    appears at most once even when multiple outcome rows exist for it.
    """
    if symbol_filter == "ALL":
        sql = """
            SELECT p.id                    AS id,
                   p.symbol                AS symbol,
                   p.prediction_for_date   AS prediction_for_date,
                   p.contract_payload_json AS contract_payload_json,
                   (SELECT o.direction_correct
                      FROM outcome_log o
                     WHERE o.prediction_id = p.id
                     ORDER BY o.captured_at DESC, o.rowid DESC
                     LIMIT 1) AS direction_correct
              FROM prediction_log p
             ORDER BY p.created_at DESC, p.rowid DESC
             LIMIT ?
        """
        params: tuple[Any, ...] = (limit,)
    else:
        sql = """
            SELECT p.id                    AS id,
                   p.symbol                AS symbol,
                   p.prediction_for_date   AS prediction_for_date,
                   p.contract_payload_json AS contract_payload_json,
                   (SELECT o.direction_correct
                      FROM outcome_log o
                     WHERE o.prediction_id = p.id
                     ORDER BY o.captured_at DESC, o.rowid DESC
                     LIMIT 1) AS direction_correct
              FROM prediction_log p
             WHERE p.symbol = ?
             ORDER BY p.created_at DESC, p.rowid DESC
             LIMIT ?
        """
        params = (symbol_filter, limit)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def _parse_payload(row: dict[str, Any]) -> tuple[dict | None, str | None]:
    """Return ``(payload, fail_reason)``; ``fail_reason`` is None on success."""
    raw = row.get("contract_payload_json")
    if not raw:
        return None, "missing_contract_payload"
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None, "invalid_json"
    if validate_projection_output(payload):
        return None, "validation_failed"
    return payload, None


def _get_confidence_extras(payload: Any) -> dict[str, Any] | None:
    """Return ``payload['confidence_system']['extras']`` if it is a dict,
    else ``None``. Old payloads (pre-Step 2C-3b) lack the ``extras`` block."""
    if not isinstance(payload, dict):
        return None
    section = payload.get("confidence_system")
    if not isinstance(section, dict):
        return None
    extras = section.get("extras")
    return extras if isinstance(extras, dict) else None


def _direction_correct_label(value: Any) -> str:
    """correct / wrong / pending — same semantics as correlation tool."""
    if value is None:
        return "pending"
    return "correct" if value else "wrong"


def _normalize_confidence_level(payload: dict, extras: dict | None) -> Any:
    """Pick the confidence-level bucket key for a record.

    Prefer ``extras.final_confidence`` (Step 2C-3b self-published) when it
    is a valid enum; otherwise fall back to the required
    ``confidence_system.confidence_level`` field (always real, normalized).
    Returns the bucket key as a string, or ``None`` when nothing usable.
    """
    valid = {"high", "medium", "low"}
    if extras:
        candidate = extras.get("final_confidence")
        if candidate in valid:
            return candidate
    section = payload.get("confidence_system") or {}
    if not isinstance(section, dict):
        return None
    candidate = section.get("confidence_level")
    return candidate if candidate in valid else None


def _is_real_number(value: Any) -> bool:
    """True for int / float, but NOT bool (bool is a subclass of int)."""
    if isinstance(value, bool):
        return False
    return isinstance(value, (int, float))


def _build_record(
    row: dict[str, Any], payload: dict, extras: dict | None
) -> dict[str, Any]:
    """Project one valid payload + its outcome into a flat record dict."""
    direction_correct_label = _direction_correct_label(row.get("direction_correct"))
    primary_score = extras.get("primary_score_raw") if extras else None
    primary_score_value = primary_score if _is_real_number(primary_score) else None

    record: dict[str, Any] = {
        "prediction_id": row.get("id"),
        "prediction_for_date": row.get("prediction_for_date"),
        "symbol": row.get("symbol"),
        "has_confidence_extras": extras is not None,
        "primary_score_raw": primary_score_value,
        "primary_confidence_raw": (extras or {}).get("primary_confidence_raw"),
        "peer_confirm_count": (extras or {}).get("peer_confirm_count"),
        "peer_oppose_count": (extras or {}).get("peer_oppose_count"),
        "peer_adjusted_confidence": (extras or {}).get("peer_adjusted_confidence"),
        "final_confidence": (extras or {}).get("final_confidence"),
        "probability_bucket": (extras or {}).get("probability_bucket"),
        "conflicting_factors_count": (extras or {}).get("conflicting_factors_count"),
        "path_risk_level": (extras or {}).get("path_risk_level"),
        "soft_signal": (extras or {}).get("soft_signal"),
        "direction_correct": direction_correct_label,
    }
    return record


def _empty_confidence_bucket() -> dict[str, Any]:
    return {"samples": 0, "correct": 0, "wrong": 0, "pending": 0, "accuracy": None}


def _compute_confidence_level_summary(
    paired: list[tuple[dict, dict | None, Any]],
) -> dict[str, dict[str, Any]]:
    """Bucket records by normalized confidence_level → correct/wrong/pending.

    ``paired`` is a list of ``(payload, extras, direction_correct_raw)``
    tuples. Records whose level can't be normalized are dropped from the
    summary (mirrors how correlation tool drops un-bucketable rows).
    """
    summary: dict[str, dict[str, Any]] = {}
    for payload, extras, direction_correct in paired:
        level = _normalize_confidence_level(payload, extras)
        if level is None:
            continue
        bucket = summary.setdefault(level, _empty_confidence_bucket())
        label = _direction_correct_label(direction_correct)
        bucket[label] += 1
        bucket["samples"] += 1

    for bucket in summary.values():
        denom = bucket["correct"] + bucket["wrong"]
        bucket["accuracy"] = (bucket["correct"] / denom) if denom > 0 else None
    return summary


def _compute_primary_score_summary(
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    """min / max / mean of ``primary_score_raw`` across records that have a
    real numeric value. Returns zero-count summary when no values."""
    values: list[float] = [
        float(r["primary_score_raw"])
        for r in records
        if _is_real_number(r.get("primary_score_raw"))
    ]
    if not values:
        return {"count": 0, "min": None, "max": None, "mean": None}
    return {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "mean": sum(values) / len(values),
    }


def _build_data_gap_report(
    paired_outcomes: int, records: list[dict[str, Any]]
) -> dict[str, Any]:
    """Static heuristic gap report. Conservative: any sparseness flips a
    flag. Used only as documentation; nothing in the pipeline acts on it."""
    missing: list[str] = []

    if paired_outcomes == 0:
        missing.append("no paired outcomes for valid contract payloads")
    elif paired_outcomes < _MIN_RECOMMENDED_PAIRS:
        missing.append(
            f"insufficient pairs: have {paired_outcomes}, "
            f"recommend ≥ {_MIN_RECOMMENDED_PAIRS}"
        )

    paired_records = [
        r for r in records if r["direction_correct"] in ("correct", "wrong")
    ]
    levels_seen = {r.get("final_confidence") for r in paired_records}
    levels_seen.discard(None)
    if {"high", "medium", "low"} - levels_seen:
        missing.append("insufficient high/medium/low coverage")

    confirm_counts_seen = {
        r.get("peer_confirm_count") for r in paired_records
        if isinstance(r.get("peer_confirm_count"), int)
    }
    if len(confirm_counts_seen) <= 1:
        missing.append("insufficient peer_confirm_count coverage")

    soft_signals_seen = {
        r.get("soft_signal") for r in paired_records
        if isinstance(r.get("soft_signal"), str)
    }
    if len(soft_signals_seen) <= 1:
        missing.append("insufficient soft_signal coverage")

    return {
        "calibration_ready": paired_outcomes >= _MIN_RECOMMENDED_PAIRS,
        "contract_outcome_pairs": paired_outcomes,
        "minimum_recommended_pairs": _MIN_RECOMMENDED_PAIRS,
        "missing_dimensions": missing,
    }


def summarize_confidence_calibration_inputs(
    db_path: str | Path | None = None,
    limit: int = _DEFAULT_LIMIT,
    symbol: str | None = "AVGO",
) -> dict[str, Any]:
    """Assemble a calibration-inputs diagnostic dict.

    Read-only. Never mutates the DB. Always returns a dict; never raises.
    """
    db = _resolve_db_path(db_path)
    requested_limit = _resolve_limit(limit)
    symbol_filter = _resolve_symbol(symbol)

    try:
        rows = _fetch_recent_with_outcome(db, requested_limit, symbol_filter)
    except Exception as exc:
        return {
            "status": "error",
            "error": f"db_read_failed: {exc}",
            "symbol_filter": symbol_filter,
        }

    if not rows:
        return {
            "status": "no_records",
            "requested_limit": requested_limit,
            "records_scanned": 0,
            "valid_payloads": 0,
            "invalid_payloads": 0,
            "records_with_confidence_extras": 0,
            "paired_outcomes": 0,
            "pending_outcomes": 0,
            "skipped_records": [],
            "records": [],
            "symbol_filter": symbol_filter,
        }

    skipped: list[dict[str, str]] = []
    records: list[dict[str, Any]] = []
    paired_for_summary: list[tuple[dict, dict | None, Any]] = []
    paired_outcomes = 0
    pending_outcomes = 0
    records_with_extras = 0

    for row in rows:
        payload, fail_reason = _parse_payload(row)
        if fail_reason is not None:
            skipped.append({"prediction_id": row["id"], "reason": fail_reason})
            continue
        assert payload is not None
        extras = _get_confidence_extras(payload)
        if extras is not None:
            records_with_extras += 1
        record = _build_record(row, payload, extras)
        records.append(record)
        paired_for_summary.append((payload, extras, row.get("direction_correct")))
        if record["direction_correct"] == "pending":
            pending_outcomes += 1
        else:
            paired_outcomes += 1

    base: dict[str, Any] = {
        "requested_limit": requested_limit,
        "records_scanned": len(rows),
        "valid_payloads": len(records),
        "invalid_payloads": len(skipped),
        "records_with_confidence_extras": records_with_extras,
        "paired_outcomes": paired_outcomes,
        "pending_outcomes": pending_outcomes,
        "skipped_records": skipped,
        "records": records,
        "symbol_filter": symbol_filter,
    }

    if not records:
        return {**base, "status": "no_valid_payloads"}

    return {
        **base,
        "status": "ok",
        "confidence_level_summary": _compute_confidence_level_summary(
            paired_for_summary
        ),
        "primary_score_raw_summary": _compute_primary_score_summary(records),
        "data_gap_report": _build_data_gap_report(paired_outcomes, records),
    }
