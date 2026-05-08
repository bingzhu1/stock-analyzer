"""Contract enforcement tests for Step 12D (RISK-7) cutoff_guard helper.

These tests pin the shared cutoff guard behaviour:

1. Records dated on or before ``target_date`` are ALLOWED.
2. Records dated after ``target_date`` are SKIPPED with reason
   ``record_after_target_date``.
3. Records without any audit-date field are SKIPPED with reason
   ``missing_audit_date``.
4. Records whose date string is unparseable are SKIPPED with reason
   ``unparseable_date``.
5. The helper never falls back to "use all records" when filtering empties
   the list — the caller sees ``allowed_records == []`` instead.
6. The audit summary lists ``skipped_reasons`` (deduped) and a
   ``by_reason`` histogram.
7. The helper does not mutate the input records.
8. Field-priority order: ``available_as_of`` > ``reviewed_at`` >
   ``created_at`` > ``prediction_date`` > ``analysis_date`` >
   ``prediction_for_date``; ``prediction_for_date`` alone is NOT a
   sufficient audit date (11D §6.3).

Design contracts: 06 / 07A / 07B / 07C / 11D / 11H.
"""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class CutoffGuardSchemaTests(unittest.TestCase):
    def test_returns_expected_keys(self) -> None:
        from services.cutoff_guard import filter_records_by_cutoff

        result = filter_records_by_cutoff(
            [{"created_at": "2026-04-20"}],
            target_date="2026-04-21",
        )
        self.assertIn("allowed_records", result)
        self.assertIn("skipped_records", result)
        self.assertIn("cutoff_guard", result)
        guard = result["cutoff_guard"]
        for key in (
            "target_date",
            "mode",
            "allowed_count",
            "skipped_count",
            "skipped_reasons",
            "by_reason",
        ):
            self.assertIn(key, guard, msg=f"cutoff_guard missing key: {key}")
        self.assertEqual(guard["target_date"], "2026-04-21")
        self.assertEqual(guard["mode"], "strict")
        self.assertIsInstance(guard["skipped_reasons"], list)
        self.assertIsInstance(guard["by_reason"], dict)


class CutoffGuardAllowTests(unittest.TestCase):
    def test_cutoff_guard_allows_records_on_or_before_target_date(self) -> None:
        from services.cutoff_guard import filter_records_by_cutoff

        records = [
            {"created_at": "2026-04-20", "id": "a"},
            {"created_at": "2026-04-21", "id": "b"},
        ]
        result = filter_records_by_cutoff(records, target_date="2026-04-21")
        self.assertEqual(len(result["allowed_records"]), 2)
        self.assertEqual(result["cutoff_guard"]["allowed_count"], 2)
        self.assertEqual(result["cutoff_guard"]["skipped_count"], 0)
        self.assertEqual(result["cutoff_guard"]["skipped_reasons"], [])

    def test_priority_uses_available_as_of_first(self) -> None:
        from services.cutoff_guard import filter_records_by_cutoff

        # available_as_of takes precedence over created_at.
        record = {
            "available_as_of": "2026-04-20",
            "created_at": "2026-04-25",  # later, but should be ignored
            "id": "x",
        }
        result = filter_records_by_cutoff([record], target_date="2026-04-21")
        self.assertEqual(len(result["allowed_records"]), 1)
        self.assertEqual(result["cutoff_guard"]["allowed_count"], 1)


class CutoffGuardSkipTests(unittest.TestCase):
    def test_cutoff_guard_skips_records_after_target_date(self) -> None:
        from services.cutoff_guard import filter_records_by_cutoff

        records = [
            {"created_at": "2026-04-22", "id": "future"},
            {"created_at": "2026-04-19", "id": "past"},
        ]
        result = filter_records_by_cutoff(records, target_date="2026-04-21")
        self.assertEqual(len(result["allowed_records"]), 1)
        self.assertEqual(result["allowed_records"][0]["id"], "past")
        self.assertEqual(result["cutoff_guard"]["skipped_count"], 1)
        self.assertIn(
            "record_after_target_date",
            result["cutoff_guard"]["skipped_reasons"],
        )

    def test_cutoff_guard_skips_records_without_audit_date(self) -> None:
        from services.cutoff_guard import filter_records_by_cutoff

        # No audit-date field at all.
        records = [
            {"id": "no_date"},
            {"prediction_for_date": "2026-04-19", "id": "only_for_date"},
        ]
        result = filter_records_by_cutoff(records, target_date="2026-04-21")
        self.assertEqual(result["allowed_records"], [])
        self.assertEqual(result["cutoff_guard"]["allowed_count"], 0)
        self.assertEqual(result["cutoff_guard"]["skipped_count"], 2)
        self.assertIn(
            "missing_audit_date",
            result["cutoff_guard"]["skipped_reasons"],
        )

    def test_cutoff_guard_skips_unparseable_dates(self) -> None:
        from services.cutoff_guard import filter_records_by_cutoff

        records = [
            {"created_at": "not-a-date", "id": "garbage"},
            {"created_at": "20260420", "id": "no_dashes"},
        ]
        result = filter_records_by_cutoff(records, target_date="2026-04-21")
        self.assertEqual(result["allowed_records"], [])
        self.assertEqual(result["cutoff_guard"]["skipped_count"], 2)
        self.assertIn(
            "unparseable_date",
            result["cutoff_guard"]["skipped_reasons"],
        )

    def test_cutoff_guard_no_fallback_to_all_records(self) -> None:
        from services.cutoff_guard import filter_records_by_cutoff

        records = [
            {"created_at": "2027-01-01", "id": "future_a"},
            {"created_at": "2027-01-02", "id": "future_b"},
        ]
        result = filter_records_by_cutoff(records, target_date="2026-04-21")
        # All records should be skipped — must NOT fall back to allowing them.
        self.assertEqual(result["allowed_records"], [])
        self.assertEqual(len(result["skipped_records"]), 2)

    def test_target_date_none_strict_skips_all(self) -> None:
        from services.cutoff_guard import filter_records_by_cutoff

        # Strict mode + missing target_date → skip everything (no fallback).
        records = [{"created_at": "2026-04-19", "id": "x"}]
        result = filter_records_by_cutoff(records, target_date=None)
        self.assertEqual(result["allowed_records"], [])
        self.assertEqual(result["cutoff_guard"]["skipped_count"], 1)


