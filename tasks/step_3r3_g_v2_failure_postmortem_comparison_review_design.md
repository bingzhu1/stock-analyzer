# Step 3R-3.3G — V2 Failure Postmortem / Comparison Review Design

> 本文是 **design only** —— 不改代码、不写 DB、不重跑 replay / validation、不 commit / push、不接 trading API、不启 hard / forced、不改 required、不触碰 2026 final-test range、不 add `logs/regime_validation/` / W4 / smoke output / `logs/prediction_log.jsonl`、不处理 DB backup / stash / `.claude/worktrees/`、不调 v1 / v2 任一 threshold / SEED / coefficient / 工程默认、不 retry / 不 sweep / 不 auto-promotion、不进 3R-5 / 3R-6、不实施 postmortem 脚本。

## 1. 背景

| 项 | 状态 | 来源 |
|---|---|---|
| v1 real W1-W4 validation single run + result checkpoint | ✅ 已 merge | output `logs/regime_validation/continuous_smoothing_v1_real_w1_w4_20260507_065417/`；commit `75f0ad5` |
| v1 postmortem report | ✅ 已 merge | commit `fc44bcf` |
| v2 candidate / execution path / single real run / result checkpoint | ✅ 已 merge | commits `ce8b81e` / `9192a5a` / output `20260507_091823` / `3de3cc5` |
| **v1 已 fail** | ❌ legal fail | report_status=fail；W1 false_exclusion_rate=1.0 |
| **v2 已 fail** | ❌ legal fail | report_status=fail；W1 false_exclusion_rate=1.0 |
| v2 execution path | ✅ 成功 | exit 0；4 文件齐；DB unchanged；13/13 acceptance |
| v2 比 v1 更保守 | ✅ | trigger total 136 → 97（−29%） |
| v2 解决 core problem？ | ❌ | survival_case_preservation 全 0.0 持平；W1 false_exclusion 仍 1.0；7 gate 全 fail |
| **本文**（v2 failure postmortem / comparison review **design only**；不实施分析、不改代码、不调参） | ⏳ design 中（未 commit） | — |

本文位置：

- 已 merge 链：v2 result checkpoint（`3de3cc5`）→ **本 design** → design checkpoint → postmortem 实施（read-only inline / 独立 read-only 脚本）→ postmortem result checkpoint → （二选一）v3 launch review 或 abandon candidate layer。
- 本文范围：**纯 markdown design**，定义 review 目标 / hypothesis / overlap analysis plan / actuator semantic review / v3-vs-abandon decision criteria；**不**给具体新参数 / 新 calibration 曲线 / 新 feature 公式；**不**实施分析。

## 2. 已知结果（v1 vs v2）

| metric | v1 | v2 | interpretation |
|---|---|---|---|
| `records_loaded` | 639 | 639 | same input（wrapper 共用） |
| `records_adapted` | 526 | 526 | same adapted count |
| `overall_status` | fail | fail | **no improvement** |
| `report_status` | fail | fail | **no improvement** |
| `worst_window` | W1 | W1 | **no improvement** |
| W1 `false_exclusion_rate` | 1.0000 | 1.0000 | flat（W1 触发的都是 survivor） |
| W2 `false_exclusion_rate` | 0.5217 | 0.5385 | v2 worse +1.7pp |
| W3 `false_exclusion_rate` | 0.5000 | 0.6000 | v2 worse +10pp |
| W4 `false_exclusion_rate` | 0.5421 | 0.5641 | v2 worse +2.2pp |
| `survival_case_preservation`（all windows） | 0.0 / 0.0 / 0.0 / 0.0 | 0.0 / 0.0 / 0.0 / 0.0 | **结构性问题持平** |
| triggered total | 136 | 97 | v2 −29%（更保守） |
| trigger_rate（total） | 25.9% | 18.4% | v2 lower |
| W1 triggered | 2 | 1 | v2 −50%（min_sample 更糟） |
| W2 triggered | 23 | 13 | v2 −43% |
| W3 triggered | 4 | 5 | v2 +25%（绝对小） |
| W4 triggered | 107 | 78 | v2 −27% |
| 7 gates | all fail | all fail | **no improvement** |
| `final_test_touched` | false | false | both safe |

