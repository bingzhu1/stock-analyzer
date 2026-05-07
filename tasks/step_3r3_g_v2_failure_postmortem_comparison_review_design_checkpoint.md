# Step 3R-3.3G — V2 Failure Postmortem / Comparison Review Design Checkpoint

> 本文是 **checkpoint markdown** —— 不改代码、不写 DB、不重跑 replay / validation、不 commit / push、不接 trading API、不启 hard / forced、不改 required、不触碰 2026 final-test range、不 add `logs/regime_validation/` / W4 / smoke output / `logs/prediction_log.jsonl`、不处理 DB backup / stash / `.claude/worktrees/`、不调 v1 / v2 任一 threshold / SEED / coefficient / 工程默认、不 retry / 不 sweep / 不 auto-promotion、不进 3R-5 / 3R-6、不实施 overlap analysis / postmortem 脚本。

## 1. 当前完成状态

| 项 | 状态 | 来源 |
|---|---|---|
| v1 real W1-W4 validation single run + result checkpoint | ✅ 已 merge | output `logs/regime_validation/continuous_smoothing_v1_real_w1_w4_20260507_065417/`；commit `75f0ad5` |
| v1 postmortem report | ✅ 已 merge | commit `fc44bcf` |
| v2 candidate / execution path / single real run / result checkpoint | ✅ 已 merge | commits `ce8b81e` / `9192a5a` / `3de3cc5`；output `20260507_091823` |
| **v1 real validation fail baseline 已固定** | ✅ legal fail | report_status=fail；W1 false_exclusion_rate=1.0 |
| **v2 real validation fail baseline 已固定** | ✅ legal fail | report_status=fail；W1 false_exclusion_rate=1.0 |
| Step 3R-3.3G **v2 failure postmortem / comparison review design**（15 节、341 行） | ✅ **已 merge** | commit `f1fbdb5` |
| **本 checkpoint** —— 固定 review 目标 / sources / dimensions / hypotheses（H1-H7） / overlap plan / actuator semantic review / v3-vs-abandon criteria / output schema / no-go / 允许下一步 / 边界 | ⏳ **本文**（未 commit） | — |
| review 实施（A inline read-only / B 独立 read-only 脚本） | ❌ 尚未启动 | — |
| overlap analysis | ❌ 尚未运行 | — |
| review result checkpoint + 二选一 recommendation | ❌ 尚未启动 | — |

> v1 / v2 都 fail；review 实施仍未开始；本 checkpoint 只固化 review design 状态。

## 2. 当前 main 状态

- `main` 最新 commit：`f1fbdb5`
- commit message：`docs(contract): Step 3R-3.3G v2 failure postmortem comparison review design`
- 上游：`origin/main` 已同步（push 完成 `3de3cc5..f1fbdb5  main -> main`）
- 本步骤已 merge 文件：

| 路径 | 类型 | 行数 |
|---|---|---|
| `tasks/step_3r3_g_v2_failure_postmortem_comparison_review_design.md` | 新增 | 341（v2 failure review design 边界） |

测试基线：本步骤纯文档；测试基线维持 commit `0a753c2` 时的 **2986 / 0 failed / 10 skipped**。

| 项 | 是否触碰 |
|---|---|
| 改代码 | ❌ 否 |
| 改 v1 orchestrator / v1 glue / v1 candidate / candidate v2 / orchestrator v2 / glue v2 / adapter / helper / wrapper / real provider / labels builder | ❌ 否 |
| 改 DB schema / 写 DB | ❌ 否 |
| 跑 replay / 重跑 real validation | ❌ 否 |
| 实施 overlap analysis | ❌ 否 |
| 调 v1 / v2 任一 threshold / SEED / coefficient / 工程默认 | ❌ 否 |
| 接 yfinance / 网络 / trading API | ❌ 否 |
| 触碰 2026 final-test range | ❌ 否 |
| add `logs/regime_validation/` / W4 / smoke / DB backup / `agent_loop.py` / `.claude/worktrees/` / `logs/prediction_log.jsonl` | ❌ 否 |
| 进 3R-5 formula / 3R-6 simulator | ❌ 否 |
| 启 hard / forced / `_PROTECTION_LAYER_CONNECTED` | ❌ 否 |
| 实施 postmortem 脚本 / 新增 `.py` 文件 | ❌ 否 |

## 3. known result comparison

