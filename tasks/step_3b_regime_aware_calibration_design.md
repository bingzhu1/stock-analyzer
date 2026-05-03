# Step 3B — Regime-Aware Calibration Design

> 状态：基于 Step 3B-0 的 regime split diagnostics 起草 calibration 公式设计。**仅设计文档**，本步骤不改代码、不写 DB、不实现公式、不升级 05 score 字段、不引入新 module。设计核心：用 `avgo_pos_20d` 主轴 × `primary_score_raw` 做 4×4 lookup 校准；用 R4 复合签名做 directional downgrade rule；通过 cross-window holdout 验证；calibration 始终是**旁路**，不反写 final_direction / 不开 trading。
> 本文件只写文档，不改代码，不写 DB，不 commit，不 push。

## 1. 背景

| 步骤 | 主题 | 关键产出 | 状态 |
|---|---|---|---|
| Step 2F | 让 `calibration_ready=true`（130 → 250 paired ≥ 90） | DB baseline + duplicate guard + cap=130 | ✅ |
| Step 3A | 真实 calibration 诊断揭示 confidence / peer / soft_signal 反向 | accuracy 0.440, high < low, peer reinforce 反向 | ✅ commit `b1dcfcd` |
| Step 3A-2 | 阅码归因，排除 sign error / 语义错配 | 反向不是 code bug，是 regime 性 | ✅ commit `758ae87` |
| Step 3A-3 | 第二窗口 replay (2023-08..2024-01)，250 records / 193 paired | 反向缓解到消失（W2 pa=upgrade 0.558）；但 +15 ppts 偏多仍存 | ✅ commit `79b7266` |
| Step 3B-0 | regime split diagnostics 找 failure regime feature | bias 是 regime-bipolar（-36 → +47）；pos20 是最强轴；R4 失败签名 | ✅ commit `95ece7f` |
| **Step 3B（本文）** | **regime-aware calibration design doc** | **公式架构 / 4×4 lookup / R4 downgrade rule / holdout 验证计划** | **仅设计** |

**本文不实现公式**。实现下放到 Step 3B-1（holdout simulation，仍只读）→ Step 3B-2（sidecar schema 设计）→ Step 3B-3（read-only simulator）→ Step 3B-4（contract `extras` 暴露）→ Step 3C（顶层 score 字段升级）。

## 2. 为什么不能 simple calibration

**Simple calibration 定义**：把 `primary_score_raw`（或 `confidence_level`）单调映射到 probability，例如 `score >= 2 → prob 0.7`。

**为什么不行**：Step 3B-0 实测 bias 是 **regime-bipolar**（按 `avgo_pos_20d` 分桶）：
| pos20 quartile | pred 偏多 率 | actual up 率 | bias |
|---|---|---|---|
| Q1 (≤ 0.38, 底) | 0.22 | 0.58 | **-0.36** |
| Q2 (0.38-0.62) | 0.60 | 0.51 | +0.09 |
| Q3 (0.62-0.82) | 0.83 | 0.43 | **+0.40** |
| Q4 (> 0.82, 顶) | 0.98 | 0.51 | **+0.47** |

- Q1：模型过度偏空（应当看多更多）
- Q3/Q4：模型过度偏多（应当看空更多）
- 对**同样的 raw score**，在 Q1 应该提高看多概率，在 Q3/Q4 应该降低看多概率
- **simple monotonic mapping 是反方向单调**：raw_score 越大 → prob 越大；但 Q1 实际反而需要 raw_score 小时 prob 大、raw_score 大时 prob 小 —— **完全做不到**

**结论**：必须显式加入 regime 轴。Calibration 公式至少 2D（`primary_score_raw × regime_axis`），不能 1D。

## 3. Regime feature 冻结（基于现有 250 records）

### 3.1 主轴 `avgo_pos_20d`（必用）
- Q1 ≤ 0.38
- Q2 (0.38, 0.62]
- Q3 (0.62, 0.82]
- Q4 > 0.82

### 3.2 互补轴 `avgo_ret_20d`（可选 cross-check）
- Q1 ≤ -1.23%
- Q2 (-1.23%, +3.90%]
- Q3 (+3.90%, +11.93%]
- Q4 > +11.93%

