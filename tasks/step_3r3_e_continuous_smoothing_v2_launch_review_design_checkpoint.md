# Step 3R-3.3E — Continuous Smoothing v2 Launch Review Design Checkpoint

> 本文是 **checkpoint markdown** —— 不改代码、不写 DB、不重跑 replay / validation、不 commit / push、不接 trading API、不启 hard / forced、不改 required、不触碰 2026 final-test range、不 add `logs/regime_validation/` / W4 / smoke output / `logs/prediction_log.jsonl`、不处理 DB backup / stash / `.claude/worktrees/`、不调 v1 `candidate_threshold` / SEED coefficients / 6 metric / 7 gate threshold、不实现 v2、不给 v2 任何具体新参数 / 新阈 / 新 feature 公式、不进 3R-5 / 3R-6 / 不自动 promotion。

## 1. 当前完成状态

| 项 | 状态 | 来源 |
|---|---|---|
| Step 3R-3.3C real W1-W4 validation single run | ✅ 已运行（一次） | output `logs/regime_validation/continuous_smoothing_v1_real_w1_w4_20260507_065417/` |
| Step 3R-3.3C real validation result checkpoint | ✅ 已 merge | commit `75f0ad5` |
| Step 3R-3.3C-D postmortem design + checkpoint + report | ✅ 已 merge | commits `289f97b` / `c5bf686` / `fc44bcf` |
| postmortem `recommended_next_step` | `launch_continuous_smoothing_v2_design_review` | postmortem report §13 |
| Step 3R-3.3E **continuous_smoothing v2 launch review design**（13 节、266 行） | ✅ **已 merge** | commit `4fd1278` |
| **本 checkpoint** —— 固定 v2 launch review 目标 / 约束 / allowed design directions / validation requirements / pass criteria / no-go rules / output schema / recommendation | ⏳ **本文**（未 commit） | — |
| v2 design（独立文档）| ❌ 尚未启动 | — |
| v2 implementation | ❌ 尚未实现 | — |
| v2 single real run / v2 result checkpoint | ❌ 尚未启动 | — |

> v1 fail 已固定为 baseline；v2 仍未设计、未实现；本 checkpoint 只固化 launch review design 状态。

## 2. 当前 main 状态

- `main` 最新 commit：`4fd1278`
- commit message：`docs(contract): Step 3R-3.3E continuous smoothing v2 launch review design`
- 上游：`origin/main` 已同步（push 完成 `fc44bcf..4fd1278  main -> main`）
- 本步骤已 merge 文件：

| 路径 | 类型 | 行数 |
|---|---|---|
| `tasks/step_3r3_e_continuous_smoothing_v2_launch_review_design.md` | 新增 | 266（v2 launch review design 边界） |

测试基线：本步骤纯文档；测试基线维持 commit `7812b10` 时的 **2905 / 0 failed / 10 skipped**。

| 项 | 是否触碰 |
|---|---|
| 改代码 | ❌ 否 |
| 改 service / candidate（v1）/ adapter / helper / orchestrator / wrapper / provider / glue | ❌ 否 |
| 改 DB schema / 写 DB | ❌ 否 |
| 跑 replay / 重跑 real validation / 跑 prepare-only smoke | ❌ 否 |
| 调 v1 `candidate_threshold` / SEED coefficients | ❌ 否 |
| 调 6 metric / 7 gate threshold | ❌ 否 |
| 接 yfinance / 网络 / trading API | ❌ 否 |
| 触碰 2026 final-test range | ❌ 否 |
| add `logs/regime_validation/` / `output_dir` 任一文件 | ❌ 否 |
| add W4 / smoke / DB backup / `agent_loop.py` / `.claude/worktrees/` / `logs/prediction_log.jsonl` | ❌ 否 |
| 进 3R-5 formula / 3R-6 simulator | ❌ 否 |
| 启 hard / forced / required / `_PROTECTION_LAYER_CONNECTED` | ❌ 否 |
| 实现 v2 / 给 v2 任何具体参数 | ❌ 否 |

