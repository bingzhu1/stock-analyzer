# Task 092 — builder handoff

## Context scanned

- `tasks/STATUS.md`
- `tasks/092_restore_predict_tab_exclusion_reliability_review.md` (this task)
- `tests/test_predict_tab_exclusion_reliability_review.py` (45 lines,
  1 test case — the protected restoration target)
- `services/big_up_contradiction_card.py` (already on main; added
  `build_contradiction_card_payload` here)
- `services/exclusion_reliability_review.py` (read-only — confirmed
  field names that the row consumer reads via `row.get(...)`)
- `ui/exclusion_reliability_review.py` (already on main; provides
  `render_exclusion_reliability_review_for_row(row)`)
- `ui/predict_tab.py` (1145 → 1161 lines after edit; no existing
  function modified — only imports + one new private helper added)
- `ui/big_up_contradiction_card.py` (PR-C renderer; *not* invoked
  in this task)

`main` HEAD: `97b4865` (post-Task-091 sync). Three protected /
deferred untracked entries remained pre-builder; this builder pass
adds two more (the new task doc + this handoff) and modifies two
tracked files.

## Changed files

- `services/big_up_contradiction_card.py` (modified — added
  `build_contradiction_card_payload` adapter and updated `__all__`;
  no existing function changed)
- `ui/predict_tab.py` (modified — added two imports and one new
  private helper `_render_exclusion_reliability_review`; no existing
  function changed)
- `tasks/092_restore_predict_tab_exclusion_reliability_review.md`
  (new)
- `.claude/handoffs/task_092_builder.md` (this file, new)
- `tasks/STATUS.md` (updated — added 092 entry to canonical mapping
  + new row at bottom)

Restored from protected untracked → ready to stage when PR-E is
opened (no content edits in this builder pass):

- `tests/test_predict_tab_exclusion_reliability_review.py`

Not changed (and forbidden by Step 2 scope):

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
- `app.py`
- `predict.py`
- `data_fetcher.py`
- `feature_builder.py`
- `encoder.py`
- `scripts/*`
- `tests/test_big_up_contradiction_card.py` (already on main; PR-C)
- `.claude/handoffs/task_089_post_pr_cleanup.md` (deferred to PR-D)
- `.claude/worktrees/`

`git diff --stat HEAD`:

```
 services/big_up_contradiction_card.py | 58 +++++++++++++++++++++++++++++++++++
 ui/predict_tab.py                     | 16 ++++++++++
 2 files changed, 74 insertions(+)
```

Both diffs are pure additions; zero deletions, zero modifications of
existing lines.

## Implementation summary

### `services/big_up_contradiction_card.py`

Added a single new function before the existing `__all__` and updated
`__all__` to expose it. The existing `build_contradiction_card`,
`DEFAULT_CARD_CONFIG`, and `FLAG_REASONS_CN` are untouched.

```python
def build_contradiction_card_payload(
    predict_result: dict[str, Any] | None,
    *,
    prediction_date: str | None = None,
) -> dict[str, Any]:
    ...
```

Behaviour:

- Iterates a curated allow-list of keys and copies them from
  `predict_result` into a fresh row dict when present (using
  `if key in predict_result`, so falsy-but-present values like `0`
  / `""` / `[]` are preserved).
- Never mutates `predict_result`. The output is a brand-new dict.
- Safe on `predict_result is None` — returns just
  `{"prediction_date": ..., "analysis_date": ...}` if a date was
  provided, else an empty dict.
- When `prediction_date` is non-empty, sets both
  `row["prediction_date"]` and `row["analysis_date"]` to the same
  value so downstream consumers that key on either name work.

The allow-list explicitly covers fields read by both the
`build_contradiction_card` audit row contract and the
`build_exclusion_reliability_review` row contract — including the
five-state margin metadata surfaced by Task 086 / 087, the
data-health summary surfaced by Task 088, and the
`contradiction_inputs_available` flag used by `big_down_tail_warning`.

### `ui/predict_tab.py`

Added two imports at the bottom of the existing import block:

```python
from services.big_up_contradiction_card import build_contradiction_card_payload
from ui.exclusion_reliability_review import render_exclusion_reliability_review_for_row
```

Both exposed as module-level attributes, satisfying the
monkeypatch surface required by the protected test:

```python
monkeypatch.setattr(predict_tab, "build_contradiction_card_payload", fake_build)
monkeypatch.setattr(predict_tab, "render_exclusion_reliability_review_for_row", fake_render)
```

Added one new private helper, placed after `_status_badge` and
before the main entry point `render_predict_tab`:

```python
def _render_exclusion_reliability_review(predict_result: dict | None) -> None:
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
    render_exclusion_reliability_review_for_row(row)
```

This is pure plumbing:

- Extracts `prediction_date` from `analysis_date`, falling back to
  `prediction_date` when present.
- Calls the adapter to build the row.
- Hands the row to the existing renderer.
- Emits no `st.caption` on the happy path — the inner renderer
  owns all visible output.

The helper is **not yet wired** into `render_predict_tab` per Step 2
scope. It exists as a callable that the protected test exercises
directly. Wiring it into the live UI flow is deferred.

