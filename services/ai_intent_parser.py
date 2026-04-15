"""services/ai_intent_parser.py

AI intent parser fallback for Command Center.

Rule parser (parse_command + plan_intent) runs first.  This module is called
only when the deterministic result is incomplete or ambiguous.  The AI outputs
structured JSON only — it never answers the user directly.

Trigger conditions:
  1. Planner could not identify intent (supported=False) AND rule parse also
     returned "unknown".
  2. OHLCV / all-data keywords appear in the text but no fields were resolved
     (e.g. "所有数据", "OHLCV", "全部数据").

Safe degradation:
  On any failure (missing API key, network error, non-JSON response, unsupported
  intent, malformed schema), the original rule parse result is returned
  unchanged and ai_used is set to False.
"""

from __future__ import annotations

import json
import warnings as _warnings
from copy import deepcopy
from typing import Any

from services.command_parser import DEFAULT_WINDOW, ParsedTask, parse_command
from services.openai_client import OpenAIClientError, generate_text


# ── constants ──────────────────────────────────────────────────────────────────

OHLCV_FIELDS = ["Open", "High", "Low", "Close", "Volume"]

# Text signals that the user wants all OHLCV columns
_OHLCV_SIGNALS = (
    "所有数据", "全部数据", "完整数据",
    "OHLCV", "ohlcv",
    "K线数据", "K线",
)

# Mapping from AI intent string → ParsedTask task_type
_INTENT_TO_TASK_TYPE: dict[str, str] = {
    "query":      "query_data",
    "compare":    "compare_data",
    "stats":      "query_data",    # plan step type handles routing
    "projection": "run_projection",
    "ai_explain": "ai_explanation",
}

_SUPPORTED_INTENTS = frozenset(_INTENT_TO_TASK_TYPE)
_SUPPORTED_OPERATIONS = frozenset({"today_vs_average"})
_SUPPORTED_CONFIDENCE = frozenset({"high", "medium", "low"})

_SYSTEM_PROMPT = """\
你是一个股票分析工具的意图解析器（intent parser）。

你的任务不是回答用户的问题，而是把用户的自然语言输入解析成一个结构化的 JSON 命令。

系统支持的 intent（意图）只有以下 5 种：
- query：查询某只股票的历史数据
- compare：对比两只股票的走势或字段
- stats：今日数据 vs 最近N天平均（today_vs_average）
- projection：推演/预测下一个交易日走势
- ai_explain：用 AI 解释某次推演或比较结果

字段说明：
- "所有数据"、"全部数据"、"完整数据"、"OHLCV"、"K线数据" 均指 \
["Open", "High", "Low", "Close", "Volume"]
- query 意图：如果用户没有明确指定字段（如"收盘价"、"成交量"），\
默认返回 ["Open", "High", "Low", "Close", "Volume"]，不要只返回 ["Close"]
- "今天 vs 最近N天平均..." 应优先解析为 stats，operation = "today_vs_average"
- "比较/强弱/走势" 通常是 compare
- "推演/明天怎么样/下一个交易日" 是 projection
- "用 AI 解释/总结..." 是 ai_explain

如果不确定，不要乱猜，应返回低置信度（confidence: "low"）和 ambiguity_reason。

输出必须是纯 JSON，不要输出任何解释文字或 markdown 格式。

输出结构：
{
  "intent": "query|compare|stats|projection|ai_explain",
  "symbols": ["AVGO"],
  "lookback_days": 20,
  "fields": ["Open", "High", "Low", "Close", "Volume"],
  "operation": "today_vs_average|null",
  "ai_followups": [],
  "confidence": "high|medium|low",
  "ambiguity_reason": null
}

已知标的映射：
- 博通 → AVGO
- 英伟达 → NVDA
- 费城半导体 / 费城 → SOXX
- 纳斯达克 / 纳指 → QQQ
"""


# ── trigger logic ──────────────────────────────────────────────────────────────

