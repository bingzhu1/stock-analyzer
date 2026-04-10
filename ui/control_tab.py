from __future__ import annotations

import pandas as pd
import streamlit as st

from services.agent_parser import parse_agent_command
from services.agent_schema import STARTER_EXAMPLES, build_command_help_text
from services.query_executor import (
    AnalysisContext,
    QueryResult,
    describe_default_scope,
    execute_agent_command,
)


def render_control_tab(context: AnalysisContext) -> None:
    st.subheader("Control Chat")
    st.caption(
        "Ask read-only questions about the current scan and match results. "
        "This chat does not refresh data, run research, or execute code."
    )
    st.info(f"Default query scope: {describe_default_scope(context)}.")
    st.caption(
        "Say `exact`, `near`, or `all matches` to override the default displayed scope. "
        "Otherwise queries use the rows currently visible after sidebar result filters."
    )

    with st.expander("Supported commands and examples", expanded=not context.has_analysis):
        st.markdown(build_command_help_text())

    if not context.has_analysis:
        st.warning(
            "No analysis is loaded yet. Use **Run Analysis** in the sidebar first; "
            "until then, Control Chat can only show help and examples."
        )

    history_key = "control_chat_history"
    if history_key not in st.session_state:
        st.session_state[history_key] = [
            {
                "role": "assistant",
                "content": (
                    "I can summarize Scan, explain bias, compare exact vs near matches, "
                    "filter/sort top rows, and group supported labels. "
                    f"Try `{STARTER_EXAMPLES[0]}` or `{STARTER_EXAMPLES[3]}`."
                ),
                "table": None,
            }
        ]

    for message in st.session_state[history_key]:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            table = message.get("table")
            if isinstance(table, pd.DataFrame) and not table.empty:
                st.dataframe(table, hide_index=True, use_container_width=True)

    prompt = st.chat_input("Ask about the current scan or match results...")
    if not prompt:
        return

    st.session_state[history_key].append({"role": "user", "content": prompt, "table": None})
    with st.chat_message("user"):
        st.write(prompt)

    command = parse_agent_command(prompt)
    result = execute_agent_command(command, context)
    _append_assistant_message(history_key, result)

    with st.chat_message("assistant"):
        st.write(result.message)
        if result.table is not None and not result.table.empty:
            st.dataframe(result.table, hide_index=True, use_container_width=True)


def _append_assistant_message(history_key: str, result: QueryResult) -> None:
    st.session_state[history_key].append(
        {
            "role": "assistant",
            "content": result.message,
            "table": result.table,
        }
    )
