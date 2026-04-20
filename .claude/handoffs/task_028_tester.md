# Task 028 Tester Handoff — polish_and_guardrails_pack

## commands run
- `Get-Content tasks/028_polish_and_guardrails_pack.md` — checked task scope and validation requirements.
- `Get-Content tasks/STATUS.md` — checked current task status context.
- `Get-Content .claude/handoffs/task_028_builder.md` — checked builder implementation and validation notes.
- `Get-Content .claude/handoffs/task_028_reviewer.md` — reviewer handoff not present at test time.
- `rg --files tests | rg "test_(command_bar_apptest|data_workbench_wiring|command_projection_wiring|predict_|projection_|command_center_stability|command_parser|research_loop_ui_apptest)"` — confirmed relevant test files.
- `rg -n "样本不足|外部确认不足|历史分布混杂|高位|暂无|空|没有可显示|readable|stronger|mixed|gap_up|Prediction is" services\predict_summary.py ui\command_bar.py tests\test_predict_summary.py tests\test_data_workbench_wiring.py` — checked wording/guardrail coverage.
- `D:\anaconda\python.exe -m py_compile services\predict_summary.py ui\command_bar.py tests\test_predict_summary.py tests\test_data_workbench_wiring.py tests\test_command_projection_wiring.py tests\test_projection_orchestrator.py tests\test_projection_entrypoint.py tests\test_command_bar_apptest.py` — PASS
- `D:\anaconda\python.exe -m unittest tests.test_predict_summary tests.test_data_workbench_wiring -v` — PASS, 30/30
- `D:\anaconda\python.exe -m unittest discover -s tests -p "test_projection_*.py" -v` — PASS, 22/22 outside sandbox
- `D:\anaconda\python.exe -m unittest tests.test_command_projection_wiring tests.test_command_center_stability -v` — PASS, 19/19 outside sandbox
- `D:\anaconda\python.exe -m unittest tests.test_command_bar_apptest -v` — PASS, 7/7 outside sandbox
- `D:\anaconda\python.exe -m unittest tests.test_command_parser tests.test_data_workbench_wiring -v` — PASS, 96/96 outside sandbox
- `D:\anaconda\python.exe -m unittest discover -s tests -p "test_predict_*.py" -v` — PASS, 5/5
- `D:\anaconda\python.exe -m unittest tests.test_research_loop_ui_apptest -v` — PASS, 2/2 outside sandbox
- Manual projection command spot-check:
  - `根据博通20天数据推演下一个交易日走势`
  - PASS, projection command returned `advisory_only = False` and readable summary with 明日基准判断 / 明日方向 / 开盘推演 / 收盘推演 / 为什么这样判断 / 风险提醒.
- Manual query/compare spot-checks:
  - `调出博通最近20天收盘价` — PASS, returned AVGO with 20 rows.
  - `比较博通和英伟达最近20天收盘价` — PASS, returned field `Close` and stats `{total: 20, matched: 13, mismatched: 7, match_rate: 65.0}`.
- Manual graceful-degradation spot-checks:
  - `build_predict_readable_summary({})` — PASS, safe neutral/low fallback with readable rationale/risk.
  - `build_predict_readable_summary(... insufficient_sample ...)` — PASS, emitted 样本不足 / 历史样本不足 risk wording.
  - `build_predict_readable_summary(... missing external confirmation ...)` — PASS, emitted 外部确认不足 risk wording.
- `D:\Git\bin\bash.exe scripts/check.sh` — PASS

## result
- PASS.
- Wording consistency improved for readable summary/projection:
  - conclusion labels use 明日方向 / 开盘倾向 or 开盘推演 / 收盘倾向 or 收盘推演.
  - risk wording includes 样本不足, 历史分布混杂, 外部确认不足.
  - manual projection output no longer exposed raw internal strings such as `mixed`, `stronger`, `gap_up`, or `Prediction is`.
- Graceful degradation checks passed for:
  - empty command input via command center/AppTest coverage.
  - missing predict/scan fields.
  - insufficient sample summary.
  - compare empty result rendering.
  - query empty result rendering.
  - projection partial/missing predict fields through projection tests.
  - external confirmation missing.
- Regression checks passed for:
  - `query_data`
  - `compare_data`
  - projection command
  - Predict/projection readable summary
  - command center to execution-layer main paths

## failed cases
- No task-direct product/code failures found.

## gaps
- `.claude/handoffs/task_028_reviewer.md` was not present, so no reviewer-specific findings were verified.
- Manual UI verification was via Streamlit AppTest/fake Streamlit/unit rendering, not by opening the app in a browser.
- Future unmapped factor strings can still pass through as-is, as builder noted.
- Some non-core labels remain intentionally technical where they are domain shorthand, but the user-facing main summary no longer showed the previously targeted raw strings in spot-checks.
- Existing unrelated dirty worktree/local git ignore permission warnings were not addressed by this task.

## recommendation
- Mark Task 028 as done.
- No blocker found for this task.

---

## 2026-04-20 focused follow-up

### commands run
Focused validation was executed in a local minimal test harness reconstructed from the exact current Task 028 source files fetched from the repository (sandbox could not clone GitHub directly).

- `python -m unittest tests.test_predict_summary -v`
- `python -m py_compile services/predict_summary.py ui/predict_tab.py tests/test_predict_summary.py`

### result
- PASS.
- `tests.test_predict_summary` PASS — 6/6 tests passed.
- `py_compile` PASS for the direct Task 028 summary/render files.
- The previously blocked reviewer edge case is now covered and passes:
  - all-`None` peer RS values no longer render as `None NVDA / None SOXX / None QQQ`
  - risk level degrades to `高`
  - `risk_reminders` includes 外部确认不足

### failed cases
- None in focused follow-up validation.

### gaps
- This focused follow-up used a reconstructed minimal environment, not a full repository checkout.
- I did not rerun the broader 028 regression matrix in this sandbox; this follow-up was intentionally scoped to the reviewer-blocked `None` guardrail path and direct summary/render files.

### recommendation
- Mark Task 028 `done`.
- No further Task 028 code change is required based on the follow-up reviewer/tester closure.
