# Step 3R-3.3C-D — Candidate Postmortem Design

> 本文是 **design only** —— 不改代码、不写 DB、不重跑 replay / validation、不 commit / push、不接 trading API、不启 hard / forced、不改 required、不触碰 2026 final-test range、不 add `logs/regime_validation/` / W4 / smoke output / `logs/prediction_log.jsonl`、不处理 DB backup / stash / `.claude/worktrees/`。

## 1. 背景

| 项 | 状态 | 来源 |
|---|---|---|
| Step 3R-3.3C real W1-W4 validation | ✅ 已运行（一次） | execution glue commit `7812b10`；output `logs/regime_validation/continuous_smoothing_v1_real_w1_w4_20260507_065417/` |
| Step 3R-3.3C real validation result checkpoint | ✅ 已 merge | commit `75f0ad5` |
| execution pipeline（wrapper / provider / orchestrator / candidate / adapter / helper / glue） | ✅ 全部通过 | exit 0 / 4 文件齐 / DB unchanged / 13/13 acceptance |
| candidate `continuous_smoothing_v1` | ❌ **fail**（legal fail） | W1 false_exclusion_rate=1.0；7 gate 全 fail |
| **本文** —— 设计 postmortem / candidate review；只读结果，不改代码、不调参、不重跑 | ⏳ design 中（未 commit） | — |

本文位置：

- 已 merge 链：3R-3.3C result checkpoint（`75f0ad5`）→ **本 design** → design checkpoint → postmortem 实施（read-only inline 分析或独立 read-only 脚本）→ postmortem result checkpoint → （若 justified）continuous_smoothing v2 launch review。
- 本文范围：**纯 markdown design**，不写脚本、不读真实 csv、不读真实 DB、不修改 output_dir 任何文件。

> **fail 是 legal fail，不是 pipeline error / schema bug / IO 错误 / DB guard 失败。** 本 postmortem 的目的是**理解**为什么 v1 SEED + threshold=0.60 在 W1 真实 regime 上几乎不触发但触发的全错；不是**修复** v1（任何参数变更必须经独立 launch review）。

## 2. 已知结果

| 字段 | 值 |
|---|---|
| `records_loaded` | 639（W1-W3 DB=286 + W4 jsonl=353） |
| `records_adapted` | 526（639-113 skipped；113 全部 `record_skipped:missing_or_invalid_direction_correct:<date>`） |
| `report_status` | `fail` |
| `overall_status` | `fail` |
| `worst_window` | **`W1`** |
| W1 `false_exclusion_rate` | **`1.0000`** |
| W1 触发样本 `candidate_triggered=True` count | **2**（< helper `GATE_MIN_WINDOW_SAMPLE = 20`） |
| W1 `candidate_triggered=False` count | 108 |
| W2 触发：True / False | 23 / 70 |
| W3 触发：True / False | 4 / 79 |
| W4 触发：True / False | 107 / 133 |
| 7 gate 状态 | 全部 **fail**（min_sample / false_exclusion / net_benefit / accuracy_delta / cross_window / survival / no_single_collapse） |
| `final_test_touched` | `false` |
| `final_test_refusal` | `false` |
| DB / market_data.db / backup count | 三组 fingerprint **unchanged** |

## 3. postmortem 目标

postmortem **回答以下 8 个问题**；**不**回答如何调 threshold / SEED；**不**回答如何让 candidate 通过：

| # | 问题 | 输出形式 |
|---|---|---|
| 1 | 为什么 W1 只触发 2 条？ | descriptive：W1 数据中 `risk_score >= 0.60` 的 row 极少；列出 risk_score 分布 |
| 2 | 为什么这 2 条全部 false exclusion？ | descriptive：列出这 2 条 row 的 outcome 字段（`direction_correct` / `actual_close_change`）+ adapter `survival_case` / `exclusion_would_block` 计算；说明 candidate 选中的全是 survivor |
| 3 | W1 的 market regime 是否和 v1 SEED 假设冲突？ | descriptive：W1 = 2023-01-03 ~ 2023-08-31；该期间 AVGO / SOXX / QQQ 走势是否构成对 SEED 的 prior 不利 |
| 4 | v1 risk_score 是否过于集中 / 过于稀疏？ | descriptive：per-window risk_score histogram / IQR / max；判断 threshold=0.60 在 W1 是否击中长尾 |
| 5 | threshold=0.60 是否导致触发样本过少？ | descriptive：在 W1 上的 trigger rate（2/110 ≈ 1.8%）vs W4（107/240 ≈ 44.6%）；说明 threshold 在 W1 几乎没击中 |
| 6 | 哪些 feature 对 W1 触发贡献最大？ | descriptive：W1 中 risk_score 最高的 row 的 features_used（pos20 / avgo_minus_soxx_20d / peer_5d_aligned_pct / market_trend_strength / monthly_shock）+ 系数；不做 SHAP / 不优化 |
| 7 | v1 是否在 W2 / W3 / W4 有不同表现？ | descriptive：per-window false_exclusion_rate / net_benefit / accuracy_delta；说明跨 window variance 来源 |
| 8 | 是否值得进入 v2 launch review？ | descriptive：summarize structural issues；**判断不动 v1**；**给出**「值得 v2 launch review」或「v1 设计完全失效，需回 candidate 设计层」的二选一 |

