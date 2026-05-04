# Step 2G-4 — Soft Metadata Layer Design

> **设计文档，不是实现。** 本文档冻结未来在 04 `exclusion_system.extras`
> 之下新增 `soft_metadata` 子结构的形状、候选信号、严重度分级、去重规则、
> 与 04 / 05 / 07 required 字段的硬隔离边界、以及 dashboard / review 的
> 消费方式。
>
> 本轮**不动任何代码**：不改 `predict.py` / `scanner.py` /
> `prediction_store.py` / `projection_output_adapter.py` /
> `projection_output_contract.py` / 任何 builder / 任何 read-only 工具 /
> DB schema 中的任何一处。

## 1. 背景

- Step 2G 原 hard / soft 设计文档（[`tasks/step_2g_exclusion_soft_hard_design.md`](step_2g_exclusion_soft_hard_design.md)）
  + Step 2G-1 / 2G-2 checkpoint（[`tasks/step_2g_exclusion_soft_hard_checkpoint.md`](step_2g_exclusion_soft_hard_checkpoint.md)）
  已**冻结**，进入 main。
- Step 3D-1 read-only regime diagnostics dashboard（commit `19533ad` /
  checkpoint `c3d8e3e`）就位之后，Step 2G-3 用真实 replay 数据
  (`replay_AVGO_%` = 380 / `paired_outcomes` = 286 /
  `calibration_ready=true`) 完成了对 Step 2G 设计文档 §5 候选映射的
  全面回测验证（[`tasks/step_2g3_exclusion_re_review_checkpoint.md`](step_2g3_exclusion_re_review_checkpoint.md)
  / commit `8e837a7`）。
- 关键再审结论：
  - 旧 `soft_signal` 三类（`peer_weaken` / `high_path_risk` / `none`）
    被数据**反驳** —— `peer_weaken` acc 0.516 > `none` 0.459；
    `high_path_risk` acc 0.564 > `none`；`path_risk=high` acc 反而最高。
    这些信号**不能** hard，**也不应**单独作为 soft exclusion 触发器。
  - **R4** 是新发现的 over-bullish risk metadata 候选：
    `samples=36 / paired=34 / accuracy=0.324 / bias_gap=+0.676`，
    与现有 `soft_signal` 几乎不重叠（94% 落在 `soft_signal=none`）。
  - R4 仍**不能** hard：`false_exclusion_rate=0.3235`（>>0.10）/
    `net_benefit=+0.0219`（<+0.05）/ anti-false-exclusion 4 个保护层
    模块全离线 / 跨窗口 holdout 在 Step 3A-4 / 3B-1 已 FAIL。
- 本文档的范围：把 R4 + 两个相关 over-bullish slice 设计为
  **metadata-only** 的 sidecar 层，**不**进 04 / 05 / 07 required 字段、
  **不**改 `final_projection`、**不**改 `simulated_trade`、**不**启用
  `hard` / `forced_exclusion` / `anti_false_exclusion_triggered`。
- **本文档不是实现。** 没有 commit、没有代码改动、没有 DB 写入、没有
  测试改动。

## 2. 设计目标

| 维度 | 边界 |
|---|---|
| 范围 | metadata-only：仅 spec 化未来 `exclusion_system.extras.soft_metadata` 子结构 |
| 不改 | `final_projection.final_direction` |
| 不改 | `final_projection.final_five_state` |
| 不改 | 04 `exclusion_system` 5 个 required 字段（`exclusion_level=none` / `exclusion_sources=[]` / `exclusion_reasons=[]` / `forced_exclusion=False` / `anti_false_exclusion_triggered=False`） |
| 不改 | 05 `confidence_system` 4 个 score 字段（`historical_score` / `structure_score` / `peer_score` / `exclusion_penalty` 全 0.0；`event_score=None`） |
| 不改 | 05 `confidence_level` / `total_confidence` / `confidence_reason` |
| 不改 | 07 `simulated_trade` 6 个决策字段（`trade_action=no_trade` / `trade_direction=none` / 三个 condition 字段空 / `suggested_position_size=0%`） |
| 不启用 | `hard` exclusion |
| 不启用 | `forced_exclusion=True` |
| 不启用 | `anti_false_exclusion_triggered=True` |
| 不接 | trading API / `longbridge` / `broker` / `paper_trade` |
| 输出消费方 | dashboard / review / future sidecar metadata；**不**影响下游决策路径 |

