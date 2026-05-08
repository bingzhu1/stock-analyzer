# 14A记录：Cleanup / Quarantine Plan

> 本记录是 **Step 14 cleanup / quarantine 的计划阶段**：Step 12 boundary fixes
> + Step 13 regression 入 main 之后的统一 cleanup 计划。
>
> 本轮**只写计划文档**：未改代码、未删除文件、未移动文件、未新增测试、
> 未清理 logs、未处理 DB backup、未处理 `.claude/worktrees/`、未处理 stash、
> 未跑 replay / validation、未写 DB、未改 DB schema、未默认迁移 `run_predict`
> 到 V2、未启动真正 cleanup、未 commit / push、未进入 3R-5 / 3R-6、未顺手碰
> 任何 RISK。

---

## 1. Step 14A 目的

Step 14A 是 **cleanup / quarantine 的计划阶段**：

- **不**实际删除 / 移动任何文件
- **不**修改任何代码
- **不**新增 / 修改测试
- **不**处理 untracked 本地 artifact（logs / DB backup / `.claude/worktrees/` 等）

目的：

1. 为后续 Step **14B / 14C / 14D / 14E / 14F / 14G** 的小步 cleanup commit
   提供 file-by-file 的清单 / 顺序 / 边界 / 回滚方案
2. 锁定 `KEEP_ACTIVE` / `KEEP_FROZEN_DIAGNOSTIC` 不变量（任何 cleanup 都不
   允许触碰这两类）
3. 为 `QUARANTINE_CANDIDATE` 设定**进入 cleanup 前必须做的 audit**（先
   audit、再决定 quarantine 或 delete）
4. 明确 `DO_NOT_TOUCH_LOCAL_ARTIFACT` 必须由用户单独确认

签收依据：[tasks/record_13_post_fix_regression_boundary_review.md](tasks/record_13_post_fix_regression_boundary_review.md)
§8 已签收 "YES — allowed to plan Step 14 cleanup / quarantine."。

---

## 2. 当前前置条件

| 项 | 状态 |
|---|---|
| Step 12 boundary fixes（11A–G + 11E X1–X5）全部入 main | ✅ |
| Step 13 regression 入 main（main HEAD = `cdfc973`） | ✅ |
| focused boundary tests（265）通过 | ✅ |
| predict-related tests（156 + 39 subtests）通过 | ✅ |
| full pytest（3252 / 10 skipped / 0 failed）通过 | ✅ |
| `scripts/check.sh` 通过 | ✅ |
| active path boundary review 通过 | ✅ |
| Step 13 §8 允许进入 cleanup planning | ✅ |
| 直接 cleanup（不写计划） | ❌ 显式禁止 |
| 默认迁移 V2 / 进入 3R-5 / 3R-6 | ❌ 显式禁止 |

---

## 3. cleanup 总原则

> Step 12 commit-per-fix 原则的延续；每条原则都来自 11H §6 / §8 / §11。

1. **先计划，后执行**：Step 14A 写计划 → 14B–14G 才执行
2. **一类文件一个 commit**：root v1 stubs、test fixture hygiene、legacy
   orchestrator、local artifact 等**分开**commit
3. **每个 cleanup commit 必须可回滚**：使用 `git revert` 即可恢复
4. **不**混 boundary fix / cleanup / validation / 功能变化（11H §6.2 / §8）
5. **不**碰 DB schema
6. **不**碰 active path（11H §10 / §10.1）
7. **不**处理不确定归属文件（先 audit 再决定）
8. **不**删除仍有 import / reference 的文件
9. **不**删除 frozen diagnostic baseline（11H §9 / 12E-X5 §11.9）
10. **不**处理用户未确认的本地 artifact（logs / DB backup / stash /
    `.claude/worktrees/`）
11. cleanup commit 完成后**必须**跑 focused + full pytest，0 failed 才入 main
12. 每个 cleanup commit **不**允许借机引入 candidate / 启用 promotion /
    复活 continuous_smoothing / 接 trading

---

## 4. 文件分类标准

定义 **5 类**，每个文件必须落到唯一一类：

