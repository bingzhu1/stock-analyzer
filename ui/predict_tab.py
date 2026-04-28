from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import pandas as pd
import streamlit as st

from predict import run_predict
from services.ai_summary import build_projection_ai_summary, build_review_ai_summary
from services.evidence_trace import build_projection_evidence_trace
from services.openai_client import OpenAIClientError
from services.predict_summary import build_predict_readable_summary
from services.prediction_store import (
    get_outcome_for_prediction,
    get_review_for_prediction,
    save_prediction,
)
from services.outcome_capture import capture_outcome
from services.review_agent import generate_review
from services.review_orchestrator import run_review_for_prediction
from services.review_analyzer import summarize_review_history, extract_review_rules
from services.pre_prediction_briefing import build_pre_prediction_briefing
from services.big_up_contradiction_card import build_contradiction_card_payload
from ui.exclusion_reliability_review import render_exclusion_reliability_review_for_row


# ─────────────────────────────────────────────────────────────────────────────
# Label maps (中文化)
# ─────────────────────────────────────────────────────────────────────────────

_BIAS_CN = {
    "bullish": "偏多",
    "bearish": "偏空",
    "neutral": "中性",
    "up_bias": "偏多",
    "down_bias": "偏空",
    "mixed": "多空分歧",
    "insufficient_sample": "样本不足",
    "unavailable": "不可用",
}
_CONFIDENCE_CN = {"high": "高", "medium": "中", "low": "低"}
_OPEN_CN = {
    "gap_up_bias": "高开",
    "gap_down_bias": "低开",
    "flat_bias": "平开",
    "unclear": "待确认",
}
_CLOSE_CN = {
    "close_strong": "收涨",
    "close_weak": "收跌",
    "range": "震荡",
    "unclear": "待确认",
}
_GAP_CN = {"gap_up": "高开", "gap_down": "低开", "flat": "平开", "unknown": "未知"}
_INTRA_CN = {"high_go": "高走", "low_go": "低走", "range": "震荡", "unknown": "未知"}
_CONFIRM_CN = {"confirmed": "信号一致", "diverging": "信号背离", "mixed": "信号混合"}
_CAUTION_CN = {"none": "无数据", "low": "低", "medium": "中等", "high": "较高"}
_CAUTION_COLOR = {
    "none": "#6b7280",
    "low": "#1f7a4f",
    "medium": "#b36b00",
    "high": "#b42318",
}
_BIAS_COLOR = {
    "bullish": "#16a34a",
    "bearish": "#dc2626",
    "neutral": "#6b7280",
    "up_bias": "#16a34a",
    "down_bias": "#dc2626",
    "mixed": "#b36b00",
}
_PEER_ADJ_CN = {
    "reinforce_bullish":  "强化多头",
    "reinforce_bearish":  "强化空头",
    "weaken_bullish":     "削弱多头",
    "weaken_bearish":     "削弱空头",
    "neutral":            "中性（不调整）",
}
_RESEARCH_ADJ_CN = {
    "reinforce_bullish":       "强化多头",
    "reinforce_bearish":       "强化空头",
    "weaken_bullish":          "削弱多头",
    "weaken_bearish":          "削弱空头",
    "no_clear_adjustment":     "无明确调整",
    "missing_research":        "未接入 Research",
    "missing_research_scan_led": "以 Scan 为主",
}


def _cn(mapping: dict, key: Any, fallback: str = "—") -> str:
    return mapping.get(str(key or ""), fallback)


def _as_dict(v: Any) -> dict:
    return v if isinstance(v, dict) else {}


