"""ui/soft_metadata_renderer.py — pure-function renderer for soft_metadata.v1.

Step 2G-6A implementation of the dashboard / review display layer
specified by Step 2G-6 ([`tasks/step_2g6_soft_metadata_display_design.md`]
commit `0c5f421`). Translates a ``soft_metadata.v1`` dict (from
``services.soft_metadata_simulator.simulate_soft_metadata``) into a
**safe display model** — a plain Python dict that downstream UI code
(Streamlit / HTML / future surfaces) can render without re-deciding
copy or safety rules.

Step 2G-6 §3 / §11 contract:
- pure function: never reads DB / CSV / network; never imports Streamlit
  or any UI framework; never imports the simulator (input dict is the
  only data source)
- never imports ``yfinance`` / ``requests`` / ``longbridge`` / ``broker``
  / ``paper_trade``
- never imports ``services.confidence_engine`` / ``services.contradiction_engine``
  / ``services.risk_model``
- forbidden copy (Step 2G-6 §3.1) is NEVER produced — covered by a
  grep test in ``tests/test_soft_metadata_renderer.py``
- ``hard_exclusion_allowed=False`` is surfaced in every card's
  ``safety_note`` (Step 2G-6 §11.1)
- ``final_test_range_refusal`` warning is NEVER hidden (Step 2G-6 §11.5
  / §9.1)
- severity badge color is implied via ``badge_tone`` field
  (``"info"`` / ``"caution"``) — NEVER ``"danger"`` / ``"red"``
  (Step 2G-6 §11.4 / §11.10)

Public API:
    render_soft_metadata_card_data(soft_metadata, *, context="predict",
                                   include_debug=False) -> dict
    render_soft_metadata_markdown(card_data) -> str
"""
from __future__ import annotations

from typing import Any


# ── safety / copy constants ─────────────────────────────────────────────

# Step 2G-6 §3.1 — these must NEVER appear in any rendered output.
# Tests grep the full card_data + markdown for these tokens.
FORBIDDEN_COPY_TOKENS: tuple[str, ...] = (
    "禁止交易", "强制否定", "必须不做",
    "hard exclusion", "forced exclusion",
    "自动拦截", "no_trade",
    "卖出信号", "做空信号", "看空信号",
    "否决主推演", "推翻主推演",
    "强制平仓", "force close",
    "阻止下单", "block order",
)

# Step 2G-6 §3.2 — recommended phrasing used to construct safe copy.
_SAFETY_NOTE_DEFAULT = "仅供复盘参考，不改变主推演方向，不构成交易指令。"
_SAFETY_NOTE_TRADE_BOUND = (
    "本卡片为复盘 metadata，不是交易指令；07 段策略边界（不交易）不变。"
)

_TITLE_PREDICT = "结构性偏多风险提示"
_TITLE_REVIEW = "结构性偏多归因维度（候选）"
_SUBTITLE_REVIEW_NONE = "本次未触发 soft metadata（候选归因维度为空）。"
_SUBTITLE_FINAL_TEST_REFUSAL = (
    "本预测进入 final test 保留区间，soft_metadata 已暂停（防止参数污染）。"
    "见 tasks/step_2g4_5_soft_metadata_schema_review_checkpoint.md §13。"
)

# Severity → badge / tone mapping (Step 2G-6 §3.3 / §11.4 / §11.10)
# tone is for downstream UI to choose color: NEVER "danger" / "red" /
# "warning" for medium — keep it amber/caution at most.
_SEVERITY_BADGE: dict[str, dict[str, str]] = {
    "low": {"badge_text": "信息提示", "badge_tone": "info"},
    "medium": {"badge_text": "复核建议", "badge_tone": "caution"},
    # "none" only valid in summary.max_severity, never as signals[i].severity
    "none": {"badge_text": "无信号", "badge_tone": "info"},
}

# Per-candidate copy templates. Each template is a function of the
# signal dict so we can interpolate measured values; callers should
# NOT extend this map without going through Step 2G-6 review.
_KNOWN_SIGNAL_NAMES = frozenset({
    "r4_overextension",
    "bullish_high_pos20_residual",
})


# ── input coercion helpers (local; do not depend on simulator) ──────────

def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _is_real_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    return isinstance(value, (int, float))


