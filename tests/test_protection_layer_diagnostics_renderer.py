"""Tests for ui/protection_layer_diagnostics_renderer.py (Step 2G-8A.2)."""
from __future__ import annotations

import ast
import sys
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.protection_layer_diagnostics import (  # noqa: E402
    build_protection_layer_diagnostics,
)
from ui.protection_layer_diagnostics_renderer import (  # noqa: E402
    FORBIDDEN_COPY_TOKENS,
    SCHEMA_VERSION,
    build_protection_layer_diagnostics_card_data,
    render_protection_layer_diagnostics_markdown,
)


# ── fixtures ────────────────────────────────────────────────────────────

def _diagnostics(*, holdout_status: str = "FAIL",
                net_benefit: float | None = 0.0219) -> dict:
    return build_protection_layer_diagnostics({
        "soft_metadata_summary": {
            "r4_overextension": {
                "holdout_status": holdout_status,
                "net_benefit": net_benefit,
            },
        },
        "warnings": [],
    })


def _diagnostics_no_data() -> dict:
    return build_protection_layer_diagnostics()


def _diagnostics_final_test_warning() -> dict:
    return build_protection_layer_diagnostics({
        "soft_metadata_summary": {
            "r4_overextension": {
                "holdout_status": "FAIL",
                "net_benefit": 0.0219,
            },
        },
        "warnings": ["final_test_range_refusal"],
    })


# ── 1. card_data: missing / empty path hidden ─────────────────────────

class CardDataMissingHiddenTests(unittest.TestCase):
    def test_none_input_hidden(self) -> None:
        cd = build_protection_layer_diagnostics_card_data(None)
        self.assertFalse(cd["visible"])
        self.assertEqual(cd["guards"], [])

    def test_non_dict_input_hidden(self) -> None:
        for junk in ("string", 123, [], 0.5, True):
            cd = build_protection_layer_diagnostics_card_data(junk)  # type: ignore[arg-type]
            self.assertFalse(cd["visible"])

    def test_missing_schema_version_hidden(self) -> None:
        cd = build_protection_layer_diagnostics_card_data({
            "guards": [], "summary": {},
        })
        self.assertFalse(cd["visible"])

    def test_no_guards_no_warnings_hidden(self) -> None:
        # Helper produces guards=[] + warnings=["missing_metrics"] for
        # the no-data path; without warnings we must hide the card.
        cd = build_protection_layer_diagnostics_card_data({
            "schema_version": "protection_layer_diagnostics.v1",
            "diagnostic_connected": True,
            "hard_gate_connected": False,
            "required_field_connected": False,
            "protection_layer_connected_for_gate": False,
            "guards": [],
            "summary": {"hard_upgrade_blocked": True, "display_only": True},
            "warnings": [],
        })
        self.assertFalse(cd["visible"])


# ── 2. card_data: guards render ─────────────────────────────────────────

class CardDataGuardsTests(unittest.TestCase):
    def test_two_guards_visible(self) -> None:
        cd = build_protection_layer_diagnostics_card_data(_diagnostics())
        self.assertTrue(cd["visible"])
        names = [g["name"] for g in cd["guards"]]
        self.assertIn("holdout_stability_guard", names)
        self.assertIn("net_benefit_guard", names)

    def test_guard_count_matches(self) -> None:
        cd = build_protection_layer_diagnostics_card_data(_diagnostics())
        self.assertEqual(cd["summary"]["blocking_guard_count"], 2)

    def test_only_holdout_guard(self) -> None:
        # holdout=FAIL but nb passes → only holdout guard
        cd = build_protection_layer_diagnostics_card_data(
            _diagnostics(holdout_status="FAIL", net_benefit=0.10),
        )
        self.assertEqual(len(cd["guards"]), 1)
        self.assertEqual(cd["guards"][0]["name"], "holdout_stability_guard")


# ── 3. card_data: four-flag mirror ─────────────────────────────────────

