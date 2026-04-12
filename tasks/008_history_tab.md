# Task 008 — history_tab

## Goal

Add a History tab that lets users inspect past predictions, captured outcomes, and generated reviews from the research loop.

## Scope

**Allowed:**

* `ui/history_tab.py`
* `app.py` (only minimal tab wiring)
* `services/prediction_store.py` (only if tiny read-only helper methods are strictly needed)
* `tests/test_history_tab.py`
* `tasks/STATUS.md`
* `.claude/handoffs/task_008_builder.md`
* `.claude/handoffs/task_008_reviewer.md`
* `.claude/handoffs/task_008_tester.md`

**Forbidden:**

* `services/outcome_capture.py`
* `services/review_agent.py`
* `research.py`
* `scanner.py`
* `predict.py`

## Requirements

1. Add a new History tab to the app
2. Show recent prediction records in a readable list/table
3. Each row should include at least:

   * prediction_for_date
   * final_bias
   * final_confidence
   * status
   * direction_correct (if outcome exists)
4. Allow viewing a single record in more detail:

   * prediction JSON / summary
   * outcome fields
   * review fields
5. Keep it read-only

   * no edit / delete actions
6. Prefer minimal app.py changes

   * only add tab wiring if needed
7. Reuse existing prediction_store reads where possible

   * only add tiny read helpers if the current store API is insufficient

## Done when

* History tab exists and renders
* Recent predictions are visible
* A user can inspect prediction/outcome/review details for one record
* No unrelated business logic changes are introduced
* Basic validation/tests pass

## Status

done

## History

| date       | agent   | event                              |
| ---------- | ------- | ---------------------------------- |
| 2026-04-12 | planner | task created after Task 007 passed |
| 2026-04-12 | builder | added read-only History tab and helper tests |
| 2026-04-12 | reviewer | passed read-only implementation; low render-test gap noted |
| 2026-04-12 | tester | verified render, recent rows, details, and validation; status moved to done |
