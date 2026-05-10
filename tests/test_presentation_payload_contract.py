"""Boundary + contract tests for ``ui.presentation_payload_contract``
(Step 18I / PR-UI-1).

Spec source of truth:

- `tasks/record_1_0_architecture_reset_canonical_principles.md` §8 (Branch 9)
- `tasks/record_17m_ui_presentation_layer_rebuild_plan.md` §8 / §13 / §15
- `tasks/record_18a_first_layer_based_implementation_batch_selection.md` §13

PR-UI-1 is a **pure addition** — a new schema constant + validator with
zero changes to any existing UI / business code. This suite verifies:

1.  valid minimal payload returns ``[]``
2.  non-dict payload returns error (no raise)
3.  wrong ``schema_version`` returns ``invalid value:``
4.  each missing top-level section returns ``missing section:``
5.  ``kind`` must equal ``"presentation"``
6.  ``page_id`` must be a non-empty string
7.  ``tab_id`` must be a non-empty string
8.  ``source_payload_schema_version`` must be str or None
9.  ``source_payload_ref`` must be str / dict / None
10. ``display_sections`` must be a list
11. ``display_sections`` dict item missing ``id`` / ``title`` / ``content``
    returns warning
12. ``cards`` must be a list
13. ``cards`` dict item missing ``id`` / ``title`` / ``body`` returns warning
14. ``tables`` must be a list
15. ``charts`` must be a list
16. ``warnings`` must be a list
17. ``missing_sections`` must be a list
18. ``compatibility_mode`` must be a valid enum
19. ``compatibility_notes`` must be list or str
20. ``generated_at`` must be str or None
21. ``raw_payload_ref`` must be str / dict / None
22. missing ``no_mutation_confirmations`` required keys returns error
23. ``no_mutation_confirmations`` required values must be ``True``
24. forbidden upstream result sections rejected
25. forbidden business result fields rejected
26. forbidden legacy bridge fields rejected
27. forbidden execution / active path fields rejected
28. forbidden trading / hard / forced fields rejected
29. validator does not mutate input payload
30. module import boundary
31. ``PRESENTATION_PAYLOAD_SECTIONS`` matches the expected fixed order
32. ``PRESENTATION_PAYLOAD_SCHEMA_VERSION`` equals ``"presentation_payload.v1"``
33. ``PRESENTATION_PAYLOAD_KIND`` equals ``"presentation"``
34. ``VALID_COMPATIBILITY_MODE`` equals expected values

The validator must never raise (returns errors as a list).
"""

from __future__ import annotations

import copy
import unittest
from pathlib import Path

import ui.presentation_payload_contract as ppc_mod
from ui.presentation_payload_contract import (
    FORBIDDEN_FIELDS,
    PRESENTATION_PAYLOAD_KIND,
    PRESENTATION_PAYLOAD_SCHEMA_VERSION,
    PRESENTATION_PAYLOAD_SECTIONS,
    VALID_COMPATIBILITY_MODE,
    validate_presentation_payload,
)


_REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(rel: str) -> str:
    return (_REPO_ROOT / rel).read_text(encoding="utf-8")


def _valid_minimal_payload() -> dict:
    """Build a payload that satisfies every PR-UI-1 shape rule."""
    return {
        "schema_version": PRESENTATION_PAYLOAD_SCHEMA_VERSION,
        "kind": PRESENTATION_PAYLOAD_KIND,
        "page_id": "predict",
        "tab_id": "predict_tab",
        "source_payload_schema_version": "final_report_result.v1",
        "source_payload_ref": None,
        "display_sections": [],
        "cards": [],
        "tables": [],
        "charts": [],
        "warnings": [],
        "missing_sections": [],
        "compatibility_mode": "standard",
        "compatibility_notes": [],
        "generated_at": "2026-05-10T00:00:00Z",
        "raw_payload_ref": None,
        "no_mutation_confirmations": {
            "ui_did_not_mutate_source_payload": True,
            "ui_did_not_recompute_projection": True,
            "ui_did_not_recompute_exclusion": True,
            "ui_did_not_recompute_confidence": True,
            "ui_did_not_run_replay": True,
            "ui_did_not_write_db": True,
        },
    }


# ---------------------------------------------------------------------------
# 0. Constants (test items 31-34)
# ---------------------------------------------------------------------------

