# Step 2G-6B.1 — Soft Metadata Injection Path Design

> **设计文档（injection path design），不是实现。** 本文档**冻结**
> Step 2G-6B.2 实现 read-only enrichment helper 时使用的注入路径选择 +
> helper API 形状 + regime_features / baseline 来源策略 + 与 Predict /
> Review / DB / 2026 final test 的关系。
>
> 本轮**不动任何代码**：不改 `predict.py` / `run_predict` /
> `scanner.py` / `prediction_store.py` / `app.py` / `ui/*` /
> `soft_metadata_simulator.py` / `regime_diagnostics_dashboard.py` /
> `soft_metadata_renderer.py` / 任何 builder / DB schema 中的任何
> 一处。

## 1. 背景

- **Step 2G-5** simulator 已实现（commit `947f1c9`）：
  `simulate_soft_metadata` 纯函数 + `build_soft_metadata_baseline`
  SELECT-only baseline builder
- **Step 2G-6A** renderer 已实现（commit `373f358`）：
  `render_soft_metadata_card_data` + `render_soft_metadata_markdown`
  pure-function UI helper
- **Step 2G-6B** Predict 页面 display hook 已实现（commit `33733d3`）：
  `_extract_soft_metadata` 三级查找 + `render_soft_metadata_section`
  thin wrapper；接入位置 Layer 2 ↔ Layer 3
- **当前缺口（Step 2G-6B checkpoint §12 已 honest 列出）**：
  canonical 位置
  `predict_result["contract_payload"]["exclusion_system"]["extras"]["soft_metadata"]`
  目前**几乎从不被填充**。`run_predict` 主链未改；当前 prediction
  无论新旧都不会自动产生 `soft_metadata`，所以 Predict 页面 99%
  时间下隐藏整个区块。
- **本文范围**：只**设计**注入路径（哪种方案最合适、helper 形状、
  regime_features / baseline 来源、边界与不变量），**不**实现。
  Step 2G-6B.2 实施时直接引用本文档 §9 / §10 / §11 / §12 / §18。

## 2. 当前数据流

```
scan_result (含 OHLCV / RS / pattern / 各 layer signal)
       │
       ▼
run_predict(scan_result, research_result, ...)
       │
       ▼
predict_result (含 final_bias / final_confidence / final_projection
                / contract_payload? — adapter 路径写入)
       │
       ▼
contract_payload["exclusion_system"]["extras"]
       │
       ▼
soft_metadata: 通常 missing  ← 这里是当前缺口
       │
       ▼
Predict display hook (_extract_soft_metadata + render_soft_metadata_section)
       │
       ▼
visible=False → hidden 整个 metadata 区块
```

说明：
- ✅ display hook 已能消费（Step 2G-6B）
- ✅ simulator 已能生成（Step 2G-5）
- ❌ 两者尚未连接 —— 没有任何代码路径在 Predict 页面渲染前 / 渲染时
  把 simulator 输出注入到 canonical 位置
- ❌ `run_predict` / `prediction_store` / adapter 也没有任何路径自动
  生成 `soft_metadata`

## 3. 设计目标

| 目标 | 说明 |
|---|---|
| ✅ 让 Predict 页面真实可见 metadata | R4 / residual 触发时显示 card；不触发时按 visibility 矩阵隐藏 |
| ❌ 不改 `run_predict` 主链 | `predict.py` 一行未动 |
| ❌ 不改 04 / 05 / 07 required 字段 | 任何升级仍走 Step 2G-8+ + hard gate |
| ❌ 不写 DB | 注入路径不调 `prediction_store.save_*` 或任何 `INSERT` / `UPDATE` |
| ❌ 不改 `prediction_store` | DB schema / save_prediction 路径 / migration 不变 |
| ❌ 不影响历史 replay | `replay_AVGO_%` 380 行 / 286 paired 不变；`calibration_ready=true` 状态保持 |
| ❌ 不影响 `final_direction` / `final_projection` 显示 | UI 既有渲染路径完全保留 |
| ❌ 不启用 hard / forced | `summary.hard_exclusion_allowed` 永远 `False`（renderer 已锁定）|
| ✅ 最小实现优先 | 单文件 helper + 单测试文件；Predict 接入只需改一行（用 enrichment 输出代替原 predict_result）|

## 4. 候选方案 A：UI-time injection

### 4.1 定义

