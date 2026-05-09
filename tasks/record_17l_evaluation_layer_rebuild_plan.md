# 17L记录：Evaluation Layer Rebuild Plan

> 本记录是 **Step 17L：Evaluation Layer 重建计划**——九分支按层重建中
> 的**第八层**（Branch 8）。1.0 canonical / 16A blueprint / 16B inventory /
> 16C target dataflow & contract decision / 16D isolation & quarantine
> plan / 16E core chain refactor plan / 16F no-patching principle / 16G
> full module decomposition standup / 16H repository clearing decision
> table / 16I core chain rebuild execution plan / 17A PR-B standard
> payload skeleton / 17B PR-C peer_alignment 抽公共模块 / 17C PR-D
> main_projection 去 `exclusion_result` 形参 / 17D layer-by-layer rebuild
> governance / 17E Data Layer Rebuild Plan / 17F Feature Layer Rebuild
> Plan / 17G Projection Layer Rebuild Plan / 17H Exclusion Layer Rebuild
> Plan / 17I Confidence Layer Rebuild Plan / 17J Final Report Layer
> Rebuild Plan / 17K Review & Learning Layer Rebuild Plan 已全部入 main
> （main 最新 commit `d0057c5`）。
>
> 本轮**只**写计划文档：未改业务代码、未新增测试、未删除文件、未移动
> 文件、未修改 `.gitignore`、未处理 handoff、未处理 logs / DB backup /
> `.claude/worktrees/`、**未处理 `avgo_agent.db`**、未跑 replay /
> validation / historical evaluation、未写 DB / 未改 DB schema、未默认
> 迁移 `run_predict` 到 V2、未接 trading、未输出 buy / sell / hold /
> hard / forced / required、未进入 3R-5 / 3R-6、未启动任何代码 PR、
> 未直接跑 2026 holdout、未直接跑 historical replay、未直接修
> calibration、未启动 UI / Bridge / orchestrator 实现任务、未做任何局部
> patch、未 commit / 未 push。
>
> 唯一 deliverable：本文件。
>
> **本记录优先级**：与 17E ~ 17K / 17M 各层 Plan 同级；与 1.0 / 16A /
> 16C / 16D / 16F / 16I / 17D / 17E ~ 17K 协同。冲突仲裁路径与 1.0 §14 /
> 17D §13 一致：旧 records 若与 17L 在 Evaluation Layer 范畴冲突，
> **以 17L 为准**。

---

## 1. Step 17L 目的

把九分支按层重建从 Review & Learning Layer（17K）推进到**第八层
（Evaluation Layer）的具体重建计划**。

**本轮只回答**：

- Evaluation Layer 当前长什么样（模块 inventory + active path）
- Evaluation Layer 目标长什么样（保留 / 迁移 / 隔离 / 删除候选）
- Evaluation Layer 与上下游的边界（prediction_store + outcome_capture ↑
  （**只读**事后批处理）；Confidence calibration_context ↓（离线权重 /
  校准表回到 Confidence System，不沿其他路径回流）；UI ↓（只展示）；
  **不**改写当次任一上游输出）
- `evaluation_result` 标准化规则（与 1.0 §8 Branch 8 / 16A §11 一致）
- **2026 holdout** 规则（与 1.0 §5 rule 8 / 07A §3.2 / 07B §3.2 / 07C §3.2 /
  07D §3.2 / 16C §11 一致）
- **historical replay** 规则（anti-lookahead / frozen data snapshot / raw
  artifact 不进 repo）
- **calibration** 规则（Evaluation → Confidence 单向；不沿其他路径回流；
  不 silent default；不接 trading rule promotion）
- `anti_false_exclusion_dashboard` / contract payload inspector / diff /
  trend / extras_dashboard 归属
- Evaluation Layer 后续可能的代码 PR 候选（**不**执行）
- 与 Review & Learning / UI 的交接

**本轮不回答**：

- 不写 UI 计划（17M）
- 不开任何代码 PR（最早 18A）
- 不动 `avgo_agent.db`、`.gitignore`、handoff、logs / DB backup /
  worktrees
- 不直接跑 2026 holdout（与 17D §11 / 1.0 §5 rule 8 一致）
- 不直接跑 historical replay
- 不直接修 calibration
- 不启动 UI / Bridge / orchestrator 实现任务（与 17D §10 一致）

**本文件性质**：layer rebuild plan（按层计划），不是 design 也不是 impl。

---

## 2. 当前前置条件

| 项 | 状态 |
|---|---|
| 1.0 canonical principles | ✅ commit `5c209bb` |
| 16A architecture reset blueprint | ✅ commit `9b98ad5` |
| 16B module standup ownership inventory | ✅ commit `bdd1314` |
| 16C target dataflow & contract decision | ✅ commit `b05d7c8` |
| 16D isolation / quarantine plan | ✅ commit `694450e` |
| 16E core chain refactor plan | ✅ commit `932d243` |
| 16F architecture reset no-patching principle | ✅ commit `6cfaa9b` |
| 16G full module decomposition standup | ✅ commit `ba6bc7d` |
| 16H repository clearing decision table | ✅ commit `cc4e9ca` |
| 16I core chain rebuild execution plan | ✅ commit `3418911` |
| 17A PR-B standard payload skeleton | ✅ commit `9c779f8` |
| 17B PR-C peer_alignment 抽公共模块 | ✅ commit `08b45c1` |
| 17C PR-D main_projection 去 `exclusion_result` 形参 | ✅ commit `b83d5c5` |
| 17D layer-by-layer rebuild governance | ✅ commit `77777d4` |
| 17E Data Layer Rebuild Plan | ✅ commit `f2cf76e` |
| 17F Feature Layer Rebuild Plan | ✅ commit `a787bf5` |
| 17G Projection Layer Rebuild Plan | ✅ commit `54f74f1` |
| 17H Exclusion Layer Rebuild Plan | ✅ commit `392e967` |
| 17I Confidence Layer Rebuild Plan | ✅ commit `7a2cd46` |
| 17J Final Report Layer Rebuild Plan | ✅ commit `912cc27` |
| 17K Review & Learning Layer Rebuild Plan | ✅ commit `d0057c5` |
| main 最新 commit | `d0057c5` |
| worktree 唯一 deliberate untracked | `.claude/handoffs/task_089_post_pr_cleanup.md` |
| 战略阶段 | 从 Review Layer plan（17K）→ **Evaluation Layer plan（17L 本轮）** |
| 3R-5 / 3R-6 | ❌ 仍然不允许进入 |
| 第一个按层实现 PR（18A）| ❌ 仍未 |
| 2026 holdout | ❌ 永久保留为 final holdout（1.0 §5 rule 8）；本轮不动 |

**17D §6 PR 准入规则提醒**：

- 任何代码 PR 必须绑定九分支某一层 + 引用对应层 Plan §
- 17L 入 main 后，Evaluation Layer 范畴的 PR 才**有资格**被讨论
- 17L 本身**不**自动批准任何 PR；PR-EVAL-* 仍需 18A 单独审批

**层间依赖**：

- 17L 依赖 17K（已就位；outcome_capture 共享归属在 17K §7 已确认）
- 17L **不**依赖 17M（可独立写完）
- 17L 与 17I（Confidence Layer）有协同点：calibration 输出回 Confidence
  System；17I §12.6 / §13 PR-CONF-7 已声明
- 17L 完成后，九分支按层重建只剩 17M（UI Layer）

---

## 3. Evaluation Layer 职责定义

**Evaluation Layer（Branch 8）只回答一件事**：

> **"在历史数据上**批量**评估系统的 signal accuracy / win-rate /
> calibration / regime-segmented metrics——**只读批处理**，**不**回灌
> 当次预测。"**

### 3.1 只做的事（与 1.0 §8 Branch 8 / 16A §11 一致）

- 读取 historical predictions（来自 `prediction_store`）
- 读取 actual outcomes（来自 `outcome_capture` / outcome_log）
- 统计 **projection accuracy**（命中率随 regime / 结构 / 样本量）
- 统计 **exclusion success / false_exclusion rate**
- 统计 **confidence calibration**（level / score 与真实命中率的一致性）
- 统计 **agreement / conflict 在历史上的表现**
- 统计 **signal win-rate**
- 统计 final_report quality proxies（如 narrative 是否出现在三系统输出中
  → 间接验证 non-mutation 契约）
- 执行 **historical replay**（按 frozen data snapshot；anti-lookahead）
- 执行 **holdout evaluation**（明确 train / validation / holdout window；
  2026 holdout 永久保留）
- 生成 win-rate / accuracy / calibration summary
- 生成 audit dashboard 数据（read-only；不参与当次 inference）
- 验证 Review lessons 是否长期有效（与 17K Review 协同；§7）
- 给 Confidence Layer 提供**离线 calibration evidence**（输出权重 / 校准表
  回到 Confidence；不沿其他路径回流）
- 输出 contract validation reports（contract_payload inspector / diff /
  trend / extras_dashboard）

### 3.2 不做的事（与 1.0 §8 Branch 8 / 16A §11 / §13 hard rule 5 一致）

- ❌ 不当次生成 `projection_result` / `exclusion_result` / `confidence_result` /
  `final_report`
- ❌ 不写个案错题本（归 Branch 7 Review）
- ❌ 不直接修改 `memory_store`（归 Branch 7）
- ❌ 不计算真实交易收益（与 1.0 §8 Branch 8 一致：win-rate 是 signal
  win-rate，不是 trading win-rate）
- ❌ 不输出 buy / sell / hold（与 1.0 §13 hard rule 1 一致）
- ❌ 不输出 hard / forced / required
- ❌ 不污染 2026-01-01 之后 final holdout（1.0 §5 rule 8）
- ❌ 不用 evaluation 结果**当场**改规则（"当场" = 在线 inference 路径；
  离线 calibration 仍允许，但其结果以"权重 / 校准表"形式回到 Confidence
  System，不沿其他路径回流）
