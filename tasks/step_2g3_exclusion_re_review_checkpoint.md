# Step 2G-3 — Soft / Hard Exclusion Re-Review Checkpoint

## 1. 当前完成状态

- Step 2G 原始设计文档（[`tasks/step_2g_exclusion_soft_hard_design.md`](step_2g_exclusion_soft_hard_design.md)）和
  Step 2G-1 / 2G-2 checkpoint（[`tasks/step_2g_exclusion_soft_hard_checkpoint.md`](step_2g_exclusion_soft_hard_checkpoint.md)）
  已**冻结**，进入 main。
- Step 3D-1 read-only regime diagnostics dashboard 已**完成**并进入 main
  （commit `19533ad` / checkpoint commit `c3d8e3e`）。
- Step 2G-3 在 Step 3D-1 工具就位之后做的第一件事 —— 用真实 replay 数据
  （`replay_AVGO_%` = 380）+ regime dashboard + 三个 read-only CLI
  + 一次只读 sqlite cross-tab 把 Step 2G 设计文档 §5 候选映射的每条规则
  做真实回测验证；本 checkpoint **冻结这次 re-review 的数据结论**。
- 本 checkpoint 是**纯文档**，没有任何 commit、没有任何代码改动、没有任何
  DB 写入。

## 2. 当前数据基线

来自 [`scripts/regime_diagnostics_dashboard.py`](../scripts/regime_diagnostics_dashboard.py)
+ [`scripts/summarize_confidence_calibration_inputs.py`](../scripts/summarize_confidence_calibration_inputs.py)
+ [`scripts/correlate_contract_outcomes.py`](../scripts/correlate_contract_outcomes.py)
+ [`scripts/dashboard_contract_extras.py`](../scripts/dashboard_contract_extras.py)
联合实跑（main DB / `avgo_agent.db`）：

| 维度 | 值 |
|---|---|
| `replay_AVGO_%` 行数 | **380** |
| `paired_outcomes`（有 `direction_correct ∈ {0,1}` 的 outcome） | **286** |
| `pending_outcomes` | 94 |
| `calibration_ready`（≥ 90 paired 阈值） | **true** |
| `time_range` | 2023-01-03 → 2024-08-02 |
| Baseline `accuracy`（全 286 paired） | **0.486** |
| Baseline `predicted_bullish_rate` | **0.671** |
| Baseline `actual_up_rate` | **0.514** |
| Baseline `bias_gap` (= pbull − aup) | **+0.157** |

**整体 baseline 已经有 +0.157 的偏多 bias** —— 这是后续所有 slice 的对照线。

## 3. 原始 Step 2G 约束复核

| 约束 | 内容 |
|---|---|
| `none` 语义 | 默认信任主推演；缺数据时仍 `none`（不用 `unknown` 代替） |
| `soft` 语义 | 有可观察信号但**不否定方向**；UI 可加 warning；**不**改 `final_projection`；**不**改 `simulated_trade` |
| `hard` 语义 | 有 backtest 支撑；下游可选忽略 `final_direction`；07 段仍 `no_trade` |
| hard 必备指标 | `false_exclusion_rate ≤ 0.10` + `net_benefit ≥ +0.05` + 不系统性误杀 big-up / 独立行情 |
| 数据需求 | 总 paired ≥ 90 + 触发组 ≥ 30 + 对照组 ≥ 30 |
| `forced_exclusion=True` | **仅允许** `level=hard`；用于系统级拦截（数据破坏 / contract 破坏 / 已知 bug / 已验证灾难信号），**不**用于策略风险 |
| `anti_false_exclusion_triggered` | hard 决策的复核标记；候选数据来源 `anti_false_exclusion_audit` / `big_up_contradiction_card` / `big_down_tail_warning` / `exclusion_reliability_review` |
| 当前阶段 | `forced_exclusion=True` **全部禁止**；anti-false-exclusion 四个模块**全部未接主链** |
| §6 红线 | 任何**单一** extras 字段（`peer_weaken` / `high_path_risk` / `path_risk=high` / `cf_count≥N` / `confidence_low` / `primary_score_raw` / 任何 `simulated_trade.extras`）**永远不能**直接 hard；hard 必须复合证据 + backtest |
| 07 段策略边界 | `simulated_trade` 任何字段不能作为 exclusion 决策依据；`trade_action=no_trade` 与 exclusion 等级永久正交 |

## 4. 工具输出摘要

### 4.1 `regime_diagnostics_dashboard.py --symbol AVGO --limit 450`

