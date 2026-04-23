from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import services.prediction_store as ps
from services.outcome_capture import (
    _compute_direction_correct,
    capture_actual_outcome,
    capture_outcome,
    classify_actual_structure,
)

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


def _saved_prediction(
    prediction_for_date: str = "2026-04-11",
    bias: str = "bullish",
    scan_result: dict | None = None,
) -> str:
    """Helper: insert a bare-minimum prediction row and return its id."""
    pr = {
        "symbol": "AVGO",
        "final_bias": bias,
        "final_confidence": "medium",
        "prediction_summary": "test",
        "supporting_factors": [],
        "conflicting_factors": [],
    }
    return ps.save_prediction(
        symbol="AVGO",
        prediction_for_date=prediction_for_date,
        scan_result=scan_result,
        research_result=None,
        predict_result=pr,
    )


def _make_hist_df(target_date: str, prev_date: str) -> "pd.DataFrame":
    """
    Build a minimal two-row DataFrame mimicking yfinance history output,
    already with a plain-string Date column.
    """
    assert HAS_PANDAS
    return pd.DataFrame(
        [
            {
                "Date": prev_date,
                "Open": 170.0,
                "High": 172.0,
                "Low": 169.0,
                "Close": 171.0,
                "Volume": 1_000_000,
            },
            {
                "Date": target_date,
                "Open": 172.0,
                "High": 175.0,
                "Low": 171.5,
                "Close": 174.0,
                "Volume": 1_200_000,
            },
        ]
    )


class DirectionLogicTests(unittest.TestCase):
    """Unit tests for _compute_direction_correct — no I/O, no DB."""

    def test_bullish_correct_on_positive_move(self) -> None:
        self.assertEqual(_compute_direction_correct("bullish", 0.02), 1)

    def test_bullish_wrong_on_negative_move(self) -> None:
        self.assertEqual(_compute_direction_correct("bullish", -0.02), 0)

    def test_bearish_correct_on_negative_move(self) -> None:
        self.assertEqual(_compute_direction_correct("bearish", -0.02), 1)

    def test_bearish_wrong_on_positive_move(self) -> None:
        self.assertEqual(_compute_direction_correct("bearish", 0.02), 0)

    def test_neutral_bias_returns_none(self) -> None:
        self.assertIsNone(_compute_direction_correct("neutral", 0.05))

    def test_unknown_bias_returns_none(self) -> None:
        self.assertIsNone(_compute_direction_correct("unknown", 0.05))

    def test_flat_move_below_threshold_returns_none(self) -> None:
        # 0.05% move — below the 0.1% flat threshold
        self.assertIsNone(_compute_direction_correct("bullish", 0.0005))

    def test_move_exactly_at_threshold_boundary(self) -> None:
        # 0.1% is the threshold; values >= 0.001 are not flat
        self.assertEqual(_compute_direction_correct("bullish", 0.001), 1)

    def test_zero_move_returns_none(self) -> None:
        self.assertIsNone(_compute_direction_correct("bullish", 0.0))

    def test_empty_bias_returns_none(self) -> None:
        self.assertIsNone(_compute_direction_correct("", 0.05))


