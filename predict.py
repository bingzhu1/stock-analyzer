# -*- coding: utf-8 -*-
"""
predict.py - Lightweight Predict v2 layer for the AVGO analyzer.

LEGACY_COMPATIBILITY_WRAPPER (RISK-8 / 11E):
predict.py is a legacy compatibility wrapper retained for backward
compatibility with 9+ active importers (UI tabs, scripts, log_store,
projection_orchestrator V1, review_agent, contract_replay_writer, ...).
Core projection, exclusion, confidence, and final report responsibilities
are being migrated to contract-separated services
(``services/projection_entrypoint.py`` /
``services/projection_orchestrator_v2.py`` /
``services/final_decision.py`` /
``services/confidence_evaluator.py`` / etc.).

This file MUST NOT add new cross-system judgment logic. The 12E split
proceeds in stages:

    X1 (this commit) — mark as legacy + add source_mapping foundation
    X2  — wire final_confidence from confidence_result (depends on 11C-A)
    X3  — wire summary from final_report.combined_user_summary (depends on 11B)
    X4  — delegate primary/peer/final to V2 path (depends on 11A/11B/11C-B)
    X5  — Step 14 cleanup of dead helpers

X1 is purely about declaration and metadata: it does not migrate any
projection / aggregator / confidence logic, does not change any legacy
field value, and does not delete any legacy field.

See:
- tasks/record_06_three_system_independence_principle.md
- tasks/record_07a_projection_system_contract.md
- tasks/record_07c_confidence_system_contract.md
- tasks/record_07d_final_report_aggregator_contract.md
- tasks/record_11e_predict_py_split_design.md
- tasks/record_11h_boundary_enforcement_design_signoff.md
"""

from __future__ import annotations

import threading
from datetime import datetime
from typing import Any, TypedDict


# ---------------------------------------------------------------------------
# Legacy wrapper metadata (RISK-8 / 11E X1)
# ---------------------------------------------------------------------------

PREDICT_LEGACY_WRAPPER_KIND = "legacy_predict_wrapper"
PREDICT_LEGACY_WRAPPER_VERSION = "predict_legacy_wrapper.v1"


_LEGACY_COMPAT_CONFIDENCE_LEVELS: tuple[str, ...] = ("low", "medium", "high", "unknown")


def _extract_compat_confidence(confidence_result: dict[str, Any] | None) -> str:
    """Read the legacy compat ``final_confidence`` value strictly from a
    ``confidence_system_result.v1`` payload.

    Boundary contract (07C / 11C / 11E X2): the wrapper MUST NOT recompute
    confidence. ``run_predict`` calls this helper to project
    ``confidence_result.combined_confidence.level`` onto the legacy
    ``final_confidence`` / ``confidence`` fields. Anything not in the
    fixed level set degrades to ``"unknown"`` — never falls back to a
    heuristic.
    """
    if not isinstance(confidence_result, dict):
        return "unknown"
    combined = confidence_result.get("combined_confidence")
    if not isinstance(combined, dict):
        return "unknown"
    raw = combined.get("level")
    if not isinstance(raw, str):
        return "unknown"
    level = raw.strip().lower()
    if level in _LEGACY_COMPAT_CONFIDENCE_LEVELS:
        return level
    return "unknown"


def _legacy_source_mapping() -> dict[str, str]:
    """Source-of-truth mapping for the legacy compat fields surfaced by
    ``run_predict``.

    X2 wires ``compat_final_confidence`` and ``compat_confidence`` to
    ``confidence_result.combined_confidence.level`` (or ``unknown`` when
    no confidence_result is supplied). Other entries remain pending until
    stages X3 / X4 migrate the corresponding fields.
    """
    return {
        "compat_final_bias": "legacy_predict_path (pending X4 migration to final_decision.final_direction)",
        "compat_final_confidence": "confidence_result.combined_confidence.level or unknown",
        "compat_confidence": "confidence_result.combined_confidence.level or unknown",
        "compat_prediction_summary": "legacy_predict_path (pending X4 migration to final_report.combined_user_summary)",
        "compat_primary_direction": "legacy_predict_path (pending X4 migration to main_projection.predicted_top1.state)",
        "compat_peer_adjustment": "legacy_predict_path (pending X4 migration to V2 peer_adjustment)",
        "compat_path_risk": "legacy_predict_path (pending X4 migration to final_decision.risk_level)",
    }


def _legacy_deprecation_notes() -> list[str]:
    """Human-readable deprecation hints attached to every ``run_predict``
    payload. Surfaced through ``deprecation_notes``."""
    return [
        "predict.py is a legacy compatibility wrapper (RISK-8 / 11E).",
        "Stage 12E-X1 marks the wrapper and adds source_mapping; X2 wires final_confidence from confidence_result.",
        "New code should call services/projection_entrypoint.run_projection_entrypoint (V2) directly.",
        "Remaining compatibility field values will be re-sourced from V2 / final_report in stages X3..X4.",
        "Wrapper must not introduce new judgment, recompute confidence, flip direction, or fabricate summary text.",
    ]


def _legacy_wrapper_metadata() -> dict[str, Any]:
    return {
        "wrapper_kind": PREDICT_LEGACY_WRAPPER_KIND,
        "wrapper_version": PREDICT_LEGACY_WRAPPER_VERSION,
        "legacy_compatibility": True,
        "source_mapping": _legacy_source_mapping(),
        "deprecation_notes": _legacy_deprecation_notes(),
    }


# Re-entry guard for the projection_three_systems attachment (Task 108).
# The legacy projection orchestrator's _build_predict_result calls run_predict,
# and run_predict (PR-I / Task 104) attaches projection_three_systems by calling
# run_projection_v2, which itself goes back through the legacy orchestrator —
# so without this guard each replay case fans out into ~30 stack levels of
# redundant CSV-load + match-table + scan + run_predict work before Python's
# recursion limit aborts the deepest frame. The guard turns the inner re-entry
# into a single deterministic degraded payload.
_projection_three_systems_attachment_state = threading.local()


class PredictResult(TypedDict):
    symbol: str
    predict_timestamp: str
    scan_bias: str
    scan_confidence: str
    research_bias_adjustment: str
    final_bias: str
    final_confidence: str
    open_tendency: str
    close_tendency: str
    prediction_summary: str
    supporting_factors: list[str]
    conflicting_factors: list[str]
    notes: str
    path_risk: str
    peer_path_risk_adjustment: dict[str, Any]
    primary_projection: dict[str, Any]
    peer_adjustment: dict[str, Any]
    final_projection: dict[str, Any]


