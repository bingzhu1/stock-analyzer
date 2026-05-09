# 17I记录：Confidence Layer Rebuild Plan

> 本记录是 **Step 17I：Confidence Layer 重建计划**——九分支按层重建中
> 的**第五层**（Branch 5）。1.0 canonical / 16A blueprint / 16B inventory /
> 16C target dataflow & contract decision / 16D isolation & quarantine
> plan / 16E core chain refactor plan / 16F no-patching principle / 16G
> full module decomposition standup / 16H repository clearing decision
> table / 16I core chain rebuild execution plan / 17A PR-B standard
> payload skeleton / 17B PR-C peer_alignment 抽公共模块 / 17C PR-D
> main_projection 去 `exclusion_result` 形参 / 17D layer-by-layer rebuild
> governance / 17E Data Layer Rebuild Plan / 17F Feature Layer Rebuild
> Plan / 17G Projection Layer Rebuild Plan / 17H Exclusion Layer Rebuild
> Plan 已全部入 main（main 最新 commit `392e967`）。
>
> 本轮**只**写计划文档：未改业务代码、未新增测试、未删除文件、未移动
> 文件、未修改 `.gitignore`、未处理 handoff、未处理 logs / DB backup /
> `.claude/worktrees/`、**未处理 `avgo_agent.db`**、未跑 replay /
> validation / historical evaluation、未写 DB / 未改 DB schema、未默认
> 迁移 `run_predict` 到 V2、未接 trading、未输出 buy / sell / hold /
> hard / forced / required、未进入 3R-5 / 3R-6、未启动任何代码 PR、
> 未直接做 PR-E confidence key 对齐、未启动 UI / bridge / orchestrator
> 实现任务、未做任何局部 patch、未 commit / 未 push。
>
> 唯一 deliverable：本文件。
>
> **本记录优先级**：与 17E / 17F / 17G / 17H / 17J ~ 17M 各层 Plan 同级；
> 与 1.0 / 16A / 16C / 16D / 16F / 16I / 17D / 17E / 17F / 17G / 17H 协同。
> 冲突仲裁路径与 1.0 §14 / 17D §13 一致：旧 records 若与 17I 在 Confidence
> Layer 范畴冲突，**以 17I 为准**。

---

## 1. Step 17I 目的

把九分支按层重建从 Exclusion Layer（17H）推进到**第五层（Confidence Layer）
的具体重建计划**。

**本轮只回答**：

- Confidence Layer 当前长什么样（模块 inventory + active path）
- Confidence Layer 目标长什么样（保留 / 迁移 / 隔离 / 删除候选）
- Confidence Layer 与上下游的边界（{Projection, Exclusion} ↑（只读，并行）
  + Feature ↑（只读 summary）；Final Report ↓；**不**改写任一系统输出）
- `confidence_result` 标准化规则（与 1.0 §8 Branch 5 / 07C §9 一致）
- standard schema 优先 + interim schema 兼容的读取规则
- `agreement_status` / `conflict_level` / `combined_confidence` / `calibration_context`
  规则
- **PR-E confidence key 对齐**如何归入本层后续 implementation PR
- Confidence Layer 后续可能的代码 PR 候选（**不**执行）
- 与 Projection / Exclusion / Final Report 的交接

**本轮不回答**：

- 不写 Final Report / Review / Evaluation / UI 计划（17J ~ 17M）
- 不开任何代码 PR（最早 18A）
- 不动 `avgo_agent.db`、`.gitignore`、handoff、logs、DB backup、worktrees
- 不直接做 PR-E confidence key 对齐（与 17D §9 / 17H §16 一致；归入 §13
  PR-CONF-2）
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
| 17G Projection Layer Rebuild Plan | ✅ commit `54f74f1` |
| 17H Exclusion Layer Rebuild Plan | ✅ commit `392e967` |
| main 最新 commit | `392e967` |
| worktree 唯一 deliberate untracked | `.claude/handoffs/task_089_post_pr_cleanup.md` |
| 战略阶段 | 从 Exclusion Layer plan（17H）→ **Confidence Layer plan（17I 本轮）** |
| 3R-5 / 3R-6 | ❌ 仍然不允许进入 |
| 第一个按层实现 PR（18A）| ❌ 仍未 |
| PR-E confidence key 对齐 | ⏸️ 暂停（17D §9）；17I 入 main 后归入 §13 PR-CONF-2 |

**17D §6 PR 准入规则提醒**：

- 任何代码 PR 必须绑定九分支某一层 + 引用对应层 Plan §
- 17I 入 main 后，Confidence Layer 范畴的 PR 才**有资格**被讨论
- 17I 本身**不**自动批准任何 PR；PR-E / PR-CONF-* 仍需 18A 单独审批

**层间依赖**：

- 17I 依赖 17F / 17G / 17H（已就位）
- 17I **不**依赖 17J ~ 17M（可独立写完）
- 17I 与 17J 在 final_decision 读 confidence_result 字段约定上有协同点；
  17J 入 main 后正式 cross-reference

---

## 3. Confidence Layer 职责定义

**Confidence Layer（Branch 5）只回答一件事**：

> **"这次推演和否定可靠吗？两者一致还是冲突？"**——**只读评价**
> projection / exclusion / feature evidence，输出 `confidence_result`。

### 3.1 只做的事（与 1.0 §8 Branch 5 / 07C §3.1 一致）

- 读取 Branch 3 Projection 输出的 `projection_result`（**只读**）
- 读取 Branch 4 Exclusion 输出的 `exclusion_result`（**只读**）
- 读取 Branch 2 Feature Layer 的 feature summary / peer_alignment summary
  （只读；通过 `historical_context` / `market_context` 间接进入；不直接
  调用 Feature Layer 模块）
- 读取 offline calibration 权重 / 校准表（通过 `calibration_context` 入参；
  不允许 online future outcome 直接入参）
- 读取 regime label / 历史样本量信息
- 派生 `projection_confidence`（projection 系统当次可靠性）
- 派生 `exclusion_confidence`（exclusion 系统当次可靠性）
- 派生 `agreement_status`（projection top vs exclusion top 是否冲突）
- 派生 `conflict_level`（none / low / medium / high）
- 派生 `combined_confidence`（保守 min combine；conflict 进一步降级）
- 输出 `confidence_reasoning` / `reliability_warnings` / `sample_size_notes` /
  `calibration_notes` / `raw_evidence_refs`
- 标注 `non_mutation_confirmations.projection_result_mutated = False` /
  `exclusion_result_mutated = False`

### 3.2 不做的事（与 1.0 §8 Branch 5 / 07C §3.2 / §5 / §11 一致）

- ❌ 不生成 `most_likely_state`（归 Branch 3 Projection）
- ❌ 不生成 `most_unlikely_state`（归 Branch 4 Exclusion）
- ❌ 不修改 `projection_result` / `exclusion_result` / `feature_payload`
- ❌ 不输出 `predicted_top1` / `predicted_top2` / `state_probabilities` /
  `direction` / `triggered_rules` / `excluded_states` 等 Projection /
  Exclusion 字段
- ❌ 不做 final report（`combined_user_summary` 归 Branch 6 Final Report）
- ❌ 不做 review / lesson（归 Branch 7）
- ❌ 不做 evaluation（accuracy / win-rate 归 Branch 8）
- ❌ 不做 UI 展示
- ❌ 不输出 trading action / hard / forced / required
- ❌ 不调用 LLM
- ❌ 不写 DB / 不改 DB schema
- ❌ 不直接运行 replay
- ❌ 不直接接 broker API
- ❌ 不读取 future outcome（在线 inference 路径）
- ❌ 不允许 `confidence_result → projection / exclusion` 回流（07C §11）

### 3.3 输入 / 输出（白名单）

**输入**（与 07C §3.1 / 17F §15 / 17G §15 / 17H §12 一致）：

- `projection_result`（来自 Branch 3 Projection，**只读**）
- `exclusion_result`（来自 Branch 4 Exclusion，**只读**）
- `market_context`（regime label / 市场环境，**只读**）
- `historical_context`（历史样本量 / evidence_refs，**只读**）
- `calibration_context`（offline calibration 权重；含 `ready` flag /
  `projection_score` / `exclusion_score` / `notes` / `evidence_refs`）
- `target_date` / `confidence_date` / `symbol`

**输出**（schema_version `confidence_system_result.v1`，与 07C §9 一致；
当前 confidence_evaluator 已实现该 schema）：

