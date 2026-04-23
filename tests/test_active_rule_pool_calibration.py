from __future__ import annotations

from services.active_rule_pool_calibration import (
    analyze_active_rule_pool_calibration,
    build_active_rule_pool_calibration_report,
)


def _validation_rule(
    *,
    rule_id: str,
    title: str,
    hit_count: int,
    changed_case_count: int,
    improved_case_count: int,
    worsened_case_count: int,
    net_effect: float,
    category: str = "wrong_direction",
    current_severity: str = "unknown",
    current_effect: str = "unknown",
    notes: str = "validation note",
) -> dict:
    return {
        "rule_id": rule_id,
        "title": title,
        "category": category,
        "hit_count": hit_count,
        "changed_case_count": changed_case_count,
        "improved_case_count": improved_case_count,
        "worsened_case_count": worsened_case_count,
        "net_effect": net_effect,
        "current_severity": current_severity,
        "current_effect": current_effect,
        "notes": notes,
    }


class TestActiveRulePoolCalibrationHappyPath:
    def test_report_shape_and_decision_counts(self):
        validation_report = {
            "rule_effects": [
                _validation_rule(
                    rule_id="retain-1",
                    title="保留规则",
                    hit_count=6,
                    changed_case_count=4,
                    improved_case_count=4,
                    worsened_case_count=1,
                    net_effect=3.0,
                    current_severity="medium",
                    current_effect="lower_confidence",
                ),
                _validation_rule(
                    rule_id="observe-1",
                    title="观察规则",
                    hit_count=2,
                    changed_case_count=1,
                    improved_case_count=1,
                    worsened_case_count=1,
                    net_effect=0.0,
                ),
                _validation_rule(
                    rule_id="recal-1",
                    title="校准规则",
                    hit_count=6,
                    changed_case_count=5,
                    improved_case_count=4,
                    worsened_case_count=1,
                    net_effect=3.0,
                    current_severity="low",
                    current_effect="warn",
                ),
                _validation_rule(
                    rule_id="remove-1",
                    title="移除候选规则",
                    hit_count=6,
                    changed_case_count=5,
                    improved_case_count=1,
                    worsened_case_count=3,
                    net_effect=-2.0,
                    current_severity="high",
                    current_effect="raise_risk",
                ),
            ]
        }

        report = build_active_rule_pool_calibration_report(validation_report=validation_report)

        assert report["kind"] == "active_rule_pool_calibration_report"
        assert report["ready"] is True
        assert report["total_active_rules"] == 4
        assert report["decision_counts"] == {
            "retain": 1,
            "downgrade": 0,
            "recalibrate": 1,
            "remove_candidate": 1,
            "observe": 1,
        }
        assert report["summary"]
        assert report["warnings"] == []


class TestActiveRulePoolCalibrationDecisions:
    def test_positive_net_effect_becomes_retain(self):
        report = build_active_rule_pool_calibration_report(
            validation_report={
                "rule_effects": [
                    _validation_rule(
                        rule_id="retain-1",
                        title="保留规则",
                        hit_count=5,
                        changed_case_count=4,
                        improved_case_count=3,
                        worsened_case_count=1,
                        net_effect=2.0,
                        current_severity="medium",
                        current_effect="lower_confidence",
                    )
                ]
            }
        )

        rule = report["rules"][0]
        assert rule["calibration_decision"] == "retain"
        assert "保留" in rule["rationale"]

    def test_borderline_rule_becomes_observe(self):
        report = build_active_rule_pool_calibration_report(
            validation_report={
                "rule_effects": [
                    _validation_rule(
                        rule_id="observe-1",
                        title="观察规则",
                        hit_count=2,
                        changed_case_count=1,
                        improved_case_count=0,
                        worsened_case_count=0,
                        net_effect=0.0,
                    )
                ]
            }
        )

        assert report["rules"][0]["calibration_decision"] == "observe"

    def test_changed_lot_but_little_gain_becomes_downgrade(self):
        report = build_active_rule_pool_calibration_report(
            validation_report={
                "rule_effects": [
                    _validation_rule(
                        rule_id="down-1",
                        title="降级规则",
                        hit_count=5,
                        changed_case_count=5,
                        improved_case_count=1,
                        worsened_case_count=1,
                        net_effect=0.0,
                        current_severity="unknown",
                        current_effect="unknown",
                    )
                ]
            }
        )

        assert report["rules"][0]["calibration_decision"] == "downgrade"

    def test_recalibrate_suggests_non_empty_severity_and_effect(self):
        report = analyze_active_rule_pool_calibration(
            validation_report={
                "rule_effects": [
                    _validation_rule(
                        rule_id="recal-1",
                        title="校准规则",
                        hit_count=6,
                        changed_case_count=5,
                        improved_case_count=4,
                        worsened_case_count=1,
                        net_effect=3.0,
                        current_severity="low",
                        current_effect="warn",
                    )
                ]
            }
        )

        rule = report["rules"][0]
        assert rule["calibration_decision"] == "recalibrate"
        assert rule["suggested_severity"] == "medium"
        assert rule["suggested_effect"] == "lower_confidence"

    def test_positive_rule_with_unknown_current_params_does_not_force_recalibrate(self):
        report = build_active_rule_pool_calibration_report(
            validation_report={
                "rule_effects": [
                    _validation_rule(
                        rule_id="retain-unknown-1",
                        title="缺参正向规则",
                        hit_count=6,
                        changed_case_count=5,
                        improved_case_count=4,
                        worsened_case_count=1,
                        net_effect=3.0,
                        current_severity="unknown",
                        current_effect="unknown",
                    )
                ]
            }
        )

        rule = report["rules"][0]
        assert rule["calibration_decision"] != "recalibrate"
        assert rule["calibration_decision"] == "retain"
        assert rule["suggested_severity"] == "unknown"
        assert rule["suggested_effect"] == "unknown"

    def test_negative_net_effect_becomes_remove_candidate(self):
        report = build_active_rule_pool_calibration_report(
            validation_report={
                "rule_effects": [
                    _validation_rule(
                        rule_id="remove-1",
                        title="移除候选规则",
                        hit_count=5,
                        changed_case_count=4,
                        improved_case_count=1,
                        worsened_case_count=2,
                        net_effect=-1.0,
                        current_severity="high",
                        current_effect="raise_risk",
                    )
                ]
            }
        )

        assert report["rules"][0]["calibration_decision"] == "remove_candidate"


