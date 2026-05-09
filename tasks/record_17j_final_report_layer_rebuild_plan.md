# 17J记录：Final Report Layer Rebuild Plan

> 本记录是 **Step 17J：Final Report Layer 重建计划**——九分支按层重建
> 中的**第六层**（Branch 6）。1.0 canonical / 16A blueprint / 16B inventory /
> 16C target dataflow & contract decision / 16D isolation & quarantine
> plan / 16E core chain refactor plan / 16F no-patching principle / 16G
> full module decomposition standup / 16H repository clearing decision
> table / 16I core chain rebuild execution plan / 17A PR-B standard
> payload skeleton / 17B PR-C peer_alignment 抽公共模块 / 17C PR-D
> main_projection 去 `exclusion_result` 形参 / 17D layer-by-layer rebuild
> governance / 17E Data Layer Rebuild Plan / 17F Feature Layer Rebuild
> Plan / 17G Projection Layer Rebuild Plan / 17H Exclusion Layer Rebuild
> Plan / 17I Confidence Layer Rebuild Plan 已全部入 main（main 最新
> commit `7a2cd46`）。
>
> 本轮**只**写计划文档：未改业务代码、未新增测试、未删除文件、未移动
> 文件、未修改 `.gitignore`、未处理 handoff、未处理 logs / DB backup /
> `.claude/worktrees/`、**未处理 `avgo_agent.db`**、未跑 replay /
> validation / historical evaluation、未写 DB / 未改 DB schema、未默认
> 迁移 `run_predict` 到 V2、未接 trading、未输出 buy / sell / hold /
> hard / forced / required、未进入 3R-5 / 3R-6、未启动任何代码 PR、
> 未直接做 architecture_orchestrator MVP、未直接迁 UI、未启动 bridge
> 清理、未做任何局部 patch、未 commit / 未 push。
>
> 唯一 deliverable：本文件。
>
> **本记录优先级**：与 17E / 17F / 17G / 17H / 17I / 17K ~ 17M 各层 Plan
> 同级；与 1.0 / 16A / 16C / 16D / 16F / 16I / 17D / 17E / 17F / 17G /
> 17H / 17I 协同。冲突仲裁路径与 1.0 §14 / 17D §13 一致：旧 records 若
> 与 17J 在 Final Report Layer 范畴冲突，**以 17J 为准**。

---

## 1. Step 17J 目的

把九分支按层重建从 Confidence Layer（17I）推进到**第六层（Final Report
Layer）的具体重建计划**。

**本轮只回答**：

- Final Report Layer 当前长什么样（模块 inventory + active path）
- Final Report Layer 目标长什么样（保留 / 迁移 / 隔离 / 删除候选）
- Final Report Layer 与上下游的边界（Feature / Projection / Exclusion /
  Confidence ↑（**只读**）；Review / Evaluation / UI ↓；**不**改写任一
  上游输出）
- `final_report` 标准化规则（与 1.0 §8 Branch 6 / 07D §9 一致）
- `final_decision.py` 归属判断
- `consistency_layer.py` 在 Final Report Layer 内的归属（与 17F §6.8 /
  17G §16.4 / 17H §15.3 / 17I §7 一致）
- contradiction / warning card（big_up_contradiction_card / big_down_tail_warning）
  归属
- `projection_chain_contract.py` 跨层 helper 归属（与 17F §7.6 / 17G §6.3 /
  17H §6.3 / 17I 一致）
- **architecture_orchestrator MVP** 归属判断（与 17D §10.3 / 16I §10 一致）
- Final Report Layer 后续可能的代码 PR 候选（**不**执行）
- 与 Review / Evaluation / UI 的交接

**本轮不回答**：

- 不写 Review / Evaluation / UI 计划（17K ~ 17M）
- 不开任何代码 PR（最早 18A）
- 不动 `avgo_agent.db`、`.gitignore`、handoff、logs、DB backup、worktrees
- 不直接做 architecture_orchestrator MVP（与 17D §10.3 一致；17J 仅做归属
  判断）
- 不直接迁 UI（与 17D §10.2 一致；归 17M）
- 不启动 bridge 清理（与 17D §10.1 一致）

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
| main 最新 commit | `7a2cd46` |
| worktree 唯一 deliberate untracked | `.claude/handoffs/task_089_post_pr_cleanup.md` |
| 战略阶段 | 从 Confidence Layer plan（17I）→ **Final Report Layer plan（17J 本轮）** |
| 3R-5 / 3R-6 | ❌ 仍然不允许进入 |
| 第一个按层实现 PR（18A）| ❌ 仍未 |
| architecture_orchestrator MVP | ⏸️ 暂停（17D §10.3 / 16I PR-F）；17J 入 main 后归入 §13 / PR-FINAL-7 |
| PR-E confidence key 对齐 | ⏸️ 暂停（17D §9）；归 17I PR-CONF-2 / PR-CONF-3 |

**17D §6 PR 准入规则提醒**：

- 任何代码 PR 必须绑定九分支某一层 + 引用对应层 Plan §
- 17J 入 main 后，Final Report Layer 范畴的 PR 才**有资格**被讨论
- 17J 本身**不**自动批准任何 PR；PR-FINAL-* / architecture_orchestrator
  MVP 仍需 18A 单独审批

**层间依赖**：

- 17J 依赖 17F / 17G / 17H / 17I（已就位）
- 17J **不**依赖 17K ~ 17M（可独立写完）
- 17J 与 17M（UI Layer）在 final_report → UI passthrough 字段约定上有
  协同点；17M 入 main 后正式 cross-reference

---

## 3. Final Report Layer 职责定义

**Final Report Layer（Branch 6）只回答一件事**：

> **"把 feature / projection / exclusion / confidence 四个上游输出**只读
> 汇总**，输出 `final_report`。"**

### 3.1 只做的事（与 1.0 §8 Branch 6 / 07D §3.1 一致）

- 读取 Feature Layer 的 `feature_payload`（**只读**）
- 读取 Projection Layer 的 `projection_result`（**只读**）
- 读取 Exclusion Layer 的 `exclusion_result`（**只读**）
- 读取 Confidence Layer 的 `confidence_result`（**只读**）
- 读取三系统的 `raw_evidence_refs`（用于 `evidence_summary`）
- 读取 display metadata / formatting rules / risk disclosure 模板文本
- **汇总**三系统结果
- **生成**一句话结论 / `combined_user_summary`
- **生成** `key_points` / `risks` / `evidence_summary` /
  `agreement_or_conflict_section`
- **展示** Projection / Exclusion / Confidence 的一致与冲突
- **汇总** contradiction card / warning card（来自 Branch 4 Exclusion 之外
  的 display warning helper；详见 §9）
- **生成** `non_mutation_confirmations`：声明 final_report 未改写任一上游
  输出（与 07D §11 体例一致）
- **为 UI / Review / Evaluation 提供稳定读接口**（passthrough）

### 3.2 不做的事（与 1.0 §8 Branch 6 / 07D §3.2 / §5 / §6 / §7 / §8 / §11 一致）

- ❌ **不**生成 `projection_result`（归 Branch 3）
- ❌ **不**生成 `exclusion_result`（归 Branch 4）
- ❌ **不**生成 `confidence_result`（归 Branch 5）
- ❌ **不**改写 `feature_payload` / `projection_result` / `exclusion_result` /
  `confidence_result`
- ❌ **不**重新预测 / 不重新否定 / 不重新计算 confidence
- ❌ **不**做 review / lesson（归 Branch 7）
- ❌ **不**做 evaluation（accuracy / win-rate 归 Branch 8）
- ❌ **不**做 UI 布局 / Streamlit rendering（归 Branch 9）
- ❌ **不**输出 trading action / hard / forced / required
- ❌ **不**调用 LLM 生成新判断（`ai_summary` 仅在显式 opt-in 时才允许做
  source-attributed explanation；详见 §6.6）
- ❌ **不**写 DB / 不改 DB schema
- ❌ **不**直接运行 replay
- ❌ **不**直接接 broker API
- ❌ **不**读取 future outcome（在线 inference 路径）
- ❌ **不**允许 `final_report → projection / exclusion / confidence` 回流
  （07D §11）

### 3.3 输入 / 输出（白名单）

**输入**（与 07D §3.1 一致）：

- `projection_result`（来自 Branch 3，**只读**）
- `exclusion_result`（来自 Branch 4，**只读**）
- `confidence_result`（来自 Branch 5，**只读**）
- 三系统的 `raw_evidence_refs`
- display metadata / formatting rules / risk disclosure 模板文本
- 可选：`feature_payload`（来自 Branch 2；Final Report 通常通过 projection /
  exclusion 间接看到 feature evidence；不应是主输入）

**输出**（schema_version `final_report_aggregator_result.v1`，与 07D §9 /
当前 final_decision.py 已部分实现一致）：

- `final_report` dict（结构详见 §11）

**禁止输入**（与 07D §3.2 / §11 / 1.0 §9 一致）：

- ❌ `review_record` / `evaluation_report`（事后路径；不进 final_report）
- ❌ Future outcome（在线 inference 路径）
- ❌ 2026-01-01 之后 final holdout（在线 inference）
- ❌ Trading 输入 / broker / position state

---

## 4. Final Report Layer 禁止事项

Final Report Layer **永久禁止**输出 / 引入以下任一：