- ❌ 不做 UI 布局 / Streamlit rendering（归 Branch 9）
- ❌ 不调用 broker / trading API
- ❌ 不直接 promote rule 到 active（active_rule_pool_promotion 永久
  OFFLINE_ONLY；与 1.0 §6.5 / 13 §4-§5 / 17K §17.3 一致）
- ❌ 不调 LLM 生成新预测 / trading suggestion
- ❌ 不写 DB schema / 不改 DB schema（17L 阶段）

### 3.3 输入 / 输出（白名单）

**输入**（与 07C §3.1 / 1.0 §8 Branch 8 / 17K §3.3 一致）：

- 历史 prediction snapshot（来自 `prediction_store`）
- 已结案的真实 outcome（来自 `outcome_capture` / outcome_log）
- 历史 review 记录（来自 `review_store`；用于 lesson 长期验证）
- holdout 区间策略（保留 2026-01-01 之后为 final holdout）
- frozen historical data snapshot（不发起 yfinance fetch；不污染 holdout）

**输出**：

- `evaluation_result` dict（结构详见 §13）
- accuracy / calibration / agreement / win-rate 表
- regime-segmented metrics
- evaluation report（manifest + summary）
- `calibration_context` 权重 / 校准表（回到 Confidence System）
- contract validation reports

**禁止输入**（与 1.0 §8 Branch 8 / §13 hard rule 5 / 1.0 §5 rule 8 一致）：

- ❌ 当次 in-flight `projection_result` / `exclusion_result` /
  `confidence_result` / `final_report`（这些通过 prediction_store
  事后读取，不直接接 in-flight）
- ❌ Future outcome 进**当次** inference 路径（Evaluation 自身就是事后；
  但 Evaluation 输出**不**回灌 in-flight）
- ❌ Trading 输入 / broker / position state
- ❌ 在 in-sample（train / validation）阶段读取 holdout 区间数据

---

## 4. Evaluation Layer 禁止事项

Evaluation Layer **永久禁止**输出 / 引入以下任一：

| 类别 | 禁止项 | 锚点 |
|---|---|---|
| 在当次 inference 中运行 | Evaluation 模块在线调用 main_projection / exclusion_layer / confidence_evaluator / final_decision；Evaluation 是**批处理**层 | 1.0 §8 Branch 8 / §13 hard rule 5 |
| Future outcome 注入当前预测 | 用真实 outcome 修改当次 projection / exclusion / confidence / final_report | 1.0 §9 / 07A §3.2 / 07B §3.2 / 07C §3.3 |
| 用 2026 holdout 训练或调参 | 在 train / validation 窗口读取 2026-01-01 之后数据 | 1.0 §5 rule 8 / 16C §11 |
| 直接修改 system 输出 | Evaluation hook 写回 prediction_store 中的 projection / exclusion / confidence / final_report 字段（即使是事后历史 record） | 1.0 §8 Branch 8 / 06 §6 |
| 直接写 active rule | Evaluation 模块直接调 active_rule_pool 写入 active rule | 1.0 §6.5 |
| 直接 promote rule 到 active | bypass `active_rule_pool_promotion` OFFLINE_ONLY 边界 | 1.0 §6.5 / 13 §4-§5 |
| 调用 broker / trading API | broker / order / position / trade routing | 1.0 §6.1 / §13 hard rule 1 |
| 输出交易动作 | `buy` / `sell` / `hold` / `simulated_trade` / `trading_action` / `no_trade` | 12E X1..X5 / 1.0 §6 |
| 输出强制语义 | `hard_*` / `forced_*` / `required_*` / `_PROTECTION_LAYER_CONNECTED` / `production_promotion` | 12E X1..X5 / 1.0 §6 |
| 默认接 UI | `streamlit` / 任何 ui/ 模块 import；Evaluation 是 logic-layer，不做 layout | 1.0 §13 hard rule 3 |
| 默认写 DB schema | `CREATE TABLE` / `ALTER TABLE` 在 17L 阶段不允许；现有 prediction_store / review_store / experience_memory schema 保持 | 17E §11 ~ 17K §16 / 17L §11 |
| Calibration silent default | calibration_context 缺失时 Confidence Layer **不**捏造 heuristic（与 17I §12.3 / 07C §9.3 一致）；Evaluation 必须显式产出 ready / score / notes | 07C §9.3 / 17I §12 |
| Calibration 沿其他路径回流 | calibration 结果以**权重 / 校准表**形式回到 Confidence；**不**经 review / lesson / rule_lifecycle / UI 等回路 | 1.0 §8 Branch 8 / §13 hard rule 5 |
| Raw artifact 进 repo | replay raw output / DB backup / large `.csv` / `.json` / `.jsonl` / `_run.log` 写入 git tracked path | 1.0 §11 / 14K `.gitignore` / 16H §3 / 17E §11.2 |
| 复活 OFFLINE_ONLY promotion | `services/active_rule_pool_promotion.py` 进 active path | 1.0 §6.5 / 17K §17.3 |
| 复活 quarantine 模块 | `services/continuous_smoothing_candidate*` / `archive/legacy/root_stubs/*` 进 active path | 1.0 §5 rule 14 / §15 / §17 |

---

## 5. 当前 Evaluation Layer 模块 inventory

> **范围说明**：本表覆盖 (1) **Contract validation diagnostic 五件套**：
> outcome_correlation / payload_inspector / payload_diff / payload_trend /
> payload_extras_dashboard (2) **Replay** chain：historical_replay_training /
> three_system_replay_audit / avgo_1000day_training (3) **Validation**：
> regime_validation_helper (4) **Diagnosis**：primary_bias_diagnosis /
> regime_diagnostics_dashboard (5) **Calibration**：active_rule_pool_calibration
> (6) **Anti-false dashboard**：anti_false_exclusion_dashboard (7) **FROZEN
> diagnostic / sidecar**：continuous_smoothing_candidate / v2 /
> soft_metadata_simulator (8) **matcher.py NextDate fields**（Evaluation
> 信号字段）(9) **scripts**：17 个 evaluation-related scripts (10) **logs
> tracked evidence**：3 dirs。standard payload skeleton（17A PR-B）属
> INFRA / SCHEMA。

### 5.1 核心 / 候选 inventory

