# 07B记录：否定系统 Contract

> 本记录是三系统 contract 序列中的第 2 份，对应 06记录"三系统独立原则"中的
> 第 2 步（固定否定系统 contract）。
>
> 本轮只写文档：不改代码、不写 DB、不运行 validation、不 commit / push、
> 不做系统体检、不进入 3R-5 / 3R-6、不新增任何否定 candidate、
> 不复活 continuous_smoothing。

---

## 1. 背景

06记录已经把"三系统独立原则"固定为项目层面的契约：

- 推演 / 否定 / 置信度三系统**互相独立**，不读取、不改写。
- 最终报告**只 aggregate，不 mutate**。
- 任意系统的输出**不得回流**到另一系统的输入。

07A 已经把推演系统 contract 固定下来。
本记录（07B）**只**固定否定系统的边界：

- 否定系统**不是**推演系统的附属层。
- 否定系统**不是**"看推演结果再否定推演"的审查员。
- 否定系统**只**回答一个问题：**明天最不可能发生什么？**

否定系统对自己负责，对"最不可能"这件事负责，仅此而已。

> 注：本文件定义"否定系统"作为一个**逻辑系统**的契约，不预设
> `services/exclusion_layer.py` / `services/anti_false_exclusion_*` /
> `services/big_up_contradiction_card.py` / `services/continuous_smoothing_candidate*.py`
> 等具体模块的归属。模块层面的归属判断留到四个 contract 全部完成后的系统体检。

---

## 2. 否定系统的核心问题

否定系统回答的问题是：

> **"在当前市场结构下，明天最不可能发生什么？"**

它**不**回答以下问题：

- 明天最可能发生什么 → 推演系统
- 推演系统是否正确 → 不属于任何子系统的职责
- 是否应该修改推演结果 → **禁止**（违反三系统独立）
- 这次判断有多可信 → 置信度系统
- 是否应该交易（buy / sell / hold / no_trade）→ 不属于否定系统
- 是否应该 hard / forced → 不属于否定系统
- 是否进入 3R-5 / 3R-6 → 与 contract 无关，是路线决策

否定系统**只**对"最不可能"这一个问题负责。任何让它回答其他问题的设计，
默认违反本 contract，应被 reject 或重定向到对应系统。

> **重要语义澄清**：
> 否定系统回答"明天最不可能发生什么"，输入是市场数据 / 历史分布 / 状态稀有性 /
> peer 非确认结构。它的合法性来自**独立判断"最不可能"**的能力，而**不是**
> "能不能反向校验推演"。任何用"它能不能反向校验推演"作为否定 candidate
> 合格标准的设计，违反 06记录第 7 节，违反 07B contract，默认 reject。

---

## 3. 否定系统允许读取的输入

### 3.1 允许读取（白名单）

- AVGO 自身行情数据（OHLCV）
- 近 15 个交易日结构（窗口长度由实现决定，但**只能**来自 AVGO 自身）
- 五状态历史样本（大涨 / 小涨 / 震荡 / 小跌 / 大跌）
- 历史相似结构中**最少发生**的状态（基于自身数据计算的稀有性）
- 极端状态历史发生频率
- NVDA / SOXX / QQQ 同行与市场结构（peer 非确认信号）
- 成交量 / 成交额 / 位置 / 趋势 / 反转结构
- 已定义的市场 regime / 标签
- 历史失败结构
- 历史 rare-event pattern
- 公开市场数据
- 已有本地数据（前提：来自市场数据，不来自其他系统输出）

### 3.2 禁止读取（黑名单）

以下输入**不允许**进入否定系统：

- 推演系统输出（任何 `projection_*` 字段）
- `projection_result`
- `most_likely_state`
- 推演系统的 `ranked_states`
- 推演系统的 `state_scores`
- `confidence_result`（置信度系统的任何字段）
- `final_report` 结果（最终报告的任何 aggregate 输出）
- hard / forced decision（hard exclusion / forced exclusion / required decision）
- future data（目标日及之后的真实数据）
- 2026 final-test range（保留给最终验证用的窗口）

### 3.3 输入边界判定原则

- **市场数据 / 历史分布 / 状态稀有性 → 允许**（自然包括 AVGO / peer / regime / rare-event）。
- **其他系统输出 → 禁止**（即使该系统也基于市场数据）。
- **未来数据 → 禁止**（包含目标日及以后的真实结果）。
- 模糊地带（例如"基于否定系统自己历史输出训练的模型"）默认禁止，
  除非显式更新本 contract。