### 3.3 R4 辅助轴 `avgo_minus_soxx_20d`（仅用于 directional downgrade rule）
- Q1 ≤ -1.37 pp
- Q2 (-1.37, +1.45 pp]
- Q3 (+1.45, +5.01 pp]
- Q4 > +5.01 pp

### 3.4 互补辅助 `avgo_minus_qqq_20d`（仅 cross-check，不进第一版公式）
- Q1 ≤ -0.93 pp
- Q2 (-0.93, +2.19 pp]
- Q3 (+2.19, +6.57 pp]
- Q4 > +6.57 pp

### 3.5 第一版公式只用主轴 + R4 辅助轴
**理由**：
- 现有 250 records 在 4×4 grid 下每格平均 ~16 records，已经接近统计噪声底线；再加一个 4-quartile 轴（变 4×4×4 = 64 cells）会让每格 ~4 records，全是噪声。
- 主轴 `pos20` 已捕捉 bipolar bias 的主要方向。
- 互补轴留给后续（Step 3B 第二版或 Step 3B-3）做 robustness check，不进第一版。

### 3.6 boundaries 重计算原则
**implementation 前必须重算并冻结**：当前 boundaries 是基于 250 records 的 quartile，如果未来加入第三窗口（Step 3A-4）或新 symbol（超出 AVGO 项目范围），必须重新拟合并在 docs 里更新；不能直接复用旧边界跑新数据。

## 4. 当前 confidence 的问题（calibration 必须解决的）

| 问题 | Step 3B-0 数据 |
|---|---|
| current `confidence_level` 是启发式标签 | `_confidence_from_score`: `abs(score) ≥ 2 → high`；不是 calibrated score |
| high 不普遍更准 | high 0.472 / medium 0.460 / low 0.595（low > high） |
| pos20 Q3 + high 是最差子集 | 19 paired, **accuracy 0.263** |
| high failure 集中在中高位动量延续场景 | pos20 Q3 + fd=偏多 + cl=high → up_acc 极低 |
| 05 required score 字段为 0.0 是 by design | Step 3A-2 阅码确认；Step 3C 才升 |
| `peer_adjusted_confidence == final_confidence == confidence_level` | 130 records 0 mismatch；**peer adjustment 已被 absorb 进 final，calibration 不需要再 split peer 维度** |

**Calibration 公式必须**：
1. **不动 `final_direction`**（CLAUDE.md 硬规则禁止改方向决策）；
2. **重映射 `confidence_level` / `probability_bucket`**，让 high → 真正"高准确率"子集；
3. **支持 downgrade**（high → medium / low）但不支持 upgrade（避免过拟合）；
4. **保留原始 `confidence_level` 在 contract 里**；calibrated 值放 `extras` 子段。

## 5. 设计目标

### 5.1 不变量（不能动）
- ❌ 不改 `final_direction`
- ❌ 不改 `final_five_state`
- ❌ 不改 04 exclusion required 字段
- ❌ 不改 07 simulated_trade 任何字段
- ❌ 不改 `predict.py` score 公式 / `scanner.py` / 任何硬规则层
- ❌ 不动 03 `peer_confirmation_adjustment` 顶层字段

### 5.2 第一版 calibration layer 的契约

**输入**：当前 contract payload 的部分字段：
- `confidence_system.extras.primary_score_raw`
- `confidence_system.confidence_level`
- `confidence_system.extras.probability_bucket`
- `final_projection.final_direction`
- `peer_confirmation_adjustment.peer_alignment` / `peer_adjustment`
- 外加从 coded_data 计算的 regime features：`avgo_pos_20d` / `avgo_minus_soxx_20d`（**只读 `Date <= D`**）

**输出**（仅旁路；不反写主链）：
- `calibrated_probability: float`（0..1）
- `calibrated_confidence_level: "high" | "medium" | "low"`
- `downgrade_reason: str | null`（"overextended_vs_soxx_high_position" / "high_mid_position_high_confidence_failure" / null）
- `calibration_regime: dict`（pos20 quartile / a-s_20d quartile / R4 hit flag）

### 5.3 旁路 vs 主链

