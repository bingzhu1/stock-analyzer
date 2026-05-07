# 09记录：Module Inventory Detail

> 本记录是依据 06–08 文档对当前项目模块所做的**详细只读归属清单**。
>
> 本轮**未改代码、未删文件、未移动文件、未写 DB、未跑 validation、
> 未处理 untracked / DB backup / stash / .claude/worktrees/、未进入 3R-5 / 3R-6、
> 未新增 candidate、未复活 continuous_smoothing、未修 RISK-1 / RISK-2**。

---

## 1. Inventory 目的

依据 06 三系统独立原则 + 07A/07B/07C/07D 四份 contract + 07E 一致性检查 +
08 architecture diagnosis 的 risk map，对**每一个主要模块**做归属与状态判定：

- 解决 08 中所有 `UNKNOWN_REVIEW_REQUIRED` 项
- 是否有新风险出现（特别是 RISK-4 / RISK-5 / RISK-6 / RISK-7 / RISK-8 落地）
- 重新评估 RISK-1 / RISK-2 / RISK-3 是否仍为最高优先级

本轮**不**修复任何风险。所有结论是 Step 10 cleanup plan 与 Step 11 boundary
enforcement plan 的输入。

---

## 2. 分类标准

### 2.1 状态字段

| 状态 | 含义 |
|---|---|
| `ACTIVE_PROJECTION` | 在线推演路径上的活跃模块 |
| `ACTIVE_EXCLUSION` | 在线否定路径上的活跃模块 |
| `ACTIVE_CONFIDENCE` | 在线置信度 / 可靠性 / 校准评价路径上的活跃模块 |
| `ACTIVE_AGGREGATOR` | 在线 aggregator / display 路径上的活跃模块 |
| `ACTIVE_DATA_INFRA` | 数据 / 存储 / 缓存 / 标签等基础设施 |
| `FROZEN_DIAGNOSTIC` | 必须保留为 baseline，但不再 active 使用 |
| `QUARANTINE_CLEANUP_LATER` | 未来可隔离 / 清理 |
| `UNKNOWN_REVIEW_REQUIRED` | 归属仍待详查 |

### 2.2 风险字段

| 风险 | 含义 |
|---|---|
| `CLEAN` | 无 contract 违规 |
| `LOW_RISK` | 仅有 wording / metadata 级别问题 |
| `MEDIUM_RISK` | 模块 boundary 不清晰，但未触发 contract 违规 |
| `HIGH_RISK` | 已确认 contract 违规（07A–07D 任一） |
| `UNKNOWN_RISK` | 需进一步审查才能判定 |

---

## 3. 总体 inventory 结论

> **PASS_WITH_RISKS**

可推进至 Step 10 cleanup plan 与 Step 11 boundary enforcement plan，
但 Step 11 boundary plan 必须把以下 **HIGH_RISK** 全部纳入修复范围：

1. **RISK-1（08 已立项）** projection 吃 exclusion 输出 → confirmed
2. **RISK-2（08 已立项）** final_decision 在 aggregator 引入新判断 → confirmed
3. **RISK-6 升级（08 待查 → 09 confirmed HIGH_RISK）** `services/home_terminal_orchestrator.py:145-152` 与 `projection_orchestrator_v2.py` 是**完全相同的违规模式**：先跑 exclusion，再把 exclusion_result 喂给 main_projection_layer。是 RISK-1 的**第二条 active 路径**，必须一起解耦
4. **RISK-9（09 新增 HIGH_RISK）** `services/ai_summary.py` 导入 `openai_client.generate_text` 在 final report 路径产出**LLM 自由文本**，违反 07D §10 "句句必有出处"

下沉到 MEDIUM 级的风险：

- **RISK-3（08 已立项）** confidence 缺独立模块 → confirmed
- **RISK-7 部分确认（MEDIUM）** memory_feedback / projection_memory_briefing → projection_rule_preflight → projection_orchestrator_v2 这条 active 链路**依赖 review records 的时间过滤**，目前未确认是否对 review record 做 `created_date <= target_date` 的 cutoff；如果未做，是 07A §3.2 / 07C §3.3 future-leak 风险
- **RISK-8（08 已立项）** predict.py 跨 projection + aggregator → confirmed

下沉到 CLEAN：

- **RISK-5（08 待查 → 09 CLEAN）** `services/protection_layer_diagnostics.py:18-23` 已 spec-lock：`hard_gate_connected` / `required_field_connected` / `protection_layer_connected_for_gate` 永远为 False；`hard_upgrade_blocked` / `display_only` 永远为 True。`ui/protection_layer_diagnostics_renderer.py:34-43` 显式禁止 "hard" / "forced" / "no_trade" / "自动拦截" 字眼。无 active 决策耦合。

新发现：

- **RISK-10（09 新增 LOW_RISK）** `services/active_rule_pool_promotion.py` + `services/promotion_adoption_gate.py` + `services/promotion_execution_bridge.py` 当前**仅由 offline 训练（avgo_1000day_training）调用**，bridge 默认 `execution_enabled = False`。**当前 CLEAN，但 bridge 结构存在被未来 active caller 启用的风险**，需 documentation lock。

08 中 RISK-4 落实情况：
- `predict_summary.py` / `projection_narrative_renderer.py`：CLEAN
- `ai_summary.py`：HIGH_RISK，提升为 RISK-9
- `projection_three_systems_renderer.py`：CLEAN（read-only reshape）

---

## 4. services/ inventory

### 4.1 推演 / 否定 / 置信度 / 聚合相关核心模块

