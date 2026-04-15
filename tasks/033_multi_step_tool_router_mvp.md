# Task 033 — multi_step_tool_router_mvp

## Goal
基于 Task 032 的结构化 plan，增加最小可用的 multi-step tool router，让 Command Center 能自动调用合适的已有工具，并把多步结果串起来。

本轮重点是 orchestration，不是重写底层工具。

---

## Background
Task 032 解决的是：
- 用户自由输入
- 系统识别意图
- 产出结构化 plan

但 plan 还不能真正自动执行。

当前系统已经有这些可复用能力：
- query_data
- compare_data
- projection
- stats summary
- AI summary / explanation

所以最合理的下一步是做一个轻量 router：
- 读取 planner 输出
- 决定调用哪些已有模块
- 按顺序执行
- 把结果汇总回 command center

---

## Scope

### In scope
1. 读取 planner plan
2. 自动调用已有 query / compare / projection / 简单 stats 工具
3. 支持 optional ai follow-up
4. 支持多步结果累积
5. 支持步骤级状态与错误处理
6. 在 Command Center 展示执行步骤和主要结果
7. 补最小 router 测试

### Out of scope
1. 不重写 query / compare / projection 底层逻辑
2. 不改 scanner / predict 核心逻辑
3. 不做复杂工作流引擎
4. 不做通用 agent executor
5. 不做跨会话长期任务系统

---

## Target behavior

### Example 1
输入：
帮我看看博通明天怎么样

期望执行：
1. projection(AVGO, 20d)
2. optional compare peers (AVGO vs NVDA/SOXX/QQQ)
3. optional ai explanation

### Example 2
输入：
只看博通最近20天成交量

期望执行：
1. query(AVGO, 20d, volume)

### Example 3
输入：
先做推演，再用 AI 解释风险

期望执行：
1. projection(AVGO, 20d)
2. ai_explain_risk

### Example 4
输入：
博通今天和最近20天平均成交量比怎么样

期望执行：
1. stats(today_vs_average, AVGO, volume, 20d)

---

## MVP expectations
优先做：
- 固定顺序执行
- 每一步有明确 status
- 每步失败安全降级
- 结果先保存在 command center 当前会话上下文

不要做：
- 复杂并行执行
- AI 决定底层参数
- 任务重试框架
- 跨页面工作流系统

---

## Suggested result shape

```json
{
  "plan": {
    "primary_intent": "projection",
    "steps": [
      {"type": "projection", "symbol": "AVGO", "lookback_days": 20},
      {"type": "ai_explain_projection", "optional": true}
    ]
  },
  "steps_executed": [
    {"step": 1, "type": "projection", "status": "success"},
    {"step": 2, "type": "ai_explain_projection", "status": "success"}
  ],
  "primary_result": {},
  "aux_results": {},
  "warnings": []
}
Routing rules
1. query routing

当 step.type = query 时：

调用现有 query_data / data workbench 查询路径
读取 symbol / lookback_days / fields
返回 query result table / summary
2. compare routing

当 step.type = compare 时：

调用现有 compare_data 路径
读取 symbols / field / lookback_days
若缺第二标的，不执行并返回 warning
3. projection routing

当 step.type = projection 时：

调用现有 projection / final wiring 路径
返回 projection_report / readable summary / predict result
将最近一次成功 projection 保存在 command center 当前会话上下文中
4. stats routing

当 step.type = stats 且 operation = today_vs_average 时：

走最小统计执行路径
支持 symbol + field + lookback_days
至少输出：
today_value
average_value
absolute_diff
pct_diff（若可安全计算）
如 stats executor 还没有单独模块，可先做最小 command-center 内部接线，但不要扩大成复杂统计框架
5. AI follow-up routing

当 step.type 为：

ai_explain_projection
ai_explain_compare
ai_explain_risk

要求：

只基于当前会话里最近一次成功结果
不重新执行 query / compare / projection
无 OPENAI_API_KEY 时安全降级
上下文不足时返回友好提示
Session context requirements

router 至少要在当前会话缓存：

latest_query_result
latest_compare_result
latest_projection_result
latest_stats_result
latest_ai_explanation

要求：

刷新后可丢失，MVP 允许
但同一会话内 follow-up 要可用
Command Center display requirements

本轮至少展示：

规划结果
执行步骤状态
step 1 / step 2 / step 3
success / skipped / failed
主要结果
warning / fallback 信息

示例：

“compare 缺少第二标的，已跳过执行”
“未找到 projection 上下文，无法执行 AI 风险解释”
“OpenAI 未配置，AI follow-up 已跳过”
Allowed files

尽量限制在 router / command center / tests 范围，例如：

services/tool_router.py（如需新增）
services/intent_planner.py
ui/command_bar.py
services/ai_summary.py
tests/test_command_center_stability.py
tests/test_tool_router.py（如需新增）
tests/test_command_bar_apptest.py
Forbidden changes
scanner 核心逻辑
predict 核心逻辑
projection 核心逻辑
stats engine 大重写
data workbench 大重写
大 UI 重构
无关清理性重构
Done when
planner 输出可自动执行
支持最小 multi-step 执行
query / compare / projection / 简单 stats 可被统一路由
optional ai follow-up 可串接
步骤失败安全降级
command center 当前会话上下文可支持 follow-up
当前 task 相关测试通过
Validation

至少覆盖：

projection single-step execute
query single-step execute
compare single-step execute
stats single-step execute (today_vs_average)
projection + ai explanation
compare + ai explanation
missing second symbol safe fallback
unsupported / partial plan safe fallback

如环境允许：

bash scripts/check.sh
Handoff requirements
Builder

写入：
.claude/handoffs/task_033_builder.md

短格式：

context scanned
changed files
implementation
validation
remaining risks
Reviewer

写入：
.claude/handoffs/task_033_reviewer.md

短格式：

findings
severity
why it matters
suggested fix
merge recommendation

Tester

写入：
.claude/handoffs/task_033_tester.md

短格式：

commands run
result
failed cases
gaps
recommendation