- `confidence_result` dict（结构详见 §8）

**禁止输入**（与 07C §3.2 / §11 / 1.0 §9 一致）：

- ❌ `final_report` / `review_record` / `evaluation_report`
- ❌ Future outcome（在线 inference 路径）
- ❌ 2026-01-01 之后 final holdout（在线 inference）
- ❌ Trading 输入 / broker / position state

---

## 4. Confidence Layer 禁止事项

Confidence Layer **永久禁止**输出 / 引入以下任一：

| 类别 | 禁止项 | 锚点 |
|---|---|---|
| Projection / Exclusion 字段（output 重写） | `most_likely_state` / `most_unlikely_state` / `predicted_top1` / `predicted_top2` / `state_probabilities` / `triggered_rules` / `excluded_states` / `false_exclusion_risk` / `direction` | 07C §5 / §11 |
| 改写 system 输出 | `modified_projection` / `modified_exclusion` / `projection_correction` / `exclusion_correction` / `projection_result_mutated = True` / `exclusion_result_mutated = True` | 07C §5 / 当前 `_FORBIDDEN_FIELDS` 已覆盖 |
| Final Report 字段 | `combined_user_summary` / `agreement_or_conflict_section` / `final_report_mutation` | 07C §3.2 / 07D §6 |
| 交易 / 强制 | `buy` / `sell` / `hold` / `simulated_trade` / `trading_action` / `no_trade` / `hard_*` / `forced_*` / `required_*` / `_PROTECTION_LAYER_CONNECTED` / `production_promotion` | 12E X1..X5 / 1.0 §6 / `_FORBIDDEN_FIELDS` |
| 回流（output → input） | `confidence_result → projection` / `confidence_result → exclusion`（在线 inference 路径） | 07C §11 / 1.0 §9 |
| 下游模块 import（active path） | import `services.main_projection_layer` / `services.exclusion_layer` / `services.final_decision` / 任何 `predict.*` 反向调用 | 07C §10 |
| LLM 调用 | `anthropic` / `openai` / 任何文本生成 SDK | 1.0 §13 hard rule 1 / 5 / 当前 docstring 已声明 |
| UI 调用 | `streamlit` / 任何 ui/ 模块 import | 1.0 §13 hard rule 3 |
| DB schema 改动 | `CREATE TABLE` / `ALTER TABLE` 在 17I 阶段不允许 | 17E §11 / 17F §11 / 17G §11 / 17H §11 / 17I §11 |
| 直接运行 replay | 调用 `scripts/run_contract_replay*` / `scripts/historical_replay_training*` | 17D §11 |
| Future outcome 回灌 | 在线 inference 路径中读取目标日之后的 close / outcome；当前 `_filter_evidence_by_target_date` 已实现 cutoff | 1.0 §9 / 07C §3.2 / 当前实现 |
| 污染 2026 holdout | 在 in-sample confidence 计算中读取 2026-01-01 之后的窗口 | 1.0 §5 rule 8 |
| heuristic fallback | 当 `calibration_context` 缺失或 `ready=False` 时**捏造** heuristic score | 07C §9.3 / 当前 docstring 已声明 |

### 4.1 当前 `_FORBIDDEN_FIELDS` 已覆盖的项

confidence_evaluator.py:53-72 已锁定以下输出禁字段（17I 不动；后续 PR-CONF-*
不允许扩 / 删）：

```
most_likely_state / most_unlikely_state / modified_projection /
modified_exclusion / projection_correction / exclusion_correction /
hard_exclusion / forced_exclusion / required_decision / trading_action /
buy / sell / hold / simulated_trade / no_trade / final_report_mutation /
production_promotion / _PROTECTION_LAYER_CONNECTED
```

---

## 5. 当前 Confidence Layer 模块 inventory

> **范围说明**：本表覆盖 (1) **核心 Confidence 模块** (2) **跨层 helper
> （final_decision / projection_chain_contract 中读 confidence_result 部分）**
> (3) **caller**（home_terminal / projection_orchestrator_v2）(4) **calibration
> data 候选**（active_rule_pool_calibration / contract_calibration_inputs）。
> standard payload skeleton（17A PR-B）属 INFRA / SCHEMA，不在本表（与
> 17F / 17G / 17H 处理一致）。

### 5.1 核心 / 候选 inventory

| module_path | current_role | current_status | target_role | keep / migrate / quarantine / delete | active_callers | risk | next_action |
|---|---|---|---|---|---|---|---|
| `services/confidence_evaluator.py` | Branch 5 唯一主入口；`build_confidence_result` 含 `_compute_agreement` / `_combine_confidence` / `_evaluate_one_side`；输出 `confidence_system_result.v1`；`_FORBIDDEN_FIELDS` 强制净化输出 | KEEP_ACTIVE；docstring 显式 06 / 07C / 11C boundary contract；`projection_result_mutated=False` / `exclusion_result_mutated=False` | **CORE_CONFIDENCE**：Branch 5 主入口 | KEEP | `services/home_terminal_orchestrator:21+169`、`services/projection_orchestrator_v2:12+483+585`、tests | M | §6.1；§13 PR-CONF-2 schema adapter（standard 优先 + interim 兼容） |
| `services/consistency_layer.py` | cross-system consistency check；输入 `exclusion_result` + `main_projection_result` + `peer_alignment` + `historical_match_result`；输出 `consistency_flag` / `consistency_score` / `conflict_reasons`；当前**读 interim schema**（`predicted_top1.state` 直接） | KEEP_ACTIVE；docstring "Internal consistency checks across projection v2 layers" | **NOT_CONFIDENCE_LAYER** / **NOT_FINAL_REPORT_CORE**：跨 projection / exclusion / peer / historical；功能与 confidence_evaluator 的 `_compute_agreement` 重叠（详见 §7）| MIGRATE_LATER（17J 决定 vs 吸收 vs freeze） | `services/home_terminal_orchestrator:22`、`services/projection_orchestrator_v2:23`、tests | M | §7；与 17F §6.8 / 17G §16.4 / 17H §15.3 一致 |
| `services/final_decision.py` 中 `confidence_result` 读取部分 | `_confidence_from_result` 把 `confidence_result.combined_confidence.level` 输出为 `final_confidence`；`build_final_decision` 把 confidence section / non_mutation 标志展示进 final_report | KEEP_ACTIVE；docstring 显式 06 / 07C / 07D / 11B boundary | **NOT_CONFIDENCE_LAYER**：归 Branch 6 Final Report（17J 决定）| KEEP（不动）；17J 接管 | V2 chain / tests | L | §15 / 17J |
| `services/projection_chain_contract.py` 中 `consistency` 字段输出（`build_unified_projection_payload` / `build_prediction_log_record`） | 把 consistency_layer 输出嵌入 `unified_projection_payload` / `prediction_log_record` | KEEP_ACTIVE | **NOT_CONFIDENCE_LAYER**：归 Branch 6 Final Report / log_store helper（17J 决定） | KEEP（不动） | V2 chain / tests | L | 17I 不动 |
| `services/standard_projection_payload.py` 中 `confidence_result` section 关系 | PR-B 9 顶层 key 之一含 `confidence_result`；validator 要求该 section 存在；当前未接入 active path | KEEP_ACTIVE；纯函数 validator | **INFRA / SCHEMA**（属 17A 新架构地基；**不**属 Branch 5）| KEEP（不在 Confidence Layer 范围；但 confidence_result 输出会被 validate） | tests | L | §9 cross-reference；不动 |
| `services/active_rule_pool_calibration.py` | confidence calibration 数据准备；16G UNKNOWN 之一 | KEEP_ACTIVE | **DEEP_AUDIT_REQUIRED**（16G UNKNOWN）；候选 calibration data source | KEEP（不动） | scripts；UI；tests | M | §12.4 / §13 PR-CONF-7（calibration data source plan） |
| `services/contract_calibration_inputs.py` | confidence calibration input contract；输入 source 准备 | KEEP_ACTIVE | **DEEP_AUDIT_REQUIRED**（与 active_rule_pool_calibration 系列协同）| KEEP（不动） | scripts；tests | M | §12.4 / §13 PR-CONF-7 |
| `services/home_terminal_orchestrator.py:169` `build_confidence_result` 调用 | **未传** `calibration_context` → 静默 fallback unknown | LEGACY_ACTIVE_DEPENDENCY；属 §15 home_terminal bridge | **NOT_CONFIDENCE_LAYER**：caller；归 17J orchestrator 处置 | KEEP（不动）；§13 PR-CONF-3 显式传 `{"ready": False}` | UI（home_terminal tab）；tests | M | §12.2 / §13 PR-CONF-3 |
| `services/projection_orchestrator_v2.py:483+585` `build_confidence_result` 调用 | **未传** `calibration_context` → 静默 fallback unknown | LEGACY_ACTIVE_DEPENDENCY；属 §15 V2 bridge | **NOT_CONFIDENCE_LAYER**：caller；归 17J orchestrator 处置 | KEEP（不动）；§13 PR-CONF-3 显式传 `{"ready": False}` | V2 chain / tests | M | §12.2 / §13 PR-CONF-3 |
| `tests/test_confidence_evaluator.py` | confidence_evaluator boundary tests；含 forbidden import + forbidden field tests | KEEP | KEEP | KEEP | — | L | 不动 |
| `tests/test_confidence_system_contract_fields.py` | 07C 契约字段 tests；含读 `predict.run_predict` boundary | KEEP | KEEP | KEEP | — | L | 不动 |
| `tests/test_confidence_result_wiring_boundary.py` | wiring boundary tests | KEEP | KEEP | KEEP | — | L | 不动 |
| `tests/test_final_decision_aggregator_purification_boundary.py` | final_decision 不重算 confidence boundary tests | KEEP（属 Branch 6 测试范围） | KEEP | KEEP | — | L | 不动 |
| `tests/test_consistency_layer.py` | consistency_layer boundary tests | KEEP（属 Branch 6 测试范围；与 §7 协同迁移） | KEEP | KEEP | — | L | 不动 |

