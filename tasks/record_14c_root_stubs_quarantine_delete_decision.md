# 14C记录：Root Stubs Quarantine / Delete Decision

> 本记录是 **Step 14 的第三阶段：root dead stubs quarantine vs delete 决策**。
> Step 14B audit 已入 main（`3808677`）；本轮按 14A §10.2 / 14B §11 给出
> 后续 cleanup 的方向决定。
>
> 本轮**只写 decision 文档**：未改代码、未删除文件、未移动文件、未新增 /
> 修改测试、未清理 logs / DB backup / `.claude/worktrees/`、未跑 replay /
> real validation、未写 DB / 未改 DB schema、未默认迁移 `run_predict` 到
> V2、未 commit / push、未进入 3R-5 / 3R-6、未顺手碰任何 RISK。

---

## 1. Step 14C 目的

基于 14B audit 的零 active import / 编译 / pytest 全绿证据，对三个 root
dead stub 给出 **quarantine vs delete** 的决策。

- **不**实际执行 quarantine（`git mv` 不允许）
- **不**实际执行 delete（`git rm` 不允许）
- **不**新增 / 修改 / 删除任何代码 / 测试
- **不**触碰任何历史引用（docs / negative-import 测试）
- **不**先创建 `archive/` 目录（属 14D 实施步骤）

签收依据：[tasks/record_14a_cleanup_quarantine_plan.md](tasks/record_14a_cleanup_quarantine_plan.md)
§10.2 + [tasks/record_14b_root_dead_stubs_audit.md](tasks/record_14b_root_dead_stubs_audit.md)
§9 / §11。

---

## 2. 当前证据摘要

直接复述 14B 的硬证据（未做任何新增 audit；本轮**仅**做决策）：

| file | active imports | docs refs | test refs | compile | pytest | current status |
|---|---:|---:|---:|---|---|---|
| [confidence_engine.py](confidence_engine.py)（31 行 / 608 字节） | **0** | 10（全部 docs-only：`tasks/record_08` ×4 / `record_10` ×2 / `record_12e_x5` ×2 / `step_2d_*` / `step_2f_*`） | 9 个 negative-import 测试 forbidden_modules（不 import；只断言被测模块**不**import） | ✅ `py_compile` PASS | ✅ `pytest -q` 3252 / 10 skipped / 0 failed | **QUARANTINE_CANDIDATE** |
| [contradiction_engine.py](contradiction_engine.py)（25 行 / 643 字节） | **0** | 9 全部 docs-only | 7 个 negative-import 测试 forbidden_modules | ✅ PASS | ✅ 同上 | **QUARANTINE_CANDIDATE** |
| [risk_model.py](risk_model.py)（25 行 / 569 字节） | **0** | 8 全部 docs-only | 7 个 negative-import 测试 forbidden_modules | ✅ PASS | ✅ 同上 | **QUARANTINE_CANDIDATE** |

`mtime` 一致（`May  8 09:58:33 2026`），表明三个文件自 step_1a 起未被实际编辑。
唯一非测试 / 非 docs reference 是 `services/contract_calibration_inputs.py:31`
模块 docstring 中的反向声明 "never imports `confidence_engine.py`"——**不是**
active 引用。

---

## 3. 决策选项

### 3.1 Option A：直接 `git rm`

**优点**：

- 最干净；root 目录直接清空 v1 stub 噪音
- 删除后任何"误用"的可能性归零（即使是动态 import 也找不到）
- `archive/` 目录不必出现（保持仓库结构简单）

**缺点**：

- 失去**文件本体**的本地可见性（虽然 `git log -- <file>` / `git show <sha>:<file>`
  仍可追溯；但需要 git 操作而不是直接 `cat`）
- 第一次 cleanup 选择"最激进"，回滚需要 `git revert`，对新协作者不直观
- 与 14A §3 第 1 条"先计划，后执行" / 第 7 条"不删除仍有 reference 的文件"
  的精神有张力：虽然 reference 只是 docs-only，但**全删**可能让未来读 docs
  的人困惑（"这个文件名指向哪里？"）

### 3.2 Option B：移动到 `archive/legacy/`

**优点**：

- 保留**文件本体的本地可见性**——读 docs 时可以直接 `cat archive/legacy/root_stubs/confidence_engine.py`
- 显式表示"已退役但留作历史参考"
- 不在 root 干扰 active path
- 回滚成本低（`git mv` 反向即可）；比 `git rm` 的回滚更直观
- 与 11H §11 / 14A §10 推荐的"audit → quarantine → delete"渐进路径一致
- 第一次 cleanup 选择"保守"，便于建立 cleanup pattern

**缺点**：

