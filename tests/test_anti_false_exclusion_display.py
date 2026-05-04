"""Tests for ui/anti_false_exclusion_display.py (Step 2G-7A)."""
from __future__ import annotations

import sys
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.anti_false_exclusion_display import (
    FORBIDDEN_COPY_TOKENS,
    SCHEMA_VERSION,
    SEVERITY_HIGH,
    SEVERITY_INFORMATIONAL,
    SEVERITY_MEDIUM,
    build_anti_false_exclusion_display,
    render_anti_false_exclusion_markdown,
)


# ── fixtures ────────────────────────────────────────────────────────────

def _r4_signal(*, holdout_status: str = "FAIL",
               accuracy: float = 0.324, paired: int = 34,
               fer: float = 0.3235, nb: float = 0.0219) -> dict:
    return {
        "name": "r4_overextension",
        "display_label": "高位跑赢同行后的偏多过热",
        "severity": "medium",
        "holdout_status": holdout_status,
        "historical_metrics_in_sample": {
            "samples": 36, "paired": paired,
            "accuracy": accuracy, "bias_gap": 0.676,
            "false_exclusion_rate": fer, "net_benefit": nb,
        },
    }


def _shell(signals: list[dict] | None = None,
           warnings: list[str] | None = None) -> dict:
    sig_list = signals or []
    return {
        "schema_version": "soft_metadata.v1",
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


# ── empty / shape ──────────────────────────────────────────────────────

class EmptyAndShapeTests(unittest.TestCase):
    def test_empty_signals_invisible(self) -> None:
        out = build_anti_false_exclusion_display(_shell())
        self.assertEqual(out["schema_version"], SCHEMA_VERSION)
        self.assertFalse(out["visible"])
        self.assertEqual(out["protective_findings"], [])
        self.assertFalse(out["hard_exclusion_allowed"])
        self.assertEqual(out["recommended_action"], "review_only")

    def test_non_dict_input_returns_empty(self) -> None:
        out = build_anti_false_exclusion_display("not a dict")  # type: ignore[arg-type]
        self.assertFalse(out["visible"])
        self.assertEqual(out["protective_findings"], [])

    def test_signals_present_visible(self) -> None:
        out = build_anti_false_exclusion_display(_shell(signals=[_r4_signal()]))
        self.assertTrue(out["visible"])
        self.assertEqual(out["status"], "blocked")
        self.assertGreaterEqual(len(out["protective_findings"]), 1)

    def test_warnings_passthrough(self) -> None:
        out = build_anti_false_exclusion_display(
            _shell(warnings=["final_test_range_refusal"]),
        )
        self.assertIn("final_test_range_refusal", out["warnings"])


# ── invariants: hard_exclusion_allowed always False ────────────────────

class InvariantsTests(unittest.TestCase):
    def test_hard_exclusion_allowed_always_false_with_signals(self) -> None:
        out = build_anti_false_exclusion_display(_shell(signals=[_r4_signal()]))
        self.assertFalse(out["hard_exclusion_allowed"])

    def test_hard_exclusion_allowed_always_false_empty(self) -> None:
        out = build_anti_false_exclusion_display(_shell())
        self.assertFalse(out["hard_exclusion_allowed"])

    def test_hard_exclusion_allowed_always_false_garbage_signal(self) -> None:
        out = build_anti_false_exclusion_display(
            _shell(signals=[{"name": "wholly_made_up"}]),
        )
        self.assertFalse(out["hard_exclusion_allowed"])

    def test_status_never_allowed(self) -> None:
        for sm in (
            _shell(),
            _shell(signals=[_r4_signal()]),
            _shell(signals=[_r4_signal(fer=0.05, nb=0.10)]),  # both pass
        ):
            out = build_anti_false_exclusion_display(sm)
            self.assertNotEqual(out["status"], "allowed")
            self.assertIn(out["status"], ("blocked",))

    def test_input_dict_not_mutated(self) -> None:
        sm = _shell(signals=[_r4_signal()])
        snapshot = deepcopy(sm)
        build_anti_false_exclusion_display(sm, prediction_correct=True)
        self.assertEqual(sm, snapshot)


# ── per-finding triggers ───────────────────────────────────────────────

class R4FalseExclusionRiskTests(unittest.TestCase):
    def test_triggers_when_fer_above_threshold(self) -> None:
        out = build_anti_false_exclusion_display(
            _shell(signals=[_r4_signal(fer=0.32)]),
        )
        names = [f["name"] for f in out["protective_findings"]]
        self.assertIn("r4_false_exclusion_risk", names)
        f = next(f for f in out["protective_findings"]
                 if f["name"] == "r4_false_exclusion_risk")
        self.assertEqual(f["severity"], SEVERITY_MEDIUM)
        self.assertEqual(f["evidence"]["false_exclusion_rate"], 0.32)
        self.assertEqual(f["evidence"]["threshold"], 0.10)

    def test_does_not_trigger_at_or_below_threshold(self) -> None:
        out = build_anti_false_exclusion_display(
            _shell(signals=[_r4_signal(fer=0.10)]),
        )
        names = [f["name"] for f in out["protective_findings"]]
        self.assertNotIn("r4_false_exclusion_risk", names)

    def test_correct_when_triggered_derived_from_accuracy_paired(self) -> None:
        # 0.324 × 34 = 11.016 → round to 11
        out = build_anti_false_exclusion_display(
            _shell(signals=[_r4_signal(accuracy=0.324, paired=34, fer=0.32)]),
        )
        f = next(f for f in out["protective_findings"]
                 if f["name"] == "r4_false_exclusion_risk")
        self.assertEqual(f["evidence"]["correct_when_triggered"], 11)


class R4SurvivalCaseTests(unittest.TestCase):
    def test_triggers_only_when_prediction_correct_true(self) -> None:
        sm = _shell(signals=[_r4_signal()])
        out = build_anti_false_exclusion_display(sm, prediction_correct=True)
        names = [f["name"] for f in out["protective_findings"]]
        self.assertIn("r4_survival_case", names)

    def test_does_not_trigger_when_prediction_correct_false(self) -> None:
        sm = _shell(signals=[_r4_signal()])
        out = build_anti_false_exclusion_display(sm, prediction_correct=False)
        names = [f["name"] for f in out["protective_findings"]]
        self.assertNotIn("r4_survival_case", names)

    def test_does_not_trigger_when_prediction_correct_none(self) -> None:
        sm = _shell(signals=[_r4_signal()])
        out = build_anti_false_exclusion_display(sm, prediction_correct=None)
        names = [f["name"] for f in out["protective_findings"]]
        self.assertNotIn("r4_survival_case", names)

    def test_severity_is_informational(self) -> None:
        out = build_anti_false_exclusion_display(
            _shell(signals=[_r4_signal()]), prediction_correct=True,
        )
        f = next(f for f in out["protective_findings"]
                 if f["name"] == "r4_survival_case")
        self.assertEqual(f["severity"], SEVERITY_INFORMATIONAL)


class HoldoutFailTests(unittest.TestCase):
    def test_triggers_when_any_signal_holdout_fail(self) -> None:
        out = build_anti_false_exclusion_display(
            _shell(signals=[_r4_signal(holdout_status="FAIL")]),
        )
        names = [f["name"] for f in out["protective_findings"]]
        self.assertIn("soft_metadata_holdout_fail", names)

    def test_does_not_trigger_when_holdout_pass(self) -> None:
        out = build_anti_false_exclusion_display(
            _shell(signals=[_r4_signal(holdout_status="PASS")]),
        )
        names = [f["name"] for f in out["protective_findings"]]
        self.assertNotIn("soft_metadata_holdout_fail", names)


class NetBenefitInsufficientTests(unittest.TestCase):
    def test_triggers_when_nb_below_threshold(self) -> None:
        out = build_anti_false_exclusion_display(
            _shell(signals=[_r4_signal(nb=0.022)]),
        )
        names = [f["name"] for f in out["protective_findings"]]
        self.assertIn("net_benefit_insufficient", names)

    def test_does_not_trigger_when_nb_at_or_above_threshold(self) -> None:
        out = build_anti_false_exclusion_display(
            _shell(signals=[_r4_signal(nb=0.05)]),
        )
        names = [f["name"] for f in out["protective_findings"]]
        self.assertNotIn("net_benefit_insufficient", names)

    def test_negative_nb_also_triggers(self) -> None:
        out = build_anti_false_exclusion_display(
            _shell(signals=[_r4_signal(nb=-0.01)]),
        )
        names = [f["name"] for f in out["protective_findings"]]
        self.assertIn("net_benefit_insufficient", names)


class MissingProtectionLayerTests(unittest.TestCase):
    def test_always_triggers_when_signals_present(self) -> None:
        out = build_anti_false_exclusion_display(_shell(signals=[_r4_signal()]))
        names = [f["name"] for f in out["protective_findings"]]
        self.assertIn("missing_protection_layer", names)

    def test_severity_is_high(self) -> None:
        out = build_anti_false_exclusion_display(_shell(signals=[_r4_signal()]))
        f = next(f for f in out["protective_findings"]
                 if f["name"] == "missing_protection_layer")
        self.assertEqual(f["severity"], SEVERITY_HIGH)

    def test_does_not_appear_when_signals_empty(self) -> None:
        out = build_anti_false_exclusion_display(_shell())
        names = [f["name"] for f in out["protective_findings"]]
        self.assertNotIn("missing_protection_layer", names)


# ── primary_reason picking ─────────────────────────────────────────────

class PrimaryReasonTests(unittest.TestCase):
    def test_false_exclusion_rate_wins_over_others(self) -> None:
        out = build_anti_false_exclusion_display(
            _shell(signals=[_r4_signal()]), prediction_correct=True,
        )
        self.assertEqual(out["primary_reason"], "false_exclusion_rate_too_high")

    def test_falls_back_to_first_non_informational(self) -> None:
        # No R4 fer trigger → primary reason should not be that.
        out = build_anti_false_exclusion_display(
            _shell(signals=[_r4_signal(fer=0.05, nb=0.10,
                                        holdout_status="PASS")]),
        )
        # Only missing_protection_layer remains (always present).
        self.assertEqual(out["primary_reason"], "missing_protection_layer")


# ── unknown signal graceful ────────────────────────────────────────────

class UnknownSignalTests(unittest.TestCase):
    def test_unknown_signal_only_emits_missing_protection_layer(self) -> None:
        out = build_anti_false_exclusion_display(
            _shell(signals=[{"name": "wholly_made_up"}]),
        )
        names = [f["name"] for f in out["protective_findings"]]
        self.assertEqual(names, ["missing_protection_layer"])
        self.assertTrue(out["visible"])

    def test_signal_without_metrics_does_not_crash(self) -> None:
        out = build_anti_false_exclusion_display(
            _shell(signals=[{"name": "r4_overextension",
                             "holdout_status": None}]),
        )
        self.assertTrue(out["visible"])


# ── markdown safety ────────────────────────────────────────────────────

class MarkdownSafetyTests(unittest.TestCase):
    def _all_text(self, sm: dict, *, prediction_correct=None) -> str:
        out = build_anti_false_exclusion_display(
            sm, prediction_correct=prediction_correct,
        )
        return render_anti_false_exclusion_markdown(out)

    def test_empty_signals_yields_empty_string(self) -> None:
        self.assertEqual(self._all_text(_shell()), "")

    def test_visible_markdown_includes_safe_title(self) -> None:
        md = self._all_text(_shell(signals=[_r4_signal()]))
        self.assertIn("为什么这里只做提示", md)
        self.assertIn("不改变主推演方向", md)
        self.assertIn("不构成交易指令", md)

    def test_no_forbidden_tokens_present_with_signals(self) -> None:
        for prediction_correct in (None, True, False):
            md = self._all_text(
                _shell(signals=[_r4_signal()]),
                prediction_correct=prediction_correct,
            )
            for token in FORBIDDEN_COPY_TOKENS:
                self.assertNotIn(
                    token, md,
                    f"forbidden token {token!r} appeared in markdown",
                )

    def test_no_forbidden_tokens_for_final_test_refusal(self) -> None:
        md = self._all_text(
            _shell(signals=[_r4_signal()],
                   warnings=["final_test_range_refusal"]),
        )
        for token in FORBIDDEN_COPY_TOKENS:
            self.assertNotIn(token, md)

    def test_no_forbidden_tokens_for_unknown_signal(self) -> None:
        md = self._all_text(_shell(signals=[{"name": "wholly_made_up"}]))
        for token in FORBIDDEN_COPY_TOKENS:
            self.assertNotIn(token, md)

    def test_evidence_numbers_displayed_clearly(self) -> None:
        md = self._all_text(
            _shell(signals=[_r4_signal()]),
            prediction_correct=True,
        )
        # Real R4 numbers should appear
        self.assertIn("32.4%", md)
        self.assertIn("11", md)
        self.assertIn("34", md)


# ── isolation: no DB / network / trading imports ───────────────────────

class IsolationTests(unittest.TestCase):
    def test_module_does_not_import_forbidden(self) -> None:
        import ast
        import ui.anti_false_exclusion_display as mod
        tree = ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))
        forbidden_modules = {
            "yfinance", "requests",
            "longbridge", "broker", "paper_trade",
            "sqlite3", "streamlit", "st",
            "services.soft_metadata_simulator",
            "services.soft_metadata_injection",
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
                    self.assertNotIn(alias.name, forbidden_modules)
            elif isinstance(node, ast.ImportFrom):
                self.assertNotIn(node.module, forbidden_modules)


if __name__ == "__main__":
    unittest.main()
