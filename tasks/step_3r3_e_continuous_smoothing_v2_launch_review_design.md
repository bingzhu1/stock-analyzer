# Step 3R-3.3E — Continuous Smoothing v2 Launch Review Design

> 本文是 **launch review design only** —— 不改代码、不写 DB、不重跑 replay / validation、不 commit / push、不接 trading API、不启 hard / forced、不改 required、不触碰 2026 final-test range、不 add `logs/regime_validation/` / W4 / smoke output / `logs/prediction_log.jsonl`、不处理 DB backup / stash / `.claude/worktrees/`、不调 v1 `candidate_threshold` / SEED coefficients / 6 metric / 7 gate threshold、不实现 v2、不给具体新参数 / 新阈 / 新 feature 公式。

## 1. 背景

| 项 | 状态 | 来源 |
|---|---|---|
| Step 3R-3.3C real W1-W4 validation single run | ✅ 已运行（一次） | execution glue commit `7812b10`；output `logs/regime_validation/continuous_smoothing_v1_real_w1_w4_20260507_065417/` |
| Step 3R-3.3C result checkpoint | ✅ 已 merge | commit `75f0ad5` |
| Step 3R-3.3C-D postmortem design + checkpoint | ✅ 已 merge | commits `289f97b` / `c5bf686` |
| Step 3R-3.3C-D1 postmortem report | ✅ 已 merge | commit `fc44bcf` |
| postmortem `recommended_next_step` | `launch_continuous_smoothing_v2_design_review` | postmortem report §13 |
| **本文**（continuous_smoothing v2 launch review **design only**；不实现 v2、不给具体参数） | ⏳ design 中（未 commit） | — |

本文位置：

- 已 merge 链：result checkpoint（`75f0ad5`）→ postmortem design（`289f97b`）→ postmortem design checkpoint（`c5bf686`）→ postmortem report（`fc44bcf`）→ **本 launch review design** → launch review checkpoint → （仅 launch review pass 之后）v2 design → v2 checkpoint → v2 impl + tests → v2 single real run → v2 result checkpoint → 重新判断。
- 本文范围：**纯 markdown launch review design**，不写脚本、不读真实 csv / DB、不修改 v1 已 merge 模块、不修改 v1 raw output。

> 本文是给未来 v2 design 的**框架文档**：明确 v2 要回答的问题、可接受的设计方向（无具体参数）、validation 要求、pass 标准、no-go 列表、output schema 草案、二选一 recommendation。本文**不**包含可直接实现的设计选型；任何具体设计在 launch review pass 后由独立 v2 design 文档承接。

## 2. v1 baseline

| 字段 | 值 |
|---|---|
| `candidate_name` | `continuous_smoothing_v1` |
| source run | `logs/regime_validation/continuous_smoothing_v1_real_w1_w4_20260507_065417/`（main commit `75f0ad5`） |
| `candidate_threshold` | `0.60`（v1 seed lock；CLI 拒非 0.60） |
| `final_test_cutoff` | `"2026-01-01"` |
| `records_loaded` | 639（W1-W3 DB=286 + W4 jsonl=353） |
| `records_adapted` | 526（639 − 113 skipped；113 全部 `record_skipped:missing_or_invalid_direction_correct:<date>`） |
| `report_status` | `fail` |
| `overall_status` | `fail` |
| `worst_window` | **`W1`** |
| W1 `false_exclusion_rate` | **`1.0000`**（gate 阈 `0.10` 的 10×） |
| W1 `candidate_triggered` count | 2（< helper `GATE_MIN_WINDOW_SAMPLE = 20`） |
| 4 window false_exclusion_rate | W1=1.00 / W2=0.52 / W3=0.50 / W4=0.54（**全部** > 0.10 gate） |
| 4 window survival_case_preservation | **全部 0.0** |
| triggered_paired vs blocked_paired | 每个 window 都相等（触发 = 阻塞，没有"软阻止"） |
| 7 gate 状态 | 全部 fail |
| `final_test_touched` | `false` |
| DB / market_data.db / backup count | 三组 fingerprint **unchanged** |
| **结论** | **v1 不 eligible**；fail 是 legal fail，不是 pipeline error |

