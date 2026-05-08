"""Contract enforcement tests for Step 12E-X2 (RISK-8 stage X2).

X2 wires ``run_predict``'s legacy compat ``final_confidence`` (and the
``confidence`` alias) to ``confidence_result.combined_confidence.level``.
When the caller does not supply a ``confidence_result``, the legacy
fields degrade to ``"unknown"``. X2 must not change ``final_direction``,
projection / scan / summary shape, or any direction-side field.

Specifically, X2 enforces:

1. ``run_predict(... confidence_result=cr)`` sets
   ``result["final_confidence"] == cr["combined_confidence"]["level"]``
   for every valid level.
2. ``run_predict(... confidence_result=cr)`` exposes the ``confidence``
   alias with the same value as ``final_confidence``.
3. Without ``confidence_result``, both ``final_confidence`` and
   ``confidence`` are ``"unknown"``.
4. Invalid ``combined_confidence.level`` values fall back to
   ``"unknown"``.
5. ``source_mapping["compat_final_confidence"]`` no longer carries a
   ``pending`` marker — it now points at
   ``confidence_result.combined_confidence.level``.
6. The legacy direction-side fields (``final_bias``,
   ``final_projection.final_direction``, ``primary_projection`` shape,
   ``prediction_summary``) are unchanged by X2.
7. The result still does not carry trading / hard / forced / required /
   promotion / mutation surfaces.
8. ``predict.py`` does not import LLM / promotion / continuous_smoothing
   surfaces (re-affirm X1 import guards).

Design contracts: 07C / 11C / 11E / 11H.
"""

from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _fresh_predict_module():
    """Reload predict to defeat the leftover monkeypatch from
    ``tests/fixtures/app_analysis_context_fixture.py`` (see X1 boundary
    test file for the same workaround)."""
    import predict as _predict

    return importlib.reload(_predict)


_FORBIDDEN_OUTPUT_FIELDS = (
    "trading_action",
    "buy",
    "sell",
    "hold",
    "simulated_trade",
    "no_trade",
    "hard_exclusion",
    "forced_exclusion",
    "required_decision",
    "production_promotion",
    "_PROTECTION_LAYER_CONNECTED",
    "final_report_mutation",
    "modified_projection",
    "modified_exclusion",
    "modified_confidence",
    "overridden_most_likely_state",
    "corrected_confidence",
)


def _confidence_result(level: str) -> dict:
    return {
        "schema_version": "confidence_system_result.v1",
        "system_name": "confidence_system",
        "ready": True,
        "combined_confidence": {"level": level, "score": None, "reasoning": []},
        "agreement_status": "aligned",
        "conflict_level": "none",
    }


def _scan() -> dict:
    recent_rows = [
        {
            "Date": f"2026-04-{day:02d}",
            "Open": 100.0 + (day - 1) - 0.25,
            "Close": 100.0 + (day - 1),
            "O_gap": 0.006,
            "C_move": 0.01,
            "V_ratio": 1.2,
        }
        for day in range(1, 21)
    ]
    return {
        "symbol": "AVGO",
        "scan_bias": "bullish",
        "scan_confidence": "medium",
        "avgo_gap_state": "gap_up",
        "avgo_intraday_state": "high_go",
        "avgo_volume_state": "expanding",
        "avgo_price_state": "bullish",
        "historical_match_summary": {"dominant_historical_outcome": "up_bias"},
        "avgo_recent_20": recent_rows,
        "relative_strength_summary": {
            "vs_nvda": "stronger",
            "vs_soxx": "stronger",
            "vs_qqq": "neutral",
        },
        "relative_strength_same_day_summary": {
            "vs_nvda": "stronger",
            "vs_soxx": "neutral",
            "vs_qqq": "stronger",
        },
    }


