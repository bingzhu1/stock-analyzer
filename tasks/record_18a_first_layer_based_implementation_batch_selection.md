# 18A记录：First Layer-Based Implementation Batch Selection

> 本记录是 **Step 18A：第一批按层实现 PR 选择**——九分支按层重建计划
> （17D ~ 17M）全部入 main 之后，进入 implementation 阶段的入口。
>
> 本轮**只**选择第一批实现 PR，**不**写代码。1.0 canonical / 16A blueprint /
> 16B inventory / 16C target dataflow & contract decision / 16D isolation &
> quarantine plan / 16E core chain refactor plan / 16F no-patching principle /
> 16G full module decomposition standup / 16H repository clearing decision
> table / 16I core chain rebuild execution plan / 17A PR-B standard payload
> skeleton / 17B PR-C peer_alignment 抽公共模块 / 17C PR-D main_projection
> 去 `exclusion_result` 形参 / 17D layer-by-layer rebuild governance /
> 17E Data Layer Rebuild Plan / 17F Feature Layer Rebuild Plan / 17G
> Projection Layer Rebuild Plan / 17H Exclusion Layer Rebuild Plan / 17I
> Confidence Layer Rebuild Plan / 17J Final Report Layer Rebuild Plan / 17K
> Review & Learning Layer Rebuild Plan / 17L Evaluation Layer Rebuild Plan /
> 17M UI / Presentation Layer Rebuild Plan 已全部入 main（main 最新 commit
> `4e191ee`）。
>
> 本轮**只**写 selection 文档：未改业务代码、未新增测试、未删除文件、
> 未移动文件、未修改 `.gitignore`、未处理 handoff、未处理 logs / DB
> backup / `.claude/worktrees/`、**未处理 `avgo_agent.db`**、未跑 replay /
> validation / historical evaluation、未写 DB / 未改 DB schema、未默认
> 迁移 `run_predict` 到 V2、未接 trading、未输出 buy / sell / hold /
> hard / forced / required、未进入 3R-5 / 3R-6、未启动任何代码 PR、
> 未直接做 confidence key patch、未直接修 `_apply_briefing_caution`、
> 未直接迁 UI、未直接实现 `architecture_orchestrator`、未 commit / 未
> push。
>
> 唯一 deliverable：本文件。
>
> **本记录优先级**：与 17D ~ 17M 同级。冲突仲裁路径与 1.0 §14 / 17D §13
> 一致：旧 records（含 16I PR-E ~ PR-H 顺序）若与 18A 冲突，**以 18A
> 为准**。

---

## 1. Step 18A 目的

九分支按层重建计划（17D 治理 + 17E ~ 17M 九层 plan）已全部入 main。
现在进入 implementation 阶段的入口。

> **本轮只选择第一批实现 PR，不写代码。**

具体目标——回答：

- 第一批从哪一层开始
- 为什么从这一层开始
- 第一批 PR 的文件范围
- 第一批 PR 的测试范围
- 第一批 PR 的回滚方式
- 是否跨层（默认 NO）
- 是否需要用户单独确认（YES，每个 batch 单独确认）

**本文件性质**：selection（选择决定），不是 design 也不是 impl。
设计与执行落地由 18B / 18C / 18D / 18E / 18F / 18G / 18H / 18I 起的
对应 batch 给出，每个 batch 单独 commit / 单独 review。

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
| 17M UI / Presentation Layer Rebuild Plan | ✅ commit `4e191ee` |
| main 最新 commit | `4e191ee` |
| worktree 状态 | clean（无 deliberate untracked） |
| 战略阶段 | 从九分支 plan（17D ~ 17M）→ **第一批实现 PR 选择（18A 本轮）** |
| 3R-5 / 3R-6 | ❌ 仍然不允许进入 |
| 第一批实现 PR | ❌ 必须等 18A 入 main + 用户单独确认后才能启动 |

**写明**：

- 17D ~ 17M 已全部入 main
- 九分支 plan 阶段完成（含治理 + 9 层各自 plan）
- 计划完成**不等于**可以乱开代码 PR
- 每个代码 PR 必须**绑定**九分支某一层
- 每个代码 PR 必须**引用**对应层 plan 章节（17E ~ 17M 的具体 §）
- 18A 只做选择，不做实现

**17D §6 PR 准入规则提醒**（全文复用）：

| # | 问题 | 期望答案形式 |
|---|---|---|
| 1 | 它属于九分支中的哪一层？ | 明确指出是 Branch 1 ~ 9 中的**某一个**（不允许"跨多个"） |
| 2 | 它执行的是该层 Rebuild Plan 中的哪一项？ | 引用 17E ~ 17M 对应文档的**具体章节** |
| 3 | 它是否跨层？ | 期望 NO；如有跨层 import，必须在描述里显式声明并引用 1.0 §9 数据流方向 |
| 4 | 它有没有顺手修别的层？ | 期望 NO；`git diff --stat` 只能命中本层文件 |
| 5 | 它有没有修改未授权模块？ | 期望 NO；该层 Plan 必须把"允许改 / 不允许碰"显式列出 |
| 6 | 它是否会扩大 bridge 依赖？ | 期望 NO |
| 7 | 它是否会引入 trading / hard / forced / buy / sell / hold？ | **永久 NO** |
| 8 | 它是否有 focused tests + full pytest + rollback plan？ | YES |

---

## 3. 第一批实现 PR 选择原则

**第一批 PR 必须同时满足以下原则**（任一条不满足则**剔除**该候选）：

1. **优先新增 contract / validator / helper**——低风险；新增文件，**不**触
   active path
2. **优先不接 active path**——validator / helper 不被 active code 调用；
   失败回滚不影响主链
3. **优先不碰 UI / app.py / predict.py / orchestrator**——这些是 high-risk
   surface；留待后续批次
4. **优先不删除 legacy**——任何 delete 走 16H 决策表 + 17A+ archive PR；
   第一批不做
5. **优先不改业务逻辑**——第一批只做"标准 schema 落地"，不动 schema
   生产端
