# -*- coding: utf-8 -*-
"""
services/prediction_store.py

SQLite-backed store for the prediction/outcome/review research loop.

Tables
------
  prediction_log  — one row per saved prediction (before market open)
  outcome_log     — one row per captured actual result (after market close)
  review_log      — one row per LLM-generated post-close review

Status machine (prediction_log.status)
---------------------------------------
  saved  →  outcome_captured  →  review_generated
  update_prediction_status() only moves forward, never backward.

All functions call init_db() defensively so callers never need to worry
about whether the DB file exists yet.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, NoReturn

DB_PATH = Path("avgo_agent.db")

# Status ordering — used by update_prediction_status to prevent rollback
_STATUS_ORDER: dict[str, int] = {
    "saved": 0,
    "outcome_captured": 1,
    "review_generated": 2,
}

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS prediction_log (
    id                   TEXT PRIMARY KEY,
    symbol               TEXT NOT NULL,
    analysis_date        TEXT NOT NULL,
    prediction_for_date  TEXT NOT NULL,
    created_at           TEXT NOT NULL,
    final_bias           TEXT NOT NULL,
    final_confidence     TEXT NOT NULL,
    status               TEXT NOT NULL DEFAULT 'saved',
    scan_result_json     TEXT,
    research_result_json TEXT,
    predict_result_json  TEXT NOT NULL,
    snapshot_id          TEXT
);

CREATE TABLE IF NOT EXISTS outcome_log (
    id                   TEXT PRIMARY KEY,
    prediction_id        TEXT NOT NULL,
    prediction_for_date  TEXT NOT NULL,
    captured_at          TEXT NOT NULL,
    actual_open          REAL,
    actual_high          REAL,
    actual_low           REAL,
    actual_close         REAL,
    actual_prev_close    REAL,
    actual_open_change   REAL,   -- fractional ratio, e.g. 0.02 = +2%
    actual_close_change  REAL,   -- fractional ratio, convert ×100 before five-state labeling
    direction_correct    INTEGER,
    scenario_match       TEXT,
    FOREIGN KEY (prediction_id) REFERENCES prediction_log(id)
);

CREATE TABLE IF NOT EXISTS review_log (
    id                   TEXT PRIMARY KEY,
    prediction_id        TEXT NOT NULL,
    created_at           TEXT NOT NULL,
    error_category       TEXT,
    root_cause           TEXT,
    confidence_note      TEXT,
    watch_for_next_time  TEXT,
    review_json          TEXT,
    raw_llm_output       TEXT,
    FOREIGN KEY (prediction_id) REFERENCES prediction_log(id)
);

CREATE INDEX IF NOT EXISTS idx_prediction_symbol_date
    ON prediction_log (symbol, prediction_for_date);
CREATE INDEX IF NOT EXISTS idx_outcome_prediction_id
    ON outcome_log (prediction_id);
CREATE INDEX IF NOT EXISTS idx_review_prediction_id
    ON review_log (prediction_id);
"""

_CORRUPT_DB_MESSAGES = (
    "database disk image is malformed",
    "file is not a database",
)


class PredictionStoreCorruptionError(RuntimeError):
    """Raised when the local prediction history database cannot be read safely."""


def _is_corrupt_db_error(exc: BaseException) -> bool:
    if not isinstance(exc, sqlite3.DatabaseError):
        return False
    message = str(exc).lower()
    return any(fragment in message for fragment in _CORRUPT_DB_MESSAGES)


def _raise_corrupt_db_error(exc: BaseException) -> NoReturn:
    raise PredictionStoreCorruptionError(
        "历史记录数据库损坏，暂时无法读取。请先备份 avgo_agent.db；"
        "确认安全后可删除该文件并重启应用重建空历史库。"
    ) from exc


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


def _prediction_exists(conn: sqlite3.Connection, prediction_id: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM prediction_log WHERE id = ?",
        (prediction_id,),
    ).fetchone()
    return row is not None


def _advance_prediction_status(
    conn: sqlite3.Connection,
    prediction_id: str,
    new_status: str,
) -> None:
    row = conn.execute(
        "SELECT status FROM prediction_log WHERE id = ?",
        (prediction_id,),
    ).fetchone()
    if not row:
        return
    current_rank = _STATUS_ORDER.get(row["status"], 0)
    new_rank = _STATUS_ORDER.get(new_status, -1)
    if new_rank > current_rank:
        conn.execute(
            "UPDATE prediction_log SET status = ? WHERE id = ?",
            (new_status, prediction_id),
        )


def init_db() -> None:
    """Create tables and indexes if they don't exist. Safe to call multiple times."""
    with _get_conn() as conn:
        conn.executescript(_CREATE_SQL)


# ─────────────────────────────────────────────────────────────────────────────
# prediction_log
# ─────────────────────────────────────────────────────────────────────────────