| 类别 | 禁止项 | 锚点 |
|---|---|---|
| Mutation 任一上游 | `feature_payload` / `projection_result` / `exclusion_result` / `confidence_result` 写回 | 07D §5 / §6 / §7 / §11 |
| 重新生成上游字段 | `most_likely_state` / `most_unlikely_state` / `state_probabilities` / `agreement_status`（重算）/ `combined_confidence`（重算）/ `triggered_rules` | 07D §6 |
| 调用上游模块重新计算 | import `services.main_projection_layer` / `services.exclusion_layer` / `services.confidence_evaluator` 在 final_decision **内部**重新调用（即 final_decision 自己跑一遍 projection / exclusion / confidence） | 07D §6 / §11 |
| 修改 `*_mutated` 标志 | 在 `non_mutation_confirmations` 中输出 `True` | 07D §11 / 当前 `_NON_MUTATION_FIELDS` 已锁 |
| 交易 / 强制 | `buy` / `sell` / `hold` / `simulated_trade` / `trading_action` / `no_trade` / `hard_*` / `forced_*` / `required_*` / `_PROTECTION_LAYER_CONNECTED` / `production_promotion` | 12E X1..X5 / 1.0 §6 / §13 hard rule 1 / 当前 ai_summary post-check 已 reject |
| Final Report → 上游回流 | `final_report → projection` / `final_report → exclusion` / `final_report → confidence` | 07D §11 / 1.0 §9 |
| LLM 调用（默认）| `anthropic` / `openai` / 任何文本生成 SDK 在主路径默认开启 | 1.0 §13 hard rule 1 / 5 / 当前 ai_summary `enable_ai_summary=False` 默认关 |
| LLM 新判断 | LLM 生成的内容超出"复述已派生结论"范围（无 source attribution） | 07D §6 / 当前 ai_summary `allow_new_judgment=True` 永久禁 |
| UI 调用 | `streamlit` / 任何 ui/ 模块 import；layout / rendering 业务 | 1.0 §13 hard rule 3 / 归 Branch 9 |
| DB schema 改动 | `CREATE TABLE` / `ALTER TABLE` 在 17J 阶段不允许 | 17E §11 ~ 17I §11 / 17J §11 |
| 直接运行 replay | 调用 `scripts/run_contract_replay*` / `scripts/historical_replay_training*` | 17D §11 |
| Future outcome 回灌 | 在线 inference 路径中读取目标日之后的 close / outcome | 1.0 §9 / 07D §3.2 |
| 污染 2026 holdout | 在 in-sample final_report 计算中读取 2026-01-01 之后的窗口 | 1.0 §5 rule 8 |

### 4.1 当前 final_decision.py `_NON_MUTATION_FIELDS` 已锁定 6 项

`services/final_decision.py:256-263`：

```
_NON_MUTATION_FIELDS = (
    "projection_result_mutated",
    "exclusion_result_mutated",
    "confidence_result_mutated",
    "final_direction_overridden",
    "confidence_recomputed",
    "preflight_applied_as_decision",
)
```

17J **不**改这 6 项；后续 PR-FINAL-* 不允许扩 / 删；可加新 boolean
（例如 `feature_payload_mutated`）但不能删既有项。

---

## 5. 当前 Final Report Layer 模块 inventory

> **范围说明**：本表覆盖 (1) **核心 Final Report 模块** (2) **Cross-system
> consistency / contract helper** (3) **Display warning card**（17H §15.3
> 引用）(4) **Narrative / Renderer**（17G §16.4 引用）(5) **Caller**（V2 /
> home_terminal orchestrator 中 final report 组装部分）(6) **architecture_orchestrator
> MVP 候选**。standard payload skeleton（17A PR-B）属 INFRA / SCHEMA。

### 5.1 核心 / 候选 inventory

| module_path | current_role | current_status | target_role | keep / migrate / quarantine / delete | active_callers | risk | next_action |
|---|---|---|---|---|---|---|---|
| `services/final_decision.py` | Branch 6 主入口；`build_final_decision`；输出 `final_report_aggregator_result.v1`；含 `_NON_MUTATION_FIELDS` 6 项；`_confidence_from_result` 把 `confidence_result.combined_confidence.level` 直接 passthrough | KEEP_ACTIVE；docstring 显式 06 / 07C / 07D / 11B boundary contract | **CORE_FINAL_REPORT**：Branch 6 主入口 | KEEP；保留 dead helper（`_apply_preflight_influence` / `_confidence_from_score` / `_risk_level`）作 Step 14 cleanup 候选；本轮不动 | `services/projection_orchestrator_v2:13+489+591`、tests | M | §6.1 / §7；§15 PR-FINAL-1 contract validator；§15 PR-FINAL-2 passthrough hardening |
| `services/projection_output_contract.py` | Step 1A 8-section pure-function validator；与 17A standard payload v1 并存 | KEEP_ACTIVE；纯函数；不接业务 | **INFRA / LEGACY_SCHEMA_VALIDATOR**（不属 Branch 6 核心；与 17G §5.1 / 17H §5 / 17I §5 一致）| KEEP（不动）；与 17A 协同 | tests；scripts；与 final_decision 输出**未**直接挂钩 | L | §6.5；与 17A standard payload validator 协同 |
| `services/projection_chain_contract.build_unified_projection_payload` | 把 feature / exclusion / main_projection / consistency 组装成 unified payload | KEEP_ACTIVE | **FINAL_REPORT_HELPER**：归 Branch 6（17F §7.6 / 17G §6.3 / 17H §6.3 / 17I §5 cross-reference）| KEEP（不动） | V2 chain；tests | M | §6.3；§15 PR-FINAL-5 split plan marker |
| `services/projection_chain_contract.build_prediction_log_record` | 含 `excluded_state` / `exclusion_action` / `triggered_rule` / `consistency_*` 等字段；面向 prediction_store | KEEP_ACTIVE | **FINAL_REPORT_HELPER / LOG_STORE_HELPER**：归 Branch 6 / log_store helper（17F §7.6 / 17G §16.4 / 17H §5 / 17I §5）| KEEP（不动） | predict.py / V2 chain / log_store / tests | M | §6.3；§15 PR-FINAL-5 |
| `services/consistency_layer.py` | cross-system consistency check；输入 4 路（exclusion / main_projection / peer / historical）；输出 `consistency_flag` / `consistency_score` / `conflict_reasons` | KEEP_ACTIVE；与 17F §6.8 / 17G §16.4 / 17H §15.3 / 17I §7 一致 | **FINAL_REPORT_AGGREGATOR_PRECHECK**：归 Branch 6（aggregator 之前的 cross-system check）；本轮**不**吸收进 final_decision；保留并存 | KEEP（不动） | `services/home_terminal_orchestrator:22`、`services/projection_orchestrator_v2:23`、tests | M | §8；§15 PR-FINAL-3 freeze / migrate decision marker |
| `services/big_up_contradiction_card.py` | Task 085 read-only presentation layer；调 `audit_big_up_exclusion` + 翻译为中文 UI warning | KEEP_ACTIVE；docstring 显式"lives in services/ not ui/" | **FINAL_REPORT_WARNING_CARD**：归 Branch 6（display warning text）；UI renderer 由 17M 决定 | KEEP（不动）；§15 PR-FINAL-4 schema for warning_cards | `services/exclusion_reliability_review`、`ui/predict_tab`、scripts、tests | M | §9.1 |
| `services/big_down_tail_warning.py` | pure logic：tail compression / strong warning / downgrade detection；输出 strong_warning / downgrade flags | KEEP_ACTIVE；纯函数 | **FINAL_REPORT_WARNING_CARD**：归 Branch 6（display warning） | KEEP（不动）；§15 PR-FINAL-4 | `services/exclusion_reliability_review`、scripts、tests | L | §9.2 |
| `services/predict_summary.py` | readable Chinese summary helpers for predict / projection results | KEEP_ACTIVE；与 13 个 bridge 之一（16I §11.2）；17G §16.4 声明非 Projection | **FINAL_REPORT_NARRATIVE_HELPER**：归 Branch 6（narrative summary helper）| KEEP（不动）；§15 PR-FINAL-8 boundary tests | predict.py / V2 chain（projection_orchestrator V1）/ evidence_trace / tests | L | §6.6 |
| `services/ai_summary.py` | 5 legacy entry points + new `generate_ai_summary`；docstring 显式 06 / 07D / 11F boundary；默认 `enable_ai_summary=False` 返回空字符串；source-attributed explanation 必需；trading / hard / forced / required post-check reject | KEEP_ACTIVE；docstring 锁严 | **FINAL_REPORT_NARRATIVE_HELPER**（optional opt-in only）：归 Branch 6 | KEEP（不动）；§15 PR-FINAL-8 boundary tests | predict.py / V2 chain / tests | M | §6.6；与 1.0 §13 hard rule 1 一致 |
| `services/projection_narrative_renderer.py` | render projection_v2 raw → 中文 trading narrative | KEEP_ACTIVE；docstring "fixed Chinese trading narrative" | **FINAL_REPORT_RENDERER**：归 Branch 6（narrative 部分）；UI layout 归 Branch 9 | KEEP（不动）；与 17G §16.4 一致 | `services/projection_entrypoint`、tests | L | §6.7 |
| `services/projection_three_systems_renderer.py` | 把 V2 raw 重塑为 negative_system / record_02_projection_system / confidence_evaluator 三段 | KEEP_ACTIVE；docstring 显式 "no scanning, prediction, or rule mutation" | **FINAL_REPORT_RENDERER**：归 Branch 6（三系统视图） | KEEP（不动）；与 17G §16.4 一致 | `services/projection_entrypoint`、`predict.py:1341`、`services/replay_record_wiring`、tests | L | §6.7 |
| `services/contract_payload_inspector.py` | read-only contract inspection；从 prediction_log 读 `contract_payload_json` → 调 `validate_projection_output` → 输出 per-section summary | KEEP_ACTIVE；docstring 显式 "verification tool, not a UI feature"；不写 DB | **NOT_FINAL_REPORT_LAYER**：归 Branch 8 Evaluation（diagnostic / dashboard tool；与 contract_payload_diff / contract_payload_trend / contract_payload_extras_dashboard 同类）| MIGRATE_LATER（17L 决定） | scripts；tests | L | §6.8 |
| `ui/projection_v2_renderer.py` | UI renderer for V2 projection raw payload | KEEP_ACTIVE；属 ui/ | **NOT_FINAL_REPORT_LAYER**：归 Branch 9 UI（17M 决定） | MIGRATE_LATER（17M 决定） | UI predict_tab；tests | L | §6.7 cross-reference 17M |
| `services/evidence_trace.py` | build projection evidence trace；调 `predict_summary` | KEEP_ACTIVE | **FINAL_REPORT_HELPER / LEGACY**：归 Branch 6 evidence summary；最终由 architecture_orchestrator 取代 | KEEP（不动） | `services/projection_orchestrator`（V1 bridge）；tests | L | §6.7 cross-reference |
| `services/projection_orchestrator_v2.py` 中 final report 组装部分（`_build_final_decision` / `build_final_decision` 调用） | V2 orchestration；汇集 main_projection + exclusion + confidence + consistency + final_decision | LEGACY_ACTIVE_DEPENDENCY；属 §17 V2 bridge | **NOT_FINAL_REPORT_CORE**：caller；归 architecture_orchestrator 取代之前保留 | KEEP（不动） | `projection_entrypoint`、`projection_v2_adapter`、tests | **H** | §13；orchestration 终态由 architecture_orchestrator 决定 |
| `services/home_terminal_orchestrator.py` 中 final report 组装部分 | 主页 orchestration；含 inline final assembly；**不**调 `build_final_decision`（独立路径） | LEGACY_ACTIVE_DEPENDENCY；与 V2 chain 并存 | **NOT_FINAL_REPORT_CORE**：caller；最终收敛到 architecture_orchestrator | KEEP（不动） | UI（home_terminal tab）；tests | **H** | §13；与 V2 收敛由 architecture_orchestrator 决定 |
| **architecture_orchestrator MVP**（候选） | 16I PR-F 提案；当前**未存在**；归属判断见 §13 | ❌ **未实现** | **ASSEMBLY_ORCHESTRATION_LAYER**（不在 9 分支正式架构内；TEMP_FUTURE_ORCHESTRATOR）| 不立即实现（17D §10.3 / 17J §13）| n/a | n/a | §13 / §15 PR-FINAL-7 ownership doc / marker |
| `tests/test_final_decision.py` / `tests/test_final_decision_aggregator_purification_boundary.py` | final_decision boundary tests；含 non-mutation / passthrough / 不重算 confidence 测试 | KEEP | KEEP | KEEP | — | L | 不动 |
| `tests/test_consistency_layer.py` | consistency_layer boundary tests | KEEP（属 Branch 6 测试范围；与 17I §5 协同迁移） | KEEP | KEEP | — | L | 不动 |
| `tests/test_final_projection_contract_fields.py` | Step 1A 契约字段 tests | KEEP | KEEP | KEEP | — | L | 不动 |

