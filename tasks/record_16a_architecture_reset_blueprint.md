# 16A记录：Architecture Reset Blueprint

> 本记录是 **Step 16A：架构重置蓝图**。Step 12 boundary fixes / Step 13
> regression / Step 14 cleanup / Step 15 final signoff 已全部完成；main 最近
> commit 为 `4c2e982 docs(cleanup): record 15 cleanup regression final status
> signoff`。
>
> 本轮**只**写架构蓝图文档：未改业务代码、未新增测试、未删除文件、
> 未移动文件、未修改 `.gitignore`、未处理 handoff、未处理 logs / DB backup /
> `.claude/worktrees/`、未跑 replay / validation / historical evaluation、
> 未写 DB / 未改 DB schema、未默认迁移 `run_predict` 到 V2、未接 trading、
> 未输出 buy / sell / hold、未输出 hard / forced / required、
> 未进入 3R-5 / 3R-6、未 commit / 未 push。
>
> 唯一 deliverable：本文件。

---

## 1. Step 16A 目的

本轮**不是**继续修 bug，**不是**直接跑胜率，**不是**新增 candidate，
**不是**默认切 V2。

本轮的目的是：在 12–15 边界修复 + 回归 + 清理签收完成之后，**确立
未来系统的大架构**，让所有模块在下一阶段（Step 16B 起）可以正式站队。

蓝图把 AVGO 系统拆成：

- **1 个主干** — AVGO Trading Research System
- **9 个正式分支** — Data / Feature / Projection / Exclusion / Confidence /
  Final Report / Review & Learning / Evaluation / UI
- **1 个临时迁移区** — Temporary Migration Bridge（**不属于**正式架构）

本轮**只**写蓝图。**不**改代码、**不**移动 / 删除文件、**不**新增测试、
**不**跑数据、**不**写 DB、**不**进入 3R-5 / 3R-6。

---

## 2. 为什么需要架构重置

继续在当前结构里做小修小补，已无法回答"系统胜率是多少"这一最终问题。
当前真实状态：

1. **三套链路并存**
   - 旧链：`predict.run_predict` → `build_primary_projection` →
     `apply_peer_adjustment` → `build_final_projection`
   - V2 链：`services.projection_orchestrator_v2.run_projection_v2`，
     内部仍通过 `services.projection_orchestrator.build_projection_orchestrator_result`
     **回调** `predict.run_predict`，再向后接入 standardized chain
     （exclusion + main_projection + consistency + confidence_evaluator + final_decision）
   - 主页链：`services.home_terminal_orchestrator.build_home_terminal_orchestrator_result`
     是 app.py 主页用的独立链路（features → exclusion → main_projection →
     consistency → confidence + log）
2. **`predict.py` 仍包含旧推演逻辑**
   - `build_primary_projection` / `apply_peer_adjustment` /
     `build_final_projection` 是另一套主推演 + peer 调整 + 最终决策栈
   - 12E X1..X5 已把 `predict.py` 标记为 legacy wrapper、`final_confidence` /
     `prediction_summary` 改为从 `confidence_result` / `final_report.combined_user_summary`
     转译，但**默认路径仍然走旧链**（hard rule 1 / Step 13 §2）
3. **`services/main_projection_layer.py` 是新主推演候选，但还有边界问题**
   - 模块顶部 `from services.exclusion_layer import build_peer_alignment`
     —— 主推演反向 import 否定层模块
   - `build_main_projection_layer` / `run_main_projection_layer` 形参仍保留
     `exclusion_result`，靠 `del exclusion_result` 软守边界
4. **`services/exclusion_layer.py` 是否定系统候选，但 peer_alignment 需要抽公共模块**
   - `build_peer_alignment` 当前住在 exclusion_layer 中；它本身是纯特征
     推导（NVDA / SOXX / QQQ ret1 → up_support / down_support / alignment），
     与"否定"这件事并无逻辑耦合
   - 从 06 / 07A / 07B 的契约看，peer_alignment 应该是 Feature 层的一部分，
     而不是 Exclusion 层的内部资产
5. **`services/confidence_evaluator.py` 边界干净，但 key 不对齐**
   - 边界本身遵守 07C：read-only、无 mutation、`_FORBIDDEN_FIELDS` 防护
   - 但 `_compute_agreement` 期望 `projection_result.most_likely_state` /
     `projection_result.ranked_states` / `exclusion_result.most_unlikely_state` /
     `exclusion_result.ranked_unlikely_states`
   - 当前 `main_projection_layer` 输出 `predicted_top1.state` /
     `state_probabilities`；`exclusion_layer` 输出 `triggered_rule` /
     `excluded`。**key 不匹配**，agreement 长期落到 `unknown`
   - `calibration_context` 在 home_terminal_orchestrator / projection_orchestrator_v2
     **均未传入**，level 长期降级到 `unknown`
6. **UI 仍读旧 `predict_result` 字段**
   - `ui/predict_tab.py:1410` 调用 `predict.run_predict(...)`，主显示字段
     仍是 `final_bias` / `final_confidence` / `primary_projection` /
     `final_projection`
   - 三系统视图 `_render_confidence_three_columns` 通过
     `predict_result["projection_three_systems"]["confidence_evaluator"]`
     接 V2 attachment，但主面板与 metric 仍走旧字段
7. **评估准确率前必须先统一系统入口和模块归属**
   - 三套链路并存 + key 不对齐 + UI 读旧字段，意味着任何"胜率"数字
     都可能在不同链路下取到不同语义
   - 必须先确立大架构、让模块站队，再做 evaluation；否则 evaluation
     的口径无法保证

---

## 3. 架构主干定义

**主干名称**：

> **AVGO Trading Research System**

**主干职责**：

- 统一数据流（所有分支共享同一份市场数据 / 历史数据 / 事件数据）
- 统一三系统输出（推演 / 否定 / 置信度的 schema 全局只有一份）
- 统一复盘和评估入口（review / evaluation 都从同一个 final report 进）
- 保持研究系统定位（research agent，不是 trading bot）
- 不直接进入交易执行

**明确**：

