# 17K记录：Review & Learning Layer Rebuild Plan

> 本记录是 **Step 17K：Review & Learning Layer 重建计划**——九分支按层
> 重建中的**第七层**（Branch 7）。1.0 canonical / 16A blueprint / 16B
> inventory / 16C target dataflow & contract decision / 16D isolation &
> quarantine plan / 16E core chain refactor plan / 16F no-patching
> principle / 16G full module decomposition standup / 16H repository
> clearing decision table / 16I core chain rebuild execution plan / 17A
> PR-B standard payload skeleton / 17B PR-C peer_alignment 抽公共模块 /
> 17C PR-D main_projection 去 `exclusion_result` 形参 / 17D layer-by-layer
> rebuild governance / 17E Data Layer Rebuild Plan / 17F Feature Layer
> Rebuild Plan / 17G Projection Layer Rebuild Plan / 17H Exclusion Layer
> Rebuild Plan / 17I Confidence Layer Rebuild Plan / 17J Final Report
> Layer Rebuild Plan 已全部入 main（main 最新 commit `912cc27`）。
>
> 本轮**只**写计划文档：未改业务代码、未新增测试、未删除文件、未移动
> 文件、未修改 `.gitignore`、未处理 handoff、未处理 logs / DB backup /
> `.claude/worktrees/`、**未处理 `avgo_agent.db`**、未跑 replay /
> validation / historical evaluation、未写 DB / 未改 DB schema、未默认
> 迁移 `run_predict` 到 V2、未接 trading、未输出 buy / sell / hold /
> hard / forced / required、未进入 3R-5 / 3R-6、未启动任何代码 PR、
> 未直接修 `_apply_briefing_caution`、未直接改 review / memory / outcome
> 逻辑、未启动 UI / Evaluation / Bridge / orchestrator 实现任务、未做
> 任何局部 patch、未 commit / 未 push。
>
> 唯一 deliverable：本文件。
>
> **本记录优先级**：与 17E ~ 17J / 17L / 17M 各层 Plan 同级；与 1.0 /
> 16A / 16C / 16D / 16F / 16I / 17D / 17E ~ 17J 协同。冲突仲裁路径与
> 1.0 §14 / 17D §13 一致：旧 records 若与 17K 在 Review & Learning Layer
> 范畴冲突，**以 17K 为准**。

---

## 1. Step 17K 目的

把九分支按层重建从 Final Report Layer（17J）推进到**第七层（Review &
Learning Layer）的具体重建计划**。

**本轮只回答**：

- Review & Learning Layer 当前长什么样（模块 inventory + active path）
- Review & Learning Layer 目标长什么样（保留 / 迁移 / 隔离 / 删除候选）
- Review & Learning Layer 与上下游的边界（Final Report ↑（**只读**事后；
  Branch 1–6 的当次 inference 路径**不**触碰）；Evaluation / UI ↓；
  **不**改写任何当次预测结果）
- `review_result` / `lesson` / `memory update` 标准化规则（与 1.0 §8
  Branch 7 / 06 §6-§7 / 07A §3.2 / 07B §3.2 / 07C §3.3 一致）
- `outcome_capture` 规则
- `review_store` / `memory_store` 规则
- `pre_prediction_briefing` / `projection_memory_briefing` 规则
- **`predict.py:_apply_briefing_caution` 问题判断**（0.x 遗留违反 Review
  契约的关键点；1.0 §8 Branch 7 已明确指出）
- `exclusion_reliability_review` / `anti_false_exclusion_audit` 归属
  （与 17H §15.3 / §7.5 一致）
- Review & Learning Layer 后续可能的代码 PR 候选（**不**执行）
- 与 Final Report / Evaluation / UI 的交接

**本轮不回答**：

- 不写 Evaluation / UI 计划（17L / 17M）
- 不开任何代码 PR（最早 18A）
- 不动 `avgo_agent.db`、`.gitignore`、handoff、logs、DB backup、worktrees
- 不直接修 `_apply_briefing_caution`（与 17D §11 一致）
- 不直接改 review / memory / outcome 逻辑
- 不启动 UI / Evaluation / Bridge / orchestrator 实现任务

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
| main 最新 commit | `912cc27` |
| worktree 唯一 deliberate untracked | `.claude/handoffs/task_089_post_pr_cleanup.md` |
| 战略阶段 | 从 Final Report Layer plan（17J）→ **Review & Learning Layer plan（17K 本轮）** |
| 3R-5 / 3R-6 | ❌ 仍然不允许进入 |
| 第一个按层实现 PR（18A）| ❌ 仍未 |
| `_apply_briefing_caution` 0.x 违反 | ⏸️ 已识别（1.0 §8 Branch 7 mention）；本轮不修；归 §10 / §15 PR-REVIEW-2 |

**17D §6 PR 准入规则提醒**：

- 任何代码 PR 必须绑定九分支某一层 + 引用对应层 Plan §
- 17K 入 main 后，Review & Learning Layer 范畴的 PR 才**有资格**被讨论
- 17K 本身**不**自动批准任何 PR；PR-REVIEW-* 仍需 18A 单独审批

**层间依赖**：

- 17K 依赖 17F / 17G / 17H / 17I / 17J（已就位）
- 17K 与 17L（Evaluation Layer）有共用模块（`outcome_capture`）；归属
  详见 §13；17L 入 main 后正式 cross-reference
- 17K **不**依赖 17M（UI Layer）；可独立写完

---

## 3. Review & Learning Layer 职责定义

**Review & Learning Layer（Branch 7）只回答一件事**：

> **"事后比对预测和真实结果，记录哪个系统错了，提炼 lesson，给下一次
> 推演**只读**提醒。"**

### 3.1 只做的事（与 1.0 §8 Branch 7 / 06 §6-§7 / 07A §3.2 / 07B §3.2 /
07C §3.3 一致）

- 读取当日 / 历史 prediction record（来自 prediction_store）
- 读取真实 outcome（来自 outcome_capture / outcome_log）
- 比较 `projection_result` / `exclusion_result` / `confidence_result` /
  `final_report` 与真实结果
- 输出 `review_result`（结构详见 §12）
- 输出 `error_reason` / `missed_signal` / `false_exclusion` /
  `false_confidence` 等复盘字段
- 生成 `lesson_candidates` / `rule_candidates`
- 写 review_store（deterministic_review_log）/ memory_store
  （experience_memory.db）
- 生成下次推演前 `pre_prediction_briefing` / `projection_memory_briefing`
- 给下一次推演提供**只读**提醒（context / warning / note）
- 维护错题本 / 规则生命周期（rule_lifecycle: candidate / watchlist /
  promoted_active / weakened / retired）
- 标记历史错误规律
- 评估 anti_false_exclusion / exclusion_reliability（事后 audit）

### 3.2 不做的事（与 1.0 §8 Branch 7 / 06 §6 / 07A §3.2 / 07B §3.2 /
07C §3.3 一致）

- ❌ **不**当次生成 `projection_result` / `exclusion_result` /
  `confidence_result` / `final_report`
- ❌ **不**直接修改当次答案（即在线 inference 路径不允许 Review hook 写回）
- ❌ **不**在 `run_predict` 里直接降级 `final_confidence` /
  `confidence_level`（**这是 `predict.py:_apply_briefing_caution` 当前的
  违反点**；详见 §10）
- ❌ **不**在 `final_report` 里直接改最终方向 / 概率
- ❌ **不**用未来真实 outcome 影响**历史时点**预测（在线 inference 路径）
- ❌ **不**做 evaluation 批量统计 / 胜率 dashboard（归 Branch 8）
- ❌ **不**做 UI 布局 / Streamlit rendering（归 Branch 9）
- ❌ **不**输出 trading action / hard / forced / required
- ❌ **不**调用 broker / trading API
- ❌ **不**直接运行 live trading
- ❌ **不**把复盘规则变成当次强制裁判（rule 不能变成 hard / forced /
  required decision）
- ❌ **不**把 briefing 变成 mutation hook（briefing 必须 read-only）
- ❌ **不**写 DB schema / 不改 DB schema（17K 阶段；schema 改动归 18A+）
- ❌ **不**调 LLM 生成新预测（review_agent 调 LLM 仅生成"为什么对 / 错"
  的解释，**不**做新判断；与 06 §7 / 07A §3.2 一致）

### 3.3 输入 / 输出（白名单）

**输入**（与 06 §6 / 07A §3.2 / 07B §3.2 / 07C §3.3 一致）：

- 历史 prediction snapshot（来自 `prediction_store`）
- 已结案的真实 outcome（来自 `outcome_capture` / outcome_log）
- 历史 review 记录（来自 `review_store` / `memory_store`）
- 历史 outcome → projection / exclusion / confidence accuracy
- offline calibration 数据（事后；不在当次回灌）

**输出**：

- `review_result` dict（结构详见 §12）
- `lesson` / `rule_memory_entry`（写到 memory_store）
- `pre_prediction_briefing`（给下次推演**展示**告警；read-only）

**禁止输入**（与 1.0 §9 / 07A §3.2 / 07B §3.2 / 07C §3.3 一致）：

- ❌ **当次** `projection_result` / `exclusion_result` /
  `confidence_result` / `final_report`（在线 inference 路径）—— Review
  只能事后读取**已结案**的 prediction record
- ❌ Future outcome（在线 inference 路径）—— `target_date` cutoff 必须由
  cutoff_guard 强制（与现有 `services/cutoff_guard.py` 协同；
  `services/memory_feedback.py` 已实现）
- ❌ 2026-01-01 之后 final holdout 的事后 outcome 进入 in-sample review
- ❌ Trading 输入 / broker / position state

---

## 4. Review & Learning Layer 禁止事项

Review & Learning Layer **永久禁止**输出 / 引入以下任一：

