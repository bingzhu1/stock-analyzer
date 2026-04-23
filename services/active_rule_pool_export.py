from __future__ import annotations

import hashlib
from typing import Any


def _empty_report() -> dict[str, Any]:
    return {
        "kind": "active_rule_pool_export",
        "ready": False,
        "pool_name": "default_active_rule_pool",
        "version_tag": "unversioned",
        "total_input_rules": 0,
        "exported_rule_count": 0,
        "exported_rules": [],
        "excluded_from_export": [],
        "preflight_bridge_rules": [],
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


def _normalize_pool_decision(rule: dict[str, Any]) -> str:
    decision = _clean_text(rule.get("pool_decision"), fallback="hold").lower()
    if decision in {"include", "hold", "exclude"}:
        return decision
    return "hold"


def _stable_rule_id(pool_name: str, rule_key: str) -> str:
    payload = f"{pool_name}::{rule_key}".encode("utf-8")
    digest = hashlib.sha1(payload).hexdigest()[:12]
    return f"arp-{digest}"


def _exported_rule_from_input(rule: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    title = _clean_text(rule.get("title"))
    category = _clean_text(rule.get("category"))
    severity = _clean_text(rule.get("severity"), fallback="unknown").lower()
    if severity not in {"low", "medium", "high", "unknown"}:
        severity = "unknown"
        warnings.append("Invalid severity encountered; exported as unknown.")

    effect = _clean_text(rule.get("effect"), fallback="unknown").lower()
    if effect not in {"warn", "lower_confidence", "raise_risk", "unknown"}:
        effect = "unknown"
        warnings.append("Invalid effect encountered; exported as unknown.")

    message_value = rule.get("message") or rule.get("pool_rationale")
    message = _clean_text(message_value)
    if message == "unknown":
        warnings.append("Missing rule message; exported with unknown placeholder.")

    if title == "unknown" or category == "unknown" or _clean_text(rule.get("rule_key")) == "unknown":
        warnings.append("Include rule had incomplete identifiers; exported with conservative placeholders.")

    exported_rule = {
        "rule_key": _clean_text(rule.get("rule_key")),
        "title": title,
        "category": category,
        "severity": severity,
        "message": message,
        "effect": effect,
        "source_status": _clean_text(rule.get("lifecycle_state"), fallback="unknown"),
        "pool_decision": _normalize_pool_decision(rule),
        "pool_rationale": _clean_text(rule.get("pool_rationale")),
        "recommended_action": _clean_text(rule.get("recommended_action"), fallback="unknown"),
        "hit_count": _as_int(rule.get("hit_count")),
        "net_score": float(_as_float(rule.get("net_score")) or 0.0),
        "effectiveness_rate": _as_float(rule.get("effectiveness_rate")),
        "harm_rate": _as_float(rule.get("harm_rate")),
    }
    return exported_rule, warnings


def build_active_rule_pool_export(
    active_rule_pool_report: dict[str, Any] | None = None,
    rules: list[dict[str, Any]] | None = None,
    pool_name: str = "default_active_rule_pool",
    version_tag: str | None = None,
) -> dict[str, Any]:
    report = _empty_report()
    clean_pool_name = _clean_text(pool_name, fallback="default_active_rule_pool")
    clean_version_tag = _clean_text(version_tag, fallback="unversioned")
    warnings: list[str] = []

    source_report = _as_dict(active_rule_pool_report)
    source_rules = _as_list(rules if rules is not None else source_report.get("rules"))
    report["pool_name"] = clean_pool_name
    report["version_tag"] = clean_version_tag
    report["total_input_rules"] = len(source_rules)

    if not source_report and rules is None:
        report["summary"] = "缺少 active rule pool 输入，暂时无法导出 active pool artifact。"
        report["warnings"] = ["No active_rule_pool_report or rules were provided for export."]
        return report

    if not source_rules:
        report["ready"] = True
        report["summary"] = "当前没有可导出的 active pool 规则，导出结果为空。"
        warnings.append("No active pool rules were available for export.")
        report["warnings"] = warnings
        return report

    exported_rules: list[dict[str, Any]] = []
    excluded_from_export: list[dict[str, str]] = []
    malformed_rules = 0

    for raw_rule in source_rules:
        rule = _as_dict(raw_rule)
        if not rule:
            malformed_rules += 1
            continue

        pool_decision = _normalize_pool_decision(rule)
        rule_key = _clean_text(rule.get("rule_key"))
        if pool_decision != "include":
            excluded_from_export.append(
                {
                    "rule_key": rule_key,
                    "reason": "hold_or_exclude",
                }
            )
            continue

        exported_rule, export_warnings = _exported_rule_from_input(rule)
        exported_rules.append(exported_rule)
        warnings.extend(export_warnings)

    if malformed_rules:
        warnings.append(f"Skipped {malformed_rules} malformed active pool rule entries.")

    preflight_bridge_rules = [
        {
            "rule_id": _stable_rule_id(clean_pool_name, rule["rule_key"]),
            "title": rule["title"],
            "category": rule["category"],
            "severity": rule["severity"],
            "message": rule["message"],
            "effect": rule["effect"],
        }
        for rule in exported_rules
    ]

    if not exported_rules:
        summary = (
            f"共收到 {len(source_rules)} 条 active pool 规则，但当前无可导出的 include 规则。"
        )
    else:
        summary = (
            f"共收到 {len(source_rules)} 条 active pool 规则，成功导出 {len(exported_rules)} 条 include 规则，"
            f"并生成 {len(preflight_bridge_rules)} 条 preflight bridge 规则。"
        )

    report.update(
        {
            "ready": True,
            "exported_rule_count": len(exported_rules),
            "exported_rules": exported_rules,
            "excluded_from_export": excluded_from_export,
            "preflight_bridge_rules": preflight_bridge_rules,
            "summary": summary,
            "warnings": warnings,
        }
    )
    return report


export_active_rule_pool = build_active_rule_pool_export
