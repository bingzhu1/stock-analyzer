"""Readable Chinese summary helpers for Predict and projection results."""

from __future__ import annotations

from typing import Any


_DIRECTION_LABELS = {
    "bullish": "偏多",
    "bearish": "偏空",
    "neutral": "中性",
    "unavailable": "中性",
}
_CONFIDENCE_STRENGTH = {"high": "强", "medium": "中", "low": "弱"}
_OPEN_LABELS = {
    "gap_up_bias": "高开",
    "gap_down_bias": "低开",
    "flat_bias": "平开",
    "up": "高开",
    "down": "低开",
    "flat": "平开",
}
_CLOSE_LABELS = {
    "close_strong": "偏强",
    "close_weak": "偏弱",
    "range": "震荡",
    "up": "偏强",
    "down": "偏弱",
    "flat": "震荡",
}
_CONFIDENCE_LABELS = {"high": "高", "medium": "中", "low": "低"}
_HISTORICAL_BIAS_LABELS = {
    "up_bias": "偏多",
    "down_bias": "偏空",
    "mixed": "历史分布混杂",
    "insufficient_sample": "样本不足",
}
_STATE_LABELS = {
    "gap_up": "高开",
    "gap_down": "低开",
    "flat": "平开",
    "bullish": "偏多",
    "bearish": "偏空",
    "neutral": "中性",
    "expanding": "量能放大",
    "shrinking": "量能收缩",
    "normal": "量能正常",
    "unknown": "未知",
}
_RS_LABELS = {
    "stronger": "强于",
    "weaker": "弱于",
    "neutral": "接近",
}


def _as_lines(values: Any, *, fallback: str | None = None) -> list[str]:
    if isinstance(values, list):
        lines = [str(v).strip() for v in values if str(v).strip()]
    elif values:
        lines = [str(values).strip()]
    else:
        lines = []
    if not lines and fallback:
        return [fallback]
    return lines


def direction_label(final_bias: str | None) -> str:
    return _DIRECTION_LABELS.get(str(final_bias or "neutral"), "中性")


def open_tendency_label(open_tendency: str | None) -> str:
    return _OPEN_LABELS.get(str(open_tendency or "unclear"), "平开")


def close_tendency_label(close_tendency: str | None) -> str:
    return _CLOSE_LABELS.get(str(close_tendency or "unclear"), "震荡")


def confidence_strength(confidence: str | None) -> str:
    return _CONFIDENCE_STRENGTH.get(str(confidence or "low"), "弱")


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _confidence_label(confidence: str | None) -> str:
    return _CONFIDENCE_LABELS.get(str(confidence or "low"), "低")


def _risk_level(confidence: str, scan_result: dict[str, Any]) -> str:
    confirmation = str(scan_result.get("confirmation_state", "mixed"))
    hist = _as_dict(scan_result.get("historical_match_summary"))
    dominant = str(hist.get("dominant_historical_outcome", ""))
    if (
        confidence == "low"
        or confirmation == "diverging"
        or dominant == "insufficient_sample"
        or _external_confirmation_missing(scan_result)
    ):
        return "高"
    if confidence == "medium" or dominant == "mixed":
        return "中"
    return "低"


def _open_watch(open_label: str) -> str:
    if open_label == "高开":
        return "防高开低走，重点看开盘后量能是否继续确认。"
    if open_label == "低开":
        return "防低开续跌，观察是否能快速收回关键价位。"
    return "留意修复失败，平开后方向需要等前半小时确认。"


def _close_watch(close_label: str) -> str:
    if close_label == "偏强":
        return "若盘中承接稳定，收盘更可能保持偏强。"
    if close_label == "偏弱":
        return "若反弹无量或同业继续走弱，收盘更可能偏弱。"
    return "多空证据不够集中，收盘更可能震荡。"


