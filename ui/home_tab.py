from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _file_mtime_str(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return "文件不存在"
    ts = datetime.fromtimestamp(p.stat().st_mtime)
    return ts.strftime("%Y-%m-%d %H:%M")


def _file_age_days(path: str) -> float | None:
    p = Path(path)
    if not p.exists():
        return None
    mtime = datetime.fromtimestamp(p.stat().st_mtime)
    return (datetime.now() - mtime).total_seconds() / 86400


def _age_badge(age_days: float | None) -> tuple[str, str]:
    """Returns (label, color) for data freshness."""
    if age_days is None:
        return "无文件", "#6b7280"
    if age_days <= 1.5:
        return "最新", "#1f7a4f"
    if age_days <= 4:
        return "较新", "#b36b00"
    return "已过期", "#b42318"


def _system_status_label(data_age: float | None, coded_age: float | None) -> tuple[str, str]:
    if data_age is None or coded_age is None:
        return "等待更新", "#6b7280"
    if data_age > 4 or coded_age > 4:
        return "数据过期", "#b42318"
    if data_age > 1.5 or coded_age > 1.5:
        return "数据偏旧，建议更新", "#b36b00"
    return "可推演", "#1f7a4f"


_BIAS_CN: dict[str, str] = {
    "up_bias":             "偏多（看涨）",
    "down_bias":           "偏空（看跌）",
    "mixed":               "震荡（多空分歧）",
    "insufficient_sample": "样本不足",
}

_CONFIDENCE_CN: dict[str, str] = {
    "high":   "高",
    "medium": "中",
    "low":    "低",
    "unavailable": "不可用",
}

_STATUS_CN: dict[str, str] = {
    "saved":            "已保存",
    "outcome_captured": "已抓结果",
    "review_generated": "已复盘",
}

_CAUTION_CN: dict[str, str] = {
    "none":   "无数据",
    "low":    "低",
    "medium": "中等",
    "high":   "较高",
}

_CAUTION_COLOR: dict[str, str] = {
    "none":   "#6b7280",
    "low":    "#1f7a4f",
    "medium": "#b36b00",
    "high":   "#b42318",
}


def _parse_predict_result(row: dict) -> dict:
    """Extract display fields from a prediction_log row."""
    raw = row.get("predict_result_json") or "{}"
    try:
        pr = json.loads(raw) if isinstance(raw, str) else _as_dict(raw)
    except Exception:
        pr = {}
    readable = _as_dict(pr.get("readable_summary"))
    return {
        "final_bias":       _BIAS_CN.get(str(pr.get("final_bias") or ""), str(pr.get("final_bias") or "—")),
        "final_confidence": _CONFIDENCE_CN.get(str(pr.get("final_confidence") or ""), str(pr.get("final_confidence") or "—")),
        "open_tendency":    str(pr.get("open_tendency") or readable.get("open_judgment") or "—"),
        "path_tendency":    str(pr.get("path_tendency") or readable.get("path_judgment") or "—"),
        "close_tendency":   str(pr.get("close_tendency") or readable.get("close_judgment") or "—"),
        "prediction_summary": str(pr.get("prediction_summary") or ""),
    }


# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────

_CSS = """
<style>
.cc-hero {
    padding: 18px 22px;
    border: 1px solid rgba(148,163,184,0.25);
    border-radius: 16px;
    background: linear-gradient(135deg, rgba(13,27,42,0.97), rgba(18,52,86,0.93));
    color: #f8fafc;
    margin-bottom: 18px;
}
.cc-section {
    margin-top: 20px;
    margin-bottom: 6px;
    font-size: 1.05rem;
    font-weight: 700;
    color: #1e293b;
    border-left: 4px solid #3b82f6;
    padding-left: 10px;
}
.cc-card {
    padding: 14px 16px;
    border: 1px solid rgba(148,163,184,0.22);
    border-radius: 12px;
    background: rgba(248,250,252,0.03);
    min-height: 90px;
}
.cc-label {
    font-size: 0.78rem;
    color: #64748b;
    margin-bottom: 5px;
}
.cc-value {
    font-size: 1.35rem;
    font-weight: 700;
    line-height: 1.2;
}
.cc-sub {
    font-size: 0.82rem;
    color: #94a3b8;
    margin-top: 4px;
}
.cc-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.82rem;
    font-weight: 600;
}
.cc-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 6px 0;
    border-bottom: 1px solid rgba(148,163,184,0.12);
    font-size: 0.88rem;
}
.cc-row-label {
    color: #64748b;
    min-width: 110px;
}
.cc-row-value {
    font-weight: 600;
    color: #1e293b;
}
.cc-warn {
    background: rgba(239,68,68,0.07);
    border: 1px solid rgba(239,68,68,0.25);
    border-radius: 10px;
    padding: 10px 14px;
    font-size: 0.87rem;
    color: #7f1d1d;
    margin-bottom: 7px;
}
.cc-info {
    background: rgba(59,130,246,0.06);
    border: 1px solid rgba(59,130,246,0.2);
    border-radius: 10px;
    padding: 10px 14px;
    font-size: 0.87rem;
    color: #1e3a5f;
    margin-bottom: 7px;
}
.cc-nav-hint {
    font-size: 0.75rem;
    color: #94a3b8;
    margin-top: 4px;
    text-align: center;
}
</style>
"""


# ─────────────────────────────────────────────────────────────────────────────
# Section renderers
# ─────────────────────────────────────────────────────────────────────────────

def _render_system_status() -> None:
    import streamlit as st

    data_path     = "data/AVGO.csv"
    features_path = "enriched_data/AVGO_features.csv"
    coded_path    = "coded_data/AVGO_coded.csv"
    training_path = "avgo_1000day_training_report.json"

    data_ts     = _file_mtime_str(data_path)
    features_ts = _file_mtime_str(features_path)
    coded_ts    = _file_mtime_str(coded_path)
    training_ts = _file_mtime_str(training_path)

    data_age     = _file_age_days(data_path)
    coded_age    = _file_age_days(coded_path)
    training_age = _file_age_days(training_path)

    sys_label, sys_color = _system_status_label(data_age, coded_age)

    _, badge_color_data  = _age_badge(data_age)
    _, badge_color_coded = _age_badge(coded_age)
    _, badge_color_train = _age_badge(training_age)

    st.markdown('<div class="cc-section">① 系统状态</div>', unsafe_allow_html=True)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(f"""
        <div class="cc-card">
            <div class="cc-label">原始数据更新时间</div>
            <div class="cc-value" style="font-size:1rem;">{data_ts}</div>
            <div class="cc-sub" style="color:{badge_color_data};">AVGO.csv</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="cc-card">
            <div class="cc-label">编码数据更新时间</div>
            <div class="cc-value" style="font-size:1rem;">{features_ts}</div>
            <div class="cc-sub">AVGO_features.csv</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="cc-card">
            <div class="cc-label">匹配结果更新时间</div>
            <div class="cc-value" style="font-size:1rem;">{coded_ts}</div>
            <div class="cc-sub">AVGO_coded.csv</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="cc-card">
            <div class="cc-label">最近一次训练时间</div>
            <div class="cc-value" style="font-size:1rem;">{training_ts}</div>
            <div class="cc-sub" style="color:{badge_color_train};">训练报告</div>
        </div>""", unsafe_allow_html=True)
    with c5:
        st.markdown(f"""
        <div class="cc-card">
            <div class="cc-label">当前系统状态</div>
            <div class="cc-value" style="color:{sys_color};">{sys_label}</div>
            <div class="cc-sub">基于数据文件时效判断</div>
        </div>""", unsafe_allow_html=True)


def _render_quick_nav() -> None:
    import streamlit as st

    st.markdown('<div class="cc-section">② 快速进入</div>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        if st.button("📊  进入扫描页", key="cc_nav_scan", use_container_width=True):
            _navigate_to_main_view("scan")
        st.markdown('<div class="cc-nav-hint">点击后直接进入扫描页</div>', unsafe_allow_html=True)

    with c2:
        if st.button("🔮  进入推演页", key="cc_nav_predict", use_container_width=True):
            _navigate_to_main_view("predict")
        st.markdown('<div class="cc-nav-hint">点击后直接进入推演页</div>', unsafe_allow_html=True)

    with c3:
        if st.button("📋  进入复盘页", key="cc_nav_review", use_container_width=True):
            _navigate_to_main_view("review")
        st.markdown('<div class="cc-nav-hint">点击后直接进入复盘页</div>', unsafe_allow_html=True)

    with c4:
        if st.button("🗂  进入历史页", key="cc_nav_history", use_container_width=True):
            _navigate_to_main_view("history")
        st.markdown('<div class="cc-nav-hint">点击后直接进入历史页</div>', unsafe_allow_html=True)

    with c5:
        if st.button("⚙️  触发日常训练", key="cc_run_automation", use_container_width=True):
            with st.spinner("正在执行训练流程，请稍候…"):
                from services.automation_wrapper import run_daily_automation
                from services.daily_training_pipeline import build_daily_training_report
                from services.daily_training_summary import build_daily_training_brief
                from services.dashboard_view_model import build_rule_dashboard_view
                result = run_daily_automation(
                    symbol="AVGO",
                    _pipeline_runner=build_daily_training_report,
                    _summary_builder=build_daily_training_brief,
                    _dashboard_builder=build_rule_dashboard_view,
                )
            st.session_state["_cc_automation_result"] = result
            status = result.get("run_status", "unknown")
            if status == "ok":
                st.success(f"训练完成：{result.get('summary', '')}")
            elif status == "partial":
                st.warning(f"训练部分完成：{result.get('summary', '')}")
            else:
                st.error(f"训练失败：{result.get('summary', '')}")
        st.markdown('<div class="cc-nav-hint">日常训练</div>', unsafe_allow_html=True)


def _navigate_to_main_view(view_key: str) -> None:
    import streamlit as st

    st.session_state["active_main_view"] = view_key
    st.rerun()


def _render_latest_prediction() -> None:
    import streamlit as st
    from services.prediction_store import list_predictions

    st.markdown('<div class="cc-section">③ 最近一次推演</div>', unsafe_allow_html=True)

    try:
        rows = list_predictions(limit=1)
    except Exception as exc:
        st.caption(f"读取推演记录失败：{exc}")
        return

    if not rows:
        st.markdown(
            '<div class="cc-info">暂无推演记录。请先在「Predict」标签页完成一次推演并保存。</div>',
            unsafe_allow_html=True,
        )
        return

    row = rows[0]
    parsed = _parse_predict_result(row)
    status_cn = _STATUS_CN.get(str(row.get("status") or ""), str(row.get("status") or "—"))
    status_color = {"已保存": "#b36b00", "已抓结果": "#1f7a4f", "已复盘": "#3b82f6"}.get(status_cn, "#6b7280")

    left, right = st.columns([2, 1])

    with left:
        st.markdown(f"""
        <div class="cc-card">
            <div class="cc-row">
                <span class="cc-row-label">推演日期</span>
                <span class="cc-row-value">{row.get('prediction_for_date', '—')}</span>
            </div>
            <div class="cc-row">
                <span class="cc-row-label">最终方向</span>
                <span class="cc-row-value">{parsed['final_bias']}</span>
            </div>
            <div class="cc-row">
                <span class="cc-row-label">最终置信度</span>
                <span class="cc-row-value">{parsed['final_confidence']}</span>
            </div>
            <div class="cc-row">
                <span class="cc-row-label">开盘判断</span>
                <span class="cc-row-value">{parsed['open_tendency']}</span>
            </div>
            <div class="cc-row">
                <span class="cc-row-label">路径判断</span>
                <span class="cc-row-value">{parsed['path_tendency']}</span>
            </div>
            <div class="cc-row" style="border-bottom:none;">
                <span class="cc-row-label">收盘判断</span>
                <span class="cc-row-value">{parsed['close_tendency']}</span>
            </div>
        </div>""", unsafe_allow_html=True)

    with right:
        st.markdown(f"""
        <div class="cc-card">
            <div class="cc-label">当前状态</div>
            <div class="cc-value" style="color:{status_color};">{status_cn}</div>
            <div class="cc-sub">分析日期：{row.get('analysis_date', '—')}</div>
            <div class="cc-sub" style="margin-top:8px;">保存时间：{str(row.get('created_at', '—'))[:16]}</div>
        </div>""", unsafe_allow_html=True)


def _render_latest_review() -> None:
    import streamlit as st
    from services.review_store import load_review_records

    st.markdown('<div class="cc-section">④ 最近一次复盘</div>', unsafe_allow_html=True)

    try:
        records = load_review_records(symbol="AVGO", limit=10)
    except Exception as exc:
        st.caption(f"读取复盘记录失败：{exc}")
        return

    # Prefer real reviews (source != 'historical') first
    real_records = [r for r in records if r.get("source") != "historical"]
    display = real_records[0] if real_records else (records[0] if records else None)

    if display is None:
        st.markdown(
            '<div class="cc-info">暂无复盘记录。请先在「复盘中心」标签页对推演进行复盘。</div>',
            unsafe_allow_html=True,
        )
        return

    score = _safe_float(display.get("overall_score"))
    score_str = f"{score:.2f}" if score is not None else "—"
    score_pct = f"{score*100:.0f}%" if score is not None else "—"
    score_color = "#1f7a4f" if (score or 0) >= 0.67 else ("#b36b00" if (score or 0) >= 0.34 else "#b42318")

    error_cat = str(display.get("error_category") or "—")
    primary_err = str(display.get("primary_error") or "—")
    review_summary = str(display.get("review_summary") or "").strip()
    rule_extraction = _as_dict(display.get("rule_extraction_json"))
    has_rule = bool(rule_extraction)
    is_real = display.get("source") != "historical"
    source_label = "真实复盘" if is_real else "历史训练数据"
    source_color = "#1f7a4f" if is_real else "#6b7280"

    left, right = st.columns([2, 1])

    with left:
        st.markdown(f"""
        <div class="cc-card">
            <div class="cc-row">
                <span class="cc-row-label">复盘日期</span>
                <span class="cc-row-value">{display.get('prediction_for_date', '—')}</span>
            </div>
            <div class="cc-row">
                <span class="cc-row-label">复盘得分</span>
                <span class="cc-row-value" style="color:{score_color};">{score_str}（{score_pct}）</span>
            </div>
            <div class="cc-row">
                <span class="cc-row-label">错误类型</span>
                <span class="cc-row-value">{error_cat}</span>
            </div>
            <div class="cc-row" style="border-bottom:none;">
                <span class="cc-row-label">主要误判维度</span>
                <span class="cc-row-value">{primary_err}</span>
            </div>
        </div>""", unsafe_allow_html=True)

    with right:
        rule_text = "是（已提炼规律）" if has_rule else "否"
        rule_color = "#1f7a4f" if has_rule else "#6b7280"
        st.markdown(f"""
        <div class="cc-card">
            <div class="cc-label">数据来源</div>
            <div class="cc-value" style="color:{source_color};font-size:1rem;">{source_label}</div>
            <div class="cc-label" style="margin-top:10px;">触发历史规律介入</div>
            <div class="cc-value" style="color:{rule_color};font-size:1rem;">{rule_text}</div>
        </div>""", unsafe_allow_html=True)

    if review_summary:
        st.caption(f"**复盘摘要：** {review_summary[:200]}")


def _render_rules_and_training() -> None:
    import streamlit as st
    from services.review_store import count_real_vs_historical
    from services.review_analyzer import summarize_review_history, extract_review_rules
    from services.pre_prediction_briefing import build_pre_prediction_briefing

    st.markdown('<div class="cc-section">⑤ 规律与训练状态</div>', unsafe_allow_html=True)

    try:
        counts = count_real_vs_historical(symbol="AVGO")
        real_count = counts.get("real", 0)
        hist_count = counts.get("historical", 0)
        total_count = counts.get("total", 0)
    except Exception:
        real_count = hist_count = total_count = 0

    try:
        briefing = build_pre_prediction_briefing(symbol="AVGO", limit=30, max_rules=3)
        caution_level = briefing.get("caution_level", "none")
        caution_cn = _CAUTION_CN.get(caution_level, caution_level)
        caution_color = _CAUTION_COLOR.get(caution_level, "#6b7280")
        rule_scope = briefing.get("rule_scope", "global")
        rule_scope_cn = "全局规律" if rule_scope == "global" else "场景规律"
        has_data = briefing.get("has_data", False)
        intervention_label = "会介入推演（有历史规律）" if has_data else "不介入（暂无数据）"
        intervention_color = "#1f7a4f" if has_data else "#6b7280"
    except Exception:
        caution_cn = "未知"
        caution_color = "#6b7280"
        rule_scope_cn = "—"
        intervention_label = "—"
        intervention_color = "#6b7280"

    # Training status: check session_state for this session's run, fallback to file mtime
    auto_result = _as_dict(st.session_state.get("_cc_automation_result"))
    if auto_result:
        train_status = "已运行（本次会话）"
        train_color = "#1f7a4f"
    else:
        training_age = _file_age_days("avgo_1000day_training_report.json")
        if training_age is None:
            train_status = "未检测到训练报告"
            train_color = "#6b7280"
        elif training_age <= 1.5:
            train_status = "今日已运行"
            train_color = "#1f7a4f"
        else:
            train_status = f"上次训练约 {training_age:.0f} 天前"
            train_color = "#b36b00" if training_age <= 7 else "#b42318"

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(f"""
        <div class="cc-card">
            <div class="cc-label">真实复盘条数</div>
            <div class="cc-value">{real_count}</div>
            <div class="cc-sub">来自实际推演后复盘</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="cc-card">
            <div class="cc-label">历史训练条数</div>
            <div class="cc-value">{hist_count}</div>
            <div class="cc-sub">来自历史导入数据</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="cc-card">
            <div class="cc-label">当前风险等级</div>
            <div class="cc-value" style="color:{caution_color};">{caution_cn}</div>
            <div class="cc-sub">{rule_scope_cn}</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="cc-card">
            <div class="cc-label">规律是否介入推演</div>
            <div class="cc-value" style="color:{intervention_color};font-size:1rem;">{intervention_label}</div>
            <div class="cc-sub">仅为建议，不改变算法</div>
        </div>""", unsafe_allow_html=True)
    with c5:
        st.markdown(f"""
        <div class="cc-card">
            <div class="cc-label">日常训练状态</div>
            <div class="cc-value" style="color:{train_color};font-size:1rem;">{train_status}</div>
            <div class="cc-sub">手动触发版</div>
        </div>""", unsafe_allow_html=True)

    # Show top rules if available
    try:
        top_rules = briefing.get("top_rules", [])
        if top_rules:
            st.markdown("**当前规律提炼（最近30条复盘）：**")
            for rule in top_rules:
                st.caption(f"• {rule}")
    except Exception:
        pass


def _render_risk_warnings() -> None:
    import streamlit as st
    from services.review_store import count_real_vs_historical

    st.markdown('<div class="cc-section">⑥ 风险提示</div>', unsafe_allow_html=True)

    warnings: list[tuple[str, str]] = []

    try:
        counts = count_real_vs_historical(symbol="AVGO")
        real_count = counts.get("real", 0)
    except Exception:
        real_count = 0

    if real_count == 0:
        warnings.append(("warn", "当前真实复盘样本为零，所有规律均来自历史训练数据，仅供参考，请勿作为决策依据。"))
    elif real_count < 5:
        warnings.append(("warn", f"当前真实复盘样本较少（{real_count} 条），规律提炼可靠性有限，建议积累更多复盘后再依赖规律。"))

    training_age_w = _file_age_days("avgo_1000day_training_report.json")
    if training_age_w is None:
        warnings.append(("warn", "未检测到训练报告文件，训练系统状态未知，建议手动触发一次日常训练。"))
    elif training_age_w > 7:
        warnings.append(("warn", f"训练系统已 {training_age_w:.0f} 天未运行，规律池可能已过期，建议尽快触发日常训练。"))

    data_age = _file_age_days("data/AVGO.csv")
    if data_age is not None and data_age > 3:
        warnings.append(("warn", f"原始数据文件已 {data_age:.0f} 天未更新，推演结果可能基于过期行情，请先更新数据。"))

    warnings.append(("info", "当前训练系统为手动触发版本，不会自动执行，请在需要时手动点击「触发日常训练」。"))
    warnings.append(("info", "外部宏观因素（美联储、财报、地缘事件等）不在本系统覆盖范围内，推演前请自行核查外部确认信号。"))
    warnings.append(("info", "所有 AI 输出仅作结构化参考，最终判断需结合个人风控体系，本系统不构成投资建议。"))

    for kind, text in warnings:
        css_class = "cc-warn" if kind == "warn" else "cc-info"
        prefix = "⚠ " if kind == "warn" else "ℹ "
        st.markdown(f'<div class="{css_class}">{prefix}{text}</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def render_home_tab(payload: dict[str, Any] | None) -> None:
    import streamlit as st

    st.markdown(_CSS, unsafe_allow_html=True)

    # Hero banner
    st.markdown("""
    <div class="cc-hero">
        <div style="font-size:0.8rem;opacity:0.75;letter-spacing:0.05em;">博通研究系统 · AVGO</div>
        <div style="font-size:1.9rem;font-weight:800;margin-top:4px;">博通（AVGO）系统总控台</div>
        <div style="margin-top:6px;font-size:0.92rem;opacity:0.88;">
            研究循环 · 预测日志 · 复盘追踪 · 规律提炼
        </div>
    </div>
    """, unsafe_allow_html=True)

    _render_system_status()
    st.markdown("---")
    _render_quick_nav()
    st.markdown("---")
    _render_latest_prediction()
    st.markdown("---")
    _render_latest_review()
    st.markdown("---")
    _render_rules_and_training()
    st.markdown("---")
    _render_risk_warnings()