| module_path | current_role | current_status | target_role | keep / migrate / quarantine / delete | active_callers | risk | next_action |
|---|---|---|---|---|---|---|---|
| `services/contract_outcome_correlation.py` | read-only outcome × contract correlation；joins prediction_log + outcome_log；validate against Step 1A；hit-rate by 3 stable contract fields | KEEP_ACTIVE；docstring "verification tool, not a UI feature；never writes DB；never raises" | **CORE_EVALUATION**：Branch 8 contract validation diagnostic | KEEP | scripts；tests | L | §6.1；§15 PR-EVAL-6 boundary marker |
| `services/contract_payload_inspector.py` | read-only contract inspection；从 prediction_log 读 contract_payload_json → validate → per-section summary | KEEP_ACTIVE；docstring "verification tool, not a UI feature" | **CORE_EVALUATION**：contract validation diagnostic | KEEP | scripts；tests；17J §17.4 已声明 NOT_FINAL_REPORT_LAYER | L | §6.2；§15 PR-EVAL-6 |
| `services/contract_payload_diff.py` | read-only diff of two latest contracts；field-level changed_fields | KEEP_ACTIVE；docstring 同上 read-only | **CORE_EVALUATION**：contract diff diagnostic | KEEP | scripts；tests | L | §6.3；§15 PR-EVAL-6 |
| `services/contract_payload_trend.py` | read-only contract field trend；recent N rows aggregation | KEEP_ACTIVE；docstring 同上 | **CORE_EVALUATION**：contract trend diagnostic | KEEP | scripts；tests | L | §6.4；§15 PR-EVAL-6 |
| `services/contract_payload_extras_dashboard.py` | read-only extras dashboard（exclusion / confidence / simulated_trade extras blocks 聚合） | KEEP_ACTIVE；docstring 显式 "verification / observability tool, not a UI feature" | **CORE_EVALUATION**：extras 聚合 dashboard 数据 | KEEP；UI 渲染部分归 17M | scripts；tests | L | §6.5；§15 PR-EVAL-6 |
| `services/historical_replay_training.py` | historical replay framework；docstring 显式 **"No-future-leak contract"**：projection runner 只见 `Date <= as_of_date`，outcome 在 projection 之后 fetch | KEEP_ACTIVE | **CORE_EVALUATION**：replay 主入口 | KEEP；schema 锁定 | `services/avgo_1000day_training:95`；scripts；tests | M | §6.6；§9；§15 PR-EVAL-3 manifest standard |
| `services/three_system_replay_audit.py` | aggregation helpers for 1005-day three-system replay audit；pure functions；driver = `scripts/run_1005_three_system_replay.py` | KEEP_ACTIVE；docstring "Pure functions only" | **CORE_EVALUATION**：replay audit aggregator | KEEP | `scripts/run_1005_three_system_replay.py`；tests | L | §6.7 |
| `services/avgo_1000day_training.py` | offline batch training caller；调 historical_replay_training | KEEP_ACTIVE | **CORE_EVALUATION**：offline training driver | KEEP | scripts | L | §6.8；与 OFFLINE_ONLY 边界一致 |
| `services/regime_validation_helper.py` | pure 4-fold validation helper；输出 `regime_validation_report.v1`；含 2026 final-test cutoff | KEEP_ACTIVE；docstring 显式 read-only / 2026 cutoff / no DB / no CSV / no network / no streamlit | **CORE_EVALUATION**：regime validation；17F §7.11 已声明 Evaluation | KEEP | scripts；tests | L | §6.9 |
| `services/primary_bias_diagnosis.py` | diagnose primary_20day_analysis directional bias from replay results | KEEP_ACTIVE；17F §7.10 已声明 Evaluation | **CORE_EVALUATION**：replay diagnostic | KEEP | scripts | L | §6.10 |
| `services/regime_diagnostics_dashboard.py` | regime diagnostic dashboard（数据层）；用作 anti_false_exclusion_dashboard / soft_metadata_simulator caller | KEEP_ACTIVE | **CORE_EVALUATION**：diagnostic dashboard 数据层；UI 渲染归 17M | KEEP | anti_false_exclusion_dashboard / soft_metadata_simulator / scripts / tests | M | §6.11；§15 PR-EVAL-5 |
| `services/active_rule_pool_calibration.py` | calibration suggestions for active rule pool；输出 retain / downgrade / recalibrate / remove_candidate / observe decisions | KEEP_ACTIVE；16G UNKNOWN（DEEP_AUDIT_REQUIRED）；17I §17.3 / 17K §17.2 已声明归 Evaluation | **CORE_EVALUATION**：calibration data preparation；与 17I PR-CONF-7 协同 | KEEP；§10；§15 PR-EVAL-4 / PR-EVAL-7 | scripts；tests | M | §6.12；§10 |
| `services/anti_false_exclusion_dashboard.py` | read-only aggregate dashboard；6-gate hard pass/fail + soft metadata baseline；docstring 显式 read-only / SELECT-only / 不写 DB / 不调 trading APIs / 不调 v1 stub trio；`hard_exclusion_allowed` 永远 `False` 在 v1 | KEEP_ACTIVE；17H §15.3 / 17J §17.4 / 17K §17.2 已声明 NOT 各自层 | **CORE_EVALUATION**：anti-false-exclusion 聚合 dashboard 数据；UI 渲染归 17M | KEEP；§11；§15 PR-EVAL-5 | scripts；tests | M | §6.13；§11 |
| `services/soft_metadata_simulator.py` | soft metadata sidecar；read-only；docstring 显式 SELECT-only DB reader；2G-5 实现 | KEEP_ACTIVE | **CORE_EVALUATION**：soft metadata 数据层；anti_false_exclusion_dashboard 委托对象 | KEEP | anti_false_exclusion_dashboard / scripts / tests | M | §6.14 |
| `services/continuous_smoothing_candidate.py` | continuous_smoothing_candidate.v1；pure read-only；docstring "FROZEN_DIAGNOSTIC"；2026 cutoff；不进 active path | KEEP_ACTIVE；与 1.0 §5 rule 14 / §17 一致 永久 FROZEN_DIAGNOSTIC | **FROZEN_DIAGNOSTIC**：研究 / calibration / validation only；不进 active inference | KEEP（不动；不复活）；17L 不接入 active path | scripts；tests | L | §6.15；与 1.0 §5 rule 14 一致 |
| `services/continuous_smoothing_candidate_v2.py` | false-exclusion-risk-aware sidecar；pure read-only；同等 FROZEN | KEEP_ACTIVE；同上 永久 FROZEN | **FROZEN_DIAGNOSTIC** | KEEP（不动；不复活）| scripts；tests | L | §6.15 |
| `matcher.py` 的 NextDate 字段 | RESULT_COLUMNS 含 `NextDate` / `NextOpen` / `NextHigh` / `NextLow` / `NextClose` / `NextOpenChange` / `NextHighMove` / `NextLowMove` / `NextCloseMove` —— 未来 K 线信息 | KEEP_ACTIVE；17F §7.2 / §12.3 / 17J §16.2 已声明 → Evaluation | **EVALUATION_SIGNAL_FIELDS**：在线 inference 路径**禁用**；replay / evaluation 后处理使用 | KEEP；归 Branch 8 ownership；§15 PR-EVAL-6 / 17F PR-FEATURE-5 协同 | matcher caller / scripts / tests | M | §6.16；与 17F §7.2 / §12.3 一致 |
| `tests/test_*` 中 evaluation / replay / calibration / dashboard / inspector 相关 | Evaluation 测试集 | KEEP | KEEP | KEEP | — | L | 不动 |

### 5.2 Scripts inventory（17 个 evaluation-related scripts；本表均不动）

| script | 性质 | 17L 决定 |
|---|---|---|
| `scripts/anti_false_exclusion_dashboard.py` | dashboard caller | KEEP |
| `scripts/audit_five_state_collapse_from_db.py` | five-state collapse audit | KEEP |
| `scripts/build_03_replay_report.py` | 03_fresh_replay 报告构建 | KEEP |
| `scripts/dashboard_contract_extras.py` | extras dashboard caller | KEEP |
| `scripts/inspect_latest_contract_payload.py` | inspector caller | KEEP |
| `scripts/plan_contract_replay.py` | replay 计划 | KEEP |
| `scripts/regime_diagnostics_dashboard.py` | regime dashboard caller | KEEP |
| `scripts/run_1005_three_system_replay.py` | 1005-day replay driver | KEEP |
| `scripts/run_continuous_smoothing_validation.py` / `_v2.py` | FROZEN_DIAGNOSTIC validation | KEEP（不复活）|
| `scripts/run_real_continuous_smoothing_validation.py` / `_execute.py` / `_execute_v2.py` | real continuous smoothing validation | KEEP（FROZEN）|
| `scripts/run_contract_replay.py` | contract replay | KEEP |
| `scripts/shadow_backtest_exclusion_reliability_review_3c5.py` | shadow backtest | KEEP |
| `scripts/summarize_confidence_calibration_inputs.py` | calibration inputs summary | KEEP；§10 |
| `scripts/diff_latest_contract_payloads.py` | contract diff caller | KEEP |
| `scripts/save_projection_records_smoke.py` | smoke test driver | KEEP |
| `scripts/correlate_contract_outcomes.py` | correlation caller | KEEP |
| `scripts/summarize_recent_contract_payloads.py` | trend caller | KEEP |

### 5.3 Tracked logs evidence（3 dirs；本表均不动）

| dir | 性质 | 17L 决定 |
|---|---|---|
| `logs/historical_training/03_fresh_replay/` | 03_fresh_replay tracked summary evidence | KEEP（与 1.0 §11 一致：summary / manifest 进 repo；raw 不进） |
| `logs/historical_training/exclusion_action_validation_2e/` | exclusion validation 2e tracked | KEEP |
| `logs/historical_training/exclusion_action_validation_2e_v2/` | exclusion validation 2e v2 tracked | KEEP |

### 5.4 关键说明

- **Evaluation Layer 是九分支中模块数量最多的层之一**：Contract validation
  五件套 + replay 链（3 个）+ validation + diagnosis（2 个）+ calibration +
  anti-false dashboard + soft_metadata + FROZEN diagnostic（2 个）= **15+ 模块**
- **所有 Contract validation diagnostic 五件套都已 docstring 锁住 "read-only,
  not a UI feature"**：本轮 17L 不改这个边界
- **`historical_replay_training` 已实现 "No-future-leak contract"**
  ：projection runner 只见 `Date <= as_of_date`；outcome 在 projection 之后
  fetch；这是 anti-lookahead 的范本
- **`regime_validation_helper` 已实现 2026 final-test cutoff**：`as_of_date >=
  final_test_cutoff` → `final_test_refusal=True`；这是 holdout isolation 的
  范本
- **`continuous_smoothing_candidate` / `v2` 永久 FROZEN_DIAGNOSTIC**：
  与 1.0 §5 rule 14 / §17 一致；17L 不复活；保留作 research / calibration /
  validation only
- **`active_rule_pool_calibration` 是 calibration data 候选源**：与 17I §17.3 /
  17I §13 PR-CONF-7 / 17K §17.2 协同；§10 / §15 PR-EVAL-4
- **`active_rule_pool_promotion` 永久 OFFLINE_ONLY**：归 17K Review tooling
  （17K §17.3）；不进 Evaluation active path
- **`anti_false_exclusion_dashboard` `hard_exclusion_allowed` 永远 `False`
  在 v1**：与 12 / 13 / 14 / 15 阶段封禁 hard exclusion 一致
- **`matcher.py` NextDate 字段**：在线 inference 路径**禁用**；replay /
  evaluation 后处理使用；归 Branch 8 ownership（17F §7.2 / §12.3 / 17J §16.2
  共同声明）
- **DELETE_NOW 集合为空**（与 16H §13 / 17E §15.7 / 17F §16.7 / 17G §16.11 /
  17H §15.8 / 17I §17.8 / 17J §17.9 / 17K §17.8 一致）

---

## 6. CORE_EVALUATION 保留模块

> Evaluation Layer 的**核心保留模块**：分 5 类（contract validation / replay /
> validation / diagnosis / calibration & dashboard）+ FROZEN sidecar + matcher
> NextDate 共 16 项。

### 6.1 `services/contract_outcome_correlation.py`

| 维度 | 说明 |
|---|---|
| 为什么保留 | read-only outcome × contract correlation；joins prediction_log + outcome_log；validate against Step 1A；hit-rate by 3 stable contract fields；docstring 锁 "verification tool, not a UI feature" |
| 目标职责 | 给 evaluation 提供 contract field 视角的 hit-rate 统计 |
| 后续实现任务 | §15 PR-EVAL-6 boundary marker |
| 当前禁止动作 | 不让其写 DB；不让其调 trading；不接 UI |

### 6.2 `services/contract_payload_inspector.py`

| 维度 | 说明 |
|---|---|
| 为什么保留 | read-only contract inspection；从 prediction_log 读 contract_payload_json → validate → per-section summary；17J §17.4 已声明 |
| 目标职责 | 检查最新 contract payload 是否合规 |
| 后续实现任务 | §15 PR-EVAL-6 |

### 6.3 `services/contract_payload_diff.py`

| 维度 | 说明 |
|---|---|
| 为什么保留 | read-only diff of two latest contracts；field-level changed_fields；DIFF_PATHS 固定 |
| 目标职责 | 比较两个最新 contract payload，检测 schema drift |
| 后续实现任务 | §15 PR-EVAL-6 |

### 6.4 `services/contract_payload_trend.py`

