# 17G记录：Projection Layer Rebuild Plan

> 本记录是 **Step 17G：Projection Layer 重建计划**——九分支按层重建中
> 的**第三层**（Branch 3）。1.0 canonical / 16A blueprint / 16B inventory /
> 16C target dataflow & contract decision / 16D isolation & quarantine
> plan / 16E core chain refactor plan / 16F no-patching principle / 16G
> full module decomposition standup / 16H repository clearing decision
> table / 16I core chain rebuild execution plan / 17A PR-B standard
> payload skeleton / 17B PR-C peer_alignment 抽公共模块 / 17C PR-D
> main_projection 去 `exclusion_result` 形参 / 17D layer-by-layer rebuild
> governance / 17E Data Layer Rebuild Plan / 17F Feature Layer Rebuild
> Plan 已全部入 main（main 最新 commit `a787bf5`）。
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
> **本记录优先级**：与 17E / 17F / 17H ~ 17M 各层 Plan 同级；与 1.0 /
> 16A / 16C / 16D / 16F / 16I / 17D / 17E / 17F 协同。冲突仲裁路径与
> 1.0 §14 / 17D §13 一致：旧 records 若与 17G 在 Projection Layer 范畴
> 冲突，**以 17G 为准**。

---

## 1. Step 17G 目的

把九分支按层重建从 Feature Layer（17F）推进到**第三层（Projection Layer）
的具体重建计划**。

**本轮只回答**：

- Projection Layer 当前长什么样（模块 inventory + active path）
- Projection Layer 目标长什么样（保留 / 迁移 / 隔离 / 删除候选）
- Projection Layer 与上下游的边界（Feature ↑；Confidence / Final Report ↓；
  **不**读 Exclusion / Confidence / Final Report / future outcome）
- `projection_result` 标准化规则（与 1.0 §8 Branch 3 / 07A §9 一致）
- Projection Layer 后续可能的代码 PR 候选（**不**执行）
- 与 Feature / Exclusion / Confidence 的交接

**本轮不回答**：

- 不写 Exclusion / Confidence / Final Report / Review / Evaluation / UI
  计划（17H ~ 17M）
- 不开任何代码 PR（最早 18A）
- 不动 `avgo_agent.db`、`.gitignore`、handoff、logs、DB backup、worktrees
- 不继续 PR-E confidence key 对齐（与 17D §9 一致）
- 不启动 UI / bridge / orchestrator 实现任务（与 17D §10 一致）

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
| main 最新 commit | `a787bf5` |
| worktree 唯一 deliberate untracked | `.claude/handoffs/task_089_post_pr_cleanup.md` |
| 战略阶段 | 从 Feature Layer plan（17F）→ **Projection Layer plan（17G 本轮）** |
| 3R-5 / 3R-6 | ❌ 仍然不允许进入 |
| 第一个按层实现 PR（18A）| ❌ 仍未 |

**17D §6 PR 准入规则提醒**：

- 任何代码 PR 必须绑定九分支某一层 + 引用对应层 Plan §
- 17G 入 main 后，Projection Layer 范畴的 PR 才**有资格**被讨论
- 17G 本身**不**自动批准任何 PR

**层间依赖**：

- 17G 依赖 17E / 17F（已就位）
- 17G **不**依赖 17H ~ 17M（可独立写完）
- 17G 与 17J 的 orchestrator / bridge 决策**有重叠**——本文件给出 Projection
  Layer 视角；orchestration 终态由 17J 综合决定（与 17D §10.3 一致）

---

## 3. Projection Layer 职责定义

**Projection Layer（Branch 3）只回答一件事**：

> **"基于 feature_payload，回答'最可能发生什么'，输出 `projection_result`。"**

### 3.1 只做的事（与 1.0 §8 Branch 3 / 07A §3.1 一致）

- 读取 Feature Layer 输出的 `feature_payload`
- 基于 AVGO 自身 15d / 20d 结构（来自 feature_payload）+ 五状态历史样本
  + 历史相似结构 + peer signal + 成交量 / 位置 / 趋势 / 反转 + regime
  label，**派生**五状态概率分布
- 输出 `most_likely_state` / `ranked_states` / `state_probabilities`（或
  scores）/ `predicted_top1` / `predicted_top2`（当前 schema）
- 输出 `primary_reasoning` / `key_supporting_signals` / `key_risk_signals`
  / `uncertainty_notes` / `raw_evidence_refs`
- 读取 historical match / historical probability **作为 evidence / prior**
  （**不是**最终答案；详见 §10）
- 使用 `peer_alignment` **作为 feature evidence**（17B PR-C / 1.0 §8 Branch 2
  一致——Projection 从 Feature Layer 读，**不**反向 import Exclusion）
- 输出 `raw_score` / projection score（如有）
- 标注 `non_mutation_confirmations.projection_did_not_read_exclusion = True`
  （1.0 §6.7 / 07A §3.2 / 07D §11 一致）

### 3.2 不做的事（与 1.0 §8 Branch 3 / 07A §3.2 一致）

- ❌ 不否定某个状态（`most_unlikely_state` / `triggered_rule` 归 Branch 4
  Exclusion）
- ❌ 不做 confidence（`agreement_status` / `combined_confidence` 归
  Branch 5 Confidence）
- ❌ 不做 final report（`combined_user_summary` 归 Branch 6 Final Report）
- ❌ 不做 review / lesson（归 Branch 7）
- ❌ 不做 evaluation（accuracy / win-rate 归 Branch 8）
- ❌ 不做 UI 展示
- ❌ 不输出 trading action / hard / forced / required
- ❌ 不调用 LLM
- ❌ 不写 DB / 不改 DB schema
- ❌ 不直接运行 replay
- ❌ 不直接接 broker API

### 3.3 输入 / 输出（白名单）

**输入**（与 07A §3.1 / 17F §8 / §15 一致）：

- `feature_payload`（来自 Branch 2 Feature Layer，**唯一**输入入口）
- 五状态历史样本（通过 feature_payload 中的 historical match summary 携带，
  或 Projection 内部从 `coded_data/` 读取——属 Feature Layer ownership）
- offline calibration 权重 / 校准表（如有；属 Confidence System 资产，
  Projection 不直接消费）
- regime label（来自 feature_payload）

**输出**（草案 schema_version `projection_system_result.v1`，与 07A §9 一致）：

- `projection_result` dict（结构详见 §8）

**禁止输入**（与 07A §3.2 / 07A §10 / 17C PR-D 一致）：

- ❌ `exclusion_result`（17C PR-D 已物理保证：`build_main_projection_layer` /
  `run_main_projection_layer` 不接受该形参）
- ❌ `confidence_result`
- ❌ `final_report`
- ❌ `review_record`
- ❌ `evaluation_report`
- ❌ Future outcome（在线 inference 路径）
- ❌ 2026-01-01 之后 final holdout（在线 inference）
- ❌ Trading 输入 / broker / position state

---

## 4. Projection Layer 禁止事项

Projection Layer **永久禁止**输出 / 引入以下任一：

| 类别 | 禁止项 | 锚点 |
|---|---|---|
| 否定输出 | `most_unlikely_state` / `triggered_rule` / `false_exclusion_risk` / `ranked_unlikely_states` | 07A §3.2 / 07B §3.2 |
| 置信度输出 | `confidence_score` / `confidence_level` / `combined_confidence` / `agreement_status` | 07A §3.2 / 07C §5 |
| Final Report 字段 | `combined_user_summary` / `agreement_or_conflict_section` / `non_mutation_confirmations`（自身仅可标 `projection_did_not_read_*`，**不**写 confidence / exclusion / final 的非 mutation 标志）| 07A §3.2 / 07D §6 |
| 交易 / 强制 | `buy` / `sell` / `hold` / `simulated_trade` / `trading_action` / `hard_*` / `forced_*` / `required_*` | 12E X1..X5 / 1.0 §6 / §13 hard rule 1 |
| 系统输出回灌（input） | 读取 `exclusion_result` / `confidence_result` / `final_report` 字段后**用作 evidence / weight / mutation** | 1.0 §9 数据流方向 / 17C PR-D |
| 下游模块 import（active path） | import `services.exclusion_layer` / `services.confidence_evaluator` / `services.final_decision` / 任何 `predict.*` 反向调用 | 07A §10 / 17C PR-D |
| LLM 调用 | `anthropic` / `openai` / 任何文本生成 SDK | 1.0 §13 hard rule 1 / 5 |
| UI 调用 | `streamlit` / 任何 ui/ 模块 import | 1.0 §13 hard rule 3 |
| DB schema 改动 | `CREATE TABLE` / `ALTER TABLE` 在 17G 阶段不允许 | 17E §11 / 17F §11 / 17G §11 |
| 直接运行 replay | 调用 `scripts/run_contract_replay*` / `scripts/historical_replay_training*` | 17D §11 |
| Future outcome 回灌 | 在线 inference 路径中读取目标日之后的 close / outcome | 1.0 §9 / 07A §3.2 |
| 污染 2026 holdout | 在 in-sample projection 计算中读取 2026-01-01 之后的窗口 | 1.0 §5 rule 8 |
| 自动 V2 default migration | 默认把 `predict.run_predict` 切到 V2 主路径 | 1.0 §6.4 / §12 |

