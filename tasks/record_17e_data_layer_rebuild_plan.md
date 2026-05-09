# 17E记录：Data Layer Rebuild Plan

> 本记录是 **Step 17E：Data Layer 重建计划**——九分支按层重建中的
> **第一层**。1.0 canonical / 16A blueprint / 16B inventory / 16C target
> dataflow & contract decision / 16D isolation & quarantine plan / 16E
> core chain refactor plan / 16F no-patching principle / 16G full module
> decomposition standup / 16H repository clearing decision table / 16I
> core chain rebuild execution plan / 17A PR-B standard payload skeleton /
> 17B PR-C peer_alignment 抽公共模块 / 17C PR-D main_projection 去
> `exclusion_result` 形参 / 17D layer-by-layer rebuild governance 已全部
> 入 main（main 最新 commit `77777d4`）。
>
> 本轮**只**写计划文档：未改业务代码、未新增测试、未删除文件、未移动
> 文件、未修改 `.gitignore`、未处理 handoff、未处理 logs / DB backup /
> `.claude/worktrees/`、**未处理 `avgo_agent.db`**、未跑 replay /
> validation / historical evaluation、未写 DB / 未改 DB schema、未默认
> 迁移 `run_predict` 到 V2、未接 trading、未输出 buy / sell / hold /
> hard / forced / required、未进入 3R-5 / 3R-6、未启动任何代码 PR、
> 未 commit / 未 push。
>
> 唯一 deliverable：本文件。
>
> **本记录优先级**：与 17F ~ 17M 各层 Plan 同级；与 1.0 / 16A / 16C /
> 16D / 16F / 16I / 17D 协同。冲突仲裁路径与 1.0 §14 / 17D §13 一致：
> 旧 records 若与 17E 在 Data Layer 范畴冲突，**以 17E 为准**。

---

## 1. Step 17E 目的

把九分支按层重建从治理（17D）推进到**第一层（Data Layer）的具体重建
计划**。

**本轮只回答**：

- Data Layer 当前长什么样（模块 inventory）
- Data Layer 目标长什么样（保留 / 迁移 / 隔离 / 删除候选）
- Data Layer 与上下游的边界（外部市场数据 ↑；Feature Layer ↓）
- Data Layer 数据标准化规则（OHLCV + Adj Close 双轨 / Date / symbol）
- Data Layer 时间窗口、来源、DB / cache / artifact 规则
- Data Layer 后续可能的代码 PR 候选（**不**执行）
- 与 Feature Layer 的交接

**本轮不回答**：

- 不写 Feature Layer 计划（17F）
- 不写 Projection / Exclusion / Confidence / Final Report / Review /
  Evaluation / UI 计划
- 不开任何代码 PR（最早 18A）
- 不动 `avgo_agent.db`、`.gitignore`、handoff、logs、DB backup、worktrees

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
| main 最新 commit | `77777d4` |
| worktree 唯一 deliberate untracked | `.claude/handoffs/task_089_post_pr_cleanup.md` |
| 战略阶段 | 从 governance（17D）→ **Data Layer plan（17E 本轮）** |
| 3R-5 / 3R-6 | ❌ 仍然不允许进入 |
| 第一个按层实现 PR（18A）| ❌ 必须等 17E 入 main 后才能讨论 |

**17D §6 PR 准入规则提醒**：

- 任何代码 PR 必须绑定九分支某一层 + 引用对应层 Plan §
- 17E 入 main 后，Data Layer 范畴的 PR 才**有资格**被讨论
- 但 17E 本身**不**自动批准任何 PR；18A 由用户单独决定

---

## 3. Data Layer 职责定义

**Data Layer（Branch 1）只回答一件事**：

> **"从外部市场源 / 本地 CSV / DB 读到一份标准化、可被 Feature Layer
> 消费的 OHLCV 数据"。**

### 3.1 只做的事

- 读取 AVGO / NVDA / SOXX / QQQ 的 OHLCV（Open / High / Low / Close /
  Adj Close / Volume）
- 读取本地 CSV 文件（`data/<SYMBOL>.csv`）
- 读取本地 DB（`avgo_agent.db` — local-only ignored；见 §11）
- 数据缓存 / 数据存储接口（`market_data_store` 提供 sqlite-backed
  raw_prices / features / coded_bars 入口）
- 数据完整性检查（缺日 / 缺列 / 重复 / 类型错位）
- symbol / Date / OHLCV / Adj Close / Volume 标准化（详见 §8）
- 提供"足够长"的历史窗口数据，供下游 Feature Layer 自行切片

### 3.2 不做的事（与 1.0 §8 Branch 1 / 16A §5 一致）

- ❌ 不预测（任何 state / direction / probability）
- ❌ 不做五状态判断（大涨 / 小涨 / 横盘 / 小跌 / 大跌）
- ❌ 不做 feature 计算（ret1 / ret3 / ret5 / pos / volume_ratio / O_gap /
  H_up / L_down / C_move / V_ratio 等——这些归 Feature Layer）
- ❌ 不做 exclusion / 不做 confidence / 不做 final report / 不做 review /
  不做 evaluation / 不做 UI 展示
- ❌ 不调用 LLM
- ❌ 不调用 Projection / Exclusion / Confidence / Final Report 任一系统
- ❌ 不读取 future outcome（在线 inference 路径）
- ❌ 不直接接交易接口（broker / order / position）
- ❌ 不污染 2026-01-01 之后 final holdout（与 07A §3.2 / 07B §3.2 / 07C
  §3.2 / 07D §3.2 一致——Data Layer 提供数据，但**不**为 holdout 区间做
  特殊抑制；holdout 抑制由 Feature / Projection / Confidence / Evaluation
  各自实现）

### 3.3 输入 / 输出（白名单）

**输入**：

- yfinance Ticker history（仅在 `data_fetcher.update_local_csv` /
  `download_full_history` 路径中）
- 本地 CSV：`data/<SYMBOL>.csv`（raw OHLCV）
- 本地 CSV：`enriched_data/<SYMBOL>_features.csv`（Feature Layer 写入；
  Data Layer **只读**）
- 本地 CSV：`coded_data/<SYMBOL>_coded.csv`（Feature Layer encoding
  下游写入；Data Layer **只读**）
- 本地 sqlite：`avgo_agent.db` 三张表（`raw_prices` / `features` /
  `coded_bars`）

**输出**：

- standardized OHLCV `pd.DataFrame`（`Date` 字符串 `YYYY-MM-DD` 或
  pandas datetime；`Open / High / Low / Close / Adj Close / Volume`）
- 任何 schema 不含 trading / projection / exclusion / confidence /
  final_report / review / evaluation 字段

