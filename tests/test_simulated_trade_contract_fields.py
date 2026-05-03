"""Step 2D-2: contract 07 simulated_trade trading-decision fields stay
pinned at safe stubs, but extras surfaces trade-relevant observation
signals already produced upstream.

This file does NOT test a trading engine — there is none, and the project
strategy forbids one. It only checks that:
  1. the 6 trading-decision fields stay pinned (``trade_action`` ==
     ``"no_trade"`` / ``trade_direction`` == ``"none"`` / 3 condition
     strings empty / ``suggested_position_size`` == ``"0%"``),
  2. ``no_trade_reason`` is the static honest message that points
     consumers at sections 06 / 05,
  3. an additive ``extras`` sub-dict reflects the live signals on
     ``predict_result`` (final_projection.final_direction /
     final_five_state / probability_bucket / final_confidence /
     path_risk / conflicting_factors / key_price_levels), and
  4. ``trade_engine_enabled`` is the constant ``False``.

If a future step ever wires a real trading engine, the pin-stays
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


_REQUIRED_07_FIELDS: tuple[str, ...] = (
    "trade_action",
    "trade_direction",
    "entry_condition",
    "stop_loss_condition",
    "take_profit_condition",
    "suggested_position_size",
    "no_trade_reason",
)

_EXTRAS_KEYS: tuple[str, ...] = (
    "final_direction",
    "final_five_state",
    "probability_bucket",
    "confidence_level",
    "total_confidence",
    "path_risk_level",
    "soft_signal",
    "has_key_price_levels",
    "trade_engine_enabled",
)


def _section(predict_result: dict | None) -> dict:
    payload = adapt_projection_output(
        scan_result=None, research_result=None, predict_result=predict_result
    )
    return payload["simulated_trade"]


# ── 1. trading-decision fields stay pinned ─────────────────────────────────

class SimulatedTradeDecisionFieldsRemainPinnedTests(unittest.TestCase):
    def test_required_fields_present_with_empty_predict_result(self) -> None:
        section = _section(None)
        for field in _REQUIRED_07_FIELDS:
            self.assertIn(field, section)

    def test_decision_fields_are_safe_stubs_with_empty_predict_result(self) -> None:
        section = _section(None)
        self.assertEqual(section["trade_action"], "no_trade")
        self.assertEqual(section["trade_direction"], "none")
        self.assertEqual(section["entry_condition"], "")
        self.assertEqual(section["stop_loss_condition"], "")
        self.assertEqual(section["take_profit_condition"], "")
        self.assertEqual(section["suggested_position_size"], "0%")

    def test_decision_fields_unchanged_under_strong_bullish_input(self) -> None:
        # Even when the upstream payload is decisively bullish + high
        # confidence + supportive risk, the 6 decision fields must NOT
        # move — Step 2D-2 only surfaces signals into extras.
        predict = {
            "final_confidence": "high",
            "prediction_summary": "<placeholder>",
            "final_projection": {
                "final_direction": "偏多",
                "final_five_state": "小涨",
                "probability_bucket": "≥70%",
                "key_price_levels": {"support": 100.0, "resistance": 110.0},
            },
            "path_risk": "low",
            "conflicting_factors": [],
        }
        section = _section(predict)
        self.assertEqual(section["trade_action"], "no_trade")
        self.assertEqual(section["trade_direction"], "none")
        self.assertEqual(section["entry_condition"], "")
        self.assertEqual(section["stop_loss_condition"], "")
        self.assertEqual(section["take_profit_condition"], "")
        self.assertEqual(section["suggested_position_size"], "0%")

    def test_decision_fields_unchanged_under_high_risk_input(self) -> None:
        # Symmetric: under elevated path_risk + peer_weaken, the 6
        # decision fields still must not move (no auto-close suggestion).
        predict = {
            "final_confidence": "low",
            "prediction_summary": "<placeholder>",
            "final_projection": {"final_direction": "偏空"},
            "path_risk": "high",
            "conflicting_factors": [
                "peer_confirmation=weaken",
                "peer_path_risk=high",
            ],
        }
        section = _section(predict)
        self.assertEqual(section["trade_action"], "no_trade")
        self.assertEqual(section["trade_direction"], "none")
        self.assertEqual(section["entry_condition"], "")
        self.assertEqual(section["stop_loss_condition"], "")
        self.assertEqual(section["take_profit_condition"], "")
        self.assertEqual(section["suggested_position_size"], "0%")


# ── 2. no_trade_reason is the static honest message ───────────────────────

class SimulatedTradeNoTradeReasonTests(unittest.TestCase):
    def test_no_trade_reason_is_static_honest_string(self) -> None:
        reason = _section(None)["no_trade_reason"]
        self.assertIsInstance(reason, str)
        self.assertGreater(len(reason), 0)
        # Honest signal that the engine is not active.
        self.assertIn("not enabled", reason)
        # Points consumer at the real decision-signal sections.
        self.assertIn("final_projection", reason)
        self.assertIn("confidence_system", reason)

    def test_no_trade_reason_is_invariant_to_predict_input(self) -> None:
        baseline = _section(None)["no_trade_reason"]
        bullish = _section({
            "final_confidence": "high",
            "final_projection": {"final_direction": "偏多"},
        })["no_trade_reason"]
        bearish = _section({
            "final_confidence": "low",
            "final_projection": {"final_direction": "偏空"},
            "path_risk": "high",
            "conflicting_factors": ["peer_confirmation=weaken"],
        })["no_trade_reason"]
        self.assertEqual(baseline, bullish)
        self.assertEqual(baseline, bearish)


# ── 3. extras presence & shape ─────────────────────────────────────────────

class SimulatedTradeExtrasShapeTests(unittest.TestCase):
    def test_extras_present_even_when_predict_result_is_none(self) -> None:
        section = _section(None)
        self.assertIn("extras", section)
        self.assertIsInstance(section["extras"], dict)
        for key in _EXTRAS_KEYS:
            self.assertIn(key, section["extras"], f"missing extras.{key}")

    def test_extras_default_values_with_empty_predict_result(self) -> None:
        extras = _section(None)["extras"]
        self.assertEqual(extras["final_direction"], "中性")
        self.assertEqual(extras["final_five_state"], "震荡")
        self.assertEqual(extras["probability_bucket"], "unknown")
        self.assertEqual(extras["confidence_level"], "low")  # _normalize_confidence default
        self.assertEqual(extras["total_confidence"], 0.25)   # low → 0.25
        self.assertEqual(extras["path_risk_level"], "unknown")
        self.assertEqual(extras["soft_signal"], "none")
        self.assertIs(extras["has_key_price_levels"], False)
        self.assertIs(extras["trade_engine_enabled"], False)


# ── 4. extras values reflect predict_result ─────────────────────────────────

class SimulatedTradeExtrasValueMappingTests(unittest.TestCase):
    def test_final_direction_passes_through(self) -> None:
        for direction in ("偏多", "偏空", "中性"):
            with self.subTest(direction=direction):
                extras = _section({
                    "final_projection": {"final_direction": direction},
                })["extras"]
                self.assertEqual(extras["final_direction"], direction)

    def test_invalid_final_direction_falls_back_to_neutral(self) -> None:
        extras = _section({
            "final_projection": {"final_direction": "totally-bogus"},
        })["extras"]
        self.assertEqual(extras["final_direction"], "中性")

    def test_final_five_state_passes_through(self) -> None:
        for state in ("大涨", "小涨", "震荡", "小跌", "大跌"):
            with self.subTest(state=state):
                extras = _section({
                    "final_projection": {"final_five_state": state},
                })["extras"]
                self.assertEqual(extras["final_five_state"], state)

    def test_invalid_final_five_state_falls_back_to_zhendang(self) -> None:
        extras = _section({
            "final_projection": {"final_five_state": "不存在"},
        })["extras"]
        self.assertEqual(extras["final_five_state"], "震荡")

    def test_probability_bucket_passes_through(self) -> None:
        for bucket in ("≥70%", "55–70%", "45–55%", "30–45%", "≤30%"):
            with self.subTest(bucket=bucket):
                extras = _section({
                    "final_projection": {"probability_bucket": bucket},
                })["extras"]
                self.assertEqual(extras["probability_bucket"], bucket)

    def test_invalid_probability_bucket_becomes_unknown(self) -> None:
        extras = _section({
            "final_projection": {"probability_bucket": "200%"},
        })["extras"]
        self.assertEqual(extras["probability_bucket"], "unknown")

    def test_confidence_level_and_total_confidence_pair(self) -> None:
        cases = {"high": 0.75, "medium": 0.50, "low": 0.25}
        for level, expected_total in cases.items():
            with self.subTest(level=level):
                extras = _section({"final_confidence": level})["extras"]
                self.assertEqual(extras["confidence_level"], level)
                self.assertEqual(extras["total_confidence"], expected_total)

    def test_path_risk_level_passes_through(self) -> None:
        for level in ("low", "medium", "high"):
            with self.subTest(level=level):
                extras = _section({"path_risk": level})["extras"]
                self.assertEqual(extras["path_risk_level"], level)

    def test_invalid_path_risk_level_becomes_unknown(self) -> None:
        extras = _section({"path_risk": "extreme"})["extras"]
        self.assertEqual(extras["path_risk_level"], "unknown")

    def test_has_key_price_levels_true_only_for_non_empty_dict(self) -> None:
        empty = _section({"final_projection": {"key_price_levels": {}}})["extras"]
        self.assertIs(empty["has_key_price_levels"], False)
        non_empty = _section({
            "final_projection": {"key_price_levels": {"support": 100.0}},
        })["extras"]
        self.assertIs(non_empty["has_key_price_levels"], True)

    def test_has_key_price_levels_false_for_non_dict(self) -> None:
        # Some legacy callers initialize as []; adapter must treat as False.
        extras = _section({"final_projection": {"key_price_levels": []}})["extras"]
        self.assertIs(extras["has_key_price_levels"], False)

    def test_trade_engine_enabled_is_constant_false(self) -> None:
        # No matter what predict carries, the engine flag is False.
        for predict in (
            None,
            {"final_confidence": "high"},
            {
                "final_confidence": "high",
                "final_projection": {"final_direction": "偏多"},
                "path_risk": "low",
            },
        ):
            with self.subTest(predict=predict):
                self.assertIs(_section(predict)["extras"]["trade_engine_enabled"], False)


# ── 5. soft_signal heuristic (re-derived, NOT read from sibling sections) ─

class SimulatedTradeSoftSignalTests(unittest.TestCase):
    def test_peer_weaken_in_conflicting_factors_yields_peer_weaken(self) -> None:
        predict = {
            "conflicting_factors": ["peer_confirmation=weaken"],
            "path_risk": "low",
        }
        self.assertEqual(_section(predict)["extras"]["soft_signal"], "peer_weaken")

    def test_peer_weaken_takes_priority_over_high_path_risk(self) -> None:
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
        self.assertEqual(_section(predict)["extras"]["soft_signal"], "none")


# ── 6. validator stays green ──────────────────────────────────────────────

class SimulatedTradeContractValidityTests(unittest.TestCase):
    def test_payload_validates_with_empty_predict_result(self) -> None:
        payload = adapt_projection_output(
            scan_result=None, research_result=None, predict_result=None
        )
        self.assertEqual(validate_projection_output(payload), [])

    def test_payload_validates_under_strong_signals(self) -> None:
        predict = {
            "final_confidence": "high",
            "prediction_summary": "<placeholder>",
            "final_projection": {
                "final_direction": "偏多",
                "final_five_state": "小涨",
                "probability_bucket": "≥70%",
                "key_price_levels": {"support": 100.0, "resistance": 110.0},
            },
            "path_risk": "high",
            "conflicting_factors": ["peer_confirmation=weaken"],
        }
        payload = adapt_projection_output(
            scan_result=None, research_result=None, predict_result=predict
        )
        self.assertEqual(validate_projection_output(payload), [])


# ── 7. live run_predict round-trip ────────────────────────────────────────

class SimulatedTradeRunPredictRoundTripTests(unittest.TestCase):
    """A real run_predict call must yield extras that mirror the live
    final_projection / path_risk / conflicting_factors on its
    predict_result, while the 6 decision fields stay pinned."""

    def _scan(self, peer_weaker: bool) -> dict:
        rs = {"vs_nvda": "weaker" if peer_weaker else "stronger",
              "vs_soxx": "weaker" if peer_weaker else "stronger",
              "vs_qqq":  "weaker" if peer_weaker else "stronger"}
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
            "relative_strength_summary": dict(rs),
            "relative_strength_same_day_summary": dict(rs),
        }

    def _payload(self, peer_weaker: bool) -> tuple[dict, dict]:
        scan = self._scan(peer_weaker)
        predict = run_predict(scan, research_result=None, symbol="AVGO")
        payload = adapt_projection_output(
            scan_result=scan, research_result=None, predict_result=predict
        )
        return predict, payload

    def test_decision_fields_pinned_under_all_peers_stronger(self) -> None:
        predict, payload = self._payload(peer_weaker=False)
        st = payload["simulated_trade"]
        self.assertEqual(st["trade_action"], "no_trade")
        self.assertEqual(st["trade_direction"], "none")
        self.assertEqual(st["suggested_position_size"], "0%")
        # extras should mirror predict's final_projection.
        self.assertEqual(
            st["extras"]["final_direction"],
            predict["final_projection"]["final_direction"],
        )
        self.assertEqual(
            st["extras"]["final_five_state"],
            predict["final_projection"]["final_five_state"],
        )
        self.assertEqual(
            st["extras"]["probability_bucket"],
            predict["final_projection"]["probability_bucket"],
        )
        # All peers stronger → no peer_weaken signal.
        self.assertEqual(st["extras"]["soft_signal"], "none")
        # Engine flag is constant False regardless.
        self.assertIs(st["extras"]["trade_engine_enabled"], False)

    def test_decision_fields_pinned_under_all_peers_weaker(self) -> None:
        predict, payload = self._payload(peer_weaker=True)
        st = payload["simulated_trade"]
        self.assertEqual(st["trade_action"], "no_trade")
        self.assertEqual(st["trade_direction"], "none")
        self.assertEqual(st["suggested_position_size"], "0%")
        # peer_confirmation=weaken should be in conflicting_factors → soft_signal triggers.
        self.assertIn(
            "peer_confirmation=weaken", predict["conflicting_factors"]
        )
        self.assertEqual(st["extras"]["soft_signal"], "peer_weaken")
        self.assertEqual(st["extras"]["path_risk_level"], predict["path_risk"])
        self.assertIs(st["extras"]["trade_engine_enabled"], False)


if __name__ == "__main__":
    unittest.main()
