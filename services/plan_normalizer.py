"""services/plan_normalizer.py

Validates an AI task schema produced by ai_task_parser and converts it to:
  1. A plan dict compatible with route_plan()
  2. A ParsedTask for backward compat with command_bar rendering

Year-inference confidence threshold
────────────────────────────────────
When the AI sets time_range.inferred=true it also reports confidence (0–1).
  ≥ INFERRED_CONFIDENCE_MIN  → proceed; add a warning so the user can verify
  < INFERRED_CONFIDENCE_MIN  → block (supported=False); ask user to clarify year

This gives users the benefit of the doubt for clear cases ("2月5号至2月25号"
when today is April 2026 → obviously 2026, confidence ≈ 0.9) while refusing to
silently execute when the year is genuinely ambiguous.
"""

from __future__ import annotations

from typing import Any

from services.command_parser import DEFAULT_WINDOW, ParsedTask
from services.data_query import ALL_SUPPORTED_FIELDS, SUPPORTED_SYMBOLS

# ── constants ──────────────────────────────────────────────────────────────────

INFERRED_CONFIDENCE_MIN: float = 0.65

_INTENT_TO_TASK_TYPE: dict[str, str] = {
    "query":          "query_data",
    "compare":        "compare_data",
    "filter":         "query_data",
    "projection":     "run_projection",
    "review":         "run_review",
    "ai_explanation": "ai_explanation",
}


# ── helpers ────────────────────────────────────────────────────────────────────

def _clean_symbols(raw: list) -> tuple[list[str], list[str]]:
    """Return (valid, invalid) symbol lists."""
    valid, invalid = [], []
    for s in raw:
        if not isinstance(s, str):
            continue
        upper = s.strip().upper()
        if not upper:
            continue
        if upper in SUPPORTED_SYMBOLS:
            valid.append(upper)
        else:
            invalid.append(upper)
    return valid, invalid


def _clean_fields(raw: list) -> tuple[list[str], list[str]]:
    """Return (valid, invalid) field lists."""
    valid, invalid = [], []
    for f in raw:
        if not isinstance(f, str):
            continue
        stripped = f.strip()
        if not stripped:
            continue
        if stripped in ALL_SUPPORTED_FIELDS:
            valid.append(stripped)
        else:
            invalid.append(stripped)
    return valid, invalid


def _unsupported_plan(text: str, warnings: list[str]) -> dict[str, Any]:
    return {
        "kind": "intent_plan",
        "raw_text": text,
        "supported": False,
        "primary_intent": "unsupported",
        "steps": [],
        "symbols": [],
        "lookback_days": DEFAULT_WINDOW,
        "fields": [],
        "ai_followups": [],
        "warnings": warnings,
        "planner": "ai_primary",
    }


# ── public API ─────────────────────────────────────────────────────────────────

