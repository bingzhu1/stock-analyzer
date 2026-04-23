from __future__ import annotations

import pandas as pd
import streamlit as st


def render_scan_result(sr: dict) -> None:
    """Render a ScanResult dict produced by scanner.run_scan()."""
    bias_colors = {"bullish": "#2ecc71", "bearish": "#e74c3c", "neutral": "#95a5a6"}
    conf_colors = {"high": "#f39c12", "medium": "#3498db", "low": "#95a5a6"}
    conf_labels = {"confirmed": "✅ confirmed", "diverging": "⚡ diverging", "mixed": "〰 mixed"}
    state_icons = {
        "gap_up": "🔼 gap_up",
        "flat": "⬛ flat",
        "gap_down": "🔽 gap_down",
        "high_go": "📈 high_go",
        "low_go": "📉 low_go",
        "range": "↔ range",
        "expanding": "🔊 expanding",
        "normal": "🔉 normal",
        "shrinking": "🔈 shrinking",
        "bullish": "🟢 bullish",
        "bearish": "🔴 bearish",
        "neutral": "⚪ neutral",
    }
    rs_icons = {
        "stronger": "▲ stronger",
        "weaker": "▼ weaker",
        "neutral": "= neutral",
        "unavailable": "— n/a",
    }

    bias = sr.get("scan_bias", "neutral")
    confidence = sr.get("scan_confidence", "low")
    conf_state = sr.get("confirmation_state", "mixed")
    bias_color = bias_colors.get(bias, "#888888")
    conf_color = conf_colors.get(confidence, "#888888")

    st.markdown(
        f'<span style="color:#888888;font-size:0.85em">'
        f'{sr.get("symbol","AVGO")} · '
        f'{sr.get("scan_phase","daily").upper()} · '
        f'{sr.get("scan_timestamp","")}</span>',
        unsafe_allow_html=True,
    )
    phase_note = sr.get("scan_phase_note")
    if phase_note:
        st.caption(phase_note)

    st.markdown(
        f'<div style="margin:8px 0 4px 0">'
        f'<span style="font-size:2em;font-weight:bold;color:{bias_color}">'
        f'{bias.upper()}</span>'
        f'&nbsp;&nbsp;'
        f'<span style="font-size:1.1em;font-weight:bold;color:{conf_color};'
        f'background:{conf_color}22;padding:2px 10px;border-radius:6px">'
        f'{confidence.upper()}</span>'
        f'&nbsp;&nbsp;'
        f'<span style="font-size:0.9em;color:#aaaaaa">'
        f'{conf_labels.get(conf_state, conf_state)}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(f"> {sr.get('notes', '')}")
    st.divider()

    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown("**AVGO States**")
        states_data = {
            "Field": ["Gap", "Intraday", "Volume", "Price / Stage"],
            "Value": [
                state_icons.get(sr.get("avgo_gap_state", ""), sr.get("avgo_gap_state", "?")),
                state_icons.get(sr.get("avgo_intraday_state", ""), sr.get("avgo_intraday_state", "?")),
                state_icons.get(sr.get("avgo_volume_state", ""), sr.get("avgo_volume_state", "?")),
                state_icons.get(sr.get("avgo_price_state", ""), sr.get("avgo_price_state", "?")),
            ],
        }
        st.dataframe(pd.DataFrame(states_data), hide_index=True, use_container_width=True)
        st.caption(f"Pattern code: `{sr.get('avgo_pattern_code', '—')}`")

    with col_r:
        st.markdown("**Relative Strength vs Peers**")
        rs_5d = sr.get("relative_strength_5d_summary", sr.get("relative_strength_summary", {}))
        rs_same_day = sr.get("relative_strength_same_day_summary", {})
        peers = list(rs_5d.keys() or rs_same_day.keys())
        rs_data = {
            "Peer": [s.replace("vs_", "").upper() for s in peers],
            "5-day": [rs_icons.get(rs_5d.get(s, "unavailable"), rs_5d.get(s, "unavailable")) for s in peers],
            "Same-day": [
                rs_icons.get(rs_same_day.get(s, "unavailable"), rs_same_day.get(s, "unavailable"))
                for s in peers
            ],
        }
        st.dataframe(pd.DataFrame(rs_data), hide_index=True, use_container_width=True)

        conf_label = conf_labels.get(conf_state, conf_state)
        st.caption(f"Confirmation: {conf_label}")

    st.divider()

    st.markdown("**Historical Match Summary**")
    hist = sr.get("historical_match_summary", {})
    top_ctx = hist.get("top_context_score")
    ctx_str = f"{top_ctx:.0f}" if top_ctx is not None else "—"
    outcome = hist.get("dominant_historical_outcome", "—")
    outcome_colors = {
        "up_bias": "#2ecc71",
        "down_bias": "#e74c3c",
        "mixed": "#f39c12",
        "insufficient_sample": "#95a5a6",
    }
    outcome_color = outcome_colors.get(outcome, "#888888")

    h1, h2, h3, h4 = st.columns(4)
    h1.metric("Exact matches", hist.get("exact_match_count", 0))
    h2.metric("Near matches", hist.get("near_match_count", 0))
    h3.metric("Top ctx score", ctx_str)
    h4.markdown(
        f'<div style="padding-top:8px">'
        f'<span style="font-size:0.75em;color:#888888">Historical bias</span><br>'
        f'<span style="font-weight:bold;color:{outcome_color}">{outcome}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    with st.expander("Raw scan JSON"):
        st.json(sr)


def render_scan_tab(target_date_str: str, scan_result: dict | None) -> None:
    st.subheader(f"Scan Result — {target_date_str}")
    if scan_result is None:
        st.info("Scan result not available. Re-run analysis to generate it.")
    else:
        render_scan_result(scan_result)
