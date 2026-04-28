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
- 037 — `ai_intent_parser_fallback_mvp`
- 038 — `projection_v2_three_stage_orchestrator`
- 039 — `primary_20day_analysis_layer`
- 040 — `peer_adjustment_layer`
- 041 — `historical_probability_layer_mvp`
- 042 — `final_decision_aggregator`
- 043 — `projection_rule_preflight`
- 044 — `projection_v2_entrypoint_cutover_and_render_adapter`
- 045 — `projection_review_closed_loop`
- 046 — `preflight_rule_influence_on_final_decision`
- 047 — `native_projection_v2_ui`
- 048 — `historical_replay_training_framework`
- 049 — `enhanced_historical_probability_layer`
- 050 — `projection_v2_full_cutover_cleanup`
- 052 — `projection_narrative_renderer`
- 053 — `primary_bias_diagnosis`
- 054 — `rule_scoring_system`
- 055 — `rule_lifecycle_management`
- 056 — `active_rule_pool_builder`
- 057 — `active_rule_pool_export_and_preflight_bridge`
- 058 — `preflight_active_rule_pool_reader`
- 059 — `active_rule_pool_effectiveness_validation`
- 060 — `active_rule_pool_calibration_report`
- 061 — `active_rule_pool_promotion_policy`
- 062 — `promotion_execution_bridge`
- 063 — `active_rule_pool_drift_monitor`
- 064 — `daily_training_pipeline`
- 065 — `daily_training_summary_and_review_brief`
- 066 — `promotion_adoption_gate_and_production_candidate_handoff`
- 067 — `dashboard_rule_library_and_monitoring_view`
- 068 — `scheduler_and_automation_wrapper`
- 069 — `avgo_1000day_replay_training_and_rule_summary`
- 06Q — `projection_output_three_systems`
- 070 — `dual_price_track_foundation`
- 071 — `exclusion_accuracy_chain`
- 084 — `five_state_collapse_audit_from_db`
- 085 — `five_state_margin_policy_design`
- 086 — `integrate_five_state_margin_policy_into_record_02_output`
- 087 — `surface_five_state_display_state_in_summary`
- 090 — `restore_big_up_contradiction_card_pr_c`
- 092 — `restore_predict_tab_exclusion_reliability_review_pr_e`
- 094 — `wire_exclusion_reliability_review_into_predict_tab`
- 096 — `wire_contradiction_card_ui_into_predict_tab`
- 100 — `fix_replay_target_date_wiring`

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
| 001 | prediction_store | tester | done | 2026-04-23 | Blockers (duplicate-save ordering, unenforced FK, orphan-row risk) fixed by Task 006; E2E loop verified 2026-04-23: prediction_log/outcome_log/review_log all wrote real rows, status machine reached review_generated |
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
| 028 | polish_and_guardrails_pack | tester | done | 2026-04-23 | None-value guardrail fixed in predict_summary.py: _rs_value_missing() helper + _format_rs() + _external_confirmation_missing() now treat None as missing; py_compile passes |
| 032 | freeform_intent_planner_mvp | done | done | 2026-04-23 | F1 收口：_render_intent_plan 同时支持 symbols/symbol 与 fields/field 两套 key；stats 步骤不再显示空值 |
| 033 | multi_step_tool_router_mvp | done | done | 2026-04-23 | F1 收口：_render_stored_result query_data 路径增加 plan.primary_intent==projection 判断，mismatch 时正确渲染推演结果；_render_router_primary 修复 projection error 不显示问题 |
| 034 | conversation_result_renderer_mvp | tester | done | 2026-04-20 | Tester closeout passed: focused Task 034 tests pass (24 passed, 21 AppTest-gated skips); acceptance points covered by renderer/stability tests; see task_034_tester.md |
| 035 | projection_evidence_trace_mvp | tester | done | 2026-04-13 | Evidence trace added for projection/predict; reviewer follow-up fixes landed for memory_feedback gating and safe None handling; focused tests pass |
| 037 | ai_intent_parser_fallback_mvp | builder | in-review | 2026-04-14 | 36 new tests pass; all 7 validation cases covered; safe degradation verified; see task_037_builder.md |
| 038 | projection_v2_three_stage_orchestrator | tester | done | 2026-04-21 | Tester closeout passed: projection v2 fixed schema/order/degradation tests pass (7/7); reviewer P1 regression covered; see task_038_tester.md |
| 039 | primary_20day_analysis_layer | tester | done | 2026-04-21 | Tester closeout passed: primary 20-day fixed schema/degradation and projection v2 Step 1 wiring tests pass (16/16); reviewer P1 regression covered; see task_039_tester.md |
| 040 | peer_adjustment_layer | tester | done | 2026-04-21 | Tester closeout passed: peer adjustment fixed schema/degradation/neutral no-change and projection v2 Step 2 wiring tests pass (16/16); reviewer P1 regression covered; see task_040_tester.md |
| 041 | historical_probability_layer_mvp | tester | done | 2026-04-21 | Tester closeout passed: historical probability fixed schema/degradation/insufficient_sample and projection v2 Step 3 wiring tests pass (14/14); reviewer P1 regression covered; see task_041_tester.md |
| 042 | final_decision_aggregator | tester | done | 2026-04-21 | Tester closeout passed: final decision fixed schema/degradation/full-support/downgrade/missing/neutral and projection v2 Step 4 wiring tests pass (15/15); see task_042_tester.md |
| 043 | projection_rule_preflight | tester | done | 2026-04-21 | Tester closeout passed: Step 0 schema/matched-rules/no-match/missing-source/malformed-source/wiring/F1-F2 regression tests pass (50/50); see task_043_tester.md |
| 044 | projection_v2_entrypoint_cutover_and_render_adapter | tester | done | 2026-04-21 | Tester closeout passed: adapter schema/mapping/degraded-path/caution-level/command-bar-render spot-checks pass (33 adapter + 4 integration + 5 wiring = 42/42); F1 regression covered; 976 regression pass; see task_044_tester.md |
| 045 | projection_review_closed_loop | tester | done | 2026-04-21 | Tester closeout passed: all 3 public functions verified; happy/wrong-direction/snapshot-missing/actual-missing/malformed/rule-candidates/F1-F4 regression tests pass (57/57); see task_045_tester.md |
| 046 | preflight_rule_influence_on_final_decision | tester | done | 2026-04-21 | Tester closeout passed: no-rule/warn/lower-confidence/raise-risk/cap/explicit-effect/direction/045-compat/shape tests pass (24/24); 045 cross-task 81/81; py_compile OK; see task_046_tester.md |
| 047 | native_projection_v2_ui | tester | done | 2026-04-21 | Tester closeout passed: direct Task 047 tests confirm v2 raw priority, compat fallback safety, Step 0-4 visibility, v2 influence/trace fields, and degraded readability (4 renderer + 5 wiring passed; 15 AppTest skipped in current environment); see task_047_tester.md |
| 048 | historical_replay_training_framework | tester | done | 2026-04-21 | Tester closeout passed: single/batch/summarize APIs verified; happy path, insufficient-history, outcome-missing, no-future-leak, partial-failure, empty-range, accuracy, aggregation tests pass (57/57); py_compile OK; see task_048_tester.md |
| 049 | enhanced_historical_probability_layer | tester | done | 2026-04-21 | Tester closeout passed: code_match/window_similarity/code_only/window_only/blended/weak-degradation/no-future-leak/semantic consistency and final_decision + replay compatibility tests pass (13 focused, 106 direct+cross-task); see task_049_tester.md |
| 050 | projection_v2_full_cutover_cleanup | tester | done | 2026-04-21 | Tester closeout passed: focused cutover tests confirm entrypoint v2 source-of-truth, adapter legacy compat shell, command-bar v2-first payload, safe compat fallback, and readable degraded path (5 entrypoint + 32 adapter + 5 wiring + 4 renderer pass; 15 AppTest skipped); see task_050_tester.md |
| 052 | projection_narrative_renderer | tester | done | 2026-04-21 | Tester closeout passed: direct Task 052 checks confirm stable narrative shape, happy/degraded readability, visible preflight influence, and additive entrypoint fallback safety (15 direct tests + 4 related renderer tests); see task_052_tester.md |
| 053 | primary_bias_diagnosis | tester | done | 2026-04-21 | Tester closeout passed: direct Task 053 checks confirm stable report shape, correct direction/wrong-direction semantics, pattern aggregation, non-empty diagnosis outputs, and degraded-path stability (6 focused tests); see task_053_tester.md |
| 054 | rule_scoring_system | tester | done | 2026-04-21 | Tester closeout passed: direct Task 054 checks confirm stable rule_score_report shape, title+category aggregation, correct effective/harmful/neutral semantics, readable empty-state, malformed-candidate resilience, and degraded-path stability (6 focused tests); see task_054_tester.md |
| 055 | rule_lifecycle_management | tester | done | 2026-04-21 | Tester closeout passed: direct Task 055 checks confirm stable lifecycle report shape, consistent lifecycle_state/actions, correct candidate/watchlist/promoted_active/weakened/retired classification, aligned state_counts/grouped lists, and degraded-path resilience (6 focused tests); see task_055_tester.md |
| 056 | active_rule_pool_builder | tester | done | 2026-04-21 | Tester closeout passed: direct Task 056 checks confirm stable active pool report shape, correct include/hold/exclude mapping, aligned pool_decision/rationale, consistent pool_counts/grouped lists, and degraded-path resilience (6 focused tests); see task_056_tester.md |
| 057 | active_rule_pool_export_and_preflight_bridge | tester | done | 2026-04-21 | Tester closeout passed: direct Task 057 checks confirm stable export shape, include-only export behavior, excluded hold/exclude tracking, deterministic bridge rule_id, conservative defaults, and degraded-path resilience (6 focused tests); see task_057_tester.md |
| 058 | preflight_active_rule_pool_reader | tester | done | 2026-04-21 | Tester closeout passed: direct Task 058 checks confirm default compatibility, optional active-pool consumption, stable active_pool_items/active_pool_matches/active_pool_used semantics, post-dedupe active-pool contribution tracking, and safe fallback on missing/empty/malformed bridge sources (35 focused tests); see task_058_tester.md |
| 059 | active_rule_pool_effectiveness_validation | tester | done | 2026-04-21 | Tester closeout passed: direct Task 059 checks confirm stable validation report shape, correct paired alignment by as_of_date+prediction_for_date, accurate delta/improved-worsened statistics, aligned rule_effects helpful/unhelpful ranking, and degraded-path resilience (7 focused tests); see task_059_tester.md |
| 060 | active_rule_pool_calibration_report | tester | done | 2026-04-21 | Tester closeout passed: direct Task 060 checks confirm stable calibration report shape, correct retain/observe/downgrade/recalibrate/remove_candidate decisions, known-param-only recalibration suggestions, unknown-param conservative fallback, aligned decision_counts/grouped outputs, and degraded-path resilience (11 focused tests); see task_060_tester.md |
| 061 | active_rule_pool_promotion_policy | tester | done | 2026-04-21 | Tester closeout passed: direct Task 061 checks confirm stable promotion report shape, correct promote_candidate/keep_active_observe/hold_back/do_not_promote decisions, promotion_confidence consistency, decision_counts↔sublists alignment, and degraded-path resilience (12 focused tests + 10 spot-checks); see task_061_tester.md |
| 062 | promotion_execution_bridge | tester | done | 2026-04-22 | Tester closeout passed: direct Task 062 checks confirm stable bridge shape, correct promote_candidate→bridge/others→held_back split, execution_bridge_rules 6-field format, deterministic rule_id, conservative fallbacks, execution_enabled status-only, and degraded-path resilience (13 focused tests + 11 spot-checks); see task_062_tester.md |
| 063 | active_rule_pool_drift_monitor | tester | done | 2026-04-22 | Tester closeout passed: direct Task 063 checks confirm stable drift report shape, correct unclear-first priority, drift_candidate/stable/improving/unclear classification, followup consistency, status_counts↔sublists alignment, and degraded-path resilience (16 focused tests + 13 spot-checks); see task_063_tester.md |
| 064 | daily_training_pipeline | tester | done | 2026-04-22 | Tester closeout passed: direct Task 064 tests confirm stable daily_training_report shape, correct replay→score→lifecycle→active-pool→export→validation→calibration→promotion→drift ordering, explicit-artifact priority, strict skipped semantics when builders are missing, partial-failure isolation, aligned ok/degraded/failed/skipped states, and no false ready on malformed downstream artifacts (9/9); see task_064_tester.md |
| 065 | daily_training_summary_and_review_brief | tester | done | 2026-04-22 | Tester closeout passed: direct Task 065 tests confirm stable daily_training_brief shape, correct overall_status/step_overview aggregation, promote/drift/risk/next-check extraction, safe malformed headline_metrics fallback, conservative degraded overall_status when step_status is missing, and stable empty-watchlist handling when promotion/drift artifacts are absent (11/11); see task_065_tester.md |
| 066 | promotion_adoption_gate_and_production_candidate_handoff | tester | done | 2026-04-22 | Tester closeout passed: direct Task 066 tests confirm stable promotion_adoption_handoff shape, correct production_candidate / execution-bridge hold / evidence hold / not-ready decisions, confidence consistency with bridge presence, production-only handoff_artifact, and degraded-path resilience for missing promotion_report, empty rules, missing bridge, and malformed rule identity (11/11); see task_066_tester.md |
| 067 | dashboard_rule_library_and_monitoring_view | tester | done | 2026-04-22 | Tester closeout passed: direct Task 067 tests confirm stable rule_dashboard_view shape, correct header/headline cards/core lists, strict export priority for active counts and active rules even when export values are 0/empty, daily-brief risk flag reuse, and degraded-path resilience for missing brief/export/promotion/adoption/drift and all-inputs-missing fallback (11/11); see task_067_tester.md |
| 068 | scheduler_and_automation_wrapper | tester | done | 2026-04-22 | Tester closeout passed: direct Task 068 tests confirmed stable daily_automation_run shape, correct pipeline / summary / dashboard orchestration, explicit artifact priority, partial-failure semantics, zero-safe headline precedence, and degraded-path stability (11/11); see task_068_tester.md |
| 069 | avgo_1000day_replay_training_and_rule_summary | tester | done | 2026-04-22 | Tester closeout passed: direct Task 069 tests confirm stable avgo_1000day_training_report shape, correct ordered (T,T+1) sample construction, conservative malformed replay handling, explicit skipped validation tail semantics without paired inputs, degraded-path resilience, and aligned findings/insights outputs (10/10); see task_069_tester.md |
| 06Q | projection_output_three_systems | builder | in-review | 2026-04-27 | Additive output-architecture refactor: new services/projection_three_systems_renderer.py exposes negative_system / record_02_projection_system / confidence_evaluator from existing v2_raw without changing rules; entrypoint adds projection_three_systems field with degraded fallback; 21 new tests pass + 56 related regression tests pass; see task_06Q_builder.md |
| 070 | dual_price_track_foundation | builder | in-review | 2026-04-27 | Hard-rule extension: introduces parallel Adj Close track alongside raw price track. encoder.py C_code now uses dividend-adjusted return (C_adj) when present, falling back to raw C_move otherwise; O / H / L / V positions unchanged. data_fetcher / feature_builder / services/data_query updated additively. Backwards-compatible with legacy CSVs (no Adj Close → original C_code). 72 / 72 focused tests pass. See tasks/06S_H1_hard_rule_layer_audit.md for full hard-rule analysis. |
| 071 | exclusion_accuracy_chain | builder | in-review | 2026-04-27 | Recovered Task 03 / 3A / 3B / 3C1 / 3C3 / 3C5 / 2E exclusion-accuracy chain (PR-A of the recovered-work split). 11 code files (8 scripts + 2 services + 1 UI), 10 tests, 1 records doc, 21 lightweight logs (option-a — reports + summaries + Task 03 baseline only; bulk *_details.csv excluded). 04A–04E2 logs deferred to PR-B. Standalone `ui/exclusion_reliability_review.py` UI surface — does not modify `ui/predict_tab.py`. Based on main @ 32ce79a (post PR-0 merge). See tasks/071_exclusion_accuracy_chain.md and tasks/06S_recovered_experimental_branch_audit.md. |
| 084 | five_state_collapse_audit_from_db | tester | done | 2026-04-28 | Tester closeout passed: focused Task 084 validation is green (`11/11` focused tests passed, `bash scripts/check.sh` passed). Full 072–084 regression skipped because this current root workspace does not contain the prior Task 072–083 test chain. Local SQLite fixture smoke passed and detected `five_state_top1_collapse`, `final_direction_collapse`, `low_margin_problem`, and `direction_state_mismatch`. No business logic modified. |
| 085 | five_state_margin_policy_design | tester | done | 2026-04-28 | Tester closeout passed: focused Task 085 validation is green (`12/12` focused tests passed, `bash scripts/check.sh` passed) and manual policy sanity check passed. Full 072–085 regression skipped because this current root workspace does not contain the prior Task 072–083 test chain. No business logic modified. |
| 086 | integrate_five_state_margin_policy_into_record_02_output | tester | done | 2026-04-28 | Tester closeout passed: focused Task 086 tests passed (`7/7`), renderer tests passed (`17/17`), and `bash scripts/check.sh` passed. Manual record_02 sanity check passed: original `five_state_top1` stayed `震荡`, `final_direction` stayed `偏多`, and additive margin metadata rendered correctly. Full 072–086 regression skipped because this current root workspace does not contain the prior Task 072–083 test chain. No forbidden business logic modified. |
| 087 | surface_five_state_display_state_in_summary | tester | done | 2026-04-28 | Tester closeout passed: focused Task 087 display-summary tests passed (`12/12`), related margin-output tests passed (`7/7`), renderer tests passed (`17/17`), and `bash scripts/check.sh` passed. Manual display-summary sanity check passed: `five_state_display_summary` surfaces the split context while original `five_state_top1` stayed `震荡` and `final_direction` stayed `偏多`. Full 072–087 regression skipped because this current root workspace does not contain the prior Task 072–083 test chain. No forbidden business logic modified. |
| 090 | restore_big_up_contradiction_card_pr_c | tester | done | 2026-04-28 | Tester closeout passed: `31/31` `tests/test_big_up_contradiction_card.py` cases passed (all §1–§9 base, §14–§19 cache-health, big-down tail integration, and 3 UI cases via monkeypatched fake streamlit). Existing consumer regression `tests/test_exclusion_reliability_review.py` passed (`5/5`). `bash scripts/check.sh` passed; `python3 -m py_compile` clean. Manual UI renderer sanity check passed (3/3 payloads — info / warning / strong_warning — correctly dispatched to `st.info` / `st.warning` / `st.error`, big-down sub-section emitted required Chinese substrings, payloads unmutated, no tracebacks). Protected PR-E file `tests/test_predict_tab_exclusion_reliability_review.py` untouched (stat identical: 1395 B, mtime `Apr 27 13:03`). `.claude/worktrees/` untouched (9 directories intact). Services logic untouched (`git status --porcelain` empty for all guarded service files; only tracked change is `tasks/STATUS.md`). Renderer deliberately NOT wired into `ui/predict_tab.py` (deferred to PR-E). See `tasks/090_restore_big_up_contradiction_card.md`, `.claude/handoffs/task_090_builder.md`, and `.claude/handoffs/task_090_tester.md`. |
| 092 | restore_predict_tab_exclusion_reliability_review_pr_e | tester | done | 2026-04-28 | Tester closeout passed: focused wrapper test `tests/test_predict_tab_exclusion_reliability_review.py` passed (`1/1`); PR-C regression `tests/test_big_up_contradiction_card.py` passed (`31/31`); services regression `tests/test_exclusion_reliability_review.py` passed (`5/5`); UI regression `tests/test_exclusion_reliability_review_ui.py` passed (`2/2`); `bash scripts/check.sh` passed; `python3 -m py_compile` clean. Manual wrapper + adapter sanity check passed (13/13 assertions — wrapper forwarded original `predict_result` and `prediction_date="2026-04-25"` to the builder, returned row passed verbatim to the renderer, zero `st.*` calls on happy path, payload unmutated; adapter direct call preserved `predicted_state` / `forced_excluded_states` / `p_大涨` / `p_大跌` / `five_state_display_state` and set both `prediction_date` and `analysis_date`, returning a fresh dict). `.claude/handoffs/task_089_post_pr_cleanup.md` untouched (stat identical: 2966 B, mtime `Apr 28 10:34`). `.claude/worktrees/` untouched (9 directories intact). Forbidden files untouched (`git status --porcelain --` empty for all guarded paths; only tracked changes are the 3 explicitly-allowed files). Live UI wiring deliberately deferred — `_render_exclusion_reliability_review` is added but not yet invoked from `render_predict_tab` (reserved for PR-F). See `tasks/092_restore_predict_tab_exclusion_reliability_review.md`, `.claude/handoffs/task_092_builder.md`, and `.claude/handoffs/task_092_tester.md`. |
| 094 | wire_exclusion_reliability_review_into_predict_tab | tester | done | 2026-04-28 | Tester closeout passed: live-wiring tests `tests/test_predict_tab_exclusion_reliability_live_wiring.py` passed (`2/2` — invocation count + ordering); PR-E wrapper regression `tests/test_predict_tab_exclusion_reliability_review.py` passed (`1/1`); PR-C regression `tests/test_big_up_contradiction_card.py` passed (`31/31`); services regression `tests/test_exclusion_reliability_review.py` passed (`5/5`); UI regression `tests/test_exclusion_reliability_review_ui.py` passed (`2/2`); predict-summary regression `tests/test_predict_summary.py` passed (`5/5`); `bash scripts/check.sh` passed; `python3 -m py_compile` clean. Total 46/46 pytests passed across 6 invocations. Manual wiring sanity check passed (6/6 assertions — wrapper invoked exactly once with same `predict_result` object, call order `expander:生成 AI 推演总结（可选）` → `wrapper` → `expander:推演原始数据（调试用）`, no traceback, both `predict_result` and `scan_result` unmutated). `.claude/handoffs/task_089_post_pr_cleanup.md` untouched (stat identical: 2966 B, mtime `Apr 28 10:34`). `.claude/worktrees/` untouched (9 directories intact). Services / app / predict / data-pipeline / `ui/exclusion_reliability_review.py` / `ui/big_up_contradiction_card.py` untouched (`git status --porcelain --` empty for all guarded paths; only tracked changes are `ui/predict_tab.py` and `tasks/STATUS.md`). Contradiction-card UI wiring (PR-C `render_contradiction_card`) deliberately deferred — out of scope for PR-F. See `tasks/094_wire_exclusion_reliability_review_into_predict_tab.md`, `.claude/handoffs/task_094_builder.md`, and `.claude/handoffs/task_094_tester.md`. |
| 096 | wire_contradiction_card_ui_into_predict_tab | tester | done | 2026-04-28 | Tester closeout passed: contradiction-card-wiring tests `tests/test_predict_tab_contradiction_card_wiring.py` passed (`2/2` — wrapper plumbing + live wiring); PR-F live wiring regression `tests/test_predict_tab_exclusion_reliability_live_wiring.py` passed (`2/2`); PR-E wrapper regression `tests/test_predict_tab_exclusion_reliability_review.py` passed (`1/1`); PR-C regression `tests/test_big_up_contradiction_card.py` passed (`31/31`); services regression `tests/test_exclusion_reliability_review.py` passed (`5/5`); UI regression `tests/test_exclusion_reliability_review_ui.py` passed (`2/2`); predict-summary regression `tests/test_predict_summary.py` passed (`5/5`); `bash scripts/check.sh` passed; `python3 -m py_compile` clean. Total 48/48 pytests passed across 7 invocations. Manual wiring + plumbing sanity check passed (12/12 assertions — both PR-F and PR-G wrappers invoked exactly once with same `predict_result` object, call order `expander:生成 AI 推演总结（可选）` → `pr_f_wrapper` → `pr_g_wrapper` → `expander:推演原始数据（调试用）`, adapter received original `predict_result` and `prediction_date="2026-04-25"`, builder received adapter row, renderer received builder payload, no direct `st.caption / st.markdown / st.write` on wrapper path, `predict_result` and `scan_result` both unmutated, no traceback). `.claude/handoffs/task_089_post_pr_cleanup.md` untouched (stat identical: 2966 B, mtime `Apr 28 10:34`). `.claude/worktrees/` untouched (9 directories intact). Services / app / predict / data-pipeline / `ui/big_up_contradiction_card.py` / `ui/exclusion_reliability_review.py` untouched (`git status --porcelain --` empty for all guarded paths; only tracked changes are `ui/predict_tab.py` and `tasks/STATUS.md`). See `tasks/096_wire_contradiction_card_ui_into_predict_tab.md`, `.claude/handoffs/task_096_builder.md`, and `.claude/handoffs/task_096_tester.md`. |
| 100 | fix_replay_target_date_wiring | tester | done | 2026-04-29 | Tester closeout passed: target_date wiring fixed across three production sites — `services/projection_orchestrator_v2.py` now forwards `target_date` to the legacy runner (1-line addition), `services/projection_orchestrator.py` filters `coded_df` by `Date <= target_date` when provided (helpers `_build_predict_result` and `_build_momentum_frame` extended with the kwarg), `services/primary_20day_analysis.py` slices the analysis df by `target_date` after load (or filters injected `data=df` before tail). Live behaviour preserved: when `target_date is None` all three sites are bit-identical to pre-fix. Validation: `5/5` new `tests/test_primary_20day_analysis_target_date.py` (NEW), `3/3` new `tests/test_projection_orchestrator_v2_target_date_forwarding.py` (NEW), `57/57` `tests/test_historical_replay_training.py`, `2/2` PR-G wiring, `2/2` PR-F live wiring, `1/1` PR-E wrapper, `31/31` PR-C suite, `5/5` predict_summary; `bash scripts/check.sh` passed; `py_compile` clean. Total 106/106 pytests passed across 8 invocations. 5-case replay variation sanity check confirmed `target_date` is respected: 5 distinct `as_of_date` values produced 5 distinct `pos20` (`96.1, 99.6, 93.3, 95.3, 90.6`), 5 byte-distinct `five_state_projection` vectors, and a non-trivial `five_state_top1` distribution (`小涨` ×4, `震荡` ×1) — pre-fix Task 098D 1005-case run had been 1 distinct value across all 1005 days for each of these. Latest-day output (`2026-04-27`, the last trading day in the local data file) reproduces pre-fix values bit-for-bit (`pos20 = 90.6`, `samples = 42`, projection `{0, 0.405, 0.4565, 0.1237, 0.0148}`), confirming live UI behaviour preserved. `.claude/handoffs/task_089_post_pr_cleanup.md` untouched (stat identical: 2966 B, mtime `Apr 28 10:34`). `.claude/worktrees/` untouched (9 directories intact). Task 098D temporary replay-driver files (`scripts/run_1005_three_system_replay.py`, `scripts/save_projection_records_smoke.py`, `services/market_data_store.py`, `services/projection_record_store.py`, `services/replay_record_wiring.py`, `services/three_system_replay_audit.py`) remain untracked and unmodified by Task 100. Modified tracked files exactly the three production sites listed plus `tasks/STATUS.md`. See `.claude/handoffs/task_100_tester.md` for full test detail. |
