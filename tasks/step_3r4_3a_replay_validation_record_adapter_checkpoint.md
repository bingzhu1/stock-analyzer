# Step 3R-4.3A — Replay Validation Record Adapter Checkpoint

> **状态固化文档（replay validation record adapter checkpoint），不实现，不改代码，不写 DB，不运行 replay / validation。**
> 本文档**冻结** Step 3R-4.3A adapter（commit `3586c05`）的：公共 API、
> `replay_validation_records.v1` schema、W4 manifest gate（8 项）、
> candidate_threshold required + 7 项验证、record mapping、window
> assignment、no-validation-claims 双层锁定、48 focused tests + 2801
> 全量 pytest 基线、与 Step 3R-2 helper / Step 3R-3.1 candidate /
> Step 3R-4.2 helper / 2026 final test range 边界。
>
> 本轮**不动任何代码**：不改 `predict.py` / `run_predict` /
> `scanner.py` / `prediction_store.py` / `app.py` / 任何 `ui/*` /
> `services/*`（含 `services/replay_validation_record_adapter.py` /
> `services/regime_validation_helper.py` /
> `services/continuous_smoothing_candidate.py` /
> `services/regime_labels_builder.py`）/ `scripts/*` / 任何 builder /
> DB schema / 任何 test 中的任何一处。
>
> **本文不实施 4-fold validation run、不跑 replay、不写 DB、不接
> trading API**；只在 markdown 层固化 adapter 状态，作为后续 Step
> 3R-3.3 4-fold validation run 的强制 gate。

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
- **Step 3R-4.3A** replay validation record adapter implementation
  已完成并进入 main（commit `3586c05`）—— Step 3R 系列**adapter 层
  第一个动代码步**
- 本 checkpoint **固定**：
  - `build_replay_validation_records(...)` 公共 API + 6 参数 + 8 项
    read-only 约束
  - `replay_validation_records.v1` 8 字段 schema + 8 项不允许字段
  - W4 manifest gate（8 项）+ 失败行为
  - candidate_threshold required + 7 项验证 + 边界（0.0/1.0）
  - record mapping（W4 jsonl → record）
  - window assignment 4 段 + 2026 forbidden
  - no-validation-claims 双层锁定（顶层 + record 内）
  - 48 focused tests + 2801 全量 pytest 基线
  - 与 Step 3R-2 / Step 3R-3.1 / Step 3R-4.2 helper / 2026 边界
- **Step 3R-3.3 4-fold validation run 仍未启动**：本 checkpoint 是
  3R-3.3 之前的强制 gate

---

## 2. 当前 main 状态

- main 最新 commit：**`3586c05`**
- commit message：`feat(diagnostics): add replay validation record adapter`
- 上游：`origin/main` 已同步
- 测试基线：**2801 passed / 0 failed / 10 skipped / 26 warnings /
  94 subtests**（Step 3R-3.1 终点 2753 → Step 3R-4.3A 终点 2801，
  +48 净增；2753 基线零回归）

本步骤新增 / 修改文件（已 merge 到 main）：

| 路径 | 类型 | 说明 |
|---|---|---|
| `services/replay_validation_record_adapter.py` | 新增 | pure read-only adapter（353 行）；W4 manifest gate + row → record mapping + 2026 cutoff + window assignment |
| `tests/test_replay_validation_record_adapter.py` | 新增 | 48 focused tests |
| `tasks/step_1_contract_pipeline_summary.md` | 修改 | 新增 §40 |

本 checkpoint 文档（即本文件）尚未 commit；本轮只写文档、**不**
commit / push。

| 项 | 是否触碰 |
|---|---|
| 改代码 | ❌ 否 |
| 写 DB | ❌ 否 |
| 跑 replay | ❌ 否 |
| 跑 validation | ❌ 否 |
| 改 services/replay_validation_record_adapter.py（已 merge 在 commit `3586c05`） | ❌ 否 |
| 改 services/regime_labels_builder.py / regime_validation_helper.py / continuous_smoothing_candidate.py | ❌ 否 |
| 改 DB schema | ❌ 否 |
| 接 yfinance / 网络 | ❌ 否 |
| 接 trading API | ❌ 否 |
| 触碰 2026 final test | ❌ 否 |

