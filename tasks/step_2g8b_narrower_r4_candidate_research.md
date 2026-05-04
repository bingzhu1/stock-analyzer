# Step 2G-8B — Narrower R4 Candidate Research

> **只读分析文档（read-only research）。**
> 本文档基于 `avgo_agent.db` 中 2023-01-04 → 2024-08-05 的 380 条
> replay-tagged predictions（286 paired），在 R4 触发的 34 条 paired
> 子集内做 only-read 切片研究，回答：**是否存在一个更窄的 R4 二级
> 条件，使 false_exclusion_rate ≤ 0.10、net_benefit ≥ +0.05、
> paired ≥ 30 同时满足？**
>
> **结论：NO-GO。**
>
> 本文不改任何代码、不改 DB、不写 DB、不接网络 / trading API、不
> 触碰 04 / 05 / 07 required 字段、不让 hard / forced 升级、不触碰
> 2026-01-01 之后 final test range。

---

## 1. 背景

Step 2G-8A 系列已经完成 protection diagnostics 的 **三层 sidecar**
（helper / UI / dashboard aggregate）。但这些 sidecar 只解决 Gate 5
的 display / diagnostic 维度，并**不**改变 hard gate 的 fail 状态：

| Gate | 当前状态 |
|---|---|
| `total_paired_ge_90` | PASS（286 ≥ 90） |
| `candidate_paired_ge_30` | PASS（R4 paired = 34 ≥ 30） |
| `false_exclusion_rate_lte_0_10` | **FAIL**（R4 fer = 0.3235） |
| `net_benefit_gte_0_05` | **FAIL**（R4 nb = +0.0219） |
| `protection_layer_connected` | FAIL（v1 hard-coded） |
| `cross_window_holdout_pass` | FAIL（holdout = FAIL） |

**Step 2G-8B 的研究问题**：能不能在 R4 内部找到一个二级条件
（`narrower_R4 = R4 ∧ X`），让该子切片同时通过：
- `paired ≥ 30`（统计学有效性）
- `fer ≤ 0.10`（误杀率门槛）
- `nb ≥ +0.05`（净收益门槛）

如果可以，未来 Step 2G-8+ launch review 可以考虑把 narrower R4
（**不是** 完整 R4）接入 hard decision pipeline。

如果不可以，Step 2G-8B 应给出明确 **NO-GO** 并建议下一步研究方向
（如 8C holdout gap analysis、扩大 replay 覆盖、或换 R-series 候选）。

---

## 2. R4 baseline 复现

直接调用 `summarize_anti_false_exclusion_dashboard()` 跑 parent main
DB（`/Users/may/Desktop/stock-analyzer-main/avgo_agent.db`，含 380
条 `replay_AVGO_*` 行 + `coded_data/AVGO_coded.csv` /
`coded_data/SOXX_coded.csv`）：

| 字段 | 实测值 | 与 Step 2G-7C / 8 / 8A.x checkpoint 一致？ |
|---|---|---|
| `paired_outcomes` | 286 | ✅ |
| `metrics_window.analysis_date_min` | 2023-01-03 | ✅ |
| `metrics_window.analysis_date_max` | 2024-08-02 | ✅ |
| `r4_overextension.samples` | 36 | ✅ |
| `r4_overextension.paired` | **34** | ✅ |
| `r4_overextension.correct_when_triggered` | **11** | ✅ |
| `r4_overextension.wrong_when_triggered` | 23 | ✅ |
| `r4_overextension.accuracy` | 0.3235 | ✅ |
| `r4_overextension.false_exclusion_rate` | **0.3235** | ✅ |
| `r4_overextension.net_benefit` | **+0.0219** | ✅ |
| `r4_overextension.bias_gap` | 0.6765 | ✅ |
| `r4_overextension.holdout_status` | FAIL | ✅ |
| `hard_gate_status.total_paired_ge_90` | pass | ✅ |
| `hard_gate_status.candidate_paired_ge_30` | pass | ✅ |
| `hard_gate_status.false_exclusion_rate_lte_0_10` | fail | ✅ |
| `hard_gate_status.net_benefit_gte_0_05` | fail | ✅ |
| `hard_gate_status.protection_layer_connected` | fail | ✅ |
| `hard_gate_status.cross_window_holdout_pass` | fail | ✅ |
| `hard_exclusion_allowed` | False | ✅ |
| `protection_layer_diagnostics.guard_summary.total_guard_count` | 2 | ✅ |
| `protection_layer_diagnostics.guard_summary.blocking_reasons` | `{holdout_status_FAIL: 1, net_benefit_below_gate: 1}` | ✅ |