class TestActiveRulePoolCalibrationDegraded:
    def test_missing_validation_report_degrades_cleanly(self):
        report = build_active_rule_pool_calibration_report(validation_report=None)

        assert report["ready"] is False
        assert report["warnings"]
        assert report["total_active_rules"] == 0

    def test_empty_rules_returns_readable_empty_state(self):
        report = build_active_rule_pool_calibration_report(validation_report={"rule_effects": []})

        assert report["ready"] is True
        assert report["total_active_rules"] == 0
        assert report["decision_counts"] == {
            "retain": 0,
            "downgrade": 0,
            "recalibrate": 0,
            "remove_candidate": 0,
            "observe": 0,
        }
        assert report["summary"]
        assert report["warnings"]

    def test_incomplete_rule_is_handled_conservatively(self):
        report = build_active_rule_pool_calibration_report(
            validation_report={
                "rule_effects": [
                    {
                        "title": "",
                        "hit_count": "not-a-number",
                        "changed_case_count": None,
                    }
                ]
            }
        )

        assert report["ready"] is True
        assert report["rules"][0]["calibration_decision"] == "observe"
        assert report["rules"][0]["suggested_severity"] == "unknown"
        assert report["rules"][0]["suggested_effect"] == "unknown"
        assert report["warnings"]


class TestActiveRulePoolCalibrationGrouping:
    def test_grouped_lists_match_decisions(self):
        report = build_active_rule_pool_calibration_report(
            validation_report={
                "rule_effects": [
                    _validation_rule(
                        rule_id="retain-1",
                        title="保留规则",
                        hit_count=5,
                        changed_case_count=4,
                        improved_case_count=3,
                        worsened_case_count=1,
                        net_effect=2.0,
                        current_severity="medium",
                        current_effect="lower_confidence",
                    ),
                    _validation_rule(
                        rule_id="observe-1",
                        title="观察规则",
                        hit_count=2,
                        changed_case_count=1,
                        improved_case_count=0,
                        worsened_case_count=0,
                        net_effect=0.0,
                    ),
                    _validation_rule(
                        rule_id="down-1",
                        title="降级规则",
                        hit_count=5,
                        changed_case_count=5,
                        improved_case_count=1,
                        worsened_case_count=1,
                        net_effect=0.0,
                    ),
                    _validation_rule(
                        rule_id="recal-1",
                        title="校准规则",
                        hit_count=6,
                        changed_case_count=5,
                        improved_case_count=4,
                        worsened_case_count=1,
                        net_effect=3.0,
                        current_severity="low",
                        current_effect="warn",
                    ),
                    _validation_rule(
                        rule_id="remove-1",
                        title="移除候选规则",
                        hit_count=5,
                        changed_case_count=4,
                        improved_case_count=1,
                        worsened_case_count=2,
                        net_effect=-1.0,
                        current_severity="high",
                        current_effect="raise_risk",
                    ),
                ]
            }
        )

        assert [row["rule_id"] for row in report["retain_rules"]] == ["retain-1"]
        assert [row["rule_id"] for row in report["downgrade_rules"]] == ["down-1"]
        assert [row["rule_id"] for row in report["recalibrate_rules"]] == ["recal-1"]
        assert [row["rule_id"] for row in report["remove_candidates"]] == ["remove-1"]
        assert [row["rule_id"] for row in report["observe_rules"]] == ["observe-1"]