---

## 5. 当前 Projection Layer 模块 inventory

> **范围说明**：本表覆盖 (1) **核心 Projection 模块** (2) **Projection
> 相关 helper / preflight / renderer** (3) **Bridge / Orchestrator** (4)
> **Legacy（predict.py + V1 chain）** (5) **scanner 内 projection-like
> 输出**。standard_projection_payload skeleton（17A PR-B）属 INFRA / SCHEMA，
> 不在本表内（与 17F §5 处理一致）。

### 5.1 核心 / 候选 inventory

| module_path | current_role | current_status | target_role | keep / migrate / quarantine / delete | active_callers | risk | next_action |
|---|---|---|---|---|---|---|---|
| `services/main_projection_layer.py` | 五状态概率分布主入口；`build_main_projection_layer` / `run_main_projection_layer`；17C PR-D 已删 `exclusion_result` 形参 | KEEP_ACTIVE；docstring 显式 07A / 11A / 17C boundary contract | **CORE_PROJECTION**：Branch 3 主入口 | KEEP | `services/home_terminal_orchestrator:25`、`services/projection_orchestrator_v2`、tests | L | §6.1；§14 PR-PROJ-2 显式 standard schema 输出 keys |
| `services/historical_probability.py` | 历史概率 evidence builder；输出 up_rate / down_rate / probability / sample_count；docstring "historical validator" | KEEP_ACTIVE；纯函数；不读 system 输出 | **CORE_PROJECTION evidence**：Projection 内 evidence helper（不是主路径，是 prior） | KEEP | `services/projection_orchestrator_v2`、`predict.py`、tests | M | §6.2；§14 PR-PROJ-3 显式归位 + boundary tests |
| `services/primary_20day_analysis.py` | 输出 `direction` / `confidence` / `position_label` / `stage_label` / `volume_state` —— 0.x primary analysis（早期 Projection 形态）| KEEP_ACTIVE；与 V2 chain 紧耦合 | **LEGACY_PROJECTION_HELPER**：归 Projection Layer 但是早期 / legacy；与 main_projection_layer 行为重复 | MIGRATE_LATER（17G 接管，不立即拆） | `services/projection_orchestrator_v2`、tests | M | §6.3 / §12；§14 PR-PROJ-4 选 (a) merge into main_projection_layer (b) 标 LEGACY (c) archive |
| `services/projection_chain_contract.py`（其中 `least_likely_from_projection`）| 从 main_projection state_probabilities 派生 least-likely state | KEEP_ACTIVE | **PROJECTION_HELPER**（其它三个 helper 跨层；详见 17F §7.6） | KEEP（不动） | V2 chain；tests | L | §6.4 |
| `scanner.py` 的 `compute_scan_bias_and_confidence` / `scan_bias` / `scan_confidence` / `confirmation_state` | 从 RS / regime score 派生 `bullish / bearish / neutral` + `high / medium / low` | KEEP_ACTIVE；与 UI（app.py）紧耦合 | **LEGACY_PROJECTION_LIKE**：早期 projection-like 输出，**不**是 Branch 3 主入口；性质与 primary_20day_analysis 类似 | MIGRATE_LATER；17G 决定方向（详见 §11） | `app.py` UI；tests | **H** | §11；§14 PR-PROJ-5 freeze / rename / archive 三选一 |
| `services/projection_preflight.py` | stable advisory preflight package | KEEP_ACTIVE；docstring 显式 06 / 07A / 11D boundary | **PROJECTION_PREFLIGHT_HELPER** | KEEP | V2 chain；`projection_orchestrator_preflight`；tests | L | 17G 不动 |
| `services/projection_orchestrator_preflight.py` | orchestration-facing advisory block | KEEP_ACTIVE | **PROJECTION_PREFLIGHT_HELPER** | KEEP | `projection_orchestrator_v2`、tests | L | 17G 不动 |
| `services/projection_rule_preflight.py` | 把 memory / review reminders 包进 Step 0 | KEEP_ACTIVE | **PROJECTION_PREFLIGHT_HELPER** | KEEP | V2 chain；tests | L | 17G 不动 |
| `services/projection_memory_briefing.py` | projection-facing advisory briefing from experience memory | KEEP_ACTIVE | **PROJECTION_PREFLIGHT_HELPER**（experience memory → projection prior） | KEEP | V2 chain；tests | L | 17G 不动 |
| `services/projection_output_contract.py` | Step 1A 8-section pure-function validator | KEEP_ACTIVE；纯函数 | **INFRA / LEGACY_SCHEMA_VALIDATOR**（Step 1A 老契约；与 17A standard_projection_payload.v1 并存）| KEEP（不动；17A 之后由对应层 Plan 决定收敛） | tests；scripts | L | 17G 不动；与 17A 协同 |
| `services/projection_output_adapter.py` | legacy scan_result / research_result / predict_result → Step 1A 契约 dict | KEEP_ACTIVE；docstring "not yet wired"（16G UNKNOWN 之一）| **DEEP_AUDIT_REQUIRED**（16G UNKNOWN）；当前未接入 active path | KEEP（不动） | tests；scripts | M | §16.10；与 16G UNKNOWN 一致；本轮不动 |
| `services/projection_narrative_renderer.py` | 把 V2 raw 输出 render 成中文交易 narrative | KEEP_ACTIVE | **NOT_PROJECTION_LAYER**：归 Branch 6 Final Report / Branch 9 UI（17J / 17M 决定）| MIGRATE_LATER | `projection_entrypoint`；tests | L | 17G 声明非 Projection；17J / 17M 接管 |
| `services/projection_three_systems_renderer.py` | reshape V2 raw → 三系统视图 | KEEP_ACTIVE | **NOT_PROJECTION_LAYER**：归 Branch 6 Final Report（17J 决定）| MIGRATE_LATER | `projection_entrypoint`、predict.py、tests | L | 17G 声明非 Projection |
| `services/projection_review_closed_loop.py` | review closed-loop pipeline | KEEP_ACTIVE | **NOT_PROJECTION_LAYER**：归 Branch 7 Review & Learning（17K 决定）| MIGRATE_LATER | scripts；UI；tests | L | 17G 声明非 Projection |
| `services/consistency_layer.py` | internal consistency checks across projection v2 layers | KEEP_ACTIVE | **NOT_PROJECTION_LAYER**：跨 projection / exclusion / confidence；归 Branch 6 Final Report（17J 决定，与 17F §6.8 一致） | MIGRATE_LATER；与 16I §10.4 一致（"不合并 consistency_layer"）| V2 chain；tests | M | 17G 声明非 Projection；17J 接管 |

### 5.2 Bridge / Orchestrator inventory

