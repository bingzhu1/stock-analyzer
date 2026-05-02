# Step 1A — Projection Output Contract

> 状态：设计冻结（草案 v1，未实现）
> 路线：05 记录路线（自动数据 → 自动结构 → 自动推演 → 自动否定 → 自动置信 → 自动模拟交易 → 自动复盘 → 自动提炼规则 → 历史教训回灌）
> 范围：本文件**只冻结输出格式**，不实现任何业务逻辑。

## 1. 目标

为什么必须先冻结推演输出格式：

- **防止系统耦合**：推演系统、否定系统、置信度系统三件套长期混在 `predict_result` 同一个 dict 里，谁都能改，谁都能吃。一旦定型，三方各自只能填自己那段，互不污染。
- **给历史回放和模拟交易提供稳定字段**：未来"重新跑 N 年"的回放、夜里跑的模拟交易、自动复盘工具，都需要从同一份输出里**只读**关键字段。字段名漂移一次，下游全坏。
- **限制 Claude 的发散**：未来任何一轮开发不允许擅自新增 / 删除 / 改名 / 改语义这 8 段中的字段；只能扩 `notes` / `extras` / `extensions` 这类独立子键。
- **形成可对比的 JSON 痕迹**：历史回放产出的 JSON 与今天产出的 JSON 用同一个 schema 才能对齐。

## 2. 总体输出结构

`run_predict(...)` 最终返回一个**单层 dict**，固定包含且仅包含 8 个顶级 section（顺序固定）：

| 序号 | 顶级 key | 中文标题 | 责任系统 |
|---|---|---|---|
| 01 | `current_structure` | 当前结构 | scanner / 数据层 |
| 02 | `avgo_primary_projection` | AVGO 近 15 日主推演 | 主推演引擎 |
| 03 | `peer_confirmation_adjustment` | NVDA / SOXX / QQQ 同行确认修正 | 同行修正层 |
| 04 | `exclusion_system` | 否定系统 | exclusion / contradiction |
| 05 | `confidence_system` | 置信度系统 | confidence engine |
| 06 | `final_projection` | 最终推演结论 | 收口层 |
| 07 | `simulated_trade` | 模拟交易建议 | 模拟交易决策层 |
| 08 | `review_payload` | 复盘字段 | review / outcome 接口 |

每个 section 也是**单层 dict**，禁止再嵌套同名 section。允许在每个 section 内额外加一个 `extras: dict` 用于试验性字段，但**主链路只读 contract 内字段**。

## 3. 每个部分必须包含的字段

> 字段名一律 `snake_case`。字段语义在注释里用中文写清楚。`null` 表示"信息不足"，**禁止用 0 / "" 假装有值**。

### 01 `current_structure` — 当前结构

| 字段 | 类型 | 含义 |
|---|---|---|
| `symbol` | str | 标的代码，目前固定 `"AVGO"` |
| `analysis_date` | str (YYYY-MM-DD) | 本次推演运行所基于的数据截止日 |
| `prediction_for_date` | str (YYYY-MM-DD) | 本次推演要预测的目标日（通常 `analysis_date + 1 个交易日`） |
| `data_window_days` | int | 用于结构识别的回看窗口（默认 15） |
| `current_price` | float | 截止日收盘价 |
| `previous_close` | float | 截止日前一交易日收盘价 |
| `volume` | int | 截止日成交量 |
| `turnover` | float | 截止日成交额（≈ price × volume） |
| `price_position_15d` | float | 当前价在过去 15 日 [low, high] 中的相对位置（0–1） |
| `structure_label` | str | 结构标签：`"顶部分歧"` / `"启动"` / `"加速"` / `"整理"` / `"延续"` / `"衰竭风险"` 等 |
| `short_summary` | str | 一句中文白描："收盘 X，处于 15 日高位 Y%，结构 Z" |

### 02 `avgo_primary_projection` — AVGO 近 15 日主推演