## 3. v1 root cause summary

postmortem report §10 列出的 5 个 hypothesis（本节复述，不修改）：

| # | Hypothesis | 证据 |
|---|---|---|
| **H1** | candidate 的 risk_score **跨 window 分布不可比** —— 同样 risk_score=0.65 在 W1 是 ~p98 长尾，在 W4 接近 mean。固定 global threshold 会在不同 regime 上给出极端不同的触发率。 | postmortem §6 trigger rate 跨 window 1 : 24（W1=1.8% vs W4=44.6%） + §7 risk_score quantile 表 |
| **H2** | seed features 看起来更像 **regime classifier**（描述当前趋势 / 偏离 / shock），而不是 **exclusion-risk classifier**（区分"会反转的 survivor"vs"不会反转的 not-survivor"）。 | postmortem §3 全 4 window false_exclusion_rate ≥ 0.5；survival_case_preservation 全 0.0 across all windows |
| **H3** | seed coefficients **极性可能颠倒**：candidate 把 `pos20` 高 + `avgo_minus_soxx_20d` 高（相对强势）当作 "overheat → 易反转 → 应排除"；但真实数据中这些 feature 处于高位的 row 反而是**继续上涨**的 survivor —— 至少在 W1 这样的早期 bull 阶段。 | postmortem §9 W1 case 2: pos20=0.90, avgo_minus_soxx_20d=0.06 → actual=up；触发 case 100% 是 survivor |
| **H4** | candidate 的 **damping feature**（`peer_5d_aligned_pct` 系数 -0.8、`market_trend_strength` 系数 -0.7）在很多 W1 row 上 = 0（peer_momentum_regime=weak / 早期 trend 未确立），无法消减"+ 系数"产生的 risk → high bucket 触发。 | postmortem §4.1 case 1: peer=0, trend=0；§4.2 case 2: peer=0, trend=1 |
| **H5** | candidate v1 缺少 **min trigger support guard** 与 **calibration**。helper 已有 `GATE_MIN_WINDOW_SAMPLE = 20`，但 candidate 自身没有"低样本不下结论"机制；同时 risk_score 没有校准到 observed false_exclusion probability，导致 score=0.65 在不同 window 含义不一致。 | postmortem §6 W1 / W3 触发数 < 20 直接 trigger min_sample fail；§7 跨 window trigger_mean 都 ≈ 0.65 ~ 0.71，但 outcomes 完全不同 |

## 4. v2 launch review 目标（8 问）

v2 launch review 必须**回答以下 8 个问题**；本文**不**给答案，只列问题作为 review session 的输入：

| # | 问题 | 与 hypothesis 的关系 |
|---|---|---|
| 1 | v2 是继续做 **fixed global threshold**，还是 **regime-aware / window-aware threshold**？是否需要"局部归一化 risk_score 后再用全局 threshold"？ | H1 / H5 |
| 2 | risk_score 是否应该 **校准到 observed false_exclusion probability**（如 isotonic / Platt / 分位归一），让跨 window / 跨 regime 含义一致？ | H1 / H5 |
| 3 | v2 如何避免**误杀 strong survivor**？是否需要"survivor-protection feature"或"continuation-of-trend protection"层？ | H2 / H3 |
| 4 | v2 如何**区分 overheat risk 与 false-exclusion risk**？是否需要把 candidate 拆成"高位提示"+"实际 exclusion 决策"两个 layer，让前者保留诊断价值，后者由 calibration / abstain 控制？ | H2 / H3 |
| 5 | 是否需要 **candidate-level minimum trigger support guard**（区别于 helper `GATE_MIN_WINDOW_SAMPLE`）？例如 candidate 在低样本 / 低 confidence 下 abstain（不触发）而非误判？ | H5 |
| 6 | `monthly_shock` 是否保留？（中位 0.000 across all windows；稀疏二值化；对 W1 触发 0 贡献） | H4 + 数据观察 |
| 7 | `market_trend_strength` 是否需要从"简单降风险"改为"**保护强趋势 continuation**"语义？是否需要 trend regime 与 trigger 的非线性交互？ | H3 / H4 |
| 8 | v2 如何**防止从 v1 fail 数据直接反推参数**？v2 design 参数来源**应是**先验 / 文献 / 工程判断；validate 阶段**才判读** v1 baseline，不是参数来源 | postmortem §12 Q7 |

