"""Step 3R-3.3F-A — continuous_smoothing_v2 candidate tests.

Covers:
  - output schema (top-level keys, schema_version, candidate_name)
  - risk_bucket ∈ {abstain, low, medium, high, extreme}
  - risk_score in (0, 1) when not abstain; None when abstain
  - bucket reachable for low / medium / high / extreme via fixtures
  - abstain on as_of_date >= cutoff (final_test_range_refusal)
  - abstain on regime_labels.final_test_refusal=True (propagated)
  - abstain on missing raw_features
  - abstain on low trigger_support
  - abstain on missing as_of_date
  - trigger_support present at top-level + features_used
  - features_used contains all 8 family keys + raw_inputs
  - leaky outcome / W4 future-leak fields ignored when injected
  - no forbidden output fields
  - deterministic output for same input (no clock / no randomness)
  - input regime_labels not mutated
  - explicit as_of_date overrides regime_labels.as_of_date
  - works with minimal valid regime_labels fixture
  - calibration_context descriptor declares NOT fitted
  - isolation: no forbidden imports
  - isolation: no v1 candidate import
  - isolation: no hard / forced / required / no_trade strings
  - isolation: no validation pass/fail strings
  - isolation: no threshold sweep / grid search strings
"""
from __future__ import annotations

import ast
import copy
import math
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.continuous_smoothing_candidate_v2 import (  # noqa: E402
    ALLOWED_RISK_BUCKETS,
    CANDIDATE_NAME,
    DEFAULT_FINAL_TEST_CUTOFF,
    FEATURE_FAMILY_KEYS,
    SCHEMA_VERSION,
    build_continuous_smoothing_candidate_v2,
)


# ── fixtures ────────────────────────────────────────────────────────────


def _labels(
    *,
    as_of_date: str = "2024-04-15",
    final_test_refusal: bool = False,
    pos20: float | None = 0.5,
    avgo_minus_soxx_20d: float | None = 0.0,
    peer_5d_aligned_pct: float | None = 0.5,
    qqq_60d_slope_per_month: float | None = 0.02,
    qqq_60d_drawdown: float | None = 0.03,
    soxx_60d_slope_per_month: float | None = 0.02,
    monthly_max_abs_daily_return: float | None = 0.04,
    monthly_return_pct: float | None = 0.04,
    extra_raw_features: dict[str, Any] | None = None,
    extra_top_level: dict[str, Any] | None = None,
) -> dict[str, Any]:
    raw_features: dict[str, Any] = {
        "pos20": pos20,
        "avgo_minus_soxx_20d": avgo_minus_soxx_20d,
        "peer_5d_aligned_pct": peer_5d_aligned_pct,
        "qqq_60d_slope_per_month": qqq_60d_slope_per_month,
        "qqq_60d_drawdown": qqq_60d_drawdown,
        "soxx_60d_slope_per_month": soxx_60d_slope_per_month,
        "monthly_max_abs_daily_return": monthly_max_abs_daily_return,
        "monthly_return_pct": monthly_return_pct,
    }
    if extra_raw_features:
        raw_features.update(extra_raw_features)
    payload: dict[str, Any] = {
        "schema_version": "regime_labels.v1",
        "as_of_date": as_of_date,
        "data_cutoff_date": as_of_date,
        "labels": {},
        "raw_features": raw_features,
        "warnings": [],
        "final_test_refusal": final_test_refusal,
    }
    if extra_top_level:
        payload.update(extra_top_level)
    return payload


# ── 1. output schema ────────────────────────────────────────────────────


