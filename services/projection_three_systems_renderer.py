"""Three-system view of projection v2 raw output.

This module reshapes an existing ``projection_v2_raw`` payload into three
independent, structured systems:

    1. ``negative_system``           — what should NOT be considered
    2. ``record_02_projection_system`` — what the system thinks will happen
    3. ``confidence_evaluator``      — how reliable the first two are

It performs no scanning, prediction, or rule mutation. It only rephrases and
groups data already produced by the projection v2 chain.
"""

from __future__ import annotations

from typing import Any


_VALID_LEVELS = {"low", "medium", "high", "unknown"}
_LEVEL_TO_SCORE: dict[str, float | None] = {
    "low": 0.3,
    "medium": 0.6,
    "high": 0.9,
    "unknown": None,
}
_LEVEL_RANK = {"unknown": 0, "low": 1, "medium": 2, "high": 3}
_RANK_TO_LEVEL = {0: "unknown", 1: "low", 2: "medium", 3: "high"}

_BULLISH_STATES = {"大涨", "小涨"}
_BEARISH_STATES = {"大跌", "小跌"}


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

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


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_level(value: Any) -> str:
    text = _clean_str(value).lower()
    return text if text in _VALID_LEVELS else "unknown"


def _level_to_score(level: str) -> float | None:
    return _LEVEL_TO_SCORE.get(level)


def _missing_feature_count(feature_snapshot: dict[str, Any]) -> int:
    if not isinstance(feature_snapshot, dict) or not feature_snapshot:
        return 0
    return sum(1 for value in feature_snapshot.values() if value is None)


# ---------------------------------------------------------------------------
# Negative system
# ---------------------------------------------------------------------------

def _negative_excluded_states(triggered_rule: str) -> list[str]:
    if triggered_rule == "exclude_big_up":
        return ["大涨"]
    if triggered_rule == "exclude_big_down":
        return ["大跌"]
    return []


def _negative_strength(
    *,
    excluded: bool,
    reasons: list[str],
    feature_snapshot: dict[str, Any],
) -> str:
    missing = _missing_feature_count(feature_snapshot)
    reason_count = len(reasons)
    if excluded:
        if reason_count >= 4:
            return "high"
        if reason_count >= 3:
            return "medium"
        return "low"
    if reason_count >= 1:
        return "low"
    if missing >= 5:
        return "none"
    return "none"


def _invalidating_conditions(triggered_rule: str, peer_alignment: dict[str, Any]) -> list[str]:
    if triggered_rule == "exclude_big_up":
        return [
            "若 NVDA / SOXX / QQQ 同步翻强且配合放量突破，排除大涨结论需要重新评估。",
            "若上影压力消失并出现连续承接，原排除依据失效。",
            "若短期动量未透支转为新方向触发，原排除约束需要解除。",
        ]
    if triggered_rule == "exclude_big_down":
        return [
            "若关键支撑明确跌破且 peers 同步转弱，排除大跌结论需要重新评估。",
            "若放量但不弱的格局被打破，原排除依据失效。",
            "若短期修复不再延续转为快速失守，原排除约束需要解除。",
        ]
    if peer_alignment and peer_alignment.get("alignment") in {"bullish", "bearish"}:
        return ["当前未排除任何极端走势，仅在出现持续单边失守 / 突破时才需要重新评估。"]
    return ["当前未触发任何排除规则，没有需要监控的失效条件。"]


def _negative_risk_notes(
    *,
    feature_snapshot: dict[str, Any],
    peer_alignment: dict[str, Any],
    summary: str,
) -> list[str]:
    notes: list[str] = []
    missing = _missing_feature_count(feature_snapshot)
    if missing >= 5:
        notes.append("排除层关键特征大量缺失，否定结论可信度受限。")
    elif missing >= 3:
        notes.append("排除层部分特征缺失，否定结论可能不完整。")
    available_peers = peer_alignment.get("available_peer_count") if isinstance(peer_alignment, dict) else None
    if isinstance(available_peers, int) and available_peers == 0:
        notes.append("缺少 NVDA / SOXX / QQQ 同日强弱输入，否定结论缺少 peers 验证。")
    if summary and "降级" in summary:
        notes.append(summary)
    return _unique(notes)


