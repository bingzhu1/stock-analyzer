# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from predict import (
    apply_peer_adjustment,
    build_final_projection,
    build_primary_projection,
    run_predict,
)


def _recent_rows(close_start: float = 100.0, close_step: float = 1.0) -> list[dict]:
    return [
        {
            "Date": f"2026-04-{day:02d}",
            "Open": close_start + (day - 1) * close_step - 0.25,
            "Close": close_start + (day - 1) * close_step,
            "O_gap": 0.006 if close_step >= 0 else -0.006,
            "C_move": 0.01 if close_step >= 0 else -0.01,
            "V_ratio": 1.2 if close_step >= 0 else 0.8,
        }
        for day in range(1, 21)
    ]


def _scan(
    *,
    gap: str = "gap_up",
    intraday: str = "high_go",
    volume: str = "expanding",
    price: str = "bullish",
    dominant: str = "up_bias",
    rs_5d: dict | None = None,
    rs_same_day: dict | None = None,
) -> dict:
    return {
        "symbol": "AVGO",
        "scan_bias": "bullish",
        "scan_confidence": "medium",
        "avgo_gap_state": gap,
        "avgo_intraday_state": intraday,
        "avgo_volume_state": volume,
        "avgo_price_state": price,
        "historical_match_summary": {
            "dominant_historical_outcome": dominant,
        },
        "avgo_recent_20": _recent_rows(close_step=1.0),
        "relative_strength_summary": rs_5d or {
            "vs_nvda": "stronger",
            "vs_soxx": "stronger",
            "vs_qqq": "neutral",
        },
        "relative_strength_same_day_summary": rs_same_day or {
            "vs_nvda": "stronger",
            "vs_soxx": "neutral",
            "vs_qqq": "stronger",
        },
    }


class PrimaryProjectionTests(unittest.TestCase):
    def test_primary_projection_is_avgo_only(self) -> None:
        scan = _scan(
            rs_5d={"vs_nvda": "weaker", "vs_soxx": "weaker", "vs_qqq": "weaker"},
            rs_same_day={"vs_nvda": "weaker", "vs_soxx": "weaker", "vs_qqq": "weaker"},
        )

        primary = build_primary_projection(scan)

        self.assertEqual(primary["status"], "computed")
        self.assertIs(primary["peer_inputs_used"], False)
        self.assertEqual(primary["lookback_days"], 20)
        self.assertEqual(primary["recent_20_summary"]["sample_count"], 20)
        self.assertGreater(primary["recent_20_summary"]["close_return"], 0)
        self.assertEqual(primary["direct_features"]["gap_state"], "gap_up")
        self.assertEqual(primary["direct_features"]["recent_20_trend_state"], "bullish")
        self.assertFalse(primary["input_boundary"]["fallback_scan_states_used"])
        self.assertIn("historical_match_summary", primary["input_boundary"]["excluded_inputs"])
        self.assertNotIn("historical_match_summary", primary)
        self.assertFalse(any("dominant_historical_outcome" in signal for signal in primary["signals"]))
        self.assertEqual(primary["final_bias"], "bullish")
        self.assertEqual(primary["pred_open"], "高开")
        self.assertEqual(primary["pred_close"], "收涨")
        self.assertEqual(primary["pred_path"], "高开高走")

    def test_primary_projection_ignores_historical_match_direction(self) -> None:
        up_history = build_primary_projection(_scan(dominant="up_bias"))
        down_history = build_primary_projection(_scan(dominant="down_bias"))

        self.assertEqual(up_history["score"], down_history["score"])
        self.assertEqual(up_history["signals"], down_history["signals"])

    def test_missing_scan_returns_unavailable_primary(self) -> None:
        primary = build_primary_projection(None)

        self.assertEqual(primary["status"], "unavailable")
        self.assertEqual(primary["lookback_days"], 20)
        self.assertEqual(primary["final_bias"], "unavailable")
        self.assertIs(primary["pred_open"], None)


