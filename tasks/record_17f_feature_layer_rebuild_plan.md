# 17F记录：Feature Layer Rebuild Plan

> 本记录是 **Step 17F：Feature Layer 重建计划**——九分支按层重建中的
> **第二层**（Branch 2）。1.0 canonical / 16A blueprint / 16B inventory /
> 16C target dataflow & contract decision / 16D isolation & quarantine
> plan / 16E core chain refactor plan / 16F no-patching principle / 16G
> full module decomposition standup / 16H repository clearing decision
> table / 16I core chain rebuild execution plan / 17A PR-B standard
> payload skeleton / 17B PR-C peer_alignment 抽公共模块 / 17C PR-D
> main_projection 去 `exclusion_result` 形参 / 17D layer-by-layer rebuild
> governance / 17E Data Layer Rebuild Plan 已全部入 main（main 最新
> commit `f2cf76e`）。
>
> 本轮**只**写计划文档：未改业务代码、未新增测试、未删除文件、未移动
> 文件、未修改 `.gitignore`、未处理 handoff、未处理 logs / DB backup /
> `.claude/worktrees/`、**未处理 `avgo_agent.db`**、未跑 replay /
> validation / historical evaluation、未写 DB / 未改 DB schema、未默认
> 迁移 `run_predict` 到 V2、未接 trading、未输出 buy / sell / hold /
> hard / forced / required、未进入 3R-5 / 3R-6、未启动任何代码 PR、
> 未继续 PR-E confidence key 对齐、未启动 UI / bridge / orchestrator
> 任务、未做任何局部 patch、未 commit / 未 push。
>
> 唯一 deliverable：本文件。
>
> **本记录优先级**：与 17E / 17G ~ 17M 各层 Plan 同级；与 1.0 / 16A /
> 16C / 16D / 16F / 16I / 17D / 17E 协同。冲突仲裁路径与 1.0 §14 / 17D §13
> 一致：旧 records 若与 17F 在 Feature Layer 范畴冲突，**以 17F 为准**。

---

## 1. Step 17F 目的

把九分支按层重建从 Data Layer（17E）推进到**第二层（Feature Layer）的具体
重建计划**。

**本轮只回答**：

- Feature Layer 当前长什么样（模块 inventory）
- Feature Layer 目标长什么样（保留 / 迁移 / 隔离 / 删除候选）
- Feature Layer 与上下游的边界（Data Layer ↑；{Projection, Exclusion,
  Confidence} ↓ —— 三系统并行从 Feature Layer 读，互相不读）
- Feature Layer feature_payload 标准化规则（含 15d window / raw vs adj /
  peer_alignment / code encoding）
- Feature Layer 后续可能的代码 PR 候选（**不**执行）
- 与 Projection / Exclusion 的交接

**本轮不回答**：

- 不写 Projection / Exclusion / Confidence / Final Report / Review /
  Evaluation / UI 计划（17G ~ 17M）
- 不开任何代码 PR（最早 18A）
- 不动 `avgo_agent.db`、`.gitignore`、handoff、logs、DB backup、worktrees
- 不继续 PR-E confidence key 对齐（与 17D §9 一致）
- 不启动 UI / bridge / orchestrator 任务（与 17D §10 一致）

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
| main 最新 commit | `f2cf76e` |
| worktree 唯一 deliberate untracked | `.claude/handoffs/task_089_post_pr_cleanup.md` |
| 战略阶段 | 从 Data Layer plan（17E）→ **Feature Layer plan（17F 本轮）** |
| 3R-5 / 3R-6 | ❌ 仍然不允许进入 |
| 第一个按层实现 PR（18A）| ❌ 仍未 |

**17D §6 PR 准入规则提醒**：

- 任何代码 PR 必须绑定九分支某一层 + 引用对应层 Plan §
- 17F 入 main 后，Feature Layer 范畴的 PR 才**有资格**被讨论
- 17F 本身**不**自动批准任何 PR

**层间依赖**：

- 17F 依赖 17E（已就位）
- 17F **不**依赖 17G ~ 17M（可独立写完）
- 17F 不阻塞 PR-DATA-* 启动（与 17E §13.1 一致）；但**强烈建议**先让 17F
  入 main 再考虑 Data / Feature 跨层 PR

---

## 3. Feature Layer 职责定义

**Feature Layer（Branch 2）只回答一件事**：

> **"把 Data Layer 输出的标准市场数据（OHLCV + Adj Close）转成统一
> `feature_payload`，供 Projection / Exclusion / Confidence 三系统**并行**
> 读取。"**

### 3.1 只做的事

- 接收 Data Layer 输出（OHLCV + Adj Close）
- 切片**目标窗口**（未来标准 15d；当前 20d 为 legacy compatibility）
- 计算收益率：`ret1` / `ret3` / `ret5` / `ret10`（`ret20` 已有但不进 15d
  payload）
- 计算位置：`pos15`（未来）/ `pos20`（当前）/ `pos30`（legacy / UI）
- 计算成交量：`volume` / `volume_ratio`（`vol_ratio20` 当前命名）/
  `turnover` / `amount`（如可获得）
- 计算蜡烛形态：`upper_shadow_ratio` / `lower_shadow_ratio`
- 双轨派生：raw `Close` 用于 `O_gap` / `PrevClose`；`Adj Close` 用于
  `C_adj` 长期收益（与 17E §8.2 双轨规则一致）
- 计算 `peer_alignment`（NVDA / SOXX / QQQ 同日 ret1 → alignment / up_support /
  down_support）
- 5-digit code 编码：`O_code` / `H_code` / `L_code` / `C_code` / `V_code` /
  `Code`（encoder.py 现行实现）
- historical match input preparation：把 5-digit code + 历史窗口准备成
  matcher 输入（matcher 主体属 Feature Layer；NextDate outcome 字段属
  Evaluation Layer，详见 §7）
- regime / stage label 的 **feature 表达**（不是 prediction）：
  `pos20_regime_bucket` / `avgo_minus_soxx_20d` / 五状态 label（基于已发生
  return 的纯分类，**不**预测）

### 3.2 不做的事（与 1.0 §8 Branch 2 / 16A §6 一致）

- ❌ 不做最终预测（`most_likely_state` / `predicted_top1` / `state_probabilities`
  归 Projection）
- ❌ 不做 exclusion / negation（`most_unlikely_state` / `triggered_rule` 归
  Exclusion）
- ❌ 不做 confidence（`agreement_status` / `combined_confidence` 归 Confidence）
- ❌ 不做 final report（`combined_user_summary` 归 Final Report Layer）
- ❌ 不做 review / lesson（归 Branch 7）
- ❌ 不做 evaluation（accuracy / win-rate 归 Branch 8）
- ❌ 不做 UI 展示
- ❌ 不输出 trading action / hard / forced / required
- ❌ 不调用 LLM
- ❌ 不写 DB schema / 不改 DB schema
- ❌ 不直接运行 replay
- ❌ 不直接接 broker API

### 3.3 输入 / 输出（白名单）

**输入**：

- Data Layer 输出（standardized OHLCV `pd.DataFrame`，与 17E §8 一致）
- 历史 5-digit code 表（`coded_data/<SYMBOL>_coded.csv`）—— Feature Layer
  自身写出 + 自身读回
- 历史 features 表（`enriched_data/<SYMBOL>_features.csv`）—— Feature
  Layer 自身写出 + 自身读回
- 不接收任何 system 输出（projection / exclusion / confidence / final_report）
- 不接收 future outcome（在线 inference 路径）

**输出**：

- `feature_payload`（dict / typed dict；snake_case 字段；缺失语义用 `null`
  不用 `0`；与 1.0 §8 Branch 2 一致）
- 5-digit code DataFrame（写到 `coded_data/<SYMBOL>_coded.csv`）
- enriched feature DataFrame（写到 `enriched_data/<SYMBOL>_features.csv`）
- regime label dict（`real_regime_label_provider` 当前形态；`build_regime_features`
  当前形态）
- **不**含 trading / projection / exclusion / confidence / final_report
  字段（boundary tests 强制）

---

## 4. Feature Layer 禁止事项

Feature Layer **永久禁止**输出 / 引入以下任一：

