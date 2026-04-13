"""Stable error taxonomy helpers for post-close review output."""

from __future__ import annotations

from typing import Any, Final, Literal

ErrorCategory = Literal[
    "correct",
    "wrong_direction",
    "right_direction_wrong_magnitude",
    "false_confidence",
    "insufficient_data",
]

CORRECT: Final[ErrorCategory] = "correct"
WRONG_DIRECTION: Final[ErrorCategory] = "wrong_direction"
RIGHT_DIRECTION_WRONG_MAGNITUDE: Final[ErrorCategory] = "right_direction_wrong_magnitude"
FALSE_CONFIDENCE: Final[ErrorCategory] = "false_confidence"
INSUFFICIENT_DATA: Final[ErrorCategory] = "insufficient_data"

VALID_ERROR_CATEGORIES: Final[frozenset[ErrorCategory]] = frozenset({
    CORRECT,
    WRONG_DIRECTION,
    RIGHT_DIRECTION_WRONG_MAGNITUDE,
    FALSE_CONFIDENCE,
    INSUFFICIENT_DATA,
})

SIGNIFICANT_MOVE_THRESHOLD: Final[float] = 0.01


def normalize_error_category(value: Any) -> ErrorCategory:
    """Return a known category, falling back to insufficient_data."""
    if not isinstance(value, str):
        return INSUFFICIENT_DATA

    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized in VALID_ERROR_CATEGORIES:
        return normalized  # type: ignore[return-value]
    return INSUFFICIENT_DATA


def classify_error_category(
    direction_correct: int | bool | None,
    actual_close_change: float | None,
    *,
    significant_move_threshold: float = SIGNIFICANT_MOVE_THRESHOLD,
) -> ErrorCategory:
    """Classify the deterministic review category from outcome facts."""
    close_change = actual_close_change or 0.0

    if direction_correct == 1 or direction_correct is True:
        if abs(close_change) >= significant_move_threshold:
            return CORRECT
        return RIGHT_DIRECTION_WRONG_MAGNITUDE

    if direction_correct == 0 or direction_correct is False:
        return WRONG_DIRECTION

    return INSUFFICIENT_DATA
