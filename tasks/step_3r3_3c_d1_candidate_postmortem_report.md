# Step 3R-3.3C-D1 — Candidate Postmortem Report

> 本文是 **postmortem markdown** —— 只读分析 real validation output，不改代码、不写 DB、不重跑 replay / validation、不 commit / push、不接 trading API、不启 hard / forced、不改 required、不触碰 2026 final-test range、不 add `logs/regime_validation/` / W4 / smoke output / `logs/prediction_log.jsonl`、不处理 DB backup / stash / `.claude/worktrees/`、不调 `candidate_threshold` / SEED coefficients / 6 metric / 7 gate threshold。本报告只描述 / 解释；不优化、不拟合、不反推参数。

## 1. 当前完成状态

| 项 | 状态 |
|---|---|
| 本轮完成 read-only postmortem analysis | ✅ |
| 改代码 | ❌ 否 |
| 写 DB | ❌ 否 |
| 重跑 validation | ❌ 否 |
| 调 `candidate_threshold` / SEED coefficients | ❌ 否 |
| 调 6 metric / 7 gate threshold | ❌ 否 |
| 修改 4 个 raw output json 任一字符 | ❌ 否 |
| `git add` raw output json | ❌ 否（保持 untracked） |
| 重新生成 raw output | ❌ 否 |
| 接 yfinance / requests / 任何网络 / trading API | ❌ 否 |
| 启 hard / forced / `anti_false_exclusion_triggered` | ❌ 否 |
| 改 04 / 05 / 07 required | ❌ 否 |
| 触碰 2026 final-test range | ❌ 否 |
| 进入 Step 3R-5 / 3R-6 | ❌ 否 |
| 给具体新 threshold / 新 SEED coefficient | ❌ 否 |
| 写可执行 sweep 脚本 | ❌ 否 |

只新增 1 份 markdown report 文档（本文件）。

## 2. source run

| 字段 | 值 |
|---|---|
| `candidate_name` | `continuous_smoothing_v1` |
| `output_dir` | `logs/regime_validation/continuous_smoothing_v1_real_w1_w4_20260507_065417/` |
| `candidate_threshold` | `0.60` |
| `final_test_cutoff` | `"2026-01-01"` |
| `records_loaded` | `639` |
| `records_adapted` | `526` |
| `overall_status` | `fail` |
| `worst_window` | `W1` |
| `final_test_touched` | `false` |
| main commit | `c5bf686`（postmortem design checkpoint） |
| run main commit | `75f0ad5`（result checkpoint）/ `35c97d0`（execution glue impl checkpoint） |

## 3. per-window summary

| window | total_records | triggered | not_triggered | trigger_rate | false_exclusion_rate | net_benefit | accuracy_delta_vs_baseline | survival_case_preservation | triggered_paired | blocked_paired |
|---|---|---|---|---|---|---|---|---|---|---|
| W1 | 110 | 2 | 108 | **0.0182** | **1.0000** | -0.0096 | -0.0096 | 0.0000 | 2 | 2 |
| W2 | 93 | 23 | 70 | 0.2473 | 0.5217 | +0.0088 | +0.0088 | 0.0000 | 23 | 23 |
| W3 | 83 | 4 | 79 | 0.0482 | 0.5000 | -0.0040 | -0.0040 | 0.0000 | 4 | 4 |
| W4 | 240 | 107 | 133 | 0.4458 | 0.5421 | -0.0539 | -0.0539 | 0.0000 | 107 | 107 |
| **Total** | **526** | **136** | **390** | 0.2586 | (helper-pooled) | (helper-pooled) | (helper-pooled) | 0.0000 across all | 136 | 136 |

> 关键观察（不开处方）：
> - 4 个 window 的 `false_exclusion_rate` **全部** > helper gate 阈值 `0.10`（W1=1.0, W2=0.52, W3=0.50, W4=0.54）—— 这是**结构性**问题，不是 W1 单一尾部异常。
> - 每个 window 的 `survival_case_preservation` 都 = `0.0` —— candidate 一旦触发，全部**阻止** survivor；从未保留任何 survivor。
> - W2 唯一一个 `net_benefit` 正值；其他 3 个 window 都为负。
> - `triggered_paired = blocked_paired` 在每个 window 都成立 —— 触发 = 阻塞，没有"软阻止"。

