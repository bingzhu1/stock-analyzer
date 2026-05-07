# 11B记录：Final Decision Aggregator Purification Design

> 本设计针对 Step 09 / Step 10 中标记为 **HIGH_RISK** 的 RISK-2。
>
> 本轮**只写设计**：未改代码、未新增测试、未删文件、未移动文件、未写 DB、
> 未跑 validation、未 commit / push、未进入 Step 12、未进入 3R-5 / 3R-6、
> 未新增 candidate、未复活 continuous_smoothing、未实际修任何 RISK、
> 未顺手碰 RISK-1 / RISK-3 / RISK-8 / RISK-9。

---

## 1. 设计目的

让 `services/final_decision.py` 不再充当**第四个判断系统**，回到 07D 契约下
"aggregate / display / annotate"的本职：

- **不**翻 `final_direction`
- **不**重算 `final_confidence`
- **不**用 preflight 影响最终输出
- 缺三系统输出时，输出 `unknown` / `unavailable` 占位，**不**自行补算

修复后 `final_decision` 是**纯 aggregator + formatter**：从三系统输出 + display
metadata 拼装 final_report 字段，不引入新判断。

本设计**只**产出设计文档，Step 12 才实施 + commit。

---

## 2. 当前违规路径

### 2.1 `services/final_decision.py` 三处违规

#### 违规点 ① — direction 翻转（`:280-286`）

```python
final_direction = primary_direction
if (
    primary_direction in {"偏多", "偏空"}
    and peer_adjustment_label == "downgrade"
    and _direction(peer.get("adjusted_direction")) == "中性"
):
    final_direction = "中性"        # ← aggregator 自己翻方向
```

`primary_direction` 来自 `primary_analysis.direction`（属推演输出）。aggregator
用"peer downgrade + peer.adjusted_direction == 中性"这一**新规则**，把推演的
"偏多/偏空"翻成"中性"，写入 `final_direction`。这是把推演结果改写。

#### 违规点 ② — confidence 重算（`:288-303`）

```python
score = _confidence_score(primary_confidence)
if primary_direction == "中性":
    score = min(score, 1)
elif peer_adjustment_label in {"reinforce_bullish", "reinforce_bearish"} and historical_impact == "support":
    score += 1                      # ← 新规则
elif peer_adjustment_label == "downgrade":
    score -= 1                      # ← 新规则

if historical_impact == "caution":
    score -= 1                      # ← 新规则
elif historical_impact == "missing":
    score -= 1                      # ← 新规则

if peer_missing and historical_impact == "missing":
    score = min(score, 1)           # ← 新规则

final_confidence = _confidence_from_score(score)
```

aggregator 用 5 条加减分规则**重算** confidence，写入 `final_confidence`。
这是把可信度评价从 confidence system（07C）抢到 aggregator（07D）。

#### 违规点 ③ — preflight influence（`:313-317`）

```python
matched_rules: list[Any] = list(preflight_layer.get("matched_rules") or [])
final_confidence, risk_level, preflight_influence = _apply_preflight_influence(
    matched_rules, final_confidence, risk_level
)
```

`_apply_preflight_influence(...)`（`:61-115`）按 severity → effect 把
matched_rules 转成 `lower_confidence` / `raise_risk` 副作用，**降级**
final_confidence 一档 / **提升** risk_level 一档。这是 final_decision 自己执行
"hard / forced 风格"的规则降级。

### 2.2 唯一 active caller

- 仅 `services/projection_orchestrator_v2.py` 调 `build_final_decision()`
  （grep 验证；非测试 import 仅此一处）。
- `predict.py` 走 v1 路径，自己有一套 final_confidence 计算（属 RISK-8，
  本设计**不**触碰）。

### 2.3 现有测试对违规行为的依赖

| 测试断言 | 行 | 依赖 |
|---|---|---|
| `final_direction == "中性"` | `tests/test_final_decision.py:272` | 违规点 ① direction 翻转 |
| `final_confidence == "medium"` / `"low"` 等具体 level | `:141-142, 160-161, 181-182, 208-209` | 违规点 ② confidence 重算 |
| `preflight_influence` shape + applied_effects 行为 | `:278-367`（多个 test） | 违规点 ③ preflight_influence |

