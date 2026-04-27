from __future__ import annotations

from typing import Any

from services.big_down_tail_warning import build_big_down_tail_warning
from services.big_up_contradiction_card import build_contradiction_card


BIG_UP_RAW_LABELS = {
    "macro_contradiction_softening": "macro_contradiction",
    "earnings_post_window_softening": "post_earnings_window",
    "sample_confidence_invalidation": "sample_confidence_invalidation",
    "oversold_rebound_risk": "oversold_rebound",
    "breakout_continuation_risk": "breakout_continuation",
    "peer_catchup_risk": "peer_catchup",
    "consolidation_breakout_risk": "consolidation_breakout",
    "market_rebound_softening": "market_rebound",
    "crisis_regime_softening": "crisis_regime",
    "low_sample_confidence_softening": "low_sample_confidence",
}

BIG_DOWN_REASON_LABELS = {
    "系统同时排除了大涨和大跌两端状态": "dual_extremes",
    "预测结果偏向震荡": "predicted_neutral",
    "大跌概率被压低到 0.05 以下": "p_big_down_compressed",
    "大涨概率被压低到 0.05 以下": "p_big_up_compressed",
    "当前处于高波动或危机环境": "high_vol_or_crisis",
    "近期量能明显放大": "volume_expansion",
    "近 3/5 日波动已经放大": "recent_volatility_expansion",
}

TECH_LABELS = {
    "rsi_bullish": "rsi_bullish",
    "macd_bullish": "macd_bullish",
    "trend_above_ma20_ma50": "trend_above_ma20_ma50",
    "positive_momentum": "positive_momentum",
    "high_position": "high_position",
    "volume_confirmation": "volume_confirmation",
    "rsi_bearish": "rsi_bearish",
    "macd_bearish": "macd_bearish",
    "trend_below_ma20_ma50": "trend_below_ma20_ma50",
    "negative_momentum": "negative_momentum",
    "low_position": "low_position",
    "volume_stress": "volume_stress",
}

TIER_LABELS_CN = {
    "strong_evidence": "强证据",
    "supporting_evidence": "辅助证据",
    "data_gap_notice": "数据缺口提醒",
}

TIER_SORT_ORDER = {
    "strong_evidence": 0,
    "supporting_evidence": 1,
    "data_gap_notice": 2,
}

