# -*- coding: utf-8 -*-
"""
services/review_orchestrator.py

Thin orchestrator that wires together the four closed-loop services:
  prediction_store → outcome_capture → review_comparator → review_classifier

Public API
----------
run_review_for_prediction(symbol, prediction_for_date) -> dict

No LLM, no direct network calls — delegates to the individual services.

Return schema
-------------
On success:
{
    "status":               "ok",
    "symbol":               str,
    "prediction_for_date":  str,
    "prediction_id":        str,
    "comparison":           dict,   # from compare_prediction_vs_actual()
    "error_info":           dict,   # from classify_review_errors()
    "review_summary":       str,    # from build_review_summary()
    "meta":                 dict,   # v2 schema block
    "primary_projection":   dict,
    "peer_adjustment":      dict,
    "final_projection":     dict,
    "historical_probability": dict,
    "actual_outcome":       dict,
    "review_result":        dict,
    "rule_extraction":      dict,
}

On failure:
{
    "status":               "no_prediction" | "no_outcome" | "error",
    "symbol":               str,
    "prediction_for_date":  str,
    "prediction_id":        str | None,
    "error":                str,    # human-readable reason
}
"""

from __future__ import annotations

import json
from typing import Any

from services.prediction_store import (
    get_latest_prediction_for_target_date,
    get_outcome_for_prediction,
)
from services.outcome_capture import capture_outcome
from services.review_comparator import compare_prediction_vs_actual
from services.review_classifier import classify_review_errors, build_review_summary
from services.review_store import save_review_record

_REVIEW_SCHEMA_VERSION = 2


def _error_payload(
    status: str,
    symbol: str,
    prediction_for_date: str,
    error: str,
    prediction_id: str | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "symbol": symbol,
        "prediction_for_date": prediction_for_date,
        "prediction_id": prediction_id,
        "error": error,
    }


