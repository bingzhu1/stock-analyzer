# 16C记录：Target Dataflow & Contract Decision

> 本记录是 **Step 16C：未来目标数据流与标准输出契约决策**。
> 1.0 canonical / 16A blueprint / 16B inventory 已全部入 main
> （main 最新 commit `bdd1314`）。本轮基于这三份文档，**决定**：
>
> 1. 未来正式数据流的唯一形状
> 2. 未来唯一标准输出契约
> 3. `predict.py` 的降级方向
> 4. UI / Evaluation / Review & Learning 各自的未来读取路径
> 5. Temporary Migration Bridge 的退出路线
>
> 本轮**只**写决策文档：未改业务代码、未新增测试、未删除文件、
> 未移动文件、未修改 `.gitignore`、未处理 handoff、未处理 logs /
> DB backup / `.claude/worktrees/`、未跑 replay / validation /
> historical evaluation、未写 DB / 未改 DB schema、未默认迁移
> `run_predict` 到 V2、未接 trading、未输出 buy / sell / hold /
> hard / forced / required、未进入 3R-5 / 3R-6、未 commit / 未 push。
>
> 唯一 deliverable：本文件。

---

## 1. Step 16C 目的

本轮**决定**未来系统的两件事：

1. **唯一目标数据流**（哪条 pipeline 是事实标准）
2. **唯一标准输出契约**（什么 payload 是事实标准）

这是从"模块归属"（16B）进入"主链路 + schema"决策的关键一步。
本轮**不**改代码，**不**直接切主入口，**不**默认迁移 V2，**不**删除
legacy module。所有落地动作留待 16D（Isolation / Quarantine Plan）/
16E（Core Chain Refactor Plan）/ 16F（第一个代码 PR）。

> **本文件的性质是"决定"，不是"提议"**。决定生效后，1.0 §14 的
> 冲突仲裁规则启动：旧 records 中与本决定冲突的字段命名 / 主入口
> 选项 / schema 选择，**以 16C 为准**。

---

## 2. 当前前置条件

| 项 | 状态 |
|---|---|
| 1.0 canonical principles 已入 main | ✅ commit `5c209bb` |
| 16A architecture reset blueprint 已入 main | ✅ commit `9b98ad5` |
| 16B module standup ownership inventory 已入 main | ✅ commit `bdd1314` |
| Step 12 boundary fixes / Step 13 regression / Step 14 cleanup / Step 15 signoff | ✅ 全部入 main |
| main 最新 commit | `bdd1314` |
| worktree 唯一 deliberate untracked | `.claude/handoffs/task_089_post_pr_cleanup.md` |
| 战略阶段 | 从模块层（16B）→ 主链路 + schema 决策（16C 本轮）|
| 3R-5 / 3R-6 | ❌ 仍然不允许进入（1.0 §12 / 16A §18） |

16B 已识别但**未决定**的关键问题（本轮回答）：

1. 哪个 orchestrator 是未来主入口
2. final_report schema 是否成为唯一事实标准
3. `predict.py` 如何降级为 bridge
4. UI 何时迁移到新 schema
5. evaluation 读取哪个 payload
6. `build_peer_alignment` / `consistency_layer` / `peer_adjustment` 归位
7. 15d 标准窗口何时迁移
8. 统一 evaluation 输出存储 / schema

---

## 3. 未来目标数据流（决定）

### 3.1 决定的数据流形状

```
                    Branch 1  Data Layer
                           │
                           ▼
                    Branch 2  Feature Layer
                       (feature_payload)
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
 Branch 3 Projection  Branch 4 Exclusion  Branch 2 Feature
     (only)              (only)         summary (read-only
        │                  │           by Confidence)
        │                  │                  │
        └────────┬─────────┘                  │
                 │                            │
                 ▼                            │
       projection_result + exclusion_result  │
                 │                            │
                 └────────────┬───────────────┘
                              ▼
                  Branch 5  Confidence System
                       (confidence_result)
                              │
                              ▼
                  Branch 6  Final Report Layer
                  ① 汇总 ② 展示 ③ 不 mutate
                              │
       ┌──────────────────────┼──────────────────────┐
       ▼                      ▼                      ▼
 Branch 7 Review &      Branch 8 Evaluation    Branch 9 UI /
 Learning（事后）        （signal-level）        Presentation
```

### 3.2 关键约束

- **Projection 与 Exclusion 并行**：二者**同时**读 `feature_payload`，
  彼此**不互读**（07A §3.2 / 07B §3.2 / 07E §9 矩阵）
- **Confidence 读三件**：`projection_result` / `exclusion_result` /
  `feature_payload` 的 summary 字段 + 离线 calibration 权重表（07C §3.1）
- **Final Report 只汇总**：从三系统 + `feature_payload` 的 metadata
  组装；**不 mutate** 任一上游（07D §3.3 / §5）
- **Review / Evaluation / UI 全部读标准 payload**：**禁止**任何一方
  直接读 `predict_result` / `final_bias` / `final_confidence` /
  `primary_projection` / `final_projection` 等 Bridge 字段