> Step 12 会需要把这些测试**改写**为 contract enforcement test
> （详见 §9.2）。

### 2.4 下游对 final_direction / final_confidence 的消费

`grep "final_direction\|final_confidence"` 显示 30+ 个 services / ui 文件
**消费**这两个字段（renderer / summary / record store / outcome / contract /
review / UI），但它们的角色是**展示**或**记录**，不是计算。Step 12 修复后
这些消费者拿到的 `final_direction` 必须严格等于 `primary_direction`（07D §10
"句句必有出处"）；schema 不变。

---

## 3. 违反的 contract

| contract | 章节 | 违规点 |
|---|---|---|
| 06 三系统独立原则 | §6 三系统正确关系 / §7 第 6 条 "final report 改写任一系统结果" | aggregator 改写 projection 方向 / 改写 confidence |
| 07A 推演 contract | §8 推演与 final report 边界 ("final report 不得改写推演输出") | `final_direction = "中性"` 改写 most_likely_state 的方向语义 |
| 07C 置信度 contract | §2 评价者非仲裁者 / §8 与 final report 边界 ("final report 不得把 confidence_result 回写") + §11 禁止数据流（hard / forced decision） | aggregator 重算 confidence；preflight 强制降级（"hard 风格"） |
| 07D final report contract | §2 展示者非决策者 / §5 禁止 `modified_*` / `overridden_*` / `corrected_*` / `final_report_mutation` / §10 combined_user_summary "句句必有出处" / §11 禁止 `final_report → hard / forced decision` | direction 翻转 + confidence 重算 + preflight forced 降级 |

---

## 4. 修复目标

修复后 `services/final_decision.py` 必须满足：

1. `final_direction` **严格等于** `primary_analysis.direction`
   （或 `primary_missing` 时 `unknown`）
2. `final_confidence` **严格等于** `confidence_result.combined_confidence.level`
   （来自 confidence_result，不是 primary_analysis.confidence）；
   **未接入** confidence_result 时填 `unknown` / `unavailable`，**不**自行计算
3. `risk_level` 不再由 aggregator 内部 `_risk_level()` / preflight rules 计算；
   仅可作为**展示标签**透传 confidence_result.reliability_warnings 类信息
4. **没有** `_apply_preflight_influence` 或等价副作用
5. preflight 信息**仅以** display warning / risk_disclosure / source_attribution
   形式出现；**不**改变任何 system result
6. 如未提供 `confidence_result`：
   - `final_confidence = "unknown"`
   - `agreement_or_conflict_section = {agreement_status: "unknown", conflict_level: "unknown"}`
   - 在 `warnings` 里加 `"final_decision 未接入 confidence_result，可信度展示为 unknown。"`
7. `combined_user_summary` 的每一句话必须可以追溯到 projection / exclusion /
   confidence / preflight warning 之一；附 `source_attribution` 列表
8. 输出**包含** `non_mutation_confirmations`：所有 `*_mutated` /
   `*_overridden` / `*_recomputed` / `preflight_applied_as_decision` 字段恒为 `false`
9. 输出**禁止包含** `trading_action` / `buy` / `sell` / `hold` / `simulated_trade`
   / `no_trade` / `hard_exclusion` / `forced_exclusion` / `required_decision` /
   `production_promotion` / `_PROTECTION_LAYER_CONNECTED` / `final_report_mutation`
10. schema_version 升级为 `final_report_aggregator_result.v1`（与 07D §9 草案对齐）
11. 既有 `kind: "final_decision"` 字段保留作为兼容 alias（避免 30+ 下游
    消费者破坏）；新加 `system_name: "final_report_aggregator"`

---

## 5. 最小代码修改设计

> 本节**只描述设计**，Step 12 才实施。

### 5.1 修改 `build_final_decision(...)` 签名

新增可选入参 `confidence_result`：

