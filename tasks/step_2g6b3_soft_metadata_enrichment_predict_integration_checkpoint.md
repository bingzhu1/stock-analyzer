# Step 2G-6B.3 — Soft Metadata Enrichment + Predict Integration Checkpoint

> **Checkpoint 文档，不是实现。** 本文档**冻结** Step 2G-6B.2
> enrichment helper + Step 2G-6B.3 Predict integration 的端到端链路、
> helper API、`regime_features` 来源策略、Predict 接入位置、当前
> baseline 状态、required 字段不变量、isolation 锁定、2026 cutoff
> 透传、当前限制与后续待办。
>
> 本轮**不动任何代码**：不改 `predict.py` / `scanner.py` /
> `prediction_store.py` / `app.py` / `ui/*` /
> `soft_metadata_simulator.py` / `regime_diagnostics_dashboard.py` /
> `soft_metadata_renderer.py` / `soft_metadata_injection.py` /
> `predict_tab.py` / 任何 builder / DB schema 中的任何一处。

## 1. 当前完成状态

- **Step 2G-3** soft / hard exclusion re-review（commit `8e837a7`）
- **Step 2G-4** soft metadata layer design（commit `607ccc0`）
- **Step 2G-4.5** schema review（commit `18936f2`）
- **Step 2G-5** read-only sidecar simulator（commit `947f1c9`）+
  checkpoint（commit `b7675b1`）
- **Step 2G-6** dashboard / review display design（commit `0c5f421`）
- **Step 2G-6A** pure-function renderer（commit `373f358`）+
  checkpoint（commit `092a24e`）
- **Step 2G-6B** Predict display hook + Step 2G-6D AppTest（commit
  `33733d3`）+ checkpoint（commit `209a600`）
- **Step 2G-6B.1** injection path design（commit `92441e0`）
- **Step 2G-6B.2** enrichment helper + **Step 2G-6B.3** Predict
  integration 已实现并进入 main —— commit `de8e2b5` 包含：
  - `services/soft_metadata_injection.py`
  - `ui/predict_tab.py` 修改（+13 行 imports + try/except 包裹的 helper 调用）
  - `tests/test_soft_metadata_injection.py`（26 个 unittest）
  - `tests/test_predict_tab_soft_metadata_display.py` 扩展（+7 个测试）
  - `tasks/step_1_contract_pipeline_summary.md` §28
- 本 checkpoint **冻结**端到端链路 + helper / Predict 行为 + 当前限制
  + 后续待办，作为 Step 2G-6B.4 baseline cache / Step 2G-6B.5
  regime_features source / Step 2G-6C Review 接入的前置文档。

## 2. 当前 main 状态

- **main 最新 commit**：
  `de8e2b5 feat(ui): add soft metadata enrichment helper and Predict integration`
- **测试基线**：**2393 passed / 0 failed / 10 skipped /
  26 warnings / 65 subtests passed**（Step 2G-6B.2/6B.3 起点 2360 →
  2393，+33 净增）
- **本步骤新增 / 修改文件（5）**：
  - 新增 [`services/soft_metadata_injection.py`](../services/soft_metadata_injection.py)
  - 修改 [`ui/predict_tab.py`](../ui/predict_tab.py)
  - 新增 [`tests/test_soft_metadata_injection.py`](../tests/test_soft_metadata_injection.py)
  - 修改 [`tests/test_predict_tab_soft_metadata_display.py`](../tests/test_predict_tab_soft_metadata_display.py)
  - 修改 [`tasks/step_1_contract_pipeline_summary.md`](step_1_contract_pipeline_summary.md)
- 未触碰：`predict.py` / `run_predict` / `scanner.py` /
  `prediction_store.py` / `projection_output_adapter.py` /
  `projection_output_contract.py` / `regime_diagnostics_dashboard.py` /
  `soft_metadata_simulator.py` / `soft_metadata_renderer.py` / 任何
  builder / DB schema / 04 / 05 / 07 任何 required 字段 /
  `simulated_trade.no_trade` 策略边界 / 任何其他 `ui/*` 模块。

## 3. 端到端链路

```
caller (UI / future scanner / future run_predict caller)
        │
        ▼  regime_features (pos20 + avgo_minus_soxx_20d)
        │
enrich_predict_result_with_soft_metadata(
    predict_result, *, scan_result, baseline,
    regime_features, analysis_date, force, final_test_cutoff)
        │
        ▼  shallow-copy + canonical write
        │
predict_result["contract_payload"]["exclusion_system"]
                                  ["extras"]["soft_metadata"]
        │
        ▼  Step 2G-6B 三级查找
        │
_extract_soft_metadata(enriched_result)
        │
        ▼
render_soft_metadata_section(soft_metadata)
        │
        ▼  Step 2G-6A renderer
        │
render_soft_metadata_card_data(...) → render_soft_metadata_markdown(...)
        │
        ▼
st.markdown(safe_markdown)
        │
        ▼
Predict 页面 Layer 2 主结论与 Layer 3 证据区之间显示安全卡片
```

