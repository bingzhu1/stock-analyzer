# 07D记录：Final Report Aggregator Contract

> 本记录是三系统 contract 序列中的第 4 份（也是最后一份），对应 06记录
> "三系统独立原则"中的第 4 步（固定 final report aggregator contract）。
>
> 本轮只写文档：不改代码、不写 DB、不运行 validation、不 commit / push、
> 不做系统体检、不进入 3R-5 / 3R-6、不新增任何 candidate、
> 不复活 continuous_smoothing。

---

## 1. 背景

06记录已经把"三系统独立原则"固定为项目层面的契约：

- 推演 / 否定 / 置信度三系统**互相独立**，不读取（推演不读否定）、不改写。
- 最终报告**只 aggregate，不 mutate**。
- 任意系统的输出**不得回流**到另一系统的输入。

07A 固定了推演系统 contract。
07B 固定了否定系统 contract。
07C 固定了置信度系统 contract。
本记录（07D）**只**固定 final report aggregator 的边界：

- final report **不是**第四个判断系统。
- final report **不是**推演系统、不是否定系统、不是置信度系统。
- final report **只**负责 **aggregate / display / annotate**。

final report 对自己负责，对"如何把三系统结果并列展示给用户"这件事负责，
仅此而已。

> 注：本文件定义"final report aggregator"作为一个**逻辑系统**的契约，
> 不预设 `services/final_decision.py` / `services/predict_summary.py` /
> `services/ai_summary.py` / `services/projection_narrative_renderer.py` /
> `services/projection_three_systems_renderer.py` /
> `ui/predict_tab.py` / `ui/projection_v2_renderer.py` 等具体模块的归属。
> 模块层面的归属判断留到四个 contract 全部完成后的系统体检。

---

## 2. Final Report 的核心问题

Final Report 回答的问题是：

> **"如何把推演系统、否定系统、置信度系统的结果并列展示给用户？"**

它**不**回答以下问题：

- 明天最可能发生什么 → 推演系统
- 明天最不可能发生什么 → 否定系统
- 二者各自有多可信 → 置信度系统
- 是否应该修改推演结果 → **禁止**（违反三系统独立）
- 是否应该修改否定结果 → **禁止**（违反三系统独立）
- 是否应该修改置信度结果 → **禁止**（违反三系统独立）
- 是否应该交易（buy / sell / hold / no_trade）→ 不属于 final report
- 是否应该 hard / forced → 不属于 final report
- 是否进入 3R-5 / 3R-6 → 与 contract 无关，是路线决策

Final Report **只**对"展示与标注"负责。任何让它回答其他问题的设计，
默认违反本 contract，应被 reject 或重定向到对应系统。

> **重要语义澄清**：
> Final Report 是**展示者**，不是**决策者**。
> 展示：把三系统结果排版、对齐、并列、标注一致 / 冲突。
> 决策：决定 most_likely / most_unlikely / 可信度 / 交易动作。
> Final Report **只能展示**，**禁止决策**。它的全部输出都必须可以
> 由"读取三系统输出 + 排版规则"复现，**不引入**额外判断。

---

## 3. Final Report 允许读取的输入

### 3.1 允许读取（白名单）

- `projection_result`（推演系统输出，**只读**）
- `exclusion_result`（否定系统输出，**只读**）
- `confidence_result`（置信度系统输出，**只读**）
- 三系统输出中的 `raw_evidence_refs`
- display metadata（用户语言 / 时区 / UI 主题等）
- user-facing formatting rules（排版规则、字段映射、label 翻译）
- risk disclosure text（风险披露模板文本）
- system conflict labels from `confidence_result`（来自置信度系统的
  `agreement_status` / `conflict_level`）

### 3.2 禁止读取（黑名单）

以下输入**不允许**进入 final report aggregator：

