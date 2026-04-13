# Task 028 Reviewer Handoff - polish_and_guardrails_pack

## findings

1. [medium] External-confirmation guardrail does not handle `None` values safely. In `services/predict_summary.py`, `_format_rs()` converts `None` to the literal string `"None"` and treats it as displayable, while `_external_confirmation_missing()` only treats `""`, `"unavailable"`, and `"unknown"` as missing. A scan result with all peer-RS values set to `None` produces `None NVDA / None SOXX / None QQQ`, keeps risk level `低`, and does not add the expected 外部确认不足 reminder.

2. [low] `tasks/STATUS.md` did not include Task 028 before reviewer pass. I added the canonical mapping and marked Task 028 `blocked` pending the guardrail fix.

3. [low] Merge hygiene caveat: the repo still has stacked prior-task and unrelated dirty files. The review applies only to the Task 028-owned polish/guardrail files, not to the whole worktree.

Code-side scope otherwise looks good: changes stay in predict summary, command rendering, and tests; no scanner core, predict core scoring, AI flow, parser rewrite, or broad UI refactor was found in the Task 028-owned files.

## severity

- medium: missing external-confirmation values can still leak ugly internal text and understate risk, which directly conflicts with Task 028's graceful-degradation goal.
- low: status source-of-truth gap, now corrected.
- low: merge hygiene caveat due dirty worktree state.

## why it matters

Task 028 is specifically a polish and guardrails pack. The main user-visible promise is that missing fields, sample gaps, and external confirmation gaps should degrade cleanly without half-structured dumps. `None` is a common missing-value shape in Python data plumbing, so rendering it as a peer-strength label and assigning low risk makes the guardrail incomplete.

The rest of the implementation is appropriately small: wording is more consistent, empty query/compare render paths are guarded, and the main command/projection/Predict summary paths have stronger regression coverage.

## suggested fix

- Normalize peer-RS values before display and missing checks. Treat `None`, `"none"`, empty strings, `"unavailable"`, and `"unknown"` as missing.
- In `_format_rs()`, skip missing values before formatting labels.
- In `_external_confirmation_missing()`, include `None`-like values in the missing set so all-missing external confirmations raise risk and add the 外部确认不足 reminder.
- Add a focused test in `tests/test_predict_summary.py` with `relative_strength_5d_summary={"vs_nvda": None, "vs_soxx": None, "vs_qqq": None}` asserting:
  - no `"None NVDA"` / raw `None` appears in `summary_text`
  - risk level is `高`
  - `risk_reminders` includes 外部确认不足

## merge recommendation

recommendation: needs fixes before merge.

status suggestion: keep Task 028 blocked until the `None` external-confirmation guardrail is fixed and covered by a test.

Validation run:

- `D:\anaconda\python.exe -m py_compile services\predict_summary.py ui\command_bar.py tests\test_predict_summary.py tests\test_data_workbench_wiring.py` - PASS
- `D:\anaconda\python.exe -m unittest tests.test_predict_summary tests.test_data_workbench_wiring -v` - PASS, 30/30
- `D:\anaconda\python.exe -m unittest tests.test_command_parser tests.test_command_projection_wiring tests.test_command_center_stability tests.test_projection_orchestrator tests.test_projection_entrypoint tests.test_research_loop_ui_apptest tests.test_command_bar_apptest -v` - PASS, 108/108 after rerun outside sandbox; first sandbox run failed only on Windows Temp/SQLite/AppTest permissions
- `D:\Git\bin\bash.exe scripts/check.sh` - PASS
- Direct smoke checks - PASS for projection/query/compare main paths:
  - `根据博通20天数据推演下一个交易日走势`
  - `调出博通最近20天收盘价`
  - `比较博通和英伟达最近20天收盘价`
- Reviewer edge spot-check - FAIL: all-`None` peer RS values render as `None NVDA / None SOXX / None QQQ` and keep risk `低`.
