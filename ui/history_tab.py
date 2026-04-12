from __future__ import annotations

import json
from typing import Any

import pandas as pd
import streamlit as st

from services.prediction_store import (
    get_outcome_for_prediction,
    get_prediction,
    get_review_for_prediction,
    list_predictions,
)


def _direction_label(value: Any, status: str = "") -> str:
    if value == 1:
        return "CORRECT"
    if value == 0:
        return "WRONG"
    if value is None:
        if status in {"outcome_captured", "review_generated"}:
            return "NEUTRAL"
        return "PENDING"
    return "NEUTRAL"


def _format_pct(value: Any) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value) * 100:+.2f}%"
    except (TypeError, ValueError):
        return ""


def _json_or_empty(raw: Any) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(str(raw))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _prediction_summary(prediction: dict[str, Any] | None) -> str:
    if not prediction:
        return ""
    predict_json = _json_or_empty(prediction.get("predict_result_json"))
    return str(predict_json.get("prediction_summary") or "")


def _scenario_label(raw: Any) -> str:
    scenario = _json_or_empty(raw)
    if not scenario:
        return ""
    return (
        f"exact {scenario.get('exact_match_count', 'N/A')} / "
        f"near {scenario.get('near_match_count', 'N/A')} / "
        f"{scenario.get('dominant_historical_outcome', 'N/A')}"
    )


def _history_rows(predictions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in predictions:
        rows.append(
            {
                "prediction_for_date": row.get("prediction_for_date", ""),
                "final_bias": row.get("final_bias", ""),
                "final_confidence": row.get("final_confidence", ""),
                "status": row.get("status", ""),
                "direction_correct": _direction_label(
                    row.get("direction_correct"),
                    str(row.get("status", "")),
                ),
                "scenario_match": _scenario_label(row.get("scenario_match")),
                "close_change": _format_pct(row.get("actual_close_change")),
                "id": row.get("id", ""),
            }
        )
    return rows


def _option_label(row: dict[str, Any]) -> str:
    return (
        f"{row.get('prediction_for_date', '')} | "
        f"{row.get('final_bias', '')} | "
        f"{row.get('status', '')} | "
        f"{str(row.get('id', ''))[:8]}"
    )


def _render_prediction_detail(prediction: dict[str, Any]) -> None:
    st.markdown("**Prediction**")
    st.write(_prediction_summary(prediction) or "No prediction summary stored.")

    with st.expander("Prediction JSON"):
        st.json(_json_or_empty(prediction.get("predict_result_json")))

    with st.expander("Scan / Research JSON"):
        st.markdown("**Scan**")
        st.json(_json_or_empty(prediction.get("scan_result_json")))
        st.markdown("**Research**")
        st.json(_json_or_empty(prediction.get("research_result_json")))


def _render_outcome_detail(outcome: dict[str, Any] | None) -> None:
    st.markdown("**Outcome**")
    if not outcome:
        st.info("No outcome captured yet.")
        return

    fields = [
        "prediction_for_date",
        "actual_open",
        "actual_high",
        "actual_low",
        "actual_close",
        "actual_prev_close",
        "actual_open_change",
        "actual_close_change",
        "direction_correct",
        "scenario_match",
    ]
    st.dataframe(
        pd.DataFrame([{field: outcome.get(field) for field in fields}]),
        hide_index=True,
        use_container_width=True,
    )


def _render_review_detail(review: dict[str, Any] | None) -> None:
    st.markdown("**Review**")
    if not review:
        st.info("No review generated yet.")
        return

    st.markdown(f"**Category:** {review.get('error_category', '')}")
    st.markdown(f"**Root cause:** {review.get('root_cause', '')}")
    st.markdown(f"**Confidence:** {review.get('confidence_note', '')}")
    st.markdown(f"**Watch for next time:** {review.get('watch_for_next_time', '')}")

    with st.expander("Review JSON"):
        st.json(_json_or_empty(review.get("review_json")))


def render_history_tab() -> None:
    st.subheader("History")
    st.caption("Review saved predictions, captured outcomes, and generated reviews.")

    predictions = list_predictions(limit=100)
    if not predictions:
        st.info("No saved predictions yet.")
        return

    rows = _history_rows(predictions)
    st.dataframe(
        pd.DataFrame(rows),
        hide_index=True,
        use_container_width=True,
    )

    options = {_option_label(row): row["id"] for row in rows if row.get("id")}
    selected_label = st.selectbox("Inspect record", list(options.keys()))
    selected_id = options[selected_label]

    prediction = get_prediction(selected_id)
    if not prediction:
        st.warning("Selected prediction was not found.")
        return

    outcome = get_outcome_for_prediction(selected_id)
    review = get_review_for_prediction(selected_id)

    st.divider()
    st.markdown(f"### {prediction.get('symbol', 'AVGO')} — {prediction.get('prediction_for_date', '')}")

    col_prediction, col_outcome, col_review = st.columns(3)
    with col_prediction:
        _render_prediction_detail(prediction)
    with col_outcome:
        _render_outcome_detail(outcome)
    with col_review:
        _render_review_detail(review)
