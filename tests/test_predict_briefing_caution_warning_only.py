"""Tests for ``predict._apply_briefing_caution`` warning-only behavior
(Step 18R / PR-REVIEW-2).

Spec source of truth:

- `tasks/record_1_0_architecture_reset_canonical_principles.md` §13 hard rule
- `tasks/record_06_three_system_independence_principle.md` §6 / §7
- `tasks/record_17k_review_learning_layer_rebuild_plan.md` §17
- `tasks/record_18a_first_layer_based_implementation_batch_selection.md` §7
- `tasks/record_18j_second_layer_based_implementation_batch_selection.md` §6 / §10

PR-REVIEW-2 fixes the violation where ``_apply_briefing_caution``
directly rewrote ``result["final_confidence"]`` based on review-memory
input. The new behavior is **warning-only**: the function attaches
markers (``briefing_caution_applied`` / ``briefing_caution_reason`` /
``briefing_caution_original_confidence`` /
``briefing_caution_recommended_confidence``) but never mutates
``final_confidence`` / ``final_direction`` / ``final_prediction`` /
``final_bias`` / ``primary_direction`` / ``primary_projection`` /
``final_projection``.

This suite verifies (numbers correspond to the user spec):

1.  high caution + has_data + can lower → applied=True, original /
    recommended set, ``final_confidence`` unchanged
2.  high caution + has_data + already at lowest → applied=False,
    original/recommended set, ``final_confidence`` unchanged
3.  medium caution + has_data → applied=False, reason set,
    ``final_confidence`` unchanged
4.  no caution / no data → applied=False, reason None,
    ``final_confidence`` unchanged
5.  ``final_direction`` is never modified
6.  ``final_prediction`` / ``primary_direction`` / ``primary_projection``
    / ``final_bias`` / ``final_projection`` are never modified
7.  Result top level has no ``hard`` / ``forced`` / ``required`` /
    ``forced_downgrade`` / ``required_downgrade``
8.  Marker fields are present and complete on every code path
9.  Input ``result`` dict not mutated in place (caller-side reference
    stays intact)
10. Source-level: function body no longer assigns
    ``result["final_confidence"] =``
11. Source-level: function body no longer contains forced / required /
    hard wording
"""

from __future__ import annotations

import copy
import re
import unittest
from pathlib import Path
from typing import Any

from predict import _apply_briefing_caution


_REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(rel: str) -> str:
    return (_REPO_ROOT / rel).read_text(encoding="utf-8")


def _result(**overrides: Any) -> dict:
    base: dict = {
        "final_confidence": "high",
        "final_direction": "小涨",
        "final_prediction": "小涨收阳",
        "final_bias": "偏多",
        "primary_direction": "偏多",
        "primary_projection": "上涨",
        "final_projection": "上涨",
        "confidence": "high",
        "notes": [],
    }
    base.update(overrides)
    return base


def _briefing(
    *,
    caution_level: str = "none",
    has_data: bool = False,
    overall_accuracy: float = 0.0,
    record_count: int = 0,
) -> dict:
    return {
        "caution_level": caution_level,
        "has_data": has_data,
        "overall_accuracy": overall_accuracy,
        "record_count": record_count,
    }


# ---------------------------------------------------------------------------
# 1. high caution + has_data + can lower → applied=True, no mutation
# ---------------------------------------------------------------------------

class HighCautionCanLowerTests(unittest.TestCase):
    def test_high_caution_high_confidence_marks_applied_true(self) -> None:
        result_in = _result(final_confidence="high")
        out = _apply_briefing_caution(
            result_in, _briefing(caution_level="high", has_data=True)
        )
        self.assertIs(out["briefing_caution_applied"], True)

    def test_high_caution_high_confidence_preserves_final_confidence(self) -> None:
        result_in = _result(final_confidence="high")
        out = _apply_briefing_caution(
            result_in, _briefing(caution_level="high", has_data=True)
        )
        self.assertEqual(out["final_confidence"], "high")

    def test_high_caution_records_original_and_recommended(self) -> None:
        result_in = _result(final_confidence="high")
        out = _apply_briefing_caution(
            result_in,
            _briefing(
                caution_level="high",
                has_data=True,
                overall_accuracy=0.45,
                record_count=20,
            ),
        )
        self.assertEqual(
            out["briefing_caution_original_confidence"], "high"
        )
        self.assertEqual(
            out["briefing_caution_recommended_confidence"], "medium"
        )

    def test_high_caution_reason_is_non_empty(self) -> None:
        result_in = _result(final_confidence="high")
        out = _apply_briefing_caution(
            result_in,
            _briefing(
                caution_level="high",
                has_data=True,
                overall_accuracy=0.45,
                record_count=20,
            ),
        )
        reason = out["briefing_caution_reason"]
        self.assertIsInstance(reason, str)
        self.assertGreater(len(reason), 0)

    def test_high_caution_medium_confidence_recommends_low(self) -> None:
        result_in = _result(final_confidence="medium")
        out = _apply_briefing_caution(
            result_in, _briefing(caution_level="high", has_data=True)
        )
        self.assertEqual(out["final_confidence"], "medium")
        self.assertIs(out["briefing_caution_applied"], True)
        self.assertEqual(
            out["briefing_caution_recommended_confidence"], "low"
        )