## 3. 总体结构设计

> 此结构是 **未来** 的 `exclusion_system.extras.soft_metadata` 子 dict
> 形状。本文档**不**实施；本结构**未**进入 contract validator。

```python
exclusion_system.extras.soft_metadata = {
    "signals": [
        {
            "name": "r4_overextension",         # str enum, 见 §4-§6 candidate 列表
            "severity": "medium",                # "low" | "medium"; "high" 保留不用
            "evidence": {
                "avgo_minus_soxx_20d": 7.3,      # 触发当下的实测值
                "pos20": 0.81,
                "final_direction": "偏多",
                "confidence_level": "high",
                "primary_score_raw": 2.7,
            },
            "historical_metrics": {
                "samples": 36,
                "paired": 34,
                "accuracy": 0.324,
                "bias_gap": 0.676,
                "false_exclusion_rate": 0.3235,
                "net_benefit": 0.0219,
            },
            "recommended_action": "review_only",  # "review_only" | "lower_confidence_review"
            "hard_forbidden_reason": "false_exclusion_rate_too_high",
            "hard_forbidden_detail": [
                "false_exclusion_rate=0.3235 exceeds gate ≤0.10",
                "net_benefit=+0.0219 below gate ≥+0.05",
                "anti_false_exclusion_protection_not_connected",
            ],
        },
        # ... up to 3 entries; see §8 dedup rules
    ],
    "summary": {
        "has_overextension_signal": True,
        "max_severity": "medium",
        "hard_exclusion_allowed": False,         # 永远 False（本设计层面）
        "signal_count": 1,
        "primary_signal": "r4_overextension",    # 最高优先级触发的 signal name
    },
}
```

强约束（spec 层面）：

- 这是 `extras` 子 dict 之下的 sidecar；**不**进 04 / 05 / 07 任何
  required 字段。
- 不改变 `exclusion_system.exclusion_level`、`forced_exclusion`、
  `anti_false_exclusion_triggered` —— 三者继续 stub。
- `summary.hard_exclusion_allowed` **永远** `False`；这不是 toggle，
  是 metadata-only spec 的一部分。
- `signals` 列表为空时，整段 `soft_metadata` 仍可省略（不需要 stub）；
  但若实现，建议总是 emit `{signals: [], summary: {has_overextension_signal: False, ...}}`
  以保持下游消费稳定。
- `historical_metrics` 字段是**触发当下**的快照（来自 metadata 计算阶段
  使用的最近 N 条 paired 样本），**不是**实时滑窗 calibration —— 那是
  Step 3 calibration 的工作，本设计不实施。

## 4. Candidate 1: `r4_overextension`

### 4.1 定义

```
avgo_minus_soxx_20d > 5
∧ avgo_pos_20d > 0.62
∧ final_direction == "偏多"
∧ (confidence_level == "high" ∨ primary_score_raw > 2)
```

与 [`services/regime_diagnostics_dashboard.py`](../services/regime_diagnostics_dashboard.py)
的 `_is_r4_record` 完全一致；与 Step 3B regime-aware 设计 + Step 3D-1
dashboard frozen 的 R4 阈值一致（`_R4_AVGO_MINUS_SOXX_THRESHOLD = 5.0`、
`_R4_POS20_THRESHOLD = 0.62`）。

### 4.2 证据（main DB / 380 replay）

| 指标 | 值 |
|---|---|
| `samples` | 36 |
| `paired` | 34 |
| `accuracy` | **0.324** |
| `bias_gap` | **+0.676** |
| `predicted_bullish_rate` | 1.0 |
| `actual_up_rate` | 0.324 |
| `false_exclusion_rate`（反事实 hard） | **0.3235** |
| `net_benefit`（反事实 hard） | **+0.0219** |
| `downgrade_candidate_count` | 22 |

### 4.3 设计

