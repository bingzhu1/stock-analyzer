"""Tests for the Step 2G-6B Predict-tab soft-metadata display hook.

Covers:
- ``_extract_soft_metadata`` walks the documented search order and is
  defensive on bad input
- ``render_soft_metadata_section`` consumes the renderer (no simulator,
  no DB, no network) and produces no forbidden copy
- AppTest-based integration: when session_state holds soft_metadata,
  the renderer's safe markdown appears in the page; when it does not,
  the predict-context visibility rule hides the section
"""
from __future__ import annotations

import sys
import textwrap
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.predict_tab import (
    _extract_soft_metadata,
    render_soft_metadata_section,
)
from ui.soft_metadata_renderer import FORBIDDEN_COPY_TOKENS

try:
    from streamlit.testing.v1 import AppTest
except ModuleNotFoundError:
    AppTest = None  # type: ignore[assignment]


# ── fixtures ────────────────────────────────────────────────────────────

def _r4_soft_metadata() -> dict:
    return {
        "schema_version": "soft_metadata.v1",
        "metrics_source": "regime_diagnostics_dashboard_v1",
        "metrics_window": {
            "analysis_date_min": "2023-01-03",
            "analysis_date_max": "2024-08-02",
            "paired_total": 286, "db_snapshot_id": None,
        },
        "metrics_computed_at": "2026-05-04T00:00:00",
        "signals": [
            {
                "name": "r4_overextension",
                "display_label": "高位跑赢同行后的偏多过热",
                "severity": "medium",
                "dedup_group": "bullish_overextension",
                "raw_features": {
                    "avgo_minus_soxx_20d": 7.3, "pos20": 0.81,
                },
                "trigger_context": {
                    "final_direction": "偏多",
                    "confidence_level": "high",
                    "primary_score_raw": 2.7,
                    "matched_or_branch": "both",
                    "peer_subtype": "upgrade",
                },
                "historical_metrics_in_sample": {
                    "samples": 36, "paired": 34,
                    "accuracy": 0.324, "bias_gap": 0.676,
                    "false_exclusion_rate": 0.3235,
                    "net_benefit": 0.0219,
                },
                "holdout_status": "FAIL",
                "recommended_action": "review_only",
                "hard_forbidden_primary_reason": "false_exclusion_rate_too_high",
                "hard_forbidden_breakdown": [
                    "false_exclusion_rate=0.3235 > 0.10",
                    "net_benefit=0.0219 < 0.05",
                    "anti_false_exclusion_not_connected",
                ],
            }
        ],
        "summary": {
            "has_overextension_signal": True,
            "max_severity": "medium",
            "hard_exclusion_allowed": False,
            "signal_count": 1,
            "primary_signal": "r4_overextension",
            "warnings": [],
        },
    }


def _empty_soft_metadata() -> dict:
    return {
        "schema_version": "soft_metadata.v1",
        "metrics_source": "regime_diagnostics_dashboard_v1",
        "metrics_window": {
            "analysis_date_min": None, "analysis_date_max": None,
            "paired_total": 0, "db_snapshot_id": None,
        },
        "metrics_computed_at": "2026-05-04T00:00:00",
        "signals": [],
        "summary": {
            "has_overextension_signal": False,
            "max_severity": "none",
            "hard_exclusion_allowed": False,
            "signal_count": 0,
            "primary_signal": None,
            "warnings": [],
        },
    }


def _final_test_refusal_soft_metadata() -> dict:
    sm = _empty_soft_metadata()
    sm["summary"]["warnings"] = ["final_test_range_refusal"]
    return sm


# ── _extract_soft_metadata ──────────────────────────────────────────────

