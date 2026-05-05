# Step 3R-4.3 — Real Replay Record Adapter Design

> **设计文档（real replay record adapter design），不实现，不改代码，不写 DB，不运行 replay / validation。**
> 本文档**冻结** Step 3R-4.3 adapter 的：目标、数据来源、W4 jsonl 字段
> 审查、`replay_validation_records.v1` 输出 schema、validation record
> 字段映射、candidate_triggered / exclusion_would_block / survival_case
> 设计、window assignment、anti-lookahead、与 Step 3R-4.2 helper /
> Step 3R-3.1 candidate generator / Step 2G-8D W4 输出 / hard / required
> / 2026 final test range 边界、风险与禁止事项。
>
> 本轮**不动任何代码**：不改 `predict.py` / `run_predict` /
> `scanner.py` / `prediction_store.py` / `app.py` / 任何 `ui/*` /
> `services/*`（含 `services/regime_validation_helper.py` /
> `services/continuous_smoothing_candidate.py` /
> `services/regime_labels_builder.py`）/ `scripts/*` / 任何 builder /
> DB schema / 任何 test 中的任何一处。
>
> **本文不实现 adapter、不跑 replay / validation、不写 DB、不读
> W4 jsonl 行（仅审查字段名）、不接 trading API**；只在 markdown 层
> 冻结 adapter 设计，给后续 Step 3R-4.3A adapter implementation /
> Step 3R-3.3 4-fold validation run 提供边界。

---

## 1. 背景

| 节点 | 状态 | 关键能力 |
|---|---|---|
| **Step 3R-4.2** validation helper（commits `c669c2f` / `5e58fee`） | ✅ 已 merge | `build_regime_validation_report(records, ...)` 接受 record list；输出 `regime_validation_report.v1` |
| **Step 3R-3.1** candidate generator（commits `5e498bc` / `d0c1387`） | ✅ 已 merge | `build_continuous_smoothing_candidate(regime_labels, ...)` 单日输入输出 `continuous_smoothing_candidate.v1` |
| **Step 3R-2** labels builder（commits `e2a681b` / `db7618b`） | ✅ 已 merge | `build_regime_labels(...)` 单日输入 |
| **Step 2G-8D.3** W4 full replay（main 上 commit `4bdd782`，输出本地 untracked） | ✅ 已跑完 | `logs/historical_training/three_system_w4_2024_08_2025_12/three_system_replay_results.jsonl`（353 paired，`final_test_touched=false`） |

**评分层 + 候选层 + 数据层**全部就绪，但**单日 candidate output 与
353 行 W4 replay records 之间缺一个 adapter**。本文设计这个 adapter。

---

## 2. 目标

| 目标 | 说明 |
|---|---|
| **读取 replay result rows** | W4 jsonl + 未来 W1/W2/W3 来源；按行解析；read-only |
| **提取 analysis_date / prediction_for_date / correctness** | 字段映射详见 §4 / §5 |
| **调用或接收 regime_labels / candidate output** | adapter 可以调用 `build_regime_labels` + `build_continuous_smoothing_candidate`；也可以接受 caller-injected 预算结果 |
| **生成 helper records** | 输出符合 `build_regime_validation_report(...)` 期待的 record list |
| **不写 DB** | 全部 read-only；输出仍是 in-memory dict |
| **不跑 replay** | 输入是已完成 replay 的 jsonl |
| **不产生 pass/fail** | adapter 只组装输入；3R-4.2 helper 才产出 `overall_status` |
| **不改 candidate / helper** | 仅 read-only 调用其 API |
| **不改 protocol thresholds** | 阈值在 helper 内部锁定 |
| **不接 yfinance / requests / trading** | 与 helper / candidate 同等 isolation |

---

## 3. 数据来源

