"""Tests for the architecture_orchestrator ownership skeleton
(Step 18V / PR-ARCH-1).

Spec source of truth:

- `tasks/record_1_0_architecture_reset_canonical_principles.md` §8 / §10
- `tasks/record_16i_core_chain_rebuild_execution_plan.md` PR-F
- `tasks/record_17j_final_report_layer_rebuild_plan.md` §13 PR-FINAL-7
- `tasks/record_18s_third_layer_based_implementation_batch_selection.md`
  §4 / §6 / §10

PR-ARCH-1 is the third batch's third cut: a **skeleton-only** module
that reserves ownership for the future ``architecture_orchestrator``.
This suite verifies:

1.  Module imports safely with no side effects.
2.  ``get_architecture_orchestrator_contract`` returns a dict with the
    expected ownership shape.
3.  ``status`` is the fixed string ``"skeleton_only"``.
4.  ``active_path_connected`` is ``False``.
5.  ``db_write_enabled`` is ``False``.
6.  ``trading_enabled`` is ``False``.
7.  ``replay_enabled`` is ``False``.
8.  ``calibration_enabled`` is ``False``.
9.  ``allowed_layer_sequence`` matches the canonical 9-layer order.
10. ``forbidden_active_path_actions`` covers the documented surface.
11. ``forbidden_output_fields`` covers the documented surface.
12. ``validate_architecture_orchestrator_contract`` returns ``[]`` for
    a valid contract.
13. validator catches each forbidden flag flipped to True.
14. validator catches a corrupted ``allowed_layer_sequence``.
15. validator catches a missing ``forbidden_active_path_actions`` entry.
16. validator catches a missing ``forbidden_output_fields`` entry.
17. validator catches a forbidden top-level field on the contract dict.
18. validator catches non-dict input without raising.
19. Returned contract is isolated (no mutation across calls).
20. Module source does not import any business / orchestrator / UI /
    DB / yfinance / pandas / streamlit / broker / OMS module.
21. Module source does not define ``run`` / ``execute`` / ``orchestrate``
    / ``main`` entry points.
22. Module source does not contain DB / file / yfinance / Streamlit
    tokens.
23. Module source does not contain trading-action quoted strings.
24. Public surface is the documented skeleton helpers + constants only.
"""

from __future__ import annotations

import inspect
import unittest
from pathlib import Path
from typing import Any

import services.architecture_orchestrator as arch_mod
from services.architecture_orchestrator import (
    ALLOWED_LAYER_SEQUENCE,
    ARCHITECTURE_ORCHESTRATOR_STATUS,
    ARCHITECTURE_ORCHESTRATOR_VERSION,
    FORBIDDEN_ACTIVE_PATH_ACTIONS,
    FORBIDDEN_OUTPUT_FIELDS,
    get_architecture_orchestrator_contract,
    validate_architecture_orchestrator_contract,
)


_REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(rel: str) -> str:
    return (_REPO_ROOT / rel).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Module imports + constants
# ---------------------------------------------------------------------------

class ModuleImportConstantsTests(unittest.TestCase):
    def test_module_imports_safely(self) -> None:
        # Re-importing must not raise; the module is side-effect free.
        import services.architecture_orchestrator as reimport

        self.assertIs(reimport, arch_mod)

    def test_version_constant(self) -> None:
        self.assertEqual(
            ARCHITECTURE_ORCHESTRATOR_VERSION,
            "architecture_orchestrator.skeleton.v1",
        )

    def test_status_constant(self) -> None:
        self.assertEqual(ARCHITECTURE_ORCHESTRATOR_STATUS, "skeleton_only")

    def test_allowed_layer_sequence_is_canonical_nine_layer_order(self) -> None:
        self.assertEqual(
            ALLOWED_LAYER_SEQUENCE,
            (
                "data",
                "feature",
                "projection",
                "exclusion",
                "confidence",
                "final_report",
                "review_learning",
                "evaluation",
                "presentation",
            ),
        )

    def test_forbidden_active_path_actions_contains_required(self) -> None:
        for action in (
            "run_predict",
            "call_main_projection_layer",
            "call_exclusion_layer",
            "call_confidence_evaluator",
            "call_final_decision",
            "write_db",
            "run_replay",
            "run_calibration",
            "place_trade",
        ):
            with self.subTest(action=action):
                self.assertIn(action, FORBIDDEN_ACTIVE_PATH_ACTIONS)

    def test_forbidden_output_fields_contains_required(self) -> None:
        for field in (
            "buy",
            "sell",
            "hold",
            "hard",
            "forced",
            "required",
            "trading_action",
            "order",
            "execution",
            "position_action",
            "active_rule_promotion",
            "promote_rule",
        ):
            with self.subTest(field=field):
                self.assertIn(field, FORBIDDEN_OUTPUT_FIELDS)


