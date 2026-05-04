# Step 2G-4.5 — Soft Metadata Schema Review Checkpoint

> **设计文档（review checkpoint），不是实现。** 本文档**冻结** Step 2G-5
> simulator 的最终 schema 决策。Step 2G-5 实现**应引用本文件的 §5 / §6 /
> §7 / §8 / §9 / §10**，**不应直接引用** Step 2G-4
> ([`tasks/step_2g4_soft_metadata_layer_design.md`](step_2g4_soft_metadata_layer_design.md))
> 的原始 schema —— 后者保留为历史设计 commit，本文件作为 schema 修订
> 的最终输入。
>
> 本轮**不动任何代码**：不改 `predict.py` / `scanner.py` /
> `prediction_store.py` / `projection_output_adapter.py` /
> `projection_output_contract.py` / `regime_diagnostics_dashboard.py` /
> 任何 builder / 任何 read-only 工具 / DB schema 中的任何一处。
> 也**不**新增任何测试 / 不启用 hard / 不启用 forced /
> 不接 anti-false-exclusion 模块。

## 1. 当前完成状态

- Step 2G-4 **soft metadata layer design** 已进入 main
  （commit `607ccc0` / [`tasks/step_2g4_soft_metadata_layer_design.md`](step_2g4_soft_metadata_layer_design.md)）
- Step 2G-4.5 已完成只读 schema review（本文件之前的 review 答复）。
- 本 checkpoint **固定** Step 2G-5 simulator 实施时使用的最终 schema 决策：
  candidate 集合（§6）、historical metrics 来源 / 时机 / 字段（§7）、
  severity enum（§8）、dedup / overlap 规则（§9）、测试要求（§10）。
- Step 2G-5 simulator 实施**不应**直接引用 Step 2G-4 的原始 schema。
  Step 2G-4 保留为历史 design commit；Step 2G-5 应基于本 checkpoint
  §5-§10 的修订 schema。

## 2. 当前 main 状态

- main 最新 commit：`607ccc0 docs(contract): Step 2G-4 soft metadata layer design`
- Step 2G-4 design doc 已存在于 `tasks/step_2g4_soft_metadata_layer_design.md`
- 本轮**没有**任何代码 / DB / 测试 / schema 改动；仅新增本 markdown
  checkpoint
- 测试基线：未触碰（保持 2254 / 0 failed / 10 skipped）

## 3. Review 总结

- **方向正确**：Step 2G-4 设计的核心方向（metadata-only / 不进 04 required /
  不启 hard / 不接 trading）与 Step 2G-3 数据再审结论一致，没有回退红线。
- **schema shape 不够稳定**：`historical_metrics` 计算时机模糊、
  candidate 之间高度 overlap、severity enum 保留 `"high"` / `"hard"`
  无用值、缺少 `schema_version` —— 这些都是 schema 形状决策，不是命名
  细节，不能在 Step 2G-5 实施阶段"边写边定"，否则 reviewer / tester /
  dashboard 实施者会重新争论一遍。
- **必须先修正后再进 simulator**：versioning / historical metrics 来源 /
  candidate overlap / severity enum / deterministic testing 五个维度
  共**8 条 blocker**，固化在 §4。
- **Step 2G-3 数据基线不变**：本 review 没有触发新的数据 deep-dive；
  R4 (`samples=36 / paired=34 / accuracy=0.324 / bias_gap=+0.676 /
  false_exclusion_rate=0.3235 / net_benefit=+0.0219`) 仍是
  metadata-only 阶段唯一通过证据门槛的候选。

## 4. Blocking issues

> 8 条必须在 Step 2G-5 实施前**冻结决策**的 blocker。每条都给出
> "为什么 blocking"+"决策方向"。详细 schema 改动见 §5；细化决策见 §6-§10。

### Blocker 1 — `schema_version` 字段缺失

- **为什么 blocking**：Step 2G-5 一旦 emit
  `extras.soft_metadata`，dashboard / review / 未来 contract validator
  都要解析它。没有版本号，未来加字段 / 改 severity 枚举 / 删 candidate
  → 下游消费者无法判断该用哪个 schema 路径。
- **决策**：必有 `schema_version: "soft_metadata.v1"` 字段；本 checkpoint
  对应的 schema 即 v1；任何 schema 改动必须 bump 到 v2 + 写 migration
  guide。

### Blocker 2 — `historical_metrics` 计算时机不明确

