# 17H记录：Exclusion Layer Rebuild Plan

> 本记录是 **Step 17H：Exclusion Layer 重建计划**——九分支按层重建中的
> **第四层**（Branch 4）。1.0 canonical / 16A blueprint / 16B inventory /
> 16C target dataflow & contract decision / 16D isolation & quarantine
> plan / 16E core chain refactor plan / 16F no-patching principle / 16G
> full module decomposition standup / 16H repository clearing decision
> table / 16I core chain rebuild execution plan / 17A PR-B standard
> payload skeleton / 17B PR-C peer_alignment 抽公共模块 / 17C PR-D
> main_projection 去 `exclusion_result` 形参 / 17D layer-by-layer rebuild
> governance / 17E Data Layer Rebuild Plan / 17F Feature Layer Rebuild
> Plan / 17G Projection Layer Rebuild Plan 已全部入 main（main 最新
> commit `54f74f1`）。
>
> 本轮**只**写计划文档：未改业务代码、未新增测试、未删除文件、未移动
> 文件、未修改 `.gitignore`、未处理 handoff、未处理 logs / DB backup /
> `.claude/worktrees/`、**未处理 `avgo_agent.db`**、未跑 replay /
> validation / historical evaluation、未写 DB / 未改 DB schema、未默认
> 迁移 `run_predict` 到 V2、未接 trading、未输出 buy / sell / hold /
> hard / forced / required、未进入 3R-5 / 3R-6、未启动任何代码 PR、
> 未继续 PR-E confidence key 对齐、未启动 UI / bridge / orchestrator
> 实现任务、未做任何局部 patch、未 commit / 未 push。
>
> 唯一 deliverable：本文件。
>
> **本记录优先级**：与 17E / 17F / 17G / 17I ~ 17M 各层 Plan 同级；与
> 1.0 / 16A / 16C / 16D / 16F / 16I / 17D / 17E / 17F / 17G 协同。冲突
> 仲裁路径与 1.0 §14 / 17D §13 一致：旧 records 若与 17H 在 Exclusion
> Layer 范畴冲突，**以 17H 为准**。

---

## 1. Step 17H 目的

把九分支按层重建从 Projection Layer（17G）推进到**第四层（Exclusion Layer）
的具体重建计划**。

**本轮只回答**：

- Exclusion Layer 当前长什么样（模块 inventory + active path）
- Exclusion Layer 目标长什么样（保留 / 迁移 / 隔离 / 删除候选）
- Exclusion Layer 与上下游的边界（Feature ↑；Confidence / Final Report ↓；
  **不**读 Projection / Confidence / Final Report / future outcome）
- `exclusion_result` 标准化规则（与 1.0 §8 Branch 4 / 07B §9 一致）
- `triggered_rule` interim → `triggered_rules` / `excluded_states` standard
  schema 迁移路线
- `false_exclusion_risk` 性质 / 边界
- contradiction / warning / reliability / anti_false / consistency 模块的
  归属判断
- Exclusion Layer 后续可能的代码 PR 候选（**不**执行）

**本轮不回答**：

- 不写 Confidence / Final Report / Review / Evaluation / UI 计划（17I ~ 17M）
- 不开任何代码 PR（最早 18A）
- 不动 `avgo_agent.db`、`.gitignore`、handoff、logs、DB backup、worktrees
- 不继续 PR-E confidence key 对齐（与 17D §9 一致）
- 不启动 UI / bridge / orchestrator 实现任务（与 17D §10 一致）

**本文件性质**：layer rebuild plan（按层计划），不是 design 也不是 impl。

### 1.1 本轮校正：anti_false_exclusion_rules 命名说明

> **校正**：用户请求中提及 `anti_false_exclusion_rules.py` /
> `anti_false_exclusion_rules_v2.py`——这两个文件**不存在**于当前 repo。
> 实际存在的相关模块是：
>
> - `services/anti_false_exclusion_audit.py`（Task 071A v1 + v2）
> - `services/anti_false_exclusion_dashboard.py`（Step 2G-7C 聚合 dashboard）
>
> 17H 按**实际存在**的模块做 inventory。命名差异在 §5 / §7 各处显式说明。
> 17H 文档**不**回溯修改用户请求；**不**误把不存在的文件列入 inventory。
> 与 16F 原则一致。

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
| main 最新 commit | `54f74f1` |
| worktree 唯一 deliberate untracked | `.claude/handoffs/task_089_post_pr_cleanup.md` |
| 战略阶段 | 从 Projection Layer plan（17G）→ **Exclusion Layer plan（17H 本轮）** |
| 3R-5 / 3R-6 | ❌ 仍然不允许进入 |
| 第一个按层实现 PR（18A）| ❌ 仍未 |

**17D §6 PR 准入规则提醒**：

- 任何代码 PR 必须绑定九分支某一层 + 引用对应层 Plan §
- 17H 入 main 后，Exclusion Layer 范畴的 PR 才**有资格**被讨论
- 17H 本身**不**自动批准任何 PR

**层间依赖**：

- 17H 依赖 17E / 17F（已就位）
- 17H 与 17G **不**互相依赖（Projection / Exclusion 并行；按 16I §10 / 17F §15
  数据流方向，二者对称）
- 17H 与 17I 在 confidence 读 exclusion_result 字段约定上有协同点；17I 入
  main 后正式 cross-reference

---

## 3. Exclusion Layer 职责定义

**Exclusion Layer（Branch 4）只回答一件事**：

> **"基于 feature_payload，回答'最不可能发生什么'，输出 `exclusion_result`。"**

### 3.1 只做的事（与 1.0 §8 Branch 4 / 07B §3.1 一致）

- 读取 Feature Layer 输出的 `feature_payload`
- 基于 AVGO 自身 15d / 20d 结构（来自 feature_payload）+ 五状态历史样本
  中"最少发生"的状态 + 历史 rare-event pattern + peer 非确认信号 + 成交量 /
  位置 / 趋势 / 反转 + regime label，**派生**"最不可能发生的状态"
- 输出 `most_unlikely_state` / `ranked_unlikely_states` /
  `state_impossibility_scores`（07B §9）
- 输出 `triggered_rules`（list；新 standard schema）
- 当前 interim schema：输出 `triggered_rule`（single；当前实现）
- 输出 `excluded_states`（五状态中文标签 list）
- 输出 `false_exclusion_risk`（自我风险标注；详见 §10）
- 输出 `primary_exclusion_reasoning` / `rare_event_evidence` /
  `historical_non_occurrence_summary` / `peer_non_confirmation_summary` /
  `key_exclusion_signals` / `key_counter_signals` / `uncertainty_notes` /
  `raw_evidence_refs`
- 使用 `peer_alignment` **作为 feature evidence**（17B PR-C / 1.0 §8 Branch 2
  一致——Exclusion 从 Feature Layer 读，**不**反向被 Projection 读）
- 标注 `non_mutation_confirmations.exclusion_did_not_read_projection = True`
  / `exclusion_did_not_read_confidence = True` / `exclusion_did_not_read_final_report = True`

### 3.2 不做的事（与 1.0 §8 Branch 4 / 07B §3.2 一致）

- ❌ 不判断 `most_likely_state`（归 Branch 3 Projection）
- ❌ 不输出五状态最终概率分布（`state_probabilities` 归 Projection）
- ❌ 不做 confidence（`agreement_status` / `combined_confidence` 归
  Branch 5 Confidence）
- ❌ 不做 final report（`combined_user_summary` 归 Branch 6 Final Report）
- ❌ 不做 review / lesson（归 Branch 7）
- ❌ 不做 evaluation（reliability metrics / win-rate 归 Branch 8）
- ❌ 不做 UI 展示
- ❌ 不输出 trading action / hard / forced / required
- ❌ 不调用 LLM
- ❌ 不写 DB / 不改 DB schema
- ❌ 不直接运行 replay
- ❌ 不直接接 broker API
- ❌ 不"根据主推演结果选择否定对象"（07B §3.2 / §6 / §10 锁定）

### 3.3 输入 / 输出（白名单）