def save_prediction(
    symbol: str,
    prediction_for_date: str,
    scan_result: dict[str, Any] | None,
    research_result: dict[str, Any] | None,
    predict_result: dict[str, Any],
    snapshot_id: str = "—",
) -> str:
    """
    Persist a prediction. Returns the new prediction_id (UUID4).

    Multiple saves for the same (symbol, prediction_for_date) are allowed —
    each creates a new row with its own id. Use get_prediction_by_date() to
    retrieve the latest, or track the id in session_state.
    """
    init_db()
    prediction_id = str(uuid.uuid4())
    analysis_date = datetime.now().date().isoformat()
    with _get_conn() as conn:
        conn.execute(
            """INSERT INTO prediction_log
               (id, symbol, analysis_date, prediction_for_date, created_at,
                final_bias, final_confidence, status,
                scan_result_json, research_result_json, predict_result_json, snapshot_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                prediction_id,
                symbol,
                analysis_date,
                prediction_for_date,
                datetime.now().isoformat(timespec="seconds"),
                str(predict_result.get("final_bias", "unavailable")),
                str(predict_result.get("final_confidence", "low")),
                "saved",
                json.dumps(scan_result) if scan_result is not None else None,
                json.dumps(research_result) if research_result is not None else None,
                json.dumps(predict_result),
                snapshot_id,
            ),
        )
    return prediction_id


def get_prediction(prediction_id: str) -> dict | None:
    """Fetch one prediction_log row by id. Returns None if not found."""
    try:
        init_db()
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM prediction_log WHERE id = ?", (prediction_id,)
            ).fetchone()
    except sqlite3.DatabaseError as exc:
        if _is_corrupt_db_error(exc):
            _raise_corrupt_db_error(exc)
        raise
    return dict(row) if row else None


def get_prediction_by_date(symbol: str, prediction_for_date: str) -> dict | None:
    """Return the most recent prediction for (symbol, prediction_for_date), or None."""
    try:
        init_db()
        with _get_conn() as conn:
            row = conn.execute(
                """SELECT * FROM prediction_log
                   WHERE symbol = ? AND prediction_for_date = ?
                   ORDER BY created_at DESC, rowid DESC LIMIT 1""",
                (symbol, prediction_for_date),
            ).fetchone()
    except sqlite3.DatabaseError as exc:
        if _is_corrupt_db_error(exc):
            _raise_corrupt_db_error(exc)
        raise
    return dict(row) if row else None


def update_prediction_status(prediction_id: str, new_status: str) -> None:
    """
    Advance prediction status forward along the state machine.
    Idempotent — silently ignores attempts to set an equal or lower status,
    so repeated calls and race conditions are safe.

    Valid transitions: saved → outcome_captured → review_generated
    """
    init_db()
    with _get_conn() as conn:
        _advance_prediction_status(conn, prediction_id, new_status)


def list_predictions(limit: int = 30) -> list[dict]:
    """Return up to `limit` predictions newest-first, joined with outcome if present."""
    try:
        init_db()
        with _get_conn() as conn:
            rows = conn.execute(
                """SELECT p.id, p.symbol, p.analysis_date, p.prediction_for_date,
                          p.created_at, p.final_bias, p.final_confidence,
                          p.status, p.snapshot_id,
                          o.direction_correct, o.actual_close_change,
                          o.scenario_match
                   FROM prediction_log p
                   LEFT JOIN outcome_log o ON o.prediction_id = p.id
                   ORDER BY p.prediction_for_date DESC
                   LIMIT ?""",
                (limit,),
            ).fetchall()
    except sqlite3.DatabaseError as exc:
        if _is_corrupt_db_error(exc):
            _raise_corrupt_db_error(exc)
        raise
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# outcome_log
# ─────────────────────────────────────────────────────────────────────────────

def save_outcome(
    prediction_id: str,
    prediction_for_date: str,
    actual_open: float,
    actual_high: float,
    actual_low: float,
    actual_close: float,
    actual_prev_close: float | None,
    direction_correct: int | None,
    scenario_match: str | None = None,
) -> str:
    """Persist an outcome. Returns the new outcome_id (UUID4)."""
    init_db()
    outcome_id = str(uuid.uuid4())
    open_change = (
        (actual_open - actual_prev_close) / actual_prev_close
        if actual_prev_close
        else None
    )
    close_change = (
        (actual_close - actual_prev_close) / actual_prev_close
        if actual_prev_close
        else None
    )
    with _get_conn() as conn:
        if not _prediction_exists(conn, prediction_id):
            raise ValueError(f"Prediction '{prediction_id}' not found in the database.")
        conn.execute(
            """INSERT INTO outcome_log
               (id, prediction_id, prediction_for_date, captured_at,
                actual_open, actual_high, actual_low, actual_close, actual_prev_close,
                actual_open_change, actual_close_change, direction_correct, scenario_match)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                outcome_id,
                prediction_id,
                prediction_for_date,
                datetime.now().isoformat(timespec="seconds"),
                actual_open,
                actual_high,
                actual_low,
                actual_close,
                actual_prev_close,
                open_change,
                close_change,
                direction_correct,
                scenario_match,
            ),
        )
    return outcome_id


