# Task 009 — scenario_match_wiring

## Goal

Wire scan/match context into stored outcomes and reviews so predictions can be analyzed by scenario, not only by direction correctness.

## Scope

**Allowed:**

* `services/prediction_store.py`
* `services/outcome_capture.py`
* `services/review_agent.py` (only if tiny read-only plumbing is needed)
* `ui/history_tab.py` (only if tiny display support is needed)
* `tests/test_prediction_store.py`
* `tests/test_outcome_capture.py`
* `tasks/STATUS.md`
* `.claude/handoffs/task_009_builder.md`
* `.claude/handoffs/task_009_reviewer.md`
* `.claude/handoffs/task_009_tester.md`

**Forbidden:**

* `app.py`
* `research.py`
* `scanner.py`
* `predict.py`

## Requirements

1. Make `scenario_match` meaningful

   * stop treating it as reserved-only
   * define what value is stored and where it comes from

2. Persist scenario context with outcomes

   * when capturing outcome, store scenario-related information if available
   * avoid breaking existing flow when scenario info is missing

3. Make history/review usable with scenario data

   * ensure stored records can surface scenario information later
   * tiny display additions are allowed only if necessary

4. Keep backward compatibility

   * existing rows without scenario data must still work
   * existing tests must keep passing unless intentionally updated

5. Add/extend tests

   * cover scenario persistence behavior
   * cover missing-scenario fallback behavior

## Done when

* `scenario_match` is actually populated in supported flows
* outcome/review/history remain readable for rows with and without scenario info
* related tests pass
* no unrelated business logic changes are introduced

## Status

done

## History

| date       | agent   | event                              |
| ---------- | ------- | ---------------------------------- |
| 2026-04-12 | planner | task created after Task 008 passed |
| 2026-04-12 | builder | wired scan historical match summary into outcome scenario_match, review prompt, and History display |
| 2026-04-12 | tester | verified scenario persistence, missing-scenario fallback, review/history compatibility, and focused regressions |
