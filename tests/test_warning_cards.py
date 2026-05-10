"""Boundary + contract tests for ``services.warning_cards``
(Step 18W / PR-FINAL-4).

Spec source of truth:

- `tasks/record_1_0_architecture_reset_canonical_principles.md` §8 (Branch 6)
- `tasks/record_17j_final_report_layer_rebuild_plan.md` §9.4 / §13 PR-FINAL-4
- `tasks/record_18s_third_layer_based_implementation_batch_selection.md`
  §4 / §6 / §10

PR-FINAL-4 is a **pure addition** — a new schema constant + builder +
validator with zero changes to any existing business code. This suite
verifies:

 1. ``build_warning_card`` returns a ``warning_card.v1`` dict with the
    canonical 10 fields.
 2. ``validate_warning_card`` accepts a card built by
    ``build_warning_card``.
 3. ``validate_warning_cards`` accepts a list of valid cards.
 4. invalid ``type`` returns error.
 5. invalid ``severity`` returns error.
 6. each missing required field returns ``missing field:`` error.
 7. ``title`` / ``message`` / ``source_layer`` must be non-empty
    strings.
 8. ``evidence`` must be dict, list, or None.
 9. ``metadata`` must be dict or None.
10. ``blocking`` must be a bool.
11. ``build_warning_card`` deep-copies ``evidence`` / ``metadata``.
12. ``validate_warning_card`` does not mutate input.
13. forbidden trading keys (``buy`` / ``sell`` / ``hold`` /
    ``trading_action`` / ``order`` / ``execution``) are rejected at
    top level.
14. forbidden hard / forced / required keys are rejected at top level.
15. ``recommended_action`` containing ``buy`` / ``sell`` / ``hold`` is
    rejected.
16. ``recommended_action`` containing ``hard`` / ``forced`` /
    ``required`` is rejected.
17. ``contradiction`` card valid example.
18. ``tail_risk`` card valid example.
19. ``briefing_caution`` card valid example.
20. ``calibration`` card valid example.
21. ``data_quality`` card valid example.
22. ``system_boundary`` card valid example.
23. import boundary: no business / orchestrator / UI / DB module
    imports.
24. import boundary: no ``yfinance`` / ``pandas`` / ``streamlit``.
25. no ``run`` / ``execute`` / ``orchestrate`` / ``main`` entry
    functions.
26. module source has no trading-output return statements.

Plus supporting tests:

- ``cards`` non-list returns error.
- ``validate_warning_cards`` per-card errors carry ``cards[i]:``
  prefix.
- ``WARNING_CARD_REQUIRED_FIELDS`` matches the canonical fixed order.
- ``FORBIDDEN_WARNING_CARD_FIELDS`` includes the trading / forcing
  tokens.
- ``recommended_action`` allows descriptive strings such as
  ``"display_warning_only"`` / ``"review_before_trusting"``.
- ``recommended_action`` token guard does not flag ``"buyer beware"``
  (whole-token match).

The validator must never raise (returns errors as a list).
"""

from __future__ import annotations

import copy
import unittest
from pathlib import Path

import services.warning_cards as wc_mod
from services.warning_cards import (
    FORBIDDEN_WARNING_CARD_FIELDS,
    VALID_WARNING_SEVERITIES,
    VALID_WARNING_TYPES,
    WARNING_CARD_REQUIRED_FIELDS,
    WARNING_CARD_SCHEMA_VERSION,
    build_warning_card,
    validate_warning_card,
    validate_warning_cards,
)


_REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(rel: str) -> str:
    return (_REPO_ROOT / rel).read_text(encoding="utf-8")


def _valid_card(**overrides) -> dict:
    """Build a card that satisfies every PR-FINAL-4 shape rule."""
    base = build_warning_card(
        warning_type="contradiction",
        severity="medium",
        title="big_up_contradiction",
        message="primary 偏多 vs exclusion 否定 偏多",
        source_layer="final_report",
        evidence={"primary_direction": "偏多"},
        recommended_action="display_warning_only",
        blocking=False,
        metadata={"origin": "big_up_contradiction_card"},
    )
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# 0. Constants
# ---------------------------------------------------------------------------