# ---------------------------------------------------------------------------
# 2. high caution + has_data + already at lowest → applied=False, no mutation
# ---------------------------------------------------------------------------

class HighCautionAtLowestTests(unittest.TestCase):
    def test_high_caution_low_confidence_marks_applied_false(self) -> None:
        result_in = _result(final_confidence="low")
        out = _apply_briefing_caution(
            result_in, _briefing(caution_level="high", has_data=True)
        )
        self.assertIs(out["briefing_caution_applied"], False)

    def test_high_caution_low_confidence_preserves_final_confidence(self) -> None:
        result_in = _result(final_confidence="low")
        out = _apply_briefing_caution(
            result_in, _briefing(caution_level="high", has_data=True)
        )
        self.assertEqual(out["final_confidence"], "low")

    def test_high_caution_at_lowest_recommendation_is_none(self) -> None:
        result_in = _result(final_confidence="low")
        out = _apply_briefing_caution(
            result_in, _briefing(caution_level="high", has_data=True)
        )
        self.assertIsNone(out["briefing_caution_recommended_confidence"])

    def test_high_caution_at_lowest_reason_describes_floor(self) -> None:
        result_in = _result(final_confidence="low")
        out = _apply_briefing_caution(
            result_in, _briefing(caution_level="high", has_data=True)
        )
        self.assertIsInstance(out["briefing_caution_reason"], str)
        self.assertIn("最低档", out["briefing_caution_reason"])


# ---------------------------------------------------------------------------
# 3. medium caution + has_data → applied=False, reason set, no mutation
# ---------------------------------------------------------------------------

class MediumCautionTests(unittest.TestCase):
    def test_medium_caution_marks_applied_false(self) -> None:
        result_in = _result(final_confidence="high")
        out = _apply_briefing_caution(
            result_in,
            _briefing(
                caution_level="medium", has_data=True, overall_accuracy=0.6
            ),
        )
        self.assertIs(out["briefing_caution_applied"], False)

    def test_medium_caution_preserves_final_confidence(self) -> None:
        for original in ("high", "medium", "low"):
            with self.subTest(original=original):
                result_in = _result(final_confidence=original)
                out = _apply_briefing_caution(
                    result_in,
                    _briefing(caution_level="medium", has_data=True),
                )
                self.assertEqual(out["final_confidence"], original)

    def test_medium_caution_reason_describes_attention(self) -> None:
        result_in = _result(final_confidence="high")
        out = _apply_briefing_caution(
            result_in,
            _briefing(caution_level="medium", has_data=True, overall_accuracy=0.55),
        )
        self.assertIsInstance(out["briefing_caution_reason"], str)
        self.assertIn("中等", out["briefing_caution_reason"])


# ---------------------------------------------------------------------------
# 4. no caution / no data → applied=False, reason None, no mutation
# ---------------------------------------------------------------------------

class NoCautionTests(unittest.TestCase):
    def test_caution_none_no_data_marks_applied_false(self) -> None:
        result_in = _result(final_confidence="high")
        out = _apply_briefing_caution(result_in, _briefing())
        self.assertIs(out["briefing_caution_applied"], False)
        self.assertIsNone(out["briefing_caution_reason"])

    def test_caution_low_no_data_preserves_final_confidence(self) -> None:
        result_in = _result(final_confidence="high")
        out = _apply_briefing_caution(
            result_in, _briefing(caution_level="low", has_data=False)
        )
        self.assertEqual(out["final_confidence"], "high")

    def test_high_caution_without_data_does_not_mutate(self) -> None:
        # Even if caution_level is "high", missing has_data must not
        # trigger any change.
        result_in = _result(final_confidence="high")
        out = _apply_briefing_caution(
            result_in, _briefing(caution_level="high", has_data=False)
        )
        self.assertEqual(out["final_confidence"], "high")
        self.assertIs(out["briefing_caution_applied"], False)


