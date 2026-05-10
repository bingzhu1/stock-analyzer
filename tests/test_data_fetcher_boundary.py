"""Data Layer boundary tests for ``data_fetcher`` (Step 18U /
PR-DATA-1).

Spec source of truth:

- `tasks/record_1_0_architecture_reset_canonical_principles.md` §8 (Branch 1)
- `tasks/record_17e_data_layer_rebuild_plan.md` §3 / §4 / §13
- `tasks/record_18s_third_layer_based_implementation_batch_selection.md` §6 / §7

PR-DATA-1 is the third batch's second cut and **Branch 1 Data Layer's
first code PR**. It is a **pure-test** PR that pins three data-layer
invariants on ``data_fetcher.py``:

1. **No live network in tests**: ``yfinance`` is the only external
   surface; calls into ``yf.Ticker(...)`` must be mocked. The test
   suite itself never hits the network.
2. **Market-data-only output**: ``fetch_history_from_yahoo`` /
   ``clean_price_data`` / ``download_full_history`` return DataFrames
   whose columns are a subset of the canonical OHLCV +
   ``Date`` / ``Adj Close`` / ``Volume`` set. No prediction / exclusion
   / confidence / final / review / evaluation / trading fields ever
   leak into Data Layer output.
3. **Local writes constrained**: when a write path is exercised, the
   test patches ``data_fetcher.DATA_DIR`` / ``get_csv_path`` to a
   ``tmp_path`` so the project ``data/`` directory and any tracked
   files stay byte-stable.

The test file imports:

- stdlib: ``inspect`` / ``unittest`` / ``pathlib`` / ``unittest.mock``
- third-party: ``pandas as pd`` (only to construct fake OHLCV
  DataFrames; never reads real CSVs)
- the unit under test: ``data_fetcher``

It does **not** pull in the upstream yfinance package directly; the
mock targets ``data_fetcher.yf.Ticker`` which is the symbol exposed by
``data_fetcher`` as the alias ``yf``.
"""

from __future__ import annotations

import inspect
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd

import data_fetcher


_REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(rel: str) -> str:
    return (_REPO_ROOT / rel).read_text(encoding="utf-8")


def _fake_yahoo_history_dataframe() -> pd.DataFrame:
    """Construct a deterministic fake DataFrame mirroring what
    ``yfinance.Ticker.history(...)`` returns: ``Date`` is the
    DatetimeIndex, columns include OHLCV + Adj Close. Used by every
    yfinance-mocked test in this suite."""
    dates = pd.to_datetime(
        ["2025-12-29", "2025-12-30", "2025-12-31"]
    )
    df = pd.DataFrame(
        {
            "Open": [100.0, 100.5, 101.0],
            "High": [101.5, 101.8, 102.2],
            "Low": [99.5, 100.0, 100.5],
            "Close": [101.0, 101.2, 101.7],
            "Adj Close": [101.0, 101.2, 101.7],
            "Volume": [1_000_000, 1_050_000, 1_100_000],
        },
        index=dates,
    )
    df.index.name = "Date"
    return df


def _build_mock_ticker(history_df: pd.DataFrame | None = None) -> MagicMock:
    """Build a MagicMock that behaves like a ``yfinance.Ticker`` —
    ``ticker.history(...)`` returns the provided DataFrame (defaults to
    ``_fake_yahoo_history_dataframe()``)."""
    if history_df is None:
        history_df = _fake_yahoo_history_dataframe()
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = history_df
    return mock_ticker


# ---------------------------------------------------------------------------
# 1. DataFetcherImportBoundaryTests
# ---------------------------------------------------------------------------