| module_path | current_role | current_status | target_role | keep / migrate / quarantine / delete | active_callers | risk | next_action |
|---|---|---|---|---|---|---|---|
| `predict.py`（root） | LEGACY_COMPATIBILITY_WRAPPER；含 `build_primary_projection` / `apply_peer_adjustment` / `build_final_projection` / `run_predict` / `_summarize` / `_apply_briefing_caution` / `_apply_v2_legacy_adapter_overlay` | TEMP_MIGRATION_BRIDGE（13 个 bridge 之一；与 16D §6 / 16I §11 一致） | **TEMP_MIGRATION_BRIDGE**（**不**进 9 分支正式架构）；最终随 Bridge 退出条件满足而解散 | QUARANTINE（marker 已存在；不再扩展）；MIGRATE_CALLER_FIRST | UI tabs / scripts / log_store / `projection_orchestrator` V1 / `review_agent` / `contract_replay_writer` / 9+ 个 importer | **H** | §7.1；§14 PR-PROJ-7 不直接动；与 16I §11 marker 协同 |
| `services/projection_orchestrator.py`（V1）| 老 orchestrator；调 `predict.run_predict` + scanner + matcher + stats_reporter | TEMP_MIGRATION_BRIDGE / LEGACY | **TEMP_MIGRATION_BRIDGE**（**不**进 9 分支） | QUARANTINE；MIGRATE_CALLER_FIRST | `projection_orchestrator_v2` 内调；tests | **H** | §7.2 |
| `services/projection_orchestrator_v2.py` | V2 orchestrator；汇集 main_projection + exclusion + confidence + consistency + final_decision + historical_probability + primary_20day + peer_adjustment + projection_orchestrator V1 | KEEP_ACTIVE；当前**事实主路径**之一 | **LEGACY_ACTIVE_DEPENDENCY**（短期主路径；最终被 architecture_orchestrator 替代）| MIGRATE_LATER（17J 决定） | `projection_entrypoint`、`projection_v2_adapter`、`predict_legacy_v2_bridge`、`historical_replay_training`、tests | **H** | §7.3；与 16I §10 / 17F §7.7 一致 |
| `services/projection_entrypoint.py` | callable entrypoint；调 V2 + narrative renderer + three-systems renderer + v2_adapter | KEEP_ACTIVE；UI 主入口 | **LEGACY_ACTIVE_DEPENDENCY**（最终被 architecture_orchestrator 替代）| MIGRATE_LATER | `services/tool_router`、tests | M | §7.4 |
| `services/projection_v2_adapter.py` | legacy compat shell：V2 raw → legacy `projection_report` / `advisory` | KEEP_ACTIVE | **TEMP_MIGRATION_BRIDGE**（**不**进 9 分支）| QUARANTINE；MIGRATE_CALLER_FIRST | `projection_entrypoint`、tests | M | §7.5 |
| `services/predict_legacy_adapter.py` | V2 payload → predict.py legacy compat（X4-A）| TEMP_MIGRATION_BRIDGE | **TEMP_MIGRATION_BRIDGE** | QUARANTINE；MIGRATE_CALLER_FIRST | `predict_legacy_v2_bridge`；tests | M | §7.6 |
| `services/predict_legacy_v2_bridge.py` | offline / diagnostic bridge from V2 → legacy PredictResult（X4-C）| TEMP_MIGRATION_BRIDGE | **TEMP_MIGRATION_BRIDGE** | QUARANTINE；MIGRATE_CALLER_FIRST | scripts / tests | L | §7.7 |
| `services/predict_summary.py` | readable Chinese summary helpers for predict / projection results | KEEP_ACTIVE；与 13 个 bridge 之一（16I §11.2）| **NOT_PROJECTION_LAYER**：归 Branch 6 Final Report（17J 决定）| MIGRATE_LATER | predict.py / V2 chain / tests | L | 17G 声明非 Projection；17J 接管 |
| `services/home_terminal_orchestrator.py` | 主页 orchestration：compute_20d_features → run_exclusion_layer → build_main_projection_layer → build_consistency_layer → write_prediction_log → confidence | KEEP_ACTIVE；当前**事实主路径**之一（与 V2 链路并存）| **LEGACY_ACTIVE_DEPENDENCY**（最终由 architecture_orchestrator 替代）| MIGRATE_LATER（17J 决定） | UI（home_terminal tab）；tests | **H** | §7.8 |

### 5.3 关键说明

- **Projection Layer 当前唯一**真正符合 1.0 §8 Branch 3 / 07A 契约的入口
  是 `services/main_projection_layer.py`（17C PR-D 已物理保证不读 exclusion）。
- **`primary_20day_analysis.py` 是 0.x 时代的 primary analysis**，在 V2
  chain 中仍被调用；它**不**符合 07A §9 标准 schema（输出 `direction` /
  `confidence` 而非 `predicted_top1` / `state_probabilities`）。17G 决定
  归 LEGACY_PROJECTION_HELPER；17G 之后由对应 PR 决定 merge / freeze /
  archive。
- **`historical_probability.py` 是 evidence builder**，**不是**主入口；
  Projection 主路径把它当 prior。它的输出（up_rate / down_rate / sample_count）
  是给 main_projection 的 evidence；**不**是 Projection 的最终答案。
- **scanner.py 的 `scan_bias` / `scan_confidence` / `confirmation_state`
  是早期 projection-like 输出**（17F §7.1 / §12.4 已声明跨层）。17G 给出
  3 选 1 路线（§11）；17G **不**立即拆。
- **predict.py + V1/V2 orchestrator + entrypoint + adapter + bridge 是
  Bridge 群**（13 个 bridge / LEGACY_ACTIVE_DEPENDENCY 中的核心 6 个）。
  17G 仅声明归属；不动；marker / migration 由 17J + 18A+ PR 决定。
- **DELETE_NOW 集合为空**（与 16H §13 / 17E §15.7 / 17F §16.7 一致）。

---

## 6. CORE_PROJECTION 保留模块

> Projection Layer 的**核心保留模块**：以下 3 个 + 1 个 helper 是 17G
> 阶段无歧义归属 Branch 3 的 active asset。

### 6.1 `services/main_projection_layer.py`

| 维度 | 说明 |
|---|---|
| 为什么保留 | Branch 3 唯一**符合 07A 契约**的主入口；17C PR-D 已物理保证不读 exclusion；docstring 显式 06 / 07A / 11A / 17C boundary contract；输出 `predicted_top1` / `predicted_top2` / `state_probabilities` 五状态分布 |
| 目标职责 | (1) 接收 `current_20day_features`（feature_payload，未来 15d 也由该入口接收）+ `historical_match_result`（evidence）+ `peer_alignment`（feature evidence，17B PR-C 之后属 Branch 2）(2) 派生五状态分布 (3) 输出 `projection_result`（草案 schema_version `projection_system_result.v1`，详见 §8）|
| 是否需要改名 / 拆分 | ❌ 17G 不改名；不拆分 |
| 是否有跨层问题 | ❌ 无（17C PR-D 已物理保证）；docstring 已声明 boundary contract |
| 后续实现任务 | §14 PR-PROJ-1：projection_result contract validator helper；§14 PR-PROJ-2：输出 `most_likely_state` / `ranked_states`（standard schema 优先）+ 保留 `predicted_top1` / `predicted_top2` 作 interim alias |
| 当前禁止动作 | 不改 `_STATE_ORDER` / `_STATE_CENTERS` / `_FALLBACK_DISTRIBUTION` 阈值；不在 17G 改输出字段集 |

### 6.2 `services/historical_probability.py`

| 维度 | 说明 |
|---|---|
| 为什么保留 | Projection 的 historical evidence builder；纯函数；不读任何 system 输出；输出 up_rate / down_rate / probability / sample_count；含 sample_quality / impact 派生 |
| 目标职责 | 给 `main_projection_layer` 提供历史 prior（dominant_historical_outcome / sample_count / win_rate 类信息）；**不是**最终答案；**不**直接决定 final_report |
| 是否需要改名 / 拆分 | ❌ 17G 不改名；不拆分 |
| 是否有跨层问题 | ⚠️ 当前 V2 chain 把 historical_probability 输出**和** main_projection 输出**并行展示**（projection_v2_raw 含两段）；这是 V2 orchestration 的混合，不是 historical_probability 自身的问题 |
| 后续实现任务 | §14 PR-PROJ-3：boundary tests + docstring 显式声明 Projection evidence helper；不改逻辑 |
| 当前禁止动作 | 不改阈值；不读 exclusion_result / confidence_result / final_report；不输出 `most_unlikely_state` 类否定字段；不在 17G 改 schema |

### 6.3 `services/projection_chain_contract.least_likely_from_projection`

