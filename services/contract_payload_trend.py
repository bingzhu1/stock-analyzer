"""services/contract_payload_trend.py — read-only contract field trend tool.

Scans the most recently created N rows from ``prediction_log``, parses each
``contract_payload_json``, validates against the Step 1A contract, and
aggregates field-level statistics across the **valid** payloads. Rows whose
contract payload is missing / unparseable / fails validation are recorded in
``skipped_records`` so the caller can still see their ids and reason; they are
**not** counted in distributions or numeric stats.

This is a verification tool, not a UI feature:
- never writes the DB
- never mutates rows
- never raises (status is reported via the returned dict)
- never logs

Public API:
    summarize_recent_contract_payloads(db_path=None, limit=10) -> dict

Status values:
    "ok"                 — at least one valid payload was aggregated
    "no_records"         — table empty
    "no_valid_payloads"  — every scanned row was skipped
    "error"              — unexpected internal failure (e.g. DB unreadable)

Field set is **reused from** :data:`services.contract_payload_diff.DIFF_PATHS`
to keep validator / inspector / diff / trend in lockstep.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import services.prediction_store as _ps
from services.contract_payload_diff import DIFF_PATHS
from services.projection_output_contract import validate_projection_output


_DEFAULT_LIMIT = 10

# Subset of DIFF_PATHS whose values are numeric (min/max/mean) rather than
# categorical (frequency count).
_NUMERIC_PATHS: frozenset[str] = frozenset({"confidence_system.total_confidence"})


def _resolve_db_path(db_path: str | Path | None) -> Path:
    if db_path is None:
        return Path(_ps.DB_PATH)
    return Path(db_path)


def _resolve_limit(limit: Any) -> int:
    """Coerce caller-provided limit to a positive int, else fall back to default."""
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        return _DEFAULT_LIMIT
    return limit


def _fetch_recent(db_path: Path, limit: int) -> list[dict[str, Any]]:
    """Read-only fetch of the most recently created prediction_log rows."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT id, contract_payload_json
              FROM prediction_log
             ORDER BY created_at DESC, rowid DESC
             LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def _parse_row(row: dict[str, Any]) -> tuple[dict | None, str | None]:
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


def summarize_recent_contract_payloads(
    db_path: str | Path | None = None,
    limit: int = _DEFAULT_LIMIT,
) -> dict[str, Any]:
    """Aggregate contract field stats across the most recent ``limit`` rows.

    Read-only. Never mutates the DB. Always returns a dict; never raises.
    """
    db = _resolve_db_path(db_path)
    requested_limit = _resolve_limit(limit)

    try:
        rows = _fetch_recent(db, requested_limit)
    except Exception as exc:
        return {"status": "error", "error": f"db_read_failed: {exc}"}

    if not rows:
        return {
            "status": "no_records",
            "requested_limit": requested_limit,
            "records_scanned": 0,
        }

    valid_payloads: list[dict] = []
    skipped: list[dict[str, str]] = []
    for row in rows:
        payload, fail_reason = _parse_row(row)
        if fail_reason is not None:
            skipped.append({"prediction_id": row["id"], "reason": fail_reason})
        else:
            assert payload is not None
            valid_payloads.append(payload)

    base: dict[str, Any] = {
        "requested_limit": requested_limit,
        "records_scanned": len(rows),
        "valid_payloads": len(valid_payloads),
        "invalid_payloads": len(skipped),
        "skipped_records": skipped,
    }

    if not valid_payloads:
        return {**base, "status": "no_valid_payloads"}

    field_distributions: dict[str, dict[str, int]] = {}
    numeric_stats: dict[str, dict[str, float]] = {}
    latest_values: dict[str, Any] = {}

    # valid_payloads is in DESC order (most recent first); latest_values picks
    # the first one.
    for section, field in DIFF_PATHS:
        path = f"{section}.{field}"
        values = [_get_field(p, section, field) for p in valid_payloads]
        latest_values[path] = values[0]

        if path in _NUMERIC_PATHS:
            nums = [
                v for v in values
                if isinstance(v, (int, float)) and not isinstance(v, bool)
            ]
            if nums:
                numeric_stats[path] = {
                    "min": min(nums),
                    "max": max(nums),
                    "mean": sum(nums) / len(nums),
                }
        else:
            counts: dict[str, int] = {}
            for v in values:
                if v is None:
                    continue
                key = v if isinstance(v, str) else str(v)
                counts[key] = counts.get(key, 0) + 1
            if counts:
                field_distributions[path] = counts

    return {
        **base,
        "status": "ok",
        "field_distributions": field_distributions,
        "numeric_stats": numeric_stats,
        "latest_values": latest_values,
    }
