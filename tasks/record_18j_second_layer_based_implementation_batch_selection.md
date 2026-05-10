# 18J记录：Second Layer-Based Implementation Batch Selection

> 本记录是 **Step 18J：第二批按层实现 PR 选择**——第一批 contract helper
> 8 件套（18B / 18C / 18D / 18E / 18F / 18G / 18H / 18I）全部入 main 之后
> 的第二批选择决定。
>
> 本轮**只**选择第二批实现 PR，**不**写代码。1.0 canonical / 16A blueprint /
> 16B inventory / 16C target dataflow & contract decision / 16D isolation &
> quarantine plan / 16E core chain refactor plan / 16F no-patching principle /
> 16G full module decomposition standup / 16H repository clearing decision
> table / 16I core chain rebuild execution plan / 17A ~ 17C / 17D layer-by-
> layer rebuild governance / 17E ~ 17M 九层 plan / 18A first batch
> selection / 18B PR-FEATURE-1 / 18C PR-PROJ-1 / 18D PR-EXCL-1 / 18E
> PR-CONF-1 / 18F PR-FINAL-1 / 18G PR-REVIEW-1 / 18H PR-EVAL-1 / 18I
> PR-UI-1 已全部入 main（main 最新 commit `428c4ae`）。
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
> **本记录优先级**：与 17D ~ 17M / 18A 同级。冲突仲裁路径与 1.0 §14 / 17D
> §13 / 18A §16 一致：旧 records（含 18A §11 第一批分组建议）若与 18J
> 冲突，**以 18J 为准**。

---

## 1. Step 18J 目的

第一批 contract helper 8 件套已经全部入 main（feature_payload / projection_result /
exclusion_result / confidence_result / final_report_result / review_result /
evaluation_result / presentation_payload，每个层一个纯 validator helper）。
现在进入第二批选择决定。

> **本轮只选择第二批 PR，不写代码。**

具体目标——回答：

- 第二批从哪条线开始
- 为什么从这条线开始
- 第二批每个 PR 的层归属
- 第二批每个 PR 的文件范围
- 第二批每个 PR 的测试范围
- 第二批每个 PR 的回滚方式
- 是否跨层（默认 NO）
- 是否需要用户单独确认（YES，每个 batch 单独确认）

**本文件性质**：selection（选择决定），不是 design 也不是 impl。
设计与执行落地由 18K / 18L / 18M / 18N / 18O / 18P / 18Q / 18R 各 batch
分别给出，每个 batch 单独 commit / 单独 review。

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
| 18A First Layer-Based Implementation Batch Selection | ✅ commit `30c7ac0` |
| 18B PR-FEATURE-1 feature_payload.v1 contract validator | ✅ commit `3c9df83` |
| 18C PR-PROJ-1 projection_result.v1 contract validator | ✅ commit `f719d71` |
| 18D PR-EXCL-1 exclusion_result.v1 contract validator | ✅ commit `bc22937` |
| 18E PR-CONF-1 confidence_result.v1 contract validator | ✅ commit `cce8f0e` |
| 18F PR-FINAL-1 final_report_result.v1 contract validator | ✅ commit `32c2aa8` |
| 18G PR-REVIEW-1 review_result.v1 contract validator | ✅ commit `3c12acb` |
| 18H PR-EVAL-1 evaluation_result.v1 contract validator | ✅ commit `49b3683` |
| 18I PR-UI-1 presentation_payload.v1 contract validator | ✅ commit `428c4ae` |
| main 最新 commit | `428c4ae` |
| 第一批 contract helper 完成度 | **8/8** |
| full pytest baseline（18I 入 main 后） | **3753 passed, 10 skipped, 0 failed, 26 warnings, 1511 subtests passed** |
| worktree 唯一 deliberate untracked | `.claude/handoffs/task_089_post_pr_cleanup.md` |
| 战略阶段 | 从第一批 contract helper（8/8）→ **第二批实现 PR 选择（18J 本轮）** |
| 3R-5 / 3R-6 | ❌ 仍然不允许进入 |
| 第二批实现 PR | ❌ 必须等 18J 入 main + 用户单独确认后才能启动 |

**写明**：

- 17D ~ 17M 已全部入 main
- 18A ~ 18I 已全部入 main
- 九分支计划完成
- 第一批 contract helper 8/8 完成
- 现在**不能**乱开代码 PR
- 每个代码 PR 必须**绑定**九分支某一层
- 每个代码 PR 必须**引用**对应 plan 章节（17E ~ 17M 的具体 §）
- 18J **只做选择**，不做实现

**17D §6 PR 准入规则提醒**（全文复用，与 18A §2 一致）：

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

### 3.1 已就位的 standard schema validator（contract surface）

