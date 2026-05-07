# 11C记录：Confidence Evaluator Separation Design

> 本设计针对 Step 09 / Step 10 中标记为 **MEDIUM_RISK** 的 RISK-3。
>
> 本轮**只写设计**：未改代码、未新增测试、未删文件、未移动文件、未写 DB、
> 未跑 validation、未 commit / push、未进入 Step 12、未进入 3R-5 / 3R-6、
> 未新增 candidate、未复活 continuous_smoothing、未实际实现 confidence
> evaluator、未顺手碰 RISK-1 / RISK-2 / RISK-8 / RISK-9。

---

## 1. 设计目的

把**置信度系统**从 projection / aggregator / renderer 中独立出来，落地为单一
模块 + 单一输出 `confidence_result`，回答 07C 核心问题：

> **"推演系统这次判断有多可信？否定系统这次判断有多可信？"**

修复后：

- 存在独立的 `services/confidence_evaluator.py` active engine（Step 12 创建）
- 输入：`projection_result` + `exclusion_result` + 历史命中率 / calibration tables
- 输出：07C §9 草案的 `confidence_system_result.v1`
- **不**修改 projection / exclusion 任一字段（07C §6 / §7）
- **不**生成 most_likely / most_unlikely / trading / hard / forced（07C §5）
- final_decision / final_report / renderer **只读** confidence_result（11B 已对齐）
- projection / exclusion **不读** confidence_result（07A §3.2 / 07B §3.2）

本设计**只**产出设计文档，Step 12 才实施 + commit。

---

## 2. 当前问题（confidence 逻辑散落清单）

### 2.1 逻辑散落地图

| 路径 | 角色 | 是否合规 | 后续动作 |
|---|---|---|---|
| `predict.py` v1 final_confidence（`_confidence_from_score` / `_raise_confidence` / `_lower_confidence` / `_normalize_confidence` / `_path_risk_from_confidence` 等） | v1 路径 projection 内自算 final_confidence + final_one_sentence | ❌ 违反 07A §5（推演不得输出 final_confidence）+ 07D §5 | RISK-8 / 11E 拆分 |
| `services/final_decision.py:288-317` | aggregator 重算 confidence + apply_preflight_influence 副作用 | ❌ 违反 07D §5 / §10 + 07C §8 | RISK-2 / 11B 已设计修除；11B Step 12 实施 |
| `services/projection_three_systems_renderer.py:893-909` `build_confidence_evaluator(v2_raw)` | 06Q 落地的 display 段：`negative_system_confidence` / `projection_system_confidence` / `overall_confidence` / `conflicts` / `reliability_warnings`；read-only reshape，**不** mutate v2_raw | ⚠️ 当前唯一**接近**合规的实现，但**位置错**：寄生在 renderer（display 层），不是独立 engine；同时直接读 `v2_raw`（含 RISK-1 / RISK-2 污染） | 11C / Step 12：**作为蓝本迁移到** 独立 engine；renderer 改为 read-only display |
| `services/contract_calibration_inputs.py` (line 1-32) | 自描述 "**diagnostic** tool — NOT a calibration engine"；read-only DB 查询 + 数据 gap 报告 | ✅ 合规：不 mutate / 不 import confidence_engine / 不调 trading | 保持现状作为 confidence engine 的 evidence source（input） |
| `services/exclusion_reliability_review.py` (574 行) | 否定可靠性 review（历史命中率） | ✅ 合规（属 07C 范畴的 evidence source） | 保持作为 confidence engine 的 evidence source（input） |
| `services/active_rule_pool*.py` (6 个) | offline 规则池 calibration / drift / promotion / validation / export | ✅ 合规（offline calibration） | 保持作为 calibration data source；参考 §9 |
| `confidence_engine.py` 根级 32 行 stub | step_1a v1 占位 | dead code（无 active import） | Step 14 cleanup 列入 |

### 2.2 关键问题

> 当前**没有**单一模块承担 07C 契约。

- `projection_three_systems_renderer.build_confidence_evaluator` 是当前唯一
  接近合规的实现，但它：
  1. **物理位置**在 display 层（renderer），不是独立 engine
  2. **读** `v2_raw` 整体（受 RISK-1 / RISK-2 污染）
  3. 输出 schema 与 07C §9 草案**字段差异**：用 `negative_system_confidence` /
     `projection_system_confidence` / `overall_confidence` / `conflicts` /
     `reliability_warnings`；07C §9 草案用 `projection_confidence` /
     `exclusion_confidence` / `agreement_status` / `conflict_level` /
     `combined_confidence` / `confidence_reasoning` / `sample_size_notes` /
     `calibration_notes` / `raw_evidence_refs`
  4. 缺 `non_mutation_confirmations` / `source_attribution` / target_date cutoff
