# 17D记录：Layer-by-Layer Rebuild Governance

> 本记录是 **Step 17D：按层重建治理原则**。1.0 canonical / 16A blueprint /
> 16B inventory / 16C target dataflow & contract decision / 16D isolation
> & quarantine plan / 16E core chain refactor plan / 16F no-patching
> principle / 16G full module decomposition standup / 16H repository
> clearing decision table / 16I core chain rebuild execution plan / 17A
> PR-B standard payload skeleton / 17B PR-C peer_alignment 抽公共模块 /
> 17C PR-D main_projection 去 `exclusion_result` 形参 已全部入 main
> （main 最新 commit `b83d5c5`）。
>
> 本轮**锁定**一个新治理原则：**当前阶段是按层重建，不是继续按线性 PR
> 顺序推进**。后续所有代码 PR 必须**绑定九分支中的某一层**，且必须
> 等该层完整重建计划完成后才能启动。
>
> 本轮**只**写治理记录文档：未改业务代码、未新增测试、未删除文件、
> 未移动文件、未修改 `.gitignore`、未处理 handoff、未处理 logs /
> DB backup / `.claude/worktrees/`、**未处理 `avgo_agent.db`**、
> 未跑 replay / validation / historical evaluation、未写 DB / 未改
> DB schema、未默认迁移 `run_predict` 到 V2、未接 trading、未输出
> buy / sell / hold / hard / forced / required、未进入 3R-5 / 3R-6、
> 未启动 confidence key 对齐 PR、未启动 UI 迁移、未启动 bridge 清理、
> 未启动任何局部 patch、未 commit / 未 push。
>
> 唯一 deliverable：本文件。
>
> **本记录优先级**：与 1.0 / 16F 同级。冲突仲裁路径与 1.0 §14 / 16F §13
> 一致：旧 records（含 16I PR-E ~ PR-H 顺序）若与 17D 冲突，**以 17D
> 为准**。

---

## 1. Step 17D 目的

锁定一个新治理原则：

> **当前阶段是 Layer-by-Layer Rebuild，不是继续按线性 PR 顺序推进。**

具体含义：

- 16I 的 PR-B / PR-C / PR-D 已分别由 17A / 17B / 17C 落地进入 main，方向
  正确，已经验证 16I 的"地基 → peer 抽出 → projection 去形参"前三步是
  逻辑闭合的最小单元
- 但 16I 的 PR-E（confidence key 对齐）/ PR-F（architecture_orchestrator）/
  PR-G（bridge marker）/ PR-H（UI / evaluation 迁移计划）**不能**作为"自动
  执行清单"按顺序连开
- 16I 的 PR 列表只是**参考**，不是**强制路线**；任何"按 16I 顺序立即开
  PR-E"的提议**默认 reject**
- 后续所有代码 PR 必须**绑定九分支中的某一层**（1.0 §8 / 16A §5–§13）；
  必须**先**有该层完整 Rebuild Plan，**再**进入该层第一个代码 PR
- 本阶段不再回答"下一行代码改哪里"；只回答"下一层架构是什么样的"

**本文件性质**：治理原则（governance），不是 design 也不是 impl plan。
设计与执行计划由 17E ~ 17M 各层 Rebuild Plan 给出，第一批代码 PR 从 18A 起。

---

## 2. 用户确认的硬原则

用户已经明确确认（本轮再次重申）：

1. **这是重新架构，不是局部修补**
   - 与 1.0 §3 / 16A §2 / 16F §2 一致；本轮再次锁定
2. **要先把系统打开、打碎、模块化**
   - 16G 已完成（109 services + 17 ui + ... 全仓库 inventory）
3. **要让模块按九分支站队**
   - 16B / 16G 已完成；任何漏标 / UNKNOWN 在 17E ~ 17M 各层计划内继续收紧
4. **要先归类、再清场、再按层补**
   - 16G（归类）→ 16H（清场决策表）→ 17D（治理原则）→ 17E ~ 17M（按层
     Rebuild Plan）→ 18A 起按层实现 PR
5. **不能再动不动走偏**
   - 不允许"看一个问题修一个问题"的执行偏差；任何偏离九分支边界的提案
     **默认 reject**