在 `ui/predict_tab.py` 渲染前（或在 `render_soft_metadata_section` 内
部）：
- 从 `predict_result` 提取 contract payload
- 从 `payload` / `scan_result` / `context` 中提取 `regime_features`
- 调用 `simulate_soft_metadata(...)`
- 得到 `soft_metadata` dict
- **仅用于页面显示**，不回写 `predict_result`，不保存 DB

### 4.2 优点

- 最小改动（只动 `ui/predict_tab.py`）
- 不碰 `run_predict`
- 不碰 DB
- 不污染 contract payload（不写回 `extras`）
- 页面实时可见（每次 render 都调 simulator）

### 4.3 缺点

- UI 层调用 simulator —— 虽然只读，但**职责混杂**（UI 既渲染又计算）
- 如果 `regime_features` 不存在，无法触发 R4 / residual（与 B / C 同
  困境，但 A 没有规范的 features extraction 入口）
- **不进入** `predict_result["contract_payload"]` —— Review 页面 / 后续
  消费者拿不到（每个 surface 各自调一遍 simulator，重复劳动且容易
  drift）
- 单元测试不好做（必须 mock simulator 才能在 UI test 里验证）

### 4.4 结论

- ⚠️ **可作为** Step 2G-6B.2 最小实现候选 —— 但**必须**保证：
  - 不读 DB
  - 不调用 `build_soft_metadata_baseline` 或使用 precomputed static
    baseline（如 cached in `session_state`）
- 不推荐作为长期方案 —— 职责混杂；Review 接入会重复劳动

## 5. 候选方案 B：post-run sidecar enrichment

### 5.1 定义

在 `run_predict` **外层**、UI 接收到 `predict_result` 后：
- 调用 sidecar enrichment function
  `enrich_predict_result_with_soft_metadata(predict_result, ...)`
- 函数返回 `enriched_predict_result`（shallow copy）
- canonical 位置
  `enriched_predict_result["contract_payload"]["exclusion_system"]["extras"]["soft_metadata"]`
  被填充
- **不**保存 DB；**不**改原 `predict_result`

### 5.2 优点

- canonical 位置被填充 —— `_extract_soft_metadata` 走第 1 级查找命中
- Predict / Review / future surfaces **复用同一份** soft_metadata
  （单点生成，多点消费）
- 不改 `run_predict` 内部
- 不写 DB
- helper 是纯函数 / 易测试 / 易 mock simulator
- 入参可以由 UI 决定：是否传 `baseline`、是否传 `regime_features`、
  是否 `force` 重新计算

### 5.3 缺点

- 需要明确 enrichment function 放哪里（建议
  `services/soft_metadata_injection.py`）
- 需要测试不改 required 字段（snapshot diff input vs output）
- 需要解决 `baseline` / `regime_features` 输入（详见 §11 / §12）

### 5.4 结论

- ✅ **推荐**优先方案
- Step 2G-6B.2 应做 read-only enrichment helper
- UI 调 helper，**而不是**直接调 simulator

## 6. 候选方案 C：prediction_store save-time enrichment

### 6.1 定义

在 `services/prediction_store.save_prediction` 内部、写入 DB 之前：
- 自动生成 `soft_metadata` 并落入 `contract_payload_json`

### 6.2 优点

- Review / history / DB 都能看到 metadata
- replay 后可复现（新 replay 行自动带 metadata）
- 单点写入 → 永久持久化

### 6.3 缺点

- ❌ **会写 DB**（每次 save_prediction 都改 `contract_payload_json`）
- ❌ 影响 `prediction_store`（违反 Step 2 全程"不改
  `prediction_store`" 边界）
- ❌ 增加 migration / historical consistency 问题（旧 prediction 没有
  metadata；要不要回填？回填用什么 baseline？）
- ❌ 写入路径需要等 simulator 返回，影响 save 性能（虽然 simulator
  本身快，但 baseline computation 较重）
- ❌ 任何 simulator 内部 bug 会污染 DB
- ❌ 与 Step 2 系列"04 段不进 required" 边界冲突 —— 即使写到 extras
  也算改 contract payload 写入路径

### 6.4 结论

- ❌ **暂不推荐**
- 如果未来要做，必须独立立项 + DB hygiene 评估 + migration 方案 +
  rollback 路径

## 7. 候选方案 D：offline batch enrichment

### 7.1 定义

