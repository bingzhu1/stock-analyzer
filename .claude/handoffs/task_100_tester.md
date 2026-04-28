# Task 100 — tester handoff

## Context scanned

- `tasks/STATUS.md`
- `services/projection_orchestrator_v2.py` (read for fix at site A;
  not edited)
- `services/projection_orchestrator.py` (read for fix at site B;
  not edited)
- `services/primary_20day_analysis.py` (read for fix at site C;
  not edited)
- `tests/test_primary_20day_analysis_target_date.py` (NEW — read
  for assertion shape)
- `tests/test_projection_orchestrator_v2_target_date_forwarding.py`
  (NEW — read for assertion shape)
- The 5-case replay output JSONL under
  `logs/historical_training/three_system_1005/`

Repository state at start of testing:

- branch: `main`
- HEAD: `de62025a56dc1dad81241940b075777520f83da8` (`de62025`)
- in sync with `origin/main` (post-Task-097 sync, PR-G merged via
  PR #8)
- builder pass left three production files modified
  (`services/projection_orchestrator_v2.py`,
  `services/projection_orchestrator.py`,
  `services/primary_20day_analysis.py`), two new untracked test
  files
  (`tests/test_primary_20day_analysis_target_date.py`,
  `tests/test_projection_orchestrator_v2_target_date_forwarding.py`),
  plus the deferred / protected entries
  (`.claude/handoffs/task_089_post_pr_cleanup.md`,
  `.claude/worktrees/`) and the Task 098D temporary replay
  artifacts (6 untracked .py files in `scripts/` + `services/` and
  the `logs/historical_training/three_system_1005/` directory)

## Commands run

All from `/Users/may/Desktop/stock-analyzer-main`, on local `main`.

Step 1 — git state sweep

- `git branch --show-current`
- `git status --short`
- `git log --oneline -5`
- `git diff --name-only HEAD`
- `git rev-parse HEAD`
- `ls -la` on the new test files, the 6 Task 098D temporary files,
  the protected `task_089_post_pr_cleanup.md`, and
  `.claude/worktrees/`

Step 2 — static + regression tests

- `python3 -m py_compile services/projection_orchestrator_v2.py
  services/projection_orchestrator.py
  services/primary_20day_analysis.py`
- `python3 -m pytest tests/test_primary_20day_analysis_target_date.py -v`
- `python3 -m pytest tests/test_projection_orchestrator_v2_target_date_forwarding.py -v`
- `python3 -m pytest tests/test_historical_replay_training.py -v`
- `python3 -m pytest tests/test_predict_tab_contradiction_card_wiring.py -v`
- `python3 -m pytest tests/test_predict_tab_exclusion_reliability_live_wiring.py -v`
- `python3 -m pytest tests/test_predict_tab_exclusion_reliability_review.py -v`
- `python3 -m pytest tests/test_big_up_contradiction_card.py -v`
- `python3 -m pytest tests/test_predict_summary.py -v`
- `bash scripts/check.sh`

Step 3 — replay variation sanity check

- `python3 scripts/run_1005_three_system_replay.py --num-cases 5
  --save-records`
- `python3 -` heredoc that parsed
  `logs/historical_training/three_system_1005/three_system_replay_results.jsonl`
  and reported per-row `as_of_date`, extracted `pos20`,
  `five_state_projection` vector, and `five_state_top1`. Computed
  distinct value counts to confirm date-by-date variation.

## Git state summary

- Branch: `main`, HEAD `de62025`, even with `origin/main`. No new
  commits during testing.
- Modified tracked files: exactly three —
  `services/primary_20day_analysis.py` (+30/-7),
  `services/projection_orchestrator.py` (+34/-17),
  `services/projection_orchestrator_v2.py` (+1).
  Total `+70, -19`.
- Untracked entries: 11 in total — 2 new Task-100 test files, 7
  Task-098D temporary replay artifacts (6 .py files +
  `logs/historical_training/three_system_1005/`), 2
  protected/deferred (`.claude/handoffs/task_089_post_pr_cleanup.md`,
  `.claude/worktrees/`).
- The new `task_100_tester.md` joins the untracked list when this
  handoff is written; `tasks/STATUS.md` becomes a fourth modified
  tracked file when the Task 100 row is added (also part of this
  Step 4).

## Static validation result

- `python3 -m py_compile services/projection_orchestrator_v2.py
  services/projection_orchestrator.py
  services/primary_20day_analysis.py` → **PASS** (exit 0, no
  output).

## Focused new-test results

### `tests/test_primary_20day_analysis_target_date.py` (NEW — 5/5)

- `test_target_date_in_middle_uses_data_through_that_date` ✓
- `test_two_different_target_dates_yield_different_features` ✓
- `test_target_date_none_uses_latest_rows` ✓
- `test_target_date_before_any_data_returns_unknown_result` ✓
- `test_target_date_filters_injected_dataframe` ✓

5 / 5 in 0.84s. Confirms the as-of-date filter at site C
(`services/primary_20day_analysis.py`) actually slices the
analysis window — an injected df with rows beyond `target_date`
is correctly truncated; two different target_dates yield
different `latest_close`; live behaviour is preserved when
`target_date is None`; an as-of-date earlier than the file's
first row returns a degraded `_unknown_result` rather than
silently using "now"-anchored data.

### `tests/test_projection_orchestrator_v2_target_date_forwarding.py` (NEW — 3/3)

- `test_target_date_is_forwarded_to_projection_runner` ✓
- `test_target_date_none_remains_none_in_runner_call` ✓
- `test_two_different_target_dates_propagate_independently` ✓

3 / 3 in 0.48s. Confirms `run_projection_v2(target_date=...)`
forwards the kwarg to its injected legacy runner — fixing the
boundary at site A
(`services/projection_orchestrator_v2.py`). Two back-to-back
calls with different `target_date` values arrive at the runner
as distinct values (no leakage).

## Regression results

| Suite | Result |
|---|---|
| `test_historical_replay_training.py` | **PASS — 57/57 in 0.04s** |
| `test_predict_tab_contradiction_card_wiring.py` (PR-G) | **PASS — 2/2 in 0.89s** |
| `test_predict_tab_exclusion_reliability_live_wiring.py` (PR-F) | **PASS — 2/2 in 0.84s** |
| `test_predict_tab_exclusion_reliability_review.py` (PR-E) | **PASS — 1/1 in 0.77s** |
| `test_big_up_contradiction_card.py` (PR-C) | **PASS — 31/31 in 0.14s** |
| `test_predict_summary.py` | **PASS — 5/5 in 0.80s** |

The four upstream-PR test surfaces (PR-C / PR-E / PR-F / PR-G) and
the existing replay-framework / predict-summary surfaces are
unaffected by the Task 100 target_date fix.

## `bash scripts/check.sh` result

- **PASS — exit 0.** Output: `All compile checks passed.`

## Total tests passed

**106 / 106** = `5 + 3 + 57 + 2 + 2 + 1 + 31 + 5`. No warnings, no
skips, no errors, no xfail / xpass / deselected.

## Replay variation sanity check (Step 3)

`python3 scripts/run_1005_three_system_replay.py --num-cases 5
--save-records` — runtime 3 s, exit 0. `record store: status=ok,
saved=5/5, skipped=0, failed=0`.

| idx | as_of_date | extracted pos20 | five_state_top1 |
|---|---|---:|---|
| 0 | 2026-04-21 | 96.1 | 小涨 |
| 1 | 2026-04-22 | 99.6 | 小涨 |
| 2 | 2026-04-23 | 93.3 | 小涨 |
| 3 | 2026-04-24 | 95.3 | 小涨 |
| 4 | 2026-04-27 | 90.6 | 震荡 |

Distinct value counts:

- `as_of_date`: 5 / 5 (expected)
- `pos20`: 5 distinct values (was 1 distinct value across all 1005
  days pre-fix)
- `five_state_top1`: 2 distinct (`小涨` × 4, `震荡` × 1) — pre-fix
  was 100 % `震荡` across 1005 days
- `final_direction`: 1 distinct (`偏多` × 5) — plausibly genuine
  for 5 consecutive days at high `pos20` in a sustained-bullish
  micro-window; not evidence of fix failure since the underlying
  probability vectors driving the direction are all distinct
- `five_state_projection`: 5 byte-distinct probability vectors
  (was 1 across all 1005 days pre-fix)

Five-state probability vectors:

```
row 0 (2026-04-21): {大涨:0.0, 小涨:0.6186, 震荡:0.3757, 小跌:0.005,  大跌:0.0007}
row 1 (2026-04-22): {大涨:0.0, 小涨:0.9854, 震荡:0.0133, 小跌:0.0009, 大跌:0.0004}
row 2 (2026-04-23): {大涨:0.0, 小涨:0.7678, 震荡:0.2188, 小跌:0.0117, 大跌:0.0017}
row 3 (2026-04-24): {大涨:0.0, 小涨:0.5745, 震荡:0.4246, 小跌:0.0007, 大跌:0.0002}
row 4 (2026-04-27): {大涨:0.0, 小涨:0.405,  震荡:0.4565, 小跌:0.1237, 大跌:0.0148}
```

Three independent confirmations that `target_date` is now respected:

1. **Per-date variation is real.** Five different `as_of_date`
   values produce five different `pos20`, five different
   probability vectors, and a non-trivial `five_state_top1`
   distribution.
2. **Latest-day reproduction is exact.** Row 4
   (`as_of_date = 2026-04-27`) reproduces the pre-fix output
   bit-for-bit (`pos20 = 90.6`, projection
   `{0, 0.405, 0.4565, 0.1237, 0.0148}`). `2026-04-27` is the
   latest trading day in the local data file, so as-of-04-27 ≡
   as-of-now, and the live UI behaviour is preserved by design.
3. **Day-by-day evolution is plausible.** `pos20` walks
   `90.6 → 95.3 → 93.3 → 99.6 → 96.1` (reading row 4 → 0) — a
   non-monotonic pattern that mirrors AVGO's actual short-term
   price-vs-20-day-window dynamics. If `target_date` were ignored,
   all five rows would be identical to row 4, which is exactly
   what Task 098D's 1005-case run produced pre-fix.

No tracebacks, no stderr noise during the replay. One informational
line `[INFO] No exact code matches found for 2026-04-24 with code
41443` from the legacy projection layer (no historical exact match
for that day's 5-digit code) — benign and is itself secondary
evidence that the fix works (different days now consult different
codes; pre-fix, every day used the same latest-day code).

## Confirmation: protected files untouched

- `.claude/handoffs/task_089_post_pr_cleanup.md` — `??`
  (untracked), stat unchanged across the 091 → 092 → 093 → 094 →
  095 → 096 → 097 → 098D → 099 → 100 sequence (`2966 B`, mtime
  `Apr 28 10:34`).
- `.claude/worktrees/` — `??` (top-level), 9 directories intact
  (`angry-babbage-fa47e1`, `beautiful-mcclintock-1dcda2`,
  `eloquent-stonebraker-e0cd86`, `frosty-zhukovsky-4a745b`,
  `hardcore-allen-3fdc69`, `jovial-mclaren-d9ee30`,
  `keen-liskov-5e6b9c`, `objective-mclaren-d459a2`,
  `sad-antonelli-49e876`).

Neither was opened by `Read`, `Edit`, or `Write` in this tester
pass. Neither appears in the index.

## Confirmation: temporary replay-driver files remain untracked

The 6 .py files copied during Task 098D Step 2 + the
`logs/historical_training/three_system_1005/` directory are still
listed as `??` in `git status` (untracked, never staged). Their
mtimes are stable from the original copy (`Apr 28 13:23 / 13:24`)
except where the Step 3 5-case replay deliberately overwrote
the `logs/historical_training/three_system_1005/*` artifacts.

These files are still in the working tree as Task-098D-era
artefacts and should be cleaned up in a separate cleanup pass once
the production-side fix from Task 100 is merged.

## Verdict

**PASS** — all of Steps 1–3 passed.

- Static validation: PASS (`py_compile` clean, `check.sh` clean).
- New `primary_20day_analysis` target_date tests: PASS (`5 / 5`).
- New orchestrator_v2 target_date forwarding tests: PASS
  (`3 / 3`).
- Existing replay-framework tests: PASS (`57 / 57`).
- Upstream PR-C / PR-E / PR-F / PR-G regressions: PASS
  (`31 + 1 + 2 + 2 = 36 / 36`).
- Predict-summary regression: PASS (`5 / 5`).
- Total: **106 / 106**.
- Replay variation check (Step 3): all five `as_of_date` produce
  distinct `pos20`, distinct `five_state_projection`, and
  non-trivial `five_state_top1` distribution. Latest-day output
  reproduces pre-fix values bit-for-bit, confirming live UI
  behaviour preserved.
- Scope guards: protected `task_089_post_pr_cleanup.md` and
  `.claude/worktrees/` unchanged; six Task-098D temporary
  replay-driver files still untracked; only the three explicitly-
  allowed production files modified (plus `tasks/STATUS.md`,
  modified now in Step 4 with the Task 100 status row).

Recommendation: Task 100 is ready to mark `done` (tester). The fix
is functionally correct, regression-free, and validated by both
unit and integration tests plus an end-to-end replay variation
check.

## Status

- Task 100: `done` (tester verdict).
