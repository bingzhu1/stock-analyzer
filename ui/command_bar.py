from __future__ import annotations

import re
from typing import Any

try:
    import streamlit as st
except ModuleNotFoundError:
    st = None

from services.command_parser import ParsedTask, parse_command
from services.comparison_engine import compare_field, is_categorical_field
from services.data_query import load_symbol_data
from services.multi_symbol_view import build_aligned_view
from services.projection_entrypoint import run_projection_entrypoint
from services.stats_engine import compute_match_stats, position_distribution
from ui.labels import (
    CMD_ERROR_LABEL,
    CMD_INPUT_LABEL,
    CMD_PARSE_BTN,
    CMD_RESULT_LABEL,
    FIELD_LABELS,
    TASK_TYPE_LABELS,
)

_PLACEHOLDER = (
    "例：调出博通最近20天数据 / "
    "比较博通和英伟达最近20天最高价走势 / "
    "推演博通下一个交易日走势 / "
    "复盘昨天"
)

_PROJECTION_ERROR_NO_SYMBOL = "推演指令需要指定标的，例如：推演博通下一个交易日走势。"
_COMPARE_ERROR_ONE_SYMBOL   = "对比指令需要至少两个标的，例如：比较博通和英伟达最近20天最高价走势。"

# ── session-state keys ────────────────────────────────────────────────────────
_SS_PARSED         = "cn_cmd_parsed"          # last ParsedTask
_SS_PROJ_RESULT    = "cn_cmd_proj_result"      # projection result dict | None
_SS_PROJ_ERROR     = "cn_cmd_proj_error"       # projection error str   | None
_SS_QUERY_RESULT   = "cn_cmd_query_result"     # list[(symbol, df)] | None
_SS_QUERY_ERROR    = "cn_cmd_query_error"      # query error str    | None
_SS_COMPARE_RESULT = "cn_cmd_compare_result"   # compare result dict | None
_SS_COMPARE_ERROR  = "cn_cmd_compare_error"    # compare error str   | None
_SS_LAST_INPUT     = "cn_cmd_last_input"       # last parsed input text

_ALL_RESULT_KEYS = (
    _SS_PARSED,
    _SS_PROJ_RESULT,   _SS_PROJ_ERROR,
    _SS_QUERY_RESULT,  _SS_QUERY_ERROR,
    _SS_COMPARE_RESULT, _SS_COMPARE_ERROR,
)


# ── command executors ─────────────────────────────────────────────────────────

def _projection_lookback_days(parsed: ParsedTask) -> int | None:
    if parsed.window and parsed.window > 0:
        return parsed.window
    match = re.search(r"(\d{1,3})\s*天\s*数据", parsed.raw_text)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def run_projection_command(parsed: ParsedTask) -> tuple[dict[str, Any] | None, str | None]:
    """Execute run_projection through the projection entrypoint. Never raises."""
    if parsed.task_type != "run_projection":
        return None, None
    if not parsed.symbols:
        return None, _PROJECTION_ERROR_NO_SYMBOL
    try:
        # error_category not yet in ParsedTask; wired in a future task
        kwargs: dict[str, Any] = {"symbol": parsed.symbols[0]}
        lookback_days = _projection_lookback_days(parsed)
        if lookback_days:
            kwargs["lookback_days"] = lookback_days
        return run_projection_entrypoint(**kwargs), None
    except Exception as exc:
        return None, f"推演执行失败：{exc}"


def run_query_command(
    parsed: ParsedTask,
    *,
    _loader=None,
) -> tuple[list[tuple[str, Any]] | None, str | None]:
    """
    Execute query_data: load data for each symbol.

    Returns ([(symbol, df), ...], None) on success,
            (None, error_str) on any failure.  Never raises.
    """
    if parsed.task_type != "query_data":
        return None, None
    if not parsed.symbols:
        return None, "查询指令需要指定标的，例如：调出博通最近20天数据。"
    loader = _loader or load_symbol_data
    try:
        results = []
        for sym in parsed.symbols:
            df = loader(sym, window=parsed.window, fields=parsed.fields or None)
            results.append((sym, df))
        return results, None
    except Exception as exc:
        return None, f"数据查询失败：{exc}"


