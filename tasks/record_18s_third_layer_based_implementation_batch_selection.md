# 18S记录：Third Layer-Based Implementation Batch Selection

> 本记录是 **Step 18S：第三批按层实现 PR 选择**——第二批 8 件套
> （18K / 18L / 18M / 18N / 18O / 18P / 18Q / 18R）全部入 main 之后的
> 第三批选择决定。
>
> 本轮**只**选择第三批实现 PR，**不**写代码。1.0 canonical / 16A
> blueprint / 16B inventory / 16C target dataflow / 16D isolation / 16E
> core chain refactor / 16F no-patching / 16G full module decomposition /
> 16H repository clearing / 16I core chain rebuild / 17A ~ 17C / 17D
> layer-by-layer rebuild governance / 17E ~ 17M 九层 plan / 18A first
> batch selection / 18B ~ 18I 第一批 contract helper / 18J second batch
> selection / 18K ~ 18R 第二批 producer adapter + Confidence schema 修
> 复 + Final Report passthrough hardening + Inspect tab + Review
> warning-only 已全部入 main（main 最新 commit `761a5b8`）。
>
> 本轮**只**写 selection 文档：未改业务代码、未新增测试、未删除文件、
> 未移动文件、未修改 `.gitignore`、未处理 handoff、未处理 logs / DB
> backup / `.claude/worktrees/`、**未处理 `avgo_agent.db`**、未跑 replay /
> validation / historical evaluation / holdout / calibration、未写 DB /
> 未改 DB schema、未默认迁移 `run_predict` 到 V2、未接 trading、未输出
> buy / sell / hold / hard / forced / required、未进入 3R-5 / 3R-6、
> 未启动任何代码 PR、未实现 architecture_orchestrator、未删 Bridge、
> 未迁 Predict tab、未 archive legacy、未 commit / 未 push。
>
> 唯一 deliverable：本文件。
>
> **本记录优先级**：与 17D ~ 17M / 18A / 18J 同级。冲突仲裁路径与 1.0
> §14 / 17D §13 / 18A §16 / 18J §17 一致：旧 records 若与 18S 冲突，
> **以 18S 为准**。

---

## 1. Step 18S 目的

第二批 8 件套已经全部入 main：第一批 contract helper + 第二批 producer
adapter + Confidence schema adapter 修复 (`agreement_status` unknown 根因) +
Final Report non-mutation hardening + Inspect tab 第一刀 + Review
`_apply_briefing_caution` warning-only（关键违规修复）。现在进入第三批选
择决定。

> **本轮只选择第三批 PR，不写代码。**

具体目标——回答：

- 第三批从哪条线开始
- 是否开始**清离 / quarantine 的前置检查**
- 是否启动 **architecture_orchestrator**
- 是否启动 **Evaluation / holdout 边界**
- 是否启动 **Data Layer 第一刀**
- 为什么仍**不**直接进入 Predict tab 迁移 / Bridge 删除 / 3R-5 / 3R-6
- 为什么仍**不**直接跑 replay / holdout / calibration

**本文件性质**：selection（选择决定），不是 design 也不是 impl。
设计与执行落地由 18T / 18U / 18V / 18W / 18X / 18Y / 18Z 各 batch 分别
给出，每个 batch 单独 commit / 单独 review。

---

## 2. 当前前置条件

| 项 | 状态 |
|---|---|
| 1.0 canonical principles | ✅ commit `5c209bb` |
| 16A architecture reset blueprint | ✅ commit `9b98ad5` |
| 16B / 16C / 16D / 16E / 16F / 16G / 16H / 16I | ✅ 全部入 main |
| 17A / 17B / 17C 三个 PR-B / PR-C / PR-D | ✅ 全部入 main |
| 17D layer-by-layer rebuild governance | ✅ commit `77777d4` |
| 17E ~ 17M 九层 Rebuild Plan | ✅ 全部入 main |
| 18A First Batch Selection | ✅ commit `30c7ac0` |
| 18B PR-FEATURE-1 | ✅ commit `3c9df83` |
| 18C PR-PROJ-1 | ✅ commit `f719d71` |
| 18D PR-EXCL-1 | ✅ commit `bc22937` |
| 18E PR-CONF-1 | ✅ commit `cce8f0e` |
| 18F PR-FINAL-1 | ✅ commit `32c2aa8` |
| 18G PR-REVIEW-1 | ✅ commit `3c12acb` |
| 18H PR-EVAL-1 | ✅ commit `49b3683` |
| 18I PR-UI-1 | ✅ commit `428c4ae` |
| 18J Second Batch Selection | ✅ commit `9182d0b` |
| 18K PR-FEATURE-2 (feature_payload producer adapter) | ✅ commit `8ec2053` |
| 18L PR-PROJ-2 (projection_result legacy-to-standard adapter) | ✅ commit `e8c68f9` |
| 18M PR-EXCL-2 (exclusion_result legacy-to-standard adapter) | ✅ commit `17070e1` |
| 18N PR-CONF-2 (confidence_evaluator schema adapter) | ✅ commit `cdaaf63` |
| 18O PR-CONF-3 (explicit `calibration_context = {"ready": False}`) | ✅ commit `2f1e1b1` |
| 18P PR-FINAL-2 (final_decision passthrough / non-mutation hardening) | ✅ commit `42c93f2` |
| 18Q PR-UI-2 (Inspect tab standard payload status section) | ✅ commit `248e857` |
| 18R PR-REVIEW-2 (`_apply_briefing_caution` warning-only) | ✅ commit `761a5b8` |
| main 最新 commit | `761a5b8` |
| 第二批完成度 | **8/8** |
| full pytest baseline（18R 入 main 后） | **4006 passed, 10 skipped, 0 failed, 26 warnings, 1711 subtests passed** |
| worktree 唯一 deliberate untracked | `.claude/handoffs/task_089_post_pr_cleanup.md` |
| 战略阶段 | 从第二批（8/8）→ **第三批实现 PR 选择（18S 本轮）** |
| 3R-5 / 3R-6 | ❌ 仍然不允许进入 |
| 第三批实现 PR | ❌ 必须等 18S 入 main + 用户单独确认后才能启动 |

**关键修复事实**（第二批已完成）：