class FinalConfidenceFromConfidenceResultTests(unittest.TestCase):
    def test_predict_final_confidence_from_confidence_result_high(self) -> None:
        predict = _fresh_predict_module()
        result = predict.run_predict(
            _scan(),
            research_result=None,
            symbol="AVGO",
            confidence_result=_confidence_result("high"),
        )
        self.assertEqual(result["final_confidence"], "high")

    def test_predict_final_confidence_from_confidence_result_medium(self) -> None:
        predict = _fresh_predict_module()
        result = predict.run_predict(
            _scan(),
            research_result=None,
            symbol="AVGO",
            confidence_result=_confidence_result("medium"),
        )
        self.assertEqual(result["final_confidence"], "medium")

    def test_predict_final_confidence_from_confidence_result_low(self) -> None:
        predict = _fresh_predict_module()
        result = predict.run_predict(
            _scan(),
            research_result=None,
            symbol="AVGO",
            confidence_result=_confidence_result("low"),
        )
        self.assertEqual(result["final_confidence"], "low")

    def test_predict_confidence_alias_mirrors_final_confidence(self) -> None:
        predict = _fresh_predict_module()
        for level in ("low", "medium", "high"):
            result = predict.run_predict(
                _scan(),
                research_result=None,
                symbol="AVGO",
                confidence_result=_confidence_result(level),
            )
            self.assertEqual(result["confidence"], level)
            self.assertEqual(result["final_confidence"], result["confidence"])

    def test_predict_missing_confidence_result_returns_unknown(self) -> None:
        predict = _fresh_predict_module()
        result = predict.run_predict(_scan(), research_result=None, symbol="AVGO")
        self.assertEqual(result["final_confidence"], "unknown")
        self.assertEqual(result["confidence"], "unknown")

    def test_predict_explicit_none_confidence_result_returns_unknown(self) -> None:
        predict = _fresh_predict_module()
        result = predict.run_predict(
            _scan(),
            research_result=None,
            symbol="AVGO",
            confidence_result=None,
        )
        self.assertEqual(result["final_confidence"], "unknown")
        self.assertEqual(result["confidence"], "unknown")

    def test_predict_invalid_level_in_confidence_result_returns_unknown(self) -> None:
        predict = _fresh_predict_module()
        for bogus in ("super_high", "", None, "??", 1.0):
            result = predict.run_predict(
                _scan(),
                research_result=None,
                symbol="AVGO",
                confidence_result={
                    "ready": True,
                    "combined_confidence": {"level": bogus},
                },
            )
            self.assertEqual(
                result["final_confidence"],
                "unknown",
                msg=f"bogus level {bogus!r} must degrade to unknown",
            )

    def test_predict_missing_combined_confidence_returns_unknown(self) -> None:
        predict = _fresh_predict_module()
        result = predict.run_predict(
            _scan(),
            research_result=None,
            symbol="AVGO",
            confidence_result={"ready": True},
        )
        self.assertEqual(result["final_confidence"], "unknown")

    def test_predict_unknown_level_passes_through(self) -> None:
        predict = _fresh_predict_module()
        result = predict.run_predict(
            _scan(),
            research_result=None,
            symbol="AVGO",
            confidence_result=_confidence_result("unknown"),
        )
        self.assertEqual(result["final_confidence"], "unknown")
        self.assertEqual(result["confidence"], "unknown")


class MissingScanPathTests(unittest.TestCase):
    def test_missing_scan_path_uses_confidence_result_when_provided(self) -> None:
        predict = _fresh_predict_module()
        result = predict.run_predict(
            None,
            research_result=None,
            symbol="AVGO",
            confidence_result=_confidence_result("medium"),
        )
        self.assertEqual(result["final_confidence"], "medium")
        self.assertEqual(result["confidence"], "medium")
        # Direction side must still be ``unavailable`` — X2 doesn't touch it.
        self.assertEqual(result["final_bias"], "unavailable")
        self.assertEqual(result["scan_bias"], "missing")

    def test_missing_scan_path_default_confidence_is_unknown(self) -> None:
        predict = _fresh_predict_module()
        result = predict.run_predict(None, research_result=None, symbol="AVGO")
        self.assertEqual(result["final_confidence"], "unknown")
        self.assertEqual(result["confidence"], "unknown")


class SourceMappingTests(unittest.TestCase):
    def test_predict_source_mapping_final_confidence_points_to_confidence_result(self) -> None:
        predict = _fresh_predict_module()
        result = predict.run_predict(_scan(), research_result=None, symbol="AVGO")
        mapping = result["source_mapping"]
        # X2 explicitly wires final_confidence — the mapping no longer
        # carries a "pending" marker for compat_final_confidence.
        target = mapping["compat_final_confidence"]
        self.assertNotIn("pending", target.lower())
        self.assertIn("confidence_result", target)
        self.assertIn("combined_confidence", target)

    def test_predict_source_mapping_includes_confidence_alias_entry(self) -> None:
        predict = _fresh_predict_module()
        result = predict.run_predict(_scan(), research_result=None, symbol="AVGO")
        mapping = result["source_mapping"]
        self.assertIn("compat_confidence", mapping)
        target = mapping["compat_confidence"]
        self.assertIn("confidence_result", target)


