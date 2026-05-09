# 17M记录：UI / Presentation Layer Rebuild Plan

> 本记录是 **Step 17M：UI / Presentation Layer 重建计划**——九分支按层
> 重建中的**第九层**（Branch 9），也是**最后一层 plan**。1.0 canonical /
> 16A blueprint / 16B inventory / 16C target dataflow & contract decision /
> 16D isolation & quarantine plan / 16E core chain refactor plan / 16F
> no-patching principle / 16G full module decomposition standup / 16H
> repository clearing decision table / 16I core chain rebuild execution
> plan / 17A PR-B standard payload skeleton / 17B PR-C peer_alignment
> 抽公共模块 / 17C PR-D main_projection 去 `exclusion_result` 形参 /
> 17D layer-by-layer rebuild governance / 17E Data Layer Rebuild Plan /
> 17F Feature Layer Rebuild Plan / 17G Projection Layer Rebuild Plan /
> 17H Exclusion Layer Rebuild Plan / 17I Confidence Layer Rebuild Plan /
> 17J Final Report Layer Rebuild Plan / 17K Review & Learning Layer
> Rebuild Plan / 17L Evaluation Layer Rebuild Plan 已全部入 main（main
> 最新 commit `ae6b3a8`）。
>
> 本轮**只**写计划文档：未改业务代码、未新增测试、未删除文件、未移动
> 文件、未修改 `.gitignore`、未处理 handoff、未处理 logs / DB backup /
> `.claude/worktrees/`、**未处理 `avgo_agent.db`**、未跑 replay /
> validation / historical evaluation、未写 DB / 未改 DB schema、未默认
> 迁移 `run_predict` 到 V2、未接 trading、未输出 buy / sell / hold /
> hard / forced / required、未进入 3R-5 / 3R-6、未启动任何代码 PR、
> 未直接迁 UI、未直接改 app.py / renderer / dashboard、未启动 bridge /
> orchestrator 实现任务、未做任何局部 patch、未 commit / 未 push。
>
> 唯一 deliverable：本文件。
>
> **本记录优先级**：与 17E ~ 17L 各层 Plan 同级；与 1.0 / 16A / 16C /
> 16D / 16F / 16I / 17D / 17E ~ 17L 协同。冲突仲裁路径与 1.0 §14 /
> 17D §13 一致：旧 records 若与 17M 在 UI Layer 范畴冲突，**以 17M 为准**。
>
> **17M 完成后，九分支按层重建计划全部完成**（详见 §18）。

---

## 1. Step 17M 目的

把九分支按层重建从 Evaluation Layer（17L）推进到**第九层（UI / Presentation
Layer）的具体重建计划**——也是**最后一层**。

**本轮只回答**：

- UI / Presentation Layer 当前长什么样（模块 inventory + active path）
- UI Layer 目标长什么样（保留 / 迁移 / 隔离 / 删除候选）
- UI Layer 与上下游的边界（Final Report / Review / Evaluation ↑（**只读**）；
  **不**回灌任一上游；**不**重算任一系统）
- legacy field（`final_bias` / `final_confidence` / ...）→ standard payload
  字段映射规则
- **Tab 迁移顺序**（低风险先 → 主入口 last；与 1.0 §13 hard rule 3 协同）
- presentation_payload / view_model 标准化规则
- UI 与 Orchestrator / Evaluation Dashboard / Review 的边界
- UI Layer 后续可能的代码 PR 候选（**不**执行）
- 九分支按层重建完成后的整体状态
- 推荐下一步（**Step 18A：First Layer-Based Implementation Batch Selection**）

**本轮不回答**：

- 不开任何代码 PR（最早 18A）
- 不动 `avgo_agent.db`、`.gitignore`、handoff、logs / DB backup /
  worktrees
- 不直接迁 UI（与 17D §10.2 一致）
- 不直接改 app.py / renderer / dashboard（与 1.0 §13 hard rule 3 一致）
- 不启动 bridge / orchestrator 实现任务（与 17D §10 一致）
- 不直接执行 18A 第一批实现 PR（用户单独审批）

**本文件性质**：layer rebuild plan（按层计划），不是 design 也不是 impl。

### 1.1 本轮校正：`services/contract_payload_dashboard.py` 命名说明

> **校正**：用户请求中提及 `services/contract_payload_dashboard.py`——
> 该文件**不存在**于当前 repo。实际存在的相关 dashboard 模块是：
>
> - `services/contract_payload_inspector.py`
> - `services/contract_payload_diff.py`
> - `services/contract_payload_trend.py`
> - `services/contract_payload_extras_dashboard.py`
> - `services/regime_diagnostics_dashboard.py`
> - `services/anti_false_exclusion_dashboard.py`
>
> 17M 按**实际存在**的模块做 inventory；命名差异在 §5 / §7 各处显式说明。
> 与 17H §1.1 / 16F 原则一致。

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
| 17J Final Report Layer Rebuild Plan | ✅ commit `912cc27` |
| 17K Review & Learning Layer Rebuild Plan | ✅ commit `d0057c5` |
| 17L Evaluation Layer Rebuild Plan | ✅ commit `ae6b3a8` |
| main 最新 commit | `ae6b3a8` |
| worktree 唯一 deliberate untracked | `.claude/handoffs/task_089_post_pr_cleanup.md` |
| 战略阶段 | 从 Evaluation Layer plan（17L）→ **UI Layer plan（17M 本轮，最后一层）** |
| 3R-5 / 3R-6 | ❌ 仍然不允许进入 |
| 第一个按层实现 PR（18A）| ❌ 仍未；17M 完成后才能讨论 |
| Bridge #1 退出条件（UI 全部读新 final_report schema）| ❌ 未满足；归 17M PR-UI-* 阶段（与 1.0 §10 / 16I §11 一致） |

**17D §6 PR 准入规则提醒**：

- 任何代码 PR 必须绑定九分支某一层 + 引用对应层 Plan §
- 17M 入 main 后，UI Layer 范畴的 PR 才**有资格**被讨论
- 17M 本身**不**自动批准任何 PR；PR-UI-* 仍需 18A 单独审批

**层间依赖**：

- 17M 依赖 17F / 17G / 17H / 17I / 17J / 17K / 17L（已就位）
- 17M 是九分支最后一层；不依赖任何其他层 plan
- 17M 入 main 后，九分支按层重建计划**全部完成**；进入 18A 阶段（详见
  §18 / §19）

---

## 3. UI / Presentation Layer 职责定义

**UI / Presentation Layer（Branch 9）只回答一件事**：

> **"展示**（不重算 / 不推演 / 不否定 / 不做 confidence / 不跑 replay）。
> 把 standard_projection_payload.v1 / final_report / review_result /
> evaluation_result 渲染给用户。"**

### 3.1 只做的事（与 1.0 §8 Branch 9 / §13 hard rule 3 一致）

- 展示 `standard_projection_payload.v1`（未来由 architecture_orchestrator
  组装；当前 V2 unified payload / legacy `PredictResult` 并存）
- 展示 `final_report`（来自 Branch 6，**只读**）
- 展示 `projection_section` / `exclusion_section` / `confidence_section`
  三段并列
- 展示 `agreement_or_conflict_section`（一致 / 冲突标注）
- 展示 `combined_user_summary` / `key_points` / `risks`
- 展示 `warning_cards`（来自 17J PR-FINAL-4 schema；含 big_up_contradiction /
  big_down_tail_warning / soft_metadata / anti_false_exclusion 等）
- 展示 review record / lesson / pre_prediction_briefing（来自 Branch 7）
- 展示 evaluation summary / dashboard data（来自 Branch 8）
- 收集用户输入（target_date / symbol / scan_phase / research notes）
- 调用上游 service / orchestrator 获取结果
- 浏览器渲染：复制 / 展开 / 表格 / 图形 / tab 布局
- 做**轻量字段映射 / display formatting**（如 bias / confidence 中文化），
  但**不能**重算业务结果
- legacy fallback：当 standard schema 缺失时**显式标注** compatibility
  mode

### 3.2 不做的事（与 1.0 §8 Branch 9 / §13 hard rule 3 一致）

- ❌ **不**生成 `feature_payload`（归 Branch 2 Feature Layer）
- ❌ **不**生成 `projection_result`（归 Branch 3 Projection Layer）
- ❌ **不**生成 `exclusion_result`（归 Branch 4 Exclusion Layer）
- ❌ **不**生成 `confidence_result`（归 Branch 5 Confidence Layer）
- ❌ **不**生成 `final_report`（归 Branch 6 Final Report Layer）
- ❌ **不**重新预测、不重算 confidence、不改 final_report、不根据展示
  需要改字段含义（与 1.0 §8 Branch 9 一致）
- ❌ **不**运行 review（review_orchestrator 由 service-layer 主入口；UI 是
  caller，不是 owner）
- ❌ **不**运行 evaluation / replay（与 17L §16.3 一致）
- ❌ **不**写 DB schema / 不改 DB schema
- ❌ **不**修改 system 输出（任一上游 payload）
- ❌ **不**调 broker / trading API
- ❌ **不**输出 buy / sell / hold / hard / forced / required
- ❌ **不**让 renderer 成为业务逻辑来源
- ❌ **不**在字段缺失时自己编造（必须显式标注 compatibility / missing）

### 3.3 输入 / 输出（白名单）

**输入**（与 07D §3.1 / 1.0 §8 Branch 9 一致）：

- `final_report`（来自 Branch 6，**只读**）
- `review_record` / `lesson` / `pre_prediction_briefing`（来自 Branch 7，
  只读）
- `evaluation_result` / dashboard-ready data（来自 Branch 8，只读）
- 用户输入（target_date / symbol / scan_phase / research notes / button
  click）
- legacy `PredictResult`（兼容期；最终随 Bridge 退出条件满足而消失）

**输出**：

- 浏览器渲染（Streamlit / HTML / Markdown）
- `presentation_payload` / `view_model`（17M 提案；详见 §13）

**禁止输入**（与 1.0 §9 / 1.0 §13 hard rule 3 一致）：

