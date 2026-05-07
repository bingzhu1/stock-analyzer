# 07E记录：Three-System Contract Consistency Review

> 本记录是三系统 contract 序列的合并检查报告。仅做"读全部五份文档对照"，
> **不改代码、不写 DB、不运行 validation、不做系统体检、不做 module inventory、
> 不 commit / push、不进入 3R-5 / 3R-6、不新增 candidate、不复活
> continuous_smoothing**。

---

## 1. Review 目的

本轮**只**检查以下事项：

- 06 记录与 07A / 07B / 07C / 07D 之间的一致性
- 07A / 07B / 07C / 07D 四份 contract 之间是否存在边界冲突
- 是否存在容易被代码误解的模糊表达
- 输出 consistency review 文档

本轮**不**做：

- 改代码
- 修正文档（即使发现 wording 可优化也不本轮 patch）
- 系统体检 / module inventory
- 进入 3R-5 / 3R-6

目标：确认是否可以进入 **Step 08 architecture diagnosis**。

---

## 2. 被检查文档

| 文档 | 路径 | 状态 |
|---|---|---|
| 06 记录：三系统独立原则 | `tasks/record_06_three_system_independence_principle.md` | 已 commit (0979d93) |
| 07A：Projection System Contract | `tasks/record_07a_projection_system_contract.md` | 已 commit (909d5f2) |
| 07B：Exclusion System Contract | `tasks/record_07b_exclusion_system_contract.md` | 已 commit (909d5f2) |
| 07C：Confidence System Contract | `tasks/record_07c_confidence_system_contract.md` | 已 commit (909d5f2) |
| 07D：Final Report Aggregator Contract | `tasks/record_07d_final_report_aggregator_contract.md` | 已 commit (909d5f2) |

---

## 3. 总体一致性结论

> **PASS_WITH_MINOR_CLARIFICATIONS**

理由：

- 06 与 07A–07D 的核心语义、输入 / 输出方向、禁止事项、跨系统数据流方向**全部一致**。
- 不存在任一对契约相互**矛盾**或**冲突**的条款。
- 五状态命名（大涨 / 小涨 / 震荡 / 小跌 / 大跌）跨四份 contract 一致。
- `schema_version` 命名约定（`*_result.v1`）跨四份 contract 一致。
- 仅存在 2 处**例子级 wording 不一致**和 1 处**前瞻性表述与 07D 实际未定义字段不完全对齐**，
  这些都是文档表面的 wording 差异，**不影响契约语义、不影响代码审查标准、不阻塞 Step 08**。

详细 wording 不一致点见 §10、§11、§12。

---

## 4. 06 vs 07A/07B/07C/07D 一致性检查

| principle (06) | document checked | status | notes |
|---|---|---|---|
| 推演 = 回答"最可能" | 07A §2 | PASS | 07A 明确只回答 most_likely |
| 否定 = 回答"最不可能" | 07B §2 | PASS | 07B 明确只回答 most_unlikely |
| 置信度 = 评价二者可信度 | 07C §2 | PASS | 07C 明确"评价者，非仲裁者" |
| Final report 只 aggregate 不 mutate | 07D §2 / §4 / §5 | PASS | 07D 明确"展示者，非决策者"，并设 `non_mutation_confirmations` 自检字段 |
| 推演不读否定结果 | 07A §3.2 / §6 / §10 | PASS | 三处独立锁死 |
| 否定不读推演结果 | 07B §3.2 / §6 / §10 | PASS | 三处独立锁死，含 `most_likely_state → exclusion_system` 显式禁流 |
| 置信度可读但不改写推演 / 否定 | 07C §3.1 / §6 / §7 | PASS | 明确"只读评价" |
| Final report 不得 mutate 三系统 | 07D §5 / §6 / §7 / §8 / §11 | PASS | 多处独立锁死 |
| 三系统输出不得回流到对方输入 | 07A §10、07B §10、07C §11、07D §11 | PASS | 数据流矩阵完全闭合（详见 §9） |
| Final report 仅 aggregate，不引入新判断 | 07D §10 + §4 (`combined_user_summary` 边界) | PASS | "summary 中任一句话必须能在三系统输出找到对应来源" |
| 06 §7 8 条禁止模式 | 07A–07D 各 contract | PASS | 全部覆盖；continuous_smoothing 在 07B §11、07C §12、07D §12 三处独立约束 |

---

## 5. 07A 推演 contract 检查