class CaptureOutcomeIntegrationTests(unittest.TestCase):
    """
    Integration tests for capture_outcome.
    yfinance is mocked so no network calls are made.
    """

    def setUp(self) -> None:
        if not HAS_PANDAS:
            self.skipTest("pandas not installed")
        self._tmpdir = tempfile.TemporaryDirectory()
        ps.DB_PATH = Path(self._tmpdir.name) / "test.db"
        ps.init_db()

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _mock_ticker(self, target_date: str, prev_date: str) -> MagicMock:
        hist_df = _make_hist_df(target_date, prev_date)
        # yfinance returns a DatetimeIndex; outcome_capture resets + normalises it
        hist_df["Date"] = pd.to_datetime(hist_df["Date"])
        hist_df = hist_df.set_index("Date")
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = hist_df
        return mock_ticker

    def test_raises_if_prediction_not_found(self) -> None:
        with self.assertRaises(ValueError, msg="Prediction not found"):
            capture_outcome("nonexistent-id")

    def test_capture_outcome_success_bullish_correct(self) -> None:
        pid = _saved_prediction(prediction_for_date="2026-04-11", bias="bullish")
        mock_ticker = self._mock_ticker("2026-04-11", "2026-04-10")

        with patch("services.outcome_capture.yf.Ticker", return_value=mock_ticker):
            result = capture_outcome(pid)

        self.assertIsNotNone(result)
        self.assertAlmostEqual(result["actual_close"], 174.0)
        self.assertAlmostEqual(result["actual_prev_close"], 171.0)
        # close went up → bullish → direction_correct = 1
        self.assertEqual(result["direction_correct"], 1)
        self.assertIn("actual_close_change", result)
        self.assertAlmostEqual(result["actual_close_change"],
                               (174.0 - 171.0) / 171.0, places=6)

    def test_capture_outcome_success_bearish_correct(self) -> None:
        pid = _saved_prediction(prediction_for_date="2026-04-11", bias="bearish")

        # Make close go DOWN
        hist_df = pd.DataFrame(
            [
                {"Date": "2026-04-10", "Open": 175.0, "High": 176.0,
                 "Low": 174.0, "Close": 175.0, "Volume": 1_000_000},
                {"Date": "2026-04-11", "Open": 173.0, "High": 174.0,
                 "Low": 170.0, "Close": 171.0, "Volume": 1_200_000},
            ]
        )
        hist_df["Date"] = pd.to_datetime(hist_df["Date"])
        hist_df = hist_df.set_index("Date")
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = hist_df

        with patch("services.outcome_capture.yf.Ticker", return_value=mock_ticker):
            result = capture_outcome(pid)

        self.assertEqual(result["direction_correct"], 1)

    def test_capture_outcome_raises_on_non_trading_day(self) -> None:
        pid = _saved_prediction(prediction_for_date="2026-04-12")  # Sunday

        # Return a hist that does not contain 2026-04-12
        hist_df = _make_hist_df("2026-04-11", "2026-04-10")
        hist_df["Date"] = pd.to_datetime(hist_df["Date"])
        hist_df = hist_df.set_index("Date")
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = hist_df

        with patch("services.outcome_capture.yf.Ticker", return_value=mock_ticker):
            with self.assertRaises(ValueError, msg="not a trading day"):
                capture_outcome(pid)

    def test_capture_outcome_raises_on_empty_yfinance(self) -> None:
        pid = _saved_prediction(prediction_for_date="2026-04-11")
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()  # empty

        with patch("services.outcome_capture.yf.Ticker", return_value=mock_ticker):
            with self.assertRaises(ValueError, msg="no data"):
                capture_outcome(pid)

    def test_capture_outcome_is_idempotent(self) -> None:
        pid = _saved_prediction(prediction_for_date="2026-04-11", bias="bullish")
        mock_ticker = self._mock_ticker("2026-04-11", "2026-04-10")

        with patch("services.outcome_capture.yf.Ticker", return_value=mock_ticker):
            result1 = capture_outcome(pid)
            result2 = capture_outcome(pid)  # second call — yfinance should NOT be called again

        # Ticker.history should only have been called once
        mock_ticker.history.assert_called_once()
        self.assertEqual(result1["id"], result2["id"])

    def test_capture_outcome_advances_status(self) -> None:
        pid = _saved_prediction(prediction_for_date="2026-04-11", bias="bullish")
        mock_ticker = self._mock_ticker("2026-04-11", "2026-04-10")

        with patch("services.outcome_capture.yf.Ticker", return_value=mock_ticker):
            capture_outcome(pid)

        row = ps.get_prediction(pid)
        assert row is not None
        self.assertEqual(row["status"], "outcome_captured")

    def test_scenario_match_is_null_by_default(self) -> None:
        pid = _saved_prediction(prediction_for_date="2026-04-11", bias="bullish")
        mock_ticker = self._mock_ticker("2026-04-11", "2026-04-10")

        with patch("services.outcome_capture.yf.Ticker", return_value=mock_ticker):
            result = capture_outcome(pid)

        self.assertIsNone(result["scenario_match"])

    def test_capture_outcome_persists_scenario_match_from_scan_summary(self) -> None:
        scan_result = {
            "scan_bias": "bullish",
            "scan_confidence": "high",
            "historical_match_summary": {
                "exact_match_count": 3,
                "near_match_count": 2,
                "top_context_score": 87.5,
                "dominant_historical_outcome": "bullish",
            },
        }
        pid = _saved_prediction(
            prediction_for_date="2026-04-11",
            bias="bullish",
            scan_result=scan_result,
        )
        mock_ticker = self._mock_ticker("2026-04-11", "2026-04-10")

        with patch("services.outcome_capture.yf.Ticker", return_value=mock_ticker):
            result = capture_outcome(pid)

        import json
        scenario = json.loads(result["scenario_match"])
        self.assertEqual(scenario["source"], "scan_result.historical_match_summary")
        self.assertEqual(scenario["exact_match_count"], 3)
        self.assertEqual(scenario["near_match_count"], 2)
        self.assertEqual(scenario["match_sample_size"], 5)
        self.assertEqual(scenario["top_context_score"], 87.5)
        self.assertEqual(scenario["dominant_historical_outcome"], "bullish")
        self.assertEqual(scenario["scan_bias"], "bullish")
        self.assertEqual(scenario["scan_confidence"], "high")


