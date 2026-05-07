# Step 3R-3.3G1 — V2 Failure Postmortem / Comparison Review Report

> 本文是 **read-only review report** —— 只读 v1 / v2 raw output 做 overlap analysis；不改代码、不写 DB、不重跑 replay / validation、不 commit / push、不接 trading API、不启 hard / forced、不改 required、不触碰 2026 final-test range、不 add `logs/regime_validation/` / W4 / smoke output / `logs/prediction_log.jsonl`、不处理 DB backup / stash / `.claude/worktrees/`、不调 v1 / v2 任一 threshold / SEED / coefficient / 工程默认、不 retry / 不 sweep / 不 auto-promotion、不进 3R-5 / 3R-6。

## 1. 当前完成状态

| 项 | 状态 |
|---|---|
| 本轮完成 read-only comparison analysis | ✅ |
| 改代码 | ❌ 否 |
| 写 DB | ❌ 否 |
| 重跑 validation | ❌ 否 |
| 调 v1 / v2 任一参数 | ❌ 否 |
| 修改 raw output json 任一字符 | ❌ 否 |
| `git add` raw output json | ❌ 否（保持 untracked） |
| 重新生成 raw output | ❌ 否 |
| 接 yfinance / 网络 / trading API | ❌ 否 |
| 启 hard / forced / required | ❌ 否 |
| 触碰 2026 final-test range | ❌ 否 |
| 进 3R-5 / 3R-6 | ❌ 否 |
| 给具体新 threshold / 新 family 公式 / 新 calibration 曲线 / 新 actuator 公式 | ❌ 否 |
| 新增 `.py` 文件 | ❌ 否 |

只新增 1 份 markdown report 文档（本文件）。

## 2. source runs

| 项 | v1 | v2 |
|---|---|---|
| `output_dir` | `logs/regime_validation/continuous_smoothing_v1_real_w1_w4_20260507_065417/` | `logs/regime_validation/continuous_smoothing_v2_real_w1_w4_20260507_091823/` |
| `candidate_name` | `continuous_smoothing_v1` | `continuous_smoothing_v2` |
| `records_loaded` | 639 | 639 |
| `records_adapted` | 526 | 526 |
| `final_test_touched` | `false` | `false` |
| `overall_status` | `fail` | `fail` |
| `worst_window` | W1 | W1 |
| triggered total | 136 | 97 |
| W1 `false_exclusion_rate` | 1.0000 | 1.0000 |
| `survival_case_preservation`（all windows） | 0.0 / 0.0 / 0.0 / 0.0 | 0.0 / 0.0 / 0.0 / 0.0 |

## 3. join method

Join key：`(analysis_date, prediction_for_date, window)` 三元组。

| 项 | 值 |
|---|---|
| v1 records | 526 |
| v2 records | 526 |
| matched（inner join） | **526**（**100%** 完全匹配） |
| v1-only keys（v1 有 v2 没有） | 0 |
| v2-only keys（v2 有 v1 没有） | 0 |

> 两次 run 的 record 集合**完全相同**（同一 wrapper / adapter input），后续 4-cell overlap 是**纯 candidate_triggered 决策差异**，不掺杂 input 差异。

约束：

- ❌ 不修改 raw output
- ❌ 不重新生成 records
- ❌ 不 `git add` raw json

## 4. overlap 4-cell summary（核心数据）

| bucket | definition | count | percent_of_total | pc_true | pc_false | pc_true_rate | survival_case_count | survival_case_rate |
|---|---|---|---|---|---|---|---|---|
| **A both_triggered** | v1=True ∧ v2=True | **88** | **16.7%** | 52 | 36 | **0.5909** | 52 | 0.5909 |
| **B v1_only** | v1=True ∧ v2=False | **48** | **9.1%** | 22 | 26 | 0.4583 | 22 | 0.4583 |
| **C v2_only** | v1=False ∧ v2=True | **9** | **1.7%** | 3 | 6 | **0.3333** | 3 | 0.3333 |
| **D neither** | v1=False ∧ v2=False | **381** | **72.4%** | 176 | 205 | 0.4619 | 0 | 0.0000 |

校验：

