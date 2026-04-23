"""
services/features_20d.py

Unified 20-trading-day feature engineering for AVGO (and peer symbols).

Public API
----------
compute_20d_features(df) -> dict
    Accepts a DataFrame of recent OHLCV rows (must be sorted ascending by date).
    Uses the last 20 rows; accepts fewer with a degraded warning.
    Returns a stable feature dict ready for exclusion layer, primary analysis,
    and consistency check.

Input columns required
----------------------
    Date    — date string or datetime (for metadata only)
    Open    — float, today's open price
    High    — float, today's 20-day rolling high (and intraday high)
    Low     — float, today's 20-day rolling low (and intraday low)
    Close   — float, closing price
    Volume  — float, trading volume

Optional columns (used if present, ignored otherwise)
------------------------------------------------------
    V_ratio — pre-computed Volume / MA20_Volume from encoder pipeline;
              used for vol_ratio20 cross-check only, not as primary source

Output fields
-------------
    pos20              float | None  — where Close sits in 20-day High/Low range (0–100)
    ret1               float | None  — 1-day return vs prior Close, in %
    ret3               float | None  — 3-day return, in %
    ret5               float | None  — 5-day return, in %
    ret10              float | None  — 10-day return, in %
    ret20              float | None  — 20-day return (first to last row in window), in %
    vol_ratio20        float | None  — today's Volume / mean(prior 19 volumes in window)
    near_high20        bool | None   — Close within 3 % of 20-day High
    near_low20         bool | None   — Close within 3 % of 20-day Low
    upper_shadow_ratio float | None  — upper wick / total candle range (latest day)
    lower_shadow_ratio float | None  — lower wick / total candle range (latest day)

Metadata fields
---------------
    days_used          int           — number of rows actually consumed
    target_date        str | None    — Date of the latest row
    high_20d           float | None  — 20-day rolling High
    low_20d            float | None  — 20-day rolling Low
    latest_close       float | None  — Close of the latest row
    warnings           list[str]     — non-fatal issues (empty = all good)
    ready              bool          — False if critical fields could not be computed
"""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

WINDOW = 20
_NEAR_THRESHOLD = 0.03   # 3 %: within this fraction of high/low → near_high/near_low


# ── helpers ───────────────────────────────────────────────────────────────────

def _sf(value: Any) -> float | None:
    """Safe float conversion; returns None for NaN / non-numeric."""
    try:
        f = float(value)
        return None if math.isnan(f) or math.isinf(f) else f
    except (TypeError, ValueError):
        return None


def _rnd(value: float | None, digits: int = 4) -> float | None:
    return round(value, digits) if value is not None else None


def _pct_return(close_now: float | None, close_then: float | None) -> float | None:
    """(close_now / close_then - 1) * 100; None when either value is missing or zero."""
    if close_now is None or close_then is None or close_then == 0:
        return None
    return (close_now / close_then - 1) * 100


# ── shadow ratio helpers (intraday candle of the latest row) ──────────────────

def _shadow_ratios(
    open_: float | None,
    high: float | None,
    low: float | None,
    close: float | None,
) -> tuple[float | None, float | None]:
    """
    Returns (upper_shadow_ratio, lower_shadow_ratio).

    Definitions (latest-day candle):
      total_range        = High - Low
      upper_shadow       = High - max(Open, Close)   ← candle top to body top
      lower_shadow       = min(Open, Close) - Low    ← body bottom to candle bottom
      upper_shadow_ratio = max(0, upper_shadow) / total_range
      lower_shadow_ratio = max(0, lower_shadow) / total_range

    Both return None when any input is missing or total_range == 0.
    """
    if any(v is None for v in (open_, high, low, close)):
        return None, None
    total_range = high - low  # type: ignore[operator]
    if total_range <= 0:
        return None, None
    body_top    = max(open_, close)  # type: ignore[type-var]
    body_bottom = min(open_, close)  # type: ignore[type-var]
    upper = max(0.0, high - body_top) / total_range    # type: ignore[operator]
    lower = max(0.0, body_bottom - low) / total_range  # type: ignore[operator]
    return round(upper, 4), round(lower, 4)


# ── public API ────────────────────────────────────────────────────────────────