| 类别 | 禁止项 | 锚点 |
|---|---|---|
| 最终预测 | `predicted_top1` / `predicted_top2` / `most_likely_state` / `state_probabilities` / `direction`（指 Projection 输出方向）| 1.0 §8 Branch 2 / 07A §3.2 |
| 否定输出 | `most_unlikely_state` / `triggered_rule` / `false_exclusion_risk` | 1.0 §8 Branch 2 / 07B §3.2 |
| 置信度输出 | `agreement_status` / `combined_confidence` / `confidence_level` / `confidence_score`（Confidence 系统） | 07C §3.2 |
| Final Report 字段 | `combined_user_summary` / `agreement_or_conflict_section` / `non_mutation_confirmations` | 07D §3.2 |
| 交易动作 | `buy` / `sell` / `hold` / `simulated_trade` / `trading_action` | 1.0 §6.1 / §13 hard rule 1 |
| 强制语义 | `hard` / `forced` / `required` / `_PROTECTION_LAYER_CONNECTED` | 12E X1..X5 / 1.0 §6 |
| 系统输出回灌 | 读取 `projection_result` / `exclusion_result` / `confidence_result` / `final_report` 字段后**用作 feature** | 1.0 §9 数据流方向 |
| LLM 调用 | `anthropic` / `openai` / 任何文本生成 SDK | 1.0 §13 hard rule 1 / 5 |
| UI 调用 | `streamlit` / 任何 ui/ 模块 import | 1.0 §13 hard rule 3 |
| 下游系统调用 | import `services.main_projection_layer` / `services.exclusion_layer` / `services.confidence_evaluator` / `services.final_decision` / `predict.py` | 1.0 §9 数据流方向 |
| DB schema 改动 | `CREATE TABLE` / `ALTER TABLE` 在 17F 阶段不允许 | 17E §11 / 17F §11 |
| 直接运行 replay | 调用 `scripts/run_contract_replay*` / `scripts/historical_replay_training*` | 17D §11 |
| Future outcome 回灌 | 在线 inference 路径中读取目标日之后的 close / outcome | 1.0 §9 / 07A §3.2 / 07B §3.2 |
| 污染 2026 holdout | 在 in-sample feature 计算中读取 2026-01-01 之后的窗口 | 1.0 §5 rule 8 |

---

## 5. 当前 Feature Layer 模块 inventory

> **范围说明**：本表覆盖 root（feature_builder / encoder / matcher /
> scanner）+ `services/` 中 Feature Layer 候选 / 跨层模块 + standard
> payload 的 feature_payload 关系 + Feature Layer 的 active callers 链。

| module_path | current_role | current_status | target_role | keep / migrate / quarantine / delete | active_callers | risk | next_action |
|---|---|---|---|---|---|---|---|
| `services/peer_alignment.py` | NVDA / SOXX / QQQ 同日 ret1 → alignment / up_support / down_support / available_peer_count / peer_returns（17B PR-C 已迁出） | KEEP_ACTIVE；docstring 显式声明 Branch 2 | **CORE_FEATURE**：Feature Layer 资产；Projection / Exclusion 共享读 | KEEP | `services/main_projection_layer:21`、`services/exclusion_layer:12` 双向调用 | L | §6.1；§13 PR-FEATURE-7 写 boundary tests（不读 system 输出 + forbidden imports） |
| `services/features_20d.py` | `compute_20d_features(df)` 纯函数；输出 pos20 / ret1/3/5/10/20 / vol_ratio20 / near_high20 / near_low20 / upper_shadow_ratio / lower_shadow_ratio + warning 字段 | KEEP_ACTIVE；纯函数；docstring 明确接口 | **CORE_FEATURE**：标准 20d feature 引擎（未来 15d 也可由该体例派生） | KEEP | `services/home_terminal_orchestrator.py:93+137`；tests | L | §6.2；§13 PR-FEATURE-2 加 15d 入口（不动 20d） |
| `services/state_label.py` | 五状态 label（大涨 / 小涨 / 震荡 / 小跌 / 大跌）—— 纯阈值分类 | KEEP_ACTIVE；唯一 source of truth；阈值锁定 | **CORE_FEATURE**：feature 分类器（**不**是预测器，是基于已发生 return 的分类） | KEEP | `services/log_store:45`、`services/three_system_replay_audit:27`；tests | L | §6.3；不改阈值；不加新 state |
| `services/regime_features_builder.py` | pure regime feature builder（pos20 + avgo_minus_soxx_20d；anti-lookahead；2026 cutoff） | KEEP_ACTIVE；docstring 明确禁 DB / CSV / network / yfinance / 交易 / v1 stub | **CORE_FEATURE**：regime feature 表达 | KEEP | `scanner.py:635`；`services/agent_*`；tests | L | §6.4 |
| `services/regime_labels_builder.py` | pure regime label builder（5 v1 labels + 9 raw features；anti-lookahead；2026 cutoff） | KEEP_ACTIVE；同上 docstring | **CORE_FEATURE**：regime label 表达（label = feature 标注，不是 prediction）| KEEP | `services/real_regime_label_provider`；tests | L | §6.5 |
| `services/projection_chain_contract.py` | `build_feature_payload_from_recent_window` + `least_likely_from_projection` + `excluded_state_from_result` + `build_prediction_log_record` | MIXED；其中 `build_feature_payload_from_recent_window` **属 Feature Layer**；`least_likely_from_projection` 属 Projection 投影；`excluded_state_from_result` 属 Exclusion adapter；`build_prediction_log_record` 属 Final Report / prediction_store | MIXED | KEEP_PARTIAL（Feature 部分）+ MIGRATE_LATER（其它部分由对应层 Plan 决定） | `services/home_terminal_orchestrator`、`services/projection_orchestrator_v2`、tests | M | §7.6；17F 不动；17J 决定 build_prediction_log_record 归属 |
| `services/standard_projection_payload.py` | PR-B validator；`STANDARD_PAYLOAD_SECTIONS` 含 `feature_payload` | KEEP_ACTIVE；纯函数 validator；不接业务 | INFRA / SCHEMA（属于 17A 新架构地基；**不**属 Branch 2） | KEEP（不在 Feature Layer 范围；但 Feature Layer 输出会被 validate） | tests；尚未接入 active path | L | §8.6 cross-reference；不动 |
| `feature_builder.py`（root） | OHLCV CSV → enriched feature CSV（PrevClose / MA20_Volume / O_gap / H_up / L_down / C_move / V_ratio / PrevAdjClose / C_adj） | KEEP_ACTIVE；docstring 不显式 layer 标签 | **CORE_FEATURE**：原始 feature 派生（双轨 raw / adj）| KEEP；17F 显式接管；root 位置不变 | `run_pipeline.py:7` + tests | L | §6.6；不改逻辑 |
| `encoder.py`（root） | 5-digit code 编码：O_code / H_code / L_code / C_code / V_code / Code | KEEP_ACTIVE | **CORE_FEATURE**：feature encoding | KEEP；17F 显式接管；root 位置不变 | `run_pipeline.py:8` + tests + scanner | L | §6.7；不改阈值 |
| `matcher.py`（root） | coded CSV → 历史 5-digit match table（含 NextDate / NextOpen / ... / NextCloseMove / VCodeDiff） | MIXED：(1) match input prep + match 主体 = Feature Layer；(2) NextDate outcome / NextCloseMove 等 = Evaluation Layer 信号 | MIXED | KEEP_PARTIAL（match 主体）+ MIGRATE_LATER（NextDate outcome 字段由 17L Evaluation Layer 决定） | `run_pipeline.py:8`；tests | M | §7.2；17F 不动；17L 决定 NextDate 字段 ownership |
| `scanner.py`（root） | (1) peer CSV 加载（Data Layer 行为，与 17E §7.1 一致）(2) 5-digit code 聚合 / RS / regime_features 调用 = Feature Layer (3) `scan_bias` / `scan_confidence` / `confirmation_state` = **Projection-like / 早期判断输出** | MIXED；最危险跨层模块；与 UI（app.py）紧耦合 | MIXED | KEEP_PARTIAL（Feature 部分）+ MIGRATE_LATER（scan_bias 等由 17G Projection Layer 决定）| `app.py` UI；tests | **H** | §7.1；17F 不动；17G + 17M 共同决定拆分 |
| `services/data_query.py` | (1) `load_symbol_data` CSV loader = Data Layer (2) `_classify_stage` / Ret3 / Ret5 / Pos30 / PosLabel / StageLabel = **Feature Layer** | MIXED | MIXED | KEEP_PARTIAL（Feature enrich 部分由 Feature Layer 接管） | `services/primary_20day_analysis`、UI workbench、tests | M | §7.3；17F 显式声明 Feature 部分；split 实现由 17F 之后 PR 决定 |
| `services/real_regime_label_provider.py` | (1) 4 OHLC CSV loader = Data Layer (2) closure factory + 调 `regime_labels_builder` = **Feature Layer** | MIXED；read-only 诊断模块 | MIXED | KEEP_PARTIAL（factory + closure 属 Feature Layer） | `services/projection_chain_contract`；tests | M | §7.4；17F 不动；17F 阶段仅声明 |
| `services/primary_20day_analysis.py` | 输出 `direction` / `confidence` / `position_label` / `stage_label` / `volume_state` —— **不是 Feature**，是 **Projection 候选** | MIXED；表面叫 "analysis"，行为是早期 Projection | **NOT_FEATURE_LAYER**：归 Branch 3 Projection（17G 决定）| MIGRATE_TO_PROJECTION（17G） | `services/projection_orchestrator_v2`；tests | M | §7.5；17F 显式声明非 Feature；17G 接管 |
| `services/peer_adjustment.py` | "stable Step 2 adjustment"——把 scanner peer summaries 转成调整字段 | **NOT_FEATURE_LAYER**：是 Projection / Bridge 内的 step 2 加工 | 归 LEGACY_ACTIVE_DEPENDENCY / Bridge（17J 决定）| MIGRATE_LATER（17J） | `services/projection_orchestrator_v2`、`predict.py`；tests | M | §7.7；17F 显式声明非 Feature |
| `services/historical_probability.py` | 输出 up_rate / down_rate / probability —— Projection 候选 | **NOT_FEATURE_LAYER**：是 Projection 内部子能力 | 归 Branch 3 Projection（17G 决定）| MIGRATE_TO_PROJECTION（17G） | `predict.py`、`services/projection_orchestrator_v2`；tests | M | §7.8；17F 显式声明非 Feature |
| `services/five_state_margin_policy.py` | 五状态概率分布 → display margin policy（low_margin / watch_margin / clear_top1） | **NOT_FEATURE_LAYER**：是输出 / 展示策略 | 归 Final Report Layer / UI（17J / 17M 决定）| MIGRATE_LATER | scripts；tests | L | §7.9；17F 不动 |
| `services/primary_bias_diagnosis.py` | 从 replay 结果诊断 `primary_20day_analysis` 的方向 bias | **NOT_FEATURE_LAYER**：是 Evaluation / 诊断 | 归 Branch 8 Evaluation（17L 决定）| MIGRATE_LATER | scripts | L | §7.10 |
| `services/regime_validation_helper.py` | 4-fold validation 报告生成（gate threshold 固定）| **NOT_FEATURE_LAYER**：是 Evaluation / regime 验证 | 归 Branch 8 Evaluation（17L 决定）| MIGRATE_LATER | scripts；tests | L | §7.11 |
| `services/regime_diagnostics_dashboard.py` | regime 诊断 dashboard 数据准备 | **NOT_FEATURE_LAYER**：是 UI / dashboard 准备 | 归 Branch 9 UI（17M 决定） | MIGRATE_LATER | UI；scripts | L | 17F 不动 |
| `tests/test_features_20d.py` | features_20d boundary tests | KEEP | KEEP | KEEP | — | L | 不动 |
| `tests/test_state_label.py` | state_label boundary tests | KEEP | KEEP | KEEP | — | L | 不动 |
| `tests/test_peer_alignment_boundary.py` | 17B PR-C boundary tests | KEEP | KEEP | KEEP | — | L | 不动 |
| `tests/test_regime_features_from_scan.py` | regime_features_from_scan boundary tests | KEEP | KEEP | KEEP | — | L | 不动 |

