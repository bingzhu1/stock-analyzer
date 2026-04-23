# -*- coding: utf-8 -*-
"""
services/review_store.py

SQLite-backed store for deterministic review results produced by
services/review_orchestrator.run_review_for_prediction().

Table
-----
  deterministic_review_log — one row per persisted review result

Uses the same avgo_agent.db file as prediction_store.py but manages its own
table and init separately. All functions call init_db() defensively.

Public API
----------
save_review_record(review_payload: dict) -> str
load_review_records(symbol: str | None = None, limit: int = 50) -> list[dict]
get_latest_review_for_target_date(symbol: str, prediction_for_date: str) -> dict | None
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

DB_PATH = Path("avgo_agent.db")

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS deterministic_review_log (
    id                   TEXT PRIMARY KEY,
    prediction_id        TEXT NOT NULL,
    symbol               TEXT NOT NULL,
    prediction_for_date  TEXT NOT NULL,
    created_at           TEXT NOT NULL,
    overall_score        REAL,
    correct_count        INTEGER,
    total_count          INTEGER,
    pred_open            TEXT,
    pred_path            TEXT,
    pred_close           TEXT,
    actual_open_type     TEXT,
    actual_path          TEXT,
    actual_close_type    TEXT,
    open_correct         INTEGER,
    path_correct         INTEGER,
    close_correct        INTEGER,
    error_category       TEXT,
    primary_error        TEXT,
    error_types_json     TEXT,
    reason_guesses_json  TEXT,
    review_summary       TEXT,
    comparison_json      TEXT,
    error_info_json      TEXT,
    review_schema_version INTEGER DEFAULT 1,
    meta_json            TEXT,
    primary_projection_json TEXT,
    peer_adjustment_json TEXT,
    final_projection_json TEXT,
    historical_probability_json TEXT,
    actual_outcome_json  TEXT,
    review_result_json   TEXT,
    rule_extraction_json TEXT,
    review_payload_json  TEXT,
    source               TEXT DEFAULT 'historical'
);

CREATE INDEX IF NOT EXISTS idx_det_review_symbol_date
    ON deterministic_review_log (symbol, prediction_for_date);
CREATE INDEX IF NOT EXISTS idx_det_review_prediction_id
    ON deterministic_review_log (prediction_id);
"""

_V2_JSON_COLUMNS = {
    "meta_json": "TEXT",
    "primary_projection_json": "TEXT",
    "peer_adjustment_json": "TEXT",
    "final_projection_json": "TEXT",
    "historical_probability_json": "TEXT",
    "actual_outcome_json": "TEXT",
    "review_result_json": "TEXT",
    "rule_extraction_json": "TEXT",
    "review_payload_json": "TEXT",
}

_MIGRATION_COLUMNS = {
    "review_schema_version": "INTEGER DEFAULT 1",
    "source": "TEXT DEFAULT 'historical'",
    **_V2_JSON_COLUMNS,
}


@contextmanager
def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create deterministic_review_log table and indexes if they don't exist."""
    with _get_conn() as conn:
        conn.executescript(_CREATE_SQL)
        _ensure_v2_columns(conn)


def _ensure_v2_columns(conn: sqlite3.Connection) -> None:
    existing = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(deterministic_review_log)").fetchall()
    }
    for column, ddl_type in _MIGRATION_COLUMNS.items():
        if column not in existing:
            conn.execute(f"ALTER TABLE deterministic_review_log ADD COLUMN {column} {ddl_type}")


def _bool_to_int(value: bool | None) -> int | None:
    if value is None:
        return None
    return 1 if value else 0


def _int_to_bool(value: int | None) -> bool | None:
    if value is None:
        return None
    return bool(value)


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    for col in ("open_correct", "path_correct", "close_correct"):
        d[col] = _int_to_bool(d.get(col))
    for col in ("error_types_json", "reason_guesses_json"):
        raw = d.get(col)
        d[col] = json.loads(raw) if raw else []
    for col in _V2_JSON_COLUMNS:
        raw = d.get(col)
        d[col] = json.loads(raw) if raw else {}
    return d


def _json_dumps(value: Any) -> str:
    return json.dumps(value if value is not None else {})


