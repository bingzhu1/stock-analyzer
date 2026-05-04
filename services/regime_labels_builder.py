"""services/regime_labels_builder.py — pure regime label builder.

Step 3R-2 implementation per Step 3R-1 design (commit ``a8df93a``) +
checkpoint (``8d4fe8f``) + Step 3R-4 protocol design (``a58aad4``) +
checkpoint (``abe3ba2``). Computes the five v1 regime labels +
nine raw features defined by ``regime_labels.v1``, from pandas
DataFrames the caller already loads.

This module is **read-only diagnostics**:
- never reads DB / CSV / network; never imports ``yfinance`` /
  ``requests`` / trading APIs / v1 stub trio
- never mutates input DataFrames
- never raises (always returns a dict; missing data → label="unknown"
  + raw feature=None + warning string)
- anti-lookahead: only consumes rows with ``Date <= as_of_date``
  (mirrors ``regime_features_builder._compute_pos20`` semantics)
- 2026 final-test cutoff: ``as_of_date >= final_test_cutoff`` →
  ``final_test_refusal=True`` + all labels="unknown" + all
  raw_features=None + ``warnings`` includes ``"final_test_range_refusal"``
- bucket thresholds are **design candidates** (Step 3R-1 §5); they
  are NOT validated and the helper does NOT claim pass/fail —
  validation reports are produced separately under Step 3R-4 protocol

Public API:
    build_regime_labels(
        avgo_df, peer_dfs=None, market_dfs=None, *,
        as_of_date, final_test_cutoff="2026-01-01",
    ) -> dict
"""
from __future__ import annotations

from typing import Any


SCHEMA_VERSION = "regime_labels.v1"
DEFAULT_FINAL_TEST_CUTOFF = "2026-01-01"
_POS20_WINDOW = 20
_PEER_5D_WINDOW = 5
_MARKET_TREND_WINDOW = 60

_LABEL_KEYS: tuple[str, ...] = (
    "pos20_regime",
    "avgo_minus_soxx_20d_regime",
    "peer_momentum_regime",
    "market_trend_regime",
    "monthly_context_regime",
)

_RAW_FEATURE_KEYS: tuple[str, ...] = (
    "pos20",
    "avgo_minus_soxx_20d",
    "peer_confirm_count",
    "peer_5d_aligned_pct",
    "qqq_60d_slope_per_month",
    "qqq_60d_drawdown",
    "soxx_60d_slope_per_month",
    "monthly_return_pct",
    "monthly_max_abs_daily_return",
)

_PEER_TICKERS_FOR_MOMENTUM: tuple[str, ...] = ("NVDA", "SOXX", "QQQ")


# ── helpers ──────────────────────────────────────────────────────────────

def _safe_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if f != f:  # noqa: PLR0124 — NaN check
        return None
    return f


def _is_within_final_test_range(date_str: str | None, cutoff: str) -> bool:
    if not isinstance(date_str, str):
        return False
    return date_str[:10] >= cutoff[:10]


def _row_at(df, target_ts):
    if df is None or df.empty or "Date" not in df.columns:
        return None
    matches = df.index[df["Date"] == target_ts].tolist()
    if not matches:
        return None
    return matches[0]


def _last_idx_le(df, target_ts):
    """Return the last row index whose ``Date <= target_ts``, or None."""
    if df is None or df.empty or "Date" not in df.columns:
        return None
    mask = df["Date"] <= target_ts
    if not mask.any():
        return None
    return df.index[mask][-1]