> v2 没显著改善；多数 metric 持平或略差；survival_case_preservation 全 0.0 是 **candidate-level 结构性问题**，不是 v1 / v2 各自的偶然 fail。

## 3. review 目标（8 问）

review **回答以下 8 个 descriptive 问题**；本文**不**给答案：

| # | 问题 | 关键变量 |
|---|---|---|
| 1 | 为什么 v2 更保守，但 `survival_case_preservation` 仍为 **0.0**？ | candidate triggered rows 是否仍**全部**是 survivor；v2 abstain 把 marginal cases 排除后，剩下的 triggered rows 是否反而更"纯 survivor" |
| 2 | 为什么 W2 / W3 / W4 `false_exclusion_rate` 反而**更差**（+1.7 ~ +10pp）？ | v2 abstain 把哪些 case 排除了；这些 case 是否本来是 v1 的 true-positive（正确 exclusion） |
| 3 | `risk_score = P̂(prediction wrong)` 方向是否**仍然错**？ | 高 v2 risk_score 的 row 实际上 `direction_correct` 比例是高还是低；如果高 → 方向反 |
| 4 | `candidate_triggered = exclude/block` actuator semantic 是否有结构问题？ | 当前 adapter 把 trigger 等价于"完全排除 prediction"；是否应该有 warn / downgrade-confidence / request-abstain 等中间动作 |
| 5 | trigger_support / abstain 是否只是减少触发，没有改善正确性？ | abstain 增加之后 false_exclusion_rate 没降反升 → abstain 选择性是否系统偏向把 true-positive 排除掉 |
| 6 | feature families 是否**仍主要描述 regime**，而不是 prediction-wrong probability？ | per-window feature mean / range 是否与 outcome `direction_correct` 几乎无关 |
| 7 | 是否应该进入 v3 launch review？ | review 判定 v1 / v2 是否仍含可救信号 |
| 8 | 是否应该 abandon continuous_smoothing candidate layer？ | review 判定该方向是否结构性失败 |

> review 输出**不**包括：新 threshold / 新 SEED / 新 coefficient / 新 calibration 曲线 / 新 feature 公式 / 任何 sweep / 任何 retry。

## 4. read-only sources

仅读取以下文件（**只读，不修改，不 commit，不重新生成**）：

| 路径 | 用途 |
|---|---|
| `logs/regime_validation/continuous_smoothing_v1_real_w1_w4_20260507_065417/replay_validation_records.json` | v1 526 条 records（per-row：window / candidate_triggered / candidate / direction_correct 派生 / survival_case） |
| `logs/regime_validation/continuous_smoothing_v1_real_w1_w4_20260507_065417/regime_validation_report.json` | v1 overall_status / per_window_metrics / gate_status |
| `logs/regime_validation/continuous_smoothing_v2_real_w1_w4_20260507_091823/replay_validation_records.json` | v2 526 条 records |
| `logs/regime_validation/continuous_smoothing_v2_real_w1_w4_20260507_091823/regime_validation_report.json` | v2 per_window_metrics / gate_status |
| `tasks/step_3r3_3f_d_continuous_smoothing_v2_real_validation_result_checkpoint.md` | v2 result（已固化字段） |
| `tasks/step_3r3_3c_d1_candidate_postmortem_report.md` | v1 postmortem 5 hypothesis（H1-H5） |
| `tasks/step_3r3_f_continuous_smoothing_v2_candidate_design.md` | v2 candidate design + 8 family + risk_score 语义锁定 |
| `services/continuous_smoothing_candidate_v2.py` | v2 family 计算 / bucket 边界（仅读，不改） |

强制 read-only：

- ❌ **不**修改 raw json 任一字符
- ❌ **不** `git add` raw json（保持 untracked）
- ❌ **不**重新生成 raw json（不重跑 validation）
- ❌ **不**用 raw json 数据反推新 threshold / 新 SEED / 新 calibration / 新 feature 公式
- ❌ **不**对 raw json 做任何统计 fitting / optimization / grid search

