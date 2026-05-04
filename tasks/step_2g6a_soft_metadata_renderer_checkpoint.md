# Step 2G-6A — Soft Metadata Pure-Function Renderer Checkpoint

> **Checkpoint 文档，不是实现。** 本文档**冻结** Step 2G-6A renderer 的
> 能力范围、公开 API、card_data 输出结构、文案安全策略（16 个禁止词）、
> visibility 规则、severity / badge 策略、R4 / residual 文案模板、
> debug view 行为、测试基线、与 Step 2G-6B / 6C / 04 / 05 / 07 required
> 字段的关系。
>
> 本轮**不动任何代码**：不改 `predict.py` / `scanner.py` /
> `prediction_store.py` / `app.py` / `ui/*` / `soft_metadata_simulator.py` /
> `regime_diagnostics_dashboard.py` / 任何 builder /
> `soft_metadata_renderer.py` / DB schema 中的任何一处。

## 1. 当前完成状态

- **Step 2G-3** soft / hard exclusion re-review 完成（commit `8e837a7`）
- **Step 2G-4** soft metadata layer design 完成（commit `607ccc0`）
- **Step 2G-4.5** schema review 完成（commit `18936f2`）
- **Step 2G-5** read-only sidecar simulator 完成（commit `947f1c9`）+
  checkpoint（commit `b7675b1`）
- **Step 2G-6** dashboard / review display design 完成（commit `0c5f421`）
- **Step 2G-6A** pure-function renderer 已实现并进入 main —— commit
  `373f358` 包含 ui helper + 36 个 tests + §26 doc
- 本 checkpoint **冻结** renderer 的实际能力 + 文案安全策略 + 测试
  基线 + 与 Step 2G-6B / 6C 的接入约束，作为后续 Predict / Review
  页面接入的前置文档。

## 2. 当前 main 状态

- **main 最新 commit**：
  `373f358 feat(ui): add soft metadata pure-function renderer`
- **测试基线**：**2338 passed / 0 failed / 10 skipped /
  26 warnings / 65 subtests passed**（Step 2G-6A 起点 2302 → 2338，
  +36 净增）
- **本步骤新增 / 修改文件（3）**：
  - 新增 [`ui/soft_metadata_renderer.py`](../ui/soft_metadata_renderer.py)
  - 新增 [`tests/test_soft_metadata_renderer.py`](../tests/test_soft_metadata_renderer.py)
  - 修改 [`tasks/step_1_contract_pipeline_summary.md`](step_1_contract_pipeline_summary.md)（新增 §26）
- 未触碰：`predict.py` / `run_predict` / `scanner.py` /
  `prediction_store.py` / `projection_output_adapter.py` /
  `projection_output_contract.py` / `regime_diagnostics_dashboard.py` /
  `soft_metadata_simulator.py` / `app.py` / 任何现有 `ui/*` 模块 /
  任何 builder / DB schema / 04 / 05 / 07 任何 required 字段 /
  4 个离线 anti-false-exclusion 模块。

## 3. Renderer 定位

- **pure-function UI helper**，不是计算引擎、不是 calibration 工具、
  不是 trade decision 工具。
- 严格只读：
  - 不读 DB / 不读 CSV / 不接网络
  - 不调用 `services.soft_metadata_simulator` / 任何其他 service
  - 不依赖 Streamlit / 任何 UI framework（framework-agnostic）
  - 输入 dict 是**唯一**数据源
- 不接 Predict / Review 页面（留给 Step 2G-6B / 6C）
- 不改 `predict.py` / `scanner.py` / `prediction_store.py`
- 不改 prediction（不改 `final_direction` / `final_five_state` /
  `final_one_sentence` 等任何字段）
- 不改 `final_projection`（任何 6 个字段）
- 不改 `simulated_trade`（继续 `no_trade` / `none` / 空 / `0%`）
- 不写 04 / 05 / 07 任何 required 字段
- 只把 `soft_metadata.v1` dict 转成**安全展示数据**（card_data）+
  可选 markdown 字符串。

## 4. Public API

```python
def render_soft_metadata_card_data(
    soft_metadata: dict,
    *,
    context: str = "predict",       # "predict" | "review"
    include_debug: bool = False,
) -> dict:
    """Pure function. Always returns a dict; never raises."""

def render_soft_metadata_markdown(card_data: dict) -> str:
    """Pure function. Empty string when card_data.visible is False."""
```