| 检查项 | 状态 | 引用 |
|---|---|---|
| 是否只回答 most_likely | PASS | 07A §2 |
| 是否禁止读取 exclusion_result | PASS | 07A §3.2 + §6 + §10 |
| 是否禁止读取 confidence_result | PASS | 07A §3.2 + §7 + §10 |
| 是否禁止输出 exclusion_* / confidence_* / trading / hard / forced | PASS | 07A §5 完整列出 |
| `uncertainty_notes` 是否与 confidence_score 区分清楚 | PASS | 07A §4 边界澄清块 + §7 |
| `projection_result` schema 是否不含 forbidden fields | PASS | 07A §9 草案不含 `confidence_*` / `exclusion_*` / `final_*` / `simulated_trade` |
| 五状态命名是否固定 | PASS | 07A §4 + §9 草案 |

**推演 contract 整体判定：PASS**

---

## 6. 07B 否定 contract 检查

| 检查项 | 状态 | 引用 |
|---|---|---|
| 是否只回答 most_unlikely | PASS | 07B §2 |
| 是否禁止读取 projection_result | PASS | 07B §3.2 + §6 + §10（含 `most_likely_state → exclusion_system` 显式禁流） |
| 是否禁止读取 confidence_result | PASS | 07B §3.2 + §7 + §10 |
| 是否禁止输出 projection_* / confidence_* / trading / hard / forced | PASS | 07B §5 完整列出 |
| `state_impossibility_scores` 是否与 confidence_score 区分清楚 | PASS | 07B §4 边界澄清块 + §7（自评不确定性 ≠ 置信度分值）；该字段为"状态层级不可能性"，非"系统自评可信度" |
| `exclusion_result` schema 是否不含 forbidden fields | PASS | 07B §9 草案不含 `confidence_*` / `projection_*` / `final_*` / `simulated_trade` / `hard_exclusion` / `forced_exclusion` |
| `continuous_smoothing` 是否固定为 FROZEN_DIAGNOSTIC | PASS | 07B §11 明确定性 + 未来重用规则 |
| 强冲突时是否禁止改写 | PASS | 07B §6 举例表 + "冲突不是 bug，是契约下的合法状态" |

**否定 contract 整体判定：PASS**

---

## 7. 07C 置信度 contract 检查

| 检查项 | 状态 | 引用 |
|---|---|---|
| 是否只评价 projection / exclusion 可信度 | PASS | 07C §2 |
| 是否允许只读 projection_result / exclusion_result | PASS | 07C §3.1 + §3.3 |
| 是否禁止修改 projection / exclusion | PASS | 07C §6 + §7 + §5 |
| 是否禁止输出 most_likely / most_unlikely / modified_* / trading / hard / forced | PASS | 07C §5 完整列出 |
| agreement / conflict 是否只作为评价，不触发改写 | PASS | 07C §10 末尾"冲突不代表改写"明确锁死 |
| online vs offline calibration 是否清楚区分 | PASS | 07C §3.3 显式区分（离线训练允许 future-as-label，在线 inference 禁止） |
| future outcome 是否只允许离线 calibration | PASS | 07C §3.2 + §11（`future outcome → confidence_system` 列入禁流，仅经"权重 / 校准表"入参） |

**置信度 contract 整体判定：PASS**

---

## 8. 07D final report contract 检查

| 检查项 | 状态 | 引用 |
|---|---|---|
| 是否只 aggregate / display / annotate | PASS | 07D §2 + §4 |
| 是否禁止 mutate 三系统输出 | PASS | 07D §5 + §6 + §7 + §8 + §11 + `non_mutation_confirmations` 自检字段 |
| `combined_user_summary` 是否不能产生新判断 | PASS | 07D §10 "summary 中任一句话必须能在三系统输出找到对应来源" |
| conflict label 是否来自 confidence_result，而不是 final report 自己生成 | PASS | 07D §3.1 显式声明 `system conflict labels from confidence_result` + §6 / §7 / §9 草案的 `agreement_or_conflict_section` 引用置信度系统字段 |
| `raw_evidence_refs` 是否只能展示，不能重新推理 | PASS | 07D §3.3 "不自己跑模型、不自己计算最可能 / 最不可能 / 可信度" + §4 `evidence_summary` 描述为 "展示化摘要" |
| `final_report` schema 是否不含 modified_* / hard / forced / trading 字段 | PASS | 07D §9 草案末尾说明 + §5 完整列出 |
| `non_mutation_confirmations` 是否合理 | PASS | 07D §4 + §9 草案，结构为 `{projection_result_mutated: false, exclusion_result_mutated: false, confidence_result_mutated: false}`；作为运行期自检契约 |

**final report contract 整体判定：PASS**

---

## 9. Cross-contract forbidden data flow matrix

下表表示"FROM → TO"的数据流是否被允许。`X` 表示禁止；`R` 表示只读允许；
`—` 表示不适用（自身到自身）。

