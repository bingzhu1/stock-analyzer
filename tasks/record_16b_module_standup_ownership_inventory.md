# 16B记录：Module Stand-up / Ownership Inventory

> 本记录是 **Step 16B：模块站队清单**。1.0记录（canonical）+ 16A蓝图
> （architecture detail）已入 main（最新 commit `9b98ad5`）。本轮根据
> 1.0 §15 标签 + 16A §15–§16，把当前 repo 的关键模块逐一归入九分支
> 正式架构、Temporary Migration Bridge、Frozen / Archive 或 Unknown。
>
> 本轮**只**做 inventory / ownership：未改业务代码、未新增测试、
> 未删除文件、未移动文件、未修改 `.gitignore`、未处理 handoff、
> 未处理 logs / DB backup / `.claude/worktrees/`、未跑 replay /
> validation / historical evaluation、未写 DB / 未改 DB schema、
> 未默认迁移 `run_predict` 到 V2、未接 trading、未输出 buy / sell /
> hold / hard / forced / required、未进入 3R-5 / 3R-6、未 commit / 未 push。
>
> 唯一 deliverable：本文件。

---

## 1. Step 16B 目的

让当前 repo 的关键模块**正式站队**：

- 给每个模块一个 1.0 §15 中的标签（`CORE_*` / `TEMP_MIGRATION_BRIDGE` /
  `LEGACY_ACTIVE_DEPENDENCY` / `KEEP_FROZEN_DIAGNOSTIC` / `ARCHIVE` /
  `QUARANTINE_CANDIDATE` / `DELETE_*` / `UNKNOWN_REVIEW_REQUIRED`）
- 标注 active import / caller / 与 07A–07D 契约的合规度 / 风险
- 给出"下一步动作"建议
- **不**改任何代码、**不**移动 / 删除任何文件

本轮**不**做：

- schema 唯一化决定（→ 16C）
- 隔离 / quarantine 实施计划（→ 16D）
- core chain refactor 的 PR 拆分（→ 16E）
- 第一个代码 PR（→ 16F）

---

## 2. 当前前置条件

| 项 | 状态 |
|---|---|
| 1.0 canonical principles 已入 main | ✅ commit `5c209bb` |
| 16A architecture reset blueprint 已入 main | ✅ commit `9b98ad5` |
| Step 12 boundary fixes（11A–11G + 12E X1–X5） | ✅ 全部入 main |
| Step 13 post-fix regression boundary review | ✅ 已 signoff（25 / 25 invariants 通过） |
| Step 14 cleanup（14A–14M） | ✅ 全部入 main |
| Step 15 cleanup regression final signoff | ✅ 已 signoff（3256 passed / 0 failed） |
| 当前 main 最新 commit | `9b98ad5` |
| worktree 唯一 deliberate untracked | `.claude/handoffs/task_089_post_pr_cleanup.md`（14L A2 / 14M / 15 §2） |
| 战略阶段 | 从战略（1.0 + 16A）→ 模块层（16B 本轮） |
| 3R-5 / 3R-6 | ❌ 仍然不允许进入（1.0 §12 / 16A §18） |

---

## 3. 站队标签定义

完整沿用 1.0 §15 + 16A §15：

| 标签 | 含义 |
|---|---|
| `CORE_DATA` | Branch 1 Data Layer |
| `CORE_FEATURE` | Branch 2 Feature Layer |
| `CORE_PROJECTION` | Branch 3 Projection System（07A 契约） |
| `CORE_EXCLUSION` | Branch 4 Exclusion System（07B 契约） |
| `CORE_CONFIDENCE` | Branch 5 Confidence System（07C 契约） |
| `CORE_FINAL_REPORT` | Branch 6 Final Report Layer（07D 契约） |
| `CORE_REVIEW_LEARNING` | Branch 7 Review & Learning Layer |
| `CORE_EVALUATION` | Branch 8 Evaluation Layer |
| `CORE_UI` | Branch 9 UI / Presentation Layer |
| `TEMP_MIGRATION_BRIDGE` | 迁移期兼容；不属正式架构；有明确退出条件 |
| `LEGACY_ACTIVE_DEPENDENCY` | 旧链仍依赖；尚不能 quarantine；优先级低于 Bridge 退出 |
| `KEEP_FROZEN_DIAGNOSTIC` | 只读冻结基线（如 `continuous_smoothing*`）；不接 active path |
| `ARCHIVE` | 已 quarantine 至 `archive/legacy/...` |
| `QUARANTINE_CANDIDATE` | 16B 评估后若无活跃依赖，应进入 archive |
| `DELETE_NOW` | 本轮即可安全删除（**本轮不实施**，仅标记） |
| `DELETE_LATER` | 16D 之后可安全删除 |
| `UNKNOWN_REVIEW_REQUIRED` | 16B 无法自动归类；需进一步人工审视 |

> **本轮硬约束**：本文件中 `DELETE_NOW` / `DELETE_LATER` 标签仅作为
> 提示，**不触发**任何 `rm` / `git rm`。所有"删除"留待 16D / 16E /
> 用户单独确认。

---

## 4. Inventory 表格总览

> 列含义：
> - `module_path`：相对 repo root 的路径
> - `current_role`：模块当前实际承担的职责
> - `target_branch`：未来正式架构归属（或 Bridge / Frozen / Archive）
> - `status_label`：§3 标签
> - `active_imports / callers`：active surface（services / ui / app.py /
>   scripts / 顶层 .py）的依赖关系；`tests/` 路径不算入此列
> - `contract_alignment`：与 07A–07D 草案的对齐情况
> - `risk_level`：`H` / `M` / `L`
> - `next_action`：建议的下一步（**不是**本轮动作）

> **来源约定**：
> - 14G/14H 的 `KEEP_ACTIVE` 分类被 1.0 §14 / 15 §5 接受
> - `continuous_smoothing*` 永久 `FROZEN_DIAGNOSTIC`（06 §8 / 07B §11 /
>   07C §12 / 07D §12 / 15 §6 一致）
> - `archive/legacy/root_stubs/*` 永久 `ARCHIVE`（14D / 15 §6）
> - promotion 三模块永久 `OFFLINE_ONLY`（11G / 13 §4 / 15 §6）—— 不在
>   active path，但**不**进 9 分支正式架构

### 4.1 主表（按 §3 标签分组）

#### 4.1.1 `CORE_DATA`（Branch 1）

| module_path | current_role | target_branch | status_label | active callers / imports | contract_alignment | risk | next_action |
|---|---|---|---|---|---|---|---|
| [data_fetcher.py](data_fetcher.py) | yfinance / 本地 CSV 读取 | Branch 1 | `CORE_DATA` | scanner / encoder / app.py / scripts | 07A §3 white-list 数据来源 | L | 16C/16D：保留；hard rule 2 锁定 |
| [services/market_data_store.py](services/market_data_store.py) | 已下载行情的本地存储读写 | Branch 1 | `CORE_DATA` | 部分 scripts / services | 数据来源合规 | L | 16C/16D：保留 |
| [services/data_query.py](services/data_query.py) | 历史样本 / 面板数据 query | Branch 1 | `CORE_DATA` | `services/projection_orchestrator.py:20` | 数据来源合规 | L | 16C/16D：保留 |
| [services/record_reader.py](services/record_reader.py) | 历史 record 读取 | Branch 1（候选） | `CORE_DATA` | 部分 dashboard / inspector | 数据来源合规 | L | 16B-2 确认是否纯读取 |
| [scanner.py](scanner.py) 数据读取部分 | 读取 + peer 加载 + 历史结构编码 | Branch 1 + Branch 2 + Branch 3（**跨分支**） | `UNKNOWN_REVIEW_REQUIRED` | app.py / ui / predict.py 链路、scripts | hard rule 2 锁定不可重写 | M | 16B-2：拆出"纯数据读取部分" vs "硬规则结构判断部分" |
| [matcher.py](matcher.py) | 五状态历史样本匹配 | Branch 2（特征）+ Branch 3（候选） | `UNKNOWN_REVIEW_REQUIRED` | scanner / predict / scripts | hard rule 2 锁定 | M | 16B-2：拆 feature vs structure |
| [encoder.py](encoder.py) | OHLCV → coded structure 编码 | Branch 1（数据）+ Branch 2（特征） | `UNKNOWN_REVIEW_REQUIRED` | scanner / matcher / data_fetcher | hard rule 2 锁定 | M | 16B-2：拆 data layer vs feature layer 边界 |

#### 4.1.2 `CORE_FEATURE`（Branch 2）

| module_path | current_role | target_branch | status_label | active callers / imports | contract_alignment | risk | next_action |
|---|---|---|---|---|---|---|---|
| [feature_builder.py](feature_builder.py) | 特征推导（顶层） | Branch 2 | `CORE_FEATURE` | scripts / pipeline 链路 | 07A §3.1 / Feature 白名单 | L | 16C/16D：保留；与 features_20d 合并审 |
| [services/features_20d.py](services/features_20d.py) | 20 日特征实现 | Branch 2（**legacy 窗口**） | `CORE_FEATURE` | 部分 services / 历史链 | 07A §3 推荐 15d；当前 20d 为 legacy | M | 16C：决定 15d 迁移路径 |
| [services/regime_features_builder.py](services/regime_features_builder.py) | regime 特征 | Branch 2 | `CORE_FEATURE` | regime 链路 | regime label 输入合规 | L | 16C/16D：保留 |
| [services/regime_labels_builder.py](services/regime_labels_builder.py) | regime 标签构造 | Branch 2 | `CORE_FEATURE` | 同上 | 同上 | L | 同上 |
| [services/state_label.py](services/state_label.py) | 五状态 label 工具 | Branch 2 | `CORE_FEATURE` | matcher / encoder / projection 链 | 五状态命名固定（07A §4） | L | 16C/16D：保留 |
| [services/real_regime_label_provider.py](services/real_regime_label_provider.py) | 真实 regime 标签 provider | Branch 2 | `CORE_FEATURE` | scripts / replay validation | 数据来源合规 | L | 16C/16D：保留 |
| [services/projection_chain_contract.py](services/projection_chain_contract.py) **feature 部分** | `build_feature_payload_from_recent_window` / `_shadow_ratio` / `_ret_pct` | Branch 2 | `CORE_FEATURE`（拆分后） | home_terminal / projection_orchestrator_v2 / 多 services | 07A §3 / Feature 白名单 | M | 16C：将 feature helpers 拆出到独立模块 |

