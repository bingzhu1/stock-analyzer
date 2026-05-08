# 14E记录：Test Fixture Hygiene Plan

> 本记录是 **Step 14 的第五阶段：test fixture hygiene 计划**。Step 14D
> root v1 stubs quarantine implementation 已入 main（`3b0d470`）。
>
> 本轮**只写计划文档**：未改业务代码、未改测试、未改 fixture、未删除 /
> 移动文件、未清理 logs / DB backup / `.claude/worktrees/`、未跑 replay /
> real validation、未写 DB / 未改 DB schema、未默认迁移 `run_predict` 到
> V2、未 commit / push、未进入 3R-5 / 3R-6、未顺手碰任何 RISK。

---

## 1. Step 14E 目的

只为 [`tests/fixtures/app_analysis_context_fixture.py`](tests/fixtures/app_analysis_context_fixture.py)
的 **monkeypatch / module-level pollution hygiene** 写计划。

目标：

1. 锁定该 fixture 的 **当前确切污染面**（哪些模块属性被永久 rebind、是否有
   `try/finally` restore、`sys.modules` / `runpy` 副作用如何传播）
2. 列出 **使用方** 与 **依赖方**，区分 (a) 真正用 fixture 的测试和 (b) 只在
   docstring 提到 fixture 的测试
3. 给 **保守 / 折中 / 激进** 三个修复方案的对比
4. 推荐其一，并写明**实施前置条件 / 最低跑测要求 / 回滚策略**

**不**改 fixture、**不**改测试、**不**改业务代码。

签收依据：[tasks/record_14a_cleanup_quarantine_plan.md](tasks/record_14a_cleanup_quarantine_plan.md)
§7.3 + §10.4 + [tasks/record_14b_root_dead_stubs_audit.md](tasks/record_14b_root_dead_stubs_audit.md)
§9（顺带列出该 fixture 为 test fixture hygiene candidate）。

---

## 2. 当前背景

| 项 | 状态 |
|---|---|
| Step 12 boundary fixes | ✅ 全部入 main |
| Step 13 regression | ✅ 入 main |
| Step 14A cleanup plan / 14B audit / 14C decision / 14D quarantine implementation | ✅ 全部入 main |
| main 最新 commit | `3b0d470 chore(cleanup): quarantine root v1 stubs to archive/legacy/root_stubs` |
| fixture hygiene 已实施 | ❌ 未开始（仅 12E-X1 起的 5 个 boundary test 文件用 `_fresh_predict_module()` 防御） |
| 本轮真正修 fixture | ❌ 不允许 |
| 本轮跑 full pytest | ❌ 不需要（14D 入 main 后 baseline 仍为 3252 passed / 0 failed） |

---

## 3. fixture 文件概览

| 项 | 值 |
|---|---|
| path | [tests/fixtures/app_analysis_context_fixture.py](tests/fixtures/app_analysis_context_fixture.py) |
| 行数 | 128 |
| tracked | ✅ `git ls-files tests/fixtures/` 命中 |
| 主要作用 | 给 `streamlit.testing.v1.AppTest.from_file(...)` 准备一份**可用 stub 替换 active 模块函数**的入口脚本，并通过 `runpy.run_path("app.py", run_name="__main__")` 触发整个 `app.py` 的 Streamlit 渲染流程，让 AppTest 能在隔离场景下断言 UI 行为 |
| 被加载方式 | **不是**作为 `pytest fixture` 注入；而是 `AppTest.from_file(FIXTURE)` 把它**作为 Streamlit 脚本**整体执行。等价于 "Python 把这个脚本顶层语句**全部**执行一遍" |

### 3.1 fixture 顶层关键操作清单