### 5.1 关键说明

- **`peer_alignment` 已经物理归位**（17B PR-C 入 main）。这是当前唯一**已经
  完成 layer 归属**的 Feature Layer 模块；docstring 显式声明 Branch 2。
- **Feature Layer 的"feature_payload 主入口"目前由 `projection_chain_contract.build_feature_payload_from_recent_window`
  承担**。该函数与 Projection / Exclusion / Confidence orchestrator
  紧耦合；17F 阶段**不**改名 / 不**移**位置；17F 仅声明 Feature 部分归
  Feature Layer。
- **`features_20d.compute_20d_features` 是另一个 Feature Layer 入口**，
  仅由 `home_terminal_orchestrator` 使用（主页链路）。两个入口（`build_feature_payload_from_recent_window`
  + `compute_20d_features`）**不收敛**——这是 17F → 18A 之后需要解决的
  历史遗留；本轮**不**强制收敛。
- **`scanner.py` 是最危险的跨层模块**：与 UI 紧耦合 + 内部含
  `scan_bias` / `scan_confidence` / `confirmation_state`（Projection-like
  早期形态）。17F 显式声明 Feature 部分；scan_bias 由 17G 决定；UI 耦合
  由 17M 决定。
- **`primary_20day_analysis.py` / `peer_adjustment.py` / `historical_probability.py`
  虽然命名像 Feature，但实际是 Projection 候选**。17F 显式声明非
  Feature；17G 决定归属。
- **DELETE_NOW 集合为空**（与 16H §13 / 17E §15.7 一致）。

---

## 6. CORE_FEATURE 保留模块

> Feature Layer 的**核心保留模块**：以下 7 个模块（外加 `peer_alignment`）
> 是 17F 阶段无歧义归属 Feature Layer 的 active asset。

### 6.1 `services/peer_alignment.py`

| 维度 | 说明 |
|---|---|
| 为什么保留 | 17B PR-C 已迁出；docstring 显式声明 Branch 2；Projection / Exclusion 双向调用；纯函数；不读任何 system 输出 |
| 目标职责 | 提供 NVDA / SOXX / QQQ 同日 ret1 alignment summary（`alignment` / `up_support` / `down_support` / `available_peer_count` / `peer_returns` / `reasons`） |
| 是否需要改名 / 拆分 | ❌ 17F 不改名；不拆分 |
| 是否有跨层问题 | ❌ 无（17B PR-C 已修复反向 import） |
| 后续实现任务 | §13 PR-FEATURE-7：boundary tests（不 import 任何 system 模块 / 不读任何 system 输出 / 输出字段不含禁字段） |
| 当前禁止动作 | 不改 alignment 阈值（`>= 0.5` / `<= -0.5` / `>= 1.0` / `<= -1.0`）；不加新输出字段 |

### 6.2 `services/features_20d.py`

| 维度 | 说明 |
|---|---|
| 为什么保留 | 标准 20d feature 引擎；纯函数；docstring 明确接口；含 anti-lookahead 安全行为；含 ret20 / near_high20 / near_low20 / shadow_ratio 等多维 feature |
| 目标职责 | 提供 `compute_20d_features(df) -> dict[str, Any]`：从已排序 OHLCV DataFrame 计算 20d feature dict（pos20 / ret1/3/5/10/20 / vol_ratio20 / near_high20 / near_low20 / upper_shadow_ratio / lower_shadow_ratio + warning） |
| 是否需要改名 / 拆分 | ❌ 17F 不改名；可以**新增** 15d 入口（`compute_15d_features`），**不**改 20d |
| 是否有跨层问题 | ❌ 无（不读 system 输出；不 import 业务链路） |
| 后续实现任务 | §13 PR-FEATURE-2：在同一文件加 15d 入口；20d 保持不变；新增 fixture-based 测试 |
| 当前禁止动作 | 不改 20d 字段集；不改阈值；不删字段；不顺手统一两套入口（`build_feature_payload_from_recent_window` 与 `compute_20d_features` 收敛由 17F 之后 PR 决定）|

### 6.3 `services/state_label.py`

| 维度 | 说明 |
|---|---|
| 为什么保留 | 五状态 label（大涨 / 小涨 / 震荡 / 小跌 / 大跌）的**唯一** source of truth；阈值已锁；纯阈值分类，**不是**预测 |
| 目标职责 | `label_state(pct)` / `label_state_from_ratio(ratio)` / `ratio_to_pct(ratio)` 等纯函数；不引入 ML / LLM |
| 是否需要改名 / 拆分 | ❌ 不改名；不拆分 |
| 是否有跨层问题 | ❌ 无（不 import 业务链路） |
| 后续实现任务 | 17F 不动；阈值锁定（与 12 / 13 / 14 / 15 阶段保持一致）|
| 当前禁止动作 | 不改阈值；不加新 state；不加 ML / LLM 预测分支 |

### 6.4 `services/regime_features_builder.py`

| 维度 | 说明 |
|---|---|
| 为什么保留 | pure regime feature builder；docstring 显式禁 DB / CSV / network / yfinance / 交易 / v1 stub；anti-lookahead；2026 final-test cutoff 处理 |
| 目标职责 | 计算 `pos20` + `avgo_minus_soxx_20d` 两项 regime feature；返回 metadata（cutoff / source / warnings） |
| 是否需要改名 / 拆分 | ❌ 不改名；不拆分 |
| 是否有跨层问题 | ❌ 无 |
| 后续实现任务 | 17F 不动；后续如增加 15d 版本，独立函数 / 字段命名加 `_15d` 后缀 |
| 当前禁止动作 | 不改阈值；不引入 v1 stub；不复活 `continuous_smoothing*` |

### 6.5 `services/regime_labels_builder.py`

| 维度 | 说明 |
|---|---|
| 为什么保留 | pure regime labels builder；同等 read-only 契约；含 5 v1 labels + 9 raw features |
| 目标职责 | 从 OHLC DataFrame 派生 regime labels；anti-lookahead；2026 final-test refusal |
| 是否需要改名 / 拆分 | ❌ 不改名；不拆分 |
| 是否有跨层问题 | ❌ 无 |
| 后续实现任务 | 17F 不动；阈值仍是"design candidate"——validation 由 17L 处理 |
| 当前禁止动作 | 不改阈值；不引入 v1 stub |

### 6.6 `feature_builder.py`（root）

