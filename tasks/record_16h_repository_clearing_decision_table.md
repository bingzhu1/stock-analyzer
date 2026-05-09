# 16H记录：Repository Clearing Decision Table

> 本记录是 **Step 16H：清场决策表**。1.0 canonical / 16A blueprint /
> 16B inventory / 16C target dataflow & contract decision / 16D isolation
> & quarantine plan / 16E core chain refactor plan / 16F no-patching
> principle / 16G full module decomposition standup 已全部入 main
> （main 最新 commit `ba6bc7d`）。本轮把 16G 的全仓库分类**转换为**清场
> 决策表：每条 inventory 项落 8 个清场标签之一。
>
> 本轮**只**做决策：未改业务代码、未新增测试、未删除文件、未移动文件、
> 未修改 `.gitignore`、未处理 handoff、未处理 logs / DB backup /
> `.claude/worktrees/`、**未处理 `avgo_agent.db`**、未跑 replay /
> validation / historical evaluation、未写 DB / 未改 DB schema、未默认
> 迁移 `run_predict` 到 V2、未接 trading、未输出 buy / sell / hold /
> hard / forced / required、未进入 3R-5 / 3R-6、未启动任何代码 PR、
> 未 commit / 未 push。
>
> 唯一 deliverable：本文件。

---

## 1. Step 16H 目的

把 16G 全仓库拆解结果**转换为**清场决策表：

- 每个文件 / 模块 / group 落一个清场标签（§3 的 8 个标签之一）
- 给出原因 / 前置条件 / 风险 / 是否需要用户确认 / 下一步动作
- **本轮不执行任何清场动作**（不删 / 不移动 / 不改 .gitignore）
- 16I 在本表之上重新设计核心链 refactor PR 顺序（**不**自动沿用 16E PR-1）

> **本文件性质**：决策（decision），不是执行（execution）。所有"删除 /
> 移动 / archive / .gitignore 改动"留待 16I 之后的代码 PR + 用户单独确认。
>
> **16F 原则不变**：本轮不开任何代码 PR；不顺手 patch；不复活已 quarantine
> 的模块。

---

## 2. 当前前置条件

| 项 | 状态 |
|---|---|
| 1.0 canonical principles 已入 main | ✅ commit `5c209bb` |
| 16A architecture reset blueprint 已入 main | ✅ commit `9b98ad5` |
| 16B module standup ownership inventory 已入 main | ✅ commit `bdd1314` |
| 16C target dataflow & contract decision 已入 main | ✅ commit `b05d7c8` |
| 16D isolation / quarantine plan 已入 main | ✅ commit `694450e` |
| 16E core chain refactor plan 已入 main | ✅ commit `932d243` |
| 16F architecture reset no-patching principle 已入 main | ✅ commit `6cfaa9b` |
| 16G full module decomposition standup 已入 main | ✅ commit `ba6bc7d` |
| Step 12–15 boundary fixes / regression / cleanup / signoff | ✅ 全部入 main |
| main 最新 commit | `ba6bc7d` |
| worktree 唯一 deliberate untracked | `.claude/handoffs/task_089_post_pr_cleanup.md` |
| 战略阶段 | 从全模块站队（16G）→ 清场决策（16H 本轮） |
| 3R-5 / 3R-6 | ❌ 仍然不允许进入 |
| 第一个代码 PR | ❌ 必须等 16I 完成后由 16I 决定 |
| 16G UNKNOWN 数 | 10（5 active_rule_pool* + projection_output_adapter + primary_bias_diagnosis + inspect_analysis + five_state_margin_policy + research.py） |

**关键校正**（见 §5）：

> 16G §5.2 / §14.6 称 `avgo_agent.db` "当前 tracked"是**误判**。
> 实际：`avgo_agent.db` **未被 git tracked**，且已被 `.gitignore:11`
> 行 `avgo_agent.db` 显式 ignore。`git ls-files avgo_agent.db` 返回空；
> `git check-ignore -v avgo_agent.db` 命中 `.gitignore:11:avgo_agent.db`。
> 16H §5 显式撤销该"紧急议题"标记。
> 16G 文档**不**回溯修改（16F 原则）；本校正以本记录为准。

---

## 3. 决策标签定义

