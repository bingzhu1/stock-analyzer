from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import services.memory_store as ms
from services.projection_entrypoint import run_projection_entrypoint


class ProjectionEntrypointTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._old_db_path = ms.DB_PATH
        ms.DB_PATH = Path(self._tmpdir.name) / "memory.db"

    def tearDown(self) -> None:
        ms.DB_PATH = self._old_db_path
        self._tmpdir.cleanup()

    def test_empty_state_calls_orchestrator_chain(self) -> None:
        result = run_projection_entrypoint(symbol="avgo")

        self.assertEqual(result["symbol"], "AVGO")
        self.assertEqual(
            result["request"],
            {"symbol": "AVGO", "error_category": None, "limit": 5, "lookback_days": None},
        )
        self.assertTrue(result["ready"])
        self.assertFalse(result["advisory_only"])
        self.assertEqual(result["projection_report"]["kind"], "final_projection_report")
        self.assertEqual(
            result["projection_report"]["readable_summary"]["kind"],
            "predict_readable_summary",
        )
        self.assertIn("明日方向：", result["projection_report"]["report_text"])
        self.assertIn("明日基准判断：", result["projection_report"]["report_text"])
        self.assertEqual(result["advisory"]["matched_count"], 0)
        self.assertEqual(result["advisory"]["caution_level"], "none")
        self.assertEqual(result["advisory"]["reminder_lines"], [])

    def test_returns_orchestrated_result_without_changing_meaning(self) -> None:
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

        result = run_projection_entrypoint(symbol="AVGO")

        self.assertEqual(result["advisory"]["matched_count"], 2)
        self.assertEqual(result["advisory"]["caution_level"], "low")
        self.assertIn("Respect failed breakouts.", result["advisory"]["reminder_lines"][0])
        self.assertIn("Scan + Predict", result["notes"][0])
        self.assertTrue(
            any("Respect failed breakouts." in line for line in result["projection_report"]["risk_reminders"])
        )

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

        result = run_projection_entrypoint(
            symbol="avgo",
            error_category="wrong-direction",
            limit=3,
            lookback_days=20,
        )

        self.assertEqual(
            result["request"],
            {"symbol": "AVGO", "error_category": "wrong-direction", "limit": 3, "lookback_days": 20},
        )
        self.assertEqual(result["advisory"]["matched_count"], 3)
        self.assertEqual(result["advisory"]["caution_level"], "medium")
        self.assertEqual(len(result["advisory"]["reminder_lines"]), 3)
        self.assertIn("最近 20 天", result["projection_report"]["basis_summary"][-1])

    def test_symbol_validation_is_preserved(self) -> None:
        with self.assertRaises(ValueError):
            run_projection_entrypoint(symbol=" ")


if __name__ == "__main__":
    unittest.main()
