# Step 3R-3 — Continuous Smoothing Candidate Design

> **设计文档（continuous smoothing candidate design），不实现，不改代码，不写 DB，不运行 replay。**
> 本文档**冻结** Step 3R-3 第一个 continuous smoothing candidate 的：
> 立项动机（4×4 lookup 双重 fail 教训）、目标（不是 hard exclusion）、
> 输入特征（基于 Step 3R-1 `regime_labels.v1` raw_features）、smoothing
> 形状（sigmoid + 连续系数 shape）、`continuous_smoothing_candidate.v1`
> 输出 schema 草案、risk_bucket 草案、validation records 转换路径、
> 与 R4 / hard / required / 2026 final test range 的衔接边界、validation
> plan 子步骤、风险与禁止事项。
>
> 本轮**不动任何代码**：不改 `predict.py` / `run_predict` /
> `scanner.py` / `prediction_store.py` / `app.py` / 任何 `ui/*` /
> `services/*`（含 `services/regime_labels_builder.py` /
> `services/regime_validation_helper.py`）/ `scripts/*` / 任何 builder /
> DB schema / 任何 test 中的任何一处。
>
> **本文不实现 candidate 公式、不选系数、不选 candidate_threshold、
> 不跑 validation、不读 W4 results、不写 DB、不接 trading API**；只在
> markdown 层冻结 candidate 设计形状，给后续 3R-3 checkpoint / 3R-3.1
> 实施 / 3R-4.3 adapter 提供边界。

---

## 1. 背景

| 节点 | 状态 | 关键证据 |
|---|---|---|
| **Step 3B-1** 4×4 lookup holdout | **❌ FAIL** | 在 W1↔W2 双向 holdout 上 6 项标准只过 2 项；monotonicity / R4 触发 / probability calibration / robustness 全 FAIL |
| **Step 3A-4** 第三窗口扩 380 records | ⚠ **partial FAIL** | Method A 改善（calibrated_high acc 0.333 → 0.611），但 Method B 仍崩；Step 3 离散桶路线**双重失败** |
| **Step 2G-8C** R4 H1/H2 holdout gap | **regime-shift NO-GO** | first_half FER 0.24 vs second_half FER 0.41，gap +0.18，由 **regime shift + R4 regime-agnostic + 2024-02 单月异常** 三层叠加；`Step 2G 范围内不可解` |
| **Step 3R-1** regime label design | ✅ 已 merge（`a8df93a` / `8d4fe8f`） | 5 v1 label + 9 raw_feature；`regime_labels.v1` schema；8 项 anti-lookahead 不变量 |
| **Step 3R-2** read-only labels builder | ✅ 已 merge（`e2a681b` / `db7618b`） | `build_regime_labels(...)` 纯 read-only；38 focused tests |
| **Step 3R-4** cross-window protocol | ✅ 已 merge（`a58aad4` / `abe3ba2`） | 6 metric + 7 gate threshold + 10 no-go + `regime_validation_report.v1` schema |
| **Step 2G-8D** W4 full replay | ✅ 已 merge（`170617c` ... `4bdd782`） | W4 = 2024-08-03 → 2025-12-31；paired_outcomes=353；`final_test_touched=false` |
| **Step 3R-4.1 / 3R-4.2** 4-fold helper | ✅ 已 merge（`8e27254` / `295ccdd` / `c669c2f` / `5e58fee`） | `build_regime_validation_report(...)` + W4 manifest gate；R4-like fixture acceptance fail |

→ 旧 4×4 lookup **双重失败**；R4 在 2G 范围内**结构性 NO-GO**；
labels 数据层 + validation 评分层都已就绪。本文设计 Step 3R-3 第一个
continuous smoothing candidate，**不实现**。

---

## 2. 为什么不用旧 4×4 lookup

