# Step 2G-5 — Read-Only Soft Metadata Sidecar Simulator Checkpoint

> **Checkpoint 文档，不是实现。** 本文档**冻结** Step 2G-5 的能力范围、
> 公开 API、`soft_metadata.v1` schema、active / removed candidates、
> 真实 DB smoke 数字、与 Step 2G hard/forced 红线的关系。
>
> 本轮**不动任何代码**：不改 `predict.py` / `scanner.py` /
> `prediction_store.py` / `projection_output_adapter.py` /
> `projection_output_contract.py` / `regime_diagnostics_dashboard.py` /
> `soft_metadata_simulator.py` / 任何 builder / 任何 read-only 工具 /
> DB schema 中的任何一处。

## 1. 当前完成状态

- **Step 2G-3** soft / hard exclusion re-review 完成 —— commit `8e837a7`，
  用 380 replay / 286 paired 反驳了旧 `soft_signal` 假设；定位 R4
  为唯一 over-bullish metadata 候选
  ([`tasks/step_2g3_exclusion_re_review_checkpoint.md`](step_2g3_exclusion_re_review_checkpoint.md))。
- **Step 2G-4** soft metadata layer design 完成 —— commit `607ccc0`
  ([`tasks/step_2g4_soft_metadata_layer_design.md`](step_2g4_soft_metadata_layer_design.md))。
- **Step 2G-4.5** soft metadata schema review 完成 —— commit `18936f2`
  ([`tasks/step_2g4_5_soft_metadata_schema_review_checkpoint.md`](step_2g4_5_soft_metadata_schema_review_checkpoint.md))，
  把 8 条 schema-level blocker 固化为 `soft_metadata.v1` 最终形状。
- **Step 2G-5** read-only sidecar simulator 已实现并进入 main —— commit
  `947f1c9` 包含 service + CLI + 48 个 tests + §25 doc。
- 本 checkpoint **冻结** simulator 的实际能力 + 真实 DB smoke 数字 +
  与 Step 2G hard/forced 红线的关系，作为 Step 2G-6（dashboard /
  review display）的前置文档。

## 2. 当前 main 状态

- **main 最新 commit**：
  `947f1c9 feat(diagnostics): add read-only soft metadata sidecar simulator`
- **测试基线**：**2302 passed / 0 failed / 10 skipped /
  26 warnings / 65 subtests passed**（Step 2G-5 起点 2254 → 2302，
  +48 净增）
- **本步骤新增 / 修改文件（4）**：
  - 新增 [`services/soft_metadata_simulator.py`](../services/soft_metadata_simulator.py)
  - 新增 [`scripts/soft_metadata_simulator.py`](../scripts/soft_metadata_simulator.py)
  - 新增 [`tests/test_soft_metadata_simulator.py`](../tests/test_soft_metadata_simulator.py)
  - 修改 [`tasks/step_1_contract_pipeline_summary.md`](step_1_contract_pipeline_summary.md)（新增 §25）
- 未触碰：`predict.py` / `run_predict` / `scanner.py` /
  `prediction_store.py` / `projection_output_adapter.py` /
  `projection_output_contract.py` / `regime_diagnostics_dashboard.py` /
  DB schema / 04 / 05 / 07 任何 required 字段 / 任何 builder /
  4 个离线 anti-false-exclusion 模块。

## 3. 工具定位

- **read-only sidecar simulator**，不是 calibration 引擎、不是
  confidence-score 写入器、不是 trade decision 工具。
- 输出 `soft_metadata.v1`（Step 2G-4.5 §5 修订 schema）。
- 严格只读：
  - `simulate_soft_metadata` 是**纯函数**：不读 DB / 不读 CSV /
    不接网络（`regime_features` + `baseline` 由 caller 注入）
  - `build_soft_metadata_baseline` 是 **SELECT-only** DB reader：不调用
    `init_db` / 不 `INSERT` / 不 `UPDATE` / 不 `DELETE` / 不写文件
- 不改：`predict.py` / `scanner.py` / `prediction_store.py` /
  `projection_output_adapter.py` / `projection_output_contract.py`
- 不改 `final_direction` / `final_projection`（任何字段）
- 不改 04 `exclusion_system` 5 个 required 字段（继续 stub）
- 不改 05 `confidence_system` 4 个 score 字段（继续 0.0；
  `event_score` 继续 None）