## 4. W1 triggered cases（完整 2 条）

### 4.1 case 1 — `2023-01-03`

| 字段 | 值 |
|---|---|
| `analysis_date` | `2023-01-03` |
| `prediction_for_date` | `2023-01-04` |
| `window` | `W1` |
| `candidate_triggered` | `true` |
| `prediction_correct` | `true` |
| `baseline_correct` | `true` |
| `survival_case` | **`true`**（survivor） |
| `exclusion_would_block` | `true` |
| `actual_direction` | `up` |
| `risk_score` | `0.6822` |
| `risk_bucket` | `high` |
| `adjustment_score` | `0.1822` |
| **features_used** | |
| `pos20` | `0.5378` |
| `avgo_minus_soxx_20d` | `0.1187` |
| `peer_5d_aligned_pct` | `0.0000` |
| `market_trend_strength` | `0.0000` |
| `monthly_shock` | `0.0000` |
| labels | `pos20_regime=mid` / `avgo_minus_soxx_20d_regime=outperform` / `peer_momentum_regime=weak` / `market_trend_regime=neutral_market` / `monthly_context_regime=normal` |

### 4.2 case 2 — `2023-07-11`

| 字段 | 值 |
|---|---|
| `analysis_date` | `2023-07-11` |
| `prediction_for_date` | `2023-07-12` |
| `window` | `W1` |
| `candidate_triggered` | `true` |
| `prediction_correct` | `true` |
| `baseline_correct` | `true` |
| `survival_case` | **`true`**（survivor） |
| `exclusion_would_block` | `true` |
| `actual_direction` | `up` |
| `risk_score` | `0.6081` |
| `risk_bucket` | `high` |
| `adjustment_score` | `0.1081` |
| **features_used** | |
| `pos20` | `0.8998` |
| `avgo_minus_soxx_20d` | `0.0597` |
| `peer_5d_aligned_pct` | `0.0000` |
| `market_trend_strength` | `1.0000` |
| `monthly_shock` | `0.0000` |
| labels | `pos20_regime=extreme` / `avgo_minus_soxx_20d_regime=outperform` / `peer_momentum_regime=weak` / `market_trend_regime=sustained_bull_market` / `monthly_context_regime=normal` |

## 5. 为什么 W1 false_exclusion_rate = 1.0

直接计算：

| 量 | 值 |
|---|---|
| W1 中 `candidate_triggered=True` 总数 | 2 |
| 其中 `survival_case=True`（且 `prediction_correct=True`） | 2 |
| 其中 `survival_case=False`（即 candidate 正确排除的） | 0 |
| `false_exclusion_rate = 2 / 2` | **1.0** |

解释：

- W1 中 candidate 一共只触发 2 次；
- 这 2 次触发的 row 都是 **survivor**（`prediction_correct=True` + `baseline_correct=True` + `actual_direction=up`）；
- candidate 把它们标 `exclusion_would_block=true` —— 等同于 candidate 错排了 100% 的触发 case；
- 因此 helper `false_exclusion_rate = blocked_paired_survivors / blocked_paired = 2/2 = 1.0`，**触顶**（gate 阈值 0.10 的 10×）。

判定：

- ✅ 与 `fail_reason` 字符串 `"... at W1: false_exclusion_rate=1.0000_above_0.1"` 完全吻合
- ✅ adapter / helper 字段映射正确；不是 pipeline bug
- ✅ candidate v1 在 W1 真实 regime 上的**直接失败原因**是：触发的 2 条全是 survivor

> 注意：survival_case_preservation = 0.0 不只是 W1 现象 —— 4 个 window 都是 0.0；candidate 一旦触发**从不保留** survivor。这是 candidate-level 结构性问题，不仅仅是 W1。

## 6. trigger sparsity（跨窗口触发率高度不均衡）

| window | trigger rate | 触发 / 总 |
|---|---|---|
| W1 | **1.8%** | 2 / 110 |
| W2 | 24.7% | 23 / 93 |
| W3 | 4.8% | 4 / 83 |
| W4 | 44.6% | 107 / 240 |

观察（不开处方）：