| 维度 | 说明 |
|---|---|
| 为什么保留 | read-only contract field trend；recent N rows aggregation；含 skipped_records 反馈 |
| 目标职责 | 统计 contract payload 各字段在 recent N predictions 上的分布 |
| 后续实现任务 | §15 PR-EVAL-6 |

### 6.5 `services/contract_payload_extras_dashboard.py`

| 维度 | 说明 |
|---|---|
| 为什么保留 | read-only extras dashboard；exclusion / confidence / simulated_trade extras 聚合；docstring "verification / observability tool, not a UI feature" |
| 目标职责 | 给 dashboard / CLI inspection 提供 extras blocks 视图 |
| 后续实现任务 | §15 PR-EVAL-6；UI 渲染归 17M |

### 6.6 `services/historical_replay_training.py`

| 维度 | 说明 |
|---|---|
| 为什么保留 | replay 主入口；docstring 显式 "No-future-leak contract" |
| 目标职责 | (1) `run_historical_replay_for_date(...)` 单日 (2) `run_historical_replay_batch(...)` 批量 (3) `summarize_replay_results(...)` 汇总 |
| 是否需要改名 / 拆分 | ❌ 不改名；不拆分 |
| 是否有跨层问题 | ❌ 无（已 anti-lookahead；不调 in-flight inference） |
| 后续实现任务 | §15 PR-EVAL-3 manifest standard；§15 PR-EVAL-2 holdout boundary tests |
| 当前禁止动作 | 不改 anti-lookahead 契约；不让 outcome 注入 projection 路径；不在 17L 阶段跑 replay |

### 6.7 `services/three_system_replay_audit.py`

| 维度 | 说明 |
|---|---|
| 为什么保留 | aggregation helpers for 1005-day three-system replay audit；pure functions only；driver = `scripts/run_1005_three_system_replay.py` |
| 目标职责 | summarize_three_system_audit + per-system rows + false_exclusion_rows / error_rows / high_confidence_wrong_rows |
| 后续实现任务 | 不动；§15 PR-EVAL-3 |

### 6.8 `services/avgo_1000day_training.py`

| 维度 | 说明 |
|---|---|
| 为什么保留 | offline batch training caller；调 historical_replay_training |
| 目标职责 | offline 长窗口训练 / 评估 driver |
| 后续实现任务 | 不动；§15 PR-EVAL-7 OFFLINE_ONLY boundary |

### 6.9 `services/regime_validation_helper.py`

| 维度 | 说明 |
|---|---|
| 为什么保留 | pure 4-fold validation helper；输出 `regime_validation_report.v1`；含 2026 final-test cutoff（`as_of_date >= cutoff` → `final_test_refusal=True`）；docstring 显式 read-only / no DB / no CSV / no network / no streamlit / no prediction_store / no predict / no scanner |
| 目标职责 | 跨窗口 4-fold validation；gate threshold 固定（Step 3R-4 §6） |
| 是否需要改名 / 拆分 | ❌ 不改名 |
| 后续实现任务 | §15 PR-EVAL-2（holdout boundary tests 范本） |
| 当前禁止动作 | 不改 cutoff；不暴露 threshold parameters |

### 6.10 `services/primary_bias_diagnosis.py`

| 维度 | 说明 |
|---|---|
| 为什么保留 | diagnose primary_20day_analysis directional bias from replay results；纯 aggregation；17F §7.10 已声明 Evaluation |
| 目标职责 | 从 replay 输出推断 primary 方向 bias |
| 后续实现任务 | 不动 |

### 6.11 `services/regime_diagnostics_dashboard.py`

| 维度 | 说明 |
|---|---|
| 为什么保留 | regime diagnostic dashboard 数据层；用作 anti_false_exclusion_dashboard / soft_metadata_simulator caller |
| 目标职责 | 数据层聚合 regime diagnostic；UI 渲染归 17M |
| 后续实现任务 | §15 PR-EVAL-5 data/UI split marker |

### 6.12 `services/active_rule_pool_calibration.py`

| 维度 | 说明 |
|---|---|
| 为什么保留 | calibration suggestions for active rule pool；输出 retain / downgrade / recalibrate / remove_candidate / observe decisions；16G UNKNOWN；17I §17.3 / 17K §17.2 已声明 |
| 目标职责 | calibration data preparation；不直接写 active rule（active_rule_pool_promotion 永久 OFFLINE_ONLY） |
| 是否有跨层问题 | ⚠️ DEEP_AUDIT_REQUIRED（16G UNKNOWN）；本轮仅声明归属 |
| 后续实现任务 | §15 PR-EVAL-4（calibration summary contract）+ PR-EVAL-7（offline-only boundary tests） |
| 当前禁止动作 | 不进 active inference path；不直接 promote rule；calibration 输出回 Confidence System，**不**沿其他路径回流 |

### 6.13 `services/anti_false_exclusion_dashboard.py`

| 维度 | 说明 |
|---|---|
| 为什么保留 | read-only aggregate dashboard；6-gate hard pass/fail + soft metadata baseline；docstring 显式 read-only / SELECT-only；17H §15.3 / 17J §17.4 / 17K §17.2 已声明 |
| 目标职责 | 数据层聚合；UI 渲染归 17M |
| 后续实现任务 | §15 PR-EVAL-5 data/UI split marker；§11 |
| 当前禁止动作 | 不改 `hard_exclusion_allowed = False` 永久；不接 trading；不调 v1 stub trio |

### 6.14 `services/soft_metadata_simulator.py`

| 维度 | 说明 |
|---|---|
| 为什么保留 | soft metadata sidecar；read-only；docstring 显式 SELECT-only DB reader / 不写 DB / 不写 files / 不发起 network；2G-5 实现 |
| 目标职责 | 给 anti_false_exclusion_dashboard 提供 soft_metadata baseline |
| 后续实现任务 | 不动 |

### 6.15 `services/continuous_smoothing_candidate.py` + `_v2.py`

| 维度 | 说明 |
|---|---|
| 为什么保留 | 与 1.0 §5 rule 14 / §17 一致 永久 FROZEN_DIAGNOSTIC；docstring 显式 read-only / no DB / no CSV / no network / no v1 stub trio / no trading APIs |
| 目标职责 | research / calibration / validation only；不进 active inference |
| 17L 决定 | KEEP；**不**复活；保留作历史 reference |
| 当前禁止动作 | 不进 active path；不让其作为 candidate replacement；不让 confidence_evaluator 调用 |

### 6.16 `matcher.py` NextDate 字段

| 维度 | 说明 |
|---|---|
| 为什么算 EVALUATION_SIGNAL_FIELDS | `RESULT_COLUMNS` 中的 `NextDate` / `NextOpen` / `NextHigh` / `NextLow` / `NextClose` / `NextOpenChange` / `NextHighMove` / `NextLowMove` / `NextCloseMove` 都是"未来 K 线信息"；replay / evaluation 后处理使用 |
| 在线 inference 路径 | **禁用**（避免 future leakage）；与 17F §7.2 / §12.3 一致 |
| 17L 决定 | 归 Branch 8 ownership；17F PR-FEATURE-5 marker（仅 docstring）协同 |
| 后续实现任务 | §15 PR-EVAL-6 cross-reference 17F PR-FEATURE-5 |

---

## 7. 与 Review & Learning 的边界

### 7.1 职责差异（与 17K §13 一致）

| 维度 | Branch 7 Review & Learning | Branch 8 Evaluation |
|---|---|---|
| 个案级 vs 批量级 | 个案：单次 prediction vs outcome | 批量：完整数据集 / regime 分段 |
| 输出形式 | review_result + lesson + rule_candidate | metrics report + calibration table + dashboard data |
| 时间窗口 | 单日 / 短期 | 长窗口（含 holdout split） |
| 是否生成 lesson | ✅ 是 | ❌ 否（只验证 lesson 是否长期有效）|
| 是否产出 dashboard | ❌ 否（review_center 产 small-window stats） | ✅ 是 |
| 是否写错题本 | ✅ 是 | ❌ 否 |
| 是否做 calibration 输入 | ⚠️ 间接（lesson 信号）| ✅ 主要（输出权重 / 校准表给 Confidence System）|
| 是否运行 historical replay | ❌ 否（review_orchestrator 只对单条 prediction） | ✅ 是 |

### 7.2 共享模块（与 17K §13.2 一致）

- `services/outcome_capture.py`：Branch 7 owner + Branch 8 reader（17K §7）
- `services/anti_false_exclusion_audit.py`：reliability gate；二者协同（17K §17.1
  / 17H §7.1 共同声明）
- `services/anti_false_exclusion_dashboard.py`：偏 Branch 8（17H §15.3 / 17J §17.4 /
  17K §17.2 共同声明）
- `services/active_rule_pool_calibration.py`：偏 Branch 8（17I §17.3 / 17K §17.2）
- `services/active_rule_pool_validation.py`：Branch 7 / Branch 8 共享（17K §6.13 /
  17K §17.1）
- `services/contract_outcome_correlation.py`：Branch 8（17K §17.2）
- `services/active_rule_pool_promotion.py`：**OFFLINE_ONLY 永久封禁**；不进 active
  path（与 1.0 §6.5 / 13 §4-§5 / 17K §17.3 一致）

### 7.3 Review 可以生成 lesson candidate；Evaluation 验证长期有效性

- Review（Branch 7）输出 `lesson_candidates` / `rule_candidates`（17K §12.1）
- Evaluation（Branch 8）通过 batch metrics / regime-segmented validation
  评估 lesson 是否长期有效（不发生过拟合）
- 失效 lesson → rule_lifecycle 进入 `weakened` / `retired`（17K §6.14）

### 7.4 Review 不做胜率 dashboard

- 与 17K §13.3 一致
- review_center 输出 small-window stats；这是 review 视图，不是 Branch 8 的
  full dashboard

### 7.5 Evaluation 不写个案错题本

- 与 17K §13.4 一致
- Branch 8 只读批处理；不写 review_store / memory_store

