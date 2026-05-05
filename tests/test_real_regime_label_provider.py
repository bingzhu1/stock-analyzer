"""Step 3R-3.3C-C-B — real regime label provider tests.

Covers:
  - _load_market_csv success + missing-file / missing-column / duplicate-Date errors
  - factory raises if any of the four CSVs is missing
  - provider returns regime_labels.v1 schema
  - provider passes as_of_date to builder
  - provider ignores row content (no outcome / W4 leak)
  - provider final_test_refusal=False at 2025-12-31
  - provider final_test_refusal=True at 2026-01-01
  - provider does not mutate loaded DataFrames across calls
  - isolation: no forbidden imports
  - isolation: no hard / forced / required / no_trade / threshold-sweep strings
  - isolation: no W4 jsonl outcome / future-leak field references in source
"""
from __future__ import annotations

import ast
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.real_regime_label_provider import (  # noqa: E402
    DEFAULT_FINAL_TEST_CUTOFF,
    REQUIRED_COLUMNS,
    _load_market_csv,
    build_real_regime_label_provider,
)


# ── fixtures ────────────────────────────────────────────────────────────


def _write_csv(path: Path, *, n: int = 250, start: str = "2022-06-01") -> None:
    """Write a synthetic OHLC csv with N business-day rows."""
    dates = pd.bdate_range(start, periods=n)
    closes = [100.0 + i * 0.1 for i in range(n)]
    df = pd.DataFrame(
        {
            "Date": dates.strftime("%Y-%m-%d"),
            "Open": closes,
            "High": [c + 0.5 for c in closes],
            "Low": [c - 0.5 for c in closes],
            "Close": closes,
            "Adj Close": closes,
            "Volume": [1_000_000] * n,
        }
    )
    df.to_csv(path, index=False)


def _write_csv_missing_close(path: Path, *, n: int = 60) -> None:
    dates = pd.bdate_range("2023-01-02", periods=n)
    df = pd.DataFrame(
        {
            "Date": dates.strftime("%Y-%m-%d"),
            "Open": [100.0] * n,
            "High": [101.0] * n,
            "Low": [99.0] * n,
            # Close missing intentionally
        }
    )
    df.to_csv(path, index=False)


def _write_csv_with_duplicate_date(path: Path) -> None:
    df = pd.DataFrame(
        {
            "Date": ["2024-01-02", "2024-01-03", "2024-01-03", "2024-01-04"],
            "Open": [1.0] * 4,
            "High": [1.0] * 4,
            "Low": [1.0] * 4,
            "Close": [1.0] * 4,
        }
    )
    df.to_csv(path, index=False)


class _CsvBundle:
    """Helper: write four synthetic CSVs and remember their paths."""

    def __init__(self, tmp: Path, *, n: int = 600, start: str = "2022-06-01"):
        self.tmp = tmp
        self.avgo = tmp / "AVGO.csv"
        self.nvda = tmp / "NVDA.csv"
        self.soxx = tmp / "SOXX.csv"
        self.qqq = tmp / "QQQ.csv"
        for p in (self.avgo, self.nvda, self.soxx, self.qqq):
            _write_csv(p, n=n, start=start)


# ── 1. _load_market_csv ─────────────────────────────────────────────────


