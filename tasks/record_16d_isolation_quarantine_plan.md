# 16D记录：Isolation / Quarantine Plan

> 本记录是 **Step 16D：隔离 / 清场计划**。1.0 canonical / 16A blueprint /
> 16B inventory / 16C target dataflow & contract decision 已全部入 main
> （main 最新 commit `b05d7c8`）。本轮把 16B 模块站队 + 16C 主链路与
> schema 决策**翻译为** file-by-file 的隔离 / 清场计划：deprecation
> marker、依赖断开顺序、archive plan、回滚策略。
>
> 本轮**只**写计划文档：未改业务代码、未新增测试、未删除文件、
> 未移动文件、未修改 `.gitignore`、未处理 handoff、未处理 logs /
> DB backup / `.claude/worktrees/`、未跑 replay / validation /
> historical evaluation、未写 DB / 未改 DB schema、未默认迁移
> `run_predict` 到 V2、未接 trading、未输出 buy / sell / hold /
> hard / forced / required、未进入 3R-5 / 3R-6、未 commit / 未 push。
>
> 唯一 deliverable：本文件。

---

## 1. Step 16D 目的

把 16B（模块站队）和 16C（目标数据流 + 标准 schema 决策）**翻译为**
执行计划：

- 对每一类模块给出"要做什么 / 不能做什么 / 何时做 / 如何回滚"
- 给出后续 16E / 16F+ 的可执行顺序
- **本轮只写计划，不改代码**。任何"删除 / 移动"留待 16E PR + 用户单独确认

> **本文件性质**：执行计划（plan），不是设计（design）也不是实施（impl）。
> 设计在 16C，实施从 16E 起。

---

## 2. 当前前置条件

| 项 | 状态 |
|---|---|
| 1.0 canonical principles 已入 main | ✅ commit `5c209bb` |
| 16A architecture reset blueprint 已入 main | ✅ commit `9b98ad5` |
| 16B module standup ownership inventory 已入 main | ✅ commit `bdd1314` |
| 16C target dataflow & contract decision 已入 main | ✅ commit `b05d7c8` |
| Step 12 boundary fixes / 13 regression / 14 cleanup / 15 signoff | ✅ 全部入 main |
| main 最新 commit | `b05d7c8` |
| worktree 唯一 deliberate untracked | `.claude/handoffs/task_089_post_pr_cleanup.md` |
| 战略阶段 | 从 schema 决策（16C）→ 隔离 / 清场计划（16D 本轮） |
| 3R-5 / 3R-6 | ❌ 仍然不允许进入（1.0 §12 / 16A §18） |

---

## 3. 隔离原则

按 1.0 §15 标签 + 16C §11 Bridge 退出路线，落实下列规则：

| 类别 | 处理原则 |
|---|---|
| `CORE_*`（站进九分支正式架构） | **保留并完善**；不是清理对象，是后续重建对象 |
| `TEMP_MIGRATION_BRIDGE` | **短期保留**；必须有退出条件；任何新代码**禁止**扩大 Bridge 字段依赖 |
| `LEGACY_ACTIVE_DEPENDENCY` | **不能直接删**；先断 caller；caller 全部迁移后才能 archive |
| `UNKNOWN_REVIEW_REQUIRED` | **不能直接删**；必须先 deep audit（16B-2 / 16D-2 / 用户确认）才能落标签 |
| `KEEP_FROZEN_DIAGNOSTIC` | 不参与 active path；保留为历史证据；不优先删除 |
| `ARCHIVE` | 已 quarantine 至 `archive/legacy/...`；不动 |
| raw artifacts / old outputs | 移出 repo（已 14K `.gitignore` 覆盖）；如需长期保留，本地或外部 archive，repo 内只留 summary / manifest |
| `DELETE_NOW` / `DELETE_LATER` | 必须满足 **active import = 0** + **用户单独确认**；本计划的标签**不**触发任何 `rm` / `git rm` |

> **核心约束**：本轮是**计划**。计划上可以写"未来 archive X"或"未来
> delete Y"，但**绝不**在本计划文档生效时实施任何文件级动作。

---

## 4. KEEP_CORE 清单

> 这些模块属于九分支正式架构，是**重建**对象，**不是**清理对象。
> 16D 不动；16E 起按 16C §3 数据流逐模块完善。

### 4.1 Branch 1 — Data Layer

- [data_fetcher.py](data_fetcher.py)
- [services/market_data_store.py](services/market_data_store.py)
- [services/data_query.py](services/data_query.py)
- [services/record_reader.py](services/record_reader.py)
- [scanner.py](scanner.py)（数据读取部分；16B-2 拆 hard rule 边界）
- [matcher.py](matcher.py)（数据 / 特征拆分待 16B-2）
- [encoder.py](encoder.py)（数据 / 特征拆分待 16B-2）

### 4.2 Branch 2 — Feature Layer

