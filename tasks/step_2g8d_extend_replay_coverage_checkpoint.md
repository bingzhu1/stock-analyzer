# Step 2G-8D — Extend Replay Coverage Checkpoint

> **状态固化文档（extend replay coverage checkpoint），不实现，不改代码，不写 DB，不运行 replay。**
> 本文档**冻结** Step 2G-8D design（commit `170617c`）的：W4 范围
> （2024-08-03 → 2025-12-31）、2026-01-01 final test 永久封禁、输出
> 目录与文件、`w4_replay_manifest.v1` schema、与 Step 3R-4 协议 /
> Step 3R-2 helper 的衔接边界、6 子步骤实施顺序、10 项风险、11 项
> 成功标准、12 项禁止事项。
>
> 本轮**不动任何代码**：不改 `predict.py` / `run_predict` /
> `scanner.py` / `prediction_store.py` / `app.py` / 任何 `ui/*` /
> `services/*` / 任何 builder / DB schema / 任何 test 中的任何一处。
>
> **本文不实现 replay 工具、不跑 replay、不写 DB、不调 yfinance、
> 不接 trading API**；只在 markdown 层固化 W4 数据扩展的状态，作为
> 后续 8D.1 / 8D.2 / 8D.3 / 8D.4 / 3R-4.1 的强制 gate。

---

## 1. 当前完成状态

- **Step 3 calibration restart launch review** 已完成并进入 main
  （commit `b8c781d`）
- **Step 3R-0** restart scope checkpoint 已完成并进入 main（commit
  `1b7288e`）
- **Step 3R-1** regime label design + checkpoint 已完成并进入 main
  （commits `a8df93a` / `8d4fe8f`）
- **Step 3R-4** cross-window validation protocol design + checkpoint
  已完成并进入 main（commits `a58aad4` / `abe3ba2`）
- **Step 3R-2** read-only regime labels builder + checkpoint 已完成并
  进入 main（commits `e2a681b` / `db7618b`）
- **Step 2G-8D** extend replay coverage design 已完成并进入 main
  （commit `170617c`）
- 本 checkpoint **固定**：
  - W4 范围 = 2024-08-03 → 2025-12-31
  - 2026-01-01 之后 final test 永久封禁
  - W4 输出目录与 5 文件 layout
  - `w4_replay_manifest.v1` schema 5 项不变量
  - 与 Step 3R-4 / Step 3R-2 的衔接关系
  - 6 子步骤实施顺序
  - 10 项风险 / 11 项成功标准 / 12 项禁止事项
- 本 checkpoint 是**纯状态归档**；**仍不运行 replay**、不实现 / 不改
  代码 / 不写 DB / 不接网络 / 不接 trading

---

## 2. 当前 main 状态

- main 最新 commit：**`170617c`**
- commit message：`docs(contract): Step 2G-8D extend replay coverage design`
- 上游：`origin/main` 已同步
- 测试基线：**2642 passed / 0 failed / 10 skipped / 26 warnings /
  94 subtests**（与 Step 3R-2 终点 commit `e2a681b` 一致；本步骤无
  代码改动，无回归）

本步骤新增文件（已 merge 到 main）：

| 路径 | 类型 | 说明 |
|---|---|---|
| `tasks/step_2g8d_extend_replay_coverage_design.md` | 新增 | 15 节、397 行；W4 范围 + cutoff 规则 + manifest schema + 6 子步骤实施顺序 |

本 checkpoint 文档（即本文件）尚未 commit；本轮只写文档、**不**
commit / push。

| 项 | 是否触碰 |
|---|---|
| 改代码 | ❌ 否 |
| 写 DB | ❌ 否 |
| 跑 replay | ❌ 否 |
| 接 yfinance / 网络 | ❌ 否 |
| 接 trading API | ❌ 否 |
| 触碰 2026 final test | ❌ 否 |

---

## 3. W4 范围

| 字段 | 值 |
|---|---|
| **W4 start** | **2024-08-03**（与 W3 终点 2024-08-02 自然衔接） |
| **W4 end** | **2025-12-31**（含；不含 2026） |
| **用途** | Step 3R-4 **optional 4-fold validation**；W4 启用前 3R-4 是 3-fold |
| **是否包含 2026-01-01** | **❌ 否**；永久封禁 |
| **是否改变 W1 / W2 / W3 baseline** | **❌ 否**；W1 / W2 / W3 的 paired 数字（~ 130 / ~ 100 / ~ 56，合计 ~ 286）保持不变 |
| **W4 paired（估）** | tbd（取决于实施后实际生成；本 checkpoint 阶段为 `null`） |
| **是否阻塞 3-fold v1 协议** | **❌ 否**；3-fold（W1+W2+W3）已可启动 3R-3 / 3R-6 candidate validation |
| **是否阻塞 3R-2 helper** | **❌ 否**；helper 已 merge（commit `e2a681b`） |

