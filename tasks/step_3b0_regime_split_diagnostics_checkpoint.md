# Step 3B-0 — Regime Split Diagnostics Checkpoint

> 状态：基于现有 250 条 cross-window replay 完成 read-only regime split diagnostics。**核心修正：Step 3A-3 报告的"结构性 +15 ppts 偏多"实际是 regime-bipolar bias 的算术平均**——模型在低位过度偏空（-36 ppts）、在中高/高位过度偏多（+47 ppts），跨度 83 ppts。**最强单一 regime 轴是 `avgo_pos_20d`**；最强复合失败签名是 R4（`avgo_minus_soxx_20d > 5pp AND pos20 > 0.62`，up_acc 0.312）；**最干净 high-confidence 失败子集是 `pos20 Q3 + cl=high`，acc 仅 0.263**。建议进入 Step 3B regime-aware calibration design（仅 docs），不能直接写代码、不能升级 05 score 字段、不能用 simple calibration。
> 本文件只写文档，不改代码，不写 DB，不 commit，不 push。

## 1. 当前完成状态

| 子步 | 主题 | 状态 |
|---|---|---|
| Step 3A-3 | 第二窗口 replay 写入 + cross-regime 验证 | ✅ commit `79b7266` |
| **Step 3B-0** | **regime split diagnostics（read-only 250 条切片）** | ✅（本文件 checkpoint） |
| Step 3B | regime-aware calibration design doc（仅 docs） | 待开（推荐下一轮） |
| Step 3B-1 | calibration formula dry-run（仅 docs + holdout 计算） | 待开 |
| Step 3C | 写入 05 score 字段 | 暂缓，最末位 |

## 2. 当前数据基线

| 字段 | 值 |
|---|---|
| `valid_payloads` | 250 |
| `paired_outcomes` | 193 |
| `pending_outcomes` | 57 |
| `calibration_ready` | True |
| `missing_dimensions` | `[]` |
| `analysis_date` 范围 | 2023-08-07 → 2024-08-02 |
| Window1 | 130 records (2024-01-29 → 2024-08-02) |
| Window2 | 120 records (2023-08-07 → 2024-01-26) |

本轮 0 代码改动 / 0 测试改动 / 0 DB 写入 / 0 schema 改动。

## 3. 核心修正：偏多不是常量，而是 regime-bipolar

> **Step 3A-3 报告**：跨两个窗口 long bias 都 ≈ +15 ppts，结论"结构性"。
> **Step 3B-0 修正**：+15 ppts 是跨 regime **算术平均**；按 `avgo_pos_20d` quartile 切片，bias 从 **-36 ppts**（Q1，AVGO 在 20d 底）到 **+47 ppts**（Q4，AVGO 在 20d 顶），**跨度 83 ppts**，**不是常量**。

这是 momentum-following score 公式（[predict.py:_score_signals](../predict.py)）在 mean-reversion regime 里的典型问题：
- AVGO 累计上涨 → trend=bullish + close_return positive + up_days majority + volume expanding → score > +2 → high confidence bullish → 但 AVGO 已经涨太多，D+1 大概率回调 → wrong
- AVGO 累计下跌 → 反向同理 → 高置信看空 → 但 D+1 反弹 → wrong

**含义**：simple "raw score → probability" 单调映射的 calibration 公式**无法解决 bipolar bias 问题**——它只能等比缩放，不能在两端反向修正。必须显式建 regime 轴。

## 4. `avgo_pos_20d` 诊断（最强 regime 轴）

> 定义：`(Close - 20d Low) / (20d High - 20d Low)`，0..1，反映 Close 在 20 日区间的位置。

| 分位 | 边界 | n | paired | acc | pred_bull | actual_up | **bias** |
|---|---|---|---|---|---|---|---|
| **Q1** | ≤ 0.38 | 63 | 50 | 0.480 | 0.22 | 0.58 | **-0.36** |
| Q2 | (0.38, 0.62] | 63 | 43 | 0.488 | 0.60 | 0.51 | +0.09 |
| **Q3** | (0.62, 0.82] | 62 | 47 | 0.511 | 0.83 | 0.43 | **+0.40** |
| **Q4** | > 0.82 | 62 | 53 | 0.491 | 0.98 | 0.51 | **+0.47** |