- [feature_builder.py](feature_builder.py)
- [services/features_20d.py](services/features_20d.py)（**legacy 窗口**；16C 决定 15d 迁移）
- [services/regime_features_builder.py](services/regime_features_builder.py)
- [services/regime_labels_builder.py](services/regime_labels_builder.py)
- [services/state_label.py](services/state_label.py)
- [services/real_regime_label_provider.py](services/real_regime_label_provider.py)
- [services/projection_chain_contract.py](services/projection_chain_contract.py) 的 feature 部分（拆分待 16E）
- **未来新建** `services/peer_alignment.py`（从 `exclusion_layer.build_peer_alignment` 抽出，16E 落地）

### 4.3 Branch 3 — Projection System

- [services/main_projection_layer.py](services/main_projection_layer.py)（核心；
  16E 修两个边界违规 + schema 对齐 07A）

### 4.4 Branch 4 — Exclusion System

- [services/exclusion_layer.py](services/exclusion_layer.py)（核心；
  16E `build_peer_alignment` 迁出 + schema 对齐 07B）

### 4.5 Branch 5 — Confidence System

- [services/confidence_evaluator.py](services/confidence_evaluator.py)（核心；
  16E key 对齐 07A/07B + 接 calibration_context；合并
  `services/consistency_layer.py`）

### 4.6 Branch 6 — Final Report Layer

- [services/final_decision.py](services/final_decision.py)（核心；
  16E 改名 / 重组为 `final_report` 生成器，schema 对齐 07D §9）
- [services/projection_output_contract.py](services/projection_output_contract.py)（外部对接 8 段 schema validator）
- [services/log_store.py](services/log_store.py)（持久化层）
- **未来新建** `services/architecture_orchestrator.py`（16E 起，未来唯一主入口）

### 4.7 Branch 7 — Review & Learning

- [services/outcome_capture.py](services/outcome_capture.py)
- [services/review_orchestrator.py](services/review_orchestrator.py)
- [services/review_center.py](services/review_center.py)
- [services/review_analyzer.py](services/review_analyzer.py)
- [services/review_classifier.py](services/review_classifier.py)
- [services/review_comparator.py](services/review_comparator.py)
- [services/review_agent.py](services/review_agent.py)
- [services/review_store.py](services/review_store.py)
- [services/memory_store.py](services/memory_store.py)
- [services/memory_feedback.py](services/memory_feedback.py)
- [services/projection_memory_briefing.py](services/projection_memory_briefing.py)
- [services/pre_prediction_briefing.py](services/pre_prediction_briefing.py)（16E
  把 caution 移到 Final Report 展示，**不**再 mutate confidence）
- [services/projection_review_closed_loop.py](services/projection_review_closed_loop.py)
- [services/prediction_store.py](services/prediction_store.py)（持久化层；
  跨 Branch 6 出口 + Branch 7 输入）
- [services/projection_record_store.py](services/projection_record_store.py)

### 4.8 Branch 8 — Evaluation Layer

- [services/historical_replay_training.py](services/historical_replay_training.py)
- [services/three_system_replay_audit.py](services/three_system_replay_audit.py)
- [services/replay_record_wiring.py](services/replay_record_wiring.py)
- [services/replay_validation_record_adapter.py](services/replay_validation_record_adapter.py)
- [services/contract_replay_planner.py](services/contract_replay_planner.py)
- [services/contract_outcome_correlation.py](services/contract_outcome_correlation.py)
- [services/regime_validation_helper.py](services/regime_validation_helper.py)
- [services/stats_engine.py](services/stats_engine.py)
- [services/avgo_1000day_training.py](services/avgo_1000day_training.py)
- [services/daily_training_pipeline.py](services/daily_training_pipeline.py)
- [services/daily_training_summary.py](services/daily_training_summary.py)

### 4.9 Branch 9 — UI / Presentation

- [app.py](app.py)（hard rule 3：最小改动）
- [ui/__init__.py](ui/__init__.py) + 全部 ui/ tabs
- 渲染器（未来从 services/projection_three_systems_renderer 等迁入或在 16B-2 决定）

> **写明**：上述 KEEP_CORE 模块**不是**清理对象，**是后续重建对象**。
> 它们的 schema / 接口 / 内部实现修改**只能**在 16E 起的 PR 中按 16C
> 决定逐步落地，**不**借 16D 计划顺手改。

---

## 5. TEMP_MIGRATION_BRIDGE 隔离计划

> 与 1.0 §10 / 16A §14 / 16B §6 / 16C §11 一致。

### 5.1 [predict.py](predict.py)

| 项 | 内容 |
|---|---|
| 当前作用 | UI / replay / scripts 主入口；含 `run_predict` legacy wrapper + 旧 `build_primary_projection` / `apply_peer_adjustment` / `build_final_projection` / `_summarize` / `_apply_briefing_caution` / `_apply_v2_legacy_adapter_overlay` |
| 为什么不能马上删 | `ui/predict_tab.py:1410`、`services/projection_orchestrator.py:107`、`services/contract_replay_writer.py:83/475`、`services/predict_legacy_v2_bridge.py:80`、`scripts/run_e2e_loop.py:108-109/232` 全部依赖 |
| 退出前置条件 | 16C §11 Phase 3（UI 切新 schema）+ Phase 4（evaluation 切新 schema）+ Phase 6（变 thin wrapper）全部满足 |
| 16D 计划动作 | **加 deprecation marker**（文件顶部 docstring + 模块级常量 `_BRIDGE_KIND = "TEMP_MIGRATION_BRIDGE"`，16E 实施；本轮**不**实施） |
| 未来路径 | 16E Phase 6 变 thin wrapper（内部完全转发到 `architecture_orchestrator`）→ Phase 7 caller 全部迁完 → Phase 8 archive 到 `archive/legacy/bridge_2026q2/`（命名按 archive 时点确定） |