- W1（2023-01-03 ~ 2023-08-31）+ W3（2024-03-01 ~ 2024-08-02）触发率 < 5%，统计稳定性不足；
- W4（2024-08-03 ~ 2025-12-31）触发率 ~45%，candidate 在该 window 极易触发；
- W1 / W3 vs W4 触发率比 ≈ 1 : 24（最极端）；
- helper `cross_window_variance` 直接 fail（per fail_reason 包含 `cross_window_variance`）；
- 这是 candidate 在不同 regime 下 risk_score 分布差异极大的间接证据 —— 但不由此反推 threshold v2。

## 7. risk_score distribution

| window | n | min | p25 | median | p75 | max | mean | triggered_mean | nontriggered_mean |
|---|---|---|---|---|---|---|---|---|---|
| W1 | 110 | 0.251 | 0.366 | 0.398 | 0.452 | **0.682** | 0.414 | 0.645 | 0.410 |
| W2 | 93 | 0.278 | 0.418 | 0.527 | 0.602 | 0.779 | 0.520 | 0.676 | 0.468 |
| W3 | 83 | 0.246 | 0.380 | 0.417 | 0.493 | 0.735 | 0.436 | 0.660 | 0.424 |
| W4 | 240 | 0.230 | 0.425 | 0.556 | 0.702 | 0.867 | 0.561 | 0.708 | 0.444 |

观察：

- **threshold = 0.60** 与各 window 的 p75 比较：
  - W1: p75 = 0.452 → threshold 在 ~p98+ 长尾 → 几乎击不中
  - W2: p75 = 0.602 → threshold ≈ p75 → 少量击中
  - W3: p75 = 0.493 → threshold 在 ~p90+ 长尾 → 少量击中
  - W4: p75 = 0.702 → threshold 在 p55 ~ p60 区间 → 大量击中
- W1 max = 0.682 —— 整窗最高 risk_score 仅略高于 threshold；触发只 2 条已经是上限；
- W4 max = 0.867 —— 显著更高，且 mean 0.561 接近 threshold；触发 ~107 条；
- triggered_mean 在 4 个 window 都 ≈ 0.65 ~ 0.71（接近 threshold + bucket 偏移）—— 说明 candidate 的"高 risk"判定在跨 window 是**绝对值**比较，不是相对比较；
- 但**不**由此提出新 threshold —— 任何 threshold v2 必须独立 launch review。

## 8. risk_bucket distribution（逐 window；含 triggered 计数）

| window | bucket | count | triggered_count |
|---|---|---|---|
| W1 | low | 18 | 0 |
| W1 | medium | 90 | 0 |
| W1 | high | 2 | 2 |
| W2 | low | 5 | 0 |
| W2 | medium | 65 | 0 |
| W2 | high | 23 | 23 |
| W3 | low | 12 | 0 |
| W3 | medium | 67 | 0 |
| W3 | high | 4 | 4 |
| W4 | low | 17 | 0 |
| W4 | medium | 116 | 0 |
| W4 | high | 100 | 100 |
| W4 | extreme | 7 | 7 |

观察：

- 触发对应 bucket = `high` 或 `extreme`；与 candidate 内部 `_bucket_risk_score(...)` 阈（< 0.35 → low, < 0.60 → medium, < 0.80 → high, ≥ 0.80 → extreme）一致；
- W1 没有任何 `extreme` bucket（max risk_score = 0.682 < 0.80）；
- W4 7 条 `extreme` 全部触发，100 条 `high` 也全部触发 —— 触发并非 bucket 细分驱动，而是 risk_bucket ∈ {high, extreme} 即触发；
- W1 / W3 极少 high bucket → 极少触发 → 统计样本不足；
- W4 触发量大但 false_exclusion_rate 仍 0.54 —— candidate 在 W4 触发量充足时，仍**没能**区分 survivor vs not。

## 9. feature review

5 个 seed feature × 4 window 的 mean / median / range（仅 descriptive；不做 SHAP / 不做回归）：