### 5.2 关键说明

- **Final Report Layer 主入口**：`services/final_decision.py` `build_final_decision`
  已实现 `final_report_aggregator_result.v1`；docstring 显式 boundary
  contract；`_NON_MUTATION_FIELDS` 锁 6 项；`_confidence_from_result`
  passthrough；不重算 direction（line 374 `final_direction = primary_direction`）
- **关键现状**：home_terminal_orchestrator **不**调 `build_final_decision`
  （inline 组装 final assembly）；V2 chain 调 `build_final_decision`。这是
  17F §7.6 / 17G §16.4 提到的"两条主链 final 组装路径不收敛"问题的具体
  表现；归 architecture_orchestrator（§13）+ 17M UI Layer Plan 协同决定
- **`final_decision.py` 含若干 dead helper**（`_apply_preflight_influence` /
  `_confidence_from_score` / `_risk_level`）；docstring 自称"Step 14 cleanup
  pass will delete them"；本轮 17J **不**清；§15 PR-FINAL-2 候选可考虑
- **`projection_chain_contract.py` 含 4 个 helper 跨多层**：
  - `build_feature_payload_from_recent_window` → Branch 2 Feature（17F §7.6）
  - `least_likely_from_projection` → Branch 3 Projection（17G §6.3）
  - `excluded_state_from_result` → Branch 4 Exclusion adapter（17H §6.3）
  - `build_prediction_log_record` / `build_unified_projection_payload` →
    Branch 6 Final Report / log_store helper（本节）
- **`consistency_layer.py` 在 17I §7 已确认归 Branch 6**：本轮 17J 把它
  收为 Final Report aggregator pre-check（§8）
- **`big_up_contradiction_card` / `big_down_tail_warning` 在 17H §15.3
  已确认归 Branch 6**：本轮 17J 把它收为 Final Report warning card（§9）
- **`predict_summary` / `ai_summary` / `projection_narrative_renderer` /
  `projection_three_systems_renderer` 在 17G §16.4 已确认归 Branch 6**：
  本轮 17J 把它收为 Final Report narrative / renderer helper（§6.6 / §6.7）
- **`contract_payload_inspector` 不属 Final Report**：是 evaluation
  diagnostic tool；归 Branch 8（§6.8）
- **DELETE_NOW 集合为空**（与 16H §13 / 17E §15.7 / 17F §16.7 / 17G §16.11 /
  17H §15.8 / 17I §17.8 一致）

---

## 6. CORE_FINAL_REPORT 保留模块

> Final Report Layer 的**核心 / 边界 helper 模块**：分主入口 + 跨层
> helper + warning card + narrative / renderer 4 类。

### 6.1 `services/final_decision.py`（主入口）

| 维度 | 说明 |
|---|---|
| 为什么保留 | Branch 6 唯一**符合 07D 契约**的主入口；docstring 显式 06 / 07C / 07D / 11B boundary contract；输出 `final_report_aggregator_result.v1`；`_NON_MUTATION_FIELDS` 锁 6 项；`_confidence_from_result` 严格 passthrough；`final_direction = primary_direction` 严格透传 |
| 目标职责 | (1) 接收 `primary_analysis` + `peer_adjustment` + `historical_probability` + `preflight` + `confidence_result` + `exclusion_result`（全部只读）(2) 派生 `final_direction`（passthrough）/ `final_confidence`（passthrough）/ display sections / warnings (3) 输出 `final_report_aggregator_result.v1` 完整 dict (4) 输出 `non_mutation_confirmations` 6 项 boolean，全部 `False`（"未 mutation" = False） |
| 是否需要改名 / 拆分 | ❌ 17J 不改名；不拆分 |
| 是否有跨层问题 | ⚠️ 当前接收 `primary_analysis`（来自 `primary_20day_analysis`，17G §7.5 声明非 Feature 也非 Projection 主路径）+ `peer_adjustment`（17F §7.7 声明非 Feature）+ `historical_probability`（17G §6.2 声明 Projection evidence）+ `preflight`（4 个 preflight helper，17G §6.4）—— 这是 0.x 时代的遗留接口；当前 schema 与 1.0 §8 Branch 6 契约部分不齐；归 §15 PR-FINAL-2 hardening |
| 后续实现任务 | §15 PR-FINAL-1：final_report_result contract validator；§15 PR-FINAL-2：passthrough / non-mutation hardening；不改 dead helper（Step 14 cleanup 候选）|
| 当前禁止动作 | 不改 `_NON_MUTATION_FIELDS`（只能加新 key，不能删）；不改 `_DIRECTIONS` / `_CONFIDENCE_LEVELS` 阈值；不改 `final_direction = primary_direction` 严格透传；不在 17J 重计算 confidence；不接 calibration table；不在 17J 切换 home_terminal 到 V2 / final_decision |

### 6.2 `services/consistency_layer.py`（aggregator pre-check）

详见 §8。

### 6.3 `services/projection_chain_contract.py`（Final Report 部分 helper）

| 维度 | 说明 |
|---|---|
| Final Report 部分 helper | `build_unified_projection_payload`（line 209）+ `build_prediction_log_record`（line 141） |
| 为什么算 FINAL_REPORT_HELPER（不是 CORE 主入口）| 不是主入口；是把 4 路输出（feature / exclusion / main_projection / consistency）组装成 unified payload（V2 chain）/ 把 4 路输出 + target_date 写成 prediction_log_record（log_store） |
| 目标职责 | (1) `build_unified_projection_payload`：组装 V2 unified payload（schema 与 standard_projection_payload.v1 不同；属 V2 链 schema） (2) `build_prediction_log_record`：组装 prediction log row（用于 log_store / projection_record_store）|
| 后续实现任务 | §15 PR-FINAL-5：split plan marker（与其他 helper 在 17F / 17G / 17H / 17I 各自归位）|
| 当前禁止动作 | 不改实现；不在 17J 拆分；不在 17J 切换到 standard_projection_payload.v1（由 architecture_orchestrator §13 决定）|

### 6.4 `services/projection_output_contract.py`（INFRA / LEGACY_SCHEMA_VALIDATOR）

| 维度 | 说明 |
|---|---|
| 为什么保留 | Step 1A 8-section pure-function validator；纯函数；不接业务；与 17A standard payload v1 并存 |
| 目标职责 | 验证 Step 1A 老契约 8 段 shape；与 final_decision **未**直接挂钩；主要由 tests / scripts 使用 |
| 是否属 CORE_FINAL_REPORT | ❌ **否**——属 INFRA / SCHEMA validator；与 17A `standard_projection_payload.py` 体例对等 |
| 17J 推荐 | KEEP；不动；与 17A 协同；后续 architecture_orchestrator 决定是否收敛到 standard_projection_payload.v1 |