class WarningCardConstantsTests(unittest.TestCase):
    def test_schema_version_is_v1(self) -> None:
        self.assertEqual(WARNING_CARD_SCHEMA_VERSION, "warning_card.v1")

    def test_required_fields_in_fixed_order(self) -> None:
        self.assertEqual(
            WARNING_CARD_REQUIRED_FIELDS,
            (
                "schema_version",
                "type",
                "severity",
                "title",
                "message",
                "source_layer",
                "evidence",
                "recommended_action",
                "blocking",
                "metadata",
            ),
        )

    def test_valid_types_includes_canonical_set(self) -> None:
        for required in (
            "contradiction",
            "tail_risk",
            "briefing_caution",
            "calibration",
            "data_quality",
            "system_boundary",
            "unknown",
        ):
            self.assertIn(required, VALID_WARNING_TYPES)

    def test_valid_severities_includes_canonical_set(self) -> None:
        for required in (
            "info",
            "low",
            "medium",
            "high",
            "critical",
            "unknown",
        ):
            self.assertIn(required, VALID_WARNING_SEVERITIES)

    def test_forbidden_fields_includes_trading_tokens(self) -> None:
        for required in (
            "buy",
            "sell",
            "hold",
            "trading_action",
            "order",
            "position_action",
            "execution",
            "broker_order",
            "live_trade",
        ):
            self.assertIn(
                required,
                FORBIDDEN_WARNING_CARD_FIELDS,
                msg=f"FORBIDDEN_WARNING_CARD_FIELDS must include {required!r}",
            )

    def test_forbidden_fields_includes_hard_forced_required(self) -> None:
        for required in ("hard", "forced", "required"):
            self.assertIn(
                required,
                FORBIDDEN_WARNING_CARD_FIELDS,
                msg=f"FORBIDDEN_WARNING_CARD_FIELDS must include {required!r}",
            )

    def test_forbidden_fields_includes_promotion_tokens(self) -> None:
        for required in ("active_rule_promotion", "promote_rule"):
            self.assertIn(
                required,
                FORBIDDEN_WARNING_CARD_FIELDS,
                msg=f"FORBIDDEN_WARNING_CARD_FIELDS must include {required!r}",
            )


# ---------------------------------------------------------------------------
# 1. build_warning_card returns warning_card.v1 dict
# ---------------------------------------------------------------------------

class BuildWarningCardTests(unittest.TestCase):
    def test_returns_dict_with_canonical_schema_version(self) -> None:
        card = _valid_card()
        self.assertIsInstance(card, dict)
        self.assertEqual(card["schema_version"], WARNING_CARD_SCHEMA_VERSION)

    def test_all_required_fields_present(self) -> None:
        card = _valid_card()
        for field in WARNING_CARD_REQUIRED_FIELDS:
            self.assertIn(field, card, msg=f"missing field {field!r}")

    def test_field_values_set_from_arguments(self) -> None:
        card = build_warning_card(
            warning_type="tail_risk",
            severity="high",
            title="big_down_tail",
            message="尾部风险偏高",
            source_layer="final_report",
        )
        self.assertEqual(card["type"], "tail_risk")
        self.assertEqual(card["severity"], "high")
        self.assertEqual(card["title"], "big_down_tail")
        self.assertEqual(card["message"], "尾部风险偏高")
        self.assertEqual(card["source_layer"], "final_report")

    def test_defaults_evidence_metadata_recommended_action_blocking(self) -> None:
        card = build_warning_card(
            warning_type="data_quality",
            severity="low",
            title="t",
            message="m",
            source_layer="data",
        )
        self.assertIsNone(card["evidence"])
        self.assertIsNone(card["metadata"])
        self.assertIsNone(card["recommended_action"])
        self.assertEqual(card["blocking"], False)

    def test_blocking_can_be_true(self) -> None:
        card = build_warning_card(
            warning_type="system_boundary",
            severity="critical",
            title="t",
            message="m",
            source_layer="architecture_orchestrator",
            blocking=True,
        )
        self.assertEqual(card["blocking"], True)


# ---------------------------------------------------------------------------
# 2 + 3. Valid card / list of valid cards passes validation
# ---------------------------------------------------------------------------