| # | 问题 | 证据 |
|---|---|---|
| 1 | **离散 bucket 边界容易跳变** | pos20 = 0.349 vs 0.351 落入相邻桶但 cell 估计可能差异巨大（small-sample noise） |
| 2 | **样本少时 bucket 噪声大** | 250 records / 4×4 = 平均每 cell ~ 16 paired，多个 cell paired ≤ 5；Step 3B-1 holdout fail 主因 |
| 3 | **无法平滑处理 pos20 / `avgo_minus_soxx_20d` 连续变化** | 真实风险信号是连续的，离散桶强行截断 |
| 4 | **对 sustained bull regime 适应差** | Step 2G-8C：H1 vs H2 同一桶下命中率系统性不同 |
| 5 | **holdout fail 说明它不稳** | Step 3B-1 双向 holdout 6 项只过 2 项 |
| 6 | **Step 3A-4 数据扩到 380 records 仍 partial fail** | 加数据**不能解决** lookup 结构性问题 |
| 7 | **Step 2G-8C narrower R4 candidate 0/42 通过** | 任何离散切片都无法在跨窗口同时 fer ≤ 0.10 + paired ≥ 30 |

→ 必须**离开离散桶路线**；改用**连续 smoothing**。

---

## 3. Candidate 目标

| 目标 | 说明 |
|---|---|
| **不是直接 hard exclusion** | candidate **不**驱动 `hard` / `forced_exclusion` / `anti_false_exclusion_triggered`；与 v1 / 3R-0 / 3R-4 一致 |
| **不是直接 formula implementation** | 本文是 candidate design **shape**，不写公式；3R-3.1 才实现 read-only generator |
| **是一个 candidate scoring layer** | 输出 continuous `risk_score` ∈ [0, 1]（sigmoid 输出域）和 `adjustment_score`（建议 `1 - risk_score` 或独立量） |
| **输出 continuous risk_score / adjustment_score** | 用于交给 3R-4.2 helper 的 records 字段（candidate_triggered = risk_score >= threshold） |
| **未来由 3R-4.2 helper 验证** | 通过 `build_regime_validation_report` 出 `regime_validation_report.v1` |
| **通过后也只进入 sidecar review** | report `pass` ≠ production permission；与 3R-4.1 §11 / 3R-4.2 §12 一致 |
| **不自动改主链** | 不改 `predict.py` / `run_predict` / `scanner` / `prediction_store` / 04 / 05 / 07 required |

---

## 4. 输入特征

基于 Step 3R-1 `regime_labels.v1` raw_features（**v1 不引入新字段**）：

| 特征 | 来源 | 单位 |
|---|---|---|
| `pos20` | `regime_labels.v1.raw_features.pos20` | decimal `[0, 1]` |
| `avgo_minus_soxx_20d` | `regime_labels.v1.raw_features.avgo_minus_soxx_20d` | decimal fraction |
| `peer_confirm_count` | `regime_labels.v1.raw_features.peer_confirm_count` | int 0..3 |
| `peer_5d_aligned_pct` | `regime_labels.v1.raw_features.peer_5d_aligned_pct` | decimal `[0, 1]` |
| `qqq_60d_slope_per_month` | `regime_labels.v1.raw_features.qqq_60d_slope_per_month` | decimal/月 |
| `qqq_60d_drawdown` | `regime_labels.v1.raw_features.qqq_60d_drawdown` | decimal `[0, 1]` |
| `soxx_60d_slope_per_month` | `regime_labels.v1.raw_features.soxx_60d_slope_per_month` | decimal/月 |
| `monthly_return_pct` | `regime_labels.v1.raw_features.monthly_return_pct` | decimal |
| `monthly_max_abs_daily_return` | `regime_labels.v1.raw_features.monthly_max_abs_daily_return` | decimal |

### 4.1 v1 不引入

| 不引入 | 理由 |
|---|---|
| **earnings calendar 字段** | v1 已通过 `monthly_context_regime` 的 `earnings_month` bucket 间接表达；不重复编码 |
| **2026 data** | 永久封禁；`final_test_cutoff` hard stop |
| **outcome leakage 字段**（`actual_*` / `direction_correct` / `review_*`） | 与 3R-1 §7 / 3R-2 §7 anti-lookahead 8 项不变量一致 |
| **scan / match / encoder 内部字段** | 与 Step 2G "sidecar-only" 边界一致；3R-3 不进入 hard 决策层 |
| **production wiring 字段**（`hard` / `forced_exclusion` / required） | 永远不在 candidate 层引入 |

