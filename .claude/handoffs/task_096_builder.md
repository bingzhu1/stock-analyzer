# Task 096 — builder handoff

## Context scanned

- `tasks/STATUS.md`
- `tasks/096_wire_contradiction_card_ui_into_predict_tab.md`
  (this task)
- `ui/predict_tab.py` (1163 → 1180 lines after edit; layer-3 body
  gained one call line, the import block gained 4 lines for the
  expanded import + new import, and the wrapper-helper block
  gained 14 lines for `_render_contradiction_card`)
- `ui/big_up_contradiction_card.py` (read for renderer contract;
  not edited)
- `services/big_up_contradiction_card.py` (read for adapter +
  builder contract; not edited)
- `tests/test_predict_tab_exclusion_reliability_live_wiring.py`
  (read as a pattern reference; not edited)
- `tests/test_predict_tab_exclusion_reliability_review.py`
  (PR-E wrapper test — read for context, not edited)

`main` HEAD: `76e2560` (post-Task-095 sync). Two protected /
deferred untracked entries pre-builder; this builder pass adds three
new artifacts (the new wiring test, the task doc, and this handoff)
plus modifies two tracked files (`ui/predict_tab.py` and
`tasks/STATUS.md`).

## Changed files

- `ui/predict_tab.py` (modified — additive only):
  - The single `from services.big_up_contradiction_card import
    build_contradiction_card_payload` line was expanded into a
    parenthesized form that also imports `build_contradiction_card`.
  - One new import line: `from ui.big_up_contradiction_card import
    render_contradiction_card`.
  - One new private helper `_render_contradiction_card(predict_result:
    dict | None) -> None` placed immediately after the existing
    PR-E helper `_render_exclusion_reliability_review`. Same
    plumbing pattern: extract `prediction_date` from
    `analysis_date` (with `prediction_date` fallback), build the
    row via `build_contradiction_card_payload`, build the structured
    payload via `build_contradiction_card`, then call
    `render_contradiction_card`.
  - One new call site inside `_render_layer3_evidence`, immediately
    after the existing PR-F call to
    `_render_exclusion_reliability_review(predict_result)` and
    before the raw-JSON debug expander.
  - **Zero existing lines deleted; zero existing function bodies
    modified beyond the targeted insertions.**
- `tests/test_predict_tab_contradiction_card_wiring.py` (new — 2
  focused tests: wrapper plumbing + live wiring).
- `tasks/096_wire_contradiction_card_ui_into_predict_tab.md` (new).
- `.claude/handoffs/task_096_builder.md` (this file, new).
- `tasks/STATUS.md` (updated — added 096 to canonical mapping +
  new row at the bottom).

Restored / preserved untracked (not staged in this builder pass):

- `.claude/handoffs/task_089_post_pr_cleanup.md`
- `.claude/worktrees/`

## Implementation summary

### `ui/predict_tab.py`

Three small additive edits, all in pure-presentation territory.
No existing function modified.

1. **Import block** — expanded the single-line import for
   `build_contradiction_card_payload` into a parenthesized
   multi-line form that also imports `build_contradiction_card`.
   Added a new import line for `render_contradiction_card` from
   `ui.big_up_contradiction_card`.
2. **`_render_layer3_evidence` body** — single new line:
   `_render_contradiction_card(predict_result)`, sitting between
   the existing PR-F call to
   `_render_exclusion_reliability_review(predict_result)` and the
   raw-JSON debug expander.
3. **Wrapper helper** — new private function placed immediately
   after `_render_exclusion_reliability_review`:

   ```python
   def _render_contradiction_card(predict_result: dict | None) -> None:
       prediction_date = None
       if isinstance(predict_result, dict):
           prediction_date = (
               predict_result.get("analysis_date")
               or predict_result.get("prediction_date")
           )
       row = build_contradiction_card_payload(
           predict_result,
           prediction_date=prediction_date,
       )
       payload = build_contradiction_card(row)
       render_contradiction_card(payload)
   ```

   Same pattern as `_render_exclusion_reliability_review`: extract
   the prediction date, adapt to a row, then run the type-specific
   pipeline. The wrapper itself emits zero `st.*` calls — visible
   output is the renderer's responsibility.

### `tests/test_predict_tab_contradiction_card_wiring.py`

Two focused cases using a minimal fake streamlit (no AppTest
harness):

1. **`test_contradiction_card_wrapper_chains_payload_to_renderer`** —
   monkeypatches `predict_tab.build_contradiction_card_payload`,
   `predict_tab.build_contradiction_card`,
   `predict_tab.render_contradiction_card`, and `predict_tab.st`.
   Calls `_render_contradiction_card(predict_result)` with
   `{"analysis_date": "2026-04-25", "predicted_state": "震荡",
   "forced_excluded_states": "大涨|大跌"}`. Asserts:
   - Adapter receives the original `predict_result` object
     (`is`-identical, no copy).
   - Adapter receives `prediction_date == "2026-04-25"` extracted
     from `analysis_date`.
   - Builder receives the row produced by the adapter
     (`{"row": "synthetic"}`).
   - Renderer receives the payload produced by the builder
     (`{"payload": "synthetic"}`).
   - Wrapper emits **no direct `st.caption`** calls.
   - Input dict is unmutated (deep-equality with deepcopy
     snapshot).