class CardDataConnectionFlagTests(unittest.TestCase):
    def test_diagnostic_connected_true(self) -> None:
        cd = build_protection_layer_diagnostics_card_data(_diagnostics())
        self.assertTrue(cd["diagnostic_connected"])

    def test_three_other_flags_false(self) -> None:
        cd = build_protection_layer_diagnostics_card_data(_diagnostics())
        self.assertFalse(cd["hard_gate_connected"])
        self.assertFalse(cd["required_field_connected"])
        self.assertFalse(cd["protection_layer_connected_for_gate"])

    def test_flags_locked_across_scenarios(self) -> None:
        for d in (
            _diagnostics(holdout_status="PASS", net_benefit=0.10),
            _diagnostics_final_test_warning(),
        ):
            cd = build_protection_layer_diagnostics_card_data(d)
            self.assertTrue(cd["diagnostic_connected"])
            self.assertFalse(cd["hard_gate_connected"])
            self.assertFalse(cd["required_field_connected"])
            self.assertFalse(cd["protection_layer_connected_for_gate"])


# ── 4. markdown: visible cases produce structure ────────────────────────

class MarkdownStructureTests(unittest.TestCase):
    def test_default_visible_renders_known_phrases(self) -> None:
        md = render_protection_layer_diagnostics_markdown(
            build_protection_layer_diagnostics_card_data(_diagnostics()),
        )
        self.assertIn("保护层诊断详情", md)
        self.assertIn("诊断信息已接入", md)
        self.assertIn("不等于自动升级", md)
        self.assertIn("当前仍只允许复盘提示", md)
        self.assertIn("跨窗口稳定性 guard", md)
        self.assertIn("净收益 guard", md)
        self.assertIn("接入状态", md)
        # Connection-flag yes/no
        self.assertIn("诊断已接入 · 是", md)
        self.assertIn("决策链未接入 · 否", md)
        self.assertIn("04 字段未升级 · 否", md)
        self.assertIn("评估闸门暂未接入 · 否", md)

    def test_invisible_returns_empty(self) -> None:
        md = render_protection_layer_diagnostics_markdown({"visible": False})
        self.assertEqual(md, "")
        md = render_protection_layer_diagnostics_markdown(None)  # type: ignore[arg-type]
        self.assertEqual(md, "")

    def test_missing_metrics_warning_visible_via_warnings(self) -> None:
        cd = build_protection_layer_diagnostics_card_data(_diagnostics_no_data())
        # The helper emits warnings=["missing_metrics"] which makes the
        # card visible (so the user sees the warning) but with no
        # guards.
        self.assertTrue(cd["visible"])
        md = render_protection_layer_diagnostics_markdown(cd)
        self.assertIn("保护层诊断缺数据", md)
        self.assertNotIn("跨窗口稳定性 guard", md)


# ── 5. forbidden words ─────────────────────────────────────────────────

class ForbiddenCopyTests(unittest.TestCase):
    SCENARIOS = [
        ("default", _diagnostics()),
        ("holdout_pass", _diagnostics(holdout_status="PASS", net_benefit=0.10)),
        ("nb_above_gate", _diagnostics(holdout_status="FAIL", net_benefit=0.10)),
        ("final_test_warning", _diagnostics_final_test_warning()),
        ("missing_metrics", _diagnostics_no_data()),
    ]

    def test_no_forbidden_in_any_scenario(self) -> None:
        for label, d in self.SCENARIOS:
            with self.subTest(scenario=label):
                cd = build_protection_layer_diagnostics_card_data(d)
                md = render_protection_layer_diagnostics_markdown(cd)
                for tok in FORBIDDEN_COPY_TOKENS:
                    self.assertNotIn(tok, md, f"leak: {tok!r} in {label}")


# ── 6. input not mutated ───────────────────────────────────────────────

class InputImmutabilityTests(unittest.TestCase):
    def test_card_data_builder_does_not_mutate(self) -> None:
        d = _diagnostics()
        snap = deepcopy(d)
        build_protection_layer_diagnostics_card_data(d)
        self.assertEqual(d, snap)

    def test_renderer_does_not_mutate(self) -> None:
        cd = build_protection_layer_diagnostics_card_data(_diagnostics())
        snap = deepcopy(cd)
        render_protection_layer_diagnostics_markdown(cd)
        self.assertEqual(cd, snap)


# ── 7. unknown / malformed guard graceful ──────────────────────────────