def _json_dict(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _projection_from_prediction(prediction: dict[str, Any]) -> dict[str, Any]:
    predict_result = _json_dict(prediction.get("predict_result_json"))
    final_projection = _json_dict(predict_result.get("final_projection"))
    return {
        "source": "prediction_log.predict_result_json",
        "symbol": prediction.get("symbol"),
        "prediction_for_date": prediction.get("prediction_for_date"),
        "final_bias": (
            prediction.get("final_bias")
            or final_projection.get("final_bias")
            or predict_result.get("final_bias")
        ),
        "final_confidence": (
            prediction.get("final_confidence")
            or final_projection.get("final_confidence")
            or predict_result.get("final_confidence")
        ),
        "pred_open": (
            final_projection.get("pred_open")
            or predict_result.get("pred_open")
            or predict_result.get("open_tendency")
        ),
        "pred_path": final_projection.get("pred_path") or predict_result.get("pred_path"),
        "pred_close": (
            final_projection.get("pred_close")
            or predict_result.get("pred_close")
            or predict_result.get("close_tendency")
        ),
        "prediction_summary": final_projection.get("prediction_summary") or predict_result.get("prediction_summary"),
        "supporting_factors": final_projection.get("supporting_factors", predict_result.get("supporting_factors", [])),
        "conflicting_factors": final_projection.get("conflicting_factors", predict_result.get("conflicting_factors", [])),
        "raw_predict_result": predict_result,
    }


def _block_with_defaults(
    block: dict[str, Any],
    defaults: dict[str, Any],
) -> dict[str, Any]:
    result = dict(block)
    for key, value in defaults.items():
        result.setdefault(key, value)
    return result


def _actual_outcome_block(outcome: dict[str, Any], comparison: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": "outcome_log",
        "prediction_for_date": outcome.get("prediction_for_date"),
        "actual_open": outcome.get("actual_open"),
        "actual_high": outcome.get("actual_high"),
        "actual_low": outcome.get("actual_low"),
        "actual_close": outcome.get("actual_close"),
        "actual_prev_close": outcome.get("actual_prev_close"),
        "actual_open_change": outcome.get("actual_open_change"),
        "actual_close_change": outcome.get("actual_close_change"),
        "actual_open_type": comparison.get("actual_open_type"),
        "actual_path": comparison.get("actual_path"),
        "actual_close_type": comparison.get("actual_close_type"),
        "direction_correct": outcome.get("direction_correct"),
        "scenario_match": outcome.get("scenario_match"),
    }


def _review_result_block(
    comparison: dict[str, Any],
    error_info: dict[str, Any],
    review_summary: str,
) -> dict[str, Any]:
    return {
        "comparison": comparison,
        "error_info": error_info,
        "review_summary": review_summary,
        "surface_errors": {
            "open_correct": comparison.get("open_correct"),
            "path_correct": comparison.get("path_correct"),
            "close_correct": comparison.get("close_correct"),
            "overall_score": comparison.get("overall_score"),
            "primary_error": error_info.get("primary_error"),
            "error_types": error_info.get("error_types", []),
        },
        "mechanism_errors": {
            "status": "reserved",
            "notes": "Task 10A only reserves mechanism-level review fields; computation lands later.",
            "items": [],
        },
    }


def _build_review_v2_blocks(
    *,
    symbol: str,
    prediction_for_date: str,
    prediction_id: str,
    prediction: dict[str, Any],
    outcome: dict[str, Any],
    comparison: dict[str, Any],
    error_info: dict[str, Any],
    review_summary: str,
) -> dict[str, dict[str, Any]]:
    predict_result = _json_dict(prediction.get("predict_result_json"))
    projection = _projection_from_prediction(prediction)
    saved_primary_projection = _json_dict(predict_result.get("primary_projection"))
    saved_peer_adjustment = _json_dict(predict_result.get("peer_adjustment"))
    saved_final_projection = _json_dict(predict_result.get("final_projection"))

    if saved_primary_projection:
        primary_projection = _block_with_defaults(
            saved_primary_projection,
            {
                "status": "computed",
                "source": "predict_result.primary_projection",
                "symbol": symbol,
                "prediction_for_date": prediction_for_date,
            },
        )
    else:
        primary_projection = {
            "status": "reserved_from_legacy_prediction",
            "notes": "Legacy prediction does not contain Task 10B primary_projection.",
            **projection,
        }

    if saved_peer_adjustment:
        peer_adjustment = _block_with_defaults(
            saved_peer_adjustment,
            {
                "status": "computed",
                "source": "predict_result.peer_adjustment",
                "peer_symbols": ["NVDA", "SOXX", "QQQ"],
            },
        )
    else:
        peer_adjustment = {
            "status": "reserved",
            "peer_symbols": ["NVDA", "SOXX", "QQQ"],
            "adjustments": [],
            "notes": "Legacy prediction does not contain Task 10B peer_adjustment.",
        }

    final_projection = _block_with_defaults(
        saved_final_projection,
        {
            "source": "legacy_prediction_result",
            "status": "carried_forward",
            "notes": "Legacy fallback uses the existing one-step prediction output.",
            "symbol": symbol,
            "prediction_for_date": prediction_for_date,
            "final_bias": comparison.get("final_bias") or projection.get("final_bias"),
            "final_confidence": comparison.get("final_confidence") or projection.get("final_confidence"),
            "pred_open": comparison.get("pred_open") or projection.get("pred_open"),
            "pred_path": comparison.get("pred_path") or projection.get("pred_path"),
            "pred_close": comparison.get("pred_close") or projection.get("pred_close"),
        },
    )
    final_projection["symbol"] = final_projection.get("symbol") or symbol
    final_projection["prediction_for_date"] = (
        final_projection.get("prediction_for_date") or prediction_for_date
    )

    return {
        "meta": {
            "schema_version": _REVIEW_SCHEMA_VERSION,
            "review_kind": "deterministic_review_v2",
            "status": "schema_only",
            "symbol": symbol,
            "prediction_for_date": prediction_for_date,
            "prediction_id": prediction_id,
        },
        "primary_projection": primary_projection,
        "peer_adjustment": peer_adjustment,
        "final_projection": final_projection,
        "historical_probability": {
            "status": "reserved",
            "probabilities": {},
            "notes": "Probability layer is intentionally not computed in Task 10A.",
        },
        "actual_outcome": _actual_outcome_block(outcome, comparison),
        "review_result": _review_result_block(comparison, error_info, review_summary),
        "rule_extraction": {
            "status": "reserved",
            "rules": [],
            "notes": "Rule extraction remains handled by review_analyzer; v2 review-level rules land later.",
        },
    }


def run_review_for_prediction(
    symbol: str,
    prediction_for_date: str,
) -> dict[str, Any]:
    """
    Run the full deterministic review loop for a (symbol, date) pair.

    Steps
    -----
    1. Look up the most recent saved prediction for (symbol, prediction_for_date).
    2. Retrieve the captured outcome; if absent, attempt to capture it via yfinance.
    3. Run compare_prediction_vs_actual() to produce structured comparison.
    4. Run classify_review_errors() to bucket errors and pick primary_error.
    5. Run build_review_summary() to produce a human-readable summary string.

    Returns a status="ok" payload on success, or a status="no_prediction" /
    "no_outcome" / "error" payload describing why the review could not be
    completed — never raises.

    Parameters
    ----------
    symbol              Ticker symbol (e.g. "AVGO")
    prediction_for_date Target trading date in "YYYY-MM-DD" format
    """
    # ── Step 1: fetch prediction ──────────────────────────────────────────────
    try:
        prediction = get_latest_prediction_for_target_date(symbol, prediction_for_date)
    except Exception as exc:
        return _error_payload("error", symbol, prediction_for_date,
                              f"Prediction lookup failed: {exc}")

    if not prediction:
        return _error_payload(
            "no_prediction", symbol, prediction_for_date,
            f"No saved prediction found for {symbol} / {prediction_for_date}. "
            "Run and save a prediction first.",
        )

    prediction_id: str = prediction["id"]

    # ── Step 2: fetch or capture outcome ─────────────────────────────────────
    try:
        outcome = get_outcome_for_prediction(prediction_id)
    except Exception as exc:
        return _error_payload("error", symbol, prediction_for_date,
                              f"Outcome lookup failed: {exc}", prediction_id)

    if not outcome:
        try:
            capture_outcome(prediction_id)
            outcome = get_outcome_for_prediction(prediction_id)
        except ValueError as exc:
            return _error_payload("no_outcome", symbol, prediction_for_date,
                                  str(exc), prediction_id)
        except Exception as exc:
            return _error_payload("error", symbol, prediction_for_date,
                                  f"Outcome capture failed: {exc}", prediction_id)

    if not outcome:
        return _error_payload(
            "no_outcome", symbol, prediction_for_date,
            "Outcome still unavailable after capture attempt. "
            "The market may not have closed yet for this date.",
            prediction_id,
        )

    # ── Steps 3–5: compare → classify → summarise ────────────────────────────
    try:
        comparison = compare_prediction_vs_actual(prediction, outcome)
        error_info = classify_review_errors(comparison)
        review_summary = build_review_summary(comparison, error_info)
    except Exception as exc:
        return _error_payload("error", symbol, prediction_for_date,
                              f"Review computation failed: {exc}", prediction_id)

    payload: dict[str, Any] = {
        "status": "ok",
        "symbol": symbol,
        "prediction_for_date": prediction_for_date,
        "prediction_id": prediction_id,
        "comparison": comparison,
        "error_info": error_info,
        "review_summary": review_summary,
    }
    payload.update(
        _build_review_v2_blocks(
            symbol=symbol,
            prediction_for_date=prediction_for_date,
            prediction_id=prediction_id,
            prediction=prediction,
            outcome=outcome,
            comparison=comparison,
            error_info=error_info,
            review_summary=review_summary,
        )
    )

    try:
        review_id = save_review_record(payload)
        payload["review_id"] = review_id
        payload["meta"]["review_id"] = review_id
    except Exception as exc:
        payload["review_save_error"] = str(exc)

    return payload
