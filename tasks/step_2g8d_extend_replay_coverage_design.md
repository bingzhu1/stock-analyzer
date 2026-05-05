# Step 2G-8D — Extend Replay Coverage Design

> **设计文档（extend replay coverage design），不实现，不改代码，不写 DB，不运行 replay。**
> 本文档**冻结** Step 2G-8D 的范围、目标、数据 / 输出建议、replay
> 方法原则、final test cutoff 规则、`w4_replay_manifest.v1` schema、
> 与 Step 3R-4 协议 / Step 3R-2 helper 的衔接边界、风险、推荐实施顺序。
>
> 本轮**不动任何代码**：不改 `predict.py` / `run_predict` /
> `scanner.py` / `prediction_store.py` / `app.py` / 任何 `ui/*` /
> `services/*` / 任何 builder / DB schema / 任何 test 中的任何一处。
>
> **本文不实现 replay 工具、不跑 replay、不写 DB、不调 yfinance、
> 不接 trading API**；只在 markdown 层冻结 W4 数据扩展的设计本身，
> 给后续 8D.1 / 8D.2 / 8D.3 / 8D.4 提供边界。

---

## 1. 背景

- **Step 3R-4** cross-window validation protocol design + checkpoint
  已完成并进入 main（commits `a58aad4` / `abe3ba2`）
- Step 3R-4 §3.2 已把 **W4 = 2024-08-03 → 2025-12-31** 定义为
  **optional validation window**
- Step 3R-4 §3.1 当前 v1 paired baseline = **286**，analysis range
  截止 **2024-08-02**
- **当前 replay coverage**：W1 / W2 / W3 三窗共 ~ 286 paired，对应
  `logs/historical_training/three_system_1005/`（与 Step 2G-7C / 8B /
  8C 一致），数据范围在 2024-08-02 之前
- **W4 尚未覆盖**：没有 2024-08-03 → 2025-12-31 的 replay 数据；
  Step 3R-4 v1 协议是 **3-fold leave-one-window-out**，4-fold 扩展
  必须等本步骤
- 后续 **3R-3 smoothing candidate** / **3R-6 read-only simulator**
  在 3-fold v1 协议下虽可启动，但 **W4 缺失会让 validation strength
  偏弱**（无法看 sustained AI bull rally + 2024-08 之后 regime
  shift 的 candidate 行为）
- **本步骤只设计**，不运行 replay、不写 DB、不接网络

---

## 2. 当前数据状态

| 字段 | 值 |
|---|---|
| **当前 paired baseline** | **286** |
| 当前 analysis range | **2023-01-03 → 2024-08-02** |
| 当前覆盖窗口 | W1 / W2 / W3（3R-4 §3.1） |
| W4 覆盖 | **❌ 未覆盖** |
| W4 计划范围 | **2024-08-03 → 2025-12-31** |
| W4 paired（估） | tbd（取决于本步骤实施后实际生成） |
| **2026-01-01 → ∞** | **final test set；永久封禁**（Step 3R-0 / 3R-4 §3.3） |
| 当前 replay 输出目录 | `logs/historical_training/three_system_1005/`（已 merge 到 main） |
| 当前 replay 触发脚本 | `scripts/run_1005_three_system_replay.py`（read-only audit；offline） |
| `prediction_store` 是否被本步骤影响 | **❌ 否** |
| `avgo_agent.db` 是否被本步骤影响 | **❌ 否** |

W1 / W2 / W3 的具体 paired 估算（来自 3R-4 §3.1）：

| window | date range | paired (估) |
|---|---|---:|
| W1 | 2023-01-03 → 2023-08-31 | ~ 130 |
| W2 | 2023-09-01 → 2024-02-29 | ~ 100（含 2024-02 shock 月） |
| W3 | 2024-03-01 → 2024-08-02 | ~ 56 |
| **合计 v1 baseline** | | **~ 286** |

---

## 3. 目标范围

