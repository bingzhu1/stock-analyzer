# Step 2G-6B — Predict Soft Metadata Display Hook Checkpoint

> **Checkpoint 文档，不是实现。** 本文档**冻结** Step 2G-6B Predict
> 页面接入的位置、`soft_metadata` 来源策略、渲染策略、文案安全锁定、
> 测试覆盖、AppTest 集成、isolation 不变量、与 Step 2G-6C / 注入路径
> / 04 / 05 / 07 required 字段的关系。
>
> 本轮**不动任何代码**：不改 `predict.py` / `scanner.py` /
> `prediction_store.py` / `app.py` / `ui/*` / `soft_metadata_simulator.py` /
> `regime_diagnostics_dashboard.py` / `soft_metadata_renderer.py` /
> 任何 builder / DB schema 中的任何一处。

## 1. 当前完成状态

- **Step 2G-3** soft / hard exclusion re-review 完成（commit `8e837a7`）
- **Step 2G-4** soft metadata layer design 完成（commit `607ccc0`）
- **Step 2G-4.5** schema review 完成（commit `18936f2`）
- **Step 2G-5** read-only sidecar simulator 完成（commit `947f1c9`）+
  checkpoint（commit `b7675b1`）
- **Step 2G-6** dashboard / review display design 完成（commit `0c5f421`）
- **Step 2G-6A** pure-function renderer 完成（commit `373f358`）+
  checkpoint（commit `092a24e`）
- **Step 2G-6B** Predict 页面接入 + Step 2G-6D UI safety tests 已
  实现并进入 main —— commit `33733d3` 包含：
  - `ui/predict_tab.py` 修改（+~80 行）
  - `tests/test_predict_tab_soft_metadata_display.py`（22 个 unittest，
    含 4 个 AppTest 集成）
  - `tasks/step_1_contract_pipeline_summary.md` §27
- 本 checkpoint **冻结** Predict 接入位置、来源策略、测试覆盖、
  与 Step 2G-6C 接入的关系，作为后续 Review 接入 + 注入路径设计的
  前置文档。

## 2. 当前 main 状态

- **main 最新 commit**：
  `33733d3 feat(ui): add soft metadata display hook to Predict tab`
- **测试基线**：**2360 passed / 0 failed / 10 skipped /
  26 warnings / 65 subtests passed**（Step 2G-6B 起点 2338 → 2360，
  +22 净增）
- **本步骤新增 / 修改文件（3）**：
  - 修改 [`ui/predict_tab.py`](../ui/predict_tab.py)
  - 新增 [`tests/test_predict_tab_soft_metadata_display.py`](../tests/test_predict_tab_soft_metadata_display.py)
  - 修改 [`tasks/step_1_contract_pipeline_summary.md`](step_1_contract_pipeline_summary.md)（新增 §27）
- 未触碰：`predict.py` / `run_predict` / `scanner.py` /
  `prediction_store.py` / `projection_output_adapter.py` /
  `projection_output_contract.py` / `regime_diagnostics_dashboard.py` /
  `soft_metadata_simulator.py` / `soft_metadata_renderer.py` / 任何
  builder / DB schema / 04 / 05 / 07 任何 required 字段 /
  `simulated_trade.no_trade` 策略边界 / 任何其他 `ui/*` 模块。

## 3. 接入位置

`render_predict_tab(scan_result, research_result)` 当前结构：

```
1. Layer 1 当前上下文      _render_layer1_context(...)
2. Divider                  st.divider()
3. Layer 2 主结论          _render_layer2_conclusion(predict_result, scan_result)
4. ✦ Soft metadata hook    render_soft_metadata_section(_extract_soft_metadata(predict_result))   ← 本步新增
5. Divider                  st.divider()
6. Layer 3 证据区          _render_layer3_evidence(...)
7. Divider                  st.divider()
8. Layer 4 闭环操作区      _render_layer4_operations(...)
```

**为什么放在这里**：

- 在 **Layer 2 主结论之后**：让用户先看完 `final_projection` 的方向
  / five_state / probability_bucket，再看 metadata 的"过热提示" ——
  避免 metadata 抢主推演的视觉焦点
- 在 **Layer 3 证据区之前**：让 metadata 与主结论视觉相邻，强化
  "metadata 描述的是主推演的结构性风险"这一关系
- **不混入 simulated_trade / 07 段**：本项目永不渲染 simulated_trade
  独立区块（07 段策略边界 pinned），所以选择"主结论 ↔ metadata ↔
  证据区"序列；与 Step 2G-6 §4.1 设计文档一致

## 4. soft_metadata 来源策略

`_extract_soft_metadata(predict_result)` 按以下顺序查找；**任何位置
都没有 → 返回 `None`，renderer 在 predict context 下隐藏整个区块**：