| 层 | schema_version | helper 模块 | 测试模块 | commit |
|---|---|---|---|---|
| Branch 2 Feature | `feature_payload.v1` | [services/feature_payload_contract.py](services/feature_payload_contract.py) | [tests/test_feature_payload_contract.py](tests/test_feature_payload_contract.py) | `3c9df83` |
| Branch 3 Projection | `projection_result.v1` | [services/projection_result_contract.py](services/projection_result_contract.py) | [tests/test_projection_result_contract.py](tests/test_projection_result_contract.py) | `f719d71` |
| Branch 4 Exclusion | `exclusion_result.v1` | [services/exclusion_result_contract.py](services/exclusion_result_contract.py) | [tests/test_exclusion_result_contract.py](tests/test_exclusion_result_contract.py) | `bc22937` |
| Branch 5 Confidence | `confidence_result.v1` | [services/confidence_result_contract.py](services/confidence_result_contract.py) | [tests/test_confidence_result_contract.py](tests/test_confidence_result_contract.py) | `cce8f0e` |
| Branch 6 Final Report | `final_report_result.v1` | [services/final_report_result_contract.py](services/final_report_result_contract.py) | [tests/test_final_report_result_contract.py](tests/test_final_report_result_contract.py) | `32c2aa8` |
| Branch 7 Review & Learning | `review_result.v1` | [services/review_result_contract.py](services/review_result_contract.py) | [tests/test_review_result_contract.py](tests/test_review_result_contract.py) | `3c12acb` |
| Branch 8 Evaluation | `evaluation_result.v1` | [services/evaluation_result_contract.py](services/evaluation_result_contract.py) | [tests/test_evaluation_result_contract.py](tests/test_evaluation_result_contract.py) | `49b3683` |
| Branch 9 UI | `presentation_payload.v1` | [ui/presentation_payload_contract.py](ui/presentation_payload_contract.py) | [tests/test_presentation_payload_contract.py](tests/test_presentation_payload_contract.py) | `428c4ae` |

### 3.2 当前**没有**就位的能力

> 这些能力在第一批 contract helper 阶段**有意未做**——避免 contract 与
> producer / consumer 一起改、把第一批做成大型跨层 PR。

- ❌ 这些都是 **pure validator / contract helper**，属于 schema surface
- ❌ 它们**还没有接 active path**——没有任何 production module 调用这些
  validator
- ❌ **生产链路还没有正式输出这些 standard schema**：
  - `services/main_projection_layer.py` 仍输出 `kind="main_projection_layer"` /
    `predicted_top1` / `predicted_top2`，**未**输出 `most_likely_state` /
    `ranked_states` / `non_mutation_confirmations`
  - `services/exclusion_layer.py` 仍输出 `triggered_rule` (单数) /
    `excluded` / `action`，**未**输出 `most_unlikely_state` /
    `triggered_rules` (复数) / `excluded_states` / `false_exclusion_risk` /
    `state_impossibility_scores`
  - `services/confidence_evaluator.py` 仍输出 `confidence_system_result.v1`
    （旧内部 schema），**未**输出 `confidence_result.v1` 顶层 standard
    keys
  - `services/final_decision.py` 仍输出 `final_report_aggregator_result.v1`
    + 旧 passthrough 字段（`final_direction` / `final_confidence`），**未**
    输出 `final_report_result.v1` 顶层 standard keys
- ❌ **UI 还没有读取这些 standard schema**：
  - `ui/predict_tab.py` 仍读 legacy `final_bias` / `final_confidence` /
    `primary_projection` / `final_projection`
  - `ui/inspect_tab.py` 还没有 standard payload display section
  - 任何 UI tab 都还没有 `compatibility_mode` 标注
- ❌ **Confidence 还没有基于 standard schema 做 key adapter**：
  - `_compute_agreement` 仍依赖 standard schema (`most_likely_state` /
    `most_unlikely_state` / `ranked_states` / `ranked_unlikely_states`)
    + interim schema 没有 fallback 路径
  - 当前 `home_terminal_orchestrator.py:169` /
    `projection_orchestrator_v2.py:483, 585` 三个 caller **未**显式传
    `calibration_context`，导致 `agreement_status` 长期 `unknown`（17I §10 /
    18A §6）
- ❌ **Review 还没有修 `_apply_briefing_caution`**：
  - `predict.py:_apply_briefing_caution` 仍**直接**修改
    `result["final_confidence"]`
  - 这是 1.0 / 06 / 07A / 07B / 07C / 07D 锁定的"复盘只能事后学习，
    不能当次改答案"的关键违反点（18A §7）
- ❌ `services/architecture_orchestrator.py` 仍**未存在**——assembly
  orchestrator 暂缓到 producer adapters 至少完成一轮后再选择（18A §9 /
  17J §13 PR-FINAL-7）

### 3.3 这意味着什么

第一批 contract helper 落地了**标准接口**；第二批必须开始**让生产端 /
adapter / 关键消费端真正使用这些 standard schema**，但顺序必须谨慎：

> 先让 producer 能产出，再让 consumer 能消费；不要先修局部 bug。

---

## 4. 第二批候选方向总览

### 4.1 四大方向

#### A. 生产端开始输出 standard schema

| 候选 PR | 来源 | 所属层 | 性质 | 风险 |
|---|---|---|---|---|
| **PR-FEATURE-2** | 17F §13 | Branch 2 Feature | feature_payload producer / adapter | L |
| **PR-PROJ-2** | 17G §13 | Branch 3 Projection | projection_result standard keys output | L |
| **PR-EXCL-2** | 17H §14 | Branch 4 Exclusion | exclusion_result standard keys output | L |
| **PR-FINAL-2** | 17J §13 | Branch 6 Final Report | final_report passthrough / non-mutation hardening | L |

#### B. Confidence key / agreement 修复

| 候选 PR | 来源 | 所属层 | 性质 | 风险 |
|---|---|---|---|---|
| **PR-CONF-2** | 17I §13 | Branch 5 Confidence | confidence_evaluator schema adapter（standard 优先 + interim fallback） | M |
| **PR-CONF-3** | 17I §13 | Branch 5 Confidence | explicit `calibration_context = {"ready": False}` 显式 fallback | L |

> 注：17I §10.5 已将 16I PR-E（confidence key 对齐）**实质等同于** PR-CONF-2 +
> PR-CONF-3。