**输入**（与 07B §3.1 / 17F §15 一致）：

- `feature_payload`（来自 Branch 2 Feature Layer，**唯一**输入入口）
- 五状态历史样本中"最少发生"的状态（通过 feature_payload 中的 historical
  rare-event summary 携带，或 Exclusion 内部从 `coded_data/` 读取——属
  Feature Layer ownership）
- regime label（来自 feature_payload）

**输出**（草案 schema_version `exclusion_system_result.v1`，与 07B §9 一致）：

- `exclusion_result` dict（结构详见 §8）

**禁止输入**（与 07B §3.2 / 07B §10 一致）：

- ❌ `projection_result` / `most_likely_state` / `final_prediction` /
  `primary_direction`
- ❌ `confidence_result`
- ❌ `final_report`
- ❌ `review_record`
- ❌ `evaluation_report`
- ❌ Future outcome（在线 inference 路径）
- ❌ 2026-01-01 之后 final holdout（在线 inference）
- ❌ Trading 输入 / broker / position state

---

## 4. Exclusion Layer 禁止事项

Exclusion Layer **永久禁止**输出 / 引入以下任一：

| 类别 | 禁止项 | 锚点 |
|---|---|---|
| 主推演输出 | `most_likely_state` / `predicted_top1` / `predicted_top2` / `state_probabilities` / `direction`（Projection 输出方向）| 07B §3.2 / 1.0 §8 Branch 4 |
| 置信度输出 | `confidence_score` / `confidence_level` / `combined_confidence` / `agreement_status` | 07B §3.2 / 07C §5 |
| Final Report 字段 | `combined_user_summary` / `agreement_or_conflict_section` / `non_mutation_confirmations`（自身仅可标 `exclusion_did_not_read_*`，**不**写其他系统的 non-mutation）| 07B §3.2 / 07D §6 |
| 交易 / 强制 | `buy` / `sell` / `hold` / `simulated_trade` / `trading_action` / `hard_*` / `forced_*` / `required_*` | 12E X1..X5 / 1.0 §6 / §13 hard rule 1 |
| 系统输出回灌（input） | 读取 `projection_result` / `confidence_result` / `final_report` 字段后**用作 evidence / weight / mutation** | 1.0 §9 数据流方向 / 07B §3.2 |
| 下游模块 import（active path） | import `services.main_projection_layer` / `services.confidence_evaluator` / `services.final_decision` / 任何 `predict.*` 反向调用 | 07B §10 |
| LLM 调用 | `anthropic` / `openai` / 任何文本生成 SDK | 1.0 §13 hard rule 1 / 5 |
| UI 调用 | `streamlit` / 任何 ui/ 模块 import | 1.0 §13 hard rule 3 |
| DB schema 改动 | `CREATE TABLE` / `ALTER TABLE` 在 17H 阶段不允许 | 17E §11 / 17F §11 / 17G §11 / 17H §11 |
| 直接运行 replay | 调用 `scripts/run_contract_replay*` / `scripts/historical_replay_training*` | 17D §11 |
| Future outcome 回灌 | 在线 inference 路径中读取目标日之后的 close / outcome | 1.0 §9 / 07B §3.2 |
| 污染 2026 holdout | 在 in-sample exclusion 计算中读取 2026-01-01 之后的窗口 | 1.0 §5 rule 8 |
| 根据 projection 选择否定对象 | "看到 projection 说大涨 → 我就不去否定大涨" | 07B §3.2 / §6 / §10 |

---

## 5. 当前 Exclusion Layer 模块 inventory

> **范围说明**：本表覆盖 (1) **核心 Exclusion 模块** (2) **Anti-false /
> Audit / Dashboard** (3) **Contradiction / Warning / Reliability** (4)
> **跨层 helper（projection_chain_contract / final_decision /
> confidence_evaluator 中读 exclusion_result 部分）**。standard payload
> skeleton（17A PR-B）属 INFRA / SCHEMA，不在本表（与 17F §5 / 17G §5
> 一致）。

| module_path | current_role | current_status | target_role | keep / migrate / quarantine / delete | active_callers | risk | next_action |
|---|---|---|---|---|---|---|---|
| `services/exclusion_layer.py` | Branch 4 主入口；`run_exclusion_layer` + `exclude_big_up` + `exclude_big_down`；当前**只**输出 `exclude_big_up` / `exclude_big_down` 二选一（不输出五状态完整 ranked_unlikely）；用 17B PR-C `peer_alignment` | KEEP_ACTIVE；docstring "Prediction-style exclusion layer for projection v2" | **CORE_EXCLUSION**：Branch 4 主入口 | KEEP | `services/home_terminal_orchestrator:23`、`services/projection_orchestrator_v2:21`、`services/confidence_evaluator`、tests | L | §6.1；§14 PR-EXCL-2 显式 standard schema 输出 keys（new schema + interim alias）|
| `services/anti_false_exclusion_audit.py` | Task 071A v1 + v2：**offline-only audit**；接受"已决定的硬否定"作为输入 → 输出 `final_decision ∈ {hard_excluded, soft_excluded, blocked_by_audit}`；4 个 auditor（rebound / breakout / peer_catchup / consolidation_breakout） | KEEP_ACTIVE | **NOT_EXCLUSION_LAYER**：归 Branch 7 Review & Learning（offline 审核当次硬否定）/ Branch 8 Evaluation（reliability gate）；docstring 自称 "audit layer"，明确不 modify production；归属是 Review / Evaluation 边界 | MIGRATE_LATER（17K / 17L 决定）| `services/big_up_contradiction_card`、`services/exclusion_reliability_review`、tests | M | §7.1；17H 声明非 Exclusion 主路径 |
| `services/anti_false_exclusion_dashboard.py` | Step 2G-7C 聚合 dashboard；SELECT-only；6 项 hard gate 状态 + soft metadata baseline | KEEP_ACTIVE；docstring 显式 "read-only" / 不写 DB / 不调 trading | **NOT_EXCLUSION_LAYER**：归 Branch 8 Evaluation（reliability dashboard）/ Branch 9 UI（17M 决定渲染） | MIGRATE_LATER（17L / 17M 决定） | tests；scripts | L | §7.2 |
| `services/big_up_contradiction_card.py` | Task 085：**read-only presentation layer**；调 `audit_big_up_exclusion` + 翻译为中文 warning；docstring 自称 "lives in services/ not ui/" 因为含逻辑 | KEEP_ACTIVE | **NOT_EXCLUSION_LAYER**：归 Branch 6 Final Report（display）+ Branch 9 UI（17J / 17M 共同决定）；逻辑层归 Final Report 显示模块 | MIGRATE_LATER（17J / 17M）| `services/exclusion_reliability_review`、`ui/predict_tab.py`、scripts、tests | M | §7.3 |
| `services/big_down_tail_warning.py` | pure logic：tail compression / strong warning / downgrade detection；输出 strong_warning / downgrade flags；不调外部模块 | KEEP_ACTIVE；纯函数 | **NOT_EXCLUSION_LAYER**：归 Branch 6 Final Report（display warning）；输入是已发生数据，输出是展示用 warning，不参与 exclusion 主路径 | MIGRATE_LATER（17J）| `services/exclusion_reliability_review`、scripts、tests | L | §7.4 |
| `services/exclusion_reliability_review.py` | 把 big_up_contradiction_card + big_down_tail_warning + 历史 row → 综合 reliability item；提供 `build_exclusion_reliability_review` 给 UI / scripts | KEEP_ACTIVE；docstring 没明确 layer 标签 | **NOT_EXCLUSION_LAYER**：归 Branch 7 Review & Learning（事后复盘 reliability）；性质是"对已发生 exclusion 的可靠性审计"，**不**参与当次 exclusion 决策 | MIGRATE_LATER（17K）| `ui/exclusion_reliability_review.py`、`scripts/batch_run_exclusion_reliability_review_3c3.py`、tests | M | §7.5 |
| `services/consistency_layer.py` | internal consistency checks across projection / exclusion / **confidence** layers；docstring "checks whether existing layer outputs agree with each other"；输入是三系统输出，输出是 consistency_flag / conflict_reasons | KEEP_ACTIVE；docstring 不显式 layer 标签 | **NOT_EXCLUSION_LAYER**：归 Branch 6 Final Report（cross-system aggregator 之前的 consistency check）；与 17F §6.8 / 17G §16.4 一致 | MIGRATE_LATER（17J）| `services/home_terminal_orchestrator:22`、`services/projection_orchestrator_v2:23`、tests | M | §7.6 |
| `services/projection_chain_contract.excluded_state_from_result` | 把 `exclusion_result.triggered_rule` → 中文 state（`exclude_big_up` → `大涨` / `exclude_big_down` → `大跌`）；纯函数 | KEEP_ACTIVE | **EXCLUSION_ADAPTER_HELPER**：属 Exclusion 输出之后的 schema adapter；归 Branch 4 边界 helper（与 17F §7.6 / §C.4 一致） | KEEP（不动）；与 §11 triggered_rule → excluded_states 迁移协同 | confidence_evaluator / projection_chain_contract.build_prediction_log_record / tests | L | §6.4 |
| `services/projection_chain_contract.build_prediction_log_record` | 含 `excluded_state` / `exclusion_action` / `exclusion_triggered_rule` 字段输出 | KEEP_ACTIVE | **NOT_EXCLUSION_LAYER**：归 Final Report / prediction store helper；17F §7.6 / 17J 决定（这里仅 cross-reference） | KEEP（不动） | predict.py / V2 chain / log_store / tests | L | 17H 不动 |
| `services/final_decision.py` 中 `exclusion_result` 读取部分 | 当前 `build_final_decision` 接 `exclusion_result` 仅作 display；输出 `exclusion_section`；含 `most_unlikely_state` 字段（来自 `exclusion_result.most_unlikely_state`，但当前 exclusion_layer **未输出**该字段——见 §11.2）| KEEP_ACTIVE；docstring 显式 boundary contract 06 / 07C / 07D / 11B | **NOT_EXCLUSION_LAYER**：归 Branch 6 Final Report（17J 决定）；当前是 final_decision 的 exclusion display 部分 | KEEP（不动）；17J 接管 final_decision 的整体处置 | V2 chain / tests | L | §15 / 17J |
| `services/confidence_evaluator.py` 中读取 `exclusion_result` 部分 | `build_confidence_result` 读 `exclusion_result.most_unlikely_state` / `exclusion_result.triggered_rule`；当前 exclusion_layer 实际**只**输出 `triggered_rule`，**未**输出 `most_unlikely_state` —— 这是 PR-E confidence key 对齐需要修的（与 17D §9 一致；归 17I）| KEEP_ACTIVE | **NOT_EXCLUSION_LAYER**：归 Branch 5 Confidence（17I 决定）；当前 schema 不齐由 17I 处理 | KEEP（不动）；17I 接管 | V2 chain / home_terminal / tests | M | §11.2 / §15 / 17I |
| `tests/test_exclusion_layer.py` | exclusion_layer boundary tests | KEEP | KEEP | KEEP | — | L | 不动 |
| `tests/test_anti_false_exclusion_dashboard.py` | dashboard tests | KEEP（属 Branch 8 / Branch 9 测试范围） | KEEP | KEEP | — | L | 不动 |
| `tests/test_big_down_tail_warning.py` | tail warning tests | KEEP（属 Branch 6 测试范围） | KEEP | KEEP | — | L | 不动 |
| `tests/test_big_up_contradiction_card.py` | contradiction card tests | KEEP（属 Branch 6 / 9 测试范围） | KEEP | KEEP | — | L | 不动 |
| `tests/test_consistency_layer.py` | consistency boundary tests | KEEP（属 Branch 6 测试范围） | KEEP | KEEP | — | L | 不动 |
| `tests/test_peer_alignment_boundary.py` 中 `services.exclusion_layer` import 限制 | 17B PR-C boundary tests；扫 source 禁反向 import | KEEP | KEEP | KEEP | — | L | 不动 |