- `final_decision.py` 与 `predict.py` 各自重算 confidence，与 renderer 的
  evaluator **三套不一致**

---

## 3. 违反的 contract

| contract | 章节 | 违规点 |
|---|---|---|
| 06 三系统独立原则 | §6 三系统正确关系 | 置信度系统未独立分权 |
| 07C 置信度 contract | §2 评价者非仲裁者 / §3.1 输入白名单 / §3.2 输入黑名单 / §3.3 在线 vs 离线 calibration / §4 输出字段 / §5 禁止字段 / §9 schema 草案 / §11 禁止数据流 | 缺独立模块；schema 不对齐；缺 future-leak guard；缺 non_mutation_confirmations |
| 07D | §3.1 final report 仅可读取 confidence_result | final_decision 自算 confidence（11B 修复）；renderer 自算 confidence（11C 范畴） |
| 11B | confidence_result 缺失时 final_confidence = unknown | 实现完整 confidence engine 才能让 11B 输出真实 level |

---

## 4. 设计目标

修复后必须满足：

1. 新增独立模块 `services/confidence_evaluator.py`
2. 公共 API：`build_confidence_result(...)`（详见 §5）
3. 输入：projection_result + exclusion_result + market_context + historical_context
   + calibration_context + target_date
4. 输出：严格符合 07C §9 草案的 `confidence_system_result.v1` schema
5. **不**修改 projection_result（07C §6）
6. **不**修改 exclusion_result（07C §7）
7. **不**生成 `most_likely_state` / `most_unlikely_state`（07C §5）
8. **不**输出 `trading_action` / `buy/sell/hold` / `simulated_trade` /
   `no_trade` / `hard_exclusion` / `forced_exclusion` / `required_decision` /
   `production_promotion` / `_PROTECTION_LAYER_CONNECTED` /
   `final_report_mutation`（07C §5）
9. **不**调用 LLM（无 `from services.openai_client import generate_text`）
10. **不**写 DB（read-only DB 查询 OK；不允许 INSERT / UPDATE）
11. **不**读取 future outcome（target_date 之后的真实数据）
12. **不**读取 2026 final-test range
13. final_decision / final_report / renderer **只读** confidence_result
14. projection / exclusion **不读** confidence_result（07A §3.2 / 07B §3.2）
15. 输出含 `non_mutation_confirmations`（保证不 mutate inputs）

---

## 5. 建议模块设计

> 以下为推荐设计；Step 12 实施时可微调，但必须保持契约边界。

### 5.1 模块位置

`services/confidence_evaluator.py`

### 5.2 公共 API

```python
def build_confidence_result(
    *,
    projection_result: dict[str, Any],
    exclusion_result: dict[str, Any],
    market_context: dict[str, Any] | None = None,
    historical_context: dict[str, Any] | None = None,
    calibration_context: dict[str, Any] | None = None,
    target_date: str | None = None,
    confidence_date: str | None = None,
    symbol: str = "AVGO",
) -> dict[str, Any]:
    """Build a confidence_system_result.v1 from projection/exclusion outputs.

    Read-only contract:
      - never mutates projection_result / exclusion_result / any context
      - never reads future outcomes (target_date is the cutoff for any
        calibration_context lookup)
      - never imports services.openai_client (no LLM)
      - never writes the DB (read-only DB queries are allowed for
        calibration tables that are themselves frozen artifacts)
      - never produces most_likely_state / most_unlikely_state / trading_*
      - returns a fresh dict; inputs are not modified
    """
```

约束：

- 函数体**不** import：`services.openai_client` / `services.exclusion_layer.run_exclusion_layer` / `services.main_projection_layer.build_main_projection_layer` / `services.final_decision.build_final_decision`
- 函数体允许 import：`services.exclusion_reliability_review` / `services.contract_calibration_inputs` / `services.projection_output_contract`（仅 schema validator）
- 入参全部 `kwargs only`（强制清晰契约）
- 返回**新 dict**，从不 alias 入参的子结构

### 5.3 内部辅助函数

| 内部函数 | 职责 |
|---|---|
| `_evaluate_projection_confidence(projection_result, historical_context, calibration_context, target_date)` | 仅评 projection；产出 level / score / reasoning / reliability_evidence |
| `_evaluate_exclusion_confidence(exclusion_result, historical_context, calibration_context, target_date)` | 仅评 exclusion；同上 |
| `_compute_agreement(projection_result, exclusion_result)` | 计算 `agreement_status` ∈ {aligned, partial_conflict, strong_conflict, unknown}（07C §10） |
| `_compute_conflict_level(agreement_status, projection_result, exclusion_result)` | 映射 conflict_level ∈ {none, low, medium, high, unknown}（07C §10 单调约束） |
| `_combine_confidence(projection_confidence, exclusion_confidence, agreement_status, conflict_level)` | 综合可信度（保守 min；冲突时进一步降级） |
| `_collect_evidence_refs(projection_result, exclusion_result, historical_context, calibration_context)` | 拼装 `raw_evidence_refs` 列表 |
| `_collect_reliability_warnings(...)` | 触发的可靠性告警 |
| `_collect_sample_size_notes(historical_context, calibration_context)` | 样本量说明 |
| `_collect_calibration_notes(calibration_context, target_date)` | 校准 / 漂移说明 |
| `_assert_no_mutation(...)` | 简单 sanity check（dict id 比较或 deep-equal） |

