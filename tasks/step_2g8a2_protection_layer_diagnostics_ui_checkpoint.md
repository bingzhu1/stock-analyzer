# Step 2G-8A.2 — Protection Layer Diagnostics UI Integration Checkpoint

> **状态固化文档（Predict / Review UI integration checkpoint），不实现，不改代码。**
> 本文档**冻结** `protection_layer_diagnostics.v1` 在 Predict / Review
> UI 中的接入位置、`protection_layer_diagnostics_card.v1` 输出 schema、
> 四个 connection flag UI 文案、两个 baseline-level blocking guards 的
> 渲染规则、8-token forbidden lockdown、与 Step 2G-7C dashboard / Gate
> 5 的隔离约束、与 Step 2G-8A.3 / 2G-8B / 2G-8+ 的衔接边界。
>
> 本轮**不动任何代码**：不改 `predict.py` / `run_predict` /
> `scanner.py` / `prediction_store.py` / `app.py` / 任何 `ui/*` /
> `services/*`（含 `services/protection_layer_diagnostics.py` /
> `ui/protection_layer_diagnostics_renderer.py`）/ 任何 builder /
> DB schema 中的任何一处。

---

## 1. 当前完成状态

- **Step 2G-8** launch condition review 已完成（结论：NO-GO，hard gate
  4/6 fail）
- **Step 2G-8A** protection-layer connection design + checkpoint 已
  完成并进入 main（commits `b4c1919` / `8c56696`）
- **Step 2G-8A.1** read-only protection diagnostics helper + checkpoint
  已完成并进入 main（commits `cdbb13a` / `b43fd9d`）
- **Step 2G-8A.2** Predict / Review UI integration 已完成并进入 main
  （commit `0eb589c`）
- 本 checkpoint **固定**：
  - UI renderer + card_data 输出形态
  - Predict / Review 两个接入点的位置与 try/except 包裹
  - 4 个 connection flag UI 文案（中文 label 故意避开 `hard` /
    `forced` 子串）
  - 8-token renderer-side forbidden lockdown
  - Gate 5 仍 fail 的隔离约束
- Step 2G-8A.2 是 **UI display-only 集成**，但本 checkpoint **只是**
  状态归档；不实现、不改代码、不写 DB

---

## 2. 当前 main 状态

- main 最新 commit：**`0eb589c`**
- commit message：`feat(ui): wire protection layer diagnostics into Predict and Review`
- 上游：`origin/main` 已同步
- full pytest：**2591 passed / 0 failed / 10 skipped / 26 warnings /
  94 subtests**（基线 2560 → 2591，+31 净增；零回归）

本步骤新增 / 修改文件（已 merge 到 main）：

| 路径 | 类型 | 说明 |
|---|---|---|
| `ui/protection_layer_diagnostics_renderer.py` | 新增 | pure card_data + markdown helpers |
| `ui/predict_tab.py` | 修改 | imports + 2 处 try/except 包裹的 sub-section 接入 |
| `tests/test_protection_layer_diagnostics_renderer.py` | 新增 | 23 focused tests + 5 subtests |
| `tests/test_predict_tab_soft_metadata_display.py` | 修改 | `ProtectionLayerDiagnosticsPredictAppTests` × 3 + wiring smoke |
| `tests/test_review_tab_soft_metadata_display.py` | 修改 | `ProtectionLayerDiagnosticsReviewAppTests` × 4 |
| `tasks/step_1_contract_pipeline_summary.md` | 修改 | 新增 §34 |

本 checkpoint 文档（即本文件）尚未 commit；本轮只写文档、不 commit /
push。

---

## 3. renderer 输出

模块：`ui/protection_layer_diagnostics_renderer.py`

### 3.1 公共 API

```python
build_protection_layer_diagnostics_card_data(
    diagnostics: dict | None,
) -> dict
```

- 输入：`protection_layer_diagnostics.v1` helper 输出（或 `None` /
  非 dict / 缺 `schema_version` → 安全 hidden）
- 输出：`protection_layer_diagnostics_card.v1`（见 §3.2）
- 纯函数；不 mutate 输入；从不 raise

```python
render_protection_layer_diagnostics_markdown(card_data: dict) -> str
```

- 输入：上面 builder 的输出
- 输出：safe markdown 字符串
- `visible=False` → 返回 `""`（UI 不渲染空盒）
- 永远不出现 8 个 forbidden token（见 §8）