## 5. v2 candidate design constraints

v2 必须满足以下硬约束（违反任一 → launch review 拒绝）：

| # | 约束 | 理由 |
|---|---|---|
| 1 | v2 **不得**直接复制 v1 SEED coefficients 作为起点 | 等价于"微调 v1"，违反 H3 极性疑虑 |
| 2 | v2 **不得**用 v1 fail 结果（`20260507_065417` baseline）反推具体参数（threshold / coefficients / cutoffs） | postmortem §12 Q7；防止 first-fail-driven 调参 |
| 3 | v2 **不得** sweep / grid search / hyperparameter optimization 在 v1 baseline 上 | 同上 |
| 4 | v2 必须保持 **read-only candidate**（与 v1 一致；不影响 final prediction） | 与 Step 2G boundary / Step 3R-3 design §11 一致 |
| 5 | v2 必须保持 **sidecar 形式**（不进入 production main path / Streamlit / trading） | 同上 |
| 6 | v2 **不得**启 hard / forced / `anti_false_exclusion_triggered` | Step 2G NO-GO；与 v1 / 3R-0 / 3R-4 一致 |
| 7 | v2 **不得**写 DB / 不得改 DB schema / 不得碰 prediction_store / outcome_capture 写路径 | DB read-only invariant |
| 8 | v2 **不得**触碰 2026 final-test range；cutoff 仍锁 `"2026-01-01"`；6 层 hard stop 全部保留 | 永久封禁 |
| 9 | v2 **不得**接 yfinance / requests / urllib / 任何网络 / trading API | 与 v1 isolation 一致 |
| 10 | v2 必须复用 v1 的 wrapper（`build_real_validation_inputs`）+ adapter / helper 接口；**不**改这些已 merge 模块 | adapter / helper 是 3R-4 protocol，v2 无权改 |
| 11 | v2 **不得**让 `_PROTECTION_LAYER_CONNECTED` 翻 True；**不得**让 `hard_gate_status.protection_layer_connected` 自动 pass | 永久封禁 |
| 12 | v2 输出 schema **必须**仍是 `continuous_smoothing_candidate.v1`（或显式 `.v2` 升级版本，但 adapter / helper 必须接受） | adapter / helper 兼容 |
| 13 | v2 **不得** import `services.continuous_smoothing_candidate`（v1）作为基础 —— 必须独立模块（如 `services/continuous_smoothing_candidate_v2.py`），可以读取 v1 模块仅用于参考接口签名 | 防止 v1 v2 互相污染 |
| 14 | v2 **不得**改任何已 merge 测试 | 兼容性保障 |
| 15 | v2 **不得**触发 retry-until-pass；single real run + result checkpoint 是唯一验证途径 | 与 3R-3.3C-C-C 一致 |

## 6. possible design directions（仅方向；无具体参数）

v2 可以考虑的设计方向（**不**给具体公式 / 系数 / 阈值 / 分位 / 校准曲线 / 网络结构）：

