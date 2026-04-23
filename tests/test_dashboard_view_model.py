from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.dashboard_view_model import (
    build_monitoring_dashboard_payload,
    build_rule_dashboard_view,
)


def _daily_brief(*, risk_flags: list[str] | None = None, overall_status: str = "healthy") -> dict:
    return {
        "kind": "daily_training_brief",
        "ready": True,
        "symbol": "AVGO",
        "run_date": "2026-04-22",
        "overall_status": overall_status,
        "headline_metrics": {
            "direction_accuracy": 0.625,
        },
        "risk_flags": risk_flags if risk_flags is not None else ["brief risk"],
    }


def _active_rule_pool_report() -> dict:
    return {
        "kind": "active_rule_pool_report",
        "ready": True,
        "pool_counts": {
            "include": 2,
            "hold": 1,
            "exclude": 0,
        },
        "rules": [
            {
                "rule_key": "arp-1",
                "title": "Active Rule A",
                "category": "momentum",
                "pool_decision": "include",
                "pool_rationale": "Strong active candidate.",
            },
            {
                "rule_key": "arp-2",
                "title": "Hold Rule",
                "category": "risk",
                "pool_decision": "hold",
                "pool_rationale": "Needs more evidence.",
            },
        ],
    }


def _active_rule_pool_export() -> dict:
    return {
        "kind": "active_rule_pool_export",
        "ready": True,
        "exported_rule_count": 2,
        "exported_rules": [
            {
                "rule_key": "arp-1",
                "title": "Active Rule A",
                "category": "momentum",
                "severity": "medium",
                "message": "Exported note A",
                "effect": "lower_confidence",
            },
            {
                "rule_key": "arp-3",
                "title": "Active Rule B",
                "category": "trend",
                "severity": "low",
                "message": "Exported note B",
                "effect": "warn",
            },
        ],
    }


def _promotion_report() -> dict:
    return {
        "kind": "active_rule_pool_promotion_report",
        "promote_candidates": [
            {
                "rule_id": "promo-1",
                "title": "Promo Rule",
                "promotion_confidence": "high",
                "notes": "promo note",
            }
        ],
        "rules": [
            {
                "rule_id": "promo-1",
                "title": "Promo Rule",
                "promotion_confidence": "high",
                "promotion_rationale": "promotion rationale",
                "notes": "promo note",
            }
        ],
    }


def _adoption_handoff() -> dict:
    return {
        "kind": "promotion_adoption_handoff",
        "production_candidates": [
            {
                "rule_id": "prod-1",
                "title": "Production Rule",
                "adoption_confidence": "medium",
                "notes": "adoption note",
                "adoption_rationale": "adoption rationale",
            }
        ],
    }


def _drift_report() -> dict:
    return {
        "kind": "active_rule_pool_drift_report",
        "drift_candidates": [
            {
                "rule_id": "drift-1",
                "title": "Drift Rule",
                "drift_status": "drift_candidate",
                "recommended_followup": "review_for_downgrade",
                "notes": "drift note",
            }
        ],
    }


class DashboardViewModelHappyPathTests(unittest.TestCase):
    def test_complete_inputs_return_stable_dashboard_shape(self) -> None:
        dashboard = build_rule_dashboard_view(
            daily_training_brief=_daily_brief(),
            active_rule_pool_report=_active_rule_pool_report(),
            active_rule_pool_export=_active_rule_pool_export(),
            promotion_report=_promotion_report(),
            promotion_adoption_handoff=_adoption_handoff(),
            drift_report=_drift_report(),
        )

        self.assertEqual(dashboard["kind"], "rule_dashboard_view")
        self.assertTrue(dashboard["ready"])
        self.assertEqual(dashboard["header"], {
            "symbol": "AVGO",
            "run_date": "2026-04-22",
            "overall_status": "healthy",
        })
        self.assertEqual(dashboard["headline_cards"]["active_rule_count"], 2)
        self.assertEqual(dashboard["headline_cards"]["promote_candidate_count"], 1)
        self.assertEqual(dashboard["headline_cards"]["production_candidate_count"], 1)
        self.assertEqual(dashboard["headline_cards"]["drift_candidate_count"], 1)
        self.assertEqual(dashboard["headline_cards"]["direction_accuracy"], 0.625)
        self.assertEqual(len(dashboard["active_rules"]), 2)
        self.assertEqual(len(dashboard["promotion_candidates"]), 1)
        self.assertEqual(len(dashboard["production_candidates"]), 1)
        self.assertEqual(len(dashboard["drift_candidates"]), 1)
        self.assertEqual(dashboard["risk_flags"], ["brief risk"])
        self.assertTrue(dashboard["summary"])

    def test_alias_matches_main_entrypoint(self) -> None:
        dashboard = build_monitoring_dashboard_payload(
            daily_training_brief=_daily_brief(),
            active_rule_pool_export=_active_rule_pool_export(),
        )
        self.assertEqual(dashboard["kind"], "rule_dashboard_view")