class ValidCardPassesValidationTests(unittest.TestCase):
    def test_valid_card_returns_empty_list(self) -> None:
        errors = validate_warning_card(_valid_card())
        self.assertEqual(errors, [], msg=f"unexpected errors: {errors}")

    def test_validate_warning_cards_accepts_list_of_valid(self) -> None:
        cards = [
            _valid_card(),
            _valid_card(type="tail_risk"),
            _valid_card(type="briefing_caution"),
        ]
        errors = validate_warning_cards(cards)
        self.assertEqual(errors, [], msg=f"unexpected errors: {errors}")

    def test_empty_list_returns_no_error(self) -> None:
        self.assertEqual(validate_warning_cards([]), [])


# ---------------------------------------------------------------------------
# Non-dict / non-list inputs
# ---------------------------------------------------------------------------

class NonDictAndNonListInputTests(unittest.TestCase):
    def test_validate_warning_card_non_dict(self) -> None:
        for bad in (None, 1, "card", [], (1, 2)):
            with self.subTest(card=bad):
                errors = validate_warning_card(bad)
                self.assertTrue(
                    any(e.startswith("invalid type: card expected dict")
                        for e in errors),
                    msg=f"unexpected errors: {errors}",
                )

    def test_validate_warning_cards_non_list(self) -> None:
        for bad in (None, 1, "cards", {}, (1, 2)):
            with self.subTest(cards=bad):
                errors = validate_warning_cards(bad)
                self.assertTrue(
                    any(e.startswith("invalid type: cards expected list")
                        for e in errors),
                    msg=f"unexpected errors: {errors}",
                )


# ---------------------------------------------------------------------------
# 4. Invalid type returns error
# ---------------------------------------------------------------------------

class InvalidTypeFieldTests(unittest.TestCase):
    def test_invalid_type_value(self) -> None:
        for bad in ("trade", "buy_signal", "", "TAIL_RISK", "execute"):
            with self.subTest(bad=bad):
                card = _valid_card(type=bad)
                errors = validate_warning_card(card)
                self.assertTrue(
                    any(e.startswith("invalid value: type expected one of")
                        for e in errors),
                    msg=f"unexpected errors: {errors}",
                )


# ---------------------------------------------------------------------------
# 5. Invalid severity returns error
# ---------------------------------------------------------------------------

class InvalidSeverityFieldTests(unittest.TestCase):
    def test_invalid_severity_value(self) -> None:
        for bad in ("urgent", "", "EXTREME", "warn"):
            with self.subTest(bad=bad):
                card = _valid_card(severity=bad)
                errors = validate_warning_card(card)
                self.assertTrue(
                    any(e.startswith("invalid value: severity expected one of")
                        for e in errors),
                    msg=f"unexpected errors: {errors}",
                )


# ---------------------------------------------------------------------------
# 6. Missing required field returns error
# ---------------------------------------------------------------------------

class MissingRequiredFieldTests(unittest.TestCase):
    def test_each_missing_field_returns_error(self) -> None:
        for field in WARNING_CARD_REQUIRED_FIELDS:
            with self.subTest(field=field):
                card = _valid_card()
                card.pop(field)
                errors = validate_warning_card(card)
                self.assertIn(f"missing field: {field}", errors)


# ---------------------------------------------------------------------------
# 7. title / message / source_layer must be non-empty string
# ---------------------------------------------------------------------------

class StringFieldNonEmptyTests(unittest.TestCase):
    def test_each_string_field_rejects_empty(self) -> None:
        for field in ("title", "message", "source_layer"):
            for bad in ("", None, 1, [], {}):
                with self.subTest(field=field, bad=bad):
                    card = _valid_card(**{field: bad})
                    errors = validate_warning_card(card)
                    self.assertTrue(
                        any(
                            e.startswith(
                                f"invalid value: {field} expected non-empty string"
                            )
                            for e in errors
                        ),
                        msg=f"unexpected errors: {errors}",
                    )


# ---------------------------------------------------------------------------
# 8. evidence must be dict / list / None
# ---------------------------------------------------------------------------

