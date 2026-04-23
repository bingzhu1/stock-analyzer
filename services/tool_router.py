"""services/tool_router.py

Lightweight multi-step tool router for the Command Center.

Reads a plan dict produced by intent_planner.plan_intent() and executes each
step using existing tool modules.  Never raises — all exceptions are caught
per-step and reflected in the step's status field.

Step statuses:
    success      — executed and returned a result
    skipped      — intentionally skipped (optional step failure, missing symbol, no API key)
    failed       — non-optional step raised an exception
    planned_only — step type not yet executable (e.g. unsupported stats operation)

Session context keys maintained across steps:
    latest_query_result, latest_compare_result,
    latest_projection_result, latest_stats_result,
    latest_ai_explanation
"""

from __future__ import annotations

import os
from typing import Any

from services.comparison_engine import compare_field
from services.data_query import load_symbol_data as _default_loader
from services.multi_symbol_view import build_aligned_view as _default_aligned_loader
from services.projection_entrypoint import run_projection_entrypoint as _default_proj_runner
from services.stats_engine import compute_match_stats
from services.ai_summary import (
    build_compare_ai_explanation,
    build_projection_ai_explanation,
    build_risk_ai_explanation,
)
from services.openai_client import OpenAIClientError


# ── step status constants ──────────────────────────────────────────────────────

STATUS_SUCCESS = "success"
STATUS_SKIPPED = "skipped"
STATUS_FAILED  = "failed"
STATUS_PLANNED = "planned_only"

_AI_TYPES = frozenset({"ai_explain_projection", "ai_explain_compare", "ai_explain_risk"})


# ── internal helpers ───────────────────────────────────────────────────────────

def _mk_step(
    n: int,
    type_: str,
    status: str,
    *,
    result: Any = None,
    error: str | None = None,
    warning: str | None = None,
) -> dict[str, Any]:
    return {
        "step": n, "type": type_, "status": status,
        "result": result, "error": error, "warning": warning,
    }


def _run_stats(step: dict[str, Any], *, loader: Any) -> tuple[Any, str | None]:
    """Execute a today_vs_average stats step. Returns (result, error)."""
    symbol  = step.get("symbol") or "AVGO"
    field   = step.get("field") or "Volume"
    n       = step.get("lookback_days", 20)
    op      = step.get("operation", "today_vs_average")

    if op != "today_vs_average":
        return None, f"统计操作 '{op}' 暂不支持，已标记为 planned_only。"

    try:
        df = loader(symbol, window=n + 1, fields=[field])
        if df is None or df.empty or field not in df.columns:
            return None, f"无法加载 {symbol} 的 {field} 数据。"
        vals = df[field].dropna()
        if len(vals) < 2:
            return None, "数据不足，无法计算今日 vs 均值。"
        today = float(vals.iloc[-1])
        avg   = float(vals.iloc[:-1].mean())
        diff  = round(today - avg, 4)
        pct   = round((today - avg) / avg * 100, 2) if avg != 0 else None
        raw_cols = ["Date", field] if "Date" in df.columns else [field]
        raw_table = df[raw_cols].copy()
        return {
            "symbol": symbol, "field": field,
            "lookback_days": n, "operation": op,
            "today_value":    round(today, 4),
            "average_value":  round(avg, 4),
            "absolute_diff":  diff,
            "pct_diff":       pct,
            "raw_table":      raw_table,
            "raw_table_label": f"最近 {n} 天均值样本 + 今日原始表格",
        }, None
    except Exception as exc:
        return None, f"统计计算失败：{exc}"


def _projection_ai_payload(r: dict[str, Any]) -> dict[str, Any]:
    report   = r.get("projection_report")
    readable = report.get("readable_summary") if isinstance(report, dict) else None
    return {
        "kind":               "router_projection_explanation",
        "projection_report":  report   if isinstance(report, dict)   else {},
        "readable_summary":   readable if isinstance(readable, dict) else {},
        "advisory":           r.get("advisory", {}),
        "request":            r.get("request", {}),
        "ready":              r.get("ready"),
    }


def _compare_ai_payload(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind":    "router_compare_explanation",
        "symbols": r.get("symbols", []),
        "field":   r.get("field", ""),
        "stats":   r.get("stats", {}),
    }


