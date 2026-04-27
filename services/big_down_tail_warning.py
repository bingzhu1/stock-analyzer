from __future__ import annotations

import ast
import json
from typing import Any


TAIL_COMPRESSION_THRESHOLD = 4
STRONG_WARNING_SCORE = 5
DOWNGRADE_COUNTER_THRESHOLD = 2


def _safe_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed != parsed:
        return None
    return parsed


def _safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or value == "":
        return False
    if isinstance(value, (int, float)):
        return bool(int(value))
    return str(value).strip().lower() in {"true", "1", "yes"}


def _split_pipe(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    return [item.strip() for item in str(value).split("|") if item.strip()]


def _parse_state_probabilities(value: Any) -> dict[str, float]:
    if isinstance(value, dict):
        payload = value
    elif value is None or value == "":
        return {}
    else:
        text = str(value)
        try:
            payload = json.loads(text)
        except Exception:
            try:
                payload = ast.literal_eval(text)
            except Exception:
                return {}
    if not isinstance(payload, dict):
        return {}
    result: dict[str, float] = {}
    for key, raw in payload.items():
        parsed = _safe_float(raw)
        if parsed is not None:
            result[str(key)] = parsed
    return result


def _resolve_probability(row: dict[str, Any], direct_key: str, state_key: str) -> float | None:
    direct = _safe_float(row.get(direct_key))
    if direct is not None:
        return direct
    state_probabilities = _parse_state_probabilities(row.get("state_probabilities"))
    return _safe_float(state_probabilities.get(state_key))


def _append_reason(reasons: list[str], condition: bool, text: str) -> int:
    if condition:
        reasons.append(text)
        return 1
    return 0


def _downgrade_warning(level: str) -> str:
    if level == "strong_warning":
        return "warning"
    if level == "warning":
        return "none"
    return "none"


def build_big_down_tail_warning(row: dict[str, Any]) -> dict[str, Any]:
    forced_states_raw = row.get("forced_excluded_states")
    predicted_state_raw = row.get("predicted_state")
    forced_states = _split_pipe(forced_states_raw)
    predicted_state = str(predicted_state_raw or "").strip()
    p_big_down = _resolve_probability(row, "p_大跌", "大跌")
    p_big_up = _resolve_probability(row, "p_大涨", "大涨")
    vol_ratio20 = _safe_float(row.get("vol_ratio20"))
    ret3 = _safe_float(row.get("ret3"))
    ret5 = _safe_float(row.get("ret5"))
    historical_big_down_rate = _safe_float(row.get("historical_big_down_rate"))

    missing_fields: list[str] = []
    if forced_states_raw in (None, ""):
        missing_fields.append("forced_excluded_states")
    if predicted_state_raw in (None, ""):
        missing_fields.append("predicted_state")
    if p_big_down is None:
        missing_fields.append("p_大跌")
    if p_big_up is None:
        missing_fields.append("p_大涨")

    contradiction_available = row.get("contradiction_inputs_available")
    contradiction_inputs_missing = contradiction_available is not None and not _safe_bool(contradiction_available)
    data_limited = bool(missing_fields) or contradiction_inputs_missing

    had_big_down_exclusion = "大跌" in forced_states
    dual_extremes = "大涨" in forced_states and "大跌" in forced_states
    base_candidate = dual_extremes or (
        predicted_state == "震荡"
        and p_big_down is not None
        and p_big_down <= 0.05
        and p_big_up is not None
        and p_big_up <= 0.05
    )

    reasons: list[str] = []
    score = 0
    score += _append_reason(reasons, dual_extremes, "系统同时排除了大涨和大跌两端状态")
    score += _append_reason(reasons, predicted_state == "震荡", "预测结果偏向震荡")
    score += _append_reason(
        reasons,
        p_big_down is not None and p_big_down <= 0.05,
        "大跌概率被压低到 0.05 以下",
    )
    score += _append_reason(
        reasons,
        p_big_up is not None and p_big_up <= 0.05,
        "大涨概率被压低到 0.05 以下",
    )
    score += _append_reason(
        reasons,
        _safe_bool(row.get("is_high_vol_regime")) or _safe_bool(row.get("is_crisis_regime")),
        "当前处于高波动或危机环境",
    )
    score += _append_reason(
        reasons,
        vol_ratio20 is not None and vol_ratio20 >= 1.2,
        "近期量能明显放大",
    )
    score += _append_reason(
        reasons,
        (ret3 is not None and abs(ret3) >= 3) or (ret5 is not None and abs(ret5) >= 5),
        "近 3/5 日波动已经放大",
    )

    counter_count = 0
    if str(row.get("market_regime_label") or "").strip().lower() == "calm":
        score -= 1
        counter_count += 1
        reasons.append("降级因素：市场处于 calm，尾部风险证据偏弱")
    if vol_ratio20 is not None and vol_ratio20 < 0.7:
        score -= 1
        counter_count += 1
        reasons.append("降级因素：量能不足，双尾收缩信号不够强")
    if (
        str(row.get("historical_sample_confidence") or "").strip().lower() == "high"
        and historical_big_down_rate is not None
        and historical_big_down_rate == 0
    ):
        score -= 1
        counter_count += 1
        reasons.append("降级因素：高置信历史样本中未出现大跌")

    tail_compression_triggered = bool(had_big_down_exclusion and base_candidate and score >= TAIL_COMPRESSION_THRESHOLD)

    warning_level = "none"
    if tail_compression_triggered:
        warning_level = "warning"
        if score >= STRONG_WARNING_SCORE and counter_count < DOWNGRADE_COUNTER_THRESHOLD:
            warning_level = "strong_warning"

    if counter_count >= DOWNGRADE_COUNTER_THRESHOLD:
        warning_level = _downgrade_warning(warning_level)

    if data_limited:
        warning_level = _downgrade_warning(warning_level)
        if missing_fields:
            reasons.append(f"数据受限：缺少关键字段 {', '.join(missing_fields)}")
        if contradiction_inputs_missing:
            reasons.append("数据受限：contradiction_inputs_available 为 false")

    if not had_big_down_exclusion:
        explanation = "本次结果没有否定“大跌”，因此不生成大跌侧双尾收缩提醒。"
    elif not tail_compression_triggered:
        if data_limited:
            explanation = "本次虽然否定了大跌，但双尾收缩证据不足，且关键输入存在缺失，因此暂不输出提醒。"
        else:
            explanation = "本次虽然否定了大跌，但未达到双尾收缩告警阈值，因此暂不输出提醒。"
    elif warning_level == "strong_warning":
        explanation = (
            "系统当前同时压低大涨和大跌概率，预测偏向震荡。"
            "但在历史复盘中，这类双尾收缩场景仍可能出现尾部大跌。"
            "因此本次“否定大跌”不建议作为强排除项。"
        )
    elif warning_level == "warning":
        explanation = (
            "系统当前对大涨和大跌两端都较保守，结果偏向震荡。"
            "这类双尾收缩场景下，“否定大跌”的可靠性会下降，建议不要把本次大跌排除理解为强结论。"
        )
    else:
        explanation = "双尾收缩信号存在，但已被降级因素或数据受限条件削弱，因此本次不输出正式提醒。"

    return {
        "had_big_down_exclusion": had_big_down_exclusion,
        "tail_compression_triggered": tail_compression_triggered,
        "warning_level": warning_level,
        "tail_compression_score": score,
        "reasons": reasons,
        "missing_fields": missing_fields,
        "data_limited": data_limited,
        "explanation": explanation,
    }
