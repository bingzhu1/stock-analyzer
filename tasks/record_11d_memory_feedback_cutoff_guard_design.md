# 11D记录：Memory Feedback Cutoff Guard Design

> 本设计针对 Step 09 / Step 10 中标记为 **MEDIUM_RISK** 的 RISK-7。
>
> 本轮**只写设计**：未改代码、未新增测试、未删文件、未移动文件、未写 DB、
> 未跑 validation、未 commit / push、未进入 Step 12、未进入 3R-5 / 3R-6、
> 未新增 candidate、未复活 continuous_smoothing、未实际实现 cutoff guard、
> 未顺手碰 RISK-1 / RISK-2 / RISK-3 / RISK-8 / RISK-9 / RISK-10。

---

## 1. 设计目的

为 **memory feedback / rule preflight / pre-prediction briefing** 等历史反馈
路径设计**统一的 target_date cutoff guard**，确保在线推演时不会把
`target_date` 之后才存在的 review / outcome / rule memory 记录带入当次判断。

修复后的目标：

- 所有在线路径上的"历史经验回灌"必须满足 `record.available_as_of <= target_date`
- 缺日期字段 / 解析失败 / `record.date > target_date` 三种情况一律 **skip**，
  不允许 fallback 到全量历史
- 输出 `cutoff_guard` 自描述字段（allowed_count / skipped_count / skipped_reasons）
  让审计可追溯
- 跳过的记录仅作为 `warnings` / `cutoff_guard.skipped_reasons` 出现，**不**
  进入 `matched_rules` / `reminders` / `reasoning`

本设计**只**产出设计文档，Step 12 才实施 + commit。

---

## 2. 当前问题

### 2.1 路径概览

历史经验进入在线推演的链路：

```
projection_orchestrator_v2._build_preflight()
    → projection_rule_preflight.build_projection_rule_preflight()
        ├── projection_memory_briefing.build_projection_memory_briefing()
        │       └── memory_feedback.build_memory_feedback()
        │               └── memory_store.list_experiences()
        │                       → SQLite SELECT (无 date 过滤)
        │
        └── review_store.load_review_records()
                → SQLite SELECT (无 date 过滤)
```

### 2.2 当前缺 cutoff 的**具体证据**

| 模块 | 行 | 证据 |
|---|---|---|
| `services/memory_store.py:126-159` `list_experiences(symbol, error_category, limit)` | 132 / 153-155 | 仅按 `symbol` / `error_category` 过滤；`ORDER BY created_at DESC, id DESC LIMIT N`；**无 date 参数** |
| `services/review_store.py:268-295` `load_review_records(symbol, limit)` | 268 / 283 / 291 | 仅按 `symbol` 过滤；`ORDER BY prediction_for_date DESC, created_at DESC LIMIT N`；**无 date 参数** |
| `services/memory_feedback.py:34-61` `build_memory_feedback(symbol, error_category, limit)` | 34 / 49-53 | 调 `list_experiences(...)`，**未传 target_date**；返回的 `reminders` / `top_categories` 可能包含 created_at > target_date 的记录 |
| `services/projection_memory_briefing.py:20-46` | 25 / 32-36 | 调 `build_memory_feedback(symbol, error_category, limit)`，**无 target_date 入参** |
| `services/projection_rule_preflight.py:228-345` | 231 / 260-264 / 277 | 函数签名**有** `target_date` 参数，但**仅写入返回字典**（line 335）；调 `_memory_briefing_builder()`（260-264）+ `_review_loader()`（277）时**未传 target_date** —— target_date 实际没被用作过滤 |
| `services/pre_prediction_briefing.py` (209 行) | 全文 | `summarize_review_history` 经 review_analyzer，从 review_store 读 review records；同样未带 target_date |

### 2.3 active 路径确认

- `services/projection_orchestrator_v2.py` 是 V2 主链路（11A 已识别），它的
  `_build_preflight()` 调 `projection_rule_preflight.build_projection_rule_preflight(...)`
  → 触发上述泄漏链