---

## 4. Data Layer 禁止事项

Data Layer **永久禁止**输出 / 引入以下任一：

| 类别 | 禁止项 | 锚点 |
|---|---|---|
| 预测结论 | `predicted_top1` / `predicted_top2` / `most_likely_state` / `state_probabilities` | 1.0 §8 Branch 1; 07A §3.2 |
| 五状态判断 | 大涨 / 小涨 / 横盘 / 小跌 / 大跌 | 同上 |
| 交易动作 | `buy` / `sell` / `hold` / `simulated_trade` / `trading_action` | 1.0 §6.1 / §13 hard rule 1 |
| 强制语义 | `hard` / `forced` / `required` / `_PROTECTION_LAYER_CONNECTED` | 12E X1..X5 / 1.0 §6 |
| LLM 调用 | `anthropic` / `openai` / 任何文本生成 SDK | 1.0 §13 hard rule 1 / 5 |
| UI 调用 | `streamlit` / 任何 ui/ 模块 import | 1.0 §13 hard rule 3 |
| 下游系统调用 | import `services.main_projection_layer` / `services.exclusion_layer` / `services.confidence_evaluator` / `services.final_decision` / `predict.py` | 1.0 §9 数据流方向；07A/B/C/D §3.1 |
| DB schema 改动 | `CREATE TABLE` / `ALTER TABLE` 在 17E 阶段不允许（schema 自身已稳定，见 §11） | 16H §6 / 17E §11 |
| 直接运行 replay | 调用 `scripts/run_contract_replay*` / `scripts/build_03_replay_report.py` 等 | 17D §11 |
| 直接改变 feature / projection 结果 | 任何"为了下游能 work"而往输出里加非市场数据字段 | 1.0 §8 Branch 1 |

---

## 5. 当前 Data Layer 模块 inventory

> **范围说明**：本表覆盖 root 数据脚本 + `services/` 中市场数据 / cache /
> store 相关模块 + 跨层模块（scanner / encoder / matcher / feature_builder
> 在 §7 单独判断）。"Data Layer-relevant"中**所有**模块按当前实际行为归
> CORE_DATA / DATA_INFRA / FEATURE_LAYER（迁出）/ NOT_DATA_LAYER（误归类）
> / OUT_OF_SCOPE。

| module_path | current_role | current_status | target_role | keep / migrate / quarantine / delete | active_callers | risk | next_action |
|---|---|---|---|---|---|---|---|
| `data_fetcher.py` | yfinance 下载 + 本地 CSV 写入 + 同日 bar 完整性检查 | KEEP_ACTIVE（root，无业务依赖） | **CORE_DATA**：唯一外部市场数据入口 | KEEP | `run_pipeline.py:6` 调 `batch_update_all`；scripts 不直接 import | L | §6.1 显式 KEEP；§13 PR-DATA-1 写 boundary tests（forbidden import + no-prediction-output）禁止再扩 |
| `services/market_data_store.py` | sqlite-backed `raw_prices` / `features` / `coded_bars` ingest + load | KEEP_ACTIVE（独立 sqlite store；schema 稳定） | **CORE_DATA**：DB 持久化层 | KEEP | tests + `services/replay_record_wiring.py` + 部分 scripts | L | §6.2 显式 KEEP；§11 锁 schema；§13 PR-DATA-4 显式 cleanup public API（不改 schema） |
| `services/data_query.py` | UI workbench data loader + **`_classify_stage` 规则分类**（属 Feature Layer 行为） | MIXED：CSV 加载 OK，但 `_classify_stage` / `Ret3` / `Ret5` / `Pos30` / `PosLabel` / `StageLabel` enrich **不属于** Data Layer | **CORE_DATA（部分）+ MIGRATE_TO_FEATURE（部分）** | KEEP（loader 部分）+ MIGRATE 17F（enrich/classify 部分） | UI workbench tab + tests | M | §7.4 显式跨层；§13 PR-DATA-3 仅清 loader；`_classify_stage` 等留给 17F |
| `services/record_reader.py` | **markdown 系统设计 record 读取**——不是市场数据读取 | **NOT_DATA_LAYER**（与 Data Layer 无关，命名误导） | INFRA / DOC TOOLING（属 9 分支之外的开发辅助） | KEEP（不在 Data Layer 范围） | 文档查询脚本 / 调试 | L | §5.1 显式说明误归类；17E **不**纳入 Data Layer 范畴；下次 inventory 可移到 `infra_*` / `tools_*` 命名 |
| `services/real_regime_label_provider.py` | 读 4 个 OHLC CSV → 构造 closure → 调 `regime_labels_builder` | MIXED：CSV loading 是 Data Layer 行为，但**返回 regime label 字典**属 Feature Layer | **CORE_DATA（CSV loader 部分）+ MIGRATE_TO_FEATURE（builder 调用部分）** | KEEP（loader）+ MIGRATE 17F（label 输出 wrapper） | `services/projection_chain_contract.py` + tests | M | §7.5 显式跨层；17E 不动；17F 决定 split |
| `services/log_store.py` | 通用日志写入（不仅市场数据） | OUT_OF_SCOPE | INFRA（监控 / 日志） | KEEP（不在 Data Layer 范畴） | 多模块 | L | 不动 |
| `services/memory_store.py` | review / lesson 记忆持久化 | OUT_OF_SCOPE | Branch 7 Review & Learning | 17K 处理 | review_orchestrator | L | 不动 |
| `services/prediction_store.py` | prediction snapshot 写入（含 projection / exclusion / confidence 全字段） | OUT_OF_SCOPE | Branch 6/7/8 共享 outcome store | 17J/K/L 共同决定 | predict / orchestrator chain | L | 不动 |
| `services/projection_record_store.py` | projection record 写入 | OUT_OF_SCOPE | Branch 6 | 17J 处理 | predict / contract_replay_writer | L | 不动 |
| `services/review_store.py` | review record 持久化 | OUT_OF_SCOPE | Branch 7 | 17K 处理 | review_orchestrator | L | 不动 |
| `scanner.py` | **MIXED**：peer CSV 加载 + 5-digit code 聚合 + 相对强度 + scan_bias / scan_confidence 输出 | MIXED；**主要部分属 Feature Layer**（含 scan_bias 是结构判断的早期版本） | **MIGRATE_TO_FEATURE**（绝大部分）+ DATA_LAYER（仅 CSV 加载） | MIGRATE_LATER（17F 决定） | `app.py` (UI) + tests | M | §7.1 显式跨层；17E 不动；17F 决定拆分 |
| `encoder.py` | feature CSV → coded CSV（O_code / H_code / L_code / C_code / V_code / Code）| **FEATURE_LAYER**（不是 Data Layer） | Branch 2 Feature Layer | KEEP（17F 接管） | `run_pipeline.py:7` + tests | L | §7.2 显式归 Feature Layer |
| `matcher.py` | coded CSV → 历史 match table | **FEATURE_LAYER / EVALUATION 边界**（历史 match 是 Feature Layer 信号；NextDate match 接近 Evaluation） | Branch 2 Feature Layer（主体）+ Branch 8 Evaluation（部分 NextDate 表）| MIGRATE_LATER | `run_pipeline.py:8` + scanner | M | §7.3 显式跨层；17E 不动；17F / 17L 共同决定 |
| `feature_builder.py` | OHLCV CSV → enriched feature CSV（PrevClose / MA20_Volume / O_gap / H_up / L_down / C_move / V_ratio / PrevAdjClose / C_adj） | **FEATURE_LAYER**（不是 Data Layer） | Branch 2 Feature Layer | KEEP（17F 接管） | `run_pipeline.py:7` + tests | L | §7.2 显式归 Feature Layer |
| `services/regime_features_builder.py` | pure regime feature builder（pos20 / avgo_minus_soxx_20d） | **FEATURE_LAYER**（pure；docstring 显式声明 no DB / CSV / network） | Branch 2 | 17F 接管 | scanner / agent | L | 不动 |
| `services/regime_labels_builder.py` | pure regime labels builder | **FEATURE_LAYER** | Branch 2 | 17F 接管 | real_regime_label_provider | L | 不动 |
| `run_pipeline.py` (root) | data_fetcher → feature_builder → encoder → matcher 串行 | INFRA / 编排 | INFRA（pipeline runner，不属任一 branch） | KEEP（pipeline 工具） | manual / scripts | L | 不动；17E 不重构 |
| `data/` 目录（CSV files） | raw OHLCV 本地缓存 | DATA_ARTIFACT | 保留为本地 fixture / 缓存 | KEEP（不 tracked） | data_fetcher / 各 loader | L | 不动；不进 17E 范围 |
| `coded_data/` 目录 | encoder 输出 | DATA_ARTIFACT (Feature Layer) | 保留 | KEEP（不 tracked） | matcher / scanner | L | 17F 决定 |
| `enriched_data/` 目录 | feature_builder 输出 | DATA_ARTIFACT (Feature Layer) | 保留 | KEEP（不 tracked） | encoder / scripts | L | 17F 决定 |
| `match_results/` 目录 | matcher 输出 | DATA_ARTIFACT (Feature/Evaluation 边界) | 保留 | KEEP（不 tracked） | scripts | L | 17F / 17L 决定 |
| `avgo_agent.db` | sqlite store（market_data_store / replay_record / projection_record / review_store 等多端写入） | local-only ignored（16H §5 校正确认；`.gitignore:11` 命中）| **不 tracked**；schema 在 17E 不改 | KEEP（local-only） | market_data_store / replay_record_wiring / 多端 | L | 不处理；17E §11 锁 schema |

