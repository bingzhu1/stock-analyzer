from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.daily_training_pipeline import (
    build_daily_training_report,
    run_daily_training_pipeline,
)


def _replay_batch(*, total_cases: int = 4, direction_accuracy: float = 0.75) -> dict:
    return {
        "kind": "historical_replay_batch",
        "ready": True,
        "results": [
            {
                "as_of_date": "2026-04-18",
                "prediction_for_date": "2026-04-19",
                "review": {"direction_correct": True},
            }
        ],
        "summary": {
            "total_cases": total_cases,
            "direction_accuracy": direction_accuracy,
        },
        "warnings": [],
    }


def _rule_score_report() -> dict:
    return {
        "kind": "rule_score_report",
        "ready": True,
        "rules": [{"title": "规则A"}],
        "warnings": [],
    }


def _rule_lifecycle_report() -> dict:
    return {
        "kind": "rule_lifecycle_report",
        "ready": True,
        "rules": [{"title": "规则A", "lifecycle_state": "promoted_active"}],
        "warnings": [],
    }


def _active_pool_report(*, include_count: int = 2) -> dict:
    return {
        "kind": "active_rule_pool_report",
        "ready": True,
        "pool_counts": {"include": include_count, "hold": 0, "exclude": 0},
        "active_pool_candidates": [{"title": f"规则{i + 1}"} for i in range(include_count)],
        "rules": [{"title": "规则A", "pool_decision": "include"}],
        "warnings": [],
    }


def _active_pool_export(*, exported_rule_count: int = 2) -> dict:
    return {
        "kind": "active_rule_pool_export",
        "ready": True,
        "exported_rule_count": exported_rule_count,
        "preflight_bridge_rules": [{"rule_id": "arp-1"} for _ in range(exported_rule_count)],
        "warnings": [],
    }


def _validation_report(*, ready: bool = True, warning: str | None = None) -> dict:
    warnings = [warning] if warning else []
    return {
        "kind": "active_rule_pool_validation_report",
        "ready": ready,
        "active_pool_accuracy": 0.8,
        "baseline_accuracy": 0.75,
        "rule_effects": [
            {
                "rule_id": "rule-1",
                "title": "规则A",
                "hit_count": 6,
                "changed_case_count": 4,
                "improved_case_count": 4,
                "worsened_case_count": 1,
                "net_effect": 3.0,
                "current_severity": "low",
                "current_effect": "warn",
                "notes": "validation note",
            }
        ],
        "warnings": warnings,
    }


def _calibration_report() -> dict:
    return {
        "kind": "active_rule_pool_calibration_report",
        "ready": True,
        "decision_counts": {
            "retain": 1,
            "downgrade": 0,
            "recalibrate": 0,
            "remove_candidate": 0,
            "observe": 0,
        },
        "rules": [
            {
                "rule_id": "rule-1",
                "title": "规则A",
                "category": "wrong_direction",
                "calibration_decision": "retain",
                "hit_count": 6,
                "improved_case_count": 4,
                "worsened_case_count": 1,
                "net_effect": 3.0,
                "notes": "",
            }
        ],
        "warnings": [],
    }


def _promotion_report(*, promote_candidate_count: int = 1) -> dict:
    return {
        "kind": "active_rule_pool_promotion_report",
        "ready": True,
        "decision_counts": {
            "promote_candidate": promote_candidate_count,
            "keep_active_observe": 0,
            "hold_back": 0,
            "do_not_promote": 0,
        },
        "promote_candidates": [{"title": f"规则{i + 1}"} for i in range(promote_candidate_count)],
        "warnings": [],
    }


def _drift_report(*, drift_candidate_count: int = 1) -> dict:
    return {
        "kind": "active_rule_pool_drift_report",
        "ready": True,
        "status_counts": {
            "stable": 0,
            "drift_candidate": drift_candidate_count,
            "improving": 0,
            "unclear": 0,
        },
        "drift_candidates": [{"title": f"规则{i + 1}"} for i in range(drift_candidate_count)],
        "warnings": [],
    }


