# Task 003 — review_agent

## Goal
Generate a structured post-close review explaining WHY a prediction succeeded or failed, using LLM with rule-based fallback.

## Scope
**Allowed:**
- `services/review_agent.py`
- `tests/test_review_agent.py`
- `requirements.txt` (anthropic dependency)

**Forbidden:**
- `app.py`
- `ui/*`
- `research.py`
- `scanner.py`

## Requirements
- Entry point: `generate_review(prediction_id) -> dict`
- Idempotent — return existing review if already generated
- Require `outcome_log` entry to exist first; raise `ValueError` otherwise
- LLM path: call `claude-haiku-4-5-20251001` via Anthropic API; parse JSON from response
- Output schema (pydantic if available): `error_category`, `root_cause`, `confidence_note`, `watch_for_next_time`
- Valid `error_category` values: `correct`, `wrong_direction`, `right_direction_wrong_magnitude`, `false_confidence`, `insufficient_data`
- Strip markdown code fences from LLM output before JSON parse
- Rule-based fallback when: `ANTHROPIC_API_KEY` absent, LLM call fails, or output invalid
- LLM prompt must use `prediction_for_date` (not `target_date`) — template placeholder and dict key must match
- Call `update_prediction_status(prediction_id, "review_generated")` via `save_review()`
- Persist `review_json` (full structured dict as JSON string) alongside flat columns

## Done when
- `generate_review()` persists a review row and advances status
- Rule-based fallback produces valid output for all 3 `direction_correct` values
- `tests/test_review_agent.py` passes: prompt date check, extract_json fences, fallback branches, idempotency
- `bash scripts/check.sh` passes

## Status
done

## History
| date | agent | event |
|------|-------|-------|
| 2026-04-11 | builder | implemented with LLM + fallback; pydantic optional dependency |
| 2026-04-11 | reviewer | found `target_date` naming trap in prompt template |
| 2026-04-12 | builder | fixed template placeholder + dict key; 22 tests added |
| 2026-04-12 | tester | 22/22 pass |