### 7.6 Evaluation 输出回到 Confidence System，不沿其他路径

- 与 1.0 §8 Branch 8 / §13 hard rule 5 一致
- calibration 权重 / 校准表 → `calibration_context` → Confidence
- **不**经 review / lesson / rule_lifecycle / UI / scanner / projection 等
  其他路径回流

### 7.7 Evaluation 不能直接改当次 confidence_result

- 与 07C §11 一致
- Confidence 在线 inference 路径只读 `calibration_context`
- Evaluation 输出权重；不直接 mutate 当次 confidence_result

---

## 8. 2026 holdout 规则

### 8.1 用户已要求 2026-01-01 之后数据作为最终 holdout

- 与 1.0 §5 rule 8 一致
- 与 07A §3.2 / 07B §3.2 / 07C §3.2 / 07D §3.2 全部一致
- 与 16C §11 一致

### 8.2 2026 holdout 不能用于训练 / 调参 / rule selection

- in-sample windows = train + validation（< 2026-01-01）
- holdout = ≥ 2026-01-01
- 在 train / validation 阶段读取 holdout = 违反

### 8.3 可以用于最终验证 / calibration report

- 但**只**在最终阶段；用户单独审批
- 不在常规 evaluation cycle 中使用

### 8.4 任何 replay / calibration 必须明确 train / validation / holdout window

- evaluation_result 中必须含 `train_window` / `validation_window` /
  `holdout_window` / `data_cutoff` 字段（详见 §13）
- 所有 evaluation 输出**必须标注是否触碰 holdout**（`holdout_touch_status`）

### 8.5 17L 不运行 holdout，只定义规则

- 与 17D §11 / 1.0 §5 rule 8 一致
- §15 PR-EVAL-2 holdout boundary tests 候选

### 8.6 当前已有的 cutoff 实现

- `services/regime_validation_helper.py` 已实现 `as_of_date >=
  final_test_cutoff` → `final_test_refusal=True`（§6.9）
- `services/regime_features_builder.py`（17F §6.4）已实现同等 cutoff
- `services/regime_labels_builder.py`（17F §6.5）已实现
- `services/cutoff_guard.py` + `services/memory_feedback.py`（17K §6.9）
  实现 record-level cutoff
- 17L 推荐：所有新 evaluation 模块沿用相同体例

### 8.7 Test 强制 holdout isolation

- §15 PR-EVAL-2 boundary tests
- AST-level grep：evaluation 模块在 train / validation 路径中不读
  `Date >= 2026-01-01` 数据

---

## 9. historical replay 规则

### 9.1 historical replay 属 Evaluation Layer

- 与 1.0 §8 Branch 8 / 16C §11 一致
- `services/historical_replay_training.py` 是主入口

### 9.2 replay 只能读取当时可见数据；必须 anti-lookahead

- 与 historical_replay_training docstring 一致：
  - projection runner 只见 `Date <= as_of_date`
  - outcome 在 projection 之后 fetch
  - actual outcome **不**传入 projection step

### 9.3 replay 输出只作为统计和 calibration

- 不直接改系统输出
- 不写回 prediction_store 中的 projection / exclusion / confidence /
  final_report 字段

### 9.4 replay raw logs 不进 repo

- 与 1.0 §11 / 14K `.gitignore` / 16H §3 / 17E §11.2 一致
- repo **只**保留 summary / manifest / docs（markdown）
- raw `.csv` / `.json` / `.jsonl` / `_run.log` 留本地或 archive

### 9.5 replay 脚本不应默认写 large artifacts into tracked path

- 当前 17 个 evaluation scripts 不直接写 git tracked path（output 走
  `logs/historical_training/...`，已 .gitignore）
- §15 PR-EVAL-8 raw artifact guard tests

### 9.6 frozen data snapshot

- replay / evaluation **必须**使用 frozen data snapshot（与 17E §10.5
  一致）
- 不发起 yfinance live fetch
- 不污染 holdout

### 9.7 17L 不跑 replay

- 与 17D §11 / 17L §1 一致

---

## 10. calibration 规则

### 10.1 confidence calibration 属 Evaluation → Confidence 的离线输入

- 与 1.0 §8 Branch 8 / §13 hard rule 5 / 17I §12.6 一致
- Evaluation 输出**权重 / 校准表**
- Confidence Layer 通过 `calibration_context` 接收（17I §12.1 / §12.2）

### 10.2 active_rule_pool_calibration 属 Evaluation

- 不属 Review / Confidence 主链
- 与 17I §17.3 / 17K §17.2 / 17L §6.12 共同声明

### 10.3 calibration_context 可由 Evaluation 生成，但当次 inference 必须只读

- 与 07C §3.1 一致
- Evaluation 离线生成；Confidence 在线读取
- Confidence **不**修改 `calibration_context`

### 10.4 calibration 不得 silent default

- 与 07C §9.3 / 17I §12.3 一致
- Evaluation 输出必须显式标注 `ready` / `projection_score` /
  `exclusion_score` / `notes` / `evidence_refs`
- caller（17I PR-CONF-3）显式传 `{"ready": False}`

### 10.5 calibration 不得直接 promote trading rule

- 与 1.0 §6.5 / 13 §4-§5 一致
- `active_rule_pool_promotion` 永久 OFFLINE_ONLY；不进 active path
- Evaluation 输出 calibration suggestion；**不**自动 promote

### 10.6 active_rule_pool_promotion 仍 OFFLINE_ONLY

- 与 17K §17.3 / 1.0 §6.5 / 13 §4-§5 一致
- 永久封禁自动 promotion
- 17L 不复活

### 10.7 17L 不修 calibration

- 与 17D §11 / 17L §1 一致
- §15 PR-EVAL-4 仅定义 contract；§15 PR-EVAL-7 仅定义 boundary tests

---

## 11. anti_false_exclusion_dashboard 归属判断

### 11.1 性质（与 17H §15.3 / 17J §17.4 / 17K §17.2 一致）

`services/anti_false_exclusion_dashboard.py` 是 read-only aggregate
diagnostics：

- 6-item hard gate pass/fail status
- soft_metadata baseline（含 R4 overextension / bullish_high_pos20_residual）
- `hard_exclusion_allowed` 永远 `False` 在 v1（与 12 / 13 / 14 / 15 阶段
  封禁 hard exclusion 一致）

### 11.2 它不是 Exclusion Layer 主路径

- 与 17H §15.3 / §7.2 一致
- exclusion_layer 不调用此模块
- 它**不**参与当次 exclusion 决策

### 11.3 它不是 Review 个案复盘

- 与 17K §17.2 一致
- 它是**批量**聚合统计；不是单条 review

### 11.4 它可以统计 false exclusion / hit rate / reliability

- 这是 Branch 8 typical 行为
- 与 1.0 §8 Branch 8 一致

### 11.5 UI 展示部分归 17M / 数据统计部分归 17L

- 与 17H §15.3 / 17J §17.4 一致
- 17L 仅声明数据层归属
- 17M 决定 UI rendering

### 11.6 当前阶段不拆

- 与 17D §11 一致
- §15 PR-EVAL-5 仅 docstring marker

---

## 12. contract payload inspector / dashboard 归属判断

### 12.1 性质

5 个 contract payload 工具（contract_outcome_correlation +
contract_payload_inspector + diff + trend + extras_dashboard）：

- 全部 **read-only** verification tool
- docstring 全部锁 "verification tool, not a UI feature"
- 全部不写 DB；全部不调 trading APIs；全部不调 streamlit

### 12.2 它们不是 Final Report 主路径

- 与 17J §17.4 一致
- final_decision 不调用这些工具
- 它们**不**参与当次 final_report 生成

### 12.3 它们可以验证 payload schema / 漂移 / trend / extras

- contract_payload_inspector：单条最新 payload 验证
- contract_payload_diff：两条最新 payload 比较
- contract_payload_trend：N 条 payload 字段分布
- contract_payload_extras_dashboard：extras blocks 聚合
- contract_outcome_correlation：outcome × contract field hit-rate

### 12.4 UI / dashboard 展示部分归 17M / 数据层归 17L

- 17L 仅声明数据层归属为 CORE_EVALUATION
- 17M 决定 UI rendering

### 12.5 当前阶段不拆

- 与 17D §11 一致
- §15 PR-EVAL-6 仅 docstring marker

---

## 13. Evaluation Result 标准化规则

### 13.1 顶层结构（草案 `evaluation_result.v1`）

> **当前未明确实现 schema_version**：现有 `historical_replay_training.summarize_replay_results` /
> `regime_validation_helper.build_regime_validation_report` /
> `three_system_replay_audit.summarize_three_system_audit` 输出 dict 的 keys
> 比较稳定，但**没有**统一 `schema_version = "evaluation_result.v1"` 顶层
> 字段。§15 PR-EVAL-1 决定是否引入。

