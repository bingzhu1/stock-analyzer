# Builder Handoff - Task 005: task_system_cleanup

## Status
PASS

## Date
2026-04-12

## What was done
- Moved duplicate legacy task files from `.claude/tasks/` to `.claude/legacy_tasks/`.
- Documented `tasks/` as the only official task source of truth.
- Updated status/project/handoff docs to say future agents must not create `.claude/tasks/`.
- Added task 005 as the formal cleanup task and moved it to `in-review`.
- Follow-up: aligned Task 005 status between `tasks/STATUS.md` and `tasks/005_task_system_cleanup.md`.
- Follow-up: aligned Task 001 status across `tasks/STATUS.md`, `.claude/PROJECT_STATUS.md`, and `tasks/001_prediction_store.md`.
- Follow-up: kept Task 006 as active, completed its mapping, and aligned its status to `in-progress`.
- Follow-up: added legacy warning banners to archived task 001 and task 002.
- Follow-up: removed `.claude/settings.local.json` from the Task 005 diff because it is outside scope.

## Validation
- Confirmed `.claude/tasks/` no longer exists.
- Confirmed `tasks/` contains the active task files.
- Searched docs for stale `.claude/tasks/` source-of-truth wording.
- Confirmed Task 005 and Task 001 status wording is aligned across the requested docs.
- Confirmed no active empty task file remains for Task 006.

## Required actions for next agent
- Review the follow-up cleanup items in `task_005_reviewer.md` and `task_005_tester.md`.
- If accepted, move Task 005 to `in-test` or `done` according to the normal handoff flow.

## Status update
- `tasks/STATUS.md` updated to: `in-review`
