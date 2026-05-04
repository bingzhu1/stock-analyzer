# Step 3R-2 — Regime Labels Builder Checkpoint

> **状态固化文档（regime labels builder checkpoint），不实现，不改代码。**
> 本文档**冻结** Step 3R-2 helper（commit `e2a681b`）的：公共 API、
> `regime_labels.v1` schema、5 labels + 9 raw_features 行为、
> anti-lookahead / cutoff 不变量、no-validation-claims 边界、与
> Step 3R-4 protocol / Step 2G display 系列的衔接关系。
>
> 本轮**不动任何代码**：不改 `predict.py` / `run_predict` /
> `scanner.py` / `prediction_store.py` / `app.py` / 任何 `ui/*` /
> `services/*`（含 `services/regime_labels_builder.py` /
> `services/regime_features_builder.py`）/ 任何 builder / DB
> schema / 任何 test 中的任何一处。

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
- **Step 3R-2** read-only regime labels builder 已完成并进入 main
  （commit `e2a681b`）—— Step 3R 系列**第一个动代码**步骤
- 本 checkpoint **固定**：
  - `build_regime_labels` 公共 API + 输入约束
  - `regime_labels.v1` schema + 5 label / 9 raw_feature 全部行为
  - anti-lookahead 8 项不变量
  - 2026 final-test refusal 路径
  - **no-validation-claims 边界**（helper 不宣称 pass / fail）
  - 与 Step 3R-4 协议、Step 2G 系列的衔接关系
- Step 3R-2 是 Step 3R-x 8 步路线的第 4 步；本 checkpoint **只是**
  状态归档；不实现 / 不改代码 / 不写 DB / 不调阈值 / 不宣称 validation
  pass / fail

---

## 2. 当前 main 状态

- main 最新 commit：**`e2a681b`**
- commit message：`feat(diagnostics): add regime labels builder`
- 上游：`origin/main` 已同步
- 测试基线：**2642 passed / 0 failed / 10 skipped / 26 warnings /
  94 subtests**（基线 2604 → 2642，+38 净增；现有 2604 基线零回归）

本步骤新增 / 修改文件（已 merge 到 main）：

| 路径 | 类型 | 说明 |
|---|---|---|
| `services/regime_labels_builder.py` | 新增 | pure read-only helper（542 行） |
| `tests/test_regime_labels_builder.py` | 新增 | 38 focused tests |
| `tasks/step_1_contract_pipeline_summary.md` | 修改 | 新增 §36 |

本 checkpoint 文档（即本文件）尚未 commit；本轮只写文档、不 commit /
push。

---

## 3. Public API

```python
build_regime_labels(
    avgo_df,
    peer_dfs: dict | None = None,
    market_dfs: dict | None = None,
    *,
    as_of_date: str,
    final_test_cutoff: str = "2026-01-01",
) -> dict
```

| 项 | 值 |
|---|---|
| 类型 | **pure read-only helper** |
| 是否读 DB | ❌ 否 |
| 是否写 DB | ❌ 否 |
| 是否调 yfinance / 网络 | ❌ 否 |
| 是否调 `prediction_store` | ❌ 否 |
| 是否调 `scanner` / `predict` / `run_predict` | ❌ 否 |
| 是否调 `services.soft_metadata_simulator` / `services.anti_false_exclusion_dashboard` / `services.regime_diagnostics_dashboard` | ❌ 否（`ast.walk` 锁定） |
| 是否产生 validation pass / fail | ❌ 否（详见 §8） |
| 是否 mutate input DataFrame | ❌ 否（`InputImmutabilityTests` × 2 锁定） |
| 是否 raise | ❌ 否（缺数据 → label="unknown" + raw_feature=null + warning） |

---

## 4. `regime_labels.v1` schema