- `services/home_terminal_orchestrator.py`（11A RISK-6 路径）暂不直接调
  rule_preflight；但它通过共享 services 层**间接**复用同一组 store
- `predict.py` v1 路径（RISK-8）也有 review/memory 相关调用，但本次 11D 仅
  关注 V2 链路；v1 修复留给 11E

### 2.4 表结构允许 cutoff（已存在 date 字段）

| 表 | 字段 | 是否可作为 cutoff |
|---|---|---|
| `experience_memory` | `created_at TEXT NOT NULL`（memory_store.py:48） | ✅ 可作为 cutoff（记录写入时间） |
| `deterministic_review_log` | `prediction_for_date TEXT NOT NULL`（review_store.py:39）+ `created_at TEXT NOT NULL`（review_store.py:40） | ✅ 两者都有；详见 §6 优先级 |

> 关键：表结构**已经支持** cutoff，缺的只是**调用层**的过滤。

---

## 3. 风险涉及模块

| path | current role | suspected risk | required guard |
|---|---|---|---|
| `services/memory_store.py` `list_experiences(...)` | DB 查询 experience_memory，无 date 过滤 | 返回的记录 `created_at` 可能 > target_date | **可选**：loader 加 `created_at_lte: str \| None = None` 入参（推荐 Step 12 加，但**不强制**）；call site 必须做 post-load filter |
| `services/review_store.py` `load_review_records(...)` | DB 查询 deterministic_review_log，无 date 过滤 | `prediction_for_date` / `created_at` 可能 > target_date | 同上：可选加 `cutoff_date: str \| None = None` 入参；call site 必须 filter |
| `services/memory_feedback.py` `build_memory_feedback(...)` | 直接调 `list_experiences`，无 cutoff | 在线 reminders / top_categories 含 future-experience 记录 | **必加** `target_date: str \| None = None` 入参；strict mode 过滤 created_at > target_date |
| `services/projection_memory_briefing.py` `build_projection_memory_briefing(...)` | 包装 build_memory_feedback | 同上 | **必加** `target_date` 入参；透传到 build_memory_feedback；输出 cutoff_guard 字段 |
| `services/projection_rule_preflight.py` `build_projection_rule_preflight(...)` | active V2 入口；签名有 target_date 但**未实际使用** | 调用 memory briefing / review_loader 未传 target_date | **必修**：把 target_date 显式传入 `_memory_briefing_builder` + `_review_loader`；review records 后置过滤 |
| `services/pre_prediction_briefing.py` `build_pre_prediction_briefing(...)` | review_analyzer 汇总；advisory_only=True | review history 可能含 future review | **必加** `target_date` 入参；review_analyzer 调用前 filter |
| `services/projection_orchestrator_preflight.py` (42 行) | preflight glue | 是否传 target_date 到下游待查 | **必查**：确保 target_date 显式传入 |
| `services/projection_preflight.py` (40 行) | preflight glue | 同上 | 同上 |
| `services/review_analyzer.py:179` `summarize_review_history(...)` / `:198` `summarize_review_history_by_open_scenario(...)` | review history 聚合 | 输入 records 未过滤 → 聚合含 future | **必加** target_date 入参（或要求调用方先过滤） |
| 任何其他读取 `historical review / rule memory / outcome / replay` 的 helper | grep 范围 | 待 Step 12 详查 | 同上 |

---

## 4. 违反的 contract / 原则

| contract | 章节 | 违规点 |
|---|---|---|
| 06 三系统独立原则 | §3 推演定义 / §4 否定定义 / §5 置信度定义 | 三系统判断**必须基于当时可得信息**；含 future review 即破契约 |
| 07A 推演 contract | §3.2 禁止读取 future data / §10 `future outcome → projection_system` 禁流 | 经 preflight 链回灌 future review = 违反 |
| 07B 否定 contract | §3.2 禁止读取 future data / §10 `future outcome → exclusion_system` 禁流 | 同上 |
| 07C 置信度 contract | §3.2 / §3.3 在线 vs 离线 / §11 `future outcome → confidence_system` 禁流 | 11C 已要求 confidence_evaluator 加 cutoff；11D 是**前置依赖** |
| 07D | §3.2 / §11 `future outcome → final_report` 禁流 | 同上 |
| 11C | §7.3 / §9 cutoff guard helper | 11D 提供共享 helper |