| 数据 | 来源 |
|---|---|
| **W1 / W2 / W3** | 现有 replay / DB / historical output；**待 adapter 实施时确定**（候选优先级：1) `logs/historical_training/three_system_1005/three_system_replay_results.jsonl`（最近 1005 trading day，覆盖 W1-W3 范围）；2) `avgo_agent.db` `prediction_log` + `outcome_log` join；3) 其他 `logs/historical_training/` 目录） |
| **W4** | `logs/historical_training/three_system_w4_2024_08_2025_12/three_system_replay_results.jsonl`（**本地 untracked**；不进 main） |
| **W4 manifest** | `logs/historical_training/three_system_w4_2024_08_2025_12/validation_ready_manifest.json`（`w4_replay_manifest.v1`） |
| **regime_labels** | future `services.regime_labels_builder.build_regime_labels(...)` 调用，或预先组装的 snapshot（adapter 应允许两种） |
| **candidate output** | `services.continuous_smoothing_candidate.build_continuous_smoothing_candidate(regime_labels, ...)` |

### 3.1 来源约束

| 约束 | 状态 |
|---|---|
| W4 jsonl 必须先通过 manifest gate（`final_test_touched=false` + 7 项其他检查） | ✅；与 Step 3R-4.2 §5 一致 |
| W1/W2/W3 来源**不**进入 final-test 范围（仅 `< 2026-01-01`） | ✅ |
| W4 输出**不**进 main；adapter 在本地运行时读取 | ✅；与 8D.4 §6.3 一致 |
| 任何来源行 `analysis_date >= 2026-01-01` → adapter 必须 skip + 触发 final_test_refusal | ✅ |
| adapter 不允许扫描 main DB 中 prediction_log 之外的字段 | ✅；read-only |

---

## 4. W4 jsonl 字段审查

实测（commit `5e498bc` 时）`three_system_replay_results.jsonl` 第一行
顶层 47 个字段（节选）：

| 字段 | 类型 | 用途 |
|---|---|---|
| **`as_of_date`** | str (ISO) | **analysis_date** 的来源 |
| **`prediction_for_date`** | str (ISO) | T+1 配对 |
| **`direction_correct`** | bool | **prediction_correct** 的来源（同时 v1 充当 baseline_correct，详见 §7） |
| `final_direction` | str | 预测方向（`"偏多"` / `"偏空"` / `"中性"`） |
| `actual_state` | str | 实际五态（`"大涨"` / `"小涨"` / `"震荡"` / `"小跌"` / `"大跌"`） |
| `actual_close_change` | float | 实际涨跌幅 |
| `actual_open_label` / `actual_close_label` / `actual_path_label` | str | 实际路径 |
| `error_layer` / `error_category` | str | 诊断；用于 warnings |
| `ready` | bool | 该 row 是否完成 |
| `warnings` | list[str] | 已有 row-level warnings |
| `negative_excluded` | bool | 历史 negative 系统是否触发；可作 candidate cross-check |
| `pos20` | float | **percentage 单位（如 27.9 = 27.9%）；与 `regime_labels.v1.raw_features.pos20`（decimal `[0, 1]`）单位不同；adapter 不直接使用 replay 的 pos20，而是调用 3R-2 builder** |
| `nvda_ret1` / `soxx_ret1` / `qqq_ret1` | float \| null | peer / market 1d 回报（v1 不被 candidate 直接消费；3R-2 builder 内部计算） |

### 4.1 字段不明确 / 注意事项

| 项 | 状态 |
|---|---|
| **`baseline_correct` 字段** | **不存在** — adapter 必须 derive；v1 设 `baseline_correct = direction_correct`（详见 §7） |
| **`survival_case` 字段** | **不存在** — adapter 必须 derive；详见 §7 |
| **`exclusion_would_block` 字段** | **不存在** — adapter 必须 derive |
| **W1/W2/W3 jsonl 是否同 schema** | **adapter implementation must inspect**；预期与 1005 jsonl 一致（同一 replay 主链），但需在 3R-4.3A 实施时实测 |
| **不同 source 的字段单位是否一致**（pos20 percentage vs decimal） | **adapter 必须**只把 jsonl 当成 outcome / correctness 来源；feature 一律由 3R-2 builder 重算 |
| **缺 `direction_correct` 行**（`ready=False` 等） | adapter skip + warning `record_skipped:not_ready_or_unpaired` |
| **pos20 / peer / market data 在 jsonl 中是 instant value，not as_of_date 的 builder 输入** | adapter 永远不用 jsonl 的 feature 列；只用 outcome 列 |

