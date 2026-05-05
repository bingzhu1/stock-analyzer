"""Step 3R-3.1 — read-only continuous smoothing candidate generator tests.

Covers:
  - output schema (top-level keys, schema_version)
  - risk_score in (0, 1) and risk_bucket boundaries
  - market_trend_strength: strong_bull / bull / weak / neutral
  - monthly_shock logic (shock vs breakout vs neutral)
  - missing feature → unknown + warning
  - final_test_refusal (as_of_date >= cutoff, propagated regime_labels)
  - input dict not mutated
  - no validation claims / no forbidden output fields
  - no DB / prediction_store / yfinance / requests / streamlit / trading imports
  - seed_coefficients exposed but not "optimized"
  - adjustment_score = risk_score - 0.5 when risk_score exists
"""
from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.continuous_smoothing_candidate import (
    CANDIDATE_NAME,
    SCHEMA_VERSION,
    SEED_COEFFICIENTS,
    build_continuous_smoothing_candidate,
)


# ── fixtures ─────────────────────────────────────────────────────────────


def _labels(
    *,
    as_of_date: str = "2024-04-15",
    final_test_refusal: bool = False,
    pos20: float | None = 0.5,
    avgo_minus_soxx_20d: float | None = 0.04,
    peer_5d_aligned_pct: float | None = 0.5,
    qqq_60d_slope_per_month: float | None = 0.02,
    qqq_60d_drawdown: float | None = 0.03,
    soxx_60d_slope_per_month: float | None = 0.02,
    monthly_max_abs_daily_return: float | None = 0.02,
    monthly_return_pct: float | None = 0.04,
) -> dict[str, Any]:
    return {
        "schema_version": "regime_labels.v1",
        "as_of_date": as_of_date,
        "data_cutoff_date": as_of_date,
        "labels": {},
        "raw_features": {
            "pos20": pos20,
            "avgo_minus_soxx_20d": avgo_minus_soxx_20d,
            "peer_confirm_count": 2,
            "peer_5d_aligned_pct": peer_5d_aligned_pct,
            "qqq_60d_slope_per_month": qqq_60d_slope_per_month,
            "qqq_60d_drawdown": qqq_60d_drawdown,
            "soxx_60d_slope_per_month": soxx_60d_slope_per_month,
            "monthly_return_pct": monthly_return_pct,
            "monthly_max_abs_daily_return": monthly_max_abs_daily_return,
        },
        "warnings": [],
        "final_test_refusal": final_test_refusal,
    }


# ── 1. output schema ─────────────────────────────────────────────────────


class OutputSchemaTests(unittest.TestCase):
    def test_top_level_keys(self) -> None:
        out = build_continuous_smoothing_candidate(_labels())
        for key in (
            "schema_version",
            "as_of_date",
            "data_cutoff_date",
            "candidate_name",
            "risk_score",
            "adjustment_score",
            "risk_bucket",
            "features_used",
            "warnings",
            "final_test_refusal",
        ):
            self.assertIn(key, out)
        self.assertEqual(out["schema_version"], "continuous_smoothing_candidate.v1")
        self.assertEqual(out["schema_version"], SCHEMA_VERSION)
        self.assertEqual(out["candidate_name"], CANDIDATE_NAME)

    def test_features_used_includes_seed_coefficients(self) -> None:
        out = build_continuous_smoothing_candidate(_labels())
        self.assertIn("seed_coefficients", out["features_used"])
        self.assertEqual(out["features_used"]["seed_coefficients"], SEED_COEFFICIENTS)

    def test_data_cutoff_equals_as_of_date(self) -> None:
        out = build_continuous_smoothing_candidate(_labels(as_of_date="2024-04-15"))
        self.assertEqual(out["data_cutoff_date"], "2024-04-15")
        self.assertEqual(out["as_of_date"], "2024-04-15")


# ── 2. risk_score range / bucket boundaries ─────────────────────────────


