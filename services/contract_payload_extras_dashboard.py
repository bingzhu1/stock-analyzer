"""services/contract_payload_extras_dashboard.py — read-only extras dashboard.

Aggregates the ``extras`` sub-dicts of contract sections 04
(``exclusion_system``), 05 (``confidence_system``), and 07
(``simulated_trade``) across the most-recent N predictions and returns a
single snapshot + per-field distribution dict. Step 2C-2 / 2C-3b / 2D-2
introduced these extras blocks; the four pre-existing read-only tools
(inspector / trend / diff / outcome correlation) deliberately do not
expand into ``extras`` (their `DIFF_PATHS` / `GROUP_PATHS` are 2-tuple
``(section, field)`` paths, three-level access is out of scope for them).

This is a verification / observability tool, not a UI feature:
- never writes the DB (read-only ``SELECT``; never calls ``init_db``)
- never mutates rows
- never raises (status is reported via the returned dict)
- never logs

Public API:
    summarize_contract_extras_dashboard(db_path=None, limit=20, symbol="AVGO") -> dict

Status values:
    "ok"                  — at least one valid contract; distributions populated
    "no_records"          — no rows under the symbol filter
    "no_valid_payloads"   — every scanned prediction was skipped (no contract /
                            invalid JSON / failed validation)
    "error"               — unexpected internal failure (e.g. DB unreadable)

Symbol filter (returned as ``symbol_filter``):
    "AVGO" (default), "ALL" / None → no filter, "" → "AVGO" fallback,
    other → ``str.strip().upper()`` (mirrors ``contract_outcome_correlation``).

Distribution buckets:
    Each tracked field's bucket map keys are stringified values. Special keys:
      "MISSING" — payload was contract-valid but the section had no ``extras``
                  (e.g. predictions written before Step 2C-2).
      "NULL"    — the extras key existed but its value was ``None``.
    Bool values are stringified to ``"True"`` / ``"False"``.
    list / dict values are NOT expanded (would explode the bucket count);
    Tracked fields are restricted to enum / int / bool / short str.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import services.prediction_store as _ps
from services.projection_output_contract import validate_projection_output


_DEFAULT_LIMIT = 20

# Fields tracked in extras_distributions. Each tuple is
# ``(section, extras_field)``; the value is read from
# ``payload[section]["extras"][extras_field]``. Continuous floats
# (``primary_score_raw``, ``total_confidence``) and list/dict fields
# (``conflicting_factors``, ``peer_path_risk_reasons``) are intentionally
# excluded — they would explode the bucket map. Use ``latest_snapshot`` to
# inspect raw values instead.
DISTRIBUTION_PATHS: tuple[tuple[str, str], ...] = (
    # 04 exclusion_system.extras
    ("exclusion_system", "soft_signal"),
    ("exclusion_system", "path_risk_level"),
    ("exclusion_system", "peer_path_risk_direction"),
    ("exclusion_system", "conflicting_factors_count"),
    # 05 confidence_system.extras
    ("confidence_system", "primary_confidence_raw"),
    ("confidence_system", "peer_adjusted_confidence"),
    ("confidence_system", "final_confidence"),
    ("confidence_system", "probability_bucket"),
    ("confidence_system", "path_risk_level"),
    ("confidence_system", "soft_signal"),
    # 07 simulated_trade.extras
    ("simulated_trade", "trade_engine_enabled"),
    ("simulated_trade", "has_key_price_levels"),
    ("simulated_trade", "final_direction"),
    ("simulated_trade", "soft_signal"),
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


def _fetch_recent(
    db_path: Path, limit: int, symbol_filter: str
) -> list[dict[str, Any]]:
    """Read-only fetch of the most-recent N predictions.

    Returns rows as dicts with keys: ``id``, ``prediction_for_date``,
    ``contract_payload_json``. ORDER BY ``created_at DESC, rowid DESC`` so
    the first row is the most recent.
    """
    if symbol_filter == "ALL":
        sql = """
            SELECT p.id                    AS id,
                   p.prediction_for_date   AS prediction_for_date,
                   p.contract_payload_json AS contract_payload_json
              FROM prediction_log p
             ORDER BY p.created_at DESC, p.rowid DESC
             LIMIT ?
        """
        params: tuple[Any, ...] = (limit,)
    else:
        sql = """
            SELECT p.id                    AS id,
                   p.prediction_for_date   AS prediction_for_date,
                   p.contract_payload_json AS contract_payload_json
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


