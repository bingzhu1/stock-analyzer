# Step 2G-6B.6 / 6B.7 — Baseline Cache + Regime Features Production Chain Checkpoint

> **Checkpoint 文档，不是实现。** 本文档**冻结** Step 2G-6B.6 baseline
> session cache + Step 2G-6B.7 `scan_result["regime_features"]` 共同
> 形成的 Predict 侧 production end-to-end 链路、helper 行为、计算
> 口径、anti-lookahead / 2026 cutoff 双重防护、Predict 接入方式、
> dev hint 两个根因的解决状态、测试覆盖、required 字段不变量、当前
> 限制、与 Step 2G-6C / 2G-7 的关系。
>
> 本轮**不动任何代码**：不改 `predict.py` / `run_predict` /
> `scanner.py` / `prediction_store.py` / `app.py` / `ui/*` /
> `services/regime_features_builder.py` /
> `services/soft_metadata_simulator.py` /
> `services/soft_metadata_injection.py` /
> `services/regime_diagnostics_dashboard.py` /
> `ui/soft_metadata_renderer.py` /
> `ui/soft_metadata_baseline_cache.py` /
> `ui/predict_tab.py` / 任何 builder / DB schema 中的任何一处。

## 1. 当前完成状态

- **Step 2G-3 → 2G-6B.3** 全部进入 main（参见 commit log）
- **Step 2G-6B.2 / 6B.3** enrichment helper + Predict integration（commit
  `de8e2b5`）+ checkpoint（commit `4e60df5`）
- **Step 2G-6B.4 / 6B.5** baseline cache + regime_features source design
  （commit `35b239d`）
- **Step 2G-6B.6 baseline session cache + Step 2G-6B.7 scan_result
  regime_features** 已实现并进入 main —— commit `f00a789` 包含：
  - 新增 `services/regime_features_builder.py`
  - 修改 `scanner.py`（+13 行 try/except + import + 新增字段）
  - 新增 `ui/soft_metadata_baseline_cache.py`
  - 修改 `ui/predict_tab.py`（+11 行 import + try/except + cache 调用）
  - 新增 `tests/test_soft_metadata_baseline_cache.py`（8 个 unittest）
  - 新增 `tests/test_regime_features_from_scan.py`（17 个 unittest）
  - 修改 `tests/test_predict_tab_soft_metadata_display.py`（+2 个测试）
  - 修改 `tasks/step_1_contract_pipeline_summary.md`（新增 §29）
- 本 checkpoint **冻结** Predict 侧 production 链路完整就位的状态 +
  当前限制 + 后续待办，作为 Step 2G-6C Review 接入 / Step 2G-7
  anti-false-exclusion 接入设计的前置文档。

## 2. 当前 main 状态

- **main 最新 commit**：
  `f00a789 feat(ui): add soft metadata baseline cache and scan regime features`
- **测试基线**：**2420 passed / 0 failed / 10 skipped /
  26 warnings / 65 subtests passed**（Step 2G-6B.6/6B.7 起点 2393 →
  2420，+27 净增）
- **本步骤新增 / 修改文件（8）**：
  - 新增 [`services/regime_features_builder.py`](../services/regime_features_builder.py)
  - 修改 [`scanner.py`](../scanner.py)
  - 新增 [`ui/soft_metadata_baseline_cache.py`](../ui/soft_metadata_baseline_cache.py)
  - 修改 [`ui/predict_tab.py`](../ui/predict_tab.py)
  - 新增 [`tests/test_soft_metadata_baseline_cache.py`](../tests/test_soft_metadata_baseline_cache.py)
  - 新增 [`tests/test_regime_features_from_scan.py`](../tests/test_regime_features_from_scan.py)
  - 修改 [`tests/test_predict_tab_soft_metadata_display.py`](../tests/test_predict_tab_soft_metadata_display.py)
  - 修改 [`tasks/step_1_contract_pipeline_summary.md`](step_1_contract_pipeline_summary.md)（新增 §29）
