"""Contract enforcement tests for Step 12E-X1 (RISK-8 stage A: legacy
wrapper marking + source_mapping foundation).

These tests pin the legacy-wrapper boundary on ``predict.py`` without
migrating any projection / aggregator / confidence logic. X1 is purely
about declaration and metadata — later stages (X2..X5) move computation.

Specifically, X1 enforces:

1. ``predict.py`` module docstring carries the
   ``LEGACY_COMPATIBILITY_WRAPPER`` marker.
2. ``predict.PREDICT_LEGACY_WRAPPER_KIND`` /
   ``PREDICT_LEGACY_WRAPPER_VERSION`` constants exist with the agreed
   values.
3. ``run_predict(...)`` output dict carries
   ``wrapper_kind == "legacy_predict_wrapper"``,
   ``wrapper_version == "predict_legacy_wrapper.v1"``,
   ``legacy_compatibility == True``, plus ``source_mapping`` and
   ``deprecation_notes``.
4. ``source_mapping`` provides the foundation entries for the most
   compat-critical fields (``compat_final_bias``,
   ``compat_final_confidence``, ``compat_prediction_summary``).
5. The legacy compat fields (``final_bias`` / ``final_confidence`` /
   ``prediction_summary`` / etc.) are NOT removed by X1.
6. The output never carries trading / hard / forced / required /
   promotion / mutation surfaces.
7. Static check: ``predict.py`` does not import ``services.continuous_smoothing*``.
8. Static check: ``predict.py`` does not import any of the three
   promotion modules.
9. Static check: ``predict.py`` does not import ``services.ai_summary`` —
   X1 keeps the wrapper free of the LLM surface.
10. The ``run_predict`` core result shape from the missing-scan path is
    preserved (PredictResult schema unchanged plus the new metadata).

Design contracts: 06 / 07A / 07C / 07D / 11E / 11H.
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
    """Return a freshly reloaded ``predict`` module.

    ``tests/fixtures/app_analysis_context_fixture.py`` rebinds
    ``predict.run_predict`` to a stripped fake at module-load time and never
    restores it. When that AppTest fixture runs earlier in the pytest
    session, any later test that reads ``predict.run_predict`` would see
    the fake. Reloading the module here re-executes the genuine
    definitions before every X1 boundary check so the contract is
    evaluated against the real wrapper, not the leftover monkeypatch.
    """
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


def _legacy_compat_fields() -> tuple[str, ...]:
    """The PredictResult schema fields that 9+ active importers depend on."""
    return (
        "symbol",
        "predict_timestamp",
        "scan_bias",
        "scan_confidence",
        "research_bias_adjustment",
        "final_bias",
        "final_confidence",
        "open_tendency",
        "close_tendency",
        "prediction_summary",
        "supporting_factors",
        "conflicting_factors",
        "notes",
        "path_risk",
        "peer_path_risk_adjustment",
        "primary_projection",
        "peer_adjustment",
        "final_projection",
    )


class PredictModuleDocLockTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module_path = ROOT / "predict.py"
        self.source = self.module_path.read_text(encoding="utf-8")

    def test_predict_py_marked_as_legacy_wrapper(self) -> None:
        self.assertIn(
            "LEGACY_COMPATIBILITY_WRAPPER",
            self.source,
            msg="predict.py must declare LEGACY_COMPATIBILITY_WRAPPER in module docstring",
        )
        self.assertIn(
            "legacy compatibility wrapper",
            self.source.lower(),
            msg="predict.py docstring must use the phrase 'legacy compatibility wrapper'",
        )

    def test_predict_module_constants_present(self) -> None:
        predict = _fresh_predict_module()

        self.assertTrue(hasattr(predict, "PREDICT_LEGACY_WRAPPER_KIND"))
        self.assertTrue(hasattr(predict, "PREDICT_LEGACY_WRAPPER_VERSION"))
        self.assertEqual(predict.PREDICT_LEGACY_WRAPPER_KIND, "legacy_predict_wrapper")
        self.assertEqual(
            predict.PREDICT_LEGACY_WRAPPER_VERSION,
            "predict_legacy_wrapper.v1",
        )


class PredictRunPredictMetadataTests(unittest.TestCase):
    """Run ``run_predict`` on the missing-scan branch (no DB / network) and
    verify the new metadata is present without changing legacy values."""

    def _run(self) -> dict:
        predict = _fresh_predict_module()
        return predict.run_predict(None, research_result=None, symbol="AVGO")

    def test_run_predict_outputs_legacy_wrapper_metadata(self) -> None:
        result = self._run()
        self.assertEqual(result["wrapper_kind"], "legacy_predict_wrapper")
        self.assertEqual(result["wrapper_version"], "predict_legacy_wrapper.v1")
        self.assertIs(result["legacy_compatibility"], True)

    def test_run_predict_outputs_source_mapping_foundation(self) -> None:
        result = self._run()
        mapping = result.get("source_mapping")
        self.assertIsInstance(mapping, dict)
        # X1 foundation keys per 11E §8 + task spec B step 4.
        for key in (
            "compat_final_bias",
            "compat_final_confidence",
            "compat_prediction_summary",
            "compat_primary_direction",
            "compat_peer_adjustment",
            "compat_path_risk",
        ):
            self.assertIn(
                key,
                mapping,
                msg=f"source_mapping must include foundation key {key!r}",
            )
            self.assertIsInstance(mapping[key], str)
            self.assertTrue(mapping[key], msg=f"source_mapping[{key}] must be non-empty")

    def test_source_mapping_marks_pending_migrations(self) -> None:
        result = self._run()
        mapping = result["source_mapping"]
        # X1 explicitly leaves later stages as pending — no premature
        # promise that the wires already point at confidence_evaluator etc.
        self.assertIn(
            "pending",
            mapping["compat_final_confidence"].lower(),
            msg="compat_final_confidence must be marked pending until X2/X3",
        )
        self.assertIn(
            "pending",
            mapping["compat_prediction_summary"].lower(),
            msg="compat_prediction_summary must be marked pending until X4",
        )

    def test_run_predict_outputs_deprecation_notes(self) -> None:
        result = self._run()
        notes = result.get("deprecation_notes")
        self.assertIsInstance(notes, list)
        self.assertGreater(len(notes), 0)
        joined = " ".join(notes)
        self.assertIn(
            "legacy",
            joined.lower(),
            msg="deprecation_notes should mention 'legacy'",
        )

    def test_run_predict_preserves_legacy_compat_fields(self) -> None:
        result = self._run()
        for field in _legacy_compat_fields():
            self.assertIn(
                field,
                result,
                msg=f"legacy compat field {field!r} must be preserved by X1",
            )

    def test_run_predict_x1_does_not_change_core_shape(self) -> None:
        """The missing-scan path produced ``final_bias=='unavailable'`` and
        ``final_confidence=='low'`` before X1; X1 must not change those
        legacy values."""
        result = self._run()
        self.assertEqual(result["final_bias"], "unavailable")
        self.assertEqual(result["final_confidence"], "low")
        self.assertEqual(result["scan_bias"], "missing")

    def test_run_predict_no_trading_or_hard_fields(self) -> None:
        result = self._run()
        for forbidden in _FORBIDDEN_OUTPUT_FIELDS:
            self.assertNotIn(
                forbidden,
                result,
                msg=f"run_predict result must not contain {forbidden!r}",
            )


class PredictRunPredictWithScanMetadataTests(unittest.TestCase):
    """Same metadata invariants on the populated (computed) branch."""

    def _scan(self) -> dict:
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

    def test_run_predict_metadata_present_on_populated_branch(self) -> None:
        predict = _fresh_predict_module()
        result = predict.run_predict(self._scan(), research_result=None, symbol="AVGO")
        self.assertEqual(result["wrapper_kind"], "legacy_predict_wrapper")
        self.assertEqual(result["wrapper_version"], "predict_legacy_wrapper.v1")
        self.assertIs(result["legacy_compatibility"], True)
        self.assertIn("source_mapping", result)
        self.assertIn("deprecation_notes", result)

    def test_run_predict_no_forbidden_fields_on_populated_branch(self) -> None:
        predict = _fresh_predict_module()
        result = predict.run_predict(self._scan(), research_result=None, symbol="AVGO")
        for forbidden in _FORBIDDEN_OUTPUT_FIELDS:
            self.assertNotIn(forbidden, result)


class PredictModuleStaticImportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module_path = ROOT / "predict.py"
        self.source = self.module_path.read_text(encoding="utf-8")

    def test_predict_py_no_continuous_smoothing_import(self) -> None:
        for forbidden in (
            "from services.continuous_smoothing",
            "import services.continuous_smoothing",
            "import continuous_smoothing",
        ):
            self.assertNotIn(
                forbidden,
                self.source,
                msg=f"predict.py must not import {forbidden!r}",
            )

    def test_predict_py_no_promotion_import(self) -> None:
        for forbidden in (
            "services.active_rule_pool_promotion",
            "services.promotion_adoption_gate",
            "services.promotion_execution_bridge",
        ):
            self.assertNotIn(
                forbidden,
                self.source,
                msg=f"predict.py must not import promotion module {forbidden!r}",
            )

    def test_predict_py_no_ai_summary_import(self) -> None:
        # Per 11E §10.1 / 11F: the legacy wrapper must not pull the AI
        # summary surface into the active path. ai_summary is opt-in only.
        for forbidden in (
            "from services.ai_summary",
            "import services.ai_summary",
        ):
            self.assertNotIn(
                forbidden,
                self.source,
                msg=f"predict.py must not import {forbidden!r}",
            )


if __name__ == "__main__":
    unittest.main()