| path | belongs_to | status | risk | reason | recommended_action |
|---|---|---|---|---|---|
| `services/projection_orchestrator_v2.py` | 推演 + 否定耦合 | ACTIVE_PROJECTION（含 contract 违规） | **HIGH_RISK** | RISK-1：line 109 `exclusion_result = run_exclusion_layer(...)`；line 110-115 把 exclusion_result 喂 main_projection_layer | Step 11 解耦 |
| `services/projection_orchestrator.py` | 推演（旧 V1） | ACTIVE_PROJECTION | UNKNOWN_RISK | 仅由 V2 自己 import + tests；是 V2 内部封装的旧实现 | Step 09→10 详查 V2 是否仍依赖；若不依赖，列入 cleanup |
| `services/projection_orchestrator_preflight.py` | 推演前置 | ACTIVE_PROJECTION | UNKNOWN_RISK | preflight glue | Step 11 验证不读 exclusion / confidence |
| `services/projection_preflight.py` | 推演前置 | ACTIVE_PROJECTION | UNKNOWN_RISK | preflight glue | 同上 |
| `services/projection_rule_preflight.py` (345 行) | 推演前置 | ACTIVE_PROJECTION（含 RISK-7 入口） | MEDIUM_RISK | line 260-264 调 `_memory_briefing_builder()`；line 277 `_review_loader()`：把 historical reviews 喂 preflight | Step 11 加 `created_date <= target_date` 过滤 guard |
| `services/projection_memory_briefing.py` (46 行) | 推演前置 | ACTIVE_PROJECTION | MEDIUM_RISK | RISK-7 中转：调 `build_memory_feedback()` | 同上 |
| `services/pre_prediction_briefing.py` (209 行) | 推演前置 | ACTIVE_PROJECTION | UNKNOWN_RISK | briefing glue | Step 11 详查 |
| `services/main_projection_layer.py` | 推演（已被否定输出污染） | ACTIVE_PROJECTION（含 contract 违规） | **HIGH_RISK** | RISK-1：`_apply_exclusion()` 把 大涨/大跌 score 置 0 | Step 11 切除 |
| `services/primary_20day_analysis.py` | 推演 | ACTIVE_PROJECTION | CLEAN | AVGO 自身 20 日分析 | — |
| `services/primary_bias_diagnosis.py` | 推演自评 | ACTIVE_PROJECTION（与 confidence 边界模糊） | LOW_RISK | 命名含 "diagnosis"，疑似 self-assessment 而非新判断 | Step 09 file-level 详查 |
| `services/peer_adjustment.py` | 推演 | ACTIVE_PROJECTION | CLEAN | 同行修正属 07A §3.1 白名单 | — |
| `services/historical_probability.py` | 推演 | ACTIVE_PROJECTION | CLEAN | 历史样本属 07A §3.1 白名单 | — |
| `services/projection_entrypoint.py` (152 行) | 聚合入口 | ACTIVE_AGGREGATOR | CLEAN | 装配 v2_raw + narrative + three_systems + compat shell；不计算 | — |
| `services/projection_chain_contract.py` | 字段 contract helper | ACTIVE_AGGREGATOR | CLEAN | 纯 helper（builds fresh feature dict） | — |
| `services/projection_output_contract.py` | 字段 validator | ACTIVE_AGGREGATOR | CLEAN | line 274-311 纯 validator | — |
| `services/projection_output_adapter.py` | 字段 adapter | ACTIVE_AGGREGATOR | CLEAN | docstring 自述 "Never mutates inputs"；返回新 dict | — |
| `services/projection_v2_adapter.py` | 字段 adapter | ACTIVE_AGGREGATOR | CLEAN | 仅构建 legacy compat shell；不 mutate | — |
| `services/projection_three_systems_renderer.py` (1019 行) | 聚合 / 三系统并列展示 | ACTIVE_AGGREGATOR | CLEAN | 06Q 落地；line 990 read-only copy；confidence_evaluator (line 814-909) 仅评分不 mutate | Step 11 验证 schema 与 07C §9 严格对齐 |
| `services/projection_narrative_renderer.py` | 聚合 / narrative | ACTIVE_AGGREGATOR | CLEAN | 纯 validator + enum mapping；无 LLM | — |
| `services/predict_summary.py` | 聚合 / 摘要 | ACTIVE_AGGREGATOR | CLEAN | line 69-99 pure mapper；无 LLM | — |
| `services/ai_summary.py` | 聚合 / LLM 自由文本 | ACTIVE_AGGREGATOR（含 contract 违规） | **HIGH_RISK** | RISK-9：line 8 `from services.openai_client import generate_text`；`build_projection_ai_summary` 调 LLM 产出可能脱离 v2_raw 出处的文本 | Step 11 加 source attribution rule 或 gate behind 显式 opt-in |
| `services/final_decision.py` (383 行) | 聚合 / final_direction + final_confidence | ACTIVE_AGGREGATOR（含 contract 违规） | **HIGH_RISK** | RISK-2：line 280-286 翻 direction；288-303 重算 confidence；313-317 apply preflight | Step 11 改造为纯 aggregate |
| `services/exclusion_layer.py` (334 行) | 否定 active 入口 | ACTIVE_EXCLUSION | CLEAN | line 38-53 `_normalize_features()` 仅市场特征 | — |
| `services/anti_false_exclusion_audit.py` | 否定审计 | ACTIVE_EXCLUSION（审计） | UNKNOWN_RISK | 名称 = audit；需查是否读 projection | Step 09→10 详查 |
| `services/anti_false_exclusion_dashboard.py` | 否定看板 | ACTIVE_AGGREGATOR（display） | UNKNOWN_RISK | 看板 | 同上 |
| `services/big_up_contradiction_card.py` | 展示卡 | ACTIVE_AGGREGATOR（display） | LOW_RISK | "contradiction card" 命名暗示 vs projection 比对，但 06Q 已把它放到展示侧 | Step 09→10 验证不写回 projection |
| `services/big_down_tail_warning.py` | 展示警示 | ACTIVE_AGGREGATOR（display） | LOW_RISK | 同上 | 同上 |
| `services/exclusion_reliability_review.py` | 否定可靠性评价 | ACTIVE_CONFIDENCE | LOW_RISK | 历史命中率评价（属 07C 范畴） | Step 11 验证只评不改 |
| `services/continuous_smoothing_candidate.py` | 已 abandon candidate | FROZEN_DIAGNOSTIC | CLEAN | 仅 scripts/tests 引用 | 保留 baseline，**不**删 |
| `services/continuous_smoothing_candidate_v2.py` | 已 abandon candidate | FROZEN_DIAGNOSTIC | CLEAN | 同上 | 同上 |
| `services/contract_calibration_inputs.py` | 置信度 calibration 数据准备 | ACTIVE_CONFIDENCE | CLEAN | docstring 自述 "diagnostic 而非 engine"；不 mutate | — |
| `services/active_rule_pool.py` / `_calibration.py` / `_drift.py` / `_export.py` / `_validation.py` | 规则池 calibration / drift / export / validation | ACTIVE_CONFIDENCE | CLEAN | offline calibration | — |
| `services/active_rule_pool_promotion.py` | 规则池 promotion 分类 | ACTIVE_CONFIDENCE | LOW_RISK | RISK-10：line 56-69 分类 candidate；当前仅 offline 调用 | Step 11 documentation-lock 为 offline-only |
| `services/promotion_adoption_gate.py` | 提升网关 | ACTIVE_CONFIDENCE | LOW_RISK | line 82-115 输出 candidate 状态；不强制 hard | 同上 |
| `services/promotion_execution_bridge.py` | 提升执行桥 | ACTIVE_CONFIDENCE | LOW_RISK | line 134-150 默认 `execution_enabled=False`；当前无 active caller | 同上 |
| `services/protection_layer_diagnostics.py` | 保护层诊断 | ACTIVE_CONFIDENCE（display 类） | CLEAN | RISK-5 解除：line 18-21 hard_gate_connected/required_field_connected/protection_layer_connected_for_gate **always False**；line 22-23 display_only=True；UI only caller | — |
| `services/projection_review_closed_loop.py` | 推演复盘 | ACTIVE_CONFIDENCE / 数据制品 | UNKNOWN_RISK | 复盘闭环 | Step 11 验证不回灌 |
| `services/consistency_layer.py` | 一致性层 | ACTIVE_AGGREGATOR | UNKNOWN_RISK | 与 final_decision 配合 | Step 09→10 详查 |
| `services/evidence_trace.py` | 证据追溯展示 | ACTIVE_AGGREGATOR | LOW_RISK | 展示用；需验不重新推理 | — |