- A + B = 88 + 48 = **136** = v1 triggered total ✓
- A + C = 88 + 9 = **97** = v2 triggered total ✓
- A + B + C + D = 526 ✓
- `pc_true_rate ≈ survival_case_rate` 在 A/B/C（D 中所有 row 都是 candidate_triggered=False，所以 survival_case 在 adapter 中只对 triggered 计数 → D 的 sv_rate=0.0 是 adapter 定义产物，**不**代表 D 没有 survivor）

> 注：`survival_case` 在 adapter 中是 `candidate_triggered=True ∧ direction_correct=True`（即"被错排的 survivor"），所以 D bucket sv_count=0 是定义性产物，不是负面信号。

baseline 参考：全 526 row 的 prediction_correct_true rate = (52+22+3+176) / 526 = **0.481**。

| bucket vs baseline | observation |
|---|---|
| **A**（pc_true_rate=0.59）| **比 baseline 高 11pp** —— v1 v2 共同触发的 row 反而**更可能是 survivor**（candidate 在 agreement zone 与 outcome **反向**） |
| **B**（pc_true_rate=0.46）| ≈ baseline —— v1 触发但 v2 未触发的 row pc_true_rate 与随机几乎一致（v2 abstain 的不是 v1 的 true positive，也不是 v1 的 false positive，是中性的） |
| **C**（pc_true_rate=0.33）| **比 baseline 低 15pp** —— v2 新增触发的 row **更可能是 wrong prediction**（**唯一**有 meaningful 信号的子集，但 N=9 太小） |
| **D**（pc_true_rate=0.46）| ≈ baseline —— 两次都不触发的 row 与基线无差异 |

## 5. per-window overlap summary

| window | both_triggered | v1_only | v2_only | neither | total |
|---|---|---|---|---|---|
| W1 | **1** | 1 | 0 | 108 | 110 |
| W2 | 13 | 10 | 0 | 70 | 93 |
| W3 | 1 | 3 | 4 | 75 | 83 |
| W4 | **73** | 34 | 5 | 128 | 240 |
| **Total** | **88** | **48** | **9** | **381** | **526** |

观察：

- **W1**：v1 触发 2 条（A=1 + B=1），v2 触发 1 条（A=1 + C=0）；v2 在 W1 没有恢复任何新 trigger；W1 触发的 1 条仍是 survivor（pc_true_rate=1.0 = 1/1）→ W1 false_exclusion_rate=1.0 **持平**
- **W2**：v1 触发 23（13+10），v2 触发 13（13+0）；v2 删了 v1 的 10 个 v1_only，没有新增；v2 abstain 主要发生在 W2
- **W3**：v1 触发 4（1+3），v2 触发 5（1+4）；这是**唯一一个 v2 触发更多的 window**；W3 v2_only=4 是 C 子集的主要来源
- **W4**：v1 触发 107（73+34），v2 触发 78（73+5）；v2 主要在 W4 删了 34 个 v1_only；v2 在 W4 几乎没有新发现

> v2 reduce 主要发生在 W2 / W4（B 子集 48 中 W2=10 + W4=34 = 44 / 48 = 92%）；v2 add 主要发生在 W3 / W4（C 子集 9 中 W3=4 + W4=5 = 9 / 9 = 100%）。

## 6. trigger quality comparison（用真实数字回答）

### 6.1 v2 删掉的 v1-only cases（B 子集）是否更偏 wrong prediction？

- B 中 pc_true=22, pc_false=26 → pc_true_rate **0.458**
- baseline pc_true_rate = **0.481**
- **结论**：B 子集 pc_true_rate **接近 baseline**（差 −2.3pp，统计上不显著）；v2 abstain 删掉的不是 v1 的 true positives（应排除的 row），也不是 v1 的 useful triggers（错排的 survivor）；v2 abstain 在 B 子集**没有偏向**

### 6.2 v2-only cases（C 子集）是否比 v1-only 更差？

- C 中 pc_true_rate **0.333**（3/9）
- B 中 pc_true_rate **0.458**（22/48）
- **结论**：C 子集 pc_true_rate **比 B 低 12.5pp** —— v2 新增的 trigger **比 v1 abstain 掉的更偏向 wrong prediction**；C 是**唯一在 baseline 之下** 的 trigger 子集
- 但 **N=9 太小**（仅占总数 1.7%）；不能基于 9 条 row 得出"v2 真的找到信号"的结论

