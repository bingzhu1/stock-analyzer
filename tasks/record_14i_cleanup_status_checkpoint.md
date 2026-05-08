# 14I记录：Cleanup Status Checkpoint

> 本记录是 **Step 14 的第九阶段：cleanup status checkpoint**。Step 14H
> （commit `e4be95f`）已把 14A §7.2 / §10.3 关于 V1 orchestrator 的分类
> 校正同步进 main。
>
> 本轮**只写状态文档**：未改业务代码、未改测试、未删除 / 移动文件、未跑
> replay / real validation、未写 DB / 未改 DB schema、未默认迁移
> `run_predict` 到 V2、未处理 local artifacts、未 commit / push、未进入
> 3R-5 / 3R-6、未顺手碰任何 RISK / cleanup 候选项。

---

## 1. Step 14I 目的

总结 **Step 14A–14H** 之后的 cleanup 状态，做一次**冻结**，用以决定下一步：

1. 是否继续处理 §8 列出的 local artifacts（=> Step 14J plan）
2. 是否暂停 cleanup 回到功能开发（仍**禁止** 3R-5 / 3R-6）
3. 是否走 Step 15 regression-after-cleanup 完整签收

本轮**不**做新 cleanup，不写 retention policy，不删 / 不 mv 任何文件，
不改任何 `.py`，不新增任何测试。

---

## 2. 当前 main 状态

| 项 | 值 |
|---|---|
| main 最新 commit | `e4be95f docs(cleanup): correct 14a v1 orchestrator classification per 14g audit` |
| Step 14A–14H | ✅ 全部入 main |
| 当前工作树（worktree）git status | clean，untracked 仅 `logs/prediction_log.jsonl` |
| main 工作树 git status | 14 个 untracked artifacts（详见 §8）— **本轮不处理** |
| Full pytest baseline（最近一次 14F 实施时跑） | 3256 passed / 10 skipped / 0 failed |
| `bash scripts/check.sh` baseline（14F 实施时跑） | All compile checks passed |
| 是否运行 full pytest / scripts/check.sh 本轮 | ❌ 否（14I 是**纯状态文档**；不改代码不需要重跑） |

---

## 3. Step 14A–14H 完成摘要

| Step | 类型 | 实际改 tracked 文件？ | 提交 / 主要结果 |
|---|---|---:|---|
| **14A** | plan | ❌（仅新增 plan 文档） | `afb006b docs(cleanup): record 14a cleanup quarantine plan` — 划定 14 系列 cleanup 范围、`DO_NOT_TOUCH_LOCAL_ARTIFACT` 名单、`NO_DIRECT_DELETE_CANDIDATE_YET` 原则 |
| **14B** | audit | ❌（仅新增 audit 文档） | `3808677 docs(cleanup): record 14b root dead stubs audit` — `confidence_engine.py` / `contradiction_engine.py` / `risk_model.py` 三 root stub 零 active import |
| **14C** | decision | ❌（仅新增 decision 文档） | `c5dca5f docs(cleanup): record 14c root stubs quarantine delete decision` — Option B：quarantine（move 到 `archive/legacy/root_stubs/`）而非 `git rm` |
| **14D** | implementation | ✅ | `3b0d470 chore(cleanup): quarantine root v1 stubs to archive/legacy/root_stubs` — `git mv` 三个 stub + 新增 `archive/legacy/root_stubs/_DEPRECATED.md` |
| **14E** | plan | ❌（仅新增 plan 文档） | `df912b8 docs(cleanup): record 14e test fixture hygiene plan` — Option A 推荐：try/finally restore，最小修复 |
| **14F** | implementation | ✅ | `bd4b81b chore(cleanup): scope app_analysis_context_fixture monkeypatch with try/finally restore` — fixture 加 `_ORIGINALS` 字典 + try/finally；新增 `tests/test_app_analysis_context_fixture_hygiene.py`（4 个 test） |
| **14G** | audit | ❌（仅新增 audit 文档） | `6d2a87e docs(cleanup): record 14g legacy v1 orchestrator audit` — `services/projection_orchestrator.py` 分类 = `KEEP_ACTIVE` |
| **14H** | docs correction | ❌（仅 doc edit） | `e4be95f docs(cleanup): correct 14a v1 orchestrator classification per 14g audit` — 把 14A §7.2 / §10.3 关于 V1 orchestrator 的过期分类校正为 `KEEP_ACTIVE` |

---

## 4. 已实际执行的 cleanup（动了 tracked 文件）

整个 14 系列里**只有两项**真正修改了 tracked code / docs（除 audit / plan
文档自身）；其余都是计划 / 审计 / 决策 / 文档修正：