#### 4.1.3 `CORE_PROJECTION`（Branch 3）

| module_path | current_role | target_branch | status_label | active callers / imports | contract_alignment | risk | next_action |
|---|---|---|---|---|---|---|---|
| [services/main_projection_layer.py](services/main_projection_layer.py) | 五状态分布 + Top1 / Top2 | Branch 3 | `CORE_PROJECTION` | `services/home_terminal_orchestrator.py:25`、`services/projection_orchestrator_v2.py:22` | 07A 契约最接近的活模块；**反向 import** `exclusion_layer.build_peer_alignment` ([main_projection_layer.py:18](services/main_projection_layer.py:18))；形参仍接 `exclusion_result` 然后 `del` | H | 16C/16E：迁出 `build_peer_alignment` 到 Feature；删 `exclusion_result` 形参；schema key 对齐 07A |
| [services/primary_20day_analysis.py](services/primary_20day_analysis.py) | V2 链 primary analysis | Branch 3（候选） | `LEGACY_ACTIVE_DEPENDENCY` | `projection_orchestrator_v2._build_primary_analysis` 默认 builder | 与 main_projection_layer 职责重叠 | M | 16C：决定 main_projection_layer vs primary_20day_analysis 谁是事实 Branch 3 实现 |
| [services/peer_adjustment.py](services/peer_adjustment.py) | V2 链 peer adjustment 步骤 | Branch 2（peer feature）+ Branch 3（adjustment 语义）（**跨分支**） | `UNKNOWN_REVIEW_REQUIRED` | `projection_orchestrator_v2._build_peer_adjustment` | 当前实现把 peer 当作"主推演后调整"，与 07A 草案"peer 是 Feature 输入"不一致 | M | 16C：决定 peer_adjustment 是 Feature 还是 Projection 内部步骤 |
| [services/historical_probability.py](services/historical_probability.py) | V2 链 historical probability | Branch 3（候选） | `LEGACY_ACTIVE_DEPENDENCY` | `projection_orchestrator_v2._build_historical_probability` | 历史样本概率分布；07A §3.1 允许 | M | 16C：与 main_projection 输出对齐 |
| [services/projection_preflight.py](services/projection_preflight.py) / [services/projection_orchestrator_preflight.py](services/projection_orchestrator_preflight.py) / [services/projection_rule_preflight.py](services/projection_rule_preflight.py) | preflight 校验链 | Branch 3 内部 | `LEGACY_ACTIVE_DEPENDENCY` | V2 / V1 orchestrator | 11D cutoff_guard 已加固 | L | 16D：合并审；可能整合到 Branch 3 内部 |
| [services/primary_bias_diagnosis.py](services/primary_bias_diagnosis.py) | primary bias 诊断 | Branch 3 内部 / 诊断 | `UNKNOWN_REVIEW_REQUIRED` | 部分 services / scripts | 诊断性质 | L | 16B-2：确认是诊断还是决策 |
| [services/five_state_margin_policy.py](services/five_state_margin_policy.py) | 五状态边界判定 | Branch 3（候选） | `UNKNOWN_REVIEW_REQUIRED` | matcher / projection 链 | 与 07A §4 五状态命名一致 | L | 16C：归位 |

#### 4.1.4 `CORE_EXCLUSION`（Branch 4）

| module_path | current_role | target_branch | status_label | active callers / imports | contract_alignment | risk | next_action |
|---|---|---|---|---|---|---|---|
| [services/exclusion_layer.py](services/exclusion_layer.py) | 否定层（feature-only 输入） | Branch 4 | `CORE_EXCLUSION` | `home_terminal_orchestrator.py:23`、`projection_orchestrator_v2.py:21`、**被 `main_projection_layer.py:18` 反向 import** | 07B 契约最接近的活模块；输出 schema 是 `excluded` / `triggered_rule` / `peer_alignment`，与 07B §9 草案 `most_unlikely_state` / `ranked_unlikely_states` 不一致 | M | 16C：schema 对齐 07B；`build_peer_alignment` 迁出到 Feature |
| [services/anti_false_exclusion_audit.py](services/anti_false_exclusion_audit.py) | 反假排除 audit | Branch 4 内部诊断 / Branch 8 Evaluation（候选） | `UNKNOWN_REVIEW_REQUIRED` | 部分 services / scripts | 不输出 mutation；偏诊断 | L | 16B-2：确认是 Branch 4 内部 vs Branch 7 / 8 |
| [services/anti_false_exclusion_dashboard.py](services/anti_false_exclusion_dashboard.py) | 反假排除 dashboard | Branch 9 UI（候选） | `UNKNOWN_REVIEW_REQUIRED` | UI / scripts | display 性质 | L | 16B-2 |
| [services/big_up_contradiction_card.py](services/big_up_contradiction_card.py) | 大涨矛盾 card | Branch 4 内部诊断 | `UNKNOWN_REVIEW_REQUIRED` | `ui/big_up_contradiction_card.py` / 链 | 是否对 projection 反向校验需审 | M | 16B-2：确认是否违反"否定不读 projection"边界 |
| [services/big_down_tail_warning.py](services/big_down_tail_warning.py) | 大跌尾部告警 | Branch 4 内部诊断 | `UNKNOWN_REVIEW_REQUIRED` | 部分 services | 类似 big_up_contradiction_card | M | 16B-2 |
| [services/exclusion_reliability_review.py](services/exclusion_reliability_review.py) | 否定可靠性 review | Branch 7 Review & Learning（候选）/ Branch 5 Confidence（数据准备，候选） | `UNKNOWN_REVIEW_REQUIRED` | `ui/exclusion_reliability_review.py` / 链 | 跨分支 | M | 16B-2：定 Branch 7 还是 Branch 5 数据准备 |

#### 4.1.5 `CORE_CONFIDENCE`（Branch 5）

| module_path | current_role | target_branch | status_label | active callers / imports | contract_alignment | risk | next_action |
|---|---|---|---|---|---|---|---|
| [services/confidence_evaluator.py](services/confidence_evaluator.py) | 置信度评估器（read-only） | Branch 5 | `CORE_CONFIDENCE` | `home_terminal_orchestrator.py:21`、`projection_orchestrator_v2.py:12` | 07C 契约边界合规（read-only / 禁字段 / 无 mutation）；但 `_compute_agreement` key 与 main_projection / exclusion 输出不对齐；`calibration_context` 在两处 caller 均未传 | H | 16C：key 对齐 + 接入 calibration_context；内部边界已合规 |
| [services/contract_calibration_inputs.py](services/contract_calibration_inputs.py) | calibration input 聚合 | Branch 5 数据准备（候选） | `UNKNOWN_REVIEW_REQUIRED` | scripts / services | 暂未接入 confidence_evaluator | M | 16C：决定 calibration_context wiring |
| [services/active_rule_pool.py](services/active_rule_pool.py) | 规则池主体 | Branch 7 Review & Learning（候选） | `UNKNOWN_REVIEW_REQUIRED` | 部分 services | active path 状态需复查 | M | 16B-2 |
| [services/active_rule_pool_calibration.py](services/active_rule_pool_calibration.py) | 规则池校准 | Branch 5 数据准备 / Branch 7（候选） | `UNKNOWN_REVIEW_REQUIRED` | 部分 services | 跨分支 | M | 16B-2 |
| [services/active_rule_pool_drift.py](services/active_rule_pool_drift.py) | 规则池 drift | Branch 5 数据准备 / Branch 7（候选） | `UNKNOWN_REVIEW_REQUIRED` | 部分 services | 跨分支 | M | 16B-2 |
| [services/active_rule_pool_export.py](services/active_rule_pool_export.py) | 规则池 export | Branch 7 / Branch 8（候选） | `UNKNOWN_REVIEW_REQUIRED` | 部分 services | 跨分支 | M | 16B-2 |
| [services/active_rule_pool_validation.py](services/active_rule_pool_validation.py) | 规则池 validation | Branch 8 Evaluation（候选） | `UNKNOWN_REVIEW_REQUIRED` | 部分 services | 跨分支 | M | 16B-2 |

#### 4.1.6 `CORE_FINAL_REPORT`（Branch 6）

