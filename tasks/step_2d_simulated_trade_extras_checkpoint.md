# Step 2D — Simulated Trade Extras Checkpoint

> 状态：Step 2D-1 ~ 2D-2 已全部进 main。本文件是进入 Step 2E（dashboard）/ Step 2F（calibration 诊断）/ Step 2G（exclusion 规则设计）/ 真模拟交易系统讨论之前的 handoff 快照。
> 只写文档，不改任何业务代码。

## 1. 当前完成状态

| 子步 | 主题 | commit | 关键产出 |
|---|---|---|---|
| 2D-1 | 只读诊断 07 `simulated_trade` 来源 | —（无代码改动） | 报告 adapter 07 段全 stub、`predict_result` 已有 02/03/06 字段化产物 + 04/05 extras 派生信号；整仓库零 trading 模块 import；`key_price_levels` 在所有路径上永远为 `{}` |
| 2D-2 | 07 `simulated_trade.extras` 暴露 trade-relevant 观察信号 | `f125d45 feat(contract): expose trade signals via simulated_trade extras` | 6 个交易决策字段保持 pinned 安全 stub；`no_trade_reason` 升级为静态诚实文本（指向 06 / 05 段）；新增 `extras` 9 键（`final_direction / final_five_state / probability_bucket / confidence_level / total_confidence / path_risk_level / soft_signal / has_key_price_levels / trade_engine_enabled=False`）；`tests/test_simulated_trade_contract_fields.py` 29 case + 22 subtests |

## 2. 当前 main 状态

- **main 最新 commit：** `f125d45 feat(contract): expose trade signals via simulated_trade extras`
- **测试基线：** **2033 passed / 0 failed / 10 skipped / 65 subtests**（从 Step 2C 末尾的 2003 累积 +30）
- **新增 / 更新的测试文件：**
  - `tests/test_simulated_trade_contract_fields.py`（2D-2 新增）
  - `tests/test_projection_output_adapter.py::SimulatedTradeDefaultTests`（2D-2 新增 1 case `test_simulated_trade_extras_surfaces_decision_signals`）

## 3. 07 `simulated_trade` 当前状态

### 3.1 contract required 字段（全部 pinned，**永不动**）

| 字段 | 当前值 | 类型 / contract enum | 策略边界 |
|---|---|---|---|
| `trade_action` | `"no_trade"` | enum {open, hold, close, no_trade} | **永不离开 `"no_trade"`** |
| `trade_direction` | `"none"` | enum {long, short, none} | **永不离开 `"none"`** |
| `entry_condition` | `""` | str | **永不非空** |
| `stop_loss_condition` | `""` | str | **永不非空** |
| `take_profit_condition` | `""` | str | **永不非空** |
| `suggested_position_size` | `"0%"` | enum {0%, 25%, 50%, 75%, 100%} | **永不离开 `"0%"`** |
| `no_trade_reason` | 静态诚实文本（见 §3.2） | str_or_null | 文本静态、零未来漂移 |

**策略边界，不是工程缺失。** 本项目按设计**不允许**让 07 决策字段动起来——即使未来有真模拟交易需求，也应当新增独立 contract section 或子键，永远配合 `trade_engine_enabled = False` 或类似明示开关。

### 3.2 `no_trade_reason` 静态文本

```
Simulated trade engine not enabled in this build; section is informational
only. See final_projection and confidence_system for decision signals.
```

- **完全静态**：不论 predict 是 None / bullish / bearish / high-risk，文本恒定（`test_no_trade_reason_is_invariant_to_predict_input` 锁住）
- **诚实**：`"not enabled"` 明示引擎未启用，不是 Step 1C 时期 `"yet wired"` 的"未来会接"暗示
- **指向真实信号源**：`final_projection` / `confidence_system` —— 让消费者去读 06 / 05 段，而不是把 07 当决策依据

### 3.3 `extras` 字段（Step 2D-2 新增）

| extras 键 | 类型 | 来源（仅读 predict_result） |
|---|---|---|
| `final_direction` | enum 偏多/偏空/中性 | `predict["final_projection"]["final_direction"]`；非合法 → `"中性"` |
| `final_five_state` | enum 大涨/小涨/震荡/小跌/大跌 | `predict["final_projection"]["final_five_state"]`；非合法 → `"震荡"` |
| `probability_bucket` | enum ≥70%/55–70%/45–55%/30–45%/≤30% \| `"unknown"` | `predict["final_projection"]["probability_bucket"]`；非合法 → `"unknown"` |
| `confidence_level` | enum high/medium/low | `_normalize_confidence(predict["final_confidence"])` |
| `total_confidence` | float | `_CONFIDENCE_TO_TOTAL[level]`（0.75 / 0.50 / 0.25） |
| `path_risk_level` | enum low/medium/high \| `"unknown"` | `predict["path_risk"]`；非合法 → `"unknown"` |
| `soft_signal` | enum peer_weaken/high_path_risk/none | **独立重派生**，与 §12 / §13 同决策树 |
| `has_key_price_levels` | bool | `isinstance(klp, dict) and bool(klp)`（**今天永远 `False`**：所有路径上 `key_price_levels` 都是 `{}` 或 `[]`） |
| `trade_engine_enabled` | bool 常量 | **`False`**，明示交易引擎未启用 |