| metric | v1 | v2 | interpretation |
|---|---|---|---|
| `records_loaded` | 639 | 639 | same input（wrapper 共用） |
| `records_adapted` | 526 | 526 | same adapted count |
| `overall_status` | fail | fail | **no improvement** |
| `report_status` | fail | fail | **no improvement** |
| `worst_window` | W1 | W1 | **no improvement** |
| W1 `false_exclusion_rate` | 1.0000 | 1.0000 | **no improvement**（W1 触发的全是 survivor） |
| `survival_case_preservation`（all windows） | 0.0 / 0.0 / 0.0 / 0.0 | 0.0 / 0.0 / 0.0 / 0.0 | **structural issue unchanged** |
| triggered total | 136 | 97 | v2 more conservative（−29%） |
| `trigger_rate`（total） | 25.9% | 18.4% | v2 lower coverage |
| 7 gates | all fail | all fail | **no improvement** |
| `final_test_touched` | false | false | both safe（2026 unchanged） |
| W2 `false_exclusion_rate` | 0.5217 | 0.5385 | v2 worse +1.7pp |
| W3 `false_exclusion_rate` | 0.5000 | 0.6000 | v2 worse +10pp |
| W4 `false_exclusion_rate` | 0.5421 | 0.5641 | v2 worse +2.2pp |

> v2 没显著改善；多数 metric 持平或略差；survival_case_preservation 全 0.0 是 candidate-level 结构性问题，不是 v1 / v2 各自的偶然 fail。

## 4. review goals（8 问）

review 必须**回答以下 8 个 descriptive 问题**；本 checkpoint **不**给答案：

| # | 问题 |
|---|---|
| 1 | 为什么 v2 更保守，但 `survival_case_preservation` 仍为 **0.0**？ |
| 2 | 为什么 W2 / W3 / W4 `false_exclusion_rate` 反而**更差**（+1.7 ~ +10pp）？ |
| 3 | `risk_score = P̂(prediction wrong)` 的方向是否**仍然错**？ |
| 4 | `candidate_triggered = exclude/block` actuator semantic 是否有结构问题？ |
| 5 | trigger_support / abstain 是否只是减少触发，没有改善正确性？ |
| 6 | feature families 是否**仍主要描述 regime**，而不是 prediction-wrong probability？ |
| 7 | 是否应该进入 v3 launch review？ |
| 8 | 是否应该 abandon continuous_smoothing candidate layer？ |

> review 输出**不**包括：新 threshold / 新 SEED / 新 coefficient / 新 calibration 曲线 / 新 feature 公式 / 任何 sweep / 任何 retry。

## 5. read-only sources

仅读取以下文件（**只读，不修改，不 commit，不重新生成**）：

| 路径 | 用途 |
|---|---|
| `logs/regime_validation/continuous_smoothing_v1_real_w1_w4_20260507_065417/replay_validation_records.json` | v1 526 条 records |
| `logs/regime_validation/continuous_smoothing_v1_real_w1_w4_20260507_065417/regime_validation_report.json` | v1 overall_status / per_window_metrics / gate_status |
| `logs/regime_validation/continuous_smoothing_v2_real_w1_w4_20260507_091823/replay_validation_records.json` | v2 526 条 records |
| `logs/regime_validation/continuous_smoothing_v2_real_w1_w4_20260507_091823/regime_validation_report.json` | v2 per_window_metrics / gate_status |
| `tasks/step_3r3_3f_d_continuous_smoothing_v2_real_validation_result_checkpoint.md` | v2 result（已固化） |
| `tasks/step_3r3_3c_d1_candidate_postmortem_report.md` | v1 postmortem 5 hypothesis |

强制 read-only：

- ❌ **不**修改 raw json 任一字符
- ❌ **不** `git add` raw json（保持 untracked）
- ❌ **不**重新生成 raw json（不重跑 validation）
- ❌ **不**用 raw json 数据反推新参数
- ❌ **不**对 raw json 做任何统计 fitting / optimization / grid search

## 6. comparison dimensions（10 项）

postmortem 实施时**只产生 descriptive 数据**：

| # | 维度 | 来源 |
|---|---|---|
| 1 | per-window trigger count（v1 vs v2） | records.window + records.candidate_triggered |
| 2 | per-window `false_exclusion_rate`（v1 vs v2） | report.per_window_metrics（已计算，复述） |
| 3 | per-window `survival_case_preservation`（v1 vs v2） | report.per_window_metrics |
| 4 | triggered case correctness（v1 vs v2） | records.candidate_triggered + records.prediction_correct |
| 5 | v1 ∩ v2 triggered overlap | (analysis_date, prediction_for_date, window) 三元组 join |
| 6 | v2-only triggered cases | join 差集 |
| 7 | v1-only triggered cases | join 差集 |
| 8 | risk_score distribution shift（v1 vs v2 per-window quantile） | records.candidate.risk_score |
| 9 | feature family pattern on false exclusions（v2 8 family vs v1 5 feature on triggered+survival 子集） | records.candidate.features_used |
| 10 | abstain / non-triggered 效应（v2 abstain rows 在 v1 中状态） | v2 records `risk_bucket="abstain"` 的 row → v1 中查找 |