- Q1（AVGO 在 20d 底部）：模型 78% 看空，但实际 58% 上涨 → bias -36 ppts
- Q4（AVGO 在 20d 顶部）：模型 98% 看多，但实际仅 51% 上涨 → bias +47 ppts
- **bias 单调随 pos20 上升**，从 -36 → +9 → +40 → +47
- pos20 是单一 feature 中 bias swing 最大、且 monotonic 的 regime 轴

## 5. `avgo_ret_20d` / relative outperformance 诊断（互补轴）

### 5.1 `avgo_ret_20d`（AVGO 20 日累计收益 %）
| 分位 | 边界 | paired | acc | bias |
|---|---|---|---|---|
| Q1 | ≤ -1.23% | 50 | 0.460 | **-0.38** |
| Q2 | (-1.23, +3.90] | 48 | **0.583** | +0.04 |
| Q3 | (+3.90, +11.93] | 48 | 0.438 | **+0.52** |
| Q4 | > +11.93% | 47 | 0.489 | **+0.47** |

> Q2 是"区间震荡"regime，acc 0.583 远超随机；其他三档 bias 都 ≥ |0.38|。

### 5.2 `avgo_minus_qqq_20d`（AVGO 跑赢 QQQ 多少 pp）
| 分位 | paired | acc | bias |
|---|---|---|---|
| Q1 ≤ -0.93pp | 47 | 0.468 | **-0.45** |
| Q4 > +6.57pp | 48 | 0.479 | **+0.48** |

### 5.3 `avgo_distance_to_20d_low`（Close 到 20 日低点的 %）
| 分位 | paired | acc | bias |
|---|---|---|---|
| Q1 ≤ +5%（接近底） | 50 | 0.480 | **-0.40** |
| Q4 > +16%（远离底） | 49 | 0.490 | **+0.51** |

### 5.4 结论
- **AVGO 自身位置 / 动量是主轴**（pos20 / ret_20d / dist_low 都在两端 bias ≥ |0.38|）
- **AVGO 相对 QQQ / SOXX 跑赢过多是次级确认轴**（a-q_20d / a-s_20d 同方向放大 bias）
- volume_ratio / volatility（vol10）信息量较弱（4 分位 acc 在 0.42-0.58 之间无 monotonic 关系）

## 6. Failure signature

### 6.1 Single-bucket failure（paired ≥ 25 + acc ≤ 0.40）
| 规则 | paired | acc | bias |
|---|---|---|---|
| `soxx_minus_qqq_5d` Q3 (0.19, 1.43] | 45 | **0.400** | +0.33 |

唯一直接命中的单 quartile failure，触发条件不直观（"半导体微弱跑赢大盘"，不是 SOXX 强领涨也不是落后）。

### 6.2 Composite R4（最强失败签名）
**规则**：`avgo_minus_soxx_20d > 5pp` **AND** `avgo_pos_20d > 0.62`

| 字段 | 值 |
|---|---|
| n | 40 |
| paired | **31** |
| accuracy | **0.419** |
| pred_bull | 0.94 |
| actual_up | 0.35 |
| **bias** | **+0.58** |
| `cl=high` 子集 acc | **0.400** |
| `up_acc`（pa_adj=upgrade 子集） | **0.312** |

**解释**：这是经典的"**短期顶 + 跑赢同行**"信号 ——
- AVGO 已在 20d [Low, High] 上半段（pos20 > 0.62）
- 同时 20d 累计跑赢 SOXX 5pp 以上
- 模型按"AVGO 强 + 同行更弱"逻辑继续 momentum-following → 大概率 D+1 mean-reverting → 错

R4 是**最适合做 regime-aware calibration downgrade rule 的起点**。

### 6.3 其他高 bias buckets（参考）
| 规则 | paired | acc | bias |
|---|---|---|---|
| AVGO 10d > +7.16% (Q4) | 47 | 0.426 | +0.53 |
| AVGO 20d > +3.90% AND cl=high (R7) | 53 | 0.453 | +0.47 |
| pos20>0.62 AND fd=偏多 AND pcc≥2 (R10) | 51 | 0.471 | +0.53 |
| AVGO 5d > +5% AND vol10 > 1.9 (R3) | 32 | 0.469 | +0.47 |

