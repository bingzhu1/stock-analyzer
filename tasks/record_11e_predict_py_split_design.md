# 11E记录：predict.py Split Design

> 本设计针对 Step 09 / Step 10 中标记为 **HIGH_RISK** 的 RISK-8。
>
> 本轮**只写设计**：未改代码、未新增测试、未删文件、未移动文件、未写 DB、
> 未跑 validation、未 commit / push、未进入 Step 12、未进入 3R-5 / 3R-6、
> 未新增 candidate、未复活 continuous_smoothing、未实际拆分 predict.py、
> 未顺手碰 RISK-1 / RISK-2 / RISK-3 / RISK-7 / RISK-9 / RISK-10。

---

## 1. 设计目的

把 `predict.py`（仓库根，1170 行）从**职责混合**逐步退化为
**legacy compatibility wrapper**，让 active 业务逻辑全部走 services 层
（projection_entrypoint / projection_orchestrator_v2 / final_decision /
confidence_evaluator / aggregator）。

修复后的目标：

- `predict.py` **不再**承载核心 projection 逻辑（核心走 services/projection_*）
- `predict.py` **不再**计算 final_confidence（走 11C confidence_evaluator）
- `predict.py` **不再**生成新的 final decision（走 11B 改造后的 final_decision）
- `predict.py` 仅保留 `run_predict()` 兼容入口 + compatibility_fields 装配
- 所有 compatibility_fields 必须有 `source_mapping` 显式标注出处
- legacy callers（`ui/predict_tab.py` / `ui/history_tab.py` / 多个 services /
  scripts）调 `run_predict()` 时仍能拿到字段，但字段值必须**可追溯**到 services
  层 source

本设计**只**产出设计文档，Step 12 才实施 + commit。

---

## 2. 当前问题

### 2.1 文件规模与角色混杂

`predict.py` 1170 行，定义了 36 个顶级函数（1 个 TypedDict + 35 个 def）。
按角色统计（详见 §5）：

- **projection 计算**：`build_primary_projection`（174 行）+ `apply_peer_adjustment`
  + scoring helpers（≈400 行 grand total）
- **aggregator**：`build_final_projection`（150 行）—— 产出 `final_direction` /
  `final_confidence` / `probability_bucket` / `final_one_sentence`，**与
  services/final_decision.py 同模式重算 final_*** 字段
- **confidence 重算**：`_confidence_from_score` / `_raise_confidence` /
  `_lower_confidence` / `_normalize_confidence` / `_path_risk_from_confidence` /
  `_apply_research_adjustment`（≈80 行）
- **summary 文本**：`_summarize` + `prediction_summary` / `final_one_sentence`
  装配（aggregator 范畴）
- **入口编排**：`run_predict`（line 1107+）+ `_missing_scan_result` +
  `_build_projection_three_systems_attachment` + `_apply_briefing_caution`

### 2.2 active importers（不能删除 predict.py）

`grep "from predict\|import predict\b"` 显示 active importer：

- `ui/predict_tab.py`（UI 主 tab）
- `ui/history_tab.py`（UI 历史 tab）
- `scripts/summarize_confidence_calibration_inputs.py`
- `scripts/run_e2e_loop.py`
- `services/projection_orchestrator.py`（旧 V1 orchestrator，仅 V2 内部 import）
- `services/projection_review_closed_loop.py`
- `services/review_agent.py`
- `services/log_store.py`
- `services/contract_replay_writer.py`

→ 9+ 个 active 调用点；**任何删除 predict.py 的尝试都会破坏链路**。Step 12
必须保留 `run_predict()` 兼容入口。

### 2.3 与 V2 路径的关系

`predict.py:1020-1068` 的 `_build_projection_three_systems_attachment` 注释说明
（line 18-24）：predict.py **本身**会通过 V1 legacy orchestrator 走回 V2
orchestrator + 反过来；存在 re-entry guard（`_projection_three_systems_attachment_state`）
防止递归 30 层。

→ predict.py 与 V2 之间已经是**双向调用**关系。Step 12 拆分必须保证：

- `run_predict()` 内部最终通过 V2 路径产出结果
- compatibility_fields 装配仅做**字段映射**，不引入新判断
- re-entry guard 保留（11E 不动这部分）

### 2.4 现有 v1 contract 字段已有"两套"

`build_primary_projection`（line 446-619）在产生 v1 字段（`final_bias` /
`final_confidence` / `score` / `signals`）的同时，line 583-617 **又派生出**
Step 1A contract 02 字段（`primary_direction` / `open_projection` /
`five_state_projection` / `primary_confidence_raw` / `key_evidence` 等）。

`build_final_projection`（line 834-984）同理：line 950-981 **又派生出**
Step 1A contract 06 字段（`final_direction` / `final_open_projection` /
`final_intraday_path` / `final_close_projection` / `final_five_state` /
`probability_bucket` / `final_one_sentence` / `key_price_levels`）。