- **为什么 blocking**：Step 2G-4 spec 说"触发当下的快照"，但**没说谁算 /
  何时算**。如果 simulator 在每次 prediction 时重读 DB 算 R4 acc，
  **每写一条 replay 都会改数字** → Step 2G-5 测试全部 flaky；同一条
  prediction 在不同时间调用 simulator 会得到不同 metadata。
- **决策**：simulator 默认使用 **caller-injected baseline** 模式
  （详见 §7）；CLI / 诊断模式可走 internal compute，但**不**作为
  deterministic tests 的默认路径。

### Blocker 3 — `metrics_source` / `metrics_window` / `metrics_computed_at` 缺失

- **为什么 blocking**：没有这三个字段就无法 audit "这次 simulator
  输出基于哪份数据 / 哪个时间窗口 / 何时算的"。Step 3D-1 dashboard
  的 R4 数字会随 DB 增长（每次新 replay 写入）发生轻微变化，下游
  必须能识别 metrics 的来源版本。
- **决策**：三个字段必填（详见 §5 / §7）。

### Blocker 4 — R4 阈值必须 import 同一常量，不能重复定义

- **为什么 blocking**：R4 阈值 (`5.0` / `0.62`) 在
  [`services/regime_diagnostics_dashboard.py:56-57`](../services/regime_diagnostics_dashboard.py)
  已是常量
  (`_R4_AVGO_MINUS_SOXX_THRESHOLD = 5.0` / `_R4_POS20_THRESHOLD = 0.62`)。
  Step 2G-5 simulator 如果局部重定义这两个数字，将来 dashboard 改阈值时
  simulator **静默 drift**，dashboard 与 simulator 给出不一致的 R4
  judgment。
- **决策**：Step 2G-5 simulator **必须** `from
  services.regime_diagnostics_dashboard import
  _R4_AVGO_MINUS_SOXX_THRESHOLD, _R4_POS20_THRESHOLD`，**不**重复定义；
  Step 2G-5 测试 suite 包含一项 `assert simulator._R4_THR is dashboard._R4_AVGO_MINUS_SOXX_THRESHOLD`
  防 drift。

### Blocker 5 — `bullish_high_pos20` 必须算 residual metrics

- **为什么 blocking**：Step 2G-4 §5.2 给的 `bullish_high_pos20` 指标
  (81 / 79 / acc 0.418 / gap +0.582) 是**整体**切片，包含 R4 的 36 条
  样本。当 R4 不触发但 pos20 仍 > 0.62 时，实际显示给 dashboard 的
  metadata 应该是**残差** `bullish_high_pos20 ∖ R4` 的指标，而**这个
  数字 spec 没给**。如果 Step 2G-5 显示整体切片的 acc，dashboard 会
  在非 R4 上下文里展示一个含 R4 数据的指标 → 误导。
- **决策**：candidate 改名 `bullish_high_pos20_residual`；
  `historical_metrics_in_sample` 必须基于残差切片计算（详见 §6 / §7）。
  Step 2G-5 实施时 caller 计算两版指标：R4 触发版（用 R4 metrics）/
  R4 未触发版（用 residual metrics）。

### Blocker 6 — `bullish_peer_upgrade_overextension` 应降级为 R4 evidence subtype

- **为什么 blocking**：Step 2G-4 §6.2 数据：R4 中 24/26 都是 peer_upgrade。
  §8.2 dedup 规则也写明"R4 触发时把它合并成 R4 的 evidence 子项"。
  这意味着该候选**几乎从不独立 emit** —— 那为何还放在顶级 candidate
  enum 里？保留只会让 Step 2G-5 实施者实现一条永远不会单独触发的代码
  路径 + 给 dashboard 增加一条永远显示不到的 entry。
- **决策**：从顶级 `signals` candidate enum **删除**；改为 R4 entry 的
  `trigger_context.peer_subtype: "upgrade"` 标志（详见 §5 / §6）。

### Blocker 7 — `peer_weaken_metadata_only` / `high_path_risk_metadata_only` 应从 candidates 删除

- **为什么 blocking**：Step 2G-4 §7 说"不进 signals 列表，可在 context
  子 dict"。**半 spec**：`context` 形状未定。Step 2G-5 实施时这两个候选
  会再次成为模糊点 —— 要么用某个未定形状的 `context` 子 dict 兜住，
  要么半实现一半不实现。Step 2G-3 数据已证明这两个信号的 accuracy 反而
  **高于** baseline（`peer_weaken=0.516` vs `none=0.459`；
  `high_path_risk=0.564` vs `none=0.459`），它们**不是** over-bullish
  风险信号，进 soft_metadata 没有正向价值。