### 3.2 card schema

```json
{
  "schema_version": "protection_layer_diagnostics_card.v1",
  "visible": true,
  "diagnostic_connected": true,
  "hard_gate_connected": false,
  "required_field_connected": false,
  "protection_layer_connected_for_gate": false,
  "guards": [
    {
      "name": "holdout_stability_guard",
      "status": "blocking",
      "reason": "holdout_status_FAIL",
      "evidence": {"holdout_status": "FAIL"},
      "message": "跨窗口验证未通过，当前只允许复盘提示。"
    },
    {
      "name": "net_benefit_guard",
      "status": "blocking",
      "reason": "net_benefit_below_gate",
      "evidence": {"net_benefit": 0.0219, "threshold": 0.05},
      "message": "净收益不足，当前只允许复盘提示。"
    }
  ],
  "summary": {
    "hard_upgrade_blocked": true,
    "display_only": true,
    "blocking_guard_count": 2,
    "required_next_step": "narrower_candidate_research"
  },
  "warnings": []
}
```

### 3.3 visibility 规则

| 输入 | `visible` | UI 行为 |
|---|---|---|
| `None` / 非 dict / 缺 `schema_version` | `false` | 完全不渲染 |
| `guards=[]` 且 `warnings=[]` | `false` | 不渲染（避免空盒） |
| 至少 1 个 guard | `true` | 渲染 guard 列表 |
| `warnings` 非空（如 `missing_metrics` / `final_test_range_refusal`） | `true` | 渲染 warning 提示 |

`visible=False` → `render_protection_layer_diagnostics_markdown` 返回
`""`，调用方的 `if _pld_card.get("visible")` 判断后**不**调用
`st.markdown`，UI 自动隐藏。

---

## 4. Predict 接入位置

文件：`ui/predict_tab.py`

### 4.1 接入点

- expander：**`"为什么这里只做提示"`**（已存在的 AFX expander）
- 渲染顺序：
  1. AFX markdown（5 项 protective findings，per-prediction）
  2. **本步骤新增** protection diagnostics markdown（2 项 blocking
     guard，baseline-level）
- 默认折叠（继承 AFX expander 的 `expanded=False`）
- **不**新增独立顶级区块（避免 dashboard 噪声）

### 4.2 双层 try/except 防御

```python
try:
    _afx_soft = _extract_soft_metadata(_enriched_for_display)
    if isinstance(_afx_soft, dict) and _afx_soft.get("signals"):
        _afx_display = build_anti_false_exclusion_display(_afx_soft)
        if _afx_display.get("visible"):
            with st.expander("为什么这里只做提示", expanded=False):
                st.markdown(render_anti_false_exclusion_markdown(_afx_display))
                # Step 2G-8A.2 — protection diagnostics sub-section
                try:
                    _pld = build_protection_layer_diagnostics(
                        soft_metadata=_afx_soft,
                    )
                    _pld_card = build_protection_layer_diagnostics_card_data(_pld)
                    if _pld_card.get("visible"):
                        st.markdown(
                            render_protection_layer_diagnostics_markdown(_pld_card)
                        )
                except Exception:
                    pass
except Exception:
    pass
```

### 4.3 行为契约

- 失败时 silently skip：内层 try/except 捕获 helper / renderer 任意
  异常，**不**影响外层 AFX 渲染，**不** crash Predict 页面
- 输入仅来自 caller-injected `soft_metadata`（不读 DB / 不调用
  dashboard service）
- **不**写 DB
- **不**改 `final_projection` / `final_direction` / `simulated_trade`
  / `no_trade` / `confidence_system`
- **不**改 `predict_result` 任何字段（renderer / helper 都不 mutate
  input）

---

## 5. Review 接入位置

文件：`ui/predict_tab.py`（在 `_render_review_result` 函数内）

### 5.1 接入点

- expander：**`"保护层诊断"`**（已存在的 AFX Review expander）
- 渲染顺序：
  1. AFX markdown（含 survival case / gate-fail findings，
     prediction_correct-aware）
  2. **本步骤新增** protection diagnostics markdown
- correct + R4 / wrong + R4 两种 outcome 都能显示
- 默认折叠（继承 AFX Review expander 的 `expanded=False`）

### 5.2 双层 try/except 防御