| window | feature | n | mean | median | min | max |
|---|---|---|---|---|---|---|
| W1 | pos20 | 110 | 0.608 | 0.645 | 0.015 | 0.993 |
| W1 | avgo_minus_soxx_20d | 110 | 0.016 | 0.016 | -0.148 | 0.165 |
| W1 | peer_5d_aligned_pct | 110 | 0.676 | 1.000 | 0.000 | 1.000 |
| W1 | market_trend_strength | 110 | 0.822 | 1.000 | 0.000 | 1.000 |
| W1 | monthly_shock | 110 | 0.032 | 0.000 | 0.000 | 1.000 |
| W2 | pos20 | 93 | 0.671 | 0.725 | 0.002 | 0.990 |
| W2 | avgo_minus_soxx_20d | 93 | 0.028 | 0.026 | -0.071 | 0.091 |
| W2 | peer_5d_aligned_pct | 93 | 0.685 | 1.000 | 0.000 | 1.000 |
| W2 | market_trend_strength | 93 | 0.409 | 0.600 | -0.500 | 1.000 |
| W2 | monthly_shock | 93 | 0.172 | 0.000 | 0.000 | 1.000 |
| W3 | pos20 | 83 | 0.544 | 0.612 | 0.005 | 0.989 |
| W3 | avgo_minus_soxx_20d | 83 | 0.021 | 0.008 | -0.097 | 0.206 |
| W3 | peer_5d_aligned_pct | 83 | 0.590 | 0.667 | 0.000 | 1.000 |
| W3 | market_trend_strength | 83 | 0.758 | 1.000 | -0.500 | 1.000 |
| W3 | monthly_shock | 83 | 0.127 | 0.000 | 0.000 | 1.000 |
| W4 | pos20 | 240 | 0.637 | 0.755 | 0.007 | 0.999 |
| W4 | avgo_minus_soxx_20d | 240 | 0.047 | 0.036 | -0.215 | 0.471 |
| W4 | peer_5d_aligned_pct | 240 | 0.585 | 0.667 | 0.000 | 1.000 |
| W4 | market_trend_strength | 240 | 0.418 | 0.600 | -0.500 | 1.000 |
| W4 | monthly_shock | 240 | 0.444 | 0.000 | 0.000 | 1.000 |

观察 + W1 触发 2 条的关键 feature pattern：

- W1 case 1（`2023-01-03`）：`peer_5d_aligned_pct = 0` 且 `market_trend_strength = 0`（neutral_market；2023 年初尚未确立 bull 趋势）。两个**减项** feature（系数 -0.8 和 -0.7）贡献为 0 → risk_score 没有被消减 → 触发。
- W1 case 2（`2023-07-11`）：`peer_5d_aligned_pct = 0`（peer momentum weak），`market_trend_strength = 1`（sustained_bull_market）。`pos20 = 0.90`（系数 +1.2）+ `avgo_minus_soxx_20d = 0.06`（系数 +1.0）—— 即使 `market_trend_strength` 满给 -0.7，`pos20` 极端 + AVGO outperform 仍把 risk_score 推上 0.60。
- 这 2 条都是 AVGO 实际**继续上涨**（`actual_direction=up`）；candidate 因为 pos20 高 + AVGO 跑赢 SOXX 把它们标为 high risk → 误排 survivor。
- 跨 window：`pos20` 长期高（W4 中位 0.755）；`avgo_minus_soxx_20d` 长期正（W4 mean 0.047）；`market_trend_strength` mean 跨 window 浮动（W1=0.82, W2=0.41, W3=0.76, W4=0.42）。
- `monthly_shock` 在所有 window 中位都 = 0.000（罕发）；W1 和 W2 case 中都 = 0；W4 mean=0.444（更高，但仍是稀疏 0/1 二值化驱动）。

> **不**做 SHAP / 不做 logistic / 不做 windowed-fit / 不做 importance ranking；只描述 observed pattern。

## 10. root cause hypotheses

5 项 hypothesis（**不**附带具体新参数 / 新阈值 / 新组合）：