| 维度 | 说明 |
|---|---|
| 为什么保留 | 从 main_projection state_probabilities 派生 least-likely state；纯函数；与 main_projection 输出绑定 |
| 目标职责 | 把 main_projection 的 state_probabilities → 最低概率状态（**不**是 Exclusion 的 most_unlikely_state；命名易混淆但语义不同——这里是 projection 自己的 lowest-prob state，不涉及 Exclusion 否定逻辑） |
| 是否需要改名 / 拆分 | ⚠️ 17G 阶段不改名；命名歧义建议在 17G 之后某个 PR-PROJ 改为 `lowest_probability_state_from_projection` 或类似明确名称 |
| 是否有跨层问题 | ⚠️ 当前与 Exclusion 的 `most_unlikely_state` 命名混淆 |
| 后续实现任务 | §14 PR-PROJ-1 contract helper 中显式区分 `lowest_prob_state`（Projection 内部）vs `most_unlikely_state`（Exclusion 输出，归 Branch 4） |
| 当前禁止动作 | 不在 17G 改名；不在 17G 调用 Exclusion |

### 6.4 边界 helper（CORE_PROJECTION 部分）

以下是**部分** Projection Layer 模块（preflight / advisory），主体保留
但属于 evidence / preflight，不是主入口：

- `services/projection_preflight.py`（advisory preflight package）
- `services/projection_orchestrator_preflight.py`（orchestration-facing
  advisory）
- `services/projection_rule_preflight.py`（memory / review reminders →
  Step 0 advisory）
- `services/projection_memory_briefing.py`（experience memory advisory）

这 4 个 preflight helper 全部 **KEEP；17G 不动**；它们：
- 不读 system 输出
- 含 06 / 07A / 11D boundary contract docstring
- 是 V2 chain 的 preflight 步骤；属 Projection Layer 范畴

### 6.5 `primary_20day_analysis` 不在 CORE_PROJECTION

- 命名误导；行为是早期 projection / "第二个 main projection"
- 与 main_projection_layer 行为重复
- 17G 决定归 LEGACY_PROJECTION_HELPER（详见 §12）

---

## 7. LEGACY / BRIDGE 投影相关模块

> **本节给出 8 个 bridge / orchestrator 模块的归属判断**；具体处置由 17J
> Final Report Layer Plan + 18A+ PR 综合决定，**不在 17G 执行**。

### 7.1 `predict.py`（root）

| 维度 | 判断 |
|---|---|
| 性质 | **TEMP_MIGRATION_BRIDGE**（与 1.0 §10 / 16D §6 / 16I §11.2 一致；13 个 bridge 之一） |
| 当前承担 | 9+ 个 importer（UI tabs / scripts / log_store / `projection_orchestrator` V1 / `review_agent` / `contract_replay_writer` / `predict_legacy_v2_bridge` / tests）；含 `build_primary_projection` / `apply_peer_adjustment` / `build_final_projection` / `run_predict` / `_summarize` / `_apply_briefing_caution` / `_apply_v2_legacy_adapter_overlay` |
| 是否进 9 分支正式架构 | ❌ **否**（与 1.0 §10 一致：Bridge 不属正式架构图） |
| 17G 立即动作 | **无**；marker（PR-G in 16I §11）已暂停（17D §10.1）；17G 不打开 PR-G |
| 退出条件（与 16D §6 / 16I §11 一致）| (1) UI 全部读新 final_report schema (2) replay 全部读新 evaluation schema (3) tests 不再依赖旧 `PredictResult` (4) `run_predict` 不再作为主入口 (5) legacy adapter / bridge 在 active path 中无 import (6) `services/projection_orchestrator.py` 不再被新链路依赖 |
| 17G 推荐 | 声明 TEMP_MIGRATION_BRIDGE；marker 由 17J 决定（与 17D §10.3 一致） |

### 7.2 `services/projection_orchestrator.py`（V1）

| 维度 | 判断 |
|---|---|
| 性质 | **TEMP_MIGRATION_BRIDGE**；调 `predict.run_predict` + scanner + matcher |
| 当前承担 | V2 orchestrator 内部调用（`projection_orchestrator_v2:18` `from services.projection_orchestrator import build_projection_orchestrator_result`）；UI 间接依赖 |
| 是否进 9 分支正式架构 | ❌ **否** |
| 17G 立即动作 | 无 |
| 17G 推荐 | 声明 TEMP_MIGRATION_BRIDGE；MIGRATE_CALLER_FIRST（V2 caller 迁完才能 archive） |

### 7.3 `services/projection_orchestrator_v2.py`

| 维度 | 判断 |
|---|---|
| 性质 | **LEGACY_ACTIVE_DEPENDENCY**；当前**事实主路径**之一；与 home_terminal_orchestrator 并存 |
| 当前承担 | 汇集 main_projection + exclusion + confidence + consistency + final_decision + historical_probability + primary_20day + peer_adjustment + projection_orchestrator V1；输出 V2 raw payload |
| 是否进 9 分支正式架构 | ❌ **否**（最终由 architecture_orchestrator 替代；与 16I §10 / 16C §4 一致） |
| 17G 立即动作 | 无（与 17D §10.3 一致：architecture_orchestrator 暂停） |
| 17G 推荐 | 声明 LEGACY_ACTIVE_DEPENDENCY；保持运行；不扩展；不接 calibration table |

### 7.4 `services/projection_entrypoint.py`

| 维度 | 判断 |
|---|---|
| 性质 | **LEGACY_ACTIVE_DEPENDENCY**；UI / tool_router 主入口 |
| 当前承担 | 调 V2 + narrative renderer + three-systems renderer + v2_adapter；返回 degraded payload on failure |
| 是否进 9 分支正式架构 | ❌ **否**（最终由 architecture_orchestrator 替代）|
| 17G 推荐 | 声明 LEGACY_ACTIVE_DEPENDENCY；保持运行 |

### 7.5 `services/projection_v2_adapter.py`

| 维度 | 判断 |
|---|---|
| 性质 | **TEMP_MIGRATION_BRIDGE**：V2 raw → legacy `projection_report` / `advisory` 兼容 shell |
| 是否进 9 分支正式架构 | ❌ **否** |
| 17G 推荐 | 声明 TEMP_MIGRATION_BRIDGE |

### 7.6 `services/predict_legacy_adapter.py`

| 维度 | 判断 |
|---|---|
| 性质 | **TEMP_MIGRATION_BRIDGE**（X4-A）：V2 payload → predict.py legacy compat |
| 是否进 9 分支正式架构 | ❌ **否** |
| 17G 推荐 | 声明 TEMP_MIGRATION_BRIDGE |

### 7.7 `services/predict_legacy_v2_bridge.py`

| 维度 | 判断 |
|---|---|
| 性质 | **TEMP_MIGRATION_BRIDGE**（X4-C）：offline / diagnostic bridge |
| 是否进 9 分支正式架构 | ❌ **否** |
| 17G 推荐 | 声明 TEMP_MIGRATION_BRIDGE |

### 7.8 `services/home_terminal_orchestrator.py`

| 维度 | 判断 |
|---|---|
| 性质 | **LEGACY_ACTIVE_DEPENDENCY**：主页链路 orchestration（与 V2 链并存 → 0.x 时代两路） |
| 当前承担 | compute_20d_features → run_exclusion_layer → build_main_projection_layer → build_consistency_layer → write_prediction_log → confidence；**不**用 V2 chain |
| 是否进 9 分支正式架构 | ❌ **否**（最终由 architecture_orchestrator 替代）|
| 17G 推荐 | 声明 LEGACY_ACTIVE_DEPENDENCY；与 V2 chain 收敛由 17J 决定 |

### 7.9 总结：8 个 bridge / orchestrator 都不进 9 分支正式架构

> 全部归 TEMP_MIGRATION_BRIDGE 或 LEGACY_ACTIVE_DEPENDENCY；未来由
> architecture_orchestrator（暂停；归 17J）+ 各层 Plan 协同决定迁移路径。
> 17G **不**改任何 bridge；**不**打开 marker PR；**不**强制收敛 V2 与
> home_terminal 两路。

---

## 8. Projection Result 标准化规则

### 8.1 顶层结构（草案 `projection_system_result.v1`，与 07A §9 / 1.0 §8 Branch 3 一致）

