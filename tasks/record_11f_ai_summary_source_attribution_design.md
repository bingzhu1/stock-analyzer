# 11F记录：AI Summary Source Attribution / Opt-in Gate Design

> 本设计针对 Step 09 / Step 10 中标记为 **HIGH_RISK** 的 RISK-9。
>
> 本轮**只写设计**：未改代码、未新增测试、未删文件、未移动文件、未写 DB、
> 未跑 validation、未 commit / push、未进入 Step 12、未进入 3R-5 / 3R-6、
> 未新增 candidate、未复活 continuous_smoothing、未实际修改 ai_summary.py、
> 未顺手碰 RISK-1 / RISK-2 / RISK-3 / RISK-7 / RISK-8 / RISK-10。

---

## 1. 设计目的

把 `services/ai_summary.py` 限制为**source-attributed optional explanation
layer**，而**不是**自由生成判断的 final report。

修复后的目标：

- AI summary **默认关闭**，必须显式 `enable_ai_summary=True` 才执行
- AI summary **只能改写**已有 source facts；**不得**新增判断 / 推理 / 重算 /
  交易建议
- 每一句 AI 输出**必须**绑定来源（source_system + source_field + source_value
  + transformation kind）
- 输出**必须**包含 `non_judgment_confirmation` 自检字段
- LLM 输出**必须** post-check 禁止词 / 禁止结构
- 任一步缺失 → 返回 `status="refused_*"` / `"disabled"` / `"unavailable"`，
  **不**自由生成

本设计**只**产出设计文档，Step 12 才实施 + commit。

---

## 2. 当前问题

### 2.1 `services/ai_summary.py` 现状（157 行）

| 公共函数 | LLM 调用 | 当前约束 |
|---|---|---|
| `build_projection_ai_summary(payload, *, text_generator=generate_text)` | ✅ generate_text | 仅"自然语言指令"`_PROJECTION_INSTRUCTIONS`（line 11-18）告诉 LLM "不要新增事实，不得改写规则层主结论"；**无程序级强制** |
| `build_review_ai_summary(...)` | ✅ | 同上 |
| `build_projection_ai_explanation(...)` | ✅ | 同上 |
| `build_compare_ai_explanation(...)` | ✅ | 同上 |
| `build_risk_ai_explanation(...)` | ✅ | 同上 |

每个函数：

- 直接 `from services.openai_client import generate_text`（line 8）
- 用 `_json_payload(payload)` 把整个 payload 序列化为 JSON 喂给 LLM
- 返回**纯文本字符串**（不是结构化 dict）
- **没有** opt-in gate（被调用即触发 LLM）
- **没有** source attribution（LLM 自由生成；无字段绑定）
- **没有** post-check 禁止词
- **没有** non_judgment_confirmation
- 全靠"prompt 文字劝阻"LLM 不要越界

### 2.2 LLM transport：`services/openai_client.py`（95 行）

- `generate_text(*, input_text, instructions, model=None, timeout=45)` — 直连
  OpenAI Responses API
- 需 `OPENAI_API_KEY` 环境变量；缺则 raise `OpenAIConfigurationError`
- `DEFAULT_MODEL = "gpt-5.4-mini"`
- **存在隐式 gate**：缺 API key 时不会调；但这是 deployment-level，不是
  contract-level opt-in

### 2.3 active callers（必须保留契约）

`grep` 显示调 ai_summary 公共函数的非测试 importer：

- `ui/command_bar.py`（UI 命令栏）
- `ui/predict_tab.py`（UI 预测 tab）
- `services/tool_router.py`（LLM tool router）

> Step 12 修复必须**保留** 5 个公共函数名 + 调用签名的兼容；这 3 个 caller
> 的调用契约不破。

### 2.4 风险落地

LLM 在没有程序级约束的情况下，可能：

- **补判断**：在三系统都没给出明确方向时，LLM 会"贴心地"补一句结论
- **解释成结论**：把"推演与否定冲突"改写为"应该谨慎，建议持有"
- **生成交易建议**：买入 / 卖出 / 持有
- **重算 confidence**：把"medium 置信"改写为"high"或"low"
- **修改最可能 / 最不可能**：把"小涨最可能"改成"震荡最可能"
- **使用未在 payload 中的事实**：LLM 训练数据里的"行业知识"
- **变成第四个判断系统**：违反 06 §6 / 07D §5 / §10

---

## 3. 违反的 contract

| contract | 章节 | 违规点 |
|---|---|---|
| 06 三系统独立原则 | §6 三系统正确关系 / §7 第 6 条 | 最终报告**不改变**任一系统输出；ai_summary LLM 自由文本可能新增判断 |
| 07D final report contract | §2 展示者非决策者 / §5 禁止 `final_report_mutation` / `production_promotion` / `_PROTECTION_LAYER_CONNECTED` / 任何 trading / hard / forced / required / §10 combined_user_summary "句句必有出处" / §11 禁止 `final_report → trading_action` / `final_report → hard / forced decision` | LLM 无 source 绑定；可能输出交易语 / hard 语 |
| 09 RISK-9 升级 | HIGH_RISK | LLM-driven free text，无 source attribution / opt-in gate |
| 10 §6 FIX_REQUIRED RISK-9 | "加 source attribution + opt-in gate" | 11F 范畴 |

