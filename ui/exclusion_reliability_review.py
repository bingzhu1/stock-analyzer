from __future__ import annotations

from typing import Any

import streamlit as st

from services.exclusion_reliability_review import build_exclusion_reliability_review


def _tier_badge(tier_cn: str) -> str:
    if tier_cn == "强证据":
        return "强证据"
    if tier_cn == "辅助证据":
        return "辅助证据"
    if tier_cn == "数据缺口提醒":
        return "数据缺口提醒"
    return "无新增解释"


def render_exclusion_reliability_review(payload: dict[str, Any]) -> None:
    if not payload or not payload.get("has_exclusion_review"):
        return

    st.markdown("**否定可靠性解释**")
    summary = str(payload.get("summary_cn") or "").strip()
    if summary:
        st.caption(summary)

    for item in payload.get("review_items") or []:
        if not item.get("has_exclusion"):
            continue

        excluded_state = str(item.get("excluded_state") or "—")
        strongest_tier_cn = str(item.get("strongest_tier_cn") or "").strip()
        support_mix = str(item.get("support_mix") or "supported").strip()
        title = f"否定方向：{excluded_state} · {_tier_badge(strongest_tier_cn)}"

        with st.container():
            st.markdown(f"**{title}**")
            st.caption(f"support_mix = {support_mix}")

            display_summary = str(item.get("display_summary_cn") or "").strip()
            if display_summary:
                st.write(display_summary)

            taxonomy_entries = item.get("taxonomy_entries") or []
            if item.get("has_reliability_concern") and taxonomy_entries:
                st.markdown("**解释依据**")
                for entry in taxonomy_entries:
                    tier = str(entry.get("display_tier_cn") or "").strip()
                    line = str(entry.get("display_cn") or "").strip()
                    title_cn = str(entry.get("title_cn") or "").strip()
                    if line:
                        st.caption(f"- [{tier}] {title_cn}：{line}")
            elif not item.get("has_reliability_concern"):
                st.caption("当前没有命中已定义的可靠性下降解释。")

            unmapped = item.get("unmapped_source_labels") or []
            if unmapped:
                st.caption(f"未映射标签：{' | '.join(str(v) for v in unmapped)}")


def render_exclusion_reliability_review_for_row(row: dict[str, Any] | None) -> None:
    payload = build_exclusion_reliability_review(row)
    render_exclusion_reliability_review(payload)


__all__ = (
    "render_exclusion_reliability_review",
    "render_exclusion_reliability_review_for_row",
)