## 3. v1 baseline

| 字段 | 值 |
|---|---|
| `candidate_name` | `continuous_smoothing_v1` |
| source run | `logs/regime_validation/continuous_smoothing_v1_real_w1_w4_20260507_065417/` |
| `candidate_threshold` | `0.60`（v1 seed lock；CLI 拒非 0.60） |
| `final_test_cutoff` | `"2026-01-01"` |
| `records_loaded` | 639（W1-W3 DB=286 + W4 jsonl=353） |
| `records_adapted` | 526（639 − 113 skipped；113 全部 `record_skipped:missing_or_invalid_direction_correct:<date>`） |
| `report_status` | `fail` |
| `overall_status` | `fail` |
| `worst_window` | **`W1`** |
| W1 `false_exclusion_rate` | **`1.0000`**（gate 阈 0.10 的 10×） |
| 4 window false_exclusion_rate | W1=1.00 / W2=0.52 / W3=0.50 / W4=0.54（**全部** > 0.10） |
| 4 window survival_case_preservation | **全部 0.0** |
| 7 gate 状态 | 全部 fail |
| `final_test_touched` | `false` |
| DB / market_data.db / backup count | 三组 fingerprint **unchanged**（7 → 7） |
| **结论** | **v1 不 eligible**；fail 是 legal fail，不是 pipeline error |

## 4. v1 root cause summary（H1-H5）

postmortem report §10 列出的 5 个 hypothesis（本节复述，不修改）：

| # | Hypothesis |
|---|---|
| **H1** | candidate 的 risk_score **跨 window 分布不可比** —— 同样 risk_score=0.65 在 W1 是 ~p98 长尾，在 W4 接近 mean。固定 global threshold 会在不同 regime 上给出极端不同的触发率（postmortem 跨 window trigger 率 1 : 24）。 |
| **H2** | seed features 看起来更像 **regime classifier**，而不是 **exclusion-risk classifier**。4 window 全 false_exclusion ≥ 0.5；survival_case_preservation 全 0.0。 |
| **H3** | seed coefficients **极性可能颠倒**：candidate 把 `pos20` 高 + `avgo_minus_soxx_20d` 高（相对强势）当 overheat → 应排除；但真实数据中这些 row 反而是**继续上涨**的 survivor —— 至少在 W1 早期 bull 阶段。 |
| **H4** | candidate 的 **damping feature**（`peer_5d_aligned_pct` 系数 -0.8、`market_trend_strength` 系数 -0.7）在 W1 经常 = 0（peer_momentum_regime=weak / 早期 trend 未确立），无法消减 + 系数 → high bucket 触发。 |
| **H5** | candidate v1 缺少 **min trigger support guard** 与 **calibration**。helper 已有 `GATE_MIN_WINDOW_SAMPLE = 20`，但 candidate 自身没有"低样本不下结论"机制；risk_score 没有校准到 observed false_exclusion probability。 |

## 5. v2 launch review 目标（8 问）

v2 launch review 必须**回答以下 8 个问题**；本 checkpoint **不**给答案，只列问题：

