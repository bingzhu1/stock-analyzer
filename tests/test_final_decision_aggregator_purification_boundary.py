"""Contract enforcement tests for Step 12B (RISK-2).

These tests pin the final_decision aggregator boundary:

1. ``build_final_decision`` must not override ``final_direction``; it must
   strictly equal ``primary_analysis.direction`` (or ``unknown`` when primary
   is missing).
2. ``build_final_decision`` must not recompute ``final_confidence``; it must
   come from ``confidence_result.combined_confidence.level`` (or ``unknown``
   when confidence_result is missing/not ready).
3. ``preflight`` must be display-only: ``preflight_influence.applied_effects``
   must always be ``[]``; preflight must not change confidence or risk.
4. Output must include ``non_mutation_confirmations`` (six false fields).
5. Output must include ``source_attribution`` listing where each surfaced
   field came from.
6. Output must NOT contain trading / hard / forced / required / promotion
   fields.
7. Output must NOT contain ``modified_*`` / ``overridden_*`` / ``corrected_*``
   / ``decision_after_preflight`` / ``override_reason`` / ``final_report_mutation``.
8. Static check: ``services/final_decision.py`` must not call
   ``_apply_preflight_influence`` from ``build_final_decision``.

Design contracts: 06 / 07C / 07D / 11B / 11H.
"""

from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


_FORBIDDEN_TOP_LEVEL_FIELDS = (
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
    "decision_after_preflight",
    "override_reason",
)


def _primary(**overrides) -> dict:
    base = {
        "kind": "primary_20day_analysis",
        "symbol": "AVGO",
        "ready": True,
        "direction": "偏多",
        "confidence": "medium",
        "summary": "primary",
        "basis": [],
    }
    base.update(overrides)
    return base


def _peer(**overrides) -> dict:
    base = {
        "kind": "peer_adjustment",
        "ready": True,
        "confirmation_level": "confirmed",
        "adjustment": "reinforce_bullish",
        "adjusted_direction": "偏多",
        "adjusted_confidence": "high",
        "summary": "peers ok",
        "basis": [],
        "warnings": [],
    }
    base.update(overrides)
    return base


def _historical(**overrides) -> dict:
    base = {
        "kind": "historical_probability",
        "ready": True,
        "sample_count": 12,
        "sample_quality": "enough",
        "historical_bias": "supports_bullish",
        "impact": "support",
        "summary": "hist ok",
        "basis": [],
        "warnings": [],
    }
    base.update(overrides)
    return base


def _preflight(*rules) -> dict:
    rule_list = list(rules)
    return {
        "kind": "projection_rule_preflight",
        "ready": True,
        "matched_rules": rule_list,
        "rule_warnings": [r.get("message", "") for r in rule_list],
        "rule_adjustments": [],
        "summary": f"命中 {len(rule_list)} 条规则。" if rule_list else "未命中规则。",
        "warnings": [],
        "source_counts": {"matched_rule_count": len(rule_list)},
    }


def _rule(severity: str = "high") -> dict:
    return {
        "rule_id": f"test-{severity}",
        "title": f"测试规则 {severity}",
        "category": "wrong_direction",
        "severity": severity,
        "message": f"{severity} 级别规则提醒。",
    }