- repo 仍保留死代码字节（约 1.8 KB，可忽略）
- 必须确保 `archive/` 不会被无意 import（→ 不创建 `archive/__init__.py` /
  `archive/legacy/__init__.py` / `archive/legacy/root_stubs/__init__.py`）
- 需要新增 README / `_DEPRECATED.md` 标注

### 3.3 Option C：暂时不动

**优点**：

- 零风险

**缺点**：

- root 继续混乱（4 个 root-level Python 文件其中 3 个是死代码）
- cleanup 没有任何实际推进；Step 14B audit 的产出就此搁置
- 文件可能被未来贡献者误以为 active 模块

---

## 4. 推荐决策

> **推荐 Option B：quarantine to `archive/legacy/root_stubs/`，而不是直接 delete。**

理由：

1. **第一次真实 cleanup，先保守**。Step 14 共 7 个子阶段（A→G）；选 Option B
   建立"audit → quarantine → 长 stability window → 后续考虑 delete"的范式，
   后续阶段（14D / 14E / 14F / 14G）有明确模板可循
2. **三个文件虽无 active import，但与历史 contract / docs / negative-import 测试有语义关联**。
   现在直接 delete，未来读 `tasks/record_08` 等历史文档时只能从 git 历史中
   `git show` 才能复现；保留 archive 副本最便于人工审计
3. **archive 方便保留上下文**。`archive/legacy/root_stubs/_DEPRECATED.md` 可以
   显式记录"step_1a v1 stub / 11C-A 接管 confidence / 11B 接管 risk / 11C
   接管 contradiction"，把退役理由钉在文件旁
4. **比直接 `git rm` 更容易让用户理解和回滚**。如果 quarantine 后任何后续
   commit 暴露问题，`git mv` 反向即可；`git rm` 的回滚需要 `git revert`，
   且对其他工作流（rebase / cherry-pick）摩擦更大
5. **未来 stability window 后再考虑 delete**。如 §7 所述，Option A 不被
   永久排除——只是**不**在 14C/14D 阶段执行
6. **与 11H §6 / §11 一致**：cleanup commit-per-fix；archive 是首选，delete
   是 Step 14 后期 / Step 14 之后单独的小 commit

---

## 5. 推荐目标路径

实施时（**未来** Step 14D，**不**在本 14C commit 内）目标如下：

```
archive/legacy/root_stubs/
├── _DEPRECATED.md                  ← 新增
├── confidence_engine.py            ← 从 ./confidence_engine.py 移过来
├── contradiction_engine.py         ← 从 ./contradiction_engine.py 移过来
└── risk_model.py                   ← 从 ./risk_model.py 移过来
```

`archive/legacy/root_stubs/_DEPRECATED.md` 必须包含的内容（实施时由
14D commit 写入；本 14C **不**预先创建）：

- "Quarantined root v1 stubs（step_1a 时代占位）"
- "No active imports as of Step 14B（commit `3808677`）"
- "**Do not import** —— 这些文件保留**仅**作为历史审计 / docs reference 的
  本地可见副本"
- "退役 owner 映射：confidence_engine → `services/confidence_evaluator.py`（11C-A）；
  risk_model → `services/final_decision.py.risk_level`（11B）；
  contradiction_engine → `services/final_decision.py.decision_factors`
  / `services/confidence_evaluator.py` 的 conflicting evidence 通道（11B / 11C）"
- "Stability window：Step 14G 完成且 Step 13-style regression 再次全绿后，
  评估是否进入 delete（**不**在 14D 范畴）"