def run_compare_command(
    parsed: ParsedTask,
    *,
    _loader=None,
) -> tuple[dict[str, Any] | None, str | None]:
    """
    Execute compare_data: build aligned view + field comparison + stats.

    Returns (result_dict, None) on success, (None, error_str) on failure.
    Never raises.

    result_dict keys:
        aligned_df      — date-aligned DataFrame for all symbols
        comparison_df   — per-day comparison result (2-symbol only)
        stats           — {"total", "matched", "mismatched", "match_rate"}
        field           — field name used for comparison
        symbols         — list of symbol strings
        position_dist   — position distribution dict | None
        stat_symbol     — symbol used for position_dist | None
    """
    if parsed.task_type != "compare_data":
        return None, None
    if len(parsed.symbols) < 2:
        return None, _COMPARE_ERROR_ONE_SYMBOL

    loader = _loader or load_symbol_data
    compare_field_name = (parsed.fields[0] if parsed.fields else "Close")

    try:
        # Build aligned view for all symbols / all requested fields + comparison field
        view_fields = list(parsed.fields) if parsed.fields else ["Close"]
        if compare_field_name not in view_fields:
            view_fields = [compare_field_name] + view_fields

        # Include PosLabel when a position distribution is requested
        if (parsed.stat_request
                and parsed.stat_request.get("type") == "distribution_by_label"
                and "PosLabel" not in view_fields):
            view_fields = view_fields + ["PosLabel"]

        aligned = build_aligned_view(
            parsed.symbols,
            window=parsed.window,
            fields=view_fields,
            _loader=loader,
        )

        # Field-level comparison (first two symbols only for MVP)
        sym_a, sym_b = parsed.symbols[0], parsed.symbols[1]
        comp_df = compare_field(aligned, compare_field_name, sym_a, sym_b)
        stats   = compute_match_stats(comp_df)

        # Position distribution (only when stat_request asks for it)
        pos_dist:  dict | None = None
        dist_sym:  str | None  = None
        if (parsed.stat_request
                and parsed.stat_request.get("type") == "distribution_by_label"):
            dist_sym = (parsed.stat_request.get("symbol")
                        or (parsed.symbols[0] if parsed.symbols else None))
            if dist_sym:
                pos_dist = position_distribution(comp_df, aligned, dist_sym)

        return {
            "aligned_df":    aligned,
            "comparison_df": comp_df,
            "stats":         stats,
            "field":         compare_field_name,
            "symbols":       parsed.symbols,
            "position_dist": pos_dist,
            "stat_symbol":   dist_sym,
        }, None

    except Exception as exc:
        return None, f"数据对比失败：{exc}"


# ── result renderers ──────────────────────────────────────────────────────────

def _render_projection_result(result: dict[str, Any]) -> None:
    if st is None:
        raise RuntimeError("streamlit is required to render the command bar")
    report = result.get("projection_report")
    if isinstance(report, dict) and report.get("kind") == "final_projection_report":
        st.info("最终推演报告")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("明日方向", str(report.get("direction", "中性")))
        with col2:
            st.metric("开盘倾向", str(report.get("open_tendency", "平开")))
        with col3:
            st.metric("收盘倾向", str(report.get("close_tendency", "震荡")))
        with col4:
            st.metric("confidence", str(report.get("confidence", "low")))

        readable = report.get("readable_summary")
        if isinstance(readable, dict):
            base = readable.get("baseline_judgment", {})
            open_block = readable.get("open_projection", {})
            close_block = readable.get("close_projection", {})
            st.markdown("**明日基准判断**")
            st.write(base.get("text", str(report.get("direction", "中性"))))
            st.markdown("**开盘推演**")
            st.write(open_block.get("text", str(report.get("open_tendency", "平开"))))
            st.markdown("**收盘推演**")
            st.write(close_block.get("text", str(report.get("close_tendency", "震荡"))))
            st.markdown("**为什么这样判断**")
            for line in readable.get("rationale", []) or []:
                st.caption(f"- {line}")
            st.markdown("**风险提醒**")
            for line in readable.get("risk_reminders", []) or []:
                st.caption(f"- {line}")
        else:
            st.markdown("**为什么这样判断**")
            for line in report.get("basis_summary", []) or []:
                st.caption(f"- {line}")

            st.markdown("**风险提醒**")
            for line in report.get("risk_reminders", []) or []:
                st.caption(f"- {line}")

        with st.expander("推演详情"):
            st.json(result)
        return

    advisory = result.get("advisory", {})
    st.info("推演预检结果（仅提示，不调整分数或置信度）")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("预检状态", "就绪" if result.get("ready") else "未就绪")
    with col2:
        st.metric("历史提醒数", str(advisory.get("matched_count", 0)))
    with col3:
        st.metric("提醒等级", str(advisory.get("caution_level", "none")))
    reminders = advisory.get("reminder_lines") or []
    if reminders:
        st.caption("历史提醒：")
        for line in reminders:
            st.caption(f"- {line}")
    try:
        st.json(result)
    except Exception:
        st.caption("（推演详情无法以 JSON 格式显示）")


