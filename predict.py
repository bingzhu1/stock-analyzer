# -*- coding: utf-8 -*-
"""
predict.py - Lightweight Predict v2 layer for the AVGO analyzer.

Predict v2 builds an AVGO-only primary projection, applies peer adjustment,
then emits the final explainable directional judgment. It is rule-based manual
trading assistance, not an ML forecaster.
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
    path_risk: str
    peer_path_risk_adjustment: dict[str, Any]
    primary_projection: dict[str, Any]
    peer_adjustment: dict[str, Any]
    final_projection: dict[str, Any]


_CONF_LEVELS = ("low", "medium", "high")
_REINFORCING_ADJUSTMENTS = {"reinforce_bullish", "reinforce_bearish"}
_WEAKENING_ADJUSTMENTS = {"weaken_bullish", "weaken_bearish"}
_DIRECTIONAL_ADJUSTMENTS = _REINFORCING_ADJUSTMENTS | _WEAKENING_ADJUSTMENTS
_PEER_SYMBOLS = ("NVDA", "SOXX", "QQQ")
_PRIMARY_LOOKBACK_DAYS = 20
_GAP_THRESHOLD = 0.005
_VOLUME_EXPANDING_THRESHOLD = 1.10
_VOLUME_SHRINKING_THRESHOLD = 0.90

_OPEN_TENDENCY_TO_LABEL = {
    "gap_up_bias": "高开",
    "gap_down_bias": "低开",
    "flat_bias": "平开",
    "unclear": None,
}
_CLOSE_TENDENCY_TO_LABEL = {
    "close_strong": "收涨",
    "close_weak": "收跌",
    "range": "平收",
    "unclear": None,
}
_PATH_LABEL_MAP = {
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


def _bias_from_score(score: float) -> str:
    if score > 0.5:
        return "bullish"
    if score < -0.5:
        return "bearish"
    return "neutral"


def _confidence_from_score(score: float) -> str:
    abs_score = abs(score)
    if abs_score >= 2.0:
        return "high"
    if abs_score >= 1.0:
        return "medium"
    return "low"


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


def _pred_labels(open_tendency: str, close_tendency: str) -> dict[str, str | None]:
    pred_open = _OPEN_TENDENCY_TO_LABEL.get(open_tendency)
    pred_close = _CLOSE_TENDENCY_TO_LABEL.get(close_tendency)
    pred_path = _PATH_LABEL_MAP.get((pred_open, pred_close)) if pred_open and pred_close else None
    return {
        "pred_open": pred_open,
        "pred_path": pred_path,
        "pred_close": pred_close,
    }


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _recent_20_summary(rows: Any) -> dict[str, Any]:
    if not isinstance(rows, list):
        return {"sample_count": 0}

    clean_rows = [row for row in rows if isinstance(row, dict)]
    closes = [
        _as_float(row.get("Close"))
        for row in clean_rows
        if _as_float(row.get("Close")) is not None
    ]
    c_moves = [
        _as_float(row.get("C_move"))
        for row in clean_rows
        if _as_float(row.get("C_move")) is not None
    ]
    o_gaps = [
        _as_float(row.get("O_gap"))
        for row in clean_rows
        if _as_float(row.get("O_gap")) is not None
    ]
    v_ratios = [
        _as_float(row.get("V_ratio"))
        for row in clean_rows
        if _as_float(row.get("V_ratio")) is not None
    ]

    ret = None
    if len(closes) >= 2 and closes[0] not in (None, 0):
        ret = (closes[-1] - closes[0]) / closes[0]

    up_days = sum(1 for move in c_moves if move > 0)
    down_days = sum(1 for move in c_moves if move < 0)
    gap_up_days = sum(1 for gap in o_gaps if gap > 0.005)
    gap_down_days = sum(1 for gap in o_gaps if gap < -0.005)

    return {
        "sample_count": len(clean_rows),
        "first_date": clean_rows[0].get("Date") if clean_rows else None,
        "last_date": clean_rows[-1].get("Date") if clean_rows else None,
        "close_return": ret,
        "up_days": up_days,
        "down_days": down_days,
        "gap_up_days": gap_up_days,
        "gap_down_days": gap_down_days,
        "last_o_gap": _as_float(clean_rows[-1].get("O_gap")) if clean_rows else None,
        "last_c_move": _as_float(clean_rows[-1].get("C_move")) if clean_rows else None,
        "last_v_ratio": _as_float(clean_rows[-1].get("V_ratio")) if clean_rows else None,
        "avg_c_move": sum(c_moves) / len(c_moves) if c_moves else None,
        "avg_o_gap": sum(o_gaps) / len(o_gaps) if o_gaps else None,
        "avg_v_ratio": sum(v_ratios) / len(v_ratios) if v_ratios else None,
    }


def _gap_state_from_value(value: float | None) -> str:
    if value is None:
        return "unknown"
    if value > _GAP_THRESHOLD:
        return "gap_up"
    if value < -_GAP_THRESHOLD:
        return "gap_down"
    return "flat"


def _intraday_state_from_value(value: float | None) -> str:
    if value is None:
        return "unknown"
    if value > _GAP_THRESHOLD:
        return "high_go"
    if value < -_GAP_THRESHOLD:
        return "low_go"
    return "range"


def _volume_state_from_value(value: float | None) -> str:
    if value is None:
        return "unknown"
    if value > _VOLUME_EXPANDING_THRESHOLD:
        return "expanding"
    if value < _VOLUME_SHRINKING_THRESHOLD:
        return "shrinking"
    return "normal"


def _trend_state_from_recent_summary(recent_summary: dict[str, Any]) -> str:
    close_return = recent_summary.get("close_return")
    if isinstance(close_return, float):
        if close_return > 0.02:
            return "bullish"
        if close_return < -0.02:
            return "bearish"
    up_days = recent_summary.get("up_days", 0)
    down_days = recent_summary.get("down_days", 0)
    if up_days > down_days:
        return "bullish"
    if down_days > up_days:
        return "bearish"
    return "neutral"


def _primary_input_boundary(fallback_scan_states_used: bool) -> dict[str, Any]:
    return {
        "raw_window": "avgo_recent_20",
        "lookback_days": _PRIMARY_LOOKBACK_DAYS,
        "direct_recent_20_fields": [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
            "O_gap",
            "C_move",
            "V_ratio",
        ],
        "direct_recent_20_derived_features": [
            "last_o_gap",
            "last_c_move",
            "last_v_ratio",
            "close_return",
            "up_days",
            "down_days",
            "gap_up_days",
            "gap_down_days",
        ],
        "recent_20_direct_scan_states": [
            "avgo_gap_state",
            "avgo_intraday_state",
            "avgo_volume_state",
        ],
        "not_direct_recent_20_scan_states": [
            "avgo_price_state",
        ],
        "excluded_inputs": [
            "historical_match_summary",
            "relative_strength_summary",
            "relative_strength_same_day_summary",
            "confirmation_state",
            "scan_bias",
            "scan_confidence",
        ],
        "fallback_scan_states_used": fallback_scan_states_used,
    }


def _path_risk_from_confidence(confidence: str) -> str:
    confidence = _normalize_confidence(confidence)
    if confidence == "high":
        return "low"
    if confidence == "medium":
        return "medium"
    return "high"


def _adjust_path_risk(primary_risk: str, adjustment_direction: str, confirm_count: int, oppose_count: int) -> tuple[str, str, list[str]]:
    reasons: list[str] = []
    risk_order = {"low": 0, "medium": 1, "high": 2}
    score = risk_order.get(primary_risk, 1)
    risk_direction = "unchanged"

    if adjustment_direction == "reinforce":
        score = max(0, score - 1)
        risk_direction = "lower"
        reasons.append(f"{confirm_count} peers confirm primary direction")
    elif adjustment_direction == "weaken":
        score = min(2, score + 1)
        risk_direction = "higher"
        reasons.append(f"{oppose_count} peers oppose primary direction")
    elif confirm_count and oppose_count:
        score = min(2, score + 1)
        risk_direction = "higher"
        reasons.append("peer evidence is mixed across confirmation and opposition")

    labels = {0: "low", 1: "medium", 2: "high"}
    return labels[score], risk_direction, reasons


def _summarize(final_bias: str, final_confidence: str, adjustment: str) -> str:
    if final_bias == "unavailable":
        return "Prediction unavailable: Scan result is missing. Run Scan before Predict."
    if adjustment == "missing_research":
        return f"Prediction is {final_bias} with {final_confidence} confidence, led by Scan only."
    return (
        f"Prediction is {final_bias} with {final_confidence} confidence after combining "
        f"Scan with Research adjustment {adjustment}."
    )


def build_primary_projection(
    scan_result: dict[str, Any] | None,
    research_result: dict[str, Any] | None = None,
    symbol: str = "AVGO",
) -> dict[str, Any]:
    """
    Build the first-stage AVGO-only projection.

    This stage intentionally does not use peer relative-strength,
    confirmation_state, scan_bias, scan_confidence, or historical matches. It
    scores AVGO's recent-20 raw window and directly derived features into a
    baseline direction.
    """
    scan = scan_result or {}
    if not scan_result:
        return {
            "status": "unavailable",
            "source": "avgo_recent_20_scan_context",
            "symbol": symbol,
            "lookback_days": _PRIMARY_LOOKBACK_DAYS,
            "peer_inputs_used": False,
            "final_bias": "unavailable",
            "final_confidence": "low",
            "open_tendency": "unclear",
            "close_tendency": "unclear",
            "pred_open": None,
            "pred_path": None,
            "pred_close": None,
            "score": 0.0,
            "signals": [],
            "direct_features": {},
            "input_boundary": _primary_input_boundary(fallback_scan_states_used=False),
            "notes": "Scan result is missing; primary projection cannot be computed.",
        }

    recent_20 = scan.get("avgo_recent_20", [])
    recent_summary = _recent_20_summary(recent_20)
    fallback_scan_states_used = recent_summary.get("sample_count", 0) == 0

    if fallback_scan_states_used:
        gap_state = str(scan.get("avgo_gap_state", "unknown"))
        intraday_state = str(scan.get("avgo_intraday_state", "unknown"))
        volume_state = str(scan.get("avgo_volume_state", "unknown"))
        trend_state = str(scan.get("avgo_price_state", "unknown"))
    else:
        gap_state = _gap_state_from_value(recent_summary.get("last_o_gap"))
        intraday_state = _intraday_state_from_value(recent_summary.get("last_c_move"))
        volume_state = _volume_state_from_value(recent_summary.get("last_v_ratio"))
        trend_state = _trend_state_from_recent_summary(recent_summary)

    score = 0.0
    signals: list[str] = []

    if gap_state == "gap_up":
        score += 1.0
        signals.append("avgo_gap_state=gap_up")
    elif gap_state == "gap_down":
        score -= 1.0
        signals.append("avgo_gap_state=gap_down")
    elif gap_state == "flat":
        signals.append("avgo_gap_state=flat")

    if intraday_state == "high_go":
        score += 1.0
        signals.append("avgo_intraday_state=high_go")
    elif intraday_state == "low_go":
        score -= 1.0
        signals.append("avgo_intraday_state=low_go")
    elif intraday_state == "range":
        signals.append("avgo_intraday_state=range")

    if volume_state == "expanding":
        score += 0.5
        signals.append("avgo_volume_state=expanding")
    elif volume_state == "shrinking":
        score -= 0.5
        signals.append("avgo_volume_state=shrinking")
    elif volume_state == "normal":
        signals.append("avgo_volume_state=normal")

    if trend_state == "bullish":
        score += 1.0
        signals.append("avgo_recent_20_trend=bullish")
    elif trend_state == "bearish":
        score -= 1.0
        signals.append("avgo_recent_20_trend=bearish")
    elif trend_state == "neutral":
        signals.append("avgo_recent_20_trend=neutral")

    close_return = recent_summary.get("close_return")
    if isinstance(close_return, float):
        if close_return > 0.02:
            score += 0.5
            signals.append("avgo_recent_20_return=positive")
        elif close_return < -0.02:
            score -= 0.5
            signals.append("avgo_recent_20_return=negative")

    if recent_summary.get("up_days", 0) > recent_summary.get("down_days", 0):
        score += 0.25
        signals.append("avgo_recent_20_up_days_majority")
    elif recent_summary.get("down_days", 0) > recent_summary.get("up_days", 0):
        score -= 0.25
        signals.append("avgo_recent_20_down_days_majority")

    final_bias = _bias_from_score(score)
    final_confidence = _confidence_from_score(score)
    open_tendency = {
        "gap_up": "gap_up_bias",
        "gap_down": "gap_down_bias",
        "flat": "flat_bias",
    }.get(gap_state, "unclear")
    close_tendency = {
        "high_go": "close_strong",
        "low_go": "close_weak",
        "range": "range",
    }.get(intraday_state, "unclear")
    labels = _pred_labels(open_tendency, close_tendency)

    return {
        "status": "computed",
        "source": "avgo_recent_20_scan_context",
        "symbol": str(scan.get("symbol", symbol)),
        "lookback_days": _PRIMARY_LOOKBACK_DAYS,
        "peer_inputs_used": False,
        "final_bias": final_bias,
        "final_confidence": final_confidence,
        "open_tendency": open_tendency,
        "close_tendency": close_tendency,
        **labels,
        "score": score,
        "signals": signals,
        "direct_features": {
            "gap_state": gap_state,
            "intraday_state": intraday_state,
            "volume_state": volume_state,
            "recent_20_trend_state": trend_state,
        },
        "recent_20_summary": recent_summary,
        "input_boundary": _primary_input_boundary(fallback_scan_states_used),
        "notes": (
            "Primary projection uses AVGO recent-20 raw window and directly "
            "derived AVGO features; historical matches and peer inputs are excluded."
        ),
    }


def _peer_layer_vote(primary_bias: str, relative_strength: str) -> str:
    if relative_strength == "unavailable":
        return "unavailable"
    if primary_bias == "bullish":
        if relative_strength == "stronger":
            return "confirm"
        if relative_strength == "weaker":
            return "oppose"
    elif primary_bias == "bearish":
        if relative_strength == "weaker":
            return "confirm"
        if relative_strength == "stronger":
            return "oppose"
    return "mixed"


def _combine_peer_votes(votes: set[str]) -> str:
    directional = votes - {"unavailable"}
    if not directional:
        return "unavailable"
    if "confirm" in directional and "oppose" in directional:
        return "mixed"
    if "confirm" in directional:
        return "confirm"
    if "oppose" in directional:
        return "oppose"
    return "mixed"


def apply_peer_adjustment(
    primary_projection: dict[str, Any],
    scan_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Use NVDA / SOXX / QQQ relative strength to adjust the primary view."""
    scan = scan_result or {}
    primary_bias = str(primary_projection.get("final_bias", "neutral"))
    primary_confidence = _normalize_confidence(str(primary_projection.get("final_confidence", "low")))
    rs_5d = scan.get("relative_strength_summary") or {}
    rs_same_day = scan.get("relative_strength_same_day_summary") or {}
    peer_raw_features = scan.get("peer_relative_strength_features") or {}
    if not isinstance(peer_raw_features, dict):
        peer_raw_features = {}

    adjustments: list[dict[str, Any]] = []
    confirm_count = 0
    oppose_count = 0

    for peer in _PEER_SYMBOLS:
        key = f"vs_{peer.lower()}"
        five_day = str(rs_5d.get(key, "unavailable"))
        same_day = str(rs_same_day.get(key, "unavailable"))
        vote = _combine_peer_votes({
            _peer_layer_vote(primary_bias, five_day),
            _peer_layer_vote(primary_bias, same_day),
        })
        if vote == "confirm":
            confirm_count += 1
        elif vote == "oppose":
            oppose_count += 1
        adjustments.append({
            "peer": peer,
            "five_day_relative_strength": five_day,
            "same_day_relative_strength": same_day,
            "vote": vote,
        })

    adjusted_bias = primary_bias
    adjusted_confidence = primary_confidence
    adjustment_direction = "neutral"

    if primary_bias in {"bullish", "bearish"}:
        if confirm_count >= 2:
            adjustment_direction = "reinforce"
            adjusted_confidence = _raise_confidence(primary_confidence)
        elif oppose_count >= 2:
            adjustment_direction = "weaken"
            adjusted_confidence = _lower_confidence(primary_confidence)
            if primary_confidence == "low":
                adjusted_bias = "neutral"
    else:
        adjustment_direction = "neutral_primary"

    primary_path_risk = _path_risk_from_confidence(primary_confidence)
    adjusted_path_risk, path_risk_direction, path_risk_reasons = _adjust_path_risk(
        primary_path_risk,
        adjustment_direction,
        confirm_count,
        oppose_count,
    )

    return {
        "status": "computed",
        "source": "peer_relative_strength",
        "data_source": {
            "current": "scanner_relative_strength_labels",
            "label_inputs": [
                "relative_strength_summary",
                "relative_strength_same_day_summary",
            ],
            "raw_feature_inputs_ready": bool(peer_raw_features),
            "future_raw_feature_fields": [
                "peer_5d_return",
                "peer_same_day_move",
                "avgo_minus_peer_5d_return",
                "avgo_minus_peer_same_day_move",
            ],
        },
        "peer_raw_features": peer_raw_features,
        "peer_symbols": list(_PEER_SYMBOLS),
        "adjustments": adjustments,
        "confirm_count": confirm_count,
        "oppose_count": oppose_count,
        "adjustment_direction": adjustment_direction,
        "primary_bias": primary_bias,
        "primary_confidence": primary_confidence,
        "adjusted_bias": adjusted_bias,
        "adjusted_confidence": adjusted_confidence,
        "path_risk_adjustment": {
            "status": "computed",
            "before": primary_path_risk,
            "after": adjusted_path_risk,
            "risk_direction": path_risk_direction,
            "reasons": path_risk_reasons,
            "path_label_changed": False,
        },
        "notes": "Peer adjustment uses NVDA / SOXX / QQQ relative-strength confirmation.",
    }