class FinalDecisionDoesNotOverrideDirectionTests(unittest.TestCase):
    def test_final_decision_does_not_override_direction_for_neutral_peer_downgrade(self) -> None:
        """The legacy direction-flip branch turned 偏多 into 中性 when peer
        downgraded with adjusted_direction=中性. The new aggregator must
        keep final_direction == primary_analysis.direction."""
        from services.final_decision import build_final_decision

        result = build_final_decision(
            primary_analysis=_primary(direction="偏多", confidence="high"),
            peer_adjustment=_peer(
                adjustment="downgrade",
                adjusted_direction="中性",
                adjusted_confidence="medium",
            ),
            historical_probability=_historical(),
            preflight=_preflight(),
        )

        self.assertEqual(result["final_direction"], "偏多")
        self.assertEqual(result["direction"], "偏多")

    def test_final_decision_keeps_neutral_primary_neutral(self) -> None:
        from services.final_decision import build_final_decision

        result = build_final_decision(
            primary_analysis=_primary(direction="中性", confidence="medium"),
            peer_adjustment=_peer(
                adjustment="reinforce_bullish",
                adjusted_direction="偏多",
                adjusted_confidence="high",
            ),
            historical_probability=_historical(),
            preflight=_preflight(),
        )

        self.assertEqual(result["final_direction"], "中性")

    def test_final_decision_direction_independent_of_peer_and_history(self) -> None:
        from services.final_decision import build_final_decision

        primary = _primary(direction="偏多", confidence="medium")
        for peer_adj in (
            _peer(adjustment="reinforce_bullish", adjusted_direction="偏多"),
            _peer(adjustment="downgrade", adjusted_direction="中性"),
            _peer(adjustment="reinforce_bearish", adjusted_direction="偏空"),
            _peer(adjustment="no_change", adjusted_direction="偏多"),
        ):
            for hist in (
                _historical(impact="support", historical_bias="supports_bullish"),
                _historical(impact="caution", historical_bias="mixed"),
                _historical(ready=False, impact="missing", historical_bias="missing"),
            ):
                result = build_final_decision(
                    primary_analysis=primary,
                    peer_adjustment=peer_adj,
                    historical_probability=hist,
                    preflight=_preflight(),
                )
                self.assertEqual(
                    result["final_direction"],
                    "偏多",
                    msg="final_direction must equal primary regardless of peer/historical",
                )


class FinalDecisionDoesNotRecomputeConfidenceTests(unittest.TestCase):
    def test_final_decision_missing_confidence_returns_unknown(self) -> None:
        from services.final_decision import build_final_decision

        result = build_final_decision(
            primary_analysis=_primary(confidence="high"),
            peer_adjustment=_peer(),
            historical_probability=_historical(),
            preflight=_preflight(),
        )

        self.assertEqual(result["final_confidence"], "unknown")
        self.assertEqual(result["confidence"], "unknown")
        self.assertTrue(
            any("confidence_result" in str(w) for w in result["warnings"]),
            msg="warnings must surface that confidence_result is not wired",
        )

    def test_final_decision_with_confidence_result_uses_combined_level(self) -> None:
        from services.final_decision import build_final_decision

        for level in ("high", "medium", "low", "unknown"):
            result = build_final_decision(
                primary_analysis=_primary(confidence="high"),
                peer_adjustment=_peer(adjustment="downgrade", adjusted_direction="中性"),
                historical_probability=_historical(impact="caution", historical_bias="mixed"),
                preflight=_preflight(_rule("high")),
                confidence_result={
                    "ready": True,
                    "combined_confidence": {"level": level},
                },
            )
            self.assertEqual(
                result["final_confidence"],
                level,
                msg=f"final_confidence must come from confidence_result for level={level}",
            )

    def test_final_decision_does_not_recompute_confidence_from_layers(self) -> None:
        """final_confidence must not depend on peer / historical / preflight
        when confidence_result is absent — it stays unknown."""
        from services.final_decision import build_final_decision

        primary = _primary(confidence="high")
        results = []
        for peer_adj in (
            _peer(adjustment="reinforce_bullish"),
            _peer(adjustment="downgrade"),
            _peer(ready=False, adjustment="missing"),
        ):
            for hist in (
                _historical(impact="support"),
                _historical(impact="caution"),
                _historical(ready=False, impact="missing", historical_bias="missing"),
            ):
                for pf in (_preflight(), _preflight(_rule("high")), _preflight(_rule("medium"))):
                    res = build_final_decision(
                        primary_analysis=primary,
                        peer_adjustment=peer_adj,
                        historical_probability=hist,
                        preflight=pf,
                    )
                    results.append(res["final_confidence"])
        self.assertEqual(set(results), {"unknown"})


