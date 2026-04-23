"""Shared contract helpers for the stabilized AVGO projection chain.

This module keeps the new exclusion/main-projection/consistency payload shape
consistent across different orchestrators without forcing a large cutover.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


_PEER_SYMBOLS = ("NVDA", "SOXX", "QQQ")


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _ret_pct(rows: list[dict[str, Any]], n: int) -> float | None:
    if len(rows) <= n:
        return None
    latest = safe_float(rows[-1].get("Close"))
    base = safe_float(rows[-(n + 1)].get("Close"))
    if latest is None or base in {None, 0}:
        return None
    return round((latest / base - 1.0) * 100.0, 2)


def _shadow_ratio(row: dict[str, Any] | None, which: str) -> float | None:
    if not row:
        return None
    open_price = safe_float(row.get("Open"))
    high = safe_float(row.get("High"))
    low = safe_float(row.get("Low"))
    close = safe_float(row.get("Close"))
    if None in {open_price, high, low, close}:
        return None
    total_range = high - low
    if total_range <= 0:
        return None
    upper_shadow = max(high - max(open_price, close), 0.0)
    lower_shadow = max(min(open_price, close) - low, 0.0)
    value = upper_shadow if which == "upper" else lower_shadow
    return round(value / total_range, 4)


def build_feature_payload_from_recent_window(
    *,
    recent_window: list[dict[str, Any]] | None,
    symbol: str = "AVGO",
    target_ctx: dict[str, Any] | None = None,
    peer_moves: dict[str, float | None] | None = None,
    feature_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the shared 20-day feature payload from recent rows.

    All returns in the payload use percentage points.
    Peer moves should also be percentage points, not ratios.
    """
    rows = [as_dict(row) for row in (recent_window or []) if isinstance(row, dict)]
    ctx = as_dict(target_ctx)
    peers = {
        symbol_name: None for symbol_name in _PEER_SYMBOLS
    }
    peers.update({str(key).upper(): value for key, value in as_dict(peer_moves).items()})

    clean_symbol = str(symbol or "AVGO").strip().upper() or "AVGO"
    if not rows:
        payload = {"symbol": clean_symbol}
        payload.update(as_dict(feature_overrides))
        return payload

    closes = [safe_float(row.get("Close")) for row in rows]
    highs = [safe_float(row.get("High")) for row in rows]
    lows = [safe_float(row.get("Low")) for row in rows]
    volumes = [safe_float(row.get("Volume")) for row in rows]

    valid_closes = [value for value in closes if value is not None]
    valid_highs = [value for value in highs if value is not None]
    valid_lows = [value for value in lows if value is not None]
    valid_volumes = [value for value in volumes if value is not None]

    latest_close = valid_closes[-1] if valid_closes else None
    high_20 = max(valid_highs) if valid_highs else None
    low_20 = min(valid_lows) if valid_lows else None
    pos20 = None
    if None not in {latest_close, high_20, low_20} and high_20 > low_20:
        pos20 = round((latest_close - low_20) / (high_20 - low_20) * 100.0, 1)

    latest_volume = valid_volumes[-1] if valid_volumes else None
    avg_volume20 = round(sum(valid_volumes) / len(valid_volumes), 6) if valid_volumes else None
    vol_ratio20 = None
    if latest_volume is not None and avg_volume20 not in {None, 0}:
        vol_ratio20 = round(latest_volume / avg_volume20, 2)

    target_row = rows[-1]
    payload = {
        "symbol": clean_symbol,
        "pos20": pos20,
        "vol_ratio20": vol_ratio20,
        "upper_shadow_ratio": _shadow_ratio(target_row, "upper"),
        "lower_shadow_ratio": _shadow_ratio(target_row, "lower"),
        "ret1": safe_float(ctx.get("ret1")) if ctx.get("ret1") is not None else _ret_pct(rows, 1),
        "ret3": safe_float(ctx.get("ret3")) if ctx.get("ret3") is not None else _ret_pct(rows, 3),
        "ret5": safe_float(ctx.get("ret5")) if ctx.get("ret5") is not None else _ret_pct(rows, 5),
    }
    for symbol_name in _PEER_SYMBOLS:
        payload[f"{symbol_name.lower()}_ret1"] = safe_float(peers.get(symbol_name))

    payload.update(as_dict(feature_overrides))
    return payload