| 类 | 含义 | 本轮处理 |
|---|---|---|
| **KEEP_ACTIVE** | 当前 active path 必须保留；删除会破坏功能 | ❌ 不动 |
| **KEEP_FROZEN_DIAGNOSTIC** | 已冻结但作为 baseline / 文档 / 诊断保留 | ❌ 不动 |
| **QUARANTINE_CANDIDATE** | 可能不用，但暂不删除；后续可移动到 archive / legacy | ⏳ 14B+ 先 audit |
| **DELETE_CANDIDATE** | 明确无引用、无价值、可删除；必须二次确认 | ⏳ 14B+ 先 audit |
| **DO_NOT_TOUCH_LOCAL_ARTIFACT** | 本地未 tracked 产物（logs / DB backup / `.claude/worktrees/`），不能直接 commit 处理 | ❌ 必须用户单独确认 |

> 重要：**未列入** 5 类的任何文件**默认**视为 KEEP_ACTIVE，cleanup 必须**显式**
> 把它列入下面四类之一才允许碰。

---

## 5. KEEP_ACTIVE 清单

> 这些文件**绝不**在 Step 14 初期删除或移动。

### 5.1 顶层入口

- `app.py`
- `predict.py`（legacy compatibility wrapper；仍被 9+ active importer 依赖；
  Step 12E-X5 已锁定）
- `agent_loop.py`（标记为 untracked，但 main 工作树里 untracked；不
  在本 worktree 范围；归 §9 处理）

### 5.2 UI 层（全部 9 个）

- `ui/predict_tab.py` / `ui/home_tab.py` / `ui/history_tab.py` /
  `ui/scan_tab.py` / `ui/research_tab.py` / `ui/review_tab.py` /
  `ui/inspect_tab.py` / `ui/command_bar.py` / `ui/control_tab.py`
- 以及 ui 渲染 helper：`ui/projection_v2_renderer.py` /
  `ui/big_up_contradiction_card.py` / `ui/exclusion_reliability_review.py` /
  `ui/anti_false_exclusion_display.py` /
  `ui/protection_layer_diagnostics_renderer.py` /
  `ui/soft_metadata_baseline_cache.py` / `ui/soft_metadata_renderer.py` /
  `ui/labels.py`

### 5.3 services 核心

- `services/projection_orchestrator_v2.py`（active V2 入口）
- `services/main_projection_layer.py`
- `services/exclusion_layer.py`
- `services/confidence_evaluator.py`（11C-A）
- `services/final_decision.py`（11B 修复后纯 aggregator）
- `services/projection_three_systems_renderer.py`
- `services/cutoff_guard.py`（11D）
- `services/predict_legacy_adapter.py`（11E-X4-A）
- `services/predict_legacy_v2_bridge.py`（11E-X4-C）
- `services/home_terminal_orchestrator.py`
- `services/contract_replay_writer.py`（offline replay；user 显式禁止本轮触碰）
- `services/ai_summary.py`（11F；默认 disabled）
- `services/log_store.py` / `services/prediction_store.py`（infra）
- `services/outcome_capture.py` / `services/review_*.py` / `services/memory_feedback.py` /
  `services/projection_memory_briefing.py` / `services/pre_prediction_briefing.py` /
  `services/projection_rule_preflight.py` / `services/review_analyzer.py` /
  `services/projection_orchestrator_preflight.py` / `services/projection_preflight.py`

### 5.4 data / feature / scanner / matcher / encoder

- `data_fetcher.py` / `feature_builder.py` / `scanner.py` / `matcher.py` /
  `encoder.py` / `stats_reporter.py`
- 配套的 services：`services/historical_probability.py` / `services/peer_adjustment.py` /
  `services/projection_chain_contract.py` / `services/projection_output_contract.py` /
  `services/features_*.py` / `services/encoder_*.py`（如存在）

### 5.5 promotion / 4-状态 / 安全相关（保留为 OFFLINE_ONLY）

