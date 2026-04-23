"""Tests for services/promotion_adoption_gate.py — Task 066."""

from __future__ import annotations

from services.promotion_adoption_gate import (
    analyze_promotion_adoption_gate,
    build_promotion_adoption_handoff,
)


def _make_promotion_rule(
    rule_id: str = "rule_001",
    title: str = "Rule 001",
    category: str = "momentum",
    promotion_decision: str = "promote_candidate",
    promotion_confidence: str = "high",
    promotion_rationale: str = "Strong promotion signal.",
    hit_count: int = 8,
    net_effect: float = 1.5,
    notes: str = "",
    **kwargs,
) -> dict:
    rule = {
        "rule_id": rule_id,
        "title": title,
        "category": category,
        "promotion_decision": promotion_decision,
        "promotion_confidence": promotion_confidence,
        "promotion_rationale": promotion_rationale,
        "hit_count": hit_count,
        "net_effect": net_effect,
        "notes": notes,
    }
    rule.update(kwargs)
    return rule


def _make_promotion_report(rules: list[dict]) -> dict:
    return {
        "kind": "active_rule_pool_promotion_report",
        "ready": True,
        "rules": rules,
    }


def _make_execution_bridge(rule_ids: list[str]) -> dict:
    return {
        "kind": "promotion_execution_bridge",
        "ready": True,
        "execution_bridge_rules": [
            {
                "rule_id": rule_id,
                "title": f"Bridge {rule_id}",
                "category": "momentum",
                "severity": "medium",
                "message": f"{rule_id} bridge message",
                "effect": "lower_confidence",
            }
            for rule_id in rule_ids
        ],
    }


def _make_calibration_report(rules: list[dict]) -> dict:
    return {
        "kind": "active_rule_pool_calibration_report",
        "ready": True,
        "rules": rules,
    }


def test_happy_path_shape_and_counts():
    rules = [
        _make_promotion_rule(rule_id="r1", promotion_decision="promote_candidate", hit_count=9, net_effect=1.6),
        _make_promotion_rule(rule_id="r2", promotion_decision="promote_candidate", promotion_confidence="low", hit_count=3, net_effect=0.4),
        _make_promotion_rule(rule_id="r3", promotion_decision="keep_active_observe", hit_count=4, net_effect=0.2),
        _make_promotion_rule(rule_id="r4", promotion_decision="do_not_promote", hit_count=6, net_effect=-1.2),
    ]
    report = build_promotion_adoption_handoff(
        promotion_report=_make_promotion_report(rules),
        promotion_execution_bridge=_make_execution_bridge(["r1", "r2"]),
    )

    assert report["kind"] == "promotion_adoption_handoff"
    assert report["ready"] is True
    assert report["total_rules"] == 4
    assert set(report["decision_counts"].keys()) == {
        "production_candidate",
        "keep_in_execution_bridge",
        "hold_for_more_evidence",
        "not_ready_for_adoption",
    }
    assert sum(report["decision_counts"].values()) == 4
    assert len(report["rules"]) == 4
    assert len(report["production_candidates"]) == 1
    assert len(report["execution_bridge_holds"]) == 1
    assert len(report["evidence_holds"]) == 1
    assert len(report["not_ready_rules"]) == 1
    assert len(report["handoff_artifact"]) == 1
    assert isinstance(report["summary"], str) and report["summary"]
    assert isinstance(report["warnings"], list)


def test_strong_promote_candidate_becomes_production_candidate():
    report = build_promotion_adoption_handoff(
        promotion_report=_make_promotion_report(
            [_make_promotion_rule(rule_id="r1", hit_count=7, net_effect=1.2, promotion_confidence="medium")]
        ),
        promotion_execution_bridge=_make_execution_bridge(["r1"]),
    )

    rule = report["rules"][0]
    assert rule["adoption_decision"] == "production_candidate"
    assert rule["adoption_confidence"] in {"medium", "high"}
    assert report["handoff_artifact"][0]["rule_id"] == "r1"


def test_weaker_promote_candidate_stays_in_execution_bridge():
    report = build_promotion_adoption_handoff(
        promotion_report=_make_promotion_report(
            [_make_promotion_rule(rule_id="r2", hit_count=3, net_effect=0.8, promotion_confidence="low")]
        ),
        promotion_execution_bridge=_make_execution_bridge(["r2"]),
    )

    rule = report["rules"][0]
    assert rule["adoption_decision"] == "keep_in_execution_bridge"
    assert report["decision_counts"]["keep_in_execution_bridge"] == 1
    assert report["handoff_artifact"] == []