| 项 | 值 |
|---|---|
| **新增 replay coverage** | **2024-08-03 → 2025-12-31** |
| **上限** | **2025-12-31**（含），**绝对不**含 2026-01-01 |
| **下限** | **2024-08-03**（与 W3 终点 2024-08-02 自然衔接） |
| 是否覆盖 final test | **❌ 否**（2026 永久封禁） |
| 是否改变 2023-2024 baseline 语义 | **❌ 否**（W1 / W2 / W3 完全保留） |
| 是否覆盖现有 `three_system_1005/` 目录 | **❌ 否**（W4 输出独立目录） |
| 用途 | 为 Step 3R-4 4-fold validation 提供 W4 数据 |
| 是否阻塞 3R-2 helper 启动 | **❌ 否**（已启动；commit `e2a681b`） |
| 是否阻塞 3R-4 v1 协议 | **❌ 否**（3-fold 已可用；W4 是 conditional 增强） |
| 是否触发任何 hard / forced / required upgrade | **❌ 否** |
| 是否改 prediction_store | **❌ 否** |
| 是否改 run_predict / predict.py / scanner.py | **❌ 否** |

---

## 4. 数据与输出建议

### 4.1 输出目录建议

```
logs/historical_training/three_system_w4_2024_08_2025_12/
```

命名遵循现有 `three_system_1005/` 风格 + `w4_` 前缀 + 显式日期范围
后缀，便于一眼区分。

### 4.2 输出文件建议

| 文件 | 内容 | 与现状对齐 |
|---|---|---|
| `predictions.csv` | W4 每个 `as_of_date` 的 prediction snapshot（与 `three_system_1005/predictions.csv` 同 schema） | ✅ |
| `reviews.csv` | T+1 outcome + review attribution（与 `three_system_1005/reviews.csv` 同 schema） | ✅ |
| `summary.md` | W4 paired count / accuracy / 月度分布 / coverage stats | ✅ |
| `regime_labels_snapshot.csv` | 每个 `as_of_date` 的 `regime_labels.v1` 输出（labels + raw_features + warnings；read-only diagnostics）| 新增（与 3R-2 helper 衔接） |
| `validation_ready_manifest.json` | `w4_replay_manifest.v1`（详见 §7） | 新增 |
| `_run.log` | replay 运行日志 | ✅（与 1005 一致） |

### 4.3 设计原则

| 原则 | 说明 |
|---|---|
| **建议设计** | 本文只是 layout 建议；实际生成由后续 8D.2 / 8D.3 实施 |
| **不写 DB** | 所有输出落 CSV / JSON / MD，**不**入 `avgo_agent.db` |
| **不覆盖原 baseline** | `three_system_1005/` 完全保留；W4 输出独立目录 |
| **不覆盖 existing baseline 语义** | W1 / W2 / W3 paired 数字保持 286 |
| **可删除** | W4 目录可整体删除；不影响 main 上其它结果 |
| **可重跑** | replay 可幂等重跑；同一 W4 范围可生成相同输出 |
| **不依赖网络** | 与 1005 replay 一致：offline；用本地 csv（`coded_data/AVGO_coded.csv` / `coded_data/SOXX_coded.csv` / 等）|
| **不接 trading API** | `longbridge` / `broker` / `paper_trade` 永远禁止 |

---

## 5. replay 方法原则

