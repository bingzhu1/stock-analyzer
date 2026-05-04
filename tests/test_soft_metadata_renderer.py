"""Tests for ui/soft_metadata_renderer.py (Step 2G-6A)."""
from __future__ import annotations

import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.soft_metadata_renderer import (
    FORBIDDEN_COPY_TOKENS,
    render_soft_metadata_card_data,
    render_soft_metadata_markdown,
)


# ── fixtures ────────────────────────────────────────────────────────────

def _r4_signal() -> dict:
    return {
        "name": "r4_overextension",
        "display_label": "高位跑赢同行后的偏多过热",
        "severity": "medium",
        "dedup_group": "bullish_overextension",
        "raw_features": {
            "avgo_minus_soxx_20d": 7.3,
            "pos20": 0.81,
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


def _residual_signal() -> dict:
    return {
        "name": "bullish_high_pos20_residual",
        "display_label": "高位偏多 + 高置信（剔除 R4 后残差）",
        "severity": "medium",
        "dedup_group": "bullish_overextension",
        "raw_features": {"pos20": 0.81},
        "trigger_context": {
            "final_direction": "偏多",
            "confidence_level": "high",
            "peer_subtype": "hold",
        },
        "historical_metrics_in_sample": {
            "samples": 47, "paired": 47,
            "accuracy": 0.489, "bias_gap": 0.511,
            "false_exclusion_rate": 0.489,
            "net_benefit": -0.001,
        },
        "holdout_status": "FAIL",
        "recommended_action": "review_only",
        "hard_forbidden_primary_reason": "false_exclusion_rate_too_high",
        "hard_forbidden_breakdown": [
            "false_exclusion_rate=0.4890 > 0.10",
            "net_benefit=-0.0010 < 0.05",
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
            "paired_total": 286,
            "db_snapshot_id": None,
        },
        "metrics_computed_at": "2026-05-04T00:00:00",
        "signals": sig_list,
        "summary": {
            "has_overextension_signal": bool(sig_list),
            "max_severity": (
                "medium" if any(s.get("severity") == "medium" for s in sig_list)
                else ("low" if sig_list else "none")
            ),
            "hard_exclusion_allowed": False,
            "signal_count": len(sig_list),
            "primary_signal": sig_list[0]["name"] if sig_list else None,
            "warnings": list(warnings or []),
        },
    }


def _all_text(card_data: dict) -> str:
    """Concatenate every string field reachable in card_data + markdown."""
    md = render_soft_metadata_markdown(card_data)
    return json.dumps(card_data, ensure_ascii=False) + "\n" + md


# ── 1. empty predict hidden ─────────────────────────────────────────────

class EmptyPredictHiddenTests(unittest.TestCase):
    def test_empty_signals_predict_context_hidden(self) -> None:
        cd = render_soft_metadata_card_data(_shell(), context="predict")
        self.assertFalse(cd["visible"])
        self.assertEqual(cd["cards"], [])

    def test_empty_signals_predict_no_warnings_zero_cards(self) -> None:
        cd = render_soft_metadata_card_data(_shell(), context="predict")
        self.assertEqual(cd["cards"], [])
        self.assertEqual(cd["warnings"], [])


# ── 2. empty review visible ─────────────────────────────────────────────

class EmptyReviewVisibleTests(unittest.TestCase):
    def test_empty_signals_review_context_visible_with_message(self) -> None:
        cd = render_soft_metadata_card_data(_shell(), context="review")
        self.assertTrue(cd["visible"])
        self.assertIn("未触发", cd["subtitle"])
        self.assertEqual(cd["cards"], [])


# ── 3. R4 card renders ─────────────────────────────────────────────────

class R4CardTests(unittest.TestCase):
    def test_r4_card_default_fields(self) -> None:
        cd = render_soft_metadata_card_data(
            _shell(signals=[_r4_signal()]), context="predict",
        )
        self.assertTrue(cd["visible"])
        self.assertEqual(len(cd["cards"]), 1)
        c = cd["cards"][0]
        self.assertEqual(c["name"], "r4_overextension")
        self.assertEqual(c["display_label"], "高位跑赢同行后的偏多过热")
        self.assertEqual(c["severity"], "medium")
        self.assertEqual(c["badge_text"], "复核建议")
        self.assertEqual(c["badge_tone"], "caution")
        self.assertIn("历史样本中该结构容易高估上涨概率", c["summary_text"])

    def test_r4_metrics_in_default_view(self) -> None:
        cd = render_soft_metadata_card_data(
            _shell(signals=[_r4_signal()]), context="predict",
        )
        labels = [m["label"] for m in cd["cards"][0]["metrics"]]
        values = [m["value"] for m in cd["cards"][0]["metrics"]]
        self.assertIn("历史命中率", labels)
        self.assertIn("32.4%", values)
        self.assertTrue(any("+67.6pp" in v for v in values))
        self.assertIn("32.4%", values)  # false_exclusion_rate
        self.assertTrue(any("+2.2pp" in v for v in values))

    def test_r4_safety_note_includes_no_change_to_main_projection(self) -> None:
        cd = render_soft_metadata_card_data(
            _shell(signals=[_r4_signal()]), context="predict",
        )
        self.assertIn("不改变主推演方向", cd["cards"][0]["safety_note"])
        self.assertIn("不构成交易指令", cd["cards"][0]["safety_note"])

    def test_r4_expandable_details_include_all_three_hard_reasons(self) -> None:
        cd = render_soft_metadata_card_data(
            _shell(signals=[_r4_signal()]), context="predict",
        )
        details_labels = {
            d["label"] for d in cd["cards"][0]["expandable_details"]
        }
        self.assertIn("为什么不强制排除", details_labels)
        self.assertIn("净收益不达 gate", details_labels)
        self.assertIn("跨窗口 holdout", details_labels)


# ── 4. residual card renders weaker wording ────────────────────────────

class ResidualCardTests(unittest.TestCase):
    def test_residual_summary_uses_weaker_context_wording(self) -> None:
        cd = render_soft_metadata_card_data(
            _shell(signals=[_residual_signal()]), context="predict",
        )
        c = cd["cards"][0]
        self.assertEqual(c["name"], "bullish_high_pos20_residual")
        self.assertIn("上下文", c["summary_text"])
        # Residual must NOT use the strong R4 phrasing
        self.assertNotIn(
            "明显跑赢 SOXX", c["summary_text"],
        )

    def test_residual_negative_net_benefit_uses_negative_wording(self) -> None:
        cd = render_soft_metadata_card_data(
            _shell(signals=[_residual_signal()]), context="predict",
        )
        details_text = " ".join(
            d["text"] for d in cd["cards"][0]["expandable_details"]
        )
        self.assertIn("不升反降", details_text)


# ── 5. forbidden words not present ─────────────────────────────────────

class ForbiddenCopyTests(unittest.TestCase):
    def _assert_no_forbidden(self, card_data: dict) -> None:
        text = _all_text(card_data)
        for token in FORBIDDEN_COPY_TOKENS:
            self.assertNotIn(
                token, text,
                f"forbidden token {token!r} appeared in renderer output",
            )

    def test_no_forbidden_in_empty_predict(self) -> None:
        self._assert_no_forbidden(
            render_soft_metadata_card_data(_shell(), context="predict")
        )

    def test_no_forbidden_in_empty_review(self) -> None:
        self._assert_no_forbidden(
            render_soft_metadata_card_data(_shell(), context="review")
        )

    def test_no_forbidden_in_r4_card(self) -> None:
        self._assert_no_forbidden(
            render_soft_metadata_card_data(
                _shell(signals=[_r4_signal()]), context="predict",
            )
        )

    def test_no_forbidden_in_residual_card(self) -> None:
        self._assert_no_forbidden(
            render_soft_metadata_card_data(
                _shell(signals=[_residual_signal()]), context="review",
            )
        )

    def test_no_forbidden_when_debug_included(self) -> None:
        self._assert_no_forbidden(
            render_soft_metadata_card_data(
                _shell(signals=[_r4_signal()]),
                context="predict", include_debug=True,
            )
        )

    def test_no_forbidden_for_final_test_refusal(self) -> None:
        sm = _shell(warnings=["final_test_range_refusal"])
        self._assert_no_forbidden(
            render_soft_metadata_card_data(sm, context="predict")
        )


# ── 6. hard_exclusion_allowed=false surfaced in safety note ────────────

class HardExclusionAllowedSurfacedTests(unittest.TestCase):
    def test_safety_note_communicates_no_trade_no_override_for_every_card(self) -> None:
        for sig in (_r4_signal(), _residual_signal()):
            cd = render_soft_metadata_card_data(
                _shell(signals=[sig]), context="predict",
            )
            note = cd["cards"][0]["safety_note"]
            self.assertIn("不改变主推演方向", note)
            self.assertIn("策略边界（不交易）不变", note)


# ── 7. final_test_range_refusal warning visible ────────────────────────

class FinalTestRefusalVisibleTests(unittest.TestCase):
    def test_predict_with_refusal_warning_is_visible(self) -> None:
        sm = _shell(warnings=["final_test_range_refusal"])
        cd = render_soft_metadata_card_data(sm, context="predict")
        self.assertTrue(cd["visible"])
        self.assertIn("final test 保留区间", cd["subtitle"])
        self.assertIn("final_test_range_refusal", cd["warnings"])

    def test_review_with_refusal_warning_is_visible(self) -> None:
        sm = _shell(warnings=["final_test_range_refusal"])
        cd = render_soft_metadata_card_data(sm, context="review")
        self.assertTrue(cd["visible"])
        self.assertIn("final_test_range_refusal", cd["warnings"])


# ── 8. include_debug toggle ────────────────────────────────────────────

class DebugToggleTests(unittest.TestCase):
    def test_include_debug_false_hides_raw_dict(self) -> None:
        cd = render_soft_metadata_card_data(
            _shell(signals=[_r4_signal()]),
            context="predict", include_debug=False,
        )
        self.assertIsNone(cd["debug"])

    def test_include_debug_true_includes_schema_version_and_window(self) -> None:
        cd = render_soft_metadata_card_data(
            _shell(signals=[_r4_signal()]),
            context="predict", include_debug=True,
        )
        self.assertIsNotNone(cd["debug"])
        self.assertEqual(cd["debug"]["schema_version"], "soft_metadata.v1")
        self.assertEqual(
            cd["debug"]["metrics_source"], "regime_diagnostics_dashboard_v1",
        )
        self.assertIn("analysis_date_min", cd["debug"]["metrics_window"])
        self.assertEqual(
            cd["debug"]["metrics_window"]["paired_total"], 286,
        )


# ── 9. severity tone never danger / red ────────────────────────────────

class SeverityToneTests(unittest.TestCase):
    def test_medium_uses_caution_not_danger(self) -> None:
        cd = render_soft_metadata_card_data(
            _shell(signals=[_r4_signal()]), context="predict",
        )
        c = cd["cards"][0]
        self.assertEqual(c["badge_tone"], "caution")
        # Check user-visible markdown only (the JSON has a `warnings` key
        # which is a developer field, not user-visible copy).
        md = render_soft_metadata_markdown(cd)
        for forbidden_tone in ("danger", "red", "危险"):
            self.assertNotIn(forbidden_tone, md)
        # And confirm the badge_tone field is the only place "caution"
        # / "info" appear — never "danger" / "red".
        self.assertNotIn("danger", c["badge_tone"])
        self.assertNotIn("red", c["badge_tone"])

    def test_low_severity_uses_info_tone(self) -> None:
        sig = _r4_signal()
        sig["severity"] = "low"
        cd = render_soft_metadata_card_data(
            _shell(signals=[sig]), context="predict",
        )
        self.assertEqual(cd["cards"][0]["badge_tone"], "info")

    def test_input_high_severity_coerced_to_medium_with_warning(self) -> None:
        sig = _r4_signal()
        sig["severity"] = "high"  # spec disallows; renderer must coerce
        cd = render_soft_metadata_card_data(
            _shell(signals=[sig]), context="predict",
        )
        self.assertEqual(cd["cards"][0]["severity"], "medium")
        self.assertTrue(any(
            "renderer_warning" in w for w in cd["warnings"]
        ))


# ── 10. unknown signal graceful degradation ────────────────────────────

class UnknownSignalGracefulTests(unittest.TestCase):
    def test_unknown_name_renders_generic_card(self) -> None:
        sig = _r4_signal()
        sig["name"] = "wholly_made_up_signal"
        sig["display_label"] = "未来扩展信号"
        cd = render_soft_metadata_card_data(
            _shell(signals=[sig]), context="predict",
        )
        c = cd["cards"][0]
        self.assertEqual(c["name"], "wholly_made_up_signal")
        self.assertIn("未识别的 metadata 信号", c["summary_text"])
        self.assertEqual(c["display_label"], "未来扩展信号")

    def test_unknown_name_without_label_uses_placeholder(self) -> None:
        cd = render_soft_metadata_card_data(
            _shell(signals=[{"name": "x", "severity": "low"}]),
            context="predict",
        )
        self.assertIn("未识别 metadata 信号", cd["cards"][0]["display_label"])

    def test_non_dict_signal_is_dropped(self) -> None:
        sm = _shell(signals=[_r4_signal()])
        sm["signals"].insert(0, "not a dict")  # type: ignore[arg-type]
        cd = render_soft_metadata_card_data(sm, context="predict")
        self.assertEqual(len(cd["cards"]), 1)
        self.assertEqual(cd["cards"][0]["name"], "r4_overextension")


# ── 11. signal_count mismatch warning ──────────────────────────────────

class SignalCountMismatchTests(unittest.TestCase):
    def test_summary_count_mismatch_emits_renderer_warning(self) -> None:
        sm = _shell(signals=[_r4_signal()])
        sm["summary"]["signal_count"] = 99  # lie
        cd = render_soft_metadata_card_data(sm, context="predict")
        self.assertTrue(any(
            "signal_count" in w and "renderer_warning" in w
            for w in cd["warnings"]
        ))


# ── 12. max 3 cards rendered ───────────────────────────────────────────

class MaxThreeCardsTests(unittest.TestCase):
    def test_more_than_three_signals_capped_at_three(self) -> None:
        sm = _shell(signals=[_r4_signal(), _r4_signal(), _r4_signal(),
                             _r4_signal(), _r4_signal()])
        cd = render_soft_metadata_card_data(sm, context="predict")
        self.assertEqual(len(cd["cards"]), 3)


# ── 13. no forbidden imports ───────────────────────────────────────────

class NoForbiddenImportsTests(unittest.TestCase):
    def test_renderer_module_does_not_import_forbidden(self) -> None:
        import ast
        import ui.soft_metadata_renderer as mod
        tree = ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))
        forbidden_modules = {
            "yfinance", "requests",
            "longbridge", "broker", "paper_trade",
            "streamlit", "st",  # renderer must not be Streamlit-coupled
            "sqlite3",
            "services.soft_metadata_simulator",
            "services.regime_diagnostics_dashboard",
            "services.prediction_store",
            "services.confidence_engine",
            "services.contradiction_engine",
            "services.risk_model",
            "confidence_engine", "contradiction_engine", "risk_model",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(
                        alias.name, forbidden_modules,
                        f"forbidden import {alias.name!r} in renderer",
                    )
            elif isinstance(node, ast.ImportFrom):
                self.assertNotIn(
                    node.module, forbidden_modules,
                    f"forbidden from-import {node.module!r} in renderer",
                )


# ── 14. markdown renderer smoke ────────────────────────────────────────

class MarkdownRendererTests(unittest.TestCase):
    def test_markdown_empty_when_not_visible(self) -> None:
        md = render_soft_metadata_markdown(
            render_soft_metadata_card_data(_shell(), context="predict")
        )
        self.assertEqual(md, "")

    def test_markdown_includes_label_and_summary(self) -> None:
        cd = render_soft_metadata_card_data(
            _shell(signals=[_r4_signal()]), context="predict",
        )
        md = render_soft_metadata_markdown(cd)
        self.assertIn("高位跑赢同行后的偏多过热", md)
        self.assertIn("历史命中率", md)
        self.assertIn("32.4%", md)
        self.assertIn("不改变主推演方向", md)

    def test_markdown_review_empty_state(self) -> None:
        cd = render_soft_metadata_card_data(_shell(), context="review")
        md = render_soft_metadata_markdown(cd)
        self.assertIn("未触发", md)

    def test_markdown_does_not_contain_forbidden_tokens(self) -> None:
        cd = render_soft_metadata_card_data(
            _shell(signals=[_r4_signal(), _residual_signal()]),
            context="review", include_debug=True,
        )
        md = render_soft_metadata_markdown(cd)
        for token in FORBIDDEN_COPY_TOKENS:
            self.assertNotIn(token, md)


# ── 15. defensive input handling ───────────────────────────────────────

class DefensiveInputTests(unittest.TestCase):
    def test_non_dict_input_returns_hidden_in_predict(self) -> None:
        cd = render_soft_metadata_card_data("not a dict", context="predict")  # type: ignore[arg-type]
        self.assertFalse(cd["visible"])
        self.assertEqual(cd["cards"], [])

    def test_unknown_context_falls_back_to_predict(self) -> None:
        cd = render_soft_metadata_card_data(_shell(), context="something")
        self.assertEqual(cd["title"], "结构性偏多风险提示")

    def test_missing_metrics_renders_na_value(self) -> None:
        sig = _r4_signal()
        sig["historical_metrics_in_sample"] = {}
        cd = render_soft_metadata_card_data(
            _shell(signals=[sig]), context="predict",
        )
        values = [m["value"] for m in cd["cards"][0]["metrics"]]
        self.assertTrue(all(v == "n/a" for v in values))


if __name__ == "__main__":
    unittest.main()
