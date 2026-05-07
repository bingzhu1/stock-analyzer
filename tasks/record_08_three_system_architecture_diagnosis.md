# 08记录：Three-System Architecture Diagnosis

> 本记录是依据 06 三系统独立原则 + 07A/07B/07C/07D 四份 contract + 07E 一致性
> 检查报告对当前系统进行的**只读架构诊断**。
>
> 本轮**未改代码、未删文件、未移动文件、未写 DB、未跑 validation、
> 未处理 untracked / DB backup / stash / .claude/worktrees/、未进入 3R-5 / 3R-6、
> 未新增 candidate、未复活 continuous_smoothing**。

---

## 1. 诊断目的

依据 06–07E 已固定的三系统 contract，对当前系统做一次**只读体检**：

- 判断主要模块属于推演 / 否定 / 置信度 / aggregator / data infra / frozen
  diagnostic / quarantine / unknown
- 找出违反三系统独立原则的**具体证据**（file:line 引用）
- 评估是否有**立即阻塞**问题
- 评估是否可进入 Step 09 module inventory

本轮**不**做删除、迁移、重构、修补；所有发现仅作为后续 Step 09 / Step 10 /
Step 11 / Step 12 的输入。

---

## 2. 诊断依据

| 文档 | 路径 | 角色 |
|---|---|---|
| 06 | `tasks/record_06_three_system_independence_principle.md` | 项目原则 |
| 07A | `tasks/record_07a_projection_system_contract.md` | 推演 contract |
| 07B | `tasks/record_07b_exclusion_system_contract.md` | 否定 contract |
| 07C | `tasks/record_07c_confidence_system_contract.md` | 置信度 contract |
| 07D | `tasks/record_07d_final_report_aggregator_contract.md` | 聚合 contract |
| 07E | `tasks/record_07e_three_system_contract_consistency_review.md` | 契约一致性 sign-off |

诊断范围：仓库根 / `services/` / `ui/` / `scripts/` / `tests/` / `tasks/` /
`logs/` 目录级别 / `app.py` / `predict.py` / `confidence_engine.py` /
`contradiction_engine.py` / `risk_model.py` 等。

---

## 3. 分类标准

| 状态 | 含义（一句话） |
|---|---|
| `ACTIVE_PROJECTION` | 当前在线推演路径上的活跃模块 |
| `ACTIVE_EXCLUSION` | 当前在线否定路径上的活跃模块 |
| `ACTIVE_CONFIDENCE` | 当前在线置信度 / 校准 / 可靠性评价路径上的活跃模块 |
| `ACTIVE_AGGREGATOR` | 当前在线 aggregator / display 路径上的活跃模块 |
| `ACTIVE_DATA_INFRA` | 数据获取 / 存储 / 缓存 / 标签等基础设施，不属于判断系统 |
| `FROZEN_DIAGNOSTIC` | 必须保留为历史 baseline，但不再 active 使用 |
| `QUARANTINE_CLEANUP_LATER` | 未来可隔离 / 清理但本轮不处理 |
| `UNKNOWN_REVIEW_REQUIRED` | 归属待 Step 09 module inventory 阶段确认 |

---

## 4. 总体架构诊断结论

> **PASS_WITH_RISKS**

- **可以**进入 Step 09 module inventory。
- 但发现 **2 个 MAJOR_RISK 级别的 contract 违规点**（详见 §13），需要在
  Step 11–12 阶段制定 minimal boundary enforcement plan 来逐步消除：
  1. **推演层吃了否定层的输出**（违反 07A §10：`exclusion_result → projection_system`）
  2. **聚合层引入了新判断**（违反 07D §5 / §10：final report 不得 mutate / 引入新判断）
- 三系统独立原则**部分**已经通过 06Q 的展示层 (`projection_three_systems_renderer.py`)
  实现了"输出层并列展示"，但**判断层**（v2 主链路）尚未真正分权。
- continuous_smoothing v1/v2 状态已**正确隔离**，仅被 scripts / tests 触达，
  active 链路未引用（详见 §11）。
- 根级 v1 stub（`confidence_engine.py` / `contradiction_engine.py` /
  `risk_model.py`）**完全无 active 引用**，是 step_1a 时代的遗留死代码（详见 §10）。

**不存在立即阻塞**问题：本轮发现的 contract 违规属于"已存在数月"的存量结构，
不是新引入的回归；Step 09–12 按部就班即可。

---

## 5. module inventory overview

> 本表是 Step 08 级粗粒度 inventory，**不**展开到每个 service 文件。
> Step 09 会做 file-by-file detailed inventory。