```python
try:
    if isinstance(soft_metadata, dict) and soft_metadata.get("signals"):
        _afx_display = build_anti_false_exclusion_display(
            soft_metadata, prediction_correct=prediction_correct,
        )
        if _afx_display.get("visible"):
            with st.expander("保护层诊断", expanded=False):
                st.markdown(render_anti_false_exclusion_markdown(_afx_display))
                # Step 2G-8A.2 — protection diagnostics sub-section
                try:
                    _pld = build_protection_layer_diagnostics(
                        soft_metadata=soft_metadata,
                    )
                    _pld_card = build_protection_layer_diagnostics_card_data(_pld)
                    if _pld_card.get("visible"):
                        st.markdown(
                            render_protection_layer_diagnostics_markdown(_pld_card)
                        )
                except Exception:
                    pass
except Exception:
    pass
```

### 5.3 行为契约

- 失败时 silently skip：内层 try/except 捕获 helper / renderer 任意
  异常，**不**影响外层 AFX 渲染，**不** crash Review 页面
- **不**写 `review_log` 任何 required 字段
- **不**写 DB
- **不**改 `error_category` / `direction_match` / `comparison` / 任何
  Review schema
- 与 Step 2G-6C `triggered_but_not_error` 象限归因展示并存（两者各自
  独立渲染）

---

## 6. 四个 connection flags UI 显示

| flag | helper 取值 | UI label | UI 显示 |
|---|---|---|---|
| `diagnostic_connected` | **`true`**（v1 永远） | "诊断已接入" | "诊断已接入 · 是" |
| `hard_gate_connected` | **`false`**（v1 永远） | "决策链未接入" | "决策链未接入 · 否" |
| `required_field_connected` | **`false`**（v1 永远） | "04 字段未升级" | "04 字段未升级 · 否" |
| `protection_layer_connected_for_gate` | **`false`**（v1 永远） | "评估闸门暂未接入" | "评估闸门暂未接入 · 否" |

### 6.1 文案设计原则

- **故意不用** `hard` / `forced` 英文 token —— renderer-side forbidden
  lockdown 严格禁止这两个子串出现在任何渲染输出中
- **故意不打印** 原始 flag 名（如 `hard_gate_connected`），改用中文
  label 表达同一语义
- **避免误导**：用户看到 `诊断已接入 · 是` 时**不会**误以为 Gate 5
  已 pass 或 hard 升级被允许
- **`diagnostic_connected = true` 仅代表**：sidecar 节点存在，UI
  可以渲染"保护层诊断详情"，**不**等于决策链已接入、**不**等于
  Gate 5 已 pass、**不**等于 hard / required 已升级

### 6.2 反误读

任何未来读者看到此 UI 都应理解：
- "诊断已接入" = sidecar 已生成
- "决策链未接入" = run_predict / scanner / prediction_store 都不读
  本 sidecar
- "04 字段未升级" = `prediction_log` schema 未变；
  `anti_false_exclusion_triggered` 未写
- "评估闸门暂未接入" = Step 2G-7C dashboard `protection_layer_connected`
  仍 fail；hard gate 仍 2 pass / 4 fail

---

## 7. 两个 baseline-level blocking guards

### 7.1 `holdout_stability_guard`

| 项 | 值 |
|---|---|
| 触发 | candidate / R4 `holdout_status == "FAIL"` |
| evidence | `{holdout_status: "FAIL"}` |
| reason | `holdout_status_FAIL` |
| status | `blocking` |
| message | `"跨窗口验证未通过，当前只允许复盘提示。"` |
| UI label | `"跨窗口稳定性 guard"` |

### 7.2 `net_benefit_guard`

| 项 | 值 |
|---|---|
| 触发 | R4 `net_benefit < 0.05`（实测 `+0.0219`） |
| evidence | `{net_benefit: 0.0219, threshold: 0.05}` |
| reason | `net_benefit_below_gate` |
| status | `blocking` |
| message | `"净收益不足，当前只允许复盘提示。"` |
| UI label | `"净收益 guard"` |

### 7.3 与 AFX 5 个 findings 的关系

- AFX 5 个 findings（`r4_survival_case` / `r4_false_exclusion_risk` /
  `soft_metadata_holdout_fail` / `net_benefit_insufficient` /
  `missing_protection_layer`）是 **per-prediction** 视图
