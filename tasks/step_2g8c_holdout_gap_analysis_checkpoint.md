# Step 2G-8C — Holdout Gap Analysis Checkpoint

> **状态固化文档（holdout gap analysis checkpoint），不实现，不改代码。**
> 本文档**冻结** Step 2G-8C analysis（commit `395ca77`）的归因结论：
> R4 first_half FER ≈ 0.24 vs second_half FER ≈ 0.41（gap ≈ +0.18）
> 主要由 **regime shift（H2 sustained AI bull rally）+ R4 regime-
> agnostic + 2024-02 单月异常** 三层叠加驱动；**Gate 6
> `cross_window_holdout_pass` 在 Step 2G 范围内不可解**；R4 hard path
> 继续 **NO-GO**。
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
- **Step 2G-8B** narrower R4 candidate research + checkpoint 已完成
  并进入 main（commits `c9b4725` / `e2f68c6`，结论：R4 narrower
  candidate NO-GO）
- **Step 2G-8C** holdout gap analysis 已完成并进入 main（commit
  `395ca77`）
- 本 checkpoint **固定**：
  - R4 holdout gap baseline 数字（与 Step 2G-8B 一致）
  - first_half vs second_half 结构差异
  - top 3 suspected gap drivers
  - 10 个反事实切片（counterfactual）结论
  - **Gate 6 仍 FAIL** + Step 2G 范围内**不可解** 的判定
  - R4 hard path 继续 **NO-GO**
- Step 2G-8C 是 **read-only 研究**；本 checkpoint **只是**状态归档；
  不实现、不改代码、不写 DB、不重跑研究

---

## 2. 当前 main 状态

- main 最新 commit：**`395ca77`**
- commit message：`docs(contract): Step 2G-8C holdout gap analysis`
- 上游：`origin/main` 已同步
- 测试基线：**2604 passed / 0 failed / 10 skipped**（与 Step 2G-8A.3
  / 2G-8B 终点一致；本步骤无代码改动，无回归）

本步骤新增文件（已 merge 到 main）：

| 路径 | 类型 | 说明 |
|---|---|---|
| `tasks/step_2g8c_holdout_gap_analysis.md` | 新增 | 11 节、391 行；归因方法 + 反事实切片 + Gate 6 NO-GO 判定 |

本 checkpoint 文档（即本文件）尚未 commit；本轮只写文档、不 commit /
push。

---

## 3. R4 holdout gap baseline

| 字段 | 值 |
|---|---|
| R4 paired | **34** |
| first_half paired | **17** |
| first_half date range | 2023-01-06 → 2023-11-07 |
| first_half correct / wrong | 4 / 13 |
| first_half FER | **0.2353** |
| second_half paired | **17** |
| second_half date range | 2023-12-15 → 2024-07-08 |
| second_half correct / wrong | 7 / 10 |
| second_half FER | **0.4118** |
| **gap (H2 − H1)** | **+0.1765** |
| Gate 6 `cross_window_holdout_pass` | **FAIL** |
| dashboard `holdout_status` | **FAIL** |

**FER 口径**：R4 是 fully-bullish exclusion candidate，
`false_exclusion_rate = correct / paired` —— 误杀率指"如果 hard 排除
R4，会错杀掉这些原本预测正确的多头判断"。与 Step 2G-7C / 2G-8 /
2G-8B / 2G-8C analysis 完全一致。

---

## 4. 核心根因

gap 不是单一原因，而是**三层叠加**：

| # | 根因 | 含义 |
|---|---|---|
| 1 | **regime shift**（首因） | H1（2023-01 → 2023-11）= 震荡市 + 周期反转；H2（2023-12 → 2024-07）= sustained AI bull rally。同一 R4 触发条件在两个 regime 下命中率系统性不同 |
| 2 | **H2 sustained AI bull rally** | 2023 年底起 NVDA / AVGO 引领 AI 主升浪；AVGO 屡创 ATH；R4 mean-reversion 假设频繁失败 |
| 3 | **R4 regime-agnostic** | R4 触发条件（`avgo_minus_soxx_20d > 5 ∧ pos20 > 0.62 ∧ bullish ∧ high-conf`）**不**含任何 regime detector；R4 在 sustained bull regime 下系统性误判 |
| 4 | **2024-02 单月异常** | NVDA earnings + AVGO ATH 突破月；4 records / fer 0.75 / 单月贡献 ≈ 0.06 absolute FER |

