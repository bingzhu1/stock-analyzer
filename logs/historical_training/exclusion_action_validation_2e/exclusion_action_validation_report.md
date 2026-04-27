# Task 2E — Exclusion Action Validation

## Scope
- No prediction-rule changes
- No UI changes
- No warning / strong_warning output layer
- Unit of analysis: one exclusion action

## Sources
- Enriched replay: `/Users/may/Desktop/stock-analyzer-main/.claude/worktrees/beautiful-mcclintock-1dcda2/logs/historical_training/state_probabilities_v1/replay_full_prob_rows_enriched.jsonl` (sibling_worktree)
- Technical replay: `/Users/may/Desktop/stock-analyzer-main/.claude/worktrees/beautiful-mcclintock-1dcda2/logs/historical_training/state_probabilities_v1/replay_full_prob_rows_with_technical_features.jsonl` (sibling_worktree)
- Merged replay rows: 1000
- Missing technical joins: 0

## Overall
- Total exclusion actions: 725
- Unsupported actions: 556
- Unsupported rate: 76.69%
- Unsupported by raw data: 360
- Unsupported by technical features: 438
- Unsupported by both: 242
- Unsupported by raw only: 118
- Unsupported by technical only: 196

## By State
- 大涨: unsupported 459/511 (89.82%); raw=360, technical=341, both=242
- 大跌: unsupported 97/214 (45.33%); raw=0, technical=97, both=0
