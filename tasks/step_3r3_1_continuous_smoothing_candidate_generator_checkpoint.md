# Step 3R-3.1 — Continuous Smoothing Candidate Generator Checkpoint

> **状态固化文档（continuous smoothing candidate generator checkpoint），不实现，不改代码，不写 DB，不运行 replay。**
> 本文档**冻结** Step 3R-3.1 helper（commit `5e498bc`）的：公共 API、
> `continuous_smoothing_candidate.v1` schema、5 seed coefficients、
> market_trend_strength 4 段、monthly_shock 3 段、risk_bucket 5 桶、
> final_test_refusal 双路径、no-validation-claims 边界、31 focused
> tests + 2753 全量 pytest 基线、与 Step 3R-2 helper / Step 3R-3
> design / Step 3R-4.2 helper / hard / required / 2026 final test range
> 边界。
>
> 本轮**不动任何代码**：不改 `predict.py` / `run_predict` /
> `scanner.py` / `prediction_store.py` / `app.py` / 任何 `ui/*` /
> `services/*`（含 `services/continuous_smoothing_candidate.py` /
> `services/regime_labels_builder.py` /
> `services/regime_validation_helper.py`）/ `scripts/*` / 任何 builder /
> DB schema / 任何 test 中的任何一处。
>
> **本文不实施 adapter / validation run / formula、不跑 replay、不写
> DB、不接 trading API**；只在 markdown 层固化 candidate generator
> 状态，作为后续 Step 3R-4.3 real replay record adapter / Step 3R-3.3
> 4-fold validation run 的强制 gate。

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
- **Step 3R-3.1** read-only candidate generator 已完成并进入 main
  （commit `5e498bc`）—— Step 3R 系列**候选层第一个动代码步**
- 本 checkpoint **固定**：
  - `build_continuous_smoothing_candidate(...)` 公共 API + 4 参数 + 8
    项 read-only 约束
  - `continuous_smoothing_candidate.v1` schema 10 字段 + 8 项不允许
    字段
  - 5 SEED 系数（design-stage，**not validated**）
  - market_trend_strength 4 段优先级 + monthly_shock 3 段
  - risk_bucket 5 桶
  - final_test_refusal 双路径（cutoff + propagated）
  - no-validation-claims 边界（输出 / 字符串 / 模块文件三层锁定）
  - 31 focused tests + 2753 全量 pytest 基线
  - 与 Step 3R-2 / Step 3R-3 / Step 3R-4.2 / hard / required / 2026 边界
- **Step 3R-4.3 real replay record adapter / Step 3R-3.3 validation
  run 仍未启动**：本 checkpoint 是它们之前的强制 gate

---

## 2. 当前 main 状态

- main 最新 commit：**`5e498bc`**
- commit message：`feat(diagnostics): add continuous smoothing candidate generator`
- 上游：`origin/main` 已同步
- 测试基线：**2753 passed / 0 failed / 10 skipped / 26 warnings /
  94 subtests**（Step 3R-4.2 终点 2722 → Step 3R-3.1 终点 2753，
  +31 净增；2722 基线零回归）

本步骤新增 / 修改文件（已 merge 到 main）：

| 路径 | 类型 | 说明 |
|---|---|---|
| `services/continuous_smoothing_candidate.py` | 新增 | pure read-only candidate generator（302 行）；输入 `regime_labels.v1` dict，输出 `continuous_smoothing_candidate.v1`（含 risk_score / risk_bucket / market_trend_strength / monthly_shock / SEED_COEFFICIENTS） |
| `tests/test_continuous_smoothing_candidate.py` | 新增 | 31 focused tests |
| `tasks/step_1_contract_pipeline_summary.md` | 修改 | 新增 §39 |

本 checkpoint 文档（即本文件）尚未 commit；本轮只写文档、**不**
commit / push。

| 项 | 是否触碰 |
|---|---|
| 改代码 | ❌ 否 |
| 写 DB | ❌ 否 |
| 跑 replay | ❌ 否 |
| 改 services/continuous_smoothing_candidate.py（已 merge 在 commit `5e498bc`） | ❌ 否 |
| 改 services/regime_labels_builder.py / regime_validation_helper.py | ❌ 否 |
| 改 DB schema | ❌ 否 |
| 接 yfinance / 网络 | ❌ 否 |
| 接 trading API | ❌ 否 |
| 触碰 2026 final test | ❌ 否 |