模块级常量（可被消费者引用）：
- `FORBIDDEN_COPY_TOKENS`：16 个禁止词的 frozenset/tuple（详见 §6）

## 5. 输出结构

`render_soft_metadata_card_data` 返回 dict 顶层字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `visible` | bool | 是否应显示（visibility 矩阵决定，见 §7）|
| `title` | str | "结构性偏多风险提示" / "结构性偏多归因维度（候选）" |
| `subtitle` | str | empty / "未触发 soft metadata（候选归因维度为空）" / "本预测进入 final test 保留区间…" 等 |
| `cards` | list | 0-3 张 card；超出截断（Step 2G-4.5 §9.3）|
| `debug` | dict \| None | 仅 `include_debug=True` 时填充 |
| `warnings` | list[str] | 来源：`summary.warnings` 透传 + renderer-level integrity warnings（severity coercion / signal_count mismatch）|

每张 `cards[i]` 包含：

| 字段 | 类型 | 说明 |
|---|---|---|
| `name` | str | `"r4_overextension"` / `"bullish_high_pos20_residual"` / 或 unknown name |
| `display_label` | str | 中文 label；缺失时填 `"未识别 metadata 信号 (<name>)"` |
| `severity` | `"low"` / `"medium"` | enum 收窄；输入 `"high"` / `"hard"` 自动 coerce 到 medium + warning |
| `badge_text` | str | `"信息提示"` / `"复核建议"` |
| `badge_tone` | str | `"info"` / `"caution"` —— 永远不是 `"danger"` / `"red"` |
| `summary_text` | str | R4 / residual / generic 三套文案 |
| `metrics` | list[{label, value}] | 4 项：历史命中率 / 看多 vs 实际上涨差 / 误杀率 / 净收益 |
| `safety_note` | str | renderer 强制注入；不接受 caller 注入 |
| `expandable_details` | list[{label, text}] | "为什么不强制排除" + "净收益不达 gate / 净收益为负" + "跨窗口 holdout" + "原始 breakdown" + "触发上下文" + "raw_features" |
| `recommended_action` | str | 默认 `"review_only"` |
| `holdout_status` | `"FAIL"` \| None | 透传自 signal |

## 6. 文案安全策略

### 6.1 16 个禁止词（`FORBIDDEN_COPY_TOKENS`）

renderer 输出（card_data + markdown 全部字符串）**永远不出现**下列词：

- 禁止交易
- 强制否定
- 必须不做
- hard exclusion
- forced exclusion
- 自动拦截
- no_trade
- 卖出信号
- 做空信号
- 看空信号
- 否决主推演
- 推翻主推演
- 强制平仓
- force close
- 阻止下单
- block order

### 6.2 测试锁定

- `ForbiddenCopyTests` 6 个测试场景（empty predict / empty review /
  R4 / residual / debug / final_test_refusal）grep 全部 16 个禁止词
- `MarkdownRendererTests::test_markdown_does_not_contain_forbidden_tokens`
  独立 grep markdown 输出
- 任何新增 candidate / template 都必须保持这 16 个禁止词的零出现

### 6.3 renderer 自己生成 `safety_note`，不接受 caller 注入

- 每张 card 的 `safety_note` 由 `_safety_note_for(signal)` **强制
  生成**，**不**读取 input signal 中的同名字段
- safety_note 内容固定包含三件套：
  - "仅供复盘参考，不改变主推演方向，不构成交易指令。"
  - "本卡片为复盘 metadata，不是交易指令；07 段策略边界（不交易）不变。"
- 这样可以防止上游误传 / 恶意注入误导文案到 UI

## 7. Visibility 规则

按 Step 2G-6 §4 / §9 / §11.5 / §11.7 visibility 矩阵：