### 6.3 both-triggered cases（A 子集）是否主要是 survivor？

- A 中 pc_true=52, pc_false=36 → pc_true_rate **0.591**
- baseline = 0.481
- **结论**：A 子集 **pc_true_rate 比 baseline 高 11pp** —— **v1 v2 共同触发的 row 反而更可能是 survivor**；这是 candidate-layer 的**结构性 anti-alignment**：v1 和 v2 都把 high-momentum / outperform regime 标为高 risk，但这些 regime 中 prediction 实际上**更可能正确**（momentum continuation）

### 6.4 neither bucket（D 子集）是否包含大量 prediction_wrong cases？

- D 中 pc_false=205, pc_true=176 → pc_true_rate **0.462**
- baseline = 0.481
- **结论**：D 子集 ≈ baseline；candidate 不触发的 381 条 row 中**有 205 条是 wrong prediction**（38.7% of all wrong predictions in dataset）；这些 candidate 应该捕捉但**没有捕捉**

> **总体判断**：candidate 在 526 条 row 上几乎是 random discriminator。A 子集（共同 trigger）甚至**反向**（更偏 survivor）；C 子集（v2-only）有微弱信号但太小；D 子集有大量未捕捉的 wrong prediction。

## 7. false exclusion interpretation

定义：

- `triggered=True ∧ prediction_correct=True` = **false exclusion**（candidate 想排除 survivor）
- `triggered=True ∧ prediction_correct=False` = **correct exclusion**（candidate 正确排除 wrong prediction）
- helper `survival_case_preservation`：在 triggered subset 中 survivor 被"保留"的比例 —— 但 candidate 是 binary actuator（trigger=block），所以 triggered + survivor 永远是"被错排" → preservation = 0

A / B / C 子集都是 candidate triggered（v1 或 v2 至少一方）：

| 子集 | survivor count | survivor rate | 是 false exclusion 吗 |
|---|---|---|---|
| A（v1 ∧ v2） | 52 | 59% | ✅ 52 cases；高于 baseline |
| B（v1 only） | 22 | 46% | ✅ 22 cases；≈ baseline |
| C（v2 only） | 3 | 33% | ✅ 3 cases；低于 baseline |
| **Total triggered survivors（v1 视角）= A + B** | **74** | / 136 = **54.4%** | v1 W1+W2+W3+W4 false_exclusion 持续高 |
| **Total triggered survivors（v2 视角）= A + C** | **55** | / 97 = **56.7%** | v2 false_exclusion 反而**比 v1 更高** |

→ **解释 survival_case_preservation = 0.0 across all windows**：v1 / v2 触发的 row 中 ≥54% 都是 survivor；helper preservation 计算 = (preserved survivors in each window) / (total survivors triggered in that window)；candidate binary actuator 让 preserved=0 → preservation=0/N=0。**所有 4 个 window 都是 0.0** 是 candidate-level 的 binary-trigger 结构性结果，不是 v1 / v2 偶然 fail。

## 8. risk_score distribution shift

per-bucket risk_score（mean / median）对比（每个 bucket 用各自 run 的 risk_score）：

| bucket | v1_risk_score_mean | v1_risk_score_median | v2_risk_score_mean | v2_risk_score_median |
|---|---|---|---|---|
| A both | **0.7210** | 0.7242 | **0.6768** | 0.6570 |
| B v1_only | 0.6613 | 0.6418 | **0.5289** | 0.5498 |
| C v2_only | **0.4933** | 0.5032 | **0.6630** | 0.6682 |
| D neither | 0.4334 | 0.4221 | 0.4320 | 0.4256 |

观察：

- **A 子集**：v1 mean 0.72 / v2 mean 0.68 —— 都高于 0.60 阈值（自然，都触发）；v2 略低
- **B 子集**：v1 mean 0.66（高于阈值 → 触发），v2 mean 0.53（低于阈值 → 不触发）—— v2 把这些 row 重计算后 score 降到阈值之下；与 family 重新加权一致
- **C 子集**：v1 mean 0.49（低于阈值），v2 mean 0.66（高于阈值）—— v2 把这 9 条 row 推过阈值；这是 v2 唯一新增的 trigger 来源
- **D 子集**：v1 mean 0.43 / v2 mean 0.43 —— 两次几乎一致；候选共同标为低 risk

