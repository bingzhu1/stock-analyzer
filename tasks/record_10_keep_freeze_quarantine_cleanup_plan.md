# 10记录：Keep / Freeze / Quarantine / Cleanup Plan

> 本记录是依据 06–09 文档对当前项目模块所做的**只读动作计划**。
>
> 本轮**未改代码、未删文件、未移动文件、未写 DB、未跑 validation、
> 未处理 untracked / DB backup / stash / .claude/worktrees/、未进入 3R-5 / 3R-6、
> 未新增 candidate、未复活 continuous_smoothing、未修 RISK-1 / RISK-2 / RISK-6 /
> RISK-8 / RISK-9**。

---

## 1. Plan 目的

依据 Step 09 inventory 的 105 个 services + 17 个 ui + 29 个 scripts + 仓库根
代码 + logs / 文档 / backup 等对象，把每个模块**预先归类**到下列动作分桶之一：

- KEEP_ACTIVE
- KEEP_INFRA
- FIX_REQUIRED（需 Step 11 设计 + Step 12 实施）
- FREEZE_DIAGNOSTIC
- QUARANTINE_LATER
- CLEANUP_LATER
- UNKNOWN_REVIEW_REQUIRED

本轮**只写动作计划**：

- **不**实际移动 / 删除 / 修改任何文件
- **不**触发任何 boundary fix（保留给 Step 11/12）
- **不**清理 untracked / DB backup / logs / .claude/worktrees/
- **不**进入 3R-5 / 3R-6
- **不**新增 candidate / **不**复活 continuous_smoothing

本计划是 Step 11 boundary enforcement plan 的**输入约束**：Step 11/12 只能针对
本计划中标 `FIX_REQUIRED` 的对象设计修复，**不允许**把 cleanup 与 boundary fix
混在一起做。

---

## 2. 分类定义

| 类别 | 含义 | 本轮是否动作 | 何时动作 |
|---|---|---|---|
| `KEEP_ACTIVE` | 继续作为在线 active path 保留 | 不动 | 永久保留（除非 contract 变化） |
| `KEEP_INFRA` | 数据 / 存储 / 工具基础设施保留 | 不动 | 永久保留 |
| `FIX_REQUIRED` | 不是清理对象，而是必须在 Step 11/12 修复的 active 风险 | 不动 | **Step 11 设计 + Step 12 最小实施** |
| `FREEZE_DIAGNOSTIC` | 保留作为诊断 baseline，不再 active 开发，不复活为 candidate | 不动 | 永久保留 |
| `QUARANTINE_LATER` | 未来隔离（move 到隔离目录或显式 deprecation 标记） | 不动 | **Step 14**（在 Step 11/12/13 完成后） |
| `CLEANUP_LATER` | 未来可删除或归档 | 不动 | **Step 14**（在 Step 11/12/13 完成后 + backup/evidence policy 明确后） |
| `UNKNOWN_REVIEW_REQUIRED` | 暂时不确定，需后续二次审查 | 不动 | Step 11 启动前的 spot-check / Step 11 设计阶段顺手解决 |

> **关键原则**：cleanup / quarantine 必须**晚于** boundary fix。先消除 contract
> 违规，再清理冗余；不允许"借清理之机偷偷改 active path"。

---

## 3. 总体计划结论

> **PASS_WITH_ACTION_PLAN**

- 可以进入 Step 11 boundary enforcement plan。
- **本轮不需要立即删除任何文件**。
- **本轮不需要立即冻结任何 active path**：HIGH_RISK 路径（projection_orchestrator_v2 /
  main_projection_layer / home_terminal_orchestrator / final_decision /
  predict.py / ai_summary）目前**仍是用户可见的活跃路径**，立即冻结会破坏
  Streamlit 展示链路；Step 11 必须设计**最小切换**而不是粗暴禁用。
- **不存在 blocker**：所有 HIGH_RISK 都是已存数月的存量结构；Step 11/12 在
  不动用户可见展示的前提下可推进。
- continuous_smoothing v1/v2 的 FREEZE 状态**已就位**（Step 09 §12 / 07B §11 /
  07D §12），本轮无需额外动作。
- 死代码（confidence_engine.py / contradiction_engine.py / risk_model.py）已确认
  无 active import，但因为它们是 step_1a 时代的 v1 stub，可能仍被 docs 引用，
  归 `CLEANUP_LATER`，**不**本轮删除。

---

## 4. KEEP_ACTIVE 清单

> 这些是已通过 Step 09 验证为 contract-clean 的 active path 模块，
> 应继续保留。Step 11 boundary 设计**不应**改动它们。

