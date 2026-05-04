# Step 2G-6B.4 / 6B.5 — Baseline Cache + Regime Features Source Design

> **设计文档（baseline cache + regime_features source design），不是实现。**
> 本文档**冻结** Step 2G-6B.6 实现 baseline session cache + Step 2G-6B.7
> 在 `scan_result` 暴露 `regime_features` 的方案选择、API 形状、cutoff /
> anti-lookahead 规则、与 enrichment helper 的对接方式、与 04 / 05 / 07
> required 字段的硬隔离、2026 final test cutoff 的 honoring 路径。
>
> 本轮**不动任何代码**：不改 `predict.py` / `run_predict` /
> `scanner.py` / `prediction_store.py` / `app.py` / `ui/*` /
> `soft_metadata_simulator.py` / `regime_diagnostics_dashboard.py` /
> `soft_metadata_renderer.py` / `soft_metadata_injection.py` /
> `predict_tab.py` / 任何 builder / DB schema 中的任何一处。

## 1. 背景

- **Step 2G-6B.2 / 6B.3** 已打通 enrichment → Predict display 端到端
  链路（commit `de8e2b5` + checkpoint `4e60df5`）：
  `regime_features` → enrichment helper → canonical
  `extras.soft_metadata` → display hook → renderer → 页面卡片
- **当前 production 仍可能显示 dev hint**（Step 2G-6B.3 checkpoint §7
  / §13 已 honest 列出）：
  - **根因一：baseline=None** —— `app.py` 启动时未 build
    `soft_metadata_baseline`；`session_state["soft_metadata_baseline"]`
    永远 `None` → simulator emit `signals` 时 `historical_metrics_in_sample`
    全 n/a → renderer 显示 dev hint 而非完整卡片
  - **根因二：regime_features=None** —— `scanner.py` /
    `run_predict` 主链尚未标准产出 `pos20` / `avgo_minus_soxx_20d` →
    enrichment helper 4 级 fallback 全空 → R4 / residual **不触发** →
    Predict 页面看不到 R4 card
- **本文范围**：只**设计** baseline cache + regime_features source 两个
  输入源（让 enrichment helper 拿到稳定的 baseline + features），**不**
  实现。Step 2G-6B.6 实施时直接引用本文档 §5 / §6 baseline 路径；
  Step 2G-6B.7 实施时直接引用 §9 / §10 features 路径。

## 2. 当前链路

```
predict_result (from run_predict)
       │
       ▼
enrich_predict_result_with_soft_metadata(
    predict_result,
    scan_result=scan_result,
    research_result=research_result,
    baseline=st.session_state.get("soft_metadata_baseline"),  ← 当前为 None
    regime_features=None,                                       ← 当前永远 None
    analysis_date=None,                                         ← 自动从 payload 读
)
       │
       ▼
simulate_soft_metadata(
    payload, regime_features=None, baseline=None,
    analysis_date=..., final_test_cutoff="2026-01-01"
)
       │
       ▼
soft_metadata.v1 = {
    "signals": [],                                              ← 因 features=None
    "summary": {
        "warnings": ["missing_baseline",                         ← 因 baseline=None
                     "missing_regime_features: pos20, avgo_minus_soxx_20d"],
        ...
    },
}
       │
       ▼
Predict display hook (renderer visibility 矩阵)
       │
       ▼
"未触发 metadata（仅有开发者 warning）"  ← 当前 production 实际显示
```

说明：
- ✅ helper **已支持** `baseline` 参数 + `regime_features` 参数
- ❌ 当前 `app.py` / `ui/predict_tab.py` 还**没有**稳定填这两个参数
- → 本文档解决两个 source 的设计

## 3. 设计目标