| 指标 | 值 |
|---|---|
| pos20 Q1 (`<= 0.4275`) `bias_gap` | **−0.36** |
| pos20 Q4 (`> 0.8198`) `bias_gap` | **+0.51** |
| R4 `samples` / `accuracy` / `bias_gap` | 36 / **32.4%** / **+0.68** |
| R4 `downgrade_candidate_count` | 22 |

### 4.2 `dashboard_contract_extras.py --limit 450 --symbol AVGO`

| 字段 | 分布 |
|---|---|
| `exclusion_system.extras.soft_signal` | none=197 / peer_weaken=84 / high_path_risk=99 |
| `exclusion_system.extras.path_risk_level` | low=135 / medium=87 / **high=158** |
| `exclusion_system.extras.peer_path_risk_direction` | lower=132 / unchanged=117 / higher=131 |
| `exclusion_system.extras.conflicting_factors_count` | 0=190 / 1=106 / 2=84 |
| `simulated_trade.extras.final_direction` | 偏多=200 / 中性=78 / 偏空=102 |

### 4.3 `correlate_contract_outcomes.py --symbol AVGO --limit 450`

| 分组 | acc |
|---|---|
| `final_direction=偏多` | **50.0%**（200 samples） |
| `final_direction=偏空` | 45.7%（102 samples） |
| `confidence_level=high` | **44.7%**（153 samples） |
| `confidence_level=medium` | 52.4% |
| `confidence_level=low` | 52.5% |

`confidence_level=high` 的命中率**反而最低** —— 这是后续所有 slice 解读
的关键背景。

### 4.4 `summarize_confidence_calibration_inputs.py --limit 450 --symbol AVGO`

- `paired_outcomes = 286 ≥ 90`；`calibration_ready = true`；
  `data_gap_report.missing_dimensions = []`
- `primary_score_raw` 范围 `[−4.25, +4.25]`；mean = **+0.59**（也是
  baseline 偏多 bias 的另一种表达）

## 5. soft_signal deep-dive

| key | samples | paired | acc | pbull | actual_up | bias_gap |
|---|---|---|---|---|---|---|
| `none` | 197 | 183 | **0.459** | 0.661 | 0.557 | +0.104 |
| `peer_weaken` | 84 | 64 | **0.516** | **0.797** | 0.469 | **+0.328** |
| `high_path_risk` | 99 | 39 | **0.564** | 0.513 | 0.385 | +0.128 |

**结论（颠覆原设计假设）**：

- `soft_signal=peer_weaken` 的 paired accuracy **51.6%**，比 `none`
  的 **45.9%** **更高** —— 它**不是**"系统更容易错"的信号。
- `soft_signal=high_path_risk` 同样 acc **56.4%** > none，**不是**
  "系统更容易错"的信号。
- 把任何 `soft_signal != none` 直接当 hard exclusion，**会损失精度**：
  `net_benefit` 转负，违反 §8 `net_benefit ≥ +0.05` 红线。
- `soft_signal != none` **不能**作为 hard exclusion；`soft_signal != none`
  也**不应**直接作为"否定方向"的 soft exclusion。
- 真正的信号价值是：`peer_weaken` 切片里**偏多调用过度膨胀**
  （pbull 0.797 vs aup 0.469，gap **+0.328**）—— 即"这条预测被判偏多
  时，要更怀疑"。这是**bias 修正**，不是"是否 exclude"。

## 6. path / peer risk deep-dive

### 6.1 `path_risk_level`

| level | paired | acc | bias_gap |
|---|---|---|---|
| `low` | 124 | 0.468 | +0.194 |
| `medium` | 84 | 0.476 | +0.024 |
| `high` | 78 | **0.526** | +0.244 |

`path_risk=high` 的 acc 反而最高。"path_risk=high 应该 exclude" 的直觉
**不被数据支持**。

### 6.2 `peer_path_risk_direction`

| dir | paired | acc | bias_gap |
|---|---|---|---|
| `lower` (peer 弱于 AVGO) | 120 | **0.450** | **+0.200** |
| `unchanged` | 57 | **0.561** | −0.053 |
| `higher` | 109 | 0.486 | +0.220 |

`lower` 是最差切片，但 acc 0.45 比 baseline 0.486 只低 3.6 pp，
gap +0.20 也只比 baseline +0.157 多 4.3 pp —— **差距不够**支撑 hard。

### 6.3 `conflicting_factors_count`

| count | paired | acc | bias_gap |
|---|---|---|---|
| 0 | 177 | 0.486 | +0.119 |
| 1 | 45 | 0.444 | +0.067 |
| 2 | **64** | **0.516** | **+0.328** |