def _safe_float(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────

_CSS = """
<style>
.pt-hero {
    padding: 22px 26px;
    border-radius: 16px;
    background: linear-gradient(135deg, rgba(13,27,42,0.97), rgba(18,52,86,0.94));
    color: #f8fafc;
    margin-bottom: 16px;
}
.pt-hero-dir {
    font-size: 3.2rem;
    font-weight: 900;
    line-height: 1;
    letter-spacing: -1px;
}
.pt-hero-conf {
    display: inline-block;
    margin-top: 6px;
    padding: 3px 14px;
    border-radius: 20px;
    font-size: 1rem;
    font-weight: 700;
}
.pt-hero-summary {
    margin-top: 14px;
    font-size: 0.97rem;
    opacity: 0.9;
    line-height: 1.55;
}
.pt-ctx-card {
    padding: 12px 14px;
    border: 1px solid rgba(148,163,184,0.2);
    border-radius: 12px;
    background: rgba(248,250,252,0.02);
}
.pt-ctx-label {
    font-size: 0.75rem;
    color: #64748b;
    margin-bottom: 4px;
}
.pt-ctx-value {
    font-size: 1.05rem;
    font-weight: 700;
    color: #1e293b;
}
.pt-pred-item {
    padding: 10px 14px;
    border: 1px solid rgba(148,163,184,0.2);
    border-radius: 10px;
    background: rgba(248,250,252,0.03);
    text-align: center;
}
.pt-pred-label {
    font-size: 0.75rem;
    color: #64748b;
    margin-bottom: 4px;
}
.pt-pred-value {
    font-size: 1.25rem;
    font-weight: 700;
    color: #1e293b;
}
.pt-ev-section {
    font-size: 0.95rem;
    font-weight: 700;
    color: #1e293b;
    border-left: 3px solid #3b82f6;
    padding-left: 8px;
    margin-bottom: 8px;
}
.pt-ev-row {
    display: flex;
    gap: 10px;
    padding: 5px 0;
    border-bottom: 1px solid rgba(148,163,184,0.1);
    font-size: 0.85rem;
}
.pt-ev-lbl { color: #64748b; min-width: 90px; }
.pt-ev-val { font-weight: 600; color: #1e293b; }
.pt-step-header {
    font-size: 0.95rem;
    font-weight: 700;
    color: #1e293b;
    margin-bottom: 6px;
}
.pt-step-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 600;
}
.pt-section-title {
    font-size: 1.1rem;
    font-weight: 800;
    color: #1e293b;
    border-left: 4px solid #3b82f6;
    padding-left: 10px;
    margin: 20px 0 10px 0;
}
.pt-warn-inline {
    background: rgba(239,68,68,0.07);
    border: 1px solid rgba(239,68,68,0.25);
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 0.85rem;
    color: #7f1d1d;
    margin: 6px 0;
}
.pt-ok-inline {
    background: rgba(22,163,74,0.07);
    border: 1px solid rgba(22,163,74,0.25);
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 0.85rem;
    color: #14532d;
    margin: 6px 0;
}
</style>
"""


# ─────────────────────────────────────────────────────────────────────────────
# AI summary helpers (kept for backward compat)
# ─────────────────────────────────────────────────────────────────────────────

def _projection_ai_payload(
    predict_result: dict,
    scan_result: dict | None,
    research_result: dict | None,
) -> dict:
    readable = predict_result.get("readable_summary")
    if not isinstance(readable, dict):
        readable = build_predict_readable_summary(predict_result, scan_result=scan_result)
    return {
        "kind": "projection_ai_summary",
        "symbol": predict_result.get("symbol", "AVGO"),
        "final_bias": predict_result.get("final_bias"),
        "final_confidence": predict_result.get("final_confidence"),
        "open_tendency": predict_result.get("open_tendency"),
        "close_tendency": predict_result.get("close_tendency"),
        "prediction_summary": predict_result.get("prediction_summary"),
        "readable_summary": readable,
        "supporting_factors": predict_result.get("supporting_factors", []),
        "conflicting_factors": predict_result.get("conflicting_factors", []),
        "primary_projection": predict_result.get("primary_projection") or {},
        "peer_adjustment": predict_result.get("peer_adjustment") or {},
        "final_projection": predict_result.get("final_projection") or {},
        "scan_result": scan_result or {},
        "research_result": research_result or {},
    }


def _review_ai_payload(
    *,
    prediction_id: str,
    predict_result: dict,
    outcome: dict,
    review: dict | None,
) -> dict:
    return {
        "kind": "review_ai_summary",
        "prediction_id": prediction_id,
        "symbol": predict_result.get("symbol", "AVGO"),
        "final_bias": predict_result.get("final_bias"),
        "final_confidence": predict_result.get("final_confidence"),
        "prediction_summary": predict_result.get("prediction_summary"),
        "readable_summary": predict_result.get("readable_summary") or {},
        "outcome": outcome,
        "rule_review": review or {},
    }


def _show_ai_summary_error(kind: str, exc: Exception) -> None:
    if isinstance(exc, OpenAIClientError):
        st.warning(str(exc))
        return
    st.warning(f"{kind}生成失败，已保留规则层结果：{exc}")


# ─────────────────────────────────────────────────────────────────────────────
# Legacy render functions — kept for test compatibility
# ─────────────────────────────────────────────────────────────────────────────

def render_readable_predict_summary(summary: dict) -> None:
    """Legacy: render readable predict summary (kept for test compat)."""
    st.markdown("**明日基准判断**")
    base = summary.get("baseline_judgment", {})
    b1, b2, b3 = st.columns(3)
    b1.metric("方向", base.get("direction", "中性"))
    b2.metric("强度", base.get("strength", "弱"))
    b3.metric("风险", base.get("risk_level", "高"))
    st.write(base.get("text", ""))
    open_block = summary.get("open_projection", {})
    close_block = summary.get("close_projection", {})
    st.markdown("**开盘推演**")
    st.write(open_block.get("text", ""))
    st.markdown("**收盘推演**")
    st.write(close_block.get("text", ""))
    st.markdown("**为什么这样判断**")
    for line in summary.get("rationale", []) or []:
        st.caption(f"- {line}")
    st.markdown("**风险提醒**")
    for line in summary.get("risk_reminders", []) or []:
        st.caption(f"- {line}")


def render_evidence_trace(trace: dict) -> None:
    """Legacy: render evidence trace (kept for test compat)."""
    if not isinstance(trace, dict):
        return
    st.markdown("**证据追踪**")
    for item in trace.get("tool_trace", []) or []:
        st.caption(f"- {item}")
    for line in trace.get("key_observations", []) or []:
        st.caption(f"- {line}")
    for line in trace.get("decision_steps", []) or []:
        st.caption(f"- {line}")
    final = trace.get("final_conclusion", {}) or {}
    cols = st.columns(4)
    cols[0].metric("明日方向", final.get("direction", "中性"))
    cols[1].metric("开盘倾向", final.get("open_tendency", "平开"))
    cols[2].metric("收盘倾向", final.get("close_tendency", "震荡"))
    cols[3].metric("置信度", _cn(_CONFIDENCE_CN, final.get("confidence"), "低"))
    for line in trace.get("verification_points", []) or []:
        st.caption(f"- {line}")


def render_projection_pipeline(pr: dict) -> None:
    """Legacy: render projection pipeline (kept for test compat)."""
    primary = _as_dict(pr.get("primary_projection"))
    peer = _as_dict(pr.get("peer_adjustment"))
    final = _as_dict(pr.get("final_projection"))
    if not any([primary, peer, final]):
        return
    st.markdown("**推演链路**")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**1. 主推演**")
        st.metric("AVGO判断", f"{_cn(_BIAS_CN, primary.get('final_bias'))} / {_cn(_CONFIDENCE_CN, primary.get('final_confidence'))}")
    with c2:
        st.markdown("**2. 同业调整**")
        st.metric("调整方向", _cn(_PEER_ADJ_CN, peer.get("adjustment_direction"), "中性"))
    with c3:
        st.markdown("**3. 最终结论**")
        st.metric("最终判断", f"{_cn(_BIAS_CN, final.get('final_bias', pr.get('final_bias')))} / {_cn(_CONFIDENCE_CN, final.get('final_confidence', pr.get('final_confidence')))}")


def render_predict_result(pr: dict) -> None:
    """Legacy: render predict result (kept for test compat)."""
    bias = str(pr.get("final_bias", "neutral"))
    confidence = str(pr.get("final_confidence", "low"))
    bias_colors = {"bullish": "#2ecc71", "bearish": "#e74c3c", "neutral": "#95a5a6"}
    conf_colors = {"high": "#f39c12", "medium": "#3498db", "low": "#95a5a6"}
    st.markdown(f"**{pr.get('symbol', 'AVGO')}** · {pr.get('predict_timestamp', '')}")
    st.markdown(
        f'<div style="margin:8px 0 4px 0">'
        f'<span style="font-size:2em;font-weight:bold;color:{bias_colors.get(bias, "#888")}">'
        f'{_cn(_BIAS_CN, bias, bias.upper())}</span>'
        f'&nbsp;&nbsp;'
        f'<span style="font-size:1.1em;font-weight:bold;color:{conf_colors.get(confidence, "#888")};">'
        f'置信度：{_cn(_CONFIDENCE_CN, confidence)}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("开盘倾向", _cn(_OPEN_CN, pr.get("open_tendency"), "待确认"))
    p2.metric("收盘倾向", _cn(_CLOSE_CN, pr.get("close_tendency"), "待确认"))
    p3.metric("扫描方向", f"{_cn(_BIAS_CN, pr.get('scan_bias'))} / {_cn(_CONFIDENCE_CN, pr.get('scan_confidence'))}")
    p4.metric("研究调整", _cn(_RESEARCH_ADJ_CN, pr.get("research_bias_adjustment"), "—"))
    render_projection_pipeline(pr)
    if pr.get("briefing_caution_applied"):
        st.warning(f"⚡ 历史复盘规则介入：{pr.get('briefing_caution_reason', '')}")
    st.markdown("**推演摘要**")
    st.write(pr.get("prediction_summary", ""))
    readable_summary = pr.get("readable_summary")
    if not isinstance(readable_summary, dict):
        readable_summary = build_predict_readable_summary(pr)
    render_readable_predict_summary(readable_summary)
    trace = pr.get("evidence_trace")
    if isinstance(trace, dict):
        render_evidence_trace(trace)
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("**支持因素**")
        supporting = pr.get("supporting_factors", [])
        st.dataframe(pd.DataFrame({"factor": supporting}), hide_index=True, use_container_width=True)
    with col_r:
        st.markdown("**冲突因素**")
        conflicting = pr.get("conflicting_factors", [])
        if conflicting:
            st.dataframe(pd.DataFrame({"factor": conflicting}), hide_index=True, use_container_width=True)
        else:
            st.caption("无明确冲突因素。")
    with st.expander("推演原始数据"):
        st.json(pr)


# ─────────────────────────────────────────────────────────────────────────────
# Internal layer renderers
# ─────────────────────────────────────────────────────────────────────────────

def _render_layer1_context(
    predict_result: dict,
    briefing: dict,
    target_date_str: str,
) -> None:
    """第一层：顶部上下文区"""
    today_str = datetime.now().strftime("%Y-%m-%d")
    caution = briefing.get("caution_level", "none")
    caution_cn = _CAUTION_CN.get(caution, caution)
    caution_color = _CAUTION_COLOR.get(caution, "#6b7280")

    rule_scope = briefing.get("rule_scope", "global")
    rule_scope_cn = "全局规律" if rule_scope == "global" else "场景规律"

    has_data = briefing.get("has_data", False)
    real_count = 0
    hist_count = 0
    try:
        from services.review_store import count_real_vs_historical
        counts = count_real_vs_historical(str(predict_result.get("symbol", "AVGO")))
        real_count = counts.get("real", 0)
        hist_count = counts.get("historical", 0)
    except Exception:
        pass

    if real_count > 0:
        source_label = f"真实复盘 {real_count} 条"
        source_color = "#1f7a4f"
    elif hist_count > 0:
        source_label = f"历史训练 {hist_count} 条"
        source_color = "#b36b00"
    else:
        source_label = "暂无数据"
        source_color = "#6b7280"

    caution_applied = bool(predict_result.get("briefing_caution_applied"))
    caution_reason = str(predict_result.get("briefing_caution_reason") or "")
    intervention_label = "是（已介入）" if caution_applied else ("否（仅参考）" if has_data else "否（无历史数据）")
    intervention_color = "#b42318" if caution_applied else ("#b36b00" if has_data else "#6b7280")

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(f"""
        <div class="pt-ctx-card">
            <div class="pt-ctx-label">分析日期</div>
            <div class="pt-ctx-value">{today_str}</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="pt-ctx-card">
            <div class="pt-ctx-label">目标预测日期</div>
            <div class="pt-ctx-value">{target_date_str or "—"}</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="pt-ctx-card">
            <div class="pt-ctx-label">规律来源</div>
            <div class="pt-ctx-value" style="color:{source_color};">{source_label}</div>
            <div style="font-size:0.72rem;color:#94a3b8;margin-top:2px;">{rule_scope_cn}</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="pt-ctx-card">
            <div class="pt-ctx-label">当前风险等级</div>
            <div class="pt-ctx-value" style="color:{caution_color};">{caution_cn}</div>
            <div style="font-size:0.72rem;color:#94a3b8;margin-top:2px;">基于历史复盘统计</div>
        </div>""", unsafe_allow_html=True)
    with c5:
        st.markdown(f"""
        <div class="pt-ctx-card">
            <div class="pt-ctx-label">历史规律介入推演</div>
            <div class="pt-ctx-value" style="color:{intervention_color};">{intervention_label}</div>
            <div style="font-size:0.72rem;color:#94a3b8;margin-top:2px;">仅建议，不改算法</div>
        </div>""", unsafe_allow_html=True)

    if caution_applied and caution_reason:
        st.markdown(
            f'<div class="pt-warn-inline">⚡ 历史规律介入原因：{caution_reason}</div>',
            unsafe_allow_html=True,
        )

    # Briefing detail (collapsible, auto-expand for high/medium caution)
    _render_briefing_compact(briefing)


def _render_briefing_compact(briefing: dict) -> None:
    """Collapsible briefing expander within Layer 1."""
    caution = briefing.get("caution_level", "none")
    has_data = briefing.get("has_data", False)
    record_count = briefing.get("record_count", 0)
    global_count = briefing.get("global_record_count", record_count)
    rule_scope = briefing.get("rule_scope", "global")
    selected_open = briefing.get("selected_open_scenario")
    caution_color = _CAUTION_COLOR.get(caution, "#6b7280")
    caution_cn = _CAUTION_CN.get(caution, caution)

    if has_data and rule_scope == "open_scenario" and selected_open:
        label = f"历史复盘提醒 — {selected_open}场景 · 风险等级：{caution_cn}（{record_count}条场景 / {global_count}条总计）"
    else:
        label = f"历史复盘提醒 — 风险等级：{caution_cn}（{record_count} 条记录）" if has_data else "历史复盘提醒 — 暂无记录"

    with st.expander(label, expanded=(caution in ("high", "medium"))):
        if not has_data:
            st.caption("尚无历史复盘记录。完成复盘后，此处将自动显示规律提醒。")
            return
        oa = briefing.get("overall_accuracy", 0.0)
        st.markdown(
            f'<span style="color:{caution_color};font-weight:700;">⚡ 风险等级：{caution_cn}</span>  '
            f'&nbsp;·&nbsp; 历史命中率 {oa:.0%}（最近 {record_count} 条）',
            unsafe_allow_html=True,
        )
        for rule in briefing.get("top_rules", []):
            st.markdown(f"- {rule}")
        weak_cn = briefing.get("weakest_dimension_cn")
        weak_acc = briefing.get("weakest_accuracy")
        if weak_cn and weak_acc is not None:
            c1, c2 = st.columns(2)
            c1.metric("最弱维度", weak_cn)
            c2.metric("该维度准确率", f"{weak_acc:.0%}")


def _render_layer2_conclusion(predict_result: dict, scan_result: dict | None) -> None:
    """第二层：主结论卡"""
    bias = str(predict_result.get("final_bias") or "neutral")
    confidence = str(predict_result.get("final_confidence") or "low")
    bias_cn = _cn(_BIAS_CN, bias, bias)
    conf_cn = _cn(_CONFIDENCE_CN, confidence, confidence)
    bias_color = _BIAS_COLOR.get(bias, "#6b7280")
    conf_bg = {"high": "rgba(22,163,74,0.15)", "medium": "rgba(59,130,246,0.15)", "low": "rgba(107,114,128,0.15)"}.get(confidence, "rgba(107,114,128,0.15)")

    final_proj = _as_dict(predict_result.get("final_projection"))
    pred_open = str(final_proj.get("pred_open") or predict_result.get("pred_open") or _cn(_OPEN_CN, predict_result.get("open_tendency"), "—"))
    pred_path = str(final_proj.get("pred_path") or predict_result.get("pred_path") or "—")
    pred_close = str(final_proj.get("pred_close") or predict_result.get("pred_close") or _cn(_CLOSE_CN, predict_result.get("close_tendency"), "—"))

    readable = _as_dict(predict_result.get("readable_summary"))
    base = _as_dict(readable.get("baseline_judgment"))
    summary_text = str(base.get("text") or predict_result.get("prediction_summary") or "").strip()
    if not summary_text:
        summary_text = "—"

    path_risk = str(final_proj.get("path_risk") or predict_result.get("path_risk") or "—")

    left, right = st.columns([1, 1.6])

    with left:
        st.markdown(f"""
        <div class="pt-hero">
            <div style="font-size:0.78rem;opacity:0.7;letter-spacing:0.06em;">最终判断</div>
            <div class="pt-hero-dir" style="color:{bias_color};">{bias_cn}</div>
            <div>
                <span class="pt-hero-conf" style="background:{conf_bg};color:{bias_color};">
                    置信度：{conf_cn}
                </span>
            </div>
            <div class="pt-hero-summary">{summary_text}</div>
        </div>
        """, unsafe_allow_html=True)

    with right:
        g1, g2, g3, g4 = st.columns(4)
        with g1:
            st.markdown(f"""
            <div class="pt-pred-item">
                <div class="pt-pred-label">预测开盘</div>
                <div class="pt-pred-value">{pred_open}</div>
            </div>""", unsafe_allow_html=True)
        with g2:
            st.markdown(f"""
            <div class="pt-pred-item">
                <div class="pt-pred-label">预测路径</div>
                <div class="pt-pred-value">{pred_path}</div>
            </div>""", unsafe_allow_html=True)
        with g3:
            st.markdown(f"""
            <div class="pt-pred-item">
                <div class="pt-pred-label">预测收盘</div>
                <div class="pt-pred-value">{pred_close}</div>
            </div>""", unsafe_allow_html=True)
        with g4:
            st.markdown(f"""
            <div class="pt-pred-item">
                <div class="pt-pred-label">路径风险</div>
                <div class="pt-pred-value" style="font-size:1rem;">{path_risk}</div>
            </div>""", unsafe_allow_html=True)

        # Open/close narrative from readable summary
        open_text = str(_as_dict(readable.get("open_projection")).get("text") or "")
        close_text = str(_as_dict(readable.get("close_projection")).get("text") or "")
        if open_text or close_text:
            st.markdown("")
            if open_text:
                st.caption(f"**开盘判断：** {open_text}")
            if close_text:
                st.caption(f"**收盘判断：** {close_text}")


def _render_layer3_evidence(
    predict_result: dict,
    scan_result: dict | None,
    research_result: dict | None,
) -> None:
    """第三层：证据区（结构扫描 / 同业对照 / 研究补充）"""
    scan = _as_dict(scan_result)
    research = _as_dict(research_result)
    peer = _as_dict(predict_result.get("peer_adjustment"))
    primary = _as_dict(predict_result.get("primary_projection"))
    readable = _as_dict(predict_result.get("readable_summary"))

    col_scan, col_peer, col_research = st.columns(3)

    # ── 结构扫描 ──────────────────────────────────────────────────────────────
    with col_scan:
        st.markdown('<div class="pt-ev-section">结构扫描</div>', unsafe_allow_html=True)
        scan_bias_cn = _cn(_BIAS_CN, scan.get("scan_bias"), "—")
        scan_conf_cn = _cn(_CONFIDENCE_CN, scan.get("scan_confidence"), "—")
        gap_cn = _cn(_GAP_CN, scan.get("avgo_gap_state"), "—")
        intra_cn = _cn(_INTRA_CN, scan.get("avgo_intraday_state"), "—")
        confirm_cn = _cn(_CONFIRM_CN, scan.get("confirmation_state"), "—")
        confirm_color = {"信号一致": "#1f7a4f", "信号背离": "#b42318", "信号混合": "#b36b00"}.get(confirm_cn, "#6b7280")

        hist = _as_dict(scan.get("historical_match_summary"))
        hist_bias_cn = _cn(_BIAS_CN, hist.get("dominant_historical_outcome"), "—")
        exact_n = hist.get("exact_match_count", 0)
        near_n = hist.get("near_match_count", 0)

        rows = [
            ("扫描方向", f"{scan_bias_cn} / {scan_conf_cn}"),
            ("开盘结构", gap_cn),
            ("日内结构", intra_cn),
            ("确认状态", f'<span style="color:{confirm_color};">{confirm_cn}</span>'),
            ("历史完全匹配", f"{exact_n} 条"),
            ("历史近似匹配", f"{near_n} 条"),
            ("历史主导倾向", hist_bias_cn),
        ]
        for lbl, val in rows:
            st.markdown(
                f'<div class="pt-ev-row"><span class="pt-ev-lbl">{lbl}</span>'
                f'<span class="pt-ev-val">{val}</span></div>',
                unsafe_allow_html=True,
            )

        # Rationale from readable summary
        rationale = readable.get("rationale") or []
        if rationale:
            with st.expander("判断依据"):
                for line in rationale[:6]:
                    st.caption(f"• {line}")

        # Supporting / conflicting factors
        supporting = predict_result.get("supporting_factors") or []
        conflicting = predict_result.get("conflicting_factors") or []
        if supporting or conflicting:
            with st.expander("支持 / 冲突因素"):
                if supporting:
                    st.markdown("**支持因素**")
                    for f in supporting[:5]:
                        st.caption(f"+ {f}")
                if conflicting:
                    st.markdown("**冲突因素**")
                    for f in conflicting[:4]:
                        st.caption(f"- {f}")

    # ── 外部/同业对照 ─────────────────────────────────────────────────────────
    with col_peer:
        st.markdown('<div class="pt-ev-section">外部 / 同业对照</div>', unsafe_allow_html=True)

        adj_dir_cn = _cn(_PEER_ADJ_CN, peer.get("adjustment_direction"), "—")
        adj_bias_cn = _cn(_BIAS_CN, peer.get("adjusted_bias"), "—")
        adj_conf_cn = _cn(_CONFIDENCE_CN, peer.get("adjusted_confidence"), "—")

        rows = [
            ("同业调整方向", adj_dir_cn),
            ("确认同向", f"{peer.get('confirm_count', '—')} 家"),
            ("反向", f"{peer.get('oppose_count', '—')} 家"),
            ("调整后方向", adj_bias_cn),
            ("调整后置信度", adj_conf_cn),
        ]
        for lbl, val in rows:
            st.markdown(
                f'<div class="pt-ev-row"><span class="pt-ev-lbl">{lbl}</span>'
                f'<span class="pt-ev-val">{val}</span></div>',
                unsafe_allow_html=True,
            )

        # Primary projection source info
        if primary:
            st.markdown("")
            src = str(primary.get("source") or "—")
            lookback = str(primary.get("lookback_days") or "—")
            peer_used = "是" if primary.get("peer_inputs_used") else "否"
            st.caption(f"主推演来源：{src}")
            st.caption(f"回溯交易日：{lookback} 天")
            st.caption(f"同业数据已纳入：{peer_used}")

        # Path risk adjustment
        path_risk_adj = _as_dict(predict_result.get("peer_path_risk_adjustment"))
        if path_risk_adj:
            with st.expander("路径风险调整详情"):
                st.json(path_risk_adj)

    # ── 研究补充 ──────────────────────────────────────────────────────────────
    with col_research:
        st.markdown('<div class="pt-ev-section">研究补充</div>', unsafe_allow_html=True)

        if not research:
            st.markdown(
                '<div style="font-size:0.85rem;color:#94a3b8;padding:10px 0;">'
                '暂未接入 Research 数据。<br>在 Research 标签页运行后将在此显示。'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            sentiment_cn = _cn(_BIAS_CN, research.get("sentiment_bias"), "—")
            adj_cn = _cn(_RESEARCH_ADJ_CN, research.get("research_bias_adjustment"), "—")
            narrative = str(research.get("market_narrative_summary") or "—")
            notes_text = str(research.get("notes") or "—")

            rows = [
                ("市场情绪", sentiment_cn),
                ("研究调整", adj_cn),
            ]
            for lbl, val in rows:
                st.markdown(
                    f'<div class="pt-ev-row"><span class="pt-ev-lbl">{lbl}</span>'
                    f'<span class="pt-ev-val">{val}</span></div>',
                    unsafe_allow_html=True,
                )
            st.markdown("")
            st.caption(f"**叙事摘要：** {narrative}")
            st.caption(f"**备注：** {notes_text}")

        # Risk reminders
        risk_reminders = readable.get("risk_reminders") or []
        if risk_reminders:
            with st.expander("风险提醒"):
                for line in risk_reminders[:5]:
                    st.caption(f"⚠ {line}")

    # AI projection summary (optional, triggered by button)
    st.markdown("")
    with st.expander("生成 AI 推演总结（可选）"):
        _render_projection_ai_summary_entry_compact(predict_result, scan_result, research_result)

    _render_exclusion_reliability_review(predict_result)

    # Raw JSON (collapsed)
    with st.expander("推演原始数据（调试用）"):
        st.json(predict_result)


def _render_projection_ai_summary_entry_compact(
    predict_result: dict,
    scan_result: dict | None,
    research_result: dict | None,
) -> None:
    if st.button("生成 AI 推演总结", key="btn_generate_ai_projection_summary"):
        payload = _projection_ai_payload(predict_result, scan_result, research_result)
        with st.spinner("正在生成 AI 推演总结…"):
            try:
                st.session_state["ai_projection_summary_text"] = build_projection_ai_summary(payload)
            except Exception as exc:
                _show_ai_summary_error("AI 推演总结", exc)
    if st.session_state.get("ai_projection_summary_text"):
        st.write(st.session_state["ai_projection_summary_text"])


def _render_review_result(review_result: dict) -> None:
    """Render the output of run_review_for_prediction()."""
    status = review_result.get("status", "error")
    if status != "ok":
        st.warning(f"复盘未完成：{review_result.get('error', '未知错误')}")
        return

    comparison = review_result.get("comparison", {})
    error_info = review_result.get("error_info", {})
    review_summary = review_result.get("review_summary", "")

    correct_count = comparison.get("correct_count", 0)
    total_count = comparison.get("total_count", 3)
    overall_score = comparison.get("overall_score", 0.0)
    score_color = "#2ecc71" if overall_score >= 0.67 else "#e67e22" if overall_score >= 0.34 else "#e74c3c"
    st.markdown(
        f'<div style="font-size:1.4em;font-weight:bold;color:{score_color}">'
        f'复盘得分 {correct_count}/{total_count}（{overall_score:.0%}）'
        f'</div>',
        unsafe_allow_html=True,
    )

    primary = error_info.get("primary_error")
    if primary:
        st.error(f"主要问题：{primary}")
    else:
        st.success("三项判断均正确 ✓")

    dim_detail = error_info.get("dimension_detail", {})
    dim_names = {"open": "开盘", "path": "路径", "close": "收盘"}
    rows = []
    for dim in ("open", "path", "close"):
        d = dim_detail.get(dim, {})
        flag = d.get("correct")
        tag = {True: "✓ 正确", False: "✗ 错误", None: "？未知"}.get(flag, "？未知")
        rows.append({"维度": dim_names[dim], "预测": d.get("predicted") or "—", "实际": d.get("actual") or "—", "结果": tag})
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    error_types = error_info.get("error_types", [])
    reason_guesses = error_info.get("reason_guesses", [])
    if error_types or reason_guesses:
        with st.expander("错误分析详情"):
            if error_types:
                st.markdown("**错误类型**")
                for et in error_types:
                    st.caption(f"· {et}")
            if reason_guesses:
                st.markdown("**原因推断**")
                for rg in reason_guesses:
                    st.caption(f"· {rg}")

    if review_summary:
        with st.expander("完整复盘摘要"):
            st.text(review_summary)

    direction_match = comparison.get("direction_match")
    error_category = comparison.get("error_category", "")
    dir_label = {1: "方向正确 ✓", 0: "方向错误 ✗", None: "N/A"}.get(direction_match, "？")
    c1, c2 = st.columns(2)
    c1.metric("方向判断", dir_label)
    c2.metric("错误分类", error_category.replace("_", " "))


def _render_layer4_operations(
    predict_result: dict,
    scan_result: dict | None,
    research_result: dict | None,
) -> None:
    """第四层：闭环操作区（步骤 1–5）"""
    prediction_for_date: str = st.session_state.get("target_date_str", "")
    snapshot_id: str = st.session_state.get("snapshot_id", "—")
    saved_pid: str | None = st.session_state.get("saved_prediction_id")
    saved_date: str = st.session_state.get("saved_prediction_date", "")
    already_saved = bool(saved_pid and saved_date == prediction_for_date)
    outcome = get_outcome_for_prediction(saved_pid) if already_saved else None

    # ── 步骤 1: 保存推演 ──────────────────────────────────────────────────────
    with st.expander("步骤一：保存本次推演", expanded=not already_saved):
        _status_badge("步骤一", "已完成" if already_saved else "待操作", done=already_saved)

        def _do_save() -> None:
            pid = save_prediction(
                symbol=str(predict_result.get("symbol", "AVGO")),
                prediction_for_date=prediction_for_date,
                scan_result=scan_result,
                research_result=research_result,
                predict_result=predict_result,
                snapshot_id=snapshot_id,
            )
            st.session_state["saved_prediction_id"] = pid
            st.session_state["saved_prediction_date"] = prediction_for_date

        if not already_saved:
            if st.button("保存今日推演", key="btn_save_prediction"):
                try:
                    _do_save()
                    st.rerun()
                except Exception as exc:
                    st.error(f"保存失败：{exc}")
        else:
            st.success(f"已保存 · ID: `{saved_pid[:8]}…`")
            st.caption("再次保存将创建新记录并重置本会话的结果/复盘状态。")
            if st.button("保存新版本 ↻", key="btn_save_new_version"):
                try:
                    _do_save()
                    st.rerun()
                except Exception as exc:
                    st.error(f"保存失败：{exc}")

    # ── 步骤 2: 抓取实际结果 ──────────────────────────────────────────────────
    with st.expander("步骤二：抓取实际结果", expanded=(already_saved and not outcome)):
        _status_badge("步骤二", "已完成" if outcome else ("待操作" if already_saved else "等待步骤一"), done=bool(outcome))
        if not already_saved:
            st.caption("请先完成步骤一（保存推演）。")
        elif outcome:
            direction_ok = outcome.get("direction_correct")
            close_chg = outcome.get("actual_close_change")
            label_cn = {1: "方向正确 ✓", 0: "方向错误 ✗", None: "方向中性"}.get(direction_ok, "？")
            chg_str = f"{close_chg * 100:+.2f}%" if close_chg is not None else "N/A"
            actual_close = outcome.get("actual_close")
            close_display = f"{actual_close:.2f}" if actual_close is not None else "N/A"
            st.success(f"{label_cn}  · 实际涨跌 {chg_str}  · 收盘价 {close_display}")
        else:
            if st.button("抓取实际结果", key="btn_capture_outcome"):
                with st.spinner("正在获取市场数据…"):
                    try:
                        capture_outcome(saved_pid)
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))

    # ── 步骤 3: 生成 AI 复盘 ─────────────────────────────────────────────────
    with st.expander("步骤三：生成 AI 复盘", expanded=False):
        review = None
        if not already_saved:
            _status_badge("步骤三", "等待步骤一", done=False)
            st.caption("请先完成步骤一。")
        elif not outcome:
            _status_badge("步骤三", "等待步骤二", done=False)
            st.caption("请先完成步骤二（抓取实际结果）。")
        else:
            review = get_review_for_prediction(saved_pid)
            if review:
                _status_badge("步骤三", "已完成", done=True)
                cat = review.get("error_category", "")
                cat_colors = {
                    "correct": "#1f7a4f",
                    "wrong_direction": "#b42318",
                    "right_direction_wrong_magnitude": "#b36b00",
                    "false_confidence": "#b36b00",
                    "insufficient_data": "#6b7280",
                }
                color = cat_colors.get(cat, "#6b7280")
                cat_labels = {
                    "correct": "判断正确",
                    "wrong_direction": "方向错误",
                    "right_direction_wrong_magnitude": "方向对但幅度偏差",
                    "false_confidence": "过度自信",
                    "insufficient_data": "信息不足",
                }
                cat_cn = cat_labels.get(cat, cat.replace("_", " "))
                st.markdown(f'<span style="color:{color};font-weight:700;">{cat_cn}</span>', unsafe_allow_html=True)
                with st.expander("查看 AI 复盘详情"):
                    st.markdown(f"**根本原因：** {review.get('root_cause', '—')}")
                    st.markdown(f"**置信度评估：** {review.get('confidence_note', '—')}")
                    st.markdown(f"**下次注意：** {review.get('watch_for_next_time', '—')}")
                    if review.get("raw_llm_output"):
                        with st.expander("大模型原始输出"):
                            st.text(review["raw_llm_output"])
            else:
                _status_badge("步骤三", "待操作", done=False)
                has_key = bool(os.getenv("ANTHROPIC_API_KEY", "").strip())
                label = "生成 AI 复盘" if has_key else "生成规则层复盘"
                if st.button(label, key="btn_generate_review"):
                    with st.spinner("正在生成复盘…"):
                        try:
                            generate_review(saved_pid)
                            st.rerun()
                        except ValueError as exc:
                            st.error(str(exc))

        # AI review summary
        st.markdown("")
        st.markdown("**AI 复盘总结**")
        if not already_saved:
            st.button("生成 AI 复盘总结", key="btn_generate_ai_review_summary_locked1", disabled=True)
            st.caption("请先完成步骤一。")
        elif not outcome:
            st.button("生成 AI 复盘总结", key="btn_generate_ai_review_summary_locked2", disabled=True)
            st.caption("请先完成步骤二。")
        else:
            if st.button("生成 AI 复盘总结", key="btn_generate_ai_review_summary"):
                payload = _review_ai_payload(
                    prediction_id=saved_pid,
                    predict_result=predict_result,
                    outcome=outcome,
                    review=review,
                )
                with st.spinner("正在生成 AI 复盘总结…"):
                    try:
                        st.session_state["ai_review_summary_text"] = build_review_ai_summary(payload)
                    except Exception as exc:
                        _show_ai_summary_error("AI 复盘总结", exc)
            if st.session_state.get("ai_review_summary_text"):
                st.write(st.session_state["ai_review_summary_text"])

    # ── 步骤 4: 确定性复盘 ───────────────────────────────────────────────────
    with st.expander("步骤四：运行确定性复盘", expanded=False):
        if already_saved and outcome:
            _status_badge("步骤四", "可运行", done=False)
            symbol_for_review = str(predict_result.get("symbol", "AVGO"))
            review_cache_key = f"review_result_{saved_pid}"
            cached = st.session_state.get(review_cache_key)
            if cached is None:
                st.caption("确定性复盘：规则层对比预测与实际结果，无需大模型。")
                if st.button("运行确定性复盘", key="btn_run_review"):
                    with st.spinner("正在运行复盘…"):
                        result = run_review_for_prediction(symbol_for_review, prediction_for_date)
                        st.session_state[review_cache_key] = result
                        st.rerun()
            else:
                _status_badge("步骤四", "已完成", done=True)
                _render_review_result(cached)
                if st.button("重新运行 ↻", key="btn_rerun_review"):
                    st.session_state.pop(review_cache_key, None)
                    st.rerun()
        else:
            _status_badge("步骤四", "等待步骤一和二", done=False)
            st.caption("请先完成步骤一（保存推演）和步骤二（抓取结果）。")

    # ── 步骤 5: 提炼规律 ─────────────────────────────────────────────────────
    with st.expander("步骤五：提炼规律", expanded=False):
        symbol_for_rules = str(predict_result.get("symbol", "AVGO"))
        rules_cache_key = f"review_rules_{symbol_for_rules}"
        st.caption("基于历史复盘记录，提炼当前系统命中规律和薄弱维度。")

        if st.button("提炼规律", key="btn_extract_rules"):
            with st.spinner("分析历史复盘…"):
                summary = summarize_review_history(symbol_for_rules, limit=30)
                rules = extract_review_rules(summary)
                st.session_state[rules_cache_key] = {"summary": summary, "rules": rules}
            st.rerun()

        cached_rules = st.session_state.get(rules_cache_key)
        if cached_rules:
            _status_badge("步骤五", "已提炼", done=True)
            try:
                from services.review_store import count_real_vs_historical
                src = count_real_vs_historical(symbol_for_rules)
                if src["real"] > 0:
                    st.caption(f"数据来源：{src['real']} 条真实预测复盘 + {src['historical']} 条历史训练数据")
                else:
                    st.caption(
                        f"⚠ 数据来源：全部 {src['total']} 条均为历史训练数据，"
                        "规律仅供参考，完成真实预测复盘后精度将提升。"
                    )
            except Exception:
                pass

            summary = cached_rules["summary"]
            rules = cached_rules["rules"]
            rc = summary.get("record_count", 0)
            oa = summary.get("overall_accuracy", 0.0)
            st.caption(f"基于最近 {rc} 条复盘 · 整体命中率 {oa:.0%}")
            for rule in rules:
                st.markdown(f"- {rule}")

            with st.expander("原始统计数据"):
                dim_acc = summary.get("dimension_accuracy", {})
                dim_n = summary.get("dimension_sample_count", {})
                rows_stats = [
                    {
                        "维度": {"open": "开盘", "path": "路径", "close": "收盘"}.get(d, d),
                        "准确率": f"{dim_acc[d]:.0%}" if dim_acc.get(d) is not None else "N/A",
                        "样本数": dim_n.get(d, 0),
                    }
                    for d in ("open", "path", "close")
                ]
                st.dataframe(pd.DataFrame(rows_stats), hide_index=True, use_container_width=True)
                st.json({
                    "error_category_counts": summary.get("error_category_counts", {}),
                    "primary_error_counts": summary.get("primary_error_counts", {}),
                })

            if st.button("重新分析 ↻", key="btn_rerun_rules"):
                st.session_state.pop(rules_cache_key, None)
                st.rerun()


def _status_badge(step_label: str, status_text: str, *, done: bool) -> None:
    color = "#1f7a4f" if done else "#6b7280"
    bg = "rgba(22,163,74,0.1)" if done else "rgba(107,114,128,0.08)"
    st.markdown(
        f'<span class="pt-step-badge" style="background:{bg};color:{color};">'
        f'{step_label}：{status_text}</span>',
        unsafe_allow_html=True,
    )
    st.markdown("")


def _render_exclusion_reliability_review(predict_result: dict | None) -> None:
    prediction_date = None
    if isinstance(predict_result, dict):
        prediction_date = (
            predict_result.get("analysis_date")
            or predict_result.get("prediction_date")
        )
    row = build_contradiction_card_payload(
        predict_result,
        prediction_date=prediction_date,
    )
    render_exclusion_reliability_review_for_row(row)


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def render_predict_tab(scan_result: dict | None, research_result: dict | None) -> dict | None:
    st.markdown(_CSS, unsafe_allow_html=True)

    if scan_result is None:
        st.info("请先在侧边栏选择日期并运行 Scan，再进入推演页。")
        return None

    if research_result is None:
        st.warning("未检测到 Research 结果，推演将以 Scan 数据为主。建议先在 Research 标签页运行研究。")

    # ── 计算推演结果 ──────────────────────────────────────────────────────────
    _briefing_pre_key = "pre_briefing_AVGO_global"
    if _briefing_pre_key not in st.session_state:
        st.session_state[_briefing_pre_key] = build_pre_prediction_briefing(
            "AVGO", limit=30, max_rules=3
        )
    _pre_briefing_for_predict = st.session_state[_briefing_pre_key]

    predict_result = run_predict(scan_result, research_result, pre_briefing=_pre_briefing_for_predict)
    predict_result["readable_summary"] = build_predict_readable_summary(
        predict_result, scan_result=scan_result
    )
    predict_result["evidence_trace"] = build_projection_evidence_trace(
        predict_result=predict_result,
        scan_result=scan_result,
    )

    # Briefing for display (may include scenario context)
    symbol_for_briefing = str(predict_result.get("symbol", "AVGO"))
    pred_open_for_briefing = predict_result.get("open_tendency")
    briefing_cache_key = f"pre_briefing_{symbol_for_briefing}_{pred_open_for_briefing}"
    if briefing_cache_key not in st.session_state:
        st.session_state[briefing_cache_key] = build_pre_prediction_briefing(
            symbol_for_briefing, limit=30, max_rules=3, pred_open=pred_open_for_briefing
        )
    display_briefing = st.session_state[briefing_cache_key]

    # ── 四层结构 ──────────────────────────────────────────────────────────────
    target_date_str: str = st.session_state.get("target_date_str", "")

    st.markdown('<div class="pt-section-title">博通（AVGO）推演页</div>', unsafe_allow_html=True)

    # 第一层：顶部上下文区
    st.markdown("**① 当前上下文**")
    _render_layer1_context(predict_result, display_briefing, target_date_str)

    st.divider()

    # 第二层：主结论卡
    st.markdown("**② 主结论**")
    _render_layer2_conclusion(predict_result, scan_result)

    st.divider()

    # 第三层：证据区
    st.markdown("**③ 证据区**")
    _render_layer3_evidence(predict_result, scan_result, research_result)

    st.divider()

    # 第四层：闭环操作区
    st.markdown("**④ 闭环操作区**")
    st.caption("保存推演 → 抓取结果 → 生成复盘 → 确定性复盘 → 提炼规律")
    _render_layer4_operations(predict_result, scan_result, research_result)

    return predict_result
