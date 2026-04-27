# Task 071 — Exclusion Accuracy Chain (PR-A)

- **Date:** 2026-04-27
- **Branch:** `pr-a-exclusion-accuracy-chain` (based on `main` @ `32ce79a`, after PR-0 dual-price-track foundation merged)
- **Status:** in-review
- **Source:** recovered from `stash@{0}: On pr-0-dual-price-track-foundation: wip-recovered-work-before-pr0-main-sync` via Task 06S audit; selectively scoped to the exclusion-accuracy chain only.

## Goal

Land the **exclusion accuracy chain** — the Task 03 / 3A / 3B / 3C1 / 3C3 / 3C5 / 2E experimental track that audits and improves the projection chain's exclusion layer. This is **PR-A** of the recovered-work split planned in `tasks/06S_recovered_experimental_branch_audit.md`.

## Scope

### Code (11 files)

#### `scripts/` — 8 research / validation runners
- `analyze_missed_false_exclusions_3b.py` — Task 3B residual analysis
- `batch_run_exclusion_reliability_review_3c3.py` — Task 3C3 batch reliability runner
- `build_03_replay_report.py` — Task 03 replay report builder
- `build_unsupported_explanation_taxonomy_3c1.py` — Task 3C1 taxonomy builder
- `decompose_unsupported_false_exclusions_3a.py` — Task 3A breakdown
- `shadow_backtest_exclusion_reliability_review_3c5.py` — Task 3C5 shadow backtest
- `validate_exclusion_actions_2e.py` — Task 2E validator
- `validate_false_exclusions_2e_v2.py` — Task 2E v2 validator

#### `services/` — 2 audit modules
- `anti_false_exclusion_audit.py` — anti-false-exclusion audit logic
- `exclusion_reliability_review.py` — reliability review service backing the UI

#### `ui/` — 1 dedicated surface
- `exclusion_reliability_review.py` — exclusion-reliability review UI module (standalone — does not modify `ui/predict_tab.py` etc.)

### Tests (10 files)
- `tests/test_analyze_missed_false_exclusions_3b.py`
- `tests/test_batch_run_exclusion_reliability_review_3c3.py`
- `tests/test_build_unsupported_explanation_taxonomy_3c1.py`
- `tests/test_decompose_unsupported_false_exclusions_3a.py`
- `tests/test_exclusion_reliability_review.py`
- `tests/test_exclusion_reliability_review_ui.py`
- `tests/test_predict_tab_exclusion_reliability_review.py`
- `tests/test_shadow_backtest_exclusion_reliability_review_3c5.py`
- `tests/test_validate_exclusion_actions_2e.py`
- `tests/test_validate_false_exclusions_2e_v2.py`

### Records (1 file)
- `records/03_replay_accuracy_and_exclusion_accuracy.md` — task summary doc that pairs with the Task 03 baseline output

### Lightweight logs (21 files) — option (a): reports + summaries + baseline only

PR-A keeps **only** report markdown, summary JSON, and Task 03 baseline files. **Bulk per-row `*_details.csv` are excluded** because they are reproducible from the scripts and would balloon the PR.

#### `logs/historical_training/03_fresh_replay/` root (7)
- `03_replay_accuracy_report.md`
- `03_replay_accuracy_summary.json`
- `_run.log`
- `predictions.csv`
- `reviews.csv`
- `rules.json`
- `summary.md`

#### Task 2E / 2E v2 (4)
- `logs/historical_training/exclusion_action_validation_2e/exclusion_action_validation_report.md`
- `logs/historical_training/exclusion_action_validation_2e/exclusion_action_validation_summary.json`
- `logs/historical_training/exclusion_action_validation_2e_v2/false_exclusion_validation_report.md`
- `logs/historical_training/exclusion_action_validation_2e_v2/false_exclusion_validation_summary.json`

#### Task 3A / 3B / 3C1 / 3C3 / 3C5 (10)
- `logs/technical_features/exclusion_reliability_review_batch_3c3/batch_review_report.md`
- `logs/technical_features/exclusion_reliability_review_batch_3c3/batch_review_summary.json`
- `logs/technical_features/exclusion_reliability_shadow_backtest_3c5/shadow_backtest_report.md`
- `logs/technical_features/exclusion_reliability_shadow_backtest_3c5/shadow_backtest_summary.json`
- `logs/technical_features/false_bigup_bigdown_missed_residual_3b/missed_false_exclusion_residual_report.md`
- `logs/technical_features/false_bigup_bigdown_missed_residual_3b/missed_false_exclusion_residual_summary.json`
- `logs/technical_features/false_bigup_bigdown_support_breakdown_3a/unsupported_source_breakdown_report.md`
- `logs/technical_features/false_bigup_bigdown_support_breakdown_3a/unsupported_source_breakdown_summary.json`
- `logs/technical_features/unsupported_explanation_taxonomy_3c1/unsupported_explanation_taxonomy_report.md`
- `logs/technical_features/unsupported_explanation_taxonomy_3c1/unsupported_explanation_taxonomy_summary.json`

### `tasks/` (2 files)
- `tasks/071_exclusion_accuracy_chain.md` (this file)
- `tasks/STATUS.md` (only one line added: 071 mapping + 071 table row)

