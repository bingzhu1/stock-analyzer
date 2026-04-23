"""Monitor active rule pool for drift: compare overall vs recent rule effects."""

from __future__ import annotations

from typing import Any

_MIN_RECENT_HITS = 3
_DRIFT_THRESHOLD = 1.0
_IMPROVE_THRESHOLD = 1.0


def _empty_report() -> dict[str, Any]:
    return {
        "kind": "active_rule_pool_drift_report",
        "ready": False,
        "total_rules": 0,
        "status_counts": {
            "stable": 0,
            "drift_candidate": 0,
            "improving": 0,
            "unclear": 0,
        },
        "rules": [],
        "drift_candidates": [],
        "stable_rules": [],
        "improving_rules": [],
        "unclear_rules": [],
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


def _build_recent_lookup(recent_rule_effects: list[Any]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for raw in recent_rule_effects:
        rule = _as_dict(raw)
        if not rule:
            continue
        rule_id = _clean_text(rule.get("rule_id"))
        title = _clean_text(rule.get("title"))
        key = rule_id if rule_id != "unknown" else title
        if key and key != "unknown":
            lookup[key] = rule
    return lookup


def _recent_key(rule: dict[str, Any]) -> str:
    rule_id = _clean_text(rule.get("rule_id"))
    title = _clean_text(rule.get("title"))
    return rule_id if rule_id != "unknown" else title


def _drift_status(
    *,
    overall_hit_count: int,
    overall_net_effect: float,
    recent_hit_count: int,
    recent_net_effect: float,
    has_recent_data: bool,
) -> str:
    if not has_recent_data or recent_hit_count < _MIN_RECENT_HITS:
        return "unclear"

    if (
        overall_net_effect > 0
        and (
            recent_net_effect < 0
            or recent_net_effect <= overall_net_effect - _DRIFT_THRESHOLD
        )
    ):
        return "drift_candidate"

    if (
        recent_net_effect >= overall_net_effect + _IMPROVE_THRESHOLD
        and recent_net_effect > 0
    ):
        return "improving"

    return "stable"


def _recommended_followup(*, drift_status: str, recent_net_effect: float) -> str:
    if drift_status == "drift_candidate":
        if recent_net_effect < -_DRIFT_THRESHOLD:
            return "review_for_removal"
        return "review_for_downgrade"
    if drift_status == "stable":
        return "retain"
    return "keep_monitoring"


def _drift_rationale(
    *,
    drift_status: str,
    overall_hit_count: int,
    overall_net_effect: float,
    recent_hit_count: int,
    recent_net_effect: float,
    has_recent_data: bool,
) -> str:
    if not has_recent_data:
        return (
            f"No recent_rule_effects provided; overall hit_count={overall_hit_count}, "
            f"net_effect={overall_net_effect:.2f}. Cannot compare recent vs overall — marking unclear."
        )
    if recent_hit_count < _MIN_RECENT_HITS:
        return (
            f"recent_hit_count={recent_hit_count} (<{_MIN_RECENT_HITS}); insufficient recent samples "
            f"for reliable comparison. Overall: hit_count={overall_hit_count}, net_effect={overall_net_effect:.2f}."
        )
    if drift_status == "drift_candidate":
        return (
            f"Overall net_effect={overall_net_effect:.2f} (positive), but recent net_effect={recent_net_effect:.2f} "
            f"({'-negative' if recent_net_effect < 0 else 'dropped by ≥1.0'}). "
            f"recent_hit_count={recent_hit_count}. Rule appears to be drifting downward."
        )
    if drift_status == "improving":
        return (
            f"Recent net_effect={recent_net_effect:.2f} is notably higher than overall net_effect={overall_net_effect:.2f} "
            f"(improvement ≥{_IMPROVE_THRESHOLD:.1f}). recent_hit_count={recent_hit_count}. Rule is improving."
        )
    return (
        f"Overall net_effect={overall_net_effect:.2f}, recent net_effect={recent_net_effect:.2f}. "
        f"recent_hit_count={recent_hit_count}. No significant drift detected — rule appears stable."
    )


def _drift_summary(
    *,
    total_rules: int,
    status_counts: dict[str, int],
    drift_candidates: list[dict[str, Any]],
    stable_rules: list[dict[str, Any]],
    improving_rules: list[dict[str, Any]],
    unclear_rules: list[dict[str, Any]],
) -> str:
    if total_rules <= 0:
        return (
            "No active rules were available for drift monitoring. "
            "Provide a validation_report with rule_effects to generate a drift report."
        )
    summary = (
        f"Drift monitor evaluated {total_rules} rule(s): "
        f"stable={status_counts['stable']}, "
        f"drift_candidate={status_counts['drift_candidate']}, "
        f"improving={status_counts['improving']}, "
        f"unclear={status_counts['unclear']}."
    )
    if drift_candidates:
        summary += f" {len(drift_candidates)} rule(s) flagged as drift_candidate for follow-up."
    if improving_rules:
        summary += f" {len(improving_rules)} rule(s) are improving recently."
    if unclear_rules:
        summary += f" {len(unclear_rules)} rule(s) lack sufficient recent data."
    return summary


def build_active_rule_pool_drift_report(
    *,
    validation_report: dict | None = None,
    recent_window_size: int = 20,
    recent_rule_effects: list[dict] | None = None,
) -> dict[str, Any]:
    report = _empty_report()
    warnings: list[str] = []

    validation = _as_dict(validation_report)
    if not validation:
        report["summary"] = (
            "No validation_report was provided; cannot generate drift report. "
            "Run build_active_rule_pool_validation_report first."
        )
        report["warnings"] = ["No validation_report provided for active rule pool drift monitor."]
        return report

    overall_rule_effects = _as_list(validation.get("rule_effects"))
    if not overall_rule_effects:
        report["ready"] = True
        report["summary"] = (
            "validation_report contained no rule_effects; "
            "no active rules available for drift monitoring."
        )
        report["warnings"] = ["No rule_effects found in validation_report."]
        return report

    has_recent_data = recent_rule_effects is not None
    recent_lookup = _build_recent_lookup(_as_list(recent_rule_effects)) if has_recent_data else {}

    if has_recent_data and not recent_lookup:
        warnings.append("recent_rule_effects was provided but contained no valid entries.")

    drift_rules: list[dict[str, Any]] = []
    malformed_count = 0

    for raw_rule in overall_rule_effects:
        rule = _as_dict(raw_rule)
        if not rule:
            malformed_count += 1
            continue

        rule_id = _clean_text(rule.get("rule_id"))
        title = _clean_text(rule.get("title"))
        overall_hit_count = _as_int(rule.get("hit_count"))
        overall_net_effect = _as_float(rule.get("net_effect"))

        key = rule_id if rule_id != "unknown" else title
        recent_entry = recent_lookup.get(key, {}) if has_recent_data else {}
        recent_hit_count = _as_int(recent_entry.get("hit_count")) if recent_entry else 0
        recent_net_effect = _as_float(recent_entry.get("net_effect")) if recent_entry else 0.0

        if rule_id == "unknown" or title == "unknown":
            warnings.append(
                "One or more rules had incomplete identifiers; drift assessed conservatively."
            )

        status = _drift_status(
            overall_hit_count=overall_hit_count,
            overall_net_effect=overall_net_effect,
            recent_hit_count=recent_hit_count,
            recent_net_effect=recent_net_effect,
            has_recent_data=has_recent_data,
        )

        rationale = _drift_rationale(
            drift_status=status,
            overall_hit_count=overall_hit_count,
            overall_net_effect=overall_net_effect,
            recent_hit_count=recent_hit_count,
            recent_net_effect=recent_net_effect,
            has_recent_data=has_recent_data,
        )

        followup = _recommended_followup(
            drift_status=status,
            recent_net_effect=recent_net_effect,
        )

        drift_rules.append(
            {
                "rule_id": rule_id,
                "title": title,
                "overall_hit_count": overall_hit_count,
                "overall_net_effect": float(overall_net_effect),
                "recent_hit_count": recent_hit_count,
                "recent_net_effect": float(recent_net_effect),
                "drift_status": status,
                "drift_rationale": rationale,
                "recommended_followup": followup,
                "notes": _clean_text(rule.get("notes")),
            }
        )

    if malformed_count:
        warnings.append(f"Skipped {malformed_count} malformed rule_effect entries.")

    status_counts = _empty_report()["status_counts"]
    for row in drift_rules:
        status_counts[row["drift_status"]] += 1

    drift_candidates = [r for r in drift_rules if r["drift_status"] == "drift_candidate"]
    stable_rules = [r for r in drift_rules if r["drift_status"] == "stable"]
    improving_rules = [r for r in drift_rules if r["drift_status"] == "improving"]
    unclear_rules = [r for r in drift_rules if r["drift_status"] == "unclear"]

    report.update(
        {
            "ready": True,
            "total_rules": len(drift_rules),
            "status_counts": status_counts,
            "rules": drift_rules,
            "drift_candidates": drift_candidates,
            "stable_rules": stable_rules,
            "improving_rules": improving_rules,
            "unclear_rules": unclear_rules,
            "summary": _drift_summary(
                total_rules=len(drift_rules),
                status_counts=status_counts,
                drift_candidates=drift_candidates,
                stable_rules=stable_rules,
                improving_rules=improving_rules,
                unclear_rules=unclear_rules,
            ),
            "warnings": warnings,
        }
    )
    return report


def analyze_active_rule_pool_drift(
    *,
    validation_report: dict | None = None,
    recent_window_size: int = 20,
    recent_rule_effects: list[dict] | None = None,
) -> dict[str, Any]:
    return build_active_rule_pool_drift_report(
        validation_report=validation_report,
        recent_window_size=recent_window_size,
        recent_rule_effects=recent_rule_effects,
    )