class OutputSchemaTests(unittest.TestCase):
    def test_top_level_keys(self) -> None:
        out = build_continuous_smoothing_candidate_v2(_labels())
        for key in (
            "schema_version",
            "as_of_date",
            "data_cutoff_date",
            "candidate_name",
            "risk_score",
            "risk_bucket",
            "abstain_reason",
            "trigger_support",
            "features_used",
            "warnings",
            "final_test_refusal",
        ):
            self.assertIn(key, out)

    def test_schema_version_and_candidate_name(self) -> None:
        out = build_continuous_smoothing_candidate_v2(_labels())
        self.assertEqual(
            out["schema_version"], "continuous_smoothing_candidate_v2.v1"
        )
        self.assertEqual(out["schema_version"], SCHEMA_VERSION)
        self.assertEqual(out["candidate_name"], "continuous_smoothing_v2")
        self.assertEqual(out["candidate_name"], CANDIDATE_NAME)

    def test_risk_bucket_in_allowed_set(self) -> None:
        out = build_continuous_smoothing_candidate_v2(_labels())
        self.assertIn(out["risk_bucket"], ALLOWED_RISK_BUCKETS)
        self.assertEqual(
            ALLOWED_RISK_BUCKETS,
            frozenset({"abstain", "low", "medium", "high", "extreme"}),
        )

    def test_features_used_has_eight_family_keys_plus_raw_inputs(self) -> None:
        out = build_continuous_smoothing_candidate_v2(_labels())
        self.assertIn("features_used", out)
        for fam in FEATURE_FAMILY_KEYS:
            self.assertIn(fam, out["features_used"])
        self.assertEqual(len(FEATURE_FAMILY_KEYS), 8)
        self.assertIn("raw_inputs", out["features_used"])

    def test_no_forbidden_output_fields(self) -> None:
        out = build_continuous_smoothing_candidate_v2(_labels())
        forbidden = (
            "gate_status",
            "validation_passed",
            "overall_status",
            "hard_gate_status",
            "hard_exclusion_allowed",
            "forced_exclusion",
            "anti_false_exclusion_triggered",
            "_PROTECTION_LAYER_CONNECTED",
            "primary_blocker",
            "final_direction",
            "final_projection",
            "simulated_trade",
            "no_trade",
            "predict_result_json",
            "research_result_json",
            "scan_result_json",
            "actual_close_change",
            "actual_state",
            "direction_correct",
            "five_state_projection",
            "seed_coefficients",
        )
        for f in forbidden:
            self.assertNotIn(f, out)
            if isinstance(out.get("features_used"), dict):
                self.assertNotIn(f, out["features_used"])


# ── 2. risk_score range and bucket reachability ─────────────────────────


class RiskScoreRangeTests(unittest.TestCase):
    def test_risk_score_in_zero_one_when_not_abstain(self) -> None:
        out = build_continuous_smoothing_candidate_v2(_labels())
        self.assertNotEqual(out["risk_bucket"], "abstain")
        self.assertIsInstance(out["risk_score"], float)
        self.assertGreater(out["risk_score"], 0.0)
        self.assertLess(out["risk_score"], 1.0)

    def test_low_risk_fixture_yields_low_bucket(self) -> None:
        # Strong continuation context + strong peer + low volatility.
        out = build_continuous_smoothing_candidate_v2(
            _labels(
                pos20=0.4,
                avgo_minus_soxx_20d=0.0,
                peer_5d_aligned_pct=0.9,
                qqq_60d_slope_per_month=0.02,
                qqq_60d_drawdown=0.02,
                soxx_60d_slope_per_month=0.02,
                monthly_max_abs_daily_return=0.02,
            )
        )
        self.assertEqual(out["risk_bucket"], "low")
        self.assertLess(out["risk_score"], 0.33)

    def test_medium_risk_fixture_yields_medium_bucket(self) -> None:
        # Default-ish: all family contributions cancel out → ~ 0.5.
        out = build_continuous_smoothing_candidate_v2(
            _labels(
                pos20=0.5,
                avgo_minus_soxx_20d=0.0,
                peer_5d_aligned_pct=0.4,
                qqq_60d_slope_per_month=0.005,
                qqq_60d_drawdown=0.04,
                soxx_60d_slope_per_month=0.005,
                monthly_max_abs_daily_return=0.04,
            )
        )
        self.assertEqual(out["risk_bucket"], "medium")
        self.assertGreaterEqual(out["risk_score"], 0.33)
        self.assertLess(out["risk_score"], 0.55)

    def test_high_risk_fixture_yields_high_bucket(self) -> None:
        # Overextension without confirmation, drawdown moderate.
        out = build_continuous_smoothing_candidate_v2(
            _labels(
                pos20=0.7,
                avgo_minus_soxx_20d=0.04,
                peer_5d_aligned_pct=0.3,
                qqq_60d_slope_per_month=0.005,
                qqq_60d_drawdown=0.07,
                soxx_60d_slope_per_month=0.005,
                monthly_max_abs_daily_return=0.05,
            )
        )
        self.assertEqual(out["risk_bucket"], "high")
        self.assertGreaterEqual(out["risk_score"], 0.55)
        self.assertLess(out["risk_score"], 0.75)

    def test_extreme_risk_fixture_yields_extreme_bucket(self) -> None:
        # Overextension + reversal + shock + instability.
        out = build_continuous_smoothing_candidate_v2(
            _labels(
                pos20=0.8,
                avgo_minus_soxx_20d=0.06,
                peer_5d_aligned_pct=0.1,
                qqq_60d_slope_per_month=-0.01,
                qqq_60d_drawdown=0.12,
                soxx_60d_slope_per_month=-0.01,
                monthly_max_abs_daily_return=0.10,
                monthly_return_pct=0.12,
            )
        )
        self.assertEqual(out["risk_bucket"], "extreme")
        self.assertGreaterEqual(out["risk_score"], 0.75)