第一版**严格旁路**：
- 计算结果只写到 `confidence_system.extras` 子段或新建一个 `calibration_extras` 子段；
- **不**改 contract `confidence_system.confidence_level`（required 字段保持原值）；
- **不**触发 exclusion；
- **不**升 `simulated_trade.score`；
- **不**写 04 / 05 / 07 顶层；
- 用户 / 下游若想用 calibrated 值，必须显式读 `extras`。

## 6. 4×4 Lookup Table 草案

### 6.1 表结构

| 维度 | bucket | 边界 |
|---|---|---|
| **Axis 1: `primary_score_raw`** | strong_bear | ≤ -2 |
|  | weak_bear | (-2, 0] |
|  | weak_bull | (0, +2] |
|  | strong_bull | > +2 |
| **Axis 2: `avgo_pos_20d`** | low | ≤ 0.38 |
|  | mid | (0.38, 0.62] |
|  | high_mid | (0.62, 0.82] |
|  | high | > 0.82 |

每格输出 5 项：

```
{
  "empirical_accuracy": float,      # paired correct / paired total（基于 holdout window）
  "empirical_up_rate": float,       # actual UP rate（不是 direction_correct）
  "sample_count": int,              # cell 中的 paired sample 数
  "calibrated_probability": float,  # 给定该 cell 的 D+1 UP probability（≈ empirical_up_rate）
  "calibrated_confidence_level": "high" | "medium" | "low",  # 重新分桶
  "suggested_action": "downgrade_high_to_medium" | "downgrade_high_to_low" | "hold" | "boost_low_to_medium"
}
```

### 6.2 cell 填充原则（不写实现，只写规则）

1. **`sample_count < 20` 的格子不单独决策** —— 回退策略：
   - 优先**沿主轴回退**（同 `pos20` quartile，相邻 score quartile 合并）；
   - 次选**沿 score 轴回退**（同 score quartile，相邻 pos20 quartile 合并）；
   - 兜底：**全局 baseline**（193 paired 的 actual_up_rate ≈ 0.508）；
2. **low pos20 (Q1) 子集**：模型过度偏空（pred_bull=0.22, actual_up=0.58）。Calibration 应**反向修正**：strong_bear cell 的 `calibrated_probability` 应**上调**到接近 actual_up_rate（≈ 0.55-0.60）；suggested_action = `boost_low_to_medium`（不是 high，避免反向过拟合）。
3. **high_mid pos20 (Q3) + bullish high confidence**：最差子集（acc 0.263）。Calibration 应**强 downgrade**：`calibrated_probability` ≈ 0.40-0.45；`calibrated_confidence_level = medium`（保守起步，不直接 → low，等 holdout 决定）。
4. **high pos20 (Q4) + bullish high confidence**：模型 pred_bull=0.98 但 actual_up=0.51；calibration `calibrated_probability ≈ 0.50`；`calibrated_confidence_level = medium`（不再"高把握看多"）。
5. **mid pos20 (Q2)**：bias 仅 +0.09，calibration 接近恒等（保留原 confidence_level）。
6. **不允许 calibration 把 medium / low → high**：第一版只 downgrade，不 upgrade（避免拟合噪声成"高把握"）。

### 6.3 cell 填值的具体来源（implementation 时）

**Step 3B-1（holdout simulation，仅只读 SQL + python）将做的事**：
- 在 design window 上聚合每个 cell 的 `paired count` / `correct count` / `actual_up count`；
- 计算 `empirical_accuracy = correct / paired`；
- 计算 `empirical_up_rate = actual_up / paired`；
- `calibrated_probability ≈ empirical_up_rate`（如果是预测偏多 cell，prob 该更接近 actual_up；如果是预测偏空 cell，需要倒置）；
- 记录 `sample_count`；
- 应用 6.2 回退规则填空 cell；
- 输出 16-cell table 到 stdout（不持久化）。

**Step 3B 本文档不计算实际值**；只冻结结构和填充规则。

## 7. R4 Downgrade Rule 草案

### 7.1 触发条件
```
IF avgo_minus_soxx_20d > +5 pp
   AND avgo_pos_20d > 0.62
   AND final_direction == "偏多"
   AND (confidence_level == "high" OR primary_score_raw > +2):
   → trigger R4 downgrade
```