## 5. comparison dimensions（10 项）

postmortem 实施步骤**只产生 descriptive 数据**：

| # | 维度 | 来源 |
|---|---|---|
| 1 | per-window trigger count（v1 vs v2） | records.window + records.candidate_triggered |
| 2 | per-window `false_exclusion_rate`（v1 vs v2） | report.per_window_metrics（已计算，复述） |
| 3 | per-window `survival_case_preservation`（v1 vs v2） | report.per_window_metrics（同上） |
| 4 | triggered case correctness（v1 vs v2） | records.candidate_triggered + records.prediction_correct（adapter 派生） |
| 5 | v1 ∩ v2 triggered overlap（同一 (analysis_date, window) row 在两次 run 中是否都触发） | 通过 (analysis_date, prediction_for_date, window) 三元组 join records 集合 |
| 6 | v2-only triggered cases（v2 触发而 v1 未触发） | join 差集 |
| 7 | v1-only triggered cases（v1 触发而 v2 未触发） | join 差集 |
| 8 | risk_score distribution shift（v1 vs v2 per-window quantile） | records.candidate.risk_score |
| 9 | feature family pattern on false exclusions（v2 8 family vs v1 5 feature 在 trigger=True + survival=True 子集上的 mean / range） | records.candidate.features_used |
| 10 | abstain / non-triggered 效应（v2 abstain rows 在 v1 中状态） | v2 records 中 candidate.risk_bucket="abstain" 的 row → 在 v1 records 中查找同 row 的 candidate_triggered |

## 6. key hypothesis set（7 项）

review 提**问题**；**不**给具体新参数：

| # | Hypothesis | 关联 v1 postmortem |
|---|---|---|
| **H1** | v2 reduced trigger volume but **not trigger quality**：v2 把 marginal cases abstain 掉之后，剩下的 triggered rows 反而**更纯** survivor → false_exclusion_rate 不降反升 | 与 v1 H2（features 是 regime classifier）的延伸 |
| **H2** | risk_score direction / calibration **仍未对齐 outcome**：v2 锁定 `risk_score = P̂(prediction wrong)`，但实证上高 score 触发的全是 `direction_correct=True` 的 row → 方向可能反，或 calibration 把 regime feature 当成 wrong-prediction signal | v1 H3（极性可能颠倒）持续 |
| **H3** | actuator semantic **"trigger = exclude" 过于 blunt**：当前 adapter 把 trigger 等价于完全排除 prediction；是否应该存在 warn / downgrade-confidence / request-abstain 等中间动作，让 candidate 不必"全或无"地承担 binary 决定 | 新假设；本次 review 引入 |
| **H4** | features **仍主要 classify market regime**，不是 prediction-wrong probability：v2 8 family（trend_continuation / peer / overextension / reversal / regime_stability / monthly_shock / trigger_support / calibration_context）仍是 regime 描述特征；prediction error 信号没被显式建模 | v1 H2 升级 |
| **H5** | abstain mode 减少 coverage 但**没保护 survivors among triggered rows**：v2 abstain 主要把"低支持度"row 排除，没有 specifically 保护"高 prediction-correct 概率"row | 与 v1 H4 + H5（damping 失效 + 缺 calibration）的延伸 |
| **H6** | v2 threshold lock 0.60 may be inappropriate but **cannot be changed from this result directly**：阈值变更必须经独立 launch review；不能从 v1 / v2 fail 反推 | 与 v1 §11 一致；v2 仍 honor |
| **H7** | continuous_smoothing 的核心信号可能更适合 **review / explanation layer**，而**不是** exclusion candidate layer：把 score 用来"标注 high-uncertainty regime"而不是"决定 exclude" | 新假设；引入 v3-vs-abandon 决定 |

> 每条 hypothesis 都是给未来 review 的**输入材料**，**不**附带"因此应改成 X"的处方。

## 7. overlap analysis plan

postmortem 实施时分析（**descriptive 4-cell 表 + 子集统计**）：

