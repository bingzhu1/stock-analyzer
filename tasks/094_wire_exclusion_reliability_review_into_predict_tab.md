# Task 094 — Wire Exclusion Reliability Review Into Predict Tab (PR-F)

- **Date:** 2026-04-28
- **Status:** in-review
- **PR target branch (later):** `pr-f-wire-exclusion-reliability-review-into-predict-tab`

## Goal

Wire the existing
`ui.predict_tab._render_exclusion_reliability_review` helper (added in
PR-E / Task 092) into the live predict-tab evidence layer so end users
actually see the exclusion-reliability review section when a forced
exclusion is present in `predict_result`.

This is **UI plumbing only**, no business logic changes.

## Context

After PR-C (Task 091) and PR-E (Task 093) merged, all the moving
parts exist on `main` (`a55601c`):

- `services.big_up_contradiction_card.build_contradiction_card_payload`
  (the predict-result → row adapter)
- `services.big_up_contradiction_card.build_contradiction_card`
  (the audit-payload builder)
- `services.exclusion_reliability_review.build_exclusion_reliability_review`
  (the row → review payload builder)
- `ui.exclusion_reliability_review.render_exclusion_reliability_review_for_row`
  (the streamlit renderer)
- `ui.big_up_contradiction_card.render_contradiction_card`
  (the contradiction-card streamlit renderer — out of scope here)
- `ui.predict_tab._render_exclusion_reliability_review` (the
  predict-tab wrapper that bridges adapter + renderer)

The PR-E wrapper is callable but not yet invoked from the live
predict-tab render path. PR-F closes that single gap.

## Scope

### In scope

- Single-line insertion in
  `ui.predict_tab._render_layer3_evidence`: call
  `_render_exclusion_reliability_review(predict_result)` between the
  existing AI-summary expander (line 753-755 pre-PR-F) and the raw
  JSON debug expander (line 758-759 pre-PR-F).
- New focused test
  `tests/test_predict_tab_exclusion_reliability_live_wiring.py`
  that monkeypatches `predict_tab._render_exclusion_reliability_review`
  and `predict_tab.st`, calls `_render_layer3_evidence(...)` with a
  constructed `predict_result`, and asserts the wrapper is invoked
  exactly once with the same `predict_result`, with the call sitting
  between the AI-summary and raw-JSON expanders.
- Add `tasks/094_wire_exclusion_reliability_review_into_predict_tab.md`
  (this doc).
- Add `.claude/handoffs/task_094_builder.md`.
- Update `tasks/STATUS.md` with the 094 entry.

### Out of scope (hard guardrails)

- `services/big_up_contradiction_card.py`,
  `services/big_down_tail_warning.py`,
  `services/anti_false_exclusion_audit.py`,
  `services/exclusion_reliability_review.py`,
  `services/projection_three_systems_renderer.py`,
  `services/main_projection_layer.py`,
  `services/final_decision.py`,
  `services/projection_orchestrator_v2.py`,
  `services/exclusion_layer.py`.
- `ui/exclusion_reliability_review.py`,
  `ui/big_up_contradiction_card.py`.
- `app.py`, `predict.py`, `data_fetcher.py`, `feature_builder.py`,
  `encoder.py`, `scripts/*`.
- Any change to `tests/test_predict_tab_exclusion_reliability_review.py`,
  `tests/test_big_up_contradiction_card.py`,
  `tests/test_exclusion_reliability_review.py`,
  `tests/test_exclusion_reliability_review_ui.py`,
  `tests/test_predict_summary.py`,
  `tests/test_evidence_trace.py`.
- Any change in the contradiction-card UI wiring (PR-C renderer).
  That's a separate next-step PR if/when desired.
- `.claude/worktrees/`,
  `.claude/handoffs/task_089_post_pr_cleanup.md`.

## Behaviour after wiring

When `render_predict_tab` runs:

1. Layer 3 evidence section now renders the exclusion-reliability
   review **after** the AI-summary expander and **before** the raw
   JSON debug expander.
2. On predictions where `forced_excluded_states` is non-empty (or the
   row matches the existing detection logic in
   `services.exclusion_reliability_review`), the wrapped renderer
   surfaces the section; otherwise the renderer's existing early
   return (`if not payload.get("has_exclusion_review"): return`) keeps
   the layer silent.
3. No new noise on neutral predictions.

## Validation

```bash
python3 -m py_compile ui/predict_tab.py
python3 -m pytest tests/test_predict_tab_exclusion_reliability_live_wiring.py -v
python3 -m pytest tests/test_predict_tab_exclusion_reliability_review.py -v
python3 -m pytest tests/test_big_up_contradiction_card.py -v
python3 -m pytest tests/test_exclusion_reliability_review.py -v
python3 -m pytest tests/test_exclusion_reliability_review_ui.py -v
python3 -m pytest tests/test_predict_summary.py -v
bash scripts/check.sh
```

## Acceptance

- New live-wiring test passes (2/2).
- All PR-C / PR-E / services / UI / predict_summary regressions still
  pass.
- `bash scripts/check.sh` passes.
- The wrapper is invoked exactly once per `_render_layer3_evidence`
  call, with the same `predict_result` reference.
- The wrapper call sits between the AI-summary and raw-JSON
  expanders.
- No protected file modified.