| 维度 | 说明 |
|---|---|
| 为什么保留 | OHLCV → enriched feature CSV 主入口；含 raw / adj 双轨实现；含 fallback 到 raw `Close` 的 17E §8 一致行为 |
| 目标职责 | (1) `load_price_csv` (2) `build_features` 计算 PrevClose / MA20_Volume / O_gap / H_up / L_down / C_move / V_ratio / PrevAdjClose / C_adj (3) 写出 `enriched_data/<SYMBOL>_features.csv` |
| 是否需要改名 / 拆分 | ❌ 17F 不改名；root 位置不变（与 1.0 §13 hard rule 2 一致） |
| 是否有跨层问题 | ❌ 无（不 import 业务链路） |
| 后续实现任务 | §13 PR-FEATURE-3：raw / adj price basis tagging；§13 PR-FEATURE-1：feature_payload contract helper |
| 当前禁止动作 | 不改字段集（`FEATURE_COLUMNS`）；不改 raw / adj 选择逻辑 |

### 6.7 `encoder.py`（root）

| 维度 | 说明 |
|---|---|
| 为什么保留 | 5-digit code 编码主入口（O_code / H_code / L_code / C_code / V_code / Code）；纯阈值；与 12 / 13 / 14 / 15 阶段一致 |
| 目标职责 | 把 `feature_builder` 输出 → 5-digit code DataFrame；写出 `coded_data/<SYMBOL>_coded.csv` |
| 是否需要改名 / 拆分 | ❌ 17F 不改名；root 位置不变 |
| 是否有跨层问题 | ❌ 无 |
| 后续实现任务 | §13 PR-FEATURE-1（feature_payload contract）参考 encoder 的 5-digit 字段 |
| 当前禁止动作 | 不改阈值（`encode_gap_style` / `encode_range_style` / `encode_v_ratio`）；不加 ML / LLM 编码分支 |

### 6.8 边界 helper（CORE_FEATURE 部分）

以下是**部分** Feature Layer 模块，主体跨层；§7 详谈：

- `services/projection_chain_contract.build_feature_payload_from_recent_window`
  —— Feature 部分；其他三个 helper 属下游
- `services/data_query._classify_stage` + Ret3 / Ret5 / Pos30 enrich 部分
- `services/real_regime_label_provider` 的 closure factory + builder 调用
- `matcher.py` 的 match input prep 部分
- `scanner.py` 的 5-digit code 聚合 + regime_features 调用部分

---

## 7. 跨层模块归属判断

> **重要**：本节给出 11 个跨层 / 误归类模块的归属判断；具体拆分动作由
> 17F 之后的 18A+ PR 决定，**不在 17F 执行**。

### 7.1 `scanner.py`

| 维度 | 判断 |
|---|---|
| 当前混合内容 | (1) `load_peer_coded`（peer CSV 加载，Data Layer 行为，17E §7.1）(2) `_get_nday_return` / `_get_same_day_move` / `compute_relative_strength_summary` / `compute_same_day_relative_strength_summary` / `compute_confirmation_state`（Feature Layer）(3) `compute_scan_bias_and_confidence`（**Projection-like / 早期判断**——`scan_bias = bullish / bearish / neutral` 是早期方向输出；`scan_confidence = high / medium / low` 是早期置信度输出）(4) regime_features 集成（Feature Layer）(5) `build_recent_avgo_window`（Feature Layer 切片）|
| 哪些部分属 Feature Layer | _get_nday_return / _get_same_day_move / RS summary / regime_features 集成 / build_recent_avgo_window |
| 哪些部分应迁到 Projection Layer | scan_bias / scan_confidence / confirmation_state（17G 决定是否吸收 / 删除 / 重命名为 feature signal） |
| 哪些部分属 Data Layer | 仅 `load_peer_coded` 的 CSV 读取（17E §7.1 已确认） |
| 当前阶段是否立即拆 | ❌ **不立即拆**。理由：scanner 与 UI（`app.py`）紧耦合；scan_bias / scan_confidence 是 0.x 时代的"准 prediction"输出，需要 17G 给出 Projection Layer 的最终 owner；UI 迁移属 17M。一刀拆分会跨 4 层 |
| 不拆时如何处理 | 17F 阶段：scanner.py 整体保留；docstring 不动；scan_bias 等输出仍可用；17G 给出 scan_bias 归属决定；17M 给出 UI 迁移路径 |

### 7.2 `matcher.py`

| 维度 | 判断 |
|---|---|
| 当前混合内容 | (1) `load_coded_avgo` / `build_near_match_table` / `build_next_day_match_table`（5-digit pattern 历史 match 主体——Feature Layer）(2) `RESULT_COLUMNS` 中含 `NextDate` / `NextOpen` / `NextHigh` / `NextLow` / `NextClose` / `NextVolume` / `NextOpenChange` / `NextHighMove` / `NextLowMove` / `NextCloseMove`（**未来 K 线信息——Evaluation Layer**）|
| 哪些部分属 Feature Layer | 主 match 逻辑 + match_input_preparation；不含 NextDate 字段 |
| 哪些部分应迁到 Evaluation Layer | NextDate / NextOpenChange / NextHighMove / NextLowMove / NextCloseMove / VCodeDiff —— 这些是"未来 K 线信息"；在线 inference 路径**禁止**使用（避免 future leakage）；replay / evaluation 后处理使用 |
| 哪些部分属 Data Layer | **无**（matcher 只读 Feature Layer 输出 `coded_data/<SYMBOL>_coded.csv`） |
| 当前阶段是否立即拆 | ❌ **不立即拆**。两类字段在同一个 result table 中产出；split 需要重写 RESULT_COLUMNS 与 caller |
| 不拆时如何处理 | 17F：matcher 整体保留；§13 PR-FEATURE-5 提案"matcher input vs evaluation split"作为 17L 协同候选；17L Evaluation Layer 决定 NextDate ownership |

### 7.3 `services/data_query.py`

| 维度 | 判断 |
|---|---|
| 当前混合内容 | (1) `load_symbol_data`（CSV loader，Data Layer 行为，17E §7.4）(2) `_enrich` / `_classify_stage`（衰竭风险 / 分歧 / 加速 / 启动 / 整理 / 延续——**Feature Layer 标注 / 早期 stage 分类**）(3) `Ret3` / `Ret5` / `Pos30` / `PosLabel` / `StageLabel` 派生（Feature Layer） |
| 哪些部分属 Feature Layer | `_enrich` / `_classify_stage` / Ret3 / Ret5 / Pos30 / PosLabel / StageLabel——全部 |
| 哪些部分属 Data Layer | 仅 `load_symbol_data` loader 部分（17E §7.4 已确认） |
| 哪些部分属其它层 | **无**（`_classify_stage` 输出"stage label"，是 feature 标注，不是 prediction） |
| 当前阶段是否立即拆 | ❌ **不立即拆**。UI workbench 当前依赖完整 enriched DataFrame；split 要保 UI 不变 |
| 不拆时如何处理 | 17F：data_query 整体保留；§13 PR-FEATURE-6 提案"data_query feature enrichment split"作为 17M UI Layer 协同候选；17M 决定 UI 是否改为先调 Data Layer loader、再调 Feature Layer enrich |

### 7.4 `services/real_regime_label_provider.py`

| 维度 | 判断 |
|---|---|
| 当前混合内容 | (1) `_load_market_csv`（4 个 OHLC CSV 加载，Data Layer 行为，17E §7.5）(2) closure factory + 调 `regime_labels_builder` 返回 callable —— **Feature Layer wrapper** |
| 哪些部分属 Feature Layer | factory + closure + label dict 输出 |
| 哪些部分属 Data Layer | 仅 `_load_market_csv` |
| 当前阶段是否立即拆 | ❌ **不立即拆**。closure 设计与 `projection_chain_contract` 紧耦合 |
| 不拆时如何处理 | 17F：保留；后续若做 Data Layer helper（17E §13 PR-DATA-2），real_regime_label_provider 可 reuse |

### 7.5 `services/primary_20day_analysis.py`

| 维度 | 判断 |
|---|---|
| 当前内容 | 输出 `direction = up_bias / down_bias / mixed / unknown` / `confidence = high / medium / low / unknown` / `position_label` / `stage_label` / `volume_state`——**这些是 Projection 输出**，不是 feature |
| 是否属 Feature Layer | ❌ **否**（命名误导）。"primary analysis" 行为是早期 Projection（与 scanner 的 scan_bias / scan_confidence 同类） |
| 应迁到 | Branch 3 Projection（17G 决定如何处置：(a) 整体并入 main_projection (b) 标 LEGACY_ACTIVE_DEPENDENCY (c) archive）|
| 当前阶段是否立即拆 | ❌ **不立即拆**。`projection_orchestrator_v2` 仍依赖 |
| 不拆时如何处理 | 17F：仅声明非 Feature；不动；17G 决定归属与处置 |

### 7.6 `services/projection_chain_contract.py`

