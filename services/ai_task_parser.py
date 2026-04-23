"""services/ai_task_parser.py

Primary AI task parser — the main entry point for understanding user intent.

Called FIRST for every Command Center input. The rule-based parser is only
used as a fallback when this module is unavailable or returns None.

Today's date is injected into the system prompt so the model can infer
missing years from bare month-day expressions (e.g. "2月5号" → "2026-02-05")
and report its confidence in that inference.

Returned schema (all fields present; conditional fields may be null/omitted)
──────────────────────────────────────────────────────────────────────────────
{
  "intent":   "query|compare|filter|projection|review|ai_explanation",
  "symbols":  ["AVGO"],
  "time_range": {
    "type":         "absolute|relative|next_trading_day",
    "start_date":   "YYYY-MM-DD",   # absolute only
    "end_date":     "YYYY-MM-DD",   # absolute only
    "lookback_days": 20,            # relative only
    "inferred":     false,          # true when year was inferred from context
    "confidence":   0.95,           # 0.0–1.0, confidence in this time range
    "raw_text":     "2月5号至2月25号"
  },
  "fields":      ["Open","High","Low","Close","Volume"],
  "transforms":  [],
  "constraints": [],
  "user_goal":   "用中文描述用户的真实目标",
  "explanation": "用中文简要解释解析结果",
  "confidence":  0.9
}
"""

from __future__ import annotations

import json
import warnings as _warnings
from datetime import date
from typing import Any

from services.openai_client import OpenAIClientError, generate_text


# ── constants ──────────────────────────────────────────────────────────────────

SUPPORTED_INTENTS: frozenset[str] = frozenset({
    "query", "compare", "filter", "projection", "review", "ai_explanation",
})

_REQUIRED_TOP_KEYS = ("intent", "symbols", "time_range", "fields", "confidence")

_TIME_RANGE_TYPES = frozenset({"absolute", "relative", "next_trading_day"})


# ── system prompt ──────────────────────────────────────────────────────────────

_SYMBOL_MAP_DOC = """\
Symbol mapping (Chinese → canonical ticker):
  博通 → AVGO
  英伟达 → NVDA
  费城半导体, 费城 → SOXX
  纳斯达克, 纳指 → QQQ"""

_FIELD_MAP_DOC = """\
Field mapping (Chinese → canonical column name):
  开盘价 → Open | 最高价 → High | 最低价 → Low | 收盘价 → Close | 成交量 → Volume
  位置 → Pos30 | 位置标签 → PosLabel | 动能 → StageLabel
  5日涨跌幅, 5日涨跌 → Ret5
  "所有数据","全部数据","完整数据","OHLCV","K线" → ["Open","High","Low","Close","Volume"]
  If the user does not specify fields, default to ["Open","High","Low","Close","Volume"]."""

_SCHEMA_DOC = """\
Output ONLY raw JSON — no markdown fences, no explanation, no leading text.

{
  "intent": "query|compare|filter|projection|review|ai_explanation",
  "symbols": ["AVGO"],
  "time_range": {
    "type": "absolute|relative|next_trading_day",
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD",
    "lookback_days": 20,
    "inferred": false,
    "confidence": 0.95,
    "raw_text": "原始时间表达"
  },
  "fields": ["Open","High","Low","Close","Volume"],
  "transforms": [],
  "constraints": [],
  "user_goal": "一句话描述用户的真实目标",
  "explanation": "一句话解释你的解析结果",
  "confidence": 0.9
}

Rules for time_range:
  • type="absolute": user gave or implied a specific date range
    — start_date and end_date must be YYYY-MM-DD; omit lookback_days
  • type="relative": user said "最近N天" or "近N天" or similar
    — set lookback_days; omit start_date / end_date
  • type="next_trading_day": user said 明天/下一个交易日/推演
    — omit start_date, end_date, lookback_days
  • inferred: true when you deduced a year that was NOT explicit in the input
  • confidence (in time_range): 0.0–1.0 — how certain you are of the inferred year

Year inference rules (apply when year is missing):
  1. Identify the current year from today's date.
  2. If the month-day is clearly in the past within this year → use current year, inferred=true, confidence ≥ 0.85.
  3. If the month-day is 2–5 months in the past → current year is most likely; confidence 0.80–0.90.
  4. If ambiguous (e.g. December when today is January) → use current year but lower confidence (0.65–0.75).
  5. If very uncertain → confidence < 0.60 (the validator will block and ask the user to clarify).
  Never guess a year with confidence below 0.50."""


