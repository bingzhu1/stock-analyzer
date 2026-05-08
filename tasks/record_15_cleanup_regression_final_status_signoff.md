# 15记录：Cleanup Regression / Final Status Signoff

> 本记录是 **Step 15：Step 12–14 cleanup 完成后的最终回归 + 状态签收**。
> Step 12 boundary fixes / Step 13 post-fix regression boundary review /
> Step 14A–14M cleanup 全部已合进 main，最近 main commit 为
> `ddf10b7 docs(cleanup): record 14l 14m local artifact follow-up`。
>
> 本轮**只**做回归检查 + 状态文档：未改业务代码、未新增测试、未删除文件、
> 未移动文件、未处理 handoff、未处理 logs / DB backup / `.claude/worktrees/`、
> 未跑 replay / real validation、未写 DB / 未改 DB schema、未默认迁移
> `run_predict` 到 V2、未 commit / push、未进入 3R-5 / 3R-6。

---

## 1. Step 15 目的

Step 12–14 已完成；本轮做最终签收：

1. 跑 full pytest 验证业务回归仍 green
2. 跑 `scripts/check.sh` 验证关键 surface py_compile 仍 clean
3. 跑 focused boundary / cleanup sanity suite 验证 12 / 13 / 14 系列加固的
   contract 仍生效
4. static sanity：root v1 stubs 已 quarantine、root 无 `agent_loop.py`
5. ignore pattern 验证：14K 加入的 6 行 pattern 命中预期文件
6. 写 Step 15 final signoff record

明确**不**做的事：

- 不改业务代码 / 测试 / `.gitignore`
- 不新增测试
- 不删除 / 移动文件
- 不处理 `.claude/handoffs/task_089_post_pr_cleanup.md`（按 14L A2 / 14M 保留 untracked landmark）
- 不处理 logs / DB backup / `.claude/worktrees/`
- 不跑 replay / real validation
- 不写 DB / 不改 DB schema
- 不默认迁移 `run_predict` 到 V2（hard rule 1）
- 不进入 3R-5 / 3R-6
- 不 commit / push（按本轮指令）

签收依据：[record_14m_user_confirmed_local_artifact_handling.md](record_14m_user_confirmed_local_artifact_handling.md) §7（推荐 Step 15）+
[record_14l_handoff_agent_loop_review.md](record_14l_handoff_agent_loop_review.md) §8.4 + [record_14j_local_artifact_handling_plan.md](record_14j_local_artifact_handling_plan.md) §11。

---

## 2. 当前 main 状态

| 项 | 值 |
|---|---|
| main 最新 commit | `ddf10b7 docs(cleanup): record 14l 14m local artifact follow-up` |
| 14 系列完成度 | 14A / 14B / 14C / 14E / 14G / 14H / 14I / 14J / 14K / 14L / 14M 全部已 commit；14D / 14F 是 14C / 14E 的实施动作（已合并） |
| Step 12 boundary fixes | ✅ 已完成；最终见 `record_12e_x5_*_completion_checkpoint.md`（commit 链至 `c125f91 feat(boundary): RISK-8 add isolated v2_payload-to-legacy bridge`） |
| Step 13 regression | ✅ 已完成；见 `record_13_post_fix_regression_boundary_review.md`（commit `cdfc973`） |
| main worktree `git status --short` | **1 项**：`?? .claude/handoffs/task_089_post_pr_cleanup.md`（按 14L/14M Option A2 deliberate keep local） |
| handoff 字节状态 | 2966 B / mtime `2026-04-28 10:34:37`（与 STATUS.md task 092~110 closeout landmark + 14L §3.1 完全一致） |
| 当前 worktree（`eager-blackwell-e5e9de`）已 ff 至 `ddf10b7` | ✅ 是（14M closeout 后 `git pull --ff-only origin main`） |
| `.gitignore` 状态 | 14K commit `66dafd8` 加入的 6 行 pattern 全部生效；14L/14M 未改字节 |

最近 15 个 commit（14 系列 + 13 + 12E 链）：

