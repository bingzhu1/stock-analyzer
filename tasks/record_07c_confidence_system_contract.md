# 07C记录：置信度系统 Contract

> 本记录是三系统 contract 序列中的第 3 份，对应 06记录"三系统独立原则"中的
> 第 3 步（固定置信度系统 contract）。
>
> 本轮只写文档：不改代码、不写 DB、不运行 validation、不 commit / push、
> 不做系统体检、不进入 3R-5 / 3R-6、不新增任何置信度 candidate、
> 不复活 continuous_smoothing。

---

## 1. 背景

06记录已经把"三系统独立原则"固定为项目层面的契约：

- 推演 / 否定 / 置信度三系统**互相独立**，不读取（推演不读否定）、不改写。
- 最终报告**只 aggregate，不 mutate**。
- 任意系统的输出**不得回流**到另一系统的输入。

07A 已经把推演系统 contract 固定下来。
07B 已经把否定系统 contract 固定下来。
本记录（07C）**只**固定置信度系统的边界：

- 置信度系统**不是**推演系统，也**不是**否定系统。
- 置信度系统**不**生成"最可能 / 最不可能"的判断，**只评价**两个系统各自的可信度。
- 置信度系统**只**回答一个问题：
  **"推演系统和否定系统各自这次判断有多可信？"**

置信度系统对自己负责，对"二者各自可信度"负责，仅此而已。

> 注：本文件定义"置信度系统"作为一个**逻辑系统**的契约，不预设
> `confidence_engine.py` / `services/contract_calibration_inputs.py` /
> `services/active_rule_pool_calibration.py` /
> `services/exclusion_reliability_review.py` 等具体模块的归属。
> 模块层面的归属判断留到四个 contract 全部完成后的系统体检。

---

## 2. 置信度系统的核心问题

置信度系统回答的问题是：

> **"推演系统这次判断有多可信？"**
> **"否定系统这次判断有多可信？"**
> **"二者之间是一致、部分冲突，还是强冲突？"**
> **"最终展示时应该如何标注可信度和冲突？"**

它**不**回答以下问题：

- 明天最可能发生什么 → 推演系统
- 明天最不可能发生什么 → 否定系统
- 是否应该修改推演结果 → **禁止**（违反三系统独立）
- 是否应该修改否定结果 → **禁止**（违反三系统独立）
- 是否应该交易（buy / sell / hold / no_trade）→ 不属于置信度系统
- 是否应该 hard / forced → 不属于置信度系统
- 是否进入 3R-5 / 3R-6 → 与 contract 无关，是路线决策

置信度系统**只**对"二者各自可信度 + 二者一致性 / 冲突程度"负责。任何让它
回答"最终结论是什么"的设计，默认违反本 contract，应被 reject 或重定向到
final report aggregator（07D 待定）。

> **重要语义澄清**：
> 置信度系统是**评价者**，不是**仲裁者**。
> 评价：描述"谁这次更可信"。
> 仲裁：决定"谁对谁错 / 用谁覆盖谁"。
> 置信度系统**只能评价**，**禁止仲裁**。低置信度不会触发"自动改写"，
> 高置信度也不会触发"自动 hard / forced"。

---

## 3. 置信度系统允许读取的输入

### 3.1 允许读取（白名单）

- 原始市场数据（OHLCV）
- AVGO 自身行情
- NVDA / SOXX / QQQ 同行与市场数据
- 历史五状态表现（大涨 / 小涨 / 震荡 / 小跌 / 大跌的历史频率与样本量）
- 历史**推演准确率**（推演 most_likely 命中率随结构 / regime 的分布）
- 历史**否定准确率**（否定 most_unlikely 命中率随结构 / regime 的分布）
- 历史 false_exclusion / survival_case 表现
- 历史样本数量（样本稀释 / 稳定性参考）
- 当前 `projection_result`（**只读**）
- 当前 `exclusion_result`（**只读**）
- 两者是否一致 / 冲突（由置信度系统自己计算的派生量）
- 已定义的 market regime / 标签
- 本地历史 logs / review records

### 3.2 禁止读取（黑名单）

以下输入**不允许**进入置信度系统：

- future outcome（目标日及之后的真实数据）
- 2026 final-test range（保留给最终验证用的窗口）
- trading result（模拟交易 / 真实交易结果）
- final_report mutation result（最终报告的任何 mutation 反馈）
- hard / forced decision **作为指令输入**（hard / forced 本就不该存在；即使存在也不得作为置信度的输入指令）
- required decision **作为指令输入**

### 3.3 输入边界判定原则

