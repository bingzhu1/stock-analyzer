"""Independent projection v2 final decision layer.

This module aggregates the projection v2 layers into a stable final decision.
It does not change scanner, predict, matcher, peer, or historical rules.
"""

from __future__ import annotations

from typing import Any


_DIRECTIONS = {"偏多", "偏空", "中性"}
_CONFIDENCE_LEVELS = {"unknown": 0, "low": 1, "medium": 2, "high": 3}
_CONFIDENCE_BY_SCORE = {0: "unknown", 1: "low", 2: "medium", 3: "high"}
_RISK_ORDER: dict[str, int] = {"low": 0, "medium": 1, "high": 2}
_RISK_BY_SCORE: dict[int, str] = {0: "low", 1: "medium", 2: "high"}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _direction(value: Any) -> str:
    text = str(value or "unknown").strip()
    return text if text in _DIRECTIONS else "unknown"


def _confidence(value: Any) -> str:
    text = str(value or "unknown").strip().lower()
    return text if text in _CONFIDENCE_LEVELS else "unknown"


def _confidence_score(value: str) -> int:
    return _CONFIDENCE_LEVELS.get(value, 0)


def _confidence_from_score(score: int) -> str:
    return _CONFIDENCE_BY_SCORE.get(max(0, min(3, score)), "unknown")


def _risk_score(value: str) -> int:
    return _RISK_ORDER.get(str(value or "").strip().lower(), 1)


def _risk_from_score(score: int) -> str:
    return _RISK_BY_SCORE.get(max(0, min(2, score)), "medium")


def _infer_rule_effect(rule: dict[str, Any]) -> str:
    explicit = rule.get("effect")
    if isinstance(explicit, str) and explicit in ("warn", "lower_confidence", "raise_risk"):
        return explicit
    severity = str(rule.get("severity") or "low").strip().lower()
    if severity == "high":
        return "lower_confidence"
    if severity == "medium":
        return "raise_risk"
    return "warn"


def _apply_preflight_influence(
    matched_rules: list[Any],
    final_confidence: str,
    risk_level: str,
) -> tuple[str, str, dict[str, Any]]:
    """Apply preflight rule effects to confidence and risk. Caps at one step each.

    severity mapping (unless rule carries explicit effect field):
      high   → lower_confidence  (−1 confidence level)
      medium → raise_risk        (+1 risk level)
      low    → warn              (no score change)
    """
    dict_rules = [r for r in (matched_rules or []) if isinstance(r, dict)]

    if not dict_rules:
        return final_confidence, risk_level, {
            "matched_rule_count": 0,
            "applied_effects": [],
            "summary": "未命中会影响最终结论的历史规则。",
        }

    applied: list[str] = []
    confidence_lowered = False
    risk_raised = False

    for rule in dict_rules:
        effect = _infer_rule_effect(rule)
        if effect == "lower_confidence" and not confidence_lowered:
            score = _confidence_score(final_confidence)
            if score > 0:
                final_confidence = _confidence_from_score(score - 1)
                confidence_lowered = True
                applied.append("lower_confidence")
        elif effect == "raise_risk" and not risk_raised:
            score = _risk_score(risk_level)
            if score < 2:
                risk_level = _risk_from_score(score + 1)
                risk_raised = True
                applied.append("raise_risk")

    if applied:
        parts = []
        if "lower_confidence" in applied:
            parts.append("下调置信度")
        if "raise_risk" in applied:
            parts.append("提高风险等级")
        summary = f"命中 {len(dict_rules)} 条历史规则：{'并'.join(parts)}。"
    else:
        summary = f"命中 {len(dict_rules)} 条历史规则提醒（仅警告，不影响置信度和风险等级）。"

    return final_confidence, risk_level, {
        "matched_rule_count": len(dict_rules),
        "applied_effects": applied,
        "summary": summary,
    }


def _preflight_rules_count(preflight: dict[str, Any]) -> int:
    matched = preflight.get("matched_rules")
    if isinstance(matched, list):
        return len(matched)
    try:
        return max(int(preflight.get("matched_count") or 0), 0)
    except (TypeError, ValueError):
        return 0