6. **不能看到 confidence key / UI 字段 / bridge / import / 参数问题就直接修**
   - 这些都属"局部 patch"；归入对应层 Rebuild Plan 后再决定执行节奏

> 这条确认覆盖之前任何"按 16I 顺序连开 PR-E / PR-F / PR-G / PR-H"的隐含
> 路径。17D 起，第一个新代码 PR 之前必须先完成**对应层**的 Rebuild Plan。

---

## 3. 正确路线

后续路线**固定**为：

1. **先架构**（1.0 / 16A / 16C 已就位）
2. **再模块**（16B / 16G 已就位）
3. **再归类**（16G 已落 inventory；16H 决策表已就位）
4. **再清场**（16H DELETE_NOW 集合为空；MOVE_OUTSIDE_REPO / ARCHIVE_IN_REPO /
   QUARANTINE / DELETE_LATER / MIGRATE_CALLER_FIRST 由各层 Rebuild Plan 引用）
5. **再按层补**（17E ~ 17M 写每层 Rebuild Plan；18A 起按层补代码）

**路线基础**（不能跳过 / 不能反向）：

| 基础 | 性质 | 状态 |
|---|---|---|
| 1.0 canonical principles | 最高准则 | ✅ commit `5c209bb` |
| 16A architecture reset blueprint | 架构详图 | ✅ commit `9b98ad5` |
| 16B module standup ownership inventory | 第一版 inventory | ✅ commit `bdd1314` |
| 16C target dataflow & contract decision | 数据流 + schema | ✅ commit `b05d7c8` |
| 16D isolation / quarantine plan | 隔离 / 边界 | ✅ commit `694450e` |
| 16F no-patching principle | 禁止小修小补 | ✅ commit `6cfaa9b` |
| 16G full module decomposition standup | 全仓库站队 | ✅ commit `ba6bc7d` |
| 16H repository clearing decision table | 清场决策表 | ✅ commit `cc4e9ca` |

**16I 的位置**：

> 16I 是核心链路重建第一批 PR 的**参考列表**，**不是**自动执行清单。
> 17A / 17B / 17C 已分别落地 PR-B / PR-C / PR-D；这三步证明 16I 前三项
> 方向正确。但 16I PR-E / PR-F / PR-G / PR-H **不能**直接连开；必须由 17E ~
> 17M 对应层 Rebuild Plan **重新批准**，且必须经过 18A 重新排序。

---

## 4. 为什么不能继续小修小补

继续小修小补会导致以下结构性恶化（与 1.0 §3 / 16A §2 / 16F §3 一致；
本轮根据 17A ~ 17C 实战观察补充）：

1. **旧链 / 新链 / Bridge 链继续并行**
   - `predict.run_predict` 旧链、`projection_orchestrator_v2` V2 链、
     `home_terminal_orchestrator` 主页链仍然三条并存
   - 任何 patch 只动其中一条，会让另外两条更难拉齐
2. **看到一个问题就修一个问题，系统越来越碎**
   - 例如 confidence `agreement_status = unknown`、UI 仍读 `final_bias`、
     bridge 模块没标记、orchestrator 之间字段不齐
   - 这些都是表象；根因是九分支没有按层补完，patch 单点反而掩盖根因
3. **confidence / UI / orchestrator / bridge 各自 patch，最后又互相不兼容**
   - confidence patch 会引用某 schema 局部 key；UI patch 会引用另一组
     legacy 字段；orchestrator patch 会引用第三套；最后三方收敛不回
4. **模块没有先站队，容易把旧逻辑继续保护起来**
   - 例如直接 patch `predict._apply_briefing_caution` 会让该函数继续
     扩散；按层重建则在 Review Layer Plan 里直接决定它的归属
5. **清场没完成前就补代码，会让 repo 继续混乱**
   - 16H DELETE_LATER / MIGRATE_CALLER_FIRST 集合还没经过对应层 plan
     批准；提前补代码会绕过 16H 决策路径

**结论**：

> 当前阶段是 Architecture Reset。每一次"局部 patch 修一行"都让整体几何
> 复杂度上升，而不是下降。正确路径是：先把每层架构 plan 写出来，再按
> 层补。

---

## 5. 已完成但不代表继续线性 patch

**已落地的事实**（不回滚 / 不撤销）：