- **数据流方向严格**（与 07E §9 矩阵闭合）：
  - 上游 → 下游（Data → Feature → 三系统 → Final Report → Review / Evaluation / UI）
  - 下游 **不**回流到上游
  - 三系统两两 **不互读**

### 3.3 与现行实现的差距

| 当前实现 | 与目标数据流的差距 |
|---|---|
| `services/main_projection_layer.py:18` 反向 import `services/exclusion_layer.build_peer_alignment` | 违反"Projection 不读 Exclusion 模块"。需把 `build_peer_alignment` 迁出到 Branch 2 Feature Layer |
| `build_main_projection_layer` / `run_main_projection_layer` 仍接受 `exclusion_result` 形参（[main_projection_layer.py:286](services/main_projection_layer.py:286), [298](services/main_projection_layer.py:298)） | 软边界；删形参 |
| `services/confidence_evaluator._compute_agreement` 期望 `most_likely_state` / `ranked_states` / `most_unlikely_state` / `ranked_unlikely_states`；当前 main_projection / exclusion 不输出这些 key | schema 不对齐；agreement 长期 unknown |
| home_terminal / V2 调用 `build_confidence_result` 时**未传** `calibration_context` | confidence level 长期 unknown |
| `services/projection_orchestrator_v2.py:16` 仍 `from services.projection_orchestrator import build_projection_orchestrator_result`（V1 反向回调） | V2 不直连 9 分支，仍依赖 V1 → `predict.run_predict` |
| `services/contract_replay_writer.py:83, 475` 直调 `predict.run_predict` | Evaluation 仍消费 Bridge schema |
| `ui/predict_tab.py:1410` 调 `predict.run_predict`，主面板读 `final_bias` / `final_confidence` / `primary_projection` / `final_projection` | UI 仍消费 Bridge schema |

→ §11 退出路线分阶段消解。

---

## 4. 未来主入口决策（决定）

### 4.1 候选对比

| 候选 | 现状 | 与目标数据流的距离 | 优势 | 劣势 |
|---|---|---|---|---|
| `services/projection_orchestrator_v2.py` | 当前 V2 主链；含 preflight / primary / peer / historical / standardized chain / final_decision | 中 | 已对接 confidence_evaluator + final_decision；接 9 分支语义最近 | 仍**反向回调** V1 (`projection_orchestrator.build_projection_orchestrator_result`)；含 `primary_20day_analysis` / `peer_adjustment` / `historical_probability` 三段 V2 内部步骤，与 9 分支不一一对应 |
| `services/home_terminal_orchestrator.py` | app.py 主页主链；feature → exclusion → projection → consistency → confidence → log | 近 | 直接走 9 分支语义（无 V1 回调）；最干净 | 范围较小（home 视图）；未传 calibration_context；schema 仍是 chain_contract `unified_payload` 而非 final_report |
| `services/projection_orchestrator.py` | V1 orchestrator；调 `predict.run_predict` | 远 | — | 包含 Bridge 路径；不能作为未来主入口 |
| `predict.py` | legacy wrapper；UI / replay 主入口 | 远 | — | Bridge schema；不能作为未来主入口 |
| **新建 `services/architecture_orchestrator.py`** | 不存在；依据 1.0 / 16A / 16C 重新构造 | 0 | 直接 9 分支链路；schema 严格对齐 07A–07D；无 legacy 包袱 | 需要 16E refactor PR；要承接现有所有 caller |

### 4.2 决定

> **未来正式主入口 = `services/architecture_orchestrator.py`（新建，16E 起落地）。**
>
> 1. **`services/architecture_orchestrator.py` 是未来唯一主入口**。
>    职责：feature_payload 构造 → Projection / Exclusion 并行 →
>    Confidence → Final Report → 持久化（prediction_store / log_store）。
>    schema 严格对齐 §5 标准 payload。
> 2. **`services/projection_orchestrator_v2.py` 进入 LEGACY_ACTIVE_DEPENDENCY**。
>    在 16E 完成前作为现行 V2 主链保留；**禁止**对它做新功能；
>    16E 起逐步迁移现有调用方（`projection_entrypoint` /
>    `projection_v2_adapter` / `historical_replay_training` /
>    `save_projection_records_smoke.py`）到 `architecture_orchestrator`。
>    迁移完成后整体 archive。
3. **`services/home_terminal_orchestrator.py` 降级为 UI orchestration layer**。
   职责仅限 app.py 主页**调用** `architecture_orchestrator` 并在
   home tab 上做**展示侧**编排（不再持有"feature → 三系统 → confidence → log"
   的核心逻辑）。16E 期间内部实现替换为对 `architecture_orchestrator` 的薄包装；
   schema 转为 final_report。**不**作为未来正式主入口（避免双链）。
4. **`services/projection_orchestrator.py` 永久标 `LEGACY_ACTIVE_DEPENDENCY`**。
   不进 9 分支正式架构；Bridge 退出条件 #6 满足后整体 archive。
5. **`predict.py` 永久标 `TEMP_MIGRATION_BRIDGE`**。
   降级方向见 §7。

### 4.3 决定生效的边界

- 16C 决定**不**直接修改任何代码
- `architecture_orchestrator.py` 的具体函数签名 / 模块布局 / 内部步骤拆分留待
  16E（Core Chain Refactor Plan）
