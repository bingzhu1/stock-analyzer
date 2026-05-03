"""Step 2B-3: apply_peer_adjustment self-publishes contract 03 fields.

Mirrors test_primary_projection_contract_fields.py for the peer layer.
Strategy logic (vote → adjustment_direction → adjusted_bias) is NOT changed
by Step 2B-3; this file only checks the additive translation fields.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from predict import apply_peer_adjustment, run_predict
from services.projection_output_adapter import adapt_projection_output
from services.projection_output_contract import (
    _DIRECTION,
    _PEER_ADJUSTMENT,
    _PEER_ALIGNMENT,
    _PEER_SIGNAL,
)


_CONTRACT_03_FIELDS: tuple[str, ...] = (
    "peer_symbols",
    "nvda_signal",
    "soxx_signal",
    "qqq_signal",
    "peer_alignment",
    "peer_adjustment",
    "adjusted_direction",
    "adjustment_reason",
)

_LEGACY_FIELDS_KEPT: tuple[str, ...] = (
    "peer_symbols",
    "confirm_count",
    "oppose_count",
    "adjusted_bias",
    "adjusted_confidence",
    "adjustment_direction",
    "adjustments",
    "notes",
)


def _recent_rows() -> list[dict]:
    return [
        {
            "Date": f"2026-04-{day:02d}",
            "Open": 99.75 + (day - 1),
            "Close": 100.0 + (day - 1),
            "Volume": 1_000_000 + day * 10_000,
            "O_gap": 0.006,
            "C_move": 0.01,
            "V_ratio": 1.2,
        }
        for day in range(1, 21)
    ]


def _scan(rs_5d: dict | None = None, rs_same_day: dict | None = None) -> dict:
    return {
        "symbol": "AVGO",
        "scan_timestamp": "2026-04-20T00:00:00",
        "scan_bias": "bullish",
        "scan_confidence": "medium",
        "avgo_gap_state": "gap_up",
        "avgo_intraday_state": "high_go",
        "avgo_volume_state": "expanding",
        "avgo_price_state": "bullish",
        "avgo_recent_20": _recent_rows(),
        "relative_strength_summary": rs_5d if rs_5d is not None else {
            "vs_nvda": "stronger",
            "vs_soxx": "stronger",
            "vs_qqq": "stronger",
        },
        "relative_strength_same_day_summary": rs_same_day if rs_same_day is not None else {
            "vs_nvda": "stronger",
            "vs_soxx": "stronger",
            "vs_qqq": "stronger",
        },
    }


def _bullish_primary() -> dict:
    return {"final_bias": "bullish", "final_confidence": "medium"}


def _bearish_primary() -> dict:
    return {"final_bias": "bearish", "final_confidence": "medium"}


# ── 1. peer_adjustment shape ────────────────────────────────────────────────

class PeerAdjustmentContract03ShapeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.peer = apply_peer_adjustment(_bullish_primary(), _scan())

    def test_all_eight_contract_03_fields_present(self) -> None:
        for field in _CONTRACT_03_FIELDS:
            self.assertIn(field, self.peer, f"missing field: {field}")

    def test_legacy_fields_are_kept(self) -> None:
        for field in _LEGACY_FIELDS_KEPT:
            self.assertIn(field, self.peer, f"legacy field dropped: {field}")

    def test_peer_symbols_is_three_tickers(self) -> None:
        self.assertEqual(self.peer["peer_symbols"], ["NVDA", "SOXX", "QQQ"])

    def test_nvda_signal_in_contract_enum(self) -> None:
        self.assertIn(self.peer["nvda_signal"], _PEER_SIGNAL)

    def test_soxx_signal_in_contract_enum(self) -> None:
        self.assertIn(self.peer["soxx_signal"], _PEER_SIGNAL)

    def test_qqq_signal_in_contract_enum(self) -> None:
        self.assertIn(self.peer["qqq_signal"], _PEER_SIGNAL)

    def test_peer_alignment_in_contract_enum(self) -> None:
        self.assertIn(self.peer["peer_alignment"], _PEER_ALIGNMENT)

    def test_peer_adjustment_in_contract_enum(self) -> None:
        self.assertIn(self.peer["peer_adjustment"], _PEER_ADJUSTMENT)

    def test_adjusted_direction_in_contract_enum(self) -> None:
        self.assertIn(self.peer["adjusted_direction"], _DIRECTION)

    def test_adjustment_reason_is_str(self) -> None:
        self.assertIsInstance(self.peer["adjustment_reason"], str)
        self.assertGreater(len(self.peer["adjustment_reason"]), 0)


# ── 2. specific value derivations ───────────────────────────────────────────

class PeerAdjustmentContract03ValuesTests(unittest.TestCase):
    def test_all_peers_stronger_under_bullish_primary_yields_all_reinforce(self) -> None:
        peer = apply_peer_adjustment(_bullish_primary(), _scan())
        # confirm_count == 3, oppose_count == 0 → all_reinforce
        self.assertEqual(peer["nvda_signal"], "reinforce")
        self.assertEqual(peer["soxx_signal"], "reinforce")
        self.assertEqual(peer["qqq_signal"], "reinforce")
        self.assertEqual(peer["peer_alignment"], "all_reinforce")
        self.assertEqual(peer["peer_adjustment"], "upgrade")
        self.assertEqual(peer["adjusted_direction"], "偏多")

    def test_all_peers_weaker_under_bullish_primary_yields_all_weaken(self) -> None:
        peer = apply_peer_adjustment(
            _bullish_primary(),
            _scan(
                rs_5d={"vs_nvda": "weaker", "vs_soxx": "weaker", "vs_qqq": "weaker"},
                rs_same_day={"vs_nvda": "weaker", "vs_soxx": "weaker", "vs_qqq": "weaker"},
            ),
        )
        self.assertEqual(peer["nvda_signal"], "weaken")
        self.assertEqual(peer["soxx_signal"], "weaken")
        self.assertEqual(peer["qqq_signal"], "weaken")
        self.assertEqual(peer["peer_alignment"], "all_weaken")
        self.assertEqual(peer["peer_adjustment"], "downgrade")

    def test_missing_relative_strength_yields_unknown_signals_and_insufficient(self) -> None:
        peer = apply_peer_adjustment(
            _bullish_primary(),
            _scan(rs_5d={}, rs_same_day={}),
        )
        # All votes "unavailable" → all signals "unknown"
        self.assertEqual(peer["nvda_signal"], "unknown")
        self.assertEqual(peer["soxx_signal"], "unknown")
        self.assertEqual(peer["qqq_signal"], "unknown")
        self.assertEqual(peer["peer_alignment"], "insufficient")
        # primary_bias bullish, no votes → adjustment_direction "neutral" → label "hold"
        self.assertEqual(peer["peer_adjustment"], "hold")

    def test_neutral_primary_yields_flip_to_neutral_label(self) -> None:
        # primary_bias not in {bullish,bearish} → adjustment_direction "neutral_primary"
        peer = apply_peer_adjustment(
            {"final_bias": "neutral", "final_confidence": "low"},
            _scan(),
        )
        self.assertEqual(peer["adjustment_direction"], "neutral_primary")
        self.assertEqual(peer["peer_adjustment"], "flip_to_neutral")

    def test_mixed_votes_yield_mixed_alignment(self) -> None:
        peer = apply_peer_adjustment(
            _bullish_primary(),
            _scan(
                rs_5d={"vs_nvda": "stronger", "vs_soxx": "weaker", "vs_qqq": "neutral"},
                rs_same_day={"vs_nvda": "stronger", "vs_soxx": "weaker", "vs_qqq": "neutral"},
            ),
        )
        # confirm_count == 1, oppose_count == 1 → mixed
        self.assertEqual(peer["peer_alignment"], "mixed")

    def test_adjusted_direction_mirrors_adjusted_bias(self) -> None:
        peer = apply_peer_adjustment(_bearish_primary(), _scan())
        # bearish primary + all peers stronger → confirm_count == 0, oppose_count == 3
        # adjusted_bias depends on confidence; we just check the translation map.
        if peer["adjusted_bias"] == "bullish":
            self.assertEqual(peer["adjusted_direction"], "偏多")
        elif peer["adjusted_bias"] == "bearish":
            self.assertEqual(peer["adjusted_direction"], "偏空")
        else:
            self.assertEqual(peer["adjusted_direction"], "中性")


# ── 3. run_predict wrapper passes the fields through ────────────────────────

class PeerAdjustmentRunPredictTests(unittest.TestCase):
    def test_run_predict_peer_adjustment_carries_contract_03_fields(self) -> None:
        result = run_predict(_scan(), research_result=None, symbol="AVGO")
        peer = result["peer_adjustment"]
        for field in _CONTRACT_03_FIELDS:
            self.assertIn(field, peer, f"missing field: {field}")
        self.assertIn(peer["peer_alignment"], _PEER_ALIGNMENT)
        self.assertIn(peer["peer_adjustment"], _PEER_ADJUSTMENT)
        self.assertIn(peer["adjusted_direction"], _DIRECTION)


# ── 4. adapter consistency: contract section == self-published ──────────────

class PeerAdjustmentAdapterAlignmentTests(unittest.TestCase):
    """When peer_adjustment self-publishes contract 03 fields, the adapter's
    contract section MUST mirror those values (no double-translation)."""

    def _payload_from(self, scan: dict) -> tuple[dict, dict]:
        result = run_predict(scan, research_result=None, symbol="AVGO")
        payload = adapt_projection_output(
            scan_result=scan, research_result=None, predict_result=result
        )
        return result["peer_adjustment"], payload["peer_confirmation_adjustment"]

    def test_adapter_section_mirrors_self_published_signals(self) -> None:
        peer, section = self._payload_from(_scan())
        for key in (
            "nvda_signal",
            "soxx_signal",
            "qqq_signal",
            "peer_alignment",
            "peer_adjustment",
            "adjusted_direction",
            "adjustment_reason",
        ):
            self.assertEqual(
                section[key], peer[key],
                f"adapter {key} != self-published peer_adjustment.{key}",
            )

    def test_adapter_section_mirrors_under_all_weaken(self) -> None:
        scan = _scan(
            rs_5d={"vs_nvda": "weaker", "vs_soxx": "weaker", "vs_qqq": "weaker"},
            rs_same_day={"vs_nvda": "weaker", "vs_soxx": "weaker", "vs_qqq": "weaker"},
        )
        peer, section = self._payload_from(scan)
        self.assertEqual(section["peer_alignment"], "all_weaken")
        self.assertEqual(section["peer_alignment"], peer["peer_alignment"])
        self.assertEqual(section["peer_adjustment"], peer["peer_adjustment"])


if __name__ == "__main__":
    unittest.main()
