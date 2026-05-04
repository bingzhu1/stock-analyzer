# Step 2G-7C — Anti-False-Exclusion Dashboard Aggregate Diagnostics Checkpoint

> **Checkpoint 文档，不是实现。** 本文档**冻结** Step 2G-7C aggregate
> service / CLI 的输出 schema、真实 DB 数字、hard gate 6 项状态、与
> Step 2G-8 的衔接关系、当前限制。
>
> 本轮**不动任何代码**：不改 `predict.py` / `run_predict` /
> `scanner.py` / `prediction_store.py` / `app.py` / `ui/*` /
> `services/*` / 任何 builder / DB schema 中的任何一处。

## 1. 当前完成状态

- **Step 2G-7** anti-false-exclusion display design（commit `cd571e4`）
- **Step 2G-7A/7B** display helper + Predict / Review expandable
  integration（commit `ca3445a`）+ checkpoint（commit `18911e4`）
- **Step 2G-7C** aggregate diagnostics service + CLI 已实现并进入
  main —— commit `e099c57` 包含：
  - 新增 `services/anti_false_exclusion_dashboard.py`
  - 新增 `scripts/anti_false_exclusion_dashboard.py`
  - 新增 `tests/test_anti_false_exclusion_dashboard.py`（35 个 unittest
    含 1 个 subprocess CLI smoke）
  - 修改 `tasks/step_1_contract_pipeline_summary.md` §32
- 本 checkpoint **冻结** dashboard aggregate 输出 schema + 真实 DB
  数字 + hard gate 6 项状态 + Step 2G-8 启动条件 + 当前限制，作为
  后续 Step 2G-7D review_log free-text design / Step 2G-7E dashboard
  UI integration / Step 2G-8 spec launch-condition review 的前置文档。

## 2. 当前 main 状态

- **main 最新 commit**：
  `e099c57 feat(diagnostics): add anti-false-exclusion dashboard aggregate`
- **测试基线**：**2521 passed / 0 failed / 10 skipped /
  26 warnings / 65 subtests passed**（Step 2G-7C 起点 2486 → 2521，
  +35 净增）
- **本步骤新增 / 修改文件（4）**：
  - 新增 [`services/anti_false_exclusion_dashboard.py`](../services/anti_false_exclusion_dashboard.py)
  - 新增 [`scripts/anti_false_exclusion_dashboard.py`](../scripts/anti_false_exclusion_dashboard.py)
  - 新增 [`tests/test_anti_false_exclusion_dashboard.py`](../tests/test_anti_false_exclusion_dashboard.py)
  - 修改 [`tasks/step_1_contract_pipeline_summary.md`](step_1_contract_pipeline_summary.md)（新增 §32）
- 未触碰：`predict.py` / `run_predict` / `scanner.py` /
  `prediction_store.py` / `projection_output_adapter.py` /
  `projection_output_contract.py` / `regime_diagnostics_dashboard.py` /
  `soft_metadata_simulator.py` / `soft_metadata_renderer.py` /
  `soft_metadata_injection.py` / `regime_features_builder.py` /
  `soft_metadata_baseline_cache.py` / `anti_false_exclusion_display.py` /
  `predict_tab.py` / `review_tab.py` / 任何 builder / DB schema /
  04 / 05 / 07 任何 required 字段 / `simulated_trade.no_trade` 策略
  边界 / 任何其他 `ui/*` 模块。

## 3. aggregate service / CLI

```python
def summarize_anti_false_exclusion_dashboard(
    db_path: str | Path | None = None,
    *, symbol: str = "AVGO", limit: int = 450,
) -> dict:
    """Read-only aggregate. Delegates to build_soft_metadata_baseline.
    Always returns a dict; never raises."""
```

- **read-only service**：不写 DB / 不写文件 / 不接网络
- 委托 `services.soft_metadata_simulator.build_soft_metadata_baseline`
  取 R4 / residual baseline；service 自身无 SQL
- CLI 文件：[`scripts/anti_false_exclusion_dashboard.py`](../scripts/anti_false_exclusion_dashboard.py)
- stdout JSON `ensure_ascii=False, indent=2`

CLI 用法：

```
python3 scripts/anti_false_exclusion_dashboard.py
python3 scripts/anti_false_exclusion_dashboard.py --symbol AVGO --limit 450
python3 scripts/anti_false_exclusion_dashboard.py --db avgo_agent.db --symbol AVGO --limit 450
```

退出码：argparse 失败时非 0；service 内部错误经 `status="error"` +
`warnings` 表面化，退出码仍为 0（与其他 read-only 诊断 CLI 一致）。

## 4. 输出 schema

