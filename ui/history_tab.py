from __future__ import annotations

import json
from collections import Counter
from typing import Any

import pandas as pd
import streamlit as st

from services.prediction_store import (
    PredictionStoreCorruptionError,
    get_outcome_for_prediction,
    get_prediction,
    get_review_for_prediction,
    list_predictions,
)

# ─────────────────────────────────────────────────────────────────────────────
# Label maps
# ─────────────────────────────────────────────────────────────────────────────

_BIAS_CN = {
    "bullish":             "偏多",
    "bearish":             "偏空",
    "neutral":             "中性",
    "up_bias":             "偏多",
    "down_bias":           "偏空",
    "mixed":               "多空分歧",
    "insufficient_sample": "样本不足",
    "unavailable":         "不可用",
}
_CONFIDENCE_CN = {"high": "高", "medium": "中", "low": "低"}
_STATUS_CN = {
    "saved":            "已保存",
    "outcome_captured": "已抓结果",
    "review_generated": "已复盘",
}
_STATUS_ORDER = {"saved": 0, "outcome_captured": 1, "review_generated": 2}
_STATUS_COLOR = {
    "已保存":    "#b36b00",
    "已抓结果":  "#1f7a4f",
    "已复盘":    "#3b82f6",
}
_OPEN_CN = {
    "gap_up_bias": "高开", "gap_down_bias": "低开", "flat_bias": "平开",
    "gap_up": "高开", "gap_down": "低开", "flat": "平开", "unclear": "待确认",
}
_CLOSE_CN = {
    "close_strong": "收涨", "close_weak": "收跌", "range": "震荡", "unclear": "待确认",
}

_CSS = """
<style>
.ht-section {
    font-size: 1.05rem;
    font-weight: 700;
    color: #1e293b;
    border-left: 4px solid #3b82f6;
    padding-left: 10px;
    margin: 18px 0 10px 0;
}
.ht-kpi {
    padding: 14px 16px;
    border: 1px solid rgba(148,163,184,0.22);
    border-radius: 12px;
    background: rgba(248,250,252,0.03);
    text-align: center;
}
.ht-kpi-label { font-size: 0.78rem; color: #64748b; margin-bottom: 5px; }
.ht-kpi-value { font-size: 1.8rem; font-weight: 800; color: #1e293b; line-height: 1.1; }
.ht-kpi-sub   { font-size: 0.76rem; color: #94a3b8; margin-top: 4px; }
.ht-dist-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 5px 0;
    border-bottom: 1px solid rgba(148,163,184,0.1);
    font-size: 0.86rem;
}
.ht-dist-lbl { color: #64748b; min-width: 80px; }
.ht-dist-bar {
    height: 10px;
    border-radius: 5px;
    background: #3b82f6;
    min-width: 4px;
}
.ht-warn {
    background: rgba(239,68,68,0.07);
    border: 1px solid rgba(239,68,68,0.2);
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 0.85rem;
    color: #7f1d1d;
    margin-bottom: 8px;
}
</style>
"""

# ─────────────────────────────────────────────────────────────────────────────
# Helpers (preserved for backward compat)
# ─────────────────────────────────────────────────────────────────────────────

def _direction_label(value: Any, status: str = "") -> str:
    if value == 1:
        return "正确"
    if value == 0:
        return "错误"
    if value is None:
        if status in {"outcome_captured", "review_generated"}:
            return "中性"
        return "待定"
    return "中性"


def _format_pct(value: Any) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value) * 100:+.2f}%"
    except (TypeError, ValueError):
        return ""


def _json_or_empty(raw: Any) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(str(raw))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _prediction_summary(prediction: dict[str, Any] | None) -> str:
    if not prediction:
        return ""
    predict_json = _json_or_empty(prediction.get("predict_result_json"))
    return str(predict_json.get("prediction_summary") or "")


def _scenario_label(raw: Any) -> str:
    scenario = _json_or_empty(raw)
    if not scenario:
        return ""
    return (
        f"exact {scenario.get('exact_match_count', 'N/A')} / "
        f"near {scenario.get('near_match_count', 'N/A')} / "
        f"{scenario.get('dominant_historical_outcome', 'N/A')}"
    )