def normalize(
    text: str,
    schema: dict[str, Any],
) -> tuple[ParsedTask, dict[str, Any]]:
    """
    Validate *schema* and return (parsed, plan).

    *parsed* is a ParsedTask for backward compat with the existing UI renderers.
    *plan* is a dict ready for route_plan().

    Never raises.
    """
    warnings: list[str] = []
    blocking = False

    # ── intent ─────────────────────────────────────────────────────────────────
    intent = str(schema.get("intent", ""))
    task_type = _INTENT_TO_TASK_TYPE.get(intent)
    if task_type is None:
        err = f"AI 返回了不支持的意图：{intent!r}。"
        parsed = ParsedTask(
            task_type="unknown", symbols=[], fields=[],
            window=DEFAULT_WINDOW, raw_text=text, parse_error=err,
        )
        return parsed, _unsupported_plan(text, [err])

    # ── symbols ────────────────────────────────────────────────────────────────
    symbols, bad_syms = _clean_symbols(schema.get("symbols") or [])
    if bad_syms:
        warnings.append(f"以下标的不受支持，已忽略：{', '.join(bad_syms)}。")

    # ── fields ─────────────────────────────────────────────────────────────────
    fields, bad_fields = _clean_fields(schema.get("fields") or [])
    if bad_fields:
        warnings.append(f"以下字段不受支持，已忽略：{', '.join(bad_fields)}。")

    # ── time range ─────────────────────────────────────────────────────────────
    time_range: dict[str, Any] = schema.get("time_range") or {}
    tr_type = str(time_range.get("type", "relative"))
    start_date: str | None = None
    end_date: str | None = None
    lookback_days: int = DEFAULT_WINDOW

    if tr_type == "absolute":
        start_date = time_range.get("start_date") or None
        end_date   = time_range.get("end_date")   or None
        inferred   = bool(time_range.get("inferred", False))
        confidence = float(time_range.get("confidence") or 1.0)
        raw_time   = str(time_range.get("raw_text") or "")

        if inferred:
            if confidence < INFERRED_CONFIDENCE_MIN:
                warnings.append(
                    f"AI 对时间范围的年份推断置信度过低（{confidence:.0%}），"
                    f"无法安全执行。原始表达：{raw_time or '—'}。"
                    "请补充完整年份，例如：2026年2月5日至2月25日。"
                )
                blocking = True
                start_date = end_date = None  # 置信度不足，不可用此日期
            else:
                warnings.append(
                    f"时间范围由 AI 推断（置信度 {confidence:.0%}）。"
                    f"原始表达：{raw_time or '—'}，推断为 {start_date} 至 {end_date}。"
                    "如有误请补充完整年份。"
                )

        if start_date and end_date and start_date > end_date:
            warnings.append(
                f"起始日期晚于结束日期（{start_date} > {end_date}），请检查输入。"
            )
            blocking = True
            start_date = end_date = None

        if (not start_date or not end_date) and not blocking:
            warnings.append("无法解析完整的起止日期，请补充。")
            blocking = True

    elif tr_type == "relative":
        raw_lb = time_range.get("lookback_days")
        lookback_days = int(raw_lb) if isinstance(raw_lb, (int, float)) and raw_lb > 0 else DEFAULT_WINDOW

    elif tr_type == "next_trading_day":
        lookback_days = -1

    # ── intent-specific validation ─────────────────────────────────────────────
    if intent in ("query", "filter"):
        if not symbols:
            warnings.append("查询计划缺少标的，请补充股票名称（博通 / 英伟达 / 费城半导体 / 纳指）。")
            blocking = True

    elif intent == "compare":
        if len(symbols) < 2:
            warnings.append("比较计划需要至少两个标的，请补充第二个标的。")
            blocking = True

    # ── build steps ────────────────────────────────────────────────────────────
    steps: list[dict[str, Any]] = []

    if intent in ("query", "filter"):
        step: dict[str, Any] = {
            "type": "query",
            "symbols": symbols,
            "fields": fields,
            "source_command": text,
        }
        if start_date and end_date:
            step["start_date"] = start_date
            step["end_date"] = end_date
        else:
            step["lookback_days"] = lookback_days if lookback_days > 0 else DEFAULT_WINDOW
        steps.append(step)

    elif intent == "compare":
        step = {
            "type": "compare",
            "symbols": symbols,
            "fields": fields or ["Close"],
            "lookback_days": lookback_days if lookback_days > 0 else DEFAULT_WINDOW,
            "missing_second_symbol": len(symbols) < 2,
            "source_command": text,
        }
        steps.append(step)

    elif intent == "projection":
        target = symbols[0] if symbols else "AVGO"
        if not symbols:
            symbols = [target]
        steps.append({
            "type": "projection",
            "symbols": [target],
            "lookback_days": lookback_days if lookback_days > 0 else DEFAULT_WINDOW,
            "source_command": text,
        })

    # review / ai_explanation produce no executable steps in the router;
    # the command_bar handles them via the existing ParsedTask path.

    # ── build plan ─────────────────────────────────────────────────────────────
    effective_window = lookback_days if lookback_days > 0 else DEFAULT_WINDOW
    plan: dict[str, Any] = {
        "kind":           "intent_plan",
        "raw_text":       text,
        "supported":      bool(steps) and not blocking,
        "primary_intent": intent,
        "steps":          steps,
        "symbols":        symbols,
        "lookback_days":  effective_window,
        "fields":         fields,
        "ai_followups":   [],
        "warnings":       warnings,
        "planner":        "ai_primary",
        # Rich AI metadata — displayed in the "任务理解" UI section
        "user_goal":      str(schema.get("user_goal") or ""),
        "explanation":    str(schema.get("explanation") or ""),
        "ai_confidence":  schema.get("confidence"),
        "ai_schema":      schema,
    }
    if start_date and end_date:
        plan["start_date"] = start_date
        plan["end_date"]   = end_date

    # ── build ParsedTask ───────────────────────────────────────────────────────
    parsed = ParsedTask(
        task_type=task_type,
        symbols=symbols,
        fields=fields,
        window=effective_window,
        raw_text=text,
        parse_error=None,
        stat_request=None,
        ai_request=None,
    )

    return parsed, plan