class RiskScoreRangeTests(unittest.TestCase):
    def test_risk_score_within_unit_interval(self) -> None:
        out = build_continuous_smoothing_candidate(_labels())
        self.assertIsNotNone(out["risk_score"])
        self.assertGreaterEqual(out["risk_score"], 0.0)
        self.assertLessEqual(out["risk_score"], 1.0)

    def test_risk_bucket_low(self) -> None:
        # Sustained bull + low pos20 + neutral diff → risk_score should be < 0.35
        out = build_continuous_smoothing_candidate(
            _labels(
                pos20=0.10,
                avgo_minus_soxx_20d=-0.05,
                peer_5d_aligned_pct=1.0,
                qqq_60d_slope_per_month=0.02,
                qqq_60d_drawdown=0.02,
                soxx_60d_slope_per_month=0.02,
                monthly_max_abs_daily_return=0.01,
                monthly_return_pct=0.01,
            )
        )
        self.assertLess(out["risk_score"], 0.35)
        self.assertEqual(out["risk_bucket"], "low")

    def test_risk_bucket_extreme(self) -> None:
        # Very high pos20 + AVGO outperforms a lot + weak peer + shock → should
        # be > 0.80
        out = build_continuous_smoothing_candidate(
            _labels(
                pos20=0.99,
                avgo_minus_soxx_20d=0.30,
                peer_5d_aligned_pct=0.0,
                qqq_60d_slope_per_month=-0.02,
                qqq_60d_drawdown=0.20,
                soxx_60d_slope_per_month=-0.02,
                monthly_max_abs_daily_return=0.10,
                monthly_return_pct=0.0,
            )
        )
        self.assertGreaterEqual(out["risk_score"], 0.80)
        self.assertEqual(out["risk_bucket"], "extreme")

    def test_adjustment_score_is_risk_minus_half(self) -> None:
        out = build_continuous_smoothing_candidate(_labels())
        self.assertAlmostEqual(out["adjustment_score"], out["risk_score"] - 0.5, places=10)


# ── 3. market_trend_strength ────────────────────────────────────────────


class MarketTrendStrengthTests(unittest.TestCase):
    def test_strong_bull_branch(self) -> None:
        out = build_continuous_smoothing_candidate(
            _labels(
                qqq_60d_slope_per_month=0.020,
                soxx_60d_slope_per_month=0.020,
                qqq_60d_drawdown=0.02,
            )
        )
        self.assertEqual(out["features_used"]["market_trend_strength"], 1.0)

    def test_bull_branch(self) -> None:
        out = build_continuous_smoothing_candidate(
            _labels(
                qqq_60d_slope_per_month=0.012,
                soxx_60d_slope_per_month=0.005,
                qqq_60d_drawdown=0.04,
            )
        )
        self.assertEqual(out["features_used"]["market_trend_strength"], 0.6)

    def test_weak_branch_high_drawdown(self) -> None:
        out = build_continuous_smoothing_candidate(
            _labels(
                qqq_60d_slope_per_month=0.005,
                soxx_60d_slope_per_month=0.005,
                qqq_60d_drawdown=0.15,
            )
        )
        self.assertEqual(out["features_used"]["market_trend_strength"], -0.5)

    def test_weak_branch_both_negative_slopes(self) -> None:
        out = build_continuous_smoothing_candidate(
            _labels(
                qqq_60d_slope_per_month=-0.01,
                soxx_60d_slope_per_month=-0.01,
                qqq_60d_drawdown=0.04,
            )
        )
        self.assertEqual(out["features_used"]["market_trend_strength"], -0.5)

    def test_neutral_branch(self) -> None:
        out = build_continuous_smoothing_candidate(
            _labels(
                qqq_60d_slope_per_month=0.005,
                soxx_60d_slope_per_month=0.005,
                qqq_60d_drawdown=0.04,
            )
        )
        self.assertEqual(out["features_used"]["market_trend_strength"], 0.0)


# ── 4. monthly_shock ────────────────────────────────────────────────────