| 字段 | 值 |
|---|---|
| `name` | `"r4_overextension"` |
| `severity` | `"medium"`（acc < 0.40 且 bias_gap > 0.50；§9 自动归档） |
| `recommended_action` | `"review_only"` 或 `"lower_confidence_review"` |
| `hard_forbidden_reason` | `"false_exclusion_rate_too_high"` |
| `hard_forbidden_detail` | 三条独立理由（见 §3 示例 dict）：`false_exclusion_rate > 0.10` / `net_benefit < +0.05` / `anti_false_exclusion_protection_not_connected` |

## 5. Candidate 2: `bullish_high_pos20`

### 5.1 定义

```
final_direction == "偏多"
∧ confidence_level == "high"
∧ avgo_pos_20d > 0.62
```

### 5.2 证据（main DB / 380 replay）

| 指标 | 值 |
|---|---|
| `samples` | 81 |
| `paired` | 79 |
| `accuracy` | **0.418** |
| `bias_gap` | **+0.582** |
| `predicted_bullish_rate` | 1.0 |
| `actual_up_rate` | 0.418 |

### 5.3 设计

- 这是 R4 的**更宽超集**（去掉了 `avgo_minus_soxx_20d > 5` 与
  `primary_score_raw > 2` 的 OR 分支，仍要求 high confidence + pos20 高位）。
- 用于提示**高位偏多 + 高置信**这一普遍 over-bullish 上下文。
- `recommended_action`：`review_only`
- `severity`：`low_to_medium`（实操按 §9 归档：acc 在 0.40-0.50 / bias_gap
  > 0.50 → `medium`；否则 `low`。81 paired / 0.418 / +0.582 → `medium`，
  但样本量大、定义宽，按 §8 优先级在 R4 触发时被覆盖）
- 与 R4 **去重**：见 §8。

## 6. Candidate 3: `bullish_peer_upgrade_overextension`

### 6.1 定义

```
final_direction == "偏多"
∧ peer_adjustment == "upgrade"
∧ avgo_pos_20d > 0.62
```

### 6.2 证据（main DB / 380 replay；最相关子切片）

| 切片 | samples | paired | accuracy | bias_gap |
|---|---|---|---|---|
| `bullish × peer_upgrade × pos20>0.62` | （独立计算，需 sidecar simulator） | — | — | — |
| `R4 × peer_upgrade`（最尖锐子切片） | 26 | **24** | **0.250** | **+0.750** |
| `peer_adjustment=upgrade`（整体） | 132 | 120 | 0.450 | +0.200 |

### 6.3 设计

- `R4 × peer_upgrade` 子切片 paired = 24 < 30，**不达** Step 2G 设计文档
  §7 的触发组阈值 —— 因此**不能**单独作为 hard 触发器。
- 但 R4 中 24/26 都是 peer_upgrade，说明"peer 反而 reinforce 偏多 +
  高位强动量"是 R4 内部最尖锐的失败模式 —— 值得作为 metadata 显示，
  辅助 review 归因。
- `recommended_action`：`review_only`
- `severity`：仅当与 R4 同时触发时归档为 `medium`；单独触发时归档
  `low`（参照 §9）。
- `hard_forbidden_reason`：
  - `paired_count_below_30`（最尖锐子切片样本不达阈值）
  - `no_anti_false_exclusion_protection`
  - `false_exclusion_rate_too_high`（继承 R4 的反事实结论）

## 7. Metadata-only signals

下列信号**仅**作为 `metadata_only`，不进入 `signals` 列表的"触发条目"，
而是作为 dashboard / review **辅助上下文**展示（设计层面：可在 `evidence`
之下平铺 raw 字段，或单独作为 `context` 子 dict —— 实施时再定）。