def _needs_ai_fallback(parsed: ParsedTask, plan: dict[str, Any], text: str) -> bool:
    """Return True when the rule parse result is incomplete and AI should be tried."""
    # Condition 1: planner could not identify intent AND rule parse also failed
    if not plan.get("supported") and parsed.task_type == "unknown":
        return True

    # Condition 2: OHLCV/all-data keywords present but no fields were resolved
    text_lower = text.lower()
    if any(sig.lower() in text_lower for sig in _OHLCV_SIGNALS) and not parsed.fields:
        return True

    return False


# ── OpenAI call ────────────────────────────────────────────────────────────────

def _call_ai_parser(text: str) -> dict[str, Any] | None:
    """Call OpenAI and return parsed intent JSON, or None on any failure."""
    try:
        raw = generate_text(
            input_text=text,
            instructions=_SYSTEM_PROMPT,
            timeout=20,
        )
    except OpenAIClientError as exc:
        _warnings.warn(f"[ai_intent_parser] OpenAI call failed: {exc}")
        return None
    except Exception as exc:
        _warnings.warn(f"[ai_intent_parser] Unexpected error calling OpenAI: {exc}")
        return None

    # Strip markdown code fences if the model wrapped the JSON
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = [ln for ln in cleaned.splitlines() if not ln.startswith("```")]
        cleaned = "\n".join(lines).strip()

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        _warnings.warn(f"[ai_intent_parser] Non-JSON response: {raw[:200]!r}")
        return None

    if not isinstance(result, dict):
        _warnings.warn("[ai_intent_parser] Response is not a JSON object")
        return None

    return _validate_ai_result(result)


def _string_list(value: Any, field_name: str) -> list[str] | None:
    """Return a normalized list[str], or None when the shape is unstable."""
    if not isinstance(value, list):
        _warnings.warn(f"[ai_intent_parser] {field_name} must be a list[str]")
        return None
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str):
            _warnings.warn(f"[ai_intent_parser] {field_name} contains non-string item")
            return None
        stripped = item.strip()
        if not stripped:
            _warnings.warn(f"[ai_intent_parser] {field_name} contains empty string")
            return None
        normalized.append(stripped)
    return normalized


def _validate_ai_result(result: dict[str, Any]) -> dict[str, Any] | None:
    """Validate model output before it is allowed to participate in merge."""
    if not result:
        _warnings.warn("[ai_intent_parser] Empty response object")
        return None

    intent = result.get("intent")
    if intent not in _SUPPORTED_INTENTS:
        _warnings.warn(f"[ai_intent_parser] Unsupported intent in response: {intent!r}")
        return None

    for required in ("symbols", "fields", "lookback_days"):
        if required not in result:
            _warnings.warn(f"[ai_intent_parser] Missing required field: {required}")
            return None

    symbols = _string_list(result.get("symbols"), "symbols")
    if symbols is None:
        return None
    fields = _string_list(result.get("fields"), "fields")
    if fields is None:
        return None

    lookback_days = result.get("lookback_days")
    if isinstance(lookback_days, bool) or not isinstance(lookback_days, int) or lookback_days <= 0:
        _warnings.warn("[ai_intent_parser] lookback_days must be an int > 0")
        return None

    operation = result.get("operation") if "operation" in result else None
    if operation is not None and operation not in _SUPPORTED_OPERATIONS:
        _warnings.warn(f"[ai_intent_parser] Unsupported operation: {operation!r}")
        return None
    if intent == "stats" and operation != "today_vs_average":
        _warnings.warn("[ai_intent_parser] stats intent requires operation=today_vs_average")
        return None
    if intent != "stats" and operation is not None:
        _warnings.warn("[ai_intent_parser] operation is only supported for stats intent")
        return None

    if "ai_followups" in result:
        ai_followups = _string_list(result.get("ai_followups"), "ai_followups")
        if ai_followups is None:
            return None
    else:
        ai_followups = []

    confidence = result.get("confidence") if "confidence" in result else None
    if confidence is not None and confidence not in _SUPPORTED_CONFIDENCE:
        _warnings.warn(f"[ai_intent_parser] Unsupported confidence: {confidence!r}")
        return None

    ambiguity_reason = result.get("ambiguity_reason") if "ambiguity_reason" in result else None
    if ambiguity_reason is not None and not isinstance(ambiguity_reason, str):
        _warnings.warn("[ai_intent_parser] ambiguity_reason must be str or null")
        return None

    if intent == "query" and (not symbols or not fields):
        _warnings.warn("[ai_intent_parser] query intent requires symbols and fields")
        return None
    if intent == "compare" and (len(symbols) < 2 or not fields):
        _warnings.warn("[ai_intent_parser] compare intent requires two symbols and fields")
        return None
    if intent == "stats" and (not symbols or not fields):
        _warnings.warn("[ai_intent_parser] stats intent requires symbols and fields")
        return None
    if intent == "projection" and not symbols:
        _warnings.warn("[ai_intent_parser] projection intent requires symbols")
        return None

    normalized = dict(result)
    normalized["intent"] = intent
    normalized["symbols"] = symbols
    normalized["fields"] = fields
    normalized["lookback_days"] = lookback_days
    normalized["operation"] = operation
    normalized["ai_followups"] = ai_followups
    if "confidence" in result:
        normalized["confidence"] = confidence
    if "ambiguity_reason" in result:
        normalized["ambiguity_reason"] = ambiguity_reason
    return normalized