```
{
    "schema_version": "evaluation_result.v1",                # 草案；PR-EVAL-1 决定
    "evaluation_id": "...",                                  # uuid / hash
    "evaluation_type": "replay" | "validation" | "calibration" | "audit" | "trend" | "diff" | "correlation" | "extras_dashboard",
    "symbol": "AVGO",                                        # uppercase
    "evaluation_timestamp": "YYYY-MM-DDTHH:MM:SS",

    # Window definition (must be explicit)
    "train_window": {
        "start_date": "YYYY-MM-DD",
        "end_date": "YYYY-MM-DD",
        "sample_count": int,
    },
    "validation_window": {
        "start_date": "YYYY-MM-DD",
        "end_date": "YYYY-MM-DD",
        "sample_count": int,
    },
    "holdout_window": {
        "start_date": "2026-01-01",                           # 永久 holdout 起点
        "end_date": "...",
        "sample_count": int,
        "is_touched": bool,                                   # 见 holdout_touch_status
    },
    "data_cutoff": "YYYY-MM-DD",                              # 当次 evaluation 的 cutoff
    "sample_count": int,                                      # train + validation 总样本

    # Metrics（按 evaluation_type 选择性填充）
    "projection_accuracy": {
        "top1_hit_rate": float | None,                        # [0.0, 1.0]
        "top2_coverage_rate": float | None,
        "by_state": {...},                                    # 五状态分组
        "by_regime": {...},                                   # regime 分段
    },
    "exclusion_hit_rate": {
        "exclude_big_up_hit_rate": float | None,
        "exclude_big_down_hit_rate": float | None,
        "false_exclusion_rate": float | None,
        "by_regime": {...},
    },
    "false_exclusion_rate": float | None,                     # 综合
    "confidence_calibration_summary": {
        "level_distribution": {...},                          # low/medium/high/unknown counts
        "calibration_score": float | None,                    # 与真实命中率的一致性
        "agreement_status_distribution": {...},
        "conflict_level_distribution": {...},
        "calibration_table": [...],                           # bucket-level calibration
    },
    "final_report_quality_summary": {
        "non_mutation_violations": int,                       # 应该永远 0
        "missing_section_count": int,
        "compatibility_metadata_drift": int,
    },
    "review_lesson_validation_summary": {
        "lesson_count_total": int,
        "lesson_count_promoted": int,
        "lesson_count_weakened": int,
        "lesson_count_retired": int,
        "lifecycle_health": str,
    },

    # Anti-lookahead confirmations
    "anti_lookahead_confirmations": {
        "projection_runner_saw_only_past_data": True,
        "outcome_fetched_after_projection": True,
        "actual_outcome_not_passed_to_projection": True,
        "future_dates_filtered_via_cutoff_guard": True,
    },

    # Holdout protection
    "holdout_touch_status": "untouched" | "validated_only" | "violated",
    "holdout_validation_notes": [...],                        # 如果 validated_only

    # Calibration output (subset; 仅 evaluation_type=calibration / replay 时填)
    "calibration_output": {
        "ready": bool,
        "projection_score": float | None,
        "exclusion_score": float | None,
        "notes": [...],
        "evidence_refs": [...],
    },

    # Artifact manifest (raw artifacts 不进 repo；只列 manifest)
    "artifact_manifest": {
        "summary_path": "...",                                # markdown summary path（进 repo）
        "raw_csv_paths": [...],                               # 本地路径（不进 repo）
        "raw_json_paths": [...],
        "run_log_path": "...",
        "frozen_data_snapshot_id": "...",
    },

    # Status
    "status": "ok" | "skipped" | "error" | "final_test_refusal",
    "warnings": [...],
    "skipped_records": [...],                                 # 与 contract_payload_trend 一致
}
```

### 13.2 字段最小要求

| 字段 | 类型 | 备注 |
|---|---|---|
| `schema_version` | str | `"evaluation_result.v1"`（PR-EVAL-1 落地后） |
| `evaluation_id` / `evaluation_type` / `symbol` / `evaluation_timestamp` | str | 必备 |
| `train_window` / `validation_window` / `holdout_window` | dict | 必须显式（与 §8 一致）|
| `data_cutoff` | str | 必备；anti-lookahead 关键 |
| `anti_lookahead_confirmations` | dict | 4 项 boolean，全部 `True`（与 historical_replay_training docstring 一致）|
| `holdout_touch_status` | str | 必备；与 §8.4 一致 |
| `status` / `warnings` | str / list[str] | 与 contract_payload_trend 一致 |

### 13.3 缺失语义（与 17F ~ 17K 体例一致）

- 缺失字段一律用 `null` / 空 list / `0`（counts 是 0 valid，不是缺失）
- `status != "ok"` 时仍输出 well-formed dict（fallback）
- `final_test_refusal` 时全部 metrics 字段降级（与 regime_validation_helper
  cutoff 行为一致）
- `anti_lookahead_confirmations` **必须始终输出**

### 13.4 不允许的字段

- ❌ `most_likely_state` / `most_unlikely_state` / `state_probabilities`
  在顶层（应在 metrics 子段中作 distribution）
- ❌ `*_mutated = True`（Evaluation 不写回任一上游；理论上不该出现）
- ❌ `simulated_trade` / `trading_action` / `buy` / `sell` / `hold`
- ❌ `hard_*` / `forced_*` / `required_*` / `_PROTECTION_LAYER_CONNECTED` /
  `production_promotion`

### 13.5 Evaluation Layer 不直接生成 standard_projection_payload.v1

- 与 17F §8.4 / 17G §9.3 / 17H §9.3 / 17I §9.3 / 17J §12.2 / 17K §12.5 一致
- standard_projection_payload.v1 由未来 architecture_orchestrator 组装；
  Evaluation 输出的是**事后** evaluation_result，**不**进 standard payload
  当次 inference flow

### 13.6 Evaluation Layer 不改当次 final_report

- 与 §3.2 / §4 一致
- evaluation_result 是**事后**输出；不写回 prediction_store final_report
  字段

---

## 14. Evaluation Layer 测试策略

后续 Evaluation Layer 实现 PR 必须满足以下测试要求：

### 14.1 anti-lookahead tests

- AST-level grep：evaluation 模块 source 中不出现：
  - 在 projection 路径中读取 `Date > target_date` 的字段
  - actual outcome 注入 projection step
- behavior test：historical_replay_training 在 replay date T → projection
  runner 只见 `Date <= T`；outcome 在 projection 之后 fetch

### 14.2 holdout isolation tests

- 在 train / validation 窗口读取 `Date >= 2026-01-01` 数据 → reject
- regime_validation_helper `as_of_date >= 2026-01-01` → `final_test_refusal=True`
- 与 §8 / §6.9 一致

### 14.3 no mutation of prediction payload tests

- Evaluation 任一函数不修改 prediction_store / outcome_log 中的 row 字段
- 输入 dict id 与输出对应字段 dict id 不同
- AST-level grep：不出现 `INSERT INTO prediction_log` / `UPDATE prediction_log`
  / `DELETE FROM prediction_log`

### 14.4 replay manifest tests

- evaluation_result.artifact_manifest 字段必备
- summary_path 是 markdown
- raw_csv_paths / raw_json_paths / run_log_path 是本地路径（不在 git tracked）

### 14.5 calibration summary shape tests

- `confidence_calibration_summary` 字段 shape 稳定
- `calibration_table` 是 list[dict]
- ready / projection_score / exclusion_score / notes / evidence_refs 完备
- 与 17I §12 / 07C §9 一致

### 14.6 false exclusion metric tests

- `exclude_big_up_hit_rate` / `exclude_big_down_hit_rate` /
  `false_exclusion_rate` 字段 shape 稳定
- 与 anti_false_exclusion_dashboard 6-gate 一致
- `hard_exclusion_allowed = False` 永久（与 v1 一致）

### 14.7 contract inspector tests

- contract_payload_inspector / diff / trend / extras_dashboard 输出 status
  字段稳定
- skipped_records 反馈 invalid payload
- 与现有测试集一致

### 14.8 no trading fields tests

- 输出 dict 字段集合中**不含**：`simulated_trade` / `trading_action` /
  `buy` / `sell` / `hold` / `no_trade` / `hard_*` / `forced_*` / `required_*` /
  `_PROTECTION_LAYER_CONNECTED` / `production_promotion`

### 14.9 no hard / forced / required fields tests

- 与 §14.8 重叠；显式 AST-level grep

### 14.10 no large raw artifact tracked tests

- AST-level grep：evaluation 模块 source 中不出现往 git tracked path 写
  `*.csv` / `*.json` / `*.jsonl` / `_run.log`
- 与 1.0 §11 / 14K `.gitignore` 一致
- §15 PR-EVAL-8 实现

### 14.11 OFFLINE_ONLY boundary tests

- `services/active_rule_pool_promotion.py` 不被 active inference 路径 import
- `services/active_rule_pool_calibration.py` 不被 active inference 路径
  作为 mutation hook
- 与 1.0 §6.5 / 13 §4-§5 / 17K §17.3 一致

### 14.12 baseline & regression

- 每个 PR-EVAL-* 必须以 Step 15 baseline 为起点（**3256 passed, 10
  skipped, 0 failed, 26 warnings, 94 subtests**）
- 新增测试数显式累加到 passed
- warnings / subtests 数变化必须**显式说明**

---

## 15. Evaluation Layer 后续 PR 候选

> **本节是 PR 候选清单，本轮 17L 不执行任一项**。最早 18A 由用户单独
> 决定执行哪个、何时执行、按什么顺序执行。

