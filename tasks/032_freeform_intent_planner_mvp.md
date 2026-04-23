# Task 032 — freeform_intent_planner_mvp

## Goal
把当前 Command Center 从“单条命令解析”升级成“自由文本意图规划器 MVP”。

用户可以输入更自然的一句话，系统先识别真实意图，并产出结构化 plan，说明下一步应该调用哪些已有工具。

本轮只做 planner，不做完整多步执行器大重构。

---

## Background
当前 Command Center 已支持：
- query / compare / projection 基础命令
- AI explanation commands
- 一定程度的自然中文解析

但目前问题是：
- 仍偏“命令式输入”，不是自由文本输入
- 遇到更自然的句子时，经常误分类
- 不会把一句话拆成多步计划
- 不能明确告诉用户“系统理解成了什么、准备怎么做”

因此本 task 的目标不是立即让系统自动完成所有步骤，而是先补一个稳定的 intent planner。

---

## Scope

### In scope
1. 新增自由文本 intent planning 能力
2. 把自由文本映射为结构化 plan
3. 支持四类主任务：
   - query
   - compare
   - projection
   - stats（仅限简单统计意图，如 today vs average / 当前值 vs 近N日均值）
4. 支持可选 AI follow-up：
   - ai_explain_projection
   - ai_explain_compare
   - ai_explain_risk
5. 在 Command Center 展示“规划结果 / 识别计划”
6. 补 planner 相关最小测试

### Out of scope
1. 不做完整多步自动执行器
2. 不重写 query / compare / projection 底层逻辑
3. 不改 scanner / predict 核心逻辑
4. 不做大 UI 重构
5. 不做通用聊天机器人
6. 不把 planner 完全交给 AI

---

## Target user inputs
本轮至少支持这些自由输入：

1. 帮我看看博通明天怎么样
2. 比较一下博通和英伟达最近20天强弱，再告诉我明天怎么看
3. 只看博通最近20天成交量
4. 为什么这次中性但收盘偏强
5. 先做推演，再用 AI 解释风险
6. 博通今天和最近20天平均成交量比怎么样
7. 博通今天成交量比最近20天均量高多少
8. 用 AI 解释这次推演为什么只是中性

---

## Expected planner output
planner 输出应是结构化 plan，例如：

### 例 1：projection
```json
{
  "primary_intent": "projection",
  "steps": [
    {"type": "projection", "symbol": "AVGO", "lookback_days": 20},
    {"type": "compare", "symbols": ["AVGO", "NVDA", "SOXX", "QQQ"], "optional": true},
    {"type": "ai_explain_projection", "optional": true}
  ],
  "symbols": ["AVGO"],
  "lookback_days": 20,
  "fields": [],
  "ai_followups": ["ai_explain_projection"]
}
### 例 2：query
{
  "primary_intent": "query",
  "steps": [
    {"type": "query", "symbol": "AVGO", "lookback_days": 20, "fields": ["volume"]}
  ],
  "symbols": ["AVGO"],
  "lookback_days": 20,
  "fields": ["volume"],
  "ai_followups": []
}
### 例 3：stats
{
  "primary_intent": "stats",
  "steps": [
    {
      "type": "stats",
      "symbol": "AVGO",
      "field": "volume",
      "lookback_days": 20,
      "operation": "today_vs_average"
    }
  ],
  "symbols": ["AVGO"],
  "lookback_days": 20,
  "fields": ["volume"],
  "ai_followups": []
}
## MVP expectations

### 先做：

rule-based / template-based planner
尽量复用已有 parser
planner 结果可视化展示
unsupported input 安全降级
对“单标的 + 当前值 vs 近N日均值”做最小支持

### 不要做：

通用多轮对话规划器
大模型自主计划器
一次性支持所有自然语言
复杂统计 DSL
Planning rules

## 本轮 planner 至少应满足这些规则：

### 1. projection 识别

以下表达优先识别为 projection：

帮我看看博通明天怎么样
推演博通明天的走势
根据博通最近20天数据推演下一个交易日走势

### 默认：

symbol = AVGO
lookback_days = 20（若用户未明确给出）
2. compare 识别

以下表达优先识别为 compare：

比较博通和英伟达最近20天强弱
比较博通和英伟达最近20天最高价走势

要求：

至少识别两个标的
若只识别到一个标的，不要擅自补第二个去执行；可以在 plan 里标记 missing_second_symbol
3. query 识别

以下表达优先识别为 query：

只看博通最近20天成交量
调出博通最近20天收盘价和成交量
4. stats 识别

以下表达优先识别为 stats：

博通今天和最近20天平均成交量比怎么样
博通今天成交量比最近20天均量高多少
博通今天收盘价和最近20天平均收盘价对比

要求：

symbol = AVGO
field = volume / close 等
operation = today_vs_average
5. AI follow-up 识别

以下表达应附带 ai_followups：

用 AI 解释这次推演
先做推演，再用 AI 解释风险
用 AI 解释为什么偏空 / 中性 / 偏多
Planner display requirements

Command Center 至少要展示：

原始输入
识别到的 primary intent
识别到的 symbols / fields / lookback_days
计划步骤 steps[]
若有歧义或缺信息，显示友好提示

例：

“比较指令只识别到一个标的，请补充第二个标的”
“该输入更像统计查询，不是双标的 compare”
“未找到可解释的 projection 上下文”
Allowed files

尽量限制在 planner / command center / tests 范围，例如：

services/intent_planner.py（如需新增）
services/command_parser.py
ui/command_bar.py
tests/test_command_parser.py
tests/test_command_center_stability.py
tests/test_intent_planner.py（如需新增）
Forbidden changes
scanner 核心逻辑
predict 核心逻辑
projection 核心逻辑
data workbench 底层重写
大 UI 重构
无关清理性重构
Done when
自由文本可稳定映射为结构化 plan
支持 query / compare / projection / 简单 stats 四类主任务
支持可选 AI follow-up 标识
Command Center 能展示规划结果
unsupported input 有友好降级
“今天 vs 近20日均值”这类 stats 输入不会再误判成 compare(AVGO, NVDA)
当前 task 相关测试通过
Validation

至少覆盖：

freeform -> projection plan
freeform -> compare plan
freeform -> query plan
freeform -> stats plan (today_vs_average)
freeform + ai follow-up
single-symbol compare-like input should not auto-force NVDA
unsupported input graceful fallback

如环境允许：

bash scripts/check.sh
Handoff requirements
Builder

.claude/handoffs/task_032_builder.md

context scanned
changed files
implementation
validation
remaining risks
Reviewer

.claude/handoffs/task_032_reviewer.md

findings
severity
why it matters
suggested fix
merge recommendation
Tester

.claude/handoffs/task_032_tester.md

commands run
result
failed cases
gaps
recommendation