| Step | PR | commit | 状态 |
|---|---|---|---|
| 17A | PR-B：`standard_projection_payload.v1` contract skeleton | `9c779f8` | ✅ in main |
| 17B | PR-C：`peer_alignment` 抽公共模块（`services/peer_alignment.py`） | `08b45c1` | ✅ in main |
| 17C | PR-D：`main_projection` 去 `exclusion_result` 形参 | `b83d5c5` | ✅ in main |

**这三个 PR 保留**：

- 17A 是 1.0 §8 / 16C §5 决定的"新架构地基"；保留
- 17B 是 1.0 §8 (Branch 2) / 16C §3.3 决定的"peer_alignment 归 Feature
  Layer"；保留
- 17C 是 1.0 §8 (Branch 3) / 07A §3.2 / 11A boundary contract 决定的
  "projection 不读 exclusion"；保留

**但这不代表**继续自动执行：

- ❌ **PR-E confidence key 对齐**——暂停；归入 17I Confidence Layer Rebuild Plan
- ❌ **PR-F architecture_orchestrator MVP**——暂停；归入 17J Final Report
  Layer / orchestration 决策（实际由对应层与 18A 起的实现 PR 共同决定）
- ❌ **PR-G bridge deprecation marker**——暂停；归入对应 bridge / 各层
  Rebuild Plan 中的 bridge 处置部分
- ❌ **PR-H UI / evaluation migration plan**——暂停；归入 17M UI Layer
  Rebuild Plan + 17L Evaluation Layer Rebuild Plan

**核心判断**：

> 这些动作必须**重新纳入按层重建计划**后才能执行；不能因为 16I 已经写过
> 就视为已批准。16I 的 PR-E ~ PR-H 当前性质是**参考资料**，不是**执行
> 指令**。

---

## 6. 后续所有 PR 的准入规则

**18A 起，每个代码 PR 在打开之前必须先回答以下 8 个问题**（默认 reject
路径——任一题答不上则**禁止开 PR**）：

| # | 问题 | 期望答案形式 |
|---|---|---|
| 1 | 它属于九分支中的哪一层？ | 明确指出是 Branch 1 ~ 9 中的**某一个**（不允许"跨多个"） |
| 2 | 它执行的是该层 Rebuild Plan 中的哪一项？ | 引用 17E ~ 17M 对应文档的**具体章节** |
| 3 | 它是否跨层？ | 期望 NO；如有跨层 import，必须在描述里显式声明并引用 1.0 §9 数据流方向 |
| 4 | 它有没有顺手修别的层？ | 期望 NO；`git diff --stat` 只能命中本层文件 |
| 5 | 它有没有修改未授权模块？ | 期望 NO；该层 Plan 必须把"允许改 / 不允许碰"显式列出 |
| 6 | 它是否会扩大 bridge 依赖？ | 期望 NO；任何"新增 bridge import"必须经过对应 bridge / 各层 Plan 显式批准 |
| 7 | 它是否会引入 trading / hard / forced / buy / sell / hold？ | **永久 NO**（1.0 §6 / §12） |
| 8 | 它是否有 focused tests + full pytest + rollback plan？ | YES；focused boundary + full pytest + 单 commit 单 revert |

**如果 8 个问题中任一题答不上，不能开 PR**。

**审查路径**：

- 该层 Rebuild Plan 是 PR 描述里的**强制 cross-reference**
- reviewer 必须**先核对**九分支归属，再核对 PR 内容
- 本轮 17D 起，PR 描述模板必须包含一行：
  `Compliant with 17D §6 layer-binding rule; bound to Branch <N>; references <17X §Y>.`

---

## 7. 九层计划必须先完成

**18A 起的代码 PR 必须以对应层 Rebuild Plan 为前置**。每一层必须先写
计划，再写代码。九层 Rebuild Plan 列表：

| 层 | Plan 文档 | 性质 |
|---|---|---|
| Branch 1 Data Layer | 17E Data Layer Rebuild Plan | 文档 |
| Branch 2 Feature Layer | 17F Feature Layer Rebuild Plan | 文档 |
| Branch 3 Projection Layer | 17G Projection Layer Rebuild Plan | 文档 |
| Branch 4 Exclusion Layer | 17H Exclusion Layer Rebuild Plan | 文档 |
| Branch 5 Confidence Layer | 17I Confidence Layer Rebuild Plan | 文档 |
| Branch 6 Final Report Layer | 17J Final Report Layer Rebuild Plan | 文档 |
| Branch 7 Review & Learning Layer | 17K Review & Learning Layer Rebuild Plan | 文档 |
| Branch 8 Evaluation Layer | 17L Evaluation Layer Rebuild Plan | 文档 |
| Branch 9 UI / Presentation Layer | 17M UI / Presentation Layer Rebuild Plan | 文档 |