### 5.2 [services/predict_legacy_adapter.py](services/predict_legacy_adapter.py)

| 项 | 内容 |
|---|---|
| 当前作用 | v2_payload → legacy 字段翻译（11E X4-A） |
| 为什么不能马上删 | `predict.py:44` 仍 import；`predict.run_predict(..., v2_payload=...)` opt-in 路径走它 |
| 退出前置条件 | Bridge #5：`predict.py` 不再需要 v2_payload overlay（即 Phase 6 thin wrapper 完成） |
| 16D 计划动作 | **加 deprecation marker**（docstring 标注 "scheduled for archive after 16E Phase 7"） |
| 未来路径 | 16E Phase 7 移除最后 import → archive |

### 5.3 [services/predict_legacy_v2_bridge.py](services/predict_legacy_v2_bridge.py)

| 项 | 内容 |
|---|---|
| 当前作用 | isolated bridge helper（11E X4-C）；提供 `build_legacy_prediction_from_v2_payload(...)` |
| 为什么不能马上删 | tests 仍存在引用；但 **active surface 中无 import**（13 §5 / 15 §5 grep 已确认） |
| 退出前置条件 | tests 不再依赖此模块；用户单独确认 archive |
| 16D 计划动作 | **第一个独立解散候选**：标 deprecation marker；同时挂 archive plan（16E Phase 1 末或 Phase 2 初即可执行） |
| 未来路径 | 16E 早期 archive 到 `archive/legacy/predict_legacy_v2_bridge/`；deprecation 到 archive 之间至少保留 1 个 release 周期作为回滚窗口 |

### 5.4 Legacy `PredictResult` 字段（schema 字段，不是文件）

| 项 | 内容 |
|---|---|
| 字段清单 | `final_bias` / `final_confidence` / `confidence` / `primary_projection` / `peer_adjustment` / `final_projection` / `path_risk` / `peer_path_risk_adjustment` |
| 定义位置 | [predict.py:297](predict.py:297) `PredictResult` TypedDict |
| 为什么不能马上删 | UI / replay / 多 boundary tests 仍引用 |
| 退出前置条件 | 16C §11 Phase 3 + 4 + 5 + 6 全部满足；test 改读 `compatibility_metadata` 或新 standard payload |
| 16D 计划动作 | **不**新增字段；**不**扩大 Bridge schema；任何新代码**禁止**写入 / 读取这些字段 |
| 未来路径 | Phase 6 之后，仅 Bridge wrapper 输出端含这些字段；`compatibility_metadata` 在 Phase 8 整段删除 |

### 5.5 `final_bias` / `final_confidence` 相关读写模块（汇总）

| 模块 | 当前如何读 / 写 | 未来动作 |
|---|---|---|
| [predict.py](predict.py) | 内部产生 `final_bias` / `final_confidence`（来自 `_extract_compat_confidence(confidence_result)` 等） | Phase 6 改为从 `architecture_orchestrator` payload 取 |
| [ui/predict_tab.py](ui/predict_tab.py) | 主面板 metric / panel 读 `final_bias` / `final_confidence` / `primary_projection` / `final_projection` | Phase 3 切到 `payload.final_report` 字段 |
| [services/contract_replay_writer.py](services/contract_replay_writer.py) | 调 `predict.run_predict` 拿 legacy `PredictResult` 持久化 | Phase 4 切到 `architecture_orchestrator` |
| [services/predict_summary.py](services/predict_summary.py) | 旧链 summary 构造（V1 链） | Phase 6 随 Bridge 退出 archive |
| [services/projection_v2_adapter.py](services/projection_v2_adapter.py) | V2 → legacy adapter | Phase 7 archive |

### 5.6 Bridge 共同约束

> 任何属 Bridge 的模块 / 字段，16D 起**禁止**：
> - 新增功能
> - 扩大依赖（任何新代码不允许读 / 写 Bridge 字段）
> - 借 16D 计划顺手改实现
> - 跳过退出条件 archive

---

## 6. LEGACY_ACTIVE_DEPENDENCY 隔离计划

> 与 1.0 §15 / 16B §7 / 16C §4.2 一致。

### 6.1 [services/projection_orchestrator.py](services/projection_orchestrator.py)

| 项 | 内容 |
|---|---|
| active caller | `services/projection_orchestrator_v2.py:16` `from services.projection_orchestrator import build_projection_orchestrator_result` |
| 当前阻塞 | V2 链通过它**回调** `predict.run_predict`（[projection_orchestrator.py:107](services/projection_orchestrator.py:107)）拿 legacy `predict_result` |
| 断 caller 前置条件 | 16E 让 V2 不再需要回调 V1（直接构造 primary_analysis；要求 16E 给出 primary_20day_analysis / peer_adjustment / historical_probability 的合并方案） |
| 16D 计划动作 | **加 deprecation marker**（docstring 标 "LEGACY_ACTIVE_DEPENDENCY since 16C/16D; pending V2 → V1 callback removal"） |
| 未来路径 | 16E 切断 V2 → V1 反向调用 → Bridge #6 满足 → 用户单独确认 → archive |

