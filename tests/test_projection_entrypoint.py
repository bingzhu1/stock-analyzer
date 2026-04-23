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
        self.assertEqual(result["projection_schema"], "v2")
        self.assertEqual(result["source_of_truth"], "projection_v2_raw")
        self.assertEqual(result["projection_v2_raw"]["kind"], "projection_v2_report")
        self.assertEqual(result["legacy_compat"]["projection_report"], "legacy_fallback")
        self.assertEqual(result["legacy_compat"]["advisory"], "legacy_fallback")
        self.assertEqual(
            result["request"],
            {"symbol": "AVGO", "error_category": None, "limit": 5, "lookback_days": None},
        )
        self.assertTrue(result["ready"])
        self.assertFalse(result["advisory_only"])
        self.assertEqual(result["projection_report"]["kind"], "final_projection_report")
        self.assertEqual(result["projection_narrative"]["kind"], "projection_narrative")
        self.assertTrue(result["projection_narrative"]["step1_conclusion"])
        self.assertTrue(result["projection_narrative"]["one_line_summary"])
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
        self.assertIsInstance(result["notes"], list)
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
        self.assertIsInstance(result["projection_report"]["basis_summary"], list)
        self.assertTrue(len(result["projection_report"]["basis_summary"]) > 0)

    def test_entrypoint_calls_v2_runner_then_packages_legacy_shell(self) -> None:
        fake_v2 = {"kind": "projection_v2_report", "ready": True}
        packaged = {
            "kind": "projection_entrypoint_result",
            "projection_schema": "v2",
            "source_of_truth": "projection_v2_raw",
            "projection_v2_raw": fake_v2,
        }
        narrative = {
            "kind": "projection_narrative",
            "ready": True,
            "step1_conclusion": "step1",
            "step2_peer_adjustment": "step2",
            "final_judgment": "final",
            "open_tendency": "open",
            "intraday_structure": "intraday",
            "close_tendency": "close",
            "key_watchpoints": {"stronger_case": ["a"], "weaker_case": ["b"]},
            "one_line_summary": "summary",
            "warnings": [],
        }

        with patch("services.projection_entrypoint.run_projection_v2", return_value=fake_v2) as runner:
            with patch(
                "services.projection_entrypoint.build_projection_entrypoint_result",
                return_value=packaged,
            ) as packager:
                with patch(
                    "services.projection_entrypoint.build_projection_narrative",
                    return_value=narrative,
                ) as narrative_builder:
                    result = run_projection_entrypoint(
                        symbol="avgo",
                        error_category="wrong-direction",
                        limit=3,
                        lookback_days=10,
                    )

        self.assertEqual(result, packaged | {"projection_narrative": narrative})
        runner.assert_called_once_with(symbol="AVGO", lookback_days=10)
        packager.assert_called_once_with(
            v2_raw=fake_v2,
            symbol="AVGO",
            error_category="wrong-direction",
            limit=3,
            lookback_days=10,
        )
        narrative_builder.assert_called_once_with(
            projection_v2_raw=fake_v2,
            symbol="AVGO",
        )

    def test_narrative_failure_does_not_break_packaged_entrypoint_result(self) -> None:
        fake_v2 = {"kind": "projection_v2_report", "ready": True}
        packaged = {
            "kind": "projection_entrypoint_result",
            "projection_schema": "v2",
            "source_of_truth": "projection_v2_raw",
            "projection_v2_raw": fake_v2,
            "legacy_compat": {
                "projection_report": "legacy_fallback",
                "advisory": "legacy_fallback",
            },
            "projection_report": {"kind": "final_projection_report"},
            "notes": ["Projection v2 orchestration chain completed."],
        }

        with patch("services.projection_entrypoint.run_projection_v2", return_value=fake_v2):
            with patch(
                "services.projection_entrypoint.build_projection_entrypoint_result",
                return_value=packaged,
            ):
                with patch(
                    "services.projection_entrypoint.build_projection_narrative",
                    side_effect=RuntimeError("malformed v2 payload"),
                ):
                    result = run_projection_entrypoint(symbol="avgo")

        self.assertEqual(result["projection_v2_raw"], fake_v2)
        self.assertEqual(result["legacy_compat"]["projection_report"], "legacy_fallback")
        self.assertEqual(result["legacy_compat"]["advisory"], "legacy_fallback")
        self.assertEqual(result["projection_report"]["kind"], "final_projection_report")
        self.assertEqual(result["projection_narrative"]["kind"], "projection_narrative")
        self.assertFalse(result["projection_narrative"]["ready"])
        self.assertTrue(any("Projection narrative degraded" in line for line in result["notes"]))

    def test_symbol_validation_is_preserved(self) -> None:
        with self.assertRaises(ValueError):
            run_projection_entrypoint(symbol=" ")


if __name__ == "__main__":
    unittest.main()
