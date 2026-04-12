# Reviewer Handoff - Task 006: fix_task001_blockers

## Status
PASS

## Date
2026-04-12

## What was found

## 1. findings

### Finding 1 - severity: low
The duplicate-save test validates the intended latest-row behavior, but it does not force an identical `created_at` tie.

Evidence:
- `get_prediction_by_date()` now orders by `created_at DESC, rowid DESC`.
- `test_get_prediction_by_date_returns_latest_save_with_tiebreaker()` saves twice and expects the second id.
- In normal fast execution those two rows usually share the same second-level timestamp, but the test does not explicitly pin or assert equal `created_at` values.

### Finding 2 - severity: low
Foreign-key protection is covered through connection PRAGMA and public orphan prevention, but there is no direct raw FK violation test.

Evidence:
- `_get_conn()` enables `PRAGMA foreign_keys = ON`.
- `save_outcome()` and `save_review()` validate the parent prediction before insert and reject missing IDs.
- Tests assert PRAGMA is enabled and public helpers leave no orphan rows, but they do not directly execute an invalid child insert through `_get_conn()` and assert `sqlite3.IntegrityError`.

No high or medium findings found.

## 2. why it matters

Finding 1 matters because the original blocker was specifically same-second latest-row ambiguity. The implementation is deterministic, but an explicit equal-timestamp test would make the regression guard less dependent on test timing.

Finding 2 matters because Task 006 asks for SQLite FK/orphan-row risk to be meaningfully protected. The current public API guard is good, and PRAGMA is enabled, but a direct FK enforcement assertion would make the DB-level guarantee obvious to future reviewers.

## 3. suggested fix

- Optional: strengthen the duplicate-save test by forcing equal `created_at` rows, either by patching `datetime.now()` or by inserting controlled rows directly, then asserting the higher `rowid` wins.
- Optional: add a direct test that inserts an `outcome_log` or `review_log` row with a missing `prediction_id` through `_get_conn()` and expects `sqlite3.IntegrityError`.

These are test-hardening suggestions, not blockers for Task 006.

## 4. validation gaps

Validation run during review:
- `D:\Git\bin\bash.exe scripts/check.sh` - PASS.
- `D:\anaconda\python.exe -m unittest discover -s tests -p "test_prediction_store.py" -v` - PASS, 20/20, after escalation because sandboxed temp DB creation failed.
- `D:\anaconda\python.exe -m unittest tests.test_prediction_store tests.test_outcome_capture tests.test_review_agent -v` - PASS, 60/60, after escalation because sandboxed temp DB creation failed.

Sandbox note:
- Running the same Anaconda unittest commands without escalation failed with `sqlite3.OperationalError: unable to open database file` during `tempfile.TemporaryDirectory()` DB setup, plus Windows temp cleanup permission errors. This appears environment-related rather than a code regression; the same suites pass outside the sandbox.

Review conclusions:
- Latest-row selection is deterministic in code via `created_at DESC, rowid DESC`.
- SQLite orphan-row risk is addressed by connection-level FK enforcement and parent validation in `save_outcome()` / `save_review()`.
- `save_review()` status advancement now happens in the same transaction/connection as the review insert.
- Status machine remains forward-only and idempotent via `_advance_prediction_status()`.
- Scope is acceptable: reviewed implementation changes are confined to Task 006 persistence/test/status surfaces; no business UI/app logic was changed for this task.

## Required actions for next agent
- Tester should run the Task 006 validation suite and decide whether to add the optional test-hardening cases in a follow-up.

## Status update
- `tasks/STATUS.md` updated to: `in-test`
- `tasks/006_fix_task001_blockers.md` updated to: `in-test`