# ── merge ──────────────────────────────────────────────────────────────────────

def _merge_ai_result(
    parsed: ParsedTask,
    plan: dict[str, Any],
    ai: dict[str, Any],
) -> tuple[ParsedTask, dict[str, Any]]:
    """Apply AI parser result onto rule-parsed structures.

    Prefers rule-parsed values when available; uses AI result as fallback.
    Returns new (parsed, plan) — originals are not mutated.
    """
    intent = ai.get("intent")
    if intent not in _INTENT_TO_TASK_TYPE:
        return parsed, plan

    ai_symbols: list[str] = [str(s) for s in (ai.get("symbols") or []) if s]
    ai_fields: list[str] = [str(f) for f in (ai.get("fields") or []) if f]
    ai_lookback: int = int(ai.get("lookback_days") or DEFAULT_WINDOW)
    ai_operation: str | None = ai.get("operation") or None

    # Prefer rule-parsed values; fall back to AI
    new_symbols = parsed.symbols or ai_symbols
    new_fields = ai_fields if ai_fields else parsed.fields
    new_window = parsed.window if parsed.window > 0 else ai_lookback

    new_parsed = ParsedTask(
        task_type=_INTENT_TO_TASK_TYPE[intent],
        symbols=new_symbols,
        fields=new_fields,
        window=new_window,
        raw_text=parsed.raw_text,
        parse_error=None,
        stat_request=parsed.stat_request,
        ai_request=parsed.ai_request,
    )

    new_plan = deepcopy(plan)

    if intent == "query":
        new_plan["primary_intent"] = "query"
        new_plan["fields"] = new_fields
        new_plan["symbols"] = new_symbols
        new_plan["supported"] = bool(new_symbols)
        query_steps = [s for s in new_plan.get("steps", []) if s.get("type") == "query"]
        if query_steps:
            for step in query_steps:
                step["fields"] = new_fields
                step["symbols"] = new_symbols
                step["lookback_days"] = new_window
        else:
            new_plan.setdefault("steps", []).insert(0, {
                "type": "query",
                "symbols": new_symbols,
                "fields": new_fields,
                "lookback_days": new_window,
                "source_command": parsed.raw_text,
            })

    elif intent == "stats":
        stat_field = new_fields[0] if new_fields else "Volume"
        new_plan["primary_intent"] = "stats"
        new_plan["fields"] = new_fields
        new_plan["supported"] = True
        stats_steps = [s for s in new_plan.get("steps", []) if s.get("type") == "stats"]
        if stats_steps:
            for step in stats_steps:
                if new_fields:
                    step["field"] = stat_field
                if ai_operation:
                    step["operation"] = ai_operation
        else:
            symbol = new_symbols[0] if new_symbols else "AVGO"
            new_plan.setdefault("steps", []).insert(0, {
                "type": "stats",
                "symbol": symbol,
                "field": stat_field,
                "lookback_days": new_window,
                "operation": ai_operation or "today_vs_average",
                "source_command": parsed.raw_text,
            })

    elif intent == "compare":
        new_plan["primary_intent"] = "compare"
        new_plan["symbols"] = new_symbols
        new_plan["fields"] = new_fields
        new_plan["supported"] = len(new_symbols) >= 2
        compare_steps = [s for s in new_plan.get("steps", []) if s.get("type") == "compare"]
        if compare_steps:
            for step in compare_steps:
                step["symbols"] = new_symbols
                if new_fields:
                    step["fields"] = new_fields
        else:
            new_plan["steps"] = [{
                "type": "compare",
                "symbols": new_symbols,
                "fields": new_fields or ["Close"],
                "lookback_days": new_window,
                "missing_second_symbol": len(new_symbols) < 2,
                "source_command": parsed.raw_text,
            }]

    elif intent == "projection":
        new_plan["primary_intent"] = "projection"
        new_plan["symbols"] = new_symbols
        new_plan["supported"] = True
        has_proj = any(s.get("type") == "projection" for s in new_plan.get("steps", []))
        if not has_proj:
            symbol = new_symbols[0] if new_symbols else "AVGO"
            new_plan.setdefault("steps", []).insert(0, {
                "type": "projection",
                "symbols": [symbol],
                "lookback_days": new_window,
                "source_command": parsed.raw_text,
            })

    elif intent == "ai_explain":
        new_plan["primary_intent"] = "ai_explain"
        new_plan["supported"] = True

    # Clear "unsupported" warnings that the AI result has resolved
    new_plan["warnings"] = [
        w for w in new_plan.get("warnings", [])
        if "暂未识别" not in w and "无法规划" not in w
    ]

    return new_parsed, new_plan