---

## 3. Public API

```python
build_replay_validation_records(
    replay_rows,
    *,
    candidate_threshold,         # REQUIRED, no default
    candidate_name="continuous_smoothing_v1",
    final_test_cutoff="2026-01-01",
    require_w4_manifest=True,
    w4_manifest=None,
) -> dict
```

| 项 | 值 |
|---|---|
| 类型 | **pure read-only adapter** |
| 是否读 DB | ❌ 否 |
| 是否写 DB | ❌ 否 |
| 是否读文件 | ❌ 否（manifest 必须 caller 注入 dict；adapter 无 `open(...)` / 无 `json` / `os` / `pathlib` import） |
| 是否跑 replay / validation | ❌ 否 |
| 是否调用 `build_regime_validation_report` 或评分层 helper | ❌ 否（`ast.walk` 锁定 22 项 forbidden module，含 `services.regime_validation_helper`） |
| 是否接 yfinance / requests / trading | ❌ 否（`ast.walk` 锁定） |
| 是否暴露 threshold default | ❌ 否（caller 必填） |
| 是否触碰 2026 | ❌ 否（manifest gate + record-level cutoff 双重 hard stop） |
| 是否宣称 validation pass / fail | ❌ 否 |

### 3.1 6 参数

| 参数 | 默认 | 说明 |
|---|---|---|
| `replay_rows` | required | list of dict（W4 jsonl shape） |
| `candidate_threshold` | **required (no default)** | float ∈ [0, 1] |
| `candidate_name` | `"continuous_smoothing_v1"` | string |
| `final_test_cutoff` | `"2026-01-01"` | hard cutoff |
| `require_w4_manifest` | True | 是否强制 W4 gate |
| `w4_manifest` | None | caller 注入 dict |

---

## 4. `replay_validation_records.v1` schema

```json
{
  "schema_version": "replay_validation_records.v1",
  "candidate_name": "continuous_smoothing_v1",
  "candidate_threshold": 0.6,
  "records": [
    {"...": "see record schema"}
  ],
  "windows": {
    "W1": {"start": "2023-01-03", "end": "2023-08-31"},
    "W2": {"start": "2023-09-01", "end": "2024-02-29"},
    "W3": {"start": "2024-03-01", "end": "2024-08-02"},
    "W4": {"start": "2024-08-03", "end": "2025-12-31"}
  },
  "source_files": [],
  "final_test_refusal": false,
  "warnings": []
}
```

### 4.1 不允许字段（顶层 + record 内双层锁定）

| 禁止字段 | 锁定测试 |
|---|---|
| `gate_status` | `NoForbiddenOutputTests::test_no_forbidden_top_level_keys` + `test_no_forbidden_record_keys` |
| `validation_passed` | 同上 |
| `overall_status` | 同上 |
| `hard_*`（`hard_exclusion_allowed` / `hard_gate_status`） | 同上 |
| `simulated_trade` | 同上 |
| `no_trade` | 同上 |
| `final_direction` | 同上 |
| `final_projection` | 同上 |
| 字符串 `build_regime_validation_report` / `regime_validation_report.v1` | `IsolationTests::test_does_not_call_validation_helper` |
| 模块文件提到 `hard_exclusion_allowed` / `forced_exclusion` / `_PROTECTION_LAYER_CONNECTED` 等 | `test_does_not_reference_hard_or_required_fields` |

---

## 5. W4 manifest gate

启动前**必须**通过 8 项检查（manifest 由 caller 注入 dict，**adapter
不读文件**）：