解释：
- ✅ canonical 位置**真正会被填充**（之前 6B 完成时 99% 时间下隐藏）
- ✅ Predict 页面**不再只是 passive hook**：上游有 `regime_features`
  就会立即出现 R4 / residual card；没有则按 visibility 矩阵显示 dev
  hint 或隐藏
- ❌ 仍然**不写 DB**（helper / Predict hook 全程 SELECT-free）
- ❌ 仍然**不改** `run_predict` / `predict.py` / `scanner.py` /
  `prediction_store.py`
- ❌ 仍然**不动** 04 / 05 / 07 任何 required 字段（snapshot 测试锁定
  byte-stable）

## 4. Enrichment helper API

```python
def enrich_predict_result_with_soft_metadata(
    predict_result: dict,
    *,
    scan_result: dict | None = None,
    research_result: dict | None = None,    # API stability; not used in v1
    baseline: dict | None = None,
    regime_features: dict | None = None,
    analysis_date: str | None = None,
    force: bool = False,
    final_test_cutoff: str = "2026-01-01",
) -> dict:
    """Pure function. Returns shallow copy with canonical
    exclusion_system.extras.soft_metadata filled. Never raises.
    Never reads DB / CSV / network. Never calls
    build_soft_metadata_baseline."""
```

行为不变量（`tests/test_soft_metadata_injection.py` 26 个测试锁定）：

| 不变量 | 测试 |
|---|---|
| shallow copy；不原地修改 input | `InputImmutabilityTests::test_input_predict_result_is_not_mutated`（deepcopy snapshot）|
| 返回 dict 与 input 不同对象（顶层 + contract_payload + exclusion_system 三层都重新引用）| `test_returned_dict_is_distinct_from_input` |
| canonical 位置写入 | `CanonicalWriteTests::test_canonical_slot_filled_after_enrichment` |
| already-set 默认不覆盖 | `test_existing_canonical_not_overwritten_by_default` |
| `force=True` 才覆盖 | `test_force_true_overwrites_existing` |
| 缺 contract_payload / extras 安全创建（不污染 input）| `test_missing_contract_payload_creates_layers_safely` / `test_missing_extras_creates_extras_dict` |
| 不写 DB / 不调 `prediction_store` | `IsolationTests::test_does_not_call_prediction_store` |
| 不调 `build_soft_metadata_baseline` | `test_does_not_call_build_soft_metadata_baseline` |
| 只调 `simulate_soft_metadata` | 整体集成 + simulator passthrough 测试 |

## 5. regime_features 来源

`_extract_regime_features(predict_result, scan_result)` 4 级 fallback；
显式 `regime_features=` kwarg 在 helper 主入口处优先（不进 fallback
链）：

| # | 来源 | 测试 |
|---|---|---|
| 1 | `regime_features=` kwarg（显式）| `test_explicit_kwarg_wins_over_predict_result` |
| 2 | `predict_result["regime_features"]` | `test_predict_result_top_level_fallback` |
| 3 | `predict_result["contract_payload"]["exclusion_system"]["extras"]["regime_features"]` | `test_contract_extras_regime_features_fallback` |
| 4 | `scan_result["regime_features"]` | `test_scan_result_regime_features_fallback` |
| 5 | `scan_result["extras"]["regime_features"]` | `test_scan_result_extras_regime_features_fallback` |
| 6 | None | `test_no_features_anywhere_yields_empty_signals_with_warning` |

如果**全部**为 None：
- 不 crash（合约保证）
- simulator 收到 `regime_features=None` → emit `signals=[]` +
  `missing_regime_features` warning
- Predict 页面按 renderer visibility 矩阵显示 **dev hint**（不显示
  R4 card），**不**误导成 metadata 已运行

## 6. Predict 接入方式

`render_predict_tab(scan_result, research_result)` Layer 2 主结论后、
display hook 前：

```python
try:
    _enriched_for_display = enrich_predict_result_with_soft_metadata(
        predict_result,
        scan_result=scan_result,
        research_result=research_result,
        baseline=st.session_state.get("soft_metadata_baseline"),
    )
except Exception:  # noqa: BLE001 — UI must never crash on metadata
    _enriched_for_display = predict_result
render_soft_metadata_section(_extract_soft_metadata(_enriched_for_display))
```