def _build_system_prompt(today: str) -> str:
    return f"""\
You are the intent parser for a stock analysis tool. Today's date is {today}.

Your ONLY job: parse the user's natural-language input into a strict JSON schema.
You do NOT compute results, generate prices, or make trading recommendations.
You do NOT need to verify data — just understand what the user wants.

Supported intents:
  query        — retrieve historical OHLCV data for one or more stocks
  compare      — compare two or more stocks on one or more fields
  filter       — filter stock rows by a numeric or label condition
  projection   — plan a next-trading-day direction analysis (rule-based system executes)
  review       — review recent trading action or performance
  ai_explanation — explain or summarize a previous result from the system

{_SYMBOL_MAP_DOC}

{_FIELD_MAP_DOC}

{_SCHEMA_DOC}"""


# ── internal helpers ───────────────────────────────────────────────────────────

def _strip_fences(raw: str) -> str:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = [ln for ln in cleaned.splitlines() if not ln.startswith("```")]
        cleaned = "\n".join(lines).strip()
    return cleaned


def _validate_schema(result: dict[str, Any]) -> dict[str, Any] | None:
    """Minimal structural validation — full semantic validation is in plan_normalizer."""
    if not isinstance(result, dict):
        _warnings.warn("[ai_task_parser] response is not a JSON object")
        return None

    intent = result.get("intent")
    if intent not in SUPPORTED_INTENTS:
        _warnings.warn(f"[ai_task_parser] unsupported intent: {intent!r}")
        return None

    symbols = result.get("symbols")
    if not isinstance(symbols, list):
        _warnings.warn("[ai_task_parser] symbols must be a list")
        return None

    time_range = result.get("time_range")
    if not isinstance(time_range, dict):
        _warnings.warn("[ai_task_parser] time_range must be a dict")
        return None

    tr_type = time_range.get("type")
    if tr_type not in _TIME_RANGE_TYPES:
        _warnings.warn(f"[ai_task_parser] unknown time_range.type: {tr_type!r}")
        return None

    if not isinstance(result.get("fields"), list):
        _warnings.warn("[ai_task_parser] fields must be a list")
        return None

    conf = result.get("confidence")
    if conf is not None and not isinstance(conf, (int, float)):
        _warnings.warn("[ai_task_parser] confidence must be numeric")
        return None

    return result


# ── public API ─────────────────────────────────────────────────────────────────

def parse_task(
    text: str,
    *,
    _today: str | None = None,
    _generate: Any = None,
) -> dict[str, Any] | None:
    """
    Call the AI to parse *text* into a structured task schema.

    Parameters
    ----------
    text : str
        Raw user input.
    _today : str | None
        Override today's date (YYYY-MM-DD) for testing.
    _generate : callable | None
        Injected generate_text function for testing.

    Returns
    -------
    dict
        Validated schema dict on success.
    None
        On any failure: missing API key, network error, invalid JSON, bad schema.
        Callers must fall back to rule-based parsing when None is returned.
    """
    today = _today or date.today().isoformat()
    _gen = _generate or generate_text

    try:
        raw = _gen(
            input_text=text,
            instructions=_build_system_prompt(today),
            timeout=25,
        )
    except OpenAIClientError as exc:
        _warnings.warn(f"[ai_task_parser] OpenAI call failed: {exc}")
        return None
    except Exception as exc:
        _warnings.warn(f"[ai_task_parser] unexpected error: {exc}")
        return None

    cleaned = _strip_fences(raw)
    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        _warnings.warn(f"[ai_task_parser] non-JSON response: {raw[:200]!r}")
        return None

    return _validate_schema(result)