---

## 4. 否定系统必须输出什么

否定系统的输出必须**至少**包含以下方向的字段。具体字段命名以
§9 contract 草案为准；本节描述含义和必填语义。

| 字段方向 | 含义 |
|---|---|
| `exclusion_date` | 本次否定运行所基于的数据截止日 |
| `target_date` | 本次否定要预测的目标交易日 |
| `system_name` | 固定 `"exclusion_system"` |
| `question_answered` | 固定 `"most_unlikely_state"` |
| `most_unlikely_state` | 五状态中"最不可能发生"的那一个 |
| `ranked_unlikely_states` | 五状态完整排序（最不可能 → 最可能，**仅基于否定视角**） |
| `state_impossibility_scores` | 五状态的"不可能性"分值或 score（任一形式，但必须可序列化） |
| `primary_exclusion_reasoning` | 驱动 most_unlikely 的核心理由列表（中文，结构化短句） |
| `rare_event_evidence` | 该状态在历史相似结构中的稀有性证据 |
| `historical_non_occurrence_summary` | 历史结构下该状态的"未发生 / 极少发生"摘要 |
| `peer_non_confirmation_summary` | NVDA / SOXX / QQQ 同行**非确认**摘要（peer 不支撑该状态） |
| `key_exclusion_signals` | 支持 most_unlikely 的关键证据 |
| `key_counter_signals` | 否定系统自身识别的反向信号（**注意**：是否定系统自评的"我也可能错"，不是推演结果） |
| `uncertainty_notes` | 否定系统自评的不确定性描述（不是 confidence_score） |
| `raw_evidence_refs` | 指向原始证据数据的引用（如稀有样本 id、分布统计 id 等） |

五状态必须保持以下五个，命名固定不可改：

- 大涨
- 小涨
- 震荡
- 小跌
- 大跌

> **关于 "key_counter_signals" / "uncertainty_notes" 的边界澄清**：
> 否定系统可以**自我标注反向信号与不确定性**（即"我自己也觉得这次否定不太稳"），
> 但**不能**输出可信度分值，也**不能**给自己打 confidence_level。
> 自评的反向信号与不确定性属于否定系统的"原始信号"；
> 量化为可信度是置信度系统的职责。

---

## 5. 否定系统不能输出什么

以下字段**不允许**出现在否定系统输出里：

- `most_likely_state`（属于推演系统）
- `projection_decision`
- `projection_correction`
- `modified_projection`
- 任何 `projection_*` mutation 字段
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
- `final_report_mutation`（否定系统不写最终报告）
- 任何修改推演系统字段的输出
- 任何修改置信度系统字段的输出
- 任何写入 final report 顶级聚合字段的输出

> 区分要点：否定系统的 `ranked_unlikely_states[0]` 是**否定视角**下"最不可能"。
> 它**不**等于推演系统的 `ranked_states[-1]`，二者**可以不同且不需要保持一致**。
> 否定系统**不能**因为推演系统排序如何而调整自己的判断 —— 它根本不应该**看到**
> 推演系统的输出。

---

## 6. 否定系统和推演系统的边界

- 否定系统**不读取**推演系统结果。
- 否定系统**不是**"推演结果的审查员"。
- 否定系统**不**根据 `most_likely_state` 决定 `most_unlikely_state`。
- 推演系统的 `ranked_states[-1]` 与否定系统的 `most_unlikely_state` **可以不同**，
  且**不需要保持一致**。
- 两者**可以冲突**，这是合法的、被预期的。
- 冲突由**置信度系统评价**（标注一致性 / 冲突程度）。
- final report 中**并列展示**，不允许任何一方覆盖另一方。

### 举例

| 场景 | 推演系统 | 否定系统 | 处理方式 |
|---|---|---|---|
| 一致 | 最可能：大涨 | 最不可能：大跌 | 二者方向同、无冲突 |
| 部分冲突 | 最可能：小涨 | 最不可能：小涨 | **冲突**：交置信度系统评价，二者输出都保留，final report 并列展示并标注冲突 |
| 强冲突 | 最可能：大涨 | 最不可能：大涨 | **强冲突**：二者输出都保留，final report 标注"推演与否定方向直接冲突"，置信度系统给出冲突程度评价 |