- 置信度系统**可以读取** `projection_result` 和 `exclusion_result`，
  但**只能评价，不能修改**。
- 派生量（如二者一致性、冲突程度）由置信度系统**自己**根据两份输入计算，
  不需要从外部传入。
- 任何"未来真实结果回灌为置信度训练数据"的设计，必须**严格区分**：
  - 离线训练 / calibration 阶段（允许使用历史已结案的真实结果作为标签）；
  - 在线 inference 阶段（**禁止**任何 future outcome 进入置信度计算路径）。
  本轮 contract 仅约束**在线 inference**；离线训练数据流另议，但其结果
  以"模型权重 / 校准表"的形式进入在线路径，**不允许**未来数据沿任何
  其他路径回流到当次评估。

---

## 4. 置信度系统必须输出什么

置信度系统的输出必须**至少**包含以下方向的字段。具体字段命名以
§9 contract 草案为准；本节描述含义和必填语义。

| 字段方向 | 含义 |
|---|---|
| `confidence_date` | 本次评价运行所基于的数据截止日 |
| `target_date` | 本次评价对应的目标交易日 |
| `system_name` | 固定 `"confidence_system"` |
| `question_answered` | 固定 `"system_reliability_evaluation"` |
| `projection_confidence` | 对推演系统输出的可信度评价（level + 可选 score + reasoning） |
| `exclusion_confidence` | 对否定系统输出的可信度评价（level + 可选 score + reasoning） |
| `projection_reliability_evidence` | 推演可信度的支撑证据（历史命中率、样本量、regime 一致性等） |
| `exclusion_reliability_evidence` | 否定可信度的支撑证据 |
| `agreement_status` | 推演 / 否定一致性状态（aligned / partial_conflict / strong_conflict / unknown，见 §10） |
| `conflict_level` | 冲突程度（none / low / medium / high / unknown） |
| `combined_confidence` | 综合可信度评价（**仅作为展示**，不回写） |
| `confidence_reasoning` | 综合评价的中文短句列表 |
| `reliability_warnings` | 触发的可靠性告警（如样本稀释、regime 漂移等） |
| `sample_size_notes` | 样本量相关说明 |
| `calibration_notes` | 校准 / 漂移相关说明 |
| `raw_evidence_refs` | 指向原始证据数据的引用 |

### 4.1 取值约定

- `level` 取自 `{"low", "medium", "high", "unknown"}`。
- `score` 可选，类型 float，范围 `[0.0, 1.0]`，缺失用 `null`，
  禁止用 `0` / `""` 假装存在。
- `level` 与 `score` 可同时存在，二者**必须**保持单调一致
  （高 level 不能配低 score）；具体映射规则由实现决定，但需在文档中固定。
- 输出**必须**明确是 **evaluation**（评价），**不是** prediction / exclusion 本身。

---

## 5. 置信度系统不能输出什么

以下字段**不允许**出现在置信度系统输出里：

- `most_likely_state`（属于推演系统）
- `most_unlikely_state`（属于否定系统）
- `modified_projection`
- `modified_exclusion`
- `projection_correction`
- `exclusion_correction`
- 任何 `*_correction` / `*_override` / `*_mutation` 字段
- `hard_exclusion`
- `forced_exclusion`
- `required_decision`
- `trading_action`
- `buy` / `sell` / `hold`
- `simulated_trade`
- `no_trade`
- `final_report_mutation`（置信度系统不写最终报告）
- 任何修改推演系统字段的输出
- 任何修改否定系统字段的输出
- 任何写入 final report 顶级聚合字段的输出

> 区分要点：`combined_confidence` 是置信度系统自己的输出，**仅供展示与
> aggregation 引用**，**不**回写到 `projection_result` 或 `exclusion_result`，
> 也**不**等同于 final report 的 `final_confidence`（后者归 07D）。

---

## 6. 置信度系统和推演系统的边界

- 置信度系统**可以读取** `projection_result`。
- 置信度系统**可以评价** `projection_result`。
- 置信度系统**不能修改** `most_likely_state` / `ranked_states` /
  `state_scores` / 任何推演字段。
- 置信度低**不代表**自动改掉推演（推演输出原样保留）。
- 置信度高**不代表**推演结果变成 hard / required（推演**不**因高置信度
  升级为强制状态）。
- **推演系统不读取 confidence_result**（07A §3.2 已固定）。
- 任何"先看 confidence_result 再调推演"的设计，违反 06 / 07A / 07C，默认 reject。

---

## 7. 置信度系统和否定系统的边界

