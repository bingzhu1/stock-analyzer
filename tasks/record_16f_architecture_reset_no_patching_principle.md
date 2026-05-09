# 16F记录：Architecture Reset No-Patching Principle

> 本记录是 **Step 16F：架构重置阶段的"禁止小修小补"原则**。
> 1.0 canonical / 16A blueprint / 16B inventory / 16C target dataflow &
> contract decision / 16D isolation & quarantine plan / 16E core chain
> refactor plan 已全部入 main（main 最新 commit `932d243`）。
>
> 本记录**锁定**一个新原则：**当前阶段是 Architecture Reset，不是
> 小修小补**。后续不能继续按"发现一个问题就 patch 一个问题"的方式
> 推进。
>
> 本轮**只**写原则记录文档：未改业务代码、未新增测试、未删除文件、
> 未移动文件、未修改 `.gitignore`、未处理 handoff、未处理 logs /
> DB backup / `.claude/worktrees/`、未跑 replay / validation /
> historical evaluation、未写 DB / 未改 DB schema、未默认迁移
> `run_predict` 到 V2、未接 trading、未输出 buy / sell / hold /
> hard / forced / required、未进入 3R-5 / 3R-6、未 commit / 未 push。
>
> 唯一 deliverable：本文件。
>
> **本记录优先级**：与 1.0 同级。冲突仲裁路径与 1.0 §14 一致：旧
> records（含 16E PR 顺序）若与 16F 冲突，**以 16F 为准**。

---

## 1. Step 16F 目的

锁定一个新原则：

> **当前阶段是 Architecture Reset，不是小修小补。**

具体含义：

- 后续**不能**继续按"发现一个 import 反向就立刻抽公共模块 / 发现一个
  字段不齐就立刻补字段 / 发现一个旧模块就立刻删"的方式推进
- 必须**先**完成全仓库模块拆解 + 全模块站队 + 清场决策表 + 核心链重建
  执行计划，**再**进入第一个真正的代码 PR
- 之前 16E 列出的 PR-1 / PR-2 / PR-3 / PR-4 方向**仍然正确**，但**不能**
  作为"下一步立即执行"的任务；它们应该被重新定位为 17A 之后的核心
  重建 PR 候选

---

## 2. 用户确认的新原则

用户已经明确确认：

1. 这一次是**重新架构**（Architecture Reset）
2. 要把整个系统**打碎**（full decomposition）
3. 要让**所有模块站队**（complete stand-up pass，比 16B 更彻底）
4. 这**不是**小修小补
5. **不能**再做小修小补的事

> 这条确认覆盖之前任何"按 16E PR 顺序立即开始第一个代码 PR"的隐含路径。
> 16F 起，第一个代码 PR 之前必须先完成 §6 的新执行顺序中 16G / 16H / 16I
> 三步。

---

## 3. 为什么不能继续小修小补

历史经验（与 1.0 §3 / 16A §2 一致）：

- 旧链 / 新链 / V2 链长期并行
- `predict.py` 继续像核心大脑（即便已封 mutation 表面）
- UI 继续读旧字段（`final_bias` / `final_confidence`）
- confidence key 长期不一致（`agreement_status` 长期 unknown）
- replay / evaluation / final_report schema 各走各的（3 套 payload）
- 旧模块残留造成认知污染（FROZEN_DIAGNOSTIC / LEGACY_ACTIVE_DEPENDENCY /
  UNKNOWN_REVIEW_REQUIRED 没有清理路径）
- 每一次"局部 patch 修一行"都让整体几何复杂度上升

**继续 patch 的结果**：系统**越修越乱**，而不是越修越清晰。

**正确的方向**：先打碎、再站队、再决定哪些重建、再执行 PR。这是 1.0 /
16A 的本意；16F 只是把"之前理论上同意但实践上仍按 PR 顺序推进"这个
执行偏差**显式拉回**。

---

## 4. 当前阶段禁止事项

**16F 起，本阶段（直到 17A 之前）严格禁止**：