- **决策**：从 soft_metadata candidates **完全删除**；dashboard 想显示
  `soft_signal=peer_weaken` / `path_risk=high` 的话，直接读 `extras`
  同级已有的 `soft_signal` / `path_risk_level` raw 字段（Step 2C-2 已
  暴露）；不在 soft_metadata.v1 里实现 `context` 子 dict，避免 schema
  膨胀。

### Blocker 8 — severity enum 收窄为 `{"low", "medium"}`

- **为什么 blocking**：Step 2G-4 §9.1 enum 包含 `"high"` / `"hard"`
  两个**保留不用**的值。任何看到 enum 的人会假设 `"high"` 是合法值
  → dashboard 后续可能误用，渲染成"高风险禁止交易"或"hard signal" UI
  → 违反 Step 2G 设计文档 §6 红线"任何单一 extras 字段不能直接 hard"
  的精神。
- **决策**：severity enum 收窄为 `{"low", "medium"}`，**删除** `"high"`
  / `"hard"` 保留位；hard gate 的判断由代码层 + `hard_exclusion_allowed`
  字段（永远 `False`）负担，**不**靠 severity 表达；hard 如未来启用，
  必须走 04 required 字段 (`exclusion_level=hard`) 和 Step 2G-8+ 流程，
  与 sidecar `severity` 解耦。

## 5. 决策后的 schema（修订版，soft_metadata.v1）

> 这是 Step 2G-5 simulator 必须 emit 的最终 schema 形状。
> 任何偏离都视为实施 bug，应该回到本 checkpoint 重新审议。

```python
exclusion_system.extras.soft_metadata = {
    "schema_version": "soft_metadata.v1",                    # Blocker 1
    "metrics_source": "regime_diagnostics_dashboard_v1",     # Blocker 3
    "metrics_window": {                                      # Blocker 3
        "analysis_date_min": "2023-01-03",
        "analysis_date_max": "2024-08-02",
        "paired_total": 286,
        "db_snapshot_id": None,                              # 实施时填 sha 或 None
    },
    "metrics_computed_at": "2026-05-04T00:00:00",            # Blocker 3 (ISO timestamp)
    "signals": [
        {
            "name": "r4_overextension",                      # Blocker 6 / 7 (enum 收窄)
            "display_label": "高位跑赢同行后的偏多过热",       # non-blocking 1
            "severity": "medium",                            # Blocker 8 (enum {low, medium})
            "dedup_group": "bullish_overextension",          # non-blocking 5
            "raw_features": {                                # non-blocking 1 (split)
                "avgo_minus_soxx_20d": 7.3,
                "pos20": 0.81,
            },
            "trigger_context": {                             # non-blocking 1 (split)
                "final_direction": "偏多",
                "confidence_level": "high",
                "primary_score_raw": 2.7,
                "matched_or_branch": "confidence_high",      # non-blocking 1
                "peer_subtype": "upgrade",                   # Blocker 6 (降级 candidate 3)
            },
            "historical_metrics_in_sample": {                # non-blocking 4 (后缀)
                "samples": 36,
                "paired": 34,
                "accuracy": 0.324,
                "bias_gap": 0.676,
                "false_exclusion_rate": 0.3235,
                "net_benefit": 0.0219,
            },
            "holdout_status": "FAIL",                        # non-blocking 4
            "recommended_action": "review_only",
            "hard_forbidden_primary_reason": "false_exclusion_rate_too_high",  # non-blocking 2
            "hard_forbidden_breakdown": [                    # non-blocking 2
                "false_exclusion_rate=0.3235 > 0.10",
                "net_benefit=0.0219 < 0.05",
                "anti_false_exclusion_not_connected",
            ],
        },
        # 0..N entries; N ≤ 3 总数；v1 实际预计最多 1-2 条（详见 §9）
    ],
    "summary": {
        "has_overextension_signal": True,
        "max_severity": "medium",                            # 空时固定 "none"
        "hard_exclusion_allowed": False,                     # 永远 False
        "signal_count": 1,                                   # derived; assert == len(signals)
        "primary_signal": "r4_overextension",                # 空时 None
    },
}
```

空触发（无 candidate 命中）时：

```python
exclusion_system.extras.soft_metadata = {
    "schema_version": "soft_metadata.v1",
    "metrics_source": "regime_diagnostics_dashboard_v1",
    "metrics_window": {...},                                 # 同上
    "metrics_computed_at": "2026-05-04T00:00:00",
    "signals": [],
    "summary": {
        "has_overextension_signal": False,
        "max_severity": "none",                              # 空时固定 "none" 字面量
        "hard_exclusion_allowed": False,
        "signal_count": 0,
        "primary_signal": None,
    },
}
```