| 标签 | 含义 | 适用对象 | 立即执行？ | 用户确认？ | 需要 regression？ |
|---|---|---|---|---|---|
| `KEEP` | 保留在主仓库；属正式架构或必要 infra | CORE_* / CONFIG_INFRA / 必要 fixture / `KEEP_ACTIVE` | 不需要执行（是常态） | 否 | 否 |
| `MOVE_OUTSIDE_REPO` | 移到本地或外部 archive；不进 repo | raw artifact / DB backup / live DB / `.claude/worktrees/` | ❌ 本轮不执行 | ✅ 必需（每项单独确认） | 否（不影响代码） |
| `ARCHIVE_IN_REPO` | 移到 `archive/legacy/<sub>/`；保留为历史证据 | 已不再 active 但有历史价值的 records / reports / 退役模块 | ❌ 本轮不执行；留待 17A+ | ✅ 必需 | ✅ 必需（确认 active import = 0） |
| `QUARANTINE` | 加 deprecation marker；待 caller 全部迁完后再 archive | LEGACY_ACTIVE_DEPENDENCY / TEMP_MIGRATION_BRIDGE | ❌ 本轮不执行；留待 16I PR | 否（marker only） | ✅ 必需（确认行为不变） |
| `DELETE_NOW` | 立即可删（active import = 0 + 已 archive + 用户确认） | **本表为空**（见 §13） | — | — | — |
| `DELETE_LATER` | 满足前置条件后才能删（必须先 archive + 满足 caller 迁移） | Bridge schema 字段 / Bridge 模块 / DUPLICATE 旧版本 | ❌ 本轮不执行；可能 17A+ | ✅ 必需 | ✅ 必需 |
| `MIGRATE_CALLER_FIRST` | 必须先迁 caller 才能动 | Bridge / LEGACY 主链路 | ❌ 本轮不执行；16I PR | 否（迁移期间） / ✅（archive 时） | ✅ 必需 |
| `DEEP_AUDIT_REQUIRED` | 16I 之前必须 deep audit；不能落决策 | 16G UNKNOWN 10 项 | ❌ 不可执行 | 否（audit 阶段） | 否（audit 阶段） |

> **本轮约束**：所有标签都**只是决策**，**不触发**任何 `git rm` / `mv` /
> `.gitignore` 改动。任何执行动作必须等到 16I 之后的代码 PR + 用户单独
> 确认。

---

## 4. Repository Clearing 总表

> 列含义：
> - `path / group`：相对 repo root
> - `current_label from 16G`：16G 给出的标签
> - `clearing_decision`：本表的清场决策（§3 的 8 个之一）
> - `reason`：决策依据
> - `prerequisite`：执行前的前置条件
> - `risk`：执行风险（H/M/L）
> - `user_confirm`：是否需要用户单独确认
> - `next_step`：16I / 17A+ 的下一步动作

### 4.1 Root-level 紧急 / 常态项

| path | 16G label | clearing_decision | reason | prerequisite | risk | user_confirm | next_step |
|---|---|---|---|---|---|---|---|
| `avgo_agent.db` | `RAW_ARTIFACT` (16G §5.2) | **`KEEP`**（local-only，已 ignored） | 16G 误判；实际 `git ls-files` 空，已被 `.gitignore:11` 覆盖 | — | L | 否 | §5：在 16I 文档中加一条 explicit note；不动文件 |
| `predict.py` | `TEMP_MIGRATION_BRIDGE` | **`MIGRATE_CALLER_FIRST`** → `DELETE_LATER` (Phase 6+) | UI / replay / scripts 5 处依赖 | Bridge #1 + #2 + #4 全部满足 | H | ✅ archive 时必需 | 16I：thin wrapper 设计；17A+ PR |
| `app.py` | `CORE_UI` | `KEEP` | 入口；hard rule 3 锁最小改动 | — | M | 否 | 16I：UI schema 切换设计 |
| `scanner.py` / `matcher.py` / `encoder.py` | `CROSS_LAYER_MODULE` | `KEEP` | hard rule 2 锁定不可重写；跨 B1/B2/B3 | — | M | 否 | 16I：拆 layer 边界（不改文件） |
| `feature_builder.py` / `data_fetcher.py` | `CORE_FEATURE` / `CORE_DATA` | `KEEP` | 正式架构内 | — | L | 否 | 保留 |
| `research.py` | `UNKNOWN_REVIEW_REQUIRED` | **`DEEP_AUDIT_REQUIRED`** | 16G 未通读；待 16H-2 / 16I 决定归位 | grep active caller | L | 否 | 16H-2 deep audit |
| `run_pipeline.py` / `run_1000day.py` / `stats_reporter.py` | `CORE_EVALUATION` + `SCRIPT_ONLY` | `KEEP`（顶层 entrypoint） | 离线 entry；保留 | — | L | 否 | 16I：可选迁入 services/ 决定 |
| `AVGO_Task1_8_Validation_Report.md` | `DOC_ONLY` + `QUARANTINE_CANDIDATE` | **`ARCHIVE_IN_REPO`**（候选 `archive/legacy/reports/`） | 历史报告；不再 active | grep 确认无引用 | L | ✅ | 17A+ archive PR |
| `.env.example` / `.gitignore` / `requirements.txt` / `runtime.txt` / `AGENTS.md` / `一键启动说明.md` / `启动博通系统.bat` / `启动博通系统.command` | `CONFIG_INFRA` / `DOC_ONLY` / `TOOL_LAYER` | `KEEP` | 必要 infra | — | L | 否 | 保留 |

