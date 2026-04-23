# -*- coding: utf-8 -*-
"""
services/review_analyzer.py

Deterministic rule extractor built on top of persisted review history.
No LLM, no network — pure aggregation and template logic.

Public API
----------
summarize_review_history(symbol: str, limit: int = 30) -> dict
summarize_review_history_by_open_scenario(symbol: str, limit: int = 30) -> dict
extract_review_rules(summary: dict) -> list[str]

summarize_review_history output schema
---------------------------------------
{
    "symbol":                str,
    "record_count":          int,
    "overall_accuracy":      float,          # mean overall_score (0.0–1.0)
    "dimension_accuracy": {
        "open":  float | None,               # fraction correct (None-flagged excluded)
        "path":  float | None,
        "close": float | None,
    },
    "dimension_sample_count": {
        "open":  int,                        # rows where open_correct is not None
        "path":  int,
        "close": int,
    },
    "weakest_dimension":         str | None, # "open" | "path" | "close" | None
    "strongest_dimension":       str | None,
    "error_category_counts":     dict[str, int],
    "primary_error_counts":      dict[str, int],
    "most_common_error_category": str | None,
    "most_common_primary_error":  str | None,
}
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from services.review_store import load_review_records

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

_DIMENSIONS = ("open", "path", "close")
_OPEN_SCENARIOS = ("高开", "低开", "平开")

_DIM_CN = {"open": "开盘", "path": "路径", "close": "收盘"}

_CATEGORY_CN: dict[str, str] = {
    "correct":                         "判断正确",
    "wrong_direction":                 "方向错误",
    "right_direction_wrong_magnitude": "方向正确但幅度偏差",
    "false_confidence":                "过度自信",
    "insufficient_data":               "信息不足",
}

# Thresholds for rule generation
_WEAK_THRESHOLD = 0.50       # below this → warn
_STRONG_THRESHOLD = 0.70     # above this → note as advantage
_MIN_SAMPLE_FOR_RULE = 3     # minimum records for a dimension rule to fire


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _dim_correct_key(dim: str) -> str:
    return f"{dim}_correct"


def _most_common(counter: Counter) -> str | None:
    if not counter:
        return None
    return counter.most_common(1)[0][0]


def _pct(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.0%}"


def _empty_summary(symbol: str) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "record_count": 0,
        "overall_accuracy": 0.0,
        "dimension_accuracy": {"open": None, "path": None, "close": None},
        "dimension_sample_count": {"open": 0, "path": 0, "close": 0},
        "weakest_dimension": None,
        "strongest_dimension": None,
        "error_category_counts": {},
        "primary_error_counts": {},
        "most_common_error_category": None,
        "most_common_primary_error": None,
    }


def _summarize_records(symbol: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    record_count = len(records)

    if record_count == 0:
        return _empty_summary(symbol)

    # Overall accuracy
    scores = [r.get("overall_score") or 0.0 for r in records]
    overall_accuracy = sum(scores) / record_count

    # Per-dimension accuracy
    dim_correct: dict[str, int] = {d: 0 for d in _DIMENSIONS}
    dim_sample:  dict[str, int] = {d: 0 for d in _DIMENSIONS}

    for r in records:
        for dim in _DIMENSIONS:
            flag = r.get(_dim_correct_key(dim))
            if flag is not None:
                dim_sample[dim] += 1
                if flag is True:
                    dim_correct[dim] += 1

    dimension_accuracy: dict[str, float | None] = {}
    for dim in _DIMENSIONS:
        n = dim_sample[dim]
        dimension_accuracy[dim] = dim_correct[dim] / n if n > 0 else None

    # Weakest / strongest (only among dims with enough samples)
    eligible = {
        d: acc
        for d, acc in dimension_accuracy.items()
        if acc is not None and dim_sample[d] >= _MIN_SAMPLE_FOR_RULE
    }
    weakest_dimension:   str | None = min(eligible, key=eligible.__getitem__) if eligible else None
    strongest_dimension: str | None = max(eligible, key=eligible.__getitem__) if eligible else None
    # If weakest == strongest, only suppress if all same accuracy
    if (
        weakest_dimension is not None
        and strongest_dimension is not None
        and weakest_dimension == strongest_dimension
    ):
        # All eligible dims have the same accuracy — set both anyway (single dim case)
        pass

    # Error category counts
    cat_counter: Counter = Counter()
    pe_counter:  Counter = Counter()
    for r in records:
        cat = r.get("error_category") or ""
        if cat:
            cat_counter[cat] += 1
        pe = r.get("primary_error") or ""
        if pe:
            pe_counter[pe] += 1

    return {
        "symbol":                symbol,
        "record_count":          record_count,
        "overall_accuracy":      overall_accuracy,
        "dimension_accuracy":    dimension_accuracy,
        "dimension_sample_count": dim_sample,
        "weakest_dimension":         weakest_dimension,
        "strongest_dimension":       strongest_dimension,
        "error_category_counts":     dict(cat_counter),
        "primary_error_counts":      dict(pe_counter),
        "most_common_error_category": _most_common(cat_counter),
        "most_common_primary_error":  _most_common(pe_counter),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def summarize_review_history(
    symbol: str,
    limit: int = 30,
) -> dict[str, Any]:
    """
    Aggregate review history for a symbol into a statistics dict.

    Loads up to `limit` records from review_store and computes:
    - overall_accuracy: mean overall_score across all records
    - per-dimension accuracy (open/path/close), excluding None-flagged rows
    - weakest/strongest dimension by accuracy
    - error category and primary error frequency counts

    Returns a summary dict — see module docstring for full schema.
    """
    records = load_review_records(symbol=symbol, limit=limit)
    return _summarize_records(symbol, records)


def summarize_review_history_by_open_scenario(
    symbol: str,
    limit: int = 30,
) -> dict[str, Any]:
    """
    Aggregate review history by predicted open scenario.

    The first scenario slice is intentionally narrow: records are grouped only
    by persisted `pred_open`, with stable buckets for 高开 / 低开 / 平开.
    Records with missing or unknown `pred_open` are counted separately so old
    rows remain compatible without being forced into a fake scenario.
    """
    records = load_review_records(symbol=symbol, limit=limit)
    grouped_records: dict[str, list[dict[str, Any]]] = {
        scenario: [] for scenario in _OPEN_SCENARIOS
    }
    unknown_count = 0

    for record in records:
        pred_open = record.get("pred_open")
        if pred_open in grouped_records:
            grouped_records[pred_open].append(record)
        else:
            unknown_count += 1

    scenario_summaries: dict[str, dict[str, Any]] = {}
    scenario_record_count: dict[str, int] = {}
    for scenario in _OPEN_SCENARIOS:
        summary = _summarize_records(symbol, grouped_records[scenario])
        summary["scenario_type"] = "pred_open"
        summary["scenario_value"] = scenario
        scenario_summaries[scenario] = summary
        scenario_record_count[scenario] = summary["record_count"]

    return {
        "symbol": symbol,
        "record_count": len(records),
        "scenario_type": "pred_open",
        "scenario_values": list(_OPEN_SCENARIOS),
        "scenario_record_count": scenario_record_count,
        "available_scenarios": [
            scenario
            for scenario in _OPEN_SCENARIOS
            if scenario_record_count[scenario] > 0
        ],
        "unknown_count": unknown_count,
        "scenarios": scenario_summaries,
    }


def extract_review_rules(summary: dict[str, Any]) -> list[str]:
    """
    Generate a list of Chinese rule strings from a summarize_review_history() result.

    Rules are deterministic templates — no LLM. Each rule is a single actionable
    string suitable for display as a pre-trade reminder.

    Returns an empty list when there is no historical data.
    """
    record_count: int = summary.get("record_count", 0)
    rules: list[str] = []
    scenario_value = summary.get("scenario_value")
    scenario_prefix = f"{scenario_value}场景" if scenario_value else ""

    if record_count == 0:
        return ["暂无复盘历史记录，无法提炼规则。"]

    overall = summary.get("overall_accuracy", 0.0)
    dim_acc: dict = summary.get("dimension_accuracy", {})
    dim_n:   dict = summary.get("dimension_sample_count", {})
    weakest:   str | None = summary.get("weakest_dimension")
    strongest: str | None = summary.get("strongest_dimension")
    most_cat = summary.get("most_common_error_category")
    most_pe  = summary.get("most_common_primary_error")

    # Rule 1 — overall hit rate
    overall_label = f"{scenario_prefix}整体命中率" if scenario_prefix else "整体命中率"
    rules.append(
        f"{overall_label} {_pct(overall)}（基于最近 {record_count} 条复盘记录）"
    )

    # Rule 2 — data sufficiency warning
    if record_count < _MIN_SAMPLE_FOR_RULE:
        rules.append(
            f"样本量较少（{record_count} 条），以下规则仅供参考，"
            "建议积累更多复盘后再使用。"
        )

    # Rule 3 — weakest dimension warning
    if weakest is not None:
        acc = dim_acc.get(weakest)
        n   = dim_n.get(weakest, 0)
        cn  = _DIM_CN.get(weakest, weakest)
        if acc is not None and acc < _WEAK_THRESHOLD:
            rules.append(
                f"⚠ {scenario_prefix}最弱维度：{cn}（准确率 {_pct(acc)}，共 {n} 条），"
                f"下次推演前重点核查 {cn} 结构。"
            )
        else:
            rules.append(
                f"{scenario_prefix}最弱维度：{cn}（准确率 {_pct(acc)}，共 {n} 条）。"
            )

    # Rule 4 — strongest dimension note (only if different from weakest)
    if strongest is not None and strongest != weakest:
        acc = dim_acc.get(strongest)
        n   = dim_n.get(strongest, 0)
        cn  = _DIM_CN.get(strongest, strongest)
        if acc is not None and acc >= _STRONG_THRESHOLD:
            rules.append(
                f"{scenario_prefix}优势维度：{cn}（准确率 {_pct(acc)}，共 {n} 条），可作为推演锚点保留。"
            )

    # Rule 5 — most common error category
    if most_cat:
        cat_cn = _CATEGORY_CN.get(most_cat, most_cat)
        cat_count = summary.get("error_category_counts", {}).get(most_cat, 0)
        rules.append(
            f"{scenario_prefix}最常见误差类型：{cat_cn}（{most_cat}，出现 {cat_count} 次），"
            "建议在推演时主动检查是否存在此类偏差。"
        )

    # Rule 6 — most common primary error (Chinese label, e.g. "路径判断错误")
    if most_pe:
        pe_count = summary.get("primary_error_counts", {}).get(most_pe, 0)
        rules.append(
            f"{scenario_prefix}主要误判维度：{most_pe}（出现 {pe_count} 次），是当前系统最需要改进的判断点。"
        )

    # Rule 7 — per-dimension accuracy for dims with enough data
    for dim in _DIMENSIONS:
        acc = dim_acc.get(dim)
        n   = dim_n.get(dim, 0)
        cn  = _DIM_CN.get(dim, dim)
        if acc is None or n < _MIN_SAMPLE_FOR_RULE:
            continue
        if dim == weakest or dim == strongest:
            continue  # already covered above
        rules.append(f"{scenario_prefix}{cn}准确率 {_pct(acc)}（共 {n} 条）。")

    return rules
