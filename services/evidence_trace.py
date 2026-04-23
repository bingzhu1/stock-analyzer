"""Deterministic evidence trace helpers for projection / predict outputs."""

from __future__ import annotations

from typing import Any

from services.predict_summary import (
    close_tendency_label,
    direction_label,
    open_tendency_label,
)


_GAP_LABELS = {
    "gap_up": "高开缺口",
    "gap_down": "低开缺口",
    "flat": "平开附近",
    "unknown": "开盘状态未知",
}
_INTRADAY_LABELS = {
    "high_go": "收于开盘价上方",
    "low_go": "收于开盘价下方",
    "range": "日内震荡",
    "unknown": "日内结构未知",
}
_VOLUME_LABELS = {
    "expanding": "量能放大",
    "shrinking": "量能收缩",
    "normal": "量能正常",
    "unknown": "量能状态未知",
}
_PRICE_LABELS = {
    "bullish": "价格/阶段偏多",
    "bearish": "价格/阶段偏空",
    "neutral": "价格/阶段中性",
    "unknown": "价格/阶段未知",
}
_HIST_LABELS = {
    "up_bias": "历史样本偏多",
    "down_bias": "历史样本偏空",
    "mixed": "历史分布混杂",
    "insufficient_sample": "历史样本不足",
}
_CONFIRMATION_LABELS = {
    "confirmed": "同业确认",
    "diverging": "同业背离",
    "mixed": "同业信号混杂",
    "unknown": "同业确认未知",
}
_RS_LABELS = {
    "stronger": "强于",
    "weaker": "弱于",
    "neutral": "接近",
    "unavailable": "不可用",
}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_lines(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value:
        return [str(value).strip()]
    return []


def _clean_str(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() == "none" else text


def _dedupe(lines: list[str]) -> list[str]:
    return list(dict.fromkeys(line for line in lines if str(line).strip()))


def _format_rs(summary: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("vs_nvda", "vs_soxx", "vs_qqq"):
        value = _clean_str(summary.get(key, ""))
        if not value:
            continue
        peer = key.replace("vs_", "").upper()
        parts.append(f"{peer}：{_RS_LABELS.get(value, value)}")
    return "；".join(parts) if parts else "暂无可用同业对照"


def _advisory_participated(advisory: dict[str, Any]) -> bool:
    if not advisory:
        return False
    if _as_lines(advisory.get("reminder_lines")):
        return True
    try:
        if int(advisory.get("matched_count") or 0) > 0:
            return True
    except (TypeError, ValueError):
        pass
    block = _as_dict(advisory.get("advisory_block"))
    if _as_lines(block.get("reminder_lines")):
        return True
    try:
        return int(block.get("matched_count") or 0) > 0
    except (TypeError, ValueError):
        return False


def _tool_trace(
    *,
    scan_result: dict[str, Any],
    predict_result: dict[str, Any],
    projection_report: dict[str, Any],
    advisory: dict[str, Any],
) -> list[str]:
    tools: list[str] = []
    if scan_result:
        tools.append("scan")
    if _as_dict(scan_result.get("historical_match_summary")):
        tools.append("historical_match")
    if (
        _as_dict(scan_result.get("relative_strength_5d_summary"))
        or _as_dict(scan_result.get("relative_strength_same_day_summary"))
        or scan_result.get("confirmation_state")
    ):
        tools.append("peer_confirmation")
    if predict_result:
        tools.append("predict_summary")
    if projection_report:
        tools.append("projection_report")
    if _advisory_participated(advisory):
        tools.append("memory_feedback")
    return tools or ["fallback_projection_trace"]


def _final_conclusion(
    *,
    predict_result: dict[str, Any],
    projection_report: dict[str, Any],
) -> dict[str, Any]:
    if projection_report:
        return {
            "direction": projection_report.get("direction", "中性"),
            "open_tendency": projection_report.get("open_tendency", "平开"),
            "close_tendency": projection_report.get("close_tendency", "震荡"),
            "confidence": projection_report.get("confidence", "low"),
        }
    return {
        "direction": direction_label(predict_result.get("final_bias")),
        "open_tendency": open_tendency_label(predict_result.get("open_tendency")),
        "close_tendency": close_tendency_label(predict_result.get("close_tendency")),
        "confidence": str(predict_result.get("final_confidence", "low")),
    }


def _key_observations(
    *,
    scan_result: dict[str, Any],
    predict_result: dict[str, Any],
    projection_report: dict[str, Any],
    advisory: dict[str, Any],
) -> list[str]:
    lines: list[str] = []
    gap = _clean_str(scan_result.get("avgo_gap_state", ""))
    intraday = _clean_str(scan_result.get("avgo_intraday_state", ""))
    volume = _clean_str(scan_result.get("avgo_volume_state", ""))
    price = _clean_str(scan_result.get("avgo_price_state", ""))
    if gap or intraday or volume or price:
        lines.append(
            "结构观察："
            f"开盘={_GAP_LABELS.get(gap, gap or '未知')}，"
            f"日内={_INTRADAY_LABELS.get(intraday, intraday or '未知')}，"
            f"量能={_VOLUME_LABELS.get(volume, volume or '未知')}，"
            f"阶段={_PRICE_LABELS.get(price, price or '未知')}。"
        )

    hist = _as_dict(scan_result.get("historical_match_summary"))
    if hist:
        lines.append(
            "历史匹配："
            f"完全匹配 {hist.get('exact_match_count', 0)}，"
            f"近似匹配 {hist.get('near_match_count', 0)}，"
            f"历史倾向={_HIST_LABELS.get(str(hist.get('dominant_historical_outcome', '')), hist.get('dominant_historical_outcome', '未知'))}。"
        )

    confirmation = _clean_str(scan_result.get("confirmation_state", ""))
    rs_5d = _as_dict(scan_result.get("relative_strength_5d_summary") or scan_result.get("relative_strength_summary"))
    rs_day = _as_dict(scan_result.get("relative_strength_same_day_summary"))
    if confirmation or rs_5d or rs_day:
        lines.append(
            "同业确认："
            f"{_CONFIRMATION_LABELS.get(confirmation, confirmation or '未知')}；"
            f"5日 {_format_rs(rs_5d)}；当日 {_format_rs(rs_day)}。"
        )

    support = _as_lines(predict_result.get("supporting_factors"))
    conflict = _as_lines(predict_result.get("conflicting_factors"))
    if support:
        lines.append("Predict 支持因子：" + "；".join(support[:4]) + "。")
    if conflict:
        lines.append("Predict 冲突因子：" + "；".join(conflict[:4]) + "。")

    risks = _as_lines(projection_report.get("risk_reminders"))
    if not risks and advisory:
        risks = _as_lines(advisory.get("reminder_lines"))
    if risks:
        lines.append("风险观察：" + "；".join(risks[:3]) + "。")

    return _dedupe(lines) or ["结构化输入不足，证据链按低信息量安全降级。"]


def _decision_steps(
    *,
    scan_result: dict[str, Any],
    predict_result: dict[str, Any],
    final_conclusion: dict[str, Any],
) -> list[str]:
    steps: list[str] = []
    gap = _clean_str(scan_result.get("avgo_gap_state")) or "unknown"
    intraday = _clean_str(scan_result.get("avgo_intraday_state")) or "unknown"
    volume = _clean_str(scan_result.get("avgo_volume_state")) or "unknown"
    hist = _as_dict(scan_result.get("historical_match_summary"))
    hist_outcome = str(hist.get("dominant_historical_outcome", ""))
    confirmation = _clean_str(scan_result.get("confirmation_state")) or "unknown"

    steps.append(
        "观察："
        f"gap state = {gap}（{_GAP_LABELS.get(gap, gap)}）"
        " → 结论影响："
        f"开盘倾向保持为 {final_conclusion['open_tendency']}。"
    )
    steps.append(
        "观察："
        f"intraday state = {intraday}（{_INTRADAY_LABELS.get(intraday, intraday)}）"
        " → 结论影响："
        f"收盘倾向保持为 {final_conclusion['close_tendency']}。"
    )
    if hist:
        steps.append(
            "观察："
            f"historical outcome = {hist_outcome or 'unknown'}（{_HIST_LABELS.get(hist_outcome, hist_outcome or '未知')}）"
            " → 结论影响："
            f"方向结论不脱离既有历史匹配背景，最终方向为 {final_conclusion['direction']}。"
        )
    if confirmation:
        steps.append(
            "观察："
            f"peer confirmation = {confirmation}（{_CONFIRMATION_LABELS.get(confirmation, confirmation)}）"
            " → 结论影响："
            f"confidence 保持为 {final_conclusion['confidence']}。"
        )
    if volume:
        steps.append(
            "观察："
            f"volume state = {volume}（{_VOLUME_LABELS.get(volume, volume)}）"
            " → 结论影响："
            "需要用下一交易日量能验证方向延续性。"
        )
    if predict_result:
        steps.append(
            "观察："
            f"Predict final_bias = {predict_result.get('final_bias', 'neutral')}, "
            f"final_confidence = {predict_result.get('final_confidence', 'low')}"
            " → 结论影响："
            "最终结论直接沿用规则层 projection / predict 输出。"
        )
    return _dedupe(steps)


def _verification_points(scan_result: dict[str, Any], final_conclusion: dict[str, Any]) -> list[str]:
    points = [
        "观察开盘后 30 分钟是否确认开盘倾向，避免只看集合竞价。",
        f"验证收盘结构是否继续支持“{final_conclusion['close_tendency']}”判断。",
        "观察量能是否放大，避免无量修复或无量下跌造成误判。",
    ]
    if (
        scan_result.get("confirmation_state")
        or scan_result.get("relative_strength_5d_summary")
        or scan_result.get("relative_strength_same_day_summary")
    ):
        points.append("观察 NVDA / SOXX / QQQ 是否继续确认或背离。")
    hist = _as_dict(scan_result.get("historical_match_summary"))
    if str(hist.get("dominant_historical_outcome", "")) in {"mixed", "insufficient_sample"}:
        points.append("历史分布不集中时，优先验证盘中承接和风险控制。")
    return _dedupe(points)


def build_projection_evidence_trace(
    payload: dict[str, Any] | None = None,
    *,
    predict_result: dict[str, Any] | None = None,
    scan_result: dict[str, Any] | None = None,
    projection_report: dict[str, Any] | None = None,
    advisory: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a stable evidence trace from existing structured projection inputs.

    The trace is a presentation layer. It does not score, forecast, or expose
    private reasoning; every line is derived from the supplied structured fields.
    """
    data = payload or {}
    predict = _as_dict(predict_result if predict_result is not None else data.get("predict_result"))
    scan = _as_dict(scan_result if scan_result is not None else data.get("scan_result"))
    report = _as_dict(projection_report if projection_report is not None else data.get("projection_report"))
    adv = _as_dict(advisory if advisory is not None else data.get("advisory"))
    final = _final_conclusion(predict_result=predict, projection_report=report)
    return {
        "kind": "projection_evidence_trace",
        "tool_trace": _tool_trace(
            scan_result=scan,
            predict_result=predict,
            projection_report=report,
            advisory=adv,
        ),
        "key_observations": _key_observations(
            scan_result=scan,
            predict_result=predict,
            projection_report=report,
            advisory=adv,
        ),
        "decision_steps": _decision_steps(
            scan_result=scan,
            predict_result=predict,
            final_conclusion=final,
        ),
        "final_conclusion": final,
        "verification_points": _verification_points(scan, final),
    }
