"""Internal consistency checks across projection v2 layers.

This module only checks whether existing layer outputs agree with each other.
It does not change UI, orchestrator wiring, or evidence-trace rendering.
"""

from __future__ import annotations

from typing import Any


_BULLISH_STATES = {"大涨", "小涨"}
_BEARISH_STATES = {"大跌", "小跌"}
_NEUTRAL_STATE = "震荡"


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _state_from_projection(main_projection_result: dict[str, Any]) -> str:
    projection = _as_dict(main_projection_result)
    top1 = _as_dict(projection.get("predicted_top1"))
    state = str(top1.get("state") or "").strip()
    return state if state else "unknown"


def _projection_probability(main_projection_result: dict[str, Any], state: str) -> float | None:
    probs = _as_dict(_as_dict(main_projection_result).get("state_probabilities"))
    return _safe_float(probs.get(state))


def _projection_side(state: str) -> str:
    if state in _BULLISH_STATES:
        return "bullish"
    if state in _BEARISH_STATES:
        return "bearish"
    if state == _NEUTRAL_STATE:
        return "neutral"
    return "unknown"


def _historical_side(historical_match_result: dict[str, Any]) -> str:
    history = _as_dict(historical_match_result)
    explicit_probs = history.get("state_probabilities")
    if isinstance(explicit_probs, dict):
        bullish = sum(
            _safe_float(explicit_probs.get(state)) or 0.0
            for state in ("大涨", "小涨")
        )
        bearish = sum(
            _safe_float(explicit_probs.get(state)) or 0.0
            for state in ("小跌", "大跌")
        )
        if bullish >= bearish + 0.15:
            return "bullish"
        if bearish >= bullish + 0.15:
            return "bearish"
        return "neutral"

    dominant = str(
        history.get("dominant_historical_outcome")
        or history.get("historical_bias")
        or history.get("dominant_outcome")
        or ""
    ).strip().lower()

    if dominant in {"up_bias", "bullish", "supports_bullish"}:
        return "bullish"
    if dominant in {"down_bias", "bearish", "supports_bearish"}:
        return "bearish"
    if dominant == "mixed":
        return "neutral"
    return "unknown"


def _exclusion_conflicts(
    exclusion_result: dict[str, Any],
    main_projection_result: dict[str, Any],
) -> list[str]:
    exclusion = _as_dict(exclusion_result)
    projection_state = _state_from_projection(main_projection_result)
    conflicts: list[str] = []

    if not exclusion.get("excluded"):
        return conflicts

    triggered_rule = str(exclusion.get("triggered_rule") or "").strip()
    if triggered_rule == "exclude_big_up" and projection_state == "大涨":
        probability = _projection_probability(main_projection_result, "大涨")
        if probability is None:
            conflicts.append("排除层已排除大涨，但主推演层 Top1 仍给出大涨，形成硬冲突。")
        else:
            conflicts.append(
                f"排除层已排除大涨，但主推演层 Top1 仍给出大涨（prob={probability:.4f}），形成硬冲突。"
            )
    elif triggered_rule == "exclude_big_down" and projection_state == "大跌":
        probability = _projection_probability(main_projection_result, "大跌")
        if probability is None:
            conflicts.append("排除层已排除大跌，但主推演层 Top1 仍给出大跌，形成硬冲突。")
        else:
            conflicts.append(
                f"排除层已排除大跌，但主推演层 Top1 仍给出大跌（prob={probability:.4f}），形成硬冲突。"
            )

    return conflicts


def _peer_conflicts(
    peer_alignment: dict[str, Any],
    main_projection_result: dict[str, Any],
) -> list[str]:
    peer = _as_dict(peer_alignment)
    projection_state = _state_from_projection(main_projection_result)
    projection_side = _projection_side(projection_state)
    conflicts: list[str] = []

    up_support = str(peer.get("up_support") or "unknown").strip().lower()
    down_support = str(peer.get("down_support") or "unknown").strip().lower()

    if projection_side == "bullish" and up_support == "unsupported":
        conflicts.append("主推演层偏多，但 peers 对上行给出 unsupported，内部存在方向冲突。")
    elif projection_side == "bearish" and down_support == "unsupported":
        conflicts.append("主推演层偏空，但 peers 对下行给出 unsupported，内部存在方向冲突。")
    elif projection_side == "neutral" and (up_support == "supported" or down_support == "supported"):
        conflicts.append("主推演层偏震荡，但 peers 已给出较明确的单边支持，存在轻度不一致。")

    return conflicts