### 7.1 每层 Plan 必须包含的最小章节

每个 17E ~ 17M 文档必须含以下 10 项：

1. **当前模块** — 该层当前 active 模块清单（从 16G inventory 抽出）
2. **目标模块** — 该层 1.0 / 16C / 16D 决定的最终模块清单
3. **保留模块** — `KEEP_ACTIVE`（无需改动）
4. **迁移模块** — 当前在别处但需要迁入该层（或反过来）
5. **隔离模块** — `QUARANTINE` / `LEGACY_ACTIVE_DEPENDENCY` /
   `TEMP_MIGRATION_BRIDGE`（仅加 marker，不删）
6. **删除候选** — `DELETE_LATER`（必须先 archive + caller 迁移）
7. **需要补的能力** — 该层在目标架构下缺失的能力（候选 PR 列表）
8. **不允许碰的边界** — 哪些上下游字段 / schema / 模块禁止动
9. **测试要求** — focused boundary 文件 + full pytest baseline + 新增测试
10. **回滚方式** — 每个候选 PR 的单 commit / 单 revert / regression 数字

### 7.2 顺序硬约束

- 每层 Plan **单独**写、**单独**入 main、**单独** review
- **不**允许在一份文档里覆盖多个层
- 17E ~ 17M 之间**没有强制顺序**（除非 Plan 中显式声明依赖；例如 17F
  Feature Layer 的某项可能依赖 17E Data Layer 完成）
- 18A 起的代码 PR 必须等**对应**层 Plan 入 main；并不要求所有 9 层 Plan
  全部入 main

---

## 8. 新执行顺序

**17D 起**，后续路线**重排**为：

| Step | 内容 | 性质 |
|---|---|---|
| **17D**（本轮） | Layer-by-Layer Rebuild Governance | 文档（治理原则） |
| 17E | Data Layer Rebuild Plan | 文档 |
| 17F | Feature Layer Rebuild Plan | 文档 |
| 17G | Projection Layer Rebuild Plan | 文档 |
| 17H | Exclusion Layer Rebuild Plan | 文档 |
| 17I | Confidence Layer Rebuild Plan | 文档 |
| 17J | Final Report Layer Rebuild Plan | 文档 |
| 17K | Review & Learning Layer Rebuild Plan | 文档 |
| 17L | Evaluation Layer Rebuild Plan | 文档 |
| 17M | UI / Presentation Layer Rebuild Plan | 文档 |
| **18A** | 按层开始**第一批**实现 PR | 代码（按对应层 Plan 启动） |

**明确**：

> 任何代码实现必须等**对应层** Plan 入 main 后才能启动。
> 17E ~ 17M 没全写完不要紧；只要某层 Plan 入 main，就允许在 18A 起开
> 该层第一个 PR。但 PR 必须显式 cross-reference 该层 Plan。

---

## 9. 对 PR-E 的处理

**PR-E confidence key 对齐**（16I §9）：

- ❌ **不取消**——方向正确（07C / 16C §6 决定 standard schema 优先）
- ⏸️ **暂停**——归入 17I Confidence Layer Rebuild Plan
- 🔄 **重新批准条件**——17I 入 main 后，由 17I 决定 PR-E：
  - 是否执行
  - 何时执行
  - 怎么执行（schema 优先策略 / interim 兼容映射 / calibration_context
    显式 fallback 是否仍按 16I §9.2 三项）
  - 是否拆分为多个 PR
- 📌 **当前禁止动作**：
  - 不直接打开 PR-E 改 `services/confidence_evaluator.py`
  - 不直接补 `home_terminal_orchestrator` / `projection_orchestrator_v2`
    的 `calibration_context` 参数
  - 不顺手修 `agreement_status` 计算逻辑
  - 不直接补 `_FORBIDDEN_FIELDS`