#### C. Review 违规点修复

| 候选 PR | 来源 | 所属层 | 性质 | 风险 |
|---|---|---|---|---|
| **PR-REVIEW-2** | 17K §17 | Branch 7 Review | `_apply_briefing_caution` 改为 warning-only / marker | **H** |

#### D. UI 低风险第一刀

| 候选 PR | 来源 | 所属层 | 性质 | 风险 |
|---|---|---|---|---|
| **PR-UI-2** | 17M §16 | Branch 9 UI | Inspect tab standard payload display section | L |

### 4.2 暂缓清单（**第二批不进入**）

> 这些项**有方向**，但**不进入**第二批，需要等第二批基础完成后再单独评估。

- **architecture_orchestrator MVP**——未来 assembly 层；暂缓到 producer
  adapters 完成第二批后再单独评估（18A §9 / 17J §13 PR-FINAL-7）
- **Predict tab 迁移**（PR-UI-7）——风险 H；必须等 final_report producer
  adapter（PR-FINAL-2）+ confidence schema adapter（PR-CONF-2 + PR-CONF-3）
  落地后再做（17M §16 / 18A §8）
- **Bridge 清理 / archive**（PR-G / 各 bridge marker PR）——必须等所有
  active producer 都迁到 standard schema 之后再做（17D §10 / 17J §15
  PR-FINAL-3）
- **3R-5 / 3R-6**——1.0 §12 七项前提仍未全部满足，**永久不允许**通过
  cleanup / signoff 自动解锁
- **replay / holdout / calibration**——必须等 calibration_summary contract /
  replay manifest standard / anti-lookahead boundary tests 落地后再做
  （17L §16 PR-EVAL-2 / PR-EVAL-3 / PR-EVAL-4 / PR-EVAL-7）

---

## 5. 第二批选择原则

**第二批 PR 必须同时满足以下原则**（任一条不满足则**剔除**该候选）：

1. **先让生产端能生成 standard schema，再让 Confidence / UI 去消费**——
   producer first，consumer after；不要先修 consumer 的局部 bug
2. **优先 producer / adapter，不优先 consumer**——producer 决定格式；
   consumer 根据 producer 的格式调整
3. **优先低风险单层改动**——避免一次跨多个层；避免一次改主入口
4. **优先不碰 Predict tab**——Predict tab 是 app.py 主入口，PR-UI-7 风险
   H；放后续批次
5. **优先不碰 `run_predict` / `predict.py`**——`run_predict` 是 Bridge 主入口；
   `predict.py` 是 TEMP_MIGRATION_BRIDGE 内核
6. **优先不改 UI 主入口**——`app.py` / `ui/predict_tab.py` / `ui/home_tab.py`
   不在第二批范围；只允许 `ui/inspect_tab.py` 作为低风险 UI 第一刀
7. **优先不做 bridge 删除**——任何 bridge `git rm` / archive 都属于
   独立 archive PR；不在第二批范围
8. **优先不跑 replay / holdout / calibration**——不生成 raw artifacts；
   不污染 2026 holdout
9. **每个 PR 必须有**：focused tests + related tests + full pytest +
   `scripts/check.sh`
10. **每个 PR 单独 commit**——单 commit 单 batch
11. **失败可 `git revert`**——单 commit 可独立回滚

**默认 reject 路径**：

- 不满足以上任一条 → **不进入**第二批
- 即使满足以上全部，仍需**用户单独确认**才能启动对应 batch

---

## 6. 推荐第二批路线

按"先 producer，后 evaluator，后 final report，再 UI，再 review mutation
hook"原则，第二批推荐顺序：

| 顺序 | Step | 候选 PR | 所属层 | 来源 | 性质 | 风险 |
|---|---|---|---|---|---|---|
| 1 | **18K** | **PR-FEATURE-2** | Branch 2 Feature | 17F §13 | feature_payload producer / adapter skeleton | L |
| 2 | **18L** | **PR-PROJ-2** | Branch 3 Projection | 17G §13 | main_projection_layer standard projection_result adapter / output | L |
| 3 | **18M** | **PR-EXCL-2** | Branch 4 Exclusion | 17H §14 | exclusion_layer standard exclusion_result adapter / output | L |
| 4 | **18N** | **PR-CONF-2** | Branch 5 Confidence | 17I §13 | confidence_evaluator schema adapter（standard 优先 + interim fallback） | M |
| 5 | **18O** | **PR-CONF-3** | Branch 5 Confidence | 17I §13 | explicit `calibration_context = {"ready": False}` caller 显式传 | L |
| 6 | **18P** | **PR-FINAL-2** | Branch 6 Final Report | 17J §13 | final_report passthrough / non-mutation hardening | L |
| 7 | **18Q** | **PR-UI-2** | Branch 9 UI | 17M §16 | Inspect tab standard payload display | L |
| 8 | **18R** | **PR-REVIEW-2** | Branch 7 Review | 17K §17 | `_apply_briefing_caution` warning-only / marker | **H** |

**说明**：

- 这个顺序体现：**先 producer，后 evaluator，后 final report，再 UI，
  再 review mutation hook**
- 不要先修局部 bug——`_apply_briefing_caution` 修复（PR-REVIEW-2）放在最后，
  必须等 final_report passthrough（PR-FINAL-2）+ confidence schema adapter
  （PR-CONF-2 / PR-CONF-3）+ review_result contract（PR-REVIEW-1，已落地）
  + warning_cards schema（PR-FINAL-4，第三批候选）共同准备好之后再做