TAXONOMY_CATALOG: dict[str, dict[str, Any]] = {
    "history_support_thin_for_big_up_exclusion": {
        "source_type": "raw",
        "applies_to_exclusion": "大涨",
        "display_tier": "data_gap_notice",
        "title_cn": "历史样本对“否定大涨”支撑偏薄",
        "short_cn": "可比历史样本不足，当前没有足够先例继续高置信排除大涨。",
        "display_cn": "历史样本信心不足，说明这次“否定大涨”更像证据偏薄，而不是有强反证支持。",
        "source_labels": ["sample_confidence_invalidation"],
    },
    "macro_rebound_conflicts_with_big_up_exclusion": {
        "source_type": "raw",
        "applies_to_exclusion": "大涨",
        "display_tier": "strong_evidence",
        "title_cn": "宏观反弹条件与“否定大涨”矛盾",
        "short_cn": "宏观环境更像反弹或风险偏好修复，不支持继续强排除大涨。",
        "display_cn": "新补全的宏观环境信号与原先“否定大涨”的判断方向相反，因此这个否定可靠性明显下降。",
        "source_labels": ["macro_contradiction"],
    },
    "post_earnings_repricing_risk": {
        "source_type": "raw",
        "applies_to_exclusion": "大涨",
        "display_tier": "supporting_evidence",
        "title_cn": "财报后重定价窗口不适合强排除大涨",
        "short_cn": "财报后窗口容易出现重新定价，直接否定大涨的把握会下降。",
        "display_cn": "当前仍处于财报后重定价窗口，这类时段更容易出现方向重估，不适合把大涨当成强排除项。",
        "source_labels": ["post_earnings_window"],
    },
    "dual_tail_conflict_against_big_down_exclusion": {
        "source_type": "raw",
        "applies_to_exclusion": "大跌",
        "display_tier": "strong_evidence",
        "title_cn": "系统同时压低双尾，说明“大跌否定”本身不稳",
        "short_cn": "系统把大涨和大跌两端同时压低，说明尾部压缩过强，大跌不能再当成稳定排除项。",
        "display_cn": "原系统同时压低双尾状态，本身就说明判断偏向过度收缩；在这种结构下，继续否定大跌并不可靠。",
        "source_labels": ["dual_extremes"],
    },
    "tail_compression_context_against_big_down_exclusion": {
        "source_type": "raw",
        "applies_to_exclusion": "大跌",
        "display_tier": "supporting_evidence",
        "title_cn": "震荡压缩结构削弱了“否定大跌”的可信度",
        "short_cn": "预测偏向震荡且上行尾部也被压低，说明系统主要是在做双尾收缩，而不是有力地否定大跌。",
        "display_cn": "这类案例更像整体尾部压缩，而不是有充分证据证明不会出现大跌，因此“大跌否定”只能视为弱结论。",
        "source_labels": ["predicted_neutral", "p_big_up_compressed"],
    },
    "tail_risk_expansion_against_big_down_exclusion": {
        "source_type": "raw",
        "applies_to_exclusion": "大跌",
        "display_tier": "supporting_evidence",
        "title_cn": "波动与量能扩张提示尾部下跌风险仍在",
        "short_cn": "高波动、危机环境或量能放大，说明尾部大跌风险没有被真正消除。",
        "display_cn": "新补全数据提示波动和量能都在扩张，这种环境下尾部下跌风险仍然存在，不适合强排除大跌。",
        "source_labels": ["high_vol_or_crisis", "volume_expansion", "recent_volatility_expansion"],
    },
    "bullish_momentum_cluster": {
        "source_type": "technical",
        "applies_to_exclusion": "大涨",
        "display_tier": "strong_evidence",
        "title_cn": "技术动量偏强，不支持“否定大涨”",
        "short_cn": "MACD、RSI 或短中期动量偏强，说明上涨延续条件仍在。",
        "display_cn": "技术动量已经转强，说明价格仍具备继续上攻的条件，因此“否定大涨”缺少技术面支持。",
        "source_labels": ["macd_bullish", "positive_momentum", "rsi_bullish"],
    },
    "bullish_trend_structure_cluster": {
        "source_type": "technical",
        "applies_to_exclusion": "大涨",
        "display_tier": "strong_evidence",
        "title_cn": "价格趋势结构偏强，不支持“否定大涨”",
        "short_cn": "价格站上关键均线或已处于高位强势区间，趋势上不适合直接否定大涨。",
        "display_cn": "价格位置和均线结构都偏强，这说明趋势仍在大涨可达区间内，原先否定大涨的技术依据不足。",
        "source_labels": ["trend_above_ma20_ma50", "high_position"],
    },
    "bullish_volume_confirmation": {
        "source_type": "technical",
        "applies_to_exclusion": "大涨",
        "display_tier": "supporting_evidence",
        "title_cn": "量能配合上行，削弱“否定大涨”",
        "short_cn": "上涨伴随量能确认时，大涨并不能轻易被排除。",
        "display_cn": "量能和价格同向配合，说明市场对上行有确认，不适合把大涨直接视为低概率事件。",
        "source_labels": ["volume_confirmation"],
    },
    "bearish_momentum_cluster": {
        "source_type": "technical",
        "applies_to_exclusion": "大跌",
        "display_tier": "strong_evidence",
        "title_cn": "技术动量转弱，不支持“否定大跌”",
        "short_cn": "MACD、RSI 或短中期动量偏弱，说明向下延续条件仍在。",
        "display_cn": "技术动量已经偏空，价格仍有继续走弱的基础，因此“否定大跌”缺少技术面支撑。",
        "source_labels": ["macd_bearish", "negative_momentum", "rsi_bearish"],
    },
    "bearish_trend_structure_cluster": {
        "source_type": "technical",
        "applies_to_exclusion": "大跌",
        "display_tier": "strong_evidence",
        "title_cn": "价格趋势走弱，不支持“否定大跌”",
        "short_cn": "价格落在关键均线下方或处于低位弱势区间，大跌仍需保留。",
        "display_cn": "价格位置和趋势结构都偏弱，说明大跌风险仍处在可触发区间，原先否定大跌的技术依据不足。",
        "source_labels": ["trend_below_ma20_ma50", "low_position"],
    },
    "bearish_volume_stress": {
        "source_type": "technical",
        "applies_to_exclusion": "大跌",
        "display_tier": "supporting_evidence",
        "title_cn": "放量下行压力削弱“否定大跌”",
        "short_cn": "下跌伴随放量时，尾部下跌风险不能被轻易排除。",
        "display_cn": "量能放大同时价格承压，说明卖压真实存在，因此不适合把大跌直接排除。",
        "source_labels": ["volume_stress"],
    },
}