### 4.2 services/ 109 文件 — 按 §6–§11 分组决策

详见后续章节。汇总如下：

| 分类 | 计数 | 决策 |
|---|---|---|
| `CORE_DATA` (B1) | 4 | `KEEP` |
| `CORE_FEATURE` (B2) | 4 | `KEEP` |
| `CORE_PROJECTION` (B3) | 1 + 2 preflight | `KEEP` |
| `CORE_EXCLUSION` (B4) | 1 | `KEEP` |
| `CORE_CONFIDENCE` (B5) | 1 + 1 数据准备 | `KEEP` |
| `CORE_FINAL_REPORT` (B6) | 5 (含 cross) | `KEEP` |
| `CORE_REVIEW_LEARNING` (B7) | 14 + 1 helper | `KEEP` |
| `CORE_EVALUATION` (B8) | 16 (含 dashboard tools) | `KEEP` |
| `TOOL_LAYER` (候选 B9 子层) | 17 | `KEEP`（待 16I 决定是否成为 Branch 9 子层） |
| `CROSS_LAYER_MODULE` 明确 | 11 | `MIGRATE_CALLER_FIRST` 或 `DEEP_AUDIT_REQUIRED`（按模块） |
| `TEMP_MIGRATION_BRIDGE` (services) | 2 | §6 |
| `LEGACY_ACTIVE_DEPENDENCY` | 12 | §7 全部 `MIGRATE_CALLER_FIRST` |
| `KEEP_FROZEN_DIAGNOSTIC` | 2 | `KEEP` |
| `OFFLINE_ONLY` | 4 | `KEEP`（永久离线） |
| `UNKNOWN_REVIEW_REQUIRED` | 9 | `DEEP_AUDIT_REQUIRED` |

### 4.3 ui/ 18 文件

全部 **`KEEP`**（Branch 9）。`ui/predict_tab.py` 标记 `MIGRATE_CALLER_FIRST`
作为 Bridge #1 子项（16I 设计 schema 迁移 PR）。

> 校正：16G §5.4 称 17 个 ui/ 文件，实际 `git ls-files ui | wc -l = 18`
> （含 `ui/__init__.py`）。差异不影响清场决策。

### 4.4 scripts/ 29 文件（28 .py + check.sh）

| 子分类 | 文件数 | 决策 |
|---|---|---|
| `CONFIG_INFRA` (check.sh) | 1 | `KEEP` |
| `KEEP_FROZEN_DIAGNOSTIC` (continuous_smoothing 5 个) | 5 | `KEEP`（永久 frozen） |
| `EVALUATION_SCRIPT` (10 个) | 10 | `KEEP` |
| `REPLAY_SCRIPT` (4 个) | 4 | `KEEP` |
| `DASHBOARD_SCRIPT` (含 3 个 DUPLICATE) | 6 | `KEEP` for 3 unique；`MIGRATE_CALLER_FIRST` for 3 DUPLICATE（§11） |
| `MIGRATION_SCRIPT` (save_projection_records_smoke) | 1 | `KEEP`（Bridge 期间）；Bridge 退出后随之 `MIGRATE_CALLER_FIRST` |
| `LOCAL_TOOL` (soft_metadata_simulator DUPLICATE) | 1 | `MIGRATE_CALLER_FIRST`（§11） |
| `CROSS_BRIDGE_CALLER` (run_e2e_loop) | 1 | `MIGRATE_CALLER_FIRST`（Bridge #4） |

### 4.5 tests/ 165 文件 — 全部 `KEEP`

| 分类 | 计数 | 决策 |
|---|---|---|
| `CORE_BOUNDARY_TEST` | ~22 | **`KEEP`** 永久保留 |
| `CONTRACT_TEST` | ~8 | **`KEEP`** 永久保留 |
| `CORE_MODULE_TEST` | ~80 | `KEEP` |
| `LEGACY_BRIDGE_TEST` | 4 | `MIGRATE_CALLER_FIRST` → `ARCHIVE_IN_REPO` 随 Bridge 退出 |
| `UI_TEST` | ~12 | `KEEP` |
| `EVALUATION_TEST` | ~12 | `KEEP` |
| `FROZEN_DIAGNOSTIC_TEST` | 5 | `KEEP`（与 frozen 候选共存） |
| `OFFLINE_ONLY_TEST` | 4 | `KEEP` |
| `FIXTURE` | 3 | `KEEP` |
| `TOOL_TEST` | ~15 | `KEEP` |

