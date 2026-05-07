# Step 3R-3.3H — Abandon Continuous Smoothing Candidate Layer Decision Checkpoint

> 本文是 **abandon decision checkpoint markdown** —— 不改代码、不删代码、不删 raw output、不删 docs、不写 DB、不重跑 replay / validation、不 commit / push、不接 trading API、不启 hard / forced、不改 required、不触碰 2026 final-test range、不 add `logs/regime_validation/` / W4 / smoke output / `logs/prediction_log.jsonl`、不处理 DB backup / stash / `.claude/worktrees/`、不调 v1 / v2 任一 threshold / SEED / coefficient / 工程默认、不 retry / 不 sweep / 不 auto-promotion、不进 v3 / 3R-5 / 3R-6、不改 adapter / helper / 主链。

## 1. 当前完成状态

| 项 | 状态 | 来源 |
|---|---|---|
| v1 candidate design + checkpoint + implementation + checkpoint | ✅ 已 merge | 3R-3 系列 commits |
| v1 real validation single run + result checkpoint | ✅ 已 merge | output `20260507_065417`；commit `75f0ad5` |
| v1 postmortem design + checkpoint + report | ✅ 已 merge | commits `289f97b` / `c5bf686` / `fc44bcf` |
| v2 launch review design + checkpoint | ✅ 已 merge | commits `4fd1278` / `7c1a0e5` |
| v2 candidate design + checkpoint + implementation + checkpoint | ✅ 已 merge | commits `b16fce9` / `7eda5b4` / `ce8b81e` / `95ded24` |
| v2 execution path design + checkpoint + implementation + checkpoint | ✅ 已 merge | commits `18a41d8` / `fe76252` / `9192a5a` / `0a753c2` |
| v2 real validation single run + result checkpoint | ✅ 已 merge | output `20260507_091823`；commit `3de3cc5` |
| v2 failure postmortem comparison review design + checkpoint | ✅ 已 merge | commits `f1fbdb5` / `5b5ed90` |
| Step 3R-3.3G1 v2 failure postmortem comparison review report | ✅ 已 merge | commit `cbb42e0` |
| G1 review `recommended_next_step` | `abandon_continuous_smoothing_candidate_layer` | G1 report §14 |
| **本 checkpoint** —— 固化 abandon 决策；保留 v1 / v2 模块 / raw output / docs；明确 blocked path 与 allowed future path | ⏳ **本文**（未 commit） | — |

> abandon decision 已由 G1 review 推荐；本 checkpoint **不删除任何代码 / output / docs**，**不修改任何系统状态**。

## 2. 当前 main 状态

- `main` 最新 commit：`cbb42e0`
- commit message：`docs(contract): Step 3R-3.3G1 v2 failure postmortem comparison review report`
- 上游：`origin/main` 已同步
- 本步骤已 merge 文件：

| 路径 | 类型 |
|---|---|
| 本 checkpoint markdown | 唯一新增 |

测试基线：本步骤纯文档；测试基线维持 commit `0a753c2` 时的 **2986 / 0 failed / 10 skipped**（与 v2 execution path implementation 一致）。

| 项 | 是否触碰 |
|---|---|
| 改代码 | ❌ 否 |
| 删代码 | ❌ 否 |
| 改 / 删 v1 / v2 已 merge 模块 / 测试 / docs | ❌ 否 |
| 改 / 删 v1 / v2 raw output | ❌ 否 |
| 改 DB schema / 写 DB | ❌ 否 |
| 跑 replay / 重跑 real validation | ❌ 否 |
| 调 v1 / v2 任一 threshold / SEED / coefficient / 工程默认 | ❌ 否 |
| 接 yfinance / 网络 / trading API | ❌ 否 |
| 触碰 2026 final-test range | ❌ 否 |
| add `logs/regime_validation/` / W4 / smoke / DB backup / `agent_loop.py` / `.claude/worktrees/` / `logs/prediction_log.jsonl` | ❌ 否 |
| 进 v3 candidate design / 3R-5 formula / 3R-6 simulator | ❌ 否 |
| 启 hard / forced / `_PROTECTION_LAYER_CONNECTED` | ❌ 否 |
| 改 adapter / helper / wrapper / real provider / orchestrator / glue | ❌ 否 |

## 3. decision

**`decision = abandon_continuous_smoothing_candidate_layer`**

含义：