设计要点：
- **try/except 防御性兜底**：helper 合约保证不 raise，但 UI 双保险，
  metadata 路径任何意外都不会让主页面崩
- **`baseline` 从 session_state 读**：caller 可在 `app.py` 启动时
  预先 build baseline 缓存到 `session_state["soft_metadata_baseline"]`；
  当前未做缓存（详见 §7）
- **`scan_result` / `research_result` 透传**：让 helper 的
  `_extract_regime_features` 4 级 fallback 第 4-5 级有数据可查
- ❌ **不回写** session_state（除 caller 预设的 baseline 缓存位置；
  helper 自身不写）
- ❌ **不保存 DB**（不调 `save_prediction` / `_get_conn`）
- ❌ **不改 original `predict_result`**：`enriched_for_display` 仅
  用于 display；不替换 `predict_result` 变量本身
- ❌ **不重新拼文案**：renderer + display hook 已锁定 16 个 forbidden
  words 的零出现

## 7. baseline 当前状态

- **没有全局缓存**：`app.py` 启动时**未**调用
  `build_soft_metadata_baseline()`，所以 `session_state["soft_metadata_baseline"]`
  始终为 `None`
- Predict 接入从 `session_state` 读 baseline → 当前永远拿到 `None`
- **如果没有 baseline**：
  - simulator 仍运行（`regime_features` 触发逻辑独立于 baseline）
  - signals 仍可触发（R4 / residual condition 不依赖 baseline；
    historical_metrics 才依赖）
  - `historical_metrics_in_sample` 为 `{}`（accuracy / bias_gap /
    false_exclusion_rate / net_benefit 全部 metric 缺失，UI 显示 `n/a`）
  - `summary.warnings` 含 `missing_baseline`
  - renderer visibility 矩阵走 "predict + warnings (other than refusal)"
    分支 → **显示 dev hint** "未触发 metadata（仅有开发者 warning）"
- **这是当前 production 注意事项，不是 bug**：dev hint 是设计行为
  （Step 2G-6 §7 / renderer visibility 矩阵）；只是用户体验上 dev
  hint 会出现在每次预测的 Predict 页面上
- **后续**：Step 2G-6B.4 应设计 baseline cache 策略，让 `app.py`
  启动时 / 用户切换日期时刷新 baseline；消除 dev hint

## 8. 测试覆盖

| 命令 | 结果 |
|---|---|
| `pytest tests/test_soft_metadata_injection.py -q` | **26 passed in 0.04s** |
| `pytest tests/test_predict_tab_soft_metadata_display.py tests/test_soft_metadata_renderer.py -q` | **65 passed in 1.13s** |
| `pytest tests/test_soft_metadata_simulator.py tests/test_regime_diagnostics_dashboard.py -q` | **69 passed in 0.39s** |
| `pytest -q`（全量） | **2393 passed, 10 skipped, 26 warnings, 65 subtests passed in 10.11s** |

测试类（共 33 个新增）：

| 测试类（文件） | 数量 | 内容 |
|---|---|---|
| `InputImmutabilityTests` (`test_soft_metadata_injection.py`) | 3 | input deepcopy snapshot 不变 / 返回 dict 与 input 不同对象 / 非 dict 输入 → `{}` |
| `CanonicalWriteTests` | 5 | canonical 填充 / already-set 不覆盖 / `force=True` 覆盖 / 缺 contract_payload 安全创建 / 缺 extras 安全创建 |
| `RequiredFieldsByteStableTests` | 3 | 04 required + 05 confidence + scores + 07 simulated_trade + 06 final_projection 全 byte-stable；`force=True` 也不动 required |
| `SimulatorPassthroughTests` | 5 | baseline / analysis_date / override 优先 / 2026 refusal warning / final_test_cutoff 五项透传 |
| `RegimeFeaturesExtractionTests` | 7 | explicit kwarg 优先 + 5 级 fallback + None 不 crash + `_extract_regime_features` 直接单元测试 |
| `IsolationTests` | 3 | 不调 `build_soft_metadata_baseline` / 不调 `prediction_store` / `ast.walk` import 锁定 |
| `EnrichmentIntegrationTests` (`test_predict_tab_soft_metadata_display.py`) | 5 | helper 从 predict_tab 可 import / canonical 触发 R4 显示 / fallback 不崩 / no forbidden words / 2026 refusal subtitle 可见 |
| `EnrichmentAppTests`（Streamlit AppTest） | 2 | with features → 页面真实显示 R4 card；without features → dev hint 可见但 R4 card 不出现 |