→ v2 的 risk_score 与 v1 在 A / D 上**高度相关**（0.72→0.68；0.43→0.43），在 B / C 上**有差异**（B 0.66→0.53；C 0.49→0.66）—— v2 family 重新加权主要影响**边界附近**的 row，没有改变 candidate 对核心高 / 低 risk 区域的判断。

## 9. per-window risk_score shift（triggered vs non-triggered mean）

| window | v1_triggered_mean | v2_triggered_mean | v1_nontriggered_mean | v2_nontriggered_mean |
|---|---|---|---|---|
| W1 | 0.645 | 0.611 | 0.410 | 0.431 |
| W2 | 0.676 | 0.645 | 0.468 | 0.431 |
| W3 | 0.660 | 0.680 | 0.424 | 0.466 |
| W4 | 0.708 | 0.681 | 0.444 | 0.446 |

观察：

- triggered_mean 跨 window：v1 0.645 ~ 0.708；v2 0.611 ~ 0.681 —— 两次都在 0.60 阈值附近，没有显著区分
- nontriggered_mean 跨 window：v1 0.41 ~ 0.47；v2 0.43 ~ 0.47 —— 持平
- **v2 没有改变 triggered / non-triggered 的整体分离度**；只是把边界附近的 row 重分配（B → not triggered；C → triggered）

## 10. feature family observations（descriptive only）

v2 records 中 `candidate.features_used` 含 8 family。从 v2 records 抽样观察（**不**给具体新参数 / 公式）：

| family | observed pattern（A 子集，N=88） |
|---|---|
| `trend_continuation_protection` | 在 A 子集中以负值（-0.2 / -0.4）出现的频率与 B / C / D 类似；没有特别集中在 survivor 上 |
| `peer_confirmation_strength` | A 子集中 `peer_5d_aligned_pct ≥ 0.50` 的 row 数与全集分布接近；damping 在 A 上没有显著效果 |
| `overextension_without_confirmation` | A 子集中**仍主要由这一项 push 上 high bucket**；A 子集 v2 mean composite 高（→ 0.68 sigmoid）主要由这一项贡献 |
| `reversal_pressure` | A 子集中大部分 row reversal_pressure=0（drawdown 不够大）；reversal 信号在 W2 / W4 zero-frequent |
| `regime_stability` | 多数 row monthly_max_abs_daily_return 在 0.03 ~ 0.07 之间 → regime_stability = 0；A 子集中没有显著正向贡献 |
| `monthly_shock_context` | 多数 row monthly_max < 0.07 → 全 0；shock 信号 ≈ 0 vs v1 monthly_shock 也 ≈ 0；H4 + Q6 的"删除 monthly_shock"假设有数据支持 |
| `trigger_support` | **整 526 条 records 全部 trigger_support ≥ 0.5**；v2 abstain 计数 = **0**；v2 的 abstain mode 在本次 run **从未激活** |
| `calibration_context` | 仅 descriptor；不参与 score |

> 关键观察：**v2 的 abstain mode 在本次 run 没有触发任何一次**（`v2 abstain rows: 0`）。trigger_support guard 设的 0.5 阈值过低（input 数据完整时 trigger_support=1.0），整个 abstain 设计在本数据上 inactive。这直接证伪了 v2 design 的核心新机制之一（H5 的"abstain reduces coverage"在本次 run 上**根本没发生**；v2 reduction 完全来自 family 重新加权，不是 abstain）。

只描述 pattern；**不**做 SHAP / 不优化 / 不反推系数 / 不给新参数。

## 11. hypothesis evaluation