### 6.2 [services/projection_orchestrator_v2.py](services/projection_orchestrator_v2.py)

| 项 | 内容 |
|---|---|
| active caller | `services/projection_entrypoint.py:7`、`services/projection_v2_adapter.py:12`、`services/historical_replay_training.py:101`、`scripts/save_projection_records_smoke.py:441`、`predict.py:1340`（`_build_projection_three_systems_attachment` 内 lazy import） |
| 当前阻塞 | 是当前 V2 主链入口；多入口依赖；自己**仍**回调 V1 |
| 断 caller 前置条件 | 16E 起 `architecture_orchestrator` 上线后，逐个迁移：(1) `projection_entrypoint` → `architecture_orchestrator` 包装 (2) `projection_v2_adapter` → 拆分后 archive (3) `historical_replay_training` → 切到 `architecture_orchestrator` (4) `save_projection_records_smoke` → 切到 `architecture_orchestrator` (5) `predict.py` lazy import → 删除（Phase 6 thin wrapper 时） |
| 16D 计划动作 | **加 deprecation marker**（"LEGACY_ACTIVE_DEPENDENCY since 16C; superseded by future architecture_orchestrator"） |
| 未来路径 | 16E 全部 caller 迁完 → archive |

### 6.3 [services/home_terminal_orchestrator.py](services/home_terminal_orchestrator.py)

| 项 | 内容 |
|---|---|
| active caller | `app.py:86, 1899` |
| 当前阻塞 | app.py 主页主链；当前持有 "feature → exclusion → projection → consistency → confidence + log" 核心逻辑 |
| 断 caller 前置条件 | 16E 把内部实现替换为对 `architecture_orchestrator` 的薄包装 |
| 16D 计划动作 | **加 deprecation marker**（"core logic to be moved to architecture_orchestrator at 16E; this module will become UI orchestration layer"） |
| 未来路径 | 16E Phase 2 之后内部实现替换为对 `architecture_orchestrator` 的薄包装；不 archive（保留作为 Branch 9 UI orchestration layer） |

### 6.4 [services/projection_entrypoint.py](services/projection_entrypoint.py)

| 项 | 内容 |
|---|---|
| active caller | 部分 services / scripts；包装 V2 raw → projection_three_systems |
| 当前阻塞 | 与 V2 主入口绑定 |
| 断 caller 前置条件 | 16E `architecture_orchestrator` 上线 + 迁移现有 caller |
| 16D 计划动作 | 加 deprecation marker（"LEGACY_ACTIVE_DEPENDENCY"） |
| 未来路径 | 16E archive 或重构为 Branch 6 出口适配器 |

### 6.5 [services/projection_v2_adapter.py](services/projection_v2_adapter.py)

| 项 | 内容 |
|---|---|
| active caller | 部分 services |
| 当前阻塞 | adapter 性质，绑定 V2 schema |
| 断 caller 前置条件 | V2 caller 全部迁完 |
| 16D 计划动作 | 加 deprecation marker |
| 未来路径 | 16E Phase 7 archive |

### 6.6 [services/projection_orchestrator_preflight.py](services/projection_orchestrator_preflight.py)

| 项 | 内容 |
|---|---|
| active caller | V1 / V2 共用 preflight |
| 当前阻塞 | 与 V1 / V2 绑定 |
| 16D 计划动作 | 不立即 deprecate（等 16E 决定是否并入 `architecture_orchestrator` 内部 preflight） |
| 未来路径 | 16E 合并到 `architecture_orchestrator` 内部 preflight；旧文件 archive |

### 6.7 [services/primary_20day_analysis.py](services/primary_20day_analysis.py) / [services/peer_adjustment.py](services/peer_adjustment.py) / [services/historical_probability.py](services/historical_probability.py)

| 项 | 内容 |
|---|---|
| active caller | `projection_orchestrator_v2._build_primary_analysis / _build_peer_adjustment / _build_historical_probability` |
| 当前阻塞 | V2 链的 primary / peer / historical 步骤；与 main_projection_layer 职责重叠 |
| 断 caller 前置条件 | 16E 决定 V2 链是否拆为 9 分支直连 |
| 16D 计划动作 | 加 deprecation marker（待 16E 决定后细化） |
| 未来路径 | 16E 之后：peer_adjustment → 拆解（peer 信号 → Branch 2 Feature；调整推演方向语义否决）；primary_20day_analysis / historical_probability → 并入 `services/main_projection_layer.py` 或 archive |

### 6.8 [services/predict_summary.py](services/predict_summary.py)

