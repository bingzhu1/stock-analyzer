# Task 087 — Surface Five-State Display State In Summary

- **Date:** 2026-04-28
- **Status:** in-review

## Goal

Surface the `five_state_display_state` / margin metadata from
`record_02_projection_system` in display summary text, while preserving
the original `five_state_top1` and `final_direction` fields.

This is **display-only**.

Do not modify:

- projection rules
- final decision logic
- negative_system
- confidence scoring
- data pipeline

## Context

Task 086 already wired margin metadata into `record_02_projection_system`:

- `five_state_display_state`
- `five_state_margin_band`
- `five_state_top2_states`
- `five_state_top1_margin`
- `five_state_secondary_state`
- `five_state_secondary_probability`
- `five_state_state_conflict`
- `five_state_policy_note`

But the readable summary/display text can still hide the split if it only
surfaces raw `five_state_top1=震荡`.

## Scope

### In scope

- Modify `services/projection_three_systems_renderer.py`
- Add `tests/test_record_02_display_state_summary.py`
- Add `tasks/087_surface_five_state_display_state_in_summary.md`
- Add `.claude/handoffs/task_087_builder.md`
- Update `tasks/STATUS.md`

### Out of scope

- Any projection/final-decision rule change
- Any DB / replay work
- Any negative_system / confidence logic change
- Any change to `services/five_state_margin_policy.py`

## Implementation

Use existing metadata:

- `five_state_display_state`
- `five_state_margin_band`
- `five_state_top2_states`
- `five_state_top1_margin`
- `five_state_policy_note`

Add one display-oriented field:

- `five_state_display_summary`

This field should mention, when applicable:

- original `five_state_top1`
- display state (`五状态展示状态`)
- nearby secondary state / split context
- weak `top1 margin`
- original `final_direction`
- direction/state conflict note when present

## Expected low-margin behavior

For:

- `five_state_top1 = 震荡`
- `final_direction = 偏多`
- `five_state_display_state = 震荡/小涨分歧`
- `five_state_margin_band = low_margin`
- `five_state_top2_states = ["震荡", "小涨"]`
- `five_state_top1_margin = 0.03`
- `five_state_state_conflict = True`

display summary should mention:

- original top1 = `震荡`
- display state = `震荡/小涨分歧`
- `小涨` 接近 / 分歧
- `top1 margin` / 微弱优势
- `final_direction = 偏多`
- `方向偏多但五状态 top1 为震荡`

It should not reduce the state to a simple `"五状态：震荡"` style summary
without split context.

## Tests

Pure unit tests only. No DB. No yfinance.

Required coverage:

1. low-margin record_02 summary includes `震荡/小涨分歧`
2. summary mentions original `top1=震荡`
3. summary mentions `小涨` 接近 / 分歧
4. summary mentions `final_direction=偏多`
5. summary does not reduce the state to only `震荡` without split context
6. clear-top1 case summary can just show primary state
7. original `five_state_top1` remains unchanged
8. original `final_direction` remains unchanged
9. negative_system unchanged
10. confidence_evaluator unchanged
11. all existing record_02 fields still present
12. malformed / unknown margin case degrades safely

## Validation

```bash
python3 -m py_compile services/projection_three_systems_renderer.py tests/test_record_02_display_state_summary.py
python3 -m pytest tests/test_record_02_display_state_summary.py -v
python3 -m pytest tests/test_record_02_five_state_margin_policy_output.py -v
python3 -m pytest tests/test_projection_three_systems_renderer.py -v
bash scripts/check.sh
```

Important:

- Do not run full 072–087 regression in this root if prerequisite files
  are missing.
- If missing, report clearly:
  `Skipped full 072–087 regression because this root workspace does not contain prior Task 072–083 test files.`

## Acceptance

- focused tests pass
- renderer tests pass
- `check.sh` passes
- display summary surfaces `five_state_display_state`
- original `five_state_top1` and `final_direction` remain unchanged
- no projection / final decision logic modified