| 维度 | 判断 |
|---|---|
| 当前内容（4 项） | (1) `build_feature_payload_from_recent_window` —— **Feature Layer**（pos20 / vol_ratio20 / shadow_ratio / ret1 / ret3 / ret5 / peer ret1） (2) `least_likely_from_projection` —— Projection 投影 helper (3) `excluded_state_from_result` —— Exclusion adapter（triggered_rule → 中文 state） (4) `build_prediction_log_record` —— Final Report / prediction store helper |
| 哪些部分属 Feature Layer | 仅 `build_feature_payload_from_recent_window`（含 `_ret_pct` / `_shadow_ratio` 内部 helper） |
| 哪些部分属其它层 | `least_likely_from_projection` → 17G Projection；`excluded_state_from_result` → 17H Exclusion；`build_prediction_log_record` → 17J Final Report / 17K Review |
| 当前阶段是否立即拆 | ❌ **不立即拆**。该模块是 12 / 13 / 14 / 15 阶段稳定的"shared contract helpers"；split 风险高 |
| 不拆时如何处理 | 17F：模块整体保留；docstring 不动；§13 PR-FEATURE-1 不接管该模块；只在 17F → 18A 之后视情况由 17G/17H/17J 协同决定是否拆 |

### 7.7 `services/peer_adjustment.py`

| 维度 | 判断 |
|---|---|
| 当前内容 | "stable Step 2 adjustment"——把 scanner peer summaries 转成调整字段；用于 `predict.apply_peer_adjustment` 与 V2 orchestrator |
| 是否属 Feature Layer | ❌ **否**。docstring 自称"Step 2 adjustment"——是 Projection / Bridge 内的 step 2 加工，不是原始 feature |
| 应迁到 | LEGACY_ACTIVE_DEPENDENCY / Bridge（17J 决定；与 17D §10.1 一致；当前 13 个 bridge 模块之一） |
| 当前阶段是否立即拆 | ❌ **不立即拆** |
| 不拆时如何处理 | 17F：仅声明非 Feature；17J 接管 |

### 7.8 `services/historical_probability.py`

| 维度 | 判断 |
|---|---|
| 当前内容 | 输出 up_rate / down_rate / probability / sample_count；docstring 自称"historical validator"；用于 V2 projection chain |
| 是否属 Feature Layer | ❌ **否**。"validator with up_rate / down_rate" 行为是 Projection 内部子能力 |
| 应迁到 | Branch 3 Projection（17G 决定） |
| 当前阶段是否立即拆 | ❌ **不立即拆** |
| 不拆时如何处理 | 17F：仅声明非 Feature；17G 接管 |

### 7.9 `services/five_state_margin_policy.py`

| 维度 | 判断 |
|---|---|
| 当前内容 | 五状态概率分布 → display margin policy（low_margin / watch_margin / clear_top1）；输出 metadata；不改 top1 |
| 是否属 Feature Layer | ❌ **否**。是输出 / 展示策略；输入 already projection 概率分布 |
| 应迁到 | Branch 6 Final Report 或 Branch 9 UI（17J / 17M 决定）|
| 当前阶段是否立即拆 | ❌ **不立即拆** |
| 不拆时如何处理 | 17F：声明非 Feature；17J / 17M 接管 |

### 7.10 `services/primary_bias_diagnosis.py`

| 维度 | 判断 |
|---|---|
| 当前内容 | 从 replay 结果诊断 `primary_20day_analysis` 的方向 bias；输入是历史 replay 输出，不是当次 feature |
| 是否属 Feature Layer | ❌ **否** |
| 应迁到 | Branch 8 Evaluation（17L 决定）|
| 不拆时如何处理 | 17F：声明非 Feature；17L 接管 |

### 7.11 `services/regime_validation_helper.py`

| 维度 | 判断 |
|---|---|
| 当前内容 | 4-fold validation 报告生成（gate threshold 固定）；输入是 caller 准备的 replay records |
| 是否属 Feature Layer | ❌ **否**。是 Evaluation / regime 验证（与 1.0 §8 Branch 8 一致） |
| 应迁到 | Branch 8 Evaluation（17L 决定）|
| 不拆时如何处理 | 17F：声明非 Feature；17L 接管 |

---

## 8. Feature Payload 标准化规则

> **本节定义 Feature Layer 输出的 `feature_payload` 最小结构**。该结构
> 是 Projection / Exclusion / Confidence 三系统**并行**消费的入口。

### 8.1 顶层结构

`feature_payload` 是一个 dict（或 typed dict），含以下顶层 section：

```
{
    "schema_version": "feature_payload.v1",  # 固定字符串（17F 提案；正式入注由 PR-FEATURE-1 决定）
    "metadata": {...},                        # symbol / dates / window
    "ohlcv_window": [...],                    # 标准化 K 线窗口
    "returns": {...},                         # ret1 / ret3 / ret5 / ret10
    "position": {...},                        # pos15 / pos20 / pos30
    "volume": {...},                          # volume / volume_ratio / turnover
    "candle": {...},                          # upper_shadow_ratio / lower_shadow_ratio
    "peer_alignment": {...},                  # 17B PR-C 输出形态
    "code_features": {...},                   # 5-digit code + state inputs
    "data_quality": {...},                    # missing_fields / source / stale_flag
}
```

### 8.2 字段最小要求

| 顶层 | 子字段 | 类型 | 备注 |
|---|---|---|---|
| `schema_version` | — | str | `"feature_payload.v1"`；与 17A standard payload 体例对齐 |
| `metadata` | `symbol` | str | uppercase；与 17E §8.4 一致 |
| `metadata` | `analysis_date` | str (`YYYY-MM-DD`) | 当次 feature 计算的日期 |
| `metadata` | `target_date` | str (`YYYY-MM-DD`) | 计算目标日（一般 = analysis_date 当日 close） |
| `metadata` | `data_window_days` | int | 主窗口天数（未来 15；当前 20）|
| `metadata` | `window_label` | str | `"15d"` / `"20d_legacy"` |
| `metadata` | `price_basis` | str | `"raw"` / `"adj"` / `"dual"`（详见 §10）|
| `ohlcv_window` | list of dict | list | 长度 ≤ `data_window_days`；按 Date 升序；含 `Date` / `Open` / `High` / `Low` / `Close` / `Adj Close`（如可获得）/ `Volume` |
| `returns.ret1` | float \| null | float | 1 日收益 %（基准见 `price_basis`） |
| `returns.ret3` | float \| null | float | 3 日 % |
| `returns.ret5` | float \| null | float | 5 日 % |
| `returns.ret10` | float \| null | float | 10 日 % |
| `position.pos15` | float \| null | float | 15d 范围内位置（0–100） |
| `position.pos20` | float \| null | float | 20d 范围内位置（legacy compatibility） |
| `position.pos30` | float \| null | float | 30d 范围（仅 UI workbench 当前依赖；新 payload 可不带） |
| `volume.volume` | int \| null | int | 当日 volume |
| `volume.volume_ratio` | float \| null | float | 当日 volume / MA-N |
| `volume.turnover` | float \| null | float | 成交额（如可获得） |
| `volume.amount` | float \| null | float | 同上备选字段 |
| `candle.upper_shadow_ratio` | float \| null | float | 上影线 / 总区间 |
| `candle.lower_shadow_ratio` | float \| null | float | 下影线 / 总区间 |
| `peer_alignment` | dict | dict | 完整 17B PR-C 输出（`alignment` / `up_support` / `down_support` / `available_peer_count` / `peer_returns` / `reasons`）|
| `code_features.code` | str \| null | str | 5-digit Code（O_code / H_code / L_code / C_code / V_code 拼接） |
| `code_features.o_code` ~ `v_code` | int \| null | int | 各分量 |
| `code_features.regime_label` | str \| null | str | regime label（如有；来自 `regime_labels_builder`） |
| `code_features.state_label_today` | str \| null | str | 今日**已发生** return 对应五状态分类（来自 `state_label.label_state`；**不是**预测）|
| `data_quality.missing_fields` | list[str] | list | 缺失字段名 |
| `data_quality.source` | str | str | `"local_csv"` / `"market_data_store"` / `"yfinance_live"`（live 仅在 fetch 路径） |
| `data_quality.stale_flag` | bool | bool | 是否使用了陈旧数据（如 today's bar 不完整） |

### 8.3 缺失语义

- 缺失字段一律用 `null` / `None`，**不**用 `0`（与 1.0 §8 Branch 2 一致）
- `data_quality.missing_fields` 必须列出所有缺失项
- 顶层 section 不存在时（如 peer 缺失），`peer_alignment` 仍要给出
  `{"alignment": "missing", ...}`（17B PR-C 已实现该 fallback）

### 8.4 与 standard_projection_payload.v1 的关系

- `standard_projection_payload.v1` 顶层 section 含 `feature_payload`
  （[services/standard_projection_payload.py:73](services/standard_projection_payload.py:73))
- Feature Layer **只**生成 `feature_payload` 自身；**不**生成 full
  standard payload
- standard payload 由 architecture_orchestrator（PR-F；当前暂停，归 17J）
  组装