| # | Hypothesis | 状态 | 数据支撑 |
|---|---|---|---|
| **H1** | v2 reduced trigger volume but not trigger quality | **supported** | total 136 → 97（−29%）；A 子集 pc_true_rate 0.591 仍高于 baseline；C 子集 pc_true_rate 0.333 改善但 N=9 太小 |
| **H2** | risk_score direction / calibration still not aligned with actual wrong-prediction risk | **supported** | A 子集 v1 mean 0.72 / v2 mean 0.68（高 score）但 pc_true_rate 0.59（这些反而是 survivor）；高 score → exclude 的语义与 outcome 反向 |
| **H3** | "trigger = exclude" actuator is too blunt | **partially_supported** | 数据一致：A 子集 88 cases 高 score 但 52 是 survivor；如有 warn / downgrade 中间档可减少 false_exclusion；但本数据无法直接证明改 actuator 一定能改善 |
| **H4** | features still classify market regime rather than prediction error | **supported** | A 子集（v1 v2 agreement zone）pc_true_rate **比 baseline 高 11pp** —— candidate 在 agreement zone 选中的是 high-momentum regime，那里 prediction 反而**更可能正确** |
| **H5** | abstain mode reduces coverage but does not protect survivors among triggered rows | **supported（plus 加强版）** | **v2 abstain 计数 = 0**；abstain mode 在本 run **从未激活**；v2 reduction 来源是 family 重新加权，不是 abstain；abstain "保护 survivor" 的设计完全 inactive |
| **H6** | v2 threshold 0.60 may be inappropriate but cannot be changed from this result directly | **inconclusive (by design)** | C 子集 v1 mean 0.49 v2 mean 0.66 —— 阈值 0.60 在 v1 / v2 决策边界；改阈值可改 trigger 数量但**不能由 baseline 反推**（永久禁止） |
| **H7** | continuous_smoothing signal may belong in review/explanation layer rather than exclusion candidate layer | **supported** | A 子集 pc_true_rate 0.591 > baseline 0.481 —— candidate 检测到的"高 risk regime"实际上是 momentum/outperform regime，是 regime classifier 的有效输出，但作为 exclusion candidate 反向；信号本身有结构（不全 random），但用错了方向 |

## 12. v3 vs abandon decision

### 12.1 数据对照 v3 launch review 条件（ALL of）

| # | 条件 | 实际 | 满足？ |
|---|---|---|---|
| 1 | 至少某 subset trigger correctness 显著优于 random / baseline | C 子集 pc_true_rate 0.333 < baseline 0.481（**优于** —— 33% < 48%），但 N=9 太小 | ⚠️ **borderline**（统计上不显著） |
| 2 | 能提出非参数化结构调整方向 | 可以提（如 risk_score 方向反转 / actuator 改 graded） | ✅ |
| 3 | 仍可保持 sidecar / read-only / non-production | ✅ | ✅ |
| 4 | 不需要改 adapter / helper / 主链 | "graded actuator"必须改 adapter；"flip 方向"虽不改 adapter 但语义颠倒已是 v3 的根本性重设计 | ❌ **否** |
| 5 | 不复制 v1 / v2 SEED / coefficient / threshold | ✅ | ✅ |

→ ALL of v3 条件**不满足**（条件 4 失败：意义结构性改善需改 adapter / helper / 主链；条件 1 borderline）。

### 12.2 数据对照 abandon 条件（ANY of）

| # | 条件 | 实际 | 满足？ |
|---|---|---|---|
| 1 | 所有 subset trigger 与 outcome 几乎独立 | A pc_true_rate 0.59（反向）；B 0.46；C 0.33（弱信号但 N=9）；D 0.46 —— 主要 buckets（A / B / D 共占 98.3%）都接近或反向 baseline | ✅ |
| 2 | triggered rows 在所有合理 subset 都主要是 survivor | A 子集 59% survivor；B 子集 46% survivor（≈ baseline）；C 子集 33% survivor（**唯一例外** but N=9） | ✅（除 C 之外） |
| 3 | 无法定义合理 non-binary action（不改 adapter） | 当前 adapter 仅接受 risk_score >= threshold → triggered=True；non-binary 必须改 adapter | ✅ |
| 4 | 改善必须改 adapter / helper / 主链 | H3 + 条件 4：graded / warn / downgrade 都需改 adapter | ✅ |
| 5 | continuous_smoothing 更适合作为 review / explanation layer | A 子集 candidate 一致检测到 high-momentum regime；该信号有结构（pc_true_rate 0.59 vs baseline 0.48 的反向相关）但作为 binary exclusion 反向；用作"标注 high-momentum regime"的 review/explanation 信号是合理的 | ✅ |

