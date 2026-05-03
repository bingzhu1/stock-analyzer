# Step 2B — Projection Fieldization Checkpoint

> 状态：Step 2B-1 ~ 2B-4 已全部进 main。本文件是进入 Step 2C 之前的 handoff 快照。
> 只写文档，不改任何业务代码。

## 1. 当前完成状态

| 子步 | 主题 | commit | 关键产出 |
|---|---|---|---|
| 2B-1 | contract alignment 安全网 + `data_window_days` 漂移暴露 | `2ac41dd test(contract): pin run_predict adapter alignment and flag data_window drift` | `tests/test_run_predict_contract_alignment.py`；锁住 run_predict → adapter → validator 链；首次显式记录 `lookback_days = 20` vs `data_window_days = 15` 不一致 |
| 2B-2 | `primary_projection` 自发布 02 段 + `data_window_days` 联动 | `0fccc72 feat(contract): self-publish primary projection fields and wire data window` | `build_primary_projection()` 自带 8 个 02 段字段；adapter 改读 `predict_result["primary_projection"]["lookback_days"]`；删 disagree 临时 case |
| 2B-3 | `peer_adjustment` 自发布 03 段 | `9aca3f2 feat(contract): peer adjustment publishes contract fields` | `apply_peer_adjustment()` 自带 8 个 03 段字段（bias-aware 翻译）；adapter 三级优先级（self-published → legacy fallback → 非法值回退） |
| 2B-4 | `final_projection` 自发布 06 段 | `c2d1d34 feat(contract): final projection publishes contract fields` | `build_final_projection()` 自带 8 个 06 段字段；`final_one_sentence` 与 `prediction_summary` 引用同一字符串；adapter 同三级优先级 |

## 2. 当前 main 状态

- **main 最新 commit：** `c2d1d34 feat(contract): final projection publishes contract fields`
- **测试基线：** **1950 passed / 0 failed / 10 skipped**（从 Step 2B-1 进入时的 1883 累积 +67：1892 → 1907 → 1929 → 1950）
- **新增 / 更新的测试文件：**
  - `tests/test_run_predict_contract_alignment.py`（2B-1 新增 / 2B-2 更新）
  - `tests/test_primary_projection_contract_fields.py`（2B-2 新增）
  - `tests/test_peer_adjustment_contract_fields.py`（2B-3 新增）
  - `tests/test_final_projection_contract_fields.py`（2B-4 新增）
  - `tests/test_projection_output_adapter.py`（2B-3 / 2B-4 各新增 3 case：self-published 优先 / legacy fallback / 非法值回退）

## 3. 已字段化的 contract 段

### 3.1 §02 `avgo_primary_projection` — `build_primary_projection()` 自发布

| 字段 | 类型 | computed 分支来源 | 字段性质 |
|---|---|---|---|
| `primary_direction` | enum 偏多/偏空/中性 | `_direction_cn_from_bias(final_bias)` | **翻译字段** |
| `open_projection` | enum 高开/平开/低开 | `pred_open` 直传，缺失回退"平开" | **翻译字段** |
| `intraday_path_projection` | enum 高走/震荡/低走/V 型反转/倒 V | `pred_path` 内含"高走/走高" → 高走，类似 | **翻译字段** |
| `close_projection` | enum 收涨/收平/收跌 | `pred_close`（"平收" → "收平"） | **翻译字段** |
| `five_state_projection` | enum 大涨/小涨/震荡/小跌/大跌 | 偏多+收涨→小涨；偏空+收跌→小跌；其余震荡 | **保守推导**（不擅自给大涨/大跌） |
| `historical_sample_count` | int | `0` | **占位**（primary 故意排除历史匹配） |
| `key_evidence` | list[str] | `signals[:5]`（如 `"avgo_gap_state=gap_up"`） | **真实字段**（裁剪 5 条） |
| `primary_confidence_raw` | enum high/medium/low | `final_confidence` 直传 | **真实字段** |

unavailable 分支：所有字段填 contract-valid 默认值（中性 / 平开 / 震荡 / 收平 / 震荡 / 0 / [] / low）。

### 3.2 §03 `peer_confirmation_adjustment` — `apply_peer_adjustment()` 自发布