| 禁止行为 | 原因 |
|---|---|
| 发现一个 import 问题就马上修 | 局部 patch；属小修小补 |
| 发现一个字段不齐就马上补 | 同上 |
| 发现一个旧模块就马上删 | 必须先经过 §6 新顺序的 16H 清场决策表 |
| 发现 UI 读旧字段就马上改 UI | Bridge 退出条件 #1 必须按 16C / 16D 顺序，不能借 patch 偷跑 |
| 发现 confidence unknown 就马上补逻辑 | 必须等 16G / 16I 之后再做 |
| 直接开 peer_alignment PR | §5 已重新定位 |
| 直接开 confidence key 对齐 PR | 16E PR-3 候选；同样推迟到 17A 之后 |
| 直接迁移 UI | Bridge #1 之前禁止 |
| 直接删除 legacy module | 必须经过 16H 清场决策表 + 用户单独确认 |
| 借 16F / 16G / 16H / 16I 任一步顺手做代码改动 | 16F–16I 全部是文档轮 |

> **本阶段唯一允许的代码动作**：紧急 hotfix（线上崩溃 / 数据丢失等
> 不可接受的故障）。这种 hotfix **必须**单独 launch review，并在 commit
> message 里显式说明"emergency hotfix; not part of architecture reset"。
> 截至本记录撰写时，**没有**这样的紧急情况。

---

## 5. peer_alignment PR 的重新定位

**事实状态**（16F 撰写时 worktree 实际情况）：

> 上一轮（紧接着 16E commit 之后）执行了 PR-1 实施动作：
> - 新增 `services/peer_alignment.py`（feature-only 共享 helper）
> - 修改 `services/exclusion_layer.py`（删本地 def，加 import）
> - 修改 `services/main_projection_layer.py`（改 import 来源）
> - 新增 `tests/test_peer_alignment_boundary.py`（18 个 boundary tests）
>
> 4 个文件的修改全部留在**当前 worktree 的 uncommitted 状态**（未 stage、
> 未 commit、未 push）。focused tests / full pytest / `scripts/check.sh`
> 全绿（3274 passed = Step 15 baseline 3256 + 18 新增）。

**16F 决定**：

> peer_alignment 抽公共模块**方向正确**，但**不**作为当前下一步立即执行的
> 任务。它被**降级**为：
>
> - **第一批核心重建 PR 候选**（17A 之后）
> - 必须等**全系统模块站队**完成（16G）+ **清场决策表**完成（16H）+
>   **核心链重建执行计划**完成（16I）后**再重新评估**是否第一个执行
> - 不允许"既然代码改动已经在 worktree 里了，就顺手 commit 进 main"

**对当前 worktree uncommitted 改动的处置建议**（**非本记录强制**；
留给用户单独决定）：

> **推荐**：用户单独发起一次 `git restore` / `git clean -fd services/peer_alignment.py
> tests/test_peer_alignment_boundary.py` + `git checkout --
> services/exclusion_layer.py services/main_projection_layer.py`，
> 把这 4 个文件还原到 main HEAD（commit `932d243`）状态，与 16F
> no-patching 原则保持一致。
>
> **本记录不实施任何 `git restore` / `git checkout` / `git clean`**
> （严守 §17 边界 + 用户授权要求）。
>
> **替代选项**：如果用户明确希望保留 worktree 的 PR-1 work，**也**可以
> 把这 4 个文件**留在本地** worktree（不 commit / 不 push），等到 17A
> 阶段重新评估时直接复用。这种情况下需要确保未来 16G / 16H / 16I 的
> 各轮**不**意外把这些 untracked / modified 文件带入它们的 commit。

无论哪种选择，**本记录的核心约束不变**：

> **PR-1 的 4 个文件改动在 16G / 16H / 16I 完成之前不允许 commit。**

---

## 6. 新执行顺序

把后续顺序从"16E → 16F (PR-1) → 17B (PR-2) → ..."调整为：