> postmortem 的输出**不**包括：新 threshold / 新 SEED / 新 gate 阈 / 新 sweep / 新 retry 计划 / 任何会触发 first-fail-driven 调参的内容。

## 4. 需要读取的数据

仅读取以下 4 个文件（**只读，不修改，不 commit，不重新生成**）：

| 路径 | 用途 |
|---|---|
| `logs/regime_validation/continuous_smoothing_v1_real_w1_w4_20260507_065417/replay_validation_records.json` | 526 条 records；含 per-row analysis_date / window / candidate_triggered / risk_score / risk_bucket / features_used / direction_correct / actual_close_change |
| `logs/regime_validation/continuous_smoothing_v1_real_w1_w4_20260507_065417/regime_validation_report.json` | overall_status / worst_window / fail_reason / gate_status / per-window metrics |
| `logs/regime_validation/continuous_smoothing_v1_real_w1_w4_20260507_065417/run_manifest.json` | records_loaded / records_adapted / warnings / windows / candidate_threshold |
| `logs/regime_validation/continuous_smoothing_v1_real_w1_w4_20260507_065417/regime_validation_summary.md` | human-readable 汇总（已抽进 result checkpoint §7） |

**强制 read-only**：

- ❌ **不**修改 4 文件任一字符
- ❌ **不** `git add` 4 文件（保持 untracked）
- ❌ **不**重新生成 4 文件（不重跑 validation；本次的 `20260507_065417` 是固定 baseline）
- ❌ **不**用 4 文件数据反推新 threshold / 新 SEED / 新 gate 阈
- ❌ **不**对 4 文件做任何统计 fitting / optimization / grid search

## 5. postmortem 分析维度（10 项）

postmortem 实施步骤**只产生 descriptive 数据**；不优化、不拟合、不反推。

| # | 维度 | 来源字段 | 输出形式 |
|---|---|---|---|
| 1 | per-window trigger count | records.window + records.candidate_triggered | 表格：W1/W2/W3/W4 × {True, False} count + ratio |
| 2 | per-window false_exclusion_rate | report.gate_status / report.per_window_metrics | 直接复述 helper 已计算的 false_exclusion_rate |
| 3 | triggered vs non-triggered baseline correctness | records.direction_correct + records.candidate_triggered | per-window 4-cell 表（trig=True/dc=True, trig=True/dc=False, trig=False/dc=True, trig=False/dc=False） |
| 4 | W1 triggered row details | records 中 W1 + candidate_triggered=True 的 2 条 | 列出 analysis_date / prediction_for_date / risk_score / risk_bucket / features_used / direction_correct / actual_close_change |
| 5 | risk_score distribution by window | records.risk_score | per-window quantile（min / 25% / 50% / 75% / max）；不拟合分布 |
| 6 | risk_bucket distribution by window | records.risk_bucket | per-window {low, mid, mid_high, high, missing} count |
| 7 | features_used distribution（5 feature） | records.features_used | per-window 5 feature 的 mean / median / null-rate；纯 descriptive；**不**回归、**不**做 SHAP / permutation importance |
| 8 | survival_case preservation | records.survival_case + records.exclusion_would_block | per-window survivor preserved / blocked rate |
| 9 | net_benefit by window | report.per_window_metrics | 复述 helper 计算；不重算 |
| 10 | cross-window variance source | gate_status.cross_window_variance / per-window false_exclusion_rate spread | descriptive：variance source = W1 极端 vs W2/W4 中间 vs W3 极少触发 |