| 顶层字段 | 类型 | 说明 |
|---|---|---|
| `status` | `"ok"` / `"no_records"` / `"error"` | 错误经此 surface |
| `symbol` | str | 标准化后 |
| `records_scanned` | int | == `metrics_window.paired_total` |
| `paired_outcomes` | int | 同上 |
| `calibration_ready` | bool | `paired_total >= 90` |
| `metrics_window` | dict | `{analysis_date_min, max, paired_total, db_snapshot_id}` |
| `metrics_computed_at` | str | ISO timestamp |
| `soft_metadata_summary.r4_overextension` | dict \| None | 9 字段（详见 §5） |
| `soft_metadata_summary.bullish_high_pos20_residual` | dict \| None | 同上结构 |
| `survival_cases.r4_survival_count` | int \| None | == `r4.correct_when_triggered` |
| `survival_cases.r4_survival_rate` | float \| None | == `r4.accuracy` |
| `hard_gate_status` | dict | 6 项 `"pass"` / `"fail"`（详见 §8） |
| `hard_exclusion_allowed` | bool | `all(v == "pass" for v in gates)` |
| `primary_blocker` | str \| None | 优先级派生（fer → nb → holdout → paired → protection） |
| `warnings` | list[str] | baseline warnings + 本层 missing-candidate warnings |

## 5. 真实 DB R4 数字（main DB / `--symbol AVGO --limit 450`）

| 字段 | 值 |
|---|---|
| `samples` | 36 |
| `paired` | **34** |
| `correct_when_triggered` | **11**（= `round(accuracy × paired)`）|
| `wrong_when_triggered` | **23** |
| `accuracy` | **0.3235** |
| `false_exclusion_rate` | **0.3235**（bullish slice 下 == accuracy）|
| `net_benefit` | **+0.0219** |
| `bias_gap` | **+0.676** |
| `holdout_status` | **`"FAIL"`** |

**解释**（与 Step 2G-7 / 2G-7A 一致）：
- R4 全部 `predicted_bullish_rate=1.0`（条件包含 `final_direction=偏多`），
  因此 `correct_when_triggered` 等价于 `actual_up_count`；fer 与
  accuracy 数字相等是这个 invariant 的自然结果
- **如果 hard 排除 R4，会同时误杀 11 个正确样本** —— 这是
  Step 2G-7 / 2G-7A / 2G-7C 全程要让消费者一眼看到的关键事实

## 6. residual 数字

| 字段 | 值 |
|---|---|
| `paired` | **47** |
| `correct_when_triggered` | **23**（= `round(0.489 × 47)`）|
| `accuracy` | **0.489** |
| `false_exclusion_rate` | **0.489** |
| `net_benefit` | **−0.001**（**负值**）|
| `bias_gap` | **+0.511** |
| `holdout_status` | **`"FAIL"`** |

**结论**：residual **更不能** hard，因为 `net_benefit` 为**负值**
—— hard 排除会让整体 accuracy 不升反降。这与 Step 2G-3 deep-dive
/ Step 2G-5 simulator baseline 一致。

## 7. survival cases

| 字段 | 值 |
|---|---|
| `r4_survival_count` | **11** |
| `r4_survival_rate` | **0.3235** |

这些样本：
- 对应 Review 的 `triggered_but_not_error` 象限（Step 2G-6C §5）
- 是 anti-false-exclusion 保护层的**核心 ground truth**：未来任何
  hard 升级都会同时杀掉这 11 个正确样本
- 在 dashboard 上显式量化让消费者看到"如果硬化排除会损失多少"

## 8. hard gate 6 项状态（main DB 真数据）

| # | gate | status | value |
|---|---|---|---|
| 1 | `total_paired_ge_90` | **pass** | 286 ≥ 90 |
| 2 | `candidate_paired_ge_30` | **pass** | R4 paired 34 ≥ 30 |
| 3 | `false_exclusion_rate_lte_0_10` | **fail** | 0.3235 > 0.10（超阈值 3.2 倍） |
| 4 | `net_benefit_gte_0_05` | **fail** | +0.0219 < +0.05（不到一半） |
| 5 | `protection_layer_connected` | **fail** | v1 hard-coded `False`（4 模块全离线） |
| 6 | `cross_window_holdout_pass` | **fail** | `holdout_status="FAIL"`（Step 3A-4 / 3B-1） |

**结论**：
- **2 pass / 4 fail**
- `hard_exclusion_allowed = False`
- `primary_blocker = "false_exclusion_rate_too_high"`（按 Step 2G-7
  §7 优先级链）

## 9. hard 是否仍禁止