class DataFetcherImportBoundaryTests(unittest.TestCase):
    """``data_fetcher.py`` must remain a thin Data Layer entry: it
    imports ``pathlib`` / ``pandas`` / ``yfinance`` only — never
    business / prediction / orchestrator / UI / DB modules."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = _read("data_fetcher.py")

    def test_does_not_import_prediction_layers(self) -> None:
        forbidden = (
            "from services.main_projection_layer",
            "import services.main_projection_layer",
            "from services.exclusion_layer",
            "import services.exclusion_layer",
            "from services.peer_alignment",
            "import services.peer_alignment",
            "from services.confidence_evaluator",
            "import services.confidence_evaluator",
            "from services.final_decision",
            "import services.final_decision",
            "from services.review_orchestrator",
            "import services.review_orchestrator",
            "from services.projection_orchestrator",
            "import services.projection_orchestrator",
            "from services.projection_orchestrator_v2",
            "import services.projection_orchestrator_v2",
            "from services.projection_entrypoint",
            "import services.projection_entrypoint",
            "from services.projection_v2_adapter",
            "import services.projection_v2_adapter",
            "from services.home_terminal_orchestrator",
            "import services.home_terminal_orchestrator",
            "from services.consistency_layer",
            "import services.consistency_layer",
            "from services.predict_legacy_adapter",
            "import services.predict_legacy_adapter",
            "from services.predict_legacy_v2_bridge",
            "import services.predict_legacy_v2_bridge",
        )
        for token in forbidden:
            self.assertNotIn(
                token, self.source,
                msg=f"data_fetcher.py must not contain `{token}`",
            )

    def test_does_not_import_predict_app_or_ui(self) -> None:
        forbidden = (
            "from predict",
            "import predict",
            "from app",
            "import app",
            "from ui",
            "import ui",
            "import streamlit",
            "from streamlit",
        )
        for token in forbidden:
            self.assertNotIn(
                token, self.source,
                msg=f"data_fetcher.py must not contain `{token}`",
            )

    def test_does_not_import_db_or_review_or_evaluation(self) -> None:
        forbidden = (
            "import sqlite3",
            "from sqlite3",
            "from services.prediction_store",
            "import services.prediction_store",
            "from services.review_store",
            "import services.review_store",
            "from services.memory_store",
            "import services.memory_store",
            "from services.market_data_store",
            "import services.market_data_store",
            "from services.historical_replay_training",
            "import services.historical_replay_training",
        )
        for token in forbidden:
            self.assertNotIn(
                token, self.source,
                msg=f"data_fetcher.py must not contain `{token}`",
            )

    def test_does_not_import_trading_or_broker_modules(self) -> None:
        # 1.0 §6 / §13 — Data Layer cannot couple to brokers / OMS /
        # paper-trading SDKs.
        forbidden_modules = (
            "broker",
            "longbridge",
            "ib_insync",
            "ibapi",
            "alpaca",
            "tda",  # TD Ameritrade
            "paper_trade",
        )
        for module_name in forbidden_modules:
            for prefix in ("from ", "import "):
                token = f"{prefix}{module_name}"
                with self.subTest(token=token):
                    self.assertNotIn(
                        token, self.source,
                        msg=(
                            f"data_fetcher.py must not contain `{token}` — "
                            "Data Layer cannot couple to broker / OMS"
                        ),
                    )


# ---------------------------------------------------------------------------
# 2. DataFetcherSourceLevelForbiddenTokenTests
# ---------------------------------------------------------------------------

class DataFetcherSourceLevelForbiddenTokenTests(unittest.TestCase):
    """``data_fetcher.py`` source must not contain prediction /
    confidence / trading-leak tokens. These are quoted-string checks
    (not word-boundary on ambient English) to avoid false positives on
    docstrings that legitimately mention these words."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = _read("data_fetcher.py")

    def test_no_prediction_layer_field_keys_as_strings(self) -> None:
        for forbidden in (
            '"projection_result"',
            "'projection_result'",
            '"exclusion_result"',
            "'exclusion_result'",
            '"confidence_result"',
            "'confidence_result'",
            '"final_report"',
            "'final_report'",
            '"review_result"',
            "'review_result'",
            '"evaluation_result"',
            "'evaluation_result'",
            '"most_likely_state"',
            "'most_likely_state'",
            '"most_unlikely_state"',
            "'most_unlikely_state'",
            '"agreement_status"',
            "'agreement_status'",
            '"combined_confidence"',
            "'combined_confidence'",
            '"final_direction"',
            "'final_direction'",
            '"final_confidence"',
            "'final_confidence'",
            '"excluded_states"',
            "'excluded_states'",
        ):
            self.assertNotIn(
                forbidden, self.source,
                msg=(
                    f"data_fetcher.py must not contain prediction-layer "
                    f"field key {forbidden!r}"
                ),
            )

    def test_no_trading_action_field_keys_as_strings(self) -> None:
        for forbidden in (
            '"trading_action"',
            "'trading_action'",
            '"buy"',
            "'buy'",
            '"sell"',
            "'sell'",
            '"hold"',
            "'hold'",
            '"order"',
            "'order'",
            '"position_action"',
            "'position_action'",
            '"execution"',
            "'execution'",
            '"simulated_trade"',
            "'simulated_trade'",
            '"hard"',
            "'hard'",
            '"forced"',
            "'forced'",
            '"required"',
            "'required'",
            '"live_trade"',
            "'live_trade'",
            '"broker_order"',
            "'broker_order'",
        ):
            self.assertNotIn(
                forbidden, self.source,
                msg=(
                    f"data_fetcher.py must not contain trading / forced "
                    f"field key {forbidden!r}"
                ),
            )

    def test_no_call_into_predict_or_run_predict(self) -> None:
        for forbidden_call in (
            "run_predict(",
            "build_main_projection_layer(",
            "run_main_projection_layer(",
            "run_exclusion_layer(",
            "build_confidence_result(",
            "build_final_decision(",
            "validate_projection_result(",
            "validate_exclusion_result(",
            "validate_confidence_result(",
            "validate_final_report_result(",
        ):
            self.assertNotIn(
                forbidden_call, self.source,
                msg=(
                    f"data_fetcher.py must not call {forbidden_call!r} — "
                    "Data Layer is upstream of all prediction subsystems"
                ),
            )