### 7.1 总体 overlap 矩阵

| 类别 | 含义 | 估算（依据 v1=136 / v2=97） |
|---|---|---|
| **both triggered**（A） | 同一 (as_of_date, prediction_for_date, window) 在 v1 + v2 都 triggered=True | ≤ min(136, 97) = ≤ 97 |
| **v1 only triggered**（B） | v1 触发 + v2 未触发 | 136 − A |
| **v2 only triggered**（C） | v1 未触发 + v2 触发 | 97 − A |
| **neither**（D） | 都未触发 | 526 − (A + B + C) |

> 实施时通过 `(analysis_date, prediction_for_date, window)` 三元组 join 两次 run 的 records；本文不预算 A 的具体值。

### 7.2 子集 correctness 分析

对每个类别（A / B / C / D）统计：

| 字段 | 含义 |
|---|---|
| `prediction_correct=True` count | 该类别中"真 survivor"数量 |
| `prediction_correct=False` count | 该类别中"真该 exclude"数量 |
| `prediction_correct=True` rate | 该类别中 survivor 比例 |

postmortem 应回答：

- A（both triggered）：survivor 比例多高？（这是两次 run 共同误判的 cases）
- B（v1 only）：v2 abstain 掉了哪些 v1 触发的 row？是否包括 v1 的 true-positive（应排除的 row）？如果 B 中 `prediction_correct=False` 比例高 → v2 abstain 把 v1 的正确触发去掉了 → 这是 v2 在 §3 Q2 上恶化的直接原因
- C（v2 only）：v2 新引入的 trigger 中 survivor 比例多高？是否高于 v1 平均？
- D（neither）：basal 比例

### 7.3 实施 form

| 选项 | 描述 |
|---|---|
| A. inline read-only 分析 | 直接在 markdown checkpoint 中 inline 读 4 个 raw json + 写 4-cell 表 + descriptive 子集 mean；不新增 .py 文件 |
| B. 独立 read-only 脚本 | 新增 `scripts/postmortem_v1_v2_comparison.py` + `tests/test_postmortem_v1_v2_comparison.py`；脚本仅读 4 raw json + 写 markdown report；isolation tests 锁 forbidden imports / 字符串扫 |

> 本 design 不强制 A / B；postmortem 实施步骤再选。两种方式都**不**调 threshold / 任一参数；都**不**重跑 validation；都**不** commit raw output；都**不**修改 v1 / v2 raw json。

## 8. actuator semantic review

| 项 | 当前状态 | review 问题 |
|---|---|---|
| current adapter semantic | `risk_score >= threshold` → `candidate_triggered=True` → record 标 `exclusion_would_block=True` → helper 视作"candidate 想 exclude 这条 prediction" | 是否合理？ |
| binary actuator | trigger 等价于 block；没有中间档 | 是否过 blunt？ |
| candidate score 含义 | `P̂(prediction wrong)` | 高 score 应做什么？ |
| 可选中间动作（仅讨论，**不**实施） | warn / downgrade-confidence / request-abstain | 这些动作是否需要新 schema field？ |
| adapter 是否需要改 | ❌ 否（本 review 不改 adapter） | review 仅记录"是否应该改"为开放问题 |
| helper 是否需要改 | ❌ 否（本 review 不改 helper） | 同上 |
| 改 adapter / helper 的边界 | 改 adapter / helper = 改 3R-4 protocol | 超出 candidate layer review 范围；如需，独立 launch review |

review 输出**不**包括：

- ❌ 具体新 actuator 公式
- ❌ 新 schema field 定义
- ❌ adapter / helper 修改建议（仅记录"是否应该"作为开放问题，由独立流程决定）
- ❌ 任何会让 candidate 跳过 helper protocol 的方案

## 9. v3 vs abandon decision criteria

review 必须给出二选一推荐；判定标准：

### 9.1 进入 **v3 launch review** 的条件

ALL of：

