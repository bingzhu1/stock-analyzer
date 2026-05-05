# Step 2G-8D.2 — Tiny Smoke Replay Checkpoint

> **状态固化文档（tiny smoke replay checkpoint），不实现，不改代码，不写 DB，不运行 full W4 replay。**
> 本文档**冻结** Step 2G-8D.2 tiny smoke run 的：命令、smoke 窗口、
> 输出目录与文件清单、`w4_replay_manifest.v1` manifest 摘要、8 项
> 通过判据、DB / git 验证结果、对 8D.3 full W4 的 conditional GO 解锁。
>
> 本轮**不动任何代码**：不改 `predict.py` / `run_predict` /
> `scanner.py` / `prediction_store.py` / `app.py` / 任何 `ui/*` /
> `services/*` / `scripts/*` / 任何 builder / DB schema / 任何 test
> 中的任何一处。
>
> **本文不实施 8D.3、不跑 full W4 replay、不写 DB、不接 trading
> API**；只在 markdown 层固化 smoke 实测状态，作为后续 8D.3 full W4
> 的强制 gate。

---

## 1. 当前完成状态

- **Step 3 calibration restart launch review** 已完成并进入 main
  （commit `b8c781d`）
- **Step 3R-0** restart scope checkpoint 已完成并进入 main（commit
  `1b7288e`）
- **Step 3R-1** regime label design + checkpoint 已完成并进入 main
  （commits `a8df93a` / `8d4fe8f`）
- **Step 3R-4** cross-window validation protocol design + checkpoint
  已完成并进入 main（commits `a58aad4` / `abe3ba2`）
- **Step 3R-2** read-only regime labels builder + checkpoint 已完成并
  进入 main（commits `e2a681b` / `db7618b`）
- **Step 2G-8D** extend replay coverage design + checkpoint + audit
  已完成并进入 main（commits `170617c` / `5eb725b` / `705e04c`）
- **Step 2G-8D.1A** minimal replay script patch + checkpoint 已完成并
  进入 main（commits `36e76c9` / `cd149ce`）
- **Step 2G-8D.2** tiny smoke replay 已**成功运行**（本 checkpoint 阶段；
  smoke 产物未进 main）
- 本 checkpoint **固定**：
  - smoke 命令 + 调用边界
  - smoke 窗口（4 pairs，2024-08-05 → 2024-08-09）
  - 输出目录与 10 个文件清单
  - `w4_replay_manifest.v1` manifest 实测摘要
  - 8 项通过判据
  - DB / git 验证结果
  - 对 8D.3 full W4 的 conditional GO 解锁
- **full W4 replay 仍未运行**：本步骤是 8D.3 之前的强制 gate

---

## 2. 当前 main 状态

- main 最新 commit：**`cd149ce`**
- commit message：`docs(contract): Step 2G-8D.1A replay script patch checkpoint`
- 上游：`origin/main` 已同步
- 测试基线：**2689 passed / 0 failed / 10 skipped / 26 warnings /
  94 subtests**（与 commit `36e76c9` 一致；smoke 只读跑 replay，**不**
  改代码 / **不**改测试 → 基线不变）

