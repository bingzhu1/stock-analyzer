"""Prediction-style exclusion layer for projection v2.

This layer does not identify whether AVGO already had a big move today.
Instead, it uses current structure features to decide whether tomorrow is
unlikely to produce an extreme big-up or big-down state.
"""

from __future__ import annotations

from typing import Any


_UPSIDE_EXCLUDE_THRESHOLD = 3
_DOWNSIDE_EXCLUDE_THRESHOLD = 3


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


def _kill_risk(score: int) -> str:
    if score >= 4:
        return "high"
    if score >= 2:
        return "medium"
    return "low"


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


def exclude_big_up(features: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_features(features)
    peer_alignment = build_peer_alignment(normalized)
    exclude_score = 0
    reasons: list[str] = []
    triggered_rules: list[str] = []

    pos20 = normalized["pos20"]
    vol_ratio20 = normalized["vol_ratio20"]
    upper_shadow_ratio = normalized["upper_shadow_ratio"]
    ret1 = normalized["ret1"]
    ret3 = normalized["ret3"]
    ret5 = normalized["ret5"]

    if pos20 is not None and pos20 >= 80:
        exclude_score += 1
        triggered_rules.append("high_position_pressure")
        reasons.append(f"pos20={pos20:.1f}，位置已偏高，高位继续走成明日大涨的空间受压。")

    if vol_ratio20 is not None and vol_ratio20 <= 0.90:
        exclude_score += 1
        triggered_rules.append("shrinking_volume")
        reasons.append(f"vol_ratio20={vol_ratio20:.2f}，量能偏缩，缺少支撑明日大涨的增量成交。")

    if upper_shadow_ratio is not None and upper_shadow_ratio >= 0.35:
        exclude_score += 1
        triggered_rules.append("long_upper_shadow")
        reasons.append(
            f"upper_shadow_ratio={upper_shadow_ratio:.2f}，上影偏长，说明上方抛压仍在。"
        )

    if (
        (ret1 is not None and ret1 >= 2.0)
        or (ret3 is not None and ret3 >= 4.5)
        or (ret5 is not None and ret5 >= 7.0)
    ):
        exclude_score += 1
        triggered_rules.append("short_term_overextended")
        reasons.append(
            "ret1 / ret3 / ret5 显示短期动量已有透支，继续演化成明日大涨的赔率下降。"
        )

    if peer_alignment["up_support"] != "supported":
        exclude_score += 1
        triggered_rules.append("peers_do_not_support_upside")
        reasons.append("NVDA / SOXX / QQQ 没有形成足够同步偏强，peers 不支持明日极端上冲。")

    excluded = exclude_score >= _UPSIDE_EXCLUDE_THRESHOLD
    return {
        "hit": bool(triggered_rules),
        "excluded": excluded,
        "rule": "exclude_big_up",
        "exclude_score": exclude_score,
        "kill_risk": _kill_risk(exclude_score),
        "reasons": reasons,
        "triggered_rules": triggered_rules,
        "peer_alignment": peer_alignment,
    }


def exclude_big_down(features: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_features(features)
    peer_alignment = build_peer_alignment(normalized)
    exclude_score = 0
    reasons: list[str] = []
    triggered_rules: list[str] = []

    pos20 = normalized["pos20"]
    vol_ratio20 = normalized["vol_ratio20"]
    lower_shadow_ratio = normalized["lower_shadow_ratio"]
    ret1 = normalized["ret1"]
    ret3 = normalized["ret3"]
    ret5 = normalized["ret5"]

    if pos20 is not None and pos20 <= 20:
        exclude_score += 1
        triggered_rules.append("low_position_support")
        reasons.append(f"pos20={pos20:.1f}，位置已偏低，低位环境对明日大跌形成支撑。")

    if lower_shadow_ratio is not None and lower_shadow_ratio >= 0.35:
        exclude_score += 1
        triggered_rules.append("long_lower_shadow_support")
        reasons.append(
            f"lower_shadow_ratio={lower_shadow_ratio:.2f}，下影承接明显，说明低位买盘在吸收抛压。"
        )

    if (
        vol_ratio20 is not None
        and vol_ratio20 >= 1.20
        and (ret1 is None or ret1 > -1.5)
    ):
        exclude_score += 1
        triggered_rules.append("high_volume_but_not_weak")
        reasons.append(
            f"vol_ratio20={vol_ratio20:.2f} 且 ret1 未显著转弱，属于放量但不弱，不支持明日极端下杀。"
        )

    if (
        (ret1 is not None and ret1 >= 0.8)
        or (ret3 is not None and ret3 >= 1.5)
        or (ret5 is not None and ret5 >= 2.5)
    ):
        exclude_score += 1
        triggered_rules.append("short_term_repair")
        reasons.append("ret1 / ret3 / ret5 已出现短期修复，继续演化成明日大跌的概率下降。")

    if peer_alignment["down_support"] != "supported":
        exclude_score += 1
        triggered_rules.append("peers_do_not_support_downside")
        reasons.append("NVDA / SOXX / QQQ 没有形成足够同步转弱，peers 不支持明日极端下跌。")

    excluded = exclude_score >= _DOWNSIDE_EXCLUDE_THRESHOLD
    return {
        "hit": bool(triggered_rules),
        "excluded": excluded,
        "rule": "exclude_big_down",
        "exclude_score": exclude_score,
        "kill_risk": _kill_risk(exclude_score),
        "reasons": reasons,
        "triggered_rules": triggered_rules,
        "peer_alignment": peer_alignment,
    }


def run_exclusion_layer(features: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_features(features)
    peer_alignment = build_peer_alignment(normalized)
    feature_snapshot = {
        "pos20": normalized["pos20"],
        "vol_ratio20": normalized["vol_ratio20"],
        "upper_shadow_ratio": normalized["upper_shadow_ratio"],
        "lower_shadow_ratio": normalized["lower_shadow_ratio"],
        "ret1": normalized["ret1"],
        "ret3": normalized["ret3"],
        "ret5": normalized["ret5"],
    }

    missing_core = [
        key for key, value in feature_snapshot.items() if value is None
    ]
    if len(missing_core) >= 5:
        return {
            "excluded": False,
            "action": "allow",
            "triggered_rule": None,
            "summary": "排除层缺少关键特征，已安全降级为放行。",
            "reasons": ["pos20 / vol_ratio20 / shadow / ret 特征缺失过多，预测型排除层未触发。"],
            "peer_alignment": peer_alignment,
            "feature_snapshot": feature_snapshot,
        }

    up_result = exclude_big_up(normalized)
    down_result = exclude_big_down(normalized)

    if up_result["excluded"] and down_result["excluded"]:
        chosen = up_result if up_result["exclude_score"] >= down_result["exclude_score"] else down_result
        label = "明天大涨" if chosen["rule"] == "exclude_big_up" else "明天大跌"
        return {
            "excluded": True,
            "action": "exclude",
            "triggered_rule": chosen["rule"],
            "summary": f"排除层同时检测到双侧极端约束，当前以“{label}不太可能”作为主触发项。",
            "reasons": chosen["reasons"],
            "peer_alignment": chosen["peer_alignment"],
            "feature_snapshot": feature_snapshot,
        }

    if up_result["excluded"]:
        return {
            "excluded": True,
            "action": "exclude",
            "triggered_rule": "exclude_big_up",
            "summary": "排除层判断：明天不太可能大涨，后续主流程应避免输出极端上冲结论。",
            "reasons": up_result["reasons"],
            "peer_alignment": up_result["peer_alignment"],
            "feature_snapshot": feature_snapshot,
        }

    if down_result["excluded"]:
        return {
            "excluded": True,
            "action": "exclude",
            "triggered_rule": "exclude_big_down",
            "summary": "排除层判断：明天不太可能大跌，后续主流程应避免输出极端下杀结论。",
            "reasons": down_result["reasons"],
            "peer_alignment": down_result["peer_alignment"],
            "feature_snapshot": feature_snapshot,
        }

    return {
        "excluded": False,
        "action": "allow",
        "triggered_rule": None,
        "summary": "排除层未形成足够强的极端排除证据，主流程可继续推演。",
        "reasons": ["当前特征未形成对明日大涨或大跌的强排除约束。"],
        "peer_alignment": peer_alignment,
        "feature_snapshot": feature_snapshot,
    }
