from __future__ import annotations

import re
from typing import Any

try:
    import streamlit as st
except ModuleNotFoundError:
    st = None

from services.ai_summary import (
    build_compare_ai_explanation,
    build_projection_ai_explanation,
    build_risk_ai_explanation,
)
from services.command_parser import ParsedTask
from services.comparison_engine import compare_field, is_categorical_field
from services.data_query import load_symbol_data
from services.ai_intent_parser import parse_with_ai_fallback, parse_with_ai_primary
from services.openai_client import OpenAIClientError
from services.tool_router import route_plan
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
from ui.projection_v2_renderer import build_projection_v2_display

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
_SS_AI_RESULT      = "cn_cmd_ai_result"        # AI explanation text | None
_SS_AI_ERROR       = "cn_cmd_ai_error"         # AI explanation error str | None
_SS_PLAN          = "cn_cmd_intent_plan"       # intent planner result dict | None
_SS_ROUTER_RESULT  = "cn_cmd_router_result"    # tool_router result dict | None
_SS_LAST_INPUT     = "cn_cmd_last_input"       # last parsed input text
_SS_LAST_PROJ_CTX  = "cn_cmd_last_proj_ctx"    # last successful projection result
_SS_LAST_COMP_CTX  = "cn_cmd_last_comp_ctx"    # last successful compare result

