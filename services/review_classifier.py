# -*- coding: utf-8 -*-
"""
services/review_classifier.py

Deterministic review classifier built on top of a comparison result dict
produced by services/review_comparator.compare_prediction_vs_actual().

No LLM, no network — pure rule logic.

Public API
----------
classify_review_errors(comparison: dict) -> dict
build_review_summary(comparison: dict, error_info: dict) -> str

classify_review_errors output schema
--------------------------------------
{
    # Required spec fields
    "error_types":        list[str],    # Chinese label per wrong dimension
                                        # e.g. ["开盘判断错误", "路径判断错误"]
    "primary_error":      str | None,   # Most significant wrong dimension
                                        # priority: path > close > open; None if all correct
    "reason_guesses":     list[str],    # Chinese reason string per wrong/unclear dimension

    # Additional metadata
    "error_category":     str,          # from error_taxonomy
    "error_dimensions":   list[str],    # internal names: ["open", "path", "close"]
    "correct_dimensions": list[str],
    "unclear_dimensions": list[str],
    "dimension_detail": {
        "open":  { "predicted": str|None, "actual": str|None, "correct": bool|None },
        "path":  { "predicted": str|None, "actual": str|None, "correct": bool|None },
        "close": { "predicted": str|None, "actual": str|None, "correct": bool|None },
    },
    "overall_score":      float,
    "correct_count":      int,
    "total_count":        int,
}
"""

from __future__ import annotations

from typing import Any

from services.error_taxonomy import ErrorCategory, normalize_error_category

# ─────────────────────────────────────────────────────────────────────────────
# Label tables
# ─────────────────────────────────────────────────────────────────────────────

# Chinese error type labels per dimension (shown when dimension is wrong)
_ERROR_TYPE: dict[str, str] = {
    "open":  "开盘判断错误",
    "path":  "路径判断错误",
    "close": "收盘判断错误",
}

# Chinese reason strings per dimension — separate messages for wrong vs unclear
_REASON_WRONG: dict[str, str] = {
    "open":  "预测开盘方向与实际不一致",
    "path":  "预测路径与实际结构不一致",
    "close": "预测收盘方向与实际不一致",
}
_REASON_UNCLEAR: dict[str, str] = {
    "open":  "开盘预测信号不明确，无法判定",
    "path":  "路径预测信号不明确，无法判定",
    "close": "收盘预测信号不明确，无法判定",
}

# Priority order for selecting the primary error (highest priority first)
# Spec: 路径判断错误 > 开盘判断错误 > 收盘判断错误
_PRIMARY_PRIORITY = ("path", "open", "close")


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _bucket(correct_flag: bool | None) -> str:
    """Classify a single dimension into 'correct', 'wrong', or 'unclear'."""
    if correct_flag is True:
        return "correct"
    if correct_flag is False:
        return "wrong"
    return "unclear"


def _dimension_detail(
    predicted: str | None,
    actual: str | None,
    correct: bool | None,
) -> dict[str, Any]:
    return {"predicted": predicted, "actual": actual, "correct": correct}


def _pick_primary_error(error_dimensions: list[str]) -> str | None:
    """Return the highest-priority wrong dimension label, or None if nothing is wrong."""
    for dim in _PRIMARY_PRIORITY:
        if dim in error_dimensions:
            return _ERROR_TYPE[dim]
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def classify_review_errors(comparison: dict[str, Any]) -> dict[str, Any]:
    """
    Classify which dimensions of a comparison were correct, wrong, or unclear.

    Parameters
    ----------
    comparison  dict produced by compare_prediction_vs_actual()

    Returns
    -------
    Structured error classification — see module docstring for full schema.
    """
    open_correct: bool | None = comparison.get("open_correct")
    path_correct: bool | None = comparison.get("path_correct")
    close_correct: bool | None = comparison.get("close_correct")

    dim_map = {
        "open":  open_correct,
        "path":  path_correct,
        "close": close_correct,
    }

    error_dimensions:   list[str] = []
    correct_dimensions: list[str] = []
    unclear_dimensions: list[str] = []

    for dim, flag in dim_map.items():
        bucket = _bucket(flag)
        if bucket == "correct":
            correct_dimensions.append(dim)
        elif bucket == "wrong":
            error_dimensions.append(dim)
        else:
            unclear_dimensions.append(dim)

    dimension_detail = {
        "open":  _dimension_detail(
            comparison.get("pred_open"),
            comparison.get("actual_open_type"),
            open_correct,
        ),
        "path":  _dimension_detail(
            comparison.get("pred_path"),
            comparison.get("actual_path"),
            path_correct,
        ),
        "close": _dimension_detail(
            comparison.get("pred_close"),
            comparison.get("actual_close_type"),
            close_correct,
        ),
    }

    error_category: ErrorCategory = normalize_error_category(
        comparison.get("error_category", "")
    )

    # ── Required spec fields ─────────────────────────────────────────────────
    error_types: list[str] = [_ERROR_TYPE[d] for d in error_dimensions]
    primary_error: str | None = _pick_primary_error(error_dimensions)

    # reason_guesses: one entry per wrong dimension, then one per unclear dimension
    reason_guesses: list[str] = (
        [_REASON_WRONG[d] for d in error_dimensions]
        + [_REASON_UNCLEAR[d] for d in unclear_dimensions]
    )

    return {
        # Required spec fields
        "error_types":        error_types,
        "primary_error":      primary_error,
        "reason_guesses":     reason_guesses,
        # Additional metadata
        "error_category":     error_category,
        "error_dimensions":   error_dimensions,
        "correct_dimensions": correct_dimensions,
        "unclear_dimensions": unclear_dimensions,
        "dimension_detail":   dimension_detail,
        "overall_score":      float(comparison.get("overall_score", 0.0)),
        "correct_count":      int(comparison.get("correct_count", 0)),
        "total_count":        int(comparison.get("total_count", 3)),
    }


