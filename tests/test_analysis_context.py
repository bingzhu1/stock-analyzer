from __future__ import annotations

import unittest

import pandas as pd

from services.analysis_context import (
    friendly_analysis_error,
    reset_analysis_context_state,
    validate_target_code_for_analysis,
)


class AnalysisContextStateTest(unittest.TestCase):
    def test_reset_clears_old_analysis_and_command_results(self) -> None:
        state = {
            "target_date_str": "2026-04-09",
            "scan_result": {"target_date": "2026-04-09"},
            "target_row": {"Code": "12345"},
            "target_code": "12345",
            "target_ctx": {"pos30": 88.0},
            "match_context": {"pos30": 88.0},
            "exact_df": object(),
            "near_df": object(),
            "cn_cmd_proj_result": {"old": True},
            "cn_cmd_compare_result": {"old": True},
            "cn_cmd_router_result": {"old": True},
            "cn_command_input": "keep widget input",
        }

        reset_analysis_context_state(state, "2026-04-13")

        self.assertEqual(state["target_date_str"], "2026-04-13")
        self.assertEqual(state["target_code"], "—")
        self.assertIsNone(state["analysis_error"])
        self.assertNotIn("scan_result", state)
        self.assertNotIn("target_row", state)
        self.assertNotIn("target_ctx", state)
        self.assertNotIn("match_context", state)
        self.assertNotIn("exact_df", state)
        self.assertNotIn("near_df", state)
        self.assertNotIn("cn_cmd_proj_result", state)
        self.assertNotIn("cn_cmd_compare_result", state)
        self.assertNotIn("cn_cmd_router_result", state)
        self.assertEqual(state["cn_command_input"], "keep widget input")

    def test_validate_target_code_returns_friendly_error_for_empty_code(self) -> None:
        coded_df = pd.DataFrame(
            {
                "Date": pd.to_datetime(["2026-04-09", "2026-04-13"]),
                "Code": ["12345", pd.NA],
            }
        )

        row, code, error = validate_target_code_for_analysis(coded_df, "2026-04-13")

        self.assertIsNotNone(row)
        self.assertEqual(code, "—")
        self.assertIsNotNone(error)
        self.assertIn("2026-04-13", error or "")
        self.assertIn("5-Digit Code", error or "")
        self.assertNotIn("Matching failed", error or "")
        self.assertNotIn("Target date has empty Code", error or "")

    def test_validate_target_code_returns_current_code_for_valid_date(self) -> None:
        coded_df = pd.DataFrame(
            {
                "Date": pd.to_datetime(["2026-04-09", "2026-04-13"]),
                "Code": ["12345", "54321"],
            }
        )

        row, code, error = validate_target_code_for_analysis(coded_df, "2026-04-13")

        self.assertIsNone(error)
        self.assertEqual(code, "54321")
        self.assertEqual(str(row["Code"]), "54321")

    def test_friendly_analysis_error_hides_low_level_empty_code_message(self) -> None:
        error = friendly_analysis_error(
            "Matching",
            ValueError("Target date has empty Code and cannot be matched: 2026-04-13"),
            "2026-04-13",
        )

        self.assertIn("2026-04-13", error)
        self.assertIn("5-Digit Code", error)
        self.assertNotIn("Matching failed", error)
        self.assertNotIn("Target date has empty Code", error)


if __name__ == "__main__":
    unittest.main()