| Step | 内容 | 性质 | 依赖 |
|---|---|---|---|
| **16F**（本轮） | Architecture Reset No-Patching Principle | 文档（最高优先级原则） | 16E |
| **16G** | Full Module Decomposition / Complete Stand-up Pass | 文档（比 16B 更彻底的全仓库站队） | 16F |
| **16H** | Repository Clearing Decision Table | 文档（每个模块的 keep / bridge / quarantine / archive / delete 决定） | 16G |
| **16I** | Core Chain Rebuild Execution Plan | 文档（在 16G + 16H 基础上重新设计 PR 顺序） | 16H |
| **17A** | 第一批代码 PR（候选：peer_alignment） | 代码 | 16I |

> **明确**：
> - 16F / 16G / 16H / 16I **全部是文档轮**
> - 17A 才是第一个真正的代码 PR
> - 17A 的具体内容由 16I 决定，**不**预先锁死为 peer_alignment（虽然
>   peer_alignment 仍是强候选）
> - 任何"借 16G / 16H / 16I 顺手改代码"的提议**默认 reject**

---

## 7. 当前阶段真正要做什么

**16F → 16G → 16H → 16I 阶段**真正要做的事（文档级）：

1. **全仓库模块拆解**（16G）
   - 不只看核心 services，要扫描全部目录：
     - `services/` 109 个文件
     - `ui/` 18 个文件
     - 顶层 .py：app.py / predict.py / scanner.py / matcher.py /
       encoder.py / feature_builder.py / data_fetcher.py / research.py /
       run_pipeline.py / run_1000day.py / stats_reporter.py
     - `scripts/` 30+ 文件
     - `archive/legacy/root_stubs/`
     - `records/`
     - tests/（仅 inventory，**不**改 tests）
2. **所有模块站队**（16G）
   - 比 16B 更彻底；16B 留下 ≥ 35 个 `UNKNOWN_REVIEW_REQUIRED`，16G
     必须把这些数字降到接近 0
   - 每个模块标 1.0 §15 的标签之一
3. **找出重复模块**（16G / 16H）
   - 例如 `services/projection_chain_contract.py` feature 部分 vs
     `services/feature_builder.py`；`services/consistency_layer.py` vs
     `services/confidence_evaluator._compute_agreement`；`services/peer_adjustment.py` vs
     `peer_alignment` 的 peer 信号
4. **找出旧链残留**（16G）
   - 不只 V1 / V2 orchestrator；还要审 `services/projection_*.py` /
     `services/predict_*.py` 全部 26+ 个文件
5. **找出 active dependency**（16G / 16H）
   - 每个 LEGACY_ACTIVE_DEPENDENCY 模块的 active import / caller graph
6. **决定哪些退出 active surface**（16H）
   - `OFFLINE_ONLY` / `KEEP_FROZEN_DIAGNOSTIC` / `ARCHIVE` / 待 archive
7. **决定哪些移出 repo**（16H）
   - raw artifacts / DB backup / `.claude/worktrees/`（已 14K ignore）
8. **决定哪些重建**（16H / 16I）
   - 9 分支正式架构内的模块；新建 `services/architecture_orchestrator.py`
     等

> 这 8 件事**全部是文档级判断**，**不**写代码。

---

## 8. 和 16E 的关系

**16E 的 PR 列表仍有参考价值**：

- 16E §3 列出的 PR-1 (peer_alignment 抽公共模块) / PR-2 (去
  `exclusion_result` 形参) / PR-3 (confidence key 对齐) / PR-4
  (`architecture_orchestrator` MVP) / PR-5 (UI / evaluation migration
  plan) / PR-6 (Bridge deprecation markers) **方向都正确**
- 它们**仍然**是未来重建 PR 的强候选

**但 16E 不能直接触发代码 PR**：

- 16E **不**作为"下一步立即执行"的指令
- 16E PR-1/2/3/4 必须等 **16G + 16H + 16I 完成后**重新确认
- 16I 有权基于 16G / 16H 的结果**重新排序** 16E 的 PR 列表，或**新增 /
  删除** PR 候选
