# 当前状态

## Current phase
MVP Phase 1: research loop — implemented; task/status hygiene in progress

## Task source of truth
- Official task directory: `tasks/`
- Do not create new files under `.claude/tasks/`
- Historical duplicate task files are archived under `.claude/legacy_tasks/`

## Current task status
- `prediction_store` (task 001) — **blocked**; implemented, but reviewer follow-up flagged duplicate-save ordering, FK/orphan-row risk, and unscoped working-tree files
- `outcome_capture` (task 002) — **done**; yfinance fetch, direction logic, 18 tests
- `review_agent` (task 003) — **done**; LLM + rule-based fallback, 22 tests
- `research_loop_ui` (task 004) — **done**; 3-step Research Loop in Predict tab
- `task_system_cleanup` (task 005) — **done**; duplicate task directory archived and follow-up cleanup verified
- `fix_task001_blockers` (task 006) — **in-progress**; active follow-up to resolve task 001 reviewer blockers

## Done (prior rounds)
- 15-day OHLCV analysis
- Relative strength module
- Pattern scan / matcher / encoder (hard-rule layer — do not modify)

## Do not touch this round
- Major refactor of `app.py`
- APScheduler / automation
- Error memory (cross-prediction learning)
- History tab (separate task, not yet filed)

## Recommended next tasks
1. Task 006: Finish task 001 review blockers — duplicate-save ordering, FK/orphan-row safety, and scoped working-tree hygiene should be resolved before treating persistence as merge-ready.
2. Task 007: Streamlit AppTest for Research Loop UI — the 3-step Predict tab flow needs automated coverage before more UI features build on it.
3. Task 008: History tab — list past predictions, outcomes, and reviews so the completed loop becomes inspectable by users.

## Later candidates
- Task 009: `scenario_match` wiring (scan → outcome correlation)
- Triage: `test_executor_replies_to_unsupported_without_analysis` pre-existing failure

## Biggest tech debt
- `app.py` too large — refactor deferred
- Pre-existing test failure in `test_control_path.py` (unrelated to this round)
