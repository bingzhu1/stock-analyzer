# 14G记录：Legacy V1 Orchestrator Audit

> 本记录是 **Step 14 的第七阶段：legacy V1 orchestrator audit**。Step 14F
> test fixture hygiene implementation 已入 main（`bd4b81b`）。
>
> 本轮**只写审计文档**：未改业务代码、未改测试、未删除 / 移动文件、未跑
> replay / real validation、未写 DB / 未改 DB schema、未默认迁移
> `run_predict` 到 V2、未 commit / push、未进入 3R-5 / 3R-6、未顺手碰
> 任何 RISK / cleanup 候选项。

---

## 1. Step 14G 目的

只审计 [`services/projection_orchestrator.py`](services/projection_orchestrator.py)
（旧 V1 orchestrator）的当前归属，**不**删除、**不**移动、**不**改代码、
**不**新增测试。

目标：

1. 锁定 V1 orchestrator 的**当前确切被 import 面**（active code 入口 vs
   tests-only 入口 vs docstring 字符串引用）
2. 锁定 V1 提供的**公共 API**，记录每个 API 的实际 caller
3. 验证 V1 与 V2 (`services/projection_orchestrator_v2.py`) 的**调用方向**
   和**重入保护**关系
4. 对照 14A §7.2 的判断（"仅由 V2 自己 import + tests"）做一次
   **fact-check**，确认证据是否仍然成立 / 已经过期
5. 给出 V1 的归类：`KEEP_ACTIVE` / `KEEP_FROZEN_DIAGNOSTIC` /
   `QUARANTINE_CANDIDATE` / `UNKNOWN_REVIEW_REQUIRED`，并写明前置条件

**不**改 V1、**不**改 V2、**不**改 `predict.py`、**不**改测试、**不**改 UI。

签收依据：[tasks/record_14a_cleanup_quarantine_plan.md](tasks/record_14a_cleanup_quarantine_plan.md)
§7.2 + [tasks/record_09_module_inventory_detail.md](tasks/record_09_module_inventory_detail.md)
§3 / §10 / §17 + [tasks/record_08_three_system_architecture_diagnosis.md](tasks/record_08_three_system_architecture_diagnosis.md)
§5 / §13 RISK-1。

---

## 2. 当前 main 状态

| 项 | 状态 |
|---|---|
| Step 12 boundary fixes | ✅ 全部入 main |
| Step 13 regression | ✅ 入 main |
| Step 14A cleanup plan | ✅ 入 main |
| Step 14B root dead stubs audit | ✅ 入 main |
| Step 14C root stubs delete decision record | ✅ 入 main |
| Step 14D root v1 stubs quarantine implementation | ✅ 入 main |
| Step 14E test fixture hygiene plan | ✅ 入 main |
| Step 14F test fixture hygiene implementation | ✅ 入 main |
| main 最新 commit | `bd4b81b chore(cleanup): scope app_analysis_context_fixture monkeypatch with try/finally restore` |
| 本轮真正改 V1 / V2 / 测试 | ❌ 不允许 |
| 本轮跑 full pytest | ✅ 仅 baseline 验证（3256 passed / 10 skipped / 0 failed）；不改代码不影响 baseline |
| 本轮处理 untracked artifacts | ❌ 不允许；`logs/prediction_log.jsonl` standing untracked 维持 14A §9 状态 |

---

## 3. 文件概览