- ✅ `agreement_status` 长期 unknown 的根因已被 PR-CONF-2 schema adapter +
  PR-CONF-3 explicit `ready=False` 修复
- ✅ `_apply_briefing_caution` 已不再当次修改 `final_confidence`（PR-REVIEW-2
  修复了 1.0 §13 / 06 §6/§7 / 07A-D 锁定的关键违反点）
- ✅ 生产端已有 Feature / Projection / Exclusion legacy-to-standard
  adapters
- ✅ Confidence 已能读 standard + legacy fallback
- ✅ Final Report non-mutation 已加固，dead helpers 已删除
- ✅ UI 已有 Inspect tab standard payload status 第一刀

**关键未完成事实**：

- ❌ 主链尚未完全切到 standard `architecture_orchestrator`
- ❌ Predict tab 尚未迁移
- ❌ Bridge 尚未清理
- ❌ replay / holdout / calibration 尚未启动
- ❌ 真实 calibration table 未接入
- ❌ Branch 1 Data Layer 尚未启动 PR-DATA-1 / PR-DATA-2

**17D §6 PR 准入规则提醒**（与 18A §2 / 18J §2 一致；本轮再次重申）：

| # | 问题 | 期望答案形式 |
|---|---|---|
| 1 | 它属于九分支中的哪一层？ | 明确指出是 Branch 1 ~ 9 中的**某一个** |
| 2 | 它执行的是该层 Rebuild Plan 中的哪一项？ | 引用 17E ~ 17M 对应文档的**具体章节** |
| 3 | 它是否跨层？ | 期望 NO |
| 4 | 它有没有顺手修别的层？ | 期望 NO |
| 5 | 它有没有修改未授权模块？ | 期望 NO |
| 6 | 它是否会扩大 bridge 依赖？ | 期望 NO |
| 7 | 它是否会引入 trading / hard / forced / buy / sell / hold？ | **永久 NO** |
| 8 | 它是否有 focused tests + full pytest + rollback plan？ | YES |

---

## 3. 当前架构状态总结

按九分支整理当前**已完成 / 未完成**实质：

### 3.1 Branch 1 Data Layer

- ✅ 17E Data Layer Rebuild Plan 已入 main
- ❌ 仍未启动 PR-DATA-1（data_fetcher / market_data boundary tests）
- ❌ 仍未启动 PR-DATA-2（standard_market_data_payload helper）
- ❌ Data Layer 目前**只有 plan**，还没有第一批代码 PR

### 3.2 Branch 2 Feature Layer

- ✅ `feature_payload.v1` contract validator（PR-FEATURE-1）
- ✅ `services/feature_payload_adapter.py` producer adapter（PR-FEATURE-2，
  not on active path）
- ❌ `feature_builder.py` / `scanner.py` / `matcher.py` / `encoder.py` 尚未
  正式迁入 standard payload active path
- ❌ PR-FEATURE-3（raw / adj price basis tagging）/ PR-FEATURE-4（scanner /
  encoder boundary tests）/ PR-FEATURE-5（matcher input vs evaluation
  split）/ PR-FEATURE-6（data_query feature enrichment split）/
  PR-FEATURE-7（peer_alignment extension boundary tests）尚未启动

### 3.3 Branch 3 Projection Layer

- ✅ `projection_result.v1` contract validator（PR-PROJ-1）
- ✅ `services/projection_result_adapter.py` legacy-to-standard adapter
  （PR-PROJ-2，not on active path）
- ❌ `services/main_projection_layer.py` 的 active output 尚未直接改为
  standard schema（仍输出 `kind="main_projection_layer"` /
  `predicted_top1` / `predicted_top2`）
- ❌ PR-PROJ-3（historical_probability boundary tests）/ PR-PROJ-4
  （primary_20day_analysis freeze marker）/ PR-PROJ-5（scanner scan_bias
  freeze marker）/ PR-PROJ-6（orchestrator caller boundary tests）/
  PR-PROJ-7（legacy projection bridge deprecation marker）尚未启动

### 3.4 Branch 4 Exclusion Layer

- ✅ `exclusion_result.v1` contract validator（PR-EXCL-1）
- ✅ `services/exclusion_result_adapter.py` legacy-to-standard adapter
  （PR-EXCL-2，not on active path）
- ❌ `services/exclusion_layer.py` 的 active output 尚未直接改为 standard
  schema（仍输出 `triggered_rule` 单数 / `excluded` bool / `action`）
- ❌ PR-EXCL-3（triggered_rule → triggered_rules / excluded_states
  migration）/ PR-EXCL-4（false_exclusion_risk 标准化）/ PR-EXCL-5 ~
  PR-EXCL-8 尚未启动

### 3.5 Branch 5 Confidence Layer

- ✅ `confidence_result.v1` contract validator（PR-CONF-1）
- ✅ `_compute_agreement` schema adapter（PR-CONF-2，**active path 已修
  复**——读 standard schema 优先 + legacy fallback；`agreement_status`
  长期 unknown 根因解决）
- ✅ `calibration_context = {"ready": False}` 已在 3 个生产 caller 显式化
  （PR-CONF-3）
- ❌ 真实 calibration table 未接入（17I §12.4 / PR-CONF-7 留待 calibration
  data source plan）
- ❌ PR-CONF-4（agreement_status / conflict_level enum standardization，
  加 `medium` 槽位）/ PR-CONF-5（consistency_layer freeze marker）/
  PR-CONF-6（active_rule_pool* 归位）/ PR-CONF-7（calibration data source
  plan）尚未启动

### 3.6 Branch 6 Final Report Layer

- ✅ `final_report_result.v1` contract validator（PR-FINAL-1）
- ✅ `services/final_decision.py` non-mutation 加固 + 3 个 dead helpers
  删除（PR-FINAL-2）
- ❌ `warning_cards` schema 尚未接入（PR-FINAL-4 候选；目前 final_decision
  只标注 dead helper 已删，warning_cards 仍是空泛字段）
- ❌ `final_report_result.v1` 真实 active path adapter 未接入（仍是 legacy
  `final_report_aggregator_result.v1` schema）
- ❌ PR-FINAL-3（consistency_layer freeze marker）/ PR-FINAL-4（warning_cards
  schema）/ PR-FINAL-5（projection_chain_contract split marker）/
  PR-FINAL-6（contract_payload translation isolation）/ PR-FINAL-7
  （architecture_orchestrator ownership doc）/ PR-FINAL-8（narrative
  summary helper boundary tests）尚未启动