- future outcome（目标日及之后的真实数据）
- 2026 final-test range（保留给最终验证用的窗口）
- trading execution result **作为指令输入**（即使存在也不得驱动 aggregator 行为）
- hard / forced decision **作为指令输入**
- hidden mutation state（任何"暗中修改三系统输出"的中间态）
- raw output JSON **作为 live decision source**，除非它已显式作为 evidence ref
  出现在三系统输出中

### 3.3 输入边界判定原则

- final report **可以读取**三系统输出，但**只能展示和标注**，**不能改写**。
- final report **不**自己跑模型、不自己计算"最可能 / 最不可能 / 可信度"。
- final report **不**根据未来数据回填或修正展示结果。
- 任何"先 aggregate 一遍，再回头改三系统输出"的设计，违反 contract，默认 reject。

---

## 4. Final Report 必须输出什么

Final Report 的输出必须**至少**包含以下方向的字段。具体字段命名以
§9 contract 草案为准；本节描述含义和必填语义。

| 字段方向 | 含义 |
|---|---|
| `report_date` | 本次报告运行所基于的数据截止日 |
| `target_date` | 本次报告对应的目标交易日 |
| `system_name` | 固定 `"final_report_aggregator"` |
| `projection_section` | 推演系统的展示段（**只读**呈现 + display_summary） |
| `exclusion_section` | 否定系统的展示段（**只读**呈现 + display_summary） |
| `confidence_section` | 置信度系统的展示段（**只读**呈现 + display_summary） |
| `agreement_or_conflict_section` | 一致 / 冲突的展示段，引用置信度系统的 `agreement_status` / `conflict_level` |
| `combined_user_summary` | 用户可读的综合摘要（**仅展示**，不构成新预测 / 新否定 / 新置信度） |
| `risk_disclosure` | 风险披露文本列表（来自模板，不是新判断） |
| `evidence_summary` | 来自三系统 `raw_evidence_refs` 的展示化摘要 |
| `raw_evidence_refs` | 透传三系统的原始证据引用，便于追溯 |
| `non_mutation_confirmations` | 自检字段，确认本次 aggregate **没有 mutate** 任一系统输出 |

> `combined_user_summary` 是展示层摘要，**不是**新预测、新否定、新置信度。
> 它的全部内容必须可以从三系统输出 + 排版规则中重新派生出来。

---

## 5. Final Report 不能输出什么

以下字段**不允许**出现在 final report 输出里：

- `modified_projection`
- `modified_exclusion`
- `modified_confidence`
- `overridden_most_likely_state`
- `overridden_most_unlikely_state`
- `corrected_confidence`
- 任何 `*_correction` / `*_override` / `*_mutation` 字段
- `hard_exclusion`
- `forced_exclusion`
- `required_decision`
- `trading_action`
- `buy` / `sell` / `hold`
- `simulated_trade`
- `no_trade`
- `production_promotion`
- `_PROTECTION_LAYER_CONNECTED`（任何系统层级 promotion 标志）
- `final_report_mutation`（aggregator 不写 mutation 出口）
- 任何修改推演 / 否定 / 置信度系统字段的输出

> 区分要点：`combined_user_summary` 是 final report **自己**的展示字段，
> **不**回写到 `projection_result` / `exclusion_result` / `confidence_result`，
> 也**不**等同于推演系统的 `most_likely_state` 或置信度系统的
> `combined_confidence`。

---

## 6. Final Report 和推演系统的边界

- final report **可以**展示 `projection_result`。
- final report **不得**修改 `most_likely_state`。
- final report **不得**修改 `ranked_states` / `state_scores` / 任何推演字段。
- final report **可以标注**"推演与否定冲突"（取自置信度系统的
  `agreement_status` / `conflict_level`）。
- final report **不能**把展示摘要回写到 `projection_result`（即不允许把
  `combined_user_summary` 中的措辞反向覆盖 `most_likely_state` 等字段）。
- 推演系统**不读取** final report 输出（07A §3.2 / §10 已固定）。

---

## 7. Final Report 和否定系统的边界