### 5.2 关键发现：当前 confidence_evaluator 已正确实现 standard schema 读取，但调用方喂的不是 standard schema

**`_compute_agreement`（confidence_evaluator.py:154-178）**只读 standard
schema：

- `proj.most_likely_state` / `proj.ranked_states`
- `excl.most_unlikely_state` / `excl.ranked_unlikely_states`

但实际**调用方喂入的 schema**：

- main_projection_layer 输出 **interim**：`predicted_top1.state` /
  `predicted_top2.state` / `state_probabilities`（17G §5 / §8.2）
- exclusion_layer 输出 **interim**：`triggered_rule` (single) / `action` /
  `reasons`（17H §5.1 / §11.1）

**结果**：`_compute_agreement` 始终走到 `if not most_likely or not most_unlikely:
return "unknown"`（line 165-166）→ `agreement_status` 长期 `unknown`。
这是 1.0 §3 问题描述对应的 schema 不齐根因。

### 5.3 当前 confidence_evaluator 已正确实现 calibration_context 显式 fallback

`build_confidence_result`（line 309-501）当 `calibration_context` 缺失或
`ready=False` 时：

- 不捏造 heuristic（与 07C §9.3 / docstring 一致）
- 显式追加 `reliability_warnings` + `calibration_notes`
- `projection_confidence.level` / `exclusion_confidence.level` /
  `combined_confidence.level` 全部走 `unknown`

**问题不在 evaluator**，而在 **caller 没显式传 `{"ready": False}`**：

- `home_terminal_orchestrator.py:169` — 不传 `calibration_context`
- `projection_orchestrator_v2.py:483` — 不传
- `projection_orchestrator_v2.py:585` — 不传

不传时 evaluator 走第一条 fallback：`if not calibration: → "calibration_context
缺失，可信度评估降级为 unknown"`（line 360-363）。已经有 warning，但用户
角度看不到 caller 主动的 contract（"我知道我没接 calibration"）。§13
PR-CONF-3 让 caller 显式传 `{"ready": False}` 把"未传"变成"明确未 ready"。

### 5.4 关键说明

- **Confidence Layer 当前唯一**真正符合 1.0 §8 Branch 5 / 07C 契约的入口
  是 `services/confidence_evaluator.py`。
- **`_FORBIDDEN_FIELDS` 已锁定 19 项禁输出字段**；17I 不改；PR-CONF-* 不
  允许扩 / 删
- **confidence_evaluator 已 byte-stable 实现 07C 大部分契约**（schema
  v1 / `non_mutation_confirmations` / `_filter_evidence_by_target_date`
  cutoff / heuristic fallback 拒绝）
- **PR-E 实质**：让 `_compute_agreement` 在 standard schema 缺失时 fallback
  到 interim schema（`predicted_top1.state` / `triggered_rule`）；同时让 3
  个 caller 显式传 `calibration_context`。这是 **Confidence Layer 内部 +
  caller** 的 schema adapter 工作；不是"小修小补"。归 §13 PR-CONF-2 + PR-CONF-3
- **`consistency_layer` 与 confidence_evaluator agreement 部分功能重叠**；
  归 17J Final Report 决定（详见 §7）
- **DELETE_NOW 集合为空**（与 16H §13 / 17E §15.7 / 17F §16.7 / 17G §16.11 /
  17H §15.8 一致）

---

## 6. CORE_CONFIDENCE 保留模块

> Confidence Layer 的**核心保留模块**：当前**只有 1 个**主入口（17I
> 阶段无歧义归属 Branch 5 的 active asset）。

### 6.1 `services/confidence_evaluator.py`

| 维度 | 说明 |
|---|---|
| 为什么保留 | Branch 5 唯一**符合 07C 契约**的主入口；docstring 显式 06 / 07C / 11C boundary contract；输出 `confidence_system_result.v1` 完整 schema；`_FORBIDDEN_FIELDS` 强制净化输出；`non_mutation_confirmations` 已实现 |
| 目标职责 | (1) 读 `projection_result` + `exclusion_result` + `market_context` + `historical_context` + `calibration_context`（全部只读）(2) 派生 `projection_confidence` / `exclusion_confidence` / `agreement_status` / `conflict_level` / `combined_confidence` (3) 输出完整 `confidence_system_result.v1` dict (4) 输出 `non_mutation_confirmations.projection_result_mutated = False` / `exclusion_result_mutated = False` |
| 是否需要改名 / 拆分 | ❌ 17I 不改名；不拆分 |
| 是否有跨层问题 | ⚠️ 当前 schema 与 main_projection / exclusion_layer 当前 interim schema 不齐 → `agreement_status` 长期 `unknown`；这是**适配器**问题，不是结构性反向 import 问题；归 §13 PR-CONF-2 |
| 后续实现任务 | §13 PR-CONF-1：confidence_result contract validator；§13 PR-CONF-2：schema adapter（standard 优先 + interim 兼容；含 PR-E 实质内容）；§13 PR-CONF-3：caller 显式传 `calibration_context = {"ready": False}`；§13 PR-CONF-4：agreement_status / conflict_level enum 标准化 |
| 当前禁止动作 | 不改 `_FORBIDDEN_FIELDS`；不改 `_LEVEL_RANK` 阈值（`< 0.4` low / `< 0.7` medium / 以上 high）；不改 `_combine_confidence` 保守 min combine 算法；不在 17I 引入 calibration table；不在 17I 改 `combined_confidence` 算法 |

### 6.2 候选模块的归属判断（不属于 CORE_CONFIDENCE）

| 模块 | 归属（17I 决定）|
|---|---|
| `services/consistency_layer.py` | NOT_CONFIDENCE_LAYER → 详见 §7（17J 决定 vs 吸收 vs freeze） |
| `services/final_decision.py` 中 `_confidence_from_result` | NOT_CONFIDENCE_LAYER → Branch 6 Final Report（17J 决定）|
| `services/projection_chain_contract.py` 中 consistency 字段嵌入 | NOT_CONFIDENCE_LAYER → Final Report / log_store helper（17J 决定）|
| `services/active_rule_pool_calibration.py` | DEEP_AUDIT_REQUIRED → 候选 calibration data source；§12.4 / §13 PR-CONF-7 |
| `services/contract_calibration_inputs.py` | DEEP_AUDIT_REQUIRED → 候选 calibration data input；§12.4 / §13 PR-CONF-7 |

> **重申**：这 5 个模块**全部不**属于 Branch 5 Confidence 主路径。详细
> 判断见 §7 / §12.4。

---

## 7. consistency_layer 归属判断

### 7.1 当前性质（与 17F §6.8 / 17G §16.4 / 17H §7.6 一致）

`services/consistency_layer.py`：

- docstring "Internal consistency checks across projection v2 layers"
- 输入：`exclusion_result` + `main_projection_result` + `peer_alignment` +
  `historical_match_result`
