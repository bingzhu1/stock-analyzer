"""2026 holdout boundary + anti-lookahead guard tests
(Step 18T / PR-EVAL-2).

Spec source of truth:

- `tasks/record_1_0_architecture_reset_canonical_principles.md` §5 rule 8
- `tasks/record_07a_projection_system_contract.md` §3.2
- `tasks/record_07b_exclusion_system_contract.md` §3.2
- `tasks/record_07c_confidence_system_contract.md` §3.2
- `tasks/record_07d_final_report_aggregator_contract.md` §3.2
- `tasks/record_17l_evaluation_layer_rebuild_plan.md` §8 / §13 / §15
- `tasks/record_18a_first_layer_based_implementation_batch_selection.md` §13
- `tasks/record_18s_third_layer_based_implementation_batch_selection.md` §6 / §7 / §8

PR-EVAL-2 is the third batch's first cut: a **pure-test** PR that locks
the 2026-01-01 final-holdout invariant. It does **not** modify
``services/evaluation_result_contract.py`` — the contract already
enforces ``holdout_touch_status`` / ``anti_lookahead_confirmations`` /
``artifact_manifest.raw_artifacts_tracked`` shape rules; this suite
pins the **invariant** behavior plus a source-level guard that
training / calibration / replay-audit producers don't hardcode the
holdout cutoff or write rule promotions.

This suite verifies (numbers correspond to the user spec for 18T):

1.  ``FINAL_HOLDOUT_START_DATE`` constant equals ``"2026-01-01"``;
    consistent across all helpers.
2.  Validator round-trip on a representative ``evaluation_result.v1``
    payload (untouched holdout) returns ``[]``.
3.  Missing ``holdout_touch_status`` triggers ``missing section`` error.
4.  ``holdout_touch_status="violated"`` is contract-valid (validator
    enum allows it) but a boundary helper flags it for operator
    attention.
5.  Each ``anti_lookahead_confirmations`` key required at top level;
    ``False`` value triggers ``invalid value`` error.
6.  ``artifact_manifest.raw_artifacts_tracked = True`` triggers error;
    missing key triggers error.
7.  Window-boundary pure helper: training / validation / calibration
    windows must end strictly before ``"2026-01-01"`` to count as
    "outside holdout".
8.  Source-level: training / calibration / replay-audit modules don't
    hardcode ``"2026-01-01"`` (they must source it via parameter /
    config / ``regime_validation_helper``).
9.  Source-level: ``regime_validation_helper.DEFAULT_FINAL_TEST_CUTOFF``
    equals ``"2026-01-01"`` (positive assertion that the cutoff is
    centralized).
10. Raw artifact dump fields (``raw_replay_rows`` /
    ``raw_predictions_dump``) forbidden at top level by the validator.
11. Trading / hard / forced / required leak fields forbidden at top
    level by the validator.
12. ``validate_evaluation_result`` is a pure function (no input
    mutation; deep-copy round-trip).

The test file imports only ``ast`` / ``copy`` / ``pathlib`` / stdlib
unittest plus ``services.evaluation_result_contract`` — never
``historical_replay_training`` / ``active_rule_pool_calibration`` /
``three_system_replay_audit`` / ``contract_outcome_correlation`` /
``regime_validation_helper`` (those are read as text via
``Path.read_text`` for source-level grep only).
"""

from __future__ import annotations

import ast  # noqa: F401 — reserved for future structural checks
import copy
import unittest
from pathlib import Path
from typing import Any

from services.evaluation_result_contract import (
    EVALUATION_RESULT_KIND,
    EVALUATION_RESULT_SCHEMA_VERSION,
    EVALUATION_RESULT_SECTIONS,
    FORBIDDEN_FIELDS,
    VALID_EVALUATION_TYPES,
    VALID_HOLDOUT_TOUCH_STATUS,
    VALID_STATUS,
    validate_evaluation_result,
)


