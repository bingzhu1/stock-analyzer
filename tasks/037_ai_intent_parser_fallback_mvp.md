# Task 037 — ai_intent_parser_fallback_mvp

## Goal
在当前 Command Center 中引入一个 **AI intent parser fallback**。

规则 parser 继续作为第一层；当规则解析不确定、字段缺失、或语义含糊时，再调用 OpenAI，把自然语言解析成结构化命令 JSON。

本轮目标不是让 AI 直接回答股票问题，而是让 AI **更好地理解用户的话**。

---

## Background
当前系统已经支持：
- query / compare / stats / projection / ai_explain
- freeform intent planner
- multi-step router
- unified response card
- AI summary / AI explanation

但目前用户仍会感觉：
- “明明接了 AI，为什么还是不太懂我的话”
- “所有数据 / 全部数据 / 怎么看 / 强弱 / 对比一下” 这类表达理解不稳定
- parser 规则没覆盖到时，会 fallback 到默认字段（例如只给 Close）
- AI 现在主要接在 explanation layer，不在 understanding layer

因此，本 task 的核心不是增加新分析能力，而是把 AI 前移到 **intent parsing fallback**。

---

## Scope

### In scope
1. 在规则 parser 后增加 AI fallback parser
2. 仅在规则解析低置信度或字段不完整时调用 AI
3. AI 只输出结构化 JSON，不直接回答用户
4. 支持以下 intent：
   - query
   - compare
   - stats
   - projection
   - ai_explain
5. 支持“所有数据 / 全部数据 / 完整数据 / OHLCV” -> 多字段 query
6. 支持“今天 vs 最近20天平均...” -> stats
7. 支持“强弱 / 对比 / 怎么看明天”这类更自然表达
8. 补 parser 相关测试

### Out of scope
1. 不让 AI 直接做股票预测
2. 不让 AI 直接替代 router
3. 不改 scanner / predict / projection 核心逻辑
4. 不做多轮对话 agent
5. 不做大 UI 重构

---

## Design

### First layer: deterministic parser
先跑现有规则 parser / intent planner。

如果满足以下条件之一，则可直接使用规则结果：
- primary_intent 明确
- symbols / fields / lookback_days 足够完整
- supported = true
- 无明显歧义

### Second layer: AI fallback parser
若出现以下情况，则调用 OpenAI 解析：

1. intent 不明确
2. fields 缺失或 fallback 到默认值过于激进
3. compare / stats / query 之间存在歧义
4. planner 标记 unsupported / low confidence / ambiguity
5. 用户表达为自然语言而非模板命令

AI fallback parser 只负责：
- 读取用户输入
- 返回结构化 JSON
- 不做自然语言回答

---

## Supported structured output

AI parser 必须输出一个 JSON，至少包含：

```json
{
  "intent": "query",
  "symbols": ["AVGO"],
  "lookback_days": 20,
  "fields": ["Open", "High", "Low", "Close", "Volume"],
  "operation": null,
  "ai_followups": [],
  "confidence": "high",
  "ambiguity_reason": null
}
允许字段：

intent
query
compare
stats
projection
ai_explain
symbols
例如 ["AVGO"]
compare 例如 ["AVGO", "NVDA"]
lookback_days
默认 20
fields
单字段：["Close"]
多字段：["Open", "High", "Low", "Close", "Volume"]
operation
仅 stats 使用，例如：
today_vs_average
ai_followups
例如：
["ai_explain_projection"]
["ai_explain_compare"]
["ai_explain_risk"]
confidence
high / medium / low
ambiguity_reason
若不确定则返回简短说明
否则为 null
AI parser rules
1. “所有数据 / 全部数据 / 完整数据 / OHLCV / K线数据”

应解析为：

intent = query
fields = ["Open", "High", "Low", "Close", "Volume"]
2. “今天和最近20天平均... / 对比今天和20日均值”

应优先解析为：

intent = stats
operation = today_vs_average

例如：

博通今天和最近20天平均成交量比怎么样
博通今天收盘价和最近20天平均收盘价对比
3. “比较...强弱 / 比较...走势”

应优先解析为：

intent = compare

例如：

比较一下博通和英伟达最近20天强弱
比较博通和英伟达最近20天最高价走势
4. “推演 / 明天怎么样 / 下一个交易日走势”

应优先解析为：

intent = projection

例如：

帮我看看博通明天怎么样
根据博通20天数据推演下一个交易日走势
5. “用 AI 解释...”

应优先解析为：

intent = ai_explain

例如：

用 AI 解释这次推演
用 AI 解释为什么是中性但收盘偏强
用 AI 解释这次风险提示
Prompting requirements

AI parser 的 system prompt 必须明确说明：

这是一个股票分析工具的意图解析器
它的任务不是回答用户，而是输出结构化命令 JSON
系统支持的 intent 只有：
query
compare
stats
projection
ai_explain
“所有数据” 默认指 OHLCV
“今天 vs 最近20天平均” 默认指 stats / today_vs_average
“怎么看明天” 默认更接近 projection
如果不确定，不要乱猜，要返回低置信度和 ambiguity_reason
输出必须是 JSON，不要输出解释文字
Fallback behavior

若 AI parser：

未配置 API key
API 调用失败
返回非 JSON
返回不支持的 intent
返回结构不完整

则：

安全降级回当前 deterministic parser 结果
不让页面报错
可以在 debug / warning 中说明 AI fallback 未生效
Command Center behavior

本轮不需要大改 UI，但至少应做到：

若使用了 AI fallback，可在任务理解中显示：
planner: rule+ai_fallback
或类似轻量标记
不应暴露大段 prompt / 原始模型返回
最终仍由现有 router 执行结构化结果
Allowed files

尽量限制在 parser / planner / openai 接口 / tests 范围，例如：

services/command_parser.py
services/intent_planner.py
services/openai_client.py
services/ai_intent_parser.py（如需新增）
ui/command_bar.py（仅轻量展示）
tests/test_command_parser.py
tests/test_intent_planner.py
tests/test_ai_intent_parser.py（如需新增）
Forbidden changes
scanner 核心逻辑
predict 核心逻辑
projection 核心逻辑
tool router 大重写
大 UI 重构
无关清理性重构
Done when
规则 parser 先执行
不确定输入时能自动走 AI fallback parser
AI parser 只输出结构化 JSON
“所有数据” 可正确解析为 OHLCV 多字段 query
“今天 vs 最近20天平均...” 可稳定解析为 stats
自然语言表达的理解率提升
AI fallback 失败时安全降级
当前 task 相关测试通过
Validation

至少覆盖：

调出博通近20天的所有数据
应解析为 query + OHLCV
调出博通近20天 OHLCV 数据
应解析为 query + OHLCV
博通今天和最近20天平均成交量比怎么样
应解析为 stats + today_vs_average + Volume
博通今天收盘价和最近20天平均收盘价对比
应解析为 stats + today_vs_average + Close
比较一下博通和英伟达最近20天强弱
应解析为 compare
帮我看看博通明天怎么样
应解析为 projection
用 AI 解释这次推演
应解析为 ai_explain
OpenAI 未配置 / 返回坏 JSON 时
应安全降级，不报错

如环境允许：

bash scripts/check.sh
Handoff requirements
Builder

写入：
.claude/handoffs/task_037_builder.md

短格式：

context scanned
changed files
implementation
validation
remaining risks
Reviewer

写入：
.claude/handoffs/task_037_reviewer.md

短格式：

findings
severity
why it matters
suggested fix
merge recommendation
Tester

写入：
.claude/handoffs/task_037_tester.md

短格式：

commands run
result
failed cases
gaps
recommendation