| 字段 | 类型 | 含义 |
|---|---|---|
| `primary_direction` | str | `"偏多"` / `"偏空"` / `"中性"` |
| `open_projection` | str | `"高开"` / `"平开"` / `"低开"` |
| `intraday_path_projection` | str | `"高走"` / `"震荡"` / `"低走"` / `"V 型反转"` / `"倒 V"` |
| `close_projection` | str | `"收涨"` / `"收平"` / `"收跌"` |
| `five_state_projection` | str | 五态合并：`"大涨"` / `"小涨"` / `"震荡"` / `"小跌"` / `"大跌"` |
| `historical_sample_count` | int | 该结构在历史上找到的相似样本数 |
| `similar_pattern_stats` | dict | `{ "win_rate": float, "avg_close_change": float, "median_close_change": float }` |
| `key_evidence` | list[str] | 给出该方向的 1–5 条结构化证据，每条一句中文 |
| `primary_confidence_raw` | str | 主推演**原始**置信度（`"high"` / `"medium"` / `"low"`），**未经过 04 / 05 调整** |

### 03 `peer_confirmation_adjustment` — NVDA / SOXX / QQQ 同行确认修正

| 字段 | 类型 | 含义 |
|---|---|---|
| `peer_symbols` | list[str] | 固定 `["NVDA", "SOXX", "QQQ"]` |
| `nvda_signal` | str | `"reinforce"` / `"weaken"` / `"neutral"` / `"unknown"` |
| `soxx_signal` | str | 同上 |
| `qqq_signal` | str | 同上 |
| `peer_alignment` | str | 综合：`"all_reinforce"` / `"mixed"` / `"all_weaken"` / `"insufficient"` |
| `peer_adjustment` | str | 对主推演方向的调整：`"upgrade"` / `"hold"` / `"downgrade"` / `"flip_to_neutral"` |
| `adjusted_direction` | str | 调整后方向（仍是 `"偏多"` / `"偏空"` / `"中性"`） |
| `adjustment_reason` | str | 一句中文写清楚为什么这样调（"NVDA + SOXX 同时反向，证据弱化"） |

### 04 `exclusion_system` — 否定系统

| 字段 | 类型 | 含义 |
|---|---|---|
| `exclusion_level` | str | `"none"` / `"soft"` / `"hard"` |
| `exclusion_sources` | list[str] | 触发否定的来源标签集合：`["macro_bearish", "volume_drop", "leader_diverge", "overheat"]` 中的子集 |
| `exclusion_reasons` | list[str] | 每个 source 对应的中文解释（与 `exclusion_sources` **同序、同长**） |
| `forced_exclusion` | bool | 是否触发"强制否定"（hard 级别） |
| `anti_false_exclusion_triggered` | bool | 反"误否定"审计是否拦截了一次 hard exclusion |
| `what_would_invalidate_bullish_case` | list[str] | 看多假设的反向证据清单 |
| `what_would_invalidate_bearish_case` | list[str] | 看空假设的反向证据清单 |

### 05 `confidence_system` — 置信度系统

| 字段 | 类型 | 含义 |
|---|---|---|
| `historical_score` | float | 0–1，来自相似样本胜率 |
| `structure_score` | float | 0–1，来自当前结构清晰度 |
| `peer_score` | float | 0–1，来自同行 alignment |
| `exclusion_penalty` | float | 0–1，**减分项**（来自 04 的扣分） |
| `event_score` | float | 0–1，事件型加/减分（财报、宏观、Fed 决议；本轮全留 `null` 占位，不接事件源） |
| `total_confidence` | float | 0–1，综合分（不强制规定计算公式；公式由 confidence engine 决定） |
| `confidence_level` | str | `"high"` / `"medium"` / `"low"`（由 `total_confidence` 分桶） |
| `confidence_reason` | str | 一句中文："历史胜率 X%，同行确认 Y，否定扣分 Z，综合 medium" |

### 06 `final_projection` — 最终推演结论

| 字段 | 类型 | 含义 |
|---|---|---|
| `final_direction` | str | `"偏多"` / `"偏空"` / `"中性"`（在 03 调整、04 否定、05 置信之后的最终方向） |
| `final_open_projection` | str | 最终开盘倾向（同 02 的取值集） |
| `final_intraday_path` | str | 最终日内路径（同 02 的取值集） |
| `final_close_projection` | str | 最终收盘倾向（同 02 的取值集） |
| `final_five_state` | str | 最终五态（同 02 的取值集） |
| `probability_bucket` | str | `"≥70%"` / `"55–70%"` / `"45–55%"` / `"30–45%"` / `"≤30%"` |
| `key_price_levels` | dict | `{ "support": float, "resistance": float, "breakout_trigger": float, "breakdown_trigger": float }` |
| `final_one_sentence` | str | 一句中文最终结论："明日偏多，五态预期小涨，关键支撑 X 阻力 Y，置信度 medium" |

