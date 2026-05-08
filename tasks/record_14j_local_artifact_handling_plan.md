# 14J记录：Local Artifact Handling Plan

> 本记录是 **Step 14 的第十阶段：local artifact handling plan**。Step 14I
> （commit `50c60f3`）已经把 cleanup status checkpoint 同步进 main，14
> 系列除 §8 local artifact 之外的明面工作已收束。
>
> 本轮**只写计划文档**：未改业务代码、未改测试、未删除 / 移动 / 新增任何
> artifact、未改 `.gitignore`、未跑 replay / real validation、未写 DB / 未
> 改 DB schema、未默认迁移 `run_predict` 到 V2、未 commit / push、未进入
> 3R-5 / 3R-6、未顺手碰任何 RISK / cleanup 候选项。

---

## 1. Step 14J 目的

只为 §2 列出的 **15** 项 local untracked artifacts 写**处理计划**：分类、
归属理由、推荐处理方式、是否需要用户单独确认。

明确**不**做的事：

- 不 `git add` 任何 untracked artifact
- 不 `git rm` / `rm` / `mv` 任何 artifact
- 不修改 `.gitignore`（即使本计划推荐添加新 pattern）
- 不打开 / 修改 `.db.backup_*` 字节
- 不修改 / 删除 `.claude/worktrees/` 下任何 worktree
- 不修改 / 删除 / 改名 `agent_loop.py` / `.claude/handoffs/task_089_post_pr_cleanup.md`
- 不进入 3R-5 / 3R-6
- 不启动任何 cleanup 实施（实施留待 14K+，且每一项需用户**单独**显式确认）

签收依据：[tasks/record_14a_cleanup_quarantine_plan.md](tasks/record_14a_cleanup_quarantine_plan.md)
§9（DO_NOT_TOUCH_LOCAL_ARTIFACT）+ [tasks/record_14i_cleanup_status_checkpoint.md](tasks/record_14i_cleanup_status_checkpoint.md)
§8 + §11.4（推荐 14J 完成 local artifact handling plan）。

---

## 2. 当前 main / git status 状态

| 项 | 值 |
|---|---|
| main 最新 commit | `50c60f3 docs(cleanup): record 14i cleanup status checkpoint` |
| 当前 worktree（`interesting-joliot-5962b5`）`git status --short` | 1 项：`?? logs/prediction_log.jsonl` |
| main 工作树 `git status --short` | 14 项 untracked artifacts |
| 本轮处理它们 | ❌ 否 |
| 是否运行 full pytest / scripts/check.sh 本轮 | ❌ 否（14J 是**纯计划文档**；不改代码不需要重跑；baseline 仍为 14F 实施时记录的 3256 passed / 0 failed） |

### 2.1 全部 15 项 untracked artifacts 一览（main + 当前 worktree 合并去重）

| # | path | 出现位置 |
|---|---|---|
| 1 | `.claude/handoffs/task_089_post_pr_cleanup.md` | main 工作树 |
| 2 | `.claude/worktrees/`（目录） | main 工作树 |
| 3 | `agent_loop.py` | main 工作树 |
| 4 | `avgo_agent.db.backup_pre_2099_hygiene_20260503_160409` | main 工作树 |
| 5 | `avgo_agent.db.backup_pre_3a3_20260504_013453` | main 工作树 |
| 6 | `avgo_agent.db.backup_pre_3a4_20260504_023331` | main 工作树 |
| 7 | `avgo_agent.db.backup_pre_4c3_rewrite_20260503_235604` | main 工作树 |
| 8 | `avgo_agent.db.backup_pre_replay_130_20260504_003707` | main 工作树 |
| 9 | `avgo_agent.db.backup_pre_replay_30_20260503_162636` | main 工作树 |
| 10 | `avgo_agent.db.backup_step_2c_2_6` | main 工作树 |
| 11 | `logs/historical_training/three_system_1005/` | main 工作树 |
| 12 | `logs/historical_training/three_system_w4_2024_08_2025_12/` | main 工作树 |
| 13 | `logs/historical_training/three_system_w4_smoke_2024_08_05_2024_08_09/` | main 工作树 |
| 14 | `logs/regime_validation/` | main 工作树 |
| 15 | `logs/prediction_log.jsonl` | 当前 worktree（main 工作树未见，worktree 间不同步） |