| 项 | 值 |
|---|---|
| path | [services/projection_orchestrator.py](services/projection_orchestrator.py) |
| tracked | ✅ `git ls-files services/projection_orchestrator.py` 命中 |
| 行数 | 191 |
| 主要函数 / public API | `build_projection_orchestrator_result(*, symbol, error_category, limit, lookback_days, target_date) -> dict`（line 148）；`format_projection_report(predict_result, *, advisory, scan_result, target_date, lookback_days) -> dict`（line 111） |
| 主要 helper（私有，模块内） | `_normalize_final_symbol`（line 29）、`_latest_target_date`（line 36）、`_build_summary_df`（line 42）、`_build_momentum_frame`（line 50）、`_build_predict_result`（line 63） |
| 模块用途（按 docstring + 实现） | "Projection orchestrator for command-facing final reports." — 把现有 advisory + Scan + Predict 输出装配成命令行 / UI 可读的次日推演报告。本身**不**做 exclusion、**不**做 V2 五状态分布、**不**做 final_decision，是 V2 链路里**主推演入口**的 thin layer |
| 与 [`services/projection_orchestrator_v2.py`](services/projection_orchestrator_v2.py) 的关系 | V2 (`projection_orchestrator_v2.py:16`) 在**模块顶层**`from services.projection_orchestrator import build_projection_orchestrator_result`；V2 的 `run_projection_v2` 把 `build_projection_orchestrator_result` 当**默认** `_projection_runner` (line 413)，并在 line 450 调用它产出 `legacy_result`。换言之：**V2 在生产路径上调用 V1**，V1 处于 V2 的 `primary_analysis` step 之内 |

### 3.1 V1 顶层依赖（自身 import 的对象）

| 行号 | 依赖 |
|---|---|
| 14 | `from matcher import build_near_match_table, build_next_day_match_table, load_coded_avgo` |
| 15 | `from predict import run_predict` |
| 16 | `from scanner import run_scan` |
| 17 | `from services.projection_orchestrator_preflight import build_projection_orchestrator_preflight` |
| 20 | `from services.data_query import load_symbol_data` |
| 21 | `from services.evidence_trace import build_projection_evidence_trace` |
| 22 | `from services.predict_summary import build_predict_readable_summary` |
| 23 | `from stats_reporter import SUMMARY_COLUMNS, summarize_match_df` |

> 关键观察：V1 在**顶层**`from predict import run_predict`。这意味着任何
> `import services.projection_orchestrator` 都会触发 `predict` 模块加载。
> 这条边 (`projection_orchestrator → predict.run_predict`) 是 [predict.py:1315](predict.py:1315)
> docstring 里**显式说明**的循环防护原因——`predict.py` 必须用 **lazy
> import** 调 V2，避免 `predict.py ↔ projection_orchestrator.py` 顶层循环。

---

## 4. import / reference audit

### 4.1 命令

```bash
rg "^\s*from services\.projection_orchestrator import|^\s*import services\.projection_orchestrator(\b|$)" --glob "*.py" -n
```

### 4.2 真实 top-level / nested import 命中

| # | path | line | scope | type | 调用方向 |
|---|---|---|---|---|---|
| 1 | [services/projection_orchestrator_v2.py](services/projection_orchestrator_v2.py:16) | 16 | **module top-level** | **active code** | V2 → V1（生产路径） |
| 2 | [tests/test_projection_orchestrator.py](tests/test_projection_orchestrator.py:13) | 13 | module top-level | **test** | test → V1（API contract） |

### 4.3 docstring / string-only references（**不**是真正 import）

| # | path | line | scope | type | 说明 |
|---|---|---|---|---|---|
| 3 | [predict.py](predict.py:1315) | 1315 | docstring of `_build_projection_three_systems_attachment` | **doc-only** | 解释为何要用 lazy import 调 V2（"projection_orchestrator (which already imports run_predict)"） |
| 4 | [services/predict_legacy_v2_bridge.py](services/predict_legacy_v2_bridge.py:20) | 20 | docstring | doc-only | 历史说明 |
| 5 | [tests/test_predict_legacy_adapter.py](tests/test_predict_legacy_adapter.py:706-708) | 706–708 | `forbidden_modules` 字符串 | **negative-import test** | **断言 `predict.py` 不 import `services.projection_orchestrator(_v2)?`**；属于防御性 contract，**保留** |
| 6 | [tests/test_predict_x4b_v2_payload_opt_in_boundary.py](tests/test_predict_x4b_v2_payload_opt_in_boundary.py:474) | 474 | `forbidden_modules` 字符串 | negative-import test | 同上 |
| 7 | [tests/test_confidence_evaluator.py](tests/test_confidence_evaluator.py:467-468) | 467–468 | `forbidden_modules` 字符串 | negative-import test | 断言 `services/confidence_evaluator.py` 不 import V1 / V2 |
| 8 | [tests/test_predict_legacy_v2_bridge.py](tests/test_predict_legacy_v2_bridge.py:33,567) | 33 / 567 | docstring | doc-only | 解释 bridge 路径 |

