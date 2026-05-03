"""Step 2B-4: build_final_projection self-publishes contract 06 fields.

Mirrors test_primary_projection_contract_fields.py and
test_peer_adjustment_contract_fields.py for the closing layer. Final-bias /
final-confidence / research-adjustment / path_risk strategy is NOT changed
by Step 2B-4; this file only checks the additive translation fields and the
adapter alignment.
"""
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
from services.projection_output_adapter import adapt_projection_output
from services.projection_output_contract import (
    _CLOSE,
    _DIRECTION,
    _FIVE_STATE,
    _OPEN,
    _PATH,
    _PROBABILITY_BUCKET,
)


_CONTRACT_06_FIELDS: tuple[str, ...] = (
    "final_direction",
    "final_open_projection",
    "final_intraday_path",
    "final_close_projection",
    "final_five_state",
    "probability_bucket",
    "key_price_levels",
    "final_one_sentence",
)

_LEGACY_FIELDS_KEPT: tuple[str, ...] = (
    "final_bias",
    "final_confidence",
    "pred_open",
    "pred_path",
    "pred_close",
    "notes",
    "prediction_summary",
    "supporting_factors",
    "conflicting_factors",
)


def _recent_rows(close_step: float = 1.0, base: float = 100.0) -> list[dict]:
    return [
        {
            "Date": f"2026-04-{day:02d}",
            "Open": base + (day - 1) * close_step - 0.25,
            "Close": base + (day - 1) * close_step,
            "Volume": 1_000_000 + day * 10_000,
            "O_gap": 0.006 if close_step >= 0 else -0.006,
            "C_move": 0.01 if close_step >= 0 else -0.01,
            "V_ratio": 1.2 if close_step >= 0 else 0.8,
        }
        for day in range(1, 21)
    ]