| # | 检查 | 期望 |
|---|---|---|
| 1 | manifest 必须为 dict（非 None） | `dict` |
| 2 | `schema_version` | `"w4_replay_manifest.v1"` |
| 3 | **`final_test_touched`** | **`False`** |
| 4 | `status` | `"ok"` |
| 5 | `paired_outcomes` | `int >= 20` |
| 6 | `replay_window.start` | `"2024-08-03"` |
| 7 | `replay_window.end` | `"2025-12-31"` |
| 8 | `final_test_cutoff` | `"2026-01-01"` |

### 5.1 失败行为

| 字段 | 值 |
|---|---|
| `records` | **`[]`**（空列表） |
| `warnings` | 含具体失败原因（例 `w4_paired_below_minimum`） |
| `final_test_refusal` | **镜像 `manifest.final_test_touched`**（仅当 `True` 时整份报告作废） |
| adapter 是否进入 row 处理 | **❌ 否**（gate fail → 直接返回 empty payload） |

`require_w4_manifest=False` → 跳过 gate + emit `w4_manifest_not_required`
informational warning。

---

## 6. candidate_threshold

| 行为 | 状态 |
|---|---|
| **caller 必填**，no default | ✅ |
| `None` → `ValueError` | ✅ |
| `bool` → `ValueError`（防 `True` / `False` 被当 1/0） | ✅ |
| `str` → `ValueError`（防 `"0.5"` 被 `float()` 接受） | ✅ |
| 非 int/float → `ValueError` | ✅ |
| `NaN` → `ValueError` | ✅ |
| `< 0.0` → `ValueError` | ✅ |
| `> 1.0` → `ValueError` | ✅ |
| `0.0` / `1.0` 边界 accepted | ✅ |
| **adapter 不优化 threshold** | ✅ |
| **adapter 不学习 threshold** | ✅；不允许通过 W4 / 4-fold validation 数据反推 |

---

## 7. record mapping

每条 record（喂给 3R-4.2 helper）字段：

| record 字段 | 来源 |
|---|---|
| `analysis_date` | `row["as_of_date"]` |
| `prediction_for_date` | `row["prediction_for_date"]` |
| `prediction_correct` | `row["direction_correct"]` |
| `baseline_correct` | `row["direction_correct"]`（v1 同 prediction_correct） |
| `candidate_triggered` | `row["candidate"]["risk_score"] >= candidate_threshold` |
| `exclusion_would_block` | `candidate_triggered` |
| `survival_case` | `candidate_triggered ∧ prediction_correct` |
| `actual_direction` | `row["actual_state"]` 优先（"大涨"/"小涨"→"up"，"大跌"/"小跌"→"down"，"震荡"→"flat"），否则 `row["actual_close_change"]` 派生 |
| `labels` | `row["labels"]`（optional；深拷贝） |
| `candidate` | `row["candidate"]`（深拷贝） |
| `window` | adapter 按 §8 分派 |
| `warnings` | record-level；含 `missing_candidate` / `candidate_unavailable` / `candidate_final_test_refusal` 等 |

---

## 8. window assignment

| window | 起止 |
|---|---|
| **W1** | **2023-01-03 → 2023-08-31** |
| **W2** | **2023-09-01 → 2024-02-29** |
| **W3** | **2024-03-01 → 2024-08-02** |
| **W4** | **2024-08-03 → 2025-12-31** |
| **final test** | **`>= 2026-01-01` — skipped + final_test_refusal=true** |

| 规则 | 实施 |
|---|---|
| `analysis_date >= cutoff` → skip + `final_test_refusal=true` + warning | ✅ |
| `prediction_for_date >= cutoff` → skip + `final_test_refusal=true` + warning（defense-in-depth） | ✅ |
| 落不进任何 window → skip + warning `outside_validation_windows:<date>` | ✅ |
| invalid date string → skip + warning `invalid_analysis_date` | ✅ |
| missing / non-bool `direction_correct` → skip + warning | ✅ |

---

## 9. no validation claims

adapter 输出**永远不包含**以下字段或字符串（双层锁定：顶层 + record 内）：

