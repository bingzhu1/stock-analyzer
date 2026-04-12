# Reviewer Handoff - Task 007: research_loop_ui_apptest

## Status
PASS

## Date
2026-04-12

## What was found

## 1. findings

### Finding 1 - severity: low
The Save New Version test covers active session id/date replacement, but it does not exercise the stronger "reset after outcome/review already exists" case.

Evidence:
- `test_save_new_version_resets_session_prediction_id()` clicks Save, then Save New Version, and asserts `saved_prediction_id` changes from `pid-1` to `pid-2`.
- It also asserts the new active prediction has capture available and review locked.
- It does not first capture an outcome or generate a review for `pid-1`, then save a new version and verify the UI drops back to the new prediction's no-outcome/no-review state.

### Finding 2 - severity: low
`tasks/007_research_loop_ui_apptest.md` still says `## Status todo` while `tasks/STATUS.md` has advanced Task 007 beyond todo.

Evidence:
- Canonical status table mapped Task 007 as `in-review` before this review and is updated to `in-test` by this handoff.
- The task file's own status section was not advanced by the builder.

No high or medium findings found.

## 2. why it matters

Finding 1 matters because the user-facing copy says saving a new version resets outcome/review for the session. The current test proves the active id changes and review is locked for a fresh second save, but a regression involving stale outcome/review display after a completed first version would be easier to catch with a fuller state-reset test.

Finding 2 matters because future agents read both the task file and `tasks/STATUS.md`. The status table is the canonical source, but stale task-file status can still cause momentary confusion during handoff.

## 3. suggested fix

- Optional: add a third AppTest path or extend the Save New Version test to Save -> Capture -> Generate Review -> Save New Version, then assert the new active id is `pid-2`, Step 2 is available, and Step 3 is locked until the new outcome is captured.
- Optional: sync `tasks/007_research_loop_ui_apptest.md` status during the next status update.

These are not blockers for Task 007.

## 4. validation gaps

Validation run during review:
- `python -m py_compile tests\test_research_loop_ui_apptest.py` - PASS.
- `D:\Git\bin\bash.exe scripts/check.sh` - PASS.
- `D:\anaconda\python.exe -m unittest discover -s tests -p "test_research_loop_ui_apptest.py" -v` - PASS, 2/2, after escalation.

Sandbox note:
- Running the AppTest command inside the sandbox failed with `PermissionError` while Streamlit tried to write its temporary app file under `C:\Users\Zach_Wen\AppData\Local\Temp`. The same test passed outside the sandbox, so this appears environment-related.

Review conclusions:
- The main 3-step Research Loop path is covered: Save Prediction -> Capture Outcome -> Generate Review.
- Button preconditions are covered before save and after save-before-outcome.
- Saved session state and Save New Version active-id replacement are covered.
- No Task 007-specific UI implementation change was needed; the implementation is test-only.
- No scope creep found for Task 007.

## Required actions for next agent
- Tester should rerun the AppTest and decide whether the optional stronger Save New Version reset case should be added now or deferred.

## Status update
- `tasks/STATUS.md` updated to: `in-test`