`soft_signal` 决策树（与 04 / 05 段完全一致，**独立重派生**，不读 sibling section's extras）：
- `"peer_confirmation=weaken" in conflicting_factors` → `"peer_weaken"`
- 否则 `path_risk == "high"` → `"high_path_risk"`
- 否则 → `"none"`

### 3.4 严守边界

- ❌ `extras` 只是观察 metadata，**不代表交易建议**
- ❌ 下游消费者**绝对不应**据 `final_direction == "偏多"` / `soft_signal == "high_path_risk"` / `probability_bucket == "≥70%"` 等做开 / 平仓判断
- ❌ `trade_engine_enabled` **必须保持 `False`**——任何让它变 `True` 的改动需先讨论"是否引入交易能力"这一根本性策略变更
- ❌ `no_trade_reason` 指向 `final_projection` / `confidence_system` 是为了**信息透明**，**不构成交易指令**——它告诉消费者"如果你想做决策，去读 06 / 05；07 本身没有决策"

## 4. 没有改的东西

严格未触碰（Step 2D 全程）：

- ❌ `predict.py` 任何决策逻辑
- ❌ `run_predict` 主入口（签名 / 子步骤调用顺序 / unavailable 分支触发条件全部不变）
- ❌ 4 个 builder（`build_primary_projection` / `apply_peer_adjustment` / `build_final_projection` / `_apply_research_adjustment`）
- ❌ `services/projection_output_contract.py`（validator）
- ❌ `services/prediction_store.py`（save 旁路）
- ❌ Step 1 read-only 工具：`contract_payload_inspector` / `contract_payload_diff` / `contract_payload_trend` / `contract_outcome_correlation`
- ❌ `risk_model.py` / `contradiction_engine.py` / `confidence_engine.py` 三个 v1 stub（整仓库零 import 状态保持）
- ❌ `big_up_contradiction_card` / `exclusion_reliability_review` / `big_down_tail_warning` / `anti_false_exclusion_audit` 四个 UI / 离线模块
- ❌ UI（`ui/predict_tab.py` 等）
- ❌ scanner / matcher / 数据层
- ❌ **longbridge / broker / paper_trade / 真实交易 / 模拟盘 API**（grep `longbridge|paper_trade|broker|trading_api` 整仓库仍只命中 `scripts/run_1005_three_system_replay.py:7` 注释里的"no broker, no automation, no live trading"）
- ❌ 长桥 / 新闻 / 财报数据接入
- ❌ stash / `.claude/worktrees/` / `logs/prediction_log.jsonl`

## 5. 当前 contract 段进度（8 段总览，Step 2D-2 后版本）

| Section | 状态 | 说明 |
|---|---|---|
| 01 `current_structure` | 字段化 | adapter 从 scan + `primary_projection.lookback_days` 构造（Step 2B-2 联动） |
| 02 `avgo_primary_projection` | **字段化** | `build_primary_projection` self-publish（Step 2B-2） |
| 03 `peer_confirmation_adjustment` | **字段化** | `apply_peer_adjustment` self-publish（Step 2B-3，bias-aware 翻译） |
| 04 `exclusion_system` | ⚠️ required 仍占位 + `extras` 暴露真实风险信号（Step 2C-2） | required 5 字段全 stub；extras 6 键 |
| 05 `confidence_system` | ⚠️ 部分真值 + 4 score 仍占位 + `extras` 暴露 raw score-like 信号（Step 2C-3b） | 3 真值 / 4 score stub / event_score None；extras 10 键 |
| 06 `final_projection` | **字段化** | `build_final_projection` self-publish（Step 2B-4） |
| 07 `simulated_trade` | ⚠️ 6 决策字段 pinned + `no_trade_reason` 静态诚实 + `extras` 暴露 trade-relevant 观察信号（Step 2D-2） | required 6 决策字段策略边界 pinned；extras 9 键含 `trade_engine_enabled=False` |
| 08 `review_payload` | 部分字段化（依赖 06） | adapter 从 final 字段派生；`prediction_id=""` 仍空 |

**已完成：** 02 / 03 / 06 三段由 builder 自发布；01 联动 02；04 / 05 / 07 三段在保持 required 字段语义不变的前提下用 `extras` 暴露 raw signals（Step 2C-2 / 2C-3b / 2D-2）。三段 extras 的 `soft_signal` 完全同口径独立派生。

**仍未做：**
- 07 段的 6 个决策字段（`trade_action / trade_direction / 三个 condition / suggested_position_size`）按设计**永不动**——本项目策略边界
- 04 段的 required 字段（`exclusion_level / forced_exclusion / anti_false_exclusion_triggered`）尚未真字段化
- 05 段的 4 个 score 字段（`historical_score / structure_score / peer_score / exclusion_penalty`）+ `event_score` 尚未真字段化
- 08 段的 `prediction_id == ""` 仍空

