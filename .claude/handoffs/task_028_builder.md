# Task 028 Builder Handoff

## context scanned
- `tasks/028_polish_and_guardrails_pack.md`
- `tasks/STATUS.md`
- `.claude/handoffs/task_024_tester.md`
- `.claude/handoffs/task_025_tester.md`
- `.claude/handoffs/task_026a_tester.md`
- Relevant command/projection/predict summary files and tests.

## changed files
- `services/predict_summary.py`
- `ui/command_bar.py`
- `tests/test_predict_summary.py`
- `tests/test_data_workbench_wiring.py`
- `.claude/handoffs/task_028_builder.md`

## implementation
- Unified readable summary wording for confidence, historical bias, open/close states, volume state, and relative-strength comparison labels.
- Added safe fallbacks for malformed/missing scan details and missing external confirmation, with explicit risk reminders.
- Normalized prediction summary text so projection/Predict summaries avoid raw internal phrases such as `mixed`, `stronger`, `gap_up`, and `Prediction is`.
- Added query empty-result warning and compare zero-sample/empty-table guardrails in command bar rendering.
- Added regression tests for summary wording, external confirmation guardrails, empty query rendering, and empty compare rendering.

## validation
- `D:\anaconda\python.exe -m py_compile services\predict_summary.py ui\command_bar.py tests\test_predict_summary.py tests\test_data_workbench_wiring.py` passed.
- `D:\anaconda\python.exe -m unittest tests.test_predict_summary tests.test_data_workbench_wiring -v` passed, 30 tests.
- `D:\anaconda\python.exe -m unittest tests.test_command_parser tests.test_command_projection_wiring tests.test_command_center_stability tests.test_projection_orchestrator tests.test_projection_entrypoint tests.test_research_loop_ui_apptest tests.test_command_bar_apptest -v` passed, 108 tests.
- Direct query/compare/projection smoke check passed for `根据博通20天数据推演下一个交易日走势`.
- `D:\Git\bin\bash.exe scripts/check.sh` passed.

## remaining risks
- No new core prediction/scanner features were added; this remains a polish and guardrail pass only.
- Future unseen factor strings may still pass through as-is if no formatter mapping exists.
- Existing unrelated dirty worktree files and local git ignore permission warning were not changed.

---

## 2026-04-20 follow-up

### context scanned
- `.claude/handoffs/task_028_reviewer.md`
- `services/predict_summary.py`
- `tests/test_predict_summary.py`

### changed files
- `services/predict_summary.py`
- `tests/test_predict_summary.py`
- `.claude/handoffs/task_028_builder.md`

### implementation
- Added `_is_missing_external_value()` to normalize missing peer-relative-strength values.
- Updated `_format_rs()` to skip `None` / empty / unavailable-like values instead of rendering raw text such as `None NVDA`.
- Updated `_external_confirmation_missing()` so all-missing peer confirmations, including Python `None`, correctly trigger the 外部确认不足 guardrail and high-risk downgrade.
- Added a focused regression test for `vs_nvda=None`, `vs_soxx=None`, `vs_qqq=None`.

### validation
- Focused regression test was added for the exact reviewer-reported edge case.
- Runtime test execution was not performed in this environment and still needs tester confirmation.

### remaining risks
- Tester still needs to confirm no wording regressions in readable summaries after the `None` normalization change.
