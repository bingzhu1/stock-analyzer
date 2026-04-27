# Task 06Q — builder handoff

## Context scanned

- `.claude/CLAUDE.md`, `.claude/PROJECT_STATUS.md`, `.claude/CHECKLIST.md`, `tasks/STATUS.md`
- `services/projection_entrypoint.py`
- `services/projection_orchestrator_v2.py`
- `services/projection_narrative_renderer.py`
- `services/projection_v2_adapter.py`
- `services/exclusion_layer.py`
- `services/main_projection_layer.py`
- `services/final_decision.py`
- `services/consistency_layer.py` (top half)
- `ui/projection_v2_renderer.py`
- existing tests `tests/test_projection_narrative_renderer.py`, `tests/test_projection_entrypoint.py`

## Implementation summary

This round delivers a pure **output-architecture refactor**, not a rule change.
The existing projection v2 chain (exclusion → primary → peer → historical → final → main_projection → consistency)
was left untouched. A new renderer reshapes the v2 raw payload into three independent, structured systems:

1. **`negative_system`** — derived from `exclusion_result` + `final_decision.why_not_more_bullish_or_bearish`.
   Fields: `conclusion`, `excluded_states`, `strength`, `evidence`, `invalidating_conditions`, `risk_notes`.
2. **`record_02_projection_system`** — derived from `primary_analysis` / `peer_adjustment` /
   `historical_probability` / `final_decision` / `main_projection` / `consistency`.
   Fields: `current_structure`, `main_projection`, `five_state_projection`, `open_path_close_projection`,
   `historical_sample_summary`, `peer_market_confirmation`, `key_price_levels`, `risk_notes`, `final_summary`.
3. **`confidence_evaluator`** — independently scores the reliability of the previous two systems.
   Sub-blocks: `negative_system_confidence`, `projection_system_confidence`, `overall_confidence`,
   `conflicts`, `reliability_warnings`. `level → score` mapping is deterministic
   (low=0.3 / medium=0.6 / high=0.9 / unknown=None) and is exposure of existing confidence,
   not new calculation.

Wiring: `services/projection_entrypoint.run_projection_entrypoint` now appends a
`result["projection_three_systems"]` field after the existing `projection_narrative` block.
Both calls are wrapped in `try/except` and degrade with a stable shape if the renderer raises.
No legacy field was removed or renamed; UI is untouched.

## Changed files

| Path | Change |
|------|--------|
| `services/projection_three_systems_renderer.py` | New module. Builds `negative_system`, `record_02_projection_system`, `confidence_evaluator`, and the unified `build_projection_three_systems` entry. |
| `services/projection_entrypoint.py` | Imports new renderer; adds `_degraded_projection_three_systems()`; sets `result["projection_three_systems"]` with try/except fallback and notes append on degradation. Existing returns unchanged. |
| `tests/test_projection_three_systems_renderer.py` | New. 17 tests covering negative-system / record-02 / confidence sub-shapes, happy path, exclusion-triggered, primary-failed degradation, conflict detection, no-mutation, symbol override. |
| `tests/test_projection_entrypoint_three_systems.py` | New. 4 tests covering field presence, legacy-field stability, degraded fallback, v2-unready handling — all using `unittest.mock.patch` so no live network calls. |
| `tests/test_projection_entrypoint.py` | Minimal update: the strict-equality assertion in `test_entrypoint_calls_v2_runner_then_packages_legacy_shell` now pops the new `projection_three_systems` key, asserts its shape, then asserts the legacy fields equal `packaged | {"projection_narrative": narrative}` exactly. No semantic change. |
| `tasks/06Q_projection_output_three_systems.md` | New canonical task spec. |
| `tasks/STATUS.md` | Added `06Q` mapping line and table row. |
| `.claude/handoffs/task_06Q_builder.md` | This file. |

## Validation steps

- `python3 -m py_compile services/projection_entrypoint.py services/projection_three_systems_renderer.py tests/test_projection_three_systems_renderer.py tests/test_projection_entrypoint_three_systems.py tests/test_projection_entrypoint.py` → OK
- `bash scripts/check.sh` → All compile checks passed.
- `python3 -m unittest tests.test_projection_three_systems_renderer tests.test_projection_entrypoint_three_systems` → 21 tests pass.
- `python3 -m unittest tests.test_projection_three_systems_renderer tests.test_projection_entrypoint_three_systems tests.test_projection_narrative_renderer tests.test_projection_v2_adapter tests.test_projection_orchestrator_v2 tests.test_main_projection_layer` → 77 tests pass.
- `python3 -m unittest tests.test_projection_entrypoint` → 4/6 tests pass; the 2 remaining failures (`test_empty_state_calls_orchestrator_chain`, `test_returns_orchestrated_result_without_changing_meaning`) **already fail without my changes** because they invoke `run_projection_entrypoint` without mocking `run_projection_v2`, which requires a live yfinance call. Confirmed via `git stash` baseline run before merging the change. Out of scope for Task 06Q.

## Remaining risks

- The numeric `score` mapping (low=0.3 / medium=0.6 / high=0.9) is deterministic and documented in the task file and the renderer. If a downstream consumer wants different numerics, only `_LEVEL_TO_SCORE` needs updating.
- `key_price_levels` is currently always `[]` because the v2 raw payload has no explicit support/resistance levels. If a future task wires those in, only `_record_02_projection_system` needs to update — no consumer relies on a non-empty list.
- The new field is **not yet read by UI**. Per the task hard rule (no production cutover, ui/ untouched), this is intentional. A future task can switch the renderer over once contract stability is reviewed.
- Two pre-existing `tests/test_projection_entrypoint.py` failures rely on live yfinance — flag for tester to triage and consider mocking in a follow-up; tracked in `feedback_tests_no_live_network.md` memory. Not introduced by this task.
- `services/exclusion_layer.run_exclusion_layer` does not currently surface `kill_risk` in its aggregate result (only `exclude_big_up` / `exclude_big_down` do). The negative-system strength derivation therefore uses `reasons` count + `feature_snapshot` completeness instead. This is consistent with current data; if exclusion_layer ever exposes aggregate `kill_risk`, the renderer can switch to that signal without any caller change.

## Suggested next role

Reviewer — should verify (a) no rule mutation occurred in scanner / matcher / encoder / feature_builder / exclusion / final_decision / orchestrator_v2; (b) new shape matches `tasks/06Q_projection_output_three_systems.md`; (c) entrypoint legacy contract preserved; (d) the 2 pre-existing live-network test failures predate this round.
