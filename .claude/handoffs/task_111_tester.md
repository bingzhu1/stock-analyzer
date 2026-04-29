# Task 111 — tester handoff (Task 110 confidence_evaluator recalibration)

## Context scanned

- `.claude/CLAUDE.md` — project mission and hard rules.
- `tasks/STATUS.md` — current status table; Task 104 row at 176, no Task 110 row yet.
- `services/projection_three_systems_renderer.py` — recalibrated module (read after Task 110 builder pass).
- `tests/test_projection_three_systems_renderer.py` — 11 new + 1 updated assertions (Task 110).
- `tests/test_record_02_five_state_margin_policy_output.py` — 1 updated assertion (Task 110).
- `services/five_state_margin_policy.py` — `apply_five_state_margin_policy` interface (read-only, used by recalibrated projection-confidence path).
- `tests/test_record_02_display_state_summary.py`, `tests/test_predict.py`,
  `tests/test_predict_tab_confidence_three_columns.py`,
  `tests/test_projection_entrypoint_three_systems.py`,
  `tests/test_three_system_replay_audit_features.py` — sibling regression suites listed in Step 2.
- `scripts/run_1005_three_system_replay.py` — replay smoke driver (read by invocation).

## Repository state at start of testing

- Branch: `main` (user-directed `cd /Users/may/Desktop/stock-analyzer-main`; the worktree branch
  `claude/focused-jennings-d2f91a` is unrelated to the validation).
- HEAD: `f417c45` (`Merge pull request #12 from bingzhu1/pr-k-fix-projection-three-systems-recursion`).
- Modified tracked files (three, exactly the expected scope):
  - `services/projection_three_systems_renderer.py`
  - `tests/test_projection_three_systems_renderer.py`
  - `tests/test_record_02_five_state_margin_policy_output.py`
- Untracked (pre-existing protected paths, not touched by Task 110/111):
  - `.claude/handoffs/task_089_post_pr_cleanup.md`
  - `.claude/worktrees/`
  - `logs/historical_training/three_system_1005/`
- `git diff --name-only HEAD` confirmed: only the three Task 110 deliverables modified — no
  `final_direction` carriers, `five_state_projection` math, `negative_excluded_states` policy,
  target-date wiring, replay-driver, or UI files modified.

## Changed files (Task 110 deliverables under test)

| Path | Status | Purpose |
|---|---|---|
| `services/projection_three_systems_renderer.py` | modified | Recalibrated confidence labels per Task 106 findings. Negative side: split `exclude_big_up` / `exclude_big_down`, dangerous-regime gate (`vol_ratio20≥1.30`, `ret5≤-2`, `pos20≤30`) caps `exclude_big_down` at `medium` (1 flag) or `low` (≥2 flags); non-excluded normal case caps at `medium` (no auto-`high`); `pos20≥80` records caution-only risk note. Projection side: tail cap (`top1 ∈ {大涨,大跌}` ⇒ `medium`), overconfidence downgrade (`top1_margin≥0.60` ⇒ −1 level), healthy-high guard (`high` only when non-tail ∧ `0.10≤margin≤0.40` ∧ no conflict). Conflicts now wired into `build_projection_system_confidence` via new `conflicts=` kwarg from `build_confidence_evaluator`. Output shapes (`{level, score, reasoning, risks}` for sub-blocks, `{level, score, reasoning}` for overall) preserved bit-for-bit; UI consumers unchanged. |
| `tests/test_projection_three_systems_renderer.py` | modified | 11 new focused recalibration tests (`ProjectionConfidenceRecalibrationTests` × 6, `NegativeConfidenceRecalibrationTests` × 5) + 1 updated assertion in `test_happy_levels_match_score_mapping` (non-excluded happy now `negative=medium / score=0.6`). |
| `tests/test_record_02_five_state_margin_policy_output.py` | modified | 1 updated assertion in `test_confidence_evaluator_unchanged` (non-excluded `_v2_low_margin()` now `negative=medium` instead of `high`). |

## Commands run

All from `/Users/may/Desktop/stock-analyzer-main` (user-directed primary checkout).

Step 1 — git state sweep
- `git branch --show-current`
- `git status --short`
- `git log --oneline -8`
- `git diff --name-only HEAD`