| # | 问题 | 关联 hypothesis |
|---|---|---|
| 1 | v2 是继续做 **fixed global threshold**，还是 **regime-aware / window-aware threshold**？是否需要"局部归一化 risk_score 后再用全局 threshold"？ | H1 / H5 |
| 2 | risk_score 是否应该 **校准到 observed false_exclusion probability**（如 isotonic / Platt / 分位归一），让跨 window / 跨 regime 含义一致？ | H1 / H5 |
| 3 | v2 如何避免**误杀 strong survivor**？是否需要"survivor-protection feature"或"continuation-of-trend protection"层？ | H2 / H3 |
| 4 | v2 如何**区分 overheat risk 与 false-exclusion risk**？是否需要把 candidate 拆成"高位提示"+"实际 exclusion 决策"两个 layer？ | H2 / H3 |
| 5 | 是否需要 **candidate-level minimum trigger support guard**（区别于 helper `GATE_MIN_WINDOW_SAMPLE`）？例如 candidate 在低样本 / 低 confidence 下 abstain 而非误判？ | H5 |
| 6 | `monthly_shock` 是否保留？（中位 0.000 across all windows；稀疏二值化；对 W1 触发 0 贡献） | H4 + 数据观察 |
| 7 | `market_trend_strength` 是否需要从"简单降风险"改为"**保护强趋势 continuation**"语义？是否需要 trend regime 与 trigger 的非线性交互？ | H3 / H4 |
| 8 | v2 如何**防止从 v1 fail 数据直接反推参数**？v2 design 参数来源应是先验 / 文献 / 工程判断；validate 阶段才判读 v1 baseline，不是参数来源 | postmortem §12 Q7 |

## 6. v2 candidate design constraints（15 项硬约束）

v2 必须满足以下硬约束（违反任一 → launch review 拒绝）：

| # | 约束 |
|---|---|
| 1 | v2 **不得**调 v1 `candidate_threshold = 0.60` |
| 2 | v2 **不得**调 v1 SEED coefficients |
| 3 | v2 **不得**直接复制 v1 SEED coefficients 作为起点 |
| 4 | v2 **不得**用 v1 fail 结果（`20260507_065417` baseline）反推具体参数 |
| 5 | v2 必须保持 **read-only candidate**（不影响 final prediction） |
| 6 | v2 必须保持 **sidecar 形式**（不进入 production main path / Streamlit / trading） |
| 7 | v2 **不得**启 hard / forced / `anti_false_exclusion_triggered` |
| 8 | v2 **不得**写 DB / 不得改 DB schema |
| 9 | v2 **不得**触碰 2026 final-test range；cutoff 仍锁 `"2026-01-01"`；6 层 hard stop 全部保留 |
| 10 | v2 **不得**接 yfinance / requests / urllib / 任何网络 / trading API |
| 11 | v2 必须复用 v1 wrapper（`build_real_validation_inputs`）+ adapter / helper 接口；**不**改这些已 merge 模块 |
| 12 | v2 **不得**让 `_PROTECTION_LAYER_CONNECTED` 翻 True；不得让 `hard_gate_status.protection_layer_connected` 自动 pass |
| 13 | v2 输出 schema 必须仍是 `continuous_smoothing_candidate.v1`（或显式 `.v2` 升级版本，但 adapter / helper 必须接受） |
| 14 | v2 **不得** import `services.continuous_smoothing_candidate`（v1）作为基础 —— 必须独立模块（如 `services/continuous_smoothing_candidate_v2.py`） |
| 15 | v2 **不得**触发 retry-until-pass；single real run + result checkpoint 是唯一验证途径 |

## 7. allowed design directions（10 项；仅方向）

v2 可以考虑的设计方向（**不**给具体公式 / 系数 / 阈值 / 分位 / 校准曲线 / 网络结构）：

| # | 方向 | 关联 hypothesis |
|---|---|---|
| 1 | window-aware risk_score normalization | H1 / H5 |
| 2 | regime-aware threshold policy | H1 |
| 3 | candidate-level minimum trigger support guard | H5 |
| 4 | survivor-protection feature | H2 / H3 |
| 5 | trend-continuation protection | H3 / H4 |
| 6 | overheat-risk vs false-exclusion-risk separation | H2 / H3 |
| 7 | risk_score calibration to observed false_exclusion probability | H1 / H5 |
| 8 | candidate confidence / abstain mode | H5 |
| 9 | feature set 重新审计（含 monthly_shock 必要性 / market_trend_strength 语义重写） | H4 + Q6 + Q7 |
| 10 | windowed-prior 而不是 windowed-fit | H1 + Q8 |

> 上面 10 个方向**互不互斥**；v2 design 选哪几条由 launch review 决定。本 checkpoint **不**做选型。