### 4.2 数据 / 工具 / 平台基础设施模块

| path | belongs_to | status | risk | reason |
|---|---|---|---|---|
| `services/market_data_store.py` | 市场数据存储 | ACTIVE_DATA_INFRA | CLEAN | 数据层 |
| `services/data_query.py` | 数据查询 | ACTIVE_DATA_INFRA | CLEAN | — |
| `services/record_reader.py` | 记录读取 | ACTIVE_DATA_INFRA | CLEAN | — |
| `services/log_store.py` | 日志存储 | ACTIVE_DATA_INFRA | CLEAN | — |
| `services/prediction_store.py` | 预测存储 | ACTIVE_DATA_INFRA | CLEAN | — |
| `services/projection_record_store.py` | 推演 record 存储 | ACTIVE_DATA_INFRA | CLEAN | — |
| `services/outcome_capture.py` | 结果捕获 | ACTIVE_DATA_INFRA | CLEAN | — |
| `services/memory_store.py` | 记忆存储 | ACTIVE_DATA_INFRA | CLEAN | — |
| `services/memory_feedback.py` (61 行) | 记忆反馈构建 | ACTIVE_DATA_INFRA（含 RISK-7 链路） | MEDIUM_RISK | line 34 `build_memory_feedback()` 构建反馈；缺 cutoff guard | Step 11 加 date filter |
| `services/regime_features_builder.py` / `regime_labels_builder.py` / `regime_validation_helper.py` / `real_regime_label_provider.py` / `regime_diagnostics_dashboard.py` | regime 特征 / 标签 / 验证 / 看板 | ACTIVE_DATA_INFRA | CLEAN | 07A/07B §3.1 白名单 |
| `services/replay_record_wiring.py` / `replay_validation_record_adapter.py` / `three_system_replay_audit.py` | replay / audit | ACTIVE_DATA_INFRA | CLEAN | offline；agent 验证不回灌 |
| `services/historical_replay_training.py` | 历史回放训练 | ACTIVE_DATA_INFRA | CLEAN | line 1-18 "No-future-leak contract"；Step 1 projection target_date=as_of_date；Step 2 outcome 在 projection 之后获取 |
| `services/avgo_1000day_training.py` | 1000 天训练 | ACTIVE_DATA_INFRA | CLEAN | offline 训练 |
| `services/daily_training_pipeline.py` / `daily_training_summary.py` | 日训练 pipeline / summary | ACTIVE_DATA_INFRA | CLEAN | offline |
| `services/contract_replay_planner.py` / `contract_replay_writer.py` | contract replay | ACTIVE_DATA_INFRA | CLEAN | — |
| `services/contract_outcome_correlation.py` | 结果相关性 | ACTIVE_DATA_INFRA | CLEAN | offline |
| `services/contract_payload_diff.py` / `_inspector.py` / `_trend.py` / `_extras_dashboard.py` | contract payload 工具 | ACTIVE_DATA_INFRA | CLEAN | 字段层工具 |
| `services/state_label.py` / `error_taxonomy.py` / `comparison_engine.py` / `stats_engine.py` / `rule_lifecycle.py` / `rule_scoring.py` / `five_state_margin_policy.py` | 工具层 | ACTIVE_DATA_INFRA | CLEAN | 工具 |
| `services/dashboard_view_model.py` / `multi_symbol_view.py` / `inspect_analysis.py` | 看板 view-model / 多标的视图 / 检查分析 | ACTIVE_AGGREGATOR | LOW_RISK | 展示层；Step 11 验证不 mutate |
| `services/features_20d.py` | 20 日特征 | ACTIVE_DATA_INFRA | CLEAN | 数据特征 |
| `services/analysis_context.py` | 分析上下文 | ACTIVE_DATA_INFRA | CLEAN | 上下文工具 |
| `services/agent_parser.py` / `agent_schema.py` / `ai_intent_parser.py` / `ai_task_parser.py` / `command_parser.py` / `intent_planner.py` / `plan_normalizer.py` / `tool_router.py` / `query_executor.py` / `openai_client.py` / `date_range_parser.py` | LLM intent / planner / parser / openai 客户端 | ACTIVE_DATA_INFRA | LOW_RISK | LLM 接入；本身不在线产判断；Step 11 验证 ai_summary 之外是否还有 LLM 漏入 final-report 路径 |
| `services/automation_wrapper.py` | 自动化包装 | ACTIVE_DATA_INFRA | UNKNOWN_RISK | 命名宽泛；Step 09→10 详查 |
| `services/home_terminal_orchestrator.py` | "home terminal" orchestrator | ACTIVE_PROJECTION + ACTIVE_EXCLUSION 耦合 | **HIGH_RISK** | RISK-6 升级：line 22 import run_exclusion_layer；line 145-152 同 RISK-1 模式（exclusion → main_projection）；被 app.py 直接调用 | Step 11 与 RISK-1 一并解耦 |
| `services/review_agent.py` / `review_analyzer.py` / `review_center.py` / `review_classifier.py` / `review_comparator.py` / `review_orchestrator.py` / `review_store.py` | 复盘 cluster | ACTIVE_DATA_INFRA / ACTIVE_AGGREGATOR | UNKNOWN_RISK | 复盘体系；Step 09→10 详查是否回灌在线 |
| `services/soft_metadata_injection.py` / `soft_metadata_simulator.py` | 软 metadata 注入 / 模拟 | UNKNOWN_REVIEW_REQUIRED | UNKNOWN_RISK | 命名含 "injection"，需查是否注入到推演路径 | Step 09→10 详查 |

