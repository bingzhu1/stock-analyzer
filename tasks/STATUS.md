# Task Status

> 更新规则：每次状态变化后更新此表。  
> Status: `todo` | `in-progress` | `in-review` | `in-test` | `done` | `blocked`
> Canonical task 文件只放在 `tasks/` 目录；不要再创建 `.claude/tasks/`。
> 旧 task 文件已移到 `.claude/legacy_tasks/`，仅作历史参考。

## Canonical task mapping

- 001 — `prediction_store`
- 002 — `outcome_capture`
- 003 — `review_agent`
- 004 — `research_loop_ui`
- 005 — `task_system_cleanup`
- 006 — `fix_task001_blockers`
- 007 — `research_loop_ui_apptest`
- 008 — `history_tab`
- 009 — `scenario_match_wiring`

## Handoff status rules

- builder 完成实现后，通常更新为 `in-review`
- reviewer 通过后，通常更新为 `in-test`
- tester 通过后，通常更新为 `done`
- 任何 agent 发现 blocker，更新为 `blocked` 并在 notes 写清楚原因

| task_id | title | owner | status | last updated | notes |
|---------|-------|-------|--------|--------------|-------|
| 001 | prediction_store | reviewer | blocked | 2026-04-12 | Review found duplicate-save ordering risk, unenforced FK/orphan-row risk, and unscoped working-tree files; see task_001_reviewer.md |
| 002 | outcome_capture | builder | done | 2026-04-11 | 18 tests pass; actual_prev_close = NULL when no prior day |
| 003 | review_agent | builder | done | 2026-04-12 | 22 tests pass; naming trap fixed; rule-based fallback verified |
| 004 | research_loop_ui | builder | done | 2026-04-11 | 3-step Research Loop wired into Predict tab; retroactive scope declared |
| 005 | task_system_cleanup | tester | done | 2026-04-12 | Tester follow-up passed: source-of-truth/status docs aligned, legacy banners present, Task 006 mapped, and no settings diff remains |
| 006 | fix_task001_blockers | tester | done | 2026-04-12 | Tester verified deterministic lookup, FK/orphan guards, forward-only status machine, and 60 focused regression tests |
| 007 | research_loop_ui_apptest | tester | done | 2026-04-12 | Tester verified AppTest runs, covers Research Loop preconditions/main flow, and keeps Task 007 implementation test-only |
| 008 | history_tab | tester | done | 2026-04-12 | Tester verified History tab render, recent predictions table, detail view, helper tests, and minimal app wiring |
| 009 | scenario_match_wiring | tester | done | 2026-04-12 | Tester verified scenario_match persistence, no-scenario fallback, review/history compatibility, and 67 focused regressions |