| path | current function | belongs_to | status | reason | recommended_action |
|---|---|---|---|---|---|
| `app.py` (107KB, 2457 行) | Streamlit UI shell；调用 `run_predict()` 与 tab renderer | UI shell | ACTIVE_AGGREGATOR (UI 层) | 无主动业务逻辑，仅 delegate（Explore Q7 CLEAN） | Step 09 列入 UI 层目录 |
| `ui/predict_tab.py` 等 17 个 tab/render 文件 | Streamlit tab 渲染，含 confidence_three_columns / contradiction_card / exclusion_reliability_review 等展示 | UI shell + display | ACTIVE_AGGREGATOR | 多数为只读展示 | Step 09 audit 是否 in-place mutate `projection_v2_raw` |
| `predict.py` (45KB, 977 行) | 旧版 v1 推演主入口 (`run_predict`)；含 `_confidence_from_score` / `final_confidence` / `primary_confidence_raw` 等本地置信度计算 | 推演 + 聚合混合 | UNKNOWN_REVIEW_REQUIRED | 既算推演又算 final_confidence，跨契约边界（待 Step 09 详查） | Step 09 file-by-file 切分 |
| `services/projection_entrypoint.py` (152 行) | V2 在线入口；调度 v2_raw + narrative + three_systems | ACTIVE_AGGREGATOR | ACTIVE_AGGREGATOR | 已为多输出装配点，但本身不计算判断 | Step 09 留作 aggregator 入口锚点 |
| `services/projection_orchestrator_v2.py` (600 行) | V2 推演 orchestrator；**调用 exclusion → 把 exclusion_result 喂给 main_projection** | 推演 + 否定耦合 | ACTIVE_PROJECTION (含 contract 违规) | **violates 07A §10**（详见 §13 RISK-1） | Step 11 boundary plan 必须解耦 |
| `services/main_projection_layer.py` (394 行) | 主推演层；含 `_apply_exclusion` 把 exclusion 触发的状态置 0 | 推演（已被否定层污染） | ACTIVE_PROJECTION (含 contract 违规) | **violates 07A §10**（详见 §13 RISK-1） | Step 11 切除 `_apply_exclusion` 路径 |
| `services/primary_20day_analysis.py` | 主推演的 20 日结构分析 | ACTIVE_PROJECTION | ACTIVE_PROJECTION | 命名 + 路径合规 | Step 09 验证仅读市场数据 |
| `services/primary_bias_diagnosis.py` | 主推演 bias 诊断 | ACTIVE_PROJECTION 或 ACTIVE_CONFIDENCE | UNKNOWN_REVIEW_REQUIRED | 名称含 "diagnosis"，归属待定 | Step 09 详查 |
| `services/peer_adjustment.py` (272 行) | NVDA / SOXX / QQQ 同行修正 | ACTIVE_PROJECTION | ACTIVE_PROJECTION | 同行 reinforce/weaken 是 07A §3.1 白名单输入 | Step 09 验证不读 exclusion / confidence |
| `services/historical_probability.py` (979 行) | 历史相似样本概率层 | ACTIVE_PROJECTION | ACTIVE_PROJECTION | 历史样本属于 07A §3.1 白名单 | Step 09 验证 |
| `services/exclusion_layer.py` (334 行) | 否定层 active 入口（rule-based, market-feature only） | ACTIVE_EXCLUSION | ACTIVE_EXCLUSION | **不读** projection 字段（Explore Q2 CLEAN） | Step 09 验证 |
| `services/anti_false_exclusion_audit.py` / `_dashboard.py` | 反误否定审计 / 看板 | ACTIVE_EXCLUSION（审计） | ACTIVE_EXCLUSION | 与否定 candidate 自我评估相关 | Step 09 验证是否读 projection |
| `services/big_up_contradiction_card.py` / `services/big_down_tail_warning.py` | 大涨矛盾卡片 / 大跌尾部告警（展示卡片） | ACTIVE_AGGREGATOR (UI 卡) | UNKNOWN_REVIEW_REQUIRED | 命名含 "contradiction"；可能是展示卡而非否定 candidate | Step 09 详查 |
| `services/exclusion_reliability_review.py` | 否定可靠性审查（历史命中率） | ACTIVE_CONFIDENCE | ACTIVE_CONFIDENCE | 是否定系统的"可信度评价"，归 07C 范畴 | Step 09 验证只评不改 |
| `services/continuous_smoothing_candidate.py` / `_v2.py` | continuous_smoothing v1/v2 candidate | FROZEN_DIAGNOSTIC | FROZEN_DIAGNOSTIC | 仅 scripts/tests 引用，active 链路未引用（详见 §11） | 保留为 baseline，**不**删 |
| `services/contract_calibration_inputs.py` | 置信度 calibration 输入诊断（文件首注释明示"诊断而非引擎"） | ACTIVE_CONFIDENCE | ACTIVE_CONFIDENCE | 不 mutate（Explore Q3 CLEAN） | Step 09 验证 |
| `services/active_rule_pool*.py` (6 个文件) | 规则池：calibration / drift / export / promotion / validation | ACTIVE_CONFIDENCE | ACTIVE_CONFIDENCE | 偏 calibration / reliability，归 07C | Step 09 详查是否被 promotion gate 喂回推演 |
| `services/promotion_adoption_gate.py` / `services/promotion_execution_bridge.py` | 规则提升网关 / 执行桥 | UNKNOWN_REVIEW_REQUIRED | UNKNOWN_REVIEW_REQUIRED | 命名含 "promotion"，需检查是否触发 hard / forced（07D §5 禁止） | Step 09 详查 |
| `services/protection_layer_diagnostics.py` / `ui/protection_layer_diagnostics_renderer.py` | "保护层"诊断 + UI | UNKNOWN_REVIEW_REQUIRED | UNKNOWN_REVIEW_REQUIRED | 07D §5 显式禁止 `_PROTECTION_LAYER_CONNECTED` 字段；需要确认实际行为 | Step 09 详查 |
| `services/final_decision.py` (383 行) | 聚合三层产出 final_direction / final_confidence | ACTIVE_AGGREGATOR (含 contract 违规) | ACTIVE_AGGREGATOR (含 contract 违规) | **violates 07D §5 / §10**（详见 §13 RISK-2） | Step 11 改造为纯 aggregate |
| `services/projection_three_systems_renderer.py` (1019 行) | 06Q 落地的三系统并列输出 renderer | ACTIVE_AGGREGATOR | ACTIVE_AGGREGATOR | 返回新 dict，未 mutate v2_raw（Explore Q3 CLEAN） | Step 09 验证 negative_system / record_02 / confidence_evaluator 不互改 |
| `services/projection_narrative_renderer.py` / `services/predict_summary.py` / `services/ai_summary.py` | 文本摘要 / narrative renderer | ACTIVE_AGGREGATOR | ACTIVE_AGGREGATOR | 是否引入新判断 + LLM-driven 自由文本，需要验证"句句必有出处"（07D §10） | Step 09 详查 |
| `services/projection_output_adapter.py` / `_contract.py` / `projection_v2_adapter.py` / `projection_chain_contract.py` | step_1a/1c 的 contract adapter | ACTIVE_AGGREGATOR (字段层) | ACTIVE_AGGREGATOR | 已存在 contract validator 的雏形 | Step 09 评估是否扩展为 07A–07D 的 contract validator |
| `services/projection_record_store.py` / `services/prediction_store.py` / `services/projection_review_closed_loop.py` / `services/outcome_capture.py` | 预测 / 复盘存储 + closed-loop | ACTIVE_DATA_INFRA | ACTIVE_DATA_INFRA | 是数据基础设施 | Step 09 验证不混入判断逻辑 |
| `services/market_data_store.py` / `services/data_query.py` / `services/record_reader.py` / `services/log_store.py` | 市场数据 / 查询 / 日志存取 | ACTIVE_DATA_INFRA | ACTIVE_DATA_INFRA | 数据层 | — |
| `services/regime_*.py` / `services/real_regime_label_provider.py` / `services/regime_features_builder.py` / `services/regime_labels_builder.py` / `services/regime_validation_helper.py` / `services/regime_diagnostics_dashboard.py` | 市场 regime 标签 / 特征 / 看板 | ACTIVE_DATA_INFRA | ACTIVE_DATA_INFRA | 07A §3.1 / 07B §3.1 白名单 | Step 09 验证 dashboard 不写回判断系统 |
| `services/replay_record_wiring.py` / `services/replay_validation_record_adapter.py` / `services/three_system_replay_audit.py` / `services/contract_replay_*.py` / `services/historical_replay_training.py` / `services/avgo_1000day_training.py` / `services/daily_training_*.py` | 历史回放 / 训练 / 复盘审计基础设施 | ACTIVE_DATA_INFRA | ACTIVE_DATA_INFRA | 用于 calibration / replay；本身不在线判断 | Step 09 验证是否回流 future outcome 到在线路径（07C §11） |
| `services/agent_*.py` / `services/ai_intent_parser.py` / `services/command_parser.py` / `services/intent_planner.py` / `services/plan_normalizer.py` / `services/tool_router.py` / `services/openai_client.py` / `services/query_executor.py` | LLM intent / command / planner / router | ACTIVE_DATA_INFRA (LLM 接入) | ACTIVE_DATA_INFRA | 用于自然语言交互，不直接产判断 | Step 09 验证不擅自创造 most_likely / most_unlikely |
| `services/memory_*.py` / `services/review_*.py` / `services/review_center.py` / `services/review_orchestrator.py` / `services/review_classifier.py` | 复盘 / 记忆 / 评估中心 | UNKNOWN_REVIEW_REQUIRED | UNKNOWN_REVIEW_REQUIRED | 命名含 review，归属待定 | Step 09 详查 |
| `services/projection_preflight.py` / `services/projection_orchestrator_preflight.py` / `services/projection_rule_preflight.py` | 推演前置规则 / preflight | UNKNOWN_REVIEW_REQUIRED | UNKNOWN_REVIEW_REQUIRED | preflight 在 final_decision 中影响 confidence；需查清楚归属 | Step 09 详查 |
| `services/projection_memory_briefing.py` / `services/pre_prediction_briefing.py` | 预测前 briefing | UNKNOWN_REVIEW_REQUIRED | UNKNOWN_REVIEW_REQUIRED | 是否回灌历史结果 → 在线路径，待查 | Step 09 详查 |
| `services/dashboard_view_model.py` / `services/multi_symbol_view.py` / `services/inspect_analysis.py` | 看板 view-model / 多标的视图 / 检查分析 | ACTIVE_AGGREGATOR (展示) | ACTIVE_AGGREGATOR | 展示层 | Step 09 验证不 mutate |
| `services/error_taxonomy.py` / `services/comparison_engine.py` / `services/state_label.py` / `services/stats_engine.py` / `services/rule_lifecycle.py` / `services/rule_scoring.py` / `services/five_state_margin_policy.py` | 工具层（错误分类 / 比较 / 状态标签 / 规则评分） | ACTIVE_DATA_INFRA | ACTIVE_DATA_INFRA | 工具，不直接判断 | — |
| `services/automation_wrapper.py` / `services/home_terminal_orchestrator.py` | 自动化 / 终端 orchestrator | UNKNOWN_REVIEW_REQUIRED | UNKNOWN_REVIEW_REQUIRED | home_terminal_orchestrator 也 import 了 exclusion_layer，需查 | Step 09 详查 |
| `confidence_engine.py` / `contradiction_engine.py` / `risk_model.py`（根级） | step_1a v1 stub（极小函数） | 死代码 | UNKNOWN_REVIEW_REQUIRED | **无 active import**（grep 验证）；详见 §10 | Step 12 列入清理候选 |
| `consistency_layer.py`（services 内） | 一致性层 | UNKNOWN_REVIEW_REQUIRED | UNKNOWN_REVIEW_REQUIRED | 与 final_decision 配合，需查 | Step 09 详查 |
| `evidence_trace.py`（services 内） | 证据追溯 | ACTIVE_AGGREGATOR (展示) | ACTIVE_AGGREGATOR | 展示层 | Step 09 验证不重新推理 |
| `feature_builder.py` / `encoder.py` / `matcher.py` / `scanner.py` / `data_fetcher.py` / `stats_reporter.py`（根级） | 数据特征 / 编码 / 匹配 / 扫描 / 数据获取 | ACTIVE_DATA_INFRA / 推演辅助 | ACTIVE_DATA_INFRA | CLAUDE.md 已注明 scanner / matcher / encoder 是硬规则层，优先保留 | — |
| `run_1000day.py` / `run_pipeline.py` / `research.py`（根级） | 1000 天回放 / pipeline / research 入口 | ACTIVE_DATA_INFRA (脚本入口) | ACTIVE_DATA_INFRA | 入口脚本 | Step 09 验证不污染在线路径 |
| `scripts/run_continuous_smoothing_validation*.py` (5+ 个) | continuous_smoothing 验证脚本 | FROZEN_DIAGNOSTIC | FROZEN_DIAGNOSTIC | 仅在 scripts，与 active 路径隔离 | 保留 |
| `scripts/run_1005_three_system_replay.py` / `run_e2e_loop.py` / `run_contract_replay.py` 等 | 三系统 replay / e2e / contract replay 脚本 | ACTIVE_DATA_INFRA | ACTIVE_DATA_INFRA | 离线工具 | Step 09 详查 |
| `tests/` (148 个文件) | 单元测试 / apptest | 测试基础设施 | ACTIVE_DATA_INFRA | 测试已包含 contract field 测试（如 `test_confidence_system_contract_fields.py` / `test_exclusion_system_contract_fields.py` / `test_final_projection_contract_fields.py` 等） | Step 12 评估是否新增 07A–07D contract enforcement test |
| `tasks/` (145 个文件) | 项目历史文档 / checkpoint | 文档基础设施 | ACTIVE_DATA_INFRA | 文档 | — |
| `logs/historical_training/` (3 个子目录：`03_fresh_replay` / `exclusion_action_validation_2e` / `exclusion_action_validation_2e_v2`) | 历史训练 / 验证大输出（仅目录，不读 raw） | 数据制品 | QUARANTINE_CLEANUP_LATER | 与 untracked 状态共存于 main worktree | 保留，**不**清理 |
| `logs/regime_validation/` (untracked, 仅目录) | regime 验证大输出 | 数据制品 | QUARANTINE_CLEANUP_LATER | untracked，按 hard rules 不处理 | 保留，**不**清理 |
| `logs/technical_features/` | 技术特征数据 | 数据制品 | ACTIVE_DATA_INFRA | — | — |
| `agent_loop.py`（main worktree untracked） | 未跟踪文件 | UNKNOWN_REVIEW_REQUIRED | UNKNOWN_REVIEW_REQUIRED | 未入库；按 hard rules 不处理 | 仅标记，**不**处理 |
| `avgo_agent.db.backup_*`（main worktree untracked，6+ 个） | DB backup 文件 | 数据制品 | QUARANTINE_CLEANUP_LATER | 按 hard rules 不处理 | 仅标记，**不**处理 |
| `.claude/worktrees/` | claude code 工作树 | 工具内部 | QUARANTINE_CLEANUP_LATER | 按 hard rules 不处理 | — |
| `.claude/handoffs/task_089_post_pr_cleanup.md`（untracked） | 旧 handoff 残留 | 文档基础设施 | QUARANTINE_CLEANUP_LATER | 仅标记 | — |
| `records/` 目录 | 项目 records | 文档基础设施 | UNKNOWN_REVIEW_REQUIRED | 与 tasks/record_NN_*.md 体系是否重复 | Step 09 详查 |