> 主干**不是** trading execution system。
> 主干**不**输出 buy / sell / hold。
> 主干**不**做 hard / forced / required decision。
> 主干**不**自动 promotion，**不**自动切 V2，**不**自动放行 LLM 决定方向。

主干为研究系统提供：

- 一份 projection（最可能）
- 一份 exclusion（最不可能）
- 一份 confidence（二者各自可信度 + 一致性）
- 一份 final report（三系统并列展示，不 mutate）
- 一份 review / outcome（事后复盘，不当次改答案）
- 一份 evaluation（signal win-rate，不是 trading win-rate）

主干**禁止**承担：

- 任何 trading-action 计算
- 任何 hard / forced / required 决策
- 任何 mutation 反馈回路（任意系统输出回流到另一系统输入）

---

## 4. 九个正式分支

正式 9 分支：

1. **Data Layer** — 原始市场数据 / 事件数据
2. **Feature Layer** — 统一特征 payload（含 peer_alignment / 15 日窗口）
3. **Projection System** — 最可能（07A 契约）
4. **Exclusion System** — 最不可能（07B 契约）
5. **Confidence System** — 二者可信度 + 一致性（07C 契约）
6. **Final Report Layer** — 三系统并列展示（07D 契约）
7. **Review & Learning Layer** — 事后复盘 / 错题本 / pre-prediction briefing
8. **Evaluation Layer** — projection / exclusion / confidence 的 signal-level 评估
9. **UI / Presentation Layer** — Streamlit 展示

每个分支的契约见 §5–§13。

> 顺序约束：上游分支不读下游分支输出。Data → Feature → {Projection,
> Exclusion, Confidence}（三者**互相不读**）→ Final Report → Review &
> Learning（事后） / Evaluation → UI。

---

## 5. Branch 1：Data Layer

**职责**：

- 读取 AVGO 自身行情（OHLCV）
- 读取 NVDA / SOXX / QQQ 同行行情
- 读取历史行情 / 历史五状态样本
- 读取成交量 / 成交额
- 读取事件 / 财报 / 新闻上下文（如已有 collector）
- 提供原始数据，**不做判断**

**输入**：外部数据源（yfinance / 本地 CSV / DB）。

**输出**：raw OHLCV / panel 数据 / 历史样本表（pandas DataFrame 或同等
结构）；不含任何 projection / exclusion / confidence 字段。

**禁止**：

- 不预测
- 不否定
- 不生成置信度
- 不输出最终结论
- 不读取下游系统的输出
- 不读取 future outcome（在线 inference 路径）

**候选模块**：

- [data_fetcher.py](data_fetcher.py)
- `collectors/`（如未来引入）
- [services/market_data_store.py](services/market_data_store.py)
- [scanner.py](scanner.py) 中的"纯数据读取"部分（注意：scanner 同时承担
  硬规则匹配，本分支只接它的数据读取层）

**当前风险**：

- scanner.py / matcher.py / encoder.py 是 hard rule 2 锁定的硬规则层；
  数据读取与硬规则推断未做物理分离，需要在 16B / 16C 站队时显式标记
  哪些函数属于 Data Layer、哪些属于 Feature Layer 或 Projection / Exclusion

---

## 6. Branch 2：Feature Layer

**职责**：

- 把原始数据转成统一 feature payload
- 生成 **15 日窗口**特征
- 生成 ret1 / ret3 / ret5 / ret10
- 生成价格位置（pos）、成交量比、成交额、K 线特征（shadow_ratio）
- 生成 peer feature（NVDA / SOXX / QQQ ret1 / 同步度 / peer_alignment）
- 生成历史相似样本特征
- 生成 regime label（如有）

**关于窗口长度**（明确）：

> 未来主系统标准窗口 = **15 trading days**（与 07A §3.1 / §9 草案一致）。
> 当前代码大量使用 20 日窗口（[services/main_projection_layer.py](services/main_projection_layer.py)、
> [services/home_terminal_orchestrator.py](services/home_terminal_orchestrator.py) 中
> `compute_20d_features`、[services/projection_chain_contract.py](services/projection_chain_contract.py)
> 中 `build_feature_payload_from_recent_window` 默认 20）。
> 本轮**不**改窗口，但显式标记：**20d 逻辑暂为 legacy / compatibility，
> 需在 16C 之后迁移到 15d**。

**输入**：Data Layer 的原始 OHLCV / panel / 历史样本。

**输出**：feature_payload（dict / typed dict），含统一字段名（snake_case），
缺失语义用 `null` 不用 `0`。

**禁止**：

- 不预测
- 不否定
- 不生成置信度
- 不读取 projection / exclusion / confidence / final_report / review 输出
- 不依赖任意系统输出回灌

**候选模块**：

- [feature_builder.py](feature_builder.py)
- [encoder.py](encoder.py)
- [matcher.py](matcher.py) 的 feature 抽取部分
- [services/projection_chain_contract.py](services/projection_chain_contract.py)
  中 `build_feature_payload_from_recent_window` / `_shadow_ratio` /
  `_ret_pct` 等 feature 推导函数
- [services/features_20d.py](services/features_20d.py)（如存在 / 内容相关）
- [services/regime_features_builder.py](services/regime_features_builder.py)
- [services/regime_labels_builder.py](services/regime_labels_builder.py)

**关于 peer_alignment 的归属**（重要）：

> 当前 `build_peer_alignment` 住在
> [services/exclusion_layer.py](services/exclusion_layer.py:64)；
> [services/main_projection_layer.py:18](services/main_projection_layer.py:18)
> 反向 import 它。peer_alignment 本身是纯特征推导（NVDA / SOXX / QQQ ret1
> → up_support / down_support / alignment），**与"否定"这件事无关**，
> 应归 Feature Layer。
>
> 16C / 16D 期间应把 `build_peer_alignment` 抽到独立模块（如
> `services/peer_alignment.py`），让 Projection 与 Exclusion **都**从
> Feature Layer import，而不是 Projection 反向 import Exclusion。

**当前风险**：

- 窗口长度仍是 20d；与 07A 契约的 15d 不一致
- peer_alignment 当前位于 Exclusion 模块内部，导致 Projection 反向 import
- feature payload schema 在 home_terminal / v2 / legacy 三条链上字段命名
  不完全统一（例：`vol_ratio20` vs `vol_ratio_5d`，[services/projection_orchestrator_v2.py:88-93](services/projection_orchestrator_v2.py:88) 已可见）