```python
def build_final_decision(
    *,
    primary_analysis: dict[str, Any],
    peer_adjustment: dict[str, Any] | None = None,
    historical_probability: dict[str, Any] | None = None,
    preflight: dict[str, Any] | None = None,
    confidence_result: dict[str, Any] | None = None,  # ← 新增（可选）
    exclusion_result: dict[str, Any] | None = None,   # ← 新增（可选，仅展示）
    symbol: str = "AVGO",
) -> dict[str, Any]:
```

`confidence_result` 默认 `None`（与 11C 解耦：本次 fix 不强制 11C 完成）。
`exclusion_result` 仅作为展示输入；不影响任一计算。

### 5.2 删除 / 禁用违规分支

- 删除 `:280-286` direction 翻转分支
- 删除 `:288-303` confidence 加减分分支
- 删除 `:313-317` `_apply_preflight_influence(...)` 调用
- `_apply_preflight_influence` 函数本体保留为 dead code（Step 14 cleanup
  阶段统一删除）；本次 fix **不**单独删除函数定义，避免与 cleanup 混淆

### 5.3 重写最终结果装配

```python
final_direction = primary_direction      # ← 严格透传，不翻转

if confidence_result is not None and confidence_result.get("ready"):
    cc = _as_dict(confidence_result.get("combined_confidence"))
    final_confidence = str(cc.get("level") or "unknown")
    agreement_status = str(confidence_result.get("agreement_status") or "unknown")
    conflict_level = str(confidence_result.get("conflict_level") or "unknown")
else:
    final_confidence = "unknown"
    agreement_status = "unknown"
    conflict_level = "unknown"
    warnings.append("final_decision 未接入 confidence_result，可信度展示为 unknown。")

risk_level = "unknown"  # 改为透传 confidence_result.reliability_warnings；
                        # 11C 完成后再具体化
```

### 5.4 preflight 转为 display-only

```python
matched_rules = list(_as_dict(preflight).get("matched_rules") or [])
preflight_count = len(matched_rules)

# preflight 不再改 final_confidence / risk_level
# 仅作为展示信息出现
preflight_warnings = [
    f"历史规则提醒：{rule.get('summary') or rule.get('rule_id') or '未命名规则'}"
    for rule in matched_rules if isinstance(rule, dict)
]
warnings.extend(preflight_warnings)

preflight_display = {
    "matched_rule_count": preflight_count,
    "applied_effects": [],          # ← 永远空：preflight 不再 apply
    "summary": (
        f"命中 {preflight_count} 条历史规则提醒（仅展示，不影响最终结论）。"
        if preflight_count else "未命中会影响最终结论的历史规则。"
    ),
}
```

### 5.5 添加 source_attribution + non_mutation_confirmations

```python
source_attribution = [
    {"section": "projection", "field": "direction",
     "source_field": "primary_analysis.direction"},
    {"section": "exclusion", "field": "most_unlikely_state",
     "source_field": "exclusion_result.most_unlikely_state"} if exclusion_result else None,
    {"section": "confidence", "field": "level",
     "source_field": "confidence_result.combined_confidence.level"} if confidence_result else None,
    {"section": "preflight", "field": "warnings",
     "source_field": "preflight.matched_rules[*]"} if preflight_count else None,
]
source_attribution = [s for s in source_attribution if s is not None]

non_mutation_confirmations = {
    "projection_result_mutated": False,
    "exclusion_result_mutated": False,
    "confidence_result_mutated": False,
    "final_direction_overridden": False,
    "confidence_recomputed": False,
    "preflight_applied_as_decision": False,
}
```

### 5.6 不动其他模块

- **不**改 `services/projection_three_systems_renderer.py`（它是 RISK-3 / 11C
  设计范畴）
- **不**改 `services/projection_narrative_renderer.py` / `predict_summary.py`
  （CLEAN，schema 透传）
- **不**改 `services/projection_orchestrator_v2.py` 的整体调用结构；只在
  调用 `build_final_decision(...)` 时新加 `confidence_result=` 关键字
  （11C 实现前传 `None`）
- **不**改 30+ 下游消费者（保持 `final_direction` / `final_confidence` /
  `kind: "final_decision"` 字段名兼容）

### 5.7 修改原则总结