- 置信度系统**可以读取** `exclusion_result`。
- 置信度系统**可以评价** `exclusion_result`。
- 置信度系统**不能修改** `most_unlikely_state` / `ranked_unlikely_states` /
  `state_impossibility_scores` / 任何否定字段。
- 置信度低**不代表**自动取消否定输出（否定输出原样保留）。
- 置信度高**不代表**否定结果变成 hard / forced（否定**不**因高置信度
  升级为强制状态）。
- **否定系统不读取 confidence_result**（07B §3.2 已固定）。
- 任何"先看 confidence_result 再调否定"的设计，违反 06 / 07B / 07C，默认 reject。

---

## 8. 置信度系统和 final report 的边界

- final report **可以读取**并**展示** `confidence_result`。
- final report **可以根据** `confidence_result` 标注风险 / 冲突 / 可信度。
- final report **不得**把 `confidence_result` 回写到 `projection_result` /
  `exclusion_result`。
- `confidence_result` **不是** final report 本身（final report 是 07D 的契约）。
- `confidence_result` **不决定**交易动作（不做任何 buy / sell / hold / no_trade
  的赋值）。
- final report 写入的是**它自己**的聚合字段，与置信度输出**并列**而非**覆盖**。

---

## 9. confidence_result contract 草案

> 本草案仅作为 contract 设计，不要求本轮代码实现。字段名采用 `snake_case`。
> 数值字段允许为 float；缺失语义用 `null`，不得用 `0` / `""` 假装存在。
> `level` 取自 `{"low", "medium", "high", "unknown"}`。

```jsonc
{
  "schema_version": "confidence_system_result.v1",

  "confidence_date": "<YYYY-MM-DD>",      // 数据截止日
  "target_date": "<YYYY-MM-DD>",          // 目标交易日

  "system_name": "confidence_system",
  "question_answered": "system_reliability_evaluation",

  "projection_confidence": {
    "level": "medium",
    "score": "<0.0–1.0 | null>",
    "reasoning": [
      "相似结构样本数 N=42，胜率分布稳定",
      "近 60 日 regime 内推演命中率约 58%"
    ]
  },

  "exclusion_confidence": {
    "level": "high",
    "score": "<0.0–1.0 | null>",
    "reasoning": [
      "当前 regime 下 most_unlikely_state 历史发生率 < 3%",
      "peer 非确认信号一致"
    ]
  },

  "projection_reliability_evidence": [
    "history_hit_rate:<projection_date>:regime=<...>",
    "similar_pattern_size:<...>"
  ],
  "exclusion_reliability_evidence": [
    "rare_event_size:<...>",
    "non_occurrence_rate:<...>"
  ],

  "agreement_status": "aligned",          // aligned / partial_conflict / strong_conflict / unknown
  "conflict_level": "none",               // none / low / medium / high / unknown

  "combined_confidence": {
    "level": "medium",
    "score": "<0.0–1.0 | null>",
    "reasoning": [
      "推演 medium，否定 high，二者方向一致",
      "样本量充分，无 regime 漂移告警"
    ]
  },

  "confidence_reasoning": [
    "本次推演与否定方向一致，combined 评为 medium 偏稳"
  ],

  "reliability_warnings": [
    "近期 regime 标签存在边缘漂移迹象"
  ],

  "sample_size_notes": [
    "推演相似样本 N=42（充分）",
    "否定 rare-event 样本 N=8（偏少，注意稳定性）"
  ],

  "calibration_notes": [
    "上次 calibration 距今 <N> 天，未触发重校阈值"
  ],

  "raw_evidence_refs": [
    "projection_result_ref:<...>",
    "exclusion_result_ref:<...>",
    "history_hit_rate_table:<...>"
  ]
}
```

> 上述草案**不**包含任何 `most_likely_state` / `most_unlikely_state` /
> `modified_*` / `final_*` / `simulated_trade` / `hard_exclusion` /
> `forced_exclusion` / `trading_action` 字段。这些字段属于其他系统的
> contract（或 07D 待定），不在 confidence_result 中出现。

---

## 10. agreement / conflict 定义

定义如下（取值固定，便于 final report 标注与下游引用）：

| 取值 | 含义 |
|---|---|
| `aligned` | 推演 `most_likely_state` 与否定 `most_unlikely_state` **不冲突**：例如推演说"小涨最可能"，否定说"大跌最不可能"，方向不矛盾。 |
| `partial_conflict` | 推演的高排名状态与否定的高不可能状态**部分重叠**：例如推演的 top-2 中包含一个被否定系统标为高不可能的状态，但 most_likely 和 most_unlikely 不相等。 |
| `strong_conflict` | 推演 `most_likely_state` **==** 否定 `most_unlikely_state`：两个系统对同一个状态的判断**直接对立**。 |
| `unknown` | 数据不足无法判定（任意一边输出缺失 / 输出 schema 不合规）。 |

