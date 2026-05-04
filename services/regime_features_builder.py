"""services/regime_features_builder.py — pure regime features builder.

Step 2G-6B.7 implementation per Step 2G-6B.4/6B.5 design (commit
`35b239d`). Computes the two regime features the soft-metadata
simulator needs (``pos20`` + ``avgo_minus_soxx_20d``) from pandas
DataFrames the scanner already loads, and packages them with cutoff /
source / warning metadata so callers (scanner, UI, agent) can drop the
dict directly into ``scan_result["regime_features"]``.

Design contract (Step 2G-6B.4/6B.5 §9 / §10):
- pure function: never reads DB / CSV / network; never imports
  ``yfinance`` / ``requests`` / trading APIs / v1 stub trio
- never mutates input DataFrames
- never raises (always returns a dict; missing data → field=None +
  warning string)
- anti-lookahead: only consumes rows with ``Date <= target_date``
  (mirrors ``scanner._get_nday_return`` semantics)
- 2026 final-test cutoff: ``as_of_date >= final_test_cutoff`` →
  ``warnings`` includes ``"final_test_range_refusal"`` (does NOT zero
  out the values; downstream simulator already refuses signals on the
  same date, so the values can stay informational)

Public API:
    build_regime_features(
        coded_df, peer_dfs, target_date_str, *,
        final_test_cutoff="2026-01-01",
    ) -> dict

``coded_df`` is the AVGO coded DataFrame with ``Date`` / ``High`` /
``Low`` / ``Close`` columns (the same the scanner already builds).
``peer_dfs`` is a dict ``{"SOXX": df_or_None, ...}`` — the SOXX entry
is the only one consumed; missing / None → ``avgo_minus_soxx_20d=None``
+ warning.
"""
from __future__ import annotations

from typing import Any


SCHEMA_SOURCE = "scan_result"
DEFAULT_FINAL_TEST_CUTOFF = "2026-01-01"
_POS20_WINDOW = 20


# ── helpers ──────────────────────────────────────────────────────────────

def _safe_float(value: Any) -> float | None:
    """Coerce to float; return None on NaN / non-numeric / bool."""
    if value is None or isinstance(value, bool):
        return None
    try:
        # pandas NA / numpy NaN both raise or return NaN; we want None.
        f = float(value)
    except (TypeError, ValueError):
        return None
    # NaN check without importing numpy explicitly.
    if f != f:  # noqa: PLR0124 — NaN != NaN
        return None
    return f


def _is_within_final_test_range(
    date_str: str | None, cutoff: str
) -> bool:
    """True iff ``date_str >= cutoff`` (string compare on YYYY-MM-DD)."""
    if not isinstance(date_str, str):
        return False
    return date_str[:10] >= cutoff[:10]


def _row_at(df, target_ts):
    """Return the first row whose Date == target_ts, or None."""
    if df is None or df.empty or "Date" not in df.columns:
        return None
    matches = df.index[df["Date"] == target_ts].tolist()
    if not matches:
        return None
    return matches[0]


def _compute_pos20(coded_df, target_ts) -> tuple[float | None, str | None]:
    """Position of Close in rolling 20-day Low/High band at target_ts.

    Returns ``(value, warning)``:
      - ``(float, None)`` on success
      - ``(None, "missing_target_date")`` when target row not in df
      - ``(None, "insufficient_history")`` when fewer than 20 prior bars
      - ``(None, "missing_ohlc")`` when High / Low / Close has NaN in the window
      - ``(None, "flat_band")`` when rolling High == rolling Low
    """
    idx = _row_at(coded_df, target_ts)
    if idx is None:
        return None, "missing_target_date"
    if idx < _POS20_WINDOW - 1:
        return None, "insufficient_history"
    window = coded_df.iloc[idx - (_POS20_WINDOW - 1) : idx + 1]
    highs = [_safe_float(v) for v in window["High"].tolist()] if "High" in window.columns else []
    lows = [_safe_float(v) for v in window["Low"].tolist()] if "Low" in window.columns else []
    if (
        len(highs) != _POS20_WINDOW
        or len(lows) != _POS20_WINDOW
        or any(h is None for h in highs)
        or any(l is None for l in lows)
    ):
        return None, "missing_ohlc"
    close = _safe_float(coded_df.iloc[idx].get("Close"))
    if close is None:
        return None, "missing_ohlc"
    hi, lo = max(highs), min(lows)
    band = hi - lo
    if band <= 0:
        return None, "flat_band"
    return (close - lo) / band, None