---

## 5. validation record schema

adapter 输出的 record 列表，每条 record（喂给 3R-4.2 helper）：

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
| `prediction_correct` | bool；`null`（未配 outcome）→ adapter skip + warning |
| `baseline_correct` | bool；`null` → adapter skip |
| `exclusion_would_block` | bool |
| `survival_case` | bool |
| `actual_direction` | enum；adapter 从 `actual_close_change` 派生（`> 0` → `"up"`；`< 0` → `"down"`；`== 0` → `"flat"`；缺 → `"unknown"`） |
| `labels` | optional；如果 adapter 启用 labels diagnostics |
| `candidate` | optional；用于回溯 candidate output |
| `window` | enum；adapter 按 §8 资料指派 |
| `warnings` | list of string；可空 |

---

## 6. candidate_triggered 设计

| 项 | 值 |
|---|---|
| 公式 | **`candidate_triggered = (risk_score >= candidate_threshold)`** |
| `risk_score` 来源 | `services.continuous_smoothing_candidate.build_continuous_smoothing_candidate(labels).risk_score` |
| `candidate_threshold` | **不在本文选择**；adapter 仅作为参数接受 |
| `risk_score is None`（refusal / 缺字段） | `candidate_triggered = False`；adapter 加 warning `candidate_unavailable` |
| 是否调用 candidate generator | adapter 可以**直接调用** OR **接受 caller-injected** candidate output；两种皆允许 |
| caller 需提供的参数 | `candidate_threshold: float`（必填；no default） |

### 6.1 强约束

| 强约束 | 状态 |
|---|---|
| **`candidate_threshold` 不在本文选择** | ✅ |
| **adapter 只能接受 threshold 参数，不内置优化** | ✅ |
| **threshold 必须由 future validation design / launch review 指定** | ✅ |
| **adapter 不调参** | ✅；不允许 adapter 在内部根据 4-fold validation 数据反推 threshold |
| **不允许 adapter 给 threshold 一个 default = 学到 4-fold 的最佳值** | ✅；adapter API 必须把 threshold 列为 required positional/keyword arg without default |
| **不允许 adapter override SEED 系数** | ✅；3R-3.1 SEED 是模块常量 |

---

## 7. exclusion_would_block / survival_case

| 字段 | 公式（v1） | 说明 |
|---|---|---|
| `exclusion_would_block` | `candidate_triggered`（即 v1 candidate 触发即 block） | 与 Step 3R-3 §9 / 3R-3.1 §8 一致 |
| `survival_case` | `candidate_triggered ∧ prediction_correct` | candidate 触发但实际预测正确（即被 candidate 误杀的多头判断） |
| `prediction_correct` | replay row 的 `direction_correct`（bool） | adapter 不重新评分 |
| `baseline_correct` | replay row 的 `direction_correct`（**v1 设同 prediction_correct**） | 见 §7.1 |

### 7.1 baseline_correct = direction_correct 的合理性（v1）

| 论据 | 状态 |
|---|---|
| replay row 的 `direction_correct` 是**没有 candidate 介入**的真实 prediction outcome（baseline） | ✅ |
| candidate 是 v1 sidecar，**不**重新预测；它只标 "would block"；当 candidate 不触发，prediction 与 baseline 完全相同 | ✅ |
| 3R-4.2 helper 对 `net_benefit` / `accuracy_delta_vs_baseline` 的算法：先剔除 blocked records 再算 candidate-adjusted accuracy；对 baseline 则是 paired records 的整体 accuracy；二者**共享 outcome 来源**（即 row.direction_correct） | ✅ |
| v1 不允许 adapter 对 prediction_correct / baseline_correct 做单独修改 | ✅；adapter 不改 correctness |