| 输入 | context | visible | 显示 |
|---|---|---|---|
| `signals=[]`、无 warnings | `predict` | **`False`** | 完全隐藏（避免视觉疲劳）|
| `signals=[]`、无 warnings | `review` | `True` | "未触发 soft metadata（候选归因维度为空）" |
| `signals=[]`、warnings 含 `final_test_range_refusal` | `predict` 或 `review` | `True` | 显示 final test refusal subtitle + warnings；**永不隐藏** |
| `signals=[]`、warnings 仅含其他 dev warning | `predict` | `True` | 折叠 dev hint："未触发 metadata（仅有开发者 warning）" |
| `signals` 非空 | `predict` | `True` | 标题"结构性偏多风险提示" + cards |
| `signals` 非空 | `review` | `True` | 标题"结构性偏多归因维度（候选）" + 副标题强调"不是确定原因" + cards |
| `signals` 超 3 条 | 任意 | `True` | 仅渲染前 3 条（Step 2G-4.5 §9.3 cap）|

## 8. Severity / badge 策略

- `severity` enum：仅 `{"low", "medium"}`（Step 2G-4.5 Blocker 8）
- 输入 `"high"` / `"hard"` / 其他值 → renderer **coerce 到 `"medium"`** +
  在 `warnings` 写 `"renderer_warning: signal severity coerced to 'medium' …"`
- `badge_tone` 只允许：
  - `"info"` （对应 severity=low）
  - `"caution"` （对应 severity=medium）
- **永远不输出**：`"danger"` / `"red"` / `"warning"`（color/tone 词）
  / `"危险"`
- `medium` **不等于** `hard`；**不等于** 交易风险指令；**不等于** 否定方向
- 测试 `SeverityToneTests`（3 个）锁定上述行为

## 9. Signal 文案

### 9.1 R4 (`r4_overextension`)

| 字段 | 值 |
|---|---|
| `display_label` | `"高位跑赢同行后的偏多过热"`（来自 simulator）|
| `summary_text` | "历史上，AVGO 在短期明显跑赢 SOXX 且处于 20 日区间高位时，系统容易继续判偏多，但实际次日上涨比例偏低。**历史样本中该结构容易高估上涨概率**。" |
| `metrics`（4 项）| 历史命中率 / 看多 vs 实际上涨差 / 误杀率（若强制排除）/ 净收益（若强制排除）|
| `safety_note` | 强制三件套（不改变主推演方向 + 不构成交易指令 + 07 段策略边界（不交易）不变）|
| `expandable_details` | "为什么不强制排除" / "净收益不达 gate" / "跨窗口 holdout" / "原始 breakdown" / "触发上下文" / "raw_features" |

### 9.2 Residual (`bullish_high_pos20_residual`)

- 文案**弱于** R4：用"残差信号" / "上下文提示"措辞
- summary：强调"命中率接近随机，主要用于上下文提示"
- `expandable_details` 中"净收益为负"使用"**不升反降**"措辞 ——
  比 R4 的 fer 解释更严，强调"绝对不能 hard"
- 测试 `ResidualCardTests` 锁定不复用 R4 的强动量措辞

### 9.3 Unknown signal（graceful degradation）

- `name` 不在 active enum (`r4_overextension` /
  `bullish_high_pos20_residual`) 内时：
  - `summary_text` 走 `_generic_summary_text`：
    "未识别的 metadata 信号 (<name>)；按 review_only 处理，
    不改变主推演方向。"
  - `display_label` 缺失时填占位符："未识别 metadata 信号 (<name>)"
  - 仍按正常 card 流程渲染（包括 safety_note / metrics）

## 10. Debug view

- `include_debug=False`（默认）→ `card_data["debug"] = None`，
  raw JSON 不暴露
- `include_debug=True` → `card_data["debug"]` 包含：
  - `schema_version`
  - `metrics_source`
  - `metrics_window`（dict：analysis_date_min / max / paired_total /
    db_snapshot_id）
  - `metrics_computed_at`
  - `summary`（完整 summary dict）
  - `signals_raw`（输入 signals 的原始 list）
- debug view 默认在 UI 上**折叠**展示（避免用户视觉负担）；Step 2G-6B
  / 6C 实施时建议放在右上角"齿轮"图标后面
- debug view 仍受 §6 文案禁止词约束（测试
  `ForbiddenCopyTests::test_no_forbidden_when_debug_included` 锁定）

## 11. 测试覆盖

- 文件：[`tests/test_soft_metadata_renderer.py`](../tests/test_soft_metadata_renderer.py)
- 数量：**36 passed in 0.03s**（unittest）
- related (`test_soft_metadata_simulator.py` +
  `test_regime_diagnostics_dashboard.py`)：**69 passed in 0.38s**
