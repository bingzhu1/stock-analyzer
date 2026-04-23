# Task 005 — task_system_cleanup

## Goal
Remove duplicate task sources and document a single long-term workflow for multi-agent task collaboration.

## Scope
**Allowed:**
- `tasks/*`
- `.claude/CLAUDE.md`
- `.claude/PROJECT_STATUS.md`
- `.claude/CHECKLIST.md`
- `.claude/handoffs/*`
- `.claude/legacy_tasks/*`

**Forbidden:**
- `app.py`
- `services/*`
- `ui/*`
- `research.py`
- `scanner.py`
- `predict.py`
- tests and business logic files

## Requirements
- Official task directory is `tasks/` only.
- Do not create new files under `.claude/tasks/`.
- Move or archive legacy duplicate task files from `.claude/tasks/`.
- Document current completed/in-progress task status.
- Recommend the next three tasks in priority order.

## Done when
- `.claude/tasks/` is no longer an active task directory.
- `tasks/STATUS.md`, `.claude/PROJECT_STATUS.md`, and `.claude/handoffs/README.md` agree on the source of truth.
- A builder handoff exists for this cleanup round.

## Status
done

## History
| date | agent | event |
|------|-------|-------|
| 2026-04-12 | builder | archived `.claude/tasks/` to `.claude/legacy_tasks/`; documented `tasks/` as sole official task directory |
| 2026-04-12 | reviewer | requested status alignment, legacy banners, task 006 cleanup, and settings diff handling |
| 2026-04-12 | builder | aligned Task 005 follow-up docs; status returned to in-review |
| 2026-04-12 | reviewer | follow-up passed; status moved to in-test |
| 2026-04-12 | tester | follow-up verified; status moved to done |
