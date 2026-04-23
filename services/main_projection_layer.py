"""Standardized main projection layer for five-state next-day output.

This module produces a stable Top1 / Top2 / probability distribution report
from current 20-day features, exclusion constraints, peer alignment, and
optional historical matching evidence.
"""

from __future__ import annotations

from math import exp
from typing import Any

from services.exclusion_layer import build_peer_alignment


_STATE_ORDER = ("大涨", "小涨", "震荡", "小跌", "大跌")
_STATE_CENTERS = {
    "大涨": 3.0,
    "小涨": 1.0,
    "震荡": 0.0,
    "小跌": -1.0,
    "大跌": -3.0,
}
_FALLBACK_DISTRIBUTION = {
    "大涨": 0.15,
    "小涨": 0.20,
    "震荡": 0.30,
    "小跌": 0.20,
    "大跌": 0.15,
}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _pick_float(source: dict[str, Any], keys: list[str]) -> float | None:
    for key in keys:
        value = _safe_float(source.get(key))
        if value is not None:
            return value
    return None


def _normalize_current_features(current_20day_features: dict[str, Any]) -> dict[str, Any]:
    source = dict(_as_dict(current_20day_features.get("features")))
    source.update(_as_dict(current_20day_features))
    return {
        "symbol": str(source.get("symbol") or "AVGO").strip().upper() or "AVGO",
        "pos20": _pick_float(source, ["pos20", "pos_20", "pos_20d", "position_20d"]),
        "vol_ratio20": _pick_float(
            source,
            ["vol_ratio20", "vol_ratio_20", "vol_ratio_20d", "vol_ratio_5d"],
        ),
        "upper_shadow_ratio": _pick_float(
            source,
            ["upper_shadow_ratio", "upper_shadow", "up_shadow_ratio"],
        ),
        "lower_shadow_ratio": _pick_float(
            source,
            ["lower_shadow_ratio", "lower_shadow", "down_shadow_ratio"],
        ),
        "ret1": _pick_float(
            source,
            ["ret1", "ret_1d", "day_return_pct", "close_change_pct", "pct_change"],
        ),
        "ret3": _pick_float(source, ["ret3", "ret_3d"]),
        "ret5": _pick_float(source, ["ret5", "ret_5d"]),
        "ret10": _pick_float(source, ["ret10", "ret_10d"]),
        "nvda_ret1": _pick_float(source, ["nvda_ret1", "nvda_ret_1d", "ret1_nvda"]),
        "soxx_ret1": _pick_float(source, ["soxx_ret1", "soxx_ret_1d", "ret1_soxx"]),
        "qqq_ret1": _pick_float(source, ["qqq_ret1", "qqq_ret_1d", "ret1_qqq"]),
    }


