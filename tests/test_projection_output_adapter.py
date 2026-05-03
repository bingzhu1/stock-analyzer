"""Tests for services/projection_output_adapter.py (Step 1C).

Adapter takes legacy scan_result / research_result / predict_result and
emits the 1A Projection Output Contract dict. All payloads use placeholder
values; no real market data.
"""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.projection_output_adapter import adapt_projection_output
from services.projection_output_contract import (
    CONTRACT_SECTIONS,
    validate_projection_output,
)
from tests.fixtures.projection_output_samples import (
    realistic_predict_result,
    realistic_scan_result,
    unavailable_predict_result,
)


def _minimal_scan_result() -> dict:
    return {
        "symbol": "AVGO",
        "scan_timestamp": "2026-04-09T00:00:00",
        "scan_phase": "daily",
        "scan_phase_note": "<placeholder note>",
        "avgo_price_state": "整理",
        "avgo_recent_20": [
            {"Date": "2026-04-08", "Close": 100.0, "Volume": 1_000_000},
            {"Date": "2026-04-09", "Close": 101.0, "Volume": 1_200_000},
        ],
        "relative_strength_summary": {
            "NVDA": {"relative_strength": "stronger"},
            "SOXX": {"relative_strength": "neutral"},
            "QQQ": {"relative_strength": "stronger"},
        },
    }


def _minimal_predict_result() -> dict:
    return {
        "symbol": "AVGO",
        "final_bias": "bullish",
        "final_confidence": "high",
        "pred_open": "高开",
        "pred_path": "高开高走",
        "pred_close": "收涨",
        "prediction_summary": "<placeholder summary>",
        "supporting_factors": ["evidence-1", "evidence-2"],
        "primary_projection": {
            "final_bias": "bullish",
            "final_confidence": "high",
        },
        "peer_adjustment": {
            "adjustment_direction": "reinforce",
            "confirm_count": 2,
            "oppose_count": 0,
            "adjusted_bias": "bullish",
            "notes": "<placeholder peer note>",
        },
    }


class AdapterContractComplianceTests(unittest.TestCase):
    def test_empty_inputs_produce_valid_contract_payload(self) -> None:
        payload = adapt_projection_output(
            scan_result=None, research_result=None, predict_result=None
        )
        self.assertEqual(set(payload.keys()), set(CONTRACT_SECTIONS))
        self.assertEqual(validate_projection_output(payload), [])

    def test_full_inputs_produce_valid_contract_payload(self) -> None:
        payload = adapt_projection_output(
            scan_result=_minimal_scan_result(),
            research_result={"research_bias_adjustment": "confirms_bias"},
            predict_result=_minimal_predict_result(),
        )
        self.assertEqual(validate_projection_output(payload), [])

    def test_payload_keys_are_exactly_the_eight_sections(self) -> None:
        payload = adapt_projection_output(
            scan_result=None, research_result=None, predict_result=None
        )
        self.assertEqual(tuple(payload.keys()), CONTRACT_SECTIONS)


class CurrentStructureMappingTests(unittest.TestCase):
    def test_minimal_scan_result_maps_into_current_structure(self) -> None:
        payload = adapt_projection_output(
            scan_result=_minimal_scan_result(),
            research_result=None,
            predict_result=None,
        )
        cs = payload["current_structure"]
        self.assertEqual(cs["symbol"], "AVGO")
        self.assertEqual(cs["analysis_date"], "2026-04-09")
        self.assertEqual(cs["data_window_days"], 15)
        # Latest row: Close=101.0, Volume=1_200_000 (2nd row)
        self.assertEqual(cs["current_price"], 101.0)
        self.assertEqual(cs["previous_close"], 100.0)
        self.assertEqual(cs["volume"], 1_200_000)
        self.assertEqual(cs["turnover"], 101.0 * 1_200_000)
        self.assertEqual(cs["structure_label"], "整理")

    def test_missing_scan_falls_back_to_unknown_not_fake_market_data(self) -> None:
        payload = adapt_projection_output(
            scan_result=None, research_result=None, predict_result=None
        )
        cs = payload["current_structure"]
        self.assertEqual(cs["symbol"], "AVGO")
        self.assertEqual(cs["analysis_date"], "unknown")
        self.assertEqual(cs["prediction_for_date"], "unknown")
        self.assertEqual(cs["current_price"], 0.0)
        self.assertEqual(cs["previous_close"], 0.0)
        self.assertEqual(cs["volume"], 0)
        self.assertEqual(cs["turnover"], 0.0)
        self.assertEqual(cs["structure_label"], "unknown")
        # No fabricated price > 0 anywhere.
        self.assertNotIn(cs["current_price"], (100.0, 101.0))


