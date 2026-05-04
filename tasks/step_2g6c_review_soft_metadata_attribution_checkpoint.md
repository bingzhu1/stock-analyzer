# Step 2G-6C — Review Soft Metadata Possible-Attribution Checkpoint

> **Checkpoint 文档，不是实现。** 本文档**冻结** Step 2G-6C Review
> 接入位置、enriched payload 复用方式、4 象限归因规则、UI 文案边界、
> Review helper 行为、测试覆盖、与 `review_log` / DB / required 字段
> 的关系、与 Step 2G-7 anti-false-exclusion 的衔接、当前限制。
>
> 本轮**不动任何代码**：不改 `predict.py` / `run_predict` /
> `scanner.py` / `prediction_store.py` / `app.py` / `ui/*` /
> `services/*` / 任何 builder / DB schema 中的任何一处。

## 1. 当前完成状态

- **Step 2G-3 → 2G-6B.6/6B.7** 全部进入 main（参见 commit log）
- **Step 2G-5** simulator + checkpoint
- **Step 2G-6 / 6A** display design + renderer + checkpoint
- **Step 2G-6B / 6B.3** Predict display hook + enrichment helper +
  Predict integration + 三个 checkpoint
- **Step 2G-6B.4/6B.5 → 6B.6/6B.7** baseline cache + scan_result
  regime_features design + 实现 + checkpoint
- **Step 2G-6C** Review 页面接入已实现并进入 main —— commit `2616a72`
  包含：
  - `ui/review_tab.py` 修改（+~120 行：3 个 helper + 4 outcome × metadata
    中文常量 + module-top `import streamlit as st`）
  - `ui/predict_tab.py` 修改（+~26 行：`_render_review_result` 调
    `render_review_soft_metadata_section`；`render_predict_tab`
    layer-2 stash enriched payload 到 session_state）
  - `tests/test_review_tab_soft_metadata_display.py` 新增（28 个 unittest
    含 3 个 AppTest）
  - `tasks/step_1_contract_pipeline_summary.md` §30
- 本 checkpoint **冻结** Review 复盘归因行为 + helper 形状 + 测试基线
  + 与 Step 2G-7 衔接的关系，作为后续 anti-false-exclusion 设计 /
  review_log free-text 写入 / 长期历史 review metadata 查询的前置文档。

## 2. 当前 main 状态

- **main 最新 commit**：
  `2616a72 feat(ui): add soft metadata possible attribution to Review`
- **测试基线**：**2448 passed / 0 failed / 10 skipped /
  26 warnings / 65 subtests passed**（Step 2G-6C 起点 2420 → 2448，
  +28 净增）
- **本步骤新增 / 修改文件（4）**：
  - 修改 [`ui/review_tab.py`](../ui/review_tab.py)
  - 修改 [`ui/predict_tab.py`](../ui/predict_tab.py)
  - 新增 [`tests/test_review_tab_soft_metadata_display.py`](../tests/test_review_tab_soft_metadata_display.py)
  - 修改 [`tasks/step_1_contract_pipeline_summary.md`](step_1_contract_pipeline_summary.md)（新增 §30）
- 未触碰：`predict.py` / `run_predict` / `scanner.py` /
  `prediction_store.py` / `projection_output_adapter.py` /
  `projection_output_contract.py` / `regime_diagnostics_dashboard.py` /
  `soft_metadata_simulator.py` / `soft_metadata_renderer.py` /
  `soft_metadata_injection.py` / `regime_features_builder.py` /
  `soft_metadata_baseline_cache.py` / 任何 builder /
  `review_orchestrator` / `review_agent` / `review_store` /
  `review_analyzer` / `review_center` / DB schema / 04 / 05 / 07
  任何 required 字段 / `review_log` 任何 required 字段 /
  `simulated_trade.no_trade` 策略边界 / 任何其他 `ui/*` 模块。

## 3. Review 接入位置

per-prediction Review surface 是 **`_render_review_result` 在
`ui/predict_tab.py` 内**（用户点击"运行确定性复盘"后输出）：

```
_render_review_result(review_result):
    复盘得分 N/M（XX%）
    主要问题 / 三项判断均正确
    维度对比表（开盘 / 路径 / 收盘）
    错误分析详情（折叠）
    完整复盘摘要（折叠）
    方向判断 / 错误分类（两栏 metric）
    ✦ Step 2G-6C — soft metadata possible-attribution 区块（新增）
        → render_review_soft_metadata_section(soft_metadata, prediction_correct=...)
        → 整段 try/except 包裹（review 永不崩）
```

