"""
ui/review_tab.py

复盘中心 — 汇总化改造版。

结构：
  ① 复盘总览区        (真实 vs 训练条数 / 平均得分 / 主要错误类型)
  ② 命中率概览区      (开 / 路径 / 收盘准确率)
  ③ 错误分布区        (常见错误类型 / 高频误判维度)
  ④ 最近复盘记录区    (表格，区分真实复盘与历史训练)
  ⑤ 推演统计（原有） (review_center 四项 KPI + 逐条明细)
"""
from __future__ import annotations

from typing import Any


# ─────────────────────────────────────────────────────────────────────────────
# Label maps
# ─────────────────────────────────────────────────────────────────────────────

_ERROR_CAT_CN: dict[str, str] = {
    "correct":                         "判断正确",
    "wrong_direction":                 "方向错误",
    "right_direction_wrong_magnitude": "方向对但幅度偏差",
    "false_confidence":                "过度自信",
    "insufficient_data":               "信息不足",
}
_DIM_CN = {"open": "开盘", "path": "路径", "close": "收盘"}

_CSS = """
<style>
.rv-hero {
    padding: 16px 20px;
    border: 1px solid rgba(148,163,184,0.25);
    border-radius: 14px;
    background: linear-gradient(135deg,rgba(13,27,42,0.96),rgba(18,52,86,0.92));
    color: #f8fafc;
    margin-bottom: 16px;
}
.rv-section {
    font-size: 1.05rem;
    font-weight: 700;
    color: #1e293b;
    border-left: 4px solid #3b82f6;
    padding-left: 10px;
    margin: 18px 0 10px 0;
}
.rv-kpi {
    padding: 14px 16px;
    border: 1px solid rgba(148,163,184,0.2);
    border-radius: 12px;
    background: rgba(15,23,42,0.03);
    text-align: center;
}
.rv-kpi-label { font-size: 0.78rem; color: #64748b; margin-bottom: 6px; }
.rv-kpi-value { font-size: 1.6rem; font-weight: 700; line-height: 1.1; }
.rv-kpi-sub   { font-size: 0.78rem; color: #94a3b8; margin-top: 4px; }
.rv-warn {
    padding: 10px 14px;
    background: rgba(234,179,8,0.08);
    border: 1px solid rgba(234,179,8,0.25);
    border-radius: 8px;
    font-size: 0.85rem;
    color: #92400e;
    margin-bottom: 8px;
}
.rv-info {
    padding: 8px 12px;
    background: rgba(59,130,246,0.06);
    border: 1px solid rgba(59,130,246,0.18);
    border-radius: 8px;
    font-size: 0.84rem;
    color: #1e3a5f;
    margin-bottom: 8px;
}
.rv-acc-bar-wrap {
    height: 10px;
    background: rgba(148,163,184,0.15);
    border-radius: 5px;
    margin: 4px 0 8px 0;
    overflow: hidden;
}
.rv-acc-bar {
    height: 10px;
    border-radius: 5px;
}
.rv-dist-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 5px 0;
    border-bottom: 1px solid rgba(148,163,184,0.1);
    font-size: 0.85rem;
}
.rv-dist-lbl { color: #64748b; min-width: 130px; }
.rv-dist-bar {
    height: 10px;
    border-radius: 5px;
    background: #3b82f6;
    min-width: 4px;
}
.rv-source-real { color:#1f7a4f; font-weight:700; }
.rv-source-hist { color:#6b7280; }
.rv-score-high   { color:#1f7a4f; font-weight:700; }
.rv-score-mid    { color:#b36b00; font-weight:700; }
.rv-score-low    { color:#b42318; font-weight:700; }
</style>
"""


# ─────────────────────────────────────────────────────────────────────────────
# Helpers preserved for backward compat
# ─────────────────────────────────────────────────────────────────────────────

def _fmt_rate(rate: Any) -> str:
    if rate is None:
        return "—"
    try:
        return f"{float(rate) * 100:.1f}%"
    except (TypeError, ValueError):
        return "—"


def _state_color(state: str | None) -> str:
    mapping = {
        "大涨": "#16a34a",
        "小涨": "#65a30d",
        "震荡": "#b45309",
        "小跌": "#dc2626",
        "大跌": "#7f1d1d",
    }
    return mapping.get(state or "", "#6b7280")