| name | 触发条件 | 历史指标 | 为什么只能 metadata_only |
|---|---|---|---|
| `peer_weaken_metadata_only` | `soft_signal == "peer_weaken"` | 84 / 64 / acc **0.516** / gap **+0.328** | accuracy **高于** baseline (0.486) 与 `none` (0.459) —— 它**不是**"系统更容易错"的信号；只在偏多子切片有 bias 修正价值（51 paired / acc 0.49 / gap +0.51） |
| `high_path_risk_metadata_only` | `soft_signal == "high_path_risk"`（或 `path_risk_level == "high"`） | 99 / 39 / acc **0.564** / gap +0.128 | accuracy 反而是三档中最高；hard 会让 net_benefit 转负 |
| `peer_path_lower_bullish` | `final_direction == "偏多" ∧ peer_path_risk_direction == "lower"` | （子集，需 sidecar 算）；lower 整体 120 paired / acc 0.45 / gap +0.20 | gap +0.20 不足以支撑硬决策；与 R4 / peer_upgrade 重叠未做正交分析 |
| `conflicting_factors_count_alias_note` | `cf_count == 2` | 84 / 64 / acc 0.516 / gap +0.328 | 与 `peer_weaken` **几乎完全 alias**（同样 84/64/0.516/+0.328），**不是**独立信号；仅作为 metadata 标注 |

实施层面提议（设计层面**不**冻结具体形状，留给 Step 2G-5 simulator
spec）：可以在 `soft_metadata.context` 子 dict 暴露这几个 raw 字段，
或者完全不在 `soft_metadata` 里出现 —— `extras` 同级已有
`soft_signal` / `path_risk_level` / `peer_path_risk_direction` /
`conflicting_factors_count`，本文档**不**复制这些 raw 字段。

## 8. Dedup / priority

### 8.1 候选优先级（高 → 低）

1. `r4_overextension`（最强 over-bullish 信号；独立于现有 `soft_signal`）
2. `bullish_peer_upgrade_overextension`（R4 内部最尖锐子切片；样本 < 30）
3. `bullish_high_pos20`（R4 的更宽超集；样本量大、gap 仍高）
4. `peer_weaken_metadata_only`（仅 metadata，§7）
5. `high_path_risk_metadata_only`（仅 metadata，§7）

### 8.2 去重规则

- **R4 触发 → 不再单独显示 `bullish_high_pos20`**：R4 是 `bullish_high_pos20`
  的真子集（前者多了 `avgo_minus_soxx_20d > 5` + `(high ∨ psr>2)` 的约束）。
  R4 触发已包含 high pos20 + bullish 的所有 metadata 价值。
- **R4 触发 + peer_adjustment=upgrade → `bullish_peer_upgrade_overextension`
  作为 R4 的 evidence 子项合并**：不重复 emit 一条 signal；在 R4 entry 的
  `evidence` 之下添加 `peer_adjustment_subtype: "upgrade"`，并把
  `R4 × peer_upgrade` 的历史指标合并进 R4 的 `historical_metrics`
  子结构（如另一字段 `subslice_metrics`）。
- **`bullish_peer_upgrade_overextension` 单独触发**（即 final_direction=偏多
  ∧ peer_upgrade ∧ pos20>0.62 但**未**满足 R4 的 SOXX 差或 high conf 条件）：
  作为独立 entry 显示，severity = `low`。
- **`bullish_high_pos20` 单独触发**（R4 不触发、上一条也不触发）：作为
  独立 entry 显示，severity 按 §9 归档。
- **`peer_weaken_metadata_only` / `high_path_risk_metadata_only`**：**不**
  进入 `signals` 列表（按 §7，仅作 dashboard 辅助上下文）。

### 8.3 输出上限

- `signals` 列表**最多 3 条**。原因：避免 dashboard / review UI 噪声，
  让消费者一眼看到最重要的 over-bullish 风险，而不是被 5+ 条 alias
  信号淹没。
- 优先级裁剪规则：按 §8.1 顺序选前 3 条；超出的丢弃（**不**显示
  "more"提示，避免诱导消费者去找额外信号）。

### 8.4 全局 invariants

- `summary.hard_exclusion_allowed` **永远** `False`。
- 若所有候选都未触发：`signals=[]`、`summary.has_overextension_signal=False`、
  `summary.max_severity` 取 `"none"`（或省略字段）；`signal_count=0`、
  `primary_signal=None`。

## 9. Severity 设计

### 9.1 等级定义

