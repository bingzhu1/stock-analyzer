# 14B记录：Root Dead Stubs Audit

> 本记录是 **Step 14 的第二阶段：root-level dead stubs 审计**。Step 14A
> cleanup / quarantine plan 已入 main（`afb006b`）；本轮按 14A §10.1 执行
> audit-only 步骤。
>
> 本轮**只写审计文档**：未改代码、未删除文件、未移动文件、未新增 / 修改测试、
> 未清理 logs / DB backup / `.claude/worktrees/`、未跑 replay / real validation、
> 未写 DB / 未改 DB schema、未默认迁移 `run_predict` 到 V2、未 commit / push、
> 未进入 3R-5 / 3R-6、未顺手碰任何 RISK。

---

## 1. Step 14B 目的

只审计 **root-level dead stubs**。**不**删除、**不**移动、**不**改代码。

目标：

1. 为 Step 14C 的 quarantine / delete 决策提供完整证据
2. 锁定每个 stub 的 (a) 当前 git 跟踪状态、(b) 字节 / 行数 / mtime、
   (c) 全仓 import 与 reference 计数、(d) 编译结果、(e) 测试影响面
3. 顺带审计 14A §7.4 (`.claude/legacy_tasks/`) 和 14A §7.5
   (`records/` vs `tasks/`)
4. **不**给出 delete 决定（必须留到 14C）；**仅**给推荐分类

签收依据：[tasks/record_14a_cleanup_quarantine_plan.md](tasks/record_14a_cleanup_quarantine_plan.md)
§10.1 / §15。

---

## 2. 当前 main 状态

| 项 | 状态 |
|---|---|
| main 最新 commit | **`afb006b docs(cleanup): record 14a cleanup quarantine plan`** |
| Step 12 / 12E-X1–X5 / 13 / 14A | ✅ 全部入 main |
| 本轮 cleanup 实际操作 | ❌ 不允许（仅 audit） |
| 本轮 local artifact 处理 | ❌ 不允许（属 14F） |
| `run_predict` 默认路径仍 legacy / `v2_payload` 仍 explicit opt-in | ✅ 锁定 |

---

## 3. 审计对象（root-level v1 stubs）

### 3.1 速览表

| path | tracked? | size / lines / bytes | mtime | module purpose（依据文件本体内容） | current classification |
|---|---|---|---|---|---|
| [confidence_engine.py](confidence_engine.py) | ✅ tracked（`git ls-files` 命中） | 31 行 / 608 字节 | `May  8 09:58:33 2026` | step_1a v1 stub：`evaluate_confidence(base_confidence, top1_margin, is_tail, has_conflict) -> str`；按 `is_tail` / `top1_margin` / `has_conflict` 把 base_confidence 降级到 medium | QUARANTINE_CANDIDATE |
| [contradiction_engine.py](contradiction_engine.py) | ✅ tracked | 25 行 / 643 字节 | `May  8 09:58:33 2026` | step_1a v1 stub：`contradiction_score(prediction, signals) -> int`；对 `["大涨", "小涨"]` 加 `macro_bearish` / `volume_drop` / `nvda_down` / `overbought` 各 +1 | QUARANTINE_CANDIDATE |
| [risk_model.py](risk_model.py) | ✅ tracked | 25 行 / 569 字节 | `May  8 09:58:33 2026` | step_1a v1 stub：`calculate_risk_score(confidence, contradiction_count, volatility) -> float`；线性组合：`(1-conf)·0.5 + count·0.2 + vol·0.3`，封顶 1.0 | QUARANTINE_CANDIDATE |

### 3.2 共性观察

- 三个文件都是 **step_1a 时代 v1 stub**：单 def + 注释，常量没有，外部状态没有，
  返回值是简单字符串 / int / float
- 三个文件**全部** tracked、**没有**位于 `.gitignore`
- 三个文件 mtime 一致（`2026-05-08 09:58:33`），表明它们大概率是历史 import
  操作把整批文件 stat 时统一刷过，但内容自 step_1a 后**未再修改**
- 三个文件**没有** `if __name__ == "__main__"` 入口，**没有** I/O，**没有**
  外部依赖
- 11C-A 已在 `services/confidence_evaluator.py` 提供 owner（confidence）；11B
  已纯化 `services/final_decision.py`（risk）；contradiction 逻辑已下沉到
  confidence / final_decision 的 supporting / conflicting decision_factors。
  三个 root stub 在 boundary 修复后全部**已无 owner 边界**。