class FinalProjectionMappingTests(unittest.TestCase):
    def test_minimal_predict_result_maps_into_final_projection(self) -> None:
        payload = adapt_projection_output(
            scan_result=None,
            research_result=None,
            predict_result=_minimal_predict_result(),
        )
        fp = payload["final_projection"]
        self.assertEqual(fp["final_direction"], "偏多")
        self.assertEqual(fp["final_open_projection"], "高开")
        self.assertEqual(fp["final_intraday_path"], "高走")
        self.assertEqual(fp["final_close_projection"], "收涨")
        self.assertEqual(fp["final_five_state"], "小涨")
        self.assertEqual(fp["probability_bucket"], "≥70%")
        self.assertEqual(fp["key_price_levels"], {})
        self.assertEqual(fp["final_one_sentence"], "<placeholder summary>")

    def test_close_label_pingshou_renamed_to_shouping(self) -> None:
        # legacy predict.py emits 平收, contract spec expects 收平
        predict = _minimal_predict_result()
        predict["pred_close"] = "平收"
        payload = adapt_projection_output(
            scan_result=None, research_result=None, predict_result=predict
        )
        self.assertEqual(payload["final_projection"]["final_close_projection"], "收平")
        self.assertEqual(payload["review_payload"]["predicted_close_type"], "收平")

    def test_unknown_bias_falls_back_to_neutral(self) -> None:
        payload = adapt_projection_output(
            scan_result=None,
            research_result=None,
            predict_result={"final_bias": "??", "final_confidence": "high"},
        )
        self.assertEqual(payload["final_projection"]["final_direction"], "中性")
        self.assertEqual(payload["final_projection"]["final_five_state"], "震荡")

    def test_self_published_final_projection_takes_priority(self) -> None:
        """Step 2B-4: when predict_result["final_projection"] self-publishes
        contract 06 fields, the adapter must use those values verbatim and
        ignore the top-level legacy fields."""
        # Top-level fields disagree with self-published on every value.
        # Self-published must win.
        predict = {
            "final_bias": "bullish",
            "final_confidence": "high",
            "pred_open": "高开",
            "pred_path": "高开高走",
            "pred_close": "收涨",
            "prediction_summary": "<top-level summary, should be ignored>",
            "final_projection": {
                "final_direction": "偏空",
                "final_open_projection": "低开",
                "final_intraday_path": "低走",
                "final_close_projection": "收跌",
                "final_five_state": "小跌",
                "probability_bucket": "30–45%",
                "key_price_levels": {"support": 100.0, "resistance": 110.0},
                "final_one_sentence": "self-published one-line summary",
            },
        }
        fp = adapt_projection_output(
            scan_result=None, research_result=None, predict_result=predict
        )["final_projection"]
        self.assertEqual(fp["final_direction"], "偏空")
        self.assertEqual(fp["final_open_projection"], "低开")
        self.assertEqual(fp["final_intraday_path"], "低走")
        self.assertEqual(fp["final_close_projection"], "收跌")
        self.assertEqual(fp["final_five_state"], "小跌")
        self.assertEqual(fp["probability_bucket"], "30–45%")
        self.assertEqual(fp["key_price_levels"], {"support": 100.0, "resistance": 110.0})
        self.assertEqual(fp["final_one_sentence"], "self-published one-line summary")

    def test_legacy_predict_without_final_projection_still_uses_fallback(self) -> None:
        """Backwards compat: predict_result missing the final_projection
        sub-dict must still produce a contract-valid section."""
        legacy = _minimal_predict_result()
        # Sanity: the legacy fixture deliberately lacks final_projection.
        self.assertNotIn("final_projection", legacy)

        fp = adapt_projection_output(
            scan_result=None, research_result=None, predict_result=legacy
        )["final_projection"]
        # Must match the legacy expectations from
        # ``test_minimal_predict_result_maps_into_final_projection``.
        self.assertEqual(fp["final_direction"], "偏多")
        self.assertEqual(fp["final_open_projection"], "高开")
        self.assertEqual(fp["final_intraday_path"], "高走")
        self.assertEqual(fp["final_close_projection"], "收涨")
        self.assertEqual(fp["final_five_state"], "小涨")
        self.assertEqual(fp["probability_bucket"], "≥70%")
        self.assertEqual(fp["key_price_levels"], {})

    def test_self_published_invalid_enum_value_falls_back_for_final(self) -> None:
        """Defensive: bogus self-published enum values must not corrupt the
        contract output; adapter falls back to legacy translation."""
        predict = {
            "final_bias": "bullish",
            "final_confidence": "medium",
            "pred_open": "高开",
            "pred_path": "高开高走",
            "pred_close": "收涨",
            "prediction_summary": "fallback sentence",
            "final_projection": {
                "final_direction": "totally-bogus",
                "final_five_state": "不存在的五态",
                "probability_bucket": "200%",
                "key_price_levels": "not-a-dict",  # also wrong type
                "final_one_sentence": 42,  # wrong type
            },
        }
        fp = adapt_projection_output(
            scan_result=None, research_result=None, predict_result=predict
        )["final_projection"]
        self.assertIn(fp["final_direction"], {"偏多", "偏空", "中性"})
        self.assertNotEqual(fp["final_direction"], "totally-bogus")
        self.assertIn(fp["final_five_state"], {"大涨", "小涨", "震荡", "小跌", "大跌"})
        self.assertIn(
            fp["probability_bucket"],
            {"≥70%", "55–70%", "45–55%", "30–45%", "≤30%"},
        )
        self.assertEqual(fp["key_price_levels"], {})
        self.assertEqual(fp["final_one_sentence"], "fallback sentence")