| # | 原则 |
|---|---|
| 1 | **anti-lookahead**：每个 date `D` 只能用 `<= D` 的数据做 prediction context；T+1 outcome **只在** review 阶段读取（与 3R-1 §7 / 3R-2 §7 / 3R-4 §4.2 一致） |
| 2 | **strict-causal monthly context**：earnings / breakout / shock 月份 derive 必须只用当天及以前数据，事后**不**回标 |
| 3 | **不得用 2026 数据**：任何 `as_of_date >= 2026-01-01` → 立即停止；不得 inspect / preview / "看一眼回头改" |
| 4 | **不得把 W4 结果回写 main DB**：W4 output 是 read-only artifact；不写 `prediction_log` / `outcome_log` / `review_log` 主表 |
| 5 | **不得改变 prediction_store**：schema / write path / read path 全部不动 |
| 6 | **不得改变 production UI**：Predict / Review / Dashboard 不渲染 W4 出来的字段（除非走未来独立 step） |
| 7 | **不动 04 / 05 / 07 required**：W4 不触发任何 required 字段升级 |
| 8 | **不启 hard / forced / anti_false_exclusion_triggered**：与 Step 2G-8 / 8A / 8B / 8C / 3R-0 / 3R-4 一致 |
| 9 | **不触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*`** |
| 10 | **不调 yfinance / requests / 任何网络**：与现有 1005 replay 同 offline |

---

## 6. final test cutoff 规则

W4 是本项目**距离 2026-01-01 最近**的合法窗口；cutoff 规则必须**写
死在 query / loop 起点**，不允许"跑到 2026 再过滤"。

### 6.1 hard rules

| # | 规则 |
|---|---|
| 1 | **target replay date 必须 ≤ 2025-12-31**（含）；任何 `as_of_date >= 2026-01-01` → 中止 |
| 2 | 任何 script / loop 起点的 `for date in ...:` 范围**必须**预先过滤到 `<= 2025-12-31`；不允许"跑全 csv 后过滤" |
| 3 | 如果 **任何 script 准备读取 / 生成 2026-01-01 之后数据**（输入或输出 row 的 `as_of_date >= 2026-01-01`）→ **必须中止** |
| 4 | 任何发现 `as_of_date >= 2026-01-01` 的输出 row → **必须标记 `final_test_refusal`**（在 manifest / summary 中）+ 整个该 row 作废 |
| 5 | **不允许"跑到 2026 再过滤"**：必须在 query / loop 起点 hard stop；防止"看一眼 2026 再回头改" |
| 6 | 如果 csv 数据源含 2026 行 → 必须**先**截断到 `<= 2025-12-31`，然后再进 replay；中间不读 2026 行 |
| 7 | T+1 outcome 也受 cutoff 约束：`prediction_date = 2025-12-31` 的 T+1 outcome 在 2026-01-02（ next trading day）→ **不**读取该 outcome（保持 W4 paired 上界 ≤ 实际最后一个 outcome 在 2025-12-31 的 prediction） |
| 8 | 任何 hyperparameter selection / threshold tuning / candidate eligibility check 都**不得**读 2026 数据 |

### 6.2 cutoff 实现位置

| 位置 | 实现方式 |
|---|---|
| replay 主循环 | `as_of_date_list = [d for d in available_dates if d <= "2025-12-31"]`（**起点过滤**） |
| outcome 读取 | `if outcome_date >= "2026-01-01": skip`（**起点过滤**） |
| manifest 写入 | `final_test_cutoff = "2026-01-01"` 硬编码；`final_test_touched = False` 必须为 `False` |
| summary.md | 顶部声明 "data_cutoff_used: 2025-12-31" + "final_test_touched: False" |
| 任何 W4 row | row-level `final_test_refusal` 字段（默认 `False`；如果 row 异常带 2026 date → `True` + row 作废） |

---

## 7. W4 validation manifest

设计 `validation_ready_manifest.json`（schema_version = `w4_replay_manifest.v1`）：

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

### 7.1 字段说明

| 字段 | 类型 | 说明 |
|---|---|---|
| `schema_version` | string | 总是 `"w4_replay_manifest.v1"` |
| `replay_window.start` | string (ISO 8601) | 总是 `"2024-08-03"`（与 W3 终点 2024-08-02 自然衔接） |
| `replay_window.end` | string (ISO 8601) | 总是 `"2025-12-31"`（W4 上限；不含 2026） |
| `final_test_cutoff` | string (ISO 8601) | 总是 `"2026-01-01"`；硬不变量 |
| `final_test_touched` | bool | 必须为 `false`；任何 `true` → 整个 W4 输出作废 + 任务中止 |
| `records_generated` | int / null | W4 实际生成的 prediction 行数；本设计阶段为 `null`，实施后填入 |
| `paired_outcomes` | int / null | W4 实际可配 outcome 的 paired 行数；本设计阶段为 `null`，实施后填入 |
| `status` | enum | `"planned"`（本设计阶段）/ `"ok"`（实施成功）/ `"error"`（实施失败） |
| `warnings` | list of string | 实施过程中累积的 warnings；本设计阶段为 `[]` |

### 7.2 manifest 不变量

| 不变量 | 强制 |
|---|---|
| `schema_version == "w4_replay_manifest.v1"` | 任何变体即视为非本协议输出 |
| `replay_window.start == "2024-08-03"` | 与 W3 终点衔接 |
| `replay_window.end == "2025-12-31"` | W4 上限；不含 2026 |
| `final_test_cutoff == "2026-01-01"` | 硬编码 |
| `final_test_touched == false` | 任何 `true` → 报告作废 |

---

## 8. 与 Step 3R-4 的关系

| 维度 | Step 2G-8D（本步骤） |
|---|---|
| 范围 | 数据层；扩展 W4 paired 池到 2024-08-03 → 2025-12-31 |
| 是否改 3R-4 protocol | **❌ 否**（不改 6 metric / 7 gate / 10 no-go / `regime_validation_report.v1` schema） |
| 是否提供 W4 数据 | **✅ 是** |
| W4 完成后效果 | 3R-4 协议从 **3-fold** 升级到 **4-fold**（W1 / W2 / W3 / W4 都做一次 held-out） |
| W4 是否自动让 candidate pass | **❌ 否**（W4 增加证据强度；任何 candidate 仍必须**完整**通过 7 gate / 6 metric） |
| W4 失败 → candidate 作废？ | **是**：W4 是 4-fold 中的一 fold，按 worst-window 决胜规则失败即整体 fail |
| W4 是否触发 protocol 阈值松绑 | **❌ 否**；阈值调整必须经 launch review，不允许"差一点没过"放松 |
| 3-fold v1 是否被本步骤阻塞 | **❌ 否**（3-fold 已 launch；W4 是 conditional 增强） |

→ Step 2G-8D **只**提供 W4 数据；Step 3R-4 协议**永远**是评分层；
两者解耦；W4 仅增强 validation strength，不改 gate threshold。

---

## 9. 与 Step 3R-2 的关系

| 维度 | Step 3R-2 helper（已 merge，commit `e2a681b`） |
|---|---|
| W4 replay 是否可调 `build_regime_labels` | **✅ 可（read-only）**；为 W4 每个 `as_of_date` 生成 `regime_labels.v1` snapshot |
| 输出位置 | `logs/historical_training/three_system_w4_2024_08_2025_12/regime_labels_snapshot.csv` |
| 这些 labels 是 production decision 输入吗 | **❌ 否**；只是 diagnostics |
| 这些 labels 是否宣称 candidate pass / fail | **❌ 否**；3R-2 helper §8 已 ban；W4 也继承禁令 |
| 这些 labels 是否写 DB | **❌ 否** |
| 这些 labels 是否优化 thresholds | **❌ 否**；继续用 3R-1 §5 design candidates 的阈值 |
| 这些 labels 是否触发任何 sidecar / UI 渲染 | **❌ 否**；W4 输出仅作为 future 3R-4 协议下 validation 的辅助 |
| 是否触发 `final_test_refusal` 路径 | 2024-08-03 → 2025-12-31 范围内 → `final_test_refusal=False`；任何 2026 行 → `final_test_refusal=True` + row 作废 |

→ W4 replay 调用 3R-2 helper 仅为生成原始 label 数据；本步骤继续
**不**做 validation 判定 / 不调阈值 / 不写 DB / 不优化 formula。

---

## 10. 风险

| # | 风险 | 含义 / 应对 |
|---|---|---|
| 1 | 数据量增加可能**暴露更多失败**（candidate 在 2024-08 之后表现更差） | **不是坏事**；W4 暴露失败正是 validation 的目的；continued NO-GO 也是合法结论 |
| 2 | W4 可能包含 2025 新 regime（例：AI 二级回调 / rate cut 周期变化），导致旧 candidate 跨窗口更不稳 | 预期可能更差；这正是 cross-window protocol 的设计意图（不允许单窗 overfit） |
| 3 | runtime 较长（增量 ~ 350 trading days × 单日 replay 时间） | 推荐先 **smoke window 5 days** 验证，再跑 full W4 |
| 4 | replay script 可能与现有 production code 耦合（共享 `services.historical_replay_training` / `services.three_system_replay_audit` 等模块） | 必须**先 audit replay script**（8D.1）；确认调用链 read-only / 不写 DB / 不接网络 |
| 5 | csv 数据源（`coded_data/AVGO_coded.csv` 等）可能不含 2025 全年数据 | 必须**先确认 csv 范围**；缺数据 → W4 无法生成；必须明示 warning |
| 6 | `as_of_date` 与 trading-day calendar 错位 | replay 必须用 trading-day 序列（与 1005 replay 一致），不允许跨非交易日 |
| 7 | W4 输出与 main DB 的偶发同名 column 冲突 | W4 永远不写 DB；CSV / JSON 独立目录；冲突不可能 |
| 8 | T+1 outcome 在 2025-12-31 的 prediction 跨到 2026-01-02 | 必须**不**读取该 outcome；W4 paired 数自然减 1 ~ 2 个边界样本 |
| 9 | replay 中途中止 → 部分 row 已生成 | manifest `status="error"` + warnings 累积；**不**回写 main DB；可整体重跑 |
| 10 | 用户误以为 W4 完成即代表 candidate pass | manifest 顶部明示 "W4 提供数据；不宣称 candidate pass / fail" |

---

## 11. 成功标准

| # | 标准 | 验证方式 |
|---|---|---|
| 1 | **不触碰 2026 final test** | manifest `final_test_touched=false`；任何 row 含 2026 → row 作废 + 中止 |
| 2 | **W4 输出独立目录** | `logs/historical_training/three_system_w4_2024_08_2025_12/` 与 `three_system_1005/` 互不覆盖 |
| 3 | manifest 标记 `final_test_touched=false` | 检查 `validation_ready_manifest.json` |
| 4 | 可以**统计 W4 paired outcomes** | `paired_outcomes` 字段填入实际值；可用于 3R-4 4-fold |
| 5 | **不改 DB** | `avgo_agent.db` schema / 内容不变；`prediction_log` / `outcome_log` / `review_log` 不被本步骤新增任何行 |
| 6 | **不改 required** | 04 / 05 / 07 任何字段 |
| 7 | **不改 UI** | Predict / Review / Dashboard 不渲染 W4 字段 |
| 8 | **不影响 full pytest** | W4 实施步骤完成时 pytest 维持 ≥ 2642 passed / 0 failed / 10 skipped（与 commit `e2a681b` 基线一致或扩张） |
| 9 | **可供 Step 3R-4 4-fold validation 使用** | manifest + predictions.csv + reviews.csv + regime_labels_snapshot.csv 满足 future validation tool 的输入需求 |
| 10 | **不让 `_PROTECTION_LAYER_CONNECTED` 翻 True** | 与 Step 2G-8A v1 / 3R-0 / 3R-4 一致 |
| 11 | **不启 hard / forced / anti_false_exclusion_triggered** | 与全程边界一致 |

---

## 12. 禁止事项

| # | 禁止 | 理由 |
|---|---|---|
| 1 | **不写 DB** | W4 是 read-only artifact；写 DB = 改变 production state |
| 2 | **不覆盖 existing logs**（`three_system_1005/` 等） | W1 / W2 / W3 baseline 必须保留；W4 独立目录 |
| 3 | **不改 prediction_store** | schema / write path / read path |
| 4 | **不改 run_predict / predict.py / scanner.py** | Step 2G "sidecar-only" 边界继承 |
| 5 | **不改 04 / 05 / 07 required** | Step 2G 全程边界 |
| 6 | **不启 hard / forced / anti_false_exclusion_triggered** | 三重 NO-GO（2G-8 / 8B / 8C）|
| 7 | **不接 trading**（`longbridge` / `broker` / `paper_trade`）| 永不 |
| 8 | **不触碰 2026** | 永久封禁 |
| 9 | **不用 W4 直接调 formula** | candidate 必须先在 3R-3 design + 3R-4 protocol 下走完，再考虑 formula 实施 |
| 10 | **不把 W4 当 final test** | final test = 2026-01-01 → ∞；W4 = 2024-08-03 → 2025-12-31 |
| 11 | **不调 yfinance / requests / 任何网络** | 与 1005 replay 一致 offline |
| 12 | **不让 W4 自动让 candidate pass** | 增加证据强度 ≠ 通过 gate |
| 13 | **不改 3R-4 protocol thresholds**（6 metric / 7 gate） | thresholds 由 launch review 调，不偷跑 |
| 14 | **不改 3R-2 helper** | helper 已 merge；W4 仅 read-only 调用 |
| 15 | **不让 `_PROTECTION_LAYER_CONNECTED` 翻 True** | 与 8A v1 / 3R-0 / 3R-4 一致 |
| 16 | **不让 `hard_gate_status.protection_layer_connected` 自动 pass** | 同上 |
| 17 | **不改 `hard_exclusion_allowed` / `primary_blocker` 派生** | 同上 |
| 18 | **不触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*`** | 历史防护 |
| 19 | **不在 hyperparameter selection / threshold tuning 中读 W4 之外的数据** | 任何"看一眼 W4 再回头改阈值"必须经 launch review |