- **删 3 段决策逻辑**（direction 翻转 + confidence 加减分 + preflight apply）
- **加 1 个 confidence_result 入参**（默认 None，Step 12 不强制 11C 完成）
- **加 source_attribution + non_mutation_confirmations 输出**
- **不**破 schema 兼容（`kind: "final_decision"` / `final_direction` /
  `final_confidence` / `risk_level` 字段名保留）
- **不**改 UI / 不改下游记录 / 不改 narrative

---

## 6. 输出结构设计

修复后 `build_final_decision(...)` 返回 dict 示例：

```jsonc
{
  // 兼容旧 schema（保持 30+ 下游消费者不破）
  "kind": "final_decision",
  "symbol": "AVGO",
  "ready": true,
  "final_direction": "偏多",          // ← 严格 == primary_analysis.direction
  "final_confidence": "unknown",     // ← 来自 confidence_result.combined_confidence.level；缺则 unknown
  "risk_level": "unknown",           // ← 透传或 unknown
  "direction": "偏多",                // 兼容 alias
  "confidence": "unknown",           // 兼容 alias

  // 新 schema（与 07D §9 对齐）
  "schema_version": "final_report_aggregator_result.v1",
  "system_name": "final_report_aggregator",
  "question_answered": "aggregate_three_system_outputs",

  "projection_section": {
    "source_schema_version": "projection_system_result.v1",
    "most_likely_state": "<from projection_v2_raw.main_projection.predicted_top1.state>",
    "ranked_states": [...],
    "display_summary": "..."
  },
  "exclusion_section": {
    "source_schema_version": "exclusion_system_result.v1",
    "most_unlikely_state": "<from exclusion_result>",
    "display_summary": "..."
  },
  "confidence_section": {
    "source_schema_version": "confidence_system_result.v1",
    "level": "unknown",
    "display_summary": "未接入 confidence system，可信度展示为 unknown。"
  },
  "agreement_or_conflict_section": {
    "agreement_status": "unknown",
    "conflict_level": "unknown",
    "display_summary": "..."
  },

  "combined_user_summary": "...",   // 每句必有出处
  "risk_disclosure": [...],
  "evidence_summary": [...],
  "raw_evidence_refs": [...],

  "source_attribution": [
    {"section": "projection", "field": "direction", "source_field": "primary_analysis.direction"},
    ...
  ],

  "non_mutation_confirmations": {
    "projection_result_mutated": false,
    "exclusion_result_mutated": false,
    "confidence_result_mutated": false,
    "final_direction_overridden": false,
    "confidence_recomputed": false,
    "preflight_applied_as_decision": false
  },

  // 兼容 layer_contributions / decision_factors / why_not / source_snapshot 等旧字段
  "layer_contributions": {...},
  "decision_factors": [...],
  "why_not_more_bullish_or_bearish": "...",
  "source_snapshot": {...},

  // preflight 改为 display-only
  "preflight_influence": {
    "matched_rule_count": 0,
    "applied_effects": [],          // ← 永远空
    "summary": "..."
  },

  "warnings": [...]
}
```

### 6.1 禁止字段

```jsonc
// ❌ 不允许出现
{
  "modified_projection": {...},
  "overridden_most_likely_state": "...",
  "corrected_confidence": "...",
  "decision_after_preflight": "...",
  "override_reason": "...",
  "trading_action": "...",
  "buy": "...", "sell": "...", "hold": "...",
  "simulated_trade": {...},
  "no_trade": true,
  "hard_exclusion": true,
  "forced_exclusion": true,
  "required_decision": true,
  "production_promotion": true,
  "_PROTECTION_LAYER_CONNECTED": true,
  "final_report_mutation": {...}
}
```

### 6.2 兼容性边界

- `final_direction` 必须 == `primary_direction`（test 验证）
- `final_confidence` 必须 == confidence_result.combined_confidence.level
  或 `"unknown"`（test 验证）
- `preflight_influence.applied_effects` 必须 == `[]`（test 验证）
- `non_mutation_confirmations.*_mutated` / `*_overridden` / `*_recomputed` 必须
  恒为 `false`（test 验证）

---

## 7. Preflight 信息处理设计

> preflight 在修复后**只能展示**，**不能**变成判断。