- protection diagnostics 2 个 guard 是 **baseline-level** 视图
- 二者**不重复**：
  - AFX 在每次预测的 metadata 上判断"为什么这里只做提示"
  - protection guard 在 baseline 累积统计上判断"为什么 Gate 5 仍
    blocking"
- 两者**同时**展示让用户看到完整保护证据链：
  per-prediction R4 evidence + baseline-level guard blocking
- 两者**都**强调：`hard_exclusion_allowed = False`、当前仅
  display-only

---

## 8. forbidden tokens / 文案安全

### 8.1 8 个 renderer-side forbidden token（Step 2G-8A.2 §1）

| # | token | 锁定理由 |
|---|---|---|
| 1 | `禁止交易` | 交易指令禁用 |
| 2 | `强制否定` | 强制语义禁用 |
| 3 | `hard`（子串） | 不让 UI 暗示 hard 升级被允许 |
| 4 | `forced`（子串） | 同上 |
| 5 | `no_trade` | 仓位指令禁用 |
| 6 | `卖出信号` | 方向指令禁用 |
| 7 | `做空信号` | 同上 |
| 8 | `自动拦截` | 决策语义禁用 |

### 8.2 测试锁定

- `tests/test_protection_layer_diagnostics_renderer.py::ForbiddenCopyTests`
  对 5 个 scenario × 8 个 token 用 `assertNotIn` 锁定
- `ProtectionLayerDiagnosticsPredictAppTests` 对 page-level markdown
  对 8 个 token 用 `assertNotIn` 锁定（AppTest 渲染后的实际页面文字）
- `ProtectionLayerDiagnosticsReviewAppTests` 同上

### 8.3 推荐使用文案

UI 中文文案使用：
- "诊断已接入"
- "不等于自动升级"
- "当前仍只允许复盘提示"
- "决策链未接入"
- "04 字段未升级"
- "评估闸门暂未接入"
- "跨窗口验证未通过"
- "净收益不足"
- "不改变主推演方向"
- "不构成交易指令"
- "升级条件未满足"
- "当前仅作展示"

---

## 9. Gate 5 状态

**Gate 5 `protection_layer_connected` 仍 fail（未改变）。**

- `services/anti_false_exclusion_dashboard.py:44` 第 44 行：
  ```python
  _PROTECTION_LAYER_CONNECTED = False
  ```
  **本步骤未改动**；Step 2G-8A.2 UI 接入不修改这一常量
- `summarize_anti_false_exclusion_dashboard()` 输出的
  `hard_gate_status.protection_layer_connected` 仍为 `"fail"`
- `hard_exclusion_allowed` 仍为 `False`（依赖 6 项 gate 全 pass，而
  Gate 5 永远 fail）
- UI 显示**不改变** gate 状态：renderer / helper 都不写 dashboard /
  contract / DB

| Gate | 状态（未变） |
|---|---|
| `total_paired_ge_90` | PASS |
| `candidate_paired_ge_30` | PASS |
| `false_exclusion_rate_lte_0_10` | FAIL（R4 fer = 0.3235） |
| `net_benefit_gte_0_05` | FAIL（nb = +0.0219） |
| **`protection_layer_connected`** | **FAIL（仍 fail）** |
| `cross_window_holdout_pass` | FAIL |

**UI 接入只是 sidecar display**：
- 不读、不写、不影响 `_PROTECTION_LAYER_CONNECTED` 常量
- 不进入 hard decision pipeline
- `protection_layer_connected_for_gate = false` 在 card_data 与 UI
  渲染中均锁定，与 Step 2G-7C dashboard 的 `protection_layer_connected`
  fail 状态**字面对应**

---

## 10. 测试覆盖

### 10.1 测试结果

| 命令 | 结果 |
|---|---|
| `pytest tests/test_protection_layer_diagnostics_renderer.py -q` | **23 passed**（+5 subtests） |
| `pytest tests/test_predict_tab_soft_metadata_display.py tests/test_review_tab_soft_metadata_display.py -q` | **70 passed** |
| `pytest tests/test_protection_layer_diagnostics.py tests/test_anti_false_exclusion_display.py -q` | **74 passed**（+24 subtests） |
| `pytest -q`（全量） | **2591 passed / 10 skipped / 0 failed / 26 warnings / 94 subtests** |