def _render_query_result(query_result: list[tuple[str, Any]]) -> None:
    if st is None:
        raise RuntimeError("streamlit is required to render the command bar")
    for sym, df in query_result:
        if df is None or getattr(df, "empty", True):
            st.warning(f"**{sym}** — 查询结果为空，请检查数据文件或时间窗口。")
            continue
        field_display = "、".join(
            FIELD_LABELS.get(c, c) for c in df.columns if c != "Date"
        ) or "数据"
        st.info(f"**{sym}** — {field_display}")
        st.dataframe(df, use_container_width=True)


def _render_compare_result(compare_result: dict[str, Any]) -> None:
    if st is None:
        raise RuntimeError("streamlit is required to render the command bar")

    symbols    = compare_result.get("symbols", [])
    field      = compare_result.get("field", "—")
    aligned    = compare_result.get("aligned_df")
    comp_df    = compare_result.get("comparison_df")
    stats      = compare_result.get("stats", {})
    field_label = FIELD_LABELS.get(field, field)

    sym_label = " vs ".join(symbols)
    st.info(f"**{sym_label}** — 字段：{field_label}")

    # Stats row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("总天数", str(stats.get("total", 0)))
    with col2:
        st.metric("方向一致", str(stats.get("matched", 0)))
    with col3:
        st.metric("不一致", str(stats.get("mismatched", 0)))
    with col4:
        st.metric("一致率", f"{stats.get('match_rate', 0.0)}%")

    if stats.get("total", 0) == 0:
        st.warning("对比结果为空或样本不足，暂无法计算稳定的一致性。")

    # Position distribution (only when stat_request produced a result)
    pos_dist  = compare_result.get("position_dist")
    dist_sym  = compare_result.get("stat_symbol", "")
    if pos_dist is not None and pos_dist.get("total_matched", 0) > 0:
        label_src = pos_dist.get("label_source", "—")
        st.caption(
            f"一致天里 **{dist_sym}** 位置分布"
            f"（{label_src}，共 {pos_dist['total_matched']} 天）"
        )
        d1, d2, d3 = st.columns(3)
        with d1:
            st.metric("高位", f"{pos_dist['高位']} 天")
        with d2:
            st.metric("中位", f"{pos_dist['中位']} 天")
        with d3:
            st.metric("低位", f"{pos_dist['低位']} 天")
        if label_src == "Pos30":
            st.caption("（位置标签由 Pos30 分桶：≥67→高位，34~66→中位，≤33→低位）")

    # Comparison detail
    if comp_df is not None and not comp_df.empty:
        st.caption("逐日对比")
        st.dataframe(comp_df, use_container_width=True)
    elif comp_df is not None:
        st.caption("逐日对比为空。")

    # Full aligned view
    if aligned is not None and not aligned.empty:
        st.caption("对齐数据")
        st.dataframe(aligned, use_container_width=True)
    elif aligned is not None:
        st.caption("对齐数据为空。")