def _compute_pos20_at(df, target_ts) -> tuple[float | None, str | None]:
    """Mirrors ``regime_features_builder._compute_pos20`` but takes any
    DataFrame — kept inline so this module stays standalone."""
    idx = _row_at(df, target_ts)
    if idx is None:
        return None, "missing_target_date"
    if idx < _POS20_WINDOW - 1:
        return None, "insufficient_history"
    window = df.iloc[idx - (_POS20_WINDOW - 1) : idx + 1]
    highs = [_safe_float(v) for v in window["High"].tolist()] if "High" in window.columns else []
    lows = [_safe_float(v) for v in window["Low"].tolist()] if "Low" in window.columns else []
    if (
        len(highs) != _POS20_WINDOW
        or len(lows) != _POS20_WINDOW
        or any(h is None for h in highs)
        or any(l is None for l in lows)
    ):
        return None, "missing_ohlc"
    close = _safe_float(df.iloc[idx].get("Close"))
    if close is None:
        return None, "missing_ohlc"
    hi, lo = max(highs), min(lows)
    band = hi - lo
    if band <= 0:
        return None, "flat_band"
    return (close - lo) / band, None


def _nday_return_decimal(df, target_ts, n: int) -> float | None:
    """``Close_t / Close_{t-n} − 1`` as a decimal fraction."""
    idx = _row_at(df, target_ts)
    if idx is None or idx < n:
        return None
    c_now = _safe_float(df.iloc[idx].get("Close"))
    c_prev = _safe_float(df.iloc[idx - n].get("Close"))
    if c_now is None or c_prev is None or c_prev == 0:
        return None
    return (c_now - c_prev) / c_prev


def _trailing_slice(df, target_ts, lookback: int):
    """Return the trailing ``lookback + 1`` rows ending at target_ts.

    Only consumes rows with ``Date <= target_ts`` (anti-lookahead).
    Returns None when target_ts is missing or window is too short.
    """
    idx = _row_at(df, target_ts)
    if idx is None or idx < lookback:
        return None
    return df.iloc[idx - lookback : idx + 1]


def _compute_60d_slope_per_month(df, target_ts) -> float | None:
    """60-day cumulative return divided by 3 (≈ 60 trading days = 3 months).

    Returns None when the window is short or close prices are missing.
    """
    ret = _nday_return_decimal(df, target_ts, _MARKET_TREND_WINDOW)
    if ret is None:
        return None
    return ret / 3.0


def _compute_60d_drawdown(df, target_ts) -> float | None:
    """Maximum drawdown within the trailing 60-day window.

    drawdown = (peak − current) / peak, with peak = max Close in window
    up to but not exceeding target_ts. Returns None when missing data.
    """
    sliced = _trailing_slice(df, target_ts, _MARKET_TREND_WINDOW)
    if sliced is None or "Close" not in sliced.columns:
        return None
    closes = [_safe_float(v) for v in sliced["Close"].tolist()]
    if any(c is None for c in closes) or not closes:
        return None
    peak = max(closes)
    if peak <= 0:
        return None
    current = closes[-1]
    return max(0.0, (peak - current) / peak)


# ── label assignment ────────────────────────────────────────────────────

def _bucket_pos20(value: float | None) -> str:
    if value is None:
        return "unknown"
    if value < 0.35:
        return "low"
    if value < 0.65:
        return "mid"
    if value < 0.85:
        return "high"
    return "extreme"


def _bucket_diff(value: float | None) -> str:
    if value is None:
        return "unknown"
    if value < -0.05:
        return "underperform"
    if value < 0.05:
        return "neutral"
    if value < 0.12:
        return "outperform"
    return "extreme_outperform"


def _bucket_peer_momentum(confirm_count: int | None) -> str:
    if confirm_count is None:
        return "unknown"
    if confirm_count <= 0:
        return "weak"
    if confirm_count == 1:
        return "mixed"
    if confirm_count == 2:
        return "confirmed"
    return "overheated"


def _bucket_market_trend(
    qqq_slope: float | None,
    qqq_drawdown: float | None,
    soxx_slope: float | None,
) -> str:
    have_any = any(
        v is not None for v in (qqq_slope, qqq_drawdown, soxx_slope)
    )
    if not have_any:
        return "unknown"
    qs = qqq_slope if qqq_slope is not None else 0.0
    ss = soxx_slope if soxx_slope is not None else 0.0
    dd = qqq_drawdown if qqq_drawdown is not None else 0.0
    if qs > 0.015 and ss > 0.015 and dd < 0.05:
        return "sustained_bull_market"
    if qs > 0.01 or ss > 0.01:
        return "bull_market"
    if (qs < -0.005 and ss < -0.005) or dd > 0.10:
        return "weak_market"
    return "neutral_market"


