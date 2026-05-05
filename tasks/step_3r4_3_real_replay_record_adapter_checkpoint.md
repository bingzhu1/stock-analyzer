# Step 3R-4.3 — Real Replay Record Adapter Checkpoint

> **状态固化文档（real replay record adapter checkpoint），不实现，不改代码，不写 DB，不运行 replay / validation。**
> 本文档**冻结** Step 3R-4.3 design（commit `9da5e57`）的：adapter
> 目标、`replay_validation_records.v1` 输出 schema、W4 jsonl 47 字段
> mapping、candidate_threshold caller 必填、`candidate_triggered` /
> `exclusion_would_block` / `survival_case` 公式、window assignment、
> adapter / helper / candidate 三层解耦关系、当前限制、允许下一步、
> 禁止事项。
>
> 本轮**不动任何代码**：不改 `predict.py` / `run_predict` /
> `scanner.py` / `prediction_store.py` / `app.py` / 任何 `ui/*` /
> `services/*`（含 `services/regime_validation_helper.py` /
> `services/continuous_smoothing_candidate.py` /
> `services/regime_labels_builder.py`）/ `scripts/*` / 任何 builder /
> DB schema / 任何 test 中的任何一处。
>
> **本文不实现 adapter、不跑 replay / validation、不写 DB、不读 W4
> jsonl 行（仅引用 design 字段表）、不接 trading API**；只在 markdown
> 层固化 adapter 设计状态，作为后续 Step 3R-4.3A adapter implementation /
> Step 3R-3.3 4-fold validation run 的强制 gate。

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
- **Step 3R-4.3** real replay record adapter design 已完成并进入 main
  （commit `9da5e57`）
- 本 checkpoint **固定**：
  - adapter 目标 + 10 项 read-only 责任
  - `replay_validation_records.v1` 8 字段 schema + 8 项不允许字段
  - validation record 12 字段 schema
  - W4 jsonl 47 字段实测 mapping（含 unit 注意事项）
  - `candidate_triggered = (risk_score >= candidate_threshold)` + threshold caller 必填
  - `exclusion_would_block` / `survival_case` / `baseline_correct` (v1) 公式
  - window assignment 4 段 + 2026 forbidden
  - adapter / helper / candidate 三层解耦
  - 当前限制 + 允许下一步 + 23 项禁止
- **Step 3R-4.3A adapter implementation 仍未启动**：本 checkpoint 是
  3R-4.3A 之前的强制 gate

---

## 2. 当前 main 状态

- main 最新 commit：**`9da5e57`**
- commit message：`docs(contract): Step 3R-4.3 real replay record adapter design`
- 上游：`origin/main` 已同步
- 测试基线：**2753 passed / 0 failed / 10 skipped / 26 warnings /
  94 subtests**（与 commit `5e498bc` 一致；本 checkpoint 阶段无代码
  改动 → 基线不变）

本步骤新增文件（已 merge 到 main）：

| 路径 | 类型 | 说明 |
|---|---|---|
| `tasks/step_3r4_3_real_replay_record_adapter_design.md` | 新增 | 17 节、445 行；adapter 目标 + W4 jsonl mapping + `replay_validation_records.v1` schema + 三层解耦 |

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

## 3. Adapter 目标

| 责任 | 是否 |
|---|---|
| **读取 replay rows**（W4 jsonl + W1/W2/W3 来源） | ✅ |
| **提取 analysis_date / prediction_for_date / correctness** | ✅ |
| **组装 validation records**（喂 3R-4.2 helper） | ✅ |
| **算 metrics** | ❌ 否（helper 责任） |
| **输出 pass/fail** | ❌ 否（helper 责任） |
| **调 threshold** | ❌ 否（caller 必填） |
| **写 DB** | ❌ 否 |
| **改 helper / candidate** | ❌ 否（仅 read-only 调用其 API） |
| **接 yfinance / requests / trading** | ❌ 否 |
| **触碰 2026** | ❌ 否（manifest gate + record-level cutoff 双重 hard stop） |

---

## 4. `replay_validation_records.v1` schema