### 4.4 lazy / dynamic import for V1 specifically

无。`rg "from services\.projection_orchestrator import"` 在 active 代码里
**只**有 `services/projection_orchestrator_v2.py:16` 一行，**且为顶层**。
V1 没有任何 lazy / dynamic / `importlib.import_module("services.projection_orchestrator")`
形式的 import。

> 这与 [predict.py](predict.py:1340) 的 lazy import **方向相反**：predict.py
> 的 lazy import 目标是 V2，**不是** V1。V1 永远是 V2 顶层 import，进入
> `sys.modules` 的时机和 V2 完全同步。

### 4.5 调用拓扑（active path）

```
predict.run_predict
  └─ (lazy)  services.projection_orchestrator_v2.run_projection_v2
              └─ (top-level via default _projection_runner)
                  services.projection_orchestrator.build_projection_orchestrator_result  ← V1
                    ├─ matcher.{load_coded_avgo, build_*_match_table}
                    ├─ scanner.run_scan
                    ├─ predict.run_predict        ← 由 [_projection_three_systems_attachment_state.active] 重入门控保护
                    └─ services.projection_orchestrator_preflight.build_projection_orchestrator_preflight
```

重入保护：[predict.py:1330-1336](predict.py:1330-1336) 的
`_projection_three_systems_attachment_state` 在外层 `run_predict` 已经
触发了 V2 → V1 → `run_predict` 的链路时，把内层
`_build_projection_three_systems_attachment` **降级**为
`_degraded_projection_three_systems` 而**不**再调一次 V2。这条防护**依赖**
V1 在 active path 内（V1 调 `run_predict` 是触发重入的入口）。

---

## 5. API / behavior audit

### 5.1 公开 API

| 函数 | 签名 | 实际 caller | 仍有 caller？ | 与 predict.py / V2 的关系 | legacy compat? |
|---|---|---|---|---|---|
| `build_projection_orchestrator_result` | `(*, symbol, error_category=None, limit=5, lookback_days=None, target_date=None) -> dict` | `services.projection_orchestrator_v2.run_projection_v2` (line 450, default `_projection_runner`)；`tests/test_projection_orchestrator.py` 4 次 | ✅ **active + test** | V2 `run_projection_v2` 在 `try/except` 内调它产出 `legacy_result`，作为 V2 五状态链 (`primary_analysis`) 的输入 | **不**是 legacy compat shim；V2 把它当**当前生产实现**用 |
| `format_projection_report` | `(predict_result, *, advisory=None, scan_result=None, target_date=None, lookback_days=None) -> dict` | 仅 `tests/test_projection_orchestrator.py:155` 直接调用 | ⚠️ **test-only direct caller**（V2 不直接调，但 `build_projection_orchestrator_result` 内部 line 173 调它） | 间接通过 `build_projection_orchestrator_result` 进入 V2 path | 否 |

> `format_projection_report` 虽然只在 test 里**直接**调用，但它是
> `build_projection_orchestrator_result` 内部第 173 行的核心步骤，所以
> **不能**视为 dead code—— V2 链路通过 `build_projection_orchestrator_result`
> 间接 reach 它。

### 5.2 私有 helper

| 函数 | 实际 caller | 仍需要？ |
|---|---|---|
| `_normalize_final_symbol` | line 76 / 162 内部使用；用于把 `"avgo" → "AVGO"` 并 reject 非 AVGO | ✅ |
| `_latest_target_date` | line 89 内部使用；当 caller 未传 `target_date` 时取 coded_df 最新日期 | ✅ |
| `_build_summary_df` | line 93 内部使用 | ✅ |
| `_build_momentum_frame` | line 94 内部使用 | ✅ |
| `_build_predict_result` | line 170 内部使用 | ✅ |