---

## 4. 修复目标

修复后必须满足：

1. **Opt-in gate**：默认 `enable_ai_summary=False`；不开启则**不调 LLM**，返回
   `{status: "disabled"}` 占位
2. **Source attribution**：每一句 AI 输出必须有 `source_system` /
   `source_field` / `source_value` / `transformation` 四元组
3. **Allowed transformation 仅 4 类**：`paraphrase` / `compression` /
   `translation` / `formatting`
4. **Forbidden transformation**（程序级 + prompt 双重）：`inference` /
   `recommendation` / `prediction` / `trading_advice` /
   `confidence_recalculation` / `conflict_reclassification` / `direction_change`
5. **Allowed source 仅 4 类**：`projection_result` / `exclusion_result` /
   `confidence_result` / `final_report`（即 source_attributed 字段）
6. **Forbidden input**：raw market data（OHLCV）/ future outcome /
   未在三系统输出中显式出现的字段
7. **Post-check 禁止词 / 禁止结构**（违反 → `status="refused_policy_violation"`）：
   - `buy / sell / hold / 买入 / 卖出 / 持有 / 加仓 / 减仓 / 清仓 / 满仓 / 空仓`
   - `hard / forced / required / 强制 / 必须 / 务必 / 一定 / 应当 / 建议交易`
   - `production ready / 生产可用`
   - `final decision changed / 最终改判 / 推翻原判 / 修正方向`
   - 新的 `most_likely_state` / `most_unlikely_state`（与 source 不一致）
   - `推荐 / 建议买入 / 建议卖出 / 建议持有 / 适合操作`
8. **`non_judgment_confirmation`**：5 个 `introduced_*` 字段恒为 `false`；任一
   `true` 即 reject
9. **缺 source attribution → status="refused_missing_sources"** + summary=""
10. **OPENAI_API_KEY 缺失 → status="llm_unavailable"** + summary=""（环境层
    fallback）
11. ai_summary 输出**不**回写 projection / exclusion / confidence / final_report
    任一字段
12. ai_summary 输出**不**作为 final_report 本身；final_report 可以**展示** AI
    summary，但**不**用 AI summary 改写

---

## 5. Opt-in gate 设计

### 5.1 函数签名（修复后）

```python
def build_projection_ai_summary(
    payload: dict[str, Any],
    *,
    enable_ai_summary: bool = False,
    require_source_attribution: bool = True,
    allow_new_judgment: bool = False,
    allowed_source_systems: tuple[str, ...] = (
        "projection_result",
        "exclusion_result",
        "confidence_result",
        "final_report",
    ),
    text_generator: Callable[..., str] = generate_text,
) -> dict[str, Any]:
    """Return a structured AI summary result.

    Read-only contract:
      - never mutates payload
      - never calls LLM unless enable_ai_summary=True
      - never produces text without per-sentence source attribution
      - never allows new judgments (allow_new_judgment must remain False)
      - returns a fresh dict; status field captures gate decisions
    """
```

> 对 5 个公共函数（projection_summary / review_summary / projection_explanation
> / compare_explanation / risk_explanation）应**全部**改为相同 gate / 返回
> 结构化 dict（与 §8 schema 对齐）。

### 5.2 Gate 决策表

| 入参组合 | 行为 |
|---|---|
| `enable_ai_summary=False` | **不**调 LLM；返回 `{status: "disabled", summary: "", ...}` |
| `enable_ai_summary=True` + `allow_new_judgment=True` | **拒绝**：`status="refused_policy_violation"`，理由 "allow_new_judgment must be False under 07D" |
| `enable_ai_summary=True` + `require_source_attribution=False` | **拒绝**：`status="refused_policy_violation"`，理由 "require_source_attribution must be True under 07D §10" |
| `enable_ai_summary=True` + payload 无可绑定 source | **拒绝**：`status="refused_missing_sources"` |
| `enable_ai_summary=True` + 正常 source 全在 | 调 LLM → post-check → 返回 |
| OPENAI_API_KEY 缺失（OpenAIConfigurationError） | `status="llm_unavailable"` + summary="" + warnings 加 |
| OpenAI API 错误（OpenAIClientError） | `status="llm_error"` + summary="" + warnings 加 |
| LLM 输出含禁止词 | `status="refused_policy_violation"` + summary="" + warnings 加触发词 |
| LLM 输出某句无 source attribution | `status="refused_missing_sources"` + summary="" |