- **Confidence key 对齐**（18A §6 / 16I PR-E 实质 = PR-CONF-2 + PR-CONF-3）
  放在 producer 之后；这是**关键**：在 main_projection / exclusion_layer
  开始输出 standard keys 之后，PR-CONF-2 的 standard 优先 + interim
  fallback 路径才能从"interim 兼容"长期演进到"standard 直接消费"
- UI 第一刀（PR-UI-2 Inspect tab）放在 producer + Confidence 之后；这样
  Inspect tab 能直接显示新 standard payload 的 `schema_version` /
  `missing_sections` / `compatibility_mode`，不需要 fallback

---

## 7. 第一刀推荐：18K / PR-FEATURE-2

**明确推荐第二批第一刀**：

> **Step 18K / PR-FEATURE-2：feature_payload producer / adapter skeleton**

**理由**：

- **Feature 是所有下游的输入**——Projection / Exclusion / Confidence /
  Final Report 全部依赖 feature_payload；先把 feature_payload 的 producer
  立起来，下游 PR-PROJ-2 / PR-EXCL-2 / PR-CONF-2 / PR-FINAL-2 才有标准
  来源
- **Projection / Exclusion / Confidence 都依赖 feature_payload**——18A §12
  已写明这个理由；在第二批中再次确认
- **已有 feature_payload.v1 validator**（PR-FEATURE-1，commit `3c9df83`）——
  PR-FEATURE-2 可以直接 import `services.feature_payload_contract`
  做组装后的 self-check
- **可以新增 adapter，不直接改 feature_builder / scanner / matcher**——
  PR-FEATURE-2 是 adapter / skeleton，**接收**已有的 feature sections
  （来自 `services/projection_chain_contract.build_feature_payload_from_recent_window`
  / `services/features_20d.compute_20d_features` / `services/peer_alignment.build_peer_alignment`
  等已有 producer 的输出），把它们组装成 `feature_payload.v1` dict +
  调用 validator
- **风险低于直接改 main_projection / confidence / UI**——adapter 只新增
  module，**不**改任何已有 producer 内部行为
- **不碰 predict.py / app.py / orchestrator / DB**——文件范围只命中
  `services/feature_payload_adapter.py` + `tests/test_feature_payload_adapter.py`
- **符合 17F Feature Layer Plan 和 18A 选择原则**——17F §13 PR-FEATURE-2
  虽然原表述是"15d window builder"，但 18J 第二批的 PR-FEATURE-2 含义
  调整为"feature_payload producer / adapter skeleton"，这与 18A §13
  Step 18B 草案中"feature_payload contract helper / validator"完成之后的
  自然下一步一致；adapter 是 producer 与 validator 之间的桥

**对比为什么不是 PR-PROJ-2 / PR-EXCL-2 / PR-CONF-2**：

- **PR-PROJ-2** 改 `services/main_projection_layer.py` 输出新字段——是
  **active path 改动**；必须等 PR-FEATURE-2 adapter 立起来，让
  main_projection 知道 feature_payload.v1 的标准来源
- **PR-EXCL-2** 改 `services/exclusion_layer.py` 输出新字段——同样是
  **active path 改动**；同样必须等 PR-FEATURE-2 adapter 先立
- **PR-CONF-2** 改 `_compute_agreement`——consumer，必须等 PR-PROJ-2 /
  PR-EXCL-2 standard keys 落地后才能"长期生效"

PR-FEATURE-2 是**adapter only / 不接 active path**，所以是第二批最低风险
第一刀。

---

## 8. 18K / PR-FEATURE-2 草案

> **本节是 Step 18K 草案，不是实现**。本轮 18J 不实现任何代码；草案只
> 用来界定后续 18K 的范围。

### 8.1 目标文件候选

| 文件 | 性质 | 内容草案 |
|---|---|---|
| `services/feature_payload_adapter.py` | 新增 helper | `build_feature_payload_from_parts(...)` 纯函数 + 内部 validator 调用 |
| `tests/test_feature_payload_adapter.py` | 新增 tests | full coverage of adapter behavior |

### 8.2 目标

- 新增 `build_feature_payload_from_parts(...)`
- 接收**already-computed** feature sections（不计算 features）
- 组装 `feature_payload.v1` dict
- 调用 `services.feature_payload_contract.validate_feature_payload`
- 返回 payload + validation_errors（或 dict with `validation_errors` 字段）
- **不**计算 feature
- **不**读 CSV
- **不**调用 yfinance
- **不**调用 `feature_builder` / `scanner` / `matcher`
- **不**接 active path（main_projection / exclusion_layer / confidence_evaluator
  / orchestrator 都不调用此 adapter；调用关系由 18L / 18M / 18N 后续 batch
  评估）

### 8.3 最小输入

| 输入参数 | 类型 | 来源 |
|---|---|---|
| `symbol` | str | caller |
| `analysis_date` | str | caller |
| `target_date` | str | caller |
| `data_window_days` | int | caller（推荐 15；20 触发 warning） |
| `price_basis` | str | caller（`"raw"` / `"adj"` / `"dual"`） |
| `window_label` | str | caller |
| `ohlcv_window` | list | caller（已切片好的 OHLCV bars） |
| `returns` | dict | caller（含 ret1 / ret3 / ret5 / ret10） |
| `position` | dict | caller（含 pos15 / pos20 / pos30） |
| `volume` | dict | caller（含 volume / volume_ratio） |
| `candle` | dict | caller（含 upper_shadow_ratio / lower_shadow_ratio） |
| `peer_alignment` | dict | caller（来自 17B PR-C `services/peer_alignment.build_peer_alignment`） |
| `code_features` | dict | caller（来自 encoder.py） |
| `data_quality` | dict | caller（含 missing_fields / source / stale_flag） |