---

## 6. tests audit

### 6.1 test 文件依赖现状

| path | 是否仍依赖 V1 |
|---|---|
| [tests/test_projection_orchestrator.py](tests/test_projection_orchestrator.py) | ✅ **直接** import `build_projection_orchestrator_result` / `format_projection_report`；5 个 test methods 全部针对 V1 行为 |
| [tests/test_projection_orchestrator_v2.py](tests/test_projection_orchestrator_v2.py) | 间接（V2 默认 `_projection_runner` 是 V1，所以不传 `_projection_runner` 的 V2 测试会跑 V1） |
| 6 个 negative-import boundary tests（见 §4.3 #5–#8） | 仅在 `forbidden_modules` 字符串里出现，断言**其他模块**不 import V1；它们不是 V1 的 caller，是 V1 import 边界的**反向**防护 |

### 6.2 focused test 结果

```
$ pytest tests/test_projection_orchestrator.py -q
.....                                                                    [100%]
5 passed in 1.34s
```

### 6.3 full pytest 结果

```
$ pytest -q
3256 passed, 10 skipped, 26 warnings, 94 subtests passed in 14.54s
```

baseline 14F = 3256 passed → 14G = 3256 passed（本轮**不**改代码 / **不**新增
测试，pytest 数字必须 byte-identical 于 14F；已确认）。

### 6.4 `python3 -m py_compile services/projection_orchestrator.py`

```
py_compile OK
```

---

## 7. 分类判断

### 7.1 证据汇总

| 证据 | 结论 |
|---|---|
| `services/projection_orchestrator_v2.py:16` **顶层** `from services.projection_orchestrator import build_projection_orchestrator_result` | V1 在 V2 加载时进 `sys.modules`，是 V2 import-graph 的一部分 |
| `projection_orchestrator_v2.py:413` 把 `build_projection_orchestrator_result` 当**默认** `_projection_runner` | V1 是 V2 生产路径的**默认** primary_analysis 实现 |
| `projection_orchestrator_v2.py:450` 在 `try` 块里调用 `_projection_runner(...)` | 任何 caller 没有显式传 `_projection_runner=...` 时，V1 都会跑 |
| `services/projection_entrypoint.py` / `services/historical_replay_training.py` / `services/projection_v2_adapter.py` / `predict.py` 调用 V2 时**没**传 `_projection_runner` | V1 = active 生产实现（4 个 V2 caller 全部走默认） |
| [predict.py:1315](predict.py:1315) docstring 显式记录 V1 → predict.run_predict 的循环依赖事实 | V1 的 active 性是 predict.py lazy-import 设计的**前提条件** |
| [predict.py:1330-1336](predict.py:1330-1336) 的 `_projection_three_systems_attachment_state` 重入保护 | 重入门控**依赖** V1 在 active path 上（V1 调 run_predict 是触发重入的入口） |
| `tests/test_projection_orchestrator.py` 5 个 method 全绿 | V1 行为契约仍被 active 测试守住 |

### 7.2 14A §7.2 的 fact-check

> 14A §7.2 表述：**"只被 `tests/test_projection_orchestrator.py` 显式
> import；`predict.py` docstring 仅文本提及"**

**该表述不准确 / 已过期。** 实际证据：

1. `services/projection_orchestrator_v2.py:16` 是**真实顶层 import**，
   不是 docstring / 字符串引用。
2. V2 的 `_projection_runner` 默认值（line 413）和 V2 实际调用点（line 450）
   把 V1 钉死在生产路径。
3. 14A §7.2 注释里"V2 path 不通过此 orchestrator 路由"是要在 14G 验证的
   **假设**，本审计**否定**该假设。

