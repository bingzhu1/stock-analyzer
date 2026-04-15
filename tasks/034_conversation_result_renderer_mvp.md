
```md id="sk6ke0"
# Task 034 — conversation_result_renderer_mvp

## Goal
把 Command Center 的多步执行结果统一渲染成一个可读、稳定、可追踪的“智能答复卡片”，避免结果碎片化、重复化和 UI 混乱。

---

## Background
当前问题不是完全没有结果，而是：
- 规划结果、执行结果、最终结果经常分散
- projection / compare / AI explanation 各自一块，不够统一
- 用户很难一眼看懂：
  - 系统理解了什么
  - 执行了哪些步骤
  - 得出了什么结论
  - 依据是什么

此外，前面已经出现过 command center UI 渲染不稳定、nested expander、DOM 切换错误等问题，因此本轮要强调“固定布局、稳定渲染”。

---

## Scope

### In scope
1. 统一 command center 结果渲染结构
2. 渲染固定区块：
   - 任务理解
   - 执行步骤
   - 核心结论
   - 依据摘要
   - 风险 / 提示
   - 原始结果折叠区
3. 减少结果重复
4. 避免不稳定的动态渲染方式
5. 补最小 UI / AppTest 测试

### Out of scope
1. 不改 planner 核心逻辑
2. 不改 tool router 核心逻辑
3. 不改 scanner / predict / projection 核心逻辑
4. 不做大页面重构
5. 不做聊天气泡式完整对话 UI

---

## Target render structure

Command Center 结果建议固定为：

### A. 任务理解
- 原始输入
- 识别到的 primary intent
- 标的 / 时间窗口 / 字段

### B. 执行步骤
- step 1: projection
- step 2: compare
- step 3: ai explanation
- 每步 status

### C. 核心结论
- 明日方向 / 开盘倾向 / 收盘倾向
- 或 compare 主要发现
- 或 query / stats 主要数据结论

### D. 依据摘要
- 关键观察 3 到 5 条

### E. 风险 / 提示
- 上下文不足
- AI 未配置
- compare 缺第二标的
- 样本不足

### F. 原始结果
- JSON / table 折叠区
- 可展开，但不抢主视觉

---

## MVP expectations
优先：
- 固定布局
- container-based 渲染
- projection / compare / query / stats 统一外层样式
- 减少 expander / placeholder 反复切换

不要：
- 复杂动态动画
- 多层嵌套 expander
- 随意切换组件树结构

---

## Rendering rules

### 1. 固定外层结构
每次 command center 输出都使用固定区块顺序：
1. planning block
2. execution block
3. conclusion block
4. evidence / notes block
5. warnings block
6. raw result block

不要因为不同类型结果而完全换一套组件树。

### 2. Projection rendering
当 primary result 是 projection 时：
- 顶部展示明日方向 / 开盘倾向 / 收盘倾向 / confidence
- 下方展示简要依据
- 可选展示 AI explanation
- 原始 projection JSON 放入折叠区

### 3. Compare rendering
当 primary result 是 compare 时：
- 顶部展示比较对象、字段、时间窗口
- 展示一致天数 / 不一致天数 / 一致率
- 如有位置分布统计，也放入核心结论区
- 原始 compare result 放入折叠区

### 4. Query / stats rendering
当 primary result 是 query 或 stats 时：
- 顶部展示标的 / 字段 / 时间窗口
- stats 至少展示：
  - today value
  - average value
  - diff
- 原始数据表放折叠区或次级区

### 5. Warnings rendering
warning / fallback 信息应放独立固定区块，不要插入主结果内部反复改变布局。

---

## Stability requirements
必须避免：
- nested expander
- 在同一 placeholder 中反复切换完全不同类型组件树
- 一会儿 table 一会儿 expander 一会儿 error block 共用同一动态节点
- 前端 removeChild / DOM mismatch 风险

建议：
- 使用稳定的 `st.container()`
- 使用固定 section header
- 原始结果区可用单层 expander，但不要嵌套

---

## Allowed files
尽量限制在 command bar / labels / tests 范围，例如：
- ui/command_bar.py
- ui/labels.py
- tests/test_command_bar_apptest.py
- tests/test_command_center_stability.py

---

## Forbidden changes
- scanner 核心逻辑
- predict 核心逻辑
- projection 核心逻辑
- planner / router 大重写
- 大 UI 重构
- 无关清理性重构

---

## Done when
1. command center 结果有统一答复卡片
2. 任务理解 / 执行步骤 / 核心结论 / 风险提示清晰可见
3. 渲染结构更稳定
4. projection / compare / query / stats 结果不再明显碎片化
5. 不再出现 nested expander / DOM removeChild 类问题
6. 当前 task 相关测试通过

---

## Validation

至少覆盖：
- projection rendered card
- compare rendered card
- query rendered card
- stats rendered card
- warnings rendered safely
- no nested expander
- no unstable placeholder switching in main command center flow

如环境允许：
- bash scripts/check.sh

---

## Handoff requirements

### Builder
写入：
`.claude/handoffs/task_034_builder.md`

短格式：
- context scanned
- changed files
- implementation
- validation
- remaining risks

### Reviewer
写入：
`.claude/handoffs/task_034_reviewer.md`

短格式：
- findings
- severity
- why it matters
- suggested fix
- merge recommendation

### Tester
写入：
`.claude/handoffs/task_034_tester.md`

短格式：
- commands run
- result
- failed cases
- gaps
- recommendation