baseline 与 Step 2G-7C / 2G-8 / 2G-8A.1 / 2G-8A.3 checkpoint 完全
一致；分析底数无误。

---

## 3. 分析方法

### 3.1 数据范围

- 仅使用 `prediction_log.snapshot_id LIKE 'replay_AVGO_%'` 的 380 行
- 仅保留 `outcome_log.direction_correct ∈ {0, 1}` 的 286 paired 记录
- R4 触发判断：`avgo_minus_soxx_20d > 5.0 ∧ pos20 > 0.62 ∧
  final_direction == "偏多" ∧ (confidence_level == "high" ∨
  primary_score_raw > 2)` — 与 `regime_diagnostics_dashboard._is_r4_record`
  完全一致
- 触发后保留 paired = 34 条记录作为研究池
- **不**触碰 2026-01-01 之后 final test range（DB 中也不存在 2024-08-05
  之后的 replay 行）

### 3.2 公式

为了与 dashboard 一致，每个候选 slice 计算：

| 字段 | 公式 |
|---|---|
| `paired` | 切片内 `direction_correct ∈ {0, 1}` 的记录数 |
| `correct` | 切片内 `direction_correct = 1` 的记录数 |
| `wrong` | `paired − correct` |
| `fer`（false_exclusion_rate）| `correct / paired` —— 因为 R4 是 fully-bullish 切片，"误杀"指**排除一个原本预测正确的多头判断** |
| `nb`（net_benefit）| `(base_correct − slice_correct) / (base_paired − slice_paired) − base_correct / base_paired` —— 即"剔除该切片后整体准确率的提升幅度" |

baseline = 286 paired × confidence_level∈{high,medium,low}（与
`soft_metadata_simulator._net_benefit_from_dashboard` 一致）：
- `base_paired = 286`
- `base_correct = 139`
- `base_acc = 0.4860`

### 3.3 候选维度清单

| # | 维度 | 切片 |
|---|---|---|
| 1 | `confidence_level` | `high` / `medium` |
| 2 | `peer_adjustment` | `upgrade` / `hold` / `downgrade` |
| 3 | `peer_confirm_count` | 0 / 1 / 2 / 3 / ≥2 / ≤1 |
| 4 | `soft_signal` | `none` / `peer_weaken` |
| 5 | `primary_score_raw` 阈值 | `≥ 2.0` / `≥ 2.5` / `≥ 3.0` / `≥ 3.5` |
| 6 | `pos20` 阈值 | `≥ 0.70` / `≥ 0.75` / `≥ 0.80` / `≥ 0.85` / `≥ 0.90` / `≤ 0.70` / `≤ 0.75` / `≤ 0.80` / `≤ 0.85` / `≤ 0.90` |
| 7 | `avgo_minus_soxx_20d` 阈值 | `≥ 6` / `≥ 7` / `≥ 8` / `≥ 10` / `≥ 12` |
| 8 | quarter（month / window） | 2023-Q1〜2024-Q3 |
| 9 | holdout window split | first / second half（按 `analysis_date` 排序） |
| 10 | confidence × peer_adjustment 交叉 | `confidence=high ∧ peer=hold` 等 |
| 11（bonus）| pos20 + diff 交叉 | `pos20 ≥ 0.85 ∧ diff ≥ 8` |
| 12（bonus）| pos20 + peer 交叉 | `pos20 ≤ 0.75 ∧ peer ≠ downgrade` |
| 13（bonus）| `peer ≠ downgrade ∧ peer_confirm ≥ 2` | — |

