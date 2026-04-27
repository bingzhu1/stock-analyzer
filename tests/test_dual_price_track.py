from __future__ import annotations

# ---------------------------------------------------------------------------
# AVGO 2026-04-23 reference values (verified via yfinance full-history download)
#
#   Open      = 422.39
#   Close     = 419.94
#   Adj Close = 419.94
#
# Close == Adj Close on this date because Dividends = 0 and Stock Splits = 0;
# the adjustment factor is 1.  This is NORMAL behaviour — it does NOT indicate
# the dual-price-track system has failed.  The two columns will diverge on any
# day that carries a dividend or split event.
#
# The earlier value 425.19 came from an incomplete intraday bar captured before
# market close (volume ~5 M vs the final ~19 M).  It has been superseded by the
# full-history re-download.
# ---------------------------------------------------------------------------

import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_fetcher import clean_price_data
from feature_builder import build_features
from encoder import encode_dataframe, encode_c_move
from data_quality_check import check_adjustment_days


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_raw_df(n: int = 5, with_adj: bool = True) -> pd.DataFrame:
    """Create synthetic OHLCV + optional Adj Close data for n rows."""
    dates = pd.date_range("2026-01-01", periods=n, freq="D")
    base = [100.0 + i for i in range(n)]
    df = pd.DataFrame({
        "Date": dates,
        "Open": base,
        "High": [v + 1.0 for v in base],
        "Low": [v - 1.0 for v in base],
        "Close": base,
        "Volume": [1_000_000] * n,
    })
    if with_adj:
        # Adj Close is slightly lower due to dividends
        df["Adj Close"] = [v - 0.5 for v in base]
    return df


def _make_feature_df(n: int = 10, with_adj: bool = True) -> pd.DataFrame:
    """Return a feature DataFrame ready for encode_dataframe."""
    raw = _make_raw_df(n=n, with_adj=with_adj)
    raw["Date"] = pd.to_datetime(raw["Date"])
    return build_features(raw)


# ---------------------------------------------------------------------------
# 1. data_fetcher preserves Adj Close
# ---------------------------------------------------------------------------

class TestDataFetcherKeepsAdjClose(unittest.TestCase):
    def test_clean_price_data_preserves_adj_close(self) -> None:
        raw = _make_raw_df(n=5, with_adj=True)
        # clean_price_data expects Date as index or column — pass as-is
        result = clean_price_data(raw)
        self.assertIn("Adj Close", result.columns)

    def test_clean_price_data_no_adj_close_still_works(self) -> None:
        raw = _make_raw_df(n=5, with_adj=False)
        result = clean_price_data(raw)
        # Should succeed and not have the column
        self.assertIn("Close", result.columns)
        self.assertNotIn("Adj Close", result.columns)


# ---------------------------------------------------------------------------
# 2. Adj Close != Close (separate columns, different values)
# ---------------------------------------------------------------------------

class TestAdjCloseDoesNotOverwriteClose(unittest.TestCase):
    def test_adj_close_and_close_are_different_columns(self) -> None:
        raw = _make_raw_df(n=5, with_adj=True)
        result = clean_price_data(raw)
        self.assertIn("Close", result.columns)
        self.assertIn("Adj Close", result.columns)
        # Values differ (adj < close in our synthetic data)
        self.assertFalse((result["Close"] == result["Adj Close"]).all())


# ---------------------------------------------------------------------------
# 3. H_up / L_down / C_move use raw intraday OHLC
# ---------------------------------------------------------------------------