| 用途 | 允许 | 禁止 |
|---|---|---|
| `risk_disclosure` 文本列表 | ✅ "本次命中 N 条历史规则提醒，仅供参考" | ❌ "本次因历史规则触发降级，置信度从 high 降为 medium" |
| `evidence_summary` 引用 | ✅ "preflight: rule_id=X" | ❌ 把 rule.severity 转成 score |
| `warnings` 文本 | ✅ "命中 N 条规则提醒（仅展示）" | ❌ 自动 lower_confidence |
| `source_attribution` | ✅ `{section: "preflight", source_field: "preflight.matched_rules[*]"}` | ❌ 写入 `final_confidence` 来源 |

**禁止**用途：

- direction override
- confidence override / lower_confidence
- risk raise（除非来自 confidence_result 的 reliability_warnings 透传）
- hard / forced / required
- no_trade / trading_action / buy / sell / hold
- projection mutation
- exclusion mutation

---

## 8. 兼容性风险

### 8.1 测试层

| 测试 | 当前行为 | Step 12 处理 |
|---|---|---|
| `tests/test_final_decision.py:96-97, 121-122` `偏多/偏空 + high confidence` 断言 | 期待 `final_confidence == "high"`（来自 primary_analysis.confidence == "high"） | **保留断言但改语义**：测试改成"final_confidence == primary_confidence 或 unknown"（11C 前默认 unknown） |
| `:141-142, 160-161, 181-182` `final_confidence == "medium"` | 来自加减分重算 | **重写**：断言"final_confidence ∈ {primary_confidence, unknown}"，移除依赖加减分逻辑 |
| `:208-209` `final_confidence == "low"` | 来自重算 | 同上 |
| `:224-225` `unknown` 路径 | primary missing → unknown | **保留** |
| `:272-273` `final_direction == "中性"` | 依赖 direction 翻转分支 | **改写**：断言"final_direction == primary_direction"；为这种 input scenario，断言"中性"应该来自 primary_analysis 自身，不是 final_decision 翻转 |
| `:278-367` preflight_influence 测试组 | 期待 applied_effects 含 lower_confidence / raise_risk | **改写**：断言 `applied_effects == []` 永远；把 matched_rule_count 测试保留 |

> Step 12 改写测试时必须保留**正向断言**（即 final_direction 来自 primary、
> final_confidence 来自 confidence 或 unknown），不要简单删除。

### 8.2 UI / 用户可见行为

- 旧行为：UI 看到的 `final_direction` 可能是 "中性"（即使 primary 是偏多）；
  `final_confidence` 是经过加减分的最终值。
- 新行为：`final_direction` 严格等于 `primary_analysis.direction`；
  `final_confidence` 在 11C 完成前**显示 unknown**。
- **可能的 UX 反差**：当 confidence_result 还没接入时，UI 上 `final_confidence`
  字段会大面积变 `unknown`。这是**契约要求的展示**，不是 bug。
- Step 12 实施时如果 UI 想显示更友好的占位（例如 "未接入"），应在 UI 层做
  i18n / fallback，不在 final_decision 内伪造。

### 8.3 narrative / summary 层

- `services/projection_narrative_renderer.py` / `predict_summary.py` /
  `projection_three_systems_renderer.py` 都消费 `final_direction` / `final_confidence`。
- 如果 narrative 文本里写"最终方向：X，置信度：Y，原因：preflight 降级"，
  Step 12 需同步移除"preflight 降级"句式（这是 RISK-2 修复，不是 RISK-9 改）。
- **不**改 `ai_summary.py`（保留给 11F / RISK-9）。

### 8.4 prediction_log

- `services/projection_record_store.py` / `prediction_store.py` /
  `services/contract_outcome_correlation.py` 等记录 `final_direction` /
  `final_confidence`。schema 不变；取值可能从 "中性" 改为 "偏多"（更接近真实推演）；
  从重算 confidence 改为 unknown（11C 前）。
- **不**回填 / 重写历史 prediction_log（Step 14 才考虑）。

### 8.5 与 11C 的依赖

