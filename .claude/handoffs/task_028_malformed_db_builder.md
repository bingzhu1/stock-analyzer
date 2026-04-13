# Malformed Prediction DB Builder Handoff

## context scanned
- Runtime error path: `app.py -> render_history_tab() -> list_predictions(limit=100) -> services/prediction_store.py`
- `services/prediction_store.py`
- `ui/history_tab.py`
- `tests/test_prediction_store.py`
- `tests/test_history_tab.py`

## changed files
- `services/prediction_store.py`
- `ui/history_tab.py`
- `tests/test_prediction_store.py`
- `tests/test_history_tab.py`
- `.claude/handoffs/task_028_malformed_db_builder.md`

## implementation
- Added `PredictionStoreCorruptionError` for malformed/corrupt sqlite history DB reads.
- Converted sqlite errors containing `database disk image is malformed` or `file is not a database` into the controlled history-store error.
- Wrapped history list rendering so a corrupt DB shows a readable warning instead of crashing the whole page.
- Added a conservative recovery note: the app does not overwrite the old DB automatically; users should back up `avgo_agent.db` before deleting it to let the app rebuild an empty history DB.
- Added minimal regression tests for controlled store error handling and History tab graceful degradation.

## validation
- `D:\anaconda\python.exe -m py_compile services\prediction_store.py ui\history_tab.py tests\test_prediction_store.py tests\test_history_tab.py` passed.
- `D:\anaconda\python.exe -m unittest tests.test_prediction_store tests.test_history_tab -v` passed, 31 tests.
- `D:\Git\bin\bash.exe scripts/check.sh` passed.

## remaining risks
- Existing corrupt history rows are not recovered automatically.
- Auto-rebuild is intentionally not performed to avoid deleting user data without explicit action.
- Write paths such as saving a new prediction may still fail if `avgo_agent.db` remains corrupt; this patch only prevents the History tab read path from taking down the page.
