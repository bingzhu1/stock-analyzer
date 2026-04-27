"""Callable entrypoint for the current projection orchestration chain."""

from __future__ import annotations

from typing import Any

from services.projection_orchestrator_v2 import run_projection_v2
from services.projection_narrative_renderer import build_projection_narrative
from services.projection_three_systems_renderer import (
    build_projection_three_systems,
)
from services.projection_v2_adapter import build_projection_entrypoint_result


_THREE_SYSTEMS_KIND = "projection_three_systems"


def _degraded_projection_three_systems(
    *, symbol: str, error_message: str
) -> dict[str, Any]:
    reason = f"projection_three_systems 降级：{error_message}"
    return {
        "kind": _THREE_SYSTEMS_KIND,
        "symbol": symbol,
        "ready": False,
        "negative_system": {
            "conclusion": "否定系统不可用，已按安全降级处理。",
            "excluded_states": [],
            "strength": "none",
            "evidence": [],
            "invalidating_conditions": ["否定系统不可用，无法给出失效条件。"],
            "risk_notes": [reason],
        },
        "record_02_projection_system": {
            "current_structure": "02 推演系统不可用，无法描述当前结构。",
            "main_projection": "02 推演系统不可用，无法生成主推演。",
            "five_state_projection": {},
            "open_path_close_projection": {
                "open": "02 推演系统不可用，开盘倾向暂不输出。",
                "intraday": "02 推演系统不可用，日内结构暂不输出。",
                "close": "02 推演系统不可用，收盘倾向暂不输出。",
            },
            "historical_sample_summary": "02 推演系统不可用，历史样本说明暂不输出。",
            "peer_market_confirmation": "02 推演系统不可用，peers 确认暂不输出。",
            "key_price_levels": [],
            "risk_notes": [reason],
            "final_summary": "02 推演系统不可用。",
        },
        "confidence_evaluator": {
            "negative_system_confidence": {
                "score": None,
                "level": "unknown",
                "reasoning": [reason],
                "risks": [reason],
            },
            "projection_system_confidence": {
                "score": None,
                "level": "unknown",
                "reasoning": [reason],
                "risks": [reason],
            },
            "overall_confidence": {
                "score": None,
                "level": "unknown",
                "reasoning": [reason],
            },
            "conflicts": [],
            "reliability_warnings": [reason],
        },
    }


def _degraded_projection_narrative(*, symbol: str, error_message: str) -> dict[str, Any]:
    warning = f"projection_narrative 降级：{error_message}"
    return {
        "kind": "projection_narrative",
        "symbol": symbol,
        "ready": False,
        "step1_conclusion": "narrative renderer 不可用，保留原始 projection_v2 输出。",
        "step2_peer_adjustment": "当前未生成 narrative peers 修正段落，请参考原始 v2 层结果。",
        "final_judgment": "narrative renderer 降级，当前不影响 projection_v2_raw 与 compat shell 的返回。",
        "open_tendency": "narrative renderer 降级，暂不输出开盘倾向。",
        "intraday_structure": "narrative renderer 降级，暂不输出日内结构倾向。",
        "close_tendency": "narrative renderer 降级，暂不输出收盘倾向。",
        "key_watchpoints": {
            "stronger_case": ["请直接参考 projection_v2_raw 的主层结论与证据字段。"],
            "weaker_case": [warning],
        },
        "one_line_summary": "projection_narrative 已降级，但 projection_v2_raw 与 compat shell 仍可正常使用。",
        "warnings": [warning],
    }


def run_projection_entrypoint(
    *,
    symbol: str,
    error_category: str | None = None,
    limit: int = 5,
    lookback_days: int | None = None,
) -> dict[str, Any]:
    """
    Call the current projection orchestrator through one stable interface.

    The v2 raw result is the entrypoint source-of-truth. A legacy compat shell
    is still packaged for fallback callers, but it is no longer the primary
    business semantic.
    """
    normalized_symbol = str(symbol or "").strip().upper()
    if not normalized_symbol:
        raise ValueError("symbol must be a non-empty string")

    v2_raw = run_projection_v2(
        symbol=normalized_symbol,
        lookback_days=int(lookback_days or 20),
    )
    result = dict(build_projection_entrypoint_result(
        v2_raw=v2_raw,
        symbol=normalized_symbol,
        error_category=error_category,
        limit=limit,
        lookback_days=lookback_days,
    ))
    try:
        result["projection_narrative"] = build_projection_narrative(
            projection_v2_raw=v2_raw,
            symbol=normalized_symbol,
        )
    except Exception as exc:
        message = str(exc).strip() or exc.__class__.__name__
        result["projection_narrative"] = _degraded_projection_narrative(
            symbol=normalized_symbol,
            error_message=message,
        )
        notes = result.get("notes")
        if isinstance(notes, list):
            notes.append(f"Projection narrative degraded: {message}")

    try:
        result["projection_three_systems"] = build_projection_three_systems(
            projection_v2_raw=v2_raw,
            symbol=normalized_symbol,
        )
    except Exception as exc:
        message = str(exc).strip() or exc.__class__.__name__
        result["projection_three_systems"] = _degraded_projection_three_systems(
            symbol=normalized_symbol,
            error_message=message,
        )
        notes = result.get("notes")
        if isinstance(notes, list):
            notes.append(f"Projection three-systems degraded: {message}")
    return result