| severity | 数据条件 | 当前 candidate |
|---|---|---|
| `"low"` | 仅 metadata 价值；无明显 accuracy 风险（acc ≥ 0.45 且 bias_gap ≤ 0.50） | `peer_weaken_metadata_only` / `high_path_risk_metadata_only` / `bullish_peer_upgrade_overextension`（单独触发时） |
| `"medium"` | acc < 0.40 **或** bias_gap > 0.50；但**未**达 hard gate（`false_exclusion_rate ≤ 0.10` + `net_benefit ≥ +0.05`） | **`r4_overextension`**（acc 0.324 / gap 0.676 → medium）；`bullish_high_pos20`（acc 0.418 / gap 0.582 → medium）；`bullish_peer_upgrade_overextension`（与 R4 同时触发时） |
| `"high"` | **保留不用** —— 任何 high severity 仍**不等于** hard | （无） |
| `"hard"` | **当前禁止** —— 无任何 candidate；§10 / §11 永久限制 | （无） |

### 9.2 关键约束

- `severity = "high"` 与 `severity = "hard"` **不是** spec 的逐步升级路径 ——
  即使一个 candidate 表现极差，也不能跳过 §10 的 hard gate 升级到 hard。
- `severity` 是 metadata 的描述维度，**不是**决策维度；`recommended_action`
  才是消费者参考的字段，且永远在 `review_only` / `lower_confidence_review`
  两个值之间，**不**包含 `exclude` / `force_exclude` / `block_trade`。
- 当 candidate 的实测 historical metrics 改变时（例如 paired 增长后 R4
  acc 上升到 0.45），severity 需要按 §9.1 的阈值重新归档。Step 2G-5
  simulator 应在每次实跑时刷新 severity，不写死。

## 10. 与 04 required 字段关系

| 字段 | 当前 | 本文档允许变化 |
|---|---|---|
| `exclusion_system.exclusion_level` | `"none"` | ❌ **不**允许升级 |
| `exclusion_system.exclusion_sources` | `[]` | ❌ **不**允许 |
| `exclusion_system.exclusion_reasons` | `[]` | ❌ **不**允许 |
| `exclusion_system.forced_exclusion` | `False` | ❌ **不**允许（与 hard 联动；hard 都没启用） |
| `exclusion_system.anti_false_exclusion_triggered` | `False` | ❌ **不**允许 |
| `exclusion_system.extras.soft_metadata`（**新**） | （不存在） | ✅ 允许在 Step 2G-5+ simulator 实施时新增；本文档**只是**spec |

强约束：

- `soft_metadata` **只**允许进入 `extras` 子 dict —— `extras` 是
  Step 2C-2 已建立的"informational only"语义层，与 04 required
  字段硬隔离。
- 任何 04 required 字段升级（`exclusion_level → soft / hard` /
  `forced_exclusion → True` / `anti_false_exclusion_triggered → True`）
  必须**另立 Step 2G-8+**，且前提是：
  1. Step 2G 设计文档 §8 hard gate **全部通过**（false_exclusion_rate
     ≤ 0.10 + net_benefit ≥ +0.05 + 跨窗口 holdout 通过）
  2. anti-false-exclusion 4 个保护层至少接入 1 个（Step 2G-7+ 设计）
  3. Step 3 calibration 重启的 holdout 评估通过（**当前 FAIL**）

## 11. 与 07 simulated_trade 关系

- `simulated_trade.trade_action` 继续 **`"no_trade"`**。
- `simulated_trade.trade_direction` 继续 **`"none"`**。
- `simulated_trade.entry_condition` / `stop_loss_condition` /
  `take_profit_condition` 继续空字符串。
- `simulated_trade.suggested_position_size` 继续 **`"0%"`**。
- `simulated_trade.no_trade_reason` 继续静态文案（与 Step 2D-2 一致）。
- `simulated_trade.extras.trade_engine_enabled` 继续 **`False`**。

强约束：

- soft metadata **不构成**交易指令。
- soft metadata **不影响** position sizing。
- soft metadata **不接** broker / paper_trade / `longbridge` /
  trading API。
- 07 段策略边界与 exclusion / metadata 等级**永久正交**（与 Step 2D
  设计一致）。

## 12. 与 dashboard / review 的关系

### 12.1 dashboard 允许显示