_CONF_LEVELS = ("low", "medium", "high")
_REINFORCING_ADJUSTMENTS = {"reinforce_bullish", "reinforce_bearish"}
_WEAKENING_ADJUSTMENTS = {"weaken_bullish", "weaken_bearish"}
_DIRECTIONAL_ADJUSTMENTS = _REINFORCING_ADJUSTMENTS | _WEAKENING_ADJUSTMENTS
_PEER_SYMBOLS = ("NVDA", "SOXX", "QQQ")
_PRIMARY_LOOKBACK_DAYS = 20
_GAP_THRESHOLD = 0.005
_VOLUME_EXPANDING_THRESHOLD = 1.10
_VOLUME_SHRINKING_THRESHOLD = 0.90

_OPEN_TENDENCY_TO_LABEL = {
    "gap_up_bias": "高开",
    "gap_down_bias": "低开",
    "flat_bias": "平开",
    "unclear": None,
}
_CLOSE_TENDENCY_TO_LABEL = {
    "close_strong": "收涨",
    "close_weak": "收跌",
    "range": "平收",
    "unclear": None,
}
_PATH_LABEL_MAP = {
    ("高开", "收涨"): "高开高走",
    ("高开", "收跌"): "高开低走",
    ("高开", "平收"): "高开震荡",
    ("低开", "收涨"): "低开高走",
    ("低开", "收跌"): "低开低走",
    ("低开", "平收"): "低开震荡",
    ("平开", "收涨"): "平开走高",
    ("平开", "收跌"): "平开走低",
    ("平开", "平收"): "平开震荡",
}

# ── Step 1A contract 02 enums (avgo_primary_projection) ─────────────────────
# Mirrors services/projection_output_contract.py — kept local so that
# build_primary_projection can self-publish contract-aligned fields without
# depending on the adapter layer.
_BIAS_TO_DIRECTION_CN = {
    "bullish": "偏多",
    "bearish": "偏空",
    "neutral": "中性",
    "unavailable": "中性",
}
_PRED_CLOSE_TO_CONTRACT = {
    "收涨": "收涨",
    "收跌": "收跌",
    "平收": "收平",  # legacy label "平收" → contract enum "收平"
}
_VALID_CONFIDENCE_RAW = frozenset({"high", "medium", "low"})


def _direction_cn_from_bias(bias: Any) -> str:
    return _BIAS_TO_DIRECTION_CN.get(str(bias), "中性")


def _open_projection_from_pred_open(pred_open: Any) -> str:
    if pred_open in {"高开", "平开", "低开"}:
        return pred_open
    return "平开"


def _intraday_path_from_pred_path(pred_path: Any) -> str:
    if not isinstance(pred_path, str) or not pred_path:
        return "震荡"
    if "高走" in pred_path or "走高" in pred_path:
        return "高走"
    if "低走" in pred_path or "走低" in pred_path:
        return "低走"
    return "震荡"


def _close_projection_from_pred_close(pred_close: Any) -> str:
    return _PRED_CLOSE_TO_CONTRACT.get(str(pred_close), "收平") if pred_close else "收平"


def _five_state_from(direction_cn: str, close_proj: str) -> str:
    """Conservative: never claim 大涨/大跌 from primary_projection alone."""
    if direction_cn == "偏多" and close_proj == "收涨":
        return "小涨"
    if direction_cn == "偏空" and close_proj == "收跌":
        return "小跌"
    return "震荡"


def _confidence_raw(confidence: Any) -> str:
    return confidence if confidence in _VALID_CONFIDENCE_RAW else "low"


# ── Step 1A contract 03 enums (peer_confirmation_adjustment) ────────────────
# bias-aware translation: a peer vote is taken in the context of primary bias,
# so "confirm" means the peer's relative strength supports primary direction.
_VOTE_TO_PEER_SIGNAL = {
    "confirm": "reinforce",
    "oppose": "weaken",
    "mixed": "neutral",
    "unavailable": "unknown",
}
_ADJUSTMENT_DIRECTION_TO_PEER_LABEL = {
    "reinforce": "upgrade",
    "weaken": "downgrade",
    "neutral_primary": "flip_to_neutral",
    "neutral": "hold",
}


def _peer_signal_from_vote(vote: Any) -> str:
    return _VOTE_TO_PEER_SIGNAL.get(str(vote), "unknown")


def _peer_alignment_from_counts(confirm_count: int, oppose_count: int) -> str:
    if confirm_count >= 3 and oppose_count == 0:
        return "all_reinforce"
    if oppose_count >= 3 and confirm_count == 0:
        return "all_weaken"
    if confirm_count == 0 and oppose_count == 0:
        return "insufficient"
    return "mixed"


def _peer_adjustment_label_from_direction(direction: Any) -> str:
    return _ADJUSTMENT_DIRECTION_TO_PEER_LABEL.get(str(direction), "hold")


# ── Step 1A contract 06 enums (final_projection) ────────────────────────────
_CONFIDENCE_TO_PROBABILITY_BUCKET = {
    "high": "≥70%",
    "medium": "55–70%",
    "low": "45–55%",
}


def _probability_bucket_from_confidence(confidence: Any) -> str:
    return _CONFIDENCE_TO_PROBABILITY_BUCKET.get(str(confidence), "45–55%")


def _raise_confidence(confidence: str) -> str:
    if confidence == "low":
        return "medium"
    if confidence == "medium":
        return "high"
    return "high"


def _lower_confidence(confidence: str) -> str:
    if confidence == "high":
        return "medium"
    return "low"


def _normalize_confidence(confidence: str) -> str:
    return confidence if confidence in _CONF_LEVELS else "low"


def _bias_from_score(score: float) -> str:
    if score > 0.5:
        return "bullish"
    if score < -0.5:
        return "bearish"
    return "neutral"


def _confidence_from_score(score: float) -> str:
    abs_score = abs(score)
    if abs_score >= 2.0:
        return "high"
    if abs_score >= 1.0:
        return "medium"
    return "low"


