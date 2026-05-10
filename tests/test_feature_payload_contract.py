"""Boundary + contract tests for ``services.feature_payload_contract``
(Step 18B / PR-FEATURE-1).

Spec source of truth:

- `tasks/record_1_0_architecture_reset_canonical_principles.md` §8 (Branch 2)
- `tasks/record_17f_feature_layer_rebuild_plan.md` §6 / §13
- `tasks/record_18a_first_layer_based_implementation_batch_selection.md` §13

PR-FEATURE-1 is a **pure addition** — a new schema constant + validator
with zero changes to any existing business code. This suite verifies:

1. valid minimal feature_payload returns ``[]``
2. non-dict payload returns error (no raise)
3. wrong ``schema_version`` returns ``invalid value:``
4. each missing top-level section returns ``missing section:``
5. each missing ``metadata`` required key returns ``missing field:``
6. ``data_window_days != 15`` produces a ``warning:`` line
7. invalid ``price_basis`` returns ``invalid value:``
8. each missing ``returns`` required key returns ``missing field:``
9. each missing ``position`` required key returns ``missing field:``
10. each missing ``volume`` required key returns ``missing field:``
11. each missing ``candle`` required key returns ``missing field:``
12. each missing ``data_quality`` required key returns ``missing field:``
13. forbidden system-result sections at top level are rejected
14. forbidden trading / hard / forced fields at top level are rejected
15. validator does not mutate input
16. module import boundary: the validator does **not** import any
    business / orchestrator / UI / DB module
17. ``FEATURE_PAYLOAD_SECTIONS`` matches the expected fixed order
18. ``FEATURE_PAYLOAD_SCHEMA_VERSION`` equals ``"feature_payload.v1"``

The validator must never raise (returns errors as a list).
"""

from __future__ import annotations

import copy
import unittest
from pathlib import Path

import services.feature_payload_contract as fpc_mod
from services.feature_payload_contract import (
    ALLOWED_PRICE_BASIS,
    FEATURE_PAYLOAD_SCHEMA_VERSION,
    FEATURE_PAYLOAD_SECTIONS,
    FORBIDDEN_FIELDS,
    RECOMMENDED_DATA_WINDOW_DAYS,
    validate_feature_payload,
)


_REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(rel: str) -> str:
    return (_REPO_ROOT / rel).read_text(encoding="utf-8")


def _valid_minimal_payload() -> dict:
    """Build a payload that satisfies every PR-FEATURE-1 shape rule."""
    return {
        "schema_version": FEATURE_PAYLOAD_SCHEMA_VERSION,
        "metadata": {
            "symbol": "AVGO",
            "analysis_date": "2026-05-08",
            "target_date": "2026-05-09",
            "data_window_days": RECOMMENDED_DATA_WINDOW_DAYS,
            "window_label": "T-15..T-1",
            "price_basis": "raw",
        },
        "ohlcv_window": [],
        "returns": {
            "ret1": 0.0,
            "ret3": 0.0,
            "ret5": 0.0,
            "ret10": 0.0,
        },
        "position": {
            "pos15": 0.5,
            "pos20": 0.5,
            "pos30": 0.5,
        },
        "volume": {
            "volume": 0,
            "volume_ratio": 1.0,
        },
        "candle": {
            "upper_shadow_ratio": 0.0,
            "lower_shadow_ratio": 0.0,
        },
        "peer_alignment": {},
        "code_features": {},
        "data_quality": {
            "missing_fields": [],
            "source": "local_csv",
            "stale_flag": False,
        },
    }


# ---------------------------------------------------------------------------
# 0. Constants (test items 17 + 18)
# ---------------------------------------------------------------------------

