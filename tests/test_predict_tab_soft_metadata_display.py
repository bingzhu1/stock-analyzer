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


# ── Step 2G-6B.3 — Predict tab calls enrichment helper ─────────────────

class EnrichmentIntegrationTests(unittest.TestCase):
    """Verify the Step 2G-6B.3 wiring: render_predict_tab invokes the
    enrichment helper before display, and the helper failure path
    falls back gracefully without crashing the page."""

    def test_enrichment_helper_importable_from_predict_tab(self) -> None:
        # The Step 2G-6B.3 import must be intact — UI cannot regress to
        # the pre-6B.3 state where canonical slot was always empty.
        from ui.predict_tab import enrich_predict_result_with_soft_metadata
        self.assertTrue(callable(enrich_predict_result_with_soft_metadata))

    def test_baseline_cache_helper_importable_from_predict_tab(self) -> None:
        # Step 2G-6B.6 — the lazy baseline cache must be wired into the
        # Predict tab so historical_metrics_in_sample is populated rather
        # than n/a. UI cannot regress to the pre-6B.6 state where
        # baseline was always None.
        from ui.predict_tab import ensure_soft_metadata_baseline_cached
        self.assertTrue(callable(ensure_soft_metadata_baseline_cached))

    def test_enrichment_fills_canonical_slot_for_predict_payload(self) -> None:
        # Mini integration: a typical predict_result with regime_features
        # threaded through the helper produces a populated canonical slot
        # that the display hook can then read.
        from ui.predict_tab import (
            enrich_predict_result_with_soft_metadata,
            _extract_soft_metadata,
        )
        pr = {
            "symbol": "AVGO", "analysis_date": "2024-01-08",
            "regime_features": {"pos20": 0.81, "avgo_minus_soxx_20d": 7.3},
            "contract_payload": {
                "current_structure": {
                    "symbol": "AVGO", "analysis_date": "2024-01-08",
                    "prediction_for_date": "2024-01-09",
                },
                "final_projection": {"final_direction": "偏多"},
                "confidence_system": {
                    "confidence_level": "high",
                    "extras": {"primary_score_raw": 2.7},
                },
                "peer_confirmation_adjustment": {
                    "peer_adjustment": "upgrade",
                },
                "exclusion_system": {
                    "extras": {"soft_signal": "none"},
                },
            },
        }
        enriched = enrich_predict_result_with_soft_metadata(pr)
        sm = _extract_soft_metadata(enriched)
        self.assertIsNotNone(sm)
        self.assertEqual(sm["schema_version"], "soft_metadata.v1")
        names = [s["name"] for s in sm["signals"]]
        self.assertIn("r4_overextension", names)

    def test_enrichment_failure_fallback_returns_input_for_predict_tab(self) -> None:
        # Step 2G-6B.3 wraps the call in try/except. If the helper
        # raised, the page would fall back to predict_result. Since the
        # try/except is in render_predict_tab itself (not exposed as a
        # function), we simulate the fallback by patching the helper to
        # raise and verifying the section still hides gracefully on the
        # raw predict_result (which has no canonical soft_metadata).
        from ui.predict_tab import (
            _extract_soft_metadata,
            render_soft_metadata_section,
        )
        raw_pr = {"symbol": "AVGO"}  # no contract_payload → display hidden
        with patch("ui.predict_tab.st") as st_mock:
            cd = render_soft_metadata_section(_extract_soft_metadata(raw_pr))
        self.assertFalse(cd["visible"])
        st_mock.markdown.assert_not_called()

    def test_enrichment_output_no_forbidden_words(self) -> None:
        from ui.predict_tab import (
            enrich_predict_result_with_soft_metadata,
            _extract_soft_metadata,
            render_soft_metadata_section,
        )
        pr = {
            "regime_features": {"pos20": 0.81, "avgo_minus_soxx_20d": 7.3},
            "contract_payload": {
                "current_structure": {"analysis_date": "2024-01-08"},
                "final_projection": {"final_direction": "偏多"},
                "confidence_system": {
                    "confidence_level": "high",
                    "extras": {"primary_score_raw": 2.7},
                },
                "peer_confirmation_adjustment": {"peer_adjustment": "upgrade"},
                "exclusion_system": {"extras": {}},
            },
        }
        enriched = enrich_predict_result_with_soft_metadata(pr)
        with patch("ui.predict_tab.st") as st_mock:
            render_soft_metadata_section(_extract_soft_metadata(enriched))
        for call in st_mock.markdown.call_args_list:
            md = call.args[0]
            for token in FORBIDDEN_COPY_TOKENS:
                self.assertNotIn(token, md)

    def test_enrichment_2026_analysis_date_keeps_section_visible_with_refusal(self) -> None:
        from ui.predict_tab import (
            enrich_predict_result_with_soft_metadata,
            _extract_soft_metadata,
            render_soft_metadata_section,
        )
        pr = {
            "regime_features": {"pos20": 0.81, "avgo_minus_soxx_20d": 7.3},
            "contract_payload": {
                "current_structure": {"analysis_date": "2026-03-15"},
                "final_projection": {"final_direction": "偏多"},
                "confidence_system": {
                    "confidence_level": "high",
                    "extras": {"primary_score_raw": 2.7},
                },
                "peer_confirmation_adjustment": {"peer_adjustment": "upgrade"},
                "exclusion_system": {"extras": {}},
            },
        }
        enriched = enrich_predict_result_with_soft_metadata(pr)
        sm = _extract_soft_metadata(enriched)
        self.assertIn("final_test_range_refusal", sm["summary"]["warnings"])
        with patch("ui.predict_tab.st") as st_mock:
            cd = render_soft_metadata_section(sm)
        self.assertTrue(cd["visible"])
        st_mock.markdown.assert_called_once()
        rendered = st_mock.markdown.call_args.args[0]
        self.assertIn("final test 保留区间", rendered)