| 类别 | 禁止项 | 锚点 |
|---|---|---|
| Mutation 当次预测 | 当次修改 `projection_result` / `exclusion_result` / `confidence_result` / `final_report` 任一字段 | 06 §6 / §7 / 07A §3.2 / 07B §3.2 / 07C §3.3 / 1.0 §8 Branch 7 |
| 在 run_predict 直接降级 confidence | `_apply_briefing_caution` 当前直接修改 `final_confidence` ([predict.py:1368](predict.py:1368)) | 1.0 §8 Branch 7 mention；本文件 §10 |
| 在 final_report 直接改方向 / 概率 | Review hook 写回 final_decision 输出 | 07D §11 / 17J §4 |
| Future outcome 回灌 | 在线 inference 路径中读取目标日之后的 close / outcome | 1.0 §9 / 07A §3.2 / 07B §3.2 / 07C §3.3 |
| 污染 2026 holdout | 2026-01-01 之后的 outcome 进入 in-sample review / 用作当次 calibration | 1.0 §5 rule 8 |
| 交易 / 强制 | `buy` / `sell` / `hold` / `simulated_trade` / `trading_action` / `hard_*` / `forced_*` / `required_*` / `_PROTECTION_LAYER_CONNECTED` / `production_promotion` | 12E X1..X5 / 1.0 §6 / §13 hard rule 1 |
| 复盘规则变成强制裁判 | rule_candidate 自动 promoted to forced decision 在当次推演中 | 1.0 §10 / promotion 三模块 OFFLINE_ONLY |
| Briefing 变成 mutation hook | briefing 直接改 projection / exclusion / confidence / final_report；当前 `_apply_briefing_caution` 是这种违反 | 06 §7 / 07A §3.2 / 1.0 §8 Branch 7 |
| LLM 新判断 | review_agent 调 LLM 生成新预测 / trading suggestion；当前 review_agent docstring 已明确 "explain WHY... does NOT make new predictions, suggest trades, or access external data" | 06 §7 / review_agent.py:14-17 |
| 下游模块 import 在线 inference 路径反向调用 | 任何 Branch 1–6 模块 import Review Layer | 1.0 §9 数据流方向 |
| UI 调用 | `streamlit` / 任何 ui/ 模块 import；layout / rendering 业务 | 1.0 §13 hard rule 3 |
| DB schema 改动 | `CREATE TABLE` / `ALTER TABLE` 在 17K 阶段不允许；现有 review_store / memory_store schema 保持不变 | 17E §11 ~ 17J §11 / 17K §11 |
| 直接运行 replay | 调用 `scripts/run_contract_replay*` / `scripts/historical_replay_training*` 在 17K 阶段不允许 | 17D §11 |
| 复活 OFFLINE_ONLY promotion | `services/active_rule_pool_promotion.py` / `services/active_rule_pool_calibration.py` / `services/active_rule_pool_drift.py` 进 active path | 1.0 §6.5 / 13 §4-§5 / promotion 三模块 OFFLINE_ONLY |

---

## 5. 当前 Review & Learning 模块 inventory

> **范围说明**：本表覆盖 (1) **Review 主链** (2) **Memory / briefing 主链**
> (3) **Outcome capture** (4) **Reliability / audit**（17H §15.3 / §7.5
> 引用；17J §16.4 协同）(5) **Closed-loop / projection review** (6)
> **Rule lifecycle / scoring** (7) **Caller**（predict.py / UI / scripts）
> (8) **OFFLINE_ONLY promotion 三模块**（与 1.0 §6.5 / 13 §4-§5 一致；不
> 进 active path；不归 Review 主路径）。standard payload skeleton（17A
> PR-B）属 INFRA / SCHEMA。

### 5.1 核心 / 候选 inventory