| # | 条件 |
|---|---|
| 1 | overlap 分析显示 v1 / v2 至少有一方在某 subset（如 W4 high-trigger regime）的 trigger correctness 显著优于 random（survivor 比例 < adapter baseline） |
| 2 | 能提出**非参数化**结构调整方向（如重新定义 risk_score 含义 / 引入 outcome-aligned anchor / 改 actuator semantic / 重新选择 feature）—— **不**给具体参数 |
| 3 | 能继续保持 sidecar / read-only / non-production / 不写 DB / 不触碰 2026 |
| 4 | v3 设计能避免直接复制 v1 / v2 SEED / coefficient / threshold |
| 5 | v3 能在 candidate layer 解决问题，**不**需要改 adapter / helper / 主链 |

### 9.2 abandon **continuous_smoothing candidate layer** 的条件

ANY of：

| # | 条件 |
|---|---|
| 1 | overlap 分析显示 v1 / v2 在所有 subset 都只是在筛 regime，**不是**在筛 prediction error（即 trigger 与 outcome `direction_correct` 几乎独立） |
| 2 | triggered rows 在所有合理 subset 都**全部**是 survivor（即 `survival_case_preservation` 在 candidate layer 无法降低）|
| 3 | 无法定义合理的 non-hard / non-binary action 让 candidate 不再触发 false exclusion |
| 4 | 任何改善都需要改 adapter / helper / 主链（超出 candidate layer 边界） |

> 二选一**互斥**；review 必须明确选择并解释理由。

## 10. no-go rules（20 项）

review + postmortem + 决定阶段全程 no-go：

| # | 条件 |
|---|---|
| 1 | 调 v1 / v2 任一 `candidate_threshold` |
| 2 | 调 v1 SEED / v2 family 公式 / v2 工程默认 |
| 3 | 调 6 metric / 7 gate threshold（3R-4 protocol 锁定） |
| 4 | sweep / grid search / hyperparameter optimization 在 v1 / v2 baseline 上 |
| 5 | retry-until-pass |
| 6 | 重新跑 validation（v1 或 v2） |
| 7 | 进入 Step 3R-5 formula |
| 8 | 进入 Step 3R-6 simulator |
| 9 | 启 hard / forced / `anti_false_exclusion_triggered` |
| 10 | 让 `_PROTECTION_LAYER_CONNECTED` 翻 True |
| 11 | 改 04 / 05 / 07 required |
| 12 | 触碰 2026 final-test range |
| 13 | commit raw output（v1 或 v2 的 `logs/regime_validation/<TS>/`） |
| 14 | 接 yfinance / requests / 任何网络 / trading API |
| 15 | 改 v1 已 merge 模块（wrapper / orchestrator v1 / candidate v1 / glue v1）|
| 16 | 改 v2 已 merge 模块（candidate v2 / orchestrator v2 / glue v2） |
| 17 | 改 adapter / helper / real provider / labels builder（3R-4 protocol） |
| 18 | 改任何已 merge 测试 |
| 19 | 在本 design 阶段实施 postmortem 分析 / 新增 `.py` 文件 |
| 20 | 把 review 写成可执行 sweep 脚本 / 用 v1 / v2 baseline 反推具体参数 |

## 11. review output schema

设计 review report schema：`continuous_smoothing_v2_failure_review.v1`（10 字段）：

