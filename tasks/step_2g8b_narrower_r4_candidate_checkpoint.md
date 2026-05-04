# Step 2G-8B — Narrower R4 Candidate Research Checkpoint

> **状态固化文档（narrower R4 candidate research checkpoint），不实现，不改代码。**
> 本文档**冻结** Step 2G-8B research（commit `c9b4725`）的 NO-GO 结论：
> 在当前 286 paired / 34 R4-paired baseline 下，**没有任何 narrower
> R4 子切片**同时满足 `paired ≥ 30 ∧ fer ≤ 0.10 ∧ nb ≥ +0.05`，
> R4 hard candidate implementation 在数据层已不可行。
>
> 本轮**不动任何代码**：不改 `predict.py` / `run_predict` /
> `scanner.py` / `prediction_store.py` / `app.py` / 任何 `ui/*` /
> `services/*` / 任何 builder / DB schema / 任何 test 中的任何一处。

---

## 1. 当前完成状态

- **Step 2G-8** launch condition review 已完成（结论：NO-GO，hard gate
  4/6 fail）
- **Step 2G-8A** protection diagnostics 三层 sidecar（design / 8A.1
  helper / 8A.2 UI / 8A.3 dashboard aggregate）+ 全部 checkpoint 已
  完成并进入 main
- **Step 2G-8B** narrower R4 candidate research 已完成并进入 main
  （commit `c9b4725`）
- 本 checkpoint **固定**：
  - R4 baseline 数字（与 Step 2G-7C / 8 / 8A.x 完全一致）
  - 42 个候选切片的扫描结果
  - 三项 hard candidate 门槛全部不达
  - **R4 narrower candidate = NO-GO**（结构性，非阈值问题）
  - 跨窗口不稳定证据 → Step 2G-8C 应继续
- Step 2G-8B 是 **read-only 研究**；本 checkpoint **只是**状态归档；
  不实现、不改代码、不写 DB、不重跑研究

---

## 2. 当前 main 状态

- main 最新 commit：**`c9b4725`**
- commit message：`docs(contract): Step 2G-8B narrower R4 candidate research`
- 上游：`origin/main` 已同步
- 测试基线：**2604 passed / 0 failed / 10 skipped**（与 Step 2G-8A.3
  终点一致；本步骤无代码改动，无回归）

本步骤新增文件（已 merge 到 main）：

| 路径 | 类型 | 说明 |
|---|---|---|
| `tasks/step_2g8b_narrower_r4_candidate_research.md` | 新增 | 9 节、332 行；研究方法 + 42 候选表 + NO-GO 结论 |

本 checkpoint 文档（即本文件）尚未 commit；本轮只写文档、不 commit /
push。

---

## 3. R4 baseline 复现

通过 `summarize_anti_false_exclusion_dashboard()` 跑 parent main DB
（`/Users/may/Desktop/stock-analyzer-main/avgo_agent.db`，380 条
`replay_AVGO_*` 行 + `coded_data/AVGO_coded.csv` /
`coded_data/SOXX_coded.csv`），得到：

| 字段 | 值 | 与 Step 2G-7C / 8 / 8A.x 一致？ |
|---|---|---|
| `paired_outcomes` | **286** | ✅ |
| R4 `samples` | 36 | ✅ |
| R4 `paired` | **34** | ✅ |
| R4 `correct_when_triggered` | **11** | ✅ |
| R4 `wrong_when_triggered` | **23** | ✅ |
| R4 `accuracy` / `false_exclusion_rate` | **0.3235** | ✅ |
| R4 `net_benefit` | **+0.0219** | ✅ |
| R4 `bias_gap` | 0.6765 | ✅ |
| R4 `holdout_status` | **FAIL** | ✅ |
| `hard_gate_status` | **2 pass / 4 fail** | ✅ |
| `hard_exclusion_allowed` | **False** | ✅ |
| `protection_layer_diagnostics.guard_summary.total_guard_count` | 2 | ✅ |
| `protection_layer_diagnostics.guard_summary.blocking_reasons` | `{holdout_status_FAIL: 1, net_benefit_below_gate: 1}` | ✅ |

baseline 数字稳定，Step 2G-8B 分析底数无误。

---