class DirectionSideUnchangedTests(unittest.TestCase):
    """X2 must not touch direction / projection / scan / summary side."""

    def test_x2_does_not_change_final_direction_or_bias(self) -> None:
        predict = _fresh_predict_module()
        baseline = predict.run_predict(_scan(), research_result=None, symbol="AVGO")
        with_high = predict.run_predict(
            _scan(),
            research_result=None,
            symbol="AVGO",
            confidence_result=_confidence_result("high"),
        )
        with_low = predict.run_predict(
            _scan(),
            research_result=None,
            symbol="AVGO",
            confidence_result=_confidence_result("low"),
        )
        # final_bias / open_tendency / close_tendency / pred_open / pred_path
        # / pred_close are direction-side. They must not vary with the
        # confidence_result level.
        for field in (
            "final_bias",
            "open_tendency",
            "close_tendency",
            "pred_open",
            "pred_path",
            "pred_close",
            "scan_bias",
        ):
            self.assertEqual(
                baseline[field],
                with_high[field],
                msg=f"X2 must not change {field!r} (baseline vs confidence=high)",
            )
            self.assertEqual(
                baseline[field],
                with_low[field],
                msg=f"X2 must not change {field!r} (baseline vs confidence=low)",
            )

    def test_x2_does_not_change_projection_and_summary_fields(self) -> None:
        predict = _fresh_predict_module()
        baseline = predict.run_predict(_scan(), research_result=None, symbol="AVGO")
        wired = predict.run_predict(
            _scan(),
            research_result=None,
            symbol="AVGO",
            confidence_result=_confidence_result("high"),
        )
        self.assertEqual(
            baseline["primary_projection"],
            wired["primary_projection"],
            msg="X2 must not change primary_projection",
        )
        self.assertEqual(
            baseline["peer_adjustment"],
            wired["peer_adjustment"],
            msg="X2 must not change peer_adjustment",
        )
        # ``final_projection`` carries its own internal ``final_confidence``
        # (a v1-computed value). X2 only overrides the outer-level wrapper
        # field; the inner final_projection stays unchanged.
        self.assertEqual(
            baseline["final_projection"],
            wired["final_projection"],
            msg="X2 must not modify the inner final_projection block",
        )
        self.assertEqual(
            baseline["prediction_summary"],
            wired["prediction_summary"],
            msg="X2 must not change prediction_summary text",
        )
        self.assertEqual(
            baseline["supporting_factors"],
            wired["supporting_factors"],
        )
        self.assertEqual(
            baseline["conflicting_factors"],
            wired["conflicting_factors"],
        )

    def test_x2_does_not_introduce_forbidden_fields(self) -> None:
        predict = _fresh_predict_module()
        for confidence_input in (
            None,
            _confidence_result("low"),
            _confidence_result("medium"),
            _confidence_result("high"),
        ):
            result = predict.run_predict(
                _scan(),
                research_result=None,
                symbol="AVGO",
                confidence_result=confidence_input,
            )
            for forbidden in _FORBIDDEN_OUTPUT_FIELDS:
                self.assertNotIn(forbidden, result, msg=f"{forbidden} present")


class StaticImportReaffirmedTests(unittest.TestCase):
    """Re-affirm the X1 import guards still hold under X2."""

    def setUp(self) -> None:
        self.source = (ROOT / "predict.py").read_text(encoding="utf-8")

    def test_predict_py_no_continuous_smoothing_import(self) -> None:
        for forbidden in (
            "from services.continuous_smoothing",
            "import services.continuous_smoothing",
            "import continuous_smoothing",
        ):
            self.assertNotIn(forbidden, self.source)

    def test_predict_py_no_promotion_import(self) -> None:
        for forbidden in (
            "services.active_rule_pool_promotion",
            "services.promotion_adoption_gate",
            "services.promotion_execution_bridge",
        ):
            self.assertNotIn(forbidden, self.source)

    def test_predict_py_no_ai_summary_import(self) -> None:
        for forbidden in (
            "from services.ai_summary",
            "import services.ai_summary",
        ):
            self.assertNotIn(forbidden, self.source)


if __name__ == "__main__":
    unittest.main()