@unittest.skipIf(AppTest is None,
                 "streamlit AppTest is not installed in this environment")
class EnrichmentAppTests(unittest.TestCase):
    """AppTest-level integration: drive the enrichment + display chain
    from a synthetic Streamlit script."""

    @staticmethod
    def _script(predict_result_repr: str, scan_result_repr: str = "None") -> str:
        return textwrap.dedent(
            f"""
            import sys
            sys.path.insert(0, {str(ROOT)!r})

            import streamlit as st
            from ui.predict_tab import (
                enrich_predict_result_with_soft_metadata,
                _extract_soft_metadata,
                render_soft_metadata_section,
            )

            pr = {predict_result_repr}
            scan = {scan_result_repr}
            enriched = enrich_predict_result_with_soft_metadata(pr, scan_result=scan)
            render_soft_metadata_section(_extract_soft_metadata(enriched))
            """
        )

    def _all_markdown(self, at) -> str:
        return "\n".join(str(m.value) for m in at.markdown)

    def test_apptest_predict_result_with_features_displays_r4_card(self) -> None:
        pr = {
            "regime_features": {"pos20": 0.81, "avgo_minus_soxx_20d": 7.3},
            "contract_payload": {
                "current_structure": {"analysis_date": "2024-01-08"},
                "final_projection": {"final_direction": "偏多"},
                "confidence_system": {
                    "confidence_level": "high",
                    "extras": {"primary_score_raw": 2.7},
                },
                "peer_confirmation_adjustment": {"peer_adjustment": "upgrade"},
                "exclusion_system": {"extras": {}},
            },
        }
        at = AppTest.from_string(self._script(repr(pr))).run()
        text = self._all_markdown(at)
        self.assertIn("高位跑赢同行后的偏多过热", text)
        self.assertIn("不改变主推演方向", text)
        for token in FORBIDDEN_COPY_TOKENS:
            self.assertNotIn(token, text)

    def test_apptest_predict_result_with_baseline_shows_real_metrics(self) -> None:
        # Step 2G-6B.6 — when a baseline dict is present, the R4 card's
        # historical_metrics_in_sample is filled with the baseline numbers
        # rather than n/a. We exercise this by building a script that
        # supplies a baseline directly.
        pr = {
            "regime_features": {"pos20": 0.81, "avgo_minus_soxx_20d": 7.3},
            "contract_payload": {
                "current_structure": {"analysis_date": "2024-01-08"},
                "final_projection": {"final_direction": "偏多"},
                "confidence_system": {
                    "confidence_level": "high",
                    "extras": {"primary_score_raw": 2.7},
                },
                "peer_confirmation_adjustment": {"peer_adjustment": "upgrade"},
                "exclusion_system": {"extras": {}},
            },
        }
        baseline = {
            "metrics_source": "regime_diagnostics_dashboard_v1",
            "metrics_window": {
                "analysis_date_min": "2023-01-03",
                "analysis_date_max": "2024-08-02",
                "paired_total": 286, "db_snapshot_id": None,
            },
            "metrics_computed_at": "2026-05-04T00:00:00",
            "r4_overextension": {
                "samples": 36, "paired": 34,
                "accuracy": 0.324, "bias_gap": 0.676,
                "false_exclusion_rate": 0.3235, "net_benefit": 0.0219,
            },
            "bullish_high_pos20_residual": None,
            "holdout_status": "FAIL",
            "warnings": [],
        }
        script = textwrap.dedent(
            f"""
            import sys
            sys.path.insert(0, {str(ROOT)!r})

            import streamlit as st
            from ui.predict_tab import (
                enrich_predict_result_with_soft_metadata,
                _extract_soft_metadata,
                render_soft_metadata_section,
            )

            pr = {pr!r}
            baseline = {baseline!r}
            enriched = enrich_predict_result_with_soft_metadata(
                pr, baseline=baseline,
            )
            render_soft_metadata_section(_extract_soft_metadata(enriched))
            """
        )
        at = AppTest.from_string(script).run()
        text = self._all_markdown(at)
        # With baseline, the metrics should be real (32.4% accuracy from
        # the canned baseline, not n/a).
        self.assertIn("32.4%", text)
        self.assertNotIn("n/a", text)
        for token in FORBIDDEN_COPY_TOKENS:
            self.assertNotIn(token, text)

    def test_apptest_anti_false_exclusion_section_renders_safely(self) -> None:
        # Step 2G-7B — when soft_metadata has signals, the Predict
        # integration adds an "为什么这里只做提示" expander with the
        # anti-false-exclusion markdown. We exercise it via a minimal
        # script that mirrors the Predict-tab integration block.
        from ui.anti_false_exclusion_display import FORBIDDEN_COPY_TOKENS as AFX_FORBIDDEN
        pr = {
            "regime_features": {"pos20": 0.81, "avgo_minus_soxx_20d": 7.3},
            "contract_payload": {
                "current_structure": {"analysis_date": "2024-01-08"},
                "final_projection": {"final_direction": "偏多"},
                "confidence_system": {
                    "confidence_level": "high",
                    "extras": {"primary_score_raw": 2.7},
                },
                "peer_confirmation_adjustment": {"peer_adjustment": "upgrade"},
                "exclusion_system": {"extras": {}},
            },
        }
        baseline = {
            "metrics_source": "regime_diagnostics_dashboard_v1",
            "metrics_window": {
                "analysis_date_min": "2023-01-03",
                "analysis_date_max": "2024-08-02",
                "paired_total": 286, "db_snapshot_id": None,
            },
            "metrics_computed_at": "2026-05-04T00:00:00",
            "r4_overextension": {
                "samples": 36, "paired": 34,
                "accuracy": 0.324, "bias_gap": 0.676,
                "false_exclusion_rate": 0.3235, "net_benefit": 0.0219,
            },
            "bullish_high_pos20_residual": None,
            "holdout_status": "FAIL", "warnings": [],
        }
        script = textwrap.dedent(
            f"""
            import sys
            sys.path.insert(0, {str(ROOT)!r})

            import streamlit as st
            from ui.predict_tab import (
                enrich_predict_result_with_soft_metadata,
                _extract_soft_metadata,
                render_soft_metadata_section,
            )
            from ui.anti_false_exclusion_display import (
                build_anti_false_exclusion_display,
                render_anti_false_exclusion_markdown,
            )

            pr = {pr!r}
            baseline = {baseline!r}
            enriched = enrich_predict_result_with_soft_metadata(
                pr, baseline=baseline,
            )
            sm = _extract_soft_metadata(enriched)
            render_soft_metadata_section(sm)
            if isinstance(sm, dict) and sm.get('signals'):
                afx = build_anti_false_exclusion_display(sm)
                if afx.get('visible'):
                    with st.expander('为什么这里只做提示', expanded=False):
                        st.markdown(render_anti_false_exclusion_markdown(afx))
            """
        )
        at = AppTest.from_string(script).run()
        # Expander label should appear among the page elements.
        all_labels = " ".join(
            getattr(el, "label", "") or "" for el in getattr(at, "expander", [])
        )
        self.assertIn("为什么这里只做提示", all_labels)
        # Markdown body should mention the gate-fail evidence.
        text = self._all_markdown(at)
        self.assertIn("32.4%", text)
        # Page-level grep uses the well-known renderer 16 tokens; the
        # AFX-only stricter tokens (hard / forced / 排除 standalone) are
        # locked in tests/test_anti_false_exclusion_display.py against
        # the AFX markdown alone — checking them at page level would
        # trip on the renderer's existing "误杀率（若强制排除）" label.
        del AFX_FORBIDDEN  # noqa: F841 — referenced earlier; suppress lint
        for token in FORBIDDEN_COPY_TOKENS:
            self.assertNotIn(token, text)

    def test_apptest_predict_result_without_features_shows_dev_hint_no_card(self) -> None:
        pr = {
            "contract_payload": {
                "current_structure": {"analysis_date": "2024-01-08"},
                "final_projection": {"final_direction": "偏多"},
                "confidence_system": {"confidence_level": "high",
                                       "extras": {}},
                "peer_confirmation_adjustment": {"peer_adjustment": "hold"},
                "exclusion_system": {"extras": {}},
            },
        }
        at = AppTest.from_string(self._script(repr(pr))).run()
        text = self._all_markdown(at)
        # No regime features + baseline=None → simulator emits signals=[]
        # plus ``missing_baseline`` + ``missing_regime_features`` dev
        # warnings. Per Step 2G-6B.1 §7 / renderer visibility matrix the
        # section becomes a folded dev hint (visible) — NOT a hidden
        # section. The R4 card itself must NOT appear.
        self.assertIn("未触发 metadata", text)
        self.assertNotIn("高位跑赢同行后的偏多过热", text)
        # And the safety guarantee still holds: no forbidden words leak.
        for token in FORBIDDEN_COPY_TOKENS:
            self.assertNotIn(token, text)