| # | 方向 | 关联 hypothesis | 概念解释（non-prescriptive） |
|---|---|---|---|
| 1 | **window-aware risk_score normalization** | H1 / H5 | 让 score 在每个 window / regime 内归一到可比尺度（如 quantile / mean-centering），threshold 在归一后空间生效 |
| 2 | **regime-aware threshold policy** | H1 | 不同 regime 用不同的"触发判定"，但保持 candidate 作为整体 read-only sidecar |
| 3 | **candidate-level minimum trigger support guard** | H5 | candidate 自身在"信号不足 / 低 confidence"下输出 `risk_bucket = abstain`，不让 adapter 把它视为 trigger |
| 4 | **survivor-protection feature** | H2 / H3 | 引入一个 feature，专门识别"强势 + 趋势连续 + 历史 base rate 高"的 row，作为 risk 减项 |
| 5 | **trend-continuation protection** | H3 / H4 | `market_trend_strength` 不只是"trend 强 → 风险低"，而是"trend 强 + AVGO outperform → 极可能 continuation → 不应排除" |
| 6 | **separation between overheat-risk and false-exclusion-risk** | H2 / H3 | candidate 输出两个 sub-score（overheat、exclusion），让 adapter / helper 用 exclusion sub-score 做触发；overheat 仍用于诊断 |
| 7 | **risk_score calibration to observed false_exclusion probability** | H1 / H5 | 用先验或历史（不限于 v1 baseline）做单调校准，让 score = P(survivor被误排) 的近似 |
| 8 | **candidate confidence / abstain mode** | H5 | candidate 输出 `confidence`；adapter 在低 confidence 下视为 not_triggered |
| 9 | **feature set 重新审计**（包含 monthly_shock 必要性 / market_trend_strength 语义重写） | H4 + Q6 + Q7 | review feature 是否每个都"对 outcome 有信号"，删除 / 重写无信号 feature |
| 10 | **windowed-prior 而不是 windowed-fit** | H1 + Q8 | 如果做 window-aware，参数应来自先验 / 文献，不来自 v1 baseline 拟合 |

> 上面 10 个方向**互不互斥**；v2 design 选哪几条由 launch review 决定。本文**不**做选型。

## 7. validation requirements

v2 必须**完整重走**以下 8 步流程（每一步都是独立 review gate；缺一不可）：

| # | 步骤 | 范围 | 输出 |
|---|---|---|---|
| 1 | **v2 design**（独立文档） | feature 集合 / score 定义 / threshold policy / abstain rule / calibration approach | `tasks/step_3r3_continuous_smoothing_v2_candidate_design.md`（命名待定） |
| 2 | **v2 design checkpoint** | 状态归档 | `tasks/step_3r3_continuous_smoothing_v2_candidate_design_checkpoint.md` |
| 3 | **v2 implementation** | 新增 `services/continuous_smoothing_candidate_v2.py`（独立模块；不 import v1） | merged 实现 |
| 4 | **v2 tests** | 新增 `tests/test_continuous_smoothing_candidate_v2.py`：unit tests（公式正确）+ isolation tests（forbidden imports / 字符串扫）+ schema tests | full pytest 零回归 |
| 5 | **adapter / helper compatibility**（不改 adapter / helper） | 调 adapter `build_replay_validation_records(..., candidate_name="continuous_smoothing_v2", ...)` + helper `build_regime_validation_report(..., candidate_kind="smoothing", ...)` | 复用现有 isolation；不动 3R-4 protocol |
| 6 | **single real W1-W4 validation run**（一次） | 通过 execution glue（如需新 glue 则独立 design + impl + tests）；同样 cutoff=2026-01-01；threshold lock（v2 自有 lock）；output_dir 新 timestamp | `logs/regime_validation/continuous_smoothing_v2_real_w1_w4_<TS>/` |
| 7 | **v2 result checkpoint** | 同 v1 result checkpoint 风格 + **v1 baseline comparison** | `tasks/step_3r3_continuous_smoothing_v2_real_validation_result_checkpoint.md` |
| 8 | **v1 baseline comparison**（在 result checkpoint 内） | 7 项 metric 对照表（v1 vs v2）；说明 v2 是否 strictly 优于 v1 | result checkpoint §X |

> 任一步 fail → 同样回到 design 层重新设计；**不**自动进入下一步；**不** retry until pass。

## 8. v2 pass criteria

v2 **不能仅"比 v1 好一点"** —— 必须满足以下硬阈才能视为 launch review 通过候选：