```
ddf10b7 docs(cleanup): record 14l 14m local artifact follow-up
66dafd8 chore(gitignore): cover local db backups, prediction log, replay raw outputs, claude worktrees
28fcf28 docs(cleanup): record 14j local artifact handling plan
50c60f3 docs(cleanup): record 14i cleanup status checkpoint
e4be95f docs(cleanup): correct 14a v1 orchestrator classification per 14g audit
6d2a87e docs(cleanup): record 14g legacy v1 orchestrator audit
bd4b81b chore(cleanup): scope app_analysis_context_fixture monkeypatch with try/finally restore
df912b8 docs(cleanup): record 14e test fixture hygiene plan
3b0d470 chore(cleanup): quarantine root v1 stubs to archive/legacy/root_stubs
c5dca5f docs(cleanup): record 14c root stubs quarantine delete decision
3808677 docs(cleanup): record 14b root dead stubs audit
afb006b docs(cleanup): record 14a cleanup quarantine plan
cdfc973 docs(contract): record 13 post-fix regression boundary review
3ecf78c docs(contract): record 12e x5 predict legacy wrapper split completion checkpoint
c125f91 feat(boundary): RISK-8 add isolated v2_payload-to-legacy bridge
```

---

## 3. 回归结果

### 3.1 Full pytest

命令：`pytest -q`

```
3256 passed, 10 skipped, 26 warnings, 94 subtests passed in 18.63s
```

| 维度 | 值 |
|---|---|
| passed | **3256** |
| skipped | 10 |
| failed | **0** |
| errors | **0** |
| warnings | 26（均为 `services/ai_*_parser.py` 的 deliberate `_warnings.warn` —— 这些是 boundary 测试在 negative path 上**期望**触发的输入校验告警，不是 regression） |
| subtests passed | 94 |
| baseline 比对（14F / 14I / 14J） | ✅ **byte-identical**（passed/skipped/warnings/subtests 完全一致） |

### 3.2 `scripts/check.sh`

命令：`bash scripts/check.sh`

```
All compile checks passed.
```

py_compile 覆盖的 18 个 surface（`app.py` / `scanner.py` / `predict.py` /
`encoder.py` / `matcher.py` / `feature_builder.py` / `data_fetcher.py` /
`services/predict_summary.py` / `services/prediction_store.py` /
`services/outcome_capture.py` / `services/review_store.py` /
`services/automation_wrapper.py` / `services/tool_router.py` /
`services/intent_planner.py` / `services/ai_intent_parser.py` /
`ui/command_bar.py` / `ui/home_tab.py` / `ui/predict_tab.py`）全部 clean。

### 3.3 Focused boundary / cleanup sanity tests

命令（15 个 suite）：

```
pytest \
  tests/test_projection_exclusion_decoupling_boundary.py \
  tests/test_final_decision_aggregator_purification_boundary.py \
  tests/test_confidence_evaluator.py \
  tests/test_confidence_result_wiring_boundary.py \
  tests/test_cutoff_guard.py \
  tests/test_memory_feedback_cutoff_guard_boundary.py \
  tests/test_ai_summary_boundary.py \
  tests/test_promotion_offline_only_boundary.py \
  tests/test_predict_legacy_wrapper_boundary.py \
  tests/test_predict_x2_confidence_wiring_boundary.py \
  tests/test_predict_x3_summary_wiring_boundary.py \
  tests/test_predict_legacy_adapter.py \
  tests/test_predict_x4b_v2_payload_opt_in_boundary.py \
  tests/test_predict_legacy_v2_bridge.py \
  tests/test_app_analysis_context_fixture_hygiene.py \
  -q
```

结果：**269 passed in 2.12s**。

| 维度 | 值 |
|---|---|
| passed | **269** |
| failed | **0** |
| errors | **0** |
| 覆盖 | 12E X1（projection_exclusion_decoupling）/ X2（final_decision_aggregator_purification + confidence_evaluator + confidence_result_wiring + cutoff_guard + memory_feedback_cutoff_guard）/ X3（ai_summary）/ X4（promotion_offline_only + predict_legacy_wrapper / x2 / x3 / x4b）/ predict_legacy_adapter / predict_legacy_v2_bridge / 14E app_analysis_context_fixture hygiene |

### 3.4 Static sanity checks

