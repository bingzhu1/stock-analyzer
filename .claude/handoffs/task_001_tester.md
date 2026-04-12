# Tester Handoff — Task 001: prediction_store

## Status
PASS

## Date
2026-04-12

## What was tested
- Scoped validation for Task 001 only: `services/prediction_store.py`, `tests/test_prediction_store.py`, and `requirements.txt`.
- Required project check script.
- Reviewer-requested regression coverage for `outcome_capture` and `review_agent`.
- Full unittest discovery to surface cross-suite failures.
- Manual UI path was not executed in this tester pass.

## Commands run

| command | result |
|---------|--------|
| `bash scripts/check.sh` | FAIL — default `bash` resolves to WSL and cannot translate the `D:\dev\...` project path; no project checks ran. |
| `& 'D:\Git\bin\bash.exe' scripts/check.sh` | FAIL in sandbox — Git Bash could not create signal pipe, Win32 error 5. |
| `& 'D:\Git\bin\bash.exe' scripts/check.sh` (escalated) | PASS. |
| `python -m py_compile services\prediction_store.py tests\test_prediction_store.py` | PASS. |
| `python -m unittest discover -s tests -p "test_prediction_store.py"` | PASS — 17/17. |
| `python -m unittest discover -s tests -p "test_*.py"` | FAIL — system Python lacks `pandas`, so `test_outcome_capture` cannot import. |
| `& 'D:\anaconda\python.exe' -c "import pandas, streamlit, yfinance; print('deps ok')"` | PASS — dependency-capable Python found. |
| `& 'D:\anaconda\python.exe' -m py_compile services\prediction_store.py tests\test_prediction_store.py` | PASS. |
| `& 'D:\anaconda\python.exe' -m unittest discover -s tests -p "test_prediction_store.py"` | PASS after escalation — 17/17. Non-escalated attempt failed because sandbox denied temp SQLite DB creation under `C:\Users\Zach_Wen\AppData\Local\Temp`. |
| `& 'D:\anaconda\python.exe' -m unittest discover -s tests -p "test_outcome_capture.py"` | PASS after escalation — 18/18. |
| `& 'D:\anaconda\python.exe' -m unittest discover -s tests -p "test_review_agent.py"` | PASS after escalation — 22/22. |
| `& 'D:\anaconda\python.exe' -m unittest discover -s tests -p "test_*.py"` | FAIL after escalation — 75 tests run, 1 failure, 1 error. See failed cases below. |

## Result
- Task 001 scoped checks pass.
- DB schema/CRUD/status-machine tests pass: 17/17.
- Reviewer-requested regression files pass: `test_outcome_capture.py` 18/18 and `test_review_agent.py` 22/22.
- `tasks/STATUS.md` was already `done` for task 001 and was left unchanged.

## Failed cases
- Out of scope / pre-existing: `test_control_path.ControlPathTests.test_executor_replies_to_unsupported_without_analysis` still expects `"supported read-only command"`, but the current message is `"That request is outside the read-only Control Chat command set..."`.
- Out of scope / environment or encoding issue: `test_control_tab_apptest.ControlTabAppTests.test_chat_help_request_returns_schema_help` hits a Streamlit script compilation `UnicodeDecodeError` while reading `app.py`, then `chat_input[0]` is missing. This is outside Task 001 allowed files.
- Environment-only: default `bash` points to WSL and cannot run from this Windows `D:\` workspace. Git Bash works when run escalated.
- Environment-only: system Python 3.12 does not have `pandas`; Anaconda Python has the required dependencies.

## Manual test suggestions
- Start the Streamlit app with the dependency-capable Python environment and open the Predict tab.
- Run the happy path: generate or load a prediction, click `Save Today's Prediction`, then verify a new `prediction_log` row with `status = saved`, `analysis_date`, and `prediction_for_date`.
- Capture an outcome for the saved prediction and verify the same prediction advances to `outcome_captured`.
- Generate the review and verify a `review_log` row exists and the prediction advances to `review_generated`.
- For the first-prior-day edge case, verify `actual_prev_close` remains `NULL` rather than `0.0`.
- For review prompt regression, verify the review prompt uses `prediction_for_date` and does not show `Date: N/A` when the row has a real date.

## Required actions for next agent
- None for Task 001.
- Triage the out-of-scope Control/AppTest failures under a separate task if full-suite green is required.

## Status update
- `tasks/STATUS.md` unchanged: task 001 remains `done`.