---

## 6. projection system candidates

### 6.1 候选清单

| path | 为什么属于 projection | active? | 读 exclusion / confidence？ | recommended_action |
|---|---|---|---|---|
| `predict.py` (45KB) | v1 推演主入口（`run_predict`）；含 `final_confidence` / `primary_confidence_raw` | yes | grep 显示 `confidence` 关键字密集（35 处含 `_normalize_confidence` / `_confidence_from_score`），但**不读 exclusion 字段**（无 `excluded_states` / `triggered_rule`）；含 `final_confidence` 计算（已是 aggregator 行为，不是纯 projection） | Step 09 切分：哪部分是 projection、哪部分是 aggregator |
| `services/projection_orchestrator_v2.py` | V2 推演 orchestrator | yes | **读 exclusion**：`projection_orchestrator_v2.py:109` `exclusion_result = run_exclusion_layer(feature_payload)` 后于 `:111-115` 把 `exclusion_result` 喂给 `build_main_projection_layer` | **MAJOR_RISK**（见 §13 RISK-1） |
| `services/projection_orchestrator.py` | 旧版 V1 推演 orchestrator | uncertain | 待 Step 09 详查 | Step 09 |
| `services/main_projection_layer.py` | 主推演层 | yes | **吃 exclusion**：`main_projection_layer.py:255-274` `_apply_exclusion()` 强制把 `大涨` / `大跌` 的得分置 0，注释明确写"排除层已给出'明天不太可能大涨'，主推演层禁止将大涨排为 Top1"（line 269） | **MAJOR_RISK**（见 §13 RISK-1） |
| `services/primary_20day_analysis.py` | AVGO 近 20 日主分析 | yes | 未发现读 exclusion / confidence（待 Step 09 详查） | 验证 |
| `services/primary_bias_diagnosis.py` | 主分析 bias 诊断 | uncertain | 名称含 "diagnosis"，可能是 confidence 而非 projection | Step 09 |
| `services/peer_adjustment.py` | 同行修正 | yes | peer 是 07A §3.1 白名单输入 | 验证 |
| `services/historical_probability.py` | 历史样本概率 | yes | 历史样本是 07A §3.1 白名单 | 验证 |
| `services/projection_entrypoint.py` | V2 入口装配 | yes | 装配三段输出（v2 + narrative + three_systems），不计算 | aggregator |
| `services/projection_chain_contract.py` / `projection_output_contract.py` / `projection_output_adapter.py` / `projection_v2_adapter.py` | step_1a contract / adapter | yes | 字段适配层，非判断 | aggregator |
| `services/projection_record_store.py` | 推演 record 存储 | yes | data infra | data infra |

