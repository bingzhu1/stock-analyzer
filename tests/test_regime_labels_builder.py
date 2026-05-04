"""Tests for services/regime_labels_builder.py (Step 3R-2)."""
from __future__ import annotations

import ast
import sys
import unittest
from copy import deepcopy
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.regime_labels_builder import (  # noqa: E402
    SCHEMA_VERSION,
    build_regime_labels,
)


# ── fixtures ────────────────────────────────────────────────────────────

def _df_from_closes(
    closes: list[float],
    *,
    start_date: str = "2024-01-01",
) -> pd.DataFrame:
    dates = pd.date_range(start_date, periods=len(closes), freq="D")
    return pd.DataFrame({
        "Date": dates,
        "Open": closes,
        "High": [c + 0.5 for c in closes],
        "Low": [c - 0.5 for c in closes],
        "Close": closes,
    })


def _linear_df(
    start_close: float,
    step: float,
    count: int,
    start_date: str = "2024-01-01",
) -> pd.DataFrame:
    return _df_from_closes(
        [start_close + step * i for i in range(count)],
        start_date=start_date,
    )


def _flat_df(
    close: float,
    count: int,
    start_date: str = "2024-01-01",
) -> pd.DataFrame:
    return _df_from_closes([close] * count, start_date=start_date)


# ── 1. output schema ────────────────────────────────────────────────────

class OutputSchemaTests(unittest.TestCase):
    def test_top_level_keys_present(self) -> None:
        df = _linear_df(100.0, 1.0, 90)
        out = build_regime_labels(df, as_of_date="2024-03-01")
        for key in (
            "schema_version", "as_of_date", "data_cutoff_date",
            "labels", "raw_features", "warnings", "final_test_refusal",
        ):
            self.assertIn(key, out)

    def test_schema_version_locked(self) -> None:
        out = build_regime_labels(
            _linear_df(100.0, 1.0, 90), as_of_date="2024-03-01",
        )
        self.assertEqual(out["schema_version"], SCHEMA_VERSION)
        self.assertEqual(SCHEMA_VERSION, "regime_labels.v1")

    def test_data_cutoff_equals_as_of_date(self) -> None:
        out = build_regime_labels(
            _linear_df(100.0, 1.0, 90), as_of_date="2024-03-01",
        )
        self.assertEqual(out["data_cutoff_date"], out["as_of_date"])

    def test_no_pass_fail_validation_fields_in_output(self) -> None:
        # Step 3R-2 must not claim pass/fail; only Step 3R-4 protocol
        # tools may emit a regime_validation_report.v1.
        out = build_regime_labels(
            _linear_df(100.0, 1.0, 90), as_of_date="2024-03-01",
        )
        forbidden = {
            "overall_status", "gate_status",
            "pass", "fail",
            "validation_status", "validation_passed",
            "candidate_status",
        }
        for key in forbidden:
            self.assertNotIn(key, out)


# ── 2. all five labels present ──────────────────────────────────────────

class LabelsPresentTests(unittest.TestCase):
    def test_five_label_keys_always_present(self) -> None:
        df = _linear_df(100.0, 1.0, 90)
        out = build_regime_labels(df, as_of_date="2024-03-01")
        for key in (
            "pos20_regime",
            "avgo_minus_soxx_20d_regime",
            "peer_momentum_regime",
            "market_trend_regime",
            "monthly_context_regime",
        ):
            self.assertIn(key, out["labels"])

    def test_nine_raw_feature_keys_always_present(self) -> None:
        df = _linear_df(100.0, 1.0, 90)
        out = build_regime_labels(df, as_of_date="2024-03-01")
        for key in (
            "pos20",
            "avgo_minus_soxx_20d",
            "peer_confirm_count",
            "peer_5d_aligned_pct",
            "qqq_60d_slope_per_month",
            "qqq_60d_drawdown",
            "soxx_60d_slope_per_month",
            "monthly_return_pct",
            "monthly_max_abs_daily_return",
        ):
            self.assertIn(key, out["raw_features"])


# ── 3. pos20 bucket boundaries ──────────────────────────────────────────

