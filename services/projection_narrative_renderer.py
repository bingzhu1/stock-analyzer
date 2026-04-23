"""Render projection_v2 raw output into a fixed Chinese trading narrative."""

from __future__ import annotations

from typing import Any


_DIRECTIONS = {"偏多", "偏空", "中性"}
_CONFIDENCE = {"low", "medium", "high", "unknown"}
_RISK = {"low", "medium", "high"}
_HISTORICAL_BIAS = {
    "supports_bullish",
    "supports_bearish",
    "mixed",
    "insufficient",
    "missing",
}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _clean_str(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"none", "null"} else text


def _unique(items: list[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        text = _clean_str(item)
        if text and text not in seen:
            seen.append(text)
    return seen


def _direction(value: Any) -> str:
    text = _clean_str(value)
    return text if text in _DIRECTIONS else "unknown"


def _confidence(value: Any) -> str:
    text = _clean_str(value).lower()
    return text if text in _CONFIDENCE else "unknown"


def _risk(value: Any) -> str:
    text = _clean_str(value).lower()
    return text if text in _RISK else "medium"


def _historical_bias(value: Any) -> str:
    text = _clean_str(value).lower()
    return text if text in _HISTORICAL_BIAS else "missing"


def _historical_impact(value: Any) -> str:
    text = _clean_str(value).lower()
    return text if text in {"support", "caution", "missing", "no_effect"} else "missing"


def _rule_line(rule: Any) -> str:
    if isinstance(rule, dict):
        message = _clean_str(rule.get("message"))
        title = _clean_str(rule.get("title"))
        rule_id = _clean_str(rule.get("rule_id"))
        category = _clean_str(rule.get("category"))
        parts = [part for part in (message, title, rule_id, category) if part]
        return " / ".join(parts) if parts else "命中历史规则"
    return _clean_str(rule)


def _preflight_signal(preflight: dict[str, Any], final: dict[str, Any]) -> dict[str, Any]:
    influence = _as_dict(final.get("preflight_influence"))
    influence_count = 0
    try:
        influence_count = max(int(influence.get("matched_rule_count") or 0), 0)
    except (TypeError, ValueError):
        influence_count = 0

    influence_summary = _clean_str(influence.get("summary"))
    matched_rules = _as_list(preflight.get("matched_rules"))
    rule_warnings = _unique([_clean_str(item) for item in _as_list(preflight.get("rule_warnings"))])
    raw_rule_lines = _unique([_rule_line(rule) for rule in matched_rules if _rule_line(rule)])
    raw_summary = _clean_str(preflight.get("summary"))

    has_raw_signal = bool(matched_rules or rule_warnings)
    if influence_count > 0:
        summary = influence_summary or raw_summary
    elif has_raw_signal:
        if raw_summary and "未命中" not in raw_summary and "未接入" not in raw_summary:
            summary = raw_summary
        elif rule_warnings:
            summary = rule_warnings[0]
        elif raw_rule_lines:
            summary = f"命中历史规则：{raw_rule_lines[0]}"
        else:
            summary = ""
    else:
        summary = ""

    details = _unique([*rule_warnings, *raw_rule_lines])
    return {
        "summary": summary,
        "details": details,
        "has_signal": bool(influence_count > 0 or has_raw_signal),
    }


def _primary_regime(primary: dict[str, Any]) -> str:
    direction = _direction(primary.get("direction"))
    stage = _clean_str(primary.get("stage_label"))

    if direction == "偏多":
        if stage in {"启动", "加速"}:
            return "强攻"
        if stage in {"延续", "整理"}:
            return "弱修复" if stage == "整理" else "偏多延续"
        return "弱修复"
    if direction == "偏空":
        if stage == "衰竭风险":
            return "高位转弱"
        return "延续回落"
    if direction == "中性":
        return "区间震荡"
    return "主分析不可用"


def _final_regime(
    *,
    direction: str,
    risk_level: str,
    peer_adjustment: str,
    historical_bias: str,
    historical_impact: str,
) -> str:
    if direction == "偏多":
        if peer_adjustment == "reinforce_bullish" and historical_impact == "support" and risk_level == "low":
            return "偏多延续"
        if peer_adjustment == "downgrade" or risk_level == "high":
            return "弱修复"
        if historical_bias in {"mixed", "insufficient", "missing"}:
            return "震荡偏多"
        return "弱修复"
    if direction == "偏空":
        if peer_adjustment == "reinforce_bearish" and historical_impact == "support":
            return "延续偏弱"
        if risk_level == "high" or historical_bias in {"insufficient", "missing"}:
            return "偏弱整理"
        return "延续回落"
    if direction == "中性":
        return "区间整理"
    return "保守观察"


def _step1_conclusion(symbol: str, primary: dict[str, Any]) -> str:
    if not primary.get("ready"):
        summary = _clean_str(primary.get("summary")) or "当前主分析不可用。"
        return f"Step 1 只看 {symbol} 本身，当前主分析不可用；{summary} 先按保守观察处理。"

    regime = _primary_regime(primary)
    summary = _clean_str(primary.get("summary")) or "最近20天主分析已完成。"
    position = _clean_str(primary.get("position_label")) or "未知位置"
    stage = _clean_str(primary.get("stage_label")) or "未知阶段"
    volume = _clean_str(primary.get("volume_state")) or "未知量能"
    return (
        f"Step 1 只看 {symbol} 本身，当前更像{regime}；"
        f"{summary} 位置在{position}，阶段偏{stage}，量能状态为{volume}。"
    )


def _step2_peer_adjustment(peer: dict[str, Any]) -> str:
    summary = _clean_str(peer.get("summary"))
    adjustment = _clean_str(peer.get("adjustment"))
    confirmation = _clean_str(peer.get("confirmation_level"))

    if not peer.get("ready") or adjustment in {"missing", "unknown", ""}:
        detail = summary or "当前未获 peers 确认。"
        return f"Step 2 peers 修正：{detail} 暂时不能据此判断同业是在支持还是拖累当前判断。"
    if adjustment == "reinforce_bullish":
        return (
            f"Step 2 peers 修正：{summary or 'peers 支持主分析偏多。'} "
            f"这说明同业更偏托底，当前强弱不只是个股单点信号，确认度为{confirmation or 'confirmed'}。"
        )
    if adjustment == "reinforce_bearish":
        return (
            f"Step 2 peers 修正：{summary or 'peers 支持主分析偏空。'} "
            f"这说明弱势更偏系统性，确认度为{confirmation or 'confirmed'}。"
        )
    if adjustment == "downgrade":
        return (
            f"Step 2 peers 修正：{summary or 'peers 未充分确认主分析方向。'} "
            "当前不能把主判断说得过满，更像需要下调一档乐观度或悲观度。"
        )
    return (
        f"Step 2 peers 修正：{summary or 'peers 未改变主分析方向。'} "
        "同业没有额外强化，也没有形成明显拖累。"
    )


def _final_judgment(
    *,
    preflight: dict[str, Any],
    final: dict[str, Any],
    peer: dict[str, Any],
    historical: dict[str, Any],
) -> str:
    ready = bool(final.get("ready"))
    direction = _direction(final.get("final_direction") or final.get("direction"))
    risk_level = _risk(final.get("risk_level"))
    peer_adjustment = _clean_str(peer.get("adjustment"))
    bias = _historical_bias(historical.get("historical_bias"))
    impact = _historical_impact(historical.get("impact"))
    why_not_more = _clean_str(final.get("why_not_more_bullish_or_bearish"))
    preflight_signal = _preflight_signal(preflight, final)
    preflight_summary = _clean_str(preflight_signal.get("summary"))

    if not ready:
        base = "最终主判断暂未就绪，先按保守场景处理，不宜把这次结果当成强交易信号。"
    else:
        regime = _final_regime(
            direction=direction,
            risk_level=risk_level,
            peer_adjustment=peer_adjustment,
            historical_bias=bias,
            historical_impact=impact,
        )
        if direction == "偏多":
            if regime == "偏多延续":
                base = "最终主判断更像偏多延续，可以看作偏强场景，而不是单纯弱反弹。"
            elif regime == "弱修复":
                base = "最终主判断更像弱修复，不是强反转。"
            else:
                base = "最终主判断偏多但仍以震荡修复看待，不宜直接上调成强趋势。"
        elif direction == "偏空":
            if regime == "延续偏弱":
                base = "最终主判断更像延续偏弱，不是简单洗盘。"
            elif regime == "偏弱整理":
                base = "最终主判断当前偏弱，但未必立刻演化成单边失守。"
            else:
                base = "最终主判断更像延续回落，反抽更偏交易性而不是趋势反转。"
        elif direction == "中性":
            base = "最终主判断更像区间整理，暂不支持单边押注。"
        else:
            base = "最终主判断暂不明确，先按保守观察处理。"

    constraints: list[str] = []
    if why_not_more:
        constraints.append(why_not_more)
    if preflight_signal.get("has_signal") and preflight_summary:
        constraints.append(f"历史规则提醒：{preflight_summary}")
    elif preflight_signal.get("has_signal"):
        constraints.append("历史规则提醒仍在生效")
    if bias in {"insufficient", "missing"}:
        constraints.append("历史样本不足，不宜过度依赖统计支持")
    if constraints:
        base += " 保留条件：" + "；".join(_unique(constraints)) + "。"
    return base


def _open_tendency(final: dict[str, Any], peer: dict[str, Any], historical: dict[str, Any]) -> str:
    direction = _direction(final.get("final_direction") or final.get("direction"))
    risk_level = _risk(final.get("risk_level"))
    adjustment = _clean_str(peer.get("adjustment"))
    bias = _historical_bias(historical.get("historical_bias"))

    if direction == "偏多":
        if adjustment == "reinforce_bullish" and bias == "supports_bullish" and risk_level == "low":
            return "开盘更偏向小幅高开或平开后偏强。"
        if adjustment == "downgrade" or risk_level == "high":
            return "开盘更偏向平开偏弱，承接差时不排除先小幅低开。"
        return "开盘更偏向平开偏强。"
    if direction == "偏空":
        if adjustment == "reinforce_bearish" or bias == "supports_bearish":
            return "开盘更偏向小幅低开或平开偏弱。"
        if risk_level == "high":
            return "开盘更偏向低开试探。"
        return "开盘更偏向平开偏弱。"
    if direction == "中性":
        return "开盘更偏向平开震荡。"
    return "开盘倾向暂不明确，先按保守观察。"


def _intraday_structure(final: dict[str, Any], peer: dict[str, Any], historical: dict[str, Any]) -> str:
    direction = _direction(final.get("final_direction") or final.get("direction"))
    risk_level = _risk(final.get("risk_level"))
    adjustment = _clean_str(peer.get("adjustment"))
    impact = _historical_impact(historical.get("impact"))

    if direction == "偏多":
        if adjustment == "reinforce_bullish" and impact == "support" and risk_level == "low":
            return "日内更像先整理再上拱，强一点时有延续上冲机会。"
        if adjustment == "downgrade" or risk_level == "high":
            return "日内更像先下探再反抽，整体仍以弱修复整理为主。"
        return "日内更像震荡偏强，回踩后看承接。"
    if direction == "偏空":
        if adjustment == "reinforce_bearish" or impact == "support":
            return "日内更像先反抽再回落，重心偏下。"
        if risk_level == "high":
            return "日内更像弱势下探，若承接不足容易延续回落。"
        return "日内更像偏弱整理，反抽力度有限。"
    if direction == "中性":
        return "日内更像区间震荡，来回拉扯。"
    return "日内结构暂不明确。"


def _close_tendency(final: dict[str, Any], historical: dict[str, Any]) -> str:
    direction = _direction(final.get("final_direction") or final.get("direction"))
    risk_level = _risk(final.get("risk_level"))
    combined = _as_dict(historical.get("combined_probability"))
    strong_close_rate = combined.get("strong_close_rate")

    try:
        strong_close = float(strong_close_rate) if strong_close_rate is not None else None
    except (TypeError, ValueError):
        strong_close = None
    if strong_close is not None and strong_close > 1 and strong_close <= 100:
        strong_close = strong_close / 100
    if strong_close is not None and (strong_close < 0 or strong_close > 1):
        strong_close = None

    if direction == "偏多":
        if strong_close is not None and strong_close >= 0.6 and risk_level != "high":
            return "收盘更可能落在偏强区间，暂不输出具体价格区间。"
        if risk_level == "high":
            return "收盘更可能落在弱修复区间，暂不输出具体价格区间。"
        return "收盘更可能落在震荡偏强区间，暂不输出具体价格区间。"
    if direction == "偏空":
        return "收盘更可能落在偏弱区间，暂不输出具体价格区间。"
    if direction == "中性":
        return "收盘更可能落在震荡区间中部，暂不输出具体价格区间。"
    return "收盘倾向暂不明确，暂不输出具体价格区间。"


def _watchpoints(
    *,
    preflight: dict[str, Any],
    final: dict[str, Any],
    peer: dict[str, Any],
    historical: dict[str, Any],
) -> dict[str, list[str]]:
    direction = _direction(final.get("final_direction") or final.get("direction"))
    risk_level = _risk(final.get("risk_level"))
    adjustment = _clean_str(peer.get("adjustment"))
    bias = _historical_bias(historical.get("historical_bias"))
    impact = _historical_impact(historical.get("impact"))
    preflight_signal = _preflight_signal(preflight, final)
    preflight_summary = _clean_str(preflight_signal.get("summary"))

    stronger_case: list[str] = []
    weaker_case: list[str] = []

    if direction == "偏多":
        stronger_case.append("若开盘不弱且回踩后仍有承接，弱修复才有机会升级成更强延续。")
    elif direction == "偏空":
        stronger_case.append("若早盘下探后能迅速收回，当前偏弱判断才可能向整理过渡。")
    else:
        stronger_case.append("若盘中能走出明确方向并持续维持，区间整理判断才会被上修。")

    if adjustment in {"reinforce_bullish", "reinforce_bearish"}:
        stronger_case.append("NVDA / SOXX / QQQ 至少要继续同向确认，不能中途掉队。")
    else:
        stronger_case.append("同业至少不能继续背离，否则当前判断很难上修。")

    if impact == "support":
        stronger_case.append("历史统计支持只有在盘中节奏被兑现时才算有效，不能只靠早盘一笔冲动。")
    else:
        stronger_case.append("没有稳定历史支持时，只有连续承接出现，场景才会向更强方向演变。")

    if direction == "偏空":
        weaker_case.append("若反抽无量且日内重心继续下移，弱势延续概率会上升。")
    else:
        weaker_case.append("若开盘后承接继续不足，日内更容易回到偏弱整理。")

    if adjustment in {"downgrade", "missing", "unknown", ""}:
        weaker_case.append("若 peers 继续不确认，主判断要按一档更保守处理。")
    else:
        weaker_case.append("若 peers 转为背离，当前判断要重新降级。")

    if bias in {"insufficient", "missing", "mixed"}:
        weaker_case.append("历史样本不足或混杂时，任何单边异动都不宜过度放大。")
    else:
        weaker_case.append("即便历史支持存在，一旦盘中走法背离样本，也要回到保守解释。")

    if risk_level == "high":
        weaker_case.append("当前风险等级偏高，失去关键承接后容易快速走弱。")
    if preflight_signal.get("has_signal") and preflight_summary:
        weaker_case.append(f"历史规则提醒仍在生效：{preflight_summary}")
    elif preflight_signal.get("has_signal"):
        weaker_case.append("历史规则提醒仍在生效，当前判断不能脱离既有规则约束。")

    return {
        "stronger_case": _unique(stronger_case)[:4],
        "weaker_case": _unique(weaker_case)[:5],
    }


def _warnings(v2: dict[str, Any], preflight: dict[str, Any], primary: dict[str, Any], peer: dict[str, Any], historical: dict[str, Any], final: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    for source in (v2, preflight, primary, peer, historical, final):
        for warning in _as_list(_as_dict(source).get("warnings")):
            text = _clean_str(warning)
            if text:
                warnings.append(text)
    return _unique(warnings)


def build_projection_narrative(
    *,
    projection_v2_raw: dict[str, Any] | None,
    market_context: dict[str, Any] | None = None,
    symbol: str = "AVGO",
    peer_market_snapshot: dict[str, Any] | None = None,
    support_resistance_levels: dict[str, Any] | None = None,
    locale: str = "zh-CN",
) -> dict[str, Any]:
    """Render projection v2 raw output into a stable narrative dict."""
    del market_context, peer_market_snapshot, support_resistance_levels, locale

    v2 = _as_dict(projection_v2_raw)
    normalized_symbol = _clean_str(v2.get("symbol")) or _clean_str(symbol) or "AVGO"
    preflight = _as_dict(v2.get("preflight"))
    primary = _as_dict(v2.get("primary_analysis"))
    peer = _as_dict(v2.get("peer_adjustment"))
    historical = _as_dict(v2.get("historical_probability"))
    final = _as_dict(v2.get("final_decision"))
    warnings = _warnings(v2, preflight, primary, peer, historical, final)

    if _historical_bias(historical.get("historical_bias")) in {"insufficient", "missing"}:
        warnings = _unique([*warnings, "历史样本不足，不宜过度依赖统计支持。"])
    if not final.get("ready"):
        warnings = _unique([*warnings, "最终结论未完全就绪，narrative 已按保守路径降级。"])

    step1 = _step1_conclusion(normalized_symbol, primary)
    step2 = _step2_peer_adjustment(peer)
    final_judgment = _final_judgment(preflight=preflight, final=final, peer=peer, historical=historical)
    open_tendency = _open_tendency(final, peer, historical)
    intraday_structure = _intraday_structure(final, peer, historical)
    close_tendency = _close_tendency(final, historical)
    watchpoints = _watchpoints(preflight=preflight, final=final, peer=peer, historical=historical)

    one_line_parts = [
        _clean_str(final_judgment),
        _clean_str(open_tendency),
        _clean_str(intraday_structure),
        _clean_str(close_tendency),
    ]

    return {
        "kind": "projection_narrative",
        "symbol": normalized_symbol,
        "ready": bool(v2.get("ready")) and bool(final.get("ready")),
        "step1_conclusion": step1,
        "step2_peer_adjustment": step2,
        "final_judgment": final_judgment,
        "open_tendency": open_tendency,
        "intraday_structure": intraday_structure,
        "close_tendency": close_tendency,
        "key_watchpoints": {
            "stronger_case": watchpoints["stronger_case"],
            "weaker_case": watchpoints["weaker_case"],
        },
        "one_line_summary": " ".join(part for part in one_line_parts if part),
        "warnings": warnings,
    }


render_projection_narrative = build_projection_narrative