**强调**：
- 这**不**是简单的阈值调整问题（提高 pos20 阈值或 diff 阈值都不能
  收敛 H1 / H2 同时让 FER ≤ 0.10）
- 这**不**是单纯的样本量问题（即使每 half 翻倍到 ~70+ paired，下面
  的 regime sensitivity 仍存在）
- 这是 **R4 在不同 market regime 下行为不稳定**的结构性问题

---

## 5. first_half vs second_half 差异（结构对比）

### 5.1 基础对比

| 字段 | H1 | H2 | 差异 |
|---|---|---|---|
| paired | 17 | 17 | 持平 |
| correct | 4 | 7 | **+3**（误杀近翻倍） |
| wrong | 13 | 10 | −3 |
| FER | 0.2353 | 0.4118 | **+0.1765** |
| NB | +0.0158 | +0.0047 | −0.0111 |
| date range | 2023-01-06 → 2023-11-07 | 2023-12-15 → 2024-07-08 | 自然时间分隔 |

### 5.2 月份集中度

| half | 月份分布 | 异常月份 |
|---|---|---|
| H1 | 2023-01/03/05/06/07/10/11 | 2023-07（fer=1.00, n=2）/ 2023-11（fer=1.00, n=1） |
| H2 | 2023-12/2024-01/02/04/06/07 | **2024-02**（fer=**0.75**, n=4）|

H2 大半月份 FER ≥ 0.25；H1 大半月份 FER = 0.00。

### 5.3 维度差异摘要

| 维度 | H1 | H2 | 差异程度 |
|---|---|---|---|
| **pos20 ≥ 0.90 cluster** | **2** | **7**（3.5×） | **显著** |
| pos20 mean | 0.7963 | 0.8295 | 偏移 |
| pos20 median | 0.8361 | 0.8761 | 偏移 |
| diff median (avgo − soxx) | 7.62 | 7.72 | 几乎相同 |
| diff stdev | 3.81 | 5.07 | H2 方差更大 |
| confidence_level | 17 high / 0 medium | 15 high / 2 medium | 微小 |
| peer_adjustment | 12 up / 5 hold / 0 down | 12 up / 3 hold / 2 down | 微小 |
| peer_confirm_count | 偏 3-confirm（8） | 偏 2-confirm（7） | 中度 |
| primary_score_raw mean | 2.76 | 2.69 | 几乎相同 |
| soft_signal | 17 none | 15 none / 2 peer_weaken | 微小 |

**核心观察**：除 pos20 高位 cluster 外，其它维度 H1 与 H2 几乎一致；
gap 不是"H2 候选质量更差"，而是"同样质量的候选在 H2 regime 下命中
率系统性更高"。

### 5.4 2024-02 影响

| 视角 | 数值 |
|---|---|
| 2024-02 paired | 4 |
| 2024-02 correct | 3 |
| 2024-02 FER | **0.75** |
| 单月对 H2 FER 的贡献 | ≈ +0.06 absolute |
| 去掉 2024-02 后 gap | **+0.0724**（从 +0.1765 缩到 +0.0724） |

→ 单月异常贡献 ~60% 的 gap，但**去掉后仍有 +0.07** —— 不是单月
能掩盖的结构性问题。

---

## 6. Suspected gap drivers（top 3）

按贡献从大到小：