- 16D（Isolation / Quarantine Plan）需要在 V2 / home_terminal /
  projection_orchestrator / predict.py 上挂明确的"deprecated since 16C"
  marker（仅文档级标记，不删 / 不移动）

---

## 5. 未来唯一标准输出契约（决定）

### 5.1 标准 payload 名称

> **采用 `standard_projection_payload.v1`** 作为唯一标准输出 payload 名称。
>
> 理由：
> - "architecture_payload" 名称含义太宽，不能精确指向"AVGO 当次预测"
> - "standard_projection_payload" 与 1.0 / 16A 中"projection / exclusion /
>   confidence / final_report 共同构成的顶层 payload"语义一致
> - schema_version 沿用 07A–07D 的 `*_result.v1` 命名约定 → 顶层用 `.v1`

### 5.2 顶层结构

```jsonc
standard_projection_payload.v1:
{
  "schema_version": "standard_projection_payload.v1",
  "metadata": {
    "symbol": "AVGO",
    "analysis_date": "<YYYY-MM-DD>",        // 数据截止日
    "target_date": "<YYYY-MM-DD>",          // 目标交易日
    "produced_at": "<ISO timestamp>",
    "orchestrator_version": "architecture_orchestrator.v1",
    "data_window_days": 15,                 // 1.0 / 07A §3.1 锁定 15
    "non_mutation_confirmations": {
      "projection_result_mutated": false,
      "exclusion_result_mutated": false,
      "confidence_result_mutated": false,
      "final_report_mutated": false
    }
  },
  "feature_payload": { ... },               // Branch 2 输出（含 peer_alignment）
  "projection_result": { ... },             // Branch 3 输出，schema = projection_system_result.v1
  "exclusion_result": { ... },              // Branch 4 输出，schema = exclusion_system_result.v1
  "confidence_result": { ... },             // Branch 5 输出，schema = confidence_system_result.v1
  "final_report": { ... },                  // Branch 6 输出，schema = final_report_aggregator_result.v1
  "review_stub": { ... },                   // Branch 7 占位（当次预测时空）
  "evaluation_stub": { ... },               // Branch 8 占位（当次预测时空）
  "compatibility_metadata": { ... }         // Bridge 期间含 legacy 字段映射；Bridge 退出后整段删除
}
```

### 5.3 字段语义边界

| 顶层字段 | 谁写 | 谁读 | 是否 mutable | 备注 |
|---|---|---|---|---|
| `metadata` | architecture_orchestrator | 全部下游 | ❌ | `data_window_days = 15` 强制 |
| `feature_payload` | Branch 2（Feature Layer） | Projection / Exclusion / Confidence（summary） / Final Report（display） | ❌ | 含 `peer_alignment` |
| `projection_result` | Branch 3（Projection） | Confidence（read-only）/ Final Report（display） | ❌ | 不读 exclusion / confidence |
| `exclusion_result` | Branch 4（Exclusion） | Confidence（read-only）/ Final Report（display） | ❌ | 不读 projection / confidence / final_report |
| `confidence_result` | Branch 5（Confidence） | Final Report（display） | ❌ | 只读评价 projection / exclusion |
| `final_report` | Branch 6（Final Report Layer） | Review / Evaluation / UI | ❌ | 含 `non_mutation_confirmations` 自检 |
| `review_stub` | Branch 7（事后填） | UI | ✅（仅事后） | 当次预测时为占位空对象 |
| `evaluation_stub` | Branch 8（批处理填） | UI | ✅（仅离线批处理） | 当次预测时为占位空对象 |
| `compatibility_metadata` | architecture_orchestrator + Bridge | Bridge / legacy callers | ⚠️ Bridge only | 退出后整段删除（不进 v2） |

### 5.4 旧 Bridge 字段不进未来标准

> 1.0 §6.4 / 16B §4.1.10 已锁：旧 `PredictResult` 字段（`final_bias` /
> `final_confidence` / `confidence` / `primary_projection` /
> `peer_adjustment` / `final_projection` / `path_risk` /
> `peer_path_risk_adjustment`）**不**作为 `standard_projection_payload.v1`
> 的字段。它们只能存在于 `compatibility_metadata.legacy_predict_result`
> 子段；Bridge 退出后整段删除。

### 5.5 8 段外部对接 schema 的位置

`services/projection_output_contract.py` 定义的 8 段
（`current_structure` / `avgo_primary_projection` /
`peer_confirmation_adjustment` / `exclusion_system` /
`confidence_system` / `final_projection` / `simulated_trade` /
`review_payload`）**不**作为未来内部主 schema，而是**外部对接 schema**：

> 决定：**`standard_projection_payload.v1` 为内部事实标准；
> `projection_output_contract` 8 段为外部对接 schema**。
>
> - 内部所有模块（Projection / Exclusion / Confidence / Final Report /
>   Review / Evaluation / UI）只读 `standard_projection_payload.v1`
> - 8 段格式由 `services/projection_output_adapter.py` 在 Final Report
>   出口翻译产生（仅当外部对接需要时）
> - 8 段中 `simulated_trade` / 任何 trading-action 字段**永久禁止**
>   生成 active 内容（与 1.0 §7 / §13 一致）

