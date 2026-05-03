"""Adapter: legacy scan_result / research_result / predict_result → 1A contract dict.

Spec: tasks/step_1a_projection_output_contract.md (commit 76d9971)
Validator: services/projection_output_contract.py (Step 1B)

Guarantees:
- Pure function. Never mutates inputs.
- Never raises (defensive .get() everywhere; missing fields fall back to
  contract-valid placeholders: ``"unknown"`` / 0 / 0.0 / [] / {} / None).
- Never reads files / calls external APIs.
- Output always passes ``validate_projection_output(...)``.

Not yet wired into ``run_predict``. This is a read-only translation layer for
Step 1C; subsequent steps may swap it in as the canonical output shape.
"""
from __future__ import annotations

from typing import Any


# ── value translation tables (legacy English / mixed labels → 1A enums) ────────

_BIAS_TO_DIRECTION_CN: dict[str, str] = {
    "bullish": "偏多",
    "bearish": "偏空",
    "neutral": "中性",
    "unavailable": "中性",
}

_PRED_OPEN_TO_OPEN_PROJ: dict[str, str] = {
    "高开": "高开",
    "平开": "平开",
    "低开": "低开",
}

_PRED_CLOSE_TO_CLOSE_PROJ: dict[str, str] = {
    "收涨": "收涨",
    "收跌": "收跌",
    "平收": "收平",  # 1A contract uses 收平, predict.py emits 平收
}

# legacy pred_path label → 1A intraday_path enum
def _pred_path_to_intraday(pred_path: str | None) -> str:
    if not isinstance(pred_path, str) or not pred_path:
        return "震荡"
    if "高走" in pred_path or "走高" in pred_path:
        return "高走"
    if "低走" in pred_path or "走低" in pred_path:
        return "低走"
    return "震荡"


_RELATIVE_STRENGTH_TO_PEER_SIGNAL: dict[str, str] = {
    "stronger": "reinforce",
    "weaker": "weaken",
    "neutral": "neutral",
    "unavailable": "unknown",
}

_PEER_ADJUSTMENT_DIRECTION_TO_LABEL: dict[str, str] = {
    "reinforce": "upgrade",
    "weaken": "downgrade",
    "neutral_primary": "flip_to_neutral",
    "neutral": "hold",
}

# Contract enums for the peer_confirmation_adjustment section. Used by the
# adapter when picking between a peer_adjustment dict's self-published fields
# (Step 2B-3) and the legacy fallback derivation.
_PEER_SIGNAL_VALUES = frozenset({"reinforce", "weaken", "neutral", "unknown"})
_PEER_ALIGNMENT_VALUES = frozenset({"all_reinforce", "mixed", "all_weaken", "insufficient"})
_PEER_ADJUSTMENT_VALUES = frozenset({"upgrade", "hold", "downgrade", "flip_to_neutral"})
_DIRECTION_CN_VALUES = frozenset({"偏多", "偏空", "中性"})

# Contract enums for the final_projection section. Used by Step 2B-4 to pick
# between final_projection's self-published fields and the legacy fallback.
_OPEN_PROJ_VALUES = frozenset({"高开", "平开", "低开"})
_INTRADAY_PATH_VALUES = frozenset({"高走", "震荡", "低走", "V 型反转", "倒 V"})
_CLOSE_PROJ_VALUES = frozenset({"收涨", "收平", "收跌"})
_FIVE_STATE_VALUES = frozenset({"大涨", "小涨", "震荡", "小跌", "大跌"})
_PROBABILITY_BUCKET_VALUES = frozenset({"≥70%", "55–70%", "45–55%", "30–45%", "≤30%"})

# confidence_level → (probability_bucket, total_confidence midpoint) for placeholder math
_CONFIDENCE_TO_BUCKET: dict[str, str] = {
    "high": "≥70%",
    "medium": "55–70%",
    "low": "45–55%",
}
_CONFIDENCE_TO_TOTAL: dict[str, float] = {
    "high": 0.75,
    "medium": 0.50,
    "low": 0.25,
}

_VALID_CONFIDENCE = frozenset({"high", "medium", "low"})


# ── small helpers ─────────────────────────────────────────────────────────────

def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_confidence(value: Any) -> str:
    return value if value in _VALID_CONFIDENCE else "low"


def _bias_to_cn(value: Any) -> str:
    return _BIAS_TO_DIRECTION_CN.get(str(value), "中性") if value is not None else "中性"


def _open_proj(value: Any) -> str:
    return _PRED_OPEN_TO_OPEN_PROJ.get(str(value), "平开") if value else "平开"