### 07 `simulated_trade` — 模拟交易建议

| 字段 | 类型 | 含义 |
|---|---|---|
| `trade_action` | str | `"open"` / `"hold"` / `"close"` / `"no_trade"` |
| `trade_direction` | str | `"long"` / `"short"` / `"none"` |
| `entry_condition` | str | 一句中文进场条件："开盘后 30 分钟内若站稳 X 进多" |
| `stop_loss_condition` | str | 一句中文止损："若跌破 Y 立即止损" |
| `take_profit_condition` | str | 一句中文止盈："至 Z 减半，全部到 W 出清" |
| `suggested_position_size` | str | `"0%"` / `"25%"` / `"50%"` / `"75%"` / `"100%"`（仓位档位，不是金额） |
| `no_trade_reason` | str \| null | 当 `trade_action == "no_trade"` 必须填，否则 null |

### 08 `review_payload` — 复盘字段

| 字段 | 类型 | 含义 |
|---|---|---|
| `predicted_open_type` | str | 预测的开盘倾向（取自 06）|
| `predicted_path_type` | str | 预测的日内路径（取自 06） |
| `predicted_close_type` | str | 预测的收盘倾向（取自 06） |
| `predicted_five_state` | str | 预测的五态（取自 06） |
| `predicted_confidence` | str | 预测置信度（取自 05.confidence_level） |
| `prediction_id` | str | 预测唯一 id（写入 `prediction_log` 后由该层回填） |
| `review_ready_fields` | list[str] | 列出本次预测里**复盘时必须比对**的字段名清单，给 outcome / review 用 |

## 4. JSON-like 输出示例

> 所有数值字段为 placeholder（用尖括号占位）；类别型字段示例值为合法集合内一员。**不编造真实市场数据**。

```jsonc
{
  "current_structure": {
    "symbol": "AVGO",
    "analysis_date": "<YYYY-MM-DD>",
    "prediction_for_date": "<YYYY-MM-DD>",
    "data_window_days": 15,
    "current_price": "<current_price>",
    "previous_close": "<previous_close>",
    "volume": "<volume>",
    "turnover": "<turnover>",
    "price_position_15d": "<0.0–1.0>",
    "structure_label": "整理",
    "short_summary": "收盘 <price>，处于 15 日 <pct> 位，结构 整理"
  },

  "avgo_primary_projection": {
    "primary_direction": "偏多",
    "open_projection": "高开",
    "intraday_path_projection": "高走",
    "close_projection": "收涨",
    "five_state_projection": "小涨",
    "historical_sample_count": "<int>",
    "similar_pattern_stats": {
      "win_rate": "<0.0–1.0>",
      "avg_close_change": "<float>",
      "median_close_change": "<float>"
    },
    "key_evidence": [
      "近 15 日量能持续放大",
      "突破前高 N 天后未回踩",
      "MA20 / MA60 多头排列"
    ],
    "primary_confidence_raw": "medium"
  },

  "peer_confirmation_adjustment": {
    "peer_symbols": ["NVDA", "SOXX", "QQQ"],
    "nvda_signal": "reinforce",
    "soxx_signal": "neutral",
    "qqq_signal": "reinforce",
    "peer_alignment": "mixed",
    "peer_adjustment": "hold",
    "adjusted_direction": "偏多",
    "adjustment_reason": "NVDA + QQQ 同向支持，SOXX 中性，整体维持偏多"
  },

  "exclusion_system": {
    "exclusion_level": "soft",
    "exclusion_sources": ["volume_drop"],
    "exclusion_reasons": ["最近 3 日量能背离，需要降一级置信"],
    "forced_exclusion": false,
    "anti_false_exclusion_triggered": false,
    "what_would_invalidate_bullish_case": [
      "明日开盘后 30 分钟跌破 <support>",
      "成交量不足前 5 日均量 60%"
    ],
    "what_would_invalidate_bearish_case": [
      "明日开盘直接突破 <resistance> 并放量"
    ]
  },

  "confidence_system": {
    "historical_score": "<0.0–1.0>",
    "structure_score": "<0.0–1.0>",
    "peer_score": "<0.0–1.0>",
    "exclusion_penalty": "<0.0–1.0>",
    "event_score": null,
    "total_confidence": "<0.0–1.0>",
    "confidence_level": "medium",
    "confidence_reason": "历史胜率 <pct>，同行 mixed，否定扣分 soft，综合 medium"
  },

  "final_projection": {
    "final_direction": "偏多",
    "final_open_projection": "高开",
    "final_intraday_path": "高走",
    "final_close_projection": "收涨",
    "final_five_state": "小涨",
    "probability_bucket": "55–70%",
    "key_price_levels": {
      "support": "<support>",
      "resistance": "<resistance>",
      "breakout_trigger": "<breakout>",
      "breakdown_trigger": "<breakdown>"
    },
    "final_one_sentence": "明日偏多，预期小涨，关键支撑 <support> 阻力 <resistance>，置信度 medium"
  },

  "simulated_trade": {
    "trade_action": "open",
    "trade_direction": "long",
    "entry_condition": "开盘后 30 分钟内若站稳 <breakout_trigger> 进多",
    "stop_loss_condition": "若日内跌破 <support> 立即止损",
    "take_profit_condition": "至 <resistance> 减半，全部至 <resistance + 1ATR> 出清",
    "suggested_position_size": "50%",
    "no_trade_reason": null
  },

  "review_payload": {
    "predicted_open_type": "高开",
    "predicted_path_type": "高走",
    "predicted_close_type": "收涨",
    "predicted_five_state": "小涨",
    "predicted_confidence": "medium",
    "prediction_id": "<set_by_prediction_store>",
    "review_ready_fields": [
      "predicted_open_type",
      "predicted_path_type",
      "predicted_close_type",
      "predicted_five_state",
      "predicted_confidence"
    ]
  }
}
```

