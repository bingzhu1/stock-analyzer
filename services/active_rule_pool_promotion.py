"""Build promotion policy report from active rule pool calibration results."""

from __future__ import annotations

from typing import Any


def _empty_report() -> dict[str, Any]:
    return {
        "kind": "active_rule_pool_promotion_report",
        "ready": False,
        "total_rules": 0,
        "decision_counts": {
            "promote_candidate": 0,
            "keep_active_observe": 0,
            "hold_back": 0,
            "do_not_promote": 0,
        },
        "rules": [],
        "promote_candidates": [],
        "keep_active_observe_rules": [],
        "hold_back_rules": [],
        "do_not_promote_rules": [],
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


def _is_promote_candidate(
    *,
    calibration_decision: str,
    hit_count: int,
    net_effect: float,
    improved_case_count: int,
    worsened_case_count: int,
) -> bool:
    return (
        calibration_decision == "retain"
        and hit_count >= 5
        and net_effect > 0
        and improved_case_count > worsened_case_count
    )


def _is_do_not_promote_edge(
    *,
    hit_count: int,
    net_effect: float,
    improved_case_count: int,
    worsened_case_count: int,
) -> bool:
    return (
        hit_count >= 5
        and net_effect < -1.0
        and worsened_case_count >= improved_case_count
    )


def _promotion_decision(
    *,
    calibration_decision: str,
    hit_count: int,
    net_effect: float,
    improved_case_count: int,
    worsened_case_count: int,
) -> str:
    # do_not_promote: explicit remove_candidate
    if calibration_decision == "remove_candidate":
        return "do_not_promote"

    # promote_candidate: retain with strong positive signal
    if _is_promote_candidate(
        calibration_decision=calibration_decision,
        hit_count=hit_count,
        net_effect=net_effect,
        improved_case_count=improved_case_count,
        worsened_case_count=worsened_case_count,
    ):
        return "promote_candidate"

    # hold_back: downgrade or recalibrate
    if calibration_decision in {"downgrade", "recalibrate"}:
        return "hold_back"

    # do_not_promote fallback: edge case of strong negative impact
    if _is_do_not_promote_edge(
        hit_count=hit_count,
        net_effect=net_effect,
        improved_case_count=improved_case_count,
        worsened_case_count=worsened_case_count,
    ):
        return "do_not_promote"

    # keep_active_observe: observe, or retain not meeting all promote conditions
    return "keep_active_observe"


def _promotion_confidence(
    *,
    promotion_decision: str,
    calibration_decision: str,
    hit_count: int,
    net_effect: float,
) -> str:
    if promotion_decision == "promote_candidate":
        if hit_count >= 10 and net_effect >= 1.0:
            return "high"
        return "medium"

    if promotion_decision == "do_not_promote" and calibration_decision == "remove_candidate":
        if hit_count >= 5:
            return "high"
        return "medium"

    return "low"


def _promotion_rationale(
    *,
    promotion_decision: str,
    calibration_decision: str,
    hit_count: int,
    net_effect: float,
    improved_case_count: int,
    worsened_case_count: int,
) -> str:
    if promotion_decision == "promote_candidate":
        return (
            f"Rule meets all promotion criteria: calibration_decision=retain, "
            f"hit_count={hit_count} (>=5), net_effect={net_effect:.2f} (>0), "
            f"improved={improved_case_count} > worsened={worsened_case_count}. "
            "Recommend promoting to active rule pool."
        )

    if promotion_decision == "keep_active_observe":
        if calibration_decision == "observe":
            return (
                f"Calibration decision is observe with hit_count={hit_count}, "
                f"net_effect={net_effect:.2f}. Insufficient evidence for promotion; keep active and continue observing."
            )
        # retain but not meeting all conditions
        reasons = []
        if hit_count < 5:
            reasons.append(f"hit_count={hit_count} (<5)")
        if net_effect <= 0:
            reasons.append(f"net_effect={net_effect:.2f} (<=0)")
        if improved_case_count <= worsened_case_count:
            reasons.append(f"improved={improved_case_count} <= worsened={worsened_case_count}")
        reason_str = "; ".join(reasons) if reasons else "not all promotion conditions met"
        return (
            f"Calibration decision is retain but not all promotion conditions met: {reason_str}. "
            "Keep active and observe for future promotion."
        )

    if promotion_decision == "hold_back":
        return (
            f"Calibration decision is {calibration_decision}: rule needs adjustment before promotion. "
            f"hit_count={hit_count}, net_effect={net_effect:.2f}, "
            f"improved={improved_case_count}, worsened={worsened_case_count}. "
            "Hold back until recalibration or re-evaluation is complete."
        )

    if promotion_decision == "do_not_promote":
        if calibration_decision == "remove_candidate":
            return (
                f"Calibration decision is remove_candidate: rule is flagged for removal. "
                f"hit_count={hit_count}, net_effect={net_effect:.2f}, "
                f"worsened={worsened_case_count} >= improved={improved_case_count}. "
                "Do not promote; consider retiring this rule."
            )
        return (
            f"Edge case: hit_count={hit_count} (>=5), net_effect={net_effect:.2f} (<-1.0), "
            f"worsened={worsened_case_count} >= improved={improved_case_count}. "
            "Strong negative signal; do not promote."
        )

    return "Decision could not be determined; conservatively keeping active for observation."


def _promotion_summary(
    *,
    total_rules: int,
    decision_counts: dict[str, int],
    promote_candidates: list[dict[str, Any]],
    do_not_promote_rules: list[dict[str, Any]],
    hold_back_rules: list[dict[str, Any]],
) -> str:
    if total_rules <= 0:
        return (
            "No rules available for promotion evaluation. "
            "Provide a calibration_report with at least one rule to generate a promotion policy."
        )

    summary = (
        f"Evaluated {total_rules} rules for promotion: "
        f"promote_candidate={decision_counts['promote_candidate']}, "
        f"keep_active_observe={decision_counts['keep_active_observe']}, "
        f"hold_back={decision_counts['hold_back']}, "
        f"do_not_promote={decision_counts['do_not_promote']}."
    )
    if promote_candidates:
        summary += f" Top promotion candidate: {promote_candidates[0]['title']}."
    if hold_back_rules:
        summary += f" {len(hold_back_rules)} rule(s) held back pending recalibration."
    if do_not_promote_rules:
        summary += f" {len(do_not_promote_rules)} rule(s) flagged as do_not_promote."
    return summary


def build_active_rule_pool_promotion_report(
    *,
    calibration_report: dict | None = None,
    validation_report: dict | None = None,
    lifecycle_report: dict | None = None,
) -> dict[str, Any]:
    report = _empty_report()
    warnings: list[str] = []

    calibration = _as_dict(calibration_report)
    if not calibration:
        report["summary"] = (
            "No calibration_report was provided; cannot generate promotion policy. "
            "Run build_active_rule_pool_calibration_report first."
        )
        report["warnings"] = [
            "No calibration_report was provided for active rule pool promotion."
        ]
        return report

    raw_rules = _as_list(calibration.get("rules"))
    if not raw_rules:
        report["ready"] = True
        report["summary"] = (
            "Calibration report contains no rules. "
            "No promotion decisions can be made at this time."
        )
        report["warnings"] = ["calibration_report contained an empty rules list."]
        return report

    promotion_rules: list[dict[str, Any]] = []
    malformed_count = 0

    for raw_rule in raw_rules:
        rule = _as_dict(raw_rule)
        if not rule:
            malformed_count += 1
            continue

        rule_id = _clean_text(rule.get("rule_id"))
        title = _clean_text(rule.get("title"))
        category = _clean_text(rule.get("category"))
        calibration_decision = _clean_text(rule.get("calibration_decision"), fallback="observe")
        hit_count = _as_int(rule.get("hit_count"))
        improved_case_count = _as_int(rule.get("improved_case_count"))
        worsened_case_count = _as_int(rule.get("worsened_case_count"))
        net_effect = _as_float(rule.get("net_effect"))
        notes = _clean_text(rule.get("notes"))

        # Normalize calibration_decision to known values; fallback to observe
        known_decisions = {"retain", "downgrade", "recalibrate", "remove_candidate", "observe"}
        if calibration_decision not in known_decisions:
            warnings.append(
                f"Rule '{title}' had unknown calibration_decision '{calibration_decision}'; "
                "treating as observe."
            )
            calibration_decision = "observe"

        decision = _promotion_decision(
            calibration_decision=calibration_decision,
            hit_count=hit_count,
            net_effect=net_effect,
            improved_case_count=improved_case_count,
            worsened_case_count=worsened_case_count,
        )

        confidence = _promotion_confidence(
            promotion_decision=decision,
            calibration_decision=calibration_decision,
            hit_count=hit_count,
            net_effect=net_effect,
        )

        rationale = _promotion_rationale(
            promotion_decision=decision,
            calibration_decision=calibration_decision,
            hit_count=hit_count,
            net_effect=net_effect,
            improved_case_count=improved_case_count,
            worsened_case_count=worsened_case_count,
        )

        if rule_id == "unknown" or title == "unknown":
            warnings.append(
                "One or more rules had incomplete identifiers and were assigned promotion decisions conservatively."
            )

        promotion_rules.append(
            {
                "rule_id": rule_id,
                "title": title,
                "category": category,
                "calibration_decision": calibration_decision,
                "hit_count": hit_count,
                "improved_case_count": improved_case_count,
                "worsened_case_count": worsened_case_count,
                "net_effect": float(net_effect),
                "promotion_decision": decision,
                "promotion_rationale": rationale,
                "promotion_confidence": confidence,
                "notes": notes,
            }
        )

    if malformed_count:
        warnings.append(f"Skipped {malformed_count} malformed rule entries.")

    decision_counts = _empty_report()["decision_counts"]
    for row in promotion_rules:
        decision_counts[row["promotion_decision"]] += 1

    promote_candidates = [r for r in promotion_rules if r["promotion_decision"] == "promote_candidate"]
    keep_active_observe_rules = [r for r in promotion_rules if r["promotion_decision"] == "keep_active_observe"]
    hold_back_rules = [r for r in promotion_rules if r["promotion_decision"] == "hold_back"]
    do_not_promote_rules = [r for r in promotion_rules if r["promotion_decision"] == "do_not_promote"]

    report.update(
        {
            "ready": True,
            "total_rules": len(promotion_rules),
            "decision_counts": decision_counts,
            "rules": promotion_rules,
            "promote_candidates": promote_candidates,
            "keep_active_observe_rules": keep_active_observe_rules,
            "hold_back_rules": hold_back_rules,
            "do_not_promote_rules": do_not_promote_rules,
            "summary": _promotion_summary(
                total_rules=len(promotion_rules),
                decision_counts=decision_counts,
                promote_candidates=promote_candidates,
                do_not_promote_rules=do_not_promote_rules,
                hold_back_rules=hold_back_rules,
            ),
            "warnings": warnings,
        }
    )
    return report


def analyze_active_rule_pool_promotion(
    *,
    calibration_report: dict | None = None,
    validation_report: dict | None = None,
    lifecycle_report: dict | None = None,
) -> dict[str, Any]:
    return build_active_rule_pool_promotion_report(
        calibration_report=calibration_report,
        validation_report=validation_report,
        lifecycle_report=lifecycle_report,
    )