### 5.4 与现有 `build_confidence_evaluator` 的关系

`projection_three_systems_renderer.py:893-909` 的 `build_confidence_evaluator(v2_raw)`
是**现有可工作**的实现。Step 12 实施时：

- **逻辑可作为蓝本**：保留 conservative_combine 思想（min 两端 + 冲突再降一档）；
  保留 `_conflicts_from_v2` 的核心冲突检测（exclusion 排除 vs projection top1 重叠）
- **schema 必须改**：从 `negative_system_confidence` / `projection_system_confidence`
  / `overall_confidence` / `conflicts` 重写为 07C §9 的 `projection_confidence`
  / `exclusion_confidence` / `agreement_status` / `conflict_level` /
  `combined_confidence` 等字段
- **输入边界必须改**：从 `v2_raw`（整包，含污染）改为 `projection_result` +
  `exclusion_result` 显式只读
- **位置必须改**：从 renderer 寄生改为独立 module
- renderer 改为：从 `confidence_result` 渲染 display 段；不再自己计算

---

## 6. confidence_result schema

严格遵循 07C §9 草案：

```jsonc
{
  "schema_version": "confidence_system_result.v1",

  "confidence_date": "<YYYY-MM-DD>",     // 数据截止日
  "target_date": "<YYYY-MM-DD>",         // 目标交易日

  "system_name": "confidence_system",
  "question_answered": "system_reliability_evaluation",

  "projection_confidence": {
    "level": "low" | "medium" | "high" | "unknown",
    "score": null | <0.0–1.0>,
    "reasoning": [
      "...",                              // 中文短句
      "..."
    ]
  },
  "exclusion_confidence": {
    "level": "...",
    "score": null | <0.0–1.0>,
    "reasoning": [...]
  },

  "projection_reliability_evidence": [
    "history_hit_rate:<...>",
    "similar_pattern_size:<...>"
  ],
  "exclusion_reliability_evidence": [
    "rare_event_size:<...>",
    "non_occurrence_rate:<...>"
  ],

  "agreement_status": "aligned" | "partial_conflict" | "strong_conflict" | "unknown",
  "conflict_level": "none" | "low" | "medium" | "high" | "unknown",

  "combined_confidence": {
    "level": "...",
    "score": null | <0.0–1.0>,
    "reasoning": [...]
  },

  "confidence_reasoning": [
    "..."
  ],

  "reliability_warnings": [...],
  "sample_size_notes": [...],
  "calibration_notes": [...],

  "raw_evidence_refs": [
    "projection_result_ref:<...>",
    "exclusion_result_ref:<...>",
    "history_hit_rate_table:<...>"
  ],

  "non_mutation_confirmations": {
    "projection_result_mutated": false,
    "exclusion_result_mutated": false
  }
}
```

### 6.1 取值约束

- `level ∈ {low, medium, high, unknown}`
- `score ∈ [0.0, 1.0]` 或 `null`
- `level` 与 `score` 单调一致：`unknown → null`、`low → [0.0, 0.4]`、
  `medium → [0.4, 0.7]`、`high → [0.7, 1.0]`（具体阈值实现决定，但需在
  docstring 固定）
- `agreement_status ∈ {aligned, partial_conflict, strong_conflict, unknown}`
- `conflict_level ∈ {none, low, medium, high, unknown}`
- `agreement_status` 与 `conflict_level` 满足 07C §10 单调约束：
  - `aligned → conflict_level ∈ {none, low}`
  - `partial_conflict → conflict_level ∈ {low, medium}`
  - `strong_conflict → conflict_level ∈ {medium, high}`
  - `unknown → conflict_level == unknown`

### 6.2 禁止字段

```jsonc
// ❌ 不允许
{
  "most_likely_state": "...",                 // 属推演
  "most_unlikely_state": "...",               // 属否定
  "modified_projection": {...},
  "modified_exclusion": {...},
  "projection_correction": "...",
  "exclusion_correction": "...",
  "*_correction": "...", "*_override": "...", "*_mutation": "...",
  "hard_exclusion": true, "forced_exclusion": true,
  "required_decision": true,
  "trading_action": "...", "buy": ..., "sell": ..., "hold": ...,
  "simulated_trade": {...}, "no_trade": true,
  "production_promotion": true,
  "_PROTECTION_LAYER_CONNECTED": true,
  "final_report_mutation": {...}
}
```

