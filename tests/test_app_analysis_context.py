from __future__ import annotations

from datetime import date
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "app_analysis_context_fixture.py"

try:
    import pandas  # noqa: F401
    from streamlit.testing.v1 import AppTest
except ModuleNotFoundError:
    AppTest = None


def _button_by_label(at, label: str):
    for button in at.button:
        if button.label == label:
            return button
    raise AssertionError(f"Button {label!r} not found")


@unittest.skipIf(AppTest is None, "streamlit AppTest or pandas is not installed")
class AppAnalysisContextTest(unittest.TestCase):
    def test_run_analysis_switch_to_empty_code_clears_old_context(self) -> None:
        at = AppTest.from_file(str(FIXTURE)).run(timeout=30)

        at.date_input[0].set_value(date(2026, 4, 9))
        at = _button_by_label(at, "Run Analysis").click().run(timeout=60)

        self.assertFalse(at.exception, msg=f"App raised: {at.exception}")
        self.assertEqual(at.session_state["target_date_str"], "2026-04-09")
        self.assertEqual(at.session_state["target_code"], "15142")
        self.assertEqual(at.session_state["scan_result"]["scan_timestamp"], "2026-04-09")
        self.assertTrue(any(s.value == "Scan Result — 2026-04-09" for s in at.subheader))

        at.date_input[0].set_value(date(2026, 4, 13))
        at = _button_by_label(at, "Run Analysis").click().run(timeout=60)

        self.assertFalse(at.exception, msg=f"App raised: {at.exception}")
        self.assertEqual(at.session_state["target_date_str"], "2026-04-13")
        self.assertEqual(at.session_state["target_code"], "—")
        self.assertIn("5-Digit Code", at.session_state["analysis_error"])
        self.assertNotIn("scan_result", at.session_state)
        self.assertNotIn("target_ctx", at.session_state)
        self.assertTrue(any(s.value == "Scan Result — 2026-04-13" for s in at.subheader))
        self.assertTrue(any("5-Digit Code" in w.value for w in at.warning))

    def test_home_quick_nav_button_switches_to_predict_page(self) -> None:
        at = AppTest.from_file(str(FIXTURE)).run(timeout=30)

        at.date_input[0].set_value(date(2026, 4, 9))
        at = _button_by_label(at, "Run Analysis").click().run(timeout=60)

        self.assertFalse(at.exception, msg=f"App raised: {at.exception}")

        at = _button_by_label(at, "🔮  进入推演页").click().run(timeout=60)

        self.assertFalse(at.exception, msg=f"App raised: {at.exception}")
        self.assertEqual(at.session_state["active_main_view"], "predict")
        self.assertTrue(
            any("博通（AVGO）推演页" in md.value for md in at.markdown),
            msg="Predict page heading not found after quick navigation.",
        )


if __name__ == "__main__":
    unittest.main()