- final report **可以**展示 `exclusion_result`。
- final report **不得**修改 `most_unlikely_state`。
- final report **不得**修改 `ranked_unlikely_states` /
  `state_impossibility_scores` / 任何否定字段。
- final report **可以标注**"否定与推演冲突"（取自置信度系统的
  `agreement_status` / `conflict_level`）。
- final report **不能**把展示摘要回写到 `exclusion_result`。
- 否定系统**不读取** final report 输出（07B §3.2 / §10 已固定）。

---

## 8. Final Report 和置信度系统的边界

- final report **可以**展示 `confidence_result`。
- final report **不得**修改 `projection_confidence` / `exclusion_confidence` /
  `combined_confidence` / 任何置信度字段。
- final report **可以**把 `confidence_result` 转成用户可读语言
  （例如："本次推演 medium 可信，否定 high 可信，二者方向一致"）。
- final report **不能**把用户可读语言回写到 `confidence_result`（即不允许
  把展示文案当成新的 `confidence_reasoning` 反向回填）。
- 置信度系统**不读取** final report 输出（07C §11 已固定）。

---

## 9. final_report contract 草案

> 本草案仅作为 contract 设计，不要求本轮代码实现。字段名采用 `snake_case`。
> 数值字段允许为 float；缺失语义用 `null`，不得用 `0` / `""` 假装存在。

```jsonc
{
  "schema_version": "final_report_aggregator_result.v1",

  "report_date": "<YYYY-MM-DD>",
  "target_date": "<YYYY-MM-DD>",

  "system_name": "final_report_aggregator",
  "question_answered": "aggregate_three_system_outputs",

  "projection_section": {
    "source_schema_version": "projection_system_result.v1",
    "most_likely_state": "小涨",
    "ranked_states": ["小涨", "震荡", "大涨", "小跌", "大跌"],
    "display_summary": "推演系统认为明天最可能小涨，依据 1) 量能放大 2) 多头排列"
  },

  "exclusion_section": {
    "source_schema_version": "exclusion_system_result.v1",
    "most_unlikely_state": "大跌",
    "ranked_unlikely_states": ["大跌", "小跌", "震荡", "大涨", "小涨"],
    "display_summary": "否定系统认为明天最不可能大跌，依据 1) 相似结构无大跌样本 2) peer 未释放风险信号"
  },

  "confidence_section": {
    "source_schema_version": "confidence_system_result.v1",
    "projection_confidence": {
      "level": "medium",
      "score": "<0.0–1.0 | null>"
    },
    "exclusion_confidence": {
      "level": "high",
      "score": "<0.0–1.0 | null>"
    },
    "combined_confidence": {
      "level": "medium",
      "score": "<0.0–1.0 | null>"
    },
    "display_summary": "推演 medium，否定 high，综合 medium"
  },

  "agreement_or_conflict_section": {
    "agreement_status": "aligned",
    "conflict_level": "none",
    "display_summary": "推演与否定方向一致，无冲突"
  },

  "combined_user_summary": "推演系统认为最可能小涨；否定系统认为最不可能大跌；置信度系统认为推演 medium、否定 high、综合 medium；二者方向一致。",

  "risk_disclosure": [
    "本报告为研究用途，不构成投资建议",
    "历史样本表现不保证未来结果"
  ],

  "evidence_summary": [
    "推演证据：相似结构 N=42，胜率 58%",
    "否定证据：当前 regime 下大跌历史发生率 < 3%",
    "置信度证据：近 60 日推演命中率分布稳定"
  ],

  "raw_evidence_refs": [
    "projection_result_ref:<...>",
    "exclusion_result_ref:<...>",
    "confidence_result_ref:<...>"
  ],

  "non_mutation_confirmations": {
    "projection_result_mutated": false,
    "exclusion_result_mutated": false,
    "confidence_result_mutated": false
  }
}
```