### 8.4 输出

```python
def build_feature_payload_from_parts(
    *,
    symbol: str,
    analysis_date: str,
    target_date: str,
    data_window_days: int,
    price_basis: str,
    window_label: str,
    ohlcv_window: list,
    returns: dict,
    position: dict,
    volume: dict,
    candle: dict,
    peer_alignment: dict,
    code_features: dict,
    data_quality: dict,
) -> dict:
    """Returns:
        {
            "schema_version": "feature_payload.v1",
            "metadata": {...},
            "ohlcv_window": [...],
            "returns": {...},
            "position": {...},
            "volume": {...},
            "candle": {...},
            "peer_alignment": {...},
            "code_features": {...},
            "data_quality": {...},
            "validation_errors": [],   # 由 validator 填入
        }
    """
    ...
```

返回的 dict **包含** `validation_errors` 字段，**不**直接 raise（与
contract validator 体例一致）。Caller 自己决定如何处理 `validation_errors`
非空的情况。

### 8.5 禁止字段（adapter 不允许从 input 透传到 payload 顶层）

`build_feature_payload_from_parts` **必须**只组装 `FEATURE_PAYLOAD_SECTIONS`
列出的 10 项 + 内部 `validation_errors` 字段；**禁止**透传以下字段（即使
caller 误传也忽略，或 raise `TypeError`）：

- `projection_result` / `exclusion_result` / `confidence_result` /
  `final_report` / `review_result` / `evaluation_result`
- `most_likely_state` / `most_unlikely_state` / `agreement_status` /
  `combined_confidence`
- `final_direction` / `final_confidence` / `final_bias`
- `trading_action` / `order` / `position_action` / `execution`
- `buy` / `sell` / `hold`
- `hard` / `forced` / `required`

### 8.6 测试覆盖草案

| 测试类 | 数量 | 内容 |
|---|---|---|
| valid parts → valid payload | ≥3 | 正常 input → 输出 dict 含完整 sections + validate 后 errors=[] |
| missing section → validation_errors 非空 | ≥10 | 各 required section 缺失 → adapter 仍返回 dict 但 `validation_errors` 含对应 message |
| no mutation of input | ≥1 | 调用前后 input 各 dict / list byte-stable |
| validator self-check call | ≥1 | adapter 内调用 `validate_feature_payload`，与直接调用 validator 结果一致 |
| no business imports | ≥1 | source 不 import `feature_builder` / `scanner` / `matcher` / `data_query` / yfinance |
| no active path | ≥1 | source 不 import `main_projection_layer` / `exclusion_layer` / `confidence_evaluator` / `final_decision` / `predict` / `app` / `ui.*` / `orchestrator` |
| no yfinance / DB / UI | ≥1 | source 不 import `yfinance` / `sqlite3` / `streamlit` |
| forbidden fields rejected | ≥10 | input 含禁字段 → adapter 不透传 / validator 报错 |
| trading-keyword post-check | ≥7 | output dict 不含 `buy` / `sell` / `hold` / `hard` / `forced` / `required` / `trading_action` |

> **本草案只用来界定 18K 范围**；实际 18K 实现细节由 builder 在用户单独
> 确认 18K 启动后给出。

---

## 9. 为什么不先做 PR-CONF-2 / PR-CONF-3

> **PR-CONF-2 / PR-CONF-3 是 16I PR-E（confidence key 对齐）的实质内容
> （17I §10.5）。**

- ✅ **方向正确**——`agreement_status` 长期 `unknown` 是当前用户视角下
  最显眼的 confidence 问题；把 standard schema 优先 + interim fallback
  落地，确实能解决根因
- ❌ **但它是 consumer，不是 producer**：
  - PR-CONF-2 改 `services/confidence_evaluator.py` 中
    `_compute_agreement` 的逻辑——这是**读** projection / exclusion
    schema 的逻辑
  - 如果 Projection / Exclusion 还**没有**稳定产出 standard schema
    （`most_likely_state` / `ranked_states` / `most_unlikely_state` /
    `ranked_unlikely_states`），PR-CONF-2 的 fallback 路径会**长期**走
    interim schema，等于"先把兼容写死"
  - 这等价于一个"**先 patch consumer，让 producer 永远不动**"的反模式，
    与 16F no-patching principle 冲突
- ❌ **不能在 producer 还没立起来时定义 consumer fallback**：
  - "standard 优先 + interim fallback"的"fallback 触发条件"应该是
    **producer 还没切换**——但如果 producer **永远**不切换（因为 PR-CONF-2
    已经把 fallback 写死、用户体感问题已经"解决"），架构永远停留在
    interim 状态
  - 这正是 1.0 §3 / 16A §2 / 17D §4 / 18A §3 反复警告的"局部 patch 反而
    掩盖根因"

**结论**：

- PR-CONF-2 / PR-CONF-3 必须等 **PR-PROJ-2 + PR-EXCL-2** 落地后做
- PR-CONF-2 在 18N（第 4 顺位），PR-CONF-3 在 18O（第 5 顺位）
- 17D §9 已写明"PR-E 暂停；归入 17I"；本 18J 接续：PR-CONF-2 / PR-CONF-3
  在第二批中明确排在 producer adapters 之后

---

## 10. 为什么不先修 _apply_briefing_caution