6. **优先增强边界测试**——boundary tests / forbidden imports / no-prediction-output
   tests 配套加
7. **每个 PR 单独 commit**——单 commit 单 batch；不允许"一个 commit 改两个层"
8. **失败可 git revert**——每个 commit 必须可独立 revert，不留连锁回滚陷阱
9. **不跨层**——除非明确写跨层理由，否则 PR 文件范围必须**只命中**所属层
   的目录 / 文件
10. **不进入 trading / hard / forced / buy / sell / hold**——永久禁止
    （1.0 §6 / §13 / §12）

**默认 reject 路径**：

- 不满足以上任一条 → **不进入**第一批
- 即使满足以上全部，仍需**用户单独确认**才能启动对应 batch

---

## 4. 候选 PR 总池

> **来源**：17E ~ 17M 各层 §13 / §14 / §13.x / 类似章节列出的 PR-* 候选
> 清单。本节按层组织，每个候选简述：来源 plan 章节 / 所属层 / 是否改
> active path / 风险 L/M/H / 是否推荐第一批。

### 4.1 Data Layer（Branch 1）— 17E §13

| 候选 | 来源 | 所属层 | 改 active path？ | 风险 | 第一批推荐？ |
|---|---|---|---|---|---|
| **PR-DATA-1** Data source inventory + no-live-network boundary tests | 17E §13 | Branch 1 | NO（仅 tests） | L | 备选；不强制 |
| **PR-DATA-2** standard market data schema helper | 17E §13 | Branch 1 | NO（新增 helper） | L | **本可入第一批，但 18A 选择以 contract validator 为主轴；Data Layer 输入是外部数据，更偏 infra；推荐放第二批** |

### 4.2 Feature Layer（Branch 2）— 17F §13

| 候选 | 来源 | 所属层 | 改 active path？ | 风险 | 第一批推荐？ |
|---|---|---|---|---|---|
| **PR-FEATURE-1** feature_payload contract helper | 17F §13 | Branch 2 | NO（新增 helper） | L | ✅ **第一批 + 第一刀** |
| **PR-FEATURE-2** 15d window builder | 17F §13 | Branch 2 | NO（新增函数） | L | NO（业务变更性大于 contract validator；放后续批次） |
| **PR-FEATURE-3** raw / adj price basis tagging | 17F §13 | Branch 2 | YES（加 metadata key） | L | NO（影响输出 schema） |
| **PR-FEATURE-4** scanner / encoder boundary split | 17F §13 | Branch 2 | NO（仅 tests / docstring） | L | 备选 |
| **PR-FEATURE-5** matcher input vs evaluation split | 17F §13 | Branch 2 | NO（仅 tests / docstring） | L | 备选 |
| **PR-FEATURE-6** data_query feature enrichment split | 17F §13 | Branch 2 | YES（拆分模块） | M | NO（业务面太大） |
| **PR-FEATURE-7** peer_alignment extension boundary tests | 17F §13 | Branch 2 | NO（仅 tests） | L | 备选 |

### 4.3 Projection Layer（Branch 3）— 17G §13

| 候选 | 来源 | 所属层 | 改 active path？ | 风险 | 第一批推荐？ |
|---|---|---|---|---|---|
| **PR-PROJ-1** projection_result contract validator helper | 17G §13 | Branch 3 | NO（新增 helper） | L | ✅ 第一批 |
| **PR-PROJ-2** main_projection_layer 输出 standard projection_result keys | 17G §13 | Branch 3 | YES（加 alias 字段） | L | NO（属第二批；改输出 schema） |
| **PR-PROJ-3** historical_probability 归位 + boundary tests | 17G §13 | Branch 3 | NO（仅 docstring + tests） | L | 备选 |
| **PR-PROJ-4** primary_20day_analysis 去重 / 降级 / 合并 | 17G §13 | Branch 3 | NO（仅 docstring marker） | L | NO（marker 可推迟到 17J 之后） |
| **PR-PROJ-5** scanner scan_bias 迁出或冻结 | 17G §13 | Branch 3 | NO（仅 docstring marker） | L | NO（要等 17M UI 协同） |
| **PR-PROJ-6** orchestrator projection caller boundary tests | 17G §13 | Branch 3 | NO（仅 tests） | L | NO（要等 17J 之后） |
| **PR-PROJ-7** legacy projection bridge deprecation marker | 17G §13 | Branch 3 | NO（仅 docstring） | L | NO（属 PR-G 子集；暂停） |

### 4.4 Exclusion Layer（Branch 4）— 17H §14

| 候选 | 来源 | 所属层 | 改 active path？ | 风险 | 第一批推荐？ |
|---|---|---|---|---|---|
| **PR-EXCL-1** exclusion_result contract validator helper | 17H §14 | Branch 4 | NO（新增 helper） | L | ✅ 第一批 |
| **PR-EXCL-2** exclusion_layer 输出 standard exclusion_result keys | 17H §14 | Branch 4 | YES（加输出字段） | L | NO（属第二批） |
| **PR-EXCL-3** triggered_rule → triggered_rules / excluded_states migration | 17H §14 | Branch 4 | YES（schema migration） | L | NO（依赖 PR-EXCL-2） |
| **PR-EXCL-4** false_exclusion_risk 标准化 | 17H §14 | Branch 4 | YES（业务派生） | L | NO（属第二批） |
| **PR-EXCL-5** anti_false_exclusion 模块归位 / freeze marker | 17H §14 | Branch 4 | NO（仅 docstring） | L | NO（要等 17K / 17L 之后） |
| **PR-EXCL-6** contradiction / warning 模块迁出 Exclusion 标识 | 17H §14 | Branch 4 | NO（仅 docstring） | L | NO（要等 17J / 17K 之后） |
| **PR-EXCL-7** consistency_layer 迁出或归 Final Report 标识 | 17H §14 | Branch 4 | NO（仅 docstring） | L | NO（要等 17J 之后） |
| **PR-EXCL-8** exclusion caller boundary tests | 17H §14 | Branch 4 | NO（仅 tests） | L | NO（要等 17I 之后） |