- 不改 07 `simulated_trade` 6 个决策字段（继续 `no_trade` / `none` /
  空 / `0%`）
- 不启用 `hard` exclusion
- 不启用 `forced_exclusion`
- 不接 trading API / `longbridge` / `broker` / `paper_trade`
- **用于**：dashboard / review / future sidecar display 消费 JSON。

## 4. Public API

```python
def simulate_soft_metadata(
    payload: dict,
    *,
    regime_features: dict | None = None,    # {"pos20": float, "avgo_minus_soxx_20d": float}
    baseline: dict | None = None,           # caller-injected historical metrics
    analysis_date: str | None = None,       # 覆盖 payload['current_structure']['analysis_date']
    final_test_cutoff: str = "2026-01-01",  # >= cutoff → refuse signals
) -> dict:
    """Pure function. Returns soft_metadata.v1 sidecar dict; never raises."""
```

```python
def build_soft_metadata_baseline(
    db_path: str | Path | None = None,
    symbol: str = "AVGO",
    limit: int = 450,
    *, coded_data_dir: str | Path | None = None,
) -> dict:
    """SELECT-only baseline builder. Calls summarize_regime_diagnostics_dashboard
    + small SELECT for residual. Always returns dict; never raises."""
```

模块级常量（可被消费者引用）：
- `SCHEMA_VERSION = "soft_metadata.v1"`
- `METRICS_SOURCE = "regime_diagnostics_dashboard_v1"`
- `HOLDOUT_STATUS = "FAIL"`
- `DEFAULT_FINAL_TEST_CUTOFF = "2026-01-01"`
- `SEVERITY_LOW = "low"` / `SEVERITY_MEDIUM = "medium"` /
  `SEVERITY_NONE = "none"`（`"high"` / `"hard"` 不存在）
- `ACTIVE_SIGNAL_NAMES = frozenset({"r4_overextension", "bullish_high_pos20_residual"})`
- R4 阈值 (`_R4_AVGO_MINUS_SOXX_THRESHOLD = 5.0` /
  `_R4_POS20_THRESHOLD = 0.62`) 从
  `services.regime_diagnostics_dashboard` import；测试
  `assertIs(..., dashboard.<same>)` 锁定同源（Step 2G-4.5 Blocker 4）。

## 5. `soft_metadata.v1` schema

按 Step 2G-4.5 §5 锁定。顶层字段：

| 字段 | 说明 |
|---|---|
| `schema_version` | 固定字符串 `"soft_metadata.v1"`；任何 schema 改动必须 bump 到 v2 + 写 migration guide |
| `metrics_source` | 固定字符串 `"regime_diagnostics_dashboard_v1"` |
| `metrics_window` | dict `{analysis_date_min, analysis_date_max, paired_total, db_snapshot_id}`；caller-injected baseline 时透传 baseline 的窗口 |
| `metrics_computed_at` | ISO 8601 UTC 时间戳；caller-injected baseline 时透传 baseline 的时间戳 |
| `signals` | list；最多 3 条（v1 实际最多 1-2 条，因两个 candidate 共享 `dedup_group`）|
| `summary` | dict `{has_overextension_signal, max_severity, hard_exclusion_allowed, signal_count, primary_signal, warnings}` |

`signals[i]` 字段：

| 字段 | 说明 |
|---|---|
| `name` | enum `{"r4_overextension", "bullish_high_pos20_residual"}` |
| `display_label` | 中文文案（dashboard 渲染用）|
| `severity` | enum `{"low", "medium"}` —— **没有** `"high"` / `"hard"` |
| `dedup_group` | 固定 `"bullish_overextension"`（v1 两个 candidate 同 group → 同时只 emit 1 条）|
| `raw_features` | trigger features：`{avgo_minus_soxx_20d, pos20}` 或 `{pos20}` |
| `trigger_context` | `{final_direction, confidence_level, primary_score_raw, matched_or_branch, peer_subtype}` 等 |
| `historical_metrics_in_sample` | `{samples, paired, accuracy, bias_gap, false_exclusion_rate, net_benefit}`；缺 baseline 时为 `{}` |
| `holdout_status` | 固定 `"FAIL"` —— Step 3A-4 / 3B-1 holdout 已 FAIL |
| `recommended_action` | 固定 `"review_only"` |
| `hard_forbidden_primary_reason` | 固定 `"false_exclusion_rate_too_high"` |
| `hard_forbidden_breakdown` | list[str]；逐项给出"为什么不能 hard"（fer / nb / 保护层）|