---

## 5. Cutoff guard 核心原则

> 所有在线路径上的历史 records 必须通过以下三关：

### 5.1 三关原则

```
关 1：是否有可审计的"可得日期"字段？
       ✅ 有 → 进入关 2
       ❌ 无 → SKIP，理由 "missing_audit_date"

关 2：日期能否解析为 ISO 日期？
       ✅ 能 → 进入关 3
       ❌ 否 → SKIP，理由 "unparseable_date"

关 3：record_date <= target_date？
       ✅ 是 → ALLOW
       ❌ 否 → SKIP，理由 "record_after_target_date"
```

### 5.2 默认 strict 模式

- 没有任何可用日期字段 → **SKIP**
- 日期解析失败 → **SKIP**
- `date > target_date` → **SKIP**
- 三种 skip 都**记录 skipped reason**

> **绝对不允许**："默认使用全量记录"作为 fallback。任何 skip → 在 warnings
> 里显式说明，但**不**回流到 reasoning / matched_rules。

### 5.3 不允许的"宽容模式"

- ❌ "缺日期默认认为可用"
- ❌ "解析失败默认认为是历史记录"
- ❌ "target_date 缺失 → 不过滤"
  - 例外：上游显式标记"离线 / 训练模式"，且模块 docstring 显式写明此 bypass
- ❌ "日期晚一天可以容忍"

---

## 6. 日期字段规范

### 6.1 字段优先级

按以下顺序选择**第一个非空且可解析**的字段作为 cutoff 比较值：

```
优先级 1：available_as_of    （显式声明"何时可得"）
优先级 2：created_at         （记录写入时间，DB 默认有）
优先级 3：reviewed_at        （review 完成时间）
优先级 4：prediction_date    （预测运行时刻）
优先级 5：analysis_date      （分析数据截止日）
优先级 6：prediction_for_date（预测的目标交易日）
```

### 6.2 字段语义

| 字段 | 含义 | 是否能单独证明"可得"？ |
|---|---|---|
| `available_as_of` | 显式声明"该记录在哪天起可被在线系统使用"。最权威，未来增加。 | ✅ 是 |
| `created_at` | 记录写入数据库的时间戳 | ✅ 是（写入即可得，单调） |
| `reviewed_at` | review 完成时间 | ✅ 是（review 完成 = 信息可得） |
| `prediction_date` | 预测**运行时刻**（与目标日不同；通常 = 目标日前一交易日） | ⚠️ 有限：仅证明"做预测时已知"；不证明 review 信息可得 |
| `analysis_date` | 分析数据截止日 | ⚠️ 类似 prediction_date |
| `prediction_for_date` | 预测的**目标交易日** | ❌ **不能单独证明可得**：这是预测要预测的那一天，本身不证明 review / outcome 已知。**必须**配合 `created_at` / `reviewed_at` 做更严格判断 |

### 6.3 关键约束

- `prediction_for_date` 单独存在时**不**够格作为 cutoff —— 必须与 `created_at`
  / `reviewed_at` 联合判定（取**较大**者作 cutoff 比较值，确保保守）
- `outcome_date` / `actual_date`（如果有）**只能离线使用**；不允许进入在线 cutoff
  逻辑（即不允许 "outcome_date <= target_date 就用"，因为 outcome 本身就是
  future 信息）
- `reviewed_at > target_date` 且 `prediction_for_date <= target_date` 的记录
  **仍 skip**：review 在 target_date 之后才完成，意味着 review 的反馈本身依赖
  了 target_date 之后的市场结果

### 6.4 联合判定示例

