# AVGO 1005-day replay accuracy and exclusion-accuracy report (03)

Built from B-path original-system replay outputs in `/Users/may/Desktop/stock-analyzer-main/logs/historical_training/03_fresh_replay`.
Source pipeline: `scripts/run_historical_training.py` (matcher_v2 + coded_data, no live yfinance).

## Replay scope

- Source pipeline: `B-path scripts/run_historical_training.py — original main pipeline`
- Total days: **1005** (target 1005 → match: **yes**)
- Date range: 2016-07-01 (pred) → 2020-06-30 (actual)
- Modules confirmed NOT used: `projection_v2`, `rule_scoring`, `rule_lifecycle`, `active_rule_pool`, `AVGO_technical_features`, `exclusion_reliability_review`, `contradiction_card`, `shadow_backtest`, `3C review payloads`, `yfinance live calls`

## Five-state prediction accuracy (overall)

- Correct: 277 / 1005
- Accuracy: **27.56%**

## Predicted state distribution

| state | count | share |
|-------|------:|------:|
| 大涨 | 3 | 0.30% |
| 小涨 | 528 | 52.54% |
| 震荡 | 416 | 41.39% |
| 小跌 | 58 | 5.77% |
| 大跌 | 0 | 0.00% |

## Actual state distribution

| state | count | share |
|-------|------:|------:|
| 大涨 | 142 | 14.13% |
| 小涨 | 274 | 27.26% |
| 震荡 | 263 | 26.17% |
| 小跌 | 211 | 21.00% |
| 大跌 | 115 | 11.44% |

## Five-state confusion matrix (rows=predicted, cols=actual)

| predicted \ actual | 大涨 | 小涨 | 震荡 | 小跌 | 大跌 | total_predicted |
|---|---:|---:|---:|---:|---:|---:|
| 大涨 | 1 | 0 | 2 | 0 | 0 | 3 |
| 小涨 | 70 | 151 | 136 | 105 | 66 | 528 |
| 震荡 | 63 | 105 | 112 | 93 | 43 | 416 |
| 小跌 | 8 | 18 | 13 | 13 | 6 | 58 |
| 大跌 | 0 | 0 | 0 | 0 | 0 | 0 |
| **total_actual** | 142 | 274 | 263 | 211 | 115 | **1005** |

## Recall by actual state

| actual_state | true_positive | actual_total | recall |
|---|---:|---:|---:|
| 大涨 | 1 | 142 | 0.70% |
| 小涨 | 151 | 274 | 55.11% |
| 震荡 | 112 | 263 | 42.59% |
| 小跌 | 13 | 211 | 6.16% |
| 大跌 | 0 | 115 | 0.00% |

## Precision by predicted state

| predicted_state | true_positive | predicted_total | precision |
|---|---:|---:|---:|
| 大涨 | 1 | 3 | 33.33% |
| 小涨 | 151 | 528 | 28.60% |
| 震荡 | 112 | 416 | 26.92% |
| 小跌 | 13 | 58 | 22.41% |
| 大跌 | 0 | 0 | N/A |

## Exclusion (negation) totals

- total_exclusion_actions: **2010**
- correct_exclusion_actions: **1737**
- false_exclusion_actions: **273**
- exclusion_accuracy: **86.42%**
- false_exclusion_rate: **13.58%**

## Exclusion accuracy by excluded_state

| excluded_state | total_actions | correct | false | accuracy |
|---|---:|---:|---:|---:|
| 大涨 | 802 | 683 | 119 | 85.16% |
| 小涨 | 14 | 10 | 4 | 71.43% |
| 震荡 | 0 | 0 | 0 | N/A |
| 小跌 | 203 | 166 | 37 | 81.77% |
| 大跌 | 991 | 878 | 113 | 88.60% |

## p_excluded_state distribution on FALSE exclusions (overall)

- n = 273
- min / p25 / median / mean / p75 / max = 0.0000 / 0.0003 / 0.0029 / 0.0141 / 0.0266 / 0.0607

## p_excluded_state distribution on FALSE exclusions, by excluded_state

| excluded_state | n | min | median | mean | max |
|---|---:|---:|---:|---:|---:|
| 大涨 | 119 | 0.0000 | 0.0070 | 0.0153 | 0.0600 |
| 小涨 | 4 | 0.0449 | 0.0473 | 0.0469 | 0.0481 |
| 震荡 | 0 | – | – | – | – |
| 小跌 | 37 | 0.0136 | 0.0432 | 0.0417 | 0.0606 |
| 大跌 | 113 | 0.0000 | 0.0002 | 0.0025 | 0.0607 |
