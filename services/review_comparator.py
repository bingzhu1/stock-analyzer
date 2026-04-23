# -*- coding: utf-8 -*-
"""
services/review_comparator.py

Deterministic comparison layer: stored prediction fields vs captured actual
outcome fields.  No LLM, no network — pure rule logic.

Public API
----------
extract_prediction_structure(prediction) -> dict
compare_prediction_vs_actual(prediction, actual) -> dict

Input shapes — prediction
-------------------------
The function tolerates three layouts (checked in priority order):

  1. Top-level Chinese labels:
       { "pred_open": "高开", "pred_path": "高开高走", "pred_close": "收涨", ... }

  2. Nested under a "predict_result" key (dict or JSON string):
       { "predict_result": { "pred_open": "高开", ... } }
     or with tendency keys that get mapped to Chinese:
       { "predict_result": { "open_tendency": "gap_up_bias", ... } }

  3. Raw prediction_log row with "predict_result_json" (JSON string):
       { "predict_result_json": '{"open_tendency": "gap_up_bias", ...}' }
     Tendency values are mapped to Chinese labels internally.
     pred_path is derived from the (pred_open, pred_close) pair.

Missing fields → None, never a fabricated value.

Input shapes — actual
---------------------
  (a) Pre-mapped:  { "actual_open_type": ..., "actual_path": ..., "actual_close_type": ... }
  (b) capture_actual_outcome() output: { "open_label": ..., "path_label": ..., "close_label": ... }
  (c) Raw OHLCV: actual_prev_close + actual_open + actual_close → derived on the fly.
Pre-mapped keys always win.

Scoring
-------
  overall_score = correct_count / 3   (denominator is always 3)
  None (unclear) contributes 0 correct; total_count is always 3.

Output schema ("return at least" per spec — extra metadata kept for downstream)
------------
{
    "symbol":               str,
    "prediction_for_date":  str,

    "pred_open":            str | None,
    "pred_path":            str | None,
    "pred_close":           str | None,

    "actual_open_type":     str | None,
    "actual_path":          str | None,
    "actual_close_type":    str | None,

    "open_correct":         bool | None,
    "path_correct":         bool | None,
    "close_correct":        bool | None,

    "correct_count":        int,          # 0–3
    "total_count":          int,          # always 3
    "overall_score":        float,        # correct_count / 3

    # Additional metadata
    "final_bias":           str,
    "final_confidence":     str,
    "direction_match":      1 | 0 | None,
    "error_category":       str,
    "summary":              str,

    # Diagnostic
    "_missing_fields":      list[str],    # names of pred fields that could not be resolved
}
"""

from __future__ import annotations

import json
from typing import Any

from services.error_taxonomy import classify_error_category, ErrorCategory
from services.outcome_capture import classify_actual_structure

# ─────────────────────────────────────────────────────────────────────────────
# Mapping tables
# ─────────────────────────────────────────────────────────────────────────────

_OPEN_TENDENCY_TO_LABEL: dict[str, str] = {
    "gap_up_bias":   "高开",
    "gap_down_bias": "低开",
    "flat_bias":     "平开",
}

_CLOSE_TENDENCY_TO_LABEL: dict[str, str] = {
    "close_strong": "收涨",
    "close_weak":   "收跌",
    "range":        "平收",
}

_PATH_LABEL_MAP: dict[tuple[str, str], str] = {
    ("高开", "收涨"): "高开高走",
    ("高开", "收跌"): "高开低走",
    ("高开", "平收"): "高开震荡",
    ("低开", "收涨"): "低开高走",
    ("低开", "收跌"): "低开低走",
    ("低开", "平收"): "低开震荡",
    ("平开", "收涨"): "平开走高",
    ("平开", "收跌"): "平开走低",
    ("平开", "平收"): "平开震荡",
}

_TOTAL_DIMENSIONS = 3  # open, path, close — denominator is always 3


# ─────────────────────────────────────────────────────────────────────────────
# Prediction-side helpers
# ─────────────────────────────────────────────────────────────────────────────

