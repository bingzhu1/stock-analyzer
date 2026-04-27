# Task 2E-v2 — False Exclusion Validation

## Source
- v4 replay: `/Users/may/Desktop/stock-analyzer-main/.claude/worktrees/eloquent-stonebraker-e0cd86/logs/historical_training/exclusion_log_enriched/enriched_conflict_analysis_v4.csv` (sibling_worktree)
- technical features: `/Users/may/Desktop/stock-analyzer-main/.claude/worktrees/beautiful-mcclintock-1dcda2/enriched_data/AVGO_technical_features.csv` (sibling_worktree)
- joined technical rows: 165/165

## Required Baseline
- false_big_up = 105
- false_big_down = 60
- false_total = 165

## Unsupported Counts
- unsupported_by_raw_enriched = 92
- unsupported_by_technical_features = 56
- unsupported_combined = 111

## Three-Line Summary
- 错误否定大涨 105
- 错误否定大跌 60
- 合计 165