```python
def _audit_record_cutoff(record, target_date) -> tuple[bool, str]:
    """Return (allowed, reason). allowed=False means skip with reason."""
    # 1) Try priority fields
    for field in ("available_as_of", "reviewed_at", "created_at"):
        value = record.get(field)
        if value:
            iso = _parse_iso_date(value)
            if iso is None:
                return False, f"unparseable_date:{field}"
            if iso > target_date:
                return False, f"record_after_target_date:{field}={iso}"
            # found a strong cutoff — allow
            return True, f"audited_by:{field}"

    # 2) Fallback to weak fields (require pair-check)
    weak_date = None
    for field in ("prediction_date", "analysis_date"):
        value = record.get(field)
        if value:
            iso = _parse_iso_date(value)
            if iso is None:
                return False, f"unparseable_date:{field}"
            weak_date = iso if (weak_date is None or iso > weak_date) else weak_date

    if weak_date is not None:
        if weak_date > target_date:
            return False, f"record_after_target_date:weak_date={weak_date}"
        return True, "audited_by:weak_date"

    # 3) Only prediction_for_date — NOT enough alone
    if record.get("prediction_for_date"):
        return False, "missing_audit_date:only_prediction_for_date"

    # 4) No usable date
    return False, "missing_audit_date"
```

---

## 7. 通用 helper 设计

### 7.1 函数签名

建议新增 `services/cutoff_guard.py`（专属模块）或挂在共享 utils：

```python
def filter_records_by_cutoff(
    records: list[dict[str, Any]],
    *,
    target_date: str | None,
    date_fields: list[str] | None = None,
    mode: str = "strict",
) -> dict[str, Any]:
    """Filter records to those available on/before target_date.

    Returns a dict (not a tuple) so callers can attach the audit info
    directly into their response payload:

        {
            "allowed_records": list[dict],
            "skipped_records": list[dict],
            "cutoff_guard": {
                "target_date": str | None,
                "mode": "strict" | "offline_bypass",
                "allowed_count": int,
                "skipped_count": int,
                "skipped_reasons": list[str],   # unique reason codes
                "by_reason": dict[str, int],    # reason → count
            }
        }

    mode="strict" (default): no audit-date → SKIP; date > target_date → SKIP.
    mode="offline_bypass": only allowed when caller is OFFLINE training /
        calibration; module-level audit log written; **NEVER** used in
        on-line projection / exclusion / confidence / aggregator paths.

    Read-only: never mutates input records.
    """
```

### 7.2 默认 date_fields

```python
_DEFAULT_DATE_FIELDS = (
    "available_as_of",
    "reviewed_at",
    "created_at",
    "prediction_date",
    "analysis_date",
    "prediction_for_date",   # only as fallback alongside another field
)
```

### 7.3 行为细节

- 输入 `records` 是 `list[dict]`；helper 从不 mutate
- 输出 `allowed_records` / `skipped_records` 是**新 list**（dict 引用透传可，
  但不允许加字段）
- `cutoff_guard.skipped_reasons` 是**去重的 reason 代码集合**（如
  `["missing_audit_date", "record_after_target_date"]`），便于审计
- `cutoff_guard.by_reason` 是 reason → count 直方图
- helper **不**依赖 SQLite / DB；仅纯函数 + 日期解析

### 7.4 共享给 11C 的 helper

`build_confidence_result(...)` 内 §11D §7.1 的 `filter_records_by_cutoff` 可
直接引用：

```python
from services.cutoff_guard import filter_records_by_cutoff
```

避免每个 caller 各自实现 / 漂移。

---

## 8. Online vs Offline 使用边界

### 8.1 在线路径**允许**的输入

- `target_date` 之前已存在的 historical summary（已固化为 frozen artifact）
- `target_date` 之前已固化的 rule memory（experience_memory.created_at <= target_date）
- `target_date` 之前已固化的 calibration table（11C 范畴）
- `target_date` 之前可得的 market data（OHLCV）
- `target_date` 之前完成的 review records（reviewed_at <= target_date 或
  created_at <= target_date）

### 8.2 在线路径**禁止**的输入

- `target_date` **之后**才生成的 review records
- `target_date` **之后**才知道的 outcome（outcome_date 永远不进在线判断）
- `target_date` **之后** replay 产生的 correction
- 未带任何 audit_date 的 feedback records（缺判断依据 → skip）
- LLM-generated feedback（无 audit_date 概念，且 11F / RISK-9 范畴）