- full pytest：**2338 passed / 0 failed / 10 skipped /
  26 warnings / 65 subtests passed**

按 Step 2G-6 §11 12 项 UI safety checks + §3 16 个文案禁止词 +
§9 visibility 矩阵 6 个分支 + R4 / residual 文案 + unknown signal
graceful degradation + defensive input handling 共 15 类覆盖：

| 类 | 数量 | 内容 |
|---|---|---|
| `EmptyPredictHiddenTests` | 2 | 空 signals + predict context → 完全隐藏 |
| `EmptyReviewVisibleTests` | 1 | 空 signals + review context → 显示"未触发" |
| `R4CardTests` | 4 | display_label / metrics / safety_note / expandable_details |
| `ResidualCardTests` | 2 | weaker context wording / negative net_benefit phrasing |
| `ForbiddenCopyTests` | 6 | 6 个典型场景 grep 16 个禁止词 |
| `HardExclusionAllowedSurfacedTests` | 1 | safety_note 必含三件套 |
| `FinalTestRefusalVisibleTests` | 2 | predict / review 都不隐藏 final_test_range_refusal |
| `DebugToggleTests` | 2 | include_debug=False 隐藏 / =True 含 schema_version + metrics_window |
| `SeverityToneTests` | 3 | medium → caution；low → info；high 输入 coerce + renderer_warning |
| `UnknownSignalGracefulTests` | 3 | 未知 name → generic 文案；缺 label → 占位符；非 dict signal 丢弃 |
| `SignalCountMismatchTests` | 1 | summary.signal_count != len(signals) → renderer_warning |
| `MaxThreeCardsTests` | 1 | 5 signals → 仅渲染 3 |
| `NoForbiddenImportsTests` | 1 | `ast.walk` parse：禁 yfinance / requests / longbridge / broker / paper_trade / streamlit / sqlite3 / simulator / dashboard / prediction_store / 三个 v1 stub trio |
| `MarkdownRendererTests` | 4 | 空时返回空串 / R4 markdown 含 label+summary+metric+safety / review empty state / markdown 不含禁止词 |
| `DefensiveInputTests` | 3 | 非 dict 输入 → hidden / 未知 context → fallback predict / 缺 metrics → "n/a" |

测试基线累积：**Step 2G-6A 起点 2302 → 2338**（+36 净增）；
0 failed；10 skipped 不变。

## 12. 与 Step 2G-6B / 6C 的关系

- **Step 2G-6B Predict 页面接入**应**调用 renderer**（即
  `render_soft_metadata_card_data` + `render_soft_metadata_markdown`），
  **不**直接手写文案
- **Step 2G-6C Review 页面接入**也**调用 renderer**，传
  `context="review"`
- 页面接入只**消费** card_data / markdown：
  - `visible` → 决定是否显示整个区块
  - `title` / `subtitle` → 区块顶部
  - `cards[i]` → 渲染成 Streamlit container / HTML（按各页面 UI 风格）
  - `warnings` → 显示 dev warning 区块（默认折叠或边栏）
  - `debug` → 仅当用户点击"齿轮"展开 debug 模式时显示
- 页面**不应**重新解释 severity（直接用 `badge_text` / `badge_tone`）
- 页面**不应**显示 §6 forbidden words（renderer 已保证不输出，
  页面也不应自己写）
- 页面**不应**改变 prediction / trade fields（任何对
  `final_direction` / `simulated_trade.*` 的修改都禁止）
- Step 2G-6D UI tests 应使用 Streamlit AppTest 框架
  （与现有 `tests/test_command_bar_apptest.py` /
  `tests/test_control_tab_apptest.py` 同模式）覆盖 Step 2G-6 §11
  全部 12 项 UI safety checks

## 13. 与 04 / 05 / 07 required 字段关系