Step 2 — static + focused tests + smoke
- `python3 -m py_compile services/projection_three_systems_renderer.py`
- `python3 -m pytest tests/test_projection_three_systems_renderer.py -v`
- `python3 -m pytest tests/test_record_02_five_state_margin_policy_output.py -v`
- `python3 -m pytest tests/test_record_02_display_state_summary.py -v`
- `python3 -m pytest tests/test_predict.py -v`
- `python3 -m pytest tests/test_predict_tab_confidence_three_columns.py -v`
- `python3 -m pytest tests/test_projection_entrypoint_three_systems.py -v`
- `python3 -m pytest tests/test_three_system_replay_audit_features.py -v`
- `bash scripts/check.sh`
- `rm -rf /tmp/task111_confidence_recalibration_smoke_5cases`
- `time python3 scripts/run_1005_three_system_replay.py --symbol AVGO --num-cases 5 --lookback-days 20 --output-dir /tmp/task111_confidence_recalibration_smoke_5cases`
- `python3 - <<'PY' …` (smoke distribution inspection)

## Static validation result

- `python3 -m py_compile services/projection_three_systems_renderer.py` → **PASS** (exit 0, no output).
- `bash scripts/check.sh` → **PASS** (exit 0, "All compile checks passed.").

## Focused recalibration test result

`python3 -m pytest tests/test_projection_three_systems_renderer.py -v`
→ **PASS — `28 passed in 0.04s`** (17 pre-existing + 11 new Task 110 cases).

| # | Case | Result |
|---|---|---|
| 1 | `ProjectionConfidenceRecalibrationTests::test_high_with_tail_top1_da_zhang_caps_at_medium` | ✓ `final=high + top1=大涨` capped at ≤medium; reasoning includes "尾部状态". |
| 2 | `ProjectionConfidenceRecalibrationTests::test_high_with_tail_top1_da_die_caps_at_medium` | ✓ `final=high + top1=大跌` capped at ≤medium. |
| 3 | `ProjectionConfidenceRecalibrationTests::test_high_with_non_tail_healthy_margin_no_conflict_keeps_high` | ✓ `final=high + 小涨 + margin=0.20 + no conflict` preserves `high`/`score=0.9`. |
| 4 | `ProjectionConfidenceRecalibrationTests::test_high_with_extreme_margin_downgraded` | ✓ `margin≈0.65` triggers overconfidence downgrade; reasoning includes "过度自信". |
| 5 | `ProjectionConfidenceRecalibrationTests::test_high_with_low_margin_demotes_via_healthy_high_guard` | ✓ `margin=0.03` demotes high→medium; reasoning includes "健康 high 条件未满足". |
| 6 | `ProjectionConfidenceRecalibrationTests::test_high_with_conflict_demotes_via_healthy_high_guard` | ✓ `conflict_reasons` non-empty demotes high→medium. |
| 7 | `NegativeConfidenceRecalibrationTests::test_exclude_big_up_with_enough_reasons_high_allowed` | ✓ `exclude_big_up + reasons=5` → high; reasoning mentions "exclude 大涨". |
| 8 | `NegativeConfidenceRecalibrationTests::test_exclude_big_down_benign_regime_allows_high` | ✓ benign regime + 5 reasons → high. |
| 9 | `NegativeConfidenceRecalibrationTests::test_exclude_big_down_with_high_vol_caps_at_medium` | ✓ `vol_ratio20=1.40` (1 flag) caps at medium; risks mention "误否定率". |
| 10 | `NegativeConfidenceRecalibrationTests::test_exclude_big_down_with_two_dangerous_flags_forced_low` | ✓ 3 flags (`vol≥1.30 + ret5≤-2 + pos20≤30`) → low; risks mention "急跌" / "低位". |
| 11 | `NegativeConfidenceRecalibrationTests::test_non_excluded_normal_case_is_medium_not_high` | ✓ non-excluded happy → `medium` / `score=0.6` (was `high` / `0.9`). |
| 12–28 | 17 pre-existing renderer cases (`NegativeSystemTests`, `Record02ProjectionSystemTests`, `ConfidenceEvaluatorTests`, `BuildProjectionThreeSystemsTests`) | ✓ All green; updated `test_happy_levels_match_score_mapping` now expects `negative=medium`/`score=0.6`. |

## Sibling regression results

- `tests/test_record_02_five_state_margin_policy_output.py` → **PASS — `7 passed in 0.02s`**.
  Updated `test_confidence_evaluator_unchanged` (non-excluded `_v2_low_margin()` → `negative=medium`) green; other 6 unchanged.