class FeaturePayloadConstantsTests(unittest.TestCase):
    def test_schema_version_is_v1(self) -> None:
        self.assertEqual(FEATURE_PAYLOAD_SCHEMA_VERSION, "feature_payload.v1")

    def test_ten_top_level_sections_in_fixed_order(self) -> None:
        self.assertEqual(
            FEATURE_PAYLOAD_SECTIONS,
            (
                "schema_version",
                "metadata",
                "ohlcv_window",
                "returns",
                "position",
                "volume",
                "candle",
                "peer_alignment",
                "code_features",
                "data_quality",
            ),
        )

    def test_recommended_data_window_days_is_15(self) -> None:
        self.assertEqual(RECOMMENDED_DATA_WINDOW_DAYS, 15)

    def test_allowed_price_basis_is_raw_adj_dual(self) -> None:
        self.assertEqual(ALLOWED_PRICE_BASIS, frozenset({"raw", "adj", "dual"}))

    def test_forbidden_fields_includes_system_results(self) -> None:
        for required in (
            "projection_result",
            "exclusion_result",
            "confidence_result",
            "final_report",
            "review_result",
            "evaluation_result",
        ):
            self.assertIn(
                required, FORBIDDEN_FIELDS,
                msg=f"FORBIDDEN_FIELDS must include {required!r}",
            )

    def test_forbidden_fields_includes_trading_and_forced_tokens(self) -> None:
        for required in (
            "trading_action",
            "order",
            "position_action",
            "execution",
            "buy",
            "sell",
            "hold",
            "hard",
            "forced",
            "required",
        ):
            self.assertIn(
                required, FORBIDDEN_FIELDS,
                msg=f"FORBIDDEN_FIELDS must include {required!r}",
            )

    def test_position_section_is_not_forbidden(self) -> None:
        # ``position`` is a required feature section in feature_payload.v1
        # (price-position features such as pos15 / pos20 / pos30); it must
        # NOT collide with the forbidden ``position_action`` key.
        self.assertNotIn("position", FORBIDDEN_FIELDS)
        self.assertIn("position_action", FORBIDDEN_FIELDS)


# ---------------------------------------------------------------------------
# 1. Valid minimal payload returns []
# ---------------------------------------------------------------------------

class ValidMinimalPayloadTests(unittest.TestCase):
    def test_valid_minimal_payload_returns_empty_list(self) -> None:
        errors = validate_feature_payload(_valid_minimal_payload())
        self.assertEqual(errors, [], msg=f"unexpected errors: {errors}")

    def test_each_allowed_price_basis_is_valid(self) -> None:
        for basis in ("raw", "adj", "dual"):
            with self.subTest(price_basis=basis):
                payload = _valid_minimal_payload()
                payload["metadata"]["price_basis"] = basis
                errors = validate_feature_payload(payload)
                self.assertEqual(
                    errors, [], msg=f"unexpected errors for {basis}: {errors}"
                )


# ---------------------------------------------------------------------------
# 2. Non-dict payload returns error (no raise)
# ---------------------------------------------------------------------------

class NonDictPayloadTests(unittest.TestCase):
    def test_none_payload(self) -> None:
        errors = validate_feature_payload(None)
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("invalid type: payload expected dict"))

    def test_list_payload(self) -> None:
        errors = validate_feature_payload([])
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("invalid type: payload expected dict"))

    def test_str_payload(self) -> None:
        errors = validate_feature_payload("not a dict")
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("invalid type: payload expected dict"))

    def test_int_payload(self) -> None:
        errors = validate_feature_payload(42)
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("invalid type: payload expected dict"))

    def test_non_dict_input_does_not_raise(self) -> None:
        # Validator must never raise (regression guard).
        for value in (None, 42, "x", [], (), 1.5, object()):
            with self.subTest(value=value):
                result = validate_feature_payload(value)
                self.assertIsInstance(result, list)


# ---------------------------------------------------------------------------
# 3. Wrong schema_version
# ---------------------------------------------------------------------------

class SchemaVersionTests(unittest.TestCase):
    def test_wrong_schema_version_returns_invalid_value_error(self) -> None:
        payload = _valid_minimal_payload()
        payload["schema_version"] = "feature_payload.v2"
        errors = validate_feature_payload(payload)
        matches = [e for e in errors if e.startswith("invalid value: schema_version")]
        self.assertEqual(
            len(matches), 1,
            msg=f"expected one schema_version error; got {matches} (all: {errors})",
        )


# ---------------------------------------------------------------------------
# 4. Missing top-level section
# ---------------------------------------------------------------------------