| module_path | current_role | target_branch | status_label | active callers / imports | contract_alignment | risk | next_action |
|---|---|---|---|---|---|---|---|
| [services/final_decision.py](services/final_decision.py) | strict passthrough aggregator | Branch 6 | `CORE_FINAL_REPORT` | `projection_orchestrator_v2.py:13` | 07D 契约最接近的活模块；`final_direction` 严格 = `primary_direction`；`final_confidence` 来自 `confidence_result`；`exclusion` display-only | L | 16C：schema 对齐 07D §9；与 `projection_output_contract` 8 段统一 |
| [services/projection_output_contract.py](services/projection_output_contract.py) | 8 段 schema validator | Branch 6（外部对接） | `CORE_FINAL_REPORT` | `contract_payload_*` / `contract_calibration_inputs` / `contract_outcome_correlation` | 是 step_1a 8 段契约的 validator；当前无原生产出者 | M | 16C：决定 8 段是否为外部对接版 |
| [services/projection_output_adapter.py](services/projection_output_adapter.py) | 旧 → 8 段翻译层 | Branch 6（adapter）/ Bridge | `UNKNOWN_REVIEW_REQUIRED` | 暂无 active import（仅 docstring 中提到） | adapter 性质 | M | 16B-2：确认 active 状态；可能是 dormant adapter |
| [services/projection_chain_contract.py](services/projection_chain_contract.py) **payload 部分** | `build_unified_projection_payload` / `build_prediction_log_record` | Branch 6 | `UNKNOWN_REVIEW_REQUIRED`（拆分前） | home_terminal / projection_orchestrator_v2 | 与 final_decision 不同的 payload 组装器 | M | 16C：拆分 — feature helpers → Branch 2，payload assembler → Branch 6 |
| [services/projection_three_systems_renderer.py](services/projection_three_systems_renderer.py) | 三系统并列展示渲染器 | Branch 6（render）/ Branch 9 UI（候选） | `UNKNOWN_REVIEW_REQUIRED` | UI / 链 | display 性质 | L | 16B-2：定 Branch 6 vs Branch 9 |
| [services/projection_narrative_renderer.py](services/projection_narrative_renderer.py) | narrative 渲染器 | Branch 6 / Branch 9（候选） | `UNKNOWN_REVIEW_REQUIRED` | UI / 链 | display 性质 | L | 16B-2 |
| [services/predict_summary.py](services/predict_summary.py) | predict_result 摘要 | Branch 6 / Bridge | `LEGACY_ACTIVE_DEPENDENCY` | `services/projection_orchestrator.py:22`（V1 链） | 12E X3 已加固 | M | 16C：随 Bridge 退出条件迁移 |
| [services/ai_summary.py](services/ai_summary.py) | LLM-based summary | Branch 6（受限） | `LEGACY_ACTIVE_DEPENDENCY` | UI / 链 | 11F default-disabled；source attribution 已加固 | M | 16C：保留为 disabled by default，未来作为 Branch 6 narrative 选项 |
| [services/consistency_layer.py](services/consistency_layer.py) | projection / exclusion 一致性 | Branch 6（候选）/ Branch 5 Confidence 数据 | `UNKNOWN_REVIEW_REQUIRED` | `home_terminal_orchestrator.py:22`、`projection_orchestrator_v2.py:23` | 与 07C agreement_status 职责重叠 | M | 16C：合并到 confidence_evaluator 或保留为 final_report 输入 |

#### 4.1.7 `CORE_REVIEW_LEARNING`（Branch 7）

| module_path | current_role | target_branch | status_label | active callers / imports | contract_alignment | risk | next_action |
|---|---|---|---|---|---|---|---|
| [services/outcome_capture.py](services/outcome_capture.py) | 真实结果捕获 | Branch 7 | `CORE_REVIEW_LEARNING` | `ui/predict_tab.py:20`、`review_orchestrator.py:54`、`contract_replay_writer.py:85`、`historical_replay_training.py`、scripts | 07A/B/C/D 各 §3.2 future outcome 仅离线允许 | L | 16C/16D：保留 |
| [services/review_orchestrator.py](services/review_orchestrator.py) | 复盘编排 | Branch 7 | `CORE_REVIEW_LEARNING` | `ui/predict_tab.py:22`、scripts | 不进当次预测路径 | L | 16C/16D：保留 |
| [services/review_center.py](services/review_center.py) | 复盘 center | Branch 7 | `CORE_REVIEW_LEARNING` | `ui/review_tab.py:631` | 同上 | L | 16C/16D：保留 |
| [services/review_analyzer.py](services/review_analyzer.py) | 复盘分析 / 历史规则提取 | Branch 7 | `CORE_REVIEW_LEARNING` | `ui/review_tab.py:756`、`ui/predict_tab.py:23`、`ui/home_tab.py:479`、`pre_prediction_briefing.py:34`、scripts | 同上 | L | 16C/16D：保留 |
| [services/review_classifier.py](services/review_classifier.py) | 复盘分类 | Branch 7 | `CORE_REVIEW_LEARNING` | review 链 | 同上 | L | 16C/16D：保留 |
| [services/review_comparator.py](services/review_comparator.py) | 复盘比较 | Branch 7 | `CORE_REVIEW_LEARNING` | review 链 | 同上 | L | 16C/16D：保留 |
| [services/review_agent.py](services/review_agent.py) | 复盘 agent | Branch 7 | `CORE_REVIEW_LEARNING` | review 链 | 同上 | L | 16C/16D：保留 |
| [services/review_store.py](services/review_store.py) | review 持久化 | Branch 7 | `CORE_REVIEW_LEARNING` | review 链 | 持久化层 | L | 16C/16D：保留 |
| [services/memory_store.py](services/memory_store.py) | 记忆持久化 | Branch 7 | `CORE_REVIEW_LEARNING` | `services/memory_feedback.py:18` 等 | 11D cutoff_guard 已加固 | L | 16C/16D：保留 |
| [services/memory_feedback.py](services/memory_feedback.py) | 记忆反馈 | Branch 7 | `CORE_REVIEW_LEARNING` | `services/projection_memory_briefing.py:14` 等 | 同上 | L | 16C/16D：保留 |
| [services/projection_memory_briefing.py](services/projection_memory_briefing.py) | projection memory briefing | Branch 7 | `CORE_REVIEW_LEARNING` | `projection_rule_preflight.py:20`、`projection_preflight.py:11` | 11D cutoff_guard 已加固 | L | 16C/16D：保留 |
| [services/pre_prediction_briefing.py](services/pre_prediction_briefing.py) | 预测前 briefing | Branch 7 | `CORE_REVIEW_LEARNING` | `ui/predict_tab.py:24`、`ui/home_tab.py:480`、scripts | **风险**：当前 `predict.py:1357` `_apply_briefing_caution` 仍 mutate `final_confidence`（属 Bridge 旧行为，非 Branch 7 本身违规） | M | 16E：把 caution 移到 Final Report Layer 展示标注，而非 mutate confidence |
| [services/projection_review_closed_loop.py](services/projection_review_closed_loop.py) | 复盘闭环 | Branch 7 | `CORE_REVIEW_LEARNING` | review 链 / scripts | 闭环逻辑；future-as-label 仅离线 | L | 16C/16D：保留 |
| [services/rule_lifecycle.py](services/rule_lifecycle.py) | 规则生命周期 | Branch 7（候选） | `UNKNOWN_REVIEW_REQUIRED` | `services/avgo_1000day_training.py:107` 等 | 与 active_rule_pool* 共享命名空间；与 promotion 命名重叠 | M | 16B-2：定与 promotion 三模块的隔离 |
| [services/rule_scoring.py](services/rule_scoring.py) | 规则评分 | Branch 7（候选） | `UNKNOWN_REVIEW_REQUIRED` | `services/avgo_1000day_training.py:101` | 同上 | M | 16B-2 |
| [services/prediction_store.py](services/prediction_store.py) | 预测快照持久化 | Branch 6（Final Report 出口）/ Branch 7（Review 输入）（**跨分支**） | `UNKNOWN_REVIEW_REQUIRED` | `ui/history_tab.py:10`、`ui/predict_tab.py:15`、`ui/home_tab.py:338`、`outcome_capture.py:53`、`review_*` / `contract_*` / `regime_diagnostics_dashboard` / scripts（高度 fan-in） | 持久化层；不参与 mutation | L | 16B-2：定持久化层归属（建议作为 Branch 6 出口的物化层 + Branch 7 输入） |
| [services/projection_record_store.py](services/projection_record_store.py) | projection record 持久化 | Branch 6 / Branch 7（候选） | `UNKNOWN_REVIEW_REQUIRED` | `scripts/save_projection_records_smoke.py:49` | 持久化层 | L | 16B-2 |
| [services/log_store.py](services/log_store.py) | prediction_log 写入 | Branch 6 出口物化（候选） | `CORE_FINAL_REPORT`（候选） | `home_terminal_orchestrator.py:24` | 写 `logs/prediction_log.jsonl` | L | 16C/16D：保留 |

#### 4.1.8 `CORE_EVALUATION`（Branch 8）

