from __future__ import annotations

import os
import pandas as pd
import streamlit as st

from predict import run_predict
from services.ai_summary import build_projection_ai_summary, build_review_ai_summary
from services.evidence_trace import build_projection_evidence_trace
from services.openai_client import OpenAIClientError
from services.predict_summary import build_predict_readable_summary
from services.prediction_store import (
    get_outcome_for_prediction,
    get_review_for_prediction,
    save_prediction,
)
from services.outcome_capture import capture_outcome
from services.review_agent import generate_review


def _projection_ai_payload(
    predict_result: dict,
    scan_result: dict | None,
    research_result: dict | None,
) -> dict:
    readable = predict_result.get("readable_summary")
    if not isinstance(readable, dict):
        readable = build_predict_readable_summary(predict_result, scan_result=scan_result)
    return {
        "kind": "projection_ai_summary",
        "symbol": predict_result.get("symbol", "AVGO"),
        "final_bias": predict_result.get("final_bias"),
        "final_confidence": predict_result.get("final_confidence"),
        "open_tendency": predict_result.get("open_tendency"),
        "close_tendency": predict_result.get("close_tendency"),
        "prediction_summary": predict_result.get("prediction_summary"),
        "readable_summary": readable,
        "supporting_factors": predict_result.get("supporting_factors", []),
        "conflicting_factors": predict_result.get("conflicting_factors", []),
        "scan_result": scan_result or {},
        "research_result": research_result or {},
    }


def _review_ai_payload(
    *,
    prediction_id: str,
    predict_result: dict,
    outcome: dict,
    review: dict | None,
) -> dict:
    return {
        "kind": "review_ai_summary",
        "prediction_id": prediction_id,
        "symbol": predict_result.get("symbol", "AVGO"),
        "final_bias": predict_result.get("final_bias"),
        "final_confidence": predict_result.get("final_confidence"),
        "prediction_summary": predict_result.get("prediction_summary"),
        "readable_summary": predict_result.get("readable_summary") or {},
        "outcome": outcome,
        "rule_review": review or {},
    }


def _show_ai_summary_error(kind: str, exc: Exception) -> None:
    if isinstance(exc, OpenAIClientError):
        st.warning(str(exc))
        return
    st.warning(f"{kind}生成失败，已保留规则层结果：{exc}")


def _render_projection_ai_summary_entry(
    predict_result: dict,
    scan_result: dict | None,
    research_result: dict | None,
) -> None:
    st.markdown("**AI 推演总结**")
    if st.button("生成 AI 推演总结", key="btn_generate_ai_projection_summary"):
        payload = _projection_ai_payload(predict_result, scan_result, research_result)
        with st.spinner("正在生成 AI 推演总结…"):
            try:
                st.session_state["ai_projection_summary_text"] = build_projection_ai_summary(payload)
            except Exception as exc:
                _show_ai_summary_error("AI 推演总结", exc)

    if st.session_state.get("ai_projection_summary_text"):
        st.write(st.session_state["ai_projection_summary_text"])


def _render_review_ai_summary_entry(
    *,
    prediction_id: str | None,
    predict_result: dict,
    outcome: dict | None,
    review: dict | None,
) -> None:
    st.markdown("**AI 复盘总结**")
    if not prediction_id:
        st.button("生成 AI 复盘总结", key="btn_generate_ai_review_summary_locked1", disabled=True)
        st.caption("Complete Step 1 first.")
        return
    if not outcome:
        st.button("生成 AI 复盘总结", key="btn_generate_ai_review_summary_locked2", disabled=True)
        st.caption("Complete Step 2 first.")
        return

    if st.button("生成 AI 复盘总结", key="btn_generate_ai_review_summary"):
        payload = _review_ai_payload(
            prediction_id=prediction_id,
            predict_result=predict_result,
            outcome=outcome,
            review=review,
        )
        with st.spinner("正在生成 AI 复盘总结…"):
            try:
                st.session_state["ai_review_summary_text"] = build_review_ai_summary(payload)
            except Exception as exc:
                _show_ai_summary_error("AI 复盘总结", exc)

    if st.session_state.get("ai_review_summary_text"):
        st.write(st.session_state["ai_review_summary_text"])


def render_readable_predict_summary(summary: dict) -> None:
    """Render the rule-based Chinese summary block for Predict."""
    st.markdown("**明日基准判断**")
    base = summary.get("baseline_judgment", {})
    b1, b2, b3 = st.columns(3)
    b1.metric("方向", base.get("direction", "中性"))
    b2.metric("强度", base.get("strength", "弱"))
    b3.metric("风险", base.get("risk_level", "高"))
    st.write(base.get("text", "中性（强度：弱，风险：高，confidence：low）"))

    open_block = summary.get("open_projection", {})
    close_block = summary.get("close_projection", {})
    st.markdown("**开盘推演**")
    st.write(open_block.get("text", "更可能平开；等待开盘确认。"))
    st.markdown("**收盘推演**")
    st.write(close_block.get("text", "更可能震荡；等待盘中确认。"))

    st.markdown("**为什么这样判断**")
    for line in summary.get("rationale", []) or []:
        st.caption(f"- {line}")

    st.markdown("**风险提醒**")
    for line in summary.get("risk_reminders", []) or []:
        st.caption(f"- {line}")

    if summary.get("ai_polish"):
        st.markdown("**AI polish**")
        st.write(summary["ai_polish"])


def render_evidence_trace(trace: dict) -> None:
    """Render deterministic evidence trace blocks for Predict / projection."""
    if not isinstance(trace, dict):
        return

    st.markdown("**Evidence trace**")

    st.markdown("**tool_trace**")
    for item in trace.get("tool_trace", []) or []:
        st.caption(f"- {item}")

    st.markdown("**key_observations**")
    for line in trace.get("key_observations", []) or []:
        st.caption(f"- {line}")

    st.markdown("**decision_steps**")
    for line in trace.get("decision_steps", []) or []:
        st.caption(f"- {line}")

    st.markdown("**final_conclusion**")
    final = trace.get("final_conclusion", {}) or {}
    cols = st.columns(4)
    cols[0].metric("明日方向", final.get("direction", "中性"))
    cols[1].metric("开盘倾向", final.get("open_tendency", "平开"))
    cols[2].metric("收盘倾向", final.get("close_tendency", "震荡"))
    cols[3].metric("confidence", final.get("confidence", "low"))

    st.markdown("**verification_points**")
    for line in trace.get("verification_points", []) or []:
        st.caption(f"- {line}")


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

    readable_summary = pr.get("readable_summary")
    if not isinstance(readable_summary, dict):
        readable_summary = build_predict_readable_summary(pr)
    render_readable_predict_summary(readable_summary)

    trace = pr.get("evidence_trace")
    if isinstance(trace, dict):
        render_evidence_trace(trace)

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
    predict_result["readable_summary"] = build_predict_readable_summary(
        predict_result,
        scan_result=scan_result,
    )
    predict_result["evidence_trace"] = build_projection_evidence_trace(
        predict_result=predict_result,
        scan_result=scan_result,
    )
    if research_result is None:
        st.warning("No Research result found. Prediction is Scan-led until Research is run.")
    render_predict_result(predict_result)
    _render_projection_ai_summary_entry(predict_result, scan_result, research_result)

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
        review = None
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
        _render_review_ai_summary_entry(
            prediction_id=saved_pid,
            predict_result=predict_result,
            outcome=outcome,
            review=review,
        )

    return predict_result