---

## 13. 推荐实施顺序

未来可按以下顺序，每一步独立 checkpoint，**不允许跳步**：

| # | 子步骤 | 范围 | 是否动代码 |
|---|---|---|---|
| 1 | **Step 2G-8D checkpoint** | 把本 design 固化进 main；锁定 W4 范围 / cutoff 规则 / manifest schema | ❌ 纯 markdown |
| 2 | **Step 2G-8D.1 replay script audit** | 审计 `scripts/run_1005_three_system_replay.py` + 依赖 `services/historical_replay_training.py` 等模块；确认 read-only / offline / 不写 DB / 不接网络；确认是否需要小补丁支持 W4 | 🔍 read-only audit；可能新增 markdown audit doc |
| 3 | **Step 2G-8D.2 tiny smoke window: 2024-08-05 → 2024-08-09** | 5 个 trading day 的 smoke run；验证 cutoff filter / 输出格式 / regime_labels 调用 / runtime；不进 main | ⚙️ 实际跑 replay；产物在 `.claude/scratch/` 或本地（暂不进 main） |
| 4 | **Step 2G-8D.3 full W4 replay** | 跑完整 2024-08-03 → 2025-12-31；写 `logs/historical_training/three_system_w4_2024_08_2025_12/` | ⚙️ 实际跑 replay；产物进 main（仅 csv / json / md，无 DB） |
| 5 | **Step 2G-8D.4 W4 checkpoint** | 把 W4 final paired count / coverage stats / `final_test_touched=false` 状态归档 | ❌ 纯 markdown |
| 6 | **Step 3R-4.1 4-fold validation helper design** | 在本协议下设计 validation helper；产出 `regime_validation_report.v1`；纯 markdown 先行 | ❌ 纯 markdown |