def _bool_badge(value: bool | None, *, true_text: str = "✓", false_text: str = "✗") -> str:
    if value is True:
        return f'<span style="color:#16a34a;font-weight:600;">{true_text}</span>'
    if value is False:
        return f'<span style="color:#dc2626;font-weight:600;">{false_text}</span>'
    return '<span style="color:#6b7280;">—</span>'


# ─────────────────────────────────────────────────────────────────────────────
# New summary section renderers
# ─────────────────────────────────────────────────────────────────────────────

def _score_class(score: float | None) -> str:
    if score is None:
        return ""
    if score >= 0.67:
        return "rv-score-high"
    if score >= 0.34:
        return "rv-score-mid"
    return "rv-score-low"


def _acc_bar_html(acc: float | None, color: str = "#3b82f6") -> str:
    if acc is None:
        return '<div style="font-size:0.78rem;color:#94a3b8;">样本不足</div>'
    pct = int(acc * 100)
    return (
        f'<div class="rv-acc-bar-wrap">'
        f'<div class="rv-acc-bar" style="width:{pct}%;background:{color};"></div>'
        f'</div>'
    )


def _bar_width(count: int, total: int, max_px: int = 140) -> int:
    if total == 0:
        return 4
    return max(4, int(count / total * max_px))


def _render_section1_overview(
    counts: dict,
    records: list[dict],
    summary: dict,
) -> None:
    """① 复盘总览区"""
    import streamlit as st

    real_n = counts.get("real", 0)
    hist_n = counts.get("historical", 0)
    total_n = counts.get("total", 0)

    # Recent average score — all records
    scores = [r.get("overall_score") for r in records if r.get("overall_score") is not None]
    recent_scores = [s for s in scores[:10] if s is not None]
    avg_score = sum(recent_scores) / len(recent_scores) if recent_scores else None

    # Real-only average score
    real_records = [r for r in records if r.get("source") != "historical"]
    real_scores = [r.get("overall_score") for r in real_records if r.get("overall_score") is not None]
    real_avg = sum(real_scores) / len(real_scores) if real_scores else None

    most_cat = summary.get("most_common_error_category")
    most_cat_cn = _ERROR_CAT_CN.get(str(most_cat or ""), str(most_cat or "—"))

    st.markdown('<div class="rv-section">① 复盘总览</div>', unsafe_allow_html=True)

    if real_n == 0:
        st.markdown(
            '<div class="rv-warn">⚠ 当前真实复盘样本为零。所有统计均基于历史训练数据，仅供参考，请勿作为决策依据。</div>',
            unsafe_allow_html=True,
        )
    elif real_n < 5:
        st.markdown(
            f'<div class="rv-warn">⚠ 当前真实复盘仅 {real_n} 条，统计置信度较低，建议积累更多真实复盘后再依赖规律。</div>',
            unsafe_allow_html=True,
        )

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        color = "#1f7a4f" if real_n > 0 else "#6b7280"
        st.markdown(
            f'<div class="rv-kpi">'
            f'<div class="rv-kpi-label">真实复盘条数</div>'
            f'<div class="rv-kpi-value" style="color:{color};">{real_n}</div>'
            f'<div class="rv-kpi-sub">来自实际推演</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div class="rv-kpi">'
            f'<div class="rv-kpi-label">历史训练条数</div>'
            f'<div class="rv-kpi-value" style="color:#6b7280;">{hist_n}</div>'
            f'<div class="rv-kpi-sub">来自历史导入</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with c3:
        avg_str = f"{avg_score:.2f}" if avg_score is not None else "—"
        avg_pct = f"（{avg_score*100:.0f}%）" if avg_score is not None else ""
        cls = _score_class(avg_score)
        st.markdown(
            f'<div class="rv-kpi">'
            f'<div class="rv-kpi-label">最近平均得分（混合）</div>'
            f'<div class="rv-kpi-value {cls}">{avg_str}</div>'
            f'<div class="rv-kpi-sub">最近10条 {avg_pct}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with c4:
        real_avg_str = f"{real_avg:.2f}" if real_avg is not None else "—"
        real_avg_pct = f"（{real_avg*100:.0f}%）" if real_avg is not None else ""
        cls = _score_class(real_avg)
        st.markdown(
            f'<div class="rv-kpi">'
            f'<div class="rv-kpi-label">真实复盘平均得分</div>'
            f'<div class="rv-kpi-value {cls}">{real_avg_str}</div>'
            f'<div class="rv-kpi-sub">{real_n} 条真实记录 {real_avg_pct}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with c5:
        st.markdown(
            f'<div class="rv-kpi">'
            f'<div class="rv-kpi-label">当前主要错误类型</div>'
            f'<div class="rv-kpi-value" style="font-size:1rem;">{most_cat_cn}</div>'
            f'<div class="rv-kpi-sub">基于最近 {summary.get("record_count", 0)} 条</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


def _render_section2_accuracy(summary: dict, counts: dict) -> None:
    """② 命中率概览区"""
    import streamlit as st

    real_n = counts.get("real", 0)
    record_count = summary.get("record_count", 0)
    overall_acc = summary.get("overall_accuracy", 0.0)
    dim_acc = summary.get("dimension_accuracy", {})
    dim_n = summary.get("dimension_sample_count", {})

    st.markdown('<div class="rv-section">② 命中率概览</div>', unsafe_allow_html=True)

    if real_n == 0 and record_count > 0:
        st.markdown(
            '<div class="rv-info">ℹ 以下准确率基于历史训练数据（非真实推演），历史训练数据普遍得分偏高，不代表实战水平。</div>',
            unsafe_allow_html=True,
        )

    c1, c2, c3, c4 = st.columns(4)

    def _acc_card(col, label: str, acc: float | None, n: int, color: str) -> None:
        acc_str = f"{acc:.0%}" if acc is not None else "—"
        sub = f"{n} 条样本" if n else "无样本"
        bar_html = _acc_bar_html(acc, color)
        col.markdown(
            f'<div class="rv-kpi">'
            f'<div class="rv-kpi-label">{label}</div>'
            f'<div class="rv-kpi-value" style="color:{color};">{acc_str}</div>'
            f'{bar_html}'
            f'<div class="rv-kpi-sub">{sub}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with c1:
        oa_color = "#1f7a4f" if overall_acc >= 0.67 else "#b36b00" if overall_acc >= 0.34 else "#b42318"
        st.markdown(
            f'<div class="rv-kpi">'
            f'<div class="rv-kpi-label">整体得分</div>'
            f'<div class="rv-kpi-value" style="color:{oa_color};">{overall_acc:.0%}</div>'
            f'{_acc_bar_html(overall_acc, oa_color)}'
            f'<div class="rv-kpi-sub">基于最近 {record_count} 条</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    open_acc = dim_acc.get("open")
    path_acc = dim_acc.get("path")
    close_acc = dim_acc.get("close")

    def _dim_color(acc: float | None) -> str:
        if acc is None:
            return "#6b7280"
        if acc >= 0.70:
            return "#1f7a4f"
        if acc >= 0.50:
            return "#b36b00"
        return "#b42318"

    _acc_card(c2, "开盘判断命中率", open_acc, dim_n.get("open", 0), _dim_color(open_acc))
    _acc_card(c3, "路径判断命中率", path_acc, dim_n.get("path", 0), _dim_color(path_acc))
    _acc_card(c4, "收盘判断命中率", close_acc, dim_n.get("close", 0), _dim_color(close_acc))

    # Weakest / strongest highlight
    weakest = summary.get("weakest_dimension")
    strongest = summary.get("strongest_dimension")
    if weakest or strongest:
        notes = []
        if weakest:
            w_acc = dim_acc.get(weakest)
            notes.append(f"最弱维度：**{_DIM_CN.get(weakest, weakest)}**（准确率 {w_acc:.0%}）" if w_acc is not None else f"最弱维度：{_DIM_CN.get(weakest, weakest)}")
        if strongest and strongest != weakest:
            s_acc = dim_acc.get(strongest)
            notes.append(f"最强维度：**{_DIM_CN.get(strongest, strongest)}**（准确率 {s_acc:.0%}）" if s_acc is not None else f"最强维度：{_DIM_CN.get(strongest, strongest)}")
        st.caption("  ·  ".join(notes))


def _render_section3_error_dist(summary: dict, records: list[dict]) -> None:
    """③ 错误分布区"""
    import streamlit as st

    st.markdown('<div class="rv-section">③ 错误分布</div>', unsafe_allow_html=True)

    cat_counts: dict[str, int] = summary.get("error_category_counts", {})
    pe_counts:  dict[str, int] = summary.get("primary_error_counts", {})
    total_cat = sum(cat_counts.values()) if cat_counts else 0

    left, right = st.columns(2)

    with left:
        st.markdown("**常见错误类型**")
        if not cat_counts:
            st.caption("暂无错误分布数据。")
        else:
            for raw_cat, cnt in sorted(cat_counts.items(), key=lambda x: -x[1])[:6]:
                label = _ERROR_CAT_CN.get(raw_cat, raw_cat)
                w = _bar_width(cnt, total_cat)
                pct_str = f"{cnt/total_cat*100:.0f}%" if total_cat else ""
                color = "#b42318" if raw_cat != "correct" else "#1f7a4f"
                st.markdown(
                    f'<div class="rv-dist-row">'
                    f'<span class="rv-dist-lbl">{label}</span>'
                    f'<span class="rv-dist-bar" style="width:{w}px;background:{color};"></span>'
                    f'<span style="font-size:0.82rem;color:#1e293b;font-weight:600;">{cnt}次 {pct_str}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    with right:
        st.markdown("**高频误判维度**")
        if not pe_counts:
            st.caption("暂无误判维度数据。")
        else:
            total_pe = sum(pe_counts.values())
            for pe_label, cnt in sorted(pe_counts.items(), key=lambda x: -x[1])[:6]:
                w = _bar_width(cnt, total_pe)
                pct_str = f"{cnt/total_pe*100:.0f}%" if total_pe else ""
                st.markdown(
                    f'<div class="rv-dist-row">'
                    f'<span class="rv-dist-lbl">{pe_label}</span>'
                    f'<span class="rv-dist-bar" style="width:{w}px;background:#b36b00;"></span>'
                    f'<span style="font-size:0.82rem;color:#1e293b;font-weight:600;">{cnt}次 {pct_str}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    # Trend check: compare last 5 vs prior 5
    recent5  = records[:5]
    prior5   = records[5:10]
    if len(recent5) >= 3 and len(prior5) >= 3:
        recent_wrong  = sum(1 for r in recent5  if r.get("error_category") not in ("correct", None, ""))
        prior_wrong   = sum(1 for r in prior5   if r.get("error_category") not in ("correct", None, ""))
        recent_rate   = recent_wrong  / len(recent5)
        prior_rate    = prior_wrong   / len(prior5)
        if recent_rate > prior_rate + 0.2:
            st.markdown(
                f'<div class="rv-warn">⚠ 近期错误率上升（最近5条: {recent_wrong}/{len(recent5)} 次错 '
                f'vs 前5条: {prior_wrong}/{len(prior5)} 次错），建议检查推演质量。</div>',
                unsafe_allow_html=True,
            )
        elif recent_rate < prior_rate - 0.2:
            st.markdown(
                f'<div class="rv-info">ℹ 近期错误率下降（最近5条: {recent_wrong}/{len(recent5)} 次错 '
                f'vs 前5条: {prior_wrong}/{len(prior5)} 次错），准确率有所改善。</div>',
                unsafe_allow_html=True,
            )


def _render_section4_recent_records(records: list[dict], counts: dict) -> None:
    """④ 最近复盘记录区"""
    import streamlit as st
    import pandas as pd

    real_n = counts.get("real", 0)

    st.markdown('<div class="rv-section">④ 最近复盘记录</div>', unsafe_allow_html=True)

    if real_n == 0:
        st.markdown(
            '<div class="rv-info">ℹ 当前无真实复盘记录，下表全部为历史训练数据。</div>',
            unsafe_allow_html=True,
        )

    recent = records[:20]
    if not recent:
        st.info("暂无复盘记录。")
        return

    rows = []
    for r in recent:
        score = r.get("overall_score")
        score_str = f"{score:.2f}" if score is not None else "—"

        is_real = r.get("source") != "historical"
        source_label = "✓ 真实复盘" if is_real else "历史训练"

        cat = str(r.get("error_category") or "")
        cat_cn = _ERROR_CAT_CN.get(cat, cat.replace("_", " ") if cat else "—")

        pe = str(r.get("primary_error") or "—")

        open_ok = r.get("open_correct")
        path_ok = r.get("path_correct")
        close_ok = r.get("close_correct")

        def _dim_icon(v: bool | None) -> str:
            if v is True:
                return "✓"
            if v is False:
                return "✗"
            return "?"

        rows.append({
            "日期":       str(r.get("prediction_for_date") or "—"),
            "得分":       score_str,
            "开盘":       _dim_icon(open_ok),
            "路径":       _dim_icon(path_ok),
            "收盘":       _dim_icon(close_ok),
            "错误类型":   cat_cn,
            "主要误判":   pe,
            "数据来源":   source_label,
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, hide_index=True, use_container_width=True)

    real_shown = sum(1 for r in recent if r.get("source") != "historical")
    hist_shown = len(recent) - real_shown
    st.caption(f"上表显示最近 {len(recent)} 条 · 其中真实复盘 {real_shown} 条 / 历史训练 {hist_shown} 条")


# ─────────────────────────────────────────────────────────────────────────────
# Existing review_center section (preserved)
# ─────────────────────────────────────────────────────────────────────────────

def _render_review_center_section() -> None:
    """⑤ 推演统计（原 review_center 内容）"""
    import streamlit as st
    from services.review_center import (
        build_review_detail,
        compute_review_stats,
        format_review_summary,
    )

    st.markdown('<div class="rv-section">⑤ 推演系统统计（基于日志层）</div>', unsafe_allow_html=True)
    st.caption("以下统计基于 prediction_log / outcome_log 配对记录，与上方复盘中心统计来源不同。")

    try:
        stats = compute_review_stats(symbol="AVGO", window=20)
        detail = build_review_detail(symbol="AVGO", window=20)
    except Exception as e:
        st.warning(f"推演统计加载失败：{e}")
        return

    for w in stats.get("warnings", []):
        st.markdown(f'<div class="rv-warn">⚠ {w}</div>', unsafe_allow_html=True)

    n = stats.get("sample_count", 0)
    if n == 0:
        st.info("暂无有效配对记录（需要同时存在推演日志与结果日志）。")
        return

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        rate = _fmt_rate(stats.get("top1_hit_rate"))
        cnt = stats.get("top1_hit_count", 0)
        st.markdown(
            f'<div class="rv-kpi"><div class="rv-kpi-label">Top1 命中率</div>'
            f'<div class="rv-kpi-value">{rate}</div>'
            f'<div class="rv-kpi-sub">{cnt}/{n} 次命中</div></div>',
            unsafe_allow_html=True,
        )
    with c2:
        rate = _fmt_rate(stats.get("top2_coverage_rate"))
        cnt = stats.get("top2_coverage_count", 0)
        note = "（含降级）" if stats.get("top2_note") else ""
        st.markdown(
            f'<div class="rv-kpi"><div class="rv-kpi-label">Top2 覆盖率</div>'
            f'<div class="rv-kpi-value">{rate}</div>'
            f'<div class="rv-kpi-sub">{cnt}/{n} 次覆盖{note}</div></div>',
            unsafe_allow_html=True,
        )
    with c3:
        excl_total = stats.get("exclusion_total", 0)
        rate = _fmt_rate(stats.get("exclusion_hit_rate"))
        cnt = stats.get("exclusion_hit_count", 0)
        denom = f"{excl_total} 次触发" if excl_total else "未触发"
        st.markdown(
            f'<div class="rv-kpi"><div class="rv-kpi-label">排除命中率</div>'
            f'<div class="rv-kpi-value">{rate}</div>'
            f'<div class="rv-kpi-sub">{cnt}/{denom}</div></div>',
            unsafe_allow_html=True,
        )
    with c4:
        rate = _fmt_rate(stats.get("exclusion_miss_rate"))
        cnt = stats.get("exclusion_miss_count", 0)
        denom = f"{excl_total} 次触发" if excl_total else "未触发"
        st.markdown(
            f'<div class="rv-kpi"><div class="rv-kpi-label">误杀率</div>'
            f'<div class="rv-kpi-value">{rate}</div>'
            f'<div class="rv-kpi-sub">{cnt}/{denom}</div></div>',
            unsafe_allow_html=True,
        )

    with st.expander("查看完整摘要", expanded=False):
        st.code(format_review_summary(stats), language=None)

    if stats.get("top2_note"):
        st.caption(f"ℹ {stats['top2_note']}")

    st.markdown("**逐条推演明细（最新在前）**")
    if not detail:
        st.info("暂无明细数据。")
        return

    rows_html = ""
    for r in detail:
        pred   = r.get("predicted_state") or "—"
        actual = r.get("actual_state") or "—"
        date   = r.get("prediction_for_date") or "—"
        match  = r.get("state_match")
        top2c  = r.get("top2_covered")
        excl_a = r.get("exclusion_action") or "—"
        excl_h = r.get("exclusion_hit")
        chg    = r.get("actual_close_change_pct")
        chg_str = f"{chg:+.2f}%" if chg is not None else "—"
        pred_col   = f'<span style="color:{_state_color(pred)};font-weight:600;">{pred}</span>'
        actual_col = f'<span style="color:{_state_color(actual)};font-weight:600;">{actual}</span>'
        excl_cell  = f"排除 {_bool_badge(excl_h, true_text='命中', false_text='误杀')}" if excl_a == "exclude" else "—"
        rows_html += (
            f"<tr><td>{date}</td><td>{pred_col}</td><td>{actual_col}</td>"
            f"<td>{_bool_badge(match, true_text='✓ 命中', false_text='✗ 未中')}</td>"
            f"<td>{_bool_badge(top2c, true_text='✓ 覆盖', false_text='✗ 未覆盖')}</td>"
            f"<td>{excl_cell}</td><td>{chg_str}</td></tr>"
        )

    table_html = f"""
    <div style="overflow-x:auto;">
    <table style="width:100%;border-collapse:collapse;font-size:0.85rem;">
      <thead>
        <tr style="border-bottom:2px solid rgba(148,163,184,0.3);color:#64748b;text-align:left;">
          <th style="padding:8px 10px;">日期</th>
          <th style="padding:8px 10px;">预测状态</th>
          <th style="padding:8px 10px;">实际状态</th>
          <th style="padding:8px 10px;">Top1</th>
          <th style="padding:8px 10px;">Top2</th>
          <th style="padding:8px 10px;">排除层</th>
          <th style="padding:8px 10px;">涨跌幅</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table></div>"""
    st.markdown(table_html, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def render_review_tab() -> None:
    import streamlit as st
    from services.review_store import load_review_records, count_real_vs_historical
    from services.review_analyzer import summarize_review_history

    st.markdown(_CSS, unsafe_allow_html=True)

    st.markdown(
        """
        <div class="rv-hero">
            <div style="font-size:0.8rem;opacity:0.8;">复盘中心</div>
            <div style="font-size:1.7rem;font-weight:800;margin-top:4px;">AVGO 推演复盘汇总</div>
            <div style="margin-top:6px;font-size:0.9rem;opacity:0.85;">
                真实复盘 · 历史训练 · 命中率趋势 · 错误分析
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── 加载数据 ──────────────────────────────────────────────────────────────
    try:
        counts = count_real_vs_historical(symbol="AVGO")
        records = load_review_records(symbol="AVGO", limit=50)
        summary = summarize_review_history(symbol="AVGO", limit=30)
    except Exception as e:
        st.error(f"复盘数据加载失败：{e}")
        return

    if counts.get("total", 0) == 0:
        st.info("暂无复盘记录。请先完成推演 → 抓取结果 → 运行确定性复盘的完整流程。")
        return

    # ── 四个汇总区 ────────────────────────────────────────────────────────────
    _render_section1_overview(counts, records, summary)
    st.markdown("")
    _render_section2_accuracy(summary, counts)
    st.markdown("")
    _render_section3_error_dist(summary, records)
    st.markdown("")
    _render_section4_recent_records(records, counts)

    # ── 原有推演统计（review_center 层） ──────────────────────────────────────
    st.divider()
    _render_review_center_section()
