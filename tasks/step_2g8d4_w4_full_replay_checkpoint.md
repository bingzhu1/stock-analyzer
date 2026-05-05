# Step 2G-8D.4 — W4 Full Replay Checkpoint

> **状态固化文档（W4 full replay checkpoint），不实现，不改代码，不写 DB，不运行 replay。**
> 本文档**冻结** Step 2G-8D.3 full W4 replay 的：命令、W4 范围（2024-08-03
> → 2025-12-31）、`w4_replay_manifest.v1` manifest 摘要、353 paired
> 实测、10 输出文件清单、DB / git 验证、final-test cutoff 验证、对
> Step 3R-4 4-fold validation 的 conditional GO 解锁。
>
> 本轮**不动任何代码**：不改 `predict.py` / `run_predict` /
> `scanner.py` / `prediction_store.py` / `app.py` / 任何 `ui/*` /
> `services/*` / `scripts/*` / 任何 builder / DB schema / 任何 test
> 中的任何一处。
>
> **本文不实施 4-fold validation、不再跑 replay、不写 DB、不接
> trading API**；只在 markdown 层固化 W4 实测状态，作为后续 3R-4.1
> validation helper design 的强制 gate。

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
- **Step 2G-8D.2** tiny smoke replay + checkpoint 已完成并进入 main
  （commit `7abf66e`；smoke 输出本地，不进 main）
- **Step 2G-8D.3** full W4 replay 已**成功运行**（exit code 0；本
  checkpoint 阶段 W4 输出本地，不进 main）
- 本 checkpoint **固定**：
  - W4 命令 + 边界
  - W4 范围（2024-08-03 → 2025-12-31）
  - `w4_replay_manifest.v1` manifest 实测摘要（353 paired / status=ok / final_test_touched=false / warnings=[]）
  - 10 输出文件清单
  - W4 摘要指标（含明确 NOT pass/fail 依据）
  - DB / git / final-test cutoff 三重验证
  - 对 Step 3R-4 4-fold validation 的 conditional GO 解锁
- W4 输出目录**暂不进 main**；是否进 main 留给后续（例：8D.5 retention
  decision 或 3R-4.1 helper design 阶段决定）

---

## 2. 当前 main 状态

- main 最新 commit：**`7abf66e`**
- commit message：`docs(contract): Step 2G-8D.2 tiny smoke replay checkpoint`
- 上游：`origin/main` 已同步
- 测试基线：**2689 passed / 0 failed / 10 skipped / 26 warnings /
  94 subtests**（与 commit `36e76c9` 一致；W4 replay 只读跑，**不**
  改代码 / **不**改测试 → 基线不变）