### 3.7 Branch 7 Review & Learning Layer

- ✅ `review_result.v1` contract validator（PR-REVIEW-1）
- ✅ `_apply_briefing_caution` warning-only（PR-REVIEW-2，**关键违规修
  复**）
- ❌ `pre_prediction_briefing` / `projection_memory_briefing` /
  `memory_feedback` 的 read-only boundary tests 尚未系统化
- ❌ `outcome_capture` cutoff guard 系统化测试尚未启动
- ❌ `review_store` / `memory_store` lifecycle schema 尚未规划
- ❌ rule_lifecycle 5 状态机持久化尚未规划
- ❌ PR-REVIEW-3（briefing read-only boundary tests）/ PR-REVIEW-4
  （review_store lifecycle schema plan）/ PR-REVIEW-5（exclusion_reliability_review
  freeze marker）/ PR-REVIEW-6（anti_false_exclusion_audit freeze marker）/
  PR-REVIEW-7（outcome_capture boundary tests）/ PR-REVIEW-8（memory rule
  lifecycle plan）尚未启动

### 3.8 Branch 8 Evaluation Layer

- ✅ `evaluation_result.v1` contract validator（PR-EVAL-1）
- ❌ 2026 holdout boundary tests 尚未系统化
- ❌ historical_replay_training anti-lookahead boundary 未通过专门测试覆盖
- ❌ replay manifest standard 未引入
- ❌ confidence calibration summary contract 未接入
- ❌ active_rule_pool_calibration offline-only 边界未通过专门测试覆盖
- ❌ raw artifact guard tests 未引入
- ❌ PR-EVAL-2 ~ PR-EVAL-8 尚未启动

### 3.9 Branch 9 UI / Presentation Layer

- ✅ `presentation_payload.v1` contract validator（PR-UI-1）
- ✅ Inspect tab Standard Payload 状态 section（PR-UI-2，第一刀低风险）
- ❌ Predict tab 仍读 legacy `final_bias` / `final_confidence` /
  `primary_projection` / `final_projection`
- ❌ History tab / Review tab / Inspect tab diff/trend display / Evaluation
  dashboard 拆分 / warning_cards renderer 等 PR 尚未启动
- ❌ PR-UI-3 ~ PR-UI-9 尚未启动

### 3.10 跨层未完成项

- ❌ `services/architecture_orchestrator.py` 仍未存在（assembly orchestration
  仍由 V1 / V2 / home_terminal 三套并行 orchestrator 承担）
- ❌ Bridge（`predict.py` / `predict_legacy_adapter.py` /
  `predict_legacy_v2_bridge.py` / V1 orchestrator / V2 orchestrator /
  home_terminal_orchestrator / projection_entrypoint /
  projection_v2_adapter）尚未清理
- ❌ 16H Repository Clearing Decision Table 中的 MOVE_OUTSIDE_REPO /
  ARCHIVE_IN_REPO / DELETE_LATER 候选尚未执行
- ❌ active import graph / bridge caller inventory / legacy field usage
  scan 尚未生成

---

## 4. 第三批候选方向总览

### 4.1 七大方向

#### A. Evaluation / Holdout 安全边界

| 候选 PR | 来源 | 所属层 | 性质 | 风险 |
|---|---|---|---|---|
| **PR-EVAL-2** | 17L §16 | Branch 8 Evaluation | 2026 holdout boundary tests / anti-lookahead guard | L |
| **PR-EVAL-3** | 17L §16 | Branch 8 Evaluation | replay manifest standard helper + tests | L |
| **PR-EVAL-4** | 17L §16 | Branch 8 Evaluation | confidence calibration summary contract | L |
| **PR-EVAL-7** | 17L §16 | Branch 8 Evaluation | active_rule_pool_calibration offline-only boundary tests | M |
| **PR-EVAL-8** | 17L §16 | Branch 8 Evaluation | raw artifact guard tests | L |

#### B. Data Layer 第一刀

| 候选 PR | 来源 | 所属层 | 性质 | 风险 |
|---|---|---|---|---|
| **PR-DATA-1** | 17E §13 | Branch 1 Data | data_fetcher / no-live-network boundary tests | L |
| **PR-DATA-2** | 17E §13 | Branch 1 Data | standard_market_data_payload helper | L |
| **PR-DATA-5** | 17E §13 | Branch 1 Data | raw artifact / DB backup guard tests | L |

#### C. Architecture Orchestrator 前置

| 候选 PR | 来源 | 所属层 | 性质 | 风险 |
|---|---|---|---|---|
| **PR-FINAL-7** | 17J §13 | Branch 6 / 跨层 | architecture_orchestrator ownership doc | L（doc only） |
| **PR-ARCH-1**（新候选） | 18S 本文件 | 跨层 / TEMP_FUTURE_ORCHESTRATOR | architecture_orchestrator skeleton — **不接 active path** | L |

> 注：`architecture_orchestrator` 不在九分支正式架构内（17J §13
> PR-FINAL-7 已写明为 ASSEMBLY_ORCHESTRATION_LAYER /
> TEMP_FUTURE_ORCHESTRATOR）。skeleton-only PR 不会立即接 active path，
> 风险低。

#### D. Standard payload active path 继续推进

| 候选 PR | 来源 | 所属层 | 性质 | 风险 |
|---|---|---|---|---|
| **PR-PROJ-2 active emit**（17G §13 PR-PROJ-2 真正 producer 输出版） | 17G §13 | Branch 3 | main_projection_layer 输出 standard keys（额外 alias）| L |
| **PR-EXCL-2 active emit** | 17H §14 | Branch 4 | exclusion_layer 输出 standard keys（额外 alias）| L |
| **PR-EXCL-3** | 17H §14 | Branch 4 | triggered_rule → triggered_rules / excluded_states migration | L |
| **PR-EXCL-4** | 17H §14 | Branch 4 | false_exclusion_risk 标准化 | L |
| **PR-FINAL-3** | 17J §13 | Branch 6 | consistency_layer freeze marker | L |
| **PR-FINAL-4** | 17J §13 | Branch 6 | warning_cards schema for contradiction / tail warning | M |
| **PR-FINAL-5** | 17J §13 | Branch 6 | projection_chain_contract split plan / marker | L |
| **PR-CONF-4** | 17I §13 | Branch 5 | agreement_status / conflict_level enum standardization（加 medium 槽位）| L |