### 4.6 tasks/ 173 文件

全部 **`KEEP`** + `DOC_ONLY` + `KEEP_FROZEN_DIAGNOSTIC` byte-frozen
（15 §6）。**不允许 retro-edit**。

### 4.7 records/ 1 文件

| path | 16G label | clearing_decision | next_step |
|---|---|---|---|
| `records/03_replay_accuracy_and_exclusion_accuracy.md` | `DOC_ONLY` + `KEEP_FROZEN_DIAGNOSTIC` | **`ARCHIVE_IN_REPO`**（候选 `archive/legacy/reports/`） | 17A+ archive PR；grep 确认无引用 + 用户确认 |

### 4.8 archive/legacy/root_stubs/ 4 文件

全部 **`KEEP`**（已 14D quarantine；保留 `_DEPRECATED.md` marker）。

### 4.9 logs/ tracked evidence 21 文件

全部 **`KEEP`** + `KEEP_FROZEN_DIAGNOSTIC`（15 §6 锁定）。

### 4.10 ignored raw artifacts

| 类型 | 当前状态 | 决策 |
|---|---|---|
| `avgo_agent.db`（root，**已 ignored**） | 14K + .gitignore:11 ignored；本地保留 | **`KEEP`**（local-only，已 ignored — 见 §5） |
| `avgo_agent.db.backup_*`（7 个） | 14K ignored；本地保留 | **`MOVE_OUTSIDE_REPO`**（用户单独确认） |
| 4 套 untracked replay / regime validation 子目录 | 14K ignored；本地保留 | **`MOVE_OUTSIDE_REPO`**（用户单独确认；可保留 markdown summary） |
| `.claude/worktrees/` 26 个 | 14K ignored；harness 自动管理 | **`KEEP`**（不在 16H 范围；harness 自动） |

### 4.11 .claude/handoffs/

| path | 决策 |
|---|---|
| `.claude/handoffs/task_089_post_pr_cleanup.md` | **`KEEP`**（14L A2 / 14M / 15 §2 deliberate keep local untracked） |

---

## 5. avgo_agent.db 紧急议题（**校正**）

### 5.1 16G 误判说明

> **16G §5.2 与 §14.6 称 `avgo_agent.db` 是 tracked。这是误判。**
>
> 实际状态（本轮 readonly check 结果）：
>
> ```
> $ git ls-files avgo_agent.db
> (空输出 — 文件未被 git tracked)
>
> $ git check-ignore -v avgo_agent.db
> .gitignore:11:avgo_agent.db    avgo_agent.db
>
> $ ls -la avgo_agent.db
> -rw-r--r--@ 1 may  staff  98304 May  9 12:38 avgo_agent.db
> ```
>
> `.gitignore` 第 11 行明确写了 `avgo_agent.db`（不是 `*.backup_*`）。
> 文件**自始就被 ignore**，**不在 git 追踪中**。

### 5.2 16H 校正后的决策

> **`clearing_decision` = `KEEP`（local-only，已 ignored）**
>
> - 文件类型：`RAW_ARTIFACT`
> - 当前位置：repo root（仅本地）
> - 是否 tracked：**否**
> - 是否 ignored：**是**（`.gitignore:11`）
> - 是否需要处理：**否**
> - 是否需要用户确认：**否**
> - 16H 紧急议题：**撤销**

### 5.3 不实施的事

- ❌ 不 `git rm --cached avgo_agent.db`（本来就不在 cache 中）
- ❌ 不改 `.gitignore`（已经覆盖）
- ❌ 不移动该文件
- ❌ 不删除该文件
- ❌ 不创建外部备份路径（保持现状）

### 5.4 16G 文档处理

> 按 16F no-patching 原则，**不**回溯修改 16G 文档。
> 本 16H §5 作为正式校正记录；任何后续 reviewer 看 16G §5.2 / §14.6 时
> 必须**同步**参考本节。
> 1.0 §14 冲突仲裁规则：**以 16H 为准**。

### 5.5 仍需 16I 关注的相关问题

> 虽然 `avgo_agent.db` 不需 untrack，但 16I 仍应回答两个相关问题
> （**不**在本轮处理）：
>
> 1. `avgo_agent.db` 当前是 live SQLite DB；UI / scripts 是否仍写入？
>    若是，需要明确"DB 变更不进 git" 的工程约束（已通过 ignore 实现，但
>    应文档化）
> 2. 是否有 schema migration / seed 机制让新开发者能 bootstrap 一个本地
>    `avgo_agent.db`？若没有，新人入门会缺 DB