| 项 | 状态 |
|---|---|
| 不再推进 continuous_smoothing 作为 exclusion candidate | ✅ |
| 不再进入 v3 candidate design | ✅ 永久封禁 |
| 不再跑 v1 / v2 retry | ✅ 永久封禁 |
| 不从 v1 / v2 fail 反推参数（threshold / SEED / family 公式 / calibration） | ✅ 永久封禁 |
| 不进入 Step 3R-5 / 3R-6 | ✅ 永久封禁（此 candidate 路径） |
| 不启 hard / forced / required / `_PROTECTION_LAYER_CONNECTED` | ✅ 永久封禁 |
| 不删除任何已 merge 模块 / docs / output | ✅ |

## 4. evidence summary

| evidence | value | interpretation |
|---|---|---|
| v1 `overall_status` | `fail` | first real run candidate-level fail |
| v2 `overall_status` | `fail` | repeat fail with re-engineered candidate |
| v1 `records_adapted` | 526 | same input as v2 |
| v2 `records_adapted` | 526 | same input as v1 |
| v1 W1 `false_exclusion_rate` | **1.0000** | W1 触发 2 条全是 survivor |
| v2 W1 `false_exclusion_rate` | **1.0000** | W1 触发 1 条仍是 survivor；持平 |
| v1 `survival_case_preservation`（all windows） | 0.0 / 0.0 / 0.0 / 0.0 | candidate-layer binary actuator 结构问题 |
| v2 `survival_case_preservation`（all windows） | 0.0 / 0.0 / 0.0 / 0.0 | 持平；abstain 没改善 |
| v1 triggered total | 136 | 25.9% trigger rate |
| v2 triggered total | 97 | 18.4% trigger rate（v2 −29%） |
| **A both-triggered count** | **88**（16.7%） | v1 ∧ v2 都触发的 row |
| **A both-triggered `pc_true_rate`** | **0.5909** | 高于 baseline 0.481 **+11pp**；agreement zone **反向** |
| B v1-only count / pc_true_rate | 48 / 0.4583 | ≈ baseline；abstain 没偏向 |
| C v2-only count / pc_true_rate | 9 / 0.3333 | 唯一优于 baseline 但 N=9 太小 |
| D neither count / pc_true_rate | 381 / 0.4619 | ≈ baseline；候选不区分 |
| **v2 abstain count** | **0** | abstain mode 在本 run **从未激活**；trigger_support 全 ≥ 0.5 |
| v3 ALL-of criteria（5 项） | **failed**（条件 4：意义结构性改善需改 adapter / helper / 主链） | v3 不满足 |
| abandon ANY-of criteria（5 项） | **5/5 全部满足** | abandon 决定有数据支持 |

## 5. why not v3

| # | 不进入 v3 的理由 |
|---|---|
| 1 | **v3 ALL-of criteria 不满足**（G1 review §12.1）：条件 4（"不需要改 adapter / helper / 主链"）失败 —— 任何意义结构性改善（graded actuator / warn / downgrade-confidence）都需改 adapter，超出 candidate layer 边界 |
| 2 | **A both-triggered 反向** 是 candidate-layer 根本结构问题：v1 ∧ v2 在 88 cases（16.7%）一致触发，但其中 **59% 是 survivor**（高于 baseline 11pp）—— candidate 在 agreement zone 与 outcome **反向** |
| 3 | **C v2-only subset N=9 太小**：唯一显示弱信号的 subset（pc_true_rate=0.333 < baseline 0.481）只有 9 条 row，统计上不显著；不能作为 v3 design 基础 |
| 4 | **trigger quality 在 v1 → v2 没有提升**：v2 reduce 的 48 个 v1_only（B 子集）pc_true_rate=0.458，与 baseline 几乎一致；v2 abstain 没有偏向地删除"应排除"或"应保留"row |
| 5 | **abstain mode 在 v2 从未激活**：v2 design 的核心新机制（abstain protect survivor）count=0；v2 reduction 来自 family 重新加权而非 abstain；abstain 的"保护 survivor"设计 inactive |
| 6 | **改 actuator semantic 等于改 3R-4 protocol**：超出 candidate layer 边界；如需，必须独立 launch review，不属 v3 候选范围 |
| 7 | **从 fail 反推参数被永久禁止**：v3 设计若出现，参数必须来自先验 / 文献 / 工程判断，不能从 v1 / v2 fail baseline 拟合 —— 但本次 v1 + v2 经验显示 candidate-layer binary actuator 与 momentum regime feature 组合不能产生 prediction-error signal，无新先验路径 |

## 6. what abandon means