def _apply_research_adjustment(
    bias: str,
    confidence: str,
    scan_bias: str,
    research_result: dict[str, Any] | None,
    supporting_factors: list[str],
    conflicting_factors: list[str],
    note_parts: list[str],
) -> tuple[str, str]:
    research = research_result or {}
    adjustment = str(research.get("research_bias_adjustment", "missing_research"))
    research_sentiment = str(research.get("sentiment_bias", "missing"))

    final_bias = bias if bias in {"bullish", "bearish", "neutral"} else "neutral"
    final_confidence = _normalize_confidence(confidence)

    if adjustment == "missing_research":
        supporting_factors.append("research_missing_scan_led")
    elif adjustment == "reinforce_bullish" and final_bias == "bullish":
        final_confidence = _raise_confidence(final_confidence)
        supporting_factors.append("research_reinforces_bullish")
    elif adjustment == "reinforce_bearish" and final_bias == "bearish":
        final_confidence = _raise_confidence(final_confidence)
        supporting_factors.append("research_reinforces_bearish")
    elif adjustment == "weaken_bullish" and final_bias == "bullish":
        conflicting_factors.append("research_weakens_bullish")
        if final_confidence == "high":
            final_confidence = "medium"
        else:
            final_bias = "neutral"
            final_confidence = "low"
    elif adjustment == "weaken_bearish" and final_bias == "bearish":
        conflicting_factors.append("research_weakens_bearish")
        if final_confidence == "high":
            final_confidence = "medium"
        else:
            final_bias = "neutral"
            final_confidence = "low"
    elif final_bias == "neutral" and adjustment in _DIRECTIONAL_ADJUSTMENTS:
        final_confidence = "low"
        conflicting_factors.append("neutral_primary_research_direction_not_applied")
        note_parts.append(
            "Research was directional, but it did not override a neutral primary projection."
        )
    else:
        if research_result is not None:
            final_confidence = _lower_confidence(final_confidence) if scan_bias != "neutral" else "low"
            supporting_factors.append(f"research_sentiment={research_sentiment}")
        else:
            supporting_factors.append("research_missing_scan_led")

    if research.get("catalyst_detected") is True:
        if adjustment in _REINFORCING_ADJUSTMENTS:
            supporting_factors.append("research_catalyst_detected")
        elif adjustment in _WEAKENING_ADJUSTMENTS:
            conflicting_factors.append("research_catalyst_conflicts_with_projection")
        elif research_result is not None:
            note_parts.append("Research detected a catalyst, but it was not classified as supporting or conflicting.")
    elif research.get("catalyst_detected") is False and research_result is not None:
        conflicting_factors.append("research_no_clear_catalyst")

    return final_bias, final_confidence