| module_path | current_role | current_status | target_role | keep / migrate / quarantine / delete | active_callers | risk | next_action |
|---|---|---|---|---|---|---|---|
| `services/review_orchestrator.py` | thin orchestrator：prediction_store → outcome_capture → review_comparator → review_classifier；run_review_for_prediction(symbol, date)；docstring "No LLM, no direct network calls" | KEEP_ACTIVE | **CORE_REVIEW_LEARNING**：Review 主入口（事后 deterministic review） | KEEP | UI predict_tab / tests | M | §6.1；§15 PR-REVIEW-1 contract validator；§15 PR-REVIEW-3 boundary tests |
| `services/review_comparator.py` | deterministic comparison：prediction vs actual outcome；pure rule logic；no LLM | KEEP_ACTIVE；docstring 显式 "No LLM, no network — pure rule logic" | **CORE_REVIEW_LEARNING**：Review 比对主体 | KEEP | review_orchestrator / tests | L | §6.2 |
| `services/review_classifier.py` | deterministic review classifier；error_types / primary_error / reason_guesses；docstring "No LLM, no network" | KEEP_ACTIVE | **CORE_REVIEW_LEARNING**：Review 分类主体 | KEEP | review_orchestrator / tests | L | §6.3 |
| `services/review_analyzer.py` | deterministic rule extractor on top of review history；summarize_review_history + extract_review_rules；docstring "No LLM, no network" | KEEP_ACTIVE | **CORE_REVIEW_LEARNING**：Review aggregator / rule extractor | KEEP | pre_prediction_briefing / tests | L | §6.4 |
| `services/review_center.py` | 复盘中心 MVP：基于 log_store JSONL 计算 sample_count / top1_hit_rate / exclusion_hit_rate / etc.；纯统计 | KEEP_ACTIVE | **CORE_REVIEW_LEARNING / EVALUATION_BORDER**：与 Branch 8 Evaluation 在统计 dashboard 上有重叠；归属偏 Review aggregator | KEEP；与 17L 协同 | tests / UI | M | §6.5；§13 与 Evaluation 边界 |
| `services/review_agent.py` | LLM-powered post-close review generator；调 Anthropic claude-haiku；docstring "explain WHY... does NOT make new predictions, suggest trades, or access external data" | KEEP_ACTIVE；显式 read-only LLM contract | **CORE_REVIEW_LEARNING / OPTIONAL_LLM**：opt-in；与 1.0 §13 hard rule 1 / 5 一致 | KEEP | UI predict_tab / tests | M | §6.6；§15 PR-REVIEW-3 boundary tests（forbidden import + post-check trading reject）|
| `services/review_store.py` | SQLite-backed store for deterministic review results；deterministic_review_log table；same `avgo_agent.db` | KEEP_ACTIVE；docstring "uses the same avgo_agent.db file as prediction_store" | **CORE_REVIEW_LEARNING**：review record 持久化 | KEEP；schema 锁定（§8）| review_orchestrator / projection_rule_preflight / UI / tests | M | §6.7；§15 PR-REVIEW-4 lifecycle schema plan |
| `services/outcome_capture.py` | fetch actual AVGO market result for saved prediction；capture_actual_outcome / classify_actual_structure / capture_outcome；写 outcome_log | KEEP_ACTIVE；与 yfinance / market data 协同（属 Data Layer 接口的 caller） | **CORE_REVIEW_LEARNING / SHARED_WITH_EVALUATION**：Branch 7 + Branch 8 共享（§7 / §13） | KEEP | review_orchestrator / contract_replay_writer / historical_replay_training / UI / tests | M | §7；§15 PR-REVIEW-7 boundary tests（cutoff guard + no-mutation-of-current-prediction） |
| `services/memory_store.py` | minimal persistence for structured experience memory；data/experience_memory.db；list_experiences | KEEP_ACTIVE；与 review_store **不**共用 db（separate sqlite） | **CORE_REVIEW_LEARNING**：lesson / rule candidate 持久化 | KEEP；schema 锁定（§8）| memory_feedback / tests | M | §6.8；§15 PR-REVIEW-4 |
| `services/memory_feedback.py` | lightweight reminders from stored experience memory；含 `cutoff_guard.filter_records_by_cutoff` 显式 anti-future-leak | KEEP_ACTIVE；docstring 显式 06 / 07A / 11D boundary contract | **CORE_REVIEW_LEARNING**：memory → reminder builder | KEEP | projection_memory_briefing / tests | L | §6.9；§15 PR-REVIEW-3 boundary tests |
| `services/projection_memory_briefing.py` | projection-facing advisory briefing from experience memory；含 cutoff_guard | KEEP_ACTIVE；docstring 显式 06 / 07A / 11D boundary | **CORE_REVIEW_LEARNING**：briefing 主入口（projection 视角） | KEEP | projection_preflight / projection_rule_preflight / tests | L | §6.10；§9；与 17G §6.4 一致（17G preflight helper 反向引用）|
| `services/pre_prediction_briefing.py` | pre-prediction rule briefing derived from review history；调 review_analyzer；docstring "No LLM, no network" | KEEP_ACTIVE | **CORE_REVIEW_LEARNING**：briefing 主入口（rule 视角） | KEEP | predict.py（**问题点**！）/ UI predict_tab / tests | M | §6.11；§9；§10 |
| `services/projection_review_closed_loop.py` | snapshot → outcome → review → rule candidates；save_projection_v2_snapshot + build_projection_review + run_projection_review | KEEP_ACTIVE | **CORE_REVIEW_LEARNING**：closed-loop pipeline（V2 chain 视角；与 17G §16.4 / 17H §15.3 一致）| KEEP | historical_replay_training / scripts / tests | L | §6.12；§13 与 Evaluation 边界 |
| `services/exclusion_reliability_review.py` | 综合 big_up_contradiction_card + big_down_tail_warning + 历史 row → reliability item；事后审计 exclusion 可靠性 | KEEP_ACTIVE；17H §15.3 / 17J §17.4 已声明 NOT_EXCLUSION_LAYER | **CORE_REVIEW_LEARNING**：事后 reliability review | KEEP；归 Branch 7 接管 | UI exclusion_reliability_review / scripts / tests | M | §11；§15 PR-REVIEW-5 |
| `services/anti_false_exclusion_audit.py` | Task 071A：offline audit；接受"已决定的硬否定" → blocked_by_audit；docstring "does not predict / does not modify any production prediction or exclusion rule" | KEEP_ACTIVE；17H §7.1 已声明 NOT_EXCLUSION_LAYER | **CORE_REVIEW_LEARNING / SHARED_WITH_EVALUATION**：事后 audit；reliability 评估候选；与 Branch 8 共享 | KEEP；归 Branch 7 / Branch 8 接管 | big_up_contradiction_card / exclusion_reliability_review / tests | M | §11；§15 PR-REVIEW-6 |
| `services/active_rule_pool.py` | active rule pool report；输出 rule pool_counts | KEEP_ACTIVE；16G UNKNOWN（DEEP_AUDIT_REQUIRED） | **REVIEW_LEARNING_RULE_POOL_HELPER**：归 Review；rule_lifecycle / rule_scoring 协同 | KEEP（不动）；§15 PR-REVIEW-8 lifecycle plan | scripts / tests | M | §6.13 |
| `services/active_rule_pool_drift.py` | rule pool drift（rule 漂移检测） | KEEP_ACTIVE；16G UNKNOWN | **REVIEW_LEARNING_RULE_POOL_HELPER**：归 Review | KEEP（不动）| scripts / tests | M | §6.13 |
| `services/active_rule_pool_export.py` | rule pool export | KEEP_ACTIVE；16G UNKNOWN | **REVIEW_LEARNING_RULE_POOL_HELPER**：归 Review | KEEP（不动）| scripts / tests | M | §6.13 |
| `services/active_rule_pool_validation.py` | rule pool validation；offline | KEEP_ACTIVE；16G UNKNOWN | **REVIEW_LEARNING_RULE_POOL_HELPER / EVALUATION_BORDER**：归 Review；与 Branch 8 协同 | KEEP（不动）| scripts / tests | M | §6.13 |
| `services/active_rule_pool_calibration.py` | confidence calibration data preparation；16G UNKNOWN；17I §17.3 / §13 PR-CONF-7 已标 DEEP_AUDIT_REQUIRED；候选 calibration data source | KEEP_ACTIVE | **EVALUATION_DATA_SOURCE**：归 Branch 8 Evaluation（17L 决定）；不归 Review 主路径 | KEEP（不动）；17L 接管 | scripts / tests | M | §13 |
| `services/active_rule_pool_promotion.py` | promotion policy report；docstring 显式 **OFFLINE_ONLY**；不允许 import 进 online projection / exclusion / confidence / final / UI / trading / production promotion paths | KEEP_ACTIVE；OFFLINE_ONLY 永久封禁（13 §4-§5 / 1.0 §6.5）| **OFFLINE_REVIEW_TOOLING**：归 Review offline tools；不进 active path | KEEP（不动；OFFLINE_ONLY）；不复活 | scripts / tests | M | §6.13；与 1.0 §6.5 一致 |
| `services/rule_lifecycle.py` | rule_lifecycle_report：candidate / watchlist / promoted_active / weakened / retired | KEEP_ACTIVE | **CORE_REVIEW_LEARNING**：rule lifecycle 状态机 | KEEP | scripts / tests | L | §6.14；§15 PR-REVIEW-8 |
| `services/rule_scoring.py` | rule_score_report：从 review history 派生 rule score | KEEP_ACTIVE | **CORE_REVIEW_LEARNING**：rule scoring | KEEP | scripts / tests | L | §6.14 |
| `services/contract_outcome_correlation.py` | contract outcome correlation；用于 outcome stats | KEEP_ACTIVE | **NOT_REVIEW_LEARNING**：归 Branch 8 Evaluation（17L 决定）；correlation = batch metric | MIGRATE_LATER（17L） | scripts / tests | L | §13 |
| `services/anti_false_exclusion_dashboard.py` | aggregate dashboard；6-gate status + soft metadata baseline；read-only | KEEP_ACTIVE；17H §15.3 / 17J §17.4 已声明 | **NOT_REVIEW_LEARNING**：归 Branch 8 Evaluation / Branch 9 UI（17L / 17M 决定） | MIGRATE_LATER | scripts / tests | L | §13 |
| `predict.py:_apply_briefing_caution`（function inline） | **直接修改 `result["final_confidence"]`**（[predict.py:1368](predict.py:1368)）当 `caution_level == "high"`；当前在线 inference 路径调用（[predict.py:1513](predict.py:1513)） | **0.x 违反点**；与 1.0 §8 Branch 7 mention 一致 | **NOT_ACCEPTABLE_IN_ACTIVE_PATH**：当前是 mutation hook；必须改为 read-only marker 或迁出 | LEGACY_VIOLATION → §15 PR-REVIEW-2 修复 | predict.py main path（active 在线 inference）/ tests | **H** | §10；§15 PR-REVIEW-2 |
| `services/log_store.py` | 通用日志写入（含 prediction log JSONL）；docstring 显式 prediction_log JSONL | KEEP_ACTIVE | **NOT_REVIEW_LEARNING_CORE**：log_store 是 INFRA；review 通过 log_store 读取，不属 Review 主路径 | KEEP（不动）| 多模块 | L | §6.15；不归 Review 主路径 |
| `services/projection_record_store.py` | projection record 持久化 | KEEP_ACTIVE；17F §5 / 17G §5 已声明 OUT_OF_SCOPE for Feature / Projection | **NOT_REVIEW_LEARNING_CORE**：与 prediction_store 同类；Review 通过 prediction_store 间接读取 | KEEP（不动） | predict / contract_replay_writer | L | 17J §16.6 cross-reference |
| `services/prediction_store.py` | prediction snapshot 写入 | KEEP_ACTIVE；17F §5 / 17G §5 已声明 OUT_OF_SCOPE | **NOT_REVIEW_LEARNING_CORE**：是 review 的 input source；不属 Review 主路径 | KEEP（不动）| 多模块 | L | §13 |
| `tests/test_review_orchestrator.py` / `test_review_agent.py` / `test_review_center.py` / `test_review_classifier.py` / `test_review_comparator.py` / `test_review_analyzer.py` / `test_review_store.py` / `test_outcome_capture.py` / `test_memory_feedback*.py` / `test_pre_prediction_briefing.py` / `test_projection_memory_briefing.py` / `test_projection_review_closed_loop.py` 等 | Review 测试集；含 cutoff_guard boundary tests | KEEP | KEEP | KEEP | — | L | 不动 |

### 5.2 关键说明

- **Review & Learning 主链已经 deterministic**：review_orchestrator /
  review_comparator / review_classifier / review_analyzer / review_center
  等都明确"No LLM, no network — pure rule logic"
- **唯一 LLM caller** 是 `review_agent.py`：但 docstring 严格锁住"explain
  WHY... does NOT make new predictions, suggest trades, or access external
  data"；与 1.0 §13 hard rule 1 一致
- **Memory 主链已经实现 cutoff guard**：`memory_feedback.py` 显式调
  `cutoff_guard.filter_records_by_cutoff`；`projection_memory_briefing`
  forwards `target_date`；这是 Branch 7 anti-future-leak 关键防线
- **`_apply_briefing_caution` 是当前唯一明确的 0.x 违反点**：直接修改
  `final_confidence`；归 §10 / §15 PR-REVIEW-2 修复
- **`exclusion_reliability_review` / `anti_false_exclusion_audit` 在 17H
  §15.3 / §7.5 已被声明非 Exclusion Layer**：本轮 17K 把它收为 Review &
  Learning Layer / Evaluation 共享
- **`outcome_capture` 是 Branch 7 + Branch 8 共享模块**：详见 §7 / §13；
  17K 主要负责其在 Review 路径上的 boundary（cutoff / no-mutation）
- **`active_rule_pool_*` 系列**：5 个模块；其中 `active_rule_pool_promotion`
  是 OFFLINE_ONLY 永久封禁（与 1.0 §6.5 / 13 §4-§5 一致；不复活）；
  `active_rule_pool_calibration` 是 17I PR-CONF-7 候选 calibration data
  source，归 Branch 8 Evaluation；其余 3 个归 Review rule lifecycle helper
- **DELETE_NOW 集合为空**（与 16H §13 / 17E §15.7 / 17F §16.7 / 17G §16.11 /
  17H §15.8 / 17I §17.8 / 17J §17.9 一致）

---

## 6. CORE_REVIEW_LEARNING 保留模块

> Review & Learning Layer 的**核心保留模块**：分主链（orchestrator /
> comparator / classifier / analyzer / center / agent）+ 持久化（review_store /
> memory_store）+ briefing（pre / projection memory）+ closed-loop +
> reliability review / audit + rule lifecycle / scoring 共 14+ 模块。

### 6.1 `services/review_orchestrator.py`

| 维度 | 说明 |
|---|---|
| 为什么保留 | Branch 7 唯一**事后 deterministic review** 主入口；docstring "No LLM, no direct network calls"；调 prediction_store + outcome_capture + review_comparator + review_classifier |
| 目标职责 | (1) 接 `(symbol, prediction_for_date)` (2) 加载 prediction snapshot + actual outcome (3) 调 comparator + classifier (4) 输出 deterministic review_payload (5) **不**调 LLM；**不**写 active inference path |
| 是否需要改名 / 拆分 | ❌ 17K 不改名；不拆分 |
| 是否有跨层问题 | ❌ 无（不调 main_projection / exclusion_layer / confidence_evaluator / final_decision 重新计算）|
| 后续实现任务 | §15 PR-REVIEW-1 contract validator；§15 PR-REVIEW-3 boundary tests |
| 当前禁止动作 | 不在 17K 改逻辑；不接 LLM；不让 Review 写回 prediction_store 任一字段 |

