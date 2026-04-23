from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.automation_wrapper import (
    run_daily_automation,
    run_scheduled_training_cycle,
)


def _daily_training_report() -> dict:
    return {
        "kind": "daily_training_report",
        "ready": True,
        "symbol": "AVGO",
        "run_date": "2026-04-22",
        "step_status": {
            "replay": "ok",
            "rule_scoring": "ok",
            "rule_lifecycle": "ok",
            "active_pool": "ok",
            "active_pool_export": "ok",
            "validation": "ok",
            "calibration": "ok",
            "promotion": "ok",
            "drift": "ok",
        },
        "artifacts": {
            "active_rule_pool_report": {
                "kind": "active_rule_pool_report",
                "pool_counts": {"include": 2, "hold": 0, "exclude": 0},
            },
            "active_rule_pool_export": {
                "kind": "active_rule_pool_export",
                "exported_rule_count": 2,
                "exported_rules": [{"rule_key": "arp-1"}],
            },
            "active_rule_pool_calibration_report": {
                "kind": "active_rule_pool_calibration_report",
                "rules": [],
            },
            "active_rule_pool_promotion_report": {
                "kind": "active_rule_pool_promotion_report",
                "promote_candidates": [{"rule_id": "promo-1"}],
            },
            "active_rule_pool_drift_report": {
                "kind": "active_rule_pool_drift_report",
                "drift_candidates": [{"rule_id": "drift-1"}],
            },
        },
        "headline_metrics": {
            "direction_accuracy": 0.625,
            "active_rule_count": 2,
            "promote_candidate_count": 1,
            "drift_candidate_count": 1,
        },
        "warnings": [],
    }


def _daily_training_brief() -> dict:
    return {
        "kind": "daily_training_brief",
        "ready": True,
        "symbol": "AVGO",
        "run_date": "2026-04-22",
        "overall_status": "healthy",
        "headline_metrics": {
            "direction_accuracy": 0.625,
            "active_rule_count": 2,
            "promote_candidate_count": 1,
            "drift_candidate_count": 1,
        },
        "warnings": [],
    }


def _dashboard_view() -> dict:
    return {
        "kind": "rule_dashboard_view",
        "ready": True,
        "header": {
            "symbol": "AVGO",
            "run_date": "2026-04-22",
            "overall_status": "healthy",
        },
        "headline_cards": {
            "active_rule_count": 2,
            "promote_candidate_count": 1,
            "production_candidate_count": 1,
            "drift_candidate_count": 1,
            "direction_accuracy": 0.625,
        },
        "warnings": [],
    }


class AutomationWrapperHappyPathTests(unittest.TestCase):
    def test_direct_artifacts_produce_stable_automation_run(self) -> None:
        run = run_daily_automation(
            daily_training_report=_daily_training_report(),
            daily_training_brief=_daily_training_brief(),
            dashboard_view=_dashboard_view(),
            symbol="avgo",
            run_date="2026-04-22",
        )

        self.assertEqual(run["kind"], "daily_automation_run")
        self.assertTrue(run["ready"])
        self.assertEqual(run["symbol"], "AVGO")
        self.assertEqual(run["run_date"], "2026-04-22")
        self.assertEqual(run["run_status"], "ok")
        self.assertEqual(run["step_status"], {
            "pipeline": "ok",
            "summary": "ok",
            "dashboard": "ok",
        })
        self.assertEqual(run["headline"]["overall_status"], "healthy")
        self.assertEqual(run["headline"]["direction_accuracy"], 0.625)
        self.assertEqual(run["headline"]["active_rule_count"], 2)
        self.assertEqual(run["headline"]["promote_candidate_count"], 1)
        self.assertEqual(run["headline"]["production_candidate_count"], 1)
        self.assertEqual(run["headline"]["drift_candidate_count"], 1)
        self.assertTrue(run["summary"])

    def test_alias_matches_main_entrypoint(self) -> None:
        self.assertEqual(
            run_scheduled_training_cycle(
                daily_training_report=_daily_training_report(),
            )["kind"],
            "daily_automation_run",
        )


class AutomationWrapperBuilderChainTests(unittest.TestCase):
    def test_injected_builders_run_in_order(self) -> None:
        call_log: list[str] = []

        def _pipeline_runner(**kwargs) -> dict:
            call_log.append("pipeline")
            self.assertEqual(kwargs["symbol"], "AVGO")
            return _daily_training_report()

        def _summary_builder(*, daily_training_report=None, **kwargs) -> dict:
            call_log.append("summary")
            self.assertIsNotNone(daily_training_report)
            return _daily_training_brief()

        def _dashboard_builder(*, daily_training_brief=None, promotion_report=None, **kwargs) -> dict:
            call_log.append("dashboard")
            self.assertIsNotNone(daily_training_brief)
            self.assertIsNotNone(promotion_report)
            return _dashboard_view()

        run = run_daily_automation(
            _pipeline_runner=_pipeline_runner,
            _summary_builder=_summary_builder,
            _dashboard_builder=_dashboard_builder,
            symbol="AVGO",
            run_date="2026-04-22",
        )

        self.assertEqual(call_log, ["pipeline", "summary", "dashboard"])
        self.assertEqual(run["run_status"], "ok")
        self.assertTrue(all(status == "ok" for status in run["step_status"].values()))