class ClassifyActualStructureTests(unittest.TestCase):
    """Unit tests for classify_actual_structure — pure function, no I/O."""

    def _classify(self, open_price: float, close_price: float, prev_close: float) -> dict:
        return classify_actual_structure(
            {"Open": open_price, "Close": close_price}, prev_close
        )

    # ── open label ──────────────────────────────────────────────────────────

    def test_high_open(self) -> None:
        r = self._classify(102.0, 101.0, 100.0)  # open +2% > threshold
        self.assertEqual(r["open_label"], "高开")

    def test_low_open(self) -> None:
        r = self._classify(98.0, 99.0, 100.0)  # open -2%
        self.assertEqual(r["open_label"], "低开")

    def test_flat_open_above_threshold_boundary(self) -> None:
        # open at exactly +0.1% hits the threshold but is NOT strictly greater → 平开
        r = self._classify(100.1, 100.0, 100.0)
        self.assertEqual(r["open_label"], "平开")

    def test_open_just_above_threshold(self) -> None:
        # +0.11% > 0.1% threshold → 高开
        r = self._classify(100.11, 100.0, 100.0)
        self.assertEqual(r["open_label"], "高开")

    def test_flat_open_below_threshold(self) -> None:
        r = self._classify(100.05, 100.0, 100.0)  # +0.05% < 0.1%
        self.assertEqual(r["open_label"], "平开")

    def test_flat_open_zero_move(self) -> None:
        r = self._classify(100.0, 100.0, 100.0)
        self.assertEqual(r["open_label"], "平开")

    # ── close label ─────────────────────────────────────────────────────────

    def test_close_up(self) -> None:
        r = self._classify(100.0, 102.0, 100.0)
        self.assertEqual(r["close_label"], "收涨")

    def test_close_down(self) -> None:
        r = self._classify(100.0, 98.0, 100.0)
        self.assertEqual(r["close_label"], "收跌")

    def test_close_flat(self) -> None:
        r = self._classify(100.0, 100.05, 100.0)  # +0.05% < threshold
        self.assertEqual(r["close_label"], "平收")

    # ── path label — all 9 combinations ─────────────────────────────────────

    def test_path_高开高走(self) -> None:
        r = self._classify(102.0, 103.0, 100.0)
        self.assertEqual(r["path_label"], "高开高走")

    def test_path_高开低走(self) -> None:
        r = self._classify(102.0, 98.0, 100.0)
        self.assertEqual(r["path_label"], "高开低走")

    def test_path_高开震荡(self) -> None:
        r = self._classify(102.0, 100.05, 100.0)  # high open, flat close
        self.assertEqual(r["path_label"], "高开震荡")

    def test_path_低开高走(self) -> None:
        r = self._classify(98.0, 102.0, 100.0)
        self.assertEqual(r["path_label"], "低开高走")

    def test_path_低开低走(self) -> None:
        r = self._classify(98.0, 97.0, 100.0)
        self.assertEqual(r["path_label"], "低开低走")

    def test_path_低开震荡(self) -> None:
        r = self._classify(98.0, 100.05, 100.0)  # low open, flat close
        self.assertEqual(r["path_label"], "低开震荡")

    def test_path_平开走高(self) -> None:
        r = self._classify(100.05, 102.0, 100.0)
        self.assertEqual(r["path_label"], "平开走高")

    def test_path_平开走低(self) -> None:
        r = self._classify(100.05, 98.0, 100.0)
        self.assertEqual(r["path_label"], "平开走低")

    def test_path_平开震荡(self) -> None:
        r = self._classify(100.05, 100.05, 100.0)
        self.assertEqual(r["path_label"], "平开震荡")

    # ── return shape ────────────────────────────────────────────────────────

    def test_returns_all_three_keys(self) -> None:
        r = self._classify(102.0, 103.0, 100.0)
        self.assertIn("open_label", r)
        self.assertIn("close_label", r)
        self.assertIn("path_label", r)
        self.assertEqual(len(r), 3)