## 6. W1 deep dive plan

W1 是 worst_window；postmortem 必须**完整复述 W1 中 candidate_triggered=True 的 2 条 row**：

| 字段 | 含义 |
|---|---|
| `as_of_date` | 触发日期 |
| `prediction_for_date` | 对应 prediction 日期 |
| `window` | 应该 = `"W1"` |
| `candidate_triggered` | 应该 = `true` |
| `risk_score` | 数值（≥ 0.60） |
| `risk_bucket` | 应该 ∈ {`mid_high`, `high`} |
| `features_used.pos20` | W1 期间 AVGO 60-day pos |
| `features_used.avgo_minus_soxx_20d` | W1 期间 AVGO vs SOXX 20d 偏离 |
| `features_used.peer_5d_aligned_pct` | W1 期间 peer 同步率 |
| `features_used.market_trend_strength` | W1 QQQ slope vs drawdown |
| `features_used.monthly_shock` | W1 monthly daily-return / monthly-return shock 触发 |
| `direction_correct` | DB outcome；**这是 false_exclusion_rate=1.0 的关键来源** |
| `actual_close_change` | DB outcome |
| 派生：`survival_case` | adapter 计算（direction_correct=True 等价于 survivor） |
| 派生：`exclusion_would_block` | adapter 根据 risk_bucket / threshold 判定 |

**判定逻辑**（不做新计算；复述已 merge 的 adapter 行为）：

- 若 W1 这 2 条 row `direction_correct=True` → 全是 survivor → candidate 把 survivor 全错排 → false_exclusion_rate = 2/2 = 1.0 ✅ 与 fail_reason 字符串一致
- 若 W1 这 2 条 row `direction_correct=False` → 不会贡献 false_exclusion；与 fail_reason 矛盾，需重新核对 adapter 字段映射

postmortem **必须**列出这 2 条原始 row（去敏感字段）作为根因证据；**不**修改 row、**不**重新跑 candidate / adapter。

postmortem **不**做：

- 不改 W1 数据
- 不改 W1 boundary（W1=2023-01-03 ~ 2023-08-31 已锁定，与 adapter `DEFAULT_WINDOWS` 对齐）
- 不重跑 W1
- 不调 threshold 让 W1 触发更多
- 不调 SEED 让 W1 risk_score 更高

## 7. feature attribution review

5 seed feature + 5 seed coefficient（来自 `services/continuous_smoothing_candidate.py:43-49` `SEED_COEFFICIENTS`）：

| feature | seed coefficient | 方向含义（设计文档 §5.1） |
|---|---|---|
| `pos20` | `+1.2` | 60-day pos20 高 → risk 高 |
| `avgo_minus_soxx_20d` | `+1.0` | AVGO 偏离 SOXX 高 → risk 高 |
| `peer_5d_aligned_pct` | `-0.8` | peer 同步率高 → risk 低（消减） |
| `market_trend_strength` | `-0.7` | market 趋强 → risk 低 |
| `monthly_shock` | `+0.5` | monthly shock 触发 → risk 高 |

postmortem 范围：

- ✅ **descriptive review**：列出 W1 中 candidate_triggered=True / False 两组的 feature mean / median / null-rate（5 feature × 2 group = 10 cell × 4 window = 40 cell 表）
- ✅ 描述 W1 / W2 / W3 / W4 中 5 feature 的 quantile spread；说明 v1 SEED 假设是否在 W1 regime 下退化（如 W1 = 2023 上半年，AVGO 暴涨；pos20 长期高 → +1.2 系数贡献长期高 → risk_score 长期高 → 但 threshold=0.60 仍击不到 / 击到的全是 survivor）
- ❌ **不**做 SHAP / permutation importance / Shapley
- ❌ **不**做 logistic / linear / tree regression on outcome
- ❌ **不**反推新 coefficient
- ❌ **不**做正交化 / decorrelation
- ❌ **不**做 W1-fit / window-tuning

> 这是**理解**，不是**优化**。任何系数改动 = 新 candidate（v2）= 必须独立 launch review。

## 8. threshold review boundary

`candidate_threshold = 0.60` 是 first-run **design seed**（lock in execution glue CLI；非 0.60 → exit 2）。

postmortem 允许：