→ 已经存在**双 schema 共存**的事实；11E 的拆分思路是：
**让 v1 字段（`final_bias` / `final_confidence` / 等）从 V2 / confidence_evaluator
派生**，不再由 predict.py 自己重算。

---

## 3. 违反的 contract

| contract | 章节 | 违规点 |
|---|---|---|
| 06 三系统独立原则 | §6 三系统正确关系 / §7 第 6 条 | predict.py 同时产 projection + final + confidence，违反三系统独立 |
| 07A 推演 contract | §5 推演不得输出 `final_confidence` / `final_*` 聚合字段 | `build_primary_projection` 输出 `final_bias` / `final_confidence`；`build_final_projection` 输出 `final_*` 全套 |
| 07C 置信度 contract | §5 confidence 不得在 projection 内自算 | `_confidence_from_score` / `_raise_confidence` / `_lower_confidence` / `_normalize_confidence` 在 v1 projection 内重算 |
| 07D final report contract | §5 禁止 aggregator 引入新判断 / §10 句句必有出处 | `build_final_projection` 翻 `final_bias` + 重算 `final_confidence` + 拼 `final_one_sentence` |
| 11A | RISK-1 不得让 projection 接收 exclusion 输出 | predict.py v1 路径未直接吃 exclusion，但通过 `_apply_research_adjustment` 的 research / scan_bias 反馈接近此 pattern |
| 11B | RISK-2 final_decision 不得重算 confidence / 翻 direction | predict.py 的 `build_final_projection` **正是** RISK-2 的 v1 双胞胎 |
| 11C | RISK-3 confidence 收敛到 confidence_evaluator | predict.py 的 confidence 计算正是 RISK-3 散落点之一 |

---

## 4. 拆分目标

修复后必须满足：

1. **predict.py 退化为 legacy compatibility wrapper**：
   - 保留 `run_predict(...)` 入口（不删函数签名）
   - 保留 `PredictResult` TypedDict（schema 兼容）
   - 保留 9+ 个 active importer 的调用契约
2. **核心 projection 逻辑迁出**或委托：
   - `build_primary_projection` 改为调 `services/projection_entrypoint.py` 取
     `projection_v2_raw`，再做字段适配
   - `apply_peer_adjustment` 改为读 `projection_v2_raw.peer_adjustment` 字段
3. **confidence 计算移除**：
   - 删除 / 标记 deprecated `_confidence_from_score` / `_raise_confidence` /
     `_lower_confidence` / `_normalize_confidence` / `_path_risk_from_confidence`
     的内部计算路径
   - `final_confidence` 字段从 `confidence_result.combined_confidence.level`
     映射来；缺失则填 `"unknown"`（与 11B / 11C 阶段 B 对齐）
4. **aggregator 计算移除**：
   - `build_final_projection` 改为读取 `projection_v2_raw.final_decision` 字段
     + `confidence_result` 字段，做**纯 mapping**（11B 修复后 final_decision 已是
     纯 aggregator）
   - **不**再翻 direction、**不**再重算 confidence、**不**再拼新的
     `final_one_sentence`
5. **summary 改为 sourced**：
   - `prediction_summary` / `final_one_sentence` 必须从 `final_report.combined_user_summary`
     映射而来；不允许 wrapper 自己产新文本（07D §10 句句必有出处）
6. **compatibility_fields 显式标注**：
   - 所有兼容字段（`final_bias` / `final_confidence` / `final_direction` /
     `probability_bucket` / `prediction_summary` / 等）必须在
     `result["source_mapping"]` 中标注出处
7. **禁止字段**：
   - `trading_action` / `buy/sell/hold` / `simulated_trade` / `no_trade` /
     `hard_exclusion` / `forced_exclusion` / `required_decision` /
     `production_promotion` / `_PROTECTION_LAYER_CONNECTED`
8. **不**改 active importers（v1 schema 字段名保留）

---

## 5. 当前职责分区审查

> 基于 1170 行 + 36 个顶级函数（1 TypedDict + 35 def），分 11 个 section。