- `signals[i].name` —— 触发的 metadata 信号名
- `signals[i].severity` —— `"low"` / `"medium"`
- `signals[i].evidence` —— 触发当下的 raw feature 值
- `signals[i].historical_metrics` —— samples / paired / accuracy /
  bias_gap / false_exclusion_rate / net_benefit
- `signals[i].recommended_action` —— `"review_only"` /
  `"lower_confidence_review"`
- `signals[i].hard_forbidden_reason` + `hard_forbidden_detail` ——
  让用户看到"这条 metadata **不是** hard exclusion，**不**应被解读为
  禁止交易"
- `summary.has_overextension_signal` / `max_severity` /
  `hard_exclusion_allowed`（**始终** `False`）/ `primary_signal`

### 12.2 dashboard 文案约束（强烈建议）

- **不**写"禁止交易" / "强制否定" / "block" / "exclude"
- **建议**写"高位偏多过度风险，建议复核" /
  "AVGO 强动量 + 高位 + 高置信，历史命中率 32%，请复核" 等**事实陈述**
  + **建议复核**的措辞
- 文案需明确 `hard_exclusion_allowed=false`，避免被误读为 hard signal

### 12.3 review 允许使用

- 把 `signals` 当作**失败归因**的候选维度（"这次 review 的 prediction
  在 R4 触发的历史样本里命中 32%，请检查"）
- 可以把 metadata 写入 review 的 `confidence_note` / `watch_for_next_time`
  字段（这两个字段是 free text，不影响 contract required）
- **不**应让 review 的 `error_category` 直接绑定到 metadata signal name
  ——前者是 review 的语义分类，后者是触发条件，二者不同维度

## 13. Future implementation path

| 步骤 | 范围 | commit 期望 |
|---|---|---|
| **Step 2G-4** | 本设计文档 | 1 个 markdown |
| **Step 2G-5** | Read-only sidecar simulator：新增 `services/soft_metadata_simulator.py` + CLI + tests；**不**改 04 / 05 / 07 / contract validator / DB schema；**不**改任何 builder；**不**改 `_build_exclusion_system`。CLI 输出 `soft_metadata` 子结构 JSON 供 dashboard / review 消费 | 1 个 service / 1 个 CLI / 1 个 test 文件 |
| **Step 2G-6** | Dashboard / review 显示层接入：把 simulator 的输出按 §12 文案约束渲染 | UI 改动 |
| **Step 2G-7** | Anti-false-exclusion 保护层接入设计：从 4 个候选模块（`anti_false_exclusion_audit` / `big_up_contradiction_card` / `big_down_tail_warning` / `exclusion_reliability_review`）挑一个写接入方案；**仍是**设计文档 | 1 个 markdown |
| **Step 2G-8+** | **只有**通过 Step 2G 设计文档 §8 hard gate（**当前任何候选都不通过**）才能讨论 04 required 字段升级 | （前提不满足时不启动） |

强约束：

- Step 2G-5 simulator **必须** read-only：`SELECT` only / 不调用
  `init_db` / 不写文件 / 不接网络 / 不接 trading。
- Step 2G-5 simulator **不**改 contract required 字段 —— 它的输出**只**
  作为 sidecar JSON，由 dashboard / review 消费。
- Step 2G-6 dashboard 接入**不**改 `_build_exclusion_system`、**不**改
  `_build_simulated_trade`、**不**改 `_build_confidence_system`。
- Step 2G-7 保护层接入**仍是**设计文档；具体实施延后到 Step 2G-8+
  且前提是 Step 2G 设计文档 §8 hard gate 通过。
- Step 2G-8+ 之前任何"试着启用 hard / 试着启用 forced"的尝试都属于
  **违反 Step 2G 设计文档 §6 红线** —— 不能凭直觉启用。

## 14. 不做什么

- ❌ 不实现（本文档是 spec，不是代码）
- ❌ 不写代码（不改 `predict.py` / `scanner.py` / `prediction_store.py` /
  adapter / validator / 任何 builder / 任何 read-only 工具）
