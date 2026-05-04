# Step 1 — Contract Pipeline Summary

> 状态：Step 1A–1K 已完成。Step 1A–1J 已 merge 进 main；Step 1K（symbol filter）已实现并通过测试，pending commit。
> 范围：本文件只是 **handoff 文档**，不改任何业务代码、不改 UI、不改 `run_predict`。

## 1. 完成了什么（Step 1A–1K 列表）

| Step | 主题 | 产出 |
|---|---|---|
| 1A | 输出契约设计冻结 | `tasks/step_1a_projection_output_contract.md` 定义 8 段 top-level section、字段、枚举值、`null` 语义；不实现业务逻辑 |
| 1B | contract validator | `services/projection_output_contract.py` — `CONTRACT_SECTIONS` / `validate_projection_output()` / 字段 + 枚举校验，纯函数、不抛 |
| 1C | predict_result → contract adapter | `services/projection_output_adapter.py` — `adapt_projection_output()` 把现有 `predict_result` 适配到 8 段 contract，不改主链 |
| 1D | DB 增列 contract_payload_json | `prediction_log.contract_payload_json TEXT NULL`，`prediction_store.save_prediction(...)` 接 `contract_payload=` 旁路，向下兼容 |
| 1E | save_prediction 旁路 auto-gen | save 路径自动 `adapt → validate → 仅在 valid 时持久化 contract_payload_json`；validate 失败不阻断主流程 |
| 1F | （并入 1B/1C/1D 一次提交）|（commit `be097e7 feat(contract): add projection output contract pipeline`）|
| 1G | inspect 工具 | `services/contract_payload_inspector.py` + `scripts/inspect_latest_contract_payload.py` — 只读最新一条 contract_payload_json |
| 1H | diff 工具 | `services/contract_payload_diff.py` + `scripts/diff_latest_contract_payloads.py` — 只读最近两条 contract_payload diff |
| 1I | trend 工具 | `services/contract_payload_trend.py` + `scripts/summarize_recent_contract_payloads.py` — 只读最近 N 条 contract 关键字段趋势 |
| 1J | outcome × contract 相关性 | `services/contract_outcome_correlation.py` + `scripts/correlate_contract_outcomes.py` — 只读 prediction × outcome join，按 contract 字段分桶算 hit-rate |
| 1K | symbol 过滤 | 给 `correlate_outcomes_with_contract(...)` 加 `symbol` 参数（默认 `"AVGO"`，`"ALL"` / `None` 不过滤，空串回退 AVGO，strip + upper），script 加 `--symbol`，结果加 `symbol_filter` 键 |

## 2. 当前 main 状态

- 最新 main commit（Step 1J）：`e2ece6b feat(contract): add read-only outcome contract correlation tool`
- Step 1K：实现已完成，本地 worktree 通过测试，**尚未 commit / 未进 main**。预计提交后 main 头部即为 Step 1K。
- 测试基线（worktree 含 1K）：**1883 passed / 0 failed / 10 skipped**（Step 1J 时基线为 1870 / 0 / 10）
- 已进 main 的内容：
  - `tasks/step_1a_projection_output_contract.md`（contract 设计）
  - `services/projection_output_contract.py`（validator）
  - `services/projection_output_adapter.py`（adapter）
  - `services/prediction_store.py`：`contract_payload_json` 列、`contract_payload=` 参数、save 旁路 auto-gen
  - `services/contract_payload_inspector.py` + `scripts/inspect_latest_contract_payload.py`
  - `services/contract_payload_diff.py` + `scripts/diff_latest_contract_payloads.py`
  - `services/contract_payload_trend.py` + `scripts/summarize_recent_contract_payloads.py`
  - `services/contract_outcome_correlation.py` + `scripts/correlate_contract_outcomes.py`
  - 上述每个模块对应的 `tests/test_*.py`

## 3. contract 标准输出结构（8 段）

`run_predict(...)` 的目标输出形态由 contract 锁定为单层 dict，固定 8 个顶级 section（顺序固定）：

1. `current_structure` — 当前结构（scanner / 数据层）
2. `avgo_primary_projection` — AVGO 近 15 日主推演（主推演引擎）
3. `peer_confirmation_adjustment` — NVDA / SOXX / QQQ 同行确认修正（同行修正层）
4. `exclusion_system` — 否定系统（exclusion / contradiction）
5. `confidence_system` — 置信度系统（confidence engine）
6. `final_projection` — 最终推演结论（收口层）
7. `simulated_trade` — 模拟交易建议（模拟交易决策层）
8. `review_payload` — 复盘字段（review / outcome 接口）

字段集、枚举值、`null` 语义见 `tasks/step_1a_projection_output_contract.md` 与 `services/projection_output_contract.py`。**主链路只读 contract 内字段；扩展只允许往各 section 的 `extras` 里加。**

## 4. 当前数据流

```
scan_result / research_result / predict_result
    │
    ▼
adapt_projection_output()        ← services/projection_output_adapter.py
    │
    ▼
validate_projection_output()     ← services/projection_output_contract.py
    │  (valid 才落库；invalid → 主流程不阻断，contract_payload_json = NULL)
    ▼
save_prediction(... contract_payload_json)   ← services/prediction_store.py 旁路
    │
    ▼
prediction_log.contract_payload_json  (TEXT NULL)
    │
    ├──► inspect       (services/contract_payload_inspector.py)
    ├──► diff          (services/contract_payload_diff.py)
    ├──► trend         (services/contract_payload_trend.py)
    └──► outcome × contract correlation  (services/contract_outcome_correlation.py)
```

所有 4 个工具：**只读**，不写 DB / 不写日志 / 不改 UI / 不改 `run_predict`。

## 5. 已有工具

### Service 层（`services/`）
- `projection_output_contract.py` — `CONTRACT_SECTIONS`、`validate_projection_output()`、字段 + 枚举校验
- `projection_output_adapter.py` — `adapt_projection_output()` 把 `predict_result` 适配到 8 段 contract
- `contract_payload_inspector.py` — 最新一条 contract_payload_json 的只读 inspect
- `contract_payload_diff.py` — 最近两条 contract_payload 字段级 diff
- `contract_payload_trend.py` — 最近 N 条 contract 关键字段趋势
- `contract_outcome_correlation.py` — prediction × outcome join，按 contract 字段分桶 hit-rate（Step 1K：可按 symbol 过滤）

### CLI（`scripts/`）— 全部只读，stdout JSON
- `inspect_latest_contract_payload.py`
- `diff_latest_contract_payloads.py`
- `summarize_recent_contract_payloads.py`
- `correlate_contract_outcomes.py`（Step 1K：`--symbol AVGO|ALL|<TICKER>`）

## 6. 当前仍未做（Step 1 范围之外，需要在后续 step 处理）

- ❌ 没有重构 `run_predict`（仍然是旧两步结构）
- ❌ 没有改 UI（Predict / History / Review tab 仍然只读旧 `predict_result`，不读 contract）
- ❌ 没有接长桥（实时行情仍走 yfinance）
- ❌ 没有接新闻 / 财报
- ❌ 没有真正稳定推演系统（`avgo_primary_projection` 字段还来自旧 adapter，不是稳定推演引擎）
- ❌ 没有真正稳定否定系统（`exclusion_system` 段仍然是 stub / 由 adapter 拼装，未真正接 risk_model）
- ❌ 没有真正稳定置信度系统（`confidence_system` 段同上，未真正接 confidence_engine）
- ❌ PR-B（risk model）/ PR-C（contradiction）/ PR-D（confidence）的 v1 stub 仍**未接入主链**，contract 段值靠 adapter 兜底
- ❌ contract 与旧 `predict_result` 的**字段一致性回归**已部分覆盖（见 §8 Step 2B-1），但 `avgo_primary_projection` / `peer_confirmation_adjustment` / `final_projection` 内部字段语义对齐尚未做

## 7. 下一步 Step 2 建议路线（推演系统稳定化）

| Step | 主题 | 范围（最小改动原则） | 状态 |
|---|---|---|---|
| 2A | 核验现有 `run_predict` 两步结构 | 只读诊断；判定为"部分两步化"——骨架在，但 contract 5 段（02/03/04/05/07）多数靠 adapter 兜底 | ✅ 已完成（无代码改动，仅诊断报告） |
| 2B-1 | contract alignment 安全网 + 文档对齐 | 加 `tests/test_run_predict_contract_alignment.py` 锁住 run_predict → adapter → validator 链；标注 `data_window_days` 已知不一致；不改任何业务代码 | ✅ 本轮 |
| 2B-2 | 在 builder 内补 02 段 contract 字段 | 让 `build_primary_projection` 直接产出 02 contract 字段；adapter 退化为直通；包括统一 `data_window_days` ↔ `lookback_days`（消除 §8 不一致） | 待办 |
| 2B-3 | 在 builder 内补 03 段 contract 字段 | 让 `apply_peer_adjustment` 直接产出 03 contract 字段（三个 peer signal / alignment / adjustment 等） | 待办 |
| 2C | 同行确认修正层稳定化 | peer signal / alignment / adjustment 的判定规则、退化条件，独立子模块化 | 待办 |
| 2D | `final_projection` 输出对齐 contract | 收口层只输出 contract 字段；adapter 退化为直通 + validate | 待办 |
| 2E | 只读对比旧输出与 contract 输出 | 跑双输出 diff，用 Step 1 inspect/diff/trend 工具，不破坏主链路 | 待办 |

每一个子步骤都遵循 Step 1 已经验证过的工作模式：

1. 先写 contract / 设计文档冻结输出
2. 加只读工具验证
3. 旁路写库，不阻断主流程
4. 严格不改 `run_predict` / UI / risk_model.py / contradiction_engine.py / confidence_engine.py，除非该子步骤明确包含

## 8. `data_window_days` 联动（Step 2B-1 暴露 → Step 2B-2 修复）

> 详见 [tasks/step_1a_projection_output_contract.md](step_1a_projection_output_contract.md) §8。

**当前状态（已联动）：**

| 位置 | 值 |
|---|---|
| `predict.py` `_PRIMARY_LOOKBACK_DAYS` | `20` |
| `predict_result["primary_projection"]["lookback_days"]` | `20` |
| `contract_payload["current_structure"]["data_window_days"]` | `20`（adapter 从 primary_projection 读取） |

`tests/test_run_predict_contract_alignment.py::test_contract_data_window_days_matches_primary_lookback` 锁住两值相等且 = 20。Step 2B-1 时期的"显式不等"临时 case 已删除。

**Step 2B-2 一并落地的字段化（02 段）：**

`build_primary_projection()` 的输出 dict 现在直接含 contract 02 段所需 8 个字段：
`primary_direction` / `open_projection` / `intraday_path_projection` / `close_projection` / `five_state_projection` / `historical_sample_count` / `key_evidence` / `primary_confidence_raw`。

`tests/test_primary_projection_contract_fields.py` 锁住字段存在性、contract 枚举合规、bullish/bearish/unavailable 三种分支取值。**未改任何推演判定逻辑**（`final_bias` / `final_confidence` / `score` 计算路径不变）。

## 9. peer_adjustment 自发布 contract 03 段（Step 2B-3）

`apply_peer_adjustment()` 的输出 dict 现在直接含 contract 03 段所需 8 个字段：
`peer_symbols` / `nvda_signal` / `soxx_signal` / `qqq_signal` / `peer_alignment` / `peer_adjustment` / `adjusted_direction` / `adjustment_reason`。

字段语义全部 **bias-aware**：每个 peer 的 signal 由 primary_bias 与该 peer 的相对强度共同决定（`confirm` → `reinforce`，`oppose` → `weaken`，`mixed` → `neutral`，`unavailable` → `unknown`）；这与 Step 1C 时期 adapter 的"方向无关"翻译相比，更准确地表达"该 peer 是支持还是削弱主推演方向"。

**adapter 优先级（[services/projection_output_adapter.py](../services/projection_output_adapter.py) `_build_peer_confirmation_adjustment`）：**
1. 如果 `predict_result["peer_adjustment"]` 自带 contract 03 字段且取值在 contract 枚举内，**直接使用**。
2. 否则回退到 Step 1C 旧推导（从 `scan_result.relative_strength_summary` 标签 + `confirm_count` / `oppose_count` 推），保证旧 payload 仍合规。
3. 取值不在合法枚举内（如外部上游写脏数据）也走 fallback，不污染 contract 输出。

**legacy 字段全部保留**（`adjustments` / `confirm_count` / `oppose_count` / `adjustment_direction` / `adjusted_bias` / `adjusted_confidence` / `notes` 等），仅做加法。

**未改：** peer 投票规则、`adjusted_bias` / `adjusted_confidence` 升降条件、`adjustment_direction` 推导逻辑、`final_bias` 生成策略。

`tests/test_peer_adjustment_contract_fields.py` + `tests/test_projection_output_adapter.py`（新增 3 case：self-published 优先 / legacy fallback / 非法枚举回退）共同锁住该层。

## 10. final_projection 自发布 contract 06 段（Step 2B-4）

`build_final_projection()` 的输出 dict 现在直接含 contract 06 段所需 8 个字段：
`final_direction` / `final_open_projection` / `final_intraday_path` / `final_close_projection` / `final_five_state` / `probability_bucket` / `key_price_levels` / `final_one_sentence`。

字段来源完全从已有 final 决策派生，没有引入任何外部信息源：
- `final_direction` ← `final_bias`（中文翻译）
- `final_open_projection` / `final_intraday_path` / `final_close_projection` ← `_pred_labels(open_tendency, close_tendency)` 输出（`pred_open` / `pred_path` / `pred_close`）经 contract 翻译（含"平收 → 收平"修正）
- `final_five_state` ← 保守规则（偏多+收涨→小涨；偏空+收跌→小跌；其余震荡）
- `probability_bucket` ← `final_confidence` 映射（high → ≥70%；medium → 55–70%；low → 45–55%）
- `key_price_levels` ← `{}`（暂无稳定来源，**不编造支撑阻力**）
- `final_one_sentence` ← 现有 `prediction_summary`，与同一 dict 里的 `prediction_summary` 完全一致

**adapter 优先级（[services/projection_output_adapter.py](../services/projection_output_adapter.py) `_build_final_projection`）：**
1. 如果 `predict_result["final_projection"]` 自带 contract 06 字段且取值在 contract 枚举内（含 `key_price_levels` 是 `dict`、`final_one_sentence` 是非空 `str`），**直接使用**。
2. 否则回退到 Step 1C 旧推导（从 top-level `final_bias` / `pred_open` / `pred_path` / `pred_close` / `final_confidence` / `prediction_summary` 推），保证旧 payload 仍合规。
3. 取值非法（如 `final_direction = "totally-bogus"` / `key_price_levels = "not-a-dict"`）也走 fallback，不污染 contract 输出。

**legacy 字段全部保留**（`final_bias` / `final_confidence` / `pred_open` / `pred_path` / `pred_close` / `prediction_summary` / `supporting_factors` / `conflicting_factors` / `notes` / `path_risk` / `peer_path_risk_adjustment` 等），仅做加法。

**未改：** `final_bias` 计算（peer.adjusted_bias 退化路径）、`final_confidence` 计算（peer.adjusted_confidence 退化路径）、`_apply_research_adjustment` 路径、`path_risk` 推导、`prediction_summary` 内容、unavailable 分支触发条件。

`tests/test_final_projection_contract_fields.py` + `tests/test_projection_output_adapter.py`（新增 3 case：self-published 优先 / legacy fallback / 非法值回退）共同锁住该层。

## 11. 当前 contract 段进度总览

| Section | 状态 | 由谁产出 |
|---|---|---|
| 01 `current_structure` | 字段化 | adapter 从 scan + `primary_projection.lookback_days` 构造（Step 2B-2） |
| 02 `avgo_primary_projection` | **字段化** | `build_primary_projection` self-publish（Step 2B-2） |
| 03 `peer_confirmation_adjustment` | **字段化** | `apply_peer_adjustment` self-publish（Step 2B-3） |
| 04 `exclusion_system` | ⚠️ required 仍占位 + `extras` 暴露真实风险信号（Step 2C-2） | adapter 5 必填字段 stub + `extras` 读取 `predict_result.conflicting_factors / path_risk / peer_path_risk_adjustment` |
| 05 `confidence_system` | ⚠️ 4 个 score 仍占位 + `extras` 暴露 raw score-like 信号（Step 2C-3b） | adapter `historical_score / structure_score / peer_score / exclusion_penalty = 0.0`、`event_score = None` 不变；`confidence_level / total_confidence / confidence_reason` 真值；`extras` 读取 `primary_projection.score / 三层 confidence / peer 计数 / probability_bucket / conflicting_factors / path_risk` |
| 06 `final_projection` | **字段化** | `build_final_projection` self-publish（Step 2B-4） |
| 07 `simulated_trade` | ⚠️ 6 决策字段 pinned + `no_trade_reason` 升级静态诚实文本 + `extras` 暴露 trade-relevant 观察信号（Step 2D-2） | adapter `trade_action="no_trade" / trade_direction="none"` 等 6 字段 pinned；`no_trade_reason` 静态指向 06/05；`extras` 读取 `final_projection / final_confidence / path_risk / conflicting_factors`；**`trade_engine_enabled = False` 常量** |
| 08 `review_payload` | 字段化（依赖 06） | adapter 从 final 字段派生 |

**已完成：** 02 / 03 / 06 三段由 builder 自发布，adapter 退化为"先信 self-published、再回退老推导、非法值不污染输出"。`run_predict` 主决策路径（投票 / 升降 / 收口）一行未改。Step 2C-2 / 2C-3b / 2D-2 让 04 / 05 / 07 三段在保持 required 字段语义不变的前提下，把已有风险信号 / score-like 信号 / trade-relevant 观察信号暴露到各自的 `extras`。

**仍未做：** 04 段的 required 字段（`exclusion_level / forced_exclusion / anti_false_exclusion_triggered`）尚未真正字段化；05 段的 4 个 score 字段（`historical_score / structure_score / peer_score / exclusion_penalty`）+ `event_score` 尚未真正字段化；07 段的 6 个决策字段（`trade_action / trade_direction` 等）按设计**永不动**——本项目策略禁止开仓建议。这些都需要**真正的子系统**（否定模块 / calibration 引擎 / 交易决策层）落地，不是字段填充。

## 12. exclusion_system extras（Step 2C-2，仅暴露不决策）

`services/projection_output_adapter.py::_build_exclusion_system(predict)` 现在做两件事：

1. **5 个 contract 必填字段保持 "no exclusion observed" stub**：
   `exclusion_level == "none"` / `exclusion_sources == []` / `exclusion_reasons == []` / `forced_exclusion is False` / `anti_false_exclusion_triggered is False`。
   语义零变化——任何下游消费者按"没有否定"理解都仍然正确。
2. **新增 `extras` 子 dict**，把 `predict_result` 已经产出的风险信号原样暴露出来：

| extras 键 | 类型 | 来源（仅读 predict_result） |
|---|---|---|
| `conflicting_factors_count` | int | `len(predict["conflicting_factors"])`（非 list 时回退 0） |
| `conflicting_factors` | list[str] | `predict["conflicting_factors"]` 副本（非 list 时回退 `[]`） |
| `path_risk_level` | str | `predict["path_risk"]`（缺失 → `"unknown"`） |
| `peer_path_risk_direction` | str | `predict["peer_path_risk_adjustment"]["risk_direction"]`（缺失或非 dict → `"unknown"`） |
| `peer_path_risk_reasons` | list[str] | `predict["peer_path_risk_adjustment"]["reasons"]` 副本（缺失或非 list → `[]`） |
| `soft_signal` | str | 启发式标签（`"peer_weaken"` / `"high_path_risk"` / `"none"`），**不**反向影响 required 字段 |

**`soft_signal` 决策树**（仅观察、不否定）：
- 若 `"peer_confirmation=weaken" in conflicting_factors` → `"peer_weaken"`
- 否则若 `path_risk_level == "high"` → `"high_path_risk"`
- 否则 → `"none"`

**严守边界（Step 2C-2 没做的事）：**
- ❌ 没接 `risk_model.py` / `contradiction_engine.py` / `confidence_engine.py` 三个 v1 stub
- ❌ 没接 `big_up_contradiction_card` / `exclusion_reliability_review` / `big_down_tail_warning` / `anti_false_exclusion_audit` 到主链
- ❌ 没改 `predict.py` / `run_predict` / UI / `prediction_store` / contract validator
- ❌ `exclusion_level` 仍是 `"none"`；`forced_exclusion` / `anti_false_exclusion_triggered` 仍是 `False`
- ❌ `extras` 完全只读派生，不参与任何决策；下游不应据 `soft_signal` 做"是否预测"的判断

**真正的 04 字段化**（让 `exclusion_level` 在合适时升 `"soft"`/`"hard"`、让 `forced_exclusion=True` 有真实触发条件、`exclusion_sources` / `exclusion_reasons` 有结构化来源）留给 Step 2C-3+，需先有真实否定模块。

`tests/test_exclusion_system_contract_fields.py`（18 case + 3 subtests）+ `tests/test_projection_output_adapter.py`（新增 1 case）锁住"required 不动、extras 反映 predict_result"。

## 13. confidence_system extras（Step 2C-3b，仅暴露不评分）

`services/projection_output_adapter.py::_build_confidence_system(predict)` 现在做三件事：

1. **4 个 score 字段保持 0.0、`event_score` 保持 `None`**：
   `historical_score == 0.0` / `structure_score == 0.0` / `peer_score == 0.0` / `exclusion_penalty == 0.0` / `event_score is None`。
   语义零变化——任何下游消费者按"分数未启用"理解都仍然正确。
2. **3 个真值字段保持原有语义**：
   `confidence_level` 来自 `predict["final_confidence"]`（经 `_normalize_confidence`）；`total_confidence` 来自三档映射（high→0.75，medium→0.50，low→0.25）；`confidence_reason` 来自 `predict["prediction_summary"]`。
3. **新增 `extras` 子 dict**，把 `predict_result` 已经产出的 score-like 信号原样暴露：

| extras 键 | 类型 | 来源（仅读 predict_result） |
|---|---|---|
| `primary_score_raw` | float \| None | `predict["primary_projection"]["score"]`（不可转 float → `None`）；**未归一化**，下游不能当 `structure_score` 用 |
| `primary_confidence_raw` | str enum \| `"unknown"` | `primary_projection.primary_confidence_raw` 优先，回退 `primary_projection.final_confidence`；非合法枚举 → `"unknown"` |
| `peer_confirm_count` | int | `peer_adjustment.confirm_count`（缺失或不可转 → 0） |
| `peer_oppose_count` | int | `peer_adjustment.oppose_count`（同上） |
| `peer_adjusted_confidence` | str enum \| `"unknown"` | `peer_adjustment.adjusted_confidence`；非合法 → `"unknown"` |
| `final_confidence` | str enum \| `"unknown"` | `predict["final_confidence"]`；非合法 → `"unknown"`（**与 required `confidence_level` 不同**：required 把非法值 coerce 成 `"low"`，extras 更诚实地保留 `"unknown"` 让原始问题可见） |
| `probability_bucket` | str enum \| `"unknown"` | `predict["final_projection"]["probability_bucket"]`；非合法 → `"unknown"` |
| `conflicting_factors_count` | int | `len(predict["conflicting_factors"])`（非 list → 0） |
| `path_risk_level` | str enum \| `"unknown"` | `predict["path_risk"]`；非 low/medium/high → `"unknown"` |
| `soft_signal` | str | 启发式（`"peer_weaken"` / `"high_path_risk"` / `"none"`），与 §12 决策树**完全一致**且**独立重派生**，不读 sibling section's extras |

**严守边界（Step 2C-3b 没做的事）：**
- ❌ 没接 `confidence_engine.py` v1 stub（31 行单纯函数，整仓库零 import；入参 `top1_margin / is_tail` 在 `predict_result` 里完全没有，本轮接 = 给 stub 喂 stub）
- ❌ 没接 `risk_model.py` / `contradiction_engine.py`
- ❌ 没改 `predict.py` / `run_predict` / 4 个 builder / UI / `prediction_store` / contract validator
- ❌ **没把 `primary_projection.score` 归一化进 `structure_score`**——这是 calibration 决策（需要 backtest 定标 / tanh 等），不是字段填充任务，留给 Step 2D
- ❌ 没让 `peer_score` 从 `confirm_count`/`oppose_count` 静默派生（语义不清：0 票是"无数据"还是"完美中性"？）
- ❌ 没让 `event_score` 从 `research_result.catalyst_detected` 这种 bool 派生
- ❌ `extras` 完全只读派生，不参与任何决策；下游不应据 `primary_score_raw` 做"是否预测"判断

**真正的 05 字段化**（让 4 个 score 从 0.0 升为真值、让 `event_score` 有真实来源）留给 Step 2D 及之后——需要：
1. 一个**校准**层把 `primary_projection.score` 归一为 `structure_score`（tanh / clip / backtest 定标皆可）
2. 一个**历史相似度**层把 `historical_score` 从 0.0 升为真值（当前 `historical_sample_count` 永远为 0，是 Step 2B-2 故意排除）
3. 一个**事件**层（财报 / 新闻 / 催化剂）把 `event_score` 从 `None` 升为真值
4. 一个**peer 校准**层定义 `peer_score` 的语义（含数据缺失的 None 表达）

`tests/test_confidence_system_contract_fields.py`（33 case + 14 subtests）+ `tests/test_projection_output_adapter.py`（新增 1 case）锁住"required 不动、extras 反映 predict_result"。

## 14. simulated_trade extras（Step 2D-2，仅暴露不交易）

`services/projection_output_adapter.py::_build_simulated_trade(predict)` 现在做三件事：

1. **6 个交易决策字段保持 pinned 安全 stub**（永不动，与本项目"不允许产生开仓 / 平仓 / 仓位建议"的策略边界绑定）：
   `trade_action == "no_trade"` / `trade_direction == "none"` / `entry_condition == ""` / `stop_loss_condition == ""` / `take_profit_condition == ""` / `suggested_position_size == "0%"`。
   语义零变化——任何下游消费者按"不交易、无方向、无开仓条件、无止损止盈、零仓位"理解都仍然正确。