## 6. Candidate set after review

### 6.1 Active signal enum（Step 2G-5 必须实现）

| `name` | 触发条件 | 来源 |
|---|---|---|
| `r4_overextension` | `avgo_minus_soxx_20d > 5 ∧ pos20 > 0.62 ∧ final_direction == "偏多" ∧ (confidence_level == "high" ∨ primary_score_raw > 2)` | Step 2G-4 §4 + Blocker 6 (并入 peer_upgrade) |
| `bullish_high_pos20_residual` | `final_direction == "偏多" ∧ confidence_level == "high" ∧ pos20 > 0.62 ∧ ¬r4_overextension` | Blocker 5（残差切片，去除 R4 重叠） |

`signals[i].name` 完整 enum 即此两值；任何其他名都视为实施 bug。

### 6.2 Removed from top-level signals

| 原候选 | 处置 | 理由 |
|---|---|---|
| `bullish_peer_upgrade_overextension` | **降级**为 R4 entry 的 `trigger_context.peer_subtype: "upgrade" \| "hold" \| "downgrade"` 标志 | Blocker 6（R4 中 24/26 都是 upgrade，几乎从不独立触发） |
| `peer_weaken_metadata_only` | **完全删除**；dashboard 改读 `extras.soft_signal` raw 字段 | Blocker 7（accuracy 反而高于 baseline，无 over-bullish 信号价值） |
| `high_path_risk_metadata_only` | **完全删除**；dashboard 改读 `extras.path_risk_level` / `extras.soft_signal` raw 字段 | Blocker 7（同上） |
| `peer_path_lower_bullish` | **不引入**（Step 2G-4 §7 提及但未列入 candidate） | gap +0.20 不足以承担 metadata；dashboard 想显示直接读 raw 字段 |
| `conflicting_factors_count_alias_note` | **不引入** | 与 `peer_weaken` 几乎完全 alias；不是独立信号 |

### 6.3 Metadata-only context（不在 v1 实现）

`soft_metadata.v1` **不**包含 `context` 子 dict；不在 schema 里复制
`extras` 同级已有的 `soft_signal` / `path_risk_level` /
`peer_path_risk_direction` / `conflicting_factors_count` raw 字段。

避免 schema 膨胀；让 `soft_metadata` 只负责"over-bullish risk metadata"
这一件事。

## 7. Historical metrics policy

### 7.1 Preferred mode：caller-injected baseline

Step 2G-5 simulator 的**默认 API**：

```python
def build_soft_metadata(
    contract_payload: dict,                                  # 单条 prediction 的 payload
    baseline: dict,                                          # caller 预先算好的 baseline dict
    *,
    coded_data_dir: str | Path | None = None,                # R4 trigger 判断需要 pos20 / SOXX diff
) -> dict | None:
    ...
```

`baseline` 形状（caller 调用 `regime_diagnostics_dashboard` 算一次后传入）：

```python
baseline = {
    "metrics_source": "regime_diagnostics_dashboard_v1",
    "metrics_window": {
        "analysis_date_min": "...", "analysis_date_max": "...",
        "paired_total": 286, "db_snapshot_id": None,
    },
    "metrics_computed_at": "<ISO>",
    "r4_overextension": {                                    # 整切片 in-sample 指标
        "samples": 36, "paired": 34,
        "accuracy": 0.324, "bias_gap": 0.676,
        "false_exclusion_rate": 0.3235, "net_benefit": 0.0219,
    },
    "bullish_high_pos20_residual": {                         # 残差切片指标（Blocker 5）
        "samples": ?, "paired": ?,                           # caller 计算时填
        "accuracy": ?, "bias_gap": ?,
        "false_exclusion_rate": ?, "net_benefit": ?,
    },
}
```

caller-injected 模式下，simulator 是**纯函数**：相同输入 → 相同输出，
测试稳定。

### 7.2 Optional mode：internal compute

Step 2G-5 CLI / 诊断模式允许 simulator 自己读 DB 算 baseline：

```python
def build_soft_metadata_with_internal_baseline(
    contract_payload: dict,
    *,
    db_path: str | Path | None = None,
    coded_data_dir: str | Path | None = None,
    limit: int = 450,
) -> dict | None:
    baseline = _compute_baseline_from_db(db_path, limit, coded_data_dir)
    return build_soft_metadata(contract_payload, baseline, coded_data_dir=coded_data_dir)
```