| path | belongs_to | reason | required_future_check |
|---|---|---|---|
| `services/exclusion_layer.py` | ACTIVE_EXCLUSION | 唯一合规 active exclusion 入口；仅市场特征输入；07B §3.1 白名单 | Step 11 验证不被未来 candidate 污染 |
| `services/primary_20day_analysis.py` | ACTIVE_PROJECTION | AVGO 自身 20 日结构分析；07A §3.1 白名单 | Step 11 boundary fix 不应改其接口 |
| `services/peer_adjustment.py` | ACTIVE_PROJECTION | NVDA / SOXX / QQQ 同行修正；07A §3.1 白名单 | 同上 |
| `services/historical_probability.py` | ACTIVE_PROJECTION | 历史相似样本概率；07A §3.1 白名单 | 同上 |
| `services/projection_entrypoint.py` (152 行) | ACTIVE_AGGREGATOR | V2 装配入口；不计算判断；CLEAN | Step 11 改 main_projection_layer 时此处 wiring 可能微调 |
| `services/projection_three_systems_renderer.py` (1019 行) | ACTIVE_AGGREGATOR | 06Q 落地的三系统并列展示；read-only reshape；schema 大致对齐 07A/07B/07C | Step 11 验证 schema 严格对齐 07A §9 / 07B §9 / 07C §9 草案 |
| `services/projection_narrative_renderer.py` | ACTIVE_AGGREGATOR | 纯 validator + enum mapping；无 LLM；CLEAN | — |
| `services/predict_summary.py` | ACTIVE_AGGREGATOR | 纯 mapper；无 LLM；CLEAN | — |
| `services/projection_chain_contract.py` | ACTIVE_AGGREGATOR | 字段 helper；纯 helper（builds fresh feature dict） | — |
| `services/projection_output_contract.py` | ACTIVE_AGGREGATOR | 字段 validator；纯 validator | Step 11 评估是否扩展为 07A–07D 的 contract enforcement validator |
| `services/projection_output_adapter.py` | ACTIVE_AGGREGATOR | 字段 adapter；docstring 自述 "Never mutates inputs" | — |
| `services/projection_v2_adapter.py` | ACTIVE_AGGREGATOR | 仅构建 legacy compat shell；不 mutate | — |
| `services/protection_layer_diagnostics.py` | ACTIVE_CONFIDENCE（display 类） | spec-lock：所有 hard / forced / required 标志 always False | — |
| `services/contract_calibration_inputs.py` | ACTIVE_CONFIDENCE | docstring 自述 "diagnostic 而非 engine"；不 mutate | — |
| `services/active_rule_pool.py` / `_calibration.py` / `_drift.py` / `_export.py` / `_validation.py` | ACTIVE_CONFIDENCE | offline calibration 套件 | — |
| `services/exclusion_reliability_review.py` | ACTIVE_CONFIDENCE | 否定可靠性历史命中率评价；属 07C 范畴 | Step 11 收敛 confidence 时纳入 |
| `services/big_up_contradiction_card.py` | ACTIVE_AGGREGATOR (display) | 展示卡 | Step 11 验证不写回 projection |
| `services/big_down_tail_warning.py` | ACTIVE_AGGREGATOR (display) | 展示警示 | 同上 |
| `services/anti_false_exclusion_dashboard.py` | ACTIVE_AGGREGATOR (display) | 看板 | Step 11 验证不写回 |
| `services/anti_false_exclusion_audit.py` | ACTIVE_EXCLUSION（审计性质） | 审计层 | Step 11 spot-check 是否读 projection（Step 09 标 UNKNOWN_RISK） |
| `services/dashboard_view_model.py` / `multi_symbol_view.py` / `inspect_analysis.py` | ACTIVE_AGGREGATOR (display) | 看板 view-model 类 | — |
| `services/evidence_trace.py` | ACTIVE_AGGREGATOR | 展示用证据追溯 | Step 11 验证不重新推理 |
| `services/projection_review_closed_loop.py` | ACTIVE_CONFIDENCE / 数据制品 | 复盘闭环 | Step 11 验证不回灌在线 |
| `app.py` (107KB) | ACTIVE_AGGREGATOR (UI) | Streamlit shell；无主动逻辑；CLEAN | Step 11 解耦 home_terminal 后 wiring 可能微调 |
| `ui/__init__.py` | ACTIVE_AGGREGATOR | 包初始化 | — |
| `ui/predict_tab.py` / `history_tab.py` / `home_tab.py` / `inspect_tab.py` / `research_tab.py` / `review_tab.py` / `scan_tab.py` / `control_tab.py` / `command_bar.py` | ACTIVE_AGGREGATOR (UI) | 各 tab 展示 | Step 11 验证不 in-place mutate v2_raw |
| `ui/labels.py` | ACTIVE_DATA_INFRA | UI 标签 | — |
| `ui/projection_v2_renderer.py` | ACTIVE_AGGREGATOR | 展示 v2_raw | — |
| `ui/anti_false_exclusion_display.py` / `big_up_contradiction_card.py` / `exclusion_reliability_review.py` / `protection_layer_diagnostics_renderer.py` | ACTIVE_AGGREGATOR | 展示组件；protection_layer_diagnostics_renderer 显式禁止 hard / forced / no_trade 字眼 | — |