### 6.2 重点结论

- **主链路推演已被否定输出污染**（V2 链路通过 `_apply_exclusion` 抹除大涨 /
  大跌得分）。这是 06 三系统独立原则下**最严重的违规**之一，因为它把
  否定的"最不可能"变成了**强制 zero-out**，等价于把否定决策写回了推演
  得分分布。
- `predict.py` 既计算"推演原始信号"又计算"final_confidence"，跨契约边界。
  Step 09 需要拆分：哪段属于 07A、哪段属于 07D。

---

## 7. exclusion system candidates

### 7.1 候选清单

| path | 为什么属于 exclusion | active? | 读 projection？ | recommended_action |
|---|---|---|---|---|
| `services/exclusion_layer.py` (334 行) | 否定层 active 入口（rule-based, market-feature only） | yes | **不读 projection**（`exclusion_layer.py:38-53` `_normalize_features()` 仅接收 `pos20`、`vol_ratio20`、`upper_shadow_ratio`、`lower_shadow_ratio`、`ret1/3/5`、peer ret 等市场特征；无任何 `most_likely_state` / `state_probabilities` / `predicted_top1`） | CLEAN（Explore Q2 验证） |
| `services/anti_false_exclusion_audit.py` | 反误否定审计 | yes | 名称提示是审计，需要 Step 09 详查是否读 projection | Step 09 |
| `services/anti_false_exclusion_dashboard.py` | 反误否定看板 | yes | 看板，类似上述 | Step 09 |
| `services/big_up_contradiction_card.py` | "大涨矛盾"卡片 | yes | 命名含 "contradiction"，归属待定（可能是展示卡而非 active exclusion candidate） | Step 09 |
| `services/big_down_tail_warning.py` | 大跌尾部告警 | yes | 同上 | Step 09 |
| `services/exclusion_reliability_review.py` | 否定可靠性评价（历史命中率） | yes | 应归 07C（评价层） | 重新分类为 ACTIVE_CONFIDENCE |
| `services/continuous_smoothing_candidate.py` | continuous_smoothing v1 | **frozen** | scripts / tests only（详见 §11） | **FROZEN_DIAGNOSTIC** |
| `services/continuous_smoothing_candidate_v2.py` | continuous_smoothing v2 | **frozen** | scripts / tests only（详见 §11） | **FROZEN_DIAGNOSTIC** |

