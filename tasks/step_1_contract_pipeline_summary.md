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
| 07 `simulated_trade` | ❌ 占位 | adapter 硬编码 `"no_trade"`；待模拟交易决策层 |
| 08 `review_payload` | 字段化（依赖 06） | adapter 从 final 字段派生 |

**已完成：** 02 / 03 / 06 三段由 builder 自发布，adapter 退化为"先信 self-published、再回退老推导、非法值不污染输出"。`run_predict` 主决策路径（投票 / 升降 / 收口）一行未改。Step 2C-2 / 2C-3b 让 04 / 05 段在保持 required 字段 stub 不变的前提下，把已有风险信号 / score-like 信号暴露到各自的 `extras`。

**仍未做：** 07 段仍由 adapter 输出占位值；04 段的 required 字段（`exclusion_level / forced_exclusion / anti_false_exclusion_triggered`）和 05 段的 4 个 score 字段（`historical_score / structure_score / peer_score / exclusion_penalty`）+ `event_score` 也尚未真正字段化，等 Step 2C-3+ / 2D 真正的否定模块 / calibration 引擎落地。

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
