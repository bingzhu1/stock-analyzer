"""SQLite-backed projection record store (Task 074).

Six tables co-located in ``data/market_data.db`` next to the Task 073 store.
Each block has its own table keyed on ``run_id``; no save_* helper writes
to a sibling block, so the storage layer enforces three-system
independence by construction.

Public API
----------
initialize_projection_record_tables(conn) -> None
create_projection_run(conn, *, symbol, as_of_date, prediction_for_date=None,
                      status="started", run_id=None) -> str
save_record_01_structure(conn, *, run_id, symbol, as_of_date,
                         lookback_days, payload) -> None
save_record_02_projection(conn, *, run_id, five_state_top1, final_direction,
                          five_state_distribution, payload) -> None
save_negative_system_record(conn, *, run_id, excluded_states, exclusion_type,
                            strength, triggered_rule, payload) -> None
save_record_03_confidence(conn, *, run_id, overall_score, confidence_band,
                          negative_confidence_level,
                          projection_confidence_level, payload) -> None
save_final_summary_record(conn, *, run_id, conflict_level, usage_advice,
                          payload) -> None
load_projection_run(conn, run_id) -> dict
list_projection_runs(conn, symbol=None, limit=50) -> list[dict]

All save_* helpers UPSERT (INSERT OR REPLACE) on ``run_id`` so re-saving
the same block is idempotent.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any


# ── schema ─────────────────────────────────────────────────────────────────

_PROJECTION_RUNS_COLUMNS = (
    "run_id", "symbol", "as_of_date", "prediction_for_date",
    "created_at", "status",
)

_RECORD_01_COLUMNS = (
    "run_id", "symbol", "as_of_date", "lookback_days",
    "payload_json", "created_at",
)

_RECORD_02_COLUMNS = (
    "run_id", "five_state_top1", "final_direction",
    "five_state_distribution_json", "payload_json", "created_at",
)

_NEGATIVE_COLUMNS = (
    "run_id", "excluded_states_json", "exclusion_type",
    "strength", "triggered_rule", "payload_json", "created_at",
)

_RECORD_03_COLUMNS = (
    "run_id", "overall_score", "confidence_band",
    "negative_confidence_level", "projection_confidence_level",
    "payload_json", "created_at",
)

_FINAL_SUMMARY_COLUMNS = (
    "run_id", "conflict_level", "usage_advice",
    "payload_json", "created_at",
)

_SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS projection_runs (
        run_id              TEXT NOT NULL,
        symbol              TEXT NOT NULL,
        as_of_date          TEXT NOT NULL,
        prediction_for_date TEXT,
        created_at          TEXT NOT NULL,
        status              TEXT NOT NULL,
        PRIMARY KEY (run_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS record_01_structure (
        run_id        TEXT NOT NULL,
        symbol        TEXT NOT NULL,
        as_of_date    TEXT NOT NULL,
        lookback_days INTEGER,
        payload_json  TEXT NOT NULL,
        created_at    TEXT NOT NULL,
        PRIMARY KEY (run_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS record_02_projection (
        run_id                       TEXT NOT NULL,
        five_state_top1              TEXT,
        final_direction              TEXT,
        five_state_distribution_json TEXT,
        payload_json                 TEXT NOT NULL,
        created_at                   TEXT NOT NULL,
        PRIMARY KEY (run_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS negative_system_records (
        run_id                TEXT NOT NULL,
        excluded_states_json  TEXT,
        exclusion_type        TEXT,
        strength              TEXT,
        triggered_rule        TEXT,
        payload_json          TEXT NOT NULL,
        created_at            TEXT NOT NULL,
        PRIMARY KEY (run_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS record_03_confidence (
        run_id                       TEXT NOT NULL,
        overall_score                REAL,
        confidence_band              TEXT,
        negative_confidence_level    TEXT,
        projection_confidence_level  TEXT,
        payload_json                 TEXT NOT NULL,
        created_at                   TEXT NOT NULL,
        PRIMARY KEY (run_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS final_summary_records (
        run_id          TEXT NOT NULL,
        conflict_level  TEXT,
        usage_advice    TEXT,
        payload_json    TEXT NOT NULL,
        created_at      TEXT NOT NULL,
        PRIMARY KEY (run_id)
    )
    """,
)

_RECORD_TABLES = (
    "projection_runs",
    "record_01_structure",
    "record_02_projection",
    "negative_system_records",
    "record_03_confidence",
    "final_summary_records",
)


# ── helpers ────────────────────────────────────────────────────────────────

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _normalize_symbol(symbol: str) -> str:
    text = str(symbol or "").strip().upper()
    if not text:
        raise ValueError("symbol must be a non-empty string")
    return text


def _require_text(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field} must be a non-empty string")
    return text


def _to_json(payload: Any) -> str:
    if payload is None:
        return "null"
    return json.dumps(payload, ensure_ascii=False, sort_keys=False, default=str)