# ---------------------------------------------------------------------------
# 5 + 6. Direction / prediction / bias / projection fields never modified
# ---------------------------------------------------------------------------

class ProtectedDirectionFieldsTests(unittest.TestCase):
    PROTECTED_FIELDS = (
        "final_direction",
        "final_prediction",
        "final_bias",
        "primary_direction",
        "primary_projection",
        "final_projection",
    )

    def _assert_protected_unchanged(self, briefing: dict) -> None:
        result_in = _result()
        snapshot = {k: result_in[k] for k in self.PROTECTED_FIELDS}
        out = _apply_briefing_caution(result_in, briefing)
        for field in self.PROTECTED_FIELDS:
            self.assertEqual(
                out[field], snapshot[field],
                msg=f"_apply_briefing_caution must not modify {field!r}",
            )

    def test_high_caution_does_not_modify_direction_fields(self) -> None:
        self._assert_protected_unchanged(
            _briefing(caution_level="high", has_data=True)
        )

    def test_medium_caution_does_not_modify_direction_fields(self) -> None:
        self._assert_protected_unchanged(
            _briefing(caution_level="medium", has_data=True)
        )

    def test_no_caution_does_not_modify_direction_fields(self) -> None:
        self._assert_protected_unchanged(_briefing())


# ---------------------------------------------------------------------------
# 7. No hard / forced / required fields at top level
# ---------------------------------------------------------------------------