## 7. key hypothesis set（H1-H7）

review 提**问题**；**不**给具体新参数：

| # | Hypothesis |
|---|---|
| **H1** | v2 reduced trigger volume but **not trigger quality**：v2 把 marginal cases abstain 之后，剩下的 triggered rows 反而更纯 survivor → false_exclusion_rate 不降反升 |
| **H2** | risk_score direction / calibration **仍未对齐 outcome**：v2 锁定 `P̂(prediction wrong)`，但实证上高 score 触发的全是 `direction_correct=True` 的 row → 方向可能反，或 calibration 把 regime feature 当成 wrong-prediction signal |
| **H3** | actuator semantic **"trigger = exclude" 过于 blunt**：当前 adapter 把 trigger 等价于完全排除 prediction；是否应该存在 warn / downgrade-confidence / request-abstain 等中间动作 |
| **H4** | features **仍主要 classify market regime**，不是 prediction-wrong probability：v2 8 family 仍是 regime 描述特征；prediction error 信号没被显式建模 |
| **H5** | abstain mode 减少 coverage 但**没保护 survivors among triggered rows**：v2 abstain 主要排除"低支持度" row，没有 specifically 保护"高 prediction-correct 概率"row |
| **H6** | v2 threshold 0.60 may be inappropriate but **cannot be changed from this result directly**：阈值变更必须经独立 launch review；不能从 v1 / v2 fail 反推 |
| **H7** | continuous_smoothing 信号可能更适合 **review / explanation layer**，而**不是** exclusion candidate layer：把 score 用来"标注 high-uncertainty regime"而不是"决定 exclude" |

> 每条 hypothesis 都是 review 的**输入材料**；不附带"因此应改成 X"的处方。

## 8. overlap analysis plan

review 实施时通过 `(analysis_date, prediction_for_date, window)` 三元组 join v1 / v2 records → 4-cell 表：

| 类别 | 含义 | 估算（v1=136 / v2=97 triggered；total=526） |
|---|---|---|
| **A** | both triggered（v1 + v2 都 True） | ≤ min(136, 97) = ≤ 97 |
| **B** | v1 only（v1 True + v2 False） | 136 − A |
| **C** | v2 only（v1 False + v2 True） | 97 − A |
| **D** | neither（都 False） | 526 − A − B − C |

每类统计：

- `count`
- `prediction_correct=True` count / rate（survivor 比例）
- `prediction_correct=False` count / rate
- `survival_case` count / rate
- `actual_close_change` distribution（如可取）

要回答的问题：

- v2 是否删掉了 v1 的 **bad triggers**（v1 触发且 prediction_correct=False，正确 exclusion）？→ 看 B 中 `prediction_correct=False` rate
- v2 是否删掉了 v1 的 **useful triggers**（v1 triggered 中 v2 abstain 掉的）？→ 看 B 总比例
- v2-only triggers 是否比 v1-only **更差**（v2 新增的 trigger 中 survivor 比例是否更高）？→ 比较 C 中 `prediction_correct=True` rate vs B 中
- **neither** bucket（D）是否包含大量 candidate 应该捕捉的 wrong predictions？→ 看 D 中 `prediction_correct=False` rate；如果高 → candidate 错过了大量 true positive

## 9. actuator semantic review

| 项 | 当前状态 | review 问题 |
|---|---|---|
| current adapter semantic | `risk_score >= threshold` → `candidate_triggered=True` → record 标 `exclusion_would_block=True`（binary） | 是否合理？ |
| binary actuator | trigger 等价于 block；没有中间档 | 是否过 blunt？ |
| candidate score 含义 | `P̂(prediction wrong)`（v2 锁定） | 高 score 应做什么？ |
| 可选中间动作（仅讨论，**不**实施） | warn / downgrade-confidence / request-abstain | 是否需要新 schema field？ |
| 是否改 adapter | ❌ 否（本 checkpoint 不改 adapter）| review 仅记录"是否应该改"为开放问题 |
| 是否改 helper | ❌ 否（本 checkpoint 不改 helper）| 同上 |
| 改 adapter / helper 的边界 | 改 adapter / helper = 改 3R-4 protocol | 超出 candidate layer review 范围；如需，独立 launch review |