### 8.3 离线路径**允许**的额外行为

- 训练 / calibration 阶段允许使用 future outcome 作为 label
  （07C §3.3 已规定）
- 但**输出**必须固化为 cutoff-safe summary / weights / table，再进入在线路径
- 离线工具脚本（`scripts/run_*.py` / `services/historical_replay_training.py`
  / `services/avgo_1000day_training.py` / `services/active_rule_pool*.py`）
  **不**受本 11D cutoff guard 直接约束，但其**写入的 artifact** 必须满足
  "在线 caller 用 cutoff guard 过滤后仍可正常工作"

### 8.4 边界判定原则

- **任何 caller** 默认走 `mode="strict"`
- **离线 caller** 必须显式声明 `mode="offline_bypass"` + 模块 docstring 标注
  原因
- **绝不允许**在线路径默认走 `offline_bypass`

---

## 9. 各模块修复设计

> 本节**只描述设计**，Step 12 才实施。每个模块**最小修改**。

### 9.1 `services/cutoff_guard.py`（新建）

- ~120 行：实现 `filter_records_by_cutoff(...)` + 辅助 `_audit_record_cutoff(...)`
- 单元测试 `tests/test_cutoff_guard.py` 覆盖 §6.4 三关 + 各种 edge case

### 9.2 `services/memory_feedback.py:34` `build_memory_feedback(...)`

- 新增入参 `target_date: str | None = None`
- 调 `list_experiences(...)` 取记录后，**post-load** 调 `filter_records_by_cutoff`
- 返回 dict 中加 `cutoff_guard` 字段（来自 helper 输出）
- 如 `target_date is None`：维持原行为 + 在 docstring 警告"未提供 target_date，
  cutoff guard 已 disabled"

> **不修改** `services/memory_store.list_experiences(...)` 函数签名（保持向后
> 兼容；离线工具仍可不带 target_date 调用）

### 9.3 `services/projection_memory_briefing.py:20` `build_projection_memory_briefing(...)`

- 新增入参 `target_date: str | None = None`
- 透传到 `build_memory_feedback(symbol=..., error_category=..., limit=..., target_date=target_date)`
- 输出加 `cutoff_guard` 字段（透传 / 合并 feedback 的 cutoff_guard）
- `reminder_lines` 只来自 allowed_records；skipped 不进 reminder

### 9.4 `services/projection_rule_preflight.py:228` `build_projection_rule_preflight(...)`

- 函数签名**已有** `target_date`（line 231）；当前**未实际使用**
- 修改 `_memory_briefing_builder(symbol=..., limit=..., target_date=target_date)`（line 260-264）
- 修改 `_review_loader` 调用：line 277 改为先 `load_review_records(...)`
  再 `filter_records_by_cutoff(... target_date=target_date)`，仅 allowed 进入 `_rules_from_review_items`
- 输出 dict 加 `cutoff_guard` 段（汇总 memory + review 两个来源）
- `matched_rules` / `rule_warnings` / `rule_adjustments` 只来自 allowed_records

### 9.5 `services/pre_prediction_briefing.py` `build_pre_prediction_briefing(...)`

- 新增入参 `target_date: str | None = None`
- 调 `summarize_review_history` 之前，先用 `filter_records_by_cutoff` 过滤 review records
- 输出加 `cutoff_guard` 段
- `top_rules` / `all_rules` 只基于 allowed records

### 9.6 `services/projection_orchestrator_preflight.py` (42 行) / `services/projection_preflight.py` (40 行)

- 确认这两个 glue 模块在调下游 preflight 时**显式传 target_date**
- 不允许丢失 target_date 上下文
- 必要时新增入参；输出透传 cutoff_guard

### 9.7 `services/review_analyzer.py:179` `summarize_review_history(...)` / `:198` `_by_open_scenario(...)`

- 新增可选入参 `target_date: str | None = None`
- 入口处用 `filter_records_by_cutoff` 过滤 records
- 输出加 `cutoff_guard` 段

### 9.8 不动的模块