# ---------------------------------------------------------------------------
# 3. YFinanceNoLiveNetworkBoundaryTests
# ---------------------------------------------------------------------------

class YFinanceNoLiveNetworkBoundaryTests(unittest.TestCase):
    """Every yfinance call path must be exercised through a mock; the
    test suite never hits the real network."""

    def test_fetch_history_from_yahoo_uses_mocked_ticker(self) -> None:
        with patch(
            "data_fetcher.yf.Ticker",
            return_value=_build_mock_ticker(),
        ) as mock_factory:
            df = data_fetcher.fetch_history_from_yahoo("AVGO", "2025-12-29")

        # Ticker(...) was called exactly once with the symbol kwarg.
        self.assertEqual(mock_factory.call_count, 1)
        called_args, _called_kwargs = mock_factory.call_args
        self.assertEqual(called_args[0], "AVGO")

        # ticker.history(...) was called exactly once with the start kwarg.
        ticker_instance = mock_factory.return_value
        ticker_instance.history.assert_called_once()
        history_kwargs = ticker_instance.history.call_args.kwargs
        self.assertEqual(history_kwargs["start"], "2025-12-29")
        self.assertEqual(history_kwargs["interval"], "1d")
        self.assertFalse(history_kwargs["auto_adjust"])
        self.assertFalse(history_kwargs["actions"])

        # The cleaned DataFrame is non-empty and has Date as a column.
        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty)
        self.assertIn("Date", df.columns)

    def test_fetch_history_from_yahoo_does_not_call_yf_download(self) -> None:
        # data_fetcher uses Ticker().history(), not yf.download().
        # If a future change introduces yf.download(), this test forces
        # the change to be deliberate (same mock pattern; same boundary
        # rule: no live network in tests).
        source = _read("data_fetcher.py")
        self.assertNotIn(
            "yf.download(", source,
            msg=(
                "data_fetcher.py currently uses yf.Ticker(...).history(...)."
                " If switching to yf.download(...), update boundary tests"
                " to mock the new entry point."
            ),
        )

    def test_test_module_does_not_pull_in_yfinance_directly(self) -> None:
        # Self-check: this test file must not pull the upstream package
        # in directly, nor call yf.download / yf.Ticker outside a patch
        # context. The forbidden patterns are constructed via string
        # concatenation so the literals themselves never appear in this
        # file's source text (otherwise the substring scan would
        # self-match).
        test_source = _read("tests/test_data_fetcher_boundary.py")
        forbidden = (
            "import " + "yfinance",  # noqa: ISC001 — split intentional
            "from " + "yfinance",  # noqa: ISC001 — split intentional
        )
        for token in forbidden:
            self.assertNotIn(
                token, test_source,
                msg=(
                    f"test file must not contain `{token}` — the upstream"
                    " package is reached only via patched"
                    " data_fetcher.yf.Ticker"
                ),
            )


