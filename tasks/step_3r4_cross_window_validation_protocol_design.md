# Step 3R-4 — Cross-Window Validation Protocol Design

> **设计文档（cross-window validation protocol design），不实现，不改代码。**
> 本文档**冻结** Step 3R 全程的多窗口 holdout 协议：windows 划分、
> leave-one-window-out 折叠方式、6 个 validation metric、gate
> thresholds、no-go 规则、`regime_validation_report.v1` 输出
> schema、与 Step 3R-2 helper / Step 2G-8D extend replay coverage
> 的衔接边界。
>
> 本轮**不动任何代码**：不改 `predict.py` / `run_predict` /
> `scanner.py` / `prediction_store.py` / `app.py` / 任何 `ui/*` /
> `services/*` / 任何 builder / DB schema / 任何 test 中的任何一处。
>
> **本文不实现验证工具、不写 helper、不实施 protocol**；只在
> markdown 层冻结协议本身，给后续 3R-2 / 3R-3 / 3R-5 / 3R-6 提供
> 强制 gate。

---

## 1. 背景

- **Step 3R-0** restart scope checkpoint 已冻结全程边界（commit `1b7288e`）
- **Step 3R-1** regime label design + checkpoint 已冻结 v1 label set
  + `regime_labels.v1` schema + 8 项 anti-lookahead 不变量（commits
  `a8df93a` / `8d4fe8f`）
- 但是 **Step 3R-1 §5 / 6.1 / 6.5 列出的所有 bucket 阈值都只是
  design candidates，未验证**
- **Step 3R-4 负责定义验证协议**：在没有 3R-4 的情况下，**禁止启动**
  Step 3R-2 helper / Step 3R-3 smoothing / Step 3R-5 formula design
- 本文输出**协议本身**，不输出协议结果；协议结果由未来 3R-2 / 3R-3
  diagnostics / 3R-6 simulator 在该协议下分别报告

---

## 2. 为什么需要 cross-window validation

| # | 证据 | 教训 |
|---|---|---|
| 1 | **Step 3B-1**：4×4 lookup 在 W1↔W2 双向 holdout 上 6 项标准只过 2 项 | 单方向 holdout 不够；必须双向 |
| 2 | **Step 3A-4**：扩第三窗口到 380 records 后 Method A 改善（calibrated_high acc 0.333 → 0.611）但 Method B 仍崩 | 单一 fold 容易找到"好看的方向"；必须 leave-one-window-out |
| 3 | **Step 2G-8C**：R4 H1 fer 0.24 vs H2 fer 0.41 gap +0.18 | 即使设计时分窗，也要每个窗口分别报告，不能 pool |
| 4 | **Step 2G-8C**：2024-02 单月 fer 0.75（4 records）单月贡献 ≈ 0.06 absolute FER | 单月 / 单事件能严重扭曲 pooled metric；必须看 worst-window 而不是 pooled |
| 5 | **Step 2G-8B**：42 个 R4 narrower 候选切片 0/42 同时满足三项门槛 | 单窗优化得到的"好看"切片不能跨窗 |
| 6 | **Step 2G 全程边界 + Step 3R-0**：不能用 2026 final test 调参 | validation 必须严格 ≤ 2025-12-31 |

**核心教训**：单窗口优化 + pooled metric **必然过拟合**。任何
calibration / smoothing / formula candidate 必须在**多窗口 +
leave-one-window-out + worst-window 优先**协议下被验证；否则视为
**未验证**。

---

## 3. validation windows

### 3.1 当前可用窗口

| 窗口 | 起止日期 | paired records（估） | 数据来源 |
|---|---|---:|---|
| **W1** | 2023-01-03 → 2023-08-31 | ~ 130（Step 3A-4 第三窗口） | `replay_AVGO_*` |
| **W2** | 2023-09-01 → 2024-02-29 | ~ 100（含 Step 2G-8C 发现的 2024-02 异常） | `replay_AVGO_*` |
| **W3** | 2024-03-01 → 2024-08-02 | ~ 56（Step 3A-3 second-window 残段 + Step 2G-7C baseline 截止） | `replay_AVGO_*` |

合计 ≈ **286 paired**（与 Step 2G-7C / 8B / 8C 一致）。

### 3.2 可选窗口