> **`predict.py:_apply_briefing_caution` 是 1.0 / 06 / 07A / 07B / 07C /
> 07D 锁定的"复盘只能事后学习，不能当次改答案"的关键违反点。**

- ✅ **方向正确**——必须把 briefing caution 改为 warning-only（不 mutate
  confidence；只追加 marker），并把 caution 信息透传到
  `final_report.warning_cards` / `final_report.risks`
- ❌ **但它跨多个层**：
  - Review Layer（briefing caution 行为）
  - Final Report Layer（warning_cards 容器；17J PR-FINAL-4 schema）
  - Confidence Layer（被错误 mutate 的目标字段；与 17I 边界协同）
  - **legacy `predict.py`**（TEMP_MIGRATION_BRIDGE 内核）
- ❌ **直接修容易又变成局部 patch**：
  - 如果 final_report 还在用 `final_report_aggregator_result.v1` 旧 schema
    （`final_confidence` 顶层），PR-REVIEW-2 必须依赖**仍然存在**的
    legacy 字段；这等于"先把违规点用 legacy 字段绑死再修"
  - 如果 confidence schema adapter（PR-CONF-2）还没落地，PR-REVIEW-2
    的"caution 不 mutate confidence"很难写出可验证的 boundary tests
  - 如果 review_result contract（PR-REVIEW-1，已落地）后没有 warning_cards
    schema，caution 信息无处可去
- ❌ **风险 H**（17K §17 已显式标注）：
  - 触及 `predict.py`（TEMP_MIGRATION_BRIDGE 中的核心 active 模块）
  - 涉及 caller path 重新接线

**结论**：

- `_apply_briefing_caution` 修复必须等：
  - PR-FINAL-2（final_report passthrough / non-mutation hardening；
    18P）落地——final_report 顶层 schema 稳定
  - PR-CONF-2（confidence_evaluator schema adapter；18N）落地——
    confidence schema 稳定
  - PR-REVIEW-1（review_result contract；18G，已落地）
- 应等 final_report passthrough / confidence schema / review_result
  contract 都更稳定后再动
- 所以 PR-REVIEW-2 放在第二批**最后一位**（18R，第 8 顺位）

---

## 11. 为什么不先迁 UI

> **17M Predict tab 主面板（`ui/predict_tab.py`）当前仍读 legacy 字段；
> Bridge #1 退出条件 #1 = "UI 全部读新 final_report schema"。**

- ✅ **方向正确**——UI 必须最终迁移到 standard schema
- ❌ **但 UI 是 consumer**：
  - 如果 producer 还没稳定产出 standard payload，UI 只能写 fallback
  - fallback 越多，UI 越难维护；用户视角下"哪个值是真的"越混乱
- ❌ **Predict tab 风险 H**——PR-UI-7（17M §16 已显式标注 H）：
  - Predict tab 是 app.py 主入口；任何字段读取偏差直接影响用户面板
  - **永久不进入第二批第一阶段**
- ❌ **Inspect tab 可以作为低风险 UI 第一刀**——PR-UI-2 风险 L：
  - Inspect tab 是观察 / 调试入口，不是用户主入口
  - 17M §16 PR-UI-2 显式定位为"§9 first to migrate"
  - **但**仍应等 producer adapter（PR-FEATURE-2 / PR-PROJ-2 / PR-EXCL-2）
    落地之后做——这样 Inspect tab 能直接显示新 standard payload 的
    `schema_version` / `missing_sections` / `compatibility_mode`，不需要
    显式 fallback 逻辑

**结论**：

- UI 迁移**必须等**：
  - PR-FEATURE-2（18K）落地
  - PR-PROJ-2（18L）落地
  - PR-EXCL-2（18M）落地
  - PR-CONF-2（18N）落地
  - PR-CONF-3（18O）落地
  - PR-FINAL-2（18P）落地
- Inspect tab 是后续低风险 UI 第一刀（**18Q，第 7 顺位**）
- Predict tab 不进入第二批第一阶段；**永久**等到 PR-FINAL-2 + PR-CONF-2 +
  PR-CONF-3 + PR-UI-2 都稳定之后才能讨论

---

## 12. 为什么不先做 architecture_orchestrator

> **`architecture_orchestrator` 是 16I PR-F / 17J PR-FINAL-7 的目标——把
> Data → Feature → Projection → Exclusion → Confidence → Final Report
> 的物理调用收敛到唯一一处。**

- ❌ 它**不在九分支正式架构内**——17J PR-FINAL-7 把它定位为
  "ASSEMBLY_ORCHESTRATION_LAYER / TEMP_FUTURE_ORCHESTRATOR"
- ❌ 它**依赖各层的 standard output adapter**：
  - feature_payload producer adapter（PR-FEATURE-2，18K）
  - projection_result producer adapter（PR-PROJ-2，18L）
  - exclusion_result producer adapter（PR-EXCL-2，18M）
  - confidence_result schema adapter（PR-CONF-2，18N）
  - final_report passthrough adapter（PR-FINAL-2，18P）
- ❌ 在没有 producer adapter 落地之前，新建
  `services/architecture_orchestrator.py` 会写出"无 schema 校验 + 字段
  散落"的临时代码，正是 16F no-patching principle 要避免的反例
- ❌ 17J §13 PR-FINAL-7 已经把 architecture_orchestrator 的"真正实现 PR
  的前置条件"写明——**第二批 PR 全部落地之后才能开**

**结论**：

- `architecture_orchestrator` 必须等第二批 producer adapters
  （PR-FEATURE-2 / PR-PROJ-2 / PR-EXCL-2 / PR-CONF-2 / PR-CONF-3 /
  PR-FINAL-2）全部落地后再选择