| 字段 | 类型 | 说明 |
|---|---|---|
| `schema_version` | str | `"continuous_smoothing_v2_failure_review.v1"` |
| `source_v1_run` | dict | `{"output_dir": "logs/regime_validation/continuous_smoothing_v1_real_w1_w4_20260507_065417", "result_checkpoint_commit": "75f0ad5", "postmortem_report_commit": "fc44bcf"}` |
| `source_v2_run` | dict | `{"output_dir": "logs/regime_validation/continuous_smoothing_v2_real_w1_w4_20260507_091823", "result_checkpoint_commit": "3de3cc5"}` |
| `comparison_summary` | dict | per-window v1 vs v2 metric 对比表（复述 v2 result checkpoint §9-11）；overlap 4-cell 表（A / B / C / D）+ 子集 correctness |
| `root_cause_hypotheses` | list[str] | 复述 §6 H1-H7；descriptive only；**不**含具体新参数 |
| `overlap_analysis_plan` | dict | 复述 §7 实施方案（A inline / B 独立脚本）+ 4-cell 表结构 |
| `actuator_semantic_review` | dict | 复述 §8 当前 actuator + 开放问题；**不**给新 actuator 公式 |
| `v3_or_abandon_decision_criteria` | dict | 复述 §9 ALL-of v3 条件 + ANY-of abandon 条件 |
| `no_go_confirmations` | list[str] | 复述 §10 的 20 项 no-go；标注本 review 对每项的 status（全 ❌ 不触发） |
| `recommended_next_step` | str | 二选一：`"launch_continuous_smoothing_v3_design_review"` 或 `"abandon_continuous_smoothing_candidate_layer"`；**不**含 "tune_threshold" / "retry" / "sweep" / "auto_promotion" |
| `unlock_3r5_3r6` | bool | **永远 false** |
| `auto_promotion` | bool | **永远 false** |

## 12. acceptance criteria

review 设计完成标准（13 项）：

| # | 标准 |
|---|---|
| 1 | 能解释 v2 为什么更保守但仍 fail（H1 / H5） |
| 2 | 能指定 overlap analysis 怎么做（§7 4-cell + 子集 correctness） |
| 3 | 能明确 risk_score / actuator semantic 的审查点（§8） |
| 4 | 能给出 v3 vs abandon 的判定标准（§9 ALL-of / ANY-of） |
| 5 | 能产出 review report schema（§11，10 字段） |
| 6 | 能列出 7 项 hypothesis（§6） |
| 7 | 能列出 10 项 comparison dimensions（§5） |
| 8 | **不**产生任何新 threshold（具体值） |
| 9 | **不**产生任何新 SEED / coefficient / family 公式 |
| 10 | **不**产生任何新 calibration 曲线 / actuator 公式 |
| 11 | **不**运行任何新 validation |
| 12 | **不**修改代码 / DB / raw output |
| 13 | **不** commit raw json / 不修改 v1 / v2 `output_dir` 任一文件 |

## 13. recommended_next_step

**`write_v2_failure_postmortem_comparison_review_checkpoint`**

| 含义 | 状态 |
|---|---|
| 只允许进入 review **design checkpoint**（独立 markdown） | ✅ |
| 允许直接进入 review **实施**（postmortem analysis） | ❌ 否（必须先过 design checkpoint） |
| 允许直接进入 v3 launch review / abandon | ❌ 否（必须先过 review 实施 + result checkpoint） |
| 允许直接进入 Step 3R-5 / 3R-6 | ❌ 否（永久 block；v1 / v2 fail） |
| 允许 review 阶段提具体新 threshold / 新 family / 新 actuator 公式 | ❌ 永久禁止；具体设计在 v3 design 阶段（如 review 选择 v3 路径） |
| 允许 review 阶段实施 postmortem | ❌ 否；本 design 是 review 的设计；实施在后续步骤 |

## 14. 与 3R-5 / 3R-6 关系

| 关系 | 状态 |
|---|---|
| v1 / v2 都 fail | ✅；fail 阻止 promotion |
| 当前是否 block 3R-5 formula | ✅ 是 |
| 当前是否 block 3R-6 simulator | ✅ 是 |
| 本 review 是否解锁 3R-5 / 3R-6 | ❌ **永远不**；review 仅产出"是否进 v3 / abandon"决定 |
| v3 launch review pass 是否解锁 3R-5 / 3R-6 | ❌ 否；仅解锁 v3 design + impl + validation |
| v3 single real run pass 是否解锁 3R-5 / 3R-6 | ❌ 否；只允许进入新一轮 3R-5 launch review |
| v3 single real run pass 是否自动启 hard / Gate 5 / Gate 6 / `_PROTECTION_LAYER_CONNECTED` | ❌ **永远不** |
| 3R-5 / 3R-6 启动条件 | 必须先：v3 launch review pass → v3 design + checkpoint → v3 impl + tests → v3 single real run → v3 result checkpoint → **新一轮** 3R-5 launch review pass（或 review 选 abandon → 完全 reset 到 candidate layer） |