- "**Not** a Python package：本目录**不**含 `__init__.py`；任何 `import
  archive.legacy.root_stubs.*` 视为违规"

如果 `archive/` 目录不存在（**当前确认不存在**，见 §10），14D 实施 commit
**首次创建**，路径如上。**不**在 `archive/` / `archive/legacy/` /
`archive/legacy/root_stubs/` 任一层级新增 `__init__.py`。

---

## 6. 后续真正执行时的最低要求

> 这是 **14D（实施）** 的最低门槛，**不**是 14C 范畴；本 14C **不**执行任一项。

实施 commit 必须**仅**：

1. **`git mv`** 这 3 个 stub 到 `archive/legacy/root_stubs/`；**不**用 `cp` +
   `rm`（`git mv` 保留 history）
2. **新增** `archive/legacy/root_stubs/_DEPRECATED.md`（§5 内容）
3. **不**改业务代码（`predict.py` / `services/*.py` / `ui/*.py` / `app.py` /
   `scripts/*.py` 全部 byte-identical）
4. **不**改 tests（包括 9 个 negative-import 测试中的 `forbidden_modules`
   字符串——保留为永久防御）
5. **不**改 docs 历史引用（`tasks/record_08` / `record_10` / `record_12e_x5`
   / `step_2d_*` / `step_2f_*` 字面引用保持不变）
6. **不**改 import path（既然 active import = 0，无需改）
7. **不**新增 `__init__.py`（避免 `archive/legacy/root_stubs/` 变成 import package）

实施前 / 后必跑：

```bash
# 实施前（baseline）
git status
grep -rn "^import \(confidence_engine\|contradiction_engine\|risk_model\)\b" --include='*.py'  # → 0 hits
grep -rn "^from \(confidence_engine\|contradiction_engine\|risk_model\) import" --include='*.py'  # → 0 hits
python3 -m py_compile confidence_engine.py contradiction_engine.py risk_model.py  # → exit 0
pytest -q  # → 3252 passed / 10 skipped / 0 failed

# 实施后
grep -rn "^import \(confidence_engine\|contradiction_engine\|risk_model\)\b" --include='*.py'  # → 0 hits
grep -rn "^from \(confidence_engine\|contradiction_engine\|risk_model\) import" --include='*.py'  # → 0 hits
python3 -m py_compile archive/legacy/root_stubs/confidence_engine.py archive/legacy/root_stubs/contradiction_engine.py archive/legacy/root_stubs/risk_model.py  # → exit 0
pytest -q  # 必须仍 3252 passed / 0 failed
bash scripts/check.sh  # → "All compile checks passed."（注意 check.sh 不再 import 这 3 个文件，因为它本来就没有；其它 20 个 module 应仍 PASS）
```

任一步 `pytest` 不全绿 → 立即 `git revert <14D commit>`；**不**手动 patch、
**不**改 tests 来迁就、**不** `--amend` / `rebase -i`。

实施 commit message 建议：

```
chore(cleanup): quarantine root v1 stubs to archive/legacy/root_stubs

Co-Authored-By: ...
```

> 注意 commit message 用 `chore(cleanup):` 而**非** `docs(cleanup):` 或
> `feat(cleanup):`：`chore` 准确表达"仓库结构调整 / 不改业务"，符合 11H §6
> 的 commit-per-fix 语义。

---

## 7. 为什么暂不 delete

虽然 14B 的 zero active import + zero attribute access 在技术上**支持** Option A
（`git rm`），但本 14C 推荐先走 Option B（quarantine）。原因：

1. **用户希望稳健推进**。Step 14 是修完 boundary 后的清理阶段；第一批
   cleanup 文件直接 delete 节奏过快
2. **archive 比 git history 更可审计**。git history 需要 `git log -- <file>`
   + `git show <sha>:<file>`，对非 git-native 用户摩擦大；archive 副本
   `cat archive/legacy/root_stubs/<file>` 直接可读
3. **后续 delete 可以在 stability window 后单独做**。建议的 stability window：
   - Step 14D 实施（quarantine）入 main
   - Step 14E（test fixture hygiene plan）/ 14F（local artifact handling plan）/
     14G（其它 cleanup）依次入 main
   - Step 13-style regression 再次跑一轮全绿
   - 至少 4 周不出现需要回查 archive 文件的事件
   - **然后**才考虑独立的 `chore(cleanup): delete archive/legacy/root_stubs/<file>` 小 commit
4. **保留 `_DEPRECATED.md` 比裸删更具教育价值**。未来其它"v1 stub-style"
   cleanup 可以复用同一 pattern

> Option A 并未被永久排除——只是**不**在 14C/14D 范畴。

---

## 8. 不应修改的引用

后续 quarantine 实施（14D）**绝不**允许修改以下引用：

1. **06 / 07 / 08 / 09 / 10 / 11A–11H / 12E-X5 / 13 / 14A / 14B 历史 docs**
   中字面提到 `confidence_engine.py` / `contradiction_engine.py` /
   `risk_model.py` 的位置——这些是历史判断证据，**不**是 active dependency
2. **9 个 negative-import 测试**中 `forbidden_modules` 集合内的
   `"confidence_engine"` / `"contradiction_engine"` / `"risk_model"` 字符串
   ——保留为**永久防御**（即使文件已 quarantine，未来如果有谁想"恢复" import，
   测试仍会拦下）
3. **本 14C 文档 + 14B 文档**中复述这些字符串的所有段落
4. **`record_10` / `record_12e_x5` / `record_14a` / `record_14b`** 中标记这
   三个文件的清单条目（保留追溯链）
5. `services/contract_calibration_inputs.py:31` 模块 docstring 的
   "never imports `confidence_engine.py`" 文本（反向声明，不是 import）

修改以上任何一项 = **违反 14C 决策 + 11H §6.2 commit-per-fix 不允许混入**。

---

## 9. 回滚策略

如果 14D quarantine commit 入 main 后**任何**测试失败 / `py_compile` 失败 /
`scripts/check.sh` 失败 / hook 失败：

1. **立即** `git revert <14D commit hash>`（**不** `--amend`，**不** `rebase -i`）
2. **不**手动 patch quarantine 后的代码
3. **不**改 tests 来迁就 archive 路径
4. **不**借机修改其他文件
5. revert commit 入 main 后，回到本 14C 文档**显式更新**评估，决定：
   (a) 修订 14C 决策（例如改为 Option C 暂不动）；
   (b) 保留 Option B 但调整目标路径 / `_DEPRECATED.md` 内容；
   (c) 进入 root cause 分析（例如发现某个动态 import 漏检）

如果 revert 后仍发现根因（例如某 hidden test 真的依赖 root stub），必须把
该信息显式补回到 14B audit 文档（`record_14b_*.md` §4），不能让证据丢失。

---

## 10. 是否允许现在执行 cleanup

> **NO**，本轮 14C **只**做 decision document。
>
> 真正执行（`git mv` + 新增 `_DEPRECATED.md`）是 **14D** 的范畴，必须由用户
> 单独触发。

当前 worktree 状态确认：

- `archive/` 目录**不**存在（实施时 14D commit 首次创建）
- 三个 root stub 仍在 root，byte-identical 与 main `3808677`
- 9 个 negative-import 测试 byte-identical 与 main
- 所有 `tasks/record_*.md` 引用 byte-identical 与 main

---

## 11. 是否允许进入 3R-5 / 3R-6

> **NO.**

理由（按 11H §12 / 13 §9 / 14A §14 / 14B §10）：

1. ❌ cleanup 尚未实际完成（14B audit + 14C decision 都仍是文档）
2. ❌ default V2 migration 未独立 launch review
3. ❌ trading / hard / forced / production_promotion 仍**永久禁止**
4. ❌ 进入 3R-5 / 3R-6 必须**另开** launch review 文档（不在 06–14 范畴）

---

## 12. 推荐下一步

> **Step 14D — root v1 stubs quarantine implementation**

**前提**（必须全部满足才允许 14D 启动）：

1. 用户**明确**同意把这 3 个文件移到 `archive/legacy/root_stubs/`
2. 用户**明确**同意新增 `archive/legacy/root_stubs/_DEPRECATED.md`
3. 单独 commit；**不**与其他 cleanup 混合
4. commit 前后跑 `pytest -q` 全绿（3252 / 0 failed）+ `bash scripts/check.sh` PASS
5. commit message：`chore(cleanup): quarantine root v1 stubs to archive/legacy/root_stubs`

**不**推荐：

- 跳过 14D 直接进 14E（test fixture hygiene plan）
- 在 14D commit 内顺手做 14E / 14F / 14G 中的任何事
- 在 14D commit 内修改 9 个 negative-import 测试 / 9 份历史 docs
- 直接进 Option A delete 而跳过 Option B archive
- 进 3R-5 / 3R-6
- 默认切 V2

如果用户希望跳过 quarantine 直接 delete（Option A），必须先**显式更新本
14C 文档**改写 §4 推荐决策，再进入 14D 的 delete 实施分支。

---

## 13. 严守边界

本轮**只写 decision 文档**：

- 未改业务代码（`predict.py` / `services/predict_legacy_*` / 全部 active 文件
  byte-identical 与 main `3808677`）
- 未新增测试 / 未修改测试
- 未删除文件 / 未移动文件
- 未创建 `archive/` / `archive/legacy/` / `archive/legacy/root_stubs/` 目录
- 未新增 `_DEPRECATED.md`
- 未写 DB / 未改 DB schema
- 未跑 replay / real validation（甚至**没**跑 pytest，本 14C 不需要新数据；
  14B 的 baseline 仍当前有效）
- 未处理 untracked / DB backup / stash / `.claude/worktrees/`
- 未默认迁移 `run_predict` 到 V2
- 未启动真正 cleanup
- 未进入 3R-5 / 3R-6
- 未启用 candidate / 未复活 `continuous_smoothing` / 未接 trading
- 未顺手碰 RISK-1 / RISK-2 / RISK-3 / RISK-7 / RISK-8 / RISK-9 / RISK-10

本决策的修改路径：任何对 §3 三选项的优劣分析、§4 推荐决策（Option B）、
§5 目标路径、§6 实施最低要求、§7 暂不 delete 的理由、§8 不应修改引用、
§9 回滚策略、§10 / §11 / §12 决策的调整，都必须以**显式更新本文件**的方式
提出；同时检查是否需要同步更新 14A / 14B / 11H / 12E-X5 / 13。