> 14A §7.2 的判断需要**校正**。本 14G 文件的 §7.3 分类即为校正后的结论。
> 不在本轮直接修改 14A 文档（避免触碰已 commit 的历史 audit）；如有需要，
> 留待后续独立 `docs(cleanup):` commit 处理。

### 7.3 分类结论

> **`KEEP_ACTIVE`**

理由：

1. V1 是 V2 默认 `_projection_runner` 的**唯一**实现，没有其他实现可以
   替代 default 位置而**不**改 V2 代码或测试调用方
2. V2 的 4 个 active caller（`projection_entrypoint` / `historical_replay_training` /
   `projection_v2_adapter` / `predict.py` 的 lazy 入口）**全部**走 V2 默认
   `_projection_runner`，意味着 production 跑 V2 时 V1 必然被调
3. V1 是 `predict.py` lazy-import 设计原因的**显式被记录方**（见
   [predict.py:1315](predict.py:1315) docstring）；删 / 移 V1 会让该设计
   说明失去 referent
4. V1 的 重入门控对应方在 [predict.py:1330-1336](predict.py:1330-1336)；
   该门控**依赖** V1 仍然在 active path 上
5. focused test (5/5) + full pytest (3256/0) 全绿 ⇒ 当前行为契约稳定，
   没有信号要求 quarantine

**不**满足 `KEEP_FROZEN_DIAGNOSTIC`：V1 不是诊断 / 报表层，是 V2 主推演链
内部步骤；**不**满足 `QUARANTINE_CANDIDATE`：active code import 仍存在；
**不**是 `UNKNOWN_REVIEW_REQUIRED`：证据完整，无需进一步 disambiguation。

---

## 8. 推荐处理

> **保留 active，不进入 14H quarantine/delete decision。**

具体建议：

1. **不**对 V1 做任何改动（不删、不移、不压缩 thin shim、不重命名为
   `_v1` 后缀、不打 `# DEPRECATED:` marker）。当前 V1 不是 deprecated
   surface，是 V2 默认 `_projection_runner`。
2. **不**对 [tests/test_projection_orchestrator.py](tests/test_projection_orchestrator.py)
   做任何改动；它守的是 V1 公开 API 行为契约，仍有意义。
3. 如果未来要把 V2 改成不依赖 V1（即把 `_projection_runner` 默认实现内联
   到 V2，或换成新的 V3 实现），属于**架构级**改动，**不**在 14 系列
   cleanup 范围；至少需要：
   - 一份独立的 V2 内联设计 plan（类似 11A / 11C 风格）
   - 把 `predict.py:1315` docstring 同步更新
   - 把 [predict.py:1330-1336](predict.py:1330-1336) 重入保护与新拓扑
     重新对齐
   - full pytest + focused boundary suite 全绿
   - 单独 commit / 单独 PR
4. 14A §7.2 的"`仅由 V2 自己 import + tests`"表述需要在**未来**某个
   `docs(cleanup):` commit 里改成"V2 active path 默认 runner + tests"；
   **不**在本轮做（本轮只产出 audit 文档；不修订历史 record）。

---

## 9. 不允许事项

本轮 14G **绝对**不允许：

1. ❌ 删除 [services/projection_orchestrator.py](services/projection_orchestrator.py)
2. ❌ 移动 [services/projection_orchestrator.py](services/projection_orchestrator.py)
3. ❌ 改 [tests/test_projection_orchestrator.py](tests/test_projection_orchestrator.py)
4. ❌ 改 [predict.py](predict.py)（包括 docstring / lazy import / 重入保护）
5. ❌ 改 [services/projection_orchestrator_v2.py](services/projection_orchestrator_v2.py)（包括 `_projection_runner` 默认值）
6. ❌ 改 [ui/](ui)（`ui/predict_tab.py` / `ui/home_tab.py` / `ui/command_bar.py` 等）
7. ❌ 默认迁移 `run_predict` 到 V2（即改 `_projection_runner` 默认实现）
8. ❌ 进入 3R-5 / 3R-6
9. ❌ 把 audit 和功能改动混在一个 commit
10. ❌ 改 9 个 negative-import 测试的 `forbidden_modules` 字符串
11. ❌ 改 14A / 14B / 14C / 14D / 14E / 14F record 历史文本
12. ❌ 在本 14G commit 内顺手处理 logs / DB backup / `.claude/worktrees/` /
    stash / 任何 §9 untracked artifact
