"""services/data_query.py

Load and enrich symbol data for the data workbench.

Public API
----------
load_symbol_data(symbol, window, fields, *, _reader) -> pd.DataFrame
    Returns a DataFrame with Date + requested columns, sliced to the last
    `window` rows (window=0 returns all rows).  Never raises on empty fields;
    raises ValueError for unsupported symbol/field, FileNotFoundError when the
    CSV is absent.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Callable

import pandas as pd

# ── paths ─────────────────────────────────────────────────────────────────────
# Absolute so the module works regardless of CWD (AppTest, CLI, etc.)
_CODED_DIR = Path(__file__).resolve().parent.parent / "coded_data"

# ── constants ─────────────────────────────────────────────────────────────────
SUPPORTED_SYMBOLS: frozenset[str] = frozenset({"AVGO", "NVDA", "SOXX", "QQQ"})

# Fields present in the coded CSV as-is
_CSV_FIELDS: frozenset[str] = frozenset({
    "Open", "High", "Low", "Close", "Volume", "Code",
})

# Fields computed on-the-fly by _enrich()
_DERIVED_FIELDS: frozenset[str] = frozenset({
    "Ret3", "Ret5", "Pos30", "PosLabel", "StageLabel",
})

ALL_SUPPORTED_FIELDS: frozenset[str] = _CSV_FIELDS | _DERIVED_FIELDS

# Default fields returned when caller requests none
_DEFAULT_FIELDS: list[str] = ["Open", "High", "Low", "Close", "Volume"]


# ── internal: stage classifier (matches app.py classify_stage exactly) ────────

def _classify_stage(
    pos30: float,
    ret3: float,
    ret5: float,
    vol5_ratio: float,
    vol_expanding: bool,
) -> str:
    """Rule-based momentum stage label. Returns '—' when any input is NaN."""
    if any(math.isnan(x) for x in [pos30, ret3, ret5, vol5_ratio]):
        return "—"

    if pos30 >= 70 and ret3 < -2.0:
        return "衰竭风险"
    if pos30 >= 75 and ret5 < -1.5:
        return "衰竭风险"
    if pos30 >= 65 and (not vol_expanding) and abs(ret3) < 2.0:
        return "分歧"
    if pos30 >= 60 and ret5 > 0 and vol5_ratio < 0.85:
        return "分歧"
    if ret3 >= 4.0 and vol5_ratio >= 1.2:
        return "加速"
    if ret5 >= 7.0 and vol5_ratio >= 1.15 and vol_expanding:
        return "加速"
    if pos30 < 35 and ret3 >= 1.5 and vol_expanding and vol5_ratio >= 1.0:
        return "启动"
    if pos30 < 40 and ret5 >= 2.5 and vol5_ratio >= 1.1:
        return "启动"
    if abs(ret5) < 2.0 and vol5_ratio < 0.90:
        return "整理"
    if abs(ret3) < 1.0 and abs(ret5) < 3.0:
        return "整理"
    if ret5 >= 0:
        return "延续"
    return "整理"


# ── internal: enrichment ──────────────────────────────────────────────────────

def _enrich(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived columns to a coded DataFrame. Works in-place on a copy."""
    df = df.copy()
    close = df["Close"].astype(float)
    high  = df["High"].astype(float)
    low   = df["Low"].astype(float)
    vol   = df["Volume"].astype(float)

    # Returns
    df["Ret3"] = (close.pct_change(3) * 100).round(2)
    df["Ret5"] = (close.pct_change(5) * 100).round(2)

    # 30-day position (0–100 scale)
    roll_high30 = high.rolling(30).max()
    roll_low30  = low.rolling(30).min()
    rng         = roll_high30 - roll_low30
    pos         = (close - roll_low30) / rng.where(rng > 0)
    df["Pos30"] = (pos * 100).round(1)

    # Position label
    def _pos_label(p: float) -> str:
        if pd.isna(p):
            return "—"
        if p < 33:
            return "低位"
        if p >= 67:
            return "高位"
        return "中位"

    df["PosLabel"] = df["Pos30"].apply(_pos_label)

    # Stage label helpers
    vol5_mean    = vol.rolling(5).mean()
    vol5_ratio   = (vol / vol5_mean).where(vol5_mean > 0)
    vol_expanding = (vol > vol.shift(1)).fillna(False)

    df["_vol5r"]  = vol5_ratio
    df["_volexp"] = vol_expanding

    def _stage(row: pd.Series) -> str:
        v5r = row["_vol5r"]
        return _classify_stage(
            row["Pos30"],
            row["Ret3"],
            row["Ret5"],
            float("nan") if pd.isna(v5r) else float(v5r),
            bool(row["_volexp"]),
        )

    df["StageLabel"] = df.apply(_stage, axis=1)
    df = df.drop(columns=["_vol5r", "_volexp"])
    return df


