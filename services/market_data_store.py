"""SQLite-backed market data store for AVGO / NVDA / SOXX / QQQ.

This module is the new canonical home for raw OHLCV, feature, and 5-position
encoded bar data. The projection v2 chain still reads CSVs — the build script
calls the existing pipeline modules to produce those CSVs, then ingests them
here. None of the projection / exclusion / confidence rules are touched.

Public API
----------
init_database(db_path) -> None
ingest_raw_prices_csv(db_path, symbol, csv_path) -> int
ingest_features_csv(db_path, symbol, csv_path) -> int
ingest_coded_bars_csv(db_path, symbol, csv_path) -> int
load_raw_prices(db_path, symbol, *, start_date=None, end_date=None) -> DataFrame
load_features(db_path, symbol, *, start_date=None, end_date=None) -> DataFrame
load_coded_bars(db_path, symbol, *, start_date=None, end_date=None) -> DataFrame
refresh_data_health(db_path, symbols=None) -> dict
get_summary(db_path) -> dict

All functions take ``db_path`` explicitly so tests can use ``tmp_path``.
No long-lived connections are kept open.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


# ── schema ─────────────────────────────────────────────────────────────────

_RAW_PRICES_COLUMNS = [
    "symbol", "date", "open", "high", "low", "close", "adj_close", "volume",
]

_FEATURES_COLUMNS = [
    "symbol", "date", "open", "high", "low", "close", "volume",
    "adj_close", "prev_adj_close", "c_adj",
    "prev_close", "ma20_volume",
    "o_gap", "h_up", "l_down", "c_move", "v_ratio",
]

_CODED_BARS_COLUMNS = [
    "symbol", "date",
    "o_code", "h_code", "l_code", "c_code", "v_code",
    "code", "c_code_source",
]

_DATA_HEALTH_COLUMNS = [
    "symbol", "first_date", "last_date",
    "raw_rows", "feature_rows", "coded_rows",
    "missing_dates", "last_checked_at", "status",
]

_SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS raw_prices (
        symbol     TEXT    NOT NULL,
        date       TEXT    NOT NULL,
        open       REAL,
        high       REAL,
        low        REAL,
        close      REAL,
        adj_close  REAL,
        volume     INTEGER,
        PRIMARY KEY (symbol, date)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS features (
        symbol          TEXT    NOT NULL,
        date            TEXT    NOT NULL,
        open            REAL,
        high            REAL,
        low             REAL,
        close           REAL,
        volume          INTEGER,
        adj_close       REAL,
        prev_adj_close  REAL,
        c_adj           REAL,
        prev_close      REAL,
        ma20_volume     REAL,
        o_gap           REAL,
        h_up            REAL,
        l_down          REAL,
        c_move          REAL,
        v_ratio         REAL,
        PRIMARY KEY (symbol, date)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS coded_bars (
        symbol         TEXT    NOT NULL,
        date           TEXT    NOT NULL,
        o_code         INTEGER,
        h_code         INTEGER,
        l_code         INTEGER,
        c_code         INTEGER,
        v_code         INTEGER,
        code           TEXT,
        c_code_source  TEXT    NOT NULL,
        PRIMARY KEY (symbol, date)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS data_health (
        symbol           TEXT    NOT NULL,
        first_date       TEXT,
        last_date        TEXT,
        raw_rows         INTEGER NOT NULL,
        feature_rows     INTEGER NOT NULL,
        coded_rows       INTEGER NOT NULL,
        missing_dates    INTEGER NOT NULL,
        last_checked_at  TEXT    NOT NULL,
        status           TEXT    NOT NULL,
        PRIMARY KEY (symbol)
    )
    """,
)


# ── helpers ────────────────────────────────────────────────────────────────

def _normalize_symbol(symbol: str) -> str:
    text = str(symbol or "").strip().upper()
    if not text:
        raise ValueError("symbol must be a non-empty string")
    return text


def _ensure_csv_exists(csv_path: Path) -> Path:
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Input CSV not found: {path}")
    return path