class PeerConfirmationMappingTests(unittest.TestCase):
    def test_relative_strength_maps_to_peer_signals(self) -> None:
        payload = adapt_projection_output(
            scan_result=_minimal_scan_result(),
            research_result=None,
            predict_result=_minimal_predict_result(),
        )
        peer = payload["peer_confirmation_adjustment"]
        self.assertEqual(peer["peer_symbols"], ["NVDA", "SOXX", "QQQ"])
        self.assertEqual(peer["nvda_signal"], "reinforce")
        self.assertEqual(peer["soxx_signal"], "neutral")
        self.assertEqual(peer["qqq_signal"], "reinforce")
        self.assertEqual(peer["peer_alignment"], "mixed")  # 2 confirm + 0 oppose
        self.assertEqual(peer["peer_adjustment"], "upgrade")
        self.assertEqual(peer["adjusted_direction"], "偏多")

    def test_missing_peer_data_falls_back_to_unknown_and_insufficient(self) -> None:
        payload = adapt_projection_output(
            scan_result=None, research_result=None, predict_result=None
        )
        peer = payload["peer_confirmation_adjustment"]
        self.assertEqual(peer["nvda_signal"], "unknown")
        self.assertEqual(peer["soxx_signal"], "unknown")
        self.assertEqual(peer["qqq_signal"], "unknown")
        self.assertEqual(peer["peer_alignment"], "insufficient")
        self.assertEqual(peer["peer_adjustment"], "hold")

    def test_self_published_peer_fields_take_priority_over_scan(self) -> None:
        """Step 2B-3: when peer_adjustment self-publishes contract 03 fields,
        the adapter must use those values verbatim, ignoring scan-derived
        translation."""
        # scan says all peers are stronger → legacy fallback would emit
        # nvda_signal=reinforce / soxx_signal=reinforce / qqq_signal=reinforce
        # peer_alignment=all_reinforce (with confirm_count=3, oppose_count=0).
        # The self-published fields below disagree on every value; the adapter
        # must trust the peer_adjustment dict.
        scan = {
            "symbol": "AVGO",
            "scan_timestamp": "2026-04-09T00:00:00",
            "relative_strength_summary": {
                "NVDA": {"relative_strength": "stronger"},
                "SOXX": {"relative_strength": "stronger"},
                "QQQ": {"relative_strength": "stronger"},
            },
        }
        predict = {
            "final_bias": "bullish",
            "final_confidence": "high",
            "peer_adjustment": {
                "confirm_count": 3,
                "oppose_count": 0,
                "adjustment_direction": "reinforce",
                "adjusted_bias": "bullish",
                "notes": "<legacy notes ignored>",
                # self-published contract 03 fields:
                "peer_symbols": ["NVDA", "SOXX", "QQQ"],
                "nvda_signal": "weaken",
                "soxx_signal": "neutral",
                "qqq_signal": "unknown",
                "peer_alignment": "mixed",
                "peer_adjustment": "downgrade",
                "adjusted_direction": "偏空",
                "adjustment_reason": "self-published reason",
            },
        }
        peer = adapt_projection_output(
            scan_result=scan, research_result=None, predict_result=predict
        )["peer_confirmation_adjustment"]
        self.assertEqual(peer["nvda_signal"], "weaken")
        self.assertEqual(peer["soxx_signal"], "neutral")
        self.assertEqual(peer["qqq_signal"], "unknown")
        self.assertEqual(peer["peer_alignment"], "mixed")
        self.assertEqual(peer["peer_adjustment"], "downgrade")
        self.assertEqual(peer["adjusted_direction"], "偏空")
        self.assertEqual(peer["adjustment_reason"], "self-published reason")

    def test_legacy_peer_payload_without_contract_fields_still_uses_fallback(self) -> None:
        """Backwards compat: a peer_adjustment dict missing the new contract
        03 fields must still produce a contract-valid section by falling
        back to scan-derived translation (Step 1C behavior)."""
        scan = _minimal_scan_result()
        legacy_predict = _minimal_predict_result()
        # Sanity: the legacy fixture deliberately lacks the new fields.
        for field in ("nvda_signal", "peer_alignment", "adjusted_direction"):
            self.assertNotIn(field, legacy_predict["peer_adjustment"])

        peer = adapt_projection_output(
            scan_result=scan, research_result=None, predict_result=legacy_predict
        )["peer_confirmation_adjustment"]
        # Must match the legacy expectations from
        # ``test_relative_strength_maps_to_peer_signals``.
        self.assertEqual(peer["nvda_signal"], "reinforce")
        self.assertEqual(peer["soxx_signal"], "neutral")
        self.assertEqual(peer["qqq_signal"], "reinforce")
        self.assertEqual(peer["peer_adjustment"], "upgrade")
        self.assertEqual(peer["adjusted_direction"], "偏多")

    def test_self_published_invalid_enum_value_falls_back_to_legacy(self) -> None:
        """Defensive: if peer_adjustment publishes a non-enum value, the
        adapter must ignore it and fall back rather than corrupt the
        contract output."""
        scan = _minimal_scan_result()
        predict = _minimal_predict_result()
        predict["peer_adjustment"]["nvda_signal"] = "totally-bogus"
        predict["peer_adjustment"]["peer_alignment"] = "not-an-alignment"

        peer = adapt_projection_output(
            scan_result=scan, research_result=None, predict_result=predict
        )["peer_confirmation_adjustment"]
        # Bogus values must be replaced by legacy fallback (validator-clean).
        self.assertIn(peer["nvda_signal"], {"reinforce", "weaken", "neutral", "unknown"})
        self.assertIn(
            peer["peer_alignment"],
            {"all_reinforce", "mixed", "all_weaken", "insufficient"},
        )
        self.assertNotEqual(peer["nvda_signal"], "totally-bogus")
        self.assertNotEqual(peer["peer_alignment"], "not-an-alignment")