# ── 3. abstain mode ─────────────────────────────────────────────────────


class AbstainTests(unittest.TestCase):
    def test_abstain_when_as_of_date_at_cutoff(self) -> None:
        out = build_continuous_smoothing_candidate_v2(
            _labels(as_of_date="2026-01-01")
        )
        self.assertEqual(out["risk_bucket"], "abstain")
        self.assertIsNone(out["risk_score"])
        self.assertEqual(out["abstain_reason"], "final_test_range_refusal")
        self.assertTrue(out["final_test_refusal"])
        self.assertIn("final_test_range_refusal", out["warnings"])

    def test_abstain_when_as_of_date_after_cutoff(self) -> None:
        out = build_continuous_smoothing_candidate_v2(
            _labels(as_of_date="2099-01-01")
        )
        self.assertEqual(out["risk_bucket"], "abstain")
        self.assertTrue(out["final_test_refusal"])

    def test_abstain_when_regime_labels_final_test_refusal_true(self) -> None:
        out = build_continuous_smoothing_candidate_v2(
            _labels(as_of_date="2024-04-15", final_test_refusal=True)
        )
        self.assertEqual(out["risk_bucket"], "abstain")
        self.assertTrue(out["final_test_refusal"])
        self.assertEqual(out["abstain_reason"], "final_test_range_refusal")
        self.assertIn(
            "regime_labels_final_test_refusal_propagated", out["warnings"]
        )

    def test_abstain_when_raw_features_missing(self) -> None:
        labels = _labels()
        del labels["raw_features"]
        out = build_continuous_smoothing_candidate_v2(labels)
        self.assertEqual(out["risk_bucket"], "abstain")
        self.assertEqual(out["abstain_reason"], "missing_raw_features")
        self.assertFalse(out["final_test_refusal"])
        self.assertIn("missing_raw_features", out["warnings"])
        self.assertIsNone(out["risk_score"])

    def test_abstain_when_trigger_support_low(self) -> None:
        # Only 2 of 8 raw inputs present → trigger_support = 0.25 < 0.5.
        labels = _labels()
        labels["raw_features"] = {
            "pos20": 0.5,
            "peer_5d_aligned_pct": 0.5,
        }
        out = build_continuous_smoothing_candidate_v2(labels)
        self.assertEqual(out["risk_bucket"], "abstain")
        self.assertEqual(out["abstain_reason"], "low_trigger_support")
        self.assertIsNotNone(out["trigger_support"])
        self.assertLess(out["trigger_support"], 0.5)
        self.assertFalse(out["final_test_refusal"])
        self.assertIn("low_trigger_support", out["warnings"])

    def test_abstain_when_as_of_date_missing_explicit_arg_and_label(self) -> None:
        labels = _labels()
        del labels["as_of_date"]
        out = build_continuous_smoothing_candidate_v2(labels, as_of_date=None)
        self.assertEqual(out["risk_bucket"], "abstain")
        self.assertEqual(out["abstain_reason"], "missing_as_of_date")
        self.assertIn("missing_as_of_date", out["warnings"])

    def test_abstain_payload_still_contains_eight_family_keys(self) -> None:
        out = build_continuous_smoothing_candidate_v2(
            _labels(as_of_date="2026-04-23")
        )
        self.assertEqual(out["risk_bucket"], "abstain")
        for fam in FEATURE_FAMILY_KEYS:
            self.assertIn(fam, out["features_used"])
        self.assertIn("raw_inputs", out["features_used"])


# ── 4. trigger_support exposure ─────────────────────────────────────────


