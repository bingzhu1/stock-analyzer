# -*- coding: utf-8 -*-
"""
services/outcome_capture.py

Fetch the actual AVGO market result for a saved prediction's target_date
and write it to outcome_log.

Public API
----------
capture_actual_outcome(symbol, target_date) -> dict
    Standalone fetch+classify — no DB write, works without a prediction_id.

classify_actual_structure(actual_row, prev_close) -> dict
    Pure deterministic classifier — open/close/path labels.

capture_outcome(prediction_id) -> dict
    Original entry point: fetch + classify + persist to outcome_log.

Stored prediction field map (for downstream review modules)
-----------------------------------------------------------
Direct columns in prediction_log:
  symbol               → prediction["symbol"]
  analysis_date        → prediction["analysis_date"]
  prediction_for_date  → prediction["prediction_for_date"]
  confidence           → prediction["final_confidence"]
  created_at           → prediction["created_at"]
  source               → prediction["snapshot_id"]  (defaults to "—")

Nested inside predict_result_json (deserialise with json.loads):
  pred_open  → predict_result["open_tendency"]
  pred_close → predict_result["close_tendency"]
  pred_path  → predict_result["prediction_summary"]
  notes      → predict_result["notes"]

Access pattern for a review module:
    import json
    pr = json.loads(prediction["predict_result_json"])
    pred_open  = pr.get("open_tendency")
    pred_close = pr.get("close_tendency")
    pred_path  = pr.get("prediction_summary")
    notes      = pr.get("notes")
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

import pandas as pd
import yfinance as yf

from services.prediction_store import (
    get_outcome_for_prediction,
    get_prediction,
    save_outcome,
    update_prediction_status,
)

# Moves smaller than this threshold are treated as "flat" (no directional call)
_FLAT_THRESHOLD = 0.001  # 0.1%


def _compute_direction_correct(predicted_bias: str, close_change: float) -> int | None:
    """
    Returns:
        1   — prediction was directionally correct
        0   — prediction was directionally wrong
        None — prediction was neutral, or move was too small to judge
    """
    bias = predicted_bias.lower() if predicted_bias else "neutral"
    if bias not in {"bullish", "bearish"}:
        return None
    if abs(close_change) < _FLAT_THRESHOLD:
        return None  # move too small to declare right or wrong
    if close_change > 0:
        return 1 if bias == "bullish" else 0
    return 1 if bias == "bearish" else 0


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _build_scenario_match(prediction: dict[str, Any]) -> str | None:
    """
    Persist compact scan/match context with the outcome.

    Source: prediction_log.scan_result_json.historical_match_summary, generated
    by the hard-rule scan/match layer before the prediction was saved.
    """
    raw_scan = prediction.get("scan_result_json")
    if not raw_scan:
        return None

    try:
        scan_result = json.loads(str(raw_scan))
    except json.JSONDecodeError:
        return None

    if not isinstance(scan_result, dict):
        return None

    hist = scan_result.get("historical_match_summary")
    if not isinstance(hist, dict):
        return None

    exact_count = _safe_int(hist.get("exact_match_count"))
    near_count = _safe_int(hist.get("near_match_count"))
    top_context_score = _safe_float(hist.get("top_context_score"))
    dominant = hist.get("dominant_historical_outcome")

    scenario = {
        "source": "scan_result.historical_match_summary",
        "exact_match_count": exact_count,
        "near_match_count": near_count,
        "match_sample_size": (exact_count or 0) + (near_count or 0),
        "top_context_score": top_context_score,
        "dominant_historical_outcome": str(dominant) if dominant is not None else None,
        "scan_bias": scan_result.get("scan_bias"),
        "scan_confidence": scan_result.get("scan_confidence"),
    }
    return json.dumps(scenario, sort_keys=True)


def capture_outcome(prediction_id: str) -> dict[str, Any]:
    """
    Fetch actual AVGO OHLCV for the prediction's target_date and write to
    outcome_log.  If an outcome already exists for this prediction it is
    returned as-is (idempotent).

    Raises
    ------
    ValueError
        - prediction_id not found in DB
        - yfinance returned no data for the date range
        - target_date is not a trading day (market was closed)
    """
    existing = get_outcome_for_prediction(prediction_id)
    if existing:
        return existing

    prediction = get_prediction(prediction_id)
    if not prediction:
        raise ValueError(f"Prediction '{prediction_id}' not found in the database.")

    prediction_for_date: str = prediction["prediction_for_date"]  # "YYYY-MM-DD"
    predicted_bias: str = prediction["final_bias"]
    scenario_match = _build_scenario_match(prediction)

    # Fetch a 10-day window so we can safely get prev_close even after weekends
    dt = datetime.strptime(prediction_for_date, "%Y-%m-%d")
    fetch_start = (dt - timedelta(days=10)).strftime("%Y-%m-%d")
    fetch_end = (dt + timedelta(days=2)).strftime("%Y-%m-%d")

    ticker = yf.Ticker("AVGO")
    hist = ticker.history(start=fetch_start, end=fetch_end, interval="1d")

    if hist.empty:
        raise ValueError(
            f"yfinance returned no data for AVGO around {prediction_for_date}. "
            "Check your internet connection or try again later."
        )

    # Normalise index to plain date strings for reliable comparison
    hist = hist.reset_index()
    if "Datetime" in hist.columns:
        hist.rename(columns={"Datetime": "Date"}, inplace=True)
    hist["Date"] = pd.to_datetime(hist["Date"]).dt.strftime("%Y-%m-%d")

    target_rows = hist[hist["Date"] == prediction_for_date]
    if target_rows.empty:
        raise ValueError(
            f"{prediction_for_date} was not a trading day for AVGO "
            "(market holiday or weekend). Choose a valid trading date."
        )

    target_row = target_rows.iloc[0]
    prev_rows = hist[hist["Date"] < prediction_for_date]

    actual_prev_close: float | None = (
        float(prev_rows.iloc[-1]["Close"]) if not prev_rows.empty else None
    )
    actual_open  = float(target_row["Open"])
    actual_high  = float(target_row["High"])
    actual_low   = float(target_row["Low"])
    actual_close = float(target_row["Close"])

    close_change = (
        (actual_close - actual_prev_close) / actual_prev_close
        if actual_prev_close
        else 0.0
    )
    direction_correct = _compute_direction_correct(predicted_bias, close_change)

    save_outcome(
        prediction_id=prediction_id,
        prediction_for_date=prediction_for_date,
        actual_open=actual_open,
        actual_high=actual_high,
        actual_low=actual_low,
        actual_close=actual_close,
        actual_prev_close=actual_prev_close,  # None → SQL NULL when no prior trading day
        direction_correct=direction_correct,
        scenario_match=scenario_match,
    )
    update_prediction_status(prediction_id, "outcome_captured")

    return get_outcome_for_prediction(prediction_id)


# ─────────────────────────────────────────────────────────────────────────────
# Standalone fetch + classify (no prediction_id required)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_window(symbol: str, target_date: str) -> pd.DataFrame:
    """
    Fetch a 10-day window around target_date from yfinance and return a
    DataFrame with a plain string Date column (YYYY-MM-DD), sorted ascending.
    """
    dt = datetime.strptime(target_date, "%Y-%m-%d")
    fetch_start = (dt - timedelta(days=10)).strftime("%Y-%m-%d")
    fetch_end = (dt + timedelta(days=2)).strftime("%Y-%m-%d")

    ticker = yf.Ticker(symbol)
    hist = ticker.history(start=fetch_start, end=fetch_end, interval="1d")

    if hist.empty:
        raise ValueError(
            f"yfinance returned no data for {symbol} around {target_date}. "
            "Check your internet connection or try again later."
        )

    hist = hist.reset_index()
    if "Datetime" in hist.columns:
        hist.rename(columns={"Datetime": "Date"}, inplace=True)
    hist["Date"] = pd.to_datetime(hist["Date"]).dt.strftime("%Y-%m-%d")
    return hist.sort_values("Date").reset_index(drop=True)


def classify_actual_structure(actual_row: dict[str, Any], prev_close: float) -> dict[str, str]:
    """
    Deterministic open/close/path classifier for one trading day.

    Parameters
    ----------
    actual_row  : dict with at least "Open" and "Close" keys (floats)
    prev_close  : prior trading day's close price

    Returns
    -------
    {
        "open_label":  "高开" | "低开" | "平开",
        "close_label": "收涨" | "收跌" | "平收",
        "path_label":  one of the 9 canonical patterns below,
    }

    Path label matrix
    -----------------
    open \\ close  收涨      收跌      平收
    高开          高开高走  高开低走  高开震荡
    低开          低开高走  低开低走  低开震荡
    平开          平开走高  平开走低  平开震荡
    """
    open_price = float(actual_row["Open"])
    close_price = float(actual_row["Close"])

    open_chg = (open_price - prev_close) / prev_close
    close_chg = (close_price - prev_close) / prev_close

    if open_chg > _FLAT_THRESHOLD:
        open_label = "高开"
    elif open_chg < -_FLAT_THRESHOLD:
        open_label = "低开"
    else:
        open_label = "平开"

    if close_chg > _FLAT_THRESHOLD:
        close_label = "收涨"
    elif close_chg < -_FLAT_THRESHOLD:
        close_label = "收跌"
    else:
        close_label = "平收"

    _PATH: dict[tuple[str, str], str] = {
        ("高开", "收涨"): "高开高走",
        ("高开", "收跌"): "高开低走",
        ("高开", "平收"): "高开震荡",
        ("低开", "收涨"): "低开高走",
        ("低开", "收跌"): "低开低走",
        ("低开", "平收"): "低开震荡",
        ("平开", "收涨"): "平开走高",
        ("平开", "收跌"): "平开走低",
        ("平开", "平收"): "平开震荡",
    }
    path_label = _PATH[(open_label, close_label)]

    return {
        "open_label": open_label,
        "close_label": close_label,
        "path_label": path_label,
    }


def capture_actual_outcome(symbol: str, target_date: str) -> dict[str, Any]:
    """
    Fetch actual OHLCV for (symbol, target_date) and return a classified result.

    Does NOT require a prediction_id and does NOT write to the database.
    Use capture_outcome(prediction_id) when you need DB persistence.

    Returns
    -------
    {
        "symbol":             str,
        "target_date":        "YYYY-MM-DD",
        "actual_open":        float,
        "actual_high":        float,
        "actual_low":         float,
        "actual_close":       float,
        "actual_prev_close":  float,
        "actual_open_change": float,   # fractional ratio, e.g. 0.012 = +1.2%
        "actual_close_change":float,   # fractional ratio, convert ×100 before label_state()
        "open_label":         "高开" | "低开" | "平开",
        "close_label":        "收涨" | "收跌" | "平收",
        "path_label":         canonical path string,
    }

    Raises
    ------
    ValueError
        - target_date is not a trading day for symbol
        - yfinance returned no data for the requested window
        - No prior trading day exists in the fetched window
    """
    hist = _fetch_window(symbol, target_date)

    target_rows = hist[hist["Date"] == target_date]
    if target_rows.empty:
        raise ValueError(
            f"{target_date} was not a trading day for {symbol} "
            "(market holiday or weekend). Choose a valid trading date."
        )

    target_row = target_rows.iloc[0]
    prev_rows = hist[hist["Date"] < target_date]
    if prev_rows.empty:
        raise ValueError(
            f"No prior trading day found before {target_date} for {symbol} "
            "in the fetched window. Try a date further into the data history."
        )

    actual_prev_close = float(prev_rows.iloc[-1]["Close"])
    actual_open = float(target_row["Open"])
    actual_high = float(target_row["High"])
    actual_low = float(target_row["Low"])
    actual_close = float(target_row["Close"])

    open_change = (actual_open - actual_prev_close) / actual_prev_close
    close_change = (actual_close - actual_prev_close) / actual_prev_close

    classification = classify_actual_structure(
        {"Open": actual_open, "Close": actual_close},
        actual_prev_close,
    )

    return {
        "symbol": symbol,
        "target_date": target_date,
        "actual_open": actual_open,
        "actual_high": actual_high,
        "actual_low": actual_low,
        "actual_close": actual_close,
        "actual_prev_close": actual_prev_close,
        "actual_open_change": open_change,
        "actual_close_change": close_change,
        **classification,
    }