## 7. 模型工作较好的 regime（inverse signature）

| 规则 | n | paired | acc | bias | high_acc |
|---|---|---|---|---|---|
| AVGO 10d < -3.84% (Q1，跌后反弹 regime) | 63 | 52 | **0.577** | -0.23 | 0.531 |
| AVGO 20d in (-1.23%, +3.90%] (Q2，区间震荡) | 63 | 48 | **0.583** | +0.04 | 0.591 |
| SOXX-QQQ 5d > +1.43 (Q4，半导体领涨) | 63 | 55 | **0.582** | +0.31 | **0.600** |

**结论**：
- 跌后反弹 regime → 模型正确捕捉 bounce
- 区间震荡 regime → 信号弱、bias 自然小、accuracy 接近随机偏正
- 半导体整体强势 regime → AVGO 的 momentum 信号与板块同步，跟得住

> 这三个 inverse 是**Step 3B 设计 regime-aware calibration 时不需要 downgrade 的 regime**。

## 8. High confidence failure 子集（pos20 Q3 深度切片）

> Q3 = `pos20 ∈ (0.62, 0.82]`，60 records / 45 paired，整体 acc 0.533。看似可接受，但分层后剧烈失效。

| 子集 | paired | accuracy | 备注 |
|---|---|---|---|
| **`cl=high`** | **19** | **0.263** | **最干净 high-conf failure 子集** |
| `fd=偏多` | 38 | 0.474 (bias +0.53) | high_acc 仅 0.250 (n=16) |
| `pa_adj=upgrade` | 16 | 0.375 | peer 强化进一步加剧 |
| `ex_ss=none` | 24 | 0.417 | 无 soft 警告反而最差 |
| `pa_adj=hold` | 15 | **0.667** | 模型自己 hold 反而准 |
| `ex_ss=high_path_risk` | 7 | **0.857** | 模型自己警觉时最准（小样本） |

**关键观察**：
- 最危险的是"**已经涨了一段（pos20 Q3）但未到极高位（不是 Q4） + 模型 high confidence 看多**"
- 模型自己犹豫（hold / high_path_risk）时反而更准 —— 与 Step 3A-2 / 3A-3 的 soft_signal 结论一致

## 9. 是否有可用 regime feature

✅ **有**。

- **单一最强**：`avgo_pos_20d`（4 分位 bias 单调从 -36 → +47）
- **复合最强（R4）**：`avgo_minus_soxx_20d > 5pp AND pos20 > 0.62`（up_acc 0.312）
- **辅助轴**：`avgo_ret_20d` / `avgo_distance_to_20d_low` / `avgo_minus_qqq_20d`（所有都给同方向 regime 区分）
- **信息量较弱**：volume_ratio / volatility（vol10 4 分位 acc 在 0.42-0.58 之间无 monotonic 关系）

## 10. 是否进入 Step 3B

✅ **建议进入 Step 3B，但仅做 design doc（不写代码）**。

理由 / 边界：
1. **不能直接写代码**：CLAUDE.md 硬规则禁止 LLM 改 scanner / encoder / 方向决策；但 calibration 是在不动 score 的前提下做 bias correction，可在 docs 层完整设计；
2. **不能直接升级 05 score 字段**：现 `historical_score / structure_score / peer_score / exclusion_penalty / event_score = 0.0 / None` 是 by design（Step 3A-2 已确认），3B 只设计公式，3C 才写 score 字段；
3. **Step 3B 必须是 `regime-aware calibration design`，不是 `simple calibration`**：
   - simple calibration 是 `raw_score → probability` 单调映射，**无法处理 bipolar bias**（它只能等比缩放，不能在两端反向修正）；
   - regime-aware calibration 必须显式加入 `pos20` / `relative outperformance` 这些轴，给"已涨太多 + 跑赢同行"和"已跌太多 + 跑输同行"两个极端做反向校准；
4. **Step 3B 不写代码 / 不动 DB / 不动测试**：纯 design + holdout 实验计划；
5. **本步骤的"regime feature 探测"已为 3B 提供具体输入**：pos20 / a-s_20d / a-q_20d 是 3B 公式的明确轴，R4 是 downgrade rule 的起点。