review 输出**不**包括：

- ❌ 具体新 actuator 公式
- ❌ 新 schema field 定义
- ❌ adapter / helper 修改建议（仅记录"是否应该"作为开放问题）
- ❌ 任何让 candidate 跳过 helper protocol 的方案

## 10. v3 vs abandon decision criteria

review 必须给出二选一推荐；判定标准：

### 10.1 进入 **v3 launch review** 的条件（ALL of）

| # | 条件 |
|---|---|
| 1 | overlap 分析显示 v1 / v2 至少一方在某 subset 的 trigger correctness 显著优于 random / baseline（即 triggered subset 中 `prediction_correct=False` rate 高于 526 总样本中的基础 rate） |
| 2 | 能提出**非参数化**结构调整方向（如重新定义 risk_score 含义 / 引入 outcome-aligned anchor / 改 actuator semantic / 重新选择 feature）—— **不**给具体参数 |
| 3 | 仍可保持 **sidecar / read-only / non-production** / 不写 DB / 不触碰 2026 |
| 4 | **不**需要改 adapter / helper / 主链 |
| 5 | **不**复制 v1 / v2 SEED / coefficient / threshold |

### 10.2 abandon **continuous_smoothing candidate layer** 的条件（ANY of）

| # | 条件 |
|---|---|
| 1 | 所有 subset trigger 与 outcome 几乎独立（trigger 与 `prediction_correct` 几乎无关） |
| 2 | triggered rows 在所有合理 subset 都**主要是** survivor（即 `survival_case_preservation` 在 candidate layer 无法降低） |
| 3 | 无法定义合理的 non-binary action 让 candidate 不再触发 false exclusion |
| 4 | 任何改善都**需要改** adapter / helper / 主链（超出 candidate layer 边界） |
| 5 | continuous_smoothing 信号更适合作为 **review / explanation layer**，而不是 candidate layer |

> 二选一**互斥**；review 必须明确选择并解释理由。

## 11. review output schema

`continuous_smoothing_v2_failure_review.v1`（10 字段）：

| 字段 | 类型 | 说明 |
|---|---|---|
| `schema_version` | str | `"continuous_smoothing_v2_failure_review.v1"` |
| `source_v1_run` | dict | `{"output_dir": "logs/regime_validation/continuous_smoothing_v1_real_w1_w4_20260507_065417", "result_checkpoint_commit": "75f0ad5", "postmortem_report_commit": "fc44bcf"}` |
| `source_v2_run` | dict | `{"output_dir": "logs/regime_validation/continuous_smoothing_v2_real_w1_w4_20260507_091823", "result_checkpoint_commit": "3de3cc5"}` |
| `comparison_summary` | dict | per-window v1 vs v2 metric 对比（复述 v2 result checkpoint）+ overlap 4-cell 表（A / B / C / D）+ 子集 correctness |
| `root_cause_hypotheses` | list[str] | 复述 §7 H1-H7；descriptive only；**不**含具体新参数 |
| `overlap_analysis` | dict | A/B/C/D 4-cell + 子集 correctness 实际数值（实施时填充） |
| `actuator_semantic_review` | dict | 复述 §9 当前 actuator + 开放问题；**不**给新 actuator 公式 |
| `v3_or_abandon_decision` | dict | 复述 §10 ALL-of v3 条件 + ANY-of abandon 条件 + review 选择的方向 + 理由 |
| `no_go_confirmations` | list[str] | 复述 §12 的 no-go；标注本 review 对每项的 status（全 ❌ 不触发） |
| `recommended_next_step` | str | 二选一：`"launch_continuous_smoothing_v3_design_review"` 或 `"abandon_continuous_smoothing_candidate_layer"`；**不**含 "tune_threshold" / "retry" / "sweep" / "auto_promotion" |

附：`unlock_3r5_3r6 = false`（永远）；`auto_promotion = false`（永远）。

## 12. no-go rules

review + postmortem + 决定阶段全程 no-go：

| # | 条件 |
|---|---|
| 1 | 调 v1 / v2 任一 `candidate_threshold` |
| 2 | 调 v1 SEED / v2 family 公式 / v2 工程默认 / v2 calibration |
| 3 | 调 6 metric / 7 gate threshold（3R-4 protocol 锁定） |
| 4 | sweep / grid search / hyperparameter optimization |
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
| 15 | 改 v1 已 merge 模块（wrapper / orchestrator v1 / candidate v1 / glue v1） |
| 16 | 改 v2 已 merge 模块（candidate v2 / orchestrator v2 / glue v2） |
| 17 | 改 adapter / helper / real provider / labels builder（3R-4 protocol） |
| 18 | 改任何已 merge 测试 |
| 19 | 在本 checkpoint 阶段实施 postmortem 分析 / 新增 `.py` 文件 |
| 20 | 把 review 写成可执行 sweep 脚本 / 用 v1 / v2 baseline 反推具体参数 |
| 21 | 把 fail 当 pipeline bug / 修复任何已 merge service |