| 字段 | 类型 | 来源 | 字段性质 |
|---|---|---|---|
| `peer_symbols` | list[str] | `list(_PEER_SYMBOLS) = ["NVDA","SOXX","QQQ"]` | **真实字段**（已存在，未新增） |
| `nvda_signal` / `soxx_signal` / `qqq_signal` | enum reinforce/weaken/neutral/unknown | `adjustments[<peer>].vote` → `_VOTE_TO_PEER_SIGNAL`（**bias-aware**） | **翻译字段**（语义升级：相比 Step 1C adapter 的"方向无关"翻译，现在 confirm/oppose 是相对于 primary_bias 的） |
| `peer_alignment` | enum all_reinforce/mixed/all_weaken/insufficient | `_peer_alignment_from_counts(confirm_count, oppose_count)` | **翻译字段** |
| `peer_adjustment` | enum upgrade/hold/downgrade/flip_to_neutral | `_peer_adjustment_label_from_direction(adjustment_direction)` | **翻译字段** |
| `adjusted_direction` | enum 偏多/偏空/中性 | `_direction_cn_from_bias(adjusted_bias)` | **翻译字段** |
| `adjustment_reason` | str | 字面常量 `"Peer adjustment uses NVDA / SOXX / QQQ relative-strength confirmation."` | **占位文本**（与 `notes` 同口径） |

### 3.3 §06 `final_projection` — `build_final_projection()` 自发布

| 字段 | 类型 | computed 分支来源 | 字段性质 |
|---|---|---|---|
| `final_direction` | enum 偏多/偏空/中性 | `_direction_cn_from_bias(final_bias)` | **翻译字段** |
| `final_open_projection` | enum 高开/平开/低开 | `_pred_labels.pred_open` | **翻译字段** |
| `final_intraday_path` | enum 高走/震荡/低走/V 型反转/倒 V | `_pred_labels.pred_path` 经 `_intraday_path_from_pred_path` | **翻译字段** |
| `final_close_projection` | enum 收涨/收平/收跌 | `_pred_labels.pred_close`（"平收" → "收平"） | **翻译字段** |
| `final_five_state` | enum 大涨/小涨/震荡/小跌/大跌 | `_five_state_from(final_direction, final_close_projection)` | **保守推导** |
| `probability_bucket` | enum ≥70%/55–70%/45–55%/30–45%/≤30% | `_probability_bucket_from_confidence(final_confidence)`（high→≥70%, medium→55–70%, low→45–55%） | **翻译字段** |
| `key_price_levels` | dict | `{}` | **占位**（无稳定来源，不编造支撑阻力） |
| `final_one_sentence` | non-empty str | `prediction_summary`（与 `_summarize(final_bias, final_confidence, adjustment)` 同一对象引用） | **真实字段**（与 `prediction_summary` 一致） |

unavailable 分支：所有字段填 contract-valid 默认值（中性 / 平开 / 震荡 / 收平 / 震荡 / "45–55%" / {} / unavailable summary 字符串）。

## 4. adapter 当前优先级（02 / 03 / 06 三段统一策略）

`services/projection_output_adapter.py` 的 `_build_avgo_primary_projection` / `_build_peer_confirmation_adjustment` / `_build_final_projection` 三段使用同一套三级回退：

```
1. predict_result 子 dict 自带 contract 字段 + 取值在 contract 枚举内
   （含 list / dict / non-empty str 的 isinstance 校验）
       └─→ 直接采用（self-published fast path）
2. 子 dict 缺失字段（旧 payload，例如 _minimal_predict_result 测试 fixture）
       └─→ 回退到 Step 1C 旧推导（top-level legacy fields → 翻译表）
3. 字段存在但取值非法 / 类型错（脏数据，例如 "totally-bogus" / "not-a-dict"）
       └─→ 同 (2) fallback，不污染 contract 输出
```

**helpers：** `_take_enum(d, key, allowed)` 仅在值合法时返回，否则 `None`，让 `or` 链命中 fallback。

**对旧 payload 完全兼容：** `tests/test_projection_output_adapter.py` 共 59 个 case，包含 Step 1C 时期的所有断言（无 `final_projection` 子 dict 时仍走老推导）+ Step 2B-3 / 2B-4 各新增 3 case 锁三级优先级。

## 5. 没有改的东西

严格未触碰（Step 2B 全程）：

- ❌ `final_bias` 计算策略（仍由 `peer_adjustment.adjusted_bias` 退化路径决定）
- ❌ `peer_adjustment` 投票逻辑（`_peer_layer_vote` / `_combine_peer_votes` / 计数 / `adjustment_direction` 推导未改）
- ❌ `adjusted_bias` / `adjusted_confidence` 升降条件（`if confirm_count >= 2` / `if oppose_count >= 2 and primary_confidence == "low"`）
- ❌ `final_confidence` 计算（`peer.adjusted_confidence` 退化 + `_apply_research_adjustment` 路径）
- ❌ `_apply_research_adjustment` 的 research 升降逻辑
- ❌ `path_risk` / `peer_path_risk_adjustment` 推导
- ❌ `_summarize(...)` 文本格式
- ❌ `_PRIMARY_LOOKBACK_DAYS = 20` 取值（如要改回 15 是独立策略任务）
- ❌ `run_predict()` 主入口（签名 / 子步骤调用顺序 / `unavailable` 分支触发条件全部不变）
- ❌ UI（`ui/predict_tab.py` 等仍只读旧 top-level `predict_result` 字段）
- ❌ `services/prediction_store.py`（save 旁路 auto-gen 仍走 `adapt_projection_output(...)` → validator → `contract_payload_json`，路径不变）
- ❌ `services/projection_output_contract.py`（validator）
- ❌ Step 1 read-only 工具：`contract_payload_inspector` / `contract_payload_diff` / `contract_payload_trend` / `contract_outcome_correlation`
- ❌ `risk_model.py` / `contradiction_engine.py` / `confidence_engine.py` 三个 v1 stub 未接入主链
- ❌ scanner / matcher / 数据层
- ❌ 长桥 / 新闻 / 财报 数据接入
- ❌ stash / `.claude/worktrees/` / `logs/prediction_log.jsonl`

