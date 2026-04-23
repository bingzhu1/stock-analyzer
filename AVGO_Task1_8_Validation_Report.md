# AVGO 分析仪 Task 1–8 检验报告

## 文档用途
本报告用于作为当前 AVGO 分析仪阶段性验收基线文档，供后续 Claude / 开发流程持续参考。目标是明确：

1. 当前系统已经实现了什么。
2. 各模块之间如何串联。
3. 当前使用方式是什么。
4. 当前限制与风险有哪些。
5. 下一阶段最优先的迭代方向是什么。

---

## 1. Executive Summary
当前系统已经具备完整的“推演 → 保存 → 抓实际 → 自动对比 → 错误分类 → 持久化复盘 → 历史统计 → 推演前规则提醒”闭环，属于一个**具备复盘闭环和前置规则提醒能力的分析智能体雏形**。

当前已落地的核心能力包括：

- 推演结果持久化（SQLite，多版本保留）
- 实际收盘数据自动抓取与结构分类
- 预测 vs 实际的三维度确定性对比（开盘 / 路径 / 收盘）
- 错误分类与主要错误识别（priority: 路径 > 开盘 > 收盘）
- 复盘结果持久化（deterministic review log）
- 基于历史复盘的统计分析与规则提炼
- 下一次推演前的历史规则前置提醒

系统当前阶段仍属于：

- 单票（主要围绕 AVGO）
- 日线级
- 规则驱动
- UI 仍偏 MVP 结构

它距离最终“交易智能体”目标仍缺少：

- 场景细分规则（不同结构、阶段、位置分别统计）
- 规则对推演结果的自动修正能力
- 更细粒度的数据（盘中 / 量能 / 时间段）
- 更完整的 Agent 自动触发与决策能力

---

## 2. Files Changed by Task

### Task 1 — Prediction Store
- update: `services/prediction_store.py`
- update: `tests/test_prediction_store.py`

实际落地：在现有 prediction store 基础上补齐 dict 风格接口，供后续 review 流程调用。

### Task 2 — Outcome Capture
- update: `services/outcome_capture.py`
- update: `tests/test_outcome_capture.py`

实际落地：新增 actual outcome 抓取与结构分类逻辑，同时保留旧有 outcome capture 路径。

### Task 3 — Review Comparator
- new: `services/review_comparator.py`
- new: `tests/test_review_comparator.py`

### Task 4 — Review Classifier
- new: `services/review_classifier.py`
- new: `tests/test_review_classifier.py`

实际落地差异：初版 primary error 优先级曾误写为 path > close > open，后修正为 **path > open > close**。

### Task 5 — Review Orchestrator + UI
- new: `services/review_orchestrator.py`
- update: `ui/predict_tab.py`
- new: `tests/test_review_orchestrator.py`

### Task 6 — Review Store / 持久化
- new: `services/review_store.py`
- update: `services/review_orchestrator.py`
- update: `tests/test_review_orchestrator.py`
- new: `tests/test_review_store.py`

实际落地差异：未复用旧 `review_log`，而是新建 `deterministic_review_log`，用于存放确定性复盘结果。

### Task 7 — Review Analyzer / 规则提炼
- new: `services/review_analyzer.py`
- update: `ui/predict_tab.py`
- new: `tests/test_review_analyzer.py`

### Task 8 — Pre-Prediction Briefing
- new: `services/pre_prediction_briefing.py`
- update: `ui/predict_tab.py`
- new: `tests/test_pre_prediction_briefing.py`

---

## 3. New Functions / Key Interfaces

### Prediction Store
**文件：** `services/prediction_store.py`

- `save_prediction_record(record: dict) -> str`
  - 作用：从 dict 形式保存 prediction
  - 输入：包含 `symbol`、`prediction_for_date`、`predict_result` 等字段的 dict
  - 输出：`prediction_id`

- `load_prediction_records(symbol: str | None = None, limit: int = 30) -> list[dict]`
  - 作用：读取 prediction 历史
  - 输出：prediction 列表

- `get_latest_prediction_for_target_date(symbol: str, prediction_for_date: str) -> dict | None`
  - 作用：返回指定 symbol + 日期的最新 prediction

### Outcome Capture
**文件：** `services/outcome_capture.py`

- `classify_actual_structure(actual_row: dict, prev_close: float) -> dict`
  - 作用：按 deterministic 规则生成开盘 / 收盘 / 路径标签

- `capture_actual_outcome(symbol: str, target_date: str) -> dict`
  - 作用：抓取指定日期的 actual OHLCV 并派生结构标签

### Review Comparator
**文件：** `services/review_comparator.py`