- ❌ Future outcome（任何路径）
- ❌ Trading 输入 / broker / position state
- ❌ 在 UI 内部重新 fetch yfinance（必须通过 Data Layer service）

---

## 4. UI / Presentation Layer 禁止事项

UI Layer **永久禁止**输出 / 引入以下任一：

| 类别 | 禁止项 | 锚点 |
|---|---|---|
| 在 UI 中重新计算 | UI 模块 import main_projection / exclusion_layer / confidence_evaluator / final_decision **并**调用其计算函数（**调** orchestrator / service 入口是允许的；**调** sub-layer 子函数重算是禁止的） | 1.0 §8 Branch 9 / §13 hard rule 3 |
| 在 UI 中重新跑 replay / holdout / calibration | UI 直接调 `historical_replay_training` / `regime_validation_helper` / `active_rule_pool_calibration` 跑批量 | 17L §16.3 |
| 在 UI 中改写 backend payload | UI 修改 final_report / projection_result / exclusion_result / confidence_result / review_record / evaluation_result 任一字段 | 07D §11 / 17J §4 / 17K §4 |
| 在 UI 中直接读 DB schema 绕过 service | UI 直接 `sqlite3.connect(avgo_agent.db)` 跑 SQL | 1.0 §13 hard rule 3 |
| legacy field 作长期主字段 | `final_bias` / `final_confidence` / `primary_projection` / `peer_adjustment` / `final_projection` / `path_risk` / `peer_path_risk_adjustment` 长期作为 UI 主面板字段而不迁 | 1.0 §6.3 / Bridge 退出条件 #1（与 1.0 §10 / 16I §11 一致） |
| 隐藏 schema mismatch | 当 standard schema 缺失时静默 fallback 到 legacy 而不显式标注 compatibility mode | 17M §8 |
| 接 trading / broker API | broker / order / position / trade routing | 1.0 §6.1 / §13 hard rule 1 |
| 输出交易动作 | `buy` / `sell` / `hold` / `simulated_trade` / `trading_action` / `no_trade` | 12E X1..X5 / 1.0 §6 |
| 输出强制语义 | `hard_*` / `forced_*` / `required_*` / `_PROTECTION_LAYER_CONNECTED` / `production_promotion` | 12E X1..X5 / 1.0 §6 |
| renderer 作业务逻辑来源 | UI renderer 内含派生计算（如重算 ret / pos / state probability） | 1.0 §13 hard rule 3 |
| LLM 默认开启 | UI 默认调 ai_summary 生成新解释；必须 `enable_ai_summary=False` | 1.0 §13 hard rule 1 / 5 / 17J §6.6 / 当前 ai_summary 实现 |
| LLM 新判断 | UI renderer 调 LLM 生成新预测 / trading suggestion | 07D §6 / 17J §6.6 |
| Future outcome 进 UI | UI 在 prediction 完成前展示 future outcome | 1.0 §9 / 17K §3.2 |
| 修改 `.gitignore` / DB schema | UI 触发 `.gitignore` 更新 / sqlite migration | 17E §11 ~ 17L §18 / 17M §11 |
| 复活 OFFLINE_ONLY promotion | UI 接 `services/active_rule_pool_promotion.py` | 1.0 §6.5 / 17K §17.3 |
| 在 app.py 加业务逻辑 | app.py 含 prediction / exclusion / confidence 业务计算 | 1.0 §13 hard rule 3（"app.py 只允许最小改动"） |

---

## 5. 当前 UI Layer 模块 inventory

> **范围说明**：本表覆盖 (1) **App entry**：`app.py` (2) **Tab modules**：
> ui/{home, predict, history, review, research, scan, inspect, control}_tab.py
> (3) **UI renderer**：ui/{projection_v2, big_up_contradiction_card,
> anti_false_exclusion_display, exclusion_reliability_review,
> protection_layer_diagnostics, soft_metadata}_renderer / display 等
> (4) **UI infra**：ui/{command_bar, labels, soft_metadata_baseline_cache}
> (5) **Service-side renderer / narrative helpers**（17J §17.2 已声明；
> 但属 UI rendering 服务）：services/{projection_narrative_renderer,
> projection_three_systems_renderer, predict_summary, ai_summary} (6)
> **Service-side dashboard data layer**（17L §17.1 已声明；UI 渲染部分
> 归 17M）：services/{contract_payload_inspector, _diff, _trend,
> _extras_dashboard, regime_diagnostics_dashboard,
> anti_false_exclusion_dashboard}。standard payload skeleton（17A PR-B）
> 属 INFRA / SCHEMA。

### 5.1 App entry & Tab modules inventory

| module_path | current_role | current_status | target_role | keep / migrate / quarantine / delete | active_callers | risk | next_action |
|---|---|---|---|---|---|---|---|
| `app.py` | Streamlit entry；含 cwd setup / matplotlib font / 1543 行 set_page_config / tabs 调用；import 7 个 ui/_tab + scanner + matcher + predict + run_scan + home_terminal_orchestrator | KEEP_ACTIVE；1.0 §13 hard rule 3 锁 "app.py 只允许最小改动" | **CORE_UI_APP_ENTRY**：Branch 9 主入口；最终业务逻辑全部移到 ui/ tabs | KEEP；不改；§15 PR-UI-8 stabilization | manual run；tests | **H** | §6.1；§9 last to migrate |
| `ui/predict_tab.py` | **主面板**；调 `run_predict` + `run_review_for_prediction` + `generate_review` + `capture_outcome` + 大量 contradiction / soft_metadata / anti_false_exclusion / protection_layer renderer；当前 read legacy `final_bias` / `final_confidence` / `primary_projection` / `final_projection`（line 273 / 274 / 281 / 283 / 300 / 301 / 371 / 373 / 380 / 386）| KEEP_ACTIVE；**Bridge #1 退出条件 #1 主对象** | **CORE_UI_TAB**：主预测 tab；最终读 standard `final_report` schema | KEEP；§9 last to migrate；§15 PR-UI-7 compatibility fallback explicit | app.py | **H** | §6.2；§9 |
| `ui/home_tab.py` | 主页 tab；调 `home_terminal_orchestrator` 间接路径；展示 home_payload | KEEP_ACTIVE | **CORE_UI_TAB**：home page | KEEP；§9 mid-migration | app.py | M | §6.3；§9 |
| `ui/history_tab.py` | 历史 tab；只读 prediction_store；调 services.prediction_store | KEEP_ACTIVE | **CORE_UI_TAB**：read-only 历史展示 | KEEP；§9 early-migration | app.py | L | §6.4；§9 |
| `ui/review_tab.py` | 复盘中心；展示 review_result / lesson；与 17K Review Layer 对接 | KEEP_ACTIVE | **CORE_UI_TAB**：review display | KEEP；§9 early-migration | app.py | L | §6.5；§9；与 17K §16.4 协同 |
| `ui/research_tab.py` | 研究 tab；调 `research.run_research`；render research result | KEEP_ACTIVE | **CORE_UI_TAB**：research display | KEEP；§9 early-migration | app.py | L | §6.6；§9 |
| `ui/scan_tab.py` | 扫描 tab；render scan_result（来自 scanner.run_scan） | KEEP_ACTIVE | **CORE_UI_TAB**：scan display | KEEP；§9 early-migration | app.py | L | §6.7；§9 |
| `ui/inspect_tab.py` | 查验分析 tab；调 services/inspect_analysis（16G UNKNOWN 之一）；展示 schema / payload | KEEP_ACTIVE | **CORE_UI_TAB**：inspect / payload validation display | KEEP；§9 **first to migrate**（最适合先做 standard payload display） | app.py | L | §6.8；§9 |
| `ui/control_tab.py` | command bar / agent command / query executor 触发 tab | KEEP_ACTIVE | **CORE_UI_TAB**：control / command | KEEP；§9 mid-migration | app.py | L | §6.9 |

### 5.2 UI renderer / infra inventory

| module_path | current_role | current_status | target_role | keep / migrate / quarantine / delete | active_callers | risk | next_action |
|---|---|---|---|---|---|---|---|
| `ui/projection_v2_renderer.py` | UI renderer for V2 projection raw payload；纯 Python helper（未直接 import streamlit） | KEEP_ACTIVE；17J §17.4 / 17L §17.1 已声明归 Branch 9 | **CORE_UI_RENDERER**：V2 raw → Streamlit-ready view | KEEP；§9 mid-migration | predict_tab；tests | M | §6.10 |
| `ui/big_up_contradiction_card.py` | Task 090：streamlit renderer；docstring 显式 "Pure presentation layer. No business logic. No payload mutation"；调 `services.big_up_contradiction_card.build_contradiction_card`（17J §17.4 / 17K §6.6）| KEEP_ACTIVE | **CORE_UI_RENDERER**：warning card | KEEP；§15 PR-UI-6 协同 | predict_tab；tests | L | §6.11 |
| `ui/anti_false_exclusion_display.py` | Step 2G-7A：read-only sidecar diagnostic；docstring "pure function: never reads DB / CSV / network" | KEEP_ACTIVE | **CORE_UI_RENDERER**：anti-false-exclusion sidecar | KEEP；§15 PR-UI-6 协同 | predict_tab；tests | L | §6.12 |
| `ui/exclusion_reliability_review.py` | streamlit renderer；调 `services.exclusion_reliability_review`（17K §17.1 已声明 → Branch 7 Review）| KEEP_ACTIVE | **CORE_UI_RENDERER**：reliability review display | KEEP；与 17K §6.6 协同 | predict_tab；tests | L | §6.13 |
| `ui/protection_layer_diagnostics_renderer.py` | Step 2G-8A.2：pure-function pair；turns `protection_layer_diagnostics.v1` dict → card_data + safe markdown；docstring 显式 read-only | KEEP_ACTIVE | **CORE_UI_RENDERER**：protection layer diagnostics display | KEEP | predict_tab；tests | L | §6.14 |
| `ui/soft_metadata_renderer.py` | Step 2G-6A：pure-function renderer for soft_metadata.v1；输出 dashboard 安全 display model | KEEP_ACTIVE | **CORE_UI_RENDERER**：soft_metadata display | KEEP | predict_tab；tests | L | §6.15 |
| `ui/soft_metadata_baseline_cache.py` | Step 2G-6B.6：session_state baseline cache；lazy-build soft_metadata_baseline once per session | KEEP_ACTIVE | **CORE_UI_INFRA**：session cache | KEEP；不动 | predict_tab；tests | L | §6.16 |
| `ui/command_bar.py` | command bar 渲染器；含 streamlit `try/except ModuleNotFoundError` 软依赖 | KEEP_ACTIVE | **CORE_UI_INFRA**：command bar | KEEP | app.py；tests | L | §6.17 |
| `ui/labels.py` | UI tab labels（中文）：TAB_SCAN / TAB_RESEARCH / TAB_PREDICT / TAB_HISTORY / etc. | KEEP_ACTIVE | **CORE_UI_INFRA**：label constants | KEEP；不动 | app.py；tabs | L | §6.18 |