### 7.2 重点结论

- **否定层本身合规**：`exclusion_layer.py` 只读市场特征，不读 projection。
  这是当前架构中**最干净的契约执行**部分。
- continuous_smoothing v1/v2 = **FROZEN_DIAGNOSTIC**，不属于 ACTIVE_EXCLUSION，
  与 07B §11 / 07D §12 一致。
- 上述 `anti_false_exclusion_*` / `big_up_contradiction_card` /
  `big_down_tail_warning` / `exclusion_reliability_review` 名称暗示与否定相关，
  实际归属可能不是 active exclusion candidate（更像 diagnostic / review），
  Step 09 需要逐个确认。

---

## 8. confidence system candidates

### 8.1 候选清单

| path | 为什么属于 confidence | active? | 与 projection / exclusion 混杂？ | 改写 projection / exclusion？ | recommended_action |
|---|---|---|---|---|---|
| `confidence_engine.py`（根级） | step_1a v1 stub（仅 32 行） | **dead code** | — | — | Step 12 清理候选 |
| `services/contract_calibration_inputs.py` | calibration inputs（**自描述为 diagnostic 而非 engine**） | yes | 与 calibration / replay 数据相关，不直接 mutate（Explore Q3 CLEAN） | no | 验证 |
| `services/active_rule_pool*.py` (6 个) | 规则池：calibration / drift / export / promotion / validation | yes | 与 calibration / reliability 相关 | promotion 路径需查 | Step 09 |
| `services/exclusion_reliability_review.py` | 否定可靠性 review（历史命中率） | yes | 评价否定 | 不应改写否定 | Step 09 |
| `services/projection_three_systems_renderer.py` 内 `confidence_evaluator` 段 | 06Q 三系统输出中的 confidence 段 | yes | 同时读 projection / exclusion 但**返回新 dict**（Explore Q3 CLEAN） | no | 验证字段 schema 是否符合 07C §9 |
| `services/projection_review_closed_loop.py` | 推演复盘闭环 | yes | 评价历史推演命中 | 不应改写在线推演 | Step 09 |
| `services/primary_bias_diagnosis.py` | 主分析 bias 诊断 | uncertain | 可能归 07C | Step 09 |
| `services/promotion_adoption_gate.py` / `services/promotion_execution_bridge.py` | 规则 promotion 网关 / 执行桥 | uncertain | 是否触发 hard / forced（07D §5 禁止） | 待查 | Step 09 |
| `predict.py` 中 `_confidence_from_score` / `_apply_preflight_influence` | v1 局部置信度计算 | yes | 在 projection 模块内 | **是**：`predict.py` 含 `final_confidence` 字段计算 | Step 09 切分 |
| `services/final_decision.py` 中 `_apply_preflight_influence` / `_confidence_score` | 聚合层置信度调整 | yes | 在 aggregator 内引入新置信度规则（line 288–317） | **是**：违反 07D（详见 §13 RISK-2） | **MAJOR_RISK**（见 §13 RISK-2） |

### 8.2 重点结论

> **confidence system appears under-separated and requires dedicated contract
> implementation later.**

- 当前架构里**没有一个独立的 ACTIVE_CONFIDENCE 模块**回答 07C 的核心问题
  （"推演 / 否定各自这次有多可信"）。可信度的计算被**散落**在以下几处：
  1. `predict.py` 的 `final_confidence` 局部计算
  2. `services/final_decision.py` 的 `_apply_preflight_influence` /
     `_confidence_score` 重算
  3. `services/projection_three_systems_renderer.py` 的 `confidence_evaluator`
     段（display 层，非独立 engine）
- `confidence_engine.py` 根级 stub 是 step_1a 占位，无 active 引用。
- `services/contract_calibration_inputs.py` 自描述为"diagnostic 而非 engine"。
- `services/exclusion_reliability_review.py` 是否定的可靠性 review，
  已有"评价"性质，但归属在 services 中尚未对齐 07C。

**结论**：07C 契约目前**没有对应的实现单点**。Step 09 / Step 11 需要决定：
是把散落的局部置信度逻辑收敛到一个新模块，还是把现有 calibration / reliability
review 提升为 confidence system 的实现。

---

## 9. final report / aggregator / UI candidates

### 9.1 候选清单

| path | 是否仅 aggregate / display | 可能 mutate 三系统？ | 可能生成新判断？ | recommended_action |
|---|---|---|---|---|
| `app.py` (107KB) | yes（Streamlit shell） | no（Explore Q7 CLEAN） | no | — |
| `ui/predict_tab.py` 等 (17 个 tab) | mostly yes | **待验**（Step 09 详查是否 in-place 改 v2_raw） | mostly no | Step 09 |
| `services/projection_three_systems_renderer.py` (1019 行) | yes（返回新 dict） | no（Explore Q3 CLEAN） | 待 Step 09 验证 confidence_evaluator 不出新结论 | 验证 |
| `services/projection_narrative_renderer.py` | yes（narrative 输出） | no | **待 Step 09 详查"句句必有出处"**（07D §10） | Step 09 |
| `services/predict_summary.py` / `services/ai_summary.py` | mostly display | no | **待 Step 09 详查 LLM 输出是否引入新 most_likely / most_unlikely / 可信度** | Step 09 |
| `services/final_decision.py` (383 行) | **No** —— 在聚合时计算新方向 / 新置信度 | not in-place mutate，但 returns **new judgment** in fields like `final_direction` / `final_confidence` | **YES**：`final_decision.py:280-286` 在 `偏多/偏空 + peer downgrade + adjusted_direction=中性` 时**翻转** `final_direction = "中性"`；`:288-303` 用新规则**重算** confidence；`:313-317` 应用 preflight 影响降置信度 | **MAJOR_RISK**（见 §13 RISK-2） |
| `services/projection_entrypoint.py` | yes（装配 v2_raw + narrative + three_systems + compat shell） | no | no | — |
| `services/evidence_trace.py` / `ui/exclusion_reliability_review.py` / `ui/big_up_contradiction_card.py` / `ui/anti_false_exclusion_display.py` / `ui/protection_layer_diagnostics_renderer.py` | display | 待验 | 待验 | Step 09 |
| `predict.py` 中 `_summarize` / `final_confidence` / `final_one_sentence` | aggregator-style | no in-place | **YES**：v1 路径在 projection 模块内做 final-decision 工作 | Step 09 切分 |