_ALL_RESULT_KEYS = (
    _SS_PARSED,
    _SS_PROJ_RESULT,   _SS_PROJ_ERROR,
    _SS_QUERY_RESULT,  _SS_QUERY_ERROR,
    _SS_COMPARE_RESULT, _SS_COMPARE_ERROR,
    _SS_AI_RESULT, _SS_AI_ERROR,
    _SS_PLAN,
    _SS_ROUTER_RESULT,
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


def _df_preview(df: Any, limit: int = 12) -> list[dict[str, Any]]:
    if df is None or getattr(df, "empty", True):
        return []
    try:
        return df.head(limit).to_dict("records")
    except Exception:
        return []


def _projection_ai_payload(
    projection_result: dict[str, Any],
    ai_request: dict | None,
) -> dict[str, Any]:
    v2_raw = projection_result.get("projection_v2_raw")
    report = projection_result.get("projection_report")
    readable = report.get("readable_summary") if isinstance(report, dict) else None
    v2 = v2_raw if isinstance(v2_raw, dict) else {}
    return {
        "kind": "command_projection_explanation",
        "ai_request": ai_request or {},
        "projection_schema": projection_result.get("projection_schema") or "legacy",
        "source_of_truth": projection_result.get("source_of_truth") or (
            "projection_v2_raw" if v2 else "projection_report"
        ),
        "projection_v2_raw": v2,
        "preflight": v2.get("preflight", {}) if isinstance(v2, dict) else {},
        "primary_analysis": v2.get("primary_analysis", {}) if isinstance(v2, dict) else {},
        "peer_adjustment": v2.get("peer_adjustment", {}) if isinstance(v2, dict) else {},
        "historical_probability": v2.get("historical_probability", {}) if isinstance(v2, dict) else {},
        "final_decision": v2.get("final_decision", {}) if isinstance(v2, dict) else {},
        "trace": v2.get("trace", []) if isinstance(v2, dict) else [],
        "projection_report": report if isinstance(report, dict) else {},
        "readable_summary": readable if isinstance(readable, dict) else {},
        "advisory": projection_result.get("advisory", {}),
        "legacy_compat": projection_result.get("legacy_compat", {}),
        "request": projection_result.get("request", {}),
        "ready": projection_result.get("ready"),
    }


def _compare_ai_payload(
    compare_result: dict[str, Any],
    ai_request: dict | None,
) -> dict[str, Any]:
    return {
        "kind": "command_compare_explanation",
        "ai_request": ai_request or {},
        "symbols": compare_result.get("symbols", []),
        "field": compare_result.get("field", ""),
        "stats": compare_result.get("stats", {}),
        "position_dist": compare_result.get("position_dist"),
        "stat_symbol": compare_result.get("stat_symbol"),
        "comparison_preview": _df_preview(compare_result.get("comparison_df")),
        "aligned_preview": _df_preview(compare_result.get("aligned_df"), limit=5),
    }


def run_ai_explanation_command(
    parsed: ParsedTask,
    *,
    projection_result: dict[str, Any] | None = None,
    compare_result: dict[str, Any] | None = None,
    _projection_builder=build_projection_ai_explanation,
    _compare_builder=build_compare_ai_explanation,
    _risk_builder=build_risk_ai_explanation,
) -> tuple[str | None, str | None]:
    """Execute AI explanation over existing structured command results. Never raises."""
    if parsed.task_type != "ai_explanation":
        return None, None

    ai_request = parsed.ai_request or {}
    focus = str(ai_request.get("focus", "projection"))

    try:
        if focus == "compare":
            if not compare_result:
                return None, "还没有可总结的比较结果。请先运行一次比较/对比命令。"
            return _compare_builder(_compare_ai_payload(compare_result, ai_request)), None

        if focus == "risk":
            if not projection_result:
                return None, "还没有可解释的风险提醒。请先运行一次推演命令。"
            payload = _projection_ai_payload(projection_result, ai_request)
            return _risk_builder(payload), None

        if not projection_result:
            return None, "还没有可解释的推演结果。请先运行一次推演命令。"
        return _projection_builder(_projection_ai_payload(projection_result, ai_request)), None

    except OpenAIClientError as exc:
        return None, str(exc)
    except Exception as exc:
        return None, f"AI 解释生成失败，已保留已有结构化结果：{exc}"


# ── response-card renderers ───────────────────────────────────────────────────

_RESPONSE_CARD_SECTION_HEADINGS = (
    "任务理解",
    "执行步骤",
    "核心结论",
    "依据摘要",
    "风险 / 提示",
    "原始结果",
)


def _window_display(parsed: ParsedTask | None = None, plan: dict[str, Any] | None = None) -> str:
    if isinstance(plan, dict):
        start = plan.get("start_date")
        end = plan.get("end_date")
        if start and end:
            return f"{start} 至 {end}"
    window = getattr(parsed, "window", None) if parsed is not None else None
    if window is None and isinstance(plan, dict):
        window = plan.get("lookback_days")
    if window == -1:
        return "下一个交易日"
    if isinstance(window, int) and window > 0:
        return f"最近 {window} 天"
    return "—"


def _field_display(fields: list[str] | None) -> str:
    return "、".join(FIELD_LABELS.get(f, f) for f in (fields or [])) or "—"


def _plan_step_lines(plan: dict[str, Any] | None) -> list[str]:
    if not isinstance(plan, dict):
        return []
    lines: list[str] = []
    steps = plan.get("steps") or []
    if steps:
        rendered = []
        for idx, step in enumerate(steps, start=1):
            stype = step.get("type", "unknown")
            syms = "、".join(step.get("symbols") or ([step.get("symbol")] if step.get("symbol") else []))
            fields = _field_display(step.get("fields") or ([step.get("field")] if step.get("field") else []))
            bits = [f"{idx}. {stype}"]
            if syms:
                bits.append(f"标的 {syms}")
            if fields != "—":
                bits.append(f"字段 {fields}")
            if step.get("optional"):
                bits.append("可选")
            rendered.append("，".join(bits))
        lines.append("识别步骤：" + "；".join(rendered))
    ai_followups = plan.get("ai_followups") or []
    if ai_followups:
        labels = []
        for item in ai_followups:
            status = "可用" if item.get("available") else "未配置 OPENAI_API_KEY"
            labels.append(f"{item.get('type', 'ai_followup')}（{status}）")
        lines.append("AI follow-up：" + "；".join(labels))
    return lines


def _router_step_lines(router_result: dict[str, Any] | None) -> list[str]:
    if not isinstance(router_result, dict):
        return []
    steps = router_result.get("steps_executed") or []
    if not steps:
        return []
    status_label = {
        "success": "success",
        "skipped": "skipped",
        "failed": "failed",
        "planned_only": "planned_only",
    }
    lines = []
    for step in steps:
        detail = step.get("error") or step.get("warning") or ""
        line = f"step {step.get('step', '')}: {step.get('type', '')} -> {status_label.get(step.get('status'), step.get('status', ''))}"
        if detail:
            line = f"{line}（{detail}）"
        lines.append(line)
    return lines


def _evidence_trace_lines(trace: dict[str, Any] | None) -> list[str]:
    if not isinstance(trace, dict):
        return []
    final = trace.get("final_conclusion") or {}
    lines: list[str] = []
    tools = trace.get("tool_trace") or []
    if tools:
        lines.append("tool_trace：" + " -> ".join(str(item) for item in tools))
    for heading, key in (
        ("key_observations", "key_observations"),
        ("decision_steps", "decision_steps"),
        ("verification_points", "verification_points"),
    ):
        values = [str(item) for item in (trace.get(key) or []) if str(item).strip()]
        if values:
            lines.append(f"{heading}：" + "；".join(values[:4]))
    if isinstance(final, dict) and final:
        lines.append(
            "final_conclusion："
            f"方向={final.get('direction', '中性')}，"
            f"开盘={final.get('open_tendency', '平开')}，"
            f"收盘={final.get('close_tendency', '震荡')}，"
            f"confidence={final.get('confidence', 'low')}"
        )
    return lines


def _safe_scalar(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    try:
        return value.item()
    except Exception:
        return str(value)


def _json_safe(value: Any, *, _depth: int = 0) -> Any:
    if _depth > 5:
        return str(value)
    if hasattr(value, "to_dict") and hasattr(value, "head"):
        try:
            return {
                "rows": int(len(value)),
                "columns": [str(c) for c in getattr(value, "columns", [])],
                "preview": _df_preview(value, limit=8),
            }
        except Exception:
            return str(value)
    if isinstance(value, dict):
        return {str(k): _json_safe(v, _depth=_depth + 1) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v, _depth=_depth + 1) for v in value]
    return _safe_scalar(value)


def _base_understanding(
    task_type: str,
    *,
    parsed: ParsedTask | None = None,
    plan: dict[str, Any] | None = None,
    symbols: list[str] | None = None,
    fields: list[str] | None = None,
) -> list[str]:
    raw_text = getattr(parsed, "raw_text", "") if parsed is not None else ""
    if not raw_text and isinstance(plan, dict):
        raw_text = str(plan.get("raw_text", ""))
    task_label = TASK_TYPE_LABELS.get(task_type, task_type)
    plan_display = (plan.get("planner") or plan.get("primary_intent")) if isinstance(plan, dict) else None
    parsed_symbols = list(getattr(parsed, "symbols", []) or []) if parsed is not None else []
    parsed_fields = list(getattr(parsed, "fields", []) or []) if parsed is not None else []
    syms = symbols or parsed_symbols or (plan.get("symbols", []) if isinstance(plan, dict) else [])
    flds = fields or parsed_fields or (plan.get("fields", []) if isinstance(plan, dict) else [])
    lines = [
        f"原始输入：{raw_text or '—'}",
        f"识别任务：{task_label}" + (f" / planner: {plan_display}" if plan_display else ""),
        f"标的：{'、'.join(syms) if syms else '—'}",
        f"时间窗口：{_window_display(parsed, plan)}",
        f"字段：{_field_display(flds)}",
    ]
    if isinstance(plan, dict):
        user_goal = str(plan.get("user_goal") or "").strip()
        explanation = str(plan.get("explanation") or "").strip()
        ai_conf = plan.get("ai_confidence")
        if user_goal:
            lines.append(f"用户目标：{user_goal}")
        if explanation:
            lines.append(f"AI 解释：{explanation}")
        if ai_conf is not None:
            try:
                lines.append(f"AI 置信度：{float(ai_conf):.0%}")
            except (TypeError, ValueError):
                pass
    lines.extend(_plan_step_lines(plan))
    return lines


def _make_response_card(
    task_type: str,
    *,
    understanding: list[str],
    steps: list[str] | None = None,
    conclusion: list[str] | None = None,
    evidence: list[str] | None = None,
    warnings: list[str] | None = None,
    raw_result: Any = None,
    raw_tables: list[tuple[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "kind": "command_response_card",
        "task_type": task_type,
        "understanding": understanding,
        "steps": steps or ["暂无执行步骤。"],
        "conclusion": conclusion or ["暂无可展示结论。"],
        "evidence": evidence or ["暂无额外依据。"],
        "warnings": warnings or ["暂无额外提示。"],
        "raw_result": _json_safe(raw_result),
        "raw_tables": raw_tables or [],
    }


def _build_projection_response_card(
    result: dict[str, Any] | None,
    *,
    parsed: ParsedTask | None = None,
    plan: dict[str, Any] | None = None,
    router_result: dict[str, Any] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    report = result.get("projection_report") if isinstance(result, dict) else None
    v2_raw = result.get("projection_v2_raw") if isinstance(result, dict) else None
    readable = report.get("readable_summary") if isinstance(report, dict) else None
    symbols = []
    if isinstance(result, dict) and isinstance(result.get("request"), dict):
        sym = result["request"].get("symbol")
        if sym:
            symbols = [str(sym)]
    if not symbols and parsed is not None:
        symbols = list(parsed.symbols or [])

    conclusion: list[str] = []
    evidence: list[str] = []
    warnings: list[str] = []

    if error:
        conclusion.append("推演未完成。")
        warnings.append(error)
    elif isinstance(v2_raw, dict) and v2_raw.get("kind") == "projection_v2_report":
        rendered = build_projection_v2_display(v2_raw)
        conclusion.extend(str(line) for line in (rendered.get("conclusion") or []))
        evidence.extend(str(line) for line in (rendered.get("evidence") or []))
        warnings.extend(str(line) for line in (rendered.get("warnings") or []))
    elif isinstance(report, dict) and report.get("kind") == "final_projection_report":
        conclusion.extend([
            f"明日方向：{report.get('direction', '中性')}",
            f"开盘倾向：{report.get('open_tendency', '平开')}",
            f"收盘倾向：{report.get('close_tendency', '震荡')}",
            f"confidence：{report.get('confidence', 'low')}",
        ])
        if isinstance(readable, dict):
            for block_key in ("baseline_judgment", "open_projection", "close_projection"):
                block = readable.get(block_key)
                text = block.get("text") if isinstance(block, dict) else None
                if text:
                    evidence.append(str(text))
            evidence.extend(str(line) for line in (readable.get("rationale") or []))
            warnings.extend(str(line) for line in (readable.get("risk_reminders") or []))
        else:
            evidence.extend(str(line) for line in (report.get("basis_summary") or []))
            warnings.extend(str(line) for line in (report.get("risk_reminders") or []))
        evidence.extend(_evidence_trace_lines(report.get("evidence_trace")))
    elif isinstance(result, dict):
        advisory = result.get("advisory", {}) or {}
        conclusion.extend([
            f"推演预检：{'就绪' if result.get('ready') else '未就绪'}",
            f"历史提醒数：{advisory.get('matched_count', 0)}",
            f"提醒等级：{advisory.get('caution_level', 'none')}",
        ])
        evidence.extend(str(line) for line in (advisory.get("reminder_lines") or []))
        if not evidence:
            evidence.append("当前仅有预检结果，尚未形成最终推演报告。")
    else:
        conclusion.append("推演暂无结果。")
        warnings.append("未找到可展示的推演结果。")

    if isinstance(router_result, dict):
        warnings.extend(str(w) for w in (router_result.get("warnings") or []))
    return _make_response_card(
        "projection",
        understanding=_base_understanding("run_projection", parsed=parsed, plan=plan, symbols=symbols),
        steps=_router_step_lines(router_result),
        conclusion=conclusion,
        evidence=evidence,
        warnings=list(dict.fromkeys(warnings)),
        raw_result=result or {"error": error},
    )


def _build_query_response_card(
    query_result: list[tuple[str, Any]] | None,
    *,
    parsed: ParsedTask | None = None,
    plan: dict[str, Any] | None = None,
    router_result: dict[str, Any] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    rows = query_result or []
    symbols = [str(sym) for sym, _ in rows] or (list(parsed.symbols or []) if parsed else [])
    conclusion: list[str] = []
    evidence: list[str] = []
    warnings: list[str] = []
    raw_tables: list[tuple[str, Any]] = []

    if error:
        conclusion.append("查询未完成。")
        warnings.append(error)
    else:
        non_empty = 0
        for sym, df in rows:
            if df is None or getattr(df, "empty", True):
                warnings.append(f"{sym} 查询结果为空，请检查数据文件或时间窗口。")
                evidence.append(f"{sym}：0 行。")
                continue
            non_empty += 1
            cols = [c for c in getattr(df, "columns", []) if c != "Date"]
            evidence.append(f"{sym}：{len(df)} 行，字段 {_field_display([str(c) for c in cols])}。")
            raw_tables.append((str(sym), df))
        conclusion.append(f"查询返回 {len(rows)} 个标的，其中 {non_empty} 个有可展示数据。")
    if isinstance(router_result, dict):
        warnings.extend(str(w) for w in (router_result.get("warnings") or []))
    return _make_response_card(
        "query",
        understanding=_base_understanding("query_data", parsed=parsed, plan=plan, symbols=symbols),
        steps=_router_step_lines(router_result),
        conclusion=conclusion,
        evidence=evidence,
        warnings=list(dict.fromkeys(warnings)),
        raw_result=rows or {"error": error},
        raw_tables=raw_tables,
    )


def _build_compare_response_card(
    compare_result: dict[str, Any] | None,
    *,
    parsed: ParsedTask | None = None,
    plan: dict[str, Any] | None = None,
    router_result: dict[str, Any] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    result = compare_result or {}
    symbols = list(result.get("symbols") or (parsed.symbols if parsed else []))
    field = result.get("field") or ((parsed.fields or ["Close"])[0] if parsed else "Close")
    stats = result.get("stats") or {}
    pos_dist = result.get("position_dist")
    conclusion: list[str] = []
    evidence: list[str] = []
    warnings: list[str] = []
    raw_tables: list[tuple[str, Any]] = []

    if error:
        conclusion.append("比较未完成。")
        warnings.append(error)
    else:
        conclusion.extend([
            f"比较对象：{' vs '.join(symbols) if symbols else '—'}",
            f"字段：{FIELD_LABELS.get(field, field)}",
            f"总天数：{stats.get('total', 0)}，方向一致：{stats.get('matched', 0)}，不一致：{stats.get('mismatched', 0)}，一致率：{stats.get('match_rate', 0.0)}%",
        ])
        if stats.get("total", 0) == 0:
            warnings.append("对比结果为空或样本不足，暂无法计算稳定的一致性。")
        if isinstance(pos_dist, dict):
            dist_sym = result.get("stat_symbol", "")
            evidence.append(
                f"{dist_sym} 一致天位置分布：高位 {pos_dist.get('高位', 0)} 天，中位 {pos_dist.get('中位', 0)} 天，低位 {pos_dist.get('低位', 0)} 天。"
            )
        comp_df = result.get("comparison_df")
        aligned = result.get("aligned_df")
        if comp_df is not None:
            evidence.append(f"逐日对比：{len(comp_df) if hasattr(comp_df, '__len__') else '—'} 行。")
            raw_tables.append(("逐日对比", comp_df))
        if aligned is not None:
            evidence.append(f"对齐数据：{len(aligned) if hasattr(aligned, '__len__') else '—'} 行。")
            raw_tables.append(("对齐数据", aligned))
    if isinstance(router_result, dict):
        warnings.extend(str(w) for w in (router_result.get("warnings") or []))
    return _make_response_card(
        "compare",
        understanding=_base_understanding("compare_data", parsed=parsed, plan=plan, symbols=symbols, fields=[field]),
        steps=_router_step_lines(router_result),
        conclusion=conclusion,
        evidence=evidence,
        warnings=list(dict.fromkeys(warnings)),
        raw_result=result or {"error": error},
        raw_tables=raw_tables,
    )


def _build_stats_response_card(
    data: dict[str, Any] | None,
    *,
    parsed: ParsedTask | None = None,
    plan: dict[str, Any] | None = None,
    router_result: dict[str, Any] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    data = data or {}
    symbol = str(data.get("symbol", "")) if data else ""
    field = str(data.get("field", "")) if data else ""
    lookback = data.get("lookback_days")
    conclusion: list[str] = []
    evidence: list[str] = []
    warnings: list[str] = []
    if error:
        conclusion.append("统计未完成。")
        warnings.append(error)
    elif data:
        field_label = FIELD_LABELS.get(field, field)
        conclusion.extend([
            f"{symbol} {field_label} 今日值：{data.get('today_value', '—')}",
            f"近 {lookback or '—'} 日均值：{data.get('average_value', '—')}",
            f"绝对差：{data.get('absolute_diff', '—')}，涨跌幅：{data.get('pct_diff', '—')}%",
        ])
        evidence.append(f"统计操作：{data.get('operation', 'today_vs_average')}。")
        raw_table = data.get("raw_table")
        if raw_table is not None and not getattr(raw_table, "empty", False):
            evidence.append(
                f"原始表格：{len(raw_table)} 行，字段 {FIELD_LABELS.get(field, field)}。"
            )
    else:
        conclusion.append("暂无统计结果。")
        warnings.append("未找到可展示的统计结果。")
    if isinstance(router_result, dict):
        warnings.extend(str(w) for w in (router_result.get("warnings") or []))
    return _make_response_card(
        "stats",
        understanding=_base_understanding("stats", parsed=parsed, plan=plan, symbols=[symbol] if symbol else None, fields=[field] if field else None),
        steps=_router_step_lines(router_result),
        conclusion=conclusion,
        evidence=evidence,
        warnings=list(dict.fromkeys(warnings)),
        raw_result=data or {"error": error},
        raw_tables=[
            (
                str(data.get("raw_table_label") or f"最近 {lookback or '—'} 天原始表格"),
                data.get("raw_table"),
            )
        ] if data.get("raw_table") is not None else [],
    )


def _build_ai_response_card(
    ai_text: str | None,
    *,
    parsed: ParsedTask | None = None,
    plan: dict[str, Any] | None = None,
    router_result: dict[str, Any] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    warnings = [error] if error else []
    if isinstance(router_result, dict):
        warnings.extend(str(w) for w in (router_result.get("warnings") or []))
    return _make_response_card(
        "ai_explanation",
        understanding=_base_understanding("ai_explanation", parsed=parsed, plan=plan),
        steps=_router_step_lines(router_result),
        conclusion=[ai_text] if ai_text else ["AI 解释暂无结果。"],
        evidence=["AI 仅基于已有结构化结果做整理，不替代规则结论。"],
        warnings=list(dict.fromkeys(warnings)),
        raw_result={"ai_summary": ai_text, "error": error},
    )


def _build_generic_response_card(
    *,
    parsed: ParsedTask | None = None,
    plan: dict[str, Any] | None = None,
    router_result: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    all_warnings = list(warnings or [])
    if isinstance(plan, dict):
        all_warnings.extend(str(w) for w in (plan.get("warnings") or []))
    if isinstance(router_result, dict):
        all_warnings.extend(str(w) for w in (router_result.get("warnings") or []))
    return _make_response_card(
        getattr(parsed, "task_type", "unknown") if parsed is not None else "unknown",
        understanding=_base_understanding(getattr(parsed, "task_type", "unknown") if parsed else "unknown", parsed=parsed, plan=plan),
        steps=_router_step_lines(router_result),
        conclusion=["当前输入没有可展示的主结果。"],
        evidence=["暂无额外依据。"],
        warnings=list(dict.fromkeys(all_warnings)),
        raw_result={"parsed": parsed.__dict__ if parsed is not None else None, "plan": plan, "router_result": router_result},
    )


def _render_lines(lines: list[str], *, warning: bool = False) -> None:
    clean = [str(line) for line in (lines or []) if str(line).strip()]
    if not clean:
        clean = ["暂无内容。"]
    for line in clean:
        if warning and line != "暂无额外提示。":
            st.warning(line)
        else:
            st.write(line)


def _render_raw_result(card: dict[str, Any]) -> None:
    with st.expander("展开原始结果", expanded=False):
        raw = card.get("raw_result")
        if raw is not None:
            try:
                st.json(raw)
            except Exception:
                st.caption("原始结果无法以 JSON 格式显示。")


def _render_table_outputs(card: dict[str, Any]) -> None:
    tables = card.get("raw_tables") or []
    if not tables:
        return
    with st.container():
        st.markdown("**表格输出**")
        for label, table in card.get("raw_tables") or []:
            if table is None or getattr(table, "empty", False):
                st.caption(f"{label}为空。")
                continue
            st.caption(str(label))
            st.dataframe(table, use_container_width=True)


def _render_response_card(card: dict[str, Any]) -> None:
    if st is None:
        raise RuntimeError("streamlit is required to render the command bar")
    with st.container():
        for heading in _RESPONSE_CARD_SECTION_HEADINGS:
            st.markdown(f"**{heading}**")
            if heading == "任务理解":
                _render_lines(card.get("understanding", []))
            elif heading == "执行步骤":
                _render_lines(card.get("steps", []))
            elif heading == "核心结论":
                _render_lines(card.get("conclusion", []))
            elif heading == "依据摘要":
                _render_lines(card.get("evidence", []))
                _render_table_outputs(card)
            elif heading == "风险 / 提示":
                _render_lines(card.get("warnings", []), warning=True)
            elif heading == "原始结果":
                _render_raw_result(card)


def _render_projection_result(
    result: dict[str, Any],
    *,
    parsed: ParsedTask | None = None,
    plan: dict[str, Any] | None = None,
    router_result: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    _render_response_card(
        _build_projection_response_card(
            result,
            parsed=parsed,
            plan=plan,
            router_result=router_result,
            error=error,
        )
    )


def _render_query_result(
    query_result: list[tuple[str, Any]] | None,
    *,
    parsed: ParsedTask | None = None,
    plan: dict[str, Any] | None = None,
    router_result: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    _render_response_card(
        _build_query_response_card(
            query_result,
            parsed=parsed,
            plan=plan,
            router_result=router_result,
            error=error,
        )
    )


def _render_compare_result(
    compare_result: dict[str, Any] | None,
    *,
    parsed: ParsedTask | None = None,
    plan: dict[str, Any] | None = None,
    router_result: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    _render_response_card(
        _build_compare_response_card(
            compare_result,
            parsed=parsed,
            plan=plan,
            router_result=router_result,
            error=error,
        )
    )


def _render_intent_plan(plan: dict[str, Any]) -> None:
    if st is None:
        raise RuntimeError("streamlit is required to render the command bar")
    if not isinstance(plan, dict):
        return

    st.markdown("**规划结果 / 识别计划**")
    if not plan.get("supported", False):
        for warning in plan.get("warnings", []) or ["暂未识别到可执行计划。"]:
            st.warning(str(warning))
        return

    st.caption(f"主任务：{plan.get('primary_intent', 'unknown')}")
    steps = plan.get("steps", []) or []
    if steps:
        rows = []
        for idx, step in enumerate(steps, start=1):
            rows.append({
                "step": idx,
                "type": step.get("type", ""),
                "symbols": "、".join(
                    step.get("symbols") or ([step["symbol"]] if step.get("symbol") else [])
                ),
                "fields": "、".join(
                    step.get("fields") or ([step["field"]] if step.get("field") else [])
                ),
                "lookback_days": step.get("lookback_days", ""),
                "optional": "yes" if step.get("optional") else "",
            })
        st.dataframe(rows, hide_index=True, use_container_width=True)

    ai_followups = plan.get("ai_followups", []) or []
    if ai_followups:
        st.caption("AI follow-up")
        for item in ai_followups:
            status = "可用" if item.get("available") else "未配置 OPENAI_API_KEY"
            st.caption(f"- {item.get('type', 'ai_followup')}：{status}")

    for warning in plan.get("warnings", []) or []:
        st.warning(str(warning))


def _render_stats_result(
    data: dict[str, Any] | None,
    *,
    parsed: ParsedTask | None = None,
    plan: dict[str, Any] | None = None,
    router_result: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    _render_response_card(
        _build_stats_response_card(
            data,
            parsed=parsed,
            plan=plan,
            router_result=router_result,
            error=error,
        )
    )


def _render_router_steps(steps_executed: list[dict[str, Any]]) -> None:
    if st is None or not steps_executed:
        return
    _STATUS_LABEL = {
        "success":      "✅ success",
        "skipped":      "⏭ skipped",
        "failed":       "❌ failed",
        "planned_only": "📋 planned_only",
    }
    st.markdown("**执行步骤**")
    rows = []
    for step in steps_executed:
        status = step.get("status", "")
        rows.append({
            "步骤": step.get("step", ""),
            "类型": step.get("type", ""),
            "状态": _STATUS_LABEL.get(status, status),
            "信息": step.get("error") or step.get("warning") or "",
        })
    st.dataframe(rows, hide_index=True, use_container_width=True)


def _render_router_primary(
    router_result: dict[str, Any] | None,
    *,
    parsed: ParsedTask | None = None,
    plan: dict[str, Any] | None = None,
) -> None:
    """Render primary result from router for plan-handled (unknown-type) inputs."""
    if st is None or not isinstance(router_result, dict):
        return
    primary = router_result.get("primary_result")
    if not primary:
        return
    rtype = primary.get("type", "")
    if rtype == "projection":
        res = st.session_state.get(_SS_PROJ_RESULT)
        proj_err = st.session_state.get(_SS_PROJ_ERROR)
        if res is not None or proj_err:
            _render_projection_result(res, parsed=parsed, plan=plan, router_result=router_result, error=proj_err)
    elif rtype == "query":
        res = st.session_state.get(_SS_QUERY_RESULT)
        if res is not None:
            _render_query_result(res, parsed=parsed, plan=plan, router_result=router_result)
    elif rtype == "compare":
        res = st.session_state.get(_SS_COMPARE_RESULT)
        if res is not None:
            _render_compare_result(res, parsed=parsed, plan=plan, router_result=router_result)
    elif rtype == "stats":
        _render_stats_result(primary.get("data"), parsed=parsed, plan=plan, router_result=router_result)
    # AI explanation (aux)
    ai_text = router_result.get("aux_results", {}).get("ai_explanation")
    if ai_text:
        _render_response_card(
            _build_ai_response_card(ai_text, parsed=parsed, plan=plan, router_result=router_result)
        )


def _sync_router_to_session(router_result: dict[str, Any]) -> None:
    """Sync router session_ctx results back to individual session-state keys."""
    if not isinstance(router_result, dict):
        return

    # Sync only results produced by this router run. session_ctx may also carry
    # prior compare/projection results for AI follow-ups, and those must not be
    # rehydrated as the current command's visible result.
    for step in router_result.get("steps_executed") or []:
        if step.get("status") != "success":
            continue
        result = step.get("result")
        stype = step.get("type", "")
        if stype == "projection" and result is not None:
            st.session_state[_SS_PROJ_RESULT] = result
            st.session_state[_SS_PROJ_ERROR] = None
            st.session_state[_SS_LAST_PROJ_CTX] = result
        elif stype == "query" and result is not None:
            st.session_state[_SS_QUERY_RESULT] = result
            st.session_state[_SS_QUERY_ERROR] = None
        elif stype == "compare" and result is not None:
            st.session_state[_SS_COMPARE_RESULT] = result
            st.session_state[_SS_COMPARE_ERROR] = None
            st.session_state[_SS_LAST_COMP_CTX] = result
        elif stype in ("ai_explain_projection", "ai_explain_compare", "ai_explain_risk") and result is not None:
            st.session_state[_SS_AI_RESULT] = result
            st.session_state[_SS_AI_ERROR] = None

    # Propagate per-step failure messages for non-optional steps
    for step in router_result.get("steps_executed") or []:
        if step.get("status") == "failed" and step.get("error"):
            stype = step.get("type", "")
            if stype == "projection":
                st.session_state[_SS_PROJ_ERROR] = step["error"]
            elif stype == "query":
                st.session_state[_SS_QUERY_ERROR] = step["error"]
            elif stype == "compare":
                st.session_state[_SS_COMPARE_ERROR] = step["error"]


def _router_primary_type(router_result: dict[str, Any] | None) -> str | None:
    if not isinstance(router_result, dict):
        return None
    primary = router_result.get("primary_result")
    if not isinstance(primary, dict):
        return None
    rtype = primary.get("type")
    return str(rtype) if rtype else None


def _parsed_router_type(parsed: ParsedTask) -> str | None:
    return {
        "run_projection": "projection",
        "query_data": "query",
        "compare_data": "compare",
        "ai_explanation": "ai_explanation",
    }.get(parsed.task_type)


def _render_stored_result() -> None:
    """Display the last parse+execution result stored in session state.

    Called on every render so results persist across tab switches and
    other re-render triggers.
    """
    if st is None or _SS_PARSED not in st.session_state:
        return

    parsed: ParsedTask   = st.session_state[_SS_PARSED]
    plan                 = st.session_state.get(_SS_PLAN)
    router_result        = st.session_state.get(_SS_ROUTER_RESULT)
    plan_supported       = isinstance(plan, dict) and plan.get("supported", False)

    # Parse error: hard-block only when the plan is also unsupported.
    if parsed.parse_error:
        if not plan_supported:
            st.error(f"**{CMD_ERROR_LABEL}：** {parsed.parse_error}")
            _render_response_card(
                _build_generic_response_card(
                    parsed=parsed,
                    plan=plan,
                    router_result=router_result,
                    warnings=[parsed.parse_error],
                )
            )
            return
        st.caption("（指令解析器标记为未识别，意图规划已执行）")

    st.success(f"**{CMD_RESULT_LABEL}**")

    primary_type = _router_primary_type(router_result)
    if primary_type and primary_type != _parsed_router_type(parsed):
        _render_router_primary(router_result, parsed=parsed, plan=plan)
        return

    # Task-specific execution result
    if parsed.task_type == "run_projection":
        proj_error: str | None = st.session_state.get(_SS_PROJ_ERROR)
        proj_result: dict | None = st.session_state.get(_SS_PROJ_RESULT)
        _render_projection_result(
            proj_result,
            parsed=parsed,
            plan=plan,
            router_result=router_result,
            error=proj_error,
        )

    elif parsed.task_type == "query_data":
        # If the intent planner routed to projection (parser/planner mismatch for
        # inputs like "看看明天"), show projection result instead of query result.
        if isinstance(plan, dict) and plan.get("primary_intent") == "projection":
            proj_error: str | None = st.session_state.get(_SS_PROJ_ERROR)
            proj_result: dict | None = st.session_state.get(_SS_PROJ_RESULT)
            _render_projection_result(
                proj_result,
                parsed=parsed,
                plan=plan,
                router_result=router_result,
                error=proj_error,
            )
        else:
            q_error: str | None = st.session_state.get(_SS_QUERY_ERROR)
            q_result = st.session_state.get(_SS_QUERY_RESULT)
            _render_query_result(
                q_result,
                parsed=parsed,
                plan=plan,
                router_result=router_result,
                error=q_error,
            )

    elif parsed.task_type == "compare_data":
        c_error: str | None = st.session_state.get(_SS_COMPARE_ERROR)
        c_result = st.session_state.get(_SS_COMPARE_RESULT)
        _render_compare_result(
            c_result,
            parsed=parsed,
            plan=plan,
            router_result=router_result,
            error=c_error,
        )

    elif parsed.task_type == "ai_explanation":
        ai_error: str | None = st.session_state.get(_SS_AI_ERROR)
        ai_result: str | None = st.session_state.get(_SS_AI_RESULT)
        _render_response_card(
            _build_ai_response_card(
                ai_result,
                parsed=parsed,
                plan=plan,
                router_result=router_result,
                error=ai_error,
            )
        )

    else:
        # Fallback: render primary result from router (plan-resolved unknowns)
        if isinstance(router_result, dict) and router_result.get("primary_result"):
            _render_router_primary(router_result, parsed=parsed, plan=plan)
        else:
            _render_response_card(
                _build_generic_response_card(
                    parsed=parsed,
                    plan=plan,
                    router_result=router_result,
                )
            )


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

    with st.container():
        st.markdown("**指令中心（中文命令）**")
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
                parsed, plan, _ = parse_with_ai_primary(cmd_text)

                # Persist parse result; clear any prior execution results.
                st.session_state[_SS_LAST_INPUT] = cmd_text
                st.session_state[_SS_PARSED]     = parsed
                st.session_state[_SS_PLAN]       = plan
                for key in (
                    _SS_PROJ_RESULT, _SS_PROJ_ERROR,
                    _SS_QUERY_RESULT, _SS_QUERY_ERROR,
                    _SS_COMPARE_RESULT, _SS_COMPARE_ERROR,
                    _SS_AI_RESULT, _SS_AI_ERROR,
                ):
                    st.session_state.pop(key, None)

                # Build session context from prior successful results
                # (enables AI follow-ups to reference previous projection/compare)
                _session_ctx: dict[str, Any] = {
                    "latest_projection_result": st.session_state.get(_SS_LAST_PROJ_CTX),
                    "latest_compare_result":    st.session_state.get(_SS_LAST_COMP_CTX),
                    "latest_query_result":      None,
                    "latest_stats_result":      None,
                    "latest_ai_explanation":    None,
                }
                _router_result = route_plan(plan, session_ctx=_session_ctx)
                st.session_state[_SS_ROUTER_RESULT] = _router_result
                _sync_router_to_session(_router_result)

        # Always render whatever is in session state — survives re-renders.
        _render_stored_result()