LABEL_TO_TAXONOMY_KEYS: dict[str, list[str]] = {}
for taxonomy_key, entry in TAXONOMY_CATALOG.items():
    for label in entry["source_labels"]:
        LABEL_TO_TAXONOMY_KEYS.setdefault(label, []).append(taxonomy_key)


def _safe_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed != parsed:
        return None
    return parsed


def split_listish(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value).split("|") if item.strip()]


def _sorted_taxonomy_keys(keys: set[str]) -> list[str]:
    return sorted(
        keys,
        key=lambda item: (
            TIER_SORT_ORDER[TAXONOMY_CATALOG[item]["display_tier"]],
            TAXONOMY_CATALOG[item]["source_type"],
            item,
        ),
    )


def map_labels_to_taxonomy_keys(labels: list[str]) -> list[str]:
    taxonomy_keys: set[str] = set()
    for label in labels:
        for taxonomy_key in LABEL_TO_TAXONOMY_KEYS.get(label, []):
            taxonomy_keys.add(taxonomy_key)
    return _sorted_taxonomy_keys(taxonomy_keys)


def build_row_display_summary(excluded_state: str, taxonomy_keys: list[str]) -> str:
    if excluded_state == "大涨":
        intro = "系统原先否定了“大涨”，但新补全证据不支持这个否定："
    elif excluded_state == "大跌":
        intro = "系统原先否定了“大跌”，但新补全证据不支持这个否定："
    else:
        intro = "系统原先做出了否定，但新补全证据不支持这个否定："

    lines = [
        str(TAXONOMY_CATALOG[key]["short_cn"]).strip().rstrip("。；")
        for key in taxonomy_keys
    ]
    if not lines:
        return intro + " 当前没有命中已定义的解释 taxonomy。"
    return intro + " " + "；".join(lines) + "。"


def normalize_big_up_raw_sources(card_payload: dict[str, Any]) -> list[str]:
    labels: list[str] = []
    for flag in card_payload.get("triggered_flags") or []:
        label = BIG_UP_RAW_LABELS.get(str(flag).strip())
        if label:
            labels.append(label)
    return sorted(set(labels))


def normalize_big_down_raw_sources(payload: dict[str, Any]) -> list[str]:
    labels: list[str] = []
    for reason in payload.get("reasons") or []:
        text = str(reason).strip()
        if not text or text.startswith("降级因素：") or text.startswith("数据受限："):
            continue
        label = BIG_DOWN_REASON_LABELS.get(text)
        if label:
            labels.append(label)
    return sorted(set(labels))