### 3.4 筛选标准

**candidate viable iff**：
- `paired ≥ 30`（统计学有效性 + 与 hard gate 第 2 项门槛对齐）
- `fer ≤ 0.10`（与 hard gate 第 3 项 `false_exclusion_rate_lte_0_10`
  对齐）
- `nb ≥ +0.05`（与 hard gate 第 4 项 `net_benefit_gte_0_05` 对齐）
- 不依赖 2026 final test range
- 不只是单窗口偶然（即在 first / second half 都至少**不**完全偏向
  一边）

任何一项不满足 → **不 viable**。

---

## 4. 候选结果表

### 4.1 完整结果（按 fer 升序）

| # | label | paired | correct | wrong | fer | nb | paired ≥ 30 | fer ≤ 0.10 | nb ≥ 0.05 |
|---|---|---:|---:|---:|---:|---:|:-:|:-:|:-:|
| 1 | R4 ∧ quarter=2023-Q1 | 4 | 0 | 4 | 0.0000 | 0.0069 | ✗ | ✓ | ✗ |
| 2 | R4 ∧ quarter=2023-Q2 | 7 | 1 | 6 | 0.1429 | 0.0086 | ✗ | ✗ | ✗ |
| 3 | R4 ∧ pos20≥0.85 ∧ diff≥8 | 6 | 1 | 5 | 0.1667 | 0.0068 | ✗ | ✗ | ✗ |
| 4 | R4 ∧ peer_confirm=2 | 11 | 2 | 9 | 0.1818 | 0.0122 | ✗ | ✗ | ✗ |
| 5 | R4 ∧ avgo-soxx≥10 | 11 | 2 | 9 | 0.1818 | 0.0122 | ✗ | ✗ | ✗ |
| 6 | R4 ∧ avgo-soxx≥12 | 10 | 2 | 8 | 0.2000 | 0.0104 | ✗ | ✗ | ✗ |
| 7 | R4 ∧ quarter=2024-Q2 | 5 | 1 | 4 | 0.2000 | 0.0051 | ✗ | ✗ | ✗ |
| 8 | R4 ∧ first_half (chronological) | 17 | 4 | 13 | 0.2353 | 0.0158 | ✗ | ✗ | ✗ |
| 9 | R4 ∧ peer=upgrade | 24 | 6 | 18 | 0.2500 | 0.0216 | ✗ | ✗ | ✗ |
| 10 | R4 ∧ peer_confirm≥2 | 24 | 6 | 18 | 0.2500 | 0.0216 | ✗ | ✗ | ✗ |
| 11 | R4 ∧ psr≥3.0 | 12 | 3 | 9 | 0.2500 | 0.0103 | ✗ | ✗ | ✗ |
| 12 | R4 ∧ pos20≤0.85 | 20 | 5 | 15 | 0.2500 | 0.0177 | ✗ | ✗ | ✗ |
| 13 | R4 ∧ avgo-soxx≥8 | 16 | 4 | 12 | 0.2500 | 0.0140 | ✗ | ✗ | ✗ |
| 14 | R4 ∧ quarter=2023-Q4 | 8 | 2 | 6 | 0.2500 | 0.0068 | ✗ | ✗ | ✗ |
| 15 | R4 ∧ confidence=high ∧ peer=upgrade | 24 | 6 | 18 | 0.2500 | 0.0216 | ✗ | ✗ | ✗ |
| 16 | R4 ∧ psr≥3.5 | 11 | 3 | 8 | 0.2727 | 0.0085 | ✗ | ✗ | ✗ |
| 17 | R4 ∧ pos20≥0.75 | 24 | 7 | 17 | 0.2917 | 0.0178 | ✗ | ✗ | ✗ |
| 18 | R4 ∧ pos20≥0.70 | 27 | 8 | 19 | 0.2963 | 0.0198 | ✗ | ✗ | ✗ |
| 19 | R4 ∧ pos20≥0.80 | 20 | 6 | 14 | 0.3000 | 0.0140 | ✗ | ✗ | ✗ |
| 20 | R4 ∧ avgo-soxx≥7 | 20 | 6 | 14 | 0.3000 | 0.0140 | ✗ | ✗ | ✗ |
| 21 | R4 ∧ peer_confirm=3 | 13 | 4 | 9 | 0.3077 | 0.0085 | ✗ | ✗ | ✗ |
| 22 | **R4 ∧ confidence=high** | **32** | **10** | **22** | **0.3125** | **0.0219** | **✓** | **✗** | **✗** |
| 23 | **R4 ∧ soft_signal=none** | **32** | **10** | **22** | **0.3125** | **0.0219** | **✓** | **✗** | **✗** |
| 24 | R4 ∧ pos20≤0.90 | 25 | 8 | 17 | 0.3200 | 0.0159 | ✗ | ✗ | ✗ |
| 25 | R4 ∧ psr≥2.0 | 28 | 9 | 19 | 0.3214 | 0.0179 | ✗ | ✗ | ✗ |
| 26 | R4 ∧ avgo-soxx≥6 | 28 | 9 | 19 | 0.3214 | 0.0179 | ✗ | ✗ | ✗ |
| 27 | R4 ∧ psr≥2.5 | 15 | 5 | 10 | 0.3333 | 0.0085 | ✗ | ✗ | ✗ |
| 28 | R4 ∧ pos20≥0.90 | 9 | 3 | 6 | 0.3333 | 0.0050 | ✗ | ✗ | ✗ |
| 29 | R4 ∧ pos20≤0.75 ∧ peer≠downgrade | 9 | 3 | 6 | 0.3333 | 0.0050 | ✗ | ✗ | ✗ |
| 30 | R4 ∧ pos20≤0.80 | 14 | 5 | 9 | 0.3571 | 0.0066 | ✗ | ✗ | ✗ |
| 31 | R4 ∧ pos20≤0.75 | 10 | 4 | 6 | 0.4000 | 0.0031 | ✗ | ✗ | ✗ |
| 32 | R4 ∧ second_half (chronological) | 17 | 7 | 10 | 0.4118 | 0.0047 | ✗ | ✗ | ✗ |
| 33 | R4 ∧ pos20≥0.85 | 14 | 6 | 8 | 0.4286 | 0.0030 | ✗ | ✗ | ✗ |
| 34 | R4 ∧ pos20≤0.70 | 7 | 3 | 4 | 0.4286 | 0.0014 | ✗ | ✗ | ✗ |
| 35 | R4 ∧ peer=hold | 8 | 4 | 4 | 0.5000 | -0.0004 | ✗ | ✗ | ✗ |
| 36 | R4 ∧ confidence=high ∧ peer=hold | 8 | 4 | 4 | 0.5000 | -0.0004 | ✗ | ✗ | ✗ |
| 37 | R4 ∧ peer_confirm≤1 | 10 | 5 | 5 | 0.5000 | -0.0005 | ✗ | ✗ | ✗ |
| 38 | R4 ∧ confidence=medium | 2 | 1 | 1 | 0.5000 | -0.0001 | ✗ | ✗ | ✗ |
| 39 | R4 ∧ peer=downgrade | 2 | 1 | 1 | 0.5000 | -0.0001 | ✗ | ✗ | ✗ |
| 40 | R4 ∧ soft_signal=peer_weaken | 2 | 1 | 1 | 0.5000 | -0.0001 | ✗ | ✗ | ✗ |
| 41 | R4 ∧ quarter=2024-Q1 | 5 | 4 | 1 | 0.8000 | -0.0056 | ✗ | ✗ | ✗ |
| 42 | R4 ∧ quarter=2023-Q3 | 2 | 2 | 0 | 1.0000 | -0.0036 | ✗ | ✗ | ✗ |