class PeerAdjustmentTests(unittest.TestCase):
    def test_peer_confirmation_reinforces_confidence(self) -> None:
        primary = {
            "final_bias": "bullish",
            "final_confidence": "medium",
        }

        adjustment = apply_peer_adjustment(primary, _scan())

        self.assertEqual(adjustment["status"], "computed")
        self.assertEqual(adjustment["adjustment_direction"], "reinforce")
        self.assertEqual(adjustment["adjusted_bias"], "bullish")
        self.assertEqual(adjustment["adjusted_confidence"], "high")
        self.assertEqual(adjustment["confirm_count"], 3)
        self.assertEqual(adjustment["path_risk_adjustment"]["risk_direction"], "lower")
        self.assertEqual(adjustment["path_risk_adjustment"]["after"], "low")
        self.assertEqual(adjustment["data_source"]["current"], "scanner_relative_strength_labels")

    def test_peer_divergence_weakens_confidence(self) -> None:
        primary = {
            "final_bias": "bullish",
            "final_confidence": "medium",
        }
        scan = _scan(
            rs_5d={"vs_nvda": "weaker", "vs_soxx": "weaker", "vs_qqq": "neutral"},
            rs_same_day={"vs_nvda": "weaker", "vs_soxx": "weaker", "vs_qqq": "weaker"},
        )

        adjustment = apply_peer_adjustment(primary, scan)

        self.assertEqual(adjustment["adjustment_direction"], "weaken")
        self.assertEqual(adjustment["adjusted_bias"], "bullish")
        self.assertEqual(adjustment["adjusted_confidence"], "low")
        self.assertEqual(adjustment["oppose_count"], 3)
        self.assertEqual(adjustment["path_risk_adjustment"]["risk_direction"], "higher")
        self.assertEqual(adjustment["path_risk_adjustment"]["after"], "high")


class FinalProjectionTests(unittest.TestCase):
    def test_final_projection_keeps_prediction_compatibility_fields(self) -> None:
        primary = build_primary_projection(_scan())
        peer = apply_peer_adjustment(primary, _scan())

        final = build_final_projection(primary, peer, research_result=None, scan_result=_scan())

        self.assertEqual(final["status"], "computed")
        self.assertEqual(final["source"], "primary_projection_plus_peer_adjustment")
        self.assertEqual(final["final_bias"], "bullish")
        self.assertEqual(final["final_confidence"], "high")
        self.assertEqual(final["open_tendency"], "gap_up_bias")
        self.assertEqual(final["close_tendency"], "close_strong")
        self.assertEqual(final["pred_open"], "高开")
        self.assertEqual(final["pred_path"], "高开高走")
        self.assertEqual(final["path_risk"], "low")
        self.assertEqual(final["peer_path_risk_adjustment"]["risk_direction"], "lower")

    def test_final_projection_keeps_path_label_but_marks_peer_path_risk(self) -> None:
        primary = build_primary_projection(_scan())
        peer = apply_peer_adjustment(
            primary,
            _scan(
                rs_5d={"vs_nvda": "weaker", "vs_soxx": "weaker", "vs_qqq": "weaker"},
                rs_same_day={"vs_nvda": "weaker", "vs_soxx": "weaker", "vs_qqq": "weaker"},
            ),
        )

        final = build_final_projection(primary, peer, research_result=None, scan_result=_scan())

        self.assertEqual(final["pred_path"], primary["pred_path"])
        self.assertEqual(final["path_risk"], "medium")
        self.assertEqual(final["peer_path_risk_adjustment"]["risk_direction"], "higher")
        self.assertIn("peer_path_risk=medium", final["conflicting_factors"])


class RunPredictV2Tests(unittest.TestCase):
    def test_run_predict_returns_old_fields_and_v2_blocks(self) -> None:
        result = run_predict(_scan(), research_result=None, symbol="AVGO")

        for key in (
            "symbol",
            "final_bias",
            "final_confidence",
            "open_tendency",
            "close_tendency",
            "prediction_summary",
        ):
            self.assertIn(key, result)

        self.assertEqual(result["primary_projection"]["status"], "computed")
        self.assertEqual(result["peer_adjustment"]["status"], "computed")
        self.assertEqual(result["final_projection"]["status"], "computed")
        self.assertEqual(result["final_bias"], result["final_projection"]["final_bias"])
        self.assertEqual(result["pred_open"], result["final_projection"]["pred_open"])
        self.assertEqual(result["path_risk"], result["final_projection"]["path_risk"])

    def test_run_predict_missing_scan_keeps_final_unavailable(self) -> None:
        result = run_predict(None, research_result=None, symbol="AVGO")

        self.assertEqual(result["final_bias"], "unavailable")
        self.assertEqual(result["primary_projection"]["status"], "unavailable")
        self.assertEqual(result["final_projection"]["status"], "unavailable")
        self.assertEqual(result["final_projection"]["final_bias"], "unavailable")


if __name__ == "__main__":
    unittest.main()