### 5.3 Default 关闭原则

- 5 个 builder 默认 `enable_ai_summary=False`
- caller 必须**显式**传 `enable_ai_summary=True`
- caller 也可通过 env var `ENABLE_AI_SUMMARY=1` 开启（兼容 ops 层 toggle）；
  但函数级显式入参优先

### 5.4 不允许的 gate 变形

- ❌ `enable_ai_summary=True` 设为默认值
- ❌ 通过 import 时副作用启用
- ❌ "如果 caller 显示已经启用其他 LLM，就默认开启 ai_summary"
- ❌ `allow_new_judgment=True` 任何场景
- ❌ `require_source_attribution=False` 任何场景

---

## 6. Source attribution 设计

### 6.1 句子级绑定

每一句 AI 输出必须绑定为 5 字段：

```python
{
    "sentence": "...",                       # AI 输出的中文句子
    "source_system": "projection|exclusion|confidence|final_report",
    "source_field": "...",                   # e.g. "most_likely_state"
    "source_value": "...",                   # e.g. "小涨"
    "transformation": "paraphrase|compression|translation|formatting",
}
```

### 6.2 Allowed transformation（4 类）

| transformation | 含义 | 示例 |
|---|---|---|
| `paraphrase` | 同语义改写 | "most_likely_state=小涨" → "明日最可能小幅上涨" |
| `compression` | 多字段合并为一句 | most_likely + ranked → "明日最可能小涨，其次震荡" |
| `translation` | 标签 → 自然语言 | level=medium → "中等可信" |
| `formatting` | 结构化 → 句子 | list → 逗号分隔 |

### 6.3 Forbidden transformation（程序 + prompt 双重）

| transformation | 含义 | 例子（禁止） |
|---|---|---|
| `inference` | 从 source facts 推导新结论 | "推演说小涨 → AI 推："因此明日不会大跌" |
| `recommendation` | 建议交易行动 | "应该持有 / 可适当加仓" |
| `prediction` | 新预测 | "下周可能反转" |
| `trading_advice` | 交易动作 | "买入 / 卖出 / 持有" |
| `confidence_recalculation` | 重算可信度 | "综合 medium 应该改为 low" |
| `conflict_reclassification` | 改 agreement_status | "看似冲突其实一致" |
| `direction_change` | 改方向 | "推演偏多但实际更接近中性" |

### 6.4 Source attribution 验证规则

- 每句必须有 4 字段全部非空
- `source_system` ∈ §4.5 白名单
- `source_field` 必须是 `source_system` 真实存在的字段（程序级校验）
- `source_value` 必须**等于**或**严格派生自** `payload[source_system][source_field]`
- `transformation` ∈ §6.2 4 类白名单
- 任一 fail → `status="refused_missing_sources"`

### 6.5 LLM 如何输出 attribution？

设计选择：

**Option A（推荐）**：LLM 输出**结构化 JSON**，每句含 attribution：

```jsonc
{
  "sentences": [
    {
      "sentence": "明日最可能小幅上涨",
      "source_system": "projection_result",
      "source_field": "most_likely_state",
      "source_value": "小涨",
      "transformation": "paraphrase"
    }
  ]
}
```

prompt 显式要求 LLM 按此 JSON schema 输出。post-check 验证每条 attribution。

**Option B（备用）**：LLM 输出纯文本 + ai_summary.py **后置** rule-based
attribution（每句逐一在 source payload 中查匹配字段）。

> Step 12 推荐 **Option A**：可强制 LLM 自报来源；不依赖后置 NLP。
> 如 LLM 不能稳定输出 JSON（旧模型），fallback 到 Option B。

---

## 7. Prompt constraint 设计

修复后的 prompt 必须**程序拼接**包含以下硬约束：

```
你是股票研究系统的中文总结助手。

【硬规则 - 不可违反】
1. 你只能基于下面的 ALLOWED_SOURCES 字段改写文本。
2. 不得添加任何 ALLOWED_SOURCES 中不存在的事实。
3. 不得输出交易建议。禁止使用：买入 / 卖出 / 持有 / 加仓 / 减仓 / 清仓。
4. 不得说"应该"、"必须"、"务必"、"一定"、"建议"、"推荐"。
5. 不得修改 most_likely / most_unlikely / confidence level / direction。
6. 不得重新分类冲突。如果 source 说 strong_conflict，你不能写"基本一致"。
7. 不得自己重算 confidence。
8. 不得说"hard / forced / required / 强制 / 生产可用"。
9. 不得引用 ALLOWED_SOURCES 之外的"行业知识"或"历史经验"。
10. 如果 ALLOWED_SOURCES 信息不足以支持某句话，请明确写"信息不足"。

【输出格式 - 严格 JSON】
{
  "sentences": [
    {
      "sentence": "<中文句子>",
      "source_system": "<projection_result|exclusion_result|confidence_result|final_report>",
      "source_field": "<source 中的字段名>",
      "source_value": "<source 中的字段值，原样或同语义>",
      "transformation": "<paraphrase|compression|translation|formatting>"
    }
  ]
}

【ALLOWED_SOURCES】
{json_payload_filtered_to_allowed_systems}

【任务】
基于上面 ALLOWED_SOURCES，按【输出格式】生成中文总结。
不要在 JSON 之外输出任何文字。
```