class CaptureActualOutcomeTests(unittest.TestCase):
    """Integration tests for capture_actual_outcome — yfinance mocked."""

    def setUp(self) -> None:
        if not HAS_PANDAS:
            self.skipTest("pandas not installed")

    def _mock_ticker(self, rows: list[dict]) -> MagicMock:
        df = pd.DataFrame(rows)
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date")
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = df
        return mock_ticker

    def _standard_rows(self, target_date: str = "2026-04-11",
                       prev_date: str = "2026-04-10") -> list[dict]:
        return [
            {"Date": prev_date, "Open": 170.0, "High": 172.0, "Low": 169.0,
             "Close": 171.0, "Volume": 1_000_000},
            {"Date": target_date, "Open": 172.0, "High": 175.0, "Low": 171.5,
             "Close": 174.0, "Volume": 1_200_000},
        ]

    def test_returns_expected_fields(self) -> None:
        mock_ticker = self._mock_ticker(self._standard_rows())
        with patch("services.outcome_capture.yf.Ticker", return_value=mock_ticker):
            result = capture_actual_outcome("AVGO", "2026-04-11")

        expected_keys = {
            "symbol", "target_date",
            "actual_open", "actual_high", "actual_low", "actual_close",
            "actual_prev_close", "actual_open_change", "actual_close_change",
            "open_label", "close_label", "path_label",
        }
        self.assertEqual(set(result.keys()), expected_keys)

    def test_ohlcv_values_correct(self) -> None:
        mock_ticker = self._mock_ticker(self._standard_rows())
        with patch("services.outcome_capture.yf.Ticker", return_value=mock_ticker):
            result = capture_actual_outcome("AVGO", "2026-04-11")

        self.assertAlmostEqual(result["actual_open"], 172.0)
        self.assertAlmostEqual(result["actual_high"], 175.0)
        self.assertAlmostEqual(result["actual_low"], 171.5)
        self.assertAlmostEqual(result["actual_close"], 174.0)
        self.assertAlmostEqual(result["actual_prev_close"], 171.0)

    def test_change_calculations(self) -> None:
        mock_ticker = self._mock_ticker(self._standard_rows())
        with patch("services.outcome_capture.yf.Ticker", return_value=mock_ticker):
            result = capture_actual_outcome("AVGO", "2026-04-11")

        self.assertAlmostEqual(result["actual_open_change"], (172.0 - 171.0) / 171.0, places=6)
        self.assertAlmostEqual(result["actual_close_change"], (174.0 - 171.0) / 171.0, places=6)

    def test_classification_high_open_high_close(self) -> None:
        # open 172 vs prev 171 → +0.58% → 高开; close 174 vs prev 171 → +1.75% → 收涨
        mock_ticker = self._mock_ticker(self._standard_rows())
        with patch("services.outcome_capture.yf.Ticker", return_value=mock_ticker):
            result = capture_actual_outcome("AVGO", "2026-04-11")

        self.assertEqual(result["open_label"], "高开")
        self.assertEqual(result["close_label"], "收涨")
        self.assertEqual(result["path_label"], "高开高走")

    def test_classification_low_open_low_close(self) -> None:
        rows = [
            {"Date": "2026-04-10", "Open": 170.0, "High": 172.0, "Low": 169.0,
             "Close": 170.0, "Volume": 1_000_000},
            {"Date": "2026-04-11", "Open": 168.0, "High": 169.0, "Low": 166.0,
             "Close": 167.0, "Volume": 1_200_000},
        ]
        mock_ticker = self._mock_ticker(rows)
        with patch("services.outcome_capture.yf.Ticker", return_value=mock_ticker):
            result = capture_actual_outcome("AVGO", "2026-04-11")

        self.assertEqual(result["open_label"], "低开")
        self.assertEqual(result["close_label"], "收跌")
        self.assertEqual(result["path_label"], "低开低走")

    def test_classification_flat_open_flat_close(self) -> None:
        rows = [
            {"Date": "2026-04-10", "Open": 170.0, "High": 170.5, "Low": 169.5,
             "Close": 170.0, "Volume": 1_000_000},
            {"Date": "2026-04-11", "Open": 170.05, "High": 170.2, "Low": 169.9,
             "Close": 170.05, "Volume": 900_000},
        ]
        mock_ticker = self._mock_ticker(rows)
        with patch("services.outcome_capture.yf.Ticker", return_value=mock_ticker):
            result = capture_actual_outcome("AVGO", "2026-04-11")

        self.assertEqual(result["open_label"], "平开")
        self.assertEqual(result["close_label"], "平收")
        self.assertEqual(result["path_label"], "平开震荡")

    def test_raises_on_non_trading_day(self) -> None:
        rows = [
            {"Date": "2026-04-10", "Open": 170.0, "High": 171.0,
             "Low": 169.0, "Close": 170.5, "Volume": 1_000_000},
        ]
        mock_ticker = self._mock_ticker(rows)
        with patch("services.outcome_capture.yf.Ticker", return_value=mock_ticker):
            with self.assertRaises(ValueError, msg="not a trading day"):
                capture_actual_outcome("AVGO", "2026-04-12")  # not in data

    def test_raises_on_empty_yfinance(self) -> None:
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()
        with patch("services.outcome_capture.yf.Ticker", return_value=mock_ticker):
            with self.assertRaises(ValueError, msg="no data"):
                capture_actual_outcome("AVGO", "2026-04-11")

    def test_symbol_passed_to_ticker(self) -> None:
        mock_ticker = self._mock_ticker(self._standard_rows())
        with patch("services.outcome_capture.yf.Ticker", return_value=mock_ticker) as mock_yf:
            capture_actual_outcome("NVDA", "2026-04-11")
        mock_yf.assert_called_once_with("NVDA")

    def test_does_not_write_to_db(self) -> None:
        mock_ticker = self._mock_ticker(self._standard_rows())
        with patch("services.outcome_capture.yf.Ticker", return_value=mock_ticker):
            with patch("services.outcome_capture.save_outcome") as mock_save:
                capture_actual_outcome("AVGO", "2026-04-11")
        mock_save.assert_not_called()


if __name__ == "__main__":
    unittest.main()