- `services/memory_store.py` / `review_store.py` 的 loader 函数签名**不动**
  （保持向后兼容）
- 离线 scripts / training pipelines **不动**（默认仍可不带 target_date 调
  loader；不属本 11D 范畴）
- v1 `predict.py`：保留给 RISK-8 / 11E
- 11C confidence_evaluator：本身已计划用 `filter_records_by_cutoff`（11C §7.3）；
  本次 11D 仅提供 helper

---

## 10. 输出结构设计

修复后所有相关模块输出必须含 `cutoff_guard` 段：

```jsonc
{
  // 既有字段保留
  "kind": "...",
  "matched_count": <int>,            // 仅 allowed 的数量
  "reminders": [...],                // 仅 allowed
  "matched_rules": [...],            // 仅 allowed
  "warnings": [
    "cutoff_guard 跳过 N 条记录（详见 cutoff_guard.skipped_reasons）。",
    ...
  ],

  // 新增 cutoff_guard 段
  "cutoff_guard": {
    "target_date": "YYYY-MM-DD" | null,
    "mode": "strict",
    "allowed_count": <int>,
    "skipped_count": <int>,
    "skipped_reasons": ["missing_audit_date", "record_after_target_date", ...],
    "by_reason": {
      "missing_audit_date": <int>,
      "record_after_target_date": <int>,
      "unparseable_date": <int>
    }
  }
}
```

### 10.1 不允许的输出反模式

```jsonc
// ❌ 不允许
{
  "matched_rules": [
    {"rule_id": "...", "from_future": true, ...}   // 不允许把 skipped 标 from_future 后塞进 rules
  ]
}

// ❌ 不允许
{
  "matched_rules": [...],   // 含 future records
  "warnings": ["有 N 条记录晚于 target_date，但已使用"]   // 警告写得清楚也不行 —— 必须 SKIP
}

// ❌ 不允许
{
  "matched_rules": [...],
  "cutoff_guard": null   // 字段必须存在；可全 0，但不能 null / 缺失
}
```

### 10.2 降级行为

- 如果 `target_date` 缺失：`cutoff_guard.mode = "strict"` + `target_date: null`
  + 全部记录视为 missing_audit_date → skip
- 如果 records 全部被 skip：`matched_count = 0`、`reminders = []`、
  `matched_rules = []`；warnings 加 "未获足够 cutoff-safe 历史经验"；**不**
  fallback 到全量

---

## 11. Contract enforcement tests 设计

### 11.1 必须新增的测试

| 测试名（建议） | 验证内容 |
|---|---|
| `test_cutoff_guard_filters_records_after_target_date` | 注入 `created_at = target_date + 1`，断言记录被 skip + `skipped_reasons` 含 `record_after_target_date` |
| `test_cutoff_guard_skips_records_without_audit_date` | 注入只有 `prediction_for_date` 字段（无 `available_as_of` / `created_at`），断言 skip + reason `missing_audit_date:only_prediction_for_date` |
| `test_cutoff_guard_skips_unparseable_date` | 注入 `created_at = "not-a-date"`，断言 skip + reason `unparseable_date:created_at` |
| `test_cutoff_guard_allows_records_on_or_before_target_date` | 注入 `created_at = target_date`，断言 allowed |
| `test_cutoff_guard_priority_uses_available_as_of_first` | 注入 `available_as_of = target_date - 1` + `created_at = target_date + 1`，断言 allowed（前者优先） |
| `test_cutoff_guard_no_fallback_to_all_records` | 全量 records 都被 skip，断言 `allowed_records == []`、**不** raise、**不** fallback |
| `test_cutoff_guard_target_date_none_strict_skips_all` | `target_date=None` + strict mode，断言所有 records 被视为 missing_audit_date 而 skip |
| `test_cutoff_guard_records_skipped_reasons` | 混合 reason，断言 `skipped_reasons` 去重；`by_reason` count 准确 |
| `test_cutoff_guard_does_not_mutate_records` | 调用前后 deepcopy 对比，断言 records 未被改 |
| `test_memory_feedback_filters_by_target_date` | mock list_experiences 返回混合 created_at，调 build_memory_feedback(... target_date=...)，断言 reminders 仅来自 allowed |
| `test_projection_memory_briefing_uses_cutoff_guard` | 同上，针对 build_projection_memory_briefing；输出含 cutoff_guard |
| `test_projection_rule_preflight_skips_future_rules` | mock memory_briefing + review_loader 返回部分 future 记录；断言 `matched_rules` 仅含 allowed；`cutoff_guard.skipped_count > 0` |
| `test_pre_prediction_briefing_does_not_use_future_reviews` | review_analyzer fixture 注入 future review，断言 `top_rules` 不含 |
| `test_orchestrator_preflight_passes_target_date` | 静态扫描或 mock 调用：`projection_orchestrator_preflight` 调下游时显式传 `target_date` |
| `test_review_analyzer_target_date_filter` | summarize_review_history(... target_date=...) 在过滤后聚合 |
| `test_offline_bypass_requires_explicit_mode` | 调用方未声明 `mode="offline_bypass"` 时不允许进入 bypass 分支 |