class PreflightDisplayOnlyTests(unittest.TestCase):
    def test_preflight_is_display_only_warning(self) -> None:
        from services.final_decision import build_final_decision

        for severity in ("high", "medium", "low"):
            result = build_final_decision(
                primary_analysis=_primary(confidence="high"),
                peer_adjustment=_peer(adjustment="reinforce_bullish"),
                historical_probability=_historical(impact="support"),
                preflight=_preflight(_rule(severity)),
            )
            inf = result["preflight_influence"]
            self.assertEqual(
                inf["applied_effects"],
                [],
                msg=f"preflight applied_effects must be [] for severity={severity}",
            )
            self.assertEqual(inf["matched_rule_count"], 1)
            self.assertIsInstance(inf["summary"], str)

    def test_preflight_does_not_change_direction_or_confidence(self) -> None:
        from services.final_decision import build_final_decision

        confidence_result = {"ready": True, "combined_confidence": {"level": "high"}}
        baseline = build_final_decision(
            primary_analysis=_primary(direction="偏多", confidence="high"),
            peer_adjustment=_peer(),
            historical_probability=_historical(),
            preflight=_preflight(),
            confidence_result=confidence_result,
        )
        with_high_rule = build_final_decision(
            primary_analysis=_primary(direction="偏多", confidence="high"),
            peer_adjustment=_peer(),
            historical_probability=_historical(),
            preflight=_preflight(_rule("high"), _rule("medium")),
            confidence_result=confidence_result,
        )
        self.assertEqual(baseline["final_direction"], with_high_rule["final_direction"])
        self.assertEqual(baseline["final_confidence"], with_high_rule["final_confidence"])
        self.assertEqual(with_high_rule["preflight_influence"]["applied_effects"], [])

    def test_preflight_warnings_surface_as_display_warnings(self) -> None:
        from services.final_decision import build_final_decision

        result = build_final_decision(
            primary_analysis=_primary(),
            peer_adjustment=_peer(),
            historical_probability=_historical(),
            preflight=_preflight(_rule("high"), _rule("medium")),
        )
        joined_warnings = " ".join(result["warnings"])
        self.assertIn("规则", joined_warnings)


class NonMutationConfirmationsTests(unittest.TestCase):
    def test_final_decision_has_non_mutation_confirmations(self) -> None:
        from services.final_decision import build_final_decision

        result = build_final_decision(
            primary_analysis=_primary(),
            peer_adjustment=_peer(),
            historical_probability=_historical(),
            preflight=_preflight(),
        )
        confirmations = result["non_mutation_confirmations"]
        for field in (
            "projection_result_mutated",
            "exclusion_result_mutated",
            "confidence_result_mutated",
            "final_direction_overridden",
            "confidence_recomputed",
            "preflight_applied_as_decision",
        ):
            self.assertIn(field, confirmations)
            self.assertIs(confirmations[field], False)


class SourceAttributionTests(unittest.TestCase):
    def test_final_decision_has_source_mapping(self) -> None:
        from services.final_decision import build_final_decision

        result = build_final_decision(
            primary_analysis=_primary(),
            peer_adjustment=_peer(),
            historical_probability=_historical(),
            preflight=_preflight(_rule("high")),
        )
        attribution = result["source_attribution"]
        self.assertIsInstance(attribution, list)
        self.assertGreater(len(attribution), 0)
        for entry in attribution:
            self.assertIsInstance(entry, dict)
            self.assertIn("section", entry)
            self.assertIn("field", entry)
            self.assertIn("source_field", entry)

    def test_source_attribution_includes_projection_and_preflight_when_present(self) -> None:
        from services.final_decision import build_final_decision

        result = build_final_decision(
            primary_analysis=_primary(),
            peer_adjustment=_peer(),
            historical_probability=_historical(),
            preflight=_preflight(_rule("high")),
            confidence_result={"ready": True, "combined_confidence": {"level": "medium"}},
            exclusion_result={"most_unlikely_state": "大跌", "excluded": False},
        )
        sections = {entry["section"] for entry in result["source_attribution"]}
        self.assertIn("projection", sections)
        self.assertIn("confidence", sections)
        self.assertIn("preflight", sections)


