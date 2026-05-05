# Step 2G-8D.1A — Minimal Replay Script Patch Checkpoint

> **状态固化文档（minimal replay script patch checkpoint），不实现，不改代码，不写 DB，不运行 replay。**
> 本文档**冻结** Step 2G-8D.1A patch（commit `36e76c9`）的：7 项新
> CLI 参数、5 项 hard guard（G1–G5）、`w4_replay_manifest.v1` schema、
> 47 focused tests + 2689 全量 pytest 基线、tiny smoke 默认窗口与
> hard 约束、与 Step 3R-4 协议 / Step 2G-8D 的衔接关系。
>
> 本轮**不动任何代码**：不改 `predict.py` / `run_predict` /
> `scanner.py` / `prediction_store.py` / `app.py` / 任何 `ui/*` /
> `services/*` / `scripts/*` / 任何 builder / DB schema / 任何 test
> 中的任何一处。
>
> **本文不实现 patch、不跑 replay、不跑 smoke、不写 DB、不调 yfinance、
> 不接 trading API**；只在 markdown 层固化 patch 状态，作为后续
> 8D.2 tiny smoke 的强制 gate。

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
- **Step 2G-8D.1A** minimal replay script patch 已完成并进入 main
  （commit `36e76c9`）
- 本 checkpoint **固定**：
  - 7 项新 CLI 参数
  - 5 项 hard guard（G1–G5）的 done 状态与触发位置
  - `w4_replay_manifest.v1` schema 5 项不变量（继承 8D design / checkpoint）
  - 47 focused tests + 2689 全量 pytest 基线
  - tiny smoke 默认窗口与 hard 约束
  - 与 Step 3R-4 / Step 2G-8D 的衔接关系
- **tiny smoke 仍未运行**：本步骤只 patch + 测试，**不**真的跑 smoke /
  full W4 replay
- 本 checkpoint 是**纯状态归档**；**仍不**改代码 / 不写 DB / 不接网络 /
  不接 trading

---

## 2. 当前 main 状态

- main 最新 commit：**`36e76c9`**
- commit message：`feat(replay): add W4 range guards and manifest support`
- 上游：`origin/main` 已同步
- 测试基线：**2689 passed / 0 failed / 10 skipped / 26 warnings /
  94 subtests**（与 commit `36e76c9` 实测一致；Step 3R-2 终点 2642 →
  Step 2G-8D.1A 终点 2689，+47 净增；2642 基线零回归）

本步骤修改 / 新增文件（已 merge 到 main）：

| 路径 | 类型 | 说明 |
|---|---|---|
| `scripts/run_1005_three_system_replay.py` | 修改 | +6 module 常量 / +7 helper / argparse 5 新参数 / `run_audit` 5 keyword-only 参数 / `main` 增加 `_apply_tiny_smoke_defaults` + `_validate_w4_args` 起点检查 + manifest emission；改动 ~ 230 行 |
| `tests/test_run_1005_three_system_replay_w4_guards.py` | 新增 | 47 focused tests（argparse / tiny-smoke / 5 guards / 2 filter helpers / manifest builder + writer / main exit codes / 2 静态 import 锁定） |
| `tasks/step_1_contract_pipeline_summary.md` | 修改 | 新增 §37 |

`services/*` 全部未触碰；DB schema 未改；no `services.prediction_store`
/ `longbridge` / `broker` / `paper_trade` 引入（`ast.walk` 静态测试
锁定）。

本 checkpoint 文档（即本文件）尚未 commit；本轮只写文档、**不**
commit / push。