| section | lines | current role | target owner | future action |
|---|---|---|---|---|
| **input normalization** | line 13-99（imports + 常量 + `PredictResult` TypedDict + 各种 enum / map） | 输入标签归一 | predict.py wrapper（保留） | 保留 |
| **数据加载** | 无独立段；通过 scan_result / research_result 入参传入 | 由调用方传入 | data_infra / scanner / research（外部） | 不动 |
| **特征构建** | `_recent_20_summary`（line 260-312）+ `_gap_state_from_value` / `_intraday_state_from_value` / `_volume_state_from_value` / `_trend_state_from_recent_summary`（line 313-358） | 从 scan_result.avgo_recent_20 派生特征 | 复用 / 委托 services/features_20d.py 或 services/projection_chain_contract.py | Step 12+ 评估 / 不本轮拆 |
| **projection scoring** | `build_primary_projection`（line 446-619） | v1 推演核心计算 | projection system（services/main_projection_layer.py 或 primary_20day_analysis.py） | **改为委托**：调 services/projection_entrypoint.run_projection_entrypoint() 取 projection_v2_raw，做 v1 字段映射 |
| **historical match / probability** | 通过 `recent_summary` 隐式 + Step 1A contract 02 `historical_sample_count` 字段 | 历史 hint（v1 路径很弱） | services/historical_probability.py（V2 已有完整实现） | 改为委托 V2 |
| **peer voting** | `_peer_layer_vote` / `_combine_peer_votes`（line 621-650）+ `apply_peer_adjustment`（line 650-770） | v1 peer 投票 / adjustment | services/peer_adjustment.py（V2 已有完整实现） | 改为委托 V2 |
| **research adjustment** | `_apply_research_adjustment`（line 770-834） | research 分支调整 | 评估：归 projection（07A 内部规则）或 confidence（07C 评价）；本轮**保留作为 evidence**，不重算 confidence | 改为 evidence_only：研究信号作为 evidence list 输出，不修改 final_bias / final_confidence |
| **final_confidence 计算** | `_confidence_from_score` / `_raise_confidence` / `_lower_confidence` / `_normalize_confidence` / `_path_risk_from_confidence`（line 134-218 + 403-411） | confidence 重算 | confidence_evaluator（11C） | **删除调用路径**；保留函数定义为 dead code，Step 14 cleanup；compatibility 输出从 confidence_result 映射 |
| **summary / explanation** | `_summarize`（line 435-443）+ `prediction_summary` 装配（在 build_final_projection 内）+ `final_one_sentence`（line 981） | aggregator 文本 | final_report.combined_user_summary（07D） | 改为映射：`prediction_summary = final_report.combined_user_summary`；缺失时填占位 |
| **output payload assembly** | `build_final_projection`（line 834-984）+ `_missing_scan_result`（line 986-1019）+ `run_predict`（line 1107+） | aggregator 装配 + 入口 | predict.py wrapper（保留） + 委托 services/projection_entrypoint.py | 改造：`build_final_projection` 退化为 v1 schema mapping；`run_predict` 内部全部走 V2 |
| **logging / persistence** | 通过 services/log_store.py / services/prediction_store.py 间接（predict.py 不直接写） | data infra | data infra（保留） | 不动 |
| **compatibility fields** | TypedDict `PredictResult` 全部字段 + `source_mapping`（待添加） + `deprecation_notes`（待添加） | 9+ active importer 兼容 | predict.py wrapper | 保留 schema；新增 source_mapping + deprecation_notes |
| **re-entry guard** | `_projection_three_systems_attachment_state` + `_build_projection_three_systems_attachment`（line 25, 1020-1068） | 防 V1↔V2 互调递归 | predict.py wrapper | 保留 |
| **briefing caution** | `_apply_briefing_caution`（line 1069-1106） | 把 briefing caution_level 反应到结果 | 待评估：是 evidence_only 还是真正影响？ | Step 12 spot-check；如属 evidence_only 保留；如修改 confidence 则禁用 |

---

## 6. 目标模块归属设计

| 逻辑 | 当前位置 | 修复后位置 |
|---|---|---|
| projection 五状态分布 | predict.py `build_primary_projection` | `services/main_projection_layer.py`（V2，11A 修复后已 contract-clean） |
| historical probability | predict.py 隐式 | `services/historical_probability.py`（V2） |
| peer adjustment | predict.py `apply_peer_adjustment` | `services/peer_adjustment.py`（V2） |
| confidence 计算 | predict.py `_confidence_from_score` / `_raise_confidence` / `_lower_confidence` / `_normalize_confidence` | `services/confidence_evaluator.py`（11C 阶段 A 创建） |
| final 方向 / 置信 | predict.py `build_final_projection` | `services/final_decision.py`（11B 修复后已 contract-clean）+ wrapper 字段映射 |
| final 文本 / one_sentence | predict.py `_summarize` / `final_one_sentence` | `services/final_decision.combined_user_summary`（11B）/ `services/projection_three_systems_renderer` |
| LLM / 自由文本 | predict.py 当前**无** LLM 调用 | （仍无；ai_summary.py 是另一处，11F 范畴） |
| compatibility 字段装配 | predict.py 主体 | predict.py wrapper（保留，但仅做 mapping） |
| 日志 / 持久化 | predict.py 不直接写；通过 services 间接 | services/log_store.py / prediction_store.py（保留） |
| logging / source attribution | 无 | wrapper 输出加 `source_mapping` + `deprecation_notes` |

---

## 7. 最小拆分策略

> 多阶段，**绝不**一次性大改。Step 12 仅做最小 enforcement。