| 窗口 | 起止日期 | 启用条件 |
|---|---|---|
| **W4 optional** | 2024-08-03 → 2025-12-31 | **仅在 Step 2G-8D extend replay coverage 完成后启用** |

W4 启用前：3-fold leave-one-window-out（W1 / W2 / W3）；
W4 启用后：4-fold leave-one-window-out（W1 / W2 / W3 / W4）。

### 3.3 永久封禁

| 区间 | 状态 |
|---|---|
| **2026-01-01 → ∞** | **final test set；永久封禁** |

任何 validation 协议**不得**：
- 在 2026-01-01 之后的数据上 train / fit / validate
- 在 2026-01-01 之后的数据上 inspect / preview / "看一眼回头改"
- 把 2026 数据用于 hyperparameter selection / threshold tuning

触发任意一项 → 任务中止 + 验证集污染。

### 3.4 窗口边界判定原则

- 窗口左闭右闭（`as_of_date ∈ [start, end]`）
- 窗口边界对齐自然月：避免跨月切割误读 monthly context
- W2 故意覆盖 2024-02：这是 Step 2G-8C 发现的 shock_month；**不**
  允许把它单独移出 W2（必须在 worst-window 暴露）
- 窗口数量 v1 = **3** （W1+W2+W3）；4-fold（含 W4）作为 conditional
  扩展，不阻塞 v1 协议交付

---

## 4. validation protocol

### 4.1 leave-one-window-out 折叠

3-fold（W4 不可用时）：

| fold | train | validate（held-out） |
|---|---|---|
| F1 | W2 + W3 | **W1** |
| F2 | W1 + W3 | **W2** |
| F3 | W1 + W2 | **W3** |

4-fold（W4 可用时）：

| fold | train | validate |
|---|---|---|
| F1 | W2 + W3 + W4 | **W1** |
| F2 | W1 + W3 + W4 | **W2** |
| F3 | W1 + W2 + W4 | **W3** |
| F4 | W1 + W2 + W3 | **W4** |

### 4.2 协议要求

| # | 要求 |
|---|---|
| 1 | **每个 fold 都报告**：candidate 必须在每个 held-out window 上单独报告 6 个 metric；不允许只 pool |
| 2 | **不允许只汇报 pooled result**：pooled metric 仅作参考，**不**作为 gate 决策 |
| 3 | **worst-window 优先**：gate 决策以 fold 中**最差**的 held-out window 为准；任一 fold 的 held-out window 不通过 → 整个 candidate 不通过 |
| 4 | **train 不偷看 validate**：每个 fold 的 train 阶段**不**得读取该 fold 的 held-out window 数据 |
| 5 | **anti-lookahead**：在 train + validate 任一阶段，**不**得使用 `as_of_date` 当日及之后的数据（与 Step 3R-1 §7 8 项 anti-lookahead 一致） |
| 6 | **不依赖 2026 数据**：每个 fold 的 train + validate 数据范围严格 ≤ 2025-12-31 |
| 7 | **strict-causal monthly context**：earnings / breakout / shock 月份的 derive 必须只用当天及以前数据，事后不回标 |

---

## 5. 6 个 validation metrics

### 5.1 `accuracy_delta_vs_baseline`

| 项 | 值 |
|---|---|
| **definition** | 在 held-out window 上，candidate 触发样本剔除后整体 accuracy 减去 baseline accuracy |
| **pass threshold** | ≥ **+0.02**（接近 Step 2G-7C 的 nb 阈值精神，但作为 candidate-level 指标） |
| **why important** | 与 Step 2G-7C net_benefit 公式一致；防止 candidate 触发后整体精度反降 |

### 5.2 `false_exclusion_rate`

| 项 | 值 |
|---|---|
| **definition** | candidate 触发样本中 `direction_correct = 1` 的比率（即 `correct / paired` for fully-bullish slice）|
| **pass threshold** | **≤ 0.10**（与 Step 2G-7C hard gate `false_exclusion_rate_lte_0_10` 一致）|
| **why important** | 控制误杀；R4 当前 0.3235 远不达；narrower R4 的全部尝试也不达 |

### 5.3 `net_benefit`

| 项 | 值 |
|---|---|
| **definition** | counterfactual：在 held-out window 上剔除 candidate 触发样本后整体 acc 提升幅度（与 `soft_metadata_simulator._net_benefit_from_dashboard` 一致）|
| **pass threshold** | **≥ +0.05**（与 Step 2G-7C `net_benefit_gte_0_05` 一致）|
| **why important** | 与 hard gate 公式对齐；R4 当前 +0.0219 不达；narrower R4 全部不达 |