def _close_proj(value: Any) -> str:
    return _PRED_CLOSE_TO_CLOSE_PROJ.get(str(value), "收平") if value else "收平"


def _five_state(direction_cn: str, close_proj: str) -> str:
    """Conservative derivation: never claim 大涨/大跌 from adapter alone."""
    if direction_cn == "偏多" and close_proj == "收涨":
        return "小涨"
    if direction_cn == "偏空" and close_proj == "收跌":
        return "小跌"
    return "震荡"


# ── per-section builders ──────────────────────────────────────────────────────

_DATA_WINDOW_DAYS_FALLBACK = 15


def _data_window_days_from_predict(predict: dict[str, Any]) -> int:
    """Source of truth: build_primary_projection's lookback_days.

    Falls back to ``_DATA_WINDOW_DAYS_FALLBACK`` when the primary block is
    missing (e.g. adapter called with ``predict_result=None``).
    """
    primary = _safe_dict(predict.get("primary_projection"))
    lookback = _as_int(primary.get("lookback_days"))
    if lookback is not None and lookback > 0:
        return lookback
    return _DATA_WINDOW_DAYS_FALLBACK


def _build_current_structure(scan: dict[str, Any], predict: dict[str, Any]) -> dict[str, Any]:
    symbol = str(scan.get("symbol") or predict.get("symbol") or "AVGO")

    timestamp = scan.get("scan_timestamp")
    analysis_date = "unknown"
    if isinstance(timestamp, str) and len(timestamp) >= 10:
        analysis_date = timestamp[:10]

    recent = _safe_list(scan.get("avgo_recent_20"))
    last_row = recent[-1] if recent and isinstance(recent[-1], dict) else {}
    prev_row = recent[-2] if len(recent) >= 2 and isinstance(recent[-2], dict) else {}

    current_price = _as_float(last_row.get("Close")) or 0.0
    previous_close = _as_float(prev_row.get("Close")) or 0.0
    volume = _as_int(last_row.get("Volume")) or 0
    turnover = current_price * volume if volume else 0.0

    return {
        "symbol": symbol,
        "analysis_date": analysis_date,
        "prediction_for_date": "unknown",
        "data_window_days": _data_window_days_from_predict(predict),
        "current_price": current_price,
        "previous_close": previous_close,
        "volume": volume,
        "turnover": turnover,
        "structure_label": str(scan.get("avgo_price_state") or "unknown"),
        "short_summary": str(scan.get("scan_phase_note") or ""),
    }


def _build_avgo_primary_projection(predict: dict[str, Any]) -> dict[str, Any]:
    primary = _safe_dict(predict.get("primary_projection"))
    primary_bias_en = primary.get("final_bias") or predict.get("final_bias")
    primary_confidence = _normalize_confidence(
        primary.get("final_confidence") or predict.get("final_confidence")
    )

    pred_open = predict.get("pred_open")
    pred_path = predict.get("pred_path")
    pred_close = predict.get("pred_close")

    return {
        "primary_direction": _bias_to_cn(primary_bias_en),
        "open_projection": _open_proj(pred_open),
        "intraday_path_projection": _pred_path_to_intraday(pred_path),
        "close_projection": _close_proj(pred_close),
        "five_state_projection": _five_state(_bias_to_cn(primary_bias_en), _close_proj(pred_close)),
        "historical_sample_count": _as_int(
            _safe_dict(primary.get("historical_match_summary")).get("sample_count")
        ) or 0,
        "key_evidence": list(_safe_list(predict.get("supporting_factors"))),
        "primary_confidence_raw": primary_confidence,
    }


def _take_enum(d: dict[str, Any], key: str, allowed: frozenset[str]) -> str | None:
    """Return ``d[key]`` only if it is a contract-valid enum value, else None."""
    value = d.get(key)
    return value if value in allowed else None