- `services/active_rule_pool_promotion.py` / `services/promotion_adoption_gate.py` /
  `services/promotion_execution_bridge.py`（11G doc-locked，**不**删，**不**改 logic）

### 5.6 tests

- 全部 11A–11G + 12E X1–X4-C 的 boundary contract test 文件
- 全部 `tests/test_predict.py` / `tests/test_run_predict_contract_alignment.py` /
  `tests/test_*_contract_fields.py`
- 全部 `tests/test_main_projection_layer.py` / `tests/test_final_decision.py` /
  `tests/test_confidence_evaluator.py` / `tests/test_cutoff_guard.py` /
  `tests/test_ai_summary*.py` / `tests/test_promotion_*.py`
- 全部 `tests/test_projection_orchestrator_v2.py` 等 V2 path 测试
- 全部 ui 相关 apptest（如 `tests/test_command_bar_apptest.py`）

### 5.7 contract / design 文档

- `tasks/record_06_*.md` / `tasks/record_07{a,b,c,d,e}_*.md` /
  `tasks/record_08_*.md` / `tasks/record_09_*.md` / `tasks/record_10_*.md` /
  `tasks/record_11{a..h}_*.md` / `tasks/record_12e_x5_*.md` /
  `tasks/record_13_*.md`
- 本计划文档 `tasks/record_14a_cleanup_quarantine_plan.md`

### 5.8 项目根 infra

- `.claude/CLAUDE.md` / `.claude/PROJECT_STATUS.md` / `.claude/CHECKLIST.md`
- `tasks/STATUS.md`
- `scripts/check.sh`（compile gate；20 个核心模块）
- `scripts/run_e2e_loop.py`（live e2e；不传 v2_payload，符合 X4-C 边界）
- `requirements*.txt` / `pyproject.toml` / `pytest.ini` / `conftest.py`（如存在）

> KEEP_ACTIVE 的精确边界：任何 Step 14 commit 如果触碰本节列出的文件，必须先在
> 该 commit 的设计文档里**显式更新本计划**，否则 commit 无效。

---

## 6. KEEP_FROZEN_DIAGNOSTIC 清单

> 这些**不** active，但作为失败案例 / baseline / 审计证据保留。**默认永久保留**。

### 6.1 continuous_smoothing v1/v2

| path | role |
|---|---|
| `services/continuous_smoothing_candidate.py` | v1 frozen candidate；不 active |
| `services/continuous_smoothing_candidate_v2.py` | v2 frozen candidate；不 active |
| `tests/test_continuous_smoothing_candidate.py` | v1 test（pin 失败案例） |
| `tests/test_continuous_smoothing_candidate_v2.py` | v2 test（pin 失败案例） |
| `scripts/run_continuous_smoothing_validation.py` | v1 validation script |
| `scripts/run_continuous_smoothing_validation_v2.py` | v2 validation script |
| `scripts/run_real_continuous_smoothing_validation.py` | real-data v1 |
| `scripts/run_real_continuous_smoothing_validation_execute.py` | real-data v1 execute |
| `scripts/run_real_continuous_smoothing_validation_execute_v2.py` | real-data v2 execute |

依据：[tasks/record_10_keep_freeze_quarantine_cleanup_plan.md](tasks/record_10_keep_freeze_quarantine_cleanup_plan.md)
§7 / 11H §9 / 12E-X5 §11.9。Step 13 §5 静态扫描确认这些**未**被任何 active path
import；保留只为审计与教训。

### 6.2 3R-3 / 3R-3.3 系列 checkpoint 文档

- `tasks/step_3r3_*.md` 系列（continuous_smoothing 复盘 checkpoint）
- `tasks/step_3r4_*.md` 系列（regime validation 复盘）
- `tasks/step_3r0_*.md` / `tasks/step_3r1_*.md` / `tasks/step_3r2_*.md`

### 6.3 12E / 13 文档与测试

- `tasks/record_11e_*.md` / `tasks/record_12e_x5_*.md` / `tasks/record_13_*.md`
- `tests/test_predict_legacy_wrapper_boundary.py` /
  `tests/test_predict_x{2,3}_*_boundary.py` /
  `tests/test_predict_legacy_adapter.py` /
  `tests/test_predict_x4b_*_boundary.py` / `tests/test_predict_legacy_v2_bridge.py`

