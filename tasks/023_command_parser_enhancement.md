# Task 023 — command_parser_enhancement

## Goal
增强中文命令解析能力，让指令中心支持更自然的表达，而不只是固定关键词命中。

本轮只做 parser / schema / routing 相关增强，不做 stats、predict 结论整合、AI 总结，也不做大 UI 改动。

---

## Background
当前项目已经具备：
- 中文命令入口
- query / compare / projection 三类基础命令
- Task 022 data workbench MVP 已让 query_data / compare_data 真正可执行

但当前 parser 仍偏 MVP：
- 更自然的中文句式识别不稳定
- 多标的表达支持不够稳
- “只看…… / 并排 / 统计……里……”等补充语义不清楚
- projection 命令虽能触发，但 parser 层的句式覆盖还不够自然

因此本 task 的目标不是增加底层能力，而是让现有能力更容易被自然中文触发。

---

## Scope

### In scope
1. 增强 command parser 的中文句式覆盖
2. 支持更稳定的多标的提取
3. 支持时间窗口提取（如最近20天）
4. 支持字段提取（如最高价、收盘价、成交量）
5. 支持附加统计请求提取（如一致里高位/中位/低位各多少天）
6. 保持 query / compare / projection 路径兼容
7. 补 parser 与 wiring 相关测试

### Out of scope
1. 不实现新的 stats engine 计算逻辑
2. 不把 projection 接到最终推演报告（那是后续 task）
3. 不改 Predict 页中文总结
4. 不接 AI API
5. 不改 scanner / predict / 核心推演规则
6. 不做大规模 UI 改动
7. 不做大规模架构重构

---

## Target user commands

本轮至少要更稳定支持以下句式：

### query_data
- 把博通、英伟达、费城、纳指最近20天数据并排
- 只看博通最近20天
- 只看英伟达最近20天最高价
- 调出博通最近20天收盘价和成交量

### compare_data
- 比较英伟达和博通最近20天最高价走势
- 比较英伟达和博通最近20天最高价走势，一致里博通高位、中位、低位各多少天

### projection
- 根据博通20天数据推演下一个交易日走势

---

## MVP expectations

本轮只要求 parser 能把自然中文稳定解析成结构化命令，执行层只需复用 Task 022 已有能力。

优先做：
- deterministic / rule-based enhancement
- controlled template extension
- synonym mapping
- multi-symbol extraction
- field extraction
- stat-request extraction

不要做：
- 泛化 NLP
- 模型驱动 parser
- 复杂语义规划

---

## Suggested implementation shape

可按现有代码结构，优先增强这些能力：

1. symbol extraction
- 识别：博通 / 英伟达 / 费城 / 纳指
- 可映射到统一 symbol：AVGO / NVDA / SOXX / QQQ

2. window extraction
- 识别：最近20天
- 输出统一 lookback_days

3. field extraction
- 识别：最高价 / 最低价 / 开盘价 / 收盘价 / 成交量
- 支持单字段和多字段

4. intent detection
- query_data
- compare_data
- projection

5. compare + stats request parsing
- 主 compare 请求
- 附加 stats 请求，如：
  - 一致天数
  - 不一致天数
  - 一致率
  - 一致里 AVGO 高位 / 中位 / 低位各多少天

---

## Allowed files
由实现者根据 task 需要选择，但应尽量限制在 command parser / wiring / tests 范围内。

典型允许范围示例：
- services/agent_parser.py
- services/agent_schema.py
- services/command_center.py
- services/data_query.py
- tests/test_command_parser.py
- tests/test_command_bar_apptest.py
- tests/test_data_workbench_wiring.py

如需新增极小辅助文件，必须服务于 parser / wiring 本身，且不能越界到 predict / scanner。

---

## Forbidden changes
- scanner 核心逻辑
- predict 核心逻辑
- projection 核心结论逻辑
- 大范围 UI 重构
- 与本 task 无关的清理性重构
- 修改 task 022 已验证稳定的核心行为，除非是 parser 接线所必须的小修

---

## Done when
1. 目标中文句式可稳定解析
2. query / compare / projection 旧命令不被破坏
3. parser 输出结构稳定、可读
4. 当前 task 直接相关测试通过
5. handoff 完整写入

---

## Validation
至少覆盖以下验证：

### parser
- query natural language cases
- compare natural language cases
- projection natural language case
- unsupported / partial input safety

### wiring
- 非 projection 命令仍走 data workbench 路径
- projection 命令不被误伤

### regression
- 旧 query / compare / projection 语句继续可用

如环境允许：
- bash scripts/check.sh

---

## Handoff requirements

### Builder handoff
写入：
`.claude/handoffs/task_023_builder.md`

短格式：
- context scanned
- changed files
- implementation
- validation
- remaining risks

### Reviewer handoff
写入：
`.claude/handoffs/task_023_reviewer.md`

短格式：
- findings
- severity
- why it matters
- suggested fix
- merge recommendation

### Tester handoff
写入：
`.claude/handoffs/task_023_tester.md`

短格式：
- commands run
- result
- failed cases
- gaps
- recommendation