def _clip(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _historical_bias_payload(historical_match_result: dict[str, Any]) -> tuple[float, list[str]]:
    history = _as_dict(historical_match_result)
    reasons: list[str] = []

    explicit_probs = history.get("state_probabilities")
    if isinstance(explicit_probs, dict):
        weighted = 0.0
        for state, center in _STATE_CENTERS.items():
            prob = _safe_float(explicit_probs.get(state))
            if prob is None:
                continue
            weighted += prob * center
        if weighted:
            reasons.append("历史匹配提供了显式五状态分布，主推演层已将其作为轻量偏置。")
        return weighted * 0.35, reasons

    dominant = str(
        history.get("dominant_historical_outcome")
        or history.get("historical_bias")
        or history.get("dominant_outcome")
        or ""
    ).strip().lower()
    if dominant in {"up_bias", "bullish", "supports_bullish"}:
        reasons.append("历史匹配偏向 bullish，对主推演层增加轻量偏多修正。")
        return 0.35, reasons
    if dominant in {"down_bias", "bearish", "supports_bearish"}:
        reasons.append("历史匹配偏向 bearish，对主推演层增加轻量偏空修正。")
        return -0.35, reasons
    if dominant == "mixed":
        reasons.append("历史匹配结果偏 mixed，主推演层不做方向性偏置。")
    return 0.0, reasons


def _peer_payload(peer_alignment: dict[str, Any], reasons: list[str]) -> float:
    peer = _as_dict(peer_alignment)
    bias = 0.0

    up_support = str(peer.get("up_support") or "unknown")
    down_support = str(peer.get("down_support") or "unknown")

    if up_support == "supported":
        bias += 0.45
        reasons.append("peers 对上行给出 supported，主推演层增加偏多权重。")
    elif up_support == "partial":
        bias += 0.15
        reasons.append("peers 对上行仅 partial，主推演层只做轻量偏多修正。")
    elif up_support == "unsupported":
        bias -= 0.15
        reasons.append("peers 不支持上行极端扩张，主推演层压低大涨权重。")

    if down_support == "supported":
        bias -= 0.45
        reasons.append("peers 对下行给出 supported，主推演层增加偏空权重。")
    elif down_support == "partial":
        bias -= 0.15
        reasons.append("peers 对下行仅 partial，主推演层只做轻量偏空修正。")
    elif down_support == "unsupported":
        bias += 0.15
        reasons.append("peers 不支持极端下跌，主推演层压低大跌权重。")

    return bias


def _base_outlook(features: dict[str, Any], reasons: list[str]) -> float:
    ret1 = features["ret1"]
    ret3 = features["ret3"]
    ret5 = features["ret5"]
    ret10 = features["ret10"]
    pos20 = features["pos20"]
    vol_ratio20 = features["vol_ratio20"]
    upper_shadow_ratio = features["upper_shadow_ratio"]
    lower_shadow_ratio = features["lower_shadow_ratio"]

    outlook = 0.0
    momentum_anchor = 0.0

    if ret1 is not None:
        outlook += ret1 * 0.28
        momentum_anchor += ret1 * 0.20
    if ret3 is not None:
        outlook += ret3 * 0.22
        momentum_anchor += ret3 * 0.30
    if ret5 is not None:
        outlook += ret5 * 0.18
        momentum_anchor += ret5 * 0.50
    if ret10 is not None:
        outlook += ret10 * 0.08
        momentum_anchor += ret10 * 0.10

    if any(value is not None for value in (ret1, ret3, ret5, ret10)):
        reasons.append(
            "ret1 / ret3 / ret5 / ret10 被用作主方向锚点，先形成基础动量倾向。"
        )

    if pos20 is not None:
        position_bias = _clip((pos20 - 50.0) / 40.0 * 0.45, -0.60, 0.60)
        outlook += position_bias
        reasons.append(f"pos20={pos20:.1f}，20日相对位置已纳入方向偏置。")

    if vol_ratio20 is not None:
        if vol_ratio20 >= 1.15 and abs(momentum_anchor) >= 1.5:
            outlook += 0.35 if momentum_anchor > 0 else -0.35
            reasons.append(f"vol_ratio20={vol_ratio20:.2f}，放量强化当前动量方向。")
        elif vol_ratio20 <= 0.85 and abs(momentum_anchor) >= 1.0:
            outlook += -0.25 if momentum_anchor > 0 else 0.25
            reasons.append(f"vol_ratio20={vol_ratio20:.2f}，缩量削弱当前动量延续。")

    if upper_shadow_ratio is not None and upper_shadow_ratio >= 0.35:
        outlook -= 0.45
        reasons.append(
            f"upper_shadow_ratio={upper_shadow_ratio:.2f}，上影偏长，对明日上行空间形成压制。"
        )
    if lower_shadow_ratio is not None and lower_shadow_ratio >= 0.35:
        outlook += 0.45
        reasons.append(
            f"lower_shadow_ratio={lower_shadow_ratio:.2f}，下影承接明显，对明日下行空间形成缓冲。"
        )

    return _clip(outlook, -3.5, 3.5)


def _score_distribution(outlook: float, features: dict[str, Any]) -> dict[str, float]:
    vol_ratio20 = features["vol_ratio20"]
    upper_shadow_ratio = features["upper_shadow_ratio"]
    lower_shadow_ratio = features["lower_shadow_ratio"]

    scores: dict[str, float] = {}
    for state in _STATE_ORDER:
        center = _STATE_CENTERS[state]
        sigma = 1.35 if state in {"大涨", "大跌"} else 0.95
        if state == "震荡":
            sigma = 0.85
        scores[state] = exp(-((outlook - center) ** 2) / (2 * sigma * sigma))

    if vol_ratio20 is not None and vol_ratio20 <= 0.90:
        scores["震荡"] += 0.18
    if upper_shadow_ratio is not None and upper_shadow_ratio >= 0.35:
        scores["大涨"] *= 0.78
        scores["小涨"] *= 0.88
        scores["震荡"] += 0.08
    if lower_shadow_ratio is not None and lower_shadow_ratio >= 0.35:
        scores["大跌"] *= 0.78
        scores["小跌"] *= 0.88
        scores["震荡"] += 0.08

    return scores


def _apply_history_weights(
    scores: dict[str, float],
    historical_match_result: dict[str, Any],
) -> dict[str, float]:
    history = _as_dict(historical_match_result)
    explicit_probs = history.get("state_probabilities")
    if not isinstance(explicit_probs, dict):
        return scores

    adjusted = dict(scores)
    for state in _STATE_ORDER:
        prob = _safe_float(explicit_probs.get(state))
        if prob is None:
            continue
        adjusted[state] = adjusted[state] * (1.0 + max(prob, 0.0))
    return adjusted


def _apply_exclusion(
    scores: dict[str, float],
    exclusion_result: dict[str, Any],
    reasons: list[str],
) -> dict[str, float]:
    exclusion = _as_dict(exclusion_result)
    adjusted = dict(scores)

    if not exclusion.get("excluded"):
        return adjusted

    triggered_rule = str(exclusion.get("triggered_rule") or "")
    if triggered_rule == "exclude_big_up":
        adjusted["大涨"] = 0.0
        reasons.append("排除层已给出“明天不太可能大涨”，主推演层禁止将大涨排为 Top1。")
    elif triggered_rule == "exclude_big_down":
        adjusted["大跌"] = 0.0
        reasons.append("排除层已给出“明天不太可能大跌”，主推演层禁止将大跌排为 Top1。")

    return adjusted


def _normalize_distribution(scores: dict[str, float]) -> dict[str, float]:
    safe_scores = {state: max(float(value), 0.0) for state, value in scores.items()}
    total = sum(safe_scores.values())
    if total <= 0:
        return dict(_FALLBACK_DISTRIBUTION)
    distribution = {
        state: round(safe_scores[state] / total, 4)
        for state in _STATE_ORDER
    }
    diff = round(1.0 - sum(distribution.values()), 4)
    if diff:
        anchor = max(distribution, key=distribution.get)
        distribution[anchor] = round(distribution[anchor] + diff, 4)
    return distribution


def _rank_states(distribution: dict[str, float]) -> list[tuple[str, float]]:
    return sorted(
        distribution.items(),
        key=lambda item: (-item[1], _STATE_ORDER.index(item[0])),
    )


def build_main_projection_layer(
    *,
    current_20day_features: dict[str, Any],
    exclusion_result: dict[str, Any] | None = None,
    historical_match_result: dict[str, Any] | None = None,
    peer_alignment: dict[str, Any] | None = None,
    symbol: str = "AVGO",
) -> dict[str, Any]:
    """Build a stable five-state projection from current 20-day context."""
    normalized = _normalize_current_features(current_20day_features)
    clean_symbol = str(symbol or normalized["symbol"] or "AVGO").strip().upper() or "AVGO"
    reasons: list[str] = []
    warnings: list[str] = []

    peer_payload = _as_dict(peer_alignment)
    if not peer_payload:
        peer_payload = _as_dict(_as_dict(exclusion_result).get("peer_alignment"))
    if not peer_payload:
        peer_payload = build_peer_alignment(normalized)

    feature_snapshot = {
        "pos20": normalized["pos20"],
        "vol_ratio20": normalized["vol_ratio20"],
        "upper_shadow_ratio": normalized["upper_shadow_ratio"],
        "lower_shadow_ratio": normalized["lower_shadow_ratio"],
        "ret1": normalized["ret1"],
        "ret3": normalized["ret3"],
        "ret5": normalized["ret5"],
        "ret10": normalized["ret10"],
    }

    available_feature_count = sum(
        1 for value in feature_snapshot.values() if value is not None
    )
    if available_feature_count < 3:
        warnings.append("主推演层可用特征不足，已安全降级为中性分布。")
        distribution = dict(_FALLBACK_DISTRIBUTION)
        ranked = _rank_states(distribution)
        return {
            "kind": "main_projection_layer",
            "symbol": clean_symbol,
            "ready": False,
            "predicted_top1": {"state": ranked[0][0], "probability": ranked[0][1]},
            "predicted_top2": {"state": ranked[1][0], "probability": ranked[1][1]},
            "state_probabilities": distribution,
            "rationale": ["当前20日特征不足，主推演层已回退到保守中性分布。"],
            "warnings": warnings,
            "peer_alignment": peer_payload,
            "feature_snapshot": feature_snapshot,
        }

    outlook = _base_outlook(normalized, reasons)
    outlook += _peer_payload(peer_payload, reasons)
    historical_bias, historical_reasons = _historical_bias_payload(
        _as_dict(historical_match_result)
    )
    outlook += historical_bias
    reasons.extend(historical_reasons)
    outlook = _clip(outlook, -3.5, 3.5)

    scores = _score_distribution(outlook, normalized)
    scores = _apply_history_weights(scores, _as_dict(historical_match_result))
    scores = _apply_exclusion(scores, _as_dict(exclusion_result), reasons)
    distribution = _normalize_distribution(scores)
    ranked = _rank_states(distribution)

    return {
        "kind": "main_projection_layer",
        "symbol": clean_symbol,
        "ready": True,
        "predicted_top1": {"state": ranked[0][0], "probability": ranked[0][1]},
        "predicted_top2": {"state": ranked[1][0], "probability": ranked[1][1]},
        "state_probabilities": distribution,
        "rationale": reasons or ["主推演层已基于当前20日特征生成五状态分布。"],
        "warnings": warnings,
        "peer_alignment": peer_payload,
        "feature_snapshot": feature_snapshot,
    }


def run_main_projection_layer(
    current_20day_features: dict[str, Any],
    exclusion_result: dict[str, Any] | None = None,
    historical_match_result: dict[str, Any] | None = None,
    peer_alignment: dict[str, Any] | None = None,
    symbol: str = "AVGO",
) -> dict[str, Any]:
    """Convenience wrapper for callers that prefer run_* naming."""
    return build_main_projection_layer(
        current_20day_features=current_20day_features,
        exclusion_result=exclusion_result,
        historical_match_result=historical_match_result,
        peer_alignment=peer_alignment,
        symbol=symbol,
    )