---

## 5. KEEP_INFRA 清单

> 数据 / 存储 / 工具基础设施，永久保留。

| path | infra_type | reason | future_check |
|---|---|---|---|
| `data_fetcher.py` (5KB) | data | yfinance loader | — |
| `feature_builder.py` (4.5KB) | features | CLAUDE.md 硬规则保留 | — |
| `encoder.py` (5.6KB) | features | CLAUDE.md 硬规则保留 | — |
| `matcher.py` (8.3KB) | features | CLAUDE.md 硬规则保留 | — |
| `scanner.py` (28KB) | features | CLAUDE.md 硬规则保留 | — |
| `stats_reporter.py` (8KB) | reporting | 统计报告 | — |
| `services/market_data_store.py` | storage | 市场数据存储 | — |
| `services/data_query.py` | query | 数据查询 | — |
| `services/record_reader.py` | storage | 记录读取 | — |
| `services/log_store.py` | storage | 日志存储 | — |
| `services/prediction_store.py` | storage | 预测存储 | — |
| `services/projection_record_store.py` | storage | 推演 record 存储 | — |
| `services/outcome_capture.py` | storage | 结果捕获 | — |
| `services/memory_store.py` | storage | 记忆存储 | — |
| `services/regime_features_builder.py` / `regime_labels_builder.py` / `regime_validation_helper.py` / `real_regime_label_provider.py` / `regime_diagnostics_dashboard.py` | regime | regime 特征 / 标签 / 验证 / 看板 | — |
| `services/replay_record_wiring.py` / `replay_validation_record_adapter.py` / `three_system_replay_audit.py` | replay | offline replay | Step 11 验证不回灌 |
| `services/historical_replay_training.py` | training | offline；有 "no future leak" 注释（line 1-18） | — |
| `services/avgo_1000day_training.py` | training | offline 1000 天训练 | — |
| `services/daily_training_pipeline.py` / `daily_training_summary.py` | training | offline 日训练 | — |
| `services/contract_replay_planner.py` / `contract_replay_writer.py` | contract | offline contract replay | — |
| `services/contract_outcome_correlation.py` | analytics | offline 结果相关性 | — |
| `services/contract_payload_diff.py` / `_inspector.py` / `_trend.py` / `_extras_dashboard.py` | tools | contract payload 工具 | — |
| `services/state_label.py` / `error_taxonomy.py` / `comparison_engine.py` / `stats_engine.py` / `rule_lifecycle.py` / `rule_scoring.py` / `five_state_margin_policy.py` | utils | 工具层 | — |
| `services/features_20d.py` | features | 20 日特征 | — |
| `services/analysis_context.py` | utils | 上下文工具 | — |
| `services/agent_parser.py` / `agent_schema.py` / `ai_intent_parser.py` / `ai_task_parser.py` / `command_parser.py` / `intent_planner.py` / `plan_normalizer.py` / `tool_router.py` / `query_executor.py` / `openai_client.py` / `date_range_parser.py` | LLM intent / planner | LLM 接入；本身不在线产判断 | Step 11 验证除 ai_summary 外无 LLM 漏入 final-report |
| `run_1000day.py` / `run_pipeline.py` / `research.py` | entry | 入口脚本 | Step 11 spot-check |
| `scripts/run_1005_three_system_replay.py` / `run_contract_replay.py` / `plan_contract_replay.py` / `run_e2e_loop.py` / `save_projection_records_smoke.py` | scripts | offline replay / smoke / e2e | — |
| `scripts/correlate_contract_outcomes.py` / `summarize_recent_contract_payloads.py` / `summarize_confidence_calibration_inputs.py` / `diff_latest_contract_payloads.py` / `inspect_latest_contract_payload.py` / `audit_five_state_collapse_from_db.py` / `decompose_unsupported_false_exclusions_3a.py` / `analyze_missed_false_exclusions_3b.py` / `build_unsupported_explanation_taxonomy_3c1.py` / `batch_run_exclusion_reliability_review_3c3.py` / `shadow_backtest_exclusion_reliability_review_3c5.py` / `validate_exclusion_actions_2e.py` / `validate_false_exclusions_2e_v2.py` / `build_03_replay_report.py` / `dashboard_contract_extras.py` / `regime_diagnostics_dashboard.py` / `anti_false_exclusion_dashboard.py` | scripts | offline 报告 / 审计工具 | — |
| `scripts/check.sh` | scripts | 统一检查（CLAUDE.md 引用） | — |
| `logs/historical_training/{03_fresh_replay, exclusion_action_validation_2e, exclusion_action_validation_2e_v2}` | data artifacts | 已 commit 的离线训练制品 | Step 11 加 cutoff guard 后这些制品仍可作为离线参考 |
| `logs/technical_features/` | data artifacts | 技术特征 | — |
| `tests/` (148 个文件) | test infra | 测试基础设施 | Step 12 评估是否新增 07A–07D contract enforcement test |
| `tasks/` (146 个文件) | docs | 项目历史文档 / checkpoint | — |
| `requirements.txt` / `runtime.txt` / `.env.example` / `.gitignore` / `AGENTS.md` / `AVGO_Task1_8_Validation_Report.md` / `一键启动说明.md` / `启动博通系统.bat` / `启动博通系统.command` | meta | 项目元文件 | — |