def _connect(db_path: Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _to_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None


def _to_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return text if text else None


def _has_non_null_value(value: Any) -> bool:
    if value is None:
        return False
    try:
        if pd.isna(value):
            return False
    except (TypeError, ValueError):
        pass
    return True


def _normalize_date(value: Any) -> str:
    text = _to_optional_text(value)
    if not text:
        raise ValueError("date column is empty")
    return text


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _column_lookup(df: pd.DataFrame) -> dict[str, str]:
    """Map lowercase / underscored column name → actual DataFrame column name."""
    out: dict[str, str] = {}
    for col in df.columns:
        key = str(col).strip().lower().replace(" ", "_")
        out.setdefault(key, col)
    return out


# ── schema init ────────────────────────────────────────────────────────────

def init_database(db_path: Path) -> None:
    """Create the four tables if they don't exist. Idempotent."""
    with _connect(db_path) as conn:
        for statement in _SCHEMA_STATEMENTS:
            conn.execute(statement)
        conn.commit()


# ── ingest helpers ─────────────────────────────────────────────────────────

def _read_csv(csv_path: Path) -> pd.DataFrame:
    return pd.read_csv(csv_path)


def ingest_raw_prices_csv(db_path: Path, symbol: str, csv_path: Path) -> int:
    """Ingest one raw OHLCV CSV (output of data_fetcher.batch_update_all).

    UPSERTs by (symbol, date). Returns number of rows ingested.
    """
    sym = _normalize_symbol(symbol)
    path = _ensure_csv_exists(csv_path)
    init_database(db_path)

    df = _read_csv(path)
    cols = _column_lookup(df)
    rows: list[tuple[Any, ...]] = []
    for _, row in df.iterrows():
        try:
            date_text = _normalize_date(row[cols["date"]])
        except (KeyError, ValueError):
            continue
        rows.append((
            sym,
            date_text,
            _to_optional_float(row[cols["open"]]) if "open" in cols else None,
            _to_optional_float(row[cols["high"]]) if "high" in cols else None,
            _to_optional_float(row[cols["low"]]) if "low" in cols else None,
            _to_optional_float(row[cols["close"]]) if "close" in cols else None,
            _to_optional_float(row[cols["adj_close"]]) if "adj_close" in cols else None,
            _to_optional_int(row[cols["volume"]]) if "volume" in cols else None,
        ))

    if not rows:
        return 0

    with _connect(db_path) as conn:
        conn.executemany(
            f"INSERT OR REPLACE INTO raw_prices "
            f"({', '.join(_RAW_PRICES_COLUMNS)}) "
            f"VALUES ({', '.join('?' * len(_RAW_PRICES_COLUMNS))})",
            rows,
        )
        conn.commit()
    return len(rows)


def ingest_features_csv(db_path: Path, symbol: str, csv_path: Path) -> int:
    """Ingest one feature CSV (output of feature_builder.batch_build_features)."""
    sym = _normalize_symbol(symbol)
    path = _ensure_csv_exists(csv_path)
    init_database(db_path)

    df = _read_csv(path)
    cols = _column_lookup(df)
    rows: list[tuple[Any, ...]] = []
    for _, row in df.iterrows():
        try:
            date_text = _normalize_date(row[cols["date"]])
        except (KeyError, ValueError):
            continue
        rows.append((
            sym,
            date_text,
            _to_optional_float(row[cols["open"]]) if "open" in cols else None,
            _to_optional_float(row[cols["high"]]) if "high" in cols else None,
            _to_optional_float(row[cols["low"]]) if "low" in cols else None,
            _to_optional_float(row[cols["close"]]) if "close" in cols else None,
            _to_optional_int(row[cols["volume"]]) if "volume" in cols else None,
            _to_optional_float(row[cols["adj_close"]]) if "adj_close" in cols else None,
            _to_optional_float(row[cols["prev_adj_close"]]) if "prev_adj_close" in cols else None,
            _to_optional_float(row[cols["c_adj"]]) if "c_adj" in cols else None,
            _to_optional_float(row[cols["prevclose"]]) if "prevclose" in cols else None,
            _to_optional_float(row[cols["ma20_volume"]]) if "ma20_volume" in cols else None,
            _to_optional_float(row[cols["o_gap"]]) if "o_gap" in cols else None,
            _to_optional_float(row[cols["h_up"]]) if "h_up" in cols else None,
            _to_optional_float(row[cols["l_down"]]) if "l_down" in cols else None,
            _to_optional_float(row[cols["c_move"]]) if "c_move" in cols else None,
            _to_optional_float(row[cols["v_ratio"]]) if "v_ratio" in cols else None,
        ))

    if not rows:
        return 0

    with _connect(db_path) as conn:
        conn.executemany(
            f"INSERT OR REPLACE INTO features "
            f"({', '.join(_FEATURES_COLUMNS)}) "
            f"VALUES ({', '.join('?' * len(_FEATURES_COLUMNS))})",
            rows,
        )
        conn.commit()
    return len(rows)


def ingest_coded_bars_csv(db_path: Path, symbol: str, csv_path: Path) -> int:
    """Ingest one coded CSV (output of encoder.batch_encode_all).

    Derives ``c_code_source``:
      - "C_adj"           if the source row has a non-null ``C_adj`` cell
      - "C_move_fallback" otherwise (column missing or NULL)
    """
    sym = _normalize_symbol(symbol)
    path = _ensure_csv_exists(csv_path)
    init_database(db_path)

    df = _read_csv(path)
    cols = _column_lookup(df)
    rows: list[tuple[Any, ...]] = []
    has_c_adj_column = "c_adj" in cols

    for _, row in df.iterrows():
        try:
            date_text = _normalize_date(row[cols["date"]])
        except (KeyError, ValueError):
            continue

        if has_c_adj_column and _has_non_null_value(row[cols["c_adj"]]):
            c_code_source = "C_adj"
        else:
            c_code_source = "C_move_fallback"

        rows.append((
            sym,
            date_text,
            _to_optional_int(row[cols["o_code"]]) if "o_code" in cols else None,
            _to_optional_int(row[cols["h_code"]]) if "h_code" in cols else None,
            _to_optional_int(row[cols["l_code"]]) if "l_code" in cols else None,
            _to_optional_int(row[cols["c_code"]]) if "c_code" in cols else None,
            _to_optional_int(row[cols["v_code"]]) if "v_code" in cols else None,
            _to_optional_text(row[cols["code"]]) if "code" in cols else None,
            c_code_source,
        ))

    if not rows:
        return 0

    with _connect(db_path) as conn:
        conn.executemany(
            f"INSERT OR REPLACE INTO coded_bars "
            f"({', '.join(_CODED_BARS_COLUMNS)}) "
            f"VALUES ({', '.join('?' * len(_CODED_BARS_COLUMNS))})",
            rows,
        )
        conn.commit()
    return len(rows)


# ── load helpers ───────────────────────────────────────────────────────────

def _load(
    db_path: Path,
    table: str,
    columns: list[str],
    symbol: str,
    start_date: str | None,
    end_date: str | None,
) -> pd.DataFrame:
    sym = _normalize_symbol(symbol)
    init_database(db_path)
    sql = f"SELECT {', '.join(columns)} FROM {table} WHERE symbol = ?"
    params: list[Any] = [sym]
    if start_date:
        sql += " AND date >= ?"
        params.append(start_date)
    if end_date:
        sql += " AND date <= ?"
        params.append(end_date)
    sql += " ORDER BY date ASC"
    with _connect(db_path) as conn:
        df = pd.read_sql_query(sql, conn, params=params)
    if df.empty:
        return pd.DataFrame(columns=columns)
    return df


def load_raw_prices(
    db_path: Path,
    symbol: str,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.DataFrame:
    return _load(db_path, "raw_prices", _RAW_PRICES_COLUMNS, symbol, start_date, end_date)


def load_features(
    db_path: Path,
    symbol: str,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.DataFrame:
    return _load(db_path, "features", _FEATURES_COLUMNS, symbol, start_date, end_date)


def load_coded_bars(
    db_path: Path,
    symbol: str,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.DataFrame:
    return _load(db_path, "coded_bars", _CODED_BARS_COLUMNS, symbol, start_date, end_date)


# ── data_health ────────────────────────────────────────────────────────────

def _classify_status(*, raw: int, features: int, coded: int, missing: int) -> str:
    if raw == 0 and features == 0 and coded == 0:
        return "empty"
    if raw == 0 or features == 0 or coded == 0 or missing > 0:
        return "partial"
    return "ok"


def _all_symbols(conn: sqlite3.Connection) -> list[str]:
    cur = conn.execute(
        "SELECT symbol FROM raw_prices "
        "UNION SELECT symbol FROM features "
        "UNION SELECT symbol FROM coded_bars "
        "ORDER BY symbol ASC"
    )
    return [row[0] for row in cur.fetchall()]


def _layer_count(conn: sqlite3.Connection, table: str, symbol: str) -> int:
    cur = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE symbol = ?", (symbol,))
    return int(cur.fetchone()[0] or 0)


def _layer_min_max(conn: sqlite3.Connection, table: str, symbol: str) -> tuple[str | None, str | None]:
    cur = conn.execute(
        f"SELECT MIN(date), MAX(date) FROM {table} WHERE symbol = ?",
        (symbol,),
    )
    row = cur.fetchone() or (None, None)
    return row[0], row[1]


def _missing_coded_dates(conn: sqlite3.Connection, symbol: str) -> int:
    cur = conn.execute(
        """
        SELECT COUNT(*) FROM raw_prices r
        WHERE r.symbol = ?
          AND NOT EXISTS (
              SELECT 1 FROM coded_bars c
              WHERE c.symbol = r.symbol AND c.date = r.date
          )
        """,
        (symbol,),
    )
    return int(cur.fetchone()[0] or 0)


def refresh_data_health(
    db_path: Path,
    symbols: list[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Recompute one ``data_health`` row per symbol. Returns rows dict."""
    init_database(db_path)
    now = _utc_now_iso()
    out: dict[str, dict[str, Any]] = {}

    with _connect(db_path) as conn:
        target_symbols = (
            [_normalize_symbol(s) for s in symbols]
            if symbols
            else _all_symbols(conn)
        )

        for sym in target_symbols:
            raw = _layer_count(conn, "raw_prices", sym)
            feat = _layer_count(conn, "features", sym)
            coded = _layer_count(conn, "coded_bars", sym)

            mins: list[str] = []
            maxs: list[str] = []
            for table in ("raw_prices", "features", "coded_bars"):
                lo, hi = _layer_min_max(conn, table, sym)
                if lo:
                    mins.append(lo)
                if hi:
                    maxs.append(hi)
            first_date = min(mins) if mins else None
            last_date = max(maxs) if maxs else None

            missing = _missing_coded_dates(conn, sym) if raw > 0 else 0
            status = _classify_status(raw=raw, features=feat, coded=coded, missing=missing)

            row = {
                "symbol": sym,
                "first_date": first_date,
                "last_date": last_date,
                "raw_rows": raw,
                "feature_rows": feat,
                "coded_rows": coded,
                "missing_dates": missing,
                "last_checked_at": now,
                "status": status,
            }
            conn.execute(
                f"INSERT OR REPLACE INTO data_health "
                f"({', '.join(_DATA_HEALTH_COLUMNS)}) "
                f"VALUES ({', '.join('?' * len(_DATA_HEALTH_COLUMNS))})",
                tuple(row[c] for c in _DATA_HEALTH_COLUMNS),
            )
            out[sym] = row

        conn.commit()

    return out


def get_summary(db_path: Path) -> dict[str, Any]:
    """Return a summary suitable for printing or test assertions."""
    init_database(db_path)
    with _connect(db_path) as conn:
        tables: dict[str, int] = {}
        for table in ("raw_prices", "features", "coded_bars", "data_health"):
            cur = conn.execute(f"SELECT COUNT(*) FROM {table}")
            tables[table] = int(cur.fetchone()[0] or 0)

        symbols = _all_symbols(conn)

        cur = conn.execute(
            f"SELECT {', '.join(_DATA_HEALTH_COLUMNS)} "
            f"FROM data_health ORDER BY symbol ASC"
        )
        health_rows = [
            dict(zip(_DATA_HEALTH_COLUMNS, row, strict=True))
            for row in cur.fetchall()
        ]

    return {
        "db_path": str(Path(db_path)),
        "tables": tables,
        "symbols": symbols,
        "data_health": health_rows,
    }