### 4.5 Confidence Layer（Branch 5）— 17I §13

| 候选 | 来源 | 所属层 | 改 active path？ | 风险 | 第一批推荐？ |
|---|---|---|---|---|---|
| **PR-CONF-1** confidence_result contract validator helper | 17I §13 | Branch 5 | NO（新增 helper） | L | ✅ 第一批 |
| **PR-CONF-2** confidence_evaluator schema adapter（PR-E 实质 part 1） | 17I §13 | Branch 5 | YES（改 `_compute_agreement`） | M | **NO（第二批；详见 §6）** |
| **PR-CONF-3** explicit calibration_context ready=False（PR-E 实质 part 2） | 17I §13 | Branch 5 | YES（改 3 个 caller） | L | **NO（第二批；与 PR-CONF-2 协同）** |

### 4.6 Final Report Layer（Branch 6）— 17J §13

| 候选 | 来源 | 所属层 | 改 active path？ | 风险 | 第一批推荐？ |
|---|---|---|---|---|---|
| **PR-FINAL-1** final_report_result contract validator helper | 17J §13 | Branch 6 | NO（新增 helper） | L | ✅ 第一批 |
| **PR-FINAL-2** final_decision passthrough / non-mutation hardening | 17J §13 | Branch 6 | YES（删 dead helper） | L | NO（涉及生产 module 删 helper） |
| **PR-FINAL-3** consistency_layer freeze / migrate decision marker | 17J §13 | Branch 6 | NO（仅 docstring） | L | 备选 |
| **PR-FINAL-4** warning_cards schema for contradiction / tail warning | 17J §13 | Branch 6 | YES（加 section + 新模块） | M | NO（与 17K PR-REVIEW-2 紧耦合；详见 §7） |
| **PR-FINAL-5** projection_chain_contract split plan or marker | 17J §13 | Branch 6 | NO（仅 docstring） | L | 备选 |
| **PR-FINAL-6** contract_payload translation isolation | 17J §13 | Branch 6 | NO（仅 docstring） | L | NO（要等 17M 协同） |
| **PR-FINAL-7** architecture_orchestrator ownership doc / marker | 17J §13 | Branch 6 | 文档 only | L | NO（属 §9 不先做范围） |
| **PR-FINAL-8** narrative summary helper boundary tests | 17J §13 | Branch 6 | NO（仅 tests） | L | 备选 |

### 4.7 Review & Learning Layer（Branch 7）— 17K §17

| 候选 | 来源 | 所属层 | 改 active path？ | 风险 | 第一批推荐？ |
|---|---|---|---|---|---|
| **PR-REVIEW-1** review_result contract helper / validator | 17K §17 | Branch 7 | NO（新增 helper） | L | ✅ 第一批 |
| **PR-REVIEW-2** `_apply_briefing_caution` 改为 warning-only / marker | 17K §17 | Branch 7 | YES（关键违反修复） | **H** | **NO（第二批以后；详见 §7）** |
| **PR-REVIEW-3** briefing read-only boundary tests | 17K §17 | Branch 7 | NO（仅 tests） | L | 备选 |
| **PR-REVIEW-4** review_store / memory_store lifecycle schema plan | 17K §17 | Branch 7 | 文档 only | L | 备选（文档） |
| **PR-REVIEW-5** exclusion_reliability_review 归位 / freeze marker | 17K §17 | Branch 7 | NO（仅 docstring） | L | 备选 |
| **PR-REVIEW-6** anti_false_exclusion_audit 归位 / freeze marker | 17K §17 | Branch 7 | NO（仅 docstring） | L | 备选 |
| **PR-REVIEW-7** outcome_capture boundary tests | 17K §17 | Branch 7 | NO（仅 tests） | L | 备选 |
| **PR-REVIEW-8** memory rule lifecycle plan | 17K §17 | Branch 7 | 文档 only | L | 备选（文档） |

### 4.8 Evaluation Layer（Branch 8）— 17L §16

| 候选 | 来源 | 所属层 | 改 active path？ | 风险 | 第一批推荐？ |
|---|---|---|---|---|---|
| **PR-EVAL-1** evaluation_result contract helper / validator | 17L §16 | Branch 8 | NO（新增 helper） | L | ✅ 第一批 |
| **PR-EVAL-2** 2026 holdout boundary tests | 17L §16 | Branch 8 | NO（仅 tests） | L | 备选 |
| **PR-EVAL-3** historical replay manifest standard | 17L §16 | Branch 8 | NO（新增 schema + helper） | L | 备选 |
| **PR-EVAL-4** confidence calibration summary contract | 17L §16 | Branch 8 | NO（新增 schema） | L | 备选（与 17I 协同） |
| **PR-EVAL-5** anti_false_exclusion_dashboard data/UI split marker | 17L §16 | Branch 8 | NO（仅 docstring） | L | NO（要等 17M 协同） |
| **PR-EVAL-6** contract payload inspector / dashboard boundary marker | 17L §16 | Branch 8 | NO（仅 docstring） | L | 备选 |
| **PR-EVAL-7** active_rule_pool_calibration offline-only boundary tests | 17L §16 | Branch 8 | NO（仅 tests） | M | 备选 |
| **PR-EVAL-8** raw artifact guard tests | 17L §16 | Branch 8 | NO（仅 tests） | L | 备选 |

### 4.9 UI / Presentation Layer（Branch 9）— 17M §16