class AutomationWrapperPartialTests(unittest.TestCase):
    def test_pipeline_success_but_summary_missing_marks_partial(self) -> None:
        run = run_daily_automation(
            daily_training_report=_daily_training_report(),
            dashboard_view=_dashboard_view(),
        )

        self.assertTrue(run["ready"])
        self.assertEqual(run["step_status"]["pipeline"], "ok")
        self.assertEqual(run["step_status"]["summary"], "skipped")
        self.assertEqual(run["step_status"]["dashboard"], "ok")
        self.assertEqual(run["run_status"], "partial")
        self.assertIsNotNone(run["artifacts"]["daily_training_report"])

    def test_dashboard_builder_exception_keeps_other_artifacts(self) -> None:
        def _boom(**kwargs) -> dict:
            raise RuntimeError("dashboard broke")

        run = run_daily_automation(
            daily_training_report=_daily_training_report(),
            daily_training_brief=_daily_training_brief(),
            _dashboard_builder=_boom,
        )

        self.assertEqual(run["step_status"]["pipeline"], "ok")
        self.assertEqual(run["step_status"]["summary"], "ok")
        self.assertEqual(run["step_status"]["dashboard"], "failed")
        self.assertEqual(run["run_status"], "partial")
        self.assertTrue(any("dashboard: builder execution failed" in warning for warning in run["warnings"]))


class AutomationWrapperFailureTests(unittest.TestCase):
    def test_missing_pipeline_input_and_runner_fails_run(self) -> None:
        run = run_daily_automation()

        self.assertFalse(run["ready"])
        self.assertEqual(run["step_status"]["pipeline"], "failed")
        self.assertEqual(run["run_status"], "failed")
        self.assertTrue(run["warnings"])


class AutomationWrapperHeadlineFallbackTests(unittest.TestCase):
    def test_brief_missing_uses_dashboard_and_report_for_headline(self) -> None:
        run = run_daily_automation(
            daily_training_report=_daily_training_report(),
            dashboard_view=_dashboard_view(),
        )

        self.assertEqual(run["headline"]["overall_status"], "healthy")
        self.assertEqual(run["headline"]["direction_accuracy"], 0.625)
        self.assertEqual(run["headline"]["active_rule_count"], 2)
        self.assertEqual(run["headline"]["production_candidate_count"], 1)

    def test_dashboard_missing_does_not_block_headline_from_brief(self) -> None:
        run = run_daily_automation(
            daily_training_report=_daily_training_report(),
            daily_training_brief=_daily_training_brief(),
        )

        self.assertEqual(run["headline"]["overall_status"], "healthy")
        self.assertEqual(run["headline"]["direction_accuracy"], 0.625)
        self.assertEqual(run["headline"]["active_rule_count"], 2)
        self.assertEqual(run["headline"]["promote_candidate_count"], 1)
        self.assertEqual(run["headline"]["production_candidate_count"], 0)

    def test_brief_zero_active_rule_count_overrides_nonzero_dashboard_and_report(self) -> None:
        report = _daily_training_report()
        dashboard = _dashboard_view()
        brief = _daily_training_brief()
        brief["headline_metrics"]["active_rule_count"] = 0

        run = run_daily_automation(
            daily_training_report=report,
            daily_training_brief=brief,
            dashboard_view=dashboard,
        )

        self.assertEqual(run["headline"]["active_rule_count"], 0)

    def test_dashboard_zero_production_candidate_count_overrides_report_fallback(self) -> None:
        dashboard = _dashboard_view()
        dashboard["headline_cards"]["production_candidate_count"] = 0

        run = run_daily_automation(
            daily_training_report=_daily_training_report(),
            dashboard_view=dashboard,
        )

        self.assertEqual(run["headline"]["production_candidate_count"], 0)


class AutomationWrapperSummaryTests(unittest.TestCase):
    def test_summary_reflects_run_status_and_available_outputs(self) -> None:
        run = run_daily_automation(
            daily_training_report=_daily_training_report(),
            daily_training_brief=_daily_training_brief(),
        )

        self.assertIn("status partial", run["summary"])
        self.assertIn("Usable daily brief was generated.", run["summary"])
        self.assertIn("Dashboard status=skipped.", run["summary"])
        self.assertIn("active rules=2", run["summary"])
        self.assertIn("promote candidates=1", run["summary"])


if __name__ == "__main__":
    unittest.main()