### 5.1 关键说明

- **Exclusion Layer 当前唯一**真正符合 1.0 §8 Branch 4 / 07B 契约的入口
  是 `services/exclusion_layer.py`。
- **当前 exclusion_layer 输出 schema 是 interim，不符合 07B §9**：
  - 现有：`excluded` (bool) / `action` (`"exclude"` / `"allow"`) /
    `triggered_rule` (single str：`"exclude_big_up"` / `"exclude_big_down"` / `None`) /
    `summary` / `reasons` / `peer_alignment` / `feature_snapshot`
  - 07B §9 要求：`most_unlikely_state` / `ranked_unlikely_states` /
    `state_impossibility_scores` / `primary_exclusion_reasoning` /
    `rare_event_evidence` / `historical_non_occurrence_summary` /
    `peer_non_confirmation_summary` / `key_exclusion_signals` /
    `key_counter_signals` / `uncertainty_notes` / `raw_evidence_refs` /
    `false_exclusion_risk` / `triggered_rules` (list)
  - 差距由 §14 PR-EXCL-2 / PR-EXCL-3 / PR-EXCL-4 在 18A+ 弥补
- **当前 confidence_evaluator 期望读 `most_unlikely_state` 但 exclusion_layer
  未输出**——这是 1.0 §3 描述的 "confidence_evaluator 字段不对齐，容易
  unknown" 问题；归 17I 解决（与 17D §9 一致）
- **`anti_false_exclusion_*` / `big_up_contradiction_card` /
  `big_down_tail_warning` / `exclusion_reliability_review` 都不属于 Branch 4
  主路径**：它们要么是 offline audit（Review / Evaluation），要么是
  display warning（Final Report / UI）
- **`consistency_layer` 不属于 Branch 4**：跨 projection / exclusion /
  confidence；归 Branch 6 Final Report 之前的 consistency check
- **DELETE_NOW 集合为空**（与 16H §13 / 17E §15.7 / 17F §16.7 / 17G §16.11
  一致）

---

## 6. CORE_EXCLUSION 保留模块

> Exclusion Layer 的**核心保留模块**：当前**只有 1 个**主入口（17H 阶段
> 无歧义归属 Branch 4 的 active asset）。

### 6.1 `services/exclusion_layer.py`

| 维度 | 说明 |
|---|---|
| 为什么保留 | Branch 4 唯一**符合 07B 契约方向**的主入口；17B PR-C 已迁出 peer_alignment；docstring 显式 "Prediction-style exclusion layer for projection v2"；输出当前 interim schema |
| 目标职责 | (1) 接收 `feature_payload`（含 pos20 / vol_ratio20 / shadow / ret1-5 / peer ret1）(2) 派生 most_unlikely_state + ranked_unlikely_states（**未来** standard schema）(3) 输出当前 interim schema（`triggered_rule` single）兼容旧 caller (4) 输出 `false_exclusion_risk` 自我风险标注 |
| 是否需要改名 / 拆分 | ❌ 17H 不改名；不拆分 |
| 是否有跨层问题 | ⚠️ 当前输出 schema 与 07B §9 / confidence_evaluator 期望不齐（详见 §11.2）；这是 **schema 差距**，不是结构性反向 import 问题 |
| 后续实现任务 | §14 PR-EXCL-1：exclusion_result contract validator；§14 PR-EXCL-2：输出 standard keys（new schema + interim alias）；§14 PR-EXCL-3：triggered_rule → triggered_rules + excluded_states migration；§14 PR-EXCL-4：false_exclusion_risk 标准化 |
| 当前禁止动作 | 不改 `_UPSIDE_EXCLUDE_THRESHOLD` / `_DOWNSIDE_EXCLUDE_THRESHOLD` 阈值；不改 `_kill_risk` 阈值；不在 17H 改输出字段集；不引入 confidence / projection import |

### 6.2 候选模块的归属判断（不属于 CORE_EXCLUSION）