| abandon **means** |
|---|
| ✅ stop treating continuous_smoothing as **exclusion candidate** |
| ✅ stop candidate-level validation for this branch（不再设计 / 实施 / 跑 v3 / v4） |
| ✅ preserve v1 / v2 as **diagnostic artifacts**（已 merge 模块作为 read-only 历史 artifact） |
| ✅ preserve raw outputs as **local untracked evidence**（v1 / v2 4 文件保持 untracked；不 commit；不删除） |
| ✅ preserve docs / commits / tests（全部 frozen；不修改） |
| ✅ future reuse must happen under **separate review / explanation layer launch review**（独立 design + checkpoint + impl + validation；不复用 candidate-layer pass / fail 语义） |
| ✅ 把 signal 重定位到 review / explanation 用途必须独立流程，不在 abandon 范围 |

## 7. what abandon does **not** mean

| abandon **does not mean** |
|---|
| ❌ 删除 `services/continuous_smoothing_candidate.py`（v1） |
| ❌ 删除 `services/continuous_smoothing_candidate_v2.py`（v2） |
| ❌ 删除 `scripts/run_continuous_smoothing_validation.py`（v1 orchestrator） |
| ❌ 删除 `scripts/run_continuous_smoothing_validation_v2.py`（v2 orchestrator） |
| ❌ 删除 `scripts/run_real_continuous_smoothing_validation.py`（wrapper） |
| ❌ 删除 `scripts/run_real_continuous_smoothing_validation_execute.py`（v1 glue） |
| ❌ 删除 `scripts/run_real_continuous_smoothing_validation_execute_v2.py`（v2 glue） |
| ❌ 删除 `services/real_regime_label_provider.py` |
| ❌ 删除任何已 merge 测试 |
| ❌ 删除任何 raw output（v1 / v2 `output_dir` 4 文件保持 untracked） |
| ❌ 删除任何 docs / checkpoint markdown |
| ❌ 修改 adapter / helper / orchestrator / wrapper / real provider / labels builder 行为 |
| ❌ 修改任何历史 result / commit / 测试基线 |
| ❌ 把 fail 当作 pipeline failure（v1 / v2 fail 是 legal fail；execution glue / wrapper / adapter / helper 全部 plumbing 13/13 acceptance pass） |
| ❌ 修改 v1 / v2 任一参数 / threshold / SEED / coefficient / 工程默认 |
| ❌ 撤销 v1 / v2 已 merge 的 commits |
| ❌ 撤销 v1 / v2 result checkpoint |
| ❌ 撤销 v2 failure review |

## 8. preserved artifacts

下列 artifact **全部保留**（不删除、不修改）：

### 8.1 services / scripts（已 merge）

| 路径 | 角色 |
|---|---|
| `services/continuous_smoothing_candidate.py` | v1 candidate（read-only diagnostic baseline） |
| `services/continuous_smoothing_candidate_v2.py` | v2 candidate（read-only diagnostic baseline） |
| `services/real_regime_label_provider.py` | real regime label provider（与 candidate 无关；可被 review/explanation layer 复用） |
| `services/regime_labels_builder.py` | regime labels builder（protocol 层；3R-2） |
| `services/regime_validation_helper.py` | helper（protocol 层；3R-4.2） |
| `services/replay_validation_record_adapter.py` | adapter（protocol 层；3R-4.3A） |
| `scripts/run_continuous_smoothing_validation.py` | v1 orchestrator |
| `scripts/run_continuous_smoothing_validation_v2.py` | v2 orchestrator |
| `scripts/run_real_continuous_smoothing_validation.py` | wrapper |
| `scripts/run_real_continuous_smoothing_validation_execute.py` | v1 execution glue |
| `scripts/run_real_continuous_smoothing_validation_execute_v2.py` | v2 execution glue |

### 8.2 raw output（local untracked）

| 路径 | 状态 |
|---|---|
| `logs/regime_validation/continuous_smoothing_v1_real_w1_w4_20260507_065417/` | v1 raw 4 文件；untracked；不进 main；不删除 |
| `logs/regime_validation/continuous_smoothing_v2_real_w1_w4_20260507_091823/` | v2 raw 4 文件；untracked；不进 main；不删除 |

### 8.3 docs / checkpoint markdown（已 merge，全部保留）

涵盖（不限于）：

- v1 design + checkpoint + result checkpoint + postmortem design + postmortem checkpoint + postmortem report
- v2 launch review design + checkpoint
- v2 candidate design + checkpoint + implementation checkpoint
- v2 execution path design + checkpoint + implementation checkpoint
- v2 result checkpoint + v1 baseline comparison
- v2 failure review design + checkpoint + G1 review report
- step_1_contract_pipeline_summary.md §43-46

### 8.4 测试