### 5.1 关键说明

- **`services/record_reader.py` 不属于 Data Layer**：尽管命名含 "record"，
  实际只读 `records/<NN>_*.md`（系统设计 markdown）。17E **不**纳入 Data
  Layer 范畴；后续按文档 / infra 处理。
- **`services/data_query.py` 是混合层**：CSV 加载是 Data Layer 行为；
  但内部 `_classify_stage` / `Ret3` / `Ret5` / `Pos30` / `PosLabel` /
  `StageLabel` 全部是 Feature Layer 计算。17E 仅声明跨层；17F 决定 split。
- **scanner / encoder / matcher / feature_builder 都不是 Data Layer
  主体**：1.0 §13 hard rule 2 把 scanner/matcher/encoder 称作"硬规则
  层"——这是**结构判断 / 编码 / 匹配**逻辑，不是数据读取。它们的"读
  CSV"动作可以视为 Data Layer 接口的 caller，但模块本体归 Feature Layer
  （详见 §7）。
- **DELETE_NOW 集合为空**（与 16H §13 一致）。

---

## 6. CORE_DATA 保留模块

Data Layer 的**核心保留模块**只有以下两个：

### 6.1 `data_fetcher.py`

| 维度 | 说明 |
|---|---|
| 为什么保留 | 系统**唯一**外部市场数据入口（yfinance）；与 4 个 symbol + 起始日期 (`2016-05-18`) 显式绑定；内部已含 same-day bar 完整性检查（`_has_complete_bar`）防止半截 bar 写入 |
| 目标职责 | (1) yfinance 下载 (2) `data/<SYMBOL>.csv` 写入 (3) `clean_price_data` 标准化（`Date` / `Open` / `High` / `Low` / `Close` / `Adj Close` / `Volume`） |
| 是否需要改名 / 拆分 | ❌ 17E 不改名；不拆分。改名 = 业务无价值；拆分 = 增加 import 改动面 |
| 是否有跨层问题 | ❌ 无。`data_fetcher.py` 不 import 任何 services / ui / projection 链路模块；纯外部 IO |
| 后续实现任务 | §13 PR-DATA-1：boundary tests（forbidden imports + no-prediction-output + 强制 mock yfinance）；不改逻辑 |
| 当前禁止动作 | 不改 `SYMBOLS` 字典；不改 `KEEP_COLUMNS`；不改 `update_local_csv` 行为；不在 17E 加 retry / cache layer |

### 6.2 `services/market_data_store.py`

| 维度 | 说明 |
|---|---|
| 为什么保留 | sqlite-backed 持久化层；schema 已在 12 / 13 / 14 / 15 阶段稳定（`raw_prices` / `features` / `coded_bars` 三表 + `data_health`）；带 `db_path` 参数支持 tmp_path 测试 |
| 目标职责 | (1) `init_database` (2) `ingest_*_csv` (3) `load_*` (4) `refresh_data_health` (5) `get_summary`——纯 sqlite 读写 |
| 是否需要改名 / 拆分 | ❌ 17E 不改名；不拆分 |
| 是否有跨层问题 | ❌ 无。public API 不 import 任何 services / ui / projection 链路 |
| 后续实现任务 | §13 PR-DATA-4：public API surface cleanup（仅文档化 + 移除已 deprecated 的内部 helper，**不**改 schema、**不**改 public API 行为）；schema 锁定（§11） |
| 当前禁止动作 | 不改 schema；不加新表；不改 `_RAW_PRICES_COLUMNS` / `_FEATURES_COLUMNS` / `_CODED_BARS_COLUMNS` / `_DATA_HEALTH_COLUMNS`；不在 17E 加新 ingest 入口 |

