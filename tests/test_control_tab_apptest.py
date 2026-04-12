from __future__ import annotations

from pathlib import Path
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]

try:
    import pandas  # noqa: F401
    from streamlit.testing.v1 import AppTest
except ModuleNotFoundError:
    AppTest = None


def _script(has_analysis: bool) -> str:
    scan_result = (
        """
scan_result = {
    "scan_bias": "bullish",
    "scan_confidence": "medium",
    "historical_match_summary": {"exact_match_count": 2, "near_match_count": 1},
}
exact_df = pd.DataFrame([
    {"MatchType": "exact", "MatchDate": "2025-01-02", "ContextScore": 82.0,
     "ContextLabel": "高相似", "NextCloseMove": 0.031},
])
near_df = pd.DataFrame([
    {"MatchType": "near", "MatchDate": "2025-03-04", "ContextScore": 67.0,
     "ContextLabel": "高相似", "NextCloseMove": 0.005},
])
"""
        if has_analysis
        else """
scan_result = None
exact_df = pd.DataFrame()
near_df = pd.DataFrame()
"""
    )
    return textwrap.dedent(
        f"""
        import sys
        sys.path.insert(0, {str(ROOT)!r})
        import pandas as pd
        from services.query_executor import AnalysisContext
        from ui.control_tab import render_control_tab

        {textwrap.indent(scan_result.strip(), "        ").strip()}

        render_control_tab(
            AnalysisContext(
                target_date_str="2026-04-08",
                scan_result=scan_result,
                exact_df=exact_df,
                near_df=near_df,
                summary_df=pd.DataFrame(),
                disp_exact_df=exact_df,
                disp_near_df=near_df,
            )
        )
        """
    )


@unittest.skipIf(AppTest is None, "streamlit AppTest or pandas is not installed")
class ControlTabAppTests(unittest.TestCase):
    def test_empty_state_shows_scope_help_and_warning(self) -> None:
        at = AppTest.from_string(_script(has_analysis=False)).run()

        self.assertTrue(any("Default query scope" in item.value for item in at.info))
        self.assertTrue(any("No analysis is loaded yet" in item.value for item in at.warning))
        self.assertTrue(any("Supported read-only commands" in item.value for item in at.markdown))

    def test_chat_help_request_returns_schema_help(self) -> None:
        at = AppTest.from_string(_script(has_analysis=True)).run()
        at.chat_input[0].set_value("help").run()

        markdown_text = "\n".join(item.value for item in at.markdown)
        self.assertIn("Supported read-only commands", markdown_text)
        self.assertIn("Scopes:", markdown_text)
        self.assertIn("Examples:", markdown_text)


if __name__ == "__main__":
    unittest.main()
