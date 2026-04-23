"""Legacy compat shell for projection_v2 entrypoint results.

The v2 raw payload is the projection source-of-truth. This module only builds
the legacy `projection_report` / `advisory` shell that older callers may still
consume as a fallback during the cutover window.
"""

from __future__ import annotations

from typing import Any, Callable

from services.projection_orchestrator_v2 import run_projection_v2


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _caution_level(count: int) -> str:
    if count <= 0:
        return "none"
    if count <= 2:
        return "low"
    if count <= 4:
        return "medium"
    return "high"


def _build_evidence_trace(v2: dict[str, Any], final: dict[str, Any]) -> dict[str, Any]:
    """Map v2 trace list to evidence_trace dict expected by _evidence_trace_lines."""
    trace_list = _as_list(v2.get("trace"))
    tool_trace = [
        f"{item.get('step', '')}:{item.get('status', '')}"
        for item in trace_list
        if isinstance(item, dict)
    ]
    direction = str(final.get("final_direction") or "中性")
    confidence = str(final.get("final_confidence") or "low")
    decision_factors = [
        str(f) for f in _as_list(final.get("decision_factors")) if str(f).strip()
    ]
    return {
        "final_conclusion": {
            "direction": direction,
            "open_tendency": "平开",
            "close_tendency": "震荡",
            "confidence": confidence,
        },
        "tool_trace": tool_trace,
        "key_observations": decision_factors[:3],
        "decision_steps": [],
        "verification_points": [],
    }


def _build_readable_summary(
    final: dict[str, Any],
    primary: dict[str, Any],
    risk_items: list[str],
) -> dict[str, Any]:
    direction = str(final.get("final_direction") or "中性")
    confidence = str(final.get("final_confidence") or "low")
    risk_level = str(final.get("risk_level") or "medium")
    basis = [str(b) for b in _as_list(primary.get("basis")) if str(b).strip()]
    return {
        "kind": "predict_readable_summary",
        "baseline_judgment": {
            "text": f"方向：{direction}，置信度：{confidence}，风险等级：{risk_level}。",
            "risk_level": risk_level,
        },
        "open_projection": {"text": "开盘倾向：平开（基于主分析）。"},
        "close_projection": {"text": "收盘倾向：震荡收敛（基于主分析）。"},
        "rationale": basis[:4],
        "risk_reminders": risk_items[:5],
    }


def _build_projection_report(
    final: dict[str, Any],
    primary: dict[str, Any],
    preflight: dict[str, Any],
    v2: dict[str, Any],
) -> dict[str, Any]:
    direction = str(final.get("final_direction") or "中性")
    confidence = str(final.get("final_confidence") or "low")

    basis = [str(b) for b in _as_list(primary.get("basis")) if str(b).strip()]
    if not basis:
        basis = [str(f) for f in _as_list(final.get("decision_factors")) if str(f).strip()]
    lookback = int(primary.get("lookback_days") or v2.get("lookback_days") or 20)
    if not any("最近" in b for b in basis):
        basis.append(f"最近 {lookback} 天分析窗口。")

    rule_warnings = [str(w) for w in _as_list(preflight.get("rule_warnings")) if str(w).strip()]
    final_warnings = [str(w) for w in _as_list(final.get("warnings")) if str(w).strip()]
    risk_items = list(dict.fromkeys(rule_warnings + final_warnings))

    readable = _build_readable_summary(final, primary, risk_items)
    evidence_trace = _build_evidence_trace(v2, final)
    target_date = str(v2.get("target_date") or primary.get("target_date") or "")

    report_text = f"明日方向：{direction}。\n明日基准判断：{direction}（置信度 {confidence}）。"
    return {
        "kind": "final_projection_report",
        "target_date": target_date,
        "direction": direction,
        "open_tendency": "平开",
        "close_tendency": "震荡",
        "confidence": confidence,
        "basis_summary": basis,
        "risk_reminders": risk_items,
        "report_text": report_text,
        "readable_summary": readable,
        "evidence_trace": evidence_trace,
    }


def build_projection_entrypoint_result(
    *,
    v2_raw: dict[str, Any],
    symbol: str,
    lookback_days: int | None = None,
    error_category: str | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    """Package one entrypoint result with v2 raw as primary and compat as legacy."""
    normalized_symbol = str(symbol or "").strip().upper()
    if not normalized_symbol:
        raise ValueError("symbol must be a non-empty string")

    v2 = _as_dict(v2_raw)
    final = _as_dict(v2.get("final_decision"))
    primary = _as_dict(v2.get("primary_analysis"))
    preflight = _as_dict(v2.get("preflight"))

    matched_rules = preflight.get("matched_rules")
    matched_count = len(matched_rules) if isinstance(matched_rules, list) else 0
    rule_warnings = [str(w) for w in _as_list(preflight.get("rule_warnings")) if str(w).strip()]

    advisory = {
        "matched_count": matched_count,
        "caution_level": _caution_level(matched_count),
        "reminder_lines": rule_warnings,
        "ready": bool(preflight.get("ready", True)),
    }

    projection_report = _build_projection_report(final, primary, preflight, v2)

    step_keys = list(_as_dict(v2.get("step_status")).keys())
    notes = [
        f"Projection v2 orchestration chain completed. Steps: {', '.join(step_keys)}."
        if step_keys
        else "Projection v2 orchestration chain completed."
    ]

    return {
        "kind": "projection_entrypoint_result",
        "projection_schema": "v2",
        "source_of_truth": "projection_v2_raw",
        "legacy_compat": {
            "kind": "projection_v2_legacy_compat",
            "projection_report": "legacy_fallback",
            "advisory": "legacy_fallback",
        },
        "symbol": normalized_symbol,
        "ready": bool(v2.get("ready")),
        "advisory_only": False,
        "request": {
            "symbol": normalized_symbol,
            "error_category": error_category,
            "limit": limit,
            "lookback_days": lookback_days,
        },
        "notes": notes,
        "advisory": advisory,
        "projection_report": projection_report,
        "projection_v2_raw": v2,
    }


def build_projection_v2_compat(
    *,
    symbol: str,
    lookback_days: int | None = None,
    error_category: str | None = None,
    limit: int = 5,
    _v2_runner: Callable[..., dict[str, Any]] = run_projection_v2,
) -> dict[str, Any]:
    """Run projection v2 and return one v2-first result plus a legacy shell.

    error_category and limit are preserved in the request dict for caller
    transparency but are not forwarded to the v2 chain.
    """
    normalized_symbol = str(symbol or "").strip().upper()
    if not normalized_symbol:
        raise ValueError("symbol must be a non-empty string")

    effective_lookback = int(lookback_days or 20)

    v2 = _v2_runner(
        symbol=normalized_symbol,
        lookback_days=effective_lookback,
    )
    return build_projection_entrypoint_result(
        v2_raw=v2,
        symbol=normalized_symbol,
        lookback_days=lookback_days,
        error_category=error_category,
        limit=limit,
    )