---

## 6. TEMP_MIGRATION_BRIDGE 清场决策

| path | 16G label | clearing_decision | reason | prerequisite | next_step |
|---|---|---|---|---|---|
| `predict.py` | `TEMP_MIGRATION_BRIDGE` | **`MIGRATE_CALLER_FIRST`** → `DELETE_LATER`（Phase 6+） | UI / replay / scripts 5 处依赖；Phase 6 变 thin wrapper 后 archive | Bridge #1 + #2 + #4 全部满足 | 16I 设计；17A+ PR |
| `services/predict_legacy_adapter.py` | `TEMP_MIGRATION_BRIDGE` | **`MIGRATE_CALLER_FIRST`** → `DELETE_LATER`（Phase 7） | `predict.py:44` 仍 import；Phase 6 thin wrapper 后不再需要 | Bridge #5 满足 | 同上 |
| `services/predict_legacy_v2_bridge.py` | `TEMP_MIGRATION_BRIDGE` | **`ARCHIVE_IN_REPO`**（第一个独立解散候选） | active import = 0（13 §5 / 15 §5 / 16G §6 已确认）；只有 tests 仍引用 | tests 改读 archive 副本或断言 archived | 16I 早期 archive PR；用户确认 |
| Bridge schema 字段（`final_bias` / `final_confidence` / `confidence` / `primary_projection` / `peer_adjustment` / `final_projection` / `path_risk` / `peer_path_risk_adjustment`） | schema only | **`DELETE_LATER`**（Phase 8 整段从 `compatibility_metadata` 删除） | UI / replay / evaluation / tests 全部迁完 | Bridge 全部 6 项退出条件满足 | 16I 设计 |

> 进度：6 项退出条件 **0/6 完全满足**；可独立解散候选 = 1
> （`predict_legacy_v2_bridge`，但**本轮不实施**）。

---

## 7. LEGACY_ACTIVE_DEPENDENCY 清场决策

**全部决策 = `MIGRATE_CALLER_FIRST`**。**不**直接删；先由 `architecture_orchestrator`
（16I 起新建）接管，再断 caller，再 archive。

| path | active caller | next_step |
|---|---|---|
| `services/projection_orchestrator.py` | `services/projection_orchestrator_v2.py:16` | 16I 切断 V2 → V1 反向调用；archive |
| `services/projection_orchestrator_v2.py` | 5 处（projection_entrypoint / projection_v2_adapter / historical_replay_training / save_projection_records_smoke / predict.py lazy） | 16I `architecture_orchestrator` 上线 + 5 个 caller 全部迁移 |
| `services/projection_orchestrator_preflight.py` | V1 / V2 共用 | 16I 合并到 `architecture_orchestrator` 内部 preflight |
| `services/projection_entrypoint.py` | 部分 services / scripts；V2 wrapper | V2 主入口决定后随之迁移 |
| `services/projection_v2_adapter.py` | 部分 services；V2 adapter | 16I Phase 7 archive |
| `services/home_terminal_orchestrator.py` | `app.py:86, 1899` | 16I 内部实现替换为 `architecture_orchestrator` 薄包装；**保留**作 UI orch（不 archive） |
| `services/primary_20day_analysis.py` | `projection_orchestrator_v2._build_primary_analysis` | 16I 决定合并 vs archive |
| `services/peer_adjustment.py` | `projection_orchestrator_v2._build_peer_adjustment` | 16I 拆解：peer 信号 → Branch 2 Feature；"调整推演方向"语义 archive |
| `services/historical_probability.py` | `projection_orchestrator_v2._build_historical_probability` | 16I 决定合并 vs archive |
| `services/predict_summary.py` | `services/projection_orchestrator.py:22` | V1 不再被调用后随之 archive |
| `services/consistency_layer.py` | `home_terminal_orchestrator.py:22`、`projection_orchestrator_v2.py:23` | 16I 把逻辑吸收到 `confidence_evaluator._compute_agreement` + `_combine_confidence`；archive |
| `services/ai_summary.py` | UI / 链 | **不** deprecate；保留为 Branch 6 narrative 选项；不解禁 default-disabled |

> 共 12 项。全部**当前不能删**。

---

## 8. CORE modules 清场决策

**全部决策 = `KEEP`**。

| Branch | 核心模块（计数）|
|---|---|
| 1 Data | 5 |
| 2 Feature | 5 (含 future new `peer_alignment`) |
| 3 Projection | 1 + 2 preflight |
| 4 Exclusion | 1 |
| 5 Confidence | 1 + 1 数据准备 |
| 6 Final Report | 5 (含 cross-layer persistence) + future `architecture_orchestrator` |
| 7 Review & Learning | 14 + 1 internal helper |
| 8 Evaluation | 16 |
| 9 UI | app.py + 18 ui/ + 17 TOOL_LAYER (candidate sub-layer) |