### 6.3 边界 helper 候选（CORE_DATA 之外）

以下两个模块是**部分 Data Layer**，但主体跨层；17E **不**作为 CORE_DATA
保留；§7 单独处置：

- `services/data_query.py`：CSV loader 部分属 Data Layer；`_classify_stage`
  + 派生字段属 Feature Layer
- `services/real_regime_label_provider.py`：CSV loader 部分属 Data Layer；
  返回 regime label 字典属 Feature Layer

---

## 7. 跨层模块归属判断

> **重要**：本节四个模块（scanner / encoder / matcher / feature_builder）
> 是 1.0 §13 hard rule 2 锁定的"scanner / matcher / encoder 是硬规则层，
> 优先保留"对象。1.0 §13 表中明确：
>
> > 1.0 起 scanner / matcher / encoder 数据读取部分归 Branch 1，特征
> > 推导部分归 Branch 2，结构判断部分归 Branch 3。
>
> 17E 在此基础上**只**给出"哪些部分属 Data Layer / 不属 Data Layer"的
> 判断；具体拆分动作由 17F / 17G 共同决定，**不在 17E 执行**。

### 7.1 `scanner.py`

| 维度 | 判断 |
|---|---|
| 当前混合内容 | (1) `load_peer_coded`（peer CSV 加载，Data Layer 行为）(2) 5-digit code 聚合 / 相对强度（Feature Layer 行为）(3) `scan_bias` / `scan_confidence` / `confirmation_state`（**结构判断 + 早期 confidence 输出**——属 Projection / Confidence 早期形态，非 Data Layer 也非纯 Feature） |
| 哪些部分属 Data Layer | 仅 `load_peer_coded`（和等价 CSV 读取 helpers） |
| 哪些部分应迁到 Feature Layer | 5-digit code 聚合 / 相对强度计算 / `relative_strength_*_summary` |
| 哪些部分应迁到其它层 | `scan_bias` / `scan_confidence` / `confirmation_state` 输出语义接近 Projection / Confidence 早期版本——由 17G / 17I 决定是否保留作为 Feature 派生信号 vs. 拆解到对应层 |
| 当前阶段是否立即拆 | ❌ **不立即拆**。理由：scanner 与 UI（`app.py`）紧耦合；拆分 = 大面积 PR。17E 仅声明跨层。17F 给出 Feature Layer 提案；17G 给出 Projection 视角提案；最终由 17J Final Report Layer Plan / Bridge 处置部分综合决定 |
| 不拆时如何处理 | 保留现状；在 17F / 17G 中 cross-reference scanner.py 的"哪段功能属哪一层" |

### 7.2 `encoder.py` + `feature_builder.py`

| 维度 | 判断 |
|---|---|
| 当前混合内容 | encoder.py 全部是 5-digit code 编码逻辑（O_code / H_code / L_code / C_code / V_code / Code）；feature_builder.py 全部是 PrevClose / MA20_Volume / O_gap / H_up / L_down / C_move / V_ratio / C_adj 等派生 |
| 哪些部分属 Data Layer | **无**。两者**不**直接读 yfinance；只读本地 CSV 后做 feature 计算 |
| 哪些部分应迁到 Feature Layer | **全部**（这是 1.0 §13 hard rule 2 中的"特征推导部分"和"结构判断部分"的早期实现） |
| 当前阶段是否立即拆 | ❌ **不立即拆**。两者已经物理独立；只是命名上不在 `services/feature_*` 命名空间。17F 决定是否归位（迁到 `services/` + 拆 sub-helpers），还是保留 root 文件名 |
| 不拆时如何处理 | 17F Feature Layer Plan 把 encoder + feature_builder 显式列入 Feature Layer；root 位置不变 |

### 7.3 `matcher.py`

| 维度 | 判断 |
|---|---|
| 当前混合内容 | (1) coded CSV 加载（与 encoder.py 输出对称；属 Feature Layer 读侧）(2) **历史 NextDate 5-day match 表**（既是 Feature 信号又是 Evaluation 数据 source） |
| 哪些部分属 Data Layer | **无**（matcher.py 只读 `coded_data/AVGO_coded.csv`，那是 Feature Layer 输出） |
| 哪些部分应迁到 Feature Layer | 主 match 逻辑 |
| 哪些部分应迁到 Evaluation Layer | NextDate / NextOpenChange / NextHighMove / NextLowMove / NextCloseMove / VCodeDiff 这些"未来 K 线信息"—— Evaluation Layer 后处理时使用；在线 inference 不能用这些字段（避免 future leakage） |
| 当前阶段是否立即拆 | ❌ **不立即拆**。17F 给出 Feature Layer 视角的归属；17L Evaluation Layer Plan 决定 NextDate 表的 ownership |
| 不拆时如何处理 | 17F / 17L 各自 cross-reference matcher.py 的归属判断 |

### 7.4 `services/data_query.py`

| 维度 | 判断 |
|---|---|
| 当前混合内容 | (1) `load_symbol_data`（CSV loader，Data Layer 行为）(2) `_classify_stage`（衰竭风险 / 分歧 / 加速 / 启动 / 整理 / 延续——Feature Layer 标注 / Projection 早期）(3) `Ret3` / `Ret5` / `Pos30` / `PosLabel` / `StageLabel` enrich（Feature Layer） |
| 哪些部分属 Data Layer | 仅 `load_symbol_data` 中"读 `coded_data/<SYMBOL>_coded.csv` + 切窗口 + 返回原始字段"部分 |
| 哪些部分应迁到 Feature Layer | `_enrich` / `_classify_stage` / `Ret3` / `Ret5` / `Pos30` / `PosLabel` / `StageLabel`——全部 |
| 当前阶段是否立即拆 | ❌ **不立即拆**。UI workbench tab 当前依赖完整 enriched DataFrame；17F 决定 split 时如何保 UI 行为不变 |
| 不拆时如何处理 | 17F Feature Layer Plan 把 `_classify_stage` 等派生字段显式列入 Feature Layer；17M UI Layer Plan 决定 UI 是否改为先调 Data Layer loader、再调 Feature Layer enrich |

### 7.5 `services/real_regime_label_provider.py`