> **冲突不是 bug，是契约下的合法状态**。强冲突时**不**修改任一方输出。
> 任何"看到强冲突就改写其中一方"的设计，违反 contract，默认 reject。

---

## 7. 否定系统和置信度系统的边界

- 否定系统**不读取**置信度系统结果。
- 置信度低**不改变**否定系统原始输出（`most_unlikely_state` 不会因为置信度
  系统打了低分就被换掉）。
- 置信度系统可以**评价**否定系统输出，但**不能修改**否定系统输出。
- 否定系统**不输出** `confidence_score` / `confidence_level` /
  `total_confidence`。
- 否定系统**可以**在 `uncertainty_notes` 中写自评不确定性短语
  （例如"稀有样本数 < 5"、"近期 regime 漂移"），但**不得**量化为可信度分值。
- 如果需要展示可信度，**交给置信度系统**。

---

## 8. 否定系统和 final report 的边界

- final report **可以读取**并**展示**否定系统输出。
- final report **不得改写**否定系统输出。
- final report **可以标注**"与推演系统冲突" / "推演与否定不一致"。
- final report **可以引用**置信度系统对否定的评价。
- final report **不得**把综合判断回写到 `exclusion_result`（比如把
  `final_unlikely_state` 写回否定系统的 `most_unlikely_state`）。
- final report 写入的是**它自己**的聚合字段，与否定输出**并列**而非**覆盖**。

---

## 9. exclusion_result contract 草案

> 本草案仅作为 contract 设计，不要求本轮代码实现。字段名采用 `snake_case`。
> 数值字段允许为 float 或 int；缺失语义用 `null`，不得用 `0` / `""` 假装存在。
> 五状态命名固定为 `["大涨", "小涨", "震荡", "小跌", "大跌"]`。

```jsonc
{
  "schema_version": "exclusion_system_result.v1",

  "exclusion_date": "<YYYY-MM-DD>",       // 数据截止日
  "target_date": "<YYYY-MM-DD>",          // 目标交易日

  "system_name": "exclusion_system",
  "question_answered": "most_unlikely_state",

  "most_unlikely_state": "大跌",
  "ranked_unlikely_states": ["大跌", "小跌", "震荡", "大涨", "小涨"],
  "state_impossibility_scores": {
    "大涨": "<0.0–1.0>",
    "小涨": "<0.0–1.0>",
    "震荡": "<0.0–1.0>",
    "小跌": "<0.0–1.0>",
    "大跌": "<0.0–1.0>"
  },

  "primary_exclusion_reasoning": [
    "近 15 日相似结构中无 5%+ 跌幅样本",
    "成交量持续放大，与大跌结构特征不符",
    "板块龙头未出现量价背离，未现风险释放"
  ],

  "rare_event_evidence": [
    "相似结构样本 N=42，大跌发生率 = 0%",
    "近 60 日 regime 内大跌从未出现"
  ],

  "historical_non_occurrence_summary": {
    "regime_label": "<偏多 / 偏空 / 中性 / ...>",
    "samples_in_regime": "<int>",
    "non_occurrence_rate": "<0.0–1.0>",
    "summary": "在当前 regime 下，大跌历史发生率极低"
  },

  "peer_non_confirmation_summary": {
    "peer_symbols": ["NVDA", "SOXX", "QQQ"],
    "nvda_non_confirm": "<true / false / unknown>",
    "soxx_non_confirm": "<true / false / unknown>",
    "qqq_non_confirm": "<true / false / unknown>",
    "summary": "NVDA / SOXX / QQQ 均未释放大跌信号"
  },

  "key_exclusion_signals": [
    "5 日 RSI 仍处中性区，无超买回落迹象",
    "成交量 5 日均量较 20 日均量放大 18%"
  ],

  "key_counter_signals": [
    "宏观事件窗口（FOMC 前 1 日），事件驱动不可控",
    "板块短期估值已偏高，存在情绪反转风险"
  ],

  "uncertainty_notes": [
    "稀有样本数 < 5，统计稳定性偏弱",
    "近期 regime 漂移迹象，历史分布参考价值下降"
  ],

  "raw_evidence_refs": [
    "rare_pattern:hash=<...>",
    "regime_distribution:<exclusion_date>",
    "peer_panel:<exclusion_date>"
  ]
}
```

> 上述草案**不**包含任何 `confidence_*` / `projection_*` /
> `final_*` / `simulated_trade` / `hard_exclusion` / `forced_exclusion`
> 字段。这些字段属于其他系统的 contract，不在 exclusion_result 中出现。