**为什么放在这里**：
- 这里**已经**有 `comparison.direction_match`（0/1/None）→ 直接派生
  `prediction_correct: bool | None`
- 已经有错误分类 / 主要问题 / 维度详情上下文 → metadata attribution
  band 是这些信息的天然补充
- per-prediction 视角 → 4 象限归因规则在 UI 上有意义
- aggregate Review tab（`ui/review_tab.py::render_review_tab`）是
  **dashboard 视图**，不适合放 per-prediction attribution；helper 函数
  仍在 `ui/review_tab.py` 模块以便测试 / 后续复用

## 4. 数据复用方式

```
render_predict_tab(scan_result, research_result):
    ...
    # Layer 2 显示阶段：
    _enriched_for_display = enrich_predict_result_with_soft_metadata(...)
    render_soft_metadata_section(_extract_soft_metadata(_enriched_for_display))
    # ✦ Step 2G-6C — stash enriched payload to session_state
    if isinstance(_enriched_for_display, dict):
        st.session_state["review_predict_result_for_metadata"] = _enriched_for_display
    ...
    # Layer 4 复盘运行后：
    _render_review_result(cached_review_result)
        # 内部从 session_state 读 enriched payload
        cached_pr = st.session_state.get("review_predict_result_for_metadata")
        soft_metadata = _extract_soft_metadata(cached_pr)
        render_review_soft_metadata_section(soft_metadata, prediction_correct=...)
```

设计要点：
- **enrichment 在 layer-2 显示阶段已计算一次**（Step 2G-6B.3）
- **stash 到 session_state** 让 review 阶段直接复用，**不重复计算**
- **session_state key**：`"review_predict_result_for_metadata"`
- **复用同一份** `canonical extras.soft_metadata` —— 单点生成，多点
  消费
- helper / renderer 仍**只读**：review 路径不修改 enriched payload
- ❌ **不写 DB**（无任何 `INSERT` / `UPDATE` / `prediction_store.save_*`）
- ❌ **不改** original `predict_result`（layer-2 stash 用的是 enriched
  shallow copy）
- ❌ **不重新计算** enrichment（review 路径**不**调
  `enrich_predict_result_with_soft_metadata`）

## 5. 4 象限归因规则

按 Step 2G-6 §8 4-quadrant：

| prediction outcome | metadata triggered | `kind` | Review 显示 label | explanation |
|---|---|---|---|---|
| **wrong** | ✅ R4 / residual 触发 | `possible_attribution` | "可能归因维度（候选，不是确定原因）" | "本次预测错误，且结构性偏多 metadata 已触发。该 metadata 是可能的归因维度之一，**不是确定原因**；不改变主推演方向，也不构成交易指令。" |
| **correct** | ✅ R4 / residual 触发 | `triggered_but_not_error` | "metadata 已触发但本次预测正确（结构幸存）" | "结构性偏多 metadata 触发，但本次预测**仍然正确**（属结构幸存）。这个信号仅作为风险参考；主推演方向已被实际行情验证。" |
| **wrong** | ❌ 无 metadata | `no_attribution` | "未触发 soft metadata（不强行归因）" | "本次预测虽然错误，但未触发 soft metadata。**不强行归因**到 metadata；请结合其他错误维度（方向 / 路径 / 五态）分析。" |
| **correct** | ❌ 无 metadata | `no_metadata` | "无 metadata 显示" | （不显示 explanation；renderer review-context empty state 显示"未触发 soft metadata"）|
| pending（None） | ✅ | `triggered_but_not_error` | 同上 | 防御性 fallback |
| pending（None） | ❌ | `no_metadata` | 同上 | empty state |

强约束：
- ❌ metadata **永远**是 *possible attribution*，**不是** *definitive cause*
- ❌ metadata **不**作为 hard exclusion
- ❌ metadata **不**作为交易指令
- ❌ `no_attribution` 场景**强制 visible** 显示 "不强行归因" 文案
  （避免 wrong + empty 被静默隐藏，让用户看到显式 guidance）

## 6. UI 文案边界

**必须保留**（Step 2G-6 §3.2 推荐措辞）：
- 候选
- 不是确定原因
- 不强行归因
- 结构幸存
- 不改变主推演方向
- 不构成交易指令
- 仅供复盘参考