> CORE 不是清理对象，是后续重建对象（与 16D §4 / 16G §6 一致）。

---

## 9. KEEP_FROZEN_DIAGNOSTIC / ARCHIVE 决策

| path | clearing_decision |
|---|---|
| `services/continuous_smoothing_candidate.py` / `_v2.py` | **`KEEP`**（永久 frozen；06 §8 / 07B §11 / 07C §12 / 07D §12 / 1.0 §6.17） |
| 5 个 `scripts/run_continuous_smoothing_validation*` | **`KEEP`**（永久 frozen） |
| `archive/legacy/root_stubs/_DEPRECATED.md` + 3 stubs | **`KEEP`**（已 14D quarantine） |
| 21 个 logs/ tracked evidence | **`KEEP`**（15 §6 锁定） |
| `records/03_replay_accuracy_and_exclusion_accuracy.md` | **`ARCHIVE_IN_REPO`** 候选（17A+ PR；用户确认） |
| `AVGO_Task1_8_Validation_Report.md`（root） | **`ARCHIVE_IN_REPO`** 候选（17A+ PR；用户确认） |

**所有"DELETE_LATER 路径"必须满足**：

1. active import = 0（grep 验证）
2. 已存在 archive 副本（archive/legacy/<sub>/）
3. 用户单独确认
4. **任何**删除必须**另开 archive/delete pass**，不允许借 16I refactor PR 顺手删

---

## 10. UNKNOWN 剩余项决策

**16G 剩余 10 项，全部决策 = `DEEP_AUDIT_REQUIRED`**。
**不能删，不能迁移，不能改，先深审**。

| path | 16G note | deep audit 内容 | 谁审 |
|---|---|---|---|
| `services/active_rule_pool.py` | 与 promotion 命名空间共享 | active caller graph + 与 promotion 三模块隔离 + B5/B7 归位 | 16H-2 / 16I |
| `services/active_rule_pool_calibration.py` | 候选 B5 数据准备 | 同上 | 同上 |
| `services/active_rule_pool_drift.py` | 候选 B5/B7 | 同上 | 同上 |
| `services/active_rule_pool_export.py` | 候选 B7/B8 | 同上 | 同上 |
| `services/active_rule_pool_validation.py` | 候选 B8 | 同上 | 同上 |
| `services/projection_output_adapter.py` | docstring 写"not yet wired" | grep active import；定 dormant vs active | 同上 |
| `services/primary_bias_diagnosis.py` | 是诊断还是决策？ | 内部行为 + 是否进入决策路径 | 同上 |
| `services/inspect_analysis.py` | 候选 B7 / B9 / TOOL | active caller graph | 同上 |
| `services/five_state_margin_policy.py` | 候选 Branch 3 内部 | 内部行为 + active caller | 同上 |
| `research.py` | 顶层 research entry；用途不明 | grep active caller；定归位 | 同上 |

> 深审在 16I（或先插一步 16H-2）完成；**16I 之前不做归位决策**。

---

## 11. DUPLICATE / CROSS_LAYER 决策

### 11.1 5 组 DUPLICATE_FUNCTIONALITY

| 组 | 决策 | next_step |
|---|---|---|
| `services/regime_diagnostics_dashboard.py` ↔ `scripts/regime_diagnostics_dashboard.py` | **`MIGRATE_CALLER_FIRST`**（拆 services 数据组装 + scripts entrypoint） | 16I 拆分设计 |
| `services/anti_false_exclusion_dashboard.py` ↔ `scripts/anti_false_exclusion_dashboard.py` | 同上 | 同上 |
| `services/soft_metadata_simulator.py` ↔ `scripts/soft_metadata_simulator.py` | 同上 | 同上 |
| `services/consistency_layer.py` ↔ `services/confidence_evaluator._compute_agreement` | **`MIGRATE_CALLER_FIRST`** → `ARCHIVE_IN_REPO`（合并 logic 后 archive consistency_layer） | 16I 合并设计 |
| `services/peer_adjustment.py` peer 信号 ↔ 未来 `services/peer_alignment.py` ；`services/primary_20day_analysis.py` ↔ `services/main_projection_layer.py` | **`MIGRATE_CALLER_FIRST`** → `ARCHIVE_IN_REPO`（拆 / 合并后 archive） | 16I 拆解设计 |

### 11.2 11 项 CROSS_LAYER（参见 16G §5.3.15）