---

## 3. Public API

```python
build_continuous_smoothing_candidate(
    regime_labels: dict,
    *,
    as_of_date: str | None = None,
    final_test_cutoff: str = "2026-01-01",
) -> dict
```

| 项 | 值 |
|---|---|
| 类型 | **pure read-only helper** |
| 是否读 DB | ❌ 否 |
| 是否写 DB | ❌ 否 |
| 是否跑 replay | ❌ 否 |
| 是否读 W4 output | ❌ 否（输入仅是 caller-injected `regime_labels.v1` dict） |
| 是否接网络 / trading | ❌ 否（`ast.walk` 锁定） |
| 是否 import `prediction_store` / `scanner` / `predict` / `yfinance` / `requests` / `streamlit` / `services.regime_validation_helper` 等 18 项 forbidden | ❌ 否（`ast.walk` 锁定） |
| 是否暴露 threshold / coefficients 参数 | ❌ 否（API 不允许 override SEED 系数；调动必须经 launch review） |
| 是否触碰 2026 | ❌ 否（`as_of_date >= cutoff` → `final_test_refusal=true` + risk_score=None） |
| 是否宣称 validation pass / fail | ❌ 否 |

### 3.1 参数

| 参数 | 默认 | 说明 |
|---|---|---|
| `regime_labels` | required | `regime_labels.v1` dict（来自 3R-2 helper） |
| `as_of_date` | None | 显式 override；优先级高于 `regime_labels["as_of_date"]` |
| `final_test_cutoff` | `"2026-01-01"` | hard cutoff |

---

## 4. `continuous_smoothing_candidate.v1` schema

```json
{
  "schema_version": "continuous_smoothing_candidate.v1",
  "as_of_date": "YYYY-MM-DD",
  "data_cutoff_date": "YYYY-MM-DD",
  "candidate_name": "continuous_smoothing_v1",
  "risk_score": "float | null",
  "adjustment_score": "float | null",
  "risk_bucket": "low | medium | high | extreme | unknown",
  "features_used": {
    "pos20": "float | null",
    "avgo_minus_soxx_20d": "float | null",
    "peer_5d_aligned_pct": "float | null",
    "market_trend_strength": "float | null",
    "monthly_shock": "float | null",
    "seed_coefficients": {
      "pos20": 1.2,
      "avgo_minus_soxx_20d": 1.0,
      "peer_5d_aligned_pct": -0.8,
      "market_trend_strength": -0.7,
      "monthly_shock": 0.5
    }
  },
  "warnings": [],
  "final_test_refusal": false
}
```

### 4.1 schema 不变量

| 字段 | 不变量 |
|---|---|
| `schema_version` | 总是 `"continuous_smoothing_candidate.v1"` |
| `as_of_date` | ISO 8601；**`< final_test_cutoff`** 当 `final_test_refusal=false` |
| `data_cutoff_date` | `== as_of_date` |
| `candidate_name` | `"continuous_smoothing_v1"` |
| `risk_score` | float ∈ [0, 1] 或 null（refusal / 缺字段） |
| `adjustment_score` | `risk_score - 0.5` 或 null |
| `risk_bucket` | enum 5 值 |
| `features_used.seed_coefficients` | dict；与 design 一致；deep copy |
| `warnings` | list of string；可空 |
| `final_test_refusal` | bool |

---

## 5. Seed coefficients

| 系数 | 值 | 方向 |
|---|---:|---|
| `pos20` | **+1.2** | pos20 高 → 风险高 |
| `avgo_minus_soxx_20d` | **+1.0** | AVGO 跑赢 SOXX 多 → 风险高 |
| `peer_5d_aligned_pct` | **-0.8** | peer 同向强 → 风险下降 |
| `market_trend_strength` | **-0.7** | sustained bull 强 → 风险下降 |
| `monthly_shock` | **+0.5** | shock / breakout 月 → 风险加成 |

### 5.1 强约束