def build_review_summary(
    comparison: dict[str, Any],
    error_info: dict[str, Any],
) -> str:
    """
    Build a concise deterministic review summary from a comparison + error_info.

    No LLM — output is fully reproducible given the same inputs.

    Returns
    -------
    A multi-line string suitable for display in the UI review panel.
    """
    bias = str(comparison.get("final_bias", "neutral")).upper()
    confidence = str(comparison.get("final_confidence", "low"))
    prediction_for_date = str(comparison.get("prediction_for_date", ""))
    symbol = str(comparison.get("symbol", "AVGO"))

    direction_match = comparison.get("direction_match")
    dir_label = {1: "方向正确 ✓", 0: "方向错误 ✗", None: "方向无法判定"}.get(
        direction_match, "方向未知"
    )

    correct_count = error_info.get("correct_count", 0)
    total_count = error_info.get("total_count", 3)
    overall_score = error_info.get("overall_score", 0.0)
    error_category = str(error_info.get("error_category", "insufficient_data"))
    error_dims = error_info.get("error_dimensions", [])
    correct_dims = error_info.get("correct_dimensions", [])
    unclear_dims = error_info.get("unclear_dimensions", [])
    detail = error_info.get("dimension_detail", {})

    lines: list[str] = []

    # ── Header ────────────────────────────────────────────────────────────────
    lines.append(f"[{symbol}] {prediction_for_date} — {bias} / {confidence}")
    lines.append(dir_label)

    # ── Score ─────────────────────────────────────────────────────────────────
    score_bar = "█" * correct_count + "░" * (total_count - correct_count)
    lines.append(f"得分 {correct_count}/{total_count} [{score_bar}]  {overall_score:.0%}")

    # ── Dimension breakdown ───────────────────────────────────────────────────
    dim_names = {"open": "开盘", "path": "路径", "close": "收盘"}
    for dim in ("open", "path", "close"):
        d = detail.get(dim, {})
        pred = d.get("predicted") or "—"
        actual = d.get("actual") or "—"
        flag = d.get("correct")
        tag = {True: "✓", False: "✗", None: "?"}.get(flag, "?")
        lines.append(f"  {dim_names[dim]}: 预期 {pred} → 实际 {actual} {tag}")

    # ── Error category ────────────────────────────────────────────────────────
    category_cn = {
        "correct":                          "判断正确",
        "wrong_direction":                  "方向错误",
        "right_direction_wrong_magnitude":  "方向正确但幅度偏差",
        "false_confidence":                 "过度自信",
        "insufficient_data":                "信息不足",
    }.get(error_category, error_category)
    lines.append(f"分类: {category_cn} ({error_category})")

    # ── Primary error + reason guesses ───────────────────────────────────────
    primary = error_info.get("primary_error")
    if primary:
        lines.append(f"主要问题: {primary}")

    reasons = error_info.get("reason_guesses", [])
    for reason in reasons:
        lines.append(f"  · {reason}")

    # ── Dimension summary ─────────────────────────────────────────────────────
    if correct_dims:
        dim_str = "、".join(dim_names.get(d, d) for d in correct_dims)
        lines.append(f"正确维度: {dim_str}")
    if unclear_dims:
        dim_str = "、".join(dim_names.get(d, d) for d in unclear_dims)
        lines.append(f"无法判定: {dim_str}")

    return "\n".join(lines)