### 7.2 R4 触发的实测 metric（Step 3B-0）
| 字段 | 值 |
|---|---|
| n | 40 |
| paired | 31 |
| accuracy | **0.419** |
| pred_bull | 0.94 |
| actual_up | 0.35 |
| **bias** | **+0.58** |
| `cl=high` 子集 acc | 0.400 |
| `pa_adj=upgrade` 子集 up_acc | **0.312** |

### 7.3 R4 downgrade 输出
```
calibrated_confidence_level = "medium"  # high → medium
calibrated_probability_bucket = "55-70%"  # ≥70% → 55-70%
downgrade_reason = "overextended_vs_soxx_high_position"
calibration_regime = {
    "rule": "R4",
    "avgo_minus_soxx_20d": <value>,
    "avgo_pos_20d": <value>,
    "primary_score_raw": <value>,
}
```

### 7.4 R4 不做的事
- ❌ 不改 `final_direction`（保持 "偏多"，只降 confidence）
- ❌ 不触发 exclusion（这是 Step 2G 的范畴）
- ❌ 不直接 → low（保守 → medium，避免过度修正）
- ❌ 不改 04 顶层 `exclusion_level`

## 8. Pos20 Q3 High-Confidence Rule 草案

### 8.1 触发条件
```
IF 0.62 < avgo_pos_20d ≤ 0.82
   AND confidence_level == "high"
   AND final_direction == "偏多":
   → trigger pos20_q3_high rule
```

### 8.2 实测 metric（Step 3B-0）
| 字段 | 值 |
|---|---|
| paired | 19 |
| accuracy | **0.263** |

### 8.3 输出
```
calibrated_confidence_level = "medium"  # 保守起步：high → medium，不直接 low
calibrated_probability_bucket = "55-70%"
downgrade_reason = "high_mid_position_high_confidence_failure"
calibration_regime = {
    "rule": "POS20_Q3_HIGH",
    "avgo_pos_20d": <value>,
    "primary_score_raw": <value>,
}
```

### 8.4 为什么保守用 medium 而不是 low

- 19 paired 是小样本（low CL 子集）；
- 直接 → low 等于"高置信看多 → 几乎无置信" 跨度太大；
- holdout 验证后，如果 cross-window 都重现 acc < 0.30，再考虑 → low；
- **第一版 design 倾向保守**：缩小 confidence range 而不是反向归零。

### 8.5 R4 与 Pos20 Q3 High Rule 的优先级
两条规则可能同时触发（R4 含 pos20 > 0.62，Q3 落在 0.62-0.82）。优先级：
1. **R4 优先**（更具体，含 a-s_20d 维度）→ `downgrade_reason = "overextended_vs_soxx_high_position"`
2. 如果 R4 不触发但 Pos20 Q3 High 触发 → `downgrade_reason = "high_mid_position_high_confidence_failure"`
3. 如果两条都不触发，仅按 4×4 lookup table 输出。

## 9. Holdout 验证计划

### 9.1 三个方案
| 方案 | design window | holdout window | 优 / 缺 |
|---|---|---|---|
| **A** | Window1 (2024-01-29 → 2024-08-02, 130 records) | Window2 (2023-08-07 → 2024-01-26, 120 records) | Window1 是 failure regime，design 时容易过拟合 mean reversion |
| **B** | Window2 (120 records) | Window1 (130 records) | Window2 acc 0.548 接近 random，design baseline 不过激；推荐起点 |
| **C** | combined 250 records，**leave-one-month-out** | 每月作为 holdout | 13 个月 × 13 次拟合 / 验证；最稳健，工作量大 |

### 9.2 推荐：先做方案 B，再补方案 C

**方案 B（首选）**：
- 在 Window2（acc 0.548）上拟合 4×4 lookup table；
- 在 Window1（acc 0.440）上 holdout，看 calibration 是否能把 Window1 high acc 从 0.431 推到 ≥ 0.50；
- 关键：**Window1 是 mean-reversion regime，calibration 必须显式 downgrade**；如果 design 在 Window2 学到的 cell 值在 Window1 直接套用就显著缓解 high failure，证明 regime-aware 公式有效。