```json
{
  "schema_version": "regime_labels.v1",
  "as_of_date": "YYYY-MM-DD",
  "data_cutoff_date": "YYYY-MM-DD",
  "labels": {
    "pos20_regime": "low | mid | high | extreme | unknown",
    "avgo_minus_soxx_20d_regime": "underperform | neutral | outperform | extreme_outperform | unknown",
    "peer_momentum_regime": "weak | mixed | confirmed | overheated | unknown",
    "market_trend_regime": "weak_market | neutral_market | bull_market | sustained_bull_market | unknown",
    "monthly_context_regime": "normal | earnings_month | breakout_month | shock_month | unknown"
  },
  "raw_features": {
    "pos20": "float | null",
    "avgo_minus_soxx_20d": "float (decimal fraction) | null",
    "peer_confirm_count": "int | null",
    "peer_5d_aligned_pct": "float [0,1] | null",
    "qqq_60d_slope_per_month": "float (decimal/month) | null",
    "qqq_60d_drawdown": "float [0,1] | null",
    "soxx_60d_slope_per_month": "float (decimal/month) | null",
    "monthly_return_pct": "float (decimal) | null",
    "monthly_max_abs_daily_return": "float (decimal) | null"
  },
  "warnings": [],
  "final_test_refusal": false
}
```

**schema 不变量**（继承 Step 3R-1 §6.1，`OutputSchemaTests` /
`LabelsPresentTests` 锁定）：

| 字段 | 必备 | 不变量 |
|---|---|---|
| `schema_version` | ✅ | 总是 `"regime_labels.v1"` |
| `as_of_date` | ✅ | ISO 8601 |
| `data_cutoff_date` | ✅ | `== as_of_date`（schema 强制） |
| `labels` | ✅ | 5 个 label key 全 present；缺数据 → `"unknown"` |
| `raw_features` | ✅ | 9 个 raw feature key 全 present；缺数据 → `null` |
| `warnings` | ✅ | list of string；可空 |
| `final_test_refusal` | ✅ | bool；`as_of_date >= 2026-01-01` 强制 `True` |

---

## 5. 5 labels 行为

| label | buckets | 触发条件 |
|---|---|---|
| `pos20_regime` | `low / mid / high / extreme / unknown` | `low<0.35`；`mid<0.65`；`high<0.85`；`extreme≥0.85`；缺数据 → `unknown` |
| `avgo_minus_soxx_20d_regime` | `underperform / neutral / outperform / extreme_outperform / unknown` | `<-0.05` / `<0.05` / `<0.12` / `≥0.12`；缺 SOXX → `unknown` |
| `peer_momentum_regime` | `weak / mixed / confirmed / overheated / unknown` | `confirm_count` 0/1/2/3 → 4 桶；无可计算 peer → `unknown` |
| `market_trend_regime` | `weak_market / neutral_market / bull_market / sustained_bull_market / unknown` | qqq slope > 0.015 ∧ soxx slope > 0.015 ∧ qqq dd < 0.05 → sustained；任一 slope > 0.01 → bull；双跌或大 drawdown → weak；否则 neutral；缺数据 → `unknown` |
| `monthly_context_regime` | `normal / earnings_month / breakout_month / shock_month / unknown` | max_abs_daily ≥ 0.08 → shock；monthly_return ≥ 0.12 → breakout；月份 ∈ {3,6,9,12} → earnings；否则 normal；缺数据 → `unknown` |

**`unknown` 只在以下场景出现**：
- 缺数据（缺 input DataFrame / insufficient history / NaN OHLC / etc.）
- `final_test_refusal=True`（`as_of_date >= 2026-01-01`）
- 非数字 / 异常输入

**bucket 阈值是 design thresholds（Step 3R-1 §5）**：
- 不是 validated formula
- 不是 production rule
- 必须在 Step 3R-4 protocol 下被 future tools 验证后，candidate 才能
  进入 3R-3 / 3R-5 / 3R-6 / 3R-7

---

## 6. 9 raw_features

每个 raw feature 行为：

| 字段 | 单位 | 缺数据时 |
|---|---|---|
| `pos20` | decimal `[0, 1]` | `null` + warning `pos20_skipped: ...` |
| `avgo_minus_soxx_20d` | **decimal fraction**（design §6 例 `0.077` = 7.7%）| `null` + warning（avgo / soxx return unavailable） |
| `peer_confirm_count` | int（0..可用 peer 数）| `null` + warning（无可计算 peer） |
| `peer_5d_aligned_pct` | decimal `[0, 1]` | `null` + warning（同上） |
| `qqq_60d_slope_per_month` | decimal/月（60d return / 3） | `null` + warning `market_trend_skipped: QQQ_60d_unavailable` |
| `qqq_60d_drawdown` | decimal `[0, 1]` | `null` + warning |
| `soxx_60d_slope_per_month` | decimal/月 | `null` + warning |
| `monthly_return_pct` | decimal | `null` + warning（缺数据时） |
| `monthly_max_abs_daily_return` | decimal | `null` + warning（缺数据时） |