未来如果 candidate 升级为"重新预测"（formula 阶段），baseline_correct
和 prediction_correct 才会语义分化。v1 设同。

---

## 8. window assignment

| 规则 | 实施 |
|---|---|
| 按 `analysis_date` 落入 W1/W2/W3/W4 之一 | adapter 用 `regime_validation_helper.DEFAULT_WINDOWS` 或 caller-supplied `windows` dict |
| 落不进任何 window → skip + warning `record_skipped:out_of_window:<date>` | ✅ |
| `analysis_date >= 2026-01-01` → **整 adapter 调用 abort + final_test_refusal=True** | ✅ |
| W4 records 必须先过 manifest gate（adapter 启动时调用 3R-4.2 helper 同款 gate） | ✅ |
| W1/W2/W3 records 不需要 manifest（来源是 main 上的 replay，不是 W4 artifact） | ✅ |

### 8.1 window 边界

| window | start | end |
|---|---|---|
| W1 | 2023-01-03 | 2023-08-31 |
| W2 | 2023-09-01 | 2024-02-29 |
| W3 | 2024-03-01 | 2024-08-02 |
| W4 | 2024-08-03 | 2025-12-31 |
| final test | 2026-01-01 | ∞ — **forbidden** |

---

## 9. anti-lookahead

| 规则 | 实施 |
|---|---|
| **adapter 不读取 future rows** | adapter 按 `analysis_date` 单向遍历；不允许"先看完整 W4 再回头给 W1 调系数" |
| **regime labels 必须按 `as_of_date == analysis_date` 计算** | 调用 `build_regime_labels(..., as_of_date=row.analysis_date)`；与 3R-1 §7 / 3R-2 §7 anti-lookahead 8 项不变量一致 |
| **candidate `as_of_date` = analysis_date** | 调用 `build_continuous_smoothing_candidate(labels, as_of_date=row.analysis_date)` |
| **outcome 只来自已配对 replay review**（即 jsonl row 的 `direction_correct`） | adapter 不重新跑 outcome / 不调 yfinance |
| **不使用 2026** | G1 + G2 + adapter row-level filter 三重 hard stop |
| **不允许 adapter 用一个 window 的 metric 调另一个 window 的 threshold** | ✅；threshold 是 caller 传入的 single value，applies uniformly |
| **不允许 adapter 把 W4 outcome 写回 W1/W2/W3 records** | ✅ |

---

## 10. output schema

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

### 10.1 schema 不变量

| 字段 | 不变量 |
|---|---|
| `schema_version` | 总是 `"replay_validation_records.v1"` |
| `candidate_name` | string；`"continuous_smoothing_v1"` (v1) |
| `candidate_threshold` | float \| null；caller 提供（**不在 adapter 内部 default**） |
| `records` | list；每条符合 §5 schema |
| `windows` | dict；与 3R-4.2 / 3R-4.1 默认一致 |
| `source_files` | list of relative paths；用于可追溯 |
| `final_test_refusal` | bool；任一 row `analysis_date >= 2026-01-01` 立即 `true` + 整 adapter abort |
| `warnings` | list of string |

### 10.2 不允许字段

| 禁止字段 | 理由 |
|---|---|
| `gate_status` / `validation_passed` / `overall_status` | adapter 是数据层；validation 由 3R-4.2 helper 输出 `regime_validation_report.v1` |
| `hard_*` / `simulated_trade` / `no_trade` / `final_direction` / `final_projection` | candidate 永不直接驱动 hard 路径 |

---

## 11. 与 Step 3R-4.2 helper 的关系

