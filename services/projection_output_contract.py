"""Pure-function validator for the Projection Output Contract (Step 1A).

Spec source of truth: tasks/step_1a_projection_output_contract.md (commit 76d9971).

Guarantees:
- Never mutates the input payload.
- Never raises (returns errors as a plain list of strings).
- Never reads files / calls external APIs / imports business modules.

Public API:
- ``CONTRACT_SECTIONS``  — the 8 top-level keys, in the contract-fixed order.
- ``validate_projection_output(payload)`` — return ``[]`` on success,
  otherwise a list of human-readable error strings.

Error message shapes (stable; tests rely on the prefix):
    invalid type: payload expected dict
    missing section: <section>
    section is not a dict: <section>
    missing field: <section>.<field>
    invalid type: <section>.<field> expected <type>
    invalid value: <section>.<field>
"""
from __future__ import annotations

from typing import Any


CONTRACT_SECTIONS: tuple[str, ...] = (
    "current_structure",
    "avgo_primary_projection",
    "peer_confirmation_adjustment",
    "exclusion_system",
    "confidence_system",
    "final_projection",
    "simulated_trade",
    "review_payload",
)


# Required fields per section. Subset of the Step 1A contract — the "核心字段"
# list explicitly requested for the validator. Optional / nice-to-have fields
# (e.g. ``what_would_invalidate_*``, ``similar_pattern_stats``,
# ``price_position_15d``) are intentionally NOT required here.
_REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "current_structure": (
        "symbol",
        "analysis_date",
        "prediction_for_date",
        "data_window_days",
        "current_price",
        "previous_close",
        "volume",
        "turnover",
        "structure_label",
        "short_summary",
    ),
    "avgo_primary_projection": (
        "primary_direction",
        "open_projection",
        "intraday_path_projection",
        "close_projection",
        "five_state_projection",
        "historical_sample_count",
        "key_evidence",
        "primary_confidence_raw",
    ),
    "peer_confirmation_adjustment": (
        "peer_symbols",
        "nvda_signal",
        "soxx_signal",
        "qqq_signal",
        "peer_alignment",
        "peer_adjustment",
        "adjusted_direction",
        "adjustment_reason",
    ),
    "exclusion_system": (
        "exclusion_level",
        "exclusion_sources",
        "exclusion_reasons",
        "forced_exclusion",
        "anti_false_exclusion_triggered",
    ),
    "confidence_system": (
        "historical_score",
        "structure_score",
        "peer_score",
        "exclusion_penalty",
        "event_score",
        "total_confidence",
        "confidence_level",
        "confidence_reason",
    ),
    "final_projection": (
        "final_direction",
        "final_open_projection",
        "final_intraday_path",
        "final_close_projection",
        "final_five_state",
        "probability_bucket",
        "key_price_levels",
        "final_one_sentence",
    ),
    "simulated_trade": (
        "trade_action",
        "trade_direction",
        "entry_condition",
        "stop_loss_condition",
        "take_profit_condition",
        "suggested_position_size",
        "no_trade_reason",
    ),
    "review_payload": (
        "predicted_open_type",
        "predicted_path_type",
        "predicted_close_type",
        "predicted_five_state",
        "predicted_confidence",
        "prediction_id",
        "review_ready_fields",
    ),
}


# Type expectations on selected fields. Untyped fields are not type-checked
# (e.g. free-text reasons / summaries are validated only for presence).
# Type tags:
#   "number"          — int or float (bool excluded)
#   "int"             — strict int (bool excluded)
#   "str"             — str
#   "list"            — list
#   "dict"            — dict
#   "bool"            — bool
#   "number_or_null"  — None or number   (1A: event_score may be null)
#   "str_or_null"     — None or str      (1A: no_trade_reason null when not no_trade)
_FIELD_TYPES: dict[str, str] = {
    # current_structure
    "current_structure.symbol": "str",
    "current_structure.analysis_date": "str",
    "current_structure.prediction_for_date": "str",
    "current_structure.data_window_days": "int",
    "current_structure.current_price": "number",
    "current_structure.previous_close": "number",
    "current_structure.volume": "number",
    "current_structure.turnover": "number",
    "current_structure.structure_label": "str",
    "current_structure.short_summary": "str",

    # avgo_primary_projection
    "avgo_primary_projection.historical_sample_count": "int",
    "avgo_primary_projection.key_evidence": "list",

    # peer_confirmation_adjustment
    "peer_confirmation_adjustment.peer_symbols": "list",
    "peer_confirmation_adjustment.adjustment_reason": "str",

    # exclusion_system
    "exclusion_system.exclusion_sources": "list",
    "exclusion_system.exclusion_reasons": "list",
    "exclusion_system.forced_exclusion": "bool",
    "exclusion_system.anti_false_exclusion_triggered": "bool",

    # confidence_system
    "confidence_system.historical_score": "number",
    "confidence_system.structure_score": "number",
    "confidence_system.peer_score": "number",
    "confidence_system.exclusion_penalty": "number",
    "confidence_system.event_score": "number_or_null",
    "confidence_system.total_confidence": "number",
    "confidence_system.confidence_reason": "str",

    # final_projection
    "final_projection.key_price_levels": "dict",
    "final_projection.final_one_sentence": "str",

    # simulated_trade
    "simulated_trade.entry_condition": "str",
    "simulated_trade.stop_loss_condition": "str",
    "simulated_trade.take_profit_condition": "str",
    "simulated_trade.no_trade_reason": "str_or_null",

    # review_payload
    "review_payload.prediction_id": "str",
    "review_payload.review_ready_fields": "list",
}


