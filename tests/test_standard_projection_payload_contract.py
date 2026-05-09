"""Boundary + contract tests for ``services.standard_projection_payload``
(Step 17A / PR-B).

Spec source of truth:

- `tasks/record_1_0_architecture_reset_canonical_principles.md` §8 / §10
- `tasks/record_16c_target_dataflow_contract_decision.md` §5 / §6
- `tasks/record_16i_core_chain_rebuild_execution_plan.md` §6

PR-B is a **pure addition** — a new schema constant + validator with
zero changes to any existing business code. This suite verifies:

1. valid minimal payload returns ``[]``
2. each missing top-level section returns a corresponding error
3. wrong ``schema_version`` returns an ``invalid value:`` error
4. non-dict payload returns an ``invalid type:`` error (no raise)
5. each missing ``metadata`` required key returns ``missing field:``
6. ``data_window_days != 15`` produces a ``warning:`` line
7. each missing ``projection_result`` required key returns ``missing field:``
8. each missing ``exclusion_result`` required key returns ``missing field:``
9. each missing ``confidence_result`` required key returns ``missing field:``
10. each missing ``final_report`` required key returns ``missing field:``
11. forbidden trading / hard / forced fields at top-level OR inside
    ``final_report`` produce ``forbidden field:`` errors
12. module import boundary: the validator does **not** import any
    business / orchestrator / UI / DB module
13. ``validate_standard_projection_payload`` does **not** mutate input

The validator must never raise (`returns errors as a list`).
"""

from __future__ import annotations

import copy
import unittest
from pathlib import Path

import services.standard_projection_payload as spp_mod
from services.standard_projection_payload import (
    FORBIDDEN_FIELDS,
    RECOMMENDED_DATA_WINDOW_DAYS,
    SCHEMA_VERSION,
    STANDARD_PAYLOAD_SECTIONS,
    validate_standard_projection_payload,
)


_REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(rel: str) -> str:
    return (_REPO_ROOT / rel).read_text(encoding="utf-8")


def _valid_minimal_payload() -> dict:
    """Build a payload that satisfies every PR-B shape rule."""
    return {
        "schema_version": SCHEMA_VERSION,
        "metadata": {
            "symbol": "AVGO",
            "analysis_date": "2026-05-08",
            "target_date": "2026-05-09",
            "data_window_days": RECOMMENDED_DATA_WINDOW_DAYS,
            "non_mutation_confirmations": {
                "projection_result_mutated": False,
                "exclusion_result_mutated": False,
                "confidence_result_mutated": False,
                "final_report_mutated": False,
            },
        },
        "feature_payload": {},
        "projection_result": {
            "most_likely_state": "小涨",
            "ranked_states": ["小涨", "震荡", "大涨", "小跌", "大跌"],
            "state_probabilities": {
                "大涨": 0.10,
                "小涨": 0.40,
                "震荡": 0.30,
                "小跌": 0.15,
                "大跌": 0.05,
            },
            "evidence": [],
            "raw_score": None,
        },
        "exclusion_result": {
            "most_unlikely_state": "大跌",
            "excluded_states": ["大跌"],
            "false_exclusion_risk": {"level": "low"},
            "evidence": [],
            "triggered_rules": [],
        },
        "confidence_result": {
            "projection_confidence": {"level": "unknown"},
            "exclusion_confidence": {"level": "unknown"},
            "agreement_status": "unknown",
            "conflict_level": "unknown",
            "combined_confidence": {"level": "unknown"},
            "calibration_notes": [],
        },
        "final_report": {
            "summary": "minimal",
            "key_points": [],
            "risks": [],
            "evidence_summary": [],
        },
        "review_stub": {},
        "evaluation_stub": {},
        "compatibility_metadata": {},
    }


# ---------------------------------------------------------------------------
# 0. Constants
# ---------------------------------------------------------------------------