### 9.2 重点结论

- **final_decision.py 是当前架构中第二个 MAJOR_RISK 点**：它表面上是"聚合"，
  实际上引入了**新决策规则**（direction 翻转、confidence 加减分、preflight
  降级），与 07D §5 / §10 直接冲突。
- `projection_three_systems_renderer.py` (1019 行) 是 06Q 阶段做的**展示层
  分系统**实现，符合 07D 的 aggregate-only 思想，但 confidence_evaluator 段
  与 07C 字段 schema 是否对齐需 Step 09 验证。
- `predict.py` 中存在 v1 路径的"projection + aggregator 二合一"，与 V2 路径的
  `final_decision.py` 形成两套并存的 final-direction 计算。

---

## 10. data infra / collector / storage

### 10.1 清单

- **collectors/**：当前为空目录（`ls collectors/` 无输出）
- **数据获取**：根级 `data_fetcher.py` (yfinance loader)
- **特征构建**：根级 `feature_builder.py` / `encoder.py` / `matcher.py` /
  `scanner.py`（CLAUDE.md hard rules 中明确要求保留）
- **数据存储 / 查询**：`services/market_data_store.py` / `services/data_query.py` /
  `services/log_store.py` / `services/record_reader.py`
- **预测 / 复盘存储**：`services/prediction_store.py` /
  `services/projection_record_store.py` / `services/outcome_capture.py` /
  `services/projection_review_closed_loop.py`
- **Replay / 训练**：`services/replay_record_wiring.py` /
  `services/replay_validation_record_adapter.py` /
  `services/three_system_replay_audit.py` / `services/contract_replay_*.py` /
  `services/historical_replay_training.py` / `services/avgo_1000day_training.py` /
  `services/daily_training_*.py`
- **Regime infra**：`services/real_regime_label_provider.py` /
  `services/regime_features_builder.py` / `services/regime_labels_builder.py` /
  `services/regime_validation_helper.py`
- **LLM 接入**：`services/openai_client.py` / `services/agent_*.py` /
  `services/ai_intent_parser.py` / `services/command_parser.py` /
  `services/intent_planner.py` / `services/plan_normalizer.py` /
  `services/tool_router.py`
- **Logs**：`logs/historical_training/{03_fresh_replay, exclusion_action_validation_2e, exclusion_action_validation_2e_v2}` /
  `logs/regime_validation/`（untracked，按 hard rules 不读）/
  `logs/technical_features/`

### 10.2 说明

- 这些是基础设施，**不属于推演 / 否定 / 置信度判断本身**，但 Step 09 需要
  审查"是否被错误当作 active judgment module"。重点关注：
  - `services/promotion_*.py` 是否会把 calibration 结果**自动回灌**到在线推演
    （如发生，会构成 07A §10 / 07C §11 的违规）
  - LLM intent / planner 是否会**自由生成** most_likely / most_unlikely 而绕开
    三系统（07D §10 "句句必有出处"）

---

## 11. frozen diagnostic artifacts

> 必须保留为 baseline，但**不**继续 active 使用、**不**复活为 active candidate。

| 对象 | 状态 |
|---|---|
| `services/continuous_smoothing_candidate.py` | FROZEN_DIAGNOSTIC |
| `services/continuous_smoothing_candidate_v2.py` | FROZEN_DIAGNOSTIC |
| `scripts/run_continuous_smoothing_validation.py` / `_v2.py` / `_real_*.py` | FROZEN_DIAGNOSTIC（验证脚本） |
| `tests/test_continuous_smoothing_candidate*.py` / `tests/test_run_continuous_smoothing_validation*.py` / `tests/test_run_real_continuous_smoothing_validation*.py` | FROZEN_DIAGNOSTIC（baseline 测试） |
| 3R-3 阶段 checkpoint 文档（`tasks/step_3r3_*.md`，约 30+ 个） | FROZEN_DIAGNOSTIC |
| v2 failure review 文档 / abandon decision checkpoint（3R-3.3F-D / 3R-3.3G / 3R-3.3G1 / 3R-3.3H） | FROZEN_DIAGNOSTIC |
| `logs/historical_training/*` (含 v1/v2 raw 输出) | FROZEN_DIAGNOSTIC（数据制品） |

**反向验证**（grep）：仅 `scripts/run_real_continuous_smoothing_validation_execute_v2.py`
和测试文件 import `continuous_smoothing_candidate*`；**active services 模块均未引用**。
对应 06 §8 / 07B §11 / 07C §12 / 07D §12 的隔离要求 ✅。

---

## 12. quarantine / future cleanup candidates

> 仅列，**不**删；本轮**不**处理。

| 对象 | 状态 | 说明 |
|---|---|---|
| `confidence_engine.py`（根级 32 行 stub） | UNKNOWN_REVIEW_REQUIRED | 无 active import；§8 已确认为死代码；Step 12 清理候选 |
| `contradiction_engine.py`（根级 26 行 stub） | UNKNOWN_REVIEW_REQUIRED | 同上 |
| `risk_model.py`（根级 26 行 stub） | UNKNOWN_REVIEW_REQUIRED | 同上 |
| `agent_loop.py`（main worktree untracked） | UNKNOWN_REVIEW_REQUIRED | 未入库；按 hard rules 不处理 |
| `avgo_agent.db.backup_*`（main worktree 6 个 untracked DB backup） | QUARANTINE_CLEANUP_LATER | 按 hard rules 不处理 |
| `logs/regime_validation/`（main worktree untracked） | QUARANTINE_CLEANUP_LATER | 按 hard rules 不处理 |
| `logs/historical_training/three_system_1005/` / `three_system_w4_2024_08_2025_12/` / `three_system_w4_smoke_2024_08_05_2024_08_09/`（main worktree untracked） | QUARANTINE_CLEANUP_LATER | 按 hard rules 不处理 |
| `.claude/handoffs/task_089_post_pr_cleanup.md`（untracked） | QUARANTINE_CLEANUP_LATER | 旧 handoff 残留 |
| `.claude/worktrees/`（含本 worktree） | QUARANTINE_CLEANUP_LATER | 按 hard rules 不处理 |
| `.claude/legacy_tasks/` | QUARANTINE_CLEANUP_LATER | CLAUDE.md 已注明的归档目录 |
| `services/projection_orchestrator.py`（旧 V1 orchestrator） | UNKNOWN_REVIEW_REQUIRED | 是否仍被 v1 路径引用？Step 09 |
| `predict.py` 中 v1 final_confidence 计算 | UNKNOWN_REVIEW_REQUIRED | 与 V2 final_decision 重复 |

---

## 13. architecture risks found

### RISK-1: 推演层吃了否定层的输出（违反 07A §10）

| 项 | 内容 |
|---|---|
| risk | active 推演路径把 `exclusion_result` 作为输入并**强制把 `大涨` / `大跌` 得分置 0** |
| evidence | `services/projection_orchestrator_v2.py:109-116` 把 `exclusion_result = run_exclusion_layer(feature_payload)` 喂给 `build_main_projection_layer(...)`；`services/main_projection_layer.py:255-274` `_apply_exclusion()` 在 `triggered_rule == "exclude_big_up"` 时设 `adjusted["大涨"] = 0.0`、`triggered_rule == "exclude_big_down"` 时设 `adjusted["大跌"] = 0.0`，并附 reason 字符串 "排除层已给出'明天不太可能大涨'，主推演层禁止将大涨排为 Top1"（line 269） |
| violated contract | 07A §3.2（"否定系统输出（任何 `exclusion_*` 字段）"为禁止读取） + 07A §10（`exclusion_result → projection_system` 禁流） + 06 §7 第 1 条（"推演结果作为否定系统输入"的镜像，更准确说是 06 §7 第 8 条"跨系统反馈回路"） |
| severity | **HIGH** |
| recommended_followup | Step 11 boundary plan：把 `_apply_exclusion` 的 zero-out 逻辑从主推演层切走；推演输出**保留**完整 5 状态分布；否定信号在 final_report 层并列展示，由置信度系统评价冲突；Step 12 加 contract enforcement test：`projection_orchestrator_v2.py` 不允许 import `services.exclusion_layer` |

### RISK-2: 聚合层引入了新判断（违反 07D §5 / §10）

| 项 | 内容 |
|---|---|
| risk | `services/final_decision.py` 在"聚合"过程中**生成新方向**与**重算可信度** |
| evidence | `services/final_decision.py:280-286`：当 `primary_direction in {偏多, 偏空} + peer_adjustment_label == "downgrade" + peer.adjusted_direction == "中性"` 时，`final_direction = "中性"` —— 这是 final report 自己**翻转**了推演方向，引入了三系统外的新判断；`:288-303`：用新规则增减 confidence score（`peer reinforce + historical support → +1`，`peer downgrade → -1`，`historical caution → -1`）；`:313-317` `_apply_preflight_influence()` 再次降级 confidence + 升级 risk |
| violated contract | 07D §5（禁止 `modified_*` / `overridden_*` / 任何修改三系统字段） + 07D §10（"summary 中任一句话必须能在三系统输出找到对应来源"） + 07A §8 / 07B §8 / 07C §8（final report 不得回写或派生改写三系统输出） |
| severity | **HIGH** |
| recommended_followup | Step 11 boundary plan：把 `final_decision.py` 的新规则要么**移到推演 contract（07A）**（如果属于 projection 自我调整），要么**移到置信度 contract（07C）**（如果属于评价 / 加减分），要么**禁用**；final_decision 仅做"读三系统输出 + 排版 + 标注"。Step 12 加 contract enforcement test：final report 字段中 `final_direction` 的取值必须等于 `projection_result.most_likely_state`（或 explicit "no direction" 状态），不允许在 aggregator 层翻转 |

### RISK-3: confidence system 缺失独立实现（违反 07C 范畴）

| 项 | 内容 |
|---|---|
| risk | 当前**没有**一个独立的 ACTIVE_CONFIDENCE 模块回答 07C 核心问题；可信度计算散落在 `predict.py` / `services/final_decision.py` / `services/projection_three_systems_renderer.py` 三处 |
| evidence | `confidence_engine.py` 根级 stub 无 active import；`predict.py:561` `final_confidence = _confidence_from_score(score)`；`services/final_decision.py:288-317` 重算 confidence；`services/projection_three_systems_renderer.py` 的 `confidence_evaluator` 段是 display 层 |
| violated contract | 07C 整体（缺少 active 实现承载点） |
| severity | **MEDIUM** |
| recommended_followup | Step 11 boundary plan：把可信度计算收敛到一个独立模块（候选名 `services/confidence_evaluator.py`），输入仅为 projection_result + exclusion_result + 历史命中率 / 样本量；废弃 `predict.py` / `final_decision.py` 内的局部 confidence 重算 |

### RISK-4: ai_summary / predict_summary / projection_narrative_renderer 可能引入新判断（违反 07D §10）

| 项 | 内容 |
|---|---|
| risk | LLM-driven 自由文本拼接可能违反"句句必有出处"；narrative 段可能从原始 v2_raw 重新组合出新方向描述 |
| evidence | 仅由文件名 + 一般性架构推断；具体实现未读 |
| violated contract | 07D §10 |
| severity | **UNKNOWN**（需 Step 09 详查后才能定级） |
| recommended_followup | Step 09 file-by-file 审查；Step 12 增加"summary 句子可追溯到三系统字段"的 contract test |

### RISK-5: protection_layer / promotion_gate 可能与 hard / forced / required 决策耦合（违反 07D §5）

| 项 | 内容 |
|---|---|
| risk | 07D §5 显式禁止 `_PROTECTION_LAYER_CONNECTED` / `production_promotion`；现有 `services/protection_layer_diagnostics.py` / `ui/protection_layer_diagnostics_renderer.py` / `services/promotion_adoption_gate.py` / `services/promotion_execution_bridge.py` 命名提示存在该类机制 |
| evidence | 仅由文件名推断；具体实现未读 |
| violated contract | 07D §5（禁止 `_PROTECTION_LAYER_CONNECTED` / `production_promotion`） |
| severity | **UNKNOWN** |
| recommended_followup | Step 09 详查；如确认存在 hard / forced / required 触发，Step 11 列入 boundary plan |

### RISK-6: home_terminal_orchestrator 也 import exclusion_layer（违反 07A §10 的二级路径）

| 项 | 内容 |
|---|---|
| risk | grep 显示 `services/home_terminal_orchestrator.py` 也 import 了 `run_exclusion_layer`；可能存在第二条 active 推演路径同样违反 RISK-1 |
| evidence | `grep "from services.exclusion_layer\|run_exclusion_layer" services/*.py` 显示 4 个 active services 文件含此 import：`projection_orchestrator_v2.py`、`exclusion_layer.py`（自身）、`main_projection_layer.py`、`home_terminal_orchestrator.py` |
| violated contract | 同 RISK-1 |
| severity | **MEDIUM**（潜在二级路径，需 Step 09 详查） |
| recommended_followup | Step 09 详查 home_terminal_orchestrator 的调用语义 |

### RISK-7: Replay / training 可能回灌 future outcome 到在线路径（违反 07A §10 / 07B §10 / 07C §11）

| 项 | 内容 |
|---|---|
| risk | `services/replay_*.py` / `services/historical_replay_training.py` / `services/avgo_1000day_training.py` / `services/daily_training_*.py` / `services/promotion_adoption_gate.py` 等可能存在 future outcome → 在线 calibration → 在线推演 / 否定 的回灌路径 |
| evidence | 仅由模块名推断；具体实现未读。07C §3.3 已明确允许"离线 calibration 阶段使用 future-as-label，但结果仅以权重 / 校准表入参在线"，需要确认实际是否如此 |
| violated contract | 07A §10、07B §10、07C §11 |
| severity | **UNKNOWN** |
| recommended_followup | Step 09 详查 replay → calibration → promotion 数据流，区分离线 vs 在线 cutoff |

### RISK-8: predict.py 同时承担 projection + aggregator 角色

| 项 | 内容 |
|---|---|
| risk | `predict.py` 中既有推演计算又有 final_confidence / final_one_sentence 等聚合产出；与 V2 路径的 `services/final_decision.py` 重复并行 |
| evidence | `predict.py:32-37` `_VALID_CONFIDENCE_RAW` / `final_confidence`；`predict.py:185-193` `_raise_confidence` / `_lower_confidence`；`predict.py:435-441` `_summarize`；`predict.py:561` `final_confidence = _confidence_from_score(score)` |
| violated contract | 07A §5（推演不得输出 `final_confidence`） + 07D §5（aggregator 不得引入新判断） |
| severity | **MEDIUM** |
| recommended_followup | Step 09 拆分 predict.py 的 projection / aggregator 部分；Step 11 决定 v1 路径与 V2 路径的去留 |

---

## 14. immediate blockers

> **NO_IMMEDIATE_BLOCKER**

理由：

- §13 列出的 RISK-1 / RISK-2 都是**已经存在数月**的存量结构（08 之前已经如此），
  不是本轮新引入的回归。
- 现有路径仍然能产出三系统并列展示（06Q 已落地 `projection_three_systems`），
  仅在内部判断层做了 zero-out + final_direction 翻转，对**最终用户可见的
  three-system display** 没有阻塞性影响。
- 07A–07D contract 已 commit 进 main（a0956f3）；Step 09 module inventory
  可在不动代码的前提下推进。
- 没有任何模块需要"立即停用"才能保护 main 分支健康。

但需要在 Step 09–12 阶段处理 §13 RISK-1 / RISK-2 的修复，以让代码与契约真正
对齐。

---

## 15. recommended next steps

按顺序推进：

1. **Step 09 — module inventory detail**
   - 对 `services/` 105 个文件做 file-by-file 归属判定
   - 重点解决 §5 表格中所有 `UNKNOWN_REVIEW_REQUIRED` 项
   - 对照 RISK-3 / RISK-4 / RISK-5 / RISK-6 / RISK-7 / RISK-8 详查

2. **Step 10 — keep / freeze / quarantine / cleanup plan**
   - 把 §11 / §12 表格的判定固化到每个文件
   - 仍**不**做删除 / 移动；产出动作清单

3. **Step 11 — dependency / data-flow audit & minimal boundary enforcement plan**
   - 针对 RISK-1（projection ← exclusion）：设计**最小切除方案**
   - 针对 RISK-2（aggregator 引入新判断）：设计**最小重写方案**
   - 针对 RISK-3（confidence 缺独立模块）：设计独立 confidence engine 落地路径
   - 仍**不**改代码，只产出方案

4. **Step 12 — contract enforcement implementation**
   - 按 Step 11 方案做最小 patch
   - 加 contract test：`projection_orchestrator_v2` 禁止 import exclusion_layer；
     `final_decision` 字段不允许翻转 most_likely_state；等等
   - 仍**不**进入 3R-5 / 3R-6

强调：

- **不要**直接删文件
- **不要**直接重构
- **不要**直接进入 3R-5 / 3R-6
- **不要**新增 candidate
- **不要**复活 continuous_smoothing
- 每一步都要保留可回滚（commit-per-step）

---

## 16. 严守边界

本轮**只读诊断**：

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

本 diagnosis 的修改路径：任何对 §4 总评、§13 风险列表、§14 blocker 判定、
§15 next steps 顺序的调整，都必须以**显式更新本文件**的方式提出。