---

## 5. scripts/ inventory

| path | belongs_to | status | risk | reason | recommended_action |
|---|---|---|---|---|---|
| `scripts/run_continuous_smoothing_validation.py` / `_v2.py` / `run_real_continuous_smoothing_validation.py` / `_execute.py` / `_execute_v2.py` | continuous_smoothing 验证 | FROZEN_DIAGNOSTIC | CLEAN | 仅与 frozen candidate 配套 | 保留，**不**删 |
| `scripts/run_1005_three_system_replay.py` | 三系统 replay | ACTIVE_DATA_INFRA（offline） | CLEAN | offline replay 工具 | — |
| `scripts/run_contract_replay.py` / `plan_contract_replay.py` | contract replay 工具 | ACTIVE_DATA_INFRA | CLEAN | — | — |
| `scripts/run_e2e_loop.py` | e2e 循环 | ACTIVE_DATA_INFRA | CLEAN | — | — |
| `scripts/save_projection_records_smoke.py` | smoke 工具 | ACTIVE_DATA_INFRA | CLEAN | smoke | — |
| `scripts/dashboard_contract_extras.py` / `regime_diagnostics_dashboard.py` / `anti_false_exclusion_dashboard.py` | 看板入口（脚本版） | ACTIVE_AGGREGATOR | LOW_RISK | 展示用；Step 11 验证 | — |
| `scripts/correlate_contract_outcomes.py` / `summarize_recent_contract_payloads.py` / `summarize_confidence_calibration_inputs.py` | offline 报告生成 | ACTIVE_DATA_INFRA | CLEAN | — | — |
| `scripts/diff_latest_contract_payloads.py` / `inspect_latest_contract_payload.py` | offline diff / inspect | ACTIVE_DATA_INFRA | CLEAN | — | — |
| `scripts/audit_five_state_collapse_from_db.py` | 五状态坍缩审计 | ACTIVE_DATA_INFRA | CLEAN | offline | — |
| `scripts/decompose_unsupported_false_exclusions_3a.py` / `analyze_missed_false_exclusions_3b.py` / `build_unsupported_explanation_taxonomy_3c1.py` / `batch_run_exclusion_reliability_review_3c3.py` / `shadow_backtest_exclusion_reliability_review_3c5.py` / `validate_exclusion_actions_2e.py` / `validate_false_exclusions_2e_v2.py` | 否定可靠性 / 误否定审计离线工具（Step 3a/3b/3c1/3c3/3c5/2e 系列） | ACTIVE_DATA_INFRA（offline） | CLEAN | offline 工具 | — |
| `scripts/build_03_replay_report.py` | 03 replay 报告 | ACTIVE_DATA_INFRA | CLEAN | — | — |
| `scripts/check.sh` | 统一检查脚本（CLAUDE.md 引用） | ACTIVE_DATA_INFRA | CLEAN | 统一检查 | — |
| `scripts/soft_metadata_simulator.py` | 软 metadata 模拟（脚本版） | UNKNOWN_REVIEW_REQUIRED | UNKNOWN_RISK | 与 services/soft_metadata_simulator.py 重叠 | Step 09→10 详查 |

---

## 6. ui/ and app.py inventory