def _history_rows(predictions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in predictions:
        rows.append(
            {
                "prediction_for_date": row.get("prediction_for_date", ""),
                "final_bias": row.get("final_bias", ""),
                "final_confidence": row.get("final_confidence", ""),
                "status": row.get("status", ""),
                "direction_correct": _direction_label(
                    row.get("direction_correct"),
                    str(row.get("status", "")),
                ),
                "scenario_match": _scenario_label(row.get("scenario_match")),
                "close_change": _format_pct(row.get("actual_close_change")),
                "id": row.get("id", ""),
            }
        )
    return rows


def _option_label(row: dict[str, Any]) -> str:
    bias_cn = _BIAS_CN.get(str(row.get("final_bias") or ""), str(row.get("final_bias") or "—"))
    status_cn = _STATUS_CN.get(str(row.get("status") or ""), str(row.get("status") or "—"))
    return (
        f"{row.get('prediction_for_date', '')} | "
        f"{bias_cn} | "
        f"{status_cn} | "
        f"{str(row.get('id', ''))[:8]}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Summary section helpers
# ─────────────────────────────────────────────────────────────────────────────

def _parse_open_close(row: dict) -> tuple[str, str]:
    """Extract open/close tendency from predict_result_json."""
    pr = _json_or_empty(row.get("predict_result_json") if "predict_result_json" in row else None)
    # For list_predictions rows, predict_result_json is not included
    # Try final_projection first
    fp = pr.get("final_projection") or {}
    if isinstance(fp, dict):
        pred_open = str(fp.get("pred_open") or pr.get("pred_open") or "")
        pred_close = str(fp.get("pred_close") or pr.get("pred_close") or "")
    else:
        pred_open = ""
        pred_close = ""
    open_cn = _OPEN_CN.get(pred_open, pred_open) if pred_open else "—"
    close_cn = _CLOSE_CN.get(pred_close, pred_close) if pred_close else "—"
    return open_cn, close_cn


def _render_kpi(label: str, value: str | int, sub: str = "", color: str = "#1e293b") -> str:
    return (
        f'<div class="ht-kpi">'
        f'<div class="ht-kpi-label">{label}</div>'
        f'<div class="ht-kpi-value" style="color:{color};">{value}</div>'
        f'<div class="ht-kpi-sub">{sub}</div>'
        f'</div>'
    )


def _bar_width(count: int, total: int, max_px: int = 120) -> int:
    if total == 0:
        return 4
    return max(4, int(count / total * max_px))


def _render_section1_overview(predictions: list[dict]) -> None:
    """历史总览区：4 KPI cards"""
    total = len(predictions)
    saved_n = sum(1 for p in predictions if p.get("status") in _STATUS_ORDER)
    outcome_n = sum(1 for p in predictions if p.get("status") in {"outcome_captured", "review_generated"})
    review_n = sum(1 for p in predictions if p.get("status") == "review_generated")
    pending_n = total - review_n

    st.markdown('<div class="ht-section">① 历史总览</div>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(_render_kpi("总推演条数", total, "所有已保存记录"), unsafe_allow_html=True)
    with c2:
        st.markdown(_render_kpi("已保存", saved_n, "已写入数据库"), unsafe_allow_html=True)
    with c3:
        pct_str = f"占 {outcome_n/total*100:.0f}%" if total else ""
        st.markdown(_render_kpi("已抓结果", outcome_n, pct_str, color="#1f7a4f"), unsafe_allow_html=True)
    with c4:
        pct_str = f"占 {review_n/total*100:.0f}%" if total else ""
        st.markdown(_render_kpi("已复盘", review_n, pct_str, color="#3b82f6"), unsafe_allow_html=True)
    with c5:
        color = "#b42318" if pending_n > 0 else "#1f7a4f"
        st.markdown(_render_kpi("未完成闭环", pending_n, "尚未完整复盘", color=color), unsafe_allow_html=True)


def _render_section2_distribution(predictions: list[dict]) -> None:
    """分布概览区：方向分布 / 置信度分布 / 未闭环列表"""
    st.markdown('<div class="ht-section">② 分布概览</div>', unsafe_allow_html=True)
    left, mid, right = st.columns(3)
    total = len(predictions)

    # 方向分布
    with left:
        st.markdown("**方向分布**")
        bias_counts: Counter = Counter()
        for p in predictions:
            raw = str(p.get("final_bias") or "unknown")
            label = _BIAS_CN.get(raw, raw)
            bias_counts[label] += 1
        for label, cnt in bias_counts.most_common():
            w = _bar_width(cnt, total)
            st.markdown(
                f'<div class="ht-dist-row">'
                f'<span class="ht-dist-lbl">{label}</span>'
                f'<span class="ht-dist-bar" style="width:{w}px;"></span>'
                f'<span style="font-size:0.82rem;color:#1e293b;font-weight:600;">{cnt}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # 置信度分布
    with mid:
        st.markdown("**置信度分布**")
        conf_counts: Counter = Counter()
        for p in predictions:
            raw = str(p.get("final_confidence") or "unknown")
            label = _CONFIDENCE_CN.get(raw, raw)
            conf_counts[label] += 1
        conf_colors = {"高": "#1f7a4f", "中": "#b36b00", "低": "#b42318"}
        for label, cnt in conf_counts.most_common():
            color = conf_colors.get(label, "#6b7280")
            w = _bar_width(cnt, total)
            st.markdown(
                f'<div class="ht-dist-row">'
                f'<span class="ht-dist-lbl">{label}</span>'
                f'<span class="ht-dist-bar" style="width:{w}px;background:{color};"></span>'
                f'<span style="font-size:0.82rem;color:#1e293b;font-weight:600;">{cnt}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # 未完成闭环
    with right:
        st.markdown("**未完成闭环记录**")
        pending = [
            p for p in predictions
            if p.get("status") != "review_generated"
        ]
        if not pending:
            st.markdown(
                '<div class="ht-dist-row" style="color:#1f7a4f;font-weight:600;">'
                '所有记录已完成复盘 ✓</div>',
                unsafe_allow_html=True,
            )
        else:
            for p in pending[:8]:
                date = str(p.get("prediction_for_date") or "—")
                status_cn = _STATUS_CN.get(str(p.get("status") or ""), "—")
                color = _STATUS_COLOR.get(status_cn, "#6b7280")
                st.markdown(
                    f'<div class="ht-dist-row">'
                    f'<span class="ht-dist-lbl">{date}</span>'
                    f'<span style="color:{color};font-size:0.82rem;font-weight:600;">{status_cn}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            if len(pending) > 8:
                st.caption(f"…还有 {len(pending)-8} 条未完成")


def _render_section3_recent(predictions: list[dict]) -> None:
    """最近记录区：中文表格"""
    st.markdown('<div class="ht-section">③ 最近推演记录</div>', unsafe_allow_html=True)

    recent = predictions[:15]
    if not recent:
        st.info("暂无推演记录。")
        return

    rows = []
    for p in recent:
        bias_cn = _BIAS_CN.get(str(p.get("final_bias") or ""), "—")
        conf_cn = _CONFIDENCE_CN.get(str(p.get("final_confidence") or ""), "—")
        status_cn = _STATUS_CN.get(str(p.get("status") or ""), "—")
        close_chg = _format_pct(p.get("actual_close_change"))
        dir_ok = p.get("direction_correct")
        dir_str = {1: "方向正确 ✓", 0: "方向错误 ✗"}.get(dir_ok, "待确认")
        rows.append({
            "预测日期":   str(p.get("prediction_for_date") or "—"),
            "最终方向":   bias_cn,
            "置信度":     conf_cn,
            "当前状态":   status_cn,
            "实际涨跌":   close_chg or "—",
            "方向结果":   dir_str,
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, hide_index=True, use_container_width=True)

    if len(predictions) > 15:
        st.caption(f"共 {len(predictions)} 条记录，上表显示最近 15 条。")


# ─────────────────────────────────────────────────────────────────────────────
# Detail section helpers (preserved)
# ─────────────────────────────────────────────────────────────────────────────

def _render_prediction_detail(prediction: dict[str, Any]) -> None:
    st.markdown("**推演摘要**")
    st.write(_prediction_summary(prediction) or "暂无推演摘要。")
    with st.expander("推演原始数据"):
        st.json(_json_or_empty(prediction.get("predict_result_json")))
    with st.expander("扫描/研究原始数据"):
        st.markdown("**Scan**")
        st.json(_json_or_empty(prediction.get("scan_result_json")))
        st.markdown("**Research**")
        st.json(_json_or_empty(prediction.get("research_result_json")))


def _render_outcome_detail(outcome: dict[str, Any] | None) -> None:
    st.markdown("**实际结果**")
    if not outcome:
        st.info("尚未抓取实际结果。")
        return
    fields = [
        "prediction_for_date",
        "actual_open",
        "actual_high",
        "actual_low",
        "actual_close",
        "actual_prev_close",
        "actual_open_change",
        "actual_close_change",
        "direction_correct",
        "scenario_match",
    ]
    labels = {
        "prediction_for_date": "预测日期",
        "actual_open": "实际开盘",
        "actual_high": "实际最高",
        "actual_low": "实际最低",
        "actual_close": "实际收盘",
        "actual_prev_close": "前一日收盘",
        "actual_open_change": "开盘变动",
        "actual_close_change": "收盘变动",
        "direction_correct": "方向正确",
        "scenario_match": "场景匹配",
    }
    display = {labels.get(f, f): outcome.get(f) for f in fields}
    st.dataframe(pd.DataFrame([display]), hide_index=True, use_container_width=True)


def _render_review_detail(review: dict[str, Any] | None) -> None:
    st.markdown("**复盘记录**")
    if not review:
        st.info("尚未生成复盘。")
        return
    cat = str(review.get("error_category") or "")
    cat_labels = {
        "correct":                         "判断正确",
        "wrong_direction":                 "方向错误",
        "right_direction_wrong_magnitude": "方向对但幅度偏差",
        "false_confidence":                "过度自信",
        "insufficient_data":               "信息不足",
    }
    cat_cn = cat_labels.get(cat, cat.replace("_", " "))
    st.markdown(f"**错误类型：** {cat_cn}")
    st.markdown(f"**根本原因：** {review.get('root_cause', '—')}")
    st.markdown(f"**置信度评估：** {review.get('confidence_note', '—')}")
    st.markdown(f"**下次注意：** {review.get('watch_for_next_time', '—')}")
    with st.expander("复盘原始数据"):
        st.json(_json_or_empty(review.get("review_json")))


def _render_history_store_unavailable(error: PredictionStoreCorruptionError) -> None:
    st.warning(str(error))
    st.caption("当前不会自动覆盖旧库；请先备份 avgo_agent.db，再按需删除该文件让应用重建空历史库。")


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def render_history_tab() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)

    st.markdown("""
    <div style="padding:16px 20px;border:1px solid rgba(148,163,184,0.25);border-radius:14px;
                background:linear-gradient(135deg,rgba(13,27,42,0.97),rgba(18,52,86,0.93));
                color:#f8fafc;margin-bottom:16px;">
        <div style="font-size:0.78rem;opacity:0.7;">AVGO · 推演历史</div>
        <div style="font-size:1.7rem;font-weight:800;margin-top:4px;">历史推演汇总</div>
        <div style="margin-top:6px;font-size:0.88rem;opacity:0.85;">查看所有已保存推演的状态、分布与趋势。</div>
    </div>
    """, unsafe_allow_html=True)

    try:
        predictions = list_predictions(limit=100)
    except PredictionStoreCorruptionError as exc:
        _render_history_store_unavailable(exc)
        return

    if not predictions:
        st.info("暂无已保存的推演记录。请先在「推演页」完成一次推演并保存。")
        return

    # ── 三个汇总区 ──────────────────────────────────────────────────────────
    _render_section1_overview(predictions)
    st.markdown("")
    _render_section2_distribution(predictions)
    st.markdown("")
    _render_section3_recent(predictions)

    # ── 原有：逐条检索区 ───────────────────────────────────────────────────
    st.divider()
    st.markdown('<div class="ht-section">④ 逐条检索</div>', unsafe_allow_html=True)
    st.caption("选择任意记录查看完整的推演 / 结果 / 复盘详情。")

    rows = _history_rows(predictions)
    options = {_option_label(row): row["id"] for row in rows if row.get("id")}
    selected_label = st.selectbox("选择记录", list(options.keys()))
    selected_id = options[selected_label]

    try:
        prediction = get_prediction(selected_id)
        outcome = get_outcome_for_prediction(selected_id)
        review = get_review_for_prediction(selected_id)
    except PredictionStoreCorruptionError as exc:
        _render_history_store_unavailable(exc)
        return

    if not prediction:
        st.warning("未找到所选推演记录。")
        return

    st.divider()
    st.markdown(
        f"### {prediction.get('symbol', 'AVGO')} — {prediction.get('prediction_for_date', '')}"
    )

    col_prediction, col_outcome, col_review = st.columns(3)
    with col_prediction:
        _render_prediction_detail(prediction)
    with col_outcome:
        _render_outcome_detail(outcome)
    with col_review:
        _render_review_detail(review)
