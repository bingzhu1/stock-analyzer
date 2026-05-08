# 14M记录：User-confirmed Local Artifact Handling

> 本记录是 **Step 14 的第十三阶段：execute user-confirmed Option B for the
> two remaining local untracked artifacts**。Step 14L（[record_14l_handoff_agent_loop_review.md](record_14l_handoff_agent_loop_review.md)）
> 完成 read-only review 后，用户在 14L §8.1 / §8.2 决策菜单中明确选择
> **B 方案**：
>
> - `.claude/handoffs/task_089_post_pr_cleanup.md`：**A2 KEEP_LOCAL_MANUAL**
>   （本地保留，**不**处理）
> - `agent_loop.py`：**B1 MOVE_OUTSIDE_REPO**（移出 repo 到
>   `~/avgo_local_scripts/agent_loop.py`）
>
> 本轮仅按 Option B 执行 1 项 file system 操作（`mv agent_loop.py`），
> 1 项目录创建（`mkdir -p ~/avgo_local_scripts`）。其余全部不动：
> 未改业务代码、未新增测试、未删 tracked 文件、未移 tracked 文件、
> 未处理 logs / DB backup / `.claude/worktrees/` / handoff、未改
> `.gitignore`、未跑 replay / validation、未写 DB / 未改 DB schema、
> 未默认迁移 `run_predict` 到 V2、未 commit / push、未进入 3R-5 / 3R-6。

---

## 1. Step 14M 目的

按 14L 用户确认的 Option B 处理剩余 2 项 untracked。

仅 2 项动作：

1. `mkdir -p ~/avgo_local_scripts`
2. `mv /Users/may/Desktop/stock-analyzer-main/agent_loop.py ~/avgo_local_scripts/agent_loop.py`

`.claude/handoffs/task_089_post_pr_cleanup.md` 保持 untouched（A2）。

明确**不**做的事：

- 不 `git add` / `git rm` / 删除 任何文件
- 不修改 `.gitignore`
- 不修改 handoff 字节
- 不修改业务代码 / 测试
- 不 commit / push（本轮只生成本文档作为 deliverable，由用户审阅后决定）
- 不进入 3R-5 / 3R-6

签收依据：[record_14j_local_artifact_handling_plan.md](record_14j_local_artifact_handling_plan.md) §8 +
[record_14l_handoff_agent_loop_review.md](record_14l_handoff_agent_loop_review.md) §6.1（A2）/ §6.2（B1）/ §8.1 / §8.2。

---

## 2. 用户确认方案

| Artifact | 14L 候选 | 用户选择 | 类别 | 动作 |
|---|---|---|---|---|
| `.claude/handoffs/task_089_post_pr_cleanup.md` | A1 / A2 / A3 / A4 | **A2** | KEEP_LOCAL_MANUAL | 无（保持 untracked / 字节不动） |
| `agent_loop.py` | B1 / B2 / B3 / B4 / B5 | **B1** | MOVE_OUTSIDE_REPO | `mv` 到 `~/avgo_local_scripts/agent_loop.py` |

> 用户输入原文要点：
> - "继续本地保留，不处理"（→ handoff A2）
> - "移出 repo，建议移动到 `~/avgo_local_scripts/`"（→ agent_loop.py B1）

> 14L §6.1 / §6.2 中**强反对**项（A4 直接删除 / B5 直接 add as-is）均**未**被
> 用户选中。

---

## 3. `agent_loop.py` 处理结果

### 3.1 执行命令

```bash
mkdir -p ~/avgo_local_scripts
mv /Users/may/Desktop/stock-analyzer-main/agent_loop.py ~/avgo_local_scripts/agent_loop.py
```

`mkdir -p` 创建目标父目录（先前不存在，已确认）；`mv` 同盘内重命名，
保留 byte / size / mtime / mode。

### 3.2 文件 metadata 对照