def _open_tendency(scan_result: dict[str, Any]) -> str:
    gap_state = str(scan_result.get("avgo_gap_state", "unknown"))
    if gap_state == "gap_up":
        return "gap_up_bias"
    if gap_state == "gap_down":
        return "gap_down_bias"
    if gap_state == "flat":
        return "flat_bias"
    return "unclear"


def _close_tendency(scan_result: dict[str, Any]) -> str:
    intraday_state = str(scan_result.get("avgo_intraday_state", "unknown"))
    if intraday_state == "high_go":
        return "close_strong"
    if intraday_state == "low_go":
        return "close_weak"
    if intraday_state == "range":
        return "range"
    return "unclear"


def _pred_labels(open_tendency: str, close_tendency: str) -> dict[str, str | None]:
    pred_open = _OPEN_TENDENCY_TO_LABEL.get(open_tendency)
    pred_close = _CLOSE_TENDENCY_TO_LABEL.get(close_tendency)
    pred_path = _PATH_LABEL_MAP.get((pred_open, pred_close)) if pred_open and pred_close else None
    return {
        "pred_open": pred_open,
        "pred_path": pred_path,
        "pred_close": pred_close,
    }


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _recent_20_summary(rows: Any) -> dict[str, Any]:
    if not isinstance(rows, list):
        return {"sample_count": 0}

    clean_rows = [row for row in rows if isinstance(row, dict)]
    closes = [
        _as_float(row.get("Close"))
        for row in clean_rows
        if _as_float(row.get("Close")) is not None
    ]
    c_moves = [
        _as_float(row.get("C_move"))
        for row in clean_rows
        if _as_float(row.get("C_move")) is not None
    ]
    o_gaps = [
        _as_float(row.get("O_gap"))
        for row in clean_rows
        if _as_float(row.get("O_gap")) is not None
    ]
    v_ratios = [
        _as_float(row.get("V_ratio"))
        for row in clean_rows
        if _as_float(row.get("V_ratio")) is not None
    ]

    ret = None
    if len(closes) >= 2 and closes[0] not in (None, 0):
        ret = (closes[-1] - closes[0]) / closes[0]

    up_days = sum(1 for move in c_moves if move > 0)
    down_days = sum(1 for move in c_moves if move < 0)
    gap_up_days = sum(1 for gap in o_gaps if gap > 0.005)
    gap_down_days = sum(1 for gap in o_gaps if gap < -0.005)

    return {
        "sample_count": len(clean_rows),
        "first_date": clean_rows[0].get("Date") if clean_rows else None,
        "last_date": clean_rows[-1].get("Date") if clean_rows else None,
        "close_return": ret,
        "up_days": up_days,
        "down_days": down_days,
        "gap_up_days": gap_up_days,
        "gap_down_days": gap_down_days,
        "last_o_gap": _as_float(clean_rows[-1].get("O_gap")) if clean_rows else None,
        "last_c_move": _as_float(clean_rows[-1].get("C_move")) if clean_rows else None,
        "last_v_ratio": _as_float(clean_rows[-1].get("V_ratio")) if clean_rows else None,
        "avg_c_move": sum(c_moves) / len(c_moves) if c_moves else None,
        "avg_o_gap": sum(o_gaps) / len(o_gaps) if o_gaps else None,
        "avg_v_ratio": sum(v_ratios) / len(v_ratios) if v_ratios else None,
    }


def _gap_state_from_value(value: float | None) -> str:
    if value is None:
        return "unknown"
    if value > _GAP_THRESHOLD:
        return "gap_up"
    if value < -_GAP_THRESHOLD:
        return "gap_down"
    return "flat"


def _intraday_state_from_value(value: float | None) -> str:
    if value is None:
        return "unknown"
    if value > _GAP_THRESHOLD:
        return "high_go"
    if value < -_GAP_THRESHOLD:
        return "low_go"
    return "range"


def _volume_state_from_value(value: float | None) -> str:
    if value is None:
        return "unknown"
    if value > _VOLUME_EXPANDING_THRESHOLD:
        return "expanding"
    if value < _VOLUME_SHRINKING_THRESHOLD:
        return "shrinking"
    return "normal"


def _trend_state_from_recent_summary(recent_summary: dict[str, Any]) -> str:
    close_return = recent_summary.get("close_return")
    if isinstance(close_return, float):
        if close_return > 0.02:
            return "bullish"
        if close_return < -0.02:
            return "bearish"
    up_days = recent_summary.get("up_days", 0)
    down_days = recent_summary.get("down_days", 0)
    if up_days > down_days:
        return "bullish"
    if down_days > up_days:
        return "bearish"
    return "neutral"


def _primary_input_boundary(fallback_scan_states_used: bool) -> dict[str, Any]:
    return {
        "raw_window": "avgo_recent_20",
        "lookback_days": _PRIMARY_LOOKBACK_DAYS,
        "direct_recent_20_fields": [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
            "O_gap",
            "C_move",
            "V_ratio",
        ],
        "direct_recent_20_derived_features": [
            "last_o_gap",
            "last_c_move",
            "last_v_ratio",
            "close_return",
            "up_days",
            "down_days",
            "gap_up_days",
            "gap_down_days",
        ],
        "recent_20_direct_scan_states": [
            "avgo_gap_state",
            "avgo_intraday_state",
            "avgo_volume_state",
        ],
        "not_direct_recent_20_scan_states": [
            "avgo_price_state",
        ],
        "excluded_inputs": [
            "historical_match_summary",
            "relative_strength_summary",
            "relative_strength_same_day_summary",
            "confirmation_state",
            "scan_bias",
            "scan_confidence",
        ],
        "fallback_scan_states_used": fallback_scan_states_used,
    }


def _path_risk_from_confidence(confidence: str) -> str:
    confidence = _normalize_confidence(confidence)
    if confidence == "high":
        return "low"
    if confidence == "medium":
        return "medium"
    return "high"


def _adjust_path_risk(primary_risk: str, adjustment_direction: str, confirm_count: int, oppose_count: int) -> tuple[str, str, list[str]]:
    reasons: list[str] = []
    risk_order = {"low": 0, "medium": 1, "high": 2}
    score = risk_order.get(primary_risk, 1)
    risk_direction = "unchanged"

    if adjustment_direction == "reinforce":
        score = max(0, score - 1)
        risk_direction = "lower"
        reasons.append(f"{confirm_count} peers confirm primary direction")
    elif adjustment_direction == "weaken":
        score = min(2, score + 1)
        risk_direction = "higher"
        reasons.append(f"{oppose_count} peers oppose primary direction")
    elif confirm_count and oppose_count:
        score = min(2, score + 1)
        risk_direction = "higher"
        reasons.append("peer evidence is mixed across confirmation and opposition")

    labels = {0: "low", 1: "medium", 2: "high"}
    return labels[score], risk_direction, reasons


