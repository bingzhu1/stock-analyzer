"""Step 2B-1 contract-alignment safety net.

End-to-end regression: run_predict(...) → adapt_projection_output(...) →
validate_projection_output(...) must produce a contract-valid 8-section
payload, today, without touching any business code.

The test deliberately encodes the **known data_window_days inconsistency**:
    - predict.py        : _PRIMARY_LOOKBACK_DAYS = 20
    - primary_projection: lookback_days = 20
    - adapter           : current_structure.data_window_days hard-coded 15

Step 2B-1 only locks the *current* state into a regression test. The
mismatch is not fixed here; it is left as a follow-up for Step 2B-2 / 2C
(see tasks/step_1a_projection_output_contract.md §"已知不一致").
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

    # ── KNOWN INCONSISTENCY (Step 2B-1 exposes; does NOT fix) ──────────────
    #
    # predict.py        : _PRIMARY_LOOKBACK_DAYS = 20
    # primary_projection: lookback_days = 20  (live computation)
    # adapter           : current_structure.data_window_days = 15
    #                     (hard-coded constant, services/projection_output_adapter.py:154)
    #
    # Both numbers below are pinned on purpose so that any future change to
    # either side surfaces here. Resolution belongs to Step 2B-2 / Step 2C
    # (see tasks/step_1a_projection_output_contract.md §"已知不一致").

    def test_primary_projection_lookback_days_is_20(self) -> None:
        self.assertEqual(
            self.predict_result["primary_projection"]["lookback_days"], 20,
            "predict.py _PRIMARY_LOOKBACK_DAYS regression",
        )

    def test_adapter_current_structure_data_window_days_is_15(self) -> None:
        self.assertEqual(
            self.payload["current_structure"]["data_window_days"], 15,
            "adapter hard-coded data_window_days regression "
            "(known inconsistency vs predict.py = 20; see Step 2B-1 doc)",
        )

    def test_lookback_and_data_window_days_currently_disagree(self) -> None:
        """Lock in that the two numbers do NOT match today.

        Once Step 2B-2 / 2C unifies them, this test should fail and be
        deleted in the same change-set that fixes the inconsistency.
        """
        primary_lookback = self.predict_result["primary_projection"]["lookback_days"]
        contract_window = self.payload["current_structure"]["data_window_days"]
        self.assertNotEqual(
            primary_lookback, contract_window,
            "If these now match, the Step 2B-1 known-inconsistency note in "
            "tasks/step_1a_projection_output_contract.md is stale — delete "
            "this test as part of the fix.",
        )


if __name__ == "__main__":
    unittest.main()