| 约束 | 状态 |
|---|---|
| **seed coefficients 是 design-stage** | ✅ |
| **不是 optimized** | ✅（`test_module_does_not_use_optimized_terminology` 锁定模块文件无 `optimized_coefficients` / `optimised_coefficients` 术语） |
| **不是 validated formula** | ✅；任何 candidate variant 必须经 Step 3R-4.2 helper 出 `regime_validation_report.v1` |
| **不能直接用于 production decision** | ✅（与 §10 一致；no validation claims） |
| 不允许 caller override（API 不暴露 threshold 参数） | ✅ |
| 调系数必须经 launch review；不允许用 4-fold validation 数据反推 | ✅ |
| `SEED_COEFFICIENTS` 是模块常量；输出层每次 deep copy 防止意外 mutate | ✅（`test_seed_coefficients_dict_is_deep_copy`） |

---

## 6. market_trend_strength（4 段优先级）

| 段 | 触发条件 | 值 |
|---|---|---:|
| `strong_bull` | `qqq_60d_slope_per_month > 0.015` ∧ `soxx_60d_slope_per_month > 0.015` ∧ `qqq_60d_drawdown < 0.05` | **1.0** |
| `bull` | `qqq_60d_slope_per_month > 0.01` 或 `soxx_60d_slope_per_month > 0.01`（任一） | **0.6** |
| `weak` | `qqq_60d_drawdown > 0.10` 或（`qqq_60d_slope_per_month < -0.005` ∧ `soxx_60d_slope_per_month < -0.005`） | **-0.5** |
| `neutral` | 其它 | **0.0** |

精度：先检 strong_bull → bull → weak → neutral；与 helper 实现一致
（commit `5e498bc` `_compute_market_trend_strength`）。

---

## 7. monthly_shock（3 段优先级）

| 段 | 触发条件 | 值 |
|---|---|---:|
| shock | `monthly_max_abs_daily_return >= 0.08` | **1.0** |
| breakout | `monthly_return_pct >= 0.12`（且 shock 未触发） | **0.5** |
| neutral | 其它 | **0.0** |

---

## 8. risk_bucket（5 桶）

| bucket | 范围 |
|---|---|
| `low` | `risk_score < 0.35` |
| `medium` | `0.35 <= risk_score < 0.60` |
| `high` | `0.60 <= risk_score < 0.80` |
| `extreme` | `risk_score >= 0.80` |
| `unknown` | `risk_score is None`（refusal / 缺字段） |

### 8.1 强约束

| 约束 | 状态 |
|---|---|
| **display only** | ✅ |
| **not hard exclusion** | ✅；与 §10 一致 |
| **not validation status** | ✅；不允许把 risk_bucket 视为 `gate_status` 等价物 |
| 不进入 4-fold gate 决策（Step 3R-4.2 helper 只看 metrics） | ✅ |
| 不允许用 W4 / final test 数据反推 bucket 阈值 | ✅ |
| 阈值变更必须经 launch review | ✅ |

---

## 9. final_test_refusal

### 9.1 双触发路径

| 触发 | 行为 |
|---|---|
| `as_of_date >= 2026-01-01`（含边界 `=`） | `final_test_refusal=true` + `risk_score=None` + `adjustment_score=None` + `risk_bucket="unknown"` + warning `final_test_range_refusal` |
| `regime_labels.final_test_refusal=True`（来自 3R-2 helper 上游） | 同上 + warning `regime_labels_final_test_refusal_propagated` |

`as_of_date` 显式参数优先级高于 `regime_labels["as_of_date"]`（用于
caller 强制重新评估某日；测试 `test_explicit_as_of_date_overrides_labels`
锁定）。

### 9.2 refusal 行为

| 字段 | refusal 时值 |
|---|---|
| `risk_score` | `None` |
| `adjustment_score` | `None` |
| `risk_bucket` | `"unknown"` |
| `features_used.pos20` | `None`（不计算） |
| `features_used.avgo_minus_soxx_20d` | `None` |
| `features_used.peer_5d_aligned_pct` | `None` |
| `features_used.market_trend_strength` | `None` |
| `features_used.monthly_shock` | `None` |
| `features_used.seed_coefficients` | dict（永远 emit；常量） |
| `warnings` | 含 `final_test_range_refusal` 或 `regime_labels_final_test_refusal_propagated` |
| `final_test_refusal` | `true` |