| module | 决策 | next_step |
|---|---|---|
| `services/projection_chain_contract.py` | **`MIGRATE_CALLER_FIRST`**（拆 feature helpers → 新 module；payload assembler → `architecture_orchestrator`） | 16I 拆分设计 |
| `services/anti_false_exclusion_audit.py` | **`DEEP_AUDIT_REQUIRED`**（B4 内部 vs B7 vs B8） | 16H-2 / 16I |
| `services/anti_false_exclusion_dashboard.py` | **`DEEP_AUDIT_REQUIRED`** + DUPLICATE 处理 | 16H-2 / 16I |
| `services/big_up_contradiction_card.py` | **`DEEP_AUDIT_REQUIRED`**（是否对 projection 反向校验） | 16H-2 / 16I |
| `services/big_down_tail_warning.py` | **`DEEP_AUDIT_REQUIRED`** | 16H-2 / 16I |
| `services/exclusion_reliability_review.py` | **`DEEP_AUDIT_REQUIRED`**（B4 / B5 / B7） | 16H-2 / 16I |
| `services/regime_diagnostics_dashboard.py` | **`MIGRATE_CALLER_FIRST`** + DUPLICATE 处理 | 16I |
| `services/projection_three_systems_renderer.py` | **`DEEP_AUDIT_REQUIRED`**（B6 internal render vs B9 UI） | 16H-2 / 16I |
| `services/projection_narrative_renderer.py` | **`DEEP_AUDIT_REQUIRED`** | 16H-2 / 16I |
| `services/soft_metadata_injection.py` | **`DEEP_AUDIT_REQUIRED`**（与 promotion 隔离明确） | 16H-2 / 16I |
| `services/soft_metadata_simulator.py` | **`DEEP_AUDIT_REQUIRED`** + DUPLICATE 处理 | 16H-2 / 16I |

### 11.3 3 套并行 orchestrator

| 模块 | 决策 |
|---|---|
| `services/projection_orchestrator.py` (V1) | **`MIGRATE_CALLER_FIRST`** → `ARCHIVE_IN_REPO` |
| `services/projection_orchestrator_v2.py` (V2) | **`MIGRATE_CALLER_FIRST`** → `ARCHIVE_IN_REPO` |
| `services/home_terminal_orchestrator.py` (home) | **`MIGRATE_CALLER_FIRST`**（**保留**作 UI orch 薄包装） |

→ 16I 收敛到唯一 `services/architecture_orchestrator.py`。

---

## 12. raw artifacts / repo slimming 决策

| 类型 | 14K 状态 | 决策 | 用户确认 |
|---|---|---|---|
| `avgo_agent.db`（root，**ignored**） | ✅ ignored | **`KEEP`**（local-only） | 否（见 §5） |
| `avgo_agent.db.backup_*` 7 个 | ✅ ignored | **`MOVE_OUTSIDE_REPO`** | ✅ |
| 4 套 untracked replay / regime validation 子目录 | ✅ ignored | **`MOVE_OUTSIDE_REPO`**（保留 markdown summary 选项；走 17A+ archive PR） | ✅ |
| `logs/prediction_log.jsonl` | ✅ ignored | **`KEEP`**（local-only；运行时产生） | 否 |
| `.claude/worktrees/` 26 个 | ✅ ignored | **`KEEP`**（harness 自动管理） | 否 |

**写明**：

- 任何"在主仓库新建 raw output 目录"的提案**默认 reject**（与 1.0 §11 一致）
- 任何 MOVE / DELETE 必须用户单独确认
- **本轮不处理任何 artifact**

---

## 13. DELETE_NOW 清单

> **DELETE_NOW = empty**（空集合）

理由：

- 当前阶段仍以 `archive` / `migrate` / `audit` 为主
- 16D §3 已锁"先 archive 再 delete"
- 任何 delete 必须满足 (active import = 0) + (已 archive) + (用户确认) +
  (regression 通过)
- 当前没有任何文件**同时**满足这 4 个条件
- `predict_legacy_v2_bridge.py` 虽然 active import = 0，但属 `ARCHIVE_IN_REPO`
  候选，不是 `DELETE_NOW`（先进 archive，至少保留 1 个 release 周期回滚窗口）

---

## 14. 16I 的输入

16I（Core Chain Rebuild Execution Plan）必须**基于 16H 决策表**重新设计
PR 顺序，**不**自动沿用 16E PR-1 / PR-2 / PR-3 / PR-4 / PR-5 / PR-6。

**16I 必须回答**：

1. `architecture_orchestrator` 上线之前，能否先做 PR-3（confidence key 对齐）
   作为最小风险 PR？还是必须等所有 LEGACY_ACTIVE_DEPENDENCY 同步迁移？