| # | 标准 | 量化要求 |
|---|---|---|
| 1 | 7 gates 全部 pass，**或**对未通过的 gate 给出明确 launch review 接受的解释 | helper 7 gate（min_sample / false_exclusion / net_benefit / accuracy_delta / cross_window_variance / survival_case_preservation / no_single_window_collapse）；任一 fail 必须有 review-approved waiver，否则视为 fail |
| 2 | `worst_window` 不 collapse | worst_window 的 false_exclusion_rate 不超过 helper 阈 `0.10`；不出现 v1 那样的 1.0 触顶 |
| 3 | `false_exclusion_rate` **显著低于** v1 的对应 window | 4 个 window 全部 < v1 对应值；且**至少**全部 ≤ 0.10（gate 阈） |
| 4 | `survival_case_preservation` **显著高于** v1 的 0.0 | 至少 4 个 window 全部 > 0；review 接受具体阈由 helper protocol 决定 |
| 5 | W1 不再出现"2/2 false exclusion"的极端结果 | W1 false_exclusion_rate ≤ helper 阈 0.10 |
| 6 | cross-window trigger rate 不极端失衡 | helper `cross_window_variance` gate pass；触发率跨 window 不出现 1 : 24 量级差距 |
| 7 | `final_test_touched = false`；`final_test_refusal = false` | 与 v1 相同 invariant；2026 不被消费 |
| 8 | DB / market_data.db / backup count **未变** | 与 v1 同样 byte-for-byte 不变 |
| 9 | output 4 文件 schema valid + untracked + 不 commit raw | 与 v1 同样 untracked；不 commit |
| 10 | v2 result checkpoint 必须包含 v1 baseline comparison 表 | 量化对比，至少 v1 fail metric 对照 v2 metric |

> v2 即便满足以上 10 项，**也不**自动启 hard / Gate 5 / Gate 6 / `_PROTECTION_LAYER_CONNECTED` / 3R-5 / 3R-6 —— 仅允许进入 review。

## 9. no-go rules

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
| 18 | 在 launch review design 阶段提具体新 threshold / 新 coefficient（必须在 v2 design 阶段） |
| 19 | 在 launch review design 阶段实现 v2 |
| 20 | 让 v2 fail 触发 retry / sweep / 调参 |

## 10. output schema

设计 launch review report schema：`continuous_smoothing_v2_launch_review.v1`（13 字段）：

| 字段 | 类型 | 说明 |
|---|---|---|
| `schema_version` | str | `"continuous_smoothing_v2_launch_review.v1"` |
| `source_v1_baseline` | dict | `{"output_dir": "logs/regime_validation/continuous_smoothing_v1_real_w1_w4_20260507_065417", "main_commit": "fc44bcf", "result_checkpoint_commit": "75f0ad5", "postmortem_report_commit": "fc44bcf"}` |
| `v1_failure_summary` | dict | `{report_status, overall_status, worst_window, w1_false_exclusion_rate, survival_case_preservation_per_window, gate_status}` —— 全部从 v1 result checkpoint / postmortem report 复述；不重新计算 |
| `v2_design_questions` | list[str] | 8 个 launch review 问题（§4） |
| `allowed_design_directions` | list[str] | 10 个 possible design directions（§6）的 label；**不**含具体参数 |
| `forbidden_actions` | list[str] | 复述 §9 的 20 项 no-go |
| `validation_requirements` | list[dict] | 8 步 validation 流程（§7）+ 每步 acceptance |
| `pass_criteria` | list[dict] | 10 项 v2 pass standard（§8） |
| `baseline_comparison_plan` | dict | 描述 v2 result checkpoint 必须包含的 v1 vs v2 对比表结构（不实际填值） |
| `design_constraints` | list[str] | 复述 §5 的 15 项 design constraint |
| `recommended_next_step` | str | 二选一：`"proceed_to_continuous_smoothing_v2_design"` 或 `"abandon_continuous_smoothing_candidate_layer"` |
| `unlock_3r5_3r6` | bool | **永远 false**；launch review 不解锁 3R-5 / 3R-6 |
| `auto_promotion` | bool | **永远 false**；v2 pass 不自动 promotion |

## 11. recommended_next_step

**`proceed_to_continuous_smoothing_v2_design`**

判定理由（基于 postmortem §13 已给出的 recommendation `launch_continuous_smoothing_v2_design_review`）：