| 行号 | 操作 | 类型 |
|---|---|---|
| 9–10 | `ROOT = …; sys.path.insert(0, str(ROOT))` | 路径污染（导入路径） |
| 12–15 | `import matcher`, `import predict`, `import scanner`, `import stats_reporter` | 加载 active 模块（让 module 对象进入 `sys.modules`） |
| 18–115 | 5 个 `fake_*` 函数定义（纯函数；无副作用） | 无害 |
| **118** | `matcher.load_coded_avgo = fake_coded_df` | **永久 attribute rebind**（active 模块） |
| **119** | `matcher.build_next_day_match_table = lambda …: fake_match_df(…)` | 同上 |
| **120** | `matcher.build_near_match_table = lambda …: fake_match_df(…)` | 同上 |
| **121** | `matcher.save_match_results = lambda *args, **kwargs: None` | 同上（吞掉写入） |
| **122** | `matcher.save_near_match_results = lambda *args, **kwargs: None` | 同上 |
| **123** | `stats_reporter.build_stats_summary = fake_summary` | 同上 |
| **124** | `stats_reporter.save_stats_summary = lambda …: None` | 同上 |
| **125** | `scanner.run_scan = fake_scan` | 同上（最高影响：scan 不再调真实 scanner） |
| **126** | `predict.run_predict = fake_predict` | 同上（最高影响：12E-X1 起所有 boundary test 都因此用 `_fresh_predict_module()` 防御） |
| 128 | `runpy.run_path(str(ROOT / "app.py"), run_name="__main__")` | 执行 `app.py` 顶层；触发 Streamlit 渲染 |

---

## 4. monkeypatch / pollution 风险审计

> 全部基于上述 fixture 顶层操作。**不修改**任何 active 代码 / 测试，仅描述风险。

| # | risk | evidence | severity | recommended handling |
|---|---|---|---|---|
| 1 | 9 个 `<module>.<attr> = <fake>` 永久 rebind 在**真实** active 模块对象上（`matcher` / `scanner` / `predict` / `stats_reporter`），**没有** `try/finally` restore | fixture lines 118–126 | **HIGH** | 必须包进 try/finally 或类似机制，在 `runpy.run_path` 完成后恢复原始 attribute |
| 2 | `from X import Y` 在 active 模块加载时把 `Y` **引用**捕获到 importer 的命名空间。fixture 在 import `app.py`（runpy 触发链）之前已 rebind，使得任何 `from predict import run_predict` 风格的 active 模块（例如 `ui/predict_tab.py:10` / `services/projection_orchestrator.py:15`）都会捕获到 **fake** 引用。即便后续 restore `predict.run_predict`，`ui.predict_tab.run_predict` 名字空间内的引用仍指向 fake | `grep -rn "^from predict import run_predict"` 命中 4 处 active importer；任意一处在 fixture 加载链路中被 import，都会捕获 fake | **HIGH** | 不能仅靠 restore source-module 解决；必须额外**清空** `sys.modules` 中受污染的 importer 模块（让下次 `import` 重新执行模块顶层；从 fixture 出来后未污染的 `predict.run_predict` 被重新 `from-import`），或者改造 importer 改用 `predict.run_predict(...)` 风格调用（属业务级改动，**不**在 14E 范畴） |
| 3 | 模块顶层无 `if __name__ == "__main__":` 守卫；任何 `import tests.fixtures.app_analysis_context_fixture` 都会触发 §3.1 的 9 个 rebind + `runpy.run_path("app.py")` | fixture 整文件没有 main guard | **HIGH** | 加 main guard / 提供 `setup()` / `teardown()` 函数 / 改用 pytest fixture API；但需保留 `AppTest.from_file(FIXTURE)` 语义（脚本被作为 Streamlit 脚本执行，等价于 main） |
| 4 | `runpy.run_path("app.py", run_name="__main__")` 在 fixture 顶层执行；如果 fixture 被 import 而非 AppTest 加载，会真的把 `app.py` 跑一遍 | fixture line 128 | **MEDIUM** | 同 #3：放进 main guard 或 helper |
| 5 | `sys.path.insert(0, str(ROOT))` 在 fixture 顶层 unconditional | fixture line 10 | **LOW** | 幂等；只是把仓库根目录加入 import 路径；可保留 |
| 6 | 测试顺序敏感：当前 5 个 12E boundary test 文件（`test_predict_legacy_wrapper_boundary` / `test_predict_x{2,3}_*` / `test_predict_legacy_adapter`?? / `test_predict_x4b_*` / `test_predict_legacy_v2_bridge`）都内置 `_fresh_predict_module() = importlib.reload(predict)` 防御。如果未来新增 boundary test 不加防御 → 在 `test_app_analysis_context.py` 之后跑会读到 `predict.run_predict == fake_predict` | 5 处 `_fresh_predict_module` 命中（grep 验证） | **MEDIUM** | 修 fixture 后可移除分布式防御；但 14E **仅**写计划，**不**移除 |
| 7 | `__pycache__/` 在 `tests/fixtures/` 下出现（已被 `.pyc` cache 加速 import）；不直接是污染源，但 fixture 的副作用通过缓存可见性增加 | `tests/fixtures/__pycache__` 存在 | **LOW** | 与正常 Python 行为一致；不需处理 |