### 5.3 Service-side renderer / narrative inventory（17J §17.2 已声明归 Branch 6；UI 渲染部分由 17M 协同）

| module_path | current_role | current_status | target_role | UI 渲染归属 | active_callers | risk | next_action |
|---|---|---|---|---|---|---|---|
| `services/projection_narrative_renderer.py` | render V2 raw → 中文 trading narrative；docstring "fixed Chinese trading narrative" | KEEP_ACTIVE；17J §17.2 已声明归 Branch 6 narrative helper；不调 streamlit；不做 layout | **FINAL_REPORT_RENDERER**（17J）；UI consume；不属 17M 主路径 | UI consume only | projection_entrypoint / tests | L | §7.1 |
| `services/projection_three_systems_renderer.py` | reshape V2 raw → 三系统视图；docstring "no scanning, prediction, or rule mutation" | KEEP_ACTIVE；17J §17.2 | **FINAL_REPORT_RENDERER**（17J）| UI consume only | projection_entrypoint / predict.py / replay_record_wiring / tests | L | §7.2 |
| `services/predict_summary.py` | readable Chinese summary helpers | KEEP_ACTIVE；17J §17.2 / 17K §6.6 协同 | **FINAL_REPORT_NARRATIVE_HELPER**（17J）| UI consume only | predict.py / V1 chain / evidence_trace / tests | L | §7.3 |
| `services/ai_summary.py` | optional LLM source-attributed explanation；默认 `enable_ai_summary=False` | KEEP_ACTIVE；17J §17.2 / §6.6 严格锁 | **FINAL_REPORT_NARRATIVE_HELPER**（OPT-IN ONLY）| UI consume only；保持 opt-in | predict.py / V2 chain / tests | M | §7.4；与 1.0 §13 hard rule 1 / 5 一致 |

### 5.4 Service-side dashboard data layer（17L §17.1 已声明归 Branch 8；UI 渲染归 17M）

| module_path | current_role | current_status | target_role | UI 渲染归属 | active_callers | risk | next_action |
|---|---|---|---|---|---|---|---|
| `services/contract_payload_inspector.py` | read-only contract inspection | KEEP_ACTIVE；17L §6.2 | **CORE_EVALUATION**（17L）| UI consume；§15 PR-UI-2 inspect tab 渲染 | scripts / tests | L | §7.5 |
| `services/contract_payload_diff.py` | read-only diff | KEEP_ACTIVE；17L §6.3 | **CORE_EVALUATION**（17L） | UI consume；§15 PR-UI-2 inspect tab | scripts / tests | L | §7.6 |
| `services/contract_payload_trend.py` | read-only trend | KEEP_ACTIVE；17L §6.4 | **CORE_EVALUATION**（17L） | UI consume；§15 PR-UI-2 inspect tab | scripts / tests | L | §7.7 |
| `services/contract_payload_extras_dashboard.py` | read-only extras dashboard | KEEP_ACTIVE；17L §6.5 | **CORE_EVALUATION**（17L） | UI consume；§15 PR-UI-5 evaluation dashboard | scripts / tests | L | §7.8 |
| `services/regime_diagnostics_dashboard.py` | regime diagnostic dashboard 数据层 | KEEP_ACTIVE；17L §6.11 | **CORE_EVALUATION**（17L） | UI consume；§15 PR-UI-5 | scripts / tests | M | §7.9 |
| `services/anti_false_exclusion_dashboard.py` | aggregate dashboard；6-gate；docstring read-only | KEEP_ACTIVE；17L §6.13 | **CORE_EVALUATION**（17L） | UI consume；§15 PR-UI-5 | scripts / tests | M | §7.10 |

### 5.5 关键说明

- **UI Layer 是九分支 plan 中最碎的层之一**：`app.py` + 8 个 ui/_tab.py +
  9 个 ui/ renderer/infra 模块 + 4 个 service-side narrative + 6 个
  service-side dashboard data = **28 个 UI-related 模块**
- **`app.py` 受 1.0 §13 hard rule 3 严格保护**："app.py 只允许最小改动"；
  17M 不改；§15 PR-UI-8 仅 stabilization
- **`ui/predict_tab.py` 是 Bridge #1 退出条件 #1 的主对象**：当前 read legacy
  `final_bias` / `final_confidence` / `primary_projection` / `final_projection`
  字段（5 处 line 273-386）；UI 全部读新 final_report schema 才满足 Bridge
  退出条件 #1（与 1.0 §10 / 16I §11 一致）
- **大部分 ui/ renderer 已经是 pure presentation**：docstring 严锁
  "no business logic / no payload mutation / pure function / never reads
  DB / CSV / network"；这是好事；§14 测试维护现状
- **service-side renderer / narrative 4 模块**（projection_narrative_renderer /
  three_systems / predict_summary / ai_summary）属 Branch 6 Final Report
  narrative helper（17J §17.2）；UI 只 consume；**不**重写
- **service-side dashboard data 6 模块**属 Branch 8 Evaluation（17L §17.1）；
  UI 只 consume；**不**重算
- **DELETE_NOW 集合为空**（与 16H §13 / 17E §15.7 ~ 17L §17.9 一致）

---

## 6. CORE_UI 保留模块

> UI Layer 的**核心保留模块**：分 4 类（app entry / tabs / renderers /
> infra）共 18 项。

### 6.1 `app.py`（CORE_UI_APP_ENTRY）

| 维度 | 说明 |
|---|---|
| 为什么保留 | Streamlit entry；唯一主入口；含 cwd setup / matplotlib font / set_page_config / tabs 调用；1.0 §13 hard rule 3 锁"只允许最小改动" |
| 目标职责 | (1) Streamlit 启动 + page config (2) tabs shell：组装 home / scan / research / predict / history / review / inspect / control 等 8 个 tab (3) 调用上游 service 拿 home_payload / scan_result 等；**不**做业务计算 |
| 是否需要改名 / 拆分 | ❌ 17M 不改；不拆分；保持 1.0 §13 hard rule 3 |
| 是否有跨层问题 | ⚠️ app.py 当前 import scanner / matcher / predict / run_scan / home_terminal_orchestrator——属于 caller 路径；不属业务 mutation |
| 后续实现任务 | §15 PR-UI-8 stabilization：仅 docstring marker；不动 logic |
| 当前禁止动作 | 不在 app.py 加业务逻辑；不引入 trading；不接 broker；不绕过 service |

### 6.2 `ui/predict_tab.py`（CORE_UI_TAB；最大改动面）

| 维度 | 说明 |
|---|---|
| 为什么保留 | 主面板；唯一 prediction caller / review trigger / outcome capture 入口；与 17K Review Layer / 17J Final Report Layer 紧耦合 |
| 目标职责 | (1) 收集用户输入（target_date / scan_phase）(2) 调用 `run_predict` 或未来 `architecture_orchestrator` (3) 调用 review_orchestrator / outcome_capture (4) 渲染 final_report / projection / exclusion / confidence 三系统 (5) 渲染 warning_cards / soft_metadata / anti_false_exclusion / protection_layer (6) **read 新 standard schema 优先 + legacy fallback** |
| 是否需要改名 / 拆分 | ❌ 17M 不改名；可在 18A+ 阶段考虑拆分（detail panel / summary panel / warning panel） |
| 是否有跨层问题 | ⚠️ 当前 5 处 read legacy `final_bias` / `final_confidence` / `primary_projection` / `final_projection`（5.1 表说明）；这是 Bridge #1 退出条件 #1 待办；归 §15 PR-UI-7 |
| 后续实现任务 | §15 PR-UI-7 compatibility fallback explicit；最后才迁（§9 §9.2 顺序 7）|
| 当前禁止动作 | 不在 predict_tab 重新计算 confidence / projection；不绕过 final_decision；不接 trading |

### 6.3 `ui/home_tab.py`（CORE_UI_TAB）

| 维度 | 说明 |
|---|---|
| 为什么保留 | 主页 tab；调 `home_terminal_orchestrator` 间接路径；展示 home_payload |
| 目标职责 | 入口卡片 / summary view |
| 后续实现任务 | §9 §9.2 顺序 6（mid-migration） |

### 6.4 `ui/history_tab.py`（CORE_UI_TAB）

| 维度 | 说明 |
|---|---|
| 为什么保留 | 历史 tab；只读 prediction_store；不影响当次推演 |
| 目标职责 | 历史 prediction record 展示 |
| 后续实现任务 | §9 §9.2 顺序 2（early-migration；只读历史风险低） |

### 6.5 `ui/review_tab.py`（CORE_UI_TAB）

| 维度 | 说明 |
|---|---|
| 为什么保留 | 复盘中心；展示 review_result / lesson；与 17K Review Layer 对接 |
| 目标职责 | 复盘记录 / 命中率 / 错误分布 / 最近复盘 4 区展示 |
| 后续实现任务 | §9 §9.2 顺序 3；与 17K §16.4 协同 |

### 6.6 `ui/research_tab.py`（CORE_UI_TAB）