> 关键问题：在 11C confidence_evaluator 还没实现时，`final_confidence` 显示
> `unknown` 是不是会影响 UI 太大？

回答：

- 不影响 schema；只影响取值。
- 短期 UX 反差是**契约设计的代价**，提醒所有人"目前没有合规的 confidence
  实现"。
- 如果实施 11B 时 UI 太难看，**不**回退；改 UI 层显式标注"confidence
  evaluator 待接入"。
- 11C 实施完毕后，`final_confidence` 自然恢复成有意义的 level。

### 8.6 不引入 deprecated 字段

- 不引入新的 deprecated display-only 字段。Step 12 修复后输出本就是干净的
  并列结构；旧的 `kind` / `final_direction` / `final_confidence` 字段名兼容
  保留（取值变了，名字不变）。

---

## 9. Contract enforcement tests 设计

> 本节**只描述测试设计**，Step 12 才新增 / 修改测试代码。

### 9.1 必须新增的测试

| 测试名（建议） | 验证内容 |
|---|---|
| `test_final_decision_does_not_override_direction` | 同一 primary_analysis 输入下，分别传不同 peer_adjustment（含 `downgrade + adjusted_direction = 中性`），断言 `result["final_direction"] == primary_analysis["direction"]` |
| `test_final_decision_does_not_recompute_confidence` | 提供不同 peer / historical / preflight 组合，断言 `result["final_confidence"]` 仅取决于 confidence_result（缺则 unknown），与 peer / historical / preflight 无关 |
| `test_preflight_is_display_only_warning` | 注入 matched_rules（含 severity high/medium/low），断言 `preflight_influence["applied_effects"] == []` 永远；matched_rule_count 仍正确；warnings 包含 "仅展示" 文案 |
| `test_final_decision_missing_confidence_result_returns_unknown` | 不传 confidence_result，断言 `final_confidence == "unknown"` 且 `agreement_status == "unknown"` 且 warnings 含相应提示 |
| `test_final_decision_with_confidence_result_uses_combined_level` | 传 `confidence_result.combined_confidence.level == "medium"`，断言 `final_confidence == "medium"`；不依赖任何加减分 |
| `test_final_decision_requires_source_attribution` | 断言 `result["source_attribution"]` 是 list，每项含 `section` / `field` / `source_field`；`combined_user_summary` 句子 ID 与 source_attribution 对应 |
| `test_final_decision_has_non_mutation_confirmations` | 断言 `result["non_mutation_confirmations"]` 含 6 个 false 字段：`projection_result_mutated` / `exclusion_result_mutated` / `confidence_result_mutated` / `final_direction_overridden` / `confidence_recomputed` / `preflight_applied_as_decision` |
| `test_final_decision_no_trading_or_hard_fields` | 断言 result 不含 `trading_action` / `buy` / `sell` / `hold` / `simulated_trade` / `no_trade` / `hard_exclusion` / `forced_exclusion` / `required_decision` / `production_promotion` / `_PROTECTION_LAYER_CONNECTED` / `final_report_mutation` 等任何禁止字段 |
| `test_final_decision_no_apply_preflight_influence_callsite` | 静态扫描 `services/final_decision.py`，断言函数体内**不调用** `_apply_preflight_influence(...)` |

### 9.2 改写的旧测试

| 旧测试 | 处理 |
|---|---|
| `tests/test_final_decision.py:272-273`（`final_direction == "中性"`） | 改为：当 input 模拟 "primary 是中性" 时断言 `final_direction == "中性"`；当 input 模拟 "primary 是偏多 + peer downgrade" 时断言 `final_direction == "偏多"`（保留 primary） |
| `:141-142, 160-161, 181-182, 208-209` `final_confidence == "medium"/"low"` | 改写：注入 `confidence_result.combined_confidence.level = ...`，断言 `final_confidence == 注入值`；不再依赖 peer / historical 加减分 |
| `:278-367` preflight_influence 测试组 | 改写为：断言 `applied_effects == []` + `matched_rule_count` 正确 + warnings 包含"仅展示"文案 |
| `:96-97, 121-122` `final_confidence == "high"` | 改为传 `confidence_result.combined_confidence.level == "high"`；断言 `final_confidence == "high"` |
| `:224-225` primary_missing → unknown | **保留** |
| `:306-315` preflight_influence 形状 | **保留**（key 仍存在），但断言 `applied_effects` 永远是 `[]` |