| # | 位置 | 用途 |
|---|---|---|
| 1 | `predict_result["contract_payload"]["exclusion_system"]["extras"]["soft_metadata"]` | **canonical** 路径；未来 pipeline / adapter 写入时使用 |
| 2 | `predict_result["soft_metadata"]` | top-level fallback；caller 直接注入到 `predict_result` |
| 3 | `st.session_state["soft_metadata_for_predict"]` | 测试 / 开发注入；`session_state.get` 异常时 graceful 返回 None |

### 4.1 强约束

- **本轮不生成** `soft_metadata` —— `run_predict` 主链未改；当前
  没有任何代码路径会自动填充 canonical 位置
- **不调用 simulator** —— 显示函数永远不调用
  `services.soft_metadata_simulator.simulate_soft_metadata` 或
  `build_soft_metadata_baseline`（测试 `IsolationTests` 锁定）
- **不读 DB** —— 显示函数永远不调用 `services.prediction_store.*`
  （测试锁定）
- **不接网络** —— 显示函数永远不接 `yfinance` / `requests` /
  trading API（renderer 已锁定 + Predict tab module 未 import simulator）
- **未来注入路径**：另立 Step 2G-6B.1（建议）—— 决定 soft_metadata
  何时由 simulator 生成并放入 `contract_payload.exclusion_system.extras`；
  仍不改 04 / 05 / 07 required 字段

## 5. 渲染策略

`render_soft_metadata_section(soft_metadata)` 是 thin wrapper：

```python
def render_soft_metadata_section(soft_metadata: dict | None) -> dict:
    payload = soft_metadata if isinstance(soft_metadata, dict) else {}
    card_data = render_soft_metadata_card_data(payload, context="predict")
    if not card_data.get("visible"):
        return card_data
    markdown = render_soft_metadata_markdown(card_data)
    if markdown:
        st.markdown(markdown)
    return card_data
```

**职责边界**：

- ✅ 调用 `render_soft_metadata_card_data` + `render_soft_metadata_markdown`
- ✅ 用 `st.markdown` 输出 renderer 生成的 markdown
- ✅ 返回 `card_data` dict 供测试断言
- ❌ **不**自己拼安全文案（renderer 已生成 markdown 文本）
- ❌ **不**重新解释 severity（直接用 renderer 的 `badge_text` /
  `badge_tone`）
- ❌ **不**重新实现 dedup（renderer 已按 `dedup_group` 处理）
- ❌ **不**改 renderer 输出（如截断 / 添加标签 / 修改 metrics）
- ❌ **不**调用 renderer 之外的任何 `ui.soft_metadata_renderer` API

## 6. 文案安全

### 6.1 16 个 forbidden words 仍由 renderer 测试锁定

renderer 模块（`ui/soft_metadata_renderer.py`）的 `FORBIDDEN_COPY_TOKENS`
模块级常量包含 16 个词；renderer 的
`tests/test_soft_metadata_renderer.py` 在 6 个典型场景 grep 锁定
（Step 2G-6A checkpoint §6 已固化）。

### 6.2 Predict 页面 AppTest 也验证页面文本不含 forbidden words

`tests/test_predict_tab_soft_metadata_display.py` 的
`PredictTabAppTests::test_apptest_r4_card_renders_safe_markdown` +
`test_apptest_final_test_refusal_visible` 两个测试在跑 AppTest 之后
对 `at.markdown` 集合 grep 全部 16 个 forbidden words —— **双重
锁定**（renderer 已禁 + Predict 页面也禁）。

### 6.3 16 个 forbidden words

页面**不出现**：
- 禁止交易 / 强制否定 / 必须不做
- hard exclusion / forced exclusion
- 自动拦截
- no_trade
- 卖出信号 / 做空信号 / 看空信号
- 否决主推演 / 推翻主推演
- 强制平仓 / force close
- 阻止下单 / block order

### 6.4 页面必须保持的安全文案

每张 card 通过 renderer 的 `safety_note` 强制三件套：
- "不改变主推演方向"
- "不构成交易指令"
- "07 段策略边界（不交易）不变"

## 7. 测试覆盖

| 命令 | 结果 |
|---|---|
| `pytest tests/test_predict_tab_soft_metadata_display.py -q` | **22 passed in 1.09s** |
| `pytest tests/test_soft_metadata_renderer.py tests/test_predict_tab_soft_metadata_display.py -q` | **58 passed in 0.84s** |
| `pytest tests/test_soft_metadata_simulator.py tests/test_regime_diagnostics_dashboard.py -q` | **69 passed in 0.37s** |
| `pytest -q`（全量） | **2360 passed, 10 skipped, 26 warnings, 65 subtests passed in 9.92s** |

测试类覆盖：

