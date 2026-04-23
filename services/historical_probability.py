"""Enhanced projection v2 historical probability layer.

This module upgrades the Task 041 wrapper into a small, explainable historical
validator. It supports three evidence paths:

1. exact code matches from coded history
2. simple similar-window matching from feature history
3. fallback to existing historical summary fields when richer data is absent

The layer stays safely degradable and keeps a fixed output shape.
"""

from __future__ import annotations

from typing import Any

import pandas as pd


_RATE_FIELDS = ("up_rate", "down_rate", "gap_up_rate", "strong_close_rate")
_MIN_LAYER_SAMPLE_COUNT = 3
_DATE_COLUMNS = ("Date", "date", "TargetDate", "target_date", "scan_timestamp")
_CODE_COLUMNS = ("Code", "code", "TargetCode", "target_code", "pattern_code", "PatternCode")
_DICT_CODE_KEYS = (
    "current_code",
    "target_code",
    "code",
    "pattern_code",
    "avgo_pattern_code",
)
_MISSING_OUTCOMES = {"", "none", "null", "missing"}
_INSUFFICIENT_OUTCOMES = {"insufficient", "insufficient_sample"}
_BULLISH_OUTCOMES = {"up_bias", "bullish", "supports_bullish"}
_BEARISH_OUTCOMES = {"down_bias", "bearish", "supports_bearish"}
_STRONG_CLOSE_LABELS = {"strong", "strong_close", "偏强", "收强", "上涨"}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_frame(value: Any) -> pd.DataFrame:
    return value.copy() if isinstance(value, pd.DataFrame) else pd.DataFrame()


def _clean_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _safe_int(value: Any) -> int:
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return 0


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_rate(value: Any) -> float | None:
    rate = _safe_float(value)
    if rate is None:
        return None
    if rate > 1 and rate <= 100:
        rate = rate / 100
    if rate < 0 or rate > 1:
        return None
    return round(rate, 4)


def _primary_direction(primary_analysis: dict[str, Any]) -> str:
    direction = str(primary_analysis.get("direction") or "unknown").strip()
    return direction if direction in {"偏多", "偏空", "中性"} else "unknown"


def _sample_count(summary: dict[str, Any]) -> int:
    explicit = summary.get("sample_count")
    if explicit is None:
        explicit = summary.get("match_sample_size")
    if explicit is not None:
        return _safe_int(explicit)
    return _safe_int(summary.get("exact_match_count")) + _safe_int(summary.get("near_match_count"))


def _sample_quality(sample_count: int, *, source_missing: bool) -> str:
    if source_missing:
        return "missing"
    if sample_count < 3:
        return "insufficient"
    if sample_count < 8:
        return "limited"
    return "enough"


def _historical_bias(summary: dict[str, Any], sample_quality: str) -> str:
    if sample_quality == "missing":
        return "missing"
    if sample_quality == "insufficient":
        return "insufficient"
    dominant = _clean_str(
        summary.get("historical_bias")
        or summary.get("dominant_historical_outcome")
        or summary.get("dominant_outcome")
    )
    if dominant in _BULLISH_OUTCOMES:
        return "supports_bullish"
    if dominant in _BEARISH_OUTCOMES:
        return "supports_bearish"
    if dominant == "mixed":
        return "mixed"
    if dominant in _INSUFFICIENT_OUTCOMES:
        return "insufficient"
    if dominant in _MISSING_OUTCOMES:
        return "missing"
    return "mixed"


def _impact(primary_direction: str, historical_bias: str) -> str:
    if historical_bias in {"missing", "insufficient"}:
        return "missing"
    if historical_bias == "mixed":
        return "caution"
    if primary_direction == "偏多":
        return "support" if historical_bias == "supports_bullish" else "caution"
    if primary_direction == "偏空":
        return "support" if historical_bias == "supports_bearish" else "caution"
    return "no_effect"


def _rates(summary: dict[str, Any]) -> dict[str, float | None]:
    return {field: _safe_rate(summary.get(field)) for field in _RATE_FIELDS}


def _coerce_timestamp(value: Any) -> pd.Timestamp | None:
    if value is None:
        return None
    ts = pd.to_datetime(value, errors="coerce")
    return None if pd.isna(ts) else ts.normalize()