**Total: 45 files.**

## Explicitly excluded (not in PR-A — staged for future PRs)

| Excluded bucket | Owner | Why excluded from PR-A |
|---|---|---|
| All `04A` / `04B` / `04C` / `04C2` / `04D` / `04D2..6` / `04E` / `04E2` log subtrees (~86 files) | PR-B | Risk-model / probability-source research; needs its own runner scripts and review |
| All bulk `*_details.csv` files (12 files) | (none — kept only in stash) | Reproducible from scripts; would bloat PR. See `tasks/06S_recovered_experimental_branch_audit.md` H6 option (a). |
| `logs/historical_training/03_fresh_replay/03_confusion_matrix.csv` | (none) | The matrix is already rendered inside `03_replay_accuracy_report.md`; standalone CSV is redundant |
| `ui/predict_tab.py`, `ui/command_bar.py`, `ui/history_tab.py`, `tests/test_history_tab.py` | PR-E | UI revision pack; PR-A keeps only the dedicated exclusion-reliability UI surface |
| `services/agent_parser.py`, `services/ai_summary.py`, `tests/test_predict_summary.py` | PR-D / PR-E | Unrelated to exclusion accuracy |
| `services/big_*`, `services/contradiction_*`, `ui/big_up_contradiction_card.py`, `tests/test_big_*`, `tests/test_*contradiction*` | PR-C | Contradiction-card / big-up / big-down warning feature |
| `services/cache_health.py`, `services/macro_features.py`, `services/earnings_calendar.py`, `services/regime_features.py`, `services/historical_match_lookup.py`, `services/direction_threshold.py`, `scripts/refresh_all_caches.py`, `scripts/run_*04*.py`, `tests/test_cache_health.py`, `tests/test_refresh_all_caches.py`, `tests/test_direction_threshold.py`, `tests/test_dual_price_track.py` (in PR-0), `tests/test_historical_training_no_lookahead.py`, `tests/test_matcher_v2.py`, `tasks/039a_direction_threshold_tuning.md`, `logs/cache_refresh/*` | PR-D | Cache + macro + earnings + regime + direction-threshold pack |
| `data_backup_before_adjclose/*.csv` | (none) | Data backup — belongs in external storage, not git |
| `dotenv/`, `streamlit/` | (none) | Vendored test scaffolding / shims |
| `.claude/worktrees/` | (none) | Local Claude worktrees, not source |
| `matcher_v2.py`, `data_quality_check.py`, `scripts/__init__.py` | (audit pending) | Unclassified; deferred to a follow-up audit |
| `data_fetcher.py`, `feature_builder.py`, `encoder.py`, `services/data_query.py`, `tests/test_dual_price_track.py`, `tasks/06S_H1_hard_rule_layer_audit.md` | **already shipped in PR-0** (Task 070) | Foundation merged via PR #2 |

## Hard-rule compliance

- ❌ no scanner / matcher / encoder / feature_builder / data_fetcher / `app.py` modification (PR-0 already covered the dual-price-track changes; PR-A is purely additive at the audit / scripts / UI layer)
- ❌ no LLM-driven direction calls
- ❌ no main UI flow modification (the new `ui/exclusion_reliability_review.py` is a standalone surface, not a `predict_tab.py` rewrite)
- ✅ all AI outputs (if any) remain structured
- ✅ scripts must run cleanly under `bash scripts/check.sh`
- ✅ no production cutover

## Validation plan (to run on this branch before pushing)

1. `python3 -m py_compile services/*.py scripts/*.py ui/*.py`
2. `bash scripts/check.sh`
3. Focused tests:
   ```bash
   PYTHONPATH=. pytest -q \
     tests/test_validate_exclusion_actions_2e.py \
     tests/test_validate_false_exclusions_2e_v2.py \
     tests/test_decompose_unsupported_false_exclusions_3a.py \
     tests/test_analyze_missed_false_exclusions_3b.py \
     tests/test_build_unsupported_explanation_taxonomy_3c1.py \
     tests/test_batch_run_exclusion_reliability_review_3c3.py \
     tests/test_shadow_backtest_exclusion_reliability_review_3c5.py \
     tests/test_exclusion_reliability_review.py \
     tests/test_exclusion_reliability_review_ui.py \
     tests/test_predict_tab_exclusion_reliability_review.py
   ```
4. (Optional) full `PYTHONPATH=. pytest -q` — but only after PR-A's regression scope is locked in.

## Output format

1. plan ✅ (this file)
2. extraction commands → see Builder Report
3. exact `git add` command list → see Builder Report
4. validation steps → above
5. risks / follow-ups:
   - PR-A's UI module (`ui/exclusion_reliability_review.py`) requires UI flow integration; if `ui/predict_tab.py` later wires it in, that's PR-E's responsibility
   - The 04A–04E2 log subtrees were authored under the same `scripts/run_historical_training.py` pipeline; they belong to PR-B. Re-deriving them after PR-A merges is a one-shot replay, not blocking.
   - Bulk `*_details.csv` files remain only in `stash@{0}` — if needed for future audit, extract them on demand
