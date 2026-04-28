"""Task 085 — big-up exclusion contradiction warning card (pure logic).

Read-only presentation layer. Takes one v4-enriched row dict (the same
shape as ``logs/historical_training/exclusion_log_enriched/enriched_conflict_analysis_v4.csv``
or the live equivalent) and returns a structured payload that the
streamlit renderer in ``ui/big_up_contradiction_card.py`` can display.

This module **does not** modify any prediction logic, the audit module's
production behaviour, or the row payload itself. It only:

1. Calls :func:`services.anti_false_exclusion_audit.audit_big_up_exclusion`
   under the Task 084 v5-best config.
2. Translates the audit output into a UI-friendly Chinese warning.
3. Surfaces missing upstream fields explicitly (no silent fallback).

Why this lives in ``services/`` and not ``ui/``
-----------------------------------------------
The streamlit renderer should be a ~30-line wrapper that calls
``st.info`` / ``st.warning`` / ``st.error``. All the conditional logic
(audit dispatch, missing-field detection, Chinese text mapping) belongs
here so it can be unit-tested without an AppTest harness.
"""

from __future__ import annotations

from typing import Any

from services.anti_false_exclusion_audit import (
    AuditConfig,
    audit_big_up_exclusion,
)
from services.big_down_tail_warning import build_big_down_tail_warning


# Task 084 best config (highest rescue/false_unblock ratio with all spec
# criteria passing). Fields not listed below take their AuditConfig defaults.
DEFAULT_CARD_CONFIG = AuditConfig(
    macro_contradiction_threshold=1,
    earnings_post_window_threshold=1,
    sample_invalidation_threshold=3,
    macro_score_for_block=4,
    peer_catchup_threshold=999,
    consolidation_threshold=999,
    enable_peer_catchup=False,
    enable_consolidation=False,
    enable_market_rebound=False,
    enable_crisis_regime=False,
    enable_low_sample=False,
    enable_macro_contradiction=True,
    enable_earnings_post_window=True,
    enable_sample_invalidation=True,
    enable_old_signals=False,
    decision_logic_version=5,
)


# Mapping risk_flag → Chinese explanation line.
FLAG_REASONS_CN: dict[str, str] = {
    "macro_contradiction_softening": "宏观反弹信号与否定大涨矛盾",
    "earnings_post_window_softening": "财报后窗口存在重新定价风险",
    "sample_confidence_invalidation": "历史样本信心不足，否定缺乏足够先例",
    "oversold_rebound_risk": "短期超卖反弹特征显现",
    "breakout_continuation_risk": "突破延续动量出现",
}


# ── helpers ───────────────────────────────────────────────────────────────────

def _excluded_contains_big_up(row: dict[str, Any]) -> bool:
    raw = row.get("forced_excluded_states") or row.get("excluded_states") or ""
    if isinstance(raw, list):
        return "大涨" in raw
    if not isinstance(raw, str):
        return False
    return any(p.strip() == "大涨" for p in raw.split("|") if p)


def _detect_missing_fields(row: dict[str, Any]) -> list[str]:
    """Return human-readable list of missing upstream feature groups.

    Each entry names the group + its data-source dependency so the user
    knows what to fix.
    """
    missing: list[str] = []
    if row.get("macro_contradicts_big_up_exclusion") in (None, "", "None"):
        missing.append(
            "宏观矛盾信号 (macro_contradicts_big_up_exclusion)：依赖 p_大涨 + macro 缓存"
        )
    if row.get("is_post_earnings_window") in (None, "", "None"):
        missing.append(
            "财报窗口 (is_post_earnings_window)：依赖 data/AVGO_earnings.csv"
        )
    sample_conf = row.get("historical_sample_confidence")
    if sample_conf in (None, "", "None"):
        missing.append(
            "历史样本信心 (historical_sample_confidence)：依赖 coded_data/AVGO_coded.csv"
        )
    return missing


# ── public API ────────────────────────────────────────────────────────────────

