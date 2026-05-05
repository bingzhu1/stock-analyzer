# Step 3R-3.3 — 4-Fold Validation Run Checkpoint

> **状态固化文档（4-fold validation run checkpoint），不实现，不改代码，不写 DB，不运行 replay / validation。**
> 本文档**冻结** Step 3R-3.3 design（commit `8a24295`）的：candidate /
> adapter / helper 三层职责、10 步 orchestration flow、`candidate_threshold`
> policy（v1 seed 0.60，**不扫**）、`regime_validation_run_manifest.v1`
> schema、6 层 final-test guard、first acceptance target（**first run
> 不需要 pass**）、no-go rules、与 hard / required / 2026 边界、允许
> 下一步、禁止事项。
>
> 本轮**不动任何代码**：不改 `predict.py` / `run_predict` /
> `scanner.py` / `prediction_store.py` / `app.py` / 任何 `ui/*` /
> `services/*`（含 `services/continuous_smoothing_candidate.py` /
> `services/replay_validation_record_adapter.py` /
> `services/regime_validation_helper.py` /
> `services/regime_labels_builder.py`）/ `scripts/*` / 任何 builder /
> DB schema / 任何 test 中的任何一处。
>
> **本文不实施 orchestrator、不跑 validation、不写 DB、不接 trading
> API**；只在 markdown 层固化 caller 设计状态，作为后续 Step 3R-3.3A
> dry-run orchestrator implementation / 3R-3.3B limited-record smoke /
> 3R-3.3C real W1-W4 validation run 的强制 gate。

---

## 1. 当前完成状态

- **Step 3 calibration restart launch review** 已完成并进入 main
  （commit `b8c781d`）
- **Step 3R-0** restart scope checkpoint 已完成并进入 main（commit
  `1b7288e`）
- **Step 3R-1** regime label design + checkpoint 已完成并进入 main
  （commits `a8df93a` / `8d4fe8f`）
- **Step 3R-2** read-only regime labels builder + checkpoint 已完成并
  进入 main（commits `e2a681b` / `db7618b`）
- **Step 3R-4** cross-window validation protocol design + checkpoint
  已完成并进入 main（commits `a58aad4` / `abe3ba2`）
- **Step 2G-8D** extend replay coverage 系列已收官（commits `170617c`
  ... `4bdd782`）；W4 paired_outcomes=353 / `final_test_touched=false`
- **Step 3R-4.1** 4-fold validation helper design + checkpoint 已完成
  并进入 main（commits `8e27254` / `295ccdd`）
- **Step 3R-4.2** read-only validation helper + checkpoint 已完成并
  进入 main（commits `c669c2f` / `5e58fee`）
- **Step 3R-3** continuous smoothing candidate design + checkpoint
  已完成并进入 main（commits `65fe411` / `596e013`）
- **Step 3R-3.1** read-only candidate generator + checkpoint 已完成并
  进入 main（commits `5e498bc` / `d0c1387`）
- **Step 3R-4.3** real replay record adapter design + checkpoint 已完成
  并进入 main（commits `9da5e57` / `2ce8230`）
- **Step 3R-4.3A** adapter implementation + checkpoint 已完成并进入
  main（commits `3586c05` / `608e2bf`）
- **Step 3R-3.3** 4-fold validation run design 已完成并进入 main
  （commit `8a24295`）
- 本 checkpoint **固定**：
  - candidate / adapter / helper 三层职责 + 解耦原则
  - 10 步 orchestration flow + 内存流转
  - candidate_threshold v1 seed = 0.60 + 不扫 / 不学 / 不反推
  - run output directory（独立本地目录，不进 main）+ 4 输出文件
  - `regime_validation_run_manifest.v1` 12 字段 schema + 5 项不变量
  - 6 层 final-test guard
  - first acceptance target（**first run 不需要 pass**）
  - 10 项 no-go rules
  - 与 hard / required / 2026 边界