class TestFeatureBuilderIntradayUsesRawOHLC(unittest.TestCase):
    def test_h_up_uses_raw_high_and_open(self) -> None:
        raw = _make_raw_df(n=5, with_adj=True)
        raw["Date"] = pd.to_datetime(raw["Date"])
        features = build_features(raw)
        # H_up = (High - Open) / Open; both raw
        # Row 0: High=101, Open=100 -> H_up = 0.01
        row0 = features.iloc[0]
        expected_h_up = (101.0 - 100.0) / 100.0
        self.assertAlmostEqual(row0["H_up"], expected_h_up, places=6)

    def test_l_down_uses_raw_open_and_low(self) -> None:
        raw = _make_raw_df(n=5, with_adj=True)
        raw["Date"] = pd.to_datetime(raw["Date"])
        features = build_features(raw)
        # L_down = (Open - Low) / Open; Row 0: Open=100, Low=99 -> 0.01
        row0 = features.iloc[0]
        expected_l_down = (100.0 - 99.0) / 100.0
        self.assertAlmostEqual(row0["L_down"], expected_l_down, places=6)

    def test_c_move_uses_raw_close_and_open(self) -> None:
        raw = _make_raw_df(n=5, with_adj=True)
        raw["Date"] = pd.to_datetime(raw["Date"])
        features = build_features(raw)
        # C_move = (Close - Open) / Open; Row 0: Close=100, Open=100 -> 0.0
        row0 = features.iloc[0]
        expected_c_move = (100.0 - 100.0) / 100.0
        self.assertAlmostEqual(row0["C_move"], expected_c_move, places=6)


# ---------------------------------------------------------------------------
# 4. O_gap uses PrevAdjClose
# ---------------------------------------------------------------------------

class TestFeatureBuilderOGapUsesRawPrevClose(unittest.TestCase):
    def test_o_gap_uses_raw_prev_close(self) -> None:
        raw = _make_raw_df(n=5, with_adj=True)
        raw["Date"] = pd.to_datetime(raw["Date"])
        features = build_features(raw)
        # Row 1: Open=101, raw Close[0]=100 -> O_gap = (101-100)/100 = 0.01
        row1 = features.iloc[1]
        expected_o_gap = (101.0 - 100.0) / 100.0
        self.assertAlmostEqual(row1["O_gap"], expected_o_gap, places=6)

    def test_o_gap_uses_raw_prev_close_without_adj(self) -> None:
        raw = _make_raw_df(n=5, with_adj=False)
        raw["Date"] = pd.to_datetime(raw["Date"])
        features = build_features(raw)
        # Same result whether or not Adj Close is present
        row1 = features.iloc[1]
        expected_o_gap = (101.0 - 100.0) / 100.0
        self.assertAlmostEqual(row1["O_gap"], expected_o_gap, places=6)

    def test_o_gap_not_affected_by_adj_close_divergence(self) -> None:
        # When Close and Adj Close differ significantly (e.g. post-dividend),
        # O_gap must still be Open / prev raw Close - 1, not Open / PrevAdjClose - 1.
        df = pd.DataFrame({
            "Date": pd.to_datetime(["2026-01-01", "2026-01-02"]),
            "Open":      [100.0, 105.0],
            "High":      [101.0, 106.0],
            "Low":       [ 99.0, 104.0],
            "Close":     [100.0, 104.0],
            # Adj Close is 5% lower due to a dividend on day 0
            "Adj Close": [ 95.0,  99.0],
            "Volume":    [1_000_000, 1_000_000],
        })
        features = build_features(df)
        row1 = features.iloc[1]
        # O_gap = (Open[1] - Close[0]) / Close[0] = (105 - 100) / 100 = 0.05
        self.assertAlmostEqual(row1["O_gap"], 0.05, places=6)
        # Confirm it is NOT (105 - 95) / 95 ≈ 0.1053
        self.assertNotAlmostEqual(row1["O_gap"], (105.0 - 95.0) / 95.0, places=4)


# ---------------------------------------------------------------------------
# 5. C_adj uses Adj Close
# ---------------------------------------------------------------------------

