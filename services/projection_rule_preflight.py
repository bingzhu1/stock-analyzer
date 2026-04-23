"""Independent projection v2 rule preflight layer.

This module packages existing memory / review reminders into a stable Step 0
report. It does not learn new rules or change projection decisions.
"""

from __future__ import annotations

from typing import Any, Callable

from services.error_taxonomy import normalize_error_category
from services.projection_memory_briefing import build_projection_memory_briefing
from services.review_store import load_review_records


_HIGH_SEVERITY = {"wrong_direction", "false_confidence"}
_MEDIUM_SEVERITY = {"right_direction_wrong_magnitude", "insufficient_data"}
_PROJECTION_CATEGORIES = {
    "wrong_direction",
    "right_direction_wrong_magnitude",
    "false_confidence",
    "insufficient_data",
}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _clean_symbol(symbol: str | None) -> str:
    return str(symbol or "AVGO").strip().upper() or "AVGO"


def _severity(category: str, fallback: Any = None) -> str:
    text = str(fallback or "").strip().lower()
    if text in {"low", "medium", "high"}:
        return text
    if category in _HIGH_SEVERITY:
        return "high"
    if category in _MEDIUM_SEVERITY:
        return "medium"
    return "low"


def _adjustment_for(category: str, severity: str) -> str:
    if category == "wrong_direction":
        return "复核主方向，避免重复历史方向性错误。"
    if category == "false_confidence":
        return "控制最终置信度，避免在证据不足时过度自信。"
    if category == "right_direction_wrong_magnitude":
        return "区分方向判断和幅度判断，避免把方向正确误读为高置信度。"
    if category == "insufficient_data":
        return "确认 peers / historical / primary 数据是否足够，再给出结论。"
    if severity == "high":
        return "命中高风险历史提醒，最终结论需要显式说明约束。"
    return "保留历史提醒，不直接修改方向。"


def _rule(
    *,
    rule_id: str,
    title: str,
    category: str,
    severity: str,
    message: str,
    source: str | None = None,
) -> dict[str, Any]:
    rule: dict[str, Any] = {
        "rule_id": rule_id,
        "title": title,
        "category": category,
        "severity": severity,
        "message": message,
    }
    if source:
        rule["sources"] = [source]
    return rule


def _rules_from_active_pool_bridge(
    bridge_rules: list[Any],
    *,
    warnings: list[str],
) -> tuple[list[dict[str, Any]], int]:
    rules: list[dict[str, Any]] = []
    total_items = len(bridge_rules)

    for index, item in enumerate(bridge_rules):
        if not isinstance(item, dict):
            warnings.append("projection_rule_preflight 跳过格式异常的 active pool bridge rule。")
            continue

        title = str(item.get("title") or "").strip()
        message = str(item.get("message") or "").strip()
        if not title or not message:
            warnings.append("projection_rule_preflight 跳过缺少 title/message 的 active pool bridge rule。")
            continue

        category = normalize_error_category(item.get("category"))
        rules.append(_rule(
            rule_id=str(item.get("rule_id") or f"active-pool-{index + 1}"),
            title=title,
            category=category,
            severity=_severity(category, item.get("severity")),
            message=message,
            source="active_pool",
        ))

    return rules, total_items


def _rules_from_memory_briefing(
    briefing: dict[str, Any],
    *,
    warnings: list[str],
) -> tuple[list[dict[str, Any]], int]:
    if not briefing:
        return [], 0
    reminder_lines = _as_list(briefing.get("reminder_lines"))
    top_categories = _as_list(briefing.get("top_categories"))
    category_by_index = [
        normalize_error_category(_as_dict(item).get("error_category"))
        for item in top_categories
        if isinstance(item, dict)
    ]
    rules: list[dict[str, Any]] = []
    for index, line in enumerate(reminder_lines):
        if not isinstance(line, str) or not line.strip():
            warnings.append("projection_rule_preflight 跳过格式异常的 memory reminder。")
            continue
        category = category_by_index[index] if index < len(category_by_index) else "insufficient_data"
        severity = _severity(category, briefing.get("caution_level"))
        rules.append(_rule(
            rule_id=f"memory-{index + 1}",
            title=f"历史记忆提醒：{category}",
            category=category,
            severity=severity,
            message=line.strip(),
            source="memory",
        ))
    return rules, len(reminder_lines)


def _rules_from_memory_items(
    memory_items: list[Any],
    *,
    warnings: list[str],
) -> tuple[list[dict[str, Any]], int]:
    rules: list[dict[str, Any]] = []
    for index, item in enumerate(memory_items):
        if not isinstance(item, dict):
            warnings.append("projection_rule_preflight 跳过格式异常的 memory item。")
            continue
        category = normalize_error_category(item.get("error_category"))
        message = str(item.get("lesson") or item.get("root_cause") or "").strip()
        if not message:
            warnings.append("projection_rule_preflight 跳过缺少 lesson/root_cause 的 memory item。")
            continue
        rules.append(_rule(
            rule_id=str(item.get("id") or f"memory-{index + 1}"),
            title=f"历史记忆提醒：{category}",
            category=category,
            severity=_severity(category, item.get("severity")),
            message=message,
            source="memory",
        ))
    return rules, len(memory_items)


