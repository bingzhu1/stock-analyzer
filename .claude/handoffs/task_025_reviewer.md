# Task 025 Reviewer Handoff - projection_final_wiring

## findings

1. [medium] Scoped merge hygiene caveat: the Task 025-owned changes reviewed here are in the expected projection/command/tests surface, but the current worktree also contains unrelated dirty changes in files such as `predict.py`, `scanner.py`, `research.py`, `.claude/PROJECT_STATUS.md`, and older task/workflow files. Those files are not listed in the Task 025 builder handoff and are outside this task's allowed scope.

2. [low] `tasks/STATUS.md` did not include Task 025 in the canonical mapping/status table before reviewer pass. I added the Task 025 mapping and moved the scoped review state to `in-test`.

3. No functional blocker found in the Task 025-owned projection wiring. The projection command now returns a `final_projection_report` with readable report text and the required Chinese fields instead of an advisory-only/preflight dump. Query/compare regressions were not observed in the focused regression set.

## severity

- medium: merge-scope hygiene caveat, because merging the whole dirty worktree would violate Task 025 boundaries and could alter scanner/predict behavior.
- low: status source-of-truth gap, now corrected in `tasks/STATUS.md`.

## why it matters

Task 025 explicitly allows final projection wiring and result integration, but forbids scanner core changes, predict core scoring changes, AI/API work, and broad UI/refactor work. The reviewed Task 025 implementation stays within the MVP intent: `run_projection` calls the existing entrypoint/orchestrator chain, formats a small final report, and keeps advisory context secondary.

The dirty-worktree caveat matters because some unrelated files currently modify prediction/scanner/research behavior. Even if those changes are from other tasks, including them in a Task 025 merge would make the final report behavior harder to trust and would break the task boundary.

## suggested fix

- Merge or stage only the Task 025-owned files from the builder handoff plus this reviewer handoff/status update:
  - `services/projection_orchestrator.py`
  - `services/projection_entrypoint.py`
  - `ui/command_bar.py` Task 025 projection hunks
  - `tests/test_projection_orchestrator.py`
  - `tests/test_projection_entrypoint.py`
  - `tests/test_command_projection_wiring.py`
  - `tests/test_command_center_stability.py`
  - `.claude/handoffs/task_025_builder.md`
  - `.claude/handoffs/task_025_reviewer.md`
  - `tasks/025_projection_final_wiring.md`
  - `tasks/STATUS.md`
- Keep unrelated dirty files out of the Task 025 merge/commit unless their owning tasks explicitly include them.

## merge recommendation

recommendation: approve scoped Task 025 implementation.

status suggestion: move Task 025 to in-test.

Do not merge the entire dirty worktree as Task 025. The approval applies to the scoped Task 025 projection final wiring only.

Validation run:

- `D:\anaconda\python.exe -m py_compile services\projection_orchestrator.py services\projection_entrypoint.py ui\command_bar.py tests\test_projection_orchestrator.py tests\test_projection_entrypoint.py tests\test_command_projection_wiring.py tests\test_command_center_stability.py` - PASS
- `D:\anaconda\python.exe -m unittest tests.test_projection_orchestrator tests.test_projection_entrypoint tests.test_command_projection_wiring tests.test_command_center_stability -v` - PASS, 28/28
- `D:\anaconda\python.exe -m unittest tests.test_command_parser tests.test_data_workbench_wiring tests.test_projection_orchestrator tests.test_projection_entrypoint tests.test_command_projection_wiring tests.test_command_center_stability -v` - PASS, 122/122
- `D:\Git\bin\bash.exe scripts/check.sh` - PASS
- Direct spot-check `根据博通20天数据推演下一个交易日走势` - PASS, returned `projection_report.kind == final_projection_report` with report text containing 明日方向/开盘倾向/收盘倾向/confidence