| 维度 | 移动前（main worktree） | 移动后（user home） |
|---|---|---|
| path | `/Users/may/Desktop/stock-analyzer-main/agent_loop.py` | `/Users/may/avgo_local_scripts/agent_loop.py` |
| size | 932 B | 932 B（**unchanged**） |
| mtime | 2026-05-02 14:17:29 | 2026-05-02 14:17:29（**unchanged**） |
| mode | `-rw-r--r--` | `-rw-r--r--`（**unchanged**） |
| repo root 是否仍存在 | ✅ 是 | ❌ 否（移走） |
| `git status` 是否仍列出 | ✅ untracked | ❌ 不再出现 |

### 3.3 git side effects

| 项 | 评估 |
|---|---|
| 是否 commit 了 `agent_loop.py` 的内容 | ❌ 否。文件本来就 untracked；`mv` 只动文件系统，不动 git index |
| 是否进 main history | ❌ 否。`agent_loop.py` 字节**从未**进入 git history（不在 `git log -- agent_loop.py` 任何 commit 里），现在依然如此 |
| 是否触发 `.gitignore` 更新 | ❌ 否。文件已不在 repo，无需 ignore pattern |
| 是否触发 reference 失效 | ❌ 否。14L §5.2 已确认无任何 tracked `.py` import `agent_loop`；14L §5.3 / §5.4 已确认所有 `.md` 引用都是 "untracked landmark" 或 "Step 14 二次审查" 性质，move 后语义仍成立（"已完成 14M 处理：移到 repo 外"） |
| 是否影响 `scripts/check.sh` py_compile | ❌ 否。它本来就不在 py_compile 列表（14L §4.1） |
| 是否影响 9 个 negative-import 测试 / 12E X1..X5 boundary suite | ❌ 否。它本来就不在 forbidden_modules / surface 任一（14L §4.1） |
| 是否影响 streamlit app / `run_predict` / `run_projection_v2` / scanner / matcher / encoder | ❌ 否。无 import 关系 |

### 3.4 内容是否丢失

❌ 否。`mv` 是文件系统重命名，**byte-identical** 保留。可在
`~/avgo_local_scripts/agent_loop.py` 直接 `cat` / 编辑 / 运行。

如果用户未来决定重新引入 agent loop 概念（14L §6.2 B4）：

- **不**直接把 `~/avgo_local_scripts/agent_loop.py` 拷回 repo root
- **应该**走独立 feature task：plan → builder → reviewer → tester
- 新逻辑放 `services/`（hard rule 第 4 条），不放 root level
- 同步加 py_compile 列表 + 9 个 negative-import + 12E X1..X5 surface 检查

---

## 4. handoff 处理结果

### 4.1 字节 / 状态 verify

| 项 | 值 |
|---|---|
| path | `.claude/handoffs/task_089_post_pr_cleanup.md` |
| size | 2966 B（≈ 2.9 KB；与 14L §3.1 + STATUS.md 中 task 092~110 closeout landmark 全部一致） |
| mtime | 2026-04-28 10:34:37（与 14L §3.1 一致；本轮**未**触碰） |
| `git status` | `?? .claude/handoffs/task_089_post_pr_cleanup.md` —— **untracked**（与 14L 之前一致） |

### 4.2 本轮**未**做的动作

| 动作 | 是否做 |
|---|---|
| `git add` | ❌ |
| `git rm` / `rm` | ❌ |
| `mv` / `cp` 出 `.claude/handoffs/` 目录 | ❌ |
| 字节修改 / 编辑 | ❌ |
| 加入 `.gitignore` 单文件 pattern | ❌ |
| 在 `archive/handoffs/` 创建副本 | ❌（A2 路径不需要） |

### 4.3 STATUS.md landmark 是否仍生效

✅ 是。Task 092 / 094 / 096 / 100 / 110 / 104 等 closeout 段中
"untouched protected file"、"stat identical: 2966 B, mtime Apr 28 10:34"
全部仍然真实（本轮 14M 未触碰 handoff，stat 完全没变）。无需同步更新
STATUS.md。

### 4.4 后续

如未来用户改主意（A2 → A1 / A3 / A4），**单独**走 14M-1 用户确认 +
单独 commit / 本地操作 + 同步更新 STATUS.md landmark；**不**借此 commit
混入其他动作。

---

## 5. git status 结果

### 5.1 main worktree（移动 + 文档生成后）

