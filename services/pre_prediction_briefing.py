# -*- coding: utf-8 -*-
"""
services/pre_prediction_briefing.py

Pre-prediction rule briefing derived from deterministic review history.
No LLM, no network — reads persisted review records via review_analyzer.

Public API
----------
build_pre_prediction_briefing(symbol, limit=30, max_rules=3, pred_open=None) -> dict

Output schema
-------------
{
    "symbol":                  str,
    "record_count":            int,
    "has_data":                bool,
    "overall_accuracy":        float,
    "caution_level":           str,        # "none" | "low" | "medium" | "high"
    "weakest_dimension":       str | None, # internal name: "open"/"path"/"close"
    "weakest_dimension_cn":    str | None, # Chinese label
    "weakest_accuracy":        float | None,
    "most_common_primary_error": str | None,
    "top_rules":               list[str],  # up to max_rules pre-trade reminders
    "all_rules":               list[str],  # full rule list from extract_review_rules
    "advisory_only":           True,       # constant — never alters prediction logic
}
"""

from __future__ import annotations

from typing import Any

from services.review_analyzer import (
    summarize_review_history,
    summarize_review_history_by_open_scenario,
    extract_review_rules,
)

_DIM_CN = {"open": "开盘", "path": "路径", "close": "收盘"}

# Caution thresholds (overall_accuracy)
_HIGH_CAUTION  = 0.34
_MED_CAUTION   = 0.67

# Accuracy level for a dimension to trigger a "weak" warning
_WEAK_DIM      = 0.50


def _caution_level(overall_accuracy: float, weakest_accuracy: float | None) -> str:
    """
    Map accuracy stats to a caution level string.

    "high"   → overall < 34% OR weakest dim < 34%
    "medium" → overall < 67% OR weakest dim < 50%
    "low"    → some data, but accuracy looks acceptable
    "none"   → no historical data at all
    """
    if overall_accuracy == 0.0 and weakest_accuracy is None:
        return "none"
    if overall_accuracy < _HIGH_CAUTION:
        return "high"
    if weakest_accuracy is not None and weakest_accuracy < _HIGH_CAUTION:
        return "high"
    if overall_accuracy < _MED_CAUTION:
        return "medium"
    if weakest_accuracy is not None and weakest_accuracy < _WEAK_DIM:
        return "medium"
    return "low"


def _build_top_rules(summary: dict[str, Any], max_rules: int) -> list[str]:
    """
    Build a focused list of pre-trade reminders from the summary.

    Priority order:
    1. Weak dimension warning (accuracy < 50%)
    2. Most common primary error
    3. Overall accuracy context
    4. Fill remaining slots with other notable stats
    """
    rules: list[str] = []

    record_count = summary.get("record_count", 0)
    overall      = summary.get("overall_accuracy", 0.0)
    weakest      = summary.get("weakest_dimension")
    weakest_acc  = summary.get("dimension_accuracy", {}).get(weakest) if weakest else None
    weakest_n    = summary.get("dimension_sample_count", {}).get(weakest, 0) if weakest else 0
    weakest_cn   = _DIM_CN.get(weakest, weakest) if weakest else None
    primary_err  = summary.get("most_common_primary_error")
    primary_n    = summary.get("primary_error_counts", {}).get(primary_err, 0) if primary_err else 0
    cat          = summary.get("most_common_error_category")
    cat_n        = summary.get("error_category_counts", {}).get(cat, 0) if cat else 0
    scenario_value = summary.get("scenario_value")
    scenario_prefix = f"{scenario_value}场景" if scenario_value else ""

    if max_rules <= 0:
        return []

    if record_count == 0:
        return ["暂无复盘历史，本次推演无历史规则可供参考。"]

    # Rule A — weakest dimension (most actionable)
    if weakest_cn and weakest_acc is not None and weakest_acc < _WEAK_DIM and len(rules) < max_rules:
        if scenario_prefix:
            rules.append(
                f"⚠ {scenario_prefix}下，{weakest_cn}判断历史准确率仅 {weakest_acc:.0%}"
                f"（{weakest_n} 条），本次推演请重点核查 {weakest_cn} 分析。"
            )
        else:
            rules.append(
                f"⚠ {weakest_cn}判断历史准确率仅 {weakest_acc:.0%}（{weakest_n} 条），"
                f"本次推演请重点核查 {weakest_cn} 分析。"
            )

    # Rule B — most common primary error
    if primary_err and len(rules) < max_rules:
        prefix = f"{scenario_prefix}最常见误判" if scenario_prefix else "历史最常见误判"
        rules.append(
            f"{prefix}：{primary_err}（出现 {primary_n} 次），"
            "推演时主动检查此维度是否存在偏差。"
        )

    # Rule C — overall accuracy context
    if len(rules) < max_rules:
        label = f"{scenario_prefix}历史命中率" if scenario_prefix else "历史整体命中率"
        rules.append(f"{label} {overall:.0%}（基于 {record_count} 条复盘）。")

    # Rule D — error category (fill remaining slot)
    if cat and cat != "correct" and len(rules) < max_rules:
        from services.review_analyzer import _CATEGORY_CN
        cat_cn = _CATEGORY_CN.get(cat, cat)
        prefix = f"{scenario_prefix}最常见误差类型" if scenario_prefix else "最常见误差类型"
        rules.append(f"{prefix}：{cat_cn}（{cat_n} 次），推演时留意是否过度自信或方向判断偏差。")

    return rules[:max_rules]


