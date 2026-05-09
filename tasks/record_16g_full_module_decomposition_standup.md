# 16G记录：Full Module Decomposition / Complete Stand-up Pass

> 本记录是 **Step 16G：全仓库模块拆解和完整站队**。1.0 canonical / 16A
> blueprint / 16B inventory / 16C target dataflow & contract decision /
> 16D isolation & quarantine plan / 16E core chain refactor plan /
> 16F architecture reset no-patching principle 已全部入 main（main 最新
> commit `6cfaa9b`）。本轮把 16B 第一版 inventory **扩大到全仓库**，
> 把 `UNKNOWN_REVIEW_REQUIRED` 数量降到最低。
>
> 本轮**只**做 inventory / 站队：未改业务代码、未新增测试、未删除文件、
> 未移动文件、未修改 `.gitignore`、未处理 handoff、未处理 logs /
> DB backup / `.claude/worktrees/`、未跑 replay / validation /
> historical evaluation、未写 DB / 未改 DB schema、未默认迁移
> `run_predict` 到 V2、未接 trading、未输出 buy / sell / hold /
> hard / forced / required、未进入 3R-5 / 3R-6、未 commit / 未 push、
> 未启动 peer_alignment PR、未做任何局部 patch。
>
> 唯一 deliverable：本文件。

---

## 1. Step 16G 目的

把 16B 第一版 inventory 进一步**扩大到全仓库**：

- 不只看核心 services（16B 主要覆盖关键 services + 部分 ui）
- 必须覆盖：root .py、root 非 .py、`services/` 109 个、`ui/` 17 个、
  `scripts/` 28 个 .py、`tests/` 165 个、`tasks/` 173 个 .md、
  `records/` 1 个、`archive/` 4 个、tracked logs evidence 21 个、
  config infra 文件
- 给每个文件落 1.0 §15 标签（含 16G 新增辅助标签）
- 把 16B 留下的 35+ `UNKNOWN_REVIEW_REQUIRED` 降到接近 0（目标）
- 显式找出**重复模块** / **跨层模块** / **旧链残留**

> **本轮性质**：inventory（清单），不是 design 也不是 impl。所有"删除 /
> 移动 / 重构"留待 16H 决策表 + 16I refactor 计划 + 17A 第一个代码 PR。
>
> **16F 原则不变**：不在本轮做任何代码改动；不顺手开 PR。

---

## 2. 当前前置条件

| 项 | 状态 |
|---|---|
| 1.0 canonical principles 已入 main | ✅ commit `5c209bb` |
| 16A architecture reset blueprint 已入 main | ✅ commit `9b98ad5` |
| 16B module standup ownership inventory 已入 main | ✅ commit `bdd1314` |
| 16C target dataflow & contract decision 已入 main | ✅ commit `b05d7c8` |
| 16D isolation / quarantine plan 已入 main | ✅ commit `694450e` |
| 16E core chain refactor plan 已入 main | ✅ commit `932d243` |
| 16F architecture reset no-patching principle 已入 main | ✅ commit `6cfaa9b` |
| Step 12–15 boundary fixes / regression / cleanup / signoff | ✅ 全部入 main |
| main 最新 commit | `6cfaa9b` |
| worktree 唯一 deliberate untracked | `.claude/handoffs/task_089_post_pr_cleanup.md` |
| 战略阶段 | 从 no-patching 原则锁定（16F）→ 全模块站队（16G 本轮） |
| 3R-5 / 3R-6 | ❌ 仍然不允许进入 |
| 第一个代码 PR | ❌ 必须等 16G + 16H + 16I 完成后由 16I 决定 |

---

## 3. 扫描范围

| 路径 | 文件数 | 范围 |
|---|---|---|
| root `*.py` | 11 | app / predict / scanner / matcher / encoder / feature_builder / data_fetcher / research / run_pipeline / run_1000day / stats_reporter |
| root 非 `*.py` | 11 | .env.example / .gitignore / AGENTS.md / AVGO_Task1_8_Validation_Report.md / avgo_agent.db / requirements.txt / runtime.txt / 一键启动说明.md / 启动博通系统.bat / 启动博通系统.command（含 .git 元目录） |
| `services/` | **109** | 全部业务 services |
| `ui/` `*.py` | 17 | 全部 UI tabs / renderers / labels（不含 `__pycache__/`） |
| `scripts/` | 28 .py + 1 `check.sh` | 评估 / replay / dashboard / migration / 工具 |
| `tests/` `*.py` | 162 + 3 fixtures | 162 个 `test_*.py` + 3 个 fixture |
| `tasks/` `*.md` | 173 | 36 个 `record_*` + 101 个 `step_*` + 35 个 numeric task + STATUS.md |
| `records/` | 1 | `03_replay_accuracy_and_exclusion_accuracy.md` |
| `archive/legacy/root_stubs/` | 4 | 14D quarantine + `_DEPRECATED.md` marker |
| `logs/` tracked evidence | 21 | git 已追踪的历史 replay / regime / technical features 输出 |
| `.claude/` | infra | CLAUDE.md / CHECKLIST.md / PROJECT_STATUS.md / TASK_TEMPLATE.md / agents/ / skills/ / handoffs/ / worktrees/（worktrees ignored） |

> **本轮只读扫描**：`find` / `git ls-files` / `head` / `sed -n 1,8p` 等
> 只读命令；**未**移动 / 删除任何文件。

---

## 4. 站队标签

沿用 1.0 §15 + 16A §15 + 16B §3：

| 标签 | 含义 |
|---|---|
| `CORE_DATA` | Branch 1 Data Layer |
| `CORE_FEATURE` | Branch 2 Feature Layer |
| `CORE_PROJECTION` | Branch 3 Projection System |
| `CORE_EXCLUSION` | Branch 4 Exclusion System |
| `CORE_CONFIDENCE` | Branch 5 Confidence System |
| `CORE_FINAL_REPORT` | Branch 6 Final Report Layer |
| `CORE_REVIEW_LEARNING` | Branch 7 Review & Learning Layer |
| `CORE_EVALUATION` | Branch 8 Evaluation Layer |
| `CORE_UI` | Branch 9 UI / Presentation Layer |
| `TEMP_MIGRATION_BRIDGE` | 迁移期兼容；不属正式架构 |
| `LEGACY_ACTIVE_DEPENDENCY` | 仍 active；不属未来正式目标 |
| `KEEP_FROZEN_DIAGNOSTIC` | 只读冻结基线 |
| `ARCHIVE` | 已 quarantine 至 `archive/legacy/...` |
| `OFFLINE_ONLY` | 仅离线诊断；不进 active path |
| `QUARANTINE_CANDIDATE` | 16H 评估后可进 archive |
| `DELETE_NOW` / `DELETE_LATER` | 候选删除（**本轮不实施**） |
| `UNKNOWN_REVIEW_REQUIRED` | 仍需 deep audit |

**16G 新增辅助标签**：

| 标签 | 含义 |
|---|---|
| `CROSS_LAYER_MODULE` | 同时承担多个分支职责，需 16H/16I 决定拆分 |
| `DUPLICATE_FUNCTIONALITY` | 与另一模块功能重叠 |
| `SCRIPT_ONLY` | 仅供 scripts/ 调用的离线工具 |
| `TEST_ONLY` | 仅 tests/ 使用 |
| `DOC_ONLY` | 纯文档；无可执行代码 |
| `RAW_ARTIFACT` | DB / log / cache 等运行时产物 |
| `CONFIG_INFRA` | `.gitignore` / `requirements.txt` / hooks / runtime |
| `TOOL_LAYER` | 1.0 未定义的工具层（command-bar / parser / dashboard helpers）；候选 Branch 9 子层 |

> 辅助标签**不**取代主标签；主标签必须是 1.0 §15 之一。辅助标签
> 描述模块的"特殊属性"（跨层 / 重复 / 仅脚本 / 仅测试 / 文档 / 工具）。

---

## 5. 全仓库总 inventory