### 6.5 与 17A standard_projection_payload.v1 的关系（详见 §12）

- `services/standard_projection_payload.py` 是 17A PR-B 引入的新 9-section
  validator；当前未接 active path
- `services/projection_output_contract.py` 是 Step 1A 引入的老 8-section
  validator；当前 V2 chain 通过 `build_unified_projection_payload` 间接
  挂钩
- 17J 不强制收敛；二者并存；最终由 architecture_orchestrator（§13）决定

### 6.6 `services/predict_summary.py` + `services/ai_summary.py`（narrative summary helpers）

| 维度 | 说明 |
|---|---|
| `predict_summary` | readable Chinese summary helpers；纯派生（不调 LLM）；用于 V1 orchestrator + evidence_trace |
| `ai_summary` | 可选 LLM 派生；默认 `enable_ai_summary=False` 返回空字符串；source-attributed explanation 必需；trading / hard / forced / required post-check reject；`allow_new_judgment=True` 永久禁；与 1.0 §13 hard rule 1 / 5 一致 |
| 目标职责 | 提供 final_report 的 `combined_user_summary` / `narrative` 字段（通过派生 + 可选 LLM explanation） |
| 后续实现任务 | §15 PR-FINAL-8：narrative summary helper boundary tests（forbidden import / forbidden output / allow_new_judgment 永久禁）|
| 当前禁止动作 | 不改 `enable_ai_summary` 默认；不改 `allow_new_judgment` 默认禁；不在 17J 改 ai_summary 语义；不让 ai_summary 进默认 active path |

### 6.7 `services/projection_narrative_renderer.py` + `services/projection_three_systems_renderer.py` + `services/evidence_trace.py`（renderer / trace helpers）

| 维度 | 说明 |
|---|---|
| `projection_narrative_renderer` | render V2 raw → 中文 trading narrative；由 `projection_entrypoint` 调用 |
| `projection_three_systems_renderer` | 把 V2 raw 重塑为 negative / projection / confidence 三段；由 `projection_entrypoint` / `predict.py:1341` / `replay_record_wiring` 调用 |
| `evidence_trace` | build projection evidence trace；调 predict_summary；由 V1 projection_orchestrator 使用 |
| 目标职责 | 把上游输出 reshape 成稳定 view；不重新预测；不调 LLM；docstring 已声明 "no scanning, prediction, or rule mutation" |
| 是否属 UI | ❌ **否**——这些是 logic-layer renderer / structurer，属 Branch 6；UI layout / Streamlit rendering 归 Branch 9（[ui/projection_v2_renderer.py](ui/projection_v2_renderer.py)） |
| 后续实现任务 | §15 PR-FINAL-6：contract_payload translation isolation；与 17M UI Layer 协同 |
| 当前禁止动作 | 不改 reshape 逻辑；不在 17J 引入 LLM；不动 UI |

### 6.8 `services/contract_payload_inspector.py`（NOT_FINAL_REPORT_LAYER）

| 维度 | 说明 |
|---|---|
| 当前性质 | read-only contract inspection；从 prediction_log 读 `contract_payload_json` → 调 `validate_projection_output` → 输出 per-section summary；docstring "verification tool, not a UI feature" |
| 是否属 Final Report | ❌ **否**——是事后 / 离线 contract validation tool；不参与当次 final_report 生成 |
| 应迁到 | Branch 8 Evaluation（diagnostic / dashboard tool；与 `contract_payload_diff` / `contract_payload_trend` / `contract_payload_extras_dashboard` 同类）|
| 17J 推荐 | 声明 NOT_FINAL_REPORT_LAYER；归 17L Evaluation |

---

## 7. final_decision.py 归属判断

### 7.1 当前混合内容

`services/final_decision.py` 当前实现：

| 部分 | 说明 |
|---|---|
| **Final aggregation** | `build_final_decision` 主体——把 5 路输入（primary / peer / historical / preflight / confidence + exclusion） aggregate 成 `final_report_aggregator_result.v1` |
| **risk_level** | `_risk_level` helper（dead code；docstring 自称 Step 14 cleanup 候选）|
| **confidence display** | `_confidence_from_result` 把 `confidence_result.combined_confidence.level` passthrough；不重算 |
| **projection / exclusion / confidence passthrough** | `final_direction = primary_direction`（line 374）；exclusion 仅作 `exclusion_section` display；confidence 仅 passthrough level / agreement / conflict |
| **narrative text** | `decision_factors` / `why_not_more` / `layer_contributions` / `_preflight_warnings` 派生中文 narrative |
| **compatibility output** | `_primary_missing_result`（line 141）作 fallback；schema 与正常路径一致 |

### 7.2 哪些部分属于 Final Report Layer

✅ **全部**——这是 Branch 6 主入口的天然组成：

- aggregation（核心职责）
- confidence display（passthrough）
- projection / exclusion passthrough（不重算）
- narrative text（"汇总三系统"必产物）
- compatibility output（fallback）

### 7.3 哪些部分应保持 passthrough

| 字段 | 来源 | 当前实现 | 17J 决定 |
|---|---|---|---|
| `final_direction` | `primary_analysis.direction` | 严格透传（line 374）| 保留 |
| `final_confidence` | `confidence_result.combined_confidence.level` | 严格透传（`_confidence_from_result`） | 保留 |
| `agreement_status` | `confidence_result.agreement_status` | 透传 | 保留 |
| `conflict_level` | `confidence_result.conflict_level` | 透传 | 保留 |
| exclusion section | `exclusion_result`（display only）| 透传；不影响 direction / confidence | 保留 |

### 7.4 哪些部分应禁止 mutation

`_NON_MUTATION_FIELDS` 6 项已锁（§4.1）；17J 不改：

- `projection_result_mutated = False`
- `exclusion_result_mutated = False`
- `confidence_result_mutated = False`
- `final_direction_overridden = False`
- `confidence_recomputed = False`
- `preflight_applied_as_decision = False`

### 7.5 是否应该成为 final_report_result.v1 的主入口

✅ **是**——已经是。当前 schema_version 已是 `"final_report_aggregator_result.v1"`
（line 355 / 471）；与 07D §9 / 1.0 §8 Branch 6 一致。

> **本轮 17J 决定**：`final_decision.py` 是 Branch 6 唯一主入口；不改名；
> 不拆分；后续 PR-FINAL-1 加独立 contract validator；PR-FINAL-2 加
> passthrough hardening + 删 dead helper。

### 7.6 当前阶段是否立即拆

❌ **不立即拆**。理由：

- 当前 schema 与 07D §9 大体一致；只缺 PR-FINAL-1 validator
- dead helper 删除属 Step 14 cleanup；本轮不动
- V2 vs home_terminal 两路收敛由 architecture_orchestrator 决定；不在 17J

### 7.7 不拆时如何处理

- 17J：保留；声明 CORE_FINAL_REPORT
- §15 PR-FINAL-1 / PR-FINAL-2 候选；可推迟到 18A+

---

## 8. consistency_layer 归属判断

### 8.1 来自 17I §7 的结论

17I §7 已分析 consistency_layer 不属 Confidence Layer，**倾向归 Final Report**。
本轮 17J 进一步固化判断。

### 8.2 是否应被 final_decision 吸收

❌ **否**。理由：

- consistency_layer 含 `peer_alignment` + `historical_match_result` 输入；
  这些**不**直接进 `build_final_decision`；二者输入集不同
- consistency_layer 输出 `consistency_score` 是 0.0–1.0 数值；与
  final_decision 的 `final_confidence` (str level) 性质不同
- 吸收会扩大 final_decision 边界；违反"final_decision 是 pure aggregator +
  display formatter"（07D §6 / 当前 docstring）

### 8.3 是否应 freeze 为 LEGACY

⚠️ **倾向是**——但保留作 aggregator pre-check：

- consistency_layer 当前 active；与 V2 + home_terminal 都有调用（5.1 表）
- freeze marker 是 docstring level（PR-FINAL-3 候选）；**不**改逻辑
- LEGACY_ACTIVE_DEPENDENCY 标签符合 1.0 §10 Bridge 性质：保留运行；不
  扩展；最终由 architecture_orchestrator 取代

### 8.4 是否应由 architecture_orchestrator 取代

✅ **是**——长期方向：

- architecture_orchestrator（§13；当前未实现）应是 cross-system aggregation
  入口；consistency check 是其内部步骤
- 取代时机：architecture_orchestrator MVP 落地之后（17J 之后某个 PR-FINAL-*）
- 取代前：consistency_layer 保持运行

### 8.5 当前阶段是否立即拆

❌ **不立即拆**（与 17D §11 / 17I §7.6 / 16I §10.4 一致）。

### 8.6 不拆时如何处理

- 17J：保留；声明 FINAL_REPORT_AGGREGATOR_PRECHECK
- §15 PR-FINAL-3 候选：consistency_layer freeze marker（docstring only）；
  与 architecture_orchestrator §13 协同决定时机

---

## 9. contradiction / warning card 归属判断

### 9.1 `services/big_up_contradiction_card.py`