```json
{
  "schema_version": "replay_validation_records.v1",
  "candidate_name": "continuous_smoothing_v1",
  "candidate_threshold": null,
  "records": [
    {"...": "see §5"}
  ],
  "windows": {
    "W1": {"start": "2023-01-03", "end": "2023-08-31"},
    "W2": {"start": "2023-09-01", "end": "2024-02-29"},
    "W3": {"start": "2024-03-01", "end": "2024-08-02"},
    "W4": {"start": "2024-08-03", "end": "2025-12-31"}
  },
  "source_files": [
    "logs/historical_training/three_system_1005/three_system_replay_results.jsonl",
    "logs/historical_training/three_system_w4_2024_08_2025_12/three_system_replay_results.jsonl"
  ],
  "final_test_refusal": false,
  "warnings": []
}
```

### 4.1 schema 不变量

| 字段 | 不变量 |
|---|---|
| `schema_version` | 总是 `"replay_validation_records.v1"` |
| `candidate_name` | string；v1 = `"continuous_smoothing_v1"` |
| `candidate_threshold` | float \| null；caller 提供（**no default in adapter API**） |
| `records` | list；每条符合 §5 schema |
| `windows` | dict；与 3R-4.2 / 3R-4.1 默认一致 |
| `source_files` | list of relative paths |
| `final_test_refusal` | bool；任一 row `>= 2026-01-01` → `true` + adapter abort |
| `warnings` | list of string |

### 4.2 不允许字段

| 禁止字段 | 理由 |
|---|---|
| `gate_status` | adapter 是数据层；validation 由 3R-4.2 helper 输出 |
| `validation_passed` | 同上 |
| `overall_status` | 同上 |
| `hard_*` | adapter 永不直接驱动 hard 路径 |
| `simulated_trade` | 与 v1 / 3R-0 / 3R-4 一致 |
| `no_trade` | 同上 |
| `final_direction` | 同上 |
| `final_projection` | 同上 |

---

## 5. validation record schema

```json
{
  "analysis_date": "YYYY-MM-DD",
  "prediction_for_date": "YYYY-MM-DD",
  "candidate_triggered": true,
  "prediction_correct": true,
  "baseline_correct": true,
  "exclusion_would_block": true,
  "survival_case": false,
  "actual_direction": "up | down | flat | unknown",
  "labels": {"...": "regime_labels.v1.labels subset, optional"},
  "candidate": {"...": "continuous_smoothing_candidate.v1 fields, optional"},
  "window": "W1 | W2 | W3 | W4",
  "warnings": []
}
```

### 5.1 字段不变量

| 字段 | 不变量 |
|---|---|
| `analysis_date` | ISO；`< final_test_cutoff` 硬不变量 |
| `prediction_for_date` | ISO；`< final_test_cutoff` 硬不变量 |
| `candidate_triggered` | bool |
| `prediction_correct` | bool；`null` → adapter skip + warning |
| `baseline_correct` | bool；`null` → adapter skip |
| `exclusion_would_block` | bool |
| `survival_case` | bool |
| `actual_direction` | enum 4 值 |
| `labels` | optional |
| `candidate` | optional |
| `window` | enum：W1/W2/W3/W4 |
| `warnings` | list of string |

---

## 6. W4 jsonl mapping

实测（commit `5e498bc` 时 `three_system_replay_results.jsonl` 第一行
顶层 47 字段）：

| jsonl 字段 | record 字段 / 用途 |
|---|---|
| `as_of_date` | **`analysis_date`** |
| `prediction_for_date` | **`prediction_for_date`** |
| `direction_correct` (bool) | **`prediction_correct`** |
| `direction_correct` (bool) | **`baseline_correct`**（v1 设同 `prediction_correct`，详见 §8） |
| `actual_state` / `actual_close_change` / `actual_*_label` | diagnostics（不喂 helper gate） |
| `final_direction` / `error_layer` / `error_category` | diagnostics only |
| `ready` / `warnings`（jsonl 行级） | adapter `ready=False` → skip + warning |
| `negative_excluded` / `negative_*` | diagnostics only |
| **`pos20` (percentage 单位，例 27.9 = 27.9%)** | **不直接用** |

### 6.1 强调