---

## 3. Artifact 分类原则

| 分类 | 定义 |
|---|---|
| **IGNORE_BY_GITIGNORE** | 应在 `.gitignore` 添加 pattern；artifact 本身留在本地 |
| **KEEP_LOCAL_MANUAL** | 继续本地保留，不纳入 git，不 ignore，由用户人工管理 |
| **MOVE_OUTSIDE_REPO** | 建议用户手动移到 repo 外（例如 `~/avgo_local_backups/`） |
| **ARCHIVE_TRACKED_DOC_ONLY** | 只把 markdown summary / 决策文档纳入 `tasks/` 或 `archive/`；不 commit 原始 raw output |
| **DELETE_CANDIDATE_USER_CONFIRM** | 可删除但**必须**用户显式确认，且建议在 `.gitignore` 加 pattern 防再生 |
| **UNKNOWN_REVIEW_REQUIRED** | 暂不判断；需进一步 read-only inspection（14L 阶段） |

> 多个分类可以同时适用一个 artifact（例如 IGNORE_BY_GITIGNORE +
> MOVE_OUTSIDE_REPO），按优先动作记录。

---

## 4. 当前 `.gitignore` 审计

### 4.1 当前 `.gitignore` 内容

```
__pycache__/
*.pyc
.DS_Store

data/
enriched_data/
coded_data/
match_results/
stats_results/
.venv/
avgo_agent.db
snapshots/
.env
!.env.example
.tmp_test_env/
.DS_Store
```

### 4.2 覆盖情况

| pattern | 是否覆盖 §2 untracked | 评估 |
|---|---|---|
| `avgo_agent.db` | ❌ 不覆盖 `avgo_agent.db.backup_*`；只匹配主 DB 文件 | 漏 7 个 DB backup |
| 无 `*.backup*` | ❌ | 漏 |
| 无 `logs/` | ❌ | 漏 4 个 logs 子目录 + `logs/prediction_log.jsonl` |
| 无 `.claude/worktrees/` | ❌ | 漏 26 个 worktree（共 ~390 MB） |
| 无 `.claude/handoffs/` | ❌（且**不能**整目录 ignore——`tasks/` 系列已经在用 handoff workflow，部分 handoff 是 tracked 或将来需要 tracked） | 部分漏 |
| 无 `agent_loop.py` | ❌ | 漏 |

### 4.3 推荐后续 `.gitignore` cleanup commit

> 推荐**Step 14K**（**仅**改 `.gitignore`，不动其他文件、不 add / 不 delete）：

```diff
+ # local DB backups
+ avgo_agent.db.backup_*
+
+ # standing local prediction log
+ logs/prediction_log.jsonl
+
+ # claude worktree caches (heavy; per-worktree session state)
+ .claude/worktrees/
+
+ # untracked replay / regime validation outputs (tracked outputs in
+ # logs/historical_training/03_fresh_replay/ + exclusion_action_validation_2e*
+ # + technical_features/ stay tracked)
+ logs/historical_training/three_system_1005/
+ logs/historical_training/three_system_w4_2024_08_2025_12/
+ logs/historical_training/three_system_w4_smoke_2024_08_05_2024_08_09/
+ logs/regime_validation/
```

> ⚠ 不一刀切 `logs/`：repo 已经把 `logs/historical_training/03_fresh_replay/` /
> `logs/historical_training/exclusion_action_validation_2e/` /
> `logs/historical_training/exclusion_action_validation_2e_v2/` /
> `logs/technical_features/...` 这 4 套 **tracked**（共 21 个 tracked log
> 文件），这些是历史 contract evidence，**不能**整目录 ignore。所以
> `.gitignore` 必须**逐目录** opt-in。