---

## 5. smoothing 思路

设计一种**简单连续函数 shape**，**不实现**：

```
risk_score = sigmoid(
    a * pos20
  + b * avgo_minus_soxx_20d
  - c * peer_5d_aligned_pct
  - d * market_trend_strength
  + e * monthly_shock
)
```

### 5.1 各项方向（含 sign 解释）

| 项 | 方向 | 解释 |
|---|---|---|
| `+ a * pos20` | 正向 | pos20 越高（越接近 20-day 高点），bullish overextension 风险越高 |
| `+ b * avgo_minus_soxx_20d` | 正向 | AVGO 跑赢 SOXX 越多，relative-strength 拉伸越大，mean-reversion 风险越高 |
| `- c * peer_5d_aligned_pct` | 负向 | peer 同向越强（NVDA / SOXX / QQQ 5d 共同上涨），sustained-momentum 越确认，**风险下降** |
| `- d * market_trend_strength` | 负向 | sustained bull regime（QQQ slope > 0 + 低 drawdown）越强，**风险下降**（与 Step 2G-8C 教训一致：bull regime 救活 R4 触发） |
| `+ e * monthly_shock` | 正向 | shock month / breakout month 不确定性高，风险加成 |

### 5.2 系数与阈值的强约束

| 强约束 | 状态 |
|---|---|
| **`a` / `b` / `c` / `d` / `e` 不在本文调参** | ✅；本文只锁 shape；未来 3R-3.1 read-only generator 才会引入 |
| **`a` / `b` / `c` / `d` / `e` 不允许通过 W4 数据回头调** | ✅；与 Step 3R-4 §6.1 / 3R-4 checkpoint §6 一致——任何用 validation 数据调阈值 = 偷跑 |
| **不允许 sigmoid 退化为 4×4 lookup**（即不允许把 `a` / `b` 等参数学成离散桶门限） | ✅；shape 必须连续 |
| **不允许引入 hidden lookup table** | ✅；coefficients 是 candidate 公开 schema 一部分 |
| **不允许 candidate 触碰 outcome 字段调参** | ✅；anti-lookahead |
| **不允许 candidate 触碰 2026 数据调参** | ✅；final-test cutoff |
| **不允许只看 pooled result 来调参** | ✅；与 3R-4 §4.2 / 3R-4.2 §8.3 一致 |

→ 后续任何 candidate variant **必须**通过 Step 3R-4.2 helper 在 4-fold
协议下出 `regime_validation_report.v1` 才算 candidate eligible。

---

## 6. `market_trend_strength` 定义草案

`market_trend_strength` 是 §5 sigmoid 中 `- d *` 项的输入，用 4 段
连续/分段函数构造：

| 段 | 触发条件 | 草案值 |
|---|---|---|
| **strong_bull** | `qqq_60d_slope_per_month > 0.015` ∧ `soxx_60d_slope_per_month > 0.015` ∧ `qqq_60d_drawdown < 0.05` | 1.0 |
| **bull** | `qqq_60d_slope_per_month > 0.01` 或 `soxx_60d_slope_per_month > 0.01`（任一） | 0.6 |
| **weak** | `qqq_60d_drawdown > 0.10` 或 `qqq_60d_slope_per_month < -0.005` 与 `soxx_60d_slope_per_month < -0.005` 同时 | -0.6 |
| **neutral** | 其它 | 0.0 |