| 检查 | 结果 |
|---|---|
| `test ! -f confidence_engine.py` | ✅ OK：root 无 `confidence_engine.py` |
| `test ! -f contradiction_engine.py` | ✅ OK：root 无 `contradiction_engine.py` |
| `test ! -f risk_model.py` | ✅ OK：root 无 `risk_model.py` |
| `test -f archive/legacy/root_stubs/confidence_engine.py` | ✅ OK：archive 存在 |
| `test -f archive/legacy/root_stubs/contradiction_engine.py` | ✅ OK：archive 存在 |
| `test -f archive/legacy/root_stubs/risk_model.py` | ✅ OK：archive 存在 |
| `test -f archive/legacy/root_stubs/_DEPRECATED.md` | ✅ OK：deprecation marker 存在 |
| `test ! -f agent_loop.py` | ✅ OK：root 无 `agent_loop.py`（14M 已移到 `~/avgo_local_scripts/`） |

8 / 8 全部 OK。同样的 8 个 check 在 main 工作树（`/Users/may/Desktop/stock-analyzer-main`）独立验证，结果一致。

### 3.5 `.gitignore` pattern verify（`git check-ignore -v`）

| 输入 | 命中 pattern | 命中行 |
|---|---|---|
| `avgo_agent.db.backup_pre_2099_hygiene_20260503_160409` | `avgo_agent.db.backup_*` | `.gitignore:24` |
| `logs/regime_validation/` | `logs/regime_validation/` | `.gitignore:29` |
| `logs/historical_training/three_system_1005/` | `logs/historical_training/three_system_1005/` | `.gitignore:26` |
| `.claude/worktrees/` | `.claude/worktrees/` | `.gitignore:30` |
| `.claude/handoffs/task_089_post_pr_cleanup.md` | （未命中；deliberate 不 ignore） | — |

14K 的 6 行 pattern 全部生效；handoff **未** ignored —— 与 14L A2 / 14M
保留 landmark 设计一致。

---

## 4. Cleanup 完成项

Step 14 系列累计完成（按 commit / record 顺序）：

| Step | 类型 | 内容 |
|---|---|---|
| **14A** | plan | quarantine 计划 + DO_NOT_TOUCH_LOCAL_ARTIFACT 边界 |
| **14B** | audit | root dead stubs 审计 |
| **14C** | decision | root stubs quarantine delete 决策 |
| **14D**（包含在 `3b0d470`） | impl | 把 `confidence_engine.py` / `contradiction_engine.py` / `risk_model.py` quarantine 到 `archive/legacy/root_stubs/`（含 `_DEPRECATED.md`） |
| **14E** | plan | test fixture hygiene 计划 |
| **14F**（包含在 `bd4b81b`） | impl | scope `app_analysis_context_fixture` monkeypatch with try/finally restore |
| **14G** | audit | legacy v1 orchestrator 审计 |
| **14H** | correction | `record_14a` v1 orchestrator 分类修正 |
| **14I** | checkpoint | cleanup status checkpoint |
| **14J** | plan | local artifact handling plan |
| **14K** | impl | `.gitignore` 加入 6 行 pattern（DB backups / prediction log / 3 个 three_system_* / regime_validation / `.claude/worktrees/`） |
| **14L** | review | handoff & agent_loop.py read-only review |
| **14M** | impl | Option B：handoff keep local（A2）+ `mv agent_loop.py ~/avgo_local_scripts/`（B1） |

明面收敛结果：

- root v1 stubs 已 quarantine 到 `archive/legacy/root_stubs/`（含 `_DEPRECATED.md`）
- `app_analysis_context_fixture` monkeypatch 已 scoped + try/finally restore
- `.gitignore` 已覆盖 7 类 local artifacts pattern：
  - `avgo_agent.db.backup_*`
  - `logs/prediction_log.jsonl`
  - `logs/historical_training/three_system_1005/`
  - `logs/historical_training/three_system_w4_2024_08_2025_12/`
  - `logs/historical_training/three_system_w4_smoke_2024_08_05_2024_08_09/`
  - `logs/regime_validation/`
  - `.claude/worktrees/`
- `agent_loop.py` 已移到 `~/avgo_local_scripts/agent_loop.py`（byte-identical 932 B / 2026-05-02 14:17）；repo root 不再有
- 4 套 tracked log evidence（`logs/historical_training/03_fresh_replay/` / `exclusion_action_validation_2e*` / `logs/technical_features/`）保持 tracked
- main worktree 普通 `git status` 噪音从 16 项收敛到 **1 项**（仅 deliberate handoff landmark）