| 字段 / 行为 | 状态 |
|---|---|
| hard exclusion | ❌ **禁止**（4 项 gate fail） |
| `forced_exclusion=True` | ❌ **禁止**（hard 都没启用，forced 没有落地基础）|
| 04 `exclusion_system` 5 个 required 字段 | ❌ 不升级（继续 stub）|
| 05 `confidence_system` 4 个 score 字段 + `event_score` | ❌ 不升级（继续 0.0 / None）|
| 07 `simulated_trade` 6 个决策字段 | ❌ 不升级（继续 `no_trade` / `none` / 空 / `0%`）|
| `anti_false_exclusion_triggered` required | ❌ 仍 stub `False`（**与本 sidecar 不同名**）|
| `summary.hard_exclusion_allowed`（soft_metadata 内 + AFX sidecar 内）| ❌ 永远 `False`（renderer + simulator + injection + Review + AFX display + AFX dashboard **六重**锁定）|

**Step 2G-7C 只是 diagnostics，不改变 gate 状态**；恰恰相反，把 4 项
fail 显式量化在 aggregate JSON 上，让 dashboard / 命令行用户一眼
看到"为什么 hard 仍然禁止"。

## 10. 测试覆盖

| 命令 | 结果 |
|---|---|
| `pytest tests/test_anti_false_exclusion_dashboard.py -q` | **35 passed in 0.11s** |
| `pytest tests/test_anti_false_exclusion_display.py tests/test_regime_diagnostics_dashboard.py -q` | **56 passed in 0.23s** |
| `pytest -q`（全量） | **2521 passed, 10 skipped, 26 warnings, 65 subtests passed in 11.65s** |

测试覆盖（共 35 个新增）：

| 测试类 | 数量 | 内容 |
|---|---|---|
| `OutputSchemaTests` | 4 | 顶层字段必填 / status=ok / calibration_ready 阈值切换 |
| `CandidateExtractionTests` | 4 | R4 字段直透 / `correct_when_triggered` 派生 / residual / `holdout_status` 继承 baseline 顶层 |
| `HardGateTests` | 8 | 默认 4 fail / 5 边界条件（paired / fer / nb / holdout PASS / FAIL）/ protection_layer 永远 fail |
| `HardExclusionAllowedTests` | 3 | 默认 False / 空 baseline False / 即使 5 项 pass 仅 protection 仍 fail → 整体 False |
| `PrimaryBlockerTests` | 4 | 优先级 fer → nb → holdout → protection_layer |
| `SurvivalCasesTests` | 2 | survival_count == correct_when_triggered；survival_rate == accuracy |
| `EmptyBaselineTests` | 5 | empty → status=no_records / soft_metadata_summary None / warnings 透传 / hard 仍 False / builder 异常 → status=error |
| `InputPassthroughTests` | 1 | `db_path` / `symbol` / `limit` 透传 |
| `InputImmutabilityTests` | 1 | baseline dict 不被原地修改 |
| `IsolationTests` | 2 | `ast.walk` 锁定禁 import / `patch` 锁定 prediction_store 不调 |
| `CliSmokeTests` | 1 | subprocess CLI smoke：JSON 解析 + 顶层 invariants |

测试基线累积：**Step 2G-7C 起点 2486 → 2521**（+35 净增）；
0 failed；10 skipped 不变。

## 11. Isolation / read-only

- ❌ service 模块**不**直接 import `sqlite3`（委托 baseline builder）
- ❌ **不** import `services.prediction_store`（同上）
- ❌ **不** import `services.regime_diagnostics_dashboard`（同上）
- ❌ **不** import `streamlit`（service 是纯数据；UI 集成由后续 step
  做）
- ❌ **不** import `yfinance` / `requests` / `longbridge` / `broker` /
  `paper_trade` / v1 stub trio
- ✅ SELECT **完全委托**已有 `build_soft_metadata_baseline`（自身已
  锁定 read-only，Step 2G-5 / 6B.6 测试已覆盖）
- ✅ CLI smoke 覆盖 `no_records` 退化路径（空 DB → status="no_records"
  + hard_exclusion_allowed=False）
- ✅ **不写 DB / 不写文件**

`ast.walk` parse 锁定的禁止 import 列表：`yfinance` / `requests` /
`longbridge` / `broker` / `paper_trade` / `sqlite3` / `services.prediction_store`
/ `services.confidence_engine` / `services.contradiction_engine` /
`services.risk_model` / `confidence_engine` / `contradiction_engine` /
`risk_model`。

## 12. 与 Step 2G-8 的关系

> **Step 2G-8 不应直接开始 implementation**。

Step 2G-8 candidate 升级 04 / 05 / 07 required 字段 + 启用 hard /
forced 的前置条件是 6 项 hard gate **全部通过**。当前 4 项 fail：

