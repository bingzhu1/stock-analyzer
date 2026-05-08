"""Contract enforcement tests for Step 12E-X3 (RISK-8 stage X3).

X3 wires ``run_predict``'s legacy compat ``prediction_summary`` (and the
``summary`` alias) to ``final_report.combined_user_summary`` when a
``final_report`` is supplied. When the caller omits ``final_report`` —
or supplies one without a usable ``combined_user_summary`` — the wrapper
falls back to the legacy v1 prediction_summary text it already produced
in stages X1/X2. X3 must not touch ``final_direction``, ``final_bias``,
``final_confidence``, ``primary_projection``, ``peer_adjustment``, or
any other direction- or projection-side field.

Specifically, X3 enforces:

1. ``run_predict(... final_report=fr)`` sets
   ``result["prediction_summary"] == fr["combined_user_summary"]`` when
   that field is a non-empty string.
2. ``run_predict(... final_report=fr)`` exposes the ``summary`` alias
   with the same value as ``prediction_summary``.
3. Without ``final_report`` (or when ``combined_user_summary`` is
   missing / empty / non-str), ``prediction_summary`` retains its
   legacy v1 value, and ``summary`` mirrors it.
4. ``source_mapping["compat_prediction_summary"]`` no longer carries a
   ``pending`` marker — it now points at
   ``final_report.combined_user_summary`` with an explicit fallback
   suffix.
5. ``compat_summary`` alias entry exists in source_mapping.
6. ``final_direction`` / ``final_bias`` / ``final_confidence`` are
   unchanged by X3 (independent of whether final_report was supplied).
7. The result still does not carry trading / hard / forced / required /
   promotion / mutation surfaces.
8. ``predict.py`` does not import LLM / promotion / continuous_smoothing
   surfaces (re-affirm X1 / X2 import guards).

Design contracts: 07D / 11B / 11E / 11H.
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
    ``tests/fixtures/app_analysis_context_fixture.py`` (see X1 / X2
    boundary test files for the same workaround)."""
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


def _confidence_result(level: str = "medium") -> dict:
    return {
        "schema_version": "confidence_system_result.v1",
        "ready": True,
        "combined_confidence": {"level": level},
        "agreement_status": "aligned",
        "conflict_level": "none",
    }


def _final_report(combined_user_summary: str | None = "明日基准判断：偏多。基于推演 + 否定 + 置信度三系统综合显示。") -> dict:
    payload: dict = {
        "schema_version": "final_report_aggregator_result.v1",
        "system_name": "final_report_aggregator",
        "final_direction": "偏多",
        "final_confidence": "medium",
    }
    if combined_user_summary is not None:
        payload["combined_user_summary"] = combined_user_summary
    return payload


# ---------------------------------------------------------------------------
# Primary-source path: prediction_summary comes from final_report
# ---------------------------------------------------------------------------


class PredictionSummaryFromFinalReportTests(unittest.TestCase):
    def test_predict_summary_from_final_report_combined_user_summary(self) -> None:
        predict = _fresh_predict_module()
        fr = _final_report("从 final_report 来的中文总结。")
        result = predict.run_predict(
            _scan(),
            research_result=None,
            symbol="AVGO",
            confidence_result=_confidence_result("high"),
            final_report=fr,
        )
        self.assertEqual(
            result["prediction_summary"],
            "从 final_report 来的中文总结。",
        )

    def test_predict_summary_alias_mirrors_prediction_summary(self) -> None:
        predict = _fresh_predict_module()
        fr = _final_report("alias mirror sentence.")
        result = predict.run_predict(
            _scan(),
            research_result=None,
            symbol="AVGO",
            confidence_result=_confidence_result("medium"),
            final_report=fr,
        )
        self.assertIn("summary", result)
        self.assertEqual(result["summary"], result["prediction_summary"])
        self.assertEqual(result["summary"], "alias mirror sentence.")

    def test_predict_summary_uses_final_report_even_without_confidence_result(self) -> None:
        predict = _fresh_predict_module()
        fr = _final_report("source-of-truth summary.")
        result = predict.run_predict(
            _scan(),
            research_result=None,
            symbol="AVGO",
            final_report=fr,
        )
        self.assertEqual(result["prediction_summary"], "source-of-truth summary.")
        self.assertEqual(result["summary"], "source-of-truth summary.")