| 强约束 | 状态 |
|---|---|
| **当前只是 shape**，不在本文验证 | ✅ |
| 阈值（`> 0.015` / `< 0.05` / `> 0.10` 等）**不在本文调** | ✅ |
| 未来 candidate variants 可换为 logistic / kernel / spline；本文不绑定具体函数族 | ✅ |
| `market_trend_strength` 输出 ∈ [-1, 1]（草案；可在 3R-3.1 时 fix） | ✅ |
| `monthly_shock` 项（§5）由 `monthly_context_regime` ∈ `{shock, breakout}` 转 indicator + 缩放 `monthly_max_abs_daily_return` | ✅；同样 shape only |

---

## 7. Candidate output schema 草案

```json
{
  "schema_version": "continuous_smoothing_candidate.v1",
  "as_of_date": "YYYY-MM-DD",
  "data_cutoff_date": "YYYY-MM-DD",
  "candidate_name": "continuous_smoothing_v1",
  "risk_score": 0.42,
  "adjustment_score": 0.58,
  "risk_bucket": "low | medium | high | extreme",
  "features_used": {
    "pos20": 0.81,
    "avgo_minus_soxx_20d": 0.077,
    "peer_5d_aligned_pct": 0.40,
    "market_trend_strength": 0.6,
    "monthly_shock": 0.0
  },
  "warnings": [],
  "final_test_refusal": false
}
```

### 7.1 schema 不变量

| 字段 | 不变量 |
|---|---|
| `schema_version` | 总是 `"continuous_smoothing_candidate.v1"` |
| `as_of_date` | ISO 8601；**`< final_test_cutoff`** 硬不变量 |
| `data_cutoff_date` | `== as_of_date` |
| `candidate_name` | string；`"continuous_smoothing_v1"`（v1） |
| `risk_score` | float ∈ [0, 1]；sigmoid 输出域 |
| `adjustment_score` | float ∈ [0, 1]；建议 `1 - risk_score`（v1）；可在 3R-3.1 时 fix |
| `risk_bucket` | enum：`low / medium / high / extreme`；详见 §8 |
| `features_used` | dict；本次 candidate 计算实际用到的 raw_features（来自 3R-2 helper 输出） |
| `warnings` | list of string；可空 |
| `final_test_refusal` | bool；`as_of_date >= 2026-01-01` 强制 `True` |

### 7.2 candidate output 不允许的字段

| 禁止字段 | 理由 |
|---|---|
| `overall_status` / `gate_status` / `validation_passed` | candidate 是数据层；validation 由 3R-4.2 helper 产出 `regime_validation_report.v1` |
| `hard_exclusion_allowed` / `forced_exclusion` / `anti_false_exclusion_triggered` | candidate 永不直接驱动 hard 路径 |
| `simulated_trade` / `no_trade` / `final_direction` / `final_projection` | 与 v1 / 3R-0 / 3R-4 一致 |
| `regime_validation_report.v1` 字段 | candidate 不预判 validation 结果 |

---

## 8. risk_bucket 草案

| bucket | 范围 |
|---|---|
| `low` | `risk_score < 0.35` |
| `medium` | `0.35 <= risk_score < 0.60` |
| `high` | `0.60 <= risk_score < 0.80` |
| `extreme` | `risk_score >= 0.80` |

### 8.1 强约束

| 强约束 | 状态 |
|---|---|
| **bucket 只是 display / diagnostics** | ✅；不是 hard exclusion 信号 |
| **bucket thresholds 未验证**（与 3R-1 §5 v1 阈值同样性质） | ✅；3R-3.1 实施前不视为 production rule |
| bucket 不进入 4-fold gate 决策（gate 只看 metrics） | ✅ |
| bucket 可在未来 candidate variant 微调；调动必须经 launch review | ✅ |
| 阈值不允许用 W4 / final test 数据反推 | ✅ |

---

## 9. 如何转换成 validation records

为了把 candidate 输出**喂给** Step 3R-4.2 helper（接受 `records`
list），未来 adapter（Step 3R-4.3）需要把 candidate output + 现有
replay records 组装成如下字段：