def _parse_json_field(value: Any) -> dict[str, Any]:
    """Parse a value that is either a dict or a JSON string. Returns {} on failure."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, ValueError):
            return {}
    return {}


def _map_open(d: dict[str, Any]) -> str | None:
    """Return Chinese open label from dict — direct key wins over tendency mapping."""
    if d.get("pred_open"):
        return str(d["pred_open"])
    return _OPEN_TENDENCY_TO_LABEL.get(str(d.get("open_tendency", "")))


def _map_close(d: dict[str, Any]) -> str | None:
    if d.get("pred_close"):
        return str(d["pred_close"])
    return _CLOSE_TENDENCY_TO_LABEL.get(str(d.get("close_tendency", "")))


def _derive_path(d: dict[str, Any], pred_open: str | None, pred_close: str | None) -> str | None:
    if d.get("pred_path"):
        return str(d["pred_path"])
    if pred_open and pred_close:
        return _PATH_LABEL_MAP.get((pred_open, pred_close))
    return None


def extract_prediction_structure(prediction: dict[str, Any]) -> dict[str, Any]:
    """
    Extract pred_open, pred_path, pred_close from a prediction dict.

    Resolution order (first non-None value wins for each field):
      1. Top-level keys:  prediction["pred_open"] etc.
      2. Nested dict:     prediction["predict_result"]["pred_open"] (or open_tendency)
      3. JSON string:     prediction["predict_result_json"] → parse → map tendency keys

    pred_path is additionally derived from (pred_open, pred_close) if not set explicitly.

    Returns
    -------
    { "pred_open": str|None, "pred_path": str|None, "pred_close": str|None }
    Values are None when a field genuinely cannot be resolved — never fabricated.
    """
    pred_open: str | None = None
    pred_path: str | None = None
    pred_close: str | None = None

    # ── 1. Top-level keys ────────────────────────────────────────────────────
    pred_open = _map_open(prediction) or pred_open
    pred_close = _map_close(prediction) or pred_close
    if prediction.get("pred_path"):
        pred_path = str(prediction["pred_path"])

    # ── 2. Nested "predict_result" (dict or JSON string) ─────────────────────
    nested = _parse_json_field(prediction.get("predict_result"))
    if nested:
        pred_open = pred_open or _map_open(nested)
        pred_close = pred_close or _map_close(nested)
        if not pred_path and nested.get("pred_path"):
            pred_path = str(nested["pred_path"])

    # ── 3. predict_result_json string (raw prediction_log row) ───────────────
    pr_json = _parse_json_field(prediction.get("predict_result_json"))
    if pr_json:
        pred_open = pred_open or _map_open(pr_json)
        pred_close = pred_close or _map_close(pr_json)
        if not pred_path and pr_json.get("pred_path"):
            pred_path = str(pr_json["pred_path"])

    # ── Derive path from open+close if still missing ──────────────────────────
    if not pred_path:
        pred_path = _derive_path({}, pred_open, pred_close)

    return {
        "pred_open": pred_open,
        "pred_path": pred_path,
        "pred_close": pred_close,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Actual-side helpers
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_actual_open_type(actual: dict[str, Any]) -> str | None:
    if actual.get("actual_open_type"):
        return str(actual["actual_open_type"])
    if actual.get("open_label"):
        return str(actual["open_label"])
    prev = actual.get("actual_prev_close")
    o = actual.get("actual_open")
    c = actual.get("actual_close")
    if prev and o and c:
        return classify_actual_structure({"Open": o, "Close": c}, prev)["open_label"]
    return None


def _resolve_actual_close_type(actual: dict[str, Any]) -> str | None:
    if actual.get("actual_close_type"):
        return str(actual["actual_close_type"])
    if actual.get("close_label"):
        return str(actual["close_label"])
    prev = actual.get("actual_prev_close")
    o = actual.get("actual_open")
    c = actual.get("actual_close")
    if prev and o and c:
        return classify_actual_structure({"Open": o, "Close": c}, prev)["close_label"]
    return None


def _resolve_actual_path(actual: dict[str, Any]) -> str | None:
    if actual.get("actual_path"):
        return str(actual["actual_path"])
    if actual.get("path_label"):
        return str(actual["path_label"])
    prev = actual.get("actual_prev_close")
    o = actual.get("actual_open")
    c = actual.get("actual_close")
    if prev and o and c:
        return classify_actual_structure({"Open": o, "Close": c}, prev)["path_label"]
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Scoring
# ─────────────────────────────────────────────────────────────────────────────

def _correct(predicted: str | None, actual: str | None) -> bool | None:
    if predicted is None or actual is None:
        return None
    return predicted == actual


def _score(open_c: bool | None, path_c: bool | None, close_c: bool | None) -> tuple[int, int, float]:
    """
    Score the three comparison dimensions.

    Returns (correct_count, total_count=3, overall_score=correct_count/3).
    None (unclear) counts as 0 correct; denominator is always 3.
    """
    correct = sum(1 for c in (open_c, path_c, close_c) if c is True)
    return correct, _TOTAL_DIMENSIONS, correct / _TOTAL_DIMENSIONS


# ─────────────────────────────────────────────────────────────────────────────
# Summary builder
# ─────────────────────────────────────────────────────────────────────────────

def _build_summary(
    *,
    bias: str,
    confidence: str,
    direction_match: int | None,
    pred_open: str | None,
    actual_open_type: str | None,
    open_correct: bool | None,
    pred_close: str | None,
    actual_close_type: str | None,
    close_correct: bool | None,
    overall_score: float,
    error_category: str,
) -> str:
    dir_label = {1: "方向正确", 0: "方向错误", None: "方向无法判定"}.get(direction_match, "?")
    parts = [f"[{bias.upper()} / {confidence}] {dir_label}"]

    if open_correct is not None:
        parts.append(f"开盘 {pred_open}→{actual_open_type} {'✓' if open_correct else '✗'}")
    if close_correct is not None:
        parts.append(f"收盘 {pred_close}→{actual_close_type} {'✓' if close_correct else '✗'}")

    parts.append(f"得分 {overall_score:.0%} | 分类: {error_category}")
    return " | ".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def compare_prediction_vs_actual(
    prediction: dict[str, Any],
    actual: dict[str, Any],
) -> dict[str, Any]:
    """
    Compare a stored prediction against a captured actual outcome.

    Tolerant of all three supported prediction shapes — see module docstring.
    Never crashes on missing fields; unresolvable values appear as None and
    are listed in the "_missing_fields" diagnostic key.

    Returns a structured dict matching the spec schema (see module docstring).
    """
    symbol: str = str(prediction.get("symbol", "AVGO"))
    prediction_for_date: str = str(prediction.get("prediction_for_date", ""))
    bias: str = str(prediction.get("final_bias", "neutral"))
    confidence: str = str(prediction.get("final_confidence", "low"))

    # ── Prediction side ───────────────────────────────────────────────────────
    pred_struct = extract_prediction_structure(prediction)
    pred_open = pred_struct["pred_open"]
    pred_path = pred_struct["pred_path"]
    pred_close = pred_struct["pred_close"]

    missing_fields = [
        name for name, val in (("pred_open", pred_open), ("pred_path", pred_path),
                               ("pred_close", pred_close))
        if val is None
    ]

    # ── Actual side ───────────────────────────────────────────────────────────
    actual_open_type = _resolve_actual_open_type(actual)
    actual_close_type = _resolve_actual_close_type(actual)
    actual_path = _resolve_actual_path(actual)

    # ── Comparisons ───────────────────────────────────────────────────────────
    open_correct = _correct(pred_open, actual_open_type)
    path_correct = _correct(pred_path, actual_path)
    close_correct = _correct(pred_close, actual_close_type)

    correct_count, total_count, overall_score = _score(open_correct, path_correct, close_correct)

    # ── Direction / error category ────────────────────────────────────────────
    direction_match: int | None = actual.get("direction_correct")
    if direction_match is None:
        close_change = actual.get("actual_close_change")
        if close_change is not None:
            from services.outcome_capture import _compute_direction_correct
            direction_match = _compute_direction_correct(bias, float(close_change))

    error_category: ErrorCategory = classify_error_category(
        direction_correct=direction_match,
        actual_close_change=actual.get("actual_close_change"),
    )

    summary = _build_summary(
        bias=bias,
        confidence=confidence,
        direction_match=direction_match,
        pred_open=pred_open,
        actual_open_type=actual_open_type,
        open_correct=open_correct,
        pred_close=pred_close,
        actual_close_type=actual_close_type,
        close_correct=close_correct,
        overall_score=overall_score,
        error_category=error_category,
    )

    return {
        "symbol": symbol,
        "prediction_for_date": prediction_for_date,
        "pred_open": pred_open,
        "pred_path": pred_path,
        "pred_close": pred_close,
        "actual_open_type": actual_open_type,
        "actual_path": actual_path,
        "actual_close_type": actual_close_type,
        "open_correct": open_correct,
        "path_correct": path_correct,
        "close_correct": close_correct,
        "correct_count": correct_count,
        "total_count": total_count,
        "overall_score": overall_score,
        "final_bias": bias,
        "final_confidence": confidence,
        "direction_match": direction_match,
        "error_category": error_category,
        "summary": summary,
        "_missing_fields": missing_fields,
    }