```
{
    "schema_version": "projection_system_result.v1",  # 草案；正式入注由 PR-PROJ-1 决定
    "kind": "main_projection_layer",                   # 当前 main_projection 已输出此字段
    "symbol": "AVGO",                                  # uppercase
    "ready": True/False,                               # feature 不足时 False + 中性 fallback
    "most_likely_state": "...",                        # 五状态之一（standard schema）
    "ranked_states": [...],                            # 按概率排序的列表（standard schema）
    "state_probabilities": {...},                      # 五状态完整分布（含 sum ≈ 1.0）
    "predicted_top1": {"state": "...", "probability": ...},  # interim alias（与 ranked_states[0] 等价）
    "predicted_top2": {"state": "...", "probability": ...},  # interim alias（与 ranked_states[1] 等价）
    "primary_reasoning": [...],                        # 推演核心理由（current_features / peer / historical）
    "key_supporting_signals": [...],                   # 支持当前 top1 的信号
    "key_risk_signals": [...],                         # 反向 / 不确定信号
    "uncertainty_notes": [...],                        # sample 不足 / regime 边界 / 校准缺失等
    "raw_evidence_refs": [...],                        # historical match / peer / regime 引用 keys
    "rationale": [...],                                # 当前 main_projection 已输出（草案合并到 primary_reasoning）
    "warnings": [...],                                 # 当前 main_projection 已输出
    "peer_alignment": {...},                           # 来自 Branch 2 Feature Layer（17B PR-C），passthrough 展示
    "feature_snapshot": {...},                         # pos20 / vol_ratio20 / shadow / ret1-10
    "non_mutation_confirmations": {                    # 与 07D §11 体例一致；Projection 自身只声明
        "projection_did_not_read_exclusion": True,     # 17C PR-D 已物理保证
        "projection_did_not_read_confidence": True,
        "projection_did_not_read_final_report": True,
        "projection_did_not_read_future_outcome": True,
    },
}
```

### 8.2 字段最小要求

| 字段 | 类型 | 备注 |
|---|---|---|
| `schema_version` | str | `"projection_system_result.v1"`（PR-PROJ-1 落地后） |
| `kind` | str | 当前 `"main_projection_layer"`；正式可改 `"projection_system_result"` |
| `symbol` | str | uppercase |
| `ready` | bool | feature 不足 → `False` + fallback distribution |
| `most_likely_state` | str | 五状态之一；当前由 `predicted_top1.state` 派生（PR-PROJ-2 显式输出 standard key） |
| `ranked_states` | list[dict] | `[{"state": ..., "probability": ...}, ...]`；按 probability desc，state 次序作为 tie-break |
| `state_probabilities` | dict[str, float] | 五状态完整分布；sum ≈ 1.0；缺失状态用 0.0 |
| `predicted_top1/top2` | dict | interim alias；不删除（V2 / home_terminal / tests 仍依赖） |
| `primary_reasoning` | list[str] | 与 07A §9 一致 |
| `key_supporting_signals` | list[str] | 与 07A §9 一致 |
| `key_risk_signals` | list[str] | 与 07A §9 一致 |
| `uncertainty_notes` | list[str] | 与 07A §9 一致 |
| `raw_evidence_refs` | list[str] | historical / peer / regime 引用 |
| `peer_alignment` | dict | 17B PR-C 输出（passthrough 展示） |
| `feature_snapshot` | dict | feature_payload 的可读子集 |
| `non_mutation_confirmations` | dict | 4 项 boolean，全部 `True`（17C PR-D 后物理保证）|

### 8.3 缺失语义（与 07A §9 / 17F §8.3 一致）

- 缺失字段一律用 `null` / `None` / `0.0`（state_probabilities 中），**不**用 `0` 表示缺失
- `warnings` 必须列出所有降级 / fallback 触发原因
- `ready = False` 时 `state_probabilities` 必须给出 `_FALLBACK_DISTRIBUTION`
  + `warnings` 含明确 reason

### 8.4 不允许的字段（与 §4 / 07A §3.2 一致）

- ❌ `most_unlikely_state` / `ranked_unlikely_states` / `triggered_rule` /
  `false_exclusion_risk`
- ❌ `confidence_score` / `confidence_level` / `combined_confidence` /
  `agreement_status`
- ❌ `combined_user_summary` / `agreement_or_conflict_section`
- ❌ `simulated_trade` / `trading_action` / `buy` / `sell` / `hold`
- ❌ `hard_*` / `forced_*` / `required_*` / `_PROTECTION_LAYER_CONNECTED`
- ❌ `final_bias` / `final_confidence` / `final_projection`（legacy
  PredictResult 字段）
- ❌ `modified_*` / `corrected_*` / `*_mutation`

### 8.5 Projection 不直接生成 standard_projection_payload.v1

- 与 17F §8.4 / 17A standard payload 草案一致：Projection Layer **只**生成
  `projection_result` 自身
- standard_projection_payload.v1 由未来 architecture_orchestrator（暂停；
  归 17J）组装

---

## 9. 与 standard_projection_payload.v1 的关系

### 9.1 17A / PR-B 已建立

- `services/standard_projection_payload.py` 已 in main（17A commit `9c779f8`）
- 含 `STANDARD_PAYLOAD_SECTIONS`（9 顶层 key）+ `validate_standard_projection_payload`
  纯函数 validator
- 当前**未接入** active path（与 16I §6 / 17F §8.4 一致）

### 9.2 Projection Layer 只填充 projection_result section

- Projection Layer 输出符合 §8.1 草案的 `projection_result`
- architecture_orchestrator（未来）把 projection_result 放入 standard
  payload 的 `projection_result` section

### 9.3 Projection Layer 不负责其它 section

- ❌ 不写 `metadata`（由 architecture_orchestrator 写）
- ❌ 不写 `feature_payload`（属 Branch 2 Feature Layer，17F §8）
- ❌ 不写 `exclusion_result`（属 Branch 4 Exclusion，17H 决定）
- ❌ 不写 `confidence_result`（属 Branch 5 Confidence，17I 决定）
- ❌ 不写 `final_report`（属 Branch 6 Final Report，17J 决定）
- ❌ 不写 `review_stub` / `evaluation_stub`（17K / 17L 决定）
- ❌ 不写 `compatibility_metadata`（由 architecture_orchestrator 写）

### 9.4 standard payload 草案对 Projection 的约束

- standard_projection_payload validator 在 17A / PR-B 实现中要求
  `projection_result` section 必须存在
- Projection Layer 的输出必须能通过该 validator 的 shape check
- Projection Layer **不**需要在自身实现中调用 validator（validator 由
  architecture_orchestrator 在组装时调）

---

## 10. Historical Probability 规则

### 10.1 historical_probability 是 evidence / prior，不是最终答案

- 输出 up_rate / down_rate / probability / sample_count / sample_quality /
  impact —— 这些是**历史先验**
- main_projection_layer 把它当作 evidence input（与 `_historical_bias_payload`
  helper 一致；[main_projection_layer.py:97](services/main_projection_layer.py:97)）

### 10.2 不能直接决定 final_report

- final_report 由 Branch 6 汇总；historical_probability 不直接进 final_report
- final_report 通过 main_projection 的 `predicted_top1` / `state_probabilities`
  间接看到 historical evidence 的影响

### 10.3 不读 system 输出

- ❌ 不读 `exclusion_result` / `confidence_result` / `final_report`
- ❌ 不输出 most_unlikely_state 类否定字段
- ❌ 不输出 trading 字段
- 与 07A §3.2 / 1.0 §9 一致

### 10.4 可输出的 evidence 字段

- `dominant_historical_outcome`（up_bias / down_bias / mixed / insufficient_sample）
- `sample_count` / `sample_quality`
- `up_rate` / `down_rate` / `gap_up_rate` / `strong_close_rate`
- `historical_bias` / `impact`
- `rationale` / `warnings`

### 10.5 historical outcome / realized next-day result 归 Evaluation Layer

- matcher.py 的 NextDate / NextOpenChange 等"未来 K 线"字段属 Evaluation
  Layer（17F §7.2 / §12.3 / 17L 决定）
- historical_probability **不读**这些字段（避免 future leakage）
- evaluation 报告（accuracy / win-rate）由 Branch 8 单独产出

### 10.6 17G 推荐处置

- KEEP；docstring 显式声明 Projection Layer evidence helper（PR-PROJ-3）
- 不在 17G 改阈值 / 算法
- boundary tests：no system output read + no future outcome read