def _find_column(df: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
    lowered = {str(col).lower(): col for col in df.columns}
    for candidate in candidates:
        if candidate.lower() in lowered:
            return str(lowered[candidate.lower()])
    return None


def _date_column(df: pd.DataFrame) -> str | None:
    column = _find_column(df, _DATE_COLUMNS)
    if column is not None:
        return column
    for name in df.columns:
        if "date" in str(name).lower():
            return str(name)
    return None


def _code_column(df: pd.DataFrame) -> str | None:
    column = _find_column(df, _CODE_COLUMNS)
    if column is not None:
        return column
    for name in df.columns:
        if "code" in str(name).lower():
            return str(name)
    return None


def _prepare_history_frame(frame: pd.DataFrame, as_of_date: str | None) -> tuple[pd.DataFrame, str | None]:
    df = _as_frame(frame)
    if df.empty:
        return df, None
    date_col = _date_column(df)
    if date_col is None:
        return pd.DataFrame(), None
    prepared = df.copy()
    prepared["_hp_date"] = pd.to_datetime(prepared[date_col], errors="coerce").dt.normalize()
    prepared = prepared[prepared["_hp_date"].notna()].sort_values("_hp_date").reset_index(drop=True)
    cutoff = _coerce_timestamp(as_of_date)
    if cutoff is not None:
        prepared = prepared[prepared["_hp_date"] <= cutoff].reset_index(drop=True)
    return prepared, date_col


def _resolve_current_row(df: pd.DataFrame, as_of_date: str | None) -> pd.Series | None:
    if df.empty:
        return None
    cutoff = _coerce_timestamp(as_of_date)
    if cutoff is not None:
        rows = df[df["_hp_date"] == cutoff]
        if not rows.empty:
            return rows.iloc[-1]
    return df.iloc[-1]


def _normalize_code(raw_code: Any) -> str:
    if pd.isna(raw_code):
        return ""
    code = str(raw_code).strip()
    if not code or code.lower() in {"nan", "none", "<na>"}:
        return ""
    if code.endswith(".0"):
        integer_part, decimal_part = code.split(".", maxsplit=1)
        if decimal_part and set(decimal_part) == {"0"}:
            code = integer_part
    return code


def _first_non_empty_code(*sources: Any) -> str:
    for source in sources:
        if isinstance(source, dict):
            for key in _DICT_CODE_KEYS:
                code = _normalize_code(source.get(key))
                if code:
                    return code
    return ""


def _extract_current_code(
    primary: dict[str, Any],
    source_summary: dict[str, Any],
    context: dict[str, Any],
    current_row: pd.Series | None,
    code_col: str | None,
) -> str:
    explicit = _first_non_empty_code(context, primary, source_summary)
    if explicit:
        return explicit
    if current_row is None or code_col is None:
        return ""
    return _normalize_code(current_row.get(code_col))


def _value_from_row(row: pd.Series | None, *candidates: str) -> Any:
    if row is None:
        return None
    lowered = {str(col).lower(): col for col in row.index}
    for candidate in candidates:
        if candidate in row.index:
            return row.get(candidate)
        match = lowered.get(candidate.lower())
        if match is not None:
            return row.get(match)
    return None


def _next_close_change_from_reference_row(row: pd.Series | None) -> float | None:
    value = _value_from_row(
        row,
        "NextCloseMove",
        "next_close_move",
        "next_close_change",
    )
    return _safe_float(value)


def _close_change_from_same_day_row(row: pd.Series | None) -> float | None:
    """Return same-day close change as a fractional ratio.

    Sources like outcome_capture.actual_close_change and scanner.C_move both
    use ratio semantics here (0.02 means +2%), not percentage points.
    """
    value = _value_from_row(
        row,
        "CloseChange",
        "close_change",
        "actual_close_change",
        "C_move",
    )
    numeric = _safe_float(value)
    if numeric is not None:
        return numeric
    close_value = _safe_float(_value_from_row(row, "Close", "close", "actual_close"))
    prev_close = _safe_float(_value_from_row(row, "PrevClose", "prev_close", "actual_prev_close"))
    if close_value is None or prev_close in {None, 0}:
        return None
    return (close_value - prev_close) / prev_close


def _next_gap_up_from_reference_row(row: pd.Series | None) -> bool | None:
    value = _value_from_row(
        row,
        "NextOpenChange",
        "next_open_change",
    )
    numeric = _safe_float(value)
    if numeric is None:
        return None
    return numeric > 0


def _gap_up_from_same_day_row(row: pd.Series | None) -> bool | None:
    label = _clean_str(_value_from_row(row, "open_label", "OpenLabel"))
    if label:
        if "高开" in label or "gap_up" in label:
            return True
        if "低开" in label or "gap_down" in label:
            return False
    value = _value_from_row(
        row,
        "actual_open_change",
        "open_change",
        "O_gap",
    )
    numeric = _safe_float(value)
    if numeric is None:
        return None
    return numeric > 0


def _next_strong_close_from_reference_row(row: pd.Series | None) -> bool | None:
    explicit = _value_from_row(
        row,
        "next_strong_close",
        "NextStrongClose",
    )
    if isinstance(explicit, bool):
        return explicit
    return None


def _strong_close_from_same_day_row(row: pd.Series | None) -> bool | None:
    explicit = _value_from_row(
        row,
        "strong_close",
        "StrongClose",
        "is_strong_close",
        "IsStrongClose",
    )
    if isinstance(explicit, bool):
        return explicit
    text = _clean_str(_value_from_row(row, "close_label", "CloseLabel"))
    if text:
        return any(label in text for label in _STRONG_CLOSE_LABELS)
    close_change = _close_change_from_same_day_row(row)
    if close_change is None:
        return None
    return close_change >= 0.01


def _next_day_metrics(reference_row: pd.Series | None, next_row: pd.Series | None) -> dict[str, Any]:
    close_change = _next_close_change_from_reference_row(reference_row)
    if close_change is None:
        close_change = _close_change_from_same_day_row(next_row)
    gap_up = _next_gap_up_from_reference_row(reference_row)
    if gap_up is None:
        gap_up = _gap_up_from_same_day_row(next_row)
    strong_close = _next_strong_close_from_reference_row(reference_row)
    if strong_close is None:
        strong_close = _strong_close_from_same_day_row(next_row)
    return {
        "close_change": close_change,
        "up": None if close_change is None else close_change > 0,
        "down": None if close_change is None else close_change < 0,
        "gap_up": gap_up,
        "strong_close": strong_close,
    }


def _aggregate_samples(samples: list[dict[str, Any]]) -> dict[str, Any]:
    sample_count = len(samples)
    if sample_count <= 0:
        return {
            "sample_count": 0,
            "up_rate": None,
            "down_rate": None,
            "gap_up_rate": None,
            "strong_close_rate": None,
        }
    gap_samples = [sample["gap_up"] for sample in samples if sample.get("gap_up") is not None]
    strong_samples = [sample["strong_close"] for sample in samples if sample.get("strong_close") is not None]
    return {
        "sample_count": sample_count,
        "up_rate": round(sum(1 for sample in samples if sample.get("up")) / sample_count, 4),
        "down_rate": round(sum(1 for sample in samples if sample.get("down")) / sample_count, 4),
        "gap_up_rate": (
            round(sum(1 for value in gap_samples if value) / len(gap_samples), 4)
            if gap_samples
            else None
        ),
        "strong_close_rate": (
            round(sum(1 for value in strong_samples if value) / len(strong_samples), 4)
            if strong_samples
            else None
        ),
    }


def _format_percent(rate: float | None) -> str:
    if rate is None:
        return "n/a"
    return f"{rate * 100:.1f}%"


def _build_code_match(
    *,
    primary: dict[str, Any],
    source_summary: dict[str, Any],
    context: dict[str, Any],
    coded_history: pd.DataFrame,
    as_of_date: str | None,
) -> tuple[dict[str, Any], list[str]]:
    result = {
        "sample_count": 0,
        "up_rate": None,
        "down_rate": None,
        "gap_up_rate": None,
        "strong_close_rate": None,
        "summary": "同编码层缺少可用样本。",
    }
    warnings: list[str] = []
    prepared, _date_col = _prepare_history_frame(coded_history, as_of_date)
    if prepared.empty:
        warnings.append("code_match 缺少 coded_history 或日期列。")
        result["summary"] = "同编码层缺少 coded_history，已降级。"
        return result, warnings

    code_col = _code_column(prepared)
    current_row = _resolve_current_row(prepared, as_of_date)
    current_code = _extract_current_code(primary, source_summary, context, current_row, code_col)
    if not current_code:
        warnings.append("code_match 无法解析当前编码。")
        result["summary"] = "同编码层无法解析当前编码，已降级。"
        return result, warnings

    current_date = current_row["_hp_date"] if current_row is not None else None
    if current_date is None:
        warnings.append("code_match 无法定位当前日期。")
        result["summary"] = "同编码层无法定位当前日期，已降级。"
        return result, warnings

    samples: list[dict[str, Any]] = []
    for index in range(len(prepared) - 1):
        row = prepared.iloc[index]
        next_row = prepared.iloc[index + 1]
        row_code = _normalize_code(row.get(code_col)) if code_col is not None else ""
        if row_code != current_code:
            continue
        if row["_hp_date"] >= current_date:
            continue
        if next_row["_hp_date"] > current_date:
            continue
        metrics = _next_day_metrics(row, next_row)
        if metrics["close_change"] is None:
            continue
        samples.append(metrics)

    aggregated = _aggregate_samples(samples)
    result.update(aggregated)
    if aggregated["sample_count"] <= 0:
        warnings.append(f"code_match 没有找到可统计的同编码样本：code={current_code}。")
        result["summary"] = f"同编码样本不足：当前编码 {current_code} 没有可统计样本。"
        return result, warnings

    if aggregated["sample_count"] < 3:
        warnings.append(
            f"code_match 同编码样本不足：code={current_code}, sample_count={aggregated['sample_count']}。"
        )
        result["summary"] = (
            f"同编码样本 {aggregated['sample_count']} 个，当前编码 {current_code} 样本仍偏少。"
        )
        return result, warnings

    result["summary"] = (
        f"同编码样本 {aggregated['sample_count']} 个，"
        f"上涨率 {_format_percent(aggregated['up_rate'])}，"
        f"下跌率 {_format_percent(aggregated['down_rate'])}。"
    )
    return result, warnings


def _window_size(context: dict[str, Any]) -> int:
    value = context.get("window_days") or context.get("similarity_window_days") or 20
    try:
        size = int(value)
    except (TypeError, ValueError):
        return 20
    return max(size, 2)


def _top_k(context: dict[str, Any]) -> int:
    value = context.get("top_k") or context.get("window_top_k") or 5
    try:
        size = int(value)
    except (TypeError, ValueError):
        return 5
    return max(size, 1)


def _feature_columns(df: pd.DataFrame, *, date_col: str | None) -> list[str]:
    excluded_exact = {date_col, "_hp_date"}
    columns: list[str] = []
    for name in df.columns:
        if name in excluded_exact:
            continue
        text = str(name).lower()
        if any(token in text for token in ("next", "future", "actual", "target", "label", "outcome")):
            continue
        if "code" in text:
            continue
        if pd.api.types.is_numeric_dtype(df[name]):
            columns.append(str(name))
    return columns


def _window_distance(
    current_window: pd.DataFrame,
    candidate_window: pd.DataFrame,
    feature_cols: list[str],
) -> float:
    current_values = current_window[feature_cols].astype(float)
    candidate_values = candidate_window[feature_cols].astype(float)
    center = current_values.mean()
    scale = current_values.std(ddof=0).replace(0, 1.0).fillna(1.0)
    normalized_current = (current_values - center) / scale
    normalized_candidate = (candidate_values - center) / scale
    diff = (normalized_candidate.to_numpy(dtype=float) - normalized_current.to_numpy(dtype=float))
    return float(abs(diff).mean())


def _build_window_similarity(
    *,
    feature_history: pd.DataFrame,
    context: dict[str, Any],
    as_of_date: str | None,
) -> tuple[dict[str, Any], list[str]]:
    result = {
        "sample_count": 0,
        "up_rate": None,
        "down_rate": None,
        "gap_up_rate": None,
        "strong_close_rate": None,
        "avg_similarity": None,
        "summary": "相似窗口层缺少可用样本。",
    }
    warnings: list[str] = []
    prepared, date_col = _prepare_history_frame(feature_history, as_of_date)
    if prepared.empty:
        warnings.append("window_similarity 缺少 feature_history 或日期列。")
        result["summary"] = "相似窗口层缺少 feature_history，已降级。"
        return result, warnings

    current_row = _resolve_current_row(prepared, as_of_date)
    if current_row is None:
        warnings.append("window_similarity 无法定位当前日期。")
        result["summary"] = "相似窗口层无法定位当前日期，已降级。"
        return result, warnings

    current_end_idx = int(current_row.name)
    window_days = _window_size(context)
    top_k = _top_k(context)
    if current_end_idx + 1 < window_days:
        warnings.append(
            f"window_similarity 历史长度不足：需要 {window_days} 天，实际 {current_end_idx + 1} 天。"
        )
        result["summary"] = f"相似窗口层缺少最近 {window_days} 天完整特征，已降级。"
        return result, warnings

    feature_cols = _feature_columns(prepared, date_col=date_col)
    if not feature_cols:
        warnings.append("window_similarity 缺少可用于匹配的数值特征列。")
        result["summary"] = "相似窗口层缺少可匹配特征，已降级。"
        return result, warnings

    current_start_idx = current_end_idx - window_days + 1
    current_window = prepared.iloc[current_end_idx - window_days + 1: current_end_idx + 1]
    matches: list[dict[str, Any]] = []
    for end_idx in range(window_days - 1, current_start_idx - 1):
        candidate_window = prepared.iloc[end_idx - window_days + 1: end_idx + 1]
        if len(candidate_window) != window_days:
            continue
        next_row = prepared.iloc[end_idx + 1]
        metrics = _next_day_metrics(prepared.iloc[end_idx], next_row)
        if metrics["close_change"] is None:
            continue
        distance = _window_distance(current_window, candidate_window, feature_cols)
        similarity = round(1 / (1 + distance), 4)
        matches.append({"distance": distance, "similarity": similarity, **metrics})

    if not matches:
        warnings.append("window_similarity 没有找到可统计的历史窗口样本。")
        result["summary"] = "相似窗口层没有找到可统计的历史窗口样本。"
        return result, warnings

    matches.sort(key=lambda item: item["distance"])
    selected = matches[:top_k]
    aggregated = _aggregate_samples(selected)
    result.update(aggregated)
    result["avg_similarity"] = round(
        sum(float(item["similarity"]) for item in selected) / len(selected),
        4,
    )
    if aggregated["sample_count"] < 3:
        warnings.append(
            f"window_similarity 相似窗口样本不足：sample_count={aggregated['sample_count']}。"
        )
        result["summary"] = (
            f"相似窗口样本 {aggregated['sample_count']} 个，平均相似度 "
            f"{_format_percent(result['avg_similarity'])}，但样本仍偏少。"
        )
        return result, warnings

    result["summary"] = (
        f"相似窗口样本 {aggregated['sample_count']} 个，"
        f"平均相似度 {_format_percent(result['avg_similarity'])}，"
        f"上涨率 {_format_percent(aggregated['up_rate'])}。"
    )
    return result, warnings


def _fallback_probability(source_summary: dict[str, Any]) -> dict[str, Any]:
    sample_count = _sample_count(source_summary)
    source_missing = not bool(source_summary)
    sample_quality = _sample_quality(sample_count, source_missing=source_missing)
    rates = _rates(source_summary)
    return {
        "sample_count": sample_count,
        "sample_quality": sample_quality,
        "historical_bias": _historical_bias(source_summary, sample_quality),
        **rates,
    }


def _available_probability_layer(layer: dict[str, Any]) -> bool:
    return _safe_int(layer.get("sample_count")) > 0 and (
        layer.get("up_rate") is not None or layer.get("down_rate") is not None
    )


def _eligible_probability_layer(layer: dict[str, Any]) -> bool:
    return _available_probability_layer(layer) and _safe_int(layer.get("sample_count")) >= _MIN_LAYER_SAMPLE_COUNT


def _weighted_rate(layers: list[dict[str, Any]], field: str) -> float | None:
    numerator = 0.0
    denominator = 0
    for layer in layers:
        rate = _safe_rate(layer.get(field))
        weight = _safe_int(layer.get("sample_count"))
        if rate is None or weight <= 0:
            continue
        numerator += rate * weight
        denominator += weight
    if denominator <= 0:
        return None
    return round(numerator / denominator, 4)


def _combine_probability(
    *,
    code_match: dict[str, Any],
    window_similarity: dict[str, Any],
    fallback: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    code_ready = _eligible_probability_layer(code_match)
    window_ready = _eligible_probability_layer(window_similarity)
    if code_ready and window_ready:
        layers = [code_match, window_similarity]
        return {
            "up_rate": _weighted_rate(layers, "up_rate"),
            "down_rate": _weighted_rate(layers, "down_rate"),
            "gap_up_rate": _weighted_rate(layers, "gap_up_rate"),
            "strong_close_rate": _weighted_rate(layers, "strong_close_rate"),
            "method": "blended",
        }, _safe_int(code_match.get("sample_count")) + _safe_int(window_similarity.get("sample_count"))
    if code_ready:
        return {
            "up_rate": _safe_rate(code_match.get("up_rate")),
            "down_rate": _safe_rate(code_match.get("down_rate")),
            "gap_up_rate": _safe_rate(code_match.get("gap_up_rate")),
            "strong_close_rate": _safe_rate(code_match.get("strong_close_rate")),
            "method": "code_only",
        }, _safe_int(code_match.get("sample_count"))
    if window_ready:
        return {
            "up_rate": _safe_rate(window_similarity.get("up_rate")),
            "down_rate": _safe_rate(window_similarity.get("down_rate")),
            "gap_up_rate": _safe_rate(window_similarity.get("gap_up_rate")),
            "strong_close_rate": _safe_rate(window_similarity.get("strong_close_rate")),
            "method": "window_only",
        }, _safe_int(window_similarity.get("sample_count"))
    fallback_count = _safe_int(fallback.get("sample_count"))
    degraded_count = max(
        _safe_int(code_match.get("sample_count")),
        _safe_int(window_similarity.get("sample_count")),
    )
    sample_count = fallback_count if fallback_count > 0 else degraded_count
    return {
        "up_rate": _safe_rate(fallback.get("up_rate")),
        "down_rate": _safe_rate(fallback.get("down_rate")),
        "gap_up_rate": _safe_rate(fallback.get("gap_up_rate")),
        "strong_close_rate": _safe_rate(fallback.get("strong_close_rate")),
        "method": "fallback",
    }, sample_count


def _bias_from_combined(
    *,
    combined_probability: dict[str, Any],
    sample_quality: str,
    fallback_bias: str,
) -> str:
    up_rate = _safe_rate(combined_probability.get("up_rate"))
    down_rate = _safe_rate(combined_probability.get("down_rate"))
    if up_rate is not None and down_rate is not None:
        if sample_quality == "insufficient":
            return "insufficient"
        diff = round(up_rate - down_rate, 4)
        if abs(diff) < 0.1:
            return "mixed"
        return "supports_bullish" if diff > 0 else "supports_bearish"
    if combined_probability.get("method") == "fallback" and fallback_bias not in {"missing", "insufficient"}:
        return fallback_bias
    if sample_quality == "insufficient":
        return "insufficient"
    return "missing" if sample_quality == "missing" else fallback_bias


def _history_basis(
    *,
    code_match: dict[str, Any],
    window_similarity: dict[str, Any],
    combined_probability: dict[str, Any],
    source_summary: dict[str, Any],
    context: dict[str, Any],
) -> list[str]:
    basis = [
        f"code_match_sample_count={_safe_int(code_match.get('sample_count'))}",
        f"window_similarity_sample_count={_safe_int(window_similarity.get('sample_count'))}",
        f"combined_method={combined_probability.get('method') or 'fallback'}",
        f"exact_match_count={_safe_int(source_summary.get('exact_match_count'))}",
        f"near_match_count={_safe_int(source_summary.get('near_match_count'))}",
    ]
    if source_summary:
        basis.append(
            "dominant_historical_outcome="
            + str(
                source_summary.get("dominant_historical_outcome")
                or source_summary.get("historical_bias")
                or "n/a"
            )
        )
    if context:
        basis.append(f"context_features={sorted(context.keys())}")
    return basis


def _ready(primary_direction: str, historical_bias: str) -> bool:
    if primary_direction == "unknown":
        return False
    return historical_bias not in {"missing", "insufficient"}


def _summary_text(
    *,
    ready: bool,
    sample_count: int,
    sample_quality: str,
    historical_bias: str,
    impact: str,
    combined_probability: dict[str, Any],
    fallback_used: bool,
) -> str:
    method = str(combined_probability.get("method") or "fallback")
    up_rate = _safe_rate(combined_probability.get("up_rate"))
    down_rate = _safe_rate(combined_probability.get("down_rate"))
    if not ready:
        if sample_quality == "missing":
            return "当前未获得可用历史概率支持，历史概率层已降级。"
        if sample_quality == "insufficient" or historical_bias == "insufficient":
            return f"历史样本不足：当前仅 {sample_count} 个样本，不能形成可靠概率层。"
        return "历史概率不可用，暂时无法形成可靠倾向。"

    if historical_bias == "supports_bullish":
        bias_text = "历史概率支持偏多"
    elif historical_bias == "supports_bearish":
        bias_text = "历史概率支持偏空"
    else:
        bias_text = "历史概率偏中性或混杂"

    if impact == "support":
        impact_text = "支持当前主分析方向"
    elif impact == "caution":
        impact_text = "对当前主分析形成 caution"
    else:
        impact_text = "不直接改变当前主分析"

    fallback_text = "；当前走 historical_summary fallback" if fallback_used else ""
    return (
        f"历史概率层完成：样本 {sample_count}，质量 {sample_quality}，"
        f"{bias_text}，{impact_text}；"
        f"method={method}，up_rate={_format_percent(up_rate)}，"
        f"down_rate={_format_percent(down_rate)}{fallback_text}。"
    )


def _unknown_result(
    *,
    symbol: str,
    sample_count: int,
    sample_quality: str,
    historical_bias: str,
    impact: str,
    summary: str,
    warnings: list[str],
    source_summary: dict[str, Any],
) -> dict[str, Any]:
    empty_combined = {
        "up_rate": None,
        "down_rate": None,
        "gap_up_rate": None,
        "strong_close_rate": None,
        "method": "fallback",
    }
    return {
        "kind": "historical_probability",
        "symbol": symbol,
        "ready": False,
        "sample_count": sample_count,
        "sample_quality": sample_quality,
        "up_rate": None,
        "down_rate": None,
        "gap_up_rate": None,
        "strong_close_rate": None,
        "historical_bias": historical_bias,
        "impact": impact,
        "code_match": {
            "sample_count": 0,
            "up_rate": None,
            "down_rate": None,
            "gap_up_rate": None,
            "strong_close_rate": None,
            "summary": "同编码层不可用。",
        },
        "window_similarity": {
            "sample_count": 0,
            "up_rate": None,
            "down_rate": None,
            "gap_up_rate": None,
            "strong_close_rate": None,
            "avg_similarity": None,
            "summary": "相似窗口层不可用。",
        },
        "combined_probability": empty_combined,
        "summary": summary,
        "basis": ["历史概率层不可用。"],
        "warnings": warnings,
        "source_summary": source_summary,
    }


def build_historical_probability(
    *,
    primary_analysis: dict[str, Any],
    symbol: str = "AVGO",
    historical_summary: dict[str, Any] | None = None,
    context_features: dict[str, Any] | None = None,
    coded_history: pd.DataFrame | None = None,
    feature_history: pd.DataFrame | None = None,
    as_of_date: str | None = None,
) -> dict[str, Any]:
    """Build a fixed-shape historical probability report."""
    normalized_symbol = str(symbol or "AVGO").strip().upper() or "AVGO"
    source_summary = _as_dict(historical_summary)
    context = _as_dict(context_features)
    primary = _as_dict(primary_analysis)
    primary_direction = _primary_direction(primary)

    if not primary.get("ready") or primary_direction == "unknown":
        return _unknown_result(
            symbol=normalized_symbol,
            sample_count=_sample_count(source_summary),
            sample_quality=_sample_quality(_sample_count(source_summary), source_missing=not bool(source_summary)),
            historical_bias="missing",
            impact="missing",
            summary="主分析不可用，历史概率层无法判断是否支持当前方向。",
            warnings=["historical_probability 不可用：缺少可用 primary_analysis。"],
            source_summary=source_summary,
        )

    code_match, code_warnings = _build_code_match(
        primary=primary,
        source_summary=source_summary,
        context=context,
        coded_history=_as_frame(coded_history),
        as_of_date=as_of_date,
    )
    window_similarity, window_warnings = _build_window_similarity(
        feature_history=_as_frame(feature_history),
        context=context,
        as_of_date=as_of_date,
    )
    fallback = _fallback_probability(source_summary)
    combined_probability, sample_count = _combine_probability(
        code_match=code_match,
        window_similarity=window_similarity,
        fallback=fallback,
    )

    if sample_count <= 0 and source_summary:
        sample_count = _sample_count(source_summary)
    source_missing = (
        sample_count <= 0
        and not source_summary
        and _safe_int(code_match.get("sample_count")) <= 0
        and _safe_int(window_similarity.get("sample_count")) <= 0
    )
    sample_quality = _sample_quality(sample_count, source_missing=source_missing)
    fallback_bias = fallback.get("historical_bias") or "missing"
    historical_bias = _bias_from_combined(
        combined_probability=combined_probability,
        sample_quality=sample_quality,
        fallback_bias=str(fallback_bias),
    )
    impact = _impact(primary_direction, historical_bias)
    ready = _ready(primary_direction, historical_bias)

    warnings = list(dict.fromkeys([*code_warnings, *window_warnings]))
    if combined_probability.get("method") == "fallback":
        if source_summary:
            warnings.append("增强历史概率层缺少直接历史数据，当前使用 historical_summary fallback。")
        else:
            warnings.append("code_match 与 window_similarity 都不可用，combined_probability 无法形成真实概率。")

    rates_missing = all(combined_probability.get(field) is None for field in _RATE_FIELDS)
    if combined_probability.get("method") == "fallback" and rates_missing and source_summary:
        warnings.append("当前 fallback 只有历史倾向，没有可融合的精细概率字段。")
    if not ready and sample_quality != "missing":
        warnings.append(f"historical_probability 样本或信号不足：sample_count={sample_count}。")
    if not ready and sample_quality == "missing":
        warnings.append("historical_probability 缺少可用历史概率来源。")

    summary = _summary_text(
        ready=ready,
        sample_count=sample_count,
        sample_quality=sample_quality,
        historical_bias=historical_bias,
        impact=impact,
        combined_probability=combined_probability,
        fallback_used=combined_probability.get("method") == "fallback" and bool(source_summary),
    )

    return {
        "kind": "historical_probability",
        "symbol": normalized_symbol,
        "ready": ready,
        "sample_count": sample_count,
        "sample_quality": sample_quality,
        "up_rate": _safe_rate(combined_probability.get("up_rate")),
        "down_rate": _safe_rate(combined_probability.get("down_rate")),
        "gap_up_rate": _safe_rate(combined_probability.get("gap_up_rate")),
        "strong_close_rate": _safe_rate(combined_probability.get("strong_close_rate")),
        "historical_bias": historical_bias,
        "impact": impact,
        "code_match": code_match,
        "window_similarity": window_similarity,
        "combined_probability": combined_probability,
        "summary": summary,
        "basis": _history_basis(
            code_match=code_match,
            window_similarity=window_similarity,
            combined_probability=combined_probability,
            source_summary=source_summary,
            context=context,
        ),
        "warnings": list(dict.fromkeys(warnings)),
        "source_summary": source_summary,
    }
