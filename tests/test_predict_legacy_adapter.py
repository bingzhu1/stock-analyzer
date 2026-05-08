"""Contract enforcement tests for Step 12E-X4-A (V2 → predict.py legacy
compatibility adapter).

X4-A is a STANDALONE pure-function adapter that maps a V2 payload to the
``PredictResult``-style legacy compatibility surface. It does NOT modify
``run_predict``'s default execution path, does NOT compute new judgments,
and does NOT touch any active service. The adapter is consumed only when
a caller explicitly invokes it; ``predict.run_predict`` is unchanged.

Pinned contract:

1. Output schema is fixed: ``adapter_kind`` / ``adapter_version`` /
   ``source`` / ``legacy_fields`` / ``source_mapping`` / ``warnings`` /
   ``non_mutation_confirmations``.
2. ``legacy_fields`` includes the full PredictResult-style surface.
3. ``source_mapping`` covers every ``legacy_fields`` key with a
   ``{legacy_field, source_path, fallback_used, notes}`` entry.
4. The adapter never mutates ``v2_payload`` / ``fallback_legacy_payload``.
5. Per-field priority chains follow X4-A §D exactly.
6. Forbidden fields never leak into the top-level dict or
   ``legacy_fields``.
7. Static checks: no LLM / promotion / continuous_smoothing /
   run_predict / V2 orchestrator / final_decision / confidence_evaluator
   / DB / file I/O imports; no calls to those surfaces.
8. The adapter is deterministic for the same inputs.

Design contracts: 07A / 07C / 07D / 11E §7 X4 / 11H.
"""

from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


_FORBIDDEN_FIELDS = (
    "hard_exclusion",
    "forced_exclusion",
    "required_decision",
    "trading_action",
    "buy",
    "sell",
    "hold",
    "simulated_trade",
    "no_trade",
    "production_promotion",
    "_PROTECTION_LAYER_CONNECTED",
    "modified_projection",
    "modified_exclusion",
    "modified_confidence",
    "corrected_confidence",
    "final_report_mutation",
)