| 候选 | 来源 | 所属层 | 改 active path？ | 风险 | 第一批推荐？ |
|---|---|---|---|---|---|
| **PR-UI-1** presentation_payload / view_model contract helper | 17M §16 | Branch 9 | NO（新增 helper） | L | ✅ 第一批 |
| **PR-UI-2** Inspect tab standard payload display | 17M §16 | Branch 9 | YES（加 inspect_tab section） | L | NO（碰 ui/，要等第二批） |
| **PR-UI-3** History tab read-only standard payload display | 17M §16 | Branch 9 | YES（加 fallback） | L | NO（碰 ui/） |
| **PR-UI-4** Review tab review_result display | 17M §16 | Branch 9 | YES（加 review_tab） | L | NO（要等 17K PR-REVIEW-1 / 2） |
| **PR-UI-5** Evaluation dashboard display-only split | 17M §16 | Branch 9 | YES（拆分） | M | NO（要等 17L 协同） |
| **PR-UI-6** warning_cards renderer | 17M §16 | Branch 9 | YES（新增 ui helper + 集成） | M | NO（要等 17J PR-FINAL-4 协同） |
| **PR-UI-7** Predict tab compatibility fallback explicit | 17M §16 | Branch 9 | YES（改 predict_tab 主入口） | **H** | **NO（详见 §8）** |
| **PR-UI-8** app.py tab shell stabilization | 17M §16 | Branch 9 | NO（仅 docstring） | L | 备选 |
| **PR-UI-9** legacy final_bias / final_confidence read deprecation marker | 17M §16 | Branch 9 | NO（仅 docstring） | L | 备选 |

---

## 5. 第一批推荐路线

按"先把标准接口立住，再改业务模块"原则，第一批以 **contract validator
为主轴**——每一层先落 result / payload contract helper + tests，让后续
PR 有共同的 schema 出处。

**推荐顺序**（按数据流方向 Data → Feature → Projection → Exclusion →
Confidence → Final Report → Review → Evaluation → UI；Data 层 contract
留作备选）：

| 顺序 | 候选 PR | 所属层 | 来源 | 性质 | 风险 |
|---|---|---|---|---|---|
| 1 | **PR-FEATURE-1** feature_payload contract helper / validator | Branch 2 Feature | 17F §13 | 新增 helper + tests | L |
| 2 | **PR-PROJ-1** projection_result contract helper / validator | Branch 3 Projection | 17G §13 | 新增 helper + tests | L |
| 3 | **PR-EXCL-1** exclusion_result contract helper / validator | Branch 4 Exclusion | 17H §14 | 新增 helper + tests | L |
| 4 | **PR-CONF-1** confidence_result contract helper / validator | Branch 5 Confidence | 17I §13 | 新增 helper + tests | L |
| 5 | **PR-FINAL-1** final_report_result contract helper / validator | Branch 6 Final Report | 17J §13 | 新增 helper + tests | L |
| 6 | **PR-REVIEW-1** review_result contract helper / validator | Branch 7 Review | 17K §17 | 新增 helper + tests | L |
| 7 | **PR-EVAL-1** evaluation_result contract helper / validator | Branch 8 Evaluation | 17L §16 | 新增 helper + tests | L |
| 8 | **PR-UI-1** presentation_payload / view_model contract helper | Branch 9 UI | 17M §16 | 新增 helper + tests | L |

**说明**：

- 这一批都是"**新建 contract / validator / tests**"，**不**接 active path，
  风险**最低**
- 与 17A 已落地的 `standard_projection_payload.v1` 体例一致（`SCHEMA_VERSION` +
  required keys + `validate_*(result) -> list[str]` 纯函数 validator）
- 这一批落地后，每一层就有了"标准 schema 出处"，后续业务 PR（PR-PROJ-2 /
  PR-EXCL-2 / PR-CONF-2 / ...）才有锚点
- 这符合先把标准接口立住，再改业务模块的原则
- 这一批**不**回答"哪一行业务代码改哪里"；只回答"每一层的输出长什么样"
- Data Layer 的 contract（PR-DATA-2）**不**进入第一批：Data Layer 的输入是
  外部数据（OHLCV）；它的"contract"更像"标准化字段集合"（OHLCV + Adj
  Close + Volume），与"system result schema"性质不同；放第二批 / Data Layer
  专属批次更合适

---

## 6. 为什么不先做 PR-CONF-2 / PR-CONF-3

> **PR-CONF-2 / PR-CONF-3 是 16I PR-E（confidence key 对齐）的实质内容。
> 17I §13 已经把 PR-E 拆成 PR-CONF-2（schema adapter）+ PR-CONF-3（caller
> 显式传 `calibration_context = {"ready": False}`）。**

- ✅ 方向正确——`agreement_status` 长期 `unknown` 是当前用户视角下最显眼
  的 confidence 问题；把 standard schema 优先 + interim fallback 落地，
  确实能解决根因
- ❌ 但**会改 active path**：
  - PR-CONF-2 改 `services/confidence_evaluator.py` 中 `_compute_agreement`
    的逻辑，直接影响 confidence 输出
  - PR-CONF-3 改 `services/home_terminal_orchestrator.py:169` /
    `services/projection_orchestrator_v2.py:483, 585` 三个 caller，影响
    生产链路
- ❌ 且**前置依赖未落地**：
  - PR-CONF-2 的"standard schema 优先"只有在 main_projection_layer 输出
    `most_likely_state` / `ranked_states`（PR-PROJ-2）+ exclusion_layer
    输出 `most_unlikely_state` / `ranked_unlikely_states`（PR-EXCL-2）
    之后才能"长期生效"；否则只是 fallback 到 interim schema
  - 在没有 confidence_result contract（PR-CONF-1）保障的前提下，PR-CONF-2
    改输出会让 contract 偏移无法事后回查

**结论**：

- PR-CONF-2 / PR-CONF-3 **必须等** confidence_result contract helper
  （PR-CONF-1）先落地
- PR-CONF-2 / PR-CONF-3 **应作为第二批候选**，不是第一批第一刀
- 17D §9 已写明"PR-E 暂停；归入 17I"；本 18A 接续：PR-E 的实质内容（PR-CONF-2 +
  PR-CONF-3）等 PR-CONF-1 入 main 之后**单独**走 18B+ 评估

---

## 7. 为什么不先修 _apply_briefing_caution

> **`predict.py:_apply_briefing_caution` 是 1.0 / 06 / 07A / 07B / 07C /
> 07D 锁定的"复盘只能事后学习，不能当次改答案"的关键违反点：
> 当前实现**直接修改** `result["final_confidence"]`。**