W1 / W2 / W3 / W4 / final test 全图（来自 3R-4 §3）：

| window | date range | paired (估) | status |
|---|---|---:|---|
| W1 | 2023-01-03 → 2023-08-31 | ~ 130 | **v1 required** |
| W2 | 2023-09-01 → 2024-02-29 | ~ 100（含 2024-02 shock 月） | **v1 required** |
| W3 | 2024-03-01 → 2024-08-02 | ~ 56 | **v1 required** |
| **W4** | **2024-08-03 → 2025-12-31** | **tbd** | **optional**（本 checkpoint 锁定） |
| **final test** | **2026-01-01 → ∞** | — | **permanently forbidden** |

---

## 4. final test cutoff

| 字段 | 值 |
|---|---|
| `final_test_cutoff` | **`2026-01-01`** |
| 状态 | **永久封禁**（与 Step 3R-0 / 3R-4 §3.3 一致） |
| 是否允许"跑到 2026 再过滤" | **❌ 否**；必须在 query / loop 起点 hard stop |
| 是否允许 inspect / preview | **❌ 否**；包括"看一眼回头改" |
| T+1 outcome 跨到 2026 | **❌ 不得读取**；W4 paired 数自然减 1 ~ 2 个边界样本 |
| `final_test_touched` | **必须保持 `false`**；任何 `true` → 整个 W4 输出作废 + 任务中止 |
| hyperparameter selection / threshold tuning 是否读 2026 | **❌ 否** |

### 4.1 cutoff 实现位置（继承 design §6.2）

| 位置 | 实现方式 |
|---|---|
| replay 主循环 | `as_of_date_list = [d for d in available_dates if d <= "2025-12-31"]`（**起点过滤**） |
| outcome 读取 | `if outcome_date >= "2026-01-01": skip`（**起点过滤**） |
| manifest 写入 | `final_test_cutoff = "2026-01-01"` 硬编码；`final_test_touched = false` 硬不变量 |
| `summary.md` | 顶部声明 `data_cutoff_used: 2025-12-31` + `final_test_touched: false` |
| 任何 W4 row | row-level `final_test_refusal` 字段；默认 `false`；异常 2026 row → `true` + 整 row 作废 |

---

## 5. 输出目录与文件

### 5.1 输出目录

```
logs/historical_training/three_system_w4_2024_08_2025_12/
```

命名遵循现有 `three_system_1005/` 风格 + `w4_` 前缀 + 显式日期范围。

### 5.2 输出文件

| 文件 | 内容 |
|---|---|
| `predictions.csv` | W4 每个 `as_of_date` 的 prediction snapshot（与 `three_system_1005/predictions.csv` 同 schema） |
| `reviews.csv` | T+1 outcome + review attribution（与 `three_system_1005/reviews.csv` 同 schema） |
| `summary.md` | W4 paired count / accuracy / 月度分布 / coverage stats |
| `regime_labels_snapshot.csv` | 每个 `as_of_date` 的 `regime_labels.v1` 输出（labels + raw_features + warnings；read-only diagnostics） |
| `validation_ready_manifest.json` | `w4_replay_manifest.v1`（详见 §6） |

### 5.3 关键约束

| 约束 | 强制 |
|---|---|
| **不覆盖 `three_system_1005/`** | ✅ |
| **不覆盖 existing baseline 语义** | ✅（W1 / W2 / W3 paired 286 不变） |
| **可删除** | ✅（W4 目录可整体删除；不影响 main 上其它结果） |
| **可重跑** | ✅（replay 可幂等重跑） |
| **不写 main DB**（`avgo_agent.db`） | ✅ |
| **不写 `prediction_log` / `outcome_log` / `review_log` 主表** | ✅ |
| **不调 yfinance / requests / 网络** | ✅（与 1005 replay 一致 offline） |
| **不接 trading API** | ✅ |

---

## 6. manifest schema

`w4_replay_manifest.v1`：