class EvidenceTypeTests(unittest.TestCase):
    def test_evidence_accepts_dict_list_none(self) -> None:
        for value in ({"k": "v"}, [1, 2, 3], None):
            with self.subTest(value=value):
                card = _valid_card(evidence=value)
                errors = validate_warning_card(card)
                self.assertEqual(errors, [], msg=f"unexpected errors: {errors}")

    def test_evidence_rejects_other_types(self) -> None:
        for bad in (1, "evidence", 1.5, True):
            with self.subTest(bad=bad):
                card = _valid_card(evidence=bad)
                errors = validate_warning_card(card)
                self.assertTrue(
                    any(e.startswith("invalid type: evidence expected") for e in errors),
                    msg=f"unexpected errors: {errors}",
                )


# ---------------------------------------------------------------------------
# 9. metadata must be dict / None
# ---------------------------------------------------------------------------

class MetadataTypeTests(unittest.TestCase):
    def test_metadata_accepts_dict_or_none(self) -> None:
        for value in ({"origin": "x"}, None):
            with self.subTest(value=value):
                card = _valid_card(metadata=value)
                errors = validate_warning_card(card)
                self.assertEqual(errors, [], msg=f"unexpected errors: {errors}")

    def test_metadata_rejects_other_types(self) -> None:
        for bad in (1, "metadata", [], 1.5, True):
            with self.subTest(bad=bad):
                card = _valid_card(metadata=bad)
                errors = validate_warning_card(card)
                self.assertTrue(
                    any(e.startswith("invalid type: metadata expected") for e in errors),
                    msg=f"unexpected errors: {errors}",
                )


# ---------------------------------------------------------------------------
# 10. blocking must be bool
# ---------------------------------------------------------------------------

class BlockingTypeTests(unittest.TestCase):
    def test_blocking_accepts_bool(self) -> None:
        for value in (True, False):
            with self.subTest(value=value):
                card = _valid_card(blocking=value)
                errors = validate_warning_card(card)
                self.assertEqual(errors, [], msg=f"unexpected errors: {errors}")

    def test_blocking_rejects_non_bool(self) -> None:
        for bad in (None, 0, 1, "true", "false", []):
            with self.subTest(bad=bad):
                card = _valid_card(blocking=bad)
                errors = validate_warning_card(card)
                self.assertTrue(
                    any(e.startswith("invalid type: blocking expected bool")
                        for e in errors),
                    msg=f"unexpected errors: {errors}",
                )


# ---------------------------------------------------------------------------
# 11. build_warning_card deep-copies evidence / metadata
# ---------------------------------------------------------------------------

class DeepCopyOnBuildTests(unittest.TestCase):
    def test_evidence_is_deep_copied(self) -> None:
        evidence = {"nested": {"k": "v"}}
        card = build_warning_card(
            warning_type="contradiction",
            severity="medium",
            title="t",
            message="m",
            source_layer="final_report",
            evidence=evidence,
        )
        card["evidence"]["nested"]["k"] = "MUTATED"
        self.assertEqual(evidence, {"nested": {"k": "v"}})

    def test_metadata_is_deep_copied(self) -> None:
        metadata = {"nested": {"k": "v"}}
        card = build_warning_card(
            warning_type="contradiction",
            severity="medium",
            title="t",
            message="m",
            source_layer="final_report",
            metadata=metadata,
        )
        card["metadata"]["nested"]["k"] = "MUTATED"
        self.assertEqual(metadata, {"nested": {"k": "v"}})

    def test_evidence_list_is_deep_copied(self) -> None:
        evidence = [{"k": "v"}]
        card = build_warning_card(
            warning_type="contradiction",
            severity="medium",
            title="t",
            message="m",
            source_layer="final_report",
            evidence=evidence,
        )
        card["evidence"][0]["k"] = "MUTATED"
        self.assertEqual(evidence, [{"k": "v"}])


# ---------------------------------------------------------------------------
# 12. validate_warning_card does not mutate input
# ---------------------------------------------------------------------------

class NonMutationTests(unittest.TestCase):
    def test_valid_card_unchanged(self) -> None:
        card = _valid_card()
        snapshot = copy.deepcopy(card)
        validate_warning_card(card)
        self.assertEqual(card, snapshot)

    def test_invalid_card_unchanged(self) -> None:
        card = _valid_card()
        card.pop("type")
        snapshot = copy.deepcopy(card)
        errors = validate_warning_card(card)
        self.assertNotEqual(errors, [])
        self.assertEqual(card, snapshot)

    def test_validate_warning_cards_does_not_mutate_list(self) -> None:
        cards = [_valid_card(), _valid_card(type="tail_risk")]
        snapshot = copy.deepcopy(cards)
        validate_warning_cards(cards)
        self.assertEqual(cards, snapshot)