class StandardPayloadConstantsTests(unittest.TestCase):
    def test_schema_version_is_v1(self) -> None:
        self.assertEqual(SCHEMA_VERSION, "standard_projection_payload.v1")

    def test_ten_top_level_sections_in_fixed_order(self) -> None:
        self.assertEqual(
            STANDARD_PAYLOAD_SECTIONS,
            (
                "schema_version",
                "metadata",
                "feature_payload",
                "projection_result",
                "exclusion_result",
                "confidence_result",
                "final_report",
                "review_stub",
                "evaluation_stub",
                "compatibility_metadata",
            ),
        )

    def test_recommended_data_window_days_is_15(self) -> None:
        self.assertEqual(RECOMMENDED_DATA_WINDOW_DAYS, 15)

    def test_forbidden_fields_includes_trading_and_hard_forced_required(self) -> None:
        for required in (
            "buy", "sell", "hold",
            "trading_action", "simulated_trade", "no_trade",
            "order", "position", "execution",
            "hard", "forced", "required",
            "hard_exclusion", "forced_exclusion", "required_decision",
            "production_promotion", "_PROTECTION_LAYER_CONNECTED",
        ):
            self.assertIn(
                required, FORBIDDEN_FIELDS,
                msg=f"FORBIDDEN_FIELDS must include {required!r}",
            )


# ---------------------------------------------------------------------------
# 1. Valid minimal payload returns []
# ---------------------------------------------------------------------------

class ValidMinimalPayloadTests(unittest.TestCase):
    def test_valid_minimal_payload_returns_empty_list(self) -> None:
        errors = validate_standard_projection_payload(_valid_minimal_payload())
        self.assertEqual(errors, [], msg=f"unexpected errors: {errors}")


# ---------------------------------------------------------------------------
# 2. Missing top-level section
# ---------------------------------------------------------------------------

class MissingTopLevelSectionTests(unittest.TestCase):
    def test_each_missing_section_yields_missing_section_error(self) -> None:
        for section in STANDARD_PAYLOAD_SECTIONS:
            with self.subTest(section=section):
                payload = _valid_minimal_payload()
                payload.pop(section)
                errors = validate_standard_projection_payload(payload)
                self.assertIn(
                    f"missing section: {section}",
                    errors,
                    msg=f"validator did not catch missing {section}; got {errors}",
                )


# ---------------------------------------------------------------------------
# 3. Wrong schema_version
# ---------------------------------------------------------------------------

class SchemaVersionTests(unittest.TestCase):
    def test_wrong_schema_version_returns_invalid_value_error(self) -> None:
        payload = _valid_minimal_payload()
        payload["schema_version"] = "standard_projection_payload.v2"
        errors = validate_standard_projection_payload(payload)
        matches = [e for e in errors if e.startswith("invalid value: schema_version")]
        self.assertEqual(
            len(matches), 1,
            msg=f"expected one schema_version error; got {matches} (all errors: {errors})",
        )


# ---------------------------------------------------------------------------
# 4. Non-dict payload returns error (no raise)
# ---------------------------------------------------------------------------

class NonDictPayloadTests(unittest.TestCase):
    def test_none_payload(self) -> None:
        errors = validate_standard_projection_payload(None)
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("invalid type: payload expected dict"))

    def test_list_payload(self) -> None:
        errors = validate_standard_projection_payload([])
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("invalid type: payload expected dict"))

    def test_str_payload(self) -> None:
        errors = validate_standard_projection_payload("not a dict")
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("invalid type: payload expected dict"))

    def test_int_payload(self) -> None:
        errors = validate_standard_projection_payload(42)
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("invalid type: payload expected dict"))


# ---------------------------------------------------------------------------
# 5. Missing metadata required keys
# ---------------------------------------------------------------------------

class MissingMetadataKeysTests(unittest.TestCase):
    def test_each_missing_metadata_key_yields_missing_field_error(self) -> None:
        for key in (
            "symbol",
            "analysis_date",
            "target_date",
            "data_window_days",
            "non_mutation_confirmations",
        ):
            with self.subTest(key=key):
                payload = _valid_minimal_payload()
                payload["metadata"].pop(key)
                errors = validate_standard_projection_payload(payload)
                self.assertIn(
                    f"missing field: metadata.{key}",
                    errors,
                    msg=f"validator did not catch missing metadata.{key}; got {errors}",
                )


# ---------------------------------------------------------------------------
# 6. data_window_days != 15 produces warning
# ---------------------------------------------------------------------------

