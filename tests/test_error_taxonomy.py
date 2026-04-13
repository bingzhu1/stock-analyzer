from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.error_taxonomy import (
    CORRECT,
    INSUFFICIENT_DATA,
    RIGHT_DIRECTION_WRONG_MAGNITUDE,
    VALID_ERROR_CATEGORIES,
    WRONG_DIRECTION,
    classify_error_category,
    normalize_error_category,
)


class ErrorTaxonomyTests(unittest.TestCase):
    def test_valid_categories_are_stable(self) -> None:
        self.assertEqual(
            VALID_ERROR_CATEGORIES,
            {
                "correct",
                "wrong_direction",
                "right_direction_wrong_magnitude",
                "false_confidence",
                "insufficient_data",
            },
        )

    def test_normalize_accepts_known_category(self) -> None:
        self.assertEqual(normalize_error_category("wrong_direction"), WRONG_DIRECTION)

    def test_normalize_handles_case_spaces_and_hyphens(self) -> None:
        self.assertEqual(normalize_error_category("Wrong Direction"), WRONG_DIRECTION)
        self.assertEqual(
            normalize_error_category("right-direction-wrong-magnitude"),
            RIGHT_DIRECTION_WRONG_MAGNITUDE,
        )

    def test_normalize_unknown_category_falls_back_to_insufficient_data(self) -> None:
        self.assertEqual(normalize_error_category("not_a_category"), INSUFFICIENT_DATA)
        self.assertEqual(normalize_error_category(None), INSUFFICIENT_DATA)

    def test_classify_correct_direction_with_significant_move(self) -> None:
        self.assertEqual(classify_error_category(1, 0.012), CORRECT)

    def test_classify_correct_direction_with_tiny_move(self) -> None:
        self.assertEqual(classify_error_category(1, 0.005), RIGHT_DIRECTION_WRONG_MAGNITUDE)

    def test_classify_wrong_direction(self) -> None:
        self.assertEqual(classify_error_category(0, -0.03), WRONG_DIRECTION)

    def test_classify_missing_direction(self) -> None:
        self.assertEqual(classify_error_category(None, 0.0), INSUFFICIENT_DATA)


if __name__ == "__main__":
    unittest.main()