2. **`no_trade_reason` 从 Step 1C 时期的"adapter default..."字面量升级为静态诚实文本**：
   ```
   Simulated trade engine not enabled in this build; section is informational
   only. See final_projection and confidence_system for decision signals.
   ```
   全静态、零未来字段漂移风险；明确告知下游"决策信号在 06 / 05 段，不是 07"，避免误读 `extras.*` 为交易建议。
3. **新增 `extras` 子 dict**，把已发布的 trade-relevant 观察信号原样暴露：

| extras 键 | 类型 | 来源（仅读 predict_result，**不跨 contract section 读**） |
|---|---|---|
| `final_direction` | enum 偏多/偏空/中性 | `predict["final_projection"]["final_direction"]`；非合法 → `"中性"` |
| `final_five_state` | enum 大涨/小涨/震荡/小跌/大跌 | `predict["final_projection"]["final_five_state"]`；非合法 → `"震荡"` |
| `probability_bucket` | enum ≥70%/55–70%/45–55%/30–45%/≤30% \| `"unknown"` | `predict["final_projection"]["probability_bucket"]`；非合法 → `"unknown"` |
| `confidence_level` | enum high/medium/low | `_normalize_confidence(predict["final_confidence"])` |
| `total_confidence` | float | `_CONFIDENCE_TO_TOTAL[confidence_level]`（0.75 / 0.50 / 0.25） |
| `path_risk_level` | enum low/medium/high \| `"unknown"` | `predict["path_risk"]`；非合法 → `"unknown"` |
| `soft_signal` | enum peer_weaken/high_path_risk/none | **独立重派生**，与 §12 / §13 同决策树 |
| `has_key_price_levels` | bool | `isinstance(klp, dict) and bool(klp)`（今天永远 `False`，因为 `key_price_levels` 全链路硬编码 `{}`） |
| `trade_engine_enabled` | bool 常量 | `False`，明示交易引擎未启用 |

`soft_signal` 决策树（与 §12 / §13 完全一致、**独立重派生**，不读 `predict["exclusion_system"]` 或 `predict["confidence_system"]`——adapter 各段独立产出，且 `predict_result` 顶层根本没有这些 contract section key）：
- `"peer_confirmation=weaken" in conflicting_factors` → `"peer_weaken"`
- 否则 `path_risk == "high"` → `"high_path_risk"`
- 否则 → `"none"`

**严守边界（Step 2D-2 没做的事 / 永远不会做的事）：**
- ❌ 没接 longbridge / 任何 broker / paper_trade / 真实交易 / 模拟盘 API
- ❌ 没接 `risk_model.py` / `contradiction_engine.py` / `confidence_engine.py` 三个 v1 stub
- ❌ 没接 `big_up_contradiction_card` / `exclusion_reliability_review` / `big_down_tail_warning` / `anti_false_exclusion_audit` 到主链
- ❌ 没改 `predict.py` / `run_predict` / 4 个 builder / UI / `prediction_store` / contract validator
- ❌ **`trade_action` 永不离开 `"no_trade"`**（本项目策略边界，不是工程缺失）
- ❌ **`entry_condition` / `stop_loss_condition` / `take_profit_condition` 永不非空**
- ❌ **`suggested_position_size` 永不离开 `"0%"`**
- ❌ `extras` 完全只读派生，下游消费者**绝对不应**据 `final_direction` / `soft_signal` / `probability_bucket` 等做开 / 平仓判断
- ❌ `extras` 中**不包含** `exclusion_level`——会需要跨段读 sibling section，违反"adapter 各段独立"原则

**真正的 07 字段化无路径**——本项目策略明确**不允许**让 07 决策字段动起来。如果未来需要"模拟交易演练"，应当：
1. 新增独立的 contract section（不是改 07）
2. 或新增 `simulated_trade.extras` 内部子键明确标注为"演练记录"而非"交易建议"
3. 永远配合 `trade_engine_enabled = False` / 类似明示开关

`tests/test_simulated_trade_contract_fields.py`（29 case + 22 subtests）+ `tests/test_projection_output_adapter.py`（新增 1 case）锁住"6 决策字段 pinned、no_trade_reason 静态、extras 反映 predict_result、`trade_engine_enabled` 常量 False"。

## 15. Step 2C / 2D extras 模式总览

04 / 05 / 07 三段已完成"required 字段保语义、extras 暴露 raw signals"模式。共有特征：

| 段 | required 字段 | required 字段策略 | extras 关键键 |
|---|---|---|---|
| 04 `exclusion_system`（Step 2C-2） | 5 字段全 stub | `exclusion_level="none"` / 空 list / 全 `False` | `conflicting_factors` / `path_risk_level` / `peer_path_risk_*` / `soft_signal` |
| 05 `confidence_system`（Step 2C-3b） | 4 score = 0.0 + `event_score=None` + 3 真值（confidence_level / total_confidence / confidence_reason） | 4 score 永不动；3 真值保原映射 | `primary_score_raw`（未归一化）/ peer 计数 / `final_confidence` / `probability_bucket` / `soft_signal` |
| 07 `simulated_trade`（Step 2D-2） | 6 决策字段 pinned + `no_trade_reason` 静态 | 6 决策永不动；策略边界 | `final_direction` / `final_five_state` / `probability_bucket` / `confidence_level` / `path_risk_level` / `soft_signal` / `trade_engine_enabled=False` |

**统一不变量：**
- 三段的 `extras.soft_signal` 用**完全相同**的决策树**独立**派生（不跨段读）
- `extras` 是**额外**字段；contract validator 不强制其形状（已在 Step 2C-2 抽查证实）
- 所有 extras 只读派生，下游不应据此决策
- 三个 v1 stub trio（`risk_model.py` / `contradiction_engine.py` / `confidence_engine.py`）整仓库零 import，本轮 / 下一轮都不接

**剩余占位段：** 仅 08 `review_payload` 的 `prediction_id == ""` 还有空字符串问题；其他 7 段 + 08 的非 `prediction_id` 字段都已是字段化或 extras 模式。

## 16. Contract Extras Dashboard（Step 2E-2，read-only 汇总工具）

> 让 04 / 05 / 07 三段的 `extras` 字段真正"可被人类看到"。Step 2C / 2D 模式落地后的闭环验证基础设施。

### 16.1 新增文件

| 文件 | 角色 |
|---|---|
| [services/contract_payload_extras_dashboard.py](../services/contract_payload_extras_dashboard.py) | service：`summarize_contract_extras_dashboard(db_path, limit, symbol) -> dict` + `DISTRIBUTION_PATHS` 常量（14 个 (section, extras_field) tuple） |
| [scripts/dashboard_contract_extras.py](../scripts/dashboard_contract_extras.py) | CLI wrapper，argparse 支持 `--db / --limit / --symbol`，stdout JSON 输出 |
| [tests/test_contract_payload_extras_dashboard.py](../tests/test_contract_payload_extras_dashboard.py) | 30 case，10 组：no_records / all_invalid / ok shape / latest_snapshot 选最新 valid / extras 分布映射 / missing extras 走 MISSING 桶 / limit 防御 / symbol 过滤 / 不修改 DB / DB 不可读 error / CLI |

### 16.2 工具语义

- **只读：** 仅 `SELECT` 不调用 `init_db`，不 `INSERT` / `UPDATE`
- **三级回退状态：** `ok` / `no_records` / `no_valid_payloads` / `error`
- **复用 correlate 风格：** `_resolve_db_path / _resolve_limit / _resolve_symbol` 三个 helper 各工具独立重写（与现有 4 工具一致）；symbol 规则与 `correlate_contract_outcomes` 完全一致（默认 AVGO，None / "ALL" → 不过滤，空字符串回退 AVGO）
- **`latest_snapshot`：** 取 `created_at DESC, rowid DESC` 的最新 **valid** payload；含 `prediction_id` / `prediction_for_date` / 4 个决策摘要字段（`final_direction` / `probability_bucket` / `confidence_level` / `trade_action`）+ 三段 `extras` 原 dict（缺失则 `None`）
- **`extras_distributions`：** 14 个统计字段，每个产出 `dict[str, int]`：
  - 04 段：`soft_signal` / `path_risk_level` / `peer_path_risk_direction` / `conflicting_factors_count`
  - 05 段：`primary_confidence_raw` / `peer_adjusted_confidence` / `final_confidence` / `probability_bucket` / `path_risk_level` / `soft_signal`
  - 07 段：`trade_engine_enabled` / `has_key_price_levels` / `final_direction` / `soft_signal`

### 16.3 桶 key 规则（关键防御性细节）

| 输入 | bucket key |
|---|---|
| `None` | `"NULL"` |
| `True` | `"True"` |
| `False` | `"False"` |
| 其他 | `str(value)` |
| 整段 `extras` 缺失（老 payload，Step 2C-2 之前写入）| `"MISSING"` |
| `extras` 存在但具体键缺失 | `"MISSING"` |

老 payload 缺 extras **不算 invalid**——payload 仍 contract-valid，进入 `extras_distributions` 时计入 `MISSING` 桶，让用户能看到"多少老 prediction 无 extras"。这与 `skipped_records`（仅 `missing_contract_payload` / `invalid_json` / `validation_failed` 三 reason）严格区分。

### 16.4 不统计的字段（避免桶爆 / 连续值无意义）

- `extras.conflicting_factors`（`list[str]`，桶会爆）
- `extras.peer_path_risk_reasons`（同上）
- `extras.primary_score_raw`（连续 float；放 `latest_snapshot` 即可）
- `extras.total_confidence`（连续 float，同上）
- `extras.peer_confirm_count` / `peer_oppose_count`（int 0–3，但小空间分布意义有限；如有需要 Step 2F 单独统计）

### 16.5 CLI 用法

```bash
python3 scripts/dashboard_contract_extras.py
python3 scripts/dashboard_contract_extras.py --limit 50
python3 scripts/dashboard_contract_extras.py --symbol ALL
python3 scripts/dashboard_contract_extras.py --symbol NVDA --limit 100
python3 scripts/dashboard_contract_extras.py --db /path/to/avgo_agent.db
```

### 16.6 严守边界

- ❌ **不替代** inspector / trend / diff / correlation 四个现有工具（它们的 `DIFF_PATHS` / `GROUP_PATHS` 一行未改）
- ❌ **不产生交易建议**：dashboard 只统计 `extras` 分布，**不**输出任何"建议方向 / 仓位 / 入场点"信息；`simulated_trade.extras.trade_engine_enabled` 只统计是否永远是 `False`
- ❌ **不改变任何 contract 字段语义**：required 字段值不动；`extras` 是 Step 2C / 2D 已落地的 metadata，dashboard 是 read-only 消费者
- ❌ 不接 `risk_model.py` / `contradiction_engine.py` / `confidence_engine.py`
- ❌ 不接 `big_up_contradiction_card` / `exclusion_reliability_review` / `big_down_tail_warning` / `anti_false_exclusion_audit`
- ❌ 不接 longbridge / broker / paper_trade / 真实交易 / 模拟盘 API
- ❌ 不动 `predict.py` / `run_predict` / 4 个 builder / adapter / contract validator / UI / `prediction_store` / DB schema

## 17. Confidence Calibration Inputs（Step 2F-2，read-only 诊断工具）

> Step 2F-1 诊断结论：当前 0 个 (contract × outcome) pair，calibration 不可启动。本工具的目标是**让数据缺口可见**，不是落地 calibration——4 个 score 字段仍是 0.0、`event_score` 仍是 None。

### 17.1 新增文件

| 文件 | 角色 |
|---|---|
| [services/contract_calibration_inputs.py](../services/contract_calibration_inputs.py) | service：`summarize_confidence_calibration_inputs(db_path, limit, symbol) -> dict` + `_MIN_RECOMMENDED_PAIRS = 90` 阈值常量 |
| [scripts/summarize_confidence_calibration_inputs.py](../scripts/summarize_confidence_calibration_inputs.py) | CLI wrapper，argparse 支持 `--db / --limit / --symbol`，stdout JSON |
| [tests/test_contract_calibration_inputs.py](../tests/test_contract_calibration_inputs.py) | 31 case，12 测试组：no_records / all_invalid / 含/不含 confidence extras 两路径 / outcome 三态标签 / `confidence_level_summary` accuracy / `primary_score_raw_summary` min-max-mean / `data_gap_report` 4 类缺口 / limit 5 防御 / symbol 3 路径 / 不修改 DB / DB error / CLI 3 case |

### 17.2 工具语义

- **完全只读：** 仅 `SELECT`（含 `outcome_log` 子查询），不调用 `init_db`，不 `INSERT` / `UPDATE`
- **三级回退状态：** `ok` / `no_records` / `no_valid_payloads` / `error`
- **复用既有模式：** `_resolve_db_path / _resolve_limit / _resolve_symbol` 与 dashboard / correlate 完全同口径；outcome 关联用 `contract_outcome_correlation` 同款的 LEFT JOIN-via-correlated-subquery（按 `captured_at DESC, rowid DESC` 取最新 outcome）
- **不替代 5 个现有 read-only 工具：** inspector / trend / diff / correlation / dashboard 一行未改；本工具专门聚焦"calibration 输入 + 数据缺口"维度

### 17.3 输出结构

```python
{
    "status": "ok" | "no_records" | "no_valid_payloads" | "error",
    "symbol_filter": str,                # "AVGO" / "ALL" / 实际 ticker
    "requested_limit": int,
    "records_scanned": int,
    "valid_payloads": int,               # 通过 contract validator
    "invalid_payloads": int,             # missing_contract_payload / invalid_json / validation_failed
    "records_with_confidence_extras": int,   # valid 中含 05 段 extras 的子集
    "paired_outcomes": int,              # direction_correct ∈ {correct, wrong}
    "pending_outcomes": int,             # direction_correct == "pending"
    "skipped_records": [{prediction_id, reason}, ...],
    "records": [
        {
            "prediction_id": str, "prediction_for_date": str, "symbol": str,
            "has_confidence_extras": bool,
            "primary_score_raw": float | None,
            "primary_confidence_raw": str | None,
            "peer_confirm_count": int | None,
            "peer_oppose_count": int | None,
            "peer_adjusted_confidence": str | None,
            "final_confidence": str | None,
            "probability_bucket": str | None,
            "conflicting_factors_count": int | None,
            "path_risk_level": str | None,
            "soft_signal": str | None,
            "direction_correct": "correct" | "wrong" | "pending",
        }, ...
    ],
    "confidence_level_summary": {
        "high"|"medium"|"low": {samples, correct, wrong, pending, accuracy}
    },
    "primary_score_raw_summary": {count, min, max, mean},  # 仅含 real number
    "data_gap_report": {
        "calibration_ready": bool,
        "contract_outcome_pairs": int,
        "minimum_recommended_pairs": 90,
        "missing_dimensions": [str, ...],
    },
}
```

### 17.4 关键防御性细节

- **`has_confidence_extras=False`** 时（老 payload，Step 2C-3b 之前）记录仍保留在 `records` 中，`primary_score_raw` 等字段为 `None`，**不进 `skipped_records`**
- **`primary_score_raw` 只统计 real number**（`int` / `float`，但**排除 bool**——`isinstance(True, int)` 在 Python 是 True，要先过滤 bool）
- **`confidence_level_summary` 优先用 `extras.final_confidence`，缺失时回退 required `confidence_system.confidence_level`**——确保即使老 payload 也能进桶（前提：`confidence_level` 字段是必填，contract validator 已锁住）
- **`accuracy = correct / (correct + wrong)`，分母 0 时 `null`**（pending 不算入分母）
- **`data_gap_report.calibration_ready`** 只是诊断标签，**永不影响**主链路；任何字段 / 流程都不读它
- **`_MIN_RECOMMENDED_PAIRS = 90`** 是经验阈值（3 档 confidence × 30 样本/档），**不是统计学保证**

### 17.5 严守边界（与 Step 2 全程一致）

- ❌ **不实现 calibration 函数**——工具只读 / 只统计 / 不归一化 / 不预测
- ❌ **不让 `historical_score / structure_score / peer_score / exclusion_penalty` 从 0.0 升真值**
- ❌ **不让 `event_score` 从 None 升真值**
- ❌ **`primary_score_raw` 仍未归一化**——工具只 dump min/max/mean，不做任何 transform
- ❌ 不接 `confidence_engine.py`（入参 `top1_margin / is_tail` 在 `predict_result` 里完全没有；接 = 给 stub 喂 stub）
- ❌ 不接 `risk_model.py` / `contradiction_engine.py`
- ❌ 不接 `big_up_contradiction_card` / `exclusion_reliability_review` / `big_down_tail_warning` / `anti_false_exclusion_audit`
- ❌ 不接 longbridge / broker / paper_trade / 真实交易 / 模拟盘 API
- ❌ 不动 `predict.py` / `run_predict` / 4 个 builder / adapter / contract validator / UI / `prediction_store` / DB schema
- ❌ 不动现有 5 个 read-only 工具的字段集（`DIFF_PATHS` / `GROUP_PATHS` / `DISTRIBUTION_PATHS` 全不动）

### 17.6 CLI 用法

```bash
python3 scripts/summarize_confidence_calibration_inputs.py
python3 scripts/summarize_confidence_calibration_inputs.py --limit 100
python3 scripts/summarize_confidence_calibration_inputs.py --symbol ALL
python3 scripts/summarize_confidence_calibration_inputs.py --symbol NVDA --limit 50
python3 scripts/summarize_confidence_calibration_inputs.py --db /path/to/avgo_agent.db
```

### 17.7 用法定位（与 dashboard 工具的关系）

| 工具 | 焦点 | 出口 | 数据来源 |
|---|---|---|---|
| `dashboard_contract_extras` (Step 2E-2) | 04 / 05 / 07 三段 extras 的**枚举/计数字段分布** | `extras_distributions` 14 字段桶图 | `prediction_log.contract_payload_json` |
| `summarize_confidence_calibration_inputs` (本节，Step 2F-2) | 05 段 extras + outcome 关联 + **calibration 数据缺口** | `records` / `confidence_level_summary` / `primary_score_raw_summary` / `data_gap_report` | `prediction_log` LEFT JOIN `outcome_log` |

两工具互补、不重叠：dashboard 看"什么 extras 字段值在出现"；calibration_inputs 看"哪些 extras 字段 + outcome 配对足够做归一化决定"。

## 18. Contract Replay Planner（Step 2F-4b，dry-run only）

> Step 2F-4 方案文档 §8 的 Option B 落地。**只读枚举 (D, D+1) pair，不写 DB、不调 yfinance、不运行 prediction、不生成 outcome。** 是 Step 2F-4c writer 的前置工具。

### 18.1 新增文件

| 文件 | 角色 |
|---|---|
| [services/contract_replay_planner.py](../services/contract_replay_planner.py) | service：`plan_contract_replay(symbol, start_date, end_date, limit, coded_data_dir) -> dict`；stdlib only（`csv` + `datetime`），不 import pandas / yfinance / requests |
| [scripts/plan_contract_replay.py](../scripts/plan_contract_replay.py) | CLI：`--symbol / --start / --end / --limit / --coded-data-dir`，stdout JSON 输出 |
| [tests/test_contract_replay_planner.py](../tests/test_contract_replay_planner.py) | 34 case，7 测试组：missing_data 三种 / 时间正序 + 去重 + ISO 时间后缀截断 / limit 5 防御 / start-end 过滤 7 case / symbol 7 路径（含 ALL→error）/ 依赖卫生（不 import yfinance/requests + 不依赖 DB）/ CLI 2 case |

### 18.2 工具语义

- **完全只读：** 仅读 `coded_data/<SYMBOL>_coded.csv` 的 `Date` 列；不写 DB / 不调 init_db / 不 INSERT/UPDATE
- **完全离线：** 不调 yfinance / 网络；不 import pandas（与 Step 2 全程 read-only 工具一致，stdlib only）
- **不运行 prediction / 不生成 outcome：** Step 2F-4c writer 的职责；本工具只枚举"会跑哪些 (D, D+1) pair"
- **status 四值：** `ok` / `missing_data` / `insufficient_data` / `error`
- **不影响 Step 1E + Step 2F-4 严守边界：** 不动 `predict.py` / `prediction_store.py` / adapter / contract validator / 6 个 read-only 工具 / DB schema

### 18.3 数据来源与 CWD 行为

- **默认数据源：** `Path.cwd() / "coded_data" / "<SYMBOL>_coded.csv"`
- **`coded_data_dir` 显式覆盖：** 可通过参数或 CLI `--coded-data-dir` 指定
- **CWD 差异：** 主项目根 `/Users/may/Desktop/stock-analyzer-main/` 有 `coded_data/`（4 份 CSV：AVGO / NVDA / QQQ / SOXX）；worktree 根没有
- **缺数据时不抛异常：** `coded_data` 目录或 `<SYMBOL>_coded.csv` 不存在 → 返回 `status="missing_data"` + `data_source_status="missing_dir" | "missing_file"`

### 18.4 候选 pair 生成

按时间正序：
1. 读 CSV `Date` 列（前 10 字符 ISO truncate，handles `2024-01-02 00:00:00` 后缀）
2. 跳过非合法日期（无效日期不抛，silently skip）
3. dedupe + sort 得 `trading_days`（YYYY-MM-DD 字符串列表）
4. 应用 `start_date <= D` / `D <= end_date` 过滤
5. 构造 `[(days[i], days[i+1]) for i in range(len(days)-1)]`
6. 截断到 `limit` 个（默认 30；非法回退 30，含 bool / non-int / `<=0` 防御）
7. 自查 `as_of_date < prediction_for_date`（anti-lookahead self-check，输出在 `anti_lookahead_check`）

### 18.5 错误处理（status=error）

- `start_date` / `end_date` 不是合法 YYYY-MM-DD → error + 描述错误的字段
- `start_date > end_date` → error
- `symbol="ALL"` / `"all"` → error（**planner 是 per-symbol，不支持聚合**——这是与 dashboard / correlate / calibration_inputs 的关键差异）

### 18.6 CLI 用法

```bash
python3 scripts/plan_contract_replay.py
python3 scripts/plan_contract_replay.py --start 2024-01-01 --end 2024-06-30
python3 scripts/plan_contract_replay.py --limit 100
python3 scripts/plan_contract_replay.py --symbol NVDA
python3 scripts/plan_contract_replay.py --coded-data-dir /path/to/coded_data
```

### 18.7 严守边界

- ❌ **不解决 `save_prediction.analysis_date = now()` 问题** —— 这是 Step 2F-4c writer 启动前的独立决策（Step 2F-4a 诊断 §3.2 推荐 Option (a) "给 `save_prediction` 加 `analysis_date` kwarg"）
- ❌ **不调 `run_predict` / `save_prediction` / `save_outcome`** —— 那是 Step 2F-4c
- ❌ **不调 yfinance / 任何网络**
- ❌ **不动 6 个现有 read-only 工具**（inspector / trend / diff / correlation / dashboard / calibration_inputs）
- ❌ 不接 `risk_model.py` / `contradiction_engine.py` / `confidence_engine.py`
- ❌ 不接 `big_up_contradiction_card` / `exclusion_reliability_review` / `big_down_tail_warning` / `anti_false_exclusion_audit`
- ❌ 不接 longbridge / broker / paper_trade / 真实交易 / 模拟盘 API
- ❌ 不写 DB / 不动 schema / 不 import pandas
- ❌ 不让 04 / 05 / 07 任何 required 字段升级
- ❌ 不使用 2099 synthetic records（与本工具范围正交：planner 完全不读 `prediction_log`）

### 18.8 与 Step 2F-4c writer 的关系

planner 输出可作为 writer 输入的"候选 pair 清单"。但 writer 启动前必须先：

1. 决定 `analysis_date` 处理方案（Option (a) / (b) / (c)）—— 见 Step 2F-4a 诊断 §3.2
2. 同样决定 `outcome_log.captured_at` 处理（同问题）
3. 复用 `services/historical_replay_training.py::run_historical_replay_for_date(...)` 作为 projection 框架（已存在、anti-lookahead 严格）
4. 复用 `services/outcome_capture.py::_compute_direction_correct(...)` 计算 outcome（不能手工传 0/1）
5. **不**使用 `services/replay_record_wiring.py`（写到 `projection_runs` 表，与 contract pair 不同维度）
6. 直接调 `save_prediction` + `save_outcome`（注意 `analysis_date` 处理）

planner 测试基线：2094 → 2128（+34）。0 failed；10 skipped 不变。

## 19. Replay timestamp overrides（Step 2F-4c-prereq）

> Step 2F-4a 诊断 §3.2 推荐的 Option (a) 落地。**最小扩展**——给 `services/prediction_store.py` 的 `save_prediction` / `save_outcome` 各加一个可选 kw-only override 参数，默认行为完全不变。**这是 Step 2F-4c replay writer 的最后一块前置拼图，本身不写 replay writer。**

### 19.1 改动文件

| 文件 | 改动 | 概要 |
|---|---|---|
| [services/prediction_store.py](../services/prediction_store.py) | 修改 | `from datetime import date, datetime`（加 `date` 类型 import）；新增 `_coerce_analysis_date_override(value)` + `_coerce_captured_at_override(value)` 两个 helper；`save_prediction` 加 kw-only `analysis_date_override: str \| date \| None = None`；`save_outcome` 加 kw-only `captured_at_override: str \| datetime \| None = None` |
| [tests/test_prediction_store.py](../tests/test_prediction_store.py) | 修改 | 新增 `ReplayTimestampOverrideTests` 类，11 case |

### 19.2 行为定义

#### `save_prediction.analysis_date_override`

| 输入 | 行为 |
|---|---|
| `None`（默认） | 走旧路径：`analysis_date = datetime.now().date().isoformat()`，**完全不变** |
| `date(2024, 1, 2)` | `.isoformat()` → `"2024-01-02"` |
| `datetime(2024, 1, 2, 16, 0, 0)` | `.date().isoformat()` → `"2024-01-02"`（取日期部分，丢时分秒） |
| `"2024-01-02"` | `date.fromisoformat(...).isoformat()` → 同上（含校验） |
| `"not-a-date"` / 12345 / 其他 | `raise ValueError("analysis_date_override must be YYYY-MM-DD")` —— **校验在 INSERT 之前，失败时不写任何行** |