class DataWindowDaysAdvisoryTests(unittest.TestCase):
    def test_data_window_days_20_emits_warning(self) -> None:
        payload = _valid_minimal_payload()
        payload["metadata"]["data_window_days"] = 20
        errors = validate_standard_projection_payload(payload)
        warnings = [e for e in errors if e.startswith("warning: metadata.data_window_days")]
        self.assertEqual(
            len(warnings), 1,
            msg=f"expected one window warning; got {warnings} (all: {errors})",
        )

    def test_data_window_days_15_does_not_emit_warning(self) -> None:
        payload = _valid_minimal_payload()
        # Already 15; full payload should validate clean.
        errors = validate_standard_projection_payload(payload)
        warnings = [e for e in errors if e.startswith("warning:")]
        self.assertEqual(warnings, [])


# ---------------------------------------------------------------------------
# 7. Missing projection_result required keys
# ---------------------------------------------------------------------------

class MissingProjectionResultKeysTests(unittest.TestCase):
    def test_each_missing_projection_key_yields_missing_field_error(self) -> None:
        for key in (
            "most_likely_state",
            "ranked_states",
            "state_probabilities",
            "evidence",
            "raw_score",
        ):
            with self.subTest(key=key):
                payload = _valid_minimal_payload()
                payload["projection_result"].pop(key)
                errors = validate_standard_projection_payload(payload)
                self.assertIn(
                    f"missing field: projection_result.{key}",
                    errors,
                )


# ---------------------------------------------------------------------------
# 8. Missing exclusion_result required keys
# ---------------------------------------------------------------------------

class MissingExclusionResultKeysTests(unittest.TestCase):
    def test_each_missing_exclusion_key_yields_missing_field_error(self) -> None:
        for key in (
            "most_unlikely_state",
            "excluded_states",
            "false_exclusion_risk",
            "evidence",
            "triggered_rules",
        ):
            with self.subTest(key=key):
                payload = _valid_minimal_payload()
                payload["exclusion_result"].pop(key)
                errors = validate_standard_projection_payload(payload)
                self.assertIn(
                    f"missing field: exclusion_result.{key}",
                    errors,
                )


# ---------------------------------------------------------------------------
# 9. Missing confidence_result required keys
# ---------------------------------------------------------------------------

class MissingConfidenceResultKeysTests(unittest.TestCase):
    def test_each_missing_confidence_key_yields_missing_field_error(self) -> None:
        for key in (
            "projection_confidence",
            "exclusion_confidence",
            "agreement_status",
            "conflict_level",
            "combined_confidence",
            "calibration_notes",
        ):
            with self.subTest(key=key):
                payload = _valid_minimal_payload()
                payload["confidence_result"].pop(key)
                errors = validate_standard_projection_payload(payload)
                self.assertIn(
                    f"missing field: confidence_result.{key}",
                    errors,
                )


# ---------------------------------------------------------------------------
# 10. Missing final_report required keys
# ---------------------------------------------------------------------------

class MissingFinalReportKeysTests(unittest.TestCase):
    def test_each_missing_final_report_key_yields_missing_field_error(self) -> None:
        for key in ("summary", "key_points", "risks", "evidence_summary"):
            with self.subTest(key=key):
                payload = _valid_minimal_payload()
                payload["final_report"].pop(key)
                errors = validate_standard_projection_payload(payload)
                self.assertIn(
                    f"missing field: final_report.{key}",
                    errors,
                )


# ---------------------------------------------------------------------------
# 11. Forbidden trading / hard / forced fields are rejected
# ---------------------------------------------------------------------------

class ForbiddenFieldsTests(unittest.TestCase):
    def test_forbidden_at_top_level(self) -> None:
        for forbidden in ("buy", "sell", "hold", "trading_action",
                          "hard", "forced", "required",
                          "hard_exclusion", "forced_exclusion", "required_decision",
                          "order", "position", "execution",
                          "simulated_trade", "production_promotion"):
            with self.subTest(forbidden=forbidden):
                payload = _valid_minimal_payload()
                payload[forbidden] = "anything"
                errors = validate_standard_projection_payload(payload)
                self.assertIn(
                    f"forbidden field: {forbidden} at top-level",
                    errors,
                    msg=f"validator did not flag {forbidden} at top-level; got {errors}",
                )

    def test_forbidden_inside_final_report(self) -> None:
        for forbidden in ("buy", "trading_action", "hard_exclusion",
                          "forced_exclusion", "required_decision",
                          "simulated_trade", "execution"):
            with self.subTest(forbidden=forbidden):
                payload = _valid_minimal_payload()
                payload["final_report"][forbidden] = "anything"
                errors = validate_standard_projection_payload(payload)
                self.assertIn(
                    f"forbidden field: {forbidden} at final_report",
                    errors,
                    msg=f"validator did not flag {forbidden} inside final_report; got {errors}",
                )