> ⚠ **不**在本计划里改 `.gitignore`；只是**推荐** 14K 单独执行。
> 14J 范围仅文档。

> 是否 ignore `.claude/handoffs/` 和 `agent_loop.py` 需要用户确认（详见 §7 / §8）。

---

## 5. logs artifacts 计划

### 5.1 逐项

| path | category | reason | recommended handling | user confirmation needed? |
|---|---|---|---|---|
| `logs/historical_training/three_system_1005/` (~48K, 9 文件) | **IGNORE_BY_GITIGNORE** + **KEEP_LOCAL_MANUAL** | replay run raw output；与 [logs/historical_training/03_fresh_replay/](logs/historical_training/03_fresh_replay/) 同形态但**未** tracked；同期 markdown summary `three_system_replay_summary.md` 已在目录内可读 | 14K 加 `.gitignore` pattern；本地保留 raw；如要保留 summary 进 repo，**单独**走 ARCHIVE_TRACKED_DOC_ONLY commit（仅 commit `three_system_replay_summary.md`） | ✅ 是 |
| `logs/historical_training/three_system_w4_2024_08_2025_12/` (~1.2M, 10 文件) | 同上 | 同形态；含 `validation_ready_manifest.json` | 同上 | ✅ 是 |
| `logs/historical_training/three_system_w4_smoke_2024_08_05_2024_08_09/` (~48K, 10 文件) | 同上 | smoke 子集 | 同上 | ✅ 是 |
| `logs/regime_validation/` (~2.0M, 3 子目录 × 4 文件) | **IGNORE_BY_GITIGNORE** + **KEEP_LOCAL_MANUAL** | continuous_smoothing v1/v2 离线诊断输出；属于 14I §7 KEEP_FROZEN_DIAGNOSTIC raw evidence；3R-3 / 3R-3.3 record 已在 `tasks/` / `records/` 写过分析 | 14K 加 `.gitignore` pattern；本地保留 raw | ✅ 是 |
| `logs/prediction_log.jsonl`（worktree 内 ~15K） | **IGNORE_BY_GITIGNORE** + **KEEP_LOCAL_MANUAL** | standing 预测日志；每次 `run_predict` append 一行；不属于 commit-worthy 历史 evidence | 14K 加 `.gitignore` pattern；本地保留 | ✅ 是（轻确认） |

### 5.2 总建议

- **不**把 raw replay / regime validation 输出提交进 repo
- 历史已有的 4 套 tracked log（`03_fresh_replay/` / `exclusion_action_validation_2e*/` /
  `technical_features/...`）**保持 tracked**，作为 contract evidence
- 任何想保留的 markdown summary 走**单独**的
  `archive(record): keep summary for <run_name>` commit；**只**commit
  markdown，不 commit `.csv` / `.json` / `.jsonl` / `_run.log`
- 4 个 untracked 子目录 + `prediction_log.jsonl` 全部归 §11 Step 14K（gitignore-only commit）

---

## 6. DB backup artifacts 计划

### 6.1 逐项

| # | path | size | category | reason | recommended handling |
|---|---|---|---|---|---|
| 1 | `avgo_agent.db.backup_pre_2099_hygiene_20260503_160409` | 1.7M | KEEP_LOCAL_MANUAL → MOVE_OUTSIDE_REPO 长期 | DB cleanup 前的 hygiene 快照；`avgo_agent.db` 自己已经 ignored 但 backup 没有 | 14K 加 `avgo_agent.db.backup_*` pattern |
| 2 | `avgo_agent.db.backup_pre_3a3_20260504_013453` | 4.7M | 同上 | 3a3 阶段前 | 同上 |
| 3 | `avgo_agent.db.backup_pre_3a4_20260504_023331` | 7.6M | 同上 | 3a4 阶段前 | 同上 |
| 4 | `avgo_agent.db.backup_pre_4c3_rewrite_20260503_235604` | 2.4M | 同上 | 4c3 rewrite 前 | 同上 |
| 5 | `avgo_agent.db.backup_pre_replay_130_20260504_003707` | 2.4M | 同上 | replay_130 前 | 同上 |
| 6 | `avgo_agent.db.backup_pre_replay_30_20260503_162636` | 1.7M | 同上 | replay_30 前 | 同上 |
| 7 | `avgo_agent.db.backup_step_2c_2_6` | 1.6M | 同上 | Step 2c 阶段 | 同上 |