| 目标 | 说明 |
|---|---|
| ✅ 让 Predict 页面**稳定显示** R4 / residual metadata | features 满足条件时立即出现完整 R4 card；不只是 dev hint |
| ✅ 避免每次预测临时读 DB | baseline build 是 SELECT 操作（虽然只读，但每次预测都 build 会拖慢页面）|
| ✅ 避免在 UI 层重复计算复杂历史指标 | regime_features 计算 (pos20 / SOXX diff) 不放 UI；UI 只消费 |
| ❌ 不写 DB | baseline / features 来源都不引入 `INSERT` / `UPDATE` |
| ❌ 不改 `run_predict` 主链 | `predict.py` 一行未动 |
| ❌ 不改 `prediction_store` | save_prediction / DB schema 不变 |
| ❌ 不改 04 / 05 / 07 required 字段 | 任何升级仍走 Step 2G-8+ + hard gate |
| ❌ 不触碰 2026-01-01 之后 final test range | features 必须带 cutoff；simulator 已锁定 refusal |

## 4. Baseline cache 候选方案

### A. app startup / first-touch session_state cache

**定义**：
- `app.py` 启动 / 首次进入 Predict 页时调用
  `services.soft_metadata_simulator.build_soft_metadata_baseline(...)`
- 保存到 `st.session_state["soft_metadata_baseline"]`
- enrichment helper 从 session_state 读取（已实现，Step 2G-6B.3）

**优点**：
- ✅ 简单（5-10 行新代码）
- ✅ 不写 DB / 不写文件
- ✅ 不改 `run_predict`
- ✅ Predict / Review 可复用同一份 baseline
- ✅ AppTest 可直接 inject `session_state` fixture

**缺点**：
- ⚠️ 首次进入 Predict 页可能稍慢（baseline build 是 SELECT，
  ~ms 级；不阻塞主预测路径）
- ⚠️ DB 更新（新 replay / 新 outcome）后 baseline 不自动刷新；需要
  用户手动刷新或重启 app（详见 §6）
- ⚠️ AppTest 需要 mock `session_state["soft_metadata_baseline"]`
  注入（已是 Streamlit AppTest 标准模式）

**结论**：✅ **推荐第一版**

### B. lazy per-session cache with refresh button

**定义**：
- 首次需要时 build（lazy）
- 在 dashboard 或 sidebar 提供"刷新 baseline"按钮
- session 内复用直到刷新或 session 重启

**优点**：
- ✅ 比 A 更可控
- ✅ 用户主动控制刷新时机（适合 DB 频繁更新场景）
- ✅ baseline build 失败时 UI 可提示

**缺点**：
- ⚠️ UI 多一个按钮 + 状态管理
- ⚠️ 需要决定刷新按钮放哪里（Sidebar / 各 tab？）

**结论**：✅ **推荐作为 A 的增强**（Step 2G-6B.6.1 后续优化；6B.6
先做 A）

### C. file cache

**定义**：
- 写本地 JSON cache（如 `.cache/soft_metadata_baseline.json`）
- 启动时读，定期 invalidate

**优点**：
- 跨 session 复用（用户重启 app 也保留）

**缺点**：
- ❌ 写文件 → 需要文件锁 / 路径管理 / 一致性问题
- ❌ baseline 只是统计快照，不需要持久化
- ❌ 缓存路径可能与多 worker / 多用户冲突

**结论**：❌ **暂不推荐**（写文件成本超过收益）

### D. DB cache

**定义**：
- 写进 DB 一张新表 `soft_metadata_baseline_cache`

**优点**：
- 跨 session 复用 + 可被 SQL 查询

**缺点**：
- ❌ 写 DB → 违反 Step 2G 全程"不写 DB" 边界
- ❌ 增加 schema migration / 一致性问题
- ❌ 当前阶段不必要

**结论**：❌ **不推荐**（当前阶段不写 DB）

## 5. 推荐 baseline 方案

明确推荐：

