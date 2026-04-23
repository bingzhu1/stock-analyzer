from __future__ import annotations

from services.active_rule_pool_validation import (
    analyze_active_rule_pool_effectiveness,
    build_active_rule_pool_validation_report,
)


def _result(
    *,
    as_of_date: str,
    prediction_for_date: str,
    direction_correct,
    final_direction: str = "偏多",
    final_confidence: str = "medium",
    risk_level: str = "medium",
    active_pool_used: bool = False,
    matched_rules: list[dict] | None = None,
    active_pool_matches: int = 0,
) -> dict:
    return {
        "ready": True,
        "as_of_date": as_of_date,
        "prediction_for_date": prediction_for_date,
        "projection_snapshot": {
            "analysis_date": as_of_date,
            "prediction_for_date": prediction_for_date,
            "final_decision": {
                "final_direction": final_direction,
                "final_confidence": final_confidence,
                "risk_level": risk_level,
            },
            "preflight": {
                "kind": "projection_rule_preflight",
                "matched_rules": matched_rules or [],
                "active_pool_used": active_pool_used,
                "source_counts": {
                    "active_pool_matches": active_pool_matches,
                },
            },
        },
        "review": {
            "direction_correct": direction_correct,
        },
    }


def _active_rule(
    rule_id: str,
    title: str,
    *,
    sources: list[str] | None = None,
) -> dict:
    return {
        "rule_id": rule_id,
        "title": title,
        "category": "wrong_direction",
        "severity": "medium",
        "message": f"{title} 命中",
        "sources": sources or ["active_pool"],
    }


class TestActiveRulePoolValidationHappyPath:
    def test_report_shape_and_accuracy_delta(self):
        baseline = [
            _result(
                as_of_date="2026-04-01",
                prediction_for_date="2026-04-02",
                direction_correct=False,
                final_confidence="high",
                risk_level="low",
            ),
            _result(
                as_of_date="2026-04-02",
                prediction_for_date="2026-04-03",
                direction_correct=True,
                final_confidence="medium",
                risk_level="medium",
            ),
            _result(
                as_of_date="2026-04-03",
                prediction_for_date="2026-04-04",
                direction_correct=True,
                final_confidence="low",
                risk_level="high",
            ),
        ]
        active = [
            _result(
                as_of_date="2026-04-01",
                prediction_for_date="2026-04-02",
                direction_correct=True,
                final_confidence="medium",
                risk_level="medium",
                active_pool_used=True,
                matched_rules=[_active_rule("rule-help", "规则A")],
                active_pool_matches=1,
            ),
            _result(
                as_of_date="2026-04-02",
                prediction_for_date="2026-04-03",
                direction_correct=False,
                final_confidence="low",
                risk_level="high",
                active_pool_used=True,
                matched_rules=[_active_rule("rule-bad", "规则B")],
                active_pool_matches=1,
            ),
            _result(
                as_of_date="2026-04-03",
                prediction_for_date="2026-04-04",
                direction_correct=True,
                final_confidence="low",
                risk_level="high",
                active_pool_used=False,
                matched_rules=[],
                active_pool_matches=0,
            ),
        ]

        report = build_active_rule_pool_validation_report(
            baseline_results=baseline,
            active_pool_results=active,
        )

        assert report["kind"] == "active_rule_pool_validation_report"
        assert report["ready"] is True
        assert report["comparable_cases"] == 3
        assert report["baseline_accuracy"] == 0.6667
        assert report["active_pool_accuracy"] == 0.6667
        assert report["accuracy_delta"] == 0.0
        assert report["baseline_confidence_distribution"] == {
            "high": 1,
            "medium": 1,
            "low": 1,
            "unknown": 0,
        }
        assert report["active_pool_confidence_distribution"] == {
            "high": 0,
            "medium": 1,
            "low": 2,
            "unknown": 0,
        }
        assert report["baseline_risk_distribution"] == {
            "low": 1,
            "medium": 1,
            "high": 1,
            "unknown": 0,
        }
        assert report["active_pool_risk_distribution"] == {
            "low": 0,
            "medium": 1,
            "high": 2,
            "unknown": 0,
        }
        assert report["changed_cases"] == 2
        assert report["improved_cases"] == 1
        assert report["worsened_cases"] == 1
        assert report["neutral_cases"] == 1
        assert report["summary"]
        assert report["warnings"] == []

    def test_improved_worsened_and_neutral_semantics(self):
        baseline = [
            _result(as_of_date="2026-04-01", prediction_for_date="2026-04-02", direction_correct=False),
            _result(as_of_date="2026-04-02", prediction_for_date="2026-04-03", direction_correct=True),
            _result(as_of_date="2026-04-03", prediction_for_date="2026-04-04", direction_correct=True),
        ]
        active = [
            _result(
                as_of_date="2026-04-01",
                prediction_for_date="2026-04-02",
                direction_correct=True,
                active_pool_used=True,
                matched_rules=[_active_rule("rule-help", "规则A")],
                active_pool_matches=1,
            ),
            _result(
                as_of_date="2026-04-02",
                prediction_for_date="2026-04-03",
                direction_correct=False,
                active_pool_used=True,
                matched_rules=[_active_rule("rule-bad", "规则B")],
                active_pool_matches=1,
            ),
            _result(
                as_of_date="2026-04-03",
                prediction_for_date="2026-04-04",
                direction_correct=True,
                active_pool_used=False,
            ),
        ]

        report = build_active_rule_pool_validation_report(
            baseline_results=baseline,
            active_pool_results=active,
        )

        assert report["improved_cases"] == 1
        assert report["worsened_cases"] == 1
        assert report["neutral_cases"] == 1