总大小：~22 MB。

### 6.2 总建议

- **KEEP_LOCAL_MANUAL** 短期（4 周内的回滚/审计需要时直接用）
- **MOVE_OUTSIDE_REPO** 长期（建议移到 `~/avgo_local_backups/db/`）
- **不** commit
- **不** delete without user confirmation
- 14K 在 `.gitignore` 加 `avgo_agent.db.backup_*` pattern 防再生
- 任何 delete 需要：(a) 用户显式列出哪些可删；(b) 单独 `chore(cleanup):
  delete obsolete db backup <name>` commit（删除本地文件，无 git 改动）

---

## 7. `.claude/` artifacts 计划

### 7.1 `.claude/worktrees/`

| 项 | 值 |
|---|---|
| 内容 | 26 个 worktree 子目录（claude session 缓存） |
| 总大小 | ~390 MB |
| category | **IGNORE_BY_GITIGNORE** + **DELETE_CANDIDATE_USER_CONFIRM** |
| reason | claude harness 自动管理；worktree 完成后理论上自动清理，但在意外终止 / 长会话场景下会累积。`.claude/worktrees/` 中可能仍有 active session 在用 |
| recommended handling | 14K 加 `.gitignore` pattern；用户**单独**确认哪些可删；活跃 session 期间**不**删 |
| user confirmation needed? | ✅ 是（**强**确认；可能影响 active claude 会话） |

### 7.2 `.claude/handoffs/task_089_post_pr_cleanup.md`

| 项 | 值 |
|---|---|
| size | 2.9 KB |
| mtime | 2026-04-28 |
| 同目录 tracked handoff 数量 | 多个（task_084/085/086/087/090/092/094/096/100/103/111 等的 builder/tester handoff 已 tracked） |
| category | **UNKNOWN_REVIEW_REQUIRED** → 倾向 **ARCHIVE_TRACKED_DOC_ONLY** |
| reason | 单独 untracked 的 handoff 文件；但同目录其它 task handoff 是 tracked。可能是漏 commit / 已废弃 / 临时草稿 |
| recommended handling | 14L 阶段**只读** review 文件内容后再决定：(a) tracked → 单独 `docs(handoffs): track task_089 post pr cleanup handoff` commit；(b) 已废弃 → DELETE_CANDIDATE_USER_CONFIRM；(c) 不属 repo → MOVE_OUTSIDE_REPO |
| user confirmation needed? | ✅ 是 |

> ⚠ **不**整体 `.gitignore .claude/handoffs/`——同目录 tracked handoff 数量
> 多，整体 ignore 会让未来新 handoff 默认不可见，违反 `.claude/CLAUDE.md`
> "Handoff system" 约定。

### 7.3 其他 `.claude/` 项

`.claude/agents/`、`.claude/skills/`、`.claude/CLAUDE.md`、`.claude/CHECKLIST.md`、
`.claude/PROJECT_STATUS.md`、`.claude/TASK_TEMPLATE.md` 全部 tracked，**不**在
本节范围；不动。

---

## 8. `agent_loop.py` 计划