| 模块 | 归属（17H 决定）|
|---|---|
| `services/anti_false_exclusion_audit.py` | NOT_EXCLUSION_LAYER → Branch 7 Review / Branch 8 Evaluation |
| `services/anti_false_exclusion_dashboard.py` | NOT_EXCLUSION_LAYER → Branch 8 Evaluation / Branch 9 UI |
| `services/big_up_contradiction_card.py` | NOT_EXCLUSION_LAYER → Branch 6 Final Report / Branch 9 UI |
| `services/big_down_tail_warning.py` | NOT_EXCLUSION_LAYER → Branch 6 Final Report |
| `services/exclusion_reliability_review.py` | NOT_EXCLUSION_LAYER → Branch 7 Review & Learning |
| `services/consistency_layer.py` | NOT_EXCLUSION_LAYER → Branch 6 Final Report |

> **重申**：这 6 个模块**全部不**属于 Branch 4 Exclusion 主路径。详细
> 判断见 §7。

### 6.3 `services/projection_chain_contract.excluded_state_from_result`（边界 helper）

| 维度 | 说明 |
|---|---|
| 性质 | Exclusion 输出之后的 schema adapter；把 `triggered_rule` → 中文 state |
| 为什么算 EXCLUSION_ADAPTER_HELPER（不是 CORE）| 不是主入口；是从 exclusion_layer 输出向下游（confidence / log_store / final_decision）传递 schema 的 adapter |
| 目标职责 | 在 standard schema 没落地之前，作为 interim alias adapter；与 17B PR-C 抽 peer_alignment 的体例不同——这个 helper 不属 Feature Layer，属 Exclusion 输出 adapter |
| 后续实现任务 | §14 PR-EXCL-3：triggered_rule → triggered_rules + excluded_states migration 完成后，该 helper 可标 deprecated（`triggered_rules` list 中已含 standard 中文 state） |
| 当前禁止动作 | 不在 17H 改名；不在 17H 删除 |

---

## 7. CONTRADICTION / WARNING / RELIABILITY 模块归属

> **本节给出 6 个 mixed / cross-layer 模块的归属判断**；具体处置由对应
> 层 Plan（17J / 17K / 17L / 17M）+ 18A+ PR 综合决定，**不在 17H 执行**。

### 7.1 `services/anti_false_exclusion_audit.py`

| 维度 | 判断 |
|---|---|
| 当前性质 | **offline audit**：接受"已决定的硬否定"作为输入 → 输出 `{hard_excluded, soft_excluded, blocked_by_audit}`；4 个 auditor + 阈值；docstring 显式 "does not predict 大涨 and does not modify any production prediction or exclusion rule" |
| 是否属 Exclusion Layer 主路径 | ❌ **否**——它**不**参与当次 exclusion 决策；它是对**已**决定的 exclusion 做 offline 复盘 |
| 应迁到 | Branch 7 Review & Learning（事后审核）/ Branch 8 Evaluation（reliability gate metrics） |
| 17H 立即动作 | 无；声明非 Exclusion 主路径 |
| 17H 推荐 | 17K Review Plan + 17L Evaluation Plan 共同决定归属（很可能归 Review；Evaluation 引用其 metric） |

### 7.2 `services/anti_false_exclusion_dashboard.py`

| 维度 | 判断 |
|---|---|
| 当前性质 | **read-only aggregate dashboard**：6 项 hard gate 状态 + soft metadata baseline；SELECT-only；不写 DB |
| 是否属 Exclusion Layer 主路径 | ❌ **否**——它是 evaluation / dashboard 视图 |
| 应迁到 | Branch 8 Evaluation（reliability dashboard）/ Branch 9 UI（17M 决定渲染） |
| 17H 立即动作 | 无 |
| 17H 推荐 | 17L Evaluation Plan / 17M UI Plan 决定 |

### 7.3 `services/big_up_contradiction_card.py`

| 维度 | 判断 |
|---|---|
| 当前性质 | Task 085 **read-only presentation layer**；调 `audit_big_up_exclusion` + 翻译为中文 UI warning；docstring 显式 "lives in services/ not ui/ because the streamlit renderer is a 30-line wrapper" |
| 是否属 Exclusion Layer 主路径 | ❌ **否**——它是 display / UI logic for already-decided exclusion |
| 应迁到 | Branch 6 Final Report（display warning text）+ Branch 9 UI（renderer） |
| 17H 立即动作 | 无 |
| 17H 推荐 | 17J Final Report / 17M UI 共同决定 |

### 7.4 `services/big_down_tail_warning.py`

| 维度 | 判断 |
|---|---|
| 当前性质 | pure logic：tail compression / strong warning / downgrade detection；输出 strong_warning / downgrade flags；不调外部模块 |
| 是否属 Exclusion Layer 主路径 | ❌ **否**——是对历史已发生数据的"尾部压缩 / 强警告"判断；输出是 display flag，不参与当次 exclusion 决策 |
| 应迁到 | Branch 6 Final Report（display warning） |
| 17H 立即动作 | 无 |
| 17H 推荐 | 17J Final Report Plan 决定 |

### 7.5 `services/exclusion_reliability_review.py`

| 维度 | 判断 |
|---|---|
| 当前性质 | 综合 big_up_contradiction_card + big_down_tail_warning + 历史 row → reliability item；用于 UI / scripts；性质是"对已发生 exclusion 的可靠性审计" |
| 是否属 Exclusion Layer 主路径 | ❌ **否**——是事后复盘 |
| 应迁到 | Branch 7 Review & Learning（reliability review = review record / lesson 派生） |
| 17H 立即动作 | 无 |
| 17H 推荐 | 17K Review Plan 决定 |

### 7.6 `services/consistency_layer.py`

| 维度 | 判断 |
|---|---|
| 当前性质 | internal consistency checks across projection / exclusion / **confidence** layers；docstring "checks whether existing layer outputs agree with each other" |
| 是否属 Exclusion Layer 主路径 | ❌ **否**——它**读** projection_result / exclusion_result / confidence_result（cross-system）；属于 Final Report aggregator 之前的 consistency check |
| 应迁到 | Branch 6 Final Report（aggregation 之前的 consistency check） |
| 17H 立即动作 | 无；与 17F §6.8 / 17G §16.4 / 16I §10.4 一致（"不合并 consistency_layer"） |
| 17H 推荐 | 17J Final Report Plan 决定（很可能保留为 LEGACY_ACTIVE_DEPENDENCY 直到 architecture_orchestrator 接管） |

### 7.7 总结：6 个模块都不属 Exclusion Layer 主路径

> 全部归 Branch 6 Final Report / Branch 7 Review / Branch 8 Evaluation /
> Branch 9 UI 之一。17H **不**改任何模块；**不**打开 marker PR；**不**强制
> 收敛模块归属。

---

## 8. Exclusion Result 标准化规则

### 8.1 顶层结构（草案 `exclusion_system_result.v1`，与 07B §9 / 1.0 §8 Branch 4 一致）

