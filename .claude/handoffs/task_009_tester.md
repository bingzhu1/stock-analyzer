# Tester Handoff - Task 009: scenario_match_wiring

## Status
PASS

## Date
2026-04-12

## What was tested
- Read required workflow docs, Task 009 task context, and builder handoff.
- Inspected scenario wiring in `services/outcome_capture.py`, `services/prediction_store.py`, `services/review_agent.py`, and `ui/history_tab.py`.
- Inspected tests covering scenario persistence, missing-scenario fallback, list/history compatibility, and review compatibility.
- Ran compile, required check script, focused unit/regression tests, and temporary direct assertions for review/history scenario rendering.

## commands run

| command | result |
|---------|--------|
| `Get-Content -Encoding utf8 .claude\CLAUDE.md` | PASS - required workflow doc read. |
| `Get-Content -Encoding utf8 .claude\CHECKLIST.md` | PASS - required checklist read. |
| `Get-Content -Encoding utf8 tasks\STATUS.md` | PASS - canonical status table read. |
| `Get-Content -Encoding utf8 tasks\009_scenario_match_wiring.md` | FAIL - requested path does not exist. Actual task file is `tasks\009_scenario_matching_wiring.md`. |
| `Get-Content -Encoding utf8 .claude\handoffs\task_009_builder.md` | PASS - builder handoff read; it also documents the task filename mismatch. |
| `Get-Content -Encoding utf8 tasks\009_scenario_matching_wiring.md` | PASS - actual Task 009 task file read. |
| `Get-Content -Encoding utf8 .claude\PROJECT_STATUS.md` | PASS - project status read per `.claude/CLAUDE.md`. |
| `rg -n "scenario_match|historical_match_summary|scenario|dominant_historical_outcome|match_sample_size" services ui tests tasks .claude\handoffs\task_009_builder.md` | PASS - located scenario wiring and coverage. |
| `Get-Content -Encoding utf8 services\outcome_capture.py` | PASS - inspected scenario construction and capture path. |
| `Get-Content -Encoding utf8 services\prediction_store.py` | PASS - inspected `scenario_match` persistence and list projection. |
| `Get-Content -Encoding utf8 services\review_agent.py` | PASS - inspected review prompt scenario formatting. |
| `Get-Content -Encoding utf8 ui\history_tab.py` | PASS - inspected History scenario display. |
| `Get-Content -Encoding utf8 tests\test_outcome_capture.py` | PASS - inspected scenario persistence and missing-scenario tests. |
| `Get-Content -Encoding utf8 tests\test_prediction_store.py` | PASS - inspected `list_predictions()` scenario test. |
| `rg -n "scenario_match|Scenario Match|_build_user_prompt|_scenario_match_label|history_rows|scenario_label" tests\test_review_agent.py tests\test_history_tab.py ui\history_tab.py services\review_agent.py` | PASS - confirmed review/history scenario code paths. |
| `python -m py_compile services\prediction_store.py services\outcome_capture.py services\review_agent.py ui\history_tab.py tests\test_prediction_store.py tests\test_outcome_capture.py tests\test_review_agent.py tests\test_history_tab.py` | PASS. |
| `python -m unittest discover -s tests -p "test_prediction_store.py" -v` | PASS - 21/21. |
| `python -m unittest discover -s tests -p "test_outcome_capture.py" -v` | FAIL in system Python - `pandas` is not installed. |
| `& 'D:\Git\bin\bash.exe' scripts/check.sh` | PASS - required project check passed. |
| `& 'D:\anaconda\python.exe' -m unittest tests.test_prediction_store tests.test_outcome_capture tests.test_review_agent tests.test_history_tab -v` | PASS - 67/67 focused regressions passed. |
| Temporary `D:\anaconda\python.exe` direct scenario assertions for `review_agent._build_user_prompt()` and `history_tab._history_rows()` | PASS - review prompt includes readable scenario summary; History scenario label works with and without scenario data. |
| `git status --short app.py research.py scanner.py predict.py services\prediction_store.py services\outcome_capture.py services\review_agent.py ui\history_tab.py tests\test_outcome_capture.py tests\test_prediction_store.py tests\test_review_agent.py tests\test_history_tab.py tasks\009_scenario_matching_wiring.md tasks\STATUS.md .claude\handoffs\task_009_builder.md .claude\handoffs\task_009_tester.md` | PASS with caveat - Task 009 implementation files are present; inherited dirty `app.py` remains from Task 008. |
| `git diff --stat -- app.py research.py scanner.py predict.py services\prediction_store.py services\outcome_capture.py services\review_agent.py ui\history_tab.py tests\test_outcome_capture.py tests\test_prediction_store.py tests\test_review_agent.py tests\test_history_tab.py tasks\009_scenario_matching_wiring.md tasks\STATUS.md .claude\handoffs\task_009_builder.md` | PASS with caveat - tracked forbidden diff only shows prior `app.py` History tab wiring; untracked Task 009 files are not represented in stat. |