## 11. 推荐 Step 3B 设计方向

### 11.1 冻结 quartile boundaries（基于现有 250 records）
| Feature | Q1 上界 | Q2 上界（中位） | Q3 上界 |
|---|---|---|---|
| `avgo_pos_20d` | 0.38 | 0.62 | 0.82 |
| `avgo_ret_20d` | -1.23% | +3.90% | +11.93% |
| `avgo_minus_soxx_20d` | -1.37pp | +1.45pp | +5.01pp |
| `avgo_minus_qqq_20d` | -0.93pp | +2.19pp | +6.57pp |
| `avgo_distance_to_20d_low` | +5.01% | +10.00% | +16.03% |

### 11.2 主公式（草案，仅供 3B 起步）
设计 `(primary_score_raw, avgo_pos_20d) → calibrated_probability` 的 **4×4 lookup table**：
- 行：`primary_score_raw` quartile（用现有 250 records 经验数据 -2.75/-1/0/+1.5/+3 分桶）
- 列：`avgo_pos_20d` quartile（0.38 / 0.62 / 0.82）
- 值：该 quartile cell 的 empirical `actual_up_rate`（calibrated probability of UP）
- 行为：`primary_score_raw > 0` 在 pos20 Q4 cell 实际 0.51 → calibrated probability ≈ 0.51（remove +47ppts bias）；同样的 score 在 pos20 Q1 cell 实际 0.58 → calibrated probability ≈ 0.58（保留 / 校正 bias）

### 11.3 R4-style downgrade rule（草案）
```
IF avgo_minus_soxx_20d > 5pp
   AND avgo_pos_20d > 0.62
   AND final_direction == "偏多"
   AND confidence_level == "high":
   downgrade confidence_level to "medium"
   downgrade probability_bucket to "55-70%"
   add note: "regime: 短期顶 + 跑赢同行"
```

### 11.4 Holdout 验证计划
- **Window1 design / Window2 validate**（或反向）；
- 在设计 window 上拟合 4×4 lookup table；
- 在 holdout window 上比较：
  - 现有启发式 confidence_level 的 acc / bias；
  - regime-aware calibration 的 acc / bias；
- **目标**：calibration 后 high_acc 至少回到 ≥ 0.50；R4 子集 up_acc 至少从 0.312 回到 ≥ 0.45；overall bias 从 ±15 ppts 回到 ±5 ppts 以内；
- **如果 holdout 验证通过** → Step 3B-1 / 3C；
- **如果 holdout 失败** → 暂缓 calibration，回到 Step 3A-4（第三窗口）或考虑结构性问题。

### 11.5 不做的事（Step 3B 边界）
- ❌ 不写代码 / 不改 `predict.py` / 不改 `confidence_engine`
- ❌ 不升级 04 / 05 / 07 顶层字段
- ❌ 不动 simulated_trade
- ❌ 不打开 trade_engine_enabled
- ❌ 不接 trading API
- ❌ 不动 scanner / encoder（CLAUDE.md 硬规则）

## 12. 严守边界（本轮已遵守）

- ❌ 没改任何代码（`predict.py` / `services/*.py` / `scripts/*.py` / `tests/*.py` / `scanner.py` / `confidence_engine` 0 字节变化）
- ❌ 没新增测试
- ❌ 没 commit / push
- ❌ 没写 DB
- ❌ 没改 DB schema
- ❌ 没改 [predict.py](../predict.py) / [scanner.py](../scanner.py) / confidence_engine
- ❌ 没升级 contract 04 / 05 / 07 顶层字段
- ❌ 没写 calibration formula（仅诊断 + 11.2/11.3 草案）
- ❌ 没接 yfinance / 网络
- ❌ 没接 trading API / longbridge / broker / paper_trade
- ❌ 没保存 csv / 新脚本进仓库（所有诊断 inline `python3 << PY`）
- ❌ 没触碰 stash / .claude/worktrees/ / logs/prediction_log.jsonl
- ✅ 仅 sqlite SELECT + json 解析 + coded_data 本地 CSV 只读 + 现有 read-only 工具 + 新 docs 1 份