---

## 7. Branch 3：Projection System

**职责**：

> 只回答"**最可能发生什么**"。

**输入**（白名单，依据 07A §3.1）：

- AVGO 自身行情 / 近 15 日结构（来自 Feature Layer）
- 五状态历史样本
- 历史相似结构
- NVDA / SOXX / QQQ peer 信号（来自 Feature Layer，**不**经 Exclusion）
- 成交量 / 成交额 / 位置 / 趋势 / 反转
- regime label

**标准输出**（07A §9 草案，schema_version `projection_system_result.v1`）：

```jsonc
projection_result:
  most_likely_state           // 五状态之一
  ranked_states               // 五状态完整排序（推演视角）
  state_probabilities         // 或 state_scores
  evidence                    // primary_reasoning / key_supporting_signals / key_risk_signals
  raw_score                   // 推演内部打分（可选）
  uncertainty_notes           // 自评不确定性（不是 confidence）
  raw_evidence_refs           // 证据指针
```

（具体字段见 07A §9 草案；此处只列方向。）

**候选模块**：

- [services/main_projection_layer.py](services/main_projection_layer.py)

**禁止**（依据 07A §3.2 / §5 / §10）：

- 不读取 `exclusion_result`（任何 `exclusion_*` 字段）
- 不读取 `confidence_result`
- 不读取 `final_report` 任何聚合输出
- 不输出交易动作（buy / sell / hold / no_trade / simulated_trade）
- 不输出 hard_exclusion / forced_exclusion / required_decision
- 不输出 most_unlikely_state（属否定）
- 不输出 confidence_score / confidence_level / final_confidence
- 不读取 future outcome（包含 2026 final-test range）

**当前风险**：

- [services/main_projection_layer.py:18](services/main_projection_layer.py:18)
  仍 `from services.exclusion_layer import build_peer_alignment`：
  虽然函数本身是 feature 推导，但 import 方向违反"projection 不 read
  exclusion 模块"的精神，需在 16C 抽到 Feature Layer
- [services/main_projection_layer.py:286](services/main_projection_layer.py:286)
  / [main_projection_layer.py:298](services/main_projection_layer.py:298)：
  `build_main_projection_layer` 仍接受 `exclusion_result` 参数并 `del`
  之；同 `run_main_projection_layer`。这是软边界，需在 16E 删形参
- 输出 schema 是 `predicted_top1.state` / `state_probabilities` /
  `peer_alignment` / `feature_snapshot` / `rationale` / `warnings`，
  与 07A §9 的 `most_likely_state` / `ranked_states` / `state_scores` /
  `primary_reasoning` 命名不一致；需在 16C 决定是否对齐 contract 草案

---

## 8. Branch 4：Exclusion System

**职责**：

> 只回答"**最不可能发生什么**"。

**输入**（白名单，依据 07B §3.1）：

- AVGO 自身行情 / 近 15 日结构
- 五状态历史样本中"最少发生"的状态
- 历史 rare-event pattern
- NVDA / SOXX / QQQ peer 非确认信号（来自 Feature Layer）
- 成交量 / 成交额 / 位置 / 趋势 / 反转
- regime label

**标准输出**（07B §9 草案，schema_version `exclusion_system_result.v1`）：

```jsonc
exclusion_result:
  most_unlikely_state           // 五状态之一
  ranked_unlikely_states        // 五状态完整排序（否定视角）
  excluded_states               // 该次否定明确排除的状态集合
  state_impossibility_scores
  primary_exclusion_reasoning
  rare_event_evidence
  historical_non_occurrence_summary
  peer_non_confirmation_summary
  key_exclusion_signals
  key_counter_signals
  uncertainty_notes
  raw_evidence_refs
  false_exclusion_risk          // 自评的"我也可能错"
  triggered_rules               // 命中的规则列表
```

**候选模块**：

- [services/exclusion_layer.py](services/exclusion_layer.py)

**禁止**（依据 07B §3.2 / §5 / §10）：

- 不读取 `projection_result`（任何 `projection_*` 字段）
- 不读取 `most_likely_state`
- 不读取 `final_prediction` / `primary_direction` / `final_report`
- 不读取 `confidence_result`
- 不根据主推演结果"选择否定对象"（违反 06 §7）
- 不输出交易动作 / hard / forced / required

**当前风险**：

- 输出 schema 是 `excluded` / `action` / `triggered_rule` /
  `peer_alignment` / `reasons`，与 07B §9 草案 `most_unlikely_state` /
  `ranked_unlikely_states` 命名不一致；需在 16C 决定对齐
- `build_peer_alignment` 当前作为 Exclusion 模块的导出 API（被
  Projection 反向 import）；应在 16C / 16D 移到 Feature Layer
- [services/anti_false_exclusion_audit.py](services/anti_false_exclusion_audit.py) /
  [services/anti_false_exclusion_dashboard.py](services/anti_false_exclusion_dashboard.py) /
  [services/exclusion_reliability_review.py](services/exclusion_reliability_review.py) /
  [services/big_up_contradiction_card.py](services/big_up_contradiction_card.py)
  归属待 16B 站队（候选：Exclusion 内部 / Review & Learning / UI）

---

## 9. Branch 5：Confidence System

**职责**：

> 只回答"**这次推演和否定可靠吗**"。

**输入**（白名单，依据 07C §3.1）：

- 原始市场数据 / 历史五状态分布
- 历史推演命中率（projection accuracy by structure / regime）
- 历史否定命中率（exclusion success / false_exclusion）
- 历史样本量（稀释 / 稳定性）
- 当前 `projection_result`（**只读**）
- 当前 `exclusion_result`（**只读**）
- regime label

**标准输出**（07C §9 草案，schema_version `confidence_system_result.v1`）：

```jsonc
confidence_result:
  projection_confidence    // {level, score, reasoning}
  exclusion_confidence     // {level, score, reasoning}
  agreement_status         // aligned / partial_conflict / strong_conflict / unknown
  conflict_level           // none / low / medium / high / unknown
  combined_confidence      // {level, score, reasoning} —— 仅展示，不回写
  confidence_reasoning
  reliability_warnings
  sample_size_notes
  calibration_notes
  raw_evidence_refs
```