对历史 `prediction_log` 批量补 `soft_metadata`：
- 写 script `scripts/backfill_soft_metadata.py`
- 遍历所有 prediction → 算 baseline + features + simulator → 写回
  `contract_payload_json`

### 7.2 优点

- 历史数据可补
- dashboard 可分析全 380 replay 的 metadata 分布
- 不影响 `run_predict` / save 路径

### 7.3 缺点

- ❌ **会写 DB**（更新 `contract_payload_json`）
- ❌ 容易污染 replay baseline —— Step 2G-3 / Step 2G-5 数字基于当前
  DB 状态，回填会让"baseline 数字 vs 历史 metadata 一致性"被 simulator
  bug 影响
- ❌ 当前阶段没必要 —— Predict / Review 主要看的是**当下**预测的
  metadata，不是历史

### 7.4 结论

- ❌ **暂不推荐**
- 如果未来要做，必须先冻结 DB snapshot + 确认 simulator 已稳定 +
  独立立项

## 8. 候选方案 E：caller-controlled injection only

### 8.1 定义

不做任何自动注入：
- 只允许外部调用方（测试 / 开发 / 未来其他 surface）自己把
  `soft_metadata` 放进 `predict_result` 或 `session_state`
- Predict display hook 三级查找路径**仍然**找到时显示

### 8.2 优点

- 零风险
- 零代码改动（已是 Step 2G-6B 的现状）

### 8.3 缺点

- ❌ 实际页面**几乎永远不显示** —— 没有自动路径，没有用户会手动
  注入
- ❌ Step 2G-6B 的接入价值无法体现 —— display hook 只对测试 fixture
  可见，对真实用户不可见
- ❌ Review 接入也只能依赖手动注入，价值更小

### 8.4 结论

- ❌ **不推荐**作为长期方案
- 只适合**当前过渡状态**（即 Step 2G-6B 完成 → 6B.2 启动之间的
  短暂过渡）

## 9. 推荐方案

**Step 2G-6B.2 应实施候选方案 B（post-run sidecar enrichment）**：

| 决策 | 内容 |
|---|---|
| 实施位置 | 新增 `services/soft_metadata_injection.py`（service 层；不放 ui/，避免 UI 职责混杂） |
| API 形状 | `enrich_predict_result_with_soft_metadata(predict_result, *, ...)` —— shallow copy + canonical 写入 + 不原地改输入 |
| 不改 | `run_predict` / `prediction_store` / `predict.py` / `scanner.py` / DB schema / 04 / 05 / 07 required 字段 / `final_direction` / `final_projection` / `simulated_trade` |
| helper 输入 | `predict_result` 必填；`scan_result` / `research_result` / `baseline` / `regime_features` / `analysis_date` 全部可选 |
| helper 输出 | enriched shallow copy；canonical 位置 (`extras.soft_metadata`) 被填充；其他字段 byte-stable |
| UI 接入 | `app.py` / `ui/predict_tab.py` 在调 `render_predict_tab` 之前调一次 helper；display hook 沿用 Step 2G-6B 的三级查找（canonical 位置已被填充 → 第一级命中）|
| 不写 DB | helper 不调 `prediction_store` / `init_db` / 任何 SQL writer |
| 不改 review | Step 2G-6C Review 接入是独立步；helper 输出可被 Review 复用，但本步不改 `review_log` |
| 兼容 already-set | 若 `extras.soft_metadata` 已存在（例如未来 simulator 直接写入），helper 默认**不覆盖**；显式 `force=True` 才覆盖 |

## 10. Enrichment helper 初步设计

> 这是 Step 2G-6B.2 实施时**必须遵守**的接口形状。任何偏离都视为
> 实施 bug，应该回到本文档重新审议。