### 9.3 测试不允许的内容

- 测试**不**应再断言"final_decision 翻方向"
- 测试**不**应再依赖 `_apply_preflight_influence` 的副作用
- 测试**不**应允许 `final_confidence` 取值与 confidence_result 不一致

---

## 10. 不允许的修复方式

以下修复方式**不**符合 contract，Step 12 实施时**禁止**：

1. **不**允许把 direction flip 改名后继续做（例如 `display_direction`
   依然按 peer 翻 中性）
2. **不**允许把 confidence recompute 改名为 `display_confidence` /
   `aggregator_confidence` 继续重算
3. **不**允许在 `final_report` 里生成新 `final_direction`（必须严格透传 primary）
4. **不**允许把 preflight influence 融入 projection 或 confidence（即把
   "降级置信度"逻辑搬到 confidence_evaluator —— 那是 11C 的事，但 preflight
   只能作为 evidence，不能作为 forced 副作用）
5. **不**允许通过 LLM 生成无出处 summary（`combined_user_summary` 必须有
   `source_attribution` 对应）
6. **不**允许顺手改 RISK-1 projection/exclusion decoupling（保留给 11A → Step 12 各自 commit）
7. **不**允许顺手实现 confidence system（保留给 11C）
8. **不**允许顺手改 RISK-8 predict.py 拆分（保留给 11E）
9. **不**允许顺手改 RISK-9 ai_summary（保留给 11F）
10. **不**允许 cleanup 与 boundary fix 混 commit（包括删除 `_apply_preflight_influence`
    函数本体 —— 留 Step 14）
11. **不**允许 large rewrite：每个 fix commit 控制在最小行数
12. **不**允许进入 3R-5 / 3R-6
13. **不**允许复活 continuous_smoothing
14. **不**允许启用 promotion_execution_bridge
15. **不**允许在本 fix commit 里删掉 30+ 下游消费者依赖的 `final_direction` /
    `final_confidence` / `kind: "final_decision"` 字段

---

## 11. Step 12 实施顺序建议

> Step 12 才允许执行；本轮**不**实施。

### 推荐顺序（commit-per-fix 内部子步骤）

1. **新增 contract enforcement tests（failing）**
   - 加 §9.1 列出的 9 个新测试；验证它们当前 fail（红灯）
   - 此时旧测试 §9.2 仍 pass（断言旧行为）

2. **改写旧测试**（§9.2）
   - 把 `:141-142, 160-161, 181-182, 208-209` 改为依赖 `confidence_result` 注入
   - 把 `:272-273` direction-flip 测试改为正向断言
   - 把 `:278-367` preflight_influence 测试改为 `applied_effects == []`
   - 此时旧测试**红灯**（断言新行为，但实现还未改）

3. **修改 `services/final_decision.py`**
   - 加 `confidence_result: dict[str, Any] | None = None` /
     `exclusion_result: dict[str, Any] | None = None` 入参
   - 删除 `:280-286` direction 翻转分支
   - 删除 `:288-303` confidence 加减分分支
   - 删除 `:313-317` `_apply_preflight_influence(...)` 调用
   - 重写 final_direction / final_confidence 装配（§5.3）
   - preflight 转为 display-only（§5.4）
   - 加 source_attribution / non_mutation_confirmations（§5.5）
   - 保留所有兼容字段名

4. **修改 `services/projection_orchestrator_v2.py`**
   - 在调用 `build_final_decision(...)` 时显式传 `confidence_result=None`
     （11C 完成前）+ `exclusion_result=exclusion_result`（仅展示）

5. **跑 focused tests**
   - `pytest tests/test_final_decision.py`
   - `pytest tests/test_projection_orchestrator_v2.py
     tests/test_projection_entrypoint*.py`