**候选模块**：

- [services/confidence_evaluator.py](services/confidence_evaluator.py)

**辅助 / 数据准备**（候选 Confidence 内部，待 16B 站队）：

- [services/contract_calibration_inputs.py](services/contract_calibration_inputs.py)
- [services/active_rule_pool_calibration.py](services/active_rule_pool_calibration.py)（**注意**：
  与 promotion 模块共享 active_rule_pool 命名空间，需独立审）
- [services/exclusion_reliability_review.py](services/exclusion_reliability_review.py)
  （也可能归 Review & Learning，待 16B 站队决定）

**禁止**（依据 07C §5 / §11）：

- 不改写 `projection_result`
- 不改写 `exclusion_result`
- 不输出 most_likely_state（属推演）
- 不输出 most_unlikely_state（属否定）
- 不输出 hard / forced / required / trading_action
- 不读取 future outcome 进入在线 inference 路径
- 不允许 `confidence_result → projection_system / exclusion_system` 回流

**当前风险**：

1. **key 与 main_projection / exclusion 输出未完全对齐**
   - [services/confidence_evaluator.py:163](services/confidence_evaluator.py:163)
     `_compute_agreement` 期望 `proj.most_likely_state` / `proj.ranked_states` /
     `excl.most_unlikely_state` / `excl.ranked_unlikely_states`
   - 当前 main_projection 输出 `predicted_top1.state` /
     `state_probabilities`；exclusion 输出 `triggered_rule` / `excluded`
   - 结果：`agreement_status` 长期落到 `unknown`
2. **calibration_context 未接入**
   - [services/home_terminal_orchestrator.py:169-174](services/home_terminal_orchestrator.py:169)
     与 [services/projection_orchestrator_v2.py:585-590](services/projection_orchestrator_v2.py:585)
     调用 `build_confidence_result` 时未传 `calibration_context`
   - 按 07C §9 / evaluator §3.3，level 长期降级为 `unknown`
3. **UI 未读 confidence_result**
   - `ui/predict_tab.py` 主面板仍用 `final_confidence`（来自旧链 +
     12E X2 转译）；`_render_confidence_three_columns` 才走
     `projection_three_systems.confidence_evaluator`，但只是辅助 panel

> 这三点都是 16C / 16D 之后的修复目标；本轮蓝图只记录风险，**不**改代码。

---

## 10. Branch 6：Final Report Layer

**职责**：

- 汇总 projection / exclusion / confidence 三系统输出
- 生成标准报告（schema 固定）
- 展示冲突 / 风险 / 证据来源
- 生成人能读懂的 final report（`combined_user_summary`）
- **可读** + **可追溯**：每一句 summary 都必须能在三系统输出找到出处

**输入**（白名单，依据 07D §3.1）：

- `projection_result`（只读）
- `exclusion_result`（只读）
- `confidence_result`（只读）
- 三系统的 `raw_evidence_refs`
- display metadata（语言 / 时区 / UI 主题）
- formatting rules / risk disclosure 模板文本

**标准输出**（07D §9 草案，schema_version `final_report_aggregator_result.v1`）：

```jsonc
final_report:
  projection_section          // 推演段（只读呈现 + display_summary）
  exclusion_section           // 否定段
  confidence_section          // 置信度段
  agreement_or_conflict_section
  combined_user_summary       // 仅展示
  risk_disclosure
  evidence_summary
  raw_evidence_refs
  non_mutation_confirmations  // 自检：projection / exclusion / confidence 是否被 mutate
```

**候选模块**：

- [services/final_decision.py](services/final_decision.py)（已实现 §6 strict
  passthrough：`final_direction = primary_direction`；`final_confidence`
  来源固定为 `confidence_result.combined_confidence.level`；exclusion
  仅 display）
- [services/projection_output_contract.py](services/projection_output_contract.py)
  （8 段 schema validator：`current_structure` / `avgo_primary_projection` /
  `peer_confirmation_adjustment` / `exclusion_system` / `confidence_system` /
  `final_projection` / `simulated_trade` / `review_payload`）
- [services/projection_output_adapter.py](services/projection_output_adapter.py)
  （旧 → 8 段的翻译层）
- [services/projection_three_systems_renderer.py](services/projection_three_systems_renderer.py)
  （Final Report 内部的"三系统并列展示"渲染器）

**明确**：

> Final Report **不是**第四个预测系统。
> Final Report **是**报告编辑器 / 标准输出生成器。
> Final Report 的 `combined_user_summary` 必须可由"读三系统输出 + 排版规则"
> 重新派生，**不引入**额外判断。

**禁止**（依据 07D §5 / §6 / §7 / §8 / §11）：

- 不重新预测（不计算 most_likely_state）
- 不修改 `projection_result`
- 不修改 `exclusion_result`
- 不重算 `confidence_result`
- 不输出 hard / forced / required / trading_action / production_promotion
- 不允许 `final_report → projection / exclusion / confidence` 回流
- 不读取 future outcome 进入当次报告

**当前风险**：

- `services/final_decision.py` 已合规（11B / 12E X2 已封禁 mutation 表面），
  但**不是**唯一的"final"组装点：[services/projection_chain_contract.py:209](services/projection_chain_contract.py:209)
  的 `build_unified_projection_payload` 也是一个 payload 组装器，且与
  `final_decision` schema 不同
- `services/projection_output_contract.py` 定义的 8 段 schema 目前没有
  原生产出者，依赖 adapter 翻译
- 16C 需要选定**唯一**的 final report schema（推荐：07D 草案 +
  `projection_output_contract` 8 段作为外部对接版）

---

## 11. Branch 7：Review & Learning Layer

**职责**：

- 记录真实结果（outcome capture）
- 对答案（已结案样本 vs 当时三系统输出）
- 判断哪个系统错了（projection 错 / exclusion 错 / confidence 错估）
- 提炼 lesson（错题本）
- 下次预测前提供提醒（pre-prediction briefing）