### 阶段 A — 加 contract tests（不改 predict.py）

**目标**：锁定 predict.py 不得继续扩大职责。

- 加 `tests/test_predict_legacy_wrapper_boundary.py`，含 §11.1 列出的 contract
  enforcement test
- predict.py **完全不动**
- 部分测试**当前 fail**（red baseline）；部分 pass（已合规的部分）
- commit message：`test(boundary): add predict.py legacy wrapper baseline tests (RISK-8 step A)`

### 阶段 B — 标记 legacy + docstring + source notes（最小 patch）

**目标**：让 predict.py 显式声明自己是 legacy wrapper。

- 在文件 docstring 顶部加 deprecation 标注
- 给每个**违规函数**加 `# DEPRECATED (RISK-8): owner = services.<X>` 行内注释
- 在 `run_predict()` 返回 dict 中加 `"deprecation_notes"` 字段
- predict.py 函数体**不改逻辑**；仅注释 + 元数据
- commit message：`docs(boundary): mark predict.py as legacy wrapper (RISK-8 step B)`

> 阶段 B 是**纯文档级别**修改，无任何行为变化。

### 阶段 C — 禁用 final_confidence 内部计算（依赖 11C 阶段 A 完成）

**前置依赖**：11C 阶段 A `services/confidence_evaluator.py` 已存在 +
`build_confidence_result(...)` 可用

**目标**：让 wrapper 的 `final_confidence` 来自 confidence_result 而不是
predict.py 自己的 `_confidence_from_score`。

- 修改 `run_predict(...)`：
  - 内部调 `build_confidence_result(projection_result=..., exclusion_result=..., target_date=...)`
  - 把 `confidence_result.combined_confidence.level` 映射到输出 `final_confidence`
  - 缺失时填 `"unknown"`
- `build_primary_projection.final_confidence` / `build_final_projection.final_confidence`
  字段值改为 `final_confidence_compat`（map 自 confidence_result）
- `_confidence_from_score` / `_raise_confidence` / `_lower_confidence` 等函数
  本体保留但**不再被调用**（dead code，Step 14 cleanup 删）
- `_apply_research_adjustment` 内部对 `final_confidence` 的调整改为**evidence_only**：
  把 research 信号 append 到 `evidence_list`，不修改 final_confidence
- 输出 dict 加 `source_mapping["compat_final_confidence"] = "confidence_result.combined_confidence.level or unknown"`
- commit message：`fix(boundary): RISK-8 wire final_confidence from confidence_result (step C)`

### 阶段 D — 改 summary 为 sourced（依赖 11B 完成）

**前置依赖**：11B `services/final_decision.py` 已是纯 aggregator +
`combined_user_summary` 可用

**目标**：让 wrapper 的 `prediction_summary` / `final_one_sentence` 从
`final_report.combined_user_summary` 映射，不再由 `_summarize` 自拼。

- 修改 `run_predict(...)`：从 `final_decision_result.combined_user_summary`
  映射到 `prediction_summary` / `final_one_sentence`
- `_summarize(...)` 函数本体保留为 dead code（Step 14 cleanup 删）
- 输出 dict 加 `source_mapping["compat_summary"] = "final_report.combined_user_summary or final_decision.summary"`
- commit message：`fix(boundary): RISK-8 wire summary from final_report (step D)`

### 阶段 E — projection 核心改为委托 V2（最大风险阶段）

**前置依赖**：阶段 A / B / C / D 全部完成 + RISK-1 / RISK-2 / RISK-6 已修

**目标**：让 `run_predict()` 主链路通过 `services/projection_entrypoint.run_projection_entrypoint()`
产出 v2_raw，wrapper 仅做字段映射。

- `run_predict(...)` 不再调 `build_primary_projection` / `apply_peer_adjustment`
  / `build_final_projection` 来计算；改为：
  ```python
  v2_result = run_projection_entrypoint(symbol=symbol, target_date=target_date)
  # 然后做 v1 schema 适配
  ```
- `build_primary_projection` / `apply_peer_adjustment` / `build_final_projection`
  函数本体**保留**（很多 active importer 直接调用）；但**内部**改为读
  v2_result 字段做 mapping，不再自己计算
- 必须保留 `PredictResult` TypedDict 的全部字段名 + 取值集
- commit message：`fix(boundary): RISK-8 delegate predict.py core to V2 path (step E)`

### 阶段 F — 后续 cleanup（属 Step 14，不在 11E 范围）

- 删除 `_confidence_from_score` 等 dead code 函数定义
- 删除 `_summarize` 等 dead code 函数定义
- 评估是否能把 `build_primary_projection` / `build_final_projection` 完全移除
  （仅当 9+ active importer 全部迁出之后）
- 11E **不**做阶段 F

### Step 12 实际执行哪些阶段？