def _build_peer_confirmation_adjustment(
    scan: dict[str, Any], predict: dict[str, Any]
) -> dict[str, Any]:
    """Build contract section 03.

    Step 2B-3 pivot: prefer fields that ``apply_peer_adjustment`` self-publishes
    on the predict_result["peer_adjustment"] dict. Fall back to the legacy
    derivation (from scan_result.relative_strength_summary + counts +
    adjustment_direction) so older predict payloads keep validating.
    """
    rs = _safe_dict(scan.get("relative_strength_summary"))
    peer_adjustment = _safe_dict(predict.get("peer_adjustment"))

    # — fallback derivations (legacy Step 1C path) —
    def _legacy_signal(peer: str) -> str:
        info = _safe_dict(rs.get(peer))
        rs_label = info.get("relative_strength")
        return _RELATIVE_STRENGTH_TO_PEER_SIGNAL.get(str(rs_label), "unknown") if rs_label else "unknown"

    confirm_count = _as_int(peer_adjustment.get("confirm_count"))
    oppose_count = _as_int(peer_adjustment.get("oppose_count"))
    if confirm_count is not None and oppose_count is not None:
        if confirm_count >= 3 and oppose_count == 0:
            legacy_alignment = "all_reinforce"
        elif oppose_count >= 3 and confirm_count == 0:
            legacy_alignment = "all_weaken"
        elif confirm_count == 0 and oppose_count == 0:
            legacy_alignment = "insufficient"
        else:
            legacy_alignment = "mixed"
    else:
        legacy_alignment = "insufficient"

    legacy_peer_adjustment_label = _PEER_ADJUSTMENT_DIRECTION_TO_LABEL.get(
        str(peer_adjustment.get("adjustment_direction")), "hold"
    )
    legacy_adjusted_direction = _bias_to_cn(
        peer_adjustment.get("adjusted_bias") or predict.get("final_bias")
    )
    legacy_reason = str(peer_adjustment.get("notes") or "")

    # — self-published preference (Step 2B-3) —
    nvda_signal = (
        _take_enum(peer_adjustment, "nvda_signal", _PEER_SIGNAL_VALUES)
        or _legacy_signal("NVDA")
    )
    soxx_signal = (
        _take_enum(peer_adjustment, "soxx_signal", _PEER_SIGNAL_VALUES)
        or _legacy_signal("SOXX")
    )
    qqq_signal = (
        _take_enum(peer_adjustment, "qqq_signal", _PEER_SIGNAL_VALUES)
        or _legacy_signal("QQQ")
    )
    peer_alignment = (
        _take_enum(peer_adjustment, "peer_alignment", _PEER_ALIGNMENT_VALUES)
        or legacy_alignment
    )
    peer_adjustment_label = (
        _take_enum(peer_adjustment, "peer_adjustment", _PEER_ADJUSTMENT_VALUES)
        or legacy_peer_adjustment_label
    )
    adjusted_direction = (
        _take_enum(peer_adjustment, "adjusted_direction", _DIRECTION_CN_VALUES)
        or legacy_adjusted_direction
    )

    self_reason = peer_adjustment.get("adjustment_reason")
    adjustment_reason = self_reason if isinstance(self_reason, str) else legacy_reason

    self_symbols = peer_adjustment.get("peer_symbols")
    peer_symbols = (
        list(self_symbols) if isinstance(self_symbols, list) and self_symbols
        else ["NVDA", "SOXX", "QQQ"]
    )

    return {
        "peer_symbols": peer_symbols,
        "nvda_signal": nvda_signal,
        "soxx_signal": soxx_signal,
        "qqq_signal": qqq_signal,
        "peer_alignment": peer_alignment,
        "peer_adjustment": peer_adjustment_label,
        "adjusted_direction": adjusted_direction,
        "adjustment_reason": adjustment_reason,
    }


def _build_exclusion_system(predict: dict[str, Any]) -> dict[str, Any]:
    # The contract's 04 section will eventually be populated by an independent
    # exclusion / contradiction module (PR-C scope). For now the adapter emits
    # a contract-valid 'no exclusion observed' payload.
    return {
        "exclusion_level": "none",
        "exclusion_sources": [],
        "exclusion_reasons": [],
        "forced_exclusion": False,
        "anti_false_exclusion_triggered": False,
    }


def _build_confidence_system(predict: dict[str, Any]) -> dict[str, Any]:
    confidence_level = _normalize_confidence(predict.get("final_confidence"))
    total_confidence = _CONFIDENCE_TO_TOTAL.get(confidence_level, 0.0)
    return {
        "historical_score": 0.0,
        "structure_score": 0.0,
        "peer_score": 0.0,
        "exclusion_penalty": 0.0,
        "event_score": None,
        "total_confidence": total_confidence,
        "confidence_level": confidence_level,
        "confidence_reason": str(predict.get("prediction_summary") or ""),
    }