| 项 | 是否触碰 |
|---|---|
| 改代码 | ❌ 否 |
| 写 DB | ❌ 否 |
| 跑 replay | ❌ 否 |
| 跑 smoke | ❌ 否 |
| 接 yfinance / 网络 | ❌ 否 |
| 接 trading API | ❌ 否 |
| 触碰 2026 final test | ❌ 否 |
| 改 services/* | ❌ 否 |
| 改 DB schema | ❌ 否 |
| 改 04 / 05 / 07 required | ❌ 否 |

---

## 3. 新 CLI 参数

| 参数 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `--start-date` | str (ISO) | None | 显式起点；与 `--num-cases` tail 行为互斥 |
| `--end-date` | str (ISO) | None | 显式终点；必须 `< --final-test-cutoff` |
| `--final-test-cutoff` | str (ISO) | `"2026-01-01"` | hard cutoff；起点 + T+1 双重过滤 |
| `--tiny-smoke` | flag | `False` | 起 smoke 模式（默认 2024-08-05 → 2024-08-09），强制 `save-records=False` + `write-manifest=True`；output_dir 默认切到 smoke 目录 |
| `--write-manifest` | flag | `False` | 写 `w4_replay_manifest.v1` 到 `output_dir/validation_ready_manifest.json`（或 `--manifest-path`） |
| `--manifest-path` | Path | None | 显式 manifest 路径；默认 `output_dir/validation_ready_manifest.json` |
| `--allow-overwrite` | flag | `False` | 允许写入非空 output_dir（仅 W4 mode）；防覆盖 1005 baseline |

### 3.1 兼容性说明

| 项 | 行为 |
|---|---|
| **legacy `--num-cases` 行为保留** | ✅；不传 `--start-date` / `--end-date` 时走原 tail-N 路径 |
| **explicit start/end 优先** | ✅；任一非 None → 进入 W4 mode，忽略 `--num-cases` tail |
| **tiny-smoke 有默认窗口** | ✅；`2024-08-05 → 2024-08-09`，5 trading day |
| **legacy 1005 调用零回归** | ✅；2642 基线 + 47 新增 = 2689 passed / 0 failed |
| **legacy `--save-records`** | ✅ 在 non-W4 mode 仍允许；W4 mode 强制 reject（G3） |

---

## 4. 5 个 hard guards

| guard | status | purpose |
|---|---|---|
| **G1** range hard stop | **done** | `start_date / end_date` 必须 `< final_test_cutoff`；trading_days 起点过滤 `< cutoff`；起点 + 数据层双重 |
| **G2** T+1 boundary skip | **done** | outcome 跨 2026 不读取；任一 `pair (as_of, pred)` 越界 → skip + warning |
| **G3** save-records guard | **done** | W4 mode（explicit start/end OR `--tiny-smoke`）+ `--save-records=True` → `ValueError` + main exit 2；W4 不允许写 DB |
| **G4** output-dir guard | **done** | 防 W4 模式 output_dir 指向 1005 baseline；防覆盖非空目录（除非 `--allow-overwrite`） |
| **G5** manifest writer | **done** | 写 `w4_replay_manifest.v1`；含 `final_test_touched` defense-in-depth；证明 cutoff 已生效 |

### 4.1 触发位置

| guard | 触发函数 / 阶段 |
|---|---|
| G1 startup | `_validate_w4_args(args)` 在 `main` 调用 `run_audit` 之前 |
| G1 数据层 | `_filter_trading_days_by_range(days, start, end, final_test_cutoff)` 在 `_resolve_date_pairs` 内 |
| G2 | `_filter_pairs_by_cutoff(pairs, final_test_cutoff)` 在 `_resolve_date_pairs` 内 |
| G3 | `_validate_w4_args` |
| G4 | `_validate_w4_args` |
| G5 | `run_audit` 输出阶段；`_build_manifest` + `_write_manifest` |

### 4.2 W4 mode 判定

`_is_w4_mode(args) = tiny_smoke ∨ start_date is not None ∨ end_date is not None`。
legacy 1005 调用（无任何 W4 标记）**完全不**经过 G3 / G4 检查，
向后兼容。

---

## 5. tiny smoke 默认

| 项 | 值 |
|---|---|
| **默认窗口** | **`2024-08-05` → `2024-08-09`**（5 trading day；W4 起点附近，避开周末 2024-08-03 / 04） |
| **默认 output_dir** | `logs/historical_training/three_system_w4_smoke_2024_08_05_2024_08_09/` |
| **强制 `save_records=False`** | ✅；`_apply_tiny_smoke_defaults` 覆盖 |
| **强制 `write_manifest=True`** | ✅；`_apply_tiny_smoke_defaults` 覆盖 |
| **不覆盖旧目录** | ✅；G4 阻断；除非 `--allow-overwrite` |
| **本步骤是否运行 tiny smoke** | **❌ 否**；patch + 测试完成；smoke 由 8D.2 启动 |

### 5.1 启动命令（仅供 8D.2 参考；本步骤不执行）

```
python -m scripts.run_1005_three_system_replay \
  --tiny-smoke \
  --final-test-cutoff 2026-01-01
  # output_dir 默认 logs/historical_training/three_system_w4_smoke_2024_08_05_2024_08_09/
  # save_records 自动 False
  # write_manifest 自动 True
```

或显式：

```
python -m scripts.run_1005_three_system_replay \
  --start-date 2024-08-05 \
  --end-date 2024-08-09 \
  --final-test-cutoff 2026-01-01 \
  --output-dir logs/historical_training/three_system_w4_smoke_2024_08_05_2024_08_09/ \
  --write-manifest
  # 不传 --save-records
```

---

## 6. manifest schema

`w4_replay_manifest.v1`：

```json
{
  "schema_version": "w4_replay_manifest.v1",
  "replay_window": {"start": "...", "end": "..."},
  "final_test_cutoff": "2026-01-01",
  "final_test_touched": false,
  "records_generated": null,
  "paired_outcomes": null,
  "status": "ok|error|planned",
  "warnings": []
}
```

### 6.1 字段说明

| 字段 | 类型 | 说明 |
|---|---|---|
| `schema_version` | string | 总是 `"w4_replay_manifest.v1"` |
| `replay_window.start` | string \| null | 与 `--start-date` 一致 |
| `replay_window.end` | string \| null | 与 `--end-date` 一致 |
| `final_test_cutoff` | string | 与 `--final-test-cutoff` 一致；硬不变量 |
| `final_test_touched` | bool | defense-in-depth：在 `replay_results` 中检查任何 `as_of_date / prediction_for_date >= cutoff`；`true` → 整份报告作废 |
| `records_generated` | int \| null | 实际 pair 数（G1 + G2 过滤后）；本 patch 阶段 manifest writer 已实现，但 full W4 未跑 → 实际值由 8D.3 填入 |
| `paired_outcomes` | int \| null | `replay_result.ready ∧ actual_outcome.actual_close is not None` 的数量 |
| `status` | enum | `"ok"`（本 patch 已实现）/ `"error"`（任何 G1/G2/G3/G4 触发）/ `"planned"`（design / checkpoint 阶段） |
| `warnings` | list[str] | 累积的 G2 boundary skip + 其它运行时 warnings |

### 6.2 5 项不变量（继承 8D design / checkpoint）

| 不变量 | 说明 |
|---|---|
| `schema_version == "w4_replay_manifest.v1"` | 任何变体即视为非本协议输出 |
| `replay_window.start` | W4 默认 `"2024-08-03"`；smoke 默认 `"2024-08-05"` |
| `replay_window.end` | W4 默认 `"2025-12-31"`；smoke 默认 `"2024-08-09"` |
| `final_test_cutoff == "2026-01-01"` | 硬编码；`DEFAULT_FINAL_TEST_CUTOFF` |
| `final_test_touched == false` | 任何 `true` → 报告作废；本 patch 已经在 run_audit 中 wire 检查 |

### 6.3 manifest writer 状态

- **已实现**：`_build_manifest` + `_write_manifest`（`scripts/run_1005_three_system_replay.py`）
- **已 stub e2e 测试**：`RunAuditManifestE2ETests` 中 2 个 case
- **真实 W4 manifest**：本步骤**未生成**；由 8D.2 / 8D.3 实施时落盘

---

## 7. 测试覆盖

### 7.1 测试结果（commit `36e76c9` 实测）

| 命令 | 结果 |
|---|---|
| `pytest tests/test_run_1005_three_system_replay_w4_guards.py -q` | **47 passed** |
| `pytest -q`（全量） | **2689 passed / 10 skipped / 0 failed / 26 warnings / 94 subtests** |

测试基线累积：**Step 3R-2 终点 2642 → Step 2G-8D.1A 终点 2689**
（+47 净增；2642 基线零回归）。

### 7.2 测试矩阵（47 cases）

| 测试类 | 数量 | 覆盖点 |
|---|---|---|
| `ParseArgsTests` | 8 | 5 新 flag + cutoff 默认 `2026-01-01` + 自定义 cutoff + manifest_path 默认 None + legacy 兼容 |
| `TinySmokeDefaultsTests` | 6 | tiny-smoke 默认范围 / 强制 save_records=False / 强制 write_manifest=True / 默认 output_dir / 显式范围保留 / 非 smoke 无副作用 |
| `ValidateW4ArgsTests` | 11 | G1 / G3 / G4 全部触发路径 + 默认 1005 通过 + legacy save_records 通过 + tiny_smoke 互斥 + start>end |
| `FilterTradingDaysByRangeTests` | 3 | range + cutoff / 仅 cutoff / 仅 start |
| `FilterPairsByCutoffTests` | 3 | T+1 边界 skip / 安全范围 / as_of 自身越界 |
| `ResolveDatePairsTests` | 2 | explicit range / legacy num_cases 都施加 cutoff |
| `BuildManifestTests` | 5 | schema_version 强制 / 完整 shape / final_test_touched 默认 false / planned status / warnings 空 list |
| `WriteManifestTests` | 1 | 写盘 round-trip |
| `MainExitCodeTests` | 4 | end>=2026 / start>=2026 / save-records-with-W4 / output-dir-1005 全部 nonzero |
| `RunAuditManifestE2ETests` | 2 | smoke window stub e2e（manifest schema + 4 paired + final_test_touched=false）+ T+1 边界 stub e2e |
| `NoNewServiceImportsTests` | 1 | `ast.walk` 锁定 services/* 子集 = audit 4 项 baseline |
| `NoDBOrPredictionStoreImportTests` | 1 | `ast.walk` 锁定无 `services.prediction_store` / `longbridge` / `broker` / `paper_trade` |

### 7.3 测试覆盖关键点

- **explicit start/end parsed** → `ParseArgsTests`
- **tiny-smoke default range** → `TinySmokeDefaultsTests`
- **cutoff start/end rejected** → `ValidateW4ArgsTests` + `MainExitCodeTests`
- **W4 save-records rejected** → `ValidateW4ArgsTests` + `MainExitCodeTests`
- **output_dir guard** → `ValidateW4ArgsTests` + `MainExitCodeTests`
- **manifest writer schema** → `BuildManifestTests` + `WriteManifestTests` + `RunAuditManifestE2ETests`
- **T+1 boundary warning** → `FilterPairsByCutoffTests` + `RunAuditManifestE2ETests`
- **no DB / trading imports** → `NoNewServiceImportsTests` + `NoDBOrPredictionStoreImportTests`

---

## 8. 当前仍未做

| # | 仍未做 | 解封步骤 |
|---|---|---|
| 1 | **未运行 tiny smoke** | Step 2G-8D.2 |
| 2 | **未运行 full W4 replay** | Step 2G-8D.3（only after 8D.2 通过） |
| 3 | **未生成真实 W4 predictions / reviews** | Step 2G-8D.3 |
| 4 | **未生成真实 `regime_labels_snapshot.csv`** | Step 2G-8D.3（可选；3R-2 helper 已 merge，可在 patch 内 read-only 调用） |
| 5 | **未接 4-fold validation** | Step 3R-4.1（在 W4 完成后；纯 markdown 先行） |
| 6 | **未改 DB** | 永远不会改；W4 是 read-only artifact |
| 7 | **未接入 dashboard / UI** | Step 3R-2.1（可选；与本步骤解耦） |
| 8 | **未改 04 / 05 / 07 required** | 永远不会改；与 Step 2G 全程边界一致 |
| 9 | **未启 `_PROTECTION_LAYER_CONNECTED`** | 永远 False；与 8A v1 / 3R-0 / 3R-4 一致 |

---

## 9. 是否允许 8D.2 tiny smoke

**✅ conditional GO**。

### 9.1 conditional GO 前提

| # | 前提 | 满足方式 |
|---|---|---|
| 1 | 使用 tiny smoke window | `--tiny-smoke` 自动填默认 `2024-08-05 → 2024-08-09`，或显式 `--start-date / --end-date` 在该范围内 |
| 2 | output_dir 独立 | `--tiny-smoke` 自动切到 `three_system_w4_smoke_2024_08_05_2024_08_09/`；G4 阻 1005 / 非空目录 |
| 3 | `save_records=false` | `--tiny-smoke` 强制；G3 在 explicit W4 也 reject `--save-records` |
| 4 | `write_manifest=true` | `--tiny-smoke` 强制；显式 W4 时需手动加 `--write-manifest` |
| 5 | `final_test_cutoff=2026-01-01` | argparse 默认 |
| 6 | 不进 main | smoke 产物**不进 main**；仅在本地 / `.claude/scratch/` 验证（与 8D checkpoint §9 一致） |
| 7 | smoke 通过判据 | manifest `final_test_touched=false` + 4 对全部 ready=true + 输出文件齐 + 无 main DB 写入 + 无 G2/G3/G4 触发 |

### 9.2 仍 NO-GO

| # | 项 | 理由 |
|---|---|---|
| 1 | **full W4 replay** | 必须先 8D.2 smoke 通过；不允许跳过 smoke 直接 full（8D checkpoint §9.1 强制规则） |
| 2 | hard / forced / required upgrade | Step 2G 全程边界 + 三重 NO-GO（2G-8 / 8B / 8C） |
| 3 | 让 W4 自动让 candidate pass | W4 仅作 cross-window validation 数据；不进 hard gate |
| 4 | 触碰 2026 final test | 永久封禁；G1 + G2 双重 hard stop |
| 5 | 让 `_PROTECTION_LAYER_CONNECTED` 翻 True | 与 8A v1 / 3R-0 / 3R-4 一致 |

---

## 10. 与 Step 3R-4 的关系

| 维度 | Step 2G-8D.1A patch（本步骤） |
|---|---|
| 是否提供 W4 数据 | **❌ 否**（只是让 W4 replay 具备安全运行条件） |
| 是否产生 W4 paired records | **❌ 否**（patch + 测试完成；smoke / full 由 8D.2 / 8D.3 实施） |
| 是否改 3R-4 protocol | **❌ 否**（不改 6 metric / 7 gate / 10 no-go / `regime_validation_report.v1` schema） |
| 是否触发 3R-4 协议升级 | **❌ 否**；3R-4 仍是 **3-fold**（W1+W2+W3） |
| 何时升级到 4-fold | **only after** 8D.3 full W4 + 8D.4 W4 checkpoint 完成 |
| W4 是否自动让 candidate pass | **❌ 否**（W4 仅增加证据强度；任何 candidate 仍必须通过 7 gate / 6 metric） |

→ 本步骤**只**让 W4 replay 具备安全运行条件；**还没**产生 W4 数据；
3R-4 仍是 3-fold；只有 **8D.3 full W4 + 8D.4 checkpoint 完成后**，
才可进入 4-fold validation（由 3R-4.1 helper design 落地）。

---

## 11. 禁止事项

| # | 禁止 | 理由 |
|---|---|---|
| 1 | **不直接跑 full W4** | 必须先 8D.2 smoke 通过；不允许跳过 smoke |
| 2 | **不写 DB** | W4 是 read-only artifact；G3 强制 |
| 3 | **不覆盖 old logs**（`three_system_1005/` 等） | W1 / W2 / W3 baseline 必须保留；G4 强制 |
| 4 | **不接 trading**（`longbridge` / `broker` / `paper_trade`） | 永不；静态测试锁定 |
| 5 | **不启 hard / forced / anti_false_exclusion_triggered** | 三重 NO-GO（2G-8 / 8B / 8C） |
| 6 | **不改 04 / 05 / 07 required** | Step 2G 全程边界 |
| 7 | **不触碰 2026** | 永久封禁；G1 + G2 双重 hard stop |
| 8 | **不把 smoke 当 W4 validation** | smoke = 5 day patch 验证；W4 = 完整 2024-08-03 → 2025-12-31 |
| 9 | **不让 W4 直接调 formula** | candidate 必须先在 3R-3 design + 3R-4 protocol 下走完 |
| 10 | **不改 services/*** | patch 只在 `scripts/` + `tests/` + `tasks/` |
| 11 | **不改 3R-4 protocol thresholds** | 阈值调整必须经 launch review |
| 12 | **不改 3R-2 helper** | helper 已 merge；W4 仅 read-only 调用 |
| 13 | **不让 `_PROTECTION_LAYER_CONNECTED` 翻 True** | 与 v1 / 3R-0 / 3R-4 一致 |
| 14 | **不让 `hard_gate_status.protection_layer_connected` 自动 pass** | 同上 |
| 15 | **不改 `hard_exclusion_allowed` / `primary_blocker` 派生** | 同上 |
| 16 | **不触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*`** | 历史防护 |

---

## 12. 下一步建议

按推荐优先级：

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **commit 本 checkpoint** | 把 §1-13 patch 状态固化到 main | **本轮 / 下一轮** |
| 2 | **Step 2G-8D.2 tiny smoke** | 跑 `2024-08-05 → 2024-08-09` 5-day smoke；产物**不进 main**；本地 / `.claude/scratch/` 验证；实测 manifest `final_test_touched=false` + 4 paired + cutoff 起点 + T+1 边界全程 | **高**（commit 本 checkpoint 后立刻启动） |
| 3 | **Step 2G-8D.2 checkpoint** | 把 smoke 实测结果（paired count / runtime / manifest snapshot）归档；判定 8D.3 是否 GO | 中（8D.2 之后） |
| 4 | **Step 2G-8D.3 full W4 replay** | 跑完整 `2024-08-03 → 2025-12-31`；产物进 main（仅 csv / json / md，无 DB） | 中（8D.2 + 8D.2 checkpoint 之后） |
| 5 | **Step 2G-8D.4 W4 checkpoint** | W4 final paired count / `final_test_touched=false` / 输出目录归档 | 中（8D.3 之后） |
| 6 | **Step 3R-4.1 4-fold validation helper design** | 纯 markdown 先行；产出 `regime_validation_report.v1` | 低（W4 完成后；与 3R-3 candidate 配对启动） |
| 7 | **不推荐**直接跑 full W4 | 必须先 8D.2 smoke | **❌** |
| 8 | **不推荐**让 W4 直接进 production decision | W4 仅作 cross-window validation 数据 | **❌** |
| 9 | **不推荐** 升级 04 required | Step 2G 全程边界 | **❌** |
| 10 | **不推荐** 触碰 2026 final test range | 永久封禁 | **❌** |
| 11 | **不推荐** R4 hard implementation | 三重 NO-GO 已锁定 | **❌** |
| 12 | **不推荐**让 `_PROTECTION_LAYER_CONNECTED` 翻 True / Gate 5 / Gate 6 自动 pass | 与 v1 / 3R-0 / 3R-4 一致 | **❌** |

**关键判断**：
- 顺序 = 本 checkpoint → 8D.2 smoke → 8D.2 checkpoint → 8D.3 full W4 →
  8D.4 W4 checkpoint → 3R-4.1 design
- Step 2G-8D.1A 与 Step 3R-2 / 3R-3 / 3R-4 v1 协议**解耦可并行**；
  3-fold v1 不依赖 W4

---

## 13. 严守边界

本文是**纯 checkpoint markdown**：

- ❌ 没改任何代码（`services/*` / `ui/*` / `tests/*` / `scripts/*` 全部未触碰）
- ❌ 没改 DB schema
- ❌ 没写 DB
- ❌ 没运行 replay
- ❌ 没运行 smoke
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
- ❌ 没接 `yfinance` / `requests` / 任何网络
- ❌ 没接 trading API / `longbridge` / `broker` / `paper_trade`
- ❌ 没让 `_PROTECTION_LAYER_CONNECTED` 翻 True
- ❌ 没让 `hard_gate_status.protection_layer_connected` 自动 pass
- ❌ 没改 `hard_exclusion_allowed` / `primary_blocker` 派生
- ❌ 没触碰 2026-01-01 之后 final test range
- ❌ 没运行 replay / 没新写 replay 行
- ❌ 没改 Step 3R-4 protocol thresholds（6 metric / 7 gate / 10 no-go）
- ❌ 没改 Step 3R-2 helper 行为
- ❌ 没改 Step 2G-8D design / checkpoint / audit
- ❌ 没改 Step 2G-8D.1A patch（已 merge 在 commit `36e76c9`，本 checkpoint 不动）
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` /
  `avgo_agent.db.backup_*`
- ❌ 没运行 `pytest`（本轮纯文档；测试基线维持 commit `36e76c9` 时
  的 2689 / 0 failed / 10 skipped）
- ✅ 只新增 1 份 markdown checkpoint 文档（本文件）