def _get_extras_block(payload: Any, section: str) -> dict[str, Any] | None:
    """Return ``payload[section]['extras']`` if it is a dict, else ``None``.

    A missing extras block is **not** an error — predictions written before
    Step 2C-2 / 2C-3b / 2D-2 will lack ``extras``.
    """
    if not isinstance(payload, dict):
        return None
    section_data = payload.get(section)
    if not isinstance(section_data, dict):
        return None
    extras = section_data.get("extras")
    return extras if isinstance(extras, dict) else None


def _bucket_key(value: Any) -> str:
    """Coerce an extras value to a deterministic bucket key.

    Rules:
      - ``None``        → "NULL"
      - ``True``/``False`` → "True"/"False"
      - everything else → ``str(value)``

    Note: bool must be checked **before** int because ``isinstance(True, int)``
    is True; the existing existing tools have the same care (cf. ``_resolve_limit``
    rejecting bool first).
    """
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "True" if value else "False"
    return str(value)


def _empty_distributions() -> dict[str, dict[str, int]]:
    return {
        f"{section}.extras.{field}": {}
        for section, field in DISTRIBUTION_PATHS
    }


def _accumulate_distribution(
    distributions: dict[str, dict[str, int]],
    payload: dict,
) -> None:
    """Update ``distributions`` in-place with one valid payload."""
    for section, field in DISTRIBUTION_PATHS:
        path = f"{section}.extras.{field}"
        bucket = distributions[path]
        extras = _get_extras_block(payload, section)
        if extras is None:
            key = "MISSING"
        elif field not in extras:
            key = "MISSING"
        else:
            key = _bucket_key(extras[field])
        bucket[key] = bucket.get(key, 0) + 1


def _build_latest_snapshot(
    row: dict[str, Any], payload: dict
) -> dict[str, Any]:
    """Pull a small decision-summary subset out of the latest valid payload."""
    final_section = payload.get("final_projection") or {}
    confidence_section = payload.get("confidence_system") or {}
    trade_section = payload.get("simulated_trade") or {}

    return {
        "prediction_id": row.get("id"),
        "prediction_for_date": row.get("prediction_for_date"),
        "final_direction": final_section.get("final_direction"),
        "probability_bucket": final_section.get("probability_bucket"),
        "confidence_level": confidence_section.get("confidence_level"),
        "trade_action": trade_section.get("trade_action"),
        "exclusion_system_extras": _get_extras_block(payload, "exclusion_system"),
        "confidence_system_extras": _get_extras_block(payload, "confidence_system"),
        "simulated_trade_extras": _get_extras_block(payload, "simulated_trade"),
    }


def summarize_contract_extras_dashboard(
    db_path: str | Path | None = None,
    limit: int = _DEFAULT_LIMIT,
    symbol: str | None = "AVGO",
) -> dict[str, Any]:
    """Aggregate extras across the most-recent N predictions.

    Read-only. Never mutates the DB. Always returns a dict; never raises.
    """
    db = _resolve_db_path(db_path)
    requested_limit = _resolve_limit(limit)
    symbol_filter = _resolve_symbol(symbol)

    try:
        rows = _fetch_recent(db, requested_limit, symbol_filter)
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
            "predictions_scanned": 0,
            "records_scanned": 0,
            "valid_payloads": 0,
            "invalid_payloads": 0,
            "skipped_records": [],
            "symbol_filter": symbol_filter,
        }

    skipped: list[dict[str, str]] = []
    valid_rows: list[tuple[dict[str, Any], dict]] = []
    for row in rows:
        payload, fail_reason = _parse_payload(row)
        if fail_reason is not None:
            skipped.append({"prediction_id": row["id"], "reason": fail_reason})
        else:
            assert payload is not None
            valid_rows.append((row, payload))

    base: dict[str, Any] = {
        "requested_limit": requested_limit,
        "records_scanned": len(rows),
        "valid_payloads": len(valid_rows),
        "invalid_payloads": len(skipped),
        "skipped_records": skipped,
        "symbol_filter": symbol_filter,
    }

    if not valid_rows:
        return {**base, "status": "no_valid_payloads"}

    distributions = _empty_distributions()
    for _, payload in valid_rows:
        _accumulate_distribution(distributions, payload)

    latest_row, latest_payload = valid_rows[0]  # rows already DESC-ordered
    latest_snapshot = _build_latest_snapshot(latest_row, latest_payload)

    return {
        **base,
        "status": "ok",
        "latest_snapshot": latest_snapshot,
        "extras_distributions": distributions,
    }