- `extract_prediction_structure(prediction: dict) -> dict`
  - 作用：兼容不同 prediction schema，提取 `pred_open / pred_path / pred_close`

- `compare_prediction_vs_actual(prediction: dict, actual: dict) -> dict`
  - 作用：对比 prediction 与 actual，输出 comparison payload

### Review Classifier
**文件：** `services/review_classifier.py`

- `classify_review_errors(comparison: dict) -> dict`
  - 作用：生成错误类型、主要错误、reason guesses

- `build_review_summary(comparison: dict, error_info: dict) -> str`
  - 作用：生成规则化中文复盘总结

### Review Orchestrator
**文件：** `services/review_orchestrator.py`

- `run_review_for_prediction(symbol: str, prediction_for_date: str) -> dict`
  - 作用：串联 prediction → outcome → compare → classify → summary → save review

### Review Store
**文件：** `services/review_store.py`

- `save_review_record(review_payload: dict) -> str`
  - 作用：持久化复盘结果

- `load_review_records(symbol: str | None = None, limit: int = 50) -> list[dict]`
  - 作用：读取复盘历史

- `get_latest_review_for_target_date(symbol: str, prediction_for_date: str) -> dict | None`
  - 作用：读取某目标日的最新复盘结果

### Review Analyzer
**文件：** `services/review_analyzer.py`

- `summarize_review_history(symbol: str, limit: int = 30) -> dict`
  - 作用：基于 review history 聚合统计结果

- `extract_review_rules(summary: dict) -> list[str]`
  - 作用：基于统计结果生成模板化中文规则

### Pre-Prediction Briefing
**文件：** `services/pre_prediction_briefing.py`

- `build_pre_prediction_briefing(symbol: str, limit: int = 30, max_rules: int = 3) -> dict`
  - 作用：在新一轮 prediction 前生成历史规则提醒包

---

## 4. End-to-End Data Flow

### 4.1 生成 prediction
用户在 Predict 页得到系统的推演结果（由现有预测流程产生 `predict_result`）。

### 4.2 保存 prediction
用户触发保存后，`prediction_store` 将 prediction 写入 `prediction_log`，生成 `prediction_id`。

### 4.3 抓取 actual outcome
在目标交易日收盘后，通过 `capture_actual_outcome(...)` 抓取实际 OHLCV，并派生：

- `open_label`
- `close_label`
- `path_label`

### 4.4 prediction vs actual 对比
`review_comparator.compare_prediction_vs_actual(...)` 比较：

- `pred_open` vs `actual_open_type`
- `pred_path` vs `actual_path`
- `pred_close` vs `actual_close_type`

输出开盘 / 路径 / 收盘三维度正确性，以及 `overall_score`。

### 4.5 错误分类
`review_classifier.classify_review_errors(...)` 根据 comparison 结果输出：

- `error_types`
- `primary_error`
- `reason_guesses`

并由 `build_review_summary(...)` 生成中文总结。

### 4.6 复盘持久化
`review_store.save_review_record(...)` 将 review payload 写入 `deterministic_review_log`，保留多版本历史。

### 4.7 历史分析
`review_analyzer.summarize_review_history(...)` 从复盘历史中提取：

- 各维度准确率
- 平均 overall score
- dominant error
- 其他统计项

然后 `extract_review_rules(...)` 生成 4–7 条中文规则。

### 4.8 推演前前置提醒
在下一次进入 prediction 流程前：

- `build_pre_prediction_briefing(...)`
- 调用历史总结与规则提炼
- 选出最多 3 条最 relevant rules
- 在 Predict 页推演区域上方展示

从而实现“历史复盘经验 → 下一次推演前主动提醒”的闭环。

---

## 5. Current UI / UX Walkthrough

### 打开 Predict 页后
用户首先能看到 prediction 结果区。

### 推演前提醒
在 Research Loop 顶部，会自动展示历史复盘提醒区域：

- 如果历史不足：提示暂无足够复盘历史
- 如果历史足够：展示 caution level + top rules
- `medium / high` 风险级别时会自动展开

### Step 1 — Save Prediction
用户点击保存后，prediction 写入数据库。

### Step 2 — Capture Outcome
在实际结果可用后，用户触发 actual outcome 抓取。

### Step 3 — AI Review
现有旧的 AI review 路径仍在，但与 deterministic review 独立。

### Step 4 — 复盘分析
用户点击运行 review 后，页面展示：

- score banner
- primary error
- 开盘 / 路径 / 收盘维度比较
- 详细错误分析
- 完整复盘总结

### Step 5 — 规则提炼
用户点击提炼规则后，页面展示：