### 7.1 Prompt 装配规则

- ai_summary.py **不**直接 dump 全部 payload；只 dump
  `payload[allowed_source_systems]` 子集
- prompt 模板**程序生成**，避免 caller 自定义 prompt 绕过约束
- payload 中如含 `raw_evidence_refs` / `raw_market_data` / `historical_outcome`
  等敏感字段，**必须**先剥离再喂给 LLM
- 每个 builder（projection / review / explanation / compare / risk）有自己的
  allowed_sources 子集

### 7.2 不同 builder 的 allowed_sources

| builder | allowed_source_systems |
|---|---|
| `build_projection_ai_summary` | `projection_result` + `final_report` |
| `build_review_ai_summary` | `final_report` + `outcome_record`（已结案 review；前提是上游显式标 offline，或仅历史 review 用） |
| `build_projection_ai_explanation` | `projection_result` |
| `build_compare_ai_explanation` | `compare_result`（统计对比，不是预测） |
| `build_risk_ai_explanation` | `final_report.risk_disclosure` + `confidence_result.reliability_warnings` |

---

## 8. Output schema 设计

修复后 5 个 builder 全部返回**结构化 dict**（不再是纯文本）：

```jsonc
{
  "schema_version": "ai_summary_result.v1",
  "system_name": "ai_summary",
  "builder_name": "projection_summary | review_summary | projection_explanation | compare_explanation | risk_explanation",

  "status": "disabled" | "ok" | "refused_missing_sources" | "refused_policy_violation" | "llm_unavailable" | "llm_error",

  "summary": "...",   // 拼接所有 sentence 的纯文本；status != "ok" 时为空字符串

  "sentences": [
    {
      "sentence": "明日最可能小幅上涨",
      "source_system": "projection_result",
      "source_field": "most_likely_state",
      "source_value": "小涨",
      "transformation": "paraphrase"
    },
    ...
  ],

  "source_attribution": [
    // 与 sentences 一一对应；冗余但便于审计
    {"sentence_index": 0, "source_system": "projection_result", "source_field": "most_likely_state"}
  ],

  "non_judgment_confirmation": {
    "introduced_new_prediction": false,
    "introduced_new_exclusion": false,
    "introduced_new_confidence": false,
    "introduced_trading_action": false,
    "introduced_hard_or_forced": false
  },

  "policy_violations": [
    // post-check 命中的禁止词列表（status="refused_policy_violation" 时填）
    "matched_term:买入"
  ],

  "warnings": [
    // 各种降级 / 调用层信息（缺 LLM key、超时等）
    "OPENAI_API_KEY 未配置；ai_summary 暂时返回 disabled。"
  ],

  "schema_version_input": "<source schema_version>",
  "request_metadata": {
    "enable_ai_summary": true,
    "require_source_attribution": true,
    "allow_new_judgment": false,
    "allowed_source_systems": ["projection_result", "final_report"]
  }
}
```

### 8.1 schema 兼容性

- 5 个 builder 输出 schema 一致（仅 `builder_name` 不同）
- 旧 caller（ui/command_bar / ui/predict_tab / tool_router）期待**字符串**返回；
  Step 12 必须在 caller 适配前**保留旧字符串行为**或在 caller 层做 dict→str
  适配（详见 §10.2）

### 8.2 禁止字段

```jsonc
// ❌ 不允许出现
{
  "trading_action": "...",
  "buy": ..., "sell": ..., "hold": ...,
  "simulated_trade": {...},
  "no_trade": true,
  "hard_exclusion": true,
  "forced_exclusion": true,
  "required_decision": true,
  "production_promotion": true,
  "_PROTECTION_LAYER_CONNECTED": true,
  "final_report_mutation": {...},
  "modified_projection": {...},
  "modified_exclusion": {...},
  "modified_confidence": {...},
  "overridden_*": ...,
  "corrected_*": ...
}
```

---

## 9. Forbidden output / post-check 设计

### 9.1 禁止词列表（程序级 substring match）

```python
_FORBIDDEN_TERMS_TRADING = (
    # 中文
    "买入", "卖出", "持有", "加仓", "减仓", "清仓", "满仓", "空仓",
    "做多", "做空", "建仓", "平仓",
    # 英文
    "buy", "sell", "hold", "BUY", "SELL", "HOLD",
    "long position", "short position",
)

_FORBIDDEN_TERMS_HARD = (
    "强制", "必须", "务必", "一定", "应当",
    "hard", "forced", "required",
    "建议交易", "推荐交易",
    "production ready", "生产可用",
)

_FORBIDDEN_TERMS_OVERRIDE = (
    "最终改判", "推翻原判", "修正方向", "重新预测",
    "应该", "适合操作", "建议买入", "建议卖出", "建议持有",
    "推荐买入", "推荐卖出", "推荐持有",
)
```