class MissingTopLevelSectionTests(unittest.TestCase):
    def test_each_missing_section_yields_missing_section_error(self) -> None:
        for section in FEATURE_PAYLOAD_SECTIONS:
            with self.subTest(section=section):
                payload = _valid_minimal_payload()
                payload.pop(section)
                errors = validate_feature_payload(payload)
                self.assertIn(
                    f"missing section: {section}",
                    errors,
                    msg=f"validator did not catch missing {section}; got {errors}",
                )


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
            "window_label",
            "price_basis",
        ):
            with self.subTest(key=key):
                payload = _valid_minimal_payload()
                payload["metadata"].pop(key)
                errors = validate_feature_payload(payload)
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
        errors = validate_feature_payload(payload)
        warnings = [e for e in errors if e.startswith("warning: metadata.data_window_days")]
        self.assertEqual(
            len(warnings), 1,
            msg=f"expected one window warning; got {warnings} (all: {errors})",
        )

    def test_data_window_days_15_does_not_emit_warning(self) -> None:
        payload = _valid_minimal_payload()
        # already 15; full payload should validate clean.
        errors = validate_feature_payload(payload)
        warnings = [e for e in errors if e.startswith("warning:")]
        self.assertEqual(warnings, [])

    def test_validator_does_not_auto_correct_window(self) -> None:
        # The validator emits an advisory but does NOT touch the value.
        payload = _valid_minimal_payload()
        payload["metadata"]["data_window_days"] = 20
        validate_feature_payload(payload)
        self.assertEqual(payload["metadata"]["data_window_days"], 20)


# ---------------------------------------------------------------------------
# 7. Invalid price_basis returns error
# ---------------------------------------------------------------------------

class PriceBasisTests(unittest.TestCase):
    def test_invalid_price_basis_returns_invalid_value_error(self) -> None:
        for basis in ("RAW", "raw_adj", "close", "", "unknown"):
            with self.subTest(price_basis=basis):
                payload = _valid_minimal_payload()
                payload["metadata"]["price_basis"] = basis
                errors = validate_feature_payload(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid value: metadata.price_basis")
                ]
                self.assertEqual(
                    len(matches), 1,
                    msg=f"expected one price_basis error for {basis!r}; got {matches}",
                )


# ---------------------------------------------------------------------------
# 8. Missing returns required keys
# ---------------------------------------------------------------------------

class MissingReturnsKeysTests(unittest.TestCase):
    def test_each_missing_returns_key_yields_missing_field_error(self) -> None:
        for key in ("ret1", "ret3", "ret5", "ret10"):
            with self.subTest(key=key):
                payload = _valid_minimal_payload()
                payload["returns"].pop(key)
                errors = validate_feature_payload(payload)
                self.assertIn(
                    f"missing field: returns.{key}", errors
                )


# ---------------------------------------------------------------------------
# 9. Missing position required keys
# ---------------------------------------------------------------------------

class MissingPositionKeysTests(unittest.TestCase):
    def test_each_missing_position_key_yields_missing_field_error(self) -> None:
        for key in ("pos15", "pos20", "pos30"):
            with self.subTest(key=key):
                payload = _valid_minimal_payload()
                payload["position"].pop(key)
                errors = validate_feature_payload(payload)
                self.assertIn(
                    f"missing field: position.{key}", errors
                )


# ---------------------------------------------------------------------------
# 10. Missing volume required keys
# ---------------------------------------------------------------------------

class MissingVolumeKeysTests(unittest.TestCase):
    def test_each_missing_volume_key_yields_missing_field_error(self) -> None:
        for key in ("volume", "volume_ratio"):
            with self.subTest(key=key):
                payload = _valid_minimal_payload()
                payload["volume"].pop(key)
                errors = validate_feature_payload(payload)
                self.assertIn(
                    f"missing field: volume.{key}", errors
                )


# ---------------------------------------------------------------------------
# 11. Missing candle required keys
# ---------------------------------------------------------------------------

class MissingCandleKeysTests(unittest.TestCase):
    def test_each_missing_candle_key_yields_missing_field_error(self) -> None:
        for key in ("upper_shadow_ratio", "lower_shadow_ratio"):
            with self.subTest(key=key):
                payload = _valid_minimal_payload()
                payload["candle"].pop(key)
                errors = validate_feature_payload(payload)
                self.assertIn(
                    f"missing field: candle.{key}", errors
                )


# ---------------------------------------------------------------------------
# 12. Missing data_quality required keys
# ---------------------------------------------------------------------------

class MissingDataQualityKeysTests(unittest.TestCase):
    def test_each_missing_data_quality_key_yields_missing_field_error(self) -> None:
        for key in ("missing_fields", "source", "stale_flag"):
            with self.subTest(key=key):
                payload = _valid_minimal_payload()
                payload["data_quality"].pop(key)
                errors = validate_feature_payload(payload)
                self.assertIn(
                    f"missing field: data_quality.{key}", errors
                )