---

## 6. FIX_REQUIRED 清单

> 这些是 Step 11 设计 + Step 12 实施的目标。本轮**不动**。

| risk_id | path | issue | contract violated | target_step | action_type |
|---|---|---|---|---|---|
| **RISK-1** | `services/projection_orchestrator_v2.py:109-116` + `services/main_projection_layer.py:255-274` | projection 把 `exclusion_result` 当输入，并强制把 `大涨` / `大跌` 得分置 0 | 07A §3.2、§10 | **Step 11 设计 → Step 12 实施** | 解耦 main_projection_layer：移除 exclusion 入参 + 删除 `_apply_exclusion`；exclusion 信号在 final_report 层并列展示 |
| **RISK-2** | `services/final_decision.py:280-303` + `:313-317` | aggregator 翻 direction、重算 confidence、apply preflight | 07D §5、§10；07A §8、07B §8、07C §8 | **Step 11 设计 → Step 12 实施** | 改造为纯 aggregate：选择 highest-confidence 的 system output 直接展示；preflight 影响移到 confidence；direction 翻转规则要么移到 projection 自身要么废弃 |
| **RISK-3** | confidence 散落在 `predict.py` / `services/final_decision.py:288-317` / `services/projection_three_systems_renderer.py:893-909` | 缺独立 confidence_evaluator 实现承载点 | 07C 整体 | **Step 11 设计 → Step 12 实施** | 收敛到 `services/confidence_evaluator.py`（候选名）；废弃 predict.py / final_decision 中的局部 confidence 重算；保留 `projection_three_systems_renderer.confidence_evaluator` 段为该 engine 的 read-only 展示 |
| **RISK-6** | `services/home_terminal_orchestrator.py:22, 145-152` | 与 RISK-1 完全相同的违规模式（exclusion → main_projection），由 app.py 调用 | 07A §3.2、§10 | **Step 11 设计 → Step 12 实施**（与 RISK-1 同步处理） | 与 RISK-1 一并解耦；保证 app.py 调用契约不破 |
| **RISK-7** | `services/memory_feedback.py` (61 行) + `projection_memory_briefing.py` + `projection_rule_preflight.py:260-264, 277` + `projection_orchestrator_v2.py:511-518` | active 链路缺 `created_date <= target_date` cutoff | 07A §3.2 future-leak、07C §3.3 在线 vs 离线 cutoff | **Step 11 设计 → Step 12 实施** | 在 `build_memory_feedback()` 与 `_review_loader()` 入口加 date filter；review records 早于或等于 target_date 才允许进入 |
| **RISK-8** | `predict.py:32-37, 185-193, 435-441, 561, 784, 962, 981, 1052-1055` | mixed projection + aggregator | 07A §5、07D §5 | **Step 11 设计 → Step 12 实施** | 拆分：`run_predict()` 仅调 `run_projection_entrypoint()` 取 v2_raw + three_systems；删除内部 `_confidence_from_score` / `_raise_confidence` / `_summarize` 等 final-confidence 重算逻辑；v1 路径若仍需保留则显式标记为 V1 legacy 并隔离 |
| **RISK-9** | `services/ai_summary.py:8` | `from services.openai_client import generate_text` → LLM 自由文本 | 07D §10（"句句必有出处"） | **Step 11 设计 → Step 12 实施** | 加 source attribution（每句必须附 `source_field` / `source_system`）+ opt-in feature flag；默认关闭；LLM 输出必须可追溯到三系统输出 |
| **RISK-10** | `services/active_rule_pool_promotion.py` + `services/promotion_adoption_gate.py` + `services/promotion_execution_bridge.py` | 当前 offline-only，但 bridge 结构存在被未来 active caller 启用的风险 | 07A §10 / 07C §11 潜在 | **Step 11 设计**（documentation-lock）；Step 12 不必修代码，只加 docstring + test 锁定 | documentation-lock：bridge `execution_enabled=False` 永久；任何 PR 启用 active caller 必须同步更新本 contract |

> **重要**：FIX_REQUIRED 清单**不包括** cleanup / quarantine 对象。Step 11/12 不允许借修复之机做清理。

---

## 7. FREEZE_DIAGNOSTIC 清单

> 保留作为 baseline。**不**删除、**不** active 使用、**不**复活为 candidate、
> **不**用于 Step 11 修复。

