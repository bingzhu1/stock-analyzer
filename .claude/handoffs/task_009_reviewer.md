# Reviewer Handoff - Task 009: scenario_match_wiring

## Status
PASS

## Date
2026-04-12

## 1. Findings

### Finding 1 - [low] Canonical task filename is still inconsistent

The requested path `tasks/009_scenario_match_wiring.md` does not exist. The repository currently has `tasks/009_scenario_matching_wiring.md`, while the task title and `tasks/STATUS.md` use `scenario_match_wiring`.

### Finding 2 - [low] Review/history scenario rendering is not covered by permanent test assertions

The implementation wires `scenario_match` into the review prompt and History display, and the tester handoff records temporary direct assertions for both paths. However, those assertions are not committed into `tests/test_review_agent.py` or `tests/test_history_tab.py`, so future regressions in those display paths would rely on manual/temporary checks.

## 2. Why It Matters

### Finding 1

The project workflow expects agents to read `tasks/{NNN}_{name}.md`. A filename mismatch is survivable because the actual file is present and documented in the builder/tester handoffs, but it still adds friction and can confuse the next agent.

### Finding 2

Outcome persistence is covered well, but Task 009 also promises that scenario data remains usable in review/history. Permanent assertions would make that promise cheaper to preserve.

## 3. Suggested Fix

### Finding 1

Normalize the filename to `tasks/009_scenario_match_wiring.md`, or intentionally update canonical references to `scenario_matching_wiring`. Prefer matching the task title and `tasks/STATUS.md`: `scenario_match_wiring`.

### Finding 2

Add two small regression tests when convenient:

- In `tests/test_review_agent.py`, pass JSON `scenario_match` into `_build_user_prompt()` and assert the prompt contains exact/near/dominant/top score values.
- In `tests/test_history_tab.py`, pass JSON `scenario_match` into `_history_rows()` and assert the compact scenario label is present.

## 4. Validation Gaps

- `python -m py_compile services\prediction_store.py services\outcome_capture.py services\review_agent.py ui\history_tab.py tests\test_prediction_store.py tests\test_outcome_capture.py tests\test_review_agent.py tests\test_history_tab.py` - PASS.
- `D:\Git\bin\bash.exe scripts/check.sh` - PASS.
- `D:\anaconda\python.exe -m unittest tests.test_prediction_store tests.test_outcome_capture tests.test_review_agent tests.test_history_tab -v` - failed in sandbox with temp SQLite directory permission errors.
- Same Anaconda unittest command after escalation - PASS, 67/67.
- Permanent test coverage is sufficient for scenario persistence and missing-scenario fallback; review/history scenario rendering was verified by tester temporary assertions, but not committed as durable test cases.

## Required Actions For Next Agent

- None required before keeping Task 009 accepted.
- Optional cleanup: normalize the Task 009 filename and add durable review/history scenario rendering assertions.

## Status Update

- No status change made by this reviewer handoff. `tasks/STATUS.md` already shows Task 009 as `done` from tester verification.