| 维度 | 判断 |
|---|---|
| 当前性质 | Task 085 read-only presentation layer；调 `audit_big_up_exclusion` + 翻译为中文 UI warning |
| 哪些属 Final Report Layer | 文本生成 + 警告语义（中文 warning text + audit 结果）|
| 哪些应迁 UI | UI layout / Streamlit rendering（[ui/big_up_contradiction_card.py](ui/big_up_contradiction_card.py)）—— 17M 决定 |
| 哪些应迁 Review / Evaluation | 调用 `audit_big_up_exclusion`（17H §7.1 已声明 audit 归 Branch 7 Review / Branch 8 Evaluation）—— 注意：这里是 contradiction_card 调 audit，audit 自身归属是 Review/Evaluation；但 **contradiction_card 作为 display warning text 归 Branch 6** |
| 当前阶段是否立即拆 | ❌ **不立即拆**；与 17H §15.3 / 17D §11 一致 |
| 17J 决定 | 归 FINAL_REPORT_WARNING_CARD；§15 PR-FINAL-4 schema |

### 9.2 `services/big_down_tail_warning.py`

| 维度 | 判断 |
|---|---|
| 当前性质 | pure logic：tail compression / strong warning / downgrade detection |
| 哪些属 Final Report Layer | 全部——pure logic 输出 strong_warning / downgrade flags 是 display warning |
| 是否属 Branch 7 / Branch 8 | ❌ **否**——是当次 final_report 的 warning，不是事后复盘 |
| 17J 决定 | 归 FINAL_REPORT_WARNING_CARD |

### 9.3 与 §6 narrative summary helper 的关系

- contradiction / warning card 是**单独**的 warning section
- predict_summary / ai_summary 是 narrative summary
- 二者并存；warning card 出现在 final_report 的 `warning_cards` section；
  narrative summary 出现在 `combined_user_summary` section

### 9.4 §15 PR-FINAL-4 schema

定义 `warning_cards` schema：

```
"warning_cards": [
    {
        "card_id": "big_up_contradiction" | "big_down_tail" | ...,
        "level": "info" | "warning" | "critical",
        "title_zh": "...",
        "message_zh": "...",
        "evidence_refs": [...],
        "non_mutation": True,  # 警告不改写任一上游
    },
    ...
]
```

详细 schema 由 PR-FINAL-4 落地决定；本轮仅锁顶层结构。

---

## 10. projection_chain_contract 归属判断

### 10.1 4 个 helper 跨多层（与 17F §7.6 / 17G §6.3 / 17H §6.3 / 17I §5 一致）

| Helper | 归属 |
|---|---|
| `build_feature_payload_from_recent_window` | Branch 2 Feature Layer（17F §7.6）|
| `least_likely_from_projection` | Branch 3 Projection Layer（17G §6.3）|
| `excluded_state_from_result` | Branch 4 Exclusion adapter（17H §6.3）|
| `build_prediction_log_record` | Branch 6 Final Report / log_store helper（17J 本节 + 17H §5）|
| `build_unified_projection_payload` | Branch 6 Final Report（17J 本节）|

### 10.2 当前阶段不拆

- 与 17D §11 / 17F §7.6 一致
- 模块整体保留为 0.x 时代 "shared contract helpers" 集合
- 4 个 helper 物理同居；split 风险高

### 10.3 17J 标计划，不实现

- §15 PR-FINAL-5 候选：split plan marker（仅 docstring 注释每个 helper 的
  归属）；不动逻辑
- 长期：当 architecture_orchestrator 落地（§13）后，`build_unified_projection_payload`
  可被 architecture_orchestrator 取代；`build_prediction_log_record`
  可移到 `services/log_store.py` 或独立文件

---

## 11. Final Report Result 标准化规则

### 11.1 顶层结构（schema_version `final_report_aggregator_result.v1`，与 07D §9 / 当前 final_decision.py 已部分实现一致）

```
{
    "schema_version": "final_report_aggregator_result.v1",  # 当前已输出
    "system_name": "final_report_aggregator",
    "question_answered": "aggregate_three_system_outputs",
    "symbol": "AVGO",                                      # uppercase

    # Display-passthrough
    "final_direction": "偏多" | "偏空" | "中性" | "unknown",  # = primary_analysis.direction（严格透传）
    "final_confidence": "low" | "medium" | "high" | "unknown",  # = confidence_result.combined_confidence.level（严格透传）
    "agreement_status": "aligned" | "partial_conflict" | "strong_conflict" | "unknown",
    "conflict_level": "none" | "low" | "medium" | "high" | "unknown",

    # Sections（草案；当前 final_decision.py 部分已实现）
    "projection_section": {                               # 来自 projection_result，不改写
        "most_likely_state": "...",
        "ranked_states": [...],
        "primary_reasoning": [...],
    },
    "exclusion_section": {                                # 来自 exclusion_result，不改写
        "most_unlikely_state": "...",
        "triggered_rules": [...],
        "false_exclusion_risk": "...",
    },
    "confidence_section": {                               # 来自 confidence_result，不改写
        "projection_confidence": {...},
        "exclusion_confidence": {...},
        "combined_confidence": {...},
        "calibration_notes": [...],
    },
    "agreement_or_conflict_section": {                    # 来自 confidence + consistency
        "agreement_status": "...",
        "conflict_level": "...",
        "consistency_flag": "...",
        "consistency_score": ...,
        "conflict_reasons": [...],
    },

    # Display-only
    "combined_user_summary": "...",                       # 一句话结论；由 predict_summary / ai_summary 派生
    "key_points": [...],                                  # narrative key points
    "risks": [...],                                       # display risks
    "evidence_summary": [...],                            # 三系统 raw_evidence_refs 汇总
    "warning_cards": [...],                               # §9.4 schema
    "decision_factors": [...],                            # 当前已输出
    "why_not_more": "...",                                # 当前已输出
    "layer_contributions": {...},                         # 当前已输出（primary / peer / historical / preflight）

    # Source attribution
    "source_attribution": [                               # 当前已输出（line 437-471）
        {"section": "...", "field": "...", "source_field": "..."},
        ...
    ],
    "raw_section_refs": [...],                            # projection / exclusion / confidence section_ref

    # Risk disclosure
    "risk_disclosure": [...],                             # display-only；与 07D §9 一致

    # Non-mutation confirmations（与 07D §11 体例一致；当前已输出）
    "non_mutation_confirmations": {
        "projection_result_mutated": False,
        "exclusion_result_mutated": False,
        "confidence_result_mutated": False,
        "final_direction_overridden": False,
        "confidence_recomputed": False,
        "preflight_applied_as_decision": False,
    },
}
```

### 11.2 字段最小要求

| 字段 | 类型 | 备注 |
|---|---|---|
| `schema_version` | str | `"final_report_aggregator_result.v1"`（当前已输出）|
| `system_name` | str | `"final_report_aggregator"`（当前已输出）|
| `question_answered` | str | `"aggregate_three_system_outputs"`（当前已输出）|
| `symbol` | str | uppercase |
| `final_direction` | str | passthrough from primary_analysis.direction；4 档：`偏多` / `偏空` / `中性` / `unknown` |
| `final_confidence` | str | passthrough from confidence_result.combined_confidence.level；4 档：`low` / `medium` / `high` / `unknown` |
| `agreement_status` / `conflict_level` | str | passthrough from confidence_result（`unknown` 时显示 `unknown`）|
| `projection_section` / `exclusion_section` / `confidence_section` | dict | 各上游输出的 display projection（不改写） |
| `agreement_or_conflict_section` | dict | confidence + consistency 协同 |
| `combined_user_summary` | str | 一句话结论；可由 predict_summary 或 ai_summary（opt-in）派生 |
| `key_points` / `risks` / `evidence_summary` | list[str] | display narrative |
| `warning_cards` | list[dict] | §9.4 schema |
| `non_mutation_confirmations` | dict | 至少 6 项 boolean，全部 `False` |

### 11.3 缺失语义（与 07D §9 / 17F §8.3 / 17G §8.3 / 17H §8.3 / 17I §8.3 一致）

- 缺失字段一律用 `null` / `None` / 空 list `[]`，**不**用 `0` / 空 dict `{}`
- `final_direction = "unknown"` / `final_confidence = "unknown"` 必须含
  对应 warnings（与 当前 `_primary_missing_result` 一致）
- `non_mutation_confirmations` 必须**始终输出**（即使其它字段缺失）

### 11.4 不允许的字段（与 §4 / 07D §6 一致）

- ❌ `most_likely_state` / `most_unlikely_state` 在顶层（应只出现在
  `projection_section` / `exclusion_section`）
- ❌ `predicted_top1` / `predicted_top2` 在顶层
- ❌ `combined_confidence` 在顶层（应只出现在 `confidence_section`）
- ❌ `simulated_trade` / `trading_action` / `buy` / `sell` / `hold` /
  `no_trade`
- ❌ `hard_*` / `forced_*` / `required_*` / `_PROTECTION_LAYER_CONNECTED` /
  `production_promotion`
- ❌ `modified_*` / `corrected_*` / `*_mutation = True`

### 11.5 Final Report Layer 是 standard_projection_payload.v1 的 final_report section

详见 §12。

---

## 12. 与 standard_projection_payload.v1 的关系

### 12.1 17A / PR-B 已建立

- `services/standard_projection_payload.py` 已 in main（17A commit `9c779f8`）
- 含 `STANDARD_PAYLOAD_SECTIONS`（9 顶层 key）+ `validate_standard_projection_payload`
  纯函数 validator
- 当前**未接入** active path（与 16I §6 / 17F §8.4 / 17G §9.1 / 17H §9.1 /
  17I §9.1 一致）

### 12.2 Final Report Layer 只填充 final_report section

- Final Report Layer 输出符合 §11.1 草案的 `final_report`
- architecture_orchestrator（§13；未来）把 final_report 放入 standard
  payload 的 `final_report` section