强约束：
- internal compute 模式**只**用于 CLI / 诊断；**不**作为 deterministic
  unit tests 的默认路径
- 测试 §10.1 要求显式覆盖两种模式：caller-injected 模式做 deterministic
  output 测试；internal compute 模式做 smoke test（只 assert status / shape，
  不 assert 具体数值）

### 7.3 Fields contract

- `metrics_source` 必须为 `"regime_diagnostics_dashboard_v1"` 字符串
  常量；版本随 dashboard 升级而 bump
- `metrics_window.analysis_date_min` / `analysis_date_max` /
  `paired_total` 必填；`db_snapshot_id` 可选（实现时填 git sha 或
  None）
- `metrics_computed_at` ISO 8601 timestamp，UTC 或本地都可（测试需固定
  注入避免 flake）
- R4 阈值 `_R4_AVGO_MINUS_SOXX_THRESHOLD` / `_R4_POS20_THRESHOLD` 必须
  `from services.regime_diagnostics_dashboard import` —— 不重定义
  （Blocker 4）

## 8. Severity decision

### 8.1 Final enum

`severity ∈ {"low", "medium"}`（仅 2 值）。

| severity | 自动派生条件（acc 与 gap 都基于 historical_metrics_in_sample） | 当前 candidate |
|---|---|---|
| `"low"` | `accuracy ≥ 0.45` **且** `bias_gap ≤ 0.50` | （v1 当前无候选落入；保留供未来扩展） |
| `"medium"` | `accuracy < 0.45` **或** `bias_gap > 0.50`，且未达 hard gate | `r4_overextension`（acc 0.324 / gap 0.676 → medium）；`bullish_high_pos20_residual`（待 caller 算残差，但预期 acc < 0.45 / gap > 0.50 → medium） |

注：边界值采用**严格小于 / 大于** —— `accuracy = 0.45` 严格归 `low`；
`bias_gap = 0.50` 严格归 `low`。Step 2G-5 测试必须覆盖这两个边界。

### 8.2 不使用的值

- ❌ `"high"` —— 容易被 UI 误解成"高风险禁止交易"
- ❌ `"hard"` —— 容易被 UI 误解成 hard exclusion / 强否定决策
- ❌ `"informational"` / `"caution"` / `"review"` —— 与 review code
  既有 `low/medium/high` 命名约定不一致；保留传统命名

### 8.3 hard 与 severity 的解耦

- `hard_exclusion_allowed` **永远** `False`（v1 spec 层面强约束）
- 如未来 hard 启用：
  - 必须走 04 required 字段（`exclusion_system.exclusion_level = "hard"`）
  - 必须走 Step 2G-8+ 流程（前提是 Step 2G 设计文档 §8 hard gate 全部
    通过）
  - 与 sidecar `severity` **解耦**：sidecar severity 仍只取 `low /
    medium`；hard 通过 04 required 字段表达，不污染 sidecar enum

## 9. Dedup / overlap decision

### 9.1 Hierarchical nesting

candidates **不是**并列独立信号，而是**层级嵌套**：

```
final_direction=偏多 ∧ confidence=high ∧ pos20>0.62
└── bullish_high_pos20_residual                        ← 81 paired 整切片
    └── r4_overextension                               ← 36 sample 子切片（最具体）
```

R4 是 `bullish_high_pos20` 的真子集（前者多了
`avgo_minus_soxx_20d > 5` + `(high ∨ psr>2)` 的 OR 约束）。

### 9.2 优先级（high → low）

1. `r4_overextension`（最具体；最强 over-bullish 信号）
2. `bullish_high_pos20_residual`（R4 不触发时的残差兜底）

Step 2G-5 simulator dedup 算法：
- 计算所有 candidate 的触发条件
- 在同 `dedup_group` 内挑**最高优先级**的 1 条 emit
- v1 中两个 candidate 同属 `dedup_group: "bullish_overextension"` —— 同时
  匹配时**只**输出 R4

### 9.3 全局上限

- `signals` 列表**最多 3 条**（与 Step 2G-4 §8.3 一致）
- v1 实际预计**最多 1-2 条**（当前 enum 只有 2 个 candidate；同 dedup
  group 后实际最多 1 条）
- 超出上限的丢弃（**不**显示 "more" 提示）

### 9.4 全局 invariants

- `summary.hard_exclusion_allowed` **永远** `False`
- `summary.signal_count == len(signals)`（assert 一致；任何不一致视为
  实施 bug）