| 字段 | 来源 |
|---|---|
| `analysis_date` | replay record 中的 `analysis_date`（即 candidate 的 `as_of_date`） |
| `candidate_triggered` | `risk_score >= candidate_threshold`（默认 candidate_threshold = 0.60，即 `risk_bucket ∈ {high, extreme}`） |
| `exclusion_would_block` | `candidate_triggered`（v1：candidate 触发即视为会 block）|
| `survival_case` | `candidate_triggered ∧ prediction_correct`（即 candidate 触发但预测正确） |
| `baseline_correct` | replay record 中 `direction_correct == 1`（baseline = 不应用 candidate 的原 prediction） |
| `prediction_correct` | replay record 中 `direction_correct == 1` |
| `prediction_for_date` | replay record 中 `prediction_for_date` |
| `actual_direction` | replay record 中 `actual_direction`（optional） |

### 9.1 强约束

| 强约束 | 状态 |
|---|---|
| **`candidate_threshold` 不能在本文调** | ✅；本文只设计 shape |
| **`candidate_threshold` 必须在 Step 3R-4.2 helper 下验证** | ✅；任何 candidate_threshold variant 都必须出独立 `regime_validation_report.v1` |
| **不允许只看 pooled result** | ✅；与 3R-4.2 §8.3 一致；worst-window 决胜 |
| **不允许把 `candidate_threshold` 学成 4 × 4 cell 边界** | ✅；shape 必须连续 |
| **adapter 不允许读 outcome 在 candidate decision 时已知的字段做 future leak** | ✅；anti-lookahead |
| **adapter 不允许读 2026 行** | ✅；与 helper 启动 gate 一致 |

---

## 10. 与 R4 的关系

| 维度 | R4 | continuous smoothing candidate |
|---|---|---|
| 形态 | 离散 soft metadata risk signal（`avgo_minus_soxx_20d > 5 ∧ pos20 > 0.62 ∧ bullish ∧ high-conf`） | 连续 sigmoid 在 9 raw_feature 上 |
| 是否 hard | ❌（v1 sidecar） | ❌（v1 sidecar） |
| 是否含 regime guard | ❌ | ✅（`market_trend_strength` 作为 sigmoid 输入） |
| 是否解 H1/H2 gap | ❌（Step 2G-8C 已证 R4 regime-agnostic） | **目标尝试**：通过 `- d * market_trend_strength` 让 sustained bull regime 期间 risk_score 系统性下降 |

### 10.1 与 R4 关系的强约束

| 强约束 | 状态 |
|---|---|
| **smoothing candidate 不是 R4 的硬化** | ✅；与 v1 / 3R-0 / 3R-4 一致 |
| **smoothing candidate 用连续特征**降低 R4 的 bucket cliff | ✅ |
| **必须首先证明能复现/改善 R4 fail**（在 3R-4.2 helper 下，用 R4-like fixture / 真实 W1-W4 records 跑） | ✅；这是 candidate eligibility 的第一个 acceptance |
| **若不能改善 R4，在 3R-4.2 下仍 fail** | ✅；helper `overall_status="fail"` → candidate 报废 |
| **R4 的 hard 实施仍 NO-GO** | ✅；与 Step 2G-8 / 8B / 8C 三重 NO-GO 一致 |

---

## 11. 与 hard / required 的关系

| 维度 | continuous smoothing candidate |
|---|---|
| **candidate `risk_score >= threshold` 是否自动启 `hard`** | **❌ 否** |
| **是否自动改 04 / 05 / 07 required** | **❌ 否** |
| **是否进 main DB**（`prediction_log` / `outcome_log` / `review_log`） | **❌ 否** |
| **是否改 `final_direction` / `final_projection` / `simulated_trade` / `no_trade` / `confidence_system`** | **❌ 否** |
| **report `overall_status="pass"` 唯一允许的下游** | **进入下一步 design review** |
| **是否驱动 `_PROTECTION_LAYER_CONNECTED` 翻 True** | **❌ 否** |
| **是否让 Gate 5 / Gate 6 自动 pass** | **❌ 否** |
| **是否驱动 `hard_exclusion_allowed` / `primary_blocker` 派生** | **❌ 否** |

