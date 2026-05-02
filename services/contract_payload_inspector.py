"""services/contract_payload_inspector.py — read-only contract inspection.

Reads the most recently created ``prediction_log`` row from the SQLite store,
parses its ``contract_payload_json`` column, validates the result against the
Step 1A Projection Output Contract, and emits a short per-section summary.

This is a verification tool, not a UI feature:
- never writes the DB
- never mutates rows
- never raises (status is reported via the returned dict)
- never logs

Public API:
    inspect_latest_contract_payload(db_path=None) -> dict

Status values:
    "ok"                          — payload present, validates, summary included
    "no_records"                  — table empty
    "missing_contract_payload"    — latest row has NULL contract_payload_json
    "invalid_json"                — JSON parse failed
    "validation_failed"           — validator returned errors
    "error"                       — unexpected internal failure (e.g. DB unreadable)
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import services.prediction_store as _ps
from services.projection_output_contract import (
    CONTRACT_SECTIONS,
    validate_projection_output,
)


def _resolve_db_path(db_path: str | Path | None) -> Path:
    """Return the path the inspector will read. Defaults to ``prediction_store.DB_PATH``."""
    if db_path is None:
        return Path(_ps.DB_PATH)
    return Path(db_path)


def _fetch_latest_prediction(db_path: Path) -> dict[str, Any] | None:
    """Read-only fetch of the most recently created prediction_log row."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            """
            SELECT id, symbol, analysis_date, prediction_for_date,
                   created_at, final_bias, final_confidence, status,
                   snapshot_id, contract_payload_json
              FROM prediction_log
             ORDER BY created_at DESC, rowid DESC
             LIMIT 1
            """
        )
        row = cur.fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


def _summary_for(section_key: str, section_data: Any) -> str:
    """Cheap, deterministic single-line summary per section. Never raises."""
    if not isinstance(section_data, dict):
        return "[invalid: section is not a dict]"

    if section_key == "current_structure":
        return (
            f"symbol={section_data.get('symbol')} · "
            f"analysis_date={section_data.get('analysis_date')} · "
            f"structure={section_data.get('structure_label')}"
        )
    if section_key == "avgo_primary_projection":
        evidence = section_data.get("key_evidence") or []
        return (
            f"direction={section_data.get('primary_direction')} · "
            f"five_state={section_data.get('five_state_projection')} · "
            f"raw_confidence={section_data.get('primary_confidence_raw')} · "
            f"evidence_count={len(evidence) if isinstance(evidence, list) else 0}"
        )
    if section_key == "peer_confirmation_adjustment":
        return (
            f"alignment={section_data.get('peer_alignment')} · "
            f"adjustment={section_data.get('peer_adjustment')} · "
            f"adjusted_direction={section_data.get('adjusted_direction')}"
        )
    if section_key == "exclusion_system":
        sources = section_data.get("exclusion_sources") or []
        return (
            f"level={section_data.get('exclusion_level')} · "
            f"sources={len(sources) if isinstance(sources, list) else 0} · "
            f"forced={section_data.get('forced_exclusion')}"
        )
    if section_key == "confidence_system":
        return (
            f"level={section_data.get('confidence_level')} · "
            f"total={section_data.get('total_confidence')}"
        )
    if section_key == "final_projection":
        return (
            f"direction={section_data.get('final_direction')} · "
            f"five_state={section_data.get('final_five_state')} · "
            f"bucket={section_data.get('probability_bucket')}"
        )
    if section_key == "simulated_trade":
        return (
            f"action={section_data.get('trade_action')} · "
            f"direction={section_data.get('trade_direction')} · "
            f"size={section_data.get('suggested_position_size')}"
        )
    if section_key == "review_payload":
        return (
            f"prediction_id={section_data.get('prediction_id') or '<empty>'} · "
            f"five_state={section_data.get('predicted_five_state')} · "
            f"confidence={section_data.get('predicted_confidence')}"
        )
    return "[unknown section]"


def _build_summary(payload: dict) -> dict[str, str]:
    return {
        section: _summary_for(section, payload.get(section, {}))
        for section in CONTRACT_SECTIONS
    }


def _present_sections(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return []
    return [section for section in CONTRACT_SECTIONS if section in payload]


def inspect_latest_contract_payload(
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Inspect the most recently created prediction's contract payload.

    Read-only. Never mutates the DB. Always returns a dict; never raises.
    """
    db = _resolve_db_path(db_path)

    try:
        row = _fetch_latest_prediction(db)
    except Exception as exc:
        return {
            "status": "error",
            "error": f"db_read_failed: {exc}",
        }

    if row is None:
        return {"status": "no_records"}

    base: dict[str, Any] = {
        "prediction_id": row["id"],
        "symbol": row["symbol"],
        "prediction_for_date": row["prediction_for_date"],
    }

    raw = row.get("contract_payload_json")
    if not raw:
        return {**base, "status": "missing_contract_payload"}

    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        return {**base, "status": "invalid_json", "error": str(exc)}

    sections_present = _present_sections(payload)
    errors = validate_projection_output(payload)

    if errors:
        return {
            **base,
            "status": "validation_failed",
            "validation_errors": errors,
            "sections_present": sections_present,
        }

    return {
        **base,
        "status": "ok",
        "validation_errors": [],
        "sections_present": sections_present,
        "summary": _build_summary(payload),
    }