def build_negative_system(v2_raw: dict[str, Any] | None) -> dict[str, Any]:
    v2 = _as_dict(v2_raw)
    exclusion = _as_dict(v2.get("exclusion_result"))
    final = _as_dict(v2.get("final_decision"))

    excluded = bool(exclusion.get("excluded"))
    triggered_rule = _clean_str(exclusion.get("triggered_rule"))
    summary = _clean_str(exclusion.get("summary"))
    reasons = _unique([_clean_str(item) for item in _as_list(exclusion.get("reasons"))])
    peer_alignment = _as_dict(exclusion.get("peer_alignment"))
    feature_snapshot = _as_dict(exclusion.get("feature_snapshot"))

    excluded_states = _negative_excluded_states(triggered_rule)
    strength = _negative_strength(
        excluded=excluded,
        reasons=reasons,
        feature_snapshot=feature_snapshot,
    )
    invalidating_conditions = _invalidating_conditions(triggered_rule, peer_alignment)
    risk_notes = _negative_risk_notes(
        feature_snapshot=feature_snapshot,
        peer_alignment=peer_alignment,
        summary=summary,
    )

    if excluded:
        if triggered_rule == "exclude_big_up":
            conclusion = "明天不太可能出现大涨，主流程应避免输出极端上冲结论。"
        elif triggered_rule == "exclude_big_down":
            conclusion = "明天不太可能出现大跌，主流程应避免输出极端下杀结论。"
        else:
            conclusion = summary or "排除层已触发，主流程应避免极端单边结论。"
    else:
        conclusion = summary or "当前没有形成对极端走势的强排除约束，主流程可继续推演。"

    why_not_more = _clean_str(final.get("why_not_more_bullish_or_bearish"))
    if why_not_more:
        risk_notes = _unique([*risk_notes, f"final_decision 约束：{why_not_more}"])

    return {
        "conclusion": conclusion,
        "excluded_states": excluded_states,
        "strength": strength,
        "evidence": reasons,
        "invalidating_conditions": invalidating_conditions,
        "risk_notes": risk_notes,
    }


# ---------------------------------------------------------------------------
# 02 record projection system
# ---------------------------------------------------------------------------

def _current_structure(primary: dict[str, Any]) -> str:
    if not primary.get("ready"):
        summary = _clean_str(primary.get("summary")) or "主分析不可用，无法描述当前结构。"
        return summary
    direction = _clean_str(primary.get("direction")) or "unknown"
    position = _clean_str(primary.get("position_label")) or "未知位置"
    stage = _clean_str(primary.get("stage_label")) or "未知阶段"
    volume = _clean_str(primary.get("volume_state")) or "未知量能"
    return (
        f"当前结构：方向{direction}，位置{position}，阶段{stage}，量能{volume}。"
    )


def _main_projection_text(final: dict[str, Any]) -> str:
    if not final.get("ready"):
        return _clean_str(final.get("summary")) or "最终主推演未就绪。"
    direction = _clean_str(final.get("final_direction") or final.get("direction")) or "unknown"
    confidence = _clean_str(final.get("final_confidence") or final.get("confidence")) or "unknown"
    risk_level = _clean_str(final.get("risk_level")) or "unknown"
    summary = _clean_str(final.get("summary"))
    base = f"主推演：方向{direction}，置信度{confidence}，风险{risk_level}。"
    if summary:
        return f"{base} {summary}"
    return base


def _five_state_projection(main_projection: dict[str, Any]) -> dict[str, float]:
    distribution = _as_dict(main_projection.get("state_probabilities"))
    output: dict[str, float] = {}
    for state, value in distribution.items():
        prob = _safe_float(value)
        if prob is None:
            continue
        output[str(state)] = prob
    return output