### 12.3 Final Report Layer 可以定义 contract payload translation，但不应替代 full standard payload

- `services/projection_chain_contract.build_unified_projection_payload`
  当前组装 V2 chain 的 unified payload（schema 与 standard_projection_payload.v1
  不同；属 V2 链 schema）
- 17J **不**强制收敛 V2 unified 与 standard payload v1
- 收敛由 architecture_orchestrator（§13）+ 18A+ PR 决定

### 12.4 Final Report Layer 不写 compatibility_metadata，除非明确是 Bridge adapter

- `compatibility_metadata` section 是 standard_projection_payload.v1 的
  9 顶层之一，由 architecture_orchestrator 填充
- Final Report Layer 主入口 `build_final_decision` 不写
- Bridge adapter（如 V2 → legacy PredictResult）可能填；属 16I §11.2
  bridge 范畴（17D §10.1 暂停）

### 12.5 Step 1A `projection_output_contract.py` 与 standard_projection_payload.v1 并存

- 当前并存（17A 之后未强制收敛）
- 17J 不强制收敛
- 后续 architecture_orchestrator 决定收敛路径

---

## 13. architecture_orchestrator 归属判断

### 13.1 当前状态

- 16I PR-F 提案：`services/architecture_orchestrator.py` MVP
- 17D §10.3 已暂停：归入 17J Final Report Layer 决策
- 当前**未实现**（无 active 文件）

### 13.2 是否属于 Final Report Layer？

⚠️ **既是又不是**：

- **是**：architecture_orchestrator 的核心动作是把 4 路输出（feature /
  projection / exclusion / confidence）+ final_report 组装成 standard
  payload；这与 Final Report Layer 的"汇总"职责高度重叠
- **不是**：architecture_orchestrator 的"组装" = 9-section standard
  payload assembly，**包括** final_report 自身作为其中一个 section；
  二者层级不同：Final Report Layer 生成 `final_report` section；
  architecture_orchestrator 把 `final_report` + 其它 8 段组装成 full
  standard payload

### 13.3 是否属于 cross-layer orchestration？

✅ **是**——这是它的本质：

- 跨 Branch 1–6（Data 由 Feature 间接提供；Branch 7–9 不进 standard
  payload 的 inference path）
- 不属任一 9 分支正式架构
- 与 1.0 §10 Bridge 不同：Bridge 是 legacy 兼容；orchestrator 是 future
  正式入口

### 13.4 是否应作为 9 分支之外的 assembly layer？

✅ **是**——本轮 17J 给出明确归属：

> **architecture_orchestrator 归 ASSEMBLY_ORCHESTRATION_LAYER**：
>
> - 不在 9 分支正式架构内
> - 与 TEMP_MIGRATION_BRIDGE 不同（Bridge 是 legacy 兼容；orchestrator
>   是 future canonical path）
> - 标签可以是 **TEMP_FUTURE_ORCHESTRATOR** 或 **ASSEMBLY_ORCHESTRATION_LAYER**
> - 17J 不立即实现；归 §15 PR-FINAL-7 ownership doc / marker

### 13.5 它是否负责组装 standard_projection_payload.v1？

✅ **是**——这是它的唯一目的：

- 调用 Branch 2 Feature Layer → `feature_payload`
- 调用 Branch 3 / 4 / 5 → `projection_result` / `exclusion_result` /
  `confidence_result`
- 调用 Branch 6 Final Report → `final_report`
- 组装为 9-section standard payload
- 调 `validate_standard_projection_payload(payload)` 自检
- 输出 standard payload dict

### 13.6 当前阶段是否立即实现？

❌ **不立即实现**。理由（与 17D §10.3 一致）：

- 17F ~ 17I + 本轮 17J 才完成 Branch 1–5 + Branch 6 计划；7–9 计划未完成
- 各层 standard schema 还未完全在 main_projection / exclusion_layer /
  final_decision 输出（PR-FEATURE-1 / PR-PROJ-2 / PR-EXCL-2 / PR-FINAL-1
  / PR-CONF-2 等都未启动）
- architecture_orchestrator 必须等 standard schema 在四层 implementation
  PR 后才能可靠组装；否则需要在 orchestrator 内部重写大量 schema fallback
- 17J **不**自动批准 PR-F；必须 18A 单独审批

### 13.7 如果不实现，后续在哪一步处理？

- §15 PR-FINAL-7 候选：ownership doc / marker（不是代码 PR；只是文档）
  说明 architecture_orchestrator 的归属、未来职责、与各层 Plan 的关系
- 真正实现 PR：等 18A+ 阶段；前置条件：
  - 17J 入 main（已完成）
  - PR-FEATURE-1 + PR-PROJ-1 + PR-EXCL-1 + PR-CONF-1 + PR-FINAL-1 全部
    contract validator 落地（feature / projection / exclusion / confidence /
    final report 的 standard schema validator）
  - PR-FEATURE-2 + PR-PROJ-2 + PR-EXCL-2 + PR-CONF-2 / 3 + PR-FINAL-2
    standard schema 输出落地（各层主入口输出 standard keys）
  - 用户单独审批 PR-F architecture_orchestrator MVP

### 13.8 17J 立即动作

- **无**（与 17D §10.3 / §11 一致：本轮不改代码）
- 仅声明归属为 ASSEMBLY_ORCHESTRATION_LAYER / TEMP_FUTURE_ORCHESTRATOR

---

## 14. Final Report Layer 测试策略

后续 Final Report Layer 实现 PR 必须满足以下测试要求：

### 14.1 final_report shape tests

- `build_final_decision` 输出顶层含 §11.2 必备字段
- `schema_version = "final_report_aggregator_result.v1"`
- `system_name = "final_report_aggregator"`
- `question_answered = "aggregate_three_system_outputs"`

### 14.2 non-mutation tests

- `build_final_decision` 不修改 `primary_analysis` / `peer_adjustment` /
  `historical_probability` / `preflight` / `confidence_result` /
  `exclusion_result` 入参
- `non_mutation_confirmations` 6 项全部 `False`
- 输入 dict id 与输出对应 section dict id 不同

### 14.3 passthrough tests for projection / exclusion / confidence

- `final_direction` ≡ `primary_analysis.direction`（严格透传）
- `final_confidence` ≡ `confidence_result.combined_confidence.level`（严格透传）
- `agreement_status` ≡ `confidence_result.agreement_status`
- `conflict_level` ≡ `confidence_result.conflict_level`

### 14.4 no recomputation tests

- AST-level grep：`final_decision.py` source 中**不**出现：
  - `from services.main_projection_layer import` / 调用 main_projection
  - `from services.exclusion_layer import` / 调用 exclusion_layer
  - `from services.confidence_evaluator import` / 调用 build_confidence_result
- `final_direction` 不会因 `peer_adjustment` / `historical_probability`
  / `preflight` 而 flip
- `final_confidence` 不会因 `preflight` / dead helper（`_apply_preflight_influence`
  / `_confidence_from_score`）而 recompute（当前 dead code 不被调用）

### 14.5 no trading fields tests

- 输出 dict 字段集合中**不含**：`simulated_trade` / `trading_action` /
  `buy` / `sell` / `hold` / `no_trade` / `hard_*` / `forced_*` /
  `required_*` / `_PROTECTION_LAYER_CONNECTED` / `production_promotion`

### 14.6 no hard / forced / required fields tests

- 与 §14.5 重叠；显式 AST-level grep

### 14.7 contract translation tests

- 当 `confidence_result` 缺失或 `ready=False` → `final_confidence = "unknown"`
  （当前 `_confidence_from_result` 已实现）
- 当 `primary_analysis` 缺失或 `ready=False` → `_primary_missing_result`
  fallback；schema 仍是 `final_report_aggregator_result.v1`

### 14.8 warning card shape tests（§9.4 schema 落地后）

- `warning_cards` 是 list[dict]
- 每 dict 含 `card_id` / `level` / `title_zh` / `message_zh` / `evidence_refs` /
  `non_mutation`

### 14.9 renderer / UI separation tests

- `services/projection_narrative_renderer` /
  `services/projection_three_systems_renderer` / `services/predict_summary` /
  `services/ai_summary` source 中**不**import `streamlit` / `ui.*`
- UI rendering 由 `ui/projection_v2_renderer.py` 等 ui/ 模块负责

### 14.10 compatibility metadata isolation tests

- `final_decision.build_final_decision` 输出**不**含 `compatibility_metadata`
  顶层字段（属 architecture_orchestrator / Bridge adapter 范畴）
- 当前 `final_report_aggregator_result.v1` 也不含 `compatibility_metadata`

### 14.11 ai_summary opt-in tests

- 默认 `enable_ai_summary=False` → 返回空字符串 / `summary=""`
- `allow_new_judgment=True` → 永久 reject（与当前 docstring 一致）
- `require_source_attribution=False` → 永久 reject
- trading / hard / forced / required 文本 → post-check reject

### 14.12 baseline & regression

- 每个 PR-FINAL-* 必须以 Step 15 baseline 为起点（**3256 passed, 10
  skipped, 0 failed, 26 warnings, 94 subtests**）
- 新增测试数显式累加到 passed
- warnings / subtests 数变化必须**显式说明**

---

## 15. Final Report Layer 后续实现 PR 候选

> **本节是 PR 候选清单，本轮 17J 不执行任一项**。最早 18A 由用户单独
> 决定执行哪个、何时执行、按什么顺序执行。