def build_pre_prediction_briefing(
    symbol: str,
    limit: int = 30,
    max_rules: int = 3,
    pred_open: str | None = None,
) -> dict[str, Any]:
    """
    Build a pre-prediction advisory briefing from historical review data.

    Reads up to `limit` review records for `symbol`, aggregates statistics, and
    produces up to `max_rules` focused pre-trade reminders ranked by actionability.

    This function is advisory only — it never modifies prediction inputs, scores,
    or confidence. `advisory_only` is always True in the returned dict.

    Parameters
    ----------
    symbol      Ticker symbol (e.g. "AVGO")
    limit       Maximum review records to read (default 30)
    max_rules   Maximum pre-trade rules to include in top_rules (default 3)
    pred_open   Optional current predicted open scenario (高开/低开/平开)
    """
    summary = summarize_review_history(symbol=symbol, limit=limit)
    scenario_summary = summarize_review_history_by_open_scenario(symbol=symbol, limit=limit)
    all_rules = extract_review_rules(summary)
    scenario_rules: list[str] = []

    selected_open_scenario = pred_open if pred_open in scenario_summary.get("scenarios", {}) else None
    selected_summary = (
        scenario_summary.get("scenarios", {}).get(selected_open_scenario)
        if selected_open_scenario else None
    )
    scenario_has_data = bool(selected_summary and selected_summary.get("record_count", 0) > 0)
    if scenario_has_data and selected_summary is not None:
        scenario_rules = extract_review_rules(selected_summary)

    active_summary = selected_summary if scenario_has_data and selected_summary is not None else summary
    rule_scope = "open_scenario" if scenario_has_data else "global"

    record_count = active_summary.get("record_count", 0)
    has_data     = record_count > 0
    overall      = active_summary.get("overall_accuracy", 0.0)
    weakest      = active_summary.get("weakest_dimension")
    weakest_acc  = active_summary.get("dimension_accuracy", {}).get(weakest) if weakest else None
    weakest_cn   = _DIM_CN.get(weakest, weakest) if weakest else None

    caution = _caution_level(overall, weakest_acc) if has_data else "none"
    top_rules = _build_top_rules(active_summary, max_rules)

    return {
        "symbol":                  symbol,
        "record_count":            record_count,
        "global_record_count":     summary.get("record_count", 0),
        "has_data":                has_data,
        "overall_accuracy":        overall,
        "caution_level":           caution,
        "weakest_dimension":       weakest,
        "weakest_dimension_cn":    weakest_cn,
        "weakest_accuracy":        weakest_acc,
        "most_common_primary_error": active_summary.get("most_common_primary_error"),
        "top_rules":               top_rules,
        "all_rules":               all_rules,
        "rule_scope":              rule_scope,
        "pred_open":               pred_open,
        "selected_open_scenario":  selected_open_scenario,
        "scenario_has_data":       scenario_has_data,
        "scenario_summary":        scenario_summary,
        "scenario_rules":          scenario_rules,
        "scenario_top_rules":      top_rules if rule_scope == "open_scenario" else [],
        "advisory_only":           True,
    }
