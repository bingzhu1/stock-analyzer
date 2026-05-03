"""Contract-alignment safety net (Step 2B-1 baseline + Step 2B-2 update).

End-to-end regression: run_predict(...) → adapt_projection_output(...) →
validate_projection_output(...) must produce a contract-valid 8-section
payload, today, without touching any business code.

History:
    Step 2B-1: pinned the *known* data_window_days inconsistency
               (primary_projection.lookback_days = 20, adapter hard-coded 15)
               so future drift would be caught.
    Step 2B-2: adapter now reads predict_result["primary_projection"]
               ["lookback_days"]. The two values are wired and equal.
               The earlier ``assertNotEqual`` case has been removed;
               the assertions below pin both values to 20 and require
               equality.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from predict import run_predict
from services.projection_output_adapter import adapt_projection_output
from services.projection_output_contract import (
    CONTRACT_SECTIONS,
    validate_projection_output,
)


def _recent_rows(close_start: float = 100.0, close_step: float = 1.0) -> list[dict]:
    """Twenty synthetic AVGO daily rows. Mirrors tests/test_predict.py:_recent_rows."""
    return [
        {
            "Date": f"2026-04-{day:02d}",
            "Open": close_start + (day - 1) * close_step - 0.25,
            "Close": close_start + (day - 1) * close_step,
            "Volume": 1_000_000 + day * 10_000,
            "O_gap": 0.006 if close_step >= 0 else -0.006,
            "C_move": 0.01 if close_step >= 0 else -0.01,
            "V_ratio": 1.2 if close_step >= 0 else 0.8,
        }
        for day in range(1, 21)
    ]


def _scan_result() -> dict:
    """Minimal scan_result that drives a fully-computed run_predict path.

    Mirrors the bullish/expanding/up_bias case used in tests/test_predict.py
    so the resulting predict_result has all primary/peer/final dicts
    populated (no 'unavailable' branch).
    """
    return {
        "symbol": "AVGO",
        "scan_timestamp": "2026-04-20T00:00:00",
        "scan_phase": "daily",
        "scan_phase_note": "<placeholder note>",
        "scan_bias": "bullish",
        "scan_confidence": "medium",
        "avgo_gap_state": "gap_up",
        "avgo_intraday_state": "high_go",
        "avgo_volume_state": "expanding",
        "avgo_price_state": "bullish",
        "historical_match_summary": {
            "dominant_historical_outcome": "up_bias",
        },
        "avgo_recent_20": _recent_rows(close_step=1.0),
        "relative_strength_summary": {
            "vs_nvda": "stronger",
            "vs_soxx": "stronger",
            "vs_qqq": "neutral",
            "NVDA": {"relative_strength": "stronger"},
            "SOXX": {"relative_strength": "neutral"},
            "QQQ": {"relative_strength": "stronger"},
        },
        "relative_strength_same_day_summary": {
            "vs_nvda": "stronger",
            "vs_soxx": "neutral",
            "vs_qqq": "stronger",
        },
    }


class RunPredictContractAlignmentTests(unittest.TestCase):
    """Step 2B-1: pin the run_predict → adapter → validator chain green."""

    def setUp(self) -> None:
        self.scan = _scan_result()
        self.research = None
        self.predict_result = run_predict(
            self.scan, research_result=self.research, symbol="AVGO"
        )
        self.payload = adapt_projection_output(
            scan_result=self.scan,
            research_result=self.research,
            predict_result=self.predict_result,
        )

    # ── contract validity ───────────────────────────────────────────────────

    def test_payload_is_contract_valid(self) -> None:
        errors = validate_projection_output(self.payload)
        self.assertEqual(errors, [])

    def test_payload_has_exactly_eight_sections(self) -> None:
        self.assertEqual(set(self.payload.keys()), set(CONTRACT_SECTIONS))
        self.assertEqual(len(self.payload), 8)

    # ── per-section presence ───────────────────────────────────────────────

    def test_avgo_primary_projection_section_exists(self) -> None:
        self.assertIn("avgo_primary_projection", self.payload)
        self.assertIsInstance(self.payload["avgo_primary_projection"], dict)
        self.assertGreater(len(self.payload["avgo_primary_projection"]), 0)

    def test_peer_confirmation_adjustment_section_exists(self) -> None:
        self.assertIn("peer_confirmation_adjustment", self.payload)
        self.assertIsInstance(self.payload["peer_confirmation_adjustment"], dict)
        self.assertGreater(len(self.payload["peer_confirmation_adjustment"]), 0)

    def test_final_projection_section_exists(self) -> None:
        self.assertIn("final_projection", self.payload)
        self.assertIsInstance(self.payload["final_projection"], dict)
        self.assertGreater(len(self.payload["final_projection"]), 0)

    # ── frozen stub: simulated_trade.trade_action ──────────────────────────

    def test_simulated_trade_is_no_trade_stub(self) -> None:
        # Step 1C scope: adapter hardcodes the 07 section to a no_trade stub
        # (see services/projection_output_adapter.py::_build_simulated_trade).
        # If this changes, the simulated-trade engine is being wired and the
        # test should be revisited under that step, not silently relaxed.
        self.assertEqual(
            self.payload["simulated_trade"]["trade_action"], "no_trade"
        )
        self.assertEqual(
            self.payload["simulated_trade"]["trade_direction"], "none"
        )

    # ── data_window_days wiring (Step 2B-2) ────────────────────────────────
    #
    # predict.py            : _PRIMARY_LOOKBACK_DAYS = 20
    # primary_projection    : lookback_days = 20  (live computation)
    # adapter / contract 01 : current_structure.data_window_days reads from
    #                         predict_result["primary_projection"]
    #                         ["lookback_days"]
    #
    # Both numbers must match. Any future change to _PRIMARY_LOOKBACK_DAYS
    # propagates through the adapter automatically.

    def test_primary_projection_lookback_days_is_20(self) -> None:
        self.assertEqual(
            self.predict_result["primary_projection"]["lookback_days"], 20,
            "predict.py _PRIMARY_LOOKBACK_DAYS regression",
        )

    def test_contract_data_window_days_matches_primary_lookback(self) -> None:
        primary_lookback = self.predict_result["primary_projection"]["lookback_days"]
        contract_window = self.payload["current_structure"]["data_window_days"]
        self.assertEqual(primary_lookback, contract_window)
        self.assertEqual(contract_window, 20)


if __name__ == "__main__":
    unittest.main()
