"""Contract enforcement tests for Step 12E-X4-B (predict.py explicit
``v2_payload`` opt-in adapter wiring).

X4-B adds an optional ``v2_payload`` kwarg to ``run_predict``. When the
caller passes ``None`` (or omits it), the wrapper preserves its X3
legacy baseline byte-for-byte. When the caller passes a dict, the
wrapper invokes ``services.predict_legacy_adapter.adapt_v2_payload_to_predict_legacy``
to overlay the allowlisted compatibility fields and surfaces
``v2_adapter_used`` / ``v2_adapter_result`` metadata. The wrapper itself
does NOT pull V2 — it never calls the V2 orchestrator, the final
decision builder, the confidence evaluator, the LLM, or any I/O surface.

Pinned contract:

1. ``v2_payload=None`` -> the legacy baseline (X3 output) is preserved
   in every key the test compares.
2. ``v2_payload=<dict>`` -> the adapter is invoked exactly once and its
   ``legacy_fields`` are projected onto the wrapper output for every
   allowlist key.
3. ``v2_adapter_used`` is True only when a dict was passed.
4. ``v2_adapter_result`` carries adapter metadata + source_mapping +
   warnings (but NOT the full ``legacy_fields`` block — that's already
   merged into the top-level result).
5. The top-level ``source_mapping`` entries for overlaid compat keys are
   replaced with the adapter's dict entries.
6. Non-dict ``v2_payload`` does not raise, does not overlay, and surfaces
   a ``v2_adapter_used = False`` plus a warning entry.
7. Forbidden output fields (trading / hard / forced / required /
   promotion / mutation) never leak in.
8. Static checks: ``predict.py`` does not import the V2 orchestrator,
   the final decision builder, the confidence evaluator, ai_summary,
   promotion modules, or continuous_smoothing.
9. The overlay does not mutate the input ``v2_payload``.

Design contracts: 07A / 07C / 07D / 11E §7 X4 / 11H.
"""

from __future__ import annotations

import ast
import copy
import importlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _fresh_predict_module():
    """Reload ``predict`` to defeat the ``app_analysis_context_fixture``
    monkeypatch that replaces ``predict.run_predict`` during AppTest
    runs (see X1/X2/X3 boundary test files for the same workaround)."""
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


