# Task 092 — Restore Predict Tab Exclusion Reliability Review (PR-E)

- **Date:** 2026-04-28
- **Status:** in-review
- **PR target branch (later):** `pr-e-predict-tab-exclusion-reliability-review`

## Goal

Restore the protected, untracked test file
`tests/test_predict_tab_exclusion_reliability_review.py` into a proper
PR-E drop by adding the missing predict-tab wrapper helper and the
adapter that turns a live `predict_result` into a row dict suitable
for the existing exclusion-reliability-review pipeline.

The pure-logic side
(`services/exclusion_reliability_review.py`,
`ui/exclusion_reliability_review.py`,
`services/big_up_contradiction_card.py`,
`ui/big_up_contradiction_card.py`) was already merged in earlier
rounds (Tasks 071 / 084 / 085 / 088 / 090). Only a thin wrapper layer
inside the predict-tab module was missing.

This is **wrapper plumbing only**, no business logic.

Do not modify:

- `services/big_down_tail_warning.py`
- `services/anti_false_exclusion_audit.py`
- `services/exclusion_reliability_review.py`
- `services/projection_three_systems_renderer.py`
- `services/main_projection_layer.py`
- `services/final_decision.py`
- `services/projection_orchestrator_v2.py`
- `services/exclusion_layer.py`
- `ui/exclusion_reliability_review.py` (already provides
  `render_exclusion_reliability_review_for_row`)
- `app.py`
- `predict.py`
- `data_fetcher.py`
- `feature_builder.py`
- `encoder.py`
- `scripts/*`
- `.claude/worktrees/`

Do not stage `.claude/handoffs/task_089_post_pr_cleanup.md` (deferred
to a separate housekeeping PR-D).

## Context

Task 091 (PR-C merge sync) left local `main` at `97b4865`, with three
remaining protected / deferred untracked entries:

- `.claude/handoffs/task_089_post_pr_cleanup.md`
- `.claude/worktrees/`
- `tests/test_predict_tab_exclusion_reliability_review.py`

PR-E targets only the third of those. The PR-C renderer
(`ui/big_up_contradiction_card.py`) is intentionally *not* invoked
from the predict-tab integration in this PR — that wider wiring is
deferred to a follow-up.

`tests/test_predict_tab_exclusion_reliability_review.py` (45 lines,
1 test case) imports `ui.predict_tab` and monkeypatches three
attributes that must exist as module-level names on `predict_tab`:

```python
monkeypatch.setattr(predict_tab, "st", fake_st)
monkeypatch.setattr(predict_tab, "build_contradiction_card_payload", fake_build)
monkeypatch.setattr(predict_tab, "render_exclusion_reliability_review_for_row", fake_render)
```

It then invokes a private helper:

```python
predict_tab._render_exclusion_reliability_review(predict_result)
```

with a minimal `predict_result` and asserts:

1. `build_contradiction_card_payload` was called with
   `prediction_date == "2026-04-25"` (the value of the input's
   `analysis_date`), as a keyword-only argument.
2. The return of `build_contradiction_card_payload` is forwarded to
   `render_exclusion_reliability_review_for_row(row)`.
3. No `st.caption(...)` is emitted on the happy path.

## Scope

### In scope

- Add `build_contradiction_card_payload` to
  [services/big_up_contradiction_card.py](services/big_up_contradiction_card.py).
- Add the private wrapper `_render_exclusion_reliability_review` to
  [ui/predict_tab.py](ui/predict_tab.py).
- Import `build_contradiction_card_payload` and
  `render_exclusion_reliability_review_for_row` into `predict_tab` so
  the test's monkeypatch surface is satisfied.
- Stage the protected `tests/test_predict_tab_exclusion_reliability_review.py`
  unchanged when PR-E is opened.
- Add `tasks/092_restore_predict_tab_exclusion_reliability_review.md`
  (this doc).
- Add `.claude/handoffs/task_092_builder.md`.
- Update `tasks/STATUS.md`.

### Out of scope

- Calling `_render_exclusion_reliability_review` from the live
  `render_predict_tab` flow. The helper is added but not yet wired.
- Calling `render_contradiction_card` (the PR-C renderer) inside the
  predict tab.
- Any change in `services/*` other than the additive
  `build_contradiction_card_payload` adapter in
  `services/big_up_contradiction_card.py`.
- Any change in `ui/exclusion_reliability_review.py`,
  `ui/big_up_contradiction_card.py`, `app.py`, `predict.py`, or the
  data-pipeline files.
- Staging or modifying `.claude/handoffs/task_089_post_pr_cleanup.md`
  (separate PR-D).
- Any change to `.claude/worktrees/`.
- Any change to `tests/test_big_up_contradiction_card.py` (already on
  `main` after PR-C).

## Public API

### `build_contradiction_card_payload`

```python
def build_contradiction_card_payload(
    predict_result: dict[str, Any] | None,
    *,
    prediction_date: str | None = None,
) -> dict[str, Any]
```

- Pure read; never mutates `predict_result`.
- Safe on `None` or partial inputs — missing fields are simply
  omitted from the row.
- When `prediction_date` is provided, the row carries it under both
  `prediction_date` and `analysis_date` so downstream code that keys
  on either name works.
- Forwards a curated allow-list of fields when present:
  `predicted_state`, `forced_excluded_states`, `excluded_states`,
  `p_大涨`, `p_大跌`, `p_小涨`, `p_小跌`, `p_震荡`,
  `state_probabilities`, `final_direction`, `final_confidence`,
  `five_state_top1`, `five_state_distribution`,
  `five_state_top1_margin`, `five_state_margin_band`,
  `five_state_display_state`, `five_state_secondary_state`,
  `exclusion_triggered_rule`, `exclusion_triggered_state`,
  `excluded_state_under_validation`, `support_mix`,
  `raw_source_labels`, `technical_source_labels`,
  `unsupported_by_raw_enriched`,
  `unsupported_by_technical_features`, `data_health_summary`,
  `contradiction_inputs_available`, `actual_state`, `symbol`.

### `_render_exclusion_reliability_review`

```python
def _render_exclusion_reliability_review(predict_result: dict | None) -> None
```

- Extracts `prediction_date` from `predict_result["analysis_date"]`
  (or, as a fallback, `predict_result["prediction_date"]`).
- Builds `row = build_contradiction_card_payload(predict_result,
  prediction_date=prediction_date)`.
- Calls `render_exclusion_reliability_review_for_row(row)`.
- Emits no `st.caption` on the happy path; it lets the inner
  renderer own all visible output.

## Validation

```bash
python3 -m py_compile ui/predict_tab.py services/big_up_contradiction_card.py tests/test_predict_tab_exclusion_reliability_review.py
python3 -m pytest tests/test_predict_tab_exclusion_reliability_review.py -v
python3 -m pytest tests/test_big_up_contradiction_card.py -v
python3 -m pytest tests/test_exclusion_reliability_review.py -v
python3 -m pytest tests/test_exclusion_reliability_review_ui.py -v
bash scripts/check.sh
```

## Acceptance

- `tests/test_predict_tab_exclusion_reliability_review.py` passes.
- `tests/test_big_up_contradiction_card.py` (PR-C suite) still
  passes.
- `tests/test_exclusion_reliability_review.py` and
  `tests/test_exclusion_reliability_review_ui.py` still pass.
- `bash scripts/check.sh` passes.
- `_render_exclusion_reliability_review` is added but not yet wired
  into the live render flow — calling it directly produces the
  expected behaviour, but `render_predict_tab` does not invoke it.
- No protected file modified.
- PR-E protected test file remains the only untracked test artifact
  to stage.