# ---------------------------------------------------------------------------
# Fallback path: missing / empty / malformed final_report -> legacy
# ---------------------------------------------------------------------------


class PredictionSummaryFallbackTests(unittest.TestCase):
    def test_predict_missing_final_report_uses_legacy_summary_fallback(self) -> None:
        predict = _fresh_predict_module()
        result = predict.run_predict(
            _scan(),
            research_result=None,
            symbol="AVGO",
        )
        # Legacy v1 prediction_summary is always non-empty in the
        # populated-scan path (it comes from build_final_projection or
        # falls back to _summarize). The fallback must keep that text.
        self.assertIsInstance(result["prediction_summary"], str)
        self.assertNotEqual(result["prediction_summary"], "")
        # ``summary`` alias must mirror ``prediction_summary`` even on the
        # fallback path so the two compat aliases never diverge.
        self.assertIn("summary", result)
        self.assertEqual(result["summary"], result["prediction_summary"])

    def test_predict_empty_combined_user_summary_falls_back_to_legacy(self) -> None:
        predict = _fresh_predict_module()
        legacy = predict.run_predict(_scan(), research_result=None, symbol="AVGO")
        wired = predict.run_predict(
            _scan(),
            research_result=None,
            symbol="AVGO",
            final_report=_final_report(""),
        )
        # Empty string in combined_user_summary must not override legacy.
        self.assertEqual(wired["prediction_summary"], legacy["prediction_summary"])
        self.assertEqual(wired["summary"], legacy["summary"])

    def test_predict_missing_combined_user_summary_field_falls_back(self) -> None:
        predict = _fresh_predict_module()
        legacy = predict.run_predict(_scan(), research_result=None, symbol="AVGO")
        wired = predict.run_predict(
            _scan(),
            research_result=None,
            symbol="AVGO",
            final_report=_final_report(combined_user_summary=None),
        )
        self.assertEqual(wired["prediction_summary"], legacy["prediction_summary"])
        self.assertEqual(wired["summary"], legacy["summary"])

    def test_predict_non_string_combined_user_summary_falls_back(self) -> None:
        predict = _fresh_predict_module()
        legacy = predict.run_predict(_scan(), research_result=None, symbol="AVGO")
        for bogus in (123, [], {}, ["x", "y"]):
            fr = {
                "schema_version": "final_report_aggregator_result.v1",
                "combined_user_summary": bogus,
            }
            wired = predict.run_predict(
                _scan(),
                research_result=None,
                symbol="AVGO",
                final_report=fr,
            )
            self.assertEqual(
                wired["prediction_summary"],
                legacy["prediction_summary"],
                msg=f"bogus combined_user_summary {bogus!r} must fall back",
            )

    def test_predict_explicit_none_final_report_falls_back(self) -> None:
        predict = _fresh_predict_module()
        legacy = predict.run_predict(_scan(), research_result=None, symbol="AVGO")
        wired = predict.run_predict(
            _scan(),
            research_result=None,
            symbol="AVGO",
            final_report=None,
        )
        self.assertEqual(wired["prediction_summary"], legacy["prediction_summary"])

    def test_missing_scan_path_summary_alias_consistent(self) -> None:
        predict = _fresh_predict_module()
        result = predict.run_predict(None, research_result=None, symbol="AVGO")
        # Legacy fallback for missing-scan path produces a fixed
        # ``_summarize`` string. Whatever it is, ``summary`` mirrors
        # ``prediction_summary``.
        self.assertEqual(result["summary"], result["prediction_summary"])

    def test_missing_scan_path_uses_final_report_when_provided(self) -> None:
        predict = _fresh_predict_module()
        fr = _final_report("missing scan but final_report has summary.")
        result = predict.run_predict(
            None,
            research_result=None,
            symbol="AVGO",
            final_report=fr,
        )
        self.assertEqual(
            result["prediction_summary"],
            "missing scan but final_report has summary.",
        )
        self.assertEqual(result["summary"], "missing scan but final_report has summary.")