| # | blocker | 当前 gap | 是否独立 step 可解决 |
|---|---|---|---|
| 3 | `false_exclusion_rate_too_high` | 0.3235 → 必须 ≤ 0.10（差 3.2 倍）| 需要 Step 3 calibration 重启或 R4 子切片重新设计 → **不**独立解决 |
| 4 | `net_benefit_insufficient` | +0.0219 → 必须 ≥ +0.05（不到一半）| 与 #3 同源 → **不**独立解决 |
| 5 | `protection_layer_connected` | v1 hard-coded false（4 模块全离线）→ 必须至少接 1 个 | **可**独立做（Step 2G-7E 候选；纯设计 → 实现需要改 `_build_exclusion_system`）|
| 6 | `cross_window_holdout_pass` | `FAIL` → 必须 `PASS`（Step 3A-4 / 3B-1 已 FAIL）| Step 3 calibration 范围 → **不**独立解决 |

**结论**：Step 2G-8 只有在 #3 / #4 / #6 任意一项**有明确缩小路径**
之后才值得启动；否则 spec launch-condition review 应判 "**当前不
启动**"。

## 13. 下一步建议

按推荐优先级：

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **Step 2G-8 spec launch-condition review**（纯文档） | 详细评估 4 个 fail gate 的 gap：哪些可以靠独立 step 缩小（如 protection layer 接入设计），哪些必须等 Step 3 calibration 重启；输出"是否值得启动 Step 2G-8 任何子任务"的明确判断 | **高**（避免 2G-8 凭直觉启动；让 calibration / hard 升级的延迟有书面理由）|
| 2 | **Step 2G-7D review_log free-text design**（可选；纯文档） | 设计 4 象限归因 + 5 个 finding 如何写入 `review_log.confidence_note` / `watch_for_next_time` free-text；不改 required；让 review 历史可查询 | 中（让 review 历史可查询；但当前 UI 临时显示已足够）|
| 3 | **Step 2G-7E dashboard UI integration**（可选；UI 改动） | 把 §4 输出 schema 渲染到 Streamlit dashboard 一个新 tab；纯 read-only UI；不改 required | 中（让 aggregate diagnostics 在 UI 真实可见；CLI 已就位）|
| 4 | **Step 2G-6B.8 baseline refresh button**（可选；UX 增强） | sidebar 加按钮；纯 UI 改动 | 中-低 |
| 5 | **不建议**直接升级 hard / required（Step 2G-8 实施） | 6 项 gate 仍有 4 项 fail；本步显示层就位**不**改变 fail 状态；必须先做 #1 review 才能决定 | — |
| 6 | **不建议**改 `run_predict` / `prediction_store` 主链 | 当前 sidecar + UI display + Review attribution + protection display + dashboard aggregate 已是最大可行边界 | — |
| 7 | **不建议**直接做 save-time DB enrichment（Step 2G-6B.1 候选 C）| 写 DB + migration 成本高 | — |

**强制约束**：Step 2G-7D / 2G-7E / 2G-6B.8 实施时仍要遵守：
- 不改 04 / 05 / 07 required 字段
- 不改 `review_log` required 字段（free-text 字段写入需独立 design）
- 不改 `run_predict` 主链
- 不写 DB（除非另立 DB hygiene 任务）
- 不出现 16 forbidden words（页面级）/ 19 forbidden words（AFX 内部）
- `hard_exclusion_allowed` 永远 `False`

## 14. 严守边界

- ❌ 没改任何代码（本 checkpoint 是 markdown）
- ❌ 没新增任何测试
- ❌ 没写 DB
- ❌ 没改 DB schema
- ❌ 没改 `run_predict`
- ❌ 没改 `predict.py`
- ❌ 没改 `scanner.py`
- ❌ 没改 `prediction_store.py`
- ❌ 没改 `projection_output_adapter.py` / `projection_output_contract.py`
- ❌ 没改 `regime_diagnostics_dashboard.py` / `soft_metadata_simulator.py` /
  `soft_metadata_renderer.py` / `soft_metadata_injection.py` /
  `regime_features_builder.py` / `soft_metadata_baseline_cache.py` /
  `anti_false_exclusion_display.py` / `anti_false_exclusion_dashboard.py` /
  `predict_tab.py` / `review_tab.py`（Step 2G-7C 已 commit；本
  checkpoint 不改）
- ❌ 没改任何 builder（`_build_exclusion_system` /
  `_build_confidence_system` / `_build_simulated_trade` / 任何其他）
- ❌ 没改 `app.py` / 任何其他 `ui/*` 模块
- ❌ 没升级 04 / 05 / 07 任何 required 字段
- ❌ 没改 `review_log` 任何 required 字段
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