---

## 6. 三系统标准字段（决定）

> 与 07A–07D 草案对齐；本轮**确认**为 `standard_projection_payload.v1`
> 内部 schema 的强制字段。

### 6.1 `projection_result`（schema_version `projection_system_result.v1`）

**必含字段**：

| 字段 | 类型 | 说明 |
|---|---|---|
| `schema_version` | str | `"projection_system_result.v1"` |
| `system_name` | str | `"projection_system"` |
| `question_answered` | str | `"most_likely_state"` |
| `most_likely_state` | enum | 五状态之一：大涨 / 小涨 / 震荡 / 小跌 / 大跌 |
| `ranked_states` | list[str] | 五状态完整排序（推演视角） |
| `state_probabilities` | dict[str, float] | 五状态概率分布（每个 ∈ [0, 1]，总和 ≈ 1） |
| `evidence` | list[str] | `key_supporting_signals` + `key_risk_signals` 的合并展示版（中文短句） |
| `raw_score` | float \| null | 推演内部连续打分（null 允许） |
| `primary_reasoning` | list[str] | 驱动 most_likely 的核心理由 |
| `uncertainty_notes` | list[str] | 自评不确定性（**不是** confidence；不允许量化为 score） |
| `raw_evidence_refs` | list[str] | 原始证据指针 |

**禁字段**（来自 07A §5）：`most_unlikely_state` / `confidence_score` /
`confidence_level` / `final_confidence` / `hard_exclusion` /
`forced_exclusion` / `required_decision` / `trading_action` /
`buy` / `sell` / `hold` / `simulated_trade` / `final_report_mutation` /
任何 `exclusion_*` 字段。

### 6.2 `exclusion_result`（schema_version `exclusion_system_result.v1`）

**必含字段**：

| 字段 | 类型 | 说明 |
|---|---|---|
| `schema_version` | str | `"exclusion_system_result.v1"` |
| `system_name` | str | `"exclusion_system"` |
| `question_answered` | str | `"most_unlikely_state"` |
| `most_unlikely_state` | enum | 五状态之一 |
| `ranked_unlikely_states` | list[str] | 五状态完整排序（否定视角） |
| `excluded_states` | list[str] | 该次否定明确排除的状态集合（可空） |
| `false_exclusion_risk` | dict | `{level, score, reasoning}`；自评"我也可能错" |
| `evidence` | list[str] | `key_exclusion_signals` + `key_counter_signals` 的合并展示版 |
| `triggered_rules` | list[str] | 命中的规则名称 |
| `primary_exclusion_reasoning` | list[str] | 驱动 most_unlikely 的核心理由 |
| `rare_event_evidence` | list[str] | 历史稀有性证据 |
| `historical_non_occurrence_summary` | dict | regime + 样本量 + 未发生率 |
| `peer_non_confirmation_summary` | dict | NVDA / SOXX / QQQ 非确认 |
| `uncertainty_notes` | list[str] | 自评不确定性 |
| `raw_evidence_refs` | list[str] | 原始证据指针 |

**禁字段**（来自 07B §5）：`most_likely_state` / `projection_*` mutation /
`confidence_*` / `final_confidence` / `hard_exclusion` /
`forced_exclusion` / `required_decision` / `trading_action` /
`buy` / `sell` / `hold` / `simulated_trade` / `final_report_mutation`。

### 6.3 `confidence_result`（schema_version `confidence_system_result.v1`）

**必含字段**：

| 字段 | 类型 | 说明 |
|---|---|---|
| `schema_version` | str | `"confidence_system_result.v1"` |
| `system_name` | str | `"confidence_system"` |
| `question_answered` | str | `"system_reliability_evaluation"` |
| `projection_confidence` | dict | `{level, score, reasoning}` |
| `exclusion_confidence` | dict | `{level, score, reasoning}` |
| `agreement_status` | enum | `aligned / partial_conflict / strong_conflict / unknown` |
| `conflict_level` | enum | `none / low / medium / high / unknown` |
| `combined_confidence` | dict | `{level, score, reasoning}` —— 仅展示，不回写 |
| `calibration_notes` | list[str] | 校准 / 漂移说明 |
| `confidence_reasoning` | list[str] | 综合评价 |
| `reliability_warnings` | list[str] | 可靠性告警 |
| `sample_size_notes` | list[str] | 样本量说明 |
| `raw_evidence_refs` | list[str] | 原始证据指针 |
| `non_mutation_confirmations` | dict | `{projection_result_mutated, exclusion_result_mutated}` |

**禁字段**（来自 07C §5 / `_FORBIDDEN_FIELDS`）：`most_likely_state` /
`most_unlikely_state` / `modified_projection` / `modified_exclusion` /
`projection_correction` / `exclusion_correction` / `hard_exclusion` /
`forced_exclusion` / `required_decision` / `trading_action` / `buy` /
`sell` / `hold` / `simulated_trade` / `no_trade` / `final_report_mutation` /
`production_promotion` / `_PROTECTION_LAYER_CONNECTED`。