---

## 7. 输入来源设计

### 7.1 允许读取（白名单）

按 07C §3.1：

- `projection_result`（**只读**；deepcopy 或 dict view）
- `exclusion_result`（**只读**；deepcopy 或 dict view）
- 原始市场数据（OHLCV）— 仅 `<= target_date`
- AVGO 自身行情 / NVDA / SOXX / QQQ 同行 — 仅 `<= target_date`
- 历史五状态表现（频率与样本量）— 仅 `<= target_date`
- 历史推演准确率（hit_rate by structure / regime）— 仅 `<= target_date`
- 历史否定准确率 — 仅 `<= target_date`
- 历史 false_exclusion / survival_case 表现 — 仅 `<= target_date`
- 历史样本数量
- 已定义的 market regime / 标签 — 仅 `<= target_date`
- 本地历史 logs / review records — 仅 `created_date <= target_date`
- calibration tables（视为已结案的 frozen artifacts）

### 7.2 禁止读取（黑名单）

按 07C §3.2 + §3.3：

- `target_date` 之后的市场真实结果（future outcome）
- 2026 final-test range
- trading result（模拟 / 真实交易）
- final_report 任何 mutation feedback
- hard / forced decision **作为指令输入**（07D §5 已禁止它存在）
- required decision **作为指令输入**
- LLM-generated free text（`services.openai_client`）

### 7.3 输入时间 cutoff guard

`build_confidence_result(... target_date=...)` 内部对每个 `historical_context`
/ `calibration_context` 中的时间序列、样本、review record，**必须**应用
`<= target_date` 过滤（或 `<` 视场景）。具体实现：

```python
def _filter_by_target_date(
    records: list[dict],
    target_date: str | None,
    field: str = "created_date",
) -> list[dict]:
    if not target_date:
        return list(records or [])
    cutoff = target_date  # ISO date string sort works lexicographically
    return [r for r in (records or []) if str(r.get(field) or "") <= cutoff]
```

> 与 RISK-7（11D）的 `memory_feedback cutoff guard` 同一思想；可共享 helper。

---

## 8. agreement / conflict 计算设计

按 07C §10 定义：

```python
def _compute_agreement(projection_result, exclusion_result) -> str:
    proj = _as_dict(projection_result)
    excl = _as_dict(exclusion_result)
    if not proj or not excl:
        return "unknown"

    most_likely = _str(proj.get("most_likely_state"))
    most_unlikely = _str(excl.get("most_unlikely_state"))

    if not most_likely or not most_unlikely:
        return "unknown"

    if most_likely == most_unlikely:
        return "strong_conflict"

    ranked_states = list(proj.get("ranked_states") or [])
    ranked_unlikely = list(excl.get("ranked_unlikely_states") or [])
    top2_likely = set(ranked_states[:2])
    top2_unlikely = set(ranked_unlikely[:2])

    if top2_likely & top2_unlikely:
        return "partial_conflict"

    return "aligned"
```

```python
def _compute_conflict_level(agreement_status, projection_result, exclusion_result) -> str:
    if agreement_status == "unknown":
        return "unknown"
    if agreement_status == "aligned":
        return "none"   # 或 "low" 视实现选择
    if agreement_status == "partial_conflict":
        return "low"    # 或 "medium" 取决于重叠深度
    if agreement_status == "strong_conflict":
        return "high"   # 或 "medium"
    return "unknown"
```

**重要**：

- 计算结果**仅**写入 confidence_result（`agreement_status` / `conflict_level`）
- **不**修改 projection_result / exclusion_result
- **不**触发任何对其他系统的副作用（07C §10 末段："冲突不代表改写"）

---

## 9. calibration 设计（在线 vs 离线）

### 9.1 离线 calibration（允许使用 future outcome 作为 label）

- 已存在的离线 infra：`services/active_rule_pool_calibration.py` /
  `services/active_rule_pool_drift.py` / `services/active_rule_pool_validation.py`
  / `services/historical_replay_training.py` / `services/avgo_1000day_training.py`
  / `scripts/summarize_confidence_calibration_inputs.py`
- 离线产物：`calibration_table.json` / `confidence_calibration.csv` / model
  weights 等 frozen artifact
- 离线训练**允许**使用历史 already-resolved outcome 作为 label（07C §3.3）

### 9.2 在线 inference（禁止 future outcome）

`build_confidence_result(...)` 是**在线**：

- 输入 `calibration_context` 应是**已 frozen 的 calibration table 引用**
  （路径或 dict），而**不是**实时查 outcome DB
- 内部如查 DB / 文件，**必须** target_date cutoff guard
- 如果 `calibration_context` 缺失，**降级**为 `unknown` / null score；**不**自行
  fallback 到读未来数据

### 9.3 缺失 calibration 时的行为