```
{
    "schema_version": "exclusion_system_result.v1",  # 草案；正式入注由 PR-EXCL-1 决定
    "kind": "exclusion_layer",                        # 当前 exclusion_layer 已输出此字段（"excluded" / "action"，但未输出 "kind"）
    "symbol": "AVGO",                                 # uppercase（17B PR-C 之后从 normalized 中继承）

    # Standard schema fields (草案；与 07B §9 一致；当前 exclusion_layer 未输出，§14 PR-EXCL-2 落地)
    "most_unlikely_state": "...",                     # 五状态之一（"大涨" / "小涨" / "震荡" / "小跌" / "大跌"）；当 action="allow" 时为 None
    "ranked_unlikely_states": [...],                  # 按 impossibility 排序的 list
    "state_impossibility_scores": {...},              # 五状态完整 impossibility 分布
    "primary_exclusion_reasoning": [...],             # 排除核心理由
    "rare_event_evidence": [...],                     # 历史 rare-event 证据
    "historical_non_occurrence_summary": {...},       # 历史样本中"最少发生"的状态
    "peer_non_confirmation_summary": {...},           # peer 不确认信号汇总（来自 peer_alignment）
    "key_exclusion_signals": [...],                   # 支持本次排除的关键信号
    "key_counter_signals": [...],                     # 反向 / 不确定信号
    "uncertainty_notes": [...],                       # sample 不足 / regime 边界 / 校准缺失等
    "raw_evidence_refs": [...],                       # historical / peer / regime 引用 keys
    "false_exclusion_risk": "low" | "medium" | "high", # 自我风险标注（详见 §10）
    "triggered_rules": [...],                         # 触发规则 list（new schema；元素如 ["exclude_big_up"]）

    # Interim schema fields (当前 exclusion_layer 已输出；保留作 alias)
    "excluded": True/False,                           # 当前 interim
    "action": "exclude" | "allow",                    # 当前 interim
    "triggered_rule": "exclude_big_up" | "exclude_big_down" | None,  # interim single；新代码读 triggered_rules
    "excluded_states": [...],                         # 五状态中文标签 list；与 triggered_rules 协同（详见 §11）

    # Common fields
    "summary": "...",                                 # 当前 exclusion_layer 已输出
    "reasons": [...],                                 # 当前 exclusion_layer 已输出（草案合并到 primary_exclusion_reasoning）
    "warnings": [...],                                # fallback / 降级 / 缺失原因
    "peer_alignment": {...},                          # 来自 Branch 2 Feature Layer（17B PR-C），passthrough 展示
    "feature_snapshot": {...},                        # pos20 / vol_ratio20 / shadow / ret1-5

    "non_mutation_confirmations": {                   # 与 07D §11 体例一致；Exclusion 自身只声明
        "exclusion_did_not_read_projection": True,    # 07B §3.2 锁
        "exclusion_did_not_read_confidence": True,
        "exclusion_did_not_read_final_report": True,
        "exclusion_did_not_read_future_outcome": True,
    },
}
```

### 8.2 字段最小要求

| 字段 | 类型 | 备注 |
|---|---|---|
| `schema_version` | str | `"exclusion_system_result.v1"`（PR-EXCL-1 落地后） |
| `kind` | str | 当前 exclusion_layer 未输出该字段；建议加 `"exclusion_layer"` 或 `"exclusion_system_result"` |
| `symbol` | str | uppercase（当前 exclusion_layer 在 normalized 内含；输出顶层未含——PR-EXCL-2 加） |
| `most_unlikely_state` | str \| None | 五状态之一；当 `action = "allow"` 时为 `None` |
| `ranked_unlikely_states` | list[dict] | `[{"state": ..., "impossibility": ...}, ...]`；按 impossibility desc 排序 |
| `state_impossibility_scores` | dict[str, float] | 五状态完整 impossibility 分布；不要求 sum=1.0（与 projection probability 不同） |
| `triggered_rules` | list[str] | new schema；元素如 `["exclude_big_up"]` / `[]`（empty when action=allow） |
| `excluded_states` | list[str] | 五状态中文标签 list；当前 interim alias；与 `most_unlikely_state` 协同 |
| `triggered_rule` | str \| None | interim single；保留作 alias |
| `false_exclusion_risk` | str | `"low"` / `"medium"` / `"high"`；详见 §10 |
| `peer_alignment` | dict | 17B PR-C 输出（passthrough 展示） |
| `feature_snapshot` | dict | feature_payload 的可读子集 |
| `non_mutation_confirmations` | dict | 4 项 boolean，全部 `True` |

### 8.3 缺失语义（与 17F §8.3 / 17G §8.3 一致）

- 缺失字段一律用 `null` / `None`，**不**用 `0`
- `state_impossibility_scores` 中缺失状态用 `0.0`（与 projection
  state_probabilities 体例不同——这里 0.0 表示"完全不排除"，不是缺失）
- `warnings` 必须列出所有降级 / fallback 触发原因
- `action = "allow"` 时 `most_unlikely_state` / `triggered_rules` /
  `excluded_states` 都为 `None` / `[]`，**不**强制 fallback 到某个状态

### 8.4 不允许的字段（与 §4 / 07B §3.2 一致）

- ❌ `most_likely_state` / `predicted_top1` / `predicted_top2` /
  `state_probabilities` / `direction`（Projection 输出）
- ❌ `confidence_score` / `confidence_level` / `combined_confidence` /
  `agreement_status`（Confidence 输出）
- ❌ `combined_user_summary` / `agreement_or_conflict_section`（Final
  Report 输出）
- ❌ `simulated_trade` / `trading_action` / `buy` / `sell` / `hold`
- ❌ `hard_*` / `forced_*` / `required_*` / `_PROTECTION_LAYER_CONNECTED`
- ❌ `final_bias` / `final_confidence` / `final_projection`（legacy
  PredictResult 字段）
- ❌ `modified_*` / `corrected_*` / `*_mutation`

### 8.5 Exclusion Layer 不直接生成 standard_projection_payload.v1

- 与 17F §8.4 / 17G §8.5 / 17A standard payload 草案一致：Exclusion Layer
  **只**生成 `exclusion_result` 自身
- standard_projection_payload.v1 由未来 architecture_orchestrator（暂停；
  归 17J）组装

---

## 9. 与 standard_projection_payload.v1 的关系

### 9.1 17A / PR-B 已建立

- `services/standard_projection_payload.py` 已 in main（17A commit `9c779f8`）
- 含 `STANDARD_PAYLOAD_SECTIONS`（9 顶层 key）+ `validate_standard_projection_payload`
  纯函数 validator
- 当前**未接入** active path（与 16I §6 / 17F §8.4 / 17G §9.1 一致）

### 9.2 Exclusion Layer 只填充 exclusion_result section

- Exclusion Layer 输出符合 §8.1 草案的 `exclusion_result`
- architecture_orchestrator（未来）把 exclusion_result 放入 standard payload
  的 `exclusion_result` section

### 9.3 Exclusion Layer 不负责其它 section

- ❌ 不写 `metadata`（由 architecture_orchestrator 写）
- ❌ 不写 `feature_payload`（属 Branch 2 Feature Layer，17F §8）
- ❌ 不写 `projection_result`（属 Branch 3 Projection，17G §8）
- ❌ 不写 `confidence_result`（属 Branch 5 Confidence，17I 决定）
- ❌ 不写 `final_report`（属 Branch 6 Final Report，17J 决定）
- ❌ 不写 `review_stub` / `evaluation_stub`（17K / 17L 决定）
- ❌ 不写 `compatibility_metadata`（由 architecture_orchestrator 写）

### 9.4 standard payload 草案对 Exclusion 的约束

- standard_projection_payload validator 在 17A / PR-B 实现中要求
  `exclusion_result` section 必须存在
- Exclusion Layer 的输出必须能通过该 validator 的 shape check
- Exclusion Layer **不**需要在自身实现中调用 validator（validator 由
  architecture_orchestrator 在组装时调）

---

## 10. false_exclusion_risk 规则

### 10.1 性质：Exclusion Layer 自我风险标注

- `false_exclusion_risk` 是 Exclusion Layer **对自身判断的可靠性**的标注
- 三档：`"low"` / `"medium"` / `"high"`
- 当 action=`allow` 时，`false_exclusion_risk = "low"`（无 false exclusion 风险）
- 当 action=`exclude` 时，根据 evidence strength + sample size + counter
  signals 派生

### 10.2 不是 Confidence System 的总置信度

- `false_exclusion_risk` ≠ `confidence_level`
- `false_exclusion_risk` 只评价**本次排除是否容易误杀**
- Confidence System 单独评价 `combined_confidence`（含 projection +
  exclusion + agreement）
- 二者**不混淆**：07B / 07C 各自独立（与 1.0 §9 / 07E §9 一致）

### 10.3 不是 Review 事后评价

- `false_exclusion_risk` 是**当次推演时**的自我评估
- Review（Branch 7）是**事后**对已发生 exclusion 的复盘
- `services/exclusion_reliability_review.py` 的 reliability item 属 Review
  Layer（§7.5）

### 10.4 可以说明该排除是否容易误杀

- 例如：低样本量 + 弱 peer 不确认 + counter signal 多 → `high`（容易误杀）
- 例如：高样本量 + 强 peer 不确认 + 无 counter signal → `low`（不容易误杀）