### 6.2 `services/review_comparator.py`

| 维度 | 说明 |
|---|---|
| 为什么保留 | deterministic comparison：prediction vs actual outcome；docstring "No LLM, no network — pure rule logic" |
| 目标职责 | (1) 抽取 prediction structure (2) 抽取 actual structure (3) 输出 dimension-by-dimension match flags |
| 后续实现任务 | 不动 |

### 6.3 `services/review_classifier.py`

| 维度 | 说明 |
|---|---|
| 为什么保留 | deterministic review classifier；error_types / primary_error / reason_guesses；纯 rule logic |
| 目标职责 | 把 comparison 结果分类为 error_types（开盘判断错误 / 路径判断错误 / 收盘判断错误）+ primary_error |
| 后续实现任务 | 不动 |

### 6.4 `services/review_analyzer.py`

| 维度 | 说明 |
|---|---|
| 为什么保留 | deterministic rule extractor on top of review history；纯 aggregation；docstring "No LLM, no network" |
| 目标职责 | (1) summarize_review_history(symbol, limit) (2) extract_review_rules(summary) → list[str] |
| 后续实现任务 | 不动；§15 PR-REVIEW-8 协同 rule lifecycle plan |

### 6.5 `services/review_center.py`

| 维度 | 说明 |
|---|---|
| 为什么保留 | 复盘中心 MVP；输出 sample_count / top1_hit_rate / top2_coverage_rate / exclusion_hit_rate / exclusion_miss_rate；纯统计 |
| 与 Branch 8 Evaluation 边界 | review_center 输出**个案级**统计（最近 N 条）；Branch 8 Evaluation 是**完整数据集 / regime 分段**统计；§13 详谈 |
| 目标职责 | 给 UI / 复盘视图提供小窗口 hit-rate；**不**做 Branch 8 的全量评估 |
| 后续实现任务 | 不动；§13 与 Evaluation 协同 |

### 6.6 `services/review_agent.py`

| 维度 | 说明 |
|---|---|
| 为什么保留 | LLM-powered post-close review generator；docstring 严格锁 "explain WHY... does NOT make new predictions, suggest trades, or access external data"；fallback to rule-based when LLM unavailable |
| 目标职责 | 用 LLM 解释为什么对 / 错；不生成新预测；不调用外部数据 |
| 是否属 CORE_REVIEW_LEARNING | ✅ 是；但**OPTIONAL_LLM**——caller 必须显式选用 |
| 后续实现任务 | §15 PR-REVIEW-3 boundary tests：post-check trading / hard / forced / required reject；forbidden import boundary |
| 当前禁止动作 | 不让 review_agent 写回 prediction / exclusion / confidence / final_report；不让 review_agent 进当次 inference 路径；保持 fallback 到 rule-based |

### 6.7 `services/review_store.py`

| 维度 | 说明 |
|---|---|
| 为什么保留 | SQLite-backed store for deterministic review results；deterministic_review_log table；同 `avgo_agent.db` |
| 目标职责 | (1) save_review_record (2) load_review_records (3) get_latest_review_for_target_date |
| schema 是否锁定 | ✅ 是（17K 阶段不改 schema） |
| 后续实现任务 | §15 PR-REVIEW-4 lifecycle schema plan（**仅 plan**；不改 schema） |
| 当前禁止动作 | 不改 schema；不在 17K 阶段加新表；不删既有列 |

### 6.8 `services/memory_store.py`

| 维度 | 说明 |
|---|---|
| 为什么保留 | minimal persistence for structured experience memory；`data/experience_memory.db`；与 review_store **不同** sqlite 文件 |
| 目标职责 | 持久化 lesson / rule_candidate / experience |
| 后续实现任务 | §15 PR-REVIEW-4；§15 PR-REVIEW-8 |
| 当前禁止动作 | 不改 schema；不让 memory 直接进 active inference path 写回 |

### 6.9 `services/memory_feedback.py`

| 维度 | 说明 |
|---|---|
| 为什么保留 | lightweight reminders from stored experience memory；含 cutoff_guard.filter_records_by_cutoff（anti-future-leak） |
| 目标职责 | 把 memory_store 的 experience records 转为 reminder list；按 target_date cutoff |
| 后续实现任务 | §15 PR-REVIEW-3 cutoff boundary tests |
| 当前禁止动作 | 不接 LLM；不写回 memory_store；不读 future outcome |

### 6.10 `services/projection_memory_briefing.py`

| 维度 | 说明 |
|---|---|
| 为什么保留 | projection-facing advisory briefing from experience memory；调 memory_feedback；含 cutoff_guard 转 audit summary |
| 目标职责 | 给 projection preflight / orchestrator 提供 read-only memory advisory |
| 后续实现任务 | §15 PR-REVIEW-3 |
| 当前禁止动作 | 不修改 projection_result；不修改 confidence_result；不修改 final_report；只输出 advisory dict |

### 6.11 `services/pre_prediction_briefing.py`

| 维度 | 说明 |
|---|---|
| 为什么保留 | pre-prediction rule briefing derived from review history；调 review_analyzer；docstring "No LLM, no network" |
| 目标职责 | 输出 caution_level / weakest_dimension / top_rules（read-only）|
| 后续实现任务 | §15 PR-REVIEW-3 |
| 当前禁止动作 | 不修改任一上游 |

> ⚠️ **关键问题**：caller `predict.py:_apply_briefing_caution` 直接读取
> 此 briefing 后**修改** `final_confidence`——这是 Branch 7 主动违反；
> 详见 §10 / §15 PR-REVIEW-2

### 6.12 `services/projection_review_closed_loop.py`

| 维度 | 说明 |
|---|---|
| 为什么保留 | snapshot → outcome → review → rule candidates；V2 chain 视角 |
| 目标职责 | (1) save_projection_v2_snapshot (2) build_projection_review (pure) (3) run_projection_review (orchestrate) |
| 后续实现任务 | §15 PR-REVIEW-1 contract validator；§13 与 Evaluation 边界 |

### 6.13 `services/active_rule_pool.py` / `_drift.py` / `_export.py` / `_validation.py`

| 维度 | 说明 |
|---|---|
| 为什么保留 | rule pool 状态 / drift / export / validation；纯 aggregation |
| 16G UNKNOWN | 16G §11 列出的 10 项 UNKNOWN 之一 |
| 17K 决定 | 归 Branch 7 Review & Learning（rule pool helper 集合）；除 `_calibration` 归 Branch 8 / `_promotion` 永久 OFFLINE_ONLY 之外 |
| 后续实现任务 | §15 PR-REVIEW-8 lifecycle plan；4 个 helper 协同 |
| 当前禁止动作 | 不进 active path；不复活 OFFLINE_ONLY |

### 6.14 `services/rule_lifecycle.py` + `services/rule_scoring.py`

| 维度 | 说明 |
|---|---|
| 为什么保留 | rule_lifecycle_report 含 5 状态（candidate / watchlist / promoted_active / weakened / retired）；rule_scoring 从 review history 派生 score |
| 目标职责 | rule lifecycle 状态机 + scoring |
| 后续实现任务 | §15 PR-REVIEW-8 |

### 6.15 `services/log_store.py` / `services/prediction_store.py` /
`services/projection_record_store.py`

| 维度 | 说明 |
|---|---|
| 为什么属 NOT_REVIEW_LEARNING_CORE | 三者都是 INFRA / 持久化层；Review 是它们的 reader，不是 owner |
| 17K 决定 | 不归 Review 主路径；保留 |

---

## 7. outcome_capture 规则

### 7.1 outcome_capture 是 Branch 7 + Branch 8 共享模块

- 既给 Review（个案复盘）用，又给 Evaluation（批量统计）用
- 17K 阶段归属：**SHARED_WITH_EVALUATION**（Branch 7 owner + Branch 8 reader）
- 17L Evaluation Plan 入 main 后正式 cross-reference

### 7.2 outcome 只能在预测之后进入 Review / Evaluation

- 与 1.0 §9 / 06 §6 一致
- 当 prediction snapshot 已写入 prediction_store + target_date 已过 →
  outcome_capture 才允许 fetch
- target_date 之前的 outcome 在线 inference 路径**禁止**进入

### 7.3 outcome 不允许进入当次 Projection / Exclusion / Confidence / Final Report

- 与 07A §3.2 / 07B §3.2 / 07C §3.3 / 07D §11 一致
- outcome **只**能进 Review / Evaluation
- main_projection_layer / exclusion_layer / confidence_evaluator /
  final_decision 不接 outcome 输入

### 7.4 outcome 可以用于复盘、胜率统计、calibration 更新

- Review：deterministic_review_log（review_store）
- Evaluation：win-rate / accuracy metrics（17L）
- Calibration：`calibration_context` 通过权重 / 校准表回到 Confidence
  System（17I §12.6 / 1.0 §8 Branch 8 一致）；**不**沿其他路径回流

### 7.5 outcome 不能污染 2026 holdout 或反向影响历史 replay

- 与 1.0 §5 rule 8 一致
- 2026-01-01 之后 outcome **不**进 in-sample review / calibration
- replay 路径必须使用 frozen data snapshot（17E §10.5）

### 7.6 当前 outcome_capture 已含 cutoff_guard 协议

- `services/cutoff_guard.py` 提供 `filter_records_by_cutoff`
- `services/memory_feedback.py` 显式调用
- outcome_capture 自身需保证："只读 target_date 之后的 close"是**事后**
  动作，不在线 inference 路径

### 7.7 17K 推荐处置