- **不能现在直接做**
- 17D §10.3 已写明"architecture_orchestrator MVP 暂停；归入 17J"；本
  18J 接续：暂缓到第二批完成后单独评估

---

## 13. 第二批 PR 验收标准

每个第二批 PR 必须**同时**满足：

| # | 标准 | 说明 |
|---|---|---|
| 1 | 绑定单一层 | PR 描述显式声明 `Compliant with 17D §6 layer-binding rule; bound to Branch <N>; references <17X §Y>.` |
| 2 | 引用对应 plan 章节 | PR 描述显式引用 17F §13 / 17G §13 / 17H §14 / 17I §13 / 17J §13 / 17K §17 / 17M §16 中具体小节 |
| 3 | 明确是否接 active path | PR-FEATURE-2 不接 active path；PR-PROJ-2 / PR-EXCL-2 / PR-CONF-2 / PR-CONF-3 / PR-FINAL-2 / PR-UI-2 / PR-REVIEW-2 接 active path（描述中明确） |
| 4 | 不跨层 | 除非文档明确批准；`git diff --stat` 只命中本层文件 |
| 5 | 不改 UI | 除非 PR-UI-* 专门做（仅 PR-UI-2 允许） |
| 6 | 不改 `predict.py` | 除非文档明确批准（仅 PR-REVIEW-2 允许，且只改 `_apply_briefing_caution` + caller wiring） |
| 7 | 不删除 bridge | 任何 bridge `git rm` / archive 都属于独立 archive PR |
| 8 | 不跑 replay / holdout | 不生成 raw artifacts |
| 9 | 不接 trading / broker | 永久禁止 |
| 10 | 不输出 buy / sell / hold | 永久禁止 |
| 11 | 不输出 hard / forced / required | 永久禁止 |
| 12 | focused tests 通过 | 该 PR 的 focused tests 100% 通过 |
| 13 | related tests 通过 | 该 PR 影响范围内的相关 tests 全绿 |
| 14 | full pytest 通过 | 18I 入 main 之后的 baseline = **3753 passed, 10 skipped, 0 failed, 26 warnings, 1511 subtests passed**；新增测试数显式累加到 passed |
| 15 | scripts/check.sh 通过 | 统一检查脚本通过 |
| 16 | git diff 只包含目标文件 | `git diff --stat` 只命中 PR 目标文件 |
| 17 | 可 git revert | 单 commit；可独立回滚 |

---

## 14. 第二批分组建议

**建议不要一次做多个**——避免一个大 commit 把多层修改混在一起。

| Batch | PR | 所属层 | 估计风险 | 估计工作量 |
|---|---|---|---|---|
| **Batch 18K** | PR-FEATURE-2 | Branch 2 Feature | L | 1 PR，~200 lines code + ~250 lines tests |
| **Batch 18L** | PR-PROJ-2 | Branch 3 Projection | L | 1 PR，~50 lines code（仅加 alias 字段）+ ~150 lines tests |
| **Batch 18M** | PR-EXCL-2 | Branch 4 Exclusion | L | 1 PR，~80 lines code（加 standard alias）+ ~200 lines tests |
| **Batch 18N** | PR-CONF-2 | Branch 5 Confidence | M | 1 PR，~80 lines code（仅 `_compute_agreement` + 私有 helper）+ ~250 lines tests |
| **Batch 18O** | PR-CONF-3 | Branch 5 Confidence | L | 1 PR，~10 lines code（3 caller kwargs）+ ~80 lines tests |
| **Batch 18P** | PR-FINAL-2 | Branch 6 Final Report | L | 1 PR，~30 lines code（删 dead helper + boundary tests）+ ~150 lines tests |
| **Batch 18Q** | PR-UI-2 | Branch 9 UI | L | 1 PR，~80 lines code（inspect_tab section）+ ~150 lines tests |
| **Batch 18R** | PR-REVIEW-2 | Branch 7 Review | **H** | 1 PR，~30 lines code（_apply_briefing_caution + caller wiring）+ ~200 lines tests |

**说明**：

- **每个 batch 独立 PR / commit / regression**——单 commit 单 batch
- **不合并多个层的实现到一个 commit**
- **每个 batch 必须**：用户单独确认 → builder → reviewer → tester → 入 main
- **顺序硬约束**：上游 producer 先（PR-FEATURE-2 → PR-PROJ-2 → PR-EXCL-2 →
  PR-CONF-2 → PR-CONF-3 → PR-FINAL-2 → PR-UI-2 → PR-REVIEW-2）；如果某个
  batch 卡壳（例如 PR-CONF-2 的 fallback 设计需要更长讨论），可以跳过到
  下一个**同层**或**与上游已落 PR 兼容**的 batch
- **回滚策略**：每个 batch 失败时 `git revert <sha>` 即可；不需要连锁
  回滚上游 batch（contract validator 已经稳定）

---

## 15. 本轮不允许事项

**18J 起，本轮（直到用户确认 18K 启动之前）严格禁止**：