- 输出：`consistency_flag` (`conflict` / `mixed` / `consistent` / `unknown`) +
  `consistency_score` (0.0–1.0) + `conflict_reasons` (list[str]) + `summary`
- 当前**读 interim schema**：`projection.predicted_top1.state` 直接（不用
  `most_likely_state`）
- 与 `confidence_evaluator._compute_agreement` 功能**重叠**：都在判断
  projection vs exclusion 是否冲突

### 7.2 与 confidence_evaluator agreement 的差异

| 维度 | confidence_evaluator._compute_agreement | consistency_layer.build_consistency_layer |
|---|---|---|
| 输入 | projection_result + exclusion_result（standard schema） | exclusion_result + main_projection_result + peer_alignment + historical_match_result |
| 输出 | `agreement_status` (`aligned` / `partial_conflict` / `strong_conflict` / `unknown`) | `consistency_flag` (`conflict` / `mixed` / `consistent` / `unknown`) + `consistency_score` + `conflict_reasons` |
| schema 读取 | standard only（导致 unknown） | interim（实际工作） |
| 信号广度 | 二元 projection vs exclusion | 四元 projection + exclusion + peer + historical |

### 7.3 是否应迁入 Confidence Layer

❌ **否**。理由：

- consistency_layer 含 **historical match** 输入；07C §3.1 不让 confidence
  读 historical_match_result（confidence 用 historical_context 接 sample
  size，不接 match table）
- consistency_layer 含 **peer_alignment** 输入；这是 Feature evidence，
  Confidence 间接通过 projection / exclusion 的 peer summary 看到，
  **不**直接消费
- consistency_layer 输出 `consistency_score` 是 0.0–1.0 数值；与 confidence
  的 `combined_confidence.score` 性质不同

### 7.4 是否应归 Final Report Layer

⚠️ **倾向是**——但由 17J 最终决定。理由：

- consistency_layer 是**aggregation 之前的 cross-system check**（与 1.0
  §8 Branch 6 一致：Final Report 汇总三系统输出）
- consistency_layer 输出 `consistency_flag` / `conflict_reasons` 是
  Final Report `agreement_or_conflict_section` 的天然来源（07D §9）
- 与 16I §10.4 一致："不合并 consistency_layer"——保留为 LEGACY_ACTIVE_DEPENDENCY
  直到 architecture_orchestrator 接管；归属 17J 路径

### 7.5 是否应被 confidence_evaluator 吸收

❌ **否**。理由：

- 吸收后 confidence_evaluator 会接 historical_match / peer_alignment 输入
  → 违反 07C §3.1 输入白名单
- agreement 二元判断 vs consistency 四元判断**职责不同**；吸收会让
  confidence 边界扩大
- 17J 决定之前不动；二者并存不会互相破坏（confidence 输出 `agreement_status`
  即使 unknown，consistency 仍可独立工作）

### 7.6 当前阶段是否立即拆

❌ **不立即拆**。与 17D §11 / 17H §16 一致。

### 7.7 不拆时如何处理

- 17I：保留；声明 NOT_CONFIDENCE_LAYER
- 17J Final Report Plan 决定 (a) 归 Final Report aggregator pre-check (b)
  freeze 为 LEGACY_ACTIVE_DEPENDENCY (c) 由 architecture_orchestrator 取代
- 17I §13 PR-CONF-5 候选：仅加 docstring marker；不动逻辑

### 7.8 17I 立即动作

- **无**（与 17D §11 一致：本轮不改代码）
- §13 PR-CONF-5 候选：consistency_layer freeze marker（marker only）；
  不改输出；可推迟到 17J 之后

---

## 8. Confidence Result 标准化规则

### 8.1 顶层结构（schema_version `confidence_system_result.v1`，与 07C §9 一致；当前 confidence_evaluator 已实现）

```
{
    "schema_version": "confidence_system_result.v1",  # 当前已输出
    "confidence_date": "2026-05-10",                  # ISO date；UTC today fallback
    "target_date": "2026-05-10",                      # 与 inference target 对齐
    "system_name": "confidence_system",
    "question_answered": "system_reliability_evaluation",
    "symbol": "AVGO",                                 # uppercase
    "ready": True,                                    # 永远 True；levels 在 unknown 时仍是 well-formed dict

    "projection_confidence": {                        # 推演侧可信度
        "level": "low" | "medium" | "high" | "unknown",
        "score": float | None,                        # [0.0, 1.0] 或 None
        "reasoning": [...],                           # list[str] 推理记录
    },
    "exclusion_confidence": {                         # 否定侧可信度
        "level": "low" | "medium" | "high" | "unknown",
        "score": float | None,
        "reasoning": [...],
    },
    "agreement_status": "aligned" | "partial_conflict" | "strong_conflict" | "unknown",
    "conflict_level": "none" | "low" | "high" | "unknown",  # 当前实现；§11 标准化为 4 档
    "combined_confidence": {                          # 综合可信度
        "level": "low" | "medium" | "high" | "unknown",
        "score": float | None,
        "reasoning": [...],
    },

    "confidence_reasoning": [...],                    # 推理记录汇总
    "reliability_warnings": [...],                    # 降级 / 缺失原因（含 calibration 缺失）
    "sample_size_notes": [...],                       # 历史样本量
    "calibration_notes": [...],                       # calibration_context 状态
    "raw_evidence_refs": [...],                       # 经过 target_date cutoff 过滤

    "non_mutation_confirmations": {                   # 07C §5 / 07D §11 一致；当前已输出
        "projection_result_mutated": False,
        "exclusion_result_mutated": False,
    },
}
```

### 8.2 字段最小要求

| 字段 | 类型 | 备注 |
|---|---|---|
| `schema_version` | str | `"confidence_system_result.v1"`（当前已输出） |
| `confidence_date` | str (`YYYY-MM-DD`) | UTC today fallback |
| `target_date` | str (`YYYY-MM-DD`) | inference 目标日；用于 evidence cutoff |
| `system_name` | str | `"confidence_system"` |
| `question_answered` | str | `"system_reliability_evaluation"` |
| `symbol` | str | uppercase |
| `ready` | bool | 永远 `True`（well-formed dict 即使 levels = unknown） |
| `projection_confidence` / `exclusion_confidence` / `combined_confidence` | dict | `level` + `score` + `reasoning` |
| `agreement_status` | str | 4 档：`aligned` / `partial_conflict` / `strong_conflict` / `unknown` |
| `conflict_level` | str | 4 档（§11 标准化）：`none` / `low` / `medium` / `high` / `unknown`（当前实现仅 `none` / `low` / `high` / `unknown`；缺 `medium`——§13 PR-CONF-4 补） |
| `confidence_reasoning` / `reliability_warnings` / `sample_size_notes` / `calibration_notes` | list[str] | 推理 / 警告 / 样本注 / calibration 注 |
| `raw_evidence_refs` | list[str] | 经 target_date cutoff |
| `non_mutation_confirmations` | dict | 至少 2 项 boolean，全部 `False`（"未改写" = False mutation） |

### 8.3 缺失语义（与 07C §9.3 / 17F §8.3 / 17G §8.3 / 17H §8.3 一致）

- `level = "unknown"` → `score = None`（不捏造）
- `calibration_context` 缺失或 `ready = False` → 全部 levels 降级 `unknown`
- 缺失 system 输入 → 全部 levels 降级 `unknown` + 显式 `reliability_warnings`
- **不**用 `0.0` 表示缺失 score（必须 `None`）

### 8.4 不允许的字段（与 §4 / 07C §5 一致；当前 `_FORBIDDEN_FIELDS` 已锁）

- ❌ `most_likely_state` / `most_unlikely_state` / `predicted_top1` /
  `predicted_top2` / `state_probabilities`（Projection / Exclusion 输出）
- ❌ `triggered_rules` / `excluded_states` / `false_exclusion_risk`
  （Exclusion 输出）
- ❌ `combined_user_summary` / `agreement_or_conflict_section`（Final
  Report 输出）
- ❌ `simulated_trade` / `trading_action` / `buy` / `sell` / `hold` /
  `no_trade`
- ❌ `hard_*` / `forced_*` / `required_*` / `_PROTECTION_LAYER_CONNECTED` /
  `production_promotion`
- ❌ `modified_projection` / `modified_exclusion` / `projection_correction` /
  `exclusion_correction` / `final_report_mutation`

### 8.5 Confidence Layer 不直接生成 standard_projection_payload.v1