**方案 C（补充 robustness）**：
- 13 个月 leave-one-month-out 验证；
- 输出 13 张表，看 calibration 性能是否在某些月份 collapse；
- 重点检查 2024-03 / 04 / 05（failure regime 月份）的 holdout 表现。

### 9.3 评估指标

| 指标 | 目标 |
|---|---|
| **calibrated confidence monotonicity** | calibrated high acc > calibrated medium acc > calibrated low acc（或至少 high ≥ low） |
| **R4 子集 up_acc** | 从 0.312 → ≥ 0.45（calibration 后） |
| **pos20 Q3 + cl=high 子集 acc** | 从 0.263 → ≥ 0.40 |
| **overall direction acc** | 不强求大幅提升（`final_direction` 不变）；目标 ≥ baseline 0.508 |
| **probability calibration** | 平均 `|calibrated_prob - actual_up_rate| ≤ 0.10` |
| **coverage** | calibrated cell 覆盖 ≥ 80% paired records；不能只对 R4 等 5% 子集生效 |
| **no direction change** | 校验 100% records 的 `final_direction` 没被改 |

### 9.4 失败 / 中止条件

如果 holdout 失败（任一指标不达标）：
- **不进 Step 3B-2**（sidecar schema）；
- 回到 Step 3A-4（第三窗口扩样本）或 Step 2G（exclusion 重审）；
- calibration design 标记 "regime-feature insufficient"，docs 留底；
- 不要"调参再试"—— 这会污染 cross-window holdout 的统计意义。

## 10. 不做什么（Step 3B 边界）

- ❌ 不改 `final_direction` / `final_five_state`
- ❌ 不改 `predict.py` score 公式
- ❌ 不改 scanner / matcher / encoder（CLAUDE.md 硬规则）
- ❌ 不启用 trading（`simulated_trade.trade_engine_enabled` 保持 False）
- ❌ 不写 05 required `historical_score` / `structure_score` / `peer_score` / `exclusion_penalty` / `event_score` 真值
- ❌ 不直接启用 exclusion hard（Step 2G 范畴；本设计明确 soft_signal != none **不应**升级 hard）
- ❌ 不把 `soft_signal != none` 当 hard warning（Step 3A-2 / 3A-3 已确认是 metadata）
- ❌ 不接 trading API / longbridge / broker / paper_trade
- ❌ 不接 yfinance / 网络
- ❌ 不写 Python module / 不动 tests / 不动 schema

## 11. 2006-01-01 最终测试集原则

> **用户明确要求**：2006-01-01 之后的数据作为系统**全部完成后的最终测试数据**，开发期间不能反复使用避免数据污染。

### 11.1 数据范围分层
| 层 | 范围 | 用途 | 当前已用 |
|---|---|---|---|
| **Development replay windows** | 2023-08-07 → 2024-08-02（当前 250 records） | Step 2F-3B 设计 / 诊断 / Holdout | ✅ |
| **Validation windows** | 2024-08 之后 + 2023-08 之前（**待划分**） | Step 3B-1 / 3B-3 holdout 之后的 robustness 验证 | ❌ |
| **Final test range** | 2006-01-01 之后**全量**（含 2008 / 2018 / 2020 / 2022 等不同 regime） | 系统全部完成后的最终验收 | ❌（保留） |

### 11.2 设计期约束
- **本步骤（Step 3B 设计）只用 development windows**；
- **Step 3B-1 holdout** 在 development windows 内做 within-sample / within-regime 验证；
- **Step 3B-2 之后引入 Validation windows**：选取 development windows **以外**的有限时间段做 out-of-sample 测试；
- **Step 3C 上线前必须做一次 Final test range 抽样**（比如 2010-2018 不重叠子段），但**不能反复抽样调参**；
- **不要用 final test range 做 grid search / hyperparameter tuning**；
- **不要把整个 2006-后数据当训练集**；
- **任何"复用 final test 子段调参"的请求，本设计文档明确禁止**。