- KEEP；归 Branch 7 + Branch 8 共享
- §15 PR-REVIEW-7 boundary tests：no-mutation-of-current-prediction +
  cutoff guard + forbidden import（不 import main_projection / exclusion_layer /
  confidence_evaluator / final_decision）

---

## 8. review_store / memory_store 规则

### 8.1 review_store 保存复盘记录

- `services/review_store.py` 用同 `avgo_agent.db`；表 `deterministic_review_log`
- 一行 = 一次 deterministic review 结果
- API：save_review_record / load_review_records / get_latest_review_for_target_date

### 8.2 memory_store 保存可复用经验 / lesson / rule candidate

- `services/memory_store.py` 用 `data/experience_memory.db`（与 avgo_agent.db
  分离）
- 保存 structured experience memory records
- API：list_experiences

### 8.3 memory 不能直接写回当次结果

- 与 1.0 §8 Branch 7 / 06 §6 / 07A §3.2 一致
- memory **只**能在下一次推演前通过 briefing **只读**呈现
- 当次推演路径不允许 memory hook 修改 projection / exclusion / confidence /
  final_report
- **当前 `_apply_briefing_caution` 违反此规则**（详见 §10）

### 8.4 memory 应有 lifecycle

- 与 `services/rule_lifecycle.py` 协同：
  - `candidate`：新生成
  - `watchlist`：观察中
  - `promoted_active`：已激活
  - `weakened`：表现弱
  - `retired`：退役
- rejected：与 1.0 §10 / promotion 三模块 OFFLINE_ONLY 一致
- §15 PR-REVIEW-8 plan

### 8.5 rule 不能变成 hard / forced / required decision

- 与 1.0 §6.4 / §6.10 / 12E X1..X5 一致
- rule_candidate / promoted_active rule 在当次推演中**只能**作为 advisory
- 任何"自动 promotion 到 forced decision"路径**永久禁止**

### 8.6 17K 不改 schema

- review_store / memory_store 当前 schema 保持
- §15 PR-REVIEW-4 仅 plan；不改 schema

---

## 9. pre_prediction_briefing / projection_memory_briefing 规则

### 9.1 briefing 可以在下一次推演前提供提醒

- `services/pre_prediction_briefing.py`：基于 review history 派生
  caution_level / weakest_dimension / top_rules
- `services/projection_memory_briefing.py`：基于 experience memory 派生
  matched / advisory dict
- 二者都是 read-only

### 9.2 briefing 只能作为 context / warning / note

- briefing 输出**字段**应该出现在 final_report 的 `risks` / `warning_cards`
  或 projection_result 的 `key_risk_signals` 等 advisory section
- briefing 输出的字段名**不**应该出现在 `final_confidence` /
  `most_likely_state` 等 mutation key

### 9.3 briefing 不能直接修改 projection_result

- 与 07A §3.2 一致
- 当前 projection_orchestrator_preflight / projection_rule_preflight /
  projection_memory_briefing 是 read-only advisory；正确

### 9.4 briefing 不能直接修改 confidence_result

- 与 07C §5 / §11 一致
- 当前 caller 路径不存在 briefing → confidence_evaluator 写回；正确

### 9.5 briefing 不能直接修改 final_report

- 与 07D §11 一致
- final_decision 已实现 `non_mutation_confirmations` 6 项 boolean，全 False
- 但 **predict.py 的 legacy `PredictResult` 不是 final_decision 输出**——
  `predict.py:_apply_briefing_caution` 修改的是 `result["final_confidence"]`
  （legacy `PredictResult` schema），这绕过了 final_decision 的 non-mutation
  contract

### 9.6 `_apply_briefing_caution` 当前违反 Review 不当次改答案契约

- 详见 §10
- 17K **本轮不修**；归 §15 PR-REVIEW-2

---

## 10. _apply_briefing_caution 问题判断

### 10.1 当前实现摘要

`predict.py:1357-1392`：

```python
def _apply_briefing_caution(result: dict, briefing: dict) -> dict:
    """Lower final_confidence by one step when caution_level is high."""
    result = dict(result)
    caution_level = briefing.get("caution_level", "none")
    has_data = briefing.get("has_data", False)

    if caution_level == "high" and has_data:
        current = result["final_confidence"]
        if current in _CONFIDENCE_ORDER:
            idx = _CONFIDENCE_ORDER.index(current)
            if idx > 0:
                result["final_confidence"] = _CONFIDENCE_ORDER[idx - 1]
                result["briefing_caution_applied"] = True
                ...
```

调用点：`predict.py:1513` `result = _apply_briefing_caution(result, pre_briefing)`
（在 `run_predict` 主路径内）

### 10.2 为什么属 0.x 遗留

- 与 1.0 §8 Branch 7 mention 一致：
  > 当前 `predict.py` 内 `_apply_briefing_caution` 仍然修改 `final_confidence`。
  > 这是 0.x 遗留；16E 必须把 caution 移到展示层（在 Final Report Layer
  > 标注，而不是 mutate confidence）。
- Review / Briefing 应只读（07A §3.2 / 07C §3.3 / 07D §11）
- 但当前在线 inference 路径调用此函数 → 修改 `final_confidence` →
  违反 Branch 7 不当次改答案契约

### 10.3 为什么是关键违反

- ✅ violates: Review 只能事后学习（06 §6）
- ✅ violates: Briefing 只能只读提醒（07A §3.2 / 07D §11）
- ✅ violates: Confidence 只能由 Confidence Layer 输出（07C §5 / §11）
- ✅ violates: Final Report 只能汇总，不应被 Review hook 改写（07D §6 / §11）
- ✅ violates: 1.0 §6.13（"复盘层成为第四个预测系统"）：当前函数确实
  把 briefing 当作了第四个判断系统

### 10.4 归属建议（17K 决定）

| 维度 | 判断 |
|---|---|
| 是否应迁出 active path | ✅ **是**——必须迁出 |
| 是否应改成 warning-only note | ✅ **是**——目标行为：把 caution_level 输出到 final_report 的 `warning_cards` / `risks` section（17J §9.4 schema）；**不**改 `final_confidence` |
| 是否应归 Review Layer cleanup | ✅ **是**——归 Branch 7 cleanup；§15 PR-REVIEW-2 |
| 当前阶段是否立即拆 | ❌ **不立即拆**（与 17D §11 一致） |
| 不拆时如何处理 | 17K 仅声明违反；§15 PR-REVIEW-2 候选；18A+ 阶段实施 |

### 10.5 17K 立即动作

- **无**（与 17D §11 一致：本轮不改代码）
- §15 PR-REVIEW-2 候选定义如下：
  - 把 `_apply_briefing_caution` 行为改为"仅追加 `briefing_caution_reason` /
    `briefing_caution_applied` 标记"，**不**修改 `final_confidence`
  - caller path 改为：将 caution 信息透传到 `final_report.warning_cards`
    （需要 17J PR-FINAL-4 warning_cards schema 协同）或 `final_report.risks`
  - 加 boundary test：no-mutation of `final_confidence` from briefing path
  - 兼容现有调用方（保持 `briefing_caution_reason` 字段以避免 schema 破坏）

### 10.6 PR-REVIEW-2 前置条件

- 17K 入 main（前置；本文件）
- 推荐：17J PR-FINAL-4（warning_cards schema）已落地，否则 caution 只能
  以散字段方式输出
- 18A 用户单独审批

### 10.7 17K 阶段不修；不允许任何 patch

- 与 17D §11 / 17K §16 一致
- 即使已识别违反点，本轮**不修**（17D 治理）

---

## 11. exclusion_reliability_review / anti_false_exclusion_audit 归属判断

### 11.1 与 17H §15.3 / §7.5 一致

- `exclusion_reliability_review` 在 17H §15.3 / 17J §17.4 已声明
  NOT_EXCLUSION_LAYER；17H §7.5 推荐归 Branch 7 Review
- `anti_false_exclusion_audit` 在 17H §7.1 / 17J §17.4 已声明
  NOT_EXCLUSION_LAYER；17H §7.1 推荐归 Branch 7 Review / Branch 8 Evaluation

### 11.2 17K 本节固化判断

| 模块 | 17K 决定 |
|---|---|
| `services/exclusion_reliability_review.py` | **CORE_REVIEW_LEARNING**（事后 reliability review；调 contradiction_card + tail_warning + 历史 row）|
| `services/anti_false_exclusion_audit.py` | **CORE_REVIEW_LEARNING / SHARED_WITH_EVALUATION**（offline audit；reliability gate metric 候选）|

### 11.3 它们可以总结 false exclusion

- `exclusion_reliability_review.build_exclusion_reliability_review` 生成
  per-row reliability item（事后）
- `anti_false_exclusion_audit.audit_big_up_exclusion` 输出
  `{hard_excluded, soft_excluded, blocked_by_audit}`（offline）

### 11.4 它们不能在当次推演里决定排除

- 与 07B §3.2 / §6 / §10 一致
- 即使 anti_false_exclusion_audit 决定 `blocked_by_audit`，**也不能**让
  exclusion_layer 在当次输出 action=allow（这是 audit 自己的决定，与
  当次 exclusion_layer 的 triggered_rule 是两个独立 channel）
- 当前 exclusion_layer 也未读 audit 输出；正确

### 11.5 后续应与 Evaluation Layer 协同

- §13 详谈
- 17L Evaluation Plan 决定 `anti_false_exclusion_dashboard` 归属（17H §15.3
  推荐 Branch 8）

### 11.6 17K 推荐处置

- KEEP；归 Branch 7 / Branch 8 共享
- §15 PR-REVIEW-5 / PR-REVIEW-6（仅 docstring marker）

---

## 12. Review Result 标准化规则

### 12.1 顶层结构（草案 `review_result.v1`）

