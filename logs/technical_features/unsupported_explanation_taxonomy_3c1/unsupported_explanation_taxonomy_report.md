# Task 3C-1 — Unsupported Explanation Taxonomy

## Sources
- details: `/Users/may/Desktop/stock-analyzer-main/logs/technical_features/false_bigup_bigdown_support_breakdown_3a/unsupported_source_breakdown_details.csv` (task_3a_output)
- summary: `/Users/may/Desktop/stock-analyzer-main/logs/technical_features/false_bigup_bigdown_support_breakdown_3a/unsupported_source_breakdown_summary.json` (task_3a_output)

## Overview
- unsupported_total: 111

## Display Tier Counts
- 强证据: 171
- 数据缺口提醒: 77
- 辅助证据: 41

## Taxonomy Catalog
- [强证据] 技术动量偏强，不支持“否定大涨” (bullish_momentum_cluster): 50
  labels: macd_bullish, positive_momentum, rsi_bullish
  copy: 技术动量已经转强，说明价格仍具备继续上攻的条件，因此“否定大涨”缺少技术面支持。
- [强证据] 宏观反弹条件与“否定大涨”矛盾 (macro_rebound_conflicts_with_big_up_exclusion): 47
  labels: macro_contradiction
  copy: 新补全的宏观环境信号与原先“否定大涨”的判断方向相反，因此这个否定可靠性明显下降。
- [强证据] 价格趋势结构偏强，不支持“否定大涨” (bullish_trend_structure_cluster): 32
  labels: trend_above_ma20_ma50, high_position
  copy: 价格位置和均线结构都偏强，这说明趋势仍在大涨可达区间内，原先否定大涨的技术依据不足。
- [强证据] 技术动量转弱，不支持“否定大跌” (bearish_momentum_cluster): 19
  labels: macd_bearish, negative_momentum, rsi_bearish
  copy: 技术动量已经偏空，价格仍有继续走弱的基础，因此“否定大跌”缺少技术面支撑。
- [强证据] 价格趋势走弱，不支持“否定大跌” (bearish_trend_structure_cluster): 15
  labels: trend_below_ma20_ma50, low_position
  copy: 价格位置和趋势结构都偏弱，说明大跌风险仍处在可触发区间，原先否定大跌的技术依据不足。
- [强证据] 系统同时压低双尾，说明“大跌否定”本身不稳 (dual_tail_conflict_against_big_down_exclusion): 8
  labels: dual_extremes
  copy: 原系统同时压低双尾状态，本身就说明判断偏向过度收缩；在这种结构下，继续否定大跌并不可靠。
- [辅助证据] 量能配合上行，削弱“否定大涨” (bullish_volume_confirmation): 13
  labels: volume_confirmation
  copy: 量能和价格同向配合，说明市场对上行有确认，不适合把大涨直接视为低概率事件。
- [辅助证据] 财报后重定价窗口不适合强排除大涨 (post_earnings_repricing_risk): 8
  labels: post_earnings_window
  copy: 当前仍处于财报后重定价窗口，这类时段更容易出现方向重估，不适合把大涨当成强排除项。
- [辅助证据] 震荡压缩结构削弱了“否定大跌”的可信度 (tail_compression_context_against_big_down_exclusion): 8
  labels: predicted_neutral, p_big_up_compressed
  copy: 这类案例更像整体尾部压缩，而不是有充分证据证明不会出现大跌，因此“大跌否定”只能视为弱结论。
- [辅助证据] 波动与量能扩张提示尾部下跌风险仍在 (tail_risk_expansion_against_big_down_exclusion): 8
  labels: high_vol_or_crisis, volume_expansion, recent_volatility_expansion
  copy: 新补全数据提示波动和量能都在扩张，这种环境下尾部下跌风险仍然存在，不适合强排除大跌。
- [辅助证据] 放量下行压力削弱“否定大跌” (bearish_volume_stress): 4
  labels: volume_stress
  copy: 量能放大同时价格承压，说明卖压真实存在，因此不适合把大跌直接排除。
- [数据缺口提醒] 历史样本对“否定大涨”支撑偏薄 (history_support_thin_for_big_up_exclusion): 77
  labels: sample_confidence_invalidation
  copy: 历史样本信心不足，说明这次“否定大涨”更像证据偏薄，而不是有强反证支持。
