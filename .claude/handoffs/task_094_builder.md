# Task 094 — builder handoff

## Context scanned

- `tasks/STATUS.md`
- `tasks/094_wire_exclusion_reliability_review_into_predict_tab.md`
  (this task)
- `ui/predict_tab.py` (1161 → 1163 lines after edit; only the
  `_render_layer3_evidence` body changed by inserting one call)
- `tests/test_predict_tab_exclusion_reliability_review.py` (PR-E
  wrapper test — read for context, not edited)
- `tests/test_evidence_trace.py` (read to confirm no change required)
- `tests/test_predict_summary.py` (read to confirm no change required)
- `services/big_up_contradiction_card.py` (read for adapter contract;
  not edited)
- `ui/exclusion_reliability_review.py` (read for renderer contract;
  not edited)

`main` HEAD: `a55601c` (post-Task-093 sync). Two protected / deferred
untracked entries pre-builder; this builder pass adds three new
artifacts (the new live-wiring test, the task doc, and this handoff)
plus modifies two tracked files (`ui/predict_tab.py` and
`tasks/STATUS.md`).

## Changed files

- `ui/predict_tab.py` (modified — single 2-line insertion in
  `_render_layer3_evidence`: blank line + call to
  `_render_exclusion_reliability_review(predict_result)` between the
  AI-summary expander and the raw-JSON debug expander; no existing
  function modified)
- `tests/test_predict_tab_exclusion_reliability_live_wiring.py`
  (new — 2 focused tests: presence + ordering)
- `tasks/094_wire_exclusion_reliability_review_into_predict_tab.md`
  (new)
- `.claude/handoffs/task_094_builder.md` (this file, new)
- `tasks/STATUS.md` (updated — added 094 to canonical mapping + new
  row at the bottom)

Restored / preserved untracked (not staged in this builder pass):

- `.claude/handoffs/task_089_post_pr_cleanup.md`
- `.claude/worktrees/`

`git diff --stat HEAD` (excluding untracked files):

```
 ui/predict_tab.py                                  |  2 ++
 tasks/STATUS.md                                    |  2 ++
 2 files changed, 4 insertions(+)
```

(Plus the new test, task doc, and handoff which appear as new
untracked files in `git status` until staged.)

## Implementation summary

### `ui/predict_tab.py`

Inserted two lines (one blank + one call) inside
`_render_layer3_evidence`, between the existing AI-summary expander
and the raw-JSON debug expander:

```python
    # AI projection summary (optional, triggered by button)
    st.markdown("")
    with st.expander("生成 AI 推演总结（可选）"):
        _render_projection_ai_summary_entry_compact(predict_result, scan_result, research_result)

    _render_exclusion_reliability_review(predict_result)        # ← NEW

    # Raw JSON (collapsed)
    with st.expander("推演原始数据（调试用）"):
        st.json(predict_result)
```

Behaviour:

- `predict_result` is the same dict held by `render_predict_tab` and
  passed into `_render_layer3_evidence`. The wrapper receives it
  unchanged.
- `_render_exclusion_reliability_review` is the PR-E helper at line
  1078 of the same module — `from … import …` is unnecessary because
  it's already in the predict_tab module.
- The wrapper internally calls `build_contradiction_card_payload` →
  `render_exclusion_reliability_review_for_row`. The renderer's own
  `if not payload.get("has_exclusion_review"): return` guard keeps
  the section silent on predictions without a forced exclusion.
- Zero existing lines modified. Pure additive 2-line insertion.

### `tests/test_predict_tab_exclusion_reliability_live_wiring.py`

New test file with two focused cases:

1. `test_layer3_evidence_invokes_exclusion_reliability_review_once`
   — monkeypatches `predict_tab.st` (a minimal `FakeStreamlit` that
   records `markdown` / `caption` / `write` / `json` / `expander`
   calls and provides `session_state = {}` / `button` returning
   `False`) and `predict_tab._render_exclusion_reliability_review`
   (a recorder), then calls
   `predict_tab._render_layer3_evidence(predict_result, scan_result, None)`
   with a representative `predict_result`. Asserts:
   - the wrapper is invoked **exactly once**;
   - the wrapper receives the **same object** (`is`-identical) as
     was passed into `_render_layer3_evidence`;
   - both surrounding expanders ("生成 AI 推演总结（可选）" and
     "推演原始数据（调试用）") are rendered.
2. `test_wrapper_call_sits_between_ai_expander_and_raw_json_expander`
   — extends the fake to record an event on every `expander(...)` /
   wrapper call, then verifies ordering:
   `expander:生成 AI 推演总结（可选）` → `wrapper` →
   `expander:推演原始数据（调试用）`.

The fake never invokes the real streamlit module. No AppTest harness
required. Runs in ≤ 1s.

## Test results

