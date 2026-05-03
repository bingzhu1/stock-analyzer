"""Step 2C-2: contract 04 exclusion_system stays stubbed, but extras
surfaces the raw risk signals already in predict_result.

This file does NOT test a real exclusion engine — there is none. It only
checks that:
  1. the 5 contract-required fields remain at the "no exclusion observed"
     stub (none / [] / [] / False / False), and
  2. an additive ``extras`` sub-dict reflects ``conflicting_factors`` /
     ``path_risk`` / ``peer_path_risk_adjustment`` from predict_result.

If a future step wires a real exclusion module, the required-fields
assertions in this file will need to be relaxed in the same change-set.
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
from services.projection_output_contract import validate_projection_output


_REQUIRED_04_FIELDS: tuple[str, ...] = (
    "exclusion_level",
    "exclusion_sources",
    "exclusion_reasons",
    "forced_exclusion",
    "anti_false_exclusion_triggered",
)

_EXTRAS_KEYS: tuple[str, ...] = (
    "conflicting_factors_count",
    "conflicting_factors",
    "path_risk_level",
    "peer_path_risk_direction",
    "peer_path_risk_reasons",
    "soft_signal",
)


def _section(predict_result: dict | None) -> dict:
    payload = adapt_projection_output(
        scan_result=None, research_result=None, predict_result=predict_result
    )
    return payload["exclusion_system"]


# ── 1. required fields stay at the "no exclusion observed" stub ────────────

class ExclusionRequiredFieldsRemainStubTests(unittest.TestCase):
    def test_required_fields_present_with_empty_predict_result(self) -> None:
        section = _section(None)
        for field in _REQUIRED_04_FIELDS:
            self.assertIn(field, section)

    def test_required_fields_are_no_exclusion_observed_stub(self) -> None:
        section = _section(None)
        self.assertEqual(section["exclusion_level"], "none")
        self.assertEqual(section["exclusion_sources"], [])
        self.assertEqual(section["exclusion_reasons"], [])
        self.assertIs(section["forced_exclusion"], False)
        self.assertIs(section["anti_false_exclusion_triggered"], False)

    def test_required_fields_unchanged_under_strong_risk_input(self) -> None:
        # Even when the predict_result carries explicit weaken / high-risk
        # signals, the 5 required fields must not move — Step 2C-2 only
        # surfaces signals into extras, never into the required slots.
        predict = {
            "conflicting_factors": [
                "peer_confirmation=weaken",
                "peer_path_risk=high",
            ],
            "path_risk": "high",
            "peer_path_risk_adjustment": {
                "risk_direction": "higher",
                "reasons": ["peer_layer_weaken"],
            },
        }
        section = _section(predict)
        self.assertEqual(section["exclusion_level"], "none")
        self.assertEqual(section["exclusion_sources"], [])
        self.assertEqual(section["exclusion_reasons"], [])
        self.assertIs(section["forced_exclusion"], False)
        self.assertIs(section["anti_false_exclusion_triggered"], False)


# ── 2. extras presence & shape ─────────────────────────────────────────────

class ExclusionExtrasShapeTests(unittest.TestCase):
    def test_extras_present_even_when_predict_result_is_none(self) -> None:
        section = _section(None)
        self.assertIn("extras", section)
        self.assertIsInstance(section["extras"], dict)
        for key in _EXTRAS_KEYS:
            self.assertIn(key, section["extras"], f"missing extras.{key}")

    def test_extras_default_values_are_empty_neutral(self) -> None:
        section = _section(None)
        extras = section["extras"]
        self.assertEqual(extras["conflicting_factors_count"], 0)
        self.assertEqual(extras["conflicting_factors"], [])
        self.assertEqual(extras["path_risk_level"], "unknown")
        self.assertEqual(extras["peer_path_risk_direction"], "unknown")
        self.assertEqual(extras["peer_path_risk_reasons"], [])
        self.assertEqual(extras["soft_signal"], "none")


# ── 3. extras values reflect predict_result ─────────────────────────────────

class ExclusionExtrasValueMappingTests(unittest.TestCase):
    def test_conflicting_factors_count_and_list_mirror_predict_result(self) -> None:
        predict = {
            "conflicting_factors": ["peer_confirmation=weaken", "peer_path_risk=medium"],
            "path_risk": "medium",
        }
        extras = _section(predict)["extras"]
        self.assertEqual(extras["conflicting_factors_count"], 2)
        self.assertEqual(
            extras["conflicting_factors"],
            ["peer_confirmation=weaken", "peer_path_risk=medium"],
        )

    def test_path_risk_level_passes_through(self) -> None:
        for level in ("low", "medium", "high"):
            with self.subTest(level=level):
                section = _section({"path_risk": level})
                self.assertEqual(section["extras"]["path_risk_level"], level)

    def test_peer_path_risk_direction_and_reasons_pass_through(self) -> None:
        predict = {
            "peer_path_risk_adjustment": {
                "risk_direction": "higher",
                "reasons": ["peer_layer_weaken", "scan_volatility_high"],
            },
        }
        extras = _section(predict)["extras"]
        self.assertEqual(extras["peer_path_risk_direction"], "higher")
        self.assertEqual(
            extras["peer_path_risk_reasons"],
            ["peer_layer_weaken", "scan_volatility_high"],
        )

    def test_non_list_conflicting_factors_falls_back_to_empty(self) -> None:
        predict = {"conflicting_factors": "not-a-list"}
        extras = _section(predict)["extras"]
        self.assertEqual(extras["conflicting_factors_count"], 0)
        self.assertEqual(extras["conflicting_factors"], [])

    def test_non_dict_peer_path_risk_falls_back_to_unknown(self) -> None:
        predict = {"peer_path_risk_adjustment": "not-a-dict"}
        extras = _section(predict)["extras"]
        self.assertEqual(extras["peer_path_risk_direction"], "unknown")
        self.assertEqual(extras["peer_path_risk_reasons"], [])


# ── 4. soft_signal heuristic ───────────────────────────────────────────────

class ExclusionSoftSignalTests(unittest.TestCase):
    def test_peer_weaken_in_conflicting_factors_yields_peer_weaken(self) -> None:
        predict = {
            "conflicting_factors": ["peer_confirmation=weaken"],
            "path_risk": "low",
        }
        self.assertEqual(_section(predict)["extras"]["soft_signal"], "peer_weaken")

    def test_peer_weaken_takes_priority_over_high_path_risk(self) -> None:
        # Both signals present → peer_weaken wins (it's the more specific
        # peer-layer message; high_path_risk is a generic fallback).
        predict = {
            "conflicting_factors": ["peer_confirmation=weaken"],
            "path_risk": "high",
        }
        self.assertEqual(_section(predict)["extras"]["soft_signal"], "peer_weaken")

    def test_high_path_risk_alone_yields_high_path_risk(self) -> None:
        predict = {"conflicting_factors": [], "path_risk": "high"}
        self.assertEqual(_section(predict)["extras"]["soft_signal"], "high_path_risk")

    def test_no_risk_signals_yield_none(self) -> None:
        predict = {"conflicting_factors": [], "path_risk": "low"}
        self.assertEqual(_section(predict)["extras"]["soft_signal"], "none")

    def test_unrelated_conflicting_factors_do_not_trigger_peer_weaken(self) -> None:
        predict = {
            "conflicting_factors": ["research_weakens_bullish"],
            "path_risk": "medium",
        }
        # research_weakens_bullish is not the peer signal we key on.
        # path_risk is medium, not high. → soft_signal stays "none".
        self.assertEqual(_section(predict)["extras"]["soft_signal"], "none")


# ── 5. validator stays green ──────────────────────────────────────────────

class ExclusionContractValidityTests(unittest.TestCase):
    def test_payload_validates_with_empty_predict_result(self) -> None:
        payload = adapt_projection_output(
            scan_result=None, research_result=None, predict_result=None
        )
        self.assertEqual(validate_projection_output(payload), [])

    def test_payload_validates_under_risk_input(self) -> None:
        payload = adapt_projection_output(
            scan_result=None,
            research_result=None,
            predict_result={
                "conflicting_factors": ["peer_confirmation=weaken"],
                "path_risk": "high",
                "peer_path_risk_adjustment": {
                    "risk_direction": "higher",
                    "reasons": ["peer_layer_weaken"],
                },
            },
        )
        self.assertEqual(validate_projection_output(payload), [])


# ── 6. live run_predict round-trip ────────────────────────────────────────

class ExclusionRunPredictRoundTripTests(unittest.TestCase):
    """A real run_predict call must produce extras that match the live
    conflicting_factors / path_risk on its predict_result."""

    def _scan(self) -> dict:
        return {
            "symbol": "AVGO",
            "scan_timestamp": "2026-04-20T00:00:00",
            "scan_bias": "bullish",
            "scan_confidence": "medium",
            "avgo_gap_state": "gap_up",
            "avgo_intraday_state": "high_go",
            "avgo_volume_state": "expanding",
            "avgo_price_state": "bullish",
            "avgo_recent_20": [
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
            ],
            "relative_strength_summary": {
                "vs_nvda": "weaker",
                "vs_soxx": "weaker",
                "vs_qqq": "weaker",
            },
            "relative_strength_same_day_summary": {
                "vs_nvda": "weaker",
                "vs_soxx": "weaker",
                "vs_qqq": "weaker",
            },
        }

    def test_extras_mirrors_live_predict_result(self) -> None:
        scan = self._scan()
        predict = run_predict(scan, research_result=None, symbol="AVGO")
        payload = adapt_projection_output(
            scan_result=scan, research_result=None, predict_result=predict
        )
        section = payload["exclusion_system"]

        # Required fields must still be the stub even with all peers weaker.
        self.assertEqual(section["exclusion_level"], "none")
        self.assertIs(section["forced_exclusion"], False)
        self.assertIs(section["anti_false_exclusion_triggered"], False)

        # Extras must reflect predict_result one-for-one.
        extras = section["extras"]
        self.assertEqual(
            extras["conflicting_factors"], predict["conflicting_factors"]
        )
        self.assertEqual(extras["path_risk_level"], predict["path_risk"])
        self.assertEqual(
            extras["peer_path_risk_direction"],
            predict["peer_path_risk_adjustment"]["risk_direction"],
        )
        # All peers weaker → peer_confirmation=weaken in conflicting_factors
        # → soft_signal = peer_weaken.
        self.assertIn("peer_confirmation=weaken", extras["conflicting_factors"])
        self.assertEqual(extras["soft_signal"], "peer_weaken")


if __name__ == "__main__":
    unittest.main()