class Pos20BucketTests(unittest.TestCase):
    def test_extreme_when_close_at_top(self) -> None:
        df = _linear_df(100.0, 1.0, 30)
        target = df.iloc[19]["Date"].strftime("%Y-%m-%d")
        out = build_regime_labels(df, as_of_date=target)
        self.assertEqual(out["labels"]["pos20_regime"], "extreme")
        self.assertGreaterEqual(out["raw_features"]["pos20"], 0.85)

    def test_low_bucket(self) -> None:
        # V-shape: rise then fall to bottom of band
        closes = [100 + i for i in range(15)] + [100 - 0.5 * i for i in range(15)]
        df = _df_from_closes(closes)
        target = df.iloc[28]["Date"].strftime("%Y-%m-%d")
        out = build_regime_labels(df, as_of_date=target)
        # Close ≈ 93 vs band ~100..115 → very low pos
        self.assertIn(out["labels"]["pos20_regime"], ("low", "mid"))

    def test_unknown_when_pos20_unavailable(self) -> None:
        # 5-day df → insufficient history
        df = _linear_df(100.0, 1.0, 5)
        target = df.iloc[4]["Date"].strftime("%Y-%m-%d")
        out = build_regime_labels(df, as_of_date=target)
        self.assertEqual(out["labels"]["pos20_regime"], "unknown")
        self.assertIsNone(out["raw_features"]["pos20"])


# ── 4. avgo_minus_soxx bucket boundaries ────────────────────────────────

class DiffBucketTests(unittest.TestCase):
    def test_extreme_outperform_when_avgo_rises_soxx_flat(self) -> None:
        avgo = _linear_df(100.0, 2.0, 30)  # +40% over 20 days
        soxx = _flat_df(100.0, 30)  # 0%
        target = avgo.iloc[20]["Date"].strftime("%Y-%m-%d")
        out = build_regime_labels(
            avgo, peer_dfs={"SOXX": soxx}, as_of_date=target,
        )
        self.assertEqual(
            out["labels"]["avgo_minus_soxx_20d_regime"],
            "extreme_outperform",
        )
        self.assertGreaterEqual(
            out["raw_features"]["avgo_minus_soxx_20d"], 0.12,
        )

    def test_underperform_when_avgo_below_soxx(self) -> None:
        avgo = _flat_df(100.0, 30)
        # SOXX rises 30% over 20 days
        soxx = _linear_df(100.0, 1.5, 30)
        target = avgo.iloc[20]["Date"].strftime("%Y-%m-%d")
        out = build_regime_labels(
            avgo, peer_dfs={"SOXX": soxx}, as_of_date=target,
        )
        self.assertEqual(
            out["labels"]["avgo_minus_soxx_20d_regime"],
            "underperform",
        )
        self.assertLess(
            out["raw_features"]["avgo_minus_soxx_20d"], -0.05,
        )

    def test_neutral_when_avgo_and_soxx_close(self) -> None:
        avgo = _linear_df(100.0, 0.1, 30)  # +2% over 20 days
        soxx = _linear_df(100.0, 0.1, 30)
        target = avgo.iloc[20]["Date"].strftime("%Y-%m-%d")
        out = build_regime_labels(
            avgo, peer_dfs={"SOXX": soxx}, as_of_date=target,
        )
        self.assertEqual(
            out["labels"]["avgo_minus_soxx_20d_regime"], "neutral",
        )

    def test_unknown_when_soxx_missing(self) -> None:
        avgo = _linear_df(100.0, 2.0, 30)
        target = avgo.iloc[20]["Date"].strftime("%Y-%m-%d")
        out = build_regime_labels(avgo, peer_dfs=None, as_of_date=target)
        self.assertEqual(
            out["labels"]["avgo_minus_soxx_20d_regime"], "unknown",
        )
        self.assertIsNone(out["raw_features"]["avgo_minus_soxx_20d"])


# ── 5. peer_momentum count / bucket ─────────────────────────────────────