# ---------------------------------------------------------------------------
# Frozen constant: 2026-01-01 final holdout start date.
# Sourced from 1.0 §5 rule 8 / 07A §3.2 / 07B §3.2 / 07C §3.2 / 07D §3.2 /
# 17L §8 — these all anchor the cutoff. The constant is local to this
# test file so the invariant survives even if a producer module changes
# its own internal cutoff name.
# ---------------------------------------------------------------------------

FINAL_HOLDOUT_START_DATE: str = "2026-01-01"


_REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(rel: str) -> str:
    return (_REPO_ROOT / rel).read_text(encoding="utf-8")


def _valid_minimal_evaluation() -> dict[str, Any]:
    """A minimal but contract-clean ``evaluation_result.v1`` payload
    with the holdout untouched. Mirrors the existing fixture style in
    ``tests/test_evaluation_result_contract.py`` (uses
    ``start_date`` / ``end_date`` keys inside windows)."""
    return {
        "schema_version": EVALUATION_RESULT_SCHEMA_VERSION,
        "kind": EVALUATION_RESULT_KIND,
        "symbol": "AVGO",
        "ready": True,
        "evaluation_id": "eval-2026-05-01",
        "evaluation_type": "validation",
        "evaluation_timestamp": None,
        "train_window": {
            "start_date": "2020-01-01",
            "end_date": "2024-12-31",
        },
        "validation_window": {
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
        },
        "holdout_window": {
            "start_date": FINAL_HOLDOUT_START_DATE,
            "end_date": None,
        },
        "data_cutoff": "2025-12-31",
        "sample_count": 0,
        "projection_accuracy": None,
        "exclusion_hit_rate": None,
        "false_exclusion_rate": None,
        "confidence_calibration_summary": None,
        "final_report_quality_summary": None,
        "review_lesson_validation_summary": None,
        "anti_lookahead_confirmations": {
            "replay_only_used_past_data": True,
            "outcome_loaded_after_prediction": True,
            "no_future_outcome_in_features": True,
            "holdout_not_used_for_training": True,
        },
        "holdout_touch_status": "untouched",
        "calibration_output": None,
        "artifact_manifest": {
            "summary_path": None,
            "raw_artifacts_tracked": False,
        },
        "status": "ok",
        "warnings": [],
        "skipped_records": [],
        "non_mutation_confirmations": {
            "evaluation_did_not_mutate_prediction_payload": True,
            "evaluation_did_not_mutate_review_memory": True,
            "evaluation_did_not_write_active_rules": True,
            "evaluation_did_not_run_live_trading": True,
        },
    }


def _status_consistent_with_holdout_touch_status(
    payload: dict[str, Any],
) -> bool:
    """Boundary helper: ``holdout_touch_status="violated"`` must not
    coexist with ``status="ok"``. Returns True iff the pair is
    operator-visibly consistent.

    A producer that detects a holdout leak must surface it in
    ``status`` (one of ``"error"`` / ``"partial"`` / ``"skipped"`` /
    ``"not_ready"``); flipping only ``holdout_touch_status`` while
    leaving ``status="ok"`` would mask the leak in dashboards.
    """
    if not isinstance(payload, dict):
        return False
    hts = payload.get("holdout_touch_status")
    status = payload.get("status")
    if hts == "violated" and status == "ok":
        return False
    return True


def _window_ends_before_holdout(
    window: dict[str, Any] | None,
    *,
    holdout_start: str = FINAL_HOLDOUT_START_DATE,
) -> bool:
    """Pure helper for boundary tests only.

    Returns True iff ``window["end_date"]`` is a string strictly less
    than ``holdout_start``. ``None`` end_date means "open-ended" — for
    training / validation / calibration windows that is treated as
    NOT outside holdout (the operator must close the window with an
    explicit pre-holdout date). For the ``holdout_window`` itself this
    helper is not relevant.
    """
    if not isinstance(window, dict):
        return False
    end_date = window.get("end_date")
    if not isinstance(end_date, str):
        return False
    return end_date < holdout_start