- 与 17F §8.4 / 17G §8.5 / 17H §8.5 / 17A standard payload 草案一致：
  Confidence Layer **只**生成 `confidence_result` 自身
- standard_projection_payload.v1 由未来 architecture_orchestrator（暂停；
  归 17J）组装

---

## 9. 与 standard_projection_payload.v1 的关系

### 9.1 17A / PR-B 已建立

- `services/standard_projection_payload.py` 已 in main（17A commit `9c779f8`）
- 含 `STANDARD_PAYLOAD_SECTIONS`（9 顶层 key）+ `validate_standard_projection_payload`
  纯函数 validator
- 当前**未接入** active path（与 16I §6 / 17F §8.4 / 17G §9.1 / 17H §9.1 一致）

### 9.2 Confidence Layer 只填充 confidence_result section

- Confidence Layer 输出符合 §8.1 草案的 `confidence_result`（已 implements
  `confidence_system_result.v1`）
- architecture_orchestrator（未来）把 confidence_result 放入 standard payload
  的 `confidence_result` section

### 9.3 Confidence Layer 不负责其它 section

- ❌ 不写 `metadata` / `feature_payload` / `projection_result` /
  `exclusion_result` / `final_report` / `review_stub` / `evaluation_stub` /
  `compatibility_metadata`
- 与 17F §9.3 / 17G §9.3 / 17H §9.3 体例一致

### 9.4 standard payload 草案对 Confidence 的约束

- standard_projection_payload validator 在 17A / PR-B 实现中要求
  `confidence_result` section 必须存在
- Confidence Layer 的输出必须能通过该 validator 的 shape check
- Confidence Layer **不**需要在自身实现中调用 validator

---

## 10. schema 读取规则（PR-E 实质）

> **本节是 17I 阶段最关键的设计决定**——把 PR-E confidence key 对齐
> 重新定位为 Confidence Layer 内部的 schema adapter 工作。

### 10.1 standard schema 优先（与 07C §9 / 16C §6 一致）

Confidence Layer 应**优先**读取以下 standard schema 字段：

**Projection standard**（17G §8 / §11 一致）：

- `projection_result.most_likely_state`
- `projection_result.ranked_states`
- `projection_result.state_probabilities`

**Exclusion standard**（17H §8 / §11 一致）：

- `exclusion_result.most_unlikely_state`
- `exclusion_result.excluded_states`
- `exclusion_result.ranked_unlikely_states`
- `exclusion_result.triggered_rules`

### 10.2 interim schema 兼容（fallback）

当 standard schema 字段缺失时，Confidence Layer **必须**fallback 到
interim schema：

**Projection interim**（17G §5 / §8.1 一致）：

- `projection_result.predicted_top1.state` → 视作 `most_likely_state`
- `[projection_result.predicted_top1.state, projection_result.predicted_top2.state]`
  → 视作 `ranked_states`
- `projection_result.state_probabilities`（已存在；通用）

**Exclusion interim**（17H §11 一致）：

- `exclusion_result.triggered_rule == "exclude_big_up"` → `most_unlikely_state = "大涨"`
- `exclusion_result.triggered_rule == "exclude_big_down"` → `most_unlikely_state = "大跌"`
- `exclusion_result.triggered_rule == None`（action=allow）→ `most_unlikely_state = None`
- `exclusion_result.excluded_state` （单数）→ 视作 `excluded_states[0]`
- `exclusion_result.excluded_states`（list）→ 直接使用

可复用 helper：`services/projection_chain_contract.excluded_state_from_result`
（17H §6.3）含完整 interim → 中文 state 映射；fallback adapter 可直接调用。

### 10.3 优先顺序示例

`_compute_agreement` 内部读取 most_likely_state 应是：

```
def _resolve_most_likely(proj):
    # 1. standard schema 优先
    state = _clean_str(proj.get("most_likely_state"))
    if state:
        return state
    # 2. interim schema fallback
    top1 = _as_dict(proj.get("predicted_top1"))
    return _clean_str(top1.get("state"))
```

### 10.4 完全缺字段 → unknown，但 reasoning 明确

- 当 standard 与 interim 都缺时：`agreement_status = "unknown"`
- `reliability_warnings` 显式：`"projection_result key missing: tried
  most_likely_state and predicted_top1.state"`
- **不**与 calibration 缺失 reason 混淆（calibration 缺失是单独的 unknown
  原因）

### 10.5 PR-E 实质 = §13 PR-CONF-2

- PR-E 的 17D §9 暂停状态由本节解锁
- PR-E 实施方式：`_compute_agreement` 加 fallback；3 个 caller 显式传
  `{"ready": False}`
- §13 PR-CONF-2 + PR-CONF-3 共同覆盖 PR-E 全部内容

### 10.6 不应让 Confidence 层长期依赖 interim schema

- 短期 17I 阶段：standard 优先 + interim 兼容
- 长期：当 17G PR-PROJ-2（main_projection 输出 standard keys）+ 17H PR-EXCL-2
  （exclusion_layer 输出 standard keys）落地后，confidence 内 interim
  fallback 可标 deprecated
- 二者全部入 main 之后某个 PR 删除 interim fallback；前提：用户单独审批

---

## 11. agreement_status / conflict_level 规则

### 11.1 agreement_status 枚举（当前已实现；17I 不改）

confidence_evaluator.py:154-178 当前实现：

| agreement_status | 触发条件（standard schema 假设；fallback 到 interim 见 §10）|
|---|---|
| `"strong_conflict"` | `most_likely_state == most_unlikely_state` |
| `"partial_conflict"` | `top2_likely & top2_unlikely` 非空（top2 有交集，但 top1 不同）|
| `"aligned"` | 以上都不命中 |
| `"unknown"` | projection_result 或 exclusion_result 为空，或关键 key 缺失 |

### 11.2 conflict_level 枚举（§13 PR-CONF-4 标准化）

当前 `_conflict_level_from_agreement`（line 181-188）：

| agreement_status | 当前 conflict_level | 17I 标准化目标 |
|---|---|---|
| `"aligned"` | `"none"` | `"none"` |
| `"partial_conflict"` | `"low"` | `"low"` |
| `"strong_conflict"` | `"high"` | `"high"` |
| `"unknown"` | `"unknown"` | `"unknown"` |
| — | （无 medium）| **新增** `"medium"`（§13 PR-CONF-4；保留作未来扩展，当前默认不触发） |

PR-CONF-4 仅扩展 enum，当前 4 档全部映射保持不变；为未来更细分 conflict
留 medium 槽位。

### 11.3 conflict 触发判断规则（必须 PR-CONF-2 之后才能正确生效）

- 如果 projection most_likely_state **命中** exclusion most_unlikely_state 或
  excluded_states → `strong_conflict` / `conflict_level = high`
- 如果 projection top state **不在** exclusion 排除集合中 → `aligned` /
  `conflict_level = none`
- top2 有交集（partial）→ `partial_conflict` / `conflict_level = low`
- 关键 key 缺失（standard + interim 都没）→ `unknown` / `conflict_level = unknown`

**不允许**：因为 standard schema mismatch 而 standard / interim key 都
存在但没读到 → 长期 `unknown`。这是 §10 + §13 PR-CONF-2 必须解决的根因。

### 11.4 agreement_status 不等于最终交易结论

- agreement_status 只是 Confidence 内部对**两个系统是否一致**的判断
- **不**等于 trading action / direction
- Final Report（Branch 6）展示 agreement，但**不**根据 agreement 改写
  projection / exclusion 结论（07D §6 / §11）

---

## 12. calibration_context 规则

### 12.1 calibration_context 是 Confidence Layer 的输入 context

- 来自调用方（home_terminal / projection_orchestrator_v2 / 未来
  architecture_orchestrator）
- 含 `ready` flag + `projection_score` + `exclusion_score` + `notes` +
  `evidence_refs`

### 12.2 当前没有真实 calibration 接入；caller 必须显式传 `{"ready": False}`

**当前 3 个 caller 全部不传**（§5.3）：

- `home_terminal_orchestrator.py:169`
- `projection_orchestrator_v2.py:483`
- `projection_orchestrator_v2.py:585`

evaluator 走 line 360-363 fallback：`reliability_warnings.append("calibration_context
缺失，可信度评估降级为 unknown。")`

§13 PR-CONF-3 要求 caller **显式**传 `calibration_context = {"ready":
False}`：