```json
{
  "schema_version": "w4_replay_manifest.v1",
  "replay_window": {
    "start": "2024-08-03",
    "end": "2025-12-31"
  },
  "final_test_cutoff": "2026-01-01",
  "final_test_touched": false,
  "records_generated": null,
  "paired_outcomes": null,
  "status": "planned|ok|error",
  "warnings": []
}
```

### 6.1 字段说明

| 字段 | 说明 |
|---|---|
| `schema_version` | 总是 `"w4_replay_manifest.v1"` |
| `replay_window.start` | 总是 `"2024-08-03"` |
| `replay_window.end` | 总是 `"2025-12-31"` |
| `final_test_cutoff` | 总是 `"2026-01-01"`；硬不变量 |
| `final_test_touched` | bool；**必须** `false`；任何 `true` → 整份报告作废 + 任务中止 |
| `records_generated` | int / null；**design 阶段为 `null`**，实施后填入 |
| `paired_outcomes` | int / null；**design 阶段为 `null`**，实施后填入 |
| `status` | `"planned"`（本 checkpoint 阶段）/ `"ok"`（实施成功）/ `"error"`（实施失败） |
| `warnings` | list of string；累积实施过程中的 warnings |

### 6.2 5 项不变量

| 不变量 | 说明 |
|---|---|
| `schema_version == "w4_replay_manifest.v1"` | 任何变体即视为非本协议输出 |
| `replay_window.start == "2024-08-03"` | 与 W3 终点衔接 |
| `replay_window.end == "2025-12-31"` | W4 上限；不含 2026 |
| `final_test_cutoff == "2026-01-01"` | 硬编码 |
| `final_test_touched == false` | 任何 `true` → 报告作废 |

---

## 7. 与 Step 3R-4 的关系

| 维度 | Step 2G-8D（本步骤） |
|---|---|
| 范围 | 数据层；扩展 W4 paired 池到 2024-08-03 → 2025-12-31 |
| 是否改 3R-4 protocol | **❌ 否**（不改 6 metric / 7 gate / 10 no-go / `regime_validation_report.v1` schema） |
| 是否提供 W4 数据 | **✅ 是** |
| W4 完成后效果 | 3R-4 协议从 **3-fold** 升级到 **4-fold**（W1 / W2 / W3 / W4 都做一次 held-out） |
| W4 是否自动让 candidate pass | **❌ 否**（W4 增加证据强度；任何 candidate 仍必须**完整**通过 7 gate / 6 metric） |
| W4 fold 失败 → candidate 作废？ | **是**：W4 是 4-fold 中的一 fold，按 worst-window 决胜规则失败即整体 fail |
| W4 是否触发 protocol 阈值松绑 | **❌ 否**；阈值调整必须经 launch review |
| 3-fold v1 是否被本步骤阻塞 | **❌ 否**（3-fold 已 launch；W4 是 conditional 增强） |

→ Step 2G-8D **只**提供 W4 数据；Step 3R-4 协议**永远**是评分层；
两者解耦；W4 仅增强 validation strength，不改 gate threshold。

---

## 8. 与 Step 3R-2 的关系

| 维度 | Step 3R-2 helper（已 merge，commit `e2a681b` / `db7618b`） |
|---|---|
| W4 replay 是否可调 `build_regime_labels` | **✅ 可（read-only）**；为 W4 每个 `as_of_date` 生成 `regime_labels.v1` snapshot |
| 输出位置 | `logs/historical_training/three_system_w4_2024_08_2025_12/regime_labels_snapshot.csv` |
| 这些 labels 是 production decision 输入吗 | **❌ 否**；只是 diagnostics |
| 这些 labels 是否宣称 candidate pass / fail | **❌ 否**；3R-2 helper §8 已 ban；W4 也继承禁令 |
| 这些 labels 是否优化 thresholds | **❌ 否**；继续用 3R-1 §5 design candidates 的阈值 |
| 这些 labels 是否写 DB | **❌ 否** |
| 这些 labels 是否触发任何 sidecar / UI 渲染 | **❌ 否** |
| `final_test_refusal` 路径 | 2024-08-03 → 2025-12-31 范围内 → `false`；任何 2026 行 → `true` + row 作废 |

→ W4 replay 调用 3R-2 helper 仅为生成原始 label 数据；本步骤继续
**不**做 validation 判定 / 不调阈值 / 不写 DB / 不优化 formula。