**禁止出现**（Step 2G-6 §3.1 / Step 2G-6A FORBIDDEN_COPY_TOKENS 16 个）：
- 禁止交易 / 强制否定 / 必须不做
- hard exclusion / forced exclusion
- 自动拦截 / no_trade
- 卖出信号 / 做空信号 / 看空信号
- 否决主推演 / 推翻主推演
- 强制平仓 / force close
- 阻止下单 / block order

测试锁定：
- `ReviewForbiddenCopyTests` 5 个场景（4 outcome × metadata 4 组合 +
  final_test_refusal）grep 全部 16 个禁止词
- 3 个 AppTest 在真实 Streamlit 框架下也独立 grep
- **双重锁定**：renderer 已禁 + Review 页面也禁

## 7. Review helper 行为

```python
def _classify_review_attribution(
    soft_metadata: Any, *, prediction_correct: bool | None,
) -> str:
    """Pure. Returns one of {possible_attribution, triggered_but_not_error,
    no_attribution, no_metadata}."""

def build_review_soft_metadata_card_data(
    soft_metadata: dict | None, *, prediction_correct: bool | None = None,
) -> dict:
    """Pure. Returns renderer card_data (context='review') with appended
    review_attribution block. Forces visible=True for no_attribution
    case so user sees explicit guidance. Never raises."""

def render_review_soft_metadata_section(
    soft_metadata: dict | None, *, prediction_correct: bool | None = None,
) -> dict:
    """Thin wrapper: builds card_data + emits st.markdown for visible
    cards + emits attribution band. Returns card_data for testability.
    Never raises."""
```

不变量（`tests/test_review_tab_soft_metadata_display.py` 28 个测试锁定）：

- ✅ 使用 `context="review"` 复用 renderer 的 review-context 文案 +
  visibility 矩阵
- ✅ **不**手写 renderer 文案（safety_note / display_label / metrics
  全部来自 renderer）
- ✅ **不**重新解释 severity（直接用 renderer 的 `badge_text` /
  `badge_tone`）
- ✅ **不**修改 review_result（thin wrapper，无副作用）
- ✅ input dict 不被原地修改（`test_input_dict_is_not_mutated` deepcopy
  snapshot）
- ❌ 模块**不** import `services.soft_metadata_simulator` /
  `services.soft_metadata_injection` / `prediction_store` /
  `yfinance` / `requests` / 网络 / trading（`ast.walk` 锁定）
- ❌ render 路径**不**调 simulator / baseline build / DB
  （`patch` + `assert_not_called` 锁定）

## 8. 测试覆盖

| 命令 | 结果 |
|---|---|
| `pytest tests/test_review_tab_soft_metadata_display.py -q` | **28 passed in 0.26s** |
| `pytest tests/test_soft_metadata_renderer.py tests/test_predict_tab_soft_metadata_display.py tests/test_review_tab_soft_metadata_display.py -q` | **95 passed in 1.11s** |
| `pytest tests/test_soft_metadata_injection.py tests/test_soft_metadata_simulator.py -q` | **74 passed in 0.22s** |
| `pytest -q`（全量） | **2448 passed, 10 skipped, 26 warnings, 65 subtests passed in 10.29s** |

测试类覆盖（共 28 个新增）：

| 测试类 | 数量 | 内容 |
|---|---|---|
| `ClassifyReviewAttributionTests` | 7 | 4 outcome × metadata 4 组合 + pending 2 组合 + 非 dict 输入 |
| `BuildReviewCardDataTests` | 6 | review_attribution 块存在 / review-context title / no_attribution 强制 visible / no_metadata correct review visible / input 不变 / None 输入不 crash |
| `RenderReviewSectionTests` | 3 | visible 调 markdown / no_metadata correct 仍调 markdown / garbage 不 raise |
| `ReviewForbiddenCopyTests` | 5 | 4 outcome × metadata 组合 + final_test_refusal 全 grep 16 forbidden words |
| `FinalTestRefusalReviewTests` | 1 | refusal warning 强制可见 + subtitle 含 "final test 保留区间" |
| `UnknownSignalReviewTests` | 1 | unknown signal 渲染 generic + attribution kind=possible_attribution |
| `ReviewTabIsolationTests` | 2 | patch 锁定 simulator / baseline / prediction_store 不被调；`ast.walk` 锁定 import |
| `ReviewSoftMetadataAppTests`（Streamlit AppTest） | 3 | wrong+R4 / correct+R4 / wrong+empty 三个集成场景 |

测试基线累积：**Step 2G-6C 起点 2420 → 2448**（+28 净增）；
0 failed；10 skipped 不变。

## 9. AppTest 覆盖