```python
def enrich_predict_result_with_soft_metadata(
    predict_result: dict,
    *,
    scan_result: dict | None = None,
    research_result: dict | None = None,
    baseline: dict | None = None,
    regime_features: dict | None = None,
    analysis_date: str | None = None,
    force: bool = False,
    final_test_cutoff: str = "2026-01-01",
) -> dict:
    """Sidecar enrichment for predict_result.

    - Returns a shallow copy with
      ``result['contract_payload']['exclusion_system']['extras']['soft_metadata']``
      filled. Does NOT mutate input.
    - When ``predict_result`` already has soft_metadata at the canonical
      path, returns it unchanged unless ``force=True``.
    - When ``regime_features`` is None, attempts to read from
      ``predict_result['regime_features']`` /
      ``scan_result['regime_features']`` /
      ``scan_result['extras']['regime_features']`` (extraction order); if
      none found, calls simulator with ``regime_features=None`` so the
      simulator emits ``signals=[]`` + ``missing_regime_features`` warning.
    - When ``baseline`` is None, calls simulator with ``baseline=None``
      so the simulator emits ``signals`` (without historical metrics) +
      ``missing_baseline`` warning. Helper does NOT call
      ``build_soft_metadata_baseline`` itself (no DB read).
    - Does NOT modify any 04 / 05 / 07 required field.
    - Does NOT write DB.
    - Pure function (modulo simulator I/O guarantees, which are also
      pure when called this way).
    """
```

### 10.1 不变量

- ❌ helper **不**原地修改输入（shallow copy 后写入）
- ❌ helper **不**调用 `build_soft_metadata_baseline`（除非 caller 显式
  传入 baseline，本设计也允许 future enhancement 让 caller 在
  `app.py` 启动时 build 一次 baseline 缓存到 `session_state`，但
  helper 自身永远不主动读 DB）
- ❌ helper **不**改 04 / 05 / 07 required 字段（snapshot 测试锁定：
  input.required_fields == output.required_fields byte-by-byte）
- ❌ helper **不**写 DB / 不接网络 / 不接 trading API
- ❌ helper **不** import `prediction_store` / `yfinance` / `requests`
- ✅ helper **必传** `analysis_date` 给 simulator（让 simulator 处理
  2026 cutoff）—— 默认从 `predict_result['contract_payload']['current_structure']['analysis_date']`
  读取
- ✅ helper 永远返回 dict；从不 raise（任何错误经 `summary.warnings`
  + 写入空 metadata 两种方式表面化）
- ✅ helper 调 simulator 时**只**用 caller-injected baseline 模式
  （Step 2G-4.5 §7.1 / §7.2 推荐路径）

## 11. regime_features 来源设计

### 11.1 理想态（未来）

上游 `scan_result` 直接提供：
- `scan_result['regime_features'] = {'pos20': 0.81, 'avgo_minus_soxx_20d': 7.3}`

这需要 `scanner.py` 主动计算并暴露这两个 feature。**当前 scanner.py
是否已经计算 pos20 / avgo_minus_soxx_20d 不在本设计的扫描范围**——
如果未计算，需要独立任务（Step 2G-6B.2-prereq）扩展 scanner 输出，
但**不**在 Step 2G-6B.2 范围内强制要求。

### 11.2 当前 fallback（Step 2G-6B.2 必须支持）

helper 按以下顺序查找；任意一级命中即用：

| # | 来源 | 用途 |
|---|---|---|
| 1 | 显式 `regime_features=` kwarg | caller 完全控制 |
| 2 | `predict_result['regime_features']` | 未来 `run_predict` 自己暴露时使用 |
| 3 | `scan_result['regime_features']` | 未来 `scanner` 自己暴露时使用 |
| 4 | `scan_result['extras']['regime_features']` | 备用 extras 子 dict 位置 |

任何一级都没有 → `regime_features=None` 传给 simulator → simulator
emit `signals=[]` + `missing_regime_features` warning → renderer 在
predict context 隐藏（因为 `signals=[]`）。

### 11.3 强约束

- helper **不**在 Step 2G-6B.2 中从 CSV / DB 计算 regime_features ——
  那是 `scanner` / `regime_diagnostics_dashboard` 的责任
- helper **不**接 `yfinance` / `requests` 来算 features
- 如果 features 缺失，UI 显示 nothing —— 用户体验上等同于"6B.2 之前
  的状态"，但代码路径已就位，等 scanner 升级后即可自动看到 metadata

## 12. baseline 来源设计

### 12.1 preferred: caller-injected baseline

- `app.py` 启动时调一次 `build_soft_metadata_baseline()` 算 baseline
- 缓存到 `st.session_state["soft_metadata_baseline"]`
- 每次 `render_predict_tab` 调 helper 时传 `baseline=st.session_state.get("soft_metadata_baseline")`
- TTL：建议 baseline 一天刷新一次（DB 内每天最多新增几条 replay；
  baseline 不会大幅变动）

### 12.2 helper 默认 `baseline=None` 也能工作

- 不传 baseline → simulator 仍 emit signals（基于 `regime_features`
  触发判断）