def _build_final_projection(predict: dict[str, Any]) -> dict[str, Any]:
    """Build contract section 06.

    Step 2B-4 pivot: prefer fields that ``build_final_projection`` self-publishes
    on ``predict_result["final_projection"]``. Fall back to the legacy
    derivation (top-level ``final_bias`` / ``pred_open`` / ``pred_path`` /
    ``pred_close`` / ``final_confidence`` / ``prediction_summary``) so older
    predict payloads keep validating.
    """
    final_block = _safe_dict(predict.get("final_projection"))

    # — fallback derivations (legacy Step 1C path) —
    legacy_direction = _bias_to_cn(predict.get("final_bias"))
    legacy_open = _open_proj(predict.get("pred_open"))
    legacy_path = _pred_path_to_intraday(predict.get("pred_path"))
    legacy_close = _close_proj(predict.get("pred_close"))
    legacy_five_state = _five_state(legacy_direction, legacy_close)
    legacy_confidence_level = _normalize_confidence(predict.get("final_confidence"))
    legacy_bucket = _CONFIDENCE_TO_BUCKET.get(legacy_confidence_level, "45–55%")
    legacy_sentence = str(predict.get("prediction_summary") or "")

    # — self-published preference (Step 2B-4) —
    final_direction = (
        _take_enum(final_block, "final_direction", _DIRECTION_CN_VALUES)
        or legacy_direction
    )
    final_open_projection = (
        _take_enum(final_block, "final_open_projection", _OPEN_PROJ_VALUES)
        or legacy_open
    )
    final_intraday_path = (
        _take_enum(final_block, "final_intraday_path", _INTRADAY_PATH_VALUES)
        or legacy_path
    )
    final_close_projection = (
        _take_enum(final_block, "final_close_projection", _CLOSE_PROJ_VALUES)
        or legacy_close
    )
    final_five_state = (
        _take_enum(final_block, "final_five_state", _FIVE_STATE_VALUES)
        or legacy_five_state
    )
    probability_bucket = (
        _take_enum(final_block, "probability_bucket", _PROBABILITY_BUCKET_VALUES)
        or legacy_bucket
    )

    self_klp = final_block.get("key_price_levels")
    key_price_levels = self_klp if isinstance(self_klp, dict) else {}

    self_sentence = final_block.get("final_one_sentence")
    final_one_sentence = (
        self_sentence if isinstance(self_sentence, str) and self_sentence
        else legacy_sentence
    )

    return {
        "final_direction": final_direction,
        "final_open_projection": final_open_projection,
        "final_intraday_path": final_intraday_path,
        "final_close_projection": final_close_projection,
        "final_five_state": final_five_state,
        "probability_bucket": probability_bucket,
        "key_price_levels": key_price_levels,
        "final_one_sentence": final_one_sentence,
    }


def _build_simulated_trade(predict: dict[str, Any]) -> dict[str, Any]:
    # 07 is intentionally a no-trade default this round (per Step 1C scope).
    return {
        "trade_action": "no_trade",
        "trade_direction": "none",
        "entry_condition": "",
        "stop_loss_condition": "",
        "take_profit_condition": "",
        "suggested_position_size": "0%",
        "no_trade_reason": "adapter default: simulated trade decision not yet wired",
    }


def _build_review_payload(predict: dict[str, Any]) -> dict[str, Any]:
    open_proj = _open_proj(predict.get("pred_open"))
    intraday_path = _pred_path_to_intraday(predict.get("pred_path"))
    close_proj = _close_proj(predict.get("pred_close"))
    direction_cn = _bias_to_cn(predict.get("final_bias"))
    five_state = _five_state(direction_cn, close_proj)
    confidence_level = _normalize_confidence(predict.get("final_confidence"))

    return {
        "predicted_open_type": open_proj,
        "predicted_path_type": intraday_path,
        "predicted_close_type": close_proj,
        "predicted_five_state": five_state,
        "predicted_confidence": confidence_level,
        "prediction_id": "",
        "review_ready_fields": [
            "predicted_open_type",
            "predicted_path_type",
            "predicted_close_type",
            "predicted_five_state",
            "predicted_confidence",
        ],
    }


# ── public API ────────────────────────────────────────────────────────────────

def adapt_projection_output(
    *,
    scan_result: dict[str, Any] | None,
    research_result: dict[str, Any] | None,
    predict_result: dict[str, Any] | None,
) -> dict[str, Any]:
    """Translate the legacy three-dict bundle into the 1A contract shape.

    All inputs may be ``None`` or partial; output always conforms to the
    contract and never embeds fabricated market values.
    """
    scan = _safe_dict(scan_result)
    predict = _safe_dict(predict_result)
    # research_result is reserved for future event_score / risk attribution
    # work; it is intentionally not consumed in this minimal adapter.
    _ = research_result

    return {
        "current_structure": _build_current_structure(scan, predict),
        "avgo_primary_projection": _build_avgo_primary_projection(predict),
        "peer_confirmation_adjustment": _build_peer_confirmation_adjustment(scan, predict),
        "exclusion_system": _build_exclusion_system(predict),
        "confidence_system": _build_confidence_system(predict),
        "final_projection": _build_final_projection(predict),
        "simulated_trade": _build_simulated_trade(predict),
        "review_payload": _build_review_payload(predict),
    }