def _format_rate(value: Any) -> str:
    """Percent with one decimal; "n/a" when unparseable."""
    if not _is_real_number(value):
        return "n/a"
    return f"{float(value) * 100:.1f}%"


def _format_signed_pp(value: Any) -> str:
    """Signed percentage points (×100); "n/a" when unparseable."""
    if not _is_real_number(value):
        return "n/a"
    return f"{float(value) * 100:+.1f}pp"


def _resolve_context(context: Any) -> str:
    if context not in ("predict", "review"):
        return "predict"
    return context


# ── per-signal copy builders ────────────────────────────────────────────

def _r4_summary_text() -> str:
    return (
        "历史上，AVGO 在短期明显跑赢 SOXX 且处于 20 日区间高位时，"
        "系统容易继续判偏多，但实际次日上涨比例偏低。"
        "历史样本中该结构容易高估上涨概率。"
    )


def _residual_summary_text() -> str:
    return (
        "高位偏多结构存在一定过热风险，但本残差信号（剔除 R4 后）"
        "的命中率接近随机，主要用于上下文提示。"
    )


def _generic_summary_text(signal_name: str) -> str:
    """Fallback for unknown signal names — graceful degradation per spec."""
    return (
        f"未识别的 metadata 信号 ({signal_name})；按 review_only 处理，"
        "不改变主推演方向。"
    )


def _summary_text_for(signal: dict[str, Any]) -> str:
    name = signal.get("name")
    if name == "r4_overextension":
        return _r4_summary_text()
    if name == "bullish_high_pos20_residual":
        return _residual_summary_text()
    return _generic_summary_text(str(name))


def _metrics_for(signal: dict[str, Any]) -> list[dict[str, str]]:
    """Default-view metrics list (Step 2G-6 §6.2 / §7.2)."""
    metrics = _as_dict(signal.get("historical_metrics_in_sample"))
    return [
        {"label": "历史命中率", "value": _format_rate(metrics.get("accuracy"))},
        {"label": "看多 vs 实际上涨差",
         "value": _format_signed_pp(metrics.get("bias_gap"))},
        {"label": "误杀率（若强制排除）",
         "value": _format_rate(metrics.get("false_exclusion_rate"))},
        {"label": "净收益（若强制排除）",
         "value": _format_signed_pp(metrics.get("net_benefit"))},
    ]


def _safety_note_for(signal: dict[str, Any]) -> str:
    """Each card's safety note must surface
    ``hard_exclusion_allowed=false`` semantics (Step 2G-6 §11.1).

    We don't read ``hard_exclusion_allowed`` from the signal directly
    (it lives on ``summary``); instead the renderer's invariant is that
    the safety note ALWAYS communicates "不改变主推演方向 / 不构成交易
    指令" regardless of any caller-supplied data — this prevents a buggy
    upstream from silently writing a misleading safety note.
    """
    return f"{_SAFETY_NOTE_DEFAULT} {_SAFETY_NOTE_TRADE_BOUND}"


# ── per-signal expandable details ───────────────────────────────────────

