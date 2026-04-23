# Task 001 — prediction_store

## Goal
Add SQLite-backed persistence for predictions, outcomes, and reviews to support the closed-loop research workflow.

## Scope
**Allowed:**
- `services/prediction_store.py`
- `tests/test_prediction_store.py`
- `requirements.txt`

**Forbidden:**
- `app.py`
- `ui/*`
- `research.py`
- `scanner.py`

## Requirements
- Create 3 tables: `prediction_log`, `outcome_log`, `review_log`
- `prediction_log`: fields `analysis_date`, `prediction_for_date`, `status`, `scan_result_json`, `research_result_json`, `predict_result_json`
- `outcome_log`: fields `prediction_for_date`, `actual_open/high/low/close/prev_close`, `direction_correct`, `scenario_match` (nullable, reserved)
- `review_log`: fields `error_category`, `root_cause`, `confidence_note`, `watch_for_next_time`, `review_json`, `raw_llm_output`
- `status` state machine: `saved → outcome_captured → review_generated` — forward-only, idempotent
- Add query indexes: `(symbol, prediction_for_date)`, `outcome.prediction_id`, `review.prediction_id`
- Support: `save_prediction`, `get_prediction`, `get_prediction_by_date`, `list_predictions`, `save_outcome`, `get_outcome_for_prediction`, `save_review`, `get_review_for_prediction`, `update_prediction_status`
- Multiple saves for same `(symbol, prediction_for_date)` are allowed; latest by `created_at DESC`

## Done when
- DB schema exists with all 3 tables and indexes
- All CRUD functions implemented and callable
- `update_prediction_status` is idempotent (tested)
- `tests/test_prediction_store.py` passes with isolated temp DB per test
- `bash scripts/check.sh` passes

## Status
blocked

## History
| date | agent | event |
|------|-------|-------|
| 2026-04-11 | builder | implemented; 17 tests pass |
| 2026-04-11 | reviewer | found `target_date` naming trap + `0.0` vs NULL issue |
| 2026-04-11 | builder | applied fixes in follow-up |
| 2026-04-11 | tester | 17/17 pass; validation gaps documented in handoff |
| 2026-04-12 | reviewer | blocked follow-up on duplicate-save ordering, FK/orphan-row safety, and unscoped working-tree files |