> **当前未明确实现 schema_version**：现有 review_orchestrator /
> review_classifier / review_comparator / review_store 输出 dict 的 keys
> 比较稳定，但**没有** `schema_version = "review_result.v1"` 顶层字段。
> §15 PR-REVIEW-1 可决定是否引入。

```
{
    "schema_version": "review_result.v1",                  # 草案；PR-REVIEW-1 决定
    "status": "ok" | "missing_prediction" | "missing_outcome" | "error",
    "symbol": "AVGO",                                      # uppercase
    "prediction_id": "...",                                # 来自 prediction_store
    "prediction_for_date": "YYYY-MM-DD",                   # target_date
    "analysis_date": "YYYY-MM-DD",                         # 当时 prediction 的 analysis_date
    "review_timestamp": "YYYY-MM-DDTHH:MM:SS",             # 当次 review 触发时间

    # Source projections (snapshot；事后只读)
    "projected_state": "...",                              # 当时 prediction 的 most_likely_state / direction
    "excluded_states": [...],                              # 当时 exclusion 的 triggered_rules / excluded_states
    "confidence_level": "low" | "medium" | "high" | "unknown",  # 当时 confidence_result.combined_confidence.level
    "final_summary_snapshot": "...",                       # 当时 final_report.combined_user_summary

    # Actual outcome
    "actual_outcome": {                                    # 来自 outcome_capture
        "actual_state": "大涨" | "小涨" | "震荡" | "小跌" | "大跌",
        "actual_open": "...",
        "actual_path": "...",
        "actual_close": "...",
        "outcome_timestamp": "...",
    },

    # Comparison
    "correctness": {                                       # 来自 review_comparator
        "open_match": True/False/None,
        "path_match": True/False/None,
        "close_match": True/False/None,
        "state_match": True/False/None,
        "overall_score": 0.0-1.0,
    },

    # Classification
    "error_type": [...],                                   # 来自 review_classifier；error_types list
    "primary_error": "open" | "path" | "close" | None,
    "missed_signals": [...],                               # 当时未捕获的关键信号
    "false_exclusion_notes": [...],                        # exclusion 误杀
    "false_confidence_notes": [...],                       # confidence 误估
    "confidence_calibration_notes": [...],                 # confidence 是否过高 / 过低

    # Lessons & rules
    "lesson_candidates": [...],                            # 候选 lesson（写到 memory_store）
    "rule_candidates": [...],                              # 候选 rule（rule_lifecycle: candidate）
    "memory_updates": [...],                               # 本次 review 触发的 memory_store 更新

    # Review metadata
    "review_summary": "...",                               # 中文 summary（来自 review_classifier.build_review_summary）
    "reviewer": "deterministic" | "llm" | "fallback",      # 当 review_agent 接 LLM 时为 "llm"

    # Non-mutation confirmations
    "non_mutation_confirmations": {
        "current_prediction_mutated": False,               # Review 不修改当次 prediction
        "current_exclusion_mutated": False,
        "current_confidence_mutated": False,
        "current_final_report_mutated": False,
        "future_outcome_used_in_inference": False,
    },
}
```

### 12.2 字段最小要求

| 字段 | 类型 | 备注 |
|---|---|---|
| `schema_version` | str | `"review_result.v1"`（PR-REVIEW-1 落地后） |
| `status` | str | `"ok"` / `"missing_prediction"` / `"missing_outcome"` / `"error"` |
| `prediction_id` | str | 来自 prediction_store |
| `prediction_for_date` / `analysis_date` | str (`YYYY-MM-DD`) | 与 prediction 对齐 |
| `actual_outcome` | dict | 必备；`actual_state` ∈ 五状态 |
| `correctness` | dict | 必备 |
| `error_type` | list[str] | 中文 error labels |
| `non_mutation_confirmations` | dict | 至少 5 项 boolean，全 `False` |

### 12.3 缺失语义（与 17F ~ 17J 体例一致）

- 缺失字段一律用 `null` / `None` / 空 list `[]`
- `status != "ok"` 时仍输出 well-formed dict（fallback）
- `non_mutation_confirmations` **必须始终输出**

### 12.4 不允许的字段

- ❌ `most_likely_state` / `most_unlikely_state` / `state_probabilities`
  在顶层（应在 `projected_state` 等 snapshot 字段中）
- ❌ `current_*_mutated = True`（必须始终 `False`）
- ❌ `simulated_trade` / `trading_action` / `buy` / `sell` / `hold`
- ❌ `hard_*` / `forced_*` / `required_*` / `_PROTECTION_LAYER_CONNECTED`

### 12.5 Review & Learning Layer 不直接生成 standard_projection_payload.v1

- 与 17F §8.4 / 17G §9.3 / 17H §9.3 / 17I §9.3 / 17J §12.2 一致
- standard_projection_payload.v1 由未来 architecture_orchestrator 组装；
  Review 输出的是**事后** review_result，**不**进 standard payload 的当次
  inference flow

---

## 13. 与 Evaluation Layer 的边界

### 13.1 职责差异

| 维度 | Branch 7 Review & Learning | Branch 8 Evaluation |
|---|---|---|
| 个案级 vs 批量级 | 个案：单次 prediction vs outcome 复盘 | 批量：完整数据集 / regime 分段统计 |
| 输出形式 | review_result（per case）+ lesson / rule candidate | metrics report（accuracy / win-rate / calibration）|
| 时间窗口 | 单日 / 短期 | 历史长窗口（含 holdout split） |
| 谁触发 | UI predict_tab 触发个案；scripts 批量触发 closed_loop | scripts 批量；offline cron |
| 是否生成 lesson | ✅ 是 | ❌ 否（只验证 lesson 是否长期有效）|
| 是否产出 dashboard | ❌ 否（review_center 产 small-window stats，不是 full dashboard） | ✅ 是 |
| 是否写错题本 | ✅ 是（memory_store / review_store） | ❌ 否 |
| 是否做 calibration 输入 | ⚠️ 可能间接 | ✅ 主要（输出权重 / 校准表给 Confidence System）|

### 13.2 共享模块

- `services/outcome_capture.py`：Branch 7 + Branch 8 都用（§7）
- `services/anti_false_exclusion_audit.py`：reliability gate；二者协同
- `services/anti_false_exclusion_dashboard.py`：偏 Branch 8 dashboard（17H §15.3）
- `services/active_rule_pool_calibration.py`：偏 Branch 8 calibration data
  source（17I §17.3 / §13 PR-CONF-7）
- `services/active_rule_pool_validation.py`：偏 Branch 7 / Branch 8 共享
- `services/contract_outcome_correlation.py`：偏 Branch 8 batch metric
- `services/active_rule_pool_promotion.py`：**OFFLINE_ONLY 永久封禁**
  （1.0 §6.5 / 13 §4-§5）；不进 active path

### 13.3 Review 不做胜率 dashboard

- review_center 输出**小窗口** sample_count / hit_rate；这是 review 视图，
  不是 Branch 8 的 full dashboard
- Branch 8 的 win-rate / accuracy / calibration table 在 17L 决定

### 13.4 Evaluation 不写个案错题本

- Branch 8 只读批处理；不写 review_store / memory_store
- Branch 8 输出 metrics 报告

### 13.5 17K 推荐处置

- 17K 锁定 Branch 7 主权；声明共享模块
- 17L Evaluation Plan 入 main 后正式 cross-reference
- §15 PR-REVIEW-7 / PR-REVIEW-8 与 17L 协同

---

## 14. Review & Learning Layer 测试策略

后续 Review & Learning 实现 PR 必须满足以下测试要求：

### 14.1 no mutation of current prediction payload

- Review 任一函数不修改当次 `prediction_result` / `exclusion_result` /
  `confidence_result` / `final_report` 入参
- 输入 dict id 与输出对应字段 dict id 不同
- AST-level grep：Review 模块 source 中不出现对当次 inference 输出的写回

### 14.2 outcome only after target date

- `outcome_capture.capture_actual_outcome` 不允许在 `target_date` 当日 /
  之前调用（必须等 close）
- cutoff_guard 强制（与 `services/cutoff_guard.py` 协同）
- 已结案 prediction snapshot + outcome 已 captured → review_orchestrator
  才允许调用

### 14.3 briefing read-only tests

- `pre_prediction_briefing` / `projection_memory_briefing` / `memory_feedback`
  source 中**不**出现：
  - 修改 projection_result / exclusion_result / confidence_result /
    final_report 任一字段
  - 写回 prediction_store / projection_record_store
- AST-level grep + behavior test
- **当前 `_apply_briefing_caution` 违反**——§15 PR-REVIEW-2 必须修复

### 14.4 memory lifecycle tests

- rule_lifecycle 5 状态转换测试
- candidate → watchlist → promoted_active 转换条件
- weakened / retired 触发条件
- rejected：与 1.0 §10 / promotion OFFLINE_ONLY 一致

### 14.5 review_result shape tests

- §12.1 草案字段全部出现
- `status = "ok"` 时所有字段非空（除 LLM optional）
- `status != "ok"` 时仍 well-formed
- `schema_version = "review_result.v1"`

### 14.6 no trading fields tests

- 输出 dict 字段集合中**不含**：`simulated_trade` / `trading_action` /
  `buy` / `sell` / `hold` / `no_trade` / `hard_*` / `forced_*` /
  `required_*` / `_PROTECTION_LAYER_CONNECTED` / `production_promotion`

### 14.7 no hard / forced / required fields tests

- 与 §14.6 重叠；显式 AST-level grep
- review_agent post-check：LLM 输出含 trading / hard / forced / required
  → reject

### 14.8 2026 holdout non-contamination tests

- 2026-01-01 之后 outcome 不进 in-sample review / lesson / calibration
- cutoff_guard 强制

### 14.9 false exclusion review tests