### 4.1 Root v1 stubs quarantine（14D）

- `confidence_engine.py` → [archive/legacy/root_stubs/confidence_engine.py](archive/legacy/root_stubs/confidence_engine.py)
- `contradiction_engine.py` → [archive/legacy/root_stubs/contradiction_engine.py](archive/legacy/root_stubs/contradiction_engine.py)
- `risk_model.py` → [archive/legacy/root_stubs/risk_model.py](archive/legacy/root_stubs/risk_model.py)
- 新增 [archive/legacy/root_stubs/_DEPRECATED.md](archive/legacy/root_stubs/_DEPRECATED.md)（quarantine 说明 + Hard rules + 未来删除 gate）

负向防御：`tests/test_predict_legacy_*` / `tests/test_confidence_*` 等 9 个
negative-import 测试的 `forbidden_modules` 仍含 `"confidence_engine"` /
`"contradiction_engine"` / `"risk_model"`。这些字符串**永久保留**，即便
quarantine 后任何尝试 `import` 这些名字都会被 negative-import 测试拒绝。

### 4.2 `app_analysis_context_fixture` hygiene（14F）

- [tests/fixtures/app_analysis_context_fixture.py](tests/fixtures/app_analysis_context_fixture.py)：
  在 9 行 `<module>.<attr> = <fake>` rebind 之前加 `_ORIGINALS` 字典；
  把 `runpy.run_path("app.py")` 包进 `try/finally`；finally 块按 `(module, attr) → original`
  恢复原函数
- 新增 [tests/test_app_analysis_context_fixture_hygiene.py](tests/test_app_analysis_context_fixture_hygiene.py)（4 个 test：predict.run_predict / scanner+matcher / stats_reporter restore + 不打断 AppTest）

### 4.3 通过的验收

两项实施完成时跑过：

- focused tests：14D = 13C / 13D / 14B 中提到的 9 个 negative-import 测试；
  14F = `tests/test_app_analysis_context.py` 2 passed + `tests/test_app_analysis_context_fixture_hygiene.py` 4 passed + 5 个 boundary 文件 共 108 passed
- full pytest：3256 passed / 0 failed
- `bash scripts/check.sh`：All compile checks passed

> 14A / 14B / 14C / 14E / 14G / 14H **未**改任何 tracked code / 测试，是纯
> 文档动作。

---

## 5. 只做计划 / 审计 / 决策 / 文档修正的事项

| Step | 性质 | 主要产出 |
|---|---|---|
| 14A | cleanup plan | 划定 14 系列范围、`DO_NOT_TOUCH_LOCAL_ARTIFACT` 名单、commit-per-fix 原则、`NO_DIRECT_DELETE_CANDIDATE_YET` |
| 14B | audit | 三个 root stub 零 active import 证据 |
| 14C | decision | Option B（quarantine）vs Option A（git rm） |
| 14E | plan | fixture hygiene 三方案对比 + Option A 推荐 |
| 14G | audit | V1 orchestrator KEEP_ACTIVE 证据 |
| 14H | docs correction | 14A §7.2 / §10.3 stale classification 校正 |

> 上述 6 项**只**新增 / 修订 `tasks/record_*.md`，**未**改任何 `.py`。

---

## 6. KEEP_ACTIVE 当前清单

> 这些文件 / 模块在 14 系列 cleanup 中**确认**仍在 active path 上，**禁止**
> 删除 / 移动 / quarantine。本清单不穷举所有 active 文件，只列与 14 系列
> cleanup 直接相关的、容易被误判为"可清"的项。

### 6.1 推演主链路（V2 + V1 + 关键 active services）

| path | 状态 | 来源 |
|---|---|---|
| [services/projection_orchestrator.py](services/projection_orchestrator.py) | KEEP_ACTIVE（14G 修正） | 14G §7.3 |
| [services/projection_orchestrator_v2.py](services/projection_orchestrator_v2.py) | KEEP_ACTIVE | 14A §6 / 09 |
| [services/projection_orchestrator_preflight.py](services/projection_orchestrator_preflight.py) | KEEP_ACTIVE | 14G §3.1 / 09 |
| [services/projection_entrypoint.py](services/projection_entrypoint.py) | KEEP_ACTIVE | 09 |
| [services/projection_v2_adapter.py](services/projection_v2_adapter.py) | KEEP_ACTIVE | 09 |
| [services/main_projection_layer.py](services/main_projection_layer.py) | KEEP_ACTIVE（仍含 RISK-1 解耦债） | 09 |
| [services/exclusion_layer.py](services/exclusion_layer.py) | KEEP_ACTIVE | 09 |
| [services/final_decision.py](services/final_decision.py) | KEEP_ACTIVE | 11B / 11C |
| [services/confidence_evaluator.py](services/confidence_evaluator.py) | KEEP_ACTIVE | 11C-A |
| [services/cutoff_guard.py](services/cutoff_guard.py) | KEEP_ACTIVE | 11D / RISK-7 |
| [services/predict_legacy_adapter.py](services/predict_legacy_adapter.py) | KEEP_ACTIVE | 11E X4-A |
| [services/predict_legacy_v2_bridge.py](services/predict_legacy_v2_bridge.py) | KEEP_ACTIVE | 11E X5 |
| [predict.py](predict.py)（legacy compatibility wrapper） | KEEP_ACTIVE | 11E X1–X5 |