> Step 12 的"RISK-8 fix commit"建议**至少包含阶段 A + B**，可以再加阶段 C / D
> 看 11C / 11B 是否已完成。**阶段 E 应放在独立 commit**（最大 blast radius）。

推荐 commit 序列（Step 12 内）：
- `commit X1: test(boundary): add predict.py legacy wrapper baseline tests` (阶段 A)
- `commit X2: docs(boundary): mark predict.py as legacy wrapper` (阶段 B)
- `commit X3: fix(boundary): RISK-8 wire final_confidence from confidence_result` (阶段 C，需 11C 阶段 A 已 commit)
- `commit X4: fix(boundary): RISK-8 wire summary from final_report` (阶段 D，需 11B 已 commit)
- `commit X5: fix(boundary): RISK-8 delegate predict.py core to V2 path` (阶段 E，需 11A / 11B / 11C 阶段 B 全部 commit)

每 commit 独立 + 可回滚。

---

## 8. 输出结构设计

修复后 `run_predict(...)` 返回 dict（兼容现 `PredictResult`）：

```jsonc
{
  // ── 既有 v1 schema（保留兼容；9+ active importer 依赖） ──
  "kind": "legacy_predict_wrapper",
  "symbol": "AVGO",
  "predict_timestamp": "<YYYY-MM-DD HH:MM:SS>",

  "scan_bias": "<from scan_result>",
  "scan_confidence": "<from scan_result>",
  "research_bias_adjustment": "<from research_result>",

  "final_bias": "<偏多|偏空|中性|unavailable>",   // ← from V2 final_decision
  "final_confidence": "<low|medium|high|unknown>", // ← from confidence_result.combined_confidence.level (11C)
  "open_tendency": "<from V2>",
  "close_tendency": "<from V2>",
  "prediction_summary": "<from final_report.combined_user_summary>",
  "supporting_factors": [...],                    // mapped from V2 evidence
  "conflicting_factors": [...],
  "notes": "...",
  "path_risk": "<from V2>",
  "peer_path_risk_adjustment": {...},

  "primary_projection": {
    // 仍提供 Step 1A contract 02 字段（兼容）
    "primary_direction": "...", "open_projection": "...",
    "intraday_path_projection": "...", "close_projection": "...",
    "five_state_projection": "...", "primary_confidence_raw": "...",
    "key_evidence": [...],
    // 取值全部 from V2 main_projection / primary_analysis
    ...
  },
  "peer_adjustment": {
    // from V2 peer_adjustment
    ...
  },
  "final_projection": {
    // Step 1A contract 06 字段（兼容）
    "final_direction": "...", "final_open_projection": "...",
    "final_intraday_path": "...", "final_close_projection": "...",
    "final_five_state": "...", "probability_bucket": "...",
    "final_one_sentence": "<from final_report.combined_user_summary>",
    "key_price_levels": {},
    // 取值全部 from V2 final_decision
    ...
  },

  // ── projection_three_systems 透传（已存在；保留） ──
  "projection_three_systems": {...},

  // ── 新增 wrapper 元数据 ──
  "source_mapping": {
    "compat_final_bias":          "final_decision.final_direction",
    "compat_final_confidence":    "confidence_result.combined_confidence.level or unknown",
    "compat_prediction_summary":  "final_report.combined_user_summary or final_decision.summary",
    "compat_final_one_sentence":  "final_report.combined_user_summary or final_decision.summary",
    "compat_primary_direction":   "main_projection.predicted_top1.state",
    "compat_peer_adjustment":     "peer_adjustment (V2)",
    "compat_path_risk":           "final_decision.risk_level"
  },

  "deprecation_notes": [
    "predict.py 自 RISK-8 起标记为 legacy compatibility wrapper。",
    "新代码请直接使用 services/projection_entrypoint.run_projection_entrypoint。",
    "compatibility 字段值由 V2 链路派生；详见 source_mapping。",
    "不允许在 wrapper 内重算 confidence / 翻 direction / 拼无出处 summary。"
  ],

  "non_mutation_confirmations": {
    "projection_result_mutated": false,
    "exclusion_result_mutated": false,
    "confidence_result_mutated": false,
    "final_report_mutated": false,
    "wrapper_introduces_new_judgment": false
  }
}
```

### 8.1 禁止字段

```jsonc
// ❌ 不允许
{
  "trading_action": "...",
  "buy": "...", "sell": "...", "hold": "...",
  "simulated_trade": {...},
  "no_trade": true,
  "hard_exclusion": true,
  "forced_exclusion": true,
  "required_decision": true,
  "production_promotion": true,
  "_PROTECTION_LAYER_CONNECTED": true,
  "final_report_mutation": {...},
  // ❌ 不允许在 compatibility 中翻 direction：
  "compat_final_direction_overridden": "中性"
}
```

### 8.2 兼容性边界