def build_final_projection(
    primary_projection: dict[str, Any],
    peer_adjustment: dict[str, Any],
    research_result: dict[str, Any] | None = None,
    scan_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the final prediction result from primary + peer adjustment."""
    scan = scan_result or {}
    research = research_result or {}
    adjustment = str(research.get("research_bias_adjustment", "missing_research"))
    scan_bias = str(scan.get("scan_bias", primary_projection.get("final_bias", "neutral")))
    scan_confidence = _normalize_confidence(str(scan.get("scan_confidence", primary_projection.get("final_confidence", "low"))))

    if primary_projection.get("final_bias") == "unavailable":
        return {
            "status": "unavailable",
            "source": "primary_projection_plus_peer_adjustment",
            "symbol": str(primary_projection.get("symbol", scan.get("symbol", "AVGO"))),
            "final_bias": "unavailable",
            "final_confidence": "low",
            "open_tendency": "unclear",
            "close_tendency": "unclear",
            "pred_open": None,
            "pred_path": None,
            "pred_close": None,
            "research_bias_adjustment": adjustment,
            "scan_bias": scan_bias,
            "scan_confidence": scan_confidence,
            "path_risk": "high",
            "peer_path_risk_adjustment": {
                "status": "unavailable",
                "before": "high",
                "after": "high",
                "risk_direction": "unchanged",
                "reasons": ["primary_projection_unavailable"],
                "path_label_changed": False,
            },
            "prediction_summary": _summarize("unavailable", "low", adjustment),
            "supporting_factors": [],
            "conflicting_factors": ["primary_projection_unavailable"],
            "notes": "Primary projection is unavailable, so final projection is unavailable.",
        }

    supporting_factors: list[str] = [
        f"primary_bias={primary_projection.get('final_bias', 'neutral')}",
        f"primary_confidence={primary_projection.get('final_confidence', 'low')}",
        f"peer_adjustment={peer_adjustment.get('adjustment_direction', 'neutral')}",
    ]
    conflicting_factors: list[str] = []
    note_parts: list[str] = [
        "Predict v2 uses AVGO-only primary projection, then NVDA/SOXX/QQQ peer adjustment; "
        "it remains rule-based and is not an automated trading signal."
    ]

    peer_direction = str(peer_adjustment.get("adjustment_direction", "neutral"))
    if peer_direction == "reinforce":
        supporting_factors.append("peer_confirmation=reinforce")
    elif peer_direction == "weaken":
        conflicting_factors.append("peer_confirmation=weaken")
    elif peer_direction == "neutral_primary":
        conflicting_factors.append("peer_adjustment_neutral_primary")

    path_risk_adjustment = peer_adjustment.get("path_risk_adjustment")
    if not isinstance(path_risk_adjustment, dict):
        primary_path_risk = _path_risk_from_confidence(str(primary_projection.get("final_confidence", "low")))
        path_risk_adjustment = {
            "status": "computed",
            "before": primary_path_risk,
            "after": primary_path_risk,
            "risk_direction": "unchanged",
            "reasons": [],
            "path_label_changed": False,
        }
    path_risk = str(path_risk_adjustment.get("after", "medium"))
    path_risk_direction = str(path_risk_adjustment.get("risk_direction", "unchanged"))
    if path_risk_direction == "higher":
        conflicting_factors.append(f"peer_path_risk={path_risk}")
        note_parts.append(
            "Peer layer raises path risk; final path label is kept but should be treated with caution."
        )
    elif path_risk_direction == "lower":
        supporting_factors.append(f"peer_path_risk={path_risk}")

    final_bias = str(peer_adjustment.get("adjusted_bias", primary_projection.get("final_bias", "neutral")))
    final_confidence = _normalize_confidence(str(peer_adjustment.get(
        "adjusted_confidence",
        primary_projection.get("final_confidence", "low"),
    )))

    final_bias, final_confidence = _apply_research_adjustment(
        final_bias,
        final_confidence,
        scan_bias,
        research_result,
        supporting_factors,
        conflicting_factors,
        note_parts,
    )

    open_tendency = str(primary_projection.get("open_tendency", "unclear"))
    close_tendency = str(primary_projection.get("close_tendency", "unclear"))
    labels = _pred_labels(open_tendency, close_tendency)

    return {
        "status": "computed",
        "source": "primary_projection_plus_peer_adjustment",
        "symbol": str(primary_projection.get("symbol", scan.get("symbol", "AVGO"))),
        "final_bias": final_bias,
        "final_confidence": final_confidence,
        "open_tendency": open_tendency,
        "close_tendency": close_tendency,
        **labels,
        "research_bias_adjustment": adjustment,
        "scan_bias": scan_bias,
        "scan_confidence": scan_confidence,
        "path_risk": path_risk,
        "peer_path_risk_adjustment": path_risk_adjustment,
        "prediction_summary": _summarize(final_bias, final_confidence, adjustment),
        "supporting_factors": supporting_factors,
        "conflicting_factors": conflicting_factors,
        "notes": " ".join(note_parts),
    }


def _missing_scan_result(research_result: dict[str, Any] | None, symbol: str) -> PredictResult:
    research = research_result or {}
    adjustment = str(research.get("research_bias_adjustment", "missing_research"))
    primary_projection = build_primary_projection(None, research_result=research_result, symbol=symbol)
    peer_adjustment = apply_peer_adjustment(primary_projection, None)
    final_projection = build_final_projection(primary_projection, peer_adjustment, research_result, None)
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
        "path_risk": "high",
        "peer_path_risk_adjustment": final_projection.get("peer_path_risk_adjustment", {}),
        "notes": (
            "Scan is missing, so Predict cannot produce a normal directional judgment. "
            "Run Scan first, then rerun Predict with optional Research context."
        ),
        "primary_projection": primary_projection,
        "peer_adjustment": peer_adjustment,
        "final_projection": final_projection,
    }


_CONFIDENCE_ORDER = ["low", "medium", "high"]


def _apply_briefing_caution(result: dict, briefing: dict) -> dict:
    """Lower final_confidence by one step when caution_level is high."""
    result = dict(result)
    caution_level = briefing.get("caution_level", "none")
    has_data = briefing.get("has_data", False)

    if caution_level == "high" and has_data:
        current = result["final_confidence"]
        if current in _CONFIDENCE_ORDER:
            idx = _CONFIDENCE_ORDER.index(current)
            if idx > 0:
                result["final_confidence"] = _CONFIDENCE_ORDER[idx - 1]
                result["briefing_caution_applied"] = True
                result["briefing_caution_reason"] = (
                    f"历史准确率 {briefing.get('overall_accuracy', 0.0):.0%}，"
                    f"基于 {briefing.get('record_count', 0)} 条复盘记录，"
                    f"信心由 {current} 下调一档"
                )
            else:
                result["briefing_caution_applied"] = False
                result["briefing_caution_reason"] = (
                    f"历史风险高但信心已在最低档（{current}），未继续下调"
                )
        else:
            result["briefing_caution_applied"] = False
            result["briefing_caution_reason"] = None
    elif caution_level == "medium" and has_data:
        result["briefing_caution_applied"] = False
        result["briefing_caution_reason"] = (
            f"历史准确率中等（{briefing.get('overall_accuracy', 0.0):.0%}），维持当前信心并标注风险"
        )
    else:
        result["briefing_caution_applied"] = False
        result["briefing_caution_reason"] = None

    return result


def run_predict(
    scan_result: dict[str, Any] | None,
    research_result: dict[str, Any] | None = None,
    symbol: str = "AVGO",
    pre_briefing: dict | None = None,
) -> PredictResult:
    """Run the v2 two-step projection chain and keep the old result shape."""
    if not scan_result:
        return _missing_scan_result(research_result, symbol)

    scan = scan_result or {}
    research = research_result or {}
    primary_projection = build_primary_projection(scan, research_result=research_result, symbol=symbol)
    peer_adjustment = apply_peer_adjustment(primary_projection, scan)
    final_projection = build_final_projection(
        primary_projection,
        peer_adjustment,
        research_result=research_result,
        scan_result=scan,
    )

    scan_bias = str(final_projection.get("scan_bias", scan.get("scan_bias", "neutral")))
    scan_confidence = _normalize_confidence(str(final_projection.get("scan_confidence", scan.get("scan_confidence", "low"))))
    adjustment = str(research.get("research_bias_adjustment", "missing_research"))
    final_bias = str(final_projection.get("final_bias", "neutral"))
    final_confidence = _normalize_confidence(str(final_projection.get("final_confidence", "low")))
    supporting_factors = list(final_projection.get("supporting_factors", []))
    conflicting_factors = list(final_projection.get("conflicting_factors", []))
    prediction_summary = str(final_projection.get("prediction_summary", _summarize(final_bias, final_confidence, adjustment)))
    path_risk = str(final_projection.get("path_risk", "medium"))
    peer_path_risk_adjustment = final_projection.get("peer_path_risk_adjustment")
    if not isinstance(peer_path_risk_adjustment, dict):
        peer_path_risk_adjustment = {}
    notes = str(final_projection.get("notes", ""))

    result = {
        "symbol": str(final_projection.get("symbol", scan.get("symbol", symbol))),
        "predict_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "scan_bias": scan_bias,
        "scan_confidence": scan_confidence,
        "research_bias_adjustment": adjustment,
        "final_bias": final_bias,
        "final_confidence": final_confidence,
        "open_tendency": str(final_projection.get("open_tendency", "unclear")),
        "close_tendency": str(final_projection.get("close_tendency", "unclear")),
        "pred_open": final_projection.get("pred_open"),
        "pred_path": final_projection.get("pred_path"),
        "pred_close": final_projection.get("pred_close"),
        "prediction_summary": prediction_summary,
        "supporting_factors": supporting_factors,
        "conflicting_factors": conflicting_factors,
        "path_risk": path_risk,
        "peer_path_risk_adjustment": peer_path_risk_adjustment,
        "notes": notes,
        "primary_projection": primary_projection,
        "peer_adjustment": peer_adjustment,
        "final_projection": final_projection,
        "briefing_caution_applied": False,
        "briefing_caution_reason": None,
    }
    if pre_briefing and pre_briefing.get("has_data"):
        result = _apply_briefing_caution(result, pre_briefing)
    return result