- **Step 3R-3.3A dry-run orchestrator implementation 仍未启动**：本
  checkpoint 是 3R-3.3A 之前的强制 gate

---

## 2. 当前 main 状态

- main 最新 commit：**`8a24295`**
- commit message：`docs(contract): Step 3R-3.3 4-fold validation run design`
- 上游：`origin/main` 已同步
- 测试基线：**2801 passed / 0 failed / 10 skipped / 26 warnings /
  94 subtests**（与 commit `3586c05` 一致；本 checkpoint 阶段无代码
  改动 → 基线不变）

本步骤新增文件（已 merge 到 main）：

| 路径 | 类型 | 说明 |
|---|---|---|
| `tasks/step_3r3_3_4fold_validation_run_design.md` | 新增 | 16 节、435 行；caller / orchestrator 设计 + 10 步 flow + threshold policy + manifest schema + 6 层 hard stop |

本 checkpoint 文档（即本文件）尚未 commit；本轮只写文档、**不**
commit / push。

| 项 | 是否触碰 |
|---|---|
| 改代码 | ❌ 否 |
| 写 DB | ❌ 否 |
| 跑 replay | ❌ 否 |
| 跑 validation | ❌ 否 |
| 改 services/* / scripts/* / tests/* | ❌ 否 |
| 改 DB schema | ❌ 否 |
| 接 yfinance / 网络 | ❌ 否 |
| 接 trading API | ❌ 否 |
| 触碰 2026 final test | ❌ 否 |

---

## 3. 三层职责

| layer | API | 输出 | forbidden |
|---|---|---|---|
| **candidate** | `build_continuous_smoothing_candidate(regime_labels, ...)` | `continuous_smoothing_candidate.v1` | pass/fail；threshold；coefficient 优化 |
| **adapter** | `build_replay_validation_records(rows, ..., candidate_threshold, w4_manifest)` | `replay_validation_records.v1` | metrics / gates；调用 evaluator helper；读文件 |
| **helper** | `build_regime_validation_report(records, ..., w4_manifest_path)` | `regime_validation_report.v1`（6 metric / 7 gate / worst-window / overall_status） | 跑 replay；调阈值；写 DB |

### 3.1 解耦原则

| 原则 | 状态 |
|---|---|
| **candidate 不知道 records / windows** | ✅ |
| **adapter 不知道 metrics / gates** | ✅；不调 evaluator helper |
| **helper 不知道 jsonl / candidate internals** | ✅；只接受任何符合 record schema 的 list |
| **三层调用顺序固定**：candidate → adapter → helper | ✅；orchestrator 是唯一串联层 |
| **不允许跨层 wiring** | ✅；helper 不直接调 candidate；candidate 不输出 records |

---

## 4. orchestration flow

| # | 步骤 | 实施 |
|---|---|---|
| 1 | **Load W4 manifest and validate** | 解析 `validation_ready_manifest.json` 为 dict；adapter 启动时 + helper `_validate_w4_manifest` 双重校验 |
| 2 | **Load replay rows** | 读 W4 jsonl + W1/W2/W3 来源；累积成 `replay_rows: list[dict]` |
| 3 | **Enforce `analysis_date < cutoff`** | 对每条 row 检查 `as_of_date >= 2026-01-01` → skip + warning + `final_test_touched=true` |
| 4 | **Build `regime_labels` as of `analysis_date`** | 调 `build_regime_labels(...)` |
| 5 | **Build `continuous_smoothing_candidate.v1`** | 调 `build_continuous_smoothing_candidate(regime_labels, ...)` |
| 6 | **Attach candidate to row in memory** | `row["candidate"] = candidate_dict`（不写 jsonl） |
| 7 | **Call `build_replay_validation_records`** | `candidate_threshold=0.60` + `w4_manifest=manifest` |
| 8 | **Call `build_regime_validation_report`** | 输入 records；得到 `regime_validation_report.v1` |
| 9 | **Write local report files** | 4 文件落盘到独立 timestamp 目录 |
| 10 | **Do not write DB** | 全程**不**写 DB；caller 永远不导入 `services.prediction_store` 或 `sqlite3` |

### 4.1 内存流转

```
W1/W2/W3/W4 jsonl rows
        │
        ▼
[per row] build_regime_labels  (3R-2)
        │
        ▼  regime_labels.v1
        │
[per row] build_continuous_smoothing_candidate  (3R-3.1)
        │
        ▼  continuous_smoothing_candidate.v1
        │  (attached to row as row["candidate"])
        │
[batch] build_replay_validation_records  (3R-4.3A)
        │
        ▼  replay_validation_records.v1  ← write to disk
        │
[batch] build_regime_validation_report  (3R-4.2)
        │
        ▼  regime_validation_report.v1   ← write to disk
        │
        write run_manifest.json + summary.md
```

---

## 5. candidate_threshold policy

| 项 | 值 |
|---|---|
| **v1 seed** | **`0.60`** |
| **caller 必须显式传入** | ✅（adapter API required；no default） |
| **是否 optimized** | **❌ 否**；design seed |
| **是否允许扫 threshold** | **❌ 否** |
| **是否允许学 threshold** | **❌ 否** |
| **是否允许用 validation 结果反推 threshold** | **❌ 否** |
| **未来 sweep 触发方式** | 单独 Step（design only，纯 markdown 先行）+ 必须经 launch review |

### 5.1 强约束

| 约束 | 状态 |
|---|---|
| **不扫 threshold** | ✅ |
| **不学 threshold** | ✅ |
| **不调 SEED 系数**（3R-3.1 模块常量） | ✅ |
| **不调 6 metric / 7 gate threshold**（3R-4 protocol） | ✅ |
| **不允许 caller 在调用时 override 任何 SEED / gate threshold** | ✅ |
| **first run 失败时不调阈值** | ✅；与 §9 first acceptance 一致 |

---

## 6. run output directory

```
logs/regime_validation/continuous_smoothing_v1_4fold_YYYYMMDD_HHMMSS/
```

`YYYYMMDD_HHMMSS` 由 caller 启动时生成。

### 6.1 输出 4 文件

| 文件 | 内容 |
|---|---|
| `replay_validation_records.json` | adapter 输出的 `replay_validation_records.v1` |
| `regime_validation_report.json` | helper 输出的 `regime_validation_report.v1` |
| `regime_validation_summary.md` | 人读 summary |
| `run_manifest.json` | `regime_validation_run_manifest.v1`（详见 §7） |

### 6.2 处置规则

| 项 | 状态 |
|---|---|
| **不进 main** | ✅；本地 untracked |
| **不覆盖旧结果** | ✅；timestamp 后缀；同名目录 → abort |
| **不写 DB** | ✅ |
| **可删除 / 可重跑** | ✅ |
| **不覆盖 W4 outputs** | ✅；只读 W4 |

---

## 7. run_manifest schema

```json
{
  "schema_version": "regime_validation_run_manifest.v1",
  "candidate_name": "continuous_smoothing_v1",
  "candidate_threshold": 0.60,
  "fold_count": 4,
  "windows": {
    "W1": {"start": "2023-01-03", "end": "2023-08-31"},
    "W2": {"start": "2023-09-01", "end": "2024-02-29"},
    "W3": {"start": "2024-03-01", "end": "2024-08-02"},
    "W4": {"start": "2024-08-03", "end": "2025-12-31"}
  },
  "w4_manifest_status": "ok | error",
  "final_test_cutoff": "2026-01-01",
  "final_test_touched": false,
  "records_loaded": null,
  "records_adapted": null,
  "report_status": "planned | pass | fail | error",
  "warnings": []
}
```

### 7.1 5 项不变量

| 字段 | 不变量 |
|---|---|
| `schema_version` | 总是 `"regime_validation_run_manifest.v1"` |
| `final_test_cutoff` | `"2026-01-01"` 硬编码 |
| `final_test_touched` | bool；`true` → run 整体作废 |
| `report_status` | 4 值之一（不允许其他） |
| `fold_count` | `4`（v1） |

---

## 8. final test guard（6 层 hard stop）

| # | 层 | 来源 |
|---|---|---|
| 1 | caller 起点 row filter（`analysis_date >= 2026-01-01` skip） | orchestrator |
| 2 | W4 manifest gate in adapter（8 项检查含 `final_test_touched=false`） | 3R-4.3A adapter |
| 3 | W4 manifest gate in helper（同 8 项检查） | 3R-4.2 helper |
| 4 | `regime_labels.v1.final_test_refusal=true` 自动 propagate | 3R-2 builder |
| 5 | `continuous_smoothing_candidate.v1.final_test_refusal=true` 自动 propagate | 3R-3.1 candidate |
| 6 | `regime_validation_report.v1.final_test_refusal=true` | 3R-4.2 helper |

任一触发：
- `report_status="error"`
- run abort
- `final_test_touched=true`

---

## 9. first acceptance target

**第一次 run 不需要 pass。** 期望可能 fail。Acceptance（6 项）：

| # | 标准 |
|---|---|
| 1 | **pipeline completes**（exit code 0） |
| 2 | **schema-valid report**（`regime_validation_report.v1` 14 字段 + `replay_validation_records.v1` 8 字段 + `run_manifest.json` 12 字段） |
| 3 | **no DB writes**（main DB / market_data.db mtime 不变；无新 backup） |
| 4 | **no 2026**（`final_test_touched=false` 在 manifest + report） |
| 5 | **`worst_window` populated** |
| 6 | **`gate_status` populated** |

R4 fail baseline 仍是 reference（pytest 中 `test_r4_like_fixture_fails_4fold_validation` 始终 pass）。

### 9.1 first run 可能 fail 的合法理由

| 理由 | 是否合法 |
|---|---|
| candidate 在某 window FER > 0.10 | ✅ |
| candidate 在某 fold cross_window_variance > 0.10 | ✅ |
| candidate 在某 fold paired < 20 | ✅ |
| candidate 在某 window survival_preservation < 0.80 | ✅ |
| candidate net_benefit < +0.05 | ✅ |

→ 任何 fail 都不是 caller / orchestrator 的 bug；只是 candidate 在
4-fold 协议下没通过。**不允许**因 first run fail 而调阈值 / 调系数 /
调 protocol。

---

## 10. no-go rules

任意一项触发 → run abort + `report_status="error"`：

| # | no-go 条件 |
|---|---|
| 1 | 缺 W4 manifest（文件不存在 / parse 失败） |
| 2 | W4 manifest `final_test_touched=true` |
| 3 | 任一 row `as_of_date / prediction_for_date >= 2026-01-01` |
| 4 | `candidate_threshold` 缺失（caller 未传） |
| 5 | report 缺必备字段（schema 检查失败） |
| 6 | 输出目录已存在且未传 allow flag |
| 7 | DB 在 run 期间被修改（mtime / size 变化） |
| 8 | helper `overall_status` 缺失 |
| 9 | adapter records 意外为空（既未 final_test_refusal 也无明确原因） |
| 10 | 任一层 import 了 forbidden module |

---

## 11. 与 hard / required 的关系

| 维度 | 行为 |
|---|---|
| **report `overall_status="pass"` 是否自动启 hard** | **❌ 否** |
| **是否自动改 04 / 05 / 07 required** | **❌ 否** |
| **report `overall_status="fail"` 是否自动改主链** | **❌ 否** |
| **是否让 Gate 5 / Gate 6 自动 pass** | **❌ 否** |
| **是否驱动 `_PROTECTION_LAYER_CONNECTED` 翻 True** | **❌ 否** |
| **是否驱动 `hard_exclusion_allowed` / `primary_blocker` 派生** | **❌ 否** |
| **report `overall_status="pass"` 唯一允许的下游** | **进入下一步 design review** |
| **report `overall_status="fail"` 唯一允许的下游** | **回 candidate / threshold design 重新设计**（不调 protocol thresholds） |

---

## 12. 允许下一步

| # | 候选 | 状态 |
|---|---|---|
| 1 | **Step 3R-3.3A dry-run orchestrator implementation** | **✅ 允许**（在本 checkpoint 进入 main 后启动）；新增 `scripts/run_continuous_smoothing_validation.py`（命名待定） |
| 2 | **必须 pure read-only** | ✅ |
| 3 | **必须 mock-based focused tests**（mock candidate / adapter / helper 调用以测 orchestration logic） | ✅ |
| 4 | **不得直接 real W1-W4 run** | ✅；必须先 dry-run 测试 + 3R-3.3B limited-record smoke 后才能 3R-3.3C |
| 5 | **3R-3.3B limited-record smoke 必须在 3R-3.3A 后** | ✅ |
| 6 | candidate / adapter / helper / labels builder 现有行为 | **❌ 不改**（仅 read-only 调用） |
| 7 | hard / required upgrade / Gate 5 / Gate 6 / `_PROTECTION_LAYER_CONNECTED` | **❌ 永远不允许** |

---

## 13. 禁止事项

| # | 禁止 | 理由 |
|---|---|---|
| 1 | **不扫 threshold** | 与 §5 一致 |
| 2 | **不调 seed coefficients** | 3R-3.1 SEED 是模块常量 |
| 3 | **不写 DB** | 全程 read-only |
| 4 | **不覆盖 W4 outputs** | W4 是不可变 baseline |
| 5 | **不 commit validation outputs** | 与 8D.4 §6.3 一致 |
| 6 | **不启 hard / forced / anti_false_exclusion_triggered** | 三重 NO-GO（2G-8 / 8B / 8C） |
| 7 | **不改 04 / 05 / 07 required** | Step 2G 全程边界 |
| 8 | **不触碰 2026** | 6 层 hard stop |
| 9 | **不接 trading**（`longbridge` / `broker` / `paper_trade`） | 永不 |
| 10 | **不直接进入 formula / simulator** | 必须先过 first run + result checkpoint |
| 11 | **不让 `_PROTECTION_LAYER_CONNECTED` 翻 True** | 与 v1 / 3R-0 / 3R-4 一致 |
| 12 | **不让 `hard_gate_status.protection_layer_connected` 自动 pass** | 同上 |
| 13 | **不改 `hard_exclusion_allowed` / `primary_blocker` 派生** | 同上 |
| 14 | **不改 3R-4 protocol thresholds** | 阈值变更必须经 launch review |
| 15 | **不改 3R-2 helper / 3R-3.1 candidate / 3R-4.2 helper / 3R-4.3A adapter 行为** | 仅 read-only 调用 |
| 16 | **不调 yfinance / requests / 任何网络** | caller 仅本地 csv |
| 17 | **不允许 orchestrator override 任何 SEED / gate threshold** | API 不暴露 |
| 18 | **不允许 first run 失败时调 threshold / 系数** | 与 §9.1 一致 |
| 19 | **不允许 caller import `services.prediction_store` / `sqlite3`** | DB 隔离 |
| 20 | **不触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*`** | 历史防护 |

---

## 14. 下一步建议

按推荐优先级：

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **commit 本 checkpoint** | 把 §1-15 validation run caller 设计状态固化到 main | **本轮 / 下一轮** |
| 2 | **Step 3R-3.3A dry-run orchestrator implementation** | 新增 `scripts/run_continuous_smoothing_validation.py`（命名待定）+ mock-based focused tests；纯 read-only；与三层 helper 同等 isolation | **高**（commit 本 checkpoint 后） |
| 3 | **Step 3R-3.3B limited-record smoke** | 用 small fixture（每 window 1-2 row）跑 orchestrator；产物 `.claude/scratch/`；不进 main；验证 schema + final_test_touched=false | 中（3R-3.3A 后） |
| 4 | **Step 3R-3.3C real W1-W4 validation run** | 跑真实 W1/W2/W3/W4；产物本地独立目录；不进 main；R4 fail acceptance 仍 pass | 中（3R-3.3B smoke 通过后） |
| 5 | **Step 3R-3.3 result checkpoint** | 把 first run 摘要 / `report_status` / `fail_reason` / per_window 简表归档 | 中（3R-3.3C 完成后） |
| 6 | **不推荐**直接 Step 3R-5 formula design | 必须先过 3R-3.3C 实测 acceptance | **❌** |
| 7 | **不推荐** Step 3R-6 read-only simulator | 必须先过 3R-5 design | **❌** |
| 8 | **不推荐**让 report `pass` 自动启 hard / Gate 5 / Gate 6 | 与 §11 一致 | **❌** |
| 9 | **不推荐** 升级 04 required | Step 2G 全程边界 | **❌** |
| 10 | **不推荐** 触碰 2026 final test range | 永久封禁 | **❌** |
| 11 | **不推荐** R4 hard implementation | 三重 NO-GO 已锁定 | **❌** |
| 12 | **不推荐**让 `_PROTECTION_LAYER_CONNECTED` 翻 True | 与 v1 / 3R-0 / 3R-4 一致 | **❌** |
| 13 | **不推荐**用 4-fold validation 数据反推 candidate_threshold | 阈值变更必须经 launch review | **❌** |

**关键判断**：
- 顺序 = 本 checkpoint → **3R-3.3A orchestrator 实施**（首个动代码步）
  → 3R-3.3B smoke → 3R-3.3C real run → 3R-3.3 result checkpoint →
  3R-5 formula → 3R-6 simulator → 3R-7 sidecar
- 任何一步 fail → 整 candidate 报废，回到 design 层重新设计

---

## 15. 严守边界

本文是**纯 checkpoint markdown**：

- ❌ 没改任何代码（`services/*` / `ui/*` / `tests/*` / `scripts/*` 全部未触碰）
- ❌ 没改 DB schema
- ❌ 没写 DB
- ❌ 没运行 replay
- ❌ 没运行 validation
- ❌ 没改 `run_predict` / `predict.py` / `scanner.py` /
  `prediction_store.py` / `app.py`
- ❌ 没改 `services/regime_features_builder.py` /
  `services/regime_labels_builder.py` /
  `services/regime_validation_helper.py` /
  `services/continuous_smoothing_candidate.py` /
  `services/replay_validation_record_adapter.py` /
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
- ❌ 没改 Step 3R-4 protocol thresholds（6 metric / 7 gate / 10 no-go）
- ❌ 没改 Step 3R-2 helper / 3R-3.1 candidate / 3R-4.2 helper / 3R-4.3A
  adapter 行为
- ❌ 没改 Step 3R-3.3 design（已 merge 在 commit `8a24295`，本 checkpoint 不动）
- ❌ 没改 Step 2G-8D / 8D.1A / 8D.2 / 8D.3 / 8D.4 文档或代码
- ❌ 没把 W4 / smoke / validation 输出 commit 进 main
- ❌ 没读 W4 jsonl 行（仅引用 manifest schema 字段）
- ❌ 没选 / 优化 / 扫 candidate_threshold（v1 seed = 0.60 是 design 锁定）
- ❌ 没运行 `pytest`（本轮纯文档；测试基线维持 commit `8a24295` 时
  的 2801 / 0 failed / 10 skipped）
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` /
  `avgo_agent.db.backup_*`
- ✅ 只新增 1 份 markdown checkpoint 文档（本文件）