| 序号 | 名称 | 性质 | 目标 | 文件范围 | 测试 | 风险 | 是否必须先做 |
|---|---|---|---|---|---|---|---|
| **PR-EVAL-1** | evaluation_result contract helper / validator | 代码（新增 helper） | 新增 `services/evaluation_result_contract.py`：定义 `EVALUATION_RESULT_FIELDS` + `validate_evaluation_result(result) -> list[str]` 纯函数 validator；体例与 17A / 17F PR-FEATURE-1 / 17G PR-PROJ-1 / 17H PR-EXCL-1 / 17I PR-CONF-1 / 17J PR-FINAL-1 / 17K PR-REVIEW-1 一致；**不**改 evaluation 实现 | `services/evaluation_result_contract.py`（新增）+ `tests/test_evaluation_result_contract.py`（新增） | focused + full pytest | L | 不强制；推荐第一项 |
| **PR-EVAL-2** | 2026 holdout boundary tests | 代码（仅 tests） | 给所有 evaluation 模块加 `tests/test_evaluation_holdout_boundary.py`：(a) train / validation 路径中读 `Date >= 2026-01-01` → reject (b) regime_validation_helper 已有 cutoff 行为验证 (c) historical_replay_training anti-lookahead 验证 (d) AST-level grep | tests only | focused + full pytest | L | 不强制；推荐 |
| **PR-EVAL-3** | historical replay manifest standard | 代码（**仅** schema 定义 + manifest helper） | 新增 `services/replay_manifest.py`：定义 `ReplayManifest` schema + `build_replay_manifest(...)` 纯函数；包含 train_window / validation_window / holdout_window / data_cutoff / frozen_data_snapshot_id / artifact paths；**不**改 historical_replay_training 实现；**不**改 scripts | `services/replay_manifest.py`（新增）+ tests | focused + full pytest | L | 不强制；与 PR-EVAL-1 协同 |
| **PR-EVAL-4** | confidence calibration summary contract | 代码（**仅** schema 定义） | 新增 `services/calibration_summary_contract.py`：定义 `CalibrationSummary` schema + `validate_calibration_summary(summary) -> list[str]`；ready / projection_score / exclusion_score / notes / evidence_refs / calibration_table；与 17I §12 协同；**不**改 active_rule_pool_calibration 实现 | `services/calibration_summary_contract.py`（新增）+ tests | focused + full pytest | L | 不强制；与 17I PR-CONF-7 协同 |
| **PR-EVAL-5** | anti_false_exclusion_dashboard data/UI split marker | 代码（**仅** docstring） | 给 `services/anti_false_exclusion_dashboard.py` / `services/regime_diagnostics_dashboard.py` 顶部 docstring 加 marker：`CORE_EVALUATION (data layer) — UI rendering belongs to Branch 9 per 17M`；**不**改逻辑 | 仅 docstring | full pytest byte-stable | L | 不强制；与 17M 协同 |
| **PR-EVAL-6** | contract payload inspector / dashboard boundary marker | 代码（**仅** docstring） | 给 5 件套（contract_outcome_correlation / contract_payload_inspector / contract_payload_diff / contract_payload_trend / contract_payload_extras_dashboard）顶部 docstring 加 marker：`CORE_EVALUATION — verification / observability tool；UI rendering belongs to Branch 9 per 17M`；**不**改逻辑 | 仅 docstring | full pytest byte-stable | L | 不强制 |
| **PR-EVAL-7** | active_rule_pool_calibration offline-only boundary tests | 代码（仅 tests） | 给 `services/active_rule_pool_calibration.py` 加 `tests/test_active_rule_pool_calibration_offline_boundary.py`：(a) 不被 main_projection / exclusion_layer / confidence_evaluator / final_decision active inference 路径 import (b) calibration 输出**不**自动 promote rule (c) 不调 broker / trading APIs (d) 不调 v1 stub trio | tests only | focused + full pytest | M | 不强制；与 1.0 §6.5 / 13 §4-§5 / 17K §17.3 一致 |
| **PR-EVAL-8** | raw artifact guard tests | 代码（仅 tests） | 加 `tests/test_evaluation_repo_guard.py`：扫 git index，断言 `logs/historical_training/**/*.csv` / `*.json` / `*.jsonl` / `*_run.log` 全部**未** tracked（除已 14L A2 / 14M / 15 §2 deliberate keep 的 markdown summary 外）；与 1.0 §11 / 14K / 16H 一致 | tests only | focused + full pytest | L | 不强制 |

### 15.1 候选 PR 之间的依赖

- PR-EVAL-1 → PR-EVAL-3 / PR-EVAL-4：先有 contract validator，再做
  manifest / calibration summary contract
- PR-EVAL-2 → PR-EVAL-3：先有 holdout boundary tests，再做 manifest
  standard
- PR-EVAL-5 / PR-EVAL-6：互不依赖；都是 docstring marker；与 17M 协同
- PR-EVAL-7：可独立做
- PR-EVAL-8：可独立做
- 任何**代码** PR-EVAL-* 都依赖 **17L 已入 main**（前置条件）

### 15.2 候选 PR 都不能做的事

- ❌ 不改 evaluation 模块业务逻辑（contract_outcome_correlation /
  contract_payload_* / historical_replay_training / three_system_replay_audit /
  regime_validation_helper / primary_bias_diagnosis / regime_diagnostics_dashboard /
  active_rule_pool_calibration / anti_false_exclusion_dashboard /
  soft_metadata_simulator）
- ❌ 不动 `historical_replay_training.py` anti-lookahead 契约（保持 docstring
  原文）
- ❌ 不动 `regime_validation_helper.py` cutoff 行为
- ❌ 不动 FROZEN_DIAGNOSTIC（continuous_smoothing_candidate / v2）
- ❌ 不复活 `services/active_rule_pool_promotion.py` OFFLINE_ONLY 边界
- ❌ 不让 calibration 直接 promote rule 进 active path
- ❌ 不让 evaluation 进 in-flight active inference path
- ❌ 不让 evaluation 写回 prediction_store / outcome_log 任一字段
- ❌ 不切换默认 `run_predict` 路径
- ❌ 不引入 trading / hard / forced / required
- ❌ 不复活 `continuous_smoothing*` / `archive/legacy/root_stubs/*`
- ❌ 不修改 `.gitignore`
- ❌ 不处理 `avgo_agent.db`（含 backup）
- ❌ 不处理 handoff / logs / DB backup / `.claude/worktrees/`
- ❌ 不在 17L 阶段跑 holdout / replay / calibration
- ❌ 不在 17L 阶段写 large raw artifact 到 tracked path

---

## 16. 与 UI Layer 的交接

### 16.1 数据流方向（与 1.0 §9 / 17F § ~ 17K § 一致）

```
Data Layer
    │
    ▼
Feature Layer  ──►  feature_payload
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
   Branch 3            Branch 4          Branch 5
   Projection          Exclusion         Confidence
        │                 │                 │
        └────────┬────────┴────────┬────────┘
                 ▼                 ▼
           Branch 6 Final Report Layer
                 │
        ┌────────┼────────┐
        ▼        ▼        ▼
   Branch 7   Branch 8   Branch 9
   Review     Evaluation UI
   事后复盘   离线评估   只展示
              （17L 本轮）（17M）
```

### 16.2 UI 只展示 evaluation_result / dashboard data

- 与 1.0 §8 Branch 9 / §13 hard rule 3 / 17M（未来）一致
- UI 通过 evaluation 输出读取
- **不**重算

### 16.3 UI 不运行 replay

- replay 由 Evaluation Layer 主入口（historical_replay_training）触发
- UI 是 read-only viewer

### 16.4 UI 不修改 evaluation_result

- evaluation_result 是 evaluation 输出 snapshot；**只读**

### 16.5 UI 不写 calibration

- calibration 由 Evaluation 离线计算
- UI **不**接 calibration_context 写入路径

### 16.6 Evaluation 不负责 Streamlit layout

- 与 1.0 §13 hard rule 3 一致
- Evaluation 是 logic-layer；layout 归 17M

### 16.7 Evaluation 可提供 dashboard-ready data

- 例如 `anti_false_exclusion_dashboard` / `regime_diagnostics_dashboard` /
  `contract_payload_extras_dashboard` 输出已是 dashboard-ready dict
- 17M UI 可直接 render

### 16.8 UI 展示部分交给 17M

- 17L 仅声明数据层归属；不预设 UI rendering

---

## 17. 清场 / 隔离建议

> **本节按 16H 决策表 8 个标签给出 Evaluation Layer 范畴内的清场建议**。
> 本轮**不**执行任何清场动作。

### 17.1 KEEP（Evaluation Layer CORE）

- `services/contract_outcome_correlation.py`
- `services/contract_payload_inspector.py`
- `services/contract_payload_diff.py`
- `services/contract_payload_trend.py`
- `services/contract_payload_extras_dashboard.py`
- `services/historical_replay_training.py`
- `services/three_system_replay_audit.py`
- `services/avgo_1000day_training.py`
- `services/regime_validation_helper.py`
- `services/primary_bias_diagnosis.py`
- `services/regime_diagnostics_dashboard.py`（数据层）
- `services/active_rule_pool_calibration.py`（DEEP_AUDIT_REQUIRED；保留）
- `services/anti_false_exclusion_dashboard.py`（数据层；UI 渲染归 17M）
- `services/soft_metadata_simulator.py`
- `matcher.py` NextDate 字段（EVALUATION_SIGNAL_FIELDS；归 Branch 8 ownership）

### 17.2 KEEP（FROZEN_DIAGNOSTIC；永久）

- `services/continuous_smoothing_candidate.py`（与 1.0 §5 rule 14 一致）
- `services/continuous_smoothing_candidate_v2.py`

### 17.3 OFFLINE_ONLY（永久封禁；不进 active path）

- `services/active_rule_pool_promotion.py`（与 1.0 §6.5 / 13 §4-§5 / 17K §17.3
  一致；保留作 offline review tooling；归 17K Review tooling）

### 17.4 NOT_EVALUATION（声明非 Evaluation；归其它层）

- 5 个 active_rule_pool helper 的非 calibration 部分（pool / drift /
  export / validation 4 项）→ Branch 7 Review（17K §17.1）
- `services/log_store.py` / `services/prediction_store.py` /
  `services/outcome_capture.py`（owner Branch 7；shared with Branch 8）

### 17.5 KEEP（INFRA / SCHEMA）

- `services/projection_output_contract.py`（与 17J §17.3 一致；与 17A
  standard payload 并存）

### 17.6 MIGRATE_LATER

- §17.4 的非 Evaluation 模块由对应层 Plan 接管
- 17L 阶段无主动 migration

### 17.7 ARCHIVE_IN_REPO

- 无 Evaluation Layer 范畴的 archive 候选（与 16H / 17E §15.5 / 17F §16.5 /
  17G §16.8 / 17H §15.5 / 17I §17.6 / 17J §17.7 / 17K §17.6 一致）

### 17.8 QUARANTINE

- 无 Evaluation Layer 范畴的 quarantine 候选（CORE 状态健康；FROZEN_DIAGNOSTIC
  + OFFLINE_ONLY 已锁定）

### 17.9 DELETE_NOW

