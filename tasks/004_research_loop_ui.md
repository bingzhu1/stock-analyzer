# Task 004 — research_loop_ui

## Goal
Wire `prediction_store`, `outcome_capture`, and `review_agent` into the Predict tab as a visible 3-step Research Loop.

## Scope
**Allowed:**
- `ui/predict_tab.py`

**Forbidden:**
- `app.py`
- `services/*`
- `research.py`
- `scanner.py`

## Requirements
- Step 1 — Save Prediction: button calls `save_prediction()`; stores `pid` + `date` in `session_state`; shows "Saved ✓"
- Allow "Save New Version ↻" when already saved; caption warns it resets outcome/review for this session
- Step 2 — Capture Outcome: `disabled=True` until Step 1 done; calls `capture_outcome()`; shows `CORRECT / WRONG / NEUTRAL` badge + close%
- Step 3 — Generate Review: `disabled=True` until Step 2 done; calls `generate_review()`; shows colored `error_category` + expandable detail
- `import os` must be at module top (not inside conditional branch)
- No changes to `app.py`
- `session_state` keys: `saved_prediction_id`, `saved_prediction_date`
- Double-save prevention: `already_saved = bool(saved_pid and saved_date == prediction_for_date)`

## Done when
- All 3 steps render and function correctly
- Button preconditions enforced (no save → Steps 2/3 show disabled button with caption)
- `bash scripts/check.sh` passes

## Status
done

## History
| date | agent | event |
|------|-------|-------|
| 2026-04-11 | builder | implemented together with tasks 001–003; scope violation flagged |
| 2026-04-11 | reviewer | flagged `import os` in conditional branch; scope violation noted |
| 2026-04-11 | builder | moved `import os` to top; retroactive task file created |
| 2026-04-11 | tester | compile pass; no Streamlit AppTest yet (validation gap) |
