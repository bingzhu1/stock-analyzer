# Step 3R-3.3 — 4-Fold Validation Run Design

> **设计文档（4-fold validation run design），不实现，不改代码，不写 DB，不运行 validation。**
> 本文档**冻结** Step 3R-3.3 caller / orchestrator 的：三层职责、数据
> 输入、`candidate_threshold` policy（v1 seed 0.60，**不扫**）、输出
> 目录与 `regime_validation_run_manifest.v1` schema、orchestration flow
> 10 步、final-test guard、first acceptance target、no-go rules、与
> R4 fail acceptance / hard / required / 2026 边界、实施顺序、禁止事项。
>
> 本轮**不动任何代码**：不改 `predict.py` / `run_predict` /
> `scanner.py` / `prediction_store.py` / `app.py` / 任何 `ui/*` /
> `services/*`（含 `services/continuous_smoothing_candidate.py` /
> `services/replay_validation_record_adapter.py` /
> `services/regime_validation_helper.py` /
> `services/regime_labels_builder.py`）/ `scripts/*` / 任何 builder /
> DB schema / 任何 test 中的任何一处。
>
> **本文不实现 orchestrator、不跑 validation、不写 DB、不读 W4 jsonl
> 行（仅引用 manifest schema）、不接 trading API**；只在 markdown 层
> 冻结 caller 设计，给后续 Step 3R-3.3A dry-run orchestrator
> implementation / 3R-3.3B limited-record smoke / 3R-3.3C real W1-W4
> validation run 提供边界。

---

## 1. 背景

| 节点 | 状态 | 关键能力 |
|---|---|---|
| **Step 3R-3.1** candidate generator | ✅ 已 merge（`5e498bc` / `d0c1387`） | 单日 `regime_labels.v1` → `continuous_smoothing_candidate.v1` |
| **Step 3R-4.3A** adapter | ✅ 已 merge（`3586c05` / `608e2bf`） | `replay_rows + candidate` → `replay_validation_records.v1` |
| **Step 3R-4.2** validation helper | ✅ 已 merge（`c669c2f` / `5e58fee`） | records → `regime_validation_report.v1`（含 6 metric / 7 gate / worst-window） |
| **Step 3R-2** labels builder | ✅ 已 merge（`e2a681b` / `db7618b`） | DataFrame → `regime_labels.v1` |
| **Step 2G-8D.3 W4 full replay** | ✅ 已跑（main 上 commit `4bdd782`，输出本地 untracked） | `three_system_w4_2024_08_2025_12/`（353 paired，`final_test_touched=false`） |

**candidate / adapter / helper 三层 + W4 数据层全部就绪**，但**还差一
个 caller / orchestrator** 把它们串起来跑出第一份真实
`regime_validation_report.v1`。本文设计这个 caller。

---

## 2. 当前三层职责

| layer | API | responsibility | forbidden |
|---|---|---|---|
| **candidate** | `build_continuous_smoothing_candidate(regime_labels, ...)` | 单日 candidate diagnostics（`risk_score` / `risk_bucket`） | pass/fail；threshold；coefficient 优化；DB；网络；trading |
| **adapter** | `build_replay_validation_records(rows, ..., candidate_threshold, w4_manifest)` | rows → validation records（含 candidate_triggered / survival_case / window 分派） | metrics / gates；调用 evaluator helper；读文件 |
| **helper** | `build_regime_validation_report(records, ..., w4_manifest_path)` | records → `regime_validation_report.v1`（6 metric / 7 gate / worst-window / overall_status） | 跑 replay；调阈值；写 DB；读外部数据 |

→ **三层完全解耦**；orchestrator 是**唯一**有责任把三层串起来 + 产
生输出文件的层。

---

## 3. validation run 目标

| 目标 | 状态 |
|---|---|
| 读取 W1/W2/W3/W4 replay rows | ✅（caller 责任） |
| 为每条 row 生成 `regime_labels.v1` | ✅（调 3R-2 builder；caller 提供 DataFrames） |
| 为每条 row 生成 `continuous_smoothing_candidate.v1` | ✅（调 3R-3.1 generator） |
| 用 adapter 生成 `replay_validation_records.v1` | ✅（调 3R-4.3A adapter） |
| 用 helper 生成 `regime_validation_report.v1` | ✅（调 3R-4.2 helper） |
| 输出 report 到**独立本地目录** | ✅；不进 main |
| 写 `regime_validation_run_manifest.v1` | ✅（详见 §7） |
| **不写 DB** | ✅ |
| **不改 production** | ✅；`predict.py` / `run_predict` / `scanner.py` / `prediction_store.py` / `app.py` / 04/05/07 required / hard / forced 全部不动 |

---

## 4. 数据输入