| module_path | current_role | target_branch | status_label | active callers / imports | contract_alignment | risk | next_action |
|---|---|---|---|---|---|---|---|
| [services/historical_replay_training.py](services/historical_replay_training.py) | 历史 replay | Branch 8 | `CORE_EVALUATION` | scripts | future outcome 仅离线；2026 holdout 须保留 | M | 16C/16D：保留；明确 holdout 政策 |
| [services/three_system_replay_audit.py](services/three_system_replay_audit.py) | 三系统 replay audit | Branch 8 | `CORE_EVALUATION` | scripts | 同上 | M | 16C/16D：保留 |
| [services/replay_record_wiring.py](services/replay_record_wiring.py) | replay 接线 | Branch 8 | `CORE_EVALUATION` | scripts | 接线层 | L | 16C/16D：保留 |
| [services/replay_validation_record_adapter.py](services/replay_validation_record_adapter.py) | replay validation adapter | Branch 8 | `CORE_EVALUATION` | scripts | 同上 | L | 16C/16D：保留 |
| [services/contract_replay_planner.py](services/contract_replay_planner.py) | replay 计划 | Branch 8 | `CORE_EVALUATION` | scripts | 计划层 | L | 16C/16D：保留 |
| [services/contract_replay_writer.py](services/contract_replay_writer.py) | replay 写入；调 `predict.run_predict` | Branch 8 + Bridge 调用方（**跨分支**） | `LEGACY_ACTIVE_DEPENDENCY` | scripts | **调用旧链** `run_predict`（[contract_replay_writer.py:83](services/contract_replay_writer.py:83)、[:475](services/contract_replay_writer.py:475)） | H | 16E：随 Bridge 退出条件 #2 迁移到新 Branch 6 schema |
| [services/contract_outcome_correlation.py](services/contract_outcome_correlation.py) | outcome 相关性 | Branch 8 | `CORE_EVALUATION` | scripts | 离线评估 | L | 16C/16D：保留 |
| [services/regime_diagnostics_dashboard.py](services/regime_diagnostics_dashboard.py) | regime 诊断 dashboard | Branch 8 + Branch 9 UI（**跨分支**） | `UNKNOWN_REVIEW_REQUIRED` | scripts / UI | 离线诊断 + UI 展示 | L | 16B-2：拆 dashboard 数据 vs 渲染 |
| [services/regime_validation_helper.py](services/regime_validation_helper.py) | regime validation helper | Branch 8 | `CORE_EVALUATION` | scripts | 同上 | L | 16C/16D：保留 |
| [services/stats_engine.py](services/stats_engine.py) | 统计引擎 | Branch 8 | `CORE_EVALUATION` | dashboard / scripts | 统计层 | L | 16C/16D：保留 |
| [services/avgo_1000day_training.py](services/avgo_1000day_training.py) | 1000-day 训练编排 | Branch 8 | `CORE_EVALUATION` | scripts | 离线训练编排 | M | 16C/16D：保留；2026 holdout 政策对齐 |
| [services/daily_training_pipeline.py](services/daily_training_pipeline.py) | 日训练 pipeline | Branch 8 | `CORE_EVALUATION` | scripts | 同上 | M | 16C/16D：保留 |
| [services/daily_training_summary.py](services/daily_training_summary.py) | 日训练 summary | Branch 8 | `CORE_EVALUATION` | scripts | 离线 | L | 16C/16D：保留 |
| [stats_reporter.py](stats_reporter.py)（root） | 统计报告（root） | Branch 8（候选）/ Bridge | `UNKNOWN_REVIEW_REQUIRED` | scripts / pipeline | 顶层位置不合分支约束 | L | 16B-2：是否迁入 services/ |
| [run_pipeline.py](run_pipeline.py) / [run_1000day.py](run_1000day.py)（root） | pipeline 入口（root） | Branch 8 入口（候选） | `UNKNOWN_REVIEW_REQUIRED` | shell / docs | 顶层 entrypoint | L | 16B-2 |

#### 4.1.9 `CORE_UI`（Branch 9）

| module_path | current_role | target_branch | status_label | active callers / imports | contract_alignment | risk | next_action |
|---|---|---|---|---|---|---|---|
| [app.py](app.py) | Streamlit 主入口 | Branch 9 | `CORE_UI` | 顶层 entry；引用 `home_terminal_orchestrator` 等 | hard rule 3：app.py 只允许最小改动 | M | 16C/16E：app.py 不进新业务逻辑 |
| [ui/__init__.py](ui/__init__.py) | UI 包 init | Branch 9 | `CORE_UI` | 包入口 | — | L | 16C/16D：保留 |
| [ui/home_tab.py](ui/home_tab.py) | home tab | Branch 9 | `CORE_UI` | app.py | 已读 prediction_store / review_analyzer / pre_prediction_briefing | L | 16C：迁到新 final_report schema |
| [ui/predict_tab.py](ui/predict_tab.py) | 主预测 tab | Branch 9 | `CORE_UI` | app.py；**直调 [`predict.run_predict`](ui/predict_tab.py:1410)** | 仍读旧字段 `final_bias` / `final_confidence` / `primary_projection` / `final_projection` | H | 16E：切到新 final_report schema；触发 Bridge 退出条件 #1 |
| [ui/scan_tab.py](ui/scan_tab.py) | scan tab | Branch 9 | `CORE_UI` | app.py | 主要展示 | L | 16C/16D：保留 |
| [ui/research_tab.py](ui/research_tab.py) | research tab | Branch 9 | `CORE_UI` | app.py | 主要展示 | L | 16C/16D：保留 |
| [ui/review_tab.py](ui/review_tab.py) | review tab | Branch 9 | `CORE_UI` | app.py；调 review_center / review_analyzer | 同上 | L | 16C/16D：保留 |
| [ui/history_tab.py](ui/history_tab.py) | history tab | Branch 9 | `CORE_UI` | app.py；读 prediction_store | 同上 | L | 16C/16D：保留 |
| [ui/inspect_tab.py](ui/inspect_tab.py) | inspect tab | Branch 9 | `CORE_UI` | app.py | 同上 | L | 16C/16D：保留 |
| [ui/control_tab.py](ui/control_tab.py) | control tab | Branch 9 | `CORE_UI` | app.py | 同上 | L | 16C/16D：保留 |
| [ui/command_bar.py](ui/command_bar.py) | command bar | Branch 9 | `CORE_UI` | app.py / 链路 | 12E 已加固；ai_intent_parser default-disabled | L | 16C/16D：保留 |
| [ui/projection_v2_renderer.py](ui/projection_v2_renderer.py) | V2 渲染器 | Branch 6（render）/ Branch 9（候选） | `UNKNOWN_REVIEW_REQUIRED` | UI 链 | display 性质 | L | 16B-2：定 Branch 6 vs Branch 9 |
| [ui/protection_layer_diagnostics_renderer.py](ui/protection_layer_diagnostics_renderer.py) | protection diagnostics 渲染 | Branch 9 | `CORE_UI` | UI 链 | display；与 promotion 隔离 | L | 16C/16D：保留 |
| [ui/anti_false_exclusion_display.py](ui/anti_false_exclusion_display.py) | 反假排除展示 | Branch 9 | `CORE_UI` | UI 链 | display | L | 16C/16D：保留 |
| [ui/exclusion_reliability_review.py](ui/exclusion_reliability_review.py) | 否定可靠性展示 | Branch 9 | `CORE_UI` | UI 链 | display | L | 16C/16D：保留 |
| [ui/big_up_contradiction_card.py](ui/big_up_contradiction_card.py) | 大涨矛盾 card UI | Branch 9 | `CORE_UI` | UI 链 | display | L | 16C/16D：保留 |
| [ui/labels.py](ui/labels.py) | 中文 / display labels | Branch 9 | `CORE_UI` | UI 链 | 翻译 | L | 16C/16D：保留 |
| [ui/soft_metadata_renderer.py](ui/soft_metadata_renderer.py) / [ui/soft_metadata_baseline_cache.py](ui/soft_metadata_baseline_cache.py) | soft metadata UI | Branch 9 | `CORE_UI` | UI 链 | display；与 promotion 隔离 | L | 16C/16D：保留 |

#### 4.1.10 `TEMP_MIGRATION_BRIDGE`

| module_path | current_role | target_branch | status_label | active callers / imports | contract_alignment | risk | next_action |
|---|---|---|---|---|---|---|---|
| [predict.py](predict.py) | legacy wrapper（含旧 `build_primary_projection` / `apply_peer_adjustment` / `build_final_projection` / `_summarize` / `_apply_briefing_caution` / `_apply_v2_legacy_adapter_overlay`） | Bridge | `TEMP_MIGRATION_BRIDGE` | `ui/predict_tab.py:1410`、`services/projection_orchestrator.py:107`、`services/contract_replay_writer.py`、`services/predict_legacy_v2_bridge.py:80`、`scripts/run_e2e_loop.py:108` | 12E X1..X5 boundary 已封禁 mutation surface；仍是 UI 主入口 | H | 16E：UI / replay 切走后随 Bridge 退出条件解散 |
| [services/predict_legacy_adapter.py](services/predict_legacy_adapter.py) | v2 → legacy 字段翻译（X4-A） | Bridge | `TEMP_MIGRATION_BRIDGE` | `predict.py:44`（lazy 路径） | 12E X4-A | M | 16E：随 Bridge 退出 |
| [services/predict_legacy_v2_bridge.py](services/predict_legacy_v2_bridge.py) | isolated bridge helper（X4-C） | Bridge | `TEMP_MIGRATION_BRIDGE` | **当前无 active import**（13 §5 / 15 §5 已确认） | 12E X4-C；isolated | L | 16D/16E：可作 Bridge 第一个解散候选 |

> **legacy 字段（不是文件，是 schema 字段）**：`final_bias` /
> `final_confidence` / `confidence` / `primary_projection` /
> `peer_adjustment` / `final_projection` / `path_risk` /
> `peer_path_risk_adjustment`。这些字段定义在 [predict.py:297](predict.py:297)
> `PredictResult` TypedDict 中；属 Bridge schema，不进 9 分支。

#### 4.1.11 `LEGACY_ACTIVE_DEPENDENCY`