- 未触碰：`predict.py` / `run_predict` / `prediction_store.py` /
  `projection_output_adapter.py` / `projection_output_contract.py` /
  `regime_diagnostics_dashboard.py` / `soft_metadata_simulator.py` /
  `soft_metadata_renderer.py` / `soft_metadata_injection.py` / 任何
  builder / DB schema / 04 / 05 / 07 任何 required 字段 /
  `simulated_trade.no_trade` 策略边界 / 任何其他 `ui/*` 模块。

## 3. Production end-to-end 链路

```
scanner.run_scan(target_date_str, coded_df, peer_codeds, ...)
        │
        ▼  Step 2G-6B.7
        │
build_regime_features(coded_df, peer_codeds, target_date_str)
        │
        ▼  shape: {pos20, avgo_minus_soxx_20d, source, as_of_date,
        │           data_cutoff_date, warnings}
        │
scan_result["regime_features"] = {...}
        │
        ▼  caller: app.py / ui/predict_tab.py
        │
render_predict_tab(scan_result, research_result)
        │
        ▼  Step 2G-6B.6
        │
ensure_soft_metadata_baseline_cached(symbol, session_state=st.session_state)
        │
        ▼  cache hit / lazy build / failure → None (no crash)
        │
baseline = session_state["soft_metadata_baseline"]   # dict | None
        │
        ▼  Step 2G-6B.3
        │
enrich_predict_result_with_soft_metadata(
    predict_result,
    scan_result=scan_result,                          # provides regime_features (4-级 fallback hit)
    baseline=baseline,
)
        │
        ▼  shallow copy + simulator call + canonical write
        │
predict_result["contract_payload"]["exclusion_system"]["extras"]["soft_metadata"]
        │
        ▼  Step 2G-6B
        │
_extract_soft_metadata(enriched) → render_soft_metadata_section(...)
        │
        ▼  Step 2G-6A
        │
render_soft_metadata_card_data(...) → render_soft_metadata_markdown(...)
        │
        ▼
st.markdown(safe_markdown)
        │
        ▼
Predict 页面 Layer 2 ↔ Layer 3 之间显示**完整** R4 / residual card
（含 historical_metrics_in_sample 真实数字，不再是 n/a）
```

说明：
- ✅ 现在**不再只是** display hook（6B），**也不再只是** enrichment
  helper（6B.3）—— baseline + features 两个输入源都已接上
- ✅ Predict 页面在 R4 condition 满足时**真实显示完整 card**：
  `display_label` + `severity` badge + 4 项 metrics（accuracy /
  bias_gap / fer / nb，均为真实数字）+ safety_note + expandable
  details
- ❌ 仍**不写 DB**（baseline cache + features builder + scanner 改动
  全程 SELECT-free / IO-free）
- ❌ 仍**不改** `run_predict` / `predict.py` / `prediction_store.py`
- ❌ 仍**不动** 04 / 05 / 07 任何 required 字段（snapshot 测试锁定
  byte-stable）

## 4. baseline session cache 行为

```python
def ensure_soft_metadata_baseline_cached(
    *, symbol: str = "AVGO", limit: int = 450, session_state: Any = None,
) -> dict | None:
    """Lazy-build + cache soft_metadata_baseline. Never raises."""
```

行为不变量（`tests/test_soft_metadata_baseline_cache.py` 8 个测试锁定）：

| 不变量 | 测试 |
|---|---|
| **cache hit**：`session_state[CACHE_KEY]` 已是 dict → 直接返回 | `test_cache_hit_does_not_call_builder` |
| **cache miss**：调 `build_soft_metadata_baseline(symbol, limit)` 一次 → 写 cache | `test_cache_miss_calls_builder_and_stores_result` |
| **builder 异常**：捕获 → 写 `session_state[ERROR_KEY] = "baseline_build_failed: ..."` → 返回 None | `test_builder_exception_records_error_and_returns_none` |
| **builder 返回非 dict**：不缓存；返回 None | `test_non_dict_builder_return_does_not_cache` |
| **session_state 不可用**（非 Streamlit context）：仍调 builder 一次（无缓存收益但不 crash） | `test_session_state_none_outside_streamlit_does_not_crash` |
| **symbol / limit 透传**给 builder | `test_symbol_and_limit_passed_to_builder` |
| 模块**不**写 DB / 不写文件 / 不接网络 | `IsolationTests` |
| 模块**不** import `prediction_store` / `yfinance` / `requests` / `longbridge` / `broker` / `paper_trade` / `sqlite3` / v1 stub trio | `test_module_does_not_import_forbidden`（`ast.walk` 锁定）|
| **不在 import 时执行**（lazy）| 模块结构保证 |