- ✅ 方向正确——必须把 briefing caution 改为 warning-only（不 mutate
  confidence；只追加 marker），并把 caution 信息透传到 `final_report.warning_cards`
  / `final_report.risks`
- ❌ 但**风险 H**（17K §17 已显式标注 H）：
  - 触及 `predict.py`（TEMP_MIGRATION_BRIDGE 中的核心 active 模块）
  - 涉及 caller path 重新接线（caution 信息必须能透传到 final_report）
- ❌ 且**跨多层**：
  - Review Layer（briefing caution 行为）
  - Final Report Layer（warning_cards 的容器；17J PR-FINAL-4 schema）
  - Confidence Layer（被错误 mutate 的目标字段；与 17I 边界协同）
- ❌ 且**前置依赖未落地**：
  - `final_report.warning_cards` schema（17J PR-FINAL-4）尚未实现 → 没有
    透传容器
  - `review_result` contract（17K PR-REVIEW-1）尚未实现 → 没有 review_record
    的标准 schema 接口
  - confidence_result contract（17I PR-CONF-1）尚未实现 → 不能保障 confidence
    侧"被 caution 影响 vs 不被影响"的对照测试

**结论**：

- `_apply_briefing_caution` 修复必须等：
  - `final_report_result` contract helper（PR-FINAL-1）落地
  - `review_result` contract helper（PR-REVIEW-1）落地
  - `confidence_result` contract helper（PR-CONF-1）落地
  - `warning_cards` schema（PR-FINAL-4）落地
- 在第一批（contract helper 八件套）之后，第二批 / 第三批再讨论 PR-REVIEW-2
- **不能作为第一批第一刀**

---

## 8. 为什么不先迁 UI

> **17M Predict tab 主面板（`ui/predict_tab.py`）当前仍读 legacy 字段
> `final_bias` / `final_confidence` / `primary_projection` / `final_projection`。
> Bridge #1 退出条件 #1 = "UI 全部读新 final_report schema"。**

- ✅ 方向正确——UI 必须最终迁移到 standard schema
- ❌ 但**风险 H**，尤其 Predict tab：
  - PR-UI-7（17M §16 已显式标注 H）
  - Predict tab 是 app.py 主入口；任何字段读取偏差会直接影响用户面板
- ❌ 且**前置依赖未落地**：
  - `standard_projection_payload.v1`（17A PR-B）已落 ✅
  - `final_report_result` contract（17J PR-FINAL-1）尚未实现 → UI 不知道
    "新 schema 的 final_report 长什么样"
  - `review_result` contract（17K PR-REVIEW-1）尚未实现 → UI Review tab
    不知道 review_record 标准字段
  - `evaluation_result` contract（17L PR-EVAL-1）尚未实现 → UI Evaluation
    dashboard 不知道 evaluation 标准字段

**Inspect tab 是否可以作为低风险 UI 第一刀**：

- 17M §9 顺序 1 = Inspect tab（低风险）
- 但 PR-UI-2 实际改 `ui/inspect_tab.py`，仍然碰 `ui/` 目录
- 18A 第一批的"避碰 UI / app.py / predict.py / orchestrator"原则是
  **绝对原则**——`ui/inspect_tab.py` 也算 UI
- **PR-UI-1** presentation_payload / view_model contract helper（新增
  `ui/presentation_payload_contract.py`）虽然写在 `ui/` 目录，但只新增
  contract validator helper，**不**改任一现有 ui tab 行为，符合"contract
  validator only"原则——这是 UI Layer 唯一能进入第一批的候选

**结论**：

- UI 迁移**必须等** standard payload / final_report / review_result /
  evaluation_result contract 稳定后再迁
- Inspect tab 可以作为后续低风险 UI 第一刀（18C / 18B 之后某轮），但
  **不是** 18A 第一批首选
- 18A 第一批 UI 候选只取 **PR-UI-1**（contract helper only），**不**取
  PR-UI-2 / PR-UI-3 / PR-UI-4 / PR-UI-7

---

## 9. 为什么不先做 architecture_orchestrator

> **`architecture_orchestrator` 是 16I PR-F 的目标——把 Data → Feature →
> Projection → Exclusion → Confidence → Final Report 的物理调用收敛到
> 唯一一处。17J PR-FINAL-7 把 architecture_orchestrator 的 ownership 写
> 成"ASSEMBLY_ORCHESTRATION_LAYER / TEMP_FUTURE_ORCHESTRATOR"——**
>
> > **`architecture_orchestrator` 不在 9 分支正式架构内。**
> >
> > 它是组装层；它的存在是为了把九分支正式契约"接起来"，本身不是
> > 一个 branch，也不是某个层的成员。

- ❌ 它**依赖**：
  - feature_payload contract（PR-FEATURE-1）
  - projection_result contract（PR-PROJ-1）
  - exclusion_result contract（PR-EXCL-1）
  - confidence_result contract（PR-CONF-1）
  - final_report_result contract（PR-FINAL-1）
  - 以及对应**生产端** standard schema 输出（PR-PROJ-2 / PR-EXCL-2 /
    PR-CONF-2 等）
- ❌ 在没有 contract helper 落地之前，新建 `services/architecture_orchestrator.py`
  会写出"无 schema 校验 + 字段散落"的临时代码，正是 16F no-patching 要
  避免的反例
- ❌ 17J §13 PR-FINAL-7 已经把 architecture_orchestrator 的"真正实现 PR
  的前置条件"写明：**PR-FEATURE-1 / PR-PROJ-1 / PR-EXCL-1 / PR-CONF-1 /
  PR-FINAL-1 全部落地 + PR-FEATURE-2 / PR-PROJ-2 / PR-EXCL-2 / PR-CONF-2 /
  PR-CONF-3 / PR-FINAL-2 standard schema 输出落地** 之后才能开

**结论**：

