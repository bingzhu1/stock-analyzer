"""Task 090 — big-up exclusion contradiction card streamlit renderer.

Pure presentation layer. Consumes the structured payload produced by
``services.big_up_contradiction_card.build_contradiction_card`` and
renders it via streamlit. No business logic. No payload mutation.

The streamlit module is imported once as ``st`` so tests can
``monkeypatch.setattr(ui.big_up_contradiction_card, "st", fake_st)``.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

__all__ = ("render_contradiction_card",)


_VARIANT_FN_NAME: dict[str, str] = {
    "strong_warning": "error",
    "warning": "warning",
    "info": "info",
}

_HEALTH_LABEL_CN: dict[str, str] = {
    "stale": "数据陈旧",
    "partial": "数据有限",
    "missing": "数据缺失",
}


def _emit_top_banner(variant: str, message: str) -> None:
    fn_name = _VARIANT_FN_NAME.get(variant, "info")
    fn = getattr(st, fn_name, None)
    if fn is None:
        st.write(message)
    else:
        fn(message)


def _render_top_section(payload: dict[str, Any]) -> None:
    title = str(payload.get("title") or "").strip()
    if title:
        st.markdown(f"**{title}**")

    header_message = str(payload.get("header_message") or "").strip()
    if header_message:
        _emit_top_banner(str(payload.get("variant") or "info"), header_message)

    explanation = str(payload.get("chinese_explanation") or "").strip()
    if explanation:
        st.write(explanation)

    original = str(payload.get("original_system_summary") or "").strip()
    if original:
        st.caption(original)

    level = str(payload.get("contradiction_level") or "").strip()
    confidence = str(payload.get("exclusion_confidence") or "").strip()
    if level or confidence:
        st.caption(
            f"矛盾等级：{level or '—'} · 否定置信：{confidence or '—'}"
        )


def _render_flag_section(payload: dict[str, Any]) -> None:
    triggered = [str(f).strip() for f in (payload.get("triggered_flags") or []) if str(f).strip()]
    reasons = [str(r).strip() for r in (payload.get("flag_reasons_cn") or []) if str(r).strip()]

    if not triggered and not reasons:
        return

    st.markdown("**反证信号**")
    if triggered:
        st.caption("触发标志：" + " | ".join(triggered))
    for reason in reasons:
        st.caption(f"- {reason}")


def _render_missing_section(payload: dict[str, Any]) -> None:
    missing = [str(m).strip() for m in (payload.get("missing_fields") or []) if str(m).strip()]
    if not missing:
        return
    st.caption("数据缺口：" + " / ".join(missing))


def _render_data_health_section(payload: dict[str, Any]) -> None:
    overall = str(payload.get("data_health_overall_status") or "").strip().lower()
    if overall in ("", "unknown", "healthy"):
        return

    label = _HEALTH_LABEL_CN.get(overall, overall)
    st.caption(f"数据健康：{label}")

    for w in payload.get("cache_health_warnings") or []:
        text = str(w).strip()
        if text:
            st.caption(f"- {text}")


def _render_big_down_section(payload: dict[str, Any]) -> None:
    tail = payload.get("big_down_tail_warning")
    if not isinstance(tail, dict):
        return

    had_big_down = bool(tail.get("had_big_down_exclusion"))
    if not had_big_down:
        st.caption("本次未触发大跌否定，因此不生成大跌侧双尾收缩提醒。")
        return

    level = str(tail.get("warning_level") or "none").strip().lower()
    explanation = str(tail.get("explanation") or "").strip()

    if level == "strong_warning":
        msg = "检测到强双尾收缩风险，本次大跌否定不建议作为强排除项。"
        if explanation:
            msg = f"{msg} {explanation}"
        st.error(msg)
        return

    if level == "warning":
        msg = "检测到大跌侧尾部风险，本次大跌否定可靠性下降。"
        if explanation:
            msg = f"{msg} {explanation}"
        st.warning(msg)
        return

    if explanation:
        st.caption(explanation)


def render_contradiction_card(payload: dict[str, Any] | None) -> None:
    """Render the big-up contradiction card payload via streamlit.

    Pure presentation. Does not mutate ``payload``.
    """
    if not isinstance(payload, dict):
        return
    if not payload.get("show_card", True):
        return

    _render_top_section(payload)
    _render_flag_section(payload)
    _render_missing_section(payload)
    _render_data_health_section(payload)
    _render_big_down_section(payload)