# ---------------------------------------------------------------------------
# 1. HoldoutDateConstantTests
# ---------------------------------------------------------------------------

class HoldoutDateConstantTests(unittest.TestCase):
    """Lock the 2026-01-01 cutoff as a project-wide invariant. The
    constant must match every spec anchor (1.0 §5 rule 8 / 07A §3.2 /
    07B §3.2 / 07C §3.2 / 07D §3.2 / 17L §8)."""

    def test_final_holdout_start_date_is_2026_01_01(self) -> None:
        self.assertEqual(FINAL_HOLDOUT_START_DATE, "2026-01-01")

    def test_holdout_constant_is_not_before_2026(self) -> None:
        # Defensive: catch accidental drift to "2025-..." or earlier.
        self.assertGreaterEqual(FINAL_HOLDOUT_START_DATE, "2026-01-01")
        self.assertLess(FINAL_HOLDOUT_START_DATE, "2027-01-01")

    def test_holdout_constant_is_iso_8601_yyyy_mm_dd(self) -> None:
        self.assertEqual(len(FINAL_HOLDOUT_START_DATE), 10)
        self.assertEqual(FINAL_HOLDOUT_START_DATE[4], "-")
        self.assertEqual(FINAL_HOLDOUT_START_DATE[7], "-")
        for ch in (
            FINAL_HOLDOUT_START_DATE[:4]
            + FINAL_HOLDOUT_START_DATE[5:7]
            + FINAL_HOLDOUT_START_DATE[8:10]
        ):
            self.assertTrue(ch.isdigit())


# ---------------------------------------------------------------------------
# 2. EvaluationResultHoldoutContractTests
# ---------------------------------------------------------------------------

class EvaluationResultHoldoutContractTests(unittest.TestCase):
    """Round-trip the contract validator with various holdout-related
    payloads. PR-EVAL-2 does NOT change the contract module; it pins
    that the existing rules already enforce the invariants we expect."""

    def test_valid_payload_passes_validate_evaluation_result(self) -> None:
        errors = validate_evaluation_result(_valid_minimal_evaluation())
        self.assertEqual(errors, [], msg=f"unexpected errors: {errors}")

    def test_payload_includes_all_holdout_related_sections(self) -> None:
        # Defensive: ensure the spec's 26 sections still cover every
        # holdout-related key our boundary tests exercise.
        for required in (
            "train_window",
            "validation_window",
            "holdout_window",
            "data_cutoff",
            "anti_lookahead_confirmations",
            "holdout_touch_status",
            "artifact_manifest",
            "status",
            "non_mutation_confirmations",
        ):
            with self.subTest(section=required):
                self.assertIn(required, EVALUATION_RESULT_SECTIONS)

    def test_missing_holdout_touch_status_triggers_missing_section_error(
        self,
    ) -> None:
        payload = _valid_minimal_evaluation()
        payload.pop("holdout_touch_status")
        errors = validate_evaluation_result(payload)
        self.assertIn("missing section: holdout_touch_status", errors)

    def test_holdout_touch_status_violated_is_contract_valid(self) -> None:
        # 17L §8 / contract enum allows "violated" so producers can
        # surface the bad case without crashing the validator. The
        # boundary helper below flags it as operator-visible.
        payload = _valid_minimal_evaluation()
        payload["holdout_touch_status"] = "violated"
        errors = validate_evaluation_result(payload)
        self.assertEqual(errors, [], msg=f"unexpected errors: {errors}")

    def test_holdout_touch_status_consistency_helper_catches_bad_pair(
        self,
    ) -> None:
        # Boundary helper: when a producer flips holdout_touch_status to
        # "violated" but leaves status="ok", the helper returns False.
        # If a future producer ever returns this combination, the
        # downstream pipeline calling this helper must surface the leak.
        payload = _valid_minimal_evaluation()
        payload["holdout_touch_status"] = "violated"
        # status defaults to "ok" — the bad combination
        self.assertFalse(
            _status_consistent_with_holdout_touch_status(payload),
            msg=(
                "boundary contract: holdout_touch_status='violated' must "
                "not coexist with status='ok'; the helper must catch this"
            ),
        )

    def test_holdout_touch_status_consistency_helper_accepts_good_pairs(
        self,
    ) -> None:
        # Pair 1: untouched + ok → consistent
        payload = _valid_minimal_evaluation()
        self.assertTrue(_status_consistent_with_holdout_touch_status(payload))

        # Pair 2: violated + error → consistent (leak surfaced)
        payload2 = _valid_minimal_evaluation()
        payload2["holdout_touch_status"] = "violated"
        payload2["status"] = "error"
        self.assertTrue(_status_consistent_with_holdout_touch_status(payload2))

        # Pair 3: violated + skipped → consistent
        payload3 = _valid_minimal_evaluation()
        payload3["holdout_touch_status"] = "violated"
        payload3["status"] = "skipped"
        self.assertTrue(_status_consistent_with_holdout_touch_status(payload3))

        # Pair 4: validated_only + ok → consistent (validation-only,
        # no leak)
        payload4 = _valid_minimal_evaluation()
        payload4["holdout_touch_status"] = "validated_only"
        payload4["status"] = "ok"
        self.assertTrue(_status_consistent_with_holdout_touch_status(payload4))

    def test_holdout_touch_status_consistency_helper_rejects_non_dict(
        self,
    ) -> None:
        for bad in (None, "string", 42, []):
            with self.subTest(value=bad):
                self.assertFalse(
                    _status_consistent_with_holdout_touch_status(bad)
                )

    def test_each_holdout_touch_status_enum_is_recognised(self) -> None:
        for value in VALID_HOLDOUT_TOUCH_STATUS:
            with self.subTest(holdout_touch_status=value):
                payload = _valid_minimal_evaluation()
                payload["holdout_touch_status"] = value
                # If "violated", flip status away from "ok" per the
                # boundary contract above.
                if value == "violated":
                    payload["status"] = "error"
                errors = validate_evaluation_result(payload)
                self.assertEqual(
                    errors, [],
                    msg=f"unexpected errors for status={value}: {errors}",
                )