> 注：substring 匹配会有误伤（例如"建仓"包含"建"+"仓"，"应该"是常用词）。
> 修复时建议用**字段边界 + 正则**减少误伤；本设计仅给出禁止词方向，
> Step 12 实施时按需细化。

### 9.2 Post-check 流程

```python
def _post_check(llm_output: dict, allowed_payload: dict) -> tuple[str, list[str]]:
    """Return (status, violations).

    status ∈ {"ok", "refused_missing_sources", "refused_policy_violation"}
    """
    violations = []

    # 1. 解析 LLM JSON
    try:
        sentences = llm_output["sentences"]
    except (KeyError, TypeError):
        return "refused_missing_sources", ["llm_output not in expected json schema"]

    # 2. 句子级 attribution 验证
    for i, sent in enumerate(sentences):
        for required in ("sentence", "source_system", "source_field", "source_value", "transformation"):
            if not sent.get(required):
                violations.append(f"sentence[{i}] missing field: {required}")
        # source_system 白名单
        if sent.get("source_system") not in _ALLOWED_SOURCE_SYSTEMS:
            violations.append(f"sentence[{i}] source_system not allowed: {sent.get('source_system')}")
        # transformation 白名单
        if sent.get("transformation") not in _ALLOWED_TRANSFORMATIONS:
            violations.append(f"sentence[{i}] transformation not allowed: {sent.get('transformation')}")
        # source_value 真值校验
        actual_value = _get_nested(allowed_payload, sent["source_system"], sent["source_field"])
        if not _values_match(actual_value, sent["source_value"]):
            violations.append(f"sentence[{i}] source_value mismatch: claimed={sent['source_value']!r} actual={actual_value!r}")

    if violations:
        return "refused_missing_sources", violations

    # 3. 禁止词扫描
    full_text = " ".join(s["sentence"] for s in sentences)
    for term in (*_FORBIDDEN_TERMS_TRADING, *_FORBIDDEN_TERMS_HARD, *_FORBIDDEN_TERMS_OVERRIDE):
        if term.lower() in full_text.lower():
            violations.append(f"matched_term:{term}")

    if violations:
        return "refused_policy_violation", violations

    # 4. non_judgment 自检
    if _looks_like_new_prediction(full_text, allowed_payload):
        return "refused_policy_violation", ["heuristic_new_prediction_detected"]

    return "ok", []
```

### 9.3 命中 → 降级行为

- `status` 设为 `"refused_*"`
- `summary = ""`（空字符串；不返回部分 LLM 输出）
- `warnings` 列出违反原因
- `policy_violations` 列出禁止词命中
- `non_judgment_confirmation.*` 全 false（即使 LLM 想引入新判断，也被拒绝了）

---

## 10. 与 final_report 的关系

### 10.1 边界

- **`ai_summary` 不是 `final_report`**
  - `final_report` 是 07D aggregator 的契约 schema（11B 范畴）
  - `ai_summary` 是 optional explanation layer，**位于** final_report 之外
- **`final_report` 不依赖 `ai_summary`**
  - `final_report.combined_user_summary` 由 11B 填充（来自三系统输出 + 排版规则）
  - `final_report` 完整可用**不需要** AI summary
- **`final_report` 可以**展示 `ai_summary.summary`（如 caller 决定开启）：
  - 但必须**单独字段**（`final_report.optional_ai_summary` 之类）
  - **不**回写到 `combined_user_summary`
  - **不**回写到三系统任一字段
- **`ai_summary` 不能**作为 active judgment source：
  - 不能驱动 trading
  - 不能驱动 hard / forced / required
  - 不能进入 prediction_log 的 active 字段

### 10.2 Caller 适配（ui/command_bar / ui/predict_tab / tool_router）

修复后 5 个 builder 返回 dict（§8 schema），但 3 个 caller 当前期待**字符串**。

设计选择：

**Option A（推荐）**：在 ai_summary.py 内**保留**字符串签名 `*_text` 函数：

```python
def build_projection_ai_summary_text(
    payload, *, enable_ai_summary=False, ...
) -> str:
    """Backward-compat wrapper that returns ai_summary_result.summary."""
    result = build_projection_ai_summary(payload, enable_ai_summary=enable_ai_summary, ...)
    return result["summary"]  # "" if disabled / refused
```

旧 caller 调 `*_text` 版本（短期兼容），新 caller 调 dict 版本。

**Option B**：让 caller 处理 dict 返回。caller 需要修改。