class UnknownGuardTests(unittest.TestCase):
    def test_unknown_guard_name_renders_raw_name(self) -> None:
        d = {
            "schema_version": "protection_layer_diagnostics.v1",
            "diagnostic_connected": True,
            "hard_gate_connected": False,
            "required_field_connected": False,
            "protection_layer_connected_for_gate": False,
            "guards": [{
                "name": "future_guard_v2",
                "status": "blocking",
                "reason": "future_reason",
                "evidence": {"holdout_status": "FAIL"},
                "message": "只读提示，不构成自动决策依据。",
            }],
            "summary": {
                "hard_upgrade_blocked": True, "display_only": True,
                "blocking_guard_count": 1,
                "required_next_step": "narrower_candidate_research",
            },
            "warnings": [],
        }
        cd = build_protection_layer_diagnostics_card_data(d)
        md = render_protection_layer_diagnostics_markdown(cd)
        self.assertIn("future_guard_v2", md)
        for tok in FORBIDDEN_COPY_TOKENS:
            self.assertNotIn(tok, md)

    def test_non_dict_guard_skipped(self) -> None:
        d = {
            "schema_version": "protection_layer_diagnostics.v1",
            "diagnostic_connected": True,
            "hard_gate_connected": False,
            "required_field_connected": False,
            "protection_layer_connected_for_gate": False,
            "guards": ["not a dict", 123, None],
            "summary": {"hard_upgrade_blocked": True, "display_only": True},
            "warnings": ["missing_metrics"],
        }
        cd = build_protection_layer_diagnostics_card_data(d)
        # Non-dict guards filtered out → no rendered guards but warning
        # keeps the card visible.
        self.assertEqual(cd["guards"], [])
        self.assertTrue(cd["visible"])
        md = render_protection_layer_diagnostics_markdown(cd)
        for tok in FORBIDDEN_COPY_TOKENS:
            self.assertNotIn(tok, md)


# ── 8. final_test_range_refusal warning passthrough ────────────────────

class FinalTestRangeWarningTests(unittest.TestCase):
    def test_warning_visible_in_markdown(self) -> None:
        cd = build_protection_layer_diagnostics_card_data(
            _diagnostics_final_test_warning(),
        )
        self.assertTrue(cd["visible"])
        md = render_protection_layer_diagnostics_markdown(cd)
        self.assertIn("final test 保留区间", md)
        for tok in FORBIDDEN_COPY_TOKENS:
            self.assertNotIn(tok, md)


# ── 9. isolation ───────────────────────────────────────────────────────

class IsolationTests(unittest.TestCase):
    def test_module_does_not_import_forbidden(self) -> None:
        import ui.protection_layer_diagnostics_renderer as mod
        tree = ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))
        forbidden_modules = {
            "streamlit",
            "yfinance", "requests",
            "longbridge", "broker", "paper_trade",
            "sqlite3",
            "services.prediction_store",
            "services.confidence_engine",
            "services.contradiction_engine",
            "services.risk_model",
            "services.soft_metadata_simulator",
            "services.anti_false_exclusion_dashboard",
            "predict", "scanner",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(alias.name, forbidden_modules)
            elif isinstance(node, ast.ImportFrom):
                self.assertNotIn(node.module, forbidden_modules)

    def test_schema_version_constant_locked(self) -> None:
        self.assertEqual(SCHEMA_VERSION, "protection_layer_diagnostics_card.v1")


# ── 10. summary state lines ───────────────────────────────────────────

class SummaryStateLineTests(unittest.TestCase):
    def test_state_lines_present(self) -> None:
        md = render_protection_layer_diagnostics_markdown(
            build_protection_layer_diagnostics_card_data(_diagnostics()),
        )
        self.assertIn("升级条件未满足", md)
        self.assertIn("当前仅作展示", md)
        self.assertIn("blocking guards：2", md)

    def test_required_next_step_visible(self) -> None:
        md = render_protection_layer_diagnostics_markdown(
            build_protection_layer_diagnostics_card_data(_diagnostics()),
        )
        self.assertIn("待补条件", md)
        self.assertIn("narrower_candidate_research", md)


if __name__ == "__main__":
    unittest.main()