`ReviewSoftMetadataAppTests` 3 个 Streamlit AppTest（用
`AppTest.from_string` 注入 fixture soft_metadata + prediction_correct，
跑 `at.run()` 后断言 `at.markdown`）：

| # | 测试 | 期望 |
|---|---|---|
| 9.1 | `test_apptest_wrong_with_r4_renders_possible_attribution` | 页面文本含 `"可能归因维度"` + `"不是确定原因"` + `"高位跑赢同行后的偏多过热"`；**不含** 16 个 forbidden words |
| 9.2 | `test_apptest_correct_with_r4_renders_survival_band` | 页面文本含 `"结构幸存"`；**不含** 16 个 forbidden words |
| 9.3 | `test_apptest_wrong_no_metadata_renders_no_attribution_band` | 页面文本含 `"不强行归因"`；**不含** 16 个 forbidden words |

加上 Step 2G-6B 已有的 4 个 `PredictTabAppTests` + Step 2G-6B.3 增加
的 4 个 `EnrichmentAppTests` —— **Predict + Review 共 11 个 AppTest
集成测试**覆盖 metadata 显示路径。

## 10. 与 review_log / DB 的关系

| 写入目标 | 行为 |
|---|---|
| `review_log` 任何 required 字段 | ❌ 不写（`error_category` / `root_cause` / `confidence_note` / `watch_for_next_time` / etc.）|
| `prediction_log` 任何字段 | ❌ 不写 |
| DB 任何表 | ❌ 不写（无 `INSERT` / `UPDATE` / `DELETE`）|
| `deterministic_review_log` | ❌ 不动 |
| 任何 schema 改动 | ❌ 没有 |

**归因只存在于 UI 文本 / `card_data["review_attribution"]` 字段**。
如果未来要写入 `review_log.confidence_note` / `watch_for_next_time`
free-text 字段（这两个字段已是 free text，不影响 contract required），
**必须另立任务**（Step 2G-6C.1 候选）+ 增加 `review_log` 写入的 unit
test + 确认不破坏现有 `review_log` 行为。

## 11. 与 04 / 05 / 07 required 字段关系

| 字段 / 位置 | Step 2G-6C 行为 |
|---|---|
| 04 `exclusion_system.exclusion_level` | ❌ 不变（继续 `"none"`）|
| 04 `exclusion_system.exclusion_sources` / `exclusion_reasons` / `forced_exclusion` / `anti_false_exclusion_triggered` | ❌ 不变 |
| 04 `exclusion_system.extras.soft_metadata` | ✅ 仅读取（review 路径从 session_state 读 enriched payload；不写）|
| 05 `confidence_system` 4 个 score 字段 + `event_score` / `confidence_level` / `total_confidence` / `confidence_reason` | ❌ 不变 |
| 06 `final_projection.*` 任何字段 | ❌ 不变 |
| 07 `simulated_trade` 6 个决策字段 + `extras.trade_engine_enabled` | ❌ 不变（继续 `no_trade` / `none` / 空 / `0%`）|
| `summary.hard_exclusion_allowed` | ❌ 仍 `False`（renderer + simulator + injection + Review 四重锁定）|
| `hard` / `forced` exclusion | ❌ 仍未启用 |
| `run_predict` 主链 | ❌ 一行未改 |
| `prediction_store` save_prediction 路径 | ❌ 一行未改 |
| `review_orchestrator` / `review_agent` / `review_store` 主流程 | ❌ 一行未改 |

metadata 仍是 **sidecar / extras-only**：Review 路径只**读**
`extras.soft_metadata` 并叠加 attribution band 在 UI 上显示，从不
修改任何 contract / review required 字段。

## 12. 2G-6C 对 2G-7 的意义

Step 2G-7 anti-false-exclusion display / design 应基于 2G-6C 的
4 象限输出：

- **`triggered_but_not_error` 象限**（correct + metadata triggered）
  是**未来误杀风险样本** —— 这是 anti-false-exclusion 设计的关键
  数据来源：如果 hard exclusion 启用（即使是单一信号），R4 触发但
  实际仍正确的样本就是被"误杀"的对象
- 当前真实数据：R4 baseline 36 paired，11 correct（32.4% accuracy）
  → 如果 R4 hard exclude，会同时误杀这 11 个正确样本
  → `false_exclusion_rate = 11/34 = 0.3235`（远超 0.10 gate）