| # | Hypothesis | 证据 |
|---|---|---|
| **H1** | candidate 的 risk_score **跨 window 分布不可比** —— 同样 risk_score=0.65 在 W1 是极端长尾，在 W4 接近 mean。固定 global threshold 会在不同 regime 上给出极端不同的触发率。 | §7 risk_score quantile 表 + §6 trigger rate 跨 window 1 : 24 |
| **H2** | seed features 看起来更像 **regime classifier**（描述当前趋势 / 偏离 / shock），而不是 **exclusion-risk classifier**（区分"会反转的 survivor"vs"不会反转的 not-survivor"）。所有 4 个 window 的 false_exclusion_rate ≥ 0.5，且 survival_case_preservation = 0.0 across all windows。 | §3 全 window false_exclusion / survival_case_preservation；§9 W1 触发 case 中 pos20 高 + AVGO outperform → AVGO 第二天**继续涨**，与 candidate 的 "high risk = block" 假设相反 |
| **H3** | seed coefficients **极性可能颠倒**：candidate 把 `pos20` 高 + `avgo_minus_soxx_20d` 高（相对强势）当作 "overheat → 易反转 → 应排除"；但真实数据中这些 feature 处于高位的 row 反而是**继续上涨**的 survivor —— 至少在 W1 这样的早期 bull 阶段是如此。 | §9 W1 case 2: pos20=0.90, avgo_minus_soxx_20d=0.06 → actual=up；这两个 feature 的 + 系数把 risk 推高，但 outcome 与 candidate 假设反向 |
| **H4** | candidate 的 **damping feature**（`peer_5d_aligned_pct` 系数 -0.8、`market_trend_strength` 系数 -0.7）在很多 W1 row 上等于 0（peer_momentum_regime=weak / 早期 trend 未确立），无法消减"+ 系数"产生的 risk → high bucket 触发。 | §4.1 case 1: peer=0, trend=0；§4.2 case 2: peer=0, trend=1；W1 中 peer mean 0.676 但中位 1.000（双峰） |
| **H5** | candidate v1 缺少 **min trigger support guard** 与 **calibration**。helper 已有 `GATE_MIN_WINDOW_SAMPLE = 20`，但 candidate 自身没有"低样本不下结论"的机制；同时 risk_score 没有校准到 observed false_exclusion probability，导致 score=0.65 在不同 window 含义不一致。 | §6 W1 / W3 触发数 < 20 直接 trigger min_sample fail；§7 跨 window trigger_mean 都 ≈ 0.65 ~ 0.71，但 outcomes 完全不同 |

> **不**针对任一 hypothesis 提出"因此应该 X = Y"。每条 hypothesis 都是给 v2 launch review 的输入材料。

## 11. threshold review

| 项 | 值 / 状态 |
|---|---|
| `candidate_threshold` 当前值 | **`0.60`** —— first-run design seed |
| 本 postmortem 是否建议新 threshold | ❌ 否 |
| 本 postmortem 是否建议 sweep / grid / retry | ❌ 否 |
| 本 postmortem 是否暗示具体 lower / higher 数值方向 | ❌ 否 |
| 本 postmortem 观察到的事实 | per-window trigger rate 极不均衡（W1=1.8% vs W4=44.6%）；4 个 window false_exclusion_rate 全 ≥ 0.50（W1=1.0）；4 个 window survival_case_preservation = 0.0；triggered_mean ≈ 0.65 ~ 0.71 跨 window 接近一致 |
| 关键判断 | threshold 单值变化**不能**修复 survival_case_preservation = 0.0 跨所有 window 的现象 —— 这是 candidate score → outcome 的对齐问题，不是单一 threshold 调位置的问题 |
| threshold v2 | 必须经独立 launch review；本 postmortem 是 review 的**输入**，不是 review 本身 |

## 12. v2 questions

v2 launch review 前需要回答的 7 个问题（不含答案）：

| # | 问题 |
|---|---|
| 1 | v2 是继续做 global fixed threshold，还是 window-aware / regime-aware threshold？（H1 + 跨 window risk_score 分布不可比） |
| 2 | v2 是否需要 **minimum trigger support guard**（candidate 自身的"低样本不下结论"机制，区别于 helper `GATE_MIN_WINDOW_SAMPLE`）？ |
| 3 | v2 是否需要区分 **overheat risk** 与 **false-exclusion risk**？（H2 + H3：v1 score → outcome 对齐方向不明） |
| 4 | `monthly_shock` 是否应该保留？（中位 0.000 across all windows；稀疏二值化；对 W1 触发 0 贡献） |
| 5 | `market_trend_strength` 是否应防止"强 bull 趋势 → 误判 high risk"？（H4：v1 中即便 trend=1 + 系数 -0.7 仍不足以消减 pos20 推高的 risk） |
| 6 | risk_score 是否应该 **calibrate** 到 observed false_exclusion probability（如 isotonic / Platt），让跨 window 比较有意义？（H5 + §7 triggered_mean 跨 window 高度相似但 outcome 不同） |
| 7 | v2 如何避免**从 v1 fail 数据直接反推参数**？（要求 v2 的设计参数来源是先验 / 文献 / 工程判断，不是 grid search 得到的最优；validate 阶段才**判读** v1 baseline，不是参数来源） |