> 注：PR-PROJ-2 / PR-EXCL-2 第二批落地的是 **adapter only**，不接 active
> path。下一阶段需要让真实 producer（main_projection_layer /
> exclusion_layer）也开始**额外**输出 standard keys（保留 legacy 兼容）。

#### E. Review & Learning 后续边界

| 候选 PR | 来源 | 所属层 | 性质 | 风险 |
|---|---|---|---|---|
| **PR-REVIEW-3** | 17K §17 | Branch 7 | briefing read-only boundary tests | L |
| **PR-REVIEW-4** | 17K §17 | Branch 7 | review_store / memory_store lifecycle schema plan | L（doc only） |
| **PR-REVIEW-5** | 17K §17 | Branch 7 | exclusion_reliability_review 归位 / freeze marker | L |
| **PR-REVIEW-6** | 17K §17 | Branch 7 | anti_false_exclusion_audit 归位 / freeze marker | L |
| **PR-REVIEW-7** | 17K §17 | Branch 7 | outcome_capture boundary tests | L |
| **PR-REVIEW-8** | 17K §17 | Branch 7 | memory rule lifecycle plan | L（doc only） |

#### F. UI 后续

| 候选 PR | 来源 | 所属层 | 性质 | 风险 |
|---|---|---|---|---|
| **PR-UI-3** | 17M §16 | Branch 9 | Inspect tab diff / trend display expansion（基于现有 contract_payload_diff / _trend / _extras）| L |
| **PR-UI-4** | 17M §16 | Branch 9 | Review tab review_result display（与 17K 协同）| L |
| **PR-UI-5** | 17M §16 | Branch 9 | Evaluation dashboard display-only split | M |
| **PR-UI-6** | 17M §16 | Branch 9 | warning_cards renderer（与 17J PR-FINAL-4 协同）| M |
| **PR-UI-7** | 17M §16 | Branch 9 | **Predict tab compatibility fallback explicit** | **H — 暂缓** |
| **PR-UI-8** | 17M §16 | Branch 9 | app.py tab shell stabilization（仅 docstring）| L |
| **PR-UI-9** | 17M §16 | Branch 9 | legacy final_bias / final_confidence read deprecation marker | L |

#### G. 清离 / quarantine / archive 前置

| 候选 PR | 来源 | 所属层 | 性质 | 风险 |
|---|---|---|---|---|
| **PR-CLEAR-1**（新候选） | 16H + 18S 本文件 | 跨层 / 文档 + tests | active import graph + bridge caller inventory + legacy field usage scan + archive readiness table | L（read-only / doc + tests） |

> PR-CLEAR-1 **不删**任何文件，**不**移动文件。它生成一份 archive
> readiness 报告 + AST-level 测试，**只**用于后续 archive PR 的前置审批。

### 4.2 暂缓清单（**第三批不进入**）

> 这些项有方向，但**不进入**第三批，需要等第三批基础完成后再单独评估。

- **architecture_orchestrator active wire-in**——skeleton 可入第三批
  （PR-ARCH-1），但**不**接 active path
- **Predict tab 迁移**（PR-UI-7）——风险 H；必须等 PR-FINAL-4 warning_cards
  + architecture_orchestrator skeleton + 进一步 adapter active wiring 后
  再做
- **Bridge 删除 / archive**——PR-CLEAR-1 只生成 readiness report；**不**
  执行 archive / delete；真正 archive 留待第四批以后
- **3R-5 / 3R-6**——1.0 §12 七项前提仍未全部满足；**永久不允许**通过
  cleanup / signoff 自动解锁
- **真实 calibration 数据接入**——必须等 calibration_summary contract
  （PR-EVAL-4）+ active_rule_pool_calibration 测试（PR-EVAL-7）落地后
  再决定
- **historical_replay_training 真实运行**——必须等 holdout boundary
  tests（PR-EVAL-2）+ replay manifest（PR-EVAL-3）+ raw artifact guard
  （PR-EVAL-8）全部落地后再决定
- **trading / broker / buy / sell / hold**——永久禁止
- **continuous_smoothing 复活 / OFFLINE_ONLY 三模块解禁**——永久禁止

---

## 5. 第三批选择原则

**第三批 PR 必须同时满足以下原则**：

1. **第二批刚完成 active path 修复（Confidence schema + Briefing
   warning-only），不马上做大迁移**——优先补"安全验证"和"迁移前置"，
   而不是直接动 Predict tab / Bridge / 全链路 replay
2. **优先 Evaluation / Data / architecture_orchestrator skeleton 这种
   低风险地基**——一旦后面开始 replay / calibration / 完整迁移，没有
   holdout 边界 / data layer 边界 / orchestrator skeleton 就没有安全
   护栏
3. **不直接做 Bridge 删除**——PR-CLEAR-1 只**列出**，不**删除**
4. **不直接迁 Predict tab**——风险 H，依赖 PR-FINAL-4 warning_cards +
   architecture_orchestrator skeleton + 更多 adapter active wiring
5. **不直接跑 replay / holdout 全流程**——必须先有 PR-EVAL-2 边界测试 +
   PR-EVAL-3 manifest + PR-EVAL-8 raw artifact guard
6. **不直接启用 calibration 真实分数**——必须先有 PR-EVAL-4
   calibration_summary contract
7. **不接 trading / broker**——永久禁止
8. **每个 PR 仍需绑定单一层**——除非显式 doc only / 跨层文档（如
   PR-ARCH-1 skeleton 标 TEMP_FUTURE_ORCHESTRATOR / PR-CLEAR-1 标
   readiness report）
9. **每个 PR 单独 commit**——单 commit 单 batch
10. **失败可 git revert**——单 commit 可独立回滚
11. **每个 PR 必须**：focused tests + related tests + full pytest +
    `scripts/check.sh`

**默认 reject 路径**：

- 不满足以上任一条 → **不进入**第三批
- 即使满足以上全部，仍需**用户单独确认**才能启动对应 batch

---

## 6. 推荐第三批路线