class MonthlyShockTests(unittest.TestCase):
    def test_shock_branch(self) -> None:
        out = build_continuous_smoothing_candidate(
            _labels(monthly_max_abs_daily_return=0.10, monthly_return_pct=0.05)
        )
        self.assertEqual(out["features_used"]["monthly_shock"], 1.0)

    def test_breakout_branch(self) -> None:
        out = build_continuous_smoothing_candidate(
            _labels(monthly_max_abs_daily_return=0.04, monthly_return_pct=0.15)
        )
        self.assertEqual(out["features_used"]["monthly_shock"], 0.5)

    def test_neutral_branch(self) -> None:
        out = build_continuous_smoothing_candidate(
            _labels(monthly_max_abs_daily_return=0.02, monthly_return_pct=0.04)
        )
        self.assertEqual(out["features_used"]["monthly_shock"], 0.0)


# ── 5. missing feature ──────────────────────────────────────────────────


class MissingFeatureTests(unittest.TestCase):
    def test_missing_pos20_returns_unknown(self) -> None:
        out = build_continuous_smoothing_candidate(_labels(pos20=None))
        self.assertIsNone(out["risk_score"])
        self.assertIsNone(out["adjustment_score"])
        self.assertEqual(out["risk_bucket"], "unknown")
        self.assertTrue(
            any("missing_required_feature:pos20" in w for w in out["warnings"])
        )

    def test_missing_peer_returns_unknown(self) -> None:
        out = build_continuous_smoothing_candidate(_labels(peer_5d_aligned_pct=None))
        self.assertIsNone(out["risk_score"])
        self.assertEqual(out["risk_bucket"], "unknown")
        self.assertTrue(
            any(
                "missing_required_feature:peer_5d_aligned_pct" in w
                for w in out["warnings"]
            )
        )

    def test_missing_raw_features_dict(self) -> None:
        labels = _labels()
        labels["raw_features"] = None  # type: ignore[assignment]
        out = build_continuous_smoothing_candidate(labels)
        self.assertIsNone(out["risk_score"])
        self.assertEqual(out["risk_bucket"], "unknown")
        self.assertTrue(
            any("missing_required_feature:raw_features" in w for w in out["warnings"])
        )


# ── 6. final_test_refusal ───────────────────────────────────────────────


class FinalTestRefusalTests(unittest.TestCase):
    def test_as_of_date_at_2026_01_01_refused(self) -> None:
        out = build_continuous_smoothing_candidate(
            _labels(as_of_date="2026-01-01"),
        )
        self.assertTrue(out["final_test_refusal"])
        self.assertIsNone(out["risk_score"])
        self.assertEqual(out["risk_bucket"], "unknown")
        self.assertIn("final_test_range_refusal", out["warnings"])

    def test_as_of_date_in_2026_refused(self) -> None:
        out = build_continuous_smoothing_candidate(
            _labels(as_of_date="2026-04-01"),
        )
        self.assertTrue(out["final_test_refusal"])

    def test_explicit_as_of_date_overrides_labels(self) -> None:
        # labels say 2025-06-01 (safe), arg says 2026-02-01 → refusal
        out = build_continuous_smoothing_candidate(
            _labels(as_of_date="2025-06-01"),
            as_of_date="2026-02-01",
        )
        self.assertTrue(out["final_test_refusal"])

    def test_regime_labels_final_test_refusal_propagated(self) -> None:
        labels = _labels(as_of_date="2025-06-01", final_test_refusal=True)
        out = build_continuous_smoothing_candidate(labels)
        self.assertTrue(out["final_test_refusal"])
        self.assertIn(
            "regime_labels_final_test_refusal_propagated", out["warnings"]
        )


# ── 7. immutability + no validation claims + no forbidden imports ───────


class ImmutabilityTests(unittest.TestCase):
    def test_input_dict_not_mutated(self) -> None:
        labels = _labels()
        snapshot = copy.deepcopy(labels)
        build_continuous_smoothing_candidate(labels)
        self.assertEqual(labels, snapshot)