### 11.2 测试不允许的内容

- 测试**不**应允许 `cutoff_guard` 字段缺失
- 测试**不**应允许 future records 出现在 reminder / matched_rule
- 测试**不**应允许 strict mode 下 fallback 到全量
- 测试**不**应允许"target_date 缺失就不过滤"（除非显式 offline_bypass）

---

## 12. 不允许的修复方式

以下修复方式**不**符合 contract，Step 12 实施时**禁止**：

1. **不**允许"无日期字段默认使用"
2. **不**允许用 `prediction_for_date` 单独伪装 `available_as_of`
3. **不**允许 fallback 到全量历史（"过滤后是空就用全部"）
4. **不**允许读取 future outcome 后再只隐藏字段（已读 → 已泄漏）
5. **不**允许把 skipped future records 放入 `reasoning` / `matched_rules` /
   `reminders`
6. **不**允许在 online path 调 replay / outcome capture
7. **不**允许"日期晚 1 天可以容忍"（边界严格）
8. **不**允许通过修改 `services/memory_store.list_experiences` 内部默认 LIMIT
   的方式间接绕过（loader 签名稳定）
9. **不**允许在 `mode="offline_bypass"` 时不写 audit log
10. **不**允许顺手修 RISK-1 / RISK-2 / RISK-3 / RISK-8 / RISK-9 / RISK-10
11. **不**允许 cleanup 与 cutoff fix 混 commit
12. **不**允许 large rewrite：每个 fix commit 控制在最小行数
13. **不**允许进入 3R-5 / 3R-6
14. **不**允许复活 continuous_smoothing 作为"cutoff-safe替身"
15. **不**允许在 cutoff_guard 字段下保留 future records（即使作为"展示用"）

---

## 13. Step 12 实施顺序建议

> Step 12 才允许执行；本轮**不**实施。

### 推荐顺序（commit-per-fix 内部子步骤）

1. **新增 `services/cutoff_guard.py` + `tests/test_cutoff_guard.py`**
   - 实现 `filter_records_by_cutoff(...)` + `_audit_record_cutoff(...)`
   - 加 §11.1 前 9 个 helper 级测试
   - 期待 focused 测试转绿

2. **修改 `services/memory_feedback.py`**
   - 加 `target_date` 入参；call `filter_records_by_cutoff`；输出 `cutoff_guard`
   - 加 `test_memory_feedback_filters_by_target_date`

3. **修改 `services/projection_memory_briefing.py`**
   - 加 `target_date` 入参；透传；输出 `cutoff_guard`
   - 加 `test_projection_memory_briefing_uses_cutoff_guard`

4. **修改 `services/projection_rule_preflight.py`**
   - 把 `target_date` 显式传 `_memory_briefing_builder` + `_review_loader`
   - review records 后置过滤
   - 输出聚合 `cutoff_guard`
   - 加 `test_projection_rule_preflight_skips_future_rules`

