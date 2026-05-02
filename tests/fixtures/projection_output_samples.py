"""Realistic-shape fixtures for projection_output adapter compatibility tests.

These mirror the actual ``scanner.run_scan`` and ``predict.run_predict`` output
dicts (Step 1C adapter spec source). Values are placeholders / fakes; no real
market data. Use these to lock the adapter against shape regressions.
"""
from __future__ import annotations

from typing import Any


# ── scan_result shape (mirrors scanner.run_scan return) ───────────────────────

def realistic_scan_result() -> dict[str, Any]:
    """Mirror of ``scanner.run_scan(...)`` output shape with placeholder values."""
    recent_20 = [
        {
            "Date": f"2026-03-{i:02d}",
            "Open": 95.0 + i * 0.3,
            "High": 96.0 + i * 0.3,
            "Low": 94.0 + i * 0.3,
            "Close": 95.5 + i * 0.3,
            "Volume": 1_000_000 + i * 5_000,
        }
        for i in range(1, 21)
    ]
    return {
        "symbol": "AVGO",
        "scan_timestamp": "2026-04-09T16:00:00",
        "scan_phase": "daily",
        "scan_phase_note": "Daily close-based scan using daily OHLCV features.",
        "avgo_price_state": "整理",
        "avgo_gap_state": "flat",
        "avgo_intraday_state": "high_go",
        "avgo_volume_state": "expanding",
        "avgo_pattern_code": "32233",
        "avgo_recent_20": recent_20,
        "historical_match_summary": {"sample_count": 42, "win_rate": 0.55},
        "relative_strength_summary": {
            "NVDA": {"avgo_5d_return": 1.0, "peer_5d_return": 0.5, "relative_strength": "stronger"},
            "SOXX": {"avgo_5d_return": 1.0, "peer_5d_return": 1.0, "relative_strength": "neutral"},
            "QQQ":  {"avgo_5d_return": 1.0, "peer_5d_return": 1.5, "relative_strength": "weaker"},
        },
        "relative_strength_5d_summary": {
            "NVDA": {"relative_strength": "stronger"},
            "SOXX": {"relative_strength": "neutral"},
            "QQQ":  {"relative_strength": "weaker"},
        },
        "relative_strength_same_day_summary": {
            "NVDA": {"relative_strength": "neutral"},
            "SOXX": {"relative_strength": "neutral"},
            "QQQ":  {"relative_strength": "neutral"},
        },
        "confirmation_state": "mixed",
        "scan_bias": "bullish",
        "scan_confidence": "medium",
        "notes": ["<placeholder note>"],
    }


# ── predict_result shape (mirrors predict.run_predict return) ─────────────────