class DailyTrainingPipelineDirectArtifactTests(unittest.TestCase):
    def test_complete_artifacts_produce_stable_report_and_metrics(self) -> None:
        report = run_daily_training_pipeline(
            replay_batch_result=_replay_batch(total_cases=4, direction_accuracy=0.75),
            rule_score_report=_rule_score_report(),
            rule_lifecycle_report=_rule_lifecycle_report(),
            active_pool_report=_active_pool_report(include_count=2),
            active_pool_export=_active_pool_export(exported_rule_count=2),
            validation_report=_validation_report(),
            calibration_report=_calibration_report(),
            promotion_report=_promotion_report(promote_candidate_count=1),
            drift_report=_drift_report(drift_candidate_count=1),
            symbol="avgo",
            run_date="2026-04-22",
        )

        self.assertEqual(report["kind"], "daily_training_report")
        self.assertTrue(report["ready"])
        self.assertEqual(report["symbol"], "AVGO")
        self.assertEqual(report["run_date"], "2026-04-22")
        self.assertEqual(set(report["step_status"].keys()), {
            "replay",
            "rule_scoring",
            "rule_lifecycle",
            "active_pool",
            "active_pool_export",
            "validation",
            "calibration",
            "promotion",
            "drift",
        })
        self.assertTrue(all(status == "ok" for status in report["step_status"].values()))
        self.assertEqual(report["headline_metrics"]["total_replay_cases"], 4)
        self.assertEqual(report["headline_metrics"]["direction_accuracy"], 0.75)
        self.assertEqual(report["headline_metrics"]["active_rule_count"], 2)
        self.assertEqual(report["headline_metrics"]["promote_candidate_count"], 1)
        self.assertEqual(report["headline_metrics"]["drift_candidate_count"], 1)
        self.assertIn("Replay cases=4", report["summary"])
        self.assertIn("Direction accuracy=75.0%", report["summary"])
        self.assertIn("Active rules=2", report["summary"])
        self.assertIn("Promote candidates=1", report["summary"])
        self.assertIn("Drift candidates=1", report["summary"])

    def test_alias_function_matches_main_entrypoint(self) -> None:
        self.assertEqual(
            build_daily_training_report(
                replay_batch_result=_replay_batch(),
                active_pool_report=_active_pool_report(),
            )["kind"],
            "daily_training_report",
        )


class DailyTrainingPipelineBuilderChainTests(unittest.TestCase):
    def test_injected_builders_run_in_order_and_fill_artifacts(self) -> None:
        call_log: list[str] = []

        def _replay_runner(**kwargs) -> dict:
            call_log.append("replay")
            self.assertEqual(kwargs["symbol"], "AVGO")
            return _replay_batch()

        def _score_builder(*, replay_batch_result=None, **kwargs) -> dict:
            call_log.append("score")
            self.assertEqual(replay_batch_result["kind"], "historical_replay_batch")
            self.assertEqual(kwargs["lookback_days"], 20)
            return _rule_score_report()

        def _lifecycle_builder(*, rule_score_report=None, **kwargs) -> dict:
            call_log.append("lifecycle")
            self.assertEqual(rule_score_report["kind"], "rule_score_report")
            return _rule_lifecycle_report()

        def _active_pool_builder(*, rule_lifecycle_report=None, **kwargs) -> dict:
            call_log.append("active_pool")
            self.assertEqual(rule_lifecycle_report["kind"], "rule_lifecycle_report")
            return _active_pool_report()

        def _export_builder(*, active_pool_report=None, **kwargs) -> dict:
            call_log.append("export")
            self.assertEqual(active_pool_report["kind"], "active_rule_pool_report")
            return _active_pool_export()

        def _validation_builder(**kwargs) -> dict:
            call_log.append("validation")
            self.assertEqual(kwargs["active_pool_export"]["kind"], "active_rule_pool_export")
            return _validation_report()

        def _calibration_builder(**kwargs) -> dict:
            call_log.append("calibration")
            self.assertEqual(kwargs["validation_report"]["kind"], "active_rule_pool_validation_report")
            return _calibration_report()

        def _promotion_builder(**kwargs) -> dict:
            call_log.append("promotion")
            self.assertEqual(kwargs["calibration_report"]["kind"], "active_rule_pool_calibration_report")
            return _promotion_report()

        def _drift_builder(**kwargs) -> dict:
            call_log.append("drift")
            self.assertEqual(kwargs["validation_report"]["kind"], "active_rule_pool_validation_report")
            return _drift_report()

        report = run_daily_training_pipeline(
            _replay_runner=_replay_runner,
            _rule_score_builder=_score_builder,
            _rule_lifecycle_builder=_lifecycle_builder,
            _active_pool_builder=_active_pool_builder,
            _active_pool_export_builder=_export_builder,
            _validation_builder=_validation_builder,
            _calibration_builder=_calibration_builder,
            _promotion_builder=_promotion_builder,
            _drift_builder=_drift_builder,
        )

        self.assertEqual(
            call_log,
            ["replay", "score", "lifecycle", "active_pool", "export", "validation", "calibration", "promotion", "drift"],
        )
        self.assertTrue(all(status == "ok" for status in report["step_status"].values()))
        self.assertEqual(report["artifacts"]["active_rule_pool_export"]["kind"], "active_rule_pool_export")
        self.assertEqual(report["artifacts"]["active_rule_pool_promotion_report"]["kind"], "active_rule_pool_promotion_report")