`tests/test_continuous_smoothing_candidate.py` / `tests/test_continuous_smoothing_candidate_v2.py` / `tests/test_run_continuous_smoothing_validation.py` / `tests/test_run_continuous_smoothing_validation_v2.py` / `tests/test_run_real_continuous_smoothing_validation.py` / `tests/test_run_real_continuous_smoothing_validation_execute.py` / `tests/test_run_real_continuous_smoothing_validation_execute_v2.py` / `tests/test_real_regime_label_provider.py` —— 全部保留；测试基线 2986 / 0 failed / 10 skipped 不变。

## 9. blocked paths

下列路径**全部 block**（永久封禁，除非另开独立流程）：

| # | blocked path | 理由 |
|---|---|---|
| 1 | Step 3R-3.3F v3 candidate design | abandon decision；不再进 v3 candidate |
| 2 | Step 3R-5 formula | v1 + v2 fail；abandon 不解锁 |
| 3 | Step 3R-6 simulator | 同上 |
| 4 | hard / forced / `anti_false_exclusion_triggered` | 永久封禁（与 v1 / 3R-0 / 3R-4 一致） |
| 5 | `_PROTECTION_LAYER_CONNECTED` 翻 True | 永久封禁 |
| 6 | `hard_gate_status.protection_layer_connected` 自动 pass | 永久封禁 |
| 7 | `hard_exclusion_allowed` / `primary_blocker` 派生改动 | 永久封禁 |
| 8 | production promotion（continuous_smoothing 进 prediction main path） | 永久封禁 |
| 9 | trading integration（`longbridge` / `broker` / `paper_trade`） | 永久封禁 |
| 10 | 04 / 05 / 07 required upgrade | Step 2G 全程边界 |
| 11 | 触碰 2026 final-test range | 永久封禁 |
| 12 | sweep / grid search / hyperparameter optimization | 永久封禁 |
| 13 | retry-until-pass | 永久封禁 |
| 14 | 用 v1 / v2 fail baseline 反推任何参数 | 永久封禁 |
| 15 | 改 v1 / v2 任一已 merge 模块 / 测试 / docs | 永久封禁 |
| 16 | 改 adapter / helper / orchestrator / wrapper / real provider / labels builder | 永久封禁（除独立 launch review） |
| 17 | auto-promotion | 永久封禁 |

## 10. allowed future path

唯一允许的未来路径：

**`continuous_smoothing_review_layer_launch_review`**（独立流程，不在本 checkpoint 范围）

| 项 | 内容 |
|---|---|
| 路径含义 | 把 continuous_smoothing signal 从 **exclusion candidate** 重定位为 **review / explanation / diagnostic layer**（如 dashboard 标注 high-momentum regime / 显示 risk_score 给人类 review；但**不**进入 candidate exclusion 决策） |
| 是否直接 block prediction | ❌ 否 |
| 是否写 DB | ❌ 否 |
| 是否启 hard | ❌ 否 |
| 是否进 trading | ❌ 否 |
| 是否复用 v1 / v2 candidate-layer 的 pass / fail 语义 | ❌ 否（review 是 explanatory，**不**判 pass/fail） |
| 是否需要独立 design + checkpoint + impl + validation | ✅ 必须 |
| 是否解锁 3R-5 / 3R-6 | ❌ 永久不（review layer 不是 candidate layer 的替代品） |
| 是否在本 abandon checkpoint 范围 | ❌ 否（仅作为 allowed future path 记录） |
| 触发条件 | 必须用户**单独**启动 launch review；不能从本 abandon 自动延伸 |

> review/explanation layer **不**意味"修复"v1 / v2 的 fail；它意味**重定位** signal 的用途。如果用户决定不重定位，candidate-layer continuous_smoothing 工作就此**永久 frozen**，作为已 merge 的 read-only diagnostic baseline。

## 11. no-go rules

| # | 条件 |
|---|---|
| 1 | 调 v1 / v2 任一 `candidate_threshold` / SEED / coefficient / family 公式 / 工程默认 / calibration |
| 2 | sweep / grid search / hyperparameter optimization |
| 3 | retry-until-pass（v1 / v2 fail → 不重跑） |
| 4 | 重新跑 v1 / v2 / 任一 candidate validation |
| 5 | 进入 Step 3R-3.3F v3 candidate design |
| 6 | 进入 Step 3R-5 formula |
| 7 | 进入 Step 3R-6 simulator |
| 8 | 启 hard / forced / `anti_false_exclusion_triggered` |
| 9 | 让 `_PROTECTION_LAYER_CONNECTED` 翻 True |
| 10 | 改 04 / 05 / 07 required |
| 11 | 删除 v1 / v2 已 merge 模块 / 测试 / docs |
| 12 | 删除 v1 / v2 raw output |
| 13 | 改 adapter / helper / orchestrator / wrapper / real provider / labels builder（3R-4 protocol） |
| 14 | 把 v1 / v2 fail 当 pipeline bug / 修复任何已 merge service |
| 15 | commit raw output（v1 / v2 4 文件仍 untracked） |
| 16 | 触碰 2026 final-test range |
| 17 | 接 yfinance / requests / 任何网络 / trading API |
| 18 | auto-promotion / 自动解锁 3R-5 / 3R-6 |
| 19 | 把 abandon 自动延伸为 review/explanation layer 实施（必须独立 launch review） |
| 20 | 用 v1 / v2 fail baseline 数据反推任何具体新参数 |
| 21 | monkey-patch / 跑 v1 冒充 v2 / 跑 v2 冒充任何后续候选 |