**所有 raw_features**：
- 都是**只读计算**（用 caller-injected DataFrame）
- 缺数据为 `null` + warning string 入 `warnings` list
- 单位与 Step 3R-1 design §6 example schema 完全一致（decimal
  fraction，与 `regime_features_builder.py` 的 percent 单位**不同**，
  本 helper 内部已除以 100）

---

## 7. anti-lookahead / cutoff

继承 Step 3R-1 §7 8 项不变量：

| # | 规则 | 实现位置 |
|---|---|---|
| 1 | `data_cutoff_date == as_of_date` | helper 设置时强制 |
| 2 | 只使用 rows `Date <= as_of_date` | `_compute_pos20_at` / `_nday_return_decimal` / `_trailing_slice` 全部用 `idx <= target_idx` |
| 3 | 不读 outcome（`outcome_log` / `direction_correct` / `actual_*`） | helper 不接受这些输入；isolation 锁定 |
| 4 | 不读 prediction result（`predict_result_json` / `final_direction` / `final_projection`） | 同上 |
| 5 | 不读 review（`review_log`） | 同上 |
| 6 | 不读 2026-01-01 之后任何数据；`as_of_date >= cutoff` → `final_test_refusal=True` + 全 unknown + 全 null + warning `final_test_range_refusal` | `_empty_payload` + `FinalTestRefusalTests` × 3 |
| 7 | strict-causal monthly：`_monthly_context_from_avgo` 用 `avgo_df.index <= target_idx` mask；prior_close 取 `first_in_month_idx - 1` | `_monthly_context_from_avgo` 实现 |
| 8 | input DataFrame 不被 mutate | `InputImmutabilityTests` × 2（avgo_df / peer_dfs） |

**额外锁定**（`AntiLookaheadTests` × 2）：
- 同一 target_date 下，full 90-day df vs truncated（仅到 target+1
  行）的 `pos20` / `avgo_minus_soxx_20d` 完全一致 —— 证明 future
  rows **不**会泄漏

---

## 8. no validation claims

helper 输出**永远不包含**以下任何字段或字符串：

| 禁止字段 / 字符串 | 锁定方式 |
|---|---|
| `overall_status` | `OutputSchemaTests::test_no_pass_fail_validation_fields_in_output` |
| `gate_status` | 同上 |
| `validation_status` / `validation_passed` | 同上 |
| `candidate_status` | 同上 |
| 字符串 `"pass"` | `NoValidationClaimsTests::test_output_does_not_contain_pass_fail_strings` |
| 字符串 `"fail"` | 同上 |
| 字符串 `"validation_passed"` | 同上 |
| 字符串 `"regime_validation_report.v1"` | 同上 |

**核心约束**：
- 本 helper 是**数据层**：只产生 `regime_labels.v1`（labels +
  raw_features + warnings）
- 任何 candidate / threshold / formula 是否通过 Step 3R-4 协议**只能**
  由未来 validation 工具产生 `regime_validation_report.v1` 报告（详见
  Step 3R-4 design §12）
- helper 不预判 / 不简化 / 不偷跑

---

## 9. 测试覆盖

### 9.1 测试结果（commit `e2a681b` 实测）

| 命令 | 结果 |
|---|---|
| `pytest tests/test_regime_labels_builder.py -q` | **38 passed** |
| `pytest tests/test_regime_features_from_scan.py -q` | **17 passed**（零回归） |
| `pytest -q`（全量） | **2642 passed / 10 skipped / 0 failed / 26 warnings / 94 subtests** |

测试基线：**Step 3R-4 终点 2604 → Step 3R-2 终点 2642**（+38 净增；
现有 2604 基线零回归）。

### 9.2 测试矩阵（38 cases）