| 警告 | 状态 |
|---|---|
| **W4 jsonl `pos20` 单位与 3R-2 `regime_labels.v1.raw_features.pos20`（decimal `[0, 1]`）不同** | ✅ 已记录 |
| **adapter 不应直接用 jsonl 的 pos20 / nvda_ret1 / soxx_ret1 / qqq_ret1** | ✅；这些是 instant value，不是 builder 输入；adapter 应调 `build_regime_labels(as_of_date=...)` 重算 |
| **需要 builder / normalized labels source** | ✅；adapter API 应允许 `labels_source` callable 或预算 snapshot |
| **W1/W2/W3 jsonl 是否同 schema** | adapter implementation must inspect（3R-4.3A 阶段）|
| **`baseline_correct` / `survival_case` / `exclusion_would_block` 字段不存在 jsonl 中** | ✅；adapter 必须 derive |

---

## 7. `candidate_triggered`

| 项 | 值 |
|---|---|
| 公式 | **`candidate_triggered = (risk_score >= candidate_threshold)`** |
| `risk_score` 来源 | `services.continuous_smoothing_candidate.build_continuous_smoothing_candidate(labels).risk_score` |
| `candidate_threshold` | **caller 必填**，no default |
| `risk_score is None`（refusal / 缺字段） | `candidate_triggered = False` + warning `candidate_unavailable` |

### 7.1 强约束

| 强约束 | 状态 |
|---|---|
| **adapter 不选择 threshold** | ✅ |
| **adapter 不优化 threshold** | ✅ |
| **不允许 adapter 自动学 / 反推 threshold** | ✅；adapter API 必须 required threshold（no default） |
| **risk_score None → candidate_triggered=false + warning** | ✅ |
| **不允许 adapter override SEED 系数** | ✅；3R-3.1 SEED 是模块常量 |

---

## 8. `exclusion_would_block` / `survival_case`

| 字段 | 公式（v1） |
|---|---|
| `exclusion_would_block` | `candidate_triggered`（即 v1 candidate 触发即 block） |
| `survival_case` | `candidate_triggered ∧ prediction_correct` |
| `baseline_correct` | `direction_correct`（v1：与 prediction_correct 同源；candidate 是 sidecar 不重新预测） |
| `prediction_correct` | replay row `direction_correct` |
| **adapter 改 correctness** | ❌ 否 |

未来 candidate 升级为"重新预测"（formula 阶段）时 baseline_correct 才
会和 prediction_correct 语义分化。

---

## 9. window assignment

| 规则 | 实施 |
|---|---|
| `analysis_date` 决定 W1/W2/W3/W4 | adapter 用 `regime_validation_helper.DEFAULT_WINDOWS` |
| `analysis_date >= 2026-01-01` → 整 adapter abort + `final_test_refusal=true` | ✅ |
| 落不进任何 window → skip + warning `record_skipped:out_of_window:<date>` | ✅ |
| W4 records 必须先过 manifest gate | ✅ 复用 3R-4.2 §5 |
| W1/W2/W3 不需要 manifest（来源是 main 上的 replay） | ✅ |

### 9.1 window 边界

| window | 起止 |
|---|---|
| W1 | **2023-01-03 → 2023-08-31** |
| W2 | **2023-09-01 → 2024-02-29** |
| W3 | **2024-03-01 → 2024-08-02** |
| W4 | **2024-08-03 → 2025-12-31** |
| final test | **2026-01-01 → ∞ — forbidden** |

---

## 10. 与 helper / candidate 的关系

三层解耦：

| 层 | 模块 | 输入 | 输出 |
|---|---|---|---|
| **candidate**（数据层 / 单日） | `services.continuous_smoothing_candidate.build_continuous_smoothing_candidate` | `regime_labels.v1` dict | `continuous_smoothing_candidate.v1` |
| **adapter**（数据组装层 / 多日） | future `services.replay_validation_record_adapter`（命名待定） | replay jsonl + labels + candidate | `replay_validation_records.v1` |
| **helper**（评分层） | `services.regime_validation_helper.build_regime_validation_report` | record list | `regime_validation_report.v1` |

### 10.1 强约束