---

## 9. 实施顺序冻结

未来必须按以下顺序，每一步独立 checkpoint，**不允许跳步**：

| # | 子步骤 | 范围 | 是否动代码 |
|---|---|---|---|
| 1 | **Step 2G-8D checkpoint**（即本文件） | 把 design 状态固化进 main；锁定 W4 范围 / cutoff 规则 / manifest schema / 实施顺序 | ❌ 纯 markdown |
| 2 | **Step 2G-8D.1 replay script audit** | 审计 `scripts/run_1005_three_system_replay.py` + 依赖 `services/historical_replay_training.py` 等模块；确认 read-only / offline / 不写 DB / 不接网络；确认是否需要小补丁支持 W4 | 🔍 read-only audit；可能新增 markdown audit doc |
| 3 | **Step 2G-8D.2 tiny smoke window: 2024-08-05 → 2024-08-09** | 5 个 trading day 的 smoke run；验证 cutoff filter / 输出格式 / regime_labels 调用 / runtime；不进 main | ⚙️ 实际跑 smoke replay；产物在本地 / `.claude/scratch/`，**不进 main** |
| 4 | **Step 2G-8D.3 full W4 replay** | 跑完整 2024-08-03 → 2025-12-31；写 `logs/historical_training/three_system_w4_2024_08_2025_12/` | ⚙️ 实际跑 replay；产物进 main（仅 csv / json / md，无 DB） |
| 5 | **Step 2G-8D.4 W4 checkpoint** | 把 W4 final paired count / coverage stats / `final_test_touched=false` 状态归档 | ❌ 纯 markdown |
| 6 | **Step 3R-4.1 4-fold validation helper design** | 在 3R-4 协议下设计 validation helper；产出 `regime_validation_report.v1`；纯 markdown 先行 | ❌ 纯 markdown |

### 9.1 强制规则

| # | 规则 |
|---|---|
| 1 | **不允许直接跑 full W4**（即不允许跳过 8D.1 audit + 8D.2 smoke 直接进 8D.3） |
| 2 | **必须先 audit + tiny smoke**：先 8D.1 read-only audit；再 8D.2 5-day smoke；smoke 通过后才能 8D.3 full |
| 3 | 任何一步发现 2026 触碰 → 整步骤中止 + 回到本 checkpoint |
| 4 | 任何一步发现 W4 paired < 30 → manifest warning + 仍可作 4-fold 的弱 evidence；不阻塞 3-fold v1 |
| 5 | 8D.1 之前**不**跑 replay |
| 6 | 8D.3 之前**不**进 main 的 W4 数据 |
| 7 | 任何子步骤的 hard / forced / required 禁令继承本 checkpoint §12 |

---

## 10. 风险

| # | 风险 | 含义 / 应对 |
|---|---|---|
| 1 | **runtime 可能长**（增量 ~ 350 trading days × 单日 replay 时间） | 推荐先 8D.2 smoke window 5 days 验证，再跑 full W4 |
| 2 | **replay script 可能耦合旧逻辑**（`services.historical_replay_training` / `services.three_system_replay_audit` / `services.replay_record_wiring` 等） | 必须**先**走 8D.1 audit；确认调用链 read-only / 不写 DB / 不接网络 |
| 3 | **W4 可能暴露更多失败**（candidate 在 2024-08 之后表现更差） | 不是坏事；W4 暴露失败正是 validation 的目的；continued NO-GO 也是合法结论 |
| 4 | **2025 可能是新 regime**（例：AI 二级回调 / rate cut 周期变化），导致旧 candidate 跨窗口更不稳 | 预期可能更差；这正是 cross-window protocol 的设计意图（不允许单窗 overfit） |
| 5 | **T+1 outcome 边界要特别小心**：2025-12-31 的 prediction 跨到 2026-01-02 → **不得**读取该 outcome | replay 实施时必须显式 skip；W4 paired 数自然减 1 ~ 2 个边界样本 |
| 6 | **不应把 W4 当 final test**：W4 = 2024-08-03 → 2025-12-31；final test = 2026-01-01 → ∞ | 任何把 W4 当 final test 的判断必须否决 |
| 7 | csv 数据源（`coded_data/AVGO_coded.csv` 等）可能不含 2025 全年数据 | 必须**先确认 csv 范围**；缺数据 → W4 无法生成；必须明示 warning |
| 8 | `as_of_date` 与 trading-day calendar 错位 | replay 必须用 trading-day 序列（与 1005 replay 一致），不允许跨非交易日 |
| 9 | replay 中途中止 → 部分 row 已生成 | manifest `status="error"` + warnings 累积；**不**回写 main DB；可整体重跑 |
| 10 | 用户误以为 W4 完成即代表 candidate pass | manifest 顶部明示 "W4 提供数据；不宣称 candidate pass / fail" |