### 5.1 root `*.py`（11）

| path | type | current_role | target_branch | status_label | active references | risk | next_action |
|---|---|---|---|---|---|---|---|
| [app.py](app.py) | code | Streamlit 主入口 | Branch 9 | `CORE_UI` | UI / 多 services | M | hard rule 3：app.py 最小改动 |
| [predict.py](predict.py) | code | legacy wrapper（含 `run_predict` + 旧 build_primary/peer/final） | Bridge | `TEMP_MIGRATION_BRIDGE` | `ui/predict_tab.py:1410`、`services/projection_orchestrator.py:107`、`services/contract_replay_writer.py`、`services/predict_legacy_v2_bridge.py:80`、`scripts/run_e2e_loop.py:108` | H | 16I：thin wrapper；Bridge Phase 6 |
| [scanner.py](scanner.py) | code | 数据读取 + 硬规则扫描 + 历史结构匹配 | Branch 1 + Branch 2 + Branch 3 | `CROSS_LAYER_MODULE` | app.py / predict / 多 services | M | 16H/16I：拆数据层 vs 硬规则层（hard rule 2 锁定不可重写） |
| [matcher.py](matcher.py) | code | 五状态历史样本匹配 | Branch 2 + Branch 3 | `CROSS_LAYER_MODULE` | scanner / predict / scripts | M | 16H：拆 feature 抽取 vs 结构判断 |
| [encoder.py](encoder.py) | code | OHLCV → coded structure 编码 | Branch 1 + Branch 2 | `CROSS_LAYER_MODULE` | scanner / matcher / data_fetcher | M | 16H：拆 data layer vs feature layer 边界 |
| [feature_builder.py](feature_builder.py) | code | 特征推导（顶层） | Branch 2 | `CORE_FEATURE` | scripts / pipeline | L | 保留；与 features_20d 合并审 |
| [data_fetcher.py](data_fetcher.py) | code | yfinance / 本地 CSV 读取 | Branch 1 | `CORE_DATA` | scanner / encoder / app.py / scripts | L | 保留；hard rule 2 |
| [research.py](research.py) | code | 顶层 research 入口（未通读） | Branch 8 候选 | `UNKNOWN_REVIEW_REQUIRED` | grep 显示无 active import；仅 root 工具 | L | 16G-2：grep 实际 caller 后归位 Branch 8 入口 / `SCRIPT_ONLY` |
| [run_pipeline.py](run_pipeline.py) | code | pipeline 入口 | Branch 8 入口 | `CORE_EVALUATION` + `SCRIPT_ONLY` | shell / docs | L | 保留；16H 决定是否迁入 services/ |
| [run_1000day.py](run_1000day.py) | code | 1000 日训练 entrypoint | Branch 8 入口 | `CORE_EVALUATION` + `SCRIPT_ONLY` | shell / docs | L | 同上 |
| [stats_reporter.py](stats_reporter.py) | code | 统计报告（顶层） | Branch 8 候选 | `CORE_EVALUATION` + `CROSS_LAYER_MODULE` | scripts / pipeline | L | 16H：决定是否迁入 services/ |

### 5.2 root 非 `*.py`（11）

| path | status_label | note |
|---|---|---|
| `.env.example` | `CONFIG_INFRA` | 环境变量模板 |
| `.gitignore` | `CONFIG_INFRA` | 14K 锁定的 6 行 pattern；本轮**不**改 |
| `requirements.txt` | `CONFIG_INFRA` | 依赖清单 |
| `runtime.txt` | `CONFIG_INFRA` | runtime 声明 |
| `AGENTS.md` | `DOC_ONLY` | agent 说明 |
| `AVGO_Task1_8_Validation_Report.md` | `DOC_ONLY` + `QUARANTINE_CANDIDATE` | 历史 task 1-8 验证报告；可 16H 移到 `archive/legacy/reports/`（候选） |
| `一键启动说明.md` | `DOC_ONLY` | 用户启动说明 |
| `启动博通系统.bat` | `TOOL_LAYER` + `CONFIG_INFRA` | Windows 启动脚本 |
| `启动博通系统.command` | `TOOL_LAYER` + `CONFIG_INFRA` | macOS 启动脚本 |
| `avgo_agent.db` | `RAW_ARTIFACT` | **当前 tracked**；live SQLite DB；`.gitignore` 已覆盖 `*.backup_*` 但**未**覆盖 `.db` 本体；16H/17A 必须决定移出 repo（用户单独确认） |
| `.git` | infra | git 元目录；不在本表范围 |

### 5.3 `services/` 109 文件

按主标签分组列出（每条单行）：

#### 5.3.1 `CORE_DATA`（Branch 1）— 4

- [services/data_query.py](services/data_query.py)
- [services/market_data_store.py](services/market_data_store.py)
- [services/record_reader.py](services/record_reader.py)
- [services/real_regime_label_provider.py](services/real_regime_label_provider.py)

#### 5.3.2 `CORE_FEATURE`（Branch 2）— 4

- [services/features_20d.py](services/features_20d.py)（**legacy 窗口**；16C 决定 15d 迁移）
- [services/regime_features_builder.py](services/regime_features_builder.py)
- [services/regime_labels_builder.py](services/regime_labels_builder.py)
- [services/state_label.py](services/state_label.py)

#### 5.3.3 `CORE_PROJECTION`（Branch 3）— 1（+ 2 preflight）

- [services/main_projection_layer.py](services/main_projection_layer.py)（核心；16E 修两个边界违规）
- [services/projection_preflight.py](services/projection_preflight.py)（preflight；候选 Branch 3 内部）
- [services/projection_rule_preflight.py](services/projection_rule_preflight.py)（preflight；候选 Branch 3 内部）

#### 5.3.4 `CORE_EXCLUSION`（Branch 4）— 1

- [services/exclusion_layer.py](services/exclusion_layer.py)（核心；16E `build_peer_alignment` 迁出 + schema 对齐 07B）

#### 5.3.5 `CORE_CONFIDENCE`（Branch 5）— 1（+ 1 数据准备）

- [services/confidence_evaluator.py](services/confidence_evaluator.py)（核心）
- [services/contract_calibration_inputs.py](services/contract_calibration_inputs.py)（数据准备；候选 Branch 5 内部）

#### 5.3.6 `CORE_FINAL_REPORT`（Branch 6）— 4 + 1 持久化

- [services/final_decision.py](services/final_decision.py)（strict passthrough aggregator）
- [services/projection_output_contract.py](services/projection_output_contract.py)（外部 8 段 schema validator）
- [services/log_store.py](services/log_store.py)（持久化层 — `logs/prediction_log.jsonl`）
- [services/prediction_store.py](services/prediction_store.py)（**CROSS** Branch 6 出口 + Branch 7 输入；持久化 SQLite）
- [services/projection_record_store.py](services/projection_record_store.py)（**CROSS** Branch 6 / Branch 7）

#### 5.3.7 `CORE_REVIEW_LEARNING`（Branch 7）— 12

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
- [services/pre_prediction_briefing.py](services/pre_prediction_briefing.py)（**风险**：当前在 `predict.py:1357 _apply_briefing_caution` 中 mutate `final_confidence`；16I 移到 Final Report 展示）
- [services/projection_review_closed_loop.py](services/projection_review_closed_loop.py)
- [services/error_taxonomy.py](services/error_taxonomy.py)（review error 分类工具；候选 Branch 7 helper）
- [services/cutoff_guard.py](services/cutoff_guard.py)（11D guard；Branch 7 内部 + tool helper）

#### 5.3.8 `CORE_EVALUATION`（Branch 8）— 13