- evaluator 走 line 368-375 fallback：`reliability_warnings.append("calibration_context.ready=False，
  可信度评估降级为 unknown。")`
- 这是更明确的 contract："caller 知道自己没接入 calibration，evaluator
  按 ready=False 处理"

### 12.3 不能 silent default

- evaluator 已实现 not-silent（任一 fallback 都加 `reliability_warnings` +
  `calibration_notes`）
- caller 必须显式：不能依赖 evaluator 的 missing fallback；caller 必须
  传 `{"ready": False}` 显示声明

### 12.4 confidence_result 应体现 calibration_status / calibration_notes

当前 confidence_result 已含 `calibration_notes` (list[str])；其内容来自：

- evaluator 自身的 fallback notes
- `calibration.notes`（如 caller 传入）

§13 PR-CONF-3 不改 schema；只改 caller 行为。

### 12.5 不在本层计划中接真实 DB calibration

- 17I **不**接 `services/active_rule_pool_calibration` /
  `contract_calibration_inputs` 进 active path
- 这两个模块当前 16G UNKNOWN（DEEP_AUDIT_REQUIRED）
- 接入路径由 §13 PR-CONF-7（calibration data source plan）决定；与
  Branch 8 Evaluation（17L）协同

### 12.6 真实 calibration / historical win-rate 属 Evaluation Layer 或后续单独计划

- Evaluation（Branch 8；17L）负责离线 calibration 计算（accuracy /
  calibration / agreement / win-rate 在历史上的表现，与 1.0 §8 Branch 8
  / 07C §3.2 一致）
- Evaluation 的输出以**权重 / 校准表**形式回到 Confidence System；**不**
  沿其他路径回流（与 1.0 §8 Branch 8 / §13 hard rule 5 一致）
- Confidence Layer 通过 `calibration_context` 接收这些权重；**不**自己
  计算 calibration

---

## 13. PR-E 重新定位

### 13.1 PR-E confidence key 对齐方向正确

- PR-E（16I §9）定义：让 confidence_evaluator 在 standard schema 缺失时
  fallback 到 interim schema，且 caller 显式传 `calibration_context`
- 17D §9 已暂停 PR-E：归入 17I Confidence Layer Plan

### 13.2 PR-E 不能作为小修小补直接执行

- 与 17D §10 / §11 一致：不直接做 confidence key patch
- 必须先有 17I（本文件）入 main
- 必须分解为多个 PR-CONF-* 协同执行

### 13.3 PR-E 的实质分解

| 16I §9 PR-E 内容 | 17I 重新定位 | PR 候选 |
|---|---|---|
| standard schema 优先（`most_likely_state` / `ranked_states` / `most_unlikely_state` / `ranked_unlikely_states`） | §10.1 / §10.3 schema adapter | §13 PR-CONF-2 |
| interim schema 兼容（`predicted_top1.state` / `triggered_rule` / `excluded_state`） | §10.2 fallback | §13 PR-CONF-2 |
| `calibration_context = {"ready": False}` 显式 fallback | §12.2 caller 显式传 | §13 PR-CONF-3 |
| 不允许 silent default | §12.3 / 当前 evaluator 已实现 | 维护现状 |
| 不改写 projection / exclusion | §3.2 / §4 / `_FORBIDDEN_FIELDS` | 维护现状 |

### 13.4 PR-E 前置条件

- 17I 已入 main（前置）
- PR-CONF-1（contract validator）已合（推荐前置；不强制）
- 18A 阶段用户单独审批

### 13.5 PR-E 只允许改 Confidence Layer 相关文件

允许动：

- `services/confidence_evaluator.py`（schema fallback 实现）
- `services/home_terminal_orchestrator.py:169`（caller 显式传 calibration_context）
- `services/projection_orchestrator_v2.py:483, 585`（caller 显式传）
- 对应新增 / 改的 tests

不允许动（与 17D §10 一致）：

- ❌ `services/main_projection_layer.py`（不为 PR-E 而改 schema 输出；归
  17G PR-PROJ-2）
- ❌ `services/exclusion_layer.py`（不为 PR-E 而改 schema 输出；归 17H
  PR-EXCL-2）
- ❌ `services/final_decision.py`（归 17J）
- ❌ UI / bridge / orchestrator 业务逻辑

### 13.6 PR-E 是否执行 / 如何拆分 / 何时执行

- 由 17I 后续 implementation PR（§13 PR-CONF-2 + PR-CONF-3）决定
- 用户单独审批；不在 17I 文档自动批准
- **17I 入 main 后**才能讨论；**18A 阶段**才能开 PR

---

## 14. Confidence Layer 测试策略

后续 Confidence Layer 实现 PR 必须满足以下测试要求：

### 14.1 standard schema read tests

- projection_result 含 `most_likely_state` / `ranked_states` →
  agreement_status 正确派生（aligned / partial_conflict / strong_conflict）
- exclusion_result 含 `most_unlikely_state` / `ranked_unlikely_states` →
  agreement 正确派生

### 14.2 interim schema compatibility tests

- projection_result 仅含 `predicted_top1.state`（standard 缺）→ fallback
  到 interim；agreement 正确
- exclusion_result 仅含 `triggered_rule = "exclude_big_up"`（standard 缺）
  → fallback 映射 `most_unlikely_state = "大涨"`；agreement 正确
- exclusion_result `triggered_rule = "exclude_big_down"` → `"大跌"`
- exclusion_result `triggered_rule = None`（action=allow）→ `most_unlikely_state
  = None`；agreement 走 unknown 或单边判断

### 14.3 conflict case tests

- projection top1 = "大涨" + exclusion most_unlikely = "大涨" →
  `strong_conflict` / `conflict_level = high`
- projection ranked top2 = ["大涨", "小涨"] + exclusion ranked unlikely
  top2 = ["小涨", "震荡"] → `partial_conflict` / `conflict_level = low`

### 14.4 aligned / compatible case tests

- projection top1 = "大涨" + exclusion most_unlikely = "大跌" → `aligned`
  / `conflict_level = none`

### 14.5 calibration_context ready=False tests

- caller 显式传 `{"ready": False}` → reliability_warnings 含
  `"calibration_context.ready=False"`；levels 全部 `unknown`
- caller 不传 → reliability_warnings 含 `"calibration_context 缺失"`
  （当前已有；维护现状）
- caller 传 `{"ready": True, "projection_score": 0.5, "exclusion_score": 0.6}`
  → levels 派生为 `medium` / `medium`

### 14.6 non-mutation tests

- `build_confidence_result` 不修改 projection_result / exclusion_result 入参
- 输出 `non_mutation_confirmations.projection_result_mutated = False` /
  `exclusion_result_mutated = False`
- 输入 dict id 与输出 dict id 不同

### 14.7 forbidden output fields tests

- 输出 dict 不含 `_FORBIDDEN_FIELDS` 任一项
- AST-level grep：source 中不出现 `most_likely_state` / `most_unlikely_state`
  作为输出 key（当前已实现 defense in depth `result.pop(forbidden, None)`）

### 14.8 no projection / exclusion generation tests

- Confidence 输出**不含** `projection_result` / `exclusion_result` /
  `predicted_top1` / `triggered_rules` 等被禁字段
- 即使 reasoning 文本提及这些字段名，输出 dict key 不能是这些名

### 14.9 no trading fields tests

- 输出 dict 字段集合中**不含**：`simulated_trade` / `trading_action` /
  `buy` / `sell` / `hold` / `no_trade` / `hard_*` / `forced_*` /
  `required_*` / `_PROTECTION_LAYER_CONNECTED` / `production_promotion`
- 与 §4 / `_FORBIDDEN_FIELDS` 一致

### 14.10 no hard / forced / required fields tests

- 与 §14.9 重叠；显式扩展为 AST-level grep

### 14.11 evidence cutoff tests

- `target_date = "2026-05-10"` + evidence_refs 含 `"ref:2026-05-15"` →
  cutoff 后该 ref 不出现在输出
- 当前 `_filter_evidence_by_target_date` 已实现；维护现状

### 14.12 no LLM / no UI / no future outcome tests

- 不 import `anthropic` / `openai`
- 不 import `streamlit` / `ui.*`
- 不读取 future outcome（在线 inference 路径）
- evidence cutoff 已实现 anti-future（line 277-306）

### 14.13 baseline & regression

- 每个 PR-CONF-* 必须以 Step 15 baseline 为起点（**3256 passed, 10
  skipped, 0 failed, 26 warnings, 94 subtests**）