| 维度 | 说明 |
|---|---|
| 为什么保留 | 研究 tab；调 `research.run_research`；render research result |
| 目标职责 | research 辅助信息展示 |
| 后续实现任务 | §9 §9.2 顺序 4 |

### 6.7 `ui/scan_tab.py`（CORE_UI_TAB）

| 维度 | 说明 |
|---|---|
| 为什么保留 | 扫描 tab；render scan_result |
| 目标职责 | scan 信号展示 |
| 后续实现任务 | §9 §9.2 顺序 5 |

### 6.8 `ui/inspect_tab.py`（CORE_UI_TAB；first to migrate）

| 维度 | 说明 |
|---|---|
| 为什么保留 | 查验分析 tab；调 services/inspect_analysis（16G UNKNOWN）；展示 schema / payload；最适合做 standard payload display 试点 |
| 目标职责 | (1) 展示当前 contract payload（来自 contract_payload_inspector） (2) 展示 trend / diff / extras_dashboard (3) 验证 schema_version / missing sections / compatibility_mode |
| 是否有跨层问题 | ⚠️ services/inspect_analysis 是 16G UNKNOWN（DEEP_AUDIT_REQUIRED）；§15 PR-UI-2 inspect tab standard payload display 推荐做 deep audit |
| 后续实现任务 | §9 §9.2 顺序 1（first to migrate；最低风险；最高价值——直接用 17A standard payload validator）；§15 PR-UI-2 |

### 6.9 `ui/control_tab.py`（CORE_UI_TAB）

| 维度 | 说明 |
|---|---|
| 为什么保留 | command bar / agent command / query executor 触发 tab |
| 目标职责 | 用户命令解析 + 触发 |
| 后续实现任务 | §9 §9.2 顺序 6（mid-migration） |

### 6.10-6.18 ui/ renderer / infra 9 项

| 模块 | 性质 | 17M 处置 |
|---|---|---|
| `ui/projection_v2_renderer.py` | V2 raw → Streamlit-ready view | KEEP；§9 mid-migration |
| `ui/big_up_contradiction_card.py` | Task 090 streamlit renderer；docstring "Pure presentation layer"；与 17K §6.6 协同 | KEEP；§15 PR-UI-6 |
| `ui/anti_false_exclusion_display.py` | Step 2G-7A read-only sidecar；docstring 严锁 | KEEP；§15 PR-UI-6 |
| `ui/exclusion_reliability_review.py` | streamlit renderer；调 services.exclusion_reliability_review（17K Review）| KEEP；与 17K 协同 |
| `ui/protection_layer_diagnostics_renderer.py` | Step 2G-8A.2 pure-function pair；docstring 严锁 | KEEP |
| `ui/soft_metadata_renderer.py` | Step 2G-6A pure-function renderer | KEEP |
| `ui/soft_metadata_baseline_cache.py` | session_state baseline cache | KEEP |
| `ui/command_bar.py` | command bar；含 streamlit 软依赖 | KEEP |
| `ui/labels.py` | UI tab labels 常量 | KEEP；不动 |

---

## 7. renderer / summary / dashboard 归属判断

> **本节给出 10 个 service-side renderer / narrative / dashboard 模块的
> UI 渲染归属判断**。这些模块**逻辑层归属其它分支**（17J Final Report
> 或 17L Evaluation），**UI 渲染由 17M 协同**；具体处置由 17M 之后的 PR
> 综合决定，**不在 17M 执行**。

### 7.1 `services/projection_narrative_renderer.py`

| 维度 | 判断 |
|---|---|
| 当前性质 | render V2 raw → 中文 trading narrative；docstring "fixed Chinese trading narrative"；不调 streamlit；不做 layout |
| 哪些属 UI Layer | **无**——本身是 logic-layer reshape；不属 17M 主路径 |
| 哪些属 Final Report Layer | 全部（17J §6.7 已声明 FINAL_REPORT_RENDERER） |
| 当前阶段是否立即拆 | ❌ **不立即拆**；与 17J §6.7 一致 |
| 17M 推荐 | UI consume only；不归 17M 主路径；§15 PR-FINAL-6 协同 |

### 7.2 `services/projection_three_systems_renderer.py`

| 维度 | 判断 |
|---|---|
| 当前性质 | reshape V2 raw → 三系统视图；docstring "no scanning, prediction, or rule mutation" |
| 哪些属 UI Layer | **无** |
| 哪些属 Final Report Layer | 全部（17J §6.7） |
| 17M 推荐 | UI consume only；不归 17M 主路径 |

### 7.3 `services/predict_summary.py`

| 维度 | 判断 |
|---|---|
| 当前性质 | readable Chinese summary helpers |
| 哪些属 UI Layer | **无**——是 logic-layer narrative helper |
| 哪些属 Final Report Layer | 全部（17J §6.6） |
| 17M 推荐 | UI consume only |

### 7.4 `services/ai_summary.py`

| 维度 | 判断 |
|---|---|
| 当前性质 | optional LLM source-attributed explanation；默认 `enable_ai_summary=False`；trading / hard / forced / required post-check reject |
| 哪些属 UI Layer | **无**——是 backend optional opt-in；UI **不**改 default；UI **不**让 LLM 进默认 active path |
| 哪些属 Final Report Layer | 全部（17J §6.6） |
| 17M 推荐 | UI 仅 consume；保持 opt-in；与 1.0 §13 hard rule 1 / 5 一致；§15 PR-UI-* 不动 ai_summary 默认 |

### 7.5-7.7 contract_payload_inspector / diff / trend

| 模块 | 17M 推荐 |
|---|---|
| `services/contract_payload_inspector.py` | 数据层归 17L §6.2；UI consume；§15 PR-UI-2 inspect tab 渲染 |
| `services/contract_payload_diff.py` | 数据层归 17L §6.3；UI consume；§15 PR-UI-2 |
| `services/contract_payload_trend.py` | 数据层归 17L §6.4；UI consume；§15 PR-UI-2 |

### 7.8 `services/contract_payload_extras_dashboard.py`

| 维度 | 判断 |
|---|---|
| 当前性质 | read-only extras dashboard；docstring "verification / observability tool, not a UI feature" |
| 哪些属 UI Layer | **无**——数据层归 17L §6.5 |
| 哪些属 Evaluation Layer | 全部（17L） |
| 17M 推荐 | UI consume；§15 PR-UI-5 evaluation dashboard display-only split |

### 7.9 `services/regime_diagnostics_dashboard.py`

| 维度 | 判断 |
|---|---|
| 当前性质 | regime diagnostic dashboard 数据层；用作 anti_false_exclusion_dashboard / soft_metadata_simulator caller |
| 哪些属 UI Layer | **无**——数据层归 17L §6.11 |
| 17M 推荐 | UI consume；§15 PR-UI-5 |

### 7.10 `services/anti_false_exclusion_dashboard.py`

| 维度 | 判断 |
|---|---|
| 当前性质 | aggregate dashboard；6-gate hard pass/fail + soft metadata baseline；`hard_exclusion_allowed` 永远 `False` 在 v1 |
| 哪些属 UI Layer | **无**——数据层归 17L §6.13；UI 渲染由 ui/anti_false_exclusion_display 完成 |
| 17M 推荐 | UI consume；§15 PR-UI-5 |

### 7.11 总结：10 个模块都不归 17M 主路径

> 全部归 17J Final Report（4 个 narrative renderer）或 17L Evaluation
> （6 个 dashboard data 层）；UI 只 consume + render via streamlit；**不**
> 重写 reshape 逻辑。17M **不**改任何模块。

---

## 8. legacy field → standard payload 映射规则

### 8.1 UI 未来应优先读取 standard_projection_payload.v1

| section | 来源 |
|---|---|
| `metadata` | architecture_orchestrator（未来；17J §13）|
| `feature_payload` | Branch 2 Feature Layer（17F §8）|
| `projection_result` | Branch 3 Projection Layer（17G §8）|
| `exclusion_result` | Branch 4 Exclusion Layer（17H §8）|
| `confidence_result` | Branch 5 Confidence Layer（17I §8）|
| `final_report` | Branch 6 Final Report Layer（17J §11）|
| `review_stub` / `review_result` | Branch 7 Review & Learning Layer（17K §12）|
| `evaluation_stub` / `evaluation_result` | Branch 8 Evaluation Layer（17L §13）|
| `compatibility_metadata` | architecture_orchestrator（未来）|

### 8.2 旧字段只能作为 compatibility fallback

UI 当前依赖的 legacy fields（来自 `predict.PredictResult`）：

| legacy field | 来源 | UI 当前位置（[ui/predict_tab.py](ui/predict_tab.py)）| 标准替代 |
|---|---|---|---|
| `final_bias` | `predict.run_predict` | line 273 / 300 / 380 / 386 | `final_report.final_direction`（passthrough from `primary_analysis.direction`；与 17J §11.1 一致）+ `projection_section.most_likely_state` |
| `final_confidence` | `confidence_result.combined_confidence.level` passthrough（17J §6.1）| line 274 / 301 / 380 / 386 | `final_report.final_confidence`（passthrough；与 17J §11.1 一致）+ `confidence_section.combined_confidence.level` |
| `primary_projection` | `predict.build_primary_projection`（V1）| line 281 / 371 | `projection_section.most_likely_state` / `ranked_states` / `state_probabilities`（与 17G §8 一致）|
| `peer_adjustment` | `predict.apply_peer_adjustment` | line 281 | feature_payload `peer_alignment`（17B PR-C / 17F §8）|
| `final_projection` | `predict.build_final_projection` | line 283 / 373 / 386 | `final_report.final_direction` + `confidence_section.combined_confidence` |
| `path_risk` | predict 派生 | predict_tab consume | `final_report.risks` / `agreement_or_conflict_section`（17J §11.1）|
| `peer_path_risk_adjustment` | predict 派生 | predict_tab consume | feature_payload `peer_alignment.up_support` / `down_support`（17B PR-C 输出 + 17F §8）|
| `predicted_top1` / `predicted_top2` | `main_projection_layer` interim alias（17G §5）| - | standard `projection_result.most_likely_state` / `ranked_states`（17G §8） |
| `triggered_rule` | `exclusion_layer` interim single（17H §5）| - | standard `exclusion_result.triggered_rules` (list) / `most_unlikely_state` / `excluded_states`（17H §8） |