| 项 | 是否触碰 |
|---|---|
| 改代码 | ❌ 否 |
| 写 DB | ❌ 否 |
| 改 services/* | ❌ 否 |
| 改 scripts/* | ❌ 否 |
| 改 tests/* | ❌ 否 |
| 改 DB schema | ❌ 否 |
| 跑 full W4 | ❌ 否 |
| 接 trading API | ❌ 否 |
| 触碰 2026 final test | ❌ 否 |

本 checkpoint 文档（即本文件）尚未 commit；本轮只写文档、**不**
commit / push。

---

## 3. smoke 命令

```
python3 scripts/run_1005_three_system_replay.py \
  --tiny-smoke \
  --final-test-cutoff 2026-01-01 \
  --output-dir logs/historical_training/three_system_w4_smoke_2024_08_05_2024_08_09 \
  --write-manifest
```

| 项 | 说明 |
|---|---|
| **未传 `--save-records`** | ✅；G3 在 W4 mode 强制 reject；同时 `--tiny-smoke` 自动 `save_records=False` 兜底 |
| **未传 `--allow-overwrite`** | ✅；smoke 输出目录是新建独立目录，G4 不触发 |
| **执行位置** | **main 工作树**（`/Users/may/Desktop/stock-analyzer-main/`）；commit `cd149ce` 时 |
| **`output_dir` 独立新目录** | ✅ `logs/historical_training/three_system_w4_smoke_2024_08_05_2024_08_09/`；与 1005 baseline (`three_system_1005/`) 互不覆盖 |
| **`--final-test-cutoff`** | `2026-01-01`（也是 argparse 默认） |
| **`--tiny-smoke`** | 自动填充 `start_date=2024-08-05` / `end_date=2024-08-09`；强制 `save_records=False` + `write_manifest=True` |
| **`--write-manifest`** | 显式启用；与 `--tiny-smoke` 自动启用兼容（双重确认） |
| **runtime** | ~ 10 秒（4 pair × ~ 2 秒 projection + outcome） |

---

## 4. smoke 窗口

| 字段 | 值 |
|---|---|
| **start** | **`2024-08-05`** |
| **end** | **`2024-08-09`** |
| **trading days 覆盖** | 5 day（避开周末 2024-08-03 / 04） |
| **pair 数** | **4** |

具体 4 pairs：

| # | as_of_date | prediction_for_date |
|---|---|---|
| 1 | 2024-08-05 | 2024-08-06 |
| 2 | 2024-08-06 | 2024-08-07 |
| 3 | 2024-08-07 | 2024-08-08 |
| 4 | 2024-08-08 | 2024-08-09 |

| 是否触碰 2026 | **❌ 否** |
|---|---|
| 是否依赖 W4 上限（2025-12-31） | ❌ 否；smoke 只覆盖 W4 起点附近 |
| 是否依赖 W3 终点（2024-08-02） | ❌ 否；smoke start = 2024-08-05 与 W3 终点不重叠 |

---

## 5. 输出目录与文件

### 5.1 输出目录

`logs/historical_training/three_system_w4_smoke_2024_08_05_2024_08_09/`

### 5.2 10 个文件清单

| 文件 | 字节 | 来源 |
|---|---:|---|
| `validation_ready_manifest.json` | 278 | **8D.1A 新增** manifest writer |
| `three_system_replay_results.jsonl` | 12,201 | per-case full audit |
| `three_system_replay_summary.md` | 1,566 | summary markdown |
| `three_system_replay_summary.json` | 3,209 | summary JSON |
| `negative_system_stats.csv` | 485 | per-case |
| `record_02_projection_stats.csv` | 691 | per-case |
| `confidence_evaluator_stats.csv` | 493 | per-case |
| `error_cases.csv` | 361 | filter |
| `false_exclusion_cases.csv` | 182 | filter |
| `high_confidence_wrong_cases.csv` | 202 | filter |

### 5.3 输出处置

| 项 | 状态 |
|---|---|
| 输出目录 git 状态 | **untracked**（与 8D checkpoint §9 "smoke 不进 main" 一致） |
| 是否进 main | **❌ 否**（本 checkpoint 不 add；后续 8D.3 / 8D.4 是 W4 full 的归属，不是 smoke） |
| 是否可删除 | ✅；smoke 是验证产物，不是 baseline |
| 是否可重跑 | ✅；G4 已防覆盖（重跑需 `--allow-overwrite` 或新目录）|
| 是否覆盖 1005 baseline | **❌ 否**（独立目录） |
| 是否写主 DB | **❌ 否** |

---

## 6. manifest 摘要

```json
{
  "schema_version": "w4_replay_manifest.v1",
  "replay_window": {"start": "2024-08-05", "end": "2024-08-09"},
  "final_test_cutoff": "2026-01-01",
  "final_test_touched": false,
  "records_generated": 4,
  "paired_outcomes": 4,
  "status": "ok",
  "warnings": []
}
```

| 字段 | 值 | 是否核心通过条件 |
|---|---|---|
| `schema_version` | `"w4_replay_manifest.v1"` | ✅（schema 合规） |
| `replay_window.start` | `"2024-08-05"` | ✅ |
| `replay_window.end` | `"2024-08-09"` | ✅ |
| `final_test_cutoff` | `"2026-01-01"` | ✅ |
| **`final_test_touched`** | **`false`** | **✅✅ 核心通过条件** |
| `records_generated` | `4` | ✅ |
| `paired_outcomes` | `4` | ✅ |
| **`status`** | **`"ok"`** | **✅** |
| **`warnings`** | **`[]`** | **✅**（无 G2 boundary skip 触发） |

### 6.1 强调

- **`final_test_touched=false`** 是 8D.2 → 8D.3 解锁的**核心通过条件**
- `status="ok"` 表示 G1/G2/G3/G4/G5 全部正常工作，无错误路径触发
- `warnings=[]` 表示 smoke 窗口内**没有任何 T+1 边界 skip**（与窗口远离 2026 一致）

---

## 7. 通过判据

| # | 判据 | 实测 | 状态 |
|---|---|---|---|
| 1 | manifest schema 合规（`schema_version="w4_replay_manifest.v1"`） | ✅ | **pass** |
| 2 | `final_test_touched=false` | ✅ | **pass** |
| 3 | 4 paired outcomes（`paired_outcomes=4`） | ✅ | **pass** |
| 4 | output files exist（10 个文件齐） | ✅ | **pass** |
| 5 | no DB writes（main DB / market_data.db mtime 未变） | ✅ | **pass** |
| 6 | no 2026 touched（无 2026 row / 无 G2 warning） | ✅ | **pass** |
| 7 | no `--save-records`（命令未传；G3 兜底） | ✅ | **pass** |
| 8 | no full W4（仅 4 pair 5 day smoke） | ✅ | **pass** |

**全部 8 项 pass**。8D checkpoint §9.1 强制规则全部满足。

---

## 8. DB / git 验证

### 8.1 DB 状态

| DB 文件 | mtime（smoke 后） | 是否被 smoke 修改 |
|---|---|---|
| `avgo_agent.db` | `May 4 02:34`（smoke 之前） | **❌ 未修改** |
| `data/market_data.db` | `Apr 29 00:02`（smoke 之前） | **❌ 未修改** |
| 任何 `avgo_agent.db.backup_*` | 无新增 | **❌ 无新增** |

→ smoke 没有写任何 DB（与 G3 + 默认 `--save-records=False` 一致）。

### 8.2 git 状态

| 路径 | 状态 |
|---|---|
| 任何 tracked file | **未 modified**（含 `scripts/run_1005_three_system_replay.py` / `services/*` / `tests/*` / `tasks/*`） |
| `logs/historical_training/three_system_w4_smoke_2024_08_05_2024_08_09/` | **untracked**（按 8D checkpoint §9 不进 main） |
| `logs/prediction_log.jsonl`（worktree side） | **untracked**；环境产物；**不 add** |
| `logs/historical_training/three_system_1005/` | **untracked**（与 8D.2 之前一致；非本步骤产物） |
| `agent_loop.py` / `avgo_agent.db.backup_*` / `.claude/worktrees/` / `.claude/handoffs/*` | **untracked**；**不 add** |

→ smoke 没有改任何 tracked 文件；smoke 输出目录保持 untracked，按指令不 add。

---

## 9. 预测精度不是 smoke 判据

| 指标 | 值 | 是否影响 smoke 通过 |
|---|---|---|
| `direction_accuracy` | **33.33%**（4 case 中 1 correct + 2 wrong + 1 unknown） | **❌ 否** |
| `triggered_count` | 2 | ❌ 否 |
| `false_exclusion_count` | 0 | ❌ 否 |
| `high_confidence_wrong` | 4 case 全 medium confidence | ❌ 否 |

**说明**：
- smoke 验证的是 **replay script safety / manifest / cutoff / no DB writes**，**不是** 预测精度
- 4 case 是**极小样本**，任何精度数字都不具统计意义
- 真实精度评估必须等 **8D.3 full W4 replay**（~ 350 paired）+ **3R-4 协议**下的 4-fold validation
- smoke 的 33.33% 不构成 candidate / formula / threshold 的任何 pass 或 fail 依据

---

## 10. 是否解锁 8D.3 full W4

**✅ conditional GO**。

### 10.1 conditional GO 前提

| # | 前提 | 满足方式 |
|---|---|---|
| 1 | **使用 same guards**（G1–G5 全部生效） | 8D.1A patch 已就位；smoke 已实测 G1 + G3 + G4 + G5 的安全路径；G2 在 smoke 窗口内无触发但 unit test 已锁定 |
| 2 | **独立 W4 output_dir** | 推荐 `logs/historical_training/three_system_w4_2024_08_2025_12/`（与 8D design §4.1 一致） |
| 3 | **no `--save-records`** | G3 在 W4 mode 强制 reject；命令不传 |
| 4 | **`--write-manifest`** | 显式传或 `--tiny-smoke` 自动；full W4 显式 |
| 5 | **`--final-test-cutoff=2026-01-01`** | argparse 默认 |
| 6 | **不触碰 2026** | G1（startup + 数据层）+ G2（T+1 边界）双重 hard stop |
| 7 | **full W4 输出不直接进 main 输出目录** | full W4 应进 main 的方式由 8D.4 W4 checkpoint 决定；本 checkpoint 不预判 |

### 10.2 仍 NO-GO

| # | 项 | 理由 |
|---|---|---|
| 1 | **不允许 W4 自动让 candidate pass** | W4 仅作 cross-window validation 数据；不进 hard gate |
| 2 | hard / forced / required upgrade | Step 2G 全程边界 + 三重 NO-GO（2G-8 / 8B / 8C） |
| 3 | 让 Gate 5 / Gate 6 pass | 与 v1 / 3R-0 / 3R-4 一致 |
| 4 | 把 smoke 当 W4 validation | smoke = 4 case 极小样本；W4 = ~350 paired |
| 5 | 把 smoke 输出 commit 进 main | 与 8D checkpoint §9 一致；smoke 是验证产物，不是 baseline |
| 6 | 触碰 2026 final test | 永久封禁；G1 + G2 双重 hard stop |
| 7 | 接 trading API | 永不 |

---

## 11. 当前仍禁止

| # | 禁止 | 理由 |
|---|---|---|
| 1 | **不启 hard / forced / anti_false_exclusion_triggered** | Step 2G-8 / 8B / 8C 三重 NO-GO 已锁定 |
| 2 | **不改 04 / 05 / 07 required** | Step 2G 全程边界 |
| 3 | **不让 Gate 5 / Gate 6 自动 pass** | 与 v1 / 3R-0 / 3R-4 一致 |
| 4 | **不把 smoke 当 W4 validation** | smoke 是 patch 验证，不是 W4 cross-window evidence |
| 5 | **不把 smoke 输出 commit 进 main** | 与 8D checkpoint §9 一致 |
| 6 | **不接 trading**（`longbridge` / `broker` / `paper_trade`） | 永不 |
| 7 | **不触碰 2026** | 永久封禁 |
| 8 | **不直接跑 full W4 而跳过本 checkpoint** | 8D checkpoint §9.1 强制规则 |
| 9 | **不写 DB**（main DB / `data/market_data.db`） | W4 是 read-only artifact |
| 10 | **不让 `_PROTECTION_LAYER_CONNECTED` 翻 True** | 与 v1 / 3R-0 / 3R-4 一致 |
| 11 | **不改 services/* / DB schema / scripts/* / tests/*** | 本 checkpoint 是纯文档 |
| 12 | **不改 3R-4 protocol thresholds** | 阈值调整必须经 launch review |
| 13 | **不改 3R-2 helper 行为** | helper 已 merge；W4 仅 read-only 调用 |
| 14 | **不触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*`** | 历史防护 |
| 15 | **不把 smoke 的 33.33% 精度当 candidate / formula 依据** | 4 case 无统计意义 |

---

## 12. 下一步建议

按推荐优先级：

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **commit 本 checkpoint** | 把 §1-13 smoke 实测状态固化到 main | **本轮 / 下一轮** |
| 2 | **Step 2G-8D.3 full W4 replay**（2024-08-03 → 2025-12-31） | 跑完整 W4；产物归属由 8D.4 checkpoint 决定；G1 + G2 + G5 manifest 全程 enforce | **高**（commit 本 checkpoint 后立刻启动） |
| 3 | **Step 2G-8D.4 W4 checkpoint** | 把 W4 final paired count / `final_test_touched=false` / 输出目录 / 是否进 main 归档 | 中（8D.3 之后） |
| 4 | **Step 3R-4.1 4-fold validation helper design** | 纯 markdown 先行；产出 `regime_validation_report.v1` | 低（W4 完成后；与 3R-3 candidate 配对启动） |
| 5 | **不推荐**跳过 W4 checkpoint | 必须先 8D.4 归档再考虑 4-fold | **❌** |
| 6 | **不推荐**让 W4 直接进 production decision | W4 仅作 cross-window validation 数据 | **❌** |
| 7 | **不推荐** 升级 04 required | Step 2G 全程边界 | **❌** |
| 8 | **不推荐** 触碰 2026 final test range | 永久封禁 | **❌** |
| 9 | **不推荐** R4 hard implementation | 三重 NO-GO 已锁定 | **❌** |
| 10 | **不推荐**让 `_PROTECTION_LAYER_CONNECTED` 翻 True / Gate 5 / Gate 6 自动 pass | 与 v1 / 3R-0 / 3R-4 一致 | **❌** |
| 11 | **不推荐** 把 smoke 输出 commit 进 main | 与 8D checkpoint §9 一致 | **❌** |
| 12 | **不推荐** 把 smoke 的 33.33% 精度当任何 pass / fail 依据 | 4 case 无统计意义 | **❌** |

**关键判断**：
- 顺序 = 本 checkpoint → 8D.3 full W4 → 8D.4 W4 checkpoint → 3R-4.1 design
- Step 2G-8D.2 与 Step 3R-2 / 3R-3 / 3R-4 v1 协议**解耦可并行**；3-fold v1
  不依赖 W4

---

## 13. 严守边界

本文是**纯 checkpoint markdown**：

- ❌ 没改任何代码（`services/*` / `ui/*` / `tests/*` / `scripts/*` 全部未触碰）
- ❌ 没改 DB schema
- ❌ 没写 DB
- ❌ 没运行 full W4 replay
- ❌ 没改 `run_predict` / `predict.py` / `scanner.py` /
  `prediction_store.py` / `app.py`
- ❌ 没改 `services/regime_features_builder.py` /
  `services/regime_labels_builder.py` /
  `services/regime_diagnostics_dashboard.py` /
  `services/anti_false_exclusion_dashboard.py` /
  `services/soft_metadata_simulator.py` /
  `services/protection_layer_diagnostics.py` /
  `services/historical_replay_training.py` /
  `services/three_system_replay_audit.py` /
  `services/replay_record_wiring.py` /
  `services/projection_three_systems_renderer.py` /
  `services/outcome_capture.py` /
  `ui/protection_layer_diagnostics_renderer.py` / 任何 ui 模块 /
  任何 builder
- ❌ 没改 `scripts/run_1005_three_system_replay.py` 或任何 replay 脚本
- ❌ 没改 04 / 05 / 07 任何 required 字段
- ❌ 没启用 `hard` / `forced_exclusion` /
  `anti_false_exclusion_triggered`
- ❌ 没接 `yfinance` / `requests` / 任何网络（本 checkpoint 阶段；
  smoke run 阶段 yfinance 已被 G1/G2 hard stop 限制在 `< 2026-01-01`）
- ❌ 没接 trading API / `longbridge` / `broker` / `paper_trade`
- ❌ 没让 `_PROTECTION_LAYER_CONNECTED` 翻 True
- ❌ 没让 `hard_gate_status.protection_layer_connected` 自动 pass
- ❌ 没改 `hard_exclusion_allowed` / `primary_blocker` 派生
- ❌ 没触碰 2026-01-01 之后 final test range
- ❌ 没把 smoke 输出 commit 进 main
- ❌ 没改 Step 3R-4 protocol thresholds（6 metric / 7 gate / 10 no-go）
- ❌ 没改 Step 3R-2 helper 行为
- ❌ 没改 Step 2G-8D design / checkpoint / audit / 8D.1A patch / 8D.1A checkpoint
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` /
  `avgo_agent.db.backup_*`
- ❌ 没运行 `pytest`（本轮纯文档；测试基线维持 commit `cd149ce` 时
  的 2689 / 0 failed / 10 skipped）
- ✅ 只新增 1 份 markdown checkpoint 文档（本文件）