| 评估项 | 结果 | 解读 |
|---|---|---|
| postmortem 是否给出充足 root cause | ✅ 5 个 hypothesis（H1-H5） | 有清晰的 review 输入 |
| candidate 是否仍**有信号** | ⚠️ 部分有（W2 net_benefit 微正；triggered vs non-triggered risk_score mean 有分离） | 不需要 abandon redesign from candidate layer |
| 数据是否健康 | ✅ 639 / 526 records；4 window 全有 records；DB unchanged | v2 可以在同一 baseline 上独立验证 |
| pipeline 是否健康 | ✅ 13/13 acceptance pass；4 文件 schema valid | 不是 pipeline 问题 |
| v2 是否能在不破坏 v1 invariant 下设计 | ✅ §5 15 项 design constraint 都可满足 | v2 可独立模块；read-only / sidecar / DB-unchanged 全部保留 |
| launch review 必要性 | ✅ 8 个 design question 必须先 review，再写 v2 design | 防止 v2 重复 v1 错误 |

> **本 recommendation 不解锁 3R-5 / 3R-6**；不允许 auto promotion；不允许在本 launch review 阶段实现 v2 / 调 v1 / 触碰 2026。

## 12. 与 3R-5 / 3R-6 关系

| 关系 | 状态 |
|---|---|
| 当前 v1 fail 是否 block 3R-5 formula | ✅ 是；fail 阻止 promotion |
| 当前 v1 fail 是否 block 3R-6 simulator | ✅ 是；3R-6 必须先过 3R-5 |
| 本 launch review 是否解锁 3R-5 / 3R-6 | ❌ **永远不**；launch review 仅产出"是否进 v2 design"决定 |
| v2 launch review pass 是否解锁 3R-5 / 3R-6 | ❌ 否；只解锁 v2 design + impl + validation |
| v2 single real run pass 是否解锁 3R-5 / 3R-6 | ❌ 否；只允许进入 3R-5 launch review（**新一轮**独立 review） |
| v2 single real run pass 是否自动启 hard / Gate 5 / Gate 6 / `_PROTECTION_LAYER_CONNECTED` | ❌ **永远不** |
| 3R-5 / 3R-6 启动条件 | 必须先：v2 launch review pass → v2 design + checkpoint → v2 impl + tests → v2 single real run → v2 result checkpoint → **新一轮** 3R-5 launch review pass |

## 13. 严守边界

本文是**纯 launch review design markdown**：

- ❌ 没改任何代码（`services/*` / `ui/*` / `tests/*` / `scripts/*` 全部未触碰）
- ❌ 没改 DB schema
- ❌ 没写 DB
- ❌ 没运行 replay
- ❌ 没**重新运行** real validation（baseline 仍是 v1 `20260507_065417` run）
- ❌ 没运行 prepare-only smoke
- ❌ 没读 v1 4 个 raw output json 任一字节（仅引用 path / 复述 result checkpoint + postmortem 已固化的字段）
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
- ❌ 没改 Step 3R-3.3 / 3R-3.3A / 3R-3.3B / 3R-3.3C 系列 / 3R-3.3C-D / 3R-3.3C-D1 已 merge 文档 / 实施
- ❌ 没改 Step 2G-8D / 8D.1A / 8D.2 / 8D.3 / 8D.4 文档或代码
- ❌ 没把 W4 / smoke / `logs/regime_validation/` / v1 raw output / `logs/prediction_log.jsonl` / DB backup / `agent_loop.py` / `.claude/worktrees/` 任一 commit 进 main
- ❌ 没创建任何新的 `logs/regime_validation/*` 子目录
- ❌ 没运行 `pytest`（本轮纯文档；测试基线维持 commit `7812b10` 时的 **2905 / 0 failed / 10 skipped**）
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*`
- ❌ 没用 v1 baseline 数据反推 v2 任何具体参数
- ❌ 没让 v1 fail 触发 retry / sweep / grid search
- ❌ 没让 launch review 自动 promotion / 自动解锁 3R-5 / 3R-6
- ✅ 只新增 1 份 markdown launch review design 文档（本文件）
