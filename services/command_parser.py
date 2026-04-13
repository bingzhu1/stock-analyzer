from __future__ import annotations

import re
from dataclasses import dataclass


# ─────────────────────────────────────────────────────────────────────────────
# Symbol mapping  (Chinese name → canonical ticker)
# ─────────────────────────────────────────────────────────────────────────────

SYMBOL_MAP: dict[str, str] = {
    "博通":       "AVGO",
    "英伟达":     "NVDA",
    "费城半导体": "SOXX",   # must come before 费城
    "费城":       "SOXX",
    "纳斯达克":   "QQQ",
    "纳指":       "QQQ",
    "QQQ":        "QQQ",
    "AVGO":       "AVGO",
    "NVDA":       "NVDA",
    "SOXX":       "SOXX",
}

# ─────────────────────────────────────────────────────────────────────────────
# Field mapping  (Chinese phrase → column name)
# ─────────────────────────────────────────────────────────────────────────────

FIELD_MAP: dict[str, str] = {
    "位置标签":   "PosLabel",   # must come before 位置
    "位置":       "Pos30",
    "开盘价":     "Open",
    "最高价":     "High",
    "最低价":     "Low",
    "收盘价":     "Close",
    "收盘方向":   "Close",
    "成交量":     "Volume",
    "动能":       "StageLabel",
    "5日涨跌幅":  "Ret5",
    "5日涨跌":    "Ret5",
}

# ─────────────────────────────────────────────────────────────────────────────
# Time-window mapping  (Chinese phrase → days; -1 = next trading day)
# ─────────────────────────────────────────────────────────────────────────────

_WINDOW_PATTERNS: list[tuple[str, int]] = [
    ("最近60天", 60),
    ("最近30天", 30),
    ("最近20天", 20),
    ("最近15天", 15),
    ("明天",          -1),
    ("下一个交易日",   -1),
]

DEFAULT_WINDOW = 20

# ─────────────────────────────────────────────────────────────────────────────
# Task-type keyword sets
# ─────────────────────────────────────────────────────────────────────────────

_REVIEW_KW    = ("复盘",)
_PROJECT_KW   = ("推演", "预测")
_COMPARE_KW   = ("比较", "对比")
_QUERY_KW     = ("调出", "查询", "显示", "看看")

VALID_TASK_TYPES = frozenset({
    "query_data",
    "compare_data",
    "run_projection",
    "run_review",
    "unknown",
})


# ─────────────────────────────────────────────────────────────────────────────
# Result dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ParsedTask:
    """Structured result produced by parse_command()."""

    task_type: str
    """One of: query_data | compare_data | run_projection | run_review | unknown"""

    symbols: list[str]
    """Resolved canonical ticker symbols, e.g. ['AVGO', 'NVDA']."""

    fields: list[str]
    """Resolved column names, e.g. ['Close', 'Volume']."""

    window: int
    """Number of days to look back; -1 means 'next trading day'."""

    raw_text: str
    """The original user input, stripped."""

    parse_error: str | None = None
    """Human-readable Chinese error message; None when parsing succeeded."""


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _extract_symbols(text: str) -> list[str]:
    """Return canonical tickers found in *text*, longest-key-first.

    Matched substrings are consumed so shorter aliases (e.g. 费城 after
    费城半导体) do not fire a second time.
    """
    found: list[str] = []
    remaining = text
    for cn in sorted(SYMBOL_MAP, key=len, reverse=True):
        if cn in remaining:
            sym = SYMBOL_MAP[cn]
            if sym not in found:
                found.append(sym)
            remaining = remaining.replace(cn, " " * len(cn))
    return found


def _extract_fields(text: str) -> list[str]:
    """Return canonical field names found in *text*, longest-key-first.

    Matched substrings are consumed so shorter substrings (e.g. 位置 after
    位置标签) do not fire a second time.
    """
    found: list[str] = []
    remaining = text
    for cn in sorted(FIELD_MAP, key=len, reverse=True):
        if cn in remaining:
            col = FIELD_MAP[cn]
            if col not in found:
                found.append(col)
            remaining = remaining.replace(cn, " " * len(cn))
    return found


def _extract_window(text: str) -> int:
    """Return the time-window as an integer number of days."""
    for pattern, days in _WINDOW_PATTERNS:
        if pattern in text:
            return days
    # Fallback: match "最近N天" with any integer N
    m = re.search(r"最近(\d+)天", text)
    if m:
        n = int(m.group(1))
        return n if n > 0 else DEFAULT_WINDOW
    return DEFAULT_WINDOW


def _detect_task_type(text: str) -> str:
    """Identify the task type from keyword presence (priority order)."""
    for kw in _REVIEW_KW:
        if kw in text:
            return "run_review"
    for kw in _PROJECT_KW:
        if kw in text:
            return "run_projection"
    for kw in _COMPARE_KW:
        if kw in text:
            return "compare_data"
    for kw in _QUERY_KW:
        if kw in text:
            return "query_data"
    return "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def parse_command(text: str) -> ParsedTask:
    """
    Parse a Chinese natural-language command into a structured ParsedTask.

    This function never raises.  If the input is unrecognisable,
    ``parse_error`` on the returned ParsedTask will contain a friendly
    Chinese message and ``task_type`` will be ``'unknown'``.
    """
    text = (text or "").strip()

    if not text:
        return ParsedTask(
            task_type="unknown",
            symbols=[],
            fields=[],
            window=DEFAULT_WINDOW,
            raw_text=text,
            parse_error="指令为空，请输入内容后再解析。",
        )

    task_type = _detect_task_type(text)
    symbols   = _extract_symbols(text)
    fields    = _extract_fields(text)
    window    = _extract_window(text)

    error: str | None = None
    if task_type == "unknown":
        error = (
            "无法识别指令类型，请使用以下关键词开头："
            "调出、比较、对比、推演、预测、复盘。"
        )
    elif task_type in ("query_data", "compare_data") and not symbols:
        error = (
            "未识别到股票名称，请使用：博通、英伟达、费城半导体、纳指。"
        )

    return ParsedTask(
        task_type=task_type,
        symbols=symbols,
        fields=fields,
        window=window,
        raw_text=text,
        parse_error=error,
    )
