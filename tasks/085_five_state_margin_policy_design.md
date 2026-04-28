# Task 085 — Five-State Margin Policy Design

- **Date:** 2026-04-28
- **Status:** in-review

## Goal

Design a five-state low-margin policy so `record_02_projection` does not
overstate a single top1 state when the top two five-state probabilities
are very close.

This task is **design / output-structure only**.

Do not modify:

- projection rules
- final decision logic
- negative_system
- confidence scoring
- data pipeline

## Context

Task 084's self-contained DB audit showed the representative pattern:

- `five_state_top1 = 震荡`
- `final_direction = 偏多`
- `震荡 = 0.45`
- `小涨 = 0.42`
- `top1_margin = 0.03`
- `low_margin_problem = true`
- `direction_state_mismatch = true`

That means a one-label top1 can hide useful ambiguity: `小涨` is nearly
as likely as `震荡`, while the direction output remains bullish.

## Scope

### In scope

- New `services/five_state_margin_policy.py`
- New `tests/test_five_state_margin_policy.py`
- New `tasks/085_five_state_margin_policy_design.md`
- New `.claude/handoffs/task_085_builder.md`
- Update `tasks/STATUS.md`

### Out of scope

- Any integration into renderer / projection output
- Any live DB / yfinance use
- Any business-logic change

## API

```python
apply_five_state_margin_policy(
    five_state_distribution: dict,
    final_direction: str | None = None,
    low_margin_threshold: float = 0.05,
    watch_margin_threshold: float = 0.10,
) -> dict
```

## Return shape

```python
{
  "primary_state": "...",
  "secondary_state": "...",
  "primary_probability": 0.45,
  "secondary_probability": 0.42,
  "top1_margin": 0.03,
  "margin_band": "low_margin" | "watch_margin" | "clear_top1" | "unknown",
  "display_state": "...",
  "state_conflict": True | False,
  "policy_note": "...",
  "top2_states": [...],
}
```

## Policy rules

1. If the distribution is missing or malformed:
   - `margin_band = "unknown"`
   - `display_state = "unknown"`

2. If `top1_margin < 0.05`:
   - `margin_band = "low_margin"`
   - `display_state = "{primary_state}/{secondary_state}分歧"`
   - `top2_states = [primary_state, secondary_state]`

3. If `0.05 <= top1_margin < 0.10`:
   - `margin_band = "watch_margin"`
   - `display_state = "{primary_state}为主，{secondary_state}接近"`

4. If `top1_margin >= 0.10`:
   - `margin_band = "clear_top1"`
   - `display_state = primary_state`

5. Direction/state conflict:
   - If `final_direction = 偏多`
   - and `primary_state = 震荡`
   - and `secondary_state in ["小涨", "大涨"]`
   - then `state_conflict = true`
   - and `policy_note` should mention:
     `方向偏多但五状态 top1 为震荡，且上涨状态接近`

6. Do not overwrite the original `primary_state`.
   This policy adds display-state and margin metadata only.

## Tests

Pure unit tests only. No DB. No yfinance.

Required coverage:

1. `震荡 0.45 vs 小涨 0.42 -> low_margin`
2. `display_state = "震荡/小涨分歧"`
3. `top2_states = ["震荡", "小涨"]`
4. `final_direction=偏多` with close `震荡/小涨` -> `state_conflict=true`
5. `margin = 0.07 -> watch_margin`
6. `margin = 0.12 -> clear_top1`
7. malformed distribution -> `unknown`
8. missing probabilities handled safely
9. tie handled deterministically
10. original distribution not mutated
11. clear top1 with agreeing direction -> `state_conflict=false`
12. `policy_note` non-empty

## Validation

```bash
python3 -m py_compile services/five_state_margin_policy.py tests/test_five_state_margin_policy.py
python3 -m pytest tests/test_five_state_margin_policy.py -v
bash scripts/check.sh
```

Important:

- Do not run full 072–085 regression in this root if prerequisite files
  are missing.
- If missing, report clearly:
  `Skipped full 072–085 regression because this root workspace does not contain prior Task 072–083 test files.`

## Acceptance

- focused tests pass
- `check.sh` passes
- no business logic modified
- policy identifies `震荡 45% vs 小涨 42%` as `low_margin`
- policy outputs `display_state` without overwriting original top1