def _open_path_close(final: dict[str, Any]) -> dict[str, str]:
    direction = _clean_str(final.get("final_direction") or final.get("direction")) or "unknown"
    risk_level = _clean_str(final.get("risk_level")).lower()

    if not final.get("ready") or direction == "unknown":
        return {
            "open": "开盘倾向暂不明确，先按保守观察处理。",
            "intraday": "日内结构暂不明确，先按区间整理处理。",
            "close": "收盘倾向暂不明确，不输出具体价格区间。",
        }

    if direction == "偏多":
        if risk_level == "high":
            open_text = "开盘更偏向平开偏弱或先小幅低开后试探。"
            intraday_text = "日内更偏先下探再反抽，整体仍以弱修复为主。"
            close_text = "收盘更可能落在弱修复区间，不输出具体价格区间。"
        else:
            open_text = "开盘更偏向平开偏强。"
            intraday_text = "日内更像震荡偏强，回踩后看承接。"
            close_text = "收盘更可能落在偏强区间，不输出具体价格区间。"
    elif direction == "偏空":
        if risk_level == "high":
            open_text = "开盘更偏向小幅低开试探。"
            intraday_text = "日内偏弱下探，承接不足时容易延续回落。"
            close_text = "收盘更可能落在偏弱区间，不输出具体价格区间。"
        else:
            open_text = "开盘更偏向平开偏弱。"
            intraday_text = "日内偏弱整理，反抽力度有限。"
            close_text = "收盘更可能落在偏弱区间，不输出具体价格区间。"
    else:
        open_text = "开盘更偏向平开震荡。"
        intraday_text = "日内更像区间震荡，来回拉扯。"
        close_text = "收盘更可能落在震荡区间中部，不输出具体价格区间。"

    return {"open": open_text, "intraday": intraday_text, "close": close_text}


def _historical_sample_summary(historical: dict[str, Any]) -> str:
    summary = _clean_str(historical.get("summary"))
    if summary:
        return summary
    sample_count = historical.get("sample_count")
    sample_quality = _clean_str(historical.get("sample_quality")) or "unknown"
    bias = _clean_str(historical.get("historical_bias")) or "unknown"
    if isinstance(sample_count, int):
        return f"历史概率层：样本 {sample_count}，质量 {sample_quality}，偏向 {bias}。"
    return "历史概率层未返回摘要。"


def _peer_market_confirmation(peer: dict[str, Any]) -> str:
    summary = _clean_str(peer.get("summary"))
    if summary:
        return summary
    if not peer.get("ready"):
        return "未获 peers 确认。"
    adjustment = _clean_str(peer.get("adjustment")) or "unknown"
    confirmation = _clean_str(peer.get("confirmation_level")) or "unknown"
    return f"peer 修正：adjustment={adjustment}，confirmation={confirmation}。"


def _projection_risk_notes(
    *,
    final: dict[str, Any],
    primary: dict[str, Any],
    peer: dict[str, Any],
    historical: dict[str, Any],
    main_projection: dict[str, Any],
    consistency: dict[str, Any],
) -> list[str]:
    notes: list[str] = []
    for source in (primary, peer, historical, final, main_projection, consistency):
        for warning in _as_list(source.get("warnings")):
            text = _clean_str(warning)
            if text:
                notes.append(text)
    consistency_summary = _clean_str(consistency.get("summary"))
    if consistency_summary and consistency.get("consistency_flag") not in {"consistent", "unknown", None}:
        notes.append(f"一致性提醒：{consistency_summary}")
    why_not_more = _clean_str(final.get("why_not_more_bullish_or_bearish"))
    if why_not_more:
        notes.append(f"约束说明：{why_not_more}")
    return _unique(notes)


def _final_summary_text(final: dict[str, Any]) -> str:
    summary = _clean_str(final.get("summary"))
    if summary:
        return summary
    if final.get("ready"):
        direction = _clean_str(final.get("final_direction")) or "unknown"
        confidence = _clean_str(final.get("final_confidence")) or "unknown"
        return f"最终结论：方向{direction}，置信度{confidence}。"
    return "最终结论暂未就绪。"


def build_record_02_projection_system(v2_raw: dict[str, Any] | None) -> dict[str, Any]:
    v2 = _as_dict(v2_raw)
    primary = _as_dict(v2.get("primary_analysis"))
    peer = _as_dict(v2.get("peer_adjustment"))
    historical = _as_dict(v2.get("historical_probability"))
    final = _as_dict(v2.get("final_decision"))
    main_projection = _as_dict(v2.get("main_projection"))
    consistency = _as_dict(v2.get("consistency"))

    return {
        "current_structure": _current_structure(primary),
        "main_projection": _main_projection_text(final),
        "five_state_projection": _five_state_projection(main_projection),
        "open_path_close_projection": _open_path_close(final),
        "historical_sample_summary": _historical_sample_summary(historical),
        "peer_market_confirmation": _peer_market_confirmation(peer),
        "key_price_levels": [],
        "risk_notes": _projection_risk_notes(
            final=final,
            primary=primary,
            peer=peer,
            historical=historical,
            main_projection=main_projection,
            consistency=consistency,
        ),
        "final_summary": _final_summary_text(final),
    }


