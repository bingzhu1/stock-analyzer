# Reviewer Handoff - Task 001: prediction_store

## Status
NEEDS_FIXES

## Date
2026-04-12

## What was reviewed
Current working tree review. I read the required project docs, canonical task files 001-004, `task_001_builder.md`, prior task 001 reviewer/tester handoffs, and inspected the tracked + untracked changes.

Note: `task_001_builder.md` is the only present builder handoff. `task_004_builder.md` is missing even though the current tracked code diff includes `ui/predict_tab.py`, so this review also calls out task/scope hygiene issues.

## 1. findings

### Finding 1 - severity: high
The working tree includes a separate Control Chat feature and generated/local artifacts that are not covered by the canonical research-loop tasks or builder handoffs.

Evidence:
- Untracked files include `services/agent_schema.py`, `services/agent_parser.py`, `services/query_executor.py`, `docs/control_layer.md`, `tests/test_control_path.py`, `tests/test_control_tab_apptest.py`, `snapshots/...`, and `.venv/...`.
- Canonical tasks 001-004 cover prediction storage, outcome capture, review generation, and Predict-tab research loop UI. None authorize Control Chat, snapshots, or virtualenv files.
- Full test discovery currently fails in the Control Chat tests.

### Finding 2 - severity: medium
`get_prediction_by_date()` does not reliably return the latest save for duplicate `(symbol, prediction_for_date)` rows.

Evidence:
- `save_prediction()` stores `created_at` with `timespec="seconds"`.
- `get_prediction_by_date()` orders only by `created_at DESC`.
- The test acknowledges same-second collisions and only asserts that either saved id may be returned.

### Finding 3 - severity: medium
SQLite foreign keys are declared but not enforced, and child-row save helpers can create orphan outcomes/reviews.

Evidence:
- `_get_conn()` opens SQLite connections without `PRAGMA foreign_keys = ON`.
- `save_outcome()` inserts `prediction_id` directly.
- `save_review()` inserts the review and only afterwards calls `update_prediction_status()`, which silently returns if the prediction is missing.

### Finding 4 - severity: low
The required `scripts/check.sh` is too narrow for the new research-loop code.

Evidence:
- It only compiles `app.py`, `scanner.py`, and `predict.py`.
- It does not compile or test the new `services/*`, `ui/predict_tab.py`, or `tests/test_*` files.

## 2. why it matters

Finding 1 matters because a merge could ship unrelated, unscoped code and data artifacts along with the research-loop work. The full test suite is also red, so downstream reviewers cannot tell whether failures are accepted pre-existing debt or regressions from the unscoped Control Chat files.

Finding 2 matters because the UI explicitly supports "Save New Version". If two saves happen inside the same second, later lookup by date can return the older row, causing outcome capture or history views to attach to the wrong prediction.

Finding 3 matters because persistence can become internally inconsistent. A typo or future caller can insert an outcome/review for a nonexistent prediction; `save_review()` can then leave `review_log` populated while the parent prediction status never advances.

Finding 4 matters because `bash scripts/check.sh` can pass while the actual changed modules are syntactically broken or their tests fail. That weakens the task's required validation gate.

## 3. suggested fix

- For Finding 1: remove/stash `.venv`, `snapshots`, and Control Chat files from this task, or open a separate canonical task with a builder handoff for Control Chat and fix its failing tests before including it.
- For Finding 2: use microsecond timestamps or a monotonic integer/rowid tie-breaker, then order by `created_at DESC, rowid DESC` or equivalent. Strengthen the duplicate-save test to assert the second save is returned.
- For Finding 3: enable `PRAGMA foreign_keys = ON` on every connection, validate parent prediction existence in `save_outcome()` and `save_review()`, and update review status in the same transaction/connection as the review insert.
- For Finding 4: expand `scripts/check.sh` to py-compile all changed Python modules and run the focused unit suites for prediction store, outcome capture, and review agent.

## 4. validation gaps

Commands run:
- `D:\Git\bin\bash.exe scripts/check.sh` - PASS after running Git Bash outside sandbox.
- `D:\anaconda\python.exe -m unittest tests.test_prediction_store tests.test_outcome_capture tests.test_review_agent` - PASS, 57 tests.
- `D:\anaconda\python.exe -m unittest discover -s tests` - FAIL, 75 tests run, 1 failure and 1 error.

Full-suite failures observed:
- `test_control_path.ControlPathTests.test_executor_replies_to_unsupported_without_analysis` expects `"supported read-only command"` but implementation returns `"outside the read-only Control Chat command set"` plus suggestions. Project status says this failure is pre-existing, but it is still red.
- `test_control_tab_apptest.ControlTabAppTests.test_chat_help_request_returns_schema_help` errors because the AppTest script fails to compile with a UTF-8 decode error, leaving no `chat_input` element.

Additional gaps:
- No Streamlit AppTest coverage for the 3-step Research Loop in `ui/predict_tab.py`.
- No test proves "Save New Version" followed by date lookup returns the newest row.
- No test proves SQLite foreign-key enforcement or rejects orphan `outcome_log` / `review_log` rows.
- No task004 builder handoff exists for the Predict-tab UI change.

## Required actions for next agent
- Address the high-severity scope/test issue before merge.
- Fix the duplicate-save ordering and orphan-row persistence risks.
- Re-run focused tests and full test discovery after fixes.