---

## 11. scanner / scan_bias 规则

### 11.1 scanner.py 拆分总览（与 17E §7.1 / 17F §7.1 / §12.4 一致）

| 部分 | 归属层 | 17G 决定 |
|---|---|---|
| `load_peer_coded`（peer CSV 加载） | Branch 1 Data Layer（17E §7.1 已确认） | — |
| `_get_nday_return` / `_get_same_day_move` / `compute_relative_strength_summary` / `compute_same_day_relative_strength_summary` / `compute_confirmation_state` / regime_features 调用 / `build_recent_avgo_window` | Branch 2 Feature Layer（17F §7.1 已确认） | — |
| `compute_scan_bias_and_confidence` / `scan_bias` / `scan_confidence` / `confirmation_state` 输出语义 | **Branch 3 Projection 候选 / LEGACY_PROJECTION_LIKE** | 详见 §11.2 |

### 11.2 scan_bias / scan_confidence 是早期 projection-like 输出

- `compute_scan_bias_and_confidence` ([scanner.py:409](scanner.py:409))：
  - 输入 RS score / regime / confirmation_state
  - 输出 `scan_bias = bullish / bearish / neutral` / `scan_confidence =
    high / medium / low`
- 这是 0.x 时代的"准 prediction"输出；**早于** main_projection_layer 存在；
  与 main_projection 的 predicted_top1 / state_probabilities 行为重复

### 11.3 17G 给出 3 选 1 路线（具体执行由 18A+ PR 决定）

| 路线 | 描述 | 优点 | 缺点 |
|---|---|---|---|
| **(a) freeze in scanner.py** | 保留 scan_bias / scan_confidence 在 scanner.py；docstring 显式 LEGACY_PROJECTION_LIKE；不再扩展 | 改动最小；UI 不需迁 | scanner.py 持续混合层；UI 仍读旧字段 |
| **(b) rename to feature signal** | 把 `scan_bias` 改为 `peer_signal_strength`（或 `rs_consensus_signal`）；显式声明这是 **feature signal**，**不是** prediction direction；保留输出但语义降级 | 语义清晰；不污染 Projection 主路径 | 改名跨 UI / tests / scripts；改动大 |
| **(c) merge into main_projection_layer evidence** | 把 RS + confirmation_state 作为 `key_supporting_signals` / `key_risk_signals` 喂给 main_projection；scanner 的 scan_bias 输出**降级**为 internal scoring，不暴露给下游 | 收敛到 Branch 3 主入口；语义统一 | 改动最大；需要 main_projection 重新平衡 evidence 权重 |

### 11.4 17G 默认推荐：路线 (a) freeze

- 理由：与 17D §11 一致——不立即拆；scan_bias 当前不在 main_projection
  的 evidence 输入中（main_projection 自己读 features + peer + historical）；
  freeze 风险最低
- 后续如果 17M UI Layer 决定迁 UI，再按 (b) / (c) 决定
- 17G **不**自动批准 (a) / (b) / (c) 任一项

### 11.5 17G 立即动作

- **无**（与 17D §11 / §17 §11 一致：本轮不改代码）
- §14 PR-PROJ-5 候选：scan_bias freeze docstring（marker only）；不改输出

---

## 12. primary_20day_analysis 规则

### 12.1 与 main_projection_layer 行为重复

- `primary_20day_analysis.py` 输出 `direction = up_bias / down_bias /
  mixed / unknown` / `confidence = high / medium / low / unknown` /
  `position_label` / `stage_label` / `volume_state`
- main_projection_layer 输出 `predicted_top1` / `predicted_top2` /
  `state_probabilities`（五状态）
- 两者**目标重叠**：都基于 20d feature 派生方向 / 概率
- 但**输出 schema 不兼容**（前者是 0.x ternary direction；后者是 07A 五
  状态分布）

### 12.2 17G 决定：归 LEGACY_PROJECTION_HELPER

- primary_20day_analysis 归 Branch 3 Projection（与 17F §7.5 一致）
- 但**不**作为 CORE_PROJECTION 主入口
- 标记为 **LEGACY_PROJECTION_HELPER**

### 12.3 17G 给出 3 选 1 路线

| 路线 | 描述 | 优点 | 缺点 |
|---|---|---|---|
| **(a) merge into main_projection_layer** | 把 primary_20day_analysis 的 direction / position_label / stage_label / volume_state 转为 main_projection 的 `key_supporting_signals` / `key_risk_signals`；删除 primary_20day_analysis 独立输出 | 收敛到主入口；schema 统一 | 改 V2 chain；caller 需迁；tests 大改 |
| **(b) freeze as legacy projection helper** | 保留；docstring 显式 LEGACY_PROJECTION_HELPER；不再扩展；caller 可继续读但不应该再加 | 改动最小；不破现有 | active path 上长期混双 helper |
| **(c) archive** | 移到 `archive/legacy/`；caller 全部迁完后 archive | 彻底清场 | 必须先全 caller 迁；时间长 |

### 12.4 17G 默认推荐：路线 (b) freeze

- 理由：与 17D §11 / §17 §11 一致；primary_20day_analysis 当前与 V2
  orchestrator 紧耦合；merge / archive 改动大
- 17G 之后视 V2 vs home_terminal 收敛进度（17J 决定）再选 (a) 或 (c)
- 17G **不**自动批准 (a) / (b) / (c) 任一项

### 12.5 17G 立即动作

- **无**
- §14 PR-PROJ-4 候选：freeze docstring + LEGACY_PROJECTION_HELPER marker；
  不改输出 schema

---

## 13. Projection Layer 测试策略

后续 Projection Layer 实现 PR 必须满足以下测试要求：

### 13.1 no exclusion_result input tests

- `build_main_projection_layer` / `run_main_projection_layer` 显式传
  `exclusion_result=...` → `TypeError`（17C PR-D 已实现）
- AST-level grep：`services/main_projection_layer.py` source 中**不**出现
  `exclusion_result` 作为变量名 / 参数名（除已废弃 docstring 描述外）
- 17G 阶段 PR-PROJ 不重复 17C 已有的 boundary tests；扩展到其它
  Projection Layer 模块

### 13.2 no confidence_result input tests

- Projection Layer 任一模块不接收 `confidence_result`
- AST-level grep：`services/main_projection_layer.py` /
  `services/historical_probability.py` / `services/primary_20day_analysis.py` /
  `services/projection_chain_contract.py`（only Projection helpers）source
  中**不**出现 `confidence_result`

### 13.3 no final_report input tests

- 同上，扩展到 `final_report` / `final_decision` / `combined_user_summary`

### 13.4 five-state probability shape tests

- `state_probabilities` 必须含 5 个 state（`大涨` / `小涨` / `震荡` /
  `小跌` / `大跌`）
- 概率值 ∈ [0.0, 1.0]
- sum 在 [0.99, 1.01] 范围内（浮点精度容忍）

### 13.5 ranked_states tests

- 长度为 5
- 按 probability desc 排序
- ties → state name lex order 作 tie-break

### 13.6 probability sum tests

- `sum(state_probabilities.values())` ≈ 1.0（容忍 ±0.01）
- 不允许 negative probability

### 13.7 historical evidence tests

- historical_probability 输出 fields shape 稳定
- main_projection 的 `_historical_bias_payload` 在 historical_match_result
  缺失时返回 `(0.0, [])` 不抛异常

### 13.8 peer_alignment evidence tests

- 当 peer_alignment passthrough 进 projection_result 时，schema 与
  `services/peer_alignment.build_peer_alignment` 输出一致（17B PR-C）

### 13.9 no trading fields tests

- Projection Layer 任一模块输出 dict / DataFrame 字段集合中**不含**：
  - `simulated_trade` / `trading_action` / `buy` / `sell` / `hold` /
    `hard_*` / `forced_*` / `required_*` / `_PROTECTION_LAYER_CONNECTED`

### 13.10 no hard / forced / required fields tests

- 与 §13.9 重叠；显式扩展为 AST-level grep

### 13.11 non-mutation tests

- Projection Layer 任一函数**不修改**入参（feature_payload / historical_match
  / peer_alignment）
- 输出 dict 与入参 dict 是不同 object（id 不同）

### 13.12 no LLM / no UI / no future outcome tests