All from `/Users/may/Desktop/stock-analyzer-main` on local `main`
(commit `a55601c`):

- `python3 -m py_compile ui/predict_tab.py` → **PASS** (exit 0).
- `python3 -m pytest tests/test_predict_tab_exclusion_reliability_live_wiring.py -v`
  → **PASS — `2/2`** (after a one-iteration fix: the FakeStreamlit
  needed `session_state = {}` because `_render_projection_ai_summary_entry_compact`
  reads it post-button-check; production code unchanged).
- `python3 -m pytest tests/test_predict_tab_exclusion_reliability_review.py -v`
  → **PASS — `1/1`** (PR-E wrapper test still green).
- `python3 -m pytest tests/test_big_up_contradiction_card.py -v`
  → **PASS — `31/31`** (PR-C regression intact).
- `python3 -m pytest tests/test_exclusion_reliability_review.py -v`
  → **PASS — `5/5`** (services consumer regression).
- `python3 -m pytest tests/test_exclusion_reliability_review_ui.py -v`
  → **PASS — `2/2`** (UI consumer regression).
- `python3 -m pytest tests/test_predict_summary.py -v`
  → **PASS — `5/5`** (predict_tab readable-summary regression).
- `bash scripts/check.sh` → **PASS — `All compile checks passed.`**

Total: **46/46 tests passed across 7 pytest invocations.** No
warnings, no skips, no errors.

## No-business-logic confirmation

Touched in this builder pass:

- `ui/predict_tab.py` — pure 2-line insertion (1 blank + 1 call) in
  the existing `_render_layer3_evidence` body. Zero deletions, zero
  modifications of existing logic.
- `tests/test_predict_tab_exclusion_reliability_live_wiring.py`
  (new test file)
- `tasks/094_wire_exclusion_reliability_review_into_predict_tab.md`
  (task doc)
- `.claude/handoffs/task_094_builder.md` (this handoff)
- `tasks/STATUS.md` (status row + canonical mapping)

Not touched:

- `services/big_up_contradiction_card.py`
- `services/big_down_tail_warning.py`
- `services/anti_false_exclusion_audit.py`
- `services/exclusion_reliability_review.py`
- `services/projection_three_systems_renderer.py`
- `services/main_projection_layer.py`
- `services/final_decision.py`
- `services/projection_orchestrator_v2.py`
- `services/exclusion_layer.py`
- `ui/exclusion_reliability_review.py`
- `ui/big_up_contradiction_card.py`
- `app.py`, `predict.py`, `data_fetcher.py`, `feature_builder.py`,
  `encoder.py`, `scripts/*`
- `tests/test_predict_tab_exclusion_reliability_review.py`
- `tests/test_big_up_contradiction_card.py`
- `tests/test_exclusion_reliability_review.py`,
  `tests/test_exclusion_reliability_review_ui.py`
- `tests/test_predict_summary.py`
- `tests/test_evidence_trace.py`
- `.claude/handoffs/task_089_post_pr_cleanup.md`
- `.claude/worktrees/`

## Remaining risks / follow-ups

1. **No live AppTest coverage of the full `render_predict_tab`
   flow.** The new live-wiring test exercises
   `_render_layer3_evidence` directly with a fake streamlit. A full
   AppTest run that drives `render_predict_tab` end-to-end is
   blocked by the pre-existing
   `tests/test_research_loop_ui_apptest.py` failures
   (`fake_run_predict` test-double doesn't accept the `pre_briefing`
   kwarg the production flow has been passing for some time). Those
   failures predate this task and are not regressions introduced by
   this PR. Worth a separate cleanup PR.
2. **Contradiction-card UI not wired.** `render_contradiction_card`
   from PR-C is still not invoked from the predict tab. Bundling it
   alongside the exclusion-reliability wiring was explicitly
   deferred per Step 2 scope. Potential next step.
3. **Cross-task regression coverage gap.** Full 072–087 cross-task
   regression cannot run in this workspace (same gap as the prior
   084–087 / 090 / 092 chains). Reviewer should verify on a
   workspace that has the full corpus before merging if possible.
4. **Section ordering choice.** The wrapper sits between the AI
   summary and the raw-JSON debug expander. If product wants it
   higher (e.g. above the AI summary expander) or as a top-level
   section in `render_predict_tab` instead of inside layer 3, a
   one-line move is enough — flagging in case the visual review
   prefers a different placement.
5. **Streamlit dependency at import time.** Same caveat as PR-E:
   `from ui import predict_tab` transitively pulls in `streamlit`
   and `pandas`. The local environment is fine — the 46/46 pytest
   run confirms it.

## Status

- Task 094: `in-review` (builder complete; reviewer + tester
  follow-ups expected before PR-F is opened on the
  `pr-f-wire-exclusion-reliability-review-into-predict-tab` branch).