# ---------------------------------------------------------------------------
# 2. Contract dict shape + invariants
# ---------------------------------------------------------------------------

class ContractDictShapeTests(unittest.TestCase):
    def test_returns_dict(self) -> None:
        contract = get_architecture_orchestrator_contract()
        self.assertIsInstance(contract, dict)

    def test_contract_status_is_skeleton_only(self) -> None:
        contract = get_architecture_orchestrator_contract()
        self.assertEqual(contract["status"], "skeleton_only")

    def test_contract_version_matches_constant(self) -> None:
        contract = get_architecture_orchestrator_contract()
        self.assertEqual(
            contract["version"], ARCHITECTURE_ORCHESTRATOR_VERSION
        )

    def test_contract_active_path_connected_is_false(self) -> None:
        contract = get_architecture_orchestrator_contract()
        self.assertIs(contract["active_path_connected"], False)

    def test_contract_db_write_enabled_is_false(self) -> None:
        contract = get_architecture_orchestrator_contract()
        self.assertIs(contract["db_write_enabled"], False)

    def test_contract_trading_enabled_is_false(self) -> None:
        contract = get_architecture_orchestrator_contract()
        self.assertIs(contract["trading_enabled"], False)

    def test_contract_replay_enabled_is_false(self) -> None:
        contract = get_architecture_orchestrator_contract()
        self.assertIs(contract["replay_enabled"], False)

    def test_contract_calibration_enabled_is_false(self) -> None:
        contract = get_architecture_orchestrator_contract()
        self.assertIs(contract["calibration_enabled"], False)

    def test_contract_holdout_run_enabled_is_false(self) -> None:
        contract = get_architecture_orchestrator_contract()
        self.assertIs(contract["holdout_run_enabled"], False)

    def test_contract_allowed_layer_sequence_matches_canonical(self) -> None:
        contract = get_architecture_orchestrator_contract()
        self.assertEqual(
            contract["allowed_layer_sequence"],
            list(ALLOWED_LAYER_SEQUENCE),
        )

    def test_contract_forbidden_active_path_actions_present(self) -> None:
        contract = get_architecture_orchestrator_contract()
        for action in FORBIDDEN_ACTIVE_PATH_ACTIONS:
            with self.subTest(action=action):
                self.assertIn(
                    action, contract["forbidden_active_path_actions"]
                )

    def test_contract_forbidden_output_fields_present(self) -> None:
        contract = get_architecture_orchestrator_contract()
        for field in FORBIDDEN_OUTPUT_FIELDS:
            with self.subTest(field=field):
                self.assertIn(field, contract["forbidden_output_fields"])

    def test_contract_notes_is_list_of_strings(self) -> None:
        contract = get_architecture_orchestrator_contract()
        self.assertIsInstance(contract["notes"], list)
        self.assertGreater(len(contract["notes"]), 0)
        for note in contract["notes"]:
            self.assertIsInstance(note, str)

    def test_contract_top_level_does_not_contain_forbidden_fields(self) -> None:
        contract = get_architecture_orchestrator_contract()
        for forbidden in FORBIDDEN_OUTPUT_FIELDS:
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, contract)


# ---------------------------------------------------------------------------
# 3. Validator behavior
# ---------------------------------------------------------------------------