- 任何"按 16E §3 顺序立即开 PR-1"的提议在 16I 完成前**默认 reject**

> 16E **保留**为 historical source（与 1.0 §14 / §16 维护规则一致）。
> 16F 不撤销 16E；16F 只是**显式拉回**执行节奏。

---

## 9. 不允许事项

本轮 + 16G / 16H / 16I 三轮**全部**严守：

- ❌ 不改代码（`.py` 文件零修改）
- ❌ 不启动 PR-1（peer_alignment 抽公共模块的代码动作）
- ❌ 不启动任何 16E §3 列出的 PR
- ❌ 不做局部 patch（即使发现明显 bug 也不改；记录到 16G / 16H 决策表中）
- ❌ 不删除文件
- ❌ 不移动文件
- ❌ 不修改 `.gitignore`
- ❌ 不处理 handoff
- ❌ 不处理 logs / DB backup / `.claude/worktrees/`
- ❌ 不跑 evaluation / replay / validation
- ❌ 不写 DB / 不改 DB schema
- ❌ 不默认迁移 `run_predict` 到 V2
- ❌ 不接 trading
- ❌ 不输出 buy / sell / hold / hard / forced / required
- ❌ 不进入 3R-5 / 3R-6（1.0 §12 / 16A §18 / 16C §13 锁定）
- ❌ 不复活 `continuous_smoothing*` / `archive/legacy/root_stubs/*` / promotion 三模块
- ❌ 不借任一步顺手 commit 上一轮的 PR-1 work

---

## 10. 推荐下一步

**首选**：

> **Step 16G：Full Module Decomposition / Complete Stand-up Pass**

理由：

- 16F 已锁原则：当前阶段是 Architecture Reset，不是 patching
- 16G 要做的事：对**全仓库模块**做更彻底的拆解和站队（不只核心
  services）。具体范围见 §7 第 1 / 2 项
- 16G 输出：每个模块带 1.0 §15 标签的总表；`UNKNOWN_REVIEW_REQUIRED`
  数量从 16B 的 ≥ 35 降到接近 0

**先决条件（用户决定）**：

> 在开 16G 之前，**用户需要决定** worktree 中 PR-1 uncommitted 4 文件的
> 处置（§5）：
>
> - 选项 A：discard（推荐）—— `git restore` + `git clean` 把 worktree 还原
>   到 main HEAD（`932d243`）状态；与 16F 原则一致
> - 选项 B：本地保留 untracked / unstaged，等 17A 重新评估时复用 ——
>   16F 原则下也允许，但需在 16G / 16H / 16I 各轮 commit 时**显式排除**
>   这 4 个文件，避免误带入文档 commit
>
> 16F 文档**不**实施任一选项；本记录只列出决策路径。

**不推荐**：

- 不推荐借 16F 顺手 commit PR-1（违反 16F §4 / §5 / §9）
- 不推荐跳过 16G 直接进 16H / 16I / 17A
- 不推荐借任一步解锁 3R-5 / 3R-6（1.0 §12 7 项前提必须全部满足）

---

## 11. 严守边界

本轮 Step 16F **只**写 no-patching principle 文档：

- ❌ 未改业务代码（无 `.py` 文件被本轮修改；上一轮 PR-1 留下的 4 个 worktree
  改动**不属本轮**，本轮**未触碰**它们）
- ❌ 未新增测试（`tests/` 字节本轮未变）
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

唯一新增文件：[tasks/record_16f_architecture_reset_no_patching_principle.md](tasks/record_16f_architecture_reset_no_patching_principle.md)（本文件）。

后续修改路径：任何对 §2 用户原则 / §4 禁止事项 / §5 peer_alignment
重新定位 / §6 新执行顺序 / §7 阶段任务 / §8 与 16E 关系 / §9 禁止 /
§10 下一步的调整，都必须**显式更新本文件**；同时检查是否需要同步更新
1.0 / 16A / 16B / 16C / 16D / 16E。
