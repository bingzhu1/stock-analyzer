"""Build calibration suggestions for active rule pool rules."""

from __future__ import annotations

from typing import Any


def _empty_report() -> dict[str, Any]:
    return {
        "kind": "active_rule_pool_calibration_report",
        "ready": False,
        "total_active_rules": 0,
        "decision_counts": {
            "retain": 0,
            "downgrade": 0,
            "recalibrate": 0,
            "remove_candidate": 0,
            "observe": 0,
        },
        "rules": [],
        "retain_rules": [],
        "downgrade_rules": [],
        "recalibrate_rules": [],
        "remove_candidates": [],
        "observe_rules": [],
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


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _normalize_severity(value: Any) -> str:
    text = _clean_text(value, fallback="unknown").lower()
    if text in {"low", "medium", "high", "unknown"}:
        return text
    return "unknown"


def _normalize_effect(value: Any) -> str:
    text = _clean_text(value, fallback="unknown").lower()
    if text in {"warn", "lower_confidence", "raise_risk", "unknown"}:
        return text
    return "unknown"


def _score_lookup(rule_score_report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for raw_rule in _as_list(rule_score_report.get("rules")):
        rule = _as_dict(raw_rule)
        title = _clean_text(rule.get("title"), fallback="")
        if title:
            lookup[title] = rule
    return lookup


def _lifecycle_lookup(rule_lifecycle_report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for raw_rule in _as_list(rule_lifecycle_report.get("rules")):
        rule = _as_dict(raw_rule)
        title = _clean_text(rule.get("title"), fallback="")
        if title:
            lookup[title] = rule
    return lookup


def _conservative_pressure(
    *,
    changed_case_count: int,
    improved_case_count: int,
    worsened_case_count: int,
) -> bool:
    decisive = improved_case_count + worsened_case_count
    neutral_changes = changed_case_count - decisive
    return changed_case_count >= 4 and neutral_changes >= max(2, improved_case_count)


def _strong_positive(
    *,
    hit_count: int,
    improved_case_count: int,
    worsened_case_count: int,
    net_effect: float,
) -> bool:
    return (
        hit_count >= 5
        and net_effect > 0
        and improved_case_count > worsened_case_count
    )


def _strong_negative(
    *,
    hit_count: int,
    improved_case_count: int,
    worsened_case_count: int,
    net_effect: float,
) -> bool:
    return (
        hit_count >= 5
        and net_effect < 0
        and worsened_case_count >= improved_case_count
    )


def _recalibrate_suggestion(
    *,
    current_severity: str,
    current_effect: str,
    net_effect: float,
    improved_case_count: int,
    worsened_case_count: int,
    changed_case_count: int,
) -> tuple[str, str]:
    if net_effect > 0 and improved_case_count > worsened_case_count:
        suggested_severity = "medium" if current_severity == "low" else current_severity
        suggested_effect = "lower_confidence" if current_effect == "warn" else current_effect
        return suggested_severity, suggested_effect

    if changed_case_count >= 4 and improved_case_count <= worsened_case_count + 1:
        suggested_severity = "medium" if current_severity == "high" else current_severity
        suggested_effect = "warn" if current_effect in {"lower_confidence", "raise_risk"} else current_effect
        return suggested_severity, suggested_effect

    return current_severity, current_effect


def _classify_rule(
    *,
    hit_count: int,
    changed_case_count: int,
    improved_case_count: int,
    worsened_case_count: int,
    net_effect: float,
    current_severity: str,
    current_effect: str,
) -> tuple[str, str, str, str]:
    strong_positive = _strong_positive(
        hit_count=hit_count,
        improved_case_count=improved_case_count,
        worsened_case_count=worsened_case_count,
        net_effect=net_effect,
    )
    strong_negative = _strong_negative(
        hit_count=hit_count,
        improved_case_count=improved_case_count,
        worsened_case_count=worsened_case_count,
        net_effect=net_effect,
    )
    conservative_only = _conservative_pressure(
        changed_case_count=changed_case_count,
        improved_case_count=improved_case_count,
        worsened_case_count=worsened_case_count,
    )

    if strong_negative:
        return (
            "remove_candidate",
            current_severity,
            current_effect,
            (
                f"命中 {hit_count} 次，净效果 {net_effect:.1f}，且 worsened={worsened_case_count} "
                f"不低于 improved={improved_case_count}，更像 active pool 中的拖累项，建议列为移除候选。"
            ),
        )

    if strong_positive and (current_effect == "warn" or current_severity == "low"):
        suggested_severity, suggested_effect = _recalibrate_suggestion(
            current_severity=current_severity,
            current_effect=current_effect,
            net_effect=net_effect,
            improved_case_count=improved_case_count,
            worsened_case_count=worsened_case_count,
            changed_case_count=changed_case_count,
        )
        return (
            "recalibrate",
            suggested_severity,
            suggested_effect,
            (
                f"命中 {hit_count} 次且 improved={improved_case_count} 明显高于 worsened={worsened_case_count}，"
                "规则本身值得保留，但当前 severity/effect 偏弱，建议做参数校准。"
            ),
        )

    if strong_positive and not conservative_only:
        return (
            "retain",
            current_severity,
            current_effect,
            (
                f"命中 {hit_count} 次，净效果 {net_effect:.1f}，且 improved={improved_case_count} "
                f"高于 worsened={worsened_case_count}，当前更适合继续保留。"
            ),
        )

    if conservative_only and (current_severity == "high" or current_effect in {"lower_confidence", "raise_risk"}):
        suggested_severity, suggested_effect = _recalibrate_suggestion(
            current_severity=current_severity,
            current_effect=current_effect,
            net_effect=net_effect,
            improved_case_count=improved_case_count,
            worsened_case_count=worsened_case_count,
            changed_case_count=changed_case_count,
        )
        return (
            "recalibrate",
            suggested_severity,
            suggested_effect,
            (
                f"规则改变了 {changed_case_count} 个样本，但 improved={improved_case_count} "
                f"并未明显领先 worsened={worsened_case_count}，当前更像参数过强，建议先校准 severity/effect。"
            ),
        )

    if changed_case_count >= 4 and improved_case_count <= worsened_case_count + 1:
        return (
            "downgrade",
            current_severity,
            current_effect,
            (
                f"规则改变了 {changed_case_count} 个样本，但净效果只有 {net_effect:.1f}，"
                "说明它仍可能有价值，但当前影响力偏强，建议先降级处理。"
            ),
        )

    return (
        "observe",
        current_severity,
        current_effect,
        (
            f"命中 {hit_count} 次、changed={changed_case_count}、net_effect={net_effect:.1f}，"
            "当前证据还不足以支持明确保留、降级或移除，建议继续观察。"
        ),
    )


def _summary(
    *,
    total_active_rules: int,
    decision_counts: dict[str, int],
    retain_rules: list[dict[str, Any]],
    remove_candidates: list[dict[str, Any]],
    recalibrate_rules: list[dict[str, Any]],
) -> str:
    if total_active_rules <= 0:
        return "当前没有可校准的 active rules，暂时无法生成 retain / downgrade / recalibrate 建议。"

    summary = (
        f"共评估 {total_active_rules} 条 active rules：retain={decision_counts['retain']}，"
        f"downgrade={decision_counts['downgrade']}，recalibrate={decision_counts['recalibrate']}，"
        f"remove_candidate={decision_counts['remove_candidate']}，observe={decision_counts['observe']}。"
    )
    if retain_rules:
        summary += f" 当前更值得继续保留的规则包括 {retain_rules[0]['title']}。"
    if recalibrate_rules:
        summary += f" 最需要优先校准的规则包括 {recalibrate_rules[0]['title']}。"
    if remove_candidates:
        summary += f" 当前最接近移除候选的规则包括 {remove_candidates[0]['title']}。"
    return summary


def build_active_rule_pool_calibration_report(
    *,
    validation_report: dict | None = None,
    rule_lifecycle_report: dict | None = None,
    rule_score_report: dict | None = None,
) -> dict[str, Any]:
    report = _empty_report()
    warnings: list[str] = []

    validation = _as_dict(validation_report)
    if not validation:
        report["summary"] = "缺少 active rule pool validation 输入，暂时无法生成校准建议。"
        report["warnings"] = ["No validation_report was provided for active rule pool calibration."]
        return report

    validation_rules = _as_list(validation.get("rule_effects"))
    if not validation_rules:
        report["ready"] = True
        report["summary"] = "当前 validation_report 中没有 active rule effects，暂时没有可校准规则。"
        report["warnings"] = ["No active rule effects were found in validation_report."]
        return report

    lifecycle_lookup = _lifecycle_lookup(_as_dict(rule_lifecycle_report))
    score_lookup = _score_lookup(_as_dict(rule_score_report))

    calibration_rules: list[dict[str, Any]] = []
    malformed_rules = 0

    for raw_rule in validation_rules:
        rule = _as_dict(raw_rule)
        if not rule:
            malformed_rules += 1
            continue

        title = _clean_text(rule.get("title"))
        lifecycle_rule = lifecycle_lookup.get(title, {})
        score_rule = score_lookup.get(title, {})

        hit_count = _as_int(rule.get("hit_count"))
        changed_case_count = _as_int(rule.get("changed_case_count"))
        improved_case_count = _as_int(rule.get("improved_case_count"))
        worsened_case_count = _as_int(rule.get("worsened_case_count"))
        net_effect = _as_float(rule.get("net_effect"))

        current_severity = _normalize_severity(
            rule.get("current_severity")
            or score_rule.get("severity")
        )
        current_effect = _normalize_effect(rule.get("current_effect"))

        decision, suggested_severity, suggested_effect, rationale = _classify_rule(
            hit_count=hit_count,
            changed_case_count=changed_case_count,
            improved_case_count=improved_case_count,
            worsened_case_count=worsened_case_count,
            net_effect=net_effect,
            current_severity=current_severity,
            current_effect=current_effect,
        )

        calibration_rule = {
            "rule_id": _clean_text(rule.get("rule_id")),
            "title": title,
            "category": _clean_text(rule.get("category") or lifecycle_rule.get("category") or score_rule.get("category")),
            "hit_count": hit_count,
            "changed_case_count": changed_case_count,
            "improved_case_count": improved_case_count,
            "worsened_case_count": worsened_case_count,
            "net_effect": float(net_effect),
            "current_severity": current_severity,
            "current_effect": current_effect,
            "calibration_decision": decision,
            "rationale": rationale,
            "suggested_severity": suggested_severity,
            "suggested_effect": suggested_effect,
            "notes": _clean_text(rule.get("notes")),
        }
        calibration_rules.append(calibration_rule)

        if calibration_rule["rule_id"] == "unknown" or calibration_rule["title"] == "unknown":
            warnings.append("One or more active rules had incomplete identifiers and were calibrated conservatively.")

    if malformed_rules:
        warnings.append(f"Skipped {malformed_rules} malformed active rule effect entries.")

    calibration_rules.sort(
        key=lambda item: (
            item["calibration_decision"] != "remove_candidate",
            item["calibration_decision"] != "recalibrate",
            item["calibration_decision"] != "retain",
            -item["hit_count"],
            -item["net_effect"],
            item["rule_id"],
        )
    )

    decision_counts = _empty_report()["decision_counts"]
    for row in calibration_rules:
        decision_counts[row["calibration_decision"]] += 1

    retain_rules = [row for row in calibration_rules if row["calibration_decision"] == "retain"]
    downgrade_rules = [row for row in calibration_rules if row["calibration_decision"] == "downgrade"]
    recalibrate_rules = [row for row in calibration_rules if row["calibration_decision"] == "recalibrate"]
    remove_candidates = [row for row in calibration_rules if row["calibration_decision"] == "remove_candidate"]
    observe_rules = [row for row in calibration_rules if row["calibration_decision"] == "observe"]

    report.update(
        {
            "ready": True,
            "total_active_rules": len(calibration_rules),
            "decision_counts": decision_counts,
            "rules": calibration_rules,
            "retain_rules": retain_rules,
            "downgrade_rules": downgrade_rules,
            "recalibrate_rules": recalibrate_rules,
            "remove_candidates": remove_candidates,
            "observe_rules": observe_rules,
            "summary": _summary(
                total_active_rules=len(calibration_rules),
                decision_counts=decision_counts,
                retain_rules=retain_rules,
                remove_candidates=remove_candidates,
                recalibrate_rules=recalibrate_rules,
            ),
            "warnings": warnings,
        }
    )
    return report


def analyze_active_rule_pool_calibration(
    *,
    validation_report: dict | None = None,
    rule_lifecycle_report: dict | None = None,
    rule_score_report: dict | None = None,
) -> dict[str, Any]:
    return build_active_rule_pool_calibration_report(
        validation_report=validation_report,
        rule_lifecycle_report=rule_lifecycle_report,
        rule_score_report=rule_score_report,
    )