`created_at` 仍用 `now()`，**不**受 override 影响（创建时间记录的是"何时写入 DB"，与 prediction 的 analysis 时间是不同维度）。

#### `save_outcome.captured_at_override`

| 输入 | 行为 |
|---|---|
| `None`（默认） | 走旧路径：`captured_at = datetime.now().isoformat(timespec="seconds")`，**完全不变** |
| `datetime(2024, 1, 3, 16, 0, 0)` | `.isoformat(timespec="seconds")` → `"2024-01-03T16:00:00"` |
| `"2024-01-03T16:00:00"` | `datetime.fromisoformat(...).isoformat(timespec="seconds")` → 同上（含校验、保留时分秒） |
| `"not-a-datetime"` / 12345 / 其他 | `raise ValueError("captured_at_override must be ISO datetime")` —— 校验在 INSERT 之前，失败时不写任何行 |

### 19.3 严格不变量

- ❌ **DB schema 一行未改**——`analysis_date` / `captured_at` 列名 / 类型不动
- ❌ **`contract_payload_json` 自动旁路语义未改**——`_AUTO_GENERATE_CONTRACT` / `_try_build_contract_payload` 路径不变；override 完全不影响 contract 生成
- ❌ **现有 39 个 `tests/test_prediction_store.py` case 全绿**（无回归）
- ❌ **现有 caller 无需改动**——所有现有 `save_prediction(...)` / `save_outcome(...)` 调用方默认不传 override，行为与升级前完全一致
- ❌ **`scenario_match` 等其他参数顺序 / 默认值不动**
- ❌ **没有新增任何 replay writer**——本步是单点能力扩展，不实施 4c

### 19.4 失败原子性

两个 override 都遵循 **"先校验再 INSERT"** 模式：
- `_coerce_*_override` 在拿锁之前 raise；任何非法输入都不会触发 `init_db()` / `_get_conn()`
- `save_prediction` 的 `_try_build_contract_payload` 也已经在 INSERT 前；override 失败时 contract 不构建

测试 `test_save_prediction_invalid_string_raises_and_writes_nothing` 与 `test_save_outcome_invalid_string_raises_and_writes_nothing` 锁住此原子性。

### 19.5 与 Step 2F-4 plan 的对接

Step 2F-4a 诊断 §3.2 的三 Option：
- **Option (a)** —— 给 `save_prediction` / `save_outcome` 加可选 override → ✅ **本节落地**
- ~~Option (b)~~ —— 把 D 编码进 `snapshot_id`：不需要了
- ~~Option (c)~~ —— 新增 `save_prediction_replay()` 函数：不需要了

Step 2F-4c writer 现在可以：

```python
# 伪代码（4c writer 范围；本节不实施）
for pair in plan_contract_replay(...).candidate_pairs:
    D = pair["as_of_date"]
    D_plus_1 = pair["prediction_for_date"]
    scan = build_historical_scan_at(D)             # 4c 范围
    predict = run_predict(scan, ...)
    pid = save_prediction(
        symbol="AVGO",
        prediction_for_date=D_plus_1,
        scan_result=scan,
        research_result=None,
        predict_result=predict,
        snapshot_id=f"replay_phaseA_{D}",
        analysis_date_override=D,                  # ← 关键
    )
    actual_ohlcv = fetch_actual_ohlcv_at(D_plus_1)  # 4c 范围
    direction_correct = _compute_direction_correct(
        predict["final_bias"],
        (actual_ohlcv["close"] - actual_ohlcv["prev_close"]) / actual_ohlcv["prev_close"],
    )
    save_outcome(
        prediction_id=pid,
        prediction_for_date=D_plus_1,
        ...,
        direction_correct=direction_correct,
        captured_at_override=f"{D_plus_1}T16:00:00",  # ← 关键
    )
```

### 19.6 严守边界（Step 2 全程一致）

- ❌ 没改 `predict.py` / `run_predict` / 4 个 builder / adapter / contract validator
- ❌ 没改 `scanner.py` / `matcher.py` / 数据层
- ❌ 没改 6 个现有 read-only 工具（inspector / trend / diff / correlation / dashboard / calibration_inputs）/ `DIFF_PATHS` / `GROUP_PATHS` / `DISTRIBUTION_PATHS`
- ❌ 没改 `services/contract_replay_planner.py`（Step 2F-4b 工具）
- ❌ 没改 DB schema
- ❌ 没接 `risk_model.py` / `contradiction_engine.py` / `confidence_engine.py`
- ❌ 没接 `big_up_contradiction_card` / `exclusion_reliability_review` / `big_down_tail_warning` / `anti_false_exclusion_audit`
- ❌ 没接 longbridge / broker / paper_trade / 真实交易 / 模拟盘 API
- ❌ 没新增 replay writer（Step 2F-4c 范围）
- ❌ 没让 04 / 05 / 07 任何 required 字段升级

测试基线：2128 → 2139（+11）。0 failed；10 skipped 不变。

## 20. Contract Replay Writer（Step 2F-4c-2，real-write upgrade）

> Step 2F-4 plan §8 Option C 第二阶段。**`dry_run=True` 仍是默认且仍完全只读**；`dry_run=False`（CLI `--write`）现在**真正写入** `prediction_log` + `outcome_log`，每条 (D, D+1) 走 `save_prediction(analysis_date_override=D)` + `save_outcome(captured_at_override=D+1T16:00:00)`，**绝不 raw INSERT**。本节升级 4c-1 skeleton。

### 20.1 改动 / 升级文件

| 文件 | 状态 | 概要 |
|---|---|---|
| [services/contract_replay_writer.py](../services/contract_replay_writer.py) | 升级 | `_LIMIT_HARD_CAP` 30→**30 保持**（writer 收紧）；`_MIN_HISTORY_ROWS = 20`；新增 helper `_read_symbol_ohlcv` / `_build_historical_scan_at` / `_read_outcome_row` / `_maybe_override_db_path` / `_write_one_pair`；写入路径走 `save_prediction` + `save_outcome`，从不 raw INSERT |
| [scripts/run_contract_replay.py](../scripts/run_contract_replay.py) | 不变 | `--write` 仍 flip `dry_run=False`，但现在走真写入 |
| [tests/test_contract_replay_writer.py](../tests/test_contract_replay_writer.py) | 升级 | 32 case（4c-1 时 28；移除 5 个 not_implemented case，新增 9 个真写入 + 4 个 skip + 1 个 db_path isolation）；含 patch+assert 锁定 dry_run 不调真函数、写入路径走 save_prediction / save_outcome |

### 20.2 核心契约

#### dry_run=True（默认，**未变**）

- 调 `plan_contract_replay(...)` 拿 `candidate_pairs`
- 返回字段：`status="ok"` / `would_write_count = len(candidate_pairs)` / `written_prediction_count=0`
- **绝对不调** `run_predict` / `save_prediction` / `save_outcome`（3 个 patch+assert call_count==0 测试锁住）

#### dry_run=False（CLI `--write`，**新启用**）

写入算法（每个 pair）：

1. **先**读 `D+1` outcome 行：缺失或不可解析 → `skipped_pairs.append({"reason": "no_outcome_data"})`，**不**进入 step 2-6（防止 half-pair）
2. 构造 `<= D` 历史 scan：`avgo_recent_20` 来自 CSV 末尾 ≤ D 的 20 行；peer 信号留空（4c-2 范围不接 peer cutoff）；< 20 行历史时 → `skipped_pairs.append({"reason": "insufficient_history"})`
3. `run_predict(scan, research_result=None, symbol=symbol)`（pure 函数，无副作用）
4. `save_prediction(symbol=..., prediction_for_date=D+1, ..., snapshot_id=f"replay_{symbol}_{D}", analysis_date_override=D)`
5. `direction_correct = _compute_direction_correct(predict["final_bias"], close_change)` — 复用 `services.outcome_capture._compute_direction_correct`
6. `save_outcome(prediction_id=pid, ..., captured_at_override=f"{D+1}T16:00:00")`

**status 决策**：
- 全部写入成功 → `"ok"`
- 部分跳过 → `"partial"`
- 全部跳过 → `"partial"`（与 ok 区分，提醒消费者）
- step 3-6 抛异常 → `"error"`，已写入的 prior pairs 保留（DB 是 durable 的）

#### planner 失败模式透传（**未变**）

- planner `missing_data` / `insufficient_data` / `error` → writer 同状态透传；不读 OHLCV、不进入写入循环

### 20.3 anti-lookahead

每个 pair：
- **scan_result 只用 `<= D` 数据**（`_build_historical_scan_at` 严格过滤 `r["Date"] <= as_of_date`）
- **outcome 只读 `D+1` 那一行 + 前一行 Close**（`_read_outcome_row` 不调用 `_build_historical_scan_at`，反向不可能从 outcome 倒灌进 scan）
- **peer 信号留空（4c-2 范围不接 peer cutoff）** —— 这意味着 peer 部分对 final_bias 没有贡献，但保证零 lookahead 风险；4c-3 可加 peer
- **`prev_close` 只取前一行 Close**（不读 CSV 的 `PrevClose` 列；该列在真实数据里第一行可能为空、值可能与前一行不一致）

### 20.4 half-pair 防御

| 失败位置 | 处理 |
|---|---|
| outcome 数据缺失 | step 1 即 skip，不写 prediction |
| 历史 < 20 行 | step 2 即 skip，不写 prediction |
| `run_predict` 抛异常（罕见，pure 函数）| 捕获 → return `status="error"` |
| `save_prediction` 抛异常（含 `analysis_date_override` 校验失败）| 捕获 → return `status="error"`，pair 不会半写（save_outcome 未被调用）|
| `save_outcome` 抛异常 | 捕获 → return `status="error"`；此时 pair **可能** half-write（prediction 写了但 outcome 没写）。Step 2F-4c-prereq 的 `_coerce_captured_at_override` 在 INSERT 之前 raise，绕过此风险，但理论上仍存在 sqlite IO 异常 |

**实践判断：** 4c-2 范围内传入的 `captured_at_override = f"{D+1}T16:00:00"` 是 ISO-valid 字符串，sqlite IO 异常极罕见。half-pair 风险是理论上的，会在 status="error" 路径 surface 出来；caller 看到 error 后可手动检查 prediction_log / outcome_log 一致性。

### 20.5 limit 安全边界（**收紧到 30**）

| 输入 | 输出 |
|---|---|
| `None` / 默认 | 30 |
| 1 ≤ N ≤ 30 | N |
| N > 30 | **30** |
| `0` / 负数 / `bool` / 非 `int` | 30 |

测试 `test_limit_clamped_at_hard_cap_30` 锁住。比 planner 的"无显式上限"更紧，比 4c-1 时的 50 更紧——**4c-2 是真写入，安全裕度优先**。

### 20.6 db_path 隔离

`_maybe_override_db_path(db_path)` context manager：
- 进入：`saved = _ps.DB_PATH; _ps.DB_PATH = Path(db_path)`
- 退出：`_ps.DB_PATH = saved`
- 即使写入循环中途异常 raise，`finally` 仍恢复

测试 `test_explicit_db_path_isolates_writes` 显式构造两个 tmpdir（默认 + 显式），验证：
- 默认 DB 行数 before==after（不被污染）
- 显式 db_path DB 中有写入

### 20.7 严守边界

- ❌ **dry_run=True 不调** `run_predict` / `save_prediction` / `save_outcome`（patch+assert 锁住）
- ❌ **写入路径绝不 raw INSERT** —— 100% 走 `save_prediction` / `save_outcome` 真路径（保证 contract_payload_json 自动旁路 + analysis_date / captured_at override 一致）
- ❌ **不调 yfinance / 不调网络**（writer / planner 都是离线）
- ❌ **不动** `predict.py` / `run_predict` 内部 / 4 个 builder / adapter / contract validator / `scanner.py` 既有行为 / `matcher.py` / 6 个现有 read-only 工具 / DB schema / UI
- ❌ **不接** `risk_model.py` / `contradiction_engine.py` / `confidence_engine.py`
- ❌ **不接** `big_up_contradiction_card` / `exclusion_reliability_review` / `big_down_tail_warning` / `anti_false_exclusion_audit`
- ❌ **不接** longbridge / broker / paper_trade / 真实交易 / 模拟盘 API
- ❌ **不让** 04 / 05 / 07 任何 required 字段升级
- ❌ **第一版不接 peer 历史 cutoff**（4c-3 范围）
- ❌ **不跑 90 pair**（hard cap 30；Step 2F-4d 才解锁更大批次）

### 20.8 CLI 用法

```bash
# 默认 dry-run（永远是默认；任何场景都不写 DB）
python3 scripts/run_contract_replay.py
python3 scripts/run_contract_replay.py --start 2024-01-29 --limit 30

# 真写入：必须显式 --write，且建议加 --start 跳过 < 20 行历史的早期日期
python3 scripts/run_contract_replay.py --write --start 2024-01-29 --limit 30

# 自定义 DB / coded_data 路径（测试或多 ticker 时常用）
python3 scripts/run_contract_replay.py --write --db /path/to/test.db --coded-data-dir /path/to/coded_data
```

stdout 输出 UTF-8 JSON（`ensure_ascii=False, indent=2`）；进程不写文件、不写日志、不调网络。

### 20.9 与 Step 2F-4 plan 的对接

| Step 2F-4 阶段 | 状态 |
|---|---|
| 方案文档（plan）| ✅ commit `e9b44e2` |
| 4a 诊断 | ✅（无代码） |
| 4b dry-run planner | ✅ commit `4c89d98` |
| 4b-verify 实跑 | ✅（无代码；2502 trading days 验证）|
| 4c-prereq 时间 override | ✅ commit `5dbd9ac` |
| 4c-1 writer skeleton | ✅ commit `b0ba05a` |
| **4c-2 真写入逻辑（本节）** | **本轮** |
| 4c-3 peer 历史 cutoff（可选）| 待办 |
| 4d 90-pair 解锁 calibration_ready | 4c-2 + DB hygiene 完成后 |

测试基线：2167 → 2171（+4：移除 5 个 not_implemented + 新增 9 个真写入 = 净 +4）。0 failed；10 skipped 不变。

---

## 21. Peer historical cutoff（Step 2F-4c-3）

> Step 2F-4 plan §8 Option A。`dry_run=True` **仍完全不读 peer CSV**；`dry_run=False` 现在在 `run_contract_replay` 入口**一次性**加载 NVDA / SOXX / QQQ 的 `coded_data/<PEER>_coded.csv`，并按每个 D 截断到 `Date <= D`，把 `relative_strength_summary` / `relative_strength_same_day_summary` 注入历史 scan_result。`predict.py` / `scanner.py` / `apply_peer_adjustment` 全部一行未改。

### 21.1 改动文件

| 文件 | 状态 | 概要 |
|---|---|---|
| [services/contract_replay_writer.py](../services/contract_replay_writer.py) | 升级 | 新增 5 个纯函数 helper：`_read_peer_ohlcv` / `_compute_nday_return_at` / `_compute_same_day_move_at` / `_classify_relative_strength` / `_compute_relative_strength_summary_at`；`_build_historical_scan_at` 增加 `peer_rows_map` 参数；`_write_one_pair` 透传；`run_contract_replay` `dry_run=False` 路径加载 3 个 peer CSV 一次性传下去 |
| [tests/test_contract_replay_writer.py](../tests/test_contract_replay_writer.py) | 升级 | 32 → **74** case（+42）；6 个新测试组覆盖 helper / build_scan / dry-run 隔离 / 真写入 e2e / peer 缺失降级 / hard-cap & pandas hygiene |

### 21.2 5 个 stdlib helper

| helper | 输入 | 输出 |
|---|---|---|
| `_read_peer_ohlcv(symbol, dir)` | peer ticker + 目录 | `list[dict] \| None`；缺文件 / 缺 Date 列 / 解析失败 → None |
| `_compute_nday_return_at(rows, D, n=5)` | 时间升序 rows + 目标 D + n | `(close[D] / close[D-n] - 1) * 100`；任一缺失 / 不足 / 0 → None；镜像 `scanner._get_nday_return` |
| `_compute_same_day_move_at(rows, D)` | rows + D | 优先 `C_move × 100`；C_move 缺失时 fallback `(Close - Open) / Open × 100`；镜像 `scanner._get_same_day_move` 主路径 + 自有 fallback |
| `_classify_relative_strength(avgo, peer, margin_pp=0.5)` | 两个百分比 + margin | `stronger / weaker / neutral / unavailable`；strict `>` 比较；镜像 `scanner._classify_rs` |
| `_compute_relative_strength_summary_at(D, avgo_rows, peer_rows_map, *, mode)` | mode `"5d"` 或 `"same_day"` | `{vs_nvda, vs_soxx, vs_qqq}` 三键，值 ∈ 上述 4 状态 |

**镜像口径常量**：`_PEER_SYMBOLS = ("NVDA", "SOXX", "QQQ")` / `_RS_MARGIN_PP = 0.5` / `_NDAY_RETURN_WINDOW = 5` —— 与 `scanner.PEER_SYMBOLS` / `scanner._RS_MARGIN * 100` / `scanner._get_nday_return n=5` 完全一致。

### 21.3 数据流

```
run_contract_replay(dry_run=False)
  ├── _read_symbol_ohlcv("AVGO", coded_data_dir)   ← 既有
  ├── peer_rows_map = {                            ← 新增（每批次一次）
  │       "NVDA": _read_peer_ohlcv("NVDA", ...),
  │       "SOXX": _read_peer_ohlcv("SOXX", ...),
  │       "QQQ":  _read_peer_ohlcv("QQQ",  ...),
  │   }
  └── for pair in candidate_pairs:
        _write_one_pair(..., peer_rows_map=peer_rows_map)
          └── _build_historical_scan_at(..., peer_rows_map)
                ├── rs_5d        = _compute_relative_strength_summary_at(D, history, peer_rows_map, mode="5d")
                └── rs_same_day  = _compute_relative_strength_summary_at(D, history, peer_rows_map, mode="same_day")
```

`apply_peer_adjustment` 读 `scan["relative_strength_summary"]["vs_nvda"|"vs_soxx"|"vs_qqq"]` —— 现在拿到的是真实分类，不再是默认 `"unavailable"`。

### 21.4 dry_run=True 仍完全不读 peer

writer 的 `dry_run=True` 路径在 [services/contract_replay_writer.py](../services/contract_replay_writer.py) 早早 return（在 OHLCV / peer 加载之前），`_read_peer_ohlcv` 永远不会被调用。
- 测试 `WriterDryRunDoesNotReadPeerCsvTests::test_dry_run_does_not_call_read_peer_ohlcv` 用 `unittest.mock.patch` 锁住 `call_count == 0`。
- 既有 3 个 patch+assert 测试（`test_dry_run_does_not_call_run_predict / save_prediction / save_outcome`）继续锁住 dry-run 不调真写入函数。

### 21.5 peer 缺失降级

| 情形 | 单 peer 行为 | batch 行为 |
|---|---|---|
| 整个 peer CSV 文件不存在 | `_read_peer_ohlcv` 返回 None → map 中存 None | 该 peer `vs_*` = `"unavailable"`；其他 peer 不受影响 |
| peer CSV Date 列缺失 | 同上 | 同上 |
| peer 在某个 D 找不到行（休市等）| `_compute_nday_return_at` 返回 None | 该 peer 当 D 当 mode `"unavailable"`；其他 D / 其他 peer 不受影响 |
| peer 在 D 处的前 n=5 行不够 | 同上 | 同上 |
| peer Close 列空 / 非数 / 0 | 同上 | 同上 |

测试覆盖：
- `WriterMissingPeerCsvDegradesTests::test_real_write_succeeds_with_no_peer_csvs` — 0 peer CSV → 全 unknown / insufficient（4c-2 baseline shape），写入仍成功
- `test_one_peer_missing_does_not_break_others` — 2/3 peer 存在，一个缺 → 缺的那个 unknown，其他正常

### 21.6 anti-lookahead 保留

- `_build_historical_scan_at` 的 `history` 仍只取 `Date <= as_of_date`
- 所有 peer helper 用 `Date == target_date` 定位 + 只读 `idx - n`（永远 ≤ 该 idx）
- peer rows 即使包含未来日期，由于 lookup 是 `Date == D`，自然只命中 D 当前及更早的 close
- 复测 `WriterRealWriteWithPeerCsvTests` 整组（5 case）→ 写入的 contract_payload 中 peer 字段全为非 unknown 且方向正确

### 21.7 严守边界

- ❌ **不改** `predict.py` / `run_predict` / `apply_peer_adjustment`
- ❌ **不改** `scanner.py` / `peer_matcher.py` / `encoder.py` / 4 个 builder / adapter / validator / `prediction_store.py` / DB schema
- ❌ **不调** yfinance / requests / pandas / 网络（writer 走 `csv` stdlib）—— 测试 `test_writer_module_does_not_import_pandas` / `does_not_import_yfinance` / `does_not_import_requests` 锁住
- ❌ **不接** longbridge / broker / paper_trade / 真实交易
- ❌ **不动** `_LIMIT_HARD_CAP = 30` —— 90-pair 仍是 Step 2F-4d 范围
- ❌ **不写主项目 DB** —— 本步只改 writer + tests + 文档；30 条已写入的 `replay_AVGO_*` 行仍是 4c-2 的 peer-坍缩版本，**需要后续单独清理 + 重写**（见 21.8），本文不执行任何 DB 写入

### 21.8 已写入 30 条数据的处理（**后续步骤，不在本步执行**）

主项目 DB 上的 30 条 `replay_AVGO_*` 行的 contract_payload_json 是 4c-2 时代的 peer-坍缩版本（nvda/soxx/qqq_signal 全 unknown / peer_alignment=insufficient / peer_path_risk_direction=unchanged / peer_confirm_count=peer_oppose_count=0）。要让它们用上新 peer cutoff，需要**单独**：

1. `cp avgo_agent.db avgo_agent.db.backup_pre_4c3_rewrite_<ts>`
2. SQL（FK 反序）：
   ```sql
   DELETE FROM outcome_log
    WHERE prediction_id IN (SELECT id FROM prediction_log WHERE snapshot_id LIKE 'replay_AVGO_%');
   DELETE FROM prediction_log
    WHERE snapshot_id LIKE 'replay_AVGO_%';
   ```
3. `python3 scripts/run_contract_replay.py --start 2024-01-29 --end 2024-03-12 --limit 30 --write`

**本文档（4c-3 实施步）不执行以上任何一步。**

### 21.9 与 Step 2F-4 plan 的对接

| Step 2F-4 阶段 | 状态 |
|---|---|
| 方案文档（plan） | ✅ commit `e9b44e2` |
| 4a 诊断 | ✅（无代码） |
| 4b dry-run planner | ✅ commit `4c89d98` |
| 4b-verify 实跑 | ✅（无代码） |
| 4c-prereq 时间 override | ✅ commit `5dbd9ac` |
| 4c-1 writer skeleton | ✅ commit `b0ba05a` |
| 4c-2 真写入逻辑 | ✅ commit `4a66228` + checkpoint `52e81b7` |
| 4c-3 诊断 | ✅（无代码；只读报告） |
| **4c-3 peer 历史 cutoff（本节）** | **本轮** |
| 4d 90-pair 解锁 calibration_ready | 4c-3 落地 + 30 条重写之后 |

测试基线：**2171 → 2213**（+42 个新 case：`ClassifyRelativeStrengthTests` 6 / `ComputeNDayReturnAtTests` 7 / `ComputeSameDayMoveAtTests` 7 / `ComputeRelativeStrengthSummaryAtTests` 8 / `BuildHistoricalScanWithPeerCutoffTests` 3 / `WriterDryRunDoesNotReadPeerCsvTests` 1 / `WriterRealWriteWithPeerCsvTests` 6 / `WriterMissingPeerCsvDegradesTests` 2 / `WriterHardCapAndPandasHygieneTests` 2）。0 failed；10 skipped 不变。

## 22. Replay duplicate guard（Step 2F-4d-2-prereq-1）

> 4d 系列的第一个 prereq：在 writer 调 `run_predict` / `save_prediction` / `save_outcome` 之前，对每个候选 pair SELECT 检查 `prediction_log.snapshot_id = "replay_<SYMBOL>_<D>"`，命中即跳过，不写不算。**只改 writer + tests，不改 schema，不加 UNIQUE index，不提高 `_LIMIT_HARD_CAP`（仍为 30）。**

### 22.1 动机

Step 2F-4d-1 dry-run planning 发现：
- `prediction_log.snapshot_id` 是普通 TEXT，**没有 UNIQUE 约束**；
- writer 当前**没有**任何 duplicate guard；
- 重跑同一段 `(symbol, start, limit)` → 直接写入重复行（同 `snapshot_id`，不同 `prediction_log.id`），把 dashboard / calibration_inputs / correlation 的 `valid_payloads` / `paired_outcomes` / `confidence_level_summary` 全部污染。

90/120-pair 扩量会显著放大该风险（多次重跑、参数微调、批次失败重试），所以扩量前必须先有 guard。

### 22.2 实现摘要

**新 helper**：[`services/contract_replay_writer.py:_snapshot_id_exists`](../services/contract_replay_writer.py)
- 直接 `sqlite3.connect(db_path or _ps.DB_PATH)` → `SELECT 1 FROM prediction_log WHERE snapshot_id = ? LIMIT 1`；
- 捕获 `sqlite3.OperationalError`（表不存在 → 返回 `False`，方便 fresh tmp DB 不强制先 `init_db`）；
- 不调用 `init_db`，不写，不改 schema；
- `db_path=None` 时回落到 `services.prediction_store.DB_PATH`，与 `save_prediction` / `save_outcome` 的 DB 解析一致。

**guard 接入点**：`run_contract_replay` 的写入循环，在调用 `_write_one_pair` **之前**：