class PresentationPayloadConstantsTests(unittest.TestCase):
    def test_schema_version_is_v1(self) -> None:
        self.assertEqual(
            PRESENTATION_PAYLOAD_SCHEMA_VERSION, "presentation_payload.v1"
        )

    def test_kind_is_presentation(self) -> None:
        self.assertEqual(PRESENTATION_PAYLOAD_KIND, "presentation")

    def test_seventeen_top_level_sections_in_fixed_order(self) -> None:
        self.assertEqual(
            PRESENTATION_PAYLOAD_SECTIONS,
            (
                "schema_version",
                "kind",
                "page_id",
                "tab_id",
                "source_payload_schema_version",
                "source_payload_ref",
                "display_sections",
                "cards",
                "tables",
                "charts",
                "warnings",
                "missing_sections",
                "compatibility_mode",
                "compatibility_notes",
                "generated_at",
                "raw_payload_ref",
                "no_mutation_confirmations",
            ),
        )

    def test_valid_compatibility_mode_enum(self) -> None:
        self.assertEqual(
            VALID_COMPATIBILITY_MODE,
            ("standard", "compatibility_fallback", "missing_sections", "unknown"),
        )

    def test_forbidden_fields_includes_upstream_result_sections(self) -> None:
        for required in (
            "feature_payload",
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

    def test_forbidden_fields_includes_business_result_keys(self) -> None:
        for required in (
            "most_likely_state",
            "most_unlikely_state",
            "agreement_status",
            "combined_confidence",
        ):
            self.assertIn(required, FORBIDDEN_FIELDS)

    def test_forbidden_fields_includes_legacy_bridge_keys(self) -> None:
        for required in (
            "final_direction",
            "final_confidence",
            "final_bias",
            "primary_projection",
            "final_projection",
            "peer_adjustment",
            "path_risk",
        ):
            self.assertIn(
                required, FORBIDDEN_FIELDS,
                msg=f"FORBIDDEN_FIELDS must include {required!r}",
            )

    def test_forbidden_fields_includes_active_path_keys(self) -> None:
        for required in ("run_predict", "replay_result", "calibration_result"):
            self.assertIn(
                required, FORBIDDEN_FIELDS,
                msg=f"FORBIDDEN_FIELDS must include {required!r}",
            )

    def test_forbidden_fields_includes_trading_and_forced_tokens(self) -> None:
        for required in (
            "trading_action",
            "buy",
            "sell",
            "hold",
            "hard",
            "forced",
            "required",
            "live_trade",
            "broker_order",
        ):
            self.assertIn(required, FORBIDDEN_FIELDS)


# ---------------------------------------------------------------------------
# 1. Valid minimal payload returns []
# ---------------------------------------------------------------------------

class ValidMinimalPayloadTests(unittest.TestCase):
    def test_valid_minimal_payload_returns_empty_list(self) -> None:
        errors = validate_presentation_payload(_valid_minimal_payload())
        self.assertEqual(errors, [], msg=f"unexpected errors: {errors}")

    def test_each_compatibility_mode_is_accepted(self) -> None:
        for value in VALID_COMPATIBILITY_MODE:
            with self.subTest(compatibility_mode=value):
                payload = _valid_minimal_payload()
                payload["compatibility_mode"] = value
                errors = validate_presentation_payload(payload)
                bad = [
                    e for e in errors
                    if e.startswith("invalid value: compatibility_mode")
                ]
                self.assertEqual(bad, [])

    def test_display_sections_with_complete_dict_is_ok(self) -> None:
        payload = _valid_minimal_payload()
        payload["display_sections"] = [
            {"id": "sec-1", "title": "标题", "content": "正文"},
        ]
        errors = validate_presentation_payload(payload)
        self.assertEqual(errors, [])

    def test_cards_with_complete_dict_is_ok(self) -> None:
        payload = _valid_minimal_payload()
        payload["cards"] = [
            {"id": "card-1", "title": "标题", "body": "正文"},
        ]
        errors = validate_presentation_payload(payload)
        self.assertEqual(errors, [])

    def test_source_payload_ref_dict_is_ok(self) -> None:
        payload = _valid_minimal_payload()
        payload["source_payload_ref"] = {"prediction_id": "pred-1"}
        payload["raw_payload_ref"] = "ref://predictions/pred-1"
        errors = validate_presentation_payload(payload)
        self.assertEqual(errors, [])


# ---------------------------------------------------------------------------
# 2. Non-dict payload returns error (no raise)
# ---------------------------------------------------------------------------

class NonDictPayloadTests(unittest.TestCase):
    def test_none_payload(self) -> None:
        errors = validate_presentation_payload(None)
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("invalid type: payload expected dict"))

    def test_list_payload(self) -> None:
        errors = validate_presentation_payload([])
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("invalid type: payload expected dict"))

    def test_str_payload(self) -> None:
        errors = validate_presentation_payload("not a dict")
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("invalid type: payload expected dict"))

    def test_int_payload(self) -> None:
        errors = validate_presentation_payload(42)
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("invalid type: payload expected dict"))

    def test_non_dict_input_does_not_raise(self) -> None:
        for value in (None, 42, "x", [], (), 1.5, object()):
            with self.subTest(value=value):
                result = validate_presentation_payload(value)
                self.assertIsInstance(result, list)