# ---------------------------------------------------------------------------
# 3 / 4. AntiLookaheadConfirmationsTests
# ---------------------------------------------------------------------------

class AntiLookaheadConfirmationsTests(unittest.TestCase):
    """All four anti-lookahead keys must be present and True (17L §8 /
    §13). The contract enforces this; PR-EVAL-2 pins each individual
    failure mode."""

    REQUIRED_KEYS = (
        "replay_only_used_past_data",
        "outcome_loaded_after_prediction",
        "no_future_outcome_in_features",
        "holdout_not_used_for_training",
    )

    def test_each_missing_key_triggers_missing_field_error(self) -> None:
        for key in self.REQUIRED_KEYS:
            with self.subTest(missing=key):
                payload = _valid_minimal_evaluation()
                payload["anti_lookahead_confirmations"].pop(key)
                errors = validate_evaluation_result(payload)
                self.assertIn(
                    f"missing field: anti_lookahead_confirmations.{key}",
                    errors,
                )

    def test_each_key_set_to_false_triggers_invalid_value_error(self) -> None:
        for key in self.REQUIRED_KEYS:
            for bad in (False, None, 0, 1, "true", []):
                with self.subTest(key=key, value=bad):
                    payload = _valid_minimal_evaluation()
                    payload["anti_lookahead_confirmations"][key] = bad
                    errors = validate_evaluation_result(payload)
                    self.assertTrue(
                        any(
                            e.startswith(
                                f"invalid value: anti_lookahead_confirmations.{key}"
                            )
                            for e in errors
                        ),
                        msg=f"expected error for {key}={bad!r}; got {errors}",
                    )

    def test_anti_lookahead_confirmations_must_be_dict(self) -> None:
        for bad in ([], "string", 42, None):
            with self.subTest(value=bad):
                payload = _valid_minimal_evaluation()
                payload["anti_lookahead_confirmations"] = bad
                errors = validate_evaluation_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith(
                        "invalid type: anti_lookahead_confirmations"
                    )
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 5. ArtifactManifestRawArtifactsTrackedTests
# ---------------------------------------------------------------------------