def least_likely_from_projection(main_projection: dict[str, Any]) -> dict[str, Any]:
    probabilities = as_dict(main_projection.get("state_probabilities"))
    if not probabilities:
        return {"state": "—", "probability": 0.0}
    state, probability = min(probabilities.items(), key=lambda item: (item[1], item[0]))
    return {"state": state, "probability": probability}


def excluded_state_from_result(exclusion_result: dict[str, Any]) -> str | None:
    rule = str(as_dict(exclusion_result).get("triggered_rule") or "").strip()
    if rule == "exclude_big_up":
        return "大涨"
    if rule == "exclude_big_down":
        return "大跌"
    return None


def build_prediction_log_record(
    *,
    feature_payload: dict[str, Any],
    exclusion_result: dict[str, Any],
    main_projection: dict[str, Any],
    consistency: dict[str, Any],
    target_date_str: str,
    analysis_date: str | None = None,
    symbol: str = "AVGO",
) -> dict[str, Any]:
    top1 = as_dict(main_projection.get("predicted_top1"))
    top2 = as_dict(main_projection.get("predicted_top2"))
    top1_state = str(top1.get("state") or "").strip() or None
    top1_probability = safe_float(top1.get("probability"))

    if top1_state in {"大涨", "小涨"}:
        direction = "偏多"
    elif top1_state in {"大跌", "小跌"}:
        direction = "偏空"
    elif top1_state == "震荡":
        direction = "中性"
    else:
        direction = None

    if top1_probability is None:
        confidence = None
    elif top1_probability >= 0.45:
        confidence = "high"
    elif top1_probability >= 0.30:
        confidence = "medium"
    else:
        confidence = "low"

    excluded_state = excluded_state_from_result(exclusion_result)
    return {
        "symbol": str(symbol or "AVGO").strip().upper() or "AVGO",
        "analysis_date": analysis_date or datetime.now().strftime("%Y-%m-%d"),
        "prediction_for_date": target_date_str,
        "window_days": 20,
        "predicted_state": top1_state,
        "predicted_top1": {
            "state": top1_state,
            "probability": top1_probability,
        },
        "predicted_top2": {
            "state": str(top2.get("state") or "").strip() or None,
            "probability": safe_float(top2.get("probability")),
        },
        "state_probabilities": as_dict(main_projection.get("state_probabilities")),
        "direction": direction,
        "confidence": confidence,
        "exclusion_action": exclusion_result.get("action"),
        "exclusion_triggered_rule": exclusion_result.get("triggered_rule"),
        "excluded_state": excluded_state,
        "consistency_passed": consistency.get("consistency_flag") == "consistent",
        "consistency_flag": consistency.get("consistency_flag"),
        "consistency_score": safe_float(consistency.get("consistency_score")),
        "consistency_conflicts": consistency.get("conflict_reasons") or [],
        "feature_snapshot": feature_payload,
        "peer_alignment": exclusion_result.get("peer_alignment") or {},
        "notes": [
            *[str(item) for item in exclusion_result.get("reasons") or [] if str(item).strip()],
            *[str(item) for item in main_projection.get("rationale") or [] if str(item).strip()],
            str(consistency.get("summary") or "").strip(),
        ],
    }


def build_unified_projection_payload(
    *,
    kind: str,
    symbol: str,
    ready: bool,
    feature_payload: dict[str, Any] | None,
    exclusion_result: dict[str, Any] | None,
    main_projection: dict[str, Any] | None,
    consistency: dict[str, Any] | None,
    historical_match_result: dict[str, Any] | None,
    prediction_log_id: str | None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    projection = as_dict(main_projection)
    payload = {
        "kind": kind,
        "symbol": str(symbol or "AVGO").strip().upper() or "AVGO",
        "ready": bool(ready),
        "feature_payload": as_dict(feature_payload),
        "exclusion_result": as_dict(exclusion_result),
        "main_projection": projection,
        "consistency": as_dict(consistency),
        "historical_match_result": as_dict(historical_match_result),
        "primary_choice": as_dict(projection.get("predicted_top1")),
        "secondary_choice": as_dict(projection.get("predicted_top2")),
        "least_likely": least_likely_from_projection(projection),
        "prediction_log_id": prediction_log_id,
    }
    payload.update(as_dict(extra))
    return payload