`summary` 字段：

| 字段 | 说明 |
|---|---|
| `has_overextension_signal` | bool；`len(signals) > 0` |
| `max_severity` | enum `{"none", "low", "medium"}`；空 signals 时固定 `"none"` |
| `hard_exclusion_allowed` | **永远** `False`（不变量；Step 2G-4.5 §9.4）|
| `signal_count` | int；assert `== len(signals)` |
| `primary_signal` | 第一条 signal 的 name；空 signals 时 `None` |
| `warnings` | list[str]；缺 baseline / 缺 regime_features / final_test_range_refusal 等 |

## 6. Active candidates

按 Step 2G-4.5 §6 锁定。

### 6.1 active signal enum（仅 2 个）

- `r4_overextension`
- `bullish_high_pos20_residual`

任何其他 `signals[i].name` 视为实施 bug。

### 6.2 removed top-level candidates（永远不出现在 `signals[].name`）

| 原候选 | 处置 |
|---|---|
| `bullish_peer_upgrade_overextension` | 降级为 R4 entry 的 `trigger_context.peer_subtype` 标志（`"upgrade"` / `"hold"` / `"downgrade"` / `"unknown"`） |
| `peer_weaken_metadata_only` | 完全删除；dashboard 改读 `extras.soft_signal` raw 字段 |
| `high_path_risk_metadata_only` | 完全删除；dashboard 改读 `extras.path_risk_level` / `extras.soft_signal` raw 字段 |
| `peer_path_lower_bullish` | 不引入；dashboard 想显示直接读 raw 字段 |
| `conflicting_factors_count_alias_note` | 不引入（与 `peer_weaken` 几乎完全 alias） |

测试 `RemovedCandidateEnforcementTests`（4 个测试）+ `test_signal_names_only_from_active_enum` 锁定。

## 7. R4 behavior

### 7.1 Trigger condition

```
avgo_minus_soxx_20d > _R4_AVGO_MINUS_SOXX_THRESHOLD  (= 5.0, imported from dashboard)
∧ pos20 > _R4_POS20_THRESHOLD                          (= 0.62, imported from dashboard)
∧ final_direction == "偏多"
∧ (confidence_level == "high" ∨ primary_score_raw > 2)
```

`matched_or_branch` 自动派生：
- `"confidence_high"` —— 仅 high confidence 命中
- `"primary_score_raw_gt_2"` —— 仅 psr 命中（confidence != high）
- `"both"` —— 两者同时命中

### 7.2 Output (R4 entry)

| 字段 | 值 |
|---|---|
| `name` | `"r4_overextension"` |
| `display_label` | `"高位跑赢同行后的偏多过热"` |
| `severity` | `"medium"`（自动派生：acc 0.324 < 0.45 → medium）|
| `dedup_group` | `"bullish_overextension"` |
| `recommended_action` | `"review_only"` |
| `hard_forbidden_primary_reason` | `"false_exclusion_rate_too_high"` |
| `hard_forbidden_breakdown` | 包含三条独立理由：<br>• `"false_exclusion_rate=0.3235 > 0.10"`<br>• `"net_benefit=0.0219 < 0.05"`<br>• `"anti_false_exclusion_not_connected"` |
| `holdout_status` | `"FAIL"`（与 Step 3A-4 / 3B-1 holdout FAIL 一致）|

### 7.3 Residual (bullish_high_pos20_residual) behavior

仅当 R4 **不**触发但下面条件满足时 emit：

```
final_direction == "偏多"
∧ confidence_level == "high"
∧ pos20 > _R4_POS20_THRESHOLD
∧ NOT R4
```

字段同 R4 entry，但 `name = "bullish_high_pos20_residual"`、
`display_label = "高位偏多 + 高置信（剔除 R4 后残差）"`、`raw_features`
不含 `avgo_minus_soxx_20d`（残差切片不要求 SOXX diff）、`severity` 自动
派生（实测 acc 0.489 → severity 仍为 medium，因为 bias_gap 0.511 >
0.50）。

## 8. Real DB smoke

CLI baseline-only smoke（main DB / `--symbol AVGO --limit 450`）：

### 8.1 metrics_window / 总览

