from __future__ import annotations

from typing import Any


def _empty_report() -> dict[str, Any]:
    return {
        "kind": "active_rule_pool_report",
        "ready": False,
        "total_rules": 0,
        "pool_counts": {
            "include": 0,
            "hold": 0,
            "exclude": 0,
        },
        "rules": [],
        "active_pool_candidates": [],
        "holdout_rules": [],
        "excluded_rules": [],
        "summary": "",
        "warnings": [],
    }


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _clean_text(value: Any, fallback: str = "unknown") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_lifecycle_state(rule: dict[str, Any]) -> str:
    state = _clean_text(rule.get("lifecycle_state"), fallback="candidate").lower()
    if state in {"candidate", "watchlist", "promoted_active", "weakened", "retired"}:
        return state
    return "candidate"


def _normalize_recommended_action(rule: dict[str, Any]) -> str:
    action = _clean_text(rule.get("recommended_action"), fallback="keep_observing").lower()
    if action in {"keep_observing", "promote", "weaken", "retire"}:
        return action
    return "keep_observing"


def _classify_pool_decision(rule: dict[str, Any]) -> tuple[str, str]:
    lifecycle_state = _normalize_lifecycle_state(rule)
    recommended_action = _normalize_recommended_action(rule)
    hit_count = _as_int(rule.get("hit_count"))
    net_score = _as_float(rule.get("net_score")) or 0.0
    effectiveness_rate = _as_float(rule.get("effectiveness_rate"))
    harm_rate = _as_float(rule.get("harm_rate"))

    if lifecycle_state == "promoted_active" and recommended_action == "promote":
        return (
            "include",
            (
                f"生命周期状态为 promoted_active，且建议动作为 promote；"
                f"当前 hit_count={hit_count}、net_score={net_score:.1f}，可纳入 active pool 候选。"
            ),
        )

    if lifecycle_state == "retired" or recommended_action == "retire":
        return (
            "exclude",
            (
                f"生命周期状态为 retired，或建议动作为 retire；"
                f"当前 harm_rate={(harm_rate if harm_rate is not None else 0.0):.2f}，应明确排除在 active pool 外。"
            ),
        )

    if lifecycle_state == "weakened" or recommended_action == "weaken":
        return (
            "exclude",
            (
                f"生命周期状态为 weakened，规则已显示边际走弱；"
                f"当前 net_score={net_score:.1f}、effectiveness_rate={(effectiveness_rate if effectiveness_rate is not None else 0.0):.2f}，先不进入 active pool。"
            ),
        )

    return (
        "hold",
        (
            f"生命周期状态为 {lifecycle_state}，建议动作为 {recommended_action}；"
            "当前证据还不足以正式纳入 active pool，建议继续观察。"
        ),
    )


def build_active_rule_pool_report(
    lifecycle_report: dict[str, Any] | None = None,
    rules: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    report = _empty_report()
    warnings: list[str] = []

    source_report = _as_dict(lifecycle_report)
    source_rules = _as_list(rules if rules is not None else source_report.get("rules"))

    if not source_report and rules is None:
        report["summary"] = "缺少 lifecycle 输入，暂时无法生成 active rule pool 推荐。"
        report["warnings"] = ["No lifecycle_report or rules were provided for active pool analysis."]
        return report

    if not source_rules:
        report["ready"] = True
        report["summary"] = "当前没有可评估的 lifecycle 规则记录，active pool 推荐结果为空。"
        warnings.append("No lifecycle rules were available for active pool classification.")
        report["warnings"] = warnings
        return report

    pool_rules: list[dict[str, Any]] = []
    malformed_rules = 0

    for raw_rule in source_rules:
        rule = _as_dict(raw_rule)
        if not rule:
            malformed_rules += 1
            continue

        lifecycle_state = _normalize_lifecycle_state(rule)
        recommended_action = _normalize_recommended_action(rule)
        pool_decision, pool_rationale = _classify_pool_decision(rule)

        pool_rule = {
            "rule_key": _clean_text(rule.get("rule_key")),
            "title": _clean_text(rule.get("title")),
            "category": _clean_text(rule.get("category")),
            "lifecycle_state": lifecycle_state,
            "recommended_action": recommended_action,
            "pool_decision": pool_decision,
            "pool_rationale": pool_rationale,
            "hit_count": _as_int(rule.get("hit_count")),
            "net_score": float(_as_float(rule.get("net_score")) or 0.0),
            "effectiveness_rate": _as_float(rule.get("effectiveness_rate")),
            "harm_rate": _as_float(rule.get("harm_rate")),
        }
        pool_rules.append(pool_rule)

        if pool_rule["rule_key"] == "unknown" or pool_rule["title"] == "unknown":
            warnings.append("One or more lifecycle rules had incomplete identifiers and were classified conservatively.")

    if malformed_rules:
        warnings.append(f"Skipped {malformed_rules} malformed lifecycle rule entries.")

    pool_rules.sort(
        key=lambda row: (
            row["pool_decision"] != "include",
            row["pool_decision"] != "hold",
            -row["hit_count"],
            -row["net_score"],
            row["rule_key"],
        )
    )

    pool_counts = _empty_report()["pool_counts"]
    for row in pool_rules:
        pool_counts[row["pool_decision"]] += 1

    active_pool_candidates = [row for row in pool_rules if row["pool_decision"] == "include"]
    holdout_rules = [row for row in pool_rules if row["pool_decision"] == "hold"]
    excluded_rules = [row for row in pool_rules if row["pool_decision"] == "exclude"]

    summary = (
        f"共评估 {len(pool_rules)} 条 lifecycle 规则：include={pool_counts['include']}，"
        f"hold={pool_counts['hold']}，exclude={pool_counts['exclude']}。"
    )
    if active_pool_candidates:
        summary += f" 当前最值得进入 active pool 候选的规则包括 {active_pool_candidates[0]['title']}。"
    elif excluded_rules:
        summary += f" 当前排除项中最显著的规则包括 {excluded_rules[0]['title']}。"
    else:
        summary += " 当前没有明确可纳入 active pool 的规则，建议继续观察。"

    report.update(
        {
            "ready": True,
            "total_rules": len(pool_rules),
            "pool_counts": pool_counts,
            "rules": pool_rules,
            "active_pool_candidates": active_pool_candidates,
            "holdout_rules": holdout_rules,
            "excluded_rules": excluded_rules,
            "summary": summary,
            "warnings": warnings,
        }
    )
    return report


analyze_active_rule_pool = build_active_rule_pool_report