| 输入 | 来源 |
|---|---|
| **W4 replay jsonl** | `logs/historical_training/three_system_w4_2024_08_2025_12/three_system_replay_results.jsonl`（**本地 untracked**） |
| **W4 manifest** | `logs/historical_training/three_system_w4_2024_08_2025_12/validation_ready_manifest.json`（`w4_replay_manifest.v1`；caller 解析为 dict） |
| **W1 / W2 / W3 source** | **implementation 前需确认**；候选优先级：1) `logs/historical_training/three_system_1005/three_system_replay_results.jsonl`（同 schema）；2) `avgo_agent.db` `prediction_log` + `outcome_log` join；3) 其他历史 `logs/historical_training/` 目录 |
| **market data for `regime_labels`** | 仅本地 csv / `data/*`（**不**调 yfinance）；caller 加载为 DataFrame 传入 `build_regime_labels(...)` |
| **`final_test_cutoff`** | `"2026-01-01"`（与 3R-2 / 3R-3.1 / 3R-4.2 / 3R-4.3A 一致） |

### 4.1 输入约束

| 约束 | 状态 |
|---|---|
| W4 manifest 必须先过 8 项 gate（与 3R-4.2 / 3R-4.3A 一致） | ✅ |
| W1/W2/W3 来源**不**在 final-test 范围（仅 `< 2026-01-01`） | ✅ |
| caller **不**调用 yfinance / requests（仅本地 csv） | ✅ |
| caller **不**重新跑 outcome；outcome 仅来自已完成 replay 行 | ✅ |
| caller **不**改 jsonl 行 | ✅ |
| caller **不**把 W4 outcome 回写 W1/W2/W3 records（anti-lookahead） | ✅ |

---

## 5. candidate_threshold policy

| 项 | 值 |
|---|---|
| **caller 必须显式传入** | ✅（adapter API required；no default） |
| **v1 design seed threshold** | **`0.60`**（仅用于 first validation run；与 3R-3.1 risk_bucket `high` 边界一致） |
| **0.60 是 optimized 吗** | **❌ 否**；这是 design seed |
| **是否允许扫 threshold** | **❌ 否**；本设计**不**扫；任何 sweep 必须单独 design |
| **是否允许用 validation 结果反推 threshold** | **❌ 否**；阈值变更必须经 launch review |
| **后续 sweep 触发方式** | 单独 Step 3R-3.4（design only，纯 markdown 先行） |
| **first run 失败时是否调整 threshold** | **❌ 否**（与 §11 first acceptance target 一致；first run 不需要 pass） |

### 5.1 强约束

| 约束 | 状态 |
|---|---|
| **不扫 threshold** | ✅ |
| **不学 threshold** | ✅ |
| **不调 SEED 系数**（3R-3.1 模块常量） | ✅ |
| **不调 6 metric / 7 gate threshold**（3R-4 protocol） | ✅ |
| **不允许 caller 在调用时 override 任何 SEED / gate threshold** | ✅ |

---

## 6. run output directory

```
logs/regime_validation/continuous_smoothing_v1_4fold_YYYYMMDD_HHMMSS/
```

`YYYYMMDD_HHMMSS` 由 caller 在启动时生成（UTC 或本地均可；caller 决定）。

### 6.1 输出文件

| 文件 | 内容 |
|---|---|
| `replay_validation_records.json` | adapter 输出的完整 `replay_validation_records.v1` |
| `regime_validation_report.json` | helper 输出的完整 `regime_validation_report.v1` |
| `regime_validation_summary.md` | 人读 summary（候选名 / threshold / fold_count / per_window 简表 / overall_status / fail_reason） |
| `run_manifest.json` | `regime_validation_run_manifest.v1`（详见 §7） |

### 6.2 处置规则

| 项 | 状态 |
|---|---|
| 是否进 main | **❌ 否**；本地 untracked；与 8D.4 W4 输出一致 |
| 是否覆盖旧目录 | **❌ 否**；timestamp 后缀确保独立目录；caller 启动时检测同名目录已存在 → abort + warning |
| 是否可删除 | ✅；run 是验证产物 |
| 是否可重跑 | ✅；幂等；新 timestamp = 新目录 |
| 是否写主 DB | **❌ 否** |
| 是否覆盖 W4 outputs | **❌ 否**（只读 W4） |

---

## 7. `regime_validation_run_manifest.v1` schema

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

### 7.1 字段说明