class ExclusionAndConfidenceMappingTests(unittest.TestCase):
    def test_exclusion_system_defaults_to_none_with_empty_lists(self) -> None:
        payload = adapt_projection_output(
            scan_result=None, research_result=None, predict_result=None
        )
        ex = payload["exclusion_system"]
        self.assertEqual(ex["exclusion_level"], "none")
        self.assertEqual(ex["exclusion_sources"], [])
        self.assertEqual(ex["exclusion_reasons"], [])
        self.assertFalse(ex["forced_exclusion"])
        self.assertFalse(ex["anti_false_exclusion_triggered"])

    def test_exclusion_system_extras_surfaces_predict_risk_signals(self) -> None:
        """Step 2C-2: required fields must stay the stub, but extras must
        reflect predict_result's conflicting_factors / path_risk /
        peer_path_risk_adjustment one-for-one."""
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
        ex = adapt_projection_output(
            scan_result=None, research_result=None, predict_result=predict
        )["exclusion_system"]

        # Required fields untouched.
        self.assertEqual(ex["exclusion_level"], "none")
        self.assertEqual(ex["exclusion_sources"], [])
        self.assertEqual(ex["exclusion_reasons"], [])
        self.assertFalse(ex["forced_exclusion"])
        self.assertFalse(ex["anti_false_exclusion_triggered"])

        # extras populated.
        extras = ex["extras"]
        self.assertEqual(extras["conflicting_factors_count"], 2)
        self.assertEqual(
            extras["conflicting_factors"],
            ["peer_confirmation=weaken", "peer_path_risk=high"],
        )
        self.assertEqual(extras["path_risk_level"], "high")
        self.assertEqual(extras["peer_path_risk_direction"], "higher")
        self.assertEqual(extras["peer_path_risk_reasons"], ["peer_layer_weaken"])
        self.assertEqual(extras["soft_signal"], "peer_weaken")
        # Validator must still pass.
        payload = adapt_projection_output(
            scan_result=None, research_result=None, predict_result=predict
        )
        self.assertEqual(validate_projection_output(payload), [])

    def test_confidence_system_event_score_is_null_and_total_matches_level(self) -> None:
        payload = adapt_projection_output(
            scan_result=None,
            research_result=None,
            predict_result=_minimal_predict_result(),
        )
        cs = payload["confidence_system"]
        self.assertIsNone(cs["event_score"])
        self.assertEqual(cs["confidence_level"], "high")
        self.assertEqual(cs["total_confidence"], 0.75)