## 4. 研究方法

### 4.1 数据范围

- 仅使用 `prediction_log.snapshot_id LIKE 'replay_AVGO_%'` 的 380 行
- 仅保留 `outcome_log.direction_correct ∈ {0, 1}` 的 286 paired 记录
- 触发判断与 `regime_diagnostics_dashboard._is_r4_record` 完全一致：
  `avgo_minus_soxx_20d > 5.0 ∧ pos20 > 0.62 ∧ final_direction == "偏多"
  ∧ (confidence_level == "high" ∨ primary_score_raw > 2)`
- R4 paired 池 = 34 records
- **不**触碰 2026-01-01 之后 final test range（DB 中也不存在该区间数据）

### 4.2 公式

| 字段 | 公式 |
|---|---|
| `paired` | 切片内 `direction_correct ∈ {0, 1}` 的记录数 |
| `correct` | 切片内 `direction_correct = 1` 的记录数 |
| `wrong` | `paired − correct` |
| `fer`（false_exclusion_rate）| `correct / paired`（R4 fully-bullish；"误杀"= 排除一个原本预测正确的多头判断） |
| `nb`（net_benefit）| `(base_correct − slice_correct) / (base_paired − slice_paired) − base_correct / base_paired`（counterfactual：剔除该切片后 base_acc 的提升） |

baseline = 286 paired × `confidence_level ∈ {high, medium, low}`
（与 `soft_metadata_simulator._net_benefit_from_dashboard` 完全一致）：
- `base_paired = 286`
- `base_correct = 139`
- `base_acc = 0.4860`

### 4.3 候选维度（10+，共 42 切片）

| # | 维度 |
|---|---|
| 1 | `pos20` 阈值（`≥ 0.70 / ≥ 0.75 / ≥ 0.80 / ≥ 0.85 / ≥ 0.90 / ≤ 0.70 / ≤ 0.75 / ≤ 0.80 / ≤ 0.85 / ≤ 0.90`） |
| 2 | `avgo_minus_soxx_20d` 阈值（`≥ 6 / ≥ 7 / ≥ 8 / ≥ 10 / ≥ 12`） |
| 3 | `confidence_level`（`high` / `medium`） |
| 4 | `primary_score_raw` 阈值（`≥ 2.0 / ≥ 2.5 / ≥ 3.0 / ≥ 3.5`） |
| 5 | `peer_adjustment`（`upgrade` / `hold` / `downgrade`） |
| 6 | `peer_confirm_count`（`0 / 1 / 2 / 3 / ≥ 2 / ≤ 1`） |
| 7 | `soft_signal`（`none` / `peer_weaken`；含 path_risk 维度，但 R4 池无 high_path_risk 样本） |
| 8 | quarter / month window（2023-Q1 〜 2024-Q3） |
| 9 | holdout split（first_half vs second_half by `analysis_date`） |
| 10 | confidence × peer 交叉、pos20 × diff 交叉、pos20 × peer 交叉 等 |

**全部研究步骤都是 read-only**：
- 只跑 `SELECT` SQL（通过 `_fetch_replay_rows`）
- 只读 `coded_data/{AVGO,SOXX}_coded.csv`
- inline Python 切片 + 计数
- **不**改代码、**不**写 DB、**不**接网络 / yfinance / trading

---

## 5. 最好的 3 个 candidate

按"接近三项门槛"综合排序：

| rank | candidate | paired | FER | NB | paired ≥ 30 | FER ≤ 0.10 | NB ≥ 0.05 | 结论 |
|---|---|---:|---:|---:|:-:|:-:|:-:|---|
| 1 | **R4 ∧ confidence=high** | **32** | 0.3125 | +0.0219 | ✓ | ✗ | ✗ | **fail** |
| 2 | R4 ∧ peer=upgrade | 24 | 0.2500 | +0.0216 | ✗ | ✗ | ✗ | **fail** |
| 3 | R4 ∧ avgo-soxx≥10 | 11 | 0.1818 | +0.0122 | ✗ | ✗ | ✗ | **fail** |

解释：
- **第 1 个**（`R4 ∧ confidence=high`，n=32）paired 勉强过，但 FER
  仍 0.3125 —— 远高于 0.10，与 R4_full 几乎重合（仅去掉 2 个 medium
  样本），未提供任何额外 narrower 力量