- `final_bias` / `final_confidence` / `final_direction` / `final_one_sentence`
  字段名**保留**；取值全部来自 V2 / confidence_result / final_report
- 缺失时填 `"unknown"` / `"unavailable"` 而非 fallback 自算
- `source_mapping` **必须**存在；缺则 contract test 失败
- `non_mutation_confirmations` **必须**存在；任一字段为 `true` 即视为违规

---

## 9. 与 11A / 11B / 11C 的关系

> **关键**：11E **不替代** 11A / 11B / 11C；11E **依赖** 它们。

| 阶段 | 11E 依赖 |
|---|---|
| 11A（projection ← exclusion 解耦） | predict.py 阶段 E（委托 V2）必须在 11A 修复后做，否则 v1 路径会继承 V2 路径的 RISK-1 |
| 11B（final_decision 纯化） | predict.py 阶段 D（summary from final_report）必须在 11B 修复后做，否则 wrapper 拿到的 `combined_user_summary` 仍是 RISK-2 旧逻辑 |
| 11C 阶段 A（confidence_evaluator 独立模块） | predict.py 阶段 C（final_confidence from confidence_result）必须在 11C 阶段 A 后做 |
| 11C 阶段 B（接入 active path） | predict.py 阶段 E 委托 V2 时，确保 V2 输出已带 confidence_result |
| 11D（cutoff guard） | predict.py 不直接调 memory / preflight；通过委托 V2 间接受益 |
| 11F（ai_summary） | predict.py 当前**无** LLM 调用；11F 修 ai_summary 后 wrapper 不会受影响 |

> **绝对禁止**：在 predict.py 内提前实现 confidence engine / aggregator
> 改造（这是 11C / 11B 的工作；11E 只能 wire from existing）。

> **绝对禁止**：predict.py 成为绕过 11A–11C 的旧入口（如发现 caller 调
> predict.py 来"绕开 V2"，必须在 Step 12 阶段 E 中切除该路径）。

---

## 10. 兼容性风险

### 10.1 测试层

`tests/test_predict.py` 等可能：

- 直接断言 `final_confidence == "high"` 等具体 level
- 断言 `_confidence_from_score(0.5) == "low"` 等内部 helper 行为
- 断言 `prediction_summary` 含特定词

Step 12 处理：

- 阶段 A 加新 contract test（与旧测试并存）
- 阶段 C / D 实施时改写**直接断言 v1 取值**的旧测试为 "from_source" 断言
- 不允许保留依赖 wrapper 重算的测试

### 10.2 UI 层

- `ui/predict_tab.py` / `ui/history_tab.py` 直接调 `run_predict()` + 读
  `final_confidence` / `final_one_sentence` 等
- 修复后字段名不变；取值会变（unknown 占位 → 后续 11C 阶段 B 完成后恢复有
  意义 level）
- 预期 UX：阶段 C commit 后短期 UI 显示 confidence = unknown；待 11C 阶段 B
  完成后恢复

### 10.3 logs / prediction_store

- `services/log_store.py` / `prediction_store.py` 写入字段 schema 不变；
  取值变化（例如不再有 `final_bias = "偏多" + final_confidence = "high"` 经
  research downgrade 的组合）
- 历史 prediction_log 不回填（Step 14 才考虑）

### 10.4 summary 文本测试

- 阶段 D 后 `prediction_summary` 由 final_report 派生；可能与旧 `_summarize`
  输出**完全不同**
- narrative / summary 测试必须改写为 source-based 断言

### 10.5 9+ active importer 全部需 spot-check

阶段 E 后必须 spot-check：

- `ui/predict_tab.py`、`ui/history_tab.py`：UI 渲染不崩
- `scripts/summarize_confidence_calibration_inputs.py`、`scripts/run_e2e_loop.py`：
  脚本仍可运行
- `services/projection_orchestrator.py`：旧 V1 orchestrator（仅 V2 内部 import；
  待评估是否仍需要）
- `services/projection_review_closed_loop.py` / `review_agent.py` /
  `log_store.py` / `contract_replay_writer.py`：复盘 / 日志 / 回放仍正常

### 10.6 大范围拆分回归风险

> Step 12 **不**一次性删 predict.py；**不**一次性改全部 importer。

阶段 E 是**最大风险阶段**；建议拆为**多个**小 commit：先迁移 `final_bias` /
`final_confidence` / `prediction_summary` 这一批，再迁 `primary_projection` /
`peer_adjustment`，最后处理 `final_projection`。

---

## 11. Contract enforcement tests 设计

> 本节**只描述测试设计**，Step 12 才新增测试代码。

### 11.1 必须新增的测试