---

## 10. 禁止数据流

以下数据流在否定系统中**严格禁止**（任意方向只要触发其一即视为违反）：

| 禁止数据流 | 含义 |
|---|---|
| `projection_result → exclusion_system` | 推演结果不得作为否定输入 |
| `most_likely_state → exclusion_system` | 推演选出的"最可能"不得作为否定输入 |
| `confidence_result → exclusion_system` | 置信度结果不得作为否定输入 |
| `final_report → exclusion_system` | 最终报告聚合结果不得回流到否定 |
| `hard / forced decision → exclusion_system` | 任何强制决策不得回流到否定 |
| `trading_result → exclusion_system` | 模拟交易 / 真实交易结果不得回流到否定 |
| `future outcome → exclusion_system` | 目标日真实结果不得回流到否定（任何对齐 / 修正 / 调参都不行） |

任何 PR / candidate / 重构若引入以上任一数据流，违反 contract，默认 reject。

---

## 11. 与 continuous_smoothing 的关系

continuous_smoothing v1 / v2 已经 abandon as candidate layer（见 3R-3.3H 决策）。

**定性**：

- continuous_smoothing **不属于** active exclusion system。
- 它的状态是 **FROZEN_DIAGNOSTIC**：
  - 不再作为"否定推演结果"的 candidate。
  - 不再作为否定系统的 input layer。
  - 不再作为否定系统的 candidate score 来源。
- 其 candidate-layer 失败的本质是：作为否定 candidate 评估时，
  无法独立判断"最不可能"，行为本质上仍依赖"看推演结果再做平滑"，
  这正是 06记录第 7 节明确禁止的模式。

**未来重用规则**：

- continuous_smoothing **不能**再以"否定 candidate"身份回归。
- 如果未来要复用其平滑思路，**只能**作为以下角色独立设计：
  - review layer（事后回看）
  - explanation layer（解释推演 / 否定输出）
  - diagnostic layer（诊断哪一个系统这次出了问题）
- 任何"continuous_smoothing 作为 active exclusion candidate"的复活提案，
  在不更新本记录与 06记录的前提下，默认 reject。

---

## 12. 与现有系统的关系

本节**只做原则性描述**，不做完整体检：

- 现有 `services/exclusion_layer.py` / `services/anti_false_exclusion_audit.py` /
  `services/anti_false_exclusion_dashboard.py` /
  `services/big_up_contradiction_card.py` /
  `services/exclusion_reliability_review.py` /
  `services/continuous_smoothing_candidate.py` /
  `services/continuous_smoothing_candidate_v2.py` 等模块，
  **未来需要依据本 contract 审查**。
- 本轮**不**判断每个模块归属（哪些属于否定系统、哪些属于诊断 / 解释层、
  哪些应进入 FROZEN_DIAGNOSTIC）。
- 本轮**不**判断现有 `exclusion_result` / `anti_false_exclusion_*` 等输出
  与本 contract 的对齐情况。
- 完整体检**留到 07A / 07B / 07C / 07D 全部完成之后**统一进行。

> 现有 step_1a 文档定义的 `exclusion_system` section 是 `run_predict` 收口层
> 的 contract 中的一段，与本 contract 的范围**不同**：step_1a 是收口层
> contract；本 contract 只关注作为独立逻辑系统的"否定系统"自身边界。
> 二者关系将在 07D（final report aggregator contract）中统一对齐。

---

## 13. 后续开发原则

- 下一步固定 **07C 置信度系统 contract**。
- 之后固定 **07D final report aggregator contract**。
- 四个 contract 都完成后，**才做系统体检**。
- 在四个 contract 全部完成之前：
  - 不进入 3R-5 / 3R-6
  - **不新增否定 candidate**
  - 不新增置信度 candidate
  - **不复活 continuous_smoothing 作为否定 candidate**
  - 任何"否定 candidate"如有提案，必须先核对是否符合本 contract
    （包括 §3 输入白/黑名单、§5 禁止输出、§10 禁止数据流、
     §6 与推演系统的独立关系）

---

## 14. 严守边界

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

本 contract 的修改路径：任何对否定系统输入 / 输出 / 边界 / 数据流的调整，
都必须以**显式更新本文件**的方式提出，并同步检查是否影响 06记录、07A、
07C、07D。