def _bullish_scan() -> dict:
    return {
        "symbol": "AVGO",
        "scan_timestamp": "2026-04-20T00:00:00",
        "scan_bias": "bullish",
        "scan_confidence": "medium",
        "avgo_gap_state": "gap_up",
        "avgo_intraday_state": "high_go",
        "avgo_volume_state": "expanding",
        "avgo_price_state": "bullish",
        "avgo_recent_20": _recent_rows(close_step=1.0),
        "relative_strength_summary": {
            "vs_nvda": "stronger",
            "vs_soxx": "stronger",
            "vs_qqq": "stronger",
        },
        "relative_strength_same_day_summary": {
            "vs_nvda": "stronger",
            "vs_soxx": "stronger",
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
    base["avgo_recent_20"] = _recent_rows(close_step=-1.0, base=120.0)
    base["relative_strength_summary"] = {
        "vs_nvda": "weaker", "vs_soxx": "weaker", "vs_qqq": "weaker",
    }
    base["relative_strength_same_day_summary"] = {
        "vs_nvda": "weaker", "vs_soxx": "weaker", "vs_qqq": "weaker",
    }
    return base


def _final_for(scan: dict) -> dict:
    primary = build_primary_projection(scan)
    peer = apply_peer_adjustment(primary, scan)
    return build_final_projection(primary, peer, research_result=None, scan_result=scan)


# ── 1. shape on the computed branch ─────────────────────────────────────────

class FinalProjectionContract06ShapeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.final = _final_for(_bullish_scan())

    def test_all_eight_contract_06_fields_present(self) -> None:
        for field in _CONTRACT_06_FIELDS:
            self.assertIn(field, self.final, f"missing field: {field}")

    def test_legacy_fields_are_kept(self) -> None:
        for field in _LEGACY_FIELDS_KEPT:
            self.assertIn(field, self.final, f"legacy field dropped: {field}")

    def test_final_direction_in_contract_enum(self) -> None:
        self.assertIn(self.final["final_direction"], _DIRECTION)

    def test_final_open_projection_in_contract_enum(self) -> None:
        self.assertIn(self.final["final_open_projection"], _OPEN)

    def test_final_intraday_path_in_contract_enum(self) -> None:
        self.assertIn(self.final["final_intraday_path"], _PATH)

    def test_final_close_projection_in_contract_enum(self) -> None:
        self.assertIn(self.final["final_close_projection"], _CLOSE)

    def test_final_five_state_in_contract_enum(self) -> None:
        self.assertIn(self.final["final_five_state"], _FIVE_STATE)

    def test_probability_bucket_in_contract_enum(self) -> None:
        self.assertIn(self.final["probability_bucket"], _PROBABILITY_BUCKET)

    def test_key_price_levels_is_dict(self) -> None:
        self.assertIsInstance(self.final["key_price_levels"], dict)

    def test_final_one_sentence_is_non_empty_str(self) -> None:
        self.assertIsInstance(self.final["final_one_sentence"], str)
        self.assertGreater(len(self.final["final_one_sentence"]), 0)


# ── 2. specific value derivations ───────────────────────────────────────────

class FinalProjectionContract06ValuesTests(unittest.TestCase):
    def test_bullish_scan_yields_bullish_close_up(self) -> None:
        final = _final_for(_bullish_scan())
        self.assertEqual(final["final_direction"], "偏多")
        self.assertEqual(final["final_open_projection"], "高开")
        self.assertEqual(final["final_intraday_path"], "高走")
        self.assertEqual(final["final_close_projection"], "收涨")
        self.assertEqual(final["final_five_state"], "小涨")

    def test_bearish_scan_yields_bearish_close_down(self) -> None:
        final = _final_for(_bearish_scan())
        self.assertEqual(final["final_direction"], "偏空")
        self.assertEqual(final["final_open_projection"], "低开")
        self.assertEqual(final["final_intraday_path"], "低走")
        self.assertEqual(final["final_close_projection"], "收跌")
        self.assertEqual(final["final_five_state"], "小跌")

    def test_probability_bucket_maps_from_final_confidence(self) -> None:
        # bullish + all peers stronger → confidence raised to high
        final = _final_for(_bullish_scan())
        self.assertEqual(final["final_confidence"], "high")
        self.assertEqual(final["probability_bucket"], "≥70%")

    def test_final_one_sentence_matches_prediction_summary(self) -> None:
        final = _final_for(_bullish_scan())
        self.assertEqual(final["final_one_sentence"], final["prediction_summary"])

    def test_unavailable_branch_provides_contract_valid_defaults(self) -> None:
        primary = build_primary_projection(None)
        peer = apply_peer_adjustment(primary, None)
        final = build_final_projection(primary, peer, research_result=None, scan_result=None)
        self.assertEqual(final["status"], "unavailable")
        self.assertEqual(final["final_direction"], "中性")
        self.assertEqual(final["final_open_projection"], "平开")
        self.assertEqual(final["final_intraday_path"], "震荡")
        self.assertEqual(final["final_close_projection"], "收平")
        self.assertEqual(final["final_five_state"], "震荡")
        self.assertEqual(final["probability_bucket"], "45–55%")
        self.assertEqual(final["key_price_levels"], {})
        self.assertIsInstance(final["final_one_sentence"], str)
        self.assertGreater(len(final["final_one_sentence"]), 0)


# ── 3. run_predict wrapper passes the fields through ────────────────────────

class FinalProjectionRunPredictTests(unittest.TestCase):
    def test_run_predict_final_projection_carries_contract_06_fields(self) -> None:
        result = run_predict(_bullish_scan(), research_result=None, symbol="AVGO")
        final = result["final_projection"]
        for field in _CONTRACT_06_FIELDS:
            self.assertIn(field, final, f"missing field: {field}")
        self.assertEqual(final["final_direction"], "偏多")
        self.assertEqual(final["final_five_state"], "小涨")


# ── 4. adapter consistency: contract section == self-published ──────────────

class FinalProjectionAdapterAlignmentTests(unittest.TestCase):
    def _payload_from(self, scan: dict) -> tuple[dict, dict]:
        result = run_predict(scan, research_result=None, symbol="AVGO")
        payload = adapt_projection_output(
            scan_result=scan, research_result=None, predict_result=result
        )
        return result["final_projection"], payload["final_projection"]

    def test_adapter_section_mirrors_self_published_fields(self) -> None:
        final, section = self._payload_from(_bullish_scan())
        for key in _CONTRACT_06_FIELDS:
            self.assertEqual(
                section[key], final[key],
                f"adapter {key} != self-published final_projection.{key}",
            )

    def test_adapter_section_mirrors_under_bearish(self) -> None:
        final, section = self._payload_from(_bearish_scan())
        self.assertEqual(section["final_direction"], "偏空")
        self.assertEqual(section["final_direction"], final["final_direction"])
        self.assertEqual(section["final_five_state"], final["final_five_state"])
        self.assertEqual(section["probability_bucket"], final["probability_bucket"])


if __name__ == "__main__":
    unittest.main()