→ candidate 全部用途是产出**结构化判断**；production wiring 永远是
独立 step，且必须经 launch review。

---

## 12. Validation plan

| # | 子步骤 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **Step 3R-3 checkpoint** | 把本 design 状态固化进 main；锁定 shape / schema / validation plan | **本轮 / 下一轮** |
| 2 | **Step 3R-3.1 read-only candidate generator design / implementation** | 新增 `services/continuous_smoothing_candidate.py`（命名待定）；纯 read-only；输入 `regime_labels.v1` raw_features；输出 `continuous_smoothing_candidate.v1` dict；与 3R-2 helper 同等 isolation；focused tests | 中（在 3R-3 checkpoint 进 main 后启动） |
| 3 | **Step 3R-4.3 real replay record adapter design** | 设计如何把 W1/W2/W3 + W4 jsonl + candidate output 组装成 3R-4.2 helper 接受的 `records` list；纯 markdown 先行 | 中（与 3R-3.1 解耦可并行） |
| 4 | **Step 3R-3.3 4-fold validation run** | 用 3R-3.1 candidate output → 3R-4.3 adapter → 3R-4.2 helper 跑出 `regime_validation_report.v1` | 中（前两步完成后） |

### 12.1 success criteria（candidate eligibility）

| # | 标准 | 来源 |
|---|---|---|
| 1 | **all 7 gates pass** | 3R-4.2 §7（含 `minimum_window_sample_size >= 20` / `false_exclusion_rate <= 0.10` / `net_benefit >= +0.05` / `cross_window_variance <= 0.10` / `no_single_window_collapse` / `survival_case_preservation >= 0.80` / `accuracy_delta_vs_baseline >= +0.02`） |
| 2 | **worst-window pass**（每个 fold 的 held-out window 单独 pass） | 3R-4.2 §8 |
| 3 | **`survival_case_preservation >= 0.80`** | 3R-4.2 §7 |
| 4 | **`final_test_refusal=false`** | 3R-4.2 §5 |
| 5 | **no 2026 data 触碰** | manifest gate + record-level cutoff 双重 hard stop |
| 6 | **W4 manifest gate 通过**（require_w4_manifest=True） | 3R-4.2 §5 |
| 7 | **不允许 candidate `risk_score`、`candidate_threshold`、`market_trend_strength` 阈值用 4-fold validation 数据反推** | 与 3R-4 §6.1 一致 |

任一不满足 → candidate 报废；不允许"差一点没过"放松阈值。

---

## 13. Risks

| # | 风险 | 应对 |
|---|---|---|
| 1 | **sigmoid shape 仍可能 overfit** | 4-fold + worst-window 决胜规则强制；任何 fold fail 即 candidate fail |
| 2 | **coefficients 可能成为 hidden lookup table**（即 `a` / `b` / `c` / `d` / `e` 学成离散桶门限） | 必须在 3R-3.1 实施时锁定 coefficients 是 candidate 公开 schema 一部分；不允许 lookup 表替代 |
| 3 | **`monthly_context` 可能编码 hindsight** | strict-causal monthly derive（与 3R-1 §7 / 3R-2 §7 一致）；3R-3.1 实施时必须从 3R-2 helper 输出读取，不重新算 |
| 4 | **`candidate_threshold` 可能 overfit** | candidate_threshold 不允许用 4-fold validation 数据反推；调动必须经 launch review |
| 5 | **W4 may reveal more failure** | 这正是 4-fold 的意义；W4 暴露 candidate 在 2024-08+ regime 下的失稳 |
| 6 | **candidate 可能降低 false_exclusion 但拉低 net_benefit** | gate 同时检查两者；`accuracy_delta_vs_baseline` 兜底 |
| 7 | **candidate 可能在 small-sample window（W3 ~ 56 paired）上 minimum_window_sample_size 不够** | 与 3R-4 §6 / 3R-4.2 §7 阈值一致：`>= 20` per-fold；W3 paired 56 高于阈值，但 candidate 触发率可能让 blocked < 20 |
| 8 | **W4 sustained AI bull regime 与 W1-W3 不同**，candidate 系数需更新 | 必须在 3R-3.1 实施时锁定**单一 candidate variant**；任何 variant 调整都是新 candidate，独立 4-fold 验证 |
| 9 | **`market_trend_strength` 阈值（0.015 / 0.05 / 0.10）可能 overfit** | 与 3R-1 §5 v1 阈值同样 design-only；3R-3.1 实施时锁定来源；调阈值必须经 launch review |