**明确**（与 06 §6 / §7 / 07A §3.2 / 07B §3.2 / 07C §3.3 一致）：

> 复盘自学习层是**错题本**，**不是**第四个预测系统。
> 它**只能事后复盘**，**不能当次改答案**。
>
> 已结案的真实结果可以进入 Review；当次预测路径**禁止**任何 future
> outcome 回流。

**输入**：

- 历史 `projection_result` / `exclusion_result` / `confidence_result` /
  `final_report` 的快照（来自 prediction_store）
- 已结案的真实 outcome（来自 outcome_capture）
- 历史 review 记录（review_store）

**输出**：

- review record（含 hit / miss / why）
- lesson / rule memory entry
- pre-prediction briefing（向"下次"预测**展示**告警，不修改三系统输出）

**候选模块**：

- [services/outcome_capture.py](services/outcome_capture.py)
- [services/review_orchestrator.py](services/review_orchestrator.py)
- [services/review_center.py](services/review_center.py)
- [services/review_analyzer.py](services/review_analyzer.py)
- [services/review_classifier.py](services/review_classifier.py)
- [services/review_comparator.py](services/review_comparator.py)
- [services/review_agent.py](services/review_agent.py)
- [services/review_store.py](services/review_store.py)
- [services/memory_store.py](services/memory_store.py) /
  [services/memory_feedback.py](services/memory_feedback.py)
- [services/rule_lifecycle.py](services/rule_lifecycle.py) /
  [services/rule_scoring.py](services/rule_scoring.py)
- [services/projection_memory_briefing.py](services/projection_memory_briefing.py) /
  [services/pre_prediction_briefing.py](services/pre_prediction_briefing.py)
- [services/projection_review_closed_loop.py](services/projection_review_closed_loop.py)
- [services/projection_record_store.py](services/projection_record_store.py) /
  [services/prediction_store.py](services/prediction_store.py)
  （prediction_store 也可能归 Final Report 的持久化端，待 16B 决定）

**禁止**：

- 不在当次预测路径中读取未来结果
- 不直接改写 `projection_result` / `exclusion_result` / `confidence_result` /
  `final_report`
- 不强制覆盖结果
- 不输出交易动作

**当前风险**：

- `pre_prediction_briefing` 已通过 12E X1..X3 + 11D cutoff_guard
  封禁 mutation 表面，但其在 `predict.run_predict` 内仍参与
  `_apply_briefing_caution` 修改 `final_confidence`（[predict.py:1357](predict.py:1357)）。
  未来需在 16E 决定是否把 caution 移到展示层而非修改 confidence
- `rule_lifecycle` / `rule_scoring` / `active_rule_pool*` 与 promotion 模块
  共享命名空间，需独立审；`promotion_*` 已 OFFLINE_ONLY 锁定，**不**进
  Review & Learning Layer 的运行路径

---

## 12. Branch 8：Evaluation Layer

**职责**：

- 评估 projection accuracy（命中率随 regime / 结构 / 样本量分布）
- 评估 exclusion success / false_exclusion rate
- 评估 confidence calibration（level / score 与真实命中率的一致性）
- 评估 agreement / conflict performance（一致 / 冲突时的命中差异）
- 评估 **signal win-rate**

**明确**：

> 这里的 win-rate 是 **signal win-rate**（推演 / 否定 / 综合方向是否对），
> **不是 trading win-rate**（不计真实交易盈亏）。
>
> Evaluation 是**只读批处理**：消费历史 prediction snapshot + 历史 outcome，
> 产出 metrics dashboard / report；**不**回灌当次预测，**不**自动改规则。

**输入**：

- 历史 prediction snapshot（projection_result / exclusion_result /
  confidence_result / final_report 已写入 store）
- 已结案的真实 outcome
- holdout 区间策略（保留 2026-01-01 之后为 final holdout，**不**污染）

**输出**：

- accuracy / calibration / agreement / win-rate 表格
- regime-segmented metrics
- evaluation report（落 file / DB / dashboard）

**候选模块**：

- [services/historical_replay_training.py](services/historical_replay_training.py)
- [services/three_system_replay_audit.py](services/three_system_replay_audit.py)
- [services/replay_record_wiring.py](services/replay_record_wiring.py) /
  [services/replay_validation_record_adapter.py](services/replay_validation_record_adapter.py)
- [services/contract_replay_planner.py](services/contract_replay_planner.py) /
  [services/contract_replay_writer.py](services/contract_replay_writer.py)
- [services/contract_outcome_correlation.py](services/contract_outcome_correlation.py)
- [services/regime_diagnostics_dashboard.py](services/regime_diagnostics_dashboard.py)
- [services/regime_validation_helper.py](services/regime_validation_helper.py)
- [services/stats_engine.py](services/stats_engine.py)
- [services/avgo_1000day_training.py](services/avgo_1000day_training.py)
- [services/daily_training_pipeline.py](services/daily_training_pipeline.py) /
  [services/daily_training_summary.py](services/daily_training_summary.py)

**禁止**：

- 不计算真实交易收益
- 不输出 buy / sell / hold
- 不污染 2026-01-01 之后 final holdout（与 06 / 07A §3.2 / 07B §3.2 /
  07C §3.2 / 07D §3.2 一致）
- 不用 evaluation 结果当场改规则（"当场"= 在线 inference 路径；
  离线 calibration 仍允许，但其结果以"权重 / 校准表"形式回到
  Confidence System，不沿其他路径回流）

**当前风险**：

- 历史 evaluation 输出散落在 `logs/historical_training/03_fresh_replay/` /
  `logs/historical_training/exclusion_action_validation_2e/` /
  `logs/technical_features/`（已 tracked 作为 evidence）
- 4 套 untracked replay 子目录（14J / 14K 已 ignored）—— 16B / 16C
  需决定 evaluation 输出的统一存储位置 / schema

---

## 13. Branch 9：UI / Presentation Layer

**职责**：

- 展示 final report（projection / exclusion / confidence 三段并列）
- 展示三系统冲突 / 一致标注
- 展示复盘结果 / lesson / pre-prediction briefing
- 展示 evaluation summary / dashboard

**输入**：

