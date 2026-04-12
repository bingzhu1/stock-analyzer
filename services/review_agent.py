# -*- coding: utf-8 -*-
"""
services/review_agent.py

LLM-powered post-close review generator.

Responsibilities
----------------
- Build a structured prompt from prediction + outcome records
- Call Anthropic API (claude-haiku-4-5) to generate a review
- Validate output against ReviewOutput schema (pydantic if available)
- Fall back to a rule-based review if LLM is unavailable or output is invalid
- Persist the result to review_log via prediction_store

Entry point: generate_review(prediction_id) -> dict

LLM's only job
--------------
Explain WHY a prediction succeeded or failed.  It does NOT make new
predictions, suggest trades, or access external data.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from services.prediction_store import (
    get_outcome_for_prediction,
    get_prediction,
    get_review_for_prediction,
    save_review,
)

# ─────────────────────────────────────────────────────────────────────────────
# Optional dependencies — degrade gracefully if absent
# ─────────────────────────────────────────────────────────────────────────────

try:
    from pydantic import BaseModel, ValidationError as PydanticValidationError

    class ReviewOutput(BaseModel):
        error_category: str
        root_cause: str
        confidence_note: str
        watch_for_next_time: str

    _PYDANTIC_OK = True
except ImportError:
    _PYDANTIC_OK = False

try:
    import anthropic as _anthropic

    _ANTHROPIC_OK = True
except ImportError:
    _ANTHROPIC_OK = False

_VALID_CATEGORIES = frozenset({
    "wrong_direction",
    "right_direction_wrong_magnitude",
    "correct",
    "false_confidence",
    "insufficient_data",
})

_LLM_MODEL = "claude-haiku-4-5-20251001"

# ─────────────────────────────────────────────────────────────────────────────
# Prompts
# ─────────────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are a quantitative research analyst reviewing a day-trading prediction for AVGO (Broadcom) stock.

Your ONLY job is to analyze WHY the prediction succeeded or failed based on the structured inputs.
You must NOT make new predictions, suggest trades, or access any external information.

Output ONLY valid JSON matching this exact schema — no text outside the JSON object:
{
  "error_category": "<one of: wrong_direction | right_direction_wrong_magnitude | correct | false_confidence | insufficient_data>",
  "root_cause": "<1-2 sentences explaining the primary reason for success or failure>",
  "confidence_note": "<1 sentence evaluating whether the stated confidence level was appropriate>",
  "watch_for_next_time": "<1 specific signal or condition to watch when this pattern appears again>"
}
"""

_USER_TEMPLATE = """\
## Prediction (made before market open)
Symbol: {symbol}
Date: {prediction_for_date}
Final Bias: {final_bias}
Final Confidence: {final_confidence}
Scan Bias: {scan_bias}
Research Adjustment: {research_adjustment}
Supporting Factors: {supporting_factors}
Conflicting Factors: {conflicting_factors}
Prediction Summary: {prediction_summary}

## Actual Market Outcome
Open Change vs Prev Close: {open_change_pct}%
Close Change vs Prev Close: {close_change_pct}%
Direction Correct: {direction_label}
Scenario Match: {scenario_match}

## Task
Analyze this prediction result. Output only the JSON object described in the system prompt.\
"""


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fmt_pct(value: float | None) -> str:
    return f"{value * 100:.2f}" if value is not None else "N/A"


def _direction_label(direction_correct: int | None) -> str:
    return {1: "YES (correct)", 0: "NO (wrong)", None: "N/A (neutral / flat move)"}.get(
        direction_correct, "unknown"
    )


def _scenario_match_label(raw: Any) -> str:
    if not raw:
        return "N/A"
    try:
        parsed = json.loads(str(raw))
    except json.JSONDecodeError:
        return str(raw)
    if not isinstance(parsed, dict):
        return str(raw)
    return (
        f"exact={parsed.get('exact_match_count', 'N/A')}, "
        f"near={parsed.get('near_match_count', 'N/A')}, "
        f"dominant={parsed.get('dominant_historical_outcome', 'N/A')}, "
        f"top_context_score={parsed.get('top_context_score', 'N/A')}"
    )


def _build_user_prompt(prediction: dict, outcome: dict) -> str:
    predict_json: dict = json.loads(prediction.get("predict_result_json") or "{}")
    return _USER_TEMPLATE.format(
        symbol=prediction.get("symbol", "AVGO"),
        prediction_for_date=prediction.get("prediction_for_date", "N/A"),
        final_bias=prediction.get("final_bias", "N/A"),
        final_confidence=prediction.get("final_confidence", "N/A"),
        scan_bias=predict_json.get("scan_bias", "N/A"),
        research_adjustment=predict_json.get("research_bias_adjustment", "N/A"),
        supporting_factors=", ".join(predict_json.get("supporting_factors", [])) or "none",
        conflicting_factors=", ".join(predict_json.get("conflicting_factors", [])) or "none",
        prediction_summary=predict_json.get("prediction_summary", "N/A"),
        open_change_pct=_fmt_pct(outcome.get("actual_open_change")),
        close_change_pct=_fmt_pct(outcome.get("actual_close_change")),
        direction_label=_direction_label(outcome.get("direction_correct")),
        scenario_match=_scenario_match_label(outcome.get("scenario_match")),
    )