def test_keep_active_observe_and_hold_back_need_more_evidence():
    report = build_promotion_adoption_handoff(
        promotion_report=_make_promotion_report(
            [
                _make_promotion_rule(rule_id="r3", promotion_decision="keep_active_observe", hit_count=4, net_effect=0.1),
                _make_promotion_rule(rule_id="r4", promotion_decision="hold_back", hit_count=5, net_effect=0.0),
            ]
        )
    )

    assert report["decision_counts"]["hold_for_more_evidence"] == 2
    assert all(rule["adoption_decision"] == "hold_for_more_evidence" for rule in report["rules"])


def test_do_not_promote_and_negative_effect_are_not_ready():
    report = build_promotion_adoption_handoff(
        promotion_report=_make_promotion_report(
            [
                _make_promotion_rule(rule_id="r5", promotion_decision="do_not_promote", net_effect=-0.2),
                _make_promotion_rule(rule_id="r6", promotion_decision="keep_active_observe", net_effect=-0.5),
            ]
        )
    )

    assert report["decision_counts"]["not_ready_for_adoption"] == 2
    assert all(rule["adoption_decision"] == "not_ready_for_adoption" for rule in report["rules"])


def test_adoption_confidence_stays_conservative_without_execution_bridge():
    report = build_promotion_adoption_handoff(
        promotion_report=_make_promotion_report(
            [_make_promotion_rule(rule_id="r7", hit_count=10, net_effect=2.0, promotion_confidence="high")]
        )
    )

    rule = report["rules"][0]
    assert rule["adoption_decision"] == "production_candidate"
    assert rule["adoption_confidence"] == "low"
    assert len(report["warnings"]) > 0


def test_missing_promotion_report_returns_not_ready_with_warning():
    report = build_promotion_adoption_handoff(promotion_report=None)

    assert report["kind"] == "promotion_adoption_handoff"
    assert report["ready"] is False
    assert report["total_rules"] == 0
    assert all(value == 0 for value in report["decision_counts"].values())
    assert report["rules"] == []
    assert len(report["warnings"]) > 0
    assert isinstance(report["summary"], str)


def test_empty_rules_list_is_stable():
    report = build_promotion_adoption_handoff(
        promotion_report=_make_promotion_report([])
    )

    assert report["ready"] is True
    assert report["total_rules"] == 0
    assert all(value == 0 for value in report["decision_counts"].values())
    assert report["rules"] == []
    assert report["handoff_artifact"] == []
    assert isinstance(report["summary"], str) and report["summary"]


def test_malformed_rule_does_not_promote_to_production_candidate():
    report = build_promotion_adoption_handoff(
        promotion_report=_make_promotion_report(
            [
                {
                    "rule_id": "r_bad",
                    "hit_count": 9,
                    "net_effect": 1.4,
                    "promotion_decision": "promote_candidate",
                    "promotion_confidence": "high",
                }
            ]
        ),
        promotion_execution_bridge=_make_execution_bridge(["r_bad"]),
        calibration_report=_make_calibration_report(
            [{"rule_id": "r_bad", "calibration_rationale": "Fallback metadata."}]
        ),
    )

    rule = report["rules"][0]
    assert rule["adoption_decision"] != "production_candidate"
    assert "Fallback metadata." in rule["notes"]


def test_handoff_artifact_only_contains_production_candidates():
    report = build_promotion_adoption_handoff(
        promotion_report=_make_promotion_report(
            [
                _make_promotion_rule(rule_id="r1", hit_count=7, net_effect=1.0, promotion_confidence="high"),
                _make_promotion_rule(rule_id="r2", promotion_decision="hold_back", hit_count=4, net_effect=0.1),
            ]
        ),
        promotion_execution_bridge=_make_execution_bridge(["r1"]),
    )

    assert [item["rule_id"] for item in report["handoff_artifact"]] == ["r1"]
    artifact = report["handoff_artifact"][0]
    assert set(artifact.keys()) == {
        "rule_id",
        "title",
        "category",
        "severity",
        "message",
        "effect",
        "adoption_confidence",
    }


def test_alias_function():
    promotion_report = _make_promotion_report(
        [_make_promotion_rule(rule_id="r1", hit_count=6, net_effect=1.1)]
    )
    bridge = _make_execution_bridge(["r1"])

    first = build_promotion_adoption_handoff(
        promotion_report=promotion_report,
        promotion_execution_bridge=bridge,
    )
    second = analyze_promotion_adoption_gate(
        promotion_report=promotion_report,
        promotion_execution_bridge=bridge,
    )

    assert first["decision_counts"] == second["decision_counts"]
    assert first["handoff_artifact"] == second["handoff_artifact"]