def _compute_nday_return(df, target_ts, n: int = _POS20_WINDOW) -> float | None:
    """``(Close_t / Close_{t-n} − 1) × 100`` (percent), or None."""
    idx = _row_at(df, target_ts)
    if idx is None or idx < n:
        return None
    c_now = _safe_float(df.iloc[idx].get("Close"))
    c_prev = _safe_float(df.iloc[idx - n].get("Close"))
    if c_now is None or c_prev is None or c_prev == 0:
        return None
    return (c_now - c_prev) / c_prev * 100.0


# ── public API ──────────────────────────────────────────────────────────

def build_regime_features(
    coded_df,
    peer_dfs: dict | None,
    target_date_str: str,
    *,
    final_test_cutoff: str = DEFAULT_FINAL_TEST_CUTOFF,
) -> dict[str, Any]:
    """Build the regime_features dict for ``scan_result["regime_features"]``.

    Pure function — no DB / CSV / network. Never raises. Missing data
    yields ``field=None`` + a warning string in ``warnings``.

    Returns:
        {
            "pos20": float | None,
            "avgo_minus_soxx_20d": float | None,
            "source": "scan_result",
            "as_of_date": "YYYY-MM-DD",
            "data_cutoff_date": "YYYY-MM-DD",  # == as_of_date (anti-lookahead)
            "warnings": [str, ...],
        }
    """
    warnings: list[str] = []
    as_of_date = (
        target_date_str.strip()[:10]
        if isinstance(target_date_str, str)
        else ""
    )
    pos20: float | None = None
    diff: float | None = None

    if not as_of_date:
        warnings.append("missing_as_of_date")
        return {
            "pos20": None,
            "avgo_minus_soxx_20d": None,
            "source": SCHEMA_SOURCE,
            "as_of_date": None,
            "data_cutoff_date": None,
            "warnings": warnings,
        }

    # 2026 final-test cutoff: defensive double-lock with simulator
    # (Step 2G-6B.4/6B.5 §10). We still compute the values (informational)
    # but flag the warning so downstream UI can refuse to display.
    if _is_within_final_test_range(as_of_date, final_test_cutoff):
        warnings.append("final_test_range_refusal")

    try:
        import pandas as pd  # local import — keeps module import cheap
        target_ts = pd.to_datetime(as_of_date)
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"target_date_parse_failed: {exc}")
        return {
            "pos20": None,
            "avgo_minus_soxx_20d": None,
            "source": SCHEMA_SOURCE,
            "as_of_date": as_of_date,
            "data_cutoff_date": as_of_date,
            "warnings": warnings,
        }

    # ── pos20 from AVGO coded df ────────────────────────────────────────
    if coded_df is None:
        warnings.append("missing_avgo_coded_df")
    else:
        pos20, pos_warn = _compute_pos20(coded_df, target_ts)
        if pos_warn is not None:
            warnings.append(f"pos20_skipped: {pos_warn}")

    # ── avgo_minus_soxx_20d from AVGO + SOXX returns ────────────────────
    soxx_df = (peer_dfs or {}).get("SOXX")
    if coded_df is None:
        warnings.append("missing_avgo_for_soxx_diff")
    elif soxx_df is None:
        warnings.append("missing_soxx_coded_df")
    else:
        avgo_ret = _compute_nday_return(coded_df, target_ts)
        soxx_ret = _compute_nday_return(soxx_df, target_ts)
        if avgo_ret is None:
            warnings.append("avgo_20d_return_unavailable")
        elif soxx_ret is None:
            warnings.append("soxx_20d_return_unavailable")
        else:
            diff = avgo_ret - soxx_ret

    return {
        "pos20": pos20,
        "avgo_minus_soxx_20d": diff,
        "source": SCHEMA_SOURCE,
        "as_of_date": as_of_date,
        "data_cutoff_date": as_of_date,  # anti-lookahead by construction
        "warnings": warnings,
    }