### 6.2 入口 / UI / 数据基础设施

- [app.py](app.py)
- [ui/](ui)（`predict_tab.py` / `home_tab.py` / `command_bar.py` / 等）
- [scanner.py](scanner.py) / [matcher.py](matcher.py) / [encoder.py](encoder.py) /
  [feature_builder.py](feature_builder.py) / [data_fetcher.py](data_fetcher.py) /
  [stats_reporter.py](stats_reporter.py)
- [services/predict_summary.py](services/predict_summary.py) / [services/prediction_store.py](services/prediction_store.py) /
  [services/outcome_capture.py](services/outcome_capture.py) / [services/review_store.py](services/review_store.py) /
  [services/automation_wrapper.py](services/automation_wrapper.py) / [services/tool_router.py](services/tool_router.py) /
  [services/intent_planner.py](services/intent_planner.py) / [services/ai_intent_parser.py](services/ai_intent_parser.py)
- contract replay 写入链：`services/contract_replay_writer.py` / `services/log_store.py` /
  `services/prediction_store.py` / `services/outcome_capture.py` / `services/review_store.py`

### 6.3 Active 测试

- 12E-X1..X5 boundary tests（`tests/test_predict_legacy_wrapper_boundary.py` /
  `tests/test_predict_x{2,3,4b}_*` / `tests/test_predict_legacy_v2_bridge.py` /
  `tests/test_predict_legacy_adapter.py`）— 5 个 X 系列文件保留 `_fresh_predict_module()`
  防御助手（14F 未移除，14E §9.10 明确不动）
- 9 个 negative-import 测试的 `forbidden_modules` 字符串—**永久保留**
- [tests/test_app_analysis_context.py](tests/test_app_analysis_context.py) +
  [tests/test_app_analysis_context_fixture_hygiene.py](tests/test_app_analysis_context_fixture_hygiene.py)（14F 新增）
- [tests/test_projection_orchestrator.py](tests/test_projection_orchestrator.py)（14G KEEP_ACTIVE 守护方）
- 全部 `tests/test_projection_orchestrator_v2*.py`、`tests/test_confidence_*.py`、
  `tests/test_*boundary.py` 等 active boundary suite

---

## 7. KEEP_FROZEN_DIAGNOSTIC 当前清单

> 这些项**仍存在**，但只用于审计 / 历史追溯 / 离线诊断；**不**进入
> active path，**不**进入 trading / promotion。本轮**不**整理 / 不删除 / 不归档。

| path | 性质 |
|---|---|
| `services/continuous_smoothing*.py`（v1 / v2） | 11G frozen；`predict.py` 不再 import；任何重启需独立 plan |
| `scripts/run_continuous_smoothing_validation*.py` 系列 | 11G frozen 验证脚本；本地诊断用 |
| `scripts/run_real_continuous_smoothing_validation*.py` 系列 | 同上 |
| `tests/test_continuous_smoothing*.py` | 11G frozen 测试；行为 pinned 不允许扩 |
| `records/` 目录（与 `tasks/` 并存，14A §7.5 仍待 audit） | 历史 record；14A 已判定**不**在 14 系列动 |
| `archive/legacy/root_stubs/`（14D 创建） | 现为 quarantine archive；按 `_DEPRECATED.md` 列举 hard rules 保留 byte-identical；删除 gate 在 4 周稳定窗口 + 用户显式批准 |
| 3R-3 / 3R-3.3 历史 checkpoint docs（如有） | 历史轨迹；不动 |
| `logs/regime_validation/` 输出（**local untracked**，见 §8） | 离线诊断输出；归 `DO_NOT_TOUCH_LOCAL_ARTIFACT` |

---

## 8. DO_NOT_TOUCH_LOCAL_ARTIFACT 当前清单

