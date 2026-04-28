# Task 086 — Integrate Five-State Margin Policy Into record_02 Output

- **Date:** 2026-04-28
- **Status:** in-review

## Goal

Integrate the pure five-state margin policy into `record_02_projection`
output as additional metadata, without overwriting the original
`five_state_top1` or `final_direction`.

This is **output-structure only**.

Do not modify:

- projection rules
- final decision logic
- negative_system
- confidence scoring
- data pipeline

## Context

Task 084 added a five-state collapse audit.
Task 085 added the pure helper:

- `services/five_state_margin_policy.py`

Validated example:

- `震荡 0.45`
- `小涨 0.42`
- `margin_band = low_margin`
- `display_state = 震荡/小涨分歧`
- `top2_states = ["震荡", "小涨"]`
- `state_conflict = True`

Task 086 wires that into `record_02_projection_system` as metadata only.

## Scope

### In scope

- Modify `services/projection_three_systems_renderer.py`
- Add `tests/test_record_02_five_state_margin_policy_output.py`
- Add `tasks/086_integrate_five_state_margin_policy_into_record_02_output.md`
- Add `.claude/handoffs/task_086_builder.md`
- Update `tasks/STATUS.md`

### Out of scope

- Any projection/final-decision rule change
- Any DB / live replay work
- Any negative_system / confidence logic change

## Integration

Allowed import:

```python
from services.five_state_margin_policy import apply_five_state_margin_policy
```

Inside `build_record_02_projection_system(...)`:

```python
margin_policy = apply_five_state_margin_policy(
    five_state_distribution,
    final_direction=final_direction,
)
```

## Added output fields

- `five_state_display_state`
- `five_state_margin_band`
- `five_state_top2_states`
- `five_state_top1_margin`
- `five_state_secondary_state`
- `five_state_secondary_probability`
- `five_state_state_conflict`
- `five_state_policy_note`

Additive raw-value fields also exposed in the same output structure:

- `five_state_top1`
- `final_direction`

## Important behavior

Do **not** change:

- `five_state_top1`
- `five_state_projection` probabilities
- `final_direction`
- `main_projection`
- `final_summary`
- sibling `negative_system`
- sibling `confidence_evaluator`

## Expected low-margin example

For:

```python
{
  "大涨": 0.00,
  "小涨": 0.42,
  "震荡": 0.45,
  "小跌": 0.11,
  "大跌": 0.02,
}
```

and `final_direction = 偏多`

the output should include:

- `five_state_top1 = 震荡`
- `five_state_display_state = 震荡/小涨分歧`
- `five_state_margin_band = low_margin`
- `five_state_top2_states = ["震荡", "小涨"]`
- `five_state_top1_margin ≈ 0.03`
- `five_state_secondary_state = 小涨`
- `five_state_secondary_probability = 0.42`
- `five_state_state_conflict = True`

## Tests

Pure unit tests only. No DB. No yfinance.

Required coverage:

1. low-margin `震荡` vs `小涨` adds `display_state=震荡/小涨分歧`
2. original `five_state_top1` remains `震荡`
3. `final_direction` remains `偏多`
4. `top2_states = ["震荡", "小涨"]`
5. `margin_band = low_margin`
6. `top1_margin ≈ 0.03`
7. `state_conflict = True` for `偏多 + 震荡/小涨` close
8. clear-top1 case `display_state = original top1`
9. malformed distribution returns unknown margin fields but does not crash
10. `confidence_evaluator` unchanged
11. `negative_system` unchanged
12. existing record_02 fields still present

## Validation

```bash
python3 -m py_compile services/projection_three_systems_renderer.py tests/test_record_02_five_state_margin_policy_output.py
python3 -m pytest tests/test_record_02_five_state_margin_policy_output.py -v
bash scripts/check.sh
```

Important:

- Do not run full 072–086 regression in this root if prerequisite files
  are missing.
- If missing, report clearly:
  `Skipped full 072–086 regression because this root workspace does not contain prior Task 072–083 test files.`

## Acceptance

- focused tests pass
- `check.sh` passes
- no projection / final decision logic modified
- `record_02` output includes margin policy metadata
- original `five_state_top1` and `final_direction` remain unchanged