class ExtractSoftMetadataTests(unittest.TestCase):
    def test_none_input_returns_none(self) -> None:
        self.assertIsNone(_extract_soft_metadata(None))

    def test_non_dict_input_returns_none(self) -> None:
        self.assertIsNone(_extract_soft_metadata("string"))  # type: ignore[arg-type]
        self.assertIsNone(_extract_soft_metadata(123))  # type: ignore[arg-type]

    def test_extracts_from_contract_payload_extras_canonical_path(self) -> None:
        sm = _r4_soft_metadata()
        pr = {
            "contract_payload": {
                "exclusion_system": {
                    "extras": {"soft_metadata": sm}
                }
            }
        }
        self.assertIs(_extract_soft_metadata(pr), sm)

    def test_extracts_from_top_level_predict_result_field(self) -> None:
        sm = _r4_soft_metadata()
        pr = {"soft_metadata": sm}
        self.assertIs(_extract_soft_metadata(pr), sm)

    def test_canonical_path_takes_precedence_over_top_level(self) -> None:
        sm_canon = _r4_soft_metadata()
        sm_top = _empty_soft_metadata()
        pr = {
            "contract_payload": {
                "exclusion_system": {
                    "extras": {"soft_metadata": sm_canon}
                }
            },
            "soft_metadata": sm_top,
        }
        self.assertIs(_extract_soft_metadata(pr), sm_canon)

    def test_malformed_extras_returns_none(self) -> None:
        pr = {
            "contract_payload": {
                "exclusion_system": {"extras": "not a dict"}
            }
        }
        self.assertIsNone(_extract_soft_metadata(pr))

    def test_session_state_lookup_when_streamlit_unavailable(self) -> None:
        # When called outside a Streamlit context, st.session_state.get
        # may raise; the helper must swallow that and return None.
        result = _extract_soft_metadata({})
        self.assertIsNone(result)


# ── render_soft_metadata_section ────────────────────────────────────────

class RenderSectionUnitTests(unittest.TestCase):
    """The section function is a thin wrapper around the renderer.

    We patch ``ui.predict_tab.st`` to capture markdown calls without
    needing a running Streamlit context."""

    def test_none_input_returns_hidden_card_data_no_markdown_call(self) -> None:
        with patch("ui.predict_tab.st") as st_mock:
            cd = render_soft_metadata_section(None)
        self.assertFalse(cd["visible"])
        st_mock.markdown.assert_not_called()

    def test_empty_signals_predict_context_hidden(self) -> None:
        with patch("ui.predict_tab.st") as st_mock:
            cd = render_soft_metadata_section(_empty_soft_metadata())
        self.assertFalse(cd["visible"])
        st_mock.markdown.assert_not_called()

    def test_non_dict_input_treated_as_hidden(self) -> None:
        for bad in ("string", 123, [], object()):
            with patch("ui.predict_tab.st") as st_mock:
                cd = render_soft_metadata_section(bad)  # type: ignore[arg-type]
            self.assertFalse(cd["visible"])
            st_mock.markdown.assert_not_called()

    def test_r4_signal_calls_st_markdown_with_safe_text(self) -> None:
        with patch("ui.predict_tab.st") as st_mock:
            cd = render_soft_metadata_section(_r4_soft_metadata())
        self.assertTrue(cd["visible"])
        st_mock.markdown.assert_called_once()
        rendered_md = st_mock.markdown.call_args.args[0]
        self.assertIn("高位跑赢同行后的偏多过热", rendered_md)
        self.assertIn("不改变主推演方向", rendered_md)

    def test_final_test_refusal_visible_and_displays_subtitle(self) -> None:
        with patch("ui.predict_tab.st") as st_mock:
            cd = render_soft_metadata_section(_final_test_refusal_soft_metadata())
        self.assertTrue(cd["visible"])
        self.assertIn("final_test_range_refusal", cd["warnings"])
        st_mock.markdown.assert_called_once()
        rendered_md = st_mock.markdown.call_args.args[0]
        self.assertIn("final test 保留区间", rendered_md)

    def test_no_forbidden_words_in_rendered_markdown(self) -> None:
        for sm in (_r4_soft_metadata(),
                   _final_test_refusal_soft_metadata(),
                   _empty_soft_metadata()):
            with patch("ui.predict_tab.st") as st_mock:
                render_soft_metadata_section(sm)
            for call in st_mock.markdown.call_args_list:
                rendered = call.args[0]
                for token in FORBIDDEN_COPY_TOKENS:
                    self.assertNotIn(
                        token, rendered,
                        f"forbidden token {token!r} reached st.markdown",
                    )


# ── isolation: section does NOT call simulator / DB / network ──────────