- `historical_metrics_in_sample` 为 `{}`
- `summary.warnings` 含 `missing_baseline`
- renderer 仍渲染 card，metrics 显示 `n/a`

这意味着 Step 2G-6B.2 实施时**不需要**强制 caller 提前 build baseline；
helper 在 baseline 缺失时只是降级到"不显示历史指标"，不 crash。

### 12.3 强约束

- helper **不**主动调 `build_soft_metadata_baseline`（避免 UI 渲染时
  阻塞读 DB）
- baseline 缓存策略由 `app.py` / `session_state` 决定，**不**在 helper
  内部
- 测试需覆盖 `baseline=None` 路径（已是 simulator 测试矩阵的一部分；
  helper 测试只需 assert 透传）

## 13. 与 Predict / Review 的关系

### 13.1 Predict 页面

```
app.py / render_predict_tab(scan_result, research_result):
    predict_result = run_predict(scan_result, research_result)
    # ↓ Step 2G-6B.2 新增一行
    enriched = enrich_predict_result_with_soft_metadata(
        predict_result,
        scan_result=scan_result,
        research_result=research_result,
        baseline=st.session_state.get("soft_metadata_baseline"),  # 可选
    )
    # ↓ Step 2G-6B 已有的 display hook 自动命中 canonical 路径
    render_soft_metadata_section(_extract_soft_metadata(enriched))
```

### 13.2 Review 页面

- Step 2G-6C 接入时**复用** enriched result（如果 review 能拿到
  enriched 版本）
- 或者：Review 页面也调一次 `enrich_predict_result_with_soft_metadata`
  把历史 prediction 的 contract_payload 加 metadata —— 仅用于显示，
  **不**回写 `prediction_log`、**不**改 `review_log` required
- Review 页面归因维度按 Step 2G-6 §8 4 种组合规则写入
  `review_log.confidence_note` / `watch_for_next_time` free-text 字段
  （Step 2G-6 / 2G-6A checkpoint 已固化）

### 13.3 阶段性限制（接受）

- 若不保存 DB，Review 历史页面**仍拿不到过去 soft_metadata** ——
  这是可接受的阶段性限制，因为：
  - 历史 prediction 的 `contract_payload_json` 不含 metadata；
    Review 显示需要 enrichment 才能看到
  - 如果 enrichment 重新基于当前 baseline / current scanner features 计算，
    可能与"当时"的实际场景有偏差（features 是基于历史 OHLCV，但
    baseline 是当前 DB 的 regime stats）
- 这个 trade-off 文档化即可，**不**为此做 save-time enrichment（候选
  方案 C）—— 后者代价太高

## 14. 与 DB / replay 的关系

- Step 2G-6B.2 helper **不写 DB**（无 `INSERT` / `UPDATE` / `DELETE`）
- **不回填** replay（无 batch 路径）
- **不改** `prediction_log` schema / 行内容
- **不影响** Step 2G-3 / Step 3D-1 的 380 replay / 286 paired baseline
  数字（baseline 仍来自现有 DB；helper 只在 UI 渲染时消费）
- 任何 save-time / batch enrichment（候选方案 C / D）必须**另立任务** +
  DB hygiene 评估 + migration 方案

## 15. 与 2026 final test cutoff

- enrichment helper **必须**把 `analysis_date` 传给
  `simulate_soft_metadata`：
  - 默认从
    `predict_result['contract_payload']['current_structure']['analysis_date']`
    读取
  - caller 可显式 override（测试用）
- `analysis_date >= "2026-01-01"` 时 simulator 已经 refusal +
  `final_test_range_refusal` warning（Step 2G-5 锁定）
- helper **不得**用 2026 final test 数据调参 / 反复跑（caller 可
  显式跨过 cutoff，但 simulator 会拒绝；helper 自身不绕过）
- 继续遵守 2026-01-01 之后为最终测试集；任何 2026 数据不进入
  baseline / 不做任何回归 / dashboard 显示明确 refusal

## 16. 下一步实施建议

按推荐优先级：