> Step 12 推荐 **Option A**：先加 dict API + 兼容 `*_text` wrapper；caller 后续
> 迁移到 dict。本次 fix commit 内不强制 caller 迁移。

---

## 11. 与 openai_client 的关系

### 11.1 openai_client.py 不动

- `services/openai_client.py:44` `generate_text(*, input_text, instructions, model, timeout)`
  保持原签名
- 不在 openai_client 内做 source attribution（那是 ai_summary 层的职责）
- openai_client 仍可被其他模块（`services/ai_intent_parser.py` /
  `services/ai_task_parser.py` / `services/tool_router.py` /
  `ui/command_bar.py`）调用 —— 这些是 LLM intent / planner，**不是** ai_summary
- 这些其他 LLM caller 是否也需要类似 gate / post-check？**留给 Step 11 后续
  专门审查**（不在 11F 范围）

### 11.2 ai_summary 调 openai_client 的额外约束

修复后 ai_summary.py 调 generate_text 必须：

1. **调用前**：opt-in gate + source 子集过滤
2. **调用时**：用程序拼装的 prompt（含硬约束 + JSON 输出格式）
3. **调用后**：post-check（attribution + 禁止词 + non_judgment）
4. **任何步骤失败**：返回 status="refused_*" / "llm_*"，**不**让 LLM 输出
   直接进 final_report / projection / exclusion / confidence

### 11.3 不允许的迂回

- ❌ 在 caller（ui/command_bar 等）层直接调 `generate_text(...)` 绕过 ai_summary
  的 gate（**注意**：grep 显示 `ui/command_bar.py` / `ui/predict_tab.py` 自己
  也 import `openai_client` —— 这是 RISK-9 的隐患，但**不在** 11F 范围；留给
  Step 11 后续 LLM caller 普查）
- ❌ 让 openai_client 输出直接进 final_report
- ❌ 在 ai_summary 内绕过 post-check（如增加 `bypass_postcheck=True` 入参）
- ❌ 让 LLM 输出回写 projection / exclusion / confidence / final_report

---

## 12. 最小代码修改设计

> 本节**只描述设计**，Step 12 才实施。

### 12.1 改动范围（仅 ai_summary.py + 测试）

| 文件 | 动作 |
|---|---|
| `services/ai_summary.py` | 重写 5 个 public function；加 gate / source attribution / post-check / structured dict 返回；保留 `*_text` 兼容 wrapper |
| `tests/test_ai_summary.py`（如已存在）/ 新增 contract test 文件 | 加 §13 列出的 10+ 测试 |
| `services/openai_client.py` | **不动** |
| `ui/command_bar.py` / `ui/predict_tab.py` / `services/tool_router.py` | **不动**（通过 `*_text` wrapper 兼容） |
| 其他 LLM caller (`ai_intent_parser` / `ai_task_parser`) | **不动**（保留给 Step 11 后续 LLM caller 普查） |
| `services/final_decision.py` / `confidence_evaluator.py` / `predict.py` | **不动** |

### 12.2 改造步骤

1. 加常量：`_ALLOWED_SOURCE_SYSTEMS` / `_ALLOWED_TRANSFORMATIONS` /
   `_FORBIDDEN_TERMS_TRADING` / `_FORBIDDEN_TERMS_HARD` / `_FORBIDDEN_TERMS_OVERRIDE`
2. 加 helpers：`_filter_payload_by_allowed_sources()` /
   `_build_constrained_prompt()` / `_post_check()` / `_get_nested()` /
   `_values_match()` / `_make_disabled_result()` /
   `_make_refused_result(status, violations)`
3. 重写 5 个 public builder（保持函数名 / 参数兼容）
4. 加 `*_text` 兼容 wrapper（返回 `result["summary"]`）
5. 不删除任何旧函数名（避免破坏 3 个 caller）

### 12.3 估计行数

- 现 157 行 → 修复后 ~350 行（增加 helpers + 5 个 builder 重写 + 兼容 wrapper）
- Step 12 single fix commit 控制在 +200 行内（合理范围）

---

## 13. Contract enforcement tests 设计

### 13.1 必须新增的测试