| 字段 | 类型 | 说明 |
|---|---|---|
| `schema_version` | string | 总是 `"regime_validation_run_manifest.v1"` |
| `candidate_name` | string | v1 = `"continuous_smoothing_v1"` |
| `candidate_threshold` | float | caller 提供；与 adapter 一致 |
| `fold_count` | int | 4（v1） |
| `windows` | dict | W1-W4；与 3R-4.2 / 3R-4.3A 默认一致 |
| `w4_manifest_status` | enum | `"ok"` 或 `"error"`；与 W4 manifest gate 结果一致 |
| `final_test_cutoff` | string | `"2026-01-01"` 硬不变量 |
| `final_test_touched` | bool | `true` → run 整体作废 |
| `records_loaded` | int / null | 读取的 replay row 总数；启动时 null，结束填入 |
| `records_adapted` | int / null | adapter 后的 record 数 |
| `report_status` | enum | `"planned"`（启动）/ `"pass"` / `"fail"`（helper overall_status）/ `"error"` |
| `warnings` | list[str] | 累积 |

### 7.2 不变量

| 字段 | 不变量 |
|---|---|
| `schema_version` | 总是 `"regime_validation_run_manifest.v1"` |
| `final_test_cutoff` | `"2026-01-01"` 硬编码 |
| `final_test_touched` | bool；`true` → run 作废 |
| `report_status` | 4 值之一；不允许其他 |
| `fold_count` | `4`（v1） |

---

## 8. orchestration flow

| # | 步骤 | 实施 |
|---|---|---|
| 1 | **Load W4 manifest and validate** | 解析 `validation_ready_manifest.json` 为 dict；adapter 启动时 + helper `_validate_w4_manifest` 双重校验；任一失败 → `report_status="error"`，run abort |
| 2 | **Load replay rows** | 读 W4 jsonl + W1/W2/W3 来源（per §4）；累积成 `replay_rows: list[dict]` |
| 3 | **Enforce `analysis_date < cutoff` per row** | 对每条 row 检查 `as_of_date >= 2026-01-01` → skip + warning + `final_test_touched=true` 标记触发 |
| 4 | **Build `regime_labels` as of `analysis_date`** | 调 `build_regime_labels(avgo_df, peer_dfs, market_dfs, as_of_date=row["as_of_date"])`；caller 准备 DataFrame |
| 5 | **Build `continuous_smoothing_candidate.v1`** | 调 `build_continuous_smoothing_candidate(regime_labels, as_of_date=row["as_of_date"])` |
| 6 | **Attach candidate to row** | `row["candidate"] = candidate_dict`（in-memory copy；不修改 jsonl 文件） |
| 7 | **Call `build_replay_validation_records`** | `candidate_threshold=0.60` + `w4_manifest=manifest`；得到 `replay_validation_records.v1` |
| 8 | **Call `build_regime_validation_report`** | 输入 records；得到 `regime_validation_report.v1`（含 overall_status / gate_status / worst_window） |
| 9 | **Write local report files** | 4 文件落盘（per §6）；timestamp 目录；UTF-8 / json indent |
| 10 | **Do not write DB** | 全程**不**写 DB；caller 永远不导入 `services.prediction_store` 或 `sqlite3` |

### 8.1 in-memory 流转

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

## 9. final test guard

任意一项触发 → run 整体 `report_status="error"` + `final_test_touched=true`：

| # | 检查 | 来源 |
|---|---|---|
| 1 | 任一 row `as_of_date >= 2026-01-01` 或 `prediction_for_date >= 2026-01-01` | caller + adapter G2 |
| 2 | W4 manifest `final_test_touched=true` | W4 manifest gate（adapter + helper 双重） |
| 3 | `regime_labels.v1.final_test_refusal=true` | 3R-2 builder |
| 4 | `continuous_smoothing_candidate.v1.final_test_refusal=true` | 3R-3.1 candidate |
| 5 | `replay_validation_records.v1.final_test_refusal=true` | 3R-4.3A adapter |
| 6 | `regime_validation_report.v1.final_test_refusal=true` | 3R-4.2 helper |

→ **6 层 hard stop**：caller 起点过滤 + 4 层 helper 内置 refusal +
manifest gate。

---

## 10. first acceptance target

**第一次 run 不需要 pass。** 期望可能 fail。Acceptance：

| # | 标准 | 说明 |
|---|---|---|
| 1 | **pipeline completes**（exit code 0） | 所有 10 步顺利结束，不抛异常 |
| 2 | **produces schema-valid report** | `regime_validation_report.v1` 14 字段全 present + `replay_validation_records.v1` 8 字段全 present + `run_manifest.json` 12 字段全 present |
| 3 | **no DB writes** | `avgo_agent.db` mtime 不变；`data/market_data.db` mtime 不变；无新 backup |
| 4 | **no 2026** | `final_test_touched=false` 在 run_manifest + report；warnings 中无 `2026` 触发 |
| 5 | **`worst_window` / `gate_status` populated** | helper 输出含 worst-window 字段 |
| 6 | **R4 fail baseline remains reference** | helper R4-like fixture acceptance test 仍 pass（`pytest -q` 全绿） |

### 10.1 first run 可能 fail 的合法理由

