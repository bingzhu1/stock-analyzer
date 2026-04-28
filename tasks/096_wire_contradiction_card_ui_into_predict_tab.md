# Task 096 — Wire Contradiction Card UI Into Predict Tab (PR-G)

- **Date:** 2026-04-28
- **Status:** in-review
- **PR target branch (later):** `pr-g-wire-contradiction-card-ui-into-predict-tab`

## Goal

Wire the existing big-up contradiction card UI renderer
(`ui.big_up_contradiction_card.render_contradiction_card`, added in
PR-C / Task 091) into the live predict-tab evidence layer so end
users see the contradiction-detector verdict alongside the
exclusion-reliability review (already wired in PR-F / Task 094).

This is **UI plumbing only**, no business logic changes.

## Context

After Tasks 091 / 093 / 094 / 095 merged, all the moving parts
exist on `main` (`76e2560`):

- `services.big_up_contradiction_card.build_contradiction_card_payload`
  (predict-result → row adapter, PR-E)
- `services.big_up_contradiction_card.build_contradiction_card`
  (row → structured payload, PR-C era)
- `ui.big_up_contradiction_card.render_contradiction_card`
  (payload → streamlit output, PR-C)
- `ui.predict_tab._render_exclusion_reliability_review`
  (PR-E wrapper, wired in PR-F)
- The PR-F call site at the tail of `_render_layer3_evidence`,
  between the AI-summary expander and the raw-JSON debug expander.

The contradiction-card pipeline exists end-to-end but was never
called from the predict tab. PR-G closes that single gap.

## Scope

### In scope

- Update the existing import in `ui/predict_tab.py` to also pull
  in `build_contradiction_card`, and add a new import for
  `render_contradiction_card` from `ui.big_up_contradiction_card`.
- Add a private wrapper `_render_contradiction_card(predict_result)`
  next to the existing PR-F wrapper. Same pattern: extract
  `prediction_date` from `analysis_date` (or `prediction_date`),
  build the row via `build_contradiction_card_payload`, build the
  payload via `build_contradiction_card`, then render via
  `render_contradiction_card`.
- Insert one call to `_render_contradiction_card(predict_result)`
  inside `_render_layer3_evidence`, immediately after the existing
  PR-F call to `_render_exclusion_reliability_review(predict_result)`
  and before the raw-JSON debug expander.
- New focused test
  `tests/test_predict_tab_contradiction_card_wiring.py` with two
  cases:
  1. **Wrapper plumbing** — monkeypatch the adapter / builder /
     renderer / `st`; verify the chain and non-mutation.
  2. **Live wiring** — monkeypatch the PR-F wrapper, the new PR-G
     wrapper, and `st`; call `_render_layer3_evidence(...)` and
     verify both wrappers are invoked exactly once each with the
     same `predict_result` object, in the order
     `AI summary expander → PR-F wrapper → PR-G wrapper → raw-JSON
     expander`.
- Add `tasks/096_wire_contradiction_card_ui_into_predict_tab.md`
  (this doc).
- Add `.claude/handoffs/task_096_builder.md`.
- Update `tasks/STATUS.md` with the 096 entry.

### Out of scope (hard guardrails)

- `services/big_up_contradiction_card.py`,
  `services/big_down_tail_warning.py`,
  `services/anti_false_exclusion_audit.py`,
  `services/exclusion_reliability_review.py`.
- `ui/big_up_contradiction_card.py` (PR-C renderer — contract
  locked in by `tests/test_big_up_contradiction_card.py`).
- `ui/exclusion_reliability_review.py`.
- `app.py`, `predict.py`, `data_fetcher.py`, `feature_builder.py`,
  `encoder.py`, `scripts/*`.
- Any change to existing tests
  (`test_big_up_contradiction_card.py`,
  `test_predict_tab_exclusion_reliability_review.py`,
  `test_predict_tab_exclusion_reliability_live_wiring.py`,
  `test_exclusion_reliability_review.py`,
  `test_exclusion_reliability_review_ui.py`,
  `test_predict_summary.py`).
- `.claude/worktrees/`,
  `.claude/handoffs/task_089_post_pr_cleanup.md`.

## Behaviour after wiring

When `render_predict_tab` runs:

1. Layer 3 evidence section now renders the contradiction card
   immediately after the exclusion-reliability review, before the
   raw-JSON debug expander.
2. On predictions where `forced_excluded_states` includes 大涨, the
   card surfaces the contradiction-detector verdict (variant /
   level / confidence / triggered flags / big-down tail warning).
3. On predictions without a 大涨 forced exclusion, the renderer's
   own `variant=info` path emits a small banner saying
   "未触发大涨否定，无需矛盾检测。" — the section is always present
   but degrades gracefully.

## Validation

```bash
python3 -m py_compile ui/predict_tab.py
python3 -m pytest tests/test_predict_tab_contradiction_card_wiring.py -v
python3 -m pytest tests/test_predict_tab_exclusion_reliability_live_wiring.py -v
python3 -m pytest tests/test_predict_tab_exclusion_reliability_review.py -v
python3 -m pytest tests/test_big_up_contradiction_card.py -v
python3 -m pytest tests/test_exclusion_reliability_review.py -v
python3 -m pytest tests/test_exclusion_reliability_review_ui.py -v
python3 -m pytest tests/test_predict_summary.py -v
bash scripts/check.sh
```

## Acceptance

- New wiring test passes (2/2).
- All earlier regressions still pass: PR-F live wiring (`2/2`),
  PR-E wrapper (`1/1`), PR-C suite (`31/31`),
  exclusion-reliability service (`5/5`), exclusion-reliability UI
  (`2/2`), predict_summary (`5/5`).
- `bash scripts/check.sh` passes.
- Both wrappers (PR-F + PR-G) invoked exactly once per
  `_render_layer3_evidence`, with the same `predict_result`
  reference.
- Section ordering inside layer 3:
  AI summary expander → PR-F wrapper → PR-G wrapper → raw-JSON
  expander.
- No protected file modified.