## 5. regime_features 计算口径

```python
def build_regime_features(
    coded_df, peer_dfs: dict | None, target_date_str: str,
    *, final_test_cutoff: str = "2026-01-01",
) -> dict:
    """Pure function. Returns regime_features dict; never raises."""
```

| 字段 | 计算 | 测试 |
|---|---|---|
| `pos20` | `(Close_D − rolling_low_20) / (rolling_high_20 − rolling_low_20)` | `Pos20Tests`（top of range / insufficient_history / missing_target_date）|
| `avgo_minus_soxx_20d` | `(AVGO 20d return − SOXX 20d return)` (pp) | `SoxxDiffTests`（正常 / 缺 SOXX / 缺 peer_dfs / SOXX 不足）|
| `source` | 固定 `"scan_result"` | `OutputShapeTests::test_required_keys_present` |
| `as_of_date` | `target_date_str[:10]`（YYYY-MM-DD）| 同上 |
| `data_cutoff_date` | == `as_of_date`（**anti-lookahead by construction**）| `test_data_cutoff_date_equals_as_of_date_anti_lookahead` |
| `warnings` | list[str]：`pos20_skipped: <reason>` / `missing_soxx_coded_df` / `soxx_20d_return_unavailable` / `final_test_range_refusal` / `missing_avgo_coded_df` / `missing_as_of_date` 等 | 多个测试 |

不变量（`tests/test_regime_features_from_scan.py` 17 个测试锁定）：

- ✅ **anti-lookahead**：只读 `Date <= target_date` 的行（与
  `scanner._get_nday_return` 同语义）
- ✅ **DataFrame 不被原地修改**（`pd.testing.assert_frame_equal`
  before / after snapshot）
- ✅ **SOXX 缺失 graceful**：`avgo_minus_soxx_20d=None` + warning（不 crash）
- ✅ **历史不足 20 日**：`pos20=None` + `pos20_skipped: insufficient_history`
- ✅ **2026 cutoff 双重锁定**：`as_of_date >= "2026-01-01"` →
  warnings 含 `"final_test_range_refusal"`
- ❌ 模块**不** import `yfinance` / `requests` / `sqlite3` / 网络 / trading
  （`ast.walk` 锁定）

## 6. anti-lookahead / cutoff

| 维度 | 实现 |
|---|---|
| **`data_cutoff_date <= analysis_date`** | `data_cutoff_date == as_of_date == target_date_str[:10]`（by construction） |
| **scanner 只读 ≤ target_date 的行** | `_compute_pos20` 用 `iloc[idx − (window − 1) : idx + 1]`；`_compute_nday_return` 用 `iloc[idx]` 与 `iloc[idx − n]`，n=20；都 ≤ target row index |
| **2026-01-01 final test cutoff 双重防护** | 1) `regime_features_builder` warning：`as_of_date >= "2026-01-01"` → `warnings` 含 `"final_test_range_refusal"`；2) `simulate_soft_metadata` refusal：`analysis_date >= "2026-01-01"` → `signals=[]` + `final_test_range_refusal` warning + renderer 强制 visible 显示 subtitle |
| **不用 2026 final test range 调参** | 整条链路无任何 path 在 `analysis_date >= "2026-01-01"` 时持续生成 / 累积 features 用于训练 / 调参 |

## 7. Predict 接入方式

`render_predict_tab` Layer 2 主结论之后插入：