def build_contradiction_card(
    row: dict[str, Any] | None,
    *,
    config: AuditConfig | None = None,
) -> dict[str, Any]:
    """Build the structured payload for one prediction row.

    Returns a dict the renderer can pass straight to streamlit. The
    payload shape is intentionally renderer-agnostic.

    Output keys::

        show_card               bool — whether to display anything
        variant                 str  — "info" / "warning" / "strong_warning"
        title                   str  — fixed: "否定矛盾检测"
        has_big_up_exclusion    bool
        audit_decision          str  — hard_excluded / soft_excluded /
                                       blocked_by_audit / not_excluded
        contradiction_level     str  — 无 / 弱 / 中 / 强 / 数据有限
        exclusion_confidence    str  — 高 / 中 / 低 / 极低 / 数据有限 / n/a
        triggered_flags         list[str]
        flag_reasons_cn         list[str]   — one Chinese line per flag
        missing_fields          list[str]
        header_message          str  — one-line summary
        chinese_explanation     str  — multi-line paragraph
        original_system_summary str  — what the system said before audit
    """
    big_down_warning = build_big_down_tail_warning(row if isinstance(row, dict) else {})

    if not isinstance(row, dict):
        return {
            "show_card": True,
            "variant": "info",
            "title": "否定矛盾检测",
            "has_big_up_exclusion": False,
            "audit_decision": "not_excluded",
            "contradiction_level": "数据有限",
            "exclusion_confidence": "数据有限",
            "triggered_flags": [],
            "flag_reasons_cn": [],
            "missing_fields": ["输入 row 缺失或格式无效"],
            "header_message": "无法读取本次预测结果，矛盾检测跳过。",
            "chinese_explanation": "矛盾检测器需要一个 enriched 预测行字典作为输入；当前未收到。",
            "original_system_summary": "未提供原系统结论。",
            "big_down_tail_warning": big_down_warning,
            "data_health_summary": {},
            "cache_health_warnings": [],
            "data_health_overall_status": "unknown",
        }

    cfg = config or DEFAULT_CARD_CONFIG

    has_big_up_exclusion = _excluded_contains_big_up(row)

    if not has_big_up_exclusion:
        return {
            "show_card": True,
            "variant": "info",
            "title": "否定矛盾检测",
            "has_big_up_exclusion": False,
            "audit_decision": "not_excluded",
            "contradiction_level": "无",
            "exclusion_confidence": "n/a",
            "triggered_flags": [],
            "flag_reasons_cn": [],
            "missing_fields": [],
            "header_message": "未触发大涨否定，无需矛盾检测。",
            "chinese_explanation": (
                "本次系统未将「大涨」列入强排除项，矛盾检测器未启动。"
                "下方仅提示当前不涉及大涨否定。"
            ),
            "original_system_summary": "原系统结论：未排除「大涨」。",
            "big_down_tail_warning": big_down_warning,
            "data_health_summary": row.get("data_health_summary") or {},
            "cache_health_warnings": list((row.get("data_health_summary") or {}).get("warnings") or []),
            "data_health_overall_status": str(((row.get("data_health_summary") or {}).get("overall_status") or "unknown")).strip().lower() or "unknown",
        }

    # Big-up was excluded → run audit and translate.
    audit = audit_big_up_exclusion(row, config=cfg)
    decision = audit["final_decision"]
    flags = list(audit["risk_flags"])
    counter_flags = list(audit["counter_flags"])

    missing = _detect_missing_fields(row)
    field_data_limited = len(missing) >= 2  # ≥ 2 of 3 core sources missing → 数据有限

    # Task 088 — merge cache health into the data_limited / suffix logic.
    health = row.get("data_health_summary") or {}
    health_overall = str(health.get("overall_status") or "").strip().lower()
    health_data_limited = bool(health.get("data_limited"))
    cache_health_warnings = list(health.get("warnings") or [])

    data_limited = field_data_limited or health_data_limited
    # Suffix policy: stale → "(数据陈旧)"; partial/missing → "(数据有限)".
    if health_overall == "stale":
        suffix = "（数据陈旧）"
    elif health_overall in ("partial", "missing"):
        suffix = "（数据有限）"
    elif field_data_limited:
        # No cache-level signal but ≥2 fields missing → keep legacy suffix.
        suffix = "（数据有限）"
    else:
        suffix = ""

    if decision == "blocked_by_audit":
        variant = "strong_warning"
        contradiction_level = "强"
        exclusion_confidence = "极低"
        header = "检测到强反证，本次不建议把大涨作为强排除项。"
        explanation = (
            "系统原本基于低历史概率或同行不支持排除大涨，"
            "但当前存在多个反证指标。"
            "因此本次不建议将「大涨」作为强排除项，只能作为低概率情形参考。"
        )
    elif decision == "soft_excluded":
        variant = "warning"
        contradiction_level = "中"
        exclusion_confidence = "低"
        header = "检测到否定失效风险，本次大涨否定置信度下降。"
        explanation = (
            "系统将「大涨」列入排除项，但矛盾检测器发现至少一个反证信号。"
            "建议把本次大涨视为低概率情形而非「几乎不可能」，"
            "结合 T+1 同行 / 财报 / overnight gap 等信号进一步判断。"
        )
    elif decision == "hard_excluded":
        variant = "info"
        contradiction_level = "弱" if flags else "无"
        exclusion_confidence = "高"
        header = "当前未发现明显反证，大涨否定保持较高置信。"
        explanation = (
            "系统将「大涨」列入强排除项；"
            "矛盾检测器在宏观环境、财报窗口与历史样本基础上未发现足以降级的反证。"
            "本次否定可作为高置信结论使用。"
        )
    else:
        variant = "info"
        contradiction_level = "数据有限"
        exclusion_confidence = "数据有限"
        header = "矛盾检测未能给出决策。"
        explanation = (
            "audit 返回 not_excluded 但行中确实包含大涨否定，"
            "可能是输入字段不一致；本次检测置信度有限。"
        )

    # Override when upstream data is limited (field-level OR cache-level).
    downgrade_note = ""
    if data_limited:
        if variant == "strong_warning":
            variant = "warning"
            downgrade_note = (
                "由于部分数据缺失或陈旧，强提醒降级为普通提醒。"
            )
        if suffix:
            contradiction_level = f"{contradiction_level} {suffix}"
            exclusion_confidence = f"{exclusion_confidence} {suffix}"

    flag_reasons_cn = [
        FLAG_REASONS_CN.get(f, f"触发 {f}") for f in flags
    ]
    if counter_flags:
        flag_reasons_cn.append(
            f"反证抵消 ({'、'.join(counter_flags)})：检测器对反证给出了一定折扣"
        )

    if downgrade_note:
        explanation = explanation + " " + downgrade_note

    return {
        "show_card": True,
        "variant": variant,
        "title": "否定矛盾检测",
        "has_big_up_exclusion": True,
        "audit_decision": decision,
        "contradiction_level": contradiction_level,
        "exclusion_confidence": exclusion_confidence,
        "triggered_flags": flags,
        "flag_reasons_cn": flag_reasons_cn,
        "missing_fields": missing,
        "header_message": header,
        "chinese_explanation": explanation,
        "original_system_summary": "原系统结论：大涨被列入排除项。",
        # Task 088: full data_health_summary forwarded so the renderer can
        # show per-source status. Empty dict when not provided.
        "data_health_summary": health,
        "cache_health_warnings": cache_health_warnings,
        "data_health_overall_status": health_overall or "unknown",
        "big_down_tail_warning": big_down_warning,
    }


