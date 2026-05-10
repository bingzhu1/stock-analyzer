"""
ui/inspect_tab.py

查验分析页面 — 接 services/inspect_analysis.py，回答"当前这种情况历史上到底准不准"。
"""
from __future__ import annotations

from typing import Any


def _fmt_rate(rate: Any) -> str:
    if rate is None:
        return "—"
    try:
        return f"{float(rate) * 100:.1f}%"
    except (TypeError, ValueError):
        return "—"


def _rate_color(rate: Any) -> str:
    if rate is None:
        return "#6b7280"
    try:
        v = float(rate)
        if v >= 0.6:
            return "#16a34a"
        if v >= 0.4:
            return "#b45309"
        return "#dc2626"
    except (TypeError, ValueError):
        return "#6b7280"


def _kpi_card(label: str, value: str, sub: str = "", color: str = "#f8fafc") -> str:
    return (
        f'<div style="padding:14px 16px;border:1px solid rgba(148,163,184,0.2);'
        f'border-radius:12px;background:rgba(15,23,42,0.03);text-align:center;">'
        f'<div style="font-size:0.78rem;color:#64748b;margin-bottom:6px;">{label}</div>'
        f'<div style="font-size:1.55rem;font-weight:700;color:{color};">{value}</div>'
        f'<div style="font-size:0.78rem;color:#94a3b8;margin-top:4px;">{sub}</div>'
        f'</div>'
    )


def _section_card(title: str, body: str) -> str:
    return (
        f'<div style="padding:16px 18px;border:1px solid rgba(148,163,184,0.2);'
        f'border-radius:12px;background:rgba(15,23,42,0.02);margin-bottom:12px;">'
        f'<div style="font-size:0.8rem;color:#64748b;margin-bottom:8px;font-weight:600;">{title}</div>'
        f'{body}'
        f'</div>'
    )


def _compute_missing_sections(sections_present: Any) -> list[str]:
    """Pure helper (PR-UI-2): derive ``missing_sections`` for the
    Inspect-tab Standard Payload section by complementing the inspector's
    ``sections_present`` against ``CONTRACT_SECTIONS``.

    Returns the canonical ``CONTRACT_SECTIONS`` list when ``sections_present``
    is not a list (defensive: tells the operator that nothing has been
    detected). The result is a plain list of section name strings;
    ordering follows ``CONTRACT_SECTIONS`` for stable display.
    """
    from services.projection_output_contract import CONTRACT_SECTIONS

    if not isinstance(sections_present, list):
        return list(CONTRACT_SECTIONS)
    present = {str(s) for s in sections_present if isinstance(s, str)}
    return [section for section in CONTRACT_SECTIONS if section not in present]


_STATUS_LABELS: dict[str, str] = {
    "ok": "通过 contract validator",
    "no_records": "尚无 prediction 记录",
    "missing_contract_payload": "最新记录缺少 contract_payload",
    "invalid_json": "contract_payload JSON 解析失败",
    "validation_failed": "contract validator 报告问题",
    "error": "查验加载异常",
}


def _render_standard_payload_section(
    inspector_result: dict[str, Any] | None,
    st_obj: Any,
) -> None:
    """Render the Inspect-tab Standard Payload status section
    (PR-UI-2 / 18Q).

    Pure read-only display. Accepts whatever
    ``services.contract_payload_inspector.inspect_latest_contract_payload``
    returns (or any equivalent dict). Never mutates the input. Never calls
    business modules / writes the DB / triggers prediction.

    The caller may enrich the dict with ``schema_version`` /
    ``compatibility_mode`` / ``missing_sections`` for richer display; this
    function reads them as optional fields.
    """
    st_obj.markdown("---")
    st_obj.markdown("### Standard Payload 状态")

    if inspector_result is None:
        st_obj.info("尚未取得 standard payload 检验结果。")
        return
    if not isinstance(inspector_result, dict):
        st_obj.warning("Standard Payload inspector 返回类型异常，已跳过展示。")
        return

    status = inspector_result.get("status", "unknown")
    label = _STATUS_LABELS.get(str(status), f"未识别状态 ({status})")
    st_obj.markdown(f"**Status**: `{status}` — {label}")

    pid = inspector_result.get("prediction_id")
    symbol = inspector_result.get("symbol")
    for_date = inspector_result.get("prediction_for_date")
    if any(v is not None for v in (pid, symbol, for_date)):
        st_obj.caption(
            f"prediction_id: {pid} / symbol: {symbol} / for_date: {for_date}"
        )

    schema_version = inspector_result.get("schema_version")
    if schema_version is not None:
        st_obj.markdown(f"**schema_version**: `{schema_version}`")

    compatibility_mode = inspector_result.get("compatibility_mode")
    if compatibility_mode is not None:
        st_obj.markdown(f"**compatibility_mode**: `{compatibility_mode}`")

    missing_sections = inspector_result.get("missing_sections")
    if isinstance(missing_sections, list):
        if missing_sections:
            st_obj.markdown(
                f"**missing_sections** ({len(missing_sections)}):"
            )
            for section in missing_sections:
                st_obj.markdown(f"- `{section}`")
        else:
            st_obj.markdown("**missing_sections**: 无")

    sections_present = inspector_result.get("sections_present")
    if isinstance(sections_present, list):
        st_obj.caption(
            f"sections_present: {len(sections_present)} sections"
        )

    validation_errors = inspector_result.get("validation_errors")
    if isinstance(validation_errors, list):
        if validation_errors:
            st_obj.markdown(
                f"**validation_errors** ({len(validation_errors)}):"
            )
            for err in validation_errors:
                st_obj.markdown(f"- {err}")
        else:
            st_obj.markdown("**validation_errors**: 无")

    summary = inspector_result.get("summary")
    if summary is not None:
        with st_obj.expander("payload summary"):
            st_obj.json(summary)