| 维度 | 判断 |
|---|---|
| 当前混合内容 | (1) `_load_market_csv`（4 个 OHLC CSV 加载，Data Layer 行为；docstring 显式 read-only）(2) closure factory + `regime_labels_builder` 调用（Feature Layer wrapper） |
| 哪些部分属 Data Layer | 仅 `_load_market_csv` |
| 哪些部分应迁到 Feature Layer | factory + `build_real_regime_label_provider` 返回的 callable（生成 regime label dict） |
| 当前阶段是否立即拆 | ❌ **不立即拆**。real_regime_label_provider 的 closure 设计与 `projection_chain_contract` 紧耦合；split 风险高 |
| 不拆时如何处理 | 17F Feature Layer Plan 把 closure 部分显式列入 Feature Layer；Data Layer 视 `_load_market_csv` 为"loader 子能力"；后续如果做 Data Layer 抽象 helper（§13 PR-DATA-2），real_regime_label_provider 可以 reuse 该 helper |

---

## 8. 数据标准化规则

Data Layer 输出**最小标准数据格式**：

### 8.1 必备字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `Date` | str (`YYYY-MM-DD`) 或 pandas `datetime64[ns]` | 日期；接口层**必须明确**使用哪一种（见 §8.3） |
| `Open` | float | 当日 raw 开盘价 |
| `High` | float | 当日 raw 最高价 |
| `Low` | float | 当日 raw 最低价 |
| `Close` | float | 当日 raw 收盘价（**未** dividend-adjusted） |
| `Adj Close` | float | 当日 adjusted 收盘价（dividend-adjusted） |
| `Volume` | int64 | 当日成交量；**保留**（与 1.0 §5 rule 10 一致） |

### 8.2 raw Close vs Adj Close 双轨规则

> **不混 raw Close 和 adjusted Close**——这是 Data Layer 的硬契约。

- `Close` = raw close（用于 `O_gap` / `PrevClose` / 日内结构计算——仅
  Feature Layer 使用 raw 字段）
- `Adj Close` = dividend-adjusted close（用于跨日收益率计算——仅 Feature
  Layer 使用 adj 字段；具体在 `feature_builder.build_features` 中体现为
  `C_adj = (Adj Close - PrevAdjClose) / PrevAdjClose`）
- Data Layer **保留**两条轨道；不允许 Data Layer 自行选择"用哪个 Close"
- O_gap 等基于 raw `PrevClose` 的规则**留给 Feature Layer**；Data Layer
  只保证两个字段同时存在（如可获得）+ 类型可用
- 如果 yfinance 某 symbol 没有返回 `Adj Close`，Data Layer 输出**允许**
  缺失该列；下游 Feature Layer 必须显式 fallback 到 raw `Close`（已在
  `feature_builder.py:73-74` 实现）

### 8.3 接口契约

| 调用 | Date 类型 | 说明 |
|---|---|---|
| `data_fetcher.clean_price_data` 输出 | str (`YYYY-MM-DD`) | 写入 CSV 前已 `dt.strftime` |
| 本地 CSV 读取 → loader 返回 | 一般 str；具体由 caller 决定（`feature_builder.load_price_csv` 转 `pd.to_datetime`；`data_query.load_symbol_data` 转 `pd.to_datetime`） |
| `market_data_store.load_*` | str (`YYYY-MM-DD`) | sqlite 列类型 `TEXT` |

> **17E 不强制统一**。如果 17F Feature Layer 决定统一到 datetime，17F
> 自己处理；Data Layer 只承诺"两种之一"。

### 8.4 symbol 标准化

- symbol 一律 **uppercase**（`AVGO` / `NVDA` / `SOXX` / `QQQ`）
- Data Layer 不接受 lowercase / mixed case
- `data_fetcher.SYMBOLS` 已经全部 uppercase；保持
- `services/data_query.SUPPORTED_SYMBOLS` 已经全部 uppercase；保持
- `services/market_data_store` 的 sqlite `symbol` 列存 uppercase 字符串；
  caller 负责 normalize

### 8.5 Data Layer 不做的字段层规则

- ❌ Data Layer **不**计算 `PrevClose`（Feature Layer 做）
- ❌ Data Layer **不**计算 `O_gap` / `H_up` / `L_down` / `C_move` /
  `V_ratio` / `MA20_Volume` / `C_adj`（Feature Layer 做）
- ❌ Data Layer **不**做"5-digit code"（Feature Layer 内 encoder 做）
- ❌ Data Layer **不**做 stage classification（Feature Layer 内
  `_classify_stage` 做；17F 处理）

---

## 9. 时间窗口规则

### 9.1 长期目标（与 1.0 §5 rule 9 / 07A §3.1 / §9 一致）

> 系统**未来主系统标准窗口** = **15 trading days**。

### 9.2 Data Layer 不决定业务窗口

- Data Layer **只**提供"足够长"的历史数据（自 2016-05-18 起，由
  `data_fetcher.SYMBOLS` 锁定）
- Data Layer **不**决定 15d / 20d 切片
- Feature Layer 决定切片窗口（当前 20d 为 legacy / compatibility；与 1.0
  §5 rule 9 一致）

### 9.3 当前 20d 不能在 Data Layer 改

- 当前 `services/projection_chain_contract.build_feature_payload_from_recent_window`
  使用 20d 窗口
- `services/main_projection_layer` / `services/exclusion_layer` / `services/confidence_evaluator`
  通过 metadata 标 `data_window_days = 20` + `legacy_window`
- **Data Layer 不能强改 20d → 15d**；这是 17F / 17G / 17H / 17I 共同决定的
  Feature 窗口决策

### 9.4 Data Layer 提供的"窗口"接口

- `services/data_query.load_symbol_data(symbol, window, fields, ...)`
  支持任意 window；window=0 返回全部
- `services/market_data_store.load_*` 支持 `start_date` / `end_date`
- 这些 API 是**纯切片**；不带"业务 15d / 20d"语义

---

## 10. 数据来源规则

### 10.1 yfinance（live fetch）

- **唯一入口**：`data_fetcher.fetch_history_from_yahoo` /
  `download_full_history` / `update_local_csv`
- **谁在调**：`run_pipeline.py:6 batch_update_all`（manual / cron）；
  scripts 不直接 import
- **测试 / inference 路径**：**不**直接调用 live fetch
- **memory `feedback_tests_no_live_network` 锚点**：测试中必须 mock
  yfinance；**不**允许 live download；本规则在 §12 测试策略再次重申

### 10.2 本地 CSV

- `data/<SYMBOL>.csv` 是 raw OHLCV 主源（Data Layer 读 / 写）
- `enriched_data/<SYMBOL>_features.csv` 是 Feature Layer 输出
- `coded_data/<SYMBOL>_coded.csv` 是 Feature Layer encoding 输出
- `data/` 不在 git tracked；CI / 用户本地需先跑 `data_fetcher.batch_update_all`

### 10.3 cached data / sqlite