def _factor_label(factor: str) -> str:
    if factor.startswith("scan_bias="):
        return f"Scan 方向：{direction_label(factor.split('=', 1)[1])}"
    if factor.startswith("scan_confidence="):
        value = factor.split("=", 1)[1]
        return f"Scan 置信度：{_confidence_label(value)}（强度 {confidence_strength(value)}）"
    mapping = {
        "research_missing_scan_led": "未接入 Research，本次以 Scan 结果为主。",
        "research_reinforces_bullish": "Research 强化偏多判断。",
        "research_reinforces_bearish": "Research 强化偏空判断。",
        "scan_confirmation=confirmed": "同业/确认信号与 Scan 方向一致。",
        "scan_confirmation=diverging": "同业/确认信号与 Scan 方向背离。",
        "neutral_scan_research_direction_not_applied": "Scan 中性时，Research 方向信号未直接覆盖规则结论。",
        "research_weakens_bullish": "Research 削弱偏多判断。",
        "research_weakens_bearish": "Research 削弱偏空判断。",
        "research_catalyst_conflicts_with_scan": "Research 催化与 Scan 方向存在冲突。",
        "research_no_clear_catalyst": "Research 未发现清晰催化。",
        "scan_result_missing": "缺少 Scan 结果，预测只能降级处理。",
    }
    return mapping.get(factor, factor)