class TriggerSupportTests(unittest.TestCase):
    def test_trigger_support_exposed_top_level_and_in_features_used(self) -> None:
        out = build_continuous_smoothing_candidate_v2(_labels())
        self.assertIn("trigger_support", out)
        self.assertIn("trigger_support", out["features_used"])
        self.assertEqual(
            out["trigger_support"], out["features_used"]["trigger_support"]
        )
        self.assertIsNotNone(out["trigger_support"])

    def test_trigger_support_full_when_all_inputs_present(self) -> None:
        out = build_continuous_smoothing_candidate_v2(_labels())
        self.assertEqual(out["trigger_support"], 1.0)


# ── 5. leak / mutation / determinism / override ─────────────────────────


class IsolationFromLeakTests(unittest.TestCase):
    def test_outcome_and_w4_fields_are_ignored(self) -> None:
        leaky_extra_raw = {
            "actual_close_change": 0.12,
            "direction_correct": True,
            "actual_state": "小涨",
            "five_state_projection": {"小涨": 0.99},
        }
        leaky_top_level = {
            "predict_result_json": "{}",
            "research_result_json": "{}",
            "scan_result_json": "{}",
        }
        clean = build_continuous_smoothing_candidate_v2(_labels())
        leaky = build_continuous_smoothing_candidate_v2(
            _labels(
                extra_raw_features=leaky_extra_raw,
                extra_top_level=leaky_top_level,
            )
        )
        # The leaky inputs must not change the candidate output.
        self.assertEqual(clean["risk_score"], leaky["risk_score"])
        self.assertEqual(clean["risk_bucket"], leaky["risk_bucket"])
        for fam in FEATURE_FAMILY_KEYS:
            self.assertEqual(
                clean["features_used"][fam],
                leaky["features_used"][fam],
            )


class InputNotMutatedTests(unittest.TestCase):
    def test_input_dict_not_mutated_across_calls(self) -> None:
        labels = _labels()
        snapshot = copy.deepcopy(labels)
        build_continuous_smoothing_candidate_v2(labels)
        build_continuous_smoothing_candidate_v2(labels)
        self.assertEqual(labels, snapshot)


class DeterminismTests(unittest.TestCase):
    def test_same_input_yields_same_output(self) -> None:
        a = build_continuous_smoothing_candidate_v2(_labels())
        b = build_continuous_smoothing_candidate_v2(_labels())
        self.assertEqual(a, b)

    def test_calibration_context_declares_not_fitted(self) -> None:
        out = build_continuous_smoothing_candidate_v2(_labels())
        ctx = out["features_used"]["calibration_context"]
        self.assertIsInstance(ctx, dict)
        self.assertEqual(ctx.get("fitted_to_v1_baseline"), False)
        self.assertEqual(ctx.get("fitted_to_outcome_data"), False)
        self.assertIn("trigger_support_threshold", ctx)
        self.assertIn("bucket_boundaries", ctx)


class AsOfDateOverrideTests(unittest.TestCase):
    def test_explicit_as_of_date_overrides_label_field(self) -> None:
        labels = _labels(as_of_date="2024-04-15")
        out = build_continuous_smoothing_candidate_v2(
            labels, as_of_date="2025-08-21"
        )
        self.assertEqual(out["as_of_date"], "2025-08-21")
        self.assertEqual(out["data_cutoff_date"], "2025-08-21")

    def test_minimal_valid_regime_labels_works(self) -> None:
        minimal = {
            "schema_version": "regime_labels.v1",
            "as_of_date": "2024-04-15",
            "data_cutoff_date": "2024-04-15",
            "raw_features": {
                "pos20": 0.5,
                "avgo_minus_soxx_20d": 0.0,
                "peer_5d_aligned_pct": 0.5,
                "qqq_60d_slope_per_month": 0.02,
                "qqq_60d_drawdown": 0.03,
                "soxx_60d_slope_per_month": 0.02,
                "monthly_max_abs_daily_return": 0.04,
                "monthly_return_pct": 0.04,
            },
        }
        out = build_continuous_smoothing_candidate_v2(minimal)
        self.assertEqual(out["schema_version"], SCHEMA_VERSION)
        self.assertEqual(out["candidate_name"], CANDIDATE_NAME)
        self.assertNotEqual(out["risk_bucket"], "abstain")
        self.assertIsInstance(out["risk_score"], float)


# ── 6. isolation: forbidden imports / strings ───────────────────────────


