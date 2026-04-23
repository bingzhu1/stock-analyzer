"""Tests for services/features_20d.py — unified 20-day feature module."""

import math
import unittest

import pandas as pd

from services.features_20d import compute_20d_features, WINDOW


# ── fixtures ──────────────────────────────────────────────────────────────────

def _make_df(
    n: int = 20,
    base_close: float = 100.0,
    close_delta: float = 0.5,   # daily close increment
    volume: float = 1_000_000.0,
) -> pd.DataFrame:
    """
    Build a minimal synthetic OHLCV DataFrame with n rows.
    Close increases by close_delta each row (starting at base_close).
    High = Close + 2, Low = Close - 2, Open = prev Close.
    """
    closes = [base_close + i * close_delta for i in range(n)]
    rows = []
    for i, c in enumerate(closes):
        rows.append({
            "Date":   f"2024-01-{i + 1:02d}",
            "Open":   closes[i - 1] if i > 0 else c - close_delta,
            "High":   c + 2.0,
            "Low":    c - 2.0,
            "Close":  c,
            "Volume": volume,
        })
    return pd.DataFrame(rows)


def _make_flat_df(n: int = 20, price: float = 100.0) -> pd.DataFrame:
    """All OHLCV rows identical — edge-case for shadow ratios and pos20."""
    rows = [{"Date": f"2024-01-{i+1:02d}", "Open": price, "High": price,
              "Low": price, "Close": price, "Volume": 1_000.0} for i in range(n)]
    return pd.DataFrame(rows)


# ── shape & keys ──────────────────────────────────────────────────────────────

class OutputShapeTests(unittest.TestCase):
    def setUp(self):
        self.result = compute_20d_features(_make_df())

    def test_all_required_keys_present(self):
        required = {
            "pos20", "ret1", "ret3", "ret5", "ret10", "ret20",
            "vol_ratio20", "near_high20", "near_low20",
            "upper_shadow_ratio", "lower_shadow_ratio",
            "days_used", "target_date", "high_20d", "low_20d",
            "latest_close", "warnings", "ready",
        }
        self.assertTrue(required.issubset(self.result.keys()))

    def test_ready_true_for_full_window(self):
        self.assertTrue(self.result["ready"])

    def test_days_used_20(self):
        self.assertEqual(self.result["days_used"], WINDOW)

    def test_no_warnings_for_clean_data(self):
        self.assertEqual(self.result["warnings"], [])


# ── pos20 ─────────────────────────────────────────────────────────────────────

class Pos20Tests(unittest.TestCase):
    def test_pos20_is_between_0_and_100(self):
        r = compute_20d_features(_make_df())
        self.assertIsNotNone(r["pos20"])
        self.assertGreaterEqual(r["pos20"], 0.0)
        self.assertLessEqual(r["pos20"], 100.0)

    def test_pos20_is_100_when_close_equals_high(self):
        df = _make_df()
        # force last close to equal 20d high
        df.at[19, "Close"] = df["High"].max()
        r = compute_20d_features(df)
        self.assertAlmostEqual(r["pos20"], 100.0, places=1)

    def test_pos20_is_0_when_close_equals_low(self):
        df = _make_df()
        df.at[19, "Close"] = df["Low"].min()
        r = compute_20d_features(df)
        self.assertAlmostEqual(r["pos20"], 0.0, places=1)

    def test_pos20_none_when_flat_range(self):
        r = compute_20d_features(_make_flat_df())
        # high == low → range == 0 → pos20 is None
        self.assertIsNone(r["pos20"])


# ── returns ───────────────────────────────────────────────────────────────────

