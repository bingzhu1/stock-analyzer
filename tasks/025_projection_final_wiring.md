# Task 025 — projection_final_wiring

## Goal
让“根据博通20天数据推演下一个交易日走势”不再只返回 advisory / preflight，而是真正接到最终预测层，输出用户可直接阅读的推演结果。

---

## Background
当前已经有：
- projection preflight / orchestrator / entrypoint
- command projection wiring
- data workbench
- parser 增强
- compare stats 增强

但现在 projection 命令的主要问题是：
- 能触发
- 但结果仍停留在 advisory / preflight
- 不是最终“明日走势推演报告”

本 task 只做接线与结果整合，不重写 predict 规则。

---

## Scope

### In scope
1. 把 projection 命令接到已有最终预测/结论生成路径
2. 统一 projection 输出结构
3. 输出用户可读的推演摘要
4. 保持 command -> projection 路径稳定
5. 补 wiring / projection 相关测试

### Out of scope
1. 不改 scanner 核心逻辑
2. 不改 predict 核心打分逻辑
3. 不做 Predict 页中文总结块
4. 不接 AI API
5. 不做大 UI 改动
6. 不做大规模重构

---

## User-visible target behavior

命令：
- 根据博通20天数据推演下一个交易日走势

输出至少包含：
- 明日方向：偏多 / 偏空 / 中性
- 开盘倾向：高开 / 平开 / 低开
- 收盘倾向：偏强 / 震荡 / 偏弱
- confidence
- 依据摘要
- 风险提醒

重点：
- 返回的是推演报告
- 不是 preflight JSON
- 不是 advisory package dump

---

## MVP expectations
本轮只做最小接线：
- 优先复用已有 projection / predict 结果
- 如结果结构分散，可加一个轻量 adapter / formatter
- 不重写规则
- 不引入新推演体系

---

## Allowed files
尽量限制在 projection / command wiring / tests 范围，例如：
- services/projection_entrypoint.py
- services/projection_orchestrator.py
- services/command_center.py
- services/predict*.py
- tests/test_projection_*.py
- tests/test_command_bar_apptest.py
- tests/test_command_projection_wiring.py

---

## Forbidden changes
- scanner 核心逻辑
- predict 核心逻辑大改
- Predict 页大改
- AI 总结接入
- 与本 task 无关的清理性重构

---

## Done when
1. projection 命令返回最终推演报告
2. 输出包含方向 / 开盘 / 收盘 / confidence / 依据 / 风险
3. 非 projection 命令不受影响
4. 当前 task 相关测试通过
5. handoff 完整写入

---

## Validation
至少覆盖：
- projection 命令返回最终报告，不再是 preflight
- 输出结构稳定
- 空结果安全处理
- query / compare 路径不受影响
- 旧 projection 路径关键回归不过坏

如环境允许：
- bash scripts/check.sh

---

## Handoff requirements

### Builder
`.claude/handoffs/task_025_builder.md`
- context scanned
- changed files
- implementation
- validation
- remaining risks

### Reviewer
`.claude/handoffs/task_025_reviewer.md`
- findings
- severity
- why it matters
- suggested fix
- merge recommendation

### Tester
`.claude/handoffs/task_025_tester.md`
- commands run
- result
- failed cases
- gaps
- recommendation