def _render_stored_result() -> None:
    """Display the last parse+execution result stored in session state.

    Called on every render so results persist across tab switches and
    other re-render triggers.
    """
    if st is None or _SS_PARSED not in st.session_state:
        return

    parsed: ParsedTask = st.session_state[_SS_PARSED]

    if parsed.parse_error:
        st.error(f"**{CMD_ERROR_LABEL}：** {parsed.parse_error}")
        return

    st.success(f"**{CMD_RESULT_LABEL}**")
    task_label    = TASK_TYPE_LABELS.get(parsed.task_type, parsed.task_type)
    window_display = (
        "下一个交易日" if parsed.window == -1
        else f"最近 {parsed.window} 天"
    )
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("指令类型", task_label)
    with col2:
        st.metric("标的", "、".join(parsed.symbols) or "—")
    with col3:
        st.metric("时间窗口", window_display)
    if parsed.fields:
        field_display = "、".join(FIELD_LABELS.get(f, f) for f in parsed.fields)
        st.caption(f"字段：{field_display}")
    st.caption(f"原始指令：{parsed.raw_text}")

    # Task-specific execution result
    if parsed.task_type == "run_projection":
        proj_error: str | None = st.session_state.get(_SS_PROJ_ERROR)
        proj_result: dict | None = st.session_state.get(_SS_PROJ_RESULT)
        if proj_error:
            st.warning(proj_error)
        elif proj_result is not None:
            _render_projection_result(proj_result)

    elif parsed.task_type == "query_data":
        q_error: str | None = st.session_state.get(_SS_QUERY_ERROR)
        q_result = st.session_state.get(_SS_QUERY_RESULT)
        if q_error:
            st.warning(q_error)
        elif q_result is not None:
            _render_query_result(q_result)

    elif parsed.task_type == "compare_data":
        c_error: str | None = st.session_state.get(_SS_COMPARE_ERROR)
        c_result = st.session_state.get(_SS_COMPARE_RESULT)
        if c_error:
            st.warning(c_error)
        elif c_result is not None:
            _render_compare_result(c_result)


# ── main entry point ──────────────────────────────────────────────────────────

def render_command_bar() -> None:
    """
    Render the unified Chinese command input bar with parse-result display.

    Placed near the top of the main page; does not affect existing tabs.
    Supports: query_data (data query), compare_data (multi-symbol comparison),
    run_projection (advisory projection preflight), run_review (parse-only).

    Results are stored in session_state so they survive tab switches and
    other Streamlit re-render triggers without re-executing the entrypoint.
    """
    if st is None:
        raise RuntimeError("streamlit is required to render the command bar")

    with st.expander("指令中心（中文命令）", expanded=False):
        cmd_text: str = st.text_input(
            CMD_INPUT_LABEL,
            key="cn_command_input",
            placeholder=_PLACEHOLDER,
        )
        parse_clicked = st.button(CMD_PARSE_BTN, key="cn_parse_btn")

        # Clear stored results when input changes to prevent stale display.
        if cmd_text != st.session_state.get(_SS_LAST_INPUT, ""):
            for key in _ALL_RESULT_KEYS:
                st.session_state.pop(key, None)

        if parse_clicked:
            if not cmd_text or not cmd_text.strip():
                st.warning("请先输入指令。")
            else:
                parsed = parse_command(cmd_text)

                # Persist parse result; clear any prior execution results.
                st.session_state[_SS_LAST_INPUT] = cmd_text
                st.session_state[_SS_PARSED]     = parsed
                for key in (
                    _SS_PROJ_RESULT, _SS_PROJ_ERROR,
                    _SS_QUERY_RESULT, _SS_QUERY_ERROR,
                    _SS_COMPARE_RESULT, _SS_COMPARE_ERROR,
                ):
                    st.session_state.pop(key, None)

                if not parsed.parse_error:
                    if parsed.task_type == "run_projection":
                        proj_result, proj_error = run_projection_command(parsed)
                        st.session_state[_SS_PROJ_RESULT] = proj_result
                        st.session_state[_SS_PROJ_ERROR]  = proj_error

                    elif parsed.task_type == "query_data":
                        q_result, q_error = run_query_command(parsed)
                        st.session_state[_SS_QUERY_RESULT] = q_result
                        st.session_state[_SS_QUERY_ERROR]  = q_error

                    elif parsed.task_type == "compare_data":
                        c_result, c_error = run_compare_command(parsed)
                        st.session_state[_SS_COMPARE_RESULT] = c_result
                        st.session_state[_SS_COMPARE_ERROR]  = c_error
                        # run_review is parse-only; no execution needed

        # Always render whatever is in session state — survives re-renders.
        _render_stored_result()