### 5.4 `survival_case_preservation`

| 项 | 值 |
|---|---|
| **definition** | candidate 触发**且**预测正确的样本（survival case）在该 held-out window 中能被 sidecar **明确呈现**的比率（不静默） |
| **pass threshold** | **≥ 0.80** |
| **why important** | 继承 Step 2G-6C `triggered_but_not_error` 象限累计 + Step 2G-7A AFX `r4_survival_case` finding 的设计；不能为压低 fer 而把 survival case 静默掉 |

### 5.5 `cross_window_variance`

| 项 | 值 |
|---|---|
| **definition** | 该 candidate 在所有 held-out windows 上 `false_exclusion_rate` 的极差（max − min） |
| **pass threshold** | **≤ 0.10** |
| **why important** | 直接对应 Step 2G-8C 发现的 R4 H1/H2 gap +0.18 —— v1 用 0.10 上限阻止跨窗"好坏天差地别"的 candidate 通过 |

### 5.6 `minimum_window_sample_size`

| 项 | 值 |
|---|---|
| **definition** | 每个 fold 的 held-out window 中 candidate 触发的 paired 样本数最小值 |
| **pass threshold** | **≥ 20** |
| **why important** | 防止 candidate 在某窗口只触发 ≤ 5 records 就被"幸运"算成 pass；防止 noise pass。Step 2G-8B 已显示 paired ≤ 11 的切片大量噪声 |

### 5.7 metric 与 hard gate 的对齐

| 本协议 metric | Step 2G-7C hard gate | 关系 |
|---|---|---|
| `false_exclusion_rate` ≤ 0.10 | `false_exclusion_rate_lte_0_10` | **完全对齐** |
| `net_benefit` ≥ +0.05 | `net_benefit_gte_0_05` | **完全对齐** |
| `minimum_window_sample_size` ≥ 20 | `candidate_paired_ge_30` | 本协议**更严**（per-window 20，hard gate 是 total 30）|
| `cross_window_variance` ≤ 0.10 | `cross_window_holdout_pass`（PASS / FAIL） | 本协议**量化**（极差 ≤ 0.10）vs 二值 |
| `accuracy_delta_vs_baseline` ≥ +0.02 | （无对应）| 新增；防止整体精度反降 |
| `survival_case_preservation` ≥ 0.80 | （无对应）| 新增；保护 Step 2G-6C / 7A 的 survival 语义 |

---

## 6. Gate thresholds

| metric | gate threshold | 备注 |
|---|---|---|
| `minimum_window_sample_size` | **≥ 20** | per-fold held-out window |
| `false_exclusion_rate` | **≤ 0.10** | per-fold held-out window，**worst-window 决胜** |
| `net_benefit` | **≥ +0.05** | per-fold held-out window |
| `accuracy_delta_vs_baseline` | **≥ +0.02** | per-fold held-out window |
| `cross_window_variance` | **≤ 0.10** | 跨 fold 极差 |
| `survival_case_preservation` | **≥ 0.80** | per-fold held-out window |
| **no single-window collapse** | 任一 window 不能 fer ≥ 0.20 OR nb ≤ 0 | 兜底守卫 |

### 6.1 阈值的可调性

- 这些是 **protocol thresholds**，**不**是公式参数
- 阈值可在**未来 checkpoint** 调整（例如样本量大幅扩增后放松 ≥20，
  或 cross_window_variance 收紧到 ≤ 0.07）
- 阈值调整必须**经过 launch review**；不能因为某 candidate "差一点
  没过" 就放松
- **不得**用 2026 数据调阈值（任何"看一眼 2026 再回头改"立即触发
  任务中止）

### 6.2 阈值的整体逻辑

| 维度 | 阈值 | 教训来源 |
|---|---|---|
| 误杀率上限 | fer ≤ 0.10 | Step 2G-7C hard gate |
| 净收益下限 | nb ≥ +0.05 | Step 2G-7C hard gate |
| 跨窗稳定性 | variance ≤ 0.10 | Step 2G-8C R4 gap +0.18 |
| 样本量 | per-window ≥ 20 | Step 2G-8B paired ≤ 11 切片噪声 |
| 整体精度 | delta ≥ +0.02 | 防止"局部 fer 低，整体 acc 反降"陷阱 |
| 保留 survival | preservation ≥ 0.80 | Step 2G-6C `triggered_but_not_error` 象限语义 |