| 类 | 数量 | 内容 |
|---|---|---|
| `ExtractSoftMetadataTests` | 6 | `_extract_soft_metadata` 三级查找：None / 非 dict / canonical / top-level fallback / canonical 优先 / malformed extras / Streamlit context 缺失 graceful |
| `RenderSectionUnitTests` | 6 | None / 空 signals / 非 dict 不调 markdown；R4 调 markdown 含安全文案；final_test_refusal 调 markdown 含 subtitle；6 场景 grep 16 个禁止词 |
| `IsolationTests` | 3 | 不调 simulator (`simulate_soft_metadata` / `build_soft_metadata_baseline`)；不调 `prediction_store.save_prediction` / `_get_conn`；模块 `ast.walk` import 不含 simulator |
| `HardExclusionSafetyTests` | 2 | hard_exclusion_allowed=false 不渲染 hard / forced / no_trade；unknown signal graceful + "未识别" 文案 |
| `PredictTabAppTests`（AppTest） | 4 | R4 / empty / final_test_refusal / None 四个集成场景 |

测试基线累积：**Step 2G-6B 起点 2338 → 2360**（+22 净增）；
0 failed；10 skipped 不变。

## 8. AppTest 覆盖

`PredictTabAppTests` 4 项（用 `streamlit.testing.v1.AppTest.from_string`
注入 fixture soft_metadata，跑 `at.run()` 后断言 `at.markdown`）：

| # | 测试 | 期望 |
|---|---|---|
| 8.1 | `test_apptest_r4_card_renders_safe_markdown` | 页面文本含 `"高位跑赢同行后的偏多过热"` + `"不改变主推演方向"` + `"32.4%"`；**不含** 16 个 forbidden words |
| 8.2 | `test_apptest_empty_signals_hides_card` | predict context 隐藏：页面文本**不含** `"结构性偏多风险提示"`、**不含** `"未触发 soft metadata"` |
| 8.3 | `test_apptest_final_test_refusal_visible` | 页面文本含 `"final test 保留区间"`（不被隐藏）；**不含** 16 个 forbidden words |
| 8.4 | `test_apptest_none_input_renders_nothing` | None 输入 → 页面 markdown 集合**完全为空** |

**AppTest 已就位**，无需等待独立的 Step 2G-6D-2。

## 9. Isolation / no side effects

测试锁定：

- **不调用** `services.soft_metadata_simulator.simulate_soft_metadata`
  （`patch` + `assert_not_called`）
- **不调用** `services.soft_metadata_simulator.build_soft_metadata_baseline`
  （同上）
- **不调用** `services.prediction_store.save_prediction`（同上）
- **不调用** `services.prediction_store._get_conn`（同上）
- `ui/predict_tab.py` 模块 **不 import** `services.soft_metadata_simulator`
  /  `soft_metadata_simulator`（`ast.walk` parse 锁定）
- **不写 DB**（无 `init_db` / `INSERT` / `UPDATE` / `DELETE` 路径）
- **不改主链**（`predict.py` / `run_predict` / 任何 builder 一行未动）
- **不接网络**（renderer 已锁定 + Predict tab 未引入新网络依赖）
- **不接 trading API**（renderer 已锁定 + Predict tab 未引入新 trading
  依赖）

## 10. 与 04 / 05 / 07 required 字段关系

| 字段 / 位置 | display hook 行为 |
|---|---|
| 04 `exclusion_system.exclusion_level` | ❌ 不读、不写（继续 `"none"`）|
| 04 `exclusion_system.exclusion_sources` / `exclusion_reasons` | ❌ 不读、不写（继续 `[]`）|
| 04 `exclusion_system.forced_exclusion` | ❌ 不读、不写（继续 `False`）|
| 04 `exclusion_system.anti_false_exclusion_triggered` | ❌ 不读、不写（继续 `False`）|
| 04 `exclusion_system.extras.soft_metadata` | ✅ 仅读取（canonical 来源；不写）|
| 05 `confidence_system` 4 个 score 字段 + `event_score` | ❌ 不读、不写 |
| 05 `confidence_level` / `total_confidence` / `confidence_reason` | ❌ 不读、不写 |
| 07 `simulated_trade` 6 个决策字段 + `extras.trade_engine_enabled` | ❌ 不读、不写（继续策略边界值）|
| `final_projection.*` 任何字段 | ❌ 不读、不写 |

display hook 是 sidecar / extras-only：**仅**读取
`extras.soft_metadata` / `predict_result.soft_metadata` /
`session_state.soft_metadata_for_predict`，从不修改任何 contract
required 字段。

## 11. 2026 final test cutoff

- Predict display hook **不**访问 2026 数据 —— 不接 DB / CSV /
  网络，因此**不可能**读到 2026-01-01 之后的数据
