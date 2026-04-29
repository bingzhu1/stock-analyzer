# Task 104 — tester handoff

## Context scanned

- `.claude/CLAUDE.md`
- `.claude/PROJECT_STATUS.md`
- `.claude/CHECKLIST.md`
- `tasks/STATUS.md`
- `.claude/handoffs/task_103_tester.md` (deferred-wiring follow-up
  marker that this task closes)
- `.claude/handoffs/task_096_tester.md` (template + scope-guard
  reference)
- `predict.py` (read-only — to confirm the new private helper
  `_build_projection_three_systems_attachment` and the two call
  sites: `_missing_scan_result` and the happy-path `result` dict
  inside `run_predict`)
- `tests/test_predict.py` (read-only — to confirm the new
  `RunPredictThreeSystemsAttachmentTests` class with three cases
  and that the existing two `RunPredictV2Tests` cases are
  preserved)
- `services/projection_entrypoint.py` (read-only — to confirm
  `_degraded_projection_three_systems` is still the canonical
  degraded shape and remains exported for predict.py to lazy-import)
- `services/projection_three_systems_renderer.py` (read-only —
  to confirm `build_projection_three_systems` and the
  `confidence_evaluator` shape consumed by Task 103's UI)
- `services/projection_orchestrator_v2.py` (read-only — to
  confirm `run_projection_v2` signature/defaults match the call
  predict.py now makes)
- `ui/predict_tab.py` (read-only — to confirm the Task 103
  helper `_render_confidence_three_columns` reads
  `predict_result["projection_three_systems"]["confidence_evaluator"]`
  and will now hit the populated branch)

## Repository state at start of testing

- Branch: `claude/musing-mclaren-fd8a4f`
- HEAD: `de62025` (`Merge pull request #8 from
  bingzhu1/pr-g-wire-contradiction-card-ui-into-predict-tab`)
- Modified tracked files (four): `predict.py`, `tasks/STATUS.md`,
  `tests/test_predict.py`, `ui/predict_tab.py`
- Untracked files (two): `.claude/handoffs/task_103_tester.md`,
  `tests/test_predict_tab_confidence_three_columns.py`
- Task 104 deltas vs. Task 103 closeout: `predict.py` and
  `tests/test_predict.py` are newly modified
- No services / orchestrator / replay / final-decision / app file
  modified by Task 104 (`git diff --name-only HEAD -- services/
  app.py` returned empty)
- Protected paths untouched: `.claude/worktrees/`,
  `.claude/handoffs/task_089_post_pr_cleanup.md` (both empty
  under `git diff --name-only HEAD`)

## Changed files (Task 104 deliverables)

| Path | Status | Purpose |
|---|---|---|
| `predict.py` | modified | New private helper `_build_projection_three_systems_attachment(symbol, reason=None)` lazily imports `services.projection_orchestrator_v2.run_projection_v2` + `services.projection_three_systems_renderer.build_projection_three_systems` (lazy to avoid the existing `services.projection_orchestrator → predict.run_predict` import cycle); falls back to `services.projection_entrypoint._degraded_projection_three_systems` on any exception or when called with an explicit `reason`. `run_predict` happy path now attaches `projection_three_systems` to its return dict; `_missing_scan_result` attaches a degraded payload with `reason="scan_result missing"` so the contract is consistent across all paths. |
| `tests/test_predict.py` | modified | Adds class `RunPredictThreeSystemsAttachmentTests` with 3 cases (happy attach via stubbed v2_raw, RuntimeError-degrade, missing-scan degraded path). Existing 9 tests unchanged. |

## Commands run

All from
`/Users/may/Desktop/stock-analyzer-main/.claude/worktrees/musing-mclaren-fd8a4f`,
on branch `claude/musing-mclaren-fd8a4f`.

Step 1 — git state sweep

- `git branch --show-current`
- `git status --short`
- `git log --oneline -5`
- `git diff --name-only HEAD`
- `git ls-files --others --exclude-standard`
- `git diff --name-only HEAD -- services/ app.py`
- `git diff --name-only HEAD -- .claude/worktrees/
  .claude/handoffs/task_089_post_pr_cleanup.md`

Step 2 — static + focused tests

- `python3 -m py_compile predict.py ui/predict_tab.py`
- `python3 -m pytest tests/test_predict.py -v`
- `python3 -m pytest tests/test_predict_tab_confidence_three_columns.py -v`
- `python3 -m pytest tests/test_projection_entrypoint_three_systems.py -v`
- `python3 -m pytest tests/test_projection_three_systems_renderer.py -v`
- `python3 -m pytest tests/test_predict_summary.py -v`
- `python3 -m pytest tests/test_predict_tab_exclusion_reliability_live_wiring.py -v`
- `python3 -m pytest tests/test_predict_tab_contradiction_card_wiring.py -v`
- `python3 -m pytest tests/test_big_up_contradiction_card.py -v`
- `bash scripts/check.sh`

## Static validation result

- `python3 -m py_compile predict.py ui/predict_tab.py` → **PASS**
  (exit 0, no output for either file).
- `bash scripts/check.sh` → **PASS** (exit 0). Output:
  `All compile checks passed.` Every module in the unified
  compile gate (incl. `predict.py` and `ui/predict_tab.py`)
  compiles clean.

## Focused predict.py test result

`python3 -m pytest tests/test_predict.py -v`
→ **PASS — `12 passed in 0.72s`** (3 new + 9 existing).

| # | Case | Result |
|---|---|---|
| 1 | `RunPredictThreeSystemsAttachmentTests::test_run_predict_attaches_projection_three_systems` | ✓ Stubbed v2_raw flows through to populated `confidence_evaluator` with all 5 keys (`negative_system_confidence` / `projection_system_confidence` / `overall_confidence` / `conflicts` / `reliability_warnings`); legacy `final_bias` / `primary_projection.status` / `final_projection.status` intact |
| 2 | `RunPredictThreeSystemsAttachmentTests::test_run_predict_projection_three_systems_degrades_when_v2_raises` | ✓ `services.projection_orchestrator_v2.run_projection_v2` raising `RuntimeError` produces a degraded payload (`ready=False`, all `*_confidence.level == "unknown"`, all `score is None`); legacy answer untouched |
| 3 | `RunPredictThreeSystemsAttachmentTests::test_run_predict_missing_scan_attaches_degraded_three_systems` | ✓ `run_predict(None, ...)` returns the canonical degraded envelope with the 5-key `confidence_evaluator` and `overall_confidence.level == "unknown"` |
| 4–12 | Pre-existing `PrimaryProjectionTests` / `PeerAdjustmentTests` / `FinalProjectionTests` / `RunPredictV2Tests` cases | ✓ All 9 still green — Task 104 attachment did not disturb the legacy two-step path |

## Three-column UI regression result

`python3 -m pytest tests/test_predict_tab_confidence_three_columns.py -v`
→ **PASS — `11 passed in 0.83s`.** Task 103 helper still green;
both populated and fallback branches still covered. (Task 103
fixtures supply synthetic `projection_three_systems` directly,
so the suite does not depend on whether `run_predict` attaches
the key.)

## projection_entrypoint regression result

`python3 -m pytest tests/test_projection_entrypoint_three_systems.py -v`
→ **PASS — `4 passed in 0.41s`.** The duplicate three-systems
wiring inside `run_predict` does NOT disturb
`run_projection_entrypoint`'s independent attachment of
`projection_three_systems`. `EntrypointThreeSystemsIntegrationTests`
(legacy fields unchanged, v2 unready handling,
narrative-coexistence, renderer-raise degraded path) all green.

## projection_three_systems_renderer regression result

`python3 -m pytest tests/test_projection_three_systems_renderer.py -v`
→ **PASS — `17 passed in 0.02s`.** Full renderer suite green:
`NegativeSystemTests` (4), `Record02ProjectionSystemTests` (3),
`ConfidenceEvaluatorTests` (5),
`BuildProjectionThreeSystemsTests` (5). Renderer not modified
by Task 104.

## predict_summary regression result

`python3 -m pytest tests/test_predict_summary.py -v`
→ **PASS — `5 passed in 0.71s`.** Readable summary builder +
`render_readable_predict_summary` path unaffected by the new
`projection_three_systems` field on `predict_result`.

## PR-F / PR-G / PR-C regression results

- **PR-F** (`tests/test_predict_tab_exclusion_reliability_live_wiring.py`)
  → **PASS — `2 passed in 0.74s`** (invocation count + ordering
  contract still green).
- **PR-G** (`tests/test_predict_tab_contradiction_card_wiring.py`)
  → **PASS — `2 passed in 0.67s`** (wrapper plumbing + live
  wiring still green; AI → PR-F → PR-G → raw-JSON ordering
  preserved).
- **PR-C** (`tests/test_big_up_contradiction_card.py`)
  → **PASS — `31 passed in 0.12s`** (all §1–§9 base, §14–§19
  cache-health, big-down tail integration, 3 UI cases, plus
  supplementary cases — all stable).

## Total tests passed in Step 2

**84 / 84** = `12 + 11 + 4 + 17 + 5 + 2 + 2 + 31`. No warnings,
no skips, no errors, no xfail / xpass / deselected. None of the
eight pytest invocations printed a warning footer.

## Confirmation: this is data-wiring only

- All edits live in `predict.py` (the wiring point) and
  `tests/test_predict.py` (its tests).
- `git diff --name-only HEAD -- services/ app.py` returned
  **empty**. No prediction-business, scanner, matcher, encoder,
  feature_builder, final-decision, replay, orchestrator,
  rule-pool, or app-shell code modified.
- The new helper is **purely additive**: it never mutates
  `final_projection`, `final_bias`, `final_confidence`,
  `primary_projection`, `peer_adjustment`, or any rule output.
  If `run_projection_v2` raises, the legacy two-step prediction
  still returns its canonical answer — only the new
  `projection_three_systems` block degrades.
- All non-stdlib imports inside the helper are **function-local
  (lazy)** so module-load order is unchanged. `predict.py`
  retains its existing import surface; the runtime cycle with
  `services.projection_orchestrator → predict.run_predict` is
  resolved by being inside the function body, not at module
  load.

## Confirmation: run_predict now attaches projection_three_systems

`predict.run_predict` now returns `result["projection_three_systems"]`
on every code path:

- **Happy path** (`scan_result` present, v2 healthy):
  `kind="projection_three_systems"`, `ready=True`,
  `confidence_evaluator` carries real
  `projection_system_confidence.level` (mirrors
  `final_decision.final_confidence`), real
  `negative_system_confidence.level` (derived from
  exclusion-layer evidence count + feature completeness), real
  `overall_confidence.level` (conservative combine + conflict
  downgrade). The Task 103 three-column UI can therefore render
  populated A / B / C data — verified by case 1 of
  `RunPredictThreeSystemsAttachmentTests`.
- **v2 exception path**: degraded envelope with
  `level="unknown"` for all three sub-blocks and
  `score=None` for each; legacy answer (`final_bias`,
  `primary_projection.status`, `final_projection.status`) is
  unaffected — verified by case 2.
- **Missing-scan path**: degraded envelope attached via the
  same `_degraded_projection_three_systems` factory used by
  `services.projection_entrypoint` so the shape is bit-for-bit
  identical regardless of which entrypoint produced it —
  verified by case 3.

## Performance risk note

`run_predict` now invokes `run_projection_v2(symbol=symbol,
lookback_days=20)` **once per call** on the happy path. v2 reads
CSVs and runs the orchestrator chain (primary 20-day analysis,
peer adjustment, historical probability, final decision,
preflight, exclusion layer, main projection layer, consistency
layer), so this is real I/O.

- For interactive use in `ui/predict_tab.py`, this is acceptable
  — it is the same work `run_projection_entrypoint` already
  performs on the command-bar path, just relocated inside
  `run_predict` so a single `predict_result` carries all data
  the new three-column UI needs. No double-execution of v2
  occurs in the predict-tab flow because the predict tab does
  not also call `run_projection_entrypoint`.
- For batch / replay scripts that call `run_predict` thousands
  of times (e.g.
  `scripts/run_e2e_loop.py`,
  `services.projection_orchestrator._build_predict_result`),
  this represents a per-call increase in work. Two follow-up
  options exist if real-world batch latency regresses:
  1. Caller-level memoization keyed by
     `(symbol, target_date, lookback_days)`.
  2. An opt-in flag on `run_predict` to skip the
     `projection_three_systems` attachment when the caller does
     not need it (the helper already returns the cheap degraded
     payload immediately on `reason=...`).
  Both belong in a separate task — out of scope for Task 104,
  which is data-wiring only.
- The degraded path costs **zero** v2 invocations (only a tiny
  factory call), so failure handling never amplifies the
  regression.

## Confirmation: protected files untouched

- `.claude/handoffs/task_089_post_pr_cleanup.md` —
  `git diff --name-only HEAD -- .claude/handoffs/task_089_post_pr_cleanup.md`
  returned empty. Not opened by any tool in this tester pass.
- `.claude/worktrees/` —
  `git diff --name-only HEAD -- .claude/worktrees/` returned
  empty. Listed only as the worktree-local root in
  `git status --short` (none of its sub-paths added or modified).
  No reads, edits, or writes inside any worktree directory in
  this tester pass.

## Confirmation: services / forbidden paths untouched

`git diff --name-only HEAD -- services/ app.py` returned
**empty**. The full guarded set is therefore trivially clean:

- `services/projection_three_systems_renderer.py`
- `services/projection_orchestrator_v2.py`
- `services/projection_entrypoint.py`
- `services/projection_orchestrator.py`
- `services/final_decision.py`
- `services/exclusion_layer.py`
- `services/main_projection_layer.py`
- `services/historical_probability.py`
- `services/peer_adjustment.py`
- `services/predict_summary.py`
- `services/projection_chain_contract.py`
- `services/consistency_layer.py`
- `services/primary_20day_analysis.py`
- `services/projection_rule_preflight.py`
- `services/big_up_contradiction_card.py`
- `services/big_down_tail_warning.py`
- `services/anti_false_exclusion_audit.py`
- `services/exclusion_reliability_review.py`
- `ui/big_up_contradiction_card.py`
- `ui/exclusion_reliability_review.py`
- `app.py`, `data_fetcher.py`, `feature_builder.py`,
  `encoder.py`, `matcher.py`, `scanner.py`

`git diff --name-only HEAD` cross-check confirms the only
tracked modifications anywhere in the repository are
`predict.py` + `tasks/STATUS.md` + `tests/test_predict.py` +
`ui/predict_tab.py`; the only untracked additions are
`.claude/handoffs/task_103_tester.md` +
`tests/test_predict_tab_confidence_three_columns.py`. After
this handoff lands and `tasks/STATUS.md` is updated, one more
file joins the untracked set
(`.claude/handoffs/task_104_tester.md`) — explicitly allowed.

## Coverage gaps / caveats

- The Task 103 fallback branch in
  `_render_confidence_three_columns` is now reached only on
  exotic call paths (`None predict_result`, fixtures bypassing
  `run_predict`). It is still covered by tests and intentionally
  kept — removing it would be a separate cleanup task.
- `tests/test_predict.py` patches v2 via direct module-attribute
  swap rather than `unittest.mock.patch`; both new patching
  cases use `try / finally` to restore. This matches the
  existing test patterns in this repo and avoids
  circular-import-during-import edge cases. A test failure
  mid-swap could leak module state, but each test is
  short-lived and `finally` is unconditional.
- Full 072–087 cross-task regression was not run because this
  workspace does not contain the prior Task 072–083 test chain.
  Same caveat as the 084–087 / 090 / 092 / 094 / 096 / 103
  rounds — not a regression introduced by Task 104.
- Pre-existing failures in
  `tests/test_research_loop_ui_apptest.py`,
  `tests/test_evidence_trace.py`, and the
  `tests/test_ai_summary.py` collection import error are
  **unchanged** by this task. They predate it.
- Task 103's fixture `_three_systems_payload` was authored with
  Task 104's exact populated shape in mind; the cross-task
  contract has now been verified end-to-end (Task 103 UI suite
  + Task 104 attachment suite both pass against the same shape
  produced by `services.projection_three_systems_renderer.
  build_projection_three_systems`).

## Verdict

**PASS** — all of Steps 1–2 passed.

- Static validation: PASS (`py_compile predict.py
  ui/predict_tab.py` clean, `bash scripts/check.sh` clean).
- Focused predict.py tests: PASS (`12/12`, incl. 3 new Task 104
  cases).
- Three-column UI regression: PASS (`11/11`).
- projection_entrypoint regression: PASS (`4/4`).
- projection_three_systems_renderer regression: PASS (`17/17`).
- predict_summary regression: PASS (`5/5`).
- PR-F regression: PASS (`2/2`).
- PR-G regression: PASS (`2/2`).
- PR-C regression: PASS (`31/31`).
- Total: **84 / 84** focused + regression cases green; 0
  warnings, 0 skips, 0 failures.
- Scope guards: every forbidden file untouched
  (`git diff --name-only HEAD -- services/ app.py` empty);
  protected `task_089_post_pr_cleanup.md` and
  `.claude/worktrees/` unchanged; only `predict.py` and
  `tests/test_predict.py` modified for the implementation;
  this tester pass adds `.claude/handoffs/task_104_tester.md`
  and the Task 104 row in `tasks/STATUS.md`.
- Data-wiring boundary respected: no business logic, no
  confidence-algorithm changes, no replay-logic changes, no
  final-decision-rule changes.
- Task 103 three-column UI now reads populated
  `projection_three_systems` from the live `run_predict` path —
  the deferred wiring flagged in Task 103's tester report is
  closed.

Recommendation: Task 104 is ready to mark `done` (tester).
Performance follow-up (caller-level memoization for batch users
of `run_predict`) is **optional** and out of scope; flag it as
a low-priority track-and-watch rather than a blocker.

## Status

- Task 104: `done` (tester verdict).
- Task 103: still `done` (closeout from prior round). The
  fallback branch noted in
  `.claude/handoffs/task_103_tester.md` is now exercised only
  in defensive paths; the live predict tab consumes the
  populated branch produced by Task 104.
