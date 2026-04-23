# Task 035 — projection_evidence_trace_mvp

## Goal
为 projection / predict 结果增加“步骤化证据链展示”，让用户能看到系统用了哪些工具、看到了哪些关键观察、这些观察如何影响最终结论。

重点不是暴露内部 chain-of-thought，而是提供结构化的 evidence trace。

---

## Background
当前 projection 结果已经能输出：
- 明日方向
- 开盘倾向
- 收盘倾向
- confidence
- 风险提醒
- readable summary
- AI 总结（可选）

但问题是：
- 用户只看到结论，不知道“从哪推出来的”
- scan / historical match / peer confirmation / risk 信息分散
- 看起来像黑箱

用户更希望看到类似：
- 我读了哪些数据
- 我发现了什么
- 这些发现如何影响判断
- 所以得出什么结论

---

## Scope

### In scope
1. 新增 projection evidence trace 结构
2. 汇总已有模块输出：
   - scan_result
   - predict_result
   - projection_report
   - peer / compare summary
   - stats / history summary
   - risk flags
   - memory feedback（如容易接）
3. 输出固定的 trace 区块
4. 在 Predict 页 / projection 展示证据链
5. 补最小测试

### Out of scope
1. 不暴露真正内部 chain-of-thought
2. 不重写 projection 逻辑
3. 不改 scanner / predict 核心规则
4. 不做新模型推理系统
5. 不做大 UI 重构

---

## Target evidence trace structure

建议至少包含：

### A. 调用了哪些工具
例如：
- scan
- historical_match
- peer_confirmation
- predict_summary

### B. 关键观察
例如：
- AVGO flat open, closed above open, volume shrinking
- exact matches 17, near matches 26, historical outcome mixed
- NVDA / SOXX / QQQ stronger, but confirmation diverging

### C. 推断步骤
例如：
- 因为当前 gap state 为 flat，所以开盘倾向不看高开
- 因为收盘结构偏强，所以收盘倾向保留偏强
- 因为量能收缩且历史分布混杂，所以整体信心降为 low
- 因为同业确认不足，所以最终方向维持中性而非偏多

### D. 最终结论
- 明日方向
- 开盘倾向
- 收盘倾向
- confidence

### E. 重点验证点
例如：
- 观察开盘后 30 分钟是否确认修复
- 观察 NVDA / SOXX 是否继续确认
- 观察量能是否放大

---

## Suggested output shape

```json
{
  "tool_trace": [
    "scan",
    "historical_match",
    "peer_confirmation",
    "predict_summary"
  ],
  "key_observations": [
    "...",
    "...",
    "..."
  ],
  "decision_steps": [
    "...",
    "...",
    "..."
  ],
  "final_conclusion": {
    "direction": "中性",
    "open_tendency": "平开",
    "close_tendency": "偏强",
    "confidence": "low"
  },
  "verification_points": [
    "...",
    "..."
  ]
}
MVP expectations

优先：

用现有结构化结果拼 evidence trace
用确定性规则生成 trace
结果简单清楚

不要：

AI 自由生成整条证据链
复杂推理图系统
大规模重写 summary 层
Evidence trace rules
1. tool_trace

至少列出本次结论用到的模块来源，例如：

scan
historical_match
peer_confirmation
predict_summary

若某模块没有参与，就不要硬写进去。

2. key_observations

必须来自现有结构化结果，不允许新增事实。

优先从以下内容抽取：

gap / intraday / volume state
exact / near match counts
historical bias / dominant outcome
peer confirmation state
risk flags
3. decision_steps

必须是“观察 → 结论影响”的规则化描述，不要写成自由发挥长文。

例如：

因为 gap state = flat，所以开盘倾向优先保持平开附近
因为 intraday state 偏强，所以收盘倾向保留偏强
因为 historical outcome mixed，所以 confidence 下调
因为 peer confirmation diverging，所以方向不升级为偏多
4. final_conclusion

必须与现有 projection_report / predict_result 一致，不能自相矛盾。

5. verification_points

必须是面向下一交易日的观察点，不是重新预测。

例如：

开盘后 30 分钟是否延续修复
NVDA / SOXX 是否继续确认
量能是否放大
Display requirements

Predict 页 / projection 区域至少展示：

调用了哪些工具
关键观察
推断步骤
最终结论
重点验证点

要求：

evidence trace 不能替代最终结论区块
evidence trace 应作为“为什么这样判断”的增强层
展示尽量清楚，不要变成大段难读文本
Allowed files

尽量限制在 predict/projection summary / ui / tests 范围，例如：

services/predict_summary.py
services/projection_entrypoint.py
services/evidence_trace.py（如需新增）
ui/predict_tab.py
tests/test_predict_summary.py
tests/test_projection_*.py
tests/test_evidence_trace.py（如需新增）
Forbidden changes
scanner 核心逻辑
predict 核心逻辑
projection 核心逻辑
大 UI 重构
无关清理性重构
Done when
projection / predict 结果可显示 evidence trace
用户能看到工具来源、关键观察、推断步骤、最终结论、验证点
trace 与已有结果一致，不自相矛盾
当前 task 相关测试通过
Validation

至少覆盖：

evidence trace build from existing projection result
missing fields safe fallback
projection page renders evidence trace
evidence trace does not replace final conclusion block

如环境允许：

bash scripts/check.sh
Handoff requirements
Builder

写入：
.claude/handoffs/task_035_builder.md

短格式：

context scanned
changed files
implementation
validation
remaining risks
Reviewer

写入：
.claude/handoffs/task_035_reviewer.md

短格式：

findings
severity
why it matters
suggested fix
merge recommendation
Tester

写入：
.claude/handoffs/task_035_tester.md

短格式：

commands run
result
failed cases
gaps
recommendation