| 测试名（建议） | 验证内容 |
|---|---|
| `test_predict_py_marked_as_legacy_wrapper` | 静态扫描 `predict.py` 文件 docstring 含 "legacy compatibility wrapper" 标注；返回 dict 中 `kind == "legacy_predict_wrapper"` |
| `test_predict_py_does_not_compute_new_confidence_when_confidence_result_missing` | mock `confidence_result = None`，调 `run_predict(...)`，断言 `final_confidence == "unknown"`；**不**等于 wrapper 自算的 low/medium/high |
| `test_predict_py_compat_confidence_from_confidence_result` | mock `confidence_result.combined_confidence.level == "medium"`，断言 `final_confidence == "medium"`；不依赖 v1 score 加减分 |
| `test_predict_py_does_not_mutate_projection_with_exclusion` | mock projection + exclusion 输入，断言 `run_predict()` 输出的 `primary_projection.state_probabilities`（如有）/ `final_bias` 不因 exclusion 改变 |
| `test_predict_py_source_mapping_present_for_compat_fields` | 断言 `result["source_mapping"]` 是 dict 且含 `compat_final_bias` / `compat_final_confidence` / `compat_prediction_summary` 等关键 key |
| `test_predict_py_no_trading_or_hard_fields` | 断言 result **不含** `trading_action` / `buy` / `sell` / `hold` / `simulated_trade` / `no_trade` / `hard_exclusion` / `forced_exclusion` / `required_decision` / `production_promotion` / `_PROTECTION_LAYER_CONNECTED` / `final_report_mutation` |
| `test_predict_py_no_continuous_smoothing_import` | 静态扫描 `predict.py` 不含 `from services.continuous_smoothing` / `import continuous_smoothing` |
| `test_predict_py_does_not_call_final_decision_recompute_path` | 静态扫描 `run_predict(...)` 路径上**不**调 `_apply_preflight_influence` 等 RISK-2 dead 函数 |
| `test_predict_py_non_mutation_confirmations_present` | 断言 `result["non_mutation_confirmations"]` 是 dict 且 5 个 `*_mutated` 字段恒为 false |
| `test_predict_py_deprecation_notes_present` | 断言 `result["deprecation_notes"]` 是非空 list；含 "legacy" 关键字 |
| `test_predict_py_prediction_summary_from_final_report_or_decision` | 断言 `prediction_summary` 与 `final_report.combined_user_summary` / `final_decision.summary` 至少一个一致；**不**是 wrapper 自拼 |
| `test_predict_py_does_not_introduce_new_final_direction` | 注入 `final_decision.final_direction == "偏多"`，断言 `result["final_bias"]` 与之对齐（v1 字段映射）；不允许 wrapper 翻成 "中性" |
| `test_predict_py_re_entry_guard_preserved` | 静态扫描或 mock 验证 `_projection_three_systems_attachment_state` re-entry guard 仍存在；防递归 |

### 11.2 测试不允许的内容

- 测试**不**应允许 wrapper 自算 final_confidence
- 测试**不**应允许 `_confidence_from_score` / `_summarize` 仍在 active call path
- 测试**不**应允许 `source_mapping` 缺失
- 测试**不**应允许 `non_mutation_confirmations` 任一字段为 true

---

## 12. 不允许的修复方式

以下修复方式**不**符合 contract，Step 12 实施时**禁止**：

1. **不**允许一次性删除 predict.py
2. **不**允许在 predict.py 里继续重算 confidence（11C 已规定 confidence 收敛
   到 confidence_evaluator）
3. **不**允许把 `services/final_decision.py` 旧逻辑复制进 predict.py（绕过
   11B 的修复）
4. **不**允许把 exclusion 融入 v1 projection（违反 RISK-1 / 11A）
5. **不**允许为 compatibility_fields 生成新判断（必须有 `source_mapping`）
6. **不**允许用 LLM 在 wrapper 内生成无出处 summary（11F / RISK-9 范畴；wrapper 不调 LLM）
7. **不**允许在 11E 内**顺手修** RISK-1 / RISK-2 / RISK-3 / RISK-7 / RISK-9 /
   RISK-10
8. **不**允许 cleanup 与 boundary fix 混 commit（包括删除 dead code 函数）
9. **不**允许 large rewrite：阶段 E 内部应拆为多个小 commit
10. **不**允许进 3R-5 / 3R-6
11. **不**允许复活 continuous_smoothing
12. **不**允许跳过 11A / 11B / 11C 直接做 11E 阶段 E
13. **不**允许"为通过测试而临时禁用 active importer"（必须保持 9+ importer 调用契约）
14. **不**允许在 `compatibility_fields` 中保留任何 wrapper 自算的 `final_*`
    字段而**不**附 source_mapping
15. **不**允许把 `_apply_research_adjustment` 内的 confidence 调整改名继续做

---

## 13. Step 12 实施顺序建议

> Step 12 才允许执行；本轮**不**实施。

### 13.1 强约束顺序