class DashboardViewModelFallbackTests(unittest.TestCase):
    def test_missing_daily_training_brief_keeps_dashboard_stable(self) -> None:
        dashboard = build_rule_dashboard_view(
            active_rule_pool_export=_active_rule_pool_export(),
            promotion_report=_promotion_report(),
        )

        self.assertTrue(dashboard["ready"])
        self.assertEqual(dashboard["header"]["symbol"], "AVGO")
        self.assertEqual(dashboard["header"]["run_date"], "unknown")
        self.assertEqual(dashboard["header"]["overall_status"], "degraded")
        self.assertTrue(dashboard["warnings"])

    def test_missing_export_falls_back_to_active_pool_report(self) -> None:
        dashboard = build_rule_dashboard_view(
            daily_training_brief=_daily_brief(),
            active_rule_pool_report=_active_rule_pool_report(),
        )

        self.assertEqual(dashboard["headline_cards"]["active_rule_count"], 2)
        self.assertEqual(len(dashboard["active_rules"]), 1)
        self.assertEqual(dashboard["active_rules"][0]["title"], "Active Rule A")

    def test_explicit_export_count_zero_does_not_fall_back_to_pool_include_count(self) -> None:
        dashboard = build_rule_dashboard_view(
            daily_training_brief=_daily_brief(),
            active_rule_pool_report=_active_rule_pool_report(),
            active_rule_pool_export={
                "kind": "active_rule_pool_export",
                "ready": True,
                "exported_rule_count": 0,
                "exported_rules": [],
            },
        )

        self.assertEqual(dashboard["headline_cards"]["active_rule_count"], 0)

    def test_explicit_empty_export_rules_do_not_fall_back_to_pool_include_rules(self) -> None:
        dashboard = build_rule_dashboard_view(
            daily_training_brief=_daily_brief(),
            active_rule_pool_report=_active_rule_pool_report(),
            active_rule_pool_export={
                "kind": "active_rule_pool_export",
                "ready": True,
                "exported_rule_count": 0,
                "exported_rules": [],
            },
        )

        self.assertEqual(dashboard["active_rules"], [])

    def test_missing_promotion_adoption_and_drift_keep_lists_empty(self) -> None:
        dashboard = build_rule_dashboard_view(
            daily_training_brief=_daily_brief(),
            active_rule_pool_export=_active_rule_pool_export(),
        )

        self.assertEqual(dashboard["promotion_candidates"], [])
        self.assertEqual(dashboard["production_candidates"], [])
        self.assertEqual(dashboard["drift_candidates"], [])
        self.assertTrue(dashboard["warnings"])


class DashboardViewModelRiskTests(unittest.TestCase):
    def test_dashboard_reuses_brief_risk_flags(self) -> None:
        dashboard = build_rule_dashboard_view(
            daily_training_brief=_daily_brief(risk_flags=["reuse this risk"]),
        )
        self.assertEqual(dashboard["risk_flags"], ["reuse this risk"])

    def test_dashboard_generates_basic_risk_flags_without_brief_flags(self) -> None:
        dashboard = build_rule_dashboard_view(
            daily_training_brief=_daily_brief(risk_flags=[], overall_status="degraded"),
            promotion_report=_promotion_report(),
            drift_report=_drift_report(),
        )

        self.assertTrue(any("overall status is degraded" in flag for flag in dashboard["risk_flags"]))
        self.assertTrue(any("drift candidates" in flag for flag in dashboard["risk_flags"]))
        self.assertTrue(any("none have cleared production candidate review" in flag for flag in dashboard["risk_flags"]))


class DashboardViewModelDegradedTests(unittest.TestCase):
    def test_all_inputs_missing_returns_ready_false_with_readable_summary(self) -> None:
        dashboard = build_rule_dashboard_view()

        self.assertFalse(dashboard["ready"])
        self.assertEqual(dashboard["kind"], "rule_dashboard_view")
        self.assertEqual(dashboard["headline_cards"]["active_rule_count"], 0)
        self.assertEqual(dashboard["active_rules"], [])
        self.assertTrue(dashboard["warnings"])
        self.assertIn("fallback mode", dashboard["summary"])


class DashboardViewModelSummaryTests(unittest.TestCase):
    def test_summary_reflects_active_promote_production_drift_and_status(self) -> None:
        dashboard = build_rule_dashboard_view(
            daily_training_brief=_daily_brief(risk_flags=[], overall_status="mixed"),
            active_rule_pool_export=_active_rule_pool_export(),
            promotion_report=_promotion_report(),
            promotion_adoption_handoff=_adoption_handoff(),
            drift_report=_drift_report(),
        )

        self.assertIn("overall status is mixed", dashboard["summary"])
        self.assertIn("Active rules=2", dashboard["summary"])
        self.assertIn("promote candidates=1", dashboard["summary"])
        self.assertIn("production candidates=1", dashboard["summary"])
        self.assertIn("drift candidates=1", dashboard["summary"])


if __name__ == "__main__":
    unittest.main()