| 决策 | 内容 |
|---|---|
| 实施步骤 | **Step 2G-6B.6** |
| 实施位置 | `app.py`（启动时 build）+ 必要时 `ui/predict_tab.py`（首次进入 lazy build）|
| key | `st.session_state["soft_metadata_baseline"]` |
| builder | `services.soft_metadata_simulator.build_soft_metadata_baseline(db_path=None, symbol="AVGO", limit=450)`（Step 2G-5 已实现） |
| 调用时机 | (a) `app.py` 启动时一次（推荐）；或 (b) `render_predict_tab` 首次进入时 lazy build（fallback）|
| refresh | Step 2G-6B.6 第一版**不**加按钮；后续 Step 2G-6B.6.1 增强 |
| 失败行为 | baseline build 失败时 `session_state["soft_metadata_baseline"]` 设为 `None`；页面仍可显示 warning，**不 crash** |
| 不写 DB / 不写文件 | ✅ |
| AppTest 兼容 | session_state inject 即可（已是现有 AppTest 模式）|

实施约束：
- **不**修改 enrichment helper（已支持 baseline 参数）
- **不**修改 renderer（baseline=None 行为已锁定）
- **不**改 04 / 05 / 07 required 字段
- baseline 只在 production app 链路上触发；测试 fixture 注入静态
  baseline，不依赖 DB

## 6. baseline invalidation / refresh

设计：

- **Session 内缓存**：默认整个 Streamlit session 内复用同一份 baseline
- **默认不自动刷新**：避免每次预测都重新 build（性能 + 行为可预测）
- **DB 数据变化**：
  - 如果 replay 数据被 backfill / 新增 → baseline 不会自动反映
  - 用户需要**手动刷新**（Step 2G-6B.6.1 提供按钮）或**重启 app**
- **baseline 输出元数据**：`build_soft_metadata_baseline` 返回的
  baseline dict 已包含：
  - `metrics_window.{analysis_date_min, analysis_date_max, paired_total, db_snapshot_id}`
  - `metrics_computed_at` (ISO timestamp)
  - 这些字段由 renderer debug view 暴露给开发者（已实现）
- **Dashboard debug 可展开查看**：用户可点开 metadata card 的 debug
  view 看到 baseline 的窗口 + 计算时间，判断是否需要刷新
- **暂不做复杂 invalidation**（如 TTL / DB row count 监听 / 文件
  watcher）—— Step 2G-6B.6 第一版交付即可，后续可增强

## 7. regime_features 当前需求

`simulate_soft_metadata` 需要 `regime_features` dict 含：
- `pos20`：AVGO 收盘价在过去 20 日 Low/High 区间的位置（0-1）
- `avgo_minus_soxx_20d`：AVGO 20 日收益减 SOXX 20 日收益（pp）

**R4 触发**还需要 `payload` 中已有：
- `final_direction`（来自 `final_projection`）
- `confidence_level`（来自 `confidence_system`）
- `primary_score_raw`（来自 `confidence_system.extras`）
- `peer_adjustment`（来自 `peer_confirmation_adjustment`，写入
  `trigger_context.peer_subtype`）

后 4 个**已经在 `predict_result.contract_payload`** 中（adapter 已写入）—
helper 自动读取。所以 **regime_features source 只需解决前 2 个**：
`pos20` + `avgo_minus_soxx_20d`。

## 8. regime_features 候选来源

### A. scanner / scan_result 产出

**定义**：
- 在 `scanner.py` 扫描阶段计算 `pos20` / `avgo_minus_soxx_20d`
- 放入 `scan_result["regime_features"]` 或
  `scan_result["extras"]["regime_features"]`

**优点**：
- ✅ 与 enrichment helper 4 级 fallback 顺序匹配（Step 2G-6B.1 §11.2
  / 6B.2 实现的 `_extract_regime_features` 已支持 scan_result 第 3-4
  级）
- ✅ Predict UI 可直接传 `scan_result` 给 helper（已实现）
- ✅ 不改 `run_predict` 主链
- ✅ 不写 DB
- ✅ regime_features 与 scan timestamp 同源 → cutoff 一致性自然
- ✅ Review 复盘时 `scan_result` 已包含 features → 历史可重现

**缺点**：
- ⚠️ 需要 `scanner.py` / scan builder 增加 2 个字段（最小改动）
- ⚠️ 要保证历史 cutoff / 当前数据口径一致 —— scanner 必须**只读**
  `analysis_date` 之前的数据（anti-lookahead）