class IsolationTests(unittest.TestCase):
    def _module_text(self) -> str:
        import services.continuous_smoothing_candidate_v2 as mod

        return Path(mod.__file__).read_text(encoding="utf-8")

    def test_no_forbidden_imports(self) -> None:
        import services.continuous_smoothing_candidate_v2 as mod

        tree = ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))
        forbidden = {
            "yfinance",
            "requests",
            "urllib",
            "urllib3",
            "httpx",
            "longbridge",
            "broker",
            "paper_trade",
            "sqlite3",
            "services.prediction_store",
            "services.outcome_capture",
            "services.confidence_engine",
            "services.contradiction_engine",
            "services.risk_model",
            "services.soft_metadata_simulator",
            "services.anti_false_exclusion_dashboard",
            "services.regime_diagnostics_dashboard",
            "services.protection_layer_diagnostics",
            "services.historical_replay_training",
            "services.regime_validation_helper",
            "services.replay_validation_record_adapter",
            "services.real_regime_label_provider",
            "services.regime_labels_builder",
            # v2 must NOT import v1 candidate.
            "services.continuous_smoothing_candidate",
            "scripts.run_continuous_smoothing_validation",
            "scripts.run_real_continuous_smoothing_validation",
            "scripts.run_real_continuous_smoothing_validation_execute",
            "predict",
            "scanner",
            "streamlit",
            "ui.protection_layer_diagnostics_renderer",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(alias.name, forbidden)
            elif isinstance(node, ast.ImportFrom):
                self.assertNotIn(node.module, forbidden)

    def test_no_v1_module_string_reference(self) -> None:
        text = self._module_text()
        # Even string-level references to v1 module are disallowed
        # (defensive: the module must be conceptually independent).
        self.assertNotIn(
            "services.continuous_smoothing_candidate ", text
        )
        self.assertNotIn(
            "from services.continuous_smoothing_candidate import", text
        )

    def test_no_hard_required_or_trading_strings(self) -> None:
        text = self._module_text()
        # Note: yfinance / paper_trade / longbridge are caught by the
        # import scan above; they are intentionally referenced in the
        # docstring's negative-claim list and would false-positive here.
        for forbidden in (
            "hard_exclusion_allowed",
            "forced_exclusion",
            "anti_false_exclusion_triggered",
            "_PROTECTION_LAYER_CONNECTED",
            "simulated_trade",
            "no_trade",
            "final_direction",
            "final_projection",
        ):
            self.assertNotIn(
                forbidden,
                text,
                f"v2 unexpectedly references {forbidden!r}",
            )

    def test_no_validation_pass_fail_strings(self) -> None:
        text = self._module_text()
        for forbidden in (
            "gate_status",
            "validation_passed",
            "overall_status",
            "primary_blocker",
            "hard_gate_status",
        ):
            self.assertNotIn(forbidden, text)

    def test_no_threshold_sweep_or_grid_strings(self) -> None:
        text = self._module_text()
        for forbidden in (
            "thresholds = [",
            "for threshold in",
            "for t in thresholds",
            "candidate_thresholds",
            "threshold_grid",
            "optimize_threshold",
            "sweep_threshold",
            "grid_search",
        ):
            self.assertNotIn(forbidden, text)

    def test_no_fitted_to_v1_baseline_claim(self) -> None:
        # The module must not claim it is fitted / optimized. The
        # calibration_context dict explicitly negates fitting via
        # `fitted_to_v1_baseline=False` / `fitted_to_outcome_data=False`,
        # so we check for affirmative claim phrases only.
        text = self._module_text()
        for forbidden in (
            "optimized_to_v1",
            "validated_against_baseline",
            "tuned_via_baseline",
            "is_validated",
        ):
            self.assertNotIn(forbidden, text)
        # And make sure the calibration_context descriptor still negates
        # fitting (catches accidental inversion).
        out = build_continuous_smoothing_candidate_v2(_labels())
        ctx = out["features_used"]["calibration_context"]
        self.assertFalse(ctx.get("fitted_to_v1_baseline"))
        self.assertFalse(ctx.get("fitted_to_outcome_data"))

    def test_default_final_test_cutoff_is_2026_01_01(self) -> None:
        self.assertEqual(DEFAULT_FINAL_TEST_CUTOFF, "2026-01-01")


if __name__ == "__main__":
    unittest.main()
