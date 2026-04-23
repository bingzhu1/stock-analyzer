from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import services.memory_store as ms
from services.projection_orchestrator import (
    build_projection_orchestrator_result,
    format_projection_report,
)


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
            {"symbol": "AVGO", "error_category": None, "limit": 5, "lookback_days": None},
        )
        self.assertTrue(result["ready"])
        self.assertFalse(result["advisory_only"])
        self.assertEqual(result["projection_report"]["kind"], "final_projection_report")
        self.assertIn(result["projection_report"]["direction"], {"偏多", "偏空", "中性"})
        self.assertIn(result["projection_report"]["open_tendency"], {"高开", "平开", "低开"})
        self.assertIn(result["projection_report"]["close_tendency"], {"偏强", "震荡", "偏弱"})
        self.assertIn("confidence", result["projection_report"])
        self.assertEqual(
            result["projection_report"]["readable_summary"]["kind"],
            "predict_readable_summary",
        )
        self.assertEqual(
            result["projection_report"]["evidence_trace"]["kind"],
            "projection_evidence_trace",
        )
        self.assertEqual(
            result["projection_report"]["evidence_trace"]["final_conclusion"]["direction"],
            result["projection_report"]["direction"],
        )
        self.assertTrue(result["projection_report"]["evidence_trace"]["tool_trace"])
        self.assertTrue(result["projection_report"]["basis_summary"])
        self.assertTrue(result["projection_report"]["risk_reminders"])
        self.assertIn("明日方向：", result["projection_report"]["report_text"])
        self.assertIn("明日基准判断：", result["projection_report"]["report_text"])
        self.assertIn("开盘推演：", result["projection_report"]["report_text"])
        self.assertIn("收盘推演：", result["projection_report"]["report_text"])
        self.assertIn("为什么这样判断：", result["projection_report"]["report_text"])
        self.assertIn("风险提醒：", result["projection_report"]["report_text"])
        self.assertEqual(result["advisory"]["matched_count"], 0)
        self.assertEqual(result["advisory"]["caution_level"], "none")
        self.assertEqual(result["advisory"]["reminder_lines"], [])
        self.assertIn("Scan + Predict", result["notes"][0])

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

        result = build_projection_orchestrator_result(
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
            build_projection_orchestrator_result(symbol=" ")

    def test_report_formatter_handles_empty_predict_result(self) -> None:
        report = format_projection_report({})

        self.assertEqual(report["kind"], "final_projection_report")
        self.assertEqual(report["direction"], "中性")
        self.assertEqual(report["open_tendency"], "平开")
        self.assertEqual(report["close_tendency"], "震荡")
        self.assertEqual(report["confidence"], "low")
        self.assertEqual(report["readable_summary"]["kind"], "predict_readable_summary")
        self.assertEqual(report["evidence_trace"]["kind"], "projection_evidence_trace")
        self.assertEqual(report["evidence_trace"]["final_conclusion"]["direction"], "中性")
        self.assertTrue(report["basis_summary"])
        self.assertTrue(report["risk_reminders"])


if __name__ == "__main__":
    unittest.main()