### 4.1 当前为什么 pytest 仍全绿

12E-X1 起，每个**新增的 boundary test 文件**主动添加了 reload 防御：

```python
def _fresh_predict_module():
    import predict as _predict
    return importlib.reload(_predict)
```

`importlib.reload(predict)` 会**重新执行** `predict.py` 模块体，覆盖 fixture
留下的 `predict.run_predict = fake_predict`。这就是为什么 `pytest -q`
3252 passed / 0 failed 在当前 main（`3b0d470`）依然全绿的原因。

但这个防御是**分布式补丁**，不是源头修复：

- 5 个 boundary test 文件**各自**重复 `_fresh_predict_module` 助手
- 任何未来新增 boundary test 的作者都**必须**记得重写这个助手
- 防御**只覆盖** `predict` 模块；`scanner` / `matcher` / `stats_reporter`
  的 fake 仍然驻留在 `sys.modules` 中（目前没有 boundary test 直接读这些模块，
  所以不显著）

---

## 5. 使用方审计

`grep -rn "app_analysis_context_fixture" tests/` 命中 7 个测试文件。区分如下：

| path | use case | risk level | 是否需要改 |
|---|---|---|---|
| [tests/test_app_analysis_context.py](tests/test_app_analysis_context.py) | **唯一真正使用 fixture 的测试**：用 `AppTest.from_file(FIXTURE)` 加载 fixture 作为 Streamlit 脚本 | HIGH（污染源驱动方） | 14E 之后实施时**可能**需要改：从读 fixture 改为读重写后的等价 fixture / fixture-script |
| [tests/test_predict_legacy_wrapper_boundary.py](tests/test_predict_legacy_wrapper_boundary.py) | 仅 docstring 提及（"fixture rebinds predict.run_predict; therefore we use `_fresh_predict_module`"）；本身**用 reload 防御** | MEDIUM | 实施时（如果污染消除）可移除 `_fresh_predict_module` 助手；但 14E **不**改 |
| [tests/test_predict_x2_confidence_wiring_boundary.py](tests/test_predict_x2_confidence_wiring_boundary.py) | 同上 | MEDIUM | 同上 |
| [tests/test_predict_x3_summary_wiring_boundary.py](tests/test_predict_x3_summary_wiring_boundary.py) | 同上 | MEDIUM | 同上 |
| [tests/test_predict_x4b_v2_payload_opt_in_boundary.py](tests/test_predict_x4b_v2_payload_opt_in_boundary.py) | 同上 | MEDIUM | 同上 |
| [tests/test_predict_legacy_v2_bridge.py](tests/test_predict_legacy_v2_bridge.py) | 同上 | MEDIUM | 同上 |
| [tests/test_regime_features_from_scan.py](tests/test_regime_features_from_scan.py) | 仅 docstring 注释（"fixture does not affect this test"） | LOW | 不需改 |

> 关键观察：**fixture 真正只有 1 个 active consumer**（`test_app_analysis_context.py`）。
> 其余 6 个文件只是**因为 fixture 的污染会扩散**而做防御性引用。如果 14E
> 实施清除污染源，5 个 boundary test 的 `_fresh_predict_module` 助手可以
> 在后续小 commit 中精简为简单的 `import predict`（但**14E 本轮不修**）。

---