def compute_20d_features(df: pd.DataFrame) -> dict[str, Any]:
    """
    Compute unified 20-day features from a DataFrame of recent OHLCV rows.

    Parameters
    ----------
    df : pd.DataFrame
        Rows sorted ascending by date.  Must contain at minimum:
        Date, Open, High, Low, Close, Volume.
        Caller is responsible for pre-filtering to the desired window;
        this function internally clips to the last WINDOW rows.

    Returns
    -------
    dict with the fields documented in this module's docstring.
    Never raises — degrades gracefully with warnings and None values.
    """
    warnings: list[str] = []

    # ── guard: empty / wrong type ─────────────────────────────────────────────
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return _empty_result("输入数据为空或格式无效。")

    required = {"Open", "High", "Low", "Close", "Volume"}
    missing = required - set(df.columns)
    if missing:
        return _empty_result(f"缺少必要字段：{', '.join(sorted(missing))}。")

    # ── clip to last WINDOW rows ───────────────────────────────────────────────
    df = df.copy().tail(WINDOW).reset_index(drop=True)
    days_used = len(df)
    if days_used < WINDOW:
        warnings.append(f"样本不足 {WINDOW} 天，实际使用 {days_used} 天。")

    # ── extract series ─────────────────────────────────────────────────────────
    close  = pd.to_numeric(df["Close"],  errors="coerce")
    high   = pd.to_numeric(df["High"],   errors="coerce")
    low    = pd.to_numeric(df["Low"],    errors="coerce")
    volume = pd.to_numeric(df["Volume"], errors="coerce")
    open_  = pd.to_numeric(df["Open"],   errors="coerce")

    latest_close  = _sf(close.iloc[-1])
    latest_open   = _sf(open_.iloc[-1])
    latest_high   = _sf(high.iloc[-1])
    latest_low    = _sf(low.iloc[-1])
    latest_volume = _sf(volume.iloc[-1])

    high_20d = _sf(high.max())
    low_20d  = _sf(low.min())

    target_date: str | None = None
    if "Date" in df.columns:
        raw = df["Date"].iloc[-1]
        try:
            target_date = str(pd.to_datetime(raw).date())
        except Exception:
            target_date = str(raw)

    # ── pos20 ─────────────────────────────────────────────────────────────────
    # Where does today's Close sit within the 20-day High/Low range?  (0 = at 20d low, 100 = at 20d high)
    pos20: float | None = None
    if latest_close is not None and high_20d is not None and low_20d is not None:
        rng = high_20d - low_20d
        if rng > 0:
            pos20 = (latest_close - low_20d) / rng * 100
        else:
            warnings.append("20日价格区间为零，pos20 无法计算。")

    # ── returns ───────────────────────────────────────────────────────────────
    # retN = (Close_latest / Close_N_days_ago - 1) * 100
    # Index reference: latest is index -1 (iloc[-1]); N days ago is iloc[-(N+1)]
    def _ret(n: int) -> float | None:
        if days_used <= n:
            return None
        return _pct_return(latest_close, _sf(close.iloc[-(n + 1)]))

    ret1  = _ret(1)
    ret3  = _ret(3)
    ret5  = _ret(5)
    ret10 = _ret(10)
    # ret20: first close in window vs latest close
    ret20: float | None = None
    if days_used >= 2:
        ret20 = _pct_return(latest_close, _sf(close.iloc[0]))

    # ── vol_ratio20 ───────────────────────────────────────────────────────────
    # Today's volume vs mean of the prior 19 volumes in the 20-day window.
    # Matches the encoder's MA20_Volume convention (shift-1 before rolling mean).
    # Falls back to mean of all available prior volumes if fewer than 19 rows.
    vol_ratio20: float | None = None
    prior_vols = volume.iloc[:-1].dropna()
    if latest_volume is not None and len(prior_vols) > 0:
        avg = _sf(prior_vols.mean())
        if avg and avg > 0:
            vol_ratio20 = latest_volume / avg

    # ── near_high20 / near_low20 ──────────────────────────────────────────────
    # True when today's Close is within _NEAR_THRESHOLD of the 20-day extreme.
    near_high20: bool | None = None
    near_low20:  bool | None = None
    if latest_close is not None and high_20d is not None and high_20d > 0:
        near_high20 = latest_close >= high_20d * (1 - _NEAR_THRESHOLD)
    if latest_close is not None and low_20d is not None and low_20d > 0:
        near_low20 = latest_close <= low_20d * (1 + _NEAR_THRESHOLD)

    # ── shadow ratios (latest candle only) ────────────────────────────────────
    upper_shadow_ratio, lower_shadow_ratio = _shadow_ratios(
        latest_open, latest_high, latest_low, latest_close
    )

    # ── ready flag ────────────────────────────────────────────────────────────
    critical = [pos20, ret1, vol_ratio20]
    ready = any(v is not None for v in critical)
    if not ready:
        warnings.append("核心字段（pos20 / ret1 / vol_ratio20）均无法计算，特征不可用。")

    return {
        # ── primary features ─────────────────────────────────────────────────
        "pos20":              _rnd(pos20, 2),
        "ret1":               _rnd(ret1, 4),
        "ret3":               _rnd(ret3, 4),
        "ret5":               _rnd(ret5, 4),
        "ret10":              _rnd(ret10, 4),
        "ret20":              _rnd(ret20, 4),
        "vol_ratio20":        _rnd(vol_ratio20, 4),
        "near_high20":        near_high20,
        "near_low20":         near_low20,
        "upper_shadow_ratio": upper_shadow_ratio,
        "lower_shadow_ratio": lower_shadow_ratio,
        # ── metadata ─────────────────────────────────────────────────────────
        "days_used":          days_used,
        "target_date":        target_date,
        "high_20d":           _rnd(high_20d, 4),
        "low_20d":            _rnd(low_20d, 4),
        "latest_close":       _rnd(latest_close, 4),
        "warnings":           warnings,
        "ready":              ready,
    }


def _empty_result(reason: str) -> dict[str, Any]:
    return {
        "pos20":              None,
        "ret1":               None,
        "ret3":               None,
        "ret5":               None,
        "ret10":              None,
        "ret20":              None,
        "vol_ratio20":        None,
        "near_high20":        None,
        "near_low20":         None,
        "upper_shadow_ratio": None,
        "lower_shadow_ratio": None,
        "days_used":          0,
        "target_date":        None,
        "high_20d":           None,
        "low_20d":            None,
        "latest_close":       None,
        "warnings":           [reason],
        "ready":              False,
    }
