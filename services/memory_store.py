"""Minimal persistence for structured experience memory records."""

from __future__ import annotations

import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.error_taxonomy import normalize_error_category

DB_PATH = Path("data") / "experience_memory.db"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def _connection():
    conn = _connect()
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """Create the experience memory table if needed."""
    with _connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS experience_memory (
                id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                error_category TEXT NOT NULL,
                root_cause TEXT NOT NULL,
                lesson TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_experience_memory_symbol_created
            ON experience_memory(symbol, created_at DESC)
            """
        )
        conn.commit()


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def save_experience(
    *,
    symbol: str,
    error_category: str,
    root_cause: str,
    lesson: str,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Persist one structured experience record and return it."""
    clean_symbol = symbol.strip().upper()
    clean_root_cause = root_cause.strip()
    clean_lesson = lesson.strip()

    if not clean_symbol:
        raise ValueError("symbol is required")
    if not clean_root_cause:
        raise ValueError("root_cause is required")
    if not clean_lesson:
        raise ValueError("lesson is required")

    init_db()
    record_id = uuid.uuid4().hex
    record = {
        "id": record_id,
        "symbol": clean_symbol,
        "error_category": normalize_error_category(error_category),
        "root_cause": clean_root_cause,
        "lesson": clean_lesson,
        "created_at": created_at or _now_iso(),
    }

    with _connection() as conn:
        conn.execute(
            """
            INSERT INTO experience_memory
                (id, symbol, error_category, root_cause, lesson, created_at)
            VALUES
                (:id, :symbol, :error_category, :root_cause, :lesson, :created_at)
            """,
            record,
        )
        conn.commit()

    return record


def get_experience(experience_id: str) -> dict[str, Any] | None:
    """Return one experience record by id, or None when absent."""
    init_db()
    with _connection() as conn:
        row = conn.execute(
            """
            SELECT id, symbol, error_category, root_cause, lesson, created_at
            FROM experience_memory
            WHERE id = ?
            """,
            (experience_id,),
        ).fetchone()
    return _row_to_dict(row)


def list_experiences(
    *,
    symbol: str | None = None,
    error_category: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """List recent experience records, optionally filtered by symbol/category."""
    init_db()
    filters: list[str] = []
    params: list[Any] = []

    if symbol:
        filters.append("symbol = ?")
        params.append(symbol.strip().upper())
    if error_category:
        filters.append("error_category = ?")
        params.append(normalize_error_category(error_category))

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    safe_limit = max(1, min(int(limit), 500))

    with _connection() as conn:
        rows = conn.execute(
            f"""
            SELECT id, symbol, error_category, root_cause, lesson, created_at
            FROM experience_memory
            {where_clause}
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (*params, safe_limit),
        ).fetchall()

    return [dict(row) for row in rows]