```
?? .claude/handoffs/task_089_post_pr_cleanup.md
```

只剩 handoff 一项 untracked（按 A2 预期保留）。

### 5.2 main worktree `git status --ignored --short` 摘要

| 类别 | 项 | 是否仍 ignored |
|---|---|---|
| `.claude/worktrees/` | 1 项 | ✅ |
| `avgo_agent.db.backup_*` | 7 项（pre_2099_hygiene / pre_3a3 / pre_3a4 / pre_4c3_rewrite / pre_replay_130 / pre_replay_30 / step_2c_2_6） | ✅ |
| `logs/historical_training/three_system_*` | 3 项（1005 / w4_2024_08_2025_12 / w4_smoke_*） | ✅ |
| `logs/regime_validation/` | 1 项 | ✅ |
| stdlib ignores（`__pycache__/` / `.pytest_cache/` / `.venv/` / `.DS_Store` / `data/` / `coded_data/` / `enriched_data/` / `match_results/` / `stats_results/` / `snapshots/` / `dotenv/` / `streamlit/` / `avgo_agent.db`） | ✅ 全部 |

14K 加入的 6 类新 ignore pattern 全部仍生效。`.gitignore` 字节未动。

### 5.3 当前 worktree（`eager-blackwell-e5e9de`）

```
?? tasks/record_14l_handoff_agent_loop_review.md
?? tasks/record_14m_user_confirmed_local_artifact_handling.md
```

两个 14 系列 record 仍 untracked（14L 上轮生成 + 14M 本轮生成）。
本轮**不** commit / push。

### 5.4 移动前后 diff

| 维度 | 移动前 main | 移动后 main |
|---|---|---|
| `git status --short` 行数 | 2（handoff + agent_loop.py） | 1（仅 handoff） |
| `git diff` | 无 staged / unstaged 改动 | 无（仍空） |
| `git log --oneline -1` | `66dafd8 chore(gitignore): cover ...` | `66dafd8`（未 commit） |
| repo 字节是否变化 | — | tracked 文件全部 byte-identical |

---

## 6. 不允许事项确认

本轮 14M **绝对没**做的事（与 14J §10 / 14L §7 / hard rules 一致）：

1. ❌ 未处理 logs（`logs/prediction_log.jsonl` / `logs/historical_training/three_system_*` / `logs/regime_validation/` 全部仅靠 14K `.gitignore` ignored，本轮未碰字节）
2. ❌ 未处理 DB backup（7 个 `avgo_agent.db.backup_*` 全部仅靠 14K ignored，本轮未碰）
3. ❌ 未处理 `.claude/worktrees/`
4. ❌ 未处理 `.claude/handoffs/task_089_post_pr_cleanup.md`（A2 keep local）
5. ❌ 未改 `.gitignore`（仍是 14K commit `66dafd8` 状态）
6. ❌ 未改业务代码（`.py` / `app.py` / `ui/*` / `services/*` / `predict.py` 全部 byte-identical 与 main `66dafd8`）
7. ❌ 未改测试（`tests/test_*.py` 全部 byte-identical）
8. ❌ 未新增测试
9. ❌ 未删除 tracked 文件
10. ❌ 未移动 tracked 文件（`agent_loop.py` 是 untracked，`mv` 不动 git index）
11. ❌ 未跑 replay / real validation
12. ❌ 未跑 full pytest（baseline 与 14F / 14I / 14K 完全一致）
13. ❌ 未写 DB / 未改 DB schema
14. ❌ 未默认迁移 `run_predict` 到 V2
15. ❌ 未启用 candidate / 未复活 `continuous_smoothing` / 未接 trading
16. ❌ 未进入 3R-5 / 3R-6
17. ❌ 未顺手碰 RISK-1 / RISK-2 / RISK-3 / RISK-7 / RISK-8 / RISK-9 / RISK-10
18. ❌ 未修改 14A / 14B / 14C / 14E / 14G / 14H / 14I / 14J / 14K / 14L 任一已 commit / 已写记录的 byte
19. ❌ 未修改 `.claude/CLAUDE.md` / `tasks/STATUS.md` 任一 hard rule / landmark
20. ❌ 未 commit / 未 push（本轮纯文件系统操作 + 文档生成；commit 决定留给用户）