---

## 4. import / reference audit

> 命令使用 `grep` 替代 `rg`（zsh 默认无 `rg`），覆盖 `--include='*.py'`、
> `--include='*.md'`，全仓 recursive。已对每条命中**人工区分**为
> active / test / docs-only / self-reference。

### 4.1 confidence_engine

| reference type | command | hits | classification |
|---|---|---|---|
| direct `import confidence_engine` | `grep -rn '^import confidence_engine\b' --include='*.py'` | **0** | — |
| `from confidence_engine import` | `grep -rn '^from confidence_engine import' --include='*.py'` | **0** | — |
| attribute `confidence_engine.<x>` | `grep -rnE 'confidence_engine\.' --include='*.py'` | 1 命中：`services/contract_calibration_inputs.py:31` | **docs-only**（出现在模块 docstring 的"never imports `confidence_engine.py` or any trading API"声明，不是 attribute access） |
| filename text `confidence_engine.py` | `grep -rn 'confidence_engine\.py'` | 9 命中 | **全部 docs-only**：`tasks/record_08`（4）、`tasks/record_10`（2）、`tasks/record_12e_x5`（2）、`tasks/step_2d_*`（1） |
| tests forbidden_modules 列表 | `grep -rn 'confidence_engine' tests/` | 9 个测试文件命中 | **negative-import 测试**：把 `"confidence_engine"` 写入 `forbidden_modules` set 用以**断言被测模块不 import 它**；测试**自身**不 import 该 stub |

**结论：active import = 0；attribute access active = 0；测试只在 negative-import
forbidden 列表中提及；docs-only 提及共 10 条。**

### 4.2 contradiction_engine

| reference type | hits | classification |
|---|---|---|
| direct `import contradiction_engine` | **0** | — |
| `from contradiction_engine import` | **0** | — |
| attribute `contradiction_engine.<x>` | **0** | — |
| filename text `contradiction_engine.py` | 9 命中 | **全部 docs-only**：`tasks/record_08`（3）、`tasks/record_10`（2）、`tasks/record_12e_x5`（2）、`tasks/step_2d_*`（1）、`tasks/step_2f_*`（1） |
| tests forbidden_modules 列表 | 7 个测试文件命中 | **negative-import 测试** |

**结论：active import = 0；attribute access = 0；同 §4.1。**

### 4.3 risk_model

| reference type | hits | classification |
|---|---|---|
| direct `import risk_model` | **0** | — |
| `from risk_model import` | **0** | — |
| attribute `risk_model.<x>` | **0** | — |
| filename text `risk_model.py` | 8 命中 | **全部 docs-only**：`tasks/record_08`（3）、`tasks/record_10`（2）、`tasks/record_12e_x5`（2）、`tasks/step_2d_*`（1）、`tasks/step_2f_*`（1） |
| tests forbidden_modules 列表 | 7 个测试文件命中 | **negative-import 测试** |

**结论：active import = 0；attribute access = 0；同 §4.1。**

### 4.4 negative-import 测试影响面分析

9 个测试文件在自身 `forbidden_modules` set 中列出 `"confidence_engine"` /
`"contradiction_engine"` / `"risk_model"`：

```
tests/test_regime_features_from_scan.py
tests/test_anti_false_exclusion_display.py
tests/test_run_continuous_smoothing_validation_v2.py
tests/test_soft_metadata_baseline_cache.py
tests/test_soft_metadata_simulator.py
tests/test_anti_false_exclusion_dashboard.py
（以及另外 3 个，总计 9 个文件）
```

每个测试都遵循 11G-style isolation 模板：

```python
class IsolationTests(unittest.TestCase):
    def test_module_does_not_import_forbidden(self) -> None:
        import ast
        import services.<MODULE_UNDER_TEST> as mod
        tree = ast.parse(Path(mod.__file__).read_text(...))
        forbidden_modules = {
            ..., "services.confidence_engine",
            "confidence_engine", "contradiction_engine", "risk_model",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(alias.name, forbidden_modules)
            elif isinstance(node, ast.ImportFrom):
                self.assertNotIn(node.module, forbidden_modules)
```

**关键观察**：

- 这些测试的语义是"被测模块**不**导入 forbidden_modules"
- 测试**自身**从不 `import` 这些 stub
- 因此**删除 stub 文件不会让这些测试失败**：测试逻辑只检查 `tree` 中的
  `Import / ImportFrom` 节点是否在 forbidden 集合里；stub 文件存不存在与
  断言无关
