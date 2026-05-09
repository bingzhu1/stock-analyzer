"""Shared peer-alignment feature helper (Step 17B / PR-C).

This module belongs to the **Feature Layer** (Branch 2) of the post-1.0
architecture; see `tasks/record_1_0_architecture_reset_canonical_principles.md`
§8 (Branch 2) and `tasks/record_16i_core_chain_rebuild_execution_plan.md`
§7.

Purpose:

- Compute the NVDA / SOXX / QQQ same-day peer-alignment summary from raw
  ``ret1`` features. Used by both the Projection System (Branch 3) and
  the Exclusion System (Branch 4); the function is **feature-only** and
  carries no opinion about what tomorrow will or will not look like.

Boundary contract (1.0 / 16A §6 / 16C §3 / 16I §7):

- This module is **not** part of the Exclusion System (Branch 4) and
  **not** part of the Projection System (Branch 3). It is a shared
  feature helper.
- ``build_peer_alignment`` **must not** read ``projection_result`` /
  ``exclusion_result`` / ``confidence_result`` / ``final_report`` /
  any system output. It only reads raw peer ``ret1`` features.
- This module **must not** import any of: ``services.exclusion_layer``,
  ``services.main_projection_layer``, ``services.confidence_evaluator``,
  ``services.final_decision``, ``services.projection_orchestrator``,
  ``services.projection_orchestrator_v2``, ``services.home_terminal_orchestrator``,
  ``services.consistency_layer``, ``services.standard_projection_payload``,
  ``predict``, ``ui.*``, any DB / sqlite / yfinance / OpenAI client.
- Output structure and semantics are identical to the prior
  ``services.exclusion_layer.build_peer_alignment`` implementation.
  PR-C is a **pure move**; behavior unchanged.
"""

from __future__ import annotations

from typing import Any


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _pick_float(source: dict[str, Any], keys: list[str]) -> float | None:
    for key in keys:
        value = _safe_float(source.get(key))
        if value is not None:
            return value
    return None


def _normalize_features(features: dict[str, Any]) -> dict[str, Any]:
    source = dict(_as_dict(features.get("features")))
    source.update(_as_dict(features))
    return {
        "symbol": str(source.get("symbol") or "AVGO").strip().upper() or "AVGO",
        "pos20": _pick_float(source, ["pos20", "pos_20", "pos_20d", "position_20d"]),
        "vol_ratio20": _pick_float(source, ["vol_ratio20", "vol_ratio_20", "vol_ratio_20d"]),
        "upper_shadow_ratio": _pick_float(source, ["upper_shadow_ratio", "upper_shadow", "up_shadow_ratio"]),
        "lower_shadow_ratio": _pick_float(source, ["lower_shadow_ratio", "lower_shadow", "down_shadow_ratio"]),
        "ret1": _pick_float(source, ["ret1", "ret_1d", "day_return_pct", "close_change_pct", "pct_change"]),
        "ret3": _pick_float(source, ["ret3", "ret_3d"]),
        "ret5": _pick_float(source, ["ret5", "ret_5d"]),
        "nvda_ret1": _pick_float(source, ["nvda_ret1", "nvda_ret_1d", "ret1_nvda"]),
        "soxx_ret1": _pick_float(source, ["soxx_ret1", "soxx_ret_1d", "ret1_soxx"]),
        "qqq_ret1": _pick_float(source, ["qqq_ret1", "qqq_ret_1d", "ret1_qqq"]),
    }


def build_peer_alignment(features: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_features(features)
    peers = {
        "NVDA": normalized["nvda_ret1"],
        "SOXX": normalized["soxx_ret1"],
        "QQQ": normalized["qqq_ret1"],
    }

    available_peer_count = 0
    bullish_count = 0
    bearish_count = 0
    strong_bullish_count = 0
    strong_bearish_count = 0

    for ret1 in peers.values():
        if ret1 is None:
            continue
        available_peer_count += 1
        if ret1 >= 0.5:
            bullish_count += 1
        if ret1 <= -0.5:
            bearish_count += 1
        if ret1 >= 1.0:
            strong_bullish_count += 1
        if ret1 <= -1.0:
            strong_bearish_count += 1

    if available_peer_count == 0:
        alignment = "missing"
        up_support = "unknown"
        down_support = "unknown"
        reasons = ["缺少 NVDA / SOXX / QQQ 的同日强弱输入，peer alignment 只能保守降级。"]
    else:
        if bullish_count >= 2:
            up_support = "supported"
        elif bullish_count == 1:
            up_support = "partial"
        else:
            up_support = "unsupported"

        if bearish_count >= 2:
            down_support = "supported"
        elif bearish_count == 1:
            down_support = "partial"
        else:
            down_support = "unsupported"

        if strong_bullish_count >= 2:
            alignment = "bullish"
        elif strong_bearish_count >= 2:
            alignment = "bearish"
        elif bullish_count == 0 and bearish_count == 0:
            alignment = "neutral"
        else:
            alignment = "mixed"

        reasons = [
            (
                f"peer alignment：available={available_peer_count}，"
                f"bullish={bullish_count}，bearish={bearish_count}。"
            )
        ]

    return {
        "alignment": alignment,
        "up_support": up_support,
        "down_support": down_support,
        "available_peer_count": available_peer_count,
        "peer_returns": peers,
        "reasons": reasons,
    }