- ❌ 不改 DB schema（不调用 `init_db` / 不 `ALTER` / 不 `INSERT`）
- ❌ 不升级 04 `exclusion_system` 5 个 required 字段
- ❌ 不升级 05 `confidence_system` 4 个 score 字段
- ❌ 不升级 05 `event_score`（保持 `None`）
- ❌ 不升级 07 `simulated_trade` 6 个决策字段
- ❌ 不启用 `hard` exclusion
- ❌ 不启用 `forced_exclusion=True`
- ❌ 不启用 `anti_false_exclusion_triggered=True`
- ❌ 不接 4 个离线 anti-false-exclusion 模块到主链
- ❌ 不改 `final_projection`（`final_direction` / `final_five_state` /
  `final_open_projection` / `final_intraday_path` /
  `final_close_projection` / `probability_bucket` / `key_price_levels` /
  `final_one_sentence`）
- ❌ 不改 `confidence_score` / `confidence_level` /
  `total_confidence` / `confidence_reason`
- ❌ 不改 `simulated_trade` / `no_trade` 策略边界
- ❌ 不接 `yfinance` / `requests` / 网络
- ❌ 不接 trading API / `longbridge` / `broker` / `paper_trade`
- ❌ 不用 2026-01-01 之后 final test range 调参
- ❌ 不新增任何测试

## 15. 成功标准

未来若实施 Step 2G-5 simulator + Step 2G-6 dashboard，应满足：

| # | 标准 |
|---|---|
| 1 | metadata coverage 可解释：每条触发的 signal 都能列出 evidence + historical_metrics + hard_forbidden_reason |
| 2 | R4 历史指标在 simulator 输出里**可复现**（与 [`services/regime_diagnostics_dashboard.py`](../services/regime_diagnostics_dashboard.py) 的 R4 数值一致：samples=36 / paired=34 / accuracy=0.324 / bias_gap=+0.676，前提是同 DB / 同 limit） |
| 3 | `false_exclusion_rate` 与 `net_benefit` 明确展示在每条 signal 的 `hard_forbidden_detail` 里 |
| 4 | `summary.hard_exclusion_allowed` 始终 `False`；任何 simulator 输出违反此约束的版本视为**实施 bug** |
| 5 | dashboard 文案不误导成 hard signal（参照 §12.2）—— 用户调研 / review 反馈不出现"以为这是禁止交易信号"的反馈 |
| 6 | 04 / 05 / 07 required 字段不变 —— 现有 `tests/test_exclusion_system_contract_fields.py` / `tests/test_confidence_system_contract_fields.py` / `tests/test_simulated_trade_contract_fields.py` 测试基线不变（2254 / 0 failed / 10 skipped） |
| 7 | 任何 simulator / dashboard 改动**不**触发 contract validator 报错 —— `extras.soft_metadata` 是新增 informational 字段，validator 对 `extras` 内部不做强 schema 校验（保持 Step 2C-2 / 2C-3b / 2D-2 已建立的 informational 语义） |
| 8 | dashboard tab / review pane 在没有 metadata 触发时**不**显示空"无信号"提示（避免误读为系统出错） |

## 16. 严守边界

- ❌ 本文档**只是**设计 / spec
- ❌ 没改任何代码
- ❌ 没新增任何测试
- ❌ 没写 DB
- ❌ 没改 DB schema
- ❌ 没接 `yfinance` / `requests` / 任何网络
- ❌ 没接 trading API / `longbridge` / `broker` / `paper_trade`
- ❌ 没改 `predict.py` / `scanner.py` / `prediction_store.py`
- ❌ 没改 `projection_output_adapter.py` / `projection_output_contract.py`
- ❌ 没改任何 builder（`_build_exclusion_system` / `_build_confidence_system` /
  `_build_simulated_trade` / 任何其他）
- ❌ 没升级 04 / 05 / 07 任何 required 字段
- ❌ 没启用 `hard` / `forced_exclusion` / `anti_false_exclusion_triggered`
- ❌ 没接 4 个 anti-false-exclusion 离线模块到主链
- ❌ 没改 `final_projection` / `confidence_score` / `simulated_trade` / `no_trade`
- ❌ 没触碰 2026-01-01 之后 final test range
- ❌ 没运行 replay / 没新写 replay 行
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` /
  `avgo_agent.db.backup_*`
- ✅ 只新增 1 份 markdown 设计文档（本文件）