> 上述草案**不**包含任何 `modified_*` / `overridden_*` / `corrected_*` /
> `hard_exclusion` / `forced_exclusion` / `required_decision` /
> `trading_action` / `simulated_trade` / `production_promotion` /
> `_PROTECTION_LAYER_CONNECTED` 字段。这些字段属于禁止集合，
> 不在 final_report 中出现。

---

## 10. combined_user_summary 的边界

`combined_user_summary` **可以说**：

- "推演系统认为最可能是 X"
- "否定系统认为最不可能是 Y"
- "置信度系统认为二者关系为 Z（aligned / partial_conflict / strong_conflict / unknown）"
- "当前系统存在一致 / 冲突 / 不确定"
- 透传三系统给出的中文短句（必须有出处，不允许 aggregator 自创新结论）

`combined_user_summary` **不能说**：

- "最终改判为 X"（违反非改写原则）
- "系统强制否定 Y"（违反非改写、非 forced 原则）
- "应该买 / 卖 / 持有"（违反非交易原则）
- "hard / forced / required 已启用"（违反非 hard / forced 原则）
- "production ready"（违反非 promotion 原则）
- 任何"我（aggregator）认为……"的新判断

判定标准：**summary 中的任一句话，都必须能在三系统输出里找到对应来源**。
找不到来源的句子 = 新判断 = 违反 contract。

---

## 11. 禁止数据流

以下数据流在 final report aggregator 中**严格禁止**（任意方向只要触发其一
即视为违反）：

| 禁止数据流 | 含义 |
|---|---|
| `final_report → projection_system` | aggregator 不得回流到推演（07A §10 已固定） |
| `final_report → exclusion_system` | aggregator 不得回流到否定（07B §10 已固定） |
| `final_report → confidence_system` | aggregator 不得回流到置信度（07C §11 已固定） |
| `final_report → hard / forced decision` | aggregator 不得触发任何 hard / forced 决策 |
| `final_report → trading_action` | aggregator 不得直接生成交易动作 |
| `final_report → DB mutation` | aggregator 不得修改三系统的持久化输出（DB / log） |
| `final_report → production promotion` | aggregator 不得触发任何"上生产 / 提权"动作 |
| `future outcome → final_report (for current prediction)` | 目标日真实结果不得回流到当次报告 |

任何 PR / candidate / 重构若引入以上任一数据流，违反 contract，默认 reject。

> 注：未来真实结果**可以**进入**已结案的复盘报告 / review 报告**，但那
> 不属于"当次 final report"的范畴；当次 final report 只描述**当下**对
> 三系统输出的展示，与 review / outcome 是不同对象。

---

## 12. 与 continuous_smoothing 的关系

continuous_smoothing v1 / v2 已经 abandon as candidate layer（见 3R-3.3H 决策、
07B §11、07C §12）。

**对 final report 的约束**：

- final report **不得**把 continuous_smoothing 作为 active exclusion signal
  展示（即不允许在 `exclusion_section` 中引用 frozen candidate 的输出
  作为否定依据）。
- 如果未来 continuous_smoothing 以 review / explanation / diagnostic layer
  形式复用，**必须**先有独立 launch review 与 contract（不在 07A–07D 范围内）。
- 当前 final report **只能**引用已入库 checkpoint 中的历史结论
  （以"历史 reference / 文档锚点"形式），**不能**复活 frozen candidate
  作为当次 aggregate 的数据源。
- 任何"continuous_smoothing 作为 active aggregator 输入"的复活提案，
  在不更新本记录与 06 / 07B / 07C 的前提下，默认 reject。

---

## 13. 与现有系统的关系

本节**只做原则性描述**，不做完整体检：

- 现有 `services/final_decision.py` / `services/predict_summary.py` /
  `services/ai_summary.py` / `services/projection_narrative_renderer.py` /
  `services/projection_three_systems_renderer.py` /
  `ui/predict_tab.py` / `ui/projection_v2_renderer.py` /
  `ui/protection_layer_diagnostics_renderer.py` /
  `ui/research_tab.py` / `ui/review_tab.py` / `ui/history_tab.py` 等模块，
  以及 summary / report / Streamlit tab / final projection display 相关层，
  **未来需要依据本 contract 审查**。