| 测试类 | 数量 | 覆盖点 |
|---|---|---|
| `OutputSchemaTests` | 4 | 顶层 key / `schema_version` / `data_cutoff_date == as_of_date` / 不出现 pass / fail 字段 |
| `LabelsPresentTests` | 2 | 5 labels + 9 raw_features 全部 present |
| `Pos20BucketTests` | 3 | extreme / low / unknown |
| `DiffBucketTests` | 4 | extreme_outperform / underperform / neutral / unknown when missing SOXX |
| `PeerMomentumTests` | 4 | overheated（3）/ confirmed（2）/ weak（0）/ unknown（无 peer）|
| `MarketTrendTests` | 5 | sustained_bull / bull / weak / unknown / market_dfs 优先级 |
| `MonthlyContextTests` | 4 | breakout / shock / earnings / normal |
| `MissingPeersGracefulTests` | 1 | 缺一个 peer 仍聚合其它 + warning |
| `MissingMarketGracefulTests` | 2 | 缺 QQQ → warning / 缺双 → unknown |
| `FinalTestRefusalTests` | 3 | ≥ 2026 / < 2026 / 自定 cutoff |
| `AntiLookaheadTests` | 2 | full vs truncated df pos20 / diff 一致 |
| `InputImmutabilityTests` | 2 | avgo_df / peer_dfs 不被 mutate |
| `IsolationTests` | 1 | `ast.walk` 锁定禁 import |
| `NoValidationClaimsTests` | 1 | 输出 dict 全树不含 pass / fail / validation_passed / `regime_validation_report.v1` |

### 9.3 关键 isolation 锁定（`ast.walk`）

helper 模块禁止 import：
- `streamlit`
- `yfinance` / `requests`
- `longbridge` / `broker` / `paper_trade`
- `sqlite3`
- `services.prediction_store`
- `services.confidence_engine` / `services.contradiction_engine` /
  `services.risk_model`
- `services.soft_metadata_simulator`
- `services.anti_false_exclusion_dashboard`
- `services.regime_diagnostics_dashboard`
- `predict` / `scanner`
- `ui.protection_layer_diagnostics_renderer`

---

## 10. 与 Step 3R-4 的关系

| 维度 | Step 3R-2 helper | Step 3R-4 protocol |
|---|---|---|
| 功能层 | **数据层**（产生 labels + raw_features） | **评分层**（决定 candidate 是否 pass） |
| 是否优化 thresholds | ❌ 否（用 Step 3R-1 §5 design candidates 原样） | ❌ 否（thresholds 由 launch review 调，不偷跑）|
| 是否宣称 candidate pass / fail | ❌ 否 | ✅ 是（产生 `regime_validation_report.v1`） |
| 是否输出 `gate_status` | ❌ 否 | ✅ 是（7 项 metric × pass/fail） |
| 是否触碰 worst-window 决策 | ❌ 否 | ✅ 是（worst-window 决胜） |
| 关系 | 3R-2 是 3R-4 的输入 | 3R-4 评分 3R-2 输出（含未来 3R-3 / 3R-6 candidate） |
| 任何后续 formula / simulator | **必须**走 3R-4 | — |

→ Step 3R-2 helper **只**给 future tools 提供原始数据；任何 pass /
fail 判断**只能**由 Step 3R-4 协议下的 validation tool 输出。

---

## 11. 与 Step 2G / required 字段关系

| Step 2G 模块 | 与 Step 3R-2 关系 |
|---|---|
| `services/soft_metadata_simulator.py` | 不动；soft_metadata.v1 是 per-prediction signal；regime_labels.v1 是 per-day context；并列存在 |
| `ui/anti_false_exclusion_display.py`（AFX v1）| 不动 |
| `services/protection_layer_diagnostics.py`（8A.1）| 不动 |
| `ui/protection_layer_diagnostics_renderer.py`（8A.2）| 不动 |
| `services/anti_false_exclusion_dashboard.py`（8A.3 aggregate）| 不动；regime_labels 暂未接入 dashboard 字段 |
| Step 2G-7C dashboard 6-gate | **不解封**；regime_labels 不参与 gate |
| `hard_exclusion_allowed` | 永远 `False`；3R-2 不解封 |
| `protection_layer_connected_for_gate` | 永远 `False`；3R-2 不解封 |
| `_PROTECTION_LAYER_CONNECTED` 常量 | 永远 `False`；3R-2 不改 |
| 04 / 05 / 07 required schema | 永远不升级；3R-2 不写 |
| `final_direction` / `final_projection` / `simulated_trade` / `no_trade` / `confidence_system` | 永远不改 |
| `hard` / `forced_exclusion` / `anti_false_exclusion_triggered` | 永远不启用 |