class NoTradingOrHardFieldsTests(unittest.TestCase):
    def test_final_decision_no_trading_or_hard_fields(self) -> None:
        from services.final_decision import build_final_decision

        result = build_final_decision(
            primary_analysis=_primary(),
            peer_adjustment=_peer(),
            historical_probability=_historical(),
            preflight=_preflight(_rule("high"), _rule("medium")),
        )
        for forbidden in _FORBIDDEN_TOP_LEVEL_FIELDS:
            self.assertNotIn(
                forbidden,
                result,
                msg=f"final_decision result must not contain {forbidden!r}",
            )

    def test_primary_missing_path_no_trading_or_hard_fields(self) -> None:
        from services.final_decision import build_final_decision

        result = build_final_decision(
            primary_analysis=_primary(ready=False, direction="unknown", confidence="unknown"),
            peer_adjustment=_peer(),
            historical_probability=_historical(),
            preflight=_preflight(),
        )
        self.assertFalse(result["ready"])
        for forbidden in _FORBIDDEN_TOP_LEVEL_FIELDS:
            self.assertNotIn(forbidden, result)


class StaticBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module_path = ROOT / "services" / "final_decision.py"
        self.source = self.module_path.read_text(encoding="utf-8")
        self.tree = ast.parse(self.source)

    def _function_body(self, name: str) -> str:
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef) and node.name == name:
                return ast.get_source_segment(self.source, node) or ""
        self.fail(f"function {name} not found in {self.module_path}")

    def test_build_final_decision_does_not_call_apply_preflight_influence(self) -> None:
        body = self._function_body("build_final_decision")
        self.assertNotIn(
            "_apply_preflight_influence(",
            body,
            msg="build_final_decision must not call _apply_preflight_influence",
        )

    def test_build_final_decision_does_not_call_confidence_from_score(self) -> None:
        body = self._function_body("build_final_decision")
        self.assertNotIn(
            "_confidence_from_score(",
            body,
            msg="build_final_decision must not recompute confidence",
        )


class PrimaryMissingPathTests(unittest.TestCase):
    def test_primary_missing_returns_unknown_with_warnings(self) -> None:
        from services.final_decision import build_final_decision

        result = build_final_decision(
            primary_analysis=_primary(ready=False, direction="unknown", confidence="unknown"),
            peer_adjustment=_peer(),
            historical_probability=_historical(),
            preflight=_preflight(),
        )
        self.assertFalse(result["ready"])
        self.assertEqual(result["final_direction"], "unknown")
        self.assertEqual(result["final_confidence"], "unknown")


# ---------------------------------------------------------------------------
# PR-FINAL-2 (18P): forbidden import boundary, input non-mutation
# round-trip, and dead helper removal pinning. Final Report Layer must
# remain a pure aggregator + display formatter — no calls into
# Projection / Exclusion / Confidence / orchestrator / UI / DB / predict.
# ---------------------------------------------------------------------------