> **关键修复决定**（与 16B §5.5 一致）：
> 1. `_compute_agreement` 必须读 `projection_result.most_likely_state` /
>    `projection_result.ranked_states` 和 `exclusion_result.most_unlikely_state` /
>    `exclusion_result.ranked_unlikely_states`，**不再**读 `predicted_top1.state` /
>    `triggered_rule`。这是 schema 对齐决定，落地在 16E。
> 2. `architecture_orchestrator` 必须传入 `calibration_context`。
>    在 calibration table 未接入前，`{"ready": False}` 是 explicit
>    fallback，**不**允许 silent default。

---

## 7. Final Report 决策（决定）

### 7.1 性质

> **Final Report 是标准展示报告，不是第四个预测系统**。
> 它**只能**：①汇总三系统 ②展示冲突 ③展示风险 ④展示证据。
> 它**不能**：改 projection / 改 exclusion / 重算 confidence / 输出
> hard / forced / required / trading。

### 7.2 schema

`final_report` 字段对齐 07D §9 `final_report_aggregator_result.v1` 草案：

```jsonc
final_report:
{
  "schema_version": "final_report_aggregator_result.v1",
  "system_name": "final_report_aggregator",
  "question_answered": "aggregate_three_system_outputs",
  "projection_section": { source_schema_version, most_likely_state, ranked_states, display_summary },
  "exclusion_section":  { source_schema_version, most_unlikely_state, ranked_unlikely_states, display_summary },
  "confidence_section": { source_schema_version, projection_confidence, exclusion_confidence, combined_confidence, display_summary },
  "agreement_or_conflict_section": { agreement_status, conflict_level, display_summary },
  "combined_user_summary": "<plain text, every sentence must be derivable from upstream>",
  "risk_disclosure": ["..."],
  "evidence_summary": ["..."],
  "raw_evidence_refs": ["..."],
  "non_mutation_confirmations": { projection_result_mutated: false, exclusion_result_mutated: false, confidence_result_mutated: false }
}
```

### 7.3 实现承接

- **当次预测路径**：`services/final_decision.py` 已实现 strict passthrough
  （`final_direction = primary_direction`；`final_confidence` 来自
  `confidence_result.combined_confidence.level`；exclusion display-only）
- **16E 起**：`final_decision.py` 改名 / 重组为 Branch 6 `final_report`
  生成器（输出 schema 严格对齐 07D §9 草案），同时移除现有"final
  decision"语义（避免与"决策"混淆）
- **8 段外部对接**：保留 `services/projection_output_adapter.py` +
  `services/projection_output_contract.py`，仅在 Final Report 出口被
  显式调用时翻译产生 8 段格式（默认不生成）

### 7.4 `consistency_layer` 归位（决定）

> **`services/consistency_layer.py` 在 16E 起合并到 `confidence_evaluator`**。
>
> 理由：07C §10 / 07E §9 已经把"agreement / conflict"明确归 Confidence
> System；保留独立的 `consistency_layer` 会造成职责重叠 + 双源真相。
> 16E 实现层把 `consistency_layer.build_consistency_layer` 的逻辑吸收到
> `confidence_evaluator._compute_agreement` 与 `_combine_confidence`，
> 然后 archive `consistency_layer.py`。

### 7.5 `peer_alignment` / `peer_adjustment` 归位（决定）

> **`build_peer_alignment` 在 16E 迁出到 Branch 2**（独立模块
> `services/peer_alignment.py`，由 Projection / Exclusion / Final Report
> 都从 Feature Layer import）。
>
> **`services/peer_adjustment.py` 在 16E 起拆解**：
> - peer 信号生成 → 并入 Branch 2（feature_payload.peer_alignment 子段）
> - "peer 调整推演方向"语义被 1.0 §6 / §8 / 07A §3 否决
>   （peer 是 Feature 输入，不是"主推演后再调整"）
> - 16E 期间 `peer_adjustment.py` 标 `LEGACY_ACTIVE_DEPENDENCY`，
>   逐步迁移；Bridge 退出后 archive

### 7.6 `_apply_briefing_caution` 归位（决定）

> **`predict.py:1357 _apply_briefing_caution` 在 16E 移除**。
>
> caution 信号属 Branch 7 Review & Learning（`pre_prediction_briefing`），
> **不**应该 mutate `final_confidence`。16E 把 caution 改为 Branch 6
> Final Report Layer 的**展示标注**：在 `final_report.confidence_section`
> 增加 `pre_prediction_caution` 字段，由 UI 展示，不修改 `confidence_result`。

---

## 8. UI 未来读取路径（决定）

### 8.1 决定

> **UI 未来只读 `standard_projection_payload.v1`**：
> - 主面板字段全部读 `final_report.projection_section` /
>   `exclusion_section` / `confidence_section` / `agreement_or_conflict_section` /
>   `combined_user_summary`
> - 不再读 `predict_result.final_bias` / `final_confidence` /
>   `primary_projection` / `final_projection`

### 8.2 迁移目标