| 强约束 | 状态 |
|---|---|
| **adapter 不知道 6 metrics / 7 gates** | ✅；不调 helper gate；不输出 gate_status |
| **helper 不知道 jsonl / candidate internals** | ✅；接受任何符合 record schema 的 list |
| **candidate 不知道 records / windows** | ✅；输入是单日 labels，输出是单日 risk_score |
| **三层调用顺序固定**：candidate → adapter → helper | ✅ |
| **不允许跨层 wiring**（例：helper 不直接调 candidate；candidate 不输出 records） | ✅ |

---

## 11. 当前限制

| # | 限制 | 解封步骤 |
|---|---|---|
| 1 | **还没有实现 adapter** | Step 3R-4.3A |
| 2 | **W1/W2/W3 来源仍需 implementation inspection** | 3R-4.3A 阶段；候选 = 1005 jsonl 或 main DB join |
| 3 | **`candidate_threshold` 未定** | Step 3R-3.3 实测后由 launch review 决定（不允许用 4-fold 数据反推） |
| 4 | **`labels_source` 未定** | 3R-4.3A 阶段决定 callable / snapshot |
| 5 | **还没有跑 4-fold validation** | Step 3R-3.3（after 3R-4.3A 完成） |
| 6 | **还没有生成真实 `regime_validation_report.v1`** | Step 3R-3.3 |
| 7 | **adapter runtime 估 ~ 15-30 分钟**（W1-W4 合计 ~ 639 行 × 单日 builder ~ 1-3s） | 3R-4.3A 可加 caching；本设计不实施 |
| 8 | **没有 dashboard / UI** | Step 3R-7（可选） |

---

## 12. 允许下一步

| # | 候选 | 状态 |
|---|---|---|
| 1 | **Step 3R-4.3A adapter implementation** | **✅ 允许**（在本 checkpoint 进入 main 后启动）；新增 `services/replay_validation_record_adapter.py`（命名待定）+ tests |
| 2 | **adapter 必须保持 read-only** | ✅；与 3R-2 helper / 3R-3.1 candidate / 3R-4.2 helper 同等 isolation |
| 3 | **必须先支持 W4 jsonl fixture** | ✅；W4 schema 已实测；可优先 W4 fixture 测试 |
| 4 | **W1/W2/W3 来源可在 implementation 中继续 inspect** | ✅；预期 1005 jsonl 同 schema，但需实测 |
| 5 | **Step 3R-3.3 4-fold validation run** | **必须等 3R-4.3A 完成**；adapter → helper → `regime_validation_report.v1` |
| 6 | Step 3R-5 formula design / Step 3R-6 read-only simulator | **❌ 仍不允许**（必须先过 3R-3.3 实测 acceptance） |
| 7 | adapter pass 自动启 hard / Gate 5 / Gate 6 | **❌ 永远不允许** |

---

## 13. 禁止事项