# ---------------------------------------------------------------------------
# 13. Forbidden trading fields rejected
# ---------------------------------------------------------------------------

class ForbiddenTradingFieldTests(unittest.TestCase):
    def test_each_trading_field_rejected_at_top_level(self) -> None:
        for forbidden in (
            "buy",
            "sell",
            "hold",
            "trading_action",
            "order",
            "position_action",
            "execution",
            "broker_order",
            "live_trade",
            "active_rule_promotion",
            "promote_rule",
        ):
            with self.subTest(forbidden=forbidden):
                card = _valid_card()
                card[forbidden] = "anything"
                errors = validate_warning_card(card)
                self.assertIn(
                    f"forbidden field: {forbidden} at top-level",
                    errors,
                )


# ---------------------------------------------------------------------------
# 14. Forbidden hard / forced / required fields rejected
# ---------------------------------------------------------------------------

class ForbiddenHardForcedRequiredFieldTests(unittest.TestCase):
    def test_hard_forced_required_rejected_at_top_level(self) -> None:
        for forbidden in ("hard", "forced", "required"):
            with self.subTest(forbidden=forbidden):
                card = _valid_card()
                card[forbidden] = True
                errors = validate_warning_card(card)
                self.assertIn(
                    f"forbidden field: {forbidden} at top-level",
                    errors,
                )


# ---------------------------------------------------------------------------
# 15 + 16. recommended_action containing forbidden tokens rejected
# ---------------------------------------------------------------------------

class RecommendedActionTokenGuardTests(unittest.TestCase):
    def test_buy_sell_hold_in_recommended_action_rejected(self) -> None:
        for ra, token in (
            ("buy now", "buy"),
            ("strong buy signal", "buy"),
            ("sell off", "sell"),
            ("must hold", "hold"),
            ("hold position", "hold"),
        ):
            with self.subTest(ra=ra, token=token):
                card = _valid_card(recommended_action=ra)
                errors = validate_warning_card(card)
                self.assertIn(
                    f"forbidden token in recommended_action: {token}",
                    errors,
                )

    def test_hard_forced_required_in_recommended_action_rejected(self) -> None:
        for ra, token in (
            ("hard cutoff", "hard"),
            ("forced exit", "forced"),
            ("required action", "required"),
            ("forced_review_required", "forced"),
            ("forced_review_required", "required"),
        ):
            with self.subTest(ra=ra, token=token):
                card = _valid_card(recommended_action=ra)
                errors = validate_warning_card(card)
                self.assertIn(
                    f"forbidden token in recommended_action: {token}",
                    errors,
                )

    def test_descriptive_recommended_action_passes(self) -> None:
        for ra in (
            "display_warning_only",
            "review_before_trusting",
            "show_in_inspect_tab",
            "annotate_decision_only",
        ):
            with self.subTest(ra=ra):
                card = _valid_card(recommended_action=ra)
                errors = validate_warning_card(card)
                self.assertEqual(
                    errors, [], msg=f"unexpected errors for {ra!r}: {errors}"
                )

    def test_token_guard_does_not_flag_substring_buyer(self) -> None:
        card = _valid_card(recommended_action="buyer beware messaging only")
        errors = validate_warning_card(card)
        self.assertEqual(errors, [], msg=f"unexpected errors: {errors}")

    def test_recommended_action_empty_string_rejected(self) -> None:
        card = _valid_card(recommended_action="")
        errors = validate_warning_card(card)
        self.assertTrue(
            any(e.startswith("invalid value: recommended_action expected") for e in errors),
            msg=f"unexpected errors: {errors}",
        )

    def test_recommended_action_non_string_non_none_rejected(self) -> None:
        for bad in (1, [], {}, 1.5):
            with self.subTest(bad=bad):
                card = _valid_card(recommended_action=bad)
                errors = validate_warning_card(card)
                self.assertTrue(
                    any(e.startswith("invalid value: recommended_action expected") for e in errors),
                    msg=f"unexpected errors: {errors}",
                )


# ---------------------------------------------------------------------------
# 17 ~ 22. Per-type valid example cards
# ---------------------------------------------------------------------------