### 6.4 logs/regime_validation 中 v1/v2 raw output（**本地** untracked）

- 见 §9 — 这些是本地 untracked 产物；属 `DO_NOT_TOUCH_LOCAL_ARTIFACT`；不允许
  commit 也不允许删除（除非用户单独确认）

### 6.5 严约束

- **不**允许复活 `continuous_smoothing*` 调用路径
- **不**允许把 §6 文件移到 `archive/` / `legacy/`（位置改变会破坏审计追溯）
- **不**允许在 §6 文件内"借机修小问题"（这些是 frozen baseline）

---

## 7. QUARANTINE_CANDIDATE 清单

> 可能未来隔离，但**进入 quarantine 前必须先 audit**。Step 14B / 14C / 14D /
> 14E 才执行；本轮只列。

### 7.1 root-level 死 stub（确认无 import；候选首批 audit）

| path | reason | current evidence | required check before quarantine | suggested action |
|---|---|---|---|---|
| `confidence_engine.py`（31 行 / 608 字节） | v1 dead stub；11C-A 已建立 `services/confidence_evaluator.py`（独立 owner） | `grep -rn '^from confidence_engine\|^import confidence_engine'` 在所有 `*.py` 中**零结果** | (a) 验证 main HEAD 此结果一致；(b) 跑 full pytest 确认无 hidden import；(c) 确认 `tasks/` / `scripts/` 中无引用 | 14B audit → 14C 决定 quarantine（移到 `archive/legacy/`）或 delete |
| `contradiction_engine.py`（~30 行 / 643 字节） | v1 dead stub；contradiction 逻辑已下沉到 confidence / final_decision | 同上：零 import | 同上 | 同上 |
| `risk_model.py`（~30 行 / 569 字节） | v1 dead stub；risk_level 已迁移到 `final_decision.risk_level` / `confidence_result` | 同上：零 import | 同上 | 同上 |

> 注意：根据 11H §11 / 12E-X5 §11.7，这三项归 Step 14 cleanup；先 audit、后
> 决定。**不**在 14A 决定 delete 还是 move。

### 7.2 旧 V1 orchestrator（仅 V2 / tests 内部 import）

> ⚠ **14G CORRECTION (supersedes the original 14A tentative classification
> for `services/projection_orchestrator.py`).**
>
> [Step 14G audit](tasks/record_14g_legacy_v1_orchestrator_audit.md) 完成
> 后已确认：[`services/projection_orchestrator_v2.py:16`](services/projection_orchestrator_v2.py:16)
> 在**模块顶层** `from services.projection_orchestrator import build_projection_orchestrator_result`，
> 并把它当作 `run_projection_v2` 的**默认** `_projection_runner`
> ([line 413](services/projection_orchestrator_v2.py:413), 在 [line 450](services/projection_orchestrator_v2.py:450)
> 实际调用)。本 14A §7.2 原文的"仅由 `tests/test_projection_orchestrator.py`
> 显式 import"判断**已过期**——V2 在生产路径上调用 V1，V1 是 active code，
> 不再是 quarantine candidate。下表已按 14G 结论更新；任何与
> "thin shim / archive / delete" 相关的 14A 措辞均**作废**，以本更正为准。

| path | status (post-14G) | reason | current evidence | suggested action |
|---|---|---|---|---|
| `services/projection_orchestrator.py` | **KEEP_ACTIVE** after Step 14G audit | imported by [`services/projection_orchestrator_v2.py:16`](services/projection_orchestrator_v2.py:16) at module top level and used as the default `_projection_runner` for `run_projection_v2`; 4 active V2 callers (`projection_entrypoint` / `historical_replay_training` / `projection_v2_adapter` / `predict.py` lazy import) all rely on this default; `predict.py` docstring + re-entry guard ([predict.py:1315](predict.py:1315), [predict.py:1330-1336](predict.py:1330-1336)) presume V1 stays on the active path | `rg "^\s*from services\.projection_orchestrator import"` 真实命中 = 2 行：V2（active code）+ `tests/test_projection_orchestrator.py`（test）；其余 6 处全部为 docstring / `forbidden_modules` 字符串；`pytest tests/test_projection_orchestrator.py -q` = 5 passed；full pytest = 3256 passed / 0 failed | **do not quarantine / do not delete / do not move / do not thin-shim**。保留 V1 byte-identical；如未来要简化 V2 → V1 调用链（V2 内联 V1），属架构改动，**不**在 14 系列 cleanup 范围 |