| module_path | current_role | target_branch | status_label | active callers / imports | contract_alignment | risk | next_action |
|---|---|---|---|---|---|---|---|
| [services/projection_orchestrator.py](services/projection_orchestrator.py) | V1 orchestrator；调 `predict.run_predict` | （正式架构内不属任何分支） | `LEGACY_ACTIVE_DEPENDENCY` | `services/projection_orchestrator_v2.py:16`（V2 内部回调） | 14G/14H KEEP_ACTIVE 分类已确认；正式架构内**无家** | H | 16E：切断 V2 → V1 反向调用，再随 Bridge 解散 |
| [services/projection_orchestrator_v2.py](services/projection_orchestrator_v2.py) | V2 orchestrator | （跨分支：preflight + primary + peer + historical + standardized chain + final_decision） | `LEGACY_ACTIVE_DEPENDENCY` | `services/projection_entrypoint.py:7`、`services/projection_v2_adapter.py:12`、`services/historical_replay_training.py:101`、`scripts/save_projection_records_smoke.py:441` | 是当前 V2 主链入口；但仍**回调 V1** orchestrator | H | 16C：决定主入口；16E：拆为 Branch 2/3/4/5/6 直连，去掉 V1 回调 |
| [services/projection_entrypoint.py](services/projection_entrypoint.py) | V2 entrypoint wrapper | （跨分支） | `LEGACY_ACTIVE_DEPENDENCY` | 部分 services / scripts | 包装 V2 raw → projection_three_systems | M | 16C：随 V2 主入口决定迁移 |
| [services/projection_v2_adapter.py](services/projection_v2_adapter.py) | V2 adapter | Bridge / 退出后归 Branch 6 | `LEGACY_ACTIVE_DEPENDENCY` | 部分 services | adapter 性质 | M | 16E：随 Bridge 退出 |
| [services/home_terminal_orchestrator.py](services/home_terminal_orchestrator.py) | home 主页主链 | （跨分支：feature → exclusion → projection → consistency → confidence + log） | `LEGACY_ACTIVE_DEPENDENCY` | `app.py:86, 1899` | 与 V2 路径并存；`calibration_context` 未传 | H | 16C：决定主入口（home_terminal vs V2 vs new orchestrator） |
| [services/projection_orchestrator_preflight.py](services/projection_orchestrator_preflight.py) | V1/V2 preflight | Branch 3 内部（候选） | `LEGACY_ACTIVE_DEPENDENCY` | V1 / V2 链 | 11D 已加固 | L | 16D：合并审 |

#### 4.1.12 `KEEP_FROZEN_DIAGNOSTIC`

| module_path | status_label | reason | next_action |
|---|---|---|---|
| [services/continuous_smoothing_candidate.py](services/continuous_smoothing_candidate.py) | `KEEP_FROZEN_DIAGNOSTIC` | 3R-3 abandon as candidate；06 §8 / 07B §11 / 07C §12 / 07D §12 / 1.0 §6.17 永久禁活；frozen baseline 用于 postmortem | 永久不进 active；如复用必须独立 launch review |
| [services/continuous_smoothing_candidate_v2.py](services/continuous_smoothing_candidate_v2.py) | `KEEP_FROZEN_DIAGNOSTIC` | 同上 | 同上 |
| [scripts/run_continuous_smoothing_validation.py](scripts/run_continuous_smoothing_validation.py) | `KEEP_FROZEN_DIAGNOSTIC` | 配套 v1 候选的离线 validator | 永久离线；不进 active |
| [scripts/run_continuous_smoothing_validation_v2.py](scripts/run_continuous_smoothing_validation_v2.py) | `KEEP_FROZEN_DIAGNOSTIC` | 配套 v2 候选 | 同上 |
| [scripts/run_real_continuous_smoothing_validation*.py](scripts/run_real_continuous_smoothing_validation.py) (3 个) | `KEEP_FROZEN_DIAGNOSTIC` | 配套真实 validator | 同上 |

#### 4.1.13 `ARCHIVE`

| module_path | status_label | reason |
|---|---|---|
| [archive/legacy/root_stubs/_DEPRECATED.md](archive/legacy/root_stubs/_DEPRECATED.md) | `ARCHIVE` | 14D quarantine marker |
| [archive/legacy/root_stubs/confidence_engine.py](archive/legacy/root_stubs/confidence_engine.py) | `ARCHIVE` | 14D quarantined v1 stub |
| [archive/legacy/root_stubs/contradiction_engine.py](archive/legacy/root_stubs/contradiction_engine.py) | `ARCHIVE` | 14D quarantined v1 stub |
| [archive/legacy/root_stubs/risk_model.py](archive/legacy/root_stubs/risk_model.py) | `ARCHIVE` | 14D quarantined v1 stub |
| [records/03_replay_accuracy_and_exclusion_accuracy.md](records/03_replay_accuracy_and_exclusion_accuracy.md) | `ARCHIVE`（候选） | 仅一个文件；评估历史 evidence | 16B-2：核实是否仍被引用，若否 → 永久 archive |

#### 4.1.14 `OFFLINE_ONLY`（**正式架构内无家**）

| module_path | status_label | reason | next_action |
|---|---|---|---|
| [services/promotion_adoption_gate.py](services/promotion_adoption_gate.py) | `OFFLINE_ONLY` | 11G / 13 §4 / 15 §6 永久 OFFLINE | 不进任何分支；不复活 |
| [services/promotion_execution_bridge.py](services/promotion_execution_bridge.py) | `OFFLINE_ONLY` | 同上 | 同上 |
| [services/active_rule_pool_promotion.py](services/active_rule_pool_promotion.py) | `OFFLINE_ONLY` | 同上 | 同上 |
| [services/protection_layer_diagnostics.py](services/protection_layer_diagnostics.py) | `OFFLINE_ONLY` 诊断 | 与 promotion 同套；display only | 不进 active path；UI 展示走 `ui/protection_layer_diagnostics_renderer.py` |

#### 4.1.15 `UNKNOWN_REVIEW_REQUIRED`（其它）

> 见 §9 详述。本表先列名：