class PerTypeValidExampleTests(unittest.TestCase):
    def test_contradiction_card_valid(self) -> None:
        card = build_warning_card(
            warning_type="contradiction",
            severity="medium",
            title="big_up_contradiction",
            message="primary 偏多 vs exclusion 否定 偏多",
            source_layer="final_report",
            evidence={"primary_direction": "偏多",
                      "exclusion_excluded_direction": "偏多"},
            recommended_action="display_warning_only",
            blocking=False,
            metadata={"origin": "big_up_contradiction_card"},
        )
        self.assertEqual(validate_warning_card(card), [])

    def test_tail_risk_card_valid(self) -> None:
        card = build_warning_card(
            warning_type="tail_risk",
            severity="high",
            title="big_down_tail",
            message="尾部风险偏高",
            source_layer="final_report",
            evidence={"tail_signal_count": 3},
            recommended_action="display_warning_only",
            metadata={"origin": "big_down_tail_warning"},
        )
        self.assertEqual(validate_warning_card(card), [])

    def test_briefing_caution_card_valid(self) -> None:
        card = build_warning_card(
            warning_type="briefing_caution",
            severity="medium",
            title="briefing_caution_high",
            message="历史准确率较低，建议视为更低信心档（仅警告）",
            source_layer="review",
            recommended_action="display_warning_only",
            metadata={
                "original_confidence": "high",
                "recommended_confidence": "medium",
                "overall_accuracy": 0.42,
            },
        )
        self.assertEqual(validate_warning_card(card), [])

    def test_calibration_card_valid(self) -> None:
        card = build_warning_card(
            warning_type="calibration",
            severity="low",
            title="calibration_not_ready",
            message="calibration_context.ready=False，可信度评估降级为 unknown",
            source_layer="confidence",
            evidence=["calibration_context.ready=False"],
            recommended_action="review_before_trusting",
        )
        self.assertEqual(validate_warning_card(card), [])

    def test_data_quality_card_valid(self) -> None:
        card = build_warning_card(
            warning_type="data_quality",
            severity="high",
            title="missing_market_data",
            message="data_fetcher 返回 None；市场数据缺失",
            source_layer="data",
            evidence={"missing_dates": ["2026-04-30"]},
            recommended_action="display_warning_only",
            blocking=True,
        )
        self.assertEqual(validate_warning_card(card), [])

    def test_system_boundary_card_valid(self) -> None:
        card = build_warning_card(
            warning_type="system_boundary",
            severity="critical",
            title="orchestrator_skeleton_only",
            message="architecture_orchestrator 仍为 skeleton，未接 active path",
            source_layer="architecture_orchestrator",
            recommended_action="display_warning_only",
        )
        self.assertEqual(validate_warning_card(card), [])

    def test_unknown_card_valid(self) -> None:
        card = build_warning_card(
            warning_type="unknown",
            severity="unknown",
            title="unclassified_warning",
            message="未分类的提醒",
            source_layer="final_report",
        )
        self.assertEqual(validate_warning_card(card), [])


# ---------------------------------------------------------------------------
# validate_warning_cards per-card error prefix
# ---------------------------------------------------------------------------

class ValidateWarningCardsPerCardErrorTests(unittest.TestCase):
    def test_per_card_errors_carry_index_prefix(self) -> None:
        cards = [
            _valid_card(),
            _valid_card(type="not_a_real_type"),
        ]
        errors = validate_warning_cards(cards)
        self.assertTrue(
            any(e.startswith("cards[1]: invalid value: type expected one of")
                for e in errors),
            msg=f"unexpected errors: {errors}",
        )

    def test_non_dict_item_in_list_returns_index_prefixed_error(self) -> None:
        cards = [_valid_card(), "not a dict"]
        errors = validate_warning_cards(cards)
        self.assertTrue(
            any(e.startswith("cards[1]: invalid type: card expected dict")
                for e in errors),
            msg=f"unexpected errors: {errors}",
        )


# ---------------------------------------------------------------------------
# 23 + 24. Module import boundary
# ---------------------------------------------------------------------------

