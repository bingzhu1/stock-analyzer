# -*- coding: utf-8 -*-
"""
predict.py - Lightweight Predict v1 layer for the AVGO analyzer.

Predict v1 synthesizes Scan + optional Research into one explainable directional
judgment. It is rule-based manual trading assistance, not an ML forecaster.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, TypedDict


class PredictResult(TypedDict):
    symbol: str
    predict_timestamp: str
    scan_bias: str
    scan_confidence: str
    research_bias_adjustment: str
    final_bias: str
    final_confidence: str
    open_tendency: str
    close_tendency: str
    prediction_summary: str
    supporting_factors: list[str]
    conflicting_factors: list[str]
    notes: str


_CONF_LEVELS = ("low", "medium", "high")
_REINFORCING_ADJUSTMENTS = {"reinforce_bullish", "reinforce_bearish"}
_WEAKENING_ADJUSTMENTS = {"weaken_bullish", "weaken_bearish"}
_DIRECTIONAL_ADJUSTMENTS = _REINFORCING_ADJUSTMENTS | _WEAKENING_ADJUSTMENTS


def _raise_confidence(confidence: str) -> str:
    if confidence == "low":
        return "medium"
    if confidence == "medium":
        return "high"
    return "high"


def _lower_confidence(confidence: str) -> str:
    if confidence == "high":
        return "medium"
    return "low"


def _normalize_confidence(confidence: str) -> str:
    return confidence if confidence in _CONF_LEVELS else "low"


def _open_tendency(scan_result: dict[str, Any]) -> str:
    gap_state = str(scan_result.get("avgo_gap_state", "unknown"))
    if gap_state == "gap_up":
        return "gap_up_bias"
    if gap_state == "gap_down":
        return "gap_down_bias"
    if gap_state == "flat":
        return "flat_bias"
    return "unclear"


def _close_tendency(scan_result: dict[str, Any]) -> str:
    intraday_state = str(scan_result.get("avgo_intraday_state", "unknown"))
    if intraday_state == "high_go":
        return "close_strong"
    if intraday_state == "low_go":
        return "close_weak"
    if intraday_state == "range":
        return "range"
    return "unclear"


def _summarize(final_bias: str, final_confidence: str, adjustment: str) -> str:
    if final_bias == "unavailable":
        return "Prediction unavailable: Scan result is missing. Run Scan before Predict."
    if adjustment == "missing_research":
        return f"Prediction is {final_bias} with {final_confidence} confidence, led by Scan only."
    return (
        f"Prediction is {final_bias} with {final_confidence} confidence after combining "
        f"Scan with Research adjustment {adjustment}."
    )


def _missing_scan_result(research_result: dict[str, Any] | None, symbol: str) -> PredictResult:
    research = research_result or {}
    adjustment = str(research.get("research_bias_adjustment", "missing_research"))
    return {
        "symbol": symbol,
        "predict_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "scan_bias": "missing",
        "scan_confidence": "low",
        "research_bias_adjustment": adjustment,
        "final_bias": "unavailable",
        "final_confidence": "low",
        "open_tendency": "unclear",
        "close_tendency": "unclear",
        "prediction_summary": _summarize("unavailable", "low", adjustment),
        "supporting_factors": [],
        "conflicting_factors": ["scan_result_missing"],
        "notes": (
            "Scan is missing, so Predict cannot produce a normal directional judgment. "
            "Run Scan first, then rerun Predict with optional Research context."
        ),
    }


def run_predict(
    scan_result: dict[str, Any] | None,
    research_result: dict[str, Any] | None = None,
    symbol: str = "AVGO",
) -> PredictResult:
    """Combine Scan and optional Research into a final PredictResult."""
    if not scan_result:
        return _missing_scan_result(research_result, symbol)

    scan = scan_result or {}
    research = research_result or {}
    scan_bias = str(scan.get("scan_bias", "neutral"))
    scan_confidence = _normalize_confidence(str(scan.get("scan_confidence", "low")))
    adjustment = str(research.get("research_bias_adjustment", "missing_research"))
    research_sentiment = str(research.get("sentiment_bias", "missing"))

    final_bias = scan_bias if scan_bias in {"bullish", "bearish", "neutral"} else "neutral"
    final_confidence = scan_confidence
    note_parts: list[str] = [
        "Predict v1 is rule-based and combines Scan direction with optional Research context; "
        "it is not an automated trading signal."
    ]
    supporting_factors: list[str] = [
        f"scan_bias={scan_bias}",
        f"scan_confidence={scan_confidence}",
    ]
    conflicting_factors: list[str] = []

    if adjustment == "missing_research":
        supporting_factors.append("research_missing_scan_led")
    elif adjustment == "reinforce_bullish" and scan_bias == "bullish":
        final_bias = "bullish"
        final_confidence = _raise_confidence(scan_confidence)
        supporting_factors.append("research_reinforces_bullish")
    elif adjustment == "reinforce_bearish" and scan_bias == "bearish":
        final_bias = "bearish"
        final_confidence = _raise_confidence(scan_confidence)
        supporting_factors.append("research_reinforces_bearish")
    elif adjustment == "weaken_bullish" and scan_bias == "bullish":
        conflicting_factors.append("research_weakens_bullish")
        if scan_confidence == "high":
            final_bias = "bullish"
            final_confidence = "medium"
        else:
            final_bias = "neutral"
            final_confidence = "low"
    elif adjustment == "weaken_bearish" and scan_bias == "bearish":
        conflicting_factors.append("research_weakens_bearish")
        if scan_confidence == "high":
            final_bias = "bearish"
            final_confidence = "medium"
        else:
            final_bias = "neutral"
            final_confidence = "low"
    elif scan_bias == "neutral" and adjustment in _DIRECTIONAL_ADJUSTMENTS:
        final_bias = "neutral"
        final_confidence = "low"
        conflicting_factors.append("neutral_scan_research_direction_not_applied")
        note_parts.append(
            "Research was directional, but it did not override a neutral Scan in Predict v1."
        )
    else:
        if research_result is not None:
            final_confidence = _lower_confidence(scan_confidence) if scan_bias != "neutral" else "low"
            supporting_factors.append(f"research_sentiment={research_sentiment}")
        else:
            supporting_factors.append("research_missing_scan_led")

    if scan.get("confirmation_state") == "confirmed":
        supporting_factors.append("scan_confirmation=confirmed")
    elif scan.get("confirmation_state") == "diverging":
        conflicting_factors.append("scan_confirmation=diverging")

    if research.get("catalyst_detected") is True:
        if adjustment in _REINFORCING_ADJUSTMENTS:
            supporting_factors.append("research_catalyst_detected")
        elif adjustment in _WEAKENING_ADJUSTMENTS:
            conflicting_factors.append("research_catalyst_conflicts_with_scan")
        elif research_result is not None:
            note_parts.append("Research detected a catalyst, but it was not classified as supporting or conflicting.")
    elif research.get("catalyst_detected") is False and research_result is not None:
        conflicting_factors.append("research_no_clear_catalyst")

    prediction_summary = _summarize(final_bias, final_confidence, adjustment)
    notes = " ".join(note_parts)

    return {
        "symbol": str(scan.get("symbol", symbol)),
        "predict_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "scan_bias": scan_bias,
        "scan_confidence": scan_confidence,
        "research_bias_adjustment": adjustment,
        "final_bias": final_bias,
        "final_confidence": final_confidence,
        "open_tendency": _open_tendency(scan),
        "close_tendency": _close_tendency(scan),
        "prediction_summary": prediction_summary,
        "supporting_factors": supporting_factors,
        "conflicting_factors": conflicting_factors,
        "notes": notes,
    }