```python
try:
    _baseline_for_display = ensure_soft_metadata_baseline_cached(
        symbol=str(predict_result.get("symbol", "AVGO")),
        session_state=st.session_state,
    )
except Exception:  # noqa: BLE001
    _baseline_for_display = None

try:
    _enriched_for_display = enrich_predict_result_with_soft_metadata(
        predict_result, scan_result=scan_result,
        research_result=research_result,
        baseline=_baseline_for_display,
    )
except Exception:  # noqa: BLE001 — UI must never crash on metadata
    _enriched_for_display = predict_result

render_soft_metadata_section(_extract_soft_metadata(_enriched_for_display))
```

设计要点：
- **两个 try/except 防御兜底**：
  - cache 失败 → `baseline=None`（metric 显示 n/a 但 R4 仍可触发）
  - enrichment 失败 → 用原 `predict_result`（display 隐藏整个区块）
  - UI **永不崩**
- **baseline 来自 session_state cache**（lazy build；session 内复用）
- **`scan_result` 透传**：helper 4 级 fallback 自动从
  `scan_result["regime_features"]` 命中（scanner.run_scan 已写入）
- ❌ **不**回写 DB
- ❌ **不**改 original `predict_result`：`enriched_for_display` 仅
  用于 display；不替换 `predict_result` 变量本身
- ❌ **不**重新拼安全文案：renderer + display hook 已锁定 16 个
  forbidden words 的零出现

## 8. dev hint 两个根因是否解决

| 之前（Step 2G-6B.3 状态） | 现在（Step 2G-6B.6/6B.7 状态） |
|---|---|
| `baseline=None` → `historical_metrics_in_sample={}` → metric 显示 n/a → renderer visibility 矩阵走 dev hint 分支 → 显示"未触发 metadata（仅有开发者 warning）"| ✅ **baseline session cache 提供 historical_metrics**：cache hit / lazy build；累计 metric 显示真实数字（如 R4: accuracy 32.4% / bias_gap +67.6pp / fer 32.4% / nb +2.2pp）|
| `regime_features=None` → simulator emit `signals=[]` + `missing_regime_features` warning → R4 / residual **不触发** | ✅ **`scanner.run_scan` 提供 `regime_features`**：每次 scan 自动计算 pos20 + avgo_minus_soxx_20d；helper 4 级 fallback 第 4 级直接命中 |

→ **当 features 满足 R4 condition 时**（`avgo_minus_soxx_20d > 5` ∧
`pos20 > 0.62` ∧ `final_direction == "偏多"` ∧ `(confidence_level ==
"high"` ∨ `primary_score_raw > 2)`），Predict 页面**真实显示完整
R4 card**：display_label + severity badge + 4 项真实 metrics + safety_note +
expandable details + hard_forbidden_breakdown。

→ **如果 SOXX 缺失或历史不足**：features builder 仍 graceful warning
（`avgo_minus_soxx_20d=None` 或 `pos20=None`）→ R4 不触发但**不
crash**；renderer 显示 dev hint（明示数据缺失原因）；用户体验仍可
预测，且开发者能从 debug view 看到具体 warning。

## 9. 测试覆盖

| 命令 | 结果 |
|---|---|
| `pytest tests/test_soft_metadata_baseline_cache.py -q` | **8 passed in 0.03s** |
| `pytest tests/test_regime_features_from_scan.py -q` | **17 passed in 0.67s** |
| `pytest tests/test_predict_tab_soft_metadata_display.py tests/test_soft_metadata_injection.py -q` | **57 passed in 0.92s** |
| `pytest tests/test_soft_metadata_simulator.py tests/test_regime_diagnostics_dashboard.py -q` | **69 passed in 0.38s** |
| `pytest -q`（全量） | **2420 passed, 10 skipped, 26 warnings, 65 subtests passed in 10.17s** |

测试覆盖（共 27 个新增）：