| 文件 | 当前 | 16E 之后 |
|---|---|---|
| [ui/predict_tab.py:1410](ui/predict_tab.py:1410) | `predict_result = run_predict(...)` | 调 `architecture_orchestrator` 取 `standard_projection_payload`；从 `payload.final_report` 渲染 |
| `ui/predict_tab.py` 主面板 metric / panel | 读 `final_bias` / `final_confidence` / `primary_projection` / `final_projection` | 读 `final_report.projection_section.most_likely_state` / `confidence_section.combined_confidence.level` / `agreement_or_conflict_section.conflict_level` |
| `ui/predict_tab.py:_render_confidence_three_columns` | 读 `predict_result["projection_three_systems"]["confidence_evaluator"]` | 直接读 `payload.confidence_result` |
| `ui/home_tab.py` / `ui/history_tab.py` / `ui/review_tab.py` 等 | 读 prediction_store + review_analyzer + pre_prediction_briefing | 同上接口；store 持久化层切换到 `standard_projection_payload.v1` |
| `ui/projection_v2_renderer.py` | V2 raw 渲染 | 16E 改名为 `final_report_renderer`；读 `final_report` 段 |

### 8.3 Bridge 期间的 UI

Bridge 退出条件 #1 满足前，UI 仍可走 `predict.run_predict`，但**新功能
禁止**新增对 `final_bias` / `final_confidence` / `primary_projection` /
`final_projection` 字段的读取。

---

## 9. Evaluation 未来读取路径（决定）

### 9.1 决定

> **Evaluation 只读 `standard_projection_payload.v1` 中的标准字段 +
> 已结案的 `actual_outcome`**：
> - `payload.projection_result`
> - `payload.exclusion_result`
> - `payload.confidence_result`
> - `payload.final_report`（用于 display attribution）
> - `payload.metadata`（`target_date` / `analysis_date` / `data_window_days`）
> - `actual_outcome`（来自 `services/outcome_capture` 已结案样本）

### 9.2 禁读

> Evaluation **禁止**读：
> - `predict_result` / 任何 `legacy PredictResult` 字段
> - `final_bias` / `final_confidence` / `primary_projection` / `final_projection`
> - `combined_user_summary` 之外的**任何** `ai_summary` / UI display 文本
> - 任何 trading-action 字段
> - 2026-01-01 之后的 holdout 区间数据（仍永久保留为 final holdout）

### 9.3 迁移目标

| 文件 | 当前 | 16E 之后 |
|---|---|---|
| [services/contract_replay_writer.py:83, 475](services/contract_replay_writer.py:83) | 直调 `predict.run_predict` 拿 legacy `PredictResult` | 调 `architecture_orchestrator` 拿 `standard_projection_payload.v1` 直接持久化 |
| `services/historical_replay_training.py` | 走 `projection_orchestrator_v2.run_projection_v2` | 切到 `architecture_orchestrator` |
| `services/three_system_replay_audit.py` | 历史 audit | 读新 standard payload |
| `scripts/run_e2e_loop.py:108-109, 232` | 调 `predict.run_predict` | 切到 `architecture_orchestrator` |
| `scripts/save_projection_records_smoke.py:441` | 调 `run_projection_v2` | 切到 `architecture_orchestrator` |

### 9.4 evaluation 输出统一（决定）

> Evaluation 输出**统一**到 `logs/evaluation/<run_kind>/<YYYY-MM-DD>/`
> 目录结构（与现有 `logs/historical_training/` 区分），schema 待 16E
> 落地；当前散落在 `logs/historical_training/03_fresh_replay/` /
> `exclusion_action_validation_2e/` / `_v2/` / `logs/technical_features/`
> 的已结案 evidence 保留为 tracked log evidence（15 §6 锁定，不动）。
>
> **本轮不创建任何新目录**；只是决定未来路径。

---

## 10. Review & Learning 未来读取路径（决定）

### 10.1 Review 读取

> Review & Learning Layer 读取：
> - `prediction snapshot`（来自 `prediction_store` 持久化的
>   `standard_projection_payload.v1`）
> - `payload.final_report`（display attribution）
> - `actual_outcome`（来自 `outcome_capture` 已结案样本）

### 10.2 Review 输出

> Review 输出（写入 `services/review_store`）：
> - `review_result`：每个 prediction 的 hit / miss / why
> - `error_diagnosis`：哪个系统错了（projection / exclusion / confidence
>   错估）
> - `lesson_candidate`：候选 lesson / rule memory entry

→ 这些输出**不**回写到当次的 `projection_result` / `exclusion_result` /
`confidence_result` / `final_report`。

### 10.3 当次预测路径不允许改答案

> Review **不能**当次改答案（与 1.0 §5 / §6.13 / 06 §6 / §7 一致）。
> 当次预测路径上的 `pre_prediction_briefing` 只能向 UI / Final Report
> Layer **展示**告警，**不**触发 mutation。
>
> 当前 `predict.py:1357 _apply_briefing_caution` mutate `final_confidence`
> 是 Bridge 旧行为，将在 16E 移除（见 §7.6）。

---

## 11. Temporary Migration Bridge 退出路线（决定）

按 1.0 §10 / 16A §14 / 16B §6 的 6 项退出条件，分 8 阶段：

