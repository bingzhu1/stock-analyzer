from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import services.memory_store as ms


class MemoryStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._old_db_path = ms.DB_PATH
        ms.DB_PATH = Path(self._tmpdir.name) / "memory.db"

    def tearDown(self) -> None:
        ms.DB_PATH = self._old_db_path
        self._tmpdir.cleanup()

    def test_save_and_get_experience(self) -> None:
        saved = ms.save_experience(
            symbol="avgo",
            error_category="Wrong Direction",
            root_cause="The scan over-weighted momentum.",
            lesson="Require confirmation from close strength.",
            created_at="2026-04-12T10:00:00+00:00",
        )

        loaded = ms.get_experience(saved["id"])

        self.assertEqual(loaded, saved)
        self.assertEqual(saved["symbol"], "AVGO")
        self.assertEqual(saved["error_category"], "wrong_direction")

    def test_get_missing_experience_returns_none(self) -> None:
        self.assertIsNone(ms.get_experience("missing-id"))

    def test_list_experiences_orders_newest_first(self) -> None:
        older = ms.save_experience(
            symbol="AVGO",
            error_category="correct",
            root_cause="Older cause",
            lesson="Older lesson",
            created_at="2026-04-12T09:00:00+00:00",
        )
        newer = ms.save_experience(
            symbol="AVGO",
            error_category="wrong_direction",
            root_cause="Newer cause",
            lesson="Newer lesson",
            created_at="2026-04-12T11:00:00+00:00",
        )

        rows = ms.list_experiences()

        self.assertEqual([row["id"] for row in rows], [newer["id"], older["id"]])

    def test_list_experiences_filters_by_symbol_and_category(self) -> None:
        keep = ms.save_experience(
            symbol="AVGO",
            error_category="right-direction-wrong-magnitude",
            root_cause="Small move",
            lesson="Treat tiny moves separately.",
            created_at="2026-04-12T10:00:00+00:00",
        )
        ms.save_experience(
            symbol="MSFT",
            error_category="right_direction_wrong_magnitude",
            root_cause="Other symbol",
            lesson="Ignore for AVGO.",
            created_at="2026-04-12T11:00:00+00:00",
        )

        rows = ms.list_experiences(
            symbol="avgo",
            error_category="Right Direction Wrong Magnitude",
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], keep["id"])

    def test_unknown_category_falls_back_to_insufficient_data(self) -> None:
        saved = ms.save_experience(
            symbol="AVGO",
            error_category="mystery",
            root_cause="Unclear cause",
            lesson="Review manually.",
        )

        self.assertEqual(saved["error_category"], "insufficient_data")

    def test_required_fields_are_validated(self) -> None:
        with self.assertRaises(ValueError):
            ms.save_experience(
                symbol=" ",
                error_category="correct",
                root_cause="Cause",
                lesson="Lesson",
            )
        with self.assertRaises(ValueError):
            ms.save_experience(
                symbol="AVGO",
                error_category="correct",
                root_cause=" ",
                lesson="Lesson",
            )
        with self.assertRaises(ValueError):
            ms.save_experience(
                symbol="AVGO",
                error_category="correct",
                root_cause="Cause",
                lesson=" ",
            )

    def test_list_limit_is_applied(self) -> None:
        for index in range(3):
            ms.save_experience(
                symbol="AVGO",
                error_category="correct",
                root_cause=f"Cause {index}",
                lesson=f"Lesson {index}",
                created_at=f"2026-04-12T1{index}:00:00+00:00",
            )

        rows = ms.list_experiences(limit=2)

        self.assertEqual(len(rows), 2)


if __name__ == "__main__":
    unittest.main()