_REQUIRED_LEGACY_FIELDS = (
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

_REQUIRED_MAPPING_KEYS = (
    "compat_final_bias",
    "compat_direction",
    "compat_final_confidence",
    "compat_confidence",
    "compat_prediction_summary",
    "compat_summary",
    "compat_primary_projection",
    "compat_peer_adjustment",
    "compat_final_projection",
    "compat_path_risk",
    "compat_supporting_factors",
    "compat_conflicting_factors",
    "compat_scan_bias",
    "compat_open_tendency",
    "compat_close_tendency",
    "compat_pred_open",
    "compat_pred_path",
    "compat_pred_close",
)


def _v2_full() -> dict:
    """A V2 payload that exercises every priority-1 source path."""
    return {
        "kind": "projection_v2_report",
        "symbol": "AVGO",
        "ready": True,
        "main_projection": {
            "kind": "main_projection_layer",
            "ready": True,
            "predicted_top1": {"state": "小涨", "probability": 0.42},
            "predicted_top2": {"state": "震荡", "probability": 0.28},
            "state_probabilities": {
                "大涨": 0.10,
                "小涨": 0.42,
                "震荡": 0.28,
                "小跌": 0.15,
                "大跌": 0.05,
            },
        },
        "exclusion_result": {
            "excluded": False,
            "triggered_rule": None,
            "peer_alignment": {"alignment": "neutral", "available_peer_count": 3},
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
            "adjusted_confidence": "high",
        },
        "historical_probability": {
            "kind": "historical_probability",
            "ready": True,
            "impact": "support",
        },
        "consistency": {"consistency_flag": "consistent"},
        "final_decision": {
            "kind": "final_decision",
            "ready": True,
            "final_direction": "偏多",
            "direction": "偏多",
            "final_confidence": "unknown",
            "confidence": "unknown",
            "risk_level": "unknown",
            "summary": "v2 final decision summary text",
            "decision_factors": {
                "supporting": ["primary 偏多", "peer reinforce bullish"],
                "conflicting": [],
            },
        },
        "confidence_result": {
            "schema_version": "confidence_system_result.v1",
            "ready": True,
            "combined_confidence": {"level": "medium"},
            "agreement_status": "aligned",
            "conflict_level": "none",
        },
        "final_report": {
            "schema_version": "final_report_aggregator_result.v1",
            "combined_user_summary": "明日基准判断：偏多。综合三系统输出。",
        },
    }


def _legacy_fallback() -> dict:
    """A fallback PredictResult-style payload exercising compat keys not
    surfaced by the V2 chain (scan/path display fields)."""
    return {
        "final_bias": "fallback_bullish",
        "direction": "fallback_direction",
        "final_confidence": "low",
        "confidence": "low",
        "prediction_summary": "fallback summary",
        "summary": "fallback summary",
        "primary_projection": {"fallback": True, "kind": "primary_legacy"},
        "peer_adjustment": {"fallback": True, "kind": "peer_legacy"},
        "final_projection": {"fallback": True, "kind": "final_legacy"},
        "path_risk": {"fallback": True, "risk_level": "medium"},
        "supporting_factors": ["fallback support"],
        "conflicting_factors": ["fallback conflict"],
        "scan_bias": "fallback_scan",
        "open_tendency": "fallback_open",
        "close_tendency": "fallback_close",
        "pred_open": "fallback_pred_open",
        "pred_path": "fallback_pred_path",
        "pred_close": "fallback_pred_close",
    }


# ---------------------------------------------------------------------------
# Schema + completeness tests
# ---------------------------------------------------------------------------


class AdapterSchemaTests(unittest.TestCase):
    def test_adapter_schema(self) -> None:
        from services.predict_legacy_adapter import adapt_v2_payload_to_predict_legacy

        result = adapt_v2_payload_to_predict_legacy(_v2_full())
        for key in (
            "adapter_kind",
            "adapter_version",
            "source",
            "legacy_fields",
            "source_mapping",
            "warnings",
            "non_mutation_confirmations",
        ):
            self.assertIn(key, result)
        self.assertEqual(result["adapter_kind"], "v2_to_predict_legacy_adapter")
        self.assertEqual(result["adapter_version"], "v2_to_predict_legacy_adapter.v1")
        self.assertEqual(result["source"], "v2_payload")
        self.assertIsInstance(result["legacy_fields"], dict)
        self.assertIsInstance(result["source_mapping"], dict)
        self.assertIsInstance(result["warnings"], list)
        self.assertEqual(
            result["non_mutation_confirmations"],
            {
                "v2_payload_mutated": False,
                "fallback_legacy_payload_mutated": False,
            },
        )
        # Adapter MUST NOT carry wrapper-level metadata (that belongs to
        # predict.py, not the adapter).
        for forbidden_meta in (
            "wrapper_kind",
            "wrapper_version",
            "legacy_compatibility",
            "deprecation_notes",
        ):
            self.assertNotIn(forbidden_meta, result)

    def test_adapter_legacy_fields_complete(self) -> None:
        from services.predict_legacy_adapter import adapt_v2_payload_to_predict_legacy

        result = adapt_v2_payload_to_predict_legacy(_v2_full())
        for field in _REQUIRED_LEGACY_FIELDS:
            self.assertIn(
                field,
                result["legacy_fields"],
                msg=f"legacy_fields missing required key {field!r}",
            )

    def test_adapter_source_mapping_complete(self) -> None:
        from services.predict_legacy_adapter import adapt_v2_payload_to_predict_legacy

        result = adapt_v2_payload_to_predict_legacy(_v2_full())
        mapping = result["source_mapping"]
        for key in _REQUIRED_MAPPING_KEYS:
            self.assertIn(key, mapping, msg=f"source_mapping missing {key!r}")
            entry = mapping[key]
            self.assertIsInstance(entry, dict)
            for sub in ("legacy_field", "source_path", "fallback_used", "notes"):
                self.assertIn(sub, entry, msg=f"{key}.{sub} missing")
            self.assertIsInstance(entry["source_path"], str)
            self.assertTrue(entry["source_path"], msg=f"{key}.source_path empty")
            self.assertIsInstance(entry["fallback_used"], bool)


# ---------------------------------------------------------------------------
# Non-mutation
# ---------------------------------------------------------------------------


class AdapterNoMutationTests(unittest.TestCase):
    def test_adapter_does_not_mutate_inputs(self) -> None:
        from services.predict_legacy_adapter import adapt_v2_payload_to_predict_legacy

        v2 = _v2_full()
        fb = _legacy_fallback()
        v2_snap = copy.deepcopy(v2)
        fb_snap = copy.deepcopy(fb)
        adapt_v2_payload_to_predict_legacy(v2, fallback_legacy_payload=fb)
        self.assertEqual(v2, v2_snap)
        self.assertEqual(fb, fb_snap)


# ---------------------------------------------------------------------------
# Direction priority chain
# ---------------------------------------------------------------------------


class AdapterDirectionTests(unittest.TestCase):
    def test_adapter_direction_from_final_decision(self) -> None:
        from services.predict_legacy_adapter import adapt_v2_payload_to_predict_legacy

        result = adapt_v2_payload_to_predict_legacy(_v2_full())
        legacy = result["legacy_fields"]
        self.assertEqual(legacy["final_bias"], "偏多")
        self.assertEqual(legacy["direction"], "偏多")
        mapping = result["source_mapping"]
        self.assertEqual(
            mapping["compat_final_bias"]["source_path"],
            "v2_payload.final_decision.final_direction",
        )
        self.assertFalse(mapping["compat_final_bias"]["fallback_used"])

    def test_adapter_direction_from_main_projection_fallback(self) -> None:
        """When final_decision.final_direction / direction are absent, the
        adapter should fall back to main_projection.predicted_top1.state
        and surface a warning."""
        from services.predict_legacy_adapter import adapt_v2_payload_to_predict_legacy

        v2 = _v2_full()
        v2["final_decision"].pop("final_direction", None)
        v2["final_decision"].pop("direction", None)
        result = adapt_v2_payload_to_predict_legacy(v2)
        legacy = result["legacy_fields"]
        self.assertEqual(legacy["final_bias"], "小涨")
        self.assertEqual(legacy["direction"], "小涨")
        mapping = result["source_mapping"]
        self.assertEqual(
            mapping["compat_final_bias"]["source_path"],
            "v2_payload.main_projection.predicted_top1.state",
        )
        # The X4-A spec marks this as "fallback used" because final_decision
        # was the priority-1 source and we had to walk further.
        self.assertTrue(mapping["compat_final_bias"]["fallback_used"])
        joined = " ".join(result["warnings"])
        self.assertIn("main_projection", joined)

    def test_adapter_direction_from_fallback_payload(self) -> None:
        from services.predict_legacy_adapter import adapt_v2_payload_to_predict_legacy

        v2 = {"kind": "projection_v2_report"}  # nothing usable
        result = adapt_v2_payload_to_predict_legacy(
            v2, fallback_legacy_payload=_legacy_fallback()
        )
        legacy = result["legacy_fields"]
        self.assertEqual(legacy["final_bias"], "fallback_bullish")
        self.assertEqual(legacy["direction"], "fallback_bullish")
        mapping = result["source_mapping"]
        self.assertTrue(mapping["compat_final_bias"]["source_path"].startswith(
            "fallback_legacy_payload."
        ))
        self.assertTrue(mapping["compat_final_bias"]["fallback_used"])

    def test_adapter_direction_default_unknown(self) -> None:
        from services.predict_legacy_adapter import adapt_v2_payload_to_predict_legacy

        result = adapt_v2_payload_to_predict_legacy({}, fallback_legacy_payload={})
        legacy = result["legacy_fields"]
        self.assertEqual(legacy["final_bias"], "unknown")
        self.assertEqual(legacy["direction"], "unknown")
        mapping = result["source_mapping"]
        self.assertEqual(
            mapping["compat_final_bias"]["source_path"],
            "adapter.default.unknown",
        )


# ---------------------------------------------------------------------------
# Confidence priority chain
# ---------------------------------------------------------------------------


class AdapterConfidenceTests(unittest.TestCase):
    def test_adapter_confidence_from_confidence_result(self) -> None:
        from services.predict_legacy_adapter import adapt_v2_payload_to_predict_legacy

        result = adapt_v2_payload_to_predict_legacy(_v2_full())
        legacy = result["legacy_fields"]
        self.assertEqual(legacy["final_confidence"], "medium")
        self.assertEqual(legacy["confidence"], "medium")
        mapping = result["source_mapping"]
        self.assertEqual(
            mapping["compat_final_confidence"]["source_path"],
            "v2_payload.confidence_result.combined_confidence.level",
        )
        self.assertFalse(mapping["compat_final_confidence"]["fallback_used"])

    def test_adapter_confidence_from_final_decision_fallback(self) -> None:
        from services.predict_legacy_adapter import adapt_v2_payload_to_predict_legacy

        v2 = _v2_full()
        v2.pop("confidence_result", None)
        v2["final_decision"]["final_confidence"] = "high"
        result = adapt_v2_payload_to_predict_legacy(v2)
        legacy = result["legacy_fields"]
        self.assertEqual(legacy["final_confidence"], "high")
        self.assertEqual(legacy["confidence"], "high")
        mapping = result["source_mapping"]
        self.assertEqual(
            mapping["compat_final_confidence"]["source_path"],
            "v2_payload.final_decision.final_confidence",
        )
        self.assertTrue(mapping["compat_final_confidence"]["fallback_used"])
        joined = " ".join(result["warnings"])
        self.assertIn("final_decision", joined)

    def test_adapter_invalid_confidence_unknown(self) -> None:
        """Levels outside {low,medium,high,unknown} normalise to unknown."""
        from services.predict_legacy_adapter import adapt_v2_payload_to_predict_legacy

        for bogus in ("super_high", "", None, 1.0, [], {}):
            v2 = _v2_full()
            v2["confidence_result"]["combined_confidence"]["level"] = bogus
            result = adapt_v2_payload_to_predict_legacy(v2)
            self.assertEqual(
                result["legacy_fields"]["final_confidence"],
                "unknown",
                msg=f"bogus level {bogus!r} must degrade to unknown",
            )
            self.assertEqual(result["legacy_fields"]["confidence"], "unknown")


# ---------------------------------------------------------------------------
# Summary priority chain
# ---------------------------------------------------------------------------


class AdapterSummaryTests(unittest.TestCase):
    def test_adapter_summary_from_final_report(self) -> None:
        from services.predict_legacy_adapter import adapt_v2_payload_to_predict_legacy

        result = adapt_v2_payload_to_predict_legacy(_v2_full())
        legacy = result["legacy_fields"]
        self.assertEqual(
            legacy["prediction_summary"],
            "明日基准判断：偏多。综合三系统输出。",
        )
        self.assertEqual(legacy["summary"], legacy["prediction_summary"])
        mapping = result["source_mapping"]
        self.assertEqual(
            mapping["compat_prediction_summary"]["source_path"],
            "v2_payload.final_report.combined_user_summary",
        )
        self.assertFalse(mapping["compat_prediction_summary"]["fallback_used"])

    def test_adapter_summary_from_final_decision_fallback(self) -> None:
        from services.predict_legacy_adapter import adapt_v2_payload_to_predict_legacy

        v2 = _v2_full()
        v2.pop("final_report", None)
        result = adapt_v2_payload_to_predict_legacy(v2)
        legacy = result["legacy_fields"]
        self.assertEqual(legacy["prediction_summary"], "v2 final decision summary text")
        self.assertEqual(legacy["summary"], "v2 final decision summary text")
        mapping = result["source_mapping"]
        self.assertEqual(
            mapping["compat_prediction_summary"]["source_path"],
            "v2_payload.final_decision.summary",
        )
        self.assertTrue(mapping["compat_prediction_summary"]["fallback_used"])

    def test_adapter_summary_from_fallback_payload(self) -> None:
        from services.predict_legacy_adapter import adapt_v2_payload_to_predict_legacy

        v2 = {"kind": "projection_v2_report"}
        result = adapt_v2_payload_to_predict_legacy(
            v2, fallback_legacy_payload=_legacy_fallback()
        )
        legacy = result["legacy_fields"]
        self.assertEqual(legacy["prediction_summary"], "fallback summary")
        self.assertEqual(legacy["summary"], "fallback summary")

    def test_adapter_summary_default_empty(self) -> None:
        from services.predict_legacy_adapter import adapt_v2_payload_to_predict_legacy

        result = adapt_v2_payload_to_predict_legacy({}, fallback_legacy_payload={})
        legacy = result["legacy_fields"]
        self.assertEqual(legacy["prediction_summary"], "")
        self.assertEqual(legacy["summary"], "")
        self.assertEqual(
            result["source_mapping"]["compat_prediction_summary"]["source_path"],
            "adapter.default.empty",
        )


# ---------------------------------------------------------------------------
# Projection / peer / final / path blocks
# ---------------------------------------------------------------------------


class AdapterProjectionBlocksTests(unittest.TestCase):
    def test_adapter_projection_blocks_from_v2_payload(self) -> None:
        from services.predict_legacy_adapter import adapt_v2_payload_to_predict_legacy

        v2 = _v2_full()
        result = adapt_v2_payload_to_predict_legacy(v2)
        legacy = result["legacy_fields"]
        # primary_projection should come from primary_analysis (priority 1).
        self.assertEqual(legacy["primary_projection"], v2["primary_analysis"])
        # peer_adjustment from V2 peer_adjustment (priority 1).
        self.assertEqual(legacy["peer_adjustment"], v2["peer_adjustment"])
        # final_projection: when final_projection key is absent, fall back
        # to final_decision display block (priority 2).
        self.assertEqual(legacy["final_projection"], v2["final_decision"])

    def test_adapter_primary_projection_main_projection_fallback(self) -> None:
        from services.predict_legacy_adapter import adapt_v2_payload_to_predict_legacy

        v2 = _v2_full()
        v2.pop("primary_analysis", None)
        result = adapt_v2_payload_to_predict_legacy(v2)
        self.assertEqual(
            result["legacy_fields"]["primary_projection"], v2["main_projection"]
        )
        self.assertEqual(
            result["source_mapping"]["compat_primary_projection"]["source_path"],
            "v2_payload.main_projection",
        )

    def test_adapter_path_risk_from_path_risk_field(self) -> None:
        from services.predict_legacy_adapter import adapt_v2_payload_to_predict_legacy

        v2 = _v2_full()
        v2["path_risk"] = {"risk_level": "low", "notes": "v2 path_risk block"}
        result = adapt_v2_payload_to_predict_legacy(v2)
        self.assertEqual(result["legacy_fields"]["path_risk"], v2["path_risk"])
        self.assertEqual(
            result["source_mapping"]["compat_path_risk"]["source_path"],
            "v2_payload.path_risk",
        )

    def test_adapter_path_risk_from_final_decision_risk_level(self) -> None:
        from services.predict_legacy_adapter import adapt_v2_payload_to_predict_legacy

        v2 = _v2_full()
        v2["final_decision"]["risk_level"] = "medium"
        result = adapt_v2_payload_to_predict_legacy(v2)
        self.assertEqual(result["legacy_fields"]["path_risk"], {"risk_level": "medium"})
        self.assertEqual(
            result["source_mapping"]["compat_path_risk"]["source_path"],
            "v2_payload.final_decision.risk_level",
        )

    def test_adapter_supporting_factors_from_decision_factors(self) -> None:
        from services.predict_legacy_adapter import adapt_v2_payload_to_predict_legacy

        v2 = _v2_full()
        result = adapt_v2_payload_to_predict_legacy(v2)
        self.assertEqual(
            result["legacy_fields"]["supporting_factors"],
            v2["final_decision"]["decision_factors"]["supporting"],
        )
        self.assertEqual(
            result["legacy_fields"]["conflicting_factors"],
            v2["final_decision"]["decision_factors"]["conflicting"],
        )

    def test_adapter_supporting_factors_from_legacy_lists(self) -> None:
        from services.predict_legacy_adapter import adapt_v2_payload_to_predict_legacy

        v2 = _v2_full()
        v2["final_decision"].pop("decision_factors", None)
        v2["final_decision"]["supporting_factors"] = ["legacy support a"]
        v2["final_decision"]["conflicting_factors"] = ["legacy conflict a"]
        result = adapt_v2_payload_to_predict_legacy(v2)
        self.assertEqual(
            result["legacy_fields"]["supporting_factors"], ["legacy support a"]
        )
        self.assertEqual(
            result["legacy_fields"]["conflicting_factors"], ["legacy conflict a"]
        )

    def test_adapter_path_fields_from_fallback_or_unknown(self) -> None:
        from services.predict_legacy_adapter import adapt_v2_payload_to_predict_legacy

        v2 = _v2_full()
        # V2 doesn't carry scan_bias / open_tendency / etc. — adapter must
        # use fallback when present, else "unknown".
        result = adapt_v2_payload_to_predict_legacy(
            v2, fallback_legacy_payload=_legacy_fallback()
        )
        legacy = result["legacy_fields"]
        self.assertEqual(legacy["scan_bias"], "fallback_scan")
        self.assertEqual(legacy["open_tendency"], "fallback_open")
        self.assertEqual(legacy["close_tendency"], "fallback_close")
        self.assertEqual(legacy["pred_open"], "fallback_pred_open")
        self.assertEqual(legacy["pred_path"], "fallback_pred_path")
        self.assertEqual(legacy["pred_close"], "fallback_pred_close")

        # Without fallback, scan/path fields default to "unknown".
        result_no_fb = adapt_v2_payload_to_predict_legacy(v2)
        legacy = result_no_fb["legacy_fields"]
        for field in ("scan_bias", "open_tendency", "close_tendency", "pred_open", "pred_path", "pred_close"):
            self.assertEqual(
                legacy[field], "unknown", msg=f"{field} default must be unknown"
            )


# ---------------------------------------------------------------------------
# Priority: V2 explicit beats fallback
# ---------------------------------------------------------------------------


class AdapterPriorityTests(unittest.TestCase):
    def test_adapter_v2_fields_beat_fallback(self) -> None:
        from services.predict_legacy_adapter import adapt_v2_payload_to_predict_legacy

        v2 = _v2_full()
        fb = _legacy_fallback()
        result = adapt_v2_payload_to_predict_legacy(v2, fallback_legacy_payload=fb)
        legacy = result["legacy_fields"]
        # V2 final_decision.final_direction wins over fallback.
        self.assertEqual(legacy["final_bias"], "偏多")
        # V2 confidence_result wins over fallback.
        self.assertEqual(legacy["final_confidence"], "medium")
        # V2 final_report.combined_user_summary wins over fallback.
        self.assertEqual(
            legacy["prediction_summary"], "明日基准判断：偏多。综合三系统输出。"
        )

    def test_adapter_missing_fields_warn_and_default(self) -> None:
        from services.predict_legacy_adapter import adapt_v2_payload_to_predict_legacy

        result = adapt_v2_payload_to_predict_legacy({}, fallback_legacy_payload=None)
        # Defaults must be deterministic.
        legacy = result["legacy_fields"]
        self.assertEqual(legacy["final_bias"], "unknown")
        self.assertEqual(legacy["final_confidence"], "unknown")
        self.assertEqual(legacy["prediction_summary"], "")
        # Warnings should call out the empty fallback chain.
        self.assertGreater(len(result["warnings"]), 0)


class AdapterInputValidationTests(unittest.TestCase):
    def test_adapter_handles_non_dict_v2_payload(self) -> None:
        from services.predict_legacy_adapter import adapt_v2_payload_to_predict_legacy

        result = adapt_v2_payload_to_predict_legacy("not-a-dict")  # type: ignore[arg-type]
        self.assertEqual(result["adapter_kind"], "v2_to_predict_legacy_adapter")
        joined = " ".join(result["warnings"])
        self.assertIn("v2_payload", joined.lower())

    def test_adapter_handles_non_dict_fallback(self) -> None:
        from services.predict_legacy_adapter import adapt_v2_payload_to_predict_legacy

        result = adapt_v2_payload_to_predict_legacy(
            _v2_full(), fallback_legacy_payload="not-a-dict"  # type: ignore[arg-type]
        )
        self.assertEqual(result["adapter_kind"], "v2_to_predict_legacy_adapter")
        joined = " ".join(result["warnings"])
        self.assertIn("fallback", joined.lower())


# ---------------------------------------------------------------------------
# Forbidden output fields
# ---------------------------------------------------------------------------


class AdapterNoForbiddenFieldsTests(unittest.TestCase):
    def test_adapter_no_forbidden_fields(self) -> None:
        from services.predict_legacy_adapter import adapt_v2_payload_to_predict_legacy

        for v2 in (_v2_full(), {}, {"kind": "projection_v2_report"}):
            result = adapt_v2_payload_to_predict_legacy(
                v2, fallback_legacy_payload=_legacy_fallback()
            )
            for forbidden in _FORBIDDEN_FIELDS:
                self.assertNotIn(
                    forbidden,
                    result,
                    msg=f"top-level: {forbidden!r} present",
                )
                self.assertNotIn(
                    forbidden,
                    result["legacy_fields"],
                    msg=f"legacy_fields: {forbidden!r} present",
                )


# ---------------------------------------------------------------------------
# Static import / call guards
# ---------------------------------------------------------------------------


class AdapterStaticBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module_path = ROOT / "services" / "predict_legacy_adapter.py"
        self.source = self.module_path.read_text(encoding="utf-8")
        self.tree = ast.parse(self.source)

    def test_adapter_no_forbidden_imports(self) -> None:
        forbidden_substrings = (
            "from services.openai_client",
            "import openai",
            "openai_client",
            "services.active_rule_pool_promotion",
            "services.promotion_adoption_gate",
            "services.promotion_execution_bridge",
            "services.continuous_smoothing",
            "import continuous_smoothing",
            "services.ai_summary",
        )
        for token in forbidden_substrings:
            self.assertNotIn(token, self.source, msg=f"forbidden import: {token}")

    def test_adapter_no_forbidden_calls(self) -> None:
        # The adapter must not invoke any active service / V2 / final
        # decision / confidence evaluator / run_predict path.
        for forbidden in (
            "from services.projection_orchestrator_v2",
            "import services.projection_orchestrator_v2",
            "from services.projection_orchestrator",
            "from services.final_decision",
            "import services.final_decision",
            "from services.confidence_evaluator",
            "import services.confidence_evaluator",
            "from predict import",
            "import predict",
            "run_projection_v2",
            "run_predict",
            "build_final_decision",
            "build_confidence_result",
        ):
            self.assertNotIn(
                forbidden, self.source, msg=f"forbidden call/import: {forbidden}"
            )

    def test_adapter_no_db_or_file_io(self) -> None:
        for forbidden in (
            "import sqlite3",
            "from sqlite3",
            "from services.log_store",
            "from services.prediction_store",
            "open(",
            "Path(",
            "requests.",
            "urllib",
            "http.client",
        ):
            self.assertNotIn(
                forbidden, self.source, msg=f"forbidden i/o token: {forbidden}"
            )


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class AdapterDeterministicTests(unittest.TestCase):
    def test_adapter_deterministic(self) -> None:
        from services.predict_legacy_adapter import adapt_v2_payload_to_predict_legacy

        kwargs = dict(
            v2_payload=_v2_full(),
            fallback_legacy_payload=_legacy_fallback(),
        )
        result_a = adapt_v2_payload_to_predict_legacy(**kwargs)
        result_b = adapt_v2_payload_to_predict_legacy(**copy.deepcopy(kwargs))
        self.assertEqual(result_a, result_b)


if __name__ == "__main__":
    unittest.main()