2. **`test_layer3_evidence_invokes_both_wrappers_in_order`** —
   monkeypatches `predict_tab._render_exclusion_reliability_review`,
   `predict_tab._render_contradiction_card`, and `predict_tab.st`
   (an `OrderingFakeSt` that records each `expander(...)` call
   into a shared event log). Calls
   `_render_layer3_evidence(predict_result, {}, None)`. Asserts:
   - Each wrapper invoked **exactly once**.
   - Each wrapper received the same `predict_result` object
     (`is`-identical to the input).
   - Event ordering:
     `expander:生成 AI 推演总结（可选）` → `pr_f_wrapper` →
     `pr_g_wrapper` → `expander:推演原始数据（调试用）`.

The fake never invokes the real streamlit module. Test file runs
in ~1.0 s wall clock.

## Test results

All from `/Users/may/Desktop/stock-analyzer-main` on local `main`
(commit `76e2560`):

| Command | Result |
|---|---|
| `python3 -m py_compile ui/predict_tab.py` | **PASS** (exit 0, no output) |
| `python3 -m pytest tests/test_predict_tab_contradiction_card_wiring.py -v` | **PASS — 2/2 in 1.02s** (NEW) |
| `python3 -m pytest tests/test_predict_tab_exclusion_reliability_live_wiring.py -v` | **PASS — 2/2 in 0.73s** (PR-F regression) |
| `python3 -m pytest tests/test_predict_tab_exclusion_reliability_review.py -v` | **PASS — 1/1 in 0.65s** (PR-E wrapper) |
| `python3 -m pytest tests/test_big_up_contradiction_card.py -v` | **PASS — 31/31 in 0.12s** (PR-C suite) |
| `python3 -m pytest tests/test_exclusion_reliability_review.py -v` | **PASS — 5/5 in 0.02s** (services) |
| `python3 -m pytest tests/test_exclusion_reliability_review_ui.py -v` | **PASS — 2/2 in 0.11s** (UI) |
| `python3 -m pytest tests/test_predict_summary.py -v` | **PASS — 5/5 in 0.69s** (predict_tab regression) |
| `bash scripts/check.sh` | **PASS — `All compile checks passed.`** |

Total: **48/48 tests passed across 7 pytest invocations.** No
warnings, no skips, no errors. No iteration on test design — all
assertions passed on the first run.

## No-business-logic confirmation

Touched in this builder pass:

- `ui/predict_tab.py` — pure additive edits (expanded import + 1
  new import + 1 new helper + 1 new call site). Zero deletions,
  zero modifications of existing logic.
- `tests/test_predict_tab_contradiction_card_wiring.py` (new test
  file)
- `tasks/096_wire_contradiction_card_ui_into_predict_tab.md`
  (task doc)
- `.claude/handoffs/task_096_builder.md` (this handoff)
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
- `ui/big_up_contradiction_card.py`
- `ui/exclusion_reliability_review.py`
- `app.py`, `predict.py`, `data_fetcher.py`, `feature_builder.py`,
  `encoder.py`, `scripts/*`
- `tests/test_predict_tab_exclusion_reliability_review.py`
- `tests/test_predict_tab_exclusion_reliability_live_wiring.py`
- `tests/test_big_up_contradiction_card.py`
- `tests/test_exclusion_reliability_review.py`,
  `tests/test_exclusion_reliability_review_ui.py`
- `tests/test_predict_summary.py`
- `tests/test_evidence_trace.py`
- `.claude/handoffs/task_089_post_pr_cleanup.md`
- `.claude/worktrees/`

## Remaining risks / follow-ups

1. **Section is always content-emitting on neutral predictions.**
   `build_contradiction_card` always returns `show_card=True`,
   and `render_contradiction_card` always renders at least the
   variant banner (`variant=info`, "未触发大涨否定，无需矛盾检测。")
   when no big-up exclusion is present. This adds a small
   always-visible banner to the layer-3 section. Matches the
   PR-C-era contract (the renderer's own
   `test_no_big_up_exclusion_shows_info_only` confirms this is
   intentional). If product wants the section gated on
   `has_big_up_exclusion=True`, that's a tiny follow-up — but
   would diverge from the renderer's documented behaviour.
2. **Adapter runs twice per layer-3 render.** Both
   `_render_exclusion_reliability_review` and
   `_render_contradiction_card` independently call
   `build_contradiction_card_payload(predict_result, ...)`. The
   adapter is pure-read and idempotent (a curated dict copy with
   ~30 key lookups), so the perf cost is negligible. If we ever
   add a third card on the same row, refactor to a shared
   `_build_predict_row(predict_result)` helper. For now,
   symmetry with PR-F's design wins.
3. **No live AppTest coverage of the full `render_predict_tab`
   flow.** The new wiring test exercises `_render_layer3_evidence`
   directly with a fake streamlit. End-to-end AppTest is still
   blocked by the pre-existing
   `tests/test_research_loop_ui_apptest.py` failures
   (`fake_run_predict` test-double doesn't accept `pre_briefing`).
   Predates this task — not a regression.
4. **Cross-task regression coverage gap.** Full 072–087 cross-task
   regression cannot run in this workspace (same gap as the
   prior 084–087 / 090 / 092 / 094 chains). Reviewer should
   verify on a workspace with the full corpus before merging if
   possible.
5. **Streamlit dependency at import time.** Same caveat as PR-E /
   PR-F: `from ui import predict_tab` transitively pulls in
   `streamlit` and `pandas`. Local environment is fine — the
   48/48 pytest run confirms it.

## Status

- Task 096: `in-review` (builder complete; reviewer + tester
  follow-ups expected before PR-G is opened on the
  `pr-g-wire-contradiction-card-ui-into-predict-tab` branch).
