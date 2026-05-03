# Step 2G — Exclusion Soft/Hard Checkpoint

> 状态：Step 2G-1 ~ 2G-2 已全部完成。Step 2G-2 是唯一产生 commit 的子步（`9d55a80`）；2G-1 是只读诊断，不产生代码改动。本文件是进入 Step 2F-4（真实回放数据方案）/ DB hygiene / Step 3+（真规则启用）之前的 handoff 快照。
> 只写文档，不改任何业务代码。

## 1. 当前完成状态

| 子步 | 主题 | commit | 关键产出 |
|---|---|---|---|
| 2G-1 | 只读诊断 exclusion 当前不可升级 | —（无代码改动） | 4 条互相独立的阻塞理由：0 个 (contract × outcome) pair / soft_signal 全部坍缩到 peer_weaken / path_risk 仅 medium / 无 baseline hit rate / 无 anti-false-exclusion 保护层。同步识别 8 条候选规则的风险级别（哪些永远不能 hard / 哪些可作 soft 候选） |
| 2G-2 | 冻结 exclusion soft/hard 规则设计文档 | `9d55a80 docs(contract): freeze exclusion soft hard rule design` | `tasks/step_2g_exclusion_soft_hard_design.md`（11 节 / 7 阶段实施路径）；spec 化三档语义、forced_exclusion 边界、anti_false_exclusion 保护逻辑、最小数据需求、4 项核心指标定义 |

## 2. 当前 main 状态

- **main 最新 commit：** `9d55a80 docs(contract): freeze exclusion soft hard rule design`
- **测试基线：** **2094 passed / 0 failed / 10 skipped / 65 subtests**（与 Step 2F 末尾持平；Step 2G 全程零代码改动 = 零基线增量）
- **新增文档（Step 2G-2，已进 main）：**
  - [`tasks/step_2g_exclusion_soft_hard_design.md`](step_2g_exclusion_soft_hard_design.md) — 307 行，纯设计文档

## 3. Step 2G-1 诊断结论

四条互相独立的阻塞理由让当前**完全不能升级 `exclusion_level`**：

### 3.1 0 个 (contract × outcome) pair

- 主项目 DB：`prediction_log` 5 行，valid contract 2 行，**paired_outcomes = 0**
- 3 条带 outcome 的 prediction 都缺 contract_payload（Step 1E migration 之前写入）
- 2 条带 contract 的 prediction（`0e7e37a6-...` / `2fe9eef2-...`）是合成验证记录（`prediction_for_date=2099-xx-xx`），无对应 outcome
- **无法测任何规则的 false positive / false negative 率**

### 3.2 soft_signal 分布坍缩到 peer_weaken

- 全部 valid 样本 `soft_signal == "peer_weaken"`（dashboard 实跑确认）
- 没有 `none` 或 `high_path_risk` 的对比样本
- **无法跨 distinct 值做对照分析**

### 3.3 path_risk_level 当前只有 medium

- 全部 valid 样本 `path_risk_level == "medium"`
- 没有 `low` 或 `high` 的样本
- **无法判断 path_risk=high 是否真有"否定"语义**

### 3.4 没有 baseline hit rate

- `confidence_level_summary` 全部 pending，`accuracy=null`
- **不知道"不做 exclusion 时主推演命中率是多少"**——也就没法证明做了 exclusion 后变好了

### 3.5 没有 anti-false-exclusion 保护层

- `big_up_contradiction_card` / `exclusion_reliability_review` / `big_down_tail_warning` / `anti_false_exclusion_audit` 四个模块都是离线 / UI 产物
- 任何一个都未接入主链
- **hard exclusion 一旦启用就没有刹车机制**

## 4. Step 2G-2 设计冻结内容

`tasks/step_2g_exclusion_soft_hard_design.md` 11 节核心要点：

### 4.1 三档语义

| 档位 | 证据要求 | 下游决策 |
|---|---|---|
| `none` | 无 | 完全信任主推演（缺数据时仍 `none`，**不**用 `unknown` 代替） |
| `soft` | 有可观察信号但不构成方向否定 | UI 加 warning；仍读 final_projection |
| `hard` | backtest 支撑 + 通过 §8 指标 | 可选择忽略 final_direction；07 仍 no_trade |

**07 段 `no_trade` 与 exclusion 等级正交**——本项目永不开仓，与 `exclusion_level` 升级无关。

### 4.2 forced_exclusion 与 hard 的关系