| 理由 | 是否合法 |
|---|---|
| candidate 在某 window FER > 0.10 | ✅ 合法 |
| candidate 在某 fold cross_window_variance > 0.10 | ✅ 合法 |
| candidate 在某 fold paired < 20 | ✅ 合法 |
| candidate 在某 window survival_preservation < 0.80 | ✅ 合法 |
| candidate net_benefit < +0.05 | ✅ 合法 |

→ 任何 fail 都不是 caller / orchestrator 的 bug；只是 candidate 在
4-fold 协议下没通过。**不允许**因 first run fail 而调阈值 / 调系数 /
调 threshold。

---

## 11. relationship to R4 fail acceptance

| 维度 | helper R4-like fixture acceptance | first real run |
|---|---|---|
| candidate | R4-like（合成 fixture） | continuous_smoothing_v1（真实 SEED） |
| 输入数据 | 内置 fixture | 真实 W1-W4 replay rows |
| 期望 | 必须 fail（已锁定） | 允许 fail |
| 锁定测试 | `test_r4_like_fixture_fails_4fold_validation`（commit `c669c2f`） | n/a（runtime artifact） |

### 11.1 强约束

| 约束 | 状态 |
|---|---|
| **continuous_smoothing_v1 fail 不影响 R4 fixture acceptance** | ✅；二者独立 |
| **continuous_smoothing_v1 pass 仅意味着 eligible for design review** | ✅；不是 production permission |
| **R4 fail remains sanity check**（每次 pytest 跑都验证） | ✅ |
| **不允许用 first run 结果调 SEED / threshold / metric** | ✅ |

---

## 12. no-go rules

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

## 13. 与 hard / required 的关系

| 维度 | first run 行为 |
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

## 14. 实施顺序建议

| # | 子步骤 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **commit 本 design** | 把 §1-16 4-fold validation run caller 设计固化到 main | **本轮 / 下一轮** |
| 2 | **Step 3R-3.3 checkpoint** | 状态归档 | **下一轮**（commit 本 design 后） |
| 3 | **Step 3R-3.3A dry-run orchestrator implementation** | 新增 `scripts/run_continuous_smoothing_validation.py`（命名待定）+ orchestrator 不接 yfinance / DB；focused tests for orchestration logic（mock candidate / adapter / helper）；pure read-only | 中（在 3R-3.3 checkpoint 进 main 后） |
| 4 | **Step 3R-3.3B limited-record smoke** | 用 small fixture（例：每 window 1-2 row）跑 orchestrator；产物 `.claude/scratch/`；不进 main；验证 schema + final_test_touched=false | 中（3R-3.3A 完成后） |
| 5 | **Step 3R-3.3C real W1-W4 validation run** | 跑真实 W1/W2/W3/W4 replay rows；产物本地独立目录；不进 main；R4 fail acceptance 仍 pass | 中（3R-3.3B smoke 通过后） |
| 6 | **Step 3R-3.3 result checkpoint** | 把 first run 的 `regime_validation_report.v1` 摘要 + report_status / fail_reason / per_window 简表归档 | 中（3R-3.3C 完成后） |

---

## 15. 禁止事项

| # | 禁止 | 理由 |
|---|---|---|
| 1 | **不扫 threshold** | 与 §5 一致；任何 sweep 必须单独 design |
| 2 | **不调 seed coefficients** | 3R-3.1 SEED 是模块常量；调动必须经 launch review |
| 3 | **不写 DB** | 全程 read-only |
| 4 | **不覆盖 W4 outputs** | W4 是不可变 baseline |
| 5 | **不 commit validation outputs** | 与 8D.4 §6.3 一致；本地 untracked |
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
| 18 | **不允许 first run 失败时调 threshold / 系数** | 与 §10.1 一致 |
| 19 | **不允许 caller import `services.prediction_store` / `sqlite3`** | DB 隔离 |
| 20 | **不触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*`** | 历史防护 |

---

## 16. 严守边界

本文是**纯 design markdown**：

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
- ❌ 没改 Step 3R-3.3 系列 design / checkpoint（即将新增）
- ❌ 没改 Step 2G-8D / 8D.1A / 8D.2 / 8D.3 / 8D.4 文档或代码
- ❌ 没把 W4 / smoke / validation 输出 commit 进 main
- ❌ 没读 W4 jsonl 行（仅引用 manifest schema 字段）
- ❌ 没选 / 优化 candidate_threshold（v1 seed = 0.60 是 design 锁定）
- ❌ 没扫 threshold
- ❌ 没运行 `pytest`（本轮纯文档；测试基线维持 commit `608e2bf` 时
  的 2801 / 0 failed / 10 skipped）
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` /
  `avgo_agent.db.backup_*`
- ✅ 只新增 1 份 markdown design 文档（本文件）
