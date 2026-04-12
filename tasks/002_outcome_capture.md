# Task 002 — outcome_capture

## Goal
Fetch the actual AVGO market result for a saved prediction's `prediction_for_date` and write to `outcome_log`.

## Scope
**Allowed:**
- `services/outcome_capture.py`
- `tests/test_outcome_capture.py`

**Forbidden:**
- `app.py`
- `ui/*`
- `research.py`
- `scanner.py`

## Requirements
- Entry point: `capture_outcome(prediction_id) -> dict`
- Idempotent — return existing outcome if already captured
- Fetch OHLCV via `yfinance.Ticker("AVGO").history(...)` with 10-day window for reliable `prev_close`
- Compute `actual_open_change`, `actual_close_change` as fractions (not pct)
- Compute `direction_correct`: `1` (correct) / `0` (wrong) / `None` (neutral bias or flat move < 0.1%)
- `actual_prev_close = None` (SQL NULL) when no prior trading day exists — never `0.0`
- Call `update_prediction_status(prediction_id, "outcome_captured")` after save
- Raise `ValueError` on: prediction not found, yfinance returns no data, non-trading day

## Done when
- `capture_outcome()` writes a row to `outcome_log`
- Direction logic handles bullish/bearish/neutral and flat-move edge cases
- `tests/test_outcome_capture.py` passes with mocked yfinance (no network)
- `bash scripts/check.sh` passes

## Status
done

## History
| date | agent | event |
|------|-------|-------|
| 2026-04-11 | builder | implemented; yfinance mocked in tests; 18 tests pass |
| 2026-04-11 | reviewer | flagged `0.0` vs NULL for `actual_prev_close` |
| 2026-04-11 | builder | fixed to pass `None` directly |
| 2026-04-11 | tester | 18/18 pass |