- 不 import `anthropic` / `openai`
- 不 import `streamlit` / `ui.*`
- 不读取 future outcome（在线 inference 路径）
- anti-lookahead：feature_payload 中 `Date <= target_date` 假设由
  Feature Layer 保证；Projection 不二次校验，但不**主动**读 Date >
  target_date 的字段

### 13.13 baseline & regression

- 每个 PR-PROJ-* 必须以 Step 15 baseline 为起点（**3256 passed, 10
  skipped, 0 failed, 26 warnings, 94 subtests**）
- 新增测试数显式累加到 passed
- warnings / subtests 数变化必须**显式说明**

---

## 14. Projection Layer 后续实现 PR 候选

> **本节是 PR 候选清单，本轮 17G 不执行任一项**。最早 18A 由用户单独
> 决定执行哪个、何时执行、按什么顺序执行。

| 序号 | 名称 | 性质 | 目标 | 文件范围 | 测试 | 风险 | 是否必须先做 |
|---|---|---|---|---|---|---|---|
| **PR-PROJ-1** | projection_result contract validator helper | 代码（新增 helper） | 新增 `services/projection_result_contract.py`：定义 `PROJECTION_RESULT_FIELDS` + `validate_projection_result(result) -> list[str]` 纯函数 validator；体例与 17A `standard_projection_payload.v1` / 17F PR-FEATURE-1 一致；**不**改 main_projection_layer 实现 | `services/projection_result_contract.py`（新增）+ `tests/test_projection_result_contract.py`（新增） | focused + full pytest | L | 不强制；推荐第一项 |
| **PR-PROJ-2** | main_projection_layer 输出 standard projection_result keys | 代码（**仅**加 alias） | 在 `build_main_projection_layer` / `run_main_projection_layer` 输出**额外**加 `most_likely_state` / `ranked_states` / `non_mutation_confirmations` 字段；保留 `predicted_top1` / `predicted_top2` / `state_probabilities` 兼容 | `services/main_projection_layer.py`（仅加输出字段） | full pytest byte-stable except 新增字段；现有 boundary tests 全绿 | L | 不强制；与 PR-PROJ-1 协同 |
| **PR-PROJ-3** | historical_probability 归位 + boundary tests | 代码（仅 docstring + tests） | docstring 显式声明 Projection Layer evidence helper；新增 boundary tests：no exclusion / confidence / final_report read；no future outcome read；nor trading fields | `services/historical_probability.py`（docstring）+ `tests/test_historical_probability_boundary.py`（新增） | focused + full pytest | L | 不强制 |
| **PR-PROJ-4** | primary_20day_analysis 去重 / 降级 / 合并 | 代码（**仅** marker docstring） | 默认推荐路线 (b) freeze：在 `services/primary_20day_analysis.py` 顶部加 LEGACY_PROJECTION_HELPER marker docstring；与 16D / 16I §11 体例一致；**不**改输出 schema；**不**改 caller | `services/primary_20day_analysis.py`（docstring） | full pytest byte-stable | L | 不强制；可推迟到 17J 之后 |
| **PR-PROJ-5** | scanner scan_bias 迁出或冻结 | 代码（**仅** marker docstring） | 默认推荐路线 (a) freeze：在 `scanner.py` 顶部 docstring 加 "scan_bias / scan_confidence: LEGACY_PROJECTION_LIKE — frozen; future direction owned by main_projection_layer"；**不**改 `compute_scan_bias_and_confidence` 实现；**不**改 caller / UI | `scanner.py`（docstring） | full pytest byte-stable | L | 不强制；可与 17M UI Layer 协同后再决定（路线 a/b/c 选择） |
| **PR-PROJ-6** | orchestrator projection caller boundary tests | 代码（仅 tests） | 给 V1 / V2 orchestrator + entrypoint + adapter 加 `tests/test_projection_orchestrator_caller_boundary.py`：扫 source，断言**不**反向 import projection / exclusion / confidence / final_report 之间错误方向；扩展 17C PR-D 已有 boundary tests | tests only | focused + full pytest | L | 不强制；可推迟到 17J 之后 |
| **PR-PROJ-7** | legacy projection bridge deprecation marker | 代码（**仅** docstring）| 给 13 个 bridge 中的 6 个 projection 相关 bridge（predict.py / projection_orchestrator V1 / projection_orchestrator_v2 / projection_entrypoint / projection_v2_adapter / predict_legacy_adapter / predict_legacy_v2_bridge / home_terminal_orchestrator）加 / 校对 marker docstring；与 16I §11.2 体例一致；**不**改逻辑 | 见 §7 列出的 8 个文件 | full pytest byte-stable | L | 不强制；与 17D §10 / §11 一致（PR-G 暂停）——本 PR 是 PR-G 在 Projection Layer 范畴的**子集** |

### 14.1 候选 PR 之间的依赖

- PR-PROJ-1 → PR-PROJ-2：先有 contract validator，再让 main_projection 输出
  standard keys
- PR-PROJ-3 / PR-PROJ-4 / PR-PROJ-5：互不依赖；可任意顺序
- PR-PROJ-6 / PR-PROJ-7：需要 17J Final Report Layer Plan 入 main 后才能
  最终决定 marker 内容（与 17D §10.1 / §10.3 一致）；可在 17J 之后启动
- 任何**代码** PR-PROJ-* 都依赖 **17G 已入 main**（前置条件）

### 14.2 候选 PR 都不能做的事

- ❌ 不改 `main_projection_layer` 内部计算逻辑（`_base_outlook` /
  `_score_distribution` / `_normalize_distribution` / `_apply_history_weights`
  / `_FALLBACK_DISTRIBUTION`）
- ❌ 不改 `historical_probability` 阈值 / 算法
- ❌ 不改 `primary_20day_analysis` 输出 schema（仅 marker）
- ❌ 不改 `scanner.py` `compute_scan_bias_and_confidence` 实现（仅 marker）
- ❌ 不动 V1 / V2 orchestrator 业务逻辑
- ❌ 不动 `predict.py` 业务逻辑
- ❌ 不切换默认 `run_predict` 路径（hard rule 1.0 §6.4）
- ❌ 不动 exclusion_layer / confidence_evaluator / final_decision（17H/I/J 处理）
- ❌ 不动 UI（17M 处理）
- ❌ 不引入 trading / hard / forced / required
- ❌ 不复活 `continuous_smoothing*` / `archive/legacy/root_stubs/*`
- ❌ 不修改 `.gitignore`
- ❌ 不处理 `avgo_agent.db`（含 backup）
- ❌ 不处理 handoff / logs / DB backup / `.claude/worktrees/`

---

## 15. 与 Feature / Exclusion / Confidence 的交接

### 15.1 数据流方向（与 1.0 §9 / 17F §15 一致）

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
   ──►projection_result
                       ──►exclusion_result
                                          ──►confidence_result
        │                 │                 │
        └────────┬────────┴────────┬────────┘
                 ▼                 ▼
           Branch 6 Final Report Layer
            （仅 aggregate / 不 mutate）