- `final_report`（来自 Final Report Layer，**只读**）
- `review record`（来自 Review & Learning，只读）
- `evaluation report`（来自 Evaluation Layer，只读）

**输出**：浏览器渲染（Streamlit / HTML / Markdown）。

**候选模块**：

- [app.py](app.py)
- [ui/](ui/) 全部（[ui/predict_tab.py](ui/predict_tab.py) /
  [ui/home_tab.py](ui/home_tab.py) / [ui/scan_tab.py](ui/scan_tab.py) /
  [ui/research_tab.py](ui/research_tab.py) / [ui/review_tab.py](ui/review_tab.py) /
  [ui/history_tab.py](ui/history_tab.py) / [ui/inspect_tab.py](ui/inspect_tab.py) /
  [ui/control_tab.py](ui/control_tab.py) / [ui/command_bar.py](ui/command_bar.py) /
  [ui/projection_v2_renderer.py](ui/projection_v2_renderer.py) /
  [ui/protection_layer_diagnostics_renderer.py](ui/protection_layer_diagnostics_renderer.py) /
  [ui/anti_false_exclusion_display.py](ui/anti_false_exclusion_display.py) /
  [ui/exclusion_reliability_review.py](ui/exclusion_reliability_review.py) /
  [ui/big_up_contradiction_card.py](ui/big_up_contradiction_card.py) /
  [ui/soft_metadata_renderer.py](ui/soft_metadata_renderer.py) /
  [ui/labels.py](ui/labels.py)）
- [services/projection_narrative_renderer.py](services/projection_narrative_renderer.py)
  （narrative 渲染器；归属可能介于 Final Report Layer 与 UI 之间，待 16B）
- [services/ai_summary.py](services/ai_summary.py)（已 11F default-disabled）

**禁止**：

- 不生成预测
- 不重算 confidence
- 不改 final report
- 不根据展示需要改字段含义
- 不允许"UI 拼出新结论"（任何展示文本必须可在 final_report / review /
  evaluation 中找到出处）

**当前风险**：

- [ui/predict_tab.py:1410](ui/predict_tab.py:1410) 仍直调 `predict.run_predict`，
  并主显示 `final_bias` / `final_confidence` / `primary_projection` /
  `final_projection` 旧字段
- [app.py:86](app.py:86) / [app.py:1899](app.py:1899) 调用
  `build_home_terminal_orchestrator_result`，是 home 主页独立链
- UI 当前同时消费旧链字段 + V2 attachment + home_terminal 三种来源；
  16C 需选定**唯一**的"UI 读什么"

---

## 14. Temporary Migration Bridge

**说明**：

> Temporary Migration Bridge **不属于**正式 9 分支。
> 它只是迁移期兼容区。它在正式架构图中**不出现**。

**职责**：

- 兼容旧 UI / 旧 replay / 旧 tests
- 翻译字段（旧 `predict_result` ↔ 新 final_report / confidence_result /
  projection_result）
- 保护迁移期系统不崩

**候选模块**：

- [predict.py](predict.py)（含 `run_predict` legacy wrapper / 旧
  `build_primary_projection` / `apply_peer_adjustment` /
  `build_final_projection` / `_summarize` / `_apply_briefing_caution` /
  `_apply_v2_legacy_adapter_overlay`）
- [services/predict_legacy_adapter.py](services/predict_legacy_adapter.py)
  （v2 → legacy 字段翻译）
- [services/predict_legacy_v2_bridge.py](services/predict_legacy_v2_bridge.py)
  （isolated bridge helper；当前**不**被任何 active caller import）
- legacy `PredictResult` typed dict 字段（`final_bias` / `final_confidence` /
  `confidence` / `primary_projection` / `peer_adjustment` /
  `final_projection` / `path_risk` / `peer_path_risk_adjustment`）
- [services/projection_orchestrator.py](services/projection_orchestrator.py)
  （V1 orchestrator；14G / 14H 修正后明确为 KEEP_ACTIVE，但**只**为
  legacy 路径与 V2 内部回调存在；正式架构里**不**进任何分支）

**禁止**：

- 不做新判断
- 不重新计算 confidence
- 不继续扩大旧字段依赖
- 不作为未来正式主链路
- 不接 trading / hard / forced / production_promotion（12E X1..X5 +
  11G 已封禁，本蓝图重申）

**退出条件**（**全部**满足后才能解散 Bridge）：

1. UI 全部读新 final_report schema（不再用 `final_bias` / `final_confidence` /
   `primary_projection` / `final_projection` 旧字段）
2. replay 全部读新 evaluation schema（不再用 legacy `PredictResult`）
3. tests 不再依赖旧 `PredictResult` typed dict
4. `run_predict` 不再作为主入口（UI / app.py / scripts 都切到新分支入口）
5. legacy adapter / bridge 在 active path 中无 import
6. `services/projection_orchestrator.py` 不再被新链路依赖

**注**：以上**任一项**不满足，Bridge 都必须保持**可工作**且**可回滚**。

---

## 15. 模块站队标签

供 16B 使用：

| 标签 | 含义 |
|---|---|
| `CORE_DATA` | Branch 1 Data Layer |
| `CORE_FEATURE` | Branch 2 Feature Layer |
| `CORE_PROJECTION` | Branch 3 Projection System |
| `CORE_EXCLUSION` | Branch 4 Exclusion System |
| `CORE_CONFIDENCE` | Branch 5 Confidence System |
| `CORE_FINAL_REPORT` | Branch 6 Final Report Layer |
| `CORE_REVIEW_LEARNING` | Branch 7 Review & Learning Layer |
| `CORE_EVALUATION` | Branch 8 Evaluation Layer |
| `CORE_UI` | Branch 9 UI / Presentation Layer |
| `TEMP_MIGRATION_BRIDGE` | 迁移期兼容；不属正式架构；有明确退出条件 |
| `LEGACY_ACTIVE_DEPENDENCY` | 旧链仍依赖；尚不能 quarantine；优先级低于 Bridge 退出 |
| `KEEP_FROZEN_DIAGNOSTIC` | 只读冻结基线（如 continuous_smoothing v1 / v2 candidate）；不接 active path |
| `ARCHIVE` | 已 quarantine 至 `archive/legacy/...`（如 root_stubs） |
| `QUARANTINE_CANDIDATE` | 16B / 16D 评估后若无活跃依赖，应进入 archive |
| `DELETE_LATER` | 16D 之后可安全删除（只删，不重写） |
| `UNKNOWN_REVIEW_REQUIRED` | 16B 需人工审视，无法自动归类 |