- `forced_exclusion=True` **仅允许** `exclusion_level == "hard"` 时出现
- forced 是**系统级拦截**（数据完整性 / contract 破坏 / 已知 bug），**不是普通策略风险**
- 策略层面的"主推演方向不可信"用 hard，**不直接 forced**
- **当前阶段强制禁止 `forced_exclusion=True`**

### 4.3 anti_false_exclusion_triggered 是 hard 的刹车

- 当 hard 规则触发 + 反向证据触发时置 `True`
- **置 True 不自动降级**——是否因此把 hard 降为 soft，是消费层决策
- 候选数据来源：`anti_false_exclusion_audit` / `big_up_contradiction_card` / `big_down_tail_warning` / `exclusion_reliability_review`
- 当前**这四个模块都未接主链**

### 4.4 永远不能直接 hard 的红线（设计文档 §6）

8 条单独使用永远不允许 hard：

- 单独 `soft_signal == "peer_weaken"`（误杀独立行情）
- 单独 `soft_signal == "high_path_risk"`（路径维度 ≠ 方向维度）
- 单独 `path_risk_level == "high"`（同上）
- 单独 `conflicting_factors_count >= N`（过度敏感）
- 单独 `confidence_level == "low"`（已是表达，双重否定）
- 单独 `primary_score_raw` 任何条件（calibration 字段，不是 exclusion 字段）
- 单独 `simulated_trade.extras` 任何字段（07 段是观察 metadata）
- **任何单一 extras 字段**（hard 必须是复合证据 + backtest 支撑）

### 4.5 hard 必须有 backtest 支撑

设计文档 §8 4 项核心指标：
- `false_exclusion_rate ≤ 0.10`
- `missed_exclusion_rate ≤ baseline 错误率`
- `net_benefit ≥ +0.05`
- 不系统性误杀 big-up / 独立行情

## 5. 当前仍然没有改的字段

严格 stub（Step 2G 全程零代码改动，自然保持）：

| 字段 | 当前值 | 说明 |
|---|---|---|
| `exclusion_system.exclusion_level` | `"none"` | 5 个 04 required 字段全部 stub |
| `exclusion_system.exclusion_sources` | `[]` | |
| `exclusion_system.exclusion_reasons` | `[]` | |
| `exclusion_system.forced_exclusion` | `False` | |
| `exclusion_system.anti_false_exclusion_triggered` | `False` | |
| `simulated_trade.trade_action` | `"no_trade"` | 07 段 6 个决策字段策略边界 pinned |
| `simulated_trade.trade_direction` | `"none"` | |
| `simulated_trade.entry_condition / stop_loss_condition / take_profit_condition` | `""` | |
| `simulated_trade.suggested_position_size` | `"0%"` | |
| `simulated_trade.extras.trade_engine_enabled` | `False` | 常量 |
| `confidence_system.historical_score / structure_score / peer_score / exclusion_penalty` | `0.0` | 4 个 score 字段未升真值 |
| `confidence_system.event_score` | `None` | |

## 6. 真启用 soft/hard 前的最小前提

> 与设计文档 §7 + §8 同口径。Step 3+ 真规则启用必须**全部满足**。

### 6.1 数据需求

| 维度 | 最低值 |
|---|---|
| 总 (contract × outcome) pair | **≥ 90** |
| 每个候选规则的触发样本 | **≥ 30** |
| 每个候选规则的非触发对照组 | **≥ 30** |
| `soft_signal` 三档（`none` / `peer_weaken` / `high_path_risk`）各覆盖 | **≥ 30** |
| `path_risk_level` 三档（`low` / `medium` / `high`）各覆盖 | **≥ 30** |
| `confidence_level` 三档（`high` / `medium` / `low`）各覆盖 | **≥ 30** |
| 数据来源 | **真实历史回放或真实运行积累**——禁止合成 outcome |

### 6.2 指标已定义并跑通

- `false_exclusion_rate` 公式定义 + 计算工具实现
- `missed_exclusion_rate` 公式定义 + 计算工具实现
- `baseline_hit_rate` 计算路径
- `net_benefit` 公式定义 + 阈值校准
- 每个候选规则的指标实测值已记录

### 6.3 anti-false-exclusion 保护层

- 至少一个候选模块（如 `anti_false_exclusion_audit`）已接入主链
- 接入方式经过历史样本验证
- 与 hard 规则同时运行的逻辑测试已通过

### 6.4 当前距离

