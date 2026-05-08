"""Contract enforcement tests for Step 12D (RISK-7) module integrations.

These tests pin the wire-up of cutoff_guard into the five modules listed
in 11D §9 (memory_feedback, projection_memory_briefing,
projection_rule_preflight, pre_prediction_briefing, projection_preflight).

Boundary contract: when an online caller passes a ``target_date``, the
modules MUST filter their historical records through
``services.cutoff_guard.filter_records_by_cutoff`` and surface a
``cutoff_guard`` audit summary in the output. Records dated after
``target_date`` MUST NOT appear in reminders / matched_rules / top_rules /
reasoning. The modules MUST NOT fall back to "use everything" when all
records are skipped.

Design contracts: 06 / 07A / 07B / 07C / 11D / 11H.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import services.memory_store as ms


class MemoryFeedbackCutoffGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._old_db_path = ms.DB_PATH
        ms.DB_PATH = Path(self._tmpdir.name) / "memory.db"

    def tearDown(self) -> None:
        ms.DB_PATH = self._old_db_path
        self._tmpdir.cleanup()

    def test_memory_feedback_filters_records_after_target_date(self) -> None:
        from services.memory_feedback import build_memory_feedback

        ms.save_experience(
            symbol="AVGO",
            error_category="wrong_direction",
            root_cause="Past lesson.",
            lesson="Past lesson body.",
            created_at="2026-04-19T10:00:00+00:00",
        )
        ms.save_experience(
            symbol="AVGO",
            error_category="false_confidence",
            root_cause="Future lesson.",
            lesson="Future lesson body.",
            created_at="2026-05-05T10:00:00+00:00",  # after target_date
        )

        feedback = build_memory_feedback(symbol="AVGO", target_date="2026-04-21")

        # Only the past record is allowed; future is skipped.
        self.assertEqual(feedback["matched_count"], 1)
        joined_reminders = " ".join(feedback["reminders"])
        self.assertIn("Past lesson body.", joined_reminders)
        self.assertNotIn("Future lesson body.", joined_reminders)
        # cutoff_guard summary present.
        self.assertIn("cutoff_guard", feedback)
        guard = feedback["cutoff_guard"]
        self.assertEqual(guard["target_date"], "2026-04-21")
        self.assertGreaterEqual(guard["skipped_count"], 1)
        self.assertIn(
            "record_after_target_date",
            guard["skipped_reasons"],
        )

    def test_memory_feedback_no_fallback_when_all_skipped(self) -> None:
        from services.memory_feedback import build_memory_feedback

        ms.save_experience(
            symbol="AVGO",
            error_category="wrong_direction",
            root_cause="Future only.",
            lesson="Should not appear.",
            created_at="2027-01-01T10:00:00+00:00",
        )

        feedback = build_memory_feedback(symbol="AVGO", target_date="2026-04-21")
        # No fallback to using future records.
        self.assertEqual(feedback["matched_count"], 0)
        self.assertEqual(feedback["reminders"], [])
        self.assertIn("cutoff_guard", feedback)
        self.assertGreaterEqual(feedback["cutoff_guard"]["skipped_count"], 1)

    def test_memory_feedback_target_date_none_preserves_old_behavior(self) -> None:
        """When the caller does not pass target_date, the old API path is
        preserved (no filtering, no cutoff_guard field)."""
        from services.memory_feedback import build_memory_feedback

        ms.save_experience(
            symbol="AVGO",
            error_category="wrong_direction",
            root_cause="Old API.",
            lesson="Old API lesson.",
            created_at="2027-01-01T10:00:00+00:00",
        )

        feedback = build_memory_feedback(symbol="AVGO")
        self.assertEqual(feedback["matched_count"], 1)
        # cutoff_guard remains absent under the legacy code path.
        self.assertNotIn("cutoff_guard", feedback)


class ProjectionMemoryBriefingCutoffGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._old_db_path = ms.DB_PATH
        ms.DB_PATH = Path(self._tmpdir.name) / "memory.db"

    def tearDown(self) -> None:
        ms.DB_PATH = self._old_db_path
        self._tmpdir.cleanup()

    def test_projection_memory_briefing_uses_cutoff_guard(self) -> None:
        from services.projection_memory_briefing import build_projection_memory_briefing

        ms.save_experience(
            symbol="AVGO",
            error_category="wrong_direction",
            root_cause="Past.",
            lesson="Past lesson body.",
            created_at="2026-04-19T10:00:00+00:00",
        )
        ms.save_experience(
            symbol="AVGO",
            error_category="false_confidence",
            root_cause="Future.",
            lesson="Future lesson body.",
            created_at="2027-01-01T10:00:00+00:00",
        )

        briefing = build_projection_memory_briefing(
            symbol="AVGO",
            target_date="2026-04-21",
        )
        self.assertEqual(briefing["matched_count"], 1)
        joined = " ".join(briefing["reminder_lines"])
        self.assertIn("Past lesson body.", joined)
        self.assertNotIn("Future lesson body.", joined)
        self.assertIn("cutoff_guard", briefing)
        self.assertEqual(briefing["cutoff_guard"]["target_date"], "2026-04-21")
        self.assertGreaterEqual(briefing["cutoff_guard"]["skipped_count"], 1)


class ProjectionRulePreflightCutoffGuardTests(unittest.TestCase):
    def test_projection_rule_preflight_skips_future_rules(self) -> None:
        from services.projection_rule_preflight import build_projection_rule_preflight

        # Memory briefing returns its own cutoff_guard via builder kwargs.
        briefing_called_with: dict = {}

        def _mock_briefing_builder(**kwargs):
            briefing_called_with.update(kwargs)
            # The briefing has 1 reminder + a cutoff_guard summary the preflight
            # should aggregate.
            return {
                "symbol": "AVGO",
                "matched_count": 1,
                "top_categories": [{"error_category": "wrong_direction"}],
                "reminder_lines": ["历史错误：方向。"],
                "caution_level": "low",
                "advisory_only": True,
                "cutoff_guard": {
                    "target_date": kwargs.get("target_date"),
                    "mode": "strict",
                    "allowed_count": 1,
                    "skipped_count": 1,
                    "skipped_reasons": ["record_after_target_date"],
                    "by_reason": {"record_after_target_date": 1},
                },
            }

        # Review loader returns a future review record and a past one.
        def _mock_review_loader(**_):
            return [
                {
                    "id": "rev-past",
                    "error_category": "wrong_direction",
                    "review_summary": "Past review msg.",
                    "created_at": "2026-04-19",
                },
                {
                    "id": "rev-future",
                    "error_category": "false_confidence",
                    "review_summary": "Future review msg.",
                    "created_at": "2027-01-01",
                },
            ]

        result = build_projection_rule_preflight(
            symbol="AVGO",
            target_date="2026-04-21",
            _memory_briefing_builder=_mock_briefing_builder,
            _review_loader=_mock_review_loader,
        )

        # Builder must have received target_date.
        self.assertEqual(briefing_called_with.get("target_date"), "2026-04-21")

        # Future review skipped from matched_rules.
        rule_messages = [r["message"] for r in result["matched_rules"]]
        self.assertIn("Past review msg.", rule_messages)
        self.assertNotIn("Future review msg.", rule_messages)

        # Aggregated cutoff_guard summary.
        self.assertIn("cutoff_guard", result)
        guard = result["cutoff_guard"]
        self.assertEqual(guard["target_date"], "2026-04-21")
        self.assertGreaterEqual(guard["skipped_count"], 2)
        self.assertIn("record_after_target_date", guard["skipped_reasons"])

    def test_projection_rule_preflight_target_date_none_legacy(self) -> None:
        """When no target_date is passed, the legacy path runs unchanged
        (no cutoff filtering of test stubs)."""
        from services.projection_rule_preflight import build_projection_rule_preflight

        def _empty_briefing(**_):
            return {
                "symbol": "AVGO",
                "matched_count": 0,
                "top_categories": [],
                "reminder_lines": [],
                "caution_level": "none",
                "advisory_only": True,
            }

        def _empty_reviews(**_):
            return []

        result = build_projection_rule_preflight(
            symbol="AVGO",
            _memory_briefing_builder=_empty_briefing,
            _review_loader=_empty_reviews,
        )
        # Legacy path: cutoff_guard either absent or summarises "no filtering".
        if "cutoff_guard" in result:
            self.assertIsNone(result["cutoff_guard"]["target_date"])


class PrePredictionBriefingCutoffGuardTests(unittest.TestCase):
    def test_pre_prediction_briefing_does_not_use_future_reviews(self) -> None:
        from services.pre_prediction_briefing import build_pre_prediction_briefing

        captured_summarize_kwargs: dict = {}

        def _mock_summarize(**kwargs):
            captured_summarize_kwargs.update(kwargs)
            return {
                "symbol": "AVGO",
                "record_count": 2,
                "overall_accuracy": 0.5,
                "dimension_accuracy": {"open": 0.5, "path": 0.5, "close": 0.5},
                "dimension_sample_count": {"open": 2, "path": 2, "close": 2},
                "weakest_dimension": "open",
                "strongest_dimension": "close",
                "error_category_counts": {},
                "primary_error_counts": {},
                "most_common_error_category": None,
                "most_common_primary_error": None,
            }

        def _mock_summarize_scenario(**_):
            return {
                "symbol": "AVGO",
                "record_count": 0,
                "scenario_type": "pred_open",
                "scenario_values": ["高开", "低开", "平开"],
                "scenario_record_count": {"高开": 0, "低开": 0, "平开": 0},
                "available_scenarios": [],
                "unknown_count": 0,
                "scenarios": {},
            }

        def _mock_extract_rules(_summary):
            return ["mock rule"]

        with patch(
            "services.pre_prediction_briefing.summarize_review_history",
            side_effect=_mock_summarize,
        ), patch(
            "services.pre_prediction_briefing.summarize_review_history_by_open_scenario",
            side_effect=_mock_summarize_scenario,
        ), patch(
            "services.pre_prediction_briefing.extract_review_rules",
            side_effect=_mock_extract_rules,
        ):
            briefing = build_pre_prediction_briefing(
                symbol="AVGO",
                limit=30,
                target_date="2026-04-21",
            )

        # summarize_review_history must have received target_date.
        self.assertEqual(captured_summarize_kwargs.get("target_date"), "2026-04-21")
        # Briefing surfaces cutoff_guard summary.
        self.assertIn("cutoff_guard", briefing)
        self.assertEqual(briefing["cutoff_guard"]["target_date"], "2026-04-21")


class ProjectionPreflightCutoffGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._old_db_path = ms.DB_PATH
        ms.DB_PATH = Path(self._tmpdir.name) / "memory.db"

    def tearDown(self) -> None:
        ms.DB_PATH = self._old_db_path
        self._tmpdir.cleanup()

    def test_orchestrator_preflight_passes_target_date(self) -> None:
        from services.projection_orchestrator_preflight import (
            build_projection_orchestrator_preflight,
        )

        ms.save_experience(
            symbol="AVGO",
            error_category="wrong_direction",
            root_cause="Past.",
            lesson="Past lesson body.",
            created_at="2026-04-19T10:00:00+00:00",
        )
        ms.save_experience(
            symbol="AVGO",
            error_category="false_confidence",
            root_cause="Future.",
            lesson="Future lesson body.",
            created_at="2027-01-01T10:00:00+00:00",
        )

        result = build_projection_orchestrator_preflight(
            symbol="AVGO",
            target_date="2026-04-21",
        )
        # target_date propagates down to the briefing.
        briefing = result["advisory_block"]["preflight"]["briefing"]
        self.assertIn("cutoff_guard", briefing)
        self.assertEqual(briefing["cutoff_guard"]["target_date"], "2026-04-21")
        # Matched count reflects only the past record.
        self.assertEqual(result["matched_count"], 1)
        joined = " ".join(result["reminder_lines"])
        self.assertIn("Past lesson body.", joined)
        self.assertNotIn("Future lesson body.", joined)


if __name__ == "__main__":
    unittest.main()
