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

## 20. Contract Replay Writer Skeleton（Step 2F-4c-1，dry-run default）

> Step 2F-4 plan §8 的 Option C 第一阶段。**dry-run-only 安全骨架**——`dry_run=True` 是默认；`dry_run=False`（CLI `--write`）今天只返回 `status="not_implemented_for_write"` 并不写任何 DB。**真写入逻辑（`run_predict + save_prediction(analysis_date_override=D) + save_outcome(captured_at_override=D+1)`）留给 Step 2F-4c-2。** 本节是 writer 的契约 + 安全边界 spec。

### 20.1 新增文件

| 文件 | 角色 |
|---|---|
| [services/contract_replay_writer.py](../services/contract_replay_writer.py) | service：`run_contract_replay(symbol, start_date, end_date, limit, coded_data_dir, *, dry_run=True, db_path=None) -> dict`；`_DEFAULT_LIMIT = 30` / `_LIMIT_HARD_CAP = 50`；本地 `_resolve_writer_limit` 在 planner 防御之上加 hard cap |
| [scripts/run_contract_replay.py](../scripts/run_contract_replay.py) | CLI：默认 dry-run；`--write` flag 翻转 `dry_run=False`；其他参数（`--symbol / --start / --end / --limit / --coded-data-dir / --db`）pass-through 到 service |
| [tests/test_contract_replay_writer.py](../tests/test_contract_replay_writer.py) | 28 case，8 测试组：dry_run 默认 True / dry_run 不调 run_predict / save_prediction / save_outcome（patch + assert call_count == 0） / planner 三种失败模式透传 / 参数转发 / limit hard cap 50 + 5 防御 / `--write` 返回 not_implemented + 同样不调 write 函数 / 依赖卫生 / CLI 2 case |

### 20.2 核心契约

#### dry_run=True（默认）

- 调 `plan_contract_replay(...)` 拿 `candidate_pairs`
- 返回字段：`status="ok"` / `would_write_count = len(candidate_pairs)` / `written_prediction_count=0` / `written_outcome_count=0` / `notes=["dry_run=True: no prediction/outcome records were written", ...]`
- **绝对不调** `run_predict` / `save_prediction` / `save_outcome`（patch 测试锁住）

#### dry_run=False（CLI `--write`）

- 仍调 `plan_contract_replay(...)` 拿 `candidate_pairs`
- 但**第一版 4c-1 在此停下**——返回 `status="not_implemented_for_write"`
- `notes` 显式写"Step 2F-4c-1 is a dry-run-only skeleton; real write logic is deferred to Step 2F-4c-2"
- **同样绝对不调** `run_predict` / `save_prediction` / `save_outcome`
- 即使未来 4c-2 启用真写入，也必须走 `save_prediction(analysis_date_override=D)` + `save_outcome(captured_at_override=D+1)`，**永远不允许直接 INSERT**

#### planner 失败模式透传

- planner `missing_data` / `insufficient_data` / `error` → writer 同状态返回；`notes` 描述"planner returned status=X; no candidate pairs available, nothing was written"

### 20.3 limit 安全边界

| 输入 | 输出 | 理由 |
|---|---|---|
| `None` / 默认 | 30 | `_DEFAULT_LIMIT` |
| 1 ≤ N ≤ 50 | N | 直接通过 |
| N > 50 | **50** | **`_LIMIT_HARD_CAP=50`** 强制 clamp——writer 是高风险（未来会真写 DB），故比 planner 更紧 |
| `0` / 负数 / `bool` / `非 int` | 30 | 同 planner 防御口径 |

测试 `test_limit_clamped_at_hard_cap_50` 锁住：`run_contract_replay(limit=200)` → `requested_limit=50`。

### 20.4 严守边界