### 4.2 Top 3 candidates by closeness to gates

按 "fer 越低 + paired 越大 + nb 越接近 +0.05" 综合排序，最接近门槛
的 3 个候选：

| 排序 | label | paired | fer | nb | 离哪个门槛最近 | 离 viable 还差什么 |
|---|---|---:|---:|---:|---|---|
| 1 | **R4 ∧ confidence=high** | 32 | 0.3125 | +0.0219 | 唯一通过 paired ≥ 30 的非平凡子切片 | fer 还差 0.21；nb 还差 0.03 |
| 2 | R4 ∧ peer=upgrade | 24 | 0.2500 | +0.0216 | 同时 fer 较低 | paired 差 6；fer 差 0.15；nb 差 0.03 |
| 3 | R4 ∧ avgo-soxx≥10 | 11 | 0.1818 | +0.0122 | 触发条件加严能压低 fer | paired 差 19；fer 差 0.08；nb 差 0.04 |

**没有任何候选同时满足三项门槛。**

---

## 5. 是否找到 viable narrower candidate？

**没有。**

- 所有 42 个候选切片中，**没有一个**同时满足 `paired ≥ 30 ∧ fer ≤ 0.10 ∧ nb ≥ +0.05`
- 唯一通过 `paired ≥ 30` 的两个非平凡切片（`R4 ∧ confidence=high` 与
  `R4 ∧ soft_signal=none`，均 n=32）的 fer 都是 0.3125、nb 都是
  +0.0219 —— 它们和 R4_full 几乎重合（仅去掉 2 个 medium / 2 个有
  soft_signal 的样本），**没有提供任何额外的 narrower 力量**