| # | driver | 证据 |
|---|---|---|
| 1 | **H2 bull regime 把"原本应被视为 over-bullish"的 R4 触发救活** | H2 pos20 ≥ 0.90 cluster 7 records 中 3/7 = 0.43 是 correct（误杀）；H1 同桶 2 records 全 wrong（R4 正确触发）。R4 mean-reversion 假设在 sustained bull regime 下系统性失效 |
| 2 | **2024-02 单月集中贡献 survival cases** | 4 records / 3 correct / fer 0.75；NVDA earnings + AVGO ATH 突破月；单独贡献 ≈ 60% 的 H2-vs-H1 gap |
| 3 | **R4 没有 regime-aware 过滤，导致同一信号在不同窗口含义不同** | R4 触发条件 `regime_diagnostics_dashboard._is_r4_record` 中没有任何 market regime 标签；2023 震荡市与 2024 多头主升浪用同一阈值，命中率天然偏差 |

---

## 7. 反事实切片结论

10 个反事实切片（来自 Step 2G-8C analysis §7）：

| 切片 | 含义 | gap |
|---|---|---:|
| confidence=high | 控制 confidence | +0.165（**不变**） |
| peer=upgrade | 控制 peer | +0.167（**不变**） |
| peer ≠ downgrade | 控制 peer | +0.165 |
| soft_signal=none | 控制 soft | +0.165 |
| **pos20 ∈ [0.70, 0.90]**（中段）| 限制 pos20 中段 | **+0.013**（gap 几乎消失） |
| H2 minus 2024-02 | 去掉单月异常 | +0.072（缩半） |
| H1 cherry-pick | 去 H1 outlier 月份 | +0.236（**反而扩大**） |
| pos20 ≤ 0.85 | H1-style 分布 | +0.208（gap 反而更大） |
| **pos20 ≥ 0.90**（高位 cluster）| 限制 pos20 高位 | **+0.429**（gap **暴增**） |
| peer_confirm ≥ 2 | 控制 confirm | +0.167（**不变**） |

**关键发现**：
- 单维度（confidence / peer / soft / confirm）控制后 gap 维持 ~0.165
  → **没有 stable narrower slice 能在两个 half 同时收敛 FER**
- pos20 中段切片 gap 几乎消失（+0.013）→ pos20 是主要 gap 载体
- pos20 高位切片 gap 暴增（+0.43）→ H2 高位 cluster 的"误杀"行为
  与 H1 完全相反
- 去掉异常月份后样本量进一步不足，无法跨过 paired ≥ 30 门槛
- **没有任何切片能让 H1 + H2 同时 FER ≤ 0.10 且 paired ≥ 30**

→ Step 2G 范围内**没有 stable narrower slice 能让 Gate 6 pass**。

---

## 8. 对 hard gate 的影响

| Gate | 当前状态（未变） |
|---|---|
| `total_paired_ge_90` | PASS（286） |
| `candidate_paired_ge_30` | PASS（R4 paired = 34） |
| `false_exclusion_rate_lte_0_10` | **FAIL**（R4 fer = 0.3235；narrower slices 均 fail） |
| `net_benefit_gte_0_05` | **FAIL**（R4 nb = +0.0219；narrower slices 均 fail） |
| `protection_layer_connected` | **FAIL**（v1 hard-coded） |
| `cross_window_holdout_pass` | **FAIL**（H1 vs H2 跨窗口 +0.18 gap；regime-shift 主因） |

**结论**：
- hard gate 仍 **2 pass / 4 fail**
- `hard_exclusion_allowed` = **False**
- 04 / 05 / 07 required 仍禁止升级
- Step 2G-8C analysis **不**改变 gate 状态；它只是给 Gate 6 fail 提供
  归因证据

---

## 9. 是否能在 2G 内解决

**不能。** 理由：