_OVERLAY_KEYS = (
    "final_bias",
    "direction",
    "final_confidence",
    "confidence",
    "prediction_summary",
    "summary",
    "primary_projection",
    "peer_adjustment",
    "final_projection",
    "path_risk",
    "supporting_factors",
    "conflicting_factors",
    "scan_bias",
    "open_tendency",
    "close_tendency",
    "pred_open",
    "pred_path",
    "pred_close",
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


def _v2_payload_full() -> dict:
    """A V2 payload that exercises every priority-1 adapter path."""
    return {
        "kind": "projection_v2_report",
        "symbol": "AVGO",
        "ready": True,
        "main_projection": {
            "kind": "main_projection_layer",
            "ready": True,
            "predicted_top1": {"state": "小涨", "probability": 0.42},
        },
        "primary_analysis": {
            "kind": "primary_20day_analysis",
            "ready": True,
            "direction": "偏多",
            "confidence": "medium",
            "summary": "primary 偏多",
        },
        "peer_adjustment": {
            "kind": "peer_adjustment",
            "ready": True,
            "adjustment": "reinforce_bullish",
            "adjusted_direction": "偏多",
        },
        "final_decision": {
            "kind": "final_decision",
            "ready": True,
            "final_direction": "偏多",
            "direction": "偏多",
            "final_confidence": "unknown",
            "risk_level": "medium",
            "summary": "v2 final decision summary text",
            "decision_factors": {
                "supporting": ["primary 偏多", "peer reinforce bullish"],
                "conflicting": ["v2 conflict reminder"],
            },
        },
        "confidence_result": {
            "schema_version": "confidence_system_result.v1",
            "ready": True,
            "combined_confidence": {"level": "high"},
            "agreement_status": "aligned",
            "conflict_level": "none",
        },
        "final_report": {
            "schema_version": "final_report_aggregator_result.v1",
            "combined_user_summary": "明日基准判断：偏多。综合三系统输出。",
        },
    }


# ---------------------------------------------------------------------------
# Default (legacy) path: v2_payload=None preserves X3 baseline
# ---------------------------------------------------------------------------


class V2PayloadNoneLegacyBaselineTests(unittest.TestCase):
    def test_run_predict_v2_payload_none_does_not_call_adapter(self) -> None:
        """When the caller does not pass ``v2_payload``, the wrapper
        must not invoke the adapter. We verify this by monkeypatching
        ``adapt_v2_payload_to_predict_legacy`` to raise; if the wrapper
        had called it on the None path the test would fail."""
        predict = _fresh_predict_module()

        def _explode(*args, **kwargs):
            raise AssertionError("adapter must not be called when v2_payload is None")

        original = predict.adapt_v2_payload_to_predict_legacy
        predict.adapt_v2_payload_to_predict_legacy = _explode  # type: ignore[assignment]
        try:
            result = predict.run_predict(_scan(), research_result=None, symbol="AVGO")
        finally:
            predict.adapt_v2_payload_to_predict_legacy = original  # type: ignore[assignment]
        # Path was reachable -> adapter was not invoked.
        self.assertFalse(result.get("v2_adapter_used", False))
        self.assertNotIn("v2_adapter_result", result)

    def test_run_predict_v2_payload_none_preserves_legacy_baseline(self) -> None:
        """Compare the legacy keys of an X3 baseline call (no v2_payload)
        against an X3 baseline call with explicit None — they must be
        identical for every legacy compat key."""
        predict = _fresh_predict_module()
        baseline = predict.run_predict(_scan(), research_result=None, symbol="AVGO")
        with_explicit_none = predict.run_predict(
            _scan(),
            research_result=None,
            symbol="AVGO",
            v2_payload=None,
        )
        for key in _OVERLAY_KEYS:
            self.assertEqual(
                baseline.get(key),
                with_explicit_none.get(key),
                msg=f"X3 baseline {key!r} must match v2_payload=None call",
            )
        # Wrapper-metadata keys also identical.
        for meta in (
            "wrapper_kind",
            "wrapper_version",
            "legacy_compatibility",
            "deprecation_notes",
        ):
            self.assertEqual(baseline[meta], with_explicit_none[meta])
        # source_mapping is the X3 string-valued mapping (not the adapter's
        # dict-valued mapping) on both calls.
        self.assertEqual(baseline["source_mapping"], with_explicit_none["source_mapping"])


# ---------------------------------------------------------------------------
# Valid-dict path: overlay applies
# ---------------------------------------------------------------------------


class V2PayloadDictOverlayTests(unittest.TestCase):
    def test_run_predict_valid_v2_payload_calls_adapter(self) -> None:
        predict = _fresh_predict_module()
        seen: list[dict] = []
        original = predict.adapt_v2_payload_to_predict_legacy

        def _spy(v2_payload, **kwargs):
            seen.append(copy.deepcopy(v2_payload))
            return original(v2_payload, **kwargs)

        predict.adapt_v2_payload_to_predict_legacy = _spy  # type: ignore[assignment]
        try:
            predict.run_predict(
                _scan(),
                research_result=None,
                symbol="AVGO",
                v2_payload=_v2_payload_full(),
            )
        finally:
            predict.adapt_v2_payload_to_predict_legacy = original  # type: ignore[assignment]
        self.assertEqual(len(seen), 1, msg="adapter must be called exactly once")

    def test_run_predict_v2_payload_overlays_direction_confidence_summary(self) -> None:
        predict = _fresh_predict_module()
        result = predict.run_predict(
            _scan(),
            research_result=None,
            symbol="AVGO",
            v2_payload=_v2_payload_full(),
        )
        # Direction / final_bias come from final_decision.final_direction.
        self.assertEqual(result["final_bias"], "偏多")
        self.assertEqual(result["direction"], "偏多")
        # Confidence comes from confidence_result.combined_confidence.level.
        self.assertEqual(result["final_confidence"], "high")
        self.assertEqual(result["confidence"], "high")
        # Summary comes from final_report.combined_user_summary.
        self.assertEqual(
            result["prediction_summary"],
            "明日基准判断：偏多。综合三系统输出。",
        )
        self.assertEqual(result["summary"], result["prediction_summary"])

    def test_run_predict_v2_payload_overlays_projection_blocks(self) -> None:
        predict = _fresh_predict_module()
        v2 = _v2_payload_full()
        result = predict.run_predict(
            _scan(),
            research_result=None,
            symbol="AVGO",
            v2_payload=v2,
        )
        self.assertEqual(result["primary_projection"], v2["primary_analysis"])
        self.assertEqual(result["peer_adjustment"], v2["peer_adjustment"])
        # final_projection field is absent in v2 -> adapter falls back to
        # final_decision display block.
        self.assertEqual(result["final_projection"], v2["final_decision"])
        # path_risk wrapped from final_decision.risk_level.
        self.assertEqual(result["path_risk"], {"risk_level": "medium"})

    def test_run_predict_v2_payload_overlays_factors_and_path_fields(self) -> None:
        predict = _fresh_predict_module()
        v2 = _v2_payload_full()
        result = predict.run_predict(
            _scan(),
            research_result=None,
            symbol="AVGO",
            v2_payload=v2,
        )
        self.assertEqual(
            result["supporting_factors"],
            v2["final_decision"]["decision_factors"]["supporting"],
        )
        self.assertEqual(
            result["conflicting_factors"],
            v2["final_decision"]["decision_factors"]["conflicting"],
        )
        # scan/path display fields are not surfaced by V2 -> they fall
        # back to the wrapper's pre-overlay value (which IS a valid
        # legacy fallback for the adapter).
        for field in (
            "scan_bias",
            "open_tendency",
            "close_tendency",
            "pred_open",
            "pred_path",
            "pred_close",
        ):
            self.assertIn(field, result)


class V2AdapterMetadataTests(unittest.TestCase):
    def test_run_predict_v2_adapter_metadata_present(self) -> None:
        predict = _fresh_predict_module()
        result = predict.run_predict(
            _scan(),
            research_result=None,
            symbol="AVGO",
            v2_payload=_v2_payload_full(),
        )
        self.assertIs(result["v2_adapter_used"], True)
        self.assertIn("v2_adapter_result", result)
        meta = result["v2_adapter_result"]
        self.assertEqual(meta["adapter_kind"], "v2_to_predict_legacy_adapter")
        self.assertEqual(meta["adapter_version"], "v2_to_predict_legacy_adapter.v1")
        self.assertEqual(meta["source"], "v2_payload")
        self.assertIn("source_mapping", meta)
        self.assertIn("warnings", meta)
        # ``legacy_fields`` is the bulk overlay payload — already merged
        # into the wrapper top-level — so it must NOT be duplicated under
        # ``v2_adapter_result`` to avoid bloating the response.
        self.assertNotIn("legacy_fields", meta)

    def test_run_predict_v2_adapter_source_mapping_merged(self) -> None:
        predict = _fresh_predict_module()
        result = predict.run_predict(
            _scan(),
            research_result=None,
            symbol="AVGO",
            v2_payload=_v2_payload_full(),
        )
        # When overlay is active, the wrapper's top-level source_mapping
        # entries for overlaid keys are replaced with the adapter's dict
        # entries (per spec: "顶层 source_mapping 中被 overlay 的 compat_*
        # 字段应该更新为 adapter 的 source_mapping").
        mapping = result["source_mapping"]
        for key in (
            "compat_final_bias",
            "compat_final_confidence",
            "compat_prediction_summary",
        ):
            entry = mapping[key]
            self.assertIsInstance(entry, dict)
            for sub in ("legacy_field", "source_path", "fallback_used", "notes"):
                self.assertIn(sub, entry)
        # The adapter's full source_mapping is also available under
        # ``v2_adapter_result.source_mapping`` for full audit.
        self.assertIn("compat_final_bias", result["v2_adapter_result"]["source_mapping"])


# ---------------------------------------------------------------------------
# Invalid v2_payload: degrade safely
# ---------------------------------------------------------------------------


class V2PayloadInvalidTests(unittest.TestCase):
    def test_run_predict_invalid_v2_payload_does_not_overlay(self) -> None:
        predict = _fresh_predict_module()
        for bogus in ("not-a-dict", 123, [1, 2, 3], 1.5):
            result = predict.run_predict(
                _scan(),
                research_result=None,
                symbol="AVGO",
                v2_payload=bogus,  # type: ignore[arg-type]
            )
            self.assertIs(result["v2_adapter_used"], False)
            # Wrapper still surfaces a warning so the audit trail is
            # explicit.
            warnings_blob = (
                result.get("v2_adapter_warnings", [])
                + result.get("warnings", [])
            )
            joined = " ".join(str(w) for w in warnings_blob)
            self.assertIn("v2_payload", joined.lower())

    def test_run_predict_invalid_v2_payload_preserves_legacy_baseline(self) -> None:
        predict = _fresh_predict_module()
        baseline = predict.run_predict(_scan(), research_result=None, symbol="AVGO")
        with_bogus = predict.run_predict(
            _scan(),
            research_result=None,
            symbol="AVGO",
            v2_payload="bogus",  # type: ignore[arg-type]
        )
        for key in _OVERLAY_KEYS:
            self.assertEqual(
                baseline.get(key),
                with_bogus.get(key),
                msg=f"invalid v2_payload must not change {key!r}",
            )


# ---------------------------------------------------------------------------
# Forbidden imports + forbidden output fields
# ---------------------------------------------------------------------------


class StaticImportReaffirmedTests(unittest.TestCase):
    """X4-B static guards.

    The wrapper's existing lazy import of ``services.projection_orchestrator_v2``
    inside ``_build_projection_three_systems_attachment`` (the re-entry-
    guarded attachment helper added in Task 104) is NOT in scope for X4-B
    — it pre-dates X4-B and is gated by ``_projection_three_systems_attachment_state``.
    The X4-B contract is that the wrapper must not introduce a NEW
    *module-level* import of the V2 orchestrator / final decision builder
    / confidence evaluator / ai_summary / promotion / continuous_smoothing
    surfaces. Lazy imports inside the existing attachment helper stay
    legal until X5 cleans them up.

    These tests AST-parse predict.py and only flag module-level
    Import / ImportFrom nodes, which is the contract level the X4-B
    wiring is supposed to respect.
    """

    def setUp(self) -> None:
        self.source = (ROOT / "predict.py").read_text(encoding="utf-8")
        self.tree = ast.parse(self.source)

    def _module_level_imports(self) -> list[str]:
        modules: list[str] = []
        for node in self.tree.body:
            if isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    modules.append(node.module)
        return modules

    def test_run_predict_x4b_no_forbidden_imports(self) -> None:
        forbidden_modules = {
            "services.projection_orchestrator_v2",
            "services.projection_orchestrator",
            "services.final_decision",
            "services.confidence_evaluator",
            "services.ai_summary",
            "services.active_rule_pool_promotion",
            "services.promotion_adoption_gate",
            "services.promotion_execution_bridge",
            "services.continuous_smoothing",
            "services.continuous_smoothing_candidate",
            "services.continuous_smoothing_candidate_v2",
            "continuous_smoothing",
        }
        offenders = [m for m in self._module_level_imports() if m in forbidden_modules]
        self.assertEqual(
            offenders,
            [],
            msg=f"predict.py module-level imports must not include {forbidden_modules!r}; offenders={offenders!r}",
        )

    def test_run_predict_x4b_imports_adapter_only(self) -> None:
        # The X4-B wiring is allowed to import the standalone adapter
        # (X4-A) — it carries no active-path edges.
        self.assertIn(
            "services.predict_legacy_adapter",
            self._module_level_imports(),
            msg="predict.py must import the X4-A adapter for the v2_payload path",
        )


class V2PayloadForbiddenFieldsTests(unittest.TestCase):
    def test_run_predict_x4b_no_forbidden_fields(self) -> None:
        predict = _fresh_predict_module()
        for v2 in (
            None,
            _v2_payload_full(),
            "not-a-dict",
            123,
        ):
            result = predict.run_predict(
                _scan(),
                research_result=None,
                symbol="AVGO",
                v2_payload=v2,  # type: ignore[arg-type]
            )
            for forbidden in _FORBIDDEN_OUTPUT_FIELDS:
                self.assertNotIn(
                    forbidden, result, msg=f"top-level: {forbidden!r}"
                )


# ---------------------------------------------------------------------------
# Mutation
# ---------------------------------------------------------------------------


class V2PayloadNoMutationTests(unittest.TestCase):
    def test_run_predict_x4b_does_not_mutate_v2_payload(self) -> None:
        predict = _fresh_predict_module()
        v2 = _v2_payload_full()
        snap = copy.deepcopy(v2)
        predict.run_predict(_scan(), research_result=None, symbol="AVGO", v2_payload=v2)
        self.assertEqual(v2, snap)


# ---------------------------------------------------------------------------
# Missing-scan + v2_payload combo
# ---------------------------------------------------------------------------


class V2PayloadMissingScanTests(unittest.TestCase):
    def test_missing_scan_with_v2_payload_overlays(self) -> None:
        """The missing-scan path must also honour an explicit
        ``v2_payload``. Direction-side stays "unavailable" only when no
        v2_payload is supplied; with a valid v2_payload the wrapper
        overlays the adapter's legacy_fields just like the populated
        path."""
        predict = _fresh_predict_module()
        result = predict.run_predict(
            None,
            research_result=None,
            symbol="AVGO",
            v2_payload=_v2_payload_full(),
        )
        self.assertEqual(result["final_bias"], "偏多")
        self.assertEqual(result["final_confidence"], "high")
        self.assertEqual(
            result["prediction_summary"],
            "明日基准判断：偏多。综合三系统输出。",
        )
        self.assertIs(result["v2_adapter_used"], True)

    def test_missing_scan_without_v2_payload_unchanged(self) -> None:
        predict = _fresh_predict_module()
        result = predict.run_predict(None, research_result=None, symbol="AVGO")
        # X1/X2/X3 baseline for missing-scan path.
        self.assertEqual(result["final_bias"], "unavailable")
        self.assertEqual(result["final_confidence"], "unknown")
        self.assertEqual(result["scan_bias"], "missing")
        self.assertFalse(result.get("v2_adapter_used", False))


if __name__ == "__main__":
    unittest.main()
