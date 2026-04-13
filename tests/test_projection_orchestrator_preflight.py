from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import services.memory_store as ms
from services.projection_orchestrator_preflight import (
    build_projection_orchestrator_preflight,
)


class ProjectionOrchestratorPreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._old_db_path = ms.DB_PATH
        ms.DB_PATH = Path(self._tmpdir.name) / "memory.db"

    def tearDown(self) -> None:
        ms.DB_PATH = self._old_db_path
        self._tmpdir.cleanup()

    def test_empty_state_returns_valid_no_warning_block(self) -> None:
        result = build_projection_orchestrator_preflight(symbol="avgo")

        self.assertEqual(result["symbol"], "AVGO")
        self.assertTrue(result["ready"])
        self.assertTrue(result["advisory_only"])
        self.assertEqual(result["matched_count"], 0)
        self.assertEqual(result["caution_level"], "none")
        self.assertEqual(result["reminder_lines"], [])
        self.assertEqual(result["advisory_block"]["kind"], "projection_preflight_advisory")
        self.assertEqual(result["advisory_block"]["source"], "projection_preflight")
        self.assertTrue(result["advisory_block"]["advisory_only"])
        self.assertEqual(result["advisory_block"]["preflight"]["matched_count"], 0)

    def test_wraps_preflight_output_for_orchestration(self) -> None:
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

        result = build_projection_orchestrator_preflight(symbol="AVGO")
        preflight = result["advisory_block"]["preflight"]

        self.assertEqual(result["matched_count"], 2)
        self.assertEqual(result["caution_level"], "low")
        self.assertEqual(result["reminder_lines"], preflight["reminder_lines"])
        self.assertEqual(result["matched_count"], preflight["matched_count"])
        self.assertEqual(result["caution_level"], preflight["caution_level"])
        self.assertIn("Respect failed breakouts.", result["reminder_lines"][0])

    def test_error_category_and_limit_are_forwarded(self) -> None:
        for index in range(4):
            ms.save_experience(
                symbol="AVGO",
                error_category="wrong_direction",
                root_cause=f"Cause {index}",
                lesson=f"Lesson {index}",
                created_at=f"2026-04-12T1{index}:00:00+00:00",
            )
        ms.save_experience(
            symbol="AVGO",
            error_category="correct",
            root_cause="Worked.",
            lesson="Not relevant.",
            created_at="2026-04-12T15:00:00+00:00",
        )

        result = build_projection_orchestrator_preflight(
            symbol="avgo",
            error_category="wrong-direction",
            limit=3,
        )

        self.assertEqual(result["matched_count"], 3)
        self.assertEqual(result["caution_level"], "medium")
        self.assertEqual(len(result["reminder_lines"]), 3)
        self.assertEqual(
            result["advisory_block"]["preflight"]["briefing"]["top_categories"],
            [{"error_category": "wrong_direction", "count": 3}],
        )

    def test_symbol_validation_is_preserved(self) -> None:
        with self.assertRaises(ValueError):
            build_projection_orchestrator_preflight(symbol=" ")


if __name__ == "__main__":
    unittest.main()