按"先安全边界 → 再地基 → 再 skeleton → 再 active path 推进 → 再 review
后续 → 再 UI → 最后清离前置"的顺序：

| 顺序 | Step | 候选 PR | 所属层 | 来源 | 性质 | 风险 |
|---|---|---|---|---|---|---|
| 1 | **18T** | **PR-EVAL-2** | Branch 8 Evaluation | 17L §16 | 2026 holdout boundary tests / anti-lookahead guard | L |
| 2 | **18U** | **PR-DATA-1** | Branch 1 Data | 17E §13 | data_fetcher / no-live-network boundary tests | L |
| 3 | **18V** | **PR-ARCH-1** | 跨层 / TEMP_FUTURE_ORCHESTRATOR | 17J §13 PR-FINAL-7 + 18S | architecture_orchestrator ownership skeleton — **不接 active path** | L |
| 4 | **18W** | **PR-FINAL-4** | Branch 6 Final Report | 17J §13 | warning_cards schema for contradiction / tail warning | M |
| 5 | **18X** | **PR-REVIEW-3** | Branch 7 Review | 17K §17 | briefing read-only boundary tests | L |
| 6 | **18Y** | **PR-UI-3** | Branch 9 UI | 17M §16 | Inspect tab diff / trend display expansion | L |
| 7 | **18Z** | **PR-CLEAR-1** | 跨层 / 文档 + tests | 16H + 18S | legacy bridge active import graph + archive readiness table | L |

**说明**：

- **18T 第一刀**：在继续推 active path 迁移之前，**必须先**锁住
  Evaluation / 2026 holdout 边界。这是后续 replay / calibration /
  active_rule_pool_calibration 等的护栏
- **18U 第二刀**：Data Layer 至今未启动任何代码 PR；与 Evaluation 并列
  作为低风险地基；让 Branch 1 也开始有 boundary test 覆盖
- **18V 第三刀**：architecture_orchestrator skeleton（不接 active）——
  让 17J PR-FINAL-7 / 16I PR-F 的 ownership doc + 一个空的 skeleton
  module 落地；所有真正的 wire-in 留待第四批+
- **18W 第四刀**：warning_cards schema——为 PR-REVIEW-2 落地的
  briefing_caution_recommended_confidence / briefing_caution_reason
  提供标准展示容器；同时为 PR-UI-7 Predict tab 迁移作准备
- **18X 第五刀**：补齐 Review Layer 的 boundary tests（briefing read-only
  / cutoff guard / no-mutation-of-current-prediction）
- **18Y 第六刀**：Inspect tab 升级（diff / trend display），消费
  contract_payload_diff / _trend / _extras 已有 helper
- **18Z 第七刀**：清离前置——只**列出**而不**删除**；为第四批+ 的真正
  archive / quarantine 提供数据
- **顺序硬约束**：18T 锁住 holdout 边界 → 18W warning_cards 是 Predict
  tab / final_report 的下游依赖 → 18Z archive readiness 必须等所有 active
  wiring 路径都被测试覆盖

---

## 7. 第一刀推荐：18T / PR-EVAL-2

**明确推荐第三批第一刀**：

> **Step 18T / PR-EVAL-2：2026 holdout boundary tests / anti-lookahead guard**

**理由**：

- **用户已经把 2026-01-01 之后数据定为最终测试集 / holdout**——1.0 §5
  rule 8 / 07A §3.2 / 07B §3.2 / 07C §3.2 / 07D §3.2 / 17L §8 全部锁定
- **当前已经完成 contract + adapter + Confidence/Review 关键修复**——
  接下来如果继续推 active path 迁移而没有 holdout 边界护栏，容易让 replay
  / calibration / active_rule_pool_calibration 无意中读 holdout
- **在继续迁移 active path 前，需要先锁住 evaluation 边界**——这是
  18J §11 暂缓清单 + 18S §4 暂缓清单中"replay / holdout / calibration"
  能够后续放行的前置条件
- **这是安全类测试 PR，不改业务逻辑**——boundary / contract 测试为主，
  不动 producer / orchestrator / DB / UI
- **能防止后续 replay / calibration / active rule promotion 偷看
  holdout**——一旦 PR-EVAL-7（active_rule_pool_calibration offline-only）
  被启动，holdout 边界已经 enforced
- **不碰 predict.py / UI / DB / orchestrator**——文件范围只命中
  `tests/test_evaluation_holdout_boundary.py`（新增）+ 可能扩展
  `tests/test_evaluation_result_contract.py`（已存在；如需新增 contract
  case）
- **风险低于 Predict tab 迁移 / Bridge 清理 / architecture_orchestrator
  active 接入**——前两个风险 H，第三个可入 18V skeleton-only

**对比为什么不是 PR-DATA-1 / PR-ARCH-1 / PR-FINAL-4**：

- **PR-DATA-1**（Branch 1 Data Layer）：好但是 Branch 1 至今未启动；
  优先级在 holdout 边界后；放 18U 第二刀
- **PR-ARCH-1**（architecture_orchestrator skeleton）：好但是没有 holdout
  边界先于它落地，后续真正 wire-in 时还得补；放 18V 第三刀
- **PR-FINAL-4**（warning_cards）：好但是它依赖 18T 边界 + 18V skeleton
  对 Predict tab 提供下游路径；放 18W 第四刀

PR-EVAL-2 是**安全测试 only / 不接 active path**，所以是第三批最低风险
第一刀。

---

## 8. 18T / PR-EVAL-2 草案

> **本节是 Step 18T 草案，不是实现**。本轮 18S 不实现任何代码；草案只
> 用来界定后续 18T 的范围。

### 8.1 目标文件候选

| 文件 | 性质 | 内容草案 |
|---|---|---|
| `tests/test_evaluation_holdout_boundary.py` | **新增** boundary tests | 锁定 2026-01-01 holdout 不变；anti-lookahead 四项必须 True；artifact_manifest.raw_artifacts_tracked 必须 False；training/calibration 窗口必须 < 2026-01-01 |
| 如发现 contract 缺口（例如 `evaluation_result_contract` 没有显式
锁定 holdout 起点常量）→ **先停止说明**，**不**改 contract module；
留待 PR-EVAL-3 之后单独评估 | — | — |

### 8.2 目标范围