## 13. recommended_next_step

**`launch_continuous_smoothing_v2_design_review`**

判定理由：

| 评估项 | 结果 | 解读 |
|---|---|---|
| pipeline 健康度 | ✅ 13/13 acceptance pass；DB unchanged；4 文件 schema valid | 不是 pipeline / schema / IO bug |
| 数据健康度 | ✅ 639 / 526 records；4 window 全有 records；W4 即使 113 row 缺 outcome 仍有 240 paired | 数据已足够评估 v1，且足够评估未来 v2 |
| candidate 是否仍有信号 | ⚠️ 部分有 —— W2 net_benefit 微正（+0.0088）；triggered 与 non-triggered 的 risk_score mean 有明显分离（如 W4 0.708 vs 0.444） | 信号存在但**对齐方向**不对（H2 / H3） |
| candidate 是否结构性失败 | ✅ 是 —— **4 window 全部** false_exclusion ≥ 0.50 + survival_case_preservation = 0.0 | 不是 W1 单一 fold 问题 |
| 是否值得 v2 重新设计 | ✅ 是 —— H1 / H2 / H3 / H4 / H5 都是可设计可测试的方向，且数据 baseline 已固定 | 有清晰的 review questions（§12） |
| 是否值得**整体放弃** continuous_smoothing 方向（abandon） | ❌ 否 —— W2 微正 net_benefit + W4 / W2 trigger rate 表明 candidate 选择的 feature 集合并非完全无信号；只是对齐 / calibration 问题 | 不需要 redesign from candidate layer |

**最终判定**：选择 `launch_continuous_smoothing_v2_design_review`。

> **本 recommendation 不解锁 3R-5 / 3R-6**；v2 必须独立 launch review → v2 design + checkpoint → v2 implementation + tests → v2 single real run → v2 result checkpoint → 再判断。任何一步 fail → 同样回到 candidate / threshold layer。

## 14. no-go confirmations

逐项确认（与 design / design checkpoint §10-11 / no-go §10 / 20 项一致）；本 postmortem 全部**未触发**：

| no-go | status |
|---|---|
| no threshold change | ✅ 未触发（threshold = 0.60 未改） |
| no SEED change | ✅ 未触发（SEED_COEFFICIENTS 未改） |
| no validation rerun | ✅ 未触发（仍使用 `20260507_065417` baseline） |
| no raw output commit | ✅ 未触发（4 文件保持 untracked） |
| no DB write | ✅ 未触发（DB 未读未写；postmortem 仅读 `output_dir` 4 json） |
| no 2026 touch | ✅ 未触发（cutoff 未改；2026 范围未读） |
| no 3R-5 / 3R-6 unlock | ✅ 未触发（`recommended_next_step` 不解锁；只允许 v2 review） |
| no hard / forced / required change | ✅ 未触发 |
| no `_PROTECTION_LAYER_CONNECTED` 翻 True | ✅ 未触发 |
| no sweep / grid search | ✅ 未触发（无 sweep；§7 的 quantile 是描述，不是搜索） |
| no retry until pass | ✅ 未触发 |
| no 接 yfinance / requests / urllib / 任何网络 | ✅ 未触发 |
| no 接 trading API | ✅ 未触发 |
| no 改 wrapper / provider / orchestrator / candidate / adapter / helper / glue 任一已 merge 模块 | ✅ 未触发 |
| no 改任何已 merge 测试 | ✅ 未触发 |
| no 用 first run 数据反推 threshold / SEED | ✅ 未触发（§10 hypothesis 全部无具体数值；§11 明确禁止；§12 所有 v2 question 都不含具体值） |
| no 把 fail 当系统错误 / 修复任何已 merge service | ✅ 未触发（§5 / §13 明确：legal fail，pipeline 健康） |
| no 把 postmortem 写成可执行 sweep 脚本 | ✅ 未触发（仅 markdown report；inline read-only Python 用于统计，不留在 repo） |
| no 新增 `.py` 文件到 repo | ✅ 未触发（不新增 `scripts/postmortem_*.py` / `tests/test_postmortem_*.py`） |
| no 新增测试 | ✅ 未触发 |