- [services/historical_replay_training.py](services/historical_replay_training.py)
- [services/three_system_replay_audit.py](services/three_system_replay_audit.py)
- [services/replay_record_wiring.py](services/replay_record_wiring.py)
- [services/replay_validation_record_adapter.py](services/replay_validation_record_adapter.py)
- [services/contract_replay_planner.py](services/contract_replay_planner.py)
- [services/contract_replay_writer.py](services/contract_replay_writer.py)（**CROSS** Branch 8 + Bridge caller — 调 `predict.run_predict`；Phase 4 退出条件）
- [services/contract_outcome_correlation.py](services/contract_outcome_correlation.py)
- [services/regime_validation_helper.py](services/regime_validation_helper.py)
- [services/stats_engine.py](services/stats_engine.py)
- [services/avgo_1000day_training.py](services/avgo_1000day_training.py)
- [services/daily_training_pipeline.py](services/daily_training_pipeline.py)
- [services/daily_training_summary.py](services/daily_training_summary.py)
- [services/contract_payload_diff.py](services/contract_payload_diff.py)（dashboard tool）
- [services/contract_payload_extras_dashboard.py](services/contract_payload_extras_dashboard.py)（dashboard tool）
- [services/contract_payload_inspector.py](services/contract_payload_inspector.py)（dashboard tool）
- [services/contract_payload_trend.py](services/contract_payload_trend.py)（dashboard tool）

#### 5.3.9 `TEMP_MIGRATION_BRIDGE`（services 部分）— 2

- [services/predict_legacy_adapter.py](services/predict_legacy_adapter.py)（11E X4-A；`predict.py:44` 仍 import）
- [services/predict_legacy_v2_bridge.py](services/predict_legacy_v2_bridge.py)（11E X4-C；**当前无 active import** — 第一个独立解散候选）

#### 5.3.10 `LEGACY_ACTIVE_DEPENDENCY`（services）— 11

- [services/projection_orchestrator.py](services/projection_orchestrator.py)（V1；调 `predict.run_predict`）
- [services/projection_orchestrator_v2.py](services/projection_orchestrator_v2.py)（V2；反向回调 V1）
- [services/projection_orchestrator_preflight.py](services/projection_orchestrator_preflight.py)（V1/V2 共用 preflight）
- [services/projection_entrypoint.py](services/projection_entrypoint.py)（V2 wrapper）
- [services/projection_v2_adapter.py](services/projection_v2_adapter.py)（V2 adapter）
- [services/home_terminal_orchestrator.py](services/home_terminal_orchestrator.py)（app.py 主页主链；16C 决定降级为 UI orch）
- [services/primary_20day_analysis.py](services/primary_20day_analysis.py)（V2 primary step；与 main_projection_layer 重叠）
- [services/peer_adjustment.py](services/peer_adjustment.py)（V2 peer step；16C §7.5 决定拆解：peer 信号 → Branch 2，"调整推演方向"语义否决）
- [services/historical_probability.py](services/historical_probability.py)（V2 historical step）
- [services/predict_summary.py](services/predict_summary.py)（V1 链 summary；Phase 6/7 archive）
- [services/consistency_layer.py](services/consistency_layer.py)（与 confidence_evaluator agreement 重叠；16C §7.4 决定合并）

#### 5.3.11 `LEGACY_ACTIVE_DEPENDENCY` + `CORE_FINAL_REPORT`（受限保留）— 1

- [services/ai_summary.py](services/ai_summary.py)（11F default-disabled；保留为 Branch 6 narrative 选项；不解禁 default）

#### 5.3.12 `KEEP_FROZEN_DIAGNOSTIC`（services）— 2

- [services/continuous_smoothing_candidate.py](services/continuous_smoothing_candidate.py)
- [services/continuous_smoothing_candidate_v2.py](services/continuous_smoothing_candidate_v2.py)

#### 5.3.13 `OFFLINE_ONLY`（services）— 4

- [services/promotion_adoption_gate.py](services/promotion_adoption_gate.py)
- [services/promotion_execution_bridge.py](services/promotion_execution_bridge.py)
- [services/active_rule_pool_promotion.py](services/active_rule_pool_promotion.py)
- [services/protection_layer_diagnostics.py](services/protection_layer_diagnostics.py)

#### 5.3.14 `TOOL_LAYER`（候选 Branch 9 子层）— 13

- [services/agent_parser.py](services/agent_parser.py)
- [services/agent_schema.py](services/agent_schema.py)
- [services/ai_intent_parser.py](services/ai_intent_parser.py)
- [services/ai_task_parser.py](services/ai_task_parser.py)
- [services/automation_wrapper.py](services/automation_wrapper.py)
- [services/intent_planner.py](services/intent_planner.py)
- [services/tool_router.py](services/tool_router.py)
- [services/plan_normalizer.py](services/plan_normalizer.py)
- [services/command_parser.py](services/command_parser.py)
- [services/openai_client.py](services/openai_client.py)（Branch 6 narrative tool 候选）
- [services/analysis_context.py](services/analysis_context.py)
- [services/dashboard_view_model.py](services/dashboard_view_model.py)
- [services/multi_symbol_view.py](services/multi_symbol_view.py)
- [services/date_range_parser.py](services/date_range_parser.py)
- [services/comparison_engine.py](services/comparison_engine.py)
- [services/query_executor.py](services/query_executor.py)
- [services/evidence_trace.py](services/evidence_trace.py)（依赖 `predict_summary`；候选 Branch 6 内部）

#### 5.3.15 `CROSS_LAYER_MODULE`（明确跨层）— 11

| module | 跨的层 | 16H 决策方向 |
|---|---|---|
| [services/projection_chain_contract.py](services/projection_chain_contract.py) | Branch 2 (feature helpers) + Branch 6 (unified payload assembler) | 16I：拆 — feature helpers → 新 module；assembler → `architecture_orchestrator` |
| [services/anti_false_exclusion_audit.py](services/anti_false_exclusion_audit.py) | Branch 4 内部诊断 + Branch 7 / Branch 8 | 16H deep audit |
| [services/anti_false_exclusion_dashboard.py](services/anti_false_exclusion_dashboard.py) | Branch 4 + Branch 9 UI | 16H deep audit |
| [services/big_up_contradiction_card.py](services/big_up_contradiction_card.py) | Branch 4 + Branch 9 UI（`ui/big_up_contradiction_card.py` 配套） | 16H：可能 Branch 4 内部诊断 |
| [services/big_down_tail_warning.py](services/big_down_tail_warning.py) | Branch 4 + Branch 7 | 16H deep audit |
| [services/exclusion_reliability_review.py](services/exclusion_reliability_review.py) | Branch 4 / Branch 5 / Branch 7 | 16H deep audit |
| [services/regime_diagnostics_dashboard.py](services/regime_diagnostics_dashboard.py) | Branch 8 + Branch 9（且 `scripts/regime_diagnostics_dashboard.py` 重名） | 16H：拆数据组装 vs UI 渲染；并解决重名 |
| [services/projection_three_systems_renderer.py](services/projection_three_systems_renderer.py) | Branch 6 (Final Report 内部 render) + Branch 9 UI | 16H deep audit |
| [services/projection_narrative_renderer.py](services/projection_narrative_renderer.py) | Branch 6 / Branch 9 | 16H deep audit |
| [services/soft_metadata_injection.py](services/soft_metadata_injection.py) | Branch 6 metadata + Branch 7 sidecar | 16H：与 promotion 隔离明确 |
| [services/soft_metadata_simulator.py](services/soft_metadata_simulator.py) | Branch 6 / Branch 8 simulator | 16H deep audit；并解决与 `scripts/soft_metadata_simulator.py` 重名 |

#### 5.3.16 `UNKNOWN_REVIEW_REQUIRED`（services）— 7

- [services/active_rule_pool.py](services/active_rule_pool.py)
- [services/active_rule_pool_calibration.py](services/active_rule_pool_calibration.py)
- [services/active_rule_pool_drift.py](services/active_rule_pool_drift.py)
- [services/active_rule_pool_export.py](services/active_rule_pool_export.py)
- [services/active_rule_pool_validation.py](services/active_rule_pool_validation.py)
- [services/projection_output_adapter.py](services/projection_output_adapter.py)（疑 dormant；docstring 写"not yet wired into run_predict"）
- [services/primary_bias_diagnosis.py](services/primary_bias_diagnosis.py)
- [services/inspect_analysis.py](services/inspect_analysis.py)
- [services/five_state_margin_policy.py](services/five_state_margin_policy.py)（候选 Branch 3 内部）