| 禁止 | 锁定测试 |
|---|---|
| `gate_status` / `validation_passed` / `overall_status` / `hard_*` / `simulated_trade` / `no_trade` / `final_direction` / `final_projection`（顶层） | `NoForbiddenOutputTests::test_no_forbidden_top_level_keys` |
| 同上（record 内） | `test_no_forbidden_record_keys` |
| 字符串 `build_regime_validation_report` | `IsolationTests::test_does_not_call_validation_helper` |
| 字符串 `regime_validation_report.v1` | 同上 |
| import `services.regime_validation_helper` | `IsolationTests::test_module_does_not_import_forbidden` |
| import `json` / `os` / `pathlib` / `io` | `IsolationTests::test_does_not_read_files` |
| 调用 `open(...)` | 同上 |

### 9.1 强约束

| 约束 | 状态 |
|---|---|
| **adapter 不输出 pass/fail** | ✅ |
| **adapter 不输出 `regime_validation_report.v1`** | ✅ |
| **adapter 不调用 validation helper** | ✅；不导入；不引用 |
| **adapter 不知道 6 metrics / 7 gates** | ✅；不计算；不参考 |
| **pass/fail 只能由 Step 3R-4.2 helper 产生** | ✅ |

---

## 10. 测试覆盖

### 10.1 测试结果（commit `3586c05` 实测）

| 命令 | 结果 |
|---|---|
| `pytest tests/test_replay_validation_record_adapter.py -q` | **48 passed** |
| `pytest tests/test_continuous_smoothing_candidate.py -q` | **31 passed**（零回归） |
| `pytest tests/test_regime_validation_helper.py -q` | **33 passed**（零回归） |
| `pytest -q`（全量） | **2801 passed / 10 skipped / 0 failed / 26 warnings / 94 subtests** |

测试基线累积：**Step 3R-3.1 终点 2753 → Step 3R-4.3A 终点 2801**
（+48 净增；2753 基线零回归）。

### 10.2 测试矩阵（48 cases）

| 测试类 | 数量 | 覆盖点 |
|---|---|---|
| `OutputSchemaTests` | 3 | 顶层 8 字段 / 默认 W1-W4 / cutoff 默认 |
| `ThresholdValidationTests` | 7 | None / 负数 / >1 / 字符串 / bool / 0.0 边界 / 1.0 边界 |
| `W4ManifestGateTests` | 10 | valid / final_test_touched / wrong start / wrong end / paired<20 / status≠ok / schema mismatch / cutoff mismatch / 缺 manifest / require=False informational |
| `RowMappingTests` | 3 | 日期映射 / direction_correct → prediction+baseline / actual_state 5 段 |
| `CandidateTriggeredTests` | 6 | >= threshold / < threshold / 边界 = / 缺 candidate / risk_score=None / candidate refusal |
| `DerivedFieldsTests` | 2 | exclusion=triggered / survival_case 真值表 |
| `WindowAssignmentTests` | 4 | W1/W2/W3/W4 分窗 |
| `SafetyTests` | 7 | 2026 refusal / 2026-01-01 边界 / outside windows / invalid date / 缺 direction_correct / rows 不 mutate / manifest 不 mutate |
| `NoForbiddenOutputTests` | 2 | 顶层 + record 内 forbidden keys 都缺 |
| `IsolationTests` | 4 | `ast.walk` 锁定 22 项 forbidden module / 不引用 evaluator function / 不 import json/os/pathlib / 不出现 hard / forced / required 字段名 |

### 10.3 关键覆盖点