def _bucket_monthly_context(
    monthly_return: float | None,
    monthly_max_abs_daily: float | None,
    month: int | None,
) -> str:
    if monthly_return is None and monthly_max_abs_daily is None:
        return "unknown"
    if monthly_max_abs_daily is not None and monthly_max_abs_daily >= 0.08:
        return "shock_month"
    if monthly_return is not None and monthly_return >= 0.12:
        return "breakout_month"
    if month in {3, 6, 9, 12}:
        return "earnings_month"
    return "normal"


# ── peer momentum helpers ───────────────────────────────────────────────

def _peer_confirm_breakdown(
    peer_dfs: dict | None, target_ts,
) -> tuple[int | None, float | None, list[str]]:
    """Compute (peer_confirm_count, peer_5d_aligned_pct, warnings).

    Counts peers whose 5-day return (decimal) > 0. Missing peers are
    skipped (with a warning per missing ticker). Returns (None, None,
    warnings) when no valid peer return is computable.
    """
    warnings: list[str] = []
    peer_dfs = peer_dfs if isinstance(peer_dfs, dict) else {}
    available_returns: list[float] = []
    for ticker in _PEER_TICKERS_FOR_MOMENTUM:
        df = peer_dfs.get(ticker)
        if df is None:
            warnings.append(f"peer_momentum_skipped: missing_{ticker}")
            continue
        ret = _nday_return_decimal(df, target_ts, _PEER_5D_WINDOW)
        if ret is None:
            warnings.append(
                f"peer_momentum_skipped: {ticker}_5d_return_unavailable"
            )
            continue
        available_returns.append(ret)
    if not available_returns:
        return None, None, warnings
    confirm_count = sum(1 for r in available_returns if r > 0)
    pct = confirm_count / len(available_returns)
    return confirm_count, pct, warnings


# ── monthly context helpers ─────────────────────────────────────────────

def _monthly_context_from_avgo(
    avgo_df, target_ts,
) -> tuple[float | None, float | None, int | None, list[str]]:
    """Compute (monthly_return_pct, monthly_max_abs_daily_return, month,
    warnings) using strict-causal data within the calendar month of
    ``target_ts``.

    Anti-lookahead: only consumes rows whose Date is in the same
    calendar month AND <= target_ts. ``monthly_max_abs_daily_return``
    is the max abs daily return across days within the window;
    ``monthly_return_pct`` is computed against the prior month's last
    Close (or, when unavailable, against the first close in the
    in-month window — clearly degraded but documented).
    """
    warnings: list[str] = []
    if avgo_df is None or avgo_df.empty or "Date" not in avgo_df.columns:
        warnings.append("monthly_context_skipped: missing_avgo_df")
        return None, None, None, warnings
    target_idx = _last_idx_le(avgo_df, target_ts)
    if target_idx is None:
        warnings.append("monthly_context_skipped: target_date_out_of_range")
        return None, None, None, warnings
    target_row_date = avgo_df.iloc[target_idx]["Date"]
    try:
        month = int(target_row_date.month)
        year = int(target_row_date.year)
    except Exception:  # noqa: BLE001
        warnings.append("monthly_context_skipped: target_date_parse_failed")
        return None, None, None, warnings

    # Restrict to in-month rows up to target.
    month_mask = (
        (avgo_df["Date"].dt.year == year)
        & (avgo_df["Date"].dt.month == month)
        & (avgo_df.index <= target_idx)
    )
    in_month = avgo_df[month_mask]
    if in_month.empty:
        warnings.append("monthly_context_skipped: empty_month")
        return None, None, month, warnings

    closes = [_safe_float(v) for v in in_month["Close"].tolist()]
    if any(c is None for c in closes) or len(closes) == 0:
        warnings.append("monthly_context_skipped: missing_close")
        return None, None, month, warnings

    # Prior-month last Close: take the last row strictly before the
    # first in-month row (anti-lookahead by construction).
    first_in_month_idx = in_month.index[0]
    prior_idx = first_in_month_idx - 1
    prior_close: float | None = None
    if prior_idx >= 0:
        prior_close = _safe_float(avgo_df.iloc[prior_idx].get("Close"))

    if prior_close is not None and prior_close > 0:
        monthly_return = (closes[-1] - prior_close) / prior_close
    else:
        warnings.append("monthly_return_degraded: no_prior_month_close")
        # Degraded fallback: in-month return only.
        if closes[0] > 0:
            monthly_return = (closes[-1] - closes[0]) / closes[0]
        else:
            monthly_return = None

    # Max abs daily return: needs at least 2 closes (compare to prior
    # available close, including prior-month last close as anchor when
    # available). We walk through in-month rows and for each compare
    # with the previous Close (in-month or prior-month last).
    daily_returns: list[float] = []
    prev_close = prior_close if prior_close is not None else closes[0]
    for c in closes:
        if prev_close is not None and prev_close > 0:
            daily_returns.append(abs((c - prev_close) / prev_close))
        prev_close = c
    monthly_max_abs_daily = max(daily_returns) if daily_returns else None

    return monthly_return, monthly_max_abs_daily, month, warnings


