# Legacy Task 001 - prediction store

> Legacy warning: this file is archived historical context only.
> It is not an active canonical task.
> The canonical Task 001 is `tasks/001_prediction_store.md`.
> New agents should read `tasks/STATUS.md` and the matching file under `tasks/`.

## Goal
Add SQLite-backed prediction persistence.

## Scope
Allowed:
- services/prediction_store.py
- tests/test_prediction_store.py
- requirements.txt

Forbidden:
- app.py
- ui/*
- research.py

## Requirements
- create prediction_log / outcome_log / review_log
- support save/get/list
- keep changes minimal

## Done when
- DB schema exists
- basic CRUD works
- validation commands pass