- **锁定 2026-01-01 之后数据为 final holdout**——常量化（可作为新增
  test fixture 内部常量；**不**改 evaluation_result_contract.py）
- **确认 training / calibration / rule promotion 不允许使用 holdout**
  ——验证 evaluation_result.train_window / validation_window / holdout_window
  时间戳关系
- **确认 evaluation_result.holdout_touch_status 必须显式**——已由
  contract 4-enum 强制；boundary tests 验证缺失 / 非法值 → validation
  error
- **确认 anti_lookahead_confirmations 四项必须 True**——已由 contract
  强制；boundary tests 验证 False / 缺失 → validation error
- **确认 raw artifacts 不进入 tracked payload**——已由 contract
  `artifact_manifest.raw_artifacts_tracked = False` 强制；boundary tests
  验证 True → validation error
- **AST-level 测试**：`services/historical_replay_training.py` /
  `services/active_rule_pool_calibration.py` 等模块**不**调用
  `Date >= 2026-01-01` 数据进行 training（这是 source-level grep 测试，
  不实际跑 replay）

### 8.3 不允许做的事（18T 范围内）

- ❌ **不**运行 `historical_replay_training`（任何形式）
- ❌ **不**生成任何 `csv` / `jsonl` / `_run.log` / replay artifact
- ❌ **不**写任何 logs（除 pytest 默认输出）
- ❌ **不**改 `services/evaluation_result_contract.py`，除非 boundary
  tests 暴露 contract 缺口；若发现缺口先**停止说明**，单独评估
- ❌ **不**改 `services/historical_replay_training.py`
- ❌ **不**改 `services/active_rule_pool_calibration.py`
- ❌ **不**改 `services/regime_validation_helper.py`
- ❌ **不**改任何 data files / coded_data / enriched_data /
  match_results
- ❌ **不**改 `predict.py` / `app.py` / UI / orchestrator / DB
- ❌ **不**接 trading / broker / production_promotion

### 8.4 测试方向草案

| 测试类 | 内容 |
|---|---|
| `HoldoutDateConstantTests` | 锁定 holdout 起点 = `"2026-01-01"`（test fixture 常量；防止意外漂移） |
| `TrainingWindowEndsBefore2026Tests` | 给定 evaluation_result with train_window.end_date >= "2026-01-01" → validate_evaluation_result 返回 error 或 holdout_touch_status="violated" |
| `ValidationWindowEndsBefore2026Tests` | 同上 for validation_window |
| `HoldoutTouchStatusRequiredTests` | 缺失 / 非 enum 值 → validation error |
| `AntiLookaheadConfirmationsRequiredTests` | 任一 False / 缺失 → validation error |
| `RawArtifactsTrackedMustBeFalseTests` | True / 缺失 → validation error |
| `HoldoutTouchStatusViolatedFlagTests` | "violated" 状态 → 至少一个 anti_lookahead_confirmations 必须 False（语义验证：违反不能伪装成 untouched） |
| `AnyAstScanForwardLeakageTests` | source-level grep `services/historical_replay_training.py` 等模块不含 `Date >= "2026-01-01"` 用于 training（source contains pattern → fail） |
| `RawArtifactGuardTests` | `evaluation_result` payload 顶层 + nested 不含 `raw_replay_rows` / `raw_predictions_dump` / `raw_csv_dump` |

> **本草案只用来界定 18T 范围**；实际 18T 实现细节由 builder 在用户单独
> 确认 18T 启动后给出。

---

## 9. 为什么不先做 Data Layer

> **Data Layer 很重要，但当前第三批更需要先锁住 Evaluation / Holdout
> 边界。**

- ✅ **方向正确**——Branch 1 至今未启动任何代码 PR，理应尽快补上
- ❌ **但优先级在 Evaluation 边界后**：
  - 一旦后面开始 replay / calibration / `architecture_orchestrator` 真实
    wire-in，**holdout 边界必须先稳定**
  - Data Layer 改动相对独立，**不**会立即触发 holdout 误读
  - Evaluation 边界是 cross-cutting 安全护栏，Data Layer 不是
- ❌ **顺序倒置的风险**：如果先做 Data Layer，后续 PR-DATA-2 standard
  schema 引入 → 可能被新 helper 在 training 路径中误用 → 没有 holdout
  guard 兜底

**结论**：

- Data Layer **必须**进入第三批，但放第二刀（18U）
- 18T evaluation guard 是 18U 的护栏

---

## 10. 为什么不先做 architecture_orchestrator

> **`architecture_orchestrator` 已经比之前更具备前置条件，但它仍然是
> 跨层组装层。**

- ✅ **方向正确**——17J §13 PR-FINAL-7 已经把 architecture_orchestrator
  的"真正实现 PR 的前置条件"写明：第二批 producer adapters 全部落地
  之后才能开。第二批已落地。
- ❌ **但仍是跨层组装**：
  - skeleton-only 不接 active path 风险低，但**真正 wire-in** 跨 Feature /
    Projection / Exclusion / Confidence / Final Report 五层
  - 如果没有 Evaluation / Holdout 边界，wire-in 后容易直接跑大链路而没有
    安全护栏
- ❌ **顺序选择**：
  - **18T evaluation guard**（先建护栏）
  - → **18U Data Layer** boundary（地基）
  - → **18V architecture_orchestrator skeleton**（接好上述两层后再开骨架）
  - → 后续批次再 wire-in

**结论**：

- `architecture_orchestrator` skeleton 进入第三批，但放第三刀（18V）
- 真正 wire-in（Feature → Projection → Exclusion → Confidence → Final
  Report 串起来）留待第四批以后

---

## 11. 为什么不先清理 Bridge

> **虽然第二批已完成 adapters 和关键修复，但 active caller 仍可能依赖
> legacy fields。**

- ✅ **方向正确**——16H Repository Clearing Decision Table 已经为 13 个
  LEGACY_ACTIVE_DEPENDENCY 模块标记 MIGRATE_CALLER_FIRST；总归要做
- ❌ **但 Bridge 清理的前置条件还没满足**：
  - active import graph **未生成**
  - bridge caller inventory **未生成**
  - legacy field usage scan **未生成**
  - 任何 archive / delete 都需要"active import = 0"+"已 archive
    副本"+"用户单独确认"+"regression 通过"四项前提全部满足
  - 当前满足 0/4
