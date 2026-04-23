from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.avgo_1000day_training import (
    build_avgo_1000day_rule_summary,
    run_avgo_1000day_replay_training,
)


def _replay_case(
    *,
    as_of_date: str,
    prediction_for_date: str,
    ready: bool = True,
    direction_correct: bool | None = True,
    confidence: str = "medium",
    risk_level: str = "medium",
    error_layer: str = "primary",
    error_category: str = "wrong_direction",
) -> dict[str, Any]:
    return {
        "kind": "historical_replay_result",
        "as_of_date": as_of_date,
        "prediction_for_date": prediction_for_date,
        "ready": ready,
        "projection_snapshot": {
            "final_decision": {
                "final_confidence": confidence,
                "risk_level": risk_level,
            }
        },
        "review": {
            "direction_correct": direction_correct,
            "error_layer": error_layer,
            "error_category": error_category,
            "rule_candidates": [],
        },
        "warnings": [] if ready else ["case degraded"],
    }


def _replay_batch_result() -> dict[str, Any]:
    return {
        "kind": "historical_replay_batch",
        "ready": True,
        "results": [
            _replay_case(as_of_date="2026-04-16", prediction_for_date="2026-04-17", direction_correct=True, confidence="high", risk_level="low"),
            _replay_case(as_of_date="2026-04-17", prediction_for_date="2026-04-18", direction_correct=False, confidence="medium", risk_level="high"),
            _replay_case(as_of_date="2026-04-18", prediction_for_date="2026-04-21", direction_correct=True, confidence="low", risk_level="medium"),
        ],
        "summary": {
            "total_cases": 3,
            "completed_cases": 2,
            "failed_cases": 1,
            "direction_accuracy": 0.6667,
        },
        "warnings": [],
    }


def _rule_score_report() -> dict[str, Any]:
    return {
        "kind": "rule_score_report",
        "ready": True,
        "top_promising_rules": [{"rule_key": "p1", "title": "规则A", "category": "bias"}],
        "top_risky_rules": [{"rule_key": "r1", "title": "规则B", "category": "bias"}],
        "rules": [
            {"rule_key": "p1", "title": "规则A", "category": "bias", "recommended_status": "promising", "hit_count": 8, "net_score": 4.0},
            {"rule_key": "r1", "title": "规则B", "category": "bias", "recommended_status": "risky", "harmful_count": 4, "harm_rate": 0.8},
        ],
        "warnings": [],
    }


def _rule_lifecycle_report() -> dict[str, Any]:
    return {
        "kind": "rule_lifecycle_report",
        "ready": True,
        "rules": [{"title": "规则A", "lifecycle_state": "promoted_active"}],
        "warnings": [],
    }


def _active_pool_report() -> dict[str, Any]:
    return {
        "kind": "active_rule_pool_report",
        "ready": True,
        "pool_counts": {"include": 1, "hold": 0, "exclude": 0},
        "active_pool_candidates": [{"rule_key": "p1", "title": "规则A"}],
        "warnings": [],
    }


def _active_pool_export() -> dict[str, Any]:
    return {
        "kind": "active_rule_pool_export",
        "ready": True,
        "exported_rule_count": 1,
        "exported_rules": [{"rule_key": "p1", "title": "规则A"}],
        "warnings": [],
    }


def _validation_report(*, ready: bool = False) -> dict[str, Any]:
    return {
        "kind": "active_rule_pool_validation_report",
        "ready": ready,
        "rule_effects": [
            {
                "rule_id": "rule-1",
                "title": "规则A",
                "category": "bias",
                "hit_count": 7,
                "changed_case_count": 3,
                "improved_case_count": 3,
                "worsened_case_count": 1,
                "net_effect": 2.0,
                "current_severity": "low",
                "current_effect": "warn",
                "notes": "validation note",
            }
        ],
        "warnings": ["validation degraded"] if not ready else [],
    }


def _calibration_report() -> dict[str, Any]:
    return {
        "kind": "active_rule_pool_calibration_report",
        "ready": True,
        "rules": [
            {
                "rule_id": "rule-1",
                "title": "规则A",
                "category": "bias",
                "calibration_decision": "retain",
                "hit_count": 7,
                "improved_case_count": 3,
                "worsened_case_count": 1,
                "net_effect": 2.0,
                "notes": "",
            }
        ],
        "warnings": [],
    }


def _promotion_report() -> dict[str, Any]:
    return {
        "kind": "active_rule_pool_promotion_report",
        "ready": True,
        "promote_candidates": [
            {
                "rule_id": "rule-1",
                "title": "规则A",
                "category": "bias",
                "promotion_decision": "promote_candidate",
                "promotion_confidence": "high",
                "hit_count": 7,
                "net_effect": 2.0,
            }
        ],
        "rules": [
            {
                "rule_id": "rule-1",
                "title": "规则A",
                "category": "bias",
                "promotion_decision": "promote_candidate",
                "promotion_confidence": "high",
                "hit_count": 7,
                "net_effect": 2.0,
            }
        ],
        "warnings": [],
    }