def _summarize(final_bias: str, final_confidence: str, adjustment: str) -> str:
    if final_bias == "unavailable":
        return "Prediction unavailable: Scan result is missing. Run Scan before Predict."
    if adjustment == "missing_research":
        return f"Prediction is {final_bias} with {final_confidence} confidence, led by Scan only."
    return (
        f"Prediction is {final_bias} with {final_confidence} confidence after combining "
        f"Scan with Research adjustment {adjustment}."
    )


def build_primary_projection(
    scan_result: dict[str, Any] | None,
    research_result: dict[str, Any] | None = None,
    symbol: str = "AVGO",
) -> dict[str, Any]:
    """
    Build the first-stage AVGO-only projection.

    This stage intentionally does not use peer relative-strength,
    confirmation_state, scan_bias, scan_confidence, or historical matches. It
    scores AVGO's recent-20 raw window and directly derived features into a
    baseline direction.
    """
    scan = scan_result or {}
    if not scan_result:
        return {
            "status": "unavailable",
            "source": "avgo_recent_20_scan_context",
            "symbol": symbol,
            "lookback_days": _PRIMARY_LOOKBACK_DAYS,
            "peer_inputs_used": False,
            "final_bias": "unavailable",
            "final_confidence": "low",
            "open_tendency": "unclear",
            "close_tendency": "unclear",
            "pred_open": None,
            "pred_path": None,
            "pred_close": None,
            "score": 0.0,
            "signals": [],
            "direct_features": {},
            # Step 1A contract 02 fields (defaults for the unavailable branch).
            "primary_direction": "中性",
            "open_projection": "平开",
            "intraday_path_projection": "震荡",
            "close_projection": "收平",
            "five_state_projection": "震荡",
            "historical_sample_count": 0,
            "key_evidence": [],
            "primary_confidence_raw": "low",
            "input_boundary": _primary_input_boundary(fallback_scan_states_used=False),
            "notes": "Scan result is missing; primary projection cannot be computed.",
        }

    recent_20 = scan.get("avgo_recent_20", [])
    recent_summary = _recent_20_summary(recent_20)
    fallback_scan_states_used = recent_summary.get("sample_count", 0) == 0

    if fallback_scan_states_used:
        gap_state = str(scan.get("avgo_gap_state", "unknown"))
        intraday_state = str(scan.get("avgo_intraday_state", "unknown"))
        volume_state = str(scan.get("avgo_volume_state", "unknown"))
        trend_state = str(scan.get("avgo_price_state", "unknown"))
    else:
        gap_state = _gap_state_from_value(recent_summary.get("last_o_gap"))
        intraday_state = _intraday_state_from_value(recent_summary.get("last_c_move"))
        volume_state = _volume_state_from_value(recent_summary.get("last_v_ratio"))
        trend_state = _trend_state_from_recent_summary(recent_summary)

    score = 0.0
    signals: list[str] = []

    if gap_state == "gap_up":
        score += 1.0
        signals.append("avgo_gap_state=gap_up")
    elif gap_state == "gap_down":
        score -= 1.0
        signals.append("avgo_gap_state=gap_down")
    elif gap_state == "flat":
        signals.append("avgo_gap_state=flat")

    if intraday_state == "high_go":
        score += 1.0
        signals.append("avgo_intraday_state=high_go")
    elif intraday_state == "low_go":
        score -= 1.0
        signals.append("avgo_intraday_state=low_go")
    elif intraday_state == "range":
        signals.append("avgo_intraday_state=range")

    if volume_state == "expanding":
        score += 0.5
        signals.append("avgo_volume_state=expanding")
    elif volume_state == "shrinking":
        score -= 0.5
        signals.append("avgo_volume_state=shrinking")
    elif volume_state == "normal":
        signals.append("avgo_volume_state=normal")

    if trend_state == "bullish":
        score += 1.0
        signals.append("avgo_recent_20_trend=bullish")
    elif trend_state == "bearish":
        score -= 1.0
        signals.append("avgo_recent_20_trend=bearish")
    elif trend_state == "neutral":
        signals.append("avgo_recent_20_trend=neutral")

    close_return = recent_summary.get("close_return")
    if isinstance(close_return, float):
        if close_return > 0.02:
            score += 0.5
            signals.append("avgo_recent_20_return=positive")
        elif close_return < -0.02:
            score -= 0.5
            signals.append("avgo_recent_20_return=negative")

    if recent_summary.get("up_days", 0) > recent_summary.get("down_days", 0):
        score += 0.25
        signals.append("avgo_recent_20_up_days_majority")
    elif recent_summary.get("down_days", 0) > recent_summary.get("up_days", 0):
        score -= 0.25
        signals.append("avgo_recent_20_down_days_majority")

    final_bias = _bias_from_score(score)
    final_confidence = _confidence_from_score(score)
    open_tendency = {
        "gap_up": "gap_up_bias",
        "gap_down": "gap_down_bias",
        "flat": "flat_bias",
    }.get(gap_state, "unclear")
    close_tendency = {
        "high_go": "close_strong",
        "low_go": "close_weak",
        "range": "range",
    }.get(intraday_state, "unclear")
    labels = _pred_labels(open_tendency, close_tendency)

    # Step 1A contract 02 fields, derived from the same primary signals so
    # downstream consumers (adapter / contract validator) can read them
    # directly without re-translation. Logic is unchanged; this is additive.
    primary_direction = _direction_cn_from_bias(final_bias)
    open_projection = _open_projection_from_pred_open(labels.get("pred_open"))
    intraday_path_projection = _intraday_path_from_pred_path(labels.get("pred_path"))
    close_projection = _close_projection_from_pred_close(labels.get("pred_close"))
    five_state_projection = _five_state_from(primary_direction, close_projection)
    primary_confidence_raw = _confidence_raw(final_confidence)
    key_evidence = list(signals[:5])

    return {
        "status": "computed",
        "source": "avgo_recent_20_scan_context",
        "symbol": str(scan.get("symbol", symbol)),
        "lookback_days": _PRIMARY_LOOKBACK_DAYS,
        "peer_inputs_used": False,
        "final_bias": final_bias,
        "final_confidence": final_confidence,
        "open_tendency": open_tendency,
        "close_tendency": close_tendency,
        **labels,
        "score": score,
        "signals": signals,
        "direct_features": {
            "gap_state": gap_state,
            "intraday_state": intraday_state,
            "volume_state": volume_state,
            "recent_20_trend_state": trend_state,
        },
        "primary_direction": primary_direction,
        "open_projection": open_projection,
        "intraday_path_projection": intraday_path_projection,
        "close_projection": close_projection,
        "five_state_projection": five_state_projection,
        "historical_sample_count": 0,
        "key_evidence": key_evidence,
        "primary_confidence_raw": primary_confidence_raw,
        "recent_20_summary": recent_summary,
        "input_boundary": _primary_input_boundary(fallback_scan_states_used),
        "notes": (
            "Primary projection uses AVGO recent-20 raw window and directly "
            "derived AVGO features; historical matches and peer inputs are excluded."
        ),
    }