| 测试类 / 文件 | 数量 | 内容 |
|---|---|---|
| `CacheBehaviorTests` (`test_soft_metadata_baseline_cache.py`) | 6 | cache miss / hit / builder 异常 / 非 dict / 无 session 不 crash / symbol+limit 透传 |
| `IsolationTests`（同上） | 2 | `ast.walk` 锁定禁 import + `prediction_store` 不调 |
| `Pos20Tests` (`test_regime_features_from_scan.py`) | 3 | top-of-range / insufficient_history / missing_target_date |
| `SoxxDiffTests` | 4 | 正常计算 / 缺 SOXX / 缺 peer_dfs / SOXX 不足 |
| `OutputShapeTests` | 4 | 必填字段 / data_cutoff == as_of / 空 target_date / 缺 coded_df |
| `FinalTestCutoffTests` | 2 | `>=2026` emit refusal / `<2026` 不 emit |
| `IsolationTests`（同上） | 2 | `ast.walk` import 锁定 + DataFrame 不被改 |
| `ScannerIntegrationSmokeTests` | 2 | scanner.run_scan 暴露 regime_features / 失败时 fallback None（用 `importlib.reload(scanner)` 防 fixture 泄漏）|
| `EnrichmentIntegrationTests::test_baseline_cache_helper_importable_from_predict_tab` | 1 | Predict tab import 锁定 |
| `EnrichmentAppTests::test_apptest_predict_result_with_baseline_shows_real_metrics` | 1 | AppTest 验证带 baseline 时显示 32.4% 而非 n/a |

**测试基线累积**：**Step 2G-6B.6/6B.7 起点 2393 → 2420**（+27 净增）；
0 failed；10 skipped 不变。

## 10. Required 字段不变量

| 字段 / 位置 | 行为 |
|---|---|
| 04 `exclusion_system.exclusion_level` | ❌ 不变（继续 `"none"`）|
| 04 `exclusion_system.exclusion_sources` / `exclusion_reasons` / `forced_exclusion` / `anti_false_exclusion_triggered` | ❌ 不变 |
| 04 `exclusion_system.extras.{soft_signal, path_risk_level, ...}` | ❌ 不变（其他 extras key 全部保留）|
| 05 `confidence_system` 4 个 score 字段 + `event_score` / `confidence_level` / `total_confidence` / `confidence_reason` | ❌ 不变 |
| 06 `final_projection.*` 任何字段 | ❌ 不变 |
| 07 `simulated_trade` 6 个决策字段 + `extras.trade_engine_enabled` | ❌ 不变（继续 `no_trade` / `none` / 空 / `0%`）|
| `summary.hard_exclusion_allowed` | ❌ 仍 `False`（renderer + simulator + injection 三重锁定）|
| `hard` / `forced` exclusion | ❌ 仍未启用 |
| `run_predict` 主链 | ❌ 一行未改 |
| `prediction_store` save_prediction 路径 | ❌ 一行未改 |

唯一新增字段：
- `scan_result["regime_features"]` —— scanner 输出的新 informational
  字段，下游 caller 可选消费；不影响现有 scanner 字段（`scan_bias` /
  `scan_confidence` / `notes` / `historical_match_summary` 等全部不变）
- `predict_result["contract_payload"]["exclusion_system"]["extras"]["soft_metadata"]`
  —— enrichment helper 在 shallow-copy 后写入；与所有 required 字段
  硬隔离（已在 Step 2G-6B.2 `RequiredFieldsByteStableTests` 锁定）

## 11. 当前限制

> 本节明确"6B.6/6B.7 完成了什么、还没完成什么"，避免后续 step 误认为
> Step 2G 全部就位。

- **`soft_metadata` 仍不保存进 `prediction_log`**：候选方案 C
  （save-time DB enrichment）已在 Step 2G-6B.1 §6 暂不推荐；Review
  历史 prediction 复盘时**仍需要**重新 enrich（基于当时的 contract
  payload + 当下 baseline / features）
- **Review 页面尚未接入** —— Step 2G-6C 是独立任务；Predict 接入与
  Review 接入对称，但 Review 多了归因维度写入 `review_log` free-text
  的逻辑
- **baseline refresh button 还没做** —— 当前 baseline 是 session 内
  cache，DB 新增 replay / outcome 后**不自动刷新**；用户需重启 app
  / 手动清 session state 才能 refresh；Step 2G-6B.6.1 / 2G-6B.8 可
  做 refresh button + diagnostics 面板（可选优化）