class ReturnTests(unittest.TestCase):
    def setUp(self):
        # Build 20-row df where closes are [100, 101, 102, ..., 119]
        self.df = _make_df(n=20, base_close=100.0, close_delta=1.0)
        self.r = compute_20d_features(self.df)

    def test_ret1_correct(self):
        # latest=119, prev=118 → (119/118 - 1)*100
        expected = (119 / 118 - 1) * 100
        self.assertAlmostEqual(self.r["ret1"], expected, places=3)

    def test_ret3_correct(self):
        # latest=119, 3 days ago=116
        expected = (119 / 116 - 1) * 100
        self.assertAlmostEqual(self.r["ret3"], expected, places=3)

    def test_ret5_correct(self):
        expected = (119 / 114 - 1) * 100
        self.assertAlmostEqual(self.r["ret5"], expected, places=3)

    def test_ret10_correct(self):
        expected = (119 / 109 - 1) * 100
        self.assertAlmostEqual(self.r["ret10"], expected, places=3)

    def test_ret20_correct(self):
        # first row close=100, last=119
        expected = (119 / 100 - 1) * 100
        self.assertAlmostEqual(self.r["ret20"], expected, places=3)

    def test_ret1_none_when_only_1_row(self):
        r = compute_20d_features(_make_df(n=1))
        self.assertIsNone(r["ret1"])

    def test_ret10_none_when_only_9_rows(self):
        r = compute_20d_features(_make_df(n=9))
        self.assertIsNone(r["ret10"])


# ── vol_ratio20 ───────────────────────────────────────────────────────────────

class VolRatio20Tests(unittest.TestCase):
    def test_vol_ratio20_is_1_when_uniform_volume(self):
        # All volumes equal → ratio = 1.0
        r = compute_20d_features(_make_df(volume=500_000.0))
        self.assertAlmostEqual(r["vol_ratio20"], 1.0, places=4)

    def test_vol_ratio20_above_1_when_latest_volume_spikes(self):
        df = _make_df(volume=1_000_000.0)
        df.at[19, "Volume"] = 3_000_000.0   # today is 3× average
        r = compute_20d_features(df)
        self.assertGreater(r["vol_ratio20"], 2.5)

    def test_vol_ratio20_below_1_when_volume_shrinks(self):
        df = _make_df(volume=1_000_000.0)
        df.at[19, "Volume"] = 100_000.0     # today is 0.1× average
        r = compute_20d_features(df)
        self.assertLess(r["vol_ratio20"], 0.2)

    def test_vol_ratio20_none_when_only_1_row(self):
        r = compute_20d_features(_make_df(n=1))
        self.assertIsNone(r["vol_ratio20"])


# ── near_high20 / near_low20 ─────────────────────────────────────────────────

class NearExtremeTests(unittest.TestCase):
    def test_near_high20_true_when_at_20d_high(self):
        df = _make_df()
        df.at[19, "Close"] = df["High"].max()   # close = 20d high
        r = compute_20d_features(df)
        self.assertTrue(r["near_high20"])

    def test_near_high20_false_when_far_below(self):
        df = _make_df()
        df.at[19, "Close"] = df["Low"].min()    # close = 20d low
        r = compute_20d_features(df)
        self.assertFalse(r["near_high20"])

    def test_near_low20_true_when_at_20d_low(self):
        df = _make_df()
        df.at[19, "Close"] = df["Low"].min()
        r = compute_20d_features(df)
        self.assertTrue(r["near_low20"])

    def test_near_low20_false_when_far_above(self):
        df = _make_df()
        df.at[19, "Close"] = df["High"].max()
        r = compute_20d_features(df)
        self.assertFalse(r["near_low20"])


# ── shadow ratios ─────────────────────────────────────────────────────────────