`conflict_level` 取自 `{"none", "low", "medium", "high", "unknown"}`，
其与 `agreement_status` 的映射由实现决定，但**必须**满足以下单调约束：

- `aligned` → `conflict_level ∈ {none, low}`
- `partial_conflict` → `conflict_level ∈ {low, medium}`
- `strong_conflict` → `conflict_level ∈ {medium, high}`
- `unknown` → `conflict_level == unknown`

> **冲突不代表改写**：任何取值（包括 `strong_conflict` + `high`）都**不**触发
> 对推演 / 否定输出的改写。冲突的唯一作用是：**让 final report 可以标注**，
> 让用户看到两个系统这次不一致。

---

## 11. 禁止数据流

以下数据流在置信度系统中**严格禁止**（任意方向只要触发其一即视为违反）：

| 禁止数据流 | 含义 |
|---|---|
| `confidence_result → projection_system` | 置信度结果不得回流到推演（07A §10 已固定） |
| `confidence_result → exclusion_system` | 置信度结果不得回流到否定（07B §10 已固定） |
| `confidence_result → hard / forced decision` | 置信度结果不得触发任何 hard / forced 决策 |
| `confidence_result → trading_action` | 置信度结果不得直接生成交易动作 |
| `final_report → confidence_system as mutation instruction` | 最终报告不得作为指令回流到置信度系统 |
| `future outcome → confidence_system` | 目标日真实结果不得直接进入在线评估路径（仅离线 calibration 经权重 / 校准表入参） |
| `2026 final-test range → confidence_system` | 保留窗口数据不得作为置信度输入 |

任何 PR / candidate / 重构若引入以上任一数据流，违反 contract，默认 reject。

---

## 12. 与 continuous_smoothing 的关系

continuous_smoothing v1 / v2 已经 abandon as candidate layer（见 3R-3.3H 决策、
07B §11）。

**对置信度系统的约束**：

- continuous_smoothing **不能**作为"置信度捷径"被吸收。
- 不允许"continuous_smoothing 失败 → 自动转译为置信度系统的 hard warning"
  这种隐式入口。
- 置信度系统**可以**在未来读取 review / explanation / diagnostic layer 的输出
  作为 calibration / reliability 的参考，但**不能**直接复活 frozen candidate
  作为置信度数据源。
- 任何"continuous_smoothing 作为 active confidence candidate"的复活提案，
  在不更新本记录与 06 / 07B 的前提下，默认 reject。

---

## 13. 与现有系统的关系

本节**只做原则性描述**，不做完整体检：

- 现有 `confidence_engine.py` / `services/contract_calibration_inputs.py` /
  `services/active_rule_pool_calibration.py` /
  `services/exclusion_reliability_review.py` 以及 calibration / reliability /
  historical accuracy / exclusion reliability 相关模块，
  **未来需要依据本 contract 审查**。
- 本轮**不**判断每个模块归属（哪些属于置信度系统、哪些属于 calibration
  数据准备、哪些应进入 review / diagnostic 层）。
- 本轮**不**判断现有 `confidence_system` section（step_1a 中收口层的一段）
  与本 contract 的对齐情况。
- 完整体检**留到 07A / 07B / 07C / 07D 全部完成之后**统一进行。

> 现有 step_1a 文档定义的 `confidence_system` section 是 `run_predict` 收口层
> contract 中的一段，与本 contract 的范围**不同**：step_1a 是收口层 contract；
> 本 contract 只关注作为独立逻辑系统的"置信度系统"自身边界。
> 二者关系将在 07D（final report aggregator contract）中统一对齐。

---

## 14. 后续开发原则

- 下一步固定 **07D final report aggregator contract**。
- 四个 contract 都完成后，**才做系统体检**。
- 在四个 contract 全部完成之前：
  - 不进入 3R-5 / 3R-6
  - 不新增否定 candidate
  - **不新增置信度 candidate**
  - **不复活 continuous_smoothing 作为任何 candidate**
  - 任何"置信度 candidate"如有提案，必须先核对是否符合本 contract
    （包括 §3 输入白/黑名单、§5 禁止输出、§11 禁止数据流、
     §6 / §7 与推演 / 否定系统的只读评价边界）

---

## 15. 严守边界

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

本 contract 的修改路径：任何对置信度系统输入 / 输出 / 边界 / 数据流的调整，
都必须以**显式更新本文件**的方式提出，并同步检查是否影响 06记录、07A、
07B、07D。