def _peer_layer_vote(primary_bias: str, relative_strength: str) -> str:
    if relative_strength == "unavailable":
        return "unavailable"
    if primary_bias == "bullish":
        if relative_strength == "stronger":
            return "confirm"
        if relative_strength == "weaker":
            return "oppose"
    elif primary_bias == "bearish":
        if relative_strength == "weaker":
            return "confirm"
        if relative_strength == "stronger":
            return "oppose"
    return "mixed"


def _combine_peer_votes(votes: set[str]) -> str:
    directional = votes - {"unavailable"}
    if not directional:
        return "unavailable"
    if "confirm" in directional and "oppose" in directional:
        return "mixed"
    if "confirm" in directional:
        return "confirm"
    if "oppose" in directional:
        return "oppose"
    return "mixed"


def apply_peer_adjustment(
    primary_projection: dict[str, Any],
    scan_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Use NVDA / SOXX / QQQ relative strength to adjust the primary view."""
    scan = scan_result or {}
    primary_bias = str(primary_projection.get("final_bias", "neutral"))
    primary_confidence = _normalize_confidence(str(primary_projection.get("final_confidence", "low")))
    rs_5d = scan.get("relative_strength_summary") or {}
    rs_same_day = scan.get("relative_strength_same_day_summary") or {}
    peer_raw_features = scan.get("peer_relative_strength_features") or {}
    if not isinstance(peer_raw_features, dict):
        peer_raw_features = {}

    adjustments: list[dict[str, Any]] = []
    confirm_count = 0
    oppose_count = 0

    for peer in _PEER_SYMBOLS:
        key = f"vs_{peer.lower()}"
        five_day = str(rs_5d.get(key, "unavailable"))
        same_day = str(rs_same_day.get(key, "unavailable"))
        vote = _combine_peer_votes({
            _peer_layer_vote(primary_bias, five_day),
            _peer_layer_vote(primary_bias, same_day),
        })
        if vote == "confirm":
            confirm_count += 1
        elif vote == "oppose":
            oppose_count += 1
        adjustments.append({
            "peer": peer,
            "five_day_relative_strength": five_day,
            "same_day_relative_strength": same_day,
            "vote": vote,
        })

    adjusted_bias = primary_bias
    adjusted_confidence = primary_confidence
    adjustment_direction = "neutral"

    if primary_bias in {"bullish", "bearish"}:
        if confirm_count >= 2:
            adjustment_direction = "reinforce"
            adjusted_confidence = _raise_confidence(primary_confidence)
        elif oppose_count >= 2:
            adjustment_direction = "weaken"
            adjusted_confidence = _lower_confidence(primary_confidence)
            if primary_confidence == "low":
                adjusted_bias = "neutral"
    else:
        adjustment_direction = "neutral_primary"

    primary_path_risk = _path_risk_from_confidence(primary_confidence)
    adjusted_path_risk, path_risk_direction, path_risk_reasons = _adjust_path_risk(
        primary_path_risk,
        adjustment_direction,
        confirm_count,
        oppose_count,
    )

    # Step 1A contract 03 fields, derived from the same vote / count signals.
    # Logic above is unchanged; this section is purely additive translation.
    votes_by_peer = {entry["peer"]: entry["vote"] for entry in adjustments}
    nvda_signal = _peer_signal_from_vote(votes_by_peer.get("NVDA"))
    soxx_signal = _peer_signal_from_vote(votes_by_peer.get("SOXX"))
    qqq_signal = _peer_signal_from_vote(votes_by_peer.get("QQQ"))
    peer_alignment = _peer_alignment_from_counts(confirm_count, oppose_count)
    peer_adjustment_label = _peer_adjustment_label_from_direction(adjustment_direction)
    adjusted_direction = _direction_cn_from_bias(adjusted_bias)
    adjustment_reason = (
        "Peer adjustment uses NVDA / SOXX / QQQ relative-strength confirmation."
    )

    return {
        "status": "computed",
        "source": "peer_relative_strength",
        "data_source": {
            "current": "scanner_relative_strength_labels",
            "label_inputs": [
                "relative_strength_summary",
                "relative_strength_same_day_summary",
            ],
            "raw_feature_inputs_ready": bool(peer_raw_features),
            "future_raw_feature_fields": [
                "peer_5d_return",
                "peer_same_day_move",
                "avgo_minus_peer_5d_return",
                "avgo_minus_peer_same_day_move",
            ],
        },
        "peer_raw_features": peer_raw_features,
        "peer_symbols": list(_PEER_SYMBOLS),
        "adjustments": adjustments,
        "confirm_count": confirm_count,
        "oppose_count": oppose_count,
        "adjustment_direction": adjustment_direction,
        "primary_bias": primary_bias,
        "primary_confidence": primary_confidence,
        "adjusted_bias": adjusted_bias,
        "adjusted_confidence": adjusted_confidence,
        "nvda_signal": nvda_signal,
        "soxx_signal": soxx_signal,
        "qqq_signal": qqq_signal,
        "peer_alignment": peer_alignment,
        "peer_adjustment": peer_adjustment_label,
        "adjusted_direction": adjusted_direction,
        "adjustment_reason": adjustment_reason,
        "path_risk_adjustment": {
            "status": "computed",
            "before": primary_path_risk,
            "after": adjusted_path_risk,
            "risk_direction": path_risk_direction,
            "reasons": path_risk_reasons,
            "path_label_changed": False,
        },
        "notes": "Peer adjustment uses NVDA / SOXX / QQQ relative-strength confirmation.",
    }


def _apply_research_adjustment(
    bias: str,
    confidence: str,
    scan_bias: str,
    research_result: dict[str, Any] | None,
    supporting_factors: list[str],
    conflicting_factors: list[str],
    note_parts: list[str],
) -> tuple[str, str]:
    research = research_result or {}
    adjustment = str(research.get("research_bias_adjustment", "missing_research"))
    research_sentiment = str(research.get("sentiment_bias", "missing"))

    final_bias = bias if bias in {"bullish", "bearish", "neutral"} else "neutral"
    final_confidence = _normalize_confidence(confidence)

    if adjustment == "missing_research":
        supporting_factors.append("research_missing_scan_led")
    elif adjustment == "reinforce_bullish" and final_bias == "bullish":
        final_confidence = _raise_confidence(final_confidence)
        supporting_factors.append("research_reinforces_bullish")
    elif adjustment == "reinforce_bearish" and final_bias == "bearish":
        final_confidence = _raise_confidence(final_confidence)
        supporting_factors.append("research_reinforces_bearish")
    elif adjustment == "weaken_bullish" and final_bias == "bullish":
        conflicting_factors.append("research_weakens_bullish")
        if final_confidence == "high":
            final_confidence = "medium"
        else:
            final_bias = "neutral"
            final_confidence = "low"
    elif adjustment == "weaken_bearish" and final_bias == "bearish":
        conflicting_factors.append("research_weakens_bearish")
        if final_confidence == "high":
            final_confidence = "medium"
        else:
            final_bias = "neutral"
            final_confidence = "low"
    elif final_bias == "neutral" and adjustment in _DIRECTIONAL_ADJUSTMENTS:
        final_confidence = "low"
        conflicting_factors.append("neutral_primary_research_direction_not_applied")
        note_parts.append(
            "Research was directional, but it did not override a neutral primary projection."
        )
    else:
        if research_result is not None:
            final_confidence = _lower_confidence(final_confidence) if scan_bias != "neutral" else "low"
            supporting_factors.append(f"research_sentiment={research_sentiment}")
        else:
            supporting_factors.append("research_missing_scan_led")

    if research.get("catalyst_detected") is True:
        if adjustment in _REINFORCING_ADJUSTMENTS:
            supporting_factors.append("research_catalyst_detected")
        elif adjustment in _WEAKENING_ADJUSTMENTS:
            conflicting_factors.append("research_catalyst_conflicts_with_projection")
        elif research_result is not None:
            note_parts.append("Research detected a catalyst, but it was not classified as supporting or conflicting.")
    elif research.get("catalyst_detected") is False and research_result is not None:
        conflicting_factors.append("research_no_clear_catalyst")

    return final_bias, final_confidence


def build_final_projection(
    primary_projection: dict[str, Any],
    peer_adjustment: dict[str, Any],
    research_result: dict[str, Any] | None = None,
    scan_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the final prediction result from primary + peer adjustment."""
    scan = scan_result or {}
    research = research_result or {}
    adjustment = str(research.get("research_bias_adjustment", "missing_research"))
    scan_bias = str(scan.get("scan_bias", primary_projection.get("final_bias", "neutral")))
    scan_confidence = _normalize_confidence(str(scan.get("scan_confidence", primary_projection.get("final_confidence", "low"))))

    if primary_projection.get("final_bias") == "unavailable":
        unavailable_summary = _summarize("unavailable", "low", adjustment)
        return {
            "status": "unavailable",
            "source": "primary_projection_plus_peer_adjustment",
            "symbol": str(primary_projection.get("symbol", scan.get("symbol", "AVGO"))),
            "final_bias": "unavailable",
            "final_confidence": "low",
            "open_tendency": "unclear",
            "close_tendency": "unclear",
            "pred_open": None,
            "pred_path": None,
            "pred_close": None,
            "research_bias_adjustment": adjustment,
            "scan_bias": scan_bias,
            "scan_confidence": scan_confidence,
            "path_risk": "high",
            "peer_path_risk_adjustment": {
                "status": "unavailable",
                "before": "high",
                "after": "high",
                "risk_direction": "unchanged",
                "reasons": ["primary_projection_unavailable"],
                "path_label_changed": False,
            },
            "prediction_summary": unavailable_summary,
            "supporting_factors": [],
            "conflicting_factors": ["primary_projection_unavailable"],
            # Step 1A contract 06 fields (defaults for the unavailable branch).
            "final_direction": "中性",
            "final_open_projection": "平开",
            "final_intraday_path": "震荡",
            "final_close_projection": "收平",
            "final_five_state": "震荡",
            "probability_bucket": "45–55%",
            "key_price_levels": {},
            "final_one_sentence": unavailable_summary,
            "notes": "Primary projection is unavailable, so final projection is unavailable.",
        }

    supporting_factors: list[str] = [
        f"primary_bias={primary_projection.get('final_bias', 'neutral')}",
        f"primary_confidence={primary_projection.get('final_confidence', 'low')}",
        f"peer_adjustment={peer_adjustment.get('adjustment_direction', 'neutral')}",
    ]
    conflicting_factors: list[str] = []
    note_parts: list[str] = [
        "Predict v2 uses AVGO-only primary projection, then NVDA/SOXX/QQQ peer adjustment; "
        "it remains rule-based and is not an automated trading signal."
    ]

    peer_direction = str(peer_adjustment.get("adjustment_direction", "neutral"))
    if peer_direction == "reinforce":
        supporting_factors.append("peer_confirmation=reinforce")
    elif peer_direction == "weaken":
        conflicting_factors.append("peer_confirmation=weaken")
    elif peer_direction == "neutral_primary":
        conflicting_factors.append("peer_adjustment_neutral_primary")

    path_risk_adjustment = peer_adjustment.get("path_risk_adjustment")
    if not isinstance(path_risk_adjustment, dict):
        primary_path_risk = _path_risk_from_confidence(str(primary_projection.get("final_confidence", "low")))
        path_risk_adjustment = {
            "status": "computed",
            "before": primary_path_risk,
            "after": primary_path_risk,
            "risk_direction": "unchanged",
            "reasons": [],
            "path_label_changed": False,
        }
    path_risk = str(path_risk_adjustment.get("after", "medium"))
    path_risk_direction = str(path_risk_adjustment.get("risk_direction", "unchanged"))
    if path_risk_direction == "higher":
        conflicting_factors.append(f"peer_path_risk={path_risk}")
        note_parts.append(
            "Peer layer raises path risk; final path label is kept but should be treated with caution."
        )
    elif path_risk_direction == "lower":
        supporting_factors.append(f"peer_path_risk={path_risk}")

    final_bias = str(peer_adjustment.get("adjusted_bias", primary_projection.get("final_bias", "neutral")))
    final_confidence = _normalize_confidence(str(peer_adjustment.get(
        "adjusted_confidence",
        primary_projection.get("final_confidence", "low"),
    )))

    final_bias, final_confidence = _apply_research_adjustment(
        final_bias,
        final_confidence,
        scan_bias,
        research_result,
        supporting_factors,
        conflicting_factors,
        note_parts,
    )

    open_tendency = str(primary_projection.get("open_tendency", "unclear"))
    close_tendency = str(primary_projection.get("close_tendency", "unclear"))
    labels = _pred_labels(open_tendency, close_tendency)
    prediction_summary = _summarize(final_bias, final_confidence, adjustment)

    # Step 1A contract 06 fields, derived from the same final signals.
    # Logic above is unchanged; this section is purely additive translation.
    final_direction = _direction_cn_from_bias(final_bias)
    final_open_projection = _open_projection_from_pred_open(labels.get("pred_open"))
    final_intraday_path = _intraday_path_from_pred_path(labels.get("pred_path"))
    final_close_projection = _close_projection_from_pred_close(labels.get("pred_close"))
    final_five_state = _five_state_from(final_direction, final_close_projection)
    probability_bucket = _probability_bucket_from_confidence(final_confidence)

    return {
        "status": "computed",
        "source": "primary_projection_plus_peer_adjustment",
        "symbol": str(primary_projection.get("symbol", scan.get("symbol", "AVGO"))),
        "final_bias": final_bias,
        "final_confidence": final_confidence,
        "open_tendency": open_tendency,
        "close_tendency": close_tendency,
        **labels,
        "research_bias_adjustment": adjustment,
        "scan_bias": scan_bias,
        "scan_confidence": scan_confidence,
        "path_risk": path_risk,
        "peer_path_risk_adjustment": path_risk_adjustment,
        "prediction_summary": prediction_summary,
        "supporting_factors": supporting_factors,
        "conflicting_factors": conflicting_factors,
        "final_direction": final_direction,
        "final_open_projection": final_open_projection,
        "final_intraday_path": final_intraday_path,
        "final_close_projection": final_close_projection,
        "final_five_state": final_five_state,
        "probability_bucket": probability_bucket,
        "key_price_levels": {},
        "final_one_sentence": prediction_summary,
        "notes": " ".join(note_parts),
    }


def _missing_scan_result(
    research_result: dict[str, Any] | None,
    symbol: str,
    confidence_result: dict[str, Any] | None = None,
) -> PredictResult:
    research = research_result or {}
    adjustment = str(research.get("research_bias_adjustment", "missing_research"))
    primary_projection = build_primary_projection(None, research_result=research_result, symbol=symbol)
    peer_adjustment = apply_peer_adjustment(primary_projection, None)
    final_projection = build_final_projection(primary_projection, peer_adjustment, research_result, None)
    # 11E X2: final_confidence / confidence are sourced from confidence_result.
    compat_confidence = _extract_compat_confidence(confidence_result)
    return {
        "symbol": symbol,
        "predict_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "scan_bias": "missing",
        "scan_confidence": "low",
        "research_bias_adjustment": adjustment,
        "final_bias": "unavailable",
        "final_confidence": compat_confidence,
        "confidence": compat_confidence,
        "open_tendency": "unclear",
        "close_tendency": "unclear",
        "prediction_summary": _summarize("unavailable", "low", adjustment),
        "supporting_factors": [],
        "conflicting_factors": ["scan_result_missing"],
        "path_risk": "high",
        "peer_path_risk_adjustment": final_projection.get("peer_path_risk_adjustment", {}),
        "notes": (
            "Scan is missing, so Predict cannot produce a normal directional judgment. "
            "Run Scan first, then rerun Predict with optional Research context."
        ),
        "primary_projection": primary_projection,
        "peer_adjustment": peer_adjustment,
        "final_projection": final_projection,
        "projection_three_systems": _build_projection_three_systems_attachment(
            symbol=symbol, reason="scan_result missing"
        ),
        # 11E X1: legacy wrapper metadata (does not change any legacy value).
        **_legacy_wrapper_metadata(),
    }


def _build_projection_three_systems_attachment(
    *, symbol: str, reason: str | None = None
) -> dict[str, Any]:
    """Wire projection_three_systems into predict_result (Task 104).

    Lazy-imports the v2 orchestrator and the three-systems renderer so
    predict.py stays free of module-load cycles with
    services.projection_orchestrator (which already imports run_predict).

    On any failure, returns the canonical degraded payload exported by
    services.projection_entrypoint so the predict_result contract stays
    stable regardless of v2 availability.
    """
    if reason:
        from services.projection_entrypoint import _degraded_projection_three_systems
        return _degraded_projection_three_systems(symbol=symbol, error_message=reason)

    # Re-entry guard: when run_predict is called from inside the legacy
    # projection orchestrator (which is itself called from run_projection_v2),
    # skip the inner v2 invocation to avoid recursive pipeline work. The
    # outer call has already produced the projection result; the inner
    # attachment would just rerun the same chain.
    state = _projection_three_systems_attachment_state
    if getattr(state, "active", False):
        from services.projection_entrypoint import _degraded_projection_three_systems
        return _degraded_projection_three_systems(
            symbol=symbol,
            error_message="projection_three_systems attachment skipped during re-entry",
        )

    state.active = True
    try:
        from services.projection_orchestrator_v2 import run_projection_v2
        from services.projection_three_systems_renderer import build_projection_three_systems

        v2_raw = run_projection_v2(symbol=symbol, lookback_days=20)
        return build_projection_three_systems(projection_v2_raw=v2_raw, symbol=symbol)
    except Exception as exc:
        from services.projection_entrypoint import _degraded_projection_three_systems

        message = str(exc).strip() or exc.__class__.__name__
        return _degraded_projection_three_systems(symbol=symbol, error_message=message)
    finally:
        state.active = False


_CONFIDENCE_ORDER = ["low", "medium", "high"]


def _apply_briefing_caution(result: dict, briefing: dict) -> dict:
    """Lower final_confidence by one step when caution_level is high."""
    result = dict(result)
    caution_level = briefing.get("caution_level", "none")
    has_data = briefing.get("has_data", False)

    if caution_level == "high" and has_data:
        current = result["final_confidence"]
        if current in _CONFIDENCE_ORDER:
            idx = _CONFIDENCE_ORDER.index(current)
            if idx > 0:
                result["final_confidence"] = _CONFIDENCE_ORDER[idx - 1]
                result["briefing_caution_applied"] = True
                result["briefing_caution_reason"] = (
                    f"历史准确率 {briefing.get('overall_accuracy', 0.0):.0%}，"
                    f"基于 {briefing.get('record_count', 0)} 条复盘记录，"
                    f"信心由 {current} 下调一档"
                )
            else:
                result["briefing_caution_applied"] = False
                result["briefing_caution_reason"] = (
                    f"历史风险高但信心已在最低档（{current}），未继续下调"
                )
        else:
            result["briefing_caution_applied"] = False
            result["briefing_caution_reason"] = None
    elif caution_level == "medium" and has_data:
        result["briefing_caution_applied"] = False
        result["briefing_caution_reason"] = (
            f"历史准确率中等（{briefing.get('overall_accuracy', 0.0):.0%}），维持当前信心并标注风险"
        )
    else:
        result["briefing_caution_applied"] = False
        result["briefing_caution_reason"] = None

    return result


def run_predict(
    scan_result: dict[str, Any] | None,
    research_result: dict[str, Any] | None = None,
    symbol: str = "AVGO",
    pre_briefing: dict | None = None,
    confidence_result: dict[str, Any] | None = None,
) -> PredictResult:
    """Run the v2 two-step projection chain and keep the old result shape.

    11E X2: ``confidence_result`` is a read-only signal from
    ``services.confidence_evaluator.build_confidence_result``. When
    provided, ``final_confidence`` / ``confidence`` are sourced from
    ``confidence_result.combined_confidence.level`` (degrades to
    ``"unknown"`` if absent or malformed). The wrapper does NOT recompute
    confidence and does not introduce new judgment.
    """
    if not scan_result:
        return _missing_scan_result(research_result, symbol, confidence_result=confidence_result)

    scan = scan_result or {}
    research = research_result or {}
    primary_projection = build_primary_projection(scan, research_result=research_result, symbol=symbol)
    peer_adjustment = apply_peer_adjustment(primary_projection, scan)
    final_projection = build_final_projection(
        primary_projection,
        peer_adjustment,
        research_result=research_result,
        scan_result=scan,
    )

    scan_bias = str(final_projection.get("scan_bias", scan.get("scan_bias", "neutral")))
    scan_confidence = _normalize_confidence(str(final_projection.get("scan_confidence", scan.get("scan_confidence", "low"))))
    adjustment = str(research.get("research_bias_adjustment", "missing_research"))
    final_bias = str(final_projection.get("final_bias", "neutral"))
    # 11E X2: final_confidence / confidence are sourced from
    # confidence_result.combined_confidence.level. The wrapper no longer
    # accepts the v1-computed value here. The inner ``final_projection``
    # block still carries its v1 ``final_confidence`` for legacy
    # consumers of that nested dict; only the outer compat field is
    # rewired.
    compat_confidence = _extract_compat_confidence(confidence_result)
    supporting_factors = list(final_projection.get("supporting_factors", []))
    conflicting_factors = list(final_projection.get("conflicting_factors", []))
    # Summary text remains v1-sourced until X3.
    legacy_v1_confidence_for_summary = _normalize_confidence(
        str(final_projection.get("final_confidence", "low"))
    )
    prediction_summary = str(
        final_projection.get(
            "prediction_summary",
            _summarize(final_bias, legacy_v1_confidence_for_summary, adjustment),
        )
    )
    path_risk = str(final_projection.get("path_risk", "medium"))
    peer_path_risk_adjustment = final_projection.get("peer_path_risk_adjustment")
    if not isinstance(peer_path_risk_adjustment, dict):
        peer_path_risk_adjustment = {}
    notes = str(final_projection.get("notes", ""))

    result = {
        "symbol": str(final_projection.get("symbol", scan.get("symbol", symbol))),
        "predict_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "scan_bias": scan_bias,
        "scan_confidence": scan_confidence,
        "research_bias_adjustment": adjustment,
        "final_bias": final_bias,
        "final_confidence": compat_confidence,
        "confidence": compat_confidence,
        "open_tendency": str(final_projection.get("open_tendency", "unclear")),
        "close_tendency": str(final_projection.get("close_tendency", "unclear")),
        "pred_open": final_projection.get("pred_open"),
        "pred_path": final_projection.get("pred_path"),
        "pred_close": final_projection.get("pred_close"),
        "prediction_summary": prediction_summary,
        "supporting_factors": supporting_factors,
        "conflicting_factors": conflicting_factors,
        "path_risk": path_risk,
        "peer_path_risk_adjustment": peer_path_risk_adjustment,
        "notes": notes,
        "primary_projection": primary_projection,
        "peer_adjustment": peer_adjustment,
        "final_projection": final_projection,
        "briefing_caution_applied": False,
        "briefing_caution_reason": None,
        "projection_three_systems": _build_projection_three_systems_attachment(symbol=symbol),
        # 11E X1/X2: legacy wrapper metadata (X2 wires confidence source).
        **_legacy_wrapper_metadata(),
    }
    if pre_briefing and pre_briefing.get("has_data"):
        result = _apply_briefing_caution(result, pre_briefing)
        # _apply_briefing_caution may have lowered final_confidence; keep
        # the ``confidence`` alias in lockstep so the two compat fields
        # never diverge.
        result["confidence"] = result.get("final_confidence", compat_confidence)
    return result