> 来源：main 工作树 `git status` 全部 untracked 项（当前 worktree 自己只有
> `logs/prediction_log.jsonl` 一项 untracked，其余 13 个仅在 main 工作树可见）。

| path | 类型 | 14A §9 决议 |
|---|---|---|
| `.claude/handoffs/task_089_post_pr_cleanup.md` | 历史 handoff（local） | DO_NOT_TOUCH |
| `.claude/worktrees/`（目录） | claude worktree 缓存（local） | DO_NOT_TOUCH |
| `agent_loop.py`（root，untracked） | 本地实验脚本 | DO_NOT_TOUCH |
| `avgo_agent.db.backup_pre_2099_hygiene_20260503_160409` | DB backup | DO_NOT_TOUCH |
| `avgo_agent.db.backup_pre_3a3_20260504_013453` | DB backup | DO_NOT_TOUCH |
| `avgo_agent.db.backup_pre_3a4_20260504_023331` | DB backup | DO_NOT_TOUCH |
| `avgo_agent.db.backup_pre_4c3_rewrite_20260503_235604` | DB backup | DO_NOT_TOUCH |
| `avgo_agent.db.backup_pre_replay_130_20260504_003707` | DB backup | DO_NOT_TOUCH |
| `avgo_agent.db.backup_pre_replay_30_20260503_162636` | DB backup | DO_NOT_TOUCH |
| `avgo_agent.db.backup_step_2c_2_6` | DB backup | DO_NOT_TOUCH |
| `logs/historical_training/three_system_1005/` | 历史训练原始输出 | DO_NOT_TOUCH |
| `logs/historical_training/three_system_w4_2024_08_2025_12/` | 同上 | DO_NOT_TOUCH |
| `logs/historical_training/three_system_w4_smoke_2024_08_05_2024_08_09/` | 同上 | DO_NOT_TOUCH |
| `logs/regime_validation/` | regime 诊断原始输出 | DO_NOT_TOUCH |
| `logs/prediction_log.jsonl`（worktree 内可见） | standing 预测日志 | DO_NOT_TOUCH |

> 共 **15** 项 untracked artifacts。本轮**不**自动 add / mv / 删除其中任何
> 一项。任何处理需**用户单独显式确认**，并在 Step 14J plan 中分类（保留 /
> archive / delete / gitignore）。

---

## 9. 仍未解决的 cleanup debt

| # | item | status | 备注 |
|---|---|---|---|
| 1 | §8 全部 15 个 local artifacts | 未处理 | 待 14J plan |
| 2 | `services/continuous_smoothing*` frozen diagnostics | 未整理 | 11G frozen 状态保留 |
| 3 | `predict.py` 内部 legacy helper（`_apply_*`、`_legacy_wrapper_metadata`、`_apply_v2_legacy_adapter_overlay` 等） | 仍存在 | 11E X1–X5 wrapper 设计；无清理计划 |
| 4 | default `run_predict` migration to V2 | 未做 | 仍需独立 launch review；非 14 范围 |
| 5 | `app_analysis_context_fixture` 的 `from X import Y` 别名级别污染（14E §4 #2） | 残余 | 由 5 个 boundary test 的 `_fresh_predict_module()` 防御兜底；本轮不动 |
| 6 | `app_analysis_context_fixture` 顶层无 main guard（14E §4 #3 / #4） | 残余 | 14E 留待独立 commit；超出本系列 |
| 7 | 5 个 boundary test 的 `_fresh_predict_module()` 助手是否未来精简 | 未决 | 14E §9.10 / 14F 不动 |
| 8 | `records/` vs `tasks/` 体系是否归并（14A §7.5） | 已判定**保留** | 14A 决定不在 14 系列动 |
| 9 | `archive/legacy/root_stubs/` 三 stub 未来是否 `git rm` | 未决 | gate：4 周稳定窗口 + 用户单独批准；详见 `_DEPRECATED.md` §"Future deletion" |
| 10 | RISK-1（exclusion → main_projection 耦合） | 未解 | 09 §RISK-1；非 14 范围；属架构层 |
| 11 | RISK-2 / RISK-3 / RISK-7 / RISK-9 / RISK-10 | 未解 | 同上；非 14 范围 |
| 12 | `tasks/STATUS.md` 是否需要更新到反映 14A–14I 当前状态 | 未做 | 本轮**不**改 STATUS.md（避免破坏 status 字段约定） |

---

## 10. 是否允许进入 3R-5 / 3R-6

> **NO.**

理由：

1. §8 列出的 **15** 项 local artifacts 全部未处理；进入 3R-5 / 3R-6 之前
   必须有明确的 retention / archive / delete 决策（最少一份 14J plan）