- ✅ **schema** — `OutputSchemaTests` × 3
- ✅ **manifest gate** — `W4ManifestGateTests` × 10
- ✅ **threshold required / bounds** — `ThresholdValidationTests` × 7
- ✅ **candidate states** — `CandidateTriggeredTests` × 6
- ✅ **window assignment** — `WindowAssignmentTests` × 4
- ✅ **final test cutoff** — `SafetyTests::test_2026_record_skipped_with_refusal` + `test_cutoff_boundary_2026_01_01_skipped`
- ✅ **input immutability** — `test_input_rows_not_mutated` + `test_manifest_not_mutated`
- ✅ **no forbidden imports** — `IsolationTests::test_module_does_not_import_forbidden`
- ✅ **no file reading** — `IsolationTests::test_does_not_read_files`
- ✅ **no validation helper import/call** — `IsolationTests::test_does_not_call_validation_helper`

---

## 11. 当前限制

| # | 限制 | 解封步骤 |
|---|---|---|
| 1 | **adapter 尚未读取真实 W4 output file** | 由 Step 3R-3.3 caller 负责文件读取 + caller 注入 dict |
| 2 | **adapter 尚未与 3R-3.1 candidate generator 自动串联** | 3R-3.3 设计；caller 责任 |
| 3 | **adapter 尚未与 3R-4.2 helper 串联** | 3R-3.3 设计；caller 责任 |
| 4 | **3R-3.3 validation run 尚未执行** | Step 3R-3.3 |
| 5 | **W1/W2/W3 实际来源仍需 validation run 设计确认** | 3R-3.3 实施时；候选 = 1005 jsonl 同 schema |
| 6 | **没有 dashboard / UI** | Step 3R-7（可选） |
| 7 | **没有 `regime_validation_report.v1` 真实输出** | 3R-3.3 |

---

## 12. 允许下一步

| # | 候选 | 状态 |
|---|---|---|
| 1 | **Step 3R-3.3 4-fold validation run design / execution** | **✅ 允许**（在本 checkpoint 进入 main 后启动）；目标是 adapter → helper 产出第一份 `regime_validation_report.v1` |
| 2 | adapter / helper / candidate 全 read-only 调用 | ✅ |
| 3 | 仍**不得**写 DB | ✅ |
| 4 | 仍**不得**启 hard / forced | ✅ |
| 5 | 仍**不得**改 04 / 05 / 07 required | ✅ |
| 6 | Step 3R-5 formula / Step 3R-6 simulator | **❌ 仍不允许**（必须先过 3R-3.3 实测 acceptance） |
| 7 | adapter pass / report pass 自动启 hard | **❌ 永远不允许** |

---

## 13. 禁止事项

