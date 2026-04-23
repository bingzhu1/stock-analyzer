"""services/date_range_parser.py

Extract absolute date ranges from Chinese and ISO/slash-notation text.

Supported formats
-----------------
  2026年1月15日至2月9日          (end year inferred from start)
  2026年1月15日到2026年2月9日    (both years explicit)
  2026-01-15 至 2026-02-09      (ISO with Chinese separator)
  2026/1/15 - 2026/2/9          (slash with ASCII dash)

Partial-signal detection
------------------------
``has_partial_date_signals(text)`` returns True when the text contains
date-like tokens (年月日 / YYYY-MM-DD) together with a range separator
(至/到) but ``parse_date_range`` could not build a complete range.  Callers
use this to fail loudly rather than silently defaulting to a relative window.
"""

from __future__ import annotations

import re


# ── compiled patterns ──────────────────────────────────────────────────────────

# 2026年1月15日到2026年2月9日  (both years explicit; 号 is colloquial for 日)
_RE_CHINESE_BOTH = re.compile(
    r"(\d{4})年(\d{1,2})月(\d{1,2})[日号]\s*[至到]\s*(\d{4})年(\d{1,2})月(\d{1,2})[日号]"
)

# 2026年1月15日至2月9日  (end omits year → same year as start)
_RE_CHINESE_SHARED_YEAR = re.compile(
    r"(\d{4})年(\d{1,2})月(\d{1,2})[日号]\s*[至到]\s*(\d{1,2})月(\d{1,2})[日号]"
)

# 2026-01-15 至/到/- 2026-02-09  or  2026/1/15 - 2026/2/9
_RE_ISO = re.compile(
    r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})"
    r"\s*[至到\-~]\s*"
    r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})"
)

# Detects any date-like fragment (for partial-signal check)
_RE_DATE_FRAGMENT = re.compile(
    r"\d{4}年\d{1,2}月"          # 2026年1月…
    r"|\d{1,2}月\d{1,2}[日号]"   # 1月15日 or 1月15号 (号 is colloquial for 日)
    r"|\d{4}[-/]\d{1,2}[-/]\d{1,2}"  # 2026-01-15 or 2026/1/15
)


# ── helpers ────────────────────────────────────────────────────────────────────

def _fmt(year: int, month: int, day: int) -> str:
    return f"{year:04d}-{month:02d}-{day:02d}"


# ── public API ─────────────────────────────────────────────────────────────────

def parse_date_range(text: str) -> tuple[str, str] | None:
    """
    Return ``(start_date, end_date)`` as ``YYYY-MM-DD`` strings, or ``None``
    when no complete date range is found.

    Pattern priority:
      1. Chinese with both years explicit
      2. Chinese with shared start year
      3. ISO / slash notation
    """
    m = _RE_CHINESE_BOTH.search(text)
    if m:
        y1, mo1, d1, y2, mo2, d2 = (int(g) for g in m.groups())
        return _fmt(y1, mo1, d1), _fmt(y2, mo2, d2)

    m = _RE_CHINESE_SHARED_YEAR.search(text)
    if m:
        y1, mo1, d1, mo2, d2 = (int(g) for g in m.groups())
        return _fmt(y1, mo1, d1), _fmt(y1, mo2, d2)

    m = _RE_ISO.search(text)
    if m:
        y1, mo1, d1, y2, mo2, d2 = (int(g) for g in m.groups())
        return _fmt(y1, mo1, d1), _fmt(y2, mo2, d2)

    return None


def has_partial_date_signals(text: str) -> bool:
    """
    Return ``True`` when the text has date-like tokens together with a range
    separator (至/到) but ``parse_date_range`` would return ``None``.

    Used to trigger a "fail loudly" warning instead of silently falling back
    to a relative window.
    """
    if not _RE_DATE_FRAGMENT.search(text):
        return False
    return "至" in text or "到" in text