**关键规则**：
- 顺序不可跳
- 任何一步发现 2026 触碰 → 整步骤中止 + 回到本 checkpoint
- 任何一步发现 W4 paired < 30 → manifest warning + 仍可作 4-fold 的弱 evidence；不阻塞 3-fold v1
- 8D.1 之前**不**跑 replay
- 8D.3 之前**不**进 main 的 W4 数据

---

## 14. 下一步建议

按推荐优先级：

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **commit 本 design** | 把 §1-15 固化到 main | **本轮 / 下一轮** |
| 2 | **Step 2G-8D checkpoint** | 紧接 commit 1，把本 design 状态归档 + W4 范围 + manifest schema 锁定 | **下一轮** |
| 3 | **Step 2G-8D.1 replay script audit** | 审计现有 1005 replay 链，确认是否能扩到 W4 / 是否需要小补丁 | 中（在 8D checkpoint 之后） |
| 4 | **不推荐**直接跑 full W4 replay | 必须先过 8D.1 audit + 8D.2 smoke | **❌** |
| 5 | **不推荐**让 W4 直接进 production decision | W4 仅作 cross-window validation 数据；不进 hard gate | **❌** |
| 6 | **不推荐** 在没有 3R-3 candidate 的情况下设计 4-fold validation helper | 无 candidate → 无 input；先等 3R-3 design | **❌** |
| 7 | **不推荐** 触碰 2026 final test range | 永久封禁 | **❌** |
| 8 | **不推荐** 升级 04 required schema | Step 2G 全程边界 | **❌** |
| 9 | **不推荐** R4 hard implementation | Step 2G-8 / 8B / 8C 三重 NO-GO 已锁定 | **❌** |
| 10 | **不推荐** 让 `_PROTECTION_LAYER_CONNECTED` 翻 True / Gate 5 / Gate 6 自动 pass | 与 Step 2G-8A v1 / 3R-0 / 3R-4 一致 | **❌** |

**关键判断**：
- 顺序 = 本 design → 8D checkpoint → 8D.1 audit → 8D.2 smoke → 8D.3 full W4 → 8D.4 W4 checkpoint → 3R-4.1 validation helper design
- Step 2G-8D 与 Step 3R-2 / 3R-3 / 3R-4 v1 协议**解耦可并行**；3-fold v1 不依赖 W4

---

## 15. 严守边界

本文是**纯 design markdown**：

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
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` /
  `avgo_agent.db.backup_*`
- ❌ 没运行 `pytest`（本轮纯文档；测试基线维持 commit `e2a681b` 的
  2642 / 0 failed / 10 skipped）
- ✅ 只新增 1 份 markdown design 文档（本文件）