| module_path | candidate target | reason |
|---|---|---|
| [services/agent_parser.py](services/agent_parser.py) / [services/agent_schema.py](services/agent_schema.py) | Branch 9 (UI / command_bar 内部) | command-bar agent parsing；性质待审 |
| [services/ai_intent_parser.py](services/ai_intent_parser.py) / [services/ai_task_parser.py](services/ai_task_parser.py) | Branch 9 / 工具层 | 12E 已封禁；用户输入解析；不参与判断 |
| [services/automation_wrapper.py](services/automation_wrapper.py) | Branch 9 / 工具层 | command-bar 自动化；待审 |
| [services/tool_router.py](services/tool_router.py) / [services/intent_planner.py](services/intent_planner.py) / [services/plan_normalizer.py](services/plan_normalizer.py) / [services/command_parser.py](services/command_parser.py) | Branch 9 / 工具层 | command-bar 工具链 |
| [services/openai_client.py](services/openai_client.py) | Branch 6 narrative tooling / 工具层 | LLM client；ai_summary / ai_intent_parser 用 |
| [services/analysis_context.py](services/analysis_context.py) | Branch 9 / 工具层 | UI / 上下文 |
| [services/dashboard_view_model.py](services/dashboard_view_model.py) | Branch 9 view model | UI 数据组装 |
| [services/multi_symbol_view.py](services/multi_symbol_view.py) | Branch 9 / 工具层 | 多 symbol 视图 |
| [services/inspect_analysis.py](services/inspect_analysis.py) | Branch 9 / 诊断 | inspect tab 数据 |
| [services/error_taxonomy.py](services/error_taxonomy.py) | 工具层 | 错误分类 |
| [services/date_range_parser.py](services/date_range_parser.py) | 工具层 | 通用 parser |
| [services/evidence_trace.py](services/evidence_trace.py) | Branch 6 / Branch 7 | evidence 追踪 |
| [services/contract_payload_diff.py](services/contract_payload_diff.py) / [services/contract_payload_extras_dashboard.py](services/contract_payload_extras_dashboard.py) / [services/contract_payload_inspector.py](services/contract_payload_inspector.py) / [services/contract_payload_trend.py](services/contract_payload_trend.py) | Branch 8 (offline diagnostics) / Branch 9 (dashboard) | 8 段 schema 离线分析 |
| [services/cutoff_guard.py](services/cutoff_guard.py) | Branch 7 内部 / 工具层 | 11D guard；read-only 防护 |
| [services/soft_metadata_injection.py](services/soft_metadata_injection.py) / [services/soft_metadata_simulator.py](services/soft_metadata_simulator.py) | Branch 6 metadata / Branch 8 simulator | 与 promotion 隔离 |
| [services/query_executor.py](services/query_executor.py) | 工具层 / Branch 9 | UI / dashboard 查询 |
| [research.py](research.py)（root） | Bridge / Branch 8 | 顶层 research 入口；待审 |
| [scripts/*](scripts/) 中非 continuous_smoothing 的 25+ 脚本 | Branch 8 入口 / Bridge 工具 | 大批量 evaluation 脚本；按用途逐一站队 |

### 4.2 用户清单中"不存在"的模块

> 用户在本轮指令中点名了若干模块，扫描结果如下：

| 用户提到 | 状态 | 实际等价物 |
|---|---|---|
| `services/rule_memory.py` | ❌ 不存在 | `services/memory_store.py` + `services/memory_feedback.py`（Branch 7） |
| `services/market_data_collector.py` | ❌ 不存在 | `services/market_data_store.py`（Branch 1）+ `data_fetcher.py`（Branch 1） |
| `collectors/` | ❌ 目录不存在 | 数据收集职责分散在 `data_fetcher.py` / `services/market_data_store.py` / `scanner.py` 数据读取部分 |

> 不编造内容；仅记录。

---

## 5. CORE modules（按九分支分组）

### 5.1 Data（Branch 1）

**模块**：`data_fetcher.py` / `services/market_data_store.py` /
`services/data_query.py` / `services/record_reader.py` + `scanner.py` /
`matcher.py` / `encoder.py` 的纯数据读取部分。

**为什么属于这里**：

- 读 OHLCV / panel / 历史样本，**不**做判断
- hard rule 2 锁定 scanner / matcher / encoder 是硬规则层，需要在 16B-2
  拆出"纯数据读取"vs"硬规则结构推断"边界，否则 Data 与 Projection 混淆

**当前是否合规**：基本合规；但 scanner / matcher / encoder 跨分支没拆开。

**需要修什么**：

- 16B-2：拆出 scanner / matcher / encoder 的 Data Layer 部分（独立函数 /
  独立 module，不必拆文件）
- 16C/16D：保留主体；hard rule 2 锁定不可重写

### 5.2 Feature（Branch 2）

**模块**：`feature_builder.py` / `services/features_20d.py` /
`services/regime_features_builder.py` / `services/regime_labels_builder.py` /
`services/state_label.py` / `services/real_regime_label_provider.py` +
`services/projection_chain_contract.py` 的 feature 部分。

**为什么属于这里**：

- 把 raw 数据变成 `feature_payload`
- `peer_alignment` 在 1.0 §8 / 16A §6 明确归 Feature Layer

**当前是否合规**：

- 窗口长度仍是 20d；与 07A §3.1 / §9 草案的 15d 不一致
- `peer_alignment` 当前位于 [services/exclusion_layer.py:64](services/exclusion_layer.py:64)，
  被 [services/main_projection_layer.py:18](services/main_projection_layer.py:18)
  反向 import；这是结构性违规
- `projection_chain_contract.py` 同时含 feature helpers 与 payload assembler；
  需要拆分

**需要修什么**：

- 16C：决定 15d 迁移路径；20d 实现暂为 legacy / compatibility
- 16C / 16E：把 `build_peer_alignment` 抽到独立模块（如
  `services/peer_alignment.py`），让 Projection / Exclusion 都从
  Feature Layer import
- 16C：拆 `projection_chain_contract.py` — feature helpers → Branch 2，
  payload assembler → Branch 6

### 5.3 Projection（Branch 3）

**主模块**：[services/main_projection_layer.py](services/main_projection_layer.py)。

**辅助模块**：
[services/primary_20day_analysis.py](services/primary_20day_analysis.py)（V2 链 primary builder，
与 main_projection 职责重叠）/
[services/historical_probability.py](services/historical_probability.py) /
[services/peer_adjustment.py](services/peer_adjustment.py) / preflight 三件套。

**为什么属于这里**：07A 契约最接近的活模块。

**当前是否合规**：

- ❌ 反向 import `services/exclusion_layer.build_peer_alignment`
  ([main_projection_layer.py:18](services/main_projection_layer.py:18))
- ❌ 形参仍接受 `exclusion_result` 然后 `del`
  ([main_projection_layer.py:286](services/main_projection_layer.py:286)、[:298](services/main_projection_layer.py:298))
- ❌ 输出 schema 用 `predicted_top1.state` / `state_probabilities`，与
  07A §9 草案 `most_likely_state` / `ranked_states` / `state_scores` 不一致
- ❓ V2 链的 `primary_20day_analysis` 与 `main_projection_layer` 同时存在；
  需在 16C 选定唯一 Branch 3 实现

**需要修什么**（16C / 16E）：

- 抽 `build_peer_alignment` 到 Feature Layer
- 删 `exclusion_result` 形参
- schema 对齐 07A 或显式声明"实现层 schema 与 contract 草案的映射规则"

### 5.4 Exclusion（Branch 4）

**主模块**：[services/exclusion_layer.py](services/exclusion_layer.py)。

**辅助 / 待审模块**：anti_false_exclusion_audit / anti_false_exclusion_dashboard /
big_up_contradiction_card / big_down_tail_warning / exclusion_reliability_review。

**为什么属于这里**：07B 契约最接近的活模块；输入 feature-only，**不** 读 projection。

**当前是否合规**：

- ✅ 不读 `projection_result` / `most_likely_state`
- ❌ 输出 schema 是 `excluded` / `triggered_rule` / `peer_alignment` / `reasons`，
  与 07B §9 草案 `most_unlikely_state` / `ranked_unlikely_states` 不一致
- ❌ `build_peer_alignment` 不属于 Exclusion，应迁出

**需要修什么**（16C）：

- schema 对齐 07B
- `build_peer_alignment` 迁出

### 5.5 Confidence（Branch 5）

**主模块**：[services/confidence_evaluator.py](services/confidence_evaluator.py)。

**辅助模块（数据准备）**：`contract_calibration_inputs.py` / `active_rule_pool*` /
`exclusion_reliability_review.py`（候选；归属待 16B-2）。

**为什么属于这里**：07C 契约最接近的活模块；read-only / 禁字段 / 无 mutation 全部合规。

**当前是否合规**：

- ✅ 边界（read-only / forbidden_fields / 无 mutation / 无 LLM / 无 DB）
- ❌ `_compute_agreement` key 与 main_projection / exclusion 输出不对齐
  → `agreement_status` 长期 `unknown`
- ❌ `calibration_context` 在 home_terminal / V2 路径**均未传**
  → confidence level 长期 `unknown`
- ❌ UI 主面板未读 `confidence_result`（仍读 `final_confidence` 旧字段）

**需要修什么**（16C）：

- key 对齐：`_compute_agreement` 改读 `predicted_top1.state` /
  `triggered_rule`（用 `excluded_state_from_result` 已有的映射）
- 在 home_terminal / V2 调用处补传最小 `calibration_context`
- 16E：UI 切到 confidence_result（属 Bridge 退出条件 #1）

### 5.6 Final Report（Branch 6）

**主模块**：[services/final_decision.py](services/final_decision.py)
（07D 最接近的活模块；strict passthrough 已实现）。

**外部 schema validator**：[services/projection_output_contract.py](services/projection_output_contract.py)。

**渲染 / 摘要**：projection_three_systems_renderer / projection_narrative_renderer /
predict_summary / ai_summary（default-disabled）/ projection_v2_renderer（UI）。

**持久化**：log_store / projection_record_store / prediction_store（持久化层
跨 Branch 6 出口与 Branch 7 输入）。

**为什么属于这里**：07D 契约的展示者；不重新预测、不修改三系统。

**当前是否合规**：

- ✅ `final_decision.py` strict passthrough 已合规
- ❌ Branch 6 当前**没有唯一的 schema 出口**：
  - `final_decision.py` 输出一种 shape
  - `projection_chain_contract.build_unified_projection_payload` 输出另一种 shape
  - `projection_output_contract.py` 的 8 段是第三种 shape（且无原生产出者）
- ❌ `consistency_layer` 与 confidence_evaluator 的 agreement 职责重叠

**需要修什么**（16C）：

- 选定唯一的 final report schema（推荐：07D §9 草案为内部，
  `projection_output_contract` 8 段为外部对接）
- 决定 `consistency_layer` 是合并到 confidence_evaluator 还是保留为
  final_report 输入

### 5.7 Review & Learning（Branch 7）

**模块组**（基本完整，且边界已 11D / 12E 加固）：

- outcome_capture / review_orchestrator / review_center / review_analyzer /
  review_classifier / review_comparator / review_agent / review_store
- memory_store / memory_feedback / projection_memory_briefing /
  pre_prediction_briefing / projection_review_closed_loop
- rule_lifecycle / rule_scoring（待 16B-2 与 promotion 命名隔离）

**当前是否合规**：

- ✅ 整体结构清晰；prediction snapshot → outcome capture → review →
  memory / lesson → pre-prediction briefing 闭环
- ❌ `pre_prediction_briefing` 仍参与 `predict.py:1357 _apply_briefing_caution` 修改
  `final_confidence`（Bridge 旧行为，非 Branch 7 本身违规）

**需要修什么**（16E）：

- 把 caution 移到 Final Report Layer 标注，**不** mutate confidence
- rule_lifecycle / rule_scoring 与 promotion 三模块的命名空间隔离

### 5.8 Evaluation（Branch 8）

**模块组**：

- historical_replay_training / three_system_replay_audit /
  replay_record_wiring / replay_validation_record_adapter
- contract_replay_planner / contract_replay_writer / contract_outcome_correlation
- regime_diagnostics_dashboard / regime_validation_helper / stats_engine
- avgo_1000day_training / daily_training_pipeline / daily_training_summary
- root entrypoint：`run_pipeline.py` / `run_1000day.py` / `stats_reporter.py` / `research.py`
- scripts/ 中 25+ evaluation / replay / dashboard 脚本

**当前是否合规**：

- ❌ `contract_replay_writer.py` **直接调** `predict.run_predict`
  ([:83](services/contract_replay_writer.py:83)、[:475](services/contract_replay_writer.py:475))
  —— 评估管道仍消费 Bridge schema
- ❌ 历史 evaluation 输出散落在 `logs/historical_training/` 多目录；
  统一存储位置 / schema 待 16C / 16D

**需要修什么**（16E）：

- 触发 Bridge 退出条件 #2：replay 切到新 evaluation schema
- 16C：统一 evaluation 输出存储 / schema

### 5.9 UI / Presentation（Branch 9）

**模块组**：app.py + ui/ 全部 + projection_three_systems_renderer /
projection_narrative_renderer / projection_v2_renderer 的 render 部分。

**当前是否合规**：

- ❌ `ui/predict_tab.py:1410` 仍直调 `predict.run_predict`，主面板仍读
  `final_bias` / `final_confidence` / `primary_projection` / `final_projection`
- ✅ 其它 ui/ 模块已通过 12E 加固，主要走 prediction_store / review_*

**需要修什么**（16E）：

- `ui/predict_tab.py` 切到新 final_report schema（Bridge 退出条件 #1）
- hard rule 3：app.py 不进新业务逻辑

---

## 6. TEMP_MIGRATION_BRIDGE 摘要

**模块**（与 §4.1.10 一致）：

- `predict.py`（`run_predict` legacy wrapper + 旧 `build_primary_projection` /
  `apply_peer_adjustment` / `build_final_projection` / `_apply_briefing_caution` /
  `_apply_v2_legacy_adapter_overlay`）
- `services/predict_legacy_adapter.py`
- `services/predict_legacy_v2_bridge.py`
- legacy `PredictResult` 字段：`final_bias` / `final_confidence` /
  `confidence` / `primary_projection` / `peer_adjustment` /
  `final_projection` / `path_risk` / `peer_path_risk_adjustment`

**1.0 重申**：

- 这些**不是**正式架构。
- 只能迁移期存在。
- **不能扩大**依赖（任何新代码不允许读 / 写这些模块的字段）。
- 退出条件沿用 1.0 §10 的 6 项（与 16A §14 一致）：
  1. UI 全部读新 final_report schema
  2. replay 全部读新 evaluation schema
  3. tests 不再依赖旧 `PredictResult`
  4. `run_predict` 不再作为主入口
  5. legacy adapter / bridge 在 active path 中无 import
  6. `services/projection_orchestrator.py` 不再被新链路依赖

**当前进度**：

| 退出条件 | 当前状态 |
|---|---|
| #1 UI 切新 schema | ❌ `ui/predict_tab.py:1410` 仍直调 `run_predict` |
| #2 replay 切新 schema | ❌ `services/contract_replay_writer.py` 仍调 `run_predict` |
| #3 tests 不依赖旧 PredictResult | ⚠️ 多份 boundary tests（X1..X5）仍依赖 PredictResult 字段做合约校验；属设计内（保护 Bridge） |
| #4 `run_predict` 不再作为主入口 | ❌ 仍是 UI 主入口 + replay 入口 + scripts/run_e2e_loop |
| #5 legacy adapter / bridge 无 active import | ⚠️ `services/predict_legacy_v2_bridge.py` 当前已无 active import；`services/predict_legacy_adapter.py` 仍被 `predict.py:44` import |
| #6 `services/projection_orchestrator.py` 不再被新链依赖 | ❌ 仍被 `services/projection_orchestrator_v2.py:16` import |

→ Bridge 退出条件 0/6 完全满足；可独立先解散的是 `services/predict_legacy_v2_bridge.py`（无 active import）。

---

## 7. LEGACY_ACTIVE_DEPENDENCY 摘要

**模块**（与 §4.1.11 一致）：

| 模块 | 为什么现在不能删 | active caller | 退出 active path 需要先做什么 |
|---|---|---|---|
| `services/projection_orchestrator.py` | V2 链通过它**回调** `predict.run_predict` 拿 legacy `predict_result` | `services/projection_orchestrator_v2.py:16` `from services.projection_orchestrator import build_projection_orchestrator_result` | 16E：让 V2 不再回调 V1（直接构造 primary_analysis），同时 Bridge #6 解锁 |
| `services/projection_orchestrator_v2.py` | 是 V2 主链入口；`projection_entrypoint` / `projection_v2_adapter` / `historical_replay_training` / `save_projection_records_smoke.py` 都依赖 | 见 §4.1.11 | 16C：选定主入口（home_terminal vs V2 vs 新 orchestrator）；16E：拆掉 V1 回调，并把 standardized chain（exclusion + main_projection + consistency + confidence + final_decision）重组为 9 分支直连 |
| `services/projection_entrypoint.py` | 包装 V2 raw → projection_three_systems | 部分 services / scripts | 16C：主入口决定后随之迁移 |
| `services/projection_v2_adapter.py` | V2 adapter | 部分 services | 16E：随 Bridge 退出 |
| `services/home_terminal_orchestrator.py` | app.py 主页入口；当前 home 主链 | `app.py:86, 1899` | 16C：决定主入口；如果选它做未来主链，需要补 `calibration_context` / agreement key 对齐 |
| `services/projection_orchestrator_preflight.py` | V1 / V2 共用 preflight | 两个 orchestrator | 16D：合并审 |
| `services/primary_20day_analysis.py` / `services/peer_adjustment.py` / `services/historical_probability.py` | V2 链的 primary / peer / historical 步骤 | `projection_orchestrator_v2._build_*` | 16C：决定 V2 链是否拆为 9 分支直连，这些模块要么并入 main_projection_layer，要么作为 Branch 2 / Branch 3 的辅助 |
| `services/predict_summary.py` | V1 链的 summary 构造 | `services/projection_orchestrator.py:22` | 16E：随 Bridge 退出 |
| `services/ai_summary.py` | LLM-based summary（11F default-disabled） | UI / 链 | 16C：保留为 Branch 6 narrative 选项；不解禁 default |

> 这些模块**当前**不能删；删除前必须先满足 Bridge 退出条件 + 主入口决策（16C）+ refactor 计划（16E）。

---

## 8. KEEP_FROZEN_DIAGNOSTIC / ARCHIVE 摘要

**KEEP_FROZEN_DIAGNOSTIC**（与 §4.1.12 一致）：

- `services/continuous_smoothing_candidate.py` / `_v2.py`
- `scripts/run_continuous_smoothing_validation.py` / `_v2.py` /
  `run_real_continuous_smoothing_validation.py` / `_execute.py` / `_execute_v2.py`

**写明**：

> 这些**不**参与 active path（13 §5 / 15 §5 grep 已确认）。
> **不**优先删除。
> 有历史证据价值（postmortem 对比）。
> 后续如要删除必须**另开** archive / delete pass，且**必须**满足 06 §8 /
> 07B §11 / 07C §12 / 07D §12 / 1.0 §6.17 的"不复活作为 candidate"约束。

**ARCHIVE**（与 §4.1.13 一致）：

- `archive/legacy/root_stubs/_DEPRECATED.md` / `confidence_engine.py` /
  `contradiction_engine.py` / `risk_model.py`（14D quarantine 已完成）
- `records/03_replay_accuracy_and_exclusion_accuracy.md`（仅一个文件；候选
  Archive，需 16B-2 核实）

**tracked log evidence**（15 §6 已锁定保留）：

- `logs/historical_training/03_fresh_replay/`
- `logs/historical_training/exclusion_action_validation_2e/` 与 `_v2/`
- `logs/technical_features/...`

→ 全部保留作为已结案 evidence；不删；不重写；不进 active path。

---

## 9. UNKNOWN_REVIEW_REQUIRED 摘要

> 这些模块**暂时**无法完全归类，需 16B-2（Module Import Graph Deep Audit）
> 进一步审；暂时**不能**删。

| 模块 | 为什么 unclear | 下一步需要读哪些 callers |
|---|---|---|
| `services/projection_chain_contract.py` | 同时含 feature helper（属 Branch 2）与 unified payload assembler（属 Branch 6） | 全文件每个公共函数的所有 active caller |
| `services/projection_output_adapter.py` | 8 段 schema 翻译；docstring 写"not yet wired into run_predict"，但需确认实际是否 dormant | active import grep |
| `services/projection_output_contract.py` | 8 段 schema validator；对接外部 step_1a；当前无原生产出者 | 16C 决定 8 段是否成为外部对接版 |
| `services/active_rule_pool.py` / `_calibration` / `_drift` / `_export` / `_validation` | 与 promotion 三模块共享命名空间；归属可能跨 Branch 5 数据准备 / Branch 7 / Branch 8 | 全 active caller graph |
| `services/projection_three_systems_renderer.py` / `services/projection_narrative_renderer.py` / `ui/projection_v2_renderer.py` | 渲染器；可能介于 Branch 6（Final Report 内部 render）与 Branch 9（UI 展示）之间 | 与 final_decision / ai_summary 的 caller 关系 |
| `services/consistency_layer.py` | 与 confidence_evaluator agreement 职责重叠 | 决定合并 vs 并存 |
| `services/anti_false_exclusion_audit.py` / `services/anti_false_exclusion_dashboard.py` / `services/big_up_contradiction_card.py` / `services/big_down_tail_warning.py` | 反假排除 / 矛盾 / 尾部告警；可能是 Branch 4 内部诊断 / Branch 7 复盘 / Branch 9 UI | 每个的 active caller + 是否读 projection_result |
| `services/exclusion_reliability_review.py` | 否定可靠性 review；可能是 Branch 7 复盘 / Branch 5 confidence 数据准备 | 同上 |
| `services/primary_bias_diagnosis.py` | primary bias 诊断 | 是否进入决策路径 |
| `services/five_state_margin_policy.py` | 五状态边界判定 | 是否属 Branch 3 内部 |
| `services/peer_adjustment.py` | V2 链 peer 调整步骤；与"peer 是 Feature 输入"的 1.0 §8 要求不一致 | 决定 Feature vs Projection 内部 |
| `services/regime_diagnostics_dashboard.py` | 既有数据组装也有 dashboard 渲染 | 拆 dashboard 数据 vs 渲染 |
| `services/agent_parser.py` / `services/agent_schema.py` / `services/ai_intent_parser.py` / `services/ai_task_parser.py` / `services/automation_wrapper.py` / `services/tool_router.py` / `services/intent_planner.py` / `services/plan_normalizer.py` / `services/command_parser.py` / `services/openai_client.py` / `services/analysis_context.py` / `services/dashboard_view_model.py` / `services/multi_symbol_view.py` / `services/inspect_analysis.py` / `services/error_taxonomy.py` / `services/date_range_parser.py` / `services/evidence_trace.py` | command-bar / UI 工具 / 通用工具 | 是否属 Branch 9 / 工具层（不在 9 分支内但是工具子层）；1.0 未定义"工具层"作为正式分支 |
| `services/contract_payload_diff.py` / `_extras_dashboard.py` / `_inspector.py` / `_trend.py` | 8 段 schema 离线 dashboard | Branch 8 / Branch 9 |
| `services/cutoff_guard.py` | 11D guard | Branch 7 内部 vs 工具层 |
| `services/soft_metadata_injection.py` / `_simulator.py` | soft metadata（与 promotion 隔离） | 16B-2：与 promotion 的关系 |
| `services/query_executor.py` | UI / dashboard 查询 | 工具层 vs Branch 9 |
| `research.py`（root） | 顶层 research 入口 | 是否属 Branch 8 入口 / Bridge |
| `scripts/*` 25+ 评估 / replay / dashboard 脚本 | 大批量；按用途逐一站队 | 16B-2 |
| `records/03_replay_accuracy_and_exclusion_accuracy.md` | 仅 1 个文件；归 ARCHIVE 候选 | 16B-2 核实是否仍被引用 |

> **暂时不能删**：以上全部模块本轮**只**标 `UNKNOWN_REVIEW_REQUIRED`，
> **不**触发任何删除 / 移动。

---

## 10. 初步清场建议

> 仅作建议；**本轮不实施**。所有"删除 / 移动"留待 16D / 16E / 用户单独确认。

**A. 可保留并完善**（CORE_*，已基本合规或修一两点即可）：

- Branch 1：`data_fetcher.py` / `services/market_data_store.py` /
  `services/data_query.py` / `services/record_reader.py`
- Branch 2：`feature_builder.py` / `services/regime_features_builder.py` /
  `services/regime_labels_builder.py` / `services/state_label.py` /
  `services/real_regime_label_provider.py`
- Branch 3：`services/main_projection_layer.py`（修两个边界违规）
- Branch 4：`services/exclusion_layer.py`（迁出 `build_peer_alignment` +
  schema 对齐）
- Branch 5：`services/confidence_evaluator.py`（key 对齐 + 接 calibration）
- Branch 6：`services/final_decision.py`（schema 唯一化）
- Branch 7：`services/outcome_capture.py` / `review_*` / `memory_*` /
  `prediction_store` / `pre_prediction_briefing` / `projection_memory_briefing` /
  `projection_review_closed_loop`
- Branch 8：`historical_replay_training` / `three_system_replay_audit` /
  `replay_*` / `contract_outcome_correlation` / `regime_validation_helper` /
  `stats_engine` / `avgo_1000day_training` / `daily_training_*`
- Branch 9：`app.py` + `ui/*`（除 `predict_tab.py` 外 5.9 §需修）

**B. 必须先迁移 caller 的**（满足 Bridge 退出条件后才能动）：

- `predict.py` → 满足 #1+#2+#4 后降级为 stub
- `services/predict_legacy_adapter.py` → 满足 #5
- `services/projection_orchestrator.py` → 满足 #6
- `services/projection_orchestrator_v2.py` → 16C / 16E 主入口决策后重构
- `services/home_terminal_orchestrator.py` → 16C 主入口决策后重构
- `services/contract_replay_writer.py` → 满足 #2

**C. 可以未来 quarantine 的**：

- `services/predict_legacy_v2_bridge.py` → 当前无 active import；可作为
  Bridge 第一个独立解散候选（16D / 16E）

**D. 应该移出 repo 的 raw artifacts**（已 14K ignore，仅本地保留）：

- `avgo_agent.db.backup_*`（7 个）
- 4 套 untracked replay / regime validation 子目录
- `.claude/worktrees/`（26 个）

**E. 不允许现在删除**：

- 所有 `KEEP_FROZEN_DIAGNOSTIC`（continuous_smoothing v1 / v2 + 5 个 validation 脚本）
- 所有 `ARCHIVE`（archive/legacy/root_stubs/* + tracked log evidence）
- 所有 `LEGACY_ACTIVE_DEPENDENCY`（V1 / V2 orchestrator / home_terminal /
  primary_20day_analysis / peer_adjustment / historical_probability / preflight /
  predict_summary）
- 所有 `UNKNOWN_REVIEW_REQUIRED`（在 16B-2 完成前不动）
- 所有 `OFFLINE_ONLY`（promotion / protection_layer_diagnostics）

---

## 11. 对 16C 的输入

16C 重点解决"**Target Dataflow & Contract Decision**"，必须回答以下问题：

1. **哪个 orchestrator 是未来主入口？**
   候选：home_terminal_orchestrator / projection_orchestrator_v2 / 新建 unified orchestrator
   - 选定后，剩余两个进 LEGACY_ACTIVE_DEPENDENCY，等 Bridge 退出后解散
2. **final_report schema 是否成为唯一事实标准？**
   - 候选 A：07D §9 草案 `final_report_aggregator_result.v1`
   - 候选 B：`projection_output_contract` 8 段（外部对接）
   - 候选 C：A 为内部 + B 为外部对接（推荐）
3. **predict.py 如何降级为 bridge？**
   - 选项 A：保留 `run_predict` 接口，内部转发到新 orchestrator + adapter
   - 选项 B：彻底删除 `run_predict`，UI / replay / scripts 全切（高风险）
4. **UI 何时迁移到新 schema？**
   - Bridge 退出条件 #1：`ui/predict_tab.py:1410` 不再调 `run_predict`，
     改读 `final_report.projection_section / exclusion_section / confidence_section`
5. **evaluation 读取哪个 payload？**
   - 当前 `services/contract_replay_writer.py` 调 `run_predict` 拿 legacy
     PredictResult；16C 需决定 evaluation 是直接读 prediction_store
     还是经新 orchestrator
6. **`build_peer_alignment` 与 `consistency_layer` / `peer_adjustment` 如何归位？**
   - peer_alignment → Branch 2 Feature
   - consistency_layer → 与 confidence_evaluator.agreement_status 合并 vs 并存
   - peer_adjustment → 拆为 Feature 输入（peer 信号）+ Projection 内部步骤（如保留）
7. **15d 标准窗口何时迁移？**
   - 当前 20d 实现暂为 legacy；16C 决定迁移路径与时间窗
8. **统一 evaluation 输出存储位置 / schema**

---

## 12. 不允许事项

本轮严守：

- ❌ 不改代码
- ❌ 不删除模块
- ❌ 不移动模块
- ❌ 不跑 evaluation
- ❌ 不接 trading
- ❌ 不进入 3R-5 / 3R-6
- ❌ 不把 `TEMP_MIGRATION_BRIDGE` 当正式架构
- ❌ 不复活已 quarantine 的 v1 stubs
- ❌ 不复活 `continuous_smoothing*` 作为 active candidate
- ❌ 不解禁 promotion 三模块 / `protection_layer_diagnostics` 作为 active path
- ❌ 不默认迁移 `run_predict` 到 V2
- ❌ 不允许借 16B 顺手做代码改动（16F 才是第一个代码 PR）

---

## 13. 推荐下一步

**首选**：

> **Step 16C：Target Dataflow & Contract Decision**

理由：

- 16B Inventory 已经把模块层"骨架"摆出来；下一步必须回答
  §11 的 8 个 schema / 主入口 / 迁移路径问题
- 不回答 §11 就直接进 16D（隔离计划）会**站不住脚**：因为不知道
  谁是未来主链，"隔离哪些模块"无法决策

**备选**（仅当 16B-2 必要）：

> **Step 16B-2：Module Import Graph Deep Audit**

仅当下列任一情况触发：

- §9 `UNKNOWN_REVIEW_REQUIRED` 中至少 5 个模块影响主链路决策
- scripts/ 25+ 评估脚本中发现非预期 active import 反向回到 Bridge
- 用户希望先把所有 UNKNOWN 解掉再做 16C

> 默认推荐：**直接进 16C**；16B-2 留作可选。

**不推荐**：

- 不推荐借 16B 做代码改动（16F 才是第一个代码 PR）
- 不推荐借任一步解锁 3R-5 / 3R-6（1.0 §12 7 项前提必须全部满足）

---

## 14. 严守边界

本轮 Step 16B **只**写 inventory 文档：

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

唯一新增文件：[tasks/record_16b_module_standup_ownership_inventory.md](tasks/record_16b_module_standup_ownership_inventory.md)（本文件）。

后续修改路径：任何对 §4 总表 / §5 CORE 分组 / §6 Bridge 摘要 / §7
LEGACY 摘要 / §8 FROZEN/ARCHIVE 摘要 / §9 UNKNOWN 摘要 / §10 清场建议 /
§11 16C 输入 / §12 禁止事项 / §13 下一步的调整，都必须**显式更新本文件**；
同时检查是否需要同步更新 1.0 / 16A。