### 8.5 不允许的 section / field

- ❌ `projection_result` / `exclusion_result` / `confidence_result` /
  `final_report`（属下游 system 输出）
- ❌ `predicted_top1` / `predicted_top2` / `state_probabilities` /
  `most_likely_state` / `most_unlikely_state`
- ❌ `triggered_rule` / `false_exclusion_risk`
- ❌ `agreement_status` / `combined_confidence`
- ❌ `combined_user_summary`
- ❌ `simulated_trade` / `trading_action` / `buy` / `sell` / `hold`
- ❌ `hard_*` / `forced_*` / `required_*`

### 8.6 现有两个 Feature 入口的关系

> 当前存在**两个** Feature payload 入口：
>
> - `services/projection_chain_contract.build_feature_payload_from_recent_window`
>   —— predict / V2 / contract_replay 链使用；20d 窗口
> - `services/features_20d.compute_20d_features` —— `home_terminal_orchestrator`
>   主页链使用；20d 窗口
>
> 二者输出**字段集大致相同**但**不严格收敛**（前者含 peer ret1，后者含
> ret10 / ret20 / near_high20 / near_low20）。
>
> 17F **不**强制收敛。收敛由 17F 之后某个 PR-FEATURE-* 决定（最早 18A）；
> 收敛前两个入口都属 CORE_FEATURE。

---

## 9. 15d window 规则

### 9.1 长期目标（与 1.0 §5 rule 9 / 07A §3.1 / §9 / 17E §9 一致）

> 系统**未来主系统标准窗口** = **15 trading days**。

### 9.2 Feature Layer 是 15d 决定层

- Feature Layer **决定**切片窗口；Data Layer 不决定（17E §9.2 已锁）
- Projection / Exclusion / Confidence **不**自行重切窗口；**只**消费
  feature_payload 中的 window
- UI **不**重算窗口；只展示

### 9.3 旧 20d / pos20 兼容字段保留

- 当前 `services/features_20d` / `services/projection_chain_contract` /
  `services/main_projection_layer` / `services/exclusion_layer` /
  `services/confidence_evaluator` 全部使用 `data_window_days = 20`
- 20d / pos20 **保留**作为 compatibility feature；payload 中以
  `position.pos20` 字段输出
- payload `metadata.window_label = "20d_legacy"`（17F 提案）

### 9.4 新 feature_payload 应明确 `data_window_days = 15`

- 新 15d 入口：`compute_15d_features`（PR-FEATURE-2 提案；本轮不实施）
- 新入口输出 `metadata.data_window_days = 15` / `window_label = "15d"`
- 新入口 + 旧入口**并存**一段时间；**不**默认切换
- 切换路径由 17G / 17H / 17I / 17J 共同决定（影响 main_projection /
  exclusion_layer / confidence_evaluator 的 window 假设）

### 9.5 不允许 Data Layer 决定 15d / 20d

- 与 17E §9.2 一致

### 9.6 不允许 Projection 层自行重切窗口

- Projection 必须从 feature_payload 读 window（与 1.0 §9 / 07A §3.1 一致）

---

## 10. raw Close / Adj Close 双轨规则

### 10.1 Data Layer 保留双轨

- 与 17E §8.2 一致：Data Layer 保留 `Close` + `Adj Close` 两列；不混

### 10.2 Feature Layer 决定哪些 feature 用 raw / adj

- **raw `Close`** 用于：
  - `O_gap = (Open - PrevClose) / PrevClose`（[feature_builder.py:81](feature_builder.py:81)）
  - `H_up = (High - Open) / Open`
  - `L_down = (Open - Low) / Open`
  - `C_move = (Close - Open) / Open`
  - `V_ratio = Volume / MA20_Volume`
  - 当日蜡烛形态 / shadow_ratio / pos20 / pos30
- **`Adj Close`** 用于：
  - `C_adj = (Adj Close - PrevAdjClose) / PrevAdjClose`（[feature_builder.py:88](feature_builder.py:88)）
  - 长期收益（ret5 / ret10 在跨派息日时建议使用 adj；当前实现混用见 §10.4）
  - split-adjusted 历史比较

### 10.3 必须在 feature_payload 中标明 price_basis

- `metadata.price_basis = "raw"` / `"adj"` / `"dual"`（17F 提案）
- 推荐 `"dual"`：raw 用于日内结构 / 短期；adj 用于跨期收益
- 不允许"不标 price_basis 而混用"

### 10.4 当前混用现状（不在 17F 修复）

- `services/projection_chain_contract.build_feature_payload_from_recent_window`
  使用 `Close`（raw）计算 ret1 / ret3 / ret5（[projection_chain_contract.py:33](services/projection_chain_contract.py:33)）
- `services/features_20d.compute_20d_features` 使用 `Close`（raw）
- `feature_builder.build_features` 在 `C_adj` 中使用 `Adj Close`，其它用 raw
- 这是 0.x 时代遗留；17F **不**修复
- §13 PR-FEATURE-3 提案"raw / adj price basis tagging"；本轮不实施

---

## 11. peer_alignment 规则

### 11.1 已经物理归位

- 17B PR-C 已迁出到 `services/peer_alignment.py`
- docstring 显式声明 Branch 2

### 11.2 属于 Feature Layer

- 与 1.0 §8 Branch 2 / 16C §3.3 / 16I §7 / 17B PR-C 一致

### 11.3 Projection / Exclusion 可读取

- 当前 `services/main_projection_layer:21` / `services/exclusion_layer:12`
  双向调用（17B PR-C 之后）
- 这是**合规调用**：peer_alignment 是 Feature Layer 资产；Projection /
  Exclusion 从 Feature Layer 读取符合 1.0 §9 数据流方向

### 11.4 peer_alignment 不属于 Projection / Exclusion / Confidence

- 不允许把 peer_alignment 模块物理放回 `services/exclusion_layer.py`
- 不允许 main_projection 反向 import exclusion_layer（17C PR-D 后已物理保证）
- 不允许 confidence_evaluator 重新计算 peer_alignment（confidence 只评价）

### 11.5 peer_alignment 后续可扩展但不能输出 prediction

- **可以**扩展为：3d / 5d alignment、different threshold、加权 alignment
- **不能**输出：方向预测、五状态判断、buy/sell/hold

---

## 12. code / scanner / matcher 规则

### 12.1 5-digit code 属 Feature Layer

- `encoder.py` / `services/data_query._enrich` 中的 stage label / scanner.py
  中的 code 聚合——全部归 Feature Layer
- 5-digit code 是 feature **encoding**，不是 prediction

### 12.2 historical match input 属 Feature Layer

- matcher 主体（`load_coded_avgo` / match table 构造）属 Feature Layer

### 12.3 NextDate outcome 属 Evaluation Layer

- matcher.py `RESULT_COLUMNS` 中的 `NextDate` / `NextOpen` / `NextHigh` /
  `NextLow` / `NextClose` / `NextOpenChange` / `NextHighMove` / `NextLowMove` /
  `NextCloseMove` / `VCodeDiff`——属 Evaluation Layer 信号
- **在线 inference 路径禁止使用**（避免 future leakage）
- replay / evaluation 后处理使用
- 17L Evaluation Layer 决定 ownership

### 12.4 scanner 的 scan_bias / scan_confidence 归属

- `compute_scan_bias_and_confidence`（[scanner.py:409](scanner.py:409)）输出
  `scan_bias = bullish / bearish / neutral` / `scan_confidence = high /
  medium / low`
- 这是 0.x 时代的"准 prediction"输出；17G 决定：
  - (a) 整体废弃（移到 LEGACY_ACTIVE_DEPENDENCY） vs
  - (b) 重命名为 feature signal（如 `peer_signal_strength`）保留 vs
  - (c) 进入 main_projection / exclusion_layer 作为输入信号
- 17F 阶段：仅声明跨层；不动

### 12.5 后续需要拆分，但本轮不拆

- 与 17D §11 / 17E §15 一致：不立即拆

---

## 13. Feature Layer 测试策略

后续 Feature Layer 实现 PR 必须满足以下测试要求：

### 13.1 fixture market data tests

- 测试用 in-tree fixture CSV 或 `tmp_path` 写入
- 不依赖 `data/<SYMBOL>.csv` / `coded_data/` / `enriched_data/`
- yfinance 必须 mock（与 17E §12.1 一致）
- 与 memory `feedback_tests_no_live_network` 一致

### 13.2 15d window tests

- 输入 ≥ 15 行 OHLCV → 输出 `pos15` / `ret10` 等 15d feature
- 输入 < 15 行 → 输出 `null` + `warnings` 含 `"insufficient_window"`
- 输入 ≥ 20 行但 `data_window_days = 15` → 只切最后 15 行

### 13.3 raw Close / Adj Close basis tests

- raw / adj 在 split / dividend 日附近**值不同**
- payload `metadata.price_basis` 显式标注
- 缺失 `Adj Close` 时 fallback 到 raw `Close`，但 `metadata.price_basis = "raw"`
  + warnings 含 `"adj_close_missing"`