# ── public API ────────────────────────────────────────────────────────────────

def load_symbol_data(
    symbol: str,
    window: int = 20,
    fields: list[str] | None = None,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    _reader: Callable[[Path], pd.DataFrame] | None = None,
) -> pd.DataFrame:
    """
    Load enriched data for one symbol.

    Parameters
    ----------
    symbol : str
        One of AVGO / NVDA / SOXX / QQQ (case-insensitive).
    window : int
        Number of most-recent rows to return.  0 = return all rows.
        Ignored when ``start_date`` and ``end_date`` are both provided.
    fields : list[str] | None
        Columns to include (besides Date).  None → default OHLCV.
    start_date : str | None
        Inclusive lower bound in ``YYYY-MM-DD`` format.  Requires ``end_date``.
    end_date : str | None
        Inclusive upper bound in ``YYYY-MM-DD`` format.  Requires ``start_date``.
    _reader : callable, optional
        Injected CSV reader for tests; defaults to pd.read_csv.

    Returns
    -------
    pd.DataFrame with "Date" + requested field columns.

    Raises
    ------
    ValueError  — unsupported symbol, unknown field name, or only one of
                  start_date / end_date provided.
    FileNotFoundError — coded CSV does not exist on disk.
    """
    if bool(start_date) != bool(end_date):
        raise ValueError("start_date 和 end_date 必须同时提供或同时省略。")
    symbol = symbol.upper()
    if symbol not in SUPPORTED_SYMBOLS:
        raise ValueError(
            f"不支持的标的: {symbol}。支持: {', '.join(sorted(SUPPORTED_SYMBOLS))}"
        )

    csv_path = _CODED_DIR / f"{symbol}_coded.csv"
    reader   = _reader or (lambda p: pd.read_csv(p))

    if _reader is None and not csv_path.exists():
        raise FileNotFoundError(f"数据文件未找到: {csv_path.name}")

    raw = reader(csv_path)
    df  = _enrich(raw)

    # Resolve requested fields
    if fields:
        unknown = [f for f in fields if f not in ALL_SUPPORTED_FIELDS]
        if unknown:
            raise ValueError(f"不支持的字段: {', '.join(unknown)}")
        col_list = ["Date"] + [f for f in fields if f in df.columns]
    else:
        col_list = ["Date"] + [f for f in _DEFAULT_FIELDS if f in df.columns]

    df = df[col_list]

    if start_date and end_date:
        start_dt = pd.to_datetime(start_date)
        end_dt   = pd.to_datetime(end_date)
        if start_dt > end_dt:
            # Primary guard is in intent_planner; this is a defense-in-depth check.
            raise ValueError(
                f"start_date ({start_date}) 晚于 end_date ({end_date})，请检查输入。"
            )
        dates = pd.to_datetime(df["Date"], errors="coerce")
        mask  = (dates >= start_dt) & (dates <= end_dt)
        df = df[mask].reset_index(drop=True)
    elif window > 0:
        df = df.tail(window).reset_index(drop=True)

    return df
