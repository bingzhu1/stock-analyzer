# Task 038 — projection_v2_three_stage_orchestrator

## Goal
Create a projection v2 orchestrator that forces every projection through a fixed, readable, safely degradable chain:

1. preflight / historical rule entry
2. primary_analysis / AVGO recent-window analysis
3. peer_adjustment / NVDA + SOXX + QQQ adjustment
4. historical_probability / historical sample probability layer
5. final_decision / combined output

The task is an orchestration skeleton, not a strategy rewrite.

## Scope
- Add `services/projection_orchestrator_v2.py`.
- Add focused tests for fixed schema, step order, safe degradation, and final decision behavior.
- Reuse existing projection / predict / scan outputs.
- Do not rewrite scanner, predict, router, planner, projection entrypoint, UI, or matching logic.

## Done When
- V2 returns fixed keys for all stages.
- `step_status`, `warnings`, and readable `trace` are always present.
- Peer and historical layers degrade explicitly.
- Primary-analysis failure returns `ready=false` and does not fake a full decision.
- Focused tests pass.
- Builder handoff is written and `tasks/STATUS.md` is updated to `in-review`.