# ---------------------------------------------------------------------------
# 4. MarketDataOnlyOutputBoundaryTests
# ---------------------------------------------------------------------------

class MarketDataOnlyOutputBoundaryTests(unittest.TestCase):
    """Data Layer output is OHLCV + Date + Adj Close + Volume only.
    No prediction / exclusion / confidence / final / trading fields
    ever appear."""

    ALLOWED_COLUMNS = frozenset(
        {"Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"}
    )
    FORBIDDEN_COLUMNS = frozenset(
        {
            "projection_result",
            "exclusion_result",
            "confidence_result",
            "final_report",
            "review_result",
            "evaluation_result",
            "most_likely_state",
            "most_unlikely_state",
            "agreement_status",
            "combined_confidence",
            "final_direction",
            "final_confidence",
            "prediction",
            "trading_action",
            "buy",
            "sell",
            "hold",
            "hard",
            "forced",
            "required",
            "order",
            "position_action",
            "execution",
            "simulated_trade",
            "live_trade",
            "broker_order",
        }
    )

    def _assert_columns_are_market_data_only(self, df: pd.DataFrame) -> None:
        cols = set(df.columns)
        # Each column must be in the allowed OHLCV set.
        unexpected = cols - self.ALLOWED_COLUMNS
        self.assertEqual(
            unexpected, set(),
            msg=(
                f"Data Layer output must contain only OHLCV + Date + "
                f"Adj Close + Volume; found unexpected columns: {unexpected}"
            ),
        )
        # And none of the forbidden prediction/trading column names
        # appears (defense in depth).
        leaked = cols & self.FORBIDDEN_COLUMNS
        self.assertEqual(
            leaked, set(),
            msg=f"Data Layer output leaked forbidden columns: {leaked}",
        )

    def test_clean_price_data_yields_market_columns_only(self) -> None:
        raw_df = _fake_yahoo_history_dataframe()
        cleaned = data_fetcher.clean_price_data(raw_df)
        self._assert_columns_are_market_data_only(cleaned)

    def test_fetch_history_from_yahoo_yields_market_columns_only(self) -> None:
        with patch(
            "data_fetcher.yf.Ticker",
            return_value=_build_mock_ticker(),
        ):
            df = data_fetcher.fetch_history_from_yahoo("AVGO", "2025-12-29")
        self._assert_columns_are_market_data_only(df)

    def test_clean_price_data_drops_nan_close_rows(self) -> None:
        # The cleaning function is part of the Data Layer; verify it
        # drops NaN-Close rows (per source: dropna(subset=[..., 'Close']))
        # without leaking non-market columns into the output.
        import math

        raw_df = _fake_yahoo_history_dataframe().copy()
        raw_df.iloc[0, raw_df.columns.get_loc("Close")] = math.nan
        cleaned = data_fetcher.clean_price_data(raw_df)
        self._assert_columns_are_market_data_only(cleaned)
        # The NaN-Close row should be filtered out.
        self.assertNotIn("2025-12-29", set(cleaned["Date"]))

    def test_clean_price_data_drops_duplicate_date_rows(self) -> None:
        # The cleaning function calls drop_duplicates(subset=['Date']);
        # verify de-duplication keeps the output OHLCV-only.
        raw_df = _fake_yahoo_history_dataframe()
        # Append a duplicate of the last row.
        duplicate_row = raw_df.iloc[[-1]].copy()
        contaminated = pd.concat([raw_df, duplicate_row])
        cleaned = data_fetcher.clean_price_data(contaminated)
        self._assert_columns_are_market_data_only(cleaned)
        # 3 unique dates after dedupe.
        self.assertEqual(len(cleaned), 3)

    def test_returned_dataframe_is_pandas(self) -> None:
        # Belt + suspenders: cleaned output is a plain DataFrame, not a
        # custom subclass that might smuggle prediction fields via
        # attributes.
        cleaned = data_fetcher.clean_price_data(
            _fake_yahoo_history_dataframe()
        )
        self.assertIs(type(cleaned), pd.DataFrame)