def _from_json(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    text = str(value)
    if not text:
        return None
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return None


def _row_to_dict(cursor: sqlite3.Cursor, row: tuple[Any, ...] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    columns = [desc[0] for desc in cursor.description]
    return dict(zip(columns, row, strict=True))


def _hydrate_json_columns(record: dict[str, Any] | None, json_cols: tuple[str, ...]) -> dict[str, Any] | None:
    if record is None:
        return None
    out = dict(record)
    for col in json_cols:
        if col in out:
            out[col] = _from_json(out[col])
    return out


# ── schema init ────────────────────────────────────────────────────────────

def initialize_projection_record_tables(conn: sqlite3.Connection) -> None:
    """Create the six projection record tables if they don't exist."""
    for statement in _SCHEMA_STATEMENTS:
        conn.execute(statement)
    conn.commit()


# ── parent run ─────────────────────────────────────────────────────────────

def create_projection_run(
    conn: sqlite3.Connection,
    *,
    symbol: str,
    as_of_date: str,
    prediction_for_date: str | None = None,
    status: str = "started",
    run_id: str | None = None,
) -> str:
    """Insert (or update on conflict) a row in projection_runs.

    Returns the run_id (auto-generated UUID4 hex when not supplied).
    Idempotent on (run_id) — re-call with the same run_id replaces the row.
    """
    initialize_projection_record_tables(conn)
    sym = _normalize_symbol(symbol)
    as_of = _require_text(as_of_date, "as_of_date")
    status_text = _require_text(status, "status")
    pred_for = (
        _require_text(prediction_for_date, "prediction_for_date")
        if prediction_for_date
        else None
    )
    final_run_id = run_id or uuid.uuid4().hex

    conn.execute(
        f"INSERT OR REPLACE INTO projection_runs "
        f"({', '.join(_PROJECTION_RUNS_COLUMNS)}) "
        f"VALUES ({', '.join('?' * len(_PROJECTION_RUNS_COLUMNS))})",
        (final_run_id, sym, as_of, pred_for, _utc_now_iso(), status_text),
    )
    conn.commit()
    return final_run_id


# ── per-block save helpers ─────────────────────────────────────────────────

def save_record_01_structure(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    symbol: str,
    as_of_date: str,
    lookback_days: int | None,
    payload: dict[str, Any] | None,
) -> None:
    initialize_projection_record_tables(conn)
    rid = _require_text(run_id, "run_id")
    sym = _normalize_symbol(symbol)
    as_of = _require_text(as_of_date, "as_of_date")
    conn.execute(
        f"INSERT OR REPLACE INTO record_01_structure "
        f"({', '.join(_RECORD_01_COLUMNS)}) "
        f"VALUES ({', '.join('?' * len(_RECORD_01_COLUMNS))})",
        (
            rid, sym, as_of,
            int(lookback_days) if lookback_days is not None else None,
            _to_json(payload), _utc_now_iso(),
        ),
    )
    conn.commit()


def save_record_02_projection(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    five_state_top1: str | None,
    final_direction: str | None,
    five_state_distribution: dict[str, Any] | None,
    payload: dict[str, Any] | None,
) -> None:
    initialize_projection_record_tables(conn)
    rid = _require_text(run_id, "run_id")
    conn.execute(
        f"INSERT OR REPLACE INTO record_02_projection "
        f"({', '.join(_RECORD_02_COLUMNS)}) "
        f"VALUES ({', '.join('?' * len(_RECORD_02_COLUMNS))})",
        (
            rid,
            (str(five_state_top1).strip() if five_state_top1 else None),
            (str(final_direction).strip() if final_direction else None),
            _to_json(five_state_distribution),
            _to_json(payload),
            _utc_now_iso(),
        ),
    )
    conn.commit()


def save_negative_system_record(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    excluded_states: list[Any] | None,
    exclusion_type: str | None,
    strength: str | None,
    triggered_rule: str | None,
    payload: dict[str, Any] | None,
) -> None:
    initialize_projection_record_tables(conn)
    rid = _require_text(run_id, "run_id")
    conn.execute(
        f"INSERT OR REPLACE INTO negative_system_records "
        f"({', '.join(_NEGATIVE_COLUMNS)}) "
        f"VALUES ({', '.join('?' * len(_NEGATIVE_COLUMNS))})",
        (
            rid,
            _to_json(list(excluded_states) if excluded_states is not None else []),
            (str(exclusion_type).strip() if exclusion_type else None),
            (str(strength).strip() if strength else None),
            (str(triggered_rule).strip() if triggered_rule else None),
            _to_json(payload),
            _utc_now_iso(),
        ),
    )
    conn.commit()


def save_record_03_confidence(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    overall_score: float | None,
    confidence_band: str | None,
    negative_confidence_level: str | None,
    projection_confidence_level: str | None,
    payload: dict[str, Any] | None,
) -> None:
    initialize_projection_record_tables(conn)
    rid = _require_text(run_id, "run_id")
    conn.execute(
        f"INSERT OR REPLACE INTO record_03_confidence "
        f"({', '.join(_RECORD_03_COLUMNS)}) "
        f"VALUES ({', '.join('?' * len(_RECORD_03_COLUMNS))})",
        (
            rid,
            (float(overall_score) if overall_score is not None else None),
            (str(confidence_band).strip() if confidence_band else None),
            (str(negative_confidence_level).strip() if negative_confidence_level else None),
            (str(projection_confidence_level).strip() if projection_confidence_level else None),
            _to_json(payload),
            _utc_now_iso(),
        ),
    )
    conn.commit()


def save_final_summary_record(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    conflict_level: str | None,
    usage_advice: str | None,
    payload: dict[str, Any] | None,
) -> None:
    initialize_projection_record_tables(conn)
    rid = _require_text(run_id, "run_id")
    conn.execute(
        f"INSERT OR REPLACE INTO final_summary_records "
        f"({', '.join(_FINAL_SUMMARY_COLUMNS)}) "
        f"VALUES ({', '.join('?' * len(_FINAL_SUMMARY_COLUMNS))})",
        (
            rid,
            (str(conflict_level).strip() if conflict_level else None),
            (str(usage_advice) if usage_advice else None),
            _to_json(payload),
            _utc_now_iso(),
        ),
    )
    conn.commit()


# ── load helpers ───────────────────────────────────────────────────────────

def _fetch_one_dict(
    conn: sqlite3.Connection,
    sql: str,
    params: tuple[Any, ...],
) -> dict[str, Any] | None:
    cur = conn.execute(sql, params)
    row = cur.fetchone()
    return _row_to_dict(cur, row)


def load_projection_run(conn: sqlite3.Connection, run_id: str) -> dict[str, Any]:
    """Load every record block for one run_id.

    Each block is None when its row is missing. JSON columns are deserialized
    to dicts/lists. The returned dict shape is stable.
    """
    initialize_projection_record_tables(conn)
    rid = _require_text(run_id, "run_id")

    run_row = _fetch_one_dict(
        conn,
        f"SELECT {', '.join(_PROJECTION_RUNS_COLUMNS)} FROM projection_runs WHERE run_id = ?",
        (rid,),
    )

    record_01 = _hydrate_json_columns(
        _fetch_one_dict(
            conn,
            f"SELECT {', '.join(_RECORD_01_COLUMNS)} FROM record_01_structure WHERE run_id = ?",
            (rid,),
        ),
        ("payload_json",),
    )

    record_02 = _hydrate_json_columns(
        _fetch_one_dict(
            conn,
            f"SELECT {', '.join(_RECORD_02_COLUMNS)} FROM record_02_projection WHERE run_id = ?",
            (rid,),
        ),
        ("five_state_distribution_json", "payload_json"),
    )

    negative = _hydrate_json_columns(
        _fetch_one_dict(
            conn,
            f"SELECT {', '.join(_NEGATIVE_COLUMNS)} FROM negative_system_records WHERE run_id = ?",
            (rid,),
        ),
        ("excluded_states_json", "payload_json"),
    )

    record_03 = _hydrate_json_columns(
        _fetch_one_dict(
            conn,
            f"SELECT {', '.join(_RECORD_03_COLUMNS)} FROM record_03_confidence WHERE run_id = ?",
            (rid,),
        ),
        ("payload_json",),
    )

    final_summary = _hydrate_json_columns(
        _fetch_one_dict(
            conn,
            f"SELECT {', '.join(_FINAL_SUMMARY_COLUMNS)} FROM final_summary_records WHERE run_id = ?",
            (rid,),
        ),
        ("payload_json",),
    )

    return {
        "run_id": rid,
        "run": run_row,
        "record_01_structure": record_01,
        "record_02_projection": record_02,
        "negative_system": negative,
        "record_03_confidence": record_03,
        "final_summary": final_summary,
    }


def _completeness_for(conn: sqlite3.Connection, run_id: str) -> dict[str, bool]:
    out: dict[str, bool] = {}
    for table in (
        "record_01_structure",
        "record_02_projection",
        "negative_system_records",
        "record_03_confidence",
        "final_summary_records",
    ):
        cur = conn.execute(
            f"SELECT 1 FROM {table} WHERE run_id = ? LIMIT 1",
            (run_id,),
        )
        out[table] = cur.fetchone() is not None
    return out


def list_projection_runs(
    conn: sqlite3.Connection,
    symbol: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Most-recent-first list of projection_runs rows + per-row completeness."""
    initialize_projection_record_tables(conn)
    sql = f"SELECT {', '.join(_PROJECTION_RUNS_COLUMNS)} FROM projection_runs"
    params: list[Any] = []
    if symbol:
        sql += " WHERE symbol = ?"
        params.append(_normalize_symbol(symbol))
    sql += " ORDER BY created_at DESC, run_id DESC LIMIT ?"
    params.append(int(max(1, limit)))

    cur = conn.execute(sql, tuple(params))
    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()

    out: list[dict[str, Any]] = []
    for row in rows:
        record = dict(zip(columns, row, strict=True))
        record["completeness"] = _completeness_for(conn, record["run_id"])
        out.append(record)
    return out