## 15. 严守边界

本文是**纯 postmortem markdown**：

- ❌ 没改任何代码（`services/*` / `ui/*` / `tests/*` / `scripts/*` 全部未触碰）
- ❌ 没改 DB schema
- ❌ 没写 DB
- ❌ 没运行 replay
- ❌ 没**重新运行** real validation（baseline 仍是 `20260507_065417` run；本 postmortem 不触发新 run）
- ❌ 没运行 prepare-only smoke
- ❌ 没修改 4 个 raw output json 任一字符
- ❌ 没改 `run_predict` / `predict.py` / `scanner.py` / `prediction_store.py` / `app.py`
- ❌ 没改 `services/regime_features_builder.py` / `services/regime_labels_builder.py` / `services/regime_validation_helper.py` / `services/continuous_smoothing_candidate.py` / `services/replay_validation_record_adapter.py` / `services/historical_replay_training.py` / `services/real_regime_label_provider.py` / 任何 ui 模块 / 任何 builder
- ❌ 没改 `scripts/run_continuous_smoothing_validation.py` / `scripts/run_real_continuous_smoothing_validation.py` / `scripts/run_real_continuous_smoothing_validation_execute.py`
- ❌ 没改 `tests/test_run_continuous_smoothing_validation.py` / `tests/test_run_real_continuous_smoothing_validation.py` / `tests/test_real_regime_label_provider.py` / `tests/test_run_real_continuous_smoothing_validation_execute.py` / 任何已 merge 测试
- ❌ 没新增 `scripts/postmortem_*.py` / `tests/test_postmortem_*.py`（postmortem 全部 inline read-only Python，不留在 repo）
- ❌ 没改 04 / 05 / 07 任何 required 字段
- ❌ 没启用 `hard` / `forced_exclusion` / `anti_false_exclusion_triggered`
- ❌ 没接 `yfinance` / `requests` / 任何网络
- ❌ 没接 trading API / `longbridge` / `broker` / `paper_trade`
- ❌ 没让 `_PROTECTION_LAYER_CONNECTED` 翻 True
- ❌ 没让 `hard_gate_status.protection_layer_connected` 自动 pass
- ❌ 没改 `hard_exclusion_allowed` / `primary_blocker` 派生
- ❌ 没触碰 2026-01-01 之后 final-test range
- ❌ 没改 Step 3R-4 protocol thresholds（6 metric / 7 gate / 10 no-go）
- ❌ 没改 Step 3R-2 helper / 3R-3.1 candidate / 3R-4.2 helper / 3R-4.3A adapter 行为
- ❌ 没改 Step 3R-3.3 / 3R-3.3A / 3R-3.3B / 3R-3.3C 系列 / 3R-3.3C-D 已 merge 文档 / 实施
- ❌ 没改 Step 2G-8D / 8D.1A / 8D.2 / 8D.3 / 8D.4 文档或代码
- ❌ 没把 W4 / smoke / `logs/regime_validation/` / `logs/prediction_log.jsonl` / DB backup / `agent_loop.py` / `.claude/worktrees/` 任一 commit 进 main
- ❌ 没创建任何**新的** `logs/regime_validation/*` 子目录
- ❌ 没运行 `pytest`（本轮纯 read-only 分析；测试基线维持 commit `7812b10` 时的 **2905 / 0 failed / 10 skipped**）
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*`
- ❌ 没调 `candidate_threshold` / SEED coefficients / 6 metric / 7 gate threshold
- ❌ 没用 first run 数据反推任何参数
- ❌ 没让 fail 触发 retry / sweep / grid search
- ✅ 只新增 1 份 markdown postmortem report 文档（本文件）