---

## 7. label threshold validation

Step 3R-1 §5 列出的所有 v1 label bucket 阈值**必须**在本协议下被
验证：

| label | 待验证阈值 | 验证方式 |
|---|---|---|
| `pos20_regime` | low / mid / high / extreme 边界（0.35 / 0.65 / 0.85） | 在每个 fold 的 held-out window 上，每个 bucket 的样本量 + per-bucket fer / nb 必须满足 §6 阈值 |
| `avgo_minus_soxx_20d_regime` | 边界（−0.05 / +0.05 / +0.12） | 同上 |
| `peer_momentum_regime` | weak / mixed / confirmed / overheated 阈值（5d 同向 50% / 70% / 85%）| 同上 |
| `market_trend_regime` | weak / neutral / bull / sustained_bull 阈值（QQQ 60d slope / drawdown / 持续 ≥ 3 月）| 同上；需要 QQQ csv 输入 |
| `monthly_context_regime` | normal / earnings / breakout / shock 阈值（月度收益 ±5% / +10% / +15%；单日 5%）| 同上；strict-causal monthly derive |

**核心约束**：阈值**不能凭直觉写死**；任何 label 在任一 fold 的
held-out window 上不通过 §6 阈值 → 必须**回到 Step 3R-1 重新设计
该 label** 而非调阈值。

---

## 8. model / candidate validation

未来 Step 3R-3 smoothing candidate / Step 3R-5 formula / Step 3R-6
read-only simulator 的**任何 candidate** 都必须按本协议产出
**完整报告**：

| 报告项 | 内容 |
|---|---|
| **per-window metrics** | 每个 held-out window 上 6 个 metric 的实际值 |
| **pooled metrics** | 跨所有 held-out window 的合并值（**仅参考，不作 gate**） |
| **worst-window metrics** | 每个 metric 的最差值（决胜） |
| **leave-one-window-out result** | 每个 fold 的 pass/fail，含失败 metric 列表 |
| **fail reason** | 如果整体 fail，列出第一项触发 fail 的 metric 与 fold |
| **是否触碰 final test** | bool；任何为 true → 该报告作废 + 任务中止 |

报告未完整呈现以上所有项 → 视为**未验证**；不得进入 Step 3R-7
sidecar integration。

---

## 9. no-go rules

任意一条触发 → candidate 整体不通过：

| # | no-go 条件 |
|---|---|
| 1 | 任一 fold 的 held-out window 样本数 < 20 |
| 2 | 任一 fold 的 held-out window `false_exclusion_rate` > **0.20**（兜底守卫，比 0.10 阈值更宽松，但触发即代表 candidate 在该窗"崩")|
| 3 | pooled pass 但任一 worst-window fail |
| 4 | candidate 需要 2026 数据才能 pass |
| 5 | candidate 牺牲 survival cases（preservation < 0.80） |
| 6 | candidate 任一 fold 的 `cross_window_variance` > 0.10 |
| 7 | candidate 在 train 阶段读取了该 fold 的 held-out window 数据 |
| 8 | candidate 触碰 2026-01-01 之后任何数据 |
| 9 | candidate 的 `accuracy_delta_vs_baseline` < 0（剔除后整体精度反降） |
| 10 | report 缺失 §8 任意必备字段 |

**触发 no-go = candidate 报废 + 必须回 3R-1 / 3R-3 / 3R-5 重新设计**；
**不允许**回头调本协议阈值蒙混过关。

---

## 10. 与 Step 3R-2 的关系

| 维度 | Step 3R-2（read-only regime label diagnostics helper） |
|---|---|
| 输出 | 每个 `as_of_date` 的 `regime_labels.v1` 与 read-only diagnostics（per-label sample / fer / nb 分布） |
| 是否优化 thresholds | **❌ 否**；只**应用** Step 3R-1 design 的阈值候选 |
| 是否宣称 pass / fail | **❌ 否**；3R-2 只产出原始数据，不做 gate 决策 |
| pass / fail 由谁宣称 | 由本 Step 3R-4 协议下的 future validation tool / report 产出（未来 3R-3 / 3R-6 实施时） |
| 是否被本协议依赖 | 是 —— 3R-2 提供 per-window per-label 的样本切片 + raw metric；本协议负责"如何切 + 如何评分" |
| 启动顺序 | **本 3R-4 protocol 必须先冻结**；3R-2 helper 才能进入实施 |