### 8.3 UI 必须遵守的 4 条规则

> **规则 1**：UI **不得长期**以 legacy fields 为主字段。新代码必须先读
> standard schema；只在缺失时 fallback。

> **规则 2**：UI **不得**在字段缺失时自己编造（与 1.0 §8 Branch 9
> "任何展示文本必须可在 final_report / review / evaluation 中找到出处"
> 一致）。

> **规则 3**：UI **必须**显示 `schema_version` / `data_freshness` /
> `missing_sections` —— 当 standard payload 缺失某 section 时，UI 必须
> 显式标注 "compatibility mode"（详见 §13 view_model schema）。

> **规则 4**：fallback **必须**显式标注 compatibility mode；不可静默
> fallback 到 legacy。

### 8.4 17M 立即动作

- **无**（与 17D §11 / 17M §17 一致：本轮不改代码）
- §15 PR-UI-7 compatibility fallback explicit + PR-UI-9 legacy field
  read deprecation marker

### 8.5 字段映射 PR 实施顺序

- 优先级与 §9 Tab 迁移顺序一致
- inspect tab（§9 顺序 1）已经天然 consume standard payload；最低改动
- predict tab（§9 顺序 7）改动最大；最后做

---

## 9. Tab 迁移顺序

### 9.1 原则

- 低风险先 → 主入口最后
- 任何 tab 迁移**必须**先有 adapter / renderer tests
- predict tab **不得**第一批迁移
- app.py shell **最后**统一（与 1.0 §13 hard rule 3 一致：app.py 只允许
  最小改动）
- 每个 tab 迁移**单独 commit**；可 git revert（与 17D §6 单 commit 单
  revert 体例一致）

### 9.2 8 步迁移顺序

| 顺序 | Tab / 模块 | 风险 | 理由 |
|---|---|---|---|
| **1** | `ui/inspect_tab.py` | L | 最适合做 standard payload display 试点；当前 consume `services/inspect_analysis`（16G UNKNOWN）；改 inspect tab 不影响主推演；最高价值——直接用 17A standard payload validator |
| **2** | `ui/history_tab.py` | L | 只读历史 prediction record；不影响当次推演；只需把 prediction_store 读出的 record 字段从 legacy 改为 standard |
| **3** | `ui/review_tab.py` | L | 只读 review record / lesson；不影响当次推演；与 17K §16.4 协同 |
| **4** | `ui/research_tab.py` | L | 只读辅助 research 信息；不影响主推演 |
| **5** | `ui/scan_tab.py` | L | 只读扫描结果；scan_result 来自 scanner（17F § / 17G §11）；scan_bias 在 17G §11 已声明 LEGACY_PROJECTION_LIKE；UI 仅 display |
| **6** | `ui/home_tab.py` | M | 入口卡片；调 `home_terminal_orchestrator` 间接路径；与 V2 chain 收敛由 architecture_orchestrator 决定（17J §13）|
| **6'** | `ui/control_tab.py` | M | command bar；与 home_tab 同期 |
| **7** | `ui/predict_tab.py` | **H** | **主入口**；最后迁移；当前 5 处 read legacy fields（line 273-386）；Bridge #1 退出条件 #1 主对象；§15 PR-UI-7 compatibility fallback explicit |
| **8** | `app.py` shell | **H** | 最后统一；§15 PR-UI-8 stabilization；保持 1.0 §13 hard rule 3 |

### 9.3 顺序硬约束

- **不允许**跳级（如先迁 predict 再迁 inspect）
- **不允许**多个 tab 在同一 PR 中迁移
- 每步 tab 迁移**单独**走 plan → builder → reviewer → tester；与 1.0 §15
  一致
- 任一 tab 迁移失败 → 立即 git revert；不修补；不绕过

### 9.4 17M 不执行任何 tab 迁移

- 与 17D §11 / 17M §17 一致
- §15 PR-UI-* 系列在 18A+ 阶段执行

---

## 10. UI 与 Orchestrator 的边界

### 10.1 UI 只调用 service / orchestrator

- UI 调用层级：
  - 当前：`run_predict` / `home_terminal_orchestrator.build_home_terminal_orchestrator_result` /
    `run_review_for_prediction` / `capture_outcome` / `generate_review` /
    `run_research` / `run_scan`
  - 未来：`architecture_orchestrator.build_standard_projection_payload`（17J §13）
- UI **不**调用 sub-layer 子函数（如 `_compute_agreement` /
  `_score_distribution` / `_kill_risk` 等内部 helper）

### 10.2 UI 不决定数据流

- 与 1.0 §9 一致
- 数据流方向由各层 plan 决定；UI 是**末端**展示

### 10.3 UI 不组合 standard_projection_payload.v1

- 组装责任归 architecture_orchestrator（17J §13）
- UI 只 consume + render

### 10.4 architecture_orchestrator 不属于 UI

- 与 17J §13 一致
- architecture_orchestrator 归 ASSEMBLY_ORCHESTRATION_LAYER /
  TEMP_FUTURE_ORCHESTRATOR；不在 9 分支正式架构内
- UI 是 architecture_orchestrator 的**消费方**，不是 owner

### 10.5 UI 不直接调用 projection / exclusion / confidence 子系统

- UI **不**直接 import `services.main_projection_layer.build_main_projection_layer`
  跑业务计算
- UI **不**直接 import `services.exclusion_layer.run_exclusion_layer` 跑
  exclusion 决策
- UI **不**直接 import `services.confidence_evaluator.build_confidence_result`
  跑 confidence 计算
- UI 通过 orchestrator 路径间接看到 results

### 10.6 UI 不绕过 final_report / payload contract

- UI 必须从 `final_report` 读 display passthrough；不绕过 final_decision
  自己派生 direction / confidence

### 10.7 UI 不写 DB schema

- 与 17K §18 / 17L §18 / 17M §11 一致
- `CREATE TABLE` / `ALTER TABLE` 在 17M 阶段不允许

---

## 11. UI 与 Evaluation Dashboard 的边界

### 11.1 Evaluation Layer 生成 dashboard-ready data

- 与 17L §6.11 / §6.13 / §16.7 一致
- `services/anti_false_exclusion_dashboard` / `services/regime_diagnostics_dashboard` /
  `services/contract_payload_extras_dashboard` 输出已是 dashboard-ready
  dict

### 11.2 UI Layer 负责展示 dashboard-ready data

- ui/anti_false_exclusion_display（已存在）+ 未来其它 dashboard renderer
- UI **不**重新计算 metric

### 11.3 UI 不运行 replay

- 与 17L §16.3 / 17M §3.2 一致
- replay 由 Evaluation Layer 主入口（historical_replay_training）触发；
  不在 UI 内部

### 11.4 UI 不计算 win-rate

- 与 17L §16.2 一致
- win-rate / accuracy 计算属 Branch 8 Evaluation 责任

### 11.5 UI 不接 holdout

- 与 17L §8.5 一致
- holdout 评估由 Evaluation 离线触发；不在 UI 路径

### 11.6 UI 不生成 raw artifacts

- 与 17L §9.4 一致
- raw replay output / raw csv / raw json **不**在 UI 路径生成
- UI 只展示已生成的 manifest / summary

### 11.7 UI 不修改 evaluation_result

- 与 17L §16.4 一致
- evaluation_result 是 evaluation 输出 snapshot；UI 只读

---

## 12. UI 与 Review / Learning 的边界

### 12.1 Review Layer 生成 review_result / memory / lesson

- 与 17K §3.1 一致
- review_orchestrator / review_store / memory_store 是 owner；UI 是 caller /
  consumer

### 12.2 UI 展示 review / memory / lesson

- ui/review_tab.py 是主入口
- ui/exclusion_reliability_review.py 调 `services.exclusion_reliability_review`
  → 17K §17.1

### 12.3 UI 不写 rule memory

- 与 17K §3.2 一致
- memory 写入由 review_orchestrator / review_agent / memory_store 完成；
  不在 UI 路径

### 12.4 UI 不 promote rule

- 与 17K §17.3 一致
- `active_rule_pool_promotion` 永久 OFFLINE_ONLY；UI **不**接

### 12.5 UI 不把 lesson 变成 forced decision

- 与 17K §3.2 / 17J §4 一致
- lesson 在 UI 中**只**作 advisory display；不影响当次 final_report 字段

### 12.6 UI 不把 briefing 变成 mutation hook

- 与 17K §10.4 一致
- `_apply_briefing_caution`（17K §10）当前是 0.x 违反；UI 不在 17M 阶段
  自己派生 caution mutation；归 17K PR-REVIEW-2

---

## 13. UI Result / Presentation Schema 规则

### 13.1 顶层结构（草案 `presentation_payload.v1` / `view_model.v1`）

> **当前未明确实现 schema_version**：现有 ui/ tabs 直接消费上游 dict
> （final_report / scan_result / review_result 等），**没有**统一 view_model
> 包装层。§15 PR-UI-1 决定是否引入。