| 字段 | 值 |
|---|---|
| `metrics_window.analysis_date_min` | `2023-01-03` |
| `metrics_window.analysis_date_max` | `2024-08-02` |
| `metrics_window.paired_total` | **286** |
| `metrics_window.db_snapshot_id` | `null`（v1 留空）|
| `holdout_status` | **`"FAIL"`** |

### 8.2 R4 historical metrics

| 指标 | 值 |
|---|---|
| `samples` | 36 |
| `paired` | 34 |
| `accuracy` | **0.324** |
| `bias_gap` | **+0.676** |
| `false_exclusion_rate` | **0.3235** |
| `net_benefit` | **+0.0219** |

### 8.3 bullish_high_pos20_residual historical metrics

| 指标 | 值 |
|---|---|
| `samples` | 47 |
| `paired` | 47 |
| `accuracy` | **0.489** |
| `bias_gap` | **+0.511** |
| `false_exclusion_rate` | **0.489** |
| `net_benefit` | **−0.001** |

### 8.4 结论

- **R4 数字与 Step 2G-3 deep-dive / Step 3D-1 dashboard byte-by-byte 一致**
  （同 DB / 同 limit）—— 证明 simulator 的 R4 baseline 路径
  (`_r4_baseline_from_dashboard`) 与 dashboard 输出 R4 切片同源。
- **Residual 首次定量化**：accuracy 0.489 / bias_gap +0.511 ——
  比 R4 弱但仍呈 over-bullish 偏多 bias；证实 Step 2G-4.5 Blocker 5
  的"必须算残差不能用整切片"决策（如果直接把整切片 81 paired /
  acc 0.418 给 dashboard 显示，会误导消费者；残差 47 paired / acc 0.489
  是非 R4 上下文里的实际表现）。
- **两者都不能 hard**：
  - R4 `false_exclusion_rate = 0.3235 > 0.10`（gate 上限）；
    `net_benefit = +0.0219 < +0.05`（gate 下限）—— 两项硬性指标都不达标
  - Residual `false_exclusion_rate = 0.489`（更高，远超 0.10）；
    `net_benefit = −0.001`（**负值** —— hard 排除会让整体 accuracy
    略降）—— 比 R4 还差
- **`hard_exclusion_allowed = false` 是正确不变量**：任何输入下、任何
  candidate 触发组合下都恒为 False；测试
  `SchemaShapeTests::test_hard_exclusion_allowed_invariant_on_arbitrary_input`
  锁定。

## 9. CLI usage

```
# Build baseline only (no payload to simulate):
python3 scripts/soft_metadata_simulator.py --symbol AVGO --limit 450

# Simulate a single payload from inline JSON:
python3 scripts/soft_metadata_simulator.py --payload-json '<json>'

# Simulate a single payload from file:
python3 scripts/soft_metadata_simulator.py --payload-file /path/to/payload.json

# Override DB / coded_data location / cutoff:
python3 scripts/soft_metadata_simulator.py --db avgo_agent.db \
    --coded-data-dir ./coded_data --final-test-cutoff 2026-01-01

# Skip baseline build (simulator runs with baseline=None + warning):
python3 scripts/soft_metadata_simulator.py --payload-file p.json --no-baseline

# Override analysis_date for cutoff testing:
python3 scripts/soft_metadata_simulator.py --payload-file p.json \
    --analysis-date 2025-12-31
```

stdout JSON `ensure_ascii=False, indent=2`。退出码：argparse 失败时
非 0；service 内部错误经 `summary.warnings` 表面化，退出码仍为 0
（与 dashboard / extras / outcome / calibration 4 个 read-only CLI
一致）。

## 10. Tests

- 文件：[`tests/test_soft_metadata_simulator.py`](../tests/test_soft_metadata_simulator.py)
- 数量：**48 passed in 0.18s**（unittest）
- related (`test_soft_metadata_simulator.py` +
  `test_regime_diagnostics_dashboard.py` +
  `test_contract_replay_writer.py`)：**163 passed in 4.43s**
- full pytest：**2302 passed / 0 failed / 10 skipped /
  26 warnings / 65 subtests passed**

按 Step 2G-4.5 §10 9 大类覆盖矩阵：

