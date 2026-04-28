"""Task 100 — `build_primary_20day_analysis(target_date=...)` is date-aware.

Confirms the as-of date actually slices the analysis window. Three cases:

1. With a synthetic DataFrame and ``target_date`` set to a middle date,
   the analysis features reflect rows on/before that date — not the
   final row of the input.
2. Two different ``target_date`` values on the same DataFrame produce
   different ``latest_close`` values.
3. When ``target_date`` is ``None``, the live behaviour (latest N rows)
   is preserved.

No live data dependency; tests are pure-Python over an in-memory df.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.primary_20day_analysis import build_primary_20day_analysis


def _make_df(num_days: int = 60, *, start: str = "2024-01-02") -> pd.DataFrame:
    """Build a synthetic OHLCV df with monotonically increasing close."""
    dates = pd.bdate_range(start=start, periods=num_days)
    rows: list[dict[str, Any]] = []
    for i, d in enumerate(dates):
        close = 100.0 + i  # close climbs linearly: row N has close = 100 + N
        rows.append({
            "Date": d.strftime("%Y-%m-%d"),
            "Open": close - 0.5,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": 1_000_000 + i * 1_000,
            "Ret5": 0.0,
            "Pos30": 50.0,
            "PosLabel": "中位",
            "StageLabel": "整理",
        })
    return pd.DataFrame(rows)


class TestPrimary20DayAnalysisTargetDate(unittest.TestCase):
    def test_target_date_in_middle_uses_data_through_that_date(self) -> None:
        df = _make_df(num_days=60)
        # Row 30 has close = 100 + 30 = 130; date = 30th business day from start.
        middle_row = df.iloc[30]
        middle_date = str(middle_row["Date"])
        expected_close = float(middle_row["Close"])

        result = build_primary_20day_analysis(
            symbol="AVGO",
            lookback_days=20,
            target_date=middle_date,
            data=df,
        )

        self.assertTrue(result["ready"], msg=f"unexpected unready result: {result}")
        self.assertEqual(result["target_date"], middle_date)
        self.assertEqual(
            result["features"]["latest_close"],
            round(expected_close, 2),
            msg=(
                f"latest_close should reflect close on target_date {middle_date} "
                f"(expected {expected_close}), but got {result['features']['latest_close']}"
            ),
        )
        self.assertEqual(result["features"]["days_used"], 20)

    def test_two_different_target_dates_yield_different_features(self) -> None:
        df = _make_df(num_days=80)
        date_a = str(df.iloc[30]["Date"])
        date_b = str(df.iloc[60]["Date"])

        result_a = build_primary_20day_analysis(
            symbol="AVGO",
            lookback_days=20,
            target_date=date_a,
            data=df,
        )
        result_b = build_primary_20day_analysis(
            symbol="AVGO",
            lookback_days=20,
            target_date=date_b,
            data=df,
        )

        self.assertTrue(result_a["ready"])
        self.assertTrue(result_b["ready"])
        self.assertNotEqual(
            result_a["features"]["latest_close"],
            result_b["features"]["latest_close"],
            msg=(
                "Two different target_date values must yield different latest_close. "
                f"Got {result_a['features']['latest_close']} vs "
                f"{result_b['features']['latest_close']}."
            ),
        )
        self.assertNotEqual(result_a["target_date"], result_b["target_date"])

    def test_target_date_none_uses_latest_rows(self) -> None:
        """Without target_date, behaviour falls back to latest lookback_days rows."""
        df = _make_df(num_days=40)
        latest_close = float(df.iloc[-1]["Close"])

        result = build_primary_20day_analysis(
            symbol="AVGO",
            lookback_days=20,
            target_date=None,
            data=df,
        )

        self.assertTrue(result["ready"])
        self.assertEqual(
            result["features"]["latest_close"],
            round(latest_close, 2),
            msg="With target_date=None, latest_close must be the df's final row.",
        )

    def test_target_date_before_any_data_returns_unknown_result(self) -> None:
        df = _make_df(num_days=30, start="2024-06-01")
        result = build_primary_20day_analysis(
            symbol="AVGO",
            lookback_days=20,
            target_date="2020-01-01",
            data=df,
        )
        self.assertFalse(result["ready"])
        self.assertEqual(result["target_date"], "2020-01-01")
        self.assertIn("as-of 日期之前没有数据", result["summary"])
        self.assertTrue(
            any("没有可用数据" in w for w in result["warnings"]),
            msg=f"warnings did not surface the empty-as-of message: {result['warnings']}",
        )

    def test_target_date_filters_injected_dataframe(self) -> None:
        """When data=df is injected and target_date is set, df must be filtered too.

        This is the core regression: the replay harness injects (or relies on)
        a single df that may contain rows beyond target_date; without slicing,
        the analysis would peek at future rows.
        """
        df = _make_df(num_days=50)
        date_at_30 = str(df.iloc[30]["Date"])

        result_filtered = build_primary_20day_analysis(
            symbol="AVGO",
            lookback_days=20,
            target_date=date_at_30,
            data=df,  # full 50-row df with rows beyond target_date
        )
        # latest_close should be the close on day 30, not day 49.
        expected_at_30 = float(df.iloc[30]["Close"])
        last_in_df = float(df.iloc[-1]["Close"])
        self.assertEqual(result_filtered["features"]["latest_close"], round(expected_at_30, 2))
        self.assertNotEqual(result_filtered["features"]["latest_close"], round(last_in_df, 2))


if __name__ == "__main__":
    unittest.main()