class PeerMomentumTests(unittest.TestCase):
    def test_three_rising_peers_overheated(self) -> None:
        avgo = _linear_df(100.0, 1.0, 90)
        nvda = _linear_df(500.0, 5.0, 90)
        soxx = _linear_df(100.0, 1.0, 90)
        qqq = _linear_df(400.0, 4.0, 90)
        target = avgo.iloc[60]["Date"].strftime("%Y-%m-%d")
        out = build_regime_labels(
            avgo,
            peer_dfs={"NVDA": nvda, "SOXX": soxx, "QQQ": qqq},
            as_of_date=target,
        )
        self.assertEqual(out["raw_features"]["peer_confirm_count"], 3)
        self.assertEqual(
            out["labels"]["peer_momentum_regime"], "overheated",
        )

    def test_two_rising_one_flat_confirmed(self) -> None:
        avgo = _linear_df(100.0, 1.0, 90)
        nvda = _linear_df(500.0, 5.0, 90)
        soxx = _flat_df(100.0, 90)
        qqq = _linear_df(400.0, 4.0, 90)
        target = avgo.iloc[60]["Date"].strftime("%Y-%m-%d")
        out = build_regime_labels(
            avgo,
            peer_dfs={"NVDA": nvda, "SOXX": soxx, "QQQ": qqq},
            as_of_date=target,
        )
        self.assertEqual(out["raw_features"]["peer_confirm_count"], 2)
        self.assertEqual(
            out["labels"]["peer_momentum_regime"], "confirmed",
        )

    def test_all_flat_peers_weak(self) -> None:
        avgo = _linear_df(100.0, 1.0, 90)
        flat = _flat_df(100.0, 90)
        target = avgo.iloc[60]["Date"].strftime("%Y-%m-%d")
        out = build_regime_labels(
            avgo,
            peer_dfs={"NVDA": flat, "SOXX": flat, "QQQ": flat},
            as_of_date=target,
        )
        self.assertEqual(out["raw_features"]["peer_confirm_count"], 0)
        self.assertEqual(
            out["labels"]["peer_momentum_regime"], "weak",
        )

    def test_no_peers_unknown_with_warnings(self) -> None:
        avgo = _linear_df(100.0, 1.0, 90)
        target = avgo.iloc[60]["Date"].strftime("%Y-%m-%d")
        out = build_regime_labels(avgo, peer_dfs={}, as_of_date=target)
        self.assertEqual(
            out["labels"]["peer_momentum_regime"], "unknown",
        )
        self.assertIsNone(out["raw_features"]["peer_confirm_count"])
        # Warnings include each missing peer
        joined = " ".join(out["warnings"])
        self.assertIn("missing_NVDA", joined)
        self.assertIn("missing_SOXX", joined)
        self.assertIn("missing_QQQ", joined)


# ── 6. market_trend bucket ──────────────────────────────────────────────

class MarketTrendTests(unittest.TestCase):
    def test_sustained_bull_when_qqq_and_soxx_rising_strong(self) -> None:
        # Need slope > 0.015 (i.e., 60d return > 4.5%, since /3)
        # Use 1.0% per day → 60d return ≈ 60%, slope ≈ 0.20/month
        avgo = _linear_df(100.0, 1.0, 90)
        qqq = _linear_df(400.0, 4.0, 90)  # +1%/day
        soxx = _linear_df(100.0, 1.0, 90)
        target = avgo.iloc[80]["Date"].strftime("%Y-%m-%d")
        out = build_regime_labels(
            avgo,
            market_dfs={"QQQ": qqq, "SOXX": soxx},
            peer_dfs={"SOXX": soxx},
            as_of_date=target,
        )
        self.assertEqual(
            out["labels"]["market_trend_regime"], "sustained_bull_market",
        )

    def test_bull_when_only_qqq_rising(self) -> None:
        avgo = _linear_df(100.0, 1.0, 90)
        qqq = _linear_df(400.0, 4.0, 90)
        soxx = _flat_df(100.0, 90)
        target = avgo.iloc[80]["Date"].strftime("%Y-%m-%d")
        out = build_regime_labels(
            avgo,
            market_dfs={"QQQ": qqq, "SOXX": soxx},
            peer_dfs={"SOXX": soxx},
            as_of_date=target,
        )
        # qqq slope > 0.01 alone qualifies as bull_market
        self.assertEqual(
            out["labels"]["market_trend_regime"], "bull_market",
        )

    def test_weak_when_both_falling(self) -> None:
        avgo = _flat_df(100.0, 90)
        qqq = _linear_df(400.0, -3.0, 90)
        soxx = _linear_df(100.0, -1.0, 90)
        target = avgo.iloc[80]["Date"].strftime("%Y-%m-%d")
        out = build_regime_labels(
            avgo,
            market_dfs={"QQQ": qqq, "SOXX": soxx},
            peer_dfs={"SOXX": soxx},
            as_of_date=target,
        )
        self.assertEqual(
            out["labels"]["market_trend_regime"], "weak_market",
        )

    def test_unknown_when_no_market_data(self) -> None:
        avgo = _linear_df(100.0, 1.0, 90)
        target = avgo.iloc[80]["Date"].strftime("%Y-%m-%d")
        out = build_regime_labels(avgo, peer_dfs={}, as_of_date=target)
        self.assertEqual(
            out["labels"]["market_trend_regime"], "unknown",
        )

    def test_market_dfs_takes_precedence_over_peer_dfs(self) -> None:
        # Confirm market_dfs is preferred when both provided.
        avgo = _linear_df(100.0, 1.0, 90)
        qqq_strong = _linear_df(400.0, 4.0, 90)
        qqq_flat = _flat_df(400.0, 90)
        soxx = _flat_df(100.0, 90)
        target = avgo.iloc[80]["Date"].strftime("%Y-%m-%d")
        out = build_regime_labels(
            avgo,
            market_dfs={"QQQ": qqq_strong, "SOXX": soxx},
            peer_dfs={"QQQ": qqq_flat, "SOXX": soxx},
            as_of_date=target,
        )
        # market_dfs strong should give bull_market not neutral
        self.assertIn(
            out["labels"]["market_trend_regime"],
            ("bull_market", "sustained_bull_market"),
        )