def _adoption_report() -> dict[str, Any]:
    return {
        "kind": "promotion_adoption_handoff",
        "ready": True,
        "production_candidates": [{"rule_id": "rule-1", "title": "规则A"}],
        "warnings": [],
    }


def _drift_report() -> dict[str, Any]:
    return {
        "kind": "active_rule_pool_drift_report",
        "ready": True,
        "drift_candidates": [{"rule_id": "rule-1", "title": "规则A"}],
        "warnings": [],
    }


class Avgo1000DayTrainingHappyPathTests(unittest.TestCase):
    def test_complete_replay_and_rule_growth_outputs_stable_report(self) -> None:
        report = run_avgo_1000day_replay_training(
            replay_batch_result=_replay_batch_result(),
            _rule_score_builder=lambda **_: _rule_score_report(),
            _rule_lifecycle_builder=lambda **_: _rule_lifecycle_report(),
            _active_pool_builder=lambda **_: _active_pool_report(),
            _active_pool_export_builder=lambda **_: _active_pool_export(),
            _validation_builder=lambda **_: _validation_report(),
            _calibration_builder=lambda **_: _calibration_report(),
            _promotion_builder=lambda **_: _promotion_report(),
            _adoption_builder=lambda **_: _adoption_report(),
            _drift_builder=lambda **_: _drift_report(),
        )

        self.assertEqual(report["kind"], "avgo_1000day_training_report")
        self.assertTrue(report["ready"])
        self.assertEqual(report["symbol"], "AVGO")
        self.assertEqual(report["num_cases_requested"], 1000)
        self.assertEqual(report["num_cases_built"], 3)
        self.assertEqual(report["date_range"]["start_as_of_date"], "2026-04-16")
        self.assertEqual(report["date_range"]["end_prediction_for_date"], "2026-04-21")
        self.assertEqual(report["replay_summary"]["total_cases"], 3)
        self.assertEqual(report["replay_summary"]["completed_cases"], 2)
        self.assertEqual(report["replay_summary"]["failed_cases"], 1)
        self.assertAlmostEqual(report["replay_summary"]["direction_accuracy"], 0.6667)
        self.assertIn("rule_score_report", report["rule_growth"])
        self.assertTrue(report["headline_findings"])
        self.assertEqual(report["rule_insights"]["top_effective_rules"][0]["title"], "规则A")
        self.assertEqual(report["rule_insights"]["top_harmful_rules"][0]["title"], "规则B")
        self.assertEqual(report["rule_insights"]["promote_candidates"][0]["title"], "规则A")
        self.assertEqual(report["rule_insights"]["production_candidates"][0]["title"], "规则A")
        self.assertEqual(report["rule_insights"]["drift_candidates"][0]["title"], "规则A")
        self.assertIn("direction accuracy", report["summary"])

    def test_alias_matches_main_entrypoint(self) -> None:
        self.assertEqual(
            build_avgo_1000day_rule_summary(
                replay_batch_result=_replay_batch_result(),
                _rule_score_builder=lambda **_: _rule_score_report(),
            )["kind"],
            "avgo_1000day_training_report",
        )


class Avgo1000DayTrainingBuilderTests(unittest.TestCase):
    def test_injected_runner_receives_ordered_date_pairs_without_future_leak(self) -> None:
        call_log: list[tuple[str, Any]] = []

        def _trading_days_provider(*, symbol: str, minimum_days: int) -> list[str]:
            call_log.append(("days", symbol, minimum_days))
            return ["2026-04-15", "2026-04-16", "2026-04-17", "2026-04-18"]

        def _replay_runner(**kwargs: Any) -> dict[str, Any]:
            call_log.append(("replay", kwargs["date_pairs"]))
            self.assertEqual(
                kwargs["date_pairs"],
                [
                    ("2026-04-15", "2026-04-16"),
                    ("2026-04-16", "2026-04-17"),
                    ("2026-04-17", "2026-04-18"),
                ],
            )
            return _replay_batch_result()

        report = run_avgo_1000day_replay_training(
            symbol="avgo",
            num_cases=1000,
            _trading_days_provider=_trading_days_provider,
            _replay_runner=_replay_runner,
        )

        self.assertEqual(call_log[0][0], "days")
        self.assertEqual(call_log[1][0], "replay")
        self.assertEqual(report["num_cases_built"], 3)
        self.assertEqual(report["date_range"]["start_as_of_date"], "2026-04-15")
        self.assertTrue(any("fewer than requested 1000" in warning for warning in report["warnings"]))

    def test_rule_growth_builder_failure_keeps_report_stable(self) -> None:
        report = run_avgo_1000day_replay_training(
            replay_batch_result=_replay_batch_result(),
            _rule_score_builder=lambda **_: (_ for _ in ()).throw(RuntimeError("score boom")),
            _rule_lifecycle_builder=lambda **_: _rule_lifecycle_report(),
        )

        self.assertIsNone(report["rule_growth"]["rule_score_report"])
        self.assertIsNotNone(report["rule_growth"]["rule_lifecycle_report"])
        self.assertTrue(any("rule_scoring: builder execution failed" in warning for warning in report["warnings"]))