# ---------------------------------------------------------------------------
# 3. Wrong schema_version
# ---------------------------------------------------------------------------

class SchemaVersionTests(unittest.TestCase):
    def test_wrong_schema_version_returns_invalid_value_error(self) -> None:
        payload = _valid_minimal_payload()
        payload["schema_version"] = "presentation_payload.v2"
        errors = validate_presentation_payload(payload)
        matches = [e for e in errors if e.startswith("invalid value: schema_version")]
        self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 4. Missing top-level section
# ---------------------------------------------------------------------------

class MissingTopLevelSectionTests(unittest.TestCase):
    def test_each_missing_section_yields_missing_section_error(self) -> None:
        for section in PRESENTATION_PAYLOAD_SECTIONS:
            with self.subTest(section=section):
                payload = _valid_minimal_payload()
                payload.pop(section)
                errors = validate_presentation_payload(payload)
                self.assertIn(
                    f"missing section: {section}",
                    errors,
                    msg=f"validator did not catch missing {section}; got {errors}",
                )


# ---------------------------------------------------------------------------
# 5. kind must equal "presentation"
# ---------------------------------------------------------------------------

class KindTests(unittest.TestCase):
    def test_wrong_kind_returns_invalid_value_error(self) -> None:
        for bad in ("display", "view_model", "tab", "", None, 42):
            with self.subTest(kind=bad):
                payload = _valid_minimal_payload()
                payload["kind"] = bad
                errors = validate_presentation_payload(payload)
                matches = [e for e in errors if e.startswith("invalid value: kind")]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 6. page_id must be non-empty string
# ---------------------------------------------------------------------------