- ✅ **描述** threshold=0.60 在 per-window 上的 trigger rate（W1=1.8%, W2=24.7%, W3=4.8%, W4=44.6%）
- ✅ **观察** threshold=0.60 在 W1 几乎没击中 → triggered count low → `minimum_window_sample_size` gate fail 是直接结果
- ✅ **观察** threshold=0.60 在 W4 击中过多 → 可能 over-eager
- ✅ 把这些观察作为 v2 launch review 的**问题**写入 §11 postmortem report

postmortem 禁止：

- ❌ **不**建议 threshold = 0.50 / 0.65 / 0.70 / 任何具体新值
- ❌ **不**给出 threshold sweep grid（如 [0.4, 0.5, 0.6, 0.7]）
- ❌ **不** retry until pass
- ❌ **不**用 W1 出 2 条 → 反推 threshold 应该 lower
- ❌ **不**用 W4 出 107 条 → 反推 threshold 应该 higher
- ❌ **不**写 "threshold v2 应该 X"，只写 "threshold v2 需要在独立 launch review 中决定"

任何 threshold v2 必须经独立 launch review；postmortem 是 review 的**输入材料**，不是 review 本身。

## 9. v2 candidate design boundary

postmortem 允许提**问题**；**禁止**给具体设计：

| 允许 | 禁止 |
|---|---|
| ✅ 提出 v2 是否需要 windowed-prior（不同 regime 用不同系数） | ❌ 给具体 windowed coefficient |
| ✅ 提出 v2 是否需要新 feature（如 historical drawdown / VIX-equivalent） | ❌ 给新 feature 公式 |
| ✅ 提出 v2 是否需要 calibration（Platt / isotonic）让 risk_score 跨 window 可比 | ❌ 实现 calibration |
| ✅ 提出 v2 是否需要 dynamic threshold（per-window） | ❌ 给具体 per-window threshold 值 |
| ✅ 提出 v2 是否需要排除 monthly_shock（如系数对 fail 贡献低） | ❌ 删除 / 改 SEED 系数 |
| ✅ 提出 v2 是否要把 5 feature 改成 4 / 6 / 其它组合 | ❌ 选具体新组合 |
| ✅ 提出 W4 outcome 是否过度 paired（107/240 触发是否健康） | ❌ 重新切 W4 boundary |

强约束（design / impl checkpoint 一致）：

- ❌ **不**改代码（v2 必须经独立 design + checkpoint + impl + tests + new real run）
- ❌ **不**跑 validation（v2 必须独立 single real run）
- ❌ **不** commit 任何 v2 实现
- ❌ **不**触碰 v1 已 merge 模块（wrapper / provider / orchestrator / candidate / adapter / helper / glue 全部 read-only 引用）
- ✅ v2 必须以 v1 fail（本次 `20260507_065417` run）为 baseline 对照；v2 必须 strictly 优于 v1，并独立验证；v2 fail 也是 legal fail，不能反推回 v1

## 10. no-go rules

postmortem 全程 **no-go**（任意一项触发 → 立即停止 postmortem，不进入下一步）：

| # | 条件 |
|---|---|
| 1 | 调 `candidate_threshold`（任何具体新值） |
| 2 | 调 SEED coefficients（任何系数改动） |
| 3 | 调 6 metric / 7 gate threshold（3R-4 protocol 锁定） |
| 4 | 重跑 validation（execution glue / orchestrator / wrapper 任一） |
| 5 | sweep / grid search / hyper-tune（任何 form） |
| 6 | retry until pass |
| 7 | 进入 Step 3R-5 formula |
| 8 | 进入 Step 3R-6 simulator |
| 9 | 启 hard / forced / `anti_false_exclusion_triggered` |
| 10 | 让 `_PROTECTION_LAYER_CONNECTED` 翻 True |
| 11 | 改 04 / 05 / 07 required |
| 12 | 触碰 2026 final-test range |
| 13 | commit raw output（`logs/regime_validation/<TS>/` 4 文件全部保持 untracked） |
| 14 | 把 fail 当系统错误 / 重写代码 / 修复任何已 merge service |
| 15 | 用 first run 数据反推 threshold / SEED |
| 16 | 接 yfinance / requests / 任何网络 |
| 17 | 接 trading API |
| 18 | 改 wrapper / provider / orchestrator / candidate / adapter / helper / glue 任一已 merge 模块 |
| 19 | 改 `tests/test_run_real_continuous_smoothing_validation_execute.py` 等已 merge 测试 |
| 20 | 把 postmortem 写成可执行 sweep 脚本 |

## 11. postmortem output schema

