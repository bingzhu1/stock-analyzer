from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import services.memory_store as ms
from services.projection_orchestrator import build_projection_orchestrator_result


class ProjectionOrchestratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._old_db_path = ms.DB_PATH
        ms.DB_PATH = Path(self._tmpdir.name) / "memory.db"

    def tearDown(self) -> None:
        ms.DB_PATH = self._old_db_path
        self._tmpdir.cleanup()

    def test_empty_state_returns_stable_ready_result(self) -> None:
        result = build_projection_orchestrator_result(symbol="avgo")

        self.assertEqual(result["symbol"], "AVGO")
        self.assertEqual(
            result["request"],
            {"symbol": "AVGO", "error_category": None, "limit": 5},
        )
        self.assertTrue(result["ready"])
        self.assertTrue(result["advisory_only"])
        self.assertEqual(result["advisory"]["matched_count"], 0)
        self.assertEqual(result["advisory"]["caution_level"], "none")
        self.assertEqual(result["advisory"]["reminder_lines"], [])
        self.assertIn("advisory package only", result["notes"][0])

    def test_packages_advisory_preflight_output(self) -> None:
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

        result = build_projection_orchestrator_result(symbol="AVGO")
        advisory = result["advisory"]

        self.assertEqual(result["symbol"], "AVGO")
        self.assertTrue(result["ready"])
        self.assertEqual(advisory["matched_count"], 2)
        self.assertEqual(advisory["caution_level"], "low")
        self.assertEqual(advisory["advisory_block"]["kind"], "projection_preflight_advisory")
        self.assertIn("Respect failed breakouts.", advisory["reminder_lines"][0])

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

        result = build_projection_orchestrator_result(
            symbol="avgo",
            error_category="wrong-direction",
            limit=3,
        )

        self.assertEqual(
            result["request"],
            {"symbol": "AVGO", "error_category": "wrong-direction", "limit": 3},
        )
        self.assertEqual(result["advisory"]["matched_count"], 3)
        self.assertEqual(result["advisory"]["caution_level"], "medium")
        self.assertEqual(len(result["advisory"]["reminder_lines"]), 3)

    def test_symbol_validation_is_preserved(self) -> None:
        with self.assertRaises(ValueError):
            build_projection_orchestrator_result(symbol=" ")


if __name__ == "__main__":
    unittest.main()