| 项 | 内容 |
|---|---|
| active caller | `services/projection_orchestrator.py:22` |
| 当前阻塞 | V1 链 summary 构造 |
| 断 caller 前置条件 | V1 orchestrator 不再被调用 |
| 16D 计划动作 | 加 deprecation marker（"LEGACY_ACTIVE_DEPENDENCY; scheduled for archive after V1 orchestrator removal"） |
| 未来路径 | 16E Phase 6 / 7 随 V1 一起 archive |

### 6.9 [services/ai_summary.py](services/ai_summary.py)

| 项 | 内容 |
|---|---|
| active caller | UI / 链 |
| 当前阻塞 | LLM-based summary；11F default-disabled；source attribution 已加固 |
| 断 caller 前置条件 | 不需要断 caller |
| 16D 计划动作 | 不 deprecate；保留为 Branch 6 narrative 选项 |
| 未来路径 | 16C §10 已决定保留为可选；**不**解禁 default disabled |

### 6.10 [services/consistency_layer.py](services/consistency_layer.py)

| 项 | 内容 |
|---|---|
| active caller | `home_terminal_orchestrator.py:22`、`projection_orchestrator_v2.py:23` |
| 当前阻塞 | 与 confidence_evaluator.agreement_status 职责重叠（16C §7.4 决定合并） |
| 断 caller 前置条件 | 16E 把逻辑吸收到 `confidence_evaluator._compute_agreement` 与 `_combine_confidence` |
| 16D 计划动作 | 加 deprecation marker（"to be merged into confidence_evaluator at 16E"） |
| 未来路径 | 16E 合并完成 → archive |

---

## 7. UNKNOWN_REVIEW_REQUIRED 处理计划

> 这些模块**暂时**无法完全归类，必须先 deep audit（16B-2 / 16D-2 /
> 用户确认）才能落标签。**全部禁止**本轮删除 / 移动。

### 7.1 [services/projection_chain_contract.py](services/projection_chain_contract.py)

- 为什么未知：同时含 feature helper（应属 Branch 2）与 unified payload assembler（应属 Branch 6）
- 需要什么 audit：16B-2 拆每个公共函数的 active caller；16E 拆出
  feature helpers → 新 `services/feature_payload_helpers.py`，payload
  assembler → 并入 `services/architecture_orchestrator.py` 内部
- 暂时不能删 / 不能移动

### 7.2 `services/active_rule_pool*`（5 个）

- [services/active_rule_pool.py](services/active_rule_pool.py)
- [services/active_rule_pool_calibration.py](services/active_rule_pool_calibration.py)
- [services/active_rule_pool_drift.py](services/active_rule_pool_drift.py)
- [services/active_rule_pool_export.py](services/active_rule_pool_export.py)
- [services/active_rule_pool_validation.py](services/active_rule_pool_validation.py)
- 为什么未知：与 promotion 三模块共享命名空间；归属可能跨 Branch 5（数据准备）/ Branch 7（Review & Learning）/ Branch 8（Evaluation）
- 需要什么 audit：每个文件的 active caller graph；与 promotion 三模块（OFFLINE_ONLY）的导入隔离
- 暂时不能删

### 7.3 [services/projection_three_systems_renderer.py](services/projection_three_systems_renderer.py) / [services/projection_narrative_renderer.py](services/projection_narrative_renderer.py)

- 为什么未知：渲染器；介于 Branch 6（Final Report 内部 render）与 Branch 9（UI 展示）
- 需要什么 audit：与 final_decision / ai_summary 的 caller 关系；是否含决策逻辑
- 暂时不能删

### 7.4 [services/peer_adjustment.py](services/peer_adjustment.py) / [services/primary_20day_analysis.py](services/primary_20day_analysis.py)

- 已在 §6.7 列入 LEGACY_ACTIVE_DEPENDENCY；本节再次强调：拆解前必须先
  完成 16B-2 import graph audit，确认没有未识别的 active path

### 7.5 反假排除 / 矛盾 / 尾部告警系列

- [services/anti_false_exclusion_audit.py](services/anti_false_exclusion_audit.py)
- [services/anti_false_exclusion_dashboard.py](services/anti_false_exclusion_dashboard.py)
- [services/big_up_contradiction_card.py](services/big_up_contradiction_card.py)
- [services/big_down_tail_warning.py](services/big_down_tail_warning.py)
- [services/exclusion_reliability_review.py](services/exclusion_reliability_review.py)
- [services/primary_bias_diagnosis.py](services/primary_bias_diagnosis.py)
- [services/five_state_margin_policy.py](services/five_state_margin_policy.py)
- 为什么未知：可能是 Branch 4 内部诊断 / Branch 5 confidence 数据 / Branch 7 复盘 / Branch 9 UI
- 需要什么 audit：每个的 active caller + 是否读 projection_result（违反 07B §3.2）+ 是否含 mutation
- 暂时不能删

### 7.6 command-bar / tool-router / 工具层