| 项 | 值 |
|---|---|
| path | `agent_loop.py`（root） |
| size | 932 B |
| mtime | 2026-05-02 |
| category | **UNKNOWN_REVIEW_REQUIRED** → 候选 **MOVE_OUTSIDE_REPO** 或 **DELETE_CANDIDATE_USER_CONFIRM** |
| reason | root level untracked Python；不在 [scripts/check.sh](scripts/check.sh) 的 py_compile 列表；不在 9 个 negative-import 测试的 `forbidden_modules` 中（即不是被防御的 v1 stub）；可能是本地 scratch / experimental agent driver |
| recommended handling | 14L **只读** inspection 后决定：<br>(a) experimental agent code 待整合 → tracked + 加 py_compile + active boundary test → 不在 14 系列范围，留待**独立 feature task** 决定<br>(b) local scratch / 已废弃 → MOVE_OUTSIDE_REPO（移到 `~/avgo_local_scripts/`）或 DELETE_CANDIDATE_USER_CONFIRM<br>(c) 临时实验仍在用 → 加入 `.gitignore`（**仅** `agent_loop.py` 这一行；**不**整个 `*.py` ignore） |
| user confirmation needed? | ✅ 是 |

> ⚠ 本轮**不** `cat agent_loop.py`；只读 size / mtime。14L 阶段才允许 read。
> 不在 14J 直接修改任何 .gitignore / 文件。

---

## 9. 推荐 `.gitignore` 后续计划（Step 14K 范围）

> **14K 是 `.gitignore`-only commit**：只改 `.gitignore`，不 add / 不删
> 文件 / 不 commit raw artifacts。

### 9.1 14K 推荐 patch（仅推荐，**不**在 14J 实施）

```diff
 __pycache__/
 *.pyc
 .DS_Store

 data/
 enriched_data/
 coded_data/
 match_results/
 stats_results/
 .venv/
 avgo_agent.db
+avgo_agent.db.backup_*
 snapshots/
 .env
 !.env.example
 .tmp_test_env/
 .DS_Store
+
+# untracked replay / regime validation raw outputs
+# (the tracked sets in logs/historical_training/03_fresh_replay/,
+#  logs/historical_training/exclusion_action_validation_2e*,
+#  logs/technical_features/ stay tracked)
+logs/prediction_log.jsonl
+logs/historical_training/three_system_1005/
+logs/historical_training/three_system_w4_2024_08_2025_12/
+logs/historical_training/three_system_w4_smoke_2024_08_05_2024_08_09/
+logs/regime_validation/
+
+# claude harness worktree caches
+.claude/worktrees/
```

### 9.2 14K 不包含项

- ❌ `agent_loop.py`：需要 14L 决定（用户先确认）
- ❌ `.claude/handoffs/`：整目录 ignore 会破坏 handoff workflow；需 14L review
- ❌ `.claude/handoffs/task_089_post_pr_cleanup.md`：单文件 ignore 不合
  handoff 系统语义；改用 tracked / move / delete 决策
- ❌ 不一刀切 `logs/`：会漏掉 4 套 tracked log evidence

### 9.3 14K 实施前置条件

1. 用户**显式**确认 §9.1 patch 的 6 行新 pattern
2. 14K commit message 建议：`chore(gitignore): cover local db backups, prediction log, replay raw outputs, claude worktrees`
3. 单 commit；不顺手 `git rm` / `mv` 任何文件
4. 入 main 后**立刻**跑 `git status` 确认上述 untracked 项都被 ignored，
   且没有意外 ignore 任何 tracked 文件（`git status --ignored` 验证）

---

## 10. 禁止事项

未来 14K / 14L / 14M+ 实施期间**绝对**不允许：

1. ❌ commit raw `.csv` / `.json` / `.jsonl` / `_run.log` 进 `logs/historical_training/three_system_*` 或 `logs/regime_validation/`
2. ❌ commit 任何 `avgo_agent.db.backup_*` 字节
3. ❌ 不经用户确认 delete 任何 DB backup
4. ❌ 不经用户确认 delete `.claude/worktrees/` 任何 worktree
5. ❌ 不经用户确认 move 任何 artifact 到 repo 外
6. ❌ 把 `agent_loop.py` 直接 `git add` 进 main
7. ❌ 把 `task_089_post_pr_cleanup.md` 直接 `git add` 进 main 而**不**先 14L review
8. ❌ 一刀切 `logs/` ignore（会漏 4 套 tracked log evidence）
9. ❌ 一刀切 `.claude/handoffs/` ignore（破坏 handoff workflow）
10. ❌ 把 14K（gitignore）和 14L（content review）和 14M（实际 move/delete）混在一个 commit
11. ❌ 借机进入 3R-5 / 3R-6
12. ❌ 借机改 `.claude/CLAUDE.md` / `tasks/STATUS.md` 中的 hard rules