- `architecture_orchestrator` 必须等各 result contract helper 落地后再实现
- **不能现在直接做**
- 17D §10.3 已写明"architecture_orchestrator MVP 暂停；归入 17J"；本 18A
  接续：18A 第一批不含 architecture_orchestrator；最早在第一批 8 件套全部
  落地之后单独评估

---

## 10. 第一批 PR 的统一验收标准

每个 contract helper PR（§5 推荐顺序的 8 件套）必须**同时**满足：

| # | 标准 | 说明 |
|---|---|---|
| 1 | 只新增 helper + tests | 不改任何已有 module；不删任何文件；不移动任何文件 |
| 2 | 不接 active path | 该 helper 不被 production code 调用；如有 import 仅为 tests / type hints |
| 3 | 不改业务逻辑 | 不修改 main_projection_layer / exclusion_layer / confidence_evaluator / final_decision / review_orchestrator 的输出语义 |
| 4 | 不 import predict.py | helper 模块**不** `from predict import *`；不 transit predict 内部 |
| 5 | 不 import UI | helper 模块**不** `import streamlit` / `import ui.*`（UI Layer 例外：PR-UI-1 在 `ui/` 目录但**不** import streamlit；只定义纯 dict / 纯函数 validator） |
| 6 | 不 import DB | helper 模块**不** `import sqlite3` / 不 `from services.market_data_store import *`（store 是 caller，不是 contract） |
| 7 | validator 不 mutate input | `validate_*(result) -> list[str]`：仅返回 errors list；**不**写回 input；**不** raise 业务异常 |
| 8 | validator 返回 errors list，不抛业务异常 | 内部仅 raise `TypeError` / `ValueError` 表示输入类型严重错误（如 `result is not a dict`）；schema-level 不 match 走 errors list |
| 9 | 禁止 trading / hard / forced / required / buy / sell / hold 字段 | contract `_FORBIDDEN_FIELDS` 必须显式禁止；validator 必须检测；tests 必须覆盖 |
| 10 | focused tests 通过 | 每个 PR 的 focused tests（同 commit 新增）100% 通过 |
| 11 | related tests 通过 | 该层已有 boundary tests / contract tests 全绿 |
| 12 | full pytest 通过 | Step 15 baseline = **3256 passed, 10 skipped, 0 failed, 26 warnings, 94 subtests**；新增测试数显式累加到 passed |
| 13 | scripts/check.sh 通过 | 统一检查脚本通过（CLAUDE.md hard rule 6） |
| 14 | git diff 只含目标文件 | `git diff --stat` 只命中 `services/<contract>.py` + `tests/test_<contract>.py`（PR-UI-1 命中 `ui/<contract>.py` + `tests/`） |
| 15 | 可单独 git revert | 单 commit；可 `git revert <sha>` 回滚；不留连锁状态 |

---

## 11. 第一批 PR 分组方式

**建议不要一次做 8 个**——避免单个大 commit 把多层标准混在一起。

**建议分组**（每个 batch 独立 PR / commit / regression）：

| Batch | PR | 所属层 | 估计风险 | 估计工作量 |
|---|---|---|---|---|
| **Batch 18B** | PR-FEATURE-1 | Branch 2 Feature | L | 1 PR，~150 lines code + ~200 lines tests |
| **Batch 18C** | PR-PROJ-1 | Branch 3 Projection | L | 1 PR，~150 lines code + ~200 lines tests |
| **Batch 18D** | PR-EXCL-1 | Branch 4 Exclusion | L | 1 PR，~150 lines code + ~200 lines tests |
| **Batch 18E** | PR-CONF-1 | Branch 5 Confidence | L | 1 PR，~150 lines code + ~200 lines tests |
| **Batch 18F** | PR-FINAL-1 | Branch 6 Final Report | L | 1 PR，~150 lines code + ~200 lines tests |
| **Batch 18G** | PR-REVIEW-1 | Branch 7 Review | L | 1 PR，~150 lines code + ~200 lines tests |
| **Batch 18H** | PR-EVAL-1 | Branch 8 Evaluation | L | 1 PR，~150 lines code + ~200 lines tests |
| **Batch 18I** | PR-UI-1 | Branch 9 UI | L | 1 PR，~150 lines code + ~200 lines tests |

**说明**：

- **每个 batch 独立 PR / commit / regression**——单 commit 单 batch；不允许
  "一个 commit 改两个层"
- **不合并多个层的实现到一个 commit**——即使 PR-FEATURE-1 + PR-PROJ-1 内容
  极相似（contract 结构对称），也必须分两个 commit
- **每个 batch 必须**：用户单独确认 → builder → reviewer → tester → 入 main
- **顺序硬约束**：上游层先（Feature → ... → UI 顺序最好接近数据流方向），
  但每个 batch 之间**没有强制顺序依赖**（contract validator 互不依赖）；
  如果某个 batch 卡壳，可以跳过到下一个
- **回滚策略**：每个 batch 失败时 `git revert <sha>` 即可；不需要连锁回滚
  上游 batch

---

## 12. 第一刀推荐

**明确推荐**：

> **Step 18B / PR-FEATURE-1：feature_payload contract helper / validator**

**理由**：

- **Feature Layer 是 Data 后第一层**——后续 Projection / Exclusion / Confidence
  全部依赖 feature_payload；先把 Feature 的 contract 立住，再向下游扩散
  最自然
- **后续 Projection / Exclusion 都依赖 feature_payload**——17F §13 / 17G §6 /
  17H §6 / 17I §10 的 standard schema 都引用 feature_payload 字段
- **新增 helper，不接 active path，风险低**——不动 `compute_20d_features` /
  `build_feature_payload_from_recent_window` 任何行为
- **与 17F Feature Layer Plan 直接对应**——17F §13 PR-FEATURE-1 显式定义了
  这个候选；本 PR 是按 17F 直接 1:1 实施
- **不碰 predict.py / UI / orchestrator / DB**——文件范围只命中
  `services/feature_payload_contract.py` + `tests/test_feature_payload_contract.py`
- **不改变业务逻辑**——validator 是纯函数；不修改任何 caller；不影响任何
  生产输出