| 测试名（建议） | 验证内容 |
|---|---|
| `test_ai_summary_disabled_by_default` | 不传 `enable_ai_summary` 调 5 个 builder，断言 `result["status"] == "disabled"` 且**未调** `generate_text`（mock 验证） |
| `test_ai_summary_refuses_when_allow_new_judgment_true` | `enable_ai_summary=True` + `allow_new_judgment=True`，断言 `status == "refused_policy_violation"` |
| `test_ai_summary_refuses_when_require_source_attribution_false` | `require_source_attribution=False`，断言 `status == "refused_policy_violation"` |
| `test_ai_summary_refuses_missing_sources` | mock LLM 返回 sentences 缺 source_system 字段，断言 `status == "refused_missing_sources"` |
| `test_ai_summary_requires_source_attribution_per_sentence` | mock LLM 返回每句都有 attribution，验证 4 字段全部存在；source_system 在白名单 |
| `test_ai_summary_prompt_forbids_new_judgment` | 静态扫描 prompt 模板含 "不得添加 / 不得修改 / 不得重算 / 不得说" 关键约束 |
| `test_ai_summary_postcheck_blocks_trading_language` | mock LLM 返回 `"建议买入"`，断言 `status == "refused_policy_violation"` 且 `policy_violations` 含 `matched_term:买入` |
| `test_ai_summary_postcheck_blocks_hard_forced_language` | mock LLM 返回 `"强制持有"` 或 `"必须卖出"`，断言 refused_policy_violation |
| `test_ai_summary_postcheck_blocks_direction_change` | mock LLM 返回 `"最终改判为偏空"`，断言 refused |
| `test_ai_summary_postcheck_blocks_recommendation` | mock LLM 返回 `"推荐买入"`，断言 refused |
| `test_ai_summary_no_mutation_confirmations` | 断言 result 含 `non_judgment_confirmation`，5 个字段全为 false |
| `test_ai_summary_does_not_call_llm_when_disabled` | mock `generate_text`，断言 `enable_ai_summary=False` 时未被调用 |
| `test_ai_summary_uses_only_allowed_source_fields` | 注入 payload 含 raw_market_data，断言 prompt 中**不**包含 raw_market_data 字段（仅含 allowed_source_systems 子集） |
| `test_ai_summary_llm_output_without_sources_refused` | mock LLM 返回纯文本（非 JSON），断言 `status == "refused_missing_sources"` |
| `test_ai_summary_source_value_must_match_payload` | mock LLM 返回 source_value="高"，但 payload 中 `confidence_result.combined_confidence.level == "medium"`，断言 refused_missing_sources（值不匹配） |
| `test_ai_summary_text_wrapper_returns_string` | 调 `*_text` 兼容 wrapper，断言返回 str 类型；disabled / refused 时返回 `""` |
| `test_ai_summary_does_not_import_openai_client_outside_call_path` | 静态扫描 ai_summary.py：`from services.openai_client import generate_text` 仅 1 处 import；不通过其他迂回 |
| `test_ai_summary_does_not_export_to_final_report_or_three_systems` | 静态扫描 ai_summary.py：函数体内**不**写 `final_report[...] = ...` / `projection_result[...] = ...` / `exclusion_result[...] = ...` / `confidence_result[...] = ...` |
| `test_ai_summary_no_forbidden_fields_in_output` | 断言 result 不含 `trading_action` / `buy/sell/hold` / `simulated_trade` / `hard_exclusion` / `forced_exclusion` / `required_decision` / `production_promotion` / `_PROTECTION_LAYER_CONNECTED` / `final_report_mutation` / `modified_*` |
| `test_ai_summary_refuses_when_openai_api_key_missing` | mock `generate_text` raise `OpenAIConfigurationError`，断言 `status == "llm_unavailable"` 且 summary="" |
| `test_ai_summary_refuses_when_llm_error` | mock `generate_text` raise `OpenAIClientError`，断言 `status == "llm_error"` 且 summary="" |

### 13.2 测试不允许的内容

- 测试**不**应允许 `enable_ai_summary=True` 默认值
- 测试**不**应允许 LLM 输出含禁止词时 `status == "ok"`
- 测试**不**应允许 sentences 缺 attribution 时 `status == "ok"`
- 测试**不**应允许 source_value 与 payload 不一致时 `status == "ok"`

---

## 14. 不允许的修复方式

以下修复方式**不**符合 contract，Step 12 实施时**禁止**：

1. **不**允许直接删除 `services/ai_summary.py`（3 个 caller 仍依赖）
2. **不**允许默认开启 AI summary（`enable_ai_summary=False` 必须是默认值）
3. **不**允许无 source attribution 生成文本（`require_source_attribution=True`
   必须强制）
4. **不**允许把 LLM summary 当 final_report（07D §11 已禁止）
5. **不**允许 LLM 重新分析 raw market data（payload 必须先剥离 raw 字段）
6. **不**允许 LLM 生成交易建议（post-check 强制）
7. **不**允许 LLM 改写三系统输出（attribution + non_judgment 强制）
8. **不**允许在 11F 内**顺手修** RISK-1 / RISK-2 / RISK-3 / RISK-7 / RISK-8 /
   RISK-10
9. **不**允许 cleanup 与 fix 混 commit（包括删除旧 prompt 常量）
10. **不**允许进入 3R-5 / 3R-6
11. **不**允许复活 continuous_smoothing
12. **不**允许通过新增 `bypass_postcheck=True` / `unsafe_mode=True` 等"逃生口"
    入参绕过 post-check
