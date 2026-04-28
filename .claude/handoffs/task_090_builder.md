# Task 090 — builder handoff

## Context scanned

- `tasks/STATUS.md`
- `tasks/090_restore_big_up_contradiction_card.md` (this task)
- `tests/test_big_up_contradiction_card.py` (588 lines, 31 cases —
  Task 085 + Task 088 spec)
- `services/big_up_contradiction_card.py` (already merged on main —
  full payload shape including big-down tail and cache health)
- `services/big_down_tail_warning.py` (already merged — payload shape
  for the big-down sub-section)
- `services/anti_false_exclusion_audit.py` v5 audit path (already
  merged — used by the card)
- `ui/exclusion_reliability_review.py` as a UI-pattern reference
- `services/exclusion_reliability_review.py` (already imports
  `build_contradiction_card` — confirmed no breakage risk)

`main` HEAD: `8c9862d` (post-Task-089 sync). Three protected untracked
entries remain in the working tree; this builder pass only stages the
big-up contradiction card test file.

## Changed files

- `ui/big_up_contradiction_card.py` (new)
- `tests/test_big_up_contradiction_card.py` (restored as-is from the
  protected untracked set; **no content edits**)
- `tasks/090_restore_big_up_contradiction_card.md` (new)
- `.claude/handoffs/task_090_builder.md` (this file, new)
- `tasks/STATUS.md` (added 090 entry to canonical mapping + table)

Not changed (and explicitly forbidden by Step 2 scope):

- `services/*`
- `app.py`
- `ui/predict_tab.py`
- `ui/projection_v2_renderer.py`
- `scripts/*`
- `data_fetcher.py`
- `feature_builder.py`
- `encoder.py`
- `tests/test_predict_tab_exclusion_reliability_review.py` (PR-E reserve)
- `.claude/worktrees/`

## Implementation summary

### New module — `ui/big_up_contradiction_card.py`

Single public function `render_contradiction_card(payload)` plus small
private helpers. Pure presentation, no side effects on the payload.
Imports streamlit once as `st` so tests can monkeypatch the name.

Behavior:

- Top section
  - `st.markdown("**否定矛盾检测**")` (title)
  - Variant dispatch: `info` → `st.info`, `warning` → `st.warning`,
    `strong_warning` → `st.error` for the header banner.
  - `st.write(chinese_explanation)` for the body paragraph.
  - `st.caption(original_system_summary)` for the "原系统结论" line.
  - `st.caption("矛盾等级：… · 否定置信：…")` summary line.
- Flag section (only when `triggered_flags` or `flag_reasons_cn`
  non-empty)
  - `st.markdown("**反证信号**")`
  - `st.caption("触发标志：…")` joined with " | "
  - One `st.caption("- {reason}")` per Chinese reason
- Missing-fields section (only when non-empty)
  - `st.caption("数据缺口：…")` joined with " / "
- Data-health section (only when `data_health_overall_status` is one
  of `stale` / `partial` / `missing` — `healthy` / `unknown` is silent)
  - `st.caption("数据健康：数据陈旧 / 数据有限 / 数据缺失")`
  - One `st.caption("- {warning}")` per `cache_health_warnings` entry
- Big-down tail section
  - `had_big_down_exclusion is False` →
    `st.caption("本次未触发大跌否定，因此不生成大跌侧双尾收缩提醒。")`
    and stop.
  - `warning_level == "strong_warning"` →
    `st.error("检测到强双尾收缩风险，本次大跌否定不建议作为强排除项。 …")`
  - `warning_level == "warning"` →
    `st.warning("检测到大跌侧尾部风险，本次大跌否定可靠性下降。 …")`
  - Otherwise → optional `st.caption(explanation)` if non-empty.

Renderer is column-free and only uses streamlit primitives that the
fake test harness mirrors (`info`, `warning`, `error`, `markdown`,
`write`, `caption`). No `expander`, `container`, `divider`, or other
methods that aren't on the fake.

The renderer never touches `services/*` and never mutates the input
payload. It guards on:

- `payload is None` → silent return
- `payload["show_card"]` falsy → silent return

### Test restoration

`tests/test_big_up_contradiction_card.py` was previously preserved
untracked across the Tasks 084–087 PR. Its content is unchanged in
this PR; staging it adds it to git as the official PR-C test asset.

## Validation steps

All run from `/Users/may/Desktop/stock-analyzer-main` on local `main`
(commit `8c9862d`):

- `python3 -m py_compile ui/big_up_contradiction_card.py tests/test_big_up_contradiction_card.py`
  - PASS
- `python3 -m pytest tests/test_big_up_contradiction_card.py -v`
  - PASS — `31/31` cases, 0.40s total
  - All §1–§9 base cases, all §14–§19 cache-health cases, both
    big-down tail integration cases, and all 3 UI cases pass.
- `python3 -m pytest tests/test_exclusion_reliability_review.py -v`
  - PASS — `5/5` cases (existing consumer of `build_contradiction_card`
    is unaffected).
- `bash scripts/check.sh`
  - PASS — `All compile checks passed.`

Full 072–087 regression skipped because this current root workspace
does not contain the prior Task 072–083 test chain — same caveat as
prior Task 084–087 builder rounds.

## No-business-logic confirmation

Touched in this builder pass:

- `ui/big_up_contradiction_card.py` (new — UI only)
- `tests/test_big_up_contradiction_card.py` (restored — test only)
- `tasks/090_restore_big_up_contradiction_card.md` (task doc)
- `.claude/handoffs/task_090_builder.md` (handoff)
- `tasks/STATUS.md` (status row + canonical mapping)

Not touched:

- `services/big_up_contradiction_card.py`
- `services/big_down_tail_warning.py`
- `services/anti_false_exclusion_audit.py`
- `services/projection_three_systems_renderer.py`
- `services/main_projection_layer.py`
- `services/final_decision.py`
- `services/projection_orchestrator_v2.py`
- `services/exclusion_layer.py`
- `app.py`
- `ui/predict_tab.py`
- `ui/projection_v2_renderer.py`
- `data_fetcher.py`
- `feature_builder.py`
- `encoder.py`
- `scripts/*`
- `tests/test_predict_tab_exclusion_reliability_review.py`
- `.claude/worktrees/`

## Remaining risks / follow-ups

- The renderer is added but **not wired into `ui/predict_tab.py`** — by
  design (Step 2 scope explicitly forbids it; that wiring belongs to
  PR-E). The card is reachable via `from ui import big_up_contradiction_card`
  but no tab renders it yet.
- Renderer assumes streamlit is already imported as `st`; in
  test environments without streamlit installed, the module-level
  `import streamlit as st` would fail at import time. The test runner
  has streamlit available (the test imports `import pytest` only and
  monkeypatches `st`, but importing `ui.big_up_contradiction_card`
  triggers the streamlit import). This matches the pattern of every
  other `ui/*.py` module in the repo.
- Full 072–087 cross-task regression is not runnable in this workspace
  — same gap as the prior 084–087 chain, not a regression introduced
  by this task.
- `tests/test_predict_tab_exclusion_reliability_review.py` remains
  untracked and reserved for PR-E. Not staged.
- `.claude/worktrees/` remains untracked. Not staged.

## Status

- Task 090: `in-review` (builder complete; reviewer + tester
  follow-ups expected before PR-C is opened on the
  `pr-c-big-up-contradiction-card` branch).