| 维度 | adapter（本设计） | helper（已 merge） |
|---|---|---|
| 角色 | 数据组装层 | 评分层 |
| 输入 | replay jsonl / DB rows + candidate output + labels | record list |
| 输出 | `replay_validation_records.v1`（含 records 列表） | `regime_validation_report.v1` |
| 是否宣称 candidate pass / fail | ❌ 否 | ✅ 是 |
| 是否调阈值 | ❌ 否 | ❌ 否 |
| 是否触碰 2026 | ❌ 否 | ❌ 否 |
| 是否写 DB | ❌ 否 | ❌ 否 |

→ adapter `replay_validation_records.v1.records` 直接作为 helper 的
`records` 输入；二者**解耦**：adapter 不知道 metric / gate；helper 不
知道 jsonl / candidate generation。

---

## 12. 与 Step 3R-3.1 candidate 的关系

| 维度 | candidate（已 merge） | adapter（本设计） |
|---|---|---|
| API | `build_continuous_smoothing_candidate(regime_labels, ...)` | adapter 可调用 |
| 输出 | `continuous_smoothing_candidate.v1` (含 risk_score) | adapter 取 `risk_score` 转 `candidate_triggered` |
| 是否调阈值 | ❌ 否（SEED 系数固定） | ❌ 否（threshold 由 caller 传入） |
| candidate 是否决定 pass/fail | ❌ 否（diagnostics） | ❌ 否（数据组装） |

→ adapter 只把 candidate 当成 read-only **diagnostics**；candidate
output 字段（risk_score / risk_bucket / features_used）可作为 record
的 `candidate` optional 字段保留以便回溯，但**不参与** validation gate。

### 12.1 强约束

| 强约束 | 状态 |
|---|---|
| **不反推 SEED 系数** | ✅；SEED 是 3R-3.1 模块常量 |
| **adapter 不修改 candidate 输出** | ✅；read-only |
| **不允许 adapter 把 risk_bucket 直接当 gate** | ✅；gate 由 3R-4.2 helper 决定 |

---

## 13. 与 W4 输出的关系

| 维度 | W4 output dir |
|---|---|
| W4 output dir 是否进 main | **❌ 否**（与 8D.4 §6.3 一致；保持 untracked） |
| adapter 是否可读取本地 untracked W4 jsonl | **✅ 可**（read-only；不修改） |
| W4 manifest 必须先通过 | **✅ 是**（与 3R-4.2 §5 W4 manifest gate 完全一致） |
| W4 是否等于 final test | **❌ 否**；W4 = 2024-08-03 → 2025-12-31，final test = 2026-01-01 → ∞ |
| adapter 是否触碰 2026 | **❌ 否**（manifest gate + record-level cutoff 双重 hard stop） |

---

## 14. 风险

| # | 风险 | 应对 |
|---|---|---|
| 1 | **replay jsonl 字段可能不稳定** | 3R-4.3A 实施时锁定 jsonl 字段映射；新增字段 → adapter ignore；缺字段 → skip + warning |
| 2 | **W1-W3 来源可能和 W4 格式不一致** | 优先选用 1005 jsonl（同 schema）；如必须用 DB，需写独立 mapping helper；3R-4.3A 实测 |
| 3 | **correctness 字段可能需要映射** | v1 直接使用 `direction_correct`；如 W1-W3 来源用其他字段名 → adapter 提供 mapping table |
| 4 | **threshold 可能被误调成 overfit** | adapter API 把 `candidate_threshold` 列为 required 参数（no default）；不允许 adapter 自动选 threshold |
| 5 | **candidate labels 可能缺 raw_features** | candidate generator 已处理（缺 → risk_score=None）；adapter 把这些 record 标记为 `candidate_triggered=False` + warning |
| 6 | **大量 records 处理可能慢**（W1-W4 合计 ~ 639 行 × 单日 labels build ~ 1-3s） | 预期 runtime ~ 15-30 分钟；3R-4.3A 实施时可加 caching 选项；本设计不实施 caching |
| 7 | **labels builder 需要 caller 准备 DataFrames** | 3R-4.3A 实施时设计 `labels_source` 回调或预算 snapshot；adapter 不读 csv |
| 8 | **W4 manifest 可能因后续操作 final_test_touched=true** | adapter 启动时强制 re-validate manifest；任何 false→true 翻转 → adapter abort |
| 9 | **某些 row `ready=False`** | adapter skip + warning `record_skipped:not_ready` |
| 10 | **某些 row 没有配 outcome** | adapter skip + warning `record_skipped:missing_outcome` |
| 11 | **重复 record（同 analysis_date 出现多次）** | adapter v1 不去重；caller 责任；如有 → warning `duplicate_analysis_date` |
| 12 | **labels / candidate 缺失 → 大量 candidate_triggered=False** | 这是合法降级；helper 仍会按 paired_outcomes 算；如 paired < 20 per fold → 该 fold 触发 `minimum_window_sample_size` no-go |