```

### 15.2 Feature Layer 输出 feature_payload

- 与 17F §8 一致

### 15.3 Projection 读 feature_payload，输出 projection_result

- 与 §3.1 / §8.1 一致
- **不**反向 import Feature Layer 业务模块（除了 17B PR-C `peer_alignment`
  公共 helper）

### 15.4 Exclusion 也读 feature_payload，输出 exclusion_result

- 与 17H 计划一致（17H 入 main 后正式 cross-reference）

### 15.5 Projection 不读 Exclusion / Exclusion 不读 Projection

- 与 07A §3.2 / 07B §3.2 / 17C PR-D 一致
- 17C PR-D 已物理保证 main_projection 不接收 `exclusion_result` 形参

### 15.6 Confidence 读 projection_result + exclusion_result + feature_payload

- 与 07C §3.1 一致
- Confidence**只读** projection_result（不改写）；与 07C §5 / §11 一致

### 15.7 Final Report 汇总，不改 projection_result

- 与 07D §5 / §6 / §7 一致
- Final Report 在 `non_mutation_confirmations` 中显式声明未改 projection

---

## 16. 清场 / 隔离建议

> **本节按 16H 决策表 8 个标签给出 Projection Layer 范畴内的清场建议**。
> 本轮**不**执行任何清场动作。

### 16.1 KEEP（Projection Layer CORE）

- `services/main_projection_layer.py`
- `services/historical_probability.py`
- `services/projection_preflight.py`
- `services/projection_orchestrator_preflight.py`
- `services/projection_rule_preflight.py`
- `services/projection_memory_briefing.py`

### 16.2 KEEP_PARTIAL（混合层；保留但需协同）

- `services/projection_chain_contract.py`（其中 `least_likely_from_projection`）
- `services/projection_output_contract.py`（Step 1A 老契约；与 17A 并存）
- `scanner.py`（其中 `compute_scan_bias_and_confidence`）

### 16.3 LEGACY_PROJECTION_HELPER（归 Branch 3，但不是主入口）

- `services/primary_20day_analysis.py`（§12 默认路线 (b) freeze）

### 16.4 NOT_PROJECTION_LAYER（17G 声明非 Projection；归其它层）

- `services/projection_narrative_renderer.py` → 17J Final Report / 17M UI
- `services/projection_three_systems_renderer.py` → 17J Final Report
- `services/projection_review_closed_loop.py` → 17K Review & Learning
- `services/consistency_layer.py` → 17J Final Report
- `services/predict_summary.py` → 17J Final Report

### 16.5 TEMP_MIGRATION_BRIDGE（不进 9 分支正式架构）

- `predict.py`
- `services/projection_orchestrator.py`（V1）
- `services/projection_v2_adapter.py`
- `services/predict_legacy_adapter.py`
- `services/predict_legacy_v2_bridge.py`

### 16.6 LEGACY_ACTIVE_DEPENDENCY（不进 9 分支；当前主路径）

- `services/projection_orchestrator_v2.py`
- `services/projection_entrypoint.py`
- `services/home_terminal_orchestrator.py`

### 16.7 MIGRATE_LATER

- §16.4 / §16.5 / §16.6 全部模块 → 17J 接管
- `services/projection_output_adapter.py`（16G UNKNOWN；DEEP_AUDIT_REQUIRED）

### 16.8 ARCHIVE_IN_REPO

- 无 Projection Layer 范畴的 archive 候选（与 16H / 17E §15.5 / 17F §16.5
  一致）

### 16.9 QUARANTINE

- `predict.py` / V1 orchestrator / projection_v2_adapter /
  predict_legacy_adapter / predict_legacy_v2_bridge → marker（与 16I §11
  体例一致；17G 不加 marker，由 PR-PROJ-7 / 17J 决定）

### 16.10 DEEP_AUDIT_REQUIRED

- `services/projection_output_adapter.py`（16G §11 UNKNOWN 之一；docstring
  "not yet wired"；本轮不动；与 17F §16.10 一致）
- 17G 阶段不要求 deep audit；可在 17J 之后视情况启动

### 16.11 DELETE_NOW

- **空**（与 16H §13 / 17E §15.7 / 17F §16.7 一致）

### 16.12 DELETE_LATER

- 无 Projection Layer 范畴的 delete 候选（17G 阶段；任何 archive 必须先
  全 caller 迁完）

### 16.13 MIGRATE_CALLER_FIRST

- §16.5 全部 TEMP_MIGRATION_BRIDGE 模块 → 必须先迁 caller，再 archive；
  与 16H §3 一致

> **重申**：任何文件删除 / 移动 / archive 必须等 16H 规则 + 17D §11 + 用户
> 单独确认。17G 仅给出**建议**，**不**执行。

---

## 17. 不允许事项

**17G 起，Projection Layer 范畴内**严格禁止：

- ❌ 不改代码（无 `.py` 文件被修改；本轮 0 修改）
- ❌ 不跑数据
- ❌ 不跑 replay / 不跑 validation / 不跑 historical evaluation
- ❌ 不改 DB / 不改 DB schema
- ❌ 不迁 Exclusion / Confidence / Final Report / Review / Evaluation /
  UI（各层 Plan 自负其责）
- ❌ 不接 trading / 不输出 buy / sell / hold / hard / forced / required
- ❌ 不进入 3R-5 / 3R-6（1.0 §12 / 16I §15 / 17D §11 / 17E §16 / 17F §17 /
  本轮再次重申）
- ❌ 不启动任何代码 PR（PR-PROJ-* 候选要等 18A）
- ❌ 不修改 `.gitignore`
- ❌ 不处理 `avgo_agent.db`（含 backup）
- ❌ 不处理 handoff / logs / DB backup / `.claude/worktrees/`
- ❌ 不复活 `continuous_smoothing*` / `archive/legacy/root_stubs/*` /
  promotion 三模块
- ❌ 不污染 2026-01-01 之后 final holdout
- ❌ 不借 17G 顺手做 Data / Feature / Exclusion / Confidence / Final
  Report / Review / Evaluation / UI 范畴改动
- ❌ 不继续 PR-E confidence key 对齐（与 17D §9 一致）
- ❌ 不启动 UI / bridge / orchestrator 实现任务（与 17D §10 一致）
- ❌ 不默认迁移 `run_predict` 到 V2（hard rule 1.0 §6.4 / §12）
- ❌ 不打开 16I PR-G bridge marker（与 17D §10.1 一致）
- ❌ 不打开 16I PR-F architecture_orchestrator MVP（与 17D §10.3 一致）

> 与 17D §11 / 17E §16 / 17F §17 一致；本轮再次锁定。

---

## 18. 推荐下一步

> **首选**：**Step 17H：Exclusion Layer Rebuild Plan**

理由（与 17D §12 / 17E §17 / 17F §18 一致 + 17G 实战观察）：

- Projection Layer 计划（17G）已就位
- 数据流方向是 Data → Feature → {Projection, **Exclusion**, Confidence} →
  Final Report → ...（1.0 §9 / 16C §3）
- 按九分支编号顺序，下一层是 Exclusion（Branch 4）
- Projection / Exclusion / Confidence 三系统**并行**；按编号 17G → 17H → 17I
  顺序写最自然
- **17H 的工作量中等**：17H 必须接管
  - `services/exclusion_layer.py`（peer_alignment 已 17B PR-C 抽出；exclusion
    层主入口）
  - `services/exclusion_*` 系列（如有 advisory / preflight）
  - peer 非确认信号映射（07B §3.1）
  - false_exclusion_risk / triggered_rule schema（07B §9）
- 17H 入 main 之前，**不**允许在 Exclusion Layer 范畴开任何代码 PR

**不推荐**：

- 不推荐跳到 17I / 17J / 17K / 17L / 17M（必须先有 Exclusion Plan）
- 不推荐借 17G / 17H 做代码改动（与 17D §11 一致）
- 不推荐重启 16I PR-E / PR-F / PR-G / PR-H（必须等对应层 Plan）
- 不推荐解锁 3R-5 / 3R-6（1.0 §12 7 项前提仍未全部满足）
- 不推荐立刻做 PR-PROJ-* 任一项（与 17G 协同更合算）

> **明确**：本轮 17G 推荐的下一步**只有一个候选**——17H Exclusion Layer
> Rebuild Plan。

---

## 19. 严守边界

本轮 Step 17G **只**写 Projection Layer Rebuild Plan：

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
- ❌ 未启动任何代码 PR（PR-PROJ-* 候选要等 18A）
- ❌ 未继续 PR-E confidence key 对齐
- ❌ 未启动 UI / bridge / orchestrator 实现任务
- ❌ 未做任何局部 patch
- ❌ 未 commit / 未 push（按本轮指令）

唯一新增文件：[tasks/record_17g_projection_layer_rebuild_plan.md](tasks/record_17g_projection_layer_rebuild_plan.md)（本文件）。

后续修改路径：任何对 §3 职责定义 / §4 禁止事项 / §5 inventory / §6
CORE_PROJECTION / §7 LEGACY/BRIDGE / §8 projection_result 标准化 / §9 与
standard payload 关系 / §10 historical_probability / §11 scanner / §12
primary_20day_analysis / §13 测试策略 / §14 PR 候选 / §15 与 Feature /
Exclusion / Confidence 交接 / §16 清场建议 / §17 禁止事项 / §18 下一步 的
调整，都必须**显式更新本文件**；同时检查是否需要同步更新 1.0 / 16C /
16D / 17D / 17E / 17F 与 17H（17H 入 main 后）。