- [services/agent_parser.py](services/agent_parser.py) / [services/agent_schema.py](services/agent_schema.py)
- [services/ai_intent_parser.py](services/ai_intent_parser.py) / [services/ai_task_parser.py](services/ai_task_parser.py)
- [services/automation_wrapper.py](services/automation_wrapper.py) / [services/tool_router.py](services/tool_router.py) / [services/intent_planner.py](services/intent_planner.py) / [services/plan_normalizer.py](services/plan_normalizer.py) / [services/command_parser.py](services/command_parser.py)
- [services/openai_client.py](services/openai_client.py) / [services/analysis_context.py](services/analysis_context.py)
- [services/dashboard_view_model.py](services/dashboard_view_model.py) / [services/multi_symbol_view.py](services/multi_symbol_view.py) / [services/inspect_analysis.py](services/inspect_analysis.py)
- [services/error_taxonomy.py](services/error_taxonomy.py) / [services/date_range_parser.py](services/date_range_parser.py) / [services/evidence_trace.py](services/evidence_trace.py) / [services/query_executor.py](services/query_executor.py)
- 为什么未知：1.0 未定义"工具层"作为正式分支；候选归属 Branch 9 / 工具子层
- 需要什么 audit：是否参与判断 / 是否仅工具性
- 暂时不能删

### 7.7 contract payload dashboard / inspector

- [services/contract_payload_diff.py](services/contract_payload_diff.py)
- [services/contract_payload_extras_dashboard.py](services/contract_payload_extras_dashboard.py)
- [services/contract_payload_inspector.py](services/contract_payload_inspector.py)
- [services/contract_payload_trend.py](services/contract_payload_trend.py)
- 为什么未知：8 段 schema 离线分析；可能 Branch 8（评估）/ Branch 9（dashboard）
- 需要什么 audit：active caller 是离线脚本还是 UI
- 暂时不能删

### 7.8 cutoff guard / soft metadata / 其他

- [services/cutoff_guard.py](services/cutoff_guard.py)（11D 已加固；可能归 Branch 7 内部 / 工具层）
- [services/soft_metadata_injection.py](services/soft_metadata_injection.py) / [services/soft_metadata_simulator.py](services/soft_metadata_simulator.py)（与 promotion 隔离）
- 暂时不能删

### 7.9 root entry / scripts

- [research.py](research.py) / [stats_reporter.py](stats_reporter.py) / [run_pipeline.py](run_pipeline.py) / [run_1000day.py](run_1000day.py)
- `scripts/` 25+ 评估 / replay / dashboard 脚本（除 continuous_smoothing 5 个已 FROZEN）
- 为什么未知：顶层 entrypoint；按用途逐一站队
- 需要什么 audit：每个脚本的输入 / 输出 / 是否调 Bridge schema
- 暂时不能删

### 7.10 records/

- [records/03_replay_accuracy_and_exclusion_accuracy.md](records/03_replay_accuracy_and_exclusion_accuracy.md)（仅 1 个文件）
- 需要什么 audit：是否仍被引用（grep tasks/ + scripts/ + services/）
- 处置：若无引用 → ARCHIVE 候选；本轮**不**移动

---

## 8. KEEP_FROZEN_DIAGNOSTIC / ARCHIVE 处理计划

### 8.1 KEEP_FROZEN_DIAGNOSTIC

- [services/continuous_smoothing_candidate.py](services/continuous_smoothing_candidate.py)
- [services/continuous_smoothing_candidate_v2.py](services/continuous_smoothing_candidate_v2.py)
- [scripts/run_continuous_smoothing_validation.py](scripts/run_continuous_smoothing_validation.py)
- [scripts/run_continuous_smoothing_validation_v2.py](scripts/run_continuous_smoothing_validation_v2.py)
- [scripts/run_real_continuous_smoothing_validation.py](scripts/run_real_continuous_smoothing_validation.py)
- [scripts/run_real_continuous_smoothing_validation_execute.py](scripts/run_real_continuous_smoothing_validation_execute.py)
- [scripts/run_real_continuous_smoothing_validation_execute_v2.py](scripts/run_real_continuous_smoothing_validation_execute_v2.py)

**写明**：

> 这些**不**参与 active path（13 §5 / 15 §5 grep 已确认）。
> **不**优先删除。
> 有历史证据价值（postmortem 对比基线）。
> 06 §8 / 07B §11 / 07C §12 / 07D §12 / 1.0 §6.17 永久禁活作为 candidate。
> 后续如要删除必须**另开** archive / delete pass，且**必须**满足
> "不复活作为 candidate"约束 + 用户单独确认。

### 8.2 ARCHIVE（已 quarantine）

- [archive/legacy/root_stubs/_DEPRECATED.md](archive/legacy/root_stubs/_DEPRECATED.md)
- [archive/legacy/root_stubs/confidence_engine.py](archive/legacy/root_stubs/confidence_engine.py)
- [archive/legacy/root_stubs/contradiction_engine.py](archive/legacy/root_stubs/contradiction_engine.py)
- [archive/legacy/root_stubs/risk_model.py](archive/legacy/root_stubs/risk_model.py)

**写明**：

> 14D quarantine 已完成；保留 `_DEPRECATED.md` 作为标记。
> **不**重新引入 root level；**不**作为任何模块的 import 目标。

### 8.3 tracked historical evidence（15 §6 锁定）

- `logs/historical_training/03_fresh_replay/`
- `logs/historical_training/exclusion_action_validation_2e/` 与 `_v2/`
- `logs/technical_features/...`

**写明**：