设计未来 **postmortem report schema**：`candidate_postmortem_report.v1`。

| 字段 | 类型 | 说明 |
|---|---|---|
| `schema_version` | str | `"candidate_postmortem_report.v1"` |
| `candidate_name` | str | `"continuous_smoothing_v1"`（从 source_run 复述） |
| `source_run` | dict | `{"output_dir": "logs/regime_validation/continuous_smoothing_v1_real_w1_w4_20260507_065417", "main_commit": "75f0ad5", "run_timestamp": "20260507_065417"}` |
| `overall_status` | str | `"fail"`（从 source_run 复述） |
| `worst_window` | str | `"W1"`（从 source_run 复述） |
| `root_cause_hypotheses` | list[str] | descriptive 假设；**不**包含具体新 threshold / 新 coef |
| `per_window_summary` | list[dict] | per-window {window, total, triggered_true, triggered_false, false_exclusion_rate, risk_score_quantiles, risk_bucket_distribution} |
| `w1_triggered_cases` | list[dict] | 列出 W1 candidate_triggered=True 的 N 条 row（本次 N=2）的 11 字段（见 §6） |
| `feature_review` | dict | 5 feature × 4 window 的 mean / median / null-rate；descriptive only |
| `threshold_review` | dict | `{seed_value: 0.60, per_window_trigger_rate: {...}, observation: "W1 trigger rate 1.8% << W4 44.6% → cross-window variance high"}`；**不**含 recommended_value |
| `v2_questions` | list[str] | postmortem 提出的 v2 候选问题（5-10 条） |
| `no_go_confirmations` | list[str] | 复述 §10 的 20 项 no-go；标注本 postmortem 对每项的 status（全部 ❌ 不触发） |
| `recommended_next_step` | str | 二选一：`"launch_continuous_smoothing_v2_design_review"` 或 `"abandon_continuous_smoothing_redesign_from_candidate_layer"`；**不**含 "tune_threshold_v1" / "retry" / "sweep" |

postmortem 实施可以选**两种方式**之一（本 design 不强制；都可）：

| 方式 | 描述 | 范围 |
|---|---|---|
| A. inline read-only 分析 | 直接在 markdown checkpoint 中 inline 读取 4 json + 写表 + 写 markdown；不新增 .py 文件 | 适合本次 N=2 / 5 feature × 4 window 的小规模分析 |
| B. read-only postmortem 脚本 | 新增 `scripts/postmortem_continuous_smoothing_v1.py` + `tests/test_postmortem_continuous_smoothing_v1.py`；脚本只读 4 json + 写 markdown report；不连 DB / 不连网 / 不动 candidate; 必须 isolation tests | 适合更大规模 / 重复 postmortem |

> 本 design 不预先决定 A / B；postmortem 实施步骤再选。两种方式都 **不**调 threshold / SEED；都 **不**重跑 validation；都 **不** commit raw output。

## 12. acceptance criteria

postmortem 完成标准（13 项）：

| # | 标准 |
|---|---|
| 1 | 能解释 W1 false_exclusion_rate=1.0 的直接原因（W1 触发 2 条 + 全是 survivor） |
| 2 | 能说明 W1 触发样本只有 2 的直接原因（risk_score 分布 + threshold=0.60） |
| 3 | 能说明 v1 是否存在 window instability（W1 极少触发 vs W4 触发过多） |
| 4 | 能描述 5 feature 在 4 window 上的 descriptive 行为 |
| 5 | 能列出 W1 triggered 的 2 条 row 完整证据 |
| 6 | 能提出 v2 设计问题（5-10 条） |
| 7 | 能给出二选一的 recommended_next_step（`v2 launch review` 或 `redesign from candidate layer`） |
| 8 | **不**产生任何新 threshold（具体值） |
| 9 | **不**产生任何新 SEED coefficient（具体值） |
| 10 | **不**产生任何新 gate threshold |
| 11 | **不**运行任何新 validation |
| 12 | **不**修改代码 |
| 13 | **不** commit raw output / 不修改 `output_dir` 任一文件 |

> 本 acceptance 是 **判断 postmortem 写得对不对**；不是判断 candidate v1 是否通过（v1 已 fail，无需再判断）。

## 13. 推荐实施顺序