### 13.4 ret / pos / volume ratio tests

- ret1 / 3 / 5 / 10 公式正确（基于已 sort 的 window）
- pos15 / pos20 在 `high == low` 时返回 `null`
- volume_ratio 在 MA-N 为 0 时返回 `null`

### 13.5 peer_alignment tests

- 全部 peer 缺失 → `alignment = "missing"` / `up_support = "unknown"` /
  `down_support = "unknown"`
- 所有 peer ≥ 1.0 → `alignment = "bullish"`
- 所有 peer ≤ -1.0 → `alignment = "bearish"`
- 17B PR-C 已有 boundary tests；17F PR-FEATURE-7 扩展

### 13.6 code encoding tests

- O_code / H_code / L_code / C_code / V_code 的阈值边界测试
- O_code 在 `O_gap == 0` 时 = 3
- 缺失 input → code = `pd.NA`
- `Code` 字段是 5 位字符串（如 `"33142"`）

### 13.7 no prediction output tests（boundary tests）

- Feature Layer 任一模块输出 dict / DataFrame 字段集合中**不含**：
  - `most_likely_state` / `most_unlikely_state` / `predicted_top1` /
    `predicted_top2` / `state_probabilities` / `direction`（指 projection
    输出方向）/ `confidence_score` / `confidence_level` / `combined_confidence` /
    `agreement_status` / `triggered_rule` / `combined_user_summary` /
    `simulated_trade` / `trading_action` / `buy` / `sell` / `hold` /
    `hard_*` / `forced_*` / `required_*`

### 13.8 no exclusion_result / confidence_result / final_report read tests

- Feature Layer 模块 source 中**不出现**：
  - `exclusion_result`（作为 input 字段）
  - `confidence_result` / `projection_result` / `final_report`（作为 input）
- AST-level grep 强制

### 13.9 no trading fields tests

- Feature Layer 模块 source 中**不出现**：
  - `trading_action` / `simulated_trade` / `buy` / `sell` / `hold` /
    `hard_*` / `forced_*` / `required_*`

### 13.10 no LLM / no UI / no future outcome tests

- 不 import `anthropic` / `openai`
- 不 import `streamlit` / `ui.*`
- 不读取 future outcome（在线 inference 路径）
- anti-lookahead：只消费 `Date <= target_date` 的行

### 13.11 baseline & regression

- 每个 PR-FEATURE-* 必须以 Step 15 baseline 为起点（**3256 passed, 10
  skipped, 0 failed, 26 warnings, 94 subtests**）
- 新增测试数显式累加到 passed
- warnings / subtests 数变化必须**显式说明**

---

## 14. Feature Layer 后续实现 PR 候选

> **本节是 PR 候选清单，本轮 17F 不执行任一项**。最早 18A 由用户单独
> 决定执行哪个、何时执行、按什么顺序执行。

| 序号 | 名称 | 性质 | 目标 | 文件范围 | 测试 | 风险 | 是否必须先做 |
|---|---|---|---|---|---|---|---|
| **PR-FEATURE-1** | feature_payload contract helper | 代码（新增 helper） | 新增 `services/feature_payload_contract.py`：定义 `FEATURE_PAYLOAD_SECTIONS` + `validate_feature_payload(payload) -> list[str]` 纯函数 validator；与 17A `standard_projection_payload.v1` 体例一致；**不**改 `build_feature_payload_from_recent_window` / `compute_20d_features` 实现 | `services/feature_payload_contract.py`（新增）+ `tests/test_feature_payload_contract.py`（新增） | focused + full pytest | L | 不强制；推荐第一项 |
| **PR-FEATURE-2** | 15d window builder | 代码（在 `features_20d.py` 同文件加 15d 入口） | 新增 `compute_15d_features(df) -> dict`；20d 入口保持不变；新入口 `metadata.data_window_days = 15`；**不**默认切换；**不**改 caller | `services/features_20d.py`（新增函数）+ `tests/test_features_15d.py`（新增） | focused + full pytest | L | 不强制 |
| **PR-FEATURE-3** | raw / adj price basis tagging | 代码（仅 metadata 字段） | 在 `build_feature_payload_from_recent_window` / `compute_20d_features` 输出顶层加 `price_basis` 字段；当前固定 `"raw"`；**不**改 ret / pos 公式；**不**改 caller 行为 | `services/projection_chain_contract.py` + `services/features_20d.py`（仅 add metadata key） | full pytest byte-stable except metadata key | L | 不强制 |
| **PR-FEATURE-4** | scanner / encoder boundary split | 代码（仅 boundary tests + docstring） | 给 `scanner.py` / `encoder.py` 加 `tests/test_scanner_feature_boundary.py` / `tests/test_encoder_boundary.py`：forbidden imports（不 import projection / exclusion / confidence / final / predict / ui / 任何 system 输出）；**不**改 scanner 业务逻辑；docstring 显式 Branch 2 标注 | tests + docstring only | focused + full pytest | L | 不强制 |
| **PR-FEATURE-5** | matcher input vs evaluation split | 代码（boundary tests + 文档说明） | 给 matcher.py 加 `tests/test_matcher_feature_boundary.py`：声明 NextDate 字段为 Evaluation 标记字段；docstring 加"NextDate fields belong to Evaluation Layer per 17L"；**不**改 RESULT_COLUMNS；**不**拆 matcher 主体 | tests + docstring only | focused + full pytest | L | 不强制；与 17L 协同 |
| **PR-FEATURE-6** | data_query feature enrichment split | 代码 | 把 `services/data_query._classify_stage` / `_enrich` / Ret / Pos / PosLabel / StageLabel 抽到 `services/data_query_feature_enrich.py`（新文件）；`data_query.load_symbol_data` 改为 thin wrapper（loader → enrich）；**保留** UI workbench 行为 | `services/data_query.py`（thin）+ `services/data_query_feature_enrich.py`（新增）+ tests | byte-equivalent UI 行为不变 | M | 不强制；与 17M UI Layer 协同 |
| **PR-FEATURE-7** | peer_alignment extension boundary tests | 代码（仅 tests） | 给 `services/peer_alignment.py` 加 `tests/test_peer_alignment_feature_boundary.py`：扩展 §13.5 + §13.7 + §13.8 + §13.10 全部 negative checks；**不**改 peer_alignment 实现 | tests only | focused + full pytest | L | 不强制 |

### 14.1 候选 PR 之间的依赖

- PR-FEATURE-1 → PR-FEATURE-2 / PR-FEATURE-3：先有 contract，再统一 metadata
- PR-FEATURE-4 / PR-FEATURE-5 / PR-FEATURE-7：互不依赖；可任意顺序
- PR-FEATURE-6：大改；推荐放最后；与 17M UI Plan 协同
- 任何**代码** PR-FEATURE-* 都依赖 **17F 已入 main**（前置条件）

### 14.2 候选 PR 都不能做的事

- ❌ 不改 `services/peer_alignment.py` 实现（仅 boundary tests）
- ❌ 不改 `state_label` 阈值
- ❌ 不改 `regime_features_builder` / `regime_labels_builder` 算法
- ❌ 不改 `encoder.py` 阈值
- ❌ 不动 `feature_builder.py` raw / adj 选择逻辑（仅加 metadata）
- ❌ 不动 `scanner.py` scan_bias / scan_confidence（17G 决定）
- ❌ 不动 `services/primary_20day_analysis` / `peer_adjustment` /
  `historical_probability`（属 Projection / Bridge；17G / 17J 决定）
- ❌ 不动 main_projection / exclusion_layer / confidence_evaluator /
  final_decision（17G/H/I/J 处理）
- ❌ 不动 UI（17M 处理）
- ❌ 不引入 trading / hard / forced / required
- ❌ 不复活 `continuous_smoothing*` / `archive/legacy/root_stubs/*`
- ❌ 不修改 `.gitignore`
- ❌ 不处理 `avgo_agent.db`
- ❌ 不处理 handoff / logs / DB backup / `.claude/worktrees/`

---

## 15. 与 Projection / Exclusion 的交接

### 15.1 数据流方向（与 1.0 §9 / 07E §9 一致）

```
Data Layer
    │
    ▼
Feature Layer  ──────────►  feature_payload
    │                              │
    │                              │ （并行读，互相不读）
    ├──► Projection (Branch 3)     │ Exclusion (Branch 4)     Confidence (Branch 5)
    │     最可能                   │ 最不可能                  评价二者
```

### 15.2 Projection 读 feature_payload

- Projection（Branch 3）从 feature_payload 读取：
  - `ohlcv_window` / `returns` / `position` / `volume` / `candle` /
    `peer_alignment` / `code_features` / `metadata`
- 输出 `projection_result`（与 07A §9 一致）
- **不**读 exclusion_result / confidence_result / final_report

### 15.3 Exclusion 读 feature_payload