class ShadowRatioTests(unittest.TestCase):
    def test_doji_has_no_body_so_full_shadow(self):
        # Open == Close → body = 0, entire range is shadow
        row = {"Date": "2024-01-01", "Open": 100.0, "High": 105.0,
               "Low": 95.0, "Close": 100.0, "Volume": 1e6}
        df = pd.DataFrame([row] * 20)
        r = compute_20d_features(df)
        # upper = (105 - 100) / 10 = 0.5
        self.assertAlmostEqual(r["upper_shadow_ratio"], 0.5, places=4)
        # lower = (100 - 95) / 10 = 0.5
        self.assertAlmostEqual(r["lower_shadow_ratio"], 0.5, places=4)

    def test_bullish_marubozu_has_no_shadows(self):
        # Open == Low, Close == High → no wicks
        row = {"Date": "2024-01-01", "Open": 95.0, "High": 105.0,
               "Low": 95.0, "Close": 105.0, "Volume": 1e6}
        df = pd.DataFrame([row] * 20)
        r = compute_20d_features(df)
        self.assertAlmostEqual(r["upper_shadow_ratio"], 0.0, places=4)
        self.assertAlmostEqual(r["lower_shadow_ratio"], 0.0, places=4)

    def test_upper_shadow_only(self):
        # Open == Close == Low → upper wick only
        row = {"Date": "2024-01-01", "Open": 95.0, "High": 105.0,
               "Low": 95.0, "Close": 95.0, "Volume": 1e6}
        df = pd.DataFrame([row] * 20)
        r = compute_20d_features(df)
        self.assertAlmostEqual(r["upper_shadow_ratio"], 1.0, places=4)
        self.assertAlmostEqual(r["lower_shadow_ratio"], 0.0, places=4)

    def test_flat_candle_returns_none(self):
        r = compute_20d_features(_make_flat_df())
        self.assertIsNone(r["upper_shadow_ratio"])
        self.assertIsNone(r["lower_shadow_ratio"])

    def test_shadow_ratios_sum_le_1(self):
        r = compute_20d_features(_make_df())
        u = r["upper_shadow_ratio"]
        l = r["lower_shadow_ratio"]
        if u is not None and l is not None:
            self.assertLessEqual(u + l, 1.0 + 1e-9)


# ── degraded / edge cases ─────────────────────────────────────────────────────

class DegradedInputTests(unittest.TestCase):
    def test_none_input_returns_ready_false(self):
        r = compute_20d_features(None)  # type: ignore[arg-type]
        self.assertFalse(r["ready"])
        self.assertFalse(r["warnings"] == [])

    def test_empty_df_returns_ready_false(self):
        r = compute_20d_features(pd.DataFrame())
        self.assertFalse(r["ready"])

    def test_missing_required_column_returns_ready_false(self):
        df = _make_df().drop(columns=["Volume"])
        r = compute_20d_features(df)
        self.assertFalse(r["ready"])
        self.assertTrue(any("Volume" in w for w in r["warnings"]))

    def test_fewer_than_20_rows_has_warning(self):
        r = compute_20d_features(_make_df(n=10))
        self.assertEqual(r["days_used"], 10)
        self.assertTrue(any("不足" in w for w in r["warnings"]))

    def test_more_than_20_rows_clips_to_20(self):
        r = compute_20d_features(_make_df(n=40))
        self.assertEqual(r["days_used"], WINDOW)

    def test_nan_close_degrades_gracefully(self):
        df = _make_df()
        df["Close"] = float("nan")
        r = compute_20d_features(df)
        # Should not raise; pos20 / rets will be None
        self.assertIsNone(r["pos20"])
        self.assertIsNone(r["ret1"])


# ── window-clip sanity ────────────────────────────────────────────────────────

class WindowClipTests(unittest.TestCase):
    def test_result_uses_last_20_rows_not_first(self):
        # 40 rows: first 20 close=10, last 20 close=200
        df1 = _make_df(n=20, base_close=10.0, close_delta=0.0)
        df2 = _make_df(n=20, base_close=200.0, close_delta=0.0)
        df = pd.concat([df1, df2], ignore_index=True)
        r = compute_20d_features(df)
        self.assertAlmostEqual(r["latest_close"], 200.0, places=2)
        self.assertAlmostEqual(r["high_20d"], 202.0, places=2)   # last 20 rows: High = Close+2 = 202


if __name__ == "__main__":
    unittest.main()