### 10.5 不能读取真实未来结果

- `false_exclusion_risk` **不**读 future outcome（在线 inference 路径）
- Branch 7 Review 才能读已发生 outcome；Exclusion 不能（07B §3.2 / 1.0 §9）

### 10.6 不能读取 confidence_result

- 与 07B §3.2 / §10 一致

### 10.7 不能变成最终裁判

- `false_exclusion_risk` **不**改写 `most_unlikely_state` / `triggered_rules`
- 例如：`false_exclusion_risk = "high"` 不会让 exclusion 自动变 `allow`；
  exclusion 决策仍由 `_kill_risk` 阈值决定；`false_exclusion_risk` 只标注

### 10.8 17H 推荐处置

- KEEP；§14 PR-EXCL-4 标准化（low / medium / high 三档 + 派生规则）
- 不在 17H 改阈值 / 算法

---

## 11. triggered_rule / excluded_states 规则

### 11.1 当前 vs 目标 schema

| schema | 当前 | 目标 |
|---|---|---|
| `triggered_rule` | str \| None；values: `"exclude_big_up"` / `"exclude_big_down"` / `None` | **interim alias**（保留兼容） |
| `triggered_rules` | **未输出** | list[str]；values: `["exclude_big_up"]` / `["exclude_big_down"]` / `[]`（**new standard schema**） |
| `excluded_states` | **未输出** | list[str]；五状态中文标签：`["大涨"]` / `["大跌"]` / `[]`（**new standard schema**） |
| `most_unlikely_state` | **未输出** | str \| None；五状态中文标签（**new standard schema**） |

### 11.2 当前 schema 不齐导致 confidence_evaluator unknown

- `services/confidence_evaluator.py` 期望读 `exclusion_result.most_unlikely_state`
  / `exclusion_result.triggered_rule`
- 当前 exclusion_layer **未**输出 `most_unlikely_state`
- 结果：`agreement_status` 长期 `unknown`（与 1.0 §3 描述一致）
- 修复路径**不**在 17H：归 17I Confidence Layer Plan / PR-E（与 17D §9
  一致——PR-E 暂停归入 17I）

### 11.3 17H 决定的迁移方向（§14 PR-EXCL-3 落地）

- new schema 优先：`triggered_rules` (list) + `excluded_states` (中文 list)
  + `most_unlikely_state` (中文 single)
- interim alias 保留：`triggered_rule` (single)
- 显式映射：
  - `triggered_rule == "exclude_big_up"` → `triggered_rules = ["exclude_big_up"]`
    + `excluded_states = ["大涨"]` + `most_unlikely_state = "大涨"`
  - `triggered_rule == "exclude_big_down"` → `triggered_rules = ["exclude_big_down"]`
    + `excluded_states = ["大跌"]` + `most_unlikely_state = "大跌"`
  - `triggered_rule == None` (action=allow) → `triggered_rules = []` +
    `excluded_states = []` + `most_unlikely_state = None`

### 11.4 五状态中文标签

- `大涨` / `小涨` / `震荡` / `小跌` / `大跌`
- 与 `services/state_label.py` 阈值锁定一致（17F §6.3）
- exclusion_layer 当前**只**触发 `大涨` / `大跌` 两端；未来**可能**扩展到
  `小涨` / `小跌` / `震荡`，但本轮 17H 不扩

### 11.5 不应让 Confidence 层长期依赖 triggered_rule

- 17I 应直接读 `most_unlikely_state` / `triggered_rules`
- 短期 17I 可同时读 interim `triggered_rule` 作 fallback；但**不**应作为
  长期方案
- `services/projection_chain_contract.excluded_state_from_result` 是当前
  从 `triggered_rule` 派生中文 state 的 adapter；§14 PR-EXCL-3 完成后该
  helper 可标 deprecated

---

## 12. 与 Projection / Confidence 的交接

### 12.1 数据流方向（与 1.0 §9 / 17F §15 / 17G §15 一致）

```
Data Layer
    │
    ▼
Feature Layer  ──►  feature_payload
                          │
                          │ （并行读，互相不读）
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
   Branch 3            Branch 4          Branch 5
   Projection          Exclusion         Confidence
   最可能              最不可能          只评价二者
                       ──►exclusion_result
        │                 │                 │
        └────────┬────────┴────────┬────────┘
                 ▼                 ▼
           Branch 6 Final Report Layer
            （仅 aggregate / 不 mutate）
```

### 12.2 Feature Layer 输出 feature_payload

- 与 17F §8 一致

### 12.3 Projection 读 feature_payload，输出 projection_result

- 与 17G §3.1 / §8 一致

### 12.4 Exclusion 也读 feature_payload，输出 exclusion_result

- 与 §3.1 / §8 一致
- **不**反向 import Projection 业务模块
- **不**读 Projection 输出（07B §3.2 / §10）

### 12.5 Projection 不读 Exclusion / Exclusion 不读 Projection

- 与 07A §3.2 / 07B §3.2 / 17C PR-D 一致

### 12.6 Confidence 读 projection_result + exclusion_result + feature_payload

- 与 07C §3.1 一致
- Confidence**只读** exclusion_result（不改写）；与 07C §5 / §11 一致
- Confidence 期望读 `exclusion_result.most_unlikely_state` /
  `exclusion_result.triggered_rules`（new schema）；当前读 `triggered_rule`
  + `excluded_state` adapter（interim）；归 17I 解决（§11.2）

### 12.7 Final Report 汇总，不改 exclusion_result

- 与 07D §5 / §6 / §7 一致
- Final Report 在 `non_mutation_confirmations` 中显式声明未改 exclusion

---

## 13. Exclusion Layer 测试策略

后续 Exclusion Layer 实现 PR 必须满足以下测试要求：

### 13.1 no projection_result input tests

- `run_exclusion_layer` / `exclude_big_up` / `exclude_big_down` 显式不
  接受 `projection_result` 参数
- AST-level grep：`services/exclusion_layer.py` source 中**不**出现
  `projection_result` 作为变量名 / 参数名（除已废弃 docstring 描述外）
- 与 17C PR-D 体例对称（projection 不读 exclusion）

### 13.2 no confidence_result input tests

- Exclusion Layer 任一函数不接收 `confidence_result`
- AST-level grep：`services/exclusion_layer.py` source 中**不**出现
  `confidence_result`

### 13.3 no final_report input tests

- 同上，扩展到 `final_report` / `final_decision` / `combined_user_summary`

### 13.4 excluded_states shape tests

- `excluded_states` 是 list[str]
- 元素 ∈ 五状态中文标签集合 `{"大涨", "小涨", "震荡", "小跌", "大跌"}`
- `action = "allow"` → `excluded_states = []`
- `action = "exclude"` → `excluded_states` 长度 ≥ 1

### 13.5 triggered_rules list tests

- `triggered_rules` 是 list[str]
- 元素 ∈ `{"exclude_big_up", "exclude_big_down"}`（17H 阶段；未来可扩）
- 与 `excluded_states` 长度一致

### 13.6 triggered_rule interim alias tests

- `triggered_rule` (single) 与 `triggered_rules[0]` 一致（当 list 非空时）
- `action = "allow"` → `triggered_rule = None`
- 兼容现有 caller（confidence / projection_chain_contract /
  build_prediction_log_record）

### 13.7 false_exclusion_risk shape tests

- `false_exclusion_risk` ∈ `{"low", "medium", "high"}`
- `action = "allow"` → `false_exclusion_risk = "low"`

### 13.8 peer_alignment evidence tests

- 当 peer_alignment passthrough 进 exclusion_result 时，schema 与
  `services/peer_alignment.build_peer_alignment` 输出一致（17B PR-C）

### 13.9 no trading fields tests

- Exclusion Layer 任一模块输出 dict 字段集合中**不含**：
  - `simulated_trade` / `trading_action` / `buy` / `sell` / `hold` /
    `hard_*` / `forced_*` / `required_*` / `_PROTECTION_LAYER_CONNECTED`

### 13.10 no hard / forced / required fields tests

