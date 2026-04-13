from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import services.memory_store as ms
from services.projection_preflight import build_projection_preflight


class ProjectionPreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._old_db_path = ms.DB_PATH
        ms.DB_PATH = Path(self._tmpdir.name) / "memory.db"

    def tearDown(self) -> None:
        ms.DB_PATH = self._old_db_path
        self._tmpdir.cleanup()

    def test_empty_state_returns_ready_preflight(self) -> None:
        preflight = build_projection_preflight(symbol="avgo")

        self.assertEqual(preflight["symbol"], "AVGO")
        self.assertTrue(preflight["ready"])
        self.assertTrue(preflight["advisory_only"])
        self.assertEqual(preflight["matched_count"], 0)
        self.assertEqual(preflight["caution_level"], "none")
        self.assertEqual(preflight["reminder_lines"], [])
        self.assertEqual(
            preflight["briefing"],
            {
                "symbol": "AVGO",
                "matched_count": 0,
                "top_categories": [],
                "reminder_lines": [],
                "caution_level": "none",
                "advisory_only": True,
            },
        )

    def test_packages_briefing_fields_for_projection(self) -> None:
        ms.save_experience(
            symbol="AVGO",
            error_category="wrong_direction",
            root_cause="Momentum faded.",
            lesson="Wait for close-strength confirmation.",
            created_at="2026-04-12T10:00:00+00:00",
        )
        ms.save_experience(
            symbol="AVGO",
            error_category="wrong_direction",
            root_cause="False breakout.",
            lesson="Respect failed breakouts.",
            created_at="2026-04-12T11:00:00+00:00",
        )

        preflight = build_projection_preflight(symbol="AVGO")

        self.assertTrue(preflight["ready"])
        self.assertEqual(preflight["matched_count"], 2)
        self.assertEqual(preflight["caution_level"], "low")
        self.assertEqual(preflight["reminder_lines"], preflight["briefing"]["reminder_lines"])
        self.assertIn("Respect failed breakouts.", preflight["reminder_lines"][0])
        self.assertEqual(
            preflight["briefing"]["top_categories"],
            [{"error_category": "wrong_direction", "count": 2}],
        )

    def test_error_category_filter_is_forwarded(self) -> None:
        ms.save_experience(
            symbol="AVGO",
            error_category="wrong_direction",
            root_cause="Wrong direction.",
            lesson="Wait for confirmation.",
            created_at="2026-04-12T10:00:00+00:00",
        )
        ms.save_experience(
            symbol="AVGO",
            error_category="correct",
            root_cause="Worked.",
            lesson="Not relevant.",
            created_at="2026-04-12T11:00:00+00:00",
        )

        preflight = build_projection_preflight(
            symbol="AVGO",
            error_category="Wrong Direction",
        )

        self.assertEqual(preflight["matched_count"], 1)
        self.assertEqual(
            preflight["briefing"]["top_categories"],
            [{"error_category": "wrong_direction", "count": 1}],
        )
        self.assertIn("Wait for confirmation.", preflight["reminder_lines"][0])

    def test_limit_is_forwarded_to_briefing(self) -> None:
        for index in range(5):
            ms.save_experience(
                symbol="AVGO",
                error_category="wrong_direction",
                root_cause=f"Cause {index}",
                lesson=f"Lesson {index}",
                created_at=f"2026-04-12T1{index}:00:00+00:00",
            )

        preflight = build_projection_preflight(symbol="AVGO", limit=4)

        self.assertEqual(preflight["matched_count"], 4)
        self.assertEqual(preflight["caution_level"], "medium")
        self.assertEqual(len(preflight["reminder_lines"]), 4)

    def test_symbol_is_required(self) -> None:
        with self.assertRaises(ValueError):
            build_projection_preflight(symbol=" ")


if __name__ == "__main__":
    unittest.main()