## 15. 严守边界

本文是**纯 design markdown**：

- ❌ 没改任何代码（`services/*` / `ui/*` / `tests/*` / `scripts/*` 全部未触碰）
- ❌ 没改 DB schema / 没写 DB
- ❌ 没运行 replay
- ❌ 没**重新运行** real validation（baseline 仍是 v1 `20260507_065417` + v2 `20260507_091823`；本 design 不再次触发 run）
- ❌ 没运行 prepare-only smoke
- ❌ 没读 v1 / v2 raw output json 任一字节（仅引用 path / 复述 result checkpoint + postmortem 已固化字段）
- ❌ 没修改 v1 / v2 raw output json
- ❌ 没改 `run_predict` / `predict.py` / `scanner.py` / `prediction_store.py` / `app.py`
- ❌ 没改 `services/regime_features_builder.py` / `regime_labels_builder.py` / `regime_validation_helper.py` / `continuous_smoothing_candidate.py`（v1） / `continuous_smoothing_candidate_v2.py` / `replay_validation_record_adapter.py` / `historical_replay_training.py` / `real_regime_label_provider.py` / 任何 ui 模块 / 任何 builder
- ❌ 没改 `scripts/run_continuous_smoothing_validation.py`（v1 orchestrator）/ `run_real_continuous_smoothing_validation.py`（wrapper）/ `run_real_continuous_smoothing_validation_execute.py`（v1 glue）/ `run_continuous_smoothing_validation_v2.py`（v2 orchestrator）/ `run_real_continuous_smoothing_validation_execute_v2.py`（v2 glue）
- ❌ 没改任何已 merge 测试
- ❌ 没新增 v3 任何代码 / 任何测试 / 任何 postmortem 脚本
- ❌ 没改 04 / 05 / 07 任何 required 字段
- ❌ 没启用 `hard` / `forced_exclusion` / `anti_false_exclusion_triggered`
- ❌ 没接 `yfinance` / `requests` / 任何网络
- ❌ 没接 trading API / `longbridge` / `broker` / `paper_trade`
- ❌ 没让 `_PROTECTION_LAYER_CONNECTED` 翻 True
- ❌ 没让 `hard_gate_status.protection_layer_connected` 自动 pass
- ❌ 没改 `hard_exclusion_allowed` / `primary_blocker` 派生
- ❌ 没触碰 2026-01-01 之后 final-test range
- ❌ 没改 Step 3R-4 protocol thresholds（6 metric / 7 gate / 10 no-go）
- ❌ 没改 Step 3R-3.3 / 3R-3.3A / 3R-3.3B / 3R-3.3C 系列 / 3R-3.3C-D / 3R-3.3E / 3R-3.3F 系列已 merge 文档 / 实施
- ❌ 没改 Step 2G-8D / 8D.1A / 8D.2 / 8D.3 / 8D.4 文档或代码
- ❌ 没把 W4 / smoke / `logs/regime_validation/` / v1 raw output / v2 raw output / `logs/prediction_log.jsonl` / DB backup / `agent_loop.py` / `.claude/worktrees/` 任一 commit 进 main
- ❌ 没创建任何**新的** `logs/regime_validation/*` 子目录
- ❌ 没运行 `pytest`（本轮纯文档；测试基线维持 commit `0a753c2` 时的 **2986 / 0 failed / 10 skipped**）
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*`
- ❌ 没调 v1 / v2 任一 threshold / SEED / coefficient / 工程默认
- ❌ 没用 v1 / v2 baseline 数据反推任何参数
- ❌ 没让 v1 / v2 fail 触发 retry / sweep / grid search
- ❌ 没让 review 自动 promotion / 自动解锁 3R-5 / 3R-6
- ❌ 没实施 postmortem 分析
- ❌ 没真实运行 v1 / v2 / v3 W1-W4 validation
- ❌ 没 monkey-patch
- ✅ 只新增 1 份 markdown design 文档（本文件）