> 全部保留作为已结案 evidence；**不**删；**不**重写；**不**进 active path。
> 不在 16D 范围内做任何改动。

### 8.4 OFFLINE_ONLY（promotion 三模块 + protection_layer_diagnostics）

- [services/promotion_adoption_gate.py](services/promotion_adoption_gate.py)
- [services/promotion_execution_bridge.py](services/promotion_execution_bridge.py)
- [services/active_rule_pool_promotion.py](services/active_rule_pool_promotion.py)
- [services/protection_layer_diagnostics.py](services/protection_layer_diagnostics.py)

**写明**：

> 11G / 13 §4 / 15 §6 / 1.0 §13 永久 OFFLINE_ONLY；**不**进任何分支；
> **不**进 active path；**不**复活。

---

## 9. Raw artifact / repo slimming 计划

### 9.1 已由 14K `.gitignore` 覆盖的 7 类

| pattern | 当前状态 |
|---|---|
| `avgo_agent.db.backup_*` | 7 个本地保留；ignored |
| `logs/prediction_log.jsonl` | 本地保留；ignored |
| `logs/historical_training/three_system_1005/` | 本地保留；ignored |
| `logs/historical_training/three_system_w4_2024_08_2025_12/` | 本地保留；ignored |
| `logs/historical_training/three_system_w4_smoke_2024_08_05_2024_08_09/` | 本地保留；ignored |
| `logs/regime_validation/` | 本地保留；ignored |
| `.claude/worktrees/` | 26 个本地保留；harness 自动管理；ignored |

### 9.2 处置计划

> 所有 raw artifacts / old outputs **不**回主 repo。如需长期保留：
>
> - 移出 repo（本地 archive 或外部对象存储）
> - repo 内可保留**仅 markdown** summary / manifest（不含 `.csv` /
>   `.json` / `.jsonl` / `_run.log`）
> - 任何"在主仓库新建 raw output 目录"的提案**默认 reject**（与 1.0
>   §11 一致）
>
> 具体每项的 MOVE / DELETE 决定**必须用户单独确认**：
> - DB backup（7 个）→ 14J §6.2 推荐 4 周内回滚审计窗口；之后用户决定 MOVE / DELETE
> - 4 套 untracked replay / regime validation 子目录 → 14J §5.2 推荐 raw 留本地；如要保留 markdown summary 进 repo，走单独 archive commit
> - `.claude/worktrees/` 26 个 → 14J §7.1：harness 自动管理；活跃 session 期间不删

### 9.3 16D 不做的事

> - **不**移动任何本地 artifact
> - **不**删除任何本地 artifact
> - **不**修改 `.gitignore`
> - **不**新建 raw output 目录

---

## 10. 推荐执行顺序

> 总策略：**战略上大改，执行上小步**。每一步**必须**可单独 commit、
> 单独 revert、单独 regression。

| Step | 内容 | 性质 | 依赖 |
|---|---|---|---|
| **16D**（本轮） | Isolation / Quarantine Plan | 文档 | 16C |
| **16E** | Core Chain Refactor Plan | 文档 | 16D |
| **16F** | PR-1：把 `build_peer_alignment` 从 `services/exclusion_layer.py` 抽到 `services/peer_alignment.py`（Feature Layer），让 Projection / Exclusion 都从 Feature Layer import；不改逻辑 | 代码 | 16E |
| **16G** | PR-2：删 `services/main_projection_layer.py` 中 `build_main_projection_layer` / `run_main_projection_layer` 的 `exclusion_result` 形参与 `del`；不改 caller 业务逻辑（caller 已不传 exclusion_result） | 代码 | 16F |
| **16H** | PR-3：`services/confidence_evaluator._compute_agreement` 改读 `most_likely_state` / `ranked_states` / `most_unlikely_state` / `ranked_unlikely_states`；同时让 main_projection / exclusion 输出对齐 07A/07B 草案的字段命名（按 16E 决定的具体映射） | 代码 | 16G |
| **16I** | `architecture_orchestrator.py` MVP：仅产出 `standard_projection_payload.v1` 框架，先复用现有 main_projection / exclusion / confidence_evaluator / final_decision 实现，不切 caller | 代码 | 16H |
| **16J** | UI / evaluation payload migration plan（plan only） | 文档 | 16I |
| **16K** | Bridge deprecation markers PR：在 `predict.py` / `predict_legacy_adapter.py` / `predict_legacy_v2_bridge.py` / `projection_orchestrator.py` / `projection_orchestrator_v2.py` / `home_terminal_orchestrator.py` / `predict_summary.py` / `consistency_layer.py` / `peer_adjustment.py` / `primary_20day_analysis.py` / `historical_probability.py` 添加 docstring deprecation marker；不改逻辑 | 代码（仅 docstring） | 16I |
| **17A** | 实际 quarantine / repo slimming 执行（含 `predict_legacy_v2_bridge` archive）；用户单独确认每项 | 代码 + 移动 | 16K |
| ...后续 | 16C §11 Phase 3–8 逐阶段 PR | — | 上一阶段 |