class ValidatorBehaviorTests(unittest.TestCase):
    def test_valid_contract_returns_empty(self) -> None:
        contract = get_architecture_orchestrator_contract()
        errors = validate_architecture_orchestrator_contract(contract)
        self.assertEqual(errors, [], msg=f"unexpected errors: {errors}")

    def test_non_dict_input_returns_invalid_type_error(self) -> None:
        for bad in (None, [], "string", 42, 1.5, ()):
            with self.subTest(value=bad):
                errors = validate_architecture_orchestrator_contract(bad)
                self.assertEqual(len(errors), 1)
                self.assertTrue(
                    errors[0].startswith("invalid type: contract expected dict")
                )

    def test_wrong_version_triggers_invalid_value_error(self) -> None:
        contract = get_architecture_orchestrator_contract()
        contract["version"] = "architecture_orchestrator.skeleton.v2"
        errors = validate_architecture_orchestrator_contract(contract)
        self.assertTrue(
            any(e.startswith("invalid value: version") for e in errors),
            msg=f"expected version error; got {errors}",
        )

    def test_wrong_status_triggers_invalid_value_error(self) -> None:
        contract = get_architecture_orchestrator_contract()
        contract["status"] = "wired_in"
        errors = validate_architecture_orchestrator_contract(contract)
        self.assertTrue(
            any(e.startswith("invalid value: status") for e in errors),
            msg=f"expected status error; got {errors}",
        )

    def test_each_forbidden_flag_flipped_true_triggers_error(self) -> None:
        for flag in (
            "active_path_connected",
            "db_write_enabled",
            "trading_enabled",
            "replay_enabled",
            "calibration_enabled",
            "holdout_run_enabled",
        ):
            with self.subTest(flag=flag):
                contract = get_architecture_orchestrator_contract()
                contract[flag] = True
                errors = validate_architecture_orchestrator_contract(contract)
                self.assertTrue(
                    any(
                        e.startswith(
                            f"invalid value: {flag} expected False"
                        )
                        for e in errors
                    ),
                    msg=f"expected error for {flag}=True; got {errors}",
                )

    def test_each_forbidden_flag_set_to_truthy_non_bool_triggers_error(
        self,
    ) -> None:
        for flag in (
            "active_path_connected",
            "db_write_enabled",
            "trading_enabled",
            "replay_enabled",
            "calibration_enabled",
            "holdout_run_enabled",
        ):
            for bad in (1, "yes", "True", [1]):
                with self.subTest(flag=flag, value=bad):
                    contract = get_architecture_orchestrator_contract()
                    contract[flag] = bad
                    errors = validate_architecture_orchestrator_contract(
                        contract
                    )
                    self.assertTrue(
                        any(
                            e.startswith(
                                f"invalid value: {flag} expected False"
                            )
                            for e in errors
                        ),
                        msg=(
                            f"expected error for {flag}={bad!r}; got {errors}"
                        ),
                    )

    def test_corrupted_layer_sequence_triggers_error(self) -> None:
        contract = get_architecture_orchestrator_contract()
        contract["allowed_layer_sequence"] = ["data", "feature"]  # missing
        errors = validate_architecture_orchestrator_contract(contract)
        self.assertTrue(
            any(
                e.startswith("invalid value: allowed_layer_sequence")
                for e in errors
            ),
            msg=f"expected layer sequence error; got {errors}",
        )

    def test_layer_sequence_wrong_order_triggers_error(self) -> None:
        contract = get_architecture_orchestrator_contract()
        # Swap two layers.
        seq = list(ALLOWED_LAYER_SEQUENCE)
        seq[0], seq[1] = seq[1], seq[0]
        contract["allowed_layer_sequence"] = seq
        errors = validate_architecture_orchestrator_contract(contract)
        self.assertTrue(
            any(
                e.startswith("invalid value: allowed_layer_sequence")
                for e in errors
            )
        )

    def test_layer_sequence_non_list_triggers_error(self) -> None:
        for bad in (None, "data,feature", 42, ()):
            with self.subTest(value=bad):
                contract = get_architecture_orchestrator_contract()
                contract["allowed_layer_sequence"] = bad
                errors = validate_architecture_orchestrator_contract(contract)
                self.assertTrue(
                    any(
                        e.startswith("invalid value: allowed_layer_sequence")
                        for e in errors
                    )
                )

    def test_missing_forbidden_active_path_action_triggers_error(self) -> None:
        contract = get_architecture_orchestrator_contract()
        # Drop one entry — should be flagged.
        contract["forbidden_active_path_actions"] = [
            a
            for a in FORBIDDEN_ACTIVE_PATH_ACTIONS
            if a != "run_predict"
        ]
        errors = validate_architecture_orchestrator_contract(contract)
        self.assertIn(
            "missing forbidden_active_path_actions entry: run_predict",
            errors,
        )

    def test_forbidden_active_path_actions_non_list_triggers_error(
        self,
    ) -> None:
        for bad in (None, "string", 42, set()):
            with self.subTest(value=bad):
                contract = get_architecture_orchestrator_contract()
                contract["forbidden_active_path_actions"] = bad
                errors = validate_architecture_orchestrator_contract(contract)
                self.assertTrue(
                    any(
                        e.startswith(
                            "invalid type: forbidden_active_path_actions"
                        )
                        for e in errors
                    )
                )

    def test_missing_forbidden_output_field_triggers_error(self) -> None:
        contract = get_architecture_orchestrator_contract()
        contract["forbidden_output_fields"] = [
            f for f in FORBIDDEN_OUTPUT_FIELDS if f != "buy"
        ]
        errors = validate_architecture_orchestrator_contract(contract)
        self.assertIn("missing forbidden_output_fields entry: buy", errors)

    def test_forbidden_output_fields_non_list_triggers_error(self) -> None:
        for bad in (None, "string", 42, set()):
            with self.subTest(value=bad):
                contract = get_architecture_orchestrator_contract()
                contract["forbidden_output_fields"] = bad
                errors = validate_architecture_orchestrator_contract(contract)
                self.assertTrue(
                    any(
                        e.startswith(
                            "invalid type: forbidden_output_fields"
                        )
                        for e in errors
                    )
                )

    def test_top_level_forbidden_field_present_triggers_error(self) -> None:
        for forbidden in (
            "buy",
            "sell",
            "hold",
            "hard",
            "forced",
            "required",
            "trading_action",
        ):
            with self.subTest(forbidden=forbidden):
                contract = get_architecture_orchestrator_contract()
                contract[forbidden] = "anything"
                errors = validate_architecture_orchestrator_contract(contract)
                self.assertIn(
                    f"forbidden field: {forbidden} at top-level",
                    errors,
                )