> 16G 后剩余 services UNKNOWN = **9**（vs 16B 的 ≥ 35）。

### 5.4 `ui/` 17 文件 — 全部 `CORE_UI`（Branch 9）

| module | 备注 |
|---|---|
| [ui/__init__.py](ui/__init__.py) | 包入口 |
| [ui/labels.py](ui/labels.py) | 中文 / display labels |
| [ui/home_tab.py](ui/home_tab.py) | home tab |
| [ui/predict_tab.py](ui/predict_tab.py) | 主预测 tab；**Bridge 退出条件 #1**（仍读 `final_bias` / `final_confidence`） |
| [ui/scan_tab.py](ui/scan_tab.py) | scan tab |
| [ui/research_tab.py](ui/research_tab.py) | research tab |
| [ui/review_tab.py](ui/review_tab.py) | review tab |
| [ui/history_tab.py](ui/history_tab.py) | history tab |
| [ui/inspect_tab.py](ui/inspect_tab.py) | inspect tab |
| [ui/control_tab.py](ui/control_tab.py) | control tab |
| [ui/command_bar.py](ui/command_bar.py) | command bar |
| [ui/projection_v2_renderer.py](ui/projection_v2_renderer.py) | V2 渲染器（候选改名 `final_report_renderer`） |
| [ui/protection_layer_diagnostics_renderer.py](ui/protection_layer_diagnostics_renderer.py) | OFFLINE_ONLY display |
| [ui/anti_false_exclusion_display.py](ui/anti_false_exclusion_display.py) | 反假排除展示 |
| [ui/exclusion_reliability_review.py](ui/exclusion_reliability_review.py) | 否定可靠性展示 |
| [ui/big_up_contradiction_card.py](ui/big_up_contradiction_card.py) | 大涨矛盾 card UI |
| [ui/soft_metadata_renderer.py](ui/soft_metadata_renderer.py) | soft metadata 渲染 |
| [ui/soft_metadata_baseline_cache.py](ui/soft_metadata_baseline_cache.py) | soft metadata 基线缓存 |

> ui/ UNKNOWN = **0**。所有 ui/ 文件归 Branch 9。

### 5.5 `scripts/` 28 .py + 1 `check.sh`

按 §10 子分类分组：

| 子分类 | 文件数 | 文件 |
|---|---|---|
| `CONFIG_INFRA` | 1 | `scripts/check.sh` |
| `KEEP_FROZEN_DIAGNOSTIC` | 5 | `run_continuous_smoothing_validation.py` / `_v2.py` / `run_real_continuous_smoothing_validation.py` / `_execute.py` / `_execute_v2.py` |
| `EVALUATION_SCRIPT` | 9 | `analyze_missed_false_exclusions_3b.py` / `audit_five_state_collapse_from_db.py` / `batch_run_exclusion_reliability_review_3c3.py` / `build_unsupported_explanation_taxonomy_3c1.py` / `correlate_contract_outcomes.py` / `decompose_unsupported_false_exclusions_3a.py` / `shadow_backtest_exclusion_reliability_review_3c5.py` / `summarize_confidence_calibration_inputs.py` / `validate_exclusion_actions_2e.py` / `validate_false_exclusions_2e_v2.py`（10 项） |
| `REPLAY_SCRIPT` | 4 | `build_03_replay_report.py` / `plan_contract_replay.py` / `run_1005_three_system_replay.py` / `run_contract_replay.py` |
| `DASHBOARD_SCRIPT` | 5 | `anti_false_exclusion_dashboard.py`（**DUPLICATE** `services/anti_false_exclusion_dashboard.py`）/ `dashboard_contract_extras.py` / `diff_latest_contract_payloads.py` / `inspect_latest_contract_payload.py` / `regime_diagnostics_dashboard.py`（**DUPLICATE** services 同名）/ `summarize_recent_contract_payloads.py` |
| `MIGRATION_SCRIPT` | 1 | `save_projection_records_smoke.py`（调 `run_projection_v2`；Bridge 期间保留） |
| `LOCAL_TOOL` | 1 | `soft_metadata_simulator.py`（**DUPLICATE** services 同名）|
| `CROSS_BRIDGE_CALLER` | 1 | `run_e2e_loop.py`（调 `predict.run_predict`；Bridge Phase 4） |

> scripts/ UNKNOWN = **0**。`DUPLICATE_FUNCTIONALITY` 标记 3 项（见 §9）。

### 5.6 `tests/` 165 文件（162 + 3 fixtures）

按 §11 子分类分组（不逐文件列；按命名 pattern 归组）：

| 子分类 | 文件数（估） | 代表文件 / 模式 |
|---|---|---|
| `CORE_BOUNDARY_TEST` | ~22 | `test_*_boundary.py`（projection_exclusion_decoupling / final_decision_aggregator_purification / confidence_result_wiring / cutoff_guard / memory_feedback_cutoff_guard / ai_summary / promotion_offline_only / predict_legacy_wrapper / x2 / x3 / x4b / 等） |
| `CONTRACT_TEST` | ~8 | `test_*_contract_fields.py`（confidence_system / exclusion_system / final_projection / peer_adjustment / primary_projection / simulated_trade）+ `test_run_predict_contract_alignment.py` + `test_record_02_*` |
| `CORE_MODULE_TEST`（per services 模块） | ~80 | `test_<service_module>.py` 一一对应（main_projection_layer / exclusion_layer / confidence_evaluator / final_decision / projection_orchestrator / projection_orchestrator_v2 / outcome_capture / review_* / memory_* / 等） |
| `LEGACY_BRIDGE_TEST` | 4 | `test_predict.py` / `test_predict_legacy_adapter.py` / `test_predict_legacy_v2_bridge.py` / `test_predict_legacy_wrapper_boundary.py` |
| `UI_TEST` | ~12 | `test_predict_tab_*.py` / `test_review_tab_*.py` / `test_command_bar_apptest.py` / `test_command_center_stability.py` / `test_history_tab.py` / `test_home_tab_navigation.py` / `test_research_loop_ui_apptest.py` / `test_control_tab_apptest.py` / `test_data_workbench_wiring.py` / `test_anti_false_exclusion_display.py` / `test_exclusion_reliability_review_ui.py` / `test_predict_tab_*` 系列 |
| `EVALUATION_TEST` | ~12 | `test_historical_replay_training.py` / `test_three_system_replay_audit_features.py` / `test_replay_validation_record_adapter.py` / `test_validate_*` / `test_analyze_missed_false_exclusions_3b.py` / `test_batch_run_*` / `test_build_unsupported_*` / `test_decompose_*` / `test_shadow_backtest_*` / `test_avgo_1000day_training.py` / `test_daily_training_*` / `test_audit_five_state_collapse_from_db.py` / `test_run_1005_three_system_replay_w4_guards.py` |
| `FROZEN_DIAGNOSTIC_TEST` | 5 | `test_continuous_smoothing_candidate.py` / `_v2.py` / `test_run_continuous_smoothing_validation.py` / `_v2.py` / `test_run_real_continuous_smoothing_validation*.py`（4 个） |
| `OFFLINE_ONLY_TEST` | 4 | `test_promotion_adoption_gate.py` / `test_promotion_execution_bridge.py` / `test_protection_layer_diagnostics.py` / `test_protection_layer_diagnostics_renderer.py` |
| `FIXTURE` | 3 | `tests/fixtures/app_analysis_context_fixture.py` / `coded_data_fixture.py` / `projection_output_samples.py` |
| `TOOL_TEST` | ~15 | `test_command_parser.py` / `test_command_projection_wiring.py` / `test_intent_planner.py` / `test_tool_router.py` / `test_plan_normalizer.py` / `test_ai_intent_parser.py` / `test_ai_task_parser.py` / `test_ai_summary.py` / `test_automation_wrapper.py` / `test_dashboard_view_model.py` / `test_data_query.py` / `test_date_range_*` / `test_error_taxonomy.py` / `test_evidence_trace.py` / `test_inspect_analysis.py` / `test_multi_symbol_view.py` / `test_state_label.py` / `test_stats_engine.py` / `test_dual_price_track.py` / `test_control_path.py` / `test_log_store.py` |