注意：`cf_count=2` 与 `soft_signal=peer_weaken` **几乎完全 alias**
（同样 84 samples / 64 paired / 0.516 acc / +0.328 gap）—— 它不是独立
信号，只是 `peer_weaken` 的另一种表达。

### 6.4 结论

- 这三类信号（path_risk_level / peer_path_risk_direction /
  conflicting_factors_count）**只能继续保留为 diagnostics / metadata**；
  **不能** hard，**也不应**单独作为 soft exclusion 触发器。
- 它们的位置仍然是 `extras` 子 dict，不上升到 04 required 字段。

## 7. R4 deep-dive

R4 condition（与 Step 3B regime-aware 设计 + Step 3D-1 dashboard 一致）：

- `avgo_minus_soxx_20d > 5`（pp）
- `avgo_pos_20d > 0.62`
- `final_direction == "偏多"`
- `confidence_level == "high"` 或 `primary_score_raw > 2`

R4 主表（36 universe / 34 paired）：

| 切分 | samples | paired | acc | pbull | actual_up | bias_gap |
|---|---|---|---|---|---|---|
| R4 (整体) | 36 | 34 | **0.324** | 1.000 | 0.324 | **+0.676** |
| R4 × `confidence_high` | 34 | 32 | 0.312 | 1.000 | 0.312 | +0.688 |
| R4 × `peer_adjustment=upgrade` | 26 | **24** | **0.250** | 1.000 | 0.250 | **+0.750** |
| R4 × `peer_adjustment=hold` | 8 | 8 | 0.500 | 1.000 | 0.500 | +0.500 |
| R4 × `peer_adjustment=downgrade` | 2 | 2 | 0.500 | 1.000 | 0.500 | +0.500 |
| R4 × `peer_path=lower` | 26 | 24 | **0.250** | 1.000 | 0.250 | +0.750 |
| R4 × `es_soft_signal=none` | 34 | 32 | 0.312 | 1.000 | 0.312 | +0.688 |
| R4 × `es_soft_signal=peer_weaken` | 2 | 2 | 0.500 | 1.000 | 0.500 | +0.500 |

解释：
- R4 中 **94%** 的样本（34/36）`soft_signal=none`，与现有 soft_signal
  几乎不重叠 —— **R4 是一条独立的 over-bullish risk metadata 候选**，
  不能用现有 soft_signal 表达。
- R4 × `peer_adjustment=upgrade`（24 paired，acc 25%，gap +0.75）
  是 R4 内部最尖锐的子切片：peer 反而 upgrade 时 R4 失败概率最高
  —— peer reinforce 在高位强动量场景下**不是**信心来源，而是过度膨胀
  的标志。
- R4 paired=34 略过 §7 的 ≥30 触发样本阈值，但仍属于"小样本统计区"；
  跨窗口 holdout 已在 Step 3A-4 / 3B-1 上 FAIL，不能假设 OOS 稳定。

## 8. hard exclusion 反事实

如果**直接** hard-exclude 所有 R4 样本：

```
baseline (all 380):       paired = 286 / acc = 0.4860
if R4 hard-excluded:      paired = 252 / acc = 0.5079
R4 itself contains:       paired =  34 / correct = 11 (32.4%)
→ false_exclusion_rate = 11 / 34 = 0.3235     (gate ≤ 0.10)  ❌
→ net_benefit          = +0.0219              (gate ≥ +0.05) ❌
```

| 指标 | 计算 | 阈值 | 通过 |
|---|---|---|---|
| `false_exclusion_rate` | 11 correct / 34 paired = **0.3235** | ≤ 0.10 | ❌（超阈值 3.2 倍） |
| `net_benefit` | 0.5079 − 0.4860 = **+0.0219** | ≥ +0.05 | ❌（不到一半） |

更尖锐的子切片 R4 × `peer_adjustment=upgrade`（acc 0.25 / gap +0.75）
理论上 false_exclusion_rate 更低（6/24 = 0.25），但仍远超 0.10；
**且 paired = 24 < 30 阈值**，自身就不满足 §7 触发样本要求。

**R4 不能 hard。** 既不满足 false_exclusion_rate 上限、也不满足
net_benefit 下限、也没有 anti-false-exclusion 保护层。

## 9. soft metadata candidates（设计候选；本轮不实现）