# ---------------------------------------------------------------------------
# Confidence evaluator
# ---------------------------------------------------------------------------

def _negative_confidence_level(
    *,
    excluded: bool,
    reasons_count: int,
    feature_snapshot: dict[str, Any],
) -> str:
    missing = _missing_feature_count(feature_snapshot)
    if missing >= 5:
        return "unknown"
    if excluded:
        if reasons_count >= 4:
            return "high"
        if reasons_count >= 3:
            return "medium"
        return "low"
    if missing <= 1:
        return "high"
    if missing <= 3:
        return "medium"
    return "low"


def _negative_confidence_reasoning(
    *,
    excluded: bool,
    reasons: list[str],
    feature_snapshot: dict[str, Any],
) -> list[str]:
    out: list[str] = []
    missing = _missing_feature_count(feature_snapshot)
    total = len(feature_snapshot) if feature_snapshot else 0
    if total:
        out.append(f"特征完整度：缺失 {missing} / {total}。")
    if excluded:
        out.append(f"排除层已触发，证据条数：{len(reasons)}。")
    else:
        out.append("排除层未触发任何极端约束。")
    if reasons:
        out.append(f"主要证据：{reasons[0]}")
    return _unique(out)


def _negative_confidence_risks(
    *,
    feature_snapshot: dict[str, Any],
    peer_alignment: dict[str, Any],
) -> list[str]:
    risks: list[str] = []
    missing = _missing_feature_count(feature_snapshot)
    if missing >= 3:
        risks.append("排除层特征缺失较多，否定结论稳定性受限。")
    if isinstance(peer_alignment, dict) and peer_alignment.get("available_peer_count") == 0:
        risks.append("无 peers 输入，否定结论失去同业验证。")
    return _unique(risks)


def build_negative_system_confidence(v2_raw: dict[str, Any] | None) -> dict[str, Any]:
    v2 = _as_dict(v2_raw)
    exclusion = _as_dict(v2.get("exclusion_result"))
    excluded = bool(exclusion.get("excluded"))
    reasons = _unique([_clean_str(item) for item in _as_list(exclusion.get("reasons"))])
    feature_snapshot = _as_dict(exclusion.get("feature_snapshot"))
    peer_alignment = _as_dict(exclusion.get("peer_alignment"))

    level = _negative_confidence_level(
        excluded=excluded,
        reasons_count=len(reasons),
        feature_snapshot=feature_snapshot,
    )
    return {
        "score": _level_to_score(level),
        "level": level,
        "reasoning": _negative_confidence_reasoning(
            excluded=excluded,
            reasons=reasons,
            feature_snapshot=feature_snapshot,
        ),
        "risks": _negative_confidence_risks(
            feature_snapshot=feature_snapshot,
            peer_alignment=peer_alignment,
        ),
    }


def _projection_confidence_reasoning(
    *,
    final: dict[str, Any],
    step_status: dict[str, Any],
) -> list[str]:
    reasoning: list[str] = []
    layer_contributions = _as_dict(final.get("layer_contributions"))
    for key in ("primary", "peer", "historical", "preflight"):
        text = _clean_str(layer_contributions.get(key))
        if text:
            reasoning.append(text)
    statuses = [
        f"{step}={status}"
        for step, status in step_status.items()
        if isinstance(status, str)
    ]
    if statuses:
        reasoning.append("step_status：" + " / ".join(statuses))
    return _unique(reasoning)


def _projection_confidence_risks(
    *,
    final: dict[str, Any],
    primary: dict[str, Any],
    peer: dict[str, Any],
    historical: dict[str, Any],
    step_status: dict[str, Any],
) -> list[str]:
    risks: list[str] = []
    for source in (primary, peer, historical, final):
        for warning in _as_list(source.get("warnings")):
            text = _clean_str(warning)
            if text:
                risks.append(text)
    risk_level = _clean_str(final.get("risk_level")).lower()
    if risk_level == "high":
        risks.append("final_decision 风险等级偏高，主推演稳定性下降。")
    for step, status in step_status.items():
        if isinstance(status, str) and status not in {"success", ""}:
            risks.append(f"步骤 {step} 状态为 {status}。")
    return _unique(risks)


