# Task 010 — task_naming_and_scenario_test_cleanup

## Goal

Clean up the Task 009 naming inconsistency and add a small amount of permanent test coverage for scenario-related display/edge cases.

## Scope

**Allowed:**

* `tasks/009_scenario_matching_wiring.md`
* `tasks/STATUS.md`
* `.claude/PROJECT_STATUS.md`
* `.claude/handoffs/README.md`
* `tests/test_review_agent.py`
* `tests/test_history_tab.py`
* `.claude/handoffs/task_010_builder.md`
* `.claude/handoffs/task_010_reviewer.md`
* `.claude/handoffs/task_010_tester.md`

**Forbidden:**

* `app.py`
* `services/*`
* `ui/*`
* `research.py`
* `scanner.py`
* `predict.py`

## Requirements

1. Resolve Task 009 naming inconsistency

   * choose one canonical name
   * update references in status/docs/handoffs as needed
   * do not leave two conflicting active names

2. Add permanent scenario-related test coverage

   * review path: scenario summary display remains readable
   * history path: scenario display remains readable
   * edge case: empty `{}` historical_match_summary behavior is explicitly tested

3. Keep this task tiny

   * no new product features
   * no business logic expansion

## Done when

* Task 009 has one clear canonical file name everywhere
* scenario-related test gaps identified by reviewer/tester are covered
* related tests pass
* no forbidden files are touched

## Status

todo

## History

| date       | agent   | event                              |
| ---------- | ------- | ---------------------------------- |
| 2026-04-12 | planner | task created after Task 009 passed |
