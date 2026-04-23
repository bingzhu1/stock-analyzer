"""Tests for services/state_label.py — unified five-state label function."""

import math
import unittest

from services.state_label import label_state, label_state_from_ratio, ratio_to_pct


class BoundaryTests(unittest.TestCase):
    """Exact boundary values — the most important cases."""

    # ── upper boundaries ──────────────────────────────────────────────────────

    def test_exactly_plus_2_is_大涨(self) -> None:
        self.assertEqual(label_state(2.0), "大涨")

    def test_above_plus_2_is_大涨(self) -> None:
        self.assertEqual(label_state(2.01), "大涨")
        self.assertEqual(label_state(5.0), "大涨")
        self.assertEqual(label_state(10.0), "大涨")

    def test_just_below_plus_2_is_小涨(self) -> None:
        self.assertEqual(label_state(1.99), "小涨")

    def test_exactly_plus_0_5_is_小涨(self) -> None:
        self.assertEqual(label_state(0.5), "小涨")

    def test_just_below_plus_0_5_is_震荡(self) -> None:
        self.assertEqual(label_state(0.49), "震荡")

    # ── lower boundaries ──────────────────────────────────────────────────────

    def test_exactly_minus_0_5_is_小跌(self) -> None:
        self.assertEqual(label_state(-0.5), "小跌")

    def test_just_above_minus_0_5_is_震荡(self) -> None:
        self.assertEqual(label_state(-0.49), "震荡")

    def test_exactly_minus_2_is_大跌(self) -> None:
        self.assertEqual(label_state(-2.0), "大跌")

    def test_just_above_minus_2_is_小跌(self) -> None:
        self.assertEqual(label_state(-1.99), "小跌")

    def test_below_minus_2_is_大跌(self) -> None:
        self.assertEqual(label_state(-2.01), "大跌")
        self.assertEqual(label_state(-5.0), "大跌")
        self.assertEqual(label_state(-10.0), "大跌")


class TypicalValueTests(unittest.TestCase):
    """Representative mid-range values for each state."""

    def test_zero_is_震荡(self) -> None:
        self.assertEqual(label_state(0.0), "震荡")

    def test_small_positive_is_震荡(self) -> None:
        self.assertEqual(label_state(0.1), "震荡")

    def test_small_negative_is_震荡(self) -> None:
        self.assertEqual(label_state(-0.1), "震荡")

    def test_mid_small_up_is_小涨(self) -> None:
        self.assertEqual(label_state(1.0), "小涨")

    def test_mid_small_down_is_小跌(self) -> None:
        self.assertEqual(label_state(-1.0), "小跌")

    def test_large_positive_is_大涨(self) -> None:
        self.assertEqual(label_state(3.5), "大涨")

    def test_large_negative_is_大跌(self) -> None:
        self.assertEqual(label_state(-3.5), "大跌")


class InputTypeTests(unittest.TestCase):
    """Numeric coercion and invalid-input handling."""

    def test_integer_input_accepted(self) -> None:
        self.assertEqual(label_state(3), "大涨")
        self.assertEqual(label_state(-3), "大跌")
        self.assertEqual(label_state(0), "震荡")

    def test_none_raises_type_error(self) -> None:
        with self.assertRaises(TypeError):
            label_state(None)  # type: ignore[arg-type]

    def test_string_raises_type_error(self) -> None:
        with self.assertRaises(TypeError):
            label_state("2.0")  # type: ignore[arg-type]

    def test_nan_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            label_state(float("nan"))

    def test_inf_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            label_state(float("inf"))
        with self.assertRaises(ValueError):
            label_state(float("-inf"))


class RatioConversionReminderTests(unittest.TestCase):
    """
    outcome_capture stores actual_close_change as a ratio (0.02 = +2%).
    Callers must convert: label_state(ratio * 100).
    These tests confirm the function behaves correctly after conversion.
    """

    def test_ratio_002_converts_to_大涨(self) -> None:
        self.assertEqual(label_state(0.02 * 100), "大涨")

    def test_ratio_0005_converts_to_小涨(self) -> None:
        self.assertEqual(label_state(0.005 * 100), "小涨")

    def test_ratio_0003_converts_to_震荡(self) -> None:
        self.assertEqual(label_state(0.003 * 100), "震荡")

    def test_ratio_minus_0005_converts_to_小跌(self) -> None:
        self.assertEqual(label_state(-0.005 * 100), "小跌")

    def test_ratio_minus_002_converts_to_大跌(self) -> None:
        self.assertEqual(label_state(-0.02 * 100), "大跌")

    def test_ratio_to_pct_is_explicit_and_deterministic(self) -> None:
        self.assertEqual(ratio_to_pct(0.02), 2.0)
        self.assertEqual(ratio_to_pct(-0.005), -0.5)

    def test_label_state_from_ratio_uses_same_boundaries(self) -> None:
        self.assertEqual(label_state_from_ratio(0.02), "大涨")
        self.assertEqual(label_state_from_ratio(0.005), "小涨")
        self.assertEqual(label_state_from_ratio(-0.005), "小跌")
        self.assertEqual(label_state_from_ratio(-0.02), "大跌")


class ExhaustivePartitionTest(unittest.TestCase):
    """Every value maps to exactly one state; no gaps or overlaps."""

    def test_all_states_reachable(self) -> None:
        from services.state_label import ALL_STATES
        results = {
            label_state(3.0),
            label_state(1.0),
            label_state(0.0),
            label_state(-1.0),
            label_state(-3.0),
        }
        self.assertEqual(results, set(ALL_STATES))

    def test_boundary_sweep_produces_no_unexpected_value(self) -> None:
        from services.state_label import ALL_STATES
        valid = set(ALL_STATES)
        test_points = [
            -5.0, -2.01, -2.0, -1.99, -0.51, -0.5, -0.49,
            -0.01, 0.0, 0.01, 0.49, 0.5, 0.51, 1.99, 2.0, 2.01, 5.0,
        ]
        for pt in test_points:
            result = label_state(pt)
            self.assertIn(result, valid, msg=f"label_state({pt}) = {result!r} not in ALL_STATES")


if __name__ == "__main__":
    unittest.main()