| 对象 | 状态 |
|---|---|
| `services/continuous_smoothing_candidate.py` | FREEZE_DIAGNOSTIC |
| `services/continuous_smoothing_candidate_v2.py` | FREEZE_DIAGNOSTIC |
| `scripts/run_continuous_smoothing_validation.py` | FREEZE_DIAGNOSTIC |
| `scripts/run_continuous_smoothing_validation_v2.py` | FREEZE_DIAGNOSTIC |
| `scripts/run_real_continuous_smoothing_validation.py` | FREEZE_DIAGNOSTIC |
| `scripts/run_real_continuous_smoothing_validation_execute.py` | FREEZE_DIAGNOSTIC |
| `scripts/run_real_continuous_smoothing_validation_execute_v2.py` | FREEZE_DIAGNOSTIC |
| `tests/test_continuous_smoothing_candidate.py` | FREEZE_DIAGNOSTIC |
| `tests/test_continuous_smoothing_candidate_v2.py` | FREEZE_DIAGNOSTIC |
| `tests/test_run_continuous_smoothing_validation.py` | FREEZE_DIAGNOSTIC |
| `tests/test_run_continuous_smoothing_validation_v2.py` | FREEZE_DIAGNOSTIC |
| `tests/test_run_real_continuous_smoothing_validation.py` | FREEZE_DIAGNOSTIC |
| `tests/test_run_real_continuous_smoothing_validation_execute.py` | FREEZE_DIAGNOSTIC |
| `tests/test_run_real_continuous_smoothing_validation_execute_v2.py` | FREEZE_DIAGNOSTIC |
| `tasks/step_3r3_*.md` 系列（30+ 个） | FREEZE_DIAGNOSTIC |
| `tasks/step_3r3_3f_*` v2 实施 / 真实验证 / 失败复盘 checkpoint | FREEZE_DIAGNOSTIC |
| `tasks/step_3r3_e_*` v2 launch review checkpoint | FREEZE_DIAGNOSTIC |
| `tasks/step_3r3_3g_*` v2 failure postmortem comparison checkpoint | FREEZE_DIAGNOSTIC |
| `tasks/step_3r3_3h_*` abandon decision checkpoint | FREEZE_DIAGNOSTIC |
| `logs/historical_training/three_system_w4_smoke_2024_08_05_2024_08_09/`（untracked） | FREEZE_DIAGNOSTIC（数据制品） |
| `logs/historical_training/three_system_w4_2024_08_2025_12/`（untracked） | FREEZE_DIAGNOSTIC（数据制品） |
| `logs/historical_training/three_system_1005/`（untracked） | FREEZE_DIAGNOSTIC（数据制品） |

> 上述对象的"动作"是：**保持原样**。Step 11/12/13/14 都**不**触碰。

---

## 8. QUARANTINE_LATER 清单

> 未来隔离候选。本轮**不**动。Step 14 在 boundary fix + regression 通过后处理。

| 对象 | current_status | why quarantine | recommended future action |
|---|---|---|---|
| `confidence_engine.py`（根级 32 行 stub） | 已确认无 active import | step_1a v1 stub 死代码 | Step 14：先验证 docs / tests / scripts 任一无 import → 移到 `services/_legacy_v1_stubs/` 或加 `_DEPRECATED.md` 同目录说明 |
| `contradiction_engine.py`（根级 26 行 stub） | 已确认无 active import | 同上 | 同上 |
| `risk_model.py`（根级 26 行 stub） | 已确认无 active import | 同上 | 同上 |
| `services/projection_orchestrator.py`（旧 V1） | 仅 V2 自身 + tests import | 与 V2 functional overlap | Step 14：在 V2 完成 RISK-1+RISK-6 解耦后，验证 V1 是否仍是 V2 内部依赖；若不再需要，加 deprecation 标记 |
| `services/automation_wrapper.py` | UNKNOWN_REVIEW_REQUIRED | 命名宽泛，归属未明 | Step 11 spot-check；如确认非 active，归 quarantine |
| `services/soft_metadata_injection.py` | UNKNOWN_REVIEW_REQUIRED | "injection" 命名风险 | Step 11 spot-check；验证是否真的注入到推演路径 |
| `services/soft_metadata_simulator.py` | UNKNOWN_REVIEW_REQUIRED | 与 scripts/soft_metadata_simulator.py 重叠 | Step 11 spot-check |
| `services/review_agent.py` / `review_analyzer.py` / `review_center.py` / `review_classifier.py` / `review_comparator.py` / `review_orchestrator.py` / `review_store.py` | UNKNOWN_REVIEW_REQUIRED | 复盘 cluster；归属与回灌情况未明 | Step 11 spot-check |
| `agent_loop.py`（main worktree untracked） | UNKNOWN_REVIEW_REQUIRED | 未入库；按 hard rules 不处理 | Step 14：决定是入库还是删除（独立 PR） |
| `.claude/handoffs/task_089_post_pr_cleanup.md`（untracked） | UNKNOWN_REVIEW_REQUIRED | 旧 handoff 残留 | Step 14：归档或删除（独立 PR） |
| `.claude/legacy_tasks/` | QUARANTINE_LATER | CLAUDE.md 已注明的归档目录 | 保持隔离；Step 14 评估是否压缩 / 归并 |
| `.claude/worktrees/`（含本 worktree） | QUARANTINE_LATER | claude code 工具内部 | 按 hard rules 不处理；工作完成后由 worktree 生命周期自然清理 |
| `records/` 仓库根目录 | UNKNOWN_REVIEW_REQUIRED | 与 tasks/record_NN_*.md 体系是否重复 | Step 11 spot-check；若 tasks/ 已是单一 source of truth，归 quarantine |