def _render_stats_block(block: dict[str, Any], st_obj: Any) -> None:
    """Render a standard stats block as a row of KPI cards."""
    n      = block.get("sample_count", 0)
    r1     = _fmt_rate(block.get("top1_hit_rate"))
    r1_col = _rate_color(block.get("top1_hit_rate"))
    excl   = block.get("exclusion_total", 0)
    re     = _fmt_rate(block.get("exclusion_hit_rate"))
    re_col = _rate_color(block.get("exclusion_hit_rate"))

    c1, c2, c3 = st_obj.columns(3)
    with c1:
        st_obj.markdown(
            _kpi_card("样本数", str(n), "条有效配对"),
            unsafe_allow_html=True,
        )
    with c2:
        st_obj.markdown(
            _kpi_card("Top1 命中率", r1,
                      f"{block.get('top1_hit_count',0)}/{n}",
                      color=r1_col),
            unsafe_allow_html=True,
        )
    with c3:
        denom = f"{excl} 次触发" if excl else "排除层未触发"
        st_obj.markdown(
            _kpi_card("排除命中率", re,
                      f"{block.get('exclusion_hit_count',0)}/{denom}",
                      color=re_col),
            unsafe_allow_html=True,
        )


def render_inspect_tab(current_snapshot: dict[str, Any] | None = None) -> None:
    import streamlit as st

    from services.inspect_analysis import (
        inspect_by_consistency,
        inspect_current,
    )

    # ── styles ─────────────────────────────────────────────────────────────────
    st.markdown(
        """
        <style>
        .ins-hero {
            padding: 16px 20px;
            border: 1px solid rgba(148,163,184,0.25);
            border-radius: 14px;
            background: linear-gradient(135deg,rgba(13,42,27,0.96),rgba(18,86,52,0.92));
            color: #f8fafc;
            margin-bottom: 16px;
        }
        .ins-badge {
            display:inline-block;
            padding:3px 10px;
            border-radius:20px;
            font-size:0.8rem;
            font-weight:600;
        }
        .ins-warn {
            padding:10px 14px;
            background:rgba(234,179,8,0.08);
            border:1px solid rgba(234,179,8,0.25);
            border-radius:8px;
            font-size:0.85rem;
            color:#92400e;
            margin-bottom:8px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="ins-hero">
            <div style="font-size:0.8rem;opacity:0.8;">查验分析</div>
            <div style="font-size:1.7rem;font-weight:800;margin-top:4px;">历史准确率查验</div>
            <div style="margin-top:6px;font-size:0.9rem;opacity:0.85;">
                当前这种情况，历史上到底准不准？基于最近 20 条有结果记录分组统计。
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Load consistency grouping ──────────────────────────────────────────────
    try:
        by_cons = inspect_by_consistency(symbol="AVGO", window=20)
    except Exception as e:
        st.error(f"查验数据加载失败：{e}")
        return

    # Warnings
    for w in by_cons.get("warnings", []):
        st.markdown(f'<div class="ins-warn">⚠ {w}</div>', unsafe_allow_html=True)

    total = by_cons.get("total_sample_count", 0)
    if total == 0:
        st.info("暂无有效配对记录（需要同时存在推演日志与结果日志）。")
        return

    # ── Section 1: Consistency split ──────────────────────────────────────────
    st.markdown("### 一致 vs 不一致样本对比")

    c_block  = by_cons.get("consistent_stats",   {})
    ic_block = by_cons.get("inconsistent_stats", {})

    tab_cons, tab_incons = st.tabs(["一致样本（consistency_passed=True）",
                                     "不一致样本（consistency_passed=False）"])

    with tab_cons:
        _render_stats_block(c_block, st)
        if c_block.get("sample_count", 0) == 0:
            st.caption("该分组暂无样本。")

    with tab_incons:
        _render_stats_block(ic_block, st)
        if ic_block.get("sample_count", 0) == 0:
            st.caption("该分组暂无样本。")

    # Diagnostic note
    for note in by_cons.get("notes", []):
        st.caption(f"ℹ {note}")

    # ── Section 2: Current situation lookup ───────────────────────────────────
    st.markdown("---")
    st.markdown("### 当前情况类比")

    snap = current_snapshot or {}

    # Show current snapshot fields
    cons_passed = snap.get("consistency_passed")
    direction   = snap.get("direction")
    confidence  = snap.get("confidence")
    excl_action = snap.get("exclusion_action")
    cons_flag   = snap.get("consistency_flag") or ("consistent" if cons_passed else
                                                     "conflict" if cons_passed is False else "—")

    # Badge: current consistency
    if cons_passed is True:
        badge_text, badge_bg = "一致", "#dcfce7"
        badge_color = "#15803d"
    elif cons_passed is False:
        badge_text, badge_bg = "不一致", "#fee2e2"
        badge_color = "#b91c1c"
    else:
        badge_text, badge_bg = "未知", "#f1f5f9"
        badge_color = "#475569"

    badge_html = (
        f'<span class="ins-badge" style="background:{badge_bg};color:{badge_color};">'
        f'{badge_text}</span>'
    )

    if snap:
        meta_parts = []
        if direction:
            meta_parts.append(f"方向：{direction}")
        if confidence:
            conf_map = {"high": "高置信度", "medium": "中置信度", "low": "低置信度"}
            meta_parts.append(conf_map.get(confidence, confidence))
        if excl_action:
            meta_parts.append("排除层已触发" if excl_action == "exclude" else "排除层未触发")
        meta_str = "　".join(meta_parts) if meta_parts else "（条件未提供）"

        st.markdown(
            f'当前一致性状态：{badge_html}&nbsp;&nbsp;'
            f'<span style="font-size:0.88rem;color:#64748b;">{meta_str}</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"当前一致性状态：{badge_html}"
            f'&nbsp;&nbsp;<span style="font-size:0.85rem;color:#94a3b8;">（未传入当前推演快照，使用兜底模式）</span>',
            unsafe_allow_html=True,
        )

    st.markdown("")

    # Run inspect_current
    try:
        cur_result = inspect_current(snap, symbol="AVGO", window=20)
    except Exception as e:
        st.error(f"当前情况查验失败：{e}")
        return

    match_level = cur_result.get("match_level", "—")
    level_color = {
        "全字段匹配":       "#15803d",
        "一致性+方向匹配":  "#b45309",
        "仅一致性匹配":     "#92400e",
        "兜底（全部记录）": "#6b7280",
    }.get(match_level, "#6b7280")

    st.markdown(
        f'匹配层级：<span style="color:{level_color};font-weight:600;">{match_level}</span>',
        unsafe_allow_html=True,
    )

    _render_stats_block(cur_result, st)

    # Summary
    summary = cur_result.get("summary", "")
    if summary:
        st.markdown(
            f'<div style="margin-top:12px;padding:14px 16px;'
            f'border-left:3px solid {level_color};'
            f'background:rgba(15,23,42,0.03);border-radius:0 8px 8px 0;'
            f'font-size:0.9rem;">{summary}</div>',
            unsafe_allow_html=True,
        )

    # Notes
    for note in cur_result.get("notes", []):
        st.caption(f"ℹ {note}")

    # Warnings from lookup
    for w in cur_result.get("warnings", []):
        st.markdown(f'<div class="ins-warn">⚠ {w}</div>', unsafe_allow_html=True)

    # ── Section 3: Unknown / degraded ─────────────────────────────────────────
    u_block = by_cons.get("unknown_stats", {})
    if u_block.get("sample_count", 0) > 0:
        st.markdown("---")
        with st.expander(f"一致性字段缺失的记录（{u_block['sample_count']} 条）"):
            _render_stats_block(u_block, st)
            st.caption("这些记录缺少 consistency_passed 字段，可能来自旧版日志或校验层未运行。")

    # ── Section 4: Standard Payload status (PR-UI-2 / 18Q) ────────────────────
    # Display-only. Calls ``inspect_latest_contract_payload`` (read-only DB
    # access) inside a try/except so any DB / parse failure degrades to a
    # friendly warning rather than breaking the tab. The pure-function
    # helpers ``_compute_missing_sections`` / ``_render_standard_payload_section``
    # carry the testable surface; ``render_inspect_tab`` only does the wiring.
    inspector_result: dict[str, Any] | None = None
    try:
        from services.contract_payload_inspector import (
            inspect_latest_contract_payload,
        )
        inspector_result = inspect_latest_contract_payload()
    except Exception as exc:  # noqa: BLE001 — display-only fallback
        st.warning(f"Standard Payload 检验加载失败：{exc}")

    if isinstance(inspector_result, dict):
        sections_present = inspector_result.get("sections_present")
        if "missing_sections" not in inspector_result and isinstance(
            sections_present, list
        ):
            inspector_result = {
                **inspector_result,
                "missing_sections": _compute_missing_sections(sections_present),
            }
    _render_standard_payload_section(inspector_result, st)