```python
for pair in candidate_pairs:
    snapshot_id = f"replay_{effective_symbol}_{as_of_date}"
    if _snapshot_id_exists(snapshot_id, db_path):
        skipped_pairs.append({
            "as_of_date": ...,
            "prediction_for_date": ...,
            "status": "skipped",
            "reason": "snapshot_id_already_exists",
            "snapshot_id": snapshot_id,
        })
        continue
    result = _write_one_pair(...)
```

含义：duplicate pair 完全不进 `run_predict` / `save_prediction` / `save_outcome`，零计算、零写入。

### 22.3 状态语义

- 全部 pair 都 dup → 沿用 4c-2 的现有规则（`skipped_pairs` 非空 + `written_records` 空）→ `status="partial"`；
- 部分 dup + 部分 write → `status="partial"`；
- 0 dup → `status="ok"`（行为不变）；
- `attempted_write_count` 仍等于 `len(written_records) + len(skipped_pairs)`；
- `written_prediction_count` / `written_outcome_count` 都不算 dup pair。

### 22.4 dry_run=True 不查 DB

- guard 仅在 `dry_run=False` 路径里触发；
- `dry_run=True` 完全不调 `_snapshot_id_exists`（测试 `WriterDryRunDoesNotReadPeerCsvTests` 之外新增 `WriterDuplicateGuardDryRunIsReadOnlyTests` 显式锁住该承诺）。

### 22.5 db_path 路由

- 写入循环包在 `_maybe_override_db_path(db_path)` 上下文里（`_ps.DB_PATH` 临时切换到 `db_path`）；
- guard 显式接收 `db_path`，确保查的是**写要去的那个 DB**，不会因 `_ps.DB_PATH` 被另外 monkeypatch 而错读；
- 测试 `WriterDuplicateGuardExplicitDbPathTests` 显式验证：当 `db_path` 与 `ps.DB_PATH` 不同（且 `db_path` 已含 dup、`ps.DB_PATH` 干净）时，guard 仍正确读 `db_path` 并 skip。

### 22.6 边界事实

- **不改 schema**：`prediction_log.snapshot_id` 仍是普通 TEXT，没加 UNIQUE index、没改列定义；
- **不提 hard cap**：`_LIMIT_HARD_CAP = 30` 不变（4d-2-prereq-2 才会动它）；
- **不动 `_write_one_pair`**：原来的"无 outcome 数据 → skipped: no_outcome_data" / "历史不足 → skipped: insufficient_history"两条 skip 路径完全不变；
- **不改 `predict.py` / `scanner.py` / `prediction_store.py`**：4d 系列对 prediction core / DB 层零改动；
- **不调 yfinance / 网络 / trading API**。

### 22.7 测试增量

| 测试类 | 用途 | case 数 |
|---|---|---|
| `SnapshotIdExistsHelperTests` | helper 单元：表缺失返 False / id 不存在返 False / id 存在返 True / `db_path=None` 回落 `_ps.DB_PATH` | 4 |
| `WriterDuplicateGuardSkipsTests` | dup pair → 进 `skipped_pairs`、不调 `run_predict` / `save_prediction` / `save_outcome`、`prediction_log` 行数零增长 | 5 |
| `WriterDuplicateGuardNonDuplicatePathTests` | clean DB → 正常写入路径不被 guard 误拦 | 1 |
| `WriterDuplicateGuardPartialMixTests` | 1 dup + 2 fresh → `status="partial"`，duplicates 跳过、fresh 写入 | 1 |
| `WriterDuplicateGuardDryRunIsReadOnlyTests` | `dry_run=True` 不调 `_snapshot_id_exists` | 1 |
| `WriterDuplicateGuardExplicitDbPathTests` | guard 走 `db_path` 而非 `ps.DB_PATH` | 1 |
| `WriterDuplicateGuardCliTests` | CLI `--write` 遇到 dup → stdout JSON 报告 `reason="snapshot_id_already_exists"`、`status="partial"`、`written=0` | 1 |

测试基线：**2213 → 2227**（+14 个新 case）。0 failed；10 skipped 不变；写测时间增加 < 1 秒。

### 22.8 与 Step 2F-4d 路线对接

| 子步 | 主题 | 状态 |
|---|---|---|
| 4d-1 | 90-pair dry-run planning（只读，无代码） | ✅ |
| 4d-2-prereq-1 | writer duplicate guard | ✅ commit `19800ac` |
| 4d-2-prereq-2 | `_LIMIT_HARD_CAP` 30 → 130 | ✅ commit `7d685a6` |
| **4d-2-prereq-2b（§23.5 已转 ✅）** | **CLI `--help` 文案随常量更新** | **本轮** |
| 4d-2 | 备份 → 130 dry-run → `--write 130` → 跑 calibration_inputs 验证 paired ≥ 90 | 4d-2-prereq-2b 之后 |

## 23. Replay writer hard cap 30 → 130（Step 2F-4d-2-prereq-2）

> 4d 系列的第二个 prereq：把 [`services/contract_replay_writer.py`](../services/contract_replay_writer.py) 的 `_LIMIT_HARD_CAP` 从 **30** 提高到 **130**，让单次 `--write` 能够覆盖到 ≈ 123 prediction（按当前 73% 非-flat 比例反推 90 paired），从而让 4d-2 一次性完成 ≥ 90 paired_outcomes 的扩量。**只改一个常量 + tests + docs；不改 schema，不改 default limit（仍 30），不动 duplicate guard 语义，不写主项目 DB。**

### 23.1 动机

- 4d-1 实跑显示 `plan_contract_replay` 没有 cap，能干净枚举到 90 / 120 / 150 候选对；
- 但 writer 把 `--limit 90` 静默 clamp 到 30（4c-1 引入的 `_LIMIT_HARD_CAP=30` 在 4c-2 / 4c-3 / 4d-2-prereq-1 保留了原值）；
- 30 条 → 22 paired（73% 非-flat），按此比例反推 90 paired ≈ 123 prediction → 单次写入需要 ≥ 123 的 cap 余量；
- 130 留出小幅 headroom（不到 +6%），即使下个时间窗口 flat 比例略高也能稳住 ≥ 90 paired。

### 23.2 改动

| 位置 | 改动 |
|---|---|
| [`services/contract_replay_writer.py`](../services/contract_replay_writer.py) docstring §"First-version safety" | 描述从"hard cap 30 / Step 2F-4d 才放宽"改为"hard cap 130（4d-2-prereq-2 引入）；与 duplicate guard 配套" |
| [`services/contract_replay_writer.py`](../services/contract_replay_writer.py) 常量注释 | 解释 30 → 130 的动机（≈ 123 → 90 paired）和 duplicate guard 的协同作用 |
| `_LIMIT_HARD_CAP = 30` | **`_LIMIT_HARD_CAP = 130`** |
| dry-run notes 字符串 | 已经是 `f"writer hard cap on limit is {_LIMIT_HARD_CAP}"` 模板，自动随常量更新 |

### 23.3 不变量

- **`_DEFAULT_LIMIT = 30` 保持**：调用方不传 `limit` 时仍只规划 30 对，老调用 site 行为零变化；
- **`_normalize_limit` 逻辑不变**：bool / 非 int / ≤ 0 → 回落 default（30）；> cap → clamp（现在是 130）；其他 → 原值；
- **duplicate guard 语义不变**（4d-2-prereq-1）：每个候选 pair 仍 SELECT 查 `snapshot_id` 后再 `_write_one_pair`，命中即 `skipped: snapshot_id_already_exists`；
- **`dry_run=True` 仍不写不读 DB**；
- **DB schema 不变**（仍无 UNIQUE index），`prediction_store` / `predict.py` / `scanner.py` / adapter / validator 全部零改动。

### 23.4 测试增量

`WriterLimitTests` 旧的"clamp 到 30 / 通过 30"两条测试被新的 cap 边界测试替换（不是新增并存；防止给后人留两套互相矛盾的 cap=30 / cap=130 断言）：

| 测试 | 行为锁定 |
|---|---|
| `test_default_limit_is_30` | 不传 limit → `requested_limit=30`（cap bump 不影响 default） |
| `test_legacy_limit_30_still_works` | 显式 `limit=30` → 通过；保持 4c 系列写入站点向后兼容 |
| `test_limit_90_passes_through_after_cap_bump` | `limit=90` → `requested_limit=90, candidate_pair_count=90`（旧 cap 下会被 clamp 到 30，本轮锁住新行为） |
| `test_limit_at_new_cap_130_passes_through` | `limit=130` → `requested_limit=130, candidate_pair_count=130` |
| `test_limit_just_above_cap_clamped` | `limit=131` → clamp 到 130（边界） |
| `test_limit_clamped_at_new_cap_130` | `limit=999` → clamp 到 130（远超） |
| `test_zero_limit_falls_back_to_default` | 0 → 30（行为不变） |
| `test_non_int_limit_falls_back_to_default` | `"abc"` → 30（行为不变） |
| `test_bool_limit_falls_back_to_default` | `True` → 30（行为不变；`True` 是 `bool` 不是 `int` 路径） |

`WriterHardCapAndPandasHygieneTests` 升级：

| 测试 | 行为锁定 |
|---|---|
| `test_limit_hard_cap_constant_is_130`（更名自 `..._remains_30`） | `crw._LIMIT_HARD_CAP == 130` |
| `test_default_limit_constant_unchanged_at_30`（新） | `crw._DEFAULT_LIMIT == 30`（防止有人误把 default 也改成 130） |
| `test_dry_run_notes_report_current_hard_cap`（新） | dry-run 输出 `notes` 里 cap 字符串包含 `130`，跟随常量更新 |
| `test_writer_module_does_not_import_pandas` | 不变 |

测试基线：**2227 → 2232**（+5 净增：删除 `test_limit_clamped_at_hard_cap_30` / `test_limit_at_cap_passes_through` / 重命名 `test_limit_hard_cap_constant_remains_30` 共 -3，新增 `test_limit_90_passes_through_after_cap_bump` / `test_limit_at_new_cap_130_passes_through` / `test_limit_just_above_cap_clamped` / `test_limit_clamped_at_new_cap_130` / `test_default_limit_constant_unchanged_at_30` / `test_dry_run_notes_report_current_hard_cap` / `test_legacy_limit_30_still_works` / `test_limit_hard_cap_constant_is_130` 共 +8）。0 failed；10 skipped 不变。

### 23.5 边界事实

- ❌ 未改 default `--limit`（`scripts/run_contract_replay.py` 默认仍是 30，新 cap 只对显式传更大 limit 的调用方生效）；
- ❌ 未改 duplicate guard / `_snapshot_id_exists`；
- ❌ 未改 `_write_one_pair` / planner / `prediction_store` / DB schema；
- ❌ 未跑主项目 `--write` / 未跑 90 / 120 / 130 真写入；
- ❌ 未走网络 / yfinance / trading API；
- ❌ 未触碰 stash / .claude/worktrees/ / logs/prediction_log.jsonl；
- ✅ **CLI `--help` 文案 stale 已修**（Step 2F-4d-2-prereq-2b）：[`scripts/run_contract_replay.py`](../scripts/run_contract_replay.py) 改为从 `services.contract_replay_writer` import `_DEFAULT_LIMIT` / `_LIMIT_HARD_CAP`，`--limit` 的 help 用 f-string 模板注入，CLI 文案随常量自动更新；`WriterScriptTests::test_cli_help_reports_current_hard_cap` 锁定 `--help` 输出含 `"hard cap {_LIMIT_HARD_CAP}"`、不含 stale `"hard cap 50"`。

### 23.6 4d-2 实跑前置清单（落地前必须满足）

| 前置 | 状态 |
|---|---|
| duplicate guard 已落地 | ✅ commit `19800ac` |
| hard cap 已 ≥ 130 | ✅（本节） |
| DB 备份命名约定（`avgo_agent.db.backup_pre_replay_<N>_<ts>`） | ✅（4c-2 / 4c-3-rewrite 已示范） |
| 30 条 baseline peer-aware replay 在 main DB | ✅（4c-3-rewrite 已写入） |
| dry-run plan 130 通过（`status=ok` / `returned_pair_count=130` / `anti_lookahead=true`） | ✅（4d-1 已验过 120 / 150；130 走同条码） |
| `summarize_confidence_calibration_inputs` baseline `paired=22` | ✅（4d-1 已记） |

4d-2 实跑步骤（**下轮**执行；本轮不跑）：
1. 备份：`cp avgo_agent.db avgo_agent.db.backup_pre_replay_130_<ts>`
2. dry-run：`python3 scripts/run_contract_replay.py --symbol AVGO --start 2024-01-29 --limit 130`，确认 `would_write_count=130 / status=ok`
3. 真写：上一条命令加 `--write`；duplicate guard 会自动跳过已存在的 30 条，新写 100 条
4. 校验：`prediction_log` 总数从 33 → 133；`replay_AVGO_%` 从 30 → 130
5. 跑 `summarize_confidence_calibration_inputs --limit 200 --symbol AVGO`，确认 `paired ≥ 90` + `calibration_ready=true`（或仅缺 Step 2G 评估）

## 24. Regime Diagnostics Dashboard（Step 3D-1，read-only）

### 24.1 为什么做

Step 3B 把 `pos20 × peer_diff` 4×4 lookup 当作 calibration 主路径推到 Step 3B-1
holdout（见 `tasks/step_3b1_holdout_simulation.md`），结果 holdout 上 lookup 反而
比 baseline 差（FAIL）。Step 3 calibration 系列因此暂停（`pos20` 作为 regime
feature 仍被确认有用，但 4×4 lookup 不稳定，3B-2 / 3C 冻结）。

下一步的 Step 2G exclusion 复审 / dashboard 展示 / calibration 复盘都需要把
"哪些 regime slice 在过度看多 / 在哪个月份 bias 突增 / R4 这种强动量看多组合
的真实命中率" 这件事工具化。本步只做 **read-only 诊断工具**，不写 DB、不实现
calibration、不升级 04/05/07 顶层字段、不接 trading。

### 24.2 改动文件

| 文件 | 角色 | 说明 |
|---|---|---|
| `services/regime_diagnostics_dashboard.py` | 新增 service | `summarize_regime_diagnostics_dashboard(db_path, symbol, limit, *, coded_data_dir)` |
| `scripts/regime_diagnostics_dashboard.py` | 新增 CLI | argparse 包装 service，stdout JSON `ensure_ascii=False, indent=2` |
| `tests/test_regime_diagnostics_dashboard.py` | 新增测试 | 21 个 unittest，全部 tmp_path 隔离 DB + tmp 隔离 coded_data |

未改：`predict.py` / `run_predict` / `scanner.py` / `prediction_store.py` / DB schema /
04 / 05 / 07 顶层字段 / `confidence_engine.py` / exclusion 硬软规则。

### 24.3 service 输出结构

```
{
  status: "ok" | "no_records" | "error",
  symbol, records_scanned, valid_payloads,
  paired_outcomes, pending_outcomes, calibration_ready,
  time_range: { analysis_date_min, analysis_date_max },
  pos20_quartile_bias: [
    { bucket, boundary, samples, paired, correct, wrong, pending,
      accuracy, predicted_bullish_rate, actual_up_rate, bias_gap }
    × 4   # Q1..Q4
  ],
  r4_signature: {
    samples, paired, correct, wrong, pending, accuracy,
    predicted_bullish_rate, actual_up_rate, bias_gap,
    high_confidence_count, downgrade_candidate_count,
    thresholds: { avgo_minus_soxx_20d, pos20 }
  },
  confidence_by_regime: {
    overall: { high|medium|low: {samples, paired, correct, wrong,
                                  pending, accuracy} },
    by_pos20_quartile: { high|medium|low: { Q1..Q4: {...} } },
    explicit_slices: { pos20_gt_0_62_high, pos20_gt_0_75_high }
  },
  peer_adjustment_summary: {
    by_peer_adjustment: { upgrade|hold|downgrade: {samples,...} },
    by_peer_confirm_count: { "0"|"1"|"2"|"3": {samples,...} }
  },
  soft_signal_summary: { none|high_path_risk|peer_weaken: {samples,...} },
  monthly_accuracy: [
    { month: "YYYY-MM", samples, paired, correct, wrong, pending,
      accuracy, predicted_bullish_rate, actual_up_rate, bias_gap }
  ],
  high_confidence_failure_slices: [
    { slice: name, samples, paired, correct, wrong, pending, accuracy,
      predicted_bullish_rate, actual_up_rate, bias_gap }
    × 5   # confidence_high / pos20_q3_and_high / pos20_q4_and_high
          # / r4_signature / bullish_high_pos20_gt_0_62
  ],
  warnings: [str, ...]
}
```

### 24.4 不变量 / 边界

- ❌ 不写任何 DB（`SELECT` only；`init_db` 不调用；`INSERT` / `UPDATE` / `DELETE` 全无）
- ❌ 不写任何文件（CLI 仅 stdout）
- ❌ 不 import `yfinance` / `requests` / `longbridge` / `broker` / `paper_trade`（test 17 grep 锁定）
- ❌ 不实现 calibration 公式；不修改 `confidence_system` 4 个 0.0 score 字段
- ❌ 不升级 04 / 05 / 07 contract（payload 只读）
- ❌ 不改 exclusion hard/soft 逻辑
- ✅ 只看 `snapshot_id LIKE "replay_<SYMBOL>_%"`（live 预测不会被算进来）
- ✅ 只读 `coded_data/<SYMBOL>_coded.csv`；缺 CSV 时 pos20 / R4 段降级 + warning
- ✅ status / 错误全部经 dict 表面化；`db_path` 不可读 → `status=error`，从不 raise
- ✅ pending outcome 计入 `pending_outcomes` + slice 的 `pending` 字段，但**不计入 accuracy 分母**
- ✅ pos20 < 4 个有效样本时 `pos20_quartile_bias = []` + warning，不爆 `statistics.quantiles`

### 24.5 CLI 用法

```
python3 scripts/regime_diagnostics_dashboard.py
python3 scripts/regime_diagnostics_dashboard.py --symbol AVGO --limit 450
python3 scripts/regime_diagnostics_dashboard.py --db avgo_agent.db --symbol AVGO --limit 450
python3 scripts/regime_diagnostics_dashboard.py --coded-data-dir /custom/coded_data
```

### 24.6 真数据基线（main DB，`replay_AVGO_%` = 380）

| 指标 | 值 |
|---|---|
| `paired_outcomes` | 286 |
| `pending_outcomes` | 94 |
| `calibration_ready` | true |
| `time_range` | 2023-01-03 → 2024-08-02 |
| Q1 pos20 (`<= 0.4275`) `bias_gap` | **−0.36**（系统在低位过度看空） |
| Q4 pos20 (`> 0.8198`) `bias_gap` | **+0.51**（系统在高位过度看多） |
| R4 signature `samples` / `accuracy` | 36 / **32.4%** |
| R4 `bias_gap` | **+0.68**（每条 R4 都 `偏多`，但只有 1/3 真涨） |
| R4 `downgrade_candidate_count` | 22（high-conf 且 wrong 的 R4 命中数） |

这个 baseline 直接给 Step 2G exclusion 复审定锚：R4 / Q4-high-confidence 是
最大的 over-bullish 来源。

### 24.7 测试基线

`tests/test_regime_diagnostics_dashboard.py` 新增 21 个测试，覆盖：
no_records / invalid JSON / pending / pos20 数值 / 4 桶 shape / R4 命中 /
confidence_by_regime overall + cross + explicit / peer summary（label + confirm count）/
soft signal 三类 / monthly YYYY-MM / 5 个固定 high-confidence-failure slice /
read-only DB 行计数不变 / DB error / 空 DB 不 crash / CLI smoke /
no network import / `_MIN_RECOMMENDED_PAIRS = 90` 锁定 / symbol filter（`replay_<SYMBOL>_%` 严格隔离 NVDA）

测试基线：**2233 → 2254**（+21 净增）；0 failed；10 skipped 不变。

## 25. Soft Metadata Simulator（Step 2G-5，read-only sidecar）

### 25.1 为什么做

Step 2G-3 数据再审用 380 replay 反驳了旧 `soft_signal` 假设
（`peer_weaken` / `high_path_risk` 的 accuracy 反而高于 baseline），
同时定位 R4 为唯一通过证据门槛的 over-bullish metadata 候选。Step
2G-4 把这套结论冻结为 design doc，Step 2G-4.5 schema review 把 8 条
schema-level blocker 固化成 `soft_metadata.v1` 的最终形状。Step 2G-5
是这套设计链路的第一段实现：read-only sidecar simulator，输出
`exclusion_system.extras.soft_metadata` 子结构，让 dashboard / review /
未来 sidecar 消费者**有可消费的 JSON**，但**不**触碰 04 / 05 / 07
required 字段、**不**启用 hard / forced、**不**接 trading。

### 25.2 改动文件

| 文件 | 角色 | 说明 |
|---|---|---|
| `services/soft_metadata_simulator.py` | 新增 service | `simulate_soft_metadata(payload, *, regime_features, baseline, analysis_date, final_test_cutoff)` 纯函数 + `build_soft_metadata_baseline(db_path, symbol, limit, *, coded_data_dir)` SELECT-only DB reader |
| `scripts/soft_metadata_simulator.py` | 新增 CLI | argparse 包装；`--payload-json` / `--payload-file` / `--db` / `--symbol` / `--limit` / `--coded-data-dir` / `--no-baseline` / `--analysis-date` / `--final-test-cutoff` |
| `tests/test_soft_metadata_simulator.py` | 新增测试 | 48 个 unittest，全部 tmp_path 隔离 DB + tmp 隔离 coded_data |

未改：`predict.py` / `run_predict` / `scanner.py` / `prediction_store.py` /
`projection_output_adapter.py` / `projection_output_contract.py` / DB
schema / 04 / 05 / 07 任何 required 字段 / `confidence_engine.py` /
`contradiction_engine.py` / `risk_model.py` / 任何 builder。

### 25.3 schema 锁定（soft_metadata.v1）

按 Step 2G-4.5 §5：

```
{
  schema_version: "soft_metadata.v1",
  metrics_source: "regime_diagnostics_dashboard_v1",
  metrics_window: { analysis_date_min, analysis_date_max,
                    paired_total, db_snapshot_id },
  metrics_computed_at,
  signals: [
    {
      name: "r4_overextension" | "bullish_high_pos20_residual",
      display_label, severity: "low" | "medium",
      dedup_group: "bullish_overextension",
      raw_features, trigger_context,
      historical_metrics_in_sample, holdout_status: "FAIL",
      recommended_action: "review_only",
      hard_forbidden_primary_reason, hard_forbidden_breakdown,
    }
  ],
  summary: {
    has_overextension_signal, max_severity: "none"|"low"|"medium",
    hard_exclusion_allowed: false, signal_count, primary_signal,
    warnings,
  },
}
```

**Active candidates** (Step 2G-4.5 Blocker 6 / 7)：
- `r4_overextension`
- `bullish_high_pos20_residual`

**Removed top-level candidates**：
- `bullish_peer_upgrade_overextension` → R4 `trigger_context.peer_subtype`
- `peer_weaken_metadata_only` / `high_path_risk_metadata_only` /
  `peer_path_lower_bullish` → 完全删除（dashboard 改读 raw `extras`
  字段）

**Severity enum** (Step 2G-4.5 Blocker 8)：仅 `{"low", "medium"}`；
`"high"` / `"hard"` **不存在**于 enum。`hard_exclusion_allowed`
**永远** `False`。

### 25.4 不变量 / 边界

- ❌ `simulate_soft_metadata` 是**纯函数** —— 不读 DB / 不读 CSV /
  不接网络（regime_features + baseline 由 caller 注入）
- ❌ `build_soft_metadata_baseline` 是 SELECT-only —— 不调用 `init_db` /
  不 `INSERT` / 不 `UPDATE` / 不 `DELETE` / 不写文件
- ❌ 不 import `yfinance` / `requests` / `longbridge` / `broker` /
  `paper_trade`（test `NoForbiddenImportsTests` 用 `ast` parse 锁定，
  仅检查实际 import 语句而非 docstring 文本）
- ❌ 不 import 三个 v1 stub trio（`confidence_engine` /
  `contradiction_engine` / `risk_model`）
- ❌ R4 阈值 (`5.0` / `0.62`) **必须**从 `services.regime_diagnostics_dashboard`
  import；测试 `ThresholdConstantSourceTests` 用 `assertIs(...)` 锁定
  同源 + grep 源码确认无字面量 `5.0` / `0.62` 在 R4 判断逻辑中
- ❌ 不改 04 / 05 / 07 任何 required 字段；现有
  `tests/test_exclusion_system_contract_fields.py` /
  `tests/test_confidence_system_contract_fields.py` /
  `tests/test_simulated_trade_contract_fields.py` 全部 pass
- ❌ 不启用 `hard` / `forced_exclusion` / `anti_false_exclusion_triggered`
- ❌ `analysis_date >= "2026-01-01"`（默认 cutoff）→ refuse signals +
  `summary.warnings.final_test_range_refusal`；防止 final-test
  contamination（Step 2G-4.5 §13）
- ❌ 不接 4 个 anti-false-exclusion 离线模块到主链