- 所有 fer ≤ 0.20 的候选切片 paired 都 ≤ 11，远远不到 30 阈值
- 所有 nb 接近 +0.05 的候选切片**不存在** —— 整个候选清单的最大 nb
  也只是 +0.0219（== R4_full 自身），任何缩窄都让 nb 下降

---

## 6. 对 hard gate 的影响

| Gate | 当前 | 如果实施任意一个 narrower R4？ |
|---|---|---|
| `total_paired_ge_90` | PASS（286） | 不变（baseline 不动） |
| `candidate_paired_ge_30` | PASS（34） | 多数候选会**变 fail**（因为 narrower paired < 30） |
| `false_exclusion_rate_lte_0_10` | FAIL（0.3235） | 极少数候选 fer ≤ 0.10（如 quarter=2023-Q1 的 fer=0），但都 paired < 5 → noise |
| `net_benefit_gte_0_05` | FAIL（+0.0219） | 全部候选 nb < +0.05 |
| `protection_layer_connected` | FAIL | 仍 fail（v1 hard-coded） |
| `cross_window_holdout_pass` | FAIL | 仍 fail |

**结论**：实施任何 narrower R4 都**不会**让 hard gate 从 2 pass / 4
fail 改善到 4 pass / 2 fail，最多让 candidate_paired 也从 pass 变
fail，让 hard gate 状态**变差**。

---

## 7. GO / NO-GO 结论

### 7.1 NO-GO

**Step 2G-8B 推荐：NO-GO 进入 narrower R4 hard implementation。**

理由：
1. **结构性不利**：R4 自身 accuracy = 0.3235 比 baseline 0.4860 低
   ~16 个百分点。在仅 34 paired 的池里寻找一个准确率"反而高"的
   sub-slice 不现实
2. **样本量瓶颈**：R4 只有 34 paired；任何二级条件都会把 paired
   砍到 ≤ 24，离 30-paired 门槛非常近，且越窄方差越大
3. **net_benefit 上界低**：counterfactual nb 公式上界由"剔除该切片
   后整体 acc 提升幅度"决定。R4 整体只能让 base_acc 从 0.4860 提到
   0.5079（提升 0.0219）。任何 narrower 子集都更小，杠杆更弱，
   nb 上界 < +0.0219
