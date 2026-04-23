from __future__ import annotations

from typing import Any


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _clean_text(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _empty_dashboard() -> dict[str, Any]:
    return {
        "kind": "rule_dashboard_view",
        "ready": False,
        "header": {
            "symbol": "AVGO",
            "run_date": "unknown",
            "overall_status": "degraded",
        },
        "headline_cards": {
            "active_rule_count": 0,
            "promote_candidate_count": 0,
            "production_candidate_count": 0,
            "drift_candidate_count": 0,
            "direction_accuracy": None,
        },
        "active_rules": [],
        "promotion_candidates": [],
        "production_candidates": [],
        "drift_candidates": [],
        "risk_flags": [],
        "summary": "",
        "warnings": [],
    }


def _header(daily_training_brief: dict[str, Any]) -> dict[str, str]:
    brief = _as_dict(daily_training_brief)
    return {
        "symbol": _clean_text(brief.get("symbol"), fallback="AVGO").upper() or "AVGO",
        "run_date": _clean_text(brief.get("run_date"), fallback="unknown"),
        "overall_status": _clean_text(brief.get("overall_status"), fallback="degraded").lower() or "degraded",
    }


def _headline_cards(
    *,
    daily_training_brief: dict[str, Any],
    active_rule_pool_report: dict[str, Any],
    active_rule_pool_export: dict[str, Any],
    promotion_report: dict[str, Any],
    promotion_adoption_handoff: dict[str, Any],
    drift_report: dict[str, Any],
) -> dict[str, Any]:
    brief_metrics = _as_dict(_as_dict(daily_training_brief).get("headline_metrics"))
    export = _as_dict(active_rule_pool_export)
    active_pool = _as_dict(active_rule_pool_report)
    promotion = _as_dict(promotion_report)
    adoption = _as_dict(promotion_adoption_handoff)
    drift = _as_dict(drift_report)

    exported_rule_count = _safe_int(export.get("exported_rule_count"))
    include_count = _safe_int(_as_dict(active_pool.get("pool_counts")).get("include"))
    has_export_report = bool(export)

    return {
        "active_rule_count": exported_rule_count if has_export_report else include_count,
        "promote_candidate_count": len(_as_list(promotion.get("promote_candidates"))),
        "production_candidate_count": len(_as_list(adoption.get("production_candidates"))),
        "drift_candidate_count": len(_as_list(drift.get("drift_candidates"))),
        "direction_accuracy": _safe_float(brief_metrics.get("direction_accuracy")),
    }


def _active_rules(
    *,
    active_rule_pool_report: dict[str, Any],
    active_rule_pool_export: dict[str, Any],
) -> list[dict[str, Any]]:
    export = _as_dict(active_rule_pool_export)
    if export:
        exported_rules = _as_list(export.get("exported_rules"))
        return [
            {
                "rule_id": _clean_text(rule.get("rule_id") or rule.get("rule_key"), fallback="unknown"),
                "title": _clean_text(rule.get("title"), fallback="unknown"),
                "category": _clean_text(rule.get("category"), fallback="unknown"),
                "severity": _clean_text(rule.get("severity"), fallback="unknown"),
                "effect": _clean_text(rule.get("effect"), fallback="unknown"),
                "notes": _clean_text(rule.get("message") or rule.get("pool_rationale"), fallback=""),
            }
            for raw_rule in exported_rules
            for rule in [_as_dict(raw_rule)]
        ]

    active_pool = _as_dict(active_rule_pool_report)
    rules = _as_list(active_pool.get("rules"))
    fallback_rules: list[dict[str, Any]] = []
    for raw_rule in rules:
        rule = _as_dict(raw_rule)
        if _clean_text(rule.get("pool_decision")).lower() != "include":
            continue
        fallback_rules.append(
            {
                "rule_id": _clean_text(rule.get("rule_id") or rule.get("rule_key"), fallback="unknown"),
                "title": _clean_text(rule.get("title"), fallback="unknown"),
                "category": _clean_text(rule.get("category"), fallback="unknown"),
                "severity": _clean_text(rule.get("severity"), fallback="unknown"),
                "effect": _clean_text(rule.get("effect"), fallback="unknown"),
                "notes": _clean_text(rule.get("pool_rationale"), fallback=""),
            }
        )
    return fallback_rules


def _promotion_candidates(promotion_report: dict[str, Any]) -> list[dict[str, Any]]:
    promotion = _as_dict(promotion_report)
    rules_by_id: dict[str, dict[str, Any]] = {}
    for raw_rule in _as_list(promotion.get("rules")):
        rule = _as_dict(raw_rule)
        rule_id = _clean_text(rule.get("rule_id"), fallback="")
        title = _clean_text(rule.get("title"), fallback="")
        if rule_id:
            rules_by_id[rule_id] = rule
        if title:
            rules_by_id[title] = rule

    candidates: list[dict[str, Any]] = []
    for raw_candidate in _as_list(promotion.get("promote_candidates")):
        candidate = _as_dict(raw_candidate)
        lookup_key = _clean_text(candidate.get("rule_id"), fallback="") or _clean_text(candidate.get("title"), fallback="")
        detail = rules_by_id.get(lookup_key, {})
        candidates.append(
            {
                "rule_id": _clean_text(candidate.get("rule_id") or detail.get("rule_id"), fallback="unknown"),
                "title": _clean_text(candidate.get("title") or detail.get("title"), fallback="unknown"),
                "promotion_confidence": _clean_text(
                    candidate.get("promotion_confidence") or detail.get("promotion_confidence"),
                    fallback="unknown",
                ),
                "notes": _clean_text(
                    candidate.get("notes") or detail.get("notes") or detail.get("promotion_rationale"),
                    fallback="",
                ),
            }
        )
    return candidates


def _production_candidates(promotion_adoption_handoff: dict[str, Any]) -> list[dict[str, Any]]:
    adoption = _as_dict(promotion_adoption_handoff)
    return [
        {
            "rule_id": _clean_text(rule.get("rule_id"), fallback="unknown"),
            "title": _clean_text(rule.get("title"), fallback="unknown"),
            "adoption_confidence": _clean_text(rule.get("adoption_confidence"), fallback="unknown"),
            "notes": _clean_text(rule.get("notes") or rule.get("adoption_rationale"), fallback=""),
        }
        for raw_rule in _as_list(adoption.get("production_candidates"))
        for rule in [_as_dict(raw_rule)]
    ]


def _drift_candidates(drift_report: dict[str, Any]) -> list[dict[str, Any]]:
    drift = _as_dict(drift_report)
    return [
        {
            "rule_id": _clean_text(rule.get("rule_id"), fallback="unknown"),
            "title": _clean_text(rule.get("title"), fallback="unknown"),
            "drift_status": _clean_text(rule.get("drift_status"), fallback="unknown"),
            "recommended_followup": _clean_text(rule.get("recommended_followup"), fallback="keep_monitoring"),
            "notes": _clean_text(rule.get("notes") or rule.get("drift_rationale"), fallback=""),
        }
        for raw_rule in _as_list(drift.get("drift_candidates"))
        for rule in [_as_dict(raw_rule)]
    ]


def _risk_flags(
    *,
    daily_training_brief: dict[str, Any],
    header: dict[str, str],
    headline_cards: dict[str, Any],
) -> list[str]:
    brief = _as_dict(daily_training_brief)
    existing = [flag for flag in _as_list(brief.get("risk_flags")) if _clean_text(flag)]
    if existing:
        return existing

    flags: list[str] = []
    status = header["overall_status"]
    if status in {"degraded", "failed"}:
        flags.append(f"Today overall status is {status}; dashboard conclusions should be read conservatively.")
    if headline_cards["drift_candidate_count"] > 0:
        flags.append(
            f"{headline_cards['drift_candidate_count']} drift candidates need closer monitoring."
        )
    if (
        headline_cards["promote_candidate_count"] > 0
        and headline_cards["production_candidate_count"] == 0
    ):
        flags.append(
            "Promote candidates exist, but none have cleared production candidate review yet."
        )
    return flags


def _summary(*, header: dict[str, str], headline_cards: dict[str, Any], ready: bool) -> str:
    if not ready:
        return (
            "Dashboard inputs are mostly unavailable, so this view is running in fallback mode. "
            "Provide daily brief or rule reports to populate active, promotion, production, and drift monitoring."
        )

    return (
        f"{header['symbol']} dashboard for {header['run_date']}: overall status is {header['overall_status']}. "
        f"Active rules={headline_cards['active_rule_count']}, "
        f"promote candidates={headline_cards['promote_candidate_count']}, "
        f"production candidates={headline_cards['production_candidate_count']}, "
        f"drift candidates={headline_cards['drift_candidate_count']}."
    )


def build_rule_dashboard_view(
    *,
    daily_training_brief: dict | None = None,
    active_rule_pool_report: dict | None = None,
    active_rule_pool_export: dict | None = None,
    promotion_report: dict | None = None,
    promotion_adoption_handoff: dict | None = None,
    drift_report: dict | None = None,
    calibration_report: dict | None = None,
) -> dict[str, Any]:
    dashboard = _empty_dashboard()
    warnings: list[str] = []

    brief = _as_dict(daily_training_brief)
    active_pool = _as_dict(active_rule_pool_report)
    export = _as_dict(active_rule_pool_export)
    promotion = _as_dict(promotion_report)
    adoption = _as_dict(promotion_adoption_handoff)
    drift = _as_dict(drift_report)
    _ = _as_dict(calibration_report)

    if not brief:
        warnings.append("daily_training_brief not provided; dashboard header and risk flags use conservative fallbacks.")

    active_rules = _active_rules(
        active_rule_pool_report=active_pool,
        active_rule_pool_export=export,
    )
    promotion_candidates = _promotion_candidates(promotion)
    production_candidates = _production_candidates(adoption)
    drift_candidates = _drift_candidates(drift)

    if not export and active_pool:
        warnings.append("active_rule_pool_export not provided; active rule count fell back to active_rule_pool_report.")
    if not promotion:
        warnings.append("promotion_report not provided; promotion candidates list is empty.")
    if not adoption:
        warnings.append("promotion_adoption_handoff not provided; production candidates list is empty.")
    if not drift:
        warnings.append("drift_report not provided; drift candidates list is empty.")

    header = _header(brief)
    headline_cards = _headline_cards(
        daily_training_brief=brief,
        active_rule_pool_report=active_pool,
        active_rule_pool_export=export,
        promotion_report=promotion,
        promotion_adoption_handoff=adoption,
        drift_report=drift,
    )
    risk_flags = _risk_flags(
        daily_training_brief=brief,
        header=header,
        headline_cards=headline_cards,
    )

    ready = any(
        (
            bool(brief),
            bool(active_pool),
            bool(export),
            bool(promotion),
            bool(adoption),
            bool(drift),
        )
    )

    dashboard.update(
        {
            "ready": ready,
            "header": header,
            "headline_cards": headline_cards,
            "active_rules": active_rules,
            "promotion_candidates": promotion_candidates,
            "production_candidates": production_candidates,
            "drift_candidates": drift_candidates,
            "risk_flags": risk_flags,
            "summary": _summary(
                header=header,
                headline_cards=headline_cards,
                ready=ready,
            ),
            "warnings": warnings,
        }
    )
    return dashboard


build_monitoring_dashboard_payload = build_rule_dashboard_view
