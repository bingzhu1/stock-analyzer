from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import services.memory_store as ms
from services.projection_memory_briefing import build_projection_memory_briefing


class ProjectionMemoryBriefingTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._old_db_path = ms.DB_PATH
        ms.DB_PATH = Path(self._tmpdir.name) / "memory.db"

    def tearDown(self) -> None:
        ms.DB_PATH = self._old_db_path
        self._tmpdir.cleanup()

    def test_empty_state_returns_no_warning_briefing(self) -> None:
        briefing = build_projection_memory_briefing(symbol="avgo")

        self.assertEqual(
            briefing,
            {
                "symbol": "AVGO",
                "matched_count": 0,
                "top_categories": [],
                "reminder_lines": [],
                "caution_level": "none",
                "advisory_only": True,
            },
        )

    def test_packages_memory_feedback_for_projection_briefing(self) -> None:
        ms.save_experience(
            symbol="AVGO",
            error_category="wrong_direction",
            root_cause="Momentum faded.",
            lesson="Check whether morning strength holds.",
            created_at="2026-04-12T10:00:00+00:00",
        )
        ms.save_experience(
            symbol="AVGO",
            error_category="wrong_direction",
            root_cause="False breakout.",
            lesson="Respect failed breakouts.",
            created_at="2026-04-12T11:00:00+00:00",
        )
        ms.save_experience(
            symbol="MSFT",
            error_category="wrong_direction",
            root_cause="Other symbol.",
            lesson="Should not appear.",
            created_at="2026-04-12T12:00:00+00:00",
        )

        briefing = build_projection_memory_briefing(symbol="avgo")

        self.assertEqual(briefing["symbol"], "AVGO")
        self.assertEqual(briefing["matched_count"], 2)
        self.assertEqual(briefing["caution_level"], "low")
        self.assertTrue(briefing["advisory_only"])
        self.assertEqual(
            briefing["top_categories"],
            [{"error_category": "wrong_direction", "count": 2}],
        )
        self.assertEqual(len(briefing["reminder_lines"]), 2)
        self.assertIn("Respect failed breakouts.", briefing["reminder_lines"][0])

    def test_error_category_filter_is_passed_to_feedback(self) -> None:
        ms.save_experience(
            symbol="AVGO",
            error_category="wrong_direction",
            root_cause="Wrong way.",
            lesson="Wait for confirmation.",
            created_at="2026-04-12T10:00:00+00:00",
        )
        ms.save_experience(
            symbol="AVGO",
            error_category="correct",
            root_cause="Worked.",
            lesson="Not relevant to this filter.",
            created_at="2026-04-12T11:00:00+00:00",
        )

        briefing = build_projection_memory_briefing(
            symbol="AVGO",
            error_category="Wrong Direction",
        )

        self.assertEqual(briefing["matched_count"], 1)
        self.assertEqual(briefing["caution_level"], "low")
        self.assertEqual(
            briefing["top_categories"],
            [{"error_category": "wrong_direction", "count": 1}],
        )
        self.assertIn("Wait for confirmation.", briefing["reminder_lines"][0])

    def test_caution_level_increases_with_match_count(self) -> None:
        for index in range(5):
            ms.save_experience(
                symbol="AVGO",
                error_category="wrong_direction",
                root_cause=f"Cause {index}",
                lesson=f"Lesson {index}",
                created_at=f"2026-04-12T1{index}:00:00+00:00",
            )

        medium = build_projection_memory_briefing(symbol="AVGO", limit=4)
        high = build_projection_memory_briefing(symbol="AVGO", limit=5)

        self.assertEqual(medium["matched_count"], 4)
        self.assertEqual(medium["caution_level"], "medium")
        self.assertEqual(high["matched_count"], 5)
        self.assertEqual(high["caution_level"], "high")


if __name__ == "__main__":
    unittest.main()