| path | belongs_to | status | risk | reason | recommended_action |
|---|---|---|---|---|---|
| `app.py` (107KB, 2457 行) | UI shell（Streamlit） | ACTIVE_AGGREGATOR (UI) | CLEAN | 仅 delegate；grep 显示无 projection / exclusion / confidence 主动逻辑；调 `home_terminal_orchestrator` | Step 11 验证 home_terminal 解耦后 app.py 不需要改动 |
| `ui/__init__.py` | UI 包初始化 | ACTIVE_AGGREGATOR | CLEAN | — | — |
| `ui/predict_tab.py` | 预测主 tab | ACTIVE_AGGREGATOR (UI) | LOW_RISK | 展示 + 引用 protection_layer 字段；Step 11 验证不 in-place mutate v2_raw | — |
| `ui/history_tab.py` / `home_tab.py` / `inspect_tab.py` / `research_tab.py` / `review_tab.py` / `scan_tab.py` / `control_tab.py` / `command_bar.py` | 各 tab | ACTIVE_AGGREGATOR (UI) | LOW_RISK | 展示用；不 mutate | Step 11 验证 |
| `ui/labels.py` | UI 标签 | ACTIVE_DATA_INFRA | CLEAN | — | — |
| `ui/projection_v2_renderer.py` | V2 推演渲染 | ACTIVE_AGGREGATOR | LOW_RISK | 展示 v2_raw；Step 11 验证不 mutate | — |
| `ui/anti_false_exclusion_display.py` | 反误否定展示 | ACTIVE_AGGREGATOR | LOW_RISK | 展示 | — |
| `ui/big_up_contradiction_card.py` | 大涨矛盾卡片 UI | ACTIVE_AGGREGATOR | LOW_RISK | 展示卡 | — |
| `ui/exclusion_reliability_review.py` | 否定可靠性 UI | ACTIVE_AGGREGATOR / ACTIVE_CONFIDENCE 展示 | LOW_RISK | 展示 | — |
| `ui/protection_layer_diagnostics_renderer.py` | 保护层诊断 UI | ACTIVE_AGGREGATOR | CLEAN | line 34-43 显式禁止 "hard" / "forced" / "no_trade" / "自动拦截" | — |
| `ui/soft_metadata_baseline_cache.py` / `ui/soft_metadata_renderer.py` | 软 metadata UI | UNKNOWN_REVIEW_REQUIRED | LOW_RISK | grep 显示与 protection_layer 相关；Step 09→10 详查 | — |

---

## 7. data infra inventory

### 7.1 仓库根级数据基础设施

| path | belongs_to | status | risk | reason |
|---|---|---|---|---|
| `data_fetcher.py` (5KB) | 数据获取（yfinance） | ACTIVE_DATA_INFRA | CLEAN | 数据层 |
| `feature_builder.py` (4.5KB) | 特征构建 | ACTIVE_DATA_INFRA | CLEAN | CLAUDE.md 硬规则保留 |
| `encoder.py` (5.6KB) | 编码器 | ACTIVE_DATA_INFRA | CLEAN | CLAUDE.md 硬规则保留 |
| `matcher.py` (8.3KB) | 匹配器 | ACTIVE_DATA_INFRA | CLEAN | CLAUDE.md 硬规则保留 |
| `scanner.py` (28KB) | 扫描器 | ACTIVE_DATA_INFRA | CLEAN | CLAUDE.md 硬规则保留 |
| `stats_reporter.py` (8KB) | 统计报告 | ACTIVE_DATA_INFRA | CLEAN | — |
| `predict.py` (45KB, 977 行) | v1 推演 + 聚合混合 | ACTIVE_PROJECTION（含违规） | **HIGH_RISK** | RISK-8：内部调 run_projection_v2 (line 1052-1055) + 自己重算 final_confidence/final_one_sentence (line 561/784/962/981/435-441) | Step 11 拆分 |
| `research.py` (8KB) | research 入口 | ACTIVE_DATA_INFRA / 入口 | UNKNOWN_RISK | Step 09→10 详查 | — |
| `run_1000day.py` / `run_pipeline.py` (各 ~1.6KB) | 入口脚本 | ACTIVE_DATA_INFRA | CLEAN | 入口 | — |
| `confidence_engine.py` / `contradiction_engine.py` / `risk_model.py` (根级 v1 stub) | step_1a 死代码 | QUARANTINE_CLEANUP_LATER | LOW_RISK | grep 验证无 active import | Step 10 列入清理候选 |

### 7.2 collectors/

- 当前为空目录（`ls collectors/` 无输出）；列入 future leakage audit 关注点。

### 7.3 logs/

| path | belongs_to | status | recommended_action |
|---|---|---|---|
| `logs/historical_training/` (含 03_fresh_replay / exclusion_action_validation_2e / _v2 子目录) | 历史训练制品 | ACTIVE_DATA_INFRA | 仅作为离线数据源；Step 11 加 cutoff guard |
| `logs/historical_training/three_system_*` (untracked，main worktree) | 三系统训练制品 | QUARANTINE_CLEANUP_LATER | **不**处理（按 hard rules） |
| `logs/regime_validation/` (untracked) | regime 验证大输出 | QUARANTINE_CLEANUP_LATER | **不**处理 |
| `logs/technical_features/` | 技术特征数据 | ACTIVE_DATA_INFRA | — |

---

## 8. confidence system inventory

> **confidence system appears under-separated and needs dedicated implementation plan.**

### 8.1 当前是否有独立 ACTIVE_CONFIDENCE 模块？

> **没有**单点承载 07C 核心问题（"推演 / 否定各自这次有多可信"）。

### 8.2 当前承载 confidence 的模块（散落）

| path | 角色 | 是否 mutate projection / exclusion |
|---|---|---|
| `predict.py` | v1 路径 final_confidence 计算（`_confidence_from_score` / `_raise_confidence` / `_lower_confidence`） | 不 mutate inputs，但**自己产 final_confidence**，跨 07A / 07D 边界 |
| `services/final_decision.py:288-317` | V2 路径 confidence 重算 | 不 mutate inputs，但产 `final_confidence` 使用新规则（违反 07D §5） |
| `services/projection_three_systems_renderer.py:893-909` build_confidence_evaluator | 06Q 三系统并列输出中的 confidence_evaluator 段 | 不 mutate（CLEAN） |
| `services/contract_calibration_inputs.py` | 置信度 calibration 数据准备 | 不 mutate；自述 "diagnostic 而非 engine" |
| `services/active_rule_pool*.py` (6 个) | 规则池 calibration / drift / promotion / validation | 不 mutate；offline calibration |
| `services/exclusion_reliability_review.py` | 否定可靠性 review | 不 mutate；属 07C 范畴 |
| `services/projection_review_closed_loop.py` | 推演复盘闭环 | 不 mutate（待 Step 11 验证） |
| `confidence_engine.py`（根级） | step_1a v1 stub | 死代码（grep 验证无 active import） |

### 8.3 风险

- RISK-3 仍是 MEDIUM_RISK：**没有**单点承载，导致每次需要"评价系统可信度"时
  都得从两三处分别取数。
