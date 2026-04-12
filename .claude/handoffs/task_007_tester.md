# Tester Handoff - Task 007: research_loop_ui_apptest

## Status
PASS

## Date
2026-04-12

## commands run

| command | result |
|---------|--------|
| `Get-Content -Encoding utf8 .claude\CLAUDE.md` | PASS - required workflow doc read. |
| `Get-Content -Encoding utf8 .claude\CHECKLIST.md` | PASS - required checklist read. |
| `Get-Content -Encoding utf8 tasks\STATUS.md` | PASS - canonical status table read. |
| `Get-Content -Encoding utf8 tasks\007_research_loop_ui_apptest.md` | PASS - Task 007 scope and requirements read. |
| `Get-Content -Encoding utf8 .claude\handoffs\task_007_builder.md` | PASS - builder handoff read. |
| `Get-Content -Encoding utf8 .claude\handoffs\task_007_reviewer.md` | PASS - reviewer handoff read after reviewer moved Task 007 to `in-test`. |
| `Get-Content -Encoding utf8 .claude\handoffs\README.md` | PASS - handoff rules read. |
| `Get-Content -Encoding utf8 tests\test_research_loop_ui_apptest.py` | PASS - inspected new AppTest coverage. |
| `git status --short` | PASS with caveat - inspected dirty worktree; inherited dirty paths remain from prior tasks. |
| `git status --short app.py services research.py scanner.py predict.py ui\predict_tab.py tests\test_research_loop_ui_apptest.py tasks\007_research_loop_ui_apptest.md tasks\STATUS.md .claude\handoffs\task_007_builder.md .claude\handoffs\task_007_tester.md` | PASS with caveat - Task 007 test file/handoff/status are present; older dirty forbidden paths are still visible. |
| `git diff -- app.py services research.py scanner.py predict.py ui\predict_tab.py tests\test_research_loop_ui_apptest.py tasks\007_research_loop_ui_apptest.md tasks\STATUS.md .claude\handoffs\task_007_builder.md` | PASS with caveat - tracked forbidden diff shows prior `ui/predict_tab.py` Research Loop implementation, not Task 007 test-only work. |
| `python -m py_compile tests\test_research_loop_ui_apptest.py` | PASS. |
| `python -m unittest discover -s tests -p "test_research_loop_ui_apptest.py" -v` | PASS with skips - system Python ran 2 tests, both skipped because Streamlit AppTest or pandas is not installed. |
| `& 'D:\Git\bin\bash.exe' scripts/check.sh` | PASS - required project check passed. |
| `& 'D:\anaconda\python.exe' -m unittest discover -s tests -p "test_research_loop_ui_apptest.py" -v` | PASS - real AppTest run passed 2/2 after escalation. |
| `rg -n "btn_save_prediction|btn_capture_outcome_locked|btn_generate_review_locked1|btn_capture_outcome|btn_generate_review_locked2|btn_generate_review|btn_save_new_version|saved_prediction_id|saved_prediction_date|fake_outcomes|fake_reviews|Complete Step" tests\test_research_loop_ui_apptest.py ui\predict_tab.py` | PASS - confirmed automated assertions target the Research Loop buttons, preconditions, session state, outcome, review, and Save New Version path. |

## result

- New AppTest runs successfully in the dependency-capable Anaconda environment: 2/2 PASS.
- Main Research Loop path is covered: Save Prediction -> Capture Outcome -> Generate Review.
- Button preconditions are automatically verified:
  - before save: Capture Outcome and Generate Review are disabled
  - after save: Capture Outcome is available and Review remains disabled
  - after outcome: Generate Review is available
- Saved-state behavior is covered through `saved_prediction_id`, `saved_prediction_date`, fake persisted payloads, and Save New Version changing the active saved prediction id from `pid-1` to `pid-2`.
- Builder/reviewer claim that Task 007 was test-only is consistent with the reviewed implementation: `tests/test_research_loop_ui_apptest.py` patches Predict-tab dependencies and does not require UI code changes for this task.

## failed cases

- None for Task 007 behavior.

## manual test suggestions

- Run the Streamlit app manually and walk the Predict tab Research Loop once: Save Prediction, Capture Outcome, Generate Review.
- Confirm the disabled states match the AppTest expectations before save and before outcome.
- Click Save New Version after an initial save and verify the displayed saved id changes and outcome/review must be regenerated for the new session prediction.

## validation gaps

- System Python cannot execute the real AppTest because required dependencies are missing; it reports 2 skipped tests. The real AppTest was verified with `D:\anaconda\python.exe`.
- Current worktree is not clean. Forbidden/out-of-scope paths such as `ui/predict_tab.py`, `services/outcome_capture.py`, `services/prediction_store.py`, `services/review_agent.py`, and `requirements.txt` are dirty or untracked from earlier tasks, so `git status` alone cannot prove attribution for "this round." I did not modify or clean those files.
- The Save New Version AppTest does not cover the stronger Save -> Capture -> Review -> Save New Version reset case. Reviewer classified this as optional hardening, not a blocker.
- `.claude/handoffs/README.md` canonical mapping still lists only 001-006, while `tasks/STATUS.md` maps 007. This did not block Task 007 AppTest validation, but should be cleaned up in a future task-system follow-up.
- I did not run full repository unittest discovery because prior rounds documented unrelated Control/AppTest failures; this pass focused on Task 007 AppTest and required project check.

## Required actions for next agent

- None for Task 007.
- Optional cleanup: add the stronger completed-first-version Save New Version reset test, align `.claude/handoffs/README.md` canonical mapping with Task 007, and clean/commit inherited dirty paths so future scope checks are unambiguous.

## Status update

- `tasks/STATUS.md` updated to: `done`.