| from \ to | projection | exclusion | confidence | final_report |
|---|---|---|---|---|
| projection | — | **X** (07B §10) | **R** (07C §3.1, 只读评价) | **R** (07D §3.1, 只读展示) |
| exclusion | **X** (07A §10) | — | **R** (07C §3.1, 只读评价) | **R** (07D §3.1, 只读展示) |
| confidence | **X** (07A §10 / 07C §11) | **X** (07B §10 / 07C §11) | — | **R** (07D §3.1, 只读展示) |
| final_report | **X** (07A §10 / 07D §11) | **X** (07B §10 / 07D §11) | **X** (07C §11 / 07D §11) | — |
| future outcome | **X** (07A §3.2 / §10) | **X** (07B §3.2 / §10) | **X** (07C §3.2 / §11，仅离线 calibration 经权重表) | **X** (07D §3.2 / §11) |
| hard / forced decision (作指令) | **X** (07A §3.2 / §10) | **X** (07B §3.2 / §10) | **X** (07C §3.2) | **X** (07D §3.2) |
| trading_result | **X** (07A §10) | **X** (07B §10) | **X** (07C §3.2 trading result, §11 trading_action) | **X** (07D §3.2 / §11) |

**矩阵闭合性结论**：

- 三系统两两之间的"修改流"全部禁止 ✅
- 置信度系统对推演 / 否定**只读评价**（不写） ✅
- final report 对三系统**只读展示**（不写） ✅
- 三系统**均不读 final report** ✅
- future outcome / hard-forced / trading_result 全部不允许进入任一在线系统 ✅
- 离线 calibration 的 future-as-label 例外仅出现在 07C，且经"权重 / 校准表"间接入参，不构成在线数据流后门 ✅

**矩阵整体判定：PASS（闭合）**

---

## 10. Potential ambiguity list

| ambiguity | current_status | suggested_fix_if_needed |
|---|---|---|
| `uncertainty_notes` (推演 / 否定) vs `confidence_score`（置信度） | 已澄清：07A §4 / 07B §4 边界块 + 07A §7 / 07B §7 明确禁止系统自打 confidence。**轻微风险**：实现层若把"自评不确定性短语"误解为"系统自打可信度"，会偷偷越界。 | 不必本轮 patch；进入 Step 08 architecture diagnosis 时把 "自评不确定性短语" 与 "可信度量化" 列为代码审查 checklist。 |
| `state_impossibility_scores`（否定状态分值） vs `confidence_score`（置信度系统分值） | 已澄清：07B §4 该字段是**状态层级**的"不可能性"，不是"否定系统对自己整体打分"。**轻微风险**：实现层可能把它误读为 `exclusion_confidence` 来源。 | 不必本轮 patch；Step 08 审 `state_impossibility_scores` 与 `exclusion_confidence` 是否被正确分开。 |
| `combined_user_summary` 是否可能引入新判断 | 已锁死：07D §10 "summary 中任一句话必须能在三系统输出找到对应来源"。**风险点**：实现层易因 LLM 拼接 / 自由文本生成偏离来源约束。 | 不必本轮 patch；Step 08 审现有 `services/ai_summary.py` / `services/predict_summary.py` / `services/projection_narrative_renderer.py` 是否符合"句句必有出处"。 |
| conflict label 来源 | 已锁死：07D §3.1 + §6 + §7 + §9 草案均指向 `confidence_result.agreement_status / conflict_level`。 | 无需 patch。 |
| `raw_evidence_refs` 展示 vs 重新推理 | 已锁死：07D §3.3 "不自己跑模型" + §4 描述为"展示化摘要"。**轻微风险**：实现层易把 evidence summary 的"重述"做成"重算"。 | 不必本轮 patch；Step 08 审 evidence summary 实现是否真的只读。 |
| offline calibration vs future leakage | 已锁死：07C §3.3 + §11。**轻微风险**：在线计算路径上若直接拿历史 outcome 作 feature（即使是过去事实），仍属"未来数据→在线"灰区，需在体检阶段验证 cutoff。 | 不必本轮 patch；Step 08 把"在线 vs 离线 cutoff 校验"列入 confidence 模块审查项。 |
| 07A §8 例子字段 (`combined_view` / `aggregate_summary`) vs 07D 实际字段 (`combined_user_summary`) | **wording 不一致**：07A 写下 final report 的占位例子字段名，07D 最终采用 `combined_user_summary` 与 `combined_*_section`。语义无冲突，仅 wording 不对齐。 | 可选 patch：把 07A §8 例子改为 `combined_user_summary` / `*_section` 与 07D 一致。**本轮不 patch。** |
| 07C §5 区分要点提到 final report 的 `final_confidence`（"后者归 07D"），但 07D 实际未定义 `final_confidence` 字段 | **前瞻性表述与最终契约未对齐**：07C 在 07D 之前写好，预设 final report 会有 `final_confidence`；07D 最终决定不引入 `final_confidence`，只透传 `confidence_section.combined_confidence`。语义无冲突（07D 不引入是更严格的展示原则），仅 07C 预设字段不再存在。 | 可选 patch：把 07C §5 区分要点改为 "...也**不**等同于 final report 透传的 `confidence_section.combined_confidence`（后者归 07D，仅展示，不重新计算）"。**本轮不 patch。** |
| 五状态跨契约命名 | **一致**（大涨 / 小涨 / 震荡 / 小跌 / 大跌） | 无需 patch。 |
| `schema_version` 命名 | **一致**（`*_result.v1`） | 无需 patch。 |
| `system_name` / `question_answered` 字段 | **一致且互不相同**：projection_system / exclusion_system / confidence_system / final_report_aggregator | 无需 patch。 |