- 需要 Step 11 boundary plan 决定：
  - 把散落的 confidence 计算**收敛**到一个独立模块（候选名
    `services/confidence_evaluator.py`）；或
  - 把现有 `projection_three_systems_renderer.confidence_evaluator` +
    `contract_calibration_inputs.py` + `exclusion_reliability_review.py` 提升
    为 confidence system 实现承载点。
- 在收敛之前，**不**新增任何置信度 candidate（守 07C §14）。

---

## 9. exclusion system inventory

### 9.1 active exclusion modules

| path | 状态 | risk | reason |
|---|---|---|---|
| `services/exclusion_layer.py` | ACTIVE_EXCLUSION | CLEAN | 仅市场特征输入；不读 projection；唯一合规 active exclusion 入口 |
| `services/anti_false_exclusion_audit.py` | ACTIVE_EXCLUSION（审计性质） | UNKNOWN_RISK | 审计；Step 09→10 详查是否读 projection |
| `services/anti_false_exclusion_dashboard.py` | ACTIVE_AGGREGATOR (display) | UNKNOWN_RISK | 看板 |
| `services/big_up_contradiction_card.py` | ACTIVE_AGGREGATOR (display) | LOW_RISK | 展示卡；命名含 "contradiction"，但功能定位为 UI 卡 |
| `services/big_down_tail_warning.py` | ACTIVE_AGGREGATOR (display) | LOW_RISK | 同上 |
| `services/exclusion_reliability_review.py` | ACTIVE_CONFIDENCE | LOW_RISK | 评价否定可靠性 → 归 07C 范畴 |

### 9.2 frozen exclusion candidates

| path | 状态 |
|---|---|
| `services/continuous_smoothing_candidate.py` | FROZEN_DIAGNOSTIC |
| `services/continuous_smoothing_candidate_v2.py` | FROZEN_DIAGNOSTIC |
| `scripts/run_continuous_smoothing_validation*.py` | FROZEN_DIAGNOSTIC |
| `tests/test_continuous_smoothing_candidate*.py` / `test_run_*continuous_smoothing*.py` | FROZEN_DIAGNOSTIC |

### 9.3 contradiction / false_exclusion / anti_false_exclusion 的最终归属

| 模块 | 归属 |
|---|---|
| `big_up_contradiction_card.py` / `ui/big_up_contradiction_card.py` | **ACTIVE_AGGREGATOR (display)**：展示卡，不是 active exclusion candidate |
| `big_down_tail_warning.py` | **ACTIVE_AGGREGATOR (display)**：展示警示 |
| `anti_false_exclusion_audit.py` | **ACTIVE_EXCLUSION（审计性质，非 candidate）** |
| `anti_false_exclusion_dashboard.py` / `ui/anti_false_exclusion_display.py` | **ACTIVE_AGGREGATOR (display)** |
| `exclusion_reliability_review.py` / `ui/exclusion_reliability_review.py` | **ACTIVE_CONFIDENCE** 评价否定 |

### 9.4 是否有读取 projection_result 风险？

- `services/exclusion_layer.py`：CLEAN（已验证）
- `services/anti_false_exclusion_audit.py`：UNKNOWN_RISK，Step 09→10 详查
- `services/anti_false_exclusion_dashboard.py`：UNKNOWN_RISK，Step 09→10 详查
- 其它：CLEAN

---

## 10. projection system inventory

### 10.1 active projection modules

| path | risk | 备注 |
|---|---|---|
| `services/projection_orchestrator_v2.py` | **HIGH_RISK** | RISK-1 |
| `services/main_projection_layer.py` | **HIGH_RISK** | RISK-1 |
| `services/home_terminal_orchestrator.py` | **HIGH_RISK** | RISK-6 升级（与 RISK-1 同模式） |
| `services/projection_orchestrator.py` | UNKNOWN_RISK | 旧 V1，仅 V2 自身 import；详查 |
| `services/primary_20day_analysis.py` | CLEAN | 自身分析 |
| `services/peer_adjustment.py` | CLEAN | peer 信号 |
| `services/historical_probability.py` | CLEAN | 历史样本 |
| `services/primary_bias_diagnosis.py` | LOW_RISK | self-assessment 嫌疑；详查 |
| `services/projection_preflight.py` / `services/projection_orchestrator_preflight.py` / `services/projection_rule_preflight.py` / `services/projection_memory_briefing.py` / `services/pre_prediction_briefing.py` | MEDIUM_RISK | RISK-7：memory_feedback cutoff guard |
| `predict.py` | **HIGH_RISK** | RISK-8：mixed projection + aggregator |

### 10.2 projection 被 exclusion_result 污染的路径

- `services/projection_orchestrator_v2.py:109-115` → `services/main_projection_layer.py:255-274`
- `services/home_terminal_orchestrator.py:145-152` → `services/main_projection_layer.py:255-274`

两条 active 路径**都**违反 07A §10。Step 11 解耦时必须**同时**处理。

### 10.3 peer / historical / primary 是否 clean？

| 模块 | 验证 |
|---|---|
| `peer_adjustment.py` | CLEAN（07A §3.1 白名单） |
| `historical_probability.py` | CLEAN（07A §3.1 白名单） |
| `primary_20day_analysis.py` | CLEAN（仅 AVGO 自身数据） |
| `primary_bias_diagnosis.py` | LOW_RISK，待详查 |

### 10.4 predict.py 是否需要拆分？

> **是**。Step 11 boundary plan 必须把 predict.py 的 projection 部分与
> aggregator 部分拆开。最小重写方式：
> - `run_predict()` 仅调 `run_projection_entrypoint()` 取 v2_raw + three_systems
> - 移除自己的 `_confidence_from_score` / `_raise_confidence` / `_summarize` 等
>   final_confidence 重算逻辑
> - v1 路径如果仍需保留，应明确标记为 V1 legacy 并隔离

---

## 11. aggregator / report inventory

### 11.1 final_decision.py

