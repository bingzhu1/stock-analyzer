from __future__ import annotations

from typing import Any


def _empty_report() -> dict[str, Any]:
    return {
        "kind": "rule_lifecycle_report",
        "ready": False,
        "total_rules": 0,
        "state_counts": {
            "candidate": 0,
            "watchlist": 0,
            "promoted_active": 0,
            "weakened": 0,
            "retired": 0,
        },
        "rules": [],
        "promoted_active_rules": [],
        "retired_rules": [],
        "weakened_rules": [],
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


def _normalize_score_status(rule: dict[str, Any]) -> str:
    status = _clean_text(
        rule.get("current_score_status") or rule.get("recommended_status"),
        fallback="candidate",
    ).lower()
    if status in {"candidate", "watchlist", "promising", "risky"}:
        return status
    return "candidate"


def _classify_lifecycle(rule: dict[str, Any]) -> tuple[str, str, str]:
    hit_count = _as_int(rule.get("hit_count"))
    effective_count = _as_int(rule.get("effective_count"))
    harmful_count = _as_int(rule.get("harmful_count"))
    neutral_count = _as_int(rule.get("neutral_count"))
    effectiveness_rate = _as_float(rule.get("effectiveness_rate"))
    harm_rate = _as_float(rule.get("harm_rate"))
    net_score = _as_float(rule.get("net_score")) or 0.0
    current_score_status = _normalize_score_status(rule)

    if hit_count < 3:
        return (
            "candidate",
            "keep_observing",
            f"命中样本仅 {hit_count} 次，证据仍偏少，当前更适合作为候选继续观察。",
        )

    if hit_count >= 5 and current_score_status == "risky" and harmful_count >= effective_count and (harm_rate or 0.0) >= 0.5:
        return (
            "retired",
            "retire",
            (
                f"命中 {hit_count} 次且 harmful_count={harmful_count} 不低于 effective_count={effective_count}，"
                f"harm_rate={(harm_rate if harm_rate is not None else 0.0):.2f}，更像长期噪音或拖累，建议淘汰。"
            ),
        )

    if (
        hit_count >= 5
        and current_score_status == "promising"
        and effective_count > harmful_count
        and (effectiveness_rate or 0.0) >= max((harm_rate or 0.0) + 0.2, 0.6)
        and net_score >= 2
    ):
        return (
            "promoted_active",
            "promote",
            (
                f"命中 {hit_count} 次且 effective_count={effective_count} 明显高于 harmful_count={harmful_count}，"
                f"effectiveness_rate={(effectiveness_rate if effectiveness_rate is not None else 0.0):.2f}，"
                "已具备进入 active 候选池的基础，建议晋升。"
            ),
        )

    if (
        hit_count >= 4
        and current_score_status in {"watchlist", "promising"}
        and harmful_count > 0
        and abs(net_score) <= 1
    ):
        return (
            "weakened",
            "weaken",
            (
                f"命中 {hit_count} 次，但正负样本接近（effective={effective_count}, harmful={harmful_count}, neutral={neutral_count}），"
                "说明规则强度不足或边际走弱，建议降级观察。"
            ),
        )

    return (
        "watchlist",
        "keep_observing",
        (
            f"命中 {hit_count} 次，但当前 score status 为 {current_score_status}，"
            f"effective={effective_count}、harmful={harmful_count} 仍未形成足够清晰的晋升或淘汰证据，建议继续观察。"
        ),
    )


def build_rule_lifecycle_report(
    rule_score_report: dict[str, Any] | None = None,
    rules: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    report = _empty_report()
    warnings: list[str] = []

    source_report = _as_dict(rule_score_report)
    source_rules = _as_list(rules if rules is not None else source_report.get("rules"))

    if not source_report and rules is None:
        report["summary"] = "缺少 rule score 输入，暂时无法生成生命周期建议。"
        report["warnings"] = ["No rule_score_report or rules were provided for lifecycle analysis."]
        return report

    if not source_rules:
        report["ready"] = True
        report["summary"] = "当前没有可管理的规则评分记录，生命周期状态暂时全部为空。"
        warnings.append("No scored rules were available for lifecycle classification.")
        report["warnings"] = warnings
        return report

    lifecycle_rules: list[dict[str, Any]] = []
    malformed_rules = 0

    for raw_rule in source_rules:
        rule = _as_dict(raw_rule)
        if not rule:
            malformed_rules += 1
            continue

        lifecycle_state, recommended_action, rationale = _classify_lifecycle(rule)
        current_score_status = _normalize_score_status(rule)
        lifecycle_rule = {
            "rule_key": _clean_text(rule.get("rule_key")),
            "title": _clean_text(rule.get("title")),
            "category": _clean_text(rule.get("category")),
            "hit_count": _as_int(rule.get("hit_count")),
            "effective_count": _as_int(rule.get("effective_count")),
            "harmful_count": _as_int(rule.get("harmful_count")),
            "neutral_count": _as_int(rule.get("neutral_count")),
            "effectiveness_rate": _as_float(rule.get("effectiveness_rate")),
            "harm_rate": _as_float(rule.get("harm_rate")),
            "net_score": float(_as_float(rule.get("net_score")) or 0.0),
            "current_score_status": current_score_status,
            "lifecycle_state": lifecycle_state,
            "rationale": rationale,
            "recommended_action": recommended_action,
        }
        lifecycle_rules.append(lifecycle_rule)

        if lifecycle_rule["title"] == "unknown" or lifecycle_rule["rule_key"] == "unknown":
            warnings.append("One or more rules had incomplete identifiers and were classified conservatively.")

    if malformed_rules:
        warnings.append(f"Skipped {malformed_rules} malformed scored rule entries.")

    lifecycle_rules.sort(
        key=lambda row: (
            row["lifecycle_state"] != "promoted_active",
            row["lifecycle_state"] != "retired",
            -row["hit_count"],
            -row["net_score"],
            row["rule_key"],
        )
    )

    state_counts = _empty_report()["state_counts"]
    for row in lifecycle_rules:
        state_counts[row["lifecycle_state"]] += 1

    promoted_active_rules = [row for row in lifecycle_rules if row["lifecycle_state"] == "promoted_active"]
    retired_rules = [row for row in lifecycle_rules if row["lifecycle_state"] == "retired"]
    weakened_rules = [row for row in lifecycle_rules if row["lifecycle_state"] == "weakened"]

    summary = (
        f"共评估 {len(lifecycle_rules)} 条规则：candidate={state_counts['candidate']}，"
        f"watchlist={state_counts['watchlist']}，promoted_active={state_counts['promoted_active']}，"
        f"weakened={state_counts['weakened']}，retired={state_counts['retired']}。"
    )
    if promoted_active_rules:
        summary += f" 当前最值得推进的规则包括 {promoted_active_rules[0]['title']}。"
    elif retired_rules:
        summary += f" 当前最需要淘汰关注的规则包括 {retired_rules[0]['title']}。"
    else:
        summary += " 当前没有足够强的晋升或淘汰信号，适合继续观察。"

    report.update(
        {
            "ready": True,
            "total_rules": len(lifecycle_rules),
            "state_counts": state_counts,
            "rules": lifecycle_rules,
            "promoted_active_rules": promoted_active_rules,
            "retired_rules": retired_rules,
            "weakened_rules": weakened_rules,
            "summary": summary,
            "warnings": warnings,
        }
    )
    return report


analyze_rule_lifecycle = build_rule_lifecycle_report