- 历史规则列表
- 折叠的统计明细

### session_state 的影响
以下内容是会话级缓存，不是持久化：

- pre-briefing
- 当前 review result
- 当前 rules extraction 结果

页面刷新后会重新计算。

---

## 6. Current Output Schemas

### A. Prediction Record
```json
{
  "id": "uuid",
  "symbol": "AVGO",
  "analysis_date": "2026-04-20",
  "prediction_for_date": "2026-04-21",
  "created_at": "2026-04-20T09:30:00",
  "final_bias": "bullish",
  "final_confidence": "medium",
  "status": "saved",
  "predict_result_json": "{...}"
}
```

### B. Actual Outcome Payload
```json
{
  "symbol": "AVGO",
  "target_date": "2026-04-21",
  "actual_open": 172.0,
  "actual_high": 175.0,
  "actual_low": 171.5,
  "actual_close": 174.0,
  "actual_prev_close": 171.0,
  "open_label": "高开",
  "close_label": "收涨",
  "path_label": "高开高走"
}
```

### C. Comparison Payload
```json
{
  "symbol": "AVGO",
  "prediction_for_date": "2026-04-21",
  "pred_open": "高开",
  "pred_path": "高开高走",
  "pred_close": "收涨",
  "actual_open_type": "高开",
  "actual_path": "高开低走",
  "actual_close_type": "收跌",
  "open_correct": true,
  "path_correct": false,
  "close_correct": false,
  "correct_count": 1,
  "total_count": 3,
  "overall_score": 0.333
}
```

### D. Error Info Payload
```json
{
  "error_types": ["路径判断错误", "收盘判断错误"],
  "primary_error": "路径判断错误",
  "reason_guesses": [
    "预测路径与实际结构不一致",
    "预测收盘方向与实际不一致"
  ]
}
```

### E. Review Payload
```json
{
  "status": "ok",
  "symbol": "AVGO",
  "prediction_for_date": "2026-04-21",
  "prediction_id": "uuid-pred",
  "comparison": {"...": "..."},
  "error_info": {"...": "..."},
  "review_summary": "...",
  "review_id": "uuid-rev"
}
```

### F. Persisted Review Record
```json
{
  "id": "uuid-rev",
  "prediction_id": "uuid-pred",
  "symbol": "AVGO",
  "prediction_for_date": "2026-04-21",
  "created_at": "2026-04-21T16:00:00",
  "overall_score": 0.333,
  "pred_open": "高开",
  "pred_path": "高开高走",
  "pred_close": "收涨",
  "actual_open_type": "高开",
  "actual_path": "高开低走",
  "actual_close_type": "收跌",
  "primary_error": "路径判断错误",
  "error_types_json": ["路径判断错误", "收盘判断错误"],
  "review_summary": "..."
}
```

### G. Review Summary
```text
[AVGO] 2026-04-21 — BULLISH / medium
方向错误 ✗
得分 1/3 [█░░]  33%
  开盘: 预期 高开 → 实际 高开 ✓
  路径: 预期 高开高走 → 实际 高开低走 ✗
  收盘: 预期 收涨 → 实际 收跌 ✗
分类: 方向错误 (wrong_direction)
主要问题: 路径判断错误
```

### H. Pre-Prediction Briefing Payload
```json
{
  "symbol": "AVGO",
  "record_count": 12,
  "has_data": true,
  "overall_accuracy": 0.55,
  "caution_level": "medium",
  "weakest_dimension": "path",
  "weakest_dimension_cn": "路径",
  "weakest_accuracy": 0.33,
  "most_common_primary_error": "路径判断错误",
  "top_rules": [
    "⚠ 路径判断历史准确率仅 33%（12 条），本次推演请重点核查路径分析。",
    "历史最常见误判：路径判断错误（7 次），推演时主动检查此维度是否存在偏差。",
    "历史整体命中率 55%（基于 12 条复盘）。"
  ],
  "advisory_only": true
}
```

---

## 7. Persistence / Storage Model

当前使用 **SQLite (`avgo_agent.db`)** 作为核心持久化存储。

### 持久化内容
- `prediction_log`：保存 prediction
- `outcome_log`：保存 actual outcome
- `review_log`：旧的 LLM review 路径
- `deterministic_review_log`：新的确定性复盘历史

### 重要特征
- prediction 和 review 共用同一个 DB 文件
- 同一 symbol + date 允许重复保存，不覆盖旧记录
- `get_latest_*` 系列函数返回最新一条记录
- review save failure 不会导致整个 review 流程失败，而是返回 `review_save_error`