## 5. 后续接入规则

未来任何 PR 都必须遵守，否则 reviewer 直接拒：

1. **`run_predict(...)` 是唯一收口**：最终必须返回正好这 8 个顶级 key 的 dict。`run_predict` 之外的辅助函数可以返回中间结构，但不能让中间结构泄露到 `prediction_log`。
2. **UI 只读不改**：`ui/predict_tab.py` / `ui/history_tab.py` / `ui/review_tab.py` 只允许**读**这 8 段字段渲染，**不允许**重命名、合并、计算派生字段并冒充原字段。需要 UI 计算的派生量必须写在 UI 层局部变量，不回写 dict。
3. **04 / 05 必须是独立模块**：否定系统和置信度系统**必须**各自有独立的 service 文件、独立的单元测试，最终由收口层把它们的输出**装进**对应 section。**禁止**在主推演引擎里直接给置信度赋值。
4. **历史回放只读这些字段**：未来"AVGO 1000 天回放"、"2016–2020 回放"等回放工具，从历史 `prediction_log` 读出来的就是这个 schema；新增字段必须做向后兼容（旧记录该字段为 `null`）。
5. **模拟交易只能基于 06 + 05**：`simulated_trade` 决策**只能**消费 `final_projection` 和 `confidence_system` 的字段，不允许越过它们去摸 `current_structure` 的原始价格之外的内部细节，**不允许**自己重新跑一遍主推演。

## 6. 非目标（本轮明确不做）

- ❌ 不实现 / 不修改 `run_predict`
- ❌ 不实现 / 不修改任何 UI（包括 [ui/predict_tab.py](../ui/predict_tab.py)）
- ❌ 不接长桥 / Longbridge / 任何券商 API
- ❌ 不抓新闻
- ❌ 不抓财报
- ❌ 不跑历史回放、不写回放脚本
- ❌ 不动 [risk_model.py](../risk_model.py) / [contradiction_engine.py](../contradiction_engine.py) / [confidence_engine.py](../confidence_engine.py) 三个 v1 stub
- ❌ 不开发 PR-B / PR-C / PR-D
- ❌ 不处理 `.claude/worktrees/`
- ❌ 不动 stash / 不动 untracked 文件

## 7. 后续 step（路线图占位）

| step | 范围 | 依赖 |
|---|---|---|
| **1A** (本文) | 冻结输出格式 | — |
| 1B | 写一份"contract validator"：纯函数，输入 dict，断言 schema 合规；只做检查，不改业务 | 1A |
| 1C | 把现有 `predict_result` 的字段一对一映射到本 contract 的 8 个 section（adapter 层） | 1A + 1B |
| 1D | 让 `prediction_store.save_prediction(...)` 写入 contract 化的 dict | 1A + 1C |
| 1E | history / review UI 只读 contract 字段 | 1A + 1D |
| 1F | 模拟交易决策最小骨架（只生成 `simulated_trade` 段，不下单） | 1A + 1E |