| 维度 | 目标 | 当前 | 距离 |
|---|---|---|---|
| 总 (contract × outcome) pair | ≥ 90 | **0** | 缺 90 |
| `soft_signal` 三档覆盖 | 各 ≥ 30 | 仅 `peer_weaken` 1 | 缺两档 |
| `path_risk` 三档覆盖 | 各 ≥ 30 | 仅 `medium` 1 | 缺两档 |
| `confidence` 三档覆盖 | 各 ≥ 30 | 仅 `medium` 1 | 缺两档 |
| 指标定义已跑通 | ✓ | 公式定义在设计文档 / 工具未实现 | 缺工具 |
| 保护层接入 | ✓ | 4 个模块全离线 | 全缺 |

**结论：当前 Step 3+ 真规则启用的所有最小前提全部不满足。** 设计文档 §9 阶段 1（数据收集）必须先完成。

## 7. 没有改的东西

严格未触碰（Step 2G 全程，零代码改动）：

- ❌ `predict.py` 任何决策逻辑
- ❌ `run_predict` 主入口
- ❌ 4 个 builder（`build_primary_projection` / `apply_peer_adjustment` / `build_final_projection` / `_apply_research_adjustment`）
- ❌ `services/projection_output_adapter.py`（adapter）
- ❌ `services/projection_output_contract.py`（validator）
- ❌ `services/prediction_store.py`（save 旁路 + DB schema）
- ❌ **6 个现有 read-only 工具：** `contract_payload_inspector` / `contract_payload_trend` / `contract_payload_diff` / `contract_outcome_correlation` / `contract_payload_extras_dashboard` / `contract_calibration_inputs` 一行未改
- ❌ DB schema（不调用 `init_db`，不 `ALTER`）
- ❌ `risk_model.py` / `contradiction_engine.py` / `confidence_engine.py` 三个 v1 stub（整仓库零 import 状态保持）
- ❌ `big_up_contradiction_card` / `exclusion_reliability_review` / `big_down_tail_warning` / `anti_false_exclusion_audit` 四个 UI / 离线模块
- ❌ UI（`ui/predict_tab.py` 等）
- ❌ scanner / matcher / 数据层
- ❌ **longbridge / broker / paper_trade / 真实交易 / 模拟盘 API**
- ❌ 长桥 / 新闻 / 财报数据接入
- ❌ stash / `.claude/worktrees/` / `logs/prediction_log.jsonl`

## 8. 下一步建议

> 按 Step 2F checkpoint §7 / Step 2G-2 设计文档 §11 的优先级。

| 候选 | 范围 | 优先级 |
|---|---|---|
| **Step 2F-4** —— 真实历史回放 / outcome pair 数据生成方案设计 | 设计文档（仿 Step 2G-2 模式），定义如何积累 ≥90 个真实 (contract × outcome) pair。**纯方案，不实施** | **高**（设计文档 §9 阶段 1 的入口；Step 3+ 必须依赖此） |
| **DB hygiene** | 清理主项目 DB 里两条 `prediction_for_date=2099-xx-xx` 的合成 validation 记录（`0e7e37a6-...` / `2fe9eef2-...`）+ 备份文件 `avgo_agent.db.backup_step_2c_2_6` | 中（避免合成数据长期混在真实数据里污染未来诊断输出；需明确确认） |
| **Step 3+ 真规则启用** | 实现 soft 试运行（设计文档 §9 阶段 4） | **低**（必须等 §6 全部最小前提满足；当前一项都不满足） |
| **真模拟交易** | **必须另开阶段，不和 Step 2 / Step 3 exclusion / calibration 混合** | 极低（与 Step 2D-2 严守边界一致：07 段策略边界永久 pinned） |

### 8.1 强烈建议优先级

**Step 2F-4 数据方案设计** 是当前最有价值的下一步：

- 它是 Step 2G-2 阶段 1 的入口（**90 真实 pair 怎么来？**）
- 它是 Step 2F checkpoint §7.1 的"Step 2F-4"候选
- 与本设计文档 §11 一致
- 纯设计文档，零代码改动，零回归风险
- 完成后 Step 2 系列的"设计 + 工具基础设施 + 数据缺口诊断 + 数据补全方案"四个维度全部就位
- 之后任何"开始 Step 3"的决定都有完整 spec 可依，不需要现场重新设计

**Step 2F-4 不写时**，"补真实数据"会变成不明确的状态——可能有人手工写代码采数据 / 可能跑个 ad-hoc 脚本——容易绕过本文档 §6.1 的"禁止合成 outcome"红线。设计文档先冻结**怎么采、采多少、怎么验证**，是避免数据污染的最关键环节。