def _align_rule_plan_with_parsed(
    parsed: ParsedTask,
    plan: dict[str, Any],
) -> dict[str, Any]:
    """Keep rule-plan labels aligned with parser-only executable intents."""
    if parsed.task_type != "ai_explanation":
        return plan
    raw_text = parsed.raw_text or ""
    if "先" in raw_text or "再" in raw_text:
        return plan
    if plan.get("primary_intent") == "ai_explain":
        return plan

    new_plan = deepcopy(plan)
    new_plan["primary_intent"] = "ai_explain"
    return new_plan


# ── public API ─────────────────────────────────────────────────────────────────

def parse_with_ai_fallback(
    text: str,
    *,
    _plan_intent_fn: Any = None,
) -> tuple[ParsedTask, dict[str, Any], bool]:
    """Parse text with rule parser first, AI fallback second.

    Parameters
    ----------
    text : str
        Raw user input.
    _plan_intent_fn : callable, optional
        Injected plan_intent function for testing.

    Returns
    -------
    tuple of (parsed, plan, ai_used)
        parsed   — ParsedTask (updated by AI when ai_used is True)
        plan     — intent plan dict (updated by AI when ai_used is True;
                   plan["planner"] == "rule+ai_fallback" when AI was applied)
        ai_used  — True when AI fallback was called and changed the result
    """
    from services.intent_planner import plan_intent as _default_plan_intent

    _plan_fn = _plan_intent_fn or _default_plan_intent

    parsed = parse_command(text)
    plan = _align_rule_plan_with_parsed(parsed, _plan_fn(text))

    if not _needs_ai_fallback(parsed, plan, text):
        return parsed, plan, False

    ai_result = _call_ai_parser(text)
    if ai_result is None:
        # Safe degradation — return original rule parse unchanged
        return parsed, plan, False

    new_parsed, new_plan = _merge_ai_result(parsed, plan, ai_result)
    new_plan["planner"] = "rule+ai_fallback"

    return new_parsed, new_plan, True