def build_projection_system_confidence(v2_raw: dict[str, Any] | None) -> dict[str, Any]:
    v2 = _as_dict(v2_raw)
    final = _as_dict(v2.get("final_decision"))
    primary = _as_dict(v2.get("primary_analysis"))
    peer = _as_dict(v2.get("peer_adjustment"))
    historical = _as_dict(v2.get("historical_probability"))
    step_status = _as_dict(v2.get("step_status"))

    if not final.get("ready"):
        level = "unknown"
    else:
        level = _normalize_level(final.get("final_confidence") or final.get("confidence"))

    return {
        "score": _level_to_score(level),
        "level": level,
        "reasoning": _projection_confidence_reasoning(
            final=final,
            step_status=step_status,
        ),
        "risks": _projection_confidence_risks(
            final=final,
            primary=primary,
            peer=peer,
            historical=historical,
            step_status=step_status,
        ),
    }


def _conservative_combine(level_a: str, level_b: str) -> str:
    rank = min(_LEVEL_RANK.get(level_a, 0), _LEVEL_RANK.get(level_b, 0))
    return _RANK_TO_LEVEL.get(rank, "unknown")


def _conflicts_from_v2(v2: dict[str, Any]) -> list[str]:
    conflicts: list[str] = []
    consistency = _as_dict(v2.get("consistency"))
    for reason in _as_list(consistency.get("conflict_reasons")):
        text = _clean_str(reason)
        if text:
            conflicts.append(text)

    exclusion = _as_dict(v2.get("exclusion_result"))
    main_projection = _as_dict(v2.get("main_projection"))
    if exclusion.get("excluded"):
        triggered_rule = _clean_str(exclusion.get("triggered_rule"))
        top1 = _as_dict(main_projection.get("predicted_top1"))
        top1_state = _clean_str(top1.get("state"))
        if triggered_rule == "exclude_big_up" and top1_state == "大涨":
            conflicts.append("否定系统排除大涨，但 main_projection top1 仍为大涨。")
        if triggered_rule == "exclude_big_down" and top1_state == "大跌":
            conflicts.append("否定系统排除大跌，但 main_projection top1 仍为大跌。")

    final = _as_dict(v2.get("final_decision"))
    final_direction = _clean_str(final.get("final_direction") or final.get("direction"))
    excluded_states = []
    if exclusion.get("excluded"):
        rule = _clean_str(exclusion.get("triggered_rule"))
        if rule == "exclude_big_up":
            excluded_states = list(_BULLISH_STATES)
        elif rule == "exclude_big_down":
            excluded_states = list(_BEARISH_STATES)
    if final_direction == "偏多" and "大涨" in excluded_states and final.get("final_confidence") == "high":
        conflicts.append("否定系统压制偏多极端，但 final_decision 给出 high 置信度偏多。")
    if final_direction == "偏空" and "大跌" in excluded_states and final.get("final_confidence") == "high":
        conflicts.append("否定系统压制偏空极端，但 final_decision 给出 high 置信度偏空。")

    return _unique(conflicts)


