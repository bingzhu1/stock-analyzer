"""Rule-based free-text intent planner for Command Center MVP."""

from __future__ import annotations

import os
from typing import Any

from services.command_parser import DEFAULT_WINDOW, FIELD_MAP, SYMBOL_MAP, parse_command


_PEER_SYMBOLS = ["NVDA", "SOXX", "QQQ"]


def _symbols_from_text(text: str) -> list[str]:
    parsed = parse_command(text)
    if parsed.symbols:
        return parsed.symbols
    found: list[str] = []
    remaining = text
    for label in sorted(SYMBOL_MAP, key=len, reverse=True):
        if label in remaining:
            sym = SYMBOL_MAP[label]
            if sym not in found:
                found.append(sym)
            remaining = remaining.replace(label, " " * len(label))
    return found


def _fields_from_text(text: str) -> list[str]:
    parsed = parse_command(text)
    if parsed.fields:
        return parsed.fields
    found: list[str] = []
    remaining = text
    for label in sorted(FIELD_MAP, key=len, reverse=True):
        if label in remaining:
            field = FIELD_MAP[label]
            if field not in found:
                found.append(field)
            remaining = remaining.replace(label, " " * len(label))
    return found


def _lookback_from_text(text: str) -> int:
    parsed = parse_command(text)
    return parsed.window if parsed.window > 0 else DEFAULT_WINDOW


def _has_ai_available() -> bool:
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def _ai_followup(kind: str) -> dict[str, Any]:
    return {
        "type": kind,
        "available": _has_ai_available(),
        "requires_openai_api_key": not _has_ai_available(),
    }


def _step(step_type: str, **kwargs: Any) -> dict[str, Any]:
    data = {"type": step_type}
    data.update(kwargs)
    return data


def _is_stats_today_vs_average(text: str) -> bool:
    """Return True when the text expresses a 'today vs recent-N-day average' intent.

    Triggers only when *both* conditions hold:
      - "今天" is present (today reference)
      - at least one average-signal word is present (均量, 均值, 平均, 均线)

    This prevents "今天成交量" from matching and lets "明天怎么样" remain a
    projection intent.
    """
    if "今天" not in text:
        return False
    avg_signals = ("均量", "均值", "平均", "均线")
    return any(s in text for s in avg_signals)