测试基线累积：**Step 2G-6B.2/6B.3 起点 2360 → 2393**（+33 净增）；
0 failed；10 skipped 不变。

## 9. AppTest 覆盖

`EnrichmentAppTests` 用 `streamlit.testing.v1.AppTest.from_string`
构造最小脚本（直接走 enrichment + display 集成路径）：

| # | 测试 | 期望 |
|---|---|---|
| 9.1 | `test_apptest_predict_result_with_features_displays_r4_card` | 页面文本含 `"高位跑赢同行后的偏多过热"` + `"不改变主推演方向"`；**不含** 16 个 forbidden words |
| 9.2 | `test_apptest_predict_result_without_features_shows_dev_hint_no_card` | 页面文本含 `"未触发 metadata"`（dev hint 可见）；**不含** `"高位跑赢同行后的偏多过热"`（R4 card 不出现）；**不含** 16 个 forbidden words |

加上 Step 2G-6B 已有的 4 个 `PredictTabAppTests`：display hook 单独
测试（R4 / empty / final_test_refusal / None）—— **总计 6 个 AppTest
集成测试**覆盖 Predict 页面 metadata 显示路径。

## 10. Required 字段不变量

`RequiredFieldsByteStableTests`（结构化 subset 比较 input vs output
byte-by-byte）锁定：

| 字段 / 位置 | 行为 |
|---|---|
| 04 `exclusion_system.exclusion_level` | ❌ 不变（继续 `"none"`）|
| 04 `exclusion_system.exclusion_sources` / `exclusion_reasons` | ❌ 不变（继续 `[]`）|
| 04 `exclusion_system.forced_exclusion` | ❌ 不变（继续 `False`）|
| 04 `exclusion_system.anti_false_exclusion_triggered` | ❌ 不变（继续 `False`）|
| 04 `exclusion_system.extras.soft_signal` / `path_risk_level` / `peer_path_risk_*` / `conflicting_factors_*` | ❌ 不变（其他 extras key 全部保留）|
| 05 `confidence_system` 4 个 score 字段 + `event_score` | ❌ 不变（继续 0.0 / None）|
| 05 `confidence_level` / `total_confidence` / `confidence_reason` | ❌ 不变（仍来自原 contract payload）|
| 06 `final_projection.*` 任何字段 | ❌ 不变 |
| 07 `simulated_trade` 6 个决策字段 + `extras.trade_engine_enabled` | ❌ 不变（继续 `no_trade` / `none` / 空 / `0%`）|
| `summary.hard_exclusion_allowed` | ❌ 仍 `False`（renderer + simulator 双重锁定）|
| `hard` / `forced` exclusion | ❌ 仍未启用 |

helper 唯一**写入**位置：
`out["contract_payload"]["exclusion_system"]["extras"]["soft_metadata"]`
—— 与所有 required 字段硬隔离。

## 11. Isolation / no side effects

helper + Predict integration 测试锁定：

- ❌ **不调用** `services.prediction_store.save_prediction` / `_get_conn`
  （helper 与 Predict integration 双重 patch 锁定）
- ❌ **不调用** `services.soft_metadata_simulator.build_soft_metadata_baseline`
  （helper patch 锁定 not_called）
- ❌ **不写 DB**（无 `init_db` / `INSERT` / `UPDATE` / `DELETE` 路径）
- ❌ helper 模块**不 import** `yfinance` / `requests` / `longbridge` /
  `broker` / `paper_trade` / `sqlite3` / `services.prediction_store` /
  `services.regime_diagnostics_dashboard` / `services.confidence_engine`
  / `services.contradiction_engine` / `services.risk_model`
  （`ast.walk` parse 锁定）
- ❌ Predict integration 模块（`ui/predict_tab.py`）**不** import
  `services.soft_metadata_simulator` 直接（Step 2G-6B 锁定继续保持）
- ❌ **不处理** logs / backups / stash / `.claude/worktrees/`
- ❌ **不接** trading API / `longbridge` / `broker` / `paper_trade`
- ❌ **不接** `yfinance` / `requests` / 任何网络

## 12. 2026 final test cutoff

- helper 默认从
  `predict_result["contract_payload"]["current_structure"]["analysis_date"]`
  提取 `analysis_date`；显式 override 优先
- `analysis_date` **必传**给 `simulate_soft_metadata`（Step 2G-6B.1
  §15 强约束）