class TestActiveRulePoolValidationRuleEffects:
    def test_rule_effects_and_top_lists_follow_statistics(self):
        baseline = [
            _result(as_of_date="2026-04-01", prediction_for_date="2026-04-02", direction_correct=False),
            _result(as_of_date="2026-04-02", prediction_for_date="2026-04-03", direction_correct=False),
            _result(as_of_date="2026-04-03", prediction_for_date="2026-04-04", direction_correct=True),
        ]
        active = [
            _result(
                as_of_date="2026-04-01",
                prediction_for_date="2026-04-02",
                direction_correct=True,
                active_pool_used=True,
                matched_rules=[_active_rule("rule-help", "规则A")],
                active_pool_matches=1,
            ),
            _result(
                as_of_date="2026-04-02",
                prediction_for_date="2026-04-03",
                direction_correct=True,
                active_pool_used=True,
                matched_rules=[_active_rule("rule-help", "规则A")],
                active_pool_matches=1,
            ),
            _result(
                as_of_date="2026-04-03",
                prediction_for_date="2026-04-04",
                direction_correct=False,
                active_pool_used=True,
                matched_rules=[_active_rule("rule-bad", "规则B", sources=["memory", "active_pool"])],
                active_pool_matches=1,
            ),
        ]

        report = analyze_active_rule_pool_effectiveness(
            baseline_results=baseline,
            active_pool_results=active,
        )

        rule_effects = {item["rule_id"]: item for item in report["rule_effects"]}
        assert rule_effects["rule-help"]["hit_count"] == 2
        assert rule_effects["rule-help"]["changed_case_count"] == 2
        assert rule_effects["rule-help"]["improved_case_count"] == 2
        assert rule_effects["rule-help"]["worsened_case_count"] == 0
        assert rule_effects["rule-help"]["net_effect"] == 2.0
        assert rule_effects["rule-bad"]["hit_count"] == 1
        assert rule_effects["rule-bad"]["improved_case_count"] == 0
        assert rule_effects["rule-bad"]["worsened_case_count"] == 1
        assert rule_effects["rule-bad"]["net_effect"] == -1.0
        assert report["top_helpful_rules"][0]["rule_id"] == "rule-help"
        assert report["top_unhelpful_rules"][0]["rule_id"] == "rule-bad"


class TestActiveRulePoolValidationDegraded:
    def test_missing_baseline_results_degrades_cleanly(self):
        report = build_active_rule_pool_validation_report(
            baseline_results=None,
            active_pool_results=[],
        )

        assert report["ready"] is False
        assert report["warnings"]
        assert report["comparable_cases"] == 0
        assert report["summary"]

    def test_missing_active_results_degrades_cleanly(self):
        report = build_active_rule_pool_validation_report(
            baseline_results=[],
            active_pool_results=None,
        )

        assert report["ready"] is False
        assert report["warnings"]
        assert report["comparable_cases"] == 0
        assert report["summary"]

    def test_unaligned_cases_return_readable_empty_comparison(self):
        baseline = [
            _result(as_of_date="2026-04-01", prediction_for_date="2026-04-02", direction_correct=True),
        ]
        active = [
            _result(as_of_date="2026-04-09", prediction_for_date="2026-04-10", direction_correct=True),
        ]

        report = build_active_rule_pool_validation_report(
            baseline_results=baseline,
            active_pool_results=active,
        )

        assert report["ready"] is True
        assert report["comparable_cases"] == 0
        assert report["warnings"]
        assert report["summary"]

    def test_partial_missing_fields_do_not_break_report(self):
        baseline = [
            {
                "as_of_date": "2026-04-01",
                "prediction_for_date": "2026-04-02",
                "review": {"direction_correct": None},
            },
        ]
        active = [
            {
                "as_of_date": "2026-04-01",
                "prediction_for_date": "2026-04-02",
                "projection_snapshot": {
                    "preflight": {
                        "matched_rules": [{"rule_id": "rule-x", "sources": ["active_pool"]}],
                        "active_pool_used": True,
                        "source_counts": {"active_pool_matches": 1},
                    },
                },
                "review": {},
            },
        ]

        report = build_active_rule_pool_validation_report(
            baseline_results=baseline,
            active_pool_results=active,
        )

        assert report["ready"] is True
        assert report["comparable_cases"] == 1
        assert report["baseline_accuracy"] is None
        assert report["active_pool_accuracy"] is None
        assert report["rule_effects"][0]["rule_id"] == "rule-x"