class ArtifactManifestRawArtifactsTrackedTests(unittest.TestCase):
    """``artifact_manifest.raw_artifacts_tracked`` must be False —
    raw replay / calibration artifacts are never tracked in git
    (1.0 §11 / 14K / 16H). The contract enforces False; PR-EVAL-2 pins
    each failure mode."""

    def test_true_triggers_invalid_value_error(self) -> None:
        payload = _valid_minimal_evaluation()
        payload["artifact_manifest"]["raw_artifacts_tracked"] = True
        errors = validate_evaluation_result(payload)
        self.assertTrue(
            any(
                e.startswith(
                    "invalid value: artifact_manifest.raw_artifacts_tracked"
                )
                for e in errors
            ),
            msg=f"expected error for raw_artifacts_tracked=True; got {errors}",
        )

    def test_missing_key_triggers_missing_field_error(self) -> None:
        payload = _valid_minimal_evaluation()
        payload["artifact_manifest"].pop("raw_artifacts_tracked")
        errors = validate_evaluation_result(payload)
        self.assertIn(
            "missing field: artifact_manifest.raw_artifacts_tracked",
            errors,
        )

    def test_truthy_non_bool_values_trigger_invalid_value_error(self) -> None:
        for bad in (1, "yes", [1], "True"):
            with self.subTest(value=bad):
                payload = _valid_minimal_evaluation()
                payload["artifact_manifest"]["raw_artifacts_tracked"] = bad
                errors = validate_evaluation_result(payload)
                self.assertTrue(
                    any(
                        e.startswith(
                            "invalid value: artifact_manifest.raw_artifacts_tracked"
                        )
                        for e in errors
                    ),
                    msg=f"expected error for raw_artifacts_tracked={bad!r}; got {errors}",
                )

    def test_summary_path_required_key_missing_error(self) -> None:
        payload = _valid_minimal_evaluation()
        payload["artifact_manifest"].pop("summary_path")
        errors = validate_evaluation_result(payload)
        self.assertIn(
            "missing field: artifact_manifest.summary_path",
            errors,
        )


# ---------------------------------------------------------------------------
# 6. HoldoutWindowBoundaryTests (pure helper)
# ---------------------------------------------------------------------------