---

## 7. 推荐下一步

> **Step 15：cleanup regression / final status signoff**

### 7.1 推荐原因

- §2 的 15 项 local untracked artifacts 处理收敛到位：
  - 14K：13 项（4 logs 子目录 + 7 DB backups + `.claude/worktrees/` + `logs/prediction_log.jsonl`）通过 `.gitignore` 转 ignored
  - 14M-本轮：1 项（`agent_loop.py`）move 到 `~/avgo_local_scripts/`
  - 14M-handoff（A2）：1 项（`.claude/handoffs/task_089_post_pr_cleanup.md`）保持 untracked landmark
- main worktree `git status --short` 现在只剩 1 项 deliberate-local-note（handoff）；噪音几乎全部收敛
- 14 系列剩余子步全部完成；可以做最终 status + regression checkpoint

### 7.2 Step 15 范围（建议）

与 14J §11 + 14L §8.4 一致：

1. full pytest（baseline 与 14F / 14I / 14K / 14L / 14M 完全一致：3256 passed / 0 failed）
2. `bash scripts/check.sh`
3. 9 个 negative-import suite
4. 12E X1..X5 boundary suite
5. 4 套 tracked log evidence 路径 sanity 检查（`logs/historical_training/03_fresh_replay/` / `exclusion_action_validation_2e*` / `logs/technical_features/`）
6. `git status --ignored --short` 确认 14K 加入的 7 类 ignore pattern 仍生效
7. main worktree `git status --short` 仅 1 项（handoff）的最终 snapshot
8. 写 `tasks/record_15_*` final signoff

### 7.3 Step 15 不允许事项

- 不进入 3R-5 / 3R-6
- 不默认迁移 `run_predict` 到 V2
- 不接 trading
- 不修改 hard rules
- 不修改 14A~14M 已 commit / 已写记录的 byte（除非 Step 15 发现 bug 需补丁；那种情况下走单独 record）
- 不混入新 feature 工作

### 7.4 14M 之后、Step 15 之前的可选 commit 顺序

| 顺序 | commit | 范围 | 是否本轮做 |
|---|---|---|---|
| Optional 1 | `docs(cleanup): record 14l handoff & agent_loop.py read-only review` | 仅 `tasks/record_14l_*.md` | ❌ 否（用户控制时机） |
| Optional 2 | `docs(cleanup): record 14m user-confirmed local artifact handling` | 仅 `tasks/record_14m_*.md` | ❌ 否（本轮指令明确不 commit） |
| Optional 3 | `chore(cleanup): step 15 regression-after-cleanup signoff` | 新 record + 必要时 `tasks/STATUS.md` 更新 | Step 15 |

> 14L 和 14M 文档可以分别独立 commit，也可以打包成 1 个 `docs(cleanup): record 14l/14m local artifact follow-up` commit；由用户决定。本轮**不**做。

---

## 8. 严守边界

本轮 14M 范围：

- **唯一 file system 写**：`mkdir -p ~/avgo_local_scripts` + `mv agent_loop.py ~/avgo_local_scripts/agent_loop.py`
- **唯一新文档**：`tasks/record_14m_user_confirmed_local_artifact_handling.md`（本文件；未 commit）
- 未改业务代码 / 测试 / `.gitignore` / `.claude/CLAUDE.md` / `tasks/STATUS.md` / `app.py` / `ui/*` / `services/*` / `predict.py`
- 未触碰 handoff 字节 / DB backup 字节 / logs 字节 / `.claude/worktrees/`
- 未跑 pytest / replay / validation
- 未 commit / 未 push
- 未进入 3R-5 / 3R-6 / 默认 V2 / trading / promotion / forced / hard / mutation surface
- 未触碰 RISK-1..3 / RISK-7..10
- 未修改 14A~14L 已写 record byte

后续修改路径：任何对 §3 / §4 / §6 / §7 内容的调整，都必须**显式更新本
文件**；同时检查是否需要同步更新 14J §8 / 14L §6 / §8。