### Phase 1 — Bridge 继续保护现状
> 当前阶段。Bridge 仍是 UI / replay / scripts 主入口；旧 `PredictResult`
> 字段仍由 `predict.run_predict` 产出。boundary tests（X1..X5 + 12E）
> 永久守护 mutation 表面。

### Phase 2 — 新标准 payload 生成稳定（16E 第一波）
> 16E 落地 `services/architecture_orchestrator.py`，能产出
> `standard_projection_payload.v1`；`compatibility_metadata` 子段
> 含 legacy 字段映射，让 UI / replay 渐进迁移。
>
> 出口指标：`architecture_orchestrator(...)` 在 home / scan / replay
> 三场景下产出 schema-validated `standard_projection_payload.v1`，
> regression 通过。

### Phase 3 — UI 迁移到新 payload（Bridge 退出条件 #1）
> 16E 改 `ui/predict_tab.py:1410` 调 `architecture_orchestrator`；
> 主面板字段全部切到 `final_report.*`。

### Phase 4 — Evaluation 迁移到新 payload（Bridge 退出条件 #2）
> 16E 改 `services/contract_replay_writer.py` /
> `services/historical_replay_training.py` /
> `services/three_system_replay_audit.py` /
> `scripts/run_e2e_loop.py` / `scripts/save_projection_records_smoke.py`
> 切到 `architecture_orchestrator`。

### Phase 5 — Replay 持久化 schema 切换
> `services/prediction_store` / `services/projection_record_store` 同时
> 接受 `standard_projection_payload.v1`（新写入）和 legacy `PredictResult`
> （旧记录读取兼容）。新写入只走标准 payload。

### Phase 6 — `predict.py` 变 thin wrapper（Bridge 退出条件 #4）
> `predict.run_predict` 内部完全转发到 `architecture_orchestrator` +
> `services/predict_legacy_adapter` 翻译；不再含
> `build_primary_projection` / `apply_peer_adjustment` /
> `build_final_projection` / `_summarize` / `_apply_briefing_caution`
> 逻辑（这些函数的副本归 archive 之前移出 active surface）。

### Phase 7 — legacy adapter / bridge 无 active import（Bridge 退出条件 #3 / #5 / #6）
> - `services/predict_legacy_adapter.py` 在 `predict.py` 内的最后一个
>   import 也被移除（因为 `predict.run_predict` 已不需要 v2_payload
>   overlay）
> - `services/predict_legacy_v2_bridge.py` 当前已无 active import；
>   16E 完成后整体 archive
> - `services/projection_orchestrator.py` 不再被 V2 / 任何活路径 import
>   （V2 自己也已被 `architecture_orchestrator` 取代）
> - `services/projection_orchestrator_v2.py` 整体 archive
> - tests 不再依赖 `PredictResult`（boundary X1..X5 改读 `compatibility_metadata`
>   或直接读标准 payload）

### Phase 8 — 删除 Bridge
> 全部 Bridge 模块（`predict.py` / `services/predict_legacy_adapter.py` /
> `services/predict_legacy_v2_bridge.py` / `services/projection_orchestrator.py` /
> `services/projection_orchestrator_v2.py` / `services/projection_entrypoint.py` /
> `services/projection_v2_adapter.py` / `services/predict_summary.py` /
> 旧 `home_terminal_orchestrator` 内核逻辑）整体 archive 到
> `archive/legacy/bridge_2026q2/`（命名按 archive 时点确定）。
>
> `compatibility_metadata` 顶层字段从 `standard_projection_payload.v1`
> 删除（`v2` 不再含此段）。

> **Phase 1 → Phase 8 的总进度：本轮（16C）仅做决定，落地从 16E 起**。
> Phase 2–8 的具体 PR 拆分由 16E 给出；每个 Phase **必须**有独立
> regression + 用户单独 confirm。

---

## 12. 16D 输入

16D（Isolation / Quarantine Plan）在 16C 决定基础上，需要回答：

1. **哪些 `LEGACY_ACTIVE_DEPENDENCY` 必须先断 caller**
   - `services/projection_orchestrator.py`：先把 V2 → V1 反向回调断掉
     （等价 V2 内部不再需要回调；这要求 16E 先把 primary_analysis /
     peer_adjustment / historical_probability 的合并方案给出）
   - `services/projection_orchestrator_v2.py`：迁移现有调用方
     （projection_entrypoint / projection_v2_adapter / historical_replay_training /
     save_projection_records_smoke）到 architecture_orchestrator 之前不能动
   - `services/home_terminal_orchestrator.py`：迁移成 UI orchestration
     之前不能删
2. **哪些 Temporary Bridge 只能标 deprecated（不能立即删）**
   - `predict.py`：deprecated since 16C；保留为 thin wrapper 直到 Phase 6
   - `services/predict_legacy_adapter.py`：deprecated since 16C；
     16E Phase 7 移除
   - `services/predict_legacy_v2_bridge.py`：当前无 active import；
     可作为第一个独立解散候选（标 deprecated 同时挂 archive plan）