> **隔离应独立 PR / commit**：本轮**不**做。Step 14 时每个对象独立判定 +
> 独立 commit，避免与 boundary fix 混合。

---

## 9. CLEANUP_LATER 清单

> 未来清理候选。本轮**不**处理。Step 14 在 backup / evidence policy 明确后做。

| 对象 | current_status | why cleanup | recommended future action |
|---|---|---|---|
| `logs/regime_validation/`（main worktree untracked） | CLEANUP_LATER | 大 raw output；未入库 | Step 14：archive 到 cold storage；保留路径索引 |
| `logs/historical_training/three_system_*`（main worktree untracked） | CLEANUP_LATER | 大 raw output；untracked | 同上 |
| `avgo_agent.db.backup_pre_2099_hygiene_20260503_160409` | CLEANUP_LATER | DB backup（hard rules 不处理） | Step 14：制定 backup retention policy 后归档 |
| `avgo_agent.db.backup_pre_3a3_20260504_013453` | CLEANUP_LATER | 同上 | 同上 |
| `avgo_agent.db.backup_pre_3a4_20260504_023331` | CLEANUP_LATER | 同上 | 同上 |
| `avgo_agent.db.backup_pre_4c3_rewrite_20260503_235604` | CLEANUP_LATER | 同上 | 同上 |
| `avgo_agent.db.backup_pre_replay_130_20260504_003707` | CLEANUP_LATER | 同上 | 同上 |
| `avgo_agent.db.backup_pre_replay_30_20260503_162636` | CLEANUP_LATER | 同上 | 同上 |
| `avgo_agent.db.backup_step_2c_2_6` | CLEANUP_LATER | 同上 | 同上 |
| `predict.py` 内 v1 final_confidence 计算（line 32-37, 185-193, 435-441, 561, 784, 962, 981） | CLEANUP_LATER | 与 V2 final_decision 重复，但归属为 RISK-8 修复 | Step 12 修 RISK-8 后这些行被 Step 14 自然清理（即修复时移除即可，不必单独 cleanup） |
| `records/` 仓库根目录 | UNKNOWN_REVIEW_REQUIRED → 待 §10 二次审查 | 与 tasks/record_NN_*.md 体系重叠 | Step 14：若确认 tasks/ 已是单一 source of truth，归并 / 删除 |
| 任何在 Step 11/12/13 验证后被识别为 dead code 的模块 | CLEANUP_LATER | 死代码 | Step 14 |

> **cleanup 必须在 backup / evidence policy 明确后进行**。本轮**不**预先决定
> 删除任何 untracked 数据 / DB backup。

---

## 10. UNKNOWN_REVIEW_REQUIRED 清单

> 仍需进一步确认归属的对象。Step 11 启动前的 spot-check / Step 11 设计阶段
> 顺手解决。

| 对象 | 待审查问题 | 安排 |
|---|---|---|
| `services/automation_wrapper.py` | 是否参与在线判断？ | Step 11 spot-check |
| `services/soft_metadata_injection.py` | 是否注入到推演路径？ | Step 11 spot-check |
| `services/soft_metadata_simulator.py`（services 与 scripts 同名） | 与 scripts 版关系？是否离线 only？ | Step 11 spot-check |
| `services/review_agent.py` / `review_analyzer.py` / `review_center.py` / `review_classifier.py` / `review_comparator.py` / `review_orchestrator.py` / `review_store.py` | 是否回灌在线？ | Step 11 spot-check |
| `services/anti_false_exclusion_audit.py` | 是否读 projection 字段？ | Step 11 spot-check |
| `services/primary_bias_diagnosis.py` | 推演 self-assessment 还是 confidence？ | Step 11 RISK-3 设计阶段顺手 |
| `services/projection_preflight.py` / `projection_orchestrator_preflight.py` | 是否读 exclusion / confidence？ | Step 11 RISK-1 设计阶段顺手 |
| `services/pre_prediction_briefing.py` | briefing 内容是否含 future outcome？ | Step 11 RISK-7 设计阶段顺手 |
| `services/consistency_layer.py` | 与 final_decision 配合，是否引入新判断？ | Step 11 RISK-2 设计阶段顺手 |
| `services/projection_orchestrator.py`（旧 V1） | V2 是否仍依赖？ | Step 11 RISK-1 设计阶段顺手 |
| `research.py` 仓库根 | 入口脚本，归属？ | Step 11 spot-check |
| `records/` 仓库根目录 | 与 tasks/ 体系重叠？ | Step 14 二次审查 |
| `agent_loop.py`（untracked） | 入库还是删除？ | Step 14 二次审查 |
| `.claude/handoffs/task_089_post_pr_cleanup.md`（untracked） | 归档还是删除？ | Step 14 二次审查 |
| `ui/soft_metadata_baseline_cache.py` / `ui/soft_metadata_renderer.py` | 与 protection_layer 关系；是否纯展示？ | Step 11 spot-check |