class DailyTrainingPipelineFailureAndDegradedTests(unittest.TestCase):
    def test_single_step_failure_does_not_block_later_independent_step(self) -> None:
        def _boom(**kwargs) -> dict:
            raise RuntimeError("promotion exploded")

        report = run_daily_training_pipeline(
            replay_batch_result=_replay_batch(),
            rule_score_report=_rule_score_report(),
            rule_lifecycle_report=_rule_lifecycle_report(),
            active_pool_report=_active_pool_report(),
            active_pool_export=_active_pool_export(),
            validation_report=_validation_report(),
            calibration_report=_calibration_report(),
            _promotion_builder=_boom,
            _drift_builder=lambda **kwargs: _drift_report(drift_candidate_count=2),
        )

        self.assertEqual(report["step_status"]["promotion"], "failed")
        self.assertEqual(report["step_status"]["drift"], "ok")
        self.assertIsNone(report["artifacts"]["active_rule_pool_promotion_report"])
        self.assertEqual(report["headline_metrics"]["drift_candidate_count"], 2)
        self.assertTrue(any("promotion" in warning and "exploded" in warning for warning in report["warnings"]))

    def test_missing_upstream_inputs_and_builders_skip_stably(self) -> None:
        report = run_daily_training_pipeline()

        self.assertFalse(report["ready"])
        self.assertEqual(report["step_status"]["replay"], "skipped")
        self.assertEqual(report["step_status"]["rule_scoring"], "skipped")
        self.assertEqual(report["step_status"]["rule_lifecycle"], "skipped")
        self.assertEqual(report["step_status"]["active_pool"], "skipped")
        self.assertEqual(report["step_status"]["active_pool_export"], "skipped")
        self.assertEqual(report["step_status"]["validation"], "skipped")
        self.assertEqual(report["artifacts"]["replay_batch_result"], None)
        self.assertEqual(report["headline_metrics"]["total_replay_cases"], 0)
        self.assertTrue(report["warnings"])

    def test_replay_only_without_intermediate_builders_skips_remaining_steps_and_stays_not_ready(self) -> None:
        report = run_daily_training_pipeline(
            replay_batch_result=_replay_batch(),
        )

        self.assertEqual(report["step_status"]["replay"], "ok")
        self.assertEqual(report["step_status"]["rule_scoring"], "skipped")
        self.assertEqual(report["step_status"]["rule_lifecycle"], "skipped")
        self.assertEqual(report["step_status"]["active_pool"], "skipped")
        self.assertEqual(report["step_status"]["active_pool_export"], "skipped")
        self.assertEqual(report["step_status"]["validation"], "skipped")
        self.assertEqual(report["step_status"]["calibration"], "skipped")
        self.assertEqual(report["step_status"]["promotion"], "skipped")
        self.assertEqual(report["step_status"]["drift"], "skipped")
        self.assertFalse(report["ready"])

    def test_degraded_artifact_is_retained_and_warning_bubbles_up(self) -> None:
        report = run_daily_training_pipeline(
            replay_batch_result=_replay_batch(),
            rule_score_report=_rule_score_report(),
            rule_lifecycle_report=_rule_lifecycle_report(),
            active_pool_report=_active_pool_report(),
            active_pool_export=_active_pool_export(),
            validation_report=_validation_report(ready=False, warning="paired cases missing"),
        )

        self.assertEqual(report["step_status"]["validation"], "degraded")
        self.assertIsNotNone(report["artifacts"]["active_rule_pool_validation_report"])
        self.assertTrue(any("validation: paired cases missing" == warning for warning in report["warnings"]))

    def test_bad_downstream_artifact_does_not_mark_report_ready(self) -> None:
        report = run_daily_training_pipeline(
            active_pool_report=[],
        )

        self.assertEqual(report["step_status"]["active_pool"], "degraded")
        self.assertEqual(report["artifacts"]["active_rule_pool_report"], {})
        self.assertEqual(report["step_status"]["active_pool_export"], "skipped")
        self.assertFalse(report["ready"])


class DailyTrainingPipelineReadySemanticsTests(unittest.TestCase):
    def test_ready_is_true_once_a_management_step_is_actually_usable(self) -> None:
        report = run_daily_training_pipeline(
            active_pool_report=_active_pool_report(),
        )

        self.assertTrue(report["ready"])
        self.assertEqual(report["step_status"]["active_pool"], "ok")
        self.assertEqual(report["headline_metrics"]["active_rule_count"], 2)


if __name__ == "__main__":
    unittest.main()