---

## 11. 成功标准

| # | 标准 | 验证方式 |
|---|---|---|
| 1 | **不触碰 2026 final test** | manifest `final_test_touched=false`；任何 row 含 2026 → row 作废 + 中止 |
| 2 | **W4 输出独立目录** | `logs/historical_training/three_system_w4_2024_08_2025_12/` 与 `three_system_1005/` 互不覆盖 |
| 3 | manifest `final_test_touched=false` | 检查 `validation_ready_manifest.json` |
| 4 | **可统计 W4 paired outcomes** | `paired_outcomes` 字段填入实际值；可用于 3R-4 4-fold |
| 5 | **不写 DB** | `avgo_agent.db` schema / 内容不变；`prediction_log` / `outcome_log` / `review_log` 不被本步骤新增任何行 |
| 6 | **不改 required**（04 / 05 / 07） | 无字段升级 |
| 7 | **不改 UI** | Predict / Review / Dashboard 不渲染 W4 字段 |
| 8 | **full pytest 不受影响** | W4 实施步骤完成时 pytest 维持 ≥ 2642 / 0 failed / 10 skipped（与 commit `e2a681b` / `db7618b` 基线一致或扩张） |
| 9 | **可供 3R-4 4-fold validation 使用** | manifest + predictions.csv + reviews.csv + regime_labels_snapshot.csv 满足 future validation tool 的输入需求 |
| 10 | **不让 `_PROTECTION_LAYER_CONNECTED` 翻 True** | 与 Step 2G-8A v1 / 3R-0 / 3R-4 一致 |
| 11 | **不启 hard / forced / anti_false_exclusion_triggered** | 与全程边界一致 |

---

## 12. 禁止事项