- forbidden_modules 集合里同时含 `services.confidence_engine`（**该路径的
  模块根本不存在**）和 root `confidence_engine`，证明 forbidden 集合的目的
  是"防止任何变体 import"，与文件存在性解耦

**进一步**：14C 如果决定 delete root stub，**不**需要修改这 9 个测试文件
（forbidden 集合保留即可，作为永久防御）。

---

## 5. compile / syntax audit

```
$ python3 -m py_compile confidence_engine.py contradiction_engine.py risk_model.py
$ echo $?
0
```

✅ **PASS**。三个文件语法合法、可被 `py_compile` 处理。本轮**不**修改它们。

---

## 6. runtime / pytest audit

执行了 read-only `pytest -q`：

```
$ pytest -q
=> 3252 passed, 10 skipped, 26 warnings, 94 subtests passed in 12.75s
```

✅ **3252 / 3252 passed, 10 skipped, 0 failed**。与 Step 13 §3.4 baseline
（3252）一致 — 14A commit 仅新增 plan 文档，无代码 / 测试改动，pytest 总数
未变。本轮**不**为审计跑额外的 replay / validation。

---

## 7. records/ vs tasks/ overlap audit

| 项 | 结果 |
|---|---|
| `records/` 是否存在 | ✅ 存在 |
| `tasks/` 是否存在 | ✅ 存在 |
| `records/` 下 tracked 文件数 | **1**（`records/03_replay_accuracy_and_exclusion_accuracy.md`） |
| `tasks/` 下 tracked 文件数 | 159 |
| 同名文件交集 | **0**（`comm -12` 比较两侧 basename 集合） |

### 7.1 唯一一份 `records/` 文件检查

`records/03_replay_accuracy_and_exclusion_accuracy.md`：

- 标题：「03 — AVGO original-system 1005-day replay: accuracy and exclusion accuracy」
- 标记为 "**canonical baseline record (03)**"
- 来自 2026-04-26 的 B-path replay run
- 明确列出 "Modules deliberately NOT used in this baseline" — 是
  baseline 审计文档（与 `tasks/record_08` / `record_10` 各自独立用途）
- 与 `tasks/record_*.md` 系列**没有**同名 / 同主题文件

### 7.2 结论

`records/` 与 `tasks/` **不**是冗余目录：

- `records/` = baseline run 记录（实证 / 审计 / 数据快照）
- `tasks/` = 设计文档 / 计划 / checkpoint / RISK 修复记录

**14B 推荐分类**：`records/` → **KEEP_ACTIVE**（不属 cleanup 范畴）。

不需要进入 14C / 14G。如果未来某次 cleanup 仍想合并，必须在那时**显式**在
14A 计划文档里更新 §7.5。

---

## 8. .claude/legacy_tasks audit

| 项 | 结果 |
|---|---|
| `.claude/legacy_tasks/` 是否存在 | ❌ **不存在** |
| `git ls-files .claude/legacy_tasks` | （空） |

**结论**：14A §7.4 列出的 `.claude/legacy_tasks/` quarantine 候选**不**存在
于当前 main / 本 worktree，**不需要** Step 14 处理。该条目从 14A §7.4 起即
可视为**已闭合**（will not exist → no action required）。任何未来如果出现，
重新进入 14B-style audit 即可。

---

## 9. 审计结论

### 9.1 三个 root stub

| file | current evidence | recommended next status | next step |
|---|---|---|---|
| `confidence_engine.py` | active import = 0；attribute access active = 0；只在 docs-only / negative-import 测试 forbidden 集合中被提及；compile pass；删除**不会**让任何测试失败 | **QUARANTINE_CANDIDATE** | Step 14C decision: **quarantine（移到 `archive/legacy/`）或 delete（直接 `git rm`）**；二选一须由 user / 后续 design 显式确认 |
| `contradiction_engine.py` | 同上 | **QUARANTINE_CANDIDATE** | 同上 |
| `risk_model.py` | 同上 | **QUARANTINE_CANDIDATE** | 同上 |

### 9.2 顺带审计

| object | current evidence | recommended status |
|---|---|---|
| `records/` | 1 个 tracked baseline 文件；与 `tasks/` 无交集；语义独立 | **KEEP_ACTIVE**（14A §7.5 该条目可标 closed） |
| `.claude/legacy_tasks/` | 不存在 | **N/A**（14A §7.4 该条目可标 closed） |

