# Task 024 — advanced_stats_output

## Goal
把“比较后再统计”的结果真正做出来，让 compare_data 不只是给出逐日对比和一致率，还能输出更有解释力的统计摘要。

本轮重点是：在 compare_data 执行链里增加 position-based distribution summary，支持用户提出的“在一致天里，AVGO 高位 / 中位 / 低位各多少天”这类问题。

---

## Background
Task 022 已经让 data workbench MVP 可用：
- raw data query
- multi-symbol aligned view
- field-level comparison
- simple stats

Task 023 已增强中文 parser，使这类命令更容易被解析：
- 比较英伟达和博通最近20天最高价走势，一致里博通高位、中位、低位各多少天

但当前问题是：
- parser 虽然能识别统计请求
- compare_data 也能跑基础比较
- 但“比较后的附加统计”还没有真正落地到结果输出层

因此本 task 的目标是：
把 compare 的结果进一步汇总为用户真正要看的统计摘要。

---

## Scope

### In scope
1. 扩展 compare_data 的结果结构
2. 支持 compare 结果里的附加统计输出
3. 支持一致天 / 不一致天基础统计
4. 支持一致天里的 position distribution 统计
5. 尽量复用已有位置字段或标签
6. 在命令输出中展示稳定、可读的统计摘要
7. 补 compare / stats / wiring 相关测试

### Out of scope
1. 不改 parser 主逻辑（除非是极小接线修复）
2. 不改 projection 最终报告链
3. 不改 Predict 页中文总结
4. 不接 AI API
5. 不改 scanner / predict / 核心推演逻辑
6. 不做大 UI 改动
7. 不做复杂统计建模

---

## User-visible target behavior

本轮重点支持：

### compare summary
- 比较英伟达和博通最近20天最高价走势
- 输出：
  - 总天数
  - 一致天数
  - 不一致天数
  - 一致率

### compare + extra stats
- 比较英伟达和博通最近20天最高价走势，一致里博通高位、中位、低位各多少天

输出至少应包含：
- 总天数
- 一致天数
- 不一致天数
- 一致率
- 一致天里 AVGO：
  - 高位 X 天
  - 中位 Y 天
  - 低位 Z 天

并且：
- X + Y + Z = 一致天数

---

## MVP expectations

本轮只做最小可用增强，不要过度设计。

优先：
- 复用已有 compare_data 输出
- 在此基础上追加 summary block
- 优先复用已有 PosLabel / Pos30 / 位置分类结果
- 若已有位置标签可用，直接用标签
- 若无稳定标签，再做简单分桶

不要做：
- 复杂可配置统计框架
- 通用 DSL
- 大规模抽象

---

## Suggested implementation shape

建议按现有结构，优先增强：

1. comparison result summary
- total_days
- matched_days
- unmatched_days
- match_rate

2. position distribution summary
针对 matched rows 中的 target symbol（本例为 AVGO）统计：
- high_count
- mid_count
- low_count

3. label source priority
优先级建议：
- 先用已有 PosLabel
- 若没有，则用 Pos30 数值分桶
- 分桶可先采用简单规则，例如：
  - 高位：>= 67
  - 中位：34 - 66
  - 低位：<= 33

4. output formatting
保持命令输出稳定、可读，不要只返回原始 dict dump。

---

## Allowed files
由实现者根据 task 需要选择，但应尽量限制在 compare / stats / wiring / tests 范围内。

典型允许范围示例：
- services/comparison_engine.py
- services/stats_engine.py
- services/data_workbench.py
- services/command_center.py
- tests/test_comparison_engine.py
- tests/test_stats_engine.py
- tests/test_data_workbench_wiring.py
- tests/test_command_bar_apptest.py

如需极小范围修 parser 接线，可做最小修改，但不能扩大到 Task 023 范围以外。

---

## Forbidden changes
- scanner 核心逻辑
- predict 核心逻辑
- projection 核心逻辑
- 大 UI 重构
- 与本 task 无关的清理性重构
- 复杂统计框架化
- 修改 task 022 / 023 已验证稳定路径，除非本 task 必须的小修

---

## Done when
1. compare_data 能输出基础统计摘要
2. compare + stats request 能输出一致天里的高 / 中 / 低分布
3. 统计结果与 compare 结果一致
4. X + Y + Z = 一致天数
5. 当前 task 直接相关测试通过
6. handoff 完整写入

---

## Validation

至少覆盖以下验证：

### compare summary
- 比较英伟达和博通最近20天最高价走势
- 可输出总天数 / 一致天数 / 不一致天数 / 一致率

### compare + position stats
- 比较英伟达和博通最近20天最高价走势，一致里博通高位、中位、低位各多少天
- 高 + 中 + 低 = 一致天数

### safety
- 无位置标签时安全降级
- 空结果安全处理
- 非 compare 命令不受影响
- projection 路径不受影响

### regression
- Task 022 基础 compare 行为仍正常
- Task 023 解析后的 compare 命令仍可执行

如环境允许：
- bash scripts/check.sh

---

## Handoff requirements

### Builder handoff
写入：
`.claude/handoffs/task_024_builder.md`

短格式：
- context scanned
- changed files
- implementation
- validation
- remaining risks

### Reviewer handoff
写入：
`.claude/handoffs/task_024_reviewer.md`

短格式：
- findings
- severity
- why it matters
- suggested fix
- merge recommendation

### Tester handoff
写入：
`.claude/handoffs/task_024_tester.md`

短格式：
- commands run
- result
- failed cases
- gaps
- recommendation