def _historical_conflicts(
    historical_match_result: dict[str, Any],
    main_projection_result: dict[str, Any],
) -> list[str]:
    history_side = _historical_side(historical_match_result)
    projection_state = _state_from_projection(main_projection_result)
    projection_side = _projection_side(projection_state)
    conflicts: list[str] = []

    if projection_side == "bullish" and history_side == "bearish":
        conflicts.append("主推演层偏多，但历史匹配结果明显偏 bearish，内部存在方向冲突。")
    elif projection_side == "bearish" and history_side == "bullish":
        conflicts.append("主推演层偏空，但历史匹配结果明显偏 bullish，内部存在方向冲突。")
    elif projection_side == "neutral" and history_side in {"bullish", "bearish"}:
        conflicts.append("主推演层偏震荡，但历史匹配已表现出方向倾向，存在轻度不一致。")

    return conflicts


def _score_from_conflicts(
    exclusion_conflicts: list[str],
    peer_conflicts: list[str],
    historical_conflicts: list[str],
) -> float:
    score = 1.0
    score -= 0.45 * len(exclusion_conflicts)
    score -= 0.25 * len(peer_conflicts)
    score -= 0.25 * len(historical_conflicts)
    return round(max(score, 0.0), 4)


def _flag_from_score(score: float) -> str:
    if score >= 0.85:
        return "consistent"
    if score >= 0.55:
        return "mixed"
    return "conflict"


def build_consistency_layer(
    *,
    exclusion_result: dict[str, Any] | None = None,
    main_projection_result: dict[str, Any] | None = None,
    peer_alignment: dict[str, Any] | None = None,
    historical_match_result: dict[str, Any] | None = None,
    symbol: str = "AVGO",
) -> dict[str, Any]:
    """Check whether existing projection layers agree with each other."""
    exclusion = _as_dict(exclusion_result)
    projection = _as_dict(main_projection_result)
    peer = _as_dict(peer_alignment) or _as_dict(exclusion.get("peer_alignment"))
    history = _as_dict(historical_match_result)
    clean_symbol = str(symbol or projection.get("symbol") or "AVGO").strip().upper() or "AVGO"

    if not projection:
        return {
            "kind": "consistency_layer",
            "symbol": clean_symbol,
            "ready": False,
            "consistency_flag": "unknown",
            "consistency_score": 0.0,
            "conflict_reasons": ["缺少主推演层输出，一致性校验无法完成。"],
            "summary": "一致性校验层缺少主推演层输入，已安全降级。",
        }

    exclusion_conflicts = _exclusion_conflicts(exclusion, projection)
    peer_conflicts = _peer_conflicts(peer, projection) if peer else []
    historical_conflicts = _historical_conflicts(history, projection) if history else []

    conflict_reasons = [
        *exclusion_conflicts,
        *peer_conflicts,
        *historical_conflicts,
    ]
    consistency_score = _score_from_conflicts(
        exclusion_conflicts,
        peer_conflicts,
        historical_conflicts,
    )
    consistency_flag = "conflict" if exclusion_conflicts else _flag_from_score(consistency_score)

    if not conflict_reasons:
        summary = "排除层、主推演层、peer alignment 与历史匹配结果整体一致。"
    elif consistency_flag == "mixed":
        summary = "系统内部存在轻中度不一致，建议在后续 orchestrator 中降低结论置信度。"
    else:
        summary = "系统内部存在明确冲突，后续 orchestrator 应将结果视为 conflict。"

    return {
        "kind": "consistency_layer",
        "symbol": clean_symbol,
        "ready": True,
        "consistency_flag": consistency_flag,
        "consistency_score": consistency_score,
        "conflict_reasons": conflict_reasons,
        "summary": summary,
    }