- **第 2 个**（`R4 ∧ peer=upgrade`，n=24）FER 略降到 0.25，但 paired
  差 6；NB 仍 +0.022
- **第 3 个**（`R4 ∧ avgo-soxx≥10`，n=11）FER 进一步降到 0.18，但
  paired 差 19，远远不到 30 阈值
- **NB 全部不达 +0.05**（counterfactual nb 上界由 R4_full 决定）

---

## 6. 三项 hard candidate 门槛

候选必须同时满足：

| # | 门槛 | 来源 | hard gate 对应 |
|---|---|---|---|
| 1 | `paired ≥ 30` | 统计学有效性 + Step 2G-3 | `candidate_paired_ge_30` |
| 2 | `fer ≤ 0.10` | Step 2G-3 / 2G-4.5 / 2G-7 / 2G-7A | `false_exclusion_rate_lte_0_10` |
| 3 | `nb ≥ +0.05` | Step 2G-3 / 2G-4.5 / 2G-7 / 2G-7A | `net_benefit_gte_0_05` |

**结论**：
- 42 个候选切片中 **0 个**同时满足三项
- 所以 **R4 narrower candidate hard implementation = NO-GO**

---

## 7. 为什么这是结构性 NO-GO

不是阈值或参数调整能解决的问题：

| 原因 | 证据 |
|---|---|
| R4 full FER 已经 **0.3235**，距离 0.10 太远 | acc 0.3235 vs gate 0.10 → 缺口 0.22；不是细微缩窄能解决 |
| 只有很窄切片能降低 FER，但样本量会掉到 ≤ 11 | 所有 fer ≤ 0.20 的候选切片 paired ≤ 11；统计学不可信 |
| paired ≥ 30 的切片 FER 仍约 0.3125 | 唯一两个非平凡 n ≥ 30 子切片（`confidence=high` / `soft_signal=none`，n=32）几乎与 R4_full 等价 |
| NB 被 R4 全体覆盖力限制，上界约 **+0.0219** | counterfactual 公式：剔除 R4 让 base_acc 从 0.4860 提到 0.5079（+0.0219）。任何 narrower 子集杠杆更弱 → nb 上界 < +0.0219 |
| residual NB 为负 | `bullish_high_pos20_residual` nb = **−0.0007** —— 扩大范围更差，方向不对 |
| 所以不是简单阈值调整问题 | 数据本身没有可挖掘的信号；只能通过**扩大数据**或**换候选**绕开 |

---

## 8. holdout / window 问题

| 切片 | n | FER |
|---|---:|---:|
| `R4 ∧ first_half (chronological)` | 17 | **0.2353** |
| `R4 ∧ second_half (chronological)` | 17 | **0.4118** |

跨窗口 FER 差距 **0.18**，且 `R4 ∧ holdout_status` 整体 FAIL —— 说明：
- R4 行为有 **regime / window dependency**
- 第二窗口本身就 fer ≫ 0.10，无法用单一 narrower 条件克服
- 这正是 `cross_window_holdout_pass` 仍 fail 的根本原因

→ 下一步应做 **Step 2G-8C holdout gap analysis** 解释这个 0.18 缺口。

---

## 9. 对 hard gate 的影响

| Gate | 当前 | Step 2G-8B 实施任意 narrower R4 后 |
|---|---|---|
| `total_paired_ge_90` | PASS（286） | 不变 |
| `candidate_paired_ge_30` | PASS（34） | **多数候选会 fail**（narrower paired < 30） |
| `false_exclusion_rate_lte_0_10` | FAIL（0.3235） | 仍 fail（最佳 fer = 0.3125 @ paired ≥ 30） |
| `net_benefit_gte_0_05` | FAIL（+0.0219） | 仍 fail（全部 nb < +0.05） |
| `protection_layer_connected` | FAIL | 仍 fail（v1 hard-coded） |
| `cross_window_holdout_pass` | FAIL | 仍 fail（first_half vs second_half 跨窗口波动） |