> **HIGH_RISK** — RISK-2 confirmed
- line 280-286：`偏多/偏空 + peer downgrade + adjusted_direction=中性` 时翻 direction
- line 288-303：peer reinforce / historical support / caution / missing 加减 confidence
- line 313-317：preflight 影响 confidence

Step 11 改造方向：
- 改造为**纯 aggregate**：选择 highest-confidence 的 system output 直接展示
- preflight 影响**移到** confidence system（07C 范畴）
- 新规则**移到** projection system 自己（07A 范畴）或彻底废弃

### 11.2 projection_three_systems_renderer.py

> **CLEAN**
- 1019 行；read-only reshape
- confidence_evaluator 仅评分不 re-project
- 三段（negative_system / record_02_projection_system / confidence_evaluator）schema 与 07A/07B/07C 草案大致对齐
- Step 11 验证 schema 严格对齐（命名 / 字段 / 取值集）

### 11.3 summary / narrative / LLM

| 模块 | 风险 | 备注 |
|---|---|---|
| `predict_summary.py` | CLEAN | 纯 mapper |
| `projection_narrative_renderer.py` | CLEAN | 纯 validator + enum mapping，无 LLM |
| `ai_summary.py` | **HIGH_RISK** | RISK-9：line 8 import openai_client.generate_text → LLM 自由文本，违反 07D §10 |
| `services/projection_three_systems_renderer.py` 内 narrative | CLEAN | display 层 |

### 11.4 final report 是否需要 source attribution rule？

> **是**。Step 12 contract enforcement 阶段需要落地：
> - 每个 final report 字段必须有 `source_field` / `source_system` 注明出处
> - LLM 生成的文本必须附 traceability metadata
> - aggregator 不允许产生**无来源**句子（07D §10）

---

## 12. frozen diagnostic inventory

| 对象 | 状态 |
|---|---|
| `services/continuous_smoothing_candidate.py` | FROZEN_DIAGNOSTIC |
| `services/continuous_smoothing_candidate_v2.py` | FROZEN_DIAGNOSTIC |
| `scripts/run_continuous_smoothing_validation.py` / `_v2.py` / `run_real_continuous_smoothing_validation*.py`（5+ 个） | FROZEN_DIAGNOSTIC |
| `tests/test_continuous_smoothing_candidate.py` / `_v2.py` / `test_run_*continuous_smoothing*.py`（5+ 个） | FROZEN_DIAGNOSTIC |
| 3R-3 系列 checkpoint（`tasks/step_3r3_*.md`，30+ 个） | FROZEN_DIAGNOSTIC |
| 3R-3.3F-D / 3R-3.3G / 3R-3.3G1 / 3R-3.3H 等 v2 failure review + abandon decision 文档 | FROZEN_DIAGNOSTIC |
| `logs/historical_training/three_system_w4_smoke_*` / `three_system_w4_2024_08_2025_12/` / `three_system_1005/`（untracked） | FROZEN_DIAGNOSTIC（数据制品） |

> **保留为 baseline，不删除，不 active 使用，不复活**。

---

## 13. quarantine cleanup candidates

> 仅列；本轮**不**处理。

| 对象 | current_status | why quarantine | recommended future action |
|---|---|---|---|
| `confidence_engine.py`（根级 32 行 stub） | UNKNOWN_REVIEW_REQUIRED → 已确认无 active import | step_1a 时代死代码 | Step 10 列入 cleanup plan |
| `contradiction_engine.py`（根级 26 行 stub） | 同上 | 同上 | 同上 |
| `risk_model.py`（根级 26 行 stub） | 同上 | 同上 | 同上 |
| `agent_loop.py`（main worktree untracked） | UNKNOWN_REVIEW_REQUIRED | 未入库 | 仅标记 |
| `avgo_agent.db.backup_*`（main worktree 6 个） | QUARANTINE_CLEANUP_LATER | DB backup | 按 hard rules 不处理 |
| `logs/regime_validation/`（untracked） | QUARANTINE_CLEANUP_LATER | 大 raw output | 按 hard rules 不处理 |
| `logs/historical_training/three_system_*`（untracked） | QUARANTINE_CLEANUP_LATER | 大 raw output | 同上 |
| `.claude/handoffs/task_089_post_pr_cleanup.md`（untracked） | QUARANTINE_CLEANUP_LATER | 旧 handoff 残留 | 仅标记 |
| `.claude/worktrees/`（含本 worktree） | QUARANTINE_CLEANUP_LATER | 工具内部 | 按 hard rules 不处理 |
| `.claude/legacy_tasks/` | QUARANTINE_CLEANUP_LATER | 已归档 | 仅标记 |
| `services/projection_orchestrator.py`（旧 V1） | UNKNOWN_REVIEW_REQUIRED → 仅 V2 自身 import | 是否仍需保留待 Step 10 决定 | Step 10 详查 |
| `services/automation_wrapper.py` | UNKNOWN_REVIEW_REQUIRED | 命名宽泛 | Step 10 详查 |
| `services/soft_metadata_injection.py` / `soft_metadata_simulator.py` | UNKNOWN_REVIEW_REQUIRED | "injection" 命名风险 | Step 10 详查 |
| `services/review_*.py`（7 个 review cluster） | UNKNOWN_REVIEW_REQUIRED | 复盘体系；Step 10 详查是否回灌 | Step 10 详查 |
| `predict.py` v1 final_confidence 计算 | UNKNOWN_REVIEW_REQUIRED → 已确认 HIGH_RISK | 与 V2 final_decision 重复 | Step 11 拆分 |
| `records/`（仓库根目录） | UNKNOWN_REVIEW_REQUIRED | 与 tasks/record_NN_*.md 体系是否重复 | Step 10 详查 |

---

## 14. Risk map

