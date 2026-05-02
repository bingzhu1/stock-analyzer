"""Tests for services/projection_output_contract.py (Step 1B).

All payloads use placeholder / fake values; no real market data.
"""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.projection_output_contract import (
    CONTRACT_SECTIONS,
    validate_projection_output,
)


def _valid_payload() -> dict:
    """Return a fully-valid payload matching the Step 1A contract."""
    return {
        "current_structure": {
            "symbol": "AVGO",
            "analysis_date": "<YYYY-MM-DD>",
            "prediction_for_date": "<YYYY-MM-DD>",
            "data_window_days": 15,
            "current_price": 100.0,
            "previous_close": 99.0,
            "volume": 1_000_000,
            "turnover": 100_000_000.0,
            "structure_label": "整理",
            "short_summary": "<placeholder>",
        },
        "avgo_primary_projection": {
            "primary_direction": "偏多",
            "open_projection": "高开",
            "intraday_path_projection": "高走",
            "close_projection": "收涨",
            "five_state_projection": "小涨",
            "historical_sample_count": 42,
            "key_evidence": ["evidence-1", "evidence-2"],
            "primary_confidence_raw": "medium",
        },
        "peer_confirmation_adjustment": {
            "peer_symbols": ["NVDA", "SOXX", "QQQ"],
            "nvda_signal": "reinforce",
            "soxx_signal": "neutral",
            "qqq_signal": "reinforce",
            "peer_alignment": "mixed",
            "peer_adjustment": "hold",
            "adjusted_direction": "偏多",
            "adjustment_reason": "<placeholder>",
        },
        "exclusion_system": {
            "exclusion_level": "soft",
            "exclusion_sources": ["volume_drop"],
            "exclusion_reasons": ["<reason>"],
            "forced_exclusion": False,
            "anti_false_exclusion_triggered": False,
        },
        "confidence_system": {
            "historical_score": 0.6,
            "structure_score": 0.5,
            "peer_score": 0.4,
            "exclusion_penalty": 0.1,
            "event_score": None,
            "total_confidence": 0.55,
            "confidence_level": "medium",
            "confidence_reason": "<placeholder>",
        },
        "final_projection": {
            "final_direction": "偏多",
            "final_open_projection": "高开",
            "final_intraday_path": "高走",
            "final_close_projection": "收涨",
            "final_five_state": "小涨",
            "probability_bucket": "55–70%",
            "key_price_levels": {
                "support": 95.0,
                "resistance": 105.0,
                "breakout_trigger": 106.0,
                "breakdown_trigger": 94.0,
            },
            "final_one_sentence": "<placeholder>",
        },
        "simulated_trade": {
            "trade_action": "open",
            "trade_direction": "long",
            "entry_condition": "<placeholder>",
            "stop_loss_condition": "<placeholder>",
            "take_profit_condition": "<placeholder>",
            "suggested_position_size": "50%",
            "no_trade_reason": None,
        },
        "review_payload": {
            "predicted_open_type": "高开",
            "predicted_path_type": "高走",
            "predicted_close_type": "收涨",
            "predicted_five_state": "小涨",
            "predicted_confidence": "medium",
            "prediction_id": "<set_by_prediction_store>",
            "review_ready_fields": [
                "predicted_open_type",
                "predicted_close_type",
            ],
        },
    }


class ContractSectionsTests(unittest.TestCase):
    def test_contract_sections_order_is_fixed(self) -> None:
        # Spec: tasks/step_1a_projection_output_contract.md §2
        self.assertEqual(
            CONTRACT_SECTIONS,
            (
                "current_structure",
                "avgo_primary_projection",
                "peer_confirmation_adjustment",
                "exclusion_system",
                "confidence_system",
                "final_projection",
                "simulated_trade",
                "review_payload",
            ),
        )
        self.assertEqual(len(CONTRACT_SECTIONS), 8)
        self.assertIsInstance(CONTRACT_SECTIONS, tuple)