**结论**：
- hard gate 仍 **2 pass / 4 fail**
- `hard_exclusion_allowed` = **False**
- 04 / 05 / 07 required 仍禁止升级
- 实施任何 narrower R4 都**不会**让 hard gate 改善，最多让
  candidate_paired 从 pass 变 fail

---

## 10. GO / NO-GO

| 候选 | 状态 | 理由 |
|---|---|---|
| **Step 2G-8B.1** R4 hard candidate implementation | **NO-GO** | 数据层 0 candidate 满足三项门槛；结构性 |
| **Step 2G-8C** holdout gap analysis | **GO** | 解释跨窗口 0.18 FER 缺口；只读，与 Step 3 calibration 重启耦合但研究层先做不影响 hard |
| **Step 2G-8D** extend replay coverage（2024-08 → 2025-12） | **conditional GO** | 数据层；扩大 paired 池让 narrower 切片 paired 有望涨到 ~70+，改变 nb 上界 |
| **Step 2G-8E** other R candidates research（R1/R2/R3/R5） | **conditional GO** | 探索性；R4 不是唯一候选 |
| hard / forced / required upgrade | **NO-GO** | Step 2G-8 launch review 已 NO-GO；本步骤进一步加强证据 |

---

## 11. 下一步建议

按推荐优先级：

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **Step 2G-8B checkpoint**（本文档） | 把 NO-GO 结论 + 候选表 + 跨窗口证据归档进 main，让未来读者一眼看到"narrower R4 已尝试，不可行" | **本轮** |
| 2 | **Step 2G-8C** holdout gap analysis | 解释 first_half (FER=0.24) vs second_half (FER=0.41) 0.18 缺口；为 Gate 6 找诊断；只读 | **高**（顺接本研究的关键开放问题） |
| 3 | **Step 2G-8D** extend replay coverage | 把 replay 跑到 2024-08 → 2025-12（不触碰 2026-01-01 之后 final test）；R4 paired 有望从 34 涨到 ~70+；narrower 切片 paired 也会变得可信；解 nb 上界瓶颈 | **高**（数据层） |
| 4 | **Step 2G-8E** 替换候选 R-series | 离开 R4，研究 R1 / R2 / R3 / R5 是否有 acc 显著低于 baseline 0.486 的切片；R4 不是唯一候选 | 中（探索性） |
| 5 | **不推荐** Step 2G-8B.1 实施 | 把某 narrower R4 接入 hard pipeline | **❌** 数据层 NO-GO |
| 6 | **不推荐** 让 `_PROTECTION_LAYER_CONNECTED` 翻 True | 让 Gate 5 自动 pass | **❌** 与 8A 设计 / 8 launch review 冲突 |
| 7 | **不推荐** 升级 04 required `anti_false_exclusion_triggered` | 把 R4 标记进 04 主链 | **❌** 与 8A 系列 sidecar-only 边界冲突 |

**强制约束**（继承 Step 2G-8A 设计 §13 / 8A.x checkpoint）：
- 不改 04 / 05 / 07 required 字段
- 不改 `run_predict` 主链
- 不写 DB
- 不出现 19 forbidden words / 16 forbidden words / 8 forbidden words
- `hard_exclusion_allowed` 永远 `False`
- `protection_layer_connected_for_gate` 永远 `False`（v1）

---

## 12. 严守边界

本文是**纯 checkpoint 文档**：

- ❌ 没改任何代码（`services/*` / `ui/*` / `tests/*` 全部未触碰）
- ❌ 没改 DB schema
- ❌ 没写 DB
- ❌ 没改 `run_predict` / `predict.py` / `scanner.py` /
  `prediction_store.py` / `app.py`
- ❌ 没改 `services/regime_diagnostics_dashboard.py` /
  `services/anti_false_exclusion_dashboard.py` /
  `services/soft_metadata_simulator.py` /
  `services/protection_layer_diagnostics.py` /
  `ui/protection_layer_diagnostics_renderer.py` / 任何 ui 模块 /
  任何 builder
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
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` /
  `avgo_agent.db.backup_*`
- ❌ 没运行 `pytest`（本轮纯文档；测试结果引用 commit `c9b4725` 的
  实测数据：2604 / 0 failed / 10 skipped）
- ✅ 只新增 1 份 markdown checkpoint 文档（本文件）