| 类 | 数量 | 内容 |
|---|---|---|
| `SchemaShapeTests` | 6 | 空 payload / schema_version / signal_count == len(signals) / severity 仅 low/medium / 最多 3 条 / `hard_exclusion_allowed` 永远 False |
| `R4TriggerTests` | 10 | R4 触发 / pos20 阈值 / SOXX diff 阈值 / final_direction / 三种 OR-branch (`confidence_high` / `primary_score_raw_gt_2` / `both`) / peer_subtype 三档 + unknown / hard_forbidden 字段 |
| `ResidualTriggerTests` | 3 | residual 触发 / R4 触发时 residual 不重复 / residual baseline 缺失 warning |
| `RemovedCandidateEnforcementTests` | 4 | peer_weaken / high_path_risk / peer_upgrade 单独 / signal name 仅 active enum 两值 |
| `SeverityClassificationTests` | 6 | 严格 `<` / `>` 边界 (acc=0.45 / gap=0.50 → low) / 实测 R4 → medium / 缺 metrics → medium |
| `BaselineHandlingTests` | 2 | baseline=None warning / metrics_window 透传 |
| `ThresholdConstantSourceTests` | 3 | `assertIs` R4 阈值与 dashboard 同源 + grep 源码无字面量 |
| `FinalTestCutoffTests` | 5 | analysis_date == cutoff refuse / > cutoff refuse / < cutoff 通过 / override 优先 / 默认常量锁定 `2026-01-01` |
| `MissingRegimeFeaturesTests` | 2 | 全缺 / pos20-only |
| `ReadOnlyTests` | 1 | tmp DB 行计数前后不变 |
| `NoForbiddenImportsTests` | 1 | `ast.walk` parse 实际 import，禁 yfinance / requests / longbridge / broker / paper_trade / v1 stub trio |
| `BuildBaselineTests` | 3 | 空 DB → empty baseline + warning / 缺 CSV → no residual / `holdout_status` 锁定 `"FAIL"` |
| `CliSmokeTests` | 2 | baseline-only stdout / payload-json + --no-baseline |

测试基线累积：**Step 2G-5 起点 2254 → 2302**（+48 净增）；0 failed；
10 skipped 不变。

## 11. 2026 final test cutoff

- simulator **拒绝** 在 `analysis_date >= "2026-01-01"`（默认 cutoff）
  的 payload 上 emit signals：
  - `signals = []`
  - `summary.warnings` 包含 `"final_test_range_refusal"`
  - `summary.hard_exclusion_allowed` 仍 `False`（不变量恒成立）
  - 不 raise
- 测试 `FinalTestCutoffTests`（5 个测试）覆盖：cutoff 当日拒绝 /
  cutoff 之后拒绝 / cutoff 之前通过 / `analysis_date` override 优先 /
  默认常量锁定 `"2026-01-01"`。
- 本工具 / 本 checkpoint **没有**用 2026-01-01 之后的数据调参 /
  反复跑（main DB 内本就没有 2026-01-01 之后的 replay 行；CLI
  baseline-only smoke 实测 metrics_window 上限 `2024-08-02`）。
- 2026-01-01 之后仍是**整个系统**完成后的最终测试集；任何后续
  Step 2G-6 dashboard / Step 2G-7 anti-false-exclusion / Step 2G-8+
  required 升级，都不得在 final test 之前消耗这部分数据。

## 12. 与 Step 2G hard / forced 的关系

- 本工具**不解除** Step 2G hard exclusion 禁止 —— `hard_exclusion_allowed`
  在每个输出里都是 `False`；hard gate 6 项中 4 项 fail（Step 2G-3 §10
  / Step 2G-4.5 §10.1.6）。
- 本工具**不解除** `forced_exclusion=True` 禁止 —— hard 都没启用，
  forced 没有落地基础（Step 2G 设计文档 §3.4）。
- 本工具**不**改变 04 `exclusion_system` 5 个 required 字段
  —— `exclusion_level` 继续 `"none"`、`exclusion_sources` 继续 `[]`、
  `exclusion_reasons` 继续 `[]`、`forced_exclusion` 继续 `False`、
  `anti_false_exclusion_triggered` 继续 `False`。
- 本工具**不**改变 05 `confidence_system` 4 个 score 字段（继续 0.0；
  `event_score` 继续 None）/ `confidence_level` /
  `total_confidence` / `confidence_reason`。
- 本工具**不**改变 07 `simulated_trade` 6 个决策字段（继续
  `no_trade` / `none` / 空 / `0%`）。
