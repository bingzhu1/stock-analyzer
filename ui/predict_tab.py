from __future__ import annotations

import os
import pandas as pd
import streamlit as st

from predict import run_predict
from services.prediction_store import (
    get_outcome_for_prediction,
    get_review_for_prediction,
    save_prediction,
)
from services.outcome_capture import capture_outcome
from services.review_agent import generate_review


def render_predict_result(pr: dict) -> None:
    """Render a PredictResult dict produced by predict.run_predict()."""
    bias = str(pr.get("final_bias", "neutral"))
    confidence = str(pr.get("final_confidence", "low"))
    bias_colors = {"bullish": "#2ecc71", "bearish": "#e74c3c", "neutral": "#95a5a6"}
    conf_colors = {"high": "#f39c12", "medium": "#3498db", "low": "#95a5a6"}

    st.markdown(
        f"**{pr.get('symbol', 'AVGO')}** · "
        f"{pr.get('predict_timestamp', '')}"
    )
    st.markdown(
        f'<div style="margin:8px 0 4px 0">'
        f'<span style="font-size:2em;font-weight:bold;color:{bias_colors.get(bias, "#888888")}">'
        f'{bias.upper()}</span>'
        f'&nbsp;&nbsp;'
        f'<span style="font-size:1.1em;font-weight:bold;color:{conf_colors.get(confidence, "#888888")};'
        f'background:{conf_colors.get(confidence, "#888888")}22;padding:2px 10px;border-radius:6px">'
        f'{confidence.upper()}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Open tendency", pr.get("open_tendency", "unclear"))
    p2.metric("Close tendency", pr.get("close_tendency", "unclear"))
    p3.metric("Scan", f"{pr.get('scan_bias', 'neutral')} / {pr.get('scan_confidence', 'low')}")
    p4.metric("Research", pr.get("research_bias_adjustment", "missing_research"))

    st.markdown("**Prediction summary**")
    st.write(pr.get("prediction_summary", ""))
    st.info(pr.get("notes", ""))

    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("**Supporting factors**")
        supporting = pr.get("supporting_factors", [])
        st.dataframe(pd.DataFrame({"factor": supporting}), hide_index=True, use_container_width=True)
    with col_r:
        st.markdown("**Conflicting factors**")
        conflicting = pr.get("conflicting_factors", [])
        if conflicting:
            st.dataframe(pd.DataFrame({"factor": conflicting}), hide_index=True, use_container_width=True)
        else:
            st.write("No explicit conflicting factors.")

    with st.expander("Raw predict JSON"):
        st.json(pr)


def render_predict_tab(scan_result: dict | None, research_result: dict | None) -> dict | None:
    st.subheader("Predict v1 — Scan + Research Synthesis")
    st.caption(
        "Predict combines Scan with optional Research. It is rule-based and does not replace risk management."
    )

    if scan_result is None:
        st.info("Run Scan first to generate a prediction.")
        return None

    predict_result = run_predict(scan_result, research_result)
    if research_result is None:
        st.warning("No Research result found. Prediction is Scan-led until Research is run.")
    render_predict_result(predict_result)

    # ── Research Loop ─────────────────────────────────────────────────────────
    st.divider()
    st.subheader("Research Loop")
    st.caption("Save this prediction, then capture the actual outcome after market close to begin building memory.")

    # prediction_for_date = the trading day being analyzed (from the date picker)
    prediction_for_date: str = st.session_state.get("target_date_str", "")
    snapshot_id: str = st.session_state.get("snapshot_id", "—")

    # Track saved prediction per prediction_for_date to detect session-level saves
    saved_pid: str | None = st.session_state.get("saved_prediction_id")
    saved_date: str = st.session_state.get("saved_prediction_date", "")
    already_saved = bool(saved_pid and saved_date == prediction_for_date)

    col_save, col_outcome, col_review = st.columns(3)

    # ── Step 1: Save Prediction ───────────────────────────────────────────────
    with col_save:
        st.markdown("**Step 1 — Save Prediction**")

        def _do_save() -> None:
            pid = save_prediction(
                symbol=str(predict_result.get("symbol", "AVGO")),
                prediction_for_date=prediction_for_date,
                scan_result=scan_result,
                research_result=research_result,
                predict_result=predict_result,
                snapshot_id=snapshot_id,
            )
            st.session_state["saved_prediction_id"] = pid
            st.session_state["saved_prediction_date"] = prediction_for_date

        if not already_saved:
            if st.button("Save Today's Prediction", key="btn_save_prediction"):
                try:
                    _do_save()
                    st.rerun()
                except Exception as exc:
                    st.error(f"Save failed: {exc}")
        else:
            st.success("Saved")
            st.caption(f"ID: `{saved_pid[:8]}…`")
            st.caption("Saving again creates a new record and resets outcome/review for this session.")
            if st.button("Save New Version ↻", key="btn_save_new_version"):
                try:
                    _do_save()
                    st.rerun()
                except Exception as exc:
                    st.error(f"Save failed: {exc}")

    # Fetch outcome once — shared by Step 2 display and Step 3 precondition check
    outcome = get_outcome_for_prediction(saved_pid) if already_saved else None

    # ── Step 2: Capture Outcome ───────────────────────────────────────────────
    with col_outcome:
        st.markdown("**Step 2 — Capture Outcome**")
        if not already_saved:
            st.button("Capture Outcome", key="btn_capture_outcome_locked", disabled=True)
            st.caption("Complete Step 1 first.")
        elif outcome:
            direction_ok = outcome.get("direction_correct")
            close_chg = outcome.get("actual_close_change")
            label = {1: "CORRECT", 0: "WRONG", None: "NEUTRAL"}.get(direction_ok, "?")
            chg_str = f"{close_chg * 100:+.2f}%" if close_chg is not None else "N/A"
            st.success(f"{label}  ({chg_str})")
            actual_close_val = outcome.get("actual_close")
            close_display = f"{actual_close_val:.2f}" if actual_close_val is not None else "N/A"
            st.caption(f"Close: {close_display}")
        else:
            if st.button("Capture Outcome", key="btn_capture_outcome"):
                with st.spinner("Fetching market data…"):
                    try:
                        capture_outcome(saved_pid)
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))

    # ── Step 3: Generate Review ───────────────────────────────────────────────
    with col_review:
        st.markdown("**Step 3 — AI Review**")
        if not already_saved:
            st.button("Generate Review", key="btn_generate_review_locked1", disabled=True)
            st.caption("Complete Step 1 first.")
        elif not outcome:
            st.button("Generate Review", key="btn_generate_review_locked2", disabled=True)
            st.caption("Complete Step 2 first.")
        else:
            review = get_review_for_prediction(saved_pid)
            if review:
                cat = review.get("error_category", "")
                cat_colors = {
                    "correct": "green",
                    "wrong_direction": "red",
                    "right_direction_wrong_magnitude": "orange",
                    "false_confidence": "orange",
                    "insufficient_data": "gray",
                }
                color = cat_colors.get(cat, "gray")
                st.markdown(
                    f'<span style="color:{color};font-weight:bold">{cat.replace("_", " ").upper()}</span>',
                    unsafe_allow_html=True,
                )
                with st.expander("View Review"):
                    st.markdown(f"**Root cause:** {review.get('root_cause', '')}")
                    st.markdown(f"**Confidence:** {review.get('confidence_note', '')}")
                    st.markdown(f"**Watch for next time:** {review.get('watch_for_next_time', '')}")
                    if review.get("raw_llm_output"):
                        with st.expander("Raw LLM output"):
                            st.text(review["raw_llm_output"])
            else:
                has_key = bool(os.getenv("ANTHROPIC_API_KEY", "").strip())
                label = "Generate AI Review" if has_key else "Generate Review (rule-based)"
                if st.button(label, key="btn_generate_review"):
                    with st.spinner("Generating review…"):
                        try:
                            generate_review(saved_pid)
                            st.rerun()
                        except ValueError as exc:
                            st.error(str(exc))

    return predict_result