```python
if calibration_context is None or not calibration_context.get("ready"):
    projection_confidence = {
        "level": "unknown",
        "score": None,
        "reasoning": [
            "未接入 calibration_context，无法量化推演可信度",
            "fallback 为 unknown，待 calibration table 接入后恢复"
        ]
    }
    # exclusion_confidence 同上
    reliability_warnings.append("calibration_context 缺失，可信度评估降级为 unknown。")
```

> **绝对禁止**：在 calibration_context 缺失时 fallback 到 "暂时实现一个简单
> heuristic confidence"。这违反"评价者非仲裁者"原则，会让 confidence engine
> 退化成 final_decision 旧重算逻辑。

### 9.4 calibration_context 的来源

Step 12 实施时，`calibration_context` 可由以下路径产生：

- `services/contract_calibration_inputs.summarize_confidence_calibration_inputs(...)`
  作为只读 evidence source（注：它是 diagnostic，不是 engine）
- `services/exclusion_reliability_review` 输出作为 exclusion 可靠性 evidence
- 未来：专门的 frozen calibration table 文件（Step 12+ 接入）

---

## 10. 与现有模块的关系

| 模块 | 当前角色 | 11C / Step 12 之后角色 |
|---|---|---|
| `services/confidence_evaluator.py`（**新建**） | — | 唯一 ACTIVE_CONFIDENCE engine；07C §9 schema |
| `services/projection_three_systems_renderer.py:893-909` | 寄生在 renderer 的 confidence_evaluator 段（display + 算） | **改为 display-only**：从 `confidence_result` 渲染 display 段；不再自己计算；保留作为 read-only 展示层 |
| `services/final_decision.py` | RISK-2：自算 confidence | 11B 修复后只读 `confidence_result.combined_confidence.level`；不计算 |
| `predict.py` v1 final_confidence 内联（`_confidence_from_score` / `_raise_confidence` / `_lower_confidence`） | RISK-8：projection 内自算 | RISK-8 / 11E 拆分；改为读 `confidence_result` 或不暴露 |
| `services/contract_calibration_inputs.py` | diagnostic / data prep（read-only） | 保持现状；作为 confidence_evaluator 的可选 evidence source |
| `services/exclusion_reliability_review.py` | 否定可靠性历史命中率 review | 保持现状；作为 confidence_evaluator 的 exclusion evidence input |
| `services/active_rule_pool*.py` (6 个) | offline calibration / rule pool | 保持现状；产出可作为 frozen calibration tables |
| `confidence_engine.py` 根级 stub | 死代码 | Step 14 cleanup 列入；**不**复用 |

> **关键**：11C **不**让 renderer 内的 `build_confidence_evaluator(v2_raw)`
> 立即消失。Step 12 推荐**两阶段**接入（详见 §11）。

---

## 11. 最小代码修改设计

> 本节**只描述设计**，Step 12 才实施。

### 11.1 推荐两阶段实施

**阶段 A（Step 12 11C-A commit）：standalone evaluator + tests，不接 active path**

- 新增 `services/confidence_evaluator.py`，实现 `build_confidence_result(...)`
- 新增 `tests/test_confidence_evaluator.py`，含 §12 列出的 contract enforcement test
- **不**修改 `final_decision.py` / `projection_orchestrator_v2.py` /
  `projection_three_systems_renderer.py` / `predict.py`
- evaluator 处于"experimental boundary module"状态：测试通过即可入库
- commit message：`feat(boundary): add standalone confidence evaluator (RISK-3 step A)`

**阶段 B（Step 12 11C-B commit，可选；建议在 11B 修复完成之后做）**

- 在 `services/projection_orchestrator_v2.py` 中**调起** `build_confidence_result(...)`
  并把结果挂在 orchestrator 输出的并列字段 `confidence_result`
- 在 `services/final_decision.py:build_final_decision(... confidence_result=...)`
  入参中真正传入 `confidence_result`（11B 已设计预留入参）
- 修改 `services/projection_three_systems_renderer.build_confidence_evaluator`
  为 read-only display：从 `confidence_result` 渲染；删除自己 conflict / overall
  计算逻辑（保留作为 fallback 展示，但 disabled）
- contract test 校验：`final_confidence == confidence_result.combined_confidence.level`
- commit message：`fix(boundary): wire confidence_result into final_decision and renderer (RISK-3 step B)`

### 11.2 阶段 A vs 阶段 B 顺序约束

> **绝对约束**：阶段 B 必须在 11B（RISK-2 final_decision purification）之后做。

理由：

- 11B 已为 `final_decision.build_final_decision(... confidence_result=None)` 留好入参
- 阶段 B 只是把 `None` 改为真正传入的 `confidence_result`
- 如果阶段 B 早于 11B，会与 11B 的 final_decision 重写冲突
- 推荐顺序：**11A → 11B → 11C-A → 11C-B → 11D → 11E → 11F → 11G**