## 6. 下一步建议

> **强烈建议：不要把 `extras` 信号直接当交易系统使用。** Step 2C / 2D 的 extras 模式专门设计成"只读观察"，把它们升级为决策需要先有数据驱动的 calibration 与 backtest，不是字段填充任务。

| 候选 step | 范围 | 风险 |
|---|---|---|
| **Step 2E** —— contract dashboard / 汇总工具 | 写一个只读 CLI 脚本（仿 `summarize_recent_contract_payloads.py`），专门 dump 最近 N 条 prediction 的 04 / 05 / 07 三段 `extras.*` 分布；让 extras 信号"可被人类看到"，闭环验证 2C / 2D 的设计假设 | 极低，新工具不动主链；与 Step 1 read-only 工具同模式 |
| **Step 2F** —— confidence calibration 只读诊断 | 用已落库 `contract_payload_json` 跑离线分析：`primary_projection.score` / `confirm_count - oppose_count` / `path_risk` 与 outcome 的实际相关性；不实现 calibration 函数 | 低，纯数据诊断；为 05 段 score 真字段化提供数据依据 |
| **Step 2G** —— `exclusion_level` soft/hard 规则设计 | 写一份"在什么条件下 `exclusion_level` 应当升 `soft`/`hard`"的设计文档，引用 2C-1 诊断里的 `big_up_contradiction_card` / `exclusion_reliability_review` 等已有信号 + 2F 数据诊断结果；**不实现，等 backtest 数据足量** | 低，纯设计文档 |
| **真模拟交易系统** | **必须另开阶段**，不可直接从 07 `extras` 推出。需要明确：策略层、回测、风险控制、是否接真 API。设计前必须先 review 本文件 §3.4 严守边界 | 高，超出 Step 2 字段化范围；本文件不推荐立即启动 |

**推荐顺序：** **Step 2E（dashboard 闭环验证）→ Step 2F（calibration 数据诊断）→ Step 2G（exclusion 规则设计）→ 真 calibration / exclusion 接入（Step 3+）→ 真模拟交易（独立阶段，需新立项讨论）**。

### 严守边界（与 Step 2C 全程一致 + 本轮交易特殊约束）

- ❌ 不要把 07 `extras` 信号直接接入交易决策
- ❌ 不要让 `trade_engine_enabled` 变 `True`
- ❌ 不要让 6 决策字段中的任何一个动起来
- ❌ 不要在没有真实 backtest 的情况下让 04 `exclusion_level` 升 `soft`/`hard`
- ❌ 不要把 `primary_score_raw` 直接归一化进 05 `structure_score`（calibration 决策，不是字段填充）
- ❌ 不要接 longbridge / broker / paper_trade / 真实交易 / 模拟盘 API
- ❌ 不要接 `confidence_engine.py` / `risk_model.py` / `contradiction_engine.py` 三个 v1 stub
- ❌ 不要接 `big_up_contradiction_card` / `exclusion_reliability_review` / `big_down_tail_warning` / `anti_false_exclusion_audit` 到主链
- ❌ 不要改 `predict.py` / `run_predict`
- ❌ 不要接长桥 / 新闻 / 财报

## 7. Step 2 系列总览（截至本 checkpoint）

| 阶段 | 范围 | 进 main commit |
|---|---|---|
| **Step 2A** | run_predict 两步结构核验（只读诊断） | —（无代码） |
| **Step 2B-1** | contract alignment 安全网 + data_window drift 暴露 | `2ac41dd` |
| **Step 2B-2** | primary_projection 自发布 02 段 + data_window_days 联动 | `0fccc72` |
| **Step 2B-3** | peer_adjustment 自发布 03 段 | `9aca3f2` |
| **Step 2B-4** | final_projection 自发布 06 段 | `c2d1d34` |
| **Step 2B Summary** | 字段化 checkpoint | `9ae30de` |
| **Step 2C-1** | exclusion_system 只读诊断 | —（无代码） |
| **Step 2C-2** | exclusion_system.extras 暴露 raw risk signals | `8f689a2` |
| **Step 2C-2.5 / 2C-2.6** | DB contract_payload_json 落库验证 | —（无代码；本地 DB 验证） |
| **Step 2C-3a** | confidence_system 只读诊断 | —（无代码） |
| **Step 2C-3b** | confidence_system.extras 暴露 raw score-like signals | `c188725` |
| **Step 2C Summary** | exclusion / confidence extras checkpoint | `1f9f8fa` |
| **Step 2D-1** | simulated_trade 只读诊断 | —（无代码） |
| **Step 2D-2** | simulated_trade.extras 暴露 trade-relevant signals | `f125d45` |
| **Step 2D Summary** | 本文件 | (pending commit) |

**测试基线累积：** Step 2 起点 1883 → 2033（+150）；0 failed；10 skipped 全程不变。

**核心不变量：** `predict.py` / `run_predict` / 4 个 builder / contract validator / UI / `prediction_store` / Step 1 工具 / 三个 v1 stub / 4 个离线模块 / 任何 trading API 在 Step 2 全程一行未改 / 一行未引入。