- exclusion_reliability_review 输出 reliability item shape 稳定
- anti_false_exclusion_audit 输出 `final_decision ∈ {hard_excluded,
  soft_excluded, blocked_by_audit}`
- 二者**不**改写当次 exclusion_layer 输出

### 14.10 baseline & regression

- 每个 PR-REVIEW-* 必须以 Step 15 baseline 为起点（**3256 passed, 10
  skipped, 0 failed, 26 warnings, 94 subtests**）
- 新增测试数显式累加到 passed
- warnings / subtests 数变化必须**显式说明**

---

## 15. Review & Learning Layer 后续 PR 候选

> **本节是 PR 候选清单，本轮 17K 不执行任一项**。最早 18A 由用户单独
> 决定执行哪个、何时执行、按什么顺序执行。

| 序号 | 名称 | 性质 | 目标 | 文件范围 | 测试 | 风险 | 是否必须先做 |
|---|---|---|---|---|---|---|---|
| **PR-REVIEW-1** | review_result contract helper / validator | 代码（新增 helper） | 新增 `services/review_result_contract.py`：定义 `REVIEW_RESULT_FIELDS` + `validate_review_result(result) -> list[str]` 纯函数 validator；体例与 17A / 17F PR-FEATURE-1 / 17G PR-PROJ-1 / 17H PR-EXCL-1 / 17I PR-CONF-1 / 17J PR-FINAL-1 一致；**不**改 review_orchestrator 实现 | `services/review_result_contract.py`（新增）+ `tests/test_review_result_contract.py`（新增） | focused + full pytest | L | 不强制；推荐第一项 |
| **PR-REVIEW-2** | `_apply_briefing_caution` 改为 warning-only / marker | 代码（关键违反修复） | 把 `predict.py:_apply_briefing_caution` 行为改为：(a) **不**修改 `result["final_confidence"]` (b) 仅追加 `briefing_caution_applied` / `briefing_caution_reason` 标记 (c) caller path 把 caution 信息透传到 final_report.warning_cards（需 17J PR-FINAL-4 协同）或 final_report.risks (d) 加 boundary test：no-mutation of `final_confidence` from briefing path | `predict.py`（仅 `_apply_briefing_caution` 函数 + caller wiring）+ tests | focused + full pytest；现有 caller 兼容 | **H** | 不强制；与 17J PR-FINAL-4 协同；最重要的一个 PR |
| **PR-REVIEW-3** | briefing read-only boundary tests | 代码（仅 tests） | 给 `pre_prediction_briefing` / `projection_memory_briefing` / `memory_feedback` / `review_agent` 加 `tests/test_review_briefing_boundary.py`：(a) AST-level grep 不修改 projection / exclusion / confidence / final_report (b) cutoff_guard 强制 (c) review_agent post-check trading / hard / forced / required reject | tests only | focused + full pytest | L | 不强制 |
| **PR-REVIEW-4** | review_store / memory_store lifecycle schema plan | **文档 only** | 写 `tasks/record_17k_pr_review_4_lifecycle_schema_plan.md`：决定 review_store / memory_store / rule_lifecycle 3 套 sqlite 之间的关系；当前共享 `avgo_agent.db`（review）vs `data/experience_memory.db`（memory）；schema 是否合并 / 收敛；rule lifecycle 5 状态如何持久化 | doc only | n/a | L | 不强制 |
| **PR-REVIEW-5** | exclusion_reliability_review 归位 / freeze marker | 代码（**仅** docstring） | 给 `services/exclusion_reliability_review.py` 顶部 docstring 加 marker：`CORE_REVIEW_LEARNING — moved from Exclusion Layer per 17H §15.3 / 17K §11`；**不**改逻辑 | 仅 docstring | full pytest byte-stable | L | 不强制 |
| **PR-REVIEW-6** | anti_false_exclusion_audit 归位 / freeze marker | 代码（**仅** docstring） | 给 `services/anti_false_exclusion_audit.py` 顶部 docstring 加 marker：`CORE_REVIEW_LEARNING / SHARED_WITH_EVALUATION — offline audit；moved from Exclusion Layer per 17H §7.1 / 17K §11`；**不**改逻辑 | 仅 docstring | full pytest byte-stable | L | 不强制；与 17L 协同 |
| **PR-REVIEW-7** | outcome_capture boundary tests | 代码（仅 tests） | 给 `services/outcome_capture.py` 加 `tests/test_outcome_capture_boundary.py`：(a) forbidden import（不 import main_projection / exclusion_layer / confidence_evaluator / final_decision） (b) cutoff guard：target_date 之前 close 不可读 (c) no-mutation of current prediction snapshot | tests only | focused + full pytest | L | 不强制；与 17L 协同 |
| **PR-REVIEW-8** | memory rule lifecycle plan | **文档 only** | 写 `tasks/record_17k_pr_review_8_rule_lifecycle_plan.md`：决定 rule_lifecycle 5 状态机的判断条件（candidate → watchlist 阈值 / weakened → retired 阈值）；与 `services/active_rule_pool*` 系列协同；与 `active_rule_pool_promotion` OFFLINE_ONLY 边界一致；与 17L Evaluation 协同 | doc only | n/a | L | 不强制；推荐 17L 之后 |

### 15.1 候选 PR 之间的依赖

- PR-REVIEW-1 → PR-REVIEW-3：先有 contract validator，再做 boundary tests
- PR-REVIEW-2 ⚠️ **关键修复**——依赖 17J PR-FINAL-4（warning_cards schema）；
  推荐 17J PR-FINAL-4 先落地
- PR-REVIEW-5 / PR-REVIEW-6：互不依赖
- PR-REVIEW-7：可独立做
- PR-REVIEW-4 / PR-REVIEW-8：文档 only；推荐在 PR-REVIEW-1 之后写
- 任何**代码** PR-REVIEW-* 都依赖 **17K 已入 main**（前置条件）

### 15.2 候选 PR 都不能做的事

- ❌ 不改 review_store / memory_store sqlite schema（17K 阶段；schema 改动
  归 18A+）
- ❌ 不改 review_orchestrator / review_comparator / review_classifier /
  review_analyzer 业务逻辑
- ❌ 不动 outcome_capture 的 actual_state classification 阈值
- ❌ 不让 review_agent 写回 prediction / exclusion / confidence / final_report
- ❌ 不让 review_agent 进默认 active path（保持 fallback to rule-based）
- ❌ 不复活 `services/active_rule_pool_promotion.py` OFFLINE_ONLY 边界
  （与 1.0 §6.5 / 13 §4-§5 一致）
- ❌ 不让 memory_store 直接进 active inference path 写回
- ❌ 不让 cutoff_guard 在 17K 内被绕过
- ❌ 不切换默认 `run_predict` 路径
- ❌ 不引入 trading / hard / forced / required
- ❌ 不复活 `continuous_smoothing*` / `archive/legacy/root_stubs/*`
- ❌ 不修改 `.gitignore`
- ❌ 不处理 `avgo_agent.db`（含 backup）
- ❌ 不处理 handoff / logs / DB backup / `.claude/worktrees/`
- ❌ 不在 17K 阶段实现 PR-REVIEW-2（关键违反修复）—— 17K 仅识别，不修
- ❌ 不动 `services/anti_false_exclusion_dashboard.py`（17L 决定）

---

## 16. 与 Final Report / Evaluation / UI 的交接

### 16.1 数据流方向（与 1.0 §9 / 17F § ~ 17J § 一致）

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
   （17K本轮）（17L）   （17M）