→ refusal 路径**不**计算 features、**不**调 sigmoid、**不**触碰 2026
范围数据。

---

## 10. no validation claims

输出**永远不包含**以下任何字段或字符串：

| 禁止字段 / 字符串 | 锁定测试 |
|---|---|
| `gate_status` | `NoValidationClaimsTests::test_no_forbidden_keys_in_output` |
| `validation_passed` | 同上 |
| `overall_status` | 同上 |
| `hard_exclusion_allowed` / `hard_gate_status` | 同上 |
| `simulated_trade` | 同上 |
| `no_trade` | 同上 |
| `final_direction` | 同上 |
| `final_projection` | 同上 |
| 字符串 `"validation_passed"` / `"regime_validation_report.v1"` | `test_no_pass_fail_validation_strings_in_output` |
| 模块文件提到 `hard_exclusion_allowed` / `forced_exclusion` / `_PROTECTION_LAYER_CONNECTED` / `simulated_trade` / `no_trade` / `final_direction` / `final_projection` | `test_module_does_not_reference_hard_or_required_fields` |
| 模块文件含 `optimized_coefficients` / `optimised_coefficients` 术语 | `test_module_does_not_use_optimized_terminology` |

---

## 11. 测试覆盖

### 11.1 测试结果（commit `5e498bc` 实测）

| 命令 | 结果 |
|---|---|
| `pytest tests/test_continuous_smoothing_candidate.py -q` | **31 passed** |
| `pytest tests/test_regime_labels_builder.py -q` | **38 passed**（零回归） |
| `pytest -q`（全量） | **2753 passed / 10 skipped / 0 failed / 26 warnings / 94 subtests** |

测试基线累积：**Step 3R-4.2 终点 2722 → Step 3R-3.1 终点 2753**
（+31 净增；2722 基线零回归）。

### 11.2 测试矩阵（31 cases）

| 测试类 | 数量 | 覆盖点 |
|---|---|---|
| `OutputSchemaTests` | 3 | 顶层 10 字段全 present / `seed_coefficients` 在 features_used 内 / `data_cutoff_date == as_of_date` |
| `RiskScoreRangeTests` | 4 | risk_score ∈ [0, 1] / low bucket / extreme bucket / `adjustment_score = risk_score - 0.5` |
| `MarketTrendStrengthTests` | 5 | strong_bull / bull / weak (drawdown) / weak (both negative) / neutral |
| `MonthlyShockTests` | 3 | shock / breakout / neutral |
| `MissingFeatureTests` | 3 | 缺 pos20 / 缺 peer / 缺 raw_features dict |
| `FinalTestRefusalTests` | 4 | 边界 2026-01-01 / 后段 2026-04-01 / 显式 arg override / regime_labels propagated |
| `ImmutabilityTests` | 1 | 输入 dict 深拷贝不被 mutate |
| `NoValidationClaimsTests` | 2 | 无 forbidden 字段；无 forbidden 字符串 |
| `IsolationTests` | 3 | `ast.walk` 锁定 18 项 forbidden module；字符串锁定无 `optimized_coefficients` / hard / required 引用 |
| `SeedCoefficientsTests` | 3 | SEED 5 项与 design 一致 / 输出含 SEED / SEED 是 deep copy |

### 11.3 关键覆盖点

- ✅ **output schema** — `OutputSchemaTests` × 3
- ✅ **risk_score range** — `RiskScoreRangeTests` × 4
- ✅ **bucket boundaries** — `RiskScoreRangeTests::test_risk_bucket_low / extreme`
- ✅ **market_trend_strength** — `MarketTrendStrengthTests` × 5
- ✅ **monthly_shock** — `MonthlyShockTests` × 3
- ✅ **missing feature behavior** — `MissingFeatureTests` × 3
- ✅ **final_test_refusal** — `FinalTestRefusalTests` × 4
- ✅ **input immutability** — `test_input_dict_not_mutated`
- ✅ **no validation claims** — `NoValidationClaimsTests` × 2
- ✅ **no forbidden imports** — `IsolationTests::test_module_does_not_import_forbidden`
- ✅ **seed coefficients** — `SeedCoefficientsTests` × 3