class ImportBoundaryTests(unittest.TestCase):
    """``services.warning_cards`` must remain a pure shape helper with
    zero coupling to any business / orchestrator / UI / DB module."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = _read("services/warning_cards.py")

    def test_no_business_module_imports(self) -> None:
        forbidden = (
            "from services.final_decision",
            "import services.final_decision",
            "from services.confidence_evaluator",
            "import services.confidence_evaluator",
            "from services.review_orchestrator",
            "import services.review_orchestrator",
            "from services.main_projection_layer",
            "import services.main_projection_layer",
            "from services.exclusion_layer",
            "import services.exclusion_layer",
            "from services.consistency_layer",
            "import services.consistency_layer",
            "from services.peer_alignment",
            "import services.peer_alignment",
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
            "from services.predict_legacy_adapter",
            "import services.predict_legacy_adapter",
            "from services.predict_legacy_v2_bridge",
            "import services.predict_legacy_v2_bridge",
            "from services.predict_summary",
            "import services.predict_summary",
            "from services.ai_summary",
            "import services.ai_summary",
            "from services.standard_projection_payload",
            "import services.standard_projection_payload",
            "from services.feature_payload_contract",
            "import services.feature_payload_contract",
            "from services.projection_result_contract",
            "import services.projection_result_contract",
            "from services.exclusion_result_contract",
            "import services.exclusion_result_contract",
            "from services.confidence_result_contract",
            "import services.confidence_result_contract",
            "from services.final_report_result_contract",
            "import services.final_report_result_contract",
            "from services.architecture_orchestrator",
            "import services.architecture_orchestrator",
            "from predict",
            "import predict",
            "from app",
            "import app",
            "from ui",
            "import ui",
        )
        for f in forbidden:
            self.assertNotIn(
                f,
                self.source,
                msg=f"services.warning_cards must not contain `{f}`",
            )

    def test_no_io_db_or_external_lib_imports(self) -> None:
        for f in (
            "import sqlite3",
            "from sqlite3",
            "import yfinance",
            "from yfinance",
            "import pandas",
            "from pandas",
            "import streamlit",
            "from streamlit",
            "openai",
            "OpenAI",
            "anthropic",
            "Anthropic",
            "open(",
            "Path(",
            "requests.",
            "urllib",
            "http.client",
        ):
            self.assertNotIn(
                f,
                self.source,
                msg=f"services.warning_cards must not contain `{f}`",
            )


# ---------------------------------------------------------------------------
# 25. No run / execute / orchestrate / main entry
# ---------------------------------------------------------------------------

class NoExecutionEntryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = _read("services/warning_cards.py")

    def test_no_run_execute_orchestrate_main_def(self) -> None:
        for f in (
            "def run(",
            "def run_",
            "def execute(",
            "def execute_",
            "def orchestrate(",
            "def orchestrate_",
            "def main(",
        ):
            self.assertNotIn(
                f,
                self.source,
                msg=f"services.warning_cards must not contain `{f}`",
            )


# ---------------------------------------------------------------------------
# 26. No trading-output return statements
# ---------------------------------------------------------------------------

class NoTradingOutputReturnTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = _read("services/warning_cards.py")

    def test_no_trading_return_statements(self) -> None:
        for f in (
            'return "buy"',
            'return "sell"',
            'return "hold"',
            'return "trading_action"',
            'return "order"',
            'return "execution"',
            'return "broker_order"',
            'return "live_trade"',
        ):
            self.assertNotIn(
                f,
                self.source,
                msg=f"services.warning_cards must not contain `{f}`",
            )


# ---------------------------------------------------------------------------
# Sanity check on module reference
# ---------------------------------------------------------------------------

class ModuleReferenceTests(unittest.TestCase):
    def test_build_function_lives_in_module(self) -> None:
        self.assertEqual(
            build_warning_card.__module__, "services.warning_cards"
        )
        self.assertIs(wc_mod.build_warning_card, build_warning_card)

    def test_validate_function_lives_in_module(self) -> None:
        self.assertEqual(
            validate_warning_card.__module__, "services.warning_cards"
        )
        self.assertIs(wc_mod.validate_warning_card, validate_warning_card)

    def test_validate_warning_cards_lives_in_module(self) -> None:
        self.assertEqual(
            validate_warning_cards.__module__, "services.warning_cards"
        )
        self.assertIs(wc_mod.validate_warning_cards, validate_warning_cards)


if __name__ == "__main__":
    unittest.main()