- 新增测试数显式累加到 passed
- warnings / subtests 数变化必须**显式说明**

---

## 15. Confidence Layer 后续实现 PR 候选

> **本节是 PR 候选清单，本轮 17I 不执行任一项**。最早 18A 由用户单独
> 决定执行哪个、何时执行、按什么顺序执行。

| 序号 | 名称 | 性质 | 目标 | 文件范围 | 测试 | 风险 | 是否必须先做 |
|---|---|---|---|---|---|---|---|
| **PR-CONF-1** | confidence_result contract validator helper | 代码（新增 helper） | 新增 `services/confidence_result_contract.py`：定义 `CONFIDENCE_RESULT_FIELDS` + `validate_confidence_result(result) -> list[str]` 纯函数 validator；体例与 17A `standard_projection_payload.v1` / 17F PR-FEATURE-1 / 17G PR-PROJ-1 / 17H PR-EXCL-1 一致；**不**改 confidence_evaluator 实现 | `services/confidence_result_contract.py`（新增）+ `tests/test_confidence_result_contract.py`（新增） | focused + full pytest | L | 不强制；推荐第一项 |
| **PR-CONF-2** | confidence_evaluator schema adapter（PR-E 实质 part 1）| 代码（在 `_compute_agreement` 加 fallback） | 让 `_compute_agreement` 在 standard schema (`most_likely_state` / `most_unlikely_state` / `ranked_states` / `ranked_unlikely_states`) 缺失时 fallback 到 interim schema (`predicted_top1.state` / `triggered_rule` 映射 + `excluded_state` / `excluded_states`)；**不**改 `_FORBIDDEN_FIELDS` / `_LEVEL_RANK` / `_combine_confidence` 算法 | `services/confidence_evaluator.py`（仅 `_compute_agreement` + 私有 helper）+ `tests/test_confidence_evaluator_schema_compat.py`（新增） | focused + full pytest；4 schema case 全部命中 | M | 不强制；与 PR-CONF-1 协同 |
| **PR-CONF-3** | explicit calibration_context ready=False（PR-E 实质 part 2）| 代码（**仅** caller 显式传） | 在 `home_terminal_orchestrator.py:169` / `projection_orchestrator_v2.py:483, 585` 三处 `build_confidence_result` 调用追加 `calibration_context={"ready": False}`；**不**改 evaluator；**不**改其它字段 | 3 个 caller 文件（仅 kwargs）+ tests | focused + full pytest；reliability_warnings 含 `"ready=False"` 而非 `"缺失"` | L | 不强制；可与 PR-CONF-2 协同 |
| **PR-CONF-4** | agreement_status / conflict_level enum standardization | 代码（仅 enum 扩展） | 在 `_conflict_level_from_agreement` 加 `medium` 槽位（保留作未来更细分 conflict；当前 4 档全部 mapping 不变）；显式 docstring 注释 5 档枚举完整集合；**不**触发 medium 实际行为 | `services/confidence_evaluator.py`（仅 enum 注释 + helper） | full pytest byte-stable | L | 不强制 |
| **PR-CONF-5** | consistency_layer 归位 / merge / freeze marker | 代码（**仅** docstring） | 给 `services/consistency_layer.py` 顶部 docstring 加 marker：`NOT_CONFIDENCE_LAYER —— belongs to Branch 6 Final Report aggregator pre-check (per 17J)`；与 17J 协同；**不**改逻辑 | 仅 docstring | full pytest byte-stable | L | 不强制；可推迟到 17J 之后 |
| **PR-CONF-6** | confidence non-mutation / forbidden field boundary tests | 代码（仅 tests） | 扩展现有 `tests/test_confidence_evaluator.py` boundary tests：(a) AST-level grep `_FORBIDDEN_FIELDS` 覆盖（19 项全） (b) non-mutation under conflict + non-mutation under aligned + non-mutation under unknown 分别测 (c) forbidden import 集合扩展（不 import main_projection / exclusion / final_decision / predict）；**不**改 evaluator 实现 | tests only | focused + full pytest | L | 不强制 |
| **PR-CONF-7** | calibration data source plan（与 Evaluation Layer 协同） | **文档 only**（不是代码 PR） | 写 `tasks/record_17i_pr_conf_7_calibration_data_source.md`：决定 `services/active_rule_pool_calibration.py` / `services/contract_calibration_inputs.py` 是否接入 active path；与 17L Evaluation Plan 共同决定 | doc only | n/a | L | 不强制；可推迟到 17L 之后 |

### 15.1 候选 PR 之间的依赖

- PR-CONF-1 → PR-CONF-2 / PR-CONF-4：先有 contract validator，再做 schema
  adapter / enum 扩展
- PR-CONF-2 + PR-CONF-3 = **PR-E 实质** 完整内容；二者可任意顺序，但都
  应在 PR-CONF-1 之后
- PR-CONF-5：需要 17J Final Report Plan 入 main 后才能最终决定 marker 内容
- PR-CONF-6：可独立做；推荐在 PR-CONF-2 之后（验证 schema fallback 不破
  forbidden）
- PR-CONF-7：文档 only；可与 17L 协同启动；可推迟
- 任何**代码** PR-CONF-* 都依赖 **17I 已入 main**（前置条件）

### 15.2 候选 PR 都不能做的事

- ❌ 不改 `_FORBIDDEN_FIELDS`（只能维持现状或加 defense；不能扩 / 删）
- ❌ 不改 `_LEVEL_RANK` 阈值（`< 0.4` low / `< 0.7` medium）
- ❌ 不改 `_combine_confidence` 保守 min combine 算法
- ❌ 不改 `non_mutation_confirmations` schema（保持 2 项 boolean）
- ❌ 不为 PR-E 顺手改 main_projection / exclusion_layer 输出（归 17G
  PR-PROJ-2 / 17H PR-EXCL-2）
- ❌ 不动 final_decision / projection_chain_contract 业务逻辑
- ❌ 不动 V2 orchestrator / home_terminal_orchestrator 业务逻辑（caller 只
  改 build_confidence_result kwargs；其它代码不动）
- ❌ 不切换默认 `run_predict` 路径
- ❌ 不引入 trading / hard / forced / required
- ❌ 不复活 `continuous_smoothing*` / `archive/legacy/root_stubs/*`
- ❌ 不修改 `.gitignore`
- ❌ 不处理 `avgo_agent.db`（含 backup）
- ❌ 不处理 handoff / logs / DB backup / `.claude/worktrees/`
- ❌ 不接真实 calibration table（PR-CONF-7 仅 plan）

---

## 16. 与 Projection / Exclusion / Final Report 的交接

### 16.1 数据流方向（与 1.0 §9 / 17F §15 / 17G §15 / 17H §12 一致）

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
                                          ──► confidence_result
        │                 │                 │
        └────────┬────────┴────────┬────────┘
                 ▼                 ▼
           Branch 6 Final Report Layer
            （仅 aggregate / 不 mutate）
