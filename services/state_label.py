"""
services/state_label.py

Unified five-state label function for AVGO daily close returns.

States (mutually exclusive, collectively exhaustive):
  大涨  >=  +2.0 %
  小涨  +0.5 % <= pct <  +2.0 %
  震荡  -0.5 % <  pct <  +0.5 %
  小跌  -2.0 % <  pct <= -0.5 %
  大跌  <= -2.0 %

Input unit: percentage points  (e.g. pass 2.0 for +2 %, -0.5 for -0.5 %).
Do not pass ratios here directly.

Ratio sources in this repo include:
  - outcome_capture.actual_close_change  (0.02 means +2%)
  - scanner.C_move                       (0.02 means +2%)

Convert them first with ratio_to_pct(...) or call label_state_from_ratio(...).
"""

from __future__ import annotations

import math

# Public constants — single source of truth for all thresholds
BIG_UP_THRESHOLD   =  2.0   # >=  this → 大涨
SMALL_UP_THRESHOLD =  0.5   # >=  this (and < BIG_UP_THRESHOLD)   → 小涨
SMALL_DN_THRESHOLD = -0.5   # <=  this (and > BIG_DN_THRESHOLD)   → 小跌
BIG_DN_THRESHOLD   = -2.0   # <=  this → 大跌

# All valid state labels in order from most bullish to most bearish
ALL_STATES: tuple[str, ...] = ("大涨", "小涨", "震荡", "小跌", "大跌")


def ratio_to_pct(return_ratio: float) -> float:
    """Convert a fractional return ratio into percentage points.

    Examples
    --------
    0.02   ->  2.0
    -0.005 -> -0.5
    """
    if return_ratio is None:
        raise TypeError("return_ratio must be a number, got None")
    if not isinstance(return_ratio, (int, float)):
        raise TypeError(f"return_ratio must be int or float, got {type(return_ratio).__name__!r}")
    ratio = float(return_ratio)
    if math.isnan(ratio) or math.isinf(ratio):
        raise ValueError(f"return_ratio must be finite, got {ratio!r}")
    return ratio * 100.0


def label_state(return_pct: float) -> str:
    """Classify a daily close return into one of five canonical states.

    Parameters
    ----------
    return_pct : float
        Close-over-prev-close return in **percentage points**.
        Examples: 2.1 → "大涨",  0.5 → "小涨",  0.0 → "震荡",
                 -0.5 → "小跌", -3.0 → "大跌".

    Returns
    -------
    str
        One of: "大涨" / "小涨" / "震荡" / "小跌" / "大跌".

    Raises
    ------
    TypeError   if return_pct is None or not numeric.
    ValueError  if return_pct is NaN or Inf.

    Boundary rules (exact thresholds, no rounding applied):
        pct >= +2.0             → 大涨
        +0.5 <= pct < +2.0     → 小涨
        -0.5 <  pct < +0.5     → 震荡
        -2.0 <  pct <= -0.5    → 小跌
        pct <= -2.0             → 大跌
    """
    if return_pct is None:
        raise TypeError("return_pct must be a number, got None")
    if not isinstance(return_pct, (int, float)):
        raise TypeError(f"return_pct must be int or float, got {type(return_pct).__name__!r}")
    pct = float(return_pct)
    if math.isnan(pct) or math.isinf(pct):
        raise ValueError(f"return_pct must be finite, got {pct!r}")

    if pct >= BIG_UP_THRESHOLD:
        return "大涨"
    if pct >= SMALL_UP_THRESHOLD:
        return "小涨"
    if pct > SMALL_DN_THRESHOLD:
        return "震荡"
    if pct > BIG_DN_THRESHOLD:
        return "小跌"
    return "大跌"


def label_state_from_ratio(return_ratio: float) -> str:
    """Classify a fractional return ratio into one canonical five-state label."""
    return label_state(ratio_to_pct(return_ratio))