1. **先等** 11A / 11B / 11C 对应最小实现完成
2. **阶段 A**（test 红灯 baseline）：单 commit
3. **阶段 B**（legacy 标注）：单 commit；纯文档级
4. **阶段 C**（final_confidence from confidence_result）：单 commit；前置 11C 阶段 A
5. **阶段 D**（summary from final_report）：单 commit；前置 11B 完成
6. **阶段 E**（projection 委托 V2）：可拆 2-3 个 commit；前置 11A / 11B / 11C 全部
7. **阶段 F**（dead code cleanup）：**不属 11E**，留 Step 14

### 13.2 commit 序列建议

```
[11A Step 12 commit] → fix(boundary): RISK-1+6 decouple projection from exclusion
[11B Step 12 commit] → fix(boundary): RISK-2 purify final decision aggregator
[11C Step 12 step A] → feat(boundary): add standalone confidence evaluator (RISK-3 step A)
[11D Step 12 commit] → fix(boundary): RISK-7 add memory feedback cutoff guard
[11C Step 12 step B] → fix(boundary): wire confidence_result into final_decision and renderer (RISK-3 step B)

[11E Step 12 commit X1] → test(boundary): add predict.py legacy wrapper baseline tests (RISK-8 step A)
[11E Step 12 commit X2] → docs(boundary): mark predict.py as legacy wrapper (RISK-8 step B)
[11E Step 12 commit X3] → fix(boundary): RISK-8 wire final_confidence from confidence_result (step C)
[11E Step 12 commit X4] → fix(boundary): RISK-8 wire summary from final_report (step D)
[11E Step 12 commit X5] → fix(boundary): RISK-8 delegate predict.py core to V2 path (step E)
                          (建议拆 X5a / X5b / X5c 三个小 commit)

[11F Step 12 commit] → fix(boundary): RISK-9 ai_summary source attribution
[11G Step 12 commit] → docs(boundary): RISK-10 promotion offline-only documentation lock

[Step 13] → 全量 regression
[Step 14] → cleanup / quarantine
```

### 13.3 不允许 inside Step 12 commit 的内容

- **不**改 9+ active importer 的调用契约（schema / 字段名）
- **不**删 dead code（`_confidence_from_score` / `_summarize` 等）
- **不**改 RISK-1 / RISK-2 / RISK-3 / RISK-7 / RISK-9 / RISK-10
- **不**改 `services/projection_orchestrator.py` 旧 V1（quarantine 留 Step 14）

---

## 14. 回滚策略

### 14.1 失败模式

如果在 Step 12 阶段 C / D / E 实施过程中：

- UI 大面积显示 `final_confidence == unknown`
- 9+ importer 中某个测试断言 final_one_sentence 含特定词组失败
- prediction_log 中字段取值剧变导致 review / outcome 测试不过

### 14.2 回滚原则

> **不**回退到 predict.py 内部重算 confidence / 重算 final_direction /
> 自拼 summary。

正确的回滚序列：

1. `git revert` 失败的阶段 commit
2. **保留** wrapper 已加的 `source_mapping` / `deprecation_notes` /
   `non_mutation_confirmations` 字段
3. 通过 `compatibility_fields` 修显示（例如对 `final_one_sentence` 缺失时
   填一句 "由 predict.py legacy wrapper 透传，待 V2 final_report 接入"）
4. **不**回到重算 confidence / 改写 projection 的旧路径
5. **不**为通过 UI 显示而临时把 wrapper 自算 confidence 恢复
6. 必要时给 9+ importer 加 i18n / fallback **在 caller 端**，而不是在 wrapper
   内伪造

### 14.3 不允许的"回滚捷径"

- **不**允许悄悄恢复 `_confidence_from_score(score)` 调用
- **不**允许把"加减分 confidence"改名为 `_compat_confidence_score` 继续算
- **不**允许跳过阶段 A 直接修改 `build_final_projection` 内部逻辑
- **不**允许 `git commit --amend` 隐藏 wrapper 自算行为

---

## 15. 严守边界

本轮**只是设计**：

- 未改代码
- 未新增测试
- 未删文件
- 未移动文件
- 未写 DB
- 未改 DB schema
- 未跑 replay
- 未跑 validation
- 未处理 untracked / DB backup / stash / .claude/worktrees/
- 未进入 3R-5 / 3R-6
- 未新增任何 candidate
- 未复活 continuous_smoothing
- 未实际拆分 predict.py（保留给 Step 12）
- 未触碰 RISK-1 / RISK-2 / RISK-3 / RISK-7 / RISK-9 / RISK-10
  （各自 11A / 11B / 11C / 11D / 11F / 11G 设计）

本设计的修改路径：任何对 §4 拆分目标、§5 职责分区、§6 模块归属、§7 最小拆分
策略、§8 输出结构、§11 测试设计、§13 实施顺序、§9 与 11A/11B/11C 关系的
调整，都必须以**显式更新本文件**的方式提出。