**对比为什么不是 PR-PROJ-1 / PR-EXCL-1 / PR-CONF-1 等其他 contract**：

- PR-PROJ-1 / PR-EXCL-1 / PR-CONF-1 / PR-FINAL-1 / PR-REVIEW-1 / PR-EVAL-1 /
  PR-UI-1 都符合"contract helper only"原则，但它们的 schema 引用 feature_payload
  字段（如 `feature_snapshot` / `metadata.window_days` / `peer_alignment`
  等）；先固定 feature_payload，让下游 contract 能直接 reference，后续 PR
  描述可以写"`projection_result.feature_payload_ref` 引用 feature_payload.v1
  §X.Y"
- 17A PR-B 已经落了 `standard_projection_payload.v1`（这是 input payload，
  不是 output result；与 feature_payload 性质不同——standard_projection_payload
  是给 main_projection_layer 喂进去的，feature_payload 是 Feature Layer
  自身输出），所以 PR-FEATURE-1 是 Feature Layer 自身 result contract
  的**首发**

---

## 13. Step 18B 的边界草案

> **本节是 Step 18B 草案，不是实现**。本轮 18A 不实现任何代码；草案只
> 用来界定后续 18B 的范围。

### 13.1 目标文件候选

| 文件 | 性质 | 内容草案 |
|---|---|---|
| `services/feature_payload_contract.py` | 新增 helper | `FEATURE_PAYLOAD_SCHEMA_VERSION` 常量 + `FEATURE_PAYLOAD_REQUIRED_SECTIONS` 常量 + `validate_feature_payload(payload: dict) -> list[str]` 纯函数 |
| `tests/test_feature_payload_contract.py` | 新增 tests | full coverage of validator behavior |

### 13.2 功能草案

```python
# services/feature_payload_contract.py 草案（不实现）

FEATURE_PAYLOAD_SCHEMA_VERSION = "feature_payload.v1"

FEATURE_PAYLOAD_REQUIRED_SECTIONS = (
    "schema_version",
    "metadata",
    "ohlcv_window",
    "returns",
    "position",
    "volume",
    "candle",
    "peer_alignment",
    "code_features",
    "data_quality",
)

_FORBIDDEN_FIELDS = (
    # projection / exclusion / confidence / final_report 不允许出现
    "most_likely_state",
    "most_unlikely_state",
    "predicted_top1",
    "predicted_top2",
    "ranked_states",
    "ranked_unlikely_states",
    "state_probabilities",
    "projection_result",
    "exclusion_result",
    "confidence_result",
    "final_report",
    # trading / hard / forced 永久禁止
    "trading_action",
    "simulated_trade",
    "buy",
    "sell",
    "hold",
    "hard",
    "forced",
    "required",
    "_PROTECTION_LAYER_CONNECTED",
)


def validate_feature_payload(payload: dict) -> list[str]:
    """Return list of human-readable error messages; empty list = valid.

    Pure function. Does not mutate input. Does not raise business errors;
    only raises TypeError if payload is not a dict.
    """
    ...
```

### 13.3 必须包含的 required sections

| section | 含义 | 来源 |
|---|---|---|
| `schema_version` | `"feature_payload.v1"` 字符串 | 17F §6 |
| `metadata` | symbol / target_date / window_days / data_source 等 | 17F §6 / §10 |
| `ohlcv_window` | window 内 OHLCV 切片 | 17E §8 |
| `returns` | ret1 / ret3 / ret5 / ret10 / ret20 | 17F §6 |
| `position` | pos20 / pos15（未来） / near_high / near_low | 17F §6 |
| `volume` | vol_ratio20 / volume_zscore | 17F §6 |
| `candle` | upper_shadow_ratio / lower_shadow_ratio / etc. | 17F §6 |
| `peer_alignment` | NVDA / SOXX / QQQ alignment 输出（来自 17B PR-C `peer_alignment.v1`） | 17F §6 / 17B PR-C |
| `code_features` | 5-digit code 派生（O_code / H_code / L_code / C_code / V_code / Code） | 17F §7 / encoder.py |
| `data_quality` | 缺失日 / 缺列 / 重复日 / 异常值标记 | 17F §6 / 17E §12.3 |

### 13.4 禁止字段（contract 显式 reject）

`_FORBIDDEN_FIELDS` 必须显式禁止以下任一项**出现在** feature_payload 中：

- ❌ `projection_result` / `most_likely_state` / `predicted_top1` /
  `predicted_top2` / `ranked_states` / `state_probabilities`
- ❌ `exclusion_result` / `most_unlikely_state` / `ranked_unlikely_states`
- ❌ `confidence_result` / `combined_confidence` / `agreement_status`
- ❌ `final_report` / `combined_user_summary` / `risk_disclosure`
- ❌ `trading_action` / `simulated_trade` / `buy` / `sell` / `hold`
- ❌ `hard` / `forced` / `required` / `_PROTECTION_LAYER_CONNECTED`

### 13.5 测试覆盖草案

| 测试类 | 数量 | 内容 |
|---|---|---|
| valid payload tests | ≥3 | 完整 payload 通过 validator (returns []) |
| missing section tests | ≥10 | 每个 required section 缺失 → errors list 含对应 message |
| extra section tests | ≥3 | extra non-required sections allowed by default |
| forbidden field tests | ≥10 | `_FORBIDDEN_FIELDS` 中每一项出现 → errors list 含对应 message |
| schema_version mismatch | ≥3 | 错误版本 / null / 缺失 → error |
| no mutation tests | ≥1 | validator 调用前后 payload byte-stable |
| pure-function tests | ≥1 | 同输入两次调用 errors list 一致 |
| trading-keyword post-check | ≥10 | trading / hard / forced / required / buy / sell / hold post-check |
| boundary tests | ≥3 | forbidden imports（不 import predict / UI / DB / projection / exclusion / confidence / final_decision / review / evaluation） |

> **本草案只用来界定 18B 范围**；实际 18B 实现细节由 builder 在用户单独
> 确认 18B 启动后给出。

---