### 25.5 CLI 用法

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
```

### 25.6 真数据基线（main DB）

CLI baseline-only smoke (`--symbol AVGO --limit 450`):

| 字段 | 值 |
|---|---|
| `metrics_window.analysis_date_min` / `analysis_date_max` | 2023-01-03 / 2024-08-02 |
| `metrics_window.paired_total` | 286 |
| `r4_overextension.samples / paired / accuracy / bias_gap` | 36 / 34 / **0.324** / **+0.676** |
| `r4_overextension.false_exclusion_rate` | **0.3235** |
| `r4_overextension.net_benefit` | **+0.0219** |
| `bullish_high_pos20_residual.samples / paired / accuracy / bias_gap` | 47 / 47 / **0.489** / **+0.511** |
| `bullish_high_pos20_residual.false_exclusion_rate` | **0.489** |
| `bullish_high_pos20_residual.net_benefit` | **−0.0007** |
| `holdout_status` | `"FAIL"` |

R4 数字与 Step 2G-3 deep-dive / Step 3D-1 dashboard 完全一致（同 DB /
同 limit）。Residual 数字首次定量化：accuracy 0.489 / gap +0.511，
**比 R4 弱但仍是 over-bullish** —— 适合作 v1 第二候选；net_benefit
−0.0007 进一步证实"残差切片不能 hard"（按 Step 2G 设计文档 §8 /
Step 2G-3 §10 / Step 2G-4.5 §10.1.6 hard gate 全失败）。

### 25.7 测试基线

`tests/test_soft_metadata_simulator.py` 新增 **48 个测试**，覆盖
（按 Step 2G-4.5 §10 9 大类）：

| 类 | 数量 | 内容 |
|---|---|---|
| `SchemaShapeTests` | 6 | 空 payload / schema_version / signal_count == len(signals) / severity 仅 low/medium / 最多 3 条 / hard_exclusion_allowed 永远 False |
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
| `BuildBaselineTests` | 3 | 空 DB → empty baseline + warning / 缺 CSV → no residual / holdout_status 锁定 `"FAIL"` |
| `CliSmokeTests` | 2 | baseline-only stdout / payload-json + --no-baseline |

测试基线：**2254 → 2302**（+48 净增）；0 failed；10 skipped 不变。

### 25.8 边界事实

- ❌ `simulate_soft_metadata` 不接 DB / CSV / 网络；caller 通过
  `regime_features` 注入 pos20 + `avgo_minus_soxx_20d`
- ❌ `build_soft_metadata_baseline` 调用 `summarize_regime_diagnostics_dashboard`
  + 一次小 SELECT 计算 residual；reuse dashboard 的 `_read_coded_csv` /
  `_compute_pos20` / `_compute_nday_return` 私有 helper 保证一致性
- ❌ R4 阈值常量从 `services.regime_diagnostics_dashboard` import；
  Blocker 4 锁定
- ❌ severity 自动从 `historical_metrics_in_sample.{accuracy, bias_gap}`
  派生（`_classify_severity` 纯函数），不写死
- ❌ 04 / 05 / 07 required 字段全部不变（不在 simulator 写入路径上）
- ❌ `summary.hard_exclusion_allowed` 永远 `False`（任何输入下；测试
  `SchemaShapeTests::test_hard_exclusion_allowed_invariant_on_arbitrary_input`）
- ❌ Step 3 calibration 仍冻结；本步只是 sidecar metadata，不解除
  Step 3B-1 holdout FAIL 状态
- ✅ 所有 48 个新增测试 pass；2302 / 0 failed / 10 skipped；现有 2254
  基线零回归

## 26. Soft Metadata Renderer（Step 2G-6A，pure UI helper）

### 26.1 为什么做

Step 2G-6 display design（commit `0c5f421`）冻结了 dashboard / review
显示层的 11 条文案禁止词、4 种归因组合、12 项 UI safety checks。
Step 2G-6A 是该 design 的第一段实现：一个**纯函数 UI helper**，输入
`soft_metadata.v1` dict，输出**安全的展示模型** + 可选 markdown
字符串，**不**直接调用 Streamlit、**不**接 Predict / Review 页面、
**不**写任何 contract 字段。Step 2G-6B / 6C 才会把这个 helper
插入 `app.py` / `ui/predict_tab.py` / `ui/review_tab.py`。

### 26.2 改动文件

| 文件 | 角色 | 说明 |
|---|---|---|
| `ui/soft_metadata_renderer.py` | 新增纯函数 helper | `render_soft_metadata_card_data(soft_metadata, *, context, include_debug)` 输出展示 dict；`render_soft_metadata_markdown(card_data)` 输出 markdown 字符串 |
| `tests/test_soft_metadata_renderer.py` | 新增测试 | 36 个 unittest，覆盖 §3 文案禁止词 / §11 12 项 safety checks / debug toggle / context (predict / review) / 缺失字段防御 / unknown signal graceful degradation |

未改：`predict.py` / `run_predict` / `scanner.py` / `prediction_store.py` /
`projection_output_adapter.py` / `projection_output_contract.py` /
`regime_diagnostics_dashboard.py` / `soft_metadata_simulator.py` /
`app.py` / 任何现有 `ui/*` 模块 / 任何 builder / DB schema / 04 / 05 /
07 任何 required 字段。

### 26.3 输入 / 输出 API

```python
def render_soft_metadata_card_data(
    soft_metadata: dict,                # simulator's soft_metadata.v1 dict
    *,
    context: str = "predict",           # "predict" | "review"
    include_debug: bool = False,
) -> dict:
    """Pure function. Always returns a dict; never raises."""

def render_soft_metadata_markdown(card_data: dict) -> str:
    """Pure function. Empty string when card_data.visible is False."""
```

`render_soft_metadata_card_data` 输出形状：

```
{
  "visible": bool,
  "title": str,                        # "结构性偏多风险提示" / "结构性偏多归因维度（候选）"
  "subtitle": str,
  "cards": [
    {
      "name": str,                     # "r4_overextension" | "bullish_high_pos20_residual"
      "display_label": str,
      "severity": "low" | "medium",
      "badge_text": str,               # "信息提示" | "复核建议"
      "badge_tone": str,               # "info" | "caution" — never "danger" / "red"
      "summary_text": str,
      "metrics": [{"label": str, "value": str}, ...],
      "safety_note": str,              # always includes "不改变主推演方向" + "不构成交易指令"
      "expandable_details": [{"label": str, "text": str}, ...],
      "recommended_action": str,
      "holdout_status": "FAIL" | None,
    }
  ],
  "debug": dict | None,                # only when include_debug=True
  "warnings": [str, ...],
}
```

### 26.4 文案安全策略

- **禁止词** (`FORBIDDEN_COPY_TOKENS`，模块级常量)：`禁止交易` /
  `强制否定` / `必须不做` / `hard exclusion` / `forced exclusion` /
  `自动拦截` / `no_trade` / `卖出信号` / `做空信号` / `看空信号` /
  `否决主推演` / `推翻主推演` / `强制平仓` / `force close` /
  `阻止下单` / `block order` —— 共 16 个
- **测试 `ForbiddenCopyTests`** 把 6 个典型场景（empty predict /
  empty review / R4 / residual / debug / final_test_refusal）的输出
  全部 grep 一遍，确保 16 个禁止词**没有任何一个**出现
- `severity` enum 只接受 `"low"` / `"medium"`；输入 `"high"` /
  `"hard"` / 其他值会被 coerce 到 `"medium"` + 写
  `renderer_warning` 到 `warnings`
- `badge_tone` 只产生 `"info"` / `"caution"`；**永远**不是 `"danger"` /
  `"red"`（测试 `SeverityToneTests` 锁定）
- `safety_note` 由 renderer 自己生成（**不**接受 caller 注入），
  保证每张 card 都包含"不改变主推演方向"+ "不构成交易指令"+
  "07 段策略边界（不交易）不变"

### 26.5 行为规则（Step 2G-6 §4 / §9 / §11.5 / §11.7 visibility 矩阵）

| 输入 | context | visible | 显示 |
|---|---|---|---|
| `signals=[]`、无 warnings | `predict` | `False` | 完全隐藏 |
| `signals=[]`、无 warnings | `review` | `True` | "未触发 soft metadata（候选归因维度为空）" |
| `signals=[]`、`warnings=["final_test_range_refusal"]` | `predict` 或 `review` | `True` | "本预测进入 final test 保留区间，soft_metadata 已暂停" + warnings |
| `signals=[]`、warnings 仅含其他 dev warning | `predict` | `True` | 折叠 dev hint："未触发 metadata（仅有开发者 warning）" |
| `signals` 非空 | `predict` | `True` | 标题"结构性偏多风险提示" + cards |
| `signals` 非空 | `review` | `True` | 标题"结构性偏多归因维度（候选）" + 副标题强调"不是确定原因" + cards |
| `signals` 超 3 条 | 任意 | `True` | 仅渲染前 3 条（Step 2G-4.5 §9.3）|

### 26.6 R4 / Residual 文案（Step 2G-6 §6 / §7）

R4 (`r4_overextension`)：
- `display_label`: "高位跑赢同行后的偏多过热"（来自 simulator）
- `summary_text`: 包含"历史样本中该结构容易高估上涨概率"
- `metrics`: 历史命中率 32.4% / 看多 vs 实际上涨差 +67.6pp / 误杀率 32.4% / 净收益 +2.2pp
- `expandable_details` 含三条 hard 禁止理由：
  - "为什么不强制排除"（fer 32.4% > 10.0% gate）
  - "净收益不达 gate"（+2.2pp < +5.0pp gate）
  - "跨窗口 holdout"（FAIL）

Residual (`bullish_high_pos20_residual`)：
- `summary_text` 文案**弱于** R4，强调"上下文提示"
- `expandable_details` 中"净收益为负"（**不升反降** −0.1pp）—— 比 R4
  的 fer 解释更严，强调"绝对不能 hard"
- 测试 `ResidualCardTests::test_residual_summary_uses_weaker_context_wording`
  锁定 residual 不复用 R4 的强动量措辞

### 26.7 测试覆盖（36 个）

按 §11 12 项 safety checks + §3 文案禁止 + §9 visibility 矩阵：

| 类 | 数量 | 内容 |
|---|---|---|
| `EmptyPredictHiddenTests` | 2 | 空 signals + predict context → 完全隐藏 |
| `EmptyReviewVisibleTests` | 1 | 空 signals + review context → 显示"未触发" |
| `R4CardTests` | 4 | display_label / metrics / safety_note / expandable_details |
| `ResidualCardTests` | 2 | weaker context wording / negative net_benefit phrasing |
| `ForbiddenCopyTests` | 6 | 6 个典型场景 grep 16 个禁止词 |
| `HardExclusionAllowedSurfacedTests` | 1 | safety_note 必含"不改变主推演方向"+ "策略边界（不交易）不变" |
| `FinalTestRefusalVisibleTests` | 2 | predict / review 都不隐藏 final_test_range_refusal |
| `DebugToggleTests` | 2 | include_debug=False 隐藏 / =True 含 schema_version + metrics_window |
| `SeverityToneTests` | 3 | medium → caution；low → info；high 输入 coerce + renderer_warning |
| `UnknownSignalGracefulTests` | 3 | 未知 name → generic 文案；缺 label → 占位符；非 dict signal 丢弃 |
| `SignalCountMismatchTests` | 1 | summary.signal_count != len(signals) → renderer_warning |
| `MaxThreeCardsTests` | 1 | 5 signals → 仅渲染 3 |
| `NoForbiddenImportsTests` | 1 | `ast.walk` parse：禁 yfinance / requests / longbridge / broker / paper_trade / streamlit / sqlite3 / simulator / dashboard / prediction_store / 三个 v1 stub trio |
| `MarkdownRendererTests` | 4 | 空时返回空串 / R4 markdown 含 label+summary+metric+safety / review empty state / markdown 不含禁止词 |
| `DefensiveInputTests` | 3 | 非 dict 输入 → hidden / 未知 context → fallback predict / 缺 metrics → "n/a" |

测试基线：**2302 → 2338**（+36 净增）；0 failed；10 skipped 不变。

### 26.8 边界事实

- ❌ renderer **没有** import `streamlit` / `st.*` —— 完全 framework-
  agnostic；下游 `ui/` 模块自己决定怎么渲染 cards / metrics / debug
- ❌ renderer **没有** import `services.soft_metadata_simulator` /
  `services.regime_diagnostics_dashboard` / `services.prediction_store`
  —— 输入 dict 是唯一数据源
- ❌ renderer **没有** import `sqlite3` / `yfinance` / `requests` /
  `longbridge` / `broker` / `paper_trade` / 任何 trading API
- ❌ renderer **没有** import 三个 v1 stub trio
  (`confidence_engine` / `contradiction_engine` / `risk_model`)
- ❌ renderer **没**改 04 / 05 / 07 任何 required 字段路径
- ❌ renderer **没**接 Predict / Review 页面（留给 Step 2G-6B / 6C）
- ❌ renderer **没**修改任何现有 `ui/*` 模块
- ✅ renderer 是**纯函数**：相同输入 → 相同输出；无副作用；从不
  raise（异常通过 `warnings` 表面化）
- ✅ renderer 永远满足 Step 2G-6 §3.1 文案禁止 + §11 12 项 safety
  checks（测试锁定）
- ✅ Step 2G-6B / 6C 实施时只需调用 `render_soft_metadata_card_data`
  + `render_soft_metadata_markdown`，**不需要**重新决策文案 / dedup /
  visibility 规则

## 27. Soft Metadata Predict Display Hook（Step 2G-6B + 6D）

### 27.1 为什么做

Step 2G-6A renderer（commit `373f358`）就位之后，soft_metadata.v1 的
JSON 已能由 `render_soft_metadata_card_data` + `render_soft_metadata_markdown`
转成安全展示数据。Step 2G-6B 把这条 renderer 钩接到 Predict 页面，
让用户**第一次**能在 UI 上看到 metadata sidecar；同步做的 Step 2G-6D
新增 22 个 unit + AppTest 集成测试，覆盖 Step 2G-6 §11 全部 12 项 UI
safety checks。**完全不**改预测逻辑、**不**改 04 / 05 / 07 required
字段、**不**接 simulator / DB / trading。

### 27.2 改动文件

| 文件 | 类型 | 说明 |
|---|---|---|
| `ui/predict_tab.py` | 修改（+~80 行）| 新增 `from ui.soft_metadata_renderer import ...`、`_extract_soft_metadata(predict_result)` 帮助函数、`render_soft_metadata_section(soft_metadata)` 显示函数；在 `render_predict_tab` 第二层主结论与第三层证据区之间插入一行调用（Step 2G-6 §4.1 位置）|
| `tests/test_predict_tab_soft_metadata_display.py` | 新增 | 22 个 unittest（含 4 个 AppTest 集成）|
| `tasks/step_1_contract_pipeline_summary.md` | 修改 | 新增本 §27 |

未改：`predict.py` / `run_predict` / `scanner.py` / `prediction_store.py` /
`projection_output_adapter.py` / `projection_output_contract.py` /
`regime_diagnostics_dashboard.py` / `soft_metadata_simulator.py` /
`soft_metadata_renderer.py` / 任何 builder / DB schema / 04 / 05 / 07
任何 required 字段 / `simulated_trade.no_trade` 策略边界 / 任何其他
`ui/*` 模块。

### 27.3 接入位置

```
render_predict_tab(scan_result, research_result):
    ① 当前上下文        _render_layer1_context
    -------------------- divider
    ② 主结论            _render_layer2_conclusion
    ✦ Step 2G-6B hook   render_soft_metadata_section(_extract_soft_metadata(...))
    -------------------- divider
    ③ 证据区            _render_layer3_evidence
    -------------------- divider
    ④ 闭环操作区        _render_layer4_operations
```

位置在 layer 2（含 final_projection）之后、第一个 divider 之前 ——
与 Step 2G-6 §4.1 一致："在 final_projection 之后、simulated_trade
之前；让 metadata 与策略边界视觉相邻"。本项目永不显示 `simulated_trade`
独立区块（07 段策略边界 pinned），因此选择放在主结论与证据区之间。

### 27.4 soft_metadata 来源（Step 2G-6B §2 最小安全策略）

`_extract_soft_metadata(predict_result)` 按以下顺序查找；**任何位置
都没有 → 返回 `None`，renderer 在 predict context 下隐藏整个区块**：

1. `predict_result['contract_payload']['exclusion_system']['extras']['soft_metadata']`
   —— canonical 位置；未来 pipeline 或 adapter 写入时使用
2. `predict_result['soft_metadata']` —— caller 直接注入到 predict_result
3. `st.session_state['soft_metadata_for_predict']` —— 测试 / 开发注入

**关键不变量**：
- ❌ 本轮**不**改 `run_predict` 主链；**不**让主链产生 soft_metadata
- ❌ 显示函数**不**调用 `services.soft_metadata_simulator`（测试
  `IsolationTests::test_section_does_not_call_simulator` 锁定）
- ❌ 显示函数**不**读 DB / CSV / 网络（测试
  `IsolationTests::test_section_does_not_call_prediction_store` 锁定）
- ❌ `ui/predict_tab.py` 模块**不** import `soft_metadata_simulator`
  （`ast.walk` 锁定）—— 让"未来在哪里注入 soft_metadata"成为独立
  待解决问题，不被本步绑定

### 27.5 显示函数（thin wrapper）

```python
def render_soft_metadata_section(soft_metadata: dict | None) -> dict:
    """Render via the pure renderer + st.markdown.
    Returns card_data dict for testability; never raises."""
    payload = soft_metadata if isinstance(soft_metadata, dict) else {}
    card_data = render_soft_metadata_card_data(payload, context="predict")
    if not card_data.get("visible"):
        return card_data
    markdown = render_soft_metadata_markdown(card_data)
    if markdown:
        st.markdown(markdown)
    return card_data
```

- **不**自己拼安全文案（renderer 已生成 markdown 文本）
- **不**重新解释 severity / badge_tone（Step 2G-6A 已锁定）
- **不**显示 forbidden words（renderer 保证 + 本步 22 个测试 grep 锁定）
- 调用 `render_soft_metadata_card_data` + `render_soft_metadata_markdown`
  以外的 `ui.soft_metadata_renderer` 公开 API：无（消费者只用这两个
  函数）

### 27.6 Step 2G-6D UI safety tests

`tests/test_predict_tab_soft_metadata_display.py` 共 22 个测试：

| 测试类 | 数量 | 内容 |
|---|---|---|
| `ExtractSoftMetadataTests` | 6 | None / 非 dict / canonical 路径 / 顶层 fallback / canonical 优先 / malformed extras / Streamlit context 缺失 graceful |
| `RenderSectionUnitTests` | 6 | None 不调 markdown / 空 signals 不调 / 非 dict 不调 / R4 调 markdown 含安全文案 / final_test_refusal 调 markdown 含 subtitle / 6 场景 grep 16 个禁止词 |
| `IsolationTests` | 3 | 不调 simulator (`simulate_soft_metadata` / `build_soft_metadata_baseline`) / 不调 `prediction_store.save_prediction` / `_get_conn` / 模块 import 不含 simulator |
| `HardExclusionSafetyTests` | 2 | hard_exclusion_allowed=false 不渲染 hard / forced / no_trade 词 / unknown signal graceful + 仍出现 "未识别" 文案 |
| `PredictTabAppTests` (AppTest) | 4 | R4 → 页面文本含 "高位跑赢同行后的偏多过热" + "32.4%" + 不含 16 个禁止词 / 空 signals → 标题不出现 / final_test_refusal → 页面文本含 "final test 保留区间" / None → 渲染 nothing |

**AppTest 已就位**：本轮直接通过 `streamlit.testing.v1.AppTest` 验证
集成行为（不需要等到独立的 Step 2G-6D-2）。AppTest 用 `from_string`
构造最小脚本，注入 fixture soft_metadata，跑 `at.run()`，断言
`at.markdown` 集合包含 / 不含期望文本。

### 27.7 测试基线

| 命令 | 结果 |
|---|---|
| `pytest tests/test_predict_tab_soft_metadata_display.py -q` | **22 passed in 1.08s** |
| `pytest tests/test_soft_metadata_renderer.py tests/test_predict_tab_soft_metadata_display.py -q` | **58 passed in 0.88s** |
| `pytest tests/test_soft_metadata_simulator.py tests/test_regime_diagnostics_dashboard.py -q` | **69 passed in 0.38s** |
| `pytest -q`（全量）| **2360 passed, 10 skipped, 26 warnings, 65 subtests passed in 9.95s** |

测试基线累积：**Step 2G-6B 起点 2338 → 2360**（+22 净增）；0 failed；
10 skipped 不变。

### 27.8 边界事实

- ❌ **没**改 `predict.py` / `run_predict` / `scanner.py` /
  `prediction_store.py` / 任何 builder
- ❌ **没**改 04 / 05 / 07 任何 required 字段
- ❌ **没**改 `final_projection` / `simulated_trade` / `confidence_system`
  任何字段（Predict 页面其他渲染路径完全不变）
- ❌ **没**让 Predict 页面调用 `services.soft_metadata_simulator`
  （`ast` 锁定模块未 import；`patch` 锁定函数未调用）
- ❌ **没**让 Predict 页面读 DB（`patch` 锁定 `prediction_store` 未调用）
- ❌ **没**接 `yfinance` / `requests` / 任何网络
- ❌ **没**接 trading API / `longbridge` / `broker` / `paper_trade`
- ❌ **没**启用 `hard` / `forced_exclusion` / `anti_false_exclusion_triggered`
- ❌ **没**重写 renderer 文案（safety_note / display_label / metrics 全部
  来自 renderer，不在 predict_tab 重新拼装）
- ❌ **没**让 forbidden words（16 个）出现在 `st.markdown` 实际调用
  参数中（unit + AppTest 双重 grep 锁定）
- ❌ **没**触碰 2026-01-01 之后 final test range（renderer 内部
  `final_test_range_refusal` 强制 visible 已在 Step 2G-6A 锁定，
  本步通过 fixture 测试此行为在 Predict 页面也保持）
- ✅ Predict 页面的 layer 2 主结论与 layer 3 证据区之间插入一行
  display hook；当 `predict_result` 不含 soft_metadata 时**完全
  隐藏**（不改变现有页面视觉）
- ✅ **2360 / 0 failed / 10 skipped**；现有 2338 基线零回归

## 28. Soft Metadata Enrichment Hook（Step 2G-6B.2 / 6B.3，read-only）

### 28.1 为什么做

Step 2G-6B Predict display hook（commit `33733d3`）就位之后，
`canonical` 位置 `predict_result["contract_payload"]["exclusion_system"]["extras"]["soft_metadata"]`
**几乎从不被填充** —— `run_predict` 主链未改，没有任何代码路径自动
生成 `soft_metadata`，所以 Predict 页面 99% 时间下隐藏整个区块。
Step 2G-6B.1 injection path design（commit `92441e0`）把候选方案
A-E 比较后推荐方案 B（post-run sidecar enrichment helper）。Step
2G-6B.2 实现这个 helper；Step 2G-6B.3 在 Predict 页面接入；同 step
完成可避免"helper 写完没接 UI / 接了 UI 没测"的拆分浪费。

### 28.2 改动文件

| 文件 | 类型 | 说明 |
|---|---|---|
| `services/soft_metadata_injection.py` | 新增 service | `enrich_predict_result_with_soft_metadata(predict_result, *, scan_result, research_result, baseline, regime_features, analysis_date, force, final_test_cutoff)` 纯函数 + `_extract_regime_features` 4-级 fallback helper |
| `ui/predict_tab.py` | 修改（+13 行）| 新增 `from services.soft_metadata_injection import enrich_predict_result_with_soft_metadata`；在 `render_predict_tab` 显示 hook 前 try/except 包裹调用，把 enriched payload 传给已有 `_extract_soft_metadata` + `render_soft_metadata_section` |
| `tests/test_soft_metadata_injection.py` | 新增 | 26 个 unittest |
| `tests/test_predict_tab_soft_metadata_display.py` | 修改 | +7 个测试（5 个 unit `EnrichmentIntegrationTests` + 2 个 AppTest `EnrichmentAppTests`），从 22 → 29 |
| `tasks/step_1_contract_pipeline_summary.md` | 修改 | 新增本 §28 |

未改：`predict.py` / `run_predict` / `scanner.py` / `prediction_store.py` /
`projection_output_adapter.py` / `projection_output_contract.py` /
`regime_diagnostics_dashboard.py` / `soft_metadata_simulator.py` /
`soft_metadata_renderer.py` / 任何 builder / DB schema / 04 / 05 / 07
任何 required 字段 / `simulated_trade.no_trade` 策略边界 / 任何其他
`ui/*` 模块。

### 28.3 enrichment helper 行为

```python
def enrich_predict_result_with_soft_metadata(
    predict_result: dict,
    *,
    scan_result: dict | None = None,
    research_result: dict | None = None,  # accepted for API stability; not used in v1
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

不变量（测试锁定）：

- ❌ **input dict 不被原地修改**（`InputImmutabilityTests` deep-copy
  snapshot 锁定）
- ❌ **不写 DB**（`IsolationTests` patch `prediction_store.save_prediction`
  / `_get_conn` 锁定 not_called）
- ❌ **不调** `build_soft_metadata_baseline`（patch 锁定 not_called）
- ❌ 模块不 import `prediction_store` / `regime_diagnostics_dashboard` /
  `yfinance` / `requests` / `longbridge` / `broker` / `paper_trade` /
  v1 stub trio（`ast.walk` parse 锁定）
- ✅ **canonical 位置被填充**：
  `out["contract_payload"]["exclusion_system"]["extras"]["soft_metadata"]`
  写入 simulator 输出
- ✅ **already-set wins by default**：canonical 已有 dict 时返回 input
  shallow copy，不覆盖；显式 `force=True` 才覆盖
- ✅ **04 / 05 / 07 required 字段 byte-stable**：
  `RequiredFieldsByteStableTests` 用结构化 subset 比较 `exclusion_required`
  / `confidence_scores` / `simulated_trade` / `final_projection`
  before vs after
- ✅ **缺 contract_payload / extras 层级时安全创建**（不污染 input；
  `CanonicalWriteTests::test_missing_contract_payload_creates_layers_safely`
  / `test_missing_extras_creates_extras_dict` 锁定）
- ✅ **2026 cutoff 透传**：`analysis_date` 默认从
  `contract_payload.current_structure.analysis_date` 提取；显式
  override 优先；`>= "2026-01-01"` 触发 simulator refusal +
  `final_test_range_refusal` warning

`_extract_regime_features` 4 级 fallback：
1. `predict_result["regime_features"]`
2. `predict_result["contract_payload"]["exclusion_system"]["extras"]["regime_features"]`
3. `scan_result["regime_features"]`
4. `scan_result["extras"]["regime_features"]`

显式 `regime_features=` kwarg **优先**（在 helper 主入口处理；不进
fallback 链）。任何一级都没有 → simulator 收到 `None` → emit
`signals=[]` + `missing_regime_features` warning（不 crash）。

### 28.4 Predict 接入方式

`render_predict_tab` Layer 2 主结论之后插入：

```python
try:
    _enriched_for_display = enrich_predict_result_with_soft_metadata(
        predict_result, scan_result=scan_result,
        research_result=research_result,
        baseline=st.session_state.get("soft_metadata_baseline"),
    )
except Exception:  # noqa: BLE001 — UI must never crash on metadata
    _enriched_for_display = predict_result
render_soft_metadata_section(_extract_soft_metadata(_enriched_for_display))
```

设计要点：
- **try/except** 包裹：helper 是纯函数 + 不 raise（合约保证），但 UI
  防御性兜底，不让 metadata 路径影响主流程
- **`baseline=st.session_state.get("soft_metadata_baseline")`**：调用方
  可在 `app.py` 启动时预先 build baseline 缓存到 session_state；
  当前未做缓存，传 None → simulator 仍 emit signals + `missing_baseline`
  warning（renderer visibility 矩阵显示 dev hint）
- **不重写 renderer 文案**：直接调
  `render_soft_metadata_section(_extract_soft_metadata(...))`；
  display hook + renderer 已锁定文案安全 + visibility 规则
- **不写 DB / 不写 session_state**（除了 caller 预设的 baseline 缓存
  位置；helper 自身不写）
- **不 modify `predict_result`**：enriched 仅用于 display；不回写
  `prediction_log` / `outcome_log` / `review_log`

### 28.5 测试基线

| 命令 | 结果 |
|---|---|
| `pytest tests/test_soft_metadata_injection.py -q` | **26 passed in 0.03s** |
| `pytest tests/test_predict_tab_soft_metadata_display.py tests/test_soft_metadata_renderer.py -q` | **65 passed in 0.90s** |
| `pytest tests/test_soft_metadata_simulator.py tests/test_regime_diagnostics_dashboard.py -q` | **69 passed in 0.39s** |
| `pytest -q`（全量） | **2393 passed, 10 skipped, 26 warnings, 65 subtests passed in 10.18s** |

测试覆盖矩阵（共 33 个新增）：

| 测试类（文件） | 数量 | 内容 |
|---|---|---|
| `InputImmutabilityTests` (`test_soft_metadata_injection.py`) | 3 | input deepcopy snapshot 不变 / 返回 dict 与 input 不同对象 / 非 dict 输入 → `{}` |
| `CanonicalWriteTests` | 5 | canonical 填充 / already-set 不覆盖 / `force=True` 覆盖 / 缺 contract_payload 安全创建 / 缺 extras 安全创建 |
| `RequiredFieldsByteStableTests` | 3 | 04 required / 05 confidence + scores / 06 final_projection / 07 simulated_trade 全 byte-stable；`force=True` 也不动 required |
| `SimulatorPassthroughTests` | 5 | baseline / analysis_date / override 优先 / 2026 refusal / final_test_cutoff 五项透传 |
| `RegimeFeaturesExtractionTests` | 7 | explicit kwarg 优先 / predict_result top-level / contract extras / scan_result / scan extras / no features → empty + warning / `_extract_regime_features` 直接单元测试 |
| `IsolationTests` | 3 | 不调 `build_soft_metadata_baseline` / 不调 `prediction_store` / `ast.walk` import 锁定 |
| `EnrichmentIntegrationTests` (`test_predict_tab_soft_metadata_display.py`) | 5 | helper 从 predict_tab 可 import / canonical 被填充触发 R4 显示 / fallback 不崩 / no forbidden words / 2026 refusal subtitle 可见 |
| `EnrichmentAppTests` (Streamlit) | 2 | with features → 页面真实显示 R4 card；without features → dev hint 可见但 R4 card 不出现 |

测试基线累积：**Step 2G-6B.2/6B.3 起点 2360 → 2393**（+33 净增）；
0 failed；10 skipped 不变。

### 28.6 边界事实

- ❌ **没**改 `predict.py` / `run_predict` / `scanner.py` /
  `prediction_store.py` / 任何 builder
- ❌ **没**改 04 / 05 / 07 任何 required 字段
- ❌ **没**改 `final_projection` / `simulated_trade` / `confidence_system`
  任何字段（snapshot 测试锁定 byte-stable）
- ❌ **没**写 DB（service 不接 sqlite / `prediction_store`；UI hook 不
  写 session_state / DB）
- ❌ **没**接 `yfinance` / `requests` / 任何网络
- ❌ **没**接 trading API / `longbridge` / `broker` / `paper_trade`
- ❌ **没**启用 `hard` / `forced_exclusion` / `anti_false_exclusion_triggered`
- ❌ **没**触碰 2026-01-01 之后 final test range（cutoff 透传 +
  refusal warning visibility 锁定）
- ❌ **没**调 `build_soft_metadata_baseline`（service 与 UI 都不主动
  读 DB；baseline 由 caller 经 session_state 注入）
- ✅ Predict 页面 canonical 位置**首次被自动填充** —— 当上游
  pipeline 提供 `regime_features` 时，R4 / residual 立即可见
- ✅ 当前 baseline 未缓存：production app 中每次预测都会有
  `missing_baseline` warning + renderer 显示 dev hint；后续可加
  baseline 缓存优化（不属于 6B.3 范围）
- ✅ **2393 / 0 failed / 10 skipped**；现有 2360 基线零回归

## 29. Soft Metadata Baseline Cache + Regime Features Source（Step 2G-6B.6/6B.7）

### 29.1 为什么做

Step 2G-6B.3 checkpoint（commit `4e60df5`）+ Step 2G-6B.4/6B.5 design
（commit `35b239d`）已 honest 列出 production 看不到 R4 的两个根因：
**baseline=None**（→ historical metrics n/a / dev hint）+
**regime_features=None**（→ R4 / residual 不触发）。Step 2G-6B.6 实现
session_state baseline cache，Step 2G-6B.7 在 `scanner.run_scan` 暴露
`regime_features` 字段；同 step 完成可一次解决"production 看不到完整
R4 card"。

### 29.2 改动文件

| 文件 | 类型 | 说明 |
|---|---|---|
| `services/regime_features_builder.py` | 新增 service | `build_regime_features(coded_df, peer_dfs, target_date_str, *, final_test_cutoff)` 纯函数；返回 `{pos20, avgo_minus_soxx_20d, source, as_of_date, data_cutoff_date, warnings}` |
| `scanner.py` | 修改（+13 行）| `run_scan` 末尾 try/except 调 `build_regime_features`；新增 `scan_result["regime_features"]` 字段；deferred import 不引入 hard dependency |
| `ui/soft_metadata_baseline_cache.py` | 新增 ui helper | `ensure_soft_metadata_baseline_cached(*, symbol, limit, session_state)` lazy build + cache `session_state["soft_metadata_baseline"]`；失败时设 `soft_metadata_baseline_error`；从不 raise |
| `ui/predict_tab.py` | 修改（+8 行）| import baseline cache helper；`render_predict_tab` 调用 cache helper 替代之前的 `session_state.get("soft_metadata_baseline")` 直读 |
| `tests/test_soft_metadata_baseline_cache.py` | 新增 | 8 个 unittest（cache miss/hit / builder 异常 / 非 dict / 无 session / symbol limit 透传 / `ast.walk` import + prediction_store 锁定）|
| `tests/test_regime_features_from_scan.py` | 新增 | 17 个 unittest（pos20 / SOXX diff / 输出 shape / 2026 cutoff / `ast.walk` import / DataFrame 不变 / scanner 集成 smoke 2 项）|
| `tests/test_predict_tab_soft_metadata_display.py` | 修改 | +2 个测试（baseline cache helper 可 import / 带 baseline 的 AppTest 显示真实 metrics 32.4% 不显示 n/a）|
| `tasks/step_1_contract_pipeline_summary.md` | 修改 | 新增本 §29 |

未改：`predict.py` / `run_predict` / `prediction_store.py` /
`projection_output_adapter.py` / `projection_output_contract.py` /
`regime_diagnostics_dashboard.py` / `soft_metadata_simulator.py` /
`soft_metadata_renderer.py` / `soft_metadata_injection.py` / 任何
builder / DB schema / 04 / 05 / 07 任何 required 字段 /
`simulated_trade.no_trade` 策略边界 / 任何其他 `ui/*` 模块。

### 29.3 baseline cache 行为

```python
def ensure_soft_metadata_baseline_cached(
    *, symbol: str = "AVGO", limit: int = 450, session_state: Any = None,
) -> dict | None:
    """Lazy-build + cache soft_metadata_baseline. Never raises."""
```

不变量（`tests/test_soft_metadata_baseline_cache.py` 8 个测试锁定）：

- ✅ **cache hit**：`session_state[CACHE_KEY]` 已是 dict → 直接返回，不调 builder
- ✅ **cache miss**：调 `build_soft_metadata_baseline(symbol, limit)` 一次 → 写入 cache
- ✅ **builder exception**：捕获 → 写 `session_state[ERROR_KEY] = "baseline_build_failed: ..."` → 返回 None
- ✅ **builder 返回非 dict**：不缓存；返回 None
- ✅ **session_state 不可用**（非 Streamlit context）：仍调 builder 一次（无缓存收益但不 crash）
- ✅ **symbol / limit 透传**给 builder
- ❌ 模块**不**写 DB / 不写文件 / 不接网络
- ❌ 模块**不** import `prediction_store` / `yfinance` / `requests` /
  `longbridge` / `broker` / `paper_trade` / `sqlite3` / v1 stub trio
  （`ast.walk` 锁定）
- ❌ 不在 import 时执行（lazy）

### 29.4 regime_features 计算口径

```python
def build_regime_features(
    coded_df, peer_dfs: dict | None, target_date_str: str,
    *, final_test_cutoff: str = "2026-01-01",
) -> dict:
    """Pure function. Returns regime_features dict; never raises."""
```

| 字段 | 计算 |
|---|---|
| `pos20` | `(Close_D − rolling_low_20) / (rolling_high_20 − rolling_low_20)`，window 长度 20，含当日 |
| `avgo_minus_soxx_20d` | `(AVGO_Close_D / AVGO_Close_{D-20} − 1) × 100 − (SOXX_Close_D / SOXX_Close_{D-20} − 1) × 100`（pp）|
| `source` | 固定 `"scan_result"` |
| `as_of_date` | `target_date_str[:10]`（YYYY-MM-DD） |
| `data_cutoff_date` | == `as_of_date`（anti-lookahead by construction） |
| `warnings` | list[str] —— `pos20_skipped: <reason>` / `missing_soxx_coded_df` / `soxx_20d_return_unavailable` / `final_test_range_refusal` 等 |

不变量（`tests/test_regime_features_from_scan.py` 17 个测试锁定）：

- ✅ **anti-lookahead**：只读 `Date <= target_date` 的行（与
  `scanner._get_nday_return` 同语义）
- ✅ **DataFrame 不被原地修改**（`pd.testing.assert_frame_equal`
  before / after snapshot）
- ✅ **SOXX 缺失**：`avgo_minus_soxx_20d=None` + warning（不 crash）
- ✅ **历史不足 20 日**：`pos20=None` + `pos20_skipped: insufficient_history`
- ✅ **2026 cutoff 双重锁定**：`as_of_date >= "2026-01-01"` →
  warnings 含 `"final_test_range_refusal"`（与 simulator 双重防护）
- ❌ 模块**不** import `yfinance` / `requests` / `sqlite3` / 网络 / trading
  （`ast.walk` 锁定）

### 29.5 Predict 接入方式

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
except Exception:  # noqa: BLE001
    _enriched_for_display = predict_result
render_soft_metadata_section(_extract_soft_metadata(_enriched_for_display))
```

设计要点：
- **两个 try/except** 防御兜底：baseline cache 失败 → baseline=None
  （metric 显示 n/a 但 R4 仍可触发）；enrichment 失败 → 用原
  predict_result（display 隐藏区块）—— UI 永不崩
- **baseline 来自 session_state cache**（lazy build；session 内复用）
- **scan_result 透传**：helper 4 级 fallback 自动从
  `scan_result["regime_features"]` 命中（scanner.run_scan 已写入；Step
  2G-6B.7）
- **不重写 renderer 文案**：renderer + display hook 已锁定文案安全
- **不**回写 session_state（除 cache helper 自身写入 baseline / error
  键）

### 29.6 测试基线

| 命令 | 结果 |
|---|---|
| `pytest tests/test_soft_metadata_baseline_cache.py -q` | **8 passed in 0.03s** |
| `pytest tests/test_regime_features_from_scan.py -q` | **17 passed in 0.53s** |
| `pytest tests/test_predict_tab_soft_metadata_display.py tests/test_soft_metadata_injection.py -q` | **57 passed in 0.90s** |
| `pytest tests/test_soft_metadata_simulator.py tests/test_regime_diagnostics_dashboard.py -q` | **69 passed in 0.39s** |
| `pytest -q`（全量） | **2420 passed, 10 skipped, 26 warnings, 65 subtests passed in 10.93s** |

测试覆盖（共 27 个新增）：

| 测试类 / 文件 | 数量 | 内容 |
|---|---|---|
| `CacheBehaviorTests` (`test_soft_metadata_baseline_cache.py`) | 6 | cache miss / hit / builder 异常 / 非 dict / 无 session 不 crash / symbol+limit 透传 |
| `IsolationTests`（同上） | 2 | `ast.walk` 锁定禁 import + `prediction_store` 不调 |
| `Pos20Tests` (`test_regime_features_from_scan.py`) | 3 | top-of-range / insufficient_history / missing_target_date |
| `SoxxDiffTests` | 4 | 正常计算 / 缺 SOXX / 缺 peer_dfs / SOXX 不足 |
| `OutputShapeTests` | 4 | 必填字段 / data_cutoff == as_of / 空 target_date / 缺 coded_df |
| `FinalTestCutoffTests` | 2 | >=2026 emit refusal / <2026 不 emit |
| `IsolationTests`（同上） | 2 | `ast.walk` import 锁定 / DataFrame 不被改 |
| `ScannerIntegrationSmokeTests` | 2 | scanner.run_scan 暴露 regime_features / 失败时 fallback None |
| `EnrichmentIntegrationTests::test_baseline_cache_helper_importable_from_predict_tab` | 1 | Predict tab import 锁定 |
| `EnrichmentAppTests::test_apptest_predict_result_with_baseline_shows_real_metrics` | 1 | AppTest 验证带 baseline 时显示 32.4% 而非 n/a |

**测试基线**：**Step 2G-6B.6/6B.7 起点 2393 → 2420**（+27 净增）；
0 failed；10 skipped 不变。

### 29.7 边界事实

- ❌ **没**改 `predict.py` / `run_predict` / `prediction_store.py` /
  任何 builder
- ❌ **没**改 04 / 05 / 07 任何 required 字段
- ❌ **没**改 `final_projection` / `simulated_trade` /
  `confidence_system` 任何字段
- ❌ **没**写 DB（baseline cache + features builder + scanner 改动
  全程 SELECT-free / IO-free）
- ❌ **没**接 `yfinance` / `requests` / 任何网络（features builder
  从已有 pandas df 计算；scanner 已有 `load_peer_coded` SELECT-only）
- ❌ **没**接 trading API / `longbridge` / `broker` / `paper_trade`
- ❌ **没**启用 `hard` / `forced_exclusion` / `anti_false_exclusion_triggered`
- ❌ **没**触碰 2026-01-01 之后 final test range（features builder 也
  锁定 refusal warning；与 simulator 双重防护）
- ✅ **scanner.run_scan 现在暴露 `regime_features`** —— Predict 页面
  自动消费 → R4 / residual 满足条件时立即触发
- ✅ **session_state baseline cache** —— `historical_metrics_in_sample`
  显示真实数字（accuracy / bias_gap / fer / nb），不再是 n/a
- ✅ **production 显示 dev hint 的两个根因都已消除** —— 当 features
  满足 R4 condition 时，Predict 页面真实显示完整 R4 card（含 32.4%
  accuracy / +67.6pp bias_gap 等真实指标）
- ✅ **AppTest 验证**：`test_apptest_predict_result_with_baseline_shows_real_metrics`
  断言页面文本含 "32.4%"、不含 "n/a"、不含 16 个 forbidden words
- ✅ **2420 / 0 failed / 10 skipped**；现有 2393 基线零回归

## 30. Soft Metadata Review Display（Step 2G-6C）

### 30.1 为什么做

Step 2G-6B.6/6B.7 已经把 Predict 侧 production 链路打通，Predict 页面
能在 R4 condition 满足时显示完整 R4 metadata card。Step 2G-6 §8 设计
文档要求 **Review 页面也要消费 metadata**，作为 4 种 outcome × metadata
触发组合的**候选归因维度**（possible attribution，不是 definitive
cause）。本步在 Review 页面（`_render_review_result` 在 `predict_tab.py`
内的复盘结果面板）接入 soft_metadata，并新增独立 `tests/test_review_tab_soft_metadata_display.py`
覆盖 4 种组合 + 16 forbidden words + isolation。

### 30.2 改动文件

| 文件 | 类型 | 说明 |
|---|---|---|
| `ui/review_tab.py` | 修改（+~140 行）| 新增 `_classify_review_attribution` / `build_review_soft_metadata_card_data` / `render_review_soft_metadata_section` 三个 review-context helper；module-top `import streamlit as st`；4 outcome × metadata 组合的中文 label / explanation 常量 |
| `ui/predict_tab.py` | 修改（+~25 行）| `_render_review_result` 在已有方向 / 错误分类 metric 之后调 `render_review_soft_metadata_section`；从 session_state 读取 enriched predict_result（在 layer-2 主结论显示时一次性 stash）|
| `tests/test_review_tab_soft_metadata_display.py` | 新增 | 28 个 unittest（含 3 个 AppTest）|
| `tasks/step_1_contract_pipeline_summary.md` | 修改 | 新增本 §30 |

未改：`predict.py` / `run_predict` / `scanner.py` / `prediction_store.py` /
`projection_output_adapter.py` / `projection_output_contract.py` /
`regime_diagnostics_dashboard.py` / `soft_metadata_simulator.py` /
`soft_metadata_renderer.py` / `soft_metadata_injection.py` /
`regime_features_builder.py` / `soft_metadata_baseline_cache.py` /
任何 builder / DB schema / 04 / 05 / 07 任何 required 字段 /
`review_log` 任何 required 字段 / `review_orchestrator` /
`review_agent` / 任何其他 `ui/*` 模块。

### 30.3 Review 接入位置

`_render_review_result(review_result)` 在 `ui/predict_tab.py` 内，是
**per-prediction** 复盘结果面板（用户点击"运行确定性复盘"后的输出）。
现在结构：

```
_render_review_result:
    复盘得分 N/M（XX%）
    主要问题 / 三项判断均正确
    维度对比表（开盘 / 路径 / 收盘）
    错误分析详情（折叠）
    完整复盘摘要（折叠）
    方向判断 / 错误分类（两栏 metric）
    ✦ Step 2G-6C — soft metadata possible-attribution 区块（新增）
```

接入逻辑：
1. 从 `comparison.direction_match`（0/1/None）派生 `prediction_correct: bool | None`
2. 从 `review_result.soft_metadata`（如果未来 review_result 自带）或
   `session_state["review_predict_result_for_metadata"]`（layer-2
   显示时 stash 的 enriched predict_result）提取 `soft_metadata`
3. 调 `render_review_soft_metadata_section(soft_metadata, prediction_correct=...)`
4. 整段 try/except 包裹 —— review 永远不会因 metadata 路径崩溃

`render_predict_tab` 在 layer-2 显示 hook 之后增加 1 行：将
`_enriched_for_display`（已含 canonical extras.soft_metadata）stash
到 `st.session_state["review_predict_result_for_metadata"]`，让后续
review 面板复用同一份 metadata，**不**重新计算 enrichment。

### 30.4 归因规则（4 outcome × metadata）

按 Step 2G-6 §8 4-quadrant：

| outcome | metadata 触发 | `kind` | label | explanation |
|---|---|---|---|---|
| **wrong** | ✅ R4 / residual 触发 | `possible_attribution` | "可能归因维度（候选，不是确定原因）" | "本次预测错误，且结构性偏多 metadata 已触发。该 metadata 是可能的归因维度之一，**不是确定原因**；不改变主推演方向，也不构成交易指令。" |
| **correct** | ✅ R4 / residual 触发 | `triggered_but_not_error` | "metadata 已触发但本次预测正确（结构幸存）" | "结构性偏多 metadata 触发，但本次预测**仍然正确**（属结构幸存）。这个信号仅作为风险参考；主推演方向已被实际行情验证。" |
| **wrong** | ❌ 无 metadata | `no_attribution` | "未触发 soft metadata（不强行归因）" | "本次预测虽然错误，但未触发 soft metadata。**不强行归因**到 metadata；请结合其他错误维度（方向 / 路径 / 五态）分析。" |
| **correct** | ❌ 无 metadata | `no_metadata` | "无 metadata 显示" | "" |
| pending（None） | ✅ | `triggered_but_not_error` | 同上 | 防御性 fallback：未到 outcome 时仍给一个安全 band |
| pending（None） | ❌ | `no_metadata` | 同上 | empty state |

强约束：
- ❌ **不**写 `review_log` 任何 required 字段（`error_category` /
  `root_cause` / `confidence_note` / `watch_for_next_time` / etc.）
- ❌ **不**写 `prediction_log` 任何字段
- ❌ **不**写 DB
- ❌ 归因 **只**作为 UI 文本 / `card_data["review_attribution"]` 字段
- ❌ 归因**永远**带"候选 / 不是确定原因 / 不强行归因"措辞，避免被
  消费者误读为确定性结论
- ❌ 不出现 16 个 forbidden words（`ForbiddenCopyTests` 5 个场景
  grep 锁定）

### 30.5 helper API

```python
def _classify_review_attribution(
    soft_metadata: Any, *, prediction_correct: bool | None,
) -> str:
    """Pure. Returns one of {possible_attribution, triggered_but_not_error,
    no_attribution, no_metadata}."""

def build_review_soft_metadata_card_data(
    soft_metadata: dict | None, *, prediction_correct: bool | None = None,
) -> dict:
    """Pure. Returns renderer card_data with appended ``review_attribution``
    block. Forces visible=True for no_attribution case so user sees
    explicit guidance. Never raises."""

def render_review_soft_metadata_section(
    soft_metadata: dict | None, *, prediction_correct: bool | None = None,
) -> dict:
    """Thin wrapper: builds card_data + emits st.markdown. Returns
    card_data for testability. Never raises."""
```

不变量（`tests/test_review_tab_soft_metadata_display.py` 28 个测试锁定）：

- ✅ **input dict 不被原地修改**（`BuildReviewCardDataTests::test_input_dict_is_not_mutated`）
- ✅ **review-context renderer 复用**：`render_soft_metadata_card_data(payload, context="review")` —— 不重新实现 visibility / 文案
- ✅ **`no_attribution` 强制 visible**：even when renderer would hide
  empty signals in some contexts, the helper forces visible+subtitle so
  the user sees explicit "不强行归因" guidance
- ❌ 模块**不** import `services.soft_metadata_simulator` /
  `services.soft_metadata_injection` / `prediction_store` /
  `yfinance` / `requests` / 网络 / trading（`ast.walk` 锁定）
- ❌ render 路径**不**调 simulator / baseline build / DB
  （`patch` + `assert_not_called` 锁定）
- ❌ 16 forbidden words 在所有 5 个场景输出都不出现（包括
  `final_test_range_refusal`）

### 30.6 测试覆盖

| 命令 | 结果 |
|---|---|
| `pytest tests/test_review_tab_soft_metadata_display.py -q` | **28 passed in 0.27s** |
| `pytest tests/test_soft_metadata_renderer.py tests/test_predict_tab_soft_metadata_display.py tests/test_review_tab_soft_metadata_display.py -q` | **95 passed in 1.11s** |
| `pytest tests/test_soft_metadata_injection.py tests/test_soft_metadata_simulator.py -q` | **74 passed in 0.20s** |
| `pytest -q`（全量） | **2448 passed, 10 skipped, 26 warnings, 65 subtests passed in 10.74s** |

测试覆盖（共 28 个新增）：

| 测试类 | 数量 | 内容 |
|---|---|---|
| `ClassifyReviewAttributionTests` | 7 | 4 outcome × metadata 4 组合 + pending 2 组合 + 非 dict 输入 |
| `BuildReviewCardDataTests` | 6 | review_attribution 块存在 / review-context title / no_attribution forced visible / no_metadata correct review visible / input 不变 / None 输入不 crash |
| `RenderReviewSectionTests` | 3 | visible 调 markdown / no_metadata correct 仍调 markdown / garbage 不 raise |
| `ReviewForbiddenCopyTests` | 5 | 4 outcome × metadata 组合 + final_test_refusal 全 grep 16 forbidden words |
| `FinalTestRefusalReviewTests` | 1 | refusal warning 强制可见 + subtitle 含 "final test 保留区间" |
| `UnknownSignalReviewTests` | 1 | unknown signal 渲染 generic + attribution kind=possible_attribution |
| `ReviewTabIsolationTests` | 2 | patch 锁定 simulator / baseline / prediction_store 不被调；`ast.walk` 锁定 import |
| `ReviewSoftMetadataAppTests`（Streamlit AppTest） | 3 | wrong+R4 / correct+R4 / wrong+empty 三个集成场景 |

测试基线累积：**Step 2G-6C 起点 2420 → 2448**（+28 净增）；
0 failed；10 skipped 不变。

### 30.7 AppTest 覆盖

`ReviewSoftMetadataAppTests`（3 个 Streamlit AppTest）：

| # | 测试 | 期望 |
|---|---|---|
| 30.7.1 | wrong + R4 → 页面文本含"可能归因维度" + "不是确定原因" + "高位跑赢同行后的偏多过热"；不含 16 forbidden words |
| 30.7.2 | correct + R4 → 页面文本含"结构幸存"；不含 16 forbidden words |
| 30.7.3 | wrong + empty signals → 页面文本含"不强行归因"；不含 16 forbidden words |

### 30.8 边界事实

- ❌ **没**改 `predict.py` / `run_predict` / `scanner.py` /
  `prediction_store.py` / 任何 builder
- ❌ **没**改 04 / 05 / 07 任何 required 字段
- ❌ **没**改 `review_log` 任何 required 字段（`error_category` /
  `root_cause` / `confidence_note` / `watch_for_next_time` 全部不写）
- ❌ **没**改 `final_projection` / `simulated_trade` /
  `confidence_system` 任何字段
- ❌ **没**写 DB
- ❌ **没**改 `review_orchestrator` / `review_agent` /
  `review_store` / `review_analyzer` / `review_center`
- ❌ **没**接 `yfinance` / `requests` / 任何网络
- ❌ **没**接 trading API / `longbridge` / `broker` / `paper_trade`
- ❌ **没**启用 `hard` / `forced_exclusion` / `anti_false_exclusion_triggered`
- ❌ **没**让 review 页面调用 simulator / baseline build / DB
  （patch 锁定 not_called；`ast.walk` 锁定 import）
- ❌ **没**让 16 forbidden words 出现在 `st.markdown` 实际调用参数中
  （unit + AppTest 双重 grep 锁定）
- ❌ **没**触碰 2026-01-01 之后 final test range（cutoff 透传 +
  refusal warning visibility 锁定）
- ✅ Review 页面（per-prediction 复盘面板）现在显示 4 种 outcome ×
  metadata 组合的安全 attribution 区块
- ✅ Review 不重新计算 enrichment：从 session_state 复用 layer-2
  显示时 stash 的 enriched payload —— 单点生成，多点消费
- ✅ Step 2G-6 §8 设计文档的 4-quadrant 归因规则**已在 UI 真实落地**
- ✅ **2448 / 0 failed / 10 skipped**；现有 2420 基线零回归

## 31. Anti-False-Exclusion Display Helper（Step 2G-7A/7B，read-only sidecar）

### 31.1 为什么做

Step 2G-7 design（commit `cd571e4`）冻结了 anti-false-exclusion 显示
层 spec：5 个 protective findings + sidecar schema + UI 显示位置 +
文案边界 + 与 hard gate 的强制阻断关系。Step 2G-7A 实现 read-only
display helper；Step 2G-7B 在 Predict / Review soft metadata
expandable area 接入；同 step 完成可避免"helper 写完没接 UI / 接了
没测"的拆分浪费。Step 2G 链路至此完整 end-to-end 闭环：simulator →
renderer → display hook → injection → Predict integration → baseline
cache + scan features → Review attribution → **anti-false-exclusion
display 显式量化"为什么不能 hard"**。

### 31.2 改动文件

| 文件 | 类型 | 说明 |
|---|---|---|
| `ui/anti_false_exclusion_display.py` | 新增 ui helper | `build_anti_false_exclusion_display(soft_metadata, *, prediction_correct)` 纯函数 + `render_anti_false_exclusion_markdown(display)`；模块级常量 `SCHEMA_VERSION` / `FORBIDDEN_COPY_TOKENS` (19 个) / 3 severity 枚举 |
| `ui/predict_tab.py` | 修改（+~28 行）| import anti-false helper；`render_predict_tab` Layer-2 hook 之后加 try/except 包裹的 expander "为什么这里只做提示"；`_render_review_result` 在 attribution band 之后加 try/except 包裹的 expander "保护层诊断" |
| `tests/test_anti_false_exclusion_display.py` | 新增 | 35 个 unittest |
| `tests/test_predict_tab_soft_metadata_display.py` | 修改 | +1 个 AppTest 验证 Predict 集成的 anti-false expander |
| `tests/test_review_tab_soft_metadata_display.py` | 修改 | +2 个 AppTest 验证 correct+R4 / wrong+R4 的 Review 集成 |
| `tasks/step_1_contract_pipeline_summary.md` | 修改 | 新增本 §31 |

未改：`predict.py` / `run_predict` / `scanner.py` / `prediction_store.py` /
`projection_output_adapter.py` / `projection_output_contract.py` /
`regime_diagnostics_dashboard.py` / `soft_metadata_simulator.py` /
`soft_metadata_renderer.py` / `soft_metadata_injection.py` /
`regime_features_builder.py` / `soft_metadata_baseline_cache.py` /
`review_tab.py` / 任何 builder / DB schema / 04 / 05 / 07 任何 required
字段 / `review_log` 任何 required 字段 / `review_orchestrator` /
`review_agent` / 任何其他 `ui/*` 模块。

### 31.3 helper 输出结构（`anti_false_exclusion_display.v1`）

```python
{
    "schema_version": "anti_false_exclusion_display.v1",
    "visible": True,
    "status": "blocked",
    "hard_exclusion_allowed": False,                    # 永远 False
    "primary_reason": "false_exclusion_rate_too_high",
    "protective_findings": [
        {
            "name": "r4_false_exclusion_risk",
            "severity": "medium",                       # informational | medium | high
            "evidence": {
                "false_exclusion_rate": 0.3235,
                "threshold": 0.10,
                "correct_when_triggered": 11,
                "paired": 34,
            },
            "message": "误杀风险较高...",
        },
        # ... 0..N protective findings
    ],
    "recommended_action": "review_only",
    "required_next_step": "collect_more_review_outcomes",
    "warnings": [...],
}
```

不变量（`tests/test_anti_false_exclusion_display.py` 35 个测试锁定）：

- ✅ `hard_exclusion_allowed` **永远** `False`（v1 spec 强约束）
- ✅ `status` **永远** `"blocked"`（不允许 `"allowed"`）
- ✅ input dict 不被原地修改（snapshot 锁定）
- ✅ 5 个 protective finding 的触发条件与 Step 2G-7 §6 一致
- ✅ `r4_survival_case` **仅当** `prediction_correct=True` 且 R4
  signal 存在时触发
- ✅ `r4_false_exclusion_risk` 仅当 `false_exclusion_rate > 0.10` 触发
  （边界严格大于）
- ✅ `net_benefit_insufficient` 仅当 `net_benefit < 0.05` 触发
- ✅ `missing_protection_layer` 总是触发（only when signals 非空）
- ✅ `primary_reason` 优先 `false_exclusion_rate_too_high`，否则
  fallback 第一个非 informational finding
- ❌ 模块**不** import `services.soft_metadata_simulator` /
  `soft_metadata_injection` / `regime_diagnostics_dashboard` /
  `prediction_store` / `streamlit` / `sqlite3` / `yfinance` /
  `requests` / `longbridge` / `broker` / `paper_trade` / v1 stub trio
  （`ast.walk` 锁定）

### 31.4 5 个 protective findings 行为

| # | name | 触发条件 | severity | 真数据示例（main DB R4）|
|---|---|---|---|---|
| 1 | `r4_survival_case` | `prediction_correct=True` 且 R4 signal 存在 | `informational` | survived_count=11 / total=34 / survival_rate=32.4% |
| 2 | `r4_false_exclusion_risk` | R4 `false_exclusion_rate > 0.10` | `medium` | fer=32.4% / threshold=10% / correct=11 / paired=34 |
| 3 | `soft_metadata_holdout_fail` | 任意 signal `holdout_status == "FAIL"` | `medium` | holdout_status=FAIL（Step 3A-4 / 3B-1 已 FAIL）|
| 4 | `net_benefit_insufficient` | R4 `net_benefit < 0.05` | `medium` | nb=2.2% / threshold=5% |
| 5 | `missing_protection_layer` | signals 非空时总是 | `high` | connected=0 / candidate_modules=4 |

`primary_reason` 选取顺序（Step 2G-7 §7）：
1. `false_exclusion_rate_too_high`（如果 #2 触发）
2. 否则第一个非 `informational` finding 的 name
3. 否则 None

### 31.5 Predict / Review 接入位置

**Predict** (`render_predict_tab` Layer-2 之后)：

```python
render_soft_metadata_section(_extract_soft_metadata(_enriched_for_display))
# Step 2G-7B — anti-false-exclusion display
try:
    _afx_soft = _extract_soft_metadata(_enriched_for_display)
    if isinstance(_afx_soft, dict) and _afx_soft.get("signals"):
        _afx_display = build_anti_false_exclusion_display(_afx_soft)
        if _afx_display.get("visible"):
            with st.expander("为什么这里只做提示", expanded=False):
                st.markdown(render_anti_false_exclusion_markdown(_afx_display))
except Exception:  # noqa: BLE001
    pass
```

**Review** (`_render_review_result` 在 attribution band 之后)：

```python
render_review_soft_metadata_section(soft_metadata, prediction_correct=...)
# Step 2G-7B — anti-false-exclusion sidecar (Review context)
if isinstance(soft_metadata, dict) and soft_metadata.get("signals"):
    _afx_display = build_anti_false_exclusion_display(
        soft_metadata, prediction_correct=prediction_correct,
    )
    if _afx_display.get("visible"):
        with st.expander("保护层诊断", expanded=False):
            st.markdown(render_anti_false_exclusion_markdown(_afx_display))
```

设计要点：
- **两个接入位置都默认折叠**（`expanded=False`）—— UI 不打扰用户
  日常浏览
- **Predict context** 没有 `prediction_correct`（outcome 未知），所以
  `r4_survival_case` 在 Predict 不触发；只在 Review context 出现
- **Review context** 有 `prediction_correct`（来自
  `comparison.direction_match`），所以 4 象限的"survival case"在 Review
  能区分显示
- **try/except 防御兜底**：anti-false 路径任何意外都不让主页面崩
- **不**改 `_render_review_result` 已有的 metric / error analysis /
  attribution band 行为（仅在末尾追加新 expander）

### 31.6 文案安全策略

`FORBIDDEN_COPY_TOKENS`（**19** 个，比 renderer 的 16 严格）：
- 16 个 renderer tokens（与 `ui/soft_metadata_renderer.FORBIDDEN_COPY_TOKENS`
  一致）
- 额外 3 个：`" hard "` / `" forced "` / `"排除"`（Step 2G-7 §9 强约束）

测试锁定路径：
- `MarkdownSafetyTests` 5 个场景（带 R4 / final_test_refusal /
  unknown signal）grep AFX markdown 全部 19 个 forbidden tokens
- AppTest（Predict + Review）只 grep **renderer 16 tokens**（页面级），
  避免与 renderer 既有 "误杀率（若强制排除）" 文本冲突 —— AFX
  特定的 3 个 tokens 在 AFX markdown 单独锁定

### 31.7 测试基线

| 命令 | 结果 |
|---|---|
| `pytest tests/test_anti_false_exclusion_display.py -q` | **35 passed in 0.03s** |
| `pytest tests/test_predict_tab_soft_metadata_display.py tests/test_review_tab_soft_metadata_display.py -q` | **62 passed in 1.13s** |
| `pytest tests/test_soft_metadata_renderer.py tests/test_soft_metadata_injection.py -q` | **62 passed in 0.06s** |
| `pytest -q`（全量） | **2486 passed, 10 skipped, 26 warnings, 65 subtests passed in 10.33s** |

测试覆盖（共 38 个新增）：

| 测试类 / 文件 | 数量 | 内容 |
|---|---|---|
| `EmptyAndShapeTests` (`test_anti_false_exclusion_display.py`) | 4 | 空 signals invisible / 非 dict / 有 signals visible / warnings 透传 |
| `InvariantsTests` | 4 | hard_exclusion_allowed 永远 False（3 场景）/ status 永远 blocked / input 不变 |
| `R4FalseExclusionRiskTests` | 3 | fer > threshold 触发 / fer ≤ threshold 不触发 / correct_when_triggered 派生正确 |
| `R4SurvivalCaseTests` | 4 | prediction_correct=True 触发 / =False 不触发 / =None 不触发 / severity=informational |
| `HoldoutFailTests` | 2 | FAIL 触发 / PASS 不触发 |
| `NetBenefitInsufficientTests` | 3 | nb < threshold 触发 / nb ≥ threshold 不触发 / 负 nb 也触发 |
| `MissingProtectionLayerTests` | 3 | signals 非空总是触发 / severity=high / signals 空时不触发 |
| `PrimaryReasonTests` | 2 | false_exclusion_rate 优先 / fallback 到第一个非 informational |
| `UnknownSignalTests` | 2 | 未知 signal 只 emit missing_protection_layer / 缺 metrics 不 crash |
| `MarkdownSafetyTests` | 6 | 空 → 空串 / safe title / 19 forbidden tokens grep（3 prediction_correct 场景 + final_test + unknown）/ 数字清晰 |
| `IsolationTests` | 1 | `ast.walk` 锁定禁 import（含 `streamlit` / `sqlite3` / 模块自身不依赖 UI 框架） |
| Predict AppTest 增量 | 1 | Predict 集成 expander label "为什么这里只做提示" + 32.4% 可见 + 16 forbidden tokens 不出现 |
| Review AppTest 增量 | 2 | correct+R4 → "结构幸存" + "32.4%"；wrong+R4 → "误杀风险较高" + "保护层未接入"；都 grep 16 forbidden tokens |

测试基线累积：**Step 2G-7A/7B 起点 2448 → 2486**（+38 净增）；
0 failed；10 skipped 不变。

### 31.8 边界事实

- ❌ **没**改 `predict.py` / `run_predict` / `scanner.py` /
  `prediction_store.py` / 任何 builder
- ❌ **没**改 04 / 05 / 07 任何 required 字段
- ❌ **没**改 `review_log` 任何 required 字段
- ❌ **没**改 `final_projection` / `simulated_trade` /
  `confidence_system` 任何字段
- ❌ **没**写 DB（helper 模块不接 sqlite / `prediction_store`；UI 接入
  不写 session_state / DB）
- ❌ **没**接 `yfinance` / `requests` / 任何网络
- ❌ **没**接 trading API / `longbridge` / `broker` / `paper_trade`
- ❌ **没**启用 `hard` / `forced_exclusion` /
  `anti_false_exclusion_triggered`（**这个 04 required 字段与本
  sidecar 不同名**：required 字段需要真接入保护层 + hard gate 通过；
  本 sidecar 是 display-only diagnostic）
- ❌ **没**让 16 + 3 = 19 forbidden words 出现在 anti-false-exclusion
  markdown 里（`MarkdownSafetyTests` grep 锁定）
- ❌ **没**让 16 forbidden words 出现在 Predict / Review 集成页面
  （AppTest grep 锁定）
- ❌ **没**触碰 2026-01-01 之后 final test range（warnings 透传 +
  refusal warning visibility 已在 Step 2G-5 / 6A 锁定）
- ✅ Predict 页面在 R4 触发时新增"为什么这里只做提示"折叠区，
  显式量化"为什么不能 hard"
- ✅ Review 页面在 4 象限归因下新增"保护层诊断"折叠区，区分
  survival case vs gate-fail case
- ✅ Step 2G-7 设计文档的 5 个 protective findings + sidecar schema
  + UI 显示位置都**已在真实代码落地**
- ✅ **2486 / 0 failed / 10 skipped**；现有 2448 基线零回归

## 32. Anti-False-Exclusion Dashboard Diagnostics（Step 2G-7C，read-only aggregate）

### 32.1 为什么做

Step 2G-7A/7B 已在 Predict / Review per-prediction surface 显示
"为什么这里只做提示" 折叠区，但**dashboard 视图**还缺累计统计：
用户只能在每条 prediction 单独看到 finding，**看不到** R4 / residual
累计 survival rate、4 项 hard gate fail 的全局趋势。Step 2G-7C
新增 read-only aggregate 服务 + CLI，把 baseline 数字 + survival cases
+ 6 项 hard gate pass/fail 一次性聚合，供 dashboard tab / 命令行
诊断使用。

### 32.2 改动文件

| 文件 | 类型 | 说明 |
|---|---|---|
| `services/anti_false_exclusion_dashboard.py` | 新增 service | `summarize_anti_false_exclusion_dashboard(db_path, *, symbol, limit) -> dict` 纯聚合函数；委托 `build_soft_metadata_baseline` 取 R4/residual 历史指标，叠加 6-gate 状态 + survival 派生 + primary_blocker 选取 |
| `scripts/anti_false_exclusion_dashboard.py` | 新增 CLI | argparse 包装；`--db` / `--symbol` / `--limit`；stdout JSON `ensure_ascii=False, indent=2` |
| `tests/test_anti_false_exclusion_dashboard.py` | 新增 | 35 个 unittest（含 1 个 subprocess CLI smoke）|
| `tasks/step_1_contract_pipeline_summary.md` | 修改 | 新增本 §32 |

未改：`predict.py` / `run_predict` / `scanner.py` / `prediction_store.py` /
`projection_output_adapter.py` / `projection_output_contract.py` /
`regime_diagnostics_dashboard.py` / `soft_metadata_simulator.py` /
`soft_metadata_renderer.py` / `soft_metadata_injection.py` /
`regime_features_builder.py` / `soft_metadata_baseline_cache.py` /
`anti_false_exclusion_display.py` / `predict_tab.py` /
`review_tab.py` / 任何 builder / DB schema / 04 / 05 / 07 任何 required
字段 / `simulated_trade.no_trade` 策略边界 / 任何其他 `ui/*` 模块。

### 32.3 输出结构

```python
{
    "status": "ok" | "no_records" | "error",
    "symbol": "AVGO",
    "records_scanned": int,
    "paired_outcomes": int,
    "calibration_ready": bool,                          # paired_total >= 90
    "metrics_window": {analysis_date_min, analysis_date_max,
                       paired_total, db_snapshot_id},
    "metrics_computed_at": str,                          # ISO timestamp
    "soft_metadata_summary": {
        "r4_overextension": {
            "samples", "paired",
            "correct_when_triggered",                    # round(accuracy × paired)
            "wrong_when_triggered",
            "accuracy", "false_exclusion_rate",
            "net_benefit", "bias_gap", "holdout_status",
        } | None,
        "bullish_high_pos20_residual": {...} | None,
    },
    "survival_cases": {
        "r4_survival_count": int,                        # = correct_when_triggered
        "r4_survival_rate": float,                       # = accuracy
    },
    "hard_gate_status": {                                # 6 项 pass/fail
        "total_paired_ge_90": "pass",
        "candidate_paired_ge_30": "pass",
        "false_exclusion_rate_lte_0_10": "fail",
        "net_benefit_gte_0_05": "fail",
        "protection_layer_connected": "fail",            # v1 永远 fail
        "cross_window_holdout_pass": "fail",
    },
    "hard_exclusion_allowed": False,                     # 永远 False（v1）
    "primary_blocker": "false_exclusion_rate_too_high",  # 优先级派生
    "warnings": [...],
}
```

### 32.4 hard gate 6 项决策表

| # | gate | 当前真实状态（main DB）| 通过条件 |
|---|---|---|---|
| 1 | `total_paired_ge_90` | **pass**（286）| `metrics_window.paired_total >= 90` |
| 2 | `candidate_paired_ge_30` | **pass**（R4=34）| `r4_overextension.paired >= 30` |
| 3 | `false_exclusion_rate_lte_0_10` | **fail**（0.3235）| R4 `false_exclusion_rate <= 0.10` |
| 4 | `net_benefit_gte_0_05` | **fail**（+0.0219）| R4 `net_benefit >= 0.05` |
| 5 | `protection_layer_connected` | **fail**（v1 永远 fail）| 至少 1 个 anti-false-exclusion 模块接入主链（4 个候选全离线）|
| 6 | `cross_window_holdout_pass` | **fail**（FAIL）| `holdout_status == "PASS"`（Step 3A-4 / 3B-1 已 FAIL）|

`hard_exclusion_allowed = all(v == "pass" for v in gate_status.values())` —
当前 4 项 fail → **False**。

`primary_blocker` 选取顺序：
1. `false_exclusion_rate_too_high`（gate #3 fail 时）
2. `net_benefit_insufficient`（gate #4 fail）
3. `soft_metadata_holdout_fail`（gate #6 fail）
4. `insufficient_total_paired` / `insufficient_candidate_paired`
5. `missing_protection_layer`（gate #5 fail，always）
6. None（every gate passes）

### 32.5 真数据基线（main DB / `--symbol AVGO --limit 450`）

| 字段 | 值 |
|---|---|
| `paired_outcomes` | **286** |
| `calibration_ready` | true |
| `metrics_window.analysis_date_min` / `max` | 2023-01-03 / 2024-08-02 |
| R4 `samples` / `paired` / `correct_when_triggered` | 36 / 34 / **11** |
| R4 `accuracy` / `bias_gap` | **0.324** / **+0.676** |
| R4 `false_exclusion_rate` / `net_benefit` | **0.3235** / **+0.022** |
| R4 `holdout_status` | **`"FAIL"`** |
| Residual `paired` / `correct_when_triggered` | 47 / **23** |
| Residual `accuracy` / `bias_gap` | **0.489** / **+0.511** |
| Residual `net_benefit` | **−0.001**（hard 排除会让整体 accuracy 下降）|
| `survival_cases.r4_survival_count` | 11 |
| `survival_cases.r4_survival_rate` | 0.324 |
| `hard_gate_status` | 2 pass / 4 fail |
| `hard_exclusion_allowed` | **false** |
| `primary_blocker` | **`"false_exclusion_rate_too_high"`** |

数字与 Step 2G-3 / 2G-5 / 2G-7A baseline 完全一致。

### 32.6 CLI 用法

```
python3 scripts/anti_false_exclusion_dashboard.py
python3 scripts/anti_false_exclusion_dashboard.py --symbol AVGO --limit 450
python3 scripts/anti_false_exclusion_dashboard.py --db avgo_agent.db --symbol AVGO --limit 450
```

stdout JSON `ensure_ascii=False, indent=2`。退出码：argparse 失败时
非 0；service 内部错误经 `status=error` + `warnings` 表面化，退出码
仍为 0（与其他 read-only 诊断 CLI 一致）。

### 32.7 测试基线

| 命令 | 结果 |
|---|---|
| `pytest tests/test_anti_false_exclusion_dashboard.py -q` | **35 passed in 0.10s** |
| `pytest tests/test_anti_false_exclusion_display.py tests/test_regime_diagnostics_dashboard.py -q` | **56 passed in 0.24s** |
| `pytest -q`（全量） | **2521 passed, 10 skipped, 26 warnings, 65 subtests passed in 10.71s** |

测试覆盖矩阵：

| 测试类 | 数量 | 内容 |
|---|---|---|
| `OutputSchemaTests` | 4 | 顶层字段 / status=ok / calibration_ready / 阈值切换 |
| `CandidateExtractionTests` | 4 | R4 字段直透 / correct_when_triggered 派生 / residual / holdout 继承 baseline 顶层 |
| `HardGateTests` | 8 | 默认 4 fail / 5 个边界条件（paired / fer / nb / holdout PASS / FAIL）/ protection_layer 永远 fail |
| `HardExclusionAllowedTests` | 3 | 默认 False / 空 baseline False / 即使 5 项 pass 而 protection 仍 fail → 整体 False |
| `PrimaryBlockerTests` | 4 | 优先级 fer → nb → holdout → protection_layer |
| `SurvivalCasesTests` | 2 | survival_count == correct_when_triggered；survival_rate == accuracy |
| `EmptyBaselineTests` | 5 | empty → status=no_records / soft_metadata_summary None / warnings 透传 / hard 仍 False / builder 异常 → status=error |
| `InputPassthroughTests` | 1 | db_path / symbol / limit 透传 |
| `InputImmutabilityTests` | 1 | baseline dict 不被原地修改 |
| `IsolationTests` | 2 | `ast.walk` 锁定禁 import / patch 锁定 prediction_store 不调 |
| `CliSmokeTests` | 1 | subprocess CLI smoke：JSON 解析 + 顶层 invariants |

测试基线累积：**Step 2G-7C 起点 2486 → 2521**（+35 净增）；
0 failed；10 skipped 不变。

### 32.8 边界事实

- ❌ **没**改 `predict.py` / `run_predict` / `scanner.py` /
  `prediction_store.py` / 任何 builder
- ❌ **没**改 04 / 05 / 07 任何 required 字段
- ❌ **没**改 `final_projection` / `simulated_trade` /
  `confidence_system` 任何字段
- ❌ **没**写 DB（service 委托 `build_soft_metadata_baseline`，后者
  也是 SELECT-only；CLI 仅 stdout）
- ❌ **没**改 `anti_false_exclusion_display.py` /
  `soft_metadata_simulator.py` / 任何已有 service 或 ui 模块
- ❌ **没**接 `yfinance` / `requests` / 任何网络
- ❌ **没**接 trading API / `longbridge` / `broker` / `paper_trade`
- ❌ **没**启用 `hard` / `forced_exclusion` /
  `anti_false_exclusion_triggered`
- ❌ **没**触碰 2026-01-01 之后 final test range（baseline 路径已锁定
  cutoff）
- ❌ **没** import `services.prediction_store` / `regime_diagnostics_dashboard`
  /  `confidence_engine` / `contradiction_engine` / `risk_model`
  / `sqlite3` / `streamlit`（`ast.walk` 锁定）
- ✅ 真数据 smoke：所有数字与 Step 2G-3 / 2G-5 / 2G-7A 基线**完全一致**
- ✅ `hard_exclusion_allowed` 在所有测试场景下都是 **False** —— 即使
  人为构造 5 项 gate pass 也不会变 True，因为 `protection_layer_connected`
  在 v1 永远是 fail（hard-coded 直到 Step 2G-8+ 真接入保护层）
- ✅ **2521 / 0 failed / 10 skipped**；现有 2486 基线零回归

## 33. Protection Layer Diagnostics Helper（Step 2G-8A.1，read-only sidecar）

### 33.1 目标

落地 Step 2G-8A protection-layer connection design（commit `b4c1919`）
+ checkpoint（`8c56696`）的 helper 层：实现 `protection_layer_diagnostics.v1`
sidecar，把 baseline 中的 `holdout_status` / `net_benefit` 显式接到
**两个轻量 guard**（`holdout_stability_guard` + `net_benefit_guard`），
让 Predict / Review / dashboard **将来**可在 anti-false expander 之下
显示 "保护层诊断详情"。

**强约束**（与 Step 2G-8A 设计一致）：
- 只新增 helper（`services/protection_layer_diagnostics.py`）+ tests +
  doc；**不**改 `predict.py` / `run_predict` / `scanner.py` /
  `prediction_store.py` / `app.py` / 任何 builder / DB schema
- **不**写 DB；helper 是纯函数；caller-injected 输入
- **不**升级 04 / 05 / 07 required 字段
- **不**让 Step 2G-7C dashboard `hard_gate_status.protection_layer_connected`
  自动 pass（仍 fail；Gate 5 只能由 Step 2G-8+ launch review 通过）

### 33.2 sidecar schema（已实现）

```json
{
  "schema_version": "protection_layer_diagnostics.v1",
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

### 33.3 公共 API

```python
build_protection_layer_diagnostics(
    anti_false_exclusion_summary: dict | None = None,
    *,
    soft_metadata: dict | None = None,
) -> dict
```

- `anti_false_exclusion_summary`：可选；`summarize_anti_false_exclusion_dashboard`
  的输出（`soft_metadata_summary.r4_overextension` 提供 `holdout_status`
  / `net_benefit`）
- `soft_metadata`：可选；`soft_metadata.v1` payload（signals[] 提供
  R4 `holdout_status` 与 `historical_metrics_in_sample.net_benefit`
  作为 fallback）
- 两者都没传或字段缺失时 → `guards=[]`，`warnings` 含
  `"missing_metrics"`，4 个 connection flag 仍按 v1 不变量返回

```python
build_protection_layer_diagnostics_from_dashboard(summary: dict) -> dict
```

是上面函数的 thin wrapper：从 dashboard summary 直接构造，**不**重新
查询 DB、**不**调 dashboard service。

### 33.4 两个 guard 行为

| guard | 触发条件 | reason | evidence |
|---|---|---|---|
| `holdout_stability_guard` | candidate 或 R4 `holdout_status == "FAIL"` | `holdout_status_FAIL` | `{holdout_status: "FAIL"}` |
| `net_benefit_guard` | R4 `net_benefit < 0.05` | `net_benefit_below_gate` | `{net_benefit, threshold: 0.05}` |

- `holdout_status` 仅在字面量为 `"FAIL"` 时才触发 holdout guard；
  `UNKNOWN` / `""` / `None` **不**触发（避免缺数据时虚假 blocking）
- `net_benefit == 0.05` **不**触发（与 hard-gate 阈值 `>=` 边界一致）
- 两个 guard 的 `message` 与 Step 2G-7A AFX renderer 共用 19 token
  forbidden-copy 标准（不出现 `禁止交易` / `hard exclusion` /
  `force close` / 等）

### 33.5 四个 connection flag（v1 强不变量）

| flag | 取值 | 含义 |
|---|---|---|
| `diagnostic_connected` | **总是 `true`** | sidecar 输出本身存在；UI 可读取此节点 |
| `hard_gate_connected` | **总是 `false`** | 没有进入 hard decision pipeline；run_predict / scanner 不读 |
| `required_field_connected` | **总是 `false`** | 没有写 04 required 字段；schema 无升级 |
| `protection_layer_connected_for_gate` | **总是 `false`** | Step 2G-7C dashboard Gate 5 仍 fail |

**反误读**：`diagnostic_connected=true` ≠ "Gate 5 pass"，仅代表
"诊断信息可在 UI 展示"。这一约束被 schema-level 测试锁定。

### 33.6 summary 不变量

- `summary.hard_upgrade_blocked`：v1 **永远 `true`**（即使两个 guard
  都 pass，`protection_layer_connected_for_gate` 仍 false → 仍 blocked）
- `summary.display_only`：v1 **永远 `true`**
- `summary.blocking_guard_count`：与 `guards` 列表中
  `status=="blocking"` 的数量一致
- `summary.required_next_step`：v1 总是 `"narrower_candidate_research"`
  （指向 Step 2G-8B）

### 33.7 与现有结构的关系

- `protection_layer_diagnostics.v1` 是 `anti_false_exclusion_display.v1`
  的**补充**，不是替代 —— 两者**同时**显示让用户看到完整保护证据链：
  per-prediction 5 项 protective findings + baseline-level 2 项
  blocking guard
- helper **不**调 `services.anti_false_exclusion_dashboard` / `services.soft_metadata_simulator`
  / `services.prediction_store` / `regime_diagnostics_dashboard` —— 调用方
  自己决定喂什么；所有读取由调用方完成（保持 helper 纯函数）
- 测试用 `ast.walk` 锁定模块未 import：`yfinance` / `requests` /
  `longbridge` / `broker` / `paper_trade` / `sqlite3` /
  `services.prediction_store` / `services.confidence_engine` /
  `services.contradiction_engine` / `services.risk_model` /
  `services.soft_metadata_simulator` /
  `services.anti_false_exclusion_dashboard` / `predict` / `scanner`

### 33.8 测试矩阵（`tests/test_protection_layer_diagnostics.py`）

| 测试类 | 数量 | 内容 |
|---|---|---|
| `OutputSchemaTests` | 4 | 顶层字段 / schema_version / summary 必备字段 / guard 字段 |
| `HoldoutStabilityGuardTests` | 4 | FAIL 触发 / PASS 不触发 / UNKNOWN/None/空字符串不触发 / soft_metadata 路径触发 |
| `NetBenefitGuardTests` | 4 | <0.05 触发 / ==0.05 不触发 / >0.05 不触发 / soft_metadata 路径触发 |
| `MissingMetricsTests` | 5 | 无输入 → warning / 空 dashboard → warning / 无 R4 → warning / 垃圾 payload graceful / 缺数据下 connection flag 仍锁定 |
| `ConnectionFlagInvariantTests` | 4 | 6 个 scenario × 4 个 flag → 各自常量锁定（diagnostic=true；其余三项=false）|
| `SummaryInvariantTests` | 4 | hard_upgrade_blocked / display_only / blocking_guard_count / required_next_step 锁定 |
| `InputImmutabilityTests` | 3 | dashboard / soft_metadata / 双输入路径下 input dict 不被原地修改 |
| `FromDashboardTests` | 3 | 默认提取 / 全 pass 路径 guards=[] / 垃圾输入 graceful |
| `FinalTestRangeWarningTests` | 3 | dashboard warnings / soft_metadata summary warnings 透传 / 去重 |
| `CrossSourceTests` | 2 | dashboard 字段优先 / 缺字段时 soft_metadata fallback |
| `IsolationTests` | 1 | `ast.walk` 锁定禁 import |
| `ForbiddenCopyTests` | 2 | 默认路径 / soft_metadata 路径下 message 字符串不含 19 forbidden token |

### 33.9 验证

| 命令 | 结果 |
|---|---|
| `pytest tests/test_protection_layer_diagnostics.py -q` | **39 passed in 0.04s（+24 subtests）** |
| `pytest tests/test_anti_false_exclusion_dashboard.py tests/test_anti_false_exclusion_display.py -q` | **70 passed in 0.16s** |
| `pytest -q`（全量） | **2560 passed, 10 skipped, 26 warnings, 89 subtests passed in 12.28s** |

测试基线累积：**Step 2G-7C 起点 2521 → Step 2G-8A.1 终点 2560**
（+39 净增）；0 failed；10 skipped 不变。

### 33.10 边界事实

- ❌ **没**改 `predict.py` / `run_predict` / `scanner.py` /
  `prediction_store.py` / `app.py` / 任何 builder / DB schema
- ❌ **没**改 04 / 05 / 07 任何 required 字段
- ❌ **没**改 `final_projection` / `final_direction` / `simulated_trade`
  / `no_trade` / `confidence_system` 任何字段
- ❌ **没**写 DB；helper 是纯函数，caller-injected 输入
- ❌ **没**改 `services.anti_false_exclusion_dashboard` /
  `ui/anti_false_exclusion_display.py` / `services.soft_metadata_simulator`
  / 任何已有 service / ui 模块
- ❌ **没**让 Step 2G-7C dashboard `hard_gate_status.protection_layer_connected`
  自动 pass（仍 fail；Gate 5 仍 fail）
- ❌ **没**启用 `hard` / `forced_exclusion` /
  `anti_false_exclusion_triggered`
- ❌ **没**接 `yfinance` / `requests` / 任何网络
- ❌ **没**接 trading API / `longbridge` / `broker` / `paper_trade`
- ❌ **没**触碰 2026-01-01 之后 final test range
- ❌ **没** import `services.prediction_store` / `regime_diagnostics_dashboard`
  / `confidence_engine` / `contradiction_engine` / `risk_model` / `predict`
  / `scanner` / `sqlite3`（`ast.walk` 锁定）
- ✅ `diagnostic_connected = True` / 其余三 flag 永远 `False`（schema-level
  invariants 测试锁定）
- ✅ `summary.hard_upgrade_blocked` / `summary.display_only` 永远
  `True`（v1 spec 强约束）
- ✅ **2560 / 0 failed / 10 skipped**；现有 2521 基线零回归

## 34. Protection Layer Diagnostics UI Integration（Step 2G-8A.2，display-only）

### 34.1 目标

把 Step 2G-8A.1 的 `protection_layer_diagnostics.v1` helper（commit
`cdbb13a`）以 **display-only sub-section** 方式接入 Predict / Review
UI，让用户在已有 anti-false expander 内同时看到：
- per-prediction 5 项 protective findings（Step 2G-7A AFX）
- baseline-level 2 项 blocking guard（本步骤；`holdout_stability_guard`
  + `net_benefit_guard`）

**强约束**（继承 Step 2G-8A 设计 §11 / 8A.1 checkpoint §12）：
- 只新增 UI renderer + tests + doc；**不**改 `predict.py` /
  `run_predict` / `scanner.py` / `prediction_store.py` / `app.py` /
  任何 builder / DB schema
- **不**写 DB；renderer 是纯函数；caller-injected 输入
- **不**升级 04 / 05 / 07 required 字段
- **不**让 Step 2G-7C dashboard `hard_gate_status.protection_layer_connected`
  自动 pass（仍 fail；Gate 5 仍 fail）
- **不**让 helper 输出 4 个 connection flag 的任意一个变为 `True`
  之外的预期值（`diagnostic_connected = True` / 其余三 flag = False
  全程不变）

### 34.2 新增模块

| 路径 | 类型 | 说明 |
|---|---|---|
| `ui/protection_layer_diagnostics_renderer.py` | 新增 | pure card_data + markdown renderer |
| `tests/test_protection_layer_diagnostics_renderer.py` | 新增 | 23 focused tests + 5 subtests |
| `ui/predict_tab.py` | 修改 | Predict + Review expander 各加 1 段 sub-section |
| `tests/test_predict_tab_soft_metadata_display.py` | 修改 | 新增 `ProtectionLayerDiagnosticsPredictAppTests` + wiring smoke |
| `tests/test_review_tab_soft_metadata_display.py` | 修改 | 新增 `ProtectionLayerDiagnosticsReviewAppTests` |

### 34.3 公共 API（renderer）

```python
build_protection_layer_diagnostics_card_data(
    diagnostics: dict | None,
) -> dict
```

- 输入：`protection_layer_diagnostics.v1` helper 输出（或 None）
- 输出：`protection_layer_diagnostics_card.v1`（含 visible / 4
  connection flags / guards / summary / warnings）
- 当 helper 输出 `guards=[]` 且 `warnings=[]` 时 `visible=False`，
  Predict / Review UI 不渲染空盒
- `warnings` 含 `missing_metrics` 或 `final_test_range_refusal` 时
  `visible=True`，让用户看到状态提示

```python
render_protection_layer_diagnostics_markdown(card_data: dict) -> str
```

- 输入：上面 builder 的输出
- 输出：safe markdown 字符串（`visible=False` → `""`）
- 永远不出现 8 个 forbidden token（见 §34.6）

### 34.4 UI 接入位置

**Predict 页面**（`render_predict_tab` → 接 `_extract_soft_metadata`
之后的 anti-false 块）：

```python
with st.expander("为什么这里只做提示", expanded=False):
    st.markdown(render_anti_false_exclusion_markdown(_afx_display))
    # Step 2G-8A.2 — protection layer diagnostics sub-section
    try:
        _pld = build_protection_layer_diagnostics(soft_metadata=_afx_soft)
        _pld_card = build_protection_layer_diagnostics_card_data(_pld)
        if _pld_card.get("visible"):
            st.markdown(render_protection_layer_diagnostics_markdown(_pld_card))
    except Exception:
        pass
```

**Review 页面**（`_render_review_result` → 已有 `保护层诊断` expander）：
同一 try / except + 同一 helper 调用，把 protection diagnostics
markdown 接到 AFX markdown 之下。

**两处接入都满足**：
- 输入仅来自现有 soft_metadata（不读 DB / 不调 dashboard service）
- 失败被 try/except 包裹，**不**会让 Predict / Review 页面 crash
- 不写任何 contract / required / DB

### 34.5 markdown 输出形态

```
**保护层诊断详情**
诊断信息已接入，但不等于自动升级；当前仍只允许复盘提示，
不改变主推演方向，不构成交易指令。

**保护层 guard 列表**
- **跨窗口稳定性 guard**（blocking）：跨窗口验证未通过，当前只允许复盘提示。
  · reason=`holdout_status_FAIL` · _evidence:_ holdout_status=FAIL
- **净收益 guard**（blocking）：净收益不足，当前只允许复盘提示。
  · reason=`net_benefit_below_gate` · _evidence:_ net_benefit=2.2% · threshold=5.0%

**接入状态（sidecar diagnostics 边界）**
- 诊断已接入 · 是
- 决策链未接入 · 否
- 04 字段未升级 · 否
- 评估闸门暂未接入 · 否

· 升级条件未满足 · 当前仅作展示 · blocking guards：2

_待补条件：_ `narrower_candidate_research`（在此之前仍只允许复盘提示）
```

**注意**：四个 connection flag 的 UI 标签**故意**不打印原始 flag 名
`hard_gate_connected` / `protection_layer_connected_for_gate` —— 因为
renderer-side forbidden 列表锁定了 `hard` / `forced` 子串，所以 UI
用中文 `决策链未接入` / `评估闸门暂未接入` 对应表达。这一点与
8A 设计 §9 文案规范完全一致。

### 34.6 forbidden copy（renderer 锁定）

| token | 锁定理由 |
|---|---|
| `禁止交易` | 交易指令禁用 |
| `强制否定` | 强制语义禁用 |
| `hard`（子串） | 不让 UI 暗示 hard 升级被允许 |
| `forced`（子串） | 同上 |
| `no_trade` | 仓位指令禁用 |
| `卖出信号` / `做空信号` | 方向指令禁用 |
| `自动拦截` | 决策语义禁用 |

`tests/test_protection_layer_diagnostics_renderer.py::ForbiddenCopyTests`
对 5 个 scenario × 8 个 token 用 `assertNotIn` 锁定。两个 AppTest
（Predict + Review）也对 page-level markdown 同时 grep。

### 34.7 测试矩阵

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

### 34.8 验证

| 命令 | 结果 |
|---|---|
| `pytest tests/test_protection_layer_diagnostics_renderer.py -q` | **23 passed**（+5 subtests） |
| `pytest tests/test_predict_tab_soft_metadata_display.py tests/test_review_tab_soft_metadata_display.py -q` | **70 passed** |
| `pytest tests/test_protection_layer_diagnostics.py tests/test_anti_false_exclusion_display.py -q` | **80 passed** |
| `pytest -q`（全量） | **2591 passed / 10 skipped / 0 failed / 26 warnings / 94 subtests** |

测试基线累积：**Step 2G-8A.1 终点 2560 → Step 2G-8A.2 终点 2591**
（+31 净增；现有 2560 基线零回归）。

### 34.9 边界事实

- ❌ **没**改 `predict.py` / `run_predict` / `scanner.py` /
  `prediction_store.py` / `app.py` / 任何 builder / DB schema
- ❌ **没**改 04 / 05 / 07 任何 required 字段
- ❌ **没**改 `final_projection` / `final_direction` /
  `simulated_trade` / `no_trade` / `confidence_system` 任何字段
- ❌ **没**写 DB；renderer 是纯函数，caller-injected 输入
- ❌ **没**改 `services/protection_layer_diagnostics.py` /
  `services/anti_false_exclusion_dashboard.py` /
  `ui/anti_false_exclusion_display.py` / `services/soft_metadata_simulator.py`
  / 任何已有 service / 其它 ui 模块
- ❌ **没**让 Step 2G-7C dashboard `protection_layer_connected`
  自动 pass（仍 fail；Gate 5 仍 fail）
- ❌ **没**启用 `hard` / `forced_exclusion` /
  `anti_false_exclusion_triggered`
- ❌ **没**接 `yfinance` / `requests` / 任何网络
- ❌ **没**接 trading API / `longbridge` / `broker` / `paper_trade`
- ❌ **没**触碰 2026-01-01 之后 final test range
- ❌ **没** import `streamlit` / `services.prediction_store` /
  `dashboard service` / `simulator`（renderer 用 `ast.walk` 锁定）
- ❌ **没**让 4 个 connection flag 任一变成预期之外（schema-level
  test 锁定）
- ✅ Predict + Review 页面 try/except 包裹接入点 —— UI 永不 crash
- ✅ **2591 / 0 failed / 10 skipped**；现有 2560 基线零回归

## 35. Protection Layer Diagnostics Dashboard Guard Counts（Step 2G-8A.3）

### 35.1 目标

把 Step 2G-8A.1 helper（commit `cdbb13a`）的 sidecar 输出**聚合到**
Step 2G-7C anti-false-exclusion dashboard（`summarize_anti_false_exclusion_dashboard`）
的 aggregate JSON 中：新增 `protection_layer_diagnostics` 字段，含
4 个 connection flag、`guard_summary`（counts + blocking reasons +
guard names）、`hard_upgrade_blocked` / `display_only`。

**强约束**（继承 Step 2G-8A 设计 §11 / 8A.1 / 8A.2 checkpoint）：
- 只改 `services/anti_false_exclusion_dashboard.py` + tests + doc；
  **不**改 helper / renderer / `predict.py` / `run_predict` /
  `scanner.py` / `prediction_store.py` / `app.py` / 任何 builder /
  DB schema
- **不**写 DB；helper 仍是纯函数；不重新查询 DB（aggregate 复用本来
  就构造好的 `soft_metadata_summary`）
- **不**升级 04 / 05 / 07 required 字段
- **不**让 Step 2G-7C dashboard `hard_gate_status.protection_layer_connected`
  自动 pass —— `_PROTECTION_LAYER_CONNECTED = False` 常量未变
- **不**改 `hard_exclusion_allowed` 派生逻辑（仍依赖 6 项 gate 全 pass）

### 35.2 新字段 schema

```json
{
  "protection_layer_diagnostics": {
    "schema_version": "protection_layer_diagnostics.v1",
    "diagnostic_connected": true,
    "hard_gate_connected": false,
    "required_field_connected": false,
    "protection_layer_connected_for_gate": false,
    "guard_summary": {
      "total_guard_count": 2,
      "blocking_guard_count": 2,
      "blocking_reasons": {
        "holdout_status_FAIL": 1,
        "net_benefit_below_gate": 1
      },
      "guard_names": [
        "holdout_stability_guard",
        "net_benefit_guard"
      ]
    },
    "hard_upgrade_blocked": true,
    "display_only": true
  }
}
```

shape 不变量（schema-level 测试锁定）：
- `schema_version` 总是 `"protection_layer_diagnostics.v1"`（与 helper
  一致）
- 4 个 connection flag 取值与 helper schema 完全对应：
  `diagnostic_connected = true` / 其余三 false
- `guard_summary.total_guard_count` 与 `guard_names` 长度一致
- `guard_summary.blocking_guard_count` 与 `blocking_reasons` 计数总和
  一致
- `hard_upgrade_blocked` / `display_only` 永远 `true`（v1）

### 35.3 实现

#### 35.3.1 dashboard service 改动

`services/anti_false_exclusion_dashboard.py`：
1. 新增 import：`from services.protection_layer_diagnostics import build_protection_layer_diagnostics_from_dashboard`
2. 新增私有函数：`_aggregate_protection_layer_diagnostics(diagnostics)` —
   纯函数，把 helper 的 `guards[]` / `summary{}` 转成 aggregate-friendly
   shape（counts / blocking reasons / guard names 提到 `guard_summary`；
   `hard_upgrade_blocked` / `display_only` 提到顶层）
3. happy path 末尾把 helper 输出（喂 `soft_metadata_summary` + `warnings`）
   transform 后写入 `protection_layer_diagnostics` 字段
4. error path（baseline load 异常）也写入空 aggregate（`total_guard_count=0`
   + 4 个 connection flag 仍按 v1 不变量）—— 让 downstream 读者无需
   `dict.get(..., {})` 兜底

#### 35.3.2 不变的部分

- `_PROTECTION_LAYER_CONNECTED = False`（Step 2G-7C 起的 hard-coded
  常量）**未改**
- `_build_hard_gate_status` 派生 `protection_layer_connected = "fail"`
  逻辑**未改**
- `_pick_primary_blocker` 返回值**未改**
- `hard_exclusion_allowed` 派生（`all(v == "pass" for v in gate_status.values())`）
  **未改**
- 现有 35 个 `test_anti_false_exclusion_dashboard.py` 用例全部直接
  通过，零回归

### 35.4 guard count 逻辑

从 helper 的 `guards[]` 派生：

| 字段 | 派生 |
|---|---|
| `total_guard_count` | `len(guard_names)` |
| `blocking_guard_count` | `count(g["status"] == "blocking")` |
| `blocking_reasons` | `Counter(g["reason"] for g in guards if g["status"] == "blocking")` |
| `guard_names` | `[g["name"] for g in guards]`（按 helper 输出顺序） |

边界：
- `guards = []`（缺数据 / 全 pass）→ counts 全部 0、`blocking_reasons={}`、
  `guard_names=[]`，`hard_upgrade_blocked=true` / `display_only=true`
  仍锁定
- 非 dict 元素被 silently skip（不 raise）
- 缺 `name` 字段的 guard 不会进入 `guard_names`

### 35.5 与现有 dashboard 字段的关系

`summarize_anti_false_exclusion_dashboard` 的 13 个顶层字段（Step
2G-7C 起）→ 新增 1 个变成 14 个：

| 现有字段（13） | 新字段（1） |
|---|---|
| `status` / `symbol` / `records_scanned` / `paired_outcomes` / `calibration_ready` / `metrics_window` / `metrics_computed_at` / `soft_metadata_summary` / `survival_cases` / `hard_gate_status` / `hard_exclusion_allowed` / `primary_blocker` / `warnings` | `protection_layer_diagnostics`（**read-only sidecar**）|

新字段**只读 sidecar**：
- 不参与 `hard_gate_status` 任何 gate 的判断
- 不参与 `hard_exclusion_allowed` 派生
- 不参与 `primary_blocker` 选择
- 不写 DB / 不写 contract / 不写 required

### 35.6 测试矩阵（新增）

`tests/test_anti_false_exclusion_dashboard.py`（+13 cases）：

| 测试类 | 数量 | 覆盖点 |
|---|---|---|
| `ProtectionLayerDiagnosticsAggregateTests` | 11 | 字段存在 / 4 flag 锁定 / 默认 baseline 两 guard 计数 / blocking reasons 完整 / `hard_upgrade_blocked` / `display_only` / Gate 5 仍 fail / `hard_exclusion_allowed` 仍 false / holdout PASS 仅 net_benefit guard / 全 pass 0 guard 但不变量保持 / no_records 安全 0 计数 / error path 安全字段 / `_PROTECTION_LAYER_CONNECTED` 常量未改 |
| `ProtectionLayerDiagnosticsAggregateIsolationTests` | 1 | `ast.walk` 锁定 dashboard 模块未 import 禁用模块（含新增的 `predict` / `scanner` / `ui.protection_layer_diagnostics_renderer`） |

### 35.7 验证

| 命令 | 结果 |
|---|---|
| `pytest tests/test_anti_false_exclusion_dashboard.py -q` | **48 passed**（35 baseline + 13 新增） |
| `pytest tests/test_protection_layer_diagnostics.py -q` | **39 passed**（+24 subtests） |
| `pytest -q`（全量） | **2604 passed / 10 skipped / 0 failed / 26 warnings / 94 subtests** |

测试基线累积：**Step 2G-8A.2 终点 2591 → Step 2G-8A.3 终点 2604**
（+13 净增；现有 2591 基线零回归）。

### 35.8 边界事实

- ❌ **没**改 `predict.py` / `run_predict` / `scanner.py` /
  `prediction_store.py` / `app.py` / 任何 builder / DB schema
- ❌ **没**改 04 / 05 / 07 任何 required 字段
- ❌ **没**改 `final_projection` / `final_direction` /
  `simulated_trade` / `no_trade` / `confidence_system` 任何字段
- ❌ **没**写 DB；新字段是 helper 输出的纯 dict transform，不持久化
- ❌ **没**改 helper（`services/protection_layer_diagnostics.py`）/
  renderer（`ui/protection_layer_diagnostics_renderer.py`）/
  `services/soft_metadata_simulator.py` / 任何 ui 模块
- ❌ **没**让 `hard_gate_status.protection_layer_connected` 自动 pass
  （仍 fail；常量 `_PROTECTION_LAYER_CONNECTED = False` 未改）
- ❌ **没**改 `hard_exclusion_allowed` 派生（仍依赖 6 gate 全 pass）
- ❌ **没**改 `primary_blocker` 选择优先级
- ❌ **没**启用 `hard` / `forced_exclusion` /
  `anti_false_exclusion_triggered`
- ❌ **没**接 `yfinance` / `requests` / 任何网络
- ❌ **没**接 trading API / `longbridge` / `broker` / `paper_trade`
- ❌ **没**触碰 2026-01-01 之后 final test range
- ❌ **没** import `streamlit` / `prediction_store` / `confidence_engine` /
  `contradiction_engine` / `risk_model` / `predict` / `scanner` /
  `ui.protection_layer_diagnostics_renderer`（`ast.walk` 锁定）
- ✅ 4 个 connection flag 在 happy / no_records / error / 全 pass /
  缺数据 5 个 scenario 下都按 v1 spec 锁定
- ✅ **2604 / 0 failed / 10 skipped**；现有 2591 基线零回归