def _primary_missing_result(
    *,
    symbol: str,
    primary: dict[str, Any],
    peer: dict[str, Any],
    historical: dict[str, Any],
    preflight: dict[str, Any],
) -> dict[str, Any]:
    preflight_count = _preflight_rules_count(preflight)
    warning = "final_decision 不可用：主分析不可用，不能伪造完整结论。"
    summary = "最终结论不可用：主分析不可用，不能伪造完整结论。"
    return {
        "kind": "final_decision",
        "symbol": symbol,
        "ready": False,
        "final_direction": "unknown",
        "final_confidence": "unknown",
        "risk_level": "high",
        "summary": summary,
        "decision_factors": ["主分析不可用，最终决策层停止生成完整结论。"],
        "warnings": [warning],
        "layer_contributions": {
            "primary": "主分析不可用，是阻断项。",
            "peer": "peer 修正未参与最终结论。",
            "historical": "历史概率未参与最终结论。",
            "preflight": "preflight 仅保留提醒入口。",
        },
        "why_not_more_bullish_or_bearish": "主分析不可用，不能判断是否更偏多或更偏空。",
        "source_snapshot": {
            "primary_direction": _direction(primary.get("direction")),
            "peer_adjustment": str(peer.get("adjustment") or "unknown"),
            "historical_bias": str(historical.get("historical_bias") or "unknown"),
            "preflight_rules_count": preflight_count,
        },
        "direction": "unknown",
        "confidence": "unknown",
        "preflight_influence": {
            "matched_rule_count": 0,
            "applied_effects": [],
            "summary": "未命中会影响最终结论的历史规则。",
        },
    }


def _history_contribution(historical: dict[str, Any]) -> str:
    bias = str(historical.get("historical_bias") or "missing")
    impact = str(historical.get("impact") or "missing")
    if historical.get("ready") and impact == "support":
        return f"历史概率层支持当前方向，bias={bias}。"
    if impact == "caution":
        return f"历史概率层给出 caution，bias={bias}。"
    return "未获得历史概率支持。"


def _peer_contribution(peer: dict[str, Any]) -> str:
    adjustment = str(peer.get("adjustment") or "missing")
    if peer.get("ready"):
        if adjustment == "downgrade":
            return "peer 修正削弱主分析置信度。"
        if adjustment in {"reinforce_bullish", "reinforce_bearish"}:
            return "peer 修正强化主分析方向。"
        return "peer 修正保持 no_change。"
    return "未获 peers 确认。"


def _risk_level(
    *,
    primary_confidence: str,
    peer_missing: bool,
    peer_adjustment: str,
    historical_impact: str,
    historical_bias: str,
) -> str:
    if peer_missing and historical_impact == "missing":
        return "high"
    if peer_adjustment == "downgrade":
        return "medium" if historical_impact == "support" else "high"
    if historical_impact == "caution" or historical_bias in {"mixed", "insufficient", "missing"}:
        return "medium"
    if historical_impact == "missing":
        return "medium"
    if primary_confidence == "high":
        return "low"
    return "medium"


def _why_not_more(
    *,
    primary_direction: str,
    peer_missing: bool,
    peer_adjustment: str,
    historical_impact: str,
    historical_bias: str,
    preflight_missing: bool,
) -> str:
    reasons: list[str] = []
    if primary_direction == "中性":
        reasons.append("主分析信号混杂")
    if peer_missing:
        reasons.append("未获 peers 确认")
    elif peer_adjustment == "downgrade":
        reasons.append("同业未确认或偏弱")
    elif peer_adjustment == "no_change":
        reasons.append("peers 未提供额外强化")
    if historical_impact == "missing" or historical_bias in {"insufficient", "missing"}:
        reasons.append("历史样本不足或不可形成可靠倾向")
    elif historical_impact == "caution" or historical_bias == "mixed":
        reasons.append("历史样本混杂或与主方向不完全一致")
    if preflight_missing:
        reasons.append("未接入规则前置提醒")
    if not reasons:
        return "主分析、peers 与历史层基本一致；MVP 决策层不做更激进加权。"
    return "；".join(reasons) + "。"


