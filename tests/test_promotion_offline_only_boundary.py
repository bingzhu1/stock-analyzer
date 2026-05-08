"""Contract enforcement tests for Step 12G (RISK-10) promotion offline-only.

These tests pin the documentation lock + import guards + output safety
contract for the three promotion modules:

- ``services/active_rule_pool_promotion.py``
- ``services/promotion_adoption_gate.py``
- ``services/promotion_execution_bridge.py``

The promotion cluster is a research / calibration / validation tool. It
must never be wired into the online projection / exclusion / confidence /
final report / UI / trading paths. RISK-10 is a *preventive* lock — the
current state is CLEAN, but the lock + import guard tests + safety fields
prevent future PRs from quietly opening the gate.

Design contracts: 06 / 07A / 07B / 07C / 07D / 11G / 11H.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


_PROMOTION_MODULE_PATHS: tuple[Path, ...] = (
    ROOT / "services" / "active_rule_pool_promotion.py",
    ROOT / "services" / "promotion_adoption_gate.py",
    ROOT / "services" / "promotion_execution_bridge.py",
)

_PROMOTION_IMPORT_TOKENS: tuple[str, ...] = (
    "services.active_rule_pool_promotion",
    "services.promotion_adoption_gate",
    "services.promotion_execution_bridge",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _has_promotion_import(source: str) -> bool:
    return any(
        f"from {token}" in source or f"import {token}" in source
        for token in _PROMOTION_IMPORT_TOKENS
    )


def _glob_active_python_paths(*relative_globs: str) -> list[Path]:
    paths: list[Path] = []
    for pattern in relative_globs:
        paths.extend(ROOT.glob(pattern))
    return [p for p in paths if p.is_file() and p.suffix == ".py"]


def _assert_no_promotion_import(test_case: unittest.TestCase, paths: list[Path]) -> None:
    offenders: list[str] = []
    for path in paths:
        try:
            source = _read(path)
        except (FileNotFoundError, OSError):
            continue
        if _has_promotion_import(source):
            offenders.append(str(path.relative_to(ROOT)))
    test_case.assertEqual(
        offenders,
        [],
        msg=f"promotion modules must not be imported by: {offenders!r}",
    )


# ---------------------------------------------------------------------------
# Doc-lock tests
# ---------------------------------------------------------------------------


class PromotionDocLockTests(unittest.TestCase):
    def test_promotion_modules_marked_offline_only(self) -> None:
        for path in _PROMOTION_MODULE_PATHS:
            source = _read(path)
            self.assertIn(
                "OFFLINE_ONLY",
                source,
                msg=f"{path.name} must declare OFFLINE_ONLY in its module docstring",
            )
            self.assertIn(
                "MUST NOT be imported",
                source,
                msg=f"{path.name} must state 'MUST NOT be imported by online ...' in its docstring",
            )

    def test_promotion_execution_bridge_documentation_forbids_active_caller(self) -> None:
        source = _read(ROOT / "services" / "promotion_execution_bridge.py")
        self.assertIn(
            "MUST NOT be set True by any active caller",
            source,
            msg=(
                "promotion_execution_bridge.py must explicitly forbid active "
                "callers from setting execution_enabled=True"
            ),
        )


# ---------------------------------------------------------------------------
# Import-guard tests for online / UI / trading paths
# ---------------------------------------------------------------------------


class AppDoesNotImportPromotionTests(unittest.TestCase):
    def test_app_does_not_import_promotion_modules(self) -> None:
        _assert_no_promotion_import(self, [ROOT / "app.py"])

    def test_predict_py_does_not_import_promotion_modules(self) -> None:
        _assert_no_promotion_import(self, [ROOT / "predict.py"])


class UIDoesNotImportPromotionTests(unittest.TestCase):
    def test_ui_does_not_import_promotion_modules(self) -> None:
        ui_paths = _glob_active_python_paths("ui/*.py", "ui/**/*.py")
        _assert_no_promotion_import(self, ui_paths)


class ActivePathDoesNotImportPromotionTests(unittest.TestCase):
    def test_projection_does_not_import_promotion_modules(self) -> None:
        # Active projection-side modules per 09/10 inventory + 11A boundary.
        projection_paths = [
            ROOT / "services" / "projection_orchestrator_v2.py",
            ROOT / "services" / "projection_orchestrator.py",
            ROOT / "services" / "main_projection_layer.py",
            ROOT / "services" / "primary_20day_analysis.py",
            ROOT / "services" / "peer_adjustment.py",
            ROOT / "services" / "historical_probability.py",
            ROOT / "services" / "projection_entrypoint.py",
            ROOT / "services" / "projection_chain_contract.py",
            ROOT / "services" / "projection_rule_preflight.py",
            ROOT / "services" / "projection_orchestrator_preflight.py",
            ROOT / "services" / "projection_preflight.py",
            ROOT / "services" / "projection_memory_briefing.py",
            ROOT / "services" / "consistency_layer.py",
        ]
        _assert_no_promotion_import(self, projection_paths)

    def test_exclusion_does_not_import_promotion_modules(self) -> None:
        exclusion_paths = [
            ROOT / "services" / "exclusion_layer.py",
            ROOT / "services" / "anti_false_exclusion_audit.py",
            ROOT / "services" / "anti_false_exclusion_dashboard.py",
            ROOT / "services" / "big_up_contradiction_card.py",
            ROOT / "services" / "big_down_tail_warning.py",
            ROOT / "services" / "exclusion_reliability_review.py",
        ]
        _assert_no_promotion_import(self, exclusion_paths)

    def test_confidence_does_not_import_promotion_modules(self) -> None:
        confidence_paths = [
            ROOT / "services" / "confidence_evaluator.py",
            ROOT / "services" / "contract_calibration_inputs.py",
            ROOT / "services" / "active_rule_pool_calibration.py",
            ROOT / "services" / "projection_three_systems_renderer.py",
        ]
        _assert_no_promotion_import(self, confidence_paths)

    def test_final_report_does_not_import_promotion_modules(self) -> None:
        final_paths = [
            ROOT / "services" / "final_decision.py",
            ROOT / "services" / "projection_three_systems_renderer.py",
            ROOT / "services" / "projection_narrative_renderer.py",
            ROOT / "services" / "predict_summary.py",
            ROOT / "services" / "ai_summary.py",
        ]
        _assert_no_promotion_import(self, final_paths)

    def test_home_terminal_orchestrator_does_not_import_promotion_modules(self) -> None:
        _assert_no_promotion_import(
            self, [ROOT / "services" / "home_terminal_orchestrator.py"]
        )


# ---------------------------------------------------------------------------
# Reverse import-guard tests: promotion modules don't reach back into trading,
# LLM, or active projection.
# ---------------------------------------------------------------------------


class PromotionDoesNotImportForbiddenSurfacesTests(unittest.TestCase):
    _FORBIDDEN_REVERSE_TOKENS: tuple[str, ...] = (
        "services.openai_client",
        "openai.ChatCompletion",
        "longbridge",
        "LongBridge",
        "tigersdk",
        "ibapi",
        "alpaca_trade_api",
        # Active projection / exclusion / confidence / final report
        "services.projection_orchestrator_v2",
        "services.main_projection_layer",
        "services.exclusion_layer",
        "services.confidence_evaluator",
        "services.final_decision",
        "services.home_terminal_orchestrator",
        "services.projection_three_systems_renderer",
        "services.ai_summary",
    )

    def test_promotion_modules_do_not_import_trading_api(self) -> None:
        offenders: list[str] = []
        for path in _PROMOTION_MODULE_PATHS:
            source = _read(path)
            for token in (
                "longbridge",
                "LongBridge",
                "tigersdk",
                "ibapi",
                "alpaca_trade_api",
            ):
                if f"import {token}" in source or f"from {token}" in source:
                    offenders.append(f"{path.name}:{token}")
        self.assertEqual(offenders, [], msg=f"trading SDK imports forbidden: {offenders}")

    def test_promotion_modules_do_not_import_openai_client(self) -> None:
        offenders: list[str] = []
        for path in _PROMOTION_MODULE_PATHS:
            source = _read(path)
            if "services.openai_client" in source or "import openai" in source:
                offenders.append(path.name)
        self.assertEqual(offenders, [], msg=f"LLM imports forbidden: {offenders}")

    def test_promotion_modules_do_not_import_active_projection(self) -> None:
        offenders: list[str] = []
        active_tokens = (
            "services.projection_orchestrator_v2",
            "services.main_projection_layer",
            "services.exclusion_layer",
            "services.confidence_evaluator",
            "services.final_decision",
            "services.home_terminal_orchestrator",
            "services.projection_three_systems_renderer",
            "services.ai_summary",
        )
        for path in _PROMOTION_MODULE_PATHS:
            source = _read(path)
            for token in active_tokens:
                if f"from {token}" in source or f"import {token}" in source:
                    offenders.append(f"{path.name}:{token}")
        self.assertEqual(
            offenders,
            [],
            msg=f"promotion modules must not import active projection: {offenders}",
        )


# ---------------------------------------------------------------------------
# Output safety contract tests
# ---------------------------------------------------------------------------


_SAFETY_FIELDS: tuple[str, ...] = (
    "mode",
    "online_safe",
    "may_affect_active_prediction",
    "may_affect_active_exclusion",
    "may_affect_active_confidence",
    "may_affect_final_report",
    "may_affect_trading",
    "requires_human_review",
)

_FORBIDDEN_OUTPUT_FIELDS: tuple[str, ...] = (
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


def _sample_calibration_report() -> dict:
    return {
        "kind": "active_rule_pool_calibration_report",
        "ready": True,
        "rules": [
            {
                "rule_id": "rule_A",
                "title": "Test Rule A",
                "category": "momentum",
                "calibration_decision": "retain",
                "hit_count": 8,
                "improved_case_count": 5,
                "worsened_case_count": 1,
                "net_effect": 1.5,
                "notes": "",
            },
        ],
    }


def _expected_safety_payload() -> dict:
    return {
        "mode": "offline_only",
        "online_safe": False,
        "may_affect_active_prediction": False,
        "may_affect_active_exclusion": False,
        "may_affect_active_confidence": False,
        "may_affect_final_report": False,
        "may_affect_trading": False,
        "requires_human_review": True,
    }


class PromotionOutputSafetyTests(unittest.TestCase):
    def _three_outputs(self) -> list[tuple[str, dict]]:
        from services.active_rule_pool_promotion import (
            build_active_rule_pool_promotion_report,
        )
        from services.promotion_adoption_gate import build_promotion_adoption_handoff
        from services.promotion_execution_bridge import (
            build_promotion_execution_bridge,
        )

        promotion_report = build_active_rule_pool_promotion_report(
            calibration_report=_sample_calibration_report()
        )
        adoption = build_promotion_adoption_handoff(promotion_report=promotion_report)
        bridge = build_promotion_execution_bridge(promotion_report=promotion_report)
        return [
            ("active_rule_pool_promotion", promotion_report),
            ("promotion_adoption_gate", adoption),
            ("promotion_execution_bridge", bridge),
        ]

    def test_promotion_outputs_offline_only_safety_fields(self) -> None:
        expected = _expected_safety_payload()
        for name, output in self._three_outputs():
            for field in _SAFETY_FIELDS:
                self.assertIn(
                    field,
                    output,
                    msg=f"{name} output missing safety field {field!r}",
                )
            for field, value in expected.items():
                self.assertEqual(
                    output[field],
                    value,
                    msg=f"{name} output {field}={output[field]!r}, expected {value!r}",
                )

    def test_promotion_outputs_no_hard_forced_required(self) -> None:
        for name, output in self._three_outputs():
            for forbidden in (
                "hard_exclusion",
                "forced_exclusion",
                "required_decision",
            ):
                self.assertNotIn(forbidden, output, msg=f"{name}: {forbidden}")

    def test_promotion_outputs_no_trading_action(self) -> None:
        for name, output in self._three_outputs():
            for forbidden in (
                "trading_action",
                "buy",
                "sell",
                "hold",
                "simulated_trade",
                "no_trade",
            ):
                self.assertNotIn(forbidden, output, msg=f"{name}: {forbidden}")

    def test_promotion_outputs_no_protection_layer_connected(self) -> None:
        for name, output in self._three_outputs():
            self.assertNotIn(
                "_PROTECTION_LAYER_CONNECTED",
                output,
                msg=f"{name} output must not carry _PROTECTION_LAYER_CONNECTED",
            )

    def test_promotion_outputs_no_production_promotion(self) -> None:
        for name, output in self._three_outputs():
            self.assertNotIn(
                "production_promotion",
                output,
                msg=f"{name} output must not carry production_promotion",
            )

    def test_promotion_outputs_no_modified_or_overridden_fields(self) -> None:
        for name, output in self._three_outputs():
            for forbidden in (
                "final_report_mutation",
                "modified_projection",
                "modified_exclusion",
                "modified_confidence",
                "overridden_most_likely_state",
                "corrected_confidence",
            ):
                self.assertNotIn(forbidden, output, msg=f"{name}: {forbidden}")


class PromotionExecutionBridgeDefaultTests(unittest.TestCase):
    def test_default_execution_enabled_is_false(self) -> None:
        from services.promotion_execution_bridge import (
            build_promotion_execution_bridge,
        )

        # Default (no enable_execution_bridge kwarg) must keep the gate off.
        result = build_promotion_execution_bridge(
            promotion_report={
                "kind": "active_rule_pool_promotion_report",
                "ready": True,
                "rules": [],
            }
        )
        self.assertIs(result["execution_enabled"], False)

    def test_explicit_disabled_returns_false(self) -> None:
        from services.promotion_execution_bridge import (
            build_promotion_execution_bridge,
        )

        result = build_promotion_execution_bridge(
            promotion_report={
                "kind": "active_rule_pool_promotion_report",
                "ready": True,
                "rules": [],
            },
            enable_execution_bridge=False,
        )
        self.assertIs(result["execution_enabled"], False)


if __name__ == "__main__":
    unittest.main()