- `analysis_date >= "2026-01-01"`（默认 cutoff）触发：
  - simulator emit `signals=[]` + `summary.warnings` 含
    `"final_test_range_refusal"`
  - renderer visibility 矩阵强制 `visible=True`
  - Predict 页面**不被隐藏**，显示 subtitle："本预测进入 final test
    保留区间，soft_metadata 已暂停（防止参数污染）"
- 测试 `SimulatorPassthroughTests::test_2026_analysis_date_emits_refusal_warning`
  + `EnrichmentIntegrationTests::test_enrichment_2026_analysis_date_keeps_section_visible_with_refusal`
  双重锁定
- **不**使用 2026-01-01 之后 final test 数据调参 / 反复跑
- 2026-01-01 之后仍是**整个系统**完成后的最终测试集

## 13. 当前限制

> 本节明确"6B.3 完成了什么、还没完成什么"，避免后续 step 误认为
> Predict 页面已经全自动显示 R4。

- **上游 scanner / `run_predict` 还没有标准产出 `regime_features`**：
  `scanner.py` 当前**不**自动计算 `pos20` / `avgo_minus_soxx_20d` 暴露
  到 `scan_result`；`run_predict` 主链未改 → caller 不传
  `regime_features` 时，4 级 fallback 链全空 → R4 / residual **不会
  触发**
- **如果 caller 不传 `regime_features`，R4 不会触发** —— 当前 Predict
  页面在生产中实际看到的是 dev hint（"未触发 metadata（仅有开发者
  warning）"），而不是 R4 card
- **baseline cache 尚未设计**：`app.py` 启动时未 build baseline；
  即使未来上游开始提供 `regime_features`，`historical_metrics_in_sample`
  仍会缺失（n/a 显示）
- **Review 页面尚未接入** —— Step 2G-6C 是独立任务
- **`soft_metadata` 尚未保存进 `prediction_log`** —— 候选方案 C
  （save-time enrichment）已在 Step 2G-6B.1 §6 暂不推荐；要做需
  独立立项 + DB hygiene 评估
- **dashboard 没有单独管理面板** —— Step 2G-6 §4 设计的两个显示位置
  中，Predict 已就位但 baseline 缺失，Review 尚未接入

这些都是**后续任务**，**不是** Step 2G-6B.3 的 bug —— 本步交付了
"end-to-end 链路 + 安全测试 + Predict 接入"，让上游 / Review / baseline
策略可以在不改 UI / 不改 helper 的前提下后续填补。

## 14. 下一步建议

按推荐优先级：

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **Step 2G-6B.4 baseline cache design** | 设计 `app.py` / `session_state` 如何缓存 `soft_metadata_baseline`；何时刷新（启动时？日期切换时？手动按钮？）；TTL 策略；失败时的降级行为；纯文档 | **高**（消除 production 中每次预测都出现的 dev hint；当前最痛点）|
| 2 | **Step 2G-6B.5 regime_features source design** | 决定 `pos20` / `avgo_minus_soxx_20d` 从哪里来：(a) 扩展 `scanner.py` 自动计算；(b) UI / app.py 在 `run_predict` 之后用 `regime_diagnostics_dashboard._compute_pos20` / `_compute_nday_return` 算一次；(c) 完全 caller-controlled；纯文档 | **高**（即使 baseline cache 就位，没 features 也看不到 R4；与 #1 同 step 完成可一次解决"看不到 R4"问题）|
| 3 | **Step 2G-6C Review 页面接入** | 在 `ui/review_tab.py` 调用 helper + renderer，`context="review"`；归因维度按 Step 2G-6 §8 4 种组合规则写入 `review_log.confidence_note` / `watch_for_next_time` free-text 字段；**不**写 04 / 05 / 07 required；**不**改 review 主流程 | 中（与 Predict 接入对称；可在 #1 / #2 完成后做）|
| 4 | **不推荐**直接做 save-time DB enrichment（候选方案 C）| 写 DB + migration + 历史一致性问题；当前阶段不必要 | — |
| 5 | **不建议**改 `run_predict` / `predict.py` | helper + Predict integration 已能满足显示需求；改主链没有边际收益且可能回归 | — |
| 6 | **不建议**启用 `hard` / `forced_exclusion` | 6 项 gate 仍有 4 项 fail | — |

**强制约束**：Step 2G-6B.4 / 6B.5 / 6C 实施时仍要遵守：
- 不改 04 / 05 / 07 required 字段
- 不改 `run_predict` 主链
- 不写 DB（除非另立 DB hygiene 任务）
- 不出现 16 个 forbidden words

## 15. 严守边界

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
  `predict_tab.py`（Step 2G-6B.2/6B.3 已 commit；本 checkpoint 不改）
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
