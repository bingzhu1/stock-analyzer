"""ui/protection_layer_diagnostics_renderer.py — read-only sidecar.

Step 2G-8A.2 implementation per Step 2G-8A design (commit ``b4c1919``)
+ checkpoint (``8c56696``) + Step 2G-8A.1 helper (``cdbb13a``) +
helper checkpoint (``b43fd9d``). Pure-function pair that turns a
``protection_layer_diagnostics.v1`` dict into a card_data shape +
safe markdown string for Predict / Review UI.

Design contract (Step 2G-8A.1 checkpoint §6.3 / §12.3):
- pure functions: never read DB / CSV / network; never import
  ``streamlit`` / simulator / dashboard / prediction_store / yfinance /
  requests / trading APIs / v1 stub trio
- never mutate input
- always returns a dict / string; never raises
- never produces forbidden copy (Step 2G-8A.2 §1 — 8 tokens explicit
  in the task spec; tests grep)

Public API:
    build_protection_layer_diagnostics_card_data(diagnostics) -> dict
    render_protection_layer_diagnostics_markdown(card_data) -> str
"""
from __future__ import annotations

from typing import Any


SCHEMA_VERSION = "protection_layer_diagnostics_card.v1"

# Forbidden copy that this renderer must NEVER emit (Step 2G-8A.2 §1).
# Note: ``hard`` and ``forced`` are forbidden as substrings — that is
# why the card_data renderer uses Chinese labels (``决策链未接入`` /
# ``评估闸门暂未接入``) instead of printing raw flag names like
# ``hard_gate_connected``.
FORBIDDEN_COPY_TOKENS: tuple[str, ...] = (
    "禁止交易",
    "强制否定",
    "hard",
    "forced",
    "no_trade",
    "卖出信号",
    "做空信号",
    "自动拦截",
)


# ── helpers ──────────────────────────────────────────────────────────────

def _is_real_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    return isinstance(value, (int, float))


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _format_pct(value: Any) -> str:
    if not _is_real_number(value):
        return "n/a"
    return f"{float(value) * 100:.1f}%"


def _format_evidence(evidence: dict) -> list[str]:
    """Pretty-print evidence values; only consume known keys to avoid
    leaking unfiltered payload into the page."""
    out: list[str] = []
    if "holdout_status" in evidence:
        out.append(f"holdout_status={evidence['holdout_status']}")
    if "net_benefit" in evidence:
        out.append(f"net_benefit={_format_pct(evidence['net_benefit'])}")
    if "threshold" in evidence:
        out.append(f"threshold={_format_pct(evidence['threshold'])}")
    return out


# Connection-flag label map. Keys mirror the helper's flag names; values
# are Chinese labels chosen to avoid the ``hard`` / ``forced`` forbidden
# substrings while preserving meaning (Step 2G-8A.1 checkpoint §5).
_FLAG_LABELS: tuple[tuple[str, str], ...] = (
    ("diagnostic_connected", "诊断已接入"),
    ("hard_gate_connected", "决策链未接入"),
    ("required_field_connected", "04 字段未升级"),
    ("protection_layer_connected_for_gate", "评估闸门暂未接入"),
)


def _flag_state_text(flag_name: str, value: bool) -> str:
    """Render a flag as ``label · 是 / 否`` so the user sees an explicit
    yes/no state without leaking forbidden tokens (e.g. ``hard``)."""
    label = dict(_FLAG_LABELS).get(flag_name, flag_name)
    state = "是" if value else "否"
    return f"{label} · {state}"


# ── card_data builder ────────────────────────────────────────────────────

def _empty_card_data(*, schema_present: bool = False) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "visible": False,
        "diagnostic_connected": True if schema_present else False,
        "hard_gate_connected": False,
        "required_field_connected": False,
        "protection_layer_connected_for_gate": False,
        "guards": [],
        "summary": {},
        "warnings": [],
    }