2. 14 系列 cleanup 还有 §9 列出的 **12** 项 debt（其中 #1 必须先解，其余
   是冷债）
3. `run_predict` 默认迁移到 V2 仍未走 launch review；3R-5 / 3R-6 任何与
   trading / promotion / hard exclusion 相关的 commit **永远禁止**
4. CLAUDE.md / `.claude/CLAUDE.md` 第 1 / 5 / 6 条 hard rules 不允许 LLM
   决定股票方向、不允许 promotion 自动放行；3R-5 / 3R-6 触碰这些边界
5. trading / hard / forced / required / promotion / mutation 输出面在
   12E-X1..X5 boundary tests 永久封禁；进入 3R-5 / 3R-6 必然命中这些
   forbidden surface

> 任何想进入 3R-5 / 3R-6 的提议都必须先：(a) 完成 14J 全部 local artifact
> 决策；(b) 跑 Step 15 regression-after-cleanup 全绿；(c) 用户显式同意。

---

## 11. 下一步选项

### 11.1 Option A — 继续 Step 14J: local artifact handling plan（**推荐**）

- 只**写计划**：列每个 §8 artifact 的归类（保留 / 加 .gitignore / archive /
  delete / 移到本地非 repo 路径），写 retention policy
- **不**直接 add / 删除 / 移动；**不**碰 DB backup 字节
- 产出：新增 [tasks/record_14j_local_artifact_handling_plan.md](tasks/record_14j_local_artifact_handling_plan.md)
- commit message 建议：`docs(cleanup): record 14j local artifact handling plan`
- 实施（14K+）需用户**单独**显式同意每一项

### 11.2 Option B — 暂停 cleanup，回到 lower-risk 功能开发

- **不**得进入 3R-5 / 3R-6
- 允许的工作面：
  - lower-risk UI 调整（不改 active 推演链）
  - docs / record 修订
  - diagnostics dashboard / 离线 inspection 脚本
  - 新增**纯加性** active boundary test（不能放松现有 forbidden 字符串）
- 风险：local artifacts 继续累积；未来 cleanup 成本递增

### 11.3 Option C — Step 15 regression-after-cleanup signoff

- 跑一次 full pytest + scripts/check.sh + 9 个 negative-import suite +
  12E X1..X5 boundary suite，把结果写入 `tasks/record_15_post_cleanup_regression.md`
- 不改代码；签字确认 14 系列 cleanup 已稳定
- 适合 Option A 完成后再做（13 系列已经做过 post-fix regression；14 系列
  规模更小，但增加了 fixture try/finally + quarantine 移动）

### 11.4 推荐

> **Option A — Step 14J local artifact handling plan**

理由：

1. §8 是 14 系列 cleanup 的最后一块明确缺口；不解就无法干净进 Option C
2. 与 14A §10.5（原计划"Step 14F local artifact handling plan"，因实施编号
   已挪用，需要新编号 14J）一致；只是改名
3. 14J **只写计划**；与 14A / 14B / 14C / 14E / 14G / 14H 的"plan-only"
   commit 模式一致；blast radius = 1 个新 docs 文件
4. 完成 14J 后再做 14K（local artifact 实施，逐项独立 commit），最后做
   Step 15 signoff，是干净的退出路径

---

## 12. 严守边界

本轮**只写 status checkpoint 文档**：

- 未改业务代码（全部 `.py` / `app.py` / `ui/*` / `services/*` / `predict.py` byte-identical 与 main `e4be95f`）
- 未改测试（`tests/test_*.py` 全部 byte-identical）
- 未新增测试
- 未删除文件 / 未移动文件
- 未处理 §8 任何 local artifact
- 未写 DB / 未改 DB schema
- 未跑 replay / real validation
- 未跑 full pytest（不改代码不需要重跑；baseline 仍为 14F 时记录的
  3256 passed / 0 failed）
- 未默认迁移 `run_predict` 到 V2
- 未启动任何 cleanup 实施
- 未进入 3R-5 / 3R-6
- 未启用 candidate / 未复活 `continuous_smoothing` / 未接 trading
- 未顺手碰 RISK-1 / RISK-2 / RISK-3 / RISK-7 / RISK-8 / RISK-9 / RISK-10
- 未改 `tasks/STATUS.md`

本计划的修改路径：任何对 §3 完成摘要、§4 / §5 cleanup 分类、§6 / §7 / §8
清单、§9 debt、§10 / §11 决策的调整，都必须以**显式更新本文件**的方式提
出；同时检查是否需要同步更新 14A / 14G。
