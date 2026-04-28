# Task 090 — Restore Big-Up Contradiction Card (PR-C)

- **Date:** 2026-04-28
- **Status:** in-review
- **PR target branch (later):** `pr-c-big-up-contradiction-card`

## Goal

Restore the protected, untracked test file
`tests/test_big_up_contradiction_card.py` into a proper PR-C drop by
adding the missing streamlit renderer module
`ui/big_up_contradiction_card.py`.

The pure-logic side (`services/big_up_contradiction_card.py`,
`services/big_down_tail_warning.py`,
`services/anti_false_exclusion_audit.py` v5 path) was already merged in
earlier rounds (Tasks 084 / 085 / 088). The only gap blocking the test
file from running is the streamlit-side renderer.

This is **UI presentation only**.

Do not modify:

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

## Context

Task 089 finalized the post-merge sync: local `main` is at `8c9862d`,
`origin/main` at `8c9862d`, three protected untracked files remain.
This task drops the first of those (the contradiction-card test) into
its own PR (PR-C) along with the missing UI renderer.

`tests/test_big_up_contradiction_card.py` (588 lines, 31 cases, ~23 KB)
imports both:

```python
from services.big_up_contradiction_card import (
    DEFAULT_CARD_CONFIG, FLAG_REASONS_CN, build_contradiction_card,
)
from ui import big_up_contradiction_card as ui_card
```

The first import already resolves on `main`. The second module did not
exist and had to be added.

## Scope

### In scope

- Add `ui/big_up_contradiction_card.py`
- Stage the protected `tests/test_big_up_contradiction_card.py` (no
  content changes — restored as-is)
- Add `tasks/090_restore_big_up_contradiction_card.md`
- Add `.claude/handoffs/task_090_builder.md`
- Update `tasks/STATUS.md`

### Out of scope

- Wiring the renderer into `ui/predict_tab.py` (deferred to PR-E)
- Any change in `services/*`
- Any change in audit / margin / final-decision logic
- Any change to `tests/test_predict_tab_exclusion_reliability_review.py`
- Any change to `.claude/worktrees/`

## Public API

`render_contradiction_card(payload: dict[str, Any] | None) -> None`

- Pure presentation. Does not mutate payload.
- Dispatch on `payload["variant"]`:
  - `"info"` → `st.info(...)`
  - `"warning"` → `st.warning(...)`
  - `"strong_warning"` → `st.error(...)`
- Render header / explanation / original-system summary / level &
  confidence.
- Render `triggered_flags` and `flag_reasons_cn` when present.
- Render `missing_fields` when present.
- Render `data_health_summary` minimally (only when overall status is
  not `healthy` / `unknown`).
- Render `payload["big_down_tail_warning"]` sub-section:
  - `had_big_down_exclusion is False` → `st.caption("本次未触发大跌否定 …")`
  - `warning_level == "warning"` → `st.warning("…检测到大跌侧尾部风险…")`
  - `warning_level == "strong_warning"` → `st.error("…检测到强双尾收缩风险…")`
- Imports streamlit once as `st` so tests can monkeypatch the name.

## Tests covered (existing test file, 31 cases)

§1–§9 base spec, §14–§19 cache health spec, plus 3 UI cases:

1.  No big-up exclusion → info
2.  Big-up + no flags → high-confidence info
3.  macro_contradiction → warning
4.  earnings_post_window → warning
5.  sample_invalidation → warning
6.  Multi-flag combo → strong_warning (`blocked_by_audit`)
7.  Missing core fields → 数据有限 annotation
8.  Chinese explanation contains key wording
9.  Card does NOT mutate input row
- §14 cache health forwarded into payload
- §15 stale → "(数据陈旧)" suffix
- §16 partial → "(数据有限)" suffix
- §17 strong_warning downgrades to warning when stale/missing
- §18 audit decision invariant under cache health
- §19 row not mutated when cache health present
- big_down tail integration (warning / strong_warning / safe degrade)
- UI: "本次未触发大跌否定" caption when no big-down exclusion
- UI: "检测到大跌侧尾部风险" warning when big-down warning level
- UI: "检测到强双尾收缩风险" error when big-down strong_warning level

## Validation

```bash
python3 -m py_compile ui/big_up_contradiction_card.py tests/test_big_up_contradiction_card.py
python3 -m pytest tests/test_big_up_contradiction_card.py -v
python3 -m pytest tests/test_exclusion_reliability_review.py -v
bash scripts/check.sh
```

## Acceptance

- All 31 tests in `tests/test_big_up_contradiction_card.py` pass.
- `tests/test_exclusion_reliability_review.py` (existing consumer of
  `build_contradiction_card`) still passes.
- `bash scripts/check.sh` passes.
- No service / app / predict-tab / projection logic touched.
- Protected PR-E test file untouched.
- `.claude/worktrees/` untouched.