| # | 禁止 | 理由 |
|---|---|---|
| 1 | **不写 DB** | W4 是 read-only artifact |
| 2 | **不覆盖 existing logs**（`three_system_1005/` 等） | W1 / W2 / W3 baseline 必须保留 |
| 3 | **不改 prediction_store** | schema / write path / read path |
| 4 | **不改 run_predict / predict.py / scanner.py** | Step 2G "sidecar-only" 边界继承 |
| 5 | **不改 04 / 05 / 07 required** | Step 2G 全程边界 |
| 6 | **不启 hard / forced / anti_false_exclusion_triggered** | 三重 NO-GO（2G-8 / 8B / 8C） |
| 7 | **不接 trading**（`longbridge` / `broker` / `paper_trade`） | 永不 |
| 8 | **不触碰 2026** | 永久封禁 |
| 9 | **不直接 full replay**（不允许跳过 8D.1 audit + 8D.2 smoke 直接进 8D.3） | 必须先 audit + smoke |
| 10 | **不用 W4 直接调 formula** | candidate 必须先在 3R-3 design + 3R-4 protocol 下走完，再考虑 formula 实施 |
| 11 | **不把 W4 当 final test** | final test = 2026-01-01 → ∞ |
| 12 | **不调 yfinance / requests / 网络** | 与 1005 replay 一致 offline |
| 13 | **不让 W4 自动让 candidate pass** | 增加证据强度 ≠ 通过 gate |
| 14 | **不改 3R-4 protocol thresholds** | 阈值调整必须经 launch review |
| 15 | **不改 3R-2 helper** | helper 已 merge；W4 仅 read-only 调用 |
| 16 | **不让 `_PROTECTION_LAYER_CONNECTED` 翻 True** | 与 8A v1 / 3R-0 / 3R-4 一致 |
| 17 | **不让 `hard_gate_status.protection_layer_connected` 自动 pass** | 同上 |
| 18 | **不改 `hard_exclusion_allowed` / `primary_blocker` 派生** | 同上 |
| 19 | **不触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*`** | 历史防护 |

---

## 13. 下一步建议

按推荐优先级：

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **Step 2G-8D.1 replay script audit** | 审计 `scripts/run_1005_three_system_replay.py` + 依赖；read-only audit；纯 markdown 输出 | **本轮 / 下一轮**（commit 本 checkpoint 之后） |
| 2 | **Step 2G-8D.2 tiny smoke window**（2024-08-05 → 2024-08-09，5 trading day） | smoke run；验证 cutoff filter / 输出格式 / regime_labels 调用 / runtime | 高（在 8D.1 audit 之后） |
| 3 | **Step 2G-8D.3 full W4 replay** | 跑完整 2024-08-03 → 2025-12-31；**only after audit + smoke** | 中（8D.2 smoke 通过后） |
| 4 | **Step 2G-8D.4 W4 checkpoint** | W4 最终状态归档 | 中（8D.3 之后） |
| 5 | **Step 3R-4.1 4-fold validation helper design** | 纯 markdown 先行；产出 `regime_validation_report.v1` | 中（3R-3 candidate 出 + W4 完成后） |
| 6 | **不推荐**直接跑 full W4 | 必须先 audit + smoke | **❌** |
| 7 | **不推荐**让 W4 直接进 production decision | W4 仅作 cross-window validation 数据 | **❌** |
| 8 | **不推荐**触碰 2026 final test range | 永久封禁 | **❌** |
| 9 | **不推荐**升级 04 required schema | Step 2G 全程边界 | **❌** |
| 10 | **不推荐** R4 hard implementation | Step 2G-8 / 8B / 8C 三重 NO-GO 已锁定 | **❌** |
| 11 | **不推荐**让 `_PROTECTION_LAYER_CONNECTED` 翻 True / Gate 5 / Gate 6 自动 pass | 与 Step 2G-8A v1 / 3R-0 / 3R-4 一致 | **❌** |

**关键判断**：
- 顺序 = 本 checkpoint → 8D.1 audit → 8D.2 smoke → 8D.3 full W4 →
  8D.4 W4 checkpoint → 3R-4.1 validation helper design
- Step 2G-8D 与 Step 3R-2 / 3R-3 / 3R-4 v1 协议**解耦可并行**；3-fold
  v1 不依赖 W4

---

## 14. 严守边界

本文是**纯 checkpoint markdown**：

- ❌ 没改任何代码（`services/*` / `ui/*` / `tests/*` / `scripts/*` 全部未触碰）
- ❌ 没改 DB schema
- ❌ 没写 DB
- ❌ 没运行 replay
- ❌ 没改 `run_predict` / `predict.py` / `scanner.py` /
  `prediction_store.py` / `app.py`
- ❌ 没改 `services/regime_features_builder.py` /
  `services/regime_labels_builder.py` /
  `services/regime_diagnostics_dashboard.py` /
  `services/anti_false_exclusion_dashboard.py` /
  `services/soft_metadata_simulator.py` /
  `services/protection_layer_diagnostics.py` /
  `services/historical_replay_training.py` /
  `services/three_system_replay_audit.py` /
  `services/replay_record_wiring.py` /
  `services/projection_three_systems_renderer.py` /
  `ui/protection_layer_diagnostics_renderer.py` / 任何 ui 模块 /
  任何 builder
- ❌ 没改 `scripts/run_1005_three_system_replay.py` 或任何 replay 脚本
- ❌ 没改 04 / 05 / 07 任何 required 字段
- ❌ 没启用 `hard` / `forced_exclusion` /
  `anti_false_exclusion_triggered`
- ❌ 没接 `yfinance` / `requests` / 任何网络
- ❌ 没接 trading API / `longbridge` / `broker` / `paper_trade`
- ❌ 没让 `_PROTECTION_LAYER_CONNECTED` 翻 True
- ❌ 没让 `hard_gate_status.protection_layer_connected` 自动 pass
- ❌ 没改 `hard_exclusion_allowed` / `primary_blocker` 派生
- ❌ 没触碰 2026-01-01 之后 final test range
- ❌ 没运行 replay / 没新写 replay 行
- ❌ 没改 Step 3R-4 protocol thresholds（6 metric / 7 gate / 10 no-go）
- ❌ 没改 Step 3R-2 helper 行为
- ❌ 没改 Step 2G-8D design（commit `170617c`）
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` /
  `avgo_agent.db.backup_*`
- ❌ 没运行 `pytest`（本轮纯文档；测试基线维持 commit `170617c` 时
  的 2642 / 0 failed / 10 skipped）
- ✅ 只新增 1 份 markdown checkpoint 文档（本文件）