| # | candidate | condition | evidence | recommended | why not hard |
|---|---|---|---|---|---|
| 1 | `r4_overextension` | `avgo_minus_soxx_20d > 5 ∧ pos20 > 0.62 ∧ final_direction=偏多 ∧ (confidence=high ∨ primary_score_raw > 2)` | 36 / 34 / acc **0.324** / gap **+0.676** | **soft_candidate**（独立于现有 soft_signal；最强 over-bullish 信号） | `false_exclusion_rate=0.3235`，远超 0.10；扔掉 R4 同时损失 11 个 correct |
| 2 | `bullish_high_pos20` | `final_direction=偏多 ∧ confidence=high ∧ pos20 > 0.62` | 81 / 79 / acc **0.418** / gap **+0.582** | **soft_candidate**（R4 的更宽超集；样本量大、gap 仍高） | high confidence 切片 acc 反而最低，hard 等于直接禁用 high confidence；同样不达 §8 指标 |
| 3 | `bullish_peer_upgrade_overextension` | `final_direction=偏多 ∧ peer_adjustment=upgrade ∧ pos20 > 0.62` | R4 × peer_upgrade=**24** paired / acc **0.25** / gap **+0.75**（更宽超集需独立计算） | **soft_candidate / needs more evidence**（peer reinforce 在高位反向价值最高） | paired < 30 阈值；anti-false-exclusion 保护层未接 |
| 4 | `peer_path_lower_bullish` | `final_direction=偏多 ∧ peer_path_risk_direction=lower` | 子集（lower 整体 120 paired / acc 0.45 / gap +0.20） | **metadata_only** | gap +0.20 不足以承担硬决策；与 R4 / peer_upgrade 重叠未做正交分析 |
| 5 | `peer_weaken_metadata_only` | `soft_signal=peer_weaken`（保持现状） | 84 / 64 / acc **0.516** / gap +0.328 | **metadata_only**（accuracy 比 baseline 还高；只在偏多子切片有 bias 价值：51 paired / acc 0.49 / gap +0.51） | accuracy 反向；hard 会让 net_benefit 转负；§6 红线 |

**所有 5 个候选都不能 hard。** 1 / 2 / 3 三条可以进入 Step 2G-4 的
"soft metadata layer design" 文档；4 / 5 两条仅作 dashboard 上的显示
metadata，不进任何决策路径。

## 10. hard exclusion gate check

| 检查项 | 当前 | 通过 |
|---|---|---|
| 总 (contract × outcome) pair ≥ 90 | 286 | ✅ |
| 至少一个候选触发样本 ≥ 30 | R4=34 / pos20×high=79 | ✅ |
| 至少一个候选 `false_exclusion_rate ≤ 0.10` | 最低 R4=**0.32** | ❌ |
| 至少一个候选 `net_benefit ≥ +0.05` | 最高 R4=**+0.022** | ❌ |
| `anti_false_exclusion` 至少一个模块接主链 | 0 / 4 | ❌ |
| 跨窗口 holdout 通过 | Step 3A-4 third-window FAIL；Step 3B-1 lookup FAIL | ❌ |
| `forced_exclusion=True` 是否可启用 | 否（hard 都没启用，forced 没有落地基础） | ✅（保持禁止） |
| 04 `required` 字段是否可升级 | 否（任何升级都会污染 04 段必要字段） | ✅（保持 stub） |

**结论**：6 项硬性前提中**有 4 项不通过**，且
`false_exclusion_rate` / `net_benefit` 任何候选都达不到。
**hard 仍然不能启用。**

## 11. 设计结论

可以**进入** soft metadata design（Step 2G-4 候选；本轮不实施）：
- ✅ 只设计 metadata，**不**改 04 required 字段
- ✅ R4 (`r4_overextension`) 是第一候选
- ✅ `bullish_high_pos20` 是 R4 的更宽超集，第二候选
- ✅ `bullish_peer_upgrade_overextension` 是第三候选（需更多证据）
- ❌ 即使是 soft metadata，也**不**改 `final_projection`、**不**改
  `simulated_trade`、**不**改 `confidence_system` 4 个 score 字段
- ❌ metadata 只暴露在 `extras` 子 dict / dashboard / review 提示，
  不影响下游决策

被数据**反驳**、不适合作为 exclusion 决策依据：
- `soft_signal=peer_weaken`（acc **高于** none）
- `soft_signal=high_path_risk`（acc **高于** none）
- `path_risk=high`（acc **高于** low / medium）
- `peer_path_risk_direction=lower`（gap 不够大）
- `conflicting_factors_count` 单独使用（与 peer_weaken alias）
- 任何**单一** extras 字段（设计文档 §6 红线，进一步加强）