---

## 12. 当前限制

| # | 限制 | 解封步骤 |
|---|---|---|
| 1 | **没有读取 replay records** | Step 3R-4.3 real replay record adapter |
| 2 | **没有生成 validation records** | Step 3R-4.3 |
| 3 | **没有跑 4-fold validation** | Step 3R-3.3（after 3R-4.3 + 3R-3.1） |
| 4 | **没有证明 candidate pass** | Step 3R-3.3 实测 + 3R-4.2 helper 出 `regime_validation_report.v1` |
| 5 | **没有 dashboard / UI** | Step 3R-7（可选；与 sidecar integration 配对） |
| 6 | **只是 read-only candidate diagnostics** | 与设计意图一致；production wiring 永远独立 step |
| 7 | **SEED 系数未验证** | 通过 3R-3.3 实测后由 launch review 决定 |
| 8 | **未接 3R-2 builder pipeline**（即未联动 3R-2 → 3R-3.1） | 可选；本 helper 接受 caller-injected dict |
| 9 | **未接 3R-4.2 helper**（即未联动 3R-3.1 → 3R-4.2） | 由 3R-4.3 adapter 串联 |

---

## 13. 允许下一步

| # | 候选 | 状态 |
|---|---|---|
| 1 | **Step 3R-4.3 real replay record adapter** | **✅ 允许**（在本 checkpoint 进入 main 后）；纯 wrapper / adapter；把 W1/W2/W3 + W4 jsonl + 3R-3.1 candidate output 组装成 3R-4.2 helper 接受的 records list |
| 2 | **Step 3R-3.3 4-fold validation run** | **必须等 3R-4.3 完成**；用 3R-3.1 + 3R-4.3 + 3R-4.2 出 `regime_validation_report.v1`；R4 fail acceptance 复检 |
| 3 | **Step 3R-5 formula design** | **❌ 仍不允许**（必须先过 3R-3.3 实测 + 4-fold acceptance） |
| 4 | **Step 3R-6 read-only simulator** | **❌ 仍不允许**（必须先过 3R-5 design） |
| 5 | candidate 直接进 production | **❌ 永远不允许**；wiring 必须经 launch review |
| 6 | 用 4-fold 数据反推 SEED 系数 | **❌ 永远不允许**；调阈值必须经 launch review |
| 7 | 升级 04 / 05 / 07 required | **❌ 永远不允许** |
| 8 | 启 hard / forced / Gate 5 / Gate 6 | **❌ 永远不允许** |

---

## 14. 严守边界

本文是**纯 checkpoint markdown**：

- ❌ 没改任何代码（`services/*` / `ui/*` / `tests/*` / `scripts/*` 全部未触碰）
- ❌ 没改 DB schema
- ❌ 没写 DB
- ❌ 没运行 replay
- ❌ 没改 `run_predict` / `predict.py` / `scanner.py` /
  `prediction_store.py` / `app.py`
- ❌ 没改 `services/regime_features_builder.py` /
  `services/regime_labels_builder.py` /
  `services/regime_validation_helper.py` /
  `services/continuous_smoothing_candidate.py`（已 merge 在 commit `5e498bc`） /
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
- ❌ 没改 Step 3R-3 design / checkpoint
- ❌ 没改 Step 3R-3.1 helper（已 merge 在 commit `5e498bc`，本 checkpoint 不动）
- ❌ 没改 Step 3R-4.1 design / checkpoint
- ❌ 没改 Step 3R-4.2 helper / checkpoint
- ❌ 没改 Step 2G-8D / 8D.1A / 8D.2 / 8D.3 / 8D.4 文档或代码
- ❌ 没把 W4 / smoke 输出 commit 进 main
- ❌ 没读 W4 results（adapter 由 3R-4.3 实施）
- ❌ 没用 4-fold 数据反推 SEED 系数
- ❌ 没运行 `pytest`（本轮纯文档；测试基线维持 commit `5e498bc` 时
  的 2753 / 0 failed / 10 skipped）
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` /
  `avgo_agent.db.backup_*`
- ✅ 只新增 1 份 markdown checkpoint 文档（本文件）