```
{
    "schema_version": "presentation_payload.v1",          # 草案；PR-UI-1 决定
    "source_payload_schema_version": "standard_projection_payload.v1" | "v2_unified" | "legacy_predict_result",
    "page_id": "predict" | "home" | "history" | "review" | "research" | "scan" | "inspect" | "control",
    "tab_id": "...",                                       # sub-tab id（如 inspect 内 sub_a/b/c/d）
    "generated_at": "YYYY-MM-DDTHH:MM:SS",

    "display_sections": [                                  # 主展示段
        {
            "section_id": "projection" | "exclusion" | "confidence" | "final_report" | ...,
            "title_zh": "...",
            "items": [...],                                # display-only items
            "source_payload_path": "final_report.projection_section",
        },
        ...
    ],

    "cards": [                                             # warning / advisory cards
        {
            "card_id": "big_up_contradiction" | "big_down_tail" | "soft_metadata" | "anti_false_exclusion" | "protection_layer" | ...,
            "level": "info" | "warning" | "critical",
            "title_zh": "...",
            "message_zh": "...",
            "evidence_refs": [...],
            "source_payload_path": "final_report.warning_cards[i]",  # 来自 17J PR-FINAL-4
        },
        ...
    ],

    "warnings": [...],                                     # display-only 警告
    "missing_sections": [...],                             # standard payload 缺失的 section names
    "compatibility_mode": "standard" | "legacy_fallback" | "v2_unified_passthrough",
    "compatibility_notes": [...],                          # 如：当前 read legacy final_bias，因为 standard projection_section.most_likely_state 缺失

    "raw_payload_ref": {                                   # 上游 payload 的 ref（不内嵌完整 dict）
        "payload_type": "...",
        "schema_version": "...",
        "source_module": "...",
    },

    "no_mutation_confirmations": {                         # UI 不修改任何上游字段
        "upstream_payload_mutated": False,
        "schema_version_overridden": False,
        "missing_section_filled_with_fabricated_values": False,
    },
}
```

### 13.2 字段最小要求

| 字段 | 类型 | 备注 |
|---|---|---|
| `schema_version` | str | `"presentation_payload.v1"`（PR-UI-1 落地后）|
| `source_payload_schema_version` | str | 显式来源 schema |
| `page_id` / `tab_id` / `generated_at` | str | 必备 |
| `display_sections` | list[dict] | 必备 |
| `compatibility_mode` | str | 必备；与 §8.3 规则 3 / 4 一致 |
| `missing_sections` | list[str] | 必备；为空 list 当 standard schema 完整 |
| `no_mutation_confirmations` | dict | 至少 3 项 boolean，全 `False` |

### 13.3 缺失语义（与 17F ~ 17L 体例一致）

- 缺失字段一律用 `null` / 空 list `[]`
- `compatibility_mode = "legacy_fallback"` 时 `compatibility_notes` 必须
  非空
- `missing_sections` 必须**始终输出**（即使为空）
- `no_mutation_confirmations` 必须**始终输出**

### 13.4 UI view model 派生展示结构，不改业务字段

- view model 可以做 display formatting（中文化 / 排序 / 分组）
- view model **不**改 source_payload 业务字段值
- view model **不**重算 direction / probability / confidence

### 13.5 不允许的字段

- ❌ `most_likely_state` / `most_unlikely_state` / `state_probabilities`
  在顶层（应在 `display_sections` 子项中）
- ❌ `*_mutated = True`（与 §3.2 一致）
- ❌ `simulated_trade` / `trading_action` / `buy` / `sell` / `hold` /
  `no_trade`
- ❌ `hard_*` / `forced_*` / `required_*` / `_PROTECTION_LAYER_CONNECTED` /
  `production_promotion`

### 13.6 UI 不直接生成 standard_projection_payload.v1

- 与 17F §8.4 / 17G §9.3 / 17H §9.3 / 17I §9.3 / 17J §12.2 / 17K §12.5 /
  17L §13.5 一致
- standard_projection_payload.v1 由 architecture_orchestrator 组装
- UI 只 consume；UI view model 是 **presentation 派生**，与 standard
  payload 平行

---

## 14. UI Layer 测试策略

后续 UI Layer 实现 PR 必须满足以下测试要求：

### 14.1 renderer pure-function tests

- 每个 ui/ renderer / display 模块必须含 pure-function helper（已大部分
  实现）
- helper 不直接调用 streamlit 业务函数（streamlit 模块本身可以 import；
  business render 函数通过 monkeypatch fake_st 测试）
- 输入是 dict；输出是 view_model dict 或 markdown str
- 不读 DB / 不调网络 / 不发 yfinance / 不调 LLM 业务

### 14.2 no backend recomputation tests

- AST-level grep：UI 模块 source 中**不**调以下函数（即使 import 也不调）：
  - `services.main_projection_layer.build_main_projection_layer`
  - `services.exclusion_layer.run_exclusion_layer`
  - `services.confidence_evaluator.build_confidence_result`
  - `services.final_decision.build_final_decision`
  - `services.historical_replay_training.run_historical_replay_*`
  - `services.regime_validation_helper.build_regime_validation_report`
  - `services.active_rule_pool_calibration.*`
- 例外：UI 通过 orchestrator 间接触发 `run_predict` / `home_terminal_orchestrator`
  / `architecture_orchestrator` 是允许的（通过主入口；不绕过）

### 14.3 legacy fallback explicit tests

- ui/ tabs 在 standard schema 缺失时显式标注 `compatibility_mode = "legacy_fallback"`
- AST-level grep：UI 不在 fallback 时静默使用 legacy 字段

### 14.4 missing section display tests

- 当 final_report 缺 `projection_section` / `exclusion_section` /
  `confidence_section` 任一段时，UI 显式提示 missing
- view model `missing_sections` 列表正确

### 14.5 warning_cards render tests

- ui/big_up_contradiction_card / ui/anti_false_exclusion_display 等
  warning 渲染器输入 final_report.warning_cards（17J PR-FINAL-4 schema）
- 输出 view_model 或 markdown
- 不调外部模块；不跑业务计算

### 14.6 evaluation dashboard display-only tests

- ui/ evaluation dashboard renderer（未来；§15 PR-UI-5）输入 evaluation
  layer dashboard data（17L §17.1）
- UI **不**重新计算 metric

### 14.7 review display-only tests

- ui/review_tab consume review_result（17K §12）
- UI **不**写 review_store / memory_store

### 14.8 no trading fields tests

- 输出 view model **不含**：`simulated_trade` / `trading_action` /
  `buy` / `sell` / `hold` / `no_trade` / `hard_*` / `forced_*` /
  `required_*` / `_PROTECTION_LAYER_CONNECTED` / `production_promotion`

### 14.9 no hard / forced / required fields tests

- 与 §14.8 重叠；显式 AST-level grep

### 14.10 no mutation tests

- AST-level grep：UI 模块不修改入参 dict（不直接 `result["foo"] = ...`
  覆盖上游字段）
- view_model 与上游 dict id 不同

### 14.11 app / tab smoke tests

- app.py 至少能 import 不抛异常
- 每个 tab render 函数能用 fake_st monkeypatch 跑通基础路径
- 至少 happy path + missing data path 两组 case

### 14.12 baseline & regression

- 每个 PR-UI-* 必须以 Step 15 baseline 为起点（**3256 passed, 10
  skipped, 0 failed, 26 warnings, 94 subtests**）
- 新增测试数显式累加到 passed
- warnings / subtests 数变化必须**显式说明**

---

## 15. UI Layer 后续 PR 候选

> **本节是 PR 候选清单，本轮 17M 不执行任一项**。最早 18A 由用户单独
> 决定执行哪个、何时执行、按什么顺序执行。

| 序号 | 名称 | 性质 | 目标 | 文件范围 | 测试 | 风险 | 是否必须先做 |
|---|---|---|---|---|---|---|---|
| **PR-UI-1** | presentation_payload / view_model contract helper | 代码（新增 helper） | 新增 `ui/presentation_payload_contract.py`：定义 `PRESENTATION_PAYLOAD_FIELDS` + `validate_presentation_payload(payload) -> list[str]` 纯函数 validator；体例与 17A / 17F PR-FEATURE-1 / 17G PR-PROJ-1 / 17H PR-EXCL-1 / 17I PR-CONF-1 / 17J PR-FINAL-1 / 17K PR-REVIEW-1 / 17L PR-EVAL-1 一致；**不**改 ui/ tabs 实现 | `ui/presentation_payload_contract.py`（新增）+ `tests/test_presentation_payload_contract.py`（新增） | focused + full pytest | L | 不强制；推荐第一项 |
| **PR-UI-2** | Inspect tab standard payload display | 代码（仅 inspect_tab + helper） | 给 `ui/inspect_tab.py` 加 standard payload display section：consume `services/contract_payload_inspector` / `_diff` / `_trend` / `_extras_dashboard`；展示 `schema_version` / `missing_sections` / `compatibility_mode`；**不**改主推演 path；§9 顺序 1 | `ui/inspect_tab.py`（add section）+ tests | focused + full pytest | L | 不强制；§9 first to migrate |
| **PR-UI-3** | History tab read-only standard payload display | 代码（仅 history_tab） | 给 `ui/history_tab.py` 加 standard schema 优先 fallback；read prediction_store rows 时优先读 `standard_projection_payload.v1` 字段；legacy fallback 显式标注；§9 顺序 2 | `ui/history_tab.py`（仅 fallback logic） | focused + full pytest | L | 不强制 |
| **PR-UI-4** | Review tab review_result display | 代码（仅 review_tab） | 给 `ui/review_tab.py` 接 17K §12 review_result schema；§9 顺序 3 | `ui/review_tab.py` | focused + full pytest | L | 不强制；与 17K 协同 |
| **PR-UI-5** | Evaluation dashboard display-only split | 代码（新增 ui renderer + 现有 dashboard split） | 把 `services/anti_false_exclusion_dashboard` / `regime_diagnostics_dashboard` / `contract_payload_extras_dashboard` 渲染部分（如有 streamlit 调用）抽到 `ui/{...}_renderer.py`；service 部分保持 read-only data；§9 顺序中 evaluation dashboard 阶段 | `ui/anti_false_exclusion_display.py`（已存在）+ 新增 ui dashboard renderer | focused + full pytest | M | 不强制；与 17L §16 协同 |
| **PR-UI-6** | warning_cards renderer | 代码（新增 ui helper + 集成） | 新增 `ui/warning_cards_renderer.py`：consume final_report.warning_cards（17J PR-FINAL-4 schema）；render 为 streamlit cards（big_up / big_down / soft_metadata / anti_false / protection_layer 5 类）；与 ui/big_up_contradiction_card 等已有 renderer 协调 | `ui/warning_cards_renderer.py`（新增）+ 与 5 个已有 renderer 集成 | focused + full pytest | M | 不强制；与 17J PR-FINAL-4 协同 |
| **PR-UI-7** | Predict tab compatibility fallback explicit | 代码（**关键 PR**；predict_tab 主入口迁移） | 给 `ui/predict_tab.py` 5 处 read legacy 字段位置（line 273-386）加显式 fallback：先读 standard `final_report.projection_section.most_likely_state` / `confidence_section.combined_confidence.level`；缺失时 fallback to legacy + 显式 `compatibility_mode = "legacy_fallback"` 标注；§9 顺序 7（最后才迁）| `ui/predict_tab.py`（仅 5 处 read 位置） | focused + full pytest；现有 caller 兼容 | **H** | 不强制；最重要的 UI PR；与 17J §11 / 17I §10 / Bridge #1 退出条件 #1 协同 |
| **PR-UI-8** | app.py tab shell stabilization | 代码（**仅** docstring + 极小改动） | 给 `app.py` 顶部加 marker docstring：`CORE_UI_APP_ENTRY — Branch 9 entry per 1.0 §13 hard rule 3：app.py 只允许最小改动`；不动 tabs 调用；不动 import；§9 顺序 8（最后） | `app.py`（仅 docstring）| full pytest byte-stable | L | 不强制；§9 last |
| **PR-UI-9** | legacy final_bias / final_confidence read deprecation marker | 代码（**仅** docstring） | 给 `predict.py` 中 legacy `PredictResult` 字段相关 helper 加 docstring marker：`LEGACY_BRIDGE_FIELD — UI 主面板未来读 standard final_report.* per 17M §8 / Bridge #1 退出条件`；与 16I §11.2 marker 体例一致；**不**改逻辑 | `predict.py`（仅 docstring） | full pytest byte-stable | L | 不强制；与 17J PR-FINAL-7 / 17G PR-PROJ-7 / 16I PR-G 一致 |