## 8. validation requirements（8 步独立 review gate）

v2 必须**完整重走**以下 8 步流程（每一步都是独立 review gate；缺一不可）：

| # | 步骤 | 范围 |
|---|---|---|
| 1 | **v2 design** | feature 集合 / score 定义 / threshold policy / abstain rule / calibration approach |
| 2 | **v2 design checkpoint** | 状态归档 |
| 3 | **v2 implementation** | 新增 `services/continuous_smoothing_candidate_v2.py`（独立模块；不 import v1） |
| 4 | **v2 tests** | unit tests + isolation tests + schema tests；full pytest 零回归 |
| 5 | **adapter / helper compatibility** | 调 adapter / helper（不改 3R-4 protocol） |
| 6 | **single real W1-W4 validation run**（一次） | 通过 execution glue（如需新 glue 则独立 design + impl + tests）；同 cutoff `2026-01-01`；output_dir 新 timestamp |
| 7 | **v2 result checkpoint** | 同 v1 result checkpoint 风格 + v1 baseline comparison |
| 8 | **v1 baseline comparison**（在 result checkpoint 内） | 量化对比表（v1 vs v2） |

> 任一步 fail → 同样回到 design 层重新设计；**不**自动进入下一步；**不** retry until pass。

## 9. v2 pass criteria（10 项硬阈）

v2 **不能仅"比 v1 好一点"** —— 必须满足以下硬阈才能视为 launch review 通过候选：

| # | 标准 | 量化要求 |
|---|---|---|
| 1 | 7 gates 全部 pass，**或**对未通过的 gate 给出明确 launch review 接受的解释 | 任一 fail 必须有 review-approved waiver |
| 2 | `worst_window` 不 collapse | worst_window false_exclusion_rate ≤ helper 阈 0.10；不出现 v1 那样的 1.0 触顶 |
| 3 | `false_exclusion_rate` **显著低于** v1 的对应 window | 4 个 window 全 < v1 对应值；且至少全部 ≤ 0.10 |
| 4 | `survival_case_preservation` **显著高于** v1 的 0.0 | 至少 4 个 window 全部 > 0；review 接受具体阈由 helper protocol 决定 |
| 5 | W1 不再"2/2 false exclusion"极端结果 | W1 false_exclusion_rate ≤ 0.10 |
| 6 | cross-window trigger rate 不极端失衡 | helper `cross_window_variance` gate pass；触发率不出现 1 : 24 量级差距 |
| 7 | `final_test_touched = false`；`final_test_refusal = false` | 6 层 hard stop 仍生效 |
| 8 | DB / market_data.db / backup count **未变** | byte-for-byte 不变 |
| 9 | output 4 文件 schema valid + untracked + **不 commit raw** | 与 v1 同样 untracked；不 commit raw output |
| 10 | v2 result checkpoint 必须包含 v1 baseline comparison 表 | 量化对比 |

> v2 即便满足以上 10 项，**也不**自动启 hard / Gate 5 / Gate 6 / `_PROTECTION_LAYER_CONNECTED` / 3R-5 / 3R-6 —— 仅允许进入 review。

## 10. no-go rules（20 项）

launch review + v2 流程全程 no-go（任意一项触发 → 立即停止）：

