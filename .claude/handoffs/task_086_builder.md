# Task 086 — builder handoff

## Context scanned

- `tasks/STATUS.md`
- `tasks/085_five_state_margin_policy_design.md`
- `services/projection_three_systems_renderer.py`
- `services/five_state_margin_policy.py`
- `tests/test_projection_three_systems_renderer.py`

Task 085 introduced a pure helper for low-margin five-state interpretation.
Task 086 wires that helper into `record_02_projection_system` only, with no
rule changes and no DB / replay work.

## Changed files

- `services/projection_three_systems_renderer.py`
- `tests/test_projection_three_systems_renderer.py`
- `tests/test_record_02_five_state_margin_policy_output.py`
- `tasks/086_integrate_five_state_margin_policy_into_record_02_output.md`
- `tasks/STATUS.md`
- `.claude/handoffs/task_086_builder.md`

## Implementation summary

### Renderer integration

`services/projection_three_systems_renderer.py` now imports:

```python
from services.five_state_margin_policy import apply_five_state_margin_policy
```

Inside `build_record_02_projection_system(...)`, the renderer now:

1. builds `five_state_distribution` from `main_projection.state_probabilities`
2. derives `final_direction` from `final_decision`
3. derives `five_state_top1` from `main_projection.predicted_top1.state`
   (fallback: margin-policy primary state when needed)
4. calls `apply_five_state_margin_policy(...)`
5. appends additive metadata fields to the output dict

Added output fields:

- `five_state_top1`
- `final_direction`
- `five_state_display_state`
- `five_state_margin_band`
- `five_state_top2_states`
- `five_state_top1_margin`
- `five_state_secondary_state`
- `five_state_secondary_probability`
- `five_state_state_conflict`
- `five_state_policy_note`

Existing fields preserved:

- `current_structure`
- `main_projection`
- `five_state_projection`
- `open_path_close_projection`
- `historical_sample_summary`
- `peer_market_confirmation`
- `key_price_levels`
- `risk_notes`
- `final_summary`

The empty/degraded `_empty_record_02_projection_system(...)` path was updated
to return the same additional fields with safe `unknown` / `None` values so
shape stays consistent across ready / unready paths.

### Test coverage

New focused file:

- `tests/test_record_02_five_state_margin_policy_output.py`

Coverage includes:

1. low-margin `震荡 0.45 / 小涨 0.42` adds `display_state=震荡/小涨分歧`
2. original `five_state_top1` remains `震荡`
3. original `final_direction` remains `偏多`
4. `top2_states = ["震荡", "小涨"]`
5. `margin_band = low_margin`
6. `top1_margin ≈ 0.03`
7. `state_conflict = True` for `偏多 + 震荡/小涨` close
8. clear-top1 case keeps `display_state = original top1`
9. malformed distribution degrades to unknown margin fields without crashing
10. `confidence_evaluator` unchanged
11. `negative_system` unchanged
12. renderer does not mutate the input

Also updated:

- `tests/test_projection_three_systems_renderer.py`

Why:
- The renderer’s `record_02_projection_system` shape changed additively.
- Existing shape assertions needed to recognize the new keys so future
  direct runs of that existing test file remain aligned with the new output.

## Validation steps

- `python3 -m py_compile services/projection_three_systems_renderer.py tests/test_record_02_five_state_margin_policy_output.py`
  - PASS
- `python3 -m pytest tests/test_record_02_five_state_margin_policy_output.py -v`
  - PASS
  - `7/7` tests passed
- `bash scripts/check.sh`
  - PASS
  - `All compile checks passed.`

Full regression:

- Skipped full 072–086 regression because this root workspace does not contain prior Task 072–083 test files.

Missing prerequisite files in this root:

- `tests/test_three_system_replay_audit.py`
- `tests/test_market_data_store.py`
- `tests/test_projection_record_store.py`
- `tests/test_projection_record_wiring_smoke.py`
- `tests/test_replay_record_wiring.py`
- `tests/test_run_1005_three_system_replay_save_records.py`
- `tests/test_audit_three_system_independence_from_db.py`
- `tests/test_audit_exclusion_overreach_from_db.py`
- `tests/test_exclusion_tier_classifier.py`
- `tests/test_negative_system_exclusion_tier_output.py`
- `tests/test_audit_effective_exclusion_tier_from_db.py`
- `tests/test_final_summary_effective_exclusions.py`

## No-business-logic confirmation

Touched in this builder pass:

- `services/projection_three_systems_renderer.py` (allowed)
- test files
- task docs / handoff / status

Not touched:

- `services/main_projection_layer.py`
- `services/final_decision.py`
- `services/projection_orchestrator_v2.py`
- `services/exclusion_layer.py`
- `services/exclusion_tier_classifier.py`
- `scripts/run_1005_three_system_replay.py`
- `data_fetcher.py`
- `feature_builder.py`
- `encoder.py`

## Remaining risks / follow-ups

- This task only adds metadata to the renderer output. No downstream UI or
  persistence layer consumes the new fields yet.
- The root workspace still lacks the broader 072–083 chain, so only focused
  validation was feasible here.