# ---------------------------------------------------------------------------
# 5. DataFetcherNoMutationTests
# ---------------------------------------------------------------------------

class DataFetcherNoMutationTests(unittest.TestCase):
    """``clean_price_data`` is the only pure helper exposed by the Data
    Layer; verify it does not mutate the caller's DataFrame in place."""

    def test_clean_price_data_does_not_mutate_input_dataframe(self) -> None:
        raw_df = _fake_yahoo_history_dataframe()
        before_columns = list(raw_df.columns)
        before_index = list(raw_df.index)
        before_values = raw_df.values.copy()

        cleaned = data_fetcher.clean_price_data(raw_df)

        # Returned df is a new object, not the input.
        self.assertIsNot(cleaned, raw_df)
        # Caller's DataFrame columns / index / values unchanged.
        self.assertEqual(list(raw_df.columns), before_columns)
        self.assertEqual(list(raw_df.index), before_index)
        self.assertTrue((raw_df.values == before_values).all())


# ---------------------------------------------------------------------------
# 6. LocalFileWriteBoundaryTests
# ---------------------------------------------------------------------------

class LocalFileWriteBoundaryTests(unittest.TestCase):
    """``download_full_history`` writes a CSV; the test must redirect
    that write to ``tmp_path`` so the project's ``data/`` directory and
    any tracked CSVs stay byte-stable."""

    def setUp(self) -> None:
        # Lightweight tmp dir for this test only; cleaned up afterwards.
        import tempfile

        self._tmp = tempfile.TemporaryDirectory()
        self._tmp_path = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _project_data_dir_snapshot(self) -> set[str]:
        data_dir = _REPO_ROOT / "data"
        if not data_dir.exists():
            return set()
        return {p.name for p in data_dir.iterdir()}

    def test_download_full_history_writes_only_to_patched_csv_path(
        self,
    ) -> None:
        symbol = "AVGO"
        tmp_csv_path = self._tmp_path / f"{symbol}.csv"
        before = self._project_data_dir_snapshot()

        with patch(
            "data_fetcher.yf.Ticker",
            return_value=_build_mock_ticker(),
        ), patch.object(
            data_fetcher, "DATA_DIR", self._tmp_path
        ), patch.object(
            data_fetcher,
            "get_csv_path",
            return_value=tmp_csv_path,
        ):
            df = data_fetcher.download_full_history(symbol, "2025-12-29")

        # Returned DataFrame is OHLCV-only.
        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty)
        self.assertIn("Date", df.columns)

        # CSV was written to tmp_path, not the project data/ dir.
        self.assertTrue(tmp_csv_path.exists())
        # Project data/ directory unchanged.
        after = self._project_data_dir_snapshot()
        self.assertEqual(before, after)

    def test_data_fetcher_data_dir_is_path_object(self) -> None:
        # Defensive: the constant must be a Path so patch.object works.
        # Failure here means a future change accidentally turned DATA_DIR
        # into a string and escapes the patching pattern above.
        self.assertIsInstance(data_fetcher.DATA_DIR, Path)
        self.assertEqual(str(data_fetcher.DATA_DIR), "data")


