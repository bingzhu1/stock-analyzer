"""Hygiene tests for ``tests/fixtures/app_analysis_context_fixture.py``.

Step 14F (RISK-7 wave): the AppTest fixture used to monkeypatch
``predict.run_predict`` / ``scanner.run_scan`` / ``matcher.*`` /
``stats_reporter.*`` at import-time without restoring them. Any test that
ran later in the same pytest session would observe the fakes, which is
why every X1+ boundary test file carries a ``_fresh_predict_module()``
``importlib.reload`` defence.

These tests pin the source-side restore. After the fixture runs (via
``AppTest.from_file``), the bound attributes on the genuine modules must
be back to the originals — so future boundary tests can read them
directly without the reload defence (the defence itself is left in place
this round per Step 14E §9.10).

Design contract: tasks/record_14e_test_fixture_hygiene_plan.md §8.1.
"""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "app_analysis_context_fixture.py"

try:
    import pandas  # noqa: F401
    from streamlit.testing.v1 import AppTest
except ModuleNotFoundError:
    AppTest = None


@unittest.skipIf(AppTest is None, "streamlit AppTest or pandas is not installed")
class AppAnalysisContextFixtureHygieneTest(unittest.TestCase):
    """Each test captures the genuine module attribute, runs the fixture
    via AppTest, and then asserts the attribute is restored to the
    original — proving the fixture's try/finally hygiene block did its
    job."""

    def _run_fixture(self) -> None:
        AppTest.from_file(str(FIXTURE)).run(timeout=30)

    def test_app_analysis_context_fixture_restores_predict_run_predict(self) -> None:
        import predict

        original = predict.run_predict
        self._run_fixture()
        self.assertIs(
            predict.run_predict,
            original,
            msg="predict.run_predict must be restored after the fixture runs",
        )

    def test_app_analysis_context_fixture_restores_scanner_and_matcher(self) -> None:
        import matcher
        import scanner

        originals = {
            ("scanner", "run_scan"): scanner.run_scan,
            ("matcher", "load_coded_avgo"): matcher.load_coded_avgo,
            ("matcher", "build_next_day_match_table"): matcher.build_next_day_match_table,
            ("matcher", "build_near_match_table"): matcher.build_near_match_table,
            ("matcher", "save_match_results"): matcher.save_match_results,
            ("matcher", "save_near_match_results"): matcher.save_near_match_results,
        }

        self._run_fixture()

        modules = {"scanner": scanner, "matcher": matcher}
        for (mod_name, attr), original in originals.items():
            current = getattr(modules[mod_name], attr)
            self.assertIs(
                current,
                original,
                msg=f"{mod_name}.{attr} must be restored after the fixture runs",
            )

    def test_app_analysis_context_fixture_restores_stats_reporter(self) -> None:
        import stats_reporter

        originals = {
            "build_stats_summary": stats_reporter.build_stats_summary,
            "save_stats_summary": stats_reporter.save_stats_summary,
        }

        self._run_fixture()

        for attr, original in originals.items():
            self.assertIs(
                getattr(stats_reporter, attr),
                original,
                msg=f"stats_reporter.{attr} must be restored after the fixture runs",
            )

    def test_app_analysis_context_fixture_does_not_break_app_context_test(self) -> None:
        """Smoke check: running the fixture twice in a row must still
        succeed (the existing AppAnalysisContextTest also calls the
        fixture twice via separate test methods — restore must be
        idempotent)."""
        self._run_fixture()
        self._run_fixture()


if __name__ == "__main__":
    unittest.main()
