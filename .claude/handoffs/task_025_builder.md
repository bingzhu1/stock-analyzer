# Task 025 Builder Handoff — projection_final_wiring

## context scanned
- `tasks/025_projection_final_wiring.md`
- `tasks/STATUS.md`
- `.claude/handoffs/task_020_builder.md`
- `.claude/handoffs/task_024_builder.md`
- `.claude/handoffs/task_024_tester.md`
- `services/projection_entrypoint.py`
- `services/projection_orchestrator.py`
- `ui/command_bar.py`
- related projection / command tests

## changed files
- `services/projection_orchestrator.py`
- `services/projection_entrypoint.py`
- `ui/command_bar.py`
- `tests/test_projection_orchestrator.py`
- `tests/test_projection_entrypoint.py`
- `tests/test_command_projection_wiring.py`
- `tests/test_command_center_stability.py`
- `.claude/handoffs/task_025_builder.md`

## implementation
- Rewired projection orchestrator from advisory-only packaging to final report output.
- Added a thin adapter that uses existing AVGO daily coded data, historical match helpers, `scanner.run_scan()`, and `predict.run_predict()`.
- Added `format_projection_report()` to produce stable Chinese report fields:
  - 明日方向：偏多 / 偏空 / 中性
  - 开盘倾向：高开 / 平开 / 低开
  - 收盘倾向：偏强 / 震荡 / 偏弱
  - confidence
  - 依据摘要
  - 风险提醒
- Kept advisory/preflight output as context and risk reminders, but `advisory_only` is now `False`.
- Command bar now renders the final report first instead of showing preflight JSON as the primary result.
- Command bar forwards `lookback_days=20` for `根据博通20天数据推演下一个交易日走势` by lightly reading the raw command text; parser behavior was not changed.

## validation
- `D:\anaconda\python.exe -m py_compile services\projection_orchestrator.py services\projection_entrypoint.py ui\command_bar.py tests\test_projection_orchestrator.py tests\test_projection_entrypoint.py tests\test_command_projection_wiring.py tests\test_command_center_stability.py` — PASS
- `D:\anaconda\python.exe -m unittest tests.test_projection_orchestrator tests.test_projection_entrypoint tests.test_command_projection_wiring tests.test_command_center_stability -v` — PASS, 28/28 outside sandbox
- Direct command spot-check: `根据博通20天数据推演下一个交易日走势` — PASS, returned final Chinese report with direction/open/close/confidence/basis/risk
- Query/compare spot-checks — PASS (`调出博通最近20天收盘价`, `比较博通和英伟达最近20天收盘价`)
- `D:\anaconda\python.exe -m unittest tests.test_command_parser tests.test_data_workbench_wiring tests.test_projection_orchestrator tests.test_projection_entrypoint tests.test_command_projection_wiring tests.test_command_center_stability -v` — PASS, 122/122 outside sandbox
- `D:\Git\bin\bash.exe scripts/check.sh` — PASS

## remaining risks
- Final projection report is AVGO-only because existing scanner/predict path is AVGO-specific.
- Projection uses latest available daily coded data; `lookback_days` is reported as command context, while the existing scanner still uses its historical match logic.
- No AI summary and no Predict tab Chinese block were added, by scope.
- The sandbox created inaccessible temporary directories during failed validation attempts (`.tmp/...`, `tmpb4m1zozv`); cleanup attempts with ACL reset/takeown still could not remove them. They are not task implementation files but may cause `git status` warnings until cleaned outside this session.