def _expandable_details_for(signal: dict[str, Any]) -> list[dict[str, Any]]:
    """Step 2G-6 §6.3 / §7.3 — "为什么不强制否定" expandable block."""
    metrics = _as_dict(signal.get("historical_metrics_in_sample"))
    raw = _as_dict(signal.get("raw_features"))
    ctx = _as_dict(signal.get("trigger_context"))
    holdout = signal.get("holdout_status")

    fer = metrics.get("false_exclusion_rate")
    nb = metrics.get("net_benefit")

    lines: list[dict[str, str]] = []
    if _is_real_number(fer):
        lines.append({
            "label": "为什么不强制排除",
            "text": (
                f"若强制排除该结构，将同时漏掉 {_format_rate(fer)} 仍真涨"
                "的样本（gate ≤ 10.0%）—— 误杀率过高。"
            ),
        })
    if _is_real_number(nb):
        if float(nb) < 0:
            lines.append({
                "label": "净收益为负",
                "text": (
                    f"若强制排除，整体准确率不升反降 "
                    f"{_format_signed_pp(nb)} —— 比保持现状还差。"
                ),
            })
        else:
            lines.append({
                "label": "净收益不达 gate",
                "text": (
                    f"若强制排除，整体准确率仅提升 {_format_signed_pp(nb)}"
                    "（gate ≥ +5.0pp）—— 收益不够。"
                ),
            })
    if holdout == "FAIL":
        lines.append({
            "label": "跨窗口 holdout",
            "text": (
                "Step 3A-4 / 3B-1 的跨窗口 holdout 已 FAIL —— 该结构在"
                "样本外不稳定。"
            ),
        })

    breakdown = _as_list(signal.get("hard_forbidden_breakdown"))
    if breakdown:
        lines.append({
            "label": "原始 breakdown",
            "text": " / ".join(str(item) for item in breakdown),
        })

    # Trigger context echo for review归因 use.
    fd = ctx.get("final_direction")
    cl = ctx.get("confidence_level")
    psr = ctx.get("primary_score_raw")
    peer = ctx.get("peer_subtype")
    branch = ctx.get("matched_or_branch")
    ctx_bits: list[str] = []
    if fd:
        ctx_bits.append(f"主推演方向={fd}")
    if cl:
        ctx_bits.append(f"置信度={cl}")
    if _is_real_number(psr):
        ctx_bits.append(f"primary_score_raw={float(psr):.2f}")
    if peer:
        ctx_bits.append(f"peer_subtype={peer}")
    if branch:
        ctx_bits.append(f"R4 OR 分支={branch}")
    if ctx_bits:
        lines.append({
            "label": "触发上下文",
            "text": " / ".join(ctx_bits),
        })

    if raw:
        raw_bits: list[str] = []
        if _is_real_number(raw.get("avgo_minus_soxx_20d")):
            raw_bits.append(
                f"avgo−SOXX 20d={float(raw['avgo_minus_soxx_20d']):.2f}pp"
            )
        if _is_real_number(raw.get("pos20")):
            raw_bits.append(f"pos20={float(raw['pos20']):.4f}")
        if raw_bits:
            lines.append({
                "label": "raw_features",
                "text": " / ".join(raw_bits),
            })

    return lines


# ── card builder ────────────────────────────────────────────────────────

def _build_card(signal: dict[str, Any]) -> dict[str, Any] | None:
    """Build one display card from a signal dict.

    Returns None if the signal is fundamentally unusable (not a dict).
    Unknown ``name`` values still produce a card via the generic
    fallback (graceful degradation, per Step 2G-6 §11.11 spirit).
    """
    if not isinstance(signal, dict):
        return None

    name = signal.get("name") or "<unknown>"
    label = signal.get("display_label")
    if not isinstance(label, str) or not label.strip():
        # Unknown signals get a neutral placeholder label rather than
        # blank — UI layers should still be able to render something.
        label = f"未识别 metadata 信号 ({name})"

    severity = signal.get("severity")
    if severity not in ("low", "medium"):
        # Step 2G-4.5 §8 + Step 2G-6 §3.1: never accept "high" / "hard".
        # Coerce anything else (including "high", "hard", None, garbage)
        # to "medium" — the conservative default — and add a warning
        # at the summary layer (handled in render_soft_metadata_card_data).
        severity = "medium"
    badge = _SEVERITY_BADGE.get(severity, _SEVERITY_BADGE["medium"])

    return {
        "name": str(name),
        "display_label": label,
        "severity": severity,
        "badge_text": badge["badge_text"],
        "badge_tone": badge["badge_tone"],
        "summary_text": _summary_text_for(signal),
        "metrics": _metrics_for(signal),
        "safety_note": _safety_note_for(signal),
        "expandable_details": _expandable_details_for(signal),
        "recommended_action": signal.get("recommended_action") or "review_only",
        "holdout_status": signal.get("holdout_status"),
    }


# ── debug builder ───────────────────────────────────────────────────────

def _build_debug(soft_metadata: dict[str, Any]) -> dict[str, Any]:
    """Step 2G-6 §10 debug view — surface raw fields for developers."""
    return {
        "schema_version": soft_metadata.get("schema_version"),
        "metrics_source": soft_metadata.get("metrics_source"),
        "metrics_window": _as_dict(soft_metadata.get("metrics_window")),
        "metrics_computed_at": soft_metadata.get("metrics_computed_at"),
        "summary": _as_dict(soft_metadata.get("summary")),
        "signals_raw": _as_list(soft_metadata.get("signals")),
    }


# ── public API ──────────────────────────────────────────────────────────