# ── 7. monthly_context bucket ───────────────────────────────────────────

class MonthlyContextTests(unittest.TestCase):
    def test_breakout_month_when_in_month_return_high(self) -> None:
        # Calendar month returns > 12% within month
        # Build a 90-day df starting Jan 1, target on Mar 25, with
        # rapid rise during March.
        closes = (
            [100 + i for i in range(60)]  # Jan + Feb gentle
            + [160 + 2 * i for i in range(30)]  # Mar accelerated
        )
        df = _df_from_closes(closes, start_date="2024-01-01")
        target = df.iloc[80]["Date"].strftime("%Y-%m-%d")  # Mar 21
        out = build_regime_labels(df, as_of_date=target)
        self.assertEqual(
            out["labels"]["monthly_context_regime"], "breakout_month",
        )

    def test_shock_month_when_max_abs_daily_high(self) -> None:
        # Insert a +10% single-day jump in March
        closes = [100 + 0.5 * i for i in range(60)]  # Jan/Feb stable
        # Mar: Mar 1 (idx 60) = 130, Mar 2 (idx 61) = 130 * 1.10 = 143
        closes.append(closes[-1] * 1.10)
        # Then resume slow drift
        for _ in range(28):
            closes.append(closes[-1] + 0.1)
        df = _df_from_closes(closes, start_date="2024-01-01")
        target = df.iloc[70]["Date"].strftime("%Y-%m-%d")
        out = build_regime_labels(df, as_of_date=target)
        self.assertEqual(
            out["labels"]["monthly_context_regime"], "shock_month",
        )

    def test_earnings_month_label_for_quarter_months(self) -> None:
        # June with stable prices → not breakout, not shock, month=6
        # → earnings_month
        df = _linear_df(100.0, 0.05, 200, start_date="2024-01-01")
        # Pick a date in June
        target_date = df[df["Date"].dt.month == 6].iloc[10]["Date"].strftime(
            "%Y-%m-%d",
        )
        out = build_regime_labels(df, as_of_date=target_date)
        self.assertEqual(
            out["labels"]["monthly_context_regime"], "earnings_month",
        )

    def test_normal_month_when_stable_april(self) -> None:
        # April (month=4) with stable prices → "normal"
        df = _linear_df(100.0, 0.05, 200, start_date="2024-01-01")
        target_date = df[df["Date"].dt.month == 4].iloc[10]["Date"].strftime(
            "%Y-%m-%d",
        )
        out = build_regime_labels(df, as_of_date=target_date)
        self.assertEqual(
            out["labels"]["monthly_context_regime"], "normal",
        )


