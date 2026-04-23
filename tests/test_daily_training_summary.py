from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.daily_training_summary import (
    build_daily_training_brief,
    summarize_daily_training_report,
)


def _promotion_report() -> dict:
    return {
        "kind": "active_rule_pool_promotion_report",
        "promote_candidates": [
            {
                "rule_id": "promo-1",
                "title": "规则A",
                "promotion_confidence": "high",
                "notes": "promotion note",
            }
        ],
        "rules": [
            {
                "rule_id": "promo-1",
                "title": "规则A",
                "promotion_confidence": "high",
                "promotion_rationale": "promote rationale",
                "notes": "promotion note",
            }
        ],
    }


def _drift_report() -> dict:
    return {
        "kind": "active_rule_pool_drift_report",
        "drift_candidates": [
            {
                "rule_id": "drift-1",
                "title": "规则B",
                "drift_status": "drift_candidate",
                "recommended_followup": "review_for_downgrade",
                "notes": "drift note",
            }
        ],
    }


def _daily_report(
    *,
    step_status: dict | None = None,
    headline_metrics: dict | None = None,
    promotion_report: dict | None = None,
    drift_report: dict | None = None,
    ready: bool = True,
    warnings: list[str] | None = None,
) -> dict:
    return {
        "kind": "daily_training_report",
        "ready": ready,
        "symbol": "AVGO",
        "run_date": "2026-04-22",
        "step_status": step_status or {
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
        "headline_metrics": headline_metrics or {
            "total_replay_cases": 8,
            "direction_accuracy": 0.625,
            "active_rule_count": 3,
            "promote_candidate_count": 1,
            "drift_candidate_count": 1,
        },
        "artifacts": {
            "replay_batch_result": {},
            "rule_score_report": {},
            "rule_lifecycle_report": {},
            "active_rule_pool_report": {},
            "active_rule_pool_export": {},
            "active_rule_pool_validation_report": {},
            "active_rule_pool_calibration_report": {},
            "active_rule_pool_promotion_report": promotion_report if promotion_report is not None else _promotion_report(),
            "active_rule_pool_drift_report": drift_report if drift_report is not None else _drift_report(),
        },
        "summary": "source summary",
        "warnings": warnings or [],
    }


class DailyTrainingSummaryHappyPathTests(unittest.TestCase):
    def test_complete_daily_report_returns_stable_brief_shape(self) -> None:
        brief = build_daily_training_brief(_daily_report())

        self.assertEqual(brief["kind"], "daily_training_brief")
        self.assertTrue(brief["ready"])
        self.assertEqual(brief["symbol"], "AVGO")
        self.assertEqual(brief["run_date"], "2026-04-22")
        self.assertEqual(brief["overall_status"], "healthy")
        self.assertEqual(brief["step_overview"], {
            "ok": 9,
            "degraded": 0,
            "failed": 0,
            "skipped": 0,
        })
        self.assertEqual(brief["headline_metrics"]["total_replay_cases"], 8)
        self.assertEqual(brief["headline_metrics"]["direction_accuracy"], 0.625)
        self.assertEqual(brief["headline_metrics"]["active_rule_count"], 3)
        self.assertTrue(brief["summary"])

    def test_alias_matches_main_entrypoint(self) -> None:
        self.assertEqual(
            summarize_daily_training_report(daily_training_report=_daily_report())["kind"],
            "daily_training_brief",
        )


class DailyTrainingSummaryHighlightTests(unittest.TestCase):
    def test_promote_candidates_show_in_highlights_and_watchlist(self) -> None:
        brief = build_daily_training_brief(_daily_report())

        self.assertTrue(any("promote candidates" in item for item in brief["top_highlights"]))
        self.assertEqual(len(brief["promotion_watchlist"]), 1)
        self.assertEqual(brief["promotion_watchlist"][0]["rule_id"], "promo-1")
        self.assertEqual(brief["promotion_watchlist"][0]["promotion_confidence"], "high")

    def test_drift_candidates_show_in_highlights_and_watchlist(self) -> None:
        brief = build_daily_training_brief(_daily_report())

        self.assertTrue(any("drift candidates" in item for item in brief["top_highlights"]))
        self.assertEqual(len(brief["drift_watchlist"]), 1)
        self.assertEqual(brief["drift_watchlist"][0]["rule_id"], "drift-1")
        self.assertEqual(brief["drift_watchlist"][0]["recommended_followup"], "review_for_downgrade")


class DailyTrainingSummaryRiskTests(unittest.TestCase):
    def test_failed_or_degraded_steps_drive_risk_flags_and_overall_status(self) -> None:
        brief = build_daily_training_brief(
            _daily_report(
                step_status={
                    "replay": "ok",
                    "rule_scoring": "ok",
                    "rule_lifecycle": "ok",
                    "active_pool": "ok",
                    "active_pool_export": "ok",
                    "validation": "degraded",
                    "calibration": "ok",
                    "promotion": "failed",
                    "drift": "ok",
                }
            )
        )

        self.assertEqual(brief["overall_status"], "failed")
        self.assertTrue(any("promotion failed" in item for item in brief["risk_flags"]))
        self.assertTrue(any("validation degraded" in item for item in brief["risk_flags"]))
        self.assertNotEqual(brief["overall_status"], "healthy")


class DailyTrainingSummaryDegradedTests(unittest.TestCase):
    def test_missing_daily_training_report_returns_ready_false_and_warning(self) -> None:
        brief = build_daily_training_brief(None)

        self.assertFalse(brief["ready"])
        self.assertEqual(brief["kind"], "daily_training_brief")
        self.assertTrue(brief["warnings"])
        self.assertIn("缺少 daily_training_report", brief["summary"])

    def test_partial_report_does_not_crash_and_summary_stays_readable(self) -> None:
        brief = build_daily_training_brief(
            {
                "symbol": "AVGO",
                "run_date": "2026-04-22",
                "step_status": {"replay": "ok", "validation": "degraded"},
            }
        )

        self.assertEqual(brief["overall_status"], "degraded")
        self.assertEqual(brief["step_overview"]["ok"], 1)
        self.assertEqual(brief["step_overview"]["degraded"], 1)
        self.assertTrue(brief["summary"])
        self.assertTrue(brief["warnings"])

    def test_malformed_headline_metrics_do_not_crash_and_fall_back_with_warning(self) -> None:
        brief = build_daily_training_brief(
            {
                "symbol": "AVGO",
                "run_date": "2026-04-22",
                "step_status": {"replay": "ok"},
                "headline_metrics": {
                    "total_replay_cases": "bad",
                    "direction_accuracy": "bad",
                    "active_rule_count": "bad",
                    "promote_candidate_count": "bad",
                    "drift_candidate_count": "bad",
                },
            }
        )

        self.assertEqual(brief["headline_metrics"]["total_replay_cases"], 0)
        self.assertIsNone(brief["headline_metrics"]["direction_accuracy"])
        self.assertEqual(brief["headline_metrics"]["active_rule_count"], 0)
        self.assertEqual(brief["headline_metrics"]["promote_candidate_count"], 0)
        self.assertEqual(brief["headline_metrics"]["drift_candidate_count"], 0)
        self.assertTrue(brief["warnings"])
        self.assertTrue(brief["summary"])

    def test_missing_step_status_does_not_report_healthy(self) -> None:
        brief = build_daily_training_brief(
            {
                "symbol": "AVGO",
                "run_date": "2026-04-22",
                "headline_metrics": {
                    "total_replay_cases": 8,
                },
            }
        )

        self.assertNotEqual(brief["overall_status"], "healthy")
        self.assertEqual(brief["overall_status"], "degraded")
        self.assertTrue(brief["warnings"])
        self.assertEqual(brief["step_overview"], {
            "ok": 0,
            "degraded": 0,
            "failed": 0,
            "skipped": 0,
        })

    def test_missing_promotion_and_drift_artifacts_keep_watchlists_empty(self) -> None:
        brief = build_daily_training_brief(
            _daily_report(
                promotion_report={},
                drift_report={},
            )
        )

        self.assertEqual(brief["promotion_watchlist"], [])
        self.assertEqual(brief["drift_watchlist"], [])
        self.assertTrue(brief["summary"])


class DailyTrainingSummaryConsistencyTests(unittest.TestCase):
    def test_summary_highlights_and_next_checks_align_with_metrics_and_status(self) -> None:
        brief = build_daily_training_brief(
            _daily_report(
                step_status={
                    "replay": "ok",
                    "rule_scoring": "ok",
                    "rule_lifecycle": "ok",
                    "active_pool": "ok",
                    "active_pool_export": "ok",
                    "validation": "skipped",
                    "calibration": "skipped",
                    "promotion": "ok",
                    "drift": "ok",
                },
                headline_metrics={
                    "total_replay_cases": 5,
                    "direction_accuracy": 0.4,
                    "active_rule_count": 0,
                    "promote_candidate_count": 1,
                    "drift_candidate_count": 1,
                },
            )
        )

        self.assertIn("方向准确率", brief["summary"])
        self.assertTrue(any("promote candidates" in item for item in brief["top_highlights"]))
        self.assertTrue(any("drift candidates" in item for item in brief["top_highlights"]))
        self.assertTrue(any("validation" in item for item in brief["risk_flags"]))
        self.assertTrue(any("不要过度依赖 calibration 与 promotion" in item for item in brief["recommended_next_checks"]))
        self.assertTrue(any("active rule 数量为 0" in item for item in brief["recommended_next_checks"]))


if __name__ == "__main__":
    unittest.main()
