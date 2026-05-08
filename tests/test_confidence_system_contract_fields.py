"""Step 2C-3b: contract 05 confidence_system score fields stay stubbed,
but extras surfaces the raw score-like signals already in predict_result.

This file does NOT test a calibrated confidence engine — there is none.
It only checks that:
  1. the 4 score fields (historical/structure/peer/exclusion_penalty)
     remain 0.0 and event_score remains None,
  2. confidence_level / total_confidence / confidence_reason continue
     to mirror predict.final_confidence / predict.prediction_summary,
  3. an additive ``extras`` sub-dict reflects the live signals on
     ``predict_result`` (primary_projection.score, peer counts,
     final_projection.probability_bucket, conflicting_factors,
     path_risk).

If a future step wires a real confidence engine, the score-stays-zero
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


_REQUIRED_05_FIELDS: tuple[str, ...] = (
    "historical_score",
    "structure_score",
    "peer_score",
    "exclusion_penalty",
    "event_score",
    "total_confidence",
    "confidence_level",
    "confidence_reason",
)

_EXTRAS_KEYS: tuple[str, ...] = (
    "primary_score_raw",
    "primary_confidence_raw",
    "peer_confirm_count",
    "peer_oppose_count",
    "peer_adjusted_confidence",
    "final_confidence",
    "probability_bucket",
    "conflicting_factors_count",
    "path_risk_level",
    "soft_signal",
)


def _section(predict_result: dict | None) -> dict:
    payload = adapt_projection_output(
        scan_result=None, research_result=None, predict_result=predict_result
    )
    return payload["confidence_system"]


# ── 1. score fields stay at the stubs ──────────────────────────────────────

class ConfidenceScoreFieldsRemainStubTests(unittest.TestCase):
    def test_required_fields_present_with_empty_predict_result(self) -> None:
        section = _section(None)
        for field in _REQUIRED_05_FIELDS:
            self.assertIn(field, section)

    def test_score_fields_are_zero_with_empty_predict_result(self) -> None:
        section = _section(None)
        self.assertEqual(section["historical_score"], 0.0)
        self.assertEqual(section["structure_score"], 0.0)
        self.assertEqual(section["peer_score"], 0.0)
        self.assertEqual(section["exclusion_penalty"], 0.0)
        self.assertIsNone(section["event_score"])

    def test_score_fields_unchanged_under_strong_signals_input(self) -> None:
        # Even when the predict_result carries a high primary score and
        # all-confirm peers, the 4 score fields and event_score must stay
        # at 0.0 / None — Step 2C-3b only surfaces signals into extras.
        predict = {
            "final_confidence": "high",
            "prediction_summary": "<placeholder>",
            "primary_projection": {
                "score": 3.25,
                "primary_confidence_raw": "high",
            },
            "peer_adjustment": {
                "confirm_count": 3,
                "oppose_count": 0,
                "adjusted_confidence": "high",
            },
        }
        section = _section(predict)
        self.assertEqual(section["historical_score"], 0.0)
        self.assertEqual(section["structure_score"], 0.0)
        self.assertEqual(section["peer_score"], 0.0)
        self.assertEqual(section["exclusion_penalty"], 0.0)
        self.assertIsNone(section["event_score"])


# ── 2. real fields keep their existing semantics ──────────────────────────

class ConfidenceRealFieldsKeepSemanticsTests(unittest.TestCase):
    def test_confidence_level_mirrors_final_confidence(self) -> None:
        for level in ("low", "medium", "high"):
            with self.subTest(level=level):
                section = _section({"final_confidence": level})
                self.assertEqual(section["confidence_level"], level)

    def test_total_confidence_three_way_mapping(self) -> None:
        cases = {"high": 0.75, "medium": 0.50, "low": 0.25}
        for level, expected in cases.items():
            with self.subTest(level=level):
                section = _section({"final_confidence": level})
                self.assertEqual(section["total_confidence"], expected)

    def test_confidence_reason_uses_prediction_summary(self) -> None:
        section = _section({"prediction_summary": "live reason text"})
        self.assertEqual(section["confidence_reason"], "live reason text")


# ── 3. extras presence & shape ─────────────────────────────────────────────

class ConfidenceExtrasShapeTests(unittest.TestCase):
    def test_extras_present_even_when_predict_result_is_none(self) -> None:
        section = _section(None)
        self.assertIn("extras", section)
        self.assertIsInstance(section["extras"], dict)
        for key in _EXTRAS_KEYS:
            self.assertIn(key, section["extras"], f"missing extras.{key}")

    def test_extras_default_values_with_empty_predict_result(self) -> None:
        extras = _section(None)["extras"]
        self.assertIsNone(extras["primary_score_raw"])
        self.assertEqual(extras["primary_confidence_raw"], "unknown")
        self.assertEqual(extras["peer_confirm_count"], 0)
        self.assertEqual(extras["peer_oppose_count"], 0)
        self.assertEqual(extras["peer_adjusted_confidence"], "unknown")
        self.assertEqual(extras["final_confidence"], "unknown")
        self.assertEqual(extras["probability_bucket"], "unknown")
        self.assertEqual(extras["conflicting_factors_count"], 0)
        self.assertEqual(extras["path_risk_level"], "unknown")
        self.assertEqual(extras["soft_signal"], "none")


# ── 4. extras values reflect predict_result ─────────────────────────────────

class ConfidenceExtrasValueMappingTests(unittest.TestCase):
    def test_primary_score_raw_passes_through_as_float(self) -> None:
        extras = _section({"primary_projection": {"score": 1.75}})["extras"]
        self.assertEqual(extras["primary_score_raw"], 1.75)
        self.assertIsInstance(extras["primary_score_raw"], float)

    def test_primary_score_raw_falls_back_to_none_when_unparsable(self) -> None:
        extras = _section({"primary_projection": {"score": "not-a-number"}})["extras"]
        self.assertIsNone(extras["primary_score_raw"])

    def test_primary_confidence_raw_pulls_from_primary(self) -> None:
        extras = _section({
            "primary_projection": {"primary_confidence_raw": "medium"},
        })["extras"]
        self.assertEqual(extras["primary_confidence_raw"], "medium")

    def test_primary_confidence_raw_falls_back_to_primary_final_confidence(self) -> None:
        extras = _section({
            "primary_projection": {"final_confidence": "high"},
        })["extras"]
        self.assertEqual(extras["primary_confidence_raw"], "high")

    def test_invalid_primary_confidence_raw_becomes_unknown(self) -> None:
        extras = _section({
            "primary_projection": {"primary_confidence_raw": "totally-bogus"},
        })["extras"]
        self.assertEqual(extras["primary_confidence_raw"], "unknown")

    def test_peer_counts_pass_through(self) -> None:
        extras = _section({
            "peer_adjustment": {"confirm_count": 3, "oppose_count": 0},
        })["extras"]
        self.assertEqual(extras["peer_confirm_count"], 3)
        self.assertEqual(extras["peer_oppose_count"], 0)

    def test_peer_counts_fall_back_to_zero_when_missing(self) -> None:
        extras = _section({"peer_adjustment": {}})["extras"]
        self.assertEqual(extras["peer_confirm_count"], 0)
        self.assertEqual(extras["peer_oppose_count"], 0)

    def test_peer_adjusted_confidence_passes_through(self) -> None:
        extras = _section({
            "peer_adjustment": {"adjusted_confidence": "low"},
        })["extras"]
        self.assertEqual(extras["peer_adjusted_confidence"], "low")

    def test_invalid_peer_adjusted_confidence_becomes_unknown(self) -> None:
        extras = _section({
            "peer_adjustment": {"adjusted_confidence": "bogus"},
        })["extras"]
        self.assertEqual(extras["peer_adjusted_confidence"], "unknown")

    def test_final_confidence_passes_through(self) -> None:
        extras = _section({"final_confidence": "medium"})["extras"]
        self.assertEqual(extras["final_confidence"], "medium")

    def test_invalid_final_confidence_becomes_unknown_in_extras(self) -> None:
        # The required `confidence_level` already coerces invalid values to
        # "low" via _normalize_confidence; the extras copy is more honest
        # and surfaces "unknown" so the original input is not silently
        # rewritten.
        extras = _section({"final_confidence": "??"})["extras"]
        self.assertEqual(extras["final_confidence"], "unknown")

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

    def test_conflicting_factors_count_mirrors_predict(self) -> None:
        extras = _section({
            "conflicting_factors": ["a", "b", "c"],
        })["extras"]
        self.assertEqual(extras["conflicting_factors_count"], 3)

    def test_non_list_conflicting_factors_count_is_zero(self) -> None:
        extras = _section({"conflicting_factors": "not-a-list"})["extras"]
        self.assertEqual(extras["conflicting_factors_count"], 0)

    def test_path_risk_level_passes_through(self) -> None:
        for level in ("low", "medium", "high"):
            with self.subTest(level=level):
                extras = _section({"path_risk": level})["extras"]
                self.assertEqual(extras["path_risk_level"], level)

    def test_invalid_path_risk_level_becomes_unknown(self) -> None:
        extras = _section({"path_risk": "extreme"})["extras"]
        self.assertEqual(extras["path_risk_level"], "unknown")


# ── 5. soft_signal heuristic (re-derived, NOT read from sibling section) ──

class ConfidenceSoftSignalTests(unittest.TestCase):
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
        self.assertEqual(
            _section(predict)["extras"]["soft_signal"], "high_path_risk"
        )

    def test_no_risk_signals_yield_none(self) -> None:
        predict = {"conflicting_factors": [], "path_risk": "low"}
        self.assertEqual(_section(predict)["extras"]["soft_signal"], "none")

    def test_unrelated_conflicting_factors_do_not_trigger_peer_weaken(self) -> None:
        predict = {
            "conflicting_factors": ["research_weakens_bullish"],
            "path_risk": "medium",
        }
        # Same heuristic as Step 2C-2: only the literal
        # "peer_confirmation=weaken" string flips the signal.
        self.assertEqual(_section(predict)["extras"]["soft_signal"], "none")


# ── 6. validator stays green ──────────────────────────────────────────────

class ConfidenceContractValidityTests(unittest.TestCase):
    def test_payload_validates_with_empty_predict_result(self) -> None:
        payload = adapt_projection_output(
            scan_result=None, research_result=None, predict_result=None
        )
        self.assertEqual(validate_projection_output(payload), [])

    def test_payload_validates_with_signals_input(self) -> None:
        predict = {
            "final_confidence": "medium",
            "prediction_summary": "live reason",
            "primary_projection": {"score": 1.5, "primary_confidence_raw": "medium"},
            "peer_adjustment": {
                "confirm_count": 2,
                "oppose_count": 1,
                "adjusted_confidence": "medium",
            },
            "final_projection": {"probability_bucket": "55–70%"},
            "conflicting_factors": ["peer_confirmation=weaken"],
            "path_risk": "high",
        }
        payload = adapt_projection_output(
            scan_result=None, research_result=None, predict_result=predict
        )
        self.assertEqual(validate_projection_output(payload), [])


# ── 7. live run_predict round-trip ────────────────────────────────────────

class ConfidenceRunPredictRoundTripTests(unittest.TestCase):
    """A real run_predict call must produce extras that reflect the live
    primary_projection.score / peer counts / final_projection on its
    predict_result."""

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

    def test_extras_mirrors_live_predict_result(self) -> None:
        scan = self._scan()
        # Step 12E-X2: ``run_predict.final_confidence`` is now sourced from
        # ``confidence_result.combined_confidence.level``. Pass a wired
        # confidence_result so this round-trip mirror retains a non-
        # ``unknown`` value to compare against; otherwise the adapter's
        # ``_normalize_confidence`` would map ``unknown`` to ``low`` and
        # break the equality below for reasons unrelated to the contract.
        confidence_result = {
            "schema_version": "confidence_system_result.v1",
            "ready": True,
            "combined_confidence": {"level": "high"},
            "agreement_status": "aligned",
            "conflict_level": "none",
        }
        predict = run_predict(
            scan,
            research_result=None,
            symbol="AVGO",
            confidence_result=confidence_result,
        )
        payload = adapt_projection_output(
            scan_result=scan, research_result=None, predict_result=predict
        )
        section = payload["confidence_system"]

        # Score fields must still be the stub even with strong bullish input.
        self.assertEqual(section["historical_score"], 0.0)
        self.assertEqual(section["structure_score"], 0.0)
        self.assertEqual(section["peer_score"], 0.0)
        self.assertEqual(section["exclusion_penalty"], 0.0)
        self.assertIsNone(section["event_score"])

        # Real fields wired correctly.
        self.assertEqual(section["confidence_level"], predict["final_confidence"])

        # Extras reflect predict_result one-for-one.
        extras = section["extras"]
        self.assertEqual(
            extras["primary_score_raw"], predict["primary_projection"]["score"]
        )
        self.assertEqual(
            extras["primary_confidence_raw"],
            predict["primary_projection"]["primary_confidence_raw"],
        )
        self.assertEqual(
            extras["peer_confirm_count"], predict["peer_adjustment"]["confirm_count"]
        )
        self.assertEqual(
            extras["peer_oppose_count"], predict["peer_adjustment"]["oppose_count"]
        )
        self.assertEqual(
            extras["peer_adjusted_confidence"],
            predict["peer_adjustment"]["adjusted_confidence"],
        )
        self.assertEqual(extras["final_confidence"], predict["final_confidence"])
        self.assertEqual(
            extras["probability_bucket"],
            predict["final_projection"]["probability_bucket"],
        )
        self.assertEqual(extras["path_risk_level"], predict["path_risk"])
        # All peers stronger under bullish primary → no peer_weaken signal.
        self.assertEqual(extras["soft_signal"], "none")


if __name__ == "__main__":
    unittest.main()