---

## 11. 不允许本轮做的动作

本轮**严格禁止**以下动作：

1. **不要**删除任何文件（包括 dead stub / 旧 V1 / untracked）
2. **不要**移动任何文件（包括隔离到 `_legacy/` 等子目录）
3. **不要**改 import（包括 unused import 清理）
4. **不要**改 active path（包括 RISK-1 / RISK-2 / RISK-6 / RISK-8 / RISK-9 修复）
5. **不要**跑 validation / replay / smoke / e2e
6. **不要**清 logs/regime_validation/
7. **不要**清 DB backup
8. **不要**处理 stash
9. **不要**处理 .claude/worktrees/
10. **不要**进入 3R-5 / 3R-6
11. **不要**新增 candidate（projection / exclusion / confidence 任一类）
12. **不要**复活 continuous_smoothing
13. **不要**启用 promotion_execution_bridge
14. **不要**改 DB schema
15. **不要**新增测试
16. **不要**为修 RISK 而提前改代码（保留给 Step 12）

> **关键**：本轮的产出是**计划**，不是**动作**。如果在写计划时发现某个判断
> 需要先修复才能成立，那是 Step 11 的工作，不是本轮。

---

## 12. Step 11 准备事项

Step 11 是 **boundary enforcement design** 阶段。Step 11 应产出**设计文档**，
**不**改代码。具体设计目标：

### 12.1 RISK-1 + RISK-6 联合解耦设计（projection ← exclusion）

- 目标：让 `services/main_projection_layer.py` **不**接受 `exclusion_result`
  入参；删除 `_apply_exclusion()`；保留完整 5 状态分布
- 涉及文件：`services/projection_orchestrator_v2.py` /
  `services/main_projection_layer.py` / `services/home_terminal_orchestrator.py`
- 兼容性：保证 `services/projection_entrypoint.py` 装配的 v2_raw 字段不破，
  确保 `services/projection_three_systems_renderer.py` / 用户可见 UI 仍可工作
- exclusion 信号未来在何处展示：在 final_report / three_systems 层并列展示，
  由 confidence 系统评价冲突
- 测试设计：禁止 import 检查 + 字段一致性检查
- **关键**：RISK-1 和 RISK-6 必须**同时**设计同步处理方案；不能只修一条路径

### 12.2 RISK-2 final_decision 改造为纯 aggregate 设计

- 目标：`build_final_decision()` 不再翻 direction / 不再重算 confidence
- 三个新规则的归属：
  - "peer downgrade → flip to 中性" → 移到 projection 自身（07A）或废弃
  - "peer reinforce/historical support → +/- score" → 移到 confidence（07C）
  - "preflight rule influence" → 移到 confidence（07C）
- final_direction 应严格等于 projection 的 most_likely_state
- 测试设计：assert `final_direction == projection.most_likely_state`

### 12.3 RISK-3 confidence 系统独立化设计

- 目标：建立 `services/confidence_evaluator.py`（候选名）作为 07C 实现承载点
- 输入：仅 `projection_result` + `exclusion_result` + 历史命中率 / 样本量
- 输出：07C §9 草案的 schema
- 废弃：predict.py / final_decision.py 内的局部 confidence 重算
- 保留：`projection_three_systems_renderer.confidence_evaluator` 作为该 engine 的 read-only 展示
- 测试设计：confidence_evaluator 不修改 projection / exclusion；输出严格符合 07C §9

### 12.4 RISK-7 cutoff guard 设计

- 目标：`build_memory_feedback()` + `_review_loader()` 入口加 date filter
- 验证：在线路径上的所有 review records / memory 必须满足 `created_date <= target_date`（或 `<` 视场景）
- 测试设计：构造未来 review record，验证不会进入在线路径

### 12.5 RISK-8 predict.py 拆分设计

- 目标：`run_predict()` 仅调 `run_projection_entrypoint()`；删除内部 final_confidence 重算
- v1 路径若仍需保留：显式标记为 V1 legacy + 隔离
- 兼容性：保证 `app.py` / UI tab 调用契约不破