13. ❌ 借机引入 candidate / 启用 promotion / 复活 continuous_smoothing /
    接 trading

---

## 10. 推荐下一步

> **基于 §7.3 `KEEP_ACTIVE` 结论，不推荐进入 Step 14H quarantine/delete
> decision；V1 必须保留。**

未来路径分两类：

### 10.1 cleanup 范围内（推荐先做）

- **Step 14H — 14A 14A§7 record fact-check**：把 14A §7.2 / §10.4
  里把 V1 描述为"仅 tests import"的表述更新为"V2 active path 默认 runner +
  tests"；同步同行 `suggested action` 列；**只**改 14A 文档措辞，**不**改
  V1 / V2 / 测试。是 docs-only 修订，可与 14G 在**不同**的 `docs(cleanup):`
  commit 里完成
- 或者：**选择跳过 14H**，认为 14A §7.2 的"required check before
  quarantine"已被 14G 完成，14A 文本保持 frozen（因为 14A 本身就是
  audit-stage record，14G 的存在已经构成更新）

### 10.2 架构层面（**不**在 14 系列 cleanup 范围）

- 如果未来需要简化 V2 → V1 调用链（例如把 `_projection_runner` 默认实现
  内联进 V2），需要单独的设计 plan + 单独 PR；此为 RISK-1 / RISK-6 解耦
  完成**之后**才能讨论的事项
- 不**推荐**在当前阶段做：14 系列 cleanup 的目标是消除死代码 / 死 stub /
  fixture 污染，不是重构 active 推演路径

### 10.3 不推荐

- ❌ 把 V1 移到 `archive/legacy/services/` —— 会破坏 V2 顶层 import
- ❌ 删除 V1 —— 同上，且会把 `predict.py:1315` docstring 变成 dangling
  reference
- ❌ 把 V1 压缩成 thin shim —— V1 自己已经是 thin layer（191 行；只做装配
  与符号校验，无算法逻辑），再压缩没有 cleanup 价值
- ❌ 跳过 14H 直接进 3R-5 / 3R-6
- ❌ 在任何 14 系列后续 commit 内把 14A / V1 / V2 改动混在一起

---

## 11. 严守边界

本轮**只写 audit 文档**：

- 未改业务代码（`services/projection_orchestrator.py` / `services/projection_orchestrator_v2.py` /
  `predict.py` / `ui/*` / 其他 `services/*` 全部 byte-identical 与 main `bd4b81b`）
- 未改测试（`tests/test_*.py` 全部 byte-identical）
- 未新增测试
- 未删除文件 / 未移动文件
- 未写 DB / 未改 DB schema
- 未跑 replay / real validation
- 未跑 full pytest 是为修改代码确认（本轮 pytest 仅作 baseline 校验，
  数字与 14F 完全一致：3256 passed / 10 skipped / 0 failed）
- 未处理 untracked / DB backup / stash / `.claude/worktrees/`
- 未默认迁移 `run_predict` 到 V2
- 未启动 V2 内联设计
- 未进入 3R-5 / 3R-6
- 未启用 candidate / 未复活 `continuous_smoothing` / 未接 trading
- 未顺手碰 RISK-1 / RISK-2 / RISK-3 / RISK-7 / RISK-8 / RISK-9 / RISK-10

本计划的修改路径：任何对 §3 文件概览、§4 import audit、§5 API audit、
§7 分类判断、§8 / §9 / §10 / §11 决策的调整，都必须以**显式更新本文件**
的方式提出；同时检查是否需要同步更新 14A / 09 / 08。