def get_outcome_for_prediction(prediction_id: str) -> dict | None:
    """Return the most recent outcome for a prediction, or None."""
    try:
        init_db()
        with _get_conn() as conn:
            row = conn.execute(
                """SELECT * FROM outcome_log
                   WHERE prediction_id = ?
                   ORDER BY captured_at DESC LIMIT 1""",
                (prediction_id,),
            ).fetchone()
    except sqlite3.DatabaseError as exc:
        if _is_corrupt_db_error(exc):
            _raise_corrupt_db_error(exc)
        raise
    return dict(row) if row else None


# ─────────────────────────────────────────────────────────────────────────────
# review_log
# ─────────────────────────────────────────────────────────────────────────────

def save_review(
    prediction_id: str,
    error_category: str,
    root_cause: str,
    confidence_note: str,
    watch_for_next_time: str,
    review_json: str = "",
    raw_llm_output: str = "",
) -> str:
    """
    Persist an LLM review and advance prediction status to 'review_generated'.
    Returns the new review_id (UUID4).
    """
    init_db()
    review_id = str(uuid.uuid4())
    with _get_conn() as conn:
        if not _prediction_exists(conn, prediction_id):
            raise ValueError(f"Prediction '{prediction_id}' not found in the database.")
        conn.execute(
            """INSERT INTO review_log
               (id, prediction_id, created_at, error_category, root_cause,
                confidence_note, watch_for_next_time, review_json, raw_llm_output)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                review_id,
                prediction_id,
                datetime.now().isoformat(timespec="seconds"),
                error_category,
                root_cause,
                confidence_note,
                watch_for_next_time,
                review_json,
                raw_llm_output,
            ),
        )
        _advance_prediction_status(conn, prediction_id, "review_generated")
    return review_id


def get_review_for_prediction(prediction_id: str) -> dict | None:
    """Return the most recent review for a prediction, or None."""
    try:
        init_db()
        with _get_conn() as conn:
            row = conn.execute(
                """SELECT * FROM review_log
                   WHERE prediction_id = ?
                   ORDER BY created_at DESC LIMIT 1""",
                (prediction_id,),
            ).fetchone()
    except sqlite3.DatabaseError as exc:
        if _is_corrupt_db_error(exc):
            _raise_corrupt_db_error(exc)
        raise
    return dict(row) if row else None


# ─────────────────────────────────────────────────────────────────────────────
# Dict-based convenience interface (used by downstream tasks / research loop)
# ─────────────────────────────────────────────────────────────────────────────

def save_prediction_record(record: dict) -> str:
    """
    Save a prediction from a flat dict. Dispatches to save_prediction().

    Required keys: symbol, prediction_for_date, predict_result
    Optional keys: scan_result, research_result, snapshot_id
    """
    return save_prediction(
        symbol=str(record["symbol"]),
        prediction_for_date=str(record["prediction_for_date"]),
        scan_result=record.get("scan_result"),
        research_result=record.get("research_result"),
        predict_result=record["predict_result"],
        snapshot_id=str(record.get("snapshot_id", "—")),
    )


def load_prediction_records(symbol: str | None = None, limit: int = 30) -> list[dict]:
    """
    Return up to `limit` predictions newest-first, optionally filtered by symbol.

    Each row is joined with outcome data when present (same as list_predictions).
    """
    try:
        init_db()
        with _get_conn() as conn:
            if symbol is None:
                rows = conn.execute(
                    """SELECT p.id, p.symbol, p.analysis_date, p.prediction_for_date,
                              p.created_at, p.final_bias, p.final_confidence,
                              p.status, p.snapshot_id,
                              o.direction_correct, o.actual_close_change,
                              o.scenario_match
                       FROM prediction_log p
                       LEFT JOIN outcome_log o ON o.prediction_id = p.id
                       ORDER BY p.prediction_for_date DESC
                       LIMIT ?""",
                    (limit,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT p.id, p.symbol, p.analysis_date, p.prediction_for_date,
                              p.created_at, p.final_bias, p.final_confidence,
                              p.status, p.snapshot_id,
                              o.direction_correct, o.actual_close_change,
                              o.scenario_match
                       FROM prediction_log p
                       LEFT JOIN outcome_log o ON o.prediction_id = p.id
                       WHERE p.symbol = ?
                       ORDER BY p.prediction_for_date DESC
                       LIMIT ?""",
                    (symbol, limit),
                ).fetchall()
    except sqlite3.DatabaseError as exc:
        if _is_corrupt_db_error(exc):
            _raise_corrupt_db_error(exc)
        raise
    return [dict(r) for r in rows]


def get_latest_prediction_for_target_date(
    symbol: str, prediction_for_date: str
) -> dict | None:
    """Alias for get_prediction_by_date — returns the most recent prediction for (symbol, date)."""
    return get_prediction_by_date(symbol, prediction_for_date)
