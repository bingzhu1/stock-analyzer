# Builder Handoff - Task 009: scenario_match_wiring

## Status
PASS

## Date
2026-04-12

## What was done
- Defined `scenario_match` as compact JSON sourced from `prediction_log.scan_result_json.historical_match_summary`.
- `capture_outcome()` now stores scenario context when saved scan data includes `historical_match_summary`.
- Existing missing-scenario behavior remains backward compatible: no scan summary means `scenario_match = NULL`.
- `list_predictions()` now includes `outcome_log.scenario_match` so History can surface scenario context.
- Review prompts now include a readable scenario summary line.
- History table now includes a compact scenario summary column.
- Added/updated focused tests for scenario persistence and missing-scenario fallback.

## Scenario format
Stored as JSON text in `outcome_log.scenario_match`:

```json
{
  "source": "scan_result.historical_match_summary",
  "exact_match_count": 3,
  "near_match_count": 2,
  "match_sample_size": 5,
  "top_context_score": 87.5,
  "dominant_historical_outcome": "bullish",
  "scan_bias": "bullish",
  "scan_confidence": "high"
}
```

## Validation
- `python -m py_compile services\prediction_store.py services\outcome_capture.py services\review_agent.py ui\history_tab.py tests\test_prediction_store.py tests\test_outcome_capture.py` - PASS.
- `python -m unittest discover -s tests -p "test_prediction_store.py" -v` - PASS, 21/21.
- `python -m unittest discover -s tests -p "test_outcome_capture.py" -v` - FAIL with system Python because `pandas` is not installed.
- `& 'D:\Git\bin\bash.exe' scripts/check.sh` - PASS.
- `& 'D:\anaconda\python.exe' -m unittest tests.test_prediction_store tests.test_outcome_capture tests.test_review_agent tests.test_history_tab -v` - FAIL in sandbox because temp SQLite directories could not be created.
- Same Anaconda command after escalation - PASS, 67/67.

## Notes
- Requested task path was `tasks/009_scenario_match_wiring.md`, but the actual task file is `tasks/009_scenario_matching_wiring.md`.
- `.claude/handoffs/task_002_builder.md` and `.claude/handoffs/task_003_builder.md` are missing; implementation used canonical task docs plus current service code.

## Required actions for next agent
- Review the scenario JSON contract and whether the chosen fields are sufficient for downstream analysis.
- Confirm that review/history use the scenario field without changing write behavior outside outcome capture.
- If accepted, move Task 009 to `in-test`.

## Status update
- `tasks/STATUS.md` updated to: `in-review`