class LoadMarketCsvTests(unittest.TestCase):
    def test_load_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "AVGO.csv"
            _write_csv(path, n=10)
            df = _load_market_csv(str(path), symbol="AVGO")
        for col in REQUIRED_COLUMNS:
            self.assertIn(col, df.columns)
        # Date should be parsed to a datetime-like dtype
        self.assertEqual(str(df["Date"].dtype).startswith("datetime"), True)
        self.assertEqual(len(df), 10)

    def test_missing_file_raises_file_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nope.csv"
            with self.assertRaises(FileNotFoundError):
                _load_market_csv(str(path), symbol="AVGO")

    def test_missing_required_column_raises_value_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken.csv"
            _write_csv_missing_close(path)
            with self.assertRaises(ValueError):
                _load_market_csv(str(path), symbol="AVGO")

    def test_duplicate_date_raises_value_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dup.csv"
            _write_csv_with_duplicate_date(path)
            with self.assertRaises(ValueError):
                _load_market_csv(str(path), symbol="AVGO")

    def test_unsorted_input_is_sorted_after_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "unsorted.csv"
            df = pd.DataFrame(
                {
                    "Date": ["2024-01-05", "2024-01-02", "2024-01-04"],
                    "Open": [1.0, 2.0, 3.0],
                    "High": [1.0, 2.0, 3.0],
                    "Low": [1.0, 2.0, 3.0],
                    "Close": [1.0, 2.0, 3.0],
                }
            )
            df.to_csv(path, index=False)
            loaded = _load_market_csv(str(path), symbol="AVGO")
        dates = list(loaded["Date"])
        self.assertEqual(dates, sorted(dates))


# ── 2. factory: required-paths fail-fast ────────────────────────────────


class FactoryRequiredPathsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.bundle = _CsvBundle(self.tmp)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_missing_avgo_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            build_real_regime_label_provider(
                avgo_csv_path=str(self.tmp / "absent.csv"),
                nvda_csv_path=str(self.bundle.nvda),
                soxx_csv_path=str(self.bundle.soxx),
                qqq_csv_path=str(self.bundle.qqq),
            )

    def test_missing_nvda_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            build_real_regime_label_provider(
                avgo_csv_path=str(self.bundle.avgo),
                nvda_csv_path=str(self.tmp / "absent.csv"),
                soxx_csv_path=str(self.bundle.soxx),
                qqq_csv_path=str(self.bundle.qqq),
            )

    def test_missing_soxx_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            build_real_regime_label_provider(
                avgo_csv_path=str(self.bundle.avgo),
                nvda_csv_path=str(self.bundle.nvda),
                soxx_csv_path=str(self.tmp / "absent.csv"),
                qqq_csv_path=str(self.bundle.qqq),
            )

    def test_missing_qqq_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            build_real_regime_label_provider(
                avgo_csv_path=str(self.bundle.avgo),
                nvda_csv_path=str(self.bundle.nvda),
                soxx_csv_path=str(self.bundle.soxx),
                qqq_csv_path=str(self.tmp / "absent.csv"),
            )


# ── 3. provider behavior ────────────────────────────────────────────────


class ProviderBehaviorTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.bundle = _CsvBundle(self.tmp, n=900, start="2022-06-01")
        self.provider = build_real_regime_label_provider(
            avgo_csv_path=str(self.bundle.avgo),
            nvda_csv_path=str(self.bundle.nvda),
            soxx_csv_path=str(self.bundle.soxx),
            qqq_csv_path=str(self.bundle.qqq),
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_returns_regime_labels_v1(self) -> None:
        out = self.provider("2024-05-15")
        self.assertEqual(out["schema_version"], "regime_labels.v1")
        self.assertEqual(out["as_of_date"], "2024-05-15")
        self.assertIn("labels", out)
        self.assertIn("raw_features", out)
        self.assertIn("warnings", out)
        self.assertIn("final_test_refusal", out)

    def test_passes_as_of_date_to_builder(self) -> None:
        out_a = self.provider("2024-05-15")
        out_b = self.provider("2024-08-01")
        self.assertEqual(out_a["as_of_date"], "2024-05-15")
        self.assertEqual(out_b["as_of_date"], "2024-08-01")

    def test_ignores_row_content(self) -> None:
        # Pass a row dict that includes outcome / W4 fields the provider
        # must NOT consult.
        leaky_row = {
            "as_of_date": "2024-05-15",
            "prediction_for_date": "2024-05-16",
            "direction_correct": True,
            "actual_state": "小涨",
            "actual_close_change": 0.01,
            "pos20": 0.99,
            "five_state_projection": {"小涨": 0.99},
        }
        out_with_row = self.provider("2024-05-15", leaky_row)
        out_without_row = self.provider("2024-05-15", None)
        # row content must not change the output
        self.assertEqual(out_with_row, out_without_row)

    def test_final_test_refusal_false_pre_cutoff(self) -> None:
        out = self.provider("2025-12-31")
        self.assertFalse(out["final_test_refusal"])

    def test_final_test_refusal_true_at_cutoff(self) -> None:
        out = self.provider("2026-01-01")
        self.assertTrue(out["final_test_refusal"])
        self.assertIn(
            "final_test_range_refusal",
            "\n".join(str(w) for w in out["warnings"]),
        )

    def test_does_not_mutate_dataframes_across_calls(self) -> None:
        # Snapshot first DataFrame and verify second call leaves it unchanged.
        first = self.provider("2024-05-15")
        # Read the AVGO CSV again from disk; row counts must be identical
        # to the first read (no DataFrame trimming / mutation).
        df_after_first = pd.read_csv(self.bundle.avgo)
        self.provider("2024-08-01")
        df_after_second = pd.read_csv(self.bundle.avgo)
        self.assertTrue(df_after_first.equals(df_after_second))
        # First payload also shouldn't be mutated by a later call.
        snapshot = deepcopy(first)
        _ = self.provider("2024-08-01")
        self.assertEqual(first, snapshot)


# ── 4. isolation / forbidden imports / strings ──────────────────────────


class IsolationTests(unittest.TestCase):
    def _module_text(self) -> str:
        import services.real_regime_label_provider as mod

        return Path(mod.__file__).read_text(encoding="utf-8")

    def test_no_forbidden_imports(self) -> None:
        import services.real_regime_label_provider as mod

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
            "predict",
            "scanner",
            "streamlit",
            "ui.protection_layer_diagnostics_renderer",
            # Must not import the orchestrator or wrapper either; the
            # provider is a building block that the execution glue
            # (Step 3R-3.3C-C-C) wires together.
            "scripts.run_continuous_smoothing_validation",
            "scripts.run_real_continuous_smoothing_validation",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(alias.name, forbidden)
            elif isinstance(node, ast.ImportFrom):
                self.assertNotIn(node.module, forbidden)

    def test_no_hard_required_or_trading_strings(self) -> None:
        text = self._module_text()
        for forbidden in (
            "hard_exclusion_allowed",
            "forced_exclusion",
            "anti_false_exclusion_triggered",
            "_PROTECTION_LAYER_CONNECTED",
            "simulated_trade",
            "no_trade",
            "final_direction",
            "final_projection",
            "yfinance",
            "paper_trade",
            "longbridge",
        ):
            self.assertNotIn(
                forbidden,
                text,
                f"provider unexpectedly references {forbidden!r}",
            )

    def test_no_threshold_sweep_strings(self) -> None:
        text = self._module_text()
        for forbidden in (
            "thresholds = [",
            "for threshold in",
            "for t in thresholds",
            "candidate_thresholds",
            "threshold_grid",
            "optimize_threshold",
            "sweep_threshold",
        ):
            self.assertNotIn(forbidden, text)

    def test_no_w4_outcome_fields_referenced(self) -> None:
        text = self._module_text()
        # The provider must not name W4 jsonl outcome / future-leak
        # fields anywhere in its source — that is a structural guarantee
        # that it cannot peek at them.
        for forbidden in (
            "actual_close_change",
            "actual_state",
            "direction_correct",
            "five_state_projection",
            "predict_result_json",
            "research_result_json",
            "scan_result_json",
        ):
            self.assertNotIn(forbidden, text)

    def test_default_final_test_cutoff(self) -> None:
        # Sanity: cutoff default matches the 6-layer hard-stop value.
        self.assertEqual(DEFAULT_FINAL_TEST_CUTOFF, "2026-01-01")


if __name__ == "__main__":
    unittest.main()