6. **修一切因新边界产生的 narrative / summary / record store 测试**
   - `tests/test_projection_narrative_renderer.py` 如有"由于 preflight 所以"
     文本断言，删除该断言
   - `tests/test_projection_three_systems_renderer.py` 如断言 final_confidence
     的具体 level，改为允许 unknown

7. **跑全量 pytest**
   - `pytest tests/`
   - 跑 `scripts/check.sh`（如可运行）

8. **手动 spot-check UI**
   - 启动 Streamlit，验证 predict_tab / home_tab 仍能渲染
   - 验证 final_confidence 显示 unknown 时 UI 不崩

9. **独立 commit**
   - commit message：`fix(boundary): RISK-2 purify final decision aggregator`
   - 单 commit；不混合任何 cleanup

### 不允许 inside Step 12 commit 的内容

- **不**删 `_apply_preflight_influence` 函数本体（dead code，留 Step 14）
- **不**删 `_risk_level()` / `_why_not_more()` 等 helper（保留作为 display 计算）
- **不**删兼容字段名（`kind` / `final_direction` / `final_confidence`）
- **不**改 RISK-1 / RISK-3 / RISK-8 / RISK-9 / RISK-10 任何路径
- **不**改 v1 predict.py（属 RISK-8）

---

## 12. 与 11C 的关系

> **关键边界**：11B 不实现完整 confidence system。

- 11B 的输出 `final_confidence` 在 11C 完成前**填 unknown**。
- 11B **不**新建 `services/confidence_evaluator.py` 或类似模块（那是 11C）。
- 11B **不**重新计算 confidence；如果发现"显示 unknown 太丑"，**不回退**到
  旧重算逻辑；改 UI 层显式标注"confidence evaluator 待接入"。
- 11B 的 contract test 中允许 `final_confidence == "unknown"` 作为合法状态。
- 11C 实施完毕后，`final_confidence` 自动从 confidence_result.combined_confidence
  取值，不需要再改 11B 的代码。

> **绝对禁止**：在 11B 中"暂时实现一个 confidence engine 占位"。这违反
> Step 11 的设计原则（每个 RISK 独立修复；不在一个 fix commit 中跨界）。

---

## 13. 回滚策略

### 13.1 失败模式

如果在 Step 12 实施过程中：

- UI **大面积**显示 `final_confidence == unknown` 导致用户体验崩
- narrative / summary 文本测试**大面积失败**
- 30+ 下游消费者中有读 `final_direction == "中性"` 的硬编码断言
- prediction_log 测试期待重算后的 final_confidence

### 13.2 回滚原则

> **不**回退 final_decision 旧的 override / recompute 逻辑。

正确的回滚序列：

1. 回到 boundary fix 之前的 commit（`git revert <fix-commit>`）
2. 重新做最小修复：保持 final_direction == primary_direction、
   final_confidence == unknown
3. 把展示层调整为显式标注"confidence evaluator 待接入"
4. 必要时保留 deprecated display-only 字段（例如 `aggregator_display_confidence`），
   但**必须**显式标注：
   - 字段名前缀含 `display_*` 或 `aggregator_display_*`
   - 字段 docstring 写明"非 confidence_system 输出"
   - schema_version 不变
5. 任何回滚动作**仍不**允许 `_apply_preflight_influence` 副作用重新生效
6. 任何回滚动作**仍不**允许 direction 翻转分支重新生效

### 13.3 不允许的"回滚捷径"

- **不**允许悄悄恢复 direction 翻转
- **不**允许把"加减分 confidence"改名为 `display_confidence_score` 继续算
- **不**允许跳过 11B 设计直接回到旧 final_decision 实现
- **不**允许在 fix commit 上做 `git commit --amend` 隐藏违规；必须显式 revert

---

## 14. 严守边界

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
- 未实际修复 RISK-2（保留给 Step 12）
- 未触碰 RISK-1 / RISK-3 / RISK-7 / RISK-8 / RISK-9 / RISK-10
  （各自 11A / 11C / 11D / 11E / 11F / 11G 设计）

本设计的修改路径：任何对 §4 修复目标、§5 最小代码修改、§9 测试设计、
§11 Step 12 实施顺序、§12 与 11C 的关系的调整，都必须以**显式更新本文件**
的方式提出。
