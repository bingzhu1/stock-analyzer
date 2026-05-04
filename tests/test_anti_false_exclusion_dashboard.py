"""Tests for services/anti_false_exclusion_dashboard.py (Step 2G-7C)."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.anti_false_exclusion_dashboard import (
    summarize_anti_false_exclusion_dashboard,
)


# ── fixtures ────────────────────────────────────────────────────────────

def _baseline(*, paired_total: int = 286,
              r4_paired: int = 34, r4_acc: float = 0.324,
              r4_fer: float = 0.3235, r4_nb: float = 0.0219,
              residual_paired: int = 47, residual_acc: float = 0.489,
              residual_fer: float = 0.489, residual_nb: float = -0.001,
              holdout_status: str = "FAIL") -> dict:
    return {
        "metrics_source": "regime_diagnostics_dashboard_v1",
        "metrics_window": {
            "analysis_date_min": "2023-01-03",
            "analysis_date_max": "2024-08-02",
            "paired_total": paired_total, "db_snapshot_id": None,
        },
        "metrics_computed_at": "2026-05-04T00:00:00",
        "r4_overextension": {
            "samples": 36, "paired": r4_paired,
            "accuracy": r4_acc, "bias_gap": 0.676,
            "false_exclusion_rate": r4_fer, "net_benefit": r4_nb,
        },
        "bullish_high_pos20_residual": {
            "samples": 47, "paired": residual_paired,
            "accuracy": residual_acc, "bias_gap": 0.511,
            "false_exclusion_rate": residual_fer, "net_benefit": residual_nb,
        },
        "holdout_status": holdout_status,
        "warnings": [],
    }


def _empty_baseline() -> dict:
    return {
        "metrics_source": "regime_diagnostics_dashboard_v1",
        "metrics_window": {
            "analysis_date_min": None, "analysis_date_max": None,
            "paired_total": 0, "db_snapshot_id": None,
        },
        "metrics_computed_at": "2026-05-04T00:00:00",
        "r4_overextension": None,
        "bullish_high_pos20_residual": None,
        "holdout_status": "FAIL",
        "warnings": ["baseline_no_records"],
    }


# ── output schema ──────────────────────────────────────────────────────

class OutputSchemaTests(unittest.TestCase):
    def _summary(self, baseline=None):
        baseline = baseline if baseline is not None else _baseline()
        with patch(
            "services.anti_false_exclusion_dashboard.build_soft_metadata_baseline",
            return_value=baseline,
        ):
            return summarize_anti_false_exclusion_dashboard()

    def test_top_level_required_keys_present(self) -> None:
        out = self._summary()
        for key in ("status", "symbol", "records_scanned", "paired_outcomes",
                    "calibration_ready", "metrics_window",
                    "metrics_computed_at", "soft_metadata_summary",
                    "survival_cases", "hard_gate_status",
                    "hard_exclusion_allowed", "primary_blocker", "warnings"):
            self.assertIn(key, out)

    def test_status_ok_with_full_baseline(self) -> None:
        out = self._summary()
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["symbol"], "AVGO")

    def test_calibration_ready_true_when_paired_total_ge_90(self) -> None:
        out = self._summary()
        self.assertTrue(out["calibration_ready"])

    def test_calibration_ready_false_when_paired_total_below_90(self) -> None:
        out = self._summary(_baseline(paired_total=50))
        self.assertFalse(out["calibration_ready"])


# ── R4 / residual metric extraction ────────────────────────────────────

class CandidateExtractionTests(unittest.TestCase):
    def _summary(self, baseline):
        with patch(
            "services.anti_false_exclusion_dashboard.build_soft_metadata_baseline",
            return_value=baseline,
        ):
            return summarize_anti_false_exclusion_dashboard()

    def test_r4_metrics_extracted_correctly(self) -> None:
        out = self._summary(_baseline())
        r4 = out["soft_metadata_summary"]["r4_overextension"]
        self.assertEqual(r4["samples"], 36)
        self.assertEqual(r4["paired"], 34)
        self.assertEqual(r4["accuracy"], 0.324)
        self.assertEqual(r4["false_exclusion_rate"], 0.3235)
        self.assertEqual(r4["net_benefit"], 0.0219)
        self.assertEqual(r4["bias_gap"], 0.676)
        self.assertEqual(r4["holdout_status"], "FAIL")

    def test_correct_when_triggered_derived_from_accuracy_paired(self) -> None:
        # 0.324 × 34 = 11.016 → round to 11
        out = self._summary(_baseline())
        r4 = out["soft_metadata_summary"]["r4_overextension"]
        self.assertEqual(r4["correct_when_triggered"], 11)
        self.assertEqual(r4["wrong_when_triggered"], 34 - 11)

    def test_residual_metrics_extracted_correctly(self) -> None:
        out = self._summary(_baseline())
        r = out["soft_metadata_summary"]["bullish_high_pos20_residual"]
        self.assertEqual(r["paired"], 47)
        self.assertEqual(r["accuracy"], 0.489)
        # 0.489 × 47 = 22.983 → round to 23
        self.assertEqual(r["correct_when_triggered"], 23)
        self.assertEqual(r["wrong_when_triggered"], 24)
        self.assertEqual(r["holdout_status"], "FAIL")

    def test_residual_holdout_inherits_from_baseline_top(self) -> None:
        # Baseline residual has no per-candidate holdout_status; must
        # inherit "FAIL" from baseline top-level.
        out = self._summary(_baseline())
        r = out["soft_metadata_summary"]["bullish_high_pos20_residual"]
        self.assertEqual(r["holdout_status"], "FAIL")


# ── hard gate logic ────────────────────────────────────────────────────

class HardGateTests(unittest.TestCase):
    def _summary(self, baseline):
        with patch(
            "services.anti_false_exclusion_dashboard.build_soft_metadata_baseline",
            return_value=baseline,
        ):
            return summarize_anti_false_exclusion_dashboard()

    def test_default_baseline_yields_4_failing_gates(self) -> None:
        out = self._summary(_baseline())
        gates = out["hard_gate_status"]
        self.assertEqual(gates["total_paired_ge_90"], "pass")
        self.assertEqual(gates["candidate_paired_ge_30"], "pass")
        self.assertEqual(gates["false_exclusion_rate_lte_0_10"], "fail")
        self.assertEqual(gates["net_benefit_gte_0_05"], "fail")
        self.assertEqual(gates["protection_layer_connected"], "fail")
        self.assertEqual(gates["cross_window_holdout_pass"], "fail")

    def test_total_paired_below_90_fails_first_gate(self) -> None:
        out = self._summary(_baseline(paired_total=50))
        self.assertEqual(out["hard_gate_status"]["total_paired_ge_90"], "fail")

    def test_candidate_paired_below_30_fails_second_gate(self) -> None:
        out = self._summary(_baseline(r4_paired=20))
        self.assertEqual(
            out["hard_gate_status"]["candidate_paired_ge_30"], "fail",
        )

    def test_fer_at_or_below_threshold_passes(self) -> None:
        out = self._summary(_baseline(r4_fer=0.10))
        self.assertEqual(
            out["hard_gate_status"]["false_exclusion_rate_lte_0_10"], "pass",
        )

    def test_nb_at_or_above_threshold_passes(self) -> None:
        out = self._summary(_baseline(r4_nb=0.05))
        self.assertEqual(
            out["hard_gate_status"]["net_benefit_gte_0_05"], "pass",
        )

    def test_protection_layer_always_fails_in_v1(self) -> None:
        # Spec invariant: 4 candidate modules all offline; gate is
        # hard-coded "fail" until at least one is wired into main.
        out = self._summary(_baseline())
        self.assertEqual(
            out["hard_gate_status"]["protection_layer_connected"], "fail",
        )

    def test_holdout_pass_only_when_status_is_PASS(self) -> None:
        out = self._summary(_baseline(holdout_status="PASS"))
        self.assertEqual(
            out["hard_gate_status"]["cross_window_holdout_pass"], "pass",
        )

    def test_holdout_fail_when_status_anything_else(self) -> None:
        for status in ("FAIL", "UNKNOWN", "", None):
            out = self._summary(_baseline(holdout_status=status))
            self.assertEqual(
                out["hard_gate_status"]["cross_window_holdout_pass"], "fail",
            )


# ── hard_exclusion_allowed invariant ───────────────────────────────────

class HardExclusionAllowedTests(unittest.TestCase):
    def _summary(self, baseline):
        with patch(
            "services.anti_false_exclusion_dashboard.build_soft_metadata_baseline",
            return_value=baseline,
        ):
            return summarize_anti_false_exclusion_dashboard()

    def test_hard_exclusion_allowed_false_when_any_gate_fails(self) -> None:
        out = self._summary(_baseline())
        self.assertFalse(out["hard_exclusion_allowed"])

    def test_hard_exclusion_allowed_false_with_empty_baseline(self) -> None:
        out = self._summary(_empty_baseline())
        self.assertFalse(out["hard_exclusion_allowed"])

    def test_protection_gate_keeps_hard_false_even_if_others_pass(self) -> None:
        # Even with R4 fer=0.05 / nb=0.10 / holdout=PASS / paired=200,
        # protection layer gate is hard-coded "fail" → overall False.
        out = self._summary(_baseline(
            paired_total=200, r4_paired=50,
            r4_fer=0.05, r4_nb=0.10,
            holdout_status="PASS",
        ))
        gates = out["hard_gate_status"]
        self.assertEqual(gates["false_exclusion_rate_lte_0_10"], "pass")
        self.assertEqual(gates["net_benefit_gte_0_05"], "pass")
        self.assertEqual(gates["cross_window_holdout_pass"], "pass")
        self.assertEqual(gates["protection_layer_connected"], "fail")
        self.assertFalse(out["hard_exclusion_allowed"])


# ── primary_blocker selection ──────────────────────────────────────────

class PrimaryBlockerTests(unittest.TestCase):
    def _summary(self, baseline):
        with patch(
            "services.anti_false_exclusion_dashboard.build_soft_metadata_baseline",
            return_value=baseline,
        ):
            return summarize_anti_false_exclusion_dashboard()

    def test_fer_too_high_wins_when_failing(self) -> None:
        out = self._summary(_baseline())
        self.assertEqual(out["primary_blocker"], "false_exclusion_rate_too_high")

    def test_falls_back_to_net_benefit_when_fer_passes(self) -> None:
        out = self._summary(_baseline(r4_fer=0.05))
        self.assertEqual(out["primary_blocker"], "net_benefit_insufficient")

    def test_falls_back_to_holdout_when_fer_and_nb_pass(self) -> None:
        out = self._summary(_baseline(r4_fer=0.05, r4_nb=0.10))
        self.assertEqual(out["primary_blocker"], "soft_metadata_holdout_fail")

    def test_falls_back_to_protection_layer_when_only_protection_fails(self) -> None:
        out = self._summary(_baseline(
            r4_fer=0.05, r4_nb=0.10, holdout_status="PASS",
        ))
        self.assertEqual(out["primary_blocker"], "missing_protection_layer")


# ── survival_cases ─────────────────────────────────────────────────────

class SurvivalCasesTests(unittest.TestCase):
    def _summary(self, baseline):
        with patch(
            "services.anti_false_exclusion_dashboard.build_soft_metadata_baseline",
            return_value=baseline,
        ):
            return summarize_anti_false_exclusion_dashboard()

    def test_survival_count_equals_correct_when_triggered(self) -> None:
        out = self._summary(_baseline())
        self.assertEqual(out["survival_cases"]["r4_survival_count"], 11)

    def test_survival_rate_equals_accuracy(self) -> None:
        out = self._summary(_baseline())
        self.assertEqual(out["survival_cases"]["r4_survival_rate"], 0.324)


# ── empty / missing baseline ───────────────────────────────────────────

class EmptyBaselineTests(unittest.TestCase):
    def _summary(self, baseline):
        with patch(
            "services.anti_false_exclusion_dashboard.build_soft_metadata_baseline",
            return_value=baseline,
        ):
            return summarize_anti_false_exclusion_dashboard()

    def test_empty_baseline_status_no_records(self) -> None:
        out = self._summary(_empty_baseline())
        self.assertEqual(out["status"], "no_records")

    def test_empty_baseline_soft_metadata_summary_none(self) -> None:
        out = self._summary(_empty_baseline())
        self.assertIsNone(out["soft_metadata_summary"]["r4_overextension"])
        self.assertIsNone(
            out["soft_metadata_summary"]["bullish_high_pos20_residual"],
        )

    def test_empty_baseline_warnings_propagated(self) -> None:
        out = self._summary(_empty_baseline())
        self.assertIn("baseline_no_records", out["warnings"])
        self.assertIn("r4_overextension_unavailable", out["warnings"])
        self.assertIn(
            "bullish_high_pos20_residual_unavailable", out["warnings"]
        )

    def test_empty_baseline_hard_exclusion_still_false(self) -> None:
        out = self._summary(_empty_baseline())
        self.assertFalse(out["hard_exclusion_allowed"])

    def test_baseline_load_exception_returns_error_status(self) -> None:
        with patch(
            "services.anti_false_exclusion_dashboard.build_soft_metadata_baseline",
            side_effect=RuntimeError("db unreadable"),
        ):
            out = summarize_anti_false_exclusion_dashboard()
        self.assertEqual(out["status"], "error")
        self.assertFalse(out["hard_exclusion_allowed"])
        self.assertTrue(any("baseline_load_failed" in w for w in out["warnings"]))


# ── input passthrough ──────────────────────────────────────────────────

class InputPassthroughTests(unittest.TestCase):
    def test_db_path_symbol_limit_passed_to_builder(self) -> None:
        with patch(
            "services.anti_false_exclusion_dashboard.build_soft_metadata_baseline",
            return_value=_baseline(),
        ) as mock_build:
            summarize_anti_false_exclusion_dashboard(
                db_path="/tmp/test.db", symbol="NVDA", limit=100,
            )
        kwargs = mock_build.call_args.kwargs
        self.assertEqual(kwargs["db_path"], "/tmp/test.db")
        self.assertEqual(kwargs["symbol"], "NVDA")
        self.assertEqual(kwargs["limit"], 100)


# ── input immutability ─────────────────────────────────────────────────

class InputImmutabilityTests(unittest.TestCase):
    def test_baseline_dict_not_mutated(self) -> None:
        baseline = _baseline()
        snapshot = deepcopy(baseline)
        with patch(
            "services.anti_false_exclusion_dashboard.build_soft_metadata_baseline",
            return_value=baseline,
        ):
            summarize_anti_false_exclusion_dashboard()
        self.assertEqual(baseline, snapshot)


# ── isolation: no DB / network / trading imports ───────────────────────

class IsolationTests(unittest.TestCase):
    def test_module_does_not_import_forbidden(self) -> None:
        import ast
        import services.anti_false_exclusion_dashboard as mod
        tree = ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))
        forbidden_modules = {
            "yfinance", "requests",
            "longbridge", "broker", "paper_trade",
            "sqlite3",
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

    def test_does_not_call_prediction_store(self) -> None:
        with patch(
            "services.anti_false_exclusion_dashboard.build_soft_metadata_baseline",
            return_value=_baseline(),
        ), patch("services.prediction_store.save_prediction") as sp, \
             patch("services.prediction_store._get_conn") as gc:
            summarize_anti_false_exclusion_dashboard()
        sp.assert_not_called()
        gc.assert_not_called()


# ── CLI smoke ──────────────────────────────────────────────────────────

class CliSmokeTests(unittest.TestCase):
    SCRIPT = ROOT / "scripts" / "anti_false_exclusion_dashboard.py"

    def test_cli_with_mocked_baseline_via_subprocess(self) -> None:
        # Use a wrapper that pre-installs a sitecustomize-style mock
        # via PYTHONSTARTUP; simpler approach: patch the service's
        # build_soft_metadata_baseline at the test process level.
        # Since subprocess inherits a fresh interpreter, we mock by
        # injecting a shim onto the module path. The cleanest approach
        # for an integration smoke test is just to run the script and
        # assert that JSON parses + has the expected top-level shape;
        # the underlying baseline call may return "no_records" against
        # a tmp DB but the dashboard should still produce a valid dict.
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_db = Path(tmpdir) / "empty.db"
            empty_db.touch()
            proc = subprocess.run(
                [
                    sys.executable, str(self.SCRIPT),
                    "--db", str(empty_db),
                    "--symbol", "AVGO", "--limit", "10",
                ],
                capture_output=True, text=True, check=True,
            )
        result = json.loads(proc.stdout)
        # Top-level invariants regardless of baseline outcome:
        self.assertIn("status", result)
        self.assertIn("hard_exclusion_allowed", result)
        self.assertFalse(result["hard_exclusion_allowed"])
        self.assertIn("hard_gate_status", result)


# ── Step 2G-8A.3 — protection_layer_diagnostics aggregate field ────────

class ProtectionLayerDiagnosticsAggregateTests(unittest.TestCase):
    """Step 2G-8A.3: dashboard summary now embeds the
    ``protection_layer_diagnostics`` aggregate. The field exposes the
    helper's spec-locked four connection flags plus a ``guard_summary``
    block (counts + blocking reasons + guard names). It must NOT
    change ``hard_gate_status`` / ``hard_exclusion_allowed`` /
    ``_PROTECTION_LAYER_CONNECTED``."""

    def _summary(self, baseline=None):
        baseline = baseline if baseline is not None else _baseline()
        with patch(
            "services.anti_false_exclusion_dashboard.build_soft_metadata_baseline",
            return_value=baseline,
        ):
            return summarize_anti_false_exclusion_dashboard()

    def test_field_present_in_default_summary(self) -> None:
        out = self._summary()
        self.assertIn("protection_layer_diagnostics", out)
        pld = out["protection_layer_diagnostics"]
        self.assertEqual(
            pld["schema_version"], "protection_layer_diagnostics.v1",
        )

    def test_four_connection_flags_locked(self) -> None:
        pld = self._summary()["protection_layer_diagnostics"]
        self.assertTrue(pld["diagnostic_connected"])
        self.assertFalse(pld["hard_gate_connected"])
        self.assertFalse(pld["required_field_connected"])
        self.assertFalse(pld["protection_layer_connected_for_gate"])

    def test_guard_summary_counts_two_guards_for_default_baseline(self) -> None:
        # Default baseline: holdout=FAIL + net_benefit=+0.0219 → both
        # guards trigger.
        pld = self._summary()["protection_layer_diagnostics"]
        gs = pld["guard_summary"]
        self.assertEqual(gs["total_guard_count"], 2)
        self.assertEqual(gs["blocking_guard_count"], 2)
        self.assertCountEqual(
            gs["guard_names"],
            ["holdout_stability_guard", "net_benefit_guard"],
        )

    def test_blocking_reasons_contain_both_default_reasons(self) -> None:
        pld = self._summary()["protection_layer_diagnostics"]
        reasons = pld["guard_summary"]["blocking_reasons"]
        self.assertEqual(reasons.get("holdout_status_FAIL"), 1)
        self.assertEqual(reasons.get("net_benefit_below_gate"), 1)

    def test_summary_top_level_invariants(self) -> None:
        pld = self._summary()["protection_layer_diagnostics"]
        self.assertTrue(pld["hard_upgrade_blocked"])
        self.assertTrue(pld["display_only"])

    def test_hard_gate_status_still_fail(self) -> None:
        # The new sidecar field MUST NOT flip Gate 5 to pass.
        out = self._summary()
        self.assertEqual(
            out["hard_gate_status"]["protection_layer_connected"], "fail",
        )

    def test_hard_exclusion_allowed_still_false(self) -> None:
        out = self._summary()
        self.assertFalse(out["hard_exclusion_allowed"])

    def test_holdout_pass_only_net_benefit_guard(self) -> None:
        out = self._summary(_baseline(holdout_status="PASS"))
        pld = out["protection_layer_diagnostics"]
        gs = pld["guard_summary"]
        self.assertEqual(gs["guard_names"], ["net_benefit_guard"])
        self.assertEqual(gs["blocking_guard_count"], 1)
        self.assertEqual(
            gs["blocking_reasons"], {"net_benefit_below_gate": 1},
        )
        # Even with both R4 metrics theoretically passing, four-flag
        # invariants stay locked.
        self.assertTrue(pld["diagnostic_connected"])
        self.assertFalse(pld["protection_layer_connected_for_gate"])

    def test_both_r4_pass_zero_guards_but_invariants_intact(self) -> None:
        out = self._summary(_baseline(
            holdout_status="PASS", r4_nb=0.10,
        ))
        pld = out["protection_layer_diagnostics"]
        gs = pld["guard_summary"]
        self.assertEqual(gs["total_guard_count"], 0)
        self.assertEqual(gs["blocking_guard_count"], 0)
        self.assertEqual(gs["blocking_reasons"], {})
        self.assertEqual(gs["guard_names"], [])
        self.assertTrue(pld["hard_upgrade_blocked"])
        self.assertTrue(pld["display_only"])
        self.assertTrue(pld["diagnostic_connected"])
        self.assertFalse(pld["protection_layer_connected_for_gate"])
        # Gate 5 still fail at the dashboard level even when both
        # baseline metrics pass.
        self.assertEqual(
            out["hard_gate_status"]["protection_layer_connected"], "fail",
        )

    def test_no_records_path_safe_zero_counts(self) -> None:
        out = self._summary(_empty_baseline())
        pld = out.get("protection_layer_diagnostics")
        self.assertIsInstance(pld, dict)
        gs = pld["guard_summary"]
        self.assertEqual(gs["total_guard_count"], 0)
        self.assertEqual(gs["blocking_guard_count"], 0)
        self.assertTrue(pld["diagnostic_connected"])
        self.assertFalse(pld["hard_gate_connected"])
        self.assertFalse(pld["required_field_connected"])
        self.assertFalse(pld["protection_layer_connected_for_gate"])
        self.assertTrue(pld["hard_upgrade_blocked"])
        self.assertTrue(pld["display_only"])

    def test_baseline_load_error_path_includes_safe_field(self) -> None:
        # Even when baseline load throws, the field must be present
        # with safe defaults so downstream readers can rely on it.
        with patch(
            "services.anti_false_exclusion_dashboard.build_soft_metadata_baseline",
            side_effect=RuntimeError("db unreadable"),
        ):
            out = summarize_anti_false_exclusion_dashboard()
        self.assertEqual(out["status"], "error")
        self.assertFalse(out["hard_exclusion_allowed"])
        self.assertIn("protection_layer_diagnostics", out)
        pld = out["protection_layer_diagnostics"]
        self.assertEqual(pld["guard_summary"]["total_guard_count"], 0)
        self.assertTrue(pld["diagnostic_connected"])
        self.assertFalse(pld["hard_gate_connected"])
        self.assertFalse(pld["required_field_connected"])
        self.assertFalse(pld["protection_layer_connected_for_gate"])

    def test_module_constant_unchanged(self) -> None:
        # Spec invariant: Step 2G-8A.3 must NOT flip the module-level
        # _PROTECTION_LAYER_CONNECTED from False to True. This assertion
        # locks it explicitly.
        from services.anti_false_exclusion_dashboard import (
            _PROTECTION_LAYER_CONNECTED,
        )
        self.assertFalse(_PROTECTION_LAYER_CONNECTED)


class ProtectionLayerDiagnosticsAggregateIsolationTests(unittest.TestCase):
    """Step 2G-8A.3 must not introduce DB / network / trading imports.
    Helper module is allowed; everything else stays forbidden."""

    def test_module_imports_helper_only(self) -> None:
        import ast
        import services.anti_false_exclusion_dashboard as mod
        tree = ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))
        forbidden_modules = {
            "yfinance", "requests",
            "longbridge", "broker", "paper_trade",
            "sqlite3",
            "services.prediction_store",
            "services.confidence_engine",
            "services.contradiction_engine",
            "services.risk_model",
            "confidence_engine", "contradiction_engine", "risk_model",
            # Step 2G-8A.3 spec: dashboard must not pull in UI / predict
            # paths (helpers stay pure).
            "predict", "scanner",
            "ui.protection_layer_diagnostics_renderer",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(alias.name, forbidden_modules)
            elif isinstance(node, ast.ImportFrom):
                self.assertNotIn(node.module, forbidden_modules)


if __name__ == "__main__":
    unittest.main()