def _reliability_warnings(v2: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    for warning in _as_list(v2.get("warnings")):
        text = _clean_str(warning)
        if text:
            warnings.append(text)
    step_status = _as_dict(v2.get("step_status"))
    for step, status in step_status.items():
        if isinstance(status, str) and status not in {"success", ""}:
            warnings.append(f"步骤 {step} 未 success：{status}。")
    if not v2.get("ready"):
        warnings.append("projection_v2 整体未 ready，可靠性受限。")
    return _unique(warnings)


def build_overall_confidence(
    *,
    negative_confidence: dict[str, Any],
    projection_confidence: dict[str, Any],
    conflicts: list[str],
) -> dict[str, Any]:
    level = _conservative_combine(
        _normalize_level(negative_confidence.get("level")),
        _normalize_level(projection_confidence.get("level")),
    )
    if conflicts and level not in {"unknown", "low"}:
        rank = max(0, _LEVEL_RANK.get(level, 0) - 1)
        level = _RANK_TO_LEVEL.get(rank, level)
    reasoning: list[str] = [
        f"否定系统置信度 level={negative_confidence.get('level', 'unknown')}",
        f"02 推演置信度 level={projection_confidence.get('level', 'unknown')}",
    ]
    if conflicts:
        reasoning.append(f"检测到 {len(conflicts)} 项跨系统冲突，已保守下调。")
    else:
        reasoning.append("未检测到跨系统冲突，按保守取最小法合并。")
    return {
        "score": _level_to_score(level),
        "level": level,
        "reasoning": _unique(reasoning),
    }


def build_confidence_evaluator(v2_raw: dict[str, Any] | None) -> dict[str, Any]:
    v2 = _as_dict(v2_raw)
    negative = build_negative_system_confidence(v2)
    projection = build_projection_system_confidence(v2)
    conflicts = _conflicts_from_v2(v2)
    overall = build_overall_confidence(
        negative_confidence=negative,
        projection_confidence=projection,
        conflicts=conflicts,
    )
    return {
        "negative_system_confidence": negative,
        "projection_system_confidence": projection,
        "overall_confidence": overall,
        "conflicts": conflicts,
        "reliability_warnings": _reliability_warnings(v2),
    }


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------

_KIND = "projection_three_systems"


def _empty_negative_system(reason: str) -> dict[str, Any]:
    return {
        "conclusion": "否定系统不可用，已按安全降级处理。",
        "excluded_states": [],
        "strength": "none",
        "evidence": [],
        "invalidating_conditions": ["否定系统不可用，无法给出失效条件。"],
        "risk_notes": [reason] if reason else ["否定系统不可用，已按安全降级处理。"],
    }


def _empty_record_02_projection_system(reason: str) -> dict[str, Any]:
    return {
        "current_structure": "02 推演系统不可用，无法描述当前结构。",
        "main_projection": "02 推演系统不可用，无法生成主推演。",
        "five_state_projection": {},
        "open_path_close_projection": {
            "open": "02 推演系统不可用，开盘倾向暂不输出。",
            "intraday": "02 推演系统不可用，日内结构暂不输出。",
            "close": "02 推演系统不可用，收盘倾向暂不输出。",
        },
        "historical_sample_summary": "02 推演系统不可用，历史样本说明暂不输出。",
        "peer_market_confirmation": "02 推演系统不可用，peers 确认暂不输出。",
        "key_price_levels": [],
        "risk_notes": [reason] if reason else ["02 推演系统不可用，已按安全降级处理。"],
        "final_summary": "02 推演系统不可用。",
    }


def _empty_confidence_evaluator(reason: str) -> dict[str, Any]:
    notes = [reason] if reason else ["置信度评判系统不可用，已按安全降级处理。"]
    return {
        "negative_system_confidence": {
            "score": None,
            "level": "unknown",
            "reasoning": notes,
            "risks": notes,
        },
        "projection_system_confidence": {
            "score": None,
            "level": "unknown",
            "reasoning": notes,
            "risks": notes,
        },
        "overall_confidence": {
            "score": None,
            "level": "unknown",
            "reasoning": notes,
        },
        "conflicts": [],
        "reliability_warnings": notes,
    }


def build_projection_three_systems(
    projection_v2_raw: dict[str, Any] | None,
    *,
    symbol: str | None = None,
) -> dict[str, Any]:
    """Reshape projection_v2_raw into three independent system blocks."""
    v2 = _as_dict(projection_v2_raw)
    normalized_symbol = (
        _clean_str(v2.get("symbol")) or _clean_str(symbol) or "AVGO"
    ).upper() or "AVGO"

    if not v2:
        reason = "projection_v2_raw 为空或不可解析，三系统输出已安全降级。"
        return {
            "kind": _KIND,
            "symbol": normalized_symbol,
            "ready": False,
            "negative_system": _empty_negative_system(reason),
            "record_02_projection_system": _empty_record_02_projection_system(reason),
            "confidence_evaluator": _empty_confidence_evaluator(reason),
        }

    final_ready = bool(_as_dict(v2.get("final_decision")).get("ready"))
    ready = bool(v2.get("ready")) and final_ready

    return {
        "kind": _KIND,
        "symbol": normalized_symbol,
        "ready": ready,
        "negative_system": build_negative_system(v2),
        "record_02_projection_system": build_record_02_projection_system(v2),
        "confidence_evaluator": build_confidence_evaluator(v2),
    }


render_projection_three_systems = build_projection_three_systems
