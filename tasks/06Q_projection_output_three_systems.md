# Task 06Q — Refactor Projection Output Into Three Independent Systems

## Goal
将 projection 输出从“混合文本结果”重构为三个独立、结构化、可读的子系统：

1. `negative_system`（否定系统）—— 哪些走势/状态不应被优先考虑。
2. `record_02_projection_system`（02 记录推演系统）—— 系统认为最可能怎么走。
3. `confidence_evaluator`（置信度评判系统）—— 否定系统和 02 推演系统是否可靠。

本轮只做输出架构重构。不引入新的预测规则，不做 production cutover。

## Scope

允许修改的文件/模块：
- 新增：`services/projection_three_systems_renderer.py`
- 修改：`services/projection_entrypoint.py`（仅追加 `projection_three_systems` 字段，原有返回不变）
- 新增：`tests/test_projection_three_systems_renderer.py`
- 新增：`tests/test_projection_entrypoint_three_systems.py`
- 新增：`tasks/06Q_projection_output_three_systems.md`
- 修改：`tasks/STATUS.md`（追加 06Q 行）
- 新增：`.claude/handoffs/task_06Q_builder.md`

禁止修改的文件/模块（hard rules）：
- `app.py`
- `scanner.py` / `matcher.py` / `encoder.py` / `feature_builder.py`
- `services/exclusion_layer.py` / `services/main_projection_layer.py`
- `services/final_decision.py`（confidence / final_direction 计算）
- `services/peer_adjustment.py` / `services/historical_probability.py`
- `services/projection_orchestrator_v2.py` / `services/projection_orchestrator.py`
- `services/projection_narrative_renderer.py`（保留现有 narrative 输出）
- `ui/`（UI 主流程不动）

## Requirements

### 1. 数据来源（只读，不修改逻辑）

新输出必须仅从已有 `projection_v2_raw` 中派生：
- 否定系统 ← `exclusion_result`（excluded / triggered_rule / reasons / kill_risk / peer_alignment / feature_snapshot）+ `final_decision.why_not_more_bullish_or_bearish`
- 02 推演 ← `primary_analysis` / `peer_adjustment` / `historical_probability` / `final_decision` / `main_projection`(predicted_top1/top2/state_probabilities) / `consistency`
- 置信度评判 ← `final_decision.final_confidence` / `consistency.conflict_reasons` / `step_status` / `kill_risk` / 各层 `warnings`

### 2. 输出结构（固定字段）

```
{
  "negative_system": {
    "conclusion": str,
    "excluded_states": list[str],
    "strength": "high"|"medium"|"low"|"none",
    "evidence": list[str],
    "invalidating_conditions": list[str],
    "risk_notes": list[str]
  },
  "record_02_projection_system": {
    "current_structure": str,
    "main_projection": str,
    "five_state_projection": dict[str, float],
    "open_path_close_projection": {
      "open": str, "intraday": str, "close": str
    },
    "historical_sample_summary": str,
    "peer_market_confirmation": str,
    "key_price_levels": list[str],
    "risk_notes": list[str],
    "final_summary": str
  },
  "confidence_evaluator": {
    "negative_system_confidence": {
      "score": float|None, "level": str, "reasoning": list[str], "risks": list[str]
    },
    "projection_system_confidence": {
      "score": float|None, "level": str, "reasoning": list[str], "risks": list[str]
    },
    "overall_confidence": {
      "score": float|None, "level": str, "reasoning": list[str]
    },
    "conflicts": list[str],
    "reliability_warnings": list[str]
  }
}
```

### 3. 行为约束

- 不调用 LLM。所有字段从 v2_raw 派生，规则化输出。
- `score` 是 [0, 1] 的浮点或 None。level 取自 {"low", "medium", "high", "unknown"}。
  level → score 映射：low=0.3 / medium=0.6 / high=0.9 / unknown=None。
- 当 v2_raw 缺失或 final 不 ready 时，三个子系统必须仍然返回完整 shape，相关字段降级为安全空值，并把降级原因写入 `risk_notes` / `reliability_warnings`。
- 不修改 final_direction、final_confidence、exclusion 阈值等任何已有规则。

### 4. 入口集成

`services/projection_entrypoint.run_projection_entrypoint` 在已有 `projection_narrative` 之后，
追加 `result["projection_three_systems"]`。任何异常都通过本模块的降级 builder 包装；不允许向上抛错。
原有字段（包括 `projection_narrative`、`projection_v2_raw`、`legacy_compat`、`projection_report` 等）一律保留不变。

## Output format
1. 先给 plan
2. 再实施
3. 最后给：
   - changed files
   - implementation summary
   - validation steps
   - risks / follow-ups