- ❌ **Bridge 清理一旦开始，影响极大**：predict.py / V1/V2 orchestrator /
  home_terminal_orchestrator / projection_entrypoint / projection_v2_adapter /
  predict_legacy_adapter / predict_legacy_v2_bridge — 任一 archive 都会
  破坏 UI / replay / tests

**结论**：

- 第三批最多做 **PR-CLEAR-1：archive readiness table + active import
  graph + caller inventory + legacy field usage scan**（**不删除文件**）
- 真正 archive / delete 仍暂缓到第四批以后
- 18Z 是第三批最后一刀（也是清离前置最重要一刀）

---

## 12. 为什么不先迁 Predict tab

> **Predict tab 是高风险 UI 主链。**

- ✅ **方向正确**——Bridge #1 退出条件 #1 = "UI 全部读新 final_report
  schema"
- ❌ **但 Predict tab 仍依赖 legacy payload**：
  - `final_bias` / `final_confidence` / `primary_projection` /
    `final_projection` / `run_predict` 输出
  - PR-UI-7（17M §16）显式标注风险 H
- ❌ **必须先**：
  - PR-FINAL-4 warning_cards schema 落地（让 Predict tab 有标准 warning
    展示容器）
  - PR-ARCH-1 architecture_orchestrator skeleton 落地（让 Predict tab
    将来读取的 standard payload 来源稳定）
  - 进一步 adapter active wiring（让 producer 真的输出 standard keys）
  - 这些都要在 Predict tab 迁移之前
- ❌ **风险 H 不应在第三批前段开**——Inspect tab（PR-UI-2）已落地，
  PR-UI-3 / PR-UI-4 / PR-UI-5 / PR-UI-6 都是中低风险候选；PR-UI-7 留待
  第四批以后

**结论**：

- Predict tab **不**进入第三批前段
- PR-UI-7（Predict tab 迁移）**永久**不能在 PR-FINAL-4 + PR-ARCH-1 +
  更多 adapter active wiring 完成之前启动
- 第三批 UI 候选只考虑 PR-UI-3（Inspect tab 升级，18Y）

---

## 13. 为什么不进入 3R-5 / 3R-6

> **3R-5 / 3R-6 需要 7 项前提全部满足（1.0 §12）**：

1. 9 分支站队完成 ✅
2. 目标 schema 唯一化 ⚠️ 部分（contract validators 已就位，但 active path
   仍混合 legacy）
3. 隔离 / quarantine 计划已落地 ⚠️ 计划已落，执行未启
4. 核心链 refactor 计划完成 ✅（16E / 16I）
5. 第一批代码 PR 已合并并通过 regression ✅
6. **standard active path** ❌ 未完成（仍是 V1 + V2 + home_terminal
   三套并行 + adapter only）
7. **evaluation guard** ❌ 未启
8. **replay manifest** ❌ 未启
9. **calibration summary** ❌ 未启
10. **UI / review lifecycle 边界** ❌ 部分（Inspect tab + briefing
    warning-only 是部分；review_store / memory lifecycle 未规划）
11. **用户单独确认** ❌ 必须由用户显式确认（永久禁止 cleanup / signoff
    自动解锁）

**还差**：第 6 / 7 / 8 / 9 / 10 / 11 项。

**结论**：

- 第三批仍**不**进入 3R-5 / 3R-6
- 这是**永久原则**——`continuous_smoothing` / promotion / production
  promotion 等都属于 3R-5 / 3R-6 阶段，必须等所有前置满足 + 用户单独
  确认后才能解锁
- 1.0 §12 / 13 §9 / 15 §8 / 16I §15 / 17D §11 / 18A §14 / 18J §15 /
  18S §15 持续锁定

---

## 14. 第三批 PR 验收标准

每个第三批 PR 必须**同时**满足：

| # | 标准 | 说明 |
|---|---|---|
| 1 | 绑定单一层 | PR 描述显式声明 `Compliant with 17D §6 layer-binding rule; bound to Branch <N>; references <17X §Y>.`（PR-ARCH-1 / PR-CLEAR-1 例外，需在描述中显式声明跨层 + TEMP_FUTURE_ORCHESTRATOR / readiness report 性质）|
| 2 | 引用对应 plan 章节 | PR 描述显式引用 17E ~ 17M / 16H / 18S 中具体小节 |
| 3 | 明确是否接 active path | PR-EVAL-2 / PR-DATA-1 / PR-ARCH-1 / PR-REVIEW-3 / PR-CLEAR-1 不接；PR-FINAL-4 / PR-UI-3 接 active path（描述中明确）|
| 4 | 不跨层 | 除非文档明确批准（PR-ARCH-1 / PR-CLEAR-1）；`git diff --stat` 只命中本层文件 |
| 5 | 不改 Predict tab | 永久禁止本批；只允许 PR-UI-3 改 Inspect tab |
| 6 | 不改 `predict.py` | 永久禁止本批 |
| 7 | 不删除 Bridge | PR-CLEAR-1 只生成 readiness report |
| 8 | 不跑 replay / holdout / calibration | 永久禁止本批 |
| 9 | 不接 trading / broker | 永久禁止 |
| 10 | 不输出 buy / sell / hold / hard / forced / required | 永久禁止 |
| 11 | focused tests 通过 | 该 PR 的 focused tests 100% 通过 |
| 12 | related tests 通过 | 该 PR 影响范围内的相关 tests 全绿 |
| 13 | full pytest 通过 | 18R 入 main 后的 baseline = **4006 passed, 10 skipped, 0 failed, 26 warnings, 1711 subtests passed**；新增测试数显式累加到 passed |
| 14 | scripts/check.sh 通过 | 统一检查脚本通过 |
| 15 | git diff 只包含目标文件 | `git diff --stat` 只命中 PR 目标文件 |
| 16 | 可 git revert | 单 commit；可独立回滚 |

---

## 15. 本轮不允许事项

**18S 起，本轮（直到用户确认 18T 启动之前）严格禁止**：