13. **不**允许在 caller 层直接调 `generate_text(...)` 来"省事"地绕过 ai_summary
    gate（但本次 fix 不修复 caller 层；属 RISK-9 follow-up 范畴）
14. **不**允许把 `_FORBIDDEN_TERMS_*` 列表设为 caller 可注入（由 ai_summary 模块固定）
15. **不**允许 LLM 输出**部分**（partial / streaming）经 post-check 漏过；
    必须 LLM 完整输出后才 post-check

---

## 15. Step 12 实施顺序建议

> Step 12 才允许执行；本轮**不**实施。

### 15.1 推荐顺序（commit-per-fix 内部子步骤）

1. **新增 contract enforcement tests（failing baseline）**
   - 加 §13.1 列出的 20+ 测试到 `tests/test_ai_summary_boundary.py`（新文件）
   - 旧 `tests/test_ai_summary.py`（如有）保留
   - 期待新测试**全部 fail**（红灯 baseline）

2. **改写 `services/ai_summary.py`**
   - 加常量（_ALLOWED_SOURCE_SYSTEMS / _ALLOWED_TRANSFORMATIONS /
     _FORBIDDEN_TERMS_*）
   - 加 helpers（_filter_payload / _build_constrained_prompt / _post_check / ...）
   - 重写 5 个 public builder（返回 dict + 加 gate）
   - 加 `*_text` 兼容 wrapper
   - 保留旧 `_PROJECTION_INSTRUCTIONS` 等常量作为 dead code（Step 14 cleanup 删）

3. **跑 focused tests**
   - `pytest tests/test_ai_summary_boundary.py`
   - `pytest tests/test_ai_summary.py`（如有）

4. **跑全量 pytest** + 旧 caller spot-check
   - 确认 `ui/command_bar.py` / `ui/predict_tab.py` / `services/tool_router.py`
     调 `*_text` 兼容 wrapper 仍正常

5. **手动 spot-check UI**
   - 启 Streamlit；命令栏触发 AI summary（如 caller 已传 `enable_ai_summary=True`）
   - 验证缺 OPENAI_API_KEY 时 UI 友好降级
   - 验证 disabled 状态 UI 不崩

6. **独立 commit**
   - commit message：`fix(boundary): RISK-9 gate AI summary with source attribution`
   - 单 commit；**不**混合任何 cleanup / 不顺手改 RISK-1/2/3/7/8/10

### 15.2 不允许 inside Step 12 commit 的内容

- **不**改 `services/openai_client.py`
- **不**改 3 个 active caller（ui/command_bar / ui/predict_tab / tool_router）
- **不**改其他 LLM caller（ai_intent_parser / ai_task_parser）
- **不**改 final_decision / confidence_evaluator / predict.py
- **不**修 RISK-1 / RISK-2 / RISK-3 / RISK-7 / RISK-8 / RISK-10
- **不**删旧 prompt 常量（dead code 留 Step 14）

---

## 16. 回滚策略

### 16.1 失败模式

如果在 Step 12 实施过程中：

- LLM 模型经常 refuse JSON 输出导致 `status == "refused_missing_sources"` 高频
- post-check 误伤大量正常文本
- UI 大面积显示 "AI summary unavailable"
- 3 个 caller 因 wrapper 不兼容而崩

### 16.2 回滚原则

> **不**回退到自由文本 LLM 输出。

正确的回滚序列：

1. `git revert` fix commit
2. 保持 `enable_ai_summary=False` 默认行为；UI 显示 "AI summary unavailable"
3. **不**让 LLM 输出进入 active judgment / final_report
4. 必要时在 ai_summary.py 内保留 fallback rule-based summary（pure mapping，不
   调 LLM；从 source 字段直接拼）作为非 LLM 替代
5. 必要时调整 `_FORBIDDEN_TERMS_*` 的精度（减少误伤）；但**不**移除禁止词
   类别
6. 任何回滚动作**仍不**允许 `allow_new_judgment=True` / `require_source_attribution=False`

### 16.3 不允许的"回滚捷径"

- **不**允许悄悄改 `enable_ai_summary=True` 默认值
- **不**允许把 `bypass_postcheck=True` 作为 escape hatch
- **不**允许跳过 11F 设计直接修改 `_PROJECTION_INSTRUCTIONS` prompt 来"加强约束"
  （prompt 文字劝阻不是契约级强制）
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
- 未实际修改 ai_summary.py（保留给 Step 12）
- 未触碰 RISK-1 / RISK-2 / RISK-3 / RISK-7 / RISK-8 / RISK-10
  （各自 11A / 11B / 11C / 11D / 11E / 11G 设计）

本设计的修改路径：任何对 §4 修复目标、§5 opt-in gate、§6 source attribution、
§7 prompt constraint、§8 schema、§9 post-check、§13 测试设计、§15 实施顺序、
§10 / §11 与 final_report / openai_client 关系的调整，都必须以**显式更新本
文件**的方式提出。