> tests/ UNKNOWN = **0**（按 pattern 全部归类）。
>
> **重要**：tests/ 任一类**都不删**；它们保护各自的契约。Bridge 测试
> （`test_predict_legacy_*`）随 Bridge 退出条件满足后才能 archive；
> FROZEN_DIAGNOSTIC 测试随候选模块共同保留。

### 5.7 `tasks/` 173 文件（按命名族分组）

| 命名族 | 文件数 | 类型 | 处置 |
|---|---|---|---|
| `STATUS.md` | 1 | task source of truth | `KEEP_ACTIVE`；按 CLAUDE.md hard rules 维护 |
| `record_*` | 36 | architecture / contract record | 全部 `KEEP_FROZEN_DIAGNOSTIC` + `DOC_ONLY`；byte-frozen（15 §6） |
| `step_*` | 101 | step checkpoint / design record | 全部 `KEEP_FROZEN_DIAGNOSTIC` + `DOC_ONLY`；byte-frozen |
| numeric `001_*` ~ `096_*` 等 | 35 | task definitions | 全部 `KEEP_FROZEN_DIAGNOSTIC` + `DOC_ONLY`；不直接删 |

> tasks/ UNKNOWN = **0**。全部 `DOC_ONLY` + `KEEP_FROZEN_DIAGNOSTIC`。
> 不允许 retro-edit。

### 5.8 `records/` 1 文件

- [records/03_replay_accuracy_and_exclusion_accuracy.md](records/03_replay_accuracy_and_exclusion_accuracy.md) — `DOC_ONLY` + `KEEP_FROZEN_DIAGNOSTIC`（候选 ARCHIVE 至 `archive/legacy/reports/`，待 16H 决定）

### 5.9 `archive/legacy/root_stubs/` 4 文件

- [archive/legacy/root_stubs/_DEPRECATED.md](archive/legacy/root_stubs/_DEPRECATED.md) — `ARCHIVE` marker
- [archive/legacy/root_stubs/confidence_engine.py](archive/legacy/root_stubs/confidence_engine.py) — `ARCHIVE`
- [archive/legacy/root_stubs/contradiction_engine.py](archive/legacy/root_stubs/contradiction_engine.py) — `ARCHIVE`
- [archive/legacy/root_stubs/risk_model.py](archive/legacy/root_stubs/risk_model.py) — `ARCHIVE`

### 5.10 `logs/` tracked evidence 21 文件

| 子目录 | 文件数 | 处置 |
|---|---|---|
| `logs/historical_training/03_fresh_replay/` | 7 | `KEEP_FROZEN_DIAGNOSTIC`（3R-3 fresh replay；15 §6 锁定） |
| `logs/historical_training/exclusion_action_validation_2e/` | 2 | `KEEP_FROZEN_DIAGNOSTIC` |
| `logs/historical_training/exclusion_action_validation_2e_v2/` | 2 | `KEEP_FROZEN_DIAGNOSTIC` |
| `logs/technical_features/exclusion_reliability_review_batch_3c3/` | 2 | `KEEP_FROZEN_DIAGNOSTIC` |
| `logs/technical_features/exclusion_reliability_shadow_backtest_3c5/` | 2 | `KEEP_FROZEN_DIAGNOSTIC` |
| `logs/technical_features/false_bigup_bigdown_missed_residual_3b/` | 2 | `KEEP_FROZEN_DIAGNOSTIC` |
| `logs/technical_features/false_bigup_bigdown_support_breakdown_3a/` | 2 | `KEEP_FROZEN_DIAGNOSTIC` |
| `logs/technical_features/unsupported_explanation_taxonomy_3c1/` | 2 | `KEEP_FROZEN_DIAGNOSTIC` |

> logs/ UNKNOWN = **0**。全部 tracked evidence 已结案；保留为历史参考。

### 5.11 `.claude/` infra（不在本 repo 业务范围）

- `.claude/CLAUDE.md` / `.claude/CHECKLIST.md` / `.claude/PROJECT_STATUS.md` /
  `.claude/TASK_TEMPLATE.md` — `CONFIG_INFRA` + `DOC_ONLY`
- `.claude/agents/` / `.claude/skills/` — `CONFIG_INFRA`（Claude Code agent / skill 配置）
- `.claude/handoffs/task_089_post_pr_cleanup.md` — `DOC_ONLY` + 14L A2 / 14M deliberate keep local
- `.claude/worktrees/` — `RAW_ARTIFACT`（已 14K ignored；harness 自动管理）

---

## 6. CORE 九分支完整站队

### Branch 1：Data Layer

**Confirmed**：`data_fetcher.py` / `services/market_data_store.py` /
`services/data_query.py` / `services/record_reader.py` /
`services/real_regime_label_provider.py`（5）

**Cross-layer**：`scanner.py`（B1+B2+B3）/ `encoder.py`（B1+B2）

**Unresolved**：无

**Next action**：16H/16I 拆 scanner / encoder 的 Data 部分；hard rule 2 锁定不可重写

### Branch 2：Feature Layer

**Confirmed**：`feature_builder.py` / `services/features_20d.py` /
`services/regime_features_builder.py` / `services/regime_labels_builder.py` /
`services/state_label.py`（5）

**Cross-layer**：`matcher.py`（B2+B3）/ `services/projection_chain_contract.py`（B2 feature + B6 payload）

**Future new**：`services/peer_alignment.py`（17A 候选；从 `exclusion_layer` 抽出）

**Unresolved**：无

**Next action**：16C 决定 15d 迁移；16I PR 拆 projection_chain_contract

### Branch 3：Projection System

**Confirmed**：`services/main_projection_layer.py`（核心）

**Internal helpers**：`services/projection_preflight.py` / `services/projection_rule_preflight.py`

**Cross-layer / candidate**：`services/five_state_margin_policy.py` / `matcher.py` 结构判断部分

**LEGACY (V2 chain step)**：`services/primary_20day_analysis.py` / `services/historical_probability.py`

**Unresolved**：`services/primary_bias_diagnosis.py`（UNKNOWN — 是诊断还是决策？）

**Next action**：16E PR-2 删 `exclusion_result` 形参；schema 对齐 07A；16I 决定是否合并 V2 chain step 到 main_projection

### Branch 4：Exclusion System

**Confirmed**：`services/exclusion_layer.py`（核心）

**Cross-layer / diag**：`services/anti_false_exclusion_audit.py` / `services/anti_false_exclusion_dashboard.py` / `services/big_up_contradiction_card.py` / `services/big_down_tail_warning.py` / `services/exclusion_reliability_review.py`

**Frozen**：`services/continuous_smoothing_candidate.py` / `_v2.py`

**Next action**：16C schema 对齐 07B；16E PR-1 `build_peer_alignment` 迁出；16H 决定 anti_false_exclusion / big_*_card 归位

### Branch 5：Confidence System

**Confirmed**：`services/confidence_evaluator.py`（核心）

**Data prep**：`services/contract_calibration_inputs.py`

**Unresolved**：`services/active_rule_pool*.py`（5 个，与 promotion 命名空间共享）

**Next action**：16E PR-3 key 对齐 + 接 calibration_context；16H 决定 active_rule_pool* 归位

### Branch 6：Final Report Layer

**Confirmed**：`services/final_decision.py`（核心）/ `services/projection_output_contract.py`（外部 schema validator）/ `services/log_store.py`（持久化）

**Cross-layer**：`services/prediction_store.py`（B6+B7）/ `services/projection_record_store.py`（B6+B7）/ `services/soft_metadata_injection.py`（B6+B7）