测试基线累积：**Step 2G-8A.1 终点 2560 → Step 2G-8A.2 终点 2591**
（+31 净增；现有 2560 基线零回归）。

### 10.2 测试矩阵

`tests/test_protection_layer_diagnostics_renderer.py`（23 tests +
5 subtests）：

| 测试类 | 数量 | 覆盖点 |
|---|---|---|
| `CardDataMissingHiddenTests` | 4 | None / non-dict / 缺 schema_version / 无 guards 无 warnings → invisible |
| `CardDataGuardsTests` | 3 | 两 guard / blocking_guard_count 一致 / 单 guard |
| `CardDataConnectionFlagTests` | 3 | `diagnostic_connected=True` / 三 false / 多 scenario 锁定 |
| `MarkdownStructureTests` | 3 | 默认可见短语 / invisible → `""` / missing_metrics warning 走 visible |
| `ForbiddenCopyTests` | 1 (5 subtests) | 5 scenario × 8 forbidden token |
| `InputImmutabilityTests` | 2 | builder / renderer 不修改 input |
| `UnknownGuardTests` | 2 | unknown guard name 渲染 / 非 dict guard 跳过 |
| `FinalTestRangeWarningTests` | 1 | `final_test_range_refusal` 透传 |
| `IsolationTests` | 2 | `ast.walk` 禁 `streamlit` / DB / 网络 / trading / dashboard import；schema_version 锁定 |
| `SummaryStateLineTests` | 2 | 状态短语 / `required_next_step` |

`tests/test_predict_tab_soft_metadata_display.py`（+4 cases）：
- `ProtectionLayerDiagnosticsPredictAppTests` × 3：诊断 sub-section
  渲染 / no-pass 短语 / no-signal 不渲染
- `ProtectionLayerWiringSmokeTests` × 1：`ui.predict_tab` 已 import
  3 个 helper

`tests/test_review_tab_soft_metadata_display.py`（+4 cases）：
- `ProtectionLayerDiagnosticsReviewAppTests` × 4：correct + R4 / wrong
  + R4 / no-signal / pass-path 不广告 upgrade

### 10.3 关键 isolation 锁定

`ast.walk` 测试锁定 renderer 模块未 import：
- `streamlit`（renderer 是纯函数；UI 调用方负责 `st.markdown`）
- `yfinance` / `requests`
- `longbridge` / `broker` / `paper_trade`
- `sqlite3`
- `services.prediction_store`
- `services.confidence_engine` / `services.contradiction_engine` /
  `services.risk_model`
- `services.soft_metadata_simulator`
- `services.anti_false_exclusion_dashboard`
- `predict` / `scanner`

---

## 11. 与 04 / 05 / 07 required 字段关系

UI 集成**只**调用现有 helper + 现有 renderer；**不**影响任何 04 / 05
/ 07 schema：

| 字段 | 状态 |
|---|---|
| `anti_false_exclusion_triggered` | **不**写（保持现状） |
| `exclusion_level` | **不**改 |
| `forced_exclusion` | **不**改 |
| `confidence_score` / `final_confidence` | **不**改 |
| `simulated_trade` | **不**改 |
| `no_trade` | **不**改 |
| `final_direction` / `final_projection` | **不**改 |
| `hard` 启用 | **不**启用 |
| `forced_exclusion` 启用 | **不**启用 |
| 04 `prediction_log` schema | **不**升级 |
| 05 `outcome_log` schema | **不**升级 |
| 07 `review_log` schema | **不**升级 |

**`protection_layer_diagnostics` 仍是 extras / sidecar-only**：
- 不进入 04 / 05 / 07 任何 required 字段
- 不进入 `contract_payload_json`
- 不持久化到任何表
- UI 仅在内存中由 renderer 构造、由 streamlit 渲染

---

## 12. 当前限制

UI 已落地，但仍有边界限制（v1 范围内）：

| # | 限制 | 解封步骤 |
|---|---|---|
| 1 | dashboard aggregate **尚未显示** `guard_total` / `guard_blocking_count` | Step 2G-8A.3 |
| 2 | `protection_layer_diagnostics` **不保存 DB**；每次 caller 即时构造 | （永远不解封；sidecar-only） |
| 3 | 保护层**仍未进入** decision pipeline | Step 2G-8+ launch review（前提是 8B / 8C 先完成） |
| 4 | hard gate 仍 **2 pass / 4 fail**（fer / nb / protection_layer / holdout） | 同上 |
| 5 | UI 仅展示 2 个 guard（holdout / net_benefit）；4 个候选模块（survival / secondary_confirm 等）**未实施** | Step 2G-8B narrower R4 candidate research |
| 6 | renderer 不读 baseline；caller 自行喂 soft_metadata | （v1 强约束；纯函数） |
| 7 | UI 仅显示在 anti-false expander 子节，**未**新增独立顶级区块 | （设计选择，避免 dashboard 噪声；不计划解封） |