### 15.1 候选 PR 之间的依赖

- PR-UI-1 → PR-UI-2 / PR-UI-3 / PR-UI-4 / PR-UI-5：先有 view_model
  contract validator，再做 tab 迁移
- PR-UI-2 → PR-UI-3 → PR-UI-4 → PR-UI-5 → PR-UI-6 → PR-UI-7 → PR-UI-8：
  与 §9.2 Tab 迁移顺序一致
- PR-UI-7 ⚠️ **关键 PR**：依赖 17J PR-FINAL-1（final_report contract validator）
  + 17I PR-CONF-2 + PR-CONF-3（PR-E 实质；schema adapter + calibration_context
  显式 fallback）；这些都需要先在对应层实施
- PR-UI-9：可独立做；与 16I PR-G bridge marker 协同
- 任何**代码** PR-UI-* 都依赖 **17M 已入 main**（前置条件）

### 15.2 候选 PR 都不能做的事

- ❌ 不在 UI 中重新计算 prediction / exclusion / confidence
- ❌ 不在 UI 中跑 replay / holdout / calibration
- ❌ 不改 app.py 业务逻辑（与 1.0 §13 hard rule 3 一致）
- ❌ 不改 predict.py 主路径业务逻辑（PR-UI-9 仅 docstring marker）
- ❌ 不动 services/ 业务模块的算法 / 阈值 / schema
- ❌ 不动 final_decision / projection_chain_contract / consistency_layer /
  main_projection_layer / exclusion_layer / confidence_evaluator
- ❌ 不动 V2 orchestrator / home_terminal_orchestrator
- ❌ 不切换默认 `run_predict` 路径
- ❌ 不引入 trading / hard / forced / required
- ❌ 不复活 `continuous_smoothing*` / `archive/legacy/root_stubs/*` /
  promotion 三模块
- ❌ 不修改 `.gitignore`
- ❌ 不处理 `avgo_agent.db`（含 backup）
- ❌ 不处理 handoff / logs / DB backup / `.claude/worktrees/`
- ❌ 不让 ai_summary 进默认 active path（保持 `enable_ai_summary=False`）
- ❌ 不直接接 broker / trading API
- ❌ 不在 UI 中绕过 service / orchestrator

---

## 16. 清场 / 隔离建议

> **本节按 16H 决策表 8 个标签给出 UI Layer 范畴内的清场建议**。本轮
> **不**执行任何清场动作。

### 16.1 KEEP（UI Layer CORE）

- `app.py`
- `ui/home_tab.py` / `ui/predict_tab.py` / `ui/history_tab.py` /
  `ui/review_tab.py` / `ui/research_tab.py` / `ui/scan_tab.py` /
  `ui/inspect_tab.py` / `ui/control_tab.py`（共 8 个 tab）
- `ui/projection_v2_renderer.py`
- `ui/big_up_contradiction_card.py`
- `ui/anti_false_exclusion_display.py`
- `ui/exclusion_reliability_review.py`
- `ui/protection_layer_diagnostics_renderer.py`
- `ui/soft_metadata_renderer.py`
- `ui/soft_metadata_baseline_cache.py`
- `ui/command_bar.py`
- `ui/labels.py`

### 16.2 NOT_UI_LAYER（声明非 UI Layer 主路径；归其它层；UI consume）

- `services/projection_narrative_renderer.py` → 17J §17.2 Final Report
- `services/projection_three_systems_renderer.py` → 17J §17.2
- `services/predict_summary.py` → 17J §17.2
- `services/ai_summary.py` → 17J §17.2（OPT-IN ONLY）
- `services/contract_payload_inspector.py` → 17L §6.2 Evaluation
- `services/contract_payload_diff.py` → 17L §6.3
- `services/contract_payload_trend.py` → 17L §6.4
- `services/contract_payload_extras_dashboard.py` → 17L §6.5
- `services/regime_diagnostics_dashboard.py` → 17L §6.11
- `services/anti_false_exclusion_dashboard.py` → 17L §6.13

### 16.3 LEGACY_BRIDGE_FIELDS（必须迁出长期使用；fallback only）

- `predict.PredictResult` 中：`final_bias` / `final_confidence` /
  `primary_projection` / `peer_adjustment` / `final_projection` /
  `path_risk` / `peer_path_risk_adjustment` / `predicted_top1` /
  `predicted_top2` / `triggered_rule`（与 1.0 §10 / 16I §11.2 / 17J §17.5
  / Bridge #1 退出条件 #1 一致）
- 17M 不删；§15 PR-UI-9 marker；最终随 Bridge 退出条件满足而消失

### 16.4 MIGRATE_LATER

- §16.2 全部 service-side narrative / dashboard 模块由对应层 Plan
  接管；UI 只 consume

### 16.5 ARCHIVE_IN_REPO

- 无 UI Layer 范畴的 archive 候选（与 16H / 17E §15.5 / 17F §16.5 / 17G §16.8 /
  17H §15.5 / 17I §17.6 / 17J §17.7 / 17K §17.6 / 17L §17.7 一致）

### 16.6 QUARANTINE

- 无 UI Layer 范畴的 quarantine 候选（CORE 状态健康；ui/ 模块全部 read-only
  presentation；service-side renderer / dashboard 已 docstring 严锁）

### 16.7 DELETE_NOW

- **空**（与 16H §13 / 17E §15.7 / 17F §16.7 / 17G §16.11 / 17H §15.8 /
  17I §17.8 / 17J §17.9 / 17K §17.8 / 17L §17.9 一致）

### 16.8 DELETE_LATER

- 无 UI Layer 范畴（17M 阶段）；legacy bridge field 长期 fallback，不
  delete
- predict.py 内 `_apply_briefing_caution`（17K §17.4 LEGACY_VIOLATION）
  在 17K PR-REVIEW-2 修复后**可能**变成 dead code 候选；归 18A+ 后续讨论

### 16.9 MIGRATE_CALLER_FIRST

- `predict.py` LEGACY_BRIDGE_FIELDS 在 UI 全部迁完（§9 8 步）后才能讨论
  fields 自身的 archive
- §15 PR-UI-9 marker；不删

### 16.10 MOVE_OUTSIDE_REPO

- 无 UI Layer 范畴

### 16.11 DEEP_AUDIT_REQUIRED

- `services/inspect_analysis.py`（16G §11 UNKNOWN 之一）—— 由 ui/inspect_tab.py
  调用；§15 PR-UI-2 推荐做 deep audit
- 17M 阶段仅声明；不动

> **重申**：任何文件删除 / 移动 / archive 必须等 16H 规则 + 17D §11 + 用户
> 单独确认。17M 仅给出**建议**，**不**执行。

---

## 17. 不允许事项

**17M 起，UI Layer 范畴内**严格禁止：

- ❌ 不改代码（无 `.py` 文件被修改；本轮 0 修改）
- ❌ 不跑数据
- ❌ 不跑 replay / 不跑 validation / 不跑 historical evaluation
- ❌ 不改 DB / 不改 DB schema
- ❌ 不接 trading / 不输出 buy / sell / hold / hard / forced / required
- ❌ 不进入 3R-5 / 3R-6（1.0 §12 / 16I §15 / 17D §11 / 17E §16 / 17F §17 /
  17G §17 / 17H §16 / 17I §18 / 17J §18 / 17K §18 / 17L §18 / 本轮再次重申）
- ❌ 不启动任何代码 PR（PR-UI-* 候选要等 18A）
- ❌ 不修改 `.gitignore`
- ❌ 不处理 `avgo_agent.db`（含 backup）
- ❌ 不处理 handoff / logs / DB backup / `.claude/worktrees/`
- ❌ 不复活 `continuous_smoothing*` / `archive/legacy/root_stubs/*` /
  `active_rule_pool_promotion`（OFFLINE_ONLY 永久）
- ❌ 不污染 2026-01-01 之后 final holdout
- ❌ 不借 17M 顺手做 Data / Feature / Projection / Exclusion / Confidence /
  Final Report / Review / Evaluation 范畴改动
- ❌ **不直接迁 Predict tab**（与 17D §10.2 / §17 §17 一致；归 §15 PR-UI-7；
  18A 审批）