**Renderers (cross B6/B9)**：`services/projection_three_systems_renderer.py` / `services/projection_narrative_renderer.py`

**LEGACY**：`services/predict_summary.py` / `services/consistency_layer.py`（合并到 confidence_evaluator）/ `services/ai_summary.py`（default-disabled）

**Future new**：`services/architecture_orchestrator.py`（16I 起；未来唯一主入口）

**Dormant?**：`services/projection_output_adapter.py`（UNKNOWN — docstring 写"not yet wired"）

**Next action**：16I 选定唯一 schema；16I 合并 consistency_layer

### Branch 7：Review & Learning Layer

**Confirmed**：`services/outcome_capture.py` / `services/review_orchestrator.py` / `services/review_center.py` / `services/review_analyzer.py` / `services/review_classifier.py` / `services/review_comparator.py` / `services/review_agent.py` / `services/review_store.py` / `services/memory_store.py` / `services/memory_feedback.py` / `services/projection_memory_briefing.py` / `services/pre_prediction_briefing.py` / `services/projection_review_closed_loop.py` / `services/error_taxonomy.py`（14）

**Internal helpers**：`services/cutoff_guard.py`（11D guard）

**Cross-layer**：`services/prediction_store.py`（B6+B7）/ `services/projection_record_store.py`

**Unresolved**：`services/rule_lifecycle.py` / `services/rule_scoring.py`（与 promotion 命名空间共享）

**Risk**：`pre_prediction_briefing` 仍参与 `predict.py:1357 _apply_briefing_caution` mutate `final_confidence`（Bridge 旧行为）

**Next action**：16I 把 caution 移到 Final Report 展示；16H 决定 rule_lifecycle / rule_scoring 隔离

### Branch 8：Evaluation Layer

**Confirmed**：`services/historical_replay_training.py` / `services/three_system_replay_audit.py` / `services/replay_record_wiring.py` / `services/replay_validation_record_adapter.py` / `services/contract_replay_planner.py` / `services/contract_outcome_correlation.py` / `services/regime_validation_helper.py` / `services/stats_engine.py` / `services/avgo_1000day_training.py` / `services/daily_training_pipeline.py` / `services/daily_training_summary.py`（11）

**Dashboard tools**：`services/contract_payload_diff.py` / `services/contract_payload_extras_dashboard.py` / `services/contract_payload_inspector.py` / `services/contract_payload_trend.py`（4）

**Cross-layer (B8 + Bridge caller)**：`services/contract_replay_writer.py`（调 `predict.run_predict`）

**Cross-layer (B8 + B9)**：`services/regime_diagnostics_dashboard.py`

**Root entrypoint (Branch 8 入口)**：`run_pipeline.py` / `run_1000day.py` / `stats_reporter.py` / `research.py`（候选）

**Scripts (Branch 8 离线工具)**：scripts/ 中的 EVALUATION_SCRIPT / REPLAY_SCRIPT / DASHBOARD_SCRIPT 全部归 Branch 8 工具

**Next action**：Bridge Phase 4 时 `contract_replay_writer` 切到 `architecture_orchestrator`；16H 统一 evaluation 输出存储位置

### Branch 9：UI / Presentation Layer

**Confirmed**：`app.py` + 全部 17 个 ui/ 文件

**Cross-layer (UI + 工具子层)**：13 个 services TOOL_LAYER 模块（command-bar / parser / dashboard helpers）