---

## 12. 当前限制

helper 已落地，但仍有边界限制：

| # | 限制 | 解封步骤 |
|---|---|---|
| 1 | 尚未接入 dashboard / UI | Step 3R-2.1（可选；dashboard / UI 集成） |
| 2 | 尚未跑 cross-window validation | 需要 Step 3R-3 / 3R-6 candidate + 3R-4 协议下的 validation tool |
| 3 | 尚未接 W4 数据 | Step 2G-8D extend replay coverage（解耦可并行） |
| 4 | thresholds 未验证 | Step 3R-4 protocol 下的 validation report |
| 5 | 只是 diagnostics helper | Step 3R-3 → 3R-5 → 3R-6 → 3R-7 才能进入 sidecar |
| 6 | 未给 `regime_labels.v1` 加 sidecar 渲染 | Step 3R-7（仅 conditional） |

---

## 13. 下一步建议

按推荐优先级：

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **Step 2G-8D** extend replay coverage（2024-08 → 2025-12） | 数据层；为 W4 准备；与 Step 3R 解耦可并行；不触碰 2026 | **高** |
| 2 | **Step 3R-2.1**（可选）dashboard diagnostics integration | 把 `regime_labels.v1` 输出在 Step 2G-7C aggregate dashboard / Predict / Review UI 中作为 read-only sidecar 显示；**不**改 hard_gate；**不**升级 required | 中（让用户/agent 看见 labels） |
| 3 | **Step 3R-3** continuous smoothing candidate design | 用 logistic / kernel / spline 替代 4×4 lookup；read-only simulator design；纯 markdown 先行 | 中（必须用 3R-4 protocol） |
| 4 | **Step 3R-4.1**（later）validation helper design | 设计未来在 3R-4 协议下产出 `regime_validation_report.v1` 的 helper；纯 markdown 先行 | 中（在 3R-3 出 candidate 后启动） |
| 5 | **不推荐** 直接实现 calibration formula | 必须先过 3R-3 / 3R-4.1 / 3R-5 design | **❌** |
| 6 | **不推荐** 直接实现 simulator | 必须先过 3R-5 design | **❌** |
| 7 | **不推荐** R4 hard implementation | Step 2G-8 / 8B / 8C 三重 NO-GO | **❌** |
| 8 | **不推荐** 让 `_PROTECTION_LAYER_CONNECTED` 翻 True / Gate 5 / Gate 6 自动 pass | 与 Step 3R-0 一致 | **❌** |
| 9 | **不推荐** 升级 04 required schema | Step 2G 全程边界 | **❌** |
| 10 | **不推荐** 触碰 2026 final test range | 永久封禁 | **❌** |

**关键判断**：
- 顺序 = 本 checkpoint → Step 2G-8D（可并行）→ Step 3R-3 design →
  Step 3R-4.1 validation helper design → Step 3R-5 → Step 3R-6 →
  Step 3R-7
- 任意一步在 3R-4 协议下 fail → 整个 Step 3R 进入 NO-GO，**Step 2G
  display 路线为系统最终形态**
- Step 3R-2.1 dashboard 集成是**可选增强**，不阻塞主线

---

## 14. 严守边界

本文是**纯 checkpoint markdown**：

- ❌ 没改任何代码（`services/*` / `ui/*` / `tests/*` 全部未触碰）
- ❌ 没改 DB schema
- ❌ 没写 DB
- ❌ 没改 `run_predict` / `predict.py` / `scanner.py` /
  `prediction_store.py` / `app.py`
- ❌ 没改 `services/regime_features_builder.py` /
  `services/regime_labels_builder.py` /
  `services/regime_diagnostics_dashboard.py` /
  `services/anti_false_exclusion_dashboard.py` /
  `services/soft_metadata_simulator.py` /
  `services/protection_layer_diagnostics.py` /
  `ui/protection_layer_diagnostics_renderer.py` / 任何 ui 模块 /
  任何 builder
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
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` /
  `avgo_agent.db.backup_*`
- ❌ 没运行 `pytest`（本轮纯文档；测试基线维持 commit `e2a681b` 时
  的 2642 / 0 failed / 10 skipped）
- ✅ 只新增 1 份 markdown checkpoint 文档（本文件）