### 9.3 forbidden_modules 测试

9 个测试文件的 negative-import 集合保留 root stub 名称是**正确**且**应永久保留**
的防御设计。这些 stub 删除后，测试**继续生效**（assertion 语义与文件存在性
解耦）。Step 14C 不需要修改这些测试。

---

## 10. 不允许事项

本轮（Step 14B）**绝对**不允许：

- ❌ 删除任何 root stub（`confidence_engine.py` / `contradiction_engine.py` /
  `risk_model.py`）
- ❌ 移动任何 root stub
- ❌ 修改任何 root stub 内容
- ❌ 删除 `records/`
- ❌ 移动 `records/`
- ❌ 删除 / 移动 9 个 negative-import 测试中的 forbidden_modules 条目
- ❌ 修改 `services/contract_calibration_inputs.py` 第 31 行的 docs reference
- ❌ 处理 `.claude/worktrees/` / stash / DB backup / logs
- ❌ 修改 9 份 `tasks/record_*.md` / `tasks/step_*.md` 中提到 root stub 的段落
- ❌ 默认迁移 `run_predict` 到 V2
- ❌ 进入 3R-5 / 3R-6
- ❌ 启用 promotion / 接 trading / 引入 hard / forced / required
- ❌ 在本轮 commit 内顺手做 14C 决策

---

## 11. 推荐下一步

> 三个 root stub 全部确认 **active import = 0** 且 `pytest -q` 全绿。

**推荐**：

> **Step 14C — root stubs quarantine 或 delete decision**

具体路径：

1. 新增 `tasks/record_14c_root_stubs_decision.md`，内容：
   - 复述 14B 的零 active import 证据
   - 在 (a) 移到 `archive/legacy/{stub}.py` + 添加 `_DEPRECATED.md` 同目录
     说明、(b) 直接 `git rm` 之间**择一**
   - 列出选项的回滚方案
   - 列出 14C 实际执行时**仍要跑**的回归命令（focused boundary tests +
     full pytest，前后各一次）
2. **不**在 14C 计划文档里直接执行 cleanup；执行属 14G optional cleanup
3. 14C 完成后再进入 14D legacy V1 orchestrator audit（`services/projection_orchestrator.py`）

如果 14C 决定 delete：
- 必须在 commit 前后跑 `pytest -q` 与 `scripts/check.sh`，0 failed 才入 main
- 必须**不**修改 9 个 negative-import 测试（forbidden_modules 保留为防御）
- 必须**不**修改 9 份 docs（提及 root stub 为历史记录；保留可追溯）

如果 14C 决定 archive（移到 `archive/legacy/`）：
- 必须新增 `archive/legacy/_DEPRECATED.md` 说明 step_1a 来历
- 必须**不**让 `archive/legacy/` 进入 active import 路径
- `archive/legacy/` 应**不**包含 `__init__.py`（避免被无意 import）

**不**推荐：

- 直接进入 14C delete（必须先 14C 写决策文档）
- 借 14C 修改 negative-import 测试 / 修改 docs（保留追溯证据）
- 跳过 14C 直接进 14D
- 进 3R-5 / 3R-6
- 默认切 V2

---

## 12. 严守边界

本轮**只写 audit 文档**：

- 未改业务代码（`predict.py` / `services/predict_legacy_*` / 全部 active 文件
  byte-identical 与 main `afb006b`）
- 未新增测试 / 未修改测试
- 未删除文件 / 未移动文件
- 未写 DB / 未改 DB schema
- 未跑 replay / real validation（仅 read-only `pytest -q`）
- 未处理 untracked / DB backup / stash / `.claude/worktrees/`
- 未默认迁移 `run_predict` 到 V2
- 未启动真正 cleanup
- 未进入 3R-5 / 3R-6
- 未启用 candidate / 未复活 `continuous_smoothing` / 未接 trading
- 未顺手碰 RISK-1 / RISK-2 / RISK-3 / RISK-7 / RISK-8 / RISK-9 / RISK-10

本审计的修改路径：任何对 §3 速览、§4 import / reference 计数、§5 / §6
compile / pytest 结论、§7 / §8 顺带审计结论、§9 推荐分类、§11 推荐下一步
的调整，都必须以**显式更新本文件**的方式提出；同时检查是否需要同步更新
14A / 11H / 12E-X5 / 13。