class FinalDecisionImportBoundaryTests(unittest.TestCase):
    """``services/final_decision.py`` must remain a pure aggregator with
    zero coupling to Projection / Exclusion / Confidence / orchestrator /
    UI / DB / predict modules. The aggregator only reads dicts handed in
    by callers — it never calls into the upstream subsystems."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = (ROOT / "services" / "final_decision.py").read_text(
            encoding="utf-8"
        )

    def test_no_main_projection_layer_import(self) -> None:
        for f in (
            "from services.main_projection_layer",
            "import services.main_projection_layer",
        ):
            self.assertNotIn(
                f, self.source,
                msg=f"final_decision must not contain `{f}`",
            )

    def test_no_exclusion_layer_or_peer_alignment_import(self) -> None:
        for f in (
            "from services.exclusion_layer",
            "import services.exclusion_layer",
            "from services.peer_alignment",
            "import services.peer_alignment",
        ):
            self.assertNotIn(
                f, self.source,
                msg=f"final_decision must not contain `{f}`",
            )

    def test_no_confidence_evaluator_import(self) -> None:
        for f in (
            "from services.confidence_evaluator",
            "import services.confidence_evaluator",
        ):
            self.assertNotIn(
                f, self.source,
                msg=f"final_decision must not contain `{f}`",
            )

    def test_no_orchestrator_imports(self) -> None:
        forbidden = (
            "from services.projection_orchestrator",
            "import services.projection_orchestrator",
            "from services.projection_orchestrator_v2",
            "import services.projection_orchestrator_v2",
            "from services.projection_entrypoint",
            "import services.projection_entrypoint",
            "from services.projection_v2_adapter",
            "import services.projection_v2_adapter",
            "from services.home_terminal_orchestrator",
            "import services.home_terminal_orchestrator",
        )
        for f in forbidden:
            self.assertNotIn(
                f, self.source,
                msg=f"final_decision must not contain `{f}`",
            )

    def test_no_predict_app_ui_import(self) -> None:
        forbidden = (
            "import predict",
            "from predict",
            "import app",
            "from app",
            "import ui",
            "from ui",
            "import streamlit",
            "from streamlit",
        )
        for f in forbidden:
            self.assertNotIn(
                f, self.source,
                msg=f"final_decision must not contain `{f}`",
            )

    def test_no_db_or_yfinance_import(self) -> None:
        for f in (
            "import sqlite3",
            "from sqlite3",
            "import yfinance",
            "from yfinance",
        ):
            self.assertNotIn(
                f, self.source,
                msg=f"final_decision must not contain `{f}`",
            )

    def test_no_review_or_adapter_import(self) -> None:
        forbidden = (
            "from services.review_orchestrator",
            "import services.review_orchestrator",
            "from services.projection_result_adapter",
            "import services.projection_result_adapter",
            "from services.exclusion_result_adapter",
            "import services.exclusion_result_adapter",
            "from services.feature_payload_adapter",
            "import services.feature_payload_adapter",
        )
        for f in forbidden:
            self.assertNotIn(
                f, self.source,
                msg=f"final_decision must not contain `{f}`",
            )


class FinalDecisionInputNonMutationTests(unittest.TestCase):
    """``build_final_decision`` must not mutate any of its dict inputs.
    PR-FINAL-2 pins this with deep-copy round-trip tests across the full
    happy path and the primary-missing path."""

    def _build_inputs(self) -> dict[str, dict[str, object]]:
        return {
            "primary_analysis": _primary(),
            "peer_adjustment": _peer(),
            "historical_probability": _historical(),
            "preflight": _preflight(),
            "confidence_result": {
                "schema_version": "confidence_system_result.v1",
                "ready": True,
                "combined_confidence": {
                    "level": "medium",
                    "score": 0.55,
                    "reasoning": ["test"],
                },
                "agreement_status": "aligned",
                "conflict_level": "none",
            },
            "exclusion_result": {
                "schema_version": "exclusion_system_result.v1",
                "kind": "exclusion_layer",
                "symbol": "AVGO",
                "ready": True,
                "excluded": True,
                "action": "exclude",
                "triggered_rule": "exclude_big_down",
                "reasons": ["legacy reason"],
            },
        }

    def test_happy_path_does_not_mutate_any_input(self) -> None:
        import copy as _copy

        from services.final_decision import build_final_decision

        inputs = self._build_inputs()
        snapshots = {key: _copy.deepcopy(value) for key, value in inputs.items()}

        build_final_decision(**inputs)

        for key, snapshot in snapshots.items():
            self.assertEqual(
                inputs[key], snapshot,
                msg=f"build_final_decision mutated input {key!r}",
            )

    def test_primary_missing_path_does_not_mutate_any_input(self) -> None:
        import copy as _copy

        from services.final_decision import build_final_decision

        inputs = {
            "primary_analysis": _primary(
                ready=False, direction="unknown", confidence="unknown",
            ),
            "peer_adjustment": _peer(),
            "historical_probability": _historical(),
            "preflight": _preflight(),
        }
        snapshots = {key: _copy.deepcopy(value) for key, value in inputs.items()}

        build_final_decision(**inputs)

        for key, snapshot in snapshots.items():
            self.assertEqual(
                inputs[key], snapshot,
                msg=f"build_final_decision mutated input {key!r}",
            )

    def test_inputs_with_nested_lists_dicts_unchanged(self) -> None:
        import copy as _copy

        from services.final_decision import build_final_decision

        inputs = self._build_inputs()
        # Pad with deeply nested mutable structures to catch any in-place
        # modification of nested data.
        inputs["preflight"]["matched_rules"] = [
            {"rule_id": "R1", "severity": "high", "message": "msg-1"},
            {"rule_id": "R2", "severity": "medium", "message": "msg-2"},
        ]
        inputs["historical_probability"]["details"] = {
            "samples": [1, 2, 3],
            "notes": ["note"],
        }
        snapshots = {key: _copy.deepcopy(value) for key, value in inputs.items()}

        build_final_decision(**inputs)

        for key, snapshot in snapshots.items():
            self.assertEqual(
                inputs[key], snapshot,
                msg=f"build_final_decision mutated input {key!r}",
            )


class FinalDecisionDeadHelperRemovalTests(unittest.TestCase):
    """PR-FINAL-2 deletes ``_apply_preflight_influence`` /
    ``_confidence_from_score`` / ``_risk_level`` from
    ``services/final_decision.py``. Their absence is pinned here."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = (ROOT / "services" / "final_decision.py").read_text(
            encoding="utf-8"
        )
        cls.tree = ast.parse(cls.source)

    def _function_names(self) -> set[str]:
        return {
            node.name
            for node in ast.walk(self.tree)
            if isinstance(node, ast.FunctionDef)
        }

    def test_apply_preflight_influence_definition_removed(self) -> None:
        self.assertNotIn(
            "_apply_preflight_influence",
            self._function_names(),
            msg=(
                "_apply_preflight_influence must be removed by PR-FINAL-2 "
                "(it has had no caller since Step 12B)."
            ),
        )

    def test_confidence_from_score_definition_removed(self) -> None:
        self.assertNotIn(
            "_confidence_from_score",
            self._function_names(),
            msg=(
                "_confidence_from_score must be removed by PR-FINAL-2 "
                "(its only caller was inside _apply_preflight_influence)."
            ),
        )

    def test_risk_level_definition_removed(self) -> None:
        self.assertNotIn(
            "_risk_level",
            self._function_names(),
            msg=(
                "_risk_level must be removed by PR-FINAL-2 "
                "(it has had no caller since Step 12B)."
            ),
        )

    def test_module_does_not_call_dead_helpers(self) -> None:
        # The pre-existing test_build_final_decision_does_not_call_*
        # tests scope to build_final_decision; this test scopes to the
        # whole module to guard against any other helper accidentally
        # reintroducing a call.
        for forbidden_call in (
            "_apply_preflight_influence(",
            "_confidence_from_score(",
            "_risk_level(",
        ):
            self.assertNotIn(
                forbidden_call,
                self.source,
                msg=(
                    f"final_decision must not call {forbidden_call!r} "
                    "anywhere — PR-FINAL-2 pins removal."
                ),
            )


if __name__ == "__main__":
    unittest.main()