## 6. 当前测试状态

| 项 | 状态 |
|---|---|
| `git status` | clean（除 `logs/prediction_log.jsonl` standing untracked） |
| 是否运行 focused tests | **否**（本轮 plan-only；14D 入 main 时 focused 已 180 / 0 failed） |
| 是否运行 full pytest | **否**（14D 入 main 时 full pytest 已 3252 / 0 failed；本计划不改代码不需要重跑） |
| 未跑原因 | 14E 是**纯计划文档阶段**：不改 fixture、不改测试 → pytest 结果与 main `3b0d470` baseline 完全一致 |

如果实施阶段（14F+）真正改 fixture，必须在 commit 前 / 后各跑一次 full pytest
确认没有引入回归（详见 §8）。

---

## 7. 推荐修复原则

未来实施 fixture cleanup 必须遵守：

1. **fixture cleanup 必须单独 commit**（与 `chore(cleanup):` 同 11H §6.2 / 14A §3 commit-per-fix 一致）
2. **先写 failing hygiene tests**（red baseline）：例如
   `tests/test_app_analysis_context_fixture_hygiene.py`，断言：
   - `import tests.fixtures.app_analysis_context_fixture` 后，`predict.run_predict`
     **未**指向 `fake_predict`
   - `scanner.run_scan` / `matcher.load_coded_avgo` / `stats_reporter.build_stats_summary`
     **未**被 fixture 永久污染
3. 使用 **pytest `monkeypatch` fixture** 或 **context manager** 进行临时 patch
   （遵守 setup → patch → run → teardown → restore 流程）
4. **所有 patch 必须 restore**（即使是测试结束时 Streamlit 已经"用完"了 fake，
   仍然 restore 让其他 collected tests 看到原始值）
5. **避免永久污染** `sys.modules`；如果必须清理，使用
   `del sys.modules[name]` 加 `try/finally`
6. **避免在 import time 改 active module 顶层属性**；若必须，只在 main guard
   下做
7. **避免测试之间共享 mutable global**（fake_* 函数本身无状态，OK；但
   "重新指向" 的 attribute 是 mutable global）
8. 修复后必须跑 **focused + full pytest**：focused 含上述 5 个 boundary test
   文件 + `tests/test_app_analysis_context.py`；full pytest 必须仍 3252 / 0 failed
9. 不允许借实施 fixture cleanup 之机：
   - 改 active business code
   - 改其他测试的断言
   - 删 / 移 negative-import tests 中的 `forbidden_modules` 字符串
   - 修改 `tasks/record_*` 历史引用

---

## 8. 推荐实施方案

> 三个方案对比；推荐 **Option A（保守 / 最小修复）** 作为 14F 实施起点。

### 8.1 Option A — 最小修复（**推荐**）

**做法**：

- 把 fixture 顶层的 9 个 `<module>.<attr> = <fake>` rebind + `runpy.run_path`
  整体包进一段 try/finally：

  ```python
  _ORIGINALS = {
      ("matcher", "load_coded_avgo"): matcher.load_coded_avgo,
      ("matcher", "build_next_day_match_table"): matcher.build_next_day_match_table,
      ("matcher", "build_near_match_table"): matcher.build_near_match_table,
      ("matcher", "save_match_results"): matcher.save_match_results,
      ("matcher", "save_near_match_results"): matcher.save_near_match_results,
      ("stats_reporter", "build_stats_summary"): stats_reporter.build_stats_summary,
      ("stats_reporter", "save_stats_summary"): stats_reporter.save_stats_summary,
      ("scanner", "run_scan"): scanner.run_scan,
      ("predict", "run_predict"): predict.run_predict,
  }
  matcher.load_coded_avgo = fake_coded_df
  # … 余 8 行 rebind 不变 …
  predict.run_predict = fake_predict
  try:
      runpy.run_path(str(ROOT / "app.py"), run_name="__main__")
  finally:
      for (mod_name, attr_name), original in _ORIGINALS.items():
          mod_obj = sys.modules.get(mod_name)
          if mod_obj is not None:
              setattr(mod_obj, attr_name, original)
  ```

