# Task 028 — polish_and_guardrails_pack

## Goal
对前面主线任务做小范围收尾，统一输出文案，补安全降级，增强主路径回归保护，避免 command / compare / projection / predict 之间后续互相打架。

---

## Background
当前主线已基本完成：
- 022 data workbench MVP
- 023 command parser enhancement
- 024 advanced stats output
- 025 projection final wiring
- 026A readable summary + optional AI polish

现在系统已经“能用”，但还存在收尾问题：
- 命令输出、Predict 输出、projection 输出用词可能不完全统一
- 空结果 / 缺字段 / 样本不足等情况可能表现不够一致
- 多轮增量后，需要补一轮主路径回归保护

因此本 task 不新增核心功能，只做 polish + guardrails。

---

## Scope

### In scope
1. 统一关键输出文案
2. 补安全降级
3. 增强主路径回归测试
4. 小范围修正命令输出可读性
5. 小范围修正 summary / risk 提示一致性

### Out of scope
1. 不新增新的核心功能
2. 不改 scanner 核心逻辑
3. 不大改 predict 核心规则
4. 不新增新的 AI 流程
5. 不做大 UI 重构
6. 不做大规模架构重构

---

## User-visible target behavior

### wording consistency
关键结论尽量统一用词，例如：
- 明日方向：偏多 / 偏空 / 中性
- 开盘倾向：高开 / 平开 / 低开
- 收盘倾向：偏强 / 震荡 / 偏弱
- 风险提醒：样本不足 / 当前高位 / 外部确认不足 / 历史分布混杂

### graceful degradation
以下情况要稳定输出，不应报错，不应出现难看的半结构化 dump：
- 空输入
- 缺字段
- 样本不足
- compare 空结果
- projection 部分字段缺失
- 外部对照不足

### regression protection
至少保护：
- query_data
- compare_data
- projection command
- Predict/projection readable summary
- command center 到执行层主路径

---

## MVP expectations
只做小修，不扩 scope。
优先：
- 统一术语
- 补 guard clauses / fallback text
- 增强关键测试
- 修小问题

不要：
- 重写 formatter
- 重写 parser
- 重写 projection / predict

---

## Allowed files
尽量限制在 command / projection / predict summary / tests 范围，例如：
- services/command_center.py
- services/projection_entrypoint.py
- services/predict_summary.py
- ui/predict_tab.py
- tests/test_command_bar_apptest.py
- tests/test_data_workbench_wiring.py
- tests/test_command_projection_wiring.py
- tests/test_predict_*.py
- tests/test_projection_*.py

---

## Forbidden changes
- scanner 核心逻辑
- predict 核心规则大改
- 新增复杂功能
- 大 UI 重构
- 与本 task 无关的清理性重构

---

## Done when
1. 关键输出术语更统一
2. 常见空结果/缺字段/样本不足可安全降级
3. query / compare / projection / summary 主路径回归测试补强
4. 当前 task 相关测试通过
5. handoff 完整写入

---

## Validation
至少覆盖：
- query 输出稳定
- compare 输出稳定
- projection 输出稳定
- Predict/projection readable summary 稳定
- 缺字段 / 空结果 / 样本不足安全处理
- command 主路径回归通过

如环境允许：
- bash scripts/check.sh

---

## Handoff requirements

### Builder
`.claude/handoffs/task_028_builder.md`
- context scanned
- changed files
- implementation
- validation
- remaining risks

### Reviewer
`.claude/handoffs/task_028_reviewer.md`
- findings
- severity
- why it matters
- suggested fix
- merge recommendation

### Tester
`.claude/handoffs/task_028_tester.md`
- commands run
- result
- failed cases
- gaps
- recommendation