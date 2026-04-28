# Task 084 — Five-State Collapse Audit (From DB)

- **Date:** 2026-04-28
- **Status:** in-review

## Goal

Audit why `record_02_projection` collapses toward:

- `five_state_top1 = 震荡`
- `final_direction = 偏多`

across recent AVGO replay cases.

This task is **audit-only**.

Do not modify:

- projection rules
- final decision logic
- negative_system logic
- confidence scoring
- existing renderer / model / data pipeline files

## Scope

### In scope

- New `scripts/audit_five_state_collapse_from_db.py`
- New `tests/test_audit_five_state_collapse_from_db.py`
- New `tasks/084_five_state_collapse_audit_from_db.md`
- New `.claude/handoffs/task_084_builder.md`
- Update `tasks/STATUS.md`

### Out of scope

- Porting missing Task 072–083 files from nearby worktrees
- Live replay / live DB smoke
- Any business-logic changes

## Data source

In this root workspace, the Task 084 audit is implemented as a
**self-contained SQLite audit** over:

- `projection_runs`
- `record_02_projection`

It does not require prior-task imports and is testable using temporary
SQLite fixtures only.

## CLI

```bash
python3 scripts/audit_five_state_collapse_from_db.py --symbol AVGO --limit 50
```

Optional args:

- `--db-path` default: `data/market_data.db`
- `--output-dir` default: `logs/five_state_collapse_audit`

## Output files

- `logs/five_state_collapse_audit/five_state_collapse_audit.json`
- `logs/five_state_collapse_audit/five_state_collapse_audit.md`
- `logs/five_state_collapse_audit/five_state_top1_distribution.csv`
- `logs/five_state_collapse_audit/final_direction_distribution.csv`
- `logs/five_state_collapse_audit/five_state_margin_cases.csv`
- `logs/five_state_collapse_audit/five_state_probability_summary.csv`
- `logs/five_state_collapse_audit/direction_state_mismatch_cases.csv`

## Audit sections

1. `total_cases`
2. `five_state_top1` distribution
3. `final_direction` distribution
4. `five_state_top1 + final_direction` joint distribution
5. parse `five_state_distribution_json`
6. compute `top1_margin = top1_prob - second_prob`
7. identify `second_state` for each valid probability row
8. count low-margin cases:
   - `margin < 0.03`
   - `margin < 0.05`
   - `margin < 0.10`
9. compute average probability for:
   - `大涨`
   - `小涨`
   - `震荡`
   - `小跌`
   - `大跌`
10. detect whether `震荡` wins by tiny margin over `小涨`
11. detect whether `final_direction=偏多` conflicts with `five_state_top1=震荡`
12. detect missing / malformed probability payloads

## Judgment

Primary `judgment` values:

- `insufficient_data`
- `malformed_probability_data`
- `five_state_top1_collapsed`
- `final_direction_collapsed`
- `low_margin_top1_problem`
- `direction_state_mismatch`
- `no_collapse`

The output also includes a `flags` object so multiple conditions can be
reported at once, even when the top-level `judgment` picks the first
matching label.

Thresholds:

- fewer than 5 cases -> `insufficient_data`
- malformed / missing probability rows > 20% -> `malformed_probability_data`
- one top1 state >= 70% -> `five_state_top1_collapsed`
- one final_direction >= 70% -> `final_direction_collapsed`
- more than 50% valid probability rows have `top1_margin < 0.05`
  -> `low_margin_top1_problem`
- more than 70% cases have `final_direction=偏多` and
  `five_state_top1=震荡` -> `direction_state_mismatch`
- otherwise -> `no_collapse`

## Tests

`tests/test_audit_five_state_collapse_from_db.py` uses temporary
SQLite only. No live DB. No yfinance. No prior-task module dependency.

Coverage includes:

1. insufficient_data when fewer than 5 rows
2. top1 collapse detection
3. final_direction collapse detection
4. low-margin detection
5. `偏多 + 震荡` mismatch detection
6. probability JSON parsing
7. malformed probability handling
8. `top1_margin` and `second_state` calculation
9. output-file writing
10. `no_collapse` branch
11. probability summary averages
12. joint distribution includes `震荡|偏多`

## Validation

Focused builder-pass validation:

```bash
python3 -m py_compile scripts/audit_five_state_collapse_from_db.py tests/test_audit_five_state_collapse_from_db.py
python3 -m pytest tests/test_audit_five_state_collapse_from_db.py -v
bash scripts/check.sh
```

Full original 072–084 regression command is **not** executed in this
task when prerequisite Task 072–083 test files are absent from the
current root workspace.

## Acceptance

- Focused Task 084 tests pass
- `bash scripts/check.sh` passes
- JSON / Markdown / CSV outputs are written
- Audit distinguishes:
  - true top1 collapse
  - low-margin top1 behavior
  - malformed probability data
  - `震荡` + `偏多` direction/state mismatch
- No business logic modified