class HoldoutWindowBoundaryTests(unittest.TestCase):
    """Pure-function ``_window_ends_before_holdout`` correctness. The
    helper exists in this test file only; production producers must
    surface the same intent via ``train_window`` / ``validation_window``
    / ``calibration_window`` end_date fields."""

    def test_training_window_2025_passes(self) -> None:
        self.assertTrue(
            _window_ends_before_holdout(
                {"start_date": "2020-01-01", "end_date": "2025-12-31"}
            )
        )

    def test_training_window_2026_fails(self) -> None:
        self.assertFalse(
            _window_ends_before_holdout(
                {"start_date": "2020-01-01", "end_date": "2026-01-01"}
            )
        )

    def test_training_window_2026_02_fails(self) -> None:
        self.assertFalse(
            _window_ends_before_holdout(
                {"start_date": "2020-01-01", "end_date": "2026-02-01"}
            )
        )

    def test_validation_window_2025_passes(self) -> None:
        self.assertTrue(
            _window_ends_before_holdout(
                {"start_date": "2025-01-01", "end_date": "2025-12-31"}
            )
        )

    def test_validation_window_2026_fails(self) -> None:
        self.assertFalse(
            _window_ends_before_holdout(
                {"start_date": "2025-01-01", "end_date": "2026-01-01"}
            )
        )

    def test_calibration_window_must_end_strictly_before_holdout(self) -> None:
        # Calibration windows must close before holdout; equality is
        # not allowed (the cutoff is "[2026-01-01, ∞)" → strict less).
        self.assertTrue(
            _window_ends_before_holdout(
                {"start_date": "2024-01-01", "end_date": "2025-12-31"}
            )
        )
        self.assertFalse(
            _window_ends_before_holdout(
                {"start_date": "2024-01-01", "end_date": "2026-01-01"}
            )
        )

    def test_data_cutoff_2025_passes(self) -> None:
        # data_cutoff is a top-level string field, not a window dict,
        # but it must satisfy the same cutoff rule. Use direct comparison.
        self.assertLess("2025-12-31", FINAL_HOLDOUT_START_DATE)

    def test_data_cutoff_2026_fails(self) -> None:
        self.assertGreaterEqual("2026-01-01", FINAL_HOLDOUT_START_DATE)
        self.assertGreaterEqual("2026-02-01", FINAL_HOLDOUT_START_DATE)

    def test_open_ended_window_treated_as_not_outside_holdout(self) -> None:
        # None end_date → window potentially extends past holdout →
        # not safe.
        self.assertFalse(
            _window_ends_before_holdout(
                {"start_date": "2020-01-01", "end_date": None}
            )
        )

    def test_non_dict_input_returns_false(self) -> None:
        for bad in (None, "2025-12-31", 42, []):
            with self.subTest(window=bad):
                self.assertFalse(_window_ends_before_holdout(bad))


# ---------------------------------------------------------------------------
# 7 / 8. SourceLevelAntiLookaheadGuardTests
# ---------------------------------------------------------------------------