**Renderers from services/**：`services/projection_three_systems_renderer.py` / `services/projection_narrative_renderer.py`（候选 Branch 9 或 Branch 6 内部 render）

**Next action**：Bridge Phase 3 时 `ui/predict_tab.py` 切新 schema；16H 决定 TOOL_LAYER 是否成为 Branch 9 子层

---

## 7. TEMP_MIGRATION_BRIDGE 完整站队

| 类别 | 内容 |
|---|---|
| Bridge **services** 2 项 | `services/predict_legacy_adapter.py` / `services/predict_legacy_v2_bridge.py` |
| Bridge **root .py** 1 项 | `predict.py` |
| Bridge **schema 字段** 8 项 | `final_bias` / `final_confidence` / `confidence` / `primary_projection` / `peer_adjustment` / `final_projection` / `path_risk` / `peer_path_risk_adjustment`（定义在 `predict.py:297` `PredictResult` TypedDict） |
| **`run_predict` 直接 caller**（必须迁移）5 项 | `ui/predict_tab.py:1410` / `services/projection_orchestrator.py:107` / `services/contract_replay_writer.py` / `services/predict_legacy_v2_bridge.py:80` / `scripts/run_e2e_loop.py:108` |
| **legacy 字段读写方** | UI 主面板 metric / panel（`ui/predict_tab.py`）；replay 写入（`services/contract_replay_writer.py`）；V1 链 summary（`services/predict_summary.py`） |

**1.0 重申**：

- 不是正式架构
- 不能扩大依赖
- 退出路线沿用 1.0 §10 / 16C §11 / 16D §10 的 6 项退出条件 / 8 阶段
- 当前进度：**0/6 完全满足**（与 16B §6 一致）

---

## 8. LEGACY_ACTIVE_DEPENDENCY 完整站队

| 模块 | active caller | 为什么不能删 | 退出 active path 前置条件 |
|---|---|---|---|
| `services/projection_orchestrator.py` | `services/projection_orchestrator_v2.py:16` | V2 反向回调 V1 → `predict.run_predict` | 16I 切断 V2 → V1 反向调用 |
| `services/projection_orchestrator_v2.py` | `services/projection_entrypoint.py:7`、`services/projection_v2_adapter.py:12`、`services/historical_replay_training.py:101`、`scripts/save_projection_records_smoke.py:441`、`predict.py:1340`（lazy） | 当前 V2 主链入口；多入口依赖 | 16I `architecture_orchestrator` 上线 + 5 个 caller 全部迁移 |
| `services/home_terminal_orchestrator.py` | `app.py:86, 1899` | app.py 主页主链；持核心逻辑 | 16I 内部实现替换为 `architecture_orchestrator` 薄包装；保留作 UI orch |
| `services/projection_entrypoint.py` | 部分 services / scripts；包装 V2 raw → projection_three_systems | 与 V2 主入口绑定 | V2 主入口决定后随之迁移 |
| `services/projection_v2_adapter.py` | 部分 services | adapter 性质 | 16I Phase 7 archive |
| `services/projection_orchestrator_preflight.py` | V1 / V2 共用 preflight | 与 V1/V2 绑定 | 16I 合并到 `architecture_orchestrator` 内部 preflight |
| `services/primary_20day_analysis.py` | `projection_orchestrator_v2._build_primary_analysis` | V2 chain step；与 main_projection_layer 重叠 | 16I 决定合并 vs archive |
| `services/peer_adjustment.py` | `projection_orchestrator_v2._build_peer_adjustment` | V2 chain step；调整推演方向语义被 1.0 §6/8 否决 | 16I 拆解：peer 信号 → Branch 2，"调整"语义 archive |
| `services/historical_probability.py` | `projection_orchestrator_v2._build_historical_probability` | V2 chain step | 16I 决定合并到 main_projection 或 archive |
| `services/predict_summary.py` | `services/projection_orchestrator.py:22`（V1 链） | V1 链 summary | V1 不再被调用后随之 archive |
| `services/consistency_layer.py` | `home_terminal_orchestrator.py:22`、`projection_orchestrator_v2.py:23` | 与 confidence_evaluator agreement 重叠 | 16I 合并到 confidence_evaluator |
| `services/ai_summary.py` | UI / 链 | 11F default-disabled；保留为 Branch 6 narrative 选项 | **不**deprecate；不解禁 default |

> 共 12 项。全部**当前不能删**。

---

## 9. CROSS_LAYER / DUPLICATE 模块

### 9.1 CROSS_LAYER（跨分支模块）— 11 项

（详见 §5.3.15 表）

### 9.2 DUPLICATE_FUNCTIONALITY（重名 / 功能重复）— 5 组

| 组 | 同名 / 重复模块 | 16H 决策方向 |
|---|---|---|
| `regime_diagnostics_dashboard` | `services/regime_diagnostics_dashboard.py` ↔ `scripts/regime_diagnostics_dashboard.py` | 16H：拆 services 为数据组装、scripts 为离线 entrypoint；保持单一 source of truth |
| `anti_false_exclusion_dashboard` | `services/anti_false_exclusion_dashboard.py` ↔ `scripts/anti_false_exclusion_dashboard.py` | 同上 |
| `soft_metadata_simulator` | `services/soft_metadata_simulator.py` ↔ `scripts/soft_metadata_simulator.py` | 同上 |
| `consistency_layer` vs `confidence_evaluator._compute_agreement` | `services/consistency_layer.py` ↔ `services/confidence_evaluator.py` 内 agreement 计算 | 16I：合并到 confidence_evaluator |
| `peer_adjustment` vs peer_alignment | `services/peer_adjustment.py` 中 peer 信号生成 ↔ 未来 `services/peer_alignment.py` | 16I：peer 信号 → Branch 2 Feature；"调整推演方向"语义 archive |
| `primary_20day_analysis` vs `main_projection_layer` | `services/primary_20day_analysis.py` ↔ `services/main_projection_layer.py` | 16I：决定合并方案 |

### 9.3 LEGACY_ACTIVE_DEPENDENCY 中的功能重复

- `projection_orchestrator.py`（V1）vs `projection_orchestrator_v2.py`（V2）vs `home_terminal_orchestrator.py`（home 主链）— **3 套并行 orchestrator**，16I 收敛到唯一 `architecture_orchestrator`

---

## 10. scripts/ 分解

（详见 §5.5 表）

| 子分类 | 文件 |
|---|---|
| `CONFIG_INFRA` | check.sh |
| `KEEP_FROZEN_DIAGNOSTIC` | continuous_smoothing 5 个 |
| `EVALUATION_SCRIPT` | 10 个（analyze / audit / batch / build / correlate / decompose / shadow / summarize / validate ×2） |
| `REPLAY_SCRIPT` | 4 个 |
| `DASHBOARD_SCRIPT` | 6 个（含 3 个 DUPLICATE） |
| `MIGRATION_SCRIPT` | save_projection_records_smoke |
| `LOCAL_TOOL` | soft_metadata_simulator（DUPLICATE） |
| `CROSS_BRIDGE_CALLER` | run_e2e_loop |

> **本轮不运行任何 script**；仅分类。

---

## 11. tests/ 分解

（详见 §5.6 表）

按 **保护对象** 分类，每类的"保留 / 退出"路径：

| 子分类 | 文件数 | 保留 / 退出 |
|---|---|---|
| `CORE_BOUNDARY_TEST` | ~22 | **永久保留**；contract 守门 |
| `CONTRACT_TEST` | ~8 | **永久保留**；schema 守门 |
| `CORE_MODULE_TEST` | ~80 | 保留；随核心模块演进 |
| `LEGACY_BRIDGE_TEST` | 4 | 随 Bridge 退出条件满足后 archive |
| `UI_TEST` | ~12 | 保留；随 UI 迁移更新 |
| `EVALUATION_TEST` | ~12 | 保留 |
| `FROZEN_DIAGNOSTIC_TEST` | 5 | 永久保留（与 frozen 候选共存） |
| `OFFLINE_ONLY_TEST` | 4 | 永久保留 |
| `FIXTURE` | 3 | 保留 |
| `TOOL_TEST` | ~15 | 保留 |

> **测试不是垃圾**。即使旧也不能删；它们保护契约 / 边界 / mutation 表面。
> 任何 archive 必须满足 1.0 §10 退出条件 + 用户单独确认。

---

## 12. tasks / records / archive / logs 分解

| 区域 | 处置 |
|---|---|
| `tasks/STATUS.md` | `KEEP_ACTIVE`；CLAUDE.md hard rule 维护 |
| `tasks/record_*` 36 个 | `DOC_ONLY` + `KEEP_FROZEN_DIAGNOSTIC`；byte-frozen（15 §6） |
| `tasks/step_*` 101 个 | 同上 |
| `tasks/<numeric>_*` 35 个 | 同上 |
| `records/03_replay_accuracy_and_exclusion_accuracy.md` | `DOC_ONLY`；候选 ARCHIVE 至 `archive/legacy/reports/`（待 16H 决定） |
| `archive/legacy/root_stubs/` 4 个 | `ARCHIVE` 已 quarantine；不动 |
| logs/ tracked 21 个 | `KEEP_FROZEN_DIAGNOSTIC`；15 §6 锁定 |
| `.claude/handoffs/task_089_post_pr_cleanup.md` | `DOC_ONLY` + 14L A2 / 14M deliberate keep local untracked |
| 未 tracked / ignored raw（DB backup / replay raw / `.claude/worktrees/`） | `RAW_ARTIFACT`；14K 已 ignore；不进入 repo |

---

## 13. UNKNOWN_REVIEW_REQUIRED 收敛情况

| 范围 | 16B 计数 | 16G 后计数 | 备注 |
|---|---|---|---|
| `services/` | ≥ 35 | **9** | 5 active_rule_pool* + projection_output_adapter + primary_bias_diagnosis + inspect_analysis + five_state_margin_policy |
| root `*.py` | 1 | **1** | research.py（仍未通读） |
| `ui/` | 0 | **0** | 全部归 Branch 9 |
| `scripts/` | 0 | **0** | 全部按子分类归位 |
| `tests/` | — | **0** | 按 pattern 归类 |
| `tasks/` / `records/` / `archive/` / `logs/` | — | **0** | 全部 `DOC_ONLY` / `ARCHIVE` / `KEEP_FROZEN_DIAGNOSTIC` |
| **TOTAL** | **35+** | **10** | 降幅 ≈ 70% |

**16G-2 deep audit 候选**（剩余 10 项）：

1. `services/active_rule_pool.py` — 主体；与 promotion 隔离 + B5/B7 归位
2. `services/active_rule_pool_calibration.py` — 候选 B5
3. `services/active_rule_pool_drift.py` — 候选 B5/B7
4. `services/active_rule_pool_export.py` — 候选 B7/B8
5. `services/active_rule_pool_validation.py` — 候选 B8
6. `services/projection_output_adapter.py` — docstring 写 dormant；实际是否被调用？
7. `services/primary_bias_diagnosis.py` — 是诊断还是决策？
8. `services/inspect_analysis.py` — 候选 B7 / B9 / TOOL
9. `services/five_state_margin_policy.py` — 候选 B3 内部
10. `research.py` — 顶层 research entrypoint；用途不明

**降到接近 0 的障碍**：

- active_rule_pool* 5 个的归属取决于"calibration table 接入路径"（16I 决定）；没有这一决定，5 个无法精确站队
- projection_output_adapter 需要 grep active import 才能定 dormant vs active
- 其余 4 个需要 deep audit 内部行为

> 推荐：进入 16H 之前，**可选**插一步 **16G-2** 做剩余 10 项的 deep import
> graph audit；或在 16H 内一并处理。

---

## 14. 清场候选初稿

> **本轮不实施**任何"删除 / 移动"；以下仅是 16H 决策表的输入。

### 14.1 可未来 archive

| 候选 | 前置条件 | 风险 | 用户确认 |
|---|---|---|---|
| `services/predict_legacy_v2_bridge.py` | active import = 0（已满足） | tests 仍引用；boundary suite 必须改读 archive 副本或断言"已 archive" | 必需 |
| `services/projection_orchestrator.py` + `services/projection_orchestrator_v2.py` + 8 个 LEGACY orchestrator helpers | Bridge #4/#5/#6 全部满足 | 多入口；必须按 16I refactor 分阶段 | 必需 |
| `services/predict_summary.py` | V1 链不再被调用 | UI / contract_replay_writer 必须先迁完 | 必需 |
| `services/consistency_layer.py` | 16I 把逻辑吸收到 confidence_evaluator | tests 调整 | 必需 |
| `records/03_replay_accuracy_and_exclusion_accuracy.md` | grep 确认无引用 | 历史价值 | 推荐 |
| `AVGO_Task1_8_Validation_Report.md`（root） | 移到 `archive/legacy/reports/` | 历史价值 | 推荐 |

### 14.2 可未来 quarantine（move to archive/legacy/）

| 候选 | 前置条件 |
|---|---|
| `services/peer_adjustment.py` 的"调整推演方向"语义 | 16I 拆解 + caller 全部迁完 |
| `services/primary_20day_analysis.py` | 16I 决定合并 vs archive |
| `services/historical_probability.py` | 16I 决定合并 vs archive |

### 14.3 可未来 delete（**仅在** active import = 0 + archive 安全网完成 + 用户确认 后）

| 候选 | 前置条件 |
|---|---|
| 暂无 — 16D §3 已锁"先 archive 再 delete" |

### 14.4 必须先断 caller

| 模块 | 当前 caller |
|---|---|
| `predict.py` | UI / replay / scripts 5 处 |
| `projection_orchestrator.py` | V2 |
| `projection_orchestrator_v2.py` | 5 处 |
| `predict_legacy_adapter.py` | `predict.py:44` |
| `consistency_layer.py` | home_terminal + V2 |

### 14.5 必须保留 frozen

| 模块 | 原因 |
|---|---|
| `services/continuous_smoothing_candidate.py` / `_v2.py` | 06 §8 / 07B §11 / 07C §12 / 07D §12 / 1.0 §6.17 永久禁活作为 candidate |
| `archive/legacy/root_stubs/*` | 14D 已 quarantine |
| logs/ 21 tracked evidence | 15 §6 锁定 |
| tasks/ 173 records | byte-frozen；不允许 retro-edit |

### 14.6 必须移出 repo 的 raw artifact 类型

| 类型 | 当前状态 | 处置 |
|---|---|---|
| `avgo_agent.db`（root，**tracked**） | tracked | **16H 紧急议题**：DB 不应 tracked；推荐 untrack + 加入 `.gitignore` + 用户单独确认是否保留历史副本 |
| `avgo_agent.db.backup_*`（7 个） | 14K ignored；本地保留 | 用户单独确认 MOVE / DELETE |
| 4 套 untracked replay / regime validation 子目录 | 14K ignored；本地保留 | 用户单独确认；可保留 markdown summary |
| `.claude/worktrees/` 26 个 | 14K ignored；harness 自动管理 | 不在 16D 范围 |

> **`avgo_agent.db` 是 16G 发现的额外问题**：当前 root 下有一个 tracked
> SQLite 文件 `avgo_agent.db`。`.gitignore` 第 24 行 `avgo_agent.db.backup_*`
> 仅覆盖 backup 文件，**不**覆盖 `.db` 本体。16H 必须决定是否 untrack。
> 本轮**不**改 `.gitignore`，**不**移动该文件。

---

## 15. 对 16H 的输入

16H（Repository Clearing Decision Table）应把 16G 的分类转换成：

| 决策标签 | 含义 |
|---|---|
| `KEEP` | 保留在主仓库；属正式架构 |
| `MOVE_OUTSIDE_REPO` | 移到本地或外部 archive；不进 repo |
| `ARCHIVE_IN_REPO` | 移到 `archive/legacy/<sub>/`；保留为历史证据 |
| `QUARANTINE` | 加 deprecation marker；待 caller 迁移完成后再 archive |
| `DELETE_NOW` | 立即可删（active import = 0 + 用户确认 + 已 archive） |
| `DELETE_LATER` | 满足前置条件后可删 |
| `MIGRATE_CALLER_FIRST` | 必须先迁移 caller 才能动 |
| `DEEP_AUDIT_REQUIRED` | 16G-2 / 16I deep audit 之前不能落决策 |

**16H 必须回答的关键议题**：

1. `avgo_agent.db` 是否 untrack（紧急）
2. Bridge 8 个 schema 字段在 standard payload `compatibility_metadata`
   中保留多久（Phase 8 整段删除）
3. 12 个 LEGACY_ACTIVE_DEPENDENCY 模块的 archive 顺序
4. 5 个 active_rule_pool* 的归属（B5 / B7 / B8 / OFFLINE_ONLY）
5. 3 组 DUPLICATE_FUNCTIONALITY（services/ ↔ scripts/ 同名）的解决方向
6. 4 套 untracked raw artifact 子目录的处置
7. 7 个 DB backup 的 MOVE / DELETE
8. records/ + AVGO_Task1_8_Validation_Report.md 的 ARCHIVE_IN_REPO 决定
9. tests/ Bridge 测试的 archive 时机
10. `pre_prediction_briefing._apply_briefing_caution` 的迁移方案（mutate confidence → final_report 展示）

---

## 16. 不允许事项

本轮 + 16G-2（如有） + 16H + 16I 全部严守：

- ❌ 不改代码（`.py` 文件零修改）
- ❌ 不启动 peer_alignment 或任何 16E §3 列出的 PR
- ❌ 不做局部 patch
- ❌ 不删除文件
- ❌ 不移动文件
- ❌ 不修改 `.gitignore`
- ❌ 不处理 handoff
- ❌ 不处理 logs / DB backup / `.claude/worktrees/`
- ❌ 不跑 evaluation / replay / validation
- ❌ 不进入 3R-5 / 3R-6（1.0 §12 / 16A §18 / 16C §13 / 16F §9 锁定）
- ❌ 不输出 trading action / hard / forced / required
- ❌ 不复活 `continuous_smoothing*` / `archive/legacy/root_stubs/*` /
  promotion 三模块 / `protection_layer_diagnostics`
- ❌ 不默认迁移 `run_predict` 到 V2
- ❌ 不借 16G / 16H / 16I 任一文档轮顺手改代码
- ❌ 不借 16G 决策表顺手 commit 任何 PR-1 work（worktree 已 discard，干净）

---

## 17. 推荐下一步

**首选**：

> **Step 16H：Repository Clearing Decision Table**

理由：

- 16G 已把全仓库模块分类完毕；`UNKNOWN` 从 35+ 降到 10
- 16H 把 §15 的 8 个决策标签应用到每个文件，并优先回答 §15 末尾的 10 个
  关键议题
- 16I 在 16H 决策表之上重新设计核心链 refactor PR 顺序

**备选（如必要）**：

> **Step 16G-2：Deep Import Graph Audit for Remaining UNKNOWN**

仅当 §13 列出的 10 项 UNKNOWN 影响 16H 决策表时使用；否则可在 16H 内一并
处理。

**默认**：直接进 16H。

**不推荐**：

- 不推荐借 16G 顺手做代码改动
- 不推荐跳过 16H 直接进 16I / 17A
- 不推荐借任一步解锁 3R-5 / 3R-6

---

## 18. 严守边界

本轮 Step 16G **只**写 full module decomposition / stand-up 文档：

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
- ❌ 未启动 peer_alignment PR / 未做任何局部 patch
- ❌ 未 commit / 未 push（按本轮指令）

唯一新增文件：[tasks/record_16g_full_module_decomposition_standup.md](tasks/record_16g_full_module_decomposition_standup.md)（本文件）。

后续修改路径：任何对 §3 扫描范围 / §4 标签 / §5 总 inventory / §6
九分支 / §7 Bridge / §8 LEGACY / §9 CROSS / DUPLICATE / §10 scripts /
§11 tests / §12 tasks records archive logs / §13 UNKNOWN 收敛 / §14
清场候选 / §15 16H 输入 / §16 禁止 / §17 下一步 的调整，都必须**显式
更新本文件**；同时检查是否需要同步更新 1.0 / 16A / 16B / 16C / 16D /
16E / 16F。
