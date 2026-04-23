"""Export promotion-ready rules as execution-ready bridge artifact from Task 061 output."""

from __future__ import annotations

import hashlib
from typing import Any


def _empty_report() -> dict[str, Any]:
    return {
        "kind": "promotion_execution_bridge",
        "ready": False,
        "bridge_name": "default_promotion_bridge",
        "version_tag": "unversioned",
        "execution_enabled": False,
        "total_input_rules": 0,
        "promotable_rule_count": 0,
        "promotable_rules": [],
        "held_back_rules": [],
        "execution_bridge_rules": [],
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
    return text if text in {"low", "medium", "high", "unknown"} else "unknown"


def _normalize_effect(value: Any) -> str:
    text = _clean_text(value, fallback="unknown").lower()
    return text if text in {"warn", "lower_confidence", "raise_risk", "unknown"} else "unknown"


def _normalize_confidence(value: Any) -> str:
    text = _clean_text(value, fallback="low").lower()
    return text if text in {"high", "medium", "low"} else "low"


def _stable_bridge_rule_id(bridge_name: str, rule_id: str, title: str) -> str:
    if rule_id and rule_id != "unknown":
        return rule_id
    payload = f"{bridge_name}::{title}".encode("utf-8")
    digest = hashlib.sha1(payload).hexdigest()[:12]
    return f"peb-{digest}"


def _build_promotable_rule(rule: dict[str, Any]) -> dict[str, Any]:
    return {
        "rule_id": _clean_text(rule.get("rule_id")),
        "title": _clean_text(rule.get("title")),
        "category": _clean_text(rule.get("category")),
        "promotion_decision": "promote_candidate",
        "promotion_confidence": _normalize_confidence(rule.get("promotion_confidence")),
        "promotion_rationale": _clean_text(rule.get("promotion_rationale")),
        "severity": _normalize_severity(rule.get("severity")),
        "effect": _normalize_effect(rule.get("effect")),
        "message": _clean_text(rule.get("message")),
        "hit_count": _as_int(rule.get("hit_count")),
        "net_effect": _as_float(rule.get("net_effect")),
    }


def _build_bridge_rule(promotable: dict[str, Any], bridge_name: str) -> dict[str, Any]:
    stable_id = _stable_bridge_rule_id(
        bridge_name,
        promotable["rule_id"],
        promotable["title"],
    )
    return {
        "rule_id": stable_id,
        "title": promotable["title"],
        "category": promotable["category"],
        "severity": promotable["severity"],
        "message": promotable["message"],
        "effect": promotable["effect"],
    }


def _promotion_summary(
    *,
    total_input_rules: int,
    promotable_rule_count: int,
    held_back_count: int,
    execution_enabled: bool,
    bridge_name: str,
) -> str:
    if total_input_rules == 0:
        return (
            "No rules were available for promotion bridge export. "
            "Provide a promotion_report with promote_candidate rules to generate an artifact."
        )
    if promotable_rule_count == 0:
        return (
            f"Evaluated {total_input_rules} rule(s); no promote_candidate rules found. "
            "Current promotion bridge is empty. No execution-ready rules to export."
        )
    gate_status = "enabled" if execution_enabled else "disabled (artifact only)"
    return (
        f"Bridge '{bridge_name}': {promotable_rule_count} promotion-ready rule(s) "
        f"out of {total_input_rules} input rule(s); {held_back_count} held back. "
        f"Execution gate: {gate_status}."
    )


def build_promotion_execution_bridge(
    *,
    promotion_report: dict | None = None,
    rules: list[dict] | None = None,
    bridge_name: str = "default_promotion_bridge",
    version_tag: str | None = None,
    enable_execution_bridge: bool = False,
) -> dict[str, Any]:
    report = _empty_report()
    clean_bridge_name = _clean_text(bridge_name, fallback="default_promotion_bridge")
    clean_version_tag = _clean_text(version_tag, fallback="unversioned")
    warnings: list[str] = []

    report["bridge_name"] = clean_bridge_name
    report["version_tag"] = clean_version_tag
    report["execution_enabled"] = bool(enable_execution_bridge)

    # Resolve source rules: promotion_report["rules"] preferred, then direct rules
    source_report = _as_dict(promotion_report)
    if rules is not None:
        source_rules = _as_list(rules)
    elif source_report:
        source_rules = _as_list(source_report.get("rules"))
    else:
        source_rules = []

    if not source_report and rules is None:
        report["summary"] = (
            "No promotion_report or rules were provided; cannot generate promotion execution bridge. "
            "Run build_active_rule_pool_promotion_report first."
        )
        report["warnings"] = [
            "No promotion_report or rules provided for promotion execution bridge."
        ]
        return report

    report["total_input_rules"] = len(source_rules)

    if not source_rules:
        report["ready"] = True
        report["summary"] = _promotion_summary(
            total_input_rules=0,
            promotable_rule_count=0,
            held_back_count=0,
            execution_enabled=bool(enable_execution_bridge),
            bridge_name=clean_bridge_name,
        )
        warnings.append("No rules found in promotion_report or rules input.")
        report["warnings"] = warnings
        return report

    promotable_rules: list[dict[str, Any]] = []
    held_back_rules: list[dict[str, Any]] = []
    malformed_count = 0

    for raw_rule in source_rules:
        rule = _as_dict(raw_rule)
        if not rule:
            malformed_count += 1
            continue

        promotion_decision = _clean_text(rule.get("promotion_decision"), fallback="unknown")

        if promotion_decision == "promote_candidate":
            promotable = _build_promotable_rule(rule)
            if promotable["rule_id"] == "unknown" or promotable["title"] == "unknown":
                warnings.append(
                    "One or more promote_candidate rules had incomplete identifiers; "
                    "exported with conservative placeholders."
                )
            promotable_rules.append(promotable)
        else:
            rule_id = _clean_text(rule.get("rule_id"))
            held_back_rules.append(
                {
                    "rule_id": rule_id,
                    "reason": "not_promoted",
                }
            )

    if malformed_count:
        warnings.append(f"Skipped {malformed_count} malformed rule entries.")

    execution_bridge_rules = [
        _build_bridge_rule(p, clean_bridge_name) for p in promotable_rules
    ]

    report.update(
        {
            "ready": True,
            "total_input_rules": len(source_rules),
            "promotable_rule_count": len(promotable_rules),
            "promotable_rules": promotable_rules,
            "held_back_rules": held_back_rules,
            "execution_bridge_rules": execution_bridge_rules,
            "summary": _promotion_summary(
                total_input_rules=len(source_rules),
                promotable_rule_count=len(promotable_rules),
                held_back_count=len(held_back_rules),
                execution_enabled=bool(enable_execution_bridge),
                bridge_name=clean_bridge_name,
            ),
            "warnings": warnings,
        }
    )
    return report


export_promotion_execution_candidates = build_promotion_execution_bridge