| 序号 | 名称 | 性质 | 目标 | 文件范围 | 测试 | 风险 | 是否必须先做 |
|---|---|---|---|---|---|---|---|
| **PR-FINAL-1** | final_report_result contract validator helper | 代码（新增 helper） | 新增 `services/final_report_result_contract.py`：定义 `FINAL_REPORT_RESULT_FIELDS` + `validate_final_report_result(result) -> list[str]` 纯函数 validator；体例与 17A `standard_projection_payload.v1` / 17F PR-FEATURE-1 / 17G PR-PROJ-1 / 17H PR-EXCL-1 / 17I PR-CONF-1 一致；**不**改 final_decision 实现 | `services/final_report_result_contract.py`（新增）+ `tests/test_final_report_result_contract.py`（新增） | focused + full pytest | L | 不强制；推荐第一项 |
| **PR-FINAL-2** | final_decision passthrough / non-mutation hardening | 代码（仅加 boundary tests + 删 dead helper） | (a) 扩展现有 `tests/test_final_decision_aggregator_purification_boundary.py`：AST-level grep `_NON_MUTATION_FIELDS` 6 项覆盖 + forbidden import（不 import main_projection / exclusion_layer / confidence_evaluator） (b) 删除 `_apply_preflight_influence` / `_confidence_from_score` / `_risk_level` dead helper（docstring 已声明 Step 14 cleanup 候选） | `services/final_decision.py`（仅删 dead helper）+ tests | focused + full pytest byte-stable except dead helper | L | 不强制；可推迟 |
| **PR-FINAL-3** | consistency_layer freeze / migrate decision marker | 代码（**仅** docstring） | 给 `services/consistency_layer.py` 顶部 docstring 加 marker：`FINAL_REPORT_AGGREGATOR_PRECHECK —— LEGACY_ACTIVE_DEPENDENCY；最终由 architecture_orchestrator 取代`；与 17I §7 / 本文件 §8 协同；**不**改逻辑 | 仅 docstring | full pytest byte-stable | L | 不强制 |
| **PR-FINAL-4** | warning_cards schema for contradiction / tail warning | 代码（新增 schema dict 顶层 + helper） | (a) 在 final_decision 输出加 `warning_cards` section（§9.4 schema） (b) 新增 `services/warning_cards_aggregator.py`：把 big_up_contradiction_card + big_down_tail_warning 输出转为 `warning_cards` list；纯函数；不调外部模块 (c) 修改 final_decision caller 路径只组装 warning_cards 进 final_report | `services/warning_cards_aggregator.py`（新增）+ `services/final_decision.py`（加 section）+ tests | focused + full pytest | M | 不强制；可推迟到 PR-FINAL-1 之后 |
| **PR-FINAL-5** | projection_chain_contract split plan or marker | 代码（**仅** docstring） | 给 `services/projection_chain_contract.py` 顶部 docstring + 4 个 helper 各自 docstring 加 layer ownership 标注（与 17F §7.6 / 17G §6.3 / 17H §6.3 / 17I §5 / 本文件 §10 一致）；**不**拆 module；**不**改逻辑 | 仅 docstring | full pytest byte-stable | L | 不强制 |
| **PR-FINAL-6** | contract_payload translation isolation | 代码 | 把 `services/projection_narrative_renderer` /  `services/projection_three_systems_renderer` 中**任何**与 layout 相关的代码（如有）显式标 docstring；与 17M UI Layer 协同；**不**动 reshape 逻辑；**不**移到 ui/ | 2 个文件（仅 docstring）+ tests | focused + full pytest | L | 不强制；与 17M 协同后再决定 |
| **PR-FINAL-7** | architecture_orchestrator ownership doc / marker | **文档 only**（不是代码 PR） | 写 `tasks/record_17j_pr_final_7_architecture_orchestrator_ownership.md`：描述 architecture_orchestrator 的归属（ASSEMBLY_ORCHESTRATION_LAYER / TEMP_FUTURE_ORCHESTRATOR）+ 不在 9 分支正式架构内 + 真正实现 PR 的前置条件（PR-FEATURE-1 / PR-PROJ-1 / PR-EXCL-1 / PR-CONF-1 / PR-FINAL-1 全部落地 + PR-FEATURE-2 / PR-PROJ-2 / PR-EXCL-2 / PR-CONF-2/3 / PR-FINAL-2 standard schema 输出落地）+ 风险列表 | doc only | n/a | L | 不强制；推荐在 PR-FINAL-1 之后写 |
| **PR-FINAL-8** | narrative summary helper boundary tests | 代码（仅 tests） | 给 `services/predict_summary.py` / `services/ai_summary.py` 加 `tests/test_predict_summary_boundary.py` / 扩展现有 `tests/test_ai_summary.py`：(a) forbidden import（不 import main_projection / exclusion_layer / confidence_evaluator / streamlit / ui.* / anthropic / openai 默认调用） (b) `enable_ai_summary=False` 默认返回空 (c) `allow_new_judgment=True` reject (d) trading / hard / forced / required text post-check reject (e) source attribution 必需 | tests only | focused + full pytest | L | 不强制 |

### 15.1 候选 PR 之间的依赖

- PR-FINAL-1 → PR-FINAL-2 / PR-FINAL-4：先有 contract validator，再做
  hardening / warning cards
- PR-FINAL-3 / PR-FINAL-5 / PR-FINAL-6：互不依赖；可任意顺序；都依赖
  对应下游层 Plan / 17M 入 main 后才能最终决定 marker 内容
- PR-FINAL-7：文档 only；推荐在 PR-FINAL-1 之后；不阻塞其它 PR-FINAL-*
- PR-FINAL-8：可独立做
- 任何**代码** PR-FINAL-* 都依赖 **17J 已入 main**（前置条件）

### 15.2 候选 PR 都不能做的事

- ❌ 不改 `_NON_MUTATION_FIELDS`（只能加新 key，不能删）
- ❌ 不改 `_DIRECTIONS` / `_CONFIDENCE_LEVELS` 阈值
- ❌ 不改 `final_direction = primary_direction` 严格透传
- ❌ 不改 `_confidence_from_result` passthrough 实现
- ❌ 不在 final_decision 内部调用 main_projection / exclusion_layer /
  confidence_evaluator
- ❌ 不在 17J 阶段实现 architecture_orchestrator MVP（PR-FINAL-7 只是
  ownership doc）
- ❌ 不动 `services/projection_chain_contract.py` 4 个 helper 的实现
- ❌ 不动 V2 / home_terminal orchestrator 业务逻辑
- ❌ 不切换 home_terminal 到 V2 / final_decision
- ❌ 不切换默认 `run_predict` 路径
- ❌ 不引入 trading / hard / forced / required
- ❌ 不复活 `continuous_smoothing*` / `archive/legacy/root_stubs/*`
- ❌ 不修改 `.gitignore`
- ❌ 不处理 `avgo_agent.db`（含 backup）
- ❌ 不处理 handoff / logs / DB backup / `.claude/worktrees/`
- ❌ 不接 LLM 进默认 active path（与 1.0 §13 hard rule 1 / 5 一致）

---

## 16. 与 Review / Evaluation / UI 的交接

### 16.1 数据流方向（与 1.0 §9 / 17F §15 / 17G §15 / 17H §12 / 17I §16 一致）

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
           （仅 aggregate / 不 mutate；本轮 17J）
                 │
        ┌────────┼────────┐
        ▼        ▼        ▼
   Branch 7   Branch 8   Branch 9
   Review     Evaluation UI
   事后复盘   离线评估   只展示