def render_soft_metadata_card_data(
    soft_metadata: dict,
    *,
    context: str = "predict",
    include_debug: bool = False,
) -> dict[str, Any]:
    """Translate ``soft_metadata.v1`` dict into a safe display model.

    Pure function. No DB / network / Streamlit. Always returns a dict;
    never raises. Forbidden copy (Step 2G-6 §3.1) is never produced.
    """
    sm = _as_dict(soft_metadata)
    surface = _resolve_context(context)
    signals = _as_list(sm.get("signals"))
    summary = _as_dict(sm.get("summary"))
    summary_warnings = _as_list(summary.get("warnings"))

    cards: list[dict[str, Any]] = []
    for raw in signals[:3]:  # Step 2G-4.5 §9.3 — max 3 cards
        card = _build_card(raw)
        if card is not None:
            cards.append(card)

    warnings: list[str] = [str(w) for w in summary_warnings if w]

    # Renderer-level integrity checks added as developer warnings.
    declared_count = summary.get("signal_count")
    if isinstance(declared_count, int) and declared_count != len(_as_list(sm.get("signals"))):
        warnings.append(
            "renderer_warning: summary.signal_count "
            f"({declared_count}) != len(signals) "
            f"({len(_as_list(sm.get('signals')))})"
        )
    if any(
        isinstance(s, dict) and s.get("severity") not in ("low", "medium")
        for s in signals
    ):
        warnings.append(
            "renderer_warning: signal severity coerced to 'medium' "
            "(input contained non-{low,medium} value; spec disallows)"
        )

    has_final_test_refusal = "final_test_range_refusal" in warnings
    title = (
        _TITLE_PREDICT if surface == "predict" else _TITLE_REVIEW
    )
    subtitle = ""

    # Visibility decision matrix (Step 2G-6 §4 / §9 / §11.5 / §11.7)
    if cards:
        visible = True
        if surface == "review":
            subtitle = "命中以下结构性 metadata；候选归因维度，**不是**确定原因。"
    else:
        if has_final_test_refusal:
            visible = True
            subtitle = _SUBTITLE_FINAL_TEST_REFUSAL
        elif surface == "predict" and not warnings:
            visible = False
            subtitle = ""
        elif surface == "review":
            visible = True
            subtitle = _SUBTITLE_REVIEW_NONE
        else:
            # predict + warnings (other than refusal) → folded dev hint
            visible = True
            subtitle = "未触发 metadata（仅有开发者 warning）。"

    debug = _build_debug(sm) if include_debug else None

    return {
        "visible": visible,
        "title": title,
        "subtitle": subtitle,
        "cards": cards,
        "debug": debug,
        "warnings": warnings,
    }


# ── markdown renderer (optional secondary) ──────────────────────────────

def render_soft_metadata_markdown(card_data: dict) -> str:
    """Render a markdown string from card_data.

    Pure function. The markdown is intentionally minimal and avoids
    heavy formatting so dashboard / review surfaces can choose their
    own typography. Always returns a string; empty when not visible.
    """
    cd = _as_dict(card_data)
    if not cd.get("visible"):
        return ""

    lines: list[str] = []
    title = cd.get("title") or ""
    subtitle = cd.get("subtitle") or ""
    if title:
        lines.append(f"### {title}")
    if subtitle:
        lines.append(subtitle)

    for card in _as_list(cd.get("cards")):
        c = _as_dict(card)
        label = c.get("display_label") or "未命名 metadata"
        badge = c.get("badge_text") or ""
        lines.append("")
        lines.append(f"**{label}** _{badge}_" if badge else f"**{label}**")
        summary_text = c.get("summary_text") or ""
        if summary_text:
            lines.append(summary_text)
        metric_bits = []
        for m in _as_list(c.get("metrics")):
            md = _as_dict(m)
            metric_bits.append(f"{md.get('label', '')}：{md.get('value', '')}")
        if metric_bits:
            lines.append(" · ".join(metric_bits))
        safety = c.get("safety_note") or ""
        if safety:
            lines.append(f"_说明：_{safety}")

    warnings = _as_list(cd.get("warnings"))
    if warnings:
        lines.append("")
        lines.append("_warnings:_ " + "; ".join(str(w) for w in warnings))

    return "\n".join(lines).strip() + "\n"