- Exclusion（Branch 4）从 feature_payload 读取：
  - 同上字段集
  - 含 `peer_alignment` 用于 peer 非确认信号
- 输出 `exclusion_result`（与 07B §9 一致）
- **不**读 projection_result / confidence_result / final_report

### 15.4 Projection 不读 Exclusion / Exclusion 不读 Projection

- 与 07A §3.2 / 07B §3.2 / 17C PR-D（main_projection 去 `exclusion_result`
  形参） 一致

### 15.5 Confidence 之后读 Projection + Exclusion，不直接改 Feature

- Confidence（Branch 5）输入：`projection_result`（只读）+
  `exclusion_result`（只读）+ feature_payload（只读）+ offline calibration
- 输出 `confidence_result`（与 07C §9 一致）
- **不**改 Feature；**不**回灌 feature_payload

### 15.6 Final Report / Review / Evaluation / UI 不与 Feature Layer 直接交互

- Final Report 只读 projection / exclusion / confidence
- Review / Evaluation 读取 prediction_store + outcome_store
- UI 只读 final_report / review_record / evaluation_report
- Feature Layer **不**为这些层定制字段

---

## 16. 清场 / 隔离建议

> **本节按 16H 决策表 8 个标签给出 Feature Layer 范畴内的清场建议**。
> 本轮**不**执行任何清场动作。

### 16.1 KEEP（Feature Layer CORE）

- `services/peer_alignment.py`
- `services/features_20d.py`
- `services/state_label.py`
- `services/regime_features_builder.py`
- `services/regime_labels_builder.py`
- `feature_builder.py`（root）
- `encoder.py`（root）

### 16.2 KEEP_PARTIAL（混合层；保留但需协同 split）

- `services/projection_chain_contract.py`（Feature 部分）
- `services/data_query.py`（enrich 部分）
- `services/real_regime_label_provider.py`（factory 部分）
- `matcher.py`（match 主体部分）
- `scanner.py`（Feature 部分）

### 16.3 MIGRATE_LATER（17G ~ 17M 接管）

- `services/primary_20day_analysis.py` → 17G Projection
- `services/peer_adjustment.py` → 17J Final Report / Bridge
- `services/historical_probability.py` → 17G Projection
- `services/five_state_margin_policy.py` → 17J Final Report / 17M UI
- `services/primary_bias_diagnosis.py` → 17L Evaluation
- `services/regime_validation_helper.py` → 17L Evaluation
- `services/regime_diagnostics_dashboard.py` → 17M UI
- scanner.py 的 `scan_bias` / `scan_confidence` / `confirmation_state` →
  17G Projection（决定 archive vs 保留 vs 合并）
- matcher.py 的 NextDate 字段 → 17L Evaluation

### 16.4 MOVE_OUTSIDE_REPO（17F 不执行）

- `coded_data/*` / `enriched_data/*` / `match_results/*` → 已 untracked；
  保留本地状态（与 17E §15.4 一致）

### 16.5 ARCHIVE_IN_REPO

- 无 Feature Layer 范畴的 archive 候选（与 16H / 17E §15.5 一致）

### 16.6 QUARANTINE

- 无 Feature Layer 范畴的 quarantine 候选（CORE_FEATURE 状态健康）

### 16.7 DELETE_NOW

- **空**（与 16H §13 / 17E §15.7 一致）

### 16.8 DELETE_LATER

- 无 Feature Layer 范畴的 delete 候选（17F 阶段）

### 16.9 MIGRATE_CALLER_FIRST

- 无（CORE_FEATURE 模块不是 Bridge）
- KEEP_PARTIAL 模块的 caller 迁移由对应层 Plan（17G ~ 17M）决定

### 16.10 DEEP_AUDIT_REQUIRED

- 无 Feature Layer 范畴的 UNKNOWN（16G §11 列出的 10 项 UNKNOWN 中，归
  Feature Layer 的：`primary_bias_diagnosis` 已声明非 Feature；
  `five_state_margin_policy` 已声明非 Feature；`primary_20day_analysis`
  已声明非 Feature）

> **重申**：任何文件删除 / 移动 / archive 必须等 16H 规则 + 17D §11 + 用户
> 单独确认。17F 仅给出**建议**，**不**执行。

---

## 17. 不允许事项

**17F 起，Feature Layer 范畴内**严格禁止：

- ❌ 不改代码（无 `.py` 文件被修改；本轮 0 修改）
- ❌ 不跑数据
- ❌ 不跑 replay / 不跑 validation / 不跑 historical evaluation
- ❌ 不改 DB / 不改 DB schema
- ❌ 不迁 Projection / Exclusion / Confidence / Final Report / Review /
  Evaluation / UI（各层 Plan 自负其责）
- ❌ 不接 trading / 不输出 buy / sell / hold / hard / forced / required
- ❌ 不进入 3R-5 / 3R-6（1.0 §12 / 16I §15 / 17D §11 / 17E §16 / 本轮再次重申）
- ❌ 不启动任何代码 PR（PR-FEATURE-* 候选要等 18A）
- ❌ 不修改 `.gitignore`
- ❌ 不处理 `avgo_agent.db`（含 backup）
- ❌ 不处理 handoff / logs / DB backup / `.claude/worktrees/`
- ❌ 不复活 `continuous_smoothing*` / `archive/legacy/root_stubs/*` /
  promotion 三模块
- ❌ 不污染 2026-01-01 之后 final holdout
- ❌ 不借 17F 顺手做 Data / Projection / Exclusion / Confidence / Final
  Report / Review / Evaluation / UI 范畴改动
- ❌ 不继续 PR-E confidence key 对齐（与 17D §9 一致）
- ❌ 不启动 UI / bridge / orchestrator 任务（与 17D §10 一致）

> 与 17D §11 / 17E §16 一致；本轮再次锁定。

---

## 18. 推荐下一步

> **首选**：**Step 17G：Projection Layer Rebuild Plan**

理由（与 17D §12 / 17E §17 一致 + 17F 实战观察）：

- Feature Layer 计划（17F）已就位
- 数据流方向是 Data → Feature → **{Projection, Exclusion, Confidence}** →
  Final Report → ...（1.0 §9 / 16C §3）
- 三系统并行；按九分支编号顺序，下一层是 Projection（Branch 3）
- **17G 的工作量大**：17G 必须接管
  - `services/main_projection_layer.py`（17C PR-D 已修复 `exclusion_result`
    形参；17G 进一步处置 schema 对齐 / window 决策）
  - `services/primary_20day_analysis.py`（17F §7.5 声明非 Feature；17G 决定
    归属 / archive / merge）
  - `services/historical_probability.py`（17F §7.8 声明非 Feature；17G 决定）
  - `scanner.py` 的 `scan_bias` / `scan_confidence` / `confirmation_state`
    （17F §7.1 / §12.4 跨层；17G 决定）
  - `services/projection_chain_contract.least_likely_from_projection`
    （17F §7.6 跨层；17G 接管投影 helper）
  - `services/projection_orchestrator` / `services/projection_orchestrator_v2`
    （bridge / orchestration；17G + 17J 共同决定）
- 17G 入 main 之前，**不**允许在 Projection Layer 范畴开任何代码 PR

**不推荐**：

- 不推荐跳到 17H / 17I / 17J / 17K / 17L / 17M（必须先有 Projection Plan）
- 不推荐借 17F / 17G 做代码改动（与 17D §11 一致）
- 不推荐重启 16I PR-E / PR-F / PR-G / PR-H（必须等对应层 Plan）
- 不推荐解锁 3R-5 / 3R-6（1.0 §12 7 项前提仍未全部满足）
- 不推荐立刻做 PR-FEATURE-* 任一项（与 17F 协同更合算）

> **明确**：本轮 17F 推荐的下一步**只有一个候选**——17G Projection Layer
> Rebuild Plan。

---

## 19. 严守边界

本轮 Step 17F **只**写 Feature Layer Rebuild Plan：

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
- ❌ 未启动任何代码 PR（PR-FEATURE-* 候选要等 18A）
- ❌ 未继续 PR-E confidence key 对齐
- ❌ 未启动 UI / bridge / orchestrator 任务
- ❌ 未做任何局部 patch
- ❌ 未 commit / 未 push（按本轮指令）

唯一新增文件：[tasks/record_17f_feature_layer_rebuild_plan.md](tasks/record_17f_feature_layer_rebuild_plan.md)（本文件）。

后续修改路径：任何对 §3 职责定义 / §4 禁止事项 / §5 inventory / §6
CORE_FEATURE / §7 跨层判断 / §8 feature_payload 标准化 / §9 15d window /
§10 raw vs adj / §11 peer_alignment / §12 code / scanner / matcher / §13
测试策略 / §14 PR 候选 / §15 与 Projection / Exclusion 交接 / §16 清场建议 /
§17 禁止事项 / §18 下一步 的调整，都必须**显式更新本文件**；同时检查是否
需要同步更新 1.0 / 16C / 16D / 17D / 17E 与 17G（17G 入 main 后）。
