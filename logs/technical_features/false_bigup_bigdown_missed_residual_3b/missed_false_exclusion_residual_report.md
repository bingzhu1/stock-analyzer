# Task 3B — Missed False Exclusion Residual Analysis

## Sources
- details: `/Users/may/Desktop/stock-analyzer-main/logs/historical_training/exclusion_action_validation_2e_v2/false_exclusion_validation_details.csv` (task_2e_v2_fallback)
- summary: `/Users/may/Desktop/stock-analyzer-main/logs/historical_training/exclusion_action_validation_2e_v2/false_exclusion_validation_summary.json` (task_2e_v2_fallback)
- v4 replay: `/Users/may/Desktop/stock-analyzer-main/.claude/worktrees/eloquent-stonebraker-e0cd86/logs/historical_training/exclusion_log_enriched/enriched_conflict_analysis_v4.csv` (sibling_worktree)
- technical features: `/Users/may/Desktop/stock-analyzer-main/.claude/worktrees/beautiful-mcclintock-1dcda2/enriched_data/AVGO_technical_features.csv` (sibling_worktree)

## Residual Total
- missed_total: 54

## Raw Residual Sources
- raw_no_base_tail_pattern: 23
- raw_no_contradiction_flags: 16
- raw_tail_pattern_but_score_below_threshold: 15

## Technical Residual Sources
- tech_zero_support_signals: 35
- tech_single_signal_macd_bearish: 11
- tech_single_signal_macd_bullish: 4
- tech_single_signal_volume_stress: 2
- tech_single_signal_positive_momentum: 1
- tech_single_signal_volume_confirmation: 1

## Raw Supporting Context
- missing_p_big_down: 38
- audit_hard_excluded: 16
- no_triggered_flags: 16
- dual_extremes: 15
- predicted_neutral: 15
- p_big_up_compressed: 14
- downgrade_low_volume: 10
- high_vol_or_crisis: 9
- volume_expansion: 7
- recent_volatility_expansion: 6
- downgrade_calm_regime: 3