class SimulatedTradeDefaultTests(unittest.TestCase):
    def test_simulated_trade_defaults_to_no_trade(self) -> None:
        payload = adapt_projection_output(
            scan_result=_minimal_scan_result(),
            research_result=None,
            predict_result=_minimal_predict_result(),
        )
        st = payload["simulated_trade"]
        self.assertEqual(st["trade_action"], "no_trade")
        self.assertEqual(st["trade_direction"], "none")
        self.assertEqual(st["suggested_position_size"], "0%")
        self.assertIsInstance(st["no_trade_reason"], str)
        self.assertTrue(st["no_trade_reason"])  # non-empty


class ReviewPayloadTests(unittest.TestCase):
    def test_review_payload_mirrors_final_projection_labels(self) -> None:
        payload = adapt_projection_output(
            scan_result=None,
            research_result=None,
            predict_result=_minimal_predict_result(),
        )
        rp = payload["review_payload"]
        fp = payload["final_projection"]
        self.assertEqual(rp["predicted_open_type"], fp["final_open_projection"])
        self.assertEqual(rp["predicted_path_type"], fp["final_intraday_path"])
        self.assertEqual(rp["predicted_close_type"], fp["final_close_projection"])
        self.assertEqual(rp["predicted_five_state"], fp["final_five_state"])
        self.assertEqual(rp["predicted_confidence"], payload["confidence_system"]["confidence_level"])
        self.assertEqual(rp["prediction_id"], "")
        self.assertIn("predicted_open_type", rp["review_ready_fields"])


class AdapterPurityTests(unittest.TestCase):
    def test_adapter_does_not_mutate_inputs(self) -> None:
        scan = _minimal_scan_result()
        predict = _minimal_predict_result()
        research = {"research_bias_adjustment": "confirms_bias"}

        scan_snapshot = copy.deepcopy(scan)
        predict_snapshot = copy.deepcopy(predict)
        research_snapshot = copy.deepcopy(research)

        adapt_projection_output(
            scan_result=scan, research_result=research, predict_result=predict
        )

        self.assertEqual(scan, scan_snapshot)
        self.assertEqual(predict, predict_snapshot)
        self.assertEqual(research, research_snapshot)

    def test_adapter_does_not_raise_on_pathological_inputs(self) -> None:
        # Garbage inputs (non-dict) must still yield a valid payload.
        for bad in (None, [], "string", 42, 3.14, ()):
            with self.subTest(bad=bad):
                payload = adapt_projection_output(
                    scan_result=bad,  # type: ignore[arg-type]
                    research_result=bad,  # type: ignore[arg-type]
                    predict_result=bad,  # type: ignore[arg-type]
                )
                self.assertEqual(validate_projection_output(payload), [])