class TestFeatureBuilderCAdjUsesAdjClose(unittest.TestCase):
    def test_c_adj_is_computed_from_adj_close(self) -> None:
        raw = _make_raw_df(n=5, with_adj=True)
        raw["Date"] = pd.to_datetime(raw["Date"])
        features = build_features(raw)
        self.assertIn("C_adj", features.columns)
        # Row 1: AdjClose=100.5, PrevAdjClose=99.5
        row1 = features.iloc[1]
        expected_c_adj = (100.5 - 99.5) / 99.5
        self.assertAlmostEqual(row1["C_adj"], expected_c_adj, places=6)

    def test_c_adj_falls_back_to_close_when_no_adj(self) -> None:
        raw = _make_raw_df(n=5, with_adj=False)
        raw["Date"] = pd.to_datetime(raw["Date"])
        features = build_features(raw)
        self.assertIn("C_adj", features.columns)
        # Row 1: Close=101, PrevClose=100 -> C_adj = 0.01
        row1 = features.iloc[1]
        expected_c_adj = (101.0 - 100.0) / 100.0
        self.assertAlmostEqual(row1["C_adj"], expected_c_adj, places=6)


# ---------------------------------------------------------------------------
# 6. C_code is encoded from C_adj, not C_move
# ---------------------------------------------------------------------------

class TestEncoderCCodeUsesCAdj(unittest.TestCase):
    def _make_encode_ready(self, with_adj: bool = True) -> pd.DataFrame:
        return _make_feature_df(n=10, with_adj=with_adj)

    def test_c_code_present_when_c_adj_available(self) -> None:
        features = self._make_encode_ready(with_adj=True)
        encoded = encode_dataframe(features)
        self.assertIn("C_code", encoded.columns)

    def test_c_code_matches_encode_c_move_applied_to_c_adj(self) -> None:
        features = self._make_encode_ready(with_adj=True)
        encoded = encode_dataframe(features)
        # Manually verify C_code = encode_c_move(C_adj) for non-NaN rows
        for _, row in encoded.iterrows():
            if pd.isna(row["C_adj"]) or pd.isna(row["C_code"]):
                continue
            expected = encode_c_move(row["C_adj"])
            self.assertEqual(int(row["C_code"]), expected)

    def test_c_code_falls_back_to_c_move_when_no_adj(self) -> None:
        # When there is no Adj Close source data, build_features falls back to Close
        # for C_adj, so C_adj is still present but equals C_move in that case.
        features = self._make_encode_ready(with_adj=False)
        encoded = encode_dataframe(features)
        self.assertIn("C_code", encoded.columns)
        # C_adj should be present (falls back to Close-based calc)
        self.assertIn("C_adj", features.columns)
        # Verify C_code = encode_c_move(C_adj) for non-NaN rows
        for _, row in encoded.iterrows():
            if pd.isna(row["C_adj"]) or pd.isna(row["C_code"]):
                continue
            expected = encode_c_move(row["C_adj"])
            self.assertEqual(int(row["C_code"]), expected)


# ---------------------------------------------------------------------------
# 7. H_code / L_code use raw intraday H_up / L_down
# ---------------------------------------------------------------------------

class TestEncoderHLCodesUseRawIntraday(unittest.TestCase):
    def test_h_code_derived_from_h_up(self) -> None:
        from encoder import encode_h_up
        features = _make_feature_df(n=10, with_adj=True)
        encoded = encode_dataframe(features)
        for _, row in encoded.iterrows():
            if pd.isna(row["H_up"]) or pd.isna(row["H_code"]):
                continue
            expected = encode_h_up(row["H_up"])
            self.assertEqual(int(row["H_code"]), expected)

    def test_l_code_derived_from_l_down(self) -> None:
        from encoder import encode_l_down
        features = _make_feature_df(n=10, with_adj=True)
        encoded = encode_dataframe(features)
        for _, row in encoded.iterrows():
            if pd.isna(row["L_down"]) or pd.isna(row["L_code"]):
                continue
            expected = encode_l_down(row["L_down"])
            self.assertEqual(int(row["L_code"]), expected)


# ---------------------------------------------------------------------------
# 8. data_quality_check — flag semantics
#
# Flags:
#   clean                    — diff <= 0.5%, no corporate action
#   historical_adjustment_gap — diff > 0.5%, no corporate action on that date
#                               (cumulative back-adjustment; NOT a data error)
#   corporate_action_day     — Dividends != 0 or Stock Splits != 0 that day
#   no_adj_close             — Adj Close column absent
# ---------------------------------------------------------------------------