- `summary.primary_signal == signals[0].name if signals else None`
- `summary.max_severity == max(s.severity for s in signals) if signals
  else "none"`（"medium" > "low" > "none" 排序）

## 10. Step 2G-5 simulator test requirements

> 必须覆盖。Step 2G-5 实施时按本清单建测试文件 `tests/test_soft_metadata_simulator.py`。

### 10.1 Schema 完整性

| # | 测试 |
|---|---|
| 10.1.1 | `schema_version == "soft_metadata.v1"` 字段存在且为该常量 |
| 10.1.2 | `metrics_source` / `metrics_window` / `metrics_computed_at` 三字段必填 |
| 10.1.3 | `metrics_window.{analysis_date_min, analysis_date_max, paired_total}` 三子字段必填 |
| 10.1.4 | 空触发：`signals=[]`、`summary` 五字段全填 default（不省略）；`max_severity == "none"`、`primary_signal is None` |
| 10.1.5 | `summary.signal_count == len(signals)`（任何输入下） |
| 10.1.6 | `summary.hard_exclusion_allowed is False`（任何输入下；强 invariant） |

### 10.2 Trigger logic

| # | 测试 |
|---|---|
| 10.2.1 | R4 触发 → 输出 1 条 entry，`name == "r4_overextension"` |
| 10.2.2 | R4 不触发但 bullish_high_pos20_residual 触发 → 输出 1 条 entry，`name == "bullish_high_pos20_residual"` |
| 10.2.3 | R4 与 bullish_high_pos20 同时命中 → **只**输出 R4，且不输出 bullish_high_pos20_residual |
| 10.2.4 | R4 触发 + `peer_adjustment=upgrade` → R4 entry 的 `trigger_context.peer_subtype == "upgrade"` |
| 10.2.5 | R4 触发 + `peer_adjustment=hold` → `trigger_context.peer_subtype == "hold"` |
| 10.2.6 | R4 触发 OR 分支由 high confidence 命中 → `trigger_context.matched_or_branch == "confidence_high"` |
| 10.2.7 | R4 触发 OR 分支由 primary_score_raw > 2 命中（low/medium confidence）→ `trigger_context.matched_or_branch == "primary_score_raw_above_2"` |

### 10.3 Removed candidate enforcement

| # | 测试 |
|---|---|
| 10.3.1 | `soft_signal=peer_weaken` 输入 → soft_metadata 中**没有** `peer_weaken_metadata_only` entry |
| 10.3.2 | `path_risk_level=high` 输入 → soft_metadata 中**没有** `high_path_risk_metadata_only` entry |
| 10.3.3 | `peer_adjustment=upgrade` 单独触发（无 R4 / 无 bullish_high_pos20 上下文）→ soft_metadata 中**没有** `bullish_peer_upgrade_overextension` entry |
| 10.3.4 | `signals[i].name` 只允许 `{"r4_overextension", "bullish_high_pos20_residual"}` 两值之一 |

### 10.4 Severity classification

| # | 测试 |
|---|---|
| 10.4.1 | severity 仅取 `{"low", "medium"}`；任何输出 `"high"` / `"hard"` / 其他值视为 bug |
| 10.4.2 | 边界值：`accuracy = 0.45` 严格 → `low`（`accuracy < 0.45` 才升 medium） |
| 10.4.3 | 边界值：`bias_gap = 0.50` 严格 → `low`（`bias_gap > 0.50` 才升 medium） |
| 10.4.4 | `_classify_severity(metrics_dict) -> str` 是纯函数，相同输入 → 相同输出 |
| 10.4.5 | R4 实测指标（acc 0.324 / gap 0.676）→ `medium` |

### 10.5 Read-only / determinism

| # | 测试 |
|---|---|
| 10.5.1 | caller-injected baseline 模式下 output deterministic（相同 contract_payload + baseline → byte-stable JSON） |
| 10.5.2 | simulator **不**写 DB（call 前后 `prediction_log` / `outcome_log` row count 不变） |
| 10.5.3 | simulator 模块源码 grep：**没有** `import yfinance` / `from yfinance` / `import requests` / `from requests` / `longbridge` / `broker` / `paper_trade` |
| 10.5.4 | simulator 模块源码 grep：**没有** `import services.confidence_engine` / `import services.contradiction_engine` / `import services.risk_model`（三个 v1 stub trio 整仓库零 import 状态保持） |
| 10.5.5 | regression snapshot：5 个固定 contract_payload 输入 → 5 个固定 JSON 输出（byte-stable） |