class NoForcedHardRequiredFieldsTests(unittest.TestCase):
    def test_high_caution_does_not_emit_forced_hard_required(self) -> None:
        result_in = _result(final_confidence="high")
        out = _apply_briefing_caution(
            result_in, _briefing(caution_level="high", has_data=True)
        )
        for forbidden in (
            "hard",
            "forced",
            "required",
            "forced_downgrade",
            "required_downgrade",
            "hard_downgrade",
            "buy",
            "sell",
            "hold",
            "trading_action",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(
                    forbidden,
                    out,
                    msg=f"_apply_briefing_caution must not emit {forbidden!r}",
                )

    def test_medium_caution_does_not_emit_forced_hard_required(self) -> None:
        result_in = _result(final_confidence="high")
        out = _apply_briefing_caution(
            result_in, _briefing(caution_level="medium", has_data=True)
        )
        for forbidden in ("hard", "forced", "required", "buy", "sell", "hold"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, out)


# ---------------------------------------------------------------------------
# 8. Marker fields complete on every code path
# ---------------------------------------------------------------------------

class MarkerFieldsCompleteTests(unittest.TestCase):
    REQUIRED_MARKERS = (
        "briefing_caution_applied",
        "briefing_caution_reason",
        "briefing_caution_original_confidence",
        "briefing_caution_recommended_confidence",
    )

    def _assert_markers_present(self, briefing: dict, original: str) -> None:
        result_in = _result(final_confidence=original)
        out = _apply_briefing_caution(result_in, briefing)
        for key in self.REQUIRED_MARKERS:
            with self.subTest(briefing=briefing, original=original, marker=key):
                self.assertIn(
                    key, out,
                    msg=f"missing marker {key!r}",
                )
        # Original confidence should match the input's final_confidence.
        self.assertEqual(
            out["briefing_caution_original_confidence"], original
        )

    def test_high_can_lower_path_has_all_markers(self) -> None:
        self._assert_markers_present(
            _briefing(caution_level="high", has_data=True), "high"
        )

    def test_high_at_lowest_path_has_all_markers(self) -> None:
        self._assert_markers_present(
            _briefing(caution_level="high", has_data=True), "low"
        )

    def test_medium_path_has_all_markers(self) -> None:
        self._assert_markers_present(
            _briefing(caution_level="medium", has_data=True), "high"
        )

    def test_no_caution_path_has_all_markers(self) -> None:
        self._assert_markers_present(_briefing(), "medium")

    def test_unknown_confidence_path_has_all_markers(self) -> None:
        # Even when final_confidence is an off-canon string, markers
        # must still be present (defaults applied).
        self._assert_markers_present(
            _briefing(caution_level="high", has_data=True), "totally_unknown"
        )


# ---------------------------------------------------------------------------
# 9. Caller-side input dict reference stays intact
# ---------------------------------------------------------------------------

class CallerReferenceProtectionTests(unittest.TestCase):
    def test_caller_input_dict_unchanged_after_call(self) -> None:
        # The function returns a new dict (via dict(result)). Mutations
        # to the returned dict must not propagate back to the caller's
        # original reference.
        original = _result(final_confidence="high")
        snapshot = copy.deepcopy(original)
        out = _apply_briefing_caution(
            original, _briefing(caution_level="high", has_data=True)
        )
        # Modify the returned dict aggressively.
        out["briefing_caution_applied"] = "MUTATED"
        out["final_confidence"] = "MUTATED"
        out["new_top_level_key"] = "MUTATED"
        # The caller's original dict must remain unchanged.
        self.assertEqual(original, snapshot)

    def test_input_lists_not_mutated(self) -> None:
        original = _result()
        original["notes"] = ["original note"]
        snapshot_notes = list(original["notes"])
        _apply_briefing_caution(
            original, _briefing(caution_level="high", has_data=True)
        )
        self.assertEqual(original["notes"], snapshot_notes)


# ---------------------------------------------------------------------------
# 10 + 11. Source-level checks
# ---------------------------------------------------------------------------

class SourceLevelChecksTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        source = _read("predict.py")
        # Extract the body of _apply_briefing_caution. The function is
        # delimited by ``def _apply_briefing_caution(`` until the next
        # top-level ``def ``.
        start = source.index("def _apply_briefing_caution(")
        # Look for the next top-level ``def `` (no leading whitespace).
        end_match = re.search(r"\n(def |class )", source[start + 1 :])
        end = (start + 1 + end_match.start()) if end_match else len(source)
        cls.body = source[start:end]

    def test_body_does_not_assign_final_confidence(self) -> None:
        # The new warning-only contract forbids any assignment to
        # result["final_confidence"] inside the function body.
        for forbidden in (
            'result["final_confidence"] = ',
            "result['final_confidence'] = ",
            'result.update({"final_confidence":',
            "result.update({'final_confidence':",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(
                    forbidden,
                    self.body,
                    msg=(
                        f"_apply_briefing_caution body must not contain "
                        f"{forbidden!r}"
                    ),
                )

    def test_body_does_not_assign_other_protected_fields(self) -> None:
        for protected in (
            "final_direction",
            "final_prediction",
            "final_bias",
            "primary_direction",
            "primary_projection",
            "final_projection",
        ):
            for token in (
                f'result["{protected}"] = ',
                f"result['{protected}'] = ",
            ):
                with self.subTest(protected=protected, token=token):
                    self.assertNotIn(
                        token,
                        self.body,
                        msg=(
                            f"_apply_briefing_caution body must not assign "
                            f"{protected!r}"
                        ),
                    )

    def test_body_does_not_contain_forced_or_required_or_hard(self) -> None:
        # Word-boundary checks via simple substring guard. The function
        # docstring + reason strings are user-facing Chinese; English
        # tokens for forced semantics must not leak into the result keys
        # or any computed string.
        for forbidden in (
            'result["forced"',
            'result["required"',
            'result["hard"',
            'result["forced_downgrade"',
            'result["required_downgrade"',
            "forced_downgrade =",
            "required_downgrade =",
            "hard_downgrade =",
            "trading_action",
            'result["buy"',
            'result["sell"',
            'result["hold"',
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(
                    forbidden,
                    self.body,
                    msg=(
                        f"_apply_briefing_caution body must not contain "
                        f"{forbidden!r}"
                    ),
                )


# ---------------------------------------------------------------------------
# Sanity: returned dict is a fresh dict (not the input)
# ---------------------------------------------------------------------------

class FreshDictTests(unittest.TestCase):
    def test_returned_dict_is_not_input_dict(self) -> None:
        original = _result()
        out = _apply_briefing_caution(
            original, _briefing(caution_level="high", has_data=True)
        )
        self.assertIsNot(out, original)


if __name__ == "__main__":
    unittest.main()