5. **修改 `services/pre_prediction_briefing.py` + `services/review_analyzer.py:summarize_review_history`**
   - 加 `target_date` 入参；review_analyzer 入口处过滤
   - 加 `test_pre_prediction_briefing_does_not_use_future_reviews` +
     `test_review_analyzer_target_date_filter`

6. **修改 `services/projection_orchestrator_preflight.py` + `services/projection_preflight.py`**
   - 确认 target_date 显式传到下游
   - 加 `test_orchestrator_preflight_passes_target_date`

7. **跑 focused tests** + **跑全量 pytest**

8. **手动 spot-check**：触发 V2 路径，验证 `projection_v2_raw.preflight.cutoff_guard`
   字段存在且字段合规

9. **独立 commit**
   - commit message：`fix(boundary): RISK-7 add memory feedback cutoff guard`
   - 单 commit；**不**混合任何 cleanup / 不顺手改 RISK-1/2/3/8/9/10

### 不允许 inside Step 12 commit 的内容

- **不**改 `services/memory_store.list_experiences` 函数签名
- **不**改 `services/review_store.load_review_records` 函数签名
- **不**改离线 scripts / training pipelines
- **不**修 RISK-1 / RISK-2 / RISK-3 / RISK-8 / RISK-9 / RISK-10
- **不**做 cleanup / 不删 dead code

---

## 14. 与 11C 的关系

11C 已在 §7.3 / §9 要求 `confidence_evaluator` 加 `_filter_by_target_date` cutoff guard。

11D 与 11C 关系：

- **11D 提供共享 helper**：`services/cutoff_guard.filter_records_by_cutoff(...)`
  可直接被 11C 的 confidence_evaluator 引用
- **11D 不实现 confidence_evaluator**：仅修复 memory / preflight / briefing 路径
- **11C 不应绕过 11D cutoff guard**：confidence_evaluator 内任何 historical
  records 必须经 helper 过滤
- **顺序约束**：
  - 推荐 **11D 先于 11C 阶段 A**（让 11C 直接复用 helper）
  - 或 **11C 阶段 A 内自己写一个简化版**，然后 11D 完成后**统一替换**到 helper
  - 两种顺序都可，但**不允许**两边各自漂移实现

---

## 15. 回滚策略

### 15.1 失败模式

如果在 Step 12 实施后：

- preflight `matched_rules` 空空如也，UI 上"历史规则提醒"区域大面积变空
- briefing `reminder_lines` 大量 skip，导致 caution_level 全部"none"
- `pre_prediction_briefing.top_rules` 长期为空

### 15.2 回滚原则

> **不**回退到无 cutoff 的旧逻辑。

正确的回滚序列：

1. 保留 cutoff guard 已加的代码
2. 在 UI / narrative 层显式标注 "本次未获足够 cutoff-safe 历史经验"
3. 允许 confidence / projection 层降级为 unknown / insufficient historical context
4. 必要时**短期**调整 strict mode 的报告频率（每天打印 cutoff_guard summary
   到日志），让维护者看到 skip 量
5. **不**允许 fallback 到 future records
6. **不**允许"target_date 缺失就不过滤"

### 15.3 不允许的"回滚捷径"

- **不**允许把 cutoff guard helper 默认改为 `mode="lenient"`
- **不**允许悄悄把 future records 放进 `cutoff_guard.allowed_records`
- **不**允许跳过 11D 设计直接修改 store loader 把过滤交给 SQL 层（逻辑等价
  但**不**符合"单点 helper"原则；store loader 修改属另一次重构）
- **不**允许在 `cutoff_guard` 字段下保留 future records 作为"参考"

---

## 16. 严守边界

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
- 未实际实现 cutoff guard（保留给 Step 12）
- 未触碰 RISK-1 / RISK-2 / RISK-3 / RISK-8 / RISK-9 / RISK-10
  （各自 11A / 11B / 11C / 11E / 11F / 11G 设计）

本设计的修改路径：任何对 §3 涉及模块、§5 核心原则、§6 字段优先级、§7 helper
设计、§9 各模块修复、§10 输出结构、§11 测试设计、§13 实施顺序、§14 与 11C
关系的调整，都必须以**显式更新本文件**的方式提出。