- Step 2G-7 应：
  1. **不**直接把 R4 升级 hard
  2. **先设计** anti-false-exclusion 保护层 / display / diagnostics
  3. 4 个候选模块（`anti_false_exclusion_audit` /
     `big_up_contradiction_card` / `big_down_tail_warning` /
     `exclusion_reliability_review`）挑一个写接入方案
  4. 用 2G-6C 的 `triggered_but_not_error` 累积统计作为保护层的
     ground truth（Review 累积"哪些 R4 被实际行情救活了"，让
     anti-false-exclusion 学会识别这些 pattern）

强约束：
- Step 2G-7 仍**只**做设计文档（与 Step 2G-6 / 6B.1 / 6B.4-6B.5
  pattern 一致）
- Step 2G-7 **不**升级 04 / 05 / 07 required
- Step 2G-7 **不**启用 hard

## 13. 当前限制

> 本节明确"6C 完成了什么、还没完成什么"，避免后续 step 误认为
> Review attribution 已完全持久化。

- **Review attribution 不保存 DB**：仅在 UI 文本 / card_data 中显示；
  用户关闭页面后归因记录消失
- **没有长期历史 review metadata 查询**：dashboard 上无法看到"过去
  N 次预测中 R4 触发了多少次 / 多少 correct / 多少 wrong"等
  累计统计 —— 需要 Step 2G-6C.1 review_log free-text design 或
  独立 dashboard tab
- **anti_false_exclusion 4 个保护层模块仍全离线**：Step 2G-7 待启动
- **hard gate 仍未通过**：6 项中 4 项 fail（详见 Step 2G-3 §10）；
  当前阶段 sidecar 是最大可行边界
- **review_log free-text 字段（`confidence_note` /
  `watch_for_next_time`）尚未自动写入**：4 象限归因可以丰富这两个
  字段，但需另立任务

这些都是**后续任务**，**不是** Step 2G-6C 的 bug —— 本步交付了
"Review 显示层 + 4 象限归因 + 26 forbidden words 双重锁定 + 11
AppTest 集成"的最小可行接入。

## 14. 下一步建议

按推荐优先级：

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **Step 2G-7 anti-false-exclusion display / design** | 4 个候选模块挑一个的 dashboard 显示设计；纯文档；使用 2G-6C 4 象限 `triggered_but_not_error` 样本作为 ground truth | **高**（hard 启用前必须先有保护层；当前 sidecar 不进 04，可在不动主链的前提下做设计）|
| 2 | **Step 2G-6C.1 review_log free-text design**（可选） | 设计 4 象限归因如何写入 `review_log.confidence_note` / `watch_for_next_time` free-text；纯文档；不改 required 字段 | 中（让 review 历史能查询累计 metadata 触发；但当前阶段 UI 临时显示已足够）|
| 3 | **Step 2G-6B.8 baseline refresh button**（可选） | sidebar 加按钮 + diagnostics；UX 增强；不改 helper / cache | 中-低（Production 用户体验优化）|
| 4 | **不推荐**直接做 save-time DB enrichment（Step 2G-6B.1 候选 C）| 写 DB + migration | — |
| 5 | **不建议**改 `run_predict` / `prediction_store` 主链 | sidecar + UI display 已能满足；改主链没有边际收益 | — |
| 6 | **不建议**启用 `hard` / `forced_exclusion` | 6 项 gate 仍有 4 项 fail；anti-false-exclusion 保护层未接 | — |

**强制约束**：Step 2G-7 / 2G-6C.1 / 2G-6B.8 实施时仍要遵守：
- 不改 04 / 05 / 07 required 字段
- 不改 `review_log` required 字段（free-text 字段写入需独立 design）
- 不改 `run_predict` 主链
- 不写 DB（除非另立 DB hygiene 任务）
- 不出现 16 个 forbidden words
- 不破坏现有 `RequiredFieldsByteStableTests` byte-stable 不变量

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
  `regime_features_builder.py` / `soft_metadata_baseline_cache.py` /
  `predict_tab.py` / `review_tab.py`（Step 2G-6C 已 commit；本
  checkpoint 不改）
- ❌ 没改任何 builder（`_build_exclusion_system` /
  `_build_confidence_system` / `_build_simulated_trade` / 任何其他）
- ❌ 没改 `app.py` / 任何其他 `ui/*` 模块
- ❌ 没改 `review_orchestrator` / `review_agent` /
  `review_store` / `review_analyzer` / `review_center`
- ❌ 没升级 04 / 05 / 07 任何 required 字段
- ❌ 没改 `review_log` 任何 required 字段（包括
  `error_category` / `root_cause` / `confidence_note` /
  `watch_for_next_time`）
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