def _block(review_payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = review_payload.get(key)
    return value if isinstance(value, dict) else {}


def _review_schema_version(review_payload: dict[str, Any]) -> int:
    meta = _block(review_payload, "meta")
    try:
        return int(meta.get("schema_version", 1))
    except (TypeError, ValueError):
        return 1


def _payload_with_review_id(review_payload: dict[str, Any], review_id: str) -> dict[str, Any]:
    payload = dict(review_payload)
    payload["review_id"] = review_id
    meta = dict(_block(payload, "meta"))
    if meta:
        meta["review_id"] = review_id
        payload["meta"] = meta
    return payload


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def save_review_record(review_payload: dict[str, Any]) -> str:
    """
    Persist a deterministic review result. Returns the new review_id (UUID4).

    Expects a status="ok" payload from run_review_for_prediction(), which must
    contain keys: symbol, prediction_for_date, prediction_id, comparison, error_info,
    review_summary.

    Multiple saves for the same (symbol, prediction_for_date) are allowed — each
    creates a new row. Use get_latest_review_for_target_date() to retrieve latest.
    """
    init_db()
    review_id = str(uuid.uuid4())
    stored_payload = _payload_with_review_id(review_payload, review_id)
    comparison: dict = review_payload.get("comparison") or {}
    error_info: dict = review_payload.get("error_info") or {}
    meta = _block(stored_payload, "meta")
    primary_projection = _block(stored_payload, "primary_projection")
    peer_adjustment = _block(stored_payload, "peer_adjustment")
    final_projection = _block(stored_payload, "final_projection")
    historical_probability = _block(stored_payload, "historical_probability")
    actual_outcome = _block(stored_payload, "actual_outcome")
    review_result = _block(stored_payload, "review_result")
    rule_extraction = _block(stored_payload, "rule_extraction")

    open_correct = comparison.get("open_correct")
    path_correct = comparison.get("path_correct")
    close_correct = comparison.get("close_correct")

    with _get_conn() as conn:
        conn.execute(
            """INSERT INTO deterministic_review_log
               (id, prediction_id, symbol, prediction_for_date, created_at,
                overall_score, correct_count, total_count,
                pred_open, pred_path, pred_close,
                actual_open_type, actual_path, actual_close_type,
                open_correct, path_correct, close_correct,
                error_category, primary_error,
                error_types_json, reason_guesses_json,
                review_summary, comparison_json, error_info_json,
                review_schema_version,
                meta_json, primary_projection_json, peer_adjustment_json,
                final_projection_json, historical_probability_json, actual_outcome_json,
                review_result_json, rule_extraction_json, review_payload_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                review_id,
                str(review_payload.get("prediction_id", "")),
                str(review_payload.get("symbol", "")),
                str(review_payload.get("prediction_for_date", "")),
                datetime.now().isoformat(timespec="seconds"),
                float(error_info.get("overall_score", 0.0)),
                int(error_info.get("correct_count", 0)),
                int(error_info.get("total_count", 3)),
                comparison.get("pred_open"),
                comparison.get("pred_path"),
                comparison.get("pred_close"),
                comparison.get("actual_open_type"),
                comparison.get("actual_path"),
                comparison.get("actual_close_type"),
                _bool_to_int(open_correct),
                _bool_to_int(path_correct),
                _bool_to_int(close_correct),
                str(error_info.get("error_category", "")),
                error_info.get("primary_error"),
                json.dumps(error_info.get("error_types", [])),
                json.dumps(error_info.get("reason_guesses", [])),
                str(review_payload.get("review_summary", "")),
                json.dumps(comparison),
                json.dumps(error_info),
                _review_schema_version(stored_payload),
                _json_dumps(meta),
                _json_dumps(primary_projection),
                _json_dumps(peer_adjustment),
                _json_dumps(final_projection),
                _json_dumps(historical_probability),
                _json_dumps(actual_outcome),
                _json_dumps(review_result),
                _json_dumps(rule_extraction),
                _json_dumps(stored_payload),
            ),
        )
    return review_id


def load_review_records(
    symbol: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Return up to `limit` review records newest-first, optionally filtered by symbol.

    Each returned dict has bool|None for open_correct/path_correct/close_correct,
    and list for error_types_json / reason_guesses_json.
    """
    init_db()
    with _get_conn() as conn:
        if symbol is None:
            rows = conn.execute(
                """SELECT * FROM deterministic_review_log
                   ORDER BY prediction_for_date DESC, created_at DESC
                   LIMIT ?""",
                (limit,),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM deterministic_review_log
                   WHERE symbol = ?
                   ORDER BY prediction_for_date DESC, created_at DESC
                   LIMIT ?""",
                (symbol, limit),
            ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_latest_review_for_target_date(
    symbol: str,
    prediction_for_date: str,
) -> dict[str, Any] | None:
    """Return the most recent review for (symbol, prediction_for_date), or None."""
    init_db()
    with _get_conn() as conn:
        row = conn.execute(
            """SELECT * FROM deterministic_review_log
               WHERE symbol = ? AND prediction_for_date = ?
               ORDER BY created_at DESC, rowid DESC LIMIT 1""",
            (symbol, prediction_for_date),
        ).fetchone()
    return _row_to_dict(row) if row else None


def count_real_vs_historical(symbol: str | None = None) -> dict[str, int]:
    """
    Count deterministic_review_log rows by source type.

    Returns dict with keys:
      "real"       — rows whose prediction_id exists in prediction_log
      "historical" — rows whose prediction_id does NOT exist in prediction_log
      "total"      — total rows
    """
    init_db()
    with _get_conn() as conn:
        if symbol is not None:
            total = conn.execute(
                "SELECT COUNT(*) FROM deterministic_review_log WHERE symbol = ?",
                (symbol,),
            ).fetchone()[0]
            real = conn.execute(
                """SELECT COUNT(*) FROM deterministic_review_log d
                   WHERE d.symbol = ?
                   AND EXISTS (SELECT 1 FROM prediction_log p WHERE p.id = d.prediction_id)""",
                (symbol,),
            ).fetchone()[0]
        else:
            total = conn.execute(
                "SELECT COUNT(*) FROM deterministic_review_log"
            ).fetchone()[0]
            real = conn.execute(
                """SELECT COUNT(*) FROM deterministic_review_log d
                   WHERE EXISTS (SELECT 1 FROM prediction_log p WHERE p.id = d.prediction_id)"""
            ).fetchone()[0]
    return {"real": real, "historical": total - real, "total": total}