---

## 14. 当前禁止事项

| # | 禁止 | 理由 |
|---|---|---|
| 1 | **不实现 formula** | 本文是 design 形状；3R-3.1 实施 |
| 2 | **不选 coefficients**（`a` / `b` / `c` / `d` / `e`） | 同上 |
| 3 | **不选 candidate_threshold** | 同上；`candidate_threshold` 必须在 3R-4.2 helper 下验证 |
| 4 | **不选 `market_trend_strength` 段阈值** | 同上 |
| 5 | **不选 `risk_bucket` 阈值**（0.35 / 0.60 / 0.80） | 同上 |
| 6 | **不跑 validation** | 3R-4.2 helper 由 3R-3.3 调用 |
| 7 | **不读 W4 results** | 本 design 不读 W4 输出；3R-4.3 adapter 才读 |
| 8 | **不写 DB** | candidate 是 read-only artifact |
| 9 | **不改 production decision**（`final_direction` / `final_projection` / `simulated_trade` / `no_trade` / `confidence_system`） | 与 v1 / 3R-0 / 3R-4 一致 |
| 10 | **不启 hard / forced / anti_false_exclusion_triggered** | 三重 NO-GO（2G-8 / 8B / 8C） |
| 11 | **不碰 2026** | 永久封禁；G1 + G2 + 3R-4.2 manifest gate 三重 hard stop |
| 12 | **不接 trading**（`longbridge` / `broker` / `paper_trade`） | 永不 |
| 13 | **不接 yfinance / 网络** | candidate 只读 caller-injected 数据 |
| 14 | **不让 `_PROTECTION_LAYER_CONNECTED` 翻 True** | 与 v1 / 3R-0 / 3R-4 一致 |
| 15 | **不让 `hard_gate_status.protection_layer_connected` 自动 pass** | 同上 |
| 16 | **不改 `hard_exclusion_allowed` / `primary_blocker` 派生** | 同上 |
| 17 | **不升级 04 / 05 / 07 required** | Step 2G 全程边界 |
| 18 | **不改 3R-4 protocol thresholds**（6 metric / 7 gate） | 阈值调整必须经 launch review |
| 19 | **不改 3R-2 helper 行为** | 仅 read-only 调用其输出 |
| 20 | **不改 3R-4.2 helper 行为** | 仅 read-only 调用其评分 |
| 21 | **不预选 candidate variants** | 本文锁 v1 shape；后续 variant 各自独立 4-fold 验证 |
| 22 | **不引入 hidden lookup table** | 与 §5.2 一致 |
| 23 | **不让 candidate output 包含 `gate_status` / `validation_passed` / `overall_status`** | candidate 是数据层；validation 由 3R-4.2 helper 输出 |

---

## 15. 下一步建议