| # | 步骤 | 是否本文范围 |
|---|---|---|
| 1 | commit 本 design doc（仅 markdown） | ⏳ 下轮（本轮不 commit） |
| 2 | 写 design checkpoint：`tasks/step_3r3_3c_d_candidate_postmortem_design_checkpoint.md` | ❌ 后续步骤 |
| 3 | postmortem 实施（inline read-only 分析 **或** read-only 脚本 + tests） | ❌ 后续步骤 |
| 4 | postmortem result checkpoint：`tasks/step_3r3_3c_d_candidate_postmortem_result_checkpoint.md` | ❌ 后续步骤 |
| 5 | 根据 postmortem `recommended_next_step` 二选一：（a）launch continuous_smoothing v2 design review；（b）回到 candidate layer 重新设计 | ❌ 后续步骤；必须独立流程 |

> **本文不实施 postmortem、不写脚本、不写测试、不改代码、不 commit、不 push**。

## 14. 与 3R-5 / 3R-6 关系

| 关系 | 状态 |
|---|---|
| 当前 v1 fail 是否 block 3R-5 formula | ✅ 是；fail 阻止 promotion |
| 当前 v1 fail 是否 block 3R-6 simulator | ✅ 是；3R-6 必须先过 3R-5 |
| postmortem 是否解锁 3R-5 / 3R-6 | ❌ 否；postmortem 仅产出 review 输入材料 |
| 是否可直接进入 3R-5 / 3R-6 | ❌ 永久禁止（除非未来 v2 通过独立 single real run + result checkpoint + launch review） |
| v2 launch review 是否在本步骤范围 | ❌ 否；本步骤只产出 postmortem |
| v2 design 是否在本步骤范围 | ❌ 否；v2 必须独立 launch review |
| 任何 formula / simulator 启动 | 必须经独立 launch review；不在 3R-3.3C-D 范围 |

## 15. 严守边界

本文是**纯 design markdown**：

- ❌ 没改任何代码（`services/*` / `ui/*` / `tests/*` / `scripts/*` 全部未触碰）
- ❌ 没改 DB schema
- ❌ 没写 DB
- ❌ 没运行 replay
- ❌ 没运行 real validation（本次记录的 baseline 是 `20260507_065417` run；本 design 不触发新 run）
- ❌ 没运行 prepare-only smoke
- ❌ 没读 4 json output 任一字节（仅引用文件路径；postmortem 实施才会读）
- ❌ 没修改 `output_dir/replay_validation_records.json` / `regime_validation_report.json` / `regime_validation_summary.md` / `run_manifest.json`
- ❌ 没改 `run_predict` / `predict.py` / `scanner.py` / `prediction_store.py` / `app.py`
- ❌ 没改 `services/regime_features_builder.py` / `services/regime_labels_builder.py` / `services/regime_validation_helper.py` / `services/continuous_smoothing_candidate.py` / `services/replay_validation_record_adapter.py` / `services/historical_replay_training.py` / `services/real_regime_label_provider.py` / 任何 ui 模块 / 任何 builder
- ❌ 没改 `scripts/run_continuous_smoothing_validation.py` / `scripts/run_real_continuous_smoothing_validation.py` / `scripts/run_real_continuous_smoothing_validation_execute.py`
- ❌ 没改 `tests/test_run_continuous_smoothing_validation.py` / `tests/test_run_real_continuous_smoothing_validation.py` / `tests/test_real_regime_label_provider.py` / `tests/test_run_real_continuous_smoothing_validation_execute.py` / 任何已 merge 测试
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
- ❌ 没改 Step 3R-3.3 / 3R-3.3A / 3R-3.3B / 3R-3.3C 系列已 merge 文档 / 实施
- ❌ 没改 Step 2G-8D / 8D.1A / 8D.2 / 8D.3 / 8D.4 文档或代码
- ❌ 没把 W4 / smoke / `logs/regime_validation/` / `logs/prediction_log.jsonl` / DB backup / `agent_loop.py` / `.claude/worktrees/` 任一 commit 进 main
- ❌ 没创建任何新的 `logs/regime_validation/*` 子目录
- ❌ 没运行 `pytest`（本轮纯文档；测试基线维持 commit `7812b10` 时的 **2905 / 0 failed / 10 skipped**）
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*`
- ❌ 没调 `candidate_threshold` / SEED coefficients / 6 metric / 7 gate threshold
- ❌ 没用 first run 数据反推任何参数
- ❌ 没让 fail 触发 retry / sweep / grid search
- ✅ 只新增 1 份 markdown design 文档（本文件）