- 与 §13.9 重叠；显式扩展为 AST-level grep

### 13.11 non-mutation tests

- Exclusion Layer 任一函数**不修改**入参（feature_payload / peer_alignment）
- 输出 dict 与入参 dict 是不同 object（id 不同）

### 13.12 no LLM / no UI / no future outcome tests

- 不 import `anthropic` / `openai`
- 不 import `streamlit` / `ui.*`
- 不读取 future outcome（在线 inference 路径）
- anti-lookahead：feature_payload 中 `Date <= target_date` 假设由 Feature
  Layer 保证；Exclusion 不二次校验

### 13.13 most_unlikely_state schema tests（新增）

- `most_unlikely_state` ∈ `{"大涨", "小涨", "震荡", "小跌", "大跌", None}`
- 与 `excluded_states[0]` 一致（当 list 非空时）

### 13.14 baseline & regression

- 每个 PR-EXCL-* 必须以 Step 15 baseline 为起点（**3256 passed, 10
  skipped, 0 failed, 26 warnings, 94 subtests**）
- 新增测试数显式累加到 passed
- warnings / subtests 数变化必须**显式说明**

---

## 14. Exclusion Layer 后续实现 PR 候选

> **本节是 PR 候选清单，本轮 17H 不执行任一项**。最早 18A 由用户单独
> 决定执行哪个、何时执行、按什么顺序执行。

| 序号 | 名称 | 性质 | 目标 | 文件范围 | 测试 | 风险 | 是否必须先做 |
|---|---|---|---|---|---|---|---|
| **PR-EXCL-1** | exclusion_result contract validator helper | 代码（新增 helper） | 新增 `services/exclusion_result_contract.py`：定义 `EXCLUSION_RESULT_FIELDS` + `validate_exclusion_result(result) -> list[str]` 纯函数 validator；体例与 17A `standard_projection_payload.v1` / 17F PR-FEATURE-1 / 17G PR-PROJ-1 一致；**不**改 exclusion_layer 实现 | `services/exclusion_result_contract.py`（新增）+ `tests/test_exclusion_result_contract.py`（新增） | focused + full pytest | L | 不强制；推荐第一项 |
| **PR-EXCL-2** | exclusion_layer 输出 standard exclusion_result keys | 代码（**仅**加 alias + 新字段） | 在 `run_exclusion_layer` 输出**额外**加 `most_unlikely_state` / `triggered_rules` / `excluded_states` / `non_mutation_confirmations` 字段；保留 `triggered_rule` (single) / `action` / `excluded` / `summary` / `reasons` / `peer_alignment` / `feature_snapshot` 兼容 | `services/exclusion_layer.py`（仅加输出字段） | full pytest byte-stable except 新增字段；现有 boundary tests 全绿；confidence_evaluator 需要后续 17I PR-E 才能消费新字段 | L | 不强制；与 PR-EXCL-1 协同 |
| **PR-EXCL-3** | triggered_rule → triggered_rules / excluded_states migration | 代码（**仅** schema migration） | (a) PR-EXCL-2 之后的延续；(b) 把 `services/projection_chain_contract.excluded_state_from_result` 标 deprecated；新代码读 `triggered_rules[0]` / `most_unlikely_state` 优先 | exclusion_layer + projection_chain_contract（仅 docstring）+ tests | full pytest byte-stable；caller 仍可用 interim | L | 不强制 |
| **PR-EXCL-4** | false_exclusion_risk 标准化 | 代码（仅在 exclusion_layer 内派生） | 在 `run_exclusion_layer` / `exclude_big_up` / `exclude_big_down` 中显式派生 `false_exclusion_risk ∈ {low, medium, high}`；规则与 §10 一致；**不**改 `_kill_risk` / `_UPSIDE_EXCLUDE_THRESHOLD` 阈值 | `services/exclusion_layer.py` | focused + full pytest | L | 不强制 |
| **PR-EXCL-5** | anti_false_exclusion 模块归位 / freeze marker | 代码（**仅** docstring） | 给 `services/anti_false_exclusion_audit.py` / `services/anti_false_exclusion_dashboard.py` 加顶部 docstring marker：`NOT_EXCLUSION_LAYER —— belongs to Branch 7 Review (audit) / Branch 8 Evaluation (dashboard)`；与 17K / 17L 协同；**不**改逻辑 | 仅 docstring | full pytest byte-stable | L | 不强制；可推迟到 17K / 17L 之后 |
| **PR-EXCL-6** | contradiction / warning 模块迁出 Exclusion 标识 | 代码（**仅** docstring） | 给 `services/big_up_contradiction_card.py` / `services/big_down_tail_warning.py` / `services/exclusion_reliability_review.py` 加顶部 docstring marker：`NOT_EXCLUSION_LAYER —— belongs to Branch 6 Final Report (display) / Branch 7 Review (reliability)`；与 17J / 17K 协同；**不**改逻辑 | 仅 docstring | full pytest byte-stable | L | 不强制；可推迟到 17J / 17K 之后 |
| **PR-EXCL-7** | consistency_layer 迁出或归 Final Report 标识 | 代码（**仅** docstring） | 给 `services/consistency_layer.py` 加顶部 docstring marker：`NOT_EXCLUSION_LAYER —— belongs to Branch 6 Final Report aggregator pre-check`；与 17J 协同；**不**改逻辑 | 仅 docstring | full pytest byte-stable | L | 不强制；可推迟到 17J 之后 |
| **PR-EXCL-8** | exclusion caller boundary tests | 代码（仅 tests） | 给 V2 orchestrator + home_terminal_orchestrator + confidence_evaluator caller 加 `tests/test_exclusion_caller_boundary.py`：扫 source，断言**不**反向 import projection / confidence 之间错误方向；扩展 17B PR-C 已有 boundary tests | tests only | focused + full pytest | L | 不强制；可推迟到 17I 之后 |

### 14.1 候选 PR 之间的依赖

- PR-EXCL-1 → PR-EXCL-2：先有 contract validator，再让 exclusion_layer
  输出 standard keys
- PR-EXCL-2 → PR-EXCL-3：先有新字段，再做 migration
- PR-EXCL-2 → PR-EXCL-4：先有新输出字段集合，再加 false_exclusion_risk
- PR-EXCL-5 / PR-EXCL-6 / PR-EXCL-7：互不依赖；可任意顺序；都依赖对应
  下游层 Plan（17J / 17K / 17L）入 main 后才能最终决定 marker 内容
- PR-EXCL-8：可在 17I 之后或 PR-EXCL-2 之后启动
- 任何**代码** PR-EXCL-* 都依赖 **17H 已入 main**（前置条件）

### 14.2 候选 PR 都不能做的事

- ❌ 不改 `exclusion_layer` 内部计算逻辑（`_normalize_features` /
  `_kill_risk` / `_UPSIDE_EXCLUDE_THRESHOLD` / `_DOWNSIDE_EXCLUDE_THRESHOLD`
  / `exclude_big_up` / `exclude_big_down` 阈值）
- ❌ 不改 `anti_false_exclusion_audit` / `anti_false_exclusion_dashboard`
  / `big_up_contradiction_card` / `big_down_tail_warning` /
  `exclusion_reliability_review` / `consistency_layer` 的逻辑（仅 docstring）
- ❌ 不动 confidence_evaluator schema（17I 处理；与 PR-E 暂停一致）
- ❌ 不动 main_projection / final_decision（17G / 17J 处理）
- ❌ 不动 V2 orchestrator / home_terminal_orchestrator / projection_entrypoint
  业务逻辑
- ❌ 不切换默认 `run_predict` 路径
- ❌ 不引入 trading / hard / forced / required
- ❌ 不复活 `continuous_smoothing*` / `archive/legacy/root_stubs/*`
- ❌ 不修改 `.gitignore`
- ❌ 不处理 `avgo_agent.db`（含 backup）
- ❌ 不处理 handoff / logs / DB backup / `.claude/worktrees/`

---

## 15. 清场 / 隔离建议

> **本节按 16H 决策表 8 个标签给出 Exclusion Layer 范畴内的清场建议**。
> 本轮**不**执行任何清场动作。