- `avgo_agent.db` 是 local-only ignored
- `services/market_data_store.ingest_*_csv` 是 CSV → sqlite 的
  "promotion" 入口
- 三表 (`raw_prices` / `features` / `coded_bars`) schema 锁定（§11）

### 10.4 offline mode

- **Data Layer 必须可在 offline 模式工作**（除 `data_fetcher` 主动 fetch
  外）
- 所有 loader（`data_query` / `market_data_store.load_*` /
  `real_regime_label_provider._load_market_csv`）**仅**读本地资源；不发起
  网络
- Test 强制 offline（mock yfinance + tmp_path sqlite + fixture CSV）

### 10.5 replay / evaluation / final holdout

- replay / evaluation **必须**使用 frozen data snapshot
- Data Layer **不**在 replay 路径中触发 live fetch
- 2026-01-01 之后 final holdout 范围由 Feature / Confidence / Evaluation
  各自隔离；Data Layer 提供数据但**不**自行做 holdout 抑制
- 与 1.0 §5 rule 8 / 07A §3.2 一致

### 10.6 不允许接交易接口

- ❌ Data Layer **永久禁止** import broker / order / position / trade
  routing 客户端
- 即使外部 SDK 提供"行情 + 交易"双能力，Data Layer 也只允许行情接口
  （隔离 SDK surface）

---

## 11. DB / cache / artifact 规则

### 11.1 `avgo_agent.db`

- **local-only ignored**（`.gitignore:11`）
- **不 tracked**（与 16H §5 校正一致）
- 17E **不**改 schema
- 17E **不**做 schema migration（含 `ALTER TABLE` / 新加列 / 改类型 / 新加表）
- 17E **不**做 backup / move / archive

### 11.2 raw logs / replay outputs / DB backup

- 与 1.0 §11 / 14K `.gitignore` 6 行 pattern + 16H 决策表一致
- raw logs / replay outputs / DB backup **不进 repo**
- 17E **不**改 `.gitignore`
- 17E **不**处理 `avgo_agent.db.backup_*`（16H 决策；17E 不复议）
- 长期保留：仅 markdown summary / manifest / archive 进 repo（必要时）；
  raw `.csv` / `.json` / `.jsonl` / `_run.log` 留本地或 archive

### 11.3 Data Layer 实现时不带回 raw artifact

- 18A 起的 PR-DATA-* 实现时**禁止**：
  - 把 `data/<SYMBOL>.csv` track 进 git
  - 把 `coded_data/` / `enriched_data/` / `match_results/` 任一文件 track
  - 把 `avgo_agent.db` 任一 backup track
  - 新建 `_run.log` / `_dump.json` / `replay_*.csv` 在 repo 根
- §13 PR-DATA-5 显式做 guard tests（命令行 / hook / unit 检查）

---

## 12. Data Layer 测试策略

后续 Data Layer 实现 PR 必须满足以下测试要求：

### 12.1 no live network tests（绝对要求）

- 与 memory `feedback_tests_no_live_network` 一致
- 任何 Data Layer 测试**不**触发实际 yfinance 下载
- yfinance 必须被 mock；HTTP 必须被 mock
- 推荐使用 `pytest.MonkeyPatch.setattr(yf.Ticker, "history", ...)` 或
  fixture-level mock

### 12.2 fixture CSV tests

- 测试用 in-tree fixture CSV（`tests/data/<SYMBOL>_fixture.csv` 或
  `tmp_path` 写入）
- 不依赖 `data/<SYMBOL>.csv` 是否存在（CI 不一定有）
- 不依赖 `coded_data/` / `enriched_data/`

### 12.3 missing column tests

- 删除 `Adj Close` 列 → loader 仍能 load（可选列）
- 删除 `Volume` 列 → loader 必须 reject（必备列）
- 删除 `Date` / `Open` / `High` / `Low` / `Close` 任一 → loader 必须 reject

### 12.4 symbol normalization tests

- 输入 `avgo` / `Avgo` / ` AVGO ` → 接受 / 标准化 / 拒绝（按 §8.4 规则）
- non-supported symbol（例如 `MSFT`）→ raise `ValueError`

### 12.5 Date parse tests

- 接受 `YYYY-MM-DD` 字符串 / pandas `datetime64[ns]`
- 拒绝 invalid date（如 `2025-13-45`）
- 重复日期 → drop_duplicates；保留 last（已在 `data_fetcher.clean_price_data:59`
  实现）

### 12.6 OHLCV + Adj Close presence tests

- 完整 7 列存在时输出 byte-stable
- `Adj Close` 缺失时 `feature_builder.build_features` fallback 到 `Close`
  （已在 [feature_builder.py:73-74](feature_builder.py:73) 实现）

### 12.7 raw Close / Adj Close 双轨测试

- raw `Close` 用于 `O_gap` / `PrevClose`（验证 `feature_builder.build_features`
  的 `O_gap = (Open - PrevClose) / PrevClose`，**不**用 `Adj Close`）
- `Adj Close` 用于 `C_adj`（验证 `C_adj = (Adj Close - PrevAdjClose) /
  PrevAdjClose`）
- 验证 raw `PrevClose` 与 `PrevAdjClose` 在不同日序列下值不同

### 12.8 no prediction output tests（boundary tests）

- `data_fetcher.py` / `services/market_data_store.py` / 任何 Data Layer
  loader 的输出 dict / DataFrame 字段集合中**不含**：
  - `most_likely_state` / `most_unlikely_state` / `predicted_top1` /
    `confidence_*` / `final_*` / `simulated_trade` / `trading_action` /
    `buy` / `sell` / `hold` / `hard_*` / `forced_*` / `required_*`
- 模块 source 中**不 import**：
  - `services.main_projection_layer` / `services.exclusion_layer` /
    `services.confidence_evaluator` / `services.final_decision` /
    `predict.py` / `services.predict_legacy_adapter` /
    `services.predict_legacy_v2_bridge` / `services.projection_orchestrator*` /
    `services.home_terminal_orchestrator` / `services.review_orchestrator` /
    任何 ui/ 模块
- 模块 source 中**不调** LLM SDK（`anthropic` / `openai`）

### 12.9 baseline & regression

- 每个 PR-DATA-* 必须以 Step 15 baseline 为起点（**3256 passed, 10
  skipped, 0 failed, 26 warnings, 94 subtests**）
- 新增测试数显式累加到 passed
- warnings / subtests 数变化必须**显式说明**

---

## 13. Data Layer 后续实现 PR 候选

> **本节是 PR 候选清单，本轮 17E 不执行任一项**。最早 18A 由用户单独
> 决定执行哪个、何时执行、按什么顺序执行。