def _scan_context_lines(scan_result: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    hist = _as_dict(scan_result.get("historical_match_summary"))
    if hist:
        hist_bias = _HISTORICAL_BIAS_LABELS.get(
            str(hist.get("dominant_historical_outcome", "")),
            "未知",
        )
        lines.append(
            "历史匹配：完全匹配 "
            f"{hist.get('exact_match_count', 0)}，近似匹配 {hist.get('near_match_count', 0)}，"
            f"历史倾向：{hist_bias}。"
        )

    state_parts = []
    if scan_result.get("avgo_gap_state"):
        state_parts.append(f"开盘状态 {_STATE_LABELS.get(str(scan_result['avgo_gap_state']), scan_result['avgo_gap_state'])}")
    if scan_result.get("avgo_price_state"):
        state_parts.append(f"位置/动能状态 {_STATE_LABELS.get(str(scan_result['avgo_price_state']), scan_result['avgo_price_state'])}")
    if scan_result.get("avgo_volume_state"):
        state_parts.append(str(_STATE_LABELS.get(str(scan_result["avgo_volume_state"]), scan_result["avgo_volume_state"])))
    if state_parts:
        lines.append("结构状态：" + "，".join(state_parts) + "。")

    rs_5d = _as_dict(scan_result.get("relative_strength_5d_summary") or scan_result.get("relative_strength_summary"))
    rs_day = _as_dict(scan_result.get("relative_strength_same_day_summary"))
    if rs_5d or rs_day:
        lines.append(
            "同业对照："
            f"5日 {_format_rs(rs_5d)}；当日 {_format_rs(rs_day)}。"
        )

    return lines


def _format_rs(summary: dict[str, Any]) -> str:
    parts = []
    for key in ("vs_nvda", "vs_soxx", "vs_qqq"):
        value = str(summary.get(key, ""))
        if value and value != "unavailable":
            label = _RS_LABELS.get(value, value)
            parts.append(f"{label} {key.replace('vs_', '').upper()}")
    return "、".join(parts) if parts else "暂无可用对照"


def _external_confirmation_missing(scan_result: dict[str, Any]) -> bool:
    rs_5d = _as_dict(scan_result.get("relative_strength_5d_summary") or scan_result.get("relative_strength_summary"))
    rs_day = _as_dict(scan_result.get("relative_strength_same_day_summary"))
    if not rs_5d and not rs_day:
        return bool(scan_result)
    values = list(rs_5d.values()) + list(rs_day.values())
    return bool(values) and all(str(value) in {"", "unavailable", "unknown"} for value in values)


def _risk_lines(
    predict_result: dict[str, Any],
    scan_result: dict[str, Any],
    advisory: dict[str, Any] | None,
) -> list[str]:
    risks = [_factor_label(line) for line in _as_lines(predict_result.get("conflicting_factors"))]
    if advisory:
        risks.extend(_as_lines(advisory.get("reminder_lines")))

    hist = _as_dict(scan_result.get("historical_match_summary"))
    if hist.get("dominant_historical_outcome") == "insufficient_sample":
        risks.append("历史样本不足，结论需要降级看待。")
    elif hist.get("dominant_historical_outcome") == "mixed":
        risks.append("历史分布混杂，方向优势不明显。")

    if str(scan_result.get("confirmation_state", "")) == "diverging":
        risks.append("外部/同业确认不足，需防方向失真。")
    elif _external_confirmation_missing(scan_result):
        risks.append("外部确认不足，需等待 NVDA / SOXX / QQQ 对照补充。")

    if not risks:
        risks.append("暂无明确冲突因子，但仍需等待开盘与量能确认。")
    risks.append("规则层推演不是交易建议，实际操作仍需控制仓位和止损。")
    return list(dict.fromkeys(risks))


def _prediction_summary_line(summary: Any) -> str | None:
    text = str(summary or "").strip()
    if not text:
        return None
    if text.startswith("Prediction unavailable"):
        return "Predict 结论：缺少 Scan 结果，暂无法形成正常方向判断。"
    if "led by Scan only" in text:
        return "Predict 结论：当前以 Scan 结果为主，未接入 Research 修正。"
    if "after combining" in text:
        return "Predict 结论：已综合 Scan 与 Research 调整。"
    if text.startswith("Prediction is"):
        return "Predict 结论：方向判断已由规则层生成。"
    return text


def _summary_text(summary: dict[str, Any]) -> str:
    why = "\n".join(f"- {line}" for line in summary["rationale"])
    risks = "\n".join(f"- {line}" for line in summary["risk_reminders"])
    return (
        f"明日基准判断：{summary['baseline_judgment']['text']}\n"
        f"明日方向：{summary['baseline_judgment']['direction']}\n"
        f"开盘推演：{summary['open_projection']['text']}\n"
        f"收盘推演：{summary['close_projection']['text']}\n"
        "为什么这样判断：\n"
        f"{why}\n"
        "风险提醒：\n"
        f"{risks}"
    )


def build_predict_readable_summary(
    predict_result: dict[str, Any] | None,
    *,
    scan_result: dict[str, Any] | None = None,
    advisory: dict[str, Any] | None = None,
    lookback_days: int | None = None,
    ai_polish: str | None = None,
) -> dict[str, Any]:
    """Build a stable rule-based Chinese summary from existing structured results."""
    predict = predict_result or {}
    scan = scan_result or {}
    confidence = str(predict.get("final_confidence", "low"))
    direction = direction_label(str(predict.get("final_bias", "neutral")))
    open_label = open_tendency_label(str(predict.get("open_tendency", "unclear")))
    close_label = close_tendency_label(str(predict.get("close_tendency", "unclear")))
    strength = confidence_strength(confidence)
    risk = _risk_level(confidence, scan)

    rationale = [_factor_label(line) for line in _as_lines(predict.get("supporting_factors"))]
    rationale.extend(_scan_context_lines(scan))
    summary_line = _prediction_summary_line(predict.get("prediction_summary"))
    if summary_line:
        rationale.append(summary_line)
    if lookback_days and lookback_days > 0:
        rationale.append(f"命令指定参考窗口：最近 {lookback_days} 天。")
    if not rationale:
        rationale = ["结构化依据不足，按中性低置信度降级展示。"]

    summary = {
        "kind": "predict_readable_summary",
        "baseline_judgment": {
            "direction": direction,
            "strength": strength,
            "risk_level": risk,
            "confidence": confidence,
            "text": f"{direction}（强度：{strength}，风险：{risk}，置信度：{_confidence_label(confidence)}）",
        },
        "open_projection": {
            "tendency": open_label,
            "watch": _open_watch(open_label),
            "text": f"更可能{open_label}；{_open_watch(open_label)}",
        },
        "close_projection": {
            "tendency": close_label,
            "watch": _close_watch(close_label),
            "text": f"更可能{close_label}；{_close_watch(close_label)}",
        },
        "rationale": rationale,
        "risk_reminders": _risk_lines(predict, scan, advisory),
        "ai_polish": ai_polish or None,
    }
    summary["summary_text"] = _summary_text(summary)
    return summary
