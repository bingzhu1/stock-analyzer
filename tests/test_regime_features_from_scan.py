"""Tests for services/regime_features_builder.py (Step 2G-6B.7)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.regime_features_builder import (
    SCHEMA_SOURCE,
    build_regime_features,
)


# ── fixtures ────────────────────────────────────────────────────────────

def _linear_coded_df(start_close: float = 100.0, step: float = 1.0,
                     count: int = 30, start_date: str = "2024-01-01") -> pd.DataFrame:
    """Linearly-rising daily bars; High = Close + 0.5; Low = Close − 0.5."""
    dates = pd.date_range(start_date, periods=count, freq="D")
    closes = [start_close + step * i for i in range(count)]
    return pd.DataFrame({
        "Date": dates,
        "Open": closes,
        "High": [c + 0.5 for c in closes],
        "Low":  [c - 0.5 for c in closes],
        "Close": closes,
    })


def _flat_coded_df(close: float = 100.0, count: int = 30,
                   start_date: str = "2024-01-01") -> pd.DataFrame:
    """Flat daily bars (used to give SOXX a 0% 20-day return)."""
    dates = pd.date_range(start_date, periods=count, freq="D")
    return pd.DataFrame({
        "Date": dates,
        "Open": [close] * count,
        "High": [close + 0.5] * count,
        "Low":  [close - 0.5] * count,
        "Close": [close] * count,
    })


# ── pos20 calculation ───────────────────────────────────────────────────

class Pos20Tests(unittest.TestCase):
    def test_pos20_at_top_of_range_when_close_at_rolling_high(self) -> None:
        # Linear-up: at day 19 (the 20th bar), close == rolling high.
        df = _linear_coded_df(count=30)
        target = df.iloc[19]["Date"].strftime("%Y-%m-%d")
        out = build_regime_features(df, peer_dfs=None, target_date_str=target)
        self.assertIsNotNone(out["pos20"])
        # Close at highest High in window → pos20 close to 1.0
        self.assertGreater(out["pos20"], 0.9)

    def test_insufficient_history_yields_warning(self) -> None:
        df = _linear_coded_df(count=10)
        target = df.iloc[9]["Date"].strftime("%Y-%m-%d")
        out = build_regime_features(df, peer_dfs=None, target_date_str=target)
        self.assertIsNone(out["pos20"])
        self.assertTrue(any(
            "insufficient_history" in w for w in out["warnings"]
        ))

    def test_missing_target_date_yields_warning(self) -> None:
        df = _linear_coded_df(count=30, start_date="2024-01-01")
        out = build_regime_features(
            df, peer_dfs=None, target_date_str="2030-01-01",
        )
        self.assertIsNone(out["pos20"])
        self.assertTrue(any(
            "pos20_skipped: missing_target_date" in w
            for w in out["warnings"]
        ))


# ── avgo_minus_soxx_20d calculation ────────────────────────────────────

class SoxxDiffTests(unittest.TestCase):
    def test_avgo_rising_soxx_flat_yields_positive_diff(self) -> None:
        avgo = _linear_coded_df(start_close=100.0, step=2.0, count=30)
        soxx = _flat_coded_df(close=100.0, count=30)
        target = avgo.iloc[20]["Date"].strftime("%Y-%m-%d")
        out = build_regime_features(
            avgo, peer_dfs={"SOXX": soxx}, target_date_str=target,
        )
        self.assertIsNotNone(out["avgo_minus_soxx_20d"])
        # AVGO 20d return ≈ ((100+40)/100 - 1) * 100 = 40%
        # SOXX 20d return = 0
        # diff ≈ 40 pp
        self.assertAlmostEqual(out["avgo_minus_soxx_20d"], 40.0, places=4)

    def test_missing_soxx_df_yields_warning(self) -> None:
        avgo = _linear_coded_df(count=30)
        target = avgo.iloc[20]["Date"].strftime("%Y-%m-%d")
        out = build_regime_features(
            avgo, peer_dfs={"SOXX": None}, target_date_str=target,
        )
        self.assertIsNone(out["avgo_minus_soxx_20d"])
        self.assertTrue(any(
            "missing_soxx_coded_df" in w for w in out["warnings"]
        ))

    def test_missing_peer_dfs_yields_warning(self) -> None:
        avgo = _linear_coded_df(count=30)
        target = avgo.iloc[20]["Date"].strftime("%Y-%m-%d")
        out = build_regime_features(
            avgo, peer_dfs=None, target_date_str=target,
        )
        self.assertIsNone(out["avgo_minus_soxx_20d"])
        self.assertTrue(any(
            "missing_soxx_coded_df" in w for w in out["warnings"]
        ))

    def test_soxx_insufficient_history_yields_warning(self) -> None:
        avgo = _linear_coded_df(count=30)
        soxx = _flat_coded_df(count=10)  # too short
        target = avgo.iloc[20]["Date"].strftime("%Y-%m-%d")
        out = build_regime_features(
            avgo, peer_dfs={"SOXX": soxx}, target_date_str=target,
        )
        self.assertIsNone(out["avgo_minus_soxx_20d"])
        self.assertTrue(any(
            "soxx_20d_return_unavailable" in w for w in out["warnings"]
        ))


# ── output shape ────────────────────────────────────────────────────────

class OutputShapeTests(unittest.TestCase):
    def test_required_keys_present(self) -> None:
        avgo = _linear_coded_df(count=30)
        soxx = _flat_coded_df(count=30)
        target = avgo.iloc[20]["Date"].strftime("%Y-%m-%d")
        out = build_regime_features(
            avgo, peer_dfs={"SOXX": soxx}, target_date_str=target,
        )
        for key in ("pos20", "avgo_minus_soxx_20d", "source",
                    "as_of_date", "data_cutoff_date", "warnings"):
            self.assertIn(key, out)
        self.assertEqual(out["source"], SCHEMA_SOURCE)

    def test_data_cutoff_date_equals_as_of_date_anti_lookahead(self) -> None:
        avgo = _linear_coded_df(count=30)
        target = avgo.iloc[20]["Date"].strftime("%Y-%m-%d")
        out = build_regime_features(avgo, peer_dfs=None, target_date_str=target)
        self.assertEqual(out["data_cutoff_date"], out["as_of_date"])

    def test_empty_target_date_does_not_crash(self) -> None:
        out = build_regime_features(None, peer_dfs=None, target_date_str="")
        self.assertIsNone(out["pos20"])
        self.assertIsNone(out["avgo_minus_soxx_20d"])
        self.assertTrue(any(
            "missing_as_of_date" in w for w in out["warnings"]
        ))

    def test_none_coded_df_warns_for_pos20(self) -> None:
        out = build_regime_features(
            None, peer_dfs=None, target_date_str="2024-01-08",
        )
        self.assertIsNone(out["pos20"])
        self.assertTrue(any(
            "missing_avgo_coded_df" in w for w in out["warnings"]
        ))


# ── 2026 final-test cutoff ─────────────────────────────────────────────

class FinalTestCutoffTests(unittest.TestCase):
    def test_as_of_date_after_2026_emits_refusal_warning(self) -> None:
        avgo = _linear_coded_df(count=30, start_date="2026-01-01")
        soxx = _flat_coded_df(count=30, start_date="2026-01-01")
        target = avgo.iloc[20]["Date"].strftime("%Y-%m-%d")
        out = build_regime_features(
            avgo, peer_dfs={"SOXX": soxx}, target_date_str=target,
        )
        self.assertIn("final_test_range_refusal", out["warnings"])

    def test_as_of_date_before_2026_does_not_emit_refusal(self) -> None:
        avgo = _linear_coded_df(count=30, start_date="2025-11-01")
        soxx = _flat_coded_df(count=30, start_date="2025-11-01")
        target = avgo.iloc[20]["Date"].strftime("%Y-%m-%d")
        out = build_regime_features(
            avgo, peer_dfs={"SOXX": soxx}, target_date_str=target,
        )
        self.assertNotIn("final_test_range_refusal", out["warnings"])


# ── isolation: no forbidden imports / no DataFrame mutation ─────────────

class IsolationTests(unittest.TestCase):
    def test_module_does_not_import_forbidden(self) -> None:
        import ast
        import services.regime_features_builder as mod
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

    def test_input_dataframes_are_not_mutated(self) -> None:
        avgo = _linear_coded_df(count=30)
        soxx = _flat_coded_df(count=30)
        snapshot_avgo = avgo.copy(deep=True)
        snapshot_soxx = soxx.copy(deep=True)
        target = avgo.iloc[20]["Date"].strftime("%Y-%m-%d")
        build_regime_features(
            avgo, peer_dfs={"SOXX": soxx}, target_date_str=target,
        )
        pd.testing.assert_frame_equal(avgo, snapshot_avgo)
        pd.testing.assert_frame_equal(soxx, snapshot_soxx)


# ── scanner integration smoke ──────────────────────────────────────────

class ScannerIntegrationSmokeTests(unittest.TestCase):
    """Sanity check that scanner.run_scan now exposes regime_features.

    Note: ``tests/fixtures/app_analysis_context_fixture.py`` does
    ``scanner.run_scan = fake_scan`` as a module-global side effect when
    AppTest loads it; that stub leaks into the test process and would
    mask our integration check. Each test here reloads ``scanner``
    fresh via importlib so the real ``run_scan`` (with the Step 2G-6B.7
    regime_features block) is exercised regardless of test ordering.
    """

    def _fresh_scanner_module(self):
        import importlib
        import scanner as _scanner
        return importlib.reload(_scanner)

    def test_scanner_run_scan_emits_regime_features_field(self) -> None:
        from unittest.mock import patch

        scanner_mod = self._fresh_scanner_module()
        avgo = _linear_coded_df(count=30)
        soxx = _flat_coded_df(count=30)
        target = avgo.iloc[20]["Date"].strftime("%Y-%m-%d")
        empty_df = pd.DataFrame()

        with patch.object(scanner_mod, "load_peer_coded") as load:
            def _by_sym(sym: str):
                return {"SOXX": soxx, "NVDA": None, "QQQ": None}.get(sym)
            load.side_effect = _by_sym
            scan_result = scanner_mod.run_scan(
                target_date_str=target,
                coded_df=avgo,
                exact_df=empty_df,
                near_df=empty_df,
                summary_df=empty_df,
                pos_df=empty_df,
                prev_df=empty_df,
                mom_df=empty_df,
                scan_phase="daily",
            )

        self.assertIn("regime_features", scan_result)
        rf = scan_result["regime_features"]
        self.assertIsNotNone(rf)
        self.assertEqual(rf["source"], SCHEMA_SOURCE)
        self.assertIsNotNone(rf["pos20"])
        self.assertIsNotNone(rf["avgo_minus_soxx_20d"])

    def test_scanner_does_not_break_when_features_builder_unavailable(self) -> None:
        from unittest.mock import patch

        scanner_mod = self._fresh_scanner_module()
        avgo = _linear_coded_df(count=30)
        target = avgo.iloc[20]["Date"].strftime("%Y-%m-%d")
        empty_df = pd.DataFrame()

        with patch.object(scanner_mod, "load_peer_coded", return_value=None), \
             patch("services.regime_features_builder.build_regime_features",
                   side_effect=RuntimeError("simulated failure")):
            scan_result = scanner_mod.run_scan(
                target_date_str=target, coded_df=avgo,
                exact_df=empty_df, near_df=empty_df, summary_df=empty_df,
                pos_df=empty_df, prev_df=empty_df, mom_df=empty_df,
            )
        # Existing scan_result fields must remain intact.
        self.assertIn("scan_bias", scan_result)
        self.assertIn("scan_confidence", scan_result)
        # regime_features falls back to None.
        self.assertIsNone(scan_result["regime_features"])


if __name__ == "__main__":
    unittest.main()