- **不**改 fixture 的 `from-import` 时机；**不**清 `sys.modules` 中的
  `ui.*` / `services.*` 缓存（这部分污染由分布式 `_fresh_predict_module`
  防御已经足够）

**优点**：

- 改动**只**在 fixture 内部；零 active code / 测试修改
- restore 保证后续测试读 `predict.run_predict` 时回到原始函数（虽然
  `ui.predict_tab.run_predict` 别名仍捕获 fake，但**没有 boundary test 读
  那个别名**——boundary test 都直接读 `predict.run_predict`）
- 对 5 个 boundary test 的 `_fresh_predict_module` 防御**保持无害**：reload
  仍然能正常工作；如果未来想精简 reload 助手，可在另一 commit 单独评估
- 与 11H §6 commit-per-fix 一致；blast radius 极小

**缺点**：

- 没有完全消除污染（`from X import Y` 别名级别仍然指向 fake；只是
  `predict.run_predict` 自身回到原始）
- `_fresh_predict_module` 防御助手仍需保留（未来 cleanup）

### 8.2 Option B — 新 fixture 替代（折中）

**做法**：

- 新增 `tests/fixtures/app_analysis_context_fixture_v2.py`，使用
  pytest `monkeypatch` 或 `contextlib.ExitStack` 在 setup 阶段
  patch、teardown 阶段 restore
- 旧 fixture 标记为 `_DEPRECATED.md` 风格的 module docstring
- `tests/test_app_analysis_context.py` 切到 v2
- 5 个 boundary test 的 `_fresh_predict_module` 防御暂保留

**优点**：

- 留下 v1 作为历史参考；v2 干净
- 修改**仅**新增文件 + 切换 1 处 `FIXTURE` 路径

**缺点**：

- repo 仓库面积扩大；多了 1 个 fixture 文件
- AppTest.from_file 的语义要求脚本顶层执行流程 — pytest `monkeypatch` fixture
  无法直接注入到 AppTest spawned script；可能需要把 patch 放在 v2 fixture
  顶层用 `contextlib.contextmanager`，本质仍是 try/finally 包装
- 复杂度比 Option A 高，但 hygiene 收益不显著

### 8.3 Option C — 删除 fixture

**做法**：

- 直接 `git rm tests/fixtures/app_analysis_context_fixture.py`
- 同步删除 `tests/test_app_analysis_context.py`（唯一 active consumer）
- 5 个 boundary test 的 `_fresh_predict_module` 防御保留（仍属正确习惯）

**优点**：

- 完全消除污染源

**缺点**：

- 失去 `app.py` Streamlit-level 集成测试覆盖（`test_app_analysis_context.py`
  是唯一 AppTest.from_file 风格的 app 行为测试）
- 删除 active test 通常**违反** "cleanup 不删测试" 原则（14A §12）
- 14E 范畴**不**推荐；只在用户**显式**确认 AppTest 集成测试可放弃时考虑

### 8.4 推荐

> **Option A（最小修复）**

理由：

1. 修复**仅**在 fixture 内部；零 active code / 测试改动
2. 与 14D quarantine 同样的"保守 / 单 commit / 可回滚"模式一致
3. restore `predict.run_predict` 已经覆盖了**所有 boundary test 的实际读取
   面**（boundary test 读 `predict.run_predict`，不读 `ui.predict_tab.run_predict`）
4. 残余污染（`from X import Y` 别名）由分布式 `_fresh_predict_module` 防御
   已经处理；如果未来要进一步精简，可以**单独**做一个 `chore(cleanup):
   simplify _fresh_predict_module helpers` commit，但**不**在 14F 范畴
5. 满足 11H §11 / 14A §11 的 "每个 cleanup commit 必须可回滚" — try/finally
   block 单个 git revert 即可

---

## 9. 不允许事项

未来实施 fixture cleanup（14F+）**绝对**不允许：

1. ❌ 为了修 fixture 改业务代码（`predict.py` / `scanner.py` / `matcher.py` /
   `stats_reporter.py` / 任意 `services/*` / `ui/*`）