→ abandon 条件 ANY of 满足（5/5 都满足）。

### 12.3 决定

**`recommended_next_step = abandon_continuous_smoothing_candidate_layer`**

理由：

1. **A 子集结构性反向**：v1 + v2 在 16.7% 的 row 上一致触发，但这些 row 中 59% 是 survivor（高于 baseline 11pp）—— 这是 candidate-layer 的根本结构问题，不是参数问题
2. **abstain mode 完全 inactive**：v2 design 的核心新机制（abstain protect survivor）在本次 run 没有触发任何一次（trigger_support 全 ≥ 0.5）
3. **C 子集 9 条 row 的弱信号 N 太小**：统计上不构成 v3 design 的基础
4. **改善必须改 adapter / helper / 主链**：所有可能的 actuator 改进（graded / warn / downgrade / inverted）都需改 adapter，超出 candidate layer 边界
5. **continuous_smoothing 信号有结构但方向错**：A 子集检测到的 momentum regime 是 review / explanation layer 的合理候选，但作为 exclusion candidate 反向

> abandon **不**意味删除 v1 / v2 模块；它们作为已 merge 的 read-only diagnostic 保留；下一步是把 continuous_smoothing 的方向**重新定位**为 review / explanation layer 信号，而**不是** exclusion candidate。该重定位本身需要独立 launch review，不在本步骤范围。

## 13. no-go confirmations

逐项确认；本 review **全部未触发**：

| no-go | status |
|---|---|
| no threshold change | ✅ 未触发（v1 0.60 / v2 0.60 仍锁） |
| no v1/v2 parameter change | ✅ 未触发 |
| no retry | ✅ 未触发 |
| no sweep / grid search | ✅ 未触发 |
| no validation rerun | ✅ 未触发（仍使用 v1 `20260507_065417` + v2 `20260507_091823` baseline） |
| no raw output commit | ✅ 未触发（4 文件仍 untracked） |
| no DB write | ✅ 未触发 |
| no 2026 touch | ✅ 未触发（cutoff 未改；2026 范围未读） |
| no 3R-5 / 3R-6 unlock | ✅ 未触发；abandon 不解锁 3R-5 / 3R-6 |
| no auto-promotion | ✅ 未触发 |
| no `_PROTECTION_LAYER_CONNECTED` 翻 True | ✅ 未触发 |
| no 接 yfinance / requests / urllib / 任何网络 | ✅ 未触发 |
| no 接 trading API | ✅ 未触发 |
| no 改 wrapper / candidate v1 / candidate v2 / orchestrator v1 / orchestrator v2 / glue v1 / glue v2 / adapter / helper / labels builder / real provider 任一已 merge 模块 | ✅ 未触发 |
| no 改任何已 merge 测试 | ✅ 未触发 |
| no 用 baseline 反推 threshold / SEED | ✅ 未触发（hypothesis 全 descriptive；§12 决定仅是结构性判断） |
| no 把 fail 当系统错误 / 修复任何已 merge service | ✅ 未触发（§12 abandon ≠ pipeline bug） |
| no 把 review 写成可执行 sweep 脚本 | ✅ 未触发（仅 markdown report；inline read-only Python 用于统计，不留在 repo） |
| no 新增 `.py` 文件到 repo | ✅ 未触发 |

## 14. recommended next step

**`recommended_next_step = abandon_continuous_smoothing_candidate_layer`**

下一步必须：

1. **commit 本 review report**（独立 commit；message 形如 `docs(contract): Step 3R-3.3G1 v2 failure postmortem comparison review report`）
2. 写 **abandon decision checkpoint**：`tasks/step_3r3_h_abandon_continuous_smoothing_candidate_layer_decision_checkpoint.md`（或同类命名）—— 固化 abandon 决定 + 保留 v1 / v2 raw output / 已 merge 模块 / 全部 baseline / 不删除 / 不修改
3. 后续可考虑（**独立流程**，不在本步骤范围）：把 continuous_smoothing 信号**重定位**到 review / explanation layer（如 dashboard 标注 high-momentum regime / 显示 risk_score 给人类 review，但不进入 candidate exclusion 决策）—— 必须独立 launch review；不能在本步骤实施

下一步**不**允许：