→ Step 3R-2 helper 是**数据层**，Step 3R-4 协议是**评分层**；
两者解耦但 3R-2 必须等本协议的 checkpoint 落地后启动。

---

## 11. 与 Step 2G-8D 的关系

| 维度 | Step 2G-8D extend replay coverage |
|---|---|
| 范围 | 把 replay 跑到 2024-08-03 → 2025-12-31，扩充 paired 样本 |
| 是否触碰 2026 | **❌ 否**；2025-12-31 上限严格 |
| 是否 formula | **❌ 否**；纯数据层 |
| 与本协议关系 | 提供 W4 候选数据；W4 启用前本协议是 3-fold；W4 启用后扩为 4-fold |
| 是否阻塞 v1 协议 | **❌ 否**；3-fold（W1+W2+W3）即可启动 |
| 优先级 | 与本协议**解耦可并行**；3-fold v1 协议交付后再扩 4-fold |
| Step 3R-2 是否依赖 | 不依赖 W4；3-fold 即可启动 3R-2 |

→ Step 2G-8D 与 Step 3R 系列**解耦可并行**；本协议的 v1 在 3-fold
即可锁定，4-fold 是 conditional extension。

---

## 12. 输出 schema 草案

```json
{
  "schema_version": "regime_validation_report.v1",
  "windows": {
    "W1": {"start": "2023-01-03", "end": "2023-08-31", "paired": 130},
    "W2": {"start": "2023-09-01", "end": "2024-02-29", "paired": 100},
    "W3": {"start": "2024-03-01", "end": "2024-08-02", "paired": 56},
    "W4": null
  },
  "candidate_name": "regime_aware_calibration_v0_smoothing",
  "candidate_kind": "smoothing | formula | label_assignment",
  "fold_count": 3,
  "per_window_metrics": {
    "W1": {
      "minimum_window_sample_size": 28,
      "false_exclusion_rate": 0.0857,
      "net_benefit": 0.0512,
      "accuracy_delta_vs_baseline": 0.0421,
      "survival_case_preservation": 0.85,
      "triggered_paired": 28
    },
    "W2": {...},
    "W3": {...}
  },
  "pooled_metrics": {
    "false_exclusion_rate": 0.0921,
    "net_benefit": 0.0498,
    "accuracy_delta_vs_baseline": 0.0395
  },
  "worst_window": "W2",
  "worst_window_metrics": {
    "false_exclusion_rate": 0.1052,
    "net_benefit": 0.0388
  },
  "cross_window_variance": {
    "false_exclusion_rate": 0.0512,
    "net_benefit": 0.0123
  },
  "leave_one_window_out": {
    "F1_train_W2_W3_validate_W1": "pass",
    "F2_train_W1_W3_validate_W2": "fail",
    "F3_train_W1_W2_validate_W3": "pass"
  },
  "gate_status": {
    "minimum_window_sample_size": "pass",
    "false_exclusion_rate": "fail",
    "net_benefit": "pass",
    "accuracy_delta_vs_baseline": "pass",
    "cross_window_variance": "pass",
    "survival_case_preservation": "pass",
    "no_single_window_collapse": "pass"
  },
  "overall_status": "fail",
  "fail_reason": "false_exclusion_rate at W2 = 0.1052 > 0.10 gate",
  "final_test_refusal": false,
  "data_cutoff_used": "2024-08-02",
  "warnings": []
}
```

### 12.1 schema 不变量

| 字段 | 不变量 |
|---|---|
| `schema_version` | 总是 `"regime_validation_report.v1"` |
| `windows` | W1 / W2 / W3 必须 present；W4 可为 null（3-fold） |
| `fold_count` | `3` 或 `4`（整数） |
| `per_window_metrics` | 每个 held-out window 必须 6 metric 全部 present |
| `worst_window_metrics` | 永远基于 worst-window 的实际值 |
| `gate_status` | 7 项（6 metric + no_single_window_collapse）全部 `"pass"` 才能 `overall_status = "pass"` |
| `overall_status` | `"pass"` / `"fail"` 二选一；不允许 `"partial"` |
| `final_test_refusal` | bool；如果 `True` → 整个报告作废 |
| `data_cutoff_used` | ≤ `2025-12-31`；硬不变量 |

