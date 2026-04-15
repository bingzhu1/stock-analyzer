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
- 009 — `scenario_matching_wiring`
- 010 — `task_naming_and_scenario_test_cleanup`
- 011 — `cn_ui_command_parser_mvp`
- 012 — `error_taxonomy`
- 013 — `experience_memory_store`
- 014 — `memory_feedback`
- 015 — `projection_memory_briefing`
- 016 — `projection_preflight`
- 017 — `projection_orchestrator_preflight`
- 018 — `projection_orchestrator_mvp`
- 019 — `projection_entrypoint`
- 020 — `command_projection_wiring`
- 021 — `command_center_stability_fix`
- 022 — `data_workbench_mvp`
- 023 — `command_parser_enhancement`
- 024 — `advanced_stats_output`
- 025 — `projection_final_wiring`
- 026a — `predict_readable_summary_and_ai_polish`
- 028 — `polish_and_guardrails_pack`
- 034 — `conversation_result_renderer_mvp`
- 035 — `projection_evidence_trace_mvp`

## Handoff status rules

- builder 完成实现后，通常更新为 `in-review`
- reviewer 通过后，通常更新为 `in-test`
- tester 通过后，通常更新为 `done`
- 任何 agent 发现 blocker，更新为 `blocked` 并在 notes 写清楚原因

## Handoff recording rules

- every agent must record what it actually did in its handoff
- builder handoff should include: context scanned, changed files, implementation summary, validation steps, remaining risks
- reviewer handoff should include: context scanned, findings, why it matters, suggested fix, validation gaps
- tester handoff should include: context scanned, commands run, result, failed cases, manual test suggestions, coverage gaps

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
| 009 | scenario_matching_wiring | tester | done | 2026-04-12 | Tester verified scenario_match persistence, no-scenario fallback, review/history compatibility, and 67 focused regressions |
| 010 | task_naming_and_scenario_test_cleanup | tester | done | 2026-04-12 | Naming fixed, task file created, 6 new scenario tests pass (33/33); forbidden files clean |
| 011 | cn_ui_command_parser_mvp | tester | done | 2026-04-12 | 52/52 tests pass (45 unit + 7 AppTest); 24 spot-checks PASS; no forbidden files touched |
| 012 | error_taxonomy | tester | done | 2026-04-12 | Tester unblock confirmed: canonical task file complete, tolerant normalization documented, focused 35/35 tests and Git Bash check pass |
| 013 | experience_memory_store | tester | done | 2026-04-12 | Tester verified memory store module, save/get/list/empty behavior, py_compile, and 7/7 focused tests |
| 014 | memory_feedback | tester | done | 2026-04-12 | Tester verified memory feedback helper, store reads, symbol/category filtering, safe empty state, py_compile, and 11/11 focused tests |
| 015 | projection_memory_briefing | tester | done | 2026-04-12 | Tester verified briefing helper, stable advisory output, caution levels, safe empty state, py_compile, and 15/15 focused tests |
| 016 | projection_preflight | tester | done | 2026-04-12 | Tester verified preflight helper, stable briefing package, ready/matched_count/reminder_lines behavior, safe empty state, py_compile, and 20/20 focused tests |
| 017 | projection_orchestrator_preflight | tester | done | 2026-04-12 | Tester verified orchestrator preflight helper, advisory block structure, ready/matched_count/reminder_lines/caution_level behavior, safe empty state, py_compile, and 24/24 focused tests |
| 018 | projection_orchestrator_mvp | tester | done | 2026-04-12 | Tester verified orchestrator module, stable request/advisory package, advisory path, ready/notes/request behavior, safe empty state, py_compile, and 28/28 focused tests |
| 019 | projection_entrypoint | tester | done | 2026-04-12 | Tester verified entrypoint module, single stable orchestrator interface, stable output structure, safe empty state, py_compile, and 32/32 focused tests |
| 020 | command_projection_wiring | tester | done | 2026-04-12 | 60/60 tests pass (53 focused + 7 AppTest); 5 wiring spot-checks PASS; no forbidden files touched |
| 021 | command_center_stability_fix | tester | done | 2026-04-12 | 70/70 tests pass; 6 stability AppTest scenarios verified; exception guard, session-state, staleness clear all confirmed |
| 022 | data_workbench_mvp | tester | done | 2026-04-12 | 132/132 tests pass; real-data query/compare/stats spot-checks PASS; distribution_by_label not wired (noted gap) |
| 023 | command_parser_enhancement | tester | done | 2026-04-13 | 71/71 parser tests + 40 regression pass; 15/15 spot-checks PASS; stat_request parsed but not yet wired (tracked gap) |
| 024 | advanced_stats_output | tester | done | 2026-04-13 | 151/151 tests pass; invariant 高+中+低=matched verified on real data (2+4+7=13); safety fallbacks clean |
| 025 | projection_final_wiring | reviewer | done | 2026-04-13 | Scoped reviewer pass: final_projection_report command path verified; 28 focused + 122 regression tests pass; merge only Task 025-owned files and exclude unrelated dirty core/workflow changes |
| 026A | predict_readable_summary_and_ai_polish | tester | done | 2026-04-13 | Covers original Task 026 and Task 027; readable Predict/projection summary landed, optional AI polish included, main paths regression-safe |
| 028 | polish_and_guardrails_pack | reviewer | blocked | 2026-04-13 | Review found external-confirmation None-value guardrail gap; tests otherwise pass (30 focused + 108 regression + scripts/check.sh) |
| 032 | freeform_intent_planner_mvp | reviewer | done | 2026-04-13 | 110/110 tests pass; 7/7 spot-checks PASS; reviewer passed with minor finding: F1 — stats steps render empty symbol/field in Command Center table (singular vs plural key mismatch in _render_intent_plan); suggest fix in follow-up |
| 033 | multi_step_tool_router_mvp | reviewer | done | 2026-04-13 | 137/137 tests pass; reviewer finding F1: parser/planner mismatch hides projection result for "看看...明天" inputs (query_data parsed but projection planned, _render_stored_result dispatches on wrong type); suggest fix in follow-up |
| 034 | conversation_result_renderer_mvp | reviewer | blocked | 2026-04-13 | Review blocked: builder handoff missing and fixed answer-card sections not implemented; tests pass but do not cover required card structure |
| 035 | projection_evidence_trace_mvp | tester | done | 2026-04-13 | Evidence trace added for projection/predict; reviewer follow-up fixes landed for memory_feedback gating and safe None handling; focused tests pass |