### 15.1 KEEP（Exclusion Layer CORE）

- `services/exclusion_layer.py`

### 15.2 KEEP（Exclusion Adapter Helper）

- `services/projection_chain_contract.excluded_state_from_result`

### 15.3 NOT_EXCLUSION_LAYER（声明非 Exclusion；归其它层）

- `services/anti_false_exclusion_audit.py` → 17K Review / 17L Evaluation
- `services/anti_false_exclusion_dashboard.py` → 17L Evaluation / 17M UI
- `services/big_up_contradiction_card.py` → 17J Final Report / 17M UI
- `services/big_down_tail_warning.py` → 17J Final Report
- `services/exclusion_reliability_review.py` → 17K Review & Learning
- `services/consistency_layer.py` → 17J Final Report
- `services/projection_chain_contract.build_prediction_log_record` → 17J
  Final Report / log_store helper
- `services/final_decision.py`（exclusion display 部分）→ 17J Final Report
- `services/confidence_evaluator.py`（read exclusion_result 部分）→ 17I
  Confidence

### 15.4 MIGRATE_LATER

- §15.3 全部模块 → 对应层 Plan 接管
- 17H 阶段无主动 migration

### 15.5 ARCHIVE_IN_REPO

- 无 Exclusion Layer 范畴的 archive 候选（与 16H / 17E §15.5 / 17F §16.5 /
  17G §16.8 一致）

### 15.6 QUARANTINE

- 无 Exclusion Layer 范畴的 quarantine 候选（CORE 状态健康；adapter helper
  保留）

### 15.7 DEEP_AUDIT_REQUIRED

- 无 Exclusion Layer 范畴的 UNKNOWN（16G §11 列出的 10 项 UNKNOWN 中无
  Exclusion 范畴）

### 15.8 DELETE_NOW

- **空**（与 16H §13 / 17E §15.7 / 17F §16.7 / 17G §16.11 一致）

### 15.9 DELETE_LATER

- 无 Exclusion Layer 范畴的 delete 候选（17H 阶段；任何 archive 必须先
  全 caller 迁完）

### 15.10 MIGRATE_CALLER_FIRST

- 无（CORE_EXCLUSION 模块不是 Bridge）
- §15.3 模块的 caller 迁移由对应层 Plan（17I / 17J / 17K / 17L / 17M）决定

### 15.11 MOVE_OUTSIDE_REPO

- 无 Exclusion Layer 范畴

> **重申**：任何文件删除 / 移动 / archive 必须等 16H 规则 + 17D §11 + 用户
> 单独确认。17H 仅给出**建议**，**不**执行。

---

## 16. 不允许事项

**17H 起，Exclusion Layer 范畴内**严格禁止：

- ❌ 不改代码（无 `.py` 文件被修改；本轮 0 修改）
- ❌ 不跑数据
- ❌ 不跑 replay / 不跑 validation / 不跑 historical evaluation
- ❌ 不改 DB / 不改 DB schema
- ❌ 不迁 Confidence / Final Report / Review / Evaluation / UI（各层 Plan
  自负其责）
- ❌ 不接 trading / 不输出 buy / sell / hold / hard / forced / required
- ❌ 不进入 3R-5 / 3R-6（1.0 §12 / 16I §15 / 17D §11 / 17E §16 / 17F §17 /
  17G §17 / 本轮再次重申）
- ❌ 不启动任何代码 PR（PR-EXCL-* 候选要等 18A）
- ❌ 不修改 `.gitignore`
- ❌ 不处理 `avgo_agent.db`（含 backup）
- ❌ 不处理 handoff / logs / DB backup / `.claude/worktrees/`
- ❌ 不复活 `continuous_smoothing*` / `archive/legacy/root_stubs/*` /
  promotion 三模块
- ❌ 不污染 2026-01-01 之后 final holdout
- ❌ 不借 17H 顺手做 Data / Feature / Projection / Confidence / Final
  Report / Review / Evaluation / UI 范畴改动
- ❌ 不继续 PR-E confidence key 对齐（与 17D §9 一致）
- ❌ 不启动 UI / bridge / orchestrator 实现任务（与 17D §10 一致）
- ❌ 不默认迁移 `run_predict` 到 V2（hard rule 1.0 §6.4 / §12）
- ❌ 不打开 16I PR-G bridge marker（与 17D §10.1 一致）
- ❌ 不打开 16I PR-F architecture_orchestrator MVP（与 17D §10.3 一致）
- ❌ 不"根据 projection 选择否定对象"（07B §3.2 / §6 / §10 永久禁）
- ❌ 不在 17H 修复 confidence_evaluator schema 不齐（归 17I）

> 与 17D §11 / 17E §16 / 17F §17 / 17G §17 一致；本轮再次锁定。

---

## 17. 推荐下一步

> **首选**：**Step 17I：Confidence Layer Rebuild Plan**

理由（与 17D §12 / 17E §17 / 17F §18 / 17G §18 一致 + 17H 实战观察）：

- Exclusion Layer 计划（17H）已就位
- 数据流方向是 Data → Feature → {Projection, Exclusion, **Confidence**} →
  Final Report → ...（1.0 §9 / 16C §3）
- 按九分支编号顺序，下一层是 Confidence（Branch 5）
- **17I 的工作量中等偏大**：17I 必须接管
  - `services/confidence_evaluator.py`（含 schema 不齐 / agreement_status
    长期 unknown 问题；§11.2 / 1.0 §3 描述）
  - PR-E confidence key 对齐（与 17D §9 一致：暂停归 17I）
  - calibration_context 显式 fallback（16I §9.2）
  - confidence_result schema 与 07C §9 对齐
- 17I 入 main 之前，**不**允许在 Confidence Layer 范畴开任何代码 PR
- 17I 入 main 之后，PR-E 才有资格被讨论；且仍需 18A 单独审批

**不推荐**：

- 不推荐跳到 17J / 17K / 17L / 17M（必须先有 Confidence Plan）
- 不推荐借 17H / 17I 做代码改动（与 17D §11 一致）
- 不推荐重启 16I PR-E / PR-F / PR-G / PR-H（必须等对应层 Plan）
- 不推荐解锁 3R-5 / 3R-6（1.0 §12 7 项前提仍未全部满足）
- 不推荐立刻做 PR-EXCL-* 任一项（与 17H 协同更合算）

> **明确**：本轮 17H 推荐的下一步**只有一个候选**——17I Confidence Layer
> Rebuild Plan。

---

## 18. 严守边界

本轮 Step 17H **只**写 Exclusion Layer Rebuild Plan：

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
- ❌ 未启用任何 candidate / 未复活 `continuous_smoothing`
- ❌ 未触碰 RISK-1 / RISK-2 / RISK-3 / RISK-7 / RISK-8 / RISK-9 / RISK-10
- ❌ 未进入 3R-5 / 3R-6
- ❌ 未启动任何代码 PR（PR-EXCL-* 候选要等 18A）
- ❌ 未继续 PR-E confidence key 对齐
- ❌ 未启动 UI / bridge / orchestrator 实现任务
- ❌ 未做任何局部 patch
- ❌ 未 commit / 未 push（按本轮指令）

唯一新增文件：[tasks/record_17h_exclusion_layer_rebuild_plan.md](tasks/record_17h_exclusion_layer_rebuild_plan.md)（本文件）。

后续修改路径：任何对 §3 职责定义 / §4 禁止事项 / §5 inventory / §6
CORE_EXCLUSION / §7 contradiction / warning / reliability 归属 / §8
exclusion_result 标准化 / §9 与 standard payload 关系 / §10
false_exclusion_risk / §11 triggered_rule / excluded_states / §12 与
Projection / Confidence 交接 / §13 测试策略 / §14 PR 候选 / §15 清场建议 /
§16 禁止事项 / §17 下一步 的调整，都必须**显式更新本文件**；同时检查是否
需要同步更新 1.0 / 16C / 16D / 17D / 17E / 17F / 17G 与 17I（17I 入 main 后）。