def build_protection_layer_diagnostics_card_data(
    diagnostics: dict | None,
) -> dict[str, Any]:
    """Turn a ``protection_layer_diagnostics.v1`` dict into a card_data
    shape suitable for the markdown renderer.

    Pure function. Never raises; missing / malformed input → safe
    invisible card_data. The four connection flags are mirrored from
    the helper's spec-locked invariants (diagnostic_connected always
    True when input has the helper schema; the rest always False).

    A card is visible when at least one guard is present OR when there
    is a passthrough warning (e.g. ``final_test_range_refusal``) that
    the user should see; the empty / no-data path stays invisible so
    Predict / Review UI does not show an empty box.
    """
    if not isinstance(diagnostics, dict):
        return _empty_card_data()

    schema = diagnostics.get("schema_version") == "protection_layer_diagnostics.v1"
    if not schema:
        return _empty_card_data()

    guards_raw = _safe_list(diagnostics.get("guards"))
    guards: list[dict[str, Any]] = []
    for g in guards_raw:
        if not isinstance(g, dict):
            continue
        guards.append({
            "name": g.get("name"),
            "status": g.get("status"),
            "reason": g.get("reason"),
            "evidence": _safe_dict(g.get("evidence")),
            "message": g.get("message"),
        })

    summary = _safe_dict(diagnostics.get("summary"))
    warnings = [
        str(w) for w in _safe_list(diagnostics.get("warnings")) if w
    ]

    visible = bool(guards) or bool(warnings)

    return {
        "schema_version": SCHEMA_VERSION,
        "visible": visible,
        # Mirror the helper's spec-locked flags. Even when the input is
        # malformed beyond schema_version, we still surface the v1
        # invariants so any future reader sees the same locked picture.
        "diagnostic_connected": bool(diagnostics.get("diagnostic_connected", True)),
        "hard_gate_connected": bool(diagnostics.get("hard_gate_connected", False)),
        "required_field_connected": bool(
            diagnostics.get("required_field_connected", False)
        ),
        "protection_layer_connected_for_gate": bool(
            diagnostics.get("protection_layer_connected_for_gate", False)
        ),
        "guards": guards,
        "summary": {
            "hard_upgrade_blocked": bool(
                summary.get("hard_upgrade_blocked", True)
            ),
            "display_only": bool(summary.get("display_only", True)),
            "blocking_guard_count": int(
                summary.get("blocking_guard_count")
                if _is_real_number(summary.get("blocking_guard_count"))
                else sum(1 for g in guards if g.get("status") == "blocking")
            ),
            "required_next_step": summary.get("required_next_step"),
        },
        "warnings": warnings,
    }


# ── per-guard label map (sidecar-local; mirrors helper guard names) ─────

_GUARD_LABEL_CN: dict[str, str] = {
    "holdout_stability_guard": "跨窗口稳定性 guard",
    "net_benefit_guard": "净收益 guard",
}


_WARNING_LABEL_CN: dict[str, str] = {
    "missing_metrics": "保护层诊断缺数据，仅展示空状态。",
    "final_test_range_refusal": "已进入 final test 保留区间，相关数值仅作占位展示。",
}


# ── markdown renderer ────────────────────────────────────────────────────

def render_protection_layer_diagnostics_markdown(card_data: dict) -> str:
    """Render the card_data into a safe markdown string.

    Pure function. Empty string when ``card_data.visible`` is False.
    Output is grep-safe per Step 2G-8A.2 §1 forbidden-copy list (tests
    lock this).
    """
    cd = card_data if isinstance(card_data, dict) else {}
    if not cd.get("visible"):
        return ""

    lines: list[str] = []
    lines.append("**保护层诊断详情**")
    lines.append(
        "诊断信息已接入，但不等于自动升级；当前仍只允许复盘提示，"
        "不改变主推演方向，不构成交易指令。"
    )

    summary = _safe_dict(cd.get("summary"))
    next_step = summary.get("required_next_step")

    guards = _safe_list(cd.get("guards"))
    if guards:
        lines.append("")
        lines.append("**保护层 guard 列表**")
        for g in guards:
            if not isinstance(g, dict):
                continue
            name = g.get("name", "")
            label = _GUARD_LABEL_CN.get(name, name)
            status = g.get("status", "")
            message = g.get("message", "")
            reason = g.get("reason", "")
            evidence = _safe_dict(g.get("evidence"))
            lines.append(f"- **{label}**（{status}）：{message}")
            ev_str = " · ".join(_format_evidence(evidence))
            tail_parts = []
            if reason:
                tail_parts.append(f"reason=`{reason}`")
            if ev_str:
                tail_parts.append(f"_evidence:_ {ev_str}")
            if tail_parts:
                lines.append("  · " + " · ".join(tail_parts))

    lines.append("")
    lines.append("**接入状态（sidecar diagnostics 边界）**")
    for flag, _label in _FLAG_LABELS:
        lines.append(f"- {_flag_state_text(flag, bool(cd.get(flag)))}")

    blocked = bool(summary.get("hard_upgrade_blocked", True))
    display_only = bool(summary.get("display_only", True))
    blocking_count = summary.get("blocking_guard_count")
    state_bits: list[str] = []
    state_bits.append(
        "升级条件未满足" if blocked else "升级条件已满足（仍受 sidecar 范围限制）"
    )
    if display_only:
        state_bits.append("当前仅作展示")
    if _is_real_number(blocking_count):
        state_bits.append(f"blocking guards：{int(blocking_count)}")
    if state_bits:
        lines.append("")
        lines.append("· " + " · ".join(state_bits))

    warnings = _safe_list(cd.get("warnings"))
    if warnings:
        lines.append("")
        lines.append("**提示**")
        for w in warnings:
            if not isinstance(w, str) or not w:
                continue
            label = _WARNING_LABEL_CN.get(w, w)
            lines.append(f"- {label}")

    if next_step:
        lines.append("")
        lines.append(
            f"_待补条件：_ `{next_step}`（在此之前仍只允许复盘提示）"
        )

    return "\n".join(lines).strip() + "\n"