> 注：16F / 16G / 16H 是**最小风险**的代码 PR，目的是先消除"软边界"
> （形参守护 / 反向 import / key 不齐），不动主入口；16I 起才碰
> orchestrator 层级。

---

## 11. 回滚策略

每个后续执行 PR 必须满足以下回滚条件：

1. **单独 commit**：每个隔离 / 重构动作**单独** commit；不混入 cleanup /
   .gitignore / STATUS.md / hard rule 修改
2. **可 git revert**：每个 commit 必须能用 `git revert <hash>` 干净回退；
   不能依赖"再合一个 fix commit"才能恢复
3. **delete 前 archive**：任何 `git rm` / 文件移动**必须**先有 archive
   plan + manifest 文件 + 用户单独 confirmation
4. **regression gate**：每个 PR 合并前**必须**通过：
   - `pytest -q`（full pytest）
   - focused boundary suite（13 §3.2 / 15 §3.3 列出的 14–15 个 file）
   - `bash scripts/check.sh`（py_compile）
5. **回归数字必须可比对**：每个 PR 写明 baseline 与 PR 后的 passed /
   skipped / failed / warnings 数字，与上一份 signoff record 对比
6. **raw artifact MOVE / DELETE 必须用户逐项确认**：DB backup / replay
   子目录 / `.claude/worktrees/` 不允许批量自动处理
7. **rollback 窗口**：deprecation marker 到 archive 之间至少保留 1 个
   release 周期（≥ 1 周）作为回滚窗口；archive 后 4 周内允许从 archive
   恢复
8. **失败立即停止**：如任何 PR 触发 boundary test failure / py_compile
   error / merge conflict，**立即停止**并 root-cause；**不**用绕过 hook
   或 force push 的方式硬合

---

## 12. 不允许事项

本轮严守：

- ❌ 不直接删除 `LEGACY_ACTIVE_DEPENDENCY` 模块
- ❌ 不直接删除 `predict.py`
- ❌ 不直接删除 `services/projection_orchestrator.py`
- ❌ 不直接迁移 UI（Bridge #1 必须按 16E Phase 3 顺序执行）
- ❌ 不直接迁移 evaluation（Bridge #2 必须按 16E Phase 4 顺序执行）
- ❌ 不直接跑 final holdout（2026-01-01 之后窗口永久保留）
- ❌ 不进入 3R-5 / 3R-6（1.0 §12 / 16A §18 锁定）
- ❌ 不输出 trading action / hard / forced / required
- ❌ 不复活 `continuous_smoothing*` / `archive/legacy/root_stubs/*` / promotion 三模块
- ❌ 不修改 `.gitignore`
- ❌ 不处理 handoff
- ❌ 不处理 logs / DB backup / `.claude/worktrees/`
- ❌ 不写 DB / 不改 DB schema
- ❌ 不默认迁移 `run_predict` 到 V2
- ❌ 不借 16D 计划顺手改实现（16D 是 plan，不是 impl）

---

## 13. 推荐下一步

**首选**：

> **Step 16E：Core Chain Refactor Plan**

理由：

- 16D 已把"哪些不能动 / 哪些等条件 / 哪些可计划 archive"写清楚
- 16E 在 16D 之上给出**第一批可执行 PR 顺序**：
  - PR-1：peer_alignment 抽出（16F）
  - PR-2：main_projection 去 exclusion_result 参数（16G）
  - PR-3：confidence key 对齐（16H）
  - PR-4：architecture_orchestrator MVP（16I）
  - PR-5：UI / evaluation payload migration plan（16J，plan only）
  - PR-6：Bridge deprecation markers（16K）
- 16E 之后才是 16F 第一个真正改代码的 PR

**备选**：

仅当 16D 评估时发现 §7 UNKNOWN_REVIEW_REQUIRED 中至少 5 个模块影响
16E 第一批 PR 顺序，先插一步：

> **Step 16D-2：Module Import Graph Deep Audit**

仅做 grep / AST 静态扫描；不改代码。

**默认**：直接进 16E。

**不推荐**：

- 不推荐直接进 16F 代码 PR（必须先有 16E 计划）
- 不推荐借 16D 做代码改动
- 不推荐借任一步解锁 3R-5 / 3R-6（1.0 §12 7 项前提必须全部满足）

---

## 14. 严守边界

本轮 Step 16D **只**写 isolation / quarantine plan：

- ❌ 未改业务代码（无 `.py` 文件被修改）
- ❌ 未新增测试（`tests/` 字节不变）
- ❌ 未删除文件
- ❌ 未移动文件
- ❌ 未修改 `.gitignore`
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
- ❌ 未 commit / 未 push（按本轮指令）

唯一新增文件：[tasks/record_16d_isolation_quarantine_plan.md](tasks/record_16d_isolation_quarantine_plan.md)（本文件）。

后续修改路径：任何对 §3 隔离原则 / §4 KEEP_CORE / §5 Bridge / §6
LEGACY / §7 UNKNOWN / §8 FROZEN/ARCHIVE / §9 raw artifact / §10
执行顺序 / §11 回滚 / §12 禁止 / §13 下一步的调整，都必须**显式更新
本文件**；同时检查是否需要同步更新 1.0 / 16A / 16B / 16C。
