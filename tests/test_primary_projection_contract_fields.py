"""Step 2B-2: build_primary_projection self-publishes contract 02 fields.

The contract-validity end-to-end test lives in
``tests/test_run_predict_contract_alignment.py``. This file pins the field
shape on the primary_projection dict itself, so subsequent steps that
move logic into the builder cannot quietly drop them.

Logic (final_bias / final_confidence / score) is NOT changed by Step 2B-2;
this file only checks the additive fields.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from predict import build_primary_projection, run_predict
from services.projection_output_contract import (
    _CLOSE,
    _CONFIDENCE_LEVEL,
    _DIRECTION,
    _FIVE_STATE,
    _OPEN,
    _PATH,
)


_CONTRACT_02_FIELDS: tuple[str, ...] = (
    "primary_direction",
    "open_projection",
    "intraday_path_projection",
    "close_projection",
    "five_state_projection",
    "historical_sample_count",
    "key_evidence",
    "primary_confidence_raw",
)


def _bullish_scan() -> dict:
    rows = [
        {
            "Date": f"2026-04-{day:02d}",
            "Open": 100.0 + (day - 1) - 0.25,
            "Close": 100.0 + (day - 1),
            "Volume": 1_000_000 + day * 10_000,
            "O_gap": 0.006,
            "C_move": 0.01,
            "V_ratio": 1.2,
        }
        for day in range(1, 21)
    ]
    return {
        "symbol": "AVGO",
        "scan_timestamp": "2026-04-20T00:00:00",
        "scan_bias": "bullish",
        "scan_confidence": "medium",
        "avgo_gap_state": "gap_up",
        "avgo_intraday_state": "high_go",
        "avgo_volume_state": "expanding",
        "avgo_price_state": "bullish",
        "avgo_recent_20": rows,
        "relative_strength_summary": {
            "vs_nvda": "stronger",
            "vs_soxx": "stronger",
            "vs_qqq": "neutral",
        },
        "relative_strength_same_day_summary": {
            "vs_nvda": "stronger",
            "vs_soxx": "neutral",
            "vs_qqq": "stronger",
        },
    }


def _bearish_scan() -> dict:
    base = _bullish_scan()
    base["scan_bias"] = "bearish"
    base["avgo_gap_state"] = "gap_down"
    base["avgo_intraday_state"] = "low_go"
    base["avgo_volume_state"] = "shrinking"
    base["avgo_price_state"] = "bearish"
    base["avgo_recent_20"] = [
        {**row, "Open": row["Open"] + 0.5, "Close": 120.0 - i,
         "O_gap": -0.006, "C_move": -0.01, "V_ratio": 0.8}
        for i, row in enumerate(base["avgo_recent_20"])
    ]
    return base


class PrimaryProjectionContract02ShapeTests(unittest.TestCase):
    """Field presence + types on the computed branch."""

    def setUp(self) -> None:
        self.primary = build_primary_projection(_bullish_scan())

    def test_all_eight_contract_02_fields_present(self) -> None:
        for field in _CONTRACT_02_FIELDS:
            self.assertIn(field, self.primary, f"missing field: {field}")

    def test_primary_direction_is_in_contract_enum(self) -> None:
        self.assertIn(self.primary["primary_direction"], _DIRECTION)

    def test_open_projection_is_in_contract_enum(self) -> None:
        self.assertIn(self.primary["open_projection"], _OPEN)

    def test_intraday_path_projection_is_in_contract_enum(self) -> None:
        self.assertIn(self.primary["intraday_path_projection"], _PATH)

    def test_close_projection_is_in_contract_enum(self) -> None:
        self.assertIn(self.primary["close_projection"], _CLOSE)

    def test_five_state_projection_is_in_contract_enum(self) -> None:
        self.assertIn(self.primary["five_state_projection"], _FIVE_STATE)

    def test_primary_confidence_raw_is_in_contract_enum(self) -> None:
        self.assertIn(self.primary["primary_confidence_raw"], _CONFIDENCE_LEVEL)

    def test_historical_sample_count_is_int(self) -> None:
        self.assertIsInstance(self.primary["historical_sample_count"], int)
        self.assertGreaterEqual(self.primary["historical_sample_count"], 0)

    def test_key_evidence_is_list_of_strings(self) -> None:
        self.assertIsInstance(self.primary["key_evidence"], list)
        for item in self.primary["key_evidence"]:
            self.assertIsInstance(item, str)

    def test_key_evidence_capped_at_five_items(self) -> None:
        # Contract spec: 1–5 short items. Builder caps at 5.
        self.assertLessEqual(len(self.primary["key_evidence"]), 5)


class PrimaryProjectionContract02ValuesTests(unittest.TestCase):
    """Specific value derivations across bullish / bearish / unavailable."""

    def test_bullish_scan_yields_bullish_direction_and_close_up(self) -> None:
        primary = build_primary_projection(_bullish_scan())
        self.assertEqual(primary["primary_direction"], "偏多")
        self.assertEqual(primary["close_projection"], "收涨")
        self.assertEqual(primary["five_state_projection"], "小涨")
        self.assertEqual(primary["open_projection"], "高开")
        self.assertEqual(primary["intraday_path_projection"], "高走")

    def test_bearish_scan_yields_bearish_direction_and_close_down(self) -> None:
        primary = build_primary_projection(_bearish_scan())
        self.assertEqual(primary["primary_direction"], "偏空")
        self.assertEqual(primary["close_projection"], "收跌")
        self.assertEqual(primary["five_state_projection"], "小跌")
        self.assertEqual(primary["open_projection"], "低开")
        self.assertEqual(primary["intraday_path_projection"], "低走")

    def test_primary_confidence_raw_mirrors_final_confidence(self) -> None:
        primary = build_primary_projection(_bullish_scan())
        self.assertEqual(
            primary["primary_confidence_raw"], primary["final_confidence"]
        )

    def test_key_evidence_contains_only_avgo_signals(self) -> None:
        primary = build_primary_projection(_bullish_scan())
        for item in primary["key_evidence"]:
            self.assertIn("avgo_", item)

    def test_unavailable_branch_provides_contract_valid_defaults(self) -> None:
        primary = build_primary_projection(None)
        self.assertEqual(primary["status"], "unavailable")
        self.assertEqual(primary["primary_direction"], "中性")
        self.assertEqual(primary["open_projection"], "平开")
        self.assertEqual(primary["intraday_path_projection"], "震荡")
        self.assertEqual(primary["close_projection"], "收平")
        self.assertEqual(primary["five_state_projection"], "震荡")
        self.assertEqual(primary["historical_sample_count"], 0)
        self.assertEqual(primary["key_evidence"], [])
        self.assertEqual(primary["primary_confidence_raw"], "low")


class PrimaryProjectionContract02RunPredictTests(unittest.TestCase):
    """Verify the fields survive the run_predict wrapper untouched."""

    def test_run_predict_primary_projection_carries_contract_02_fields(self) -> None:
        result = run_predict(_bullish_scan(), research_result=None, symbol="AVGO")
        primary = result["primary_projection"]
        for field in _CONTRACT_02_FIELDS:
            self.assertIn(field, primary, f"missing field: {field}")
        self.assertEqual(primary["primary_direction"], "偏多")
        self.assertEqual(primary["five_state_projection"], "小涨")


if __name__ == "__main__":
    unittest.main()