| # | 步骤 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **Step 2G-6B.2** read-only enrichment helper + tests | 新增 `services/soft_metadata_injection.py` + `tests/test_soft_metadata_injection.py`；按 §10 API 形状；测试覆盖 §10.1 不变量 + §11 / §12 来源策略 + §15 cutoff 透传 | **高**（本文档天然延续；零风险） |
| 2 | **Step 2G-6B.3** Predict 页面调用 helper | 在 `app.py` / `ui/predict_tab.py` `run_predict` 之后调一行 helper；display hook 沿用 Step 2G-6B 三级查找；如果 baseline 缓存策略需要，加 `session_state` 缓存逻辑 | **高**（与 #1 同 step 完成最佳） |
| 3 | **Step 2G-6C** Review 页面接入 | 复用 enriched 结果或对历史 prediction 调 helper；context="review"；归因写入 `review_log` free-text | 中（Predict 接入稳定后再做） |
| 4 | **Step 2G-6D** AppTest 扩展 | Predict AppTest 升级到使用真实 enrichment 路径（仍 mock simulator）；Review 接入完成后扩展 review AppTest | 中-低（与 #2 / #3 配套）|
| 5 | **不建议**直接做 prediction_store save-time enrichment（候选 C） | 写 DB + migration + 性能影响 + 历史一致性问题；当前阶段不必要 | — |
| 6 | **不建议**直接做 offline batch enrichment（候选 D） | 写 DB + 污染 baseline 风险 | — |
| 7 | **不建议**直接做 UI-time injection（候选 A）| 职责混杂；Review 重复劳动 | — |

## 17. 不做什么

- ❌ 不改 `run_predict` / `predict.py`
- ❌ 不改 `scanner.py`（`regime_features` extraction 是 fallback；
  scanner 升级是独立任务）
- ❌ 不写 DB / 不改 DB schema
- ❌ 不改 `prediction_store`（save_prediction 路径不变）
- ❌ 不保存 `soft_metadata` 到 `prediction_log` / `outcome_log` /
  `review_log`
- ❌ 不接 trading API / `longbridge` / `broker` / `paper_trade`
- ❌ 不接 `yfinance` / `requests` / 任何网络
- ❌ 不启用 `hard` / `forced_exclusion` /
  `anti_false_exclusion_triggered`
- ❌ 不升级 04 `exclusion_system` 5 个 required 字段
- ❌ 不升级 05 `confidence_system` 4 个 score 字段 / `event_score`
- ❌ 不升级 07 `simulated_trade` 6 个决策字段
- ❌ 不改 `final_projection` / `final_direction` / `final_five_state`
- ❌ 不接 4 个 anti-false-exclusion 离线模块到主链
- ❌ 不用 2026-01-01 之后 final test range 调参
- ❌ 不新增任何测试（本文档只是 spec）

## 18. 成功标准

未来若实施 Step 2G-6B.2 必须满足：

| # | 标准 |
|---|---|
| 1 | canonical 位置 `enriched["contract_payload"]["exclusion_system"]["extras"]["soft_metadata"]` 被填充 |
| 2 | input `predict_result` **不被原地修改**（snapshot diff before vs after = byte-stable）|
| 3 | required 字段 byte-stable（04 / 05 / 07 required + `final_projection.*` 在 enrichment 前后完全一致）|
| 4 | `baseline=None` 不 crash（warning 经 `summary.warnings` 表面化）|
| 5 | `regime_features` 缺失（任何一级查找都没命中）→ simulator emit `signals=[]` + `missing_regime_features` warning；不 crash |
| 6 | already-exists 不覆盖（`extras.soft_metadata` 已存在 → 直接返回，除非 `force=True`）|
| 7 | **no DB writes**（helper 模块无 `init_db` / `INSERT` / `UPDATE` / `DELETE` / `prediction_store.save_*` / `_get_conn`；测试 `patch` 锁定）|
| 8 | **no simulator baseline build**（helper 不调 `build_soft_metadata_baseline`；测试 `patch` 锁定）|
| 9 | 2026 refusal visible（`analysis_date >= "2026-01-01"` → renderer 强制 visible 显示 refusal subtitle）|
| 10 | Predict 页面**真实显示** metadata when features supplied（manual fixture or 未来 scanner 升级后）|
| 11 | 现有测试基线（2360 / 0 failed / 10 skipped）不变 —— Step 2G-6B.2 新增测试是净增 |

## 19. 严守边界

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
  `soft_metadata_renderer.py` / `predict_tab.py`
- ❌ 没改任何 builder（`_build_exclusion_system` /
  `_build_confidence_system` / `_build_simulated_trade` / 任何其他）
- ❌ 没改 `app.py` / `ui/*` 任何模块
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