def _run_ai(
    step_type: str,
    ctx: dict[str, Any],
    *,
    proj_builder: Any = None,
    comp_builder: Any = None,
    risk_builder: Any = None,
) -> tuple[str | None, str | None]:
    """Execute an AI follow-up step. Returns (text, error). Never raises."""
    if not os.getenv("OPENAI_API_KEY", "").strip():
        return None, "OpenAI 未配置，AI follow-up 已跳过。"

    _proj = proj_builder or build_projection_ai_explanation
    _comp = comp_builder or build_compare_ai_explanation
    _risk = risk_builder or build_risk_ai_explanation

    try:
        if step_type == "ai_explain_projection":
            pr = ctx.get("latest_projection_result")
            if not pr:
                return None, "未找到 projection 上下文，无法执行 AI 推演解释。"
            return _proj(_projection_ai_payload(pr)), None

        if step_type == "ai_explain_compare":
            cr = ctx.get("latest_compare_result")
            if not cr:
                return None, "未找到 compare 上下文，无法执行 AI 比较解释。"
            return _comp(_compare_ai_payload(cr)), None

        if step_type == "ai_explain_risk":
            pr = ctx.get("latest_projection_result")
            if not pr:
                return None, "未找到 projection 上下文，无法执行 AI 风险解释。"
            return _risk(_projection_ai_payload(pr)), None

        return None, f"未知的 AI follow-up 类型：{step_type}"

    except OpenAIClientError as exc:
        return None, str(exc)
    except Exception as exc:
        return None, f"AI 解释生成失败：{exc}"


# ── public API ─────────────────────────────────────────────────────────────────