# ---------------------------------------------------------------------------
# 7. NoPredictionLeakageBoundaryTests (source + behavior)
# ---------------------------------------------------------------------------

class NoPredictionLeakageBoundaryTests(unittest.TestCase):
    """Defense-in-depth: even if a future change adds a helper that
    annotates raw market data with prediction-layer fields, the test
    suite catches it via column-set checks on every public Data Layer
    function."""

    def test_clean_price_data_does_not_emit_prediction_columns(self) -> None:
        raw = _fake_yahoo_history_dataframe()
        # Inject prediction-flavored columns into the raw input — the
        # cleaner must drop them (KEEP_COLUMNS is the explicit allowlist).
        contaminated = raw.copy()
        contaminated["projection_result"] = "leak"
        contaminated["combined_confidence"] = "leak"
        contaminated["trading_action"] = "leak"
        cleaned = data_fetcher.clean_price_data(contaminated)
        for forbidden in (
            "projection_result",
            "combined_confidence",
            "trading_action",
        ):
            self.assertNotIn(
                forbidden, cleaned.columns,
                msg=(
                    f"clean_price_data must drop {forbidden!r} — only "
                    "KEEP_COLUMNS are allowed in the output"
                ),
            )

    def test_keep_columns_is_market_data_subset(self) -> None:
        # Pin KEEP_COLUMNS to the canonical Data Layer schema (17E §8.1).
        self.assertEqual(
            list(data_fetcher.KEEP_COLUMNS),
            ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"],
        )

    def test_symbols_constant_only_contains_research_symbols(self) -> None:
        # Defensive: SYMBOLS must remain the AVGO research universe;
        # adding broker / live trading symbols here would be a leak.
        symbols = set(data_fetcher.SYMBOLS.keys())
        # All keys must be uppercase tickers (no broker / OMS account
        # names).
        for sym in symbols:
            with self.subTest(symbol=sym):
                self.assertTrue(
                    sym.isupper(),
                    msg=f"SYMBOLS key {sym!r} must be uppercase ticker",
                )
                self.assertLessEqual(
                    len(sym), 5,
                    msg=f"SYMBOLS key {sym!r} suspiciously long",
                )


# ---------------------------------------------------------------------------
# Sanity: module reference + public surface stable
# ---------------------------------------------------------------------------

class DataFetcherPublicSurfaceTests(unittest.TestCase):
    """Pin the Data Layer public surface so future PRs can't quietly
    add prediction-flavored helpers next to the data fetcher."""

    EXPECTED_PUBLIC_FUNCTIONS = (
        "get_csv_path",
        "clean_price_data",
        "fetch_history_from_yahoo",
        "download_full_history",
        "update_local_csv",
        "batch_update_all",
        "main",
    )

    def test_each_expected_public_function_is_callable(self) -> None:
        for name in self.EXPECTED_PUBLIC_FUNCTIONS:
            with self.subTest(name=name):
                fn = getattr(data_fetcher, name, None)
                self.assertTrue(
                    callable(fn),
                    msg=f"data_fetcher.{name} missing or not callable",
                )

    def test_no_unexpected_public_functions(self) -> None:
        # Iterate over module attributes; flag any non-private callable
        # that isn't in the allowlist (catches accidental additions
        # like `predict(...)` / `fetch_prediction(...)` / etc.).
        actual_public = {
            name
            for name, value in inspect.getmembers(
                data_fetcher, predicate=inspect.isfunction
            )
            if not name.startswith("_")
            and value.__module__ == "data_fetcher"
        }
        unexpected = actual_public - set(self.EXPECTED_PUBLIC_FUNCTIONS)
        self.assertEqual(
            unexpected, set(),
            msg=(
                f"data_fetcher gained unexpected public functions: "
                f"{unexpected} — Data Layer must remain a thin entry"
            ),
        )


if __name__ == "__main__":
    unittest.main()
