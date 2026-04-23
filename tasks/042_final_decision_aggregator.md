# Task 042 — final_decision_aggregator

## Goal
Promote projection v2 final decision aggregation into an independent, stable, testable Step 4 layer.

## Scope
- Add `services/final_decision.py`.
- Return a fixed schema with final direction, final confidence, risk level, summary, decision factors, warnings, layer contributions, constraint explanation, and source snapshot.
- Treat `primary_analysis` as the main judgment source.
- Treat `peer_adjustment` as the confidence / risk correction layer.
- Treat `historical_probability` as the support / caution / missing constraint layer.
- Treat `preflight` as a non-blocking reminder layer.
- Safely degrade when primary analysis is unavailable.
- Minimally wire projection v2 Step 4 to the new final decision layer.

## Out of Scope
- UI changes.
- Legacy projection entrypoint wiring.
- Scanner / predict / matcher core rewrites.
- Complex ML or weighting systems.
- Long-term memory / rule preflight rewrites.
- New historical probability algorithms.
- New peer scoring models.

## Done When
- Final decision has an independent module.
- Output shape is stable.
- Primary / peer / historical / preflight contributions are explicit.
- Degraded paths are stable.
- `why_not_more_bullish_or_bearish` exists and explains constraints.
- Projection v2 Step 4 consumes the new layer.
- Focused tests pass.
- Builder handoff is written and `tasks/STATUS.md` is updated to `in-review`.