- **空**（与 16H §13 / 17E §15.7 / 17F §16.7 / 17G §16.11 / 17H §15.8 /
  17I §17.8 / 17J §17.9 / 17K §17.8 一致）

### 17.10 DELETE_LATER

- 无 Evaluation Layer 范畴（17L 阶段；FROZEN_DIAGNOSTIC 永久保留作
  reference）

### 17.11 MIGRATE_CALLER_FIRST

- `services/avgo_1000day_training.py` → `services/historical_replay_training.py`
  caller 路径迁移在 PR-EVAL-3 manifest standard 之后再决定

### 17.12 MOVE_OUTSIDE_REPO

- raw replay output / DB backup / `.claude/worktrees/` → 已 untracked；
  保留本地状态（与 17E §15.4 / 17F §16.4 一致）
- `logs/historical_training/**/*.csv` / `.json` / `.jsonl` / `_run.log` →
  当前已被 `.gitignore` 6 行 pattern 部分覆盖；§15 PR-EVAL-8 加 guard tests

### 17.13 DEEP_AUDIT_REQUIRED

- `services/active_rule_pool_calibration.py`（16G §11 UNKNOWN；本轮 17L
  仅声明归属为 Branch 8）
- `services/active_rule_pool_validation.py`（16G UNKNOWN；归 Branch 7 /
  Branch 8 共享；17K §17.13）
- 其余 `active_rule_pool_*`（pool / drift / export）已在 17K §17.1 归
  Branch 7 Review；本表不重列

> **重申**：任何文件删除 / 移动 / archive 必须等 16H 规则 + 17D §11 + 用户
> 单独确认。17L 仅给出**建议**，**不**执行。

---

## 18. 不允许事项

**17L 起，Evaluation Layer 范畴内**严格禁止：

- ❌ 不改代码（无 `.py` 文件被修改；本轮 0 修改）
- ❌ 不跑数据
- ❌ 不跑 replay / 不跑 validation / 不跑 historical evaluation
- ❌ 不改 DB / 不改 DB schema（review_store / memory_store / prediction_store /
  outcome_log / experience_memory 等 schema 保持）
- ❌ 不迁 UI（17M 自负其责）
- ❌ 不接 trading / 不输出 buy / sell / hold / hard / forced / required
- ❌ 不进入 3R-5 / 3R-6（1.0 §12 / 16I §15 / 17D §11 / 17E §16 / 17F §17 /
  17G §17 / 17H §16 / 17I §18 / 17J §18 / 17K §18 / 本轮再次重申）
- ❌ 不启动任何代码 PR（PR-EVAL-* 候选要等 18A）
- ❌ 不修改 `.gitignore`
- ❌ 不处理 `avgo_agent.db`（含 backup）
- ❌ 不处理 handoff / logs / DB backup / `.claude/worktrees/`
- ❌ 不复活 `continuous_smoothing*` / `archive/legacy/root_stubs/*` /
  `active_rule_pool_promotion`（OFFLINE_ONLY 永久）
- ❌ 不污染 2026-01-01 之后 final holdout
- ❌ 不借 17L 顺手做 Data / Feature / Projection / Exclusion / Confidence /
  Final Report / Review / UI 范畴改动
- ❌ **不直接跑 2026 holdout**（与 17D §11 / 1.0 §5 rule 8 一致）
- ❌ **不直接跑 historical replay**（与 17D §11 一致）
- ❌ **不直接修 calibration**（与 17D §11 / 1.0 §13 hard rule 5 一致）
- ❌ **不直接生成 raw artifacts** 进 git tracked path
- ❌ 不启动 UI / Bridge / orchestrator 实现任务（与 17D §10 一致）
- ❌ 不让 evaluation 进 in-flight active inference path
- ❌ 不让 evaluation 写回 prediction_store / outcome_log 任一字段
- ❌ 不让 calibration 自动 promote rule 进 active

> 与 17D §11 / 17E §16 / 17F §17 / 17G §17 / 17H §16 / 17I §18 / 17J §18 /
> 17K §18 一致；本轮再次锁定。

---

## 19. 推荐下一步

> **首选**：**Step 17M：UI / Presentation Layer Rebuild Plan**

理由（与 17D §12 / 17E §17 / 17F §18 / 17G §18 / 17H §17 / 17I §19 / 17J §19 /
17K §19 一致 + 17L 实战观察）：

- Evaluation Layer 计划（17L）已就位
- 数据流方向是 Data → Feature → {Projection, Exclusion, Confidence} →
  Final Report → {Review, Evaluation} → **UI**（1.0 §9 / 16C §3）
- 按九分支编号顺序，下一层是 UI / Presentation（Branch 9）
- **17M 的工作量大**：17M 必须接管
  - `app.py`（与 1.0 §13 hard rule 3 一致：app.py 只允许最小改动；UI 主入口）
  - `ui/predict_tab.py`（**主面板**；当前依赖 legacy `final_bias` / `final_confidence` /
    `primary_projection` / `final_projection` 字段 — Bridge #1 退出条件 #1）
  - `ui/home_tab.py` / `ui/history_tab.py` / `ui/inspect_tab.py` /
    `ui/review_tab.py` / `ui/scan_tab.py` / `ui/research_tab.py` /
    `ui/control_tab.py`
  - `ui/projection_v2_renderer.py`（17J §17.4 已声明 → Branch 9）
  - `ui/big_up_contradiction_card.py`（17J §17.4 / 17K §6.6 协同）
  - `ui/exclusion_reliability_review.py`（17K §17.1 cross-reference）
  - `ui/anti_false_exclusion_display.py` / `ui/soft_metadata_renderer.py` /
    `ui/protection_layer_diagnostics_renderer.py` / `ui/command_bar.py` /
    `ui/labels.py` / `ui/soft_metadata_baseline_cache.py`（共 17 个 ui/
    模块）
  - UI 字段映射：legacy `final_bias` / `final_confidence` → standard
    `final_report.projection_section.most_likely_state` / `confidence_section.combined_confidence.level`
  - tab 迁移顺序：低风险 tab（history / inspect）先 → 中风险（home /
    review）→ 主入口（predict_tab，Bridge #1）
  - evaluation dashboard rendering（与 17L §11 / §12 / §16 协同）
  - 17J PR-FINAL-4 warning_cards UI rendering（与 17K PR-REVIEW-2 协同）
- 17M 是九分支按层重建的**最后一层**；17M 入 main 后才能讨论 18A
  第一批按层实现 PR

**不推荐**：

- 不推荐借 17L / 17M 做代码改动（与 17D §11 一致）
- 不推荐重启 16I PR-E / PR-F / PR-G / PR-H（必须等对应层 Plan）
- 不推荐解锁 3R-5 / 3R-6（1.0 §12 7 项前提仍未全部满足）
- 不推荐立刻做 PR-EVAL-* 任一项（与 17L 协同更合算）
- 不推荐立刻实现 architecture_orchestrator MVP（17J §13.6 前置条件未满足）
- 不推荐立刻修 `_apply_briefing_caution`（17K PR-REVIEW-2 必须等 17K 入
  main + 17J PR-FINAL-4 warning_cards schema 协同 + 18A 审批）
- 不推荐立刻跑 2026 holdout / historical replay / calibration（与 17L §1
  / §18 一致）

> **明确**：本轮 17L 推荐的下一步**只有一个候选**——17M UI / Presentation
> Layer Rebuild Plan，也是九分支按层重建的**最后一层 plan**。

---

## 20. 严守边界

本轮 Step 17L **只**写 Evaluation Layer Rebuild Plan：

- ❌ 未改业务代码（无 `.py` 文件被修改；`git diff --stat` 仅 markdown）
- ❌ 未新增测试（`tests/` 字节不变）
- ❌ 未删除文件
- ❌ 未移动文件
- ❌ 未修改 `.gitignore`
- ❌ 未处理 `avgo_agent.db`（16H §5 校正后无需处理）
- ❌ 未处理 handoff（`.claude/handoffs/task_089_post_pr_cleanup.md` 字节
  不变；与 14L A2 / 14M / 15 §2 一致）
- ❌ 未处理 logs / DB backup / `.claude/worktrees/`
- ❌ 未跑 replay / validation / historical evaluation
- ❌ 未写 DB / 未改 DB schema
- ❌ 未默认迁移 `run_predict` 到 V2
- ❌ 未接 trading
- ❌ 未输出 buy / sell / hold / hard / forced / required
- ❌ 未启用任何 candidate / 未复活 `continuous_smoothing` /
  `active_rule_pool_promotion`
- ❌ 未触碰 RISK-1 / RISK-2 / RISK-3 / RISK-7 / RISK-8 / RISK-9 / RISK-10
- ❌ 未进入 3R-5 / 3R-6
- ❌ 未启动任何代码 PR（PR-EVAL-* 候选要等 18A）
- ❌ 未直接跑 2026 holdout / historical replay / calibration
- ❌ 未直接修 calibration
- ❌ 未直接生成 raw artifacts
- ❌ 未启动 UI / Bridge / orchestrator 实现任务
- ❌ 未做任何局部 patch
- ❌ 未 commit / 未 push（按本轮指令）

唯一新增文件：[tasks/record_17l_evaluation_layer_rebuild_plan.md](tasks/record_17l_evaluation_layer_rebuild_plan.md)（本文件）。

后续修改路径：任何对 §3 职责定义 / §4 禁止事项 / §5 inventory / §6
CORE_EVALUATION / §7 与 Review 边界 / §8 2026 holdout / §9 historical
replay / §10 calibration / §11 anti_false_exclusion_dashboard / §12
contract payload tools / §13 evaluation_result 标准化 / §14 测试策略 /
§15 PR 候选 / §16 与 UI 交接 / §17 清场建议 / §18 禁止事项 / §19 下一步
的调整，都必须**显式更新本文件**；同时检查是否需要同步更新 1.0 / 16C /
16D / 16I / 17D / 17E / 17F / 17G / 17H / 17I / 17J / 17K 与 17M（17M 入
main 后）。