按推荐优先级：

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **commit 本 design** | 把 §1-16 candidate shape / schema / validation plan 固化到 main | **本轮 / 下一轮** |
| 2 | **Step 3R-3 checkpoint** | 状态归档；锁定 shape / schema / validation plan | **下一轮**（commit 本 design 后） |
| 3 | **Step 3R-3.1 read-only candidate generator design / implementation** | 新增 `services/continuous_smoothing_candidate.py`（命名待定）；纯 read-only；输入 `regime_labels.v1` raw_features；输出 `continuous_smoothing_candidate.v1`；与 3R-2 helper 同等 isolation；focused tests | 中（在 3R-3 checkpoint 进 main 后） |
| 4 | **Step 3R-4.3 real replay record adapter design / implementation** | 把 W1/W2/W3 + W4 jsonl + candidate output 组装成 3R-4.2 helper 接受的 `records`；纯 wrapper / adapter | 中（与 3R-3.1 解耦可并行） |
| 5 | **Step 3R-3.3 4-fold validation run** | 用 3R-3.1 + 3R-4.3 + 3R-4.2 出 `regime_validation_report.v1` | 中（3R-3.1 + 3R-4.3 完成后） |
| 6 | **不推荐**直接 Step 3R-5 formula design | 必须先过 3R-3.3 实测 + 4-fold acceptance | **❌** |
| 7 | **不推荐** Step 3R-6 read-only simulator | 必须先过 3R-5 design | **❌** |
| 8 | **不推荐**让 candidate `pass` 自动启 hard / Gate 5 / Gate 6 | 与 §11 一致 | **❌** |
| 9 | **不推荐** R4 hard implementation | 三重 NO-GO 已锁定 | **❌** |
| 10 | **不推荐** 升级 04 required | Step 2G 全程边界 | **❌** |
| 11 | **不推荐** 触碰 2026 final test range | 永久封禁 | **❌** |
| 12 | **不推荐**让 `_PROTECTION_LAYER_CONNECTED` 翻 True | 与 v1 / 3R-0 / 3R-4 一致 | **❌** |
| 13 | **不推荐**用 W4 / final test 数据反推 candidate / threshold 系数 | 阈值调整必须经 launch review；偷跑视为污染 | **❌** |
| 14 | **不推荐**预选多个 candidate variant | 一次只 commit 一个 candidate variant；每个 variant 独立 4-fold | **❌** |

**关键判断**：
- 顺序 = 本 design → 3R-3 checkpoint → 3R-3.1 generator + 3R-4.3
  adapter（可并行）→ 3R-3.3 validation run → 3R-5 formula → 3R-6
  simulator → 3R-7 sidecar
- 任何一步 fail → 整 candidate 报废，回到 design 层重新设计

---

## 16. 严守边界

本文是**纯 design markdown**：

- ❌ 没改任何代码（`services/*` / `ui/*` / `tests/*` / `scripts/*` 全部未触碰）
- ❌ 没改 DB schema
- ❌ 没写 DB
- ❌ 没运行 replay
- ❌ 没改 `run_predict` / `predict.py` / `scanner.py` /
  `prediction_store.py` / `app.py`
- ❌ 没改 `services/regime_features_builder.py` /
  `services/regime_labels_builder.py` /
  `services/regime_validation_helper.py` /
  `services/regime_diagnostics_dashboard.py` /
  `services/anti_false_exclusion_dashboard.py` /
  `services/soft_metadata_simulator.py` /
  `services/protection_layer_diagnostics.py` /
  `services/historical_replay_training.py` /
  `services/three_system_replay_audit.py` /
  `services/replay_record_wiring.py` /
  `services/projection_three_systems_renderer.py` /
  `services/outcome_capture.py` /
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
- ❌ 没改 Step 3R-4 protocol thresholds（6 metric / 7 gate / 10 no-go）
- ❌ 没改 Step 3R-2 helper 行为
- ❌ 没改 Step 3R-4.1 design / checkpoint
- ❌ 没改 Step 3R-4.2 helper 行为 / checkpoint
- ❌ 没改 Step 2G-8D / 8D.1A / 8D.2 / 8D.3 / 8D.4 文档或代码
- ❌ 没把 W4 / smoke 输出 commit 进 main
- ❌ 没读 W4 results（adapter 由 3R-4.3 实施）
- ❌ 没选 candidate 系数 / `candidate_threshold` / `market_trend_strength` 阈值 / `risk_bucket` 阈值
- ❌ 没运行 `pytest`（本轮纯文档；测试基线维持 commit `5e58fee` 时
  的 2722 / 0 failed / 10 skipped）
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` /
  `avgo_agent.db.backup_*`
- ✅ 只新增 1 份 markdown design 文档（本文件）