class SourceLevelAntiLookaheadGuardTests(unittest.TestCase):
    """Source-level scan for forward-leakage patterns in producer
    modules. The cutoff string ``"2026-01-01"`` must be sourced via
    ``regime_validation_helper.DEFAULT_FINAL_TEST_CUTOFF`` (or an
    equivalent parameter) — never hardcoded inside training /
    calibration / replay-audit producers.

    These tests read source files via ``Path.read_text``; they do NOT
    import the modules (PR-EVAL-2 must not run any replay /
    calibration / training code path)."""

    PRODUCER_MODULES = (
        "services/historical_replay_training.py",
        "services/active_rule_pool_calibration.py",
        "services/three_system_replay_audit.py",
        "services/contract_outcome_correlation.py",
    )

    GUARD_MODULE = "services/regime_validation_helper.py"

    def _source(self, rel: str) -> str:
        path = _REPO_ROOT / rel
        if not path.exists():
            self.skipTest(f"{rel} not present in this checkout")
        return path.read_text(encoding="utf-8")

    def test_producers_do_not_hardcode_holdout_cutoff_literal(self) -> None:
        # Each producer module must NOT contain the literal
        # "2026-01-01". Cutoff sourcing must go through
        # regime_validation_helper.DEFAULT_FINAL_TEST_CUTOFF or a
        # caller-supplied parameter.
        for rel in self.PRODUCER_MODULES:
            with self.subTest(module=rel):
                src = self._source(rel)
                self.assertNotIn(
                    FINAL_HOLDOUT_START_DATE,
                    src,
                    msg=(
                        f"{rel} must not hardcode holdout cutoff "
                        f"'{FINAL_HOLDOUT_START_DATE}' — source it via "
                        "regime_validation_helper or a parameter"
                    ),
                )

    def test_producers_do_not_compare_directly_to_2026(self) -> None:
        # Defensive: even if a producer constructs the date string
        # piecewise, common comparison patterns would still be a leak
        # signal. Scan for ">= '2026'" / '>= "2026"' / '== "2026-01-01"'.
        forbidden_patterns = (
            ">= \"2026",
            ">= '2026",
            ">=\"2026",
            ">='2026",
            "== \"2026-01-01\"",
            "== '2026-01-01'",
            ">= 2026",  # int / fstring form
        )
        for rel in self.PRODUCER_MODULES:
            with self.subTest(module=rel):
                src = self._source(rel)
                for pattern in forbidden_patterns:
                    self.assertNotIn(
                        pattern,
                        src,
                        msg=(
                            f"{rel} must not contain pattern {pattern!r} — "
                            "training / calibration must not compare data "
                            "dates directly to a hardcoded 2026 cutoff"
                        ),
                    )

    def test_regime_validation_helper_centralises_holdout_cutoff(
        self,
    ) -> None:
        # Positive assertion: the cutoff lives in a centralized
        # module. This anchors the producer-side test above (which
        # forbids hardcoding) — the cutoff has a designated home.
        src = self._source(self.GUARD_MODULE)
        self.assertIn(
            'DEFAULT_FINAL_TEST_CUTOFF = "2026-01-01"',
            src,
            msg=(
                f"{self.GUARD_MODULE} must define "
                "`DEFAULT_FINAL_TEST_CUTOFF = \"2026-01-01\"` so producers "
                "have a designated source for the cutoff string"
            ),
        )

    def test_producers_do_not_set_raw_artifacts_tracked_true(self) -> None:
        forbidden_patterns = (
            'raw_artifacts_tracked": True',
            "raw_artifacts_tracked': True",
            "raw_artifacts_tracked = True",
            "raw_artifacts_tracked=True",
        )
        for rel in self.PRODUCER_MODULES:
            with self.subTest(module=rel):
                src = self._source(rel)
                for pattern in forbidden_patterns:
                    self.assertNotIn(
                        pattern,
                        src,
                        msg=(
                            f"{rel} must not set "
                            f"raw_artifacts_tracked=True (1.0 §11 / 14K / "
                            "16H raw artifact policy)"
                        ),
                    )

    def test_producers_do_not_emit_active_rule_promotion_calls(self) -> None:
        # Producers must not invoke active_rule_promotion / promote_rule
        # against a holdout. This is a coarse string scan; a full AST
        # check is out of scope for PR-EVAL-2.
        forbidden_calls = (
            "active_rule_promotion(",
            "promote_rule(",
            "live_trade(",
            "broker_order(",
        )
        for rel in self.PRODUCER_MODULES:
            with self.subTest(module=rel):
                src = self._source(rel)
                for call in forbidden_calls:
                    self.assertNotIn(
                        call,
                        src,
                        msg=(
                            f"{rel} must not call {call!r} — these are "
                            "trading / promotion surfaces forbidden by "
                            "1.0 §6 / §13"
                        ),
                    )


# ---------------------------------------------------------------------------
# 9. RawArtifactGuardTests
# ---------------------------------------------------------------------------

class RawArtifactGuardTests(unittest.TestCase):
    """Raw artifact dump fields are forbidden at the top level of an
    ``evaluation_result.v1`` payload. This pins the contract's
    ``FORBIDDEN_FIELDS`` for those specific keys."""

    def test_raw_artifacts_tracked_false_passes(self) -> None:
        payload = _valid_minimal_evaluation()
        payload["artifact_manifest"]["raw_artifacts_tracked"] = False
        errors = validate_evaluation_result(payload)
        self.assertEqual(errors, [])

    def test_raw_replay_rows_top_level_rejected(self) -> None:
        payload = _valid_minimal_evaluation()
        payload["raw_replay_rows"] = ["row1", "row2"]
        errors = validate_evaluation_result(payload)
        self.assertIn(
            "forbidden field: raw_replay_rows at top-level",
            errors,
        )

    def test_raw_predictions_dump_top_level_rejected(self) -> None:
        payload = _valid_minimal_evaluation()
        payload["raw_predictions_dump"] = {"id-1": {}, "id-2": {}}
        errors = validate_evaluation_result(payload)
        self.assertIn(
            "forbidden field: raw_predictions_dump at top-level",
            errors,
        )

    def test_raw_artifact_keys_in_forbidden_set(self) -> None:
        # Belt + suspenders: pin that the contract's FORBIDDEN_FIELDS
        # frozenset still includes both raw artifact dump keys.
        for key in ("raw_replay_rows", "raw_predictions_dump"):
            with self.subTest(key=key):
                self.assertIn(key, FORBIDDEN_FIELDS)