### 12.6 RISK-9 ai_summary source attribution + opt-in gate 设计

- 目标：每条 LLM 生成的句子必须附 `source_field` / `source_system` traceability
- 加 feature flag：默认关闭 ai_summary
- 测试设计：开 feature flag 后输出必须含 source attribution metadata

### 12.7 RISK-10 promotion offline-only documentation lock 设计

- 目标：在 `services/promotion_execution_bridge.py` docstring 与 README 显式锁定 "offline-only"
- 测试设计：禁止任何 active services 模块 import promotion_execution_bridge

### 12.8 Step 11 的产出物

- `tasks/record_11a_projection_exclusion_decoupling_design.md`（RISK-1+6）
- `tasks/record_11b_final_decision_aggregator_purification_design.md`（RISK-2）
- `tasks/record_11c_confidence_evaluator_separation_design.md`（RISK-3）
- `tasks/record_11d_memory_feedback_cutoff_guard_design.md`（RISK-7）
- `tasks/record_11e_predict_py_split_design.md`（RISK-8）
- `tasks/record_11f_ai_summary_source_attribution_design.md`（RISK-9）
- `tasks/record_11g_promotion_offline_only_documentation_lock_design.md`（RISK-10）

> 每份设计文档**只是设计**，不改代码。Step 12 才允许实施。

---

## 13. Step 12 准备事项

Step 12 是 **minimal boundary enforcement implementation** 阶段。Step 12 才允许
最小改动代码。规则：

1. **commit-per-fix**：每个 RISK 的修复独立 commit，保留可回滚
2. **commit message** 规范：`fix(boundary): RISK-NN <one-line 说明>`
3. **不允许** large rewrite：每个 fix 控制在最小行数
4. **不允许** cleanup 与 boundary fix 混合：Step 12 仅做 boundary fix；cleanup 留 Step 14
5. **必须**附 contract enforcement test：每个 fix 至少 1 个新 test 锁定 contract
6. **不进入** 3R-5 / 3R-6
7. **不新增** candidate
8. **不复活** continuous_smoothing
9. **不启用** promotion_execution_bridge

每次 Step 12 commit 必须能通过：

- `python -m pytest tests/`
- `scripts/check.sh`（如可运行）
- 用户可见 UI 路径（手动 spot-check 即可）

Step 12 的 6 个 commit 序列：

1. `fix(boundary): RISK-1+6 decouple projection from exclusion`
2. `fix(boundary): RISK-2 final_decision aggregator purification`
3. `fix(boundary): RISK-3 confidence evaluator separation`
4. `fix(boundary): RISK-7 memory feedback cutoff guard`
5. `fix(boundary): RISK-8 predict.py projection/aggregator split`
6. `fix(boundary): RISK-9 ai_summary source attribution + opt-in gate`
7. `fix(boundary): RISK-10 promotion offline-only documentation lock`

> 顺序不是绝对的，但 RISK-1+6 应**最先**做（影响范围最大），RISK-9 / RISK-10
> 可放最后（影响最小）。

---

## 14. 推荐执行顺序

```
Step 10  (本轮)       Keep / Freeze / Quarantine / Cleanup Plan       ← 当前
   ↓
Step 11  (后续设计)    Boundary enforcement plan（7 份子设计文档）       ← 不改代码
   ↓
Step 12  (后续实施)    Minimal boundary implementation（commit-per-fix）  ← 改代码
   ↓
Step 13  (后续验证)    Post-fix contract regression（端到端验证）        ← 跑 test/replay
   ↓
Step 14  (后续清理)    Cleanup / quarantine execution plan              ← 删/移文件
   ↓
之后才考虑 3R-5 / 3R-6 / 启用 promotion / 新增 candidate
```

**绝不允许**：

- 跳过 Step 11 直接进 Step 12
- 跳过 Step 12 直接进 Step 14
- 把 cleanup 与 boundary fix 混在一个 commit
- 在 Step 12 完成前进 3R-5 / 3R-6
- 在 Step 13 验证通过前启用 promotion
- 在 Step 14 完成前复活 continuous_smoothing

---

## 15. 严守边界

本轮**只写计划**：

- 未改代码
- 未删文件
- 未移动文件
- 未新增测试
- 未写 DB
- 未改 DB schema
- 未跑 replay
- 未跑 validation
- 未处理 untracked / DB backup / stash / .claude/worktrees/
- 未进入 3R-5 / 3R-6
- 未新增任何 candidate
- 未复活 continuous_smoothing
- 未修 RISK-1 / RISK-2 / RISK-3 / RISK-6 / RISK-7 / RISK-8 / RISK-9 / RISK-10

本计划的修改路径：任何对 §3 总评、§6 FIX_REQUIRED 列表、§12 / §13 准备事项、
§14 推荐顺序的调整，都必须以**显式更新本文件**的方式提出。
