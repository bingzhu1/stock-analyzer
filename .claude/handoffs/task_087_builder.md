# Task 087 — builder handoff

## Context scanned

- `tasks/STATUS.md`
- `tasks/086_integrate_five_state_margin_policy_into_record_02_output.md`
- `services/projection_three_systems_renderer.py`
- `tests/test_record_02_five_state_margin_policy_output.py`

Task 086 already surfaced additive margin metadata in
`record_02_projection_system`, but no dedicated display-summary field
used that metadata. Task 087 adds display-only text that exposes the
split explicitly while preserving all original values.

## Changed files

- `services/projection_three_systems_renderer.py`
- `tests/test_projection_three_systems_renderer.py`
- `tests/test_record_02_display_state_summary.py`
- `tasks/087_surface_five_state_display_state_in_summary.md`
- `tasks/STATUS.md`
- `.claude/handoffs/task_087_builder.md`

## Implementation summary

### Renderer change

Added a private helper in `services/projection_three_systems_renderer.py`:

- `_five_state_display_summary(...)`

This helper builds a readable, display-only summary from:

- `five_state_top1`
- `final_direction`
- `five_state_display_state`
- `five_state_margin_band`
- `five_state_secondary_state`
- `five_state_top1_margin`
- `five_state_policy_note`
- `five_state_state_conflict`

Behavior by band:

- `low_margin`
  - mentions original top1
  - mentions display state such as `震荡/小涨分歧`
  - mentions `小涨` 接近 / 分歧
  - mentions `top1 margin` / `微弱优势`
  - mentions `final_direction`
  - appends the conflict note when present
- `watch_margin`
  - mentions original top1
  - mentions display state
  - mentions secondary state still close
  - mentions `top1 margin`
- `clear_top1`
  - can simply show the primary state as current display
- `unknown`
  - degrades safely to a generic unavailable summary

The renderer now adds one new field to `record_02_projection_system`:

- `five_state_display_summary`

Important preservation guarantees:

- original `five_state_top1` unchanged
- original `final_direction` unchanged
- original `five_state_projection` unchanged
- original `main_projection` unchanged
- original `final_summary` unchanged
- sibling `negative_system` unchanged
- sibling `confidence_evaluator` unchanged

The `_empty_record_02_projection_system(...)` degraded path was updated
to include the new `five_state_display_summary` field with a safe
fallback string so shape remains consistent.

### Tests

New focused file:

- `tests/test_record_02_display_state_summary.py`

Coverage includes:

1. low-margin summary includes `震荡/小涨分歧`
2. summary mentions original `top1=震荡`
3. summary mentions `小涨` 接近 / 分歧
4. summary mentions `final_direction=偏多`
5. summary does not collapse to a bare `"五状态：震荡"` style
6. clear-top1 case can simply show the primary state
7. original `five_state_top1` remains unchanged
8. original `final_direction` remains unchanged
9. negative_system unchanged
10. confidence_evaluator unchanged
11. all existing record_02 fields still present
12. malformed / unknown margin case degrades safely

Also updated:

- `tests/test_projection_three_systems_renderer.py`

Reason:
- additive renderer shape now includes `five_state_display_summary`
- existing shape assertions need to acknowledge the new field

## Validation steps

- `python3 -m py_compile services/projection_three_systems_renderer.py tests/test_record_02_display_state_summary.py`
  - PASS
- `python3 -m pytest tests/test_record_02_display_state_summary.py -v`
  - PASS
  - `12/12` tests passed
- `python3 -m pytest tests/test_record_02_five_state_margin_policy_output.py -v`
  - PASS
  - `7/7` tests passed
- `python3 -m pytest tests/test_projection_three_systems_renderer.py -v`
  - PASS
  - `17/17` tests passed
- `bash scripts/check.sh`
  - PASS
  - `All compile checks passed.`

Full regression:

- Skipped full 072–087 regression because this root workspace does not contain prior Task 072–083 test files.

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
- tests
- task doc / handoff / status

Not touched:

- `services/five_state_margin_policy.py`
- `services/main_projection_layer.py`
- `services/final_decision.py`
- `services/projection_orchestrator_v2.py`
- `services/exclusion_layer.py`
- `scripts/run_1005_three_system_replay.py`
- `data_fetcher.py`
- `feature_builder.py`
- `encoder.py`

## Notes on root workspace state

The current root already contains untracked files from prior Tasks 084–086,
including:

- `services/five_state_margin_policy.py`
- `tests/test_record_02_five_state_margin_policy_output.py`

Those are pre-existing root-workspace state for this turn and were not
created by Task 087.

## Remaining risks / follow-ups

- This task only adds display summary text to renderer output. No downstream
  UI / persistence surface is consuming it yet.
- The broader 072–083 chain remains absent in this root, so only focused
  validation was feasible here.