# Enum sets aligned with the 1A contract (commit 76d9971).
_DIRECTION = frozenset({"偏多", "偏空", "中性"})
_OPEN = frozenset({"高开", "平开", "低开"})
_PATH = frozenset({"高走", "震荡", "低走", "V 型反转", "倒 V"})
_CLOSE = frozenset({"收涨", "收平", "收跌"})
_FIVE_STATE = frozenset({"大涨", "小涨", "震荡", "小跌", "大跌"})
_PEER_SIGNAL = frozenset({"reinforce", "weaken", "neutral", "unknown"})
_PEER_ALIGNMENT = frozenset({"all_reinforce", "mixed", "all_weaken", "insufficient"})
_PEER_ADJUSTMENT = frozenset({"upgrade", "hold", "downgrade", "flip_to_neutral"})
_EXCLUSION_LEVEL = frozenset({"none", "soft", "hard"})
_CONFIDENCE_LEVEL = frozenset({"high", "medium", "low"})
_PROBABILITY_BUCKET = frozenset({"≥70%", "55–70%", "45–55%", "30–45%", "≤30%"})
_TRADE_ACTION = frozenset({"open", "hold", "close", "no_trade"})
_TRADE_DIRECTION = frozenset({"long", "short", "none"})
_POSITION_SIZE = frozenset({"0%", "25%", "50%", "75%", "100%"})


_ENUMS: dict[str, frozenset[str]] = {
    # avgo_primary_projection
    "avgo_primary_projection.primary_direction": _DIRECTION,
    "avgo_primary_projection.open_projection": _OPEN,
    "avgo_primary_projection.intraday_path_projection": _PATH,
    "avgo_primary_projection.close_projection": _CLOSE,
    "avgo_primary_projection.five_state_projection": _FIVE_STATE,
    "avgo_primary_projection.primary_confidence_raw": _CONFIDENCE_LEVEL,

    # peer_confirmation_adjustment
    "peer_confirmation_adjustment.nvda_signal": _PEER_SIGNAL,
    "peer_confirmation_adjustment.soxx_signal": _PEER_SIGNAL,
    "peer_confirmation_adjustment.qqq_signal": _PEER_SIGNAL,
    "peer_confirmation_adjustment.peer_alignment": _PEER_ALIGNMENT,
    "peer_confirmation_adjustment.peer_adjustment": _PEER_ADJUSTMENT,
    "peer_confirmation_adjustment.adjusted_direction": _DIRECTION,

    # exclusion_system
    "exclusion_system.exclusion_level": _EXCLUSION_LEVEL,

    # confidence_system
    "confidence_system.confidence_level": _CONFIDENCE_LEVEL,

    # final_projection
    "final_projection.final_direction": _DIRECTION,
    "final_projection.final_open_projection": _OPEN,
    "final_projection.final_intraday_path": _PATH,
    "final_projection.final_close_projection": _CLOSE,
    "final_projection.final_five_state": _FIVE_STATE,
    "final_projection.probability_bucket": _PROBABILITY_BUCKET,

    # simulated_trade
    "simulated_trade.trade_action": _TRADE_ACTION,
    "simulated_trade.trade_direction": _TRADE_DIRECTION,
    "simulated_trade.suggested_position_size": _POSITION_SIZE,

    # review_payload
    "review_payload.predicted_open_type": _OPEN,
    "review_payload.predicted_path_type": _PATH,
    "review_payload.predicted_close_type": _CLOSE,
    "review_payload.predicted_five_state": _FIVE_STATE,
    "review_payload.predicted_confidence": _CONFIDENCE_LEVEL,
}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _matches_type(value: Any, type_tag: str) -> bool:
    if type_tag == "number":
        return _is_number(value)
    if type_tag == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    if type_tag == "str":
        return isinstance(value, str)
    if type_tag == "list":
        return isinstance(value, list)
    if type_tag == "dict":
        return isinstance(value, dict)
    if type_tag == "bool":
        return isinstance(value, bool)
    if type_tag == "number_or_null":
        return value is None or _is_number(value)
    if type_tag == "str_or_null":
        return value is None or isinstance(value, str)
    return True


def validate_projection_output(payload: dict) -> list[str]:
    """Validate ``payload`` against the Step 1A Projection Output Contract.

    Returns an empty list on success, otherwise a list of human-readable
    error strings. Never raises; never mutates ``payload``.
    """
    if not isinstance(payload, dict):
        return [f"invalid type: payload expected dict (got {type(payload).__name__})"]

    errors: list[str] = []

    for section in CONTRACT_SECTIONS:
        if section not in payload:
            errors.append(f"missing section: {section}")
            continue
        section_value = payload[section]
        if not isinstance(section_value, dict):
            errors.append(f"section is not a dict: {section}")
            continue

        for field in _REQUIRED_FIELDS.get(section, ()):
            full_key = f"{section}.{field}"
            if field not in section_value:
                errors.append(f"missing field: {full_key}")
                continue

            value = section_value[field]

            type_tag = _FIELD_TYPES.get(full_key)
            if type_tag and not _matches_type(value, type_tag):
                errors.append(f"invalid type: {full_key} expected {type_tag}")
                continue

            allowed = _ENUMS.get(full_key)
            if allowed is not None and value not in allowed:
                errors.append(f"invalid value: {full_key}")

    return errors