- ❌ **不直接改 app.py**（与 1.0 §13 hard rule 3 一致；只允许最小改动）
- ❌ **不直接改 renderer**（仅 17J / 17L / 17M 之后某个 PR-UI 在 ui/
  范围操作）
- ❌ **不直接改 dashboard**（service-side dashboard data 由 17L 范畴；
  UI rendering 由 17M 之后 PR）
- ❌ **不直接接 architecture_orchestrator**（17J §13.6 前置条件未满足；
  归 18A+ 单独审批）
- ❌ **不直接清 bridge**（与 17D §10.1 一致；归对应层 / Bridge plan）
- ❌ 不让 ai_summary 进默认 active path（保持 opt-in only）
- ❌ 不让 LLM 默认接入 UI
- ❌ 不让 UI 重算业务结果
- ❌ 不在 UI 内部重新 fetch yfinance（必须通过 Data Layer service）
- ❌ 不切换默认 `run_predict` 路径
- ❌ 不打开 16I PR-G bridge marker（与 17D §10.1 一致）
- ❌ 不打开 16I PR-F architecture_orchestrator MVP（与 17D §10.3 / 17J §13 一致）

> 与 17D §11 / 17E §16 / 17F §17 / 17G §17 / 17H §16 / 17I §18 / 17J §18 /
> 17K §18 / 17L §18 一致；本轮再次锁定。

---

## 18. 九分支计划完成后的状态

### 18.1 17M 完成后，九分支按层重建计划全部完成

| Branch | Plan | Status | commit |
|---|---|---|---|
| Branch 1 Data | 17E | ✅ | `f2cf76e` |
| Branch 2 Feature | 17F | ✅ | `a787bf5` |
| Branch 3 Projection | 17G | ✅ | `54f74f1` |
| Branch 4 Exclusion | 17H | ✅ | `392e967` |
| Branch 5 Confidence | 17I | ✅ | `7a2cd46` |
| Branch 6 Final Report | 17J | ✅ | `912cc27` |
| Branch 7 Review & Learning | 17K | ✅ | `d0057c5` |
| Branch 8 Evaluation | 17L | ✅ | `ae6b3a8` |
| Branch 9 UI / Presentation | 17M | ✅（本轮入 main 后）| 待 |
| 治理 | 17D Layer-by-Layer Rebuild Governance | ✅ | `77777d4` |

### 18.2 九分支全部计划齐全 ≠ 可以乱开代码 PR

- 与 17D §6 PR 准入规则一致：每个代码 PR 必须绑定九分支某一层 + 引用
  对应层 Plan §
- 17M 入 main 不**自动**批准任一 PR-UI-* / PR-FEATURE-* / PR-PROJ-* /
  PR-EXCL-* / PR-CONF-* / PR-FINAL-* / PR-REVIEW-* / PR-EVAL-*
- 用户单独审批每个 PR

### 18.3 16I PR-E / PR-F / PR-G / PR-H 全部归各层

- 与 17D §9 / §10 一致：PR-E / PR-F / PR-G / PR-H 全部暂停
- 现在归各层：
  - PR-E confidence key 对齐 → 17I PR-CONF-2 + PR-CONF-3 共同覆盖
  - PR-F architecture_orchestrator MVP → 17J §13 / PR-FINAL-7 ownership
    doc；前置条件 §13.6 / §13.7
  - PR-G bridge deprecation marker → 各层 marker（17G PR-PROJ-7 / 17J
    PR-FINAL-* / 17M PR-UI-9）共同覆盖
  - PR-H UI / evaluation migration plan → 17L + 17M 已经覆盖

### 18.4 下一步必须进入 18A：First Layer-Based Implementation Batch Selection

- 17M 入 main 后；用户单独审批
- 18A 必须明确：第一批实现从哪一层开始 / 为什么 / 文件范围 / 测试范围 /
  回滚方式 / 是否会跨层 / 是否需要用户确认
- 18A **不**自动恢复 16I PR-E / PR-F / PR-G / PR-H

### 18.5 18A 之前禁止任何代码 PR

- 与 17D §11 / §6 一致
- 17M 入 main 之前，UI Layer 范畴 PR 都不能开
- 18A 之前，任何按层 PR 都不能开（17F / 17G / 17H / 17I / 17J / 17K / 17L /
  17M 范畴的 PR-* 候选都需要 18A 单独审批）

---

## 19. 推荐下一步

> **首选**：**Step 18A：First Layer-Based Implementation Batch Selection**

理由（与 17D §6 / §12 / 18 §18.4 一致 + 17M 实战观察）：

- 17M 入 main 后，九分支按层重建**计划**全部完成
- 但**计划**完成 ≠ **实施**完成
- 18A 必须从 9 层 plan + 多个 PR 候选中**选第一批**实施 PR
- 18A 是九分支重建从 plan 阶段进入 implementation 阶段的入口

### 19.1 18A 的工作内容

18A 必须回答：

| 问题 | 决策 |
|---|---|
| 第一批实现从哪一层开始？ | 推荐候选见 §19.2 |
| 为什么？ | 风险 / 价值 / 依赖 / 用户优先级综合判断 |
| 文件范围？ | 严格限制；**不**跨层；与 17D §6 PR 准入 8 题一致 |
| 测试范围？ | focused boundary + full pytest + Step 15 baseline |
| 回滚方式？ | 单 commit 单 revert |
| 是否会跨层？ | 不允许；如确实需要必须显式标注 + 用户审批 |
| 是否需要用户确认？ | ✅ 是；每个 PR 都需要 |

### 19.2 18A 候选第一批 PR（推荐顺序，仅供 18A 参考）

| 优先级 | PR | 性质 | 理由 |
|---|---|---|---|
| **1（推荐）** | **PR-FEATURE-1** + **PR-PROJ-1** + **PR-EXCL-1** + **PR-CONF-1** + **PR-FINAL-1** + **PR-REVIEW-1** + **PR-EVAL-1** + **PR-UI-1**（8 个 contract validator） | 代码（仅新增 helper + tests） | 全部是新增 contract validator helper；体例与 17A PR-B 一致；不动业务；最低风险；为后续按层实现奠基 |
| **2** | **PR-CONF-2** + **PR-CONF-3**（PR-E 实质 part 1 + part 2）| 代码（schema adapter + caller 显式 fallback） | 解决 1.0 §3 描述的 `agreement_status = unknown` 问题；与 17I §13 一致；用户可见价值最高 |
| **3** | **PR-UI-2**（Inspect tab standard payload display） | 代码（仅 inspect_tab） | §9 顺序 1 first to migrate；最低风险；最高价值——直接用 17A standard payload validator |
| **4** | **PR-FINAL-4**（warning_cards schema） + **PR-REVIEW-2**（_apply_briefing_caution warning-only） | 代码（关键违反修复） | 17K §10 / §15 关键违反点；需 17J PR-FINAL-4 协同；用户可见价值高 |

> **本节 §19.2 是推荐供 18A 参考；不是 18A 自动批准清单**。18A 由用户
> 单独决定。

### 19.3 18A 不能自动恢复 16I PR-E / PR-F / PR-G / PR-H

- 与 17D §9 / §10 / 18 §18.3 一致
- PR-E 已实际由 PR-CONF-2 + PR-CONF-3 替代
- PR-F architecture_orchestrator MVP 必须等 §13.6 前置条件全部满足
- PR-G bridge marker 已由各层 marker 替代
- PR-H UI / evaluation migration plan 已由 17L + 17M 覆盖

### 19.4 不推荐

- 不推荐借 17M / 18A 做代码改动（17M 阶段；18A 阶段才能开 PR）
- 不推荐立刻实施 PR-UI-7（predict_tab 主面板迁移；H 风险；§9 顺序 7 最后做）
- 不推荐立刻实施 architecture_orchestrator MVP（§13.6 前置条件未满足）
- 不推荐解锁 3R-5 / 3R-6（1.0 §12 7 项前提仍未全部满足）
- 不推荐立刻跑 2026 holdout / historical replay / calibration（与 17L §1
  / §18 一致）
- 不推荐立刻迁默认 `run_predict` 路径

> **明确**：本轮 17M 推荐的下一步**只有一个候选**——**Step 18A：First
> Layer-Based Implementation Batch Selection**。九分支按层重建从 plan
> 阶段进入 implementation 阶段。

---

## 20. 严守边界

本轮 Step 17M **只**写 UI / Presentation Layer Rebuild Plan：

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
- ❌ 未启用任何 candidate / 未复活 `continuous_smoothing` /
  `active_rule_pool_promotion`
- ❌ 未触碰 RISK-1 / RISK-2 / RISK-3 / RISK-7 / RISK-8 / RISK-9 / RISK-10
- ❌ 未进入 3R-5 / 3R-6
- ❌ 未启动任何代码 PR（PR-UI-* 候选要等 18A）
- ❌ 未直接迁 UI（与 17D §10.2 一致）
- ❌ 未直接改 app.py / renderer / dashboard
- ❌ 未启动 bridge / orchestrator 实现任务
- ❌ 未做任何局部 patch
- ❌ 未 commit / 未 push（按本轮指令）

唯一新增文件：[tasks/record_17m_ui_presentation_layer_rebuild_plan.md](tasks/record_17m_ui_presentation_layer_rebuild_plan.md)（本文件）。

后续修改路径：任何对 §3 职责定义 / §4 禁止事项 / §5 inventory / §6
CORE_UI / §7 renderer 归属 / §8 legacy field 映射 / §9 Tab 迁移顺序 /
§10 与 Orchestrator 边界 / §11 与 Evaluation Dashboard 边界 / §12 与
Review / Learning 边界 / §13 view_model 标准化 / §14 测试策略 / §15 PR
候选 / §16 清场建议 / §17 禁止事项 / §18 九分支完成状态 / §19 下一步
的调整，都必须**显式更新本文件**；同时检查是否需要同步更新 1.0 / 16C /
16D / 16I / 17D / 17E / 17F / 17G / 17H / 17I / 17J / 17K / 17L 与 18A
（18A 入 main 后）。