def _make_actions(dates: list[str], dividends: list[float], splits: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {"Dividends": dividends, "Stock Splits": splits},
        index=pd.Index(dates, name="Date"),
    )


class TestDataQualityCheckFlagSemantics(unittest.TestCase):
    def _price_df(self) -> pd.DataFrame:
        """Four rows with varying Close / Adj Close spreads."""
        return pd.DataFrame({
            "Date": ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"],
            # Row 0: no diff  (clean)
            # Row 1: 1% diff  (historical_adjustment_gap when no action)
            # Row 2: 50% diff (historical_adjustment_gap when no action)
            # Row 3: 0.1% diff (clean — below threshold)
            "Close":     [100.0, 100.0, 100.0, 100.0],
            "Adj Close": [100.0,  99.0,  50.0,  99.9],
        })

    # -- no actions provided (fallback to diff-only path) --------------------

    def test_clean_when_no_diff_no_actions(self) -> None:
        result = check_adjustment_days(self._price_df())
        self.assertEqual(result.iloc[0]["adjustment_flag"], "clean")

    def test_historical_gap_when_diff_and_no_actions(self) -> None:
        # 1% diff, no actions object → historical_adjustment_gap (not an error)
        result = check_adjustment_days(self._price_df())
        self.assertEqual(result.iloc[1]["adjustment_flag"], "historical_adjustment_gap")

    def test_large_historical_gap_is_not_error(self) -> None:
        # 50% diff (e.g. old pre-split price vs current adj price) → historical_adjustment_gap
        result = check_adjustment_days(self._price_df())
        self.assertEqual(result.iloc[2]["adjustment_flag"], "historical_adjustment_gap")

    def test_sub_threshold_is_clean(self) -> None:
        # 0.1% diff < 0.5% threshold → clean
        result = check_adjustment_days(self._price_df())
        self.assertEqual(result.iloc[3]["adjustment_flag"], "clean")

    # -- with actions provided -----------------------------------------------

    def test_corporate_action_day_when_dividend_nonzero(self) -> None:
        # Row 1 has a dividend → corporate_action_day regardless of diff size
        actions = _make_actions(["2026-01-02"], [0.53], [0.0])
        result = check_adjustment_days(self._price_df(), actions)
        self.assertEqual(result.iloc[1]["adjustment_flag"], "corporate_action_day")

    def test_corporate_action_day_when_split_nonzero(self) -> None:
        # Row 2 has a stock split → corporate_action_day
        actions = _make_actions(["2026-01-03"], [0.0], [2.0])
        result = check_adjustment_days(self._price_df(), actions)
        self.assertEqual(result.iloc[2]["adjustment_flag"], "corporate_action_day")

    def test_historical_gap_when_diff_but_action_on_different_date(self) -> None:
        # Action is on row 0; row 1 has diff but no action → historical_adjustment_gap
        actions = _make_actions(["2026-01-01"], [0.53], [0.0])
        result = check_adjustment_days(self._price_df(), actions)
        self.assertEqual(result.iloc[1]["adjustment_flag"], "historical_adjustment_gap")

    def test_clean_when_no_diff_even_with_actions_present(self) -> None:
        # Row 0 has 0% diff and its date has no action → clean
        actions = _make_actions(["2026-01-02"], [0.53], [0.0])
        result = check_adjustment_days(self._price_df(), actions)
        self.assertEqual(result.iloc[0]["adjustment_flag"], "clean")

    # -- edge cases ----------------------------------------------------------

    def test_missing_adj_close_column_returns_no_adj_close_flag(self) -> None:
        df = pd.DataFrame({"Date": ["2026-01-01"], "Close": [100.0]})
        result = check_adjustment_days(df)
        self.assertTrue((result["adjustment_flag"] == "no_adj_close").all())

    def test_adj_diff_pct_column_present(self) -> None:
        result = check_adjustment_days(self._price_df())
        self.assertIn("adj_diff_pct", result.columns)
        self.assertAlmostEqual(result.iloc[1]["adj_diff_pct"], 1.0, places=2)


if __name__ == "__main__":
    unittest.main()