# ── 8. missing peers graceful unknown + warning ────────────────────────

class MissingPeersGracefulTests(unittest.TestCase):
    def test_missing_one_peer_still_aggregates_others(self) -> None:
        avgo = _linear_df(100.0, 1.0, 90)
        nvda = _linear_df(500.0, 5.0, 90)
        soxx = _linear_df(100.0, 1.0, 90)
        # No QQQ
        target = avgo.iloc[60]["Date"].strftime("%Y-%m-%d")
        out = build_regime_labels(
            avgo,
            peer_dfs={"NVDA": nvda, "SOXX": soxx},
            as_of_date=target,
        )
        # 2 of 2 confirmed
        self.assertEqual(out["raw_features"]["peer_confirm_count"], 2)
        # peer_5d_aligned_pct = 1.0 (2/2)
        self.assertAlmostEqual(
            out["raw_features"]["peer_5d_aligned_pct"], 1.0,
        )
        # Missing QQQ produces a warning
        self.assertTrue(
            any("missing_QQQ" in w for w in out["warnings"])
        )


# ── 9. missing QQQ/SOXX graceful unknown + warning ─────────────────────

class MissingMarketGracefulTests(unittest.TestCase):
    def test_missing_qqq_emits_warning(self) -> None:
        avgo = _linear_df(100.0, 1.0, 90)
        soxx = _linear_df(100.0, 1.0, 90)
        target = avgo.iloc[80]["Date"].strftime("%Y-%m-%d")
        out = build_regime_labels(
            avgo,
            market_dfs={"SOXX": soxx},
            peer_dfs={"SOXX": soxx},
            as_of_date=target,
        )
        self.assertIsNone(out["raw_features"]["qqq_60d_slope_per_month"])
        self.assertTrue(
            any("missing_QQQ" in w for w in out["warnings"])
        )

    def test_missing_both_market_dfs_unknown_label(self) -> None:
        avgo = _linear_df(100.0, 1.0, 90)
        target = avgo.iloc[80]["Date"].strftime("%Y-%m-%d")
        out = build_regime_labels(
            avgo, market_dfs={}, peer_dfs={}, as_of_date=target,
        )
        self.assertEqual(
            out["labels"]["market_trend_regime"], "unknown",
        )


# ── 10. final_test_refusal when as_of_date >= 2026-01-01 ───────────────

class FinalTestRefusalTests(unittest.TestCase):
    def test_refusal_on_or_after_2026(self) -> None:
        df = _linear_df(100.0, 1.0, 90, start_date="2025-12-01")
        out = build_regime_labels(df, as_of_date="2026-01-15")
        self.assertTrue(out["final_test_refusal"])
        self.assertTrue(
            any("final_test_range_refusal" in w for w in out["warnings"])
        )
        # All labels = "unknown"
        for v in out["labels"].values():
            self.assertEqual(v, "unknown")
        # All raw features = None
        for v in out["raw_features"].values():
            self.assertIsNone(v)

    def test_no_refusal_before_2026(self) -> None:
        df = _linear_df(100.0, 1.0, 90)
        out = build_regime_labels(df, as_of_date="2024-03-01")
        self.assertFalse(out["final_test_refusal"])
        self.assertNotIn(
            "final_test_range_refusal", out["warnings"],
        )

    def test_custom_cutoff_respected(self) -> None:
        df = _linear_df(100.0, 1.0, 90, start_date="2024-01-01")
        out = build_regime_labels(
            df,
            as_of_date="2024-06-01",
            final_test_cutoff="2024-05-01",
        )
        self.assertTrue(out["final_test_refusal"])


# ── 11. anti-lookahead rows > as_of_date ignored ───────────────────────