def _big_up_technical_flags(row: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    rsi_14 = _safe_float(row.get("rsi_14"))
    macd = _safe_float(row.get("macd"))
    macd_signal = _safe_float(row.get("macd_signal"))
    macd_hist = _safe_float(row.get("macd_hist"))
    close_vs_ma20_pct = _safe_float(row.get("close_vs_ma20_pct"))
    close_vs_ma50_pct = _safe_float(row.get("close_vs_ma50_pct"))
    ret1 = _safe_float(row.get("ret1"))
    ret5 = _safe_float(row.get("ret5"))
    ret10 = _safe_float(row.get("ret10"))
    pos20 = _safe_float(row.get("pos20"))
    pos60 = _safe_float(row.get("pos60"))
    vol_ratio_20 = _safe_float(row.get("vol_ratio_20"))

    if rsi_14 is not None and rsi_14 >= 60.0:
        flags.append("rsi_bullish")
    if (
        macd_hist is not None
        and macd_hist > 0
        and macd is not None
        and macd_signal is not None
        and macd > macd_signal
    ):
        flags.append("macd_bullish")
    if (
        close_vs_ma20_pct is not None
        and close_vs_ma20_pct > 0
        and close_vs_ma50_pct is not None
        and close_vs_ma50_pct > 0
    ):
        flags.append("trend_above_ma20_ma50")
    if (ret5 is not None and ret5 >= 2.0) or (ret10 is not None and ret10 >= 4.0):
        flags.append("positive_momentum")
    if (
        pos20 is not None
        and pos20 >= 70.0
        and pos60 is not None
        and pos60 >= 60.0
    ):
        flags.append("high_position")
    if (
        vol_ratio_20 is not None
        and vol_ratio_20 >= 1.2
        and ret1 is not None
        and ret1 > 0
    ):
        flags.append("volume_confirmation")
    return flags


def _big_down_technical_flags(row: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    rsi_14 = _safe_float(row.get("rsi_14"))
    macd = _safe_float(row.get("macd"))
    macd_signal = _safe_float(row.get("macd_signal"))
    macd_hist = _safe_float(row.get("macd_hist"))
    close_vs_ma20_pct = _safe_float(row.get("close_vs_ma20_pct"))
    close_vs_ma50_pct = _safe_float(row.get("close_vs_ma50_pct"))
    ret1 = _safe_float(row.get("ret1"))
    ret5 = _safe_float(row.get("ret5"))
    ret10 = _safe_float(row.get("ret10"))
    pos20 = _safe_float(row.get("pos20"))
    pos60 = _safe_float(row.get("pos60"))
    vol_ratio_20 = _safe_float(row.get("vol_ratio_20"))

    if rsi_14 is not None and rsi_14 <= 40.0:
        flags.append("rsi_bearish")
    if (
        macd_hist is not None
        and macd_hist < 0
        and macd is not None
        and macd_signal is not None
        and macd < macd_signal
    ):
        flags.append("macd_bearish")
    if (
        close_vs_ma20_pct is not None
        and close_vs_ma20_pct < 0
        and close_vs_ma50_pct is not None
        and close_vs_ma50_pct < 0
    ):
        flags.append("trend_below_ma20_ma50")
    if (ret5 is not None and ret5 <= -2.0) or (ret10 is not None and ret10 <= -4.0):
        flags.append("negative_momentum")
    if (
        pos20 is not None
        and pos20 <= 30.0
        and pos60 is not None
        and pos60 <= 40.0
    ):
        flags.append("low_position")
    if (
        vol_ratio_20 is not None
        and vol_ratio_20 >= 1.2
        and ret1 is not None
        and ret1 < 0
    ):
        flags.append("volume_stress")
    return flags


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or value == "":
        return False
    if isinstance(value, (int, float)):
        return bool(int(value))
    return str(value).strip().lower() in {"true", "1", "yes"}


def _infer_source_signals(row: dict[str, Any], excluded_state: str) -> dict[str, Any]:
    if excluded_state == "大涨":
        card_payload = build_contradiction_card(row)
        raw_unsupported = card_payload.get("audit_decision") != "hard_excluded"
        raw_source_labels = normalize_big_up_raw_sources(card_payload) if raw_unsupported else []
        technical_source_labels = _big_up_technical_flags(row)
        raw_detail = {
            "audit_decision": card_payload.get("audit_decision"),
            "raw_source_detail": card_payload,
        }
    elif excluded_state == "大跌":
        warning_payload = build_big_down_tail_warning(row)
        raw_unsupported = bool(warning_payload.get("tail_compression_triggered"))
        raw_source_labels = normalize_big_down_raw_sources(warning_payload) if raw_unsupported else []
        technical_source_labels = _big_down_technical_flags(row)
        raw_detail = {
            "tail_compression_triggered": warning_payload.get("tail_compression_triggered"),
            "tail_compression_score": warning_payload.get("tail_compression_score"),
            "raw_source_detail": warning_payload,
        }
    else:
        raw_unsupported = False
        raw_source_labels = []
        technical_source_labels = []
        raw_detail = {}

    technical_unsupported = len(technical_source_labels) >= 2
    return {
        "unsupported_by_raw_enriched": raw_unsupported,
        "unsupported_by_technical_features": technical_unsupported,
        "raw_source_labels": raw_source_labels,
        "technical_source_labels": technical_source_labels,
        **raw_detail,
    }


def _support_mix(raw_unsupported: bool, technical_unsupported: bool) -> str:
    if raw_unsupported and technical_unsupported:
        return "raw_and_technical"
    if raw_unsupported:
        return "raw_only"
    if technical_unsupported:
        return "technical_only"
    return "supported"


def build_exclusion_reliability_item(
    row: dict[str, Any] | None,
    *,
    excluded_state: str,
) -> dict[str, Any]:
    if not isinstance(row, dict):
        return {
            "excluded_state": excluded_state,
            "has_exclusion": False,
            "has_reliability_concern": False,
            "support_mix": "supported",
            "raw_source_labels": [],
            "technical_source_labels": [],
            "taxonomy_keys": [],
            "taxonomy_entries": [],
            "strongest_tier": "",
            "strongest_tier_cn": "",
            "display_summary_cn": "输入 row 缺失或格式无效，无法生成否定可靠性解释。",
            "display_lines_cn": [],
        }

    input_state = str(row.get("excluded_state_under_validation") or "").strip()
    has_exclusion = (
        input_state == excluded_state
        or excluded_state in split_listish(row.get("forced_excluded_states"))
    )
    if not has_exclusion:
        return {
            "excluded_state": excluded_state,
            "has_exclusion": False,
            "has_reliability_concern": False,
            "support_mix": "supported",
            "raw_source_labels": [],
            "technical_source_labels": [],
            "taxonomy_keys": [],
            "taxonomy_entries": [],
            "strongest_tier": "",
            "strongest_tier_cn": "",
            "display_summary_cn": f"本次结果没有否定“{excluded_state}”，无需生成该方向的可靠性解释。",
            "display_lines_cn": [],
        }

    if input_state == excluded_state and (
        "unsupported_by_raw_enriched" in row
        or "unsupported_by_technical_features" in row
        or "raw_source_labels" in row
        or "technical_source_labels" in row
    ):
        raw_unsupported = _coerce_bool(row.get("unsupported_by_raw_enriched"))
        technical_unsupported = _coerce_bool(row.get("unsupported_by_technical_features"))
        raw_source_labels = split_listish(row.get("raw_source_labels"))
        technical_source_labels = split_listish(row.get("technical_source_labels"))
        derived_detail: dict[str, Any] = {}
    else:
        inferred = _infer_source_signals(row, excluded_state)
        raw_unsupported = bool(inferred["unsupported_by_raw_enriched"])
        technical_unsupported = bool(inferred["unsupported_by_technical_features"])
        raw_source_labels = list(inferred["raw_source_labels"])
        technical_source_labels = list(inferred["technical_source_labels"])
        derived_detail = inferred

    support_mix = str(row.get("support_mix") or "").strip() or _support_mix(
        raw_unsupported,
        technical_unsupported,
    )
    effective_raw_source_labels = raw_source_labels if raw_unsupported else []
    effective_technical_source_labels = (
        technical_source_labels if technical_unsupported else []
    )
    taxonomy_keys = map_labels_to_taxonomy_keys(
        effective_raw_source_labels + effective_technical_source_labels
    )
    taxonomy_entries = [
        {
            "taxonomy_key": key,
            "source_type": TAXONOMY_CATALOG[key]["source_type"],
            "display_tier": TAXONOMY_CATALOG[key]["display_tier"],
            "display_tier_cn": TIER_LABELS_CN[TAXONOMY_CATALOG[key]["display_tier"]],
            "title_cn": TAXONOMY_CATALOG[key]["title_cn"],
            "short_cn": TAXONOMY_CATALOG[key]["short_cn"],
            "display_cn": TAXONOMY_CATALOG[key]["display_cn"],
        }
        for key in taxonomy_keys
    ]
    strongest_tier = (
        TAXONOMY_CATALOG[taxonomy_keys[0]]["display_tier"] if taxonomy_keys else ""
    )
    has_reliability_concern = bool(raw_unsupported or technical_unsupported)
    unmapped_source_labels = [
        label for label in (raw_source_labels + technical_source_labels)
        if label not in LABEL_TO_TAXONOMY_KEYS
    ]
    if has_reliability_concern:
        display_summary_cn = build_row_display_summary(excluded_state, taxonomy_keys)
    else:
        display_summary_cn = (
            f"系统原先否定了“{excluded_state}”，当前没有命中已定义的可靠性下降解释。"
        )

    return {
        "excluded_state": excluded_state,
        "has_exclusion": True,
        "has_reliability_concern": has_reliability_concern,
        "unsupported_by_raw_enriched": raw_unsupported,
        "unsupported_by_technical_features": technical_unsupported,
        "support_mix": support_mix,
        "raw_source_labels": effective_raw_source_labels,
        "technical_source_labels": effective_technical_source_labels,
        "taxonomy_keys": taxonomy_keys,
        "taxonomy_entries": taxonomy_entries,
        "strongest_tier": strongest_tier,
        "strongest_tier_cn": TIER_LABELS_CN.get(strongest_tier, ""),
        "display_summary_cn": display_summary_cn,
        "display_lines_cn": [entry["display_cn"] for entry in taxonomy_entries],
        "unmapped_source_labels": unmapped_source_labels,
        "system_negation_cn": f"系统原先否定了“{excluded_state}”。",
        "derived_detail": derived_detail,
    }


def build_exclusion_reliability_review(row: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(row, dict):
        return {
            "title": "否定可靠性解释",
            "has_exclusion_review": False,
            "review_items": [],
            "excluded_states_reviewed": [],
            "summary_cn": "输入 row 缺失或格式无效，无法生成否定可靠性解释。",
        }

    explicit_state = str(row.get("excluded_state_under_validation") or "").strip()
    if explicit_state in {"大涨", "大跌"}:
        states = [explicit_state]
    else:
        states = [state for state in split_listish(row.get("forced_excluded_states")) if state in {"大涨", "大跌"}]
    states = list(dict.fromkeys(states))

    if not states:
        return {
            "title": "否定可靠性解释",
            "has_exclusion_review": False,
            "review_items": [],
            "excluded_states_reviewed": [],
            "summary_cn": "本次结果没有否定“大涨”或“大跌”，无需生成否定可靠性解释。",
        }

    review_items = [
        build_exclusion_reliability_item(row, excluded_state=state)
        for state in states
    ]
    concern_items = [item for item in review_items if item["has_reliability_concern"]]
    if concern_items:
        summary_cn = "；".join(item["display_summary_cn"] for item in concern_items)
    else:
        summary_cn = "本次虽然存在方向否定，但当前没有命中已定义的可靠性下降解释。"

    return {
        "title": "否定可靠性解释",
        "has_exclusion_review": True,
        "review_items": review_items,
        "excluded_states_reviewed": states,
        "has_reliability_concern": bool(concern_items),
        "summary_cn": summary_cn,
    }