### 11.3 阶段 A 内最小修改清单

| 文件 | 动作 |
|---|---|
| `services/confidence_evaluator.py`（新建） | ~300 行：API + helpers + schema |
| `tests/test_confidence_evaluator.py`（新建） | §12 列出的 9+ 测试 |
| 其他模块 | **不动** |

### 11.4 阶段 B 内最小修改清单

| 文件 | 动作 |
|---|---|
| `services/projection_orchestrator_v2.py` | 在调 `build_final_decision` 之前 + 之后插入 `confidence_result = build_confidence_result(...)`；把 `confidence_result` 挂在顶层输出 |
| `services/final_decision.py` | 把 `confidence_result=None` 默认替换为真实传入；其他不变（11B 已铺好） |
| `services/projection_three_systems_renderer.py` | `build_confidence_evaluator` 改为 read-only display；保留旧 schema 兼容字段名（`negative_system_confidence` / `projection_system_confidence` / `overall_confidence`），但**值**从 `confidence_result` 派生而非自算 |
| `tests/test_projection_three_systems_renderer.py` | 改写 confidence 段断言：从"自算 level"改为"等于 confidence_result 派生 level" |
| 其他模块 | **不动**（特别是 predict.py / ai_summary 留给 RISK-8 / RISK-9） |

### 11.5 不动其他模块

- **不**改 `predict.py`（保留给 RISK-8 / 11E）
- **不**改 `ai_summary.py`（保留给 RISK-9 / 11F）
- **不**改 `exclusion_layer.py` / `main_projection_layer.py`（保留给 RISK-1 / 11A）
- **不**改 30+ 下游 `final_direction` / `final_confidence` 消费者
- **不**改 `confidence_engine.py` 根级 stub（dead code，Step 14 cleanup）
- **不**改 `active_rule_pool*.py` / `historical_replay_training.py` 等 offline infra

---

## 12. Contract enforcement tests 设计

> 本节**只描述测试设计**，Step 12 才新增测试代码。

### 12.1 阶段 A 必须新增的测试

| 测试名（建议） | 验证内容 |
|---|---|
| `test_confidence_result_schema` | `build_confidence_result(...)` 返回 dict 含全部 07C §9 草案字段；`schema_version == "confidence_system_result.v1"`；`system_name == "confidence_system"`；`question_answered == "system_reliability_evaluation"` |
| `test_confidence_evaluator_does_not_mutate_projection_or_exclusion` | 调用前后 deepcopy 对比 `projection_result` / `exclusion_result`；断言 dict 等价（id 可不同但 deep_equal） |
| `test_confidence_evaluator_detects_strong_conflict` | 注入 `projection_result.most_likely_state == exclusion_result.most_unlikely_state`，断言 `agreement_status == "strong_conflict"` 且 `conflict_level ∈ {medium, high}`；同时 `projection_result` / `exclusion_result` 未变 |
| `test_confidence_evaluator_detects_aligned` | 注入互不冲突的状态对，断言 `agreement_status == "aligned"` 且 `conflict_level ∈ {none, low}` |
| `test_confidence_evaluator_detects_partial_conflict` | 注入 most_likely ≠ most_unlikely 但 top2 重叠，断言 `agreement_status == "partial_conflict"` |
| `test_confidence_evaluator_detects_unknown_when_input_missing` | projection_result / exclusion_result 任一为空，断言 `agreement_status == "unknown"` 且 `conflict_level == "unknown"` |
| `test_confidence_evaluator_missing_calibration_returns_unknown` | 不传 `calibration_context`（None），断言 `projection_confidence.level == "unknown"` / `score is None` 且 `reliability_warnings` 含相应提示 |
| `test_confidence_evaluator_no_trading_or_hard_fields` | 断言返回 dict **不含** `trading_action` / `buy` / `sell` / `hold` / `simulated_trade` / `no_trade` / `hard_exclusion` / `forced_exclusion` / `required_decision` / `production_promotion` / `_PROTECTION_LAYER_CONNECTED` / `final_report_mutation` 任一字段 |
| `test_confidence_evaluator_no_future_outcome_access` | 注入 `historical_context` 含日期 `> target_date` 的样本；断言 evaluator 输出**不**反映这些样本（用 evidence_refs 间接验证：refs 中不出现 future date） |
| `test_confidence_evaluator_no_llm_import` | 静态扫描 `services/confidence_evaluator.py`，断言**不含** `from services.openai_client` / `import openai` 任一 import |
| `test_confidence_evaluator_score_level_monotonic` | 遍历构造 score ∈ {0.1, 0.5, 0.85, None} 的输入，断言对应 level 满足 `unknown / low / medium / high` 单调映射 |
| `test_confidence_evaluator_no_module_writes_db` | 静态扫描断言**不含** `INSERT` / `UPDATE` / `DELETE` SQL；DB 查询仅 `SELECT` |
| `test_confidence_evaluator_non_mutation_confirmations` | 断言返回 dict 含 `non_mutation_confirmations` 且 `projection_result_mutated == False` / `exclusion_result_mutated == False` |
| `test_confidence_evaluator_does_not_produce_most_likely_or_most_unlikely` | 断言返回 dict **不含** `most_likely_state` / `most_unlikely_state` 字段 |