### 仅存在于 session_state 的内容
- 当前 briefing
- 当前 review result
- 当前 rules extraction 结果

这些刷新页面后会丢失。

---

## 8. Deterministic Rules Implemented

### 8.1 actual structure classification
- 开盘：高开 / 低开 / 平开
- 收盘：收涨 / 收跌 / 平收
- 路径：3 × 3 固定组合

### 8.2 comparison scoring
- `overall_score = correct_count / 3`
- 分母固定为 3
- 字段缺失不伪造默认值

### 8.3 error classification
- `open_correct == False` → 开盘判断错误
- `path_correct == False` → 路径判断错误
- `close_correct == False` → 收盘判断错误
- primary error priority：**路径 > 开盘 > 收盘**

### 8.4 review summary
基于 deterministic 模板生成中文复盘总结，不依赖 LLM。

### 8.5 review analyzer
- 计算各维度准确率
- 计算 dominant error
- 给出 insight flags
- 生成规则列表

### 8.6 pre-prediction briefing
- 从历史规则中选择最多 3 条 top rules
- 生成 caution level
- 当前为 advisory only，不自动改 prediction

---

## 9. Known Gaps / Limitations / Risks

1. 当前规则主要是**全局统计**，没有按市场场景细分。
2. briefing 只提醒，不自动修正 prediction。
3. review 仍是**日线级**，路径定义偏粗。
4. `capture_outcome` 中仍有 **AVGO 硬编码** 问题。
5. UI 中 Step 3 / 4 / 5 分散，新用户可能混淆。
6. deterministic review 与旧的 AI review 是两条并存但独立的线。
7. session 缓存可能导致用户误以为 briefing 是实时刷新的。
8. 某些旧测试文件存在与本轮任务无关的预先失败。

---

## 10. What Is Still Missing vs Final Vision

### 数据与结构层
- 更细粒度盘中数据
- 量能进入复盘与规则层
- 多票种支持
- 场景标签真正接入复盘统计

### 推演层
- 历史规则对 prediction 自动修正
- confidence 的历史校准
- 条件概率式推演

### 复盘层
- 场景细分复盘
- false confidence 等更细误差类别
- 时间窗口对比（近期 vs 全量）

### 记忆层
- 规则随时间演化
- 反事实分析
- 更结构化的知识沉淀

### Agent 层
- 自动触发 capture / review
- 自主决定是否值得推演
- 与 Command Center 的更深整合

---

## 11. Recommended Next Priorities

### 1. 场景细分复盘统计
最值得优先做。让规则从“全局平均”升级为“按条件统计”。

### 2. 收盘后自动复盘
提升 review history 累积速度，减少手动依赖。

### 3. 独立复盘历史页面
让复盘成为系统独立能力，而不是依附于 Predict 页。

### 4. 修复 symbol 硬编码
这是低成本高收益项。

### 5. 时间窗口感知规则提炼
让系统区分“长期平均”与“近期变化”。

---

## 12. Practical Daily Usage Guide

### 早盘前
1. 打开 Predict 页
2. 先看顶部历史复盘提醒
3. 查看当日推演结果
4. 如确认使用，点击保存 prediction

### 收盘后
5. 回到 Predict 页
6. 点击 Capture Outcome
7. 点击 Run Review
8. 看 Step 4 的 primary error 和 score

### 每周 / 定期
9. 点击 Step 5 提炼规则
10. 查看当前最弱维度与 dominant error
11. 用这些规则辅助下一轮判断

### 下一次使用
12. 新一轮推演前，先看 briefing，再看 prediction

---

## 13. Final Verdict
当前系统已经形成最小的“复盘 — 记忆 — 前置提醒”闭环，属于**分析智能体 MVP 已落地**阶段。

从工程上看，Task 1–8 的主线已经成立：

- 预测可以保存
- 实际结果可以抓取
- 预测与实际可以自动比较
- 错误可以分类
- 复盘可以持久化
- 历史可以统计与提炼规则
- 历史规则可以在下一次推演前主动提醒

下一轮最值得投入的方向，不是继续堆更多 UI，而是：

1. **场景细分复盘统计**
2. **自动触发复盘积累**
3. **让历史规则参与 prediction 的 confidence / bias 修正**

---

## 14. 使用建议（给后续 Claude）
后续所有开发与修正，请优先基于本报告校验以下原则：

- 不破坏当前 deterministic review 主链路
- 新规则优先保持 deterministic 和可测试
- 新功能优先服务于“复盘质量提升”和“推演前规则前置调用”
- 避免只做 UI 装饰而不增强闭环能力
- 所有扩展优先考虑是否能沉淀到 history / rule / briefing 三层