class CutoffGuardAuditTests(unittest.TestCase):
    def test_skipped_reasons_are_deduped(self) -> None:
        from services.cutoff_guard import filter_records_by_cutoff

        records = [
            {"created_at": "2027-01-01", "id": "f1"},
            {"created_at": "2027-02-01", "id": "f2"},
            {"id": "no_date_a"},
            {"id": "no_date_b"},
            {"created_at": "garbage", "id": "bad"},
        ]
        result = filter_records_by_cutoff(records, target_date="2026-04-21")
        guard = result["cutoff_guard"]
        # The reasons list is deduped.
        self.assertEqual(
            sorted(guard["skipped_reasons"]),
            sorted(["record_after_target_date", "missing_audit_date", "unparseable_date"]),
        )
        # by_reason is a histogram.
        self.assertEqual(guard["by_reason"]["record_after_target_date"], 2)
        self.assertEqual(guard["by_reason"]["missing_audit_date"], 2)
        self.assertEqual(guard["by_reason"]["unparseable_date"], 1)

    def test_does_not_mutate_records(self) -> None:
        from services.cutoff_guard import filter_records_by_cutoff

        records = [
            {"created_at": "2026-04-20", "id": "x", "extra": {"nested": [1, 2]}},
            {"created_at": "2027-04-21", "id": "y"},
        ]
        snapshot = copy.deepcopy(records)
        filter_records_by_cutoff(records, target_date="2026-04-21")
        self.assertEqual(records, snapshot)

    def test_summary_target_date_field_records_input(self) -> None:
        from services.cutoff_guard import filter_records_by_cutoff

        result = filter_records_by_cutoff([], target_date="2026-04-21")
        self.assertEqual(result["cutoff_guard"]["target_date"], "2026-04-21")

    def test_empty_records_list(self) -> None:
        from services.cutoff_guard import filter_records_by_cutoff

        result = filter_records_by_cutoff([], target_date="2026-04-21")
        self.assertEqual(result["allowed_records"], [])
        self.assertEqual(result["skipped_records"], [])
        self.assertEqual(result["cutoff_guard"]["allowed_count"], 0)
        self.assertEqual(result["cutoff_guard"]["skipped_count"], 0)


class CutoffGuardReviewedAtPriorityTests(unittest.TestCase):
    def test_reviewed_at_used_when_no_available_as_of(self) -> None:
        from services.cutoff_guard import filter_records_by_cutoff

        record = {"reviewed_at": "2026-04-22T03:00:00", "id": "future_review"}
        result = filter_records_by_cutoff([record], target_date="2026-04-21")
        # reviewed_at falls one day after target_date → SKIP
        self.assertEqual(result["allowed_records"], [])
        self.assertIn(
            "record_after_target_date",
            result["cutoff_guard"]["skipped_reasons"],
        )

    def test_reviewed_at_within_target_allows(self) -> None:
        from services.cutoff_guard import filter_records_by_cutoff

        record = {"reviewed_at": "2026-04-21T23:59:59", "id": "ok_review"}
        result = filter_records_by_cutoff([record], target_date="2026-04-21")
        self.assertEqual(len(result["allowed_records"]), 1)


class CutoffGuardOnlyPredictionForDateTests(unittest.TestCase):
    def test_only_prediction_for_date_is_not_enough(self) -> None:
        """Per 11D §6.3 prediction_for_date alone is NOT sufficient as
        cutoff (it's the predict target, not the audit date)."""
        from services.cutoff_guard import filter_records_by_cutoff

        record = {"prediction_for_date": "2026-04-19", "id": "only_for"}
        result = filter_records_by_cutoff([record], target_date="2026-04-21")
        self.assertEqual(result["allowed_records"], [])
        self.assertIn(
            "missing_audit_date",
            result["cutoff_guard"]["skipped_reasons"],
        )


if __name__ == "__main__":
    unittest.main()