### 11.3 设计选择倾向于 robust over fitting
- 第一版只用 1 个主轴 + 1 个辅助 R4 规则；
- 不用 vol10 / volume_ratio / NVDA 维度（避免过拟合）；
- cell 中 `sample_count < 20` 的回退到邻近桶 / 全局 baseline；
- holdout 评估 5 项指标，单项失败即视为不达标。

## 12. Implementation Roadmap

| 子步 | 主题 | 改动类型 | 当前 |
|---|---|---|---|
| **Step 3B（本文）** | regime-aware calibration design doc | 仅 docs | ✅（本轮） |
| Step 3B-1 | holdout simulation（read-only SQL + python，cell 填值 + 5 项指标计算） | 仅诊断脚本 inline，无落盘代码 | 待开 |
| Step 3B-2 | calibration sidecar schema design（`extras.calibration_*` 字段定义） | 仅 docs / 不写主链 | 待开 |
| Step 3B-3 | 实现 read-only `calibration_simulator.py`（参考 `summarize_confidence_calibration_inputs.py` 风格） | 新增 service + tests，不改 contract / predict / adapter | 待开 |
| Step 3B-4 | 如果 3B-1/3B-3 holdout 通过 → contract `confidence_system.extras` 暴露 `calibrated_probability` 等字段 | adapter 改动（小） + tests | 视 holdout |
| Step 3C | 升级 05 required `score` 字段到非零 | 改 adapter required field + 大量 tests | 视 3B-4 之后 |
| Step 2G | exclusion soft → hard 重审（独立路径） | 视 calibration 结论；当前建议**取消或重新设计** | 独立 |

## 13. 成功标准

第一版 calibration 公式视为"成功"需要在 holdout 上同时满足：

1. **calibrated bucket monotonicity**：calibrated `high` accuracy ≥ calibrated `medium` accuracy ≥ calibrated `low` accuracy（或至少 calibrated `high` ≥ calibrated `low`）；当前 raw confidence_level 是反向（high 0.472 < low 0.595），calibration 必须**至少打平**。
2. **R4 downgrade 后子集 up_acc 提升**：R4 触发的 31 paired 子集（当前 up_acc 0.312）经 calibration 后 ≥ 0.45；如果 calibration 不动 direction 但降级 confidence，那 calibrated_high 在 R4 子集应该接近空集 → R4 子集落入 calibrated_medium，medium 子集 acc 应 ≥ 0.45。
3. **probability calibration**：在 holdout 上，每个 cell 的 `mean(|calibrated_prob - empirical_up_rate|) ≤ 0.10`；avg deviation ≤ 0.05 视为 well-calibrated。
4. **direction unchanged**：100% records 的 `final_direction` 保持原值；calibration 没绕过这个约束。
5. **coverage**：calibrated cell 覆盖 ≥ 80% paired records；不能只对 R4 等 5% 子集生效。
6. **holdout robustness**：方案 B（W2 design / W1 holdout）+ 方案 C（leave-one-month-out）都不出现 monotonicity 反向；任意单月 calibrated_high acc ≥ 0.40。

如果**任一项不达标**：design 视为"还不够强"，不进 Step 3B-2。回 Step 3A-4 加第三窗口或重新评估 regime feature。

## 14. 严守边界（本轮已遵守）

- ❌ 没改任何代码（`predict.py` / `services/*.py` / `scripts/*.py` / `tests/*.py` / `scanner.py` / `confidence_engine` 0 字节变化）
- ❌ 没新增测试
- ❌ 没 commit / push
- ❌ 没写 DB
- ❌ 没改 DB schema
- ❌ 没改 `predict.py` / `scanner.py` / confidence_engine
- ❌ 没升级 contract 04 / 05 / 07 顶层字段
- ❌ 没实现 calibration formula（仅设计；§6 / §7 / §8 都是规则草案，无代码）
- ❌ 没写 Python module / 没建 service
- ❌ 没接 trading API / longbridge / broker / paper_trade
- ❌ 没接 yfinance / 网络
- ❌ 没用 final test range（2006-后 / 2010-2018 等）做任何调参
- ❌ 没保存 csv / 新脚本进仓库
- ❌ 没触碰 stash / .claude/worktrees/ / logs/prediction_log.jsonl
- ✅ 仅新增 1 个 markdown design doc