### 12.2 阶段 B 必须新增的测试

| 测试名 | 验证内容 |
|---|---|
| `test_orchestrator_attaches_confidence_result` | 调 `run_projection_v2(...)`，断言顶层输出含 `confidence_result` 字段且 schema 合规 |
| `test_final_decision_uses_confidence_result_combined_level` | 注入 `confidence_result.combined_confidence.level == "high"`，调 `build_final_decision(... confidence_result=...)`，断言 `final_confidence == "high"` |
| `test_three_systems_renderer_confidence_section_from_confidence_result` | 调 renderer，断言 `confidence_evaluator` display 段的 level 等于 `confidence_result` 对应字段；不再自己计算 |

### 12.3 测试不允许的内容

- 测试**不**应允许 evaluator 修改 projection_result / exclusion_result
- 测试**不**应允许 evaluator 输出 most_likely / most_unlikely / trading
- 测试**不**应允许 evaluator 在 `calibration_context` 缺失时 fallback 到非
  unknown 的 confidence level
- 测试**不**应允许 evaluator 调 LLM
- 测试**不**应允许 evaluator 写 DB

---

## 13. 不允许的修复方式

以下修复方式**不**符合 contract，Step 12 实施时**禁止**：

1. **不**允许在 `final_decision.py` 里继续重算 confidence（11B 已修除；11C 不
   恢复）
2. **不**允许在 projection system 内输出 `confidence_score` / `confidence_level`
   （07A §5）
3. **不**允许在 exclusion system 内输出 `confidence_score` / `confidence_level`
   （07B §5）
4. **不**允许用 LLM（`services.openai_client.generate_text`）生成 confidence
5. **不**允许读取**当前 target_date 之后**的 outcome
6. **不**允许把 `confidence_result` 回写到 `projection_result` /
   `exclusion_result`（07C §6 / §7）
7. **不**允许生成 `trading_action` / `buy` / `sell` / `hold` / `simulated_trade`
   / `no_trade` / `hard_exclusion` / `forced_exclusion` / `required_decision`
8. **不**允许复活 `continuous_smoothing` 作为 confidence shortcut（07C §12）
9. **不**允许在 `calibration_context` 缺失时 fallback 到 "暂时实现一个 heuristic
   confidence"（详见 §9.3）
10. **不**允许 cleanup 与 boundary fix 混 commit
11. **不**允许 large rewrite：每个 fix commit 控制在最小行数
12. **不**允许进入 3R-5 / 3R-6
13. **不**允许在 11C 内顺手修 RISK-1 / RISK-2 / RISK-7 / RISK-8 / RISK-9 /
    RISK-10
14. **不**允许在 11C 阶段 A commit 内同时修改 final_decision（必须留到阶段 B）
15. **不**允许通过 `confidence_engine.py` 根级 stub 的 `evaluate_confidence(...)`
    迂回实现（dead code，Step 14 cleanup；11C 不复用）

---

## 14. Step 12 实施顺序建议

> Step 12 才允许执行；本轮**不**实施。

### 14.1 阶段 A（standalone evaluator）

1. **新增 `tests/test_confidence_evaluator.py`**（failing；evaluator 还没实现）
   - 加 §12.1 列出的 14 个新测试
   - 此时所有测试 fail（红灯）

2. **新增 `services/confidence_evaluator.py`**
   - 实现 `build_confidence_result(...)`
   - 实现 §5.3 的内部辅助函数
   - 严格遵守 §6 schema / §7 输入边界 / §8 agreement 计算 / §9 calibration 降级
   - **不**修改任何现有模块

3. **跑 focused tests**：`pytest tests/test_confidence_evaluator.py`
   - 期待全部转绿

4. **跑 full pytest**
   - 期待无回归（因为没动现有模块）

5. **独立 commit**
   - commit message：`feat(boundary): add standalone confidence evaluator (RISK-3 step A)`
   - 单 commit；**不**接 active path

### 14.2 阶段 B（接入 active path，前置依赖：11B Step 12 已完成）

1. **新增 §12.2 的 3 个 contract enforcement test**（failing）

2. **修改 `services/projection_orchestrator_v2.py`**
   - 在合适位置（在 final_decision 之前）调 `build_confidence_result(...)`
   - 顶层输出加 `confidence_result` 字段

