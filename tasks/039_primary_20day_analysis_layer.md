# Task 039 — primary_20day_analysis_layer

## Goal
Extract the AVGO recent-20-day primary analysis into an independent, stable, testable layer that becomes projection v2 Step 1.

## Scope
- Add `services/primary_20day_analysis.py`.
- Return a fixed schema with direction, confidence, position, stage, volume state, summary, basis, warnings, and features.
- Analyze only the target symbol's own recent data.
- Support safe degradation for empty data, insufficient days, and missing key fields.
- Minimally wire projection v2 Step 1 to the new primary analysis layer.

## Out of Scope
- Peer adjustment changes.
- Historical probability algorithm changes.
- Scanner / predict core rewrites.
- UI changes.
- Legacy projection entrypoint wiring.

## Done When
- Primary 20-day analysis has an independent module.
- Output shape is stable.
- Safe degradation is covered.
- Projection v2 Step 1 consumes the new layer.
- Focused tests pass.
- Builder handoff is written and `tasks/STATUS.md` is updated to `in-review`.