> 17I Confidence Layer Rebuild Plan 写完之前，confidence 相关任何代码
> 改动**全部默认 reject**。

---

## 10. 对 bridge / UI / orchestrator 的处理

### 10.1 Bridge 清理（含 13 个 LEGACY_ACTIVE_DEPENDENCY / TEMP_MIGRATION_BRIDGE 模块）

- ⏸️ **暂停**
- 📌 归入对应 bridge / orchestration / 各层 Plan：
  - `predict.py` / `predict_legacy_adapter` / `predict_legacy_v2_bridge`
    → 17J Final Report Layer Plan + 17G Projection Layer Plan + 17I
    Confidence Layer Plan 共同决定（涉及多层 caller 迁移）
  - `projection_orchestrator` / `projection_orchestrator_v2` /
    `home_terminal_orchestrator` / `projection_entrypoint` /
    `projection_v2_adapter` → 17J Final Report Layer Plan（orchestration
    归 Final Report 之前的 aggregation 入口）
  - `consistency_layer` / `peer_adjustment` / `primary_20day_analysis` /
    `historical_probability` → 17F / 17G 共同决定（Feature ↔ Projection
    边界）
  - `predict_summary` → 17J Final Report Layer Plan
- 📌 **当前禁止动作**：不打开 PR-G bridge marker docstring；不直接改
  bridge 模块顶部 docstring；不删除任一 bridge 模块

### 10.2 UI 迁移

- ⏸️ **暂停**
- 📌 归入 17M UI Layer Rebuild Plan
- 📌 **当前禁止动作**：
  - 不改 `ui/predict_tab.py` 主面板字段读取（仍从 `final_bias` /
    `final_confidence` 读，不动）
  - 不改 `ui/home_terminal_tab.py` / `ui/history_tab.py` /
    `ui/inspect_tab.py` / `ui/review_tab.py`
  - 不直接迁移 evaluation dashboard
  - 不打开 PR-H UI / evaluation migration plan 的子 PR
- 📌 **17M 必须解答**：
  - 字段映射表（`final_bias` → `final_report.projection_section.most_likely_state` 等）
  - tab 迁移顺序（低风险 tab 先 → 主入口 last）
  - Bridge #1 退出条件（UI 全部读新 final_report schema）

### 10.3 architecture_orchestrator MVP

- ⏸️ **暂停**
- 📌 归入 17J Final Report Layer Rebuild Plan（orchestration 是 Final Report
  之前的 aggregation 入口；Final Report 自身不重新预测）
- 📌 **当前禁止动作**：
  - 不新建 `services/architecture_orchestrator.py`
  - 不调用 `validate_standard_projection_payload` 作为生产路径自检
  - 不切换默认 `run_predict` 路径
- 📌 **17J 必须解答**：
  - architecture_orchestrator MVP 是否仍是合并入口（vs. 直接由 Final
    Report Layer 模块 aggregation）
  - 与现有 `services/projection_orchestrator_v2` 的合并 / 替换关系
  - `feature_payload` → `projection_result` + `exclusion_result` →
    `confidence_result` → `final_report` 的物理调用路径

### 10.4 不允许临时跳去做这些任务

> 即使遇到 confidence unknown / UI 字段不齐 / bridge marker 缺失等"看起来
> 立刻能修的问题"，也**必须先写对应层 Rebuild Plan**；不允许"先 patch
> 一下再写 plan"。

---

## 11. 不允许事项

**17D 起，本阶段（直到 18A 之前）严格禁止**：

- ❌ 不直接做 confidence key patch（归 17I）
- ❌ 不直接迁 UI（归 17M）
- ❌ 不直接清 bridge（归对应层 Plan）
- ❌ 不直接改 orchestrator（归 17J）
- ❌ 不直接删 legacy module（必须先经过对应层 Plan + 16H 决策表）
- ❌ 不直接跑 evaluation（归 17L）
- ❌ 不进入 3R-5 / 3R-6（1.0 §12 / 16A §18 / 16C §13 / 16F §9 / 16G §16 /
  16H §15 / 16I §15 锁定；本轮再次重申）
- ❌ 不因为看到局部问题就开 PR
- ❌ 不复活已 quarantine 的 v1 stubs / `continuous_smoothing*` /
  promotion 三模块