- **R4 仍然不能 hard**：`false_exclusion_rate = 0.3235`（>>0.10）/
  `net_benefit = +0.0219`（<+0.05）—— 两项硬性指标都不达标。
- **Residual 也不能 hard**：`net_benefit = −0.001` 为**负值** ——
  hard 排除会让整体 accuracy **下降**，比保持现状还差。
- 因此本工具的输出**只**作为 dashboard / review / future sidecar
  display 的 metadata 来源；**不**进入主链决策路径。

## 13. 下一步建议

按推荐优先级：

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **Step 2G-6** dashboard / review display design or implementation | 把 simulator 的 JSON 渲染到 Streamlit dashboard 的一个新 tab / review pane；按 Step 2G-4.5 §12.2 文案约束（不写"禁止交易" / "强制否定" / "block" / "exclude"），用"高位偏多过度风险，建议复核" 等措辞 | **高**（本 checkpoint 的天然延续；simulator JSON 已就位，下游消费者就差 UI） |
| 2 | **先做 design doc 还是直接做 small read-only UI component** | 推荐**先 design doc**：dashboard 文案约束 + UI 显示位置 + review 字段绑定 + dedup 显示规则需要冻结，避免边写边改 | 中（与 #1 同 step，可同 checkpoint 完成） |
| 3 | **Step 2G-7** anti-false-exclusion 接入设计 | 4 个候选模块挑一个写接入方案；纯文档，零实现 | 中（任何 soft 真接 04 之前必须先有保护层；当前 sidecar 不进 04，所以可延后）|
| 4 | **不建议**改主链代码 | simulator 输出已能让 dashboard / review 消费 metadata；改 04 / 05 / 07 required 没有边际收益 | — |
| 5 | **不建议**启用 hard | 6 项 gate 仍有 4 项 fail；2 项硬性指标 R4 / residual 都不达标 | — |
| 6 | **不建议**升级 04 / 05 / 07 required 字段 | Step 2G 设计文档 §6 红线 + Step 2G-3 / 2G-4.5 数据加强 | — |
| 7 | **不建议**重启 Step 3 calibration | holdout 仍 FAIL；本 simulator 不解除 holdout FAIL 状态 | — |

dashboard 文案约束（**强烈建议**写进 Step 2G-6 design doc）：

- ❌ 不写 "禁止交易" / "强制否定" / "block" / "exclude" / "force_exclude"
- ✅ 建议写 "高位偏多过度风险，建议复核" /
  "AVGO 强动量 + 高位 + 高置信，历史命中率 32%，请复核" 等**事实陈述**
  + **建议复核**的措辞
- ✅ 文案需明确 `hard_exclusion_allowed=false`（例如 UI 里显式
  显示"非强制否定 / 仅作风险提示"），避免被消费者误读为 hard signal

## 14. 严守边界

- ❌ 没改任何代码（本 checkpoint 是 markdown）
- ❌ 没新增任何测试
- ❌ 没写 DB
- ❌ 没改 DB schema
- ❌ 没改 `predict.py`
- ❌ 没改 `scanner.py`
- ❌ 没改 `prediction_store.py`
- ❌ 没改 `projection_output_adapter.py` / `projection_output_contract.py`
- ❌ 没改 `regime_diagnostics_dashboard.py` /
  `soft_metadata_simulator.py`（service / CLI / tests 全部保持
  Step 2G-5 进 main 的原状）
- ❌ 没改任何 builder（`_build_exclusion_system` /
  `_build_confidence_system` / `_build_simulated_trade` / 任何其他）
- ❌ 没升级 04 / 05 / 07 任何 required 字段
- ❌ 没启用 `hard` / `forced_exclusion` /
  `anti_false_exclusion_triggered`
- ❌ 没接 4 个 anti-false-exclusion 离线模块到主链
- ❌ 没改 `final_projection` / `confidence_score` / `simulated_trade` /
  `no_trade`
- ❌ 没接 `yfinance` / `requests` / 任何网络
- ❌ 没接 trading API / `longbridge` / `broker` / `paper_trade`
- ❌ 没触碰 2026-01-01 之后 final test range
- ❌ 没运行 replay / 没新写 replay 行
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` /
  `avgo_agent.db.backup_*`
- ✅ 只新增 1 份 markdown checkpoint（本文件）