# ---------------------------------------------------------------------------
# 12. Module import boundary
# ---------------------------------------------------------------------------

class ImportBoundaryTests(unittest.TestCase):
    """``services.standard_projection_payload`` must remain a pure
    shape validator with zero coupling to any business / orchestrator /
    UI / DB module."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = _read("services/standard_projection_payload.py")

    def test_no_business_module_imports(self) -> None:
        forbidden = (
            "from services.predict_legacy_adapter",
            "import services.predict_legacy_adapter",
            "from services.predict_legacy_v2_bridge",
            "import services.predict_legacy_v2_bridge",
            "from services.projection_orchestrator",
            "import services.projection_orchestrator",
            "from services.projection_orchestrator_v2",
            "import services.projection_orchestrator_v2",
            "from services.home_terminal_orchestrator",
            "import services.home_terminal_orchestrator",
            "from services.main_projection_layer",
            "import services.main_projection_layer",
            "from services.exclusion_layer",
            "import services.exclusion_layer",
            "from services.confidence_evaluator",
            "import services.confidence_evaluator",
            "from services.final_decision",
            "import services.final_decision",
            "from services.consistency_layer",
            "import services.consistency_layer",
            "from services.predict_summary",
            "import services.predict_summary",
            "from services.ai_summary",
            "import services.ai_summary",
            "from predict",
            "import predict",
            "from ui",
            "import ui",
            "import sqlite3",
            "from sqlite3",
            "import yfinance",
            "from yfinance",
        )
        for f in forbidden:
            self.assertNotIn(
                f,
                self.source,
                msg=f"services.standard_projection_payload must not contain `{f}`",
            )

    def test_no_io_or_llm_calls(self) -> None:
        for f in ("open(", "Path(", "requests.", "urllib", "http.client",
                  "openai", "OpenAI"):
            self.assertNotIn(
                f,
                self.source,
                msg=f"services.standard_projection_payload must not contain `{f}`",
            )


# ---------------------------------------------------------------------------
# 13. Validator does not mutate input
# ---------------------------------------------------------------------------

class NonMutationTests(unittest.TestCase):
    def test_valid_payload_unchanged(self) -> None:
        payload = _valid_minimal_payload()
        snapshot = copy.deepcopy(payload)
        validate_standard_projection_payload(payload)
        self.assertEqual(payload, snapshot)

    def test_invalid_payload_unchanged(self) -> None:
        payload = _valid_minimal_payload()
        payload.pop("metadata")  # makes it invalid
        snapshot = copy.deepcopy(payload)
        errors = validate_standard_projection_payload(payload)
        self.assertNotEqual(errors, [])  # confirm we exercised the failure path
        self.assertEqual(payload, snapshot)

    def test_non_dict_input_does_not_raise(self) -> None:
        # Validator must never raise (regression guard).
        for value in (None, 42, "x", [], (), 1.5, object()):
            with self.subTest(value=value):
                # Just confirm it returns a list and does not raise.
                result = validate_standard_projection_payload(value)
                self.assertIsInstance(result, list)


# ---------------------------------------------------------------------------
# 14. Sanity check on module reference
# ---------------------------------------------------------------------------

class ModuleReferenceTests(unittest.TestCase):
    def test_validate_function_lives_in_module(self) -> None:
        self.assertEqual(
            validate_standard_projection_payload.__module__,
            "services.standard_projection_payload",
        )
        # Belt + suspenders: the function exposed through the module is
        # the same object as the one we imported.
        self.assertIs(
            spp_mod.validate_standard_projection_payload,
            validate_standard_projection_payload,
        )


if __name__ == "__main__":
    unittest.main()