```

### 16.2 Projection Layer 输出 projection_result

- 与 17G §3.1 / §8 一致

### 16.3 Exclusion Layer 输出 exclusion_result

- 与 17H §3.1 / §8 一致

### 16.4 Confidence Layer 只读二者，输出 confidence_result

- 与 §3.1 / §8 一致
- **只读**：`build_confidence_result` 不修改 projection_result /
  exclusion_result 入参（当前已实现）
- **不**反向 import Projection / Exclusion 业务模块

### 16.5 Final Report 之后汇总，不改 confidence_result

- 与 07D §5 / §6 / §7 / §11 一致
- Final Report 在 `non_mutation_confirmations` 中显式声明未改 confidence
- final_decision.py 中 `_confidence_from_result` 把
  `combined_confidence.level` 输出为 `final_confidence`——这是 display
  passthrough，不是 mutation

### 16.6 Review / Evaluation 事后评价 confidence calibration，不影响当次 confidence_result

- 与 1.0 §8 Branch 7 / Branch 8 一致
- Evaluation 离线 calibration 输出**权重 / 校准表**，通过
  `calibration_context` 回到 Confidence；**不**沿其他路径回流
- Review 复盘 confidence calibration 与真实命中率，**不**改当次结果

### 16.7 UI 只展示，不重算 confidence

- 与 1.0 §8 Branch 9 一致
- UI 通过 final_decision 间接看到 `final_confidence = combined_confidence.level`；
  **不**重算

---

## 17. 清场 / 隔离建议

> **本节按 16H 决策表 8 个标签给出 Confidence Layer 范畴内的清场建议**。
> 本轮**不**执行任何清场动作。

### 17.1 KEEP（Confidence Layer CORE）

- `services/confidence_evaluator.py`

### 17.2 NOT_CONFIDENCE_LAYER（声明非 Confidence；归其它层）

- `services/consistency_layer.py` → 17J Final Report
- `services/final_decision.py`（confidence display 部分）→ 17J Final Report
- `services/projection_chain_contract.py`（consistency 嵌入部分）→ 17J
  Final Report / log_store helper

### 17.3 DEEP_AUDIT_REQUIRED（calibration data source 候选）

- `services/active_rule_pool_calibration.py`（16G UNKNOWN）
- `services/contract_calibration_inputs.py`
- 与 17L Evaluation Layer 协同；§13 PR-CONF-7 plan 决定接入路径

### 17.4 LEGACY_ACTIVE_DEPENDENCY（caller；不进 9 分支正式架构）

- `services/home_terminal_orchestrator.py`（caller；归 17J）
- `services/projection_orchestrator_v2.py`（caller；归 17J）

### 17.5 MIGRATE_LATER

- §17.2 / §17.3 / §17.4 全部模块 → 对应层 Plan 接管
- 17I 阶段无主动 migration

### 17.6 ARCHIVE_IN_REPO

- 无 Confidence Layer 范畴的 archive 候选（与 16H / 17E §15.5 / 17F §16.5 /
  17G §16.8 / 17H §15.5 一致）

### 17.7 QUARANTINE

- 无 Confidence Layer 范畴的 quarantine 候选（CORE 状态健康）

### 17.8 DELETE_NOW

- **空**（与 16H §13 / 17E §15.7 / 17F §16.7 / 17G §16.11 / 17H §15.8
  一致）

### 17.9 DELETE_LATER

- 无 Confidence Layer 范畴的 delete 候选（17I 阶段）

### 17.10 MIGRATE_CALLER_FIRST

- 无（CORE_CONFIDENCE 模块不是 Bridge）
- §17.4 caller 迁移由对应层 Plan（17J）决定

### 17.11 MOVE_OUTSIDE_REPO

- 无 Confidence Layer 范畴

> **重申**：任何文件删除 / 移动 / archive 必须等 16H 规则 + 17D §11 + 用户
> 单独确认。17I 仅给出**建议**，**不**执行。

---

## 18. 不允许事项

**17I 起，Confidence Layer 范畴内**严格禁止：

- ❌ 不改代码（无 `.py` 文件被修改；本轮 0 修改）
- ❌ 不跑数据
- ❌ 不跑 replay / 不跑 validation / 不跑 historical evaluation
- ❌ 不改 DB / 不改 DB schema
- ❌ 不迁 Final Report / Review / Evaluation / UI（各层 Plan 自负其责）
- ❌ 不接 trading / 不输出 buy / sell / hold / hard / forced / required
- ❌ 不进入 3R-5 / 3R-6（1.0 §12 / 16I §15 / 17D §11 / 17E §16 / 17F §17 /
  17G §17 / 17H §16 / 本轮再次重申）
- ❌ 不启动任何代码 PR（PR-CONF-* 候选要等 18A）
- ❌ 不修改 `.gitignore`
- ❌ 不处理 `avgo_agent.db`（含 backup）
- ❌ 不处理 handoff / logs / DB backup / `.claude/worktrees/`
- ❌ 不复活 `continuous_smoothing*` / `archive/legacy/root_stubs/*` /
  promotion 三模块
- ❌ 不污染 2026-01-01 之后 final holdout
- ❌ 不借 17I 顺手做 Data / Feature / Projection / Exclusion / Final
  Report / Review / Evaluation / UI 范畴改动
- ❌ **不直接启动 PR-E confidence key patch**（与 17D §9 / 17H §16 一致；
  必须分解为 PR-CONF-2 + PR-CONF-3，且必须等 17I 入 main + 18A 单独审批）
- ❌ 不启动 UI / bridge / orchestrator 实现任务（与 17D §10 一致）
- ❌ 不默认迁移 `run_predict` 到 V2（hard rule 1.0 §6.4 / §12）
- ❌ 不打开 16I PR-G bridge marker（与 17D §10.1 一致）
- ❌ 不打开 16I PR-F architecture_orchestrator MVP（与 17D §10.3 一致）
- ❌ 不允许 `confidence_result → projection / exclusion` 回流
- ❌ 不在 17I 接真实 calibration table

> 与 17D §11 / 17E §16 / 17F §17 / 17G §17 / 17H §16 一致；本轮再次锁定。

---

## 19. 推荐下一步

> **首选**：**Step 17J：Final Report Layer Rebuild Plan**

理由（与 17D §12 / 17E §17 / 17F §18 / 17G §18 / 17H §17 一致 + 17I 实战
观察）：

- Confidence Layer 计划（17I）已就位
- 数据流方向是 Data → Feature → {Projection, Exclusion, Confidence} →
  **Final Report** → ...（1.0 §9 / 16C §3）
- 按九分支编号顺序，下一层是 Final Report（Branch 6）
- **17J 的工作量大**：17J 必须接管
  - `services/final_decision.py`（aggregator + display formatter）
  - `services/consistency_layer.py`（cross-system consistency check；
    17F §6.8 / 17G §16.4 / 17H §15.3 / 17I §7 一致）
  - `services/projection_chain_contract.build_unified_projection_payload`
    / `build_prediction_log_record` / `excluded_state_from_result`（17F §7.6 / 17G §6.3 / 17H §6.3 一致）
  - `services/big_up_contradiction_card.py` / `services/big_down_tail_warning.py`
    （display warning；17H §15.3 / §7.3 / §7.4）
  - `services/predict_summary.py`（readable summary helper；17G §16.4）
  - `services/projection_narrative_renderer.py` /
    `services/projection_three_systems_renderer.py`（17G §16.4）
  - V2 / home_terminal orchestrator 中 final report 组装部分（属
    LEGACY_ACTIVE_DEPENDENCY；最终由 architecture_orchestrator 替代）
  - architecture_orchestrator MVP 决策（暂停归 17J；与 17D §10.3 一致）
- 17J 入 main 之前，**不**允许在 Final Report Layer 范畴开任何代码 PR

**不推荐**：

- 不推荐跳到 17K / 17L / 17M（必须先有 Final Report Plan）
- 不推荐借 17I / 17J 做代码改动（与 17D §11 一致）
- 不推荐重启 16I PR-E / PR-F / PR-G / PR-H（必须等对应层 Plan）
- 不推荐解锁 3R-5 / 3R-6（1.0 §12 7 项前提仍未全部满足）
- 不推荐立刻做 PR-CONF-* 任一项（与 17I 协同更合算）
- 不推荐立刻做 PR-E（必须等 17I 入 main + 18A 审批）

> **明确**：本轮 17I 推荐的下一步**只有一个候选**——17J Final Report
> Layer Rebuild Plan。

---

## 20. 严守边界

本轮 Step 17I **只**写 Confidence Layer Rebuild Plan：

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
- ❌ 未启动任何代码 PR（PR-CONF-* / PR-E 候选要等 18A）
- ❌ 未直接做 PR-E confidence key 对齐（归 §13 PR-CONF-2 + PR-CONF-3）
- ❌ 未启动 UI / bridge / orchestrator 实现任务
- ❌ 未做任何局部 patch
- ❌ 未 commit / 未 push（按本轮指令）

唯一新增文件：[tasks/record_17i_confidence_layer_rebuild_plan.md](tasks/record_17i_confidence_layer_rebuild_plan.md)（本文件）。

后续修改路径：任何对 §3 职责定义 / §4 禁止事项 / §5 inventory / §6
CORE_CONFIDENCE / §7 consistency_layer 归属 / §8 confidence_result 标准化 /
§9 与 standard payload 关系 / §10 schema 读取规则 / §11 agreement_status /
conflict_level / §12 calibration_context / §13 PR-E 重新定位 / §14 测试
策略 / §15 PR 候选 / §16 与 Projection / Exclusion / Final Report 交接 /
§17 清场建议 / §18 禁止事项 / §19 下一步 的调整，都必须**显式更新本文件**；
同时检查是否需要同步更新 1.0 / 16C / 16D / 16I / 17D / 17E / 17F / 17G /
17H 与 17J（17J 入 main 后）。