| 路径 | Step 2G 内可行？ | 解释 |
|---|---|---|
| 修 R4 触发条件加 regime filter | **❌ 否** | 违反 Step 2G "不改 `_build_exclusion_system` / `regime_diagnostics_dashboard._is_r4_record`" 边界 |
| narrower R4 hard 实施 | **❌ 否** | Step 2G-8B 已 NO-GO；Step 2G-8C 进一步证实 narrower 切片在跨窗口仍不稳定 |
| 等更多数据 | **❌ 否** | Step 2G-8D 范围；不在 2G 主线 |
| 让 `_PROTECTION_LAYER_CONNECTED` 翻 True | **❌ 否** | 与 Step 2G-8A 系列 sidecar-only 边界 / Step 2G-8 launch review NO-GO 冲突 |
| 升级 04 required | **❌ 否** | 与 Step 2G 全程"不升级 required"边界冲突 |

**Step 2G 是什么**：
- soft metadata / display / diagnostics / sidecar
- read-only aggregate dashboard
- UI 子节渲染
- 不进入 hard decision pipeline
- 不写 DB / 不升级 required

**R4 跨窗口问题需要的**：
- regime-aware calibration / exclusion framework
- 不同 regime 下不同的 fer / nb 门槛
- 或 R4 触发条件含 regime guard（"sustained bull regime 时静默"）
- 或换候选（R1 / R2 / R3 / R5）

→ 这些都**超出 Step 2G 范围**，必须等 **Step 3 calibration 重启**
（regime-aware exclusion）或 **Step 2G-8D extend replay coverage**
（数据层）+ **Step 2G-8E other R candidates**（候选层）。

---

## 10. GO / NO-GO 结论

| 问题 | 结论 | 理由 |
|---|---|---|
| Step 2G-8C resolves Gate 6？ | **NO** | analysis 仅诊断，不改代码 |
| R4 hard path？ | **NO-GO**（继承 8B + 加强证据） | 跨窗口 +0.18 gap + regime-shift 主因 |
| **Step 3 calibration restart**？ | **GO（最高优先级）** | 唯一引入 regime-aware exclusion 框架的路径 |
| Step 2G-8D extend replay coverage？ | **conditional GO** | 数据层；必要但不充分；解样本量不解 regime sensitivity |
| Step 2G-8E other R candidates research？ | **conditional GO** | 探索性；前提是 Step 3 / 8D 至少完成一个 |
| hard / forced / required upgrade？ | **NO-GO** | 与 Step 2G-8 launch review / 8A 系列 / 8B / 8C 一致 |

---

## 11. 下一步建议

按推荐优先级：

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **Step 2G-8C checkpoint**（本文档） | 把 NO-GO + regime-shift 证据归档进 main | **本轮** |
| 2 | **Step 3 calibration restart** | 引入 regime detector + 不同 regime 下不同 exclusion 阈值；让 R4 在 sustained bull regime 下静默 | **最高**（解 Gate 6 根因） |
| 3 | **Step 2G-8D** extend replay coverage（2024-08 → 2025-12） | 不触碰 2026-01-01 之后 final test；让每 half 涨到 ~70+ paired；让 holdout split 平均化；解样本量瓶颈 | 高（数据层；与 #2 互补） |
| 4 | **Step 2G-8E** 替换候选 R-series | 离开 R4，研究 R1 / R2 / R3 / R5 是否有 regime-stable 候选 | 中（探索性；前提 #2 / #3 至少一个完成） |
| 5 | **不推荐** 继续 R4 hard path | 跨窗口 regime-shift 已证实结构性 NO-GO | **❌** |
| 6 | **不推荐** 让 `_PROTECTION_LAYER_CONNECTED` 翻 True | 与 8A 设计 / 8 launch review 冲突 | **❌** |
| 7 | **不推荐** 升级 04 required `anti_false_exclusion_triggered` | 与 Step 2G 全程边界冲突 | **❌** |

**强制约束**（继承 Step 2G-8A 设计 §13 / 8A.x checkpoint / 8B
checkpoint / 8C analysis §10）：
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
- ❌ 没运行 `pytest`（本轮纯文档；测试结果引用 commit `395ca77` 的
  实测数据：2604 / 0 failed / 10 skipped）
- ✅ 只新增 1 份 markdown checkpoint 文档（本文件）
