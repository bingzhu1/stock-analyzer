# Task 3C-5 — Exclusion Reliability Review Shadow Backtest

## Actual Paths Used
- preferred replay_with_technical_features jsonl: `/Users/may/Desktop/stock-analyzer-main/replay_full_prob_rows_with_technical_features.jsonl` (exists=False)
- replay base rows: `/Users/may/Desktop/stock-analyzer-main/.claude/worktrees/eloquent-stonebraker-e0cd86/logs/historical_training/exclusion_log_enriched/enriched_conflict_analysis_v4.csv` (sibling_worktree)
- replay review details: `/Users/may/Desktop/stock-analyzer-main/logs/technical_features/exclusion_reliability_review_batch_3c3/replay_batch_review_details.csv`
- false exclusion baseline: `/Users/may/Desktop/stock-analyzer-main/logs/historical_training/exclusion_action_validation_2e_v2/false_exclusion_validation_details.csv`
- false exclusion review details: `/Users/may/Desktop/stock-analyzer-main/logs/technical_features/exclusion_reliability_review_batch_3c3/false_exclusion_batch_review_details.csv`

## Shadow Rule
- action unit: exclusion action
- trigger: `strongest_tier_cn == "强证据"`
- prediction / forced_exclusion fields remain unchanged

## Replay Coverage
- replay_days: 1005
- replay_rows_with_big_exclusions: 996
- replay_actions_total: 1258
- baseline_false_big_up: 105
- baseline_false_big_down: 60
- baseline_false_total: 165

## Overall
- false_exclusions_total: 165
- correct_exclusions_total: 1093
- shadow_downgrade_triggered: 575
- rescued_false_exclusions: 91
- hurt_correct_exclusions: 484
- false_rescue_rate: 55.15%
- correct_hurt_rate: 44.28%
- flagged_false_precision: 15.83%

## By Excluded State
- 大涨: rescued_false=69, hurt_correct=343, false_rescue_rate=65.71%, correct_hurt_rate=54.53%
- 大跌: rescued_false=22, hurt_correct=141, false_rescue_rate=36.67%, correct_hurt_rate=30.39%