| # | 条件 |
|---|---|
| 1 | 直接调 v1 `candidate_threshold` |
| 2 | 直接调 v1 SEED coefficients |
| 3 | 直接调 v1 6 metric / 7 gate threshold（3R-4 protocol 锁定） |
| 4 | sweep / grid search / hyperparameter optimization 在 v1 / v2 baseline 上 |
| 5 | retry until pass（v2 single real run fail → 回 design，不重跑） |
| 6 | 用 v1 / v2 baseline 数据反推 threshold / SEED / cutoffs |
| 7 | 进入 Step 3R-5 formula |
| 8 | 进入 Step 3R-6 simulator |
| 9 | 让 v2 pass 自动进 production / 自动启 hard |
| 10 | 让 v2 pass 自动启 Gate 5 / Gate 6 / `_PROTECTION_LAYER_CONNECTED` |
| 11 | 改 04 / 05 / 07 required |
| 12 | 触碰 2026 final-test range |
| 13 | commit raw output（v1 或 v2 的 `logs/regime_validation/<TS>/`） |
| 14 | 接 yfinance / requests / 任何网络 / trading API |
| 15 | 改 v1 已 merge 模块（wrapper / provider / orchestrator / candidate / adapter / helper / glue） |
| 16 | 改任何已 merge 测试 |
| 17 | 把 launch review 写成可执行 sweep 脚本 |
| 18 | launch review design 阶段提具体新 threshold / 新 coefficient |
| 19 | launch review design 阶段实现 v2 |
| 20 | 让 v2 fail 触发 retry / sweep / 调参 |

## 11. output schema

`continuous_smoothing_v2_launch_review.v1`（13 字段）：

| 字段 | 类型 | 说明 |
|---|---|---|
| `schema_version` | str | `"continuous_smoothing_v2_launch_review.v1"` |
| `source_v1_baseline` | dict | `{"output_dir": "logs/regime_validation/continuous_smoothing_v1_real_w1_w4_20260507_065417", "main_commit": "4fd1278", "result_checkpoint_commit": "75f0ad5", "postmortem_report_commit": "fc44bcf"}` |
| `v1_failure_summary` | dict | `{report_status, overall_status, worst_window, w1_false_exclusion_rate, survival_case_preservation_per_window, gate_status}` —— 全部从 v1 result checkpoint / postmortem report 复述 |
| `v2_design_questions` | list[str] | 8 个 launch review 问题（§5） |
| `allowed_design_directions` | list[str] | 10 个 possible design directions（§7）的 label；**不**含具体参数 |
| `forbidden_actions` | list[str] | 复述 §10 的 20 项 no-go |
| `validation_requirements` | list[dict] | 8 步 validation 流程（§8） |
| `pass_criteria` | list[dict] | 10 项 v2 pass standard（§9） |
| `baseline_comparison_plan` | dict | v2 result checkpoint 必须包含的 v1 vs v2 对比表结构 |
| `design_constraints` | list[str] | §6 的 15 项 design constraint |
| `recommended_next_step` | str | 二选一：`"proceed_to_continuous_smoothing_v2_design"` 或 `"abandon_continuous_smoothing_candidate_layer"` |
| `unlock_3r5_3r6` | bool | **永远 false** |
| `auto_promotion` | bool | **永远 false** |

## 12. recommended_next_step

**`proceed_to_continuous_smoothing_v2_design`**

| 含义 | 状态 |
|---|---|
| 只允许进入 v2 **design**（独立文档） | ✅ |
| 允许直接进入 v2 **implementation** | ❌ 否（必须先过 v2 design + design checkpoint） |
| 允许直接进入 v2 **validation** | ❌ 否（必须先过 v2 impl + tests） |
| 允许直接进入 Step 3R-5 formula | ❌ 否（必须先过 v2 result checkpoint + 新一轮 3R-5 launch review） |
| 允许直接进入 Step 3R-6 simulator | ❌ 否（必须先过 3R-5 launch review） |
| 允许 launch review pass 自动 promotion | ❌ 否；`auto_promotion` 永远 false |
| 允许 launch review pass 解锁 3R-5 / 3R-6 | ❌ 否；`unlock_3r5_3r6` 永远 false |

## 13. 与 3R-5 / 3R-6 关系