---

## 11. 是否需要 patch

> **NO_PATCH_NEEDED**

判定依据：

- §10 列出的所有 wording 不一致**均不影响契约语义**，也**不阻塞 Step 08
  architecture diagnosis** —— 体检阶段对照四份 contract 审现有代码时，
  以 07D §9 草案为 final report 的权威字段定义即可，07A §8 / 07C §5 的
  例子级 / 前瞻性表述不会产生误判。
- 没有发现任何**契约级冲突**或**禁止事项漏洞**。
- 跨系统数据流矩阵闭合（§9）。
- 不需要"先 patch 再做体检"，可直接进入 Step 08。

可选的文档级 wording polish（**本轮不做**，留作 Step 08+ 阶段补丁候选）：

1. 07A §8 把 `combined_view` / `aggregate_summary` 例子字段名替换为
   `combined_user_summary`，与 07D 对齐；
2. 07C §5 区分要点把"final report 的 `final_confidence`"改为
   "final report 透传的 `confidence_section.combined_confidence`"，与
   07D 实际未引入 `final_confidence` 的事实对齐。

---

## 12. 是否可以进入 Step 08 architecture diagnosis

> **YES**

理由：

- 06 + 07A–07D 五份文档**全部 commit 进 main**，构成完整契约链
  （06 原则 → 07A 推演 → 07B 否定 → 07C 置信度 → 07D 聚合）。
- 跨契约一致性矩阵闭合，禁止数据流闭环（§9）。
- 没有任何契约级冲突或漏洞。
- §10 列出的 wording polish 是**可选项**，不阻塞体检判定标准。
- 四份 contract 已足够作为系统体检（architecture diagnosis）的判定依据。

下一步可以做：

1. **Step 08 system architecture diagnosis** —— 对照四份 contract 审现有代码：
   - `predict.py` / `services/projection_*.py` 等 → 是否符合 07A
   - `services/exclusion_layer.py` / `services/anti_false_exclusion_*` /
     `services/big_up_contradiction_card.py` /
     `services/exclusion_reliability_review.py` /
     `services/continuous_smoothing_candidate*.py` 等 → 是否符合 07B
   - `confidence_engine.py` / `services/contract_calibration_inputs.py` /
     `services/active_rule_pool_calibration.py` 等 → 是否符合 07C
   - `services/final_decision.py` / `services/predict_summary.py` /
     `services/ai_summary.py` / `services/projection_narrative_renderer.py` /
     `services/projection_three_systems_renderer.py` /
     `ui/predict_tab.py` / `ui/projection_v2_renderer.py` 等 → 是否符合 07D
   - 现有 step_1a 的 8-section `run_predict` 输出 contract 与四份新 contract 的对齐
     （特别是 step_1a 的 `final_projection.final_direction` /
     `probability_bucket` / `final_one_sentence` 是否被当作"新决策"使用）。

2. **Step 09 module inventory** —— 列出每个模块的当前归属与合规状态。

3. **Step 10 keep / freeze / quarantine / cleanup 标记** —— 每个模块明确去向。

在 Step 08–10 完成之前：

- **不进入 3R-5 / 3R-6**
- **不新增 candidate**（projection / exclusion / confidence 任何一类都不新增）
- **不复活 continuous_smoothing**
- **不允许"先改一改让它过 contract"的妥协式重构**

---

## 13. 严守边界

本轮**只读 review**：

- 未改代码
- 未新增测试
- 未写 DB
- 未改 DB schema
- 未跑 replay
- 未跑 validation
- 未做 module inventory
- 未做系统体检
- 未进入 3R-5 / 3R-6
- 未新增任何 candidate
- 未复活 continuous_smoothing
- 未对 06 / 07A / 07B / 07C / 07D 做任何 patch

本 review 的修改路径：任何对 §3 总体结论、§9 矩阵、§10 ambiguity 列表、
§11 patch 决定、§12 进入 Step 08 决定的调整，都必须以**显式更新本文件**
的方式提出。