class IsolationTests(unittest.TestCase):
    def test_section_does_not_call_simulator(self) -> None:
        # Patch the simulator module's public functions; they must NEVER
        # be invoked from the predict-tab display hook.
        with patch("services.soft_metadata_simulator.simulate_soft_metadata") as sim, \
             patch("services.soft_metadata_simulator.build_soft_metadata_baseline") as bs, \
             patch("ui.predict_tab.st"):
            render_soft_metadata_section(_r4_soft_metadata())
            render_soft_metadata_section(None)
        sim.assert_not_called()
        bs.assert_not_called()

    def test_section_does_not_call_prediction_store(self) -> None:
        with patch("services.prediction_store.save_prediction") as sp, \
             patch("services.prediction_store._get_conn") as gc, \
             patch("ui.predict_tab.st"):
            render_soft_metadata_section(_r4_soft_metadata())
        sp.assert_not_called()
        gc.assert_not_called()

    def test_predict_tab_module_does_not_import_simulator(self) -> None:
        # The predict-tab module's import surface must not pull in the
        # simulator (it would imply the page can compute soft_metadata
        # on the fly, violating Step 2G-6B §2).
        import ast
        import ui.predict_tab as mod
        tree = ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))
        forbidden = {
            "services.soft_metadata_simulator",
            "soft_metadata_simulator",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(alias.name, forbidden)
            elif isinstance(node, ast.ImportFrom):
                self.assertNotIn(node.module, forbidden)


# ── hard_exclusion / severity safety ───────────────────────────────────

class HardExclusionSafetyTests(unittest.TestCase):
    def test_hard_exclusion_allowed_false_does_not_render_hard_or_no_trade(self) -> None:
        with patch("ui.predict_tab.st") as st_mock:
            render_soft_metadata_section(_r4_soft_metadata())
        rendered = st_mock.markdown.call_args.args[0]
        for token in ("hard exclusion", "forced exclusion", "no_trade",
                      "禁止交易", "强制否定"):
            self.assertNotIn(token, rendered)

    def test_unknown_signal_graceful_no_crash(self) -> None:
        sm = _r4_soft_metadata()
        sm["signals"][0]["name"] = "wholly_made_up"
        with patch("ui.predict_tab.st") as st_mock:
            cd = render_soft_metadata_section(sm)
        self.assertTrue(cd["visible"])
        rendered = st_mock.markdown.call_args.args[0]
        self.assertIn("未识别", rendered)


# ── AppTest integration ─────────────────────────────────────────────────

@unittest.skipIf(AppTest is None,
                 "streamlit AppTest is not installed in this environment")
class PredictTabAppTests(unittest.TestCase):
    """Integration: drive ``render_soft_metadata_section`` via a minimal
    Streamlit script using AppTest. We do NOT render the full
    ``render_predict_tab`` (it requires scan_result + run_predict + DB
    state); instead we test the hook in isolation, which is what
    Step 2G-6B introduces."""

    @staticmethod
    def _script(injection: str) -> str:
        return textwrap.dedent(
            f"""
            import sys
            sys.path.insert(0, {str(ROOT)!r})

            import streamlit as st
            from ui.predict_tab import render_soft_metadata_section

            sm = {injection}
            render_soft_metadata_section(sm)
            """
        )

    def _all_markdown(self, at) -> str:
        return "\n".join(str(m.value) for m in at.markdown)

    def test_apptest_r4_card_renders_safe_markdown(self) -> None:
        sm_dict = _r4_soft_metadata()
        at = AppTest.from_string(self._script(repr(sm_dict))).run()
        text = self._all_markdown(at)
        self.assertIn("高位跑赢同行后的偏多过热", text)
        self.assertIn("不改变主推演方向", text)
        self.assertIn("32.4%", text)
        for token in FORBIDDEN_COPY_TOKENS:
            self.assertNotIn(token, text)

    def test_apptest_empty_signals_hides_card(self) -> None:
        sm_dict = _empty_soft_metadata()
        at = AppTest.from_string(self._script(repr(sm_dict))).run()
        text = self._all_markdown(at)
        # Hidden in predict context — neither the title nor the empty
        # state copy should appear
        self.assertNotIn("结构性偏多风险提示", text)
        self.assertNotIn("未触发 soft metadata", text)

    def test_apptest_final_test_refusal_visible(self) -> None:
        sm_dict = _final_test_refusal_soft_metadata()
        at = AppTest.from_string(self._script(repr(sm_dict))).run()
        text = self._all_markdown(at)
        self.assertIn("final test 保留区间", text)
        for token in FORBIDDEN_COPY_TOKENS:
            self.assertNotIn(token, text)

    def test_apptest_none_input_renders_nothing(self) -> None:
        at = AppTest.from_string(self._script("None")).run()
        text = self._all_markdown(at)
        self.assertEqual(text.strip(), "")


if __name__ == "__main__":
    unittest.main()