```

### 16.2 Final Report 当次输出完成后，Review 才能事后读取

- 与 1.0 §8 Branch 7 / 06 §6 一致
- review_orchestrator 输入：prediction_store + outcome_capture
- prediction_store 中 `final_report` 是当次输出 snapshot；**只读**

### 16.3 Evaluation 批量读取 Review / prediction / outcome 做统计

- 与 1.0 §8 Branch 8 一致
- Branch 8 不写 review_store / memory_store
- Branch 8 输出 metrics 报告（17L 详谈）

### 16.4 UI 只展示 review / memory / lessons，不重算

- 与 1.0 §8 Branch 9 / §13 hard rule 3 一致
- UI 通过 review_orchestrator / review_store / memory_store 读取
- **不**重算 review classification

### 16.5 Review 不负责 UI layout

- 与 1.0 §13 hard rule 3 一致
- UI rendering 由 ui/review_tab.py / ui/exclusion_reliability_review.py
  等 ui/ 模块负责

### 16.6 Review 不写 Evaluation dashboard

- review_center 仅产 small-window stats（per-call）
- Branch 8 的 full dashboard 由 17L 决定

### 16.7 Review 不接 trading

- 与 1.0 §6.1 / §13 hard rule 1 一致
- review_agent 已严格锁住 LLM 不输出 trading suggestion
- §15 PR-REVIEW-3 boundary tests 强化

---

## 17. 清场 / 隔离建议

> **本节按 16H 决策表 8 个标签给出 Review & Learning Layer 范畴内的清场
> 建议**。本轮**不**执行任何清场动作。

### 17.1 KEEP（Review & Learning Layer CORE）

- `services/review_orchestrator.py`
- `services/review_comparator.py`
- `services/review_classifier.py`
- `services/review_analyzer.py`
- `services/review_center.py`
- `services/review_agent.py`（OPTIONAL_LLM）
- `services/review_store.py`
- `services/memory_store.py`
- `services/memory_feedback.py`
- `services/projection_memory_briefing.py`
- `services/pre_prediction_briefing.py`
- `services/projection_review_closed_loop.py`
- `services/exclusion_reliability_review.py`（CORE_REVIEW_LEARNING；从 17H 接管）
- `services/anti_false_exclusion_audit.py`（SHARED_WITH_EVALUATION；从 17H 接管）
- `services/rule_lifecycle.py`
- `services/rule_scoring.py`
- `services/active_rule_pool.py` / `_drift.py` / `_export.py` /
  `_validation.py`（rule pool helper 集合）

### 17.2 NOT_REVIEW_LEARNING（声明非 Review；归其它层）

- `services/contract_outcome_correlation.py` → 17L Evaluation
- `services/anti_false_exclusion_dashboard.py` → 17L Evaluation / 17M UI
  （17H §15.3）
- `services/active_rule_pool_calibration.py` → 17L Evaluation
  （17I §17.3 / §13 PR-CONF-7）
- `services/log_store.py` → INFRA（infrastructure；多模块共享）
- `services/prediction_store.py` → INFRA
- `services/projection_record_store.py` → INFRA

### 17.3 OFFLINE_ONLY（永久封禁；不进 active path）

- `services/active_rule_pool_promotion.py` —— 与 1.0 §6.5 / 13 §4-§5 一致；
  17K 不复活；保留作 offline review tooling

### 17.4 LEGACY_VIOLATION（必须修复）

- `predict.py:_apply_briefing_caution`（function inline）—— §10；§15
  PR-REVIEW-2

### 17.5 MIGRATE_LATER

- §17.2 全部模块 → 对应层 Plan 接管

### 17.6 ARCHIVE_IN_REPO

- 无 Review Layer 范畴的 archive 候选（与 16H / 17E §15.5 / 17F §16.5 /
  17G §16.8 / 17H §15.5 / 17I §17.6 / 17J §17.7 一致）

### 17.7 QUARANTINE

- 无 Review Layer 范畴的 quarantine 候选（CORE 状态健康；OFFLINE_ONLY 已
  锁定）

### 17.8 DELETE_NOW

- **空**（与 16H §13 / 17E §15.7 / 17F §16.7 / 17G §16.11 / 17H §15.8 /
  17I §17.8 / 17J §17.9 一致）

### 17.9 DELETE_LATER

- 无 Review Layer 范畴（17K 阶段）

### 17.10 MIGRATE_CALLER_FIRST

- `predict.py:_apply_briefing_caution`：caller 路径迁移在 PR-REVIEW-2
  之前必须先看 17J PR-FINAL-4 warning_cards schema 是否落地

### 17.11 MOVE_OUTSIDE_REPO

- 无 Review Layer 范畴

### 17.12 DEEP_AUDIT_REQUIRED

- `services/active_rule_pool.py` / `_drift.py` / `_export.py` /
  `_validation.py` / `_calibration.py`（5 项）—— 16G §11 列出的 10 项
  UNKNOWN 中的 5 项；本轮 17K 仅声明归属（前 4 项归 Review；calibration
  归 Evaluation）；deep audit 由 §15 PR-REVIEW-8 / 17L 决定时机

> **重申**：任何文件删除 / 移动 / archive 必须等 16H 规则 + 17D §11 + 用户
> 单独确认。17K 仅给出**建议**，**不**执行。

---

## 18. 不允许事项

**17K 起，Review & Learning Layer 范畴内**严格禁止：

- ❌ 不改代码（无 `.py` 文件被修改；本轮 0 修改）
- ❌ 不跑数据
- ❌ 不跑 replay / 不跑 validation / 不跑 historical evaluation
- ❌ 不改 DB / 不改 DB schema（review_store / memory_store schema 保持）
- ❌ 不迁 Evaluation / UI（17L / 17M 自负其责）
- ❌ 不接 trading / 不输出 buy / sell / hold / hard / forced / required
- ❌ 不进入 3R-5 / 3R-6（1.0 §12 / 16I §15 / 17D §11 / 17E §16 / 17F §17 /
  17G §17 / 17H §16 / 17I §18 / 17J §18 / 本轮再次重申）
- ❌ 不启动任何代码 PR（PR-REVIEW-* 候选要等 18A）
- ❌ 不修改 `.gitignore`
- ❌ 不处理 `avgo_agent.db`（含 backup）
- ❌ 不处理 handoff / logs / DB backup / `.claude/worktrees/`
- ❌ 不复活 `continuous_smoothing*` / `archive/legacy/root_stubs/*`
- ❌ 不复活 `services/active_rule_pool_promotion.py` OFFLINE_ONLY 边界
- ❌ 不污染 2026-01-01 之后 final holdout
- ❌ 不借 17K 顺手做 Data / Feature / Projection / Exclusion / Confidence /
  Final Report / Evaluation / UI 范畴改动
- ❌ **不直接修 `_apply_briefing_caution`**（与 17D §11 一致；归 §15
  PR-REVIEW-2）
- ❌ **不直接改 review / memory / outcome 逻辑**（与 17D §11 一致）
- ❌ 不启动 UI / Evaluation / Bridge / orchestrator 实现任务（与 17D §10
  一致）
- ❌ 不让 review_agent 进默认 active path
- ❌ 不让 memory_store 直接写回当次结果
- ❌ 不让 cutoff_guard 在 17K 内被绕过

> 与 17D §11 / 17E §16 / 17F §17 / 17G §17 / 17H §16 / 17I §18 / 17J §18
> 一致；本轮再次锁定。

---

## 19. 推荐下一步

> **首选**：**Step 17L：Evaluation Layer Rebuild Plan**

理由（与 17D §12 / 17E §17 / 17F §18 / 17G §18 / 17H §17 / 17I §19 / 17J §19
一致 + 17K 实战观察）：

- Review & Learning Layer 计划（17K）已就位
- 数据流方向是 Data → Feature → {Projection, Exclusion, Confidence} →
  Final Report → {Review, **Evaluation**} → UI（1.0 §9 / 16C §3）
- 按九分支编号顺序，下一层是 Evaluation（Branch 8）
- **17L 的工作量中等**：17L 必须接管
  - `services/contract_outcome_correlation.py`（Branch 8 batch metric）
  - `services/anti_false_exclusion_dashboard.py`（17H §15.3 / 17J §17.4
    / 17K §17.2 共同声明）
  - `services/active_rule_pool_calibration.py`（17I §17.3 / 17K §17.2）
  - `services/active_rule_pool_validation.py`（17K §6.13 / §17.1 共享）
  - `services/regime_validation_helper.py`（17F §7.11 已声明 Evaluation）
  - `services/primary_bias_diagnosis.py`（17F §7.10 已声明 Evaluation）
  - `services/contract_payload_inspector.py`（17J §17.4）
  - `services/contract_payload_diff.py` / `contract_payload_trend.py` /
    `contract_payload_extras_dashboard.py`（同类 batch diagnostic）
  - `matcher.py` 的 NextDate / NextOpenChange 等"未来 K 线"字段（17F §7.2 /
    §12.3 / 17J §16.2 共同声明 → Evaluation）
  - `services/historical_replay_training.py`（replay 主入口）
  - 2026-01-01 之后 final holdout 的处理路径
  - calibration / win-rate 表的产出形式（输出回 Confidence，不沿其他路径回流）
- 17L 入 main 之前，**不**允许在 Evaluation Layer 范畴开任何代码 PR

**不推荐**：

- 不推荐跳到 17M（必须先有 Evaluation Plan）
- 不推荐借 17K / 17L 做代码改动（与 17D §11 一致）
- 不推荐重启 16I PR-E / PR-F / PR-G / PR-H（必须等对应层 Plan）
- 不推荐解锁 3R-5 / 3R-6（1.0 §12 7 项前提仍未全部满足）
- 不推荐立刻做 PR-REVIEW-* 任一项（与 17K 协同更合算）
- 不推荐立刻实现 architecture_orchestrator MVP（17J §13.6 前置条件未满足）
- 不推荐立刻修 `_apply_briefing_caution`（PR-REVIEW-2 必须等 17K 入 main +
  17J PR-FINAL-4 warning_cards schema 协同 + 18A 审批）

> **明确**：本轮 17K 推荐的下一步**只有一个候选**——17L Evaluation Layer
> Rebuild Plan。

---

## 20. 严守边界

本轮 Step 17K **只**写 Review & Learning Layer Rebuild Plan：

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
- ❌ 未启用任何 candidate / 未复活 `continuous_smoothing` / `active_rule_pool_promotion`
- ❌ 未触碰 RISK-1 / RISK-2 / RISK-3 / RISK-7 / RISK-8 / RISK-9 / RISK-10
- ❌ 未进入 3R-5 / 3R-6
- ❌ 未启动任何代码 PR（PR-REVIEW-* 候选要等 18A）
- ❌ 未直接修 `_apply_briefing_caution`（关键违反点已识别；归 §15 PR-REVIEW-2）
- ❌ 未直接改 review / memory / outcome 逻辑
- ❌ 未启动 UI / Evaluation / Bridge / orchestrator 实现任务
- ❌ 未做任何局部 patch
- ❌ 未 commit / 未 push（按本轮指令）

唯一新增文件：[tasks/record_17k_review_learning_layer_rebuild_plan.md](tasks/record_17k_review_learning_layer_rebuild_plan.md)（本文件）。

后续修改路径：任何对 §3 职责定义 / §4 禁止事项 / §5 inventory / §6
CORE_REVIEW_LEARNING / §7 outcome_capture / §8 review_store / memory_store /
§9 briefing / §10 `_apply_briefing_caution` 问题 / §11 reliability /
audit / §12 review_result 标准化 / §13 与 Evaluation 边界 / §14 测试
策略 / §15 PR 候选 / §16 与 Final Report / Evaluation / UI 交接 / §17
清场建议 / §18 禁止事项 / §19 下一步 的调整，都必须**显式更新本文件**；
同时检查是否需要同步更新 1.0 / 16C / 16D / 16I / 17D / 17E / 17F / 17G /
17H / 17I / 17J 与 17L（17L 入 main 后）。