### 10.6 R4 阈值常量同步

| # | 测试 |
|---|---|
| 10.6.1 | `from services.soft_metadata_simulator import _R4_AVGO_MINUS_SOXX_THRESHOLD as sim_thr; from services.regime_diagnostics_dashboard import _R4_AVGO_MINUS_SOXX_THRESHOLD as dash_thr; assert sim_thr is dash_thr`（防 drift） |
| 10.6.2 | 同上对 `_R4_POS20_THRESHOLD` |
| 10.6.3 | 或：grep simulator 源码确认无字面量 `5.0` / `0.62` 出现在 R4 判断逻辑中 |

### 10.7 Required fields invariance

| # | 测试 |
|---|---|
| 10.7.1 | simulator output 的同一 contract_payload，04 `exclusion_system` 5 个 required 字段不变（仍 `none / [] / [] / False / False`） |
| 10.7.2 | 05 `confidence_system` 4 个 score 字段不变（仍 `0.0` / `event_score=None`） |
| 10.7.3 | 07 `simulated_trade` 6 个决策字段不变（`no_trade` / `none` / 空 / `0%`） |
| 10.7.4 | `validate_projection_output(payload)` 在新增 `extras.soft_metadata` 后仍返回 `[]`（无 error）—— validator 对 extras 内部不强校验 |
| 10.7.5 | 现有测试基线不变：`tests/test_exclusion_system_contract_fields.py` / `tests/test_confidence_system_contract_fields.py` / `tests/test_simulated_trade_contract_fields.py` 全部 pass |

### 10.8 Graceful degradation

| # | 测试 |
|---|---|
| 10.8.1 | 缺 `coded_data/AVGO_coded.csv` → R4 / bullish_high_pos20_residual 无法判断 → 写 warning 到 `summary.warnings`（v1 schema 可加可选 `warnings` 字段）；不 raise；signals=[] |
| 10.8.2 | 缺 `coded_data/SOXX_coded.csv` → `avgo_minus_soxx_20d` 无法算 → R4 不能 emit；bullish_high_pos20_residual 仍可（不依赖 SOXX）；写 warning |
| 10.8.3 | `analysis_date >= "2026-01-01"` → simulator warning 或 refusal，**不**计算 R4（防止 final test contamination） |
| 10.8.4 | 损坏 contract_payload（缺 `final_projection.final_direction`）→ 不 raise；signals=[]；写 warning |

### 10.9 CLI smoke

| # | 测试 |
|---|---|
| 10.9.1 | CLI 接受 `--symbol` / `--limit` / `--db` / `--coded-data-dir` / `--analysis-date-max`（cutoff 参数）；stdout JSON `ensure_ascii=False, indent=2` |
| 10.9.2 | CLI internal compute 模式 smoke：在 main DB 上跑通，status="ok" |

## 11. Remaining non-blocking suggestions

> 这些是 review 中的 non-blocking 建议；按 §5 schema 已**默认采纳**。
> Step 2G-5 实施时无需重新决策，按 §5 schema 实现即可。

| # | 建议 | §5 中已采纳 |
|---|---|---|
| 11.1 | `evidence` 拆分 `raw_features` / `trigger_context` | ✅ |
| 11.2 | `hard_forbidden_reason` 改 `hard_forbidden_primary_reason` + `hard_forbidden_breakdown`（list） | ✅ |
| 11.3 | `display_label` 中文文案字段 | ✅（仅 `r4_overextension` 给了示例；其他 candidate 实施时同补） |
| 11.4 | `historical_metrics_in_sample` 后缀 + `holdout_status` | ✅ |
| 11.5 | `signal_count` 标记为 derived + assert 一致 | ✅（§9.4 / §10.1.5 测试） |
| 11.6 | `dedup_group` 用于 UI 去重 | ✅ |
| 11.7 | empty signals 时 summary 默认值完整 | ✅（§5 空触发示例 + §10.1.4 测试） |

## 12. 是否进入 Step 2G-5

### 12.1 决策：**有条件 yes**

可以进入 Step 2G-5（read-only sidecar simulator），但**必须满足以下
约束**：

- ✅ Step 2G-5 实施基于本 checkpoint §5 修订 schema，**不**直接引用
  Step 2G-4 原始 schema
- ✅ Step 2G-5 simulator **必须** read-only：`SELECT` only / 不调用
  `init_db` / 不写文件 / 不接网络 / 不接 trading
