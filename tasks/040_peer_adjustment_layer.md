# Task 040 — peer_adjustment_layer

## Goal
Promote NVDA / SOXX / QQQ adjustment into an independent, stable, testable projection v2 Step 2 layer.

## Scope
- Add `services/peer_adjustment.py`.
- Return a fixed schema with peer confirmation, adjustment, adjusted direction/confidence, summary, basis, warnings, and peer snapshot.
- Use existing scanner relative-strength summaries and confirmation labels.
- Safely degrade when peers are missing or all relative-strength values are unavailable.
- Safely degrade when primary analysis is unavailable.
- Minimally wire projection v2 Step 2 to the new peer adjustment layer.

## Out of Scope
- Historical probability changes.
- Long-term rule preflight changes.
- UI changes.
- Legacy projection entrypoint wiring.
- Scanner / predict core rewrites.
- Complex peer scoring models.

## Done When
- Peer adjustment has an independent module.
- Output shape is stable.
- Missing / all-unavailable peer data does not fake success.
- `adjusted_direction` and `adjusted_confidence` are always explicit.
- Projection v2 Step 2 consumes the new layer.
- Focused tests pass.
- Builder handoff is written and `tasks/STATUS.md` is updated to `in-review`.