- `tests/test_record_02_display_state_summary.py` → **PASS — `12 passed in 0.02s`**.
  No assertion changes needed — `test_confidence_evaluator_unchanged` only checks `projection=medium` and `overall=medium`, both unchanged under recalibration.
- `tests/test_predict.py` → **PASS — `15 passed in 1.06s`**.
  `RunPredictThreeSystemsAttachmentTests`, `ProjectionThreeSystemsReentryGuardTests`, and legacy `RunPredictV2Tests` all green; assertions only check shape and `level` for degraded paths.
- `tests/test_predict_tab_confidence_three_columns.py` → **PASS — `11 passed in 1.09s`**.
  UI shape contract unchanged; A/B/C three-column rendering still pulls `level`/`score`/`reasoning`/`risks` correctly.
- `tests/test_projection_entrypoint_three_systems.py` → **PASS — `4 passed in 0.47s`**.
  Entrypoint integration intact; `confidence_evaluator` keys still `{negative_system_confidence, projection_system_confidence, overall_confidence, conflicts, reliability_warnings}`.
- `tests/test_three_system_replay_audit_features.py` → **PASS — `4 passed in 0.02s`**.
  Audit-case feature flattening unaffected.

## Total tests passed in Step 2

**81 / 81** = `28 + 7 + 12 + 15 + 11 + 4 + 4`. **0 warnings, 0 skips, 0 errors, 0 xfail / xpass / deselected.**

## Runtime smoke result

```
time python3 scripts/run_1005_three_system_replay.py \
  --symbol AVGO --num-cases 5 --lookback-days 20 \
  --output-dir /tmp/task111_confidence_recalibration_smoke_5cases
```

- 5 trading-day pairs (`2026-04-22 → 2026-04-29`).
- `total=5, completed=5, failed=0, direction_accuracy=0.25`.
- Wall time **3.95s** (user 3.71s).
- One informational log: `[INFO] No exact code matches found for 2026-04-24 with code 41443`
  / `[INFO] No near code matches found ...` — matcher's normal "no historical analogue"
  notice for that date; not a regression.

## Smoke confidence distribution

```
rows 5
failed 0
projection_confidence Counter({'low': 2, 'medium': 2, 'unknown': 1})
negative_confidence   Counter({'medium': 4, 'high': 1})
overall_confidence    Counter({'low': 3, 'medium': 1, 'unknown': 1})
```

| as_of | top1 | actual | proj | neg | overall | pos20 | vol_ratio20 | ret5 |
|---|---|---|---|---|---|---|---|---|
| 2026-04-22 | 小涨 | 小跌 | low | medium | low | 99.6 | 1.23 | 6.54 |
| 2026-04-23 | 小涨 | 小涨 | medium | high | medium | 93.3 | 1.00 | 5.39 |
| 2026-04-24 | 小涨 | 小跌 | low | medium | low | 95.3 | 1.14 | 3.99 |
| 2026-04-27 | 震荡 | 大跌 | medium | medium | low | 90.6 | 0.52 | 4.15 |
| 2026-04-28 | 大跌 | 震荡 | unknown | medium | unknown | 77.8 | 1.27 | -0.58 |

Behavioral observations consistent with the recalibration intent:

- No `projection=high` survives in this 5-case sample — the healthy-high guard, tail cap, and
  margin downgrade are pruning previously over-confident outputs.
- Only one `negative=high` (row 1, an `exclude_big_up` candidate) — the rest are `medium`,
  matching the new "non-excluded → cap at medium" rule.
- Row 4 (`top1=大跌`, tail state) produced `projection=unknown` (final_decision not ready
  in this case) rather than a misleading `high` — fail-safe degradation holds.
- Cross-system conservatism: row 3 has both `proj=medium` and `neg=medium` but `overall=low`,
  indicating the `_conflicts_from_v2` + overall downgrade chain still fires through.

## Confirmation: this is confidence-label-only

- `git diff --name-only HEAD` returns exactly the three expected paths
  (`services/projection_three_systems_renderer.py`,
  `tests/test_projection_three_systems_renderer.py`,
  `tests/test_record_02_five_state_margin_policy_output.py`).
- Within `services/projection_three_systems_renderer.py`, the diff is confined to the
  confidence helpers (`_negative_confidence_level_and_notes`, `_dangerous_down_flags`,
  `_projection_confidence_calibrate`, `build_negative_system_confidence`,
  `build_projection_system_confidence`, `build_confidence_evaluator`).