继续**禁止**：
- ❌ hard exclusion（6 项 gate 不通过）
- ❌ `forced_exclusion=True`（hard 都没启用）
- ❌ `anti_false_exclusion_triggered=True`（保持 false）
- ❌ 04 `exclusion_system` 5 个 required 字段升级（保持 stub）
- ❌ 05 `confidence_system` 4 个 score 字段升真值（保持 0.0）
- ❌ 05 `event_score` 升真值（保持 None）
- ❌ 07 `simulated_trade` 任何字段升级（保持 `no_trade` / `none` / `0%`）
- ❌ 把任何 extras 字段写入 04 required

## 12. 下一步建议

按推荐优先级：

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **Step 2G-4 — soft metadata layer design doc** | 纯设计文档，spec 化 `r4_overextension` / `bullish_high_pos20` / `bullish_peer_upgrade_overextension` 三个 metadata 候选；明确"metadata-only / 不进 04 required / 不改 07"；定义触发条件、显示方式、评估指标 | **高**（本 checkpoint 的天然延续；零代码改动） |
| 2 | **anti-false-exclusion 接入设计**（Step 2G 设计文档 §9 阶段 3） | 在 4 个候选模块（`anti_false_exclusion_audit` / `big_up_contradiction_card` / `big_down_tail_warning` / `exclusion_reliability_review`）里挑一个写接入方案；纯设计文档，零实现 | 中（任何 soft 真接 04 之前必须先有保护层） |
| 3 | **不建议改代码** | 当前 read-only 工具 + dashboard 已能让消费者看到所有 slice；改 04 required 没有边际收益 | — |
| 4 | **不建议启用 hard** | 6 项 gate 不通过；2 项硬性指标任何候选都达不到 | — |
| 5 | **不建议升级 04 / 05 / 07 required 字段** | 设计文档 §6 红线 + 本次数据加强 | — |
| 6 | **不建议重启 Step 3 calibration** | holdout FAIL；本次 cross-tab 进一步证实 in-sample 双极 / 反向 bias | — |
| 7 | 后续若实现 metadata layer | 也应优先作为 `extras` / dashboard / review 提示，**不**进 04 required | 低（前置 Step 2G-4 设计） |

## 13. 2026 final test cutoff

- 本轮只用 **2023-01-03 → 2024-08-02** 的 replay 数据，与 Step 2F-4d-2
  落定的 130-pair window + Step 3A 系列 second / third window + Step 3D-1
  smoke 完全一致。
- **未触碰 2026-01-01 之后的 final test range**（CLI / sqlite SELECT
  都不按时间过滤，但 DB 本身没有 2026-01-01 之后的 replay 行）。
- 后续 Step 2G-4 设计 / 任何 metadata layer 实现 / 任何 anti-false-exclusion
  接入，**都不能**用 2026-01-01 之后数据反复调参 / 反复跑 dashboard
  挑参数。
- 2026-01-01 之后仍是**整个系统**完成后的最终测试集；如果将来要把
  metadata layer 用到 final test，必须新增显式时间过滤参数 + 显式
  final-test 模式，避免无意中把 final test 数据混入调参样本。

## 14. 严守边界

- ❌ **没**改任何代码
- ❌ **没**新增任何测试
- ❌ **没**写 DB（SELECT only；`init_db` 不调用；`INSERT` / `UPDATE` /
  `DELETE` 全无）
- ❌ **没**改 DB schema
- ❌ **没**接 `yfinance` / `requests` / 任何网络
- ❌ **没**接 trading API / `longbridge` / `broker` / `paper_trade`
- ❌ **没**改 `predict.py` / `scanner.py` / `prediction_store.py`
- ❌ **没**改 `confidence_engine.py` / `contradiction_engine.py` /
  `feature_builder.py`
- ❌ **没**升级 04 `exclusion_system` 5 个 required 字段
- ❌ **没**升级 05 `confidence_system` 4 个 0.0 score 字段
- ❌ **没**升级 05 `event_score`（保持 None）
- ❌ **没**升级 07 `simulated_trade` 6 个决策字段
- ❌ **没**启用 hard exclusion
- ❌ **没**启用 `forced_exclusion=True`
- ❌ **没**修改 `anti_false_exclusion_triggered`
- ❌ **没**接四个离线 anti-false-exclusion 模块到主链
- ❌ **没**触碰 2026-01-01 之后 final test range
- ❌ **没**运行 replay / **没**新写 replay 行
- ❌ **没**触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` /
  `avgo_agent.db.backup_*`
- ✅ 只新增 1 份 markdown checkpoint（本文件）