- ❌ 直接进入 v3 launch review（abandon 已选择；v3 路径关闭）
- ❌ 直接进入 Step 3R-5 / 3R-6（v1 + v2 都 fail；abandon 不解锁）
- ❌ 直接修改 adapter / helper / 主链（即便 H3 / H7 提及；改动必须经独立 launch review）
- ❌ 删除 v1 / v2 模块（保留为 read-only diagnostic）
- ❌ 自动 promotion / 自动启 hard / Gate 5 / Gate 6 / `_PROTECTION_LAYER_CONNECTED`
- ❌ 调 v1 / v2 任一参数 / threshold / SEED / coefficient
- ❌ 用 v1 / v2 fail 数据反推任何具体新参数（任何阈值变更必须经独立 launch review）

## 15. 严守边界

本文是**纯 read-only review report markdown**：

- ❌ 没改任何代码（`services/*` / `ui/*` / `tests/*` / `scripts/*` 全部未触碰）
- ❌ 没改 DB schema / 没写 DB
- ❌ 没运行 replay
- ❌ 没**重新运行** real validation（baseline 仍是 v1 `20260507_065417` + v2 `20260507_091823`）
- ❌ 没运行 prepare-only smoke
- ❌ 没修改 v1 / v2 raw output json 任一字符
- ❌ 没改 `run_predict` / `predict.py` / `scanner.py` / `prediction_store.py` / `app.py`
- ❌ 没改 `services/regime_features_builder.py` / `regime_labels_builder.py` / `regime_validation_helper.py` / `continuous_smoothing_candidate.py`（v1）/ `continuous_smoothing_candidate_v2.py` / `replay_validation_record_adapter.py` / `historical_replay_training.py` / `real_regime_label_provider.py` / 任何 ui 模块 / 任何 builder
- ❌ 没改 `scripts/run_continuous_smoothing_validation.py`（v1 orchestrator）/ `run_real_continuous_smoothing_validation.py`（wrapper）/ `run_real_continuous_smoothing_validation_execute.py`（v1 glue）/ `run_continuous_smoothing_validation_v2.py`（v2 orchestrator）/ `run_real_continuous_smoothing_validation_execute_v2.py`（v2 glue）
- ❌ 没新增 `scripts/postmortem_*.py` / `tests/test_postmortem_*.py`（postmortem 全部 inline read-only Python，不留在 repo）
- ❌ 没改任何已 merge 测试
- ❌ 没改 04 / 05 / 07 任何 required 字段
- ❌ 没启用 `hard` / `forced_exclusion` / `anti_false_exclusion_triggered`
- ❌ 没接 `yfinance` / `requests` / 任何网络
- ❌ 没接 trading API / `longbridge` / `broker` / `paper_trade`
- ❌ 没让 `_PROTECTION_LAYER_CONNECTED` 翻 True
- ❌ 没让 `hard_gate_status.protection_layer_connected` 自动 pass
- ❌ 没改 `hard_exclusion_allowed` / `primary_blocker` 派生
- ❌ 没触碰 2026-01-01 之后 final-test range
- ❌ 没改 Step 3R-4 protocol thresholds（6 metric / 7 gate / 10 no-go）
- ❌ 没改 Step 3R-3.3 系列已 merge 文档 / 实施
- ❌ 没改 Step 2G-8D 系列文档或代码
- ❌ 没把 W4 / smoke / `logs/regime_validation/` / v1 raw output / v2 raw output / `logs/prediction_log.jsonl` / DB backup / `agent_loop.py` / `.claude/worktrees/` 任一 commit 进 main
- ❌ 没创建任何**新的** `logs/regime_validation/*` 子目录
- ❌ 没运行 `pytest`（本轮纯 read-only 分析；测试基线维持 commit `0a753c2` 时的 **2986 / 0 failed / 10 skipped**）
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*`
- ❌ 没调 v1 / v2 任一 threshold / SEED / coefficient / 工程默认
- ❌ 没用 v1 / v2 baseline 数据反推任何具体新参数
- ❌ 没让 v1 / v2 fail 触发 retry / sweep / grid search
- ❌ 没让 review 自动 promotion / 自动解锁 3R-5 / 3R-6
- ✅ 只新增 1 份 markdown review report 文档（本文件）