3. **哪些 `UNKNOWN_REVIEW_REQUIRED` 需要 16B-2 深审**
   - `services/projection_chain_contract.py`（feature/payload 二合一）
   - `services/projection_output_adapter.py`（疑 dormant）
   - `services/active_rule_pool*`（5 个）
   - `services/projection_three_systems_renderer.py` / `projection_narrative_renderer.py`
   - `services/anti_false_exclusion_*` / `big_up_contradiction_card` / `big_down_tail_warning` / `exclusion_reliability_review` / `primary_bias_diagnosis` / `five_state_margin_policy`
   - `scripts/` 25+ evaluation / replay / dashboard 脚本
   - command-bar 工具层（agent_parser / ai_intent_parser / tool_router 等）
4. **哪些 raw artifacts / old output 已可移出 repo**
   - 7 个 `avgo_agent.db.backup_*`（已 14K ignore）→ 用户 single confirm 后 MOVE / DELETE
   - 4 套 untracked replay / regime validation 子目录（已 14K ignore）→ 同上
   - `.claude/worktrees/` 26 个（已 14K ignore）→ harness 自动管理；不在 16D 范围
   - tracked log evidence（`logs/historical_training/03_fresh_replay/` 等）→ 永久保留作为已结案 evidence

→ 16D 文档应给出每项的 archive marker / deprecation comment / 依赖断开顺序，**仍然不删 / 不移动**。

---

## 13. 不允许事项

本轮严守：

- ❌ 不改代码（`architecture_orchestrator.py` 本轮**不**创建）
- ❌ 不直接切主入口（决定写入 16C 文档；落地从 16E PR 起）
- ❌ 不默认迁移 V2（hard rule 1 + 1.0 §6.12 永久禁止"由 cleanup / signoff /
  decision 自动解锁"）
- ❌ 不删除 legacy modules
- ❌ 不移动 legacy modules
- ❌ 不跑 evaluation
- ❌ 不写 DB / 不改 DB schema
- ❌ 不接 trading
- ❌ 不输出 buy / sell / hold / hard / forced / required
- ❌ 不进入 3R-5 / 3R-6（1.0 §12 / 16A §18 锁定）
- ❌ 不复活 `continuous_smoothing*`
- ❌ 不解禁 promotion 三模块作为 active path
- ❌ 不重新引入已 quarantine 的 v1 stubs
- ❌ 不把 `TEMP_MIGRATION_BRIDGE` 当未来正式架构

---

## 14. 推荐下一步

**首选**：

> **Step 16D：Isolation / Quarantine Plan**

理由：
- 16C 已决定主入口 + 标准 schema + Bridge 退出路线
- 16D 把决定**翻译**为 file-by-file 的 deprecation marker + 依赖断开顺序
  + archive plan（仍然不动代码 / 不删文件）
- 16E 在 16D 输出之上做 PR 拆分；16F 起第一个代码 PR

**备选**（仅当主入口判断仍不够明确）：

> **Step 16C-2：Orchestrator Deep Decision**

仅当：
- 用户认为 §4.2 中"新建 `architecture_orchestrator.py`"的承接方式
  仍需进一步讨论（例如：是否分阶段从 home_terminal 演化 vs 完全新建）
- 16B-2 深审发现现有 V2 链路有未识别的 active dependency

**默认**：直接进 16D；16C-2 留作可选。

**不推荐**：

- 不推荐借 16C 做代码改动（16F 才是第一个代码 PR）
- 不推荐借任一步解锁 3R-5 / 3R-6（1.0 §12 7 项前提必须全部满足）

---

## 15. 严守边界

本轮 Step 16C **只**写 decision 文档：

- ❌ 未改业务代码（无 `.py` 文件被修改）
- ❌ 未新增测试（`tests/` 字节不变）
- ❌ 未删除文件
- ❌ 未移动文件
- ❌ 未修改 `.gitignore`
- ❌ 未处理 handoff（`.claude/handoffs/task_089_post_pr_cleanup.md` 字节
  不变；与 14L A2 / 14M / 15 §2 一致）
- ❌ 未处理 logs / DB backup / `.claude/worktrees/`
- ❌ 未跑 replay / validation / historical evaluation
- ❌ 未写 DB / 未改 DB schema
- ❌ 未默认迁移 `run_predict` 到 V2
- ❌ 未接 trading
- ❌ 未输出 buy / sell / hold / hard / forced / required
- ❌ 未启用任何 candidate / 未复活 `continuous_smoothing`
- ❌ 未触碰 RISK-1 / RISK-2 / RISK-3 / RISK-7 / RISK-8 / RISK-9 / RISK-10
- ❌ 未进入 3R-5 / 3R-6
- ❌ 未 commit / 未 push（按本轮指令）

唯一新增文件：[tasks/record_16c_target_dataflow_contract_decision.md](tasks/record_16c_target_dataflow_contract_decision.md)（本文件）。

后续修改路径：任何对 §3 数据流 / §4 主入口决策 / §5 标准 payload /
§6 三系统字段 / §7 Final Report / §8 UI / §9 Evaluation / §10 Review /
§11 Bridge 退出路线 / §12 16D 输入 / §13 禁止事项 / §14 下一步的调整，
都必须**显式更新本文件**；同时检查是否需要同步更新 1.0 / 16A / 16B。