> 站队规则（16B 起严守）：
> - 一个模块**只能**有一个主标签；不允许"同时是 CORE_PROJECTION 和 CORE_EXCLUSION"
> - `TEMP_MIGRATION_BRIDGE` 必须配套 §14 退出条件
> - `KEEP_FROZEN_DIAGNOSTIC` 必须有 frozen marker（`_DEPRECATED.md` /
>   tasks/record 锚点）
> - 站队结果必须**可追溯**：每个标签来源必须能在 16B / 16C / 16D 文档
>   找到出处

---

## 16. 初步模块站队草案

> **草案性质**：本表是 16A 蓝图视角下的**初步**判断；最终归属由 16B
> Module Stand-up / Ownership Inventory 在每个模块逐一审视后确定。
> 本表**不是**最终归属；如发现冲突，以 16B 输出为准。

| module | target branch | status | reason | risk |
|---|---|---|---|---|
| [services/main_projection_layer.py](services/main_projection_layer.py) | Branch 3 Projection | `CORE_PROJECTION` | 五状态推演实现；07A 草案最接近的活模块 | 反向 import exclusion_layer.build_peer_alignment；保留 exclusion_result 形参；schema key 需对齐 07A |
| [services/exclusion_layer.py](services/exclusion_layer.py) | Branch 4 Exclusion | `CORE_EXCLUSION` | 否定层实现；不 read projection；feature-only 输入 | `build_peer_alignment` 应迁出到 Feature Layer；输出 schema 需对齐 07B |
| [services/confidence_evaluator.py](services/confidence_evaluator.py) | Branch 5 Confidence | `CORE_CONFIDENCE` | 边界合规（read-only / forbidden_fields / 无 mutation） | agreement key 与 main_projection / exclusion 不对齐；calibration_context 未接入；UI 未读 |
| [services/final_decision.py](services/final_decision.py) | Branch 6 Final Report | `CORE_FINAL_REPORT` | strict passthrough：`final_direction = primary_direction`；confidence 来源 `confidence_result`；exclusion display-only | schema 与 07D 草案 / projection_output_contract 8 段未统一 |
| [services/projection_orchestrator_v2.py](services/projection_orchestrator_v2.py) | (跨分支) | `LEGACY_ACTIVE_DEPENDENCY` | 当前 V2 编排器；通过 projection_orchestrator 回调 run_predict | 不属任何单一分支；16D 应拆成 Feature → 三系统 → Final Report 的明确链路 |
| [services/home_terminal_orchestrator.py](services/home_terminal_orchestrator.py) | (跨分支) | `LEGACY_ACTIVE_DEPENDENCY` | 主页主链；feature → exclusion → projection → consistency → confidence → log | 不属任何单一分支；与 v2 路径并存；16C 需决定主入口 |
| [services/projection_orchestrator.py](services/projection_orchestrator.py) | (跨分支 / Bridge 内) | `TEMP_MIGRATION_BRIDGE` | V1 orchestrator；被 predict.run_predict legacy 路径用；被 V2 内部 import | 14G/14H 已确认 KEEP_ACTIVE，但**正式架构中不属任何分支**；Bridge 退出条件之一 |
| [predict.py](predict.py) | Bridge | `TEMP_MIGRATION_BRIDGE` | legacy wrapper；run_predict 默认走旧链 | 仍包含 build_primary_projection / apply_peer_adjustment / build_final_projection 旧推演逻辑；UI 主入口 |
| [services/predict_legacy_adapter.py](services/predict_legacy_adapter.py) | Bridge | `TEMP_MIGRATION_BRIDGE` | v2_payload → legacy 字段翻译（X4-A） | Bridge 退出条件之一 |
| [services/predict_legacy_v2_bridge.py](services/predict_legacy_v2_bridge.py) | Bridge | `TEMP_MIGRATION_BRIDGE` | isolated bridge helper（X4-C）；当前无 active import | Bridge 退出条件之一 |
| [ui/predict_tab.py](ui/predict_tab.py) | Branch 9 UI | `CORE_UI` | 主预测 tab 渲染 | 当前直调 run_predict + 读旧字段；16C 需切到 final_report schema |
| [app.py](app.py) | Branch 9 UI | `CORE_UI` | Streamlit 主入口 | hard rule 3 锁定最小改动；同时调 home_terminal 与 ui/* |
| [services/projection_output_contract.py](services/projection_output_contract.py) | Branch 6 Final Report | `CORE_FINAL_REPORT` | 8 段 schema validator | 暂无原生产出者；16C 决定是否作为外部对接 schema |
| [services/projection_chain_contract.py](services/projection_chain_contract.py) | (跨 Branch 2 / 6) | `UNKNOWN_REVIEW_REQUIRED` | 同时含 feature payload helper 与 unified payload assembler | 16B 拆分：feature 部分 → Branch 2，payload assembler 部分 → Branch 6 |
| `services/continuous_smoothing_candidate*` | (无) | `KEEP_FROZEN_DIAGNOSTIC` | 3R-3 abandon as candidate；frozen baseline | 06 §8 / 07B §11 / 07C §12 / 07D §12 严禁复活作为 active candidate |
| [archive/legacy/root_stubs/](archive/legacy/root_stubs) | (无) | `ARCHIVE` | 14D 已 quarantine（confidence_engine / contradiction_engine / risk_model） | 含 `_DEPRECATED.md`；不再 import |
| [records/](records) | Branch 8 Evaluation（候选） | `UNKNOWN_REVIEW_REQUIRED` | 历史 prediction / outcome 记录 | 16B 需审清是 prediction store 持久化（Final Report 出口）还是 evaluation 输入 |
| `services/review_*` / [services/outcome_capture.py](services/outcome_capture.py) / [services/rule_lifecycle.py](services/rule_lifecycle.py) / [services/rule_scoring.py](services/rule_scoring.py) / [services/memory_store.py](services/memory_store.py) / [services/memory_feedback.py](services/memory_feedback.py) / [services/pre_prediction_briefing.py](services/pre_prediction_briefing.py) / [services/projection_memory_briefing.py](services/projection_memory_briefing.py) / [services/projection_review_closed_loop.py](services/projection_review_closed_loop.py) | Branch 7 Review & Learning | `CORE_REVIEW_LEARNING` | 复盘 / 错题本 / 提醒 | pre_prediction_briefing 仍参与 `_apply_briefing_caution` 修改 final_confidence；16E 需移到展示层 |
| [services/active_rule_pool.py](services/active_rule_pool.py) / `*_calibration` / `*_drift` / `*_export` / `*_validation` | (跨分支：Branch 5 Confidence 数据准备 + Branch 7 Review) | `UNKNOWN_REVIEW_REQUIRED` | 与 promotion 命名空间共享；归属需 16B 拆分 | promotion 三模块（`promotion_*`）已 OFFLINE_ONLY，**不**进 active path |
| [services/projection_narrative_renderer.py](services/projection_narrative_renderer.py) / [services/projection_three_systems_renderer.py](services/projection_three_systems_renderer.py) | (跨 Branch 6 / 9) | `UNKNOWN_REVIEW_REQUIRED` | 渲染器；逻辑可能介于 Final Report 与 UI 之间 | 16B 决定边界 |

> 缺漏 / 未列出的模块（如 `services/anti_false_exclusion_*` /
> `services/big_up_contradiction_card.py` / `services/inspect_analysis.py` /
> `services/state_label.py` / `services/five_state_margin_policy.py` /
> `services/protection_layer_diagnostics.py` 等）由 16B Inventory 逐个落位。

---

## 17. 后续执行路线

| Step | 内容 | 性质 |
|---|---|---|
| **16A**（本轮） | Architecture Reset Blueprint | 文档 |
| **16B** | Module Stand-up / Ownership Inventory | 文档 |
| **16C** | Target Dataflow & Contract Decision（最终 schema 唯一化） | 文档 |
| **16D** | Isolation / Quarantine Plan（Bridge 模块边界 + frozen marker） | 文档 |
| **16E** | Core Chain Refactor Plan（PR 拆分 / 顺序 / 回滚） | 文档 |
| **16F** | 第一个代码 PR（按 16E 计划） | 代码 |

**明确**：

> 战略上大改。
> 执行上小步。
> 每一步都要可回滚。

每步**单独**走 plan → builder → reviewer → tester；**不**借任一步顺手
解锁 3R-5 / 3R-6、trading、default V2、promotion、continuous_smoothing 复活。

---

## 18. 不允许事项

本轮严守以下边界：

- ❌ 不进入 3R-5 / 3R-6
- ❌ 不接 trading
- ❌ 不输出 buy / sell / hold
- ❌ 不输出 hard / forced / required
- ❌ 不直接删除 legacy modules
- ❌ 不直接 default migrate `run_predict` 到 V2
- ❌ 不直接跑 final holdout（2026-01-01 之后窗口保留）
- ❌ 不把 Temporary Migration Bridge 当正式架构
- ❌ 不复活 `continuous_smoothing` 作为 active candidate
- ❌ 不重新引入 archive/legacy/root_stubs 已 quarantine 的 v1 stubs
- ❌ 不允许"先改一改让它过 contract"的妥协式重构（07D §15 已锁）
- ❌ 不允许 evaluation 结果当场改规则（仅离线 calibration 经"权重 / 校准表"
  形式回到 Confidence System）

---

## 19. 推荐下一步

**推荐**：

> **Step 16B：Module Stand-up / Ownership Inventory**

**目标**：

让所有关键模块**正式站队**。每个模块（services/*.py / ui/*.py / 顶层 .py）
都标上 §15 的标签之一，并写明：

- target branch（如属正式分支）
- 当前 active caller / dependency
- 与 contract（07A / 07B / 07C / 07D）对照下的合规度
- 风险（如 schema mismatch / import 反向 / 软边界）
- 16B 之后建议的处置（保留 / 重构 / 抽出 / 标记 frozen / archive / delete）

**不**推荐：

- 不推荐直接进 16C / 16D（必须先有完整的 Module Inventory）
- 不推荐借 16B 顺手做代码改动（16F 才是第一个代码 PR）

---

## 20. 严守边界

本轮 Step 16A **只**写 architecture blueprint：

- ❌ 未改代码（无 `.py` 文件被修改）
- ❌ 未新增测试（`tests/` 字节不变）
- ❌ 未移动文件
- ❌ 未删除文件
- ❌ 未修改 `.gitignore`
- ❌ 未处理 handoff（`.claude/handoffs/task_089_post_pr_cleanup.md` 字节
  不变，仍按 14L A2 / 14M / 15 §2 deliberate keep local）
- ❌ 未处理 logs / DB backup / `.claude/worktrees/`
- ❌ 未跑 replay
- ❌ 未跑 validation
- ❌ 未跑 historical evaluation
- ❌ 未写 DB
- ❌ 未改 DB schema
- ❌ 未默认迁移 `run_predict` 到 V2
- ❌ 未接 trading
- ❌ 未输出 buy / sell / hold
- ❌ 未输出 hard / forced / required
- ❌ 未启用任何 candidate / 未复活 `continuous_smoothing`
- ❌ 未触碰 RISK-1 / RISK-2 / RISK-3 / RISK-7 / RISK-8 / RISK-9 / RISK-10
- ❌ 未进入 3R-5 / 3R-6
- ❌ 未 commit / 未 push（按本轮指令）

唯一新增文件：[tasks/record_16a_architecture_reset_blueprint.md](tasks/record_16a_architecture_reset_blueprint.md)
（本文件）。

后续修改路径：任何对 §3 主干定义、§4 9 分支、§5–§13 各分支契约、
§14 Bridge 退出条件、§15 标签、§16 初步站队、§17 后续路线、§18 禁止事项
的调整，都必须**显式更新本文件**；同时检查是否需要同步更新 06 / 07A / 07B /
07C / 07D / 13 / 14A–14M / 15。
