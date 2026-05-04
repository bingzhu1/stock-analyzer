"""Tests for the Step 2G-6C Review-tab soft-metadata attribution helpers.

Covers:
- ``_classify_review_attribution`` 4 outcome × metadata combinations
  (Step 2G-6 §8)
- ``build_review_soft_metadata_card_data`` returns renderer card_data
  augmented with ``review_attribution`` band; never mutates input;
  visibility rules are honored
- ``render_review_soft_metadata_section`` calls ``st.markdown`` only
  when visible; produces no forbidden copy; never raises
- AppTest integration: review-context page text contains the safe
  attribution band and no forbidden words
"""
from __future__ import annotations

import sys
import textwrap
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.review_tab import (
    _classify_review_attribution,
    build_review_soft_metadata_card_data,
    render_review_soft_metadata_section,
)
from ui.soft_metadata_renderer import FORBIDDEN_COPY_TOKENS

try:
    from streamlit.testing.v1 import AppTest
except ModuleNotFoundError:
    AppTest = None  # type: ignore[assignment]


# ── fixtures ────────────────────────────────────────────────────────────

def _r4_signal() -> dict:
    return {
        "name": "r4_overextension",
        "display_label": "高位跑赢同行后的偏多过热",
        "severity": "medium",
        "dedup_group": "bullish_overextension",
        "raw_features": {"avgo_minus_soxx_20d": 7.3, "pos20": 0.81},
        "trigger_context": {
            "final_direction": "偏多", "confidence_level": "high",
            "primary_score_raw": 2.7, "matched_or_branch": "both",
            "peer_subtype": "upgrade",
        },
        "historical_metrics_in_sample": {
            "samples": 36, "paired": 34,
            "accuracy": 0.324, "bias_gap": 0.676,
            "false_exclusion_rate": 0.3235, "net_benefit": 0.0219,
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


def _shell(signals: list[dict] | None = None,
           warnings: list[str] | None = None) -> dict:
    sig_list = signals or []
    return {
        "schema_version": "soft_metadata.v1",
        "metrics_source": "regime_diagnostics_dashboard_v1",
        "metrics_window": {
            "analysis_date_min": "2023-01-03",
            "analysis_date_max": "2024-08-02",
            "paired_total": 286, "db_snapshot_id": None,
        },
        "metrics_computed_at": "2026-05-04T00:00:00",
        "signals": sig_list,
        "summary": {
            "has_overextension_signal": bool(sig_list),
            "max_severity": "medium" if sig_list else "none",
            "hard_exclusion_allowed": False,
            "signal_count": len(sig_list),
            "primary_signal": sig_list[0]["name"] if sig_list else None,
            "warnings": list(warnings or []),
        },
    }


# ── _classify_review_attribution (Step 2G-6 §8 4-quadrant) ─────────────

class ClassifyReviewAttributionTests(unittest.TestCase):
    def test_signals_present_wrong_yields_possible_attribution(self) -> None:
        sm = _shell(signals=[_r4_signal()])
        self.assertEqual(
            _classify_review_attribution(sm, prediction_correct=False),
            "possible_attribution",
        )

    def test_signals_present_correct_yields_triggered_but_not_error(self) -> None:
        sm = _shell(signals=[_r4_signal()])
        self.assertEqual(
            _classify_review_attribution(sm, prediction_correct=True),
            "triggered_but_not_error",
        )

    def test_no_signals_wrong_yields_no_attribution(self) -> None:
        sm = _shell(signals=[])
        self.assertEqual(
            _classify_review_attribution(sm, prediction_correct=False),
            "no_attribution",
        )

    def test_no_signals_correct_yields_no_metadata(self) -> None:
        sm = _shell(signals=[])
        self.assertEqual(
            _classify_review_attribution(sm, prediction_correct=True),
            "no_metadata",
        )

    def test_signals_present_pending_outcome_falls_back_to_triggered(self) -> None:
        sm = _shell(signals=[_r4_signal()])
        self.assertEqual(
            _classify_review_attribution(sm, prediction_correct=None),
            "triggered_but_not_error",
        )

    def test_no_signals_pending_outcome_yields_no_metadata(self) -> None:
        sm = _shell(signals=[])
        self.assertEqual(
            _classify_review_attribution(sm, prediction_correct=None),
            "no_metadata",
        )

    def test_non_dict_input_treated_as_no_signals(self) -> None:
        self.assertEqual(
            _classify_review_attribution(None, prediction_correct=False),
            "no_attribution",
        )
        self.assertEqual(
            _classify_review_attribution("garbage", prediction_correct=True),
            "no_metadata",
        )


# ── build_review_soft_metadata_card_data ───────────────────────────────

class BuildReviewCardDataTests(unittest.TestCase):
    def test_card_data_includes_review_attribution_block(self) -> None:
        sm = _shell(signals=[_r4_signal()])
        cd = build_review_soft_metadata_card_data(sm, prediction_correct=False)
        self.assertIn("review_attribution", cd)
        attr = cd["review_attribution"]
        self.assertEqual(attr["kind"], "possible_attribution")
        self.assertIn("候选", attr["label"])
        self.assertIn("不是确定原因", attr["explanation"])

    def test_review_context_uses_review_title(self) -> None:
        sm = _shell(signals=[_r4_signal()])
        cd = build_review_soft_metadata_card_data(sm, prediction_correct=False)
        # The renderer's review-context title is "结构性偏多归因维度（候选）"
        self.assertIn("候选", cd["title"])

    def test_no_attribution_path_forces_visible_subtitle(self) -> None:
        # signals=[] + wrong → renderer would normally still show the
        # review empty state; the helper guarantees visible=True with
        # the "no_attribution" label as the subtitle so the user sees
        # explicit guidance.
        sm = _shell(signals=[])
        cd = build_review_soft_metadata_card_data(sm, prediction_correct=False)
        self.assertTrue(cd["visible"])
        self.assertIn("不强行归因", cd["review_attribution"]["explanation"])

    def test_no_metadata_correct_predict_review_context_visible(self) -> None:
        # Review context default for empty signals shows "未触发 soft
        # metadata"; that's the no_metadata kind.
        sm = _shell(signals=[])
        cd = build_review_soft_metadata_card_data(sm, prediction_correct=True)
        self.assertTrue(cd["visible"])  # renderer review default
        self.assertEqual(cd["review_attribution"]["kind"], "no_metadata")

    def test_input_dict_is_not_mutated(self) -> None:
        sm = _shell(signals=[_r4_signal()])
        snapshot = deepcopy(sm)
        build_review_soft_metadata_card_data(sm, prediction_correct=False)
        self.assertEqual(sm, snapshot)

    def test_none_input_does_not_crash(self) -> None:
        cd = build_review_soft_metadata_card_data(None, prediction_correct=None)
        self.assertIn("review_attribution", cd)
        self.assertEqual(cd["review_attribution"]["kind"], "no_metadata")


# ── render_review_soft_metadata_section: st.markdown wiring ────────────

class RenderReviewSectionTests(unittest.TestCase):
    def test_visible_card_calls_st_markdown_at_least_once(self) -> None:
        sm = _shell(signals=[_r4_signal()])
        with patch("ui.review_tab.st") as st_mock:
            cd = render_review_soft_metadata_section(
                sm, prediction_correct=False,
            )
        self.assertTrue(cd["visible"])
        self.assertGreaterEqual(st_mock.markdown.call_count, 1)

    def test_no_metadata_correct_review_renders_empty_state(self) -> None:
        sm = _shell(signals=[])
        with patch("ui.review_tab.st") as st_mock:
            cd = render_review_soft_metadata_section(
                sm, prediction_correct=True,
            )
        self.assertTrue(cd["visible"])  # review empty state visible
        # markdown still called at least once for the empty-state band
        self.assertGreaterEqual(st_mock.markdown.call_count, 1)

    def test_section_does_not_raise_on_garbage_input(self) -> None:
        with patch("ui.review_tab.st"):
            cd = render_review_soft_metadata_section(
                "not a dict", prediction_correct=None,
            )  # type: ignore[arg-type]
        self.assertIn("review_attribution", cd)


# ── 16 forbidden-word lock ─────────────────────────────────────────────

class ReviewForbiddenCopyTests(unittest.TestCase):
    def _capture_markdown(self, sm, *, prediction_correct):
        with patch("ui.review_tab.st") as st_mock:
            render_review_soft_metadata_section(
                sm, prediction_correct=prediction_correct,
            )
        return "\n".join(
            call.args[0] for call in st_mock.markdown.call_args_list
            if call.args
        )

    def _assert_clean(self, text: str) -> None:
        for token in FORBIDDEN_COPY_TOKENS:
            self.assertNotIn(
                token, text,
                f"forbidden token {token!r} reached review st.markdown",
            )

    def test_no_forbidden_in_possible_attribution(self) -> None:
        self._assert_clean(self._capture_markdown(
            _shell(signals=[_r4_signal()]), prediction_correct=False,
        ))

    def test_no_forbidden_in_triggered_but_not_error(self) -> None:
        self._assert_clean(self._capture_markdown(
            _shell(signals=[_r4_signal()]), prediction_correct=True,
        ))

    def test_no_forbidden_in_no_attribution(self) -> None:
        self._assert_clean(self._capture_markdown(
            _shell(signals=[]), prediction_correct=False,
        ))

    def test_no_forbidden_in_no_metadata_correct(self) -> None:
        self._assert_clean(self._capture_markdown(
            _shell(signals=[]), prediction_correct=True,
        ))

    def test_no_forbidden_for_final_test_refusal(self) -> None:
        sm = _shell(warnings=["final_test_range_refusal"])
        self._assert_clean(self._capture_markdown(
            sm, prediction_correct=None,
        ))


# ── final_test_refusal visibility in review context ────────────────────

class FinalTestRefusalReviewTests(unittest.TestCase):
    def test_final_test_refusal_keeps_section_visible(self) -> None:
        sm = _shell(warnings=["final_test_range_refusal"])
        with patch("ui.review_tab.st") as st_mock:
            cd = render_review_soft_metadata_section(
                sm, prediction_correct=False,
            )
        self.assertTrue(cd["visible"])
        rendered = "\n".join(
            call.args[0] for call in st_mock.markdown.call_args_list
            if call.args
        )
        self.assertIn("final test 保留区间", rendered)


# ── unknown signal graceful degradation in review context ──────────────

class UnknownSignalReviewTests(unittest.TestCase):
    def test_unknown_signal_name_renders_generic_card(self) -> None:
        sig = _r4_signal()
        sig["name"] = "wholly_made_up"
        sm = _shell(signals=[sig])
        with patch("ui.review_tab.st") as st_mock:
            cd = render_review_soft_metadata_section(
                sm, prediction_correct=False,
            )
        self.assertTrue(cd["visible"])
        self.assertEqual(
            cd["review_attribution"]["kind"], "possible_attribution",
        )
        rendered = "\n".join(
            c.args[0] for c in st_mock.markdown.call_args_list if c.args
        )
        self.assertIn("未识别", rendered)


# ── isolation: no DB / no simulator / no forbidden imports ─────────────

class ReviewTabIsolationTests(unittest.TestCase):
    def test_render_section_does_not_call_simulator_or_db(self) -> None:
        sm = _shell(signals=[_r4_signal()])
        with patch("services.soft_metadata_simulator.simulate_soft_metadata") as sim, \
             patch("services.soft_metadata_simulator.build_soft_metadata_baseline") as bs, \
             patch("services.prediction_store.save_prediction") as sp, \
             patch("services.prediction_store._get_conn") as gc, \
             patch("ui.review_tab.st"):
            render_review_soft_metadata_section(sm, prediction_correct=False)
        sim.assert_not_called()
        bs.assert_not_called()
        sp.assert_not_called()
        gc.assert_not_called()

    def test_review_tab_does_not_import_simulator_or_injection(self) -> None:
        # The review tab consumes the renderer only — it must NOT
        # import the simulator or the injection helper. (If a future
        # surface needs enrichment, it should call the existing helper
        # from services/, not pull simulator into ui/review_tab.)
        import ast
        import ui.review_tab as mod
        tree = ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))
        forbidden = {
            "yfinance", "requests", "longbridge", "broker", "paper_trade",
            "sqlite3",
            "services.soft_metadata_simulator",
            "services.soft_metadata_injection",
            "services.confidence_engine",
            "services.contradiction_engine",
            "services.risk_model",
            "confidence_engine", "contradiction_engine", "risk_model",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(alias.name, forbidden)
            elif isinstance(node, ast.ImportFrom):
                self.assertNotIn(node.module, forbidden)


# ── AppTest integration ────────────────────────────────────────────────

@unittest.skipIf(AppTest is None,
                 "streamlit AppTest is not installed in this environment")
class ReviewSoftMetadataAppTests(unittest.TestCase):
    @staticmethod
    def _script(soft_repr: str, predict_correct_repr: str) -> str:
        return textwrap.dedent(
            f"""
            import sys
            sys.path.insert(0, {str(ROOT)!r})

            from ui.review_tab import render_review_soft_metadata_section

            sm = {soft_repr}
            render_review_soft_metadata_section(
                sm, prediction_correct={predict_correct_repr},
            )
            """
        )

    def _all_markdown(self, at) -> str:
        return "\n".join(str(m.value) for m in at.markdown)

    def test_apptest_wrong_with_r4_renders_possible_attribution(self) -> None:
        sm = _shell(signals=[_r4_signal()])
        at = AppTest.from_string(self._script(repr(sm), "False")).run()
        text = self._all_markdown(at)
        self.assertIn("可能归因维度", text)
        self.assertIn("不是确定原因", text)
        self.assertIn("高位跑赢同行后的偏多过热", text)
        for token in FORBIDDEN_COPY_TOKENS:
            self.assertNotIn(token, text)

    def test_apptest_correct_with_r4_renders_survival_band(self) -> None:
        sm = _shell(signals=[_r4_signal()])
        at = AppTest.from_string(self._script(repr(sm), "True")).run()
        text = self._all_markdown(at)
        self.assertIn("结构幸存", text)
        for token in FORBIDDEN_COPY_TOKENS:
            self.assertNotIn(token, text)

    def test_apptest_correct_with_r4_anti_false_section_includes_survival(self) -> None:
        # Step 2G-7B Review integration — when correct + R4, the anti-
        # false sidecar emits r4_survival_case + gate-fail findings.
        # We exercise the helper directly via AppTest (mirrors the
        # _render_review_result block).
        from ui.anti_false_exclusion_display import FORBIDDEN_COPY_TOKENS as AFX_FORBIDDEN
        sm = _shell(signals=[_r4_signal()])
        script = textwrap.dedent(
            f"""
            import sys
            sys.path.insert(0, {str(ROOT)!r})

            import streamlit as st
            from ui.review_tab import render_review_soft_metadata_section
            from ui.anti_false_exclusion_display import (
                build_anti_false_exclusion_display,
                render_anti_false_exclusion_markdown,
            )

            sm = {sm!r}
            render_review_soft_metadata_section(sm, prediction_correct=True)
            if isinstance(sm, dict) and sm.get('signals'):
                afx = build_anti_false_exclusion_display(
                    sm, prediction_correct=True,
                )
                if afx.get('visible'):
                    with st.expander('保护层诊断', expanded=False):
                        st.markdown(render_anti_false_exclusion_markdown(afx))
            """
        )
        at = AppTest.from_string(script).run()
        text = self._all_markdown(at)
        labels = " ".join(
            getattr(el, "label", "") or "" for el in getattr(at, "expander", [])
        )
        self.assertIn("保护层诊断", labels)
        self.assertIn("结构幸存", text)  # survival case wording
        self.assertIn("32.4%", text)     # gate-fail evidence
        # Page-level grep uses the renderer 16 tokens only; AFX-only
        # stricter tokens (hard / forced / 排除 standalone) are locked
        # in tests/test_anti_false_exclusion_display.py against the
        # AFX markdown alone — checking them at page level would trip
        # on the renderer's existing "误杀率（若强制排除）" label.
        del AFX_FORBIDDEN  # noqa: F841 — imported above; suppress unused
        for token in FORBIDDEN_COPY_TOKENS:
            self.assertNotIn(token, text)

    def test_apptest_wrong_with_r4_anti_false_section_includes_gate_fail(self) -> None:
        from ui.anti_false_exclusion_display import FORBIDDEN_COPY_TOKENS as AFX_FORBIDDEN
        sm = _shell(signals=[_r4_signal()])
        script = textwrap.dedent(
            f"""
            import sys
            sys.path.insert(0, {str(ROOT)!r})

            import streamlit as st
            from ui.review_tab import render_review_soft_metadata_section
            from ui.anti_false_exclusion_display import (
                build_anti_false_exclusion_display,
                render_anti_false_exclusion_markdown,
            )

            sm = {sm!r}
            render_review_soft_metadata_section(sm, prediction_correct=False)
            if isinstance(sm, dict) and sm.get('signals'):
                afx = build_anti_false_exclusion_display(
                    sm, prediction_correct=False,
                )
                if afx.get('visible'):
                    with st.expander('保护层诊断', expanded=False):
                        st.markdown(render_anti_false_exclusion_markdown(afx))
            """
        )
        at = AppTest.from_string(script).run()
        text = self._all_markdown(at)
        # wrong + R4 → no survival case; should still include gate-fail
        # evidence and the missing_protection_layer finding.
        self.assertNotIn("结构幸存", text)
        self.assertIn("误杀风险较高", text)
        self.assertIn("保护层未接入", text)
        # Page-level grep uses the renderer 16 tokens only; AFX-only
        # stricter tokens (hard / forced / 排除 standalone) are locked
        # in tests/test_anti_false_exclusion_display.py against the
        # AFX markdown alone — checking them at page level would trip
        # on the renderer's existing "误杀率（若强制排除）" label.
        del AFX_FORBIDDEN  # noqa: F841 — imported above; suppress unused
        for token in FORBIDDEN_COPY_TOKENS:
            self.assertNotIn(token, text)

    def test_apptest_wrong_no_metadata_renders_no_attribution_band(self) -> None:
        sm = _shell(signals=[])
        at = AppTest.from_string(self._script(repr(sm), "False")).run()
        text = self._all_markdown(at)
        self.assertIn("不强行归因", text)
        for token in FORBIDDEN_COPY_TOKENS:
            self.assertNotIn(token, text)


if __name__ == "__main__":
    unittest.main()