class PageIdTests(unittest.TestCase):
    def test_page_id_must_be_non_empty_string(self) -> None:
        for bad in ("", None, 42, [], {}):
            with self.subTest(page_id=bad):
                payload = _valid_minimal_payload()
                payload["page_id"] = bad
                errors = validate_presentation_payload(payload)
                matches = [
                    e for e in errors if e.startswith("invalid value: page_id")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 7. tab_id must be non-empty string
# ---------------------------------------------------------------------------

class TabIdTests(unittest.TestCase):
    def test_tab_id_must_be_non_empty_string(self) -> None:
        for bad in ("", None, 42, [], {}):
            with self.subTest(tab_id=bad):
                payload = _valid_minimal_payload()
                payload["tab_id"] = bad
                errors = validate_presentation_payload(payload)
                matches = [
                    e for e in errors if e.startswith("invalid value: tab_id")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 8. source_payload_schema_version must be str or None
# ---------------------------------------------------------------------------

class SourcePayloadSchemaVersionTests(unittest.TestCase):
    def test_must_be_str_or_none(self) -> None:
        for bad in (42, 1.5, [], {}):
            with self.subTest(source_payload_schema_version=bad):
                payload = _valid_minimal_payload()
                payload["source_payload_schema_version"] = bad
                errors = validate_presentation_payload(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid type: source_payload_schema_version")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 9. source_payload_ref must be str / dict / None
# ---------------------------------------------------------------------------

class SourcePayloadRefTests(unittest.TestCase):
    def test_must_be_str_dict_or_none(self) -> None:
        for bad in (42, 1.5, [], True):
            with self.subTest(source_payload_ref=bad):
                payload = _valid_minimal_payload()
                payload["source_payload_ref"] = bad
                errors = validate_presentation_payload(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid type: source_payload_ref")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 10. display_sections must be list
# ---------------------------------------------------------------------------

class DisplaySectionsTypeTests(unittest.TestCase):
    def test_display_sections_must_be_list(self) -> None:
        for bad in ({}, "list", 42, None):
            with self.subTest(display_sections=bad):
                payload = _valid_minimal_payload()
                payload["display_sections"] = bad
                errors = validate_presentation_payload(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid type: display_sections")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 11. display_sections dict missing id/title/content emits warning
# ---------------------------------------------------------------------------

class DisplaySectionsAdvisoryTests(unittest.TestCase):
    def test_missing_id_emits_warning(self) -> None:
        payload = _valid_minimal_payload()
        payload["display_sections"] = [{"title": "标题", "content": "正文"}]
        errors = validate_presentation_payload(payload)
        warnings = [
            e for e in errors
            if e.startswith("warning: display_sections[0] dict missing 'id'")
        ]
        self.assertEqual(len(warnings), 1)

    def test_missing_title_emits_warning(self) -> None:
        payload = _valid_minimal_payload()
        payload["display_sections"] = [{"id": "x", "content": "正文"}]
        errors = validate_presentation_payload(payload)
        warnings = [
            e for e in errors
            if e.startswith("warning: display_sections[0] dict missing 'title'")
        ]
        self.assertEqual(len(warnings), 1)

    def test_missing_content_emits_warning(self) -> None:
        payload = _valid_minimal_payload()
        payload["display_sections"] = [{"id": "x", "title": "标题"}]
        errors = validate_presentation_payload(payload)
        warnings = [
            e for e in errors
            if e.startswith("warning: display_sections[0] dict missing 'content'")
        ]
        self.assertEqual(len(warnings), 1)

    def test_non_dict_item_does_not_emit_advisory(self) -> None:
        payload = _valid_minimal_payload()
        payload["display_sections"] = ["plain string section"]
        errors = validate_presentation_payload(payload)
        warnings = [e for e in errors if e.startswith("warning: display_sections")]
        self.assertEqual(warnings, [])

    def test_validator_does_not_auto_correct_display_sections(self) -> None:
        payload = _valid_minimal_payload()
        payload["display_sections"] = [{"other": "x"}]
        snapshot = copy.deepcopy(payload["display_sections"])
        validate_presentation_payload(payload)
        self.assertEqual(payload["display_sections"], snapshot)


# ---------------------------------------------------------------------------
# 12. cards must be list
# ---------------------------------------------------------------------------

class CardsTypeTests(unittest.TestCase):
    def test_cards_must_be_list(self) -> None:
        for bad in ({}, "list", 42, None):
            with self.subTest(cards=bad):
                payload = _valid_minimal_payload()
                payload["cards"] = bad
                errors = validate_presentation_payload(payload)
                matches = [e for e in errors if e.startswith("invalid type: cards")]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 13. cards dict missing id/title/body emits warning
# ---------------------------------------------------------------------------

class CardsAdvisoryTests(unittest.TestCase):
    def test_missing_id_emits_warning(self) -> None:
        payload = _valid_minimal_payload()
        payload["cards"] = [{"title": "标题", "body": "正文"}]
        errors = validate_presentation_payload(payload)
        warnings = [
            e for e in errors
            if e.startswith("warning: cards[0] dict missing 'id'")
        ]
        self.assertEqual(len(warnings), 1)

    def test_missing_title_emits_warning(self) -> None:
        payload = _valid_minimal_payload()
        payload["cards"] = [{"id": "x", "body": "正文"}]
        errors = validate_presentation_payload(payload)
        warnings = [
            e for e in errors
            if e.startswith("warning: cards[0] dict missing 'title'")
        ]
        self.assertEqual(len(warnings), 1)

    def test_missing_body_emits_warning(self) -> None:
        payload = _valid_minimal_payload()
        payload["cards"] = [{"id": "x", "title": "标题"}]
        errors = validate_presentation_payload(payload)
        warnings = [
            e for e in errors
            if e.startswith("warning: cards[0] dict missing 'body'")
        ]
        self.assertEqual(len(warnings), 1)

    def test_non_dict_item_does_not_emit_advisory(self) -> None:
        payload = _valid_minimal_payload()
        payload["cards"] = ["plain string card"]
        errors = validate_presentation_payload(payload)
        warnings = [e for e in errors if e.startswith("warning: cards")]
        self.assertEqual(warnings, [])


# ---------------------------------------------------------------------------
# 14 / 15 / 16 / 17. tables / charts / warnings / missing_sections
# must be list
# ---------------------------------------------------------------------------

class ListFieldsTests(unittest.TestCase):
    def test_each_list_field_must_be_list(self) -> None:
        for field in ("tables", "charts", "warnings", "missing_sections"):
            for bad in ({}, "list", 42, None):
                with self.subTest(field=field, value=bad):
                    payload = _valid_minimal_payload()
                    payload[field] = bad
                    errors = validate_presentation_payload(payload)
                    matches = [
                        e for e in errors
                        if e.startswith(f"invalid type: {field}")
                    ]
                    self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 18. compatibility_mode must be valid enum
# ---------------------------------------------------------------------------

class CompatibilityModeTests(unittest.TestCase):
    def test_invalid_compatibility_mode_returns_error(self) -> None:
        for bad in ("STANDARD", "legacy_fallback", "v2_unified_passthrough",
                    "", None, 42):
            with self.subTest(compatibility_mode=bad):
                payload = _valid_minimal_payload()
                payload["compatibility_mode"] = bad
                errors = validate_presentation_payload(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid value: compatibility_mode")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 19. compatibility_notes must be list or str
# ---------------------------------------------------------------------------

class CompatibilityNotesTests(unittest.TestCase):
    def test_compatibility_notes_must_be_list_or_str(self) -> None:
        for bad in ({}, 42, None, True):
            with self.subTest(compatibility_notes=bad):
                payload = _valid_minimal_payload()
                payload["compatibility_notes"] = bad
                errors = validate_presentation_payload(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid type: compatibility_notes")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 20. generated_at must be str or None
# ---------------------------------------------------------------------------

class GeneratedAtTests(unittest.TestCase):
    def test_generated_at_must_be_str_or_none(self) -> None:
        for bad in (42, 1.5, [], {}):
            with self.subTest(generated_at=bad):
                payload = _valid_minimal_payload()
                payload["generated_at"] = bad
                errors = validate_presentation_payload(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid type: generated_at")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 21. raw_payload_ref must be str / dict / None
# ---------------------------------------------------------------------------

class RawPayloadRefTests(unittest.TestCase):
    def test_raw_payload_ref_must_be_str_dict_or_none(self) -> None:
        for bad in (42, 1.5, [], True):
            with self.subTest(raw_payload_ref=bad):
                payload = _valid_minimal_payload()
                payload["raw_payload_ref"] = bad
                errors = validate_presentation_payload(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid type: raw_payload_ref")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 22. Missing no_mutation_confirmations required keys
# ---------------------------------------------------------------------------

class MissingNoMutationConfirmationKeysTests(unittest.TestCase):
    def test_each_missing_key_yields_missing_field_error(self) -> None:
        for key in (
            "ui_did_not_mutate_source_payload",
            "ui_did_not_recompute_projection",
            "ui_did_not_recompute_exclusion",
            "ui_did_not_recompute_confidence",
            "ui_did_not_run_replay",
            "ui_did_not_write_db",
        ):
            with self.subTest(key=key):
                payload = _valid_minimal_payload()
                payload["no_mutation_confirmations"].pop(key)
                errors = validate_presentation_payload(payload)
                self.assertIn(
                    f"missing field: no_mutation_confirmations.{key}",
                    errors,
                )


# ---------------------------------------------------------------------------
# 23. no_mutation_confirmations required values must be True
# ---------------------------------------------------------------------------

class NoMutationConfirmationValueTests(unittest.TestCase):
    def test_each_required_key_must_be_true(self) -> None:
        for key in (
            "ui_did_not_mutate_source_payload",
            "ui_did_not_recompute_projection",
            "ui_did_not_recompute_exclusion",
            "ui_did_not_recompute_confidence",
            "ui_did_not_run_replay",
            "ui_did_not_write_db",
        ):
            for bad in (False, None, 0, 1, "true", []):
                with self.subTest(key=key, value=bad):
                    payload = _valid_minimal_payload()
                    payload["no_mutation_confirmations"][key] = bad
                    errors = validate_presentation_payload(payload)
                    self.assertTrue(
                        any(
                            e.startswith(
                                f"invalid value: no_mutation_confirmations.{key}"
                            )
                            for e in errors
                        ),
                        msg=f"expected error for {key}={bad!r}; got {errors}",
                    )


# ---------------------------------------------------------------------------
# 24. Forbidden upstream result sections rejected
# ---------------------------------------------------------------------------

class ForbiddenUpstreamSectionsTests(unittest.TestCase):
    def test_forbidden_upstream_at_top_level(self) -> None:
        for forbidden in (
            "feature_payload",
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
                errors = validate_presentation_payload(payload)
                self.assertIn(
                    f"forbidden field: {forbidden} at top-level",
                    errors,
                )


# ---------------------------------------------------------------------------
# 25. Forbidden business result fields rejected
# ---------------------------------------------------------------------------

class ForbiddenBusinessResultFieldsTests(unittest.TestCase):
    def test_forbidden_business_result_at_top_level(self) -> None:
        for forbidden in (
            "most_likely_state",
            "most_unlikely_state",
            "agreement_status",
            "combined_confidence",
        ):
            with self.subTest(forbidden=forbidden):
                payload = _valid_minimal_payload()
                payload[forbidden] = "anything"
                errors = validate_presentation_payload(payload)
                self.assertIn(
                    f"forbidden field: {forbidden} at top-level",
                    errors,
                )


# ---------------------------------------------------------------------------
# 26. Forbidden legacy bridge fields rejected
# ---------------------------------------------------------------------------

class ForbiddenLegacyBridgeFieldsTests(unittest.TestCase):
    def test_forbidden_legacy_bridge_at_top_level(self) -> None:
        for forbidden in (
            "final_direction",
            "final_confidence",
            "final_bias",
            "primary_projection",
            "final_projection",
            "peer_adjustment",
            "path_risk",
        ):
            with self.subTest(forbidden=forbidden):
                payload = _valid_minimal_payload()
                payload[forbidden] = "anything"
                errors = validate_presentation_payload(payload)
                self.assertIn(
                    f"forbidden field: {forbidden} at top-level",
                    errors,
                )


# ---------------------------------------------------------------------------
# 27. Forbidden execution / active path fields rejected
# ---------------------------------------------------------------------------

class ForbiddenActivePathFieldsTests(unittest.TestCase):
    def test_forbidden_active_path_at_top_level(self) -> None:
        for forbidden in ("run_predict", "replay_result", "calibration_result"):
            with self.subTest(forbidden=forbidden):
                payload = _valid_minimal_payload()
                payload[forbidden] = "anything"
                errors = validate_presentation_payload(payload)
                self.assertIn(
                    f"forbidden field: {forbidden} at top-level",
                    errors,
                )


# ---------------------------------------------------------------------------
# 28. Forbidden trading / hard / forced fields rejected
# ---------------------------------------------------------------------------

class ForbiddenTradingForcedFieldsTests(unittest.TestCase):
    def test_forbidden_trading_and_forced_at_top_level(self) -> None:
        for forbidden in (
            "trading_action",
            "buy",
            "sell",
            "hold",
            "hard",
            "forced",
            "required",
            "live_trade",
            "broker_order",
        ):
            with self.subTest(forbidden=forbidden):
                payload = _valid_minimal_payload()
                payload[forbidden] = "anything"
                errors = validate_presentation_payload(payload)
                self.assertIn(
                    f"forbidden field: {forbidden} at top-level",
                    errors,
                )


# ---------------------------------------------------------------------------
# 29. Validator does not mutate input
# ---------------------------------------------------------------------------

class NonMutationTests(unittest.TestCase):
    def test_valid_payload_unchanged(self) -> None:
        payload = _valid_minimal_payload()
        snapshot = copy.deepcopy(payload)
        validate_presentation_payload(payload)
        self.assertEqual(payload, snapshot)

    def test_invalid_payload_unchanged(self) -> None:
        payload = _valid_minimal_payload()
        payload.pop("compatibility_mode")
        snapshot = copy.deepcopy(payload)
        errors = validate_presentation_payload(payload)
        self.assertNotEqual(errors, [])
        self.assertEqual(payload, snapshot)

    def test_pure_function_repeatable_output(self) -> None:
        payload = _valid_minimal_payload()
        first = validate_presentation_payload(payload)
        second = validate_presentation_payload(payload)
        self.assertEqual(first, second)


# ---------------------------------------------------------------------------
# 30. Module import boundary
# ---------------------------------------------------------------------------

class ImportBoundaryTests(unittest.TestCase):
    """``ui.presentation_payload_contract`` must remain a pure shape
    validator with zero coupling to streamlit / app / ui tabs / services /
    DB / business modules."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = _read("ui/presentation_payload_contract.py")

    def test_no_streamlit_import(self) -> None:
        for f in (
            "import streamlit",
            "from streamlit",
        ):
            self.assertNotIn(
                f,
                self.source,
                msg=f"ui.presentation_payload_contract must not contain `{f}`",
            )

    def test_no_app_import(self) -> None:
        for f in (
            "from app",
            "import app",
        ):
            self.assertNotIn(
                f,
                self.source,
                msg=f"ui.presentation_payload_contract must not contain `{f}`",
            )

    def test_no_ui_tab_imports(self) -> None:
        forbidden = (
            "from ui.home_tab",
            "import ui.home_tab",
            "from ui.predict_tab",
            "import ui.predict_tab",
            "from ui.history_tab",
            "import ui.history_tab",
            "from ui.review_tab",
            "import ui.review_tab",
            "from ui.research_tab",
            "import ui.research_tab",
            "from ui.inspect_tab",
            "import ui.inspect_tab",
            "from ui.scan_tab",
            "import ui.scan_tab",
            "from ui.control_tab",
            "import ui.control_tab",
            "from ui.command_bar",
            "import ui.command_bar",
            "from ui.projection_v2_renderer",
            "import ui.projection_v2_renderer",
            "from ui.protection_layer_diagnostics_renderer",
            "import ui.protection_layer_diagnostics_renderer",
            "from ui.soft_metadata_renderer",
            "import ui.soft_metadata_renderer",
            "from ui.anti_false_exclusion_display",
            "import ui.anti_false_exclusion_display",
            "from ui.big_up_contradiction_card",
            "import ui.big_up_contradiction_card",
            "from ui.exclusion_reliability_review",
            "import ui.exclusion_reliability_review",
            "from ui.labels",
            "import ui.labels",
            "from ui.soft_metadata_baseline_cache",
            "import ui.soft_metadata_baseline_cache",
        )
        for f in forbidden:
            self.assertNotIn(
                f,
                self.source,
                msg=f"ui.presentation_payload_contract must not contain `{f}`",
            )

    def test_no_services_import(self) -> None:
        for f in (
            "from services",
            "import services",
        ):
            self.assertNotIn(
                f,
                self.source,
                msg=f"ui.presentation_payload_contract must not contain `{f}`",
            )

    def test_no_predict_or_orchestrator_or_db_imports(self) -> None:
        forbidden = (
            "from predict",
            "import predict",
            "import sqlite3",
            "from sqlite3",
            "import yfinance",
            "from yfinance",
        )
        for f in forbidden:
            self.assertNotIn(
                f,
                self.source,
                msg=f"ui.presentation_payload_contract must not contain `{f}`",
            )

    def test_no_io_or_llm_calls(self) -> None:
        for f in ("open(", "Path(", "requests.", "urllib", "http.client",
                  "openai", "OpenAI", "anthropic", "Anthropic"):
            self.assertNotIn(
                f,
                self.source,
                msg=f"ui.presentation_payload_contract must not contain `{f}`",
            )


# ---------------------------------------------------------------------------
# Sanity check on module reference
# ---------------------------------------------------------------------------

class ModuleReferenceTests(unittest.TestCase):
    def test_validate_function_lives_in_module(self) -> None:
        self.assertEqual(
            validate_presentation_payload.__module__,
            "ui.presentation_payload_contract",
        )
        self.assertIs(
            ppc_mod.validate_presentation_payload,
            validate_presentation_payload,
        )


if __name__ == "__main__":
    unittest.main()