- ❌ 不改代码（无 `.py` 文件被修改；本轮 0 修改）
- ❌ 不新增测试（`tests/` 字节不变）
- ❌ 不跑 pytest（除 readonly 校验外不执行 test 命令）
- ❌ 不跑 replay
- ❌ 不跑 holdout
- ❌ 不做 PR-FEATURE-2 实现（PR-FEATURE-2 留待 18K）
- ❌ 不做 confidence key（PR-CONF-2 / PR-CONF-3 留待 18N / 18O）
- ❌ 不修 `_apply_briefing_caution`（PR-REVIEW-2 留待 18R）
- ❌ 不迁 UI（PR-UI-2 留待 18Q；PR-UI-3 ~ PR-UI-9 留待第三批以后）
- ❌ 不实现 `architecture_orchestrator`（留待第二批全部落地后单独评估）
- ❌ 不进入 3R-5 / 3R-6（1.0 §12 / 17D §11 / 17E ~ 17M / 18A §14 持续锁定；
  本轮再次重申）
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
- ❌ 不借 18J 顺手做代码改动（本轮全部 markdown 改动）

> 与 17D §11 / 17E ~ 17M §禁止事项 / 18A §14 一致；本轮再次锁定。

---

## 16. 推荐下一步

**推荐**：

> **Step 18K / PR-FEATURE-2：feature_payload producer / adapter skeleton**

**前置条件**：

- 18J 入 main
- 用户单独确认 18K 启动

**18J 入 main 后启动顺序建议**（每个 batch 单独确认）：

1. **Step 18K**：PR-FEATURE-2 — feature_payload producer / adapter skeleton
2. **Step 18L**：PR-PROJ-2 — main_projection standard projection_result adapter
3. **Step 18M**：PR-EXCL-2 — exclusion_layer standard exclusion_result adapter
4. **Step 18N**：PR-CONF-2 — confidence_evaluator schema adapter
5. **Step 18O**：PR-CONF-3 — explicit `calibration_context = {"ready": False}`
6. **Step 18P**：PR-FINAL-2 — final_report passthrough / non-mutation hardening
7. **Step 18Q**：PR-UI-2 — Inspect tab standard payload display
8. **Step 18R**：PR-REVIEW-2 — `_apply_briefing_caution` warning-only

**18J 本轮只做 selection doc**——不启动 18K。

**不推荐**：

- 不推荐跳到 PR-CONF-2 / PR-CONF-3（必须等 PR-FEATURE-2 / PR-PROJ-2 /
  PR-EXCL-2）
- 不推荐跳到 PR-REVIEW-2（必须等 PR-FINAL-2 + PR-CONF-2 + PR-CONF-3）
- 不推荐跳到 PR-UI-2 之外的任何 UI PR（PR-UI-3 ~ PR-UI-9 留待第三批）
- 不推荐立刻做 `architecture_orchestrator`（必须等第二批全部落地）
- 不推荐解锁 3R-5 / 3R-6（1.0 §12 7 项前提仍未全部满足）
- 不推荐借 18J 顺手做任何代码改动（与 17D §11 / 18A §14 一致）
- 不推荐重启 16I PR-F / PR-G / PR-H（实质内容已被 17I / 17J / 17K /
  17L / 17M / 18A / 18J 拆开 + 排序）

> **明确**：本轮 18J 推荐的下一步**只有一个候选**——Step 18K / PR-FEATURE-2。
> 启动需要用户单独确认。

---

## 17. 严守边界

本轮 Step 18J **只**写 Second Layer-Based Implementation Batch Selection：

- ❌ 未改代码（无 `.py` 文件被修改；`git diff --stat` 仅 markdown）
- ❌ 未新增测试（`tests/` 字节不变）
- ❌ 未删除文件
- ❌ 未移动文件
- ❌ 未修改 `.gitignore`
- ❌ 未处理 `avgo_agent.db`（16H §5 校正后无需处理）
- ❌ 未处理 handoff（worktree clean except deliberate keep；无新增 deliberate untracked）
- ❌ 未处理 logs / DB backup / `.claude/worktrees/`
- ❌ 未跑 replay / validation / historical evaluation
- ❌ 未写 DB / 未改 DB schema
- ❌ 未默认迁移 `run_predict` 到 V2
- ❌ 未接 trading
- ❌ 未输出 buy / sell / hold / hard / forced / required
- ❌ 未启用任何 candidate / 未复活 `continuous_smoothing`
- ❌ 未触碰 RISK-1 / RISK-2 / RISK-3 / RISK-7 / RISK-8 / RISK-9 / RISK-10
- ❌ 未进入 3R-5 / 3R-6
- ❌ 未启动任何代码 PR（PR-FEATURE-2 候选要等 18K）
- ❌ 未直接做 confidence key patch（PR-CONF-2 / PR-CONF-3 留待 18N / 18O）
- ❌ 未直接修 `_apply_briefing_caution`（PR-REVIEW-2 留待 18R）
- ❌ 未直接迁 UI（PR-UI-2 留待 18Q；其它 UI PR 留待第三批以后）
- ❌ 未直接实现 `architecture_orchestrator`（留待第二批全部落地后）
- ❌ 未做任何局部 patch
- ❌ 未 commit / 未 push（按本轮指令）

唯一新增文件：[tasks/record_18j_second_layer_based_implementation_batch_selection.md](tasks/record_18j_second_layer_based_implementation_batch_selection.md)（本文件）。

后续修改路径：任何对 §3 当前架构状态 / §4 候选方向总览 / §5 选择原则 /
§6 推荐路线 / §7 第一刀推荐 / §8 18K 草案 / §9 PR-CONF-2 / PR-CONF-3 处理 /
§10 PR-REVIEW-2 处理 / §11 UI 处理 / §12 architecture_orchestrator 处理 /
§13 验收标准 / §14 分组方式 / §15 禁止事项 / §16 下一步 的调整，都必须
**显式更新本文件**；同时检查是否需要同步更新 1.0 / 17D / 17E ~ 17M /
18A。