### 7.3 test fixture monkeypatch hygiene

| path | reason | current evidence | required check before quarantine | suggested action |
|---|---|---|---|---|
| `tests/fixtures/app_analysis_context_fixture.py` | 永久 rebind `predict.run_predict` 不 restore；导致 12E boundary tests 必须用 `_fresh_predict_module()` 防御 | 12E-X1/X2/X3/X4-B/X4-C 各 boundary test 文件 docstring 都记录了此 hygiene issue | 14E 步骤：(a) 找到 fixture 调用方；(b) 评估改为 context manager 或 `monkeypatch.setattr` 模式（不影响 fixture 用法）；(c) 确认改造后 12E boundary tests 仍然全绿 | 14E 写 hygiene plan（仍**只**是计划）→ 后续小 commit 修；不允许在 14A 直接改 |

### 7.4 .claude/legacy_tasks/

| path | reason | current evidence | required check before quarantine | suggested action |
|---|---|---|---|---|
| `.claude/legacy_tasks/`（目录） | 历史 task 归档；当前 worktree **不存在**该目录（`find .claude -maxdepth 2 -type d -name legacy_tasks` → 空） | 不存在 | 14B audit：在 main 工作树确认是否存在；若不存在则 §7.4 整条移除 | 仅在确实存在时考虑压缩 / 归并 |

### 7.5 records/ 与 tasks/ 是否归并

| path | reason | current evidence | required check before quarantine | suggested action |
|---|---|---|---|---|
| `records/`（目录） | 与 `tasks/` 体系疑似重复；记录历史 record 文件 | `ls -d records tasks` 显示**两个**目录都存在 | 14B audit：(a) 列 `records/` 内每个文件归属（contract / 历史 record / 临时）；(b) 比对 `tasks/record_*.md` 是否同名重复；(c) 决策：归并 / 保留 / archive | 仅在 audit 完整后决定；不在 14A 动 |

### 7.6 旧 handoff（**本地** untracked）

`.claude/handoffs/task_089_post_pr_cleanup.md` — 在 main 工作树 untracked；
归 §9 `DO_NOT_TOUCH_LOCAL_ARTIFACT`，本节**不**列。

---

## 8. DELETE_CANDIDATE 清单

> **NO_DIRECT_DELETE_CANDIDATE_YET.**

理由：

- §7 中所有候选都需要先 audit
- 11H §6.2 / §8 禁止"借 cleanup 之机偷偷删除"
- 12E-X5 §11 列出的 14 项债务**全部**应先经 quarantine 或 audit，再决定 delete
- 用户在本 14A 任务边界中**显式**写："建议：先不要列 active repo tracked
  文件为 delete。删除必须晚于 quarantine。"

> Step 14B / 14C / 14D 中每完成一项 audit 后，**才**允许把对应文件从
> QUARANTINE_CANDIDATE 移到 DELETE_CANDIDATE，且**必须**在那一阶段的 commit
> 设计文档里**显式**记录依据。

---

## 9. DO_NOT_TOUCH_LOCAL_ARTIFACT 清单

> 当前 worktree (`claude/optimistic-gauss-b20a8e`) git status 唯一未 tracked
> 文件：`logs/prediction_log.jsonl`。
>
> main 工作树 (`/Users/may/Desktop/stock-analyzer-main`) git status 显示的
> 全部 untracked artifacts（继承自 hard rules / 11H §9）：