- ❌ 不修改 `.gitignore`（与 14L A2 / 14M / 15 §2 / 16I §15 一致）
- ❌ 不处理 `avgo_agent.db`（16H §5 校正后无需处理）
- ❌ 不处理 handoff（`.claude/handoffs/task_089_post_pr_cleanup.md` 字节
  不变；与 14L A2 / 14M / 15 §2 一致）
- ❌ 不处理 logs / DB backup / `.claude/worktrees/`
- ❌ 不写 DB / 不改 DB schema
- ❌ 不接 trading / 不输出 buy / sell / hold / hard / forced / required
- ❌ 不默认迁移 `run_predict` 到 V2（hard rule 1）
- ❌ 不污染 2026-01-01 之后 final holdout
- ❌ 不借 17D / 17E ~ 17M 任一步顺手做代码改动（17D ~ 17M 全部是文档轮）

> **本阶段唯一允许的代码动作**：紧急 hotfix（线上崩溃 / 数据丢失等不可
> 接受的故障）。这种 hotfix **必须**单独 launch review，并在 commit
> message 里显式说明 `emergency hotfix; not part of layer-by-layer rebuild`
> （与 16F §4 一致）。

---

## 12. 推荐下一步

> **首选**：**Step 17E：Data Layer Rebuild Plan**

理由：

- 数据流方向是 Data → Feature → {Projection, Exclusion, Confidence} →
  Final Report → {Review, Evaluation} → UI（1.0 §9 / 16C §3）
- 从最上游开始写 Plan，可以让下游层 Plan 直接 reference 上游契约
- Data Layer 当前模块相对清晰：`data_fetcher.py` / scanner / matcher /
  encoder / `feature_builder.py` 数据读取部分（注：scanner / matcher /
  encoder 的特征推导部分归 Feature Layer，结构判断部分归 Projection Layer，
  与 1.0 §13 hard rule 2 一致）
- Data Layer 的"目标模块 / 保留模块 / 迁移模块"在 16G inventory 中已经
  落了大半，17E 的工作量是把 16G 抽出来 + 写"需要补的能力 + 不允许碰
  的边界 + 测试要求 + 回滚方式"

**不推荐**：

- 不推荐跳到 17I Confidence Layer Plan（用户视角下"agreement_status 长期
  unknown"很显眼，但从架构方向看必须从 Data 层开始）
- 不推荐跳到 17M UI Layer Plan（UI 是末端展示；Plan 顺序最好接近数据流方向）
- 不推荐借 17D / 17E 顺手做任何代码改动
- 不推荐借 17D / 17E 解锁 3R-5 / 3R-6（1.0 §12 7 项前提仍未全部满足）
- 不推荐重启 16I PR-E（必须等 17I）
- 不推荐重启 16I PR-F（必须等 17J）
- 不推荐重启 16I PR-G（必须等对应层 bridge 处置部分）
- 不推荐重启 16I PR-H（必须等 17M / 17L）

**次选**（也可作为并行 prep）：

> **Step 17J / Step 17M**——如果用户认为 Final Report Layer / UI Layer 的
> 模块归属比 Data Layer 更紧迫（例如希望先固化 final report schema 再补
> 上游），也可以把 17E 与其他层并行。但**默认仍推荐**从 Data Layer 起，
> 沿数据流方向写下去。

> **明确**：本轮 17D 推荐的下一步**只有一个候选**——17E Data Layer
> Rebuild Plan。

---

## 13. 严守边界

本轮 Step 17D **只**写 governance record：

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
- ❌ 未启动 confidence key 对齐 / 未启动 UI 迁移 / 未启动 bridge 清理 /
  未启动 architecture_orchestrator / 未做任何局部 patch
- ❌ 未 commit / 未 push（按本轮指令）

唯一新增文件：[tasks/record_17d_layer_by_layer_rebuild_governance.md](tasks/record_17d_layer_by_layer_rebuild_governance.md)（本文件）。

后续修改路径：任何对 §3 路线基础 / §6 PR 准入规则 / §7 九层 Plan 章节
要求 / §8 新执行顺序 / §9 PR-E 处理 / §10 bridge / UI / orchestrator
处理 / §11 禁止事项 / §12 下一步 的调整，都必须**显式更新本文件**；同时
检查是否需要同步更新 1.0 / 16A / 16C / 16D / 16F / 16I。