| # | 禁止 | 理由 |
|---|---|---|
| 1 | **不写 DB** | adapter 是 read-only artifact |
| 2 | **不改 replay output** | adapter 只读 jsonl |
| 3 | **不改 candidate coefficients**（SEED） | 与 3R-3.1 §5 一致 |
| 4 | **不选择 candidate_threshold** | caller 提供；调动必须经 launch review |
| 5 | **不跑 validation** | helper 由 3R-3.3 调 |
| 6 | **不宣称 pass/fail** | 输出**无** `gate_status` / `overall_status` |
| 7 | **不启 hard / forced / anti_false_exclusion_triggered** | 三重 NO-GO（2G-8 / 8B / 8C） |
| 8 | **不改 04 / 05 / 07 required** | Step 2G 全程边界 |
| 9 | **不触碰 2026** | manifest gate + record-level cutoff 双重 hard stop |
| 10 | **不把 W4 output commit 进 main** | 与 8D.4 §6.3 一致 |
| 11 | **不接 trading**（`longbridge` / `broker` / `paper_trade`） | 永不 |
| 12 | **不接 yfinance / 网络** | adapter 只读 jsonl / 调用 caller-injected DataFrames |
| 13 | **不让 `_PROTECTION_LAYER_CONNECTED` 翻 True** | 与 v1 / 3R-0 / 3R-4 一致 |
| 14 | **不让 `hard_gate_status.protection_layer_connected` 自动 pass** | 同上 |
| 15 | **不改 `hard_exclusion_allowed` / `primary_blocker` 派生** | 同上 |
| 16 | **不改 3R-4 protocol thresholds** | 阈值变更必须经 launch review |
| 17 | **不改 3R-2 helper / 3R-3.1 candidate / 3R-4.2 helper 行为** | 仅 read-only 调用 |
| 18 | **不允许 adapter 自动学 / 选 threshold** | adapter API 必须 required threshold（no default） |
| 19 | **不允许 adapter 把 W4 outcome 回写 W1/W2/W3 records** | anti-lookahead |
| 20 | **不允许 adapter 重跑 yfinance / outcome_capture** | outcome 来源仅是已完成 replay |
| 21 | **不允许 adapter 改 jsonl 字段** | read-only |
| 22 | **不允许 `replay_validation_records.v1` 包含 `gate_status` / `validation_passed` / `overall_status` / `hard_*` / `simulated_trade` / `no_trade` / `final_direction` / `final_projection`** | 与 §4.2 一致 |
| 23 | **不触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*`** | 历史防护 |

---

## 14. 下一步建议

按推荐优先级：

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **commit 本 checkpoint** | 把 §1-15 adapter 设计状态固化到 main | **本轮 / 下一轮** |
| 2 | **Step 3R-4.3A adapter implementation** | 新增 `services/replay_validation_record_adapter.py`（命名待定）+ focused tests；纯 read-only；先支持 W4 jsonl fixture；W1-W3 来源 inspection | **高**（commit 本 checkpoint 后） |
| 3 | **Step 3R-3.3 4-fold validation run** | adapter → helper → `regime_validation_report.v1`；R4 fail acceptance 复检；threshold 由 caller 显式提供 | 中（3R-4.3A 完成后） |
| 4 | **Step 3R-3.3 checkpoint** | 把实测结果归档 | 中（3R-3.3 完成后） |
| 5 | **不推荐**直接 Step 3R-5 formula design | 必须先过 3R-3.3 实测 acceptance | **❌** |
| 6 | **不推荐** Step 3R-6 read-only simulator | 必须先过 3R-5 design | **❌** |
| 7 | **不推荐**让 adapter `pass` 自动启 hard / Gate 5 / Gate 6 | 与 §10 一致 | **❌** |
| 8 | **不推荐** 升级 04 required | Step 2G 全程边界 | **❌** |
| 9 | **不推荐** 触碰 2026 final test range | 永久封禁 | **❌** |
| 10 | **不推荐** R4 hard implementation | 三重 NO-GO 已锁定 | **❌** |
| 11 | **不推荐**让 `_PROTECTION_LAYER_CONNECTED` 翻 True | 与 v1 / 3R-0 / 3R-4 一致 | **❌** |
| 12 | **不推荐**用 W4 / 4-fold 数据反推 candidate_threshold | 阈值变更必须经 launch review | **❌** |

**关键判断**：
- 顺序 = 本 checkpoint → **3R-4.3A adapter 实施**（首个动代码步）→
  3R-3.3 validation run → 3R-3.3 checkpoint → 3R-5 formula → 3R-6
  simulator → 3R-7 sidecar
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
- ❌ 没改 Step 3R-2 helper 行为
- ❌ 没改 Step 3R-3.1 candidate 行为 / SEED 系数
- ❌ 没改 Step 3R-4.2 helper 行为 / W4 manifest gate
- ❌ 没改 Step 3R-4.3 design（已 merge 在 commit `9da5e57`，本 checkpoint 不动）
- ❌ 没改 Step 2G-8D / 8D.1A / 8D.2 / 8D.3 / 8D.4 文档或代码
- ❌ 没把 W4 / smoke 输出 commit 进 main
- ❌ 没读 W4 jsonl 行（仅引用 design 字段表）
- ❌ 没选 `candidate_threshold` / 任何系数 / 任何阈值
- ❌ 没运行 `pytest`（本轮纯文档；测试基线维持 commit `9da5e57` 时
  的 2753 / 0 failed / 10 skipped）
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` /
  `avgo_agent.db.backup_*`
- ✅ 只新增 1 份 markdown checkpoint 文档（本文件）
