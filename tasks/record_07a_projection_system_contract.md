# 07A记录：推演系统 Contract

> 本记录是三系统 contract 序列中的第 1 份，对应 06记录"三系统独立原则"中的
> 第 1 步（固定推演系统 contract）。
>
> 本轮只写文档：不改代码、不写 DB、不运行 validation、不 commit / push、
> 不做系统体检、不进入 3R-5 / 3R-6。

---

## 1. 背景

06记录已经把"三系统独立原则"固定为项目层面的契约：

- 推演系统、否定系统、置信度系统是**三个独立系统**，互相不读取、不改写。
- 最终报告**只 aggregate，不 mutate**。
- 任意一系统的输出**不得回流**到另一系统的输入。

06记录定义了三系统各自要回答的问题，但**没有展开**任何一个系统自己的契约。
07A 序列的目的，是逐个把三系统 + 最终报告 aggregator 各自的边界写死：

- 07A：推演系统 contract（本记录）
- 07B：否定系统 contract（待写）
- 07C：置信度系统 contract（待写）
- 07D：final report aggregator contract（待写）

本记录**只**固定推演系统的边界。
推演系统不是否定系统，也不是置信度系统。
推演系统只回答一个问题：**明天最可能发生什么？**

> 注：本文件定义"推演系统"作为一个**逻辑系统**的契约，不是任何具体模块的
> 实现规范。它不预设 `predict.py` / `services/projection_*.py` 之中哪些
> 模块属于推演系统范畴 —— 这一判断留到四个 contract 全部完成后的系统体检。

---

## 2. 推演系统的核心问题

推演系统回答的问题是：

> **"在当前市场结构下，明天最可能发生什么？"**

它**不**回答以下问题（这些属于其他系统或不属于本项目）：

- 明天最不可能发生什么 → 否定系统
- 这次判断有多可信 → 置信度系统
- 是否应该否定某个状态 → 否定系统
- 是否应该交易（buy / sell / hold / no_trade）→ 不属于推演系统
- 是否应该 hard / forced 决策 → 不属于推演系统
- 是否进入 3R-5 / 3R-6 → 与 contract 无关，是路线决策

推演系统**只**对"最可能"这一个问题负责。任何让它回答其他问题的设计，
默认违反本 contract，应被 reject 或重定向到对应系统。

---

## 3. 推演系统允许读取的输入

### 3.1 允许读取（白名单）

- AVGO 自身行情数据（OHLCV）
- 近 15 个交易日结构（结构窗口长度由实现决定，但**只能**来自 AVGO 自身）
- 五状态历史样本（大涨 / 小涨 / 震荡 / 小跌 / 大跌）
- 历史相似结构（基于自身数据计算的相似度，不依赖任何系统输出）
- NVDA / SOXX / QQQ 同行与市场确认（peer 信号）
- 成交量 / 成交额 / 位置 / 趋势 / 反转结构
- 已定义的市场 regime / 标签
- 公开市场数据
- 已有本地数据（前提：来自市场数据，不来自其他系统输出）

### 3.2 禁止读取（黑名单）

以下输入**不允许**进入推演系统：

- 否定系统输出（任何 `exclusion_*` 字段）
- exclusion_result（否定结论 / 否定状态 / 否定理由 / 否定强度）
- confidence_result（置信度系统的任何字段）
- final_report 结果（最终报告的任何 aggregate 输出）
- hard / forced decision（hard exclusion / forced exclusion / required decision）
- future data（目标日及之后的真实数据）
- 2026 final-test range（保留给最终验证用的窗口）

### 3.3 输入边界判定原则

- **数据来源是市场数据 → 允许**（自然包括 AVGO / peer / regime）。
- **数据来源是其他系统输出 → 禁止**（即使该系统也基于市场数据）。
- **数据来源是未来 → 禁止**（包含目标日及以后的真实结果）。
- 模糊地带（例如"基于推演自己历史输出训练的模型"）默认禁止，
  除非显式更新本 contract。

---

## 4. 推演系统必须输出什么

推演系统的输出必须**至少**包含以下方向的字段。具体字段命名以
§9 contract 草案为准；本节描述含义和必填语义。

| 字段方向 | 含义 |
|---|---|
| `projection_date` | 本次推演运行所基于的数据截止日 |
| `target_date` | 本次推演要预测的目标交易日 |
| `most_likely_state` | 五状态中"最可能发生"的那一个 |
| `ranked_states` | 五状态完整排序（最可能 → 最不可能，**仅基于推演视角**） |
| `state_probabilities_or_scores` | 五状态的概率或得分（任一形式，但必须可序列化） |
| `primary_reasoning` | 驱动 most_likely 的核心理由列表（中文，结构化短句） |
| `avgo_structure_summary` | AVGO 自身结构摘要（位置 / 趋势 / 量能 / 标签） |
| `peer_confirmation_summary` | NVDA / SOXX / QQQ 同行确认摘要 |
| `key_supporting_signals` | 支持 most_likely 的关键证据 |
| `key_risk_signals` | 推演自身识别的风险信号（**注意**：是推演系统自己的风险，不是否定系统的否定） |
| `uncertainty_notes` | 推演系统自评的不确定性描述（不是 confidence_score） |
| `raw_evidence_refs` | 指向原始证据数据的引用（如成交量序列、相似样本 id 等） |