## Validation steps

All run from `/Users/may/Desktop/stock-analyzer-main` on local
`main` (commit `97b4865`).

- `python3 -m py_compile ui/predict_tab.py services/big_up_contradiction_card.py tests/test_predict_tab_exclusion_reliability_review.py`
  - PASS (exit 0, no output)
- `python3 -m pytest tests/test_predict_tab_exclusion_reliability_review.py -v`
  - PASS — `1/1` case, 3.39s (the wall-clock includes streamlit
    import side-effects, not real work)
- `python3 -m pytest tests/test_big_up_contradiction_card.py -v`
  - PASS — `31/31` cases, 0.14s (PR-C regression — adapter
    addition didn't disturb the existing pure-logic suite)
- `python3 -m pytest tests/test_exclusion_reliability_review.py -v`
  - PASS — `5/5` cases, 0.02s (services consumer regression)
- `python3 -m pytest tests/test_exclusion_reliability_review_ui.py -v`
  - PASS — `2/2` cases, 0.11s (UI consumer regression)
- `bash scripts/check.sh`
  - PASS — `All compile checks passed.`

### Broader predict-tab regression sweep (additional, not requested)

- `python3 -m pytest tests/test_predict_summary.py -v` → PASS (5/5)
- `python3 -m pytest tests/test_evidence_trace.py -v` → **5 passed,
  1 failed** — single failure (`test_predict_page_renders_required_evidence_trace_blocks`)
  is **pre-existing on clean `main`**. Re-ran with `git stash`
  applied (working tree wiped to `97b4865`) and the same assertion
  fails (`AssertionError: 'tool_trace' not found in …`). Not a
  regression introduced by Task 092.
- `python3 -m pytest tests/test_research_loop_ui_apptest.py -v` →
  **2 failed** — both with `TypeError: fake_run_predict() got an
  unexpected keyword argument 'pre_briefing'`. The fake_run_predict
  test double doesn't accept the `pre_briefing=…` kwarg that
  `render_predict_tab` already passes (line 1098 on main, was 1098
  on `8c9862d` too — predates this task). Pre-existing test/API
  drift, not introduced by Task 092.
- `python3 -m pytest tests/test_ai_summary.py -v` → **collection
  error** — `ImportError: cannot import name 'load_dotenv' from
  'dotenv' (unknown location)`. Environment / package issue with
  the local `dotenv` install. Unrelated to source code changes.

These three pre-existing flakies do not block PR-E and are not in
the user-specified validation list. Reporting transparently for the
reviewer.

## No-business-logic confirmation

Touched in this builder pass:

- `services/big_up_contradiction_card.py` — pure addition (adapter +
  `__all__` update); zero deletions, zero modifications of existing
  lines.
- `ui/predict_tab.py` — pure addition (2 imports + 1 private
  helper); zero deletions, zero modifications of existing lines.
- `tasks/092_restore_predict_tab_exclusion_reliability_review.md`
  (task doc)
- `.claude/handoffs/task_092_builder.md` (this handoff)
- `tasks/STATUS.md` (status row + canonical mapping)

Not touched:

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
- `app.py`
- `predict.py`
- `data_fetcher.py`
- `feature_builder.py`
- `encoder.py`
- `scripts/*`
- `tests/test_big_up_contradiction_card.py`
- `.claude/handoffs/task_089_post_pr_cleanup.md`
- `.claude/worktrees/`

## Remaining risks / follow-ups

1. **Helper not wired into the live UI.** By design (Step 2 scope
   forbids it). PR-E delivers `_render_exclusion_reliability_review`
   as a callable but `render_predict_tab` does not invoke it.
   A follow-up PR-F would slot it in alongside the layer-3 evidence
   block and would also be the natural place to call
   `render_contradiction_card` (PR-C) for the same predict_result.
2. **Pre-existing test failures unmasked by the broader sweep.**
   `tests/test_evidence_trace.py::test_predict_page_renders_required_evidence_trace_blocks`,
   `tests/test_research_loop_ui_apptest.py` (two cases), and the
   `tests/test_ai_summary.py` collection error are all pre-existing
   on clean `main` (`97b4865`), confirmed via `git stash` /
   re-run. Not blocking PR-E. Worth a separate cleanup PR.
3. **Adapter allow-list is conservative.** It forwards fields known
   to be read by the contradiction-card audit and the exclusion
   reliability review. If future row consumers add new field names,
   the allow-list will need an additive update. Each new field is a
   one-line append, low-risk.
4. **Streamlit import-time dependency.** `from ui import predict_tab`
   transitively imports `streamlit` and `pandas`; a test environment
   without those would fail at import. Existing test pass rate
   confirms the local environment is fine.
5. **Cross-task regression coverage gap.** Full 072–087 cross-task
   regression cannot run in this workspace (same gap as the prior
   084–087 / 090 chains). Reviewer should verify on a workspace
   that has the full test corpus before merging if possible.

## Status

- Task 092: `in-review` (builder complete; reviewer + tester
  follow-ups expected before PR-E is opened on the
  `pr-e-predict-tab-exclusion-reliability-review` branch).
