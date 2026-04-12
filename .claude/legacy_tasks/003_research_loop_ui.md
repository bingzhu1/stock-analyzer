# Legacy Task 003 - Research Loop UI

> Legacy numbering note: this file was created before the final task map was stabilized.
> The canonical Research Loop UI task is now `tasks/004_research_loop_ui.md`.
> The canonical Task 003 is `tasks/003_review_agent.md`.
> Keep this file only as historical context; new agents should read `tasks/STATUS.md` and the matching file under `tasks/`.

## Goal
Wire prediction_store, outcome_capture, and review_agent into the Predict tab UI.

## Scope
Allowed:
- ui/predict_tab.py

Forbidden:
- app.py
- services/*
- research.py
- scanner.py

## Requirements
- Step 1: Save Prediction button — calls save_prediction(), stores pid in session_state
- Step 2: Capture Outcome button — disabled until Step 1 done; calls capture_outcome()
- Step 3: Generate Review button — disabled until Step 2 done; calls generate_review()
- Allow "Save New Version" when already saved; warn user it resets outcome/review for session
- Show result badges (CORRECT / WRONG / NEUTRAL, colored error_category) inline
- No changes to app.py

## Done when
- All 3 steps render and function correctly in manual walkthrough
- Button preconditions enforced (no save → no capture; no capture → no review)
- session_state keys: saved_prediction_id, saved_prediction_date

## Note
This task was implemented together with Task 001/002 in the same session.
Scope violation flagged by tester; this file retroactively documents the intent.
