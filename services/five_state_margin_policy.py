"""Five-state margin display policy (Task 085).

Pure output-structure helper for interpreting a five-state probability
distribution without overwriting the original top1 state. This policy
adds margin metadata and a display-oriented state string so callers can
surface low-margin ambiguity such as:

    震荡 = 0.45
    小涨 = 0.42

as "震荡/小涨分歧" rather than presenting only a single confident top1.
"""

from __future__ import annotations

from typing import Any

CANONICAL_STATES: tuple[str, ...] = ("大涨", "小涨", "震荡", "小跌", "大跌")
STATE_ORDER = {state: idx for idx, state in enumerate(CANONICAL_STATES)}

MARGIN_UNKNOWN = "unknown"
MARGIN_LOW = "low_margin"
MARGIN_WATCH = "watch_margin"
MARGIN_CLEAR = "clear_top1"

DISPLAY_UNKNOWN = "unknown"


def _parse_probability(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _validate_distribution(
    five_state_distribution: Any,
) -> tuple[dict[str, float] | None, str]:
    if not isinstance(five_state_distribution, dict):
        return None, "五状态分布缺失或格式不正确"

    parsed: dict[str, float] = {}
    for state in CANONICAL_STATES:
        if state not in five_state_distribution:
            return None, f"五状态分布缺少 {state}"
        value = _parse_probability(five_state_distribution.get(state))
        if value is None:
            return None, f"五状态分布中的 {state} 概率无效"
        if value < 0:
            return None, f"五状态分布中的 {state} 概率不能为负"
        parsed[state] = value

    total = sum(parsed.values())
    if total <= 0:
        return None, "五状态分布总和无效"
    return parsed, ""


def _rank_states(probabilities: dict[str, float]) -> list[tuple[str, float]]:
    return sorted(
        probabilities.items(),
        key=lambda item: (-item[1], STATE_ORDER[item[0]]),
    )


def apply_five_state_margin_policy(
    five_state_distribution: dict,
    final_direction: str | None = None,
    low_margin_threshold: float = 0.05,
    watch_margin_threshold: float = 0.10,
) -> dict[str, Any]:
    """Return display-oriented margin metadata for a five-state distribution."""
    probabilities, invalid_note = _validate_distribution(five_state_distribution)
    if probabilities is None:
        return {
            "primary_state": None,
            "secondary_state": None,
            "primary_probability": None,
            "secondary_probability": None,
            "top1_margin": None,
            "margin_band": MARGIN_UNKNOWN,
            "display_state": DISPLAY_UNKNOWN,
            "state_conflict": False,
            "policy_note": invalid_note or "五状态分布不可用",
            "top2_states": [],
        }

    ranked = _rank_states(probabilities)
    primary_state, primary_probability = ranked[0]
    secondary_state, secondary_probability = ranked[1]
    top1_margin = primary_probability - secondary_probability

    if top1_margin < low_margin_threshold:
        margin_band = MARGIN_LOW
        display_state = f"{primary_state}/{secondary_state}分歧"
        policy_note = (
            f"{primary_state} 仅以 {top1_margin:.2f} 的微弱优势领先 {secondary_state}，"
            "不宜过度强调单一 top1。"
        )
    elif top1_margin < watch_margin_threshold:
        margin_band = MARGIN_WATCH
        display_state = f"{primary_state}为主，{secondary_state}接近"
        policy_note = (
            f"{primary_state} 仍为第一选择，但与 {secondary_state} 的差距仅 "
            f"{top1_margin:.2f}，应保留观察。"
        )
    else:
        margin_band = MARGIN_CLEAR
        display_state = primary_state
        policy_note = (
            f"{primary_state} 以 {top1_margin:.2f} 的明显优势领先 {secondary_state}，"
            "可按清晰 top1 展示。"
        )

    state_conflict = False
    if (
        final_direction == "偏多"
        and primary_state == "震荡"
        and secondary_state in {"小涨", "大涨"}
    ):
        state_conflict = True
        policy_note += " 方向偏多但五状态 top1 为震荡，且上涨状态接近。"

    return {
        "primary_state": primary_state,
        "secondary_state": secondary_state,
        "primary_probability": primary_probability,
        "secondary_probability": secondary_probability,
        "top1_margin": top1_margin,
        "margin_band": margin_band,
        "display_state": display_state,
        "state_conflict": state_conflict,
        "policy_note": policy_note,
        "top2_states": [primary_state, secondary_state],
    }
