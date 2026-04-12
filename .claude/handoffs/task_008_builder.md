# Builder Handoff - Task 008: history_tab

## Status
PASS

## Date
2026-04-12

## What was done
- Added `ui/history_tab.py`.
- Wired a new `History` tab into `app.py` with minimal import/tab/render changes.
- Reused existing `prediction_store` read APIs: `list_predictions`, `get_prediction`, `get_outcome_for_prediction`, and `get_review_for_prediction`.
- Added a read-only recent predictions table with `prediction_for_date`, `final_bias`, `final_confidence`, `status`, `direction_correct`, close change, and id.
- Added a read-only detail selector for one prediction, showing prediction summary/JSON, outcome fields, and review fields.
- Added `tests/test_history_tab.py` for display helper behavior.
- Did not add store helpers; existing read APIs were enough.

## Validation
- `python -m py_compile ui\history_tab.py tests\test_history_tab.py app.py` - PASS.
- `python -m unittest discover -s tests -p "test_history_tab.py" -v` - PASS with system Python, 5 skipped because Streamlit/pandas are not installed.
- `& 'D:\anaconda\python.exe' -m unittest discover -s tests -p "test_history_tab.py" -v` - PASS, 5/5.
- `& 'D:\Git\bin\bash.exe' scripts/check.sh` - PASS.

## Required actions for next agent
- Review that `app.py` changes are only tab wiring.
- Review that History remains read-only and uses existing store reads.
- If accepted, move Task 008 to `in-test`.

## Status update
- `tasks/STATUS.md` updated to: `in-review`