def realistic_predict_result(
    *,
    final_bias: str = "bullish",
    final_confidence: str = "high",
    primary_confidence: str = "medium",
    confirm_count: int = 2,
    oppose_count: int = 0,
    adjustment_direction: str = "reinforce",
    pred_open: str | None = "高开",
    pred_path: str | None = "高开高走",
    pred_close: str | None = "收涨",
) -> dict[str, Any]:
    """Mirror of ``predict.run_predict(...)`` output shape with placeholder values.

    Tunable knobs cover the most common variations the adapter must absorb.
    """
    primary_projection = {
        "symbol": "AVGO",
        "status": "computed",
        "final_bias": final_bias,
        "final_confidence": primary_confidence,
        "open_tendency": "gap_up_bias",
        "close_tendency": "close_strong",
        "pred_open": pred_open,
        "pred_close": pred_close,
        "historical_match_summary": {"sample_count": 27, "win_rate": 0.55},
        "supporting_factors": ["primary_bias=" + final_bias],
        "conflicting_factors": [],
    }
    peer_adjustment = {
        "status": "computed",
        "source": "peer_relative_strength",
        "peer_symbols": ["NVDA", "SOXX", "QQQ"],
        "adjustments": [],
        "confirm_count": confirm_count,
        "oppose_count": oppose_count,
        "adjustment_direction": adjustment_direction,
        "primary_bias": final_bias,
        "primary_confidence": primary_confidence,
        "adjusted_bias": final_bias,
        "adjusted_confidence": final_confidence,
        "path_risk_adjustment": {
            "status": "computed",
            "before": "medium",
            "after": "low" if adjustment_direction == "reinforce" else "medium",
            "risk_direction": "lower" if adjustment_direction == "reinforce" else "unchanged",
            "reasons": [],
            "path_label_changed": False,
        },
        "notes": "Peer adjustment uses NVDA / SOXX / QQQ relative-strength confirmation.",
    }
    final_projection = {
        "status": "computed",
        "source": "primary_projection_plus_peer_adjustment",
        "symbol": "AVGO",
        "final_bias": final_bias,
        "final_confidence": final_confidence,
        "open_tendency": "gap_up_bias",
        "close_tendency": "close_strong",
        "pred_open": pred_open,
        "pred_path": pred_path,
        "pred_close": pred_close,
        "research_bias_adjustment": "confirms_bias",
        "scan_bias": "bullish",
        "scan_confidence": "medium",
        "path_risk": "low",
        "peer_path_risk_adjustment": peer_adjustment["path_risk_adjustment"],
        "prediction_summary": "<placeholder final summary>",
        "supporting_factors": ["primary_bias=" + final_bias, "peer_confirmation=reinforce"],
        "conflicting_factors": [],
        "notes": "<placeholder final notes>",
    }
    return {
        "symbol": "AVGO",
        "predict_timestamp": "2026-04-09 16:00:00",
        "scan_bias": "bullish",
        "scan_confidence": "medium",
        "research_bias_adjustment": "confirms_bias",
        "final_bias": final_bias,
        "final_confidence": final_confidence,
        "open_tendency": "gap_up_bias",
        "close_tendency": "close_strong",
        "pred_open": pred_open,
        "pred_path": pred_path,
        "pred_close": pred_close,
        "prediction_summary": "<placeholder final summary>",
        "supporting_factors": ["primary_bias=" + final_bias, "peer_confirmation=reinforce"],
        "conflicting_factors": [],
        "path_risk": "low",
        "peer_path_risk_adjustment": peer_adjustment["path_risk_adjustment"],
        "notes": "<placeholder final notes>",
        "primary_projection": primary_projection,
        "peer_adjustment": peer_adjustment,
        "final_projection": final_projection,
        "briefing_caution_applied": False,
        "briefing_caution_reason": None,
        "projection_three_systems": {
            "kind": "projection_three_systems",
            "symbol": "AVGO",
            "ready": False,
            "negative_system": {},
            "record_02_projection_system": {},
            "confidence_evaluator": {},
        },
    }


def unavailable_predict_result() -> dict[str, Any]:
    """Mirror of the predict.run_predict 'scan missing' branch."""
    return {
        "symbol": "AVGO",
        "predict_timestamp": "2026-04-09 16:00:00",
        "scan_bias": "neutral",
        "scan_confidence": "low",
        "research_bias_adjustment": "missing_research",
        "final_bias": "unavailable",
        "final_confidence": "low",
        "open_tendency": "unclear",
        "close_tendency": "unclear",
        "pred_open": None,
        "pred_path": None,
        "pred_close": None,
        "prediction_summary": "<unavailable summary>",
        "supporting_factors": [],
        "conflicting_factors": ["primary_projection_unavailable"],
        "path_risk": "high",
        "peer_path_risk_adjustment": {
            "status": "unavailable",
            "before": "high",
            "after": "high",
            "risk_direction": "unchanged",
            "reasons": ["primary_projection_unavailable"],
            "path_label_changed": False,
        },
        "notes": "Primary projection is unavailable, so final projection is unavailable.",
        "primary_projection": {
            "symbol": "AVGO",
            "status": "unavailable",
            "final_bias": "unavailable",
            "final_confidence": "low",
            "pred_open": None,
            "pred_close": None,
        },
        "peer_adjustment": {
            "status": "unavailable",
            "peer_symbols": ["NVDA", "SOXX", "QQQ"],
            "confirm_count": 0,
            "oppose_count": 0,
            "adjustment_direction": "neutral",
            "adjusted_bias": "unavailable",
            "adjusted_confidence": "low",
            "notes": "Peer adjustment unavailable.",
        },
        "final_projection": {
            "status": "unavailable",
            "final_bias": "unavailable",
            "final_confidence": "low",
            "pred_open": None,
            "pred_path": None,
            "pred_close": None,
            "prediction_summary": "<unavailable summary>",
        },
        "briefing_caution_applied": False,
        "briefing_caution_reason": None,
        "projection_three_systems": None,
    }