def _rules_from_review_items(
    review_items: list[Any],
    *,
    warnings: list[str],
) -> tuple[list[dict[str, Any]], int]:
    rules: list[dict[str, Any]] = []
    for index, item in enumerate(review_items):
        if not isinstance(item, dict):
            warnings.append("projection_rule_preflight 跳过格式异常的 review item。")
            continue
        category = normalize_error_category(
            item.get("error_category")
            or _as_dict(item.get("error_info_json")).get("error_category")
            or _as_dict(item.get("error_info")).get("error_category")
        )
        if category not in _PROJECTION_CATEGORIES or category == "correct":
            continue
        message = str(
            item.get("review_summary")
            or item.get("primary_error")
            or _as_dict(item.get("error_info_json")).get("primary_error")
            or "复核最近一次 review 中的历史错误。"
        ).strip()
        rules.append(_rule(
            rule_id=str(item.get("id") or f"review-{index + 1}"),
            title=f"历史复盘提醒：{category}",
            category=category,
            severity=_severity(category, item.get("severity")),
            message=message,
            source="review",
        ))
    return rules, len(review_items)


def _dedupe_rules(rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[tuple[str, str], dict[str, Any]] = {}
    deduped: list[dict[str, Any]] = []
    for rule in rules:
        key = (rule["category"], rule["message"])
        if key in seen:
            existing = seen[key]
            existing_sources = list(existing.get("sources") or [])
            new_sources = list(rule.get("sources") or [])
            for source in new_sources:
                if source not in existing_sources:
                    existing_sources.append(source)
            if existing_sources:
                existing["sources"] = existing_sources
            continue
        seen[key] = rule
        deduped.append(rule)
    return deduped


def build_projection_rule_preflight(
    *,
    symbol: str = "AVGO",
    target_date: str | None = None,
    lookback_days: int = 20,
    projection_context: dict[str, Any] | None = None,
    active_rule_pool_export: dict[str, Any] | None = None,
    active_bridge_rules: list[dict[str, Any]] | None = None,
    use_active_rule_pool: bool = False,
    _memory_briefing_builder: Callable[..., dict[str, Any]] = build_projection_memory_briefing,
    _review_loader: Callable[..., list[dict[str, Any]]] = load_review_records,
) -> dict[str, Any]:
    """Build a stable rule preflight report for projection v2."""
    clean_symbol = _clean_symbol(symbol)
    context = _as_dict(projection_context)
    warnings: list[str] = []
    source_errors: list[str] = []
    rules: list[dict[str, Any]] = []
    memory_count = 0
    review_count = 0
    active_pool_items = 0
    active_pool_matches = 0
    active_pool_used = False

    if "memory_items" in context:
        memory_rules, memory_count = _rules_from_memory_items(
            _as_list(context.get("memory_items")),
            warnings=warnings,
        )
        rules.extend(memory_rules)
    else:
        try:
            briefing = _as_dict(context.get("memory_briefing")) or _memory_briefing_builder(
                symbol=clean_symbol,
                limit=5,
            )
            memory_rules, memory_count = _rules_from_memory_briefing(briefing, warnings=warnings)
            rules.extend(memory_rules)
        except Exception as exc:
            source_errors.append(f"memory source unavailable: {exc}")

    if "review_items" in context:
        review_rules, review_count = _rules_from_review_items(
            _as_list(context.get("review_items")),
            warnings=warnings,
        )
        rules.extend(review_rules)
    else:
        try:
            review_items = _review_loader(symbol=clean_symbol, limit=5)
            review_rules, review_count = _rules_from_review_items(review_items, warnings=warnings)
            rules.extend(review_rules)
        except Exception as exc:
            source_errors.append(f"review source unavailable: {exc}")

    if use_active_rule_pool:
        bridge_source = (
            _as_list(active_bridge_rules)
            if active_bridge_rules is not None
            else _as_list(_as_dict(active_rule_pool_export).get("preflight_bridge_rules"))
        )
        active_pool_used = True
        if bridge_source:
            active_rules, active_pool_items = _rules_from_active_pool_bridge(
                bridge_source,
                warnings=warnings,
            )
            rules.extend(active_rules)
        else:
            active_pool_items = 0

    rules = _dedupe_rules(rules)
    active_pool_matches = sum(
        1 for rule in rules if "active_pool" in list(rule.get("sources") or [])
    )
    rule_warnings = [rule["message"] for rule in rules]
    rule_adjustments = [
        _adjustment_for(rule["category"], rule["severity"])
        for rule in rules
    ]
    source_counts = {
        "memory_items": memory_count,
        "review_items": review_count,
        "matched_rule_count": len(rules),
        "active_pool_items": active_pool_items,
        "active_pool_matches": active_pool_matches,
    }

    if source_errors and memory_count == 0 and review_count == 0:
        warnings.extend(source_errors)
        summary = "当前未接入历史规则或未读取到可用规则，projection_rule_preflight 已降级。"
        ready = False
    elif rules:
        if active_pool_used and active_pool_matches > 0:
            summary = f"命中 {len(rules)} 条历史规则提醒，其中 {active_pool_matches} 条规则也来自 active rule pool。"
        else:
            summary = f"命中 {len(rules)} 条历史规则提醒。"
        ready = True
        warnings.extend(source_errors)
    else:
        summary = "未命中历史规则。"
        ready = True
        warnings.extend(source_errors)

    return {
        "kind": "projection_rule_preflight",
        "symbol": clean_symbol,
        "target_date": target_date,
        "lookback_days": lookback_days,
        "ready": ready,
        "matched_rules": rules,
        "rule_warnings": rule_warnings,
        "rule_adjustments": rule_adjustments,
        "summary": summary,
        "warnings": warnings,
        "source_counts": source_counts,
        "active_pool_used": active_pool_used,
    }