## 14. 本轮不允许事项

**18A 起，本轮（直到用户确认 18B 启动之前）严格禁止**：

- ❌ 不改代码（无 `.py` 文件被修改；本轮 0 修改）
- ❌ 不新增测试（`tests/` 字节不变）
- ❌ 不跑 pytest（除 readonly 校验外不执行 test 命令）
- ❌ 不跑 replay
- ❌ 不跑 holdout
- ❌ 不做 PR-FEATURE-1 实现（PR-FEATURE-1 留待 18B）
- ❌ 不做 confidence key（PR-CONF-2 / PR-CONF-3 留待第二批）
- ❌ 不修 `_apply_briefing_caution`（PR-REVIEW-2 留待第二批以后）
- ❌ 不迁 UI（PR-UI-2 ~ PR-UI-9 留待 18C+）
- ❌ 不实现 `architecture_orchestrator`（留待 contract helper 全部落地后）
- ❌ 不进入 3R-5 / 3R-6（1.0 §12 / 17D §11 / 17E ~ 17M §禁止 / 本轮再次重申）
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
- ❌ 不借 18A 顺手做代码改动（本轮全部 markdown 改动）

> 与 17D §11 / 17E ~ 17M §禁止事项一致；本轮再次锁定。

---

## 15. 推荐下一步

**推荐**：

> **Step 18B / PR-FEATURE-1：feature_payload contract helper / validator**

**前置条件**：

- 18A 入 main
- 用户单独确认 18B 启动

**18A 入 main 后启动顺序建议**（每个 batch 单独确认）：

1. **Step 18B**：PR-FEATURE-1 — feature_payload contract validator
2. **Step 18C**：PR-PROJ-1 — projection_result contract validator
3. **Step 18D**：PR-EXCL-1 — exclusion_result contract validator
4. **Step 18E**：PR-CONF-1 — confidence_result contract validator
5. **Step 18F**：PR-FINAL-1 — final_report_result contract validator
6. **Step 18G**：PR-REVIEW-1 — review_result contract validator
7. **Step 18H**：PR-EVAL-1 — evaluation_result contract validator
8. **Step 18I**：PR-UI-1 — presentation_payload contract validator

**18A 本轮只做 selection doc**——不启动 18B。

**不推荐**：

- 不推荐跳到 PR-CONF-2 / PR-CONF-3（必须等 PR-CONF-1）
- 不推荐跳到 PR-REVIEW-2 _apply_briefing_caution 修复（必须等 PR-REVIEW-1 +
  PR-FINAL-1 + PR-CONF-1 + PR-FINAL-4）
- 不推荐跳到 PR-UI-2 ~ PR-UI-9（必须等 PR-UI-1 + 上游 contract helper）
- 不推荐立刻做 PR-FEATURE-2 ~ PR-FEATURE-7（必须等 PR-FEATURE-1）
- 不推荐立刻做 architecture_orchestrator（必须等 contract helper 八件套全部
  落地）
- 不推荐解锁 3R-5 / 3R-6（1.0 §12 7 项前提仍未全部满足）
- 不推荐借 18A 顺手做任何代码改动（与 17D §11 一致）
- 不推荐重启 16I PR-E / PR-F / PR-G / PR-H（实质内容已被 17I / 17J / 17K /
  17L / 17M 拆开 + 17D §10 暂停 + 18A 重排）

> **明确**：本轮 18A 推荐的下一步**只有一个候选**——Step 18B / PR-FEATURE-1。
> 启动需要用户单独确认。

---

## 16. 严守边界

本轮 Step 18A **只**写 First Layer-Based Implementation Batch Selection：

- ❌ 未改代码（无 `.py` 文件被修改；`git diff --stat` 仅 markdown）
- ❌ 未新增测试（`tests/` 字节不变）
- ❌ 未删除文件
- ❌ 未移动文件
- ❌ 未修改 `.gitignore`
- ❌ 未处理 `avgo_agent.db`（16H §5 校正后无需处理）
- ❌ 未处理 handoff（worktree clean；无 deliberate untracked）
- ❌ 未处理 logs / DB backup / `.claude/worktrees/`
- ❌ 未跑 replay / validation / historical evaluation
- ❌ 未写 DB / 未改 DB schema
- ❌ 未默认迁移 `run_predict` 到 V2
- ❌ 未接 trading
- ❌ 未输出 buy / sell / hold / hard / forced / required
- ❌ 未启用任何 candidate / 未复活 `continuous_smoothing`
- ❌ 未触碰 RISK-1 / RISK-2 / RISK-3 / RISK-7 / RISK-8 / RISK-9 / RISK-10
- ❌ 未进入 3R-5 / 3R-6
- ❌ 未启动任何代码 PR（PR-FEATURE-1 候选要等 18B）
- ❌ 未直接做 confidence key patch（PR-CONF-2 / PR-CONF-3 留待第二批）
- ❌ 未直接修 `_apply_briefing_caution`（PR-REVIEW-2 留待第二批以后）
- ❌ 未直接迁 UI（PR-UI-2 ~ PR-UI-9 留待 18C+）
- ❌ 未直接实现 `architecture_orchestrator`（留待 contract helper 全部落地后）
- ❌ 未做任何局部 patch
- ❌ 未 commit / 未 push（按本轮指令）

唯一新增文件：[tasks/record_18a_first_layer_based_implementation_batch_selection.md](tasks/record_18a_first_layer_based_implementation_batch_selection.md)（本文件）。

后续修改路径：任何对 §3 选择原则 / §4 候选 PR 总池 / §5 第一批推荐路线 /
§6 PR-CONF-2 / PR-CONF-3 处理 / §7 `_apply_briefing_caution` 处理 / §8
UI 处理 / §9 `architecture_orchestrator` 处理 / §10 验收标准 / §11 分组
方式 / §12 第一刀推荐 / §13 18B 草案 / §14 禁止事项 / §15 下一步 的调整，
都必须**显式更新本文件**；同时检查是否需要同步更新 1.0 / 17D / 17E ~
17M。