- 本轮**不**判断每个模块归属（哪些属于 aggregator、哪些属于纯展示层、
  哪些其实在隐式做 mutation）。
- 本轮**不**判断现有 `final_projection` section（step_1a 中的一段）
  与本 contract 的对齐情况。
- 完整体检**留到 07A / 07B / 07C / 07D 全部完成之后**统一进行。

> 现有 step_1a 文档定义的 `final_projection` section 是 `run_predict` 收口层
> contract 中的一段，与本 contract 的范围**部分重叠但不等同**：step_1a 是
> 收口层 contract（包括三系统、final、模拟交易、复盘），本 contract 仅关注
> 作为独立逻辑系统的"final report aggregator"自身边界。
> step_1a 中 `final_projection` 现有字段是否合规（特别是 `final_direction` /
> `probability_bucket` / `final_one_sentence` 是否被当作"新决策"使用），
> 是系统体检阶段需要审查的重点。

---

## 14. 四份 contract 的合并检查要求

07A / 07B / 07C / 07D 全部完成后，**必须先做文档一致性检查**，再 commit
或按顺序 commit。一致性检查的最低要求：

| 检查项 | 期望 |
|---|---|
| 07A 不允许输出 exclusion / confidence | 07A §5 已禁止 ✅ |
| 07A 不读取 exclusion / confidence | 07A §3.2 已禁止 ✅ |
| 07B 不允许输出 projection / confidence | 07B §5 已禁止 ✅ |
| 07B 不读取 projection / confidence | 07B §3.2 已禁止 ✅ |
| 07C 不允许输出 projection / exclusion mutation | 07C §5 已禁止 ✅ |
| 07C 可读 projection / exclusion 但只读评价 | 07C §3.1 + §6 + §7 已固定 ✅ |
| 07D 不允许 mutate 三系统 | 07D §5 + §6 + §7 + §8 已禁止 ✅ |
| 07D 不读取 future outcome / hard / forced as instruction | 07D §3.2 已禁止 ✅ |
| 五状态命名跨四份 contract 一致 | 大涨 / 小涨 / 震荡 / 小跌 / 大跌（07A §4、07B §4 已固定，07C / 07D 引用一致）✅ |
| schema_version 命名一致 | `*_result.v1` 命名约定（07A / 07B / 07C / 07D 均采用）✅ |
| `system_name` / `question_answered` 字段一致 | 四份契约均要求显式声明，命名互不相同 ✅ |

> 一致性检查由"读全部四份文档对照本表"完成，**不**需要跑代码。
> 如发现冲突，先更新文档，再 commit；**不允许**靠代码 hack 抹平契约冲突。

---

## 15. 后续开发原则

- 四个 contract 都完成后，下一步**不是**进入 3R-5 / 3R-6，而是按顺序：
  1. **contract consistency review**（按 §14 表格逐项核对）
  2. **system architecture diagnosis**（对照四份 contract 审现有代码）
  3. **module inventory**（列出所有 projection / exclusion / confidence /
     aggregator / UI 模块及当前归属）
  4. **keep / freeze / quarantine / cleanup 标记**（每个模块明确去向）
- 在以上四步全部完成之前：
  - 不进入 3R-5 / 3R-6
  - 不新增任何 candidate（包括 projection / exclusion / confidence）
  - 不复活 continuous_smoothing 作为任何 candidate
  - 不允许"先改一改让它过 contract"的妥协式重构

---

## 16. 严守边界

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

本 contract 的修改路径：任何对 final report aggregator 输入 / 输出 /
边界 / 数据流的调整，都必须以**显式更新本文件**的方式提出，并同步检查
是否影响 06记录、07A、07B、07C。