- ❌ **`dry_run=False` 不调用** `run_predict` / `save_prediction` / `save_outcome` —— 4c-1 范围
- ❌ **永远不允许直接 INSERT / UPDATE** —— 未来 4c-2 真写也必须走 `save_prediction` / `save_outcome` 真路径
- ❌ **不调 yfinance / 不调网络**（writer 只调 planner，planner 已是离线）
- ❌ **不动** `predict.py` / `run_predict` / 4 个 builder / `prediction_store` (`save_prediction` / `save_outcome`) / adapter / contract validator / `scanner.py` / `matcher.py` / 6 个现有 read-only 工具 / DB schema / UI
- ❌ **不接** `risk_model.py` / `contradiction_engine.py` / `confidence_engine.py`
- ❌ **不接** `big_up_contradiction_card` / `exclusion_reliability_review` / `big_down_tail_warning` / `anti_false_exclusion_audit`
- ❌ **不接** longbridge / broker / paper_trade / 真实交易 / 模拟盘 API
- ❌ **不清理 2099 synthetic records**（DB hygiene 范围；不在 4c-1 范围）
- ❌ **不让** 04 / 05 / 07 任何 required 字段升级

### 20.5 CLI 用法

```bash
# 默认 dry-run（永远是默认）
python3 scripts/run_contract_replay.py
python3 scripts/run_contract_replay.py --start 2024-01-01 --end 2024-01-31
python3 scripts/run_contract_replay.py --limit 50

# 显式 --write（4c-1 阶段返回 not_implemented_for_write，仍然不写 DB）
python3 scripts/run_contract_replay.py --write
```

stdout 输出 UTF-8 JSON（`ensure_ascii=False, indent=2`）；进程不写文件、不写 DB、不调网络。

### 20.6 与 Step 2F-4 plan 的对接

| Step 2F-4 阶段 | 状态 |
|---|---|
| 方案文档（plan）| ✅ commit `e9b44e2` |
| 4a 诊断 | ✅（无代码） |
| 4b dry-run planner | ✅ commit `4c89d98` |
| 4b-verify 实跑 | ✅（无代码；2502 trading days 验证）|
| 4c-prereq 时间 override | ✅ commit `5dbd9ac` |
| **4c-1 writer skeleton（本节）** | **本轮** |
| 4c-2 真写入逻辑 | 待办——必须在 DB hygiene 后启动 |
| 4d 90-pair 解锁 calibration_ready | 4c-2 完成后 |

### 20.7 Step 2F-4c-2 的最小动作（本节范围之外）

writer 内部填入 4 步链路（每步都已就位）：

```python
# 4c-2 范围（本节不实施）
for pair in planner_result["candidate_pairs"]:
    D = pair["as_of_date"]
    D_plus_1 = pair["prediction_for_date"]
    scan = build_historical_scan_at(D)              # ← 需要 4c-2 设计
    predict = run_predict(scan, ...)                # ← 已就位（pure 函数）
    pid = save_prediction(
        ..., snapshot_id=f"replay_phaseA_{D}",
        analysis_date_override=D,                    # ← 4c-prereq 已就位
    )
    actual_ohlcv = fetch_actual_ohlcv_at(D_plus_1)  # ← 需要 4c-2 设计
    direction_correct = _compute_direction_correct(  # ← 已就位
        predict["final_bias"],
        (actual_ohlcv["close"] - actual_ohlcv["prev_close"]) / actual_ohlcv["prev_close"],
    )
    save_outcome(
        ..., direction_correct=direction_correct,
        captured_at_override=f"{D_plus_1}T16:00:00",  # ← 4c-prereq 已就位
    )
```

**4c-2 真正的工程难点**：
1. `build_historical_scan_at(D)`：需要把 scanner 输入按 `<= D` 截断（含 peer NVDA / SOXX / QQQ 的 `<= D`）
2. `fetch_actual_ohlcv_at(D_plus_1)`：从 `coded_data/AVGO_coded.csv` 读 D+1 行 OHLCV（已存在数据，直接读）
3. anti-lookahead 端到端验证：可能需要新增一个独立 audit 工具（仿 calibration_inputs 模式）

测试基线：2139 → 2167（+28）。0 failed；10 skipped 不变。