# ---------------------------------------------------------------------------
# 13. Forbidden system-result sections at top level are rejected
# ---------------------------------------------------------------------------

class ForbiddenSystemResultSectionsTests(unittest.TestCase):
    def test_forbidden_system_result_sections_at_top_level(self) -> None:
        for forbidden in (
            "projection_result",
            "exclusion_result",
            "confidence_result",
            "final_report",
            "review_result",
            "evaluation_result",
        ):
            with self.subTest(forbidden=forbidden):
                payload = _valid_minimal_payload()
                payload[forbidden] = {}
                errors = validate_feature_payload(payload)
                self.assertIn(
                    f"forbidden field: {forbidden} at top-level",
                    errors,
                    msg=f"validator did not flag {forbidden} at top-level; got {errors}",
                )


# ---------------------------------------------------------------------------
# 14. Forbidden trading / hard / forced fields at top level are rejected
# ---------------------------------------------------------------------------

class ForbiddenTradingForcedFieldsTests(unittest.TestCase):
    def test_forbidden_trading_and_forced_at_top_level(self) -> None:
        for forbidden in (
            "trading_action",
            "order",
            "position_action",
            "execution",
            "buy",
            "sell",
            "hold",
            "hard",
            "forced",
            "required",
        ):
            with self.subTest(forbidden=forbidden):
                payload = _valid_minimal_payload()
                payload[forbidden] = "anything"
                errors = validate_feature_payload(payload)
                self.assertIn(
                    f"forbidden field: {forbidden} at top-level",
                    errors,
                    msg=f"validator did not flag {forbidden} at top-level; got {errors}",
                )


# ---------------------------------------------------------------------------
# 15. Validator does not mutate input
# ---------------------------------------------------------------------------

class NonMutationTests(unittest.TestCase):
    def test_valid_payload_unchanged(self) -> None:
        payload = _valid_minimal_payload()
        snapshot = copy.deepcopy(payload)
        validate_feature_payload(payload)
        self.assertEqual(payload, snapshot)

    def test_invalid_payload_unchanged(self) -> None:
        payload = _valid_minimal_payload()
        payload.pop("metadata")  # makes it invalid
        snapshot = copy.deepcopy(payload)
        errors = validate_feature_payload(payload)
        self.assertNotEqual(errors, [])
        self.assertEqual(payload, snapshot)

    def test_pure_function_repeatable_output(self) -> None:
        payload = _valid_minimal_payload()
        first = validate_feature_payload(payload)
        second = validate_feature_payload(payload)
        self.assertEqual(first, second)


# ---------------------------------------------------------------------------
# 16. Module import boundary
# ---------------------------------------------------------------------------

class ImportBoundaryTests(unittest.TestCase):
    """``services.feature_payload_contract`` must remain a pure shape
    validator with zero coupling to any business / orchestrator / UI / DB
    module."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = _read("services/feature_payload_contract.py")

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
            "from services.review_orchestrator",
            "import services.review_orchestrator",
            "from services.predict_summary",
            "import services.predict_summary",
            "from services.ai_summary",
            "import services.ai_summary",
            "from predict",
            "import predict",
            "from app",
            "import app",
            "from ui",
            "import ui",
            "import sqlite3",
            "from sqlite3",
            "import yfinance",
            "from yfinance",
            "import streamlit",
            "from streamlit",
        )
        for f in forbidden:
            self.assertNotIn(
                f,
                self.source,
                msg=f"services.feature_payload_contract must not contain `{f}`",
            )

    def test_no_io_or_llm_calls(self) -> None:
        for f in ("open(", "Path(", "requests.", "urllib", "http.client",
                  "openai", "OpenAI", "anthropic", "Anthropic"):
            self.assertNotIn(
                f,
                self.source,
                msg=f"services.feature_payload_contract must not contain `{f}`",
            )


# ---------------------------------------------------------------------------
# Sanity check on module reference
# ---------------------------------------------------------------------------

class ModuleReferenceTests(unittest.TestCase):
    def test_validate_function_lives_in_module(self) -> None:
        self.assertEqual(
            validate_feature_payload.__module__,
            "services.feature_payload_contract",
        )
        self.assertIs(
            fpc_mod.validate_feature_payload,
            validate_feature_payload,
        )


if __name__ == "__main__":
    unittest.main()