class ValidateProjectionOutputTests(unittest.TestCase):
    def test_valid_payload_returns_empty_list(self) -> None:
        self.assertEqual(validate_projection_output(_valid_payload()), [])

    def test_non_dict_payload_returns_error(self) -> None:
        for bad in (None, [], "string", 42, 3.14, ()):
            with self.subTest(bad=bad):
                errors = validate_projection_output(bad)  # type: ignore[arg-type]
                self.assertEqual(len(errors), 1)
                self.assertTrue(errors[0].startswith("invalid type: payload"))

    def test_missing_top_level_section(self) -> None:
        payload = _valid_payload()
        del payload["confidence_system"]
        errors = validate_projection_output(payload)
        self.assertIn("missing section: confidence_system", errors)
        # Other sections still validate fine — only confidence_system flagged.
        self.assertEqual(
            [e for e in errors if "confidence_system" in e],
            ["missing section: confidence_system"],
        )

    def test_section_is_not_dict(self) -> None:
        payload = _valid_payload()
        payload["exclusion_system"] = "not a dict"
        errors = validate_projection_output(payload)
        self.assertIn("section is not a dict: exclusion_system", errors)
        # Field-level errors are skipped when the section itself is broken.
        self.assertFalse(any(e.startswith("missing field: exclusion_system.") for e in errors))

    def test_missing_required_field(self) -> None:
        payload = _valid_payload()
        del payload["current_structure"]["symbol"]
        errors = validate_projection_output(payload)
        self.assertIn("missing field: current_structure.symbol", errors)

    def test_invalid_numeric_type(self) -> None:
        payload = _valid_payload()
        payload["confidence_system"]["total_confidence"] = "not a number"
        errors = validate_projection_output(payload)
        self.assertTrue(
            any(
                e.startswith("invalid type: confidence_system.total_confidence")
                for e in errors
            ),
            msg=f"errors={errors}",
        )

    def test_invalid_list_type(self) -> None:
        payload = _valid_payload()
        payload["avgo_primary_projection"]["key_evidence"] = "not a list"
        errors = validate_projection_output(payload)
        self.assertTrue(
            any(
                e.startswith("invalid type: avgo_primary_projection.key_evidence")
                for e in errors
            ),
            msg=f"errors={errors}",
        )

    def test_invalid_enum_value(self) -> None:
        payload = _valid_payload()
        payload["exclusion_system"]["exclusion_level"] = "extreme"
        errors = validate_projection_output(payload)
        self.assertIn("invalid value: exclusion_system.exclusion_level", errors)

    def test_validate_does_not_mutate_payload(self) -> None:
        # Valid payload — must remain identical after validation.
        payload = _valid_payload()
        snapshot = copy.deepcopy(payload)
        validate_projection_output(payload)
        self.assertEqual(payload, snapshot)

        # Malformed payload — also must not be mutated.
        broken = {"current_structure": "wrong", "extras_only": 123}
        broken_snapshot = copy.deepcopy(broken)
        validate_projection_output(broken)
        self.assertEqual(broken, broken_snapshot)

    def test_extras_field_in_section_does_not_break_validation(self) -> None:
        # 1A allows an `extras` dict per section for experimental fields.
        payload = _valid_payload()
        payload["confidence_system"]["extras"] = {"experimental_score": 0.99}
        self.assertEqual(validate_projection_output(payload), [])

    def test_bool_is_not_accepted_as_number(self) -> None:
        # Defensive: bool is a subclass of int in Python; we explicitly reject it
        # for numeric fields so that True/False can't slip into score fields.
        payload = _valid_payload()
        payload["confidence_system"]["total_confidence"] = True
        errors = validate_projection_output(payload)
        self.assertTrue(
            any(
                e.startswith("invalid type: confidence_system.total_confidence")
                for e in errors
            ),
            msg=f"errors={errors}",
        )

    def test_event_score_may_be_null(self) -> None:
        # 1A: event_score is the only score that may be null this round.
        payload = _valid_payload()
        payload["confidence_system"]["event_score"] = None
        self.assertEqual(validate_projection_output(payload), [])

    def test_no_trade_reason_may_be_null_when_action_is_open(self) -> None:
        payload = _valid_payload()
        payload["simulated_trade"]["no_trade_reason"] = None
        self.assertEqual(validate_projection_output(payload), [])

    def test_no_trade_reason_can_be_string(self) -> None:
        payload = _valid_payload()
        payload["simulated_trade"]["trade_action"] = "no_trade"
        payload["simulated_trade"]["trade_direction"] = "none"
        payload["simulated_trade"]["suggested_position_size"] = "0%"
        payload["simulated_trade"]["no_trade_reason"] = "结构不清晰，跳过"
        self.assertEqual(validate_projection_output(payload), [])


if __name__ == "__main__":
    unittest.main()
