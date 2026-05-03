"""services/contract_outcome_correlation.py — read-only outcome × contract.

Joins the most recently created N rows of ``prediction_log`` with their latest
matching ``outcome_log`` row (via correlated subquery), parses each
``contract_payload_json``, validates against the Step 1A contract, and reports
hit-rate statistics grouped by 3 stable contract fields.

This is a verification tool, not a UI feature:
- never writes the DB
- never mutates rows
- never raises (status is reported via the returned dict)
- never logs

Public API:
    correlate_outcomes_with_contract(db_path=None, limit=30) -> dict

Status values:
    "ok"                   — at least one valid contract; group_accuracy populated
    "no_records"           — prediction_log empty
    "no_valid_contracts"   — every scanned prediction was skipped (no contract /
                             invalid JSON / failed validation)
    "error"                — unexpected internal failure (e.g. DB unreadable)

Outcome classification:
    direction_correct == 1     → "correct"
    direction_correct == 0     → "wrong"
    direction_correct is None  → "pending"   (no outcome row yet, or NULL)

Accuracy = correct / (correct + wrong); pending excluded from denominator.
``accuracy = None`` when correct + wrong == 0.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import services.prediction_store as _ps
from services.projection_output_contract import validate_projection_output


_DEFAULT_LIMIT = 30

# Fixed grouping set (kept tight per the Step 1J spec). Each tuple is
# ``(section, field)``; the field's value within ``contract_payload_json`` is
# used as the group key.
GROUP_PATHS: tuple[tuple[str, str], ...] = (
    ("final_projection", "final_direction"),
    ("confidence_system", "confidence_level"),
    ("final_projection", "final_five_state"),
)


def _resolve_db_path(db_path: str | Path | None) -> Path:
    if db_path is None:
        return Path(_ps.DB_PATH)
    return Path(db_path)


def _resolve_limit(limit: Any) -> int:
    """Coerce caller-provided limit to a positive int, else default."""
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        return _DEFAULT_LIMIT
    return limit


def _fetch_recent_with_outcome(db_path: Path, limit: int) -> list[dict[str, Any]]:
    """Read-only fetch of the most recent N predictions + their latest outcome.

    The outcome is selected via a correlated subquery so each prediction
    appears at most once even when multiple outcome rows exist for it.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT p.id           AS id,
                   p.contract_payload_json AS contract_payload_json,
                   (SELECT o.direction_correct
                      FROM outcome_log o
                     WHERE o.prediction_id = p.id
                     ORDER BY o.captured_at DESC, o.rowid DESC
                     LIMIT 1) AS direction_correct
              FROM prediction_log p
             ORDER BY p.created_at DESC, p.rowid DESC
             LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def _parse_payload(row: dict[str, Any]) -> tuple[dict | None, str | None]:
    """Return ``(payload, fail_reason)``; fail_reason is None on success."""
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


def _get_field(payload: Any, section: str, field: str) -> Any:
    if not isinstance(payload, dict):
        return None
    section_data = payload.get(section)
    if not isinstance(section_data, dict):
        return None
    return section_data.get(field)


def _classify(direction_correct: Any) -> str:
    """Bucket a raw direction_correct value into correct / wrong / pending."""
    if direction_correct is None:
        return "pending"
    # SQLite stores 0/1; treat 1 (or any truthy non-None) as correct.
    return "correct" if direction_correct else "wrong"


def _group_by_field(
    rows: list[tuple[dict, Any]], section: str, field: str
) -> dict[str, dict[str, Any]]:
    """Group ``(payload, direction_correct)`` rows by ``payload[section][field]``.

    Rows whose group key is ``None`` (field missing or section malformed) are
    excluded from grouping but were already counted in valid_contracts.
    """
    buckets: dict[str, dict[str, int]] = {}
    for payload, direction_correct in rows:
        value = _get_field(payload, section, field)
        if value is None:
            continue
        key = value if isinstance(value, str) else str(value)
        bucket = buckets.setdefault(
            key, {"correct": 0, "wrong": 0, "pending": 0}
        )
        bucket[_classify(direction_correct)] += 1

    result: dict[str, dict[str, Any]] = {}
    for key, bucket in buckets.items():
        correct = bucket["correct"]
        wrong = bucket["wrong"]
        pending = bucket["pending"]
        denom = correct + wrong
        result[key] = {
            "samples": correct + wrong + pending,
            "correct": correct,
            "wrong": wrong,
            "pending": pending,
            "accuracy": (correct / denom) if denom > 0 else None,
        }
    return result


def correlate_outcomes_with_contract(
    db_path: str | Path | None = None,
    limit: int = _DEFAULT_LIMIT,
) -> dict[str, Any]:
    """Correlate contract field values with their captured outcomes.

    Read-only. Never mutates the DB. Always returns a dict; never raises.
    """
    db = _resolve_db_path(db_path)
    requested_limit = _resolve_limit(limit)

    try:
        rows = _fetch_recent_with_outcome(db, requested_limit)
    except Exception as exc:
        return {"status": "error", "error": f"db_read_failed: {exc}"}

    if not rows:
        return {
            "status": "no_records",
            "requested_limit": requested_limit,
            "predictions_scanned": 0,
        }

    valid: list[tuple[dict, Any]] = []
    skipped: list[dict[str, str]] = []
    for row in rows:
        payload, fail_reason = _parse_payload(row)
        if fail_reason is not None:
            skipped.append({"prediction_id": row["id"], "reason": fail_reason})
        else:
            assert payload is not None
            valid.append((payload, row.get("direction_correct")))

    paired = sum(1 for _, dc in valid if dc is not None)
    pending = sum(1 for _, dc in valid if dc is None)

    base: dict[str, Any] = {
        "requested_limit": requested_limit,
        "predictions_scanned": len(rows),
        "valid_contracts": len(valid),
        "invalid_contracts": len(skipped),
        "paired_outcomes": paired,
        "pending_outcomes": pending,
        "skipped_records": skipped,
    }

    if not valid:
        return {**base, "status": "no_valid_contracts"}

    group_accuracy = {
        f"{section}.{field}": _group_by_field(valid, section, field)
        for section, field in GROUP_PATHS
    }

    return {**base, "status": "ok", "group_accuracy": group_accuracy}
