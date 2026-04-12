# -*- coding: utf-8 -*-
"""
services/outcome_capture.py

Fetch the actual AVGO market result for a saved prediction's target_date
and write it to outcome_log.

Entry point: capture_outcome(prediction_id) -> dict
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
