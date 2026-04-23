from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import services.memory_store as ms
from services.memory_feedback import build_memory_feedback


class MemoryFeedbackTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._old_db_path = ms.DB_PATH
        ms.DB_PATH = Path(self._tmpdir.name) / "memory.db"

    def tearDown(self) -> None:
        ms.DB_PATH = self._old_db_path
        self._tmpdir.cleanup()

    def test_empty_state_returns_no_reminders(self) -> None:
        feedback = build_memory_feedback(symbol="AVGO")

        self.assertEqual(feedback["symbol"], "AVGO")
        self.assertIsNone(feedback["error_category"])
        self.assertEqual(feedback["matched_count"], 0)
        self.assertEqual(feedback["reminders"], [])
        self.assertEqual(feedback["top_categories"], [])

    def test_builds_reminders_from_matching_symbol_records(self) -> None:
        first = ms.save_experience(
            symbol="AVGO",
            error_category="wrong_direction",
            root_cause="Momentum faded after the open.",
            lesson="Check whether morning strength holds into the close.",
            created_at="2026-04-12T10:00:00+00:00",
        )
        second = ms.save_experience(
            symbol="AVGO",
            error_category="right_direction_wrong_magnitude",
            root_cause="Correct direction but tiny move.",
            lesson="Separate direction calls from magnitude confidence.",
            created_at="2026-04-12T11:00:00+00:00",
        )
        ms.save_experience(
            symbol="MSFT",
            error_category="wrong_direction",
            root_cause="Other symbol.",
            lesson="Should not appear.",
            created_at="2026-04-12T12:00:00+00:00",
        )

        feedback = build_memory_feedback(symbol="avgo")

        self.assertEqual(feedback["matched_count"], 2)
        self.assertIn(second["lesson"], feedback["reminders"][0])
        self.assertIn(first["lesson"], feedback["reminders"][1])
        self.assertEqual(
            feedback["top_categories"],
            [
                {"error_category": "right_direction_wrong_magnitude", "count": 1},
                {"error_category": "wrong_direction", "count": 1},
            ],
        )

    def test_filters_by_normalized_error_category(self) -> None:
        keep = ms.save_experience(
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

        feedback = build_memory_feedback(
            symbol="AVGO",
            error_category="Wrong Direction",
        )

        self.assertEqual(feedback["error_category"], "wrong_direction")
        self.assertEqual(feedback["matched_count"], 1)
        self.assertIn(keep["lesson"], feedback["reminders"][0])
        self.assertEqual(
            feedback["top_categories"],
            [{"error_category": "wrong_direction", "count": 1}],
        )

    def test_limit_is_passed_through_to_retrieval(self) -> None:
        for index in range(3):
            ms.save_experience(
                symbol="AVGO",
                error_category="wrong_direction",
                root_cause=f"Cause {index}",
                lesson=f"Lesson {index}",
                created_at=f"2026-04-12T1{index}:00:00+00:00",
            )

        feedback = build_memory_feedback(symbol="AVGO", limit=2)

        self.assertEqual(feedback["matched_count"], 2)
        self.assertEqual(len(feedback["reminders"]), 2)


if __name__ == "__main__":
    unittest.main()