| path | type | 处理方式 |
|---|---|---|
| `logs/prediction_log.jsonl` | live runtime artifact | ⛔ 不 add、不 commit、不 delete；live 数据，需用户单独确认 |
| `logs/regime_validation/` | v1/v2 validation raw output（FROZEN_DIAGNOSTIC 范畴） | ⛔ 不 add、不 commit、不 delete；归档需用户决定 retention policy |
| `logs/historical_training/three_system_1005/` | training raw output | ⛔ 不动 |
| `logs/historical_training/three_system_w4_2024_08_2025_12/` | training raw output | ⛔ 不动 |
| `logs/historical_training/three_system_w4_smoke_2024_08_05_2024_08_09/` | training smoke output | ⛔ 不动 |
| `avgo_agent.db.backup_pre_2099_hygiene_20260503_160409` | DB backup | ⛔ 不动；retention policy 需用户决定 |
| `avgo_agent.db.backup_pre_3a3_20260504_013453` | DB backup | ⛔ 不动 |
| `avgo_agent.db.backup_pre_3a4_20260504_023331` | DB backup | ⛔ 不动 |
| `avgo_agent.db.backup_pre_4c3_rewrite_20260503_235604` | DB backup | ⛔ 不动 |
| `avgo_agent.db.backup_pre_replay_130_20260504_003707` | DB backup | ⛔ 不动 |
| `avgo_agent.db.backup_pre_replay_30_20260503_162636` | DB backup | ⛔ 不动 |
| `avgo_agent.db.backup_step_2c_2_6` | DB backup | ⛔ 不动 |
| `.claude/worktrees/` | per hard rules 不主动处理；worktree 生命周期自然清理 | ⛔ 不动 |
| `.claude/handoffs/task_089_post_pr_cleanup.md` | 历史 handoff | ⛔ 不动；归 14F 用户确认 |
| `agent_loop.py` | main 工作树 untracked；归属待用户确认（保留 / archive / cleanup） | ⛔ 不动；归 14F 用户确认 |

### 9.1 处理原则

- **不**在 Step 14 任何 commit 里 `git add` 这些文件
- **不**在 Step 14 任何 commit 里删除这些文件
- 如需处理，**必须**有用户单独 issue / instruction 明确允许，且每项**独立 commit**

---

## 10. cleanup 执行顺序建议

> 每项**独立 commit**；commit 之间**不**混合；commit message 必须含 cleanup
> 类型。每个 commit 之前 / 之后跑 focused + full pytest。

### 10.1 Step 14B — tracked dead root stubs audit（仅 audit）

- **范围**：`confidence_engine.py` / `contradiction_engine.py` / `risk_model.py`
- **动作**：跑 grep + AST 检查，**不**删除、**不**移动
- **产出**：新增 `tasks/record_14b_root_dead_stubs_audit.md`
- **commit message**：`docs(cleanup): record 14b root dead stubs audit`

### 10.2 Step 14C — root dead stubs quarantine 或 delete 决策

- **前置**：14B audit 通过
- **范围**：14B 中确认无引用的 root stub
- **动作**：移到 `archive/legacy/` 或 delete（**择一**，每项独立 commit）
- **commit message**：`cleanup: archive root v1 dead stub <name>` 或
  `cleanup: delete root v1 dead stub <name>`

### 10.3 Step 14D — legacy V1 orchestrator audit + 决策

> ⚠ **Superseded by Step 14G (commit `6d2a87e`).** 实际编号路径：root dead
> stubs audit → 14B；root stubs delete decision → 14C；root v1 stubs
> quarantine → 14D；test fixture hygiene plan → 14E；test fixture hygiene
> implementation → 14F；**legacy V1 orchestrator audit → 14G**（原计划
> 此 §10.3 中的 "Step 14D"）。14G 结论 = `KEEP_ACTIVE`；本 §10.3 中
> "保留 thin shim、archive 或 delete" 的三选项**全部作废**——不 archive、
> 不 delete、不 thin-shim，详见 §7.2 14G CORRECTION 与
> [tasks/record_14g_legacy_v1_orchestrator_audit.md](tasks/record_14g_legacy_v1_orchestrator_audit.md) §7.3 / §8。