- `summary.warnings` 含 `"final_test_range_refusal"` 时（输入
  `analysis_date >= "2026-01-01"` 由 simulator 生成的 sidecar），
  Predict 页面**强制可见**显示 subtitle："本预测进入 final test
  保留区间，soft_metadata 已暂停（防止参数污染）"
- 测试 `RenderSectionUnitTests::test_final_test_refusal_visible_and_displays_subtitle`
  + `PredictTabAppTests::test_apptest_final_test_refusal_visible`
  双重锁定
- 继续遵守 2026-01-01 之后为最终测试集；display hook 不参与任何
  调参 / 反复跑

## 12. 当前限制

> 本节明确"6B 完成了什么、还没完成什么"，避免后续 step 误认为
> Predict 页面已经全自动显示 metadata。

- **页面只有在 `soft_metadata` 已存在时才显示** —— 三级查找位置
  全部为空时，整个 metadata 区块隐藏
- **当前 `run_predict` 不生成 `soft_metadata`** —— 主链未改；canonical
  位置 `contract_payload.exclusion_system.extras.soft_metadata` 在
  现有 prediction 中**几乎从不**出现（旧 prediction 不含；新
  prediction 也不含）
- **当前 `prediction_store` 不保存新 metadata** —— `save_prediction`
  侧边路径 + adapter 仍按 Step 2C-2 的 5-字段 stub 写 04 段，
  不写 `soft_metadata`
- **当前 Review 页面还未接入** —— Step 2G-6C 是独立任务
- **当前 dashboard 没有单独管理面板** —— Step 2G-6 §4.1 / §4.2 设计
  的两个显示位置中，Predict 已就位，Review 未就位
- **未来注入路径未定** —— soft_metadata 何时 / 由谁 / 在哪里调用
  simulator 并填入 canonical 位置，留给独立的 Step 2G-6B.1

这些都是后续任务，**不属于** Step 2G-6B 的范围；本步只交付"显示
能力 + 安全测试"，让接入路径可以在不改 UI 的前提下后续填补。

## 13. 下一步建议

按推荐优先级：

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **Step 2G-6C Review 页面接入** | 在 `ui/review_tab.py` 调用 renderer，传 `context="review"`；归因维度按 Step 2G-6 §8 4 种组合规则写入 `review_log.confidence_note` / `watch_for_next_time` free-text 字段；**不**写 04 / 05 / 07 required；**不**改 review 主流程 | **高**（与 Predict 接入对称；renderer + display 模式已就位） |
| 2 | **Step 2G-6B.1 注入路径设计** | 设计 `soft_metadata` 何时由 simulator 生成并放入 `contract_payload.exclusion_system.extras`；纯文档；候选方案：(a) `prediction_store.save_prediction` 旁路；(b) `app.py` predict 流程结尾计算；(c) 离线 batch 写入；(d) 完全 caller-controlled 仅在 dashboard 主动请求时算 | 高（Predict 接入已就位但 canonical 位置永远空 → 用户看不到任何 metadata；注入路径决策不能拖太久）|
| 3 | **Step 2G-7** anti-false-exclusion 接入设计 | 4 个候选模块挑一个的 dashboard 显示设计；纯文档 | 中（任何 hard 启用前必须先有保护层；当前 sidecar 不进 04，可延后）|
| 4 | **不建议**改 `run_predict` 主链 | display hook + 注入路径设计已能满足 dashboard / review 消费；改主链没有边际收益且可能回归 | — |
| 5 | **不建议**启用 `hard` / `forced_exclusion` | 6 项 gate 仍有 4 项 fail | — |

**强制约束**：Step 2G-6C / 6B.1 实施时仍要遵守：
- 不改 04 / 05 / 07 required 字段
- 不接 simulator 到主链（除非 6B.1 设计明确允许）
- 不写 review 的 `error_category` 主分类（仅写 free-text）
- 不出现 16 个 forbidden words

## 14. 严守边界

- ❌ 没改任何代码（本 checkpoint 是 markdown）
- ❌ 没新增任何测试
- ❌ 没写 DB
- ❌ 没改 DB schema
- ❌ 没改 `predict.py`
- ❌ 没改 `scanner.py`
- ❌ 没改 `prediction_store.py`
- ❌ 没改 `projection_output_adapter.py` / `projection_output_contract.py`
- ❌ 没改 `regime_diagnostics_dashboard.py` / `soft_metadata_simulator.py` /
  `soft_metadata_renderer.py` / `predict_tab.py`（Step 2G-6B 已 commit；
  本 checkpoint 不改）
- ❌ 没改任何 builder（`_build_exclusion_system` /
  `_build_confidence_system` / `_build_simulated_trade` / 任何其他）
- ❌ 没改 `app.py` / `ui/*` 任何模块（包括新增的
  `ui/soft_metadata_renderer.py` 与已修改的 `ui/predict_tab.py`）
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