class Avgo1000DayTrainingDegradedTests(unittest.TestCase):
    def test_partial_failed_cases_do_not_break_summary(self) -> None:
        replay_batch = _replay_batch_result()
        replay_batch["results"][1]["ready"] = False
        replay_batch["results"][1]["warnings"] = ["projection failed"]

        report = run_avgo_1000day_replay_training(replay_batch_result=replay_batch)

        self.assertEqual(report["replay_summary"]["failed_cases"], 1)
        self.assertTrue(report["headline_findings"])
        self.assertIn("failed 1 case", report["summary"])

    def test_malformed_replay_batch_result_is_handled_conservatively(self) -> None:
        report = run_avgo_1000day_replay_training(
            replay_batch_result={"kind": "historical_replay_batch", "results": "bad"},
        )

        self.assertFalse(report["ready"])
        self.assertEqual(report["num_cases_built"], 0)
        self.assertEqual(report["replay_summary"]["total_cases"], 0)
        self.assertIsNone(report["replay_summary"]["direction_accuracy"])
        self.assertTrue(report["headline_findings"])

    def test_summary_only_replay_batch_does_not_fabricate_built_cases_or_ready(self) -> None:
        report = run_avgo_1000day_replay_training(
            replay_batch_result={"summary": {"total_cases": 1000}},
        )

        self.assertEqual(report["num_cases_built"], 0)
        self.assertFalse(report["ready"])
        self.assertTrue(report["warnings"])

    def test_short_history_degrades_cleanly(self) -> None:
        report = run_avgo_1000day_replay_training(
            num_cases=1000,
            _trading_days_provider=lambda **_: ["2026-04-21"],
            _replay_runner=lambda **_: _replay_batch_result(),
        )

        self.assertFalse(report["ready"])
        self.assertEqual(report["num_cases_built"], 0)
        self.assertIn("No usable historical date pairs", report["summary"])


class Avgo1000DayTrainingInsightTests(unittest.TestCase):
    def test_default_path_skips_validation_tail_without_paired_validation_input(self) -> None:
        report = run_avgo_1000day_replay_training(
            replay_batch_result=_replay_batch_result(),
            _rule_score_builder=lambda **_: _rule_score_report(),
            _rule_lifecycle_builder=lambda **_: _rule_lifecycle_report(),
            _active_pool_builder=lambda **_: _active_pool_report(),
            _active_pool_export_builder=lambda **_: _active_pool_export(),
        )

        self.assertIsNone(report["rule_growth"]["validation_report"])
        self.assertIsNone(report["rule_growth"]["calibration_report"])
        self.assertIsNone(report["rule_growth"]["promotion_report"])
        self.assertIsNone(report["rule_growth"]["adoption_handoff"])
        self.assertIsNone(report["rule_growth"]["drift_report"])
        self.assertTrue(any("validation: skipped" in warning for warning in report["warnings"]))
        self.assertTrue(any("calibration: skipped" in warning for warning in report["warnings"]))
        self.assertTrue(any("promotion: skipped" in warning for warning in report["warnings"]))

    def test_findings_and_summary_align_with_growth_outputs(self) -> None:
        report = run_avgo_1000day_replay_training(
            replay_batch_result=_replay_batch_result(),
            _rule_score_builder=lambda **_: _rule_score_report(),
            _validation_builder=lambda **_: _validation_report(),
            _promotion_builder=lambda **_: _promotion_report(),
            _adoption_builder=lambda **_: _adoption_report(),
            _drift_builder=lambda **_: _drift_report(),
        )

        joined_findings = " ".join(report["headline_findings"])
        self.assertIn("promote candidates", joined_findings)
        self.assertIn("production candidates", joined_findings)
        self.assertIn("drift candidates", joined_findings)
        self.assertIn("Promote candidates=1", report["summary"])
        self.assertIn("production candidates=1", report["summary"])
        self.assertIn("drift candidates=1", report["summary"])