## 9. Step 2 系列总览（截至本 checkpoint，最终版）

| 阶段 | 范围 | 进 main commit |
|---|---|---|
| **Step 2A** | run_predict 两步结构核验（只读诊断） | —（无代码） |
| **Step 2B-1** | contract alignment 安全网 + data_window drift 暴露 | `2ac41dd` |
| **Step 2B-2** | primary_projection 自发布 02 段 + data_window_days 联动 | `0fccc72` |
| **Step 2B-3** | peer_adjustment 自发布 03 段 | `9aca3f2` |
| **Step 2B-4** | final_projection 自发布 06 段 | `c2d1d34` |
| **Step 2B Summary** | 字段化 checkpoint | `9ae30de` |
| **Step 2C-1** | exclusion_system 只读诊断 | —（无代码） |
| **Step 2C-2** | exclusion_system.extras 暴露 raw risk signals | `8f689a2` |
| **Step 2C-2.5 / 2C-2.6** | DB contract_payload_json 落库验证 | —（无代码） |
| **Step 2C-3a** | confidence_system 只读诊断 | —（无代码） |
| **Step 2C-3b** | confidence_system.extras 暴露 raw score-like signals | `c188725` |
| **Step 2C Summary** | exclusion / confidence extras checkpoint | `1f9f8fa` |
| **Step 2D-1** | simulated_trade 只读诊断 | —（无代码） |
| **Step 2D-2** | simulated_trade.extras 暴露 trade-relevant signals | `f125d45` |
| **Step 2D Summary** | simulated_trade extras checkpoint | `4468f73` |
| **Step 2E-1** | dashboard 只读诊断 | —（无代码） |
| **Step 2E-2** | Contract Extras Dashboard 三件套 | `524552b` |
| **Step 2E-3 / 2E-4** | 主项目 DB 实跑 + 写新 prediction 验证 04/05/07 落库 | —（无代码） |
| **Step 2E Summary** | dashboard checkpoint | `ddb10e1` |
| **Step 2F-1** | confidence calibration 只读诊断 | —（无代码） |
| **Step 2F-2** | calibration_inputs 三件套（service / CLI / tests） | `7500b5b` |
| **Step 2F-3** | 主项目 DB 实跑验证 calibration_ready=false | —（无代码） |
| **Step 2F Summary** | calibration_inputs checkpoint | `5ab64bf` |
| **Step 2G-1** | exclusion soft/hard 规则只读诊断 | —（无代码） |
| **Step 2G-2** | exclusion soft/hard 规则设计文档冻结 | `9d55a80` |
| **Step 2G Summary** | 本文件 | (pending commit) |

**测试基线累积：** Step 2 起点 1883 → 2094（**+211**）；0 failed；10 skipped 全程不变。

**核心不变量（Step 2 全程）：**
- ❌ `predict.py` / `run_predict` / 4 个 builder / contract validator / UI / `prediction_store` / DB schema 一行未改 / 一行未引入
- ❌ 6 个现有 read-only 工具的字段集（`DIFF_PATHS` / `GROUP_PATHS` / `DISTRIBUTION_PATHS` / `_MIN_RECOMMENDED_PAIRS`）一行未改
- ❌ 三个 v1 stub trio（`risk_model.py` / `contradiction_engine.py` / `confidence_engine.py`）整仓库零 import
- ❌ 四个离线 / UI 模块（`big_up_contradiction_card` / `exclusion_reliability_review` / `big_down_tail_warning` / `anti_false_exclusion_audit`）未接主链
- ❌ 任何 trading API（longbridge / broker / paper_trade）未引入
- ❌ **04 段 5 个 required 字段全程 stub；05 段 4 个 score 字段全程 0.0；05 段 event_score 全程 None；07 段 6 个决策字段全程策略边界 pinned；08 段 prediction_id 全程空字符串**

**Step 2 全程的核心交付：**
- 02 / 03 / 06 三段由 builder 自发布
- 04 / 05 / 07 三段以 `extras` 暴露 raw signals（required 字段不动）
- 6 个 read-only 工具组成完整可观察基础设施
- 2 份诊断报告（Step 2F calibration_inputs / Step 2G exclusion soft/hard）+ 1 份规则设计文档（Step 2G-2）

至此，Step 2 系列完整收口；Step 3+ 真规则启用前的所有 spec、工具、诊断、数据缺口报告都已就位。下一步 Step 2F-4（数据方案）+ DB hygiene + Step 3+（真规则启用）都可以直接引用 Step 2 阶段的产出。