| 序号 | 名称 | 性质 | 目标 | 文件范围 | 测试 | 风险 | 是否必须先做 |
|---|---|---|---|---|---|---|---|
| **PR-DATA-1** | Data source inventory + no-live-network boundary tests | 测试 only | 给 `data_fetcher.py` 加显式 boundary tests：forbidden imports + no-prediction-output + 强制 mock yfinance；不改 `data_fetcher.py` 逻辑 | `tests/test_data_fetcher_boundary.py`（新增） | focused + full pytest | L | 推荐第一项；不强制 |
| **PR-DATA-2** | standard market data schema helper | 代码（新增 helper） | 新增 `services/standard_market_data_payload.py`：定义 `STANDARD_MARKET_DATA_FIELDS = ("Date", "Open", "High", "Low", "Close", "Adj Close", "Volume")` + `validate_standard_market_data(df) -> list[str]` 纯函数 validator；与 17A `standard_projection_payload.v1` 体例一致；**不**改任何业务模块 | `services/standard_market_data_payload.py`（新增）+ `tests/test_standard_market_data_payload.py`（新增） | focused + full pytest | L | 不强制；可作为 17F Feature Layer 的依赖 |
| **PR-DATA-3** | local CSV loader normalization | 代码（**仅** loader 部分） | 把 `services/data_query.load_symbol_data` 中"读 CSV + 切窗口 + 返回原始字段"部分抽出为 `services/local_csv_loader.py`（或类似命名）；`load_symbol_data` 改为 thin wrapper（loader → enrich）；**保留** `_classify_stage` 等 enrich 逻辑给 17F 处理 | `services/local_csv_loader.py`（新增）+ `services/data_query.py`（thin wrapper） | byte-equivalent + UI 行为不变 | M | 不强制；与 17F Feature Layer Plan 协同 |
| **PR-DATA-4** | market_data_store API surface cleanup | 代码（**仅**文档化 + 内部 helper 清理） | `services/market_data_store.py`：public API 加 type hints + docstring 升级；移除 module-private 已 dead 的 helper（如有）；**不**改 schema、**不**改 public API 行为；**不**改 ingest / load 函数签名 | `services/market_data_store.py`（编辑） | full pytest byte-stable | L | 不强制 |
| **PR-DATA-5** | raw artifact / DB backup guard tests | 测试 only | 加 `tests/test_data_layer_repo_guard.py`：扫 git index，断言 `data/*.csv` / `coded_data/*` / `enriched_data/*` / `match_results/*` / `avgo_agent.db` / `avgo_agent.db.backup_*` / `*_run.log` 全部**未** tracked；与 1.0 §11 / 14K / 16H 一致 | `tests/test_data_layer_repo_guard.py`（新增） | focused + full pytest | L | 不强制；可在 18A 之后任意位置加 |

### 13.1 候选 PR 之间的依赖

- PR-DATA-1 / PR-DATA-4 / PR-DATA-5 互不依赖；可任意顺序
- PR-DATA-2 → PR-DATA-3：PR-DATA-3 中 `local_csv_loader` 可调
  PR-DATA-2 的 validator
- 任何**代码** PR-DATA-* 都依赖 **17E 已入 main**（前置条件）

### 13.2 候选 PR 都不能做的事

- ❌ 不改 schema（`market_data_store` 三表 / sqlite migration）
- ❌ 不动 `data_fetcher.SYMBOLS` / `KEEP_COLUMNS` / `clean_price_data` 行为
- ❌ 不动 `feature_builder` / `encoder` / `matcher`（属 Feature Layer，17F 处理）
- ❌ 不动 `scanner.py`（17F / 17G 共同决定）
- ❌ 不动 UI（17M 处理）
- ❌ 不动 confidence / projection / exclusion / final report
- ❌ 不引入 trading / hard / forced / required
- ❌ 不复活 `continuous_smoothing*` / `archive/legacy/root_stubs/*`
- ❌ 不修改 `.gitignore`
- ❌ 不处理 `avgo_agent.db`（含 backup）
- ❌ 不处理 handoff / logs / DB backup / `.claude/worktrees/`

---

## 14. 与 Feature Layer 的交接

### 14.1 Data Layer → Feature Layer 输出契约

> Data Layer 输出 standardized market data DataFrame（§8 字段）；
> Feature Layer 接收并计算所有派生字段。

### 14.2 Feature Layer 接收后会做的事（**不**在 17E 实现）

| 派生字段 | 当前实现位置 | Data Layer 角色 |
|---|---|---|
| `PrevClose` / `PrevAdjClose` | `feature_builder.build_features` | 提供 raw `Close` + `Adj Close` |
| `MA20_Volume` | `feature_builder.build_features` | 提供 `Volume` |
| `O_gap` / `H_up` / `L_down` / `C_move` / `V_ratio` | `feature_builder.build_features` | 提供 OHLCV |
| `C_adj` | `feature_builder.build_features` | 提供 `Adj Close` + `PrevAdjClose` |
| `O_code` / `H_code` / `L_code` / `C_code` / `V_code` / `Code`（5-digit） | `encoder.encode_dataframe` | 提供完整 OHLCV + features（间接） |
| 15d window 切片（未来标准） | 17F 决定 | 提供"足够长"的历史 |
| 20d window 切片（legacy） | `services/projection_chain_contract` | 同上 |
| `pos15` / `pos20` | `services/regime_features_builder` | 提供 OHLCV |
| `peer_alignment` | `services/peer_alignment`（17B PR-C 已迁出） | 提供各 symbol OHLCV |
| `ret1` / `ret3` / `ret5` / `ret10` | 待 17F 整理（当前散落在 scanner / data_query / regime_features_builder / projection_chain_contract）| 提供 `Adj Close` / `Close` |
| stage label（衰竭风险 / 分歧 / 加速 / 启动 / 整理 / 延续） | `services/data_query._classify_stage` | **不**做 |

### 14.3 Data Layer **不**负责

- ❌ 不算任何派生 feature
- ❌ 不做窗口切片决策
- ❌ 不做 stage / regime / state 标注
- ❌ 不做 peer alignment 计算（这是 Feature Layer 的资产；17B PR-C 已落
  `services/peer_alignment.py`；与 1.0 §8 Branch 2 / 16C §3.3 一致）

---

## 15. 清场 / 隔离建议

> **本节按 16H 决策表 8 个标签 (`KEEP` / `MOVE_OUTSIDE_REPO` /
> `ARCHIVE_IN_REPO` / `QUARANTINE` / `DELETE_NOW` / `DELETE_LATER` /
> `MIGRATE_CALLER_FIRST` / `DEEP_AUDIT_REQUIRED`) 给出 Data Layer 范畴
> 内的清场建议**。本轮**不**执行任何清场动作。