class RealShapeCompatibilityTests(unittest.TestCase):
    """Lock the adapter against the actual scanner.run_scan / predict.run_predict
    output shapes (Step 1D)."""

    def test_realistic_full_inputs_validate_clean(self) -> None:
        payload = adapt_projection_output(
            scan_result=realistic_scan_result(),
            research_result={"research_bias_adjustment": "confirms_bias"},
            predict_result=realistic_predict_result(),
        )
        self.assertEqual(validate_projection_output(payload), [])

    def test_unavailable_predict_result_still_validates(self) -> None:
        payload = adapt_projection_output(
            scan_result=None,
            research_result=None,
            predict_result=unavailable_predict_result(),
        )
        self.assertEqual(validate_projection_output(payload), [])
        # 'unavailable' bias must collapse to 中性, not be passed through.
        self.assertEqual(payload["final_projection"]["final_direction"], "中性")
        self.assertEqual(payload["avgo_primary_projection"]["primary_direction"], "中性")
        # Missing pred_* must collapse to 平开 / 震荡 / 收平 (contract-valid neutrals).
        self.assertEqual(payload["final_projection"]["final_open_projection"], "平开")
        self.assertEqual(payload["final_projection"]["final_intraday_path"], "震荡")
        self.assertEqual(payload["final_projection"]["final_close_projection"], "收平")
        # five_state defaults to 震荡 when direction is 中性.
        self.assertEqual(payload["final_projection"]["final_five_state"], "震荡")

    def test_primary_confidence_raw_reads_from_primary_projection_not_top_level(self) -> None:
        # primary_projection.final_confidence='medium', top-level final_confidence='high'.
        # The contract's primary_confidence_raw must reflect the PRE-adjustment confidence.
        predict = realistic_predict_result(
            primary_confidence="medium", final_confidence="high"
        )
        payload = adapt_projection_output(
            scan_result=None, research_result=None, predict_result=predict
        )
        self.assertEqual(payload["avgo_primary_projection"]["primary_confidence_raw"], "medium")
        self.assertEqual(payload["confidence_system"]["confidence_level"], "high")

    def test_historical_sample_count_reads_from_primary_projection(self) -> None:
        predict = realistic_predict_result()
        payload = adapt_projection_output(
            scan_result=None, research_result=None, predict_result=predict
        )
        self.assertEqual(payload["avgo_primary_projection"]["historical_sample_count"], 27)

    def test_supporting_factors_flow_to_key_evidence(self) -> None:
        predict = realistic_predict_result()
        payload = adapt_projection_output(
            scan_result=None, research_result=None, predict_result=predict
        )
        self.assertIn("primary_bias=bullish", payload["avgo_primary_projection"]["key_evidence"])
        self.assertIn("peer_confirmation=reinforce", payload["avgo_primary_projection"]["key_evidence"])

    def test_prediction_summary_flows_to_confidence_reason_and_final_one_sentence(self) -> None:
        predict = realistic_predict_result()
        payload = adapt_projection_output(
            scan_result=None, research_result=None, predict_result=predict
        )
        self.assertEqual(
            payload["confidence_system"]["confidence_reason"], "<placeholder final summary>"
        )
        self.assertEqual(
            payload["final_projection"]["final_one_sentence"], "<placeholder final summary>"
        )

    def test_peer_adjustment_notes_flow_to_adjustment_reason(self) -> None:
        predict = realistic_predict_result()
        payload = adapt_projection_output(
            scan_result=None, research_result=None, predict_result=predict
        )
        self.assertIn(
            "Peer adjustment",
            payload["peer_confirmation_adjustment"]["adjustment_reason"],
        )

    def test_relative_strength_weaker_maps_to_weaken(self) -> None:
        # realistic_scan_result has QQQ=weaker, NVDA=stronger, SOXX=neutral.
        payload = adapt_projection_output(
            scan_result=realistic_scan_result(),
            research_result=None,
            predict_result=None,
        )
        peer = payload["peer_confirmation_adjustment"]
        self.assertEqual(peer["nvda_signal"], "reinforce")
        self.assertEqual(peer["soxx_signal"], "neutral")
        self.assertEqual(peer["qqq_signal"], "weaken")

    def test_relative_strength_unavailable_maps_to_unknown(self) -> None:
        scan = realistic_scan_result()
        scan["relative_strength_summary"]["NVDA"]["relative_strength"] = "unavailable"
        payload = adapt_projection_output(
            scan_result=scan, research_result=None, predict_result=None
        )
        self.assertEqual(payload["peer_confirmation_adjustment"]["nvda_signal"], "unknown")