2. ❌ 删除测试（任意 `tests/test_*.py`）
3. ❌ 跳过测试（`@pytest.skip` / `@unittest.skip`）
4. ❌ 改 contract 行为（`PredictResult` schema / final_decision 输出 / 等）
5. ❌ 默认迁移 `run_predict` 到 V2
6. ❌ 进入 3R-5 / 3R-6
7. ❌ 把 cleanup 和功能改动混在一个 commit
8. ❌ 改 9 个 negative-import 测试的 `forbidden_modules` 字符串（保留为永久防御）
9. ❌ 改 `tasks/record_*` 历史引用
10. ❌ 改 5 个 boundary test 的 `_fresh_predict_module` 助手（**14F 实施 Option
    A 时不动**；如想精简留待独立后续 commit）
11. ❌ 把 fixture 的 9 个 `fake_*` 函数功能改了 / 删了（保持纯函数 stub
    的可读性 / 行为；只改污染机制）
12. ❌ 借机引入 candidate / 启用 promotion / 复活 continuous_smoothing /
    接 trading
13. ❌ 在 14F commit 内顺手处理 logs / DB backup / `.claude/worktrees/` /
    stash / 任何 §9 untracked artifact

---

## 10. 推荐下一步

**推荐**：

- **Step 14F — test fixture hygiene implementation**（前提：用户**显式**同意
  Option A 推荐方案）
- 实施 commit 命名建议：
  `chore(cleanup): scope app_analysis_context_fixture monkeypatch with try/finally restore`
  或 `chore(cleanup): restore active module attrs after AppTest fixture runs`
- 实施前 / 后必跑：
  - `git status` clean
  - `pytest tests/test_app_analysis_context.py tests/test_predict_legacy_wrapper_boundary.py tests/test_predict_x2_confidence_wiring_boundary.py tests/test_predict_x3_summary_wiring_boundary.py tests/test_predict_legacy_v2_bridge.py tests/test_predict_x4b_v2_payload_opt_in_boundary.py -q` → 0 failed
  - `pytest -q` → 3252 / 0 failed
  - `bash scripts/check.sh` → PASS
- 失败处理：立即 `git revert <14F commit>`；不 amend、不 rebase

**也可以选择**（如果用户判断 fixture hygiene 风险较低）：

- 跳到 **Step 14G — legacy V1 orchestrator audit**（即 14A §10.3 中的
  `services/projection_orchestrator.py` audit），暂时保留分布式
  `_fresh_predict_module` 防御现状

**不**推荐：

- 直接进 Option B / Option C（前者复杂度高收益低；后者删测试违反 14A §12）
- 跳过 14F 直接进 3R-5 / 3R-6
- 在 14F commit 内同时处理 fixture + boundary test 防御助手

---

## 11. 严守边界

本轮**只写 plan 文档**：

- 未改业务代码（`predict.py` / `services/predict_legacy_*` / 全部 active 文件
  byte-identical 与 main `3b0d470`）
- 未改测试（`tests/test_*.py` 全部 byte-identical）
- 未改 fixture（`tests/fixtures/app_analysis_context_fixture.py` byte-identical）
- 未删除文件 / 未移动文件
- 未写 DB / 未改 DB schema
- 未跑 replay / real validation
- 未跑 full pytest（14D baseline 仍当前有效；本计划不改代码）
- 未处理 untracked / DB backup / stash / `.claude/worktrees/`
- 未默认迁移 `run_predict` 到 V2
- 未启动真正 fixture cleanup
- 未进入 3R-5 / 3R-6
- 未启用 candidate / 未复活 `continuous_smoothing` / 未接 trading
- 未顺手碰 RISK-1 / RISK-2 / RISK-3 / RISK-7 / RISK-8 / RISK-9 / RISK-10

本计划的修改路径：任何对 §3 fixture 概览、§4 风险审计、§5 使用方清单、
§7 / §8 修复原则与方案对比、§9 / §10 / §11 决策的调整，都必须以**显式更新
本文件**的方式提出；同时检查是否需要同步更新 14A / 14B / 11H / 12E-X5 / 13。
