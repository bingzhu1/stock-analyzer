from __future__ import annotations

import re
from dataclasses import dataclass, field


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
# Extended with natural-language query triggers:
#   只看  — "只看博通最近20天"
#   并排  — "把博通、英伟达、纳指最近20天数据并排"
#   查看  — "查看英伟达最近20天数据"
_QUERY_KW     = ("调出", "查询", "显示", "看看", "只看", "并排", "查看")

VALID_TASK_TYPES = frozenset({
    "query_data",
    "compare_data",
    "run_projection",
    "run_review",
    "ai_explanation",
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

    stat_request: dict | None = None
    """
    Optional supplementary statistics request parsed from the command.

    Populated for commands like "一致里博通高位、中位、低位各多少天".
    Possible shapes:
      {"type": "distribution_by_label", "symbol": "AVGO", "field": "PosLabel"}
      {"type": "match_rate"}
      {"type": "matched_count"}
      {"type": "mismatched_count"}
    None when no supplementary stat was requested.
    """

    ai_request: dict | None = None
    """
    Optional AI explanation request parsed from commands like:
      {"focus": "projection"}
      {"focus": "direction", "direction": "偏空"}
      {"focus": "compare"}
      {"focus": "risk"}
    None when the command is not an AI explanation request.
    """


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
    """Return the time-window as an integer number of days.

    Priority order:
    1. Fixed phrase table (最近20天, 明天, 下一个交易日, etc.)
    2. Regex: 最近N天  (any N)
    3. Regex: bare N天 (N >= 5, to avoid noise from small ordinals)
    4. DEFAULT_WINDOW
    """
    for pattern, days in _WINDOW_PATTERNS:
        if pattern in text:
            return days
    # Fallback 1: "最近N天" with any N
    m = re.search(r"最近(\d+)天", text)
    if m:
        n = int(m.group(1))
        return n if n > 0 else DEFAULT_WINDOW
    # Fallback 2: bare "N天" without "最近" (e.g. "根据博通20天数据")
    # Require N >= 5 to avoid matching noise like "第1天".
    m = re.search(r"(\d+)天", text)
    if m:
        n = int(m.group(1))
        if n >= 5:
            return n
    return DEFAULT_WINDOW


def _extract_ai_request(text: str) -> dict | None:
    """
    Detect optional AI explanation intents.

    This never asks AI to execute query/compare/projection; it only routes to
    explanation over already stored structured results.
    """
    lower = text.lower()
    if "ai" not in lower:
        return None
    if "解释" not in text and "总结" not in text:
        return None

    if "比较" in text or "对比" in text:
        return {"focus": "compare"}
    if "风险" in text:
        return {"focus": "risk"}
    for direction in ("偏多", "偏空", "中性"):
        if direction in text:
            return {"focus": "direction", "direction": direction}
    if "推演" in text or "预测" in text:
        return {"focus": "projection"}
    return {"focus": "projection"}


def _detect_task_type(text: str) -> str:
    """Identify the task type from keyword presence (priority order)."""
    if _extract_ai_request(text):
        return "ai_explanation"
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


def _extract_stat_request(text: str, symbols: list[str]) -> dict | None:
    """
    Extract an optional supplementary statistics request.

    Detects patterns like:
    - "高位、中位、低位各多少天" → distribution_by_label (PosLabel)
    - "一致率"                  → match_rate
    - "不一致天数"              → mismatched_count
    - "一致天数"                → matched_count

    The symbol used for distribution is the one whose Chinese name appears
    immediately before position-level labels (e.g. "博通高位" → AVGO).
    Falls back to the first symbol in the extracted list when ambiguous.
    """
    # Distribution-by-label: "各多少天" with position labels
    if "各多少天" in text:
        # Identify the symbol that appears closest (and most recently) before
        # the first position label ("高位"/"中位"/"低位").  This handles sentences
        # like "一致里博通高位、中位、低位各多少天" where the symbol to group by
        # immediately precedes the labels, even if another symbol appears earlier.
        pos_label_positions = [
            text.find(lbl) for lbl in ("高位", "中位", "低位")
            if text.find(lbl) >= 0
        ]
        # Upper bound: search for symbols before the first position label
        ceiling = min(pos_label_positions) if pos_label_positions else len(text)

        best_sym: str | None = None
        best_pos: int = -1
        for cn in sorted(SYMBOL_MAP, key=len, reverse=True):
            sym = SYMBOL_MAP[cn]
            if sym not in symbols:
                continue
            # rfind: last occurrence of cn strictly before the ceiling index
            idx = text.rfind(cn, 0, ceiling)
            if idx >= 0 and idx > best_pos:
                best_pos = idx
                best_sym = sym

        dist_sym: str | None = best_sym if best_sym is not None else (symbols[0] if symbols else None)

        return {
            "type":   "distribution_by_label",
            "symbol": dist_sym,
            "field":  "PosLabel",
        }

    if "一致率" in text:
        return {"type": "match_rate"}

    if "不一致天数" in text:
        return {"type": "mismatched_count"}

    if "一致天数" in text:
        return {"type": "matched_count"}

    return None


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
    # 推演任务锁定20日窗口；-1（明天/下一个交易日）保留原义，其余非标准天数强制归20
    if task_type == "run_projection" and window > 0:
        window = DEFAULT_WINDOW
    stat_req  = _extract_stat_request(text, symbols)
    ai_req    = _extract_ai_request(text) if task_type == "ai_explanation" else None

    error: str | None = None
    if task_type == "unknown":
        error = (
            "无法识别指令类型，请使用以下关键词开头："
            "调出、只看、并排、比较、对比、推演、预测、复盘，或用 AI 解释/总结。"
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
        stat_request=stat_req,
        ai_request=ai_req,
    )