| risk_id | path | severity | contract violated | evidence | recommended_followup |
|---|---|---|---|---|---|
| **RISK-1** | `services/projection_orchestrator_v2.py:109-116` + `services/main_projection_layer.py:255-274` | **HIGH** | 07A §3.2、§10 | line 109 `exclusion_result = run_exclusion_layer(...)`；line 110-115 喂 main_projection；main_projection_layer line 268-272 强制把 大涨/大跌 score=0.0 | Step 11 解耦：移除 main_projection 的 exclusion 入参 |
| **RISK-2** | `services/final_decision.py:280-303` + `:313-317` | **HIGH** | 07D §5、§10；07A §8、07B §8、07C §8 | line 280-286 翻 direction；288-303 重算 confidence；313-317 apply preflight | Step 11 改造为纯 aggregate |
| **RISK-3** | confidence 散落在 `predict.py` / `final_decision.py` / `projection_three_systems_renderer.py` 三处 | MEDIUM | 07C 整体（缺独立实现承载点） | 同 §8 表格 | Step 11 收敛到 `services/confidence_evaluator.py` 候选 |
| **RISK-4** | `services/ai_summary.py` 已升级为 RISK-9；`predict_summary.py` / `projection_narrative_renderer.py` CLEAN | — | — | Agent 1 已澄清 | RISK-4 关闭 |
| **RISK-5** | `services/protection_layer_diagnostics.py:18-23` 已 spec-lock；UI only caller | CLEAN | — | hard_gate_connected/required_field_connected/protection_layer_connected_for_gate **always False** | RISK-5 关闭 |
| **RISK-6** | `services/home_terminal_orchestrator.py:22, 145-152` | **HIGH**（升级） | 07A §3.2、§10 | line 22 `from services.exclusion_layer import run_exclusion_layer`；line 145-152 同 RISK-1 模式；由 app.py 调用 | Step 11 与 RISK-1 一并解耦 |
| **RISK-7** | `services/memory_feedback.py` (61 行) + `projection_memory_briefing.py` + `projection_rule_preflight.py:260-264, 277` + `projection_orchestrator_v2.py:511-518` | MEDIUM | 07A §3.2 future-leak / 07C §3.3 离线 vs 在线 cutoff | active 链路 → memory_feedback 读 historical reviews；缺 `created_date <= target_date` cutoff guard | Step 11 加 date filter |
| **RISK-8** | `predict.py:32-37, 185-193, 435-441, 561, 784, 962, 981, 1052-1055` | **HIGH** | 07A §5（推演不得输出 final_confidence） + 07D §5（aggregator 不得引入新判断） | predict.py 内同时 call run_projection_v2 + 自己重算 final_confidence + 自己拼 final_one_sentence | Step 11 拆分 |
| **RISK-9（新）** | `services/ai_summary.py:8` `from services.openai_client import generate_text` | **HIGH** | 07D §10（"句句必有出处"） | LLM 自由文本，无来源约束 | Step 11 加 source attribution + opt-in gate |
| **RISK-10（新）** | `services/active_rule_pool_promotion.py` + `services/promotion_adoption_gate.py` + `services/promotion_execution_bridge.py` | LOW | 07A §10 / 07C §11 潜在 | 当前 offline-only；bridge `execution_enabled=False`；avgo_1000day_training 唯一 caller | Step 11 documentation-lock 为 offline-only |

---

## 15. Immediate blockers

> **NO_IMMEDIATE_BLOCKER**

理由：

- 本轮新发现的 RISK-6 升级（home_terminal_orchestrator）、RISK-9（ai_summary LLM）
  都是**已存在数月**的存量结构，不是本轮新引入的回归。
- RISK-7（memory_feedback future-leak）当前**未确认**真实泄漏发生，是
  "缺 cutoff guard 的潜在风险"，不阻塞 Step 10。
- 三系统并列展示（06Q）仍工作；07A–07D + 07E + 08 已 commit 入 main。
- Step 10 cleanup plan 与 Step 11 boundary plan 在不动代码的前提下可推进。

---

## 16. Recommended next steps

按顺序：

1. **Commit Step 09 inventory**（建议 commit message：`docs(contract): record 09 module inventory detail`）
2. **Step 10 — keep / freeze / quarantine / cleanup plan**
   - 把 §13 quarantine 表格中每项写明动作清单
   - 重点决定：v1 死 stub（confidence_engine / contradiction_engine / risk_model）的清理路径
   - 重点决定：旧 V1 `services/projection_orchestrator.py` 是否仍保留
   - 重点决定：`records/` 目录是否归并到 `tasks/`
   - **不**做删除 / 移动
3. **Step 11 — minimal boundary enforcement plan**
   - 针对 RISK-1 + RISK-6（同模式 active 路径 ×2）：设计 main_projection_layer 的最小切除方案
   - 针对 RISK-2：设计 final_decision 改造为纯 aggregate 的最小方案
   - 针对 RISK-3：设计独立 confidence_evaluator 模块的落地方案
   - 针对 RISK-7：设计 memory_feedback 的 date cutoff guard
   - 针对 RISK-8：设计 predict.py 的 projection / aggregator 拆分方案
   - 针对 RISK-9：设计 ai_summary 的 source attribution + opt-in gate
   - **不**改代码，仅产出方案
4. **Step 12 — contract enforcement implementation**
   - 按 Step 11 方案做最小 patch（commit-per-fix 保留可回滚）
   - 加 contract enforcement test：projection_orchestrator_v2 / home_terminal_orchestrator 禁止 import exclusion_layer 在判断路径上；final_decision 字段 final_direction 必须等于 projection 的 most_likely_state；ai_summary 输出必须有 source attribution
5. **只有 Step 12 全部通过后**，才考虑：
   - 新 candidate
   - 进入 3R-5 / 3R-6
   - 启用 promotion_execution_bridge

强调：

- **不要**直接删文件
- **不要**直接重构
- **不要**直接进入 3R-5 / 3R-6
- **不要**新增 candidate
- **不要**复活 continuous_smoothing
- **不要**启用任何 hard / forced / required 决策

---

## 17. 严守边界

本轮**只读 inventory**：

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

本 inventory 的修改路径：任何对 §3 总评、§14 risk map、§15 blocker 判定、
§16 next steps 顺序的调整，都必须以**显式更新本文件**的方式提出。