五状态必须保持以下五个，命名固定不可改：

- 大涨
- 小涨
- 震荡
- 小跌
- 大跌

> **关于 "key_risk_signals" / "uncertainty_notes" 的边界澄清**：
> 推演系统可以**自我标注风险与不确定性**（即"我自己也觉得这次不太稳"），
> 但**不能**输出可信度分值，也**不能**给自己打 confidence_level。
> 自评的风险与不确定性属于推演系统的"原始信号"；
> 量化为可信度是置信度系统的职责。

---

## 5. 推演系统不能输出什么

以下字段**不允许**出现在推演系统输出里：

- `most_unlikely_state`（属于否定系统）
- `exclusion_decision`
- `exclusion_reason`
- `exclusion_strength`
- 任何 `exclusion_*` 字段
- `confidence_score`
- `confidence_level`
- `final_confidence`
- `hard_exclusion`
- `forced_exclusion`
- `required_decision`
- `trading_action`
- `buy` / `sell` / `hold`
- `simulated_trade`
- `no_trade`
- `final_report_mutation`（推演系统不写最终报告）
- 任何修改否定系统字段的输出
- 任何修改置信度系统字段的输出
- 任何写入 final report 顶级聚合字段的输出

> 区分要点：推演系统的 `ranked_states` 是**推演视角**下的排序，
> 不是"经过否定系统校验后的排序"。推演系统**自己**认为某个状态最不可能
> 是允许的，但不能将该判断标记为 `exclusion_*` 字段或与否定系统结果对齐。
> 否定系统的"最不可能"是另一个独立判断，不受此排序影响。

---

## 6. 推演系统和否定系统的边界

- 推演系统**不读取**否定系统结果。
- 推演系统**不**根据否定结果修改 `most_likely_state` 或 `ranked_states`。
- 否定系统的"最不可能"**不能反向改写**推演系统输出。
- 推演系统的 `ranked_states[-1]`（推演视角下"最不可能"）与
  否定系统的 `most_unlikely_state`**可以不同**，且不需要保持一致。
- 二者可以在 final report 中**并列展示**。
- 如果二者冲突，由置信度系统**评价**冲突（例如标注一致性 / 冲突程度），
  **不**由推演系统自我修正。
- 任何在推演系统内部"先看一眼否定再调整"的设计，违反 contract。

---

## 7. 推演系统和置信度系统的边界

- 推演系统**不读取**置信度系统结果。
- 置信度低**不改变**推演系统原始输出（`most_likely_state` 不会因为
  置信度系统打了低分就被换掉）。
- 置信度系统可以**评价**推演系统输出，但**不能修改**推演系统输出。
- 推演系统**不输出** `confidence_score` / `confidence_level` / `total_confidence`。
- 推演系统**可以**在 `uncertainty_notes` 中写自评不确定性短语
  （例如"样本量小"、"结构罕见"），但**不得**量化为可信度分值。
- 如果需要展示可信度，**交给置信度系统**。

---

## 8. 推演系统和 final report 的边界

- final report **可以读取**并**展示**推演系统输出。
- final report **不得改写**推演系统输出。
- final report **可以标注**"与否定系统冲突" / "推演与否定不一致"。
- final report **可以引用**置信度系统对推演的评价。
- final report **不得**把综合判断回写到 projection_result（比如把
  `final_direction` 写回推演系统的 `most_likely_state`）。
- final report 写入的是**它自己**的聚合字段，例如 `combined_view` /
  `aggregate_summary`，与推演输出**并列**而非**覆盖**。

---

## 9. projection_result contract 草案

> 本草案仅作为 contract 设计，不要求本轮代码实现。字段名采用 `snake_case`。
> 数值字段允许为 float 或 int；缺失语义用 `null`，不得用 `0` / `""` 假装存在。
> 五状态命名固定为 `["大涨", "小涨", "震荡", "小跌", "大跌"]`。