- ✅ Step 2G-5 simulator **不**改 04 / 05 / 07 任何 required 字段
- ✅ Step 2G-5 simulator **不**启用 `hard` / `forced_exclusion` /
  `anti_false_exclusion_triggered`
- ✅ Step 2G-5 测试覆盖 §10 全部要求（schema / trigger / removed
  candidate / severity / read-only / R4 阈值同步 / required invariance /
  graceful degradation / CLI smoke）
- ✅ Step 2G-5 默认 caller-injected baseline 模式（§7.1）；internal
  compute 仅 CLI / 诊断
- ✅ Step 2G-5 R4 阈值从 `regime_diagnostics_dashboard.py` import，
  **不**重定义
- ❌ Step 2G-5 **不**实现 `soft_metadata.context` 子 dict（v1 不引入）
- ❌ Step 2G-5 **不**接 4 个 anti-false-exclusion 离线模块到主链
  （延后到 Step 2G-7+）

### 12.2 不建议

- ❌ **不**在 Step 2G-5 实施中"边写边定 schema"（已固化在 §5-§10）
- ❌ **不**绕过 Blocker 8 在 enum 里保留 `"high"` / `"hard"`
- ❌ **不**在 simulator 中实时读 DB 算 metrics 作为默认路径
- ❌ **不**直接跳过 Step 2G-5 做 Step 2G-6 dashboard（dashboard 需要
  simulator 的 JSON 输出作为消费源）
- ❌ **不**提前做 Step 2G-7 / 2G-8（前者依赖 simulator + dashboard；
  后者依赖 hard gate 通过，当前 6 项 gate 有 4 项 fail）

### 12.3 推荐 Step 2G-5 实施顺序

1. 新建 `services/soft_metadata_simulator.py`：纯函数 `build_soft_metadata`
   （caller-injected baseline 模式）
2. 新建 `scripts/build_soft_metadata.py`：argparse CLI，internal compute
   模式（自己读 DB 算 baseline）
3. 新建 `tests/test_soft_metadata_simulator.py`：覆盖 §10 全部要求
4. 跑 full `pytest -q`，确认基线不变（**目标 2254 + 新增测试数**，
   0 failed，10 skipped 不变）
5. 更新 `tasks/step_1_contract_pipeline_summary.md` 新增 §25
6. commit / push / merge to main

## 13. 2026 final test cutoff

- 本 review 未使用 **2026-01-01 之后**的数据；与 Step 2G-3 / Step 3D-1
  的 2023-01-03 → 2024-08-02 replay window 完全一致。
- Step 2G-5 simulator **不得**用 2026-01-01 之后的 final test 数据
  调参 / 反复跑：
  - simulator API 必须接受 `analysis_date_max` cutoff 参数（默认
    `<= "2025-12-31"` 或 `< "2026-01-01"`）
  - 输入 `analysis_date >= "2026-01-01"` 时，simulator 应**warning 或
    refusal**（§10.8.3 测试），防止无意中把 final test 数据混入调参样本
- 2026-01-01 之后仍是**整个系统**完成后的最终测试集；任何 sidecar
  metadata 实施都不得在 final test 之前消耗这部分数据。

## 14. 严守边界

- ❌ 本文档**只是** review checkpoint / spec 修订
- ❌ 没改任何代码
- ❌ 没新增任何测试
- ❌ 没写 DB
- ❌ 没改 DB schema
- ❌ 没接 `yfinance` / `requests` / 任何网络
- ❌ 没接 trading API / `longbridge` / `broker` / `paper_trade`
- ❌ 没改 `predict.py` / `scanner.py` / `prediction_store.py`
- ❌ 没改 `projection_output_adapter.py` / `projection_output_contract.py`
- ❌ 没改 `regime_diagnostics_dashboard.py`（R4 阈值常量保持原值，
  Step 2G-5 import 即可）
- ❌ 没改任何 builder（`_build_exclusion_system` /
  `_build_confidence_system` / `_build_simulated_trade` / 任何其他）
- ❌ 没升级 04 / 05 / 07 任何 required 字段
- ❌ 没启用 `hard` / `forced_exclusion` / `anti_false_exclusion_triggered`
- ❌ 没接 4 个 anti-false-exclusion 离线模块到主链
- ❌ 没改 `final_projection` / `confidence_score` / `simulated_trade` /
  `no_trade`
- ❌ 没触碰 2026-01-01 之后 final test range
- ❌ 没运行 replay / 没新写 replay 行
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` /
  `avgo_agent.db.backup_*`
- ✅ 只新增 1 份 markdown review checkpoint（本文件）