---

## 5. 当前 KEEP_ACTIVE

按 [.claude/CLAUDE.md](../.claude/CLAUDE.md) Mission + 14A §9 / 14G / 14I 分类：

| 模块组 | 状态 | 说明 |
|---|---|---|
| `services/projection_orchestrator.py` | **KEEP_ACTIVE** | 14G / 14H 修正分类后明确：仍是 active orchestrator，被 `predict.run_predict` legacy 路径使用；**不**算 dead code |
| `services/projection_orchestrator_v2.py` | **KEEP_ACTIVE** | V2 orchestrator stack；3R-3 / 3R-3.x 系列已完成；当前**未**默认（hard rule 1）；通过 `predict._build_projection_three_systems_attachment` 给 predict-tab 提供 `confidence_evaluator` 数据 |
| `predict.py`（含 legacy wrapper + adapter + v2 bridge） | **KEEP_ACTIVE** | 12E X1..X5 boundary 已封禁 trading / hard / forced / promotion / mutation surface；wrapper / adapter / x2 / x3 / x4b / v2 bridge 全部 covered |
| `services/projection_three_systems_renderer.py` | **KEEP_ACTIVE** | confidence_evaluator 主体；110 已 recalibrate |
| `services/exclusion_*` / `services/big_up_big_down_warning.py` / `services/contradiction_card.py` | **KEEP_ACTIVE** | exclusion / contradiction / big-up/down 链 |
| `services/final_decision_aggregator*.py` | **KEEP_ACTIVE** | final report 链；12E X2 已封禁 mutation surface |
| `services/scanner*` / `services/matcher*` / `services/encoder*` / `services/feature_builder.py` / `services/data_fetcher*` | **KEEP_ACTIVE**（hard rule 2：scanner/matcher/encoder 是硬规则层，优先保留） |
| `predict_summary` / `prediction_store` / `outcome_capture` / `review_store` | **KEEP_ACTIVE** | research loop v1（prediction log / outcome capture / review generation） |
| `services/automation_wrapper.py` / `services/tool_router.py` / `services/intent_planner.py` / `services/ai_intent_parser.py` / `services/ai_task_parser.py` | **KEEP_ACTIVE** | command bar / intent parsing；`_warnings.warn` 是 deliberate degraded path（boundary tests 期望） |
| `app.py` | **KEEP_ACTIVE**（hard rule 3：本轮只允许最小改动） |
| `ui/command_bar.py` / `ui/home_tab.py` / `ui/predict_tab.py` / 其它 ui/* | **KEEP_ACTIVE** | 12E / 13 / 14 期间均无破坏性修改 |
| `services/cutoff_guard*` / `services/memory_feedback_cutoff_guard*` / `services/ai_summary_*` | **KEEP_ACTIVE** | 12E 系列加固 |

---

## 6. 当前 KEEP_FROZEN_DIAGNOSTIC / archived

| 路径 | 状态 | 说明 |
|---|---|---|
| `archive/legacy/root_stubs/confidence_engine.py` | **archived (quarantine)** | 14D；含 `_DEPRECATED.md` |
| `archive/legacy/root_stubs/contradiction_engine.py` | **archived (quarantine)** | 同上 |
| `archive/legacy/root_stubs/risk_model.py` | **archived (quarantine)** | 同上 |
| `archive/legacy/root_stubs/_DEPRECATED.md` | **tracked deprecation marker** | 14D |
| `services/continuous_smoothing*`（v1 / v2 candidate） | **KEEP_FROZEN_DIAGNOSTIC** | 3R-3 / 3R-3.x 已完成；v2 candidate 未 promote；frozen baseline 用于 postmortem 对比 |
| `logs/historical_training/03_fresh_replay/` | **tracked log evidence** | 3R-3 fresh replay；保持 tracked |
| `logs/historical_training/exclusion_action_validation_2e/` 与 `_v2/` | **tracked log evidence** | exclusion action validation；保持 tracked |
| `logs/technical_features/...` | **tracked log evidence** | technical_features 历史；保持 tracked |
| `tasks/` 全系列 record（含 11h / 10 / 09 / 08 / 12 / 12E / 13 / 14A~14M） | **tracked historical contract docs** | byte-frozen，禁止 retro-edit |
| `.claude/CLAUDE.md` / `.claude/CHECKLIST.md` / `.claude/PROJECT_STATUS.md` / `.claude/TASK_TEMPLATE.md` / `.claude/agents/*` / `.claude/skills/*` | **tracked infra** | hard rules / handoff workflow / agent / skill 配置 |

---

## 7. 当前仍未处理事项

> 这些是 **deliberate** 保留 / 推迟的事项，**不**算 cleanup 缺口。

| 项 | 当前状态 | 推迟理由 / 处理路径 |
|---|---|---|
| `.claude/handoffs/task_089_post_pr_cleanup.md` | untracked deliberate landmark | 14L A2 / 14M：用户明确选择 KEEP_LOCAL_MANUAL；STATUS.md 多处 task closeout 用作 "untouched protected file" landmark；如未来想 archive，**单独**走用户确认 + 同步更新 STATUS.md |
| `run_predict` 默认 path | **legacy**（`services/projection_orchestrator.py`） | hard rule 1（不让 LLM 决定股票方向）+ 默认 V2 迁移需独立 launch review；**不**由 cleanup signoff 自动解锁 |
| 默认 V2 migration | **未** launch review | 同上；3R-5（如存在）应为 launch review 阶段 |
| `services/continuous_smoothing*` v2 candidate | **未** promote；frozen baseline | 3R-3 / 3R-3.x 已完成；postmortem 对比已写；接活化需独立 launch review |
| `predict.py` 内部 legacy helpers | **保留** | 12E X1..X5 boundary 已锁住 surface；删除/重构需独立 task |
| 7 个 `avgo_agent.db.backup_*` 字节 | **本地保留**（14K 已 ignore） | 14J §6.2 推荐 4 周内回滚审计窗口；之后**用户单独**决定 MOVE_OUTSIDE_REPO 或 DELETE |
| 4 个 untracked replay / regime validation 子目录 | **本地保留**（14K 已 ignore） | 14J §5.2 推荐 raw 留本地；如要保留 markdown summary 进 repo，走**单独** archive commit（仅 .md，不含 .csv/.json/.jsonl/_run.log） |
| `.claude/worktrees/` 26 个 worktree（~390 MB） | **本地保留**（14K 已 ignore） | 14J §7.1：harness 自动管理；活跃 session 期间不删；**用户单独**确认可删 |
| 3R-5 / 3R-6 | **未启动** | hard rules + cleanup signoff 不自动解锁；详见 §8 |

---

## 8. 是否允许进入 3R-5 / 3R-6

> **NO.**

理由（与 14I §10 / 14J §13 / 14L §8 一致 + Step 15 新增）：

1. **默认 V2 migration 未 launch review**。Step 15 是 **cleanup
   regression**，不是 launch review；性质上不能解锁 production behavior
   change（`run_predict` 默认路径切换）。
2. **hard rule 第 1 条**：不让 LLM 决定股票方向。3R-5 / 3R-6 触及
   trading / hard decision / production promotion 路径；不允许由 cleanup
   signoff 顺手放行。
3. **12E X1..X5 boundary suite**：已**永久封禁** trading / hard / forced /
   promotion / mutation surface（Step 15 §3.3 269 个 focused tests 全部
   pass 是这条封禁仍生效的证据）。
4. **3R-5 / 3R-6 需要独立 launch review doc**：`launch review` ≠
   `regression signoff`。launch review 必须含：
   - dry-run / shadow comparison metrics
   - 显式风险评估（regime-edge / contradiction / exclusion edge cases）
   - 默认切换 rollback plan
   - 用户**单独**显式确认
5. **Step 14 cleanup 的 deliberate scope** 自始至终不包含 3R-5 / 3R-6
   推进；14A / 14J §10 / 14L §7 全部明文禁止借机进入。

---

## 9. 是否允许进入普通开发

> **YES，with constraints。**

### 9.1 允许（在严守 hard rules 前提下）

- ✅ **lower-risk docs**（含 tasks/ record / handoffs / CHECKLIST 更新）
- ✅ **UI 改动**：在 hard rule 3（app.py 最小改动）+ hard rule 4（新逻辑优先 services/ 或 ui/）+ 12E X1..X5 boundary 不被绕过的前提下
- ✅ **diagnostics**（新 logging / monitoring / observability，不写 DB / 不改 schema）
- ✅ **isolated tests**（覆盖现有 KEEP_ACTIVE surface 的新 unit / boundary / negative-import suite，不重跑 replay）
- ✅ **non-trading feature work**（research loop v1 enhancement：prediction log / outcome capture / review generation 改进，但**不**让 LLM 决定方向）
- ✅ **bug fixes**（如有发现），单独 task / commit；走 plan → builder → reviewer → tester

### 9.2 不允许

- ❌ trading automation
- ❌ hard / forced / required decision 路径接 LLM 输出
- ❌ production promotion 自动放行（hard rule 5：所有 AI 输出必须结构化；
  但结构化 ≠ 自动促销）
- ❌ default V2 migration without independent launch review
- ❌ 重新引入 root level v1 stubs（已 quarantine 的 confidence_engine /
  contradiction_engine / risk_model）
- ❌ 重新引入 root level `agent_loop.py`（应走 services/ 路径 + 独立 feature task）
- ❌ 一次 commit 同时改业务 + .gitignore + tasks/STATUS.md hard rules
- ❌ 触碰 RISK-1 / RISK-2 / RISK-3 / RISK-7 / RISK-8 / RISK-9 / RISK-10 现有边界
  （除非走完整 task 流程；不能借机搂草打兔子）

---

## 10. 推荐下一步

| 优先级 | 动作 |
|---|---|
| 1 | **暂停 cleanup**。Step 14 系列（14A~14M）+ Step 15 已签收；继续做 cleanup 只会引入边际收益递减 + 风险递增 |
| 2 | **回到正常开发路线**。可选方向：(a) research loop v1 增强（prediction log 字段补全 / outcome capture 完整化 / review generation 自动化）；(b) UI / diagnostics 增强（KEEP_ACTIVE surface 内）；(c) 已发现 bug 的修复（单独 task） |
| 3 | **若要处理 3R-5 / 3R-6**：先写独立 launch review doc（`tasks/step_3r5_*_launch_review.md`），含 dry-run metrics + risk assessment + rollback plan + 显式用户确认；**不**借 Step 15 顺手解锁 |
| 4 | **若要处理 §7 推迟项**：每一项**单独** task + 单独 commit + 用户确认（DB backup MOVE / DELETE，4 套 untracked replay 子目录 markdown archive，handoff archive A1，`.claude/worktrees/` 清理） |
| 5 | **下次 cleanup 触发条件**：当 main worktree 普通 `git status` 再次出现 ≥ 3 项非 deliberate untracked，或 `archive/legacy/` 出现新 entry，或 9 个 negative-import / 12E X1..X5 任一 surface 触发新 boundary fix；**不**做时间驱动的常规 cleanup |

---

## 11. 严守边界

本轮 Step 15 **只**做 regression signoff：

- 未改业务代码（`.py` / `app.py` / `ui/*` / `services/*` / `predict.py`
  全部 byte-identical 与 main `ddf10b7`）
- 未改测试（`tests/test_*.py` 全部 byte-identical）
- 未新增测试
- 未删除文件 / 未移动文件
- 未处理 handoff（`.claude/handoffs/task_089_post_pr_cleanup.md` 字节
  不变，仍 untracked）
- 未处理 logs / DB backup / `.claude/worktrees/`
- 未改 `.gitignore`（仍是 14K commit `66dafd8` 状态）
- 未跑 replay / real validation
- 未写 DB / 未改 DB schema
- 未默认迁移 `run_predict` 到 V2
- 未启用 candidate / 未复活 `continuous_smoothing` / 未接 trading
- 未进入 3R-5 / 3R-6
- 未启动任何 §7 推迟项的处理
- 未修改 `.claude/CLAUDE.md` / `tasks/STATUS.md` 任一 hard rule / landmark
- 未修改 12E / 13 / 14A~14M 已 commit / 已写 record 的 byte
- 未 commit / 未 push（按本轮指令；本文件作为 untracked deliverable，由用户决定后续 commit 时机）

后续修改路径：任何对 §3 回归数字、§4 完成项、§5 KEEP_ACTIVE / §6 KEEP_FROZEN /
§7 推迟项、§8 / §9 边界、§10 推荐下一步的调整，都必须**显式更新本文件**；
同时检查是否需要同步更新 14I §8 / 14J / 14L / 14M。