def plan_intent(text: str) -> dict[str, Any]:
    """
    Build a small rule-based plan from free-form Chinese text.

    The planner does not execute tools. It only describes which existing
    command-center capabilities should run next.

    Priority order:
      1. stats (today_vs_average) — must be checked before compare/projection
         because inputs like "今天…平均…怎么样" contain projection signals too
      2. query
      3. compare
      4. projection
      5. unsupported
    """
    raw_text = (text or "").strip()
    if not raw_text:
        return {
            "kind": "intent_plan",
            "raw_text": raw_text,
            "supported": False,
            "primary_intent": "unsupported",
            "steps": [],
            "symbols": [],
            "lookback_days": DEFAULT_WINDOW,
            "fields": [],
            "ai_followups": [],
            "warnings": ["输入为空，暂无法规划。"],
        }

    parsed = parse_command(raw_text)
    symbols = _symbols_from_text(raw_text)
    fields = _fields_from_text(raw_text)
    lookback_days = _lookback_from_text(raw_text)
    text_lower = raw_text.lower()

    wants_ai = "ai" in text_lower or "解释" in raw_text or "总结" in raw_text
    wants_risk_ai = wants_ai and "风险" in raw_text

    # Stats check must run first — guards against misclassification.
    wants_stats = _is_stats_today_vs_average(raw_text)

    # Compare/query/projection are mutually exclusive with stats to prevent
    # inputs like "今天…平均…怎么样" from falling into the projection branch.
    wants_compare = not wants_stats and (
        parsed.task_type == "compare_data"
        or "比较" in raw_text
        or "对比" in raw_text
        or "强弱" in raw_text
    )
    wants_query = not wants_stats and (
        parsed.task_type == "query_data"
        or "只看" in raw_text
        or "查看" in raw_text
    )
    wants_projection = not wants_stats and (
        parsed.task_type == "run_projection"
        or "推演" in raw_text
        or "预测" in raw_text
        or "明天" in raw_text
        or "下一个交易日" in raw_text
        or "怎么看" in raw_text
        or "怎么样" in raw_text
    )

    steps: list[dict[str, Any]] = []
    ai_followups: list[dict[str, Any]] = []
    warnings: list[str] = []
    blocking = False

    # ── 1. stats ──────────────────────────────────────────────────────────────
    if wants_stats:
        target = symbols[0] if symbols else "AVGO"
        if not symbols:
            symbols = [target]
        stat_field = fields[0] if fields else "Volume"
        steps.append(
            _step(
                "stats",
                symbol=target,
                field=stat_field,
                lookback_days=lookback_days,
                operation="today_vs_average",
                source_command=raw_text,
            )
        )
        primary = "stats"

    # ── 2. query ──────────────────────────────────────────────────────────────
    elif wants_query and not wants_compare and not wants_projection:
        if not symbols:
            warnings.append("查询计划缺少标的，请补充股票名称。")
            blocking = True
        steps.append(
            _step(
                "query",
                symbols=symbols,
                fields=fields or ["Close"],
                lookback_days=lookback_days,
                source_command=raw_text,
            )
        )
        primary = "query"

    # ── 3. compare ────────────────────────────────────────────────────────────
    elif wants_compare:
        compare_symbols = symbols[:]
        if len(compare_symbols) == 1:
            blocking = True
            warnings.append("比较指令只识别到一个标的，请补充第二个标的。")
        elif len(compare_symbols) == 0:
            blocking = True
            warnings.append("比较计划缺少两个标的，请补充股票名称。")
        steps.append(
            _step(
                "compare",
                symbols=compare_symbols,
                fields=fields or ["Close"],
                lookback_days=lookback_days,
                missing_second_symbol=(len(compare_symbols) < 2),
                source_command=raw_text,
            )
        )
        if wants_projection:
            target = symbols[0] if symbols else "AVGO"
            steps.append(
                _step(
                    "projection",
                    symbols=[target],
                    lookback_days=lookback_days,
                    source_command=raw_text,
                )
            )
        if wants_ai:
            ai_followups.append(_ai_followup("ai_explain_compare"))
            if wants_projection:
                ai_followups.append(_ai_followup("ai_explain_projection"))
        primary = "compare"

    # ── 4. projection ─────────────────────────────────────────────────────────
    elif wants_projection:
        target = symbols[0] if symbols else "AVGO"
        if not symbols:
            warnings.append("未识别到标的，默认按 AVGO 规划推演。")
            symbols = [target]
        steps.append(
            _step(
                "projection",
                symbols=[target],
                lookback_days=lookback_days,
                source_command=raw_text,
            )
        )
        if "看看" in raw_text or "怎么样" in raw_text:
            peer_symbols = [sym for sym in _PEER_SYMBOLS if sym != target]
            steps.append(
                _step(
                    "compare",
                    symbols=[target] + peer_symbols[:2],
                    fields=["Close"],
                    lookback_days=lookback_days,
                    optional=True,
                    reason="补充同业强弱背景。",
                )
            )
        if wants_risk_ai:
            ai_followups.append(_ai_followup("ai_explain_risk"))
        elif wants_ai:
            ai_followups.append(_ai_followup("ai_explain_projection"))
        primary = "projection"

    # ── 5. unsupported ────────────────────────────────────────────────────────
    else:
        return {
            "kind": "intent_plan",
            "raw_text": raw_text,
            "supported": False,
            "primary_intent": "unsupported",
            "steps": [],
            "symbols": symbols,
            "lookback_days": lookback_days,
            "fields": fields,
            "ai_followups": [],
            "warnings": ["暂未识别到 query / compare / projection / stats 计划。"],
        }

    return {
        "kind": "intent_plan",
        "raw_text": raw_text,
        "supported": bool(steps) and not blocking,
        "primary_intent": primary,
        "steps": steps,
        "symbols": symbols,
        "lookback_days": lookback_days,
        "fields": fields,
        "ai_followups": ai_followups,
        "warnings": warnings,
    }
