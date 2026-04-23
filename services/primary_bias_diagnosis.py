"""Diagnose primary_20day_analysis directional bias from replay results."""

from __future__ import annotations

from collections import Counter
from typing import Any


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _clean_str(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"none", "null"} else text


def _unique(items: list[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        text = _clean_str(item)
        if text and text not in seen:
            seen.append(text)
    return seen


def _safe_rate(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 4)


def _direction_bucket(value: Any) -> str:
    text = _clean_str(value)
    return {
        "偏多": "bullish",
        "偏空": "bearish",
        "中性": "neutral",
    }.get(text, "unknown")


def _counter_rows(counter: Counter[str], *, key_name: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for label, count in counter.most_common():
        rows.append({key_name: label, "count": count})
    return rows


def _basis_patterns(basis: list[Any]) -> list[str]:
    patterns: list[str] = []
    for raw in basis:
        line = _clean_str(raw)
        if not line:
            continue
        if "最近5日收益" in line:
            if "+" in line:
                patterns.append("短期收益偏强")
            elif "-" in line:
                patterns.append("短期收益偏弱")
            else:
                patterns.append("短期收益信号")
            continue
        if "最近10日收益" in line:
            if "+" in line:
                patterns.append("中短期收益偏强")
            elif "-" in line:
                patterns.append("中短期收益偏弱")
            else:
                patterns.append("中短期收益信号")
            continue
        if "20日区间约" in line:
            if "约" in line and "%" in line:
                try:
                    percent = float(line.split("约", 1)[1].split("%", 1)[0])
                except (TypeError, ValueError):
                    percent = None
                if percent is not None:
                    if percent >= 67:
                        patterns.append("高位区间信号")
                    elif percent < 33:
                        patterns.append("低位区间信号")
                    else:
                        patterns.append("中位区间信号")
                    continue
            patterns.append("区间位置参考")
            continue
        if "状态为放量" in line:
            patterns.append("量能放量")
            continue
        if "状态为缩量" in line:
            patterns.append("量能缩量")
            continue
        if "状态为正常" in line:
            patterns.append("量能正常")
            continue
        if "简化阶段标签为" in line:
            patterns.append(line.replace("。", "").replace("简化阶段标签为", "阶段="))
            continue
        if "主分析方向信号归纳为" in line:
            patterns.append(line.replace("。", "").replace("主分析方向信号归纳为", "方向="))
            continue
        patterns.append(line[:30])
    return patterns


def _extract_case(item: dict[str, Any]) -> dict[str, Any]:
    projection_snapshot = _as_dict(item.get("projection_snapshot"))
    primary = _as_dict(projection_snapshot.get("primary_analysis"))
    if not primary and item.get("primary_analysis"):
        primary = _as_dict(item.get("primary_analysis"))
    review = _as_dict(item.get("review"))
    return {
        "primary": primary,
        "review": review,
        "ready": bool(item.get("ready")),
    }


def _source_items(
    *,
    replay_results: list[dict[str, Any]] | None,
    historical_snapshots: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    if isinstance(replay_results, list):
        return [item for item in replay_results if isinstance(item, dict)]
    if isinstance(historical_snapshots, list):
        return [item for item in historical_snapshots if isinstance(item, dict)]
    return []


def _empty_report(symbol: str) -> dict[str, Any]:
    return {
        "kind": "primary_bias_report",
        "symbol": symbol,
        "ready": False,
        "total_cases": 0,
        "judged_cases": 0,
        "primary_direction_distribution": {
            "bullish": 0,
            "bearish": 0,
            "neutral": 0,
            "unknown": 0,
        },
        "wrong_direction_cases": 0,
        "wrong_direction_rate": None,
        "primary_error_share": None,
        "top_position_labels": [],
        "top_stage_labels": [],
        "top_volume_states": [],
        "top_basis_patterns": [],
        "suspected_bias_sources": [],
        "diagnosis_summary": "当前缺少可用 replay 或 snapshot 输入，暂时无法诊断 primary 偏差来源。",
        "recommended_next_actions": [
            "先提供最近一段 replay_results，再比较 primary 的 bullish / bearish / neutral 分布。",
            "补齐 projection_snapshot.primary_analysis 与 review 字段后再定位偏差来源。",
        ],
        "warnings": ["缺少 replay_results 或 historical_snapshots，primary bias diagnosis 已降级。"],
    }


def _diagnosis_summary(
    *,
    total_cases: int,
    judged_cases: int,
    direction_distribution: dict[str, int],
    wrong_direction_cases: int,
    primary_error_share: float | None,
    suspected_bias_sources: list[dict[str, str]],
) -> str:
    bullish = direction_distribution["bullish"]
    bearish = direction_distribution["bearish"]
    neutral = direction_distribution["neutral"]
    unknown = direction_distribution["unknown"]

    if total_cases <= 0:
        return "当前缺少可用 replay 或 snapshot 输入，暂时无法诊断 primary 偏差来源。"

    parts = [
        f"共诊断 {total_cases} 个样本，其中可判定 primary 方向的有 {judged_cases} 个。",
        f"方向分布为 bullish={bullish} / bearish={bearish} / neutral={neutral} / unknown={unknown}。",
    ]
    if wrong_direction_cases:
        parts.append(f"wrong_direction 共 {wrong_direction_cases} 个样本。")
    else:
        parts.append("当前未观察到明确 wrong_direction 样本。")

    if primary_error_share is not None:
        parts.append(f"其中 primary_error_share 约为 {primary_error_share * 100:.1f}%。")
    if suspected_bias_sources:
        parts.append("最可疑的偏差来源集中在：" + "；".join(src["title"] for src in suspected_bias_sources[:3]) + "。")
    else:
        parts.append("当前证据有限，暂未形成强结论，只能先给出分布级诊断。")
    return " ".join(parts)


def _recommended_actions(
    *,
    direction_distribution: dict[str, int],
    wrong_direction_cases: int,
    primary_error_share: float | None,
    top_stage_labels: list[dict[str, Any]],
    top_basis_patterns: list[dict[str, Any]],
) -> list[str]:
    actions: list[str] = [
        "先用最近 60 个 replay 样本复核 primary 的方向打分门槛，而不是直接改 final 或规则层。",
    ]
    if direction_distribution["bullish"] > (direction_distribution["bearish"] + direction_distribution["neutral"]):
        actions.append("重点检查 primary 的 bullish 判定阈值，以及 neutral 触发是否过严。")
    if primary_error_share is not None and primary_error_share >= 0.5:
        actions.append("优先抽样复盘 primary error_layer=primary 的 wrong_direction 案例，确认偏差是否源自 Step 1 本身。")
    if top_stage_labels and _clean_str(top_stage_labels[0].get("label")) in {"延续", "启动"}:
        actions.append("专项检查高位回落样本是否仍被过早归成延续/启动，而不是分歧或衰竭。")
    if top_basis_patterns and "收益" in _clean_str(top_basis_patterns[0].get("pattern")):
        actions.append("拆解 ret_5d / ret_10d / pos_20d 对偏多判定的贡献，确认短期收益是否权重过高。")
    if wrong_direction_cases <= 0:
        actions.append("后续继续积累带 review verdict 的 replay 样本，再判断偏差是否稳定存在。")
    return _unique(actions)


def _suspected_bias_sources(
    *,
    judged_cases: int,
    direction_distribution: dict[str, int],
    wrong_direction_cases: int,
    primary_error_share: float | None,
    top_position_labels: list[dict[str, Any]],
    top_stage_labels: list[dict[str, Any]],
    top_basis_patterns: list[dict[str, Any]],
) -> list[dict[str, str]]:
    sources: list[dict[str, str]] = []
    bullish = direction_distribution["bullish"]
    bearish = direction_distribution["bearish"]
    neutral = direction_distribution["neutral"]
    bullish_rate = _safe_rate(bullish, judged_cases) or 0.0
    neutral_rate = _safe_rate(neutral, judged_cases) or 0.0
    bearish_rate = _safe_rate(bearish, judged_cases) or 0.0

    if judged_cases >= 5 and bullish_rate >= 0.75 and bearish_rate <= 0.1:
        sources.append({
            "title": "偏多门槛可能过松",
            "evidence": f"在 {judged_cases} 个可判定样本中，bullish 占 {bullish} 个，bearish 仅 {bearish} 个。",
            "severity": "high",
        })

    if judged_cases >= 5 and neutral_rate <= 0.15:
        sources.append({
            "title": "neutral 触发可能不足",
            "evidence": f"neutral 仅出现 {neutral} 次，说明当前 primary 更容易把样本推向单边判断。",
            "severity": "medium",
        })

    if wrong_direction_cases > 0 and primary_error_share is not None and primary_error_share >= 0.5:
        sources.append({
            "title": "wrong_direction 主要来自 primary 层",
            "evidence": f"wrong_direction 共 {wrong_direction_cases} 个样本，其中约 {primary_error_share * 100:.1f}% 被归因到 error_layer=primary。",
            "severity": "high" if primary_error_share >= 0.7 else "medium",
        })

    top_position = _clean_str(top_position_labels[0].get("label")) if top_position_labels else ""
    top_stage = _clean_str(top_stage_labels[0].get("label")) if top_stage_labels else ""
    if top_position == "高位" and top_stage in {"延续", "启动"}:
        sources.append({
            "title": "高位样本可能仍被过度解释成延续",
            "evidence": f"错误样本里最常见 position_label={top_position}，stage_label={top_stage}，高位回落场景可能没有充分转入中性/偏空。",
            "severity": "medium",
        })

    top_pattern = _clean_str(top_basis_patterns[0].get("pattern")) if top_basis_patterns else ""
    if "收益" in top_pattern:
        sources.append({
            "title": "收益类 basis 可能过度推动偏多结论",
            "evidence": f"错误样本里高频 basis 模式为“{top_pattern}”，说明短期收益信号可能对 primary 方向影响过强。",
            "severity": "medium",
        })

    return sources[:4]


def build_primary_bias_report(
    *,
    replay_results: list[dict[str, Any]] | None = None,
    symbol: str = "AVGO",
    lookback_days: int = 20,
    as_of_dates: list[str] | None = None,
    historical_snapshots: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a structured diagnostic report for primary bullish bias."""
    del lookback_days, as_of_dates

    normalized_symbol = _clean_str(symbol).upper() or "AVGO"
    report = _empty_report(normalized_symbol)
    items = _source_items(replay_results=replay_results, historical_snapshots=historical_snapshots)
    if not items:
        return report

    direction_distribution = {"bullish": 0, "bearish": 0, "neutral": 0, "unknown": 0}
    judged_cases = 0
    wrong_direction_cases = 0
    judged_review_cases = 0
    primary_error_cases = 0
    warnings: list[str] = []

    wrong_cases: list[dict[str, Any]] = []
    primary_error_cohort: list[dict[str, Any]] = []

    for item in items:
        case = _extract_case(item)
        primary = case["primary"]
        review = case["review"]

        bucket = _direction_bucket(primary.get("direction"))
        direction_distribution[bucket] += 1
        if bucket != "unknown":
            judged_cases += 1

        direction_correct = review.get("direction_correct")
        error_category = _clean_str(review.get("error_category"))
        if isinstance(direction_correct, bool):
            judged_review_cases += 1
        if error_category == "wrong_direction":
            wrong_direction_cases += 1
            wrong_cases.append(case)
        elif direction_correct is False:
            wrong_cases.append(case)

        if error_category == "wrong_direction" and _clean_str(review.get("error_layer")) == "primary":
            primary_error_cases += 1
            primary_error_cohort.append(case)

    error_cohort = primary_error_cohort or wrong_cases

    position_counter: Counter[str] = Counter()
    stage_counter: Counter[str] = Counter()
    volume_counter: Counter[str] = Counter()
    basis_counter: Counter[str] = Counter()

    for case in error_cohort:
        primary = case["primary"]
        position_counter[_clean_str(primary.get("position_label")) or "unknown"] += 1
        stage_counter[_clean_str(primary.get("stage_label")) or "unknown"] += 1
        volume_counter[_clean_str(primary.get("volume_state")) or "unknown"] += 1
        for pattern in _basis_patterns(_as_list(primary.get("basis"))):
            basis_counter[pattern] += 1

    if judged_cases == 0:
        warnings.append("primary_analysis 可用字段不足，方向分布以 unknown 为主。")
    if not error_cohort:
        warnings.append("当前缺少足够的错误样本，错误模式归纳证据有限。")
    if not primary_error_cohort and wrong_direction_cases > 0:
        warnings.append("wrong_direction 样本存在，但 error_layer=primary 证据较少，primary_error_share 解释力有限。")

    top_position_labels = _counter_rows(position_counter, key_name="label")[:5]
    top_stage_labels = _counter_rows(stage_counter, key_name="label")[:5]
    top_volume_states = _counter_rows(volume_counter, key_name="label")[:5]
    top_basis_patterns = _counter_rows(basis_counter, key_name="pattern")[:6]

    primary_error_share = _safe_rate(primary_error_cases, wrong_direction_cases)
    suspected_bias_sources = _suspected_bias_sources(
        judged_cases=judged_cases,
        direction_distribution=direction_distribution,
        wrong_direction_cases=wrong_direction_cases,
        primary_error_share=primary_error_share,
        top_position_labels=top_position_labels,
        top_stage_labels=top_stage_labels,
        top_basis_patterns=top_basis_patterns,
    )
    diagnosis_summary = _diagnosis_summary(
        total_cases=len(items),
        judged_cases=judged_cases,
        direction_distribution=direction_distribution,
        wrong_direction_cases=wrong_direction_cases,
        primary_error_share=primary_error_share,
        suspected_bias_sources=suspected_bias_sources,
    )
    recommended_next_actions = _recommended_actions(
        direction_distribution=direction_distribution,
        wrong_direction_cases=wrong_direction_cases,
        primary_error_share=primary_error_share,
        top_stage_labels=top_stage_labels,
        top_basis_patterns=top_basis_patterns,
    )

    return {
        "kind": "primary_bias_report",
        "symbol": normalized_symbol,
        "ready": True,
        "total_cases": len(items),
        "judged_cases": judged_cases,
        "primary_direction_distribution": direction_distribution,
        "wrong_direction_cases": wrong_direction_cases,
        "wrong_direction_rate": _safe_rate(wrong_direction_cases, judged_review_cases),
        "primary_error_share": primary_error_share,
        "top_position_labels": top_position_labels,
        "top_stage_labels": top_stage_labels,
        "top_volume_states": top_volume_states,
        "top_basis_patterns": top_basis_patterns,
        "suspected_bias_sources": suspected_bias_sources,
        "diagnosis_summary": diagnosis_summary,
        "recommended_next_actions": recommended_next_actions,
        "warnings": _unique(warnings),
    }


analyze_primary_bias = build_primary_bias_report
