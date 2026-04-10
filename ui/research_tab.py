from __future__ import annotations

import streamlit as st

from research import run_research


def render_research_result(rr: dict) -> None:
    """Render a ResearchResult dict produced by research.run_research()."""
    st.markdown(
        f"**{rr.get('symbol', 'AVGO')}** · "
        f"{rr.get('research_timestamp', '')} · "
        f"{rr.get('source_count', 0)} sources"
    )

    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Sentiment", str(rr.get("sentiment_bias", "neutral")).upper())
    r2.metric("Confidence", str(rr.get("confidence", "low")).upper())
    r3.metric("Catalyst", "YES" if rr.get("catalyst_detected") else "NO")
    r4.metric("Adjustment", str(rr.get("research_bias_adjustment", "no_change")))

    tags = rr.get("topic_tags", [])
    st.markdown("**Topic tags**")
    st.write(", ".join(tags) if tags else "No topic tags detected.")

    st.markdown("**Summary**")
    st.write(rr.get("market_narrative_summary", ""))
    st.write(rr.get("catalyst_summary", ""))
    st.write(rr.get("peer_context_summary", ""))
    st.info(rr.get("notes", ""))

    with st.expander("Raw research JSON"):
        st.json(rr)


def render_research_tab(scan_result: dict | None, research_result: dict | None) -> dict | None:
    st.subheader("Research v1 — Manual Narrative Check")
    st.caption(
        "Paste headlines, snippets, or notes. Research comments on Scan; it does not replace Scan."
    )

    if scan_result is None:
        st.warning("Run Scan first so Research can compare against the current scan_result.")

    pasted_headlines = st.text_area(
        "Pasted headlines",
        key="research_headlines",
        height=120,
        placeholder="One headline per line...",
    )
    pasted_snippets = st.text_area(
        "Pasted social/news snippets",
        key="research_snippets",
        height=160,
        placeholder="Paste short news/social excerpts here...",
    )
    freeform_notes = st.text_area(
        "Optional freeform notes",
        key="research_notes",
        height=100,
        placeholder="Your own context or observations...",
    )

    run_research_clicked = st.button(
        "Run Research",
        type="secondary",
        use_container_width=True,
        disabled=scan_result is None,
    )
    if run_research_clicked:
        has_research_text = any(
            text.strip()
            for text in (pasted_headlines, pasted_snippets, freeform_notes)
        )
        if not has_research_text:
            st.warning("Paste at least one headline, snippet, or note before running Research.")
        else:
            research_result = run_research(
                pasted_headlines=pasted_headlines,
                pasted_snippets=pasted_snippets,
                freeform_notes=freeform_notes,
                scan_result=scan_result,
            )
            st.session_state["research_result"] = research_result

    if research_result is None:
        st.info("Paste research text and click **Run Research** to generate a structured summary.")
    else:
        render_research_result(research_result)

    return research_result