**结论**：✅ **推荐**

### B. predict_result 产出

**定义**：
- `run_predict` 内部生成 `predict_result["regime_features"]`

**优点**：
- 与 helper fallback 第 2 级匹配

**缺点**：
- ❌ 会改 `run_predict` 主链 —— 违反"不改 `run_predict`" 全程边界
- ❌ 计算 regime features 与 prediction 主逻辑无关，放进 `run_predict`
  职责混杂

**结论**：❌ **暂不推荐**（违反 `run_predict` 不改约束）

### C. UI 层临时从 CSV 计算

**定义**：
- `ui/predict_tab.py` 读 `coded_data/AVGO_coded.csv` /
  `coded_data/SOXX_coded.csv` 计算 features

**优点**：
- 不改 scanner / run_predict

**缺点**：
- ❌ UI 层职责混杂（计算 + 渲染）
- ❌ Review 页面需要重复实现一遍
- ❌ AppTest 需要 mock CSV 读取
- ❌ cutoff / anti-lookahead 在 UI 层难以保证

**结论**：❌ **不推荐**

### D. enrichment helper 内部计算

**定义**：
- helper 读 CSV / DB 算 features

**优点**：
- 单点封装

**缺点**：
- ❌ 违反 Step 2G-6B.1 §10 helper 设计契约："helper 是纯函数，
  不读 CSV / DB / 网络"
- ❌ 让 helper 与 `regime_diagnostics_dashboard` 私有 helper 耦合，
  drift 风险

**结论**：❌ **不推荐**（与 helper 设计冲突）

### E. caller explicit 参数

**定义**：
- 外部调用方（test / agent / future surface）直接传 `regime_features=`

**优点**：
- ✅ 测试场景必备（已实现，Step 2G-6B.2 测试矩阵第一级 fallback）
- ✅ Agent / scripting 场景可定制 features

**缺点**：
- 不能作为**主生产**方案（每次都要外部计算）

**结论**：⚠️ **保留作为测试 / agent 调用支持**，但**不**作为主生产
方案

## 9. 推荐 regime_features 方案

明确推荐：

| 决策 | 内容 |
|---|---|
| 实施步骤 | **Step 2G-6B.7** |
| 实施位置 | `scanner.py` 或新建 `services/regime_features_builder.py`（如果不想动 scanner 主流程，可以另起 helper 在 `app.py` / `ui/predict_tab.py` 调用 scanner 之后注入到 scan_result）|
| 字段位置 | `scan_result["regime_features"]`（推荐）；或 `scan_result["extras"]["regime_features"]`（如果 scan_result 已有 `extras` 子 dict 模式）|
| 字段内容 | `{"pos20": float, "avgo_minus_soxx_20d": float, "source": "scanner_v1", "as_of_date": "YYYY-MM-DD", "data_cutoff_date": "YYYY-MM-DD", "warnings": [...]}` |
| 不改 `run_predict` | ✅ |
| Predict tab 接入 | 已实现（`ui/predict_tab.py` 已传 `scan_result` 给 helper；helper 4 级 fallback 自动命中）|
| Review 页面 | 历史 prediction 复盘时，scan_result 中应已含 features（如果是从 DB 取的历史 scan_result，需要确认 features 也持久化或重新计算）|

字段细节（**建议**；Step 2G-6B.7 实施时可调整）：

```python
scan_result["regime_features"] = {
    "pos20": 0.81,
    "avgo_minus_soxx_20d": 7.3,
    "source": "scanner_v1",                 # 版本标识，供 helper / debug 追溯
    "as_of_date": "2024-01-08",             # features 的 anchor date
    "data_cutoff_date": "2024-01-08",       # 用了 ≤ 这天的数据
    "warnings": [],                          # 数据缺失 / 历史不足等
}
```

## 10. cutoff / anti-lookahead

强约束：

- **live Predict**：使用最新 available scan data（`as_of_date` =
  `analysis_date` = today / picked date）
- **historical replay**：**不应**使用未来数据 —— `regime_features`
  必须带 `data_cutoff_date`，且 `data_cutoff_date <= analysis_date`