class NoValidationClaimsTests(unittest.TestCase):
    FORBIDDEN_OUTPUT_KEYS = (
        "gate_status",
        "validation_passed",
        "overall_status",
        "hard_exclusion_allowed",
        "hard_gate_status",
        "simulated_trade",
        "no_trade",
        "final_direction",
        "final_projection",
    )

    def _walk_strings(self, obj: Any) -> list[str]:
        if isinstance(obj, str):
            return [obj]
        if isinstance(obj, dict):
            out: list[str] = []
            for k, v in obj.items():
                out.append(str(k))
                out.extend(self._walk_strings(v))
            return out
        if isinstance(obj, (list, tuple)):
            out = []
            for v in obj:
                out.extend(self._walk_strings(v))
            return out
        return []

    def test_no_forbidden_keys_in_output(self) -> None:
        out = build_continuous_smoothing_candidate(_labels())
        for forbidden in self.FORBIDDEN_OUTPUT_KEYS:
            self.assertNotIn(
                forbidden,
                out,
                f"output unexpectedly contains forbidden key {forbidden}",
            )
            # also nested:
            self.assertNotIn(forbidden, out.get("features_used", {}))

    def test_no_pass_fail_validation_strings_in_output(self) -> None:
        out = build_continuous_smoothing_candidate(_labels())
        all_strings = self._walk_strings(out)
        for forbidden in (
            "validation_passed",
            "regime_validation_report.v1",
        ):
            self.assertNotIn(forbidden, all_strings)


class IsolationTests(unittest.TestCase):
    def test_module_does_not_import_forbidden(self) -> None:
        import services.continuous_smoothing_candidate as mod

        tree = ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))
        forbidden_modules = {
            "yfinance",
            "requests",
            "longbridge",
            "broker",
            "paper_trade",
            "sqlite3",
            "services.prediction_store",
            "services.confidence_engine",
            "services.contradiction_engine",
            "services.risk_model",
            "services.soft_metadata_simulator",
            "services.anti_false_exclusion_dashboard",
            "services.regime_diagnostics_dashboard",
            "services.protection_layer_diagnostics",
            "services.historical_replay_training",
            "services.outcome_capture",
            "services.regime_validation_helper",
            "predict",
            "scanner",
            "streamlit",
            "ui.protection_layer_diagnostics_renderer",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(alias.name, forbidden_modules)
            elif isinstance(node, ast.ImportFrom):
                self.assertNotIn(node.module, forbidden_modules)

    def test_module_does_not_use_optimized_terminology(self) -> None:
        import services.continuous_smoothing_candidate as mod

        text = Path(mod.__file__).read_text(encoding="utf-8")
        # design must call them seed coefficients, never claim optimized
        self.assertNotIn("optimized_coefficients", text)
        self.assertNotIn("optimised_coefficients", text)

    def test_module_does_not_reference_hard_or_required_fields(self) -> None:
        import services.continuous_smoothing_candidate as mod

        text = Path(mod.__file__).read_text(encoding="utf-8")
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
                f"helper unexpectedly references {forbidden}",
            )


# ── 8. seed coefficients exposure ───────────────────────────────────────


class SeedCoefficientsTests(unittest.TestCase):
    def test_seed_coefficients_match_design(self) -> None:
        self.assertEqual(SEED_COEFFICIENTS["pos20"], 1.2)
        self.assertEqual(SEED_COEFFICIENTS["avgo_minus_soxx_20d"], 1.0)
        self.assertEqual(SEED_COEFFICIENTS["peer_5d_aligned_pct"], -0.8)
        self.assertEqual(SEED_COEFFICIENTS["market_trend_strength"], -0.7)
        self.assertEqual(SEED_COEFFICIENTS["monthly_shock"], 0.5)

    def test_seed_coefficients_emitted_in_output(self) -> None:
        out = build_continuous_smoothing_candidate(_labels())
        self.assertEqual(
            out["features_used"]["seed_coefficients"],
            SEED_COEFFICIENTS,
        )

    def test_seed_coefficients_dict_is_deep_copy(self) -> None:
        out = build_continuous_smoothing_candidate(_labels())
        out["features_used"]["seed_coefficients"]["pos20"] = 999
        self.assertEqual(SEED_COEFFICIENTS["pos20"], 1.2)


if __name__ == "__main__":
    unittest.main()