# ---------------------------------------------------------------------------
# 4. Contract dict isolation (no shared state across calls)
# ---------------------------------------------------------------------------

class ContractIsolationTests(unittest.TestCase):
    def test_returned_dicts_are_independent(self) -> None:
        a = get_architecture_orchestrator_contract()
        b = get_architecture_orchestrator_contract()
        self.assertIsNot(a, b)
        self.assertIsNot(
            a["allowed_layer_sequence"], b["allowed_layer_sequence"]
        )
        self.assertIsNot(
            a["forbidden_active_path_actions"],
            b["forbidden_active_path_actions"],
        )
        self.assertIsNot(
            a["forbidden_output_fields"], b["forbidden_output_fields"]
        )
        self.assertIsNot(a["notes"], b["notes"])

    def test_mutating_returned_dict_does_not_affect_next_call(self) -> None:
        first = get_architecture_orchestrator_contract()
        first["status"] = "MUTATED"
        first["allowed_layer_sequence"].append("MUTATED")
        first["forbidden_active_path_actions"].append("MUTATED")
        first["forbidden_output_fields"].append("MUTATED")
        first["notes"].append("MUTATED")

        second = get_architecture_orchestrator_contract()
        self.assertEqual(second["status"], "skeleton_only")
        self.assertEqual(
            second["allowed_layer_sequence"], list(ALLOWED_LAYER_SEQUENCE)
        )
        self.assertEqual(
            tuple(second["forbidden_active_path_actions"]),
            FORBIDDEN_ACTIVE_PATH_ACTIONS,
        )
        self.assertEqual(
            tuple(second["forbidden_output_fields"]),
            FORBIDDEN_OUTPUT_FIELDS,
        )
        self.assertNotIn("MUTATED", second["notes"])


# ---------------------------------------------------------------------------
# 5. Module import boundary (source-level scan)
# ---------------------------------------------------------------------------