---

## 13. 下一步建议

按推荐优先级：

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **Step 2G-8A.2 checkpoint**（本文档） | 冻结 UI 接入位置 + card schema + 4 connection flag UI 文案 + 8-token forbidden + Gate 5 仍 fail | **本轮** |
| 2 | **Step 2G-8A.3** dashboard guard count integration | 在 Step 2G-7C aggregate JSON / dashboard 中增加 `guard_total` / `guard_blocking_count` / blocking_reason 分布；read-only；**不**让 Gate 5 自动 pass | **高**（与 8A.1 / 8A.2 配套；让 dashboard 也看见 sidecar） |
| 3 | **Step 2G-8B** narrower R4 candidate research | 只读 ad-hoc sqlite 研究 survival pattern / secondary confirmation；为 Gate 3 / 4 缩小 gap 找证据；**不**接决策链 | 中（与 8A 解耦；可并行） |
| 4 | **Step 2G-8C** holdout gap analysis | 只读对比 in-sample vs holdout；为 Gate 6 找诊断 | 中-低（与 Step 3 calibration 重启耦合） |
| 5 | **不推荐** 直接实施 hard gate / required 升级 | 4 项 gate fail；Step 2G-8 launch review 已 NO-GO | — |
| 6 | **不推荐** 让 Step 2G-7C dashboard `protection_layer_connected` 自动变 pass | sidecar ≠ decision pipeline；必须 Step 2G-8+ launch review | — |
| 7 | **不推荐** 改 `_build_exclusion_system` / `run_predict` / `prediction_store` 主链 | 当前 sidecar + UI display + Review attribution + protection display + dashboard aggregate 已是最大可行边界 | — |

**强制约束**（继承 Step 2G-8A 设计 §13 / 8A.1 checkpoint §14）：
Step 2G-8A.3 / 2G-8B / 2G-8C 实施时仍要遵守：
- 不改 04 / 05 / 07 required 字段
- 不改 `run_predict` 主链
- 不写 DB
- 不出现 19 forbidden words（AFX 内部）/ 16 forbidden words（页面级）
  / 8 forbidden words（protection sidecar 内部 — 本步骤建立）
- `hard_exclusion_allowed` 永远 `False`
- `protection_layer_connected_for_gate` 永远 `False`（v1）

---

## 14. 严守边界

本文是**纯 checkpoint 文档**：

- ❌ 没改任何代码（含 `ui/protection_layer_diagnostics_renderer.py`
  / `ui/predict_tab.py` / `ui/review_tab.py`）
- ❌ 没改 DB schema
- ❌ 没写 DB
- ❌ 没改 `run_predict` / `predict.py` / `scanner.py` /
  `prediction_store.py` / `app.py`
- ❌ 没改 `services/protection_layer_diagnostics.py` /
  `services/anti_false_exclusion_dashboard.py` /
  `ui/anti_false_exclusion_display.py` /
  `services/soft_metadata_simulator.py` / 任何已有 service / ui 模块
  / 任何 builder
- ❌ 没改 04 / 05 / 07 任何 required 字段
- ❌ 没启用 `hard` / `forced_exclusion` /
  `anti_false_exclusion_triggered`
- ❌ 没接 `yfinance` / `requests` / 任何网络
- ❌ 没接 trading API / `longbridge` / `broker` / `paper_trade`
- ❌ 没让 Step 2G-7C dashboard `hard_gate_status.protection_layer_connected`
  自动 pass
- ❌ 没触碰 2026-01-01 之后 final test range
- ❌ 没运行 replay / 没新写 replay 行
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` /
  `avgo_agent.db.backup_*`
- ❌ 没运行 `pytest`（本轮纯文档；测试结果引用 commit `0eb589c`
  的实测数据）
- ✅ 只新增 1 份 markdown checkpoint 文档（本文件）
