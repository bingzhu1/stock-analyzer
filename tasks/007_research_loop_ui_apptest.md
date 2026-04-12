# Task 007 — research_loop_ui_apptest

## Goal

Add automated Streamlit AppTest coverage for the 3-step Research Loop in the Predict tab so the main user path is protected before adding more UI features.

## Scope

**Allowed:**

* `tests/test_research_loop_ui_apptest.py`
* `ui/predict_tab.py` (only if tiny testability adjustments are strictly necessary)
* `tasks/STATUS.md`
* `.claude/handoffs/task_007_builder.md`
* `.claude/handoffs/task_007_reviewer.md`
* `.claude/handoffs/task_007_tester.md`

**Forbidden:**

* `app.py`
* `services/*`
* `research.py`
* `scanner.py`
* `predict.py`

## Requirements

1. Add a Streamlit AppTest for the Predict tab Research Loop
2. Cover the main 3-step flow:

   * Save Prediction
   * Capture Outcome
   * Generate Review
3. Verify button preconditions:

   * before save: outcome/review actions not available or disabled
   * after save: capture becomes available
   * after outcome: review becomes available
4. Verify saved-state behavior:

   * saved_prediction_id / saved_prediction_date handling
   * "Save New Version" path when already saved
5. Keep scope tight

   * prefer tests only
   * only make tiny UI adjustments if required for testability

## Done when

* `tests/test_research_loop_ui_apptest.py` exists
* main Research Loop path has automated coverage
* test passes locally
* no unrelated UI/business logic changes are introduced

## Status

done

## History

| date       | agent   | event                              |
| ---------- | ------- | ---------------------------------- |
| 2026-04-12 | planner | task created after Task 006 passed |
| 2026-04-12 | builder | added Streamlit AppTest coverage for Research Loop UI |
| 2026-04-12 | reviewer | passed AppTest coverage; optional stronger reset-state test suggested |
| 2026-04-12 | tester | verified AppTest runs and covers preconditions/main flow; status moved to done |