2. 12 个 LEGACY_ACTIVE_DEPENDENCY 模块的迁移**顺序**（哪些先断 caller）
3. 5 组 DUPLICATE 的合并 / 拆分方案（先做哪个）
4. 11 项 CROSS_LAYER 的 deep audit 路径（16H-2 vs 直接 16I 内）
5. 10 项 DEEP_AUDIT_REQUIRED 的 audit 顺序（哪些卡住主链）
6. 16E PR-1/2/3/4/5/6 中哪些**保留**、哪些**重排**、哪些**新增**
7. Bridge 8 阶段（16C §11）每阶段对应的代码 PR 数量与依赖
8. 17A 第一个代码 PR 的具体内容（候选：peer_alignment 抽出 / consistency_layer 合并 /
   confidence key 对齐 / `architecture_orchestrator` skeleton 之一）

**16I 的输出形式**：与 16E 同体例（PR-1 / PR-2 / ... 每条含目标 / 范围 /
文件 / 测试 / 验收 / 回滚），但**整体 PR 列表必须**显式说明与 16E 的
对比（保留 / 重排 / 新增 / 删除）。

---

## 15. 不允许事项

本轮 + 16H-2（如有） + 16I 严守：

- ❌ 不改代码
- ❌ 不删文件
- ❌ 不移动文件
- ❌ 不修改 `.gitignore`
- ❌ 不处理 `avgo_agent.db`（已 ignored；§5 校正）
- ❌ 不处理 handoff
- ❌ 不处理 logs / DB backup / `.claude/worktrees/`
- ❌ 不跑 evaluation / replay / validation
- ❌ 不启动 peer_alignment 或任何 16E §3 列出的 PR
- ❌ 不启动任何代码 PR
- ❌ 不进入 3R-5 / 3R-6（1.0 §12 / 16A §18 / 16C §13 / 16F §9 锁定）
- ❌ 不输出 trading action / hard / forced / required
- ❌ 不复活 `continuous_smoothing*` / `archive/legacy/root_stubs/*` /
  promotion 三模块 / `protection_layer_diagnostics`
- ❌ 不默认迁移 `run_predict` 到 V2
- ❌ 不借 16H 决策表顺手 archive / delete 任何文件
- ❌ 不回溯修改 16G（按 16F 原则；§5 校正以本记录为准）

---

## 16. 推荐下一步

**首选**：

> **Step 16I：Core Chain Rebuild Execution Plan**

理由：

- 16H 已为每条 inventory 项落清场标签
- 16I 在本表之上重新设计代码 PR 顺序（**不**自动沿用 16E）
- 16I 之后才是 17A 第一个代码 PR

**备选**（如必要）：

> **Step 16H-2：Deep Audit for Remaining UNKNOWN / CROSS_LAYER**

仅当 §10（10 项 UNKNOWN）+ §11.2（11 项 CROSS_LAYER 中 8 项 DEEP_AUDIT_REQUIRED）
影响 16I PR 顺序时使用；否则可在 16I 内一并处理。

**默认**：直接进 16I。

**不推荐**：

- 不推荐借 16H 顺手做代码改动
- 不推荐跳过 16I 直接进 17A
- 不推荐借任一步解锁 3R-5 / 3R-6
- 不推荐借 16I 自动复用 16E PR-1（必须重新评估）

---

## 17. 严守边界

本轮 Step 16H **只**写 clearing decision table：

- ❌ 未改业务代码（无 `.py` 文件被修改）
- ❌ 未新增测试（`tests/` 字节不变）
- ❌ 未删除文件
- ❌ 未移动文件
- ❌ 未修改 `.gitignore`
- ❌ 未处理 `avgo_agent.db`（§5 校正后无需处理）
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
- ❌ 未启动 peer_alignment PR / 未做任何局部 patch
- ❌ 未 commit / 未 push（按本轮指令）
- ❌ 未回溯修改 16G（§5 校正以本记录为准）

唯一新增文件：[tasks/record_16h_repository_clearing_decision_table.md](tasks/record_16h_repository_clearing_decision_table.md)（本文件）。

后续修改路径：任何对 §3 标签 / §4 总表 / §5 avgo_agent.db 校正 / §6
Bridge / §7 LEGACY / §8 CORE / §9 FROZEN/ARCHIVE / §10 UNKNOWN / §11
DUPLICATE/CROSS_LAYER / §12 raw artifacts / §13 DELETE_NOW / §14 16I 输入 /
§15 禁止 / §16 下一步 的调整，都必须**显式更新本文件**；同时检查是否
需要同步更新 1.0 / 16A / 16B / 16C / 16D / 16E / 16F / 16G。