### 15.1 KEEP（Data Layer CORE）

- `data_fetcher.py`
- `services/market_data_store.py`

### 15.2 KEEP_PARTIAL（混合层；保留但与 17F 协同 split）

- `services/data_query.py`（loader 保留；enrich 由 17F 处理）
- `services/real_regime_label_provider.py`（loader 保留；factory 由 17F 处理）

### 15.3 MIGRATE_LATER（17F 接管；17E 不动）

- `feature_builder.py`
- `encoder.py`
- `scanner.py`
- `matcher.py`
- `services/regime_features_builder.py`
- `services/regime_labels_builder.py`

### 15.4 MOVE_OUTSIDE_REPO（17E 不执行）

- raw `data/*.csv` / `coded_data/*` / `enriched_data/*` / `match_results/*`
  → 已 untracked；保留本地状态
- `avgo_agent.db` / `avgo_agent.db.backup_*` → 16H §5 / §6；本轮不动
- `.claude/worktrees/` → 14K `.gitignore`；harness 自动管理

### 15.5 ARCHIVE_IN_REPO

- 无 Data Layer 范畴的 archive 候选（与 16H 一致）

### 15.6 QUARANTINE

- 无 Data Layer 范畴的 quarantine 候选（CORE_DATA / DATA_INFRA 状态健康）

### 15.7 DELETE_NOW

- **空**（与 16H §13 一致）

### 15.8 DELETE_LATER

- 无 Data Layer 范畴的 delete 候选（17E 阶段无废弃 Data Layer 模块）

### 15.9 MIGRATE_CALLER_FIRST

- 无（Data Layer 模块不是 Bridge / 不需要 caller 迁移）

### 15.10 DEEP_AUDIT_REQUIRED

- 无 Data Layer 范畴的 UNKNOWN（16G §11 列出的 10 项 UNKNOWN 中，无一项
  是 Data Layer 范畴）

> **重申**：任何文件删除 / 移动 / archive 必须等 16H 规则 + 17D §11 + 用户
> 单独确认。17E 仅给出**建议**，**不**执行。

---

## 16. 不允许事项

**17E 起，Data Layer 范畴内**严格禁止：

- ❌ 不改代码（无 `.py` 文件被修改；本轮 0 修改）
- ❌ 不跑数据（不 yfinance fetch / 不 CSV 重建 / 不 sqlite ingest）
- ❌ 不跑 replay / 不跑 validation / 不跑 historical evaluation
- ❌ 不改 DB / 不改 DB schema
- ❌ 不迁 Feature / Projection / Confidence / Final Report / Review /
  Evaluation / UI（各层 Plan 自负其责）
- ❌ 不接 trading / 不输出 buy / sell / hold / hard / forced / required
- ❌ 不进入 3R-5 / 3R-6（1.0 §12 / 16I §15 / 17D §11 / 本轮再次重申）
- ❌ 不启动任何代码 PR（PR-DATA-* 候选要等 18A）
- ❌ 不修改 `.gitignore`
- ❌ 不处理 `avgo_agent.db`（含 backup）
- ❌ 不处理 handoff / logs / DB backup / `.claude/worktrees/`
- ❌ 不复活 `continuous_smoothing*` / `archive/legacy/root_stubs/*` /
  promotion 三模块
- ❌ 不污染 2026-01-01 之后 final holdout
- ❌ 不借 17E 顺手做 Feature / Projection 范畴改动

> 与 17D §11 一致；本轮再次锁定。

---

## 17. 推荐下一步

> **首选**：**Step 17F：Feature Layer Rebuild Plan**

理由（与 17D §12 一致 + 17E 实战观察）：

- Data Layer 计划（17E）已就位
- 数据流方向是 Data → **Feature** → {Projection, Exclusion, Confidence}
  → Final Report → ...（1.0 §9 / 16C §3）
- **17F 的工作量大于 17E**：17F 必须接管
  - encoder.py（5-digit code）
  - feature_builder.py（OHLCV → 派生 features）
  - scanner.py 中"5-digit code 聚合 / 相对强度"部分（剩余部分由 17G/17J
    处理）
  - matcher.py 主体（NextDate 部分由 17L 协同）
  - services/data_query.py 的 `_classify_stage` 等 enrich 字段
  - services/real_regime_label_provider.py 的 closure factory
  - services/regime_features_builder.py / regime_labels_builder.py
  - services/peer_alignment.py（17B PR-C 已迁出，17F 显式接管）
- 17F 入 main 之前，**不**允许在 Feature Layer 范畴开任何代码 PR
- 17F 写完后，PR-DATA-* 仍可以并行启动（无依赖）；但建议先让 17F 入 main
  再考虑 Data / Feature 跨层 PR

**不推荐**：

- 不推荐跳到 17G / 17H / 17I / 17J / 17K / 17L / 17M（必须先有 Feature
  Layer Plan）
- 不推荐借 17E / 17F 做代码改动（与 17D §11 一致）
- 不推荐重启 16I PR-E / PR-F / PR-G / PR-H（必须等对应层 Plan）
- 不推荐解锁 3R-5 / 3R-6（1.0 §12 7 项前提仍未全部满足）
- 不推荐立刻做 PR-DATA-1 / PR-DATA-5（不强制；与 17F 协同更合算）

> **明确**：本轮 17E 推荐的下一步**只有一个候选**——17F Feature Layer
> Rebuild Plan。

---

## 18. 严守边界

本轮 Step 17E **只**写 Data Layer Rebuild Plan：

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
- ❌ 未启动任何代码 PR（PR-DATA-* 候选要等 18A）
- ❌ 未做任何局部 patch
- ❌ 未 commit / 未 push（按本轮指令）

唯一新增文件：[tasks/record_17e_data_layer_rebuild_plan.md](tasks/record_17e_data_layer_rebuild_plan.md)（本文件）。

后续修改路径：任何对 §3 职责定义 / §4 禁止事项 / §5 inventory / §6
CORE_DATA / §7 跨层判断 / §8 标准化规则 / §9 时间窗口 / §10 数据来源 /
§11 DB / cache / artifact / §12 测试策略 / §13 PR 候选 / §14 与 Feature
Layer 交接 / §15 清场建议 / §16 禁止事项 / §17 下一步 的调整，都必须
**显式更新本文件**；同时检查是否需要同步更新 1.0 / 16C / 16D / 17D 与
17F（17F 入 main 后）。
