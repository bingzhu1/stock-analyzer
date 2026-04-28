# Task 085 — builder handoff

## Context scanned

- `tasks/STATUS.md`
- `tasks/084_five_state_collapse_audit_from_db.md`
- `services/state_label.py`
- `tests/test_state_label.py`

Task 084 established the motivating pattern in a self-contained audit:

- `five_state_top1 = 震荡`
- `final_direction = 偏多`
- `震荡 = 0.45`
- `小涨 = 0.42`
- `top1_margin = 0.03`

Task 085 answers that by adding a pure display-policy helper only. No
integration into renderer / projection output is attempted here.

## Changed files

- `services/five_state_margin_policy.py`
- `tests/test_five_state_margin_policy.py`
- `tasks/085_five_state_margin_policy_design.md`
- `tasks/STATUS.md`
- `.claude/handoffs/task_085_builder.md`

## Implementation summary

### `services/five_state_margin_policy.py`

New pure helper:

```python
apply_five_state_margin_policy(
    five_state_distribution: dict,
    final_direction: str | None = None,
    low_margin_threshold: float = 0.05,
    watch_margin_threshold: float = 0.10,
) -> dict
```

Returned fields:

- `primary_state`
- `secondary_state`
- `primary_probability`
- `secondary_probability`
- `top1_margin`
- `margin_band`
- `display_state`
- `state_conflict`
- `policy_note`
- `top2_states`

Policy behavior:

- malformed / missing distribution → `margin_band="unknown"`,
  `display_state="unknown"`
- `top1_margin < 0.05` → `low_margin`,
  `display_state="{primary}/{secondary}分歧"`
- `0.05 <= top1_margin < 0.10` → `watch_margin`,
  `display_state="{primary}为主，{secondary}接近"`
- `top1_margin >= 0.10` → `clear_top1`,
  `display_state=primary_state`
- if `final_direction="偏多"` and `primary_state="震荡"` and
  `secondary_state in {"小涨", "大涨"}`:
  - `state_conflict=True`
  - `policy_note` appends:
    `方向偏多但五状态 top1 为震荡，且上涨状态接近`

Design choices:

- The original `primary_state` is preserved and never overwritten
- `display_state` is additive metadata only
- Sorting is deterministic: by probability descending, then canonical
  state order (`大涨`, `小涨`, `震荡`, `小跌`, `大跌`)
- Input dict is not mutated

### `tests/test_five_state_margin_policy.py`

12 focused unit tests cover:

1. `震荡 0.45 vs 小涨 0.42` → `low_margin`
2. `display_state = "震荡/小涨分歧"`
3. `top2_states = ["震荡", "小涨"]`
4. `final_direction=偏多` with close `震荡/小涨` → `state_conflict=True`
5. margin `0.07` → `watch_margin`
6. margin `0.12` → `clear_top1`
7. malformed distribution → `unknown`
8. missing state probabilities handled safely
9. tie handled deterministically
10. original distribution not mutated
11. clear top1 with agreeing direction → `state_conflict=False`
12. `policy_note` non-empty

## Validation steps

- `python3 -m py_compile services/five_state_margin_policy.py tests/test_five_state_margin_policy.py`
  - PASS
- `python3 -m pytest tests/test_five_state_margin_policy.py -v`
  - PASS
  - `12/12` tests passed
- `bash scripts/check.sh`
  - PASS
  - `All compile checks passed.`

Full regression:

- Skipped full 072–085 regression because this root workspace does not contain prior Task 072–083 test files.

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

Checked and not touched by Task 085:

- `services/projection_three_systems_renderer.py`
- `services/main_projection_layer.py`
- `services/final_decision.py`
- `services/projection_orchestrator_v2.py`
- `services/exclusion_layer.py`
- `scripts/run_1005_three_system_replay.py`
- `data_fetcher.py`
- `feature_builder.py`
- `encoder.py`

Only Task 085 files plus `tasks/STATUS.md` changed in this builder pass.

## Remaining risks / follow-ups

- This task does not integrate the policy into any live output surface.
  A future task can wire `display_state` / `margin_band` into
  `record_02_projection` rendering without altering the underlying
  probability logic.
- Current helper expects a complete five-state dict. If future callers
  need percent-string support or partial distributions, that can be
  added in a later scoped task.