## 6. 当前仍是占位的 contract 段

| Section | 状态 | 当前由谁产出 | 解锁条件 |
|---|---|---|---|
| 04 `exclusion_system` | ❌ 全 stub | adapter 硬编码：`exclusion_level="none"` / 空 list / `forced_exclusion=False` / `anti_false_exclusion_triggered=False`（[adapter._build_exclusion_system](../services/projection_output_adapter.py)） | risk_model / contradiction_engine 稳定化 |
| 05 `confidence_system` | ❌ 多数 stub | adapter 硬编码：`historical_score / structure_score / peer_score / exclusion_penalty = 0.0` / `event_score = None`；只有 `confidence_level` 与 `total_confidence` 是真值（从 `final_confidence` 派生） | confidence_engine 稳定化 |
| 07 `simulated_trade` | ❌ 全 stub | adapter 硬编码：`trade_action="no_trade"` / `trade_direction="none"` / 空 entry/stop/take 字符串 / `suggested_position_size="0%"` / `no_trade_reason="adapter default: simulated trade decision not yet wired"` | 模拟交易决策层 |

**这三段不能算真正稳定。** 04 的 `forced_exclusion=False` / 05 的 `historical_score=0.0` / 07 的 `trade_action="no_trade"` 都是"validator 合规但语义为空"的占位，下游消费者不应据此做任何判断。

## 7. 下一步建议：Step 2C 路线

> 强烈建议**只做诊断，不要直接重构所有否定系统**。

### 7.1 推荐的最小子步划分

| 子步 | 范围 | 风险 |
|---|---|---|
| **2C-1** | 只读诊断：grep `risk_model.py` / `contradiction_engine.py` 在主链的所有调用点、当前数据流；列出 `predict_result` 里已有哪些 exclusion / reliability / contradiction 相关字段；确认这些字段与 contract 04 段的距离 | 极低，纯读 + 诊断报告，不改代码 |
| **2C-2** | contract alignment 安全网（如 Step 2B-1 模式）：写"如果 04 段还是 stub 必须显式标记"的回归测试；同时给 04 段引入 `extras` 子字段，把现有 risk_model 输出（如果 `predict_result` 里已有）镜像进去，**不改 contract 必填字段** | 低，只加测试 + adapter 微调 |
| **2C-3** | 让 `build_final_projection`（或独立 `build_exclusion_section()`）self-publish 04 段——**仅当 risk_model / contradiction_engine 数据真实可用时**；否则保持当前 stub 不变 | 中，需要先确认 v1 stub 是否真值 |

### 7.2 严守边界

进入 Step 2C 时仍要严守 Step 2B 全程的边界：
- ❌ 不要直接接 `risk_model.py` / `contradiction_engine.py` / `confidence_engine.py` 三个 v1 stub。先确认它们的真实输出语义，再决定怎么映射进 contract。
- ❌ 不要把 contract 04 / 05 段的占位字段静默"激活"——validator 全绿不代表语义有效。
- ❌ 不要改 `run_predict` 主入口的签名 / 子步骤顺序。如果需要新增否定层，应当作为新 builder 函数挂在 `build_final_projection` 之前或之后，类似 Step 2B-3 的字段化模式。
- ❌ 不要改 UI / `prediction_store` / Step 1 read-only 工具。

### 7.3 可选 / 旁路任务

如果你想在进入 Step 2C 之前先收一个小尾巴：
- 把 `tests/test_predict.py` 里的 `_scan()` / `_recent_rows()` 抽到共用 fixture 文件，让 Step 2B-2/3/4 的三个 contract field 测试不再各自维护一份"近 20 天 bullish 行情"
- 用 Step 1 的 `contract_payload_trend.py` 工具实跑一次 main，看 02 / 03 / 06 三段在 prediction_log 里的真实分布——把这个作为 Step 2C 诊断的输入