- **2026 final test range**：
  - **不得**用于调参 / 反复跑（与 Step 2G-3 / Step 2G-4.5 / Step
    2G-6B.1 一致）
  - 如果 `analysis_date >= "2026-01-01"`（默认 cutoff），simulator
    **already** refuses + warns（Step 2G-5 已锁定）
  - regime_features builder 也应在 `as_of_date >= "2026-01-01"`
    时**警告或拒绝输出 features**（防御性双重锁定；即使 simulator
    后续放宽，features 这层仍守住边界）
- **anti-lookahead in scanner**：scanner 计算 pos20 / SOXX diff 时
  **只**读 `analysis_date` 之前的数据；测试需覆盖 ASCII 时序断言

## 11. baseline 与 regime_features 的关系

| 维度 | baseline | regime_features |
|---|---|---|
| **是什么** | 历史样本统计（R4 / residual 在 380 paired 上的 accuracy / bias_gap / fer / nb 等）| 当前预测当下的特征（pos20 / SOXX diff 当前值）|
| **何时变** | DB 新增 replay 时变；当前 session 内默认不变 | 每次预测都不同（与 `analysis_date` / 价格走势绑定）|
| **何时计算** | 一次 / session（cache）| 每次 prediction（与 scan 同步）|
| **来源** | `build_soft_metadata_baseline()` SELECT-only | `scanner.py` 计算 + 写入 `scan_result` |
| **失败行为** | `baseline=None` → simulator 仍 emit signals，但 `historical_metrics_in_sample={}` + warning；不 crash | `regime_features=None` → R4 / residual **不触发**；signals=[] + warning；不 crash |
| **缓存策略** | session_state / lazy cache | 每次 scan 重算；不缓存 |
| **测试注入** | `session_state["soft_metadata_baseline"]` fixture | helper kwarg 直接传 / scan_result fixture |

**两者不要混淆**：
- baseline 缺失 → metric 显示 n/a（card 仍显示）
- regime_features 缺失 → R4 / residual 完全不显示

## 12. 推荐实施顺序

按优先级：

| # | 步骤 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **Step 2G-6B.6 baseline session cache** | `app.py` 启动时调 `build_soft_metadata_baseline` 缓存到 `session_state`；helper 已支持读取；新增 `tests/test_app_baseline_cache.py` AppTest 验证缓存命中 / fallback；不改 helper / renderer / DB | **高**（消除 missing_baseline warning；让 metric 显示真实数字）|
| 2 | **Step 2G-6B.7 scan_result regime_features** | `scanner.py` 或新 `services/regime_features_builder.py` 计算 pos20 / SOXX diff，写入 `scan_result["regime_features"]`；helper 4 级 fallback 自动命中；新增 `tests/test_regime_features_builder.py` 单测 + scanner 测试覆盖 anti-lookahead | **高**（让 R4 / residual 真触发；与 #1 同 step 完成最佳）|
| 3 | **Step 2G-6B.8 AppTest / integration verification** | end-to-end AppTest：从 scan → run_predict → enrichment → display → 实际看到 R4 card 的完整 production 路径 | 中（#1 + #2 完成后做）|
| 4 | **Step 2G-6C Review 页面接入** | `ui/review_tab.py` 调 helper + renderer，`context="review"`；归因写入 `review_log` free-text | 中（#3 完成后做）|
| 5 | **不推荐**做 save-time DB enrichment（候选 C from 6B.1）| 写 DB + migration | — |
| 6 | **不建议**改 `run_predict` 主链 | helper / cache / scanner 已能满足；改主链没有边际收益 | — |

## 13. 成功标准

未来若实施 Step 2G-6B.6 + 6B.7 应满足：

