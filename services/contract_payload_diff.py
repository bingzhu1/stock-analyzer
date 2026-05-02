"""services/contract_payload_diff.py — read-only diff of the two latest contracts.

Reads the two most recently created ``prediction_log`` rows, parses each
``contract_payload_json``, validates both against the Step 1A Projection Output
Contract, and reports field-level diffs over a fixed set of stable contract
paths.

This is a verification tool, not a UI feature:
- never writes the DB
- never mutates rows
- never raises (status is reported via the returned dict)
- never logs

Public API:
    diff_latest_contract_payloads(db_path=None) -> dict

Status values:
    "ok"                          — both payloads valid; ``changed_fields`` and
                                    ``summary`` populated (may be empty if no
                                    fields changed between the two rows)
    "not_enough_records"          — fewer than 2 rows in prediction_log
    "missing_contract_payload"    — at least one row has NULL
                                    ``contract_payload_json``
    "invalid_json"                — at least one row's JSON parse failed
    "validation_failed"           — at least one row's payload failed
                                    contract validation
    "error"                       — unexpected internal failure (e.g. DB
                                    unreadable)
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import services.prediction_store as _ps
from services.projection_output_contract import validate_projection_output


# Fixed comparison set. Each tuple = ``(section, field)``; the field's value
# is read from each payload via dict.get() and compared with ``!=``.
DIFF_PATHS: tuple[tuple[str, str], ...] = (
    ("final_projection", "final_direction"),
    ("final_projection", "final_five_state"),
    ("final_projection", "probability_bucket"),
    ("final_projection", "final_one_sentence"),
    ("confidence_system", "confidence_level"),
    ("confidence_system", "total_confidence"),
    ("exclusion_system", "exclusion_level"),
    ("simulated_trade", "trade_action"),
    ("simulated_trade", "trade_direction"),
    ("simulated_trade", "suggested_position_size"),
)


def _resolve_db_path(db_path: str | Path | None) -> Path:
    if db_path is None:
        return Path(_ps.DB_PATH)
    return Path(db_path)


def _fetch_latest_two(db_path: Path) -> list[dict[str, Any]]:
    """Read-only fetch of the two most recently created prediction_log rows."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT id, symbol, prediction_for_date, created_at,
                   contract_payload_json
              FROM prediction_log
             ORDER BY created_at DESC, rowid DESC
             LIMIT 2
            """
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def _parse_payload(
    row: dict[str, Any],
) -> tuple[dict | None, str | None, Any]:
    """Return ``(payload, status, error_detail)``.

    ``status`` is ``None`` on success; otherwise one of
    ``missing_contract_payload`` / ``invalid_json`` / ``validation_failed``.
    """
    raw = row.get("contract_payload_json")
    if not raw:
        return None, "missing_contract_payload", None
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        return None, "invalid_json", str(exc)
    errors = validate_projection_output(payload)
    if errors:
        return None, "validation_failed", errors
    return payload, None, None


def _get_field(payload: Any, section: str, field: str) -> Any:
    if not isinstance(payload, dict):
        return None
    section_data = payload.get(section)
    if not isinstance(section_data, dict):
        return None
    return section_data.get(field)


def _build_diff(
    prev_payload: dict, latest_payload: dict
) -> tuple[list[str], dict[str, dict[str, Any]]]:
    changed_fields: list[str] = []
    summary: dict[str, dict[str, Any]] = {}
    for section, field in DIFF_PATHS:
        prev_val = _get_field(prev_payload, section, field)
        latest_val = _get_field(latest_payload, section, field)
        if prev_val != latest_val:
            changed_fields.append(f"{section}.{field}")
            summary[field] = {"from": prev_val, "to": latest_val}
    return changed_fields, summary


def diff_latest_contract_payloads(
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Diff the contract payloads of the two most recently created predictions.

    Read-only. Never mutates the DB. Always returns a dict; never raises.
    """
    db = _resolve_db_path(db_path)

    try:
        rows = _fetch_latest_two(db)
    except Exception as exc:
        return {"status": "error", "error": f"db_read_failed: {exc}"}

    if len(rows) < 2:
        return {
            "status": "not_enough_records",
            "available_records": len(rows),
        }

    latest_row, previous_row = rows[0], rows[1]
    base: dict[str, Any] = {
        "latest_prediction_id": latest_row["id"],
        "previous_prediction_id": previous_row["id"],
        "symbol": latest_row["symbol"],
    }

    # Parse both rows; if either side is broken, surface that status.
    # Latest is checked first so when both are broken, the latest's failure
    # mode wins (most recent reading is the most actionable).
    latest_payload, latest_status, latest_detail = _parse_payload(latest_row)
    previous_payload, previous_status, previous_detail = _parse_payload(previous_row)

    if latest_status is not None:
        return _wrap_failure(base, latest_status, latest_detail, side="latest")
    if previous_status is not None:
        return _wrap_failure(base, previous_status, previous_detail, side="previous")

    assert latest_payload is not None and previous_payload is not None
    changed_fields, summary = _build_diff(previous_payload, latest_payload)
    return {
        **base,
        "status": "ok",
        "changed_fields": changed_fields,
        "summary": summary,
    }


def _wrap_failure(
    base: dict[str, Any],
    status: str,
    detail: Any,
    *,
    side: str,
) -> dict[str, Any]:
    result: dict[str, Any] = {**base, "status": status, "failed_side": side}
    if status == "invalid_json":
        result["error"] = detail
    elif status == "validation_failed":
        result["validation_errors"] = detail
    return result
