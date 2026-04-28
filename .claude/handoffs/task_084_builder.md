# Task 084 — builder handoff

## Context scanned

- `tasks/STATUS.md`
- Related prior-task audit specs and handoffs from the nearby worktree:
  - `079_exclusion_overreach_audit_from_db.md`
  - `082_audit_effective_exclusion_tier_from_db.md`
  - `083_adjust_summary_to_use_effective_exclusions.md`
  - `task_078_builder.md`
  - `task_079_builder.md`
  - `task_082_builder.md`
  - `task_083_builder.md`
- Related nearby audit implementations used only as pattern references:
  - `audit_three_system_independence_from_db.py`
  - `audit_exclusion_overreach_from_db.py`
  - `audit_effective_exclusion_tier_from_db.py`
- Local root validation helper:
  - `scripts/check.sh`

Important scope decision followed:

- **Did not port** missing Task 072–083 files from the nearby worktree
- Implemented Task 084 as a **self-contained** SQLite audit in the
  current root workspace
- **Did not modify** business logic, projection rules, final decision,
  negative_system, confidence scoring, renderer, model, or data pipeline files

## Changed files

- `scripts/audit_five_state_collapse_from_db.py`
- `tests/test_audit_five_state_collapse_from_db.py`
- `tasks/084_five_state_collapse_audit_from_db.md`
- `tasks/STATUS.md`
- `.claude/handoffs/task_084_builder.md`

## Implementation

### `scripts/audit_five_state_collapse_from_db.py`

New audit-only script that reads:

- `projection_runs`
- `record_02_projection`

and computes:

- `five_state_top1` distribution
- `final_direction` distribution
- `five_state_top1 + final_direction` joint distribution
- parsed five-state probabilities from `five_state_distribution_json`
- `derived_top1`, `second_state`, `top1_prob`, `second_prob`, `top1_margin`
- low-margin buckets:
  - `margin < 0.03`
  - `margin < 0.05`
  - `margin < 0.10`
- average probability by state:
  - `大涨`
  - `小涨`
  - `震荡`
  - `小跌`
  - `大跌`
- malformed / missing probability rows
- `final_direction=偏多` + `five_state_top1=震荡` mismatch share
- `震荡` beating `小涨` by tiny margin

It writes 7 outputs:

- `five_state_collapse_audit.json`
- `five_state_collapse_audit.md`
- `five_state_top1_distribution.csv`
- `final_direction_distribution.csv`
- `five_state_margin_cases.csv`
- `five_state_probability_summary.csv`
- `direction_state_mismatch_cases.csv`

Judgment handling:

- primary `judgment` follows the requested priority order
- `flags` exposes **all** triggered conditions simultaneously:
  - `insufficient_data`
  - `malformed_probability_data`
  - `five_state_top1_collapse`
  - `final_direction_collapse`
  - `low_margin_problem`
  - `direction_state_mismatch`

Implementation details:

- probability parsing accepts both decimal form (`0.45`) and percent form
  (`45%` / `45`)
- malformed rows are counted when JSON is invalid, not a dict, missing
  canonical states, or contains non-numeric / negative values
- top1/direction collapse uses the saved record columns
- margin analysis uses the parsed probability distribution
- low-margin share is computed over valid probability rows only

### `tests/test_audit_five_state_collapse_from_db.py`

New focused tests using **temporary in-memory SQLite only**.
No live DB, no yfinance, no prior-task imports required.

Covered behaviors:

1. `insufficient_data` when fewer than 5 rows
2. `five_state_top1` collapse detection
3. `final_direction` collapse detection
4. low-margin top1 problem detection
5. `偏多 + 震荡` mismatch flag + joint distribution
6. probability JSON parsing
7. malformed probability handling
8. `top1_margin` and `second_state` calculation
9. output-file writing
10. `no_collapse` branch
11. probability summary averages

## Validation

Focused Task 084 validation completed:

- `python3 -m py_compile scripts/audit_five_state_collapse_from_db.py tests/test_audit_five_state_collapse_from_db.py`
  - PASS
- `python3 -m pytest tests/test_audit_five_state_collapse_from_db.py -v`
  - PASS
  - `11 passed in 0.11s`
- `bash scripts/check.sh`
  - PASS
  - `All compile checks passed.`

Full original 072–084 regression command:

- **Skipped full 072–084 regression because this root workspace does not contain prior Task 072–083 test files.**

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

Present in this root:

- `tests/test_audit_five_state_collapse_from_db.py`

## Remaining risks

- Builder pass did **not** run a live 50-case AVGO audit. This matches scope.
- Full cross-task regression remains blocked on missing local Task 072–083
  test files in this root workspace.
- The audit is descriptive only; it does not act on any collapse finding.
