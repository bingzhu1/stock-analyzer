# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scanner import build_recent_avgo_window


class RecentAvgoWindowTests(unittest.TestCase):
    def test_returns_latest_twenty_rows_through_target_date(self) -> None:
        df = pd.DataFrame(
            {
                "Date": pd.date_range("2026-03-01", periods=25, freq="D"),
                "Open": range(25),
                "High": range(1, 26),
                "Low": range(25),
                "Close": range(10, 35),
                "Volume": range(100, 125),
                "O_gap": [0.001] * 25,
                "C_move": [0.002] * 25,
                "V_ratio": [1.0] * 25,
                "Code": ["12345"] * 25,
            }
        )

        rows = build_recent_avgo_window(df, "2026-03-25", window=20)

        self.assertEqual(len(rows), 20)
        self.assertEqual(rows[0]["Date"], "2026-03-06")
        self.assertEqual(rows[-1]["Date"], "2026-03-25")
        self.assertEqual(rows[-1]["Close"], 34)

    def test_excludes_rows_after_target_date(self) -> None:
        df = pd.DataFrame(
            {
                "Date": pd.date_range("2026-03-01", periods=5, freq="D"),
                "Close": range(5),
            }
        )

        rows = build_recent_avgo_window(df, "2026-03-03", window=20)

        self.assertEqual([row["Date"] for row in rows], ["2026-03-01", "2026-03-02", "2026-03-03"])


if __name__ == "__main__":
    unittest.main()