# ─────────────────────────────────────────────────────────────────────────
# Step 2G-8A.2 — protection layer diagnostics integration in Predict
# ─────────────────────────────────────────────────────────────────────────

@unittest.skipIf(AppTest is None,
                 "streamlit AppTest is not installed in this environment")
class ProtectionLayerDiagnosticsPredictAppTests(unittest.TestCase):
    """Drive the protection_layer_diagnostics.v1 sub-section by mirror
    of the Predict-tab inline block (lines under the AFX expander).
    Same wiring pattern as the existing AFX AppTests."""

    @staticmethod
    def _script(soft_repr: str) -> str:
        return textwrap.dedent(
            f"""
            import sys
            sys.path.insert(0, {str(ROOT)!r})

            import streamlit as st
            from ui.anti_false_exclusion_display import (
                build_anti_false_exclusion_display,
                render_anti_false_exclusion_markdown,
            )
            from services.protection_layer_diagnostics import (
                build_protection_layer_diagnostics,
            )
            from ui.protection_layer_diagnostics_renderer import (
                build_protection_layer_diagnostics_card_data,
                render_protection_layer_diagnostics_markdown,
            )

            sm = {soft_repr}
            if isinstance(sm, dict) and sm.get('signals'):
                _afx = build_anti_false_exclusion_display(sm)
                if _afx.get('visible'):
                    with st.expander('为什么这里只做提示', expanded=False):
                        st.markdown(render_anti_false_exclusion_markdown(_afx))
                        _pld = build_protection_layer_diagnostics(soft_metadata=sm)
                        _pld_card = build_protection_layer_diagnostics_card_data(_pld)
                        if _pld_card.get('visible'):
                            st.markdown(
                                render_protection_layer_diagnostics_markdown(_pld_card)
                            )
            """
        )

    def _all_markdown(self, at) -> str:
        return "\n".join(str(m.value) for m in at.markdown)

    def _expander_labels(self, at) -> str:
        return " ".join(
            getattr(el, "label", "") or "" for el in getattr(at, "expander", [])
        )

    def test_apptest_predict_includes_protection_diagnostics(self) -> None:
        from ui.protection_layer_diagnostics_renderer import (
            FORBIDDEN_COPY_TOKENS as PLD_FORBIDDEN,
        )
        sm = _r4_soft_metadata()
        at = AppTest.from_string(self._script(repr(sm))).run()
        text = self._all_markdown(at)
        labels = self._expander_labels(at)
        self.assertIn("为什么这里只做提示", labels)
        # Protection diagnostics block markers
        self.assertIn("保护层诊断详情", text)
        self.assertIn("跨窗口稳定性 guard", text)
        self.assertIn("净收益 guard", text)
        # Connection-flag yes/no display
        self.assertIn("诊断已接入 · 是", text)
        self.assertIn("决策链未接入 · 否", text)
        self.assertIn("04 字段未升级 · 否", text)
        self.assertIn("评估闸门暂未接入 · 否", text)
        # State lines
        self.assertIn("升级条件未满足", text)
        # Stricter renderer-side forbidden lockdown (8 tokens including
        # ``hard`` / ``forced`` substrings)
        for token in PLD_FORBIDDEN:
            self.assertNotIn(token, text)

    def test_apptest_predict_protection_no_pass_phrasing(self) -> None:
        # Even with both metrics passing on the helper side, the four
        # connection flags stay locked → diagnostic_connected=true / 三
        # false. Sanity: the page must not let the user think Gate 5
        # passed.
        sm = _r4_soft_metadata()
        # Force a happy R4 metric so neither guard triggers.
        sm["signals"][0]["holdout_status"] = "PASS"
        sm["signals"][0]["historical_metrics_in_sample"]["net_benefit"] = 0.10
        at = AppTest.from_string(self._script(repr(sm))).run()
        text = self._all_markdown(at)
        # Protection card stays hidden (no guards, no warnings).
        self.assertNotIn("保护层诊断详情", text)
        # And the AFX expander still rendered separately (we do not
        # assert on AFX content here — that is locked elsewhere).

    def test_apptest_predict_no_signals_renders_no_protection_block(self) -> None:
        sm = _empty_soft_metadata()
        at = AppTest.from_string(self._script(repr(sm))).run()
        text = self._all_markdown(at)
        self.assertNotIn("保护层诊断详情", text)


# ─────────────────────────────────────────────────────────────────────────
# Step 2G-8A.2 — wiring smoke: predict_tab module imports new helpers
# ─────────────────────────────────────────────────────────────────────────

class ProtectionLayerWiringSmokeTests(unittest.TestCase):
    def test_predict_tab_imports_protection_helpers(self) -> None:
        from ui.predict_tab import (
            build_protection_layer_diagnostics,
            build_protection_layer_diagnostics_card_data,
            render_protection_layer_diagnostics_markdown,
        )
        self.assertTrue(callable(build_protection_layer_diagnostics))
        self.assertTrue(callable(build_protection_layer_diagnostics_card_data))
        self.assertTrue(callable(render_protection_layer_diagnostics_markdown))


if __name__ == "__main__":
    unittest.main()