- **如果 SOXX coded_df 缺失** → `avgo_minus_soxx_20d=None` → R4 **不
  触发**（仅 residual 可能仍触发，因为 residual 不依赖 SOXX diff）
- **production 中 baseline build 首次可能稍慢** —— 第一次进入
  Predict 页面时 cache miss 触发 build（SELECT-only，~ms 级），后续
  cache hit 无延迟
- **dashboard 没有单独管理面板** —— Step 2G-6 §4 / §10 设计的两个
  显示位置中，Predict 已就位，Review 未就位；dashboard 上 metadata
  diagnostics（baseline window / metric_computed_at）目前只能从 debug
  expandable view 看
- **anti-false-exclusion 4 个保护层模块全离线** —— Step 2G-7 待启动；
  hard 启用前必须先有保护层（Step 2G 设计文档红线）

这些都是**后续任务**，**不是** Step 2G-6B.6/6B.7 的 bug —— 本步交付
"production 看到完整 R4 card 的最小可行链路"。

## 12. 下一步建议

按推荐优先级：

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **Step 2G-6C Review 页面接入** | `ui/review_tab.py` 调 `enrich_predict_result_with_soft_metadata(..., context="review" 给 renderer)`；归因维度按 Step 2G-6 §8 4 种组合规则写入 `review_log.confidence_note` / `watch_for_next_time` free-text；**不**写 04 / 05 / 07 required；**不**改 review 主流程 | **高**（与 Predict 接入对称；renderer + helper + cache 都已就位）|
| 2 | **Step 2G-6B.8 baseline refresh button / diagnostics**（可选优化） | sidebar 加"刷新 baseline"按钮；dashboard 显示 baseline metrics_window / computed_at；纯 UI 改动；不改 helper / cache | 中（增强 UX，不阻塞 6C）|
| 3 | **Step 2G-7 anti-false-exclusion display / design** | 4 个候选模块（`anti_false_exclusion_audit` / `big_up_contradiction_card` / `big_down_tail_warning` / `exclusion_reliability_review`）挑一个的 dashboard 显示设计；**仍只做设计文档** | 中-低（任何 hard 启用前必须先有保护层；当前 sidecar 不进 04，可延后）|
| 4 | **不推荐**直接做 save-time DB enrichment（候选 C） | 写 DB + migration + 历史一致性问题；当前阶段不必要 | — |
| 5 | **不建议**改 `run_predict` 主链 | 当前链路已能让 dashboard / Review 消费 metadata；改主链没有边际收益 | — |
| 6 | **不建议**启用 `hard` / `forced_exclusion` | 6 项 gate 仍有 4 项 fail | — |

**强制约束**：Step 2G-6C / 2G-7 / 2G-6B.8 实施时仍要遵守：
- 不改 04 / 05 / 07 required 字段
- 不改 `run_predict` 主链
- 不写 DB（除非另立 DB hygiene 任务）
- 不出现 16 个 forbidden words
- 不破坏 `RequiredFieldsByteStableTests` byte-stable 不变量

## 13. 严守边界

- ❌ 没改任何代码（本 checkpoint 是 markdown）
- ❌ 没新增任何测试
- ❌ 没写 DB
- ❌ 没改 DB schema
- ❌ 没改 `run_predict`
- ❌ 没改 `predict.py`
- ❌ 没改 `prediction_store.py`
- ❌ 没改 `projection_output_adapter.py` / `projection_output_contract.py`
- ❌ 没改 `regime_diagnostics_dashboard.py` / `soft_metadata_simulator.py` /
  `soft_metadata_renderer.py` / `soft_metadata_injection.py` /
  `regime_features_builder.py` / `soft_metadata_baseline_cache.py` /
  `predict_tab.py` / `scanner.py`（Step 2G-6B.6/6B.7 已 commit；本
  checkpoint 不改）
- ❌ 没改任何 builder（`_build_exclusion_system` /
  `_build_confidence_system` / `_build_simulated_trade` / 任何其他）
- ❌ 没改 `app.py` / 任何其他 `ui/*` 模块
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
