# Task 006 — fix_task001_blockers

## Goal

Resolve the remaining reviewer blockers on task 001 so prediction persistence can be treated as merge-ready and used safely by later UI/history features.

## Scope

**Allowed:**

* `services/prediction_store.py`
* `tests/test_prediction_store.py`
* `tasks/STATUS.md`
* `.claude/handoffs/task_006_builder.md`
* `.claude/handoffs/task_006_reviewer.md`
* `.claude/handoffs/task_006_tester.md`

**Forbidden:**

* `app.py`
* `ui/*`
* `services/outcome_capture.py`
* `services/review_agent.py`
* `research.py`
* `scanner.py`
* `predict.py`

## Requirements

1. Fix duplicate-save ordering risk

   * `get_prediction_by_date()` must return a deterministic latest row even if two saves land in the same second
   * do not rely only on second-level `created_at`

2. Improve FK / orphan-row safety

   * ensure `outcome_log.prediction_id` and `review_log.prediction_id` are meaningfully protected
   * at minimum, enforce foreign keys correctly in SQLite connections
   * reviewer/tester should be able to verify the intended behavior

3. Keep status machine behavior intact

   * `update_prediction_status()` must remain forward-only and idempotent

4. Tighten validation

   * extend `tests/test_prediction_store.py` to cover:

     * deterministic latest-row selection
     * foreign-key behavior / orphan-row prevention expectation
     * no regression in existing CRUD + status machine behavior

5. Do not expand scope

   * this task is only for task 001 blockers
   * no UI or app wiring changes

## Done when

* `get_prediction_by_date()` has deterministic latest-row behavior
* FK/orphan-row safety is explicitly enforced or clearly guarded in code
* `tests/test_prediction_store.py` passes with new coverage
* `bash scripts/check.sh` passes
* builder writes `.claude/handoffs/task_006_builder.md`
* reviewer and tester can evaluate this task without needing unrelated context

## Status

done

## History

| date       | agent   | event                                        |
| ---------- | ------- | -------------------------------------------- |
| 2026-04-12 | planner | task created from task 001 reviewer blockers |
| 2026-04-12 | builder | fixed duplicate-save ordering and FK/orphan-row safety; 60 focused regressions pass |
| 2026-04-12 | reviewer | passed implementation; low test-hardening suggestions documented |
| 2026-04-12 | tester | verified implementation and focused regressions; status moved to done |
