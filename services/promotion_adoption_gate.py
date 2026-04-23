"""Build a conservative production adoption handoff from promotion outputs."""

from __future__ import annotations

from typing import Any


def _empty_report() -> dict[str, Any]:
    return {
        "kind": "promotion_adoption_handoff",
        "ready": False,
        "total_rules": 0,
        "decision_counts": {
            "production_candidate": 0,
            "keep_in_execution_bridge": 0,
            "hold_for_more_evidence": 0,
            "not_ready_for_adoption": 0,
        },
        "rules": [],
        "production_candidates": [],
        "execution_bridge_holds": [],
        "evidence_holds": [],
        "not_ready_rules": [],
        "handoff_artifact": [],
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


def _normalize_confidence(value: Any, *, fallback: str = "low") -> str:
    text = _clean_text(value, fallback=fallback).lower()
    return text if text in {"high", "medium", "low"} else fallback


def _bridge_rule_lookup(bridge: dict[str, Any]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for raw_rule in _as_list(bridge.get("execution_bridge_rules")):
        rule = _as_dict(raw_rule)
        rule_id = _clean_text(rule.get("rule_id"), fallback="")
        if rule_id:
            lookup[rule_id] = rule
    return lookup


def _calibration_rule_lookup(calibration_report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for raw_rule in _as_list(calibration_report.get("rules")):
        rule = _as_dict(raw_rule)
        rule_id = _clean_text(rule.get("rule_id"), fallback="")
        if rule_id:
            lookup[rule_id] = rule
    return lookup


def _adoption_decision(
    *,
    promotion_decision: str,
    promotion_confidence: str,
    hit_count: int,
    net_effect: float,
) -> tuple[str, str]:
    if promotion_decision == "do_not_promote" or net_effect < 0:
        return (
            "not_ready_for_adoption",
            "Promotion outcome is negative or net effect is below zero, so this rule should stay out of production adoption review.",
        )

    if promotion_decision == "promote_candidate":
        if hit_count >= 5 and net_effect > 0 and promotion_confidence in {"high", "medium"}:
            return (
                "production_candidate",
                "Promotion signal is strong enough for formal production adoption review: promote_candidate, positive net effect, and sufficient hit count.",
            )
        return (
            "keep_in_execution_bridge",
            "Rule is promotable but evidence is still short of the more conservative production adoption gate.",
        )

    if promotion_decision in {"keep_active_observe", "hold_back"}:
        return (
            "hold_for_more_evidence",
            "Rule is not clearly negative, but the current promotion outcome still points to more observation before adoption review.",
        )

    return (
        "not_ready_for_adoption",
        "Promotion decision is incomplete or not supportive enough for production adoption review.",
    )


def _adoption_confidence(
    *,
    adoption_decision: str,
    promotion_confidence: str,
    hit_count: int,
    net_effect: float,
    has_bridge: bool,
) -> str:
    if adoption_decision == "production_candidate":
        if promotion_confidence == "high" and hit_count >= 8 and net_effect >= 1.0 and has_bridge:
            return "high"
        if promotion_confidence in {"high", "medium"}:
            return "medium" if has_bridge else "low"
        return "low"

    if adoption_decision == "keep_in_execution_bridge":
        if has_bridge and promotion_confidence in {"high", "medium"}:
            return "medium"
        return "low"

    if adoption_decision == "hold_for_more_evidence":
        return "medium" if promotion_confidence == "high" and net_effect >= 0 else "low"

    return "low"


def _handoff_message(
    *,
    title: str,
    hit_count: int,
    net_effect: float,
    adoption_confidence: str,
) -> str:
    return (
        f"{title} passed the conservative adoption gate with hit_count={hit_count}, "
        f"net_effect={net_effect:.1f}, adoption_confidence={adoption_confidence}."
    )


def _build_rule_entry(
    *,
    rule: dict[str, Any],
    bridge_rule: dict[str, Any],
    calibration_rule: dict[str, Any],
    bridge_available: bool,
) -> dict[str, Any]:
    rule_id = _clean_text(rule.get("rule_id"))
    title = _clean_text(rule.get("title"))
    category = _clean_text(rule.get("category"))
    promotion_decision = _clean_text(rule.get("promotion_decision")).lower()
    promotion_confidence = _normalize_confidence(rule.get("promotion_confidence"))
    hit_count = _as_int(rule.get("hit_count"))
    net_effect = _as_float(rule.get("net_effect"))
    has_complete_identity = all(
        value != "unknown" for value in (rule_id, title, category)
    )

    adoption_decision, adoption_rationale = _adoption_decision(
        promotion_decision=promotion_decision,
        promotion_confidence=promotion_confidence,
        hit_count=hit_count,
        net_effect=net_effect,
    )

    if adoption_decision == "production_candidate" and not has_complete_identity:
        adoption_decision = "keep_in_execution_bridge"
        adoption_rationale = (
            "Promotion signal is promising, but rule identity fields are incomplete, "
            "so it should stay in the execution bridge until the handoff is auditable."
        )

    has_bridge = bool(bridge_rule)
    adoption_confidence = _adoption_confidence(
        adoption_decision=adoption_decision,
        promotion_confidence=promotion_confidence,
        hit_count=hit_count,
        net_effect=net_effect,
        has_bridge=has_bridge,
    )

    note_parts: list[str] = []
    promotion_rationale = _clean_text(rule.get("promotion_rationale"), fallback="")
    rule_notes = _clean_text(rule.get("notes"), fallback="")
    calibration_reason = _clean_text(
        calibration_rule.get("calibration_rationale") or calibration_rule.get("rationale"),
        fallback="",
    )

    if promotion_rationale:
        note_parts.append(promotion_rationale)
    if rule_notes:
        note_parts.append(rule_notes)
    if calibration_reason:
        note_parts.append(calibration_reason)
    if bridge_available and not has_bridge and adoption_decision == "production_candidate":
        note_parts.append("Execution bridge entry not found; adoption confidence kept conservative.")

    return {
        "rule_id": rule_id,
        "title": title,
        "category": category,
        "promotion_decision": promotion_decision,
        "promotion_confidence": promotion_confidence,
        "hit_count": hit_count,
        "net_effect": net_effect,
        "adoption_decision": adoption_decision,
        "adoption_rationale": adoption_rationale,
        "adoption_confidence": adoption_confidence,
        "notes": " ".join(part for part in note_parts if part).strip(),
    }


def _handoff_item(rule: dict[str, Any], bridge_rule: dict[str, Any]) -> dict[str, Any]:
    return {
        "rule_id": rule["rule_id"],
        "title": rule["title"],
        "category": rule["category"],
        "severity": _clean_text(bridge_rule.get("severity"), fallback="unknown"),
        "message": _handoff_message(
            title=rule["title"],
            hit_count=rule["hit_count"],
            net_effect=rule["net_effect"],
            adoption_confidence=rule["adoption_confidence"],
        ),
        "effect": _clean_text(bridge_rule.get("effect"), fallback="unknown"),
        "adoption_confidence": rule["adoption_confidence"],
    }


def _summary(
    *,
    total_rules: int,
    decision_counts: dict[str, int],
    bridge_available: bool,
) -> str:
    if total_rules == 0:
        return (
            "No promotion rules were available for adoption review. "
            "Provide a promotion_report with rule entries to build a production candidate handoff."
        )

    bridge_phrase = "with execution bridge context" if bridge_available else "without execution bridge context"
    return (
        f"Evaluated {total_rules} rule(s) for production adoption review {bridge_phrase}: "
        f"{decision_counts['production_candidate']} production candidate(s), "
        f"{decision_counts['keep_in_execution_bridge']} execution-bridge hold(s), "
        f"{decision_counts['hold_for_more_evidence']} evidence hold(s), "
        f"and {decision_counts['not_ready_for_adoption']} not-ready rule(s)."
    )


def build_promotion_adoption_handoff(
    *,
    promotion_report: dict | None = None,
    promotion_execution_bridge: dict | None = None,
    calibration_report: dict | None = None,
) -> dict[str, Any]:
    report = _empty_report()
    warnings: list[str] = []

    source_report = _as_dict(promotion_report)
    bridge_report = _as_dict(promotion_execution_bridge)
    calibration = _as_dict(calibration_report)

    if not source_report:
        report["summary"] = (
            "No promotion_report provided; cannot build production adoption handoff. "
            "Run build_active_rule_pool_promotion_report first."
        )
        report["warnings"] = ["No promotion_report provided for promotion adoption gate."]
        return report

    source_rules = _as_list(source_report.get("rules"))
    report["total_rules"] = len(source_rules)

    if not bridge_report:
        warnings.append(
            "promotion_execution_bridge not provided; adoption confidence kept conservative."
        )

    if not source_rules:
        report["ready"] = True
        report["summary"] = _summary(
            total_rules=0,
            decision_counts=report["decision_counts"],
            bridge_available=bool(bridge_report),
        )
        warnings.append("No rules found in promotion_report.")
        report["warnings"] = warnings
        return report

    bridge_lookup = _bridge_rule_lookup(bridge_report)
    calibration_lookup = _calibration_rule_lookup(calibration)
    bridge_available = bool(bridge_report)

    malformed_count = 0
    rules: list[dict[str, Any]] = []
    production_candidates: list[dict[str, Any]] = []
    execution_bridge_holds: list[dict[str, Any]] = []
    evidence_holds: list[dict[str, Any]] = []
    not_ready_rules: list[dict[str, Any]] = []
    handoff_artifact: list[dict[str, Any]] = []

    for raw_rule in source_rules:
        rule = _as_dict(raw_rule)
        if not rule:
            malformed_count += 1
            continue

        rule_id = _clean_text(rule.get("rule_id"))
        bridge_rule = bridge_lookup.get(rule_id, {})
        calibration_rule = calibration_lookup.get(rule_id, {})

        entry = _build_rule_entry(
            rule=rule,
            bridge_rule=bridge_rule,
            calibration_rule=calibration_rule,
            bridge_available=bridge_available,
        )
        rules.append(entry)

        decision = entry["adoption_decision"]
        report["decision_counts"][decision] += 1

        if decision == "production_candidate":
            production_candidates.append(entry)
            handoff_artifact.append(_handoff_item(entry, bridge_rule))
        elif decision == "keep_in_execution_bridge":
            execution_bridge_holds.append(entry)
        elif decision == "hold_for_more_evidence":
            evidence_holds.append(entry)
        else:
            not_ready_rules.append(entry)

    if malformed_count:
        warnings.append(f"Skipped {malformed_count} malformed promotion rule entries.")

    report.update(
        {
            "ready": True,
            "rules": rules,
            "production_candidates": production_candidates,
            "execution_bridge_holds": execution_bridge_holds,
            "evidence_holds": evidence_holds,
            "not_ready_rules": not_ready_rules,
            "handoff_artifact": handoff_artifact,
            "summary": _summary(
                total_rules=len(source_rules),
                decision_counts=report["decision_counts"],
                bridge_available=bridge_available,
            ),
            "warnings": warnings,
        }
    )
    return report


analyze_promotion_adoption_gate = build_promotion_adoption_handoff