# ---------------------------------------------------------------------------
# source_mapping
# ---------------------------------------------------------------------------


class SourceMappingTests(unittest.TestCase):
    def test_predict_source_mapping_summary_points_to_final_report_or_fallback(self) -> None:
        predict = _fresh_predict_module()
        result = predict.run_predict(_scan(), research_result=None, symbol="AVGO")
        mapping = result["source_mapping"]
        target = mapping["compat_prediction_summary"]
        self.assertNotIn("pending", target.lower())
        self.assertIn("final_report.combined_user_summary", target)
        self.assertIn("legacy_predict_path_fallback", target)

    def test_predict_source_mapping_includes_summary_alias_entry(self) -> None:
        predict = _fresh_predict_module()
        result = predict.run_predict(_scan(), research_result=None, symbol="AVGO")
        mapping = result["source_mapping"]
        self.assertIn("compat_summary", mapping)
        target = mapping["compat_summary"]
        self.assertIn("final_report.combined_user_summary", target)
        self.assertIn("legacy_predict_path_fallback", target)


# ---------------------------------------------------------------------------
# X3 must not touch direction / confidence / projection side
# ---------------------------------------------------------------------------


class DirectionAndConfidenceUnchangedTests(unittest.TestCase):
    def test_x3_does_not_change_final_direction_or_bias(self) -> None:
        predict = _fresh_predict_module()
        baseline = predict.run_predict(_scan(), research_result=None, symbol="AVGO")
        with_fr = predict.run_predict(
            _scan(),
            research_result=None,
            symbol="AVGO",
            final_report=_final_report("a wholly new summary."),
        )
        # Even if the final_report dictates a different final_direction
        # value (we set "偏多" in the fixture), the wrapper must NOT
        # surface that — it stays on the v1-derived final_bias.
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
                with_fr[field],
                msg=f"X3 must not change {field!r}",
            )

    def test_x3_does_not_change_final_confidence_x2_behavior(self) -> None:
        predict = _fresh_predict_module()
        # Without confidence_result + with final_report → confidence stays unknown.
        result = predict.run_predict(
            _scan(),
            research_result=None,
            symbol="AVGO",
            final_report=_final_report("hello"),
        )
        self.assertEqual(result["final_confidence"], "unknown")
        self.assertEqual(result["confidence"], "unknown")

        # With confidence_result + with final_report → still wired from cr.
        result = predict.run_predict(
            _scan(),
            research_result=None,
            symbol="AVGO",
            confidence_result=_confidence_result("high"),
            final_report=_final_report("hello again"),
        )
        self.assertEqual(result["final_confidence"], "high")
        self.assertEqual(result["confidence"], "high")

    def test_x3_preserves_projection_fields(self) -> None:
        predict = _fresh_predict_module()
        baseline = predict.run_predict(_scan(), research_result=None, symbol="AVGO")
        with_fr = predict.run_predict(
            _scan(),
            research_result=None,
            symbol="AVGO",
            final_report=_final_report("non-default summary."),
        )
        self.assertEqual(
            baseline["primary_projection"],
            with_fr["primary_projection"],
        )
        self.assertEqual(baseline["peer_adjustment"], with_fr["peer_adjustment"])
        self.assertEqual(baseline["final_projection"], with_fr["final_projection"])
        self.assertEqual(baseline["path_risk"], with_fr["path_risk"])

    def test_x3_does_not_introduce_forbidden_fields(self) -> None:
        predict = _fresh_predict_module()
        for fr in (
            None,
            _final_report("ok summary."),
            _final_report(""),
            {"schema_version": "final_report_aggregator_result.v1"},
        ):
            result = predict.run_predict(
                _scan(),
                research_result=None,
                symbol="AVGO",
                final_report=fr,
            )
            for forbidden in _FORBIDDEN_OUTPUT_FIELDS:
                self.assertNotIn(
                    forbidden,
                    result,
                    msg=f"X3 must not introduce {forbidden!r}",
                )


# ---------------------------------------------------------------------------
# Static import guards reaffirmed
# ---------------------------------------------------------------------------


class StaticImportReaffirmedTests(unittest.TestCase):
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