```jsonc
{
  "schema_version": "projection_system_result.v1",

  "projection_date": "<YYYY-MM-DD>",      // 数据截止日
  "target_date": "<YYYY-MM-DD>",          // 目标交易日

  "system_name": "projection_system",
  "question_answered": "most_likely_state",

  "most_likely_state": "小涨",
  "ranked_states": ["小涨", "震荡", "大涨", "小跌", "大跌"],
  "state_scores": {
    "大涨": "<0.0–1.0>",
    "小涨": "<0.0–1.0>",
    "震荡": "<0.0–1.0>",
    "小跌": "<0.0–1.0>",
    "大跌": "<0.0–1.0>"
  },

  "primary_reasoning": [
    "近 15 日量能持续放大",
    "突破前高 N 天后未回踩",
    "MA20 / MA60 多头排列"
  ],

  "avgo_structure_summary": {
    "structure_label": "整理",
    "price_position_15d": "<0.0–1.0>",
    "trend_label": "<偏多 / 偏空 / 中性>",
    "volume_label": "<放量 / 缩量 / 平稳>",
    "short_summary": "收盘 <price>，处于 15 日 <pct> 位，结构 整理"
  },

  "peer_confirmation_summary": {
    "peer_symbols": ["NVDA", "SOXX", "QQQ"],
    "nvda_signal": "<reinforce / weaken / neutral / unknown>",
    "soxx_signal": "<reinforce / weaken / neutral / unknown>",
    "qqq_signal": "<reinforce / weaken / neutral / unknown>",
    "peer_alignment": "<all_reinforce / mixed / all_weaken / insufficient>",
    "summary": "NVDA + QQQ 同向支持，SOXX 中性"
  },

  "key_supporting_signals": [
    "成交量较 5 日均量放大 28%",
    "突破 <resistance> 后第 2 日未回踩"
  ],

  "key_risk_signals": [
    "5 日 RSI 已进入超买区",
    "板块龙头 NVDA 出现量价背离"
  ],

  "uncertainty_notes": [
    "相似历史样本数 < 12，统计稳定性偏弱",
    "近期处于财报窗口，事件驱动不可控"
  ],

  "raw_evidence_refs": [
    "ohlcv:AVGO:<projection_date>:window=15",
    "similar_pattern:hash=<...>",
    "peer_panel:<projection_date>"
  ]
}
```

> 上述草案**不**包含任何 `confidence_*` / `exclusion_*` /
> `final_*` / `simulated_trade` 字段。这些字段属于其他系统的 contract，
> 不在 projection_result 中出现。

---

## 10. 禁止数据流

以下数据流在推演系统中**严格禁止**（任意方向只要触发其一即视为违反）：

| 禁止数据流 | 含义 |
|---|---|
| `exclusion_result → projection_system` | 否定结果不得作为推演输入 |
| `confidence_result → projection_system` | 置信度结果不得作为推演输入 |
| `final_report → projection_system` | 最终报告聚合结果不得回流到推演 |
| `hard / forced decision → projection_system` | 任何强制决策不得回流到推演 |
| `trading_result → projection_system` | 模拟交易 / 真实交易结果不得回流到推演 |
| `future outcome → projection_system` | 目标日真实结果不得回流到推演（任何对齐 / 修正 / 调参都不行） |

任何 PR / candidate / 重构若引入以上任一数据流，违反 contract，默认 reject。

---

## 11. 与现有系统的关系

本节**只做原则性描述**，不做完整体检：

- 现有 `predict.py` / `services/projection_*.py` / `services/main_projection_layer.py`
  / `services/primary_20day_analysis.py` / `services/peer_adjustment.py` /
  `services/historical_probability.py` / `services/projection_orchestrator*.py`
  / `services/projection_entrypoint.py` 等模块，**未来需要依据本 contract 审查**。
- 本轮**不**判断每个模块归属（哪些属于推演系统、哪些属于其他系统）。
- 本轮**不**判断现有 `predict_result` / `projection_v2_raw` /
  `projection_three_systems` 等输出与本 contract 的对齐情况。
- 完整体检**留到 07A / 07B / 07C / 07D 全部完成之后**统一进行。

> 现有 step_1a 文档定义的"8 个顶级 section"是 `run_predict` 的输出 contract，
> 与本 contract 的范围**不同**：step_1a 是收口层 contract，包含推演 / 否定 /
> 置信度 / 最终 / 模拟交易 / 复盘；本 contract 只关注其中"推演系统"那一段。
> 二者关系将在 07D（final report aggregator contract）中统一对齐。

---

## 12. 后续开发原则

- 下一步固定 **07B 否定系统 contract**。
- 之后固定 **07C 置信度系统 contract**。
- 之后固定 **07D final report aggregator contract**。
- 四个 contract 都完成后，**才做系统体检**。
- 在四个 contract 全部完成之前：
  - 不进入 3R-5 / 3R-6
  - 不新增否定 candidate
  - 不新增置信度 candidate
  - 不复活 continuous_smoothing 作为否定 candidate
  - 任何"推演 candidate"如有新增，必须先核对是否符合本 contract

---

## 13. 严守边界

本文件**只是 contract 文档**：

- 未改代码
- 未新增测试
- 未写 DB
- 未改 DB schema
- 未跑 replay
- 未跑 validation
- 未做系统体检
- 未进入 3R-5 / 3R-6
- 未新增任何 candidate
- 未复活 continuous_smoothing

本 contract 的修改路径：任何对推演系统输入 / 输出 / 边界 / 数据流的调整，
都必须以**显式更新本文件**的方式提出，并同步检查是否影响 07B / 07C / 07D。