| # | 禁止 | 理由 |
|---|---|---|
| 1 | **不写 DB** | adapter 是 read-only artifact |
| 2 | **不跑 replay** | 输入是已完成 replay 的 jsonl 行 |
| 3 | **不启 hard / forced / anti_false_exclusion_triggered** | 三重 NO-GO（2G-8 / 8B / 8C） |
| 4 | **不改 04 / 05 / 07 required** | Step 2G 全程边界 |
| 5 | **不接 trading**（`longbridge` / `broker` / `paper_trade`） | 永不 |
| 6 | **不触碰 2026** | manifest gate + record-level cutoff 双重 hard stop |
| 7 | **不把 adapter 输出当 pass/fail** | adapter 是数据组装层；pass/fail 由 3R-4.2 helper 产生 |
| 8 | **不直接进入 formula / simulator** | 必须先过 3R-3.3 实测 acceptance |
| 9 | **不读文件** | manifest 由 caller 注入 dict；无 `open(...)` / 无 json/os/pathlib import |
| 10 | **不调用 validation helper** | 评分层与适配层解耦 |
| 11 | **不优化 / 学 candidate_threshold** | 阈值变更必须经 launch review |
| 12 | **不让 `_PROTECTION_LAYER_CONNECTED` 翻 True** | 与 v1 / 3R-0 / 3R-4 一致 |
| 13 | **不让 `hard_gate_status.protection_layer_connected` 自动 pass** | 同上 |
| 14 | **不改 `hard_exclusion_allowed` / `primary_blocker` 派生** | 同上 |
| 15 | **不改 3R-4 protocol thresholds** | 阈值变更必须经 launch review |
| 16 | **不改 3R-2 helper / 3R-3.1 candidate / 3R-4.2 helper 行为** | 仅 read-only 调用 |
| 17 | **不允许 adapter 输出 `gate_status` / `validation_passed` / `overall_status` / `hard_*` / `simulated_trade` / `no_trade` / `final_direction` / `final_projection`** | 双层锁定 |
| 18 | **不接 yfinance / requests / 任何网络** | adapter 不读外部数据 |
| 19 | **不触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*`** | 历史防护 |

---

## 14. 下一步建议

按推荐优先级：

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **commit 本 checkpoint** | 把 §1-15 adapter 状态固化到 main | **本轮 / 下一轮** |
| 2 | **Step 3R-3.3 4-fold validation run design** | 纯 markdown 先行；明确 caller 责任（文件读取 / candidate 调用 / threshold 选择 / report 输出位置） | **高**（commit 本 checkpoint 后） |
| 3 | **Step 3R-3.3 small dry-run using fixtures / limited records** | smoke 验证 adapter → helper 完整链路；产物本地 / `.claude/scratch/`；不进 main | 中（3R-3.3 design 后） |
| 4 | **Step 3R-3.3 real W1-W4 validation report** | 用真实 W4 jsonl + W1/W2/W3（来源由 design 确认）跑 4-fold；产出 `regime_validation_report.v1`；R4 fail acceptance 复检 | 中（dry-run 通过后） |
| 5 | **Step 3R-3.3 checkpoint validation result** | 把实测结果归档（含 candidate 是否 pass / fail / 各 fold worst-window） | 中（3R-3.3 完成后） |
| 6 | **不推荐**直接 Step 3R-5 formula design | 必须先过 3R-3.3 实测 acceptance | **❌** |
| 7 | **不推荐** Step 3R-6 read-only simulator | 必须先过 3R-5 design | **❌** |
| 8 | **不推荐**让 adapter / report `pass` 自动启 hard / Gate 5 / Gate 6 | 与 §10 一致 | **❌** |
| 9 | **不推荐** 升级 04 required | Step 2G 全程边界 | **❌** |
| 10 | **不推荐** 触碰 2026 final test range | 永久封禁 | **❌** |
| 11 | **不推荐** R4 hard implementation | 三重 NO-GO 已锁定 | **❌** |
| 12 | **不推荐**让 `_PROTECTION_LAYER_CONNECTED` 翻 True | 与 v1 / 3R-0 / 3R-4 一致 | **❌** |
| 13 | **不推荐**用 4-fold validation 数据反推 candidate_threshold | 阈值变更必须经 launch review | **❌** |

**关键判断**：
- 顺序 = 本 checkpoint → **3R-3.3 design**（纯 markdown）→ 3R-3.3
  dry-run → 3R-3.3 real validation → 3R-3.3 checkpoint → 3R-5 formula
  → 3R-6 simulator → 3R-7 sidecar
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
  `services/replay_validation_record_adapter.py`（已 merge 在 commit `3586c05`，本 checkpoint 不动） /
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
- ❌ 没改 Step 3R-4.3 design / checkpoint
- ❌ 没改 Step 3R-4.3A adapter（已 merge 在 commit `3586c05`，本 checkpoint 不动）
- ❌ 没改 Step 2G-8D / 8D.1A / 8D.2 / 8D.3 / 8D.4 文档或代码
- ❌ 没把 W4 / smoke 输出 commit 进 main
- ❌ 没读 W4 jsonl 行（仅引用 design / impl 字段表）
- ❌ 没选 `candidate_threshold` / 任何系数 / 任何阈值
- ❌ 没运行 `pytest`（本轮纯文档；测试基线维持 commit `3586c05` 时
  的 2801 / 0 failed / 10 skipped）
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` /
  `avgo_agent.db.backup_*`
- ✅ 只新增 1 份 markdown checkpoint 文档（本文件）