## Result
- `scenario_match` is written in the supported path: PASS. `capture_outcome()` builds compact JSON from `prediction_log.scan_result_json.historical_match_summary` and passes it to `save_outcome()`. `test_capture_outcome_persists_scenario_match_from_scan_summary` verifies the stored JSON fields.
- Missing scenario data still works: PASS. If saved scan data is absent or not usable, `_build_scenario_match()` returns `None`, and `test_scenario_match_is_null_by_default` verifies `scenario_match` remains SQL NULL while outcome capture succeeds.
- History is not broken: PASS. `list_predictions()` now includes `outcome_log.scenario_match`; History renders a compact scenario label in the recent table and still shows outcome detail including raw `scenario_match`. Existing History helper tests pass, and a temporary direct assertion verified History labels for both scenario and no-scenario rows.
- Review is not broken: PASS. Review prompt construction still passes the focused review suite, and a temporary assertion verified the prompt includes `Scenario Match: exact=3, near=2, dominant=bullish, top_context_score=87.5` when scenario data exists.
- Focused regression suite: PASS. Anaconda environment ran 67/67 across prediction store, outcome capture, review agent, and history tab.
- Forbidden files: PASS with attribution caveat. `research.py`, `scanner.py`, and `predict.py` are clean in the scoped status check. `app.py` is dirty, but its mtime/diff correspond to prior Task 008 History tab wiring, not Task 009 scenario wiring.

## failed cases
- None for Task 009 behavior.

## manual test suggestions
- Use the Predict tab to save a prediction whose scan result includes `historical_match_summary`, then Capture Outcome and inspect `outcome_log.scenario_match` in SQLite.
- Open the History tab and confirm the recent predictions table shows a compact scenario summary such as `exact 3 / near 2 / bullish`.
- Generate a review for that same prediction and confirm the prompt/review path continues to work when `scenario_match` is present.
- Repeat with an older prediction or a saved prediction without `historical_match_summary`; outcome capture, History, and Review should still work with blank/`N/A` scenario display.

## validation gaps
- The user-requested task path `tasks/009_scenario_match_wiring.md` is missing; actual file is `tasks/009_scenario_matching_wiring.md`. I used the actual file after confirming the mismatch in builder handoff.
- `tasks/009_scenario_matching_wiring.md` and `.claude/PROJECT_STATUS.md` had stale status/project text before tester close-out. I updated the task file and canonical status table, but did not edit `.claude/PROJECT_STATUS.md` because Task 009 scope does not include it.
- System Python cannot run outcome/history tests because required dependencies are missing; real focused regression execution was verified with `D:\anaconda\python.exe`.
- Current worktree is dirty from prior tasks, so `git status` cannot fully prove forbidden-file attribution. The reviewed Task 009 implementation surface is confined to allowed service/UI/test/task/handoff files.
- Existing tests do not explicitly cover an empty `{}` `historical_match_summary`; they cover absent scan scenario data. Empty summary currently produces a compact JSON with null/zero values rather than SQL NULL.

## Required actions for next agent
- None for Task 009.
- Optional cleanup: normalize the Task 009 filename/mapping (`scenario_match` vs `scenario_matching`), update `.claude/PROJECT_STATUS.md`, and consider adding an empty-`historical_match_summary` fallback test.

## Status update
- `tasks/STATUS.md` updated to: `done`.