```

### 16.2 Review / Learning 事后读取 final_report，但不改当次 final_report

- 与 1.0 §8 Branch 7 / 17K（未来）一致
- Review 只读 prediction_store + outcome_store + final_report 历史
- 不改当次 final_report

### 16.3 Evaluation 统计 final_report / projection / exclusion / confidence 的表现，但不改当次输出

- 与 1.0 §8 Branch 8 / 17L（未来）一致
- Evaluation 只读批处理
- 输出 metrics / dashboard
- 不改当次 final_report
- 离线 calibration 输出回到 Confidence；**不**沿其他路径回流（与 1.0
  §13 hard rule 5 / 17I §12.6 一致）

### 16.4 UI 只展示 final_report，不重算

- 与 1.0 §8 Branch 9 / §13 hard rule 3 / 17M（未来）一致
- UI 通过 final_report 看到结论；**不**重算
- UI layout 归 Branch 9；narrative reshape 归 Branch 6（§6.7）

### 16.5 Final Report 不负责 layout / Streamlit rendering

- 与 1.0 §13 hard rule 3 一致
- `services/projection_narrative_renderer` /
  `services/projection_three_systems_renderer` 是 logic-layer reshape；
  **不**调 streamlit；**不**做 layout
- UI rendering 由 `ui/projection_v2_renderer.py` 等 ui/ 模块负责

### 16.6 Final Report 不读取未来 outcome

- 与 1.0 §9 / 07D §3.2 / §11 一致
- 在线 inference 路径**禁止**读取目标日之后的 close
- evidence cutoff 由 `confidence_result.raw_evidence_refs`
  （`_filter_evidence_by_target_date`）保证；final_decision 不重新 cutoff

---

## 17. 清场 / 隔离建议

> **本节按 16H 决策表 8 个标签给出 Final Report Layer 范畴内的清场建议**。
> 本轮**不**执行任何清场动作。

### 17.1 KEEP（Final Report Layer CORE）

- `services/final_decision.py`

### 17.2 KEEP（Final Report Layer 边界 helper）

- `services/consistency_layer.py`（FINAL_REPORT_AGGREGATOR_PRECHECK）
- `services/projection_chain_contract.build_unified_projection_payload`
- `services/projection_chain_contract.build_prediction_log_record`
- `services/big_up_contradiction_card.py`（FINAL_REPORT_WARNING_CARD）
- `services/big_down_tail_warning.py`（FINAL_REPORT_WARNING_CARD）
- `services/predict_summary.py`（FINAL_REPORT_NARRATIVE_HELPER）
- `services/ai_summary.py`（FINAL_REPORT_NARRATIVE_HELPER；opt-in only）
- `services/projection_narrative_renderer.py`（FINAL_REPORT_RENDERER）
- `services/projection_three_systems_renderer.py`（FINAL_REPORT_RENDERER）
- `services/evidence_trace.py`（FINAL_REPORT_HELPER）

### 17.3 KEEP（INFRA / SCHEMA）

- `services/projection_output_contract.py`（与 17A standard payload v1 并存）

### 17.4 NOT_FINAL_REPORT_LAYER（声明非 Final Report；归其它层）

- `services/contract_payload_inspector.py` → 17L Evaluation
- `ui/projection_v2_renderer.py` → 17M UI
- `services/projection_orchestrator_v2.py`（caller；含 `_build_final_decision`）→ orchestration（与 V1 / home_terminal 一起最终由 architecture_orchestrator §13 取代）
- `services/home_terminal_orchestrator.py`（caller；inline final assembly）→ 同上

### 17.5 ASSEMBLY_ORCHESTRATION_LAYER（不在 9 分支正式架构内）

- **architecture_orchestrator MVP**（候选；当前未实现）—— TEMP_FUTURE_ORCHESTRATOR；§13 / §15 PR-FINAL-7

### 17.6 MIGRATE_LATER

- §17.4 全部模块 → 对应层 Plan 接管
- §17.5 architecture_orchestrator → 18A+ 阶段实现

### 17.7 ARCHIVE_IN_REPO

- 无 Final Report Layer 范畴的 archive 候选（与 16H / 17E §15.5 / 17F §16.5 /
  17G §16.8 / 17H §15.5 / 17I §17.6 一致）

### 17.8 QUARANTINE

- 无 Final Report Layer 范畴的 quarantine 候选（CORE 状态健康）

### 17.9 DELETE_NOW

- **空**（与 16H §13 / 17E §15.7 / 17F §16.7 / 17G §16.11 / 17H §15.8 /
  17I §17.8 一致）

### 17.10 DELETE_LATER

- `services/final_decision.py` 中的 dead helper（`_apply_preflight_influence` /
  `_confidence_from_score` / `_risk_level`）—— Step 14 cleanup 候选；
  PR-FINAL-2 可选

### 17.11 MIGRATE_CALLER_FIRST

- `services/projection_orchestrator_v2.py`（V2 caller；最终由 architecture_orchestrator
  取代之前必须先迁 caller）
- `services/home_terminal_orchestrator.py`（home_terminal caller；同上）

### 17.12 MOVE_OUTSIDE_REPO

- 无 Final Report Layer 范畴

### 17.13 DEEP_AUDIT_REQUIRED

- 无 Final Report Layer 范畴的 UNKNOWN（16G §11 列出的 10 项 UNKNOWN 中
  无 Final Report 范畴）

> **重申**：任何文件删除 / 移动 / archive 必须等 16H 规则 + 17D §11 + 用户
> 单独确认。17J 仅给出**建议**，**不**执行。

---

## 18. 不允许事项

**17J 起，Final Report Layer 范畴内**严格禁止：

- ❌ 不改代码（无 `.py` 文件被修改；本轮 0 修改）
- ❌ 不跑数据
- ❌ 不跑 replay / 不跑 validation / 不跑 historical evaluation
- ❌ 不改 DB / 不改 DB schema
- ❌ 不迁 Review / Evaluation / UI（17K / 17L / 17M 自负其责）
- ❌ 不接 trading / 不输出 buy / sell / hold / hard / forced / required
- ❌ 不进入 3R-5 / 3R-6（1.0 §12 / 16I §15 / 17D §11 / 17E §16 / 17F §17 /
  17G §17 / 17H §16 / 17I §18 / 本轮再次重申）
- ❌ 不启动任何代码 PR（PR-FINAL-* / PR-F architecture_orchestrator 候选要等 18A）
- ❌ 不修改 `.gitignore`
- ❌ 不处理 `avgo_agent.db`（含 backup）
- ❌ 不处理 handoff / logs / DB backup / `.claude/worktrees/`
- ❌ 不复活 `continuous_smoothing*` / `archive/legacy/root_stubs/*` /
  promotion 三模块
- ❌ 不污染 2026-01-01 之后 final holdout
- ❌ 不借 17J 顺手做 Data / Feature / Projection / Exclusion / Confidence /
  Review / Evaluation / UI 范畴改动
- ❌ **不直接做 architecture_orchestrator MVP**（与 17D §10.3 / §13 一致；
  必须等 17J 入 main + Branch 1–6 standard schema 落地 + 18A 单独审批）
- ❌ **不直接迁 UI**（与 17D §10.2 一致；归 17M）
- ❌ **不直接做 bridge 清理**（与 17D §10.1 一致）
- ❌ 不默认迁移 `run_predict` 到 V2（hard rule 1.0 §6.4 / §12）
- ❌ 不打开 16I PR-G bridge marker（与 17D §10.1 一致）
- ❌ 不打开 16I PR-F architecture_orchestrator MVP（与 17D §10.3 / §13 一致）
- ❌ 不允许 `final_report → projection / exclusion / confidence` 回流
- ❌ 不在 17J 接真实 calibration table（归 17L）
- ❌ 不在 17J 切换 home_terminal 到 V2 chain
- ❌ 不在 17J 强制收敛 V2 unified payload 与 standard_projection_payload.v1
  （归 architecture_orchestrator）
- ❌ 不让 ai_summary 进默认 active path（保持 `enable_ai_summary=False`）

> 与 17D §11 / 17E §16 / 17F §17 / 17G §17 / 17H §16 / 17I §18 一致；
> 本轮再次锁定。

---

## 19. 推荐下一步

> **首选**：**Step 17K：Review & Learning Layer Rebuild Plan**

理由（与 17D §12 / 17E §17 / 17F §18 / 17G §18 / 17H §17 / 17I §19 一致 +
17J 实战观察）：

- Final Report Layer 计划（17J）已就位
- 数据流方向是 Data → Feature → {Projection, Exclusion, Confidence} →
  Final Report → **{Review, Evaluation}** → UI（1.0 §9 / 16C §3）
- 按九分支编号顺序，下一层是 Review & Learning（Branch 7）
- **17K 的工作量中等**：17K 必须接管
  - `services/review_orchestrator.py`（review 主入口）
  - `services/review_store.py`（review record 持久化）
  - `services/review_agent.py`（review prompt + outcome）
  - `services/exclusion_reliability_review.py`（17H §15.3 已声明归 Review）
  - `services/anti_false_exclusion_audit.py`（17H §7.1 已声明归 Review / Evaluation）
  - `services/projection_review_closed_loop.py`（17G §16.4 已声明归 Review）
  - `services/outcome_capture.py`（outcome capture 主入口）
  - `services/projection_memory_briefing.py`（pre-prediction briefing；17G §6.4 一致）
  - `services/memory_store.py`（review / lesson 持久化）
  - 以及 `predict.py:_apply_briefing_caution`（1.0 §8 Branch 7 mention 中
    指出的 0.x 遗留——当前修改 `final_confidence`，违反 Review 不当次改答案
    的契约；归 17K 修复路径决定）
- 17K 入 main 之前，**不**允许在 Review Layer 范畴开任何代码 PR

**不推荐**：

- 不推荐跳到 17L / 17M（必须先有 Review Plan）
- 不推荐借 17J / 17K 做代码改动（与 17D §11 一致）
- 不推荐重启 16I PR-E / PR-F / PR-G / PR-H（必须等对应层 Plan）
- 不推荐解锁 3R-5 / 3R-6（1.0 §12 7 项前提仍未全部满足）
- 不推荐立刻做 PR-FINAL-* 任一项（与 17J 协同更合算）
- 不推荐立刻实现 architecture_orchestrator MVP（必须等 §13.6 / §13.7 前置
  条件 + 18A 审批）

> **明确**：本轮 17J 推荐的下一步**只有一个候选**——17K Review & Learning
> Layer Rebuild Plan。

---

## 20. 严守边界

本轮 Step 17J **只**写 Final Report Layer Rebuild Plan：

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
- ❌ 未启动任何代码 PR（PR-FINAL-* / PR-F 候选要等 18A）
- ❌ 未直接做 architecture_orchestrator MVP（仅归属判断 + ownership doc 候选）
- ❌ 未直接迁 UI
- ❌ 未启动 bridge 清理
- ❌ 未做任何局部 patch
- ❌ 未 commit / 未 push（按本轮指令）

唯一新增文件：[tasks/record_17j_final_report_layer_rebuild_plan.md](tasks/record_17j_final_report_layer_rebuild_plan.md)（本文件）。

后续修改路径：任何对 §3 职责定义 / §4 禁止事项 / §5 inventory / §6
CORE_FINAL_REPORT / §7 final_decision 归属 / §8 consistency_layer 归属 /
§9 contradiction / warning card 归属 / §10 projection_chain_contract /
§11 final_report 标准化 / §12 与 standard payload 关系 / §13
architecture_orchestrator 归属 / §14 测试策略 / §15 PR 候选 / §16 与
Review / Evaluation / UI 交接 / §17 清场建议 / §18 禁止事项 / §19 下一步
的调整，都必须**显式更新本文件**；同时检查是否需要同步更新 1.0 / 16C /
16D / 16I / 17D / 17E / 17F / 17G / 17H / 17I 与 17K（17K 入 main 后）。