4. **Top-3 candidates 的实际 fer**（0.18 - 0.31）距离 0.10 仍很远
5. **季度集中**：R4 触发分布在 13 个月份；最低 fer 的几个季度
   （2023-Q1 fer=0、2023-Q2 fer=0.14）都 paired ≤ 7 —— 是噪声而非
   信号
6. holdout split 检验：first_half (n=17) fer=0.24，second_half
   (n=17) fer=0.41 —— **跨窗口不稳定**，第二个窗口本身就 fer >> 0.10

### 7.2 不进入 Step 2G-8B.1 实施

任何"实施" narrower R4 hard 路径的尝试都会：
- 让 04 / 05 / 07 required schema 升级（违反 8A 系列设计约束）
- 让 hard exclusion 启用（违反 Step 2G-8 launch review 的 NO-GO）
- 把当前 Gate 5 的 sidecar 隔离破坏
- 在仅 34 paired + 跨窗口不稳定的数据上做不可逆决策

---

## 8. 下一步建议

按推荐优先级：

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **本文 commit + checkpoint** | 把 NO-GO 结论 + 候选表归档进 main，让未来读者一眼看到"narrower R4 已尝试，不可行" | **本轮** |
| 2 | **Step 2G-8C** holdout gap analysis | 只读对比 in-sample vs holdout window；解释为何 R4 在 first_half / second_half 表现差距如此大；为 Gate 6 找诊断 | **高**（与 Step 3 calibration 重启耦合，但研究层先做不影响 hard） |
| 3 | **Step 2G-8D**（建议新增）扩展 replay 覆盖 | 把 replay 跑到 2024-08 → 2025-12（不触碰 2026-01-01 之后 final test）以扩充 baseline；R4 paired 有望从 34 涨到 ~70+，narrower 切片 paired 也会变得可信 | **高**（数据层；解 nb 上界瓶颈） |
| 4 | **Step 2G-8E**（建议新增）替换候选 R-series | 离开 R4，研究 R1 / R2 / R3 / R5 是否有 acc 显著低于 baseline 0.486 的切片 —— R4 不是唯一候选，可能 R-series 中有更好的 hard exclusion 候选 | 中（探索性） |
| 5 | **Step 2G-8B.1 实施** | 把某 narrower R4 接入 hard pipeline | **❌ 不推荐**（数据层 NO-GO） |
| 6 | 让 `_PROTECTION_LAYER_CONNECTED` 翻 True | 让 Gate 5 自动 pass | **❌ 不推荐**（与 8A 设计 / 8 launch review 冲突） |
| 7 | 升级 04 required `anti_false_exclusion_triggered` | 把 R4 标记进 04 主链 | **❌ 不推荐**（与 8A 系列 sidecar-only 边界冲突） |

**强制约束**（继承 Step 2G-8A 设计 §13 / 8A.x checkpoint）：
- 不改 04 / 05 / 07 required 字段
- 不改 `run_predict` 主链
- 不写 DB
- 不出现 19 forbidden words / 16 forbidden words / 8 forbidden words
- `hard_exclusion_allowed` 永远 `False`
- `protection_layer_connected_for_gate` 永远 `False`（v1）

---

## 9. 严守边界

本文是**纯 read-only 研究文档**：

- ❌ 没改任何代码
- ❌ 没改 DB schema
- ❌ 没写 DB（只 SELECT）
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
- ❌ 没触碰 2026-01-01 之后 final test range（DB 中也无此区间数据）
- ❌ 没运行 replay / 没新写 replay 行
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` /
  `avgo_agent.db.backup_*`
- ❌ 没运行 `pytest`（本轮纯研究；无新测试）
- ❌ 没新增 / 修改任何 service / ui / test / DB / contract
- ✅ 只跑 read-only Python 调用 + read-only SQLite SELECT
- ✅ 数字与 Step 2G-7C / 2G-8 / 2G-8A.x checkpoint 完全一致
- ✅ 只新增 1 份 markdown 研究文档（本文件）