| # | 标准 |
|---|---|
| 1 | `app.py` 启动后 `st.session_state["soft_metadata_baseline"]` 是非 None dict（含 `metrics_source` / `metrics_window` / `r4_overextension` / `bullish_high_pos20_residual`）|
| 2 | baseline build 失败（DB 不可读 / `status="error"` / `status="no_records"`）→ `session_state` 设为 `None`；不 crash |
| 3 | `scan_result["regime_features"]`（或 `scan_result["extras"]["regime_features"]`）存在且包含 `pos20` / `avgo_minus_soxx_20d` / `source` / `as_of_date` / `data_cutoff_date` |
| 4 | Predict 页面在 features 满足 R4 condition 时**真实显示** R4 card（含完整 metrics）—— `EnrichmentAppTests::test_apptest_predict_result_with_features_displays_r4_card` 类型的测试在 production 路径上等价通过 |
| 5 | 不写 DB（baseline cache + features builder 都不调 `prediction_store.save_*` / `INSERT` / `UPDATE`）|
| 6 | 不改 `run_predict`（`predict.py` 一行未动）|
| 7 | 04 / 05 / 07 required 字段 byte-stable（已有 `RequiredFieldsByteStableTests` 锁定；新增改动不破坏） |
| 8 | `analysis_date >= "2026-01-01"` 时 features builder 警告 / 拒绝；simulator refusal 仍可见 |
| 9 | 现有测试基线（2393 / 0 failed / 10 skipped）不变 —— 6B.6 / 6B.7 新增测试是净增 |
| 10 | scanner anti-lookahead 测试覆盖（features 计算只读 `analysis_date` 之前的数据）|

## 14. 不做什么

- ❌ 不写 DB cache（候选 D）
- ❌ 不写 file cache（候选 C）
- ❌ 不改 `run_predict` / `predict.py`
- ❌ 不在 UI 临时读 CSV（候选 features C）
- ❌ 不让 helper 内部计算 features（候选 features D）
- ❌ 不保存 `soft_metadata` 到 `prediction_log`（属于 6B.1 候选 C，
  暂不推荐）
- ❌ 不接 4 个 anti-false-exclusion 离线模块到主链
- ❌ 不启用 `hard` / `forced_exclusion` /
  `anti_false_exclusion_triggered`
- ❌ 不升级 04 / 05 / 07 任何 required 字段
- ❌ 不改 `final_projection` / `simulated_trade` / `confidence_system`
  的任何字段
- ❌ 不接 `yfinance` / `requests` / 任何网络
- ❌ 不接 trading API / `longbridge` / `broker` / `paper_trade`
- ❌ 不用 2026-01-01 之后 final test range 调参
- ❌ 不新增任何测试（本文档只是 spec）

## 15. 严守边界

- ❌ 本文档**只是**设计 / spec
- ❌ 没改任何代码
- ❌ 没新增任何测试
- ❌ 没写 DB
- ❌ 没改 DB schema
- ❌ 没接 `yfinance` / `requests` / 任何网络
- ❌ 没接 trading API / `longbridge` / `broker` / `paper_trade`
- ❌ 没改 `predict.py` / `scanner.py` / `prediction_store.py`
- ❌ 没改 `projection_output_adapter.py` / `projection_output_contract.py`
- ❌ 没改 `regime_diagnostics_dashboard.py` / `soft_metadata_simulator.py` /
  `soft_metadata_renderer.py` / `soft_metadata_injection.py` /
  `predict_tab.py`
- ❌ 没改任何 builder（`_build_exclusion_system` /
  `_build_confidence_system` / `_build_simulated_trade` / 任何其他）
- ❌ 没改 `app.py` / 任何其他 `ui/*` 模块
- ❌ 没升级 04 / 05 / 07 任何 required 字段
- ❌ 没启用 `hard` / `forced_exclusion` /
  `anti_false_exclusion_triggered`
- ❌ 没接 4 个 anti-false-exclusion 离线模块到主链
- ❌ 没改 `final_projection` / `confidence_score` / `simulated_trade` /
  `no_trade`
- ❌ 没触碰 2026-01-01 之后 final test range
- ❌ 没运行 replay / 没新写 replay 行
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` /
  `avgo_agent.db.backup_*`
- ✅ 只新增 1 份 markdown 设计文档（本文件）