| 项 | 是否触碰 |
|---|---|
| 改代码 | ❌ 否 |
| 写 DB | ❌ 否 |
| 启 hard / forced / anti_false_exclusion_triggered | ❌ 否 |
| 改 services/* / scripts/* / tests/* | ❌ 否 |
| 改 DB schema | ❌ 否 |
| 跑额外 replay | ❌ 否 |
| 接 trading API | ❌ 否 |
| 触碰 2026 final test | ❌ 否 |

本 checkpoint 文档（即本文件）尚未 commit；本轮只写文档、**不**
commit / push。

---

## 3. W4 命令

```
python3 scripts/run_1005_three_system_replay.py \
  --start-date 2024-08-03 \
  --end-date 2025-12-31 \
  --final-test-cutoff 2026-01-01 \
  --output-dir logs/historical_training/three_system_w4_2024_08_2025_12 \
  --write-manifest
```

| 项 | 说明 |
|---|---|
| **未传 `--save-records`** | ✅；G3 在 W4 mode 强制 reject；本命令显式不传 |
| **未传 `--allow-overwrite`** | ✅；输出目录预先确认 ABSENT，G4 不触发 |
| **输出目录预先确认** | `test -e logs/historical_training/three_system_w4_2024_08_2025_12 → ABSENT` |
| **执行位置** | **main 工作树**（`/Users/may/Desktop/stock-analyzer-main/`） |
| **exit code** | **0** |
| **runtime** | ~ 11 分钟（10:44 启动 → 10:55 完成） |
| **与 8D.2 smoke 命令的差异** | 显式 `--start-date` + `--end-date` 替代 `--tiny-smoke` 默认；显式 `--output-dir` 而非 smoke 默认目录 |

---

## 4. W4 范围

| 字段 | 值 |
|---|---|
| **start** | **`2024-08-03`** |
| **end** | **`2025-12-31`** |
| **`final_test_cutoff`** | **`2026-01-01`**（hard） |
| **是否含 2026** | **❌ 否**（永久封禁；G1 + G2 双重 hard stop） |
| **与 Step 3R-4 W4 optional window 是否一致** | **✅ 完全一致**（与 3R-4 §3.2 / 3R-4 checkpoint §3 / 8D design §3 / 8D checkpoint §3 / 8D.1A checkpoint §6 全部对齐） |
| **W4 trading-day 跨度** | ~ 350 day（实测 353 pair → 354 trading day filtered） |
| **是否覆盖 W3 / W2 / W1** | ❌ 否；W4 起点 `2024-08-03` = W3 终点 `2024-08-02` + 1 |

---

## 5. manifest 摘要

```json
{
  "schema_version": "w4_replay_manifest.v1",
  "replay_window": {"start": "2024-08-03", "end": "2025-12-31"},
  "final_test_cutoff": "2026-01-01",
  "final_test_touched": false,
  "records_generated": 353,
  "paired_outcomes": 353,
  "status": "ok",
  "warnings": []
}
```

| 字段 | 实测值 | 是否核心通过条件 |
|---|---|---|
| `schema_version` | `"w4_replay_manifest.v1"` | ✅ |
| `replay_window.start` | `"2024-08-03"` | ✅ |
| `replay_window.end` | `"2025-12-31"` | ✅ |
| `final_test_cutoff` | `"2026-01-01"` | ✅ |
| **`final_test_touched`** | **`false`** | **✅✅ 核心通过条件** |
| `records_generated` | **`353`** | ✅ |
| `paired_outcomes` | **`353`** | ✅ |
| **`status`** | **`"ok"`** | **✅** |
| **`warnings`** | **`[]`** | **✅**（G2 boundary skip 未触发） |

### 5.1 强调

- **`final_test_touched=false`** 是 8D.4 → 3R-4 4-fold conditional GO 的**核心通过条件**
- **`warnings=[]`** 表明 G2 未触发 —— G1 起点过滤已在 trading_days 阶段把任何 `>= 2026-01-01` 的 row 全部移除，G2 边界检查未发现越界 pair
- `status="ok"` 表示 G1/G2/G3/G4/G5 全部正常工作，无错误路径触发
- `paired_outcomes == records_generated == 353` 表明每对 (as_of, prediction_for_date) 都成功配对真实 outcome，**无降级 / 无 ready=false**

---

## 6. 输出目录与文件

### 6.1 输出目录

`logs/historical_training/three_system_w4_2024_08_2025_12/`

### 6.2 10 个文件清单

| 文件 | 字节 | 来源 |
|---|---:|---|
| `validation_ready_manifest.json` | 282 | 8D.1A 新增 manifest writer |
| `three_system_replay_results.jsonl` | 1,073,105 | per-case full audit |
| `three_system_replay_summary.md` | 1,668 | summary markdown |
| `three_system_replay_summary.json` | 4,572 | summary JSON |
| `negative_system_stats.csv` | 28,297 | per-case |
| `record_02_projection_stats.csv` | 37,315 | per-case |
| `confidence_evaluator_stats.csv` | 23,910 | per-case |
| `error_cases.csv` | 12,224 | filter |
| `false_exclusion_cases.csv` | 32,456 | filter |
| `high_confidence_wrong_cases.csv` | 202 | filter |

### 6.3 输出处置

| 项 | 状态 |
|---|---|
| 输出目录 git 状态 | **untracked** |
| 是否进 main | **❌ 暂不**（本 checkpoint 不 add；后续是否进 main 由单独决策决定，例：8D.5 retention decision 或 3R-4.1 helper design 阶段） |
| 是否覆盖 1005 baseline | **❌ 否**（独立目录） |
| 是否覆盖 smoke 输出 | **❌ 否**（独立目录） |
| 是否可删除 | ✅；W4 输出可整体删除而不影响 main 任何 baseline |
| 是否可重跑 | ✅；幂等；G4 已防覆盖（重跑需 `--allow-overwrite` 或新目录） |
| 是否写主 DB | **❌ 否** |

---

## 7. W4 摘要指标

来自 `three_system_replay_summary.md` / `.json`（read-only diagnostics）：

| 指标 | 实测值 |
|---|---|
| `total_cases` | 353 |
| `completed_cases` | 353 |
| `failed_cases` | 0 |
| `ready_rate` | 100.00% |
| **`direction_accuracy`** | **47.50%** |
| `accuracy_by_confidence.medium` | 32.35% |
| `accuracy_by_confidence.low` | 46.79% |
| `accuracy_by_confidence.unknown` | 60.00% |
| top error category | `wrong_direction: 126` / `correct: 114` |
| `triggered_count`（negative system） | **229** |
| `exclude_big_up_count` | 168 |
| `exclude_big_down_count` | 61 |
| `no_exclusion_count` | 124 |
| **`false_exclusion_count`** | **52** |
| `final_direction_distribution` | 偏多=167 / 偏空=85 / 中性=101 |
| `five_state_top1_distribution` | 大涨=26 / 小涨=102 / 震荡=127 / 小跌=50 / 大跌=48 |
| **`five_state_top1_accuracy`** | **20.40%** (n=353) |

### 7.1 强调（不是 pass / fail 依据）

| # | 警告 |
|---|---|
| 1 | **这些指标不是 candidate / formula / threshold 的 pass / fail 依据**——全部由 Step 3R-4 协议下的 4-fold validation 工具产出 `regime_validation_report.v1` 报告决定 |
| 2 | **不能据此调整 formula**——任何调阈值都必须经 launch review；用 W4 指标"反推"调参视为 final-test 风险（虽然 W4 不是 final-test，但跨窗 overfit 必须避免） |
| 3 | **不能据此让 candidate 自动 pass**——W4 仅增加证据强度，不改 7 gate / 6 metric / 10 no-go |
| 4 | `direction_accuracy=47.50%` 与 W3 (~ 56 paired) / W2 / W1 的对比仍需 4-fold helper 实施后给出 |
| 5 | `false_exclusion_count=52` 是绝对计数，不是 fer；fer = correct/paired 必须按候选切片单独计算（与 Step 2G-7C / 8C 一致） |

→ W4 摘要指标仅作 read-only diagnostics；任何 cross-window 评估**必须**
等 **Step 3R-4.1 4-fold validation helper design + 实施**。

---

## 8. DB / git 验证

### 8.1 DB 状态

| DB 文件 | mtime（W4 后） | 是否被 W4 修改 |
|---|---|---|
| `avgo_agent.db` | `May 4 02:34`（W4 之前） | **❌ 未修改** |
| `data/market_data.db` | `Apr 29 00:02`（W4 之前） | **❌ 未修改** |
| 任何 `avgo_agent.db.backup_*` | 无新增（保持 7 个） | **❌ 无新增** |

→ W4 没有写任何 DB（与 G3 + 默认 `--save-records=False` 一致）。

### 8.2 git 状态

| 路径 | 状态 |
|---|---|
| 任何 tracked file | **未 modified**（含 `scripts/run_1005_three_system_replay.py` / `services/*` / `tests/*` / `tasks/*`） |
| `logs/historical_training/three_system_w4_2024_08_2025_12/` | **untracked**；本 checkpoint 不 add |
| `logs/historical_training/three_system_w4_smoke_2024_08_05_2024_08_09/` | **untracked**（来自 8D.2 smoke；保持 untracked） |
| `logs/historical_training/three_system_1005/` | **untracked**（与 W4 之前一致） |
| `logs/prediction_log.jsonl`（worktree side） | **untracked**；环境产物；**不 add** |
| `agent_loop.py` / `avgo_agent.db.backup_*` / `.claude/worktrees/` / `.claude/handoffs/*` | **untracked**；**不 add** |

→ W4 没有改任何 tracked 文件；W4 输出目录保持 untracked，按指令不 add。

---

## 9. final test / cutoff 验证

| 检查 | 实测 | 通过 |
|---|---|---|
| `final_test_touched` | **`false`** | ✅ |
| `replay_window.end` | **`"2025-12-31"`** | ✅（不含 2026） |
| `warnings` | **`[]`** | ✅（无 G2 边界 skip） |
| W4 progress 最末几条（来自 run log） | `2025-11-25` / `2025-12-01` / `2025-12-08` / `2025-12-15` / `2025-12-16` / `353/353` | ✅（全部 < 2026） |
| 是否读取 / 生成 2026 row | **❌ 否**（G1 起点过滤 trading_days；G2 兜底） | ✅ |
| 是否触碰 T+1 边界（即 `as_of_date=2025-12-31` 配 `prediction_for_date >= 2026-01-01`） | **❌ 否**（G1 起点已把 trading_days 限制到 `< 2026-01-01`，最末 pair 是 `(2025-12-30, 2025-12-31)`，pred 仍 `< cutoff`） | ✅ |
| `data_cutoff_used`（与 3R-4 schema 一致语义） | `"2025-12-31"`（≤ 2025-12-31 硬不变量） | ✅ |
| 是否在 hyperparameter / threshold tuning 中读取 W4 之外数据 | **❌ 否**（本 checkpoint 不调阈值） | ✅ |

→ G1（起点 + 数据层）+ G2（T+1 边界）+ G5（manifest defense-in-depth）
**三重 hard stop 全部生效**；2026 final test range 完全未被触碰。

---

## 10. 是否解锁 4-fold validation

**✅ conditional GO**：Step 3R-4 协议从 **3-fold** 升级到 **4-fold**
（W1 / W2 / W3 / W4 都做一次 held-out）。

### 10.1 conditional GO 前提

| # | 前提 | 满足方式 |
|---|---|---|
| 1 | **W4 输出保持可用** | `logs/historical_training/three_system_w4_2024_08_2025_12/` 10 个文件齐；本 checkpoint 锁定不可被覆盖（除非显式 `--allow-overwrite`） |
| 2 | **W4 manifest `final_test_touched=false`** | 实测 ✅；§9 三重验证 |
| 3 | **W4 paired ≥ 阈值** | 353 paired（远超 §6 `minimum_window_sample_size ≥ 20` per-fold；总 paired 远超 30） |
| 4 | **4-fold helper / report 仍需单独设计** | **Step 3R-4.1 4-fold validation helper design**（纯 markdown 先行；产出 `regime_validation_report.v1`） |
| 5 | **W4 不改 3R-4 protocol** | ✅；本 checkpoint 不改 6 metric / 7 gate / 10 no-go |
| 6 | **W4 不自动让 candidate pass** | ✅；W4 仅增加证据强度；任何 candidate 仍必须**完整**通过 7 gate / 6 metric |
| 7 | **W4 fold 失败 → candidate 作废** | 与 3R-4 §4.2 worst-window 决胜规则一致 |

### 10.2 仍 NO-GO

| # | 项 | 理由 |
|---|---|---|
| 1 | 把 W4 当 final test | final test = 2026-01-01 → ∞；W4 = 2024-08-03 → 2025-12-31 |
| 2 | 用 W4 指标直接调 formula | 任何调阈值都必须经 launch review |
| 3 | hard / forced / required upgrade | Step 2G 全程边界 + 三重 NO-GO（2G-8 / 8B / 8C） |
| 4 | 让 Gate 5 / Gate 6 自动 pass | 与 v1 / 3R-0 / 3R-4 一致 |
| 5 | 让 `_PROTECTION_LAYER_CONNECTED` 翻 True | 同上 |
| 6 | 跳过 3R-4.1 helper design 直接产 4-fold report | 必须先纯 markdown 先行 |
| 7 | 把 W4 47.50% direction_accuracy 当任何 pass / fail 依据 | W4 摘要不是 candidate-level fer / nb / acc_delta |

---

## 11. 仍然禁止

| # | 禁止 | 理由 |
|---|---|---|
| 1 | **不启 hard / forced / anti_false_exclusion_triggered** | 三重 NO-GO（2G-8 / 8B / 8C） |
| 2 | **不改 04 / 05 / 07 required** | Step 2G 全程边界 |
| 3 | **不让 Gate 5 / Gate 6 自动 pass** | 与 v1 / 3R-0 / 3R-4 一致 |
| 4 | **不把 W4 summary 当 validation pass** | summary 是 read-only diagnostics |
| 5 | **不把 W4 输出直接 commit 进 main** | 本 checkpoint 不 add；后续单独决策 |
| 6 | **不接 trading**（`longbridge` / `broker` / `paper_trade`） | 永不 |
| 7 | **不触碰 2026** | 永久封禁；G1 + G2 双重 hard stop |
| 8 | **不直接产 4-fold report 而跳过 3R-4.1 design** | 必须 markdown 先行 |
| 9 | **不写 DB**（main DB / `data/market_data.db`） | W4 是 read-only artifact |
| 10 | **不让 `_PROTECTION_LAYER_CONNECTED` 翻 True** | 与 v1 / 3R-0 / 3R-4 一致 |
| 11 | **不改 services/* / DB schema / scripts/* / tests/*** | 本 checkpoint 是纯文档 |
| 12 | **不改 3R-4 protocol thresholds** | 阈值调整必须经 launch review |
| 13 | **不改 3R-2 helper 行为** | helper 已 merge；W4 仅 read-only 调用 |
| 14 | **不触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*`** | 历史防护 |
| 15 | **不把 W4 47.50% direction_accuracy 当 candidate / formula / threshold 依据** | 必须经 4-fold validation |
| 16 | **不直接进入 3R-5 formula design / 3R-6 simulator** | 必须先过 3R-3 + 3R-4.1 |

---

## 12. 下一步建议

按推荐优先级：

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **commit 本 checkpoint** | 把 §1-13 W4 实测状态固化到 main | **本轮 / 下一轮** |
| 2 | **Step 3R-4.1 4-fold validation helper design** | 纯 markdown 先行；产出 `regime_validation_report.v1` schema 实施版 + 计算流程；为未来 candidate 在 4-fold 协议下报告做准备 | **高**（commit 本 checkpoint 后立刻启动） |
| 3 | **Step 2G-8D.5 W4 output retention decision**（可选） | 决定 W4 输出是否进 main、retention 期限、备份规则；纯 markdown | 中（与 3R-4.1 解耦可并行） |
| 4 | **Step 3R-3** continuous smoothing candidate design | 用 logistic / kernel / spline 替代 4×4 lookup；read-only simulator design；纯 markdown 先行 | 中（需要 3R-4.1 协议落地） |
| 5 | **不推荐**直接跳到 formula / simulator / hard | 必须先过 3R-4.1 + 3R-3 在 4-fold 协议下出报告 | **❌** |
| 6 | **不推荐**让 W4 直接进 production decision | W4 仅作 cross-window validation 数据 | **❌** |
| 7 | **不推荐** 升级 04 required | Step 2G 全程边界 | **❌** |
| 8 | **不推荐** 触碰 2026 final test range | 永久封禁 | **❌** |
| 9 | **不推荐** R4 hard implementation | 三重 NO-GO 已锁定 | **❌** |
| 10 | **不推荐**让 `_PROTECTION_LAYER_CONNECTED` 翻 True / Gate 5 / Gate 6 自动 pass | 与 v1 / 3R-0 / 3R-4 一致 | **❌** |
| 11 | **不推荐** 把 W4 47.50% direction_accuracy 当任何 pass / fail 依据 | 必须经 4-fold validation | **❌** |

**关键判断**：
- 顺序 = 本 checkpoint → **3R-4.1 design**（纯 markdown）→ 3R-3 design
  → 3R-5 formula design → 3R-6 simulator → 3R-7 sidecar
- Step 2G-8D 系列至此**收官**：design / checkpoint / audit / 8D.1A patch
  / 8D.2 smoke + checkpoint / 8D.3 full W4 / 8D.4 W4 checkpoint 全部
  完成；W4 数据层准备就绪
- Step 3R 系列下一步进入**评分层**（3R-4.1 helper → 3R-3 candidate
  → 3R-5 formula → 3R-6 simulator）

---

## 13. 严守边界

本文是**纯 checkpoint markdown**：

- ❌ 没改任何代码（`services/*` / `ui/*` / `tests/*` / `scripts/*` 全部未触碰）
- ❌ 没改 DB schema
- ❌ 没写 DB
- ❌ 没跑额外 replay
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
- ❌ 没接 trading API / `longbridge` / `broker` / `paper_trade`
- ❌ 没让 `_PROTECTION_LAYER_CONNECTED` 翻 True
- ❌ 没让 `hard_gate_status.protection_layer_connected` 自动 pass
- ❌ 没改 `hard_exclusion_allowed` / `primary_blocker` 派生
- ❌ 没触碰 2026-01-01 之后 final test range
- ❌ 没把 W4 输出 commit 进 main（W4 输出保持 untracked）
- ❌ 没改 Step 3R-4 protocol thresholds（6 metric / 7 gate / 10 no-go）
- ❌ 没改 Step 3R-2 helper 行为
- ❌ 没改 Step 2G-8D design / checkpoint / audit / 8D.1A patch / 8D.1A
  checkpoint / 8D.2 smoke / 8D.2 checkpoint
- ❌ 没把 W4 摘要指标当 candidate / formula / threshold 依据
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` /
  `avgo_agent.db.backup_*`
- ❌ 没运行 `pytest`（本轮纯文档；测试基线维持 commit `7abf66e` 时
  的 2689 / 0 failed / 10 skipped）
- ✅ 只新增 1 份 markdown checkpoint 文档（本文件）