- **前置**：14C 完成
- **范围**：`services/projection_orchestrator.py` + `tests/test_projection_orchestrator.py`
- **动作**：(a) audit V2 path 是否仍走此入口；(b) 决定保留 thin shim、archive
  或 delete
- **产出**：新增 `tasks/record_14d_legacy_v1_orchestrator_audit.md`
- **commit message**：`docs(cleanup): record 14d legacy v1 orchestrator audit`，
  实际处理在后续 commit

### 10.4 Step 14E — test fixture hygiene plan

- **前置**：14D 完成
- **范围**：`tests/fixtures/app_analysis_context_fixture.py` 永久 monkeypatch
- **动作**：(a) 写 hygiene plan（**仅**是计划）；(b) 评估改造方式；(c) 后续
  小 commit 修；改造后跑 12E boundary tests 全绿确认
- **产出**：新增 `tasks/record_14e_test_fixture_hygiene_plan.md`
- **commit message**：`docs(cleanup): record 14e test fixture hygiene plan`

### 10.5 Step 14F — local artifact handling plan（**用户确认**驱动）

- **前置**：14E 完成
- **范围**：§9 全部 untracked artifact（logs / DB backup / handoff /
  `.claude/worktrees/` / `agent_loop.py`）
- **动作**：写 retention policy；**不**实际处理；**等待用户单独确认**
- **产出**：新增 `tasks/record_14f_local_artifact_handling_plan.md`
- **commit message**：`docs(cleanup): record 14f local artifact handling plan`

### 10.6 Step 14G — optional cleanup commits（按需）

- **前置**：14B / 14C / 14D / 14E 全部计划与决策完成
- **范围**：14C / 14D / 14E 中真正需要执行的 cleanup
- **动作**：每类**独立 commit**；每个 commit 前后跑 focused + full pytest
- **commit message**：`cleanup: <具体类型>`（每个 commit 单独 message）

### 10.7 顺序总览

```
14A (本计划) → 14B audit → 14C root stubs → 14D legacy orchestrator audit →
14E fixture hygiene plan → 14F local artifact plan → 14G 实际 cleanup commits
```

每步**独立 commit**；不混合；不并行。任何步骤失败，立即 `git revert`，下一步
不进入。

---

## 11. 每个 cleanup commit 的最低要求

每个 14B–14G commit **必须**满足：

1. **commit 前**：
   - `git status` clean（除 §9 standing untracked）
   - 待清理项的 import / reference grep 全部抓取并 attach 到设计文档
   - focused tests 全绿（与本 commit 范畴相关的 boundary / contract test）
   - full pytest baseline 全绿
2. **commit 后**：
   - focused tests 仍全绿
   - full pytest 仍全绿（passed 数量**只**允许减少与被删测试一致；不允许任何
     失败）
   - 触发的 import error / runtime error 必须导致 commit 立即 revert
3. **commit 内容**：
   - **不**混入代码重构（即使发现 typo 也另 commit）
   - **不**混入功能变化
   - **不**混入 DB schema / log / raw output 改动
   - **不**混入 boundary fix（已经 Step 12 完成）
4. **commit message**：
   - `cleanup: <action> <target>`（动作 + 目标），例如
     `cleanup: archive root v1 dead stub confidence_engine`
   - 或 `docs(cleanup): record 14<X> <plan/audit name>`
5. **失败处理**：
   - 任一测试 / hook / compile 失败 → `git revert <commit>`；不 amend、不
     `rebase -i`
   - 失败原因记入下一阶段的 audit doc

---

## 12. 禁止事项

Step 14 期间**绝对禁止**：