| 关系 | 状态 |
|---|---|
| 当前 v1 fail 是否 block 3R-5 formula | ✅ 是；fail 阻止 promotion |
| 当前 v1 fail 是否 block 3R-6 simulator | ✅ 是；3R-6 必须先过 3R-5 |
| 本 launch review 是否解锁 3R-5 / 3R-6 | ❌ **永远不**；launch review 仅产出"是否进 v2 design"决定 |
| v2 launch review pass 是否解锁 3R-5 / 3R-6 | ❌ 否；只解锁 v2 design + impl + validation |
| v2 single real run pass 是否解锁 3R-5 / 3R-6 | ❌ 否；只允许进入 3R-5 launch review（**新一轮**独立 review） |
| v2 single real run pass 是否自动启 hard / Gate 5 / Gate 6 / `_PROTECTION_LAYER_CONNECTED` | ❌ **永远不** |
| 3R-5 / 3R-6 启动条件 | 必须先：v2 launch review pass → v2 design + checkpoint → v2 impl + tests → v2 single real run → v2 result checkpoint → **新一轮** 3R-5 launch review pass |

## 14. 严守边界

本文是**纯 checkpoint markdown**：

- ❌ 没改任何代码（`services/*` / `ui/*` / `tests/*` / `scripts/*` 全部未触碰）
- ❌ 没改 DB schema
- ❌ 没写 DB
- ❌ 没运行 replay
- ❌ 没**重新运行** real validation（baseline 仍是 v1 `20260507_065417` run）
- ❌ 没运行 prepare-only smoke
- ❌ 没读 v1 4 个 raw output json 任一字节（仅引用 path / 复述 result checkpoint + postmortem 已固化字段）
- ❌ 没修改 v1 4 个 raw output json
- ❌ 没改 `run_predict` / `predict.py` / `scanner.py` / `prediction_store.py` / `app.py`
- ❌ 没改 `services/regime_features_builder.py` / `services/regime_labels_builder.py` / `services/regime_validation_helper.py` / `services/continuous_smoothing_candidate.py`（v1） / `services/replay_validation_record_adapter.py` / `services/historical_replay_training.py` / `services/real_regime_label_provider.py` / 任何 ui 模块 / 任何 builder
- ❌ 没改 `scripts/run_continuous_smoothing_validation.py` / `scripts/run_real_continuous_smoothing_validation.py` / `scripts/run_real_continuous_smoothing_validation_execute.py`
- ❌ 没改 `tests/test_run_continuous_smoothing_validation.py` / `tests/test_run_real_continuous_smoothing_validation.py` / `tests/test_real_regime_label_provider.py` / `tests/test_run_real_continuous_smoothing_validation_execute.py` / 任何已 merge 测试
- ❌ 没新增 v2 任何代码 / 任何测试
- ❌ 没改 v1 `candidate_threshold = 0.60`（仍锁）
- ❌ 没改 v1 SEED coefficients（仍锁）
- ❌ 没改 v1 6 metric / 7 gate threshold（3R-4 protocol 锁定）
- ❌ 没给 v2 任何具体新 threshold / 新 coefficient / 新 feature 公式 / 新 cutoff
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
- ❌ 没改 Step 3R-3.3 / 3R-3.3A / 3R-3.3B / 3R-3.3C 系列 / 3R-3.3C-D / 3R-3.3C-D1 / 3R-3.3E 已 merge 文档 / 实施
- ❌ 没改 Step 2G-8D / 8D.1A / 8D.2 / 8D.3 / 8D.4 文档或代码
- ❌ 没把 W4 / smoke / `logs/regime_validation/` / v1 raw output / `logs/prediction_log.jsonl` / DB backup / `agent_loop.py` / `.claude/worktrees/` 任一 commit 进 main
- ❌ 没创建任何新的 `logs/regime_validation/*` 子目录
- ❌ 没运行 `pytest`（本轮纯文档；测试基线维持 commit `7812b10` 时的 **2905 / 0 failed / 10 skipped**）
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*`
- ❌ 没用 v1 baseline 数据反推 v2 任何具体参数
- ❌ 没让 v1 fail 触发 retry / sweep / grid search
- ❌ 没让 launch review 自动 promotion / 自动解锁 3R-5 / 3R-6
- ❌ 没实现 v2
- ✅ 只新增 1 份 markdown checkpoint 文档（本文件）