# ── public API ──────────────────────────────────────────────────────────

def _empty_payload(
    *, as_of_date: str | None, refusal: bool, warnings: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "as_of_date": as_of_date,
        "data_cutoff_date": as_of_date,
        "labels": {key: "unknown" for key in _LABEL_KEYS},
        "raw_features": {key: None for key in _RAW_FEATURE_KEYS},
        "warnings": list(warnings),
        "final_test_refusal": refusal,
    }


def build_regime_labels(
    avgo_df,
    peer_dfs: dict | None = None,
    market_dfs: dict | None = None,
    *,
    as_of_date: str,
    final_test_cutoff: str = DEFAULT_FINAL_TEST_CUTOFF,
) -> dict[str, Any]:
    """Build the ``regime_labels.v1`` payload for one ``as_of_date``.

    Pure function; never raises. Missing data → label="unknown" + raw
    feature=None + warning string. ``as_of_date >= final_test_cutoff``
    → ``final_test_refusal=True`` + all labels="unknown" + all
    raw_features=None.

    Inputs:
    - ``avgo_df``: pandas DataFrame with ``Date`` / ``High`` / ``Low``
      / ``Close`` columns (the same the scanner already builds)
    - ``peer_dfs``: optional dict ``{"NVDA": df, "SOXX": df, "QQQ": df}``;
      missing tickers → warning + skipped
    - ``market_dfs``: optional dict ``{"QQQ": df, "SOXX": df}`` for
      60-day market trend; falls back to ``peer_dfs`` for the same
      tickers when not provided
    - ``as_of_date``: ISO date string ``"YYYY-MM-DD"``
    - ``final_test_cutoff``: ISO date string; default ``"2026-01-01"``
    """
    warnings: list[str] = []
    as_of = (
        as_of_date.strip()[:10]
        if isinstance(as_of_date, str)
        else ""
    )
    if not as_of:
        warnings.append("missing_as_of_date")
        return _empty_payload(
            as_of_date=None, refusal=False, warnings=warnings,
        )

    if _is_within_final_test_range(as_of, final_test_cutoff):
        warnings.append("final_test_range_refusal")
        return _empty_payload(
            as_of_date=as_of, refusal=True, warnings=warnings,
        )

    try:
        import pandas as pd
        target_ts = pd.to_datetime(as_of)
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"target_date_parse_failed: {exc}")
        return _empty_payload(
            as_of_date=as_of, refusal=False, warnings=warnings,
        )

    # ── 1. pos20 ────────────────────────────────────────────────────────
    pos20: float | None = None
    if avgo_df is None:
        warnings.append("missing_avgo_coded_df")
    else:
        pos20, pos_warn = _compute_pos20_at(avgo_df, target_ts)
        if pos_warn is not None:
            warnings.append(f"pos20_skipped: {pos_warn}")

    # ── 2. avgo_minus_soxx_20d (decimal fraction) ───────────────────────
    diff: float | None = None
    soxx_df = (peer_dfs or {}).get("SOXX") if isinstance(peer_dfs, dict) else None
    if avgo_df is None:
        warnings.append("missing_avgo_for_soxx_diff")
    elif soxx_df is None:
        warnings.append("missing_soxx_coded_df")
    else:
        avgo_ret = _nday_return_decimal(avgo_df, target_ts, _POS20_WINDOW)
        soxx_ret = _nday_return_decimal(soxx_df, target_ts, _POS20_WINDOW)
        if avgo_ret is None:
            warnings.append("avgo_20d_return_unavailable")
        elif soxx_ret is None:
            warnings.append("soxx_20d_return_unavailable")
        else:
            diff = avgo_ret - soxx_ret

    # ── 3. peer momentum ────────────────────────────────────────────────
    confirm_count, aligned_pct, peer_warns = _peer_confirm_breakdown(
        peer_dfs, target_ts,
    )
    warnings.extend(peer_warns)

    # ── 4. market trend (QQQ / SOXX 60d) ────────────────────────────────
    # Prefer market_dfs; fall back to peer_dfs.
    md = market_dfs if isinstance(market_dfs, dict) else {}
    pd_dict = peer_dfs if isinstance(peer_dfs, dict) else {}
    qqq_df = md.get("QQQ") if md else pd_dict.get("QQQ")
    soxx_for_trend = md.get("SOXX") if md else pd_dict.get("SOXX")
    qqq_slope: float | None = None
    qqq_drawdown: float | None = None
    soxx_slope: float | None = None
    if qqq_df is None:
        warnings.append("market_trend_skipped: missing_QQQ")
    else:
        qqq_slope = _compute_60d_slope_per_month(qqq_df, target_ts)
        if qqq_slope is None:
            warnings.append("market_trend_skipped: QQQ_60d_unavailable")
        qqq_drawdown = _compute_60d_drawdown(qqq_df, target_ts)
        if qqq_drawdown is None:
            warnings.append("market_trend_skipped: QQQ_drawdown_unavailable")
    if soxx_for_trend is None:
        warnings.append("market_trend_skipped: missing_SOXX")
    else:
        soxx_slope = _compute_60d_slope_per_month(soxx_for_trend, target_ts)
        if soxx_slope is None:
            warnings.append("market_trend_skipped: SOXX_60d_unavailable")

    # ── 5. monthly context ──────────────────────────────────────────────
    (
        monthly_return,
        monthly_max_abs_daily,
        month,
        monthly_warns,
    ) = _monthly_context_from_avgo(avgo_df, target_ts)
    warnings.extend(monthly_warns)

    # ── assemble ────────────────────────────────────────────────────────
    labels = {
        "pos20_regime": _bucket_pos20(pos20),
        "avgo_minus_soxx_20d_regime": _bucket_diff(diff),
        "peer_momentum_regime": _bucket_peer_momentum(confirm_count),
        "market_trend_regime": _bucket_market_trend(
            qqq_slope, qqq_drawdown, soxx_slope,
        ),
        "monthly_context_regime": _bucket_monthly_context(
            monthly_return, monthly_max_abs_daily, month,
        ),
    }
    raw_features = {
        "pos20": pos20,
        "avgo_minus_soxx_20d": diff,
        "peer_confirm_count": confirm_count,
        "peer_5d_aligned_pct": aligned_pct,
        "qqq_60d_slope_per_month": qqq_slope,
        "qqq_60d_drawdown": qqq_drawdown,
        "soxx_60d_slope_per_month": soxx_slope,
        "monthly_return_pct": monthly_return,
        "monthly_max_abs_daily_return": monthly_max_abs_daily,
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "as_of_date": as_of,
        "data_cutoff_date": as_of,
        "labels": labels,
        "raw_features": raw_features,
        "warnings": warnings,
        "final_test_refusal": False,
    }