3. **修改 `services/final_decision.py`**
   - 把 `confidence_result=None` 默认替换为真实传入
   - 11B 已铺好这一切；只需 wire 起来

4. **修改 `services/projection_three_systems_renderer.py:893-909`**
   - `build_confidence_evaluator` 改为 read-only display
   - 保留旧 schema 字段名（`negative_system_confidence` /
     `projection_system_confidence` / `overall_confidence`）以保兼容
   - 字段值从 `confidence_result` 映射而来；不自己 conflict / overall 计算

5. **改写 `tests/test_projection_three_systems_renderer.py` 中 confidence 段断言**

6. **跑全量 pytest**

7. **手动 spot-check UI**

8. **独立 commit**
   - commit message：`fix(boundary): wire confidence_result into final_decision and renderer (RISK-3 step B)`

### 14.3 阶段 A vs 阶段 B 时间点选择

如果不确定阶段 B 何时做：

- **可以**单独提交阶段 A（feat 性质），再等 11B 完成后做阶段 B
- **不可以**只做阶段 B 而跳过阶段 A（违反"先有 engine 再接入"）
- **不可以**在阶段 A commit 中顺手改任何 active path

---

## 15. 与 11B / 11E 的关系

| 步骤 | 与 11C 的关系 |
|---|---|
| **11B**（RISK-2 final_decision purification） | 已设计 `confidence_result=None` 时 final_confidence = unknown；11C 阶段 B 把 None 替换为真实传入；**11B 必须先于 11C 阶段 B** |
| **11E**（RISK-8 predict.py split） | predict.py v1 final_confidence 应被移除；移除后改为读 `confidence_result.combined_confidence.level`（如果 v1 路径仍保留）或彻底废弃 v1；**11E 可以在 11C 阶段 A 之后做**；**不应在 11C 阶段 A commit 中顺手改 predict.py** |
| **11D**（RISK-7 memory_feedback cutoff guard） | 11C 与 11D 共享 target_date cutoff guard 思想；可共享 helper（例如 `_filter_by_target_date`）；但实施顺序无强依赖 |
| **11F**（RISK-9 ai_summary source attribution） | confidence_evaluator **绝不**调 LLM；ai_summary 修复后可读 `confidence_result` 但**不**修改它 |

> **三者互不替代**：11B 不能假装实现 confidence engine；11C 不能在没有 11B
> 的情况下接入 final_decision；11E 不能借机重新实现 confidence。

---

## 16. 回滚策略

### 16.1 失败模式

如果在 Step 12 实施过程中：

- evaluator 输出**质量太差**（confidence 全部 unknown，UI 展示空白）
- 阶段 B 接入后导致 final_decision 取值过保守，user 觉得"什么都不可信"
- contract test 暴露 evaluator 内部有未发现的 mutation

### 16.2 回滚原则

> **不**回退到 final_decision 重算 confidence；**不**回退到 renderer 寄生计算。

正确的回滚序列：

1. **阶段 A 失败**：直接 `git revert` 阶段 A commit；保留旧的 renderer 寄生
   evaluator；继续设计 / 测试新 evaluator
2. **阶段 B 失败**：
   - `git revert` 阶段 B commit
   - 保留阶段 A 的 standalone evaluator（experimental boundary module 状态）
   - final_decision 回到 `confidence_result=None` → final_confidence = unknown
     状态（11B 默认行为）
   - **不**恢复 final_decision 旧重算逻辑
   - **不**恢复 renderer 自己计算 conflict
3. **必要时保留 deprecated experimental flag**：
   - 添加 feature flag `ENABLE_CONFIDENCE_EVALUATOR_WIRING = False`
   - 默认关闭；UI 显示 unknown
   - flag 打开时启用 evaluator
   - flag 默认值 / 行为必须有显式 docstring 说明
4. 任何回滚动作**仍不**允许 `_apply_preflight_influence` 副作用重新生效

### 16.3 不允许的"回滚捷径"

- **不**允许悄悄把 final_decision 加减分恢复
- **不**允许把 evaluator 改成 LLM 占位
- **不**允许跳过阶段 A 直接修改 renderer 内的 `build_confidence_evaluator`
- **不**允许 `git commit --amend` 隐藏违规

---

## 17. 严守边界

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
- 未实际实现 confidence evaluator（保留给 Step 12 阶段 A）
- 未触碰 RISK-1 / RISK-2 / RISK-7 / RISK-8 / RISK-9 / RISK-10
  （各自 11A / 11B / 11D / 11E / 11F / 11G 设计）

本设计的修改路径：任何对 §4 设计目标、§5 模块设计、§6 schema、§7 输入边界、
§9 calibration 设计、§11 最小代码修改、§12 测试设计、§14 Step 12 实施顺序、
§15 与 11B / 11E 关系的调整，都必须以**显式更新本文件**的方式提出。