class AntiLookaheadTests(unittest.TestCase):
    def test_future_rows_in_df_do_not_affect_pos20(self) -> None:
        # Build 90-day df, query at day 30; future rows must not leak.
        # Compare with 30-day df → same pos20.
        full_df = _linear_df(100.0, 1.0, 90, start_date="2024-01-01")
        target = full_df.iloc[29]["Date"].strftime("%Y-%m-%d")
        truncated = full_df.iloc[:30].copy()
        out_full = build_regime_labels(full_df, as_of_date=target)
        out_short = build_regime_labels(truncated, as_of_date=target)
        self.assertAlmostEqual(
            out_full["raw_features"]["pos20"],
            out_short["raw_features"]["pos20"],
            places=10,
        )

    def test_future_rows_do_not_affect_diff(self) -> None:
        full_avgo = _linear_df(100.0, 1.0, 90)
        full_soxx = _flat_df(100.0, 90)
        target = full_avgo.iloc[25]["Date"].strftime("%Y-%m-%d")
        out_full = build_regime_labels(
            full_avgo, peer_dfs={"SOXX": full_soxx}, as_of_date=target,
        )
        out_short = build_regime_labels(
            full_avgo.iloc[:26].copy(),
            peer_dfs={"SOXX": full_soxx.iloc[:26].copy()},
            as_of_date=target,
        )
        self.assertAlmostEqual(
            out_full["raw_features"]["avgo_minus_soxx_20d"],
            out_short["raw_features"]["avgo_minus_soxx_20d"],
            places=10,
        )


# ── 12. input DataFrame not mutated ────────────────────────────────────

class InputImmutabilityTests(unittest.TestCase):
    def test_avgo_df_not_mutated(self) -> None:
        df = _linear_df(100.0, 1.0, 90)
        snap = df.copy(deep=True)
        build_regime_labels(df, as_of_date="2024-03-01")
        pd.testing.assert_frame_equal(df, snap)

    def test_peer_dfs_not_mutated(self) -> None:
        avgo = _linear_df(100.0, 1.0, 90)
        nvda = _linear_df(500.0, 5.0, 90)
        soxx = _flat_df(100.0, 90)
        snap_nvda = nvda.copy(deep=True)
        snap_soxx = soxx.copy(deep=True)
        peer = {"NVDA": nvda, "SOXX": soxx}
        snap_peer = dict(peer)
        build_regime_labels(avgo, peer_dfs=peer, as_of_date="2024-03-01")
        pd.testing.assert_frame_equal(nvda, snap_nvda)
        pd.testing.assert_frame_equal(soxx, snap_soxx)
        self.assertEqual(peer, snap_peer)


# ── 13. isolation: no DB / network / trading imports ───────────────────

class IsolationTests(unittest.TestCase):
    def test_module_does_not_import_forbidden(self) -> None:
        import services.regime_labels_builder as mod
        tree = ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))
        forbidden_modules = {
            "yfinance", "requests",
            "longbridge", "broker", "paper_trade",
            "sqlite3",
            "services.prediction_store",
            "services.confidence_engine",
            "services.contradiction_engine",
            "services.risk_model",
            "services.soft_metadata_simulator",
            "services.anti_false_exclusion_dashboard",
            "services.regime_diagnostics_dashboard",
            "predict", "scanner",
            "streamlit",
            "ui.protection_layer_diagnostics_renderer",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(alias.name, forbidden_modules)
            elif isinstance(node, ast.ImportFrom):
                self.assertNotIn(node.module, forbidden_modules)


# ── 14. no pass/fail validation fields in output ───────────────────────

class NoValidationClaimsTests(unittest.TestCase):
    def test_output_does_not_contain_pass_fail_strings(self) -> None:
        # Step 3R-2 helper must never claim validation pass/fail.
        df = _linear_df(100.0, 1.0, 90)
        nvda = _linear_df(500.0, 5.0, 90)
        soxx = _linear_df(100.0, 1.0, 90)
        qqq = _linear_df(400.0, 4.0, 90)
        out = build_regime_labels(
            df,
            peer_dfs={"NVDA": nvda, "SOXX": soxx, "QQQ": qqq},
            as_of_date="2024-03-25",
        )

        # Walk the dict; ensure no value is "pass" / "fail" /
        # "validation_passed" / regime_validation_report schema strings.
        forbidden_values = {
            "pass", "fail",
            "validation_passed",
            "regime_validation_report.v1",
        }

        def walk(obj):
            if isinstance(obj, dict):
                for v in obj.values():
                    walk(v)
            elif isinstance(obj, list):
                for v in obj:
                    walk(v)
            elif isinstance(obj, str):
                self.assertNotIn(obj, forbidden_values)

        walk(out)


if __name__ == "__main__":
    unittest.main()