---

## 13. 成功标准

| # | 标准 | 验证方式 |
|---|---|---|
| 1 | **协议能复现 Step 2G-8C 的 R4 FAIL** | 在 R4 candidate 上跑本协议，必然触发 `cross_window_variance > 0.10` 与 `false_exclusion_rate > 0.10` |
| 2 | **协议能阻止单窗口 overfit** | leave-one-window-out + worst-window 决胜机制；任何只在 pooled 上看好的 candidate 必然被 worst-window 击穿 |
| 3 | **协议不用 2026 final test** | `data_cutoff_used ≤ 2025-12-31` 硬不变量；任何 2026 触碰 → `final_test_refusal = True` 且报告作废 |
| 4 | **协议能供 Step 3R-2 / 3R-3 / 3R-5 / 3R-6 使用** | 输出 schema 稳定；不依赖未实施的 helper |
| 5 | **未来实施时 full pytest 0 failed** | 与现状 2604 / 0 failed / 10 skipped 持平或扩张 |
| 6 | **每个 candidate 必须按本协议生成完整报告** | §8 必备字段缺失 → 视为未验证 |
| 7 | **survival case 保护贯穿** | survival_case_preservation ≥ 0.80 是硬 gate |
| 8 | **没有 partial-pass 出口** | overall_status 二选一；防止"差一点没过" 蒙混进入 3R-7 |

---

## 14. 下一步建议

按推荐优先级：

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **Step 3R-4 checkpoint** | 把本文协议固化进 checkpoint；冻结 3-fold + 6 metric + 7 gate threshold + 10 项 no-go | **本轮 / 下一轮** |
| 2 | **Step 2G-8D** extend replay coverage（2024-08 → 2025-12） | 数据层；为 W4 准备；与 Step 3R 解耦可并行；不触碰 2026 | **高** |
| 3 | **Step 3R-2** read-only regime label diagnostics helper | 新增 `services/regime_labels_builder.py` + tests + dashboard 字段；**仅在 3R-4 checkpoint 完成后**启动；首个动代码步 | 中 |
| 4 | **Step 3R-3** continuous smoothing candidate | read-only simulator design；**仅在 3R-2 完成后**启动 | 中 |
| 5 | **不推荐**直接进入 3R-5 formula design | 必须先过 3R-2 / 3R-3 在本协议下出报告 | **❌** |
| 6 | **不推荐**直接 3R-6 read-only simulator | 必须先过 3R-5 design | **❌** |
| 7 | **不推荐** R4 hard implementation | Step 2G-8 / 8B / 8C 三重 NO-GO | **❌** |
| 8 | **不推荐**让 `_PROTECTION_LAYER_CONNECTED` 翻 True / Gate 5 / Gate 6 自动 pass | 与 Step 3R-0 / Step 2G-8A v1 一致 | **❌** |
| 9 | **不推荐**升级 04 required schema | Step 2G 全程边界 | **❌** |
| 10 | **不推荐**触碰 2026 final test range | 永久封禁 | **❌** |

**关键判断**：
- 顺序 = 本 3R-4 design → 3R-4 checkpoint → 3R-2 helper → 3R-3
  smoothing → 3R-5 formula → 3R-6 simulator → 3R-7 sidecar
- 任意一步在本协议下 fail → 整个 Step 3R 进入 NO-GO，Step 2G display
  路线为系统最终形态
- Step 2G-8D 与 Step 3R 系列**解耦可并行**

---

## 15. 严守边界

本文是**纯 design markdown**：

- ❌ 没改任何代码（`services/*` / `ui/*` / `tests/*` 全部未触碰）
- ❌ 没改 DB schema
- ❌ 没写 DB
- ❌ 没改 `run_predict` / `predict.py` / `scanner.py` /
  `prediction_store.py` / `app.py`
- ❌ 没改 `services/regime_features_builder.py` /
  `services/regime_diagnostics_dashboard.py` /
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
- ❌ 没运行 `pytest`（本轮纯文档；测试基线维持 commit `8d4fe8f` 时
  的 2604 / 0 failed / 10 skipped）
- ✅ 只新增 1 份 markdown design 文档（本文件）