## 13. 允许下一步

| # | 候选 | 状态 |
|---|---|---|
| 1 | **Step 3R-3.3G1 read-only comparison analysis**（在本 checkpoint 进 main 后启动） | ✅ 允许 |
| 2 | 选项 A：inline read-only 分析（直接在 markdown checkpoint 中 inline 读 4 raw json + 写 4-cell 表 + 子集 correctness；不新增 `.py` 文件） | ✅（推荐 N=4 cell 小规模） |
| 3 | 选项 B：独立 read-only 脚本 + isolation tests（`scripts/postmortem_v1_v2_comparison.py` + `tests/test_postmortem_v1_v2_comparison.py`；脚本仅读 4 raw json + 写 markdown report；isolation tests 锁 forbidden imports / 字符串扫） | ✅（适合更大规模 / 重复 postmortem） |
| 4 | 实施时**不调参**、**不重跑**、**不 commit raw output**、**不改任一已 merge 模块** | ✅ 强制 |
| 5 | review result checkpoint：`tasks/step_3r3_g1_v2_failure_postmortem_comparison_review_result_checkpoint.md`（命名待定） | ✅（review 完成后） |
| 6 | review **必须二选一**：`proceed_to_v3_launch_review` 或 `abandon_continuous_smoothing_candidate_layer` | ✅ 强制 |
| 7 | continuous_smoothing v3 launch review（独立流程） | ✅（仅在 review 选 v3 路径） |
| 8 | abandon redesign from candidate layer（独立流程） | ✅（仅在 review 选 abandon 路径） |
| 9 | wrapper / candidate v1 / candidate v2 / orchestrator v1 / orchestrator v2 / glue v1 / glue v2 / adapter / helper / real provider / labels builder 现有行为 | ❌ 不改（仅只读引用） |
| 10 | hard / required upgrade / Gate 5 / Gate 6 / `_PROTECTION_LAYER_CONNECTED` | ❌ 永久封禁 |
| 11 | 直接进入 Step 3R-5 / 3R-6 | ❌ 永久封禁 |

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
| auto-promotion | ❌ 永远不 |

## 15. 严守边界

本文是**纯 checkpoint markdown**：

- ❌ 没改任何代码（`services/*` / `ui/*` / `tests/*` / `scripts/*` 全部未触碰）
- ❌ 没改 DB schema / 没写 DB
- ❌ 没运行 replay
- ❌ 没**重新运行** real validation（baseline 仍是 v1 `20260507_065417` + v2 `20260507_091823`；本 checkpoint 不再次触发 run）
- ❌ 没运行 prepare-only smoke
- ❌ 没**实施 overlap analysis**（4-cell 表未填具体数值）
- ❌ 没读 v1 / v2 raw output json 任一字节（仅引用 path / 复述 result checkpoint + postmortem 已固化字段）
- ❌ 没修改 v1 / v2 raw output json
- ❌ 没改 `run_predict` / `predict.py` / `scanner.py` / `prediction_store.py` / `app.py`
- ❌ 没改 `services/regime_features_builder.py` / `regime_labels_builder.py` / `regime_validation_helper.py` / `continuous_smoothing_candidate.py`（v1） / `continuous_smoothing_candidate_v2.py` / `replay_validation_record_adapter.py` / `historical_replay_training.py` / `real_regime_label_provider.py` / 任何 ui 模块 / 任何 builder
- ❌ 没改 `scripts/run_continuous_smoothing_validation.py`（v1 orchestrator）/ `run_real_continuous_smoothing_validation.py`（wrapper）/ `run_real_continuous_smoothing_validation_execute.py`（v1 glue）/ `run_continuous_smoothing_validation_v2.py`（v2 orchestrator）/ `run_real_continuous_smoothing_validation_execute_v2.py`（v2 glue）
- ❌ 没新增 v3 任何代码 / 任何测试 / 任何 postmortem 脚本
- ❌ 没改任一已 merge 测试
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
- ❌ 没改 Step 2G-8D 系列文档 / 代码
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
- ✅ 只新增 1 份 markdown checkpoint 文档（本文件）