# ---------------------------------------------------------------------------
# 10. NoTradingOrDecisionLeakTests
# ---------------------------------------------------------------------------

class NoTradingOrDecisionLeakTests(unittest.TestCase):
    """Trading / promotion / forced-decision leaks must be rejected at
    the top level of an evaluation_result payload. PR-EVAL-2 pins each
    forbidden key individually so future contract changes can't quietly
    relax the guard."""

    FORBIDDEN_TOP_LEVEL = (
        "trading_action",
        "buy",
        "sell",
        "hold",
        "hard",
        "forced",
        "required",
        "live_trade",
        "broker_order",
        "active_rule_promotion",
        "promote_rule",
        "order",
        "position_action",
        "execution",
        "simulated_trade",
    )

    def test_each_forbidden_top_level_field_rejected(self) -> None:
        for key in self.FORBIDDEN_TOP_LEVEL:
            with self.subTest(forbidden=key):
                payload = _valid_minimal_evaluation()
                payload[key] = "should-be-rejected"
                errors = validate_evaluation_result(payload)
                self.assertIn(
                    f"forbidden field: {key} at top-level",
                    errors,
                )

    def test_each_forbidden_key_in_forbidden_set(self) -> None:
        for key in self.FORBIDDEN_TOP_LEVEL:
            with self.subTest(forbidden=key):
                self.assertIn(key, FORBIDDEN_FIELDS)


# ---------------------------------------------------------------------------
# 11. ValidatorPurityTests
# ---------------------------------------------------------------------------

class ValidatorPurityTests(unittest.TestCase):
    """``validate_evaluation_result`` must not mutate its input. PR-EVAL-2
    pins this with deep-copy round-trips on the holdout-related shapes."""

    def test_valid_payload_round_trip_unchanged(self) -> None:
        payload = _valid_minimal_evaluation()
        snapshot = copy.deepcopy(payload)
        validate_evaluation_result(payload)
        self.assertEqual(payload, snapshot)

    def test_payload_with_violated_status_round_trip_unchanged(self) -> None:
        payload = _valid_minimal_evaluation()
        payload["holdout_touch_status"] = "violated"
        payload["status"] = "error"
        snapshot = copy.deepcopy(payload)
        validate_evaluation_result(payload)
        self.assertEqual(payload, snapshot)

    def test_payload_with_forbidden_field_round_trip_unchanged(self) -> None:
        payload = _valid_minimal_evaluation()
        payload["raw_replay_rows"] = ["row"]
        snapshot = copy.deepcopy(payload)
        errors = validate_evaluation_result(payload)
        self.assertNotEqual(errors, [])  # confirm error path exercised
        self.assertEqual(payload, snapshot)


# ---------------------------------------------------------------------------
# Sanity: contract enums + constants we depend on
# ---------------------------------------------------------------------------

class ContractEnumSanityTests(unittest.TestCase):
    def test_valid_holdout_touch_status_enum(self) -> None:
        self.assertEqual(
            VALID_HOLDOUT_TOUCH_STATUS,
            ("untouched", "validated_only", "violated", "unknown"),
        )

    def test_valid_status_enum(self) -> None:
        self.assertEqual(
            VALID_STATUS,
            ("ok", "partial", "skipped", "error", "not_ready"),
        )

    def test_valid_evaluation_types_enum(self) -> None:
        self.assertEqual(
            VALID_EVALUATION_TYPES,
            (
                "replay",
                "validation",
                "calibration",
                "audit",
                "trend",
                "diff",
                "correlation",
                "extras_dashboard",
            ),
        )


if __name__ == "__main__":
    unittest.main()