- ❌ 删除 active path（§5 全部）
- ❌ 删除 `predict.py`（仍是 legacy compatibility wrapper；9+ active importer 依赖）
- ❌ 删除 Step 12 boundary tests（任一 11A–11G + 11E X1–X4-C 测试文件）
- ❌ 删除 06–13 contract docs / sign-off / regression report
- ❌ 删除 `continuous_smoothing*` baseline（永久保留为 frozen diagnostic）
- ❌ 处理 DB backup（retention policy 由用户决定）
- ❌ 处理 `logs/regime_validation/` 内的 v1/v2 raw output
- ❌ 处理 `.claude/worktrees/`
- ❌ 处理 stash
- ❌ 默认迁移 `run_predict` 到 V2（不在 Step 14 范畴；属架构级 launch review）
- ❌ 启动 promotion_execution_bridge / 启用 candidate / 接 trading
- ❌ 引入 hard / forced / required 字段
- ❌ 启用 production_promotion
- ❌ 进入 3R-5 / 3R-6
- ❌ `git commit --amend` / `git rebase -i` 已 push 的 14 系列 commit
- ❌ 一个 commit 修多个 cleanup 类
- ❌ cleanup 与 boundary fix 混 commit
- ❌ cleanup 与 DB schema 改动混 commit

---

## 13. 是否允许真正 cleanup

> **NO**，Step 14A 本轮**只**允许写计划。
>
> 真正 cleanup 必须从 **Step 14B audit** 开始，且按 §10 顺序逐步执行。

---

## 14. 是否允许进入 3R-5 / 3R-6

> **NO.**

理由（按 11H §12 严格前置条件 + 13 §9）：

1. ❌ Step 14 cleanup 尚未执行（仅 14A 计划阶段）
2. ❌ default V2 migration 尚未独立 launch review（仍属架构级切换）
3. ❌ 06 / 07A–D contract 未显式更新 / 新增 candidate
4. ❌ trading / hard / forced / production_promotion 仍**永久禁止**
5. ❌ 进入 3R-5 / 3R-6 必须**另开** launch review 文档（不在 06–14 范畴）

---

## 15. 推荐下一步

> **Step 14B — tracked dead root stubs audit**

具体路径：

1. 新增 `tasks/record_14b_root_dead_stubs_audit.md`，内容：
   - 列 `confidence_engine.py` / `contradiction_engine.py` / `risk_model.py`
     当前每个文件的：
     - 行数 / 字节数 / mtime
     - 是否被 `tasks/*.md` / `scripts/*.py` / `tests/*.py` / `services/*.py` /
       `ui/*.py` / `app.py` 中**任何**地方 import / reference
     - AST 顶层定义（class / def / 常量）
     - 是否有动态 import / `importlib` 引用
   - 每个文件给出 (a) 保留 thin shim、(b) archive、(c) delete 三选一建议
   - 不实际改动
2. **不**改代码、**不**新增测试、**不**删除文件、**不**移动文件
3. commit message：`docs(cleanup): record 14b root dead stubs audit`

**不**推荐：

- 跳过 14B 直接 archive / delete
- 借机 cleanup 其他文件
- 进入 3R-5 / 3R-6
- 默认切 V2

---

## 16. 严守边界

本轮**只写 cleanup / quarantine plan**：

- 未改业务代码（`predict.py` / `services/predict_legacy_*` / 全部 services /
  ui / scripts / tests 文件 byte-identical 与 main `cdfc973`）
- 未新增测试 / 未修改测试
- 未删除文件 / 未移动文件
- 未写 DB / 未改 DB schema
- 未跑 replay / real validation
- 未 add / 未 commit / 未 delete 任何 §9 untracked artifact
- 未默认迁移 `run_predict` 到 V2
- 未启动真正 cleanup
- 未进入 3R-5 / 3R-6
- 未启用 candidate / 未复活 `continuous_smoothing` / 未接 trading
- 未顺手碰 RISK-1 / RISK-2 / RISK-3 / RISK-7 / RISK-8 / RISK-9 / RISK-10

本计划的修改路径：任何对 §3 总原则、§4 分类标准、§5 / §6 锁定清单、§7
quarantine 候选与 audit 步骤、§8 / §9 禁止条款、§10 执行顺序、§11 / §12 / §13
/ §14 / §15 决策的调整，都必须以**显式更新本文件**的方式提出；同时检查是否
需要同步更新 11H / 12E-X5 / 13。