def build_final_decision(
    *,
    primary_analysis: dict[str, Any],
    peer_adjustment: dict[str, Any] | None = None,
    historical_probability: dict[str, Any] | None = None,
    preflight: dict[str, Any] | None = None,
    symbol: str = "AVGO",
) -> dict[str, Any]:
    """Aggregate projection v2 layers into a stable final decision."""
    normalized_symbol = str(symbol or "AVGO").strip().upper() or "AVGO"
    primary = _as_dict(primary_analysis)
    peer = _as_dict(peer_adjustment)
    historical = _as_dict(historical_probability)
    preflight_layer = _as_dict(preflight)

    if not primary.get("ready") or _direction(primary.get("direction")) == "unknown":
        return _primary_missing_result(
            symbol=normalized_symbol,
            primary=primary,
            peer=peer,
            historical=historical,
            preflight=preflight_layer,
        )

    primary_direction = _direction(primary.get("direction"))
    primary_confidence = _confidence(primary.get("confidence"))
    peer_ready = bool(peer.get("ready"))
    peer_adjustment_label = str(peer.get("adjustment") or "missing")
    peer_missing = not peer_ready or peer_adjustment_label == "missing"
    historical_ready = bool(historical.get("ready"))
    historical_impact = str(historical.get("impact") or "missing")
    historical_bias = str(historical.get("historical_bias") or "missing")
    preflight_count = _preflight_rules_count(preflight_layer)
    preflight_missing = not preflight_layer or (
        preflight_count == 0 and not preflight_layer.get("matched_rules")
    )

    final_direction = primary_direction
    if (
        primary_direction in {"偏多", "偏空"}
        and peer_adjustment_label == "downgrade"
        and _direction(peer.get("adjusted_direction")) == "中性"
    ):
        final_direction = "中性"

    score = _confidence_score(primary_confidence)
    if primary_direction == "中性":
        score = min(score, 1)
    elif peer_adjustment_label in {"reinforce_bullish", "reinforce_bearish"} and historical_impact == "support":
        score += 1
    elif peer_adjustment_label == "downgrade":
        score -= 1

    if historical_impact == "caution":
        score -= 1
    elif historical_impact == "missing":
        score -= 1

    if peer_missing and historical_impact == "missing":
        score = min(score, 1)

    final_confidence = _confidence_from_score(score)
    risk_level = _risk_level(
        primary_confidence=final_confidence,
        peer_missing=peer_missing,
        peer_adjustment=peer_adjustment_label,
        historical_impact=historical_impact,
        historical_bias=historical_bias,
    )

    # Apply preflight rule influence (confidence −1 / risk +1, capped at one step each)
    matched_rules: list[Any] = list(preflight_layer.get("matched_rules") or [])
    final_confidence, risk_level, preflight_influence = _apply_preflight_influence(
        matched_rules, final_confidence, risk_level
    )

    warnings: list[str] = []
    if peer_missing:
        warnings.append("final_decision 未获 peers 确认。")
    if not historical_ready or historical_impact == "missing":
        warnings.append("final_decision 未获历史样本支持。")
    if preflight_missing:
        warnings.append("final_decision 未接入规则前置提醒或未命中规则。")

    _preflight_contrib = (
        f"preflight 命中 {preflight_count} 条提醒。"
        + (f" {preflight_influence['summary']}" if preflight_influence["applied_effects"] else "")
        if preflight_count
        else "preflight 未命中规则或未接入可用提醒。"
    )
    layer_contributions = {
        "primary": f"主分析给出 {primary_direction}，置信度 {primary_confidence}，作为主判断来源。",
        "peer": _peer_contribution(peer),
        "historical": _history_contribution(historical),
        "preflight": _preflight_contrib,
    }
    why_not_more = _why_not_more(
        primary_direction=primary_direction,
        peer_missing=peer_missing,
        peer_adjustment=peer_adjustment_label,
        historical_impact=historical_impact,
        historical_bias=historical_bias,
        preflight_missing=preflight_missing,
    )
    if preflight_influence["applied_effects"]:
        why_not_more += f" 历史规则约束：{preflight_influence['summary']}"
    decision_factors = [
        layer_contributions["primary"],
        layer_contributions["peer"],
        layer_contributions["historical"],
        layer_contributions["preflight"],
        f"约束说明：{why_not_more}",
    ]
    summary = (
        f"最终结论：方向{final_direction}，置信度{final_confidence}，风险{risk_level}。"
        f"{layer_contributions['primary']} {layer_contributions['peer']} "
        f"{layer_contributions['historical']} 约束：{why_not_more}"
    )

    return {
        "kind": "final_decision",
        "symbol": normalized_symbol,
        "ready": True,
        "final_direction": final_direction,
        "final_confidence": final_confidence,
        "risk_level": risk_level,
        "summary": summary,
        "decision_factors": decision_factors,
        "warnings": warnings,
        "layer_contributions": layer_contributions,
        "why_not_more_bullish_or_bearish": why_not_more,
        "source_snapshot": {
            "primary_direction": primary_direction,
            "peer_adjustment": peer_adjustment_label,
            "historical_bias": historical_bias,
            "preflight_rules_count": preflight_count,
        },
        "direction": final_direction,
        "confidence": final_confidence,
        "preflight_influence": preflight_influence,
    }