| 字段 / 位置 | renderer 行为 |
|---|---|
| 04 `exclusion_system.exclusion_level` | ❌ 不读、不写（继续 `"none"`）|
| 04 `exclusion_system.exclusion_sources` / `exclusion_reasons` | ❌ 不读、不写（继续 `[]`）|
| 04 `exclusion_system.forced_exclusion` | ❌ 不读、不写（继续 `False`）|
| 04 `exclusion_system.anti_false_exclusion_triggered` | ❌ 不读、不写（继续 `False`）|
| 04 `exclusion_system.extras.soft_metadata` | ✅ 仅消费（输入 dict）|
| 05 `confidence_system` 4 个 score 字段 + `event_score` | ❌ 不读、不写 |
| 05 `confidence_level` / `total_confidence` / `confidence_reason` | ❌ 不读、不写 |
| 07 `simulated_trade` 6 个决策字段 + `extras.trade_engine_enabled` | ❌ 不读、不写（继续策略边界值）|
| `final_projection.*` 任何字段 | ❌ 不读、不写 |

renderer 是 sidecar / extras-only：**仅**消费 `soft_metadata.v1`
dict（来自 `extras.soft_metadata` 或 simulator 直接调用），从不读取
或修改任何 contract required 字段。任何 required 升级仍需 Step 2G-8+
+ hard gate 通过。

## 14. 2026 final test cutoff

- renderer **只显示**输入 metadata，**不**访问 2026 数据
- renderer 不接 DB / CSV / 网络，因此**不可能**读到 2026-01-01 之后
  的数据
- `summary.warnings` 含 `"final_test_range_refusal"` 时，renderer
  visibility 矩阵强制 `visible=True` + 显示 subtitle："本预测进入
  final test 保留区间，soft_metadata 已暂停（防止参数污染）"
- 测试 `FinalTestRefusalVisibleTests`（2 个）锁定 predict / review
  两个 context 下都不隐藏 final_test_range_refusal
- 继续遵守 2026-01-01 之后为最终测试集；renderer 不参与任何
  调参 / 反复跑

## 15. 下一步建议

按推荐优先级：

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **Step 2G-6B** Predict 页面接入 | 在 `app.py` / `ui/predict_tab.py` 调用 renderer；位置按 Step 2G-6 §4.1（`final_projection` 之后 / `simulated_trade` 之前）；**仅显示 renderer output**；**不**重写文案；**不**改 `final_direction` / `simulated_trade.*` | **高**（本 checkpoint 的天然延续；renderer 已就位） |
| 2 | **Step 2G-6D** UI tests | 用 Streamlit AppTest 覆盖 Step 2G-6 §11 全部 12 项 UI safety checks；与现有 AppTest 测试同模式 | 高（建议与 #1 同 step 完成，避免接入后没有回归覆盖） |
| 3 | **Step 2G-6C** Review 页面接入 | 类似 #1，但 context="review"；归因维度按 Step 2G-6 §8 4 种组合规则写入 `review_log.confidence_note` / `watch_for_next_time` free-text 字段 | 中（Predict 接入完成 + 稳定运行后再做）|
| 4 | **Step 2G-7** anti-false-exclusion display / design | 4 个候选模块挑一个的 dashboard 显示设计；纯文档 | 中-低（任何 hard 启用前必须先有保护层；当前 sidecar 不进 04，可延后）|
| 5 | **不建议**改 prediction logic | renderer + 接入已能让 dashboard / review 消费 metadata | — |
| 6 | **不建议**启用 hard | 6 项 gate 仍有 4 项 fail | — |
| 7 | **不建议**升级 04 / 05 / 07 required 字段 | Step 2G 设计文档 §6 红线 | — |

## 16. 严守边界

- ❌ 没改任何代码（本 checkpoint 是 markdown）
- ❌ 没新增任何测试
- ❌ 没写 DB
- ❌ 没改 DB schema
- ❌ 没改 `predict.py`
- ❌ 没改 `scanner.py`
- ❌ 没改 `prediction_store.py`
- ❌ 没改 `projection_output_adapter.py` / `projection_output_contract.py`
- ❌ 没改 `regime_diagnostics_dashboard.py` / `soft_metadata_simulator.py` /
  `soft_metadata_renderer.py`（renderer 已 commit，本 checkpoint 不改）
- ❌ 没改任何 builder（`_build_exclusion_system` /
  `_build_confidence_system` / `_build_simulated_trade` / 任何其他）
- ❌ 没改 `app.py` / `ui/*` 任何模块（包括新增的 `ui/soft_metadata_renderer.py`）
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