- ❌ 不改代码（无 `.py` 文件被修改；本轮 0 修改）
- ❌ 不新增测试（`tests/` 字节不变）
- ❌ 不跑 pytest（除 readonly 校验外不执行 test 命令）
- ❌ 不跑 replay
- ❌ 不跑 holdout
- ❌ 不跑 calibration
- ❌ 不做 PR-EVAL-2 实现（PR-EVAL-2 留待 18T）
- ❌ 不做 PR-DATA-1 / PR-DATA-2 实现（留待 18U）
- ❌ 不实现 architecture_orchestrator（PR-ARCH-1 skeleton 留待 18V）
- ❌ 不做 PR-FINAL-4 warning_cards（留待 18W）
- ❌ 不做 PR-REVIEW-3 ~ PR-REVIEW-8（留待 18X 起）
- ❌ 不做 PR-UI-3 ~ PR-UI-9（PR-UI-3 留待 18Y；PR-UI-7 永久暂缓本批）
- ❌ 不做 PR-CLEAR-1（archive readiness 留待 18Z）
- ❌ 不清 Bridge / 不 archive legacy
- ❌ 不迁 Predict tab
- ❌ 不进入 3R-5 / 3R-6（永久原则；本轮再次重申）
- ❌ 不复活 `continuous_smoothing*` / `archive/legacy/root_stubs/*` /
  promotion 三模块
- ❌ 不修改 `.gitignore`
- ❌ 不处理 `avgo_agent.db`（含 backup）
- ❌ 不处理 handoff
- ❌ 不处理 logs / DB backup / `.claude/worktrees/`
- ❌ 不写 DB / 不改 DB schema
- ❌ 不接 trading
- ❌ 不输出 buy / sell / hold / hard / forced / required
- ❌ 不污染 2026-01-01 之后 final holdout
- ❌ 不借 18S 顺手做代码改动（本轮全部 markdown 改动）

> 与 17D §11 / 17E ~ 17M §禁止事项 / 18A §14 / 18J §15 一致；本轮再次锁定。

---

## 16. 推荐下一步

**推荐**：

> **Step 18T / PR-EVAL-2：2026 holdout boundary tests / anti-lookahead guard**

**前置条件**：

- 18S 入 main
- 用户单独确认 18T 启动

**18S 入 main 后启动顺序建议**（每个 batch 单独确认）：

1. **Step 18T**：PR-EVAL-2 — 2026 holdout boundary tests / anti-lookahead guard
2. **Step 18U**：PR-DATA-1 — data_fetcher / no-live-network boundary tests
3. **Step 18V**：PR-ARCH-1 — architecture_orchestrator ownership skeleton（不接 active path）
4. **Step 18W**：PR-FINAL-4 — warning_cards schema for contradiction / tail warning
5. **Step 18X**：PR-REVIEW-3 — briefing read-only boundary tests
6. **Step 18Y**：PR-UI-3 — Inspect tab diff / trend display expansion
7. **Step 18Z**：PR-CLEAR-1 — legacy bridge active import graph + archive readiness table

**18S 本轮只做 selection doc**——不启动 18T。

**不推荐**：

- 不推荐跳到 PR-DATA-1（必须等 PR-EVAL-2 holdout guard）
- 不推荐跳到 PR-ARCH-1 skeleton（必须等 PR-EVAL-2 + PR-DATA-1）
- 不推荐立刻做 PR-FINAL-4（必须等 PR-EVAL-2 + PR-DATA-1 + PR-ARCH-1
  skeleton）
- 不推荐做 PR-UI-7 Predict tab 迁移（永久暂缓本批；必须等 PR-FINAL-4 +
  PR-ARCH-1 + 更多 adapter active wiring）
- 不推荐立刻做 PR-CLEAR-1（必须放在第三批最后；让前面 6 个 PR 把
  active wiring / safety boundary 都完整先）
- 不推荐解锁 3R-5 / 3R-6（1.0 §12 七项前提仍未全部满足）
- 不推荐做真实 calibration / 真实 replay / 真实 holdout 运行
- 不推荐借 18S 顺手做任何代码改动（与 17D §11 / 18A §14 / 18J §15 一致）

> **明确**：本轮 18S 推荐的下一步**只有一个候选**——Step 18T / PR-EVAL-2。
> 启动需要用户单独确认。

---

## 17. 严守边界

本轮 Step 18S **只**写 Third Layer-Based Implementation Batch Selection：

- ❌ 未改代码（无 `.py` 文件被修改；`git diff --stat` 仅 markdown）
- ❌ 未新增测试（`tests/` 字节不变）
- ❌ 未删除文件
- ❌ 未移动文件
- ❌ 未修改 `.gitignore`
- ❌ 未处理 `avgo_agent.db`（16H §5 校正后无需处理）
- ❌ 未处理 handoff（worktree clean except deliberate keep；无新增 deliberate untracked）
- ❌ 未处理 logs / DB backup / `.claude/worktrees/`
- ❌ 未跑 replay / validation / historical evaluation / holdout / calibration
- ❌ 未写 DB / 未改 DB schema
- ❌ 未默认迁移 `run_predict` 到 V2
- ❌ 未接 trading
- ❌ 未输出 buy / sell / hold / hard / forced / required
- ❌ 未启用任何 candidate / 未复活 `continuous_smoothing`
- ❌ 未触碰 RISK-1 / RISK-2 / RISK-3 / RISK-7 / RISK-8 / RISK-9 / RISK-10
- ❌ 未进入 3R-5 / 3R-6
- ❌ 未启动任何代码 PR（PR-EVAL-2 候选要等 18T）
- ❌ 未实现 architecture_orchestrator（PR-ARCH-1 skeleton 留待 18V）
- ❌ 未删 Bridge / 未 archive legacy
- ❌ 未迁 Predict tab
- ❌ 未做任何局部 patch
- ❌ 未 commit / 未 push（按本轮指令）

唯一新增文件：[tasks/record_18s_third_layer_based_implementation_batch_selection.md](tasks/record_18s_third_layer_based_implementation_batch_selection.md)（本文件）。

后续修改路径：任何对 §3 当前架构状态 / §4 候选方向总览 / §5 选择原则 /
§6 推荐路线 / §7 第一刀推荐 / §8 18T 草案 / §9 ~ §13 各暂缓 / §14 验收
标准 / §15 禁止事项 / §16 下一步 的调整，都必须**显式更新本文件**；
同时检查是否需要同步更新 1.0 / 17D / 17E ~ 17M / 18A / 18J。