def build_contradiction_card_payload(
    predict_result: dict[str, Any] | None,
    *,
    prediction_date: str | None = None,
) -> dict[str, Any]:
    """Adapt a live ``predict_result`` into a row dict for downstream
    contradiction-card / exclusion-reliability-review consumers.

    Pure read. ``predict_result`` is never mutated. Safe on ``None`` or
    partial inputs — missing fields are simply omitted. The returned
    row carries ``prediction_date`` (and a duplicate ``analysis_date``)
    when provided so downstream code that keys on either name works.
    """
    row: dict[str, Any] = {}

    if isinstance(predict_result, dict):
        for key in (
            "predicted_state",
            "forced_excluded_states",
            "excluded_states",
            "p_大涨",
            "p_大跌",
            "p_小涨",
            "p_小跌",
            "p_震荡",
            "state_probabilities",
            "final_direction",
            "final_confidence",
            "five_state_top1",
            "five_state_distribution",
            "five_state_top1_margin",
            "five_state_margin_band",
            "five_state_display_state",
            "five_state_secondary_state",
            "exclusion_triggered_rule",
            "exclusion_triggered_state",
            "excluded_state_under_validation",
            "support_mix",
            "raw_source_labels",
            "technical_source_labels",
            "unsupported_by_raw_enriched",
            "unsupported_by_technical_features",
            "data_health_summary",
            "contradiction_inputs_available",
            "actual_state",
            "symbol",
        ):
            if key in predict_result:
                row[key] = predict_result[key]

    if prediction_date:
        row["prediction_date"] = prediction_date
        row["analysis_date"] = prediction_date

    return row


__all__ = (
    "DEFAULT_CARD_CONFIG",
    "FLAG_REASONS_CN",
    "build_contradiction_card",
    "build_contradiction_card_payload",
)