---

## 11. 推荐执行顺序

| Step | 类型 | 范围 | 用户确认强度 |
|---|---|---|---|
| **14J**（本记录） | plan | local artifact 分类 + handling 推荐 | n/a（plan-only） |
| **14K** | gitignore-only commit | 加 §9.1 patch 6 行 pattern | 必需 |
| **14L** | read-only review | 14L-a: `cat agent_loop.py`；14L-b: `cat .claude/handoffs/task_089_post_pr_cleanup.md`；只读，写**审阅记录** `tasks/record_14l_*` | 弱 |
| **14M** | user-confirmed move/delete | 按 14L 结论分项独立 commit / 本地操作（每项前用户显式同意） | 强（每项） |
| **Step 15** | regression-after-cleanup signoff | 14J–14M 完成后跑 full pytest + scripts/check.sh + 9 个 negative-import suite + 12E X1..X5 boundary suite + 4 套 tracked log evidence 路径 sanity 检查 | n/a（结果驱动） |

---

## 12. 是否允许现在处理 artifacts

> **NO.**

本轮**只**写计划。任何实际处理：

- 必须在 14K（gitignore）/ 14L（read review）/ 14M（move/delete）阶段完成
- 每个分类项**单独**用户确认
- 每项**单独** commit
- **不**在 14J commit 中混入实施动作

---

## 13. 是否允许进入 3R-5 / 3R-6

> **NO.**

理由（与 14I §10 一致 + 14J 新增）：

1. §2 的 15 项 local artifacts 全部仍然 untracked / 未处理（14J 是计划，
   不是实施）
2. 14K / 14L / 14M 都还没起步；blast radius 仍未收敛
3. `run_predict` 默认迁移到 V2 仍未走 launch review
4. CLAUDE.md / `.claude/CLAUDE.md` hard rules 第 1 / 5 / 6 条不允许 LLM
   决定股票方向、不允许 promotion 自动放行；3R-5 / 3R-6 触碰这些边界
5. 12E-X1..X5 boundary tests 永久封禁 trading / hard / forced / promotion /
   mutation surface

---

## 14. 严守边界

本轮**只写 local artifact handling plan 文档**：

- 未改业务代码（全部 `.py` / `app.py` / `ui/*` / `services/*` / `predict.py` byte-identical 与 main `50c60f3`）
- 未改测试（`tests/test_*.py` 全部 byte-identical）
- 未新增测试
- 未删除 / 移动任何 artifact
- 未 `git add` 任何 untracked artifact
- 未修改 `.gitignore`
- 未修改 `.claude/worktrees/` / `.claude/handoffs/` 任何内容
- 未读取 `agent_loop.py` / `task_089_post_pr_cleanup.md` 内容（只读 size / mtime）
- 未打开 / 修改 DB backup 字节
- 未写 DB / 未改 DB schema
- 未跑 replay / real validation
- 未跑 full pytest（baseline 与 14F / 14I 完全一致）
- 未默认迁移 `run_predict` 到 V2
- 未启动任何 cleanup 实施
- 未进入 3R-5 / 3R-6
- 未启用 candidate / 未复活 `continuous_smoothing` / 未接 trading
- 未顺手碰 RISK-1 / RISK-2 / RISK-3 / RISK-7 / RISK-8 / RISK-9 / RISK-10

本计划的修改路径：任何对 §3 分类原则、§4 `.gitignore` 推荐、§5 / §6 / §7 /
§8 分项处理、§9 14K patch、§11 执行顺序的调整，都必须以**显式更新本文件**
的方式提出；同时检查是否需要同步更新 14A §9 / 14I §8。