---

## 15. 实施顺序建议

| # | 子步骤 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **commit 本 design** | 把 §1-17 adapter 设计固化到 main | **本轮 / 下一轮** |
| 2 | **Step 3R-4.3 checkpoint** | 状态归档；锁定 schema / 字段映射 / 实施顺序 | **下一轮**（commit 本 design 后） |
| 3 | **Step 3R-4.3A adapter implementation** | 新增 `services/replay_validation_record_adapter.py`（命名待定）；纯 read-only；focused tests；W4 manifest gate；W1-W3 来源在实施时通过 inspection 确认 | 中（在 3R-4.3 checkpoint 进 main 后） |
| 4 | **Step 3R-3.3 4-fold validation run using adapter + helper** | adapter → helper → `regime_validation_report.v1`；R4 fail acceptance 复检；threshold 由 caller 显式提供（v0 可用 0.60 即 risk_bucket >= high） | 中（3R-4.3A 完成后） |
| 5 | **Step 3R-3.3 checkpoint validation result** | 把 `regime_validation_report.v1` 实测结果归档 | 中（3R-3.3 完成后） |

---

## 16. 禁止事项

| # | 禁止 | 理由 |
|---|---|---|
| 1 | **不写 DB** | adapter 是 read-only artifact |
| 2 | **不改 replay output** | adapter 只读取 jsonl，不修改 |
| 3 | **不改 candidate coefficients**（SEED） | 与 3R-3.1 §5 一致 |
| 4 | **不选择 candidate_threshold** | 由 caller 提供；调动必须经 launch review |
| 5 | **不跑 validation** | helper 由 3R-3.3 调 |
| 6 | **不宣称 pass/fail** | 与 §11 / §12 一致；输出**无** `gate_status` / `overall_status` |
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
| 22 | **不允许 adapter `replay_validation_records.v1` 包含 `gate_status` / `validation_passed` / `overall_status` / `hard_*` / `simulated_trade` / `no_trade` / `final_direction` / `final_projection`** | 与 §10.2 一致 |
| 23 | **不触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*`** | 历史防护 |

---

## 17. 严守边界

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
- ❌ 没改 Step 2G-8D / 8D.1A / 8D.2 / 8D.3 / 8D.4 文档或代码
- ❌ 没把 W4 / smoke 输出 commit 进 main
- ❌ 没读 W4 jsonl 行（仅审查字段名 + 第一行 schema 用于 §4 字段表）
- ❌ 没选 `candidate_threshold` / 任何系数 / 任何阈值
- ❌ 没运行 `pytest`（本轮纯文档；测试基线维持 commit `d0c1387` 时
  的 2753 / 0 failed / 10 skipped）
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` /
  `avgo_agent.db.backup_*`
- ✅ 只新增 1 份 markdown design 文档（本文件）