## 12. recommended_next_step

**`commit_abandon_decision_checkpoint`**

之后可选（**独立流程**，不在本 checkpoint 范围）：

| 选项 | 含义 |
|---|---|
| **close continuous_smoothing candidate branch** | 把 candidate-layer 工作 frozen 在当前 main 状态；v1 / v2 模块保留为 read-only diagnostic；不再有 candidate-side 改动 |
| **open separate review/explanation layer launch review**（用户单独触发） | 启动 `continuous_smoothing_review_layer_launch_review`；新 design / checkpoint / impl / validation；与 candidate-layer 完全分离；**不**复用 pass / fail 语义 |
| **return to broader prediction / exclusion roadmap** | 回到 prediction / exclusion 整体 roadmap；可能在 Step 3R-3 之外的 candidate 路径继续；与 continuous_smoothing 无关；独立 launch review |

下一步**不**允许：

- ❌ 直接进入 v3 candidate design
- ❌ 直接进入 Step 3R-5 / 3R-6
- ❌ 直接修改 adapter / helper / 主链
- ❌ 删除 v1 / v2 任一 artifact
- ❌ 自动 promotion / 自动启 hard / Gate 5 / Gate 6 / `_PROTECTION_LAYER_CONNECTED`
- ❌ 调 v1 / v2 任一参数
- ❌ 用 v1 / v2 fail 数据反推任何具体新参数

## 13. 严守边界

本文是**纯 abandon decision checkpoint markdown**：

- ❌ 没改任何代码（`services/*` / `ui/*` / `tests/*` / `scripts/*` 全部未触碰）
- ❌ 没**删除**任何代码（v1 / v2 模块全部保留）
- ❌ 没改 / 删 v1 / v2 raw output（`output_dir` 4 文件全部保留 untracked）
- ❌ 没改 / 删任何 docs / checkpoint markdown
- ❌ 没改 / 删任何已 merge 测试
- ❌ 没改 DB schema / 没写 DB
- ❌ 没运行 replay
- ❌ 没**重新运行** real validation（baseline 仍是 v1 `20260507_065417` + v2 `20260507_091823`）
- ❌ 没运行 prepare-only smoke
- ❌ 没修改 v1 / v2 raw output json 任一字符
- ❌ 没改 `run_predict` / `predict.py` / `scanner.py` / `prediction_store.py` / `app.py`
- ❌ 没改 `services/regime_features_builder.py` / `regime_labels_builder.py` / `regime_validation_helper.py` / `continuous_smoothing_candidate.py`（v1）/ `continuous_smoothing_candidate_v2.py` / `replay_validation_record_adapter.py` / `historical_replay_training.py` / `real_regime_label_provider.py` / 任何 ui 模块 / 任何 builder
- ❌ 没改 `scripts/run_continuous_smoothing_validation.py`（v1 orchestrator）/ `run_real_continuous_smoothing_validation.py`（wrapper）/ `run_real_continuous_smoothing_validation_execute.py`（v1 glue）/ `run_continuous_smoothing_validation_v2.py`（v2 orchestrator）/ `run_real_continuous_smoothing_validation_execute_v2.py`（v2 glue）
- ❌ 没改任一已 merge 测试
- ❌ 没新增 v3 任何代码 / 任何测试 / 任何脚本
- ❌ 没新增 review/explanation layer 任何代码 / 测试（独立 launch review；不在本 checkpoint）
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
- ❌ 没让 abandon 自动延伸为 review/explanation layer 实施（独立 launch review）
- ❌ 没让 abandon 自动 promotion / 自动解锁 3R-5 / 3R-6
- ❌ 没 monkey-patch / 没跑 v1 / v2 / v3 任一冒充另一版本
- ✅ 只新增 1 份 markdown abandon decision checkpoint 文档（本文件）