class ModuleImportBoundaryTests(unittest.TestCase):
    """``services/architecture_orchestrator.py`` must remain a pure
    skeleton with zero coupling to any business / orchestrator / UI /
    DB / yfinance / pandas / streamlit / broker module."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = _read("services/architecture_orchestrator.py")

    def test_no_data_or_feature_or_business_imports(self) -> None:
        forbidden = (
            "from data_fetcher",
            "import data_fetcher",
            "from feature_builder",
            "import feature_builder",
            "from scanner",
            "import scanner",
            "from matcher",
            "import matcher",
            "from encoder",
            "import encoder",
            "from services.feature_payload_adapter",
            "import services.feature_payload_adapter",
            "from services.projection_result_adapter",
            "import services.projection_result_adapter",
            "from services.exclusion_result_adapter",
            "import services.exclusion_result_adapter",
            "from services.main_projection_layer",
            "import services.main_projection_layer",
            "from services.exclusion_layer",
            "import services.exclusion_layer",
            "from services.peer_alignment",
            "import services.peer_alignment",
            "from services.confidence_evaluator",
            "import services.confidence_evaluator",
            "from services.final_decision",
            "import services.final_decision",
            "from services.consistency_layer",
            "import services.consistency_layer",
            "from services.review_orchestrator",
            "import services.review_orchestrator",
            "from services.prediction_store",
            "import services.prediction_store",
            "from services.market_data_store",
            "import services.market_data_store",
        )
        for token in forbidden:
            self.assertNotIn(
                token, self.source,
                msg=f"architecture_orchestrator.py must not contain `{token}`",
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
        for token in forbidden:
            self.assertNotIn(
                token, self.source,
                msg=f"architecture_orchestrator.py must not contain `{token}`",
            )

    def test_no_predict_app_ui_imports(self) -> None:
        forbidden = (
            "from predict",
            "import predict",
            "from app",
            "import app",
            "from ui",
            "import ui",
            "import streamlit",
            "from streamlit",
        )
        for token in forbidden:
            self.assertNotIn(
                token, self.source,
                msg=f"architecture_orchestrator.py must not contain `{token}`",
            )

    def test_no_db_or_yfinance_or_pandas_imports(self) -> None:
        forbidden = (
            "import sqlite3",
            "from sqlite3",
            "import yfinance",
            "from yfinance",
            "import pandas",
            "from pandas",
        )
        for token in forbidden:
            self.assertNotIn(
                token, self.source,
                msg=f"architecture_orchestrator.py must not contain `{token}`",
            )

    def test_no_broker_or_oms_imports(self) -> None:
        for module_name in (
            "broker",
            "longbridge",
            "ib_insync",
            "ibapi",
            "alpaca",
            "tda",
            "paper_trade",
        ):
            for prefix in ("from ", "import "):
                token = f"{prefix}{module_name}"
                with self.subTest(token=token):
                    self.assertNotIn(token, self.source)

    def test_no_io_or_llm_calls(self) -> None:
        for token in (
            "open(",
            "Path(",
            "requests.",
            "urllib",
            "http.client",
            "openai",
            "OpenAI",
            "anthropic",
            "Anthropic",
        ):
            self.assertNotIn(
                token, self.source,
                msg=f"architecture_orchestrator.py must not contain `{token}`",
            )


# ---------------------------------------------------------------------------
# 6. No active execution surface
# ---------------------------------------------------------------------------

class NoActiveExecutionSurfaceTests(unittest.TestCase):
    """The skeleton must not define any ``run`` / ``orchestrate`` /
    ``execute`` / ``main`` entry point that could be wired by accident.
    The only callable surface is the documented contract helpers."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = _read("services/architecture_orchestrator.py")

    def test_no_run_orchestrate_execute_main_definitions(self) -> None:
        for forbidden in (
            "def run(",
            "def run_",
            "def orchestrate(",
            "def execute(",
            "def main(",
            "def assemble(",
            "def wire(",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(
                    forbidden, self.source,
                    msg=(
                        f"architecture_orchestrator.py must not define "
                        f"`{forbidden}` — skeleton has no execution "
                        "surface"
                    ),
                )

    def test_no_call_into_business_subsystems(self) -> None:
        for forbidden_call in (
            "run_predict(",
            "build_main_projection_layer(",
            "run_main_projection_layer(",
            "run_exclusion_layer(",
            "build_confidence_result(",
            "build_final_decision(",
            "build_home_terminal_orchestrator_result(",
            "run_projection_v2(",
        ):
            with self.subTest(forbidden=forbidden_call):
                self.assertNotIn(
                    forbidden_call, self.source,
                    msg=(
                        f"architecture_orchestrator.py must not call "
                        f"{forbidden_call!r} — skeleton-only"
                    ),
                )


# ---------------------------------------------------------------------------
# 7. Public surface stable
# ---------------------------------------------------------------------------

class PublicSurfaceTests(unittest.TestCase):
    """Pin the skeleton's public surface so future PRs cannot quietly
    add execution helpers next to the contract module."""

    EXPECTED_PUBLIC_NAMES = {
        # Constants
        "ARCHITECTURE_ORCHESTRATOR_VERSION",
        "ARCHITECTURE_ORCHESTRATOR_STATUS",
        "ALLOWED_LAYER_SEQUENCE",
        "FORBIDDEN_ACTIVE_PATH_ACTIONS",
        "FORBIDDEN_OUTPUT_FIELDS",
        # Functions
        "get_architecture_orchestrator_contract",
        "validate_architecture_orchestrator_contract",
    }

    def test_each_expected_public_name_exists(self) -> None:
        for name in self.EXPECTED_PUBLIC_NAMES:
            with self.subTest(name=name):
                self.assertTrue(
                    hasattr(arch_mod, name),
                    msg=f"missing expected public name: {name}",
                )

    def test_no_unexpected_public_callables(self) -> None:
        actual_public = {
            name
            for name, value in inspect.getmembers(
                arch_mod, predicate=inspect.isfunction
            )
            if not name.startswith("_")
            and value.__module__ == "services.architecture_orchestrator"
        }
        unexpected = actual_public - self.EXPECTED_PUBLIC_NAMES
        self.assertEqual(
            unexpected, set(),
            msg=(
                f"architecture_orchestrator gained unexpected public "
                f"callables: {unexpected} — skeleton must remain a thin "
                "ownership doc"
            ),
        )


# ---------------------------------------------------------------------------
# 8. Source-level forbidden tokens
# ---------------------------------------------------------------------------

class SourceLevelForbiddenTokenTests(unittest.TestCase):
    """The skeleton source must not contain trading / forced / required
    tokens as quoted assignment targets (the constants list these as
    metadata, not as outputs)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = _read("services/architecture_orchestrator.py")

    def test_no_assignment_to_buy_sell_hold(self) -> None:
        for forbidden in (
            'result["buy"',
            "result['buy'",
            'result["sell"',
            "result['sell'",
            'result["hold"',
            "result['hold'",
            'result["trading_action"',
            "result['trading_action'",
            'result["hard"',
            "result['hard'",
            'result["forced"',
            "result['forced'",
            'result["required"',
            "result['required'",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(
                    forbidden, self.source,
                    msg=(
                        f"architecture_orchestrator.py must not assign "
                        f"{forbidden!r}"
                    ),
                )

    def test_no_db_or_io_or_replay_call_sites(self) -> None:
        for forbidden in (
            "sqlite3.connect(",
            ".to_csv(",
            ".write(",
            ".execute(",
            "subprocess.",
            "yf.",
            "yfinance.",
            "st.markdown",
            "st.write",
            "st.json",
            "ticker.history",
            "Ticker(",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(
                    forbidden, self.source,
                    msg=(
                        f"architecture_orchestrator.py must not contain "
                        f"{forbidden!r}"
                    ),
                )


# ---------------------------------------------------------------------------
# Sanity: module reference
# ---------------------------------------------------------------------------

class ModuleReferenceTests(unittest.TestCase):
    def test_helpers_live_in_module(self) -> None:
        self.assertEqual(
            get_architecture_orchestrator_contract.__module__,
            "services.architecture_orchestrator",
        )
        self.assertEqual(
            validate_architecture_orchestrator_contract.__module__,
            "services.architecture_orchestrator",
        )

    def test_module_has_no_unexpected_classes(self) -> None:
        # The skeleton is function-based; no class definitions expected.
        classes = {
            name
            for name, value in inspect.getmembers(
                arch_mod, predicate=inspect.isclass
            )
            if value.__module__ == "services.architecture_orchestrator"
        }
        self.assertEqual(
            classes, set(),
            msg=f"architecture_orchestrator should not define classes; got {classes}",
        )


if __name__ == "__main__":
    unittest.main()