- All other functions (`build_negative_system`, `build_record_02_projection_system`,
  `_negative_excluded_states`, `_five_state_projection`, `_five_state_top1`,
  `build_overall_confidence`, `_conflicts_from_v2`, `_reliability_warnings`,
  `build_projection_three_systems`, the `_empty_*` factories) are unchanged.

## Confirmation: prediction direction / five_state probabilities / negative excluded states unchanged

- `final_direction` is read from `final_decision.final_direction` exactly as before by
  `_final_direction_value` and `build_record_02_projection_system`. The recalibration only
  reads `final_decision.final_confidence` and never writes to `final_direction`.
- `five_state_projection` probabilities come from `main_projection.state_probabilities`
  and are passed through `_five_state_projection` and `apply_five_state_margin_policy`
  without modification. The recalibrated projection-confidence path consumes
  `top1_state` and `top1_margin` derived from this distribution but does **not** alter
  the distribution.
- `negative_excluded_states` continues to be derived by the unchanged
  `_negative_excluded_states(triggered_rule)` helper used inside `build_negative_system`.
  The new `_dangerous_down_flags` helper reads `feature_snapshot` only and never writes
  to or reorders the excluded-state set.

## Protected files untouched

- `.claude/handoffs/task_089_post_pr_cleanup.md` — listed only as pre-existing untracked;
  `git diff --name-only HEAD -- .claude/handoffs/task_089_post_pr_cleanup.md` empty.
  Not opened by any tool in Task 110/111.
- `.claude/worktrees/` — listed only as pre-existing untracked directory;
  `git diff --name-only HEAD -- .claude/worktrees/` empty. Tester pass operated from
  `/Users/may/Desktop/stock-analyzer-main`, not from inside the worktree.
- `logs/historical_training/three_system_1005/` — pre-existing untracked artifact
  directory; no `M` entry. Smoke replay output written to `/tmp/...` instead of this path.

## Coverage gaps / caveats

- The full repo-wide pytest run flagged 13 pre-existing failures unrelated to the
  confidence_evaluator (UI app-tests, data workbench, history tab, projection
  orchestrator, research-loop UI). All 13 reproduce on `main` without the Task 110 diff
  (verified by `git stash → pytest → git stash pop` during Task 110); none import
  `confidence_evaluator` / `build_confidence_evaluator` / related symbols. Two additional
  collection import errors (`tests/test_ai_summary.py` missing `dotenv`,
  `tests/test_dual_price_track.py` missing `data_quality_check` module) are environment
  issues that pre-date this task.
- The 5-case smoke sample is intentionally small. The recalibration's per-rule behavior
  is comprehensively covered by the 11 deterministic focused tests; the smoke run
  serves only as a runtime-shape sanity check that real `run_projection_v2` outputs
  flow cleanly through the new helpers.
- `ScheduleWakeup`/replay-driver behavior, target_date wiring, and replay date selection
  were explicitly out of scope and are unchanged.

## Verdict

**PASS** — Task 110 confidence_evaluator recalibration validates clean.

- Static validation: PASS (`py_compile services/projection_three_systems_renderer.py` clean,
  `bash scripts/check.sh` clean).
- Focused recalibration tests: PASS (`28/28`, incl. 11 new Task 110 cases).
- Sibling regression: PASS (`7/7 + 12/12 + 15/15 + 11/11 + 4/4 + 4/4 = 53/53`).
- Total: **81 / 81** focused + regression cases green; **0 warnings, 0 skips, 0 failures.**
- Runtime smoke: 5/5 completed, 0 failed, ~3.95 s wall — confidence distribution shifted
  away from auto-`high` exactly as Task 106 prescribed.
- Scope guards: every forbidden file untouched (`git diff --name-only HEAD` returns
  exactly the three Task 110 deliverables). `final_direction`, `five_state_projection`
  probabilities, `negative_excluded_states`, target-date wiring, replay date selection,
  and UI shape all bit-for-bit unchanged. Protected paths
  (`.claude/handoffs/task_089_post_pr_cleanup.md`, `.claude/worktrees/`,
  `logs/historical_training/three_system_1005/`) untouched.

Recommendation: Task 110 is ready to mark `done` (tester).

## Status

- Task 110: `done` (tester verdict).
- Task 106: still `done` (calibration source). The recalibration closes the
  Task 106 follow-up loop: tail-state cap, overconfidence margin downgrade, and
  exclude_big_down regime guard are now production-shipped; `negative_confidence_level`
  flatness for non-excluded paths is removed.