def route_plan(
    plan: dict[str, Any],
    *,
    session_ctx: dict[str, Any] | None = None,
    _loader: Any = None,
    _aligned_loader: Any = None,
    _projection_runner: Any = None,
    _proj_ai_builder: Any = None,
    _comp_ai_builder: Any = None,
    _risk_ai_builder: Any = None,
) -> dict[str, Any]:
    """
    Execute a plan from intent_planner.plan_intent().  Never raises.

    Parameters
    ----------
    plan : dict
        Output of plan_intent(); must have keys ``supported`` and ``steps``.
    session_ctx : dict, optional
        Mutable dict carrying cross-step context (prior projection/compare/query
        results for AI follow-up chaining).  If None a fresh dict is used.
    _loader : callable, optional
        Injected data loader (for query and stats steps); defaults to
        load_symbol_data.
    _aligned_loader : callable, optional
        Injected aligned-view builder (for compare steps); defaults to
        build_aligned_view.
    _projection_runner : callable, optional
        Injected projection function; defaults to run_projection_entrypoint.
    _proj_ai_builder, _comp_ai_builder, _risk_ai_builder : callable, optional
        Injected AI builders (for AI follow-up steps).

    Returns
    -------
    dict with keys:
        plan              — the input plan dict
        steps_executed    — list of per-step result dicts
        primary_result    — {"type": ..., "data": ...} for the first non-optional result
        aux_results       — secondary results keyed by type ("compare", "ai_explanation")
        session_ctx       — updated session context dict
        warnings          — deduplicated list of warning / error messages
    """
    if session_ctx is None:
        session_ctx = {}

    loader   = _loader           or _default_loader
    al_load  = _aligned_loader   or _default_aligned_loader
    proj_run = _projection_runner or _default_proj_runner

    executed:       list[dict[str, Any]] = []
    primary_result: dict[str, Any] | None = None
    aux_results:    dict[str, Any]        = {}
    warnings:       list[str]             = list(plan.get("warnings") or [])

    # ── early exit when plan is unsupported ────────────────────────────────────
    if not plan.get("supported"):
        for w in (plan.get("warnings") or ["计划未受支持，无法执行。"]):
            if w not in warnings:
                warnings.append(w)
        return {
            "plan": plan, "steps_executed": [],
            "primary_result": None, "aux_results": {},
            "session_ctx": session_ctx,
            "warnings": list(dict.fromkeys(warnings)),
        }

    steps        = plan.get("steps")        or []
    ai_followups = plan.get("ai_followups") or []

    # ── primary steps ──────────────────────────────────────────────────────────
    for i, step in enumerate(steps, start=1):
        stype    = step.get("type", "")
        optional = bool(step.get("optional", False))

        # ── query ──────────────────────────────────────────────────────────────
        if stype == "query":
            syms       = step.get("symbols") or []
            fields     = step.get("fields")  or None
            win        = step.get("lookback_days", 20)
            start_date = step.get("start_date")
            end_date   = step.get("end_date")
            if not syms:
                msg = "查询步骤缺少标的。"
                executed.append(_mk_step(i, stype, STATUS_FAILED, error=msg))
                warnings.append(msg)
            else:
                try:
                    if start_date and end_date:
                        res = [
                            (s, loader(s, start_date=start_date, end_date=end_date,
                                       fields=fields or None))
                            for s in syms
                        ]
                    else:
                        res = [(s, loader(s, window=win, fields=fields or None)) for s in syms]
                    executed.append(_mk_step(i, stype, STATUS_SUCCESS, result=res))
                    session_ctx["latest_query_result"] = res
                    if primary_result is None:
                        primary_result = {"type": "query", "data": res}
                except Exception as exc:
                    msg = f"数据查询失败：{exc}"
                    st_ = STATUS_SKIPPED if optional else STATUS_FAILED
                    executed.append(_mk_step(i, stype, st_, error=msg))
                    if not optional:
                        warnings.append(msg)

        # ── compare ────────────────────────────────────────────────────────────
        elif stype == "compare":
            syms = step.get("symbols") or []
            if step.get("missing_second_symbol") or len(syms) < 2:
                msg = "compare 缺少第二标的，已跳过执行。"
                executed.append(_mk_step(i, stype, STATUS_SKIPPED, warning=msg))
                warnings.append(msg)
            else:
                fields  = step.get("fields") or ["Close"]
                win     = step.get("lookback_days", 20)
                cf_name = fields[0] if fields else "Close"
                vf      = list(fields)
                if cf_name not in vf:
                    vf = [cf_name] + vf
                try:
                    aligned = al_load(syms, window=win, fields=vf)
                    comp_df = compare_field(aligned, cf_name, syms[0], syms[1])
                    stats   = compute_match_stats(comp_df)
                    res = {
                        "aligned_df": aligned, "comparison_df": comp_df,
                        "stats": stats, "field": cf_name, "symbols": syms,
                    }
                    executed.append(_mk_step(i, stype, STATUS_SUCCESS, result=res))
                    session_ctx["latest_compare_result"] = res
                    if primary_result is None and not optional:
                        primary_result = {"type": "compare", "data": res}
                    else:
                        aux_results["compare"] = res
                except Exception as exc:
                    msg = f"数据对比失败：{exc}"
                    st_ = STATUS_SKIPPED if optional else STATUS_FAILED
                    executed.append(_mk_step(i, stype, st_, error=msg))
                    if not optional:
                        warnings.append(msg)

        # ── projection ─────────────────────────────────────────────────────────
        elif stype == "projection":
            syms = step.get("symbols") or ["AVGO"]
            win  = step.get("lookback_days", 20)
            try:
                kwargs: dict[str, Any] = {"symbol": syms[0]}
                if win and win > 0:
                    kwargs["lookback_days"] = win
                res = proj_run(**kwargs)
                executed.append(_mk_step(i, stype, STATUS_SUCCESS, result=res))
                session_ctx["latest_projection_result"] = res
                if primary_result is None:
                    primary_result = {"type": "projection", "data": res}
            except Exception as exc:
                msg = f"推演执行失败：{exc}"
                st_ = STATUS_SKIPPED if optional else STATUS_FAILED
                executed.append(_mk_step(i, stype, st_, error=msg))
                if not optional:
                    warnings.append(msg)

        # ── stats ──────────────────────────────────────────────────────────────
        elif stype == "stats":
            res, err = _run_stats(step, loader=loader)
            if err:
                is_planned = "planned_only" in err
                st_ = (STATUS_PLANNED if is_planned
                       else STATUS_SKIPPED if optional
                       else STATUS_FAILED)
                executed.append(_mk_step(i, stype, st_, error=err))
                if not optional:
                    warnings.append(err)
            else:
                executed.append(_mk_step(i, stype, STATUS_SUCCESS, result=res))
                session_ctx["latest_stats_result"] = res
                if primary_result is None:
                    primary_result = {"type": "stats", "data": res}

        # ── unknown step type ──────────────────────────────────────────────────
        else:
            msg = f"步骤类型 '{stype}' 暂不支持执行。"
            executed.append(_mk_step(i, stype, STATUS_PLANNED, warning=msg))

    # ── AI follow-ups ──────────────────────────────────────────────────────────
    for j, fu in enumerate(ai_followups, start=len(steps) + 1):
        fu_type = fu.get("type", "")
        if not fu.get("available"):
            msg = "OpenAI 未配置，AI follow-up 已跳过。"
            executed.append(_mk_step(j, fu_type, STATUS_SKIPPED, warning=msg))
            if msg not in warnings:
                warnings.append(msg)
            continue

        text, err = _run_ai(
            fu_type, session_ctx,
            proj_builder=_proj_ai_builder,
            comp_builder=_comp_ai_builder,
            risk_builder=_risk_ai_builder,
        )
        if err:
            executed.append(_mk_step(j, fu_type, STATUS_SKIPPED, error=err))
            if err not in warnings:
                warnings.append(err)
        else:
            executed.append(_mk_step(j, fu_type, STATUS_SUCCESS, result=text))
            session_ctx["latest_ai_explanation"] = text
            aux_results["ai_explanation"] = text

    return {
        "plan":           plan,
        "steps_executed": executed,
        "primary_result": primary_result,
        "aux_results":    aux_results,
        "session_ctx":    session_ctx,
        "warnings":       list(dict.fromkeys(warnings)),
    }