def _extract_json(raw: str) -> dict:
    """Parse JSON from LLM output, stripping any markdown code fences."""
    text = raw.strip()
    # Strip ```json ... ``` or ``` ... ``` wrappers
    fence_match = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    if fence_match:
        text = fence_match.group(1).strip()
    return json.loads(text)


def _normalize_category(cat: str) -> str:
    return cat if cat in _VALID_CATEGORIES else "insufficient_data"


def _validate(parsed: dict) -> dict:
    """Validate parsed LLM output. Returns normalized dict or raises."""
    if _PYDANTIC_OK:
        output = ReviewOutput(**parsed)
        return {
            "error_category": _normalize_category(output.error_category),
            "root_cause": output.root_cause,
            "confidence_note": output.confidence_note,
            "watch_for_next_time": output.watch_for_next_time,
        }
    # Manual fallback if pydantic not installed
    for field in ("error_category", "root_cause", "confidence_note", "watch_for_next_time"):
        if field not in parsed or not isinstance(parsed[field], str):
            raise ValueError(f"Missing or invalid field: {field}")
    return {
        "error_category": _normalize_category(parsed["error_category"]),
        "root_cause": parsed["root_cause"],
        "confidence_note": parsed["confidence_note"],
        "watch_for_next_time": parsed["watch_for_next_time"],
    }


def _rule_based_fallback(prediction: dict, outcome: dict) -> dict:
    """
    Deterministic fallback used when LLM is unavailable or produces invalid output.
    No reasoning — just a factual summary from the available numbers.
    """
    direction_ok = outcome.get("direction_correct")
    close_chg = outcome.get("actual_close_change") or 0.0
    bias = prediction.get("final_bias", "neutral")
    confidence = prediction.get("final_confidence", "low")

    if direction_ok == 1:
        category = (
            "correct" if abs(close_chg) >= 0.01
            else "right_direction_wrong_magnitude"
        )
        root = (
            f"Prediction ({bias}) was directionally correct; "
            f"actual close change was {close_chg * 100:.2f}%."
        )
    elif direction_ok == 0:
        category = "wrong_direction"
        root = (
            f"Prediction ({bias}) was directionally wrong; "
            f"actual close change was {close_chg * 100:.2f}%."
        )
    else:
        category = "insufficient_data"
        root = (
            f"Move was too small or prediction was neutral — "
            f"cannot classify direction. Close change: {close_chg * 100:.2f}%."
        )

    return {
        "error_category": category,
        "root_cause": root,
        "confidence_note": (
            f"Stated confidence was {confidence}. "
            "LLM review unavailable — manual assessment required."
        ),
        "watch_for_next_time": "Review this case manually when LLM is available.",
    }


def _call_llm(user_prompt: str, api_key: str) -> tuple[dict, str]:
    """
    Call Anthropic API, parse and validate the response.
    Returns (validated_review_dict, raw_text).
    Raises on network error, JSON parse failure, or schema validation failure.
    """
    client = _anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=_LLM_MODEL,
        max_tokens=512,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    raw_text: str = response.content[0].text
    parsed = _extract_json(raw_text)
    validated = _validate(parsed)
    return validated, raw_text


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def generate_review(prediction_id: str) -> dict[str, Any]:
    """
    Generate and persist a post-close review for a prediction.

    Idempotent — returns the existing review if one already exists.

    Requires an outcome_log entry to exist first (call capture_outcome first).

    Raises
    ------
    ValueError
        - prediction or outcome not found in DB
    """
    existing = get_review_for_prediction(prediction_id)
    if existing:
        return existing

    prediction = get_prediction(prediction_id)
    if not prediction:
        raise ValueError(f"Prediction '{prediction_id}' not found in the database.")

    outcome = get_outcome_for_prediction(prediction_id)
    if not outcome:
        raise ValueError(
            f"No outcome found for prediction '{prediction_id}'. "
            "Run Capture Outcome first."
        )

    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    review_data: dict | None = None
    raw_text = ""

    if api_key and _ANTHROPIC_OK:
        user_prompt = _build_user_prompt(prediction, outcome)
        try:
            review_data, raw_text = _call_llm(user_prompt, api_key)
        except Exception as exc:
            # Log to stderr for debugging; fall through to rule-based fallback
            import sys
            print(f"[review_agent] LLM call failed ({exc!r}), using fallback.", file=sys.stderr)
            review_data = None

    if review_data is None:
        review_data = _rule_based_fallback(prediction, outcome)

    save_review(
        prediction_id=prediction_id,
        error_category=review_data["error_category"],
        root_cause=review_data["root_cause"],
        confidence_note=review_data["confidence_note"],
        watch_for_next_time=review_data["watch_for_next_time"],
        review_json=json.dumps(review_data),
        raw_llm_output=raw_text,
    )

    return get_review_for_prediction(prediction_id)
