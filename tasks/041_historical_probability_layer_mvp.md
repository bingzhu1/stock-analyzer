# Task 041 — historical_probability_layer_mvp

## Goal
Promote historical sample probability into an independent, stable, testable projection v2 Step 3 layer.

## Scope
- Add `services/historical_probability.py`.
- Return a fixed schema with sample count, sample quality, probability fields, historical bias, impact, summary, basis, warnings, and source summary.
- Reuse existing `historical_match_summary` fields from the scanner / match pipeline.
- Safely degrade when historical summary is missing, sample count is insufficient, or primary analysis is unavailable.
- Minimally wire projection v2 Step 3 to the new historical probability layer.

## Out of Scope
- Complex ML prediction.
- Large historical similarity rewrites.
- UI changes.
- Legacy projection entrypoint wiring.
- Matcher / scanner / predict core rewrites.
- Long-term memory / rule preflight changes.
- Final decision weighting changes.

## Done When
- Historical probability has an independent module.
- Output shape is stable.
- Missing / insufficient / mixed semantics are explicit.
- `historical_bias` and `impact` are always explicit.
- Projection v2 Step 3 consumes the new layer.
- Focused tests pass.
- Builder handoff is written and `tasks/STATUS.md` is updated to `in-review`.