class PeerAlignmentDerivationTests(unittest.TestCase):
    """Locks all 4 branches of peer_alignment derivation."""

    def _payload(self, confirm: int, oppose: int) -> dict:
        return adapt_projection_output(
            scan_result=None,
            research_result=None,
            predict_result=realistic_predict_result(
                confirm_count=confirm, oppose_count=oppose
            ),
        )

    def test_all_reinforce(self) -> None:
        payload = self._payload(confirm=3, oppose=0)
        self.assertEqual(
            payload["peer_confirmation_adjustment"]["peer_alignment"], "all_reinforce"
        )

    def test_all_weaken(self) -> None:
        payload = self._payload(confirm=0, oppose=3)
        self.assertEqual(
            payload["peer_confirmation_adjustment"]["peer_alignment"], "all_weaken"
        )

    def test_insufficient(self) -> None:
        payload = self._payload(confirm=0, oppose=0)
        self.assertEqual(
            payload["peer_confirmation_adjustment"]["peer_alignment"], "insufficient"
        )

    def test_mixed(self) -> None:
        payload = self._payload(confirm=2, oppose=1)
        self.assertEqual(
            payload["peer_confirmation_adjustment"]["peer_alignment"], "mixed"
        )


class PeerAdjustmentLabelTests(unittest.TestCase):
    """Locks all 4 branches of adjustment_direction → peer_adjustment label."""

    def _label(self, direction: str) -> str:
        payload = adapt_projection_output(
            scan_result=None,
            research_result=None,
            predict_result=realistic_predict_result(adjustment_direction=direction),
        )
        return payload["peer_confirmation_adjustment"]["peer_adjustment"]

    def test_reinforce_to_upgrade(self) -> None:
        self.assertEqual(self._label("reinforce"), "upgrade")

    def test_weaken_to_downgrade(self) -> None:
        self.assertEqual(self._label("weaken"), "downgrade")

    def test_neutral_primary_to_flip(self) -> None:
        self.assertEqual(self._label("neutral_primary"), "flip_to_neutral")

    def test_neutral_to_hold(self) -> None:
        self.assertEqual(self._label("neutral"), "hold")


class ConfidenceLevelMappingTests(unittest.TestCase):
    def test_high_maps_to_bucket_and_total(self) -> None:
        payload = adapt_projection_output(
            scan_result=None,
            research_result=None,
            predict_result=realistic_predict_result(final_confidence="high"),
        )
        self.assertEqual(payload["confidence_system"]["confidence_level"], "high")
        self.assertEqual(payload["confidence_system"]["total_confidence"], 0.75)
        self.assertEqual(payload["final_projection"]["probability_bucket"], "≥70%")

    def test_medium_maps_to_bucket_and_total(self) -> None:
        payload = adapt_projection_output(
            scan_result=None,
            research_result=None,
            predict_result=realistic_predict_result(final_confidence="medium"),
        )
        self.assertEqual(payload["confidence_system"]["confidence_level"], "medium")
        self.assertEqual(payload["confidence_system"]["total_confidence"], 0.50)
        self.assertEqual(payload["final_projection"]["probability_bucket"], "55–70%")

    def test_low_maps_to_bucket_and_total(self) -> None:
        payload = adapt_projection_output(
            scan_result=None,
            research_result=None,
            predict_result=realistic_predict_result(final_confidence="low"),
        )
        self.assertEqual(payload["confidence_system"]["confidence_level"], "low")
        self.assertEqual(payload["confidence_system"]["total_confidence"], 0.25)
        self.assertEqual(payload["final_projection"]["probability_bucket"], "45–55%")

    def test_garbage_confidence_collapses_to_low(self) -> None:
        payload = adapt_projection_output(
            scan_result=None,
            research_result=None,
            predict_result=realistic_predict_result(final_confidence="extreme"),
        )
        self.assertEqual(payload["confidence_system"]["confidence_level"], "low")


class PredCloseRenameTests(unittest.TestCase):
    """The 平收 → 收平 rename is the only legacy-vs-contract label drift; lock it."""

    def test_legacy_pingshou_maps_to_contract_shouping(self) -> None:
        predict = realistic_predict_result(pred_close="平收")
        payload = adapt_projection_output(
            scan_result=None, research_result=None, predict_result=predict
        )
        self.assertEqual(payload["final_projection"]["final_close_projection"], "收平")
        self.assertEqual(payload["review_payload"]["predicted_close_type"], "收平")
        self.assertEqual(validate_projection_output(payload), [])


if __name__ == "__main__":
    unittest.main()
