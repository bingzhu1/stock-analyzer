# Step 2G — Exclusion Soft/Hard Design

> **设计文档，不是实现。** 本文档冻结未来 04 `exclusion_system` `exclusion_level` 从 `none` 升级到 `soft` / `hard` 的规则框架与最小数据需求。
> Step 2G-1 诊断已确认当前数据完全不支持任何规则升级；本文档把"规则该长什么样、需要什么数据、什么时候能启用、永远不能启用什么"写死下来，作为未来 Step 3+ 真规则启用前的 spec。
> 写文档不动代码：本轮不改 `predict.py` / adapter / contract validator / 6 个 read-only 工具 / DB schema 中的任何一处。

## 1. 背景与结论

### 1.1 当前 04 段 contract required 字段

```python
{
    "exclusion_level": "none",
    "exclusion_sources": [],
    "exclusion_reasons": [],
    "forced_exclusion": False,
    "anti_false_exclusion_triggered": False,
}
```

5 个字段全部 stub。Step 2C-2 已通过 `extras` 子 dict 暴露 `conflicting_factors / path_risk_level / peer_path_risk_* / soft_signal` 等观察信号；required 字段语义保持不变。

### 1.2 Step 2G-1 诊断结论（4 条互相独立的阻塞理由）

1. **0 个 (contract × outcome) pair**——主项目 DB 里 3 条带 outcome 的 prediction 都缺 contract_payload；2 条带 contract 的 prediction（`0e7e37a6-...` / `2fe9eef2-...`）是合成验证记录，无 outcome
2. **样本分布坍缩到单点**——所有 valid 样本 `soft_signal == "peer_weaken"`、`path_risk_level == "medium"`、`peer_oppose_count == 3`。无 distinct 值变化
3. **没有 baseline hit rate**——不知道"不做 exclusion 时主推演命中率是多少"，无法证明"做了 exclusion 后变好了"
4. **没有 anti-false-exclusion 保护层**——`big_up_contradiction_card` / `exclusion_reliability_review` / `big_down_tail_warning` / `anti_false_exclusion_audit` 都是离线 / UI 模块，未接主链

**结论：当前不能升级 `exclusion_level`。** 任何凭直觉启用 soft/hard 的尝试都属于"为零样本设计的规则"——比保持 stub 还差。

### 1.3 关键反例（Step 2C-2.6 / 2E-4 验证样本）

`2fe9eef2-...` 这条本地验证 prediction：

- 主推演：`final_direction="偏多"`，`final_five_state="小涨"`
- peer：三 peer 全 weaker，`peer_confirm_count=0 / peer_oppose_count=3`
- `soft_signal="peer_weaken"`

**问题：** 这条预测如果直接用 `soft_signal=peer_weaken` 触发 hard exclusion，主推演的"偏多"判断会被丢弃。但**这是真否定还是误杀？** AVGO 完全可能在三 peer 都弱的情况下走个股独立行情上涨。**没有 outcome 数据，分不出来。** 这是设计文档的核心防线：**不能用单一 peer 反向信号直接 hard exclusion，否则会系统性误杀独立行情。**

## 2. exclusion_level 三档语义定义

三档**单调递进**，证据要求严格强于前一档。

### 2.1 `none` —— 无否定（默认状态）

- 主推演正常输出，下游完全信任 `final_projection` 字段
- **缺数据时仍保持 `none`**——`none` 不等于 `unknown`，缺数据用 extras 表达，不污染 required 字段
- 当前所有 prediction 都属于这一档（直到 Step 3+ 真规则启用）

### 2.2 `soft` —— 有可观察风险信号但不构成方向否定

- 有结构化的风险证据，但**不足以否定主推演方向**
- UI 可以显示 warning（如黄色标记 / 备注栏列出 reason）
- **不改变 `final_projection` 字段**——主推演结论照常输出
- **不影响 `simulated_trade` required 字段**——07 段仍 `no_trade / none / 0%`（本项目永不交易，与 exclusion 等级正交）
- 下游可以选择"加注意但仍按主推演执行"

### 2.3 `hard` —— 强证据表明主推演方向不可信

- 有 backtest 支撑的证据：触发该规则时主推演 hit rate 显著低于 baseline
- 下游**可以选择忽略 `final_direction`**——但**契约不强制忽略**（消费者按场景决策）
- **07 simulated_trade 仍保持 `no_trade`**——本项目永不开仓，hard exclusion 不改变这条策略边界
- hard 必须经过 §7 的最小数据需求验证 + §8 的指标达标 + §9 的实施路径完成

### 2.4 三档对照表

| 档位 | 证据要求 | UI 行为 | 下游决策 | 当前是否可启用 |
|---|---|---|---|---|
| `none` | 无 | 正常 | 完全信任主推演 | ✅ 默认 |
| `soft` | 有可观察信号 | warning 标记 | 加注意，可仍按主推演 | ❌ 等数据 |
| `hard` | backtest 支撑 + 通过指标 | 显示否定状态 | 可选择忽略 final_direction | ❌ 等数据 + 保护层 |

## 3. forced_exclusion 与 exclusion_level 的关系

### 3.1 关键约束

- **`forced_exclusion=True` 仅允许在 `exclusion_level == "hard"` 时出现**
- `exclusion_level < hard` 时 `forced_exclusion=True` 是**契约违反**——语义自相矛盾

### 3.2 forced_exclusion 的语义

`forced_exclusion=True` 表示"这条预测**必须**被否定，下游不应覆盖"。它是**系统级拦截**，不是策略风险。区别于普通 hard：

- **hard**：策略层面认为主推演方向不可信，但下游有权审查后覆盖
- **hard + forced**：连下游都不应覆盖，因为问题在系统层（数据 / 契约 / bug）

### 3.3 forced_exclusion 应保留给的场景

- **数据完整性错误**：scan_result 里关键字段缺失或异常（contract validator 没接住的边缘情况）
- **contract 破坏**：上游某段 payload 与 contract 严重不一致
- **明确的系统 bug**：已知的回归/错配，需要拦截避免伤害下游
- **已验证的灾难性信号**：极特定的失败模式，且 backtest 验证主推演在该信号下几乎从不正确

### 3.4 当前阶段的强约束

**当前禁止 `forced_exclusion=True`。** 理由：

- 没有 hard exclusion 启用，forced 也无落地基础
- 没有可信的 backtest 数据界定"灾难性信号"
- 数据完整性 / contract 破坏的检测应当用 contract validator 处理（已是 Step 1B 范围），不是 04 段
- 系统 bug 应当用测试和监控发现，不是 contract 字段

## 4. anti_false_exclusion_triggered 保护逻辑

### 4.1 角色：hard exclusion 的刹车

`anti_false_exclusion_triggered` 是 hard 决策的**复核标记**：

- 当 hard 规则触发，**同时**反向证据（如已知的 big-up 反例 / 历史相似不否定）触发时，置 `True`
- **置 True 不自动降级**——是否因此把 hard 降为 soft，是消费层决策
- 契约层只负责报告"该 hard 触发可能是误杀，请复核"

### 4.2 语义边界

- `exclusion_level=soft` 时不应有 `anti_false_exclusion_triggered=True`——soft 本身已是弱表达，不需要二级保护
- `exclusion_level=hard` 时**允许** `anti_false_exclusion_triggered=True / False`
- `forced_exclusion=True` 时通常不应触发 anti-false——因为 forced 已经是"不可覆盖"决策；如果同时触发反向证据，应当审视 forced 的设定本身（设计 bug）

### 4.3 未来候选数据来源

| 模块 | 当前状态 | 接入主链需要做什么 |
|---|---|---|
| `services/anti_false_exclusion_audit.py::audit_big_up_exclusion` | 离线 audit | 需要在 `_build_exclusion_system` 加调用，且统一 row 输入 schema |
| `services/big_up_contradiction_card.py::audit_decision` | 仅 UI | 同上 + 需要把 `audit_decision == "blocked_by_audit"` 翻译为 anti-false-trigger |
| `services/big_down_tail_warning.py` | 离线告警 | 同上，专 big_down 场景 |
| `services/exclusion_reliability_review.py` | 仅 UI | 同上，专 review 后置评估 |

**当前这四个模块都未接主链**——Step 2C-1 已诊断；本文档不实施任何接入。

## 5. 当前 extras 到未来规则的候选映射

> 严格分类：**当前仅观察 / 未来最多到 soft / 未来可能 hard（需 backtest）/ 永远不应升级**。

| 候选规则 | 当前 | 最高未来档位 | 主要风险 |
|---|---|---|---|
| `soft_signal == "peer_weaken"` | 观察项 | **soft** 候选 | 误杀 AVGO 独立行情；当前唯一可观测样本就是这条，触发频率可能很高 |
| `soft_signal == "high_path_risk"` | 观察项 | **永远不应升级**（路径维度，方向 ≠ 路径）| 路径风险与方向预测正交，混淆会污染 04 段语义 |
| `path_risk_level == "high"` | 观察项 | **永远不应升级** | 同上 |
| `peer_path_risk_direction == "higher"` | 观察项 | **辅助 warning**（可作 reason 文本，但不单独触发档位升级） | 不能单独否定方向 |
| `conflicting_factors_count >= N` | 观察项 | **soft** 候选（N 由 backtest 校准）| 阈值太低会过度否定；N 必须从数据反推，不能直觉定 |
| 主推演 `偏多` + 三 peer 全 weaker（即 `final_direction=偏多` 且 `peer_oppose_count=3 且 peer_confirm_count=0`） | 观察项 | **soft** 候选 | 个股独立行情误杀；与单独 peer_weaken 的风险同源 |
| `confidence_level == "low"` 且 `soft_signal != "none"` | 观察项 | **soft** 候选 | 低置信本身已被 confidence_level 表达，不应双重惩罚 |
| `primary_score_raw` 越界（如绝对值 > X 或符号与 final_direction 矛盾） | 观察项 | **永远不应升级**（calibration 决策，不是 exclusion）| 这是 Step 2F 范围，归一化进 `structure_score`，不是 04 段 |

### 5.1 hard 升级的强约束

**没有任何单一 extras 信号可以单独升级到 hard。** Hard 必须满足以下**复合条件之一**（仅候选；具体阈值由 backtest 决定）：

- 多个 soft 信号同时触发（如 `peer_weaken` + `confidence_level=low` + `path_risk=high` 同时成立）
- 历史相似度匹配显示该状态组合的 hit rate 显著低于 baseline
- 来自独立模块（如未来某个真接入的 anti-false-exclusion 层）的反否定证据**不**触发

## 6. 哪些规则永远不能直接 hard

> 这一节是**红线**，不允许任何未来 step 突破。

| 单独使用 | 永远不允许 hard 的理由 |
|---|---|
| `soft_signal == "peer_weaken"` | 一信号一规则，会系统性误杀独立行情；必须组合其他信号 |
| `soft_signal == "high_path_risk"` | 路径维度 ≠ 方向维度 |
| `path_risk_level == "high"` | 同上 |
| `conflicting_factors_count >= N` | 单独使用容易过度敏感（一个 peer 反对就 N=1，过度敏感）|
| `confidence_level == "low"` | 已被 confidence_level 表达，hard 等于双重否定 |
| `primary_score_raw` 任何条件 | 这是 calibration 字段，不是 exclusion 字段 |
| `simulated_trade.extras.*` 任何字段 | 07 段 extras 是观察 metadata，与决策正交 |
| **任何单一 extras 字段** | hard 必须是复合证据 + backtest 支撑 |

## 7. 最小数据需求

> 与 Step 2F-2 `_MIN_RECOMMENDED_PAIRS = 90` 同口径。

| 维度 | 最低值 |
|---|---|
| 总 (contract × outcome) pair | **≥ 90** |
| 每个候选规则的"触发样本"数（trigger group）| **≥ 30** |
| 每个候选规则的"非触发对照组" | **≥ 30** |
| `confidence_level` 三档（high / medium / low）各覆盖 | **≥ 30**（用于跨档位 baseline） |
| `soft_signal` 三档（none / peer_weaken / high_path_risk）各覆盖 | **≥ 30** |
| `path_risk_level` 三档（low / medium / high）各覆盖 | **≥ 30**（仅作 warning 评估，不直接进 hard）|
| baseline hit rate 标准误差 | ≤ 0.05（pair 数足够大就自然满足）|

### 7.1 真实样本要求

- **必须来自真实历史回放或真实运行**——不接受合成 outcome
- 当前主项目 DB 里两条 `prediction_for_date=2099-xx-xx` 的合成验证记录**不算**
- 如何积累真实样本是 Step 2F-4 的范围（独立任务），不在本文档实施范围

## 8. 指标定义

### 8.1 核心指标（评估某候选规则的好坏）

- **False exclusion rate（误杀率）：** 规则触发后，如果**主推演原本会正确**，算误杀
  - 公式：`false_exclusion = correct_in_trigger_group / total_in_trigger_group`
  - 目标：**≤ 0.10**（任何 hard 候选规则的硬性下限）
- **Missed exclusion rate（漏报率）：** 规则**没**触发但**主推演错误**的比例
  - 公式：`missed_exclusion = wrong_in_non_trigger_group / total_in_non_trigger_group`
  - 目标：**≤ baseline 错误率**（即不让漏报比"完全不否定"更严重）
- **Baseline hit rate：** 不开任何 exclusion 时全样本的命中率（参考线）
- **Net benefit：** 启用规则后整体 hit rate 提升
  - 公式：`net = post_rule_hit_rate - baseline_hit_rate`
  - 目标：**≥ +0.05**（绝对值，5% 以上才值得启用）

### 8.2 hard exclusion 的目标

| 指标 | 目标 |
|---|---|
| False exclusion rate | ≤ 0.10 |
| Net benefit | ≥ +0.05 |
| 不系统性误杀 big-up | anti_false_exclusion_audit 不报警 |
| 不系统性误杀独立行情 | 主推演偏多场景下的 hit rate 不低于该场景 baseline |

### 8.3 指标的负样本意义

- **任何候选规则若 false exclusion rate > 0.10**：永远不进 hard 候选，最多到 soft 候选
- **任何候选规则若 net benefit ≤ 0**：完全不应启用——不是"等更多数据"，是"不启用"
- **任何候选规则若系统性误杀 big-up / 独立行情**：永远不进 hard 候选，且 anti_false_exclusion_audit 应作为保护层接入

## 9. 实施路径（必须按顺序）

> 每一步都需要**独立立项**；每一步都不应在前一步未完成时启动。**当前在第 0 阶段。**

### 阶段 0（本文档）—— 设计冻结

- 写本文件，把规则语义、约束、指标、阈值、最小数据需求 spec 化
- **不实施任何代码**
- 完成标志：本文件进 main

### 阶段 1 —— 数据收集

- 目标：积累真实 (contract × outcome) pair ≥ 90
- 方法：真实历史回放（Step 2F-4 范围）/ 持续真实运行积累
- **禁止合成 outcome**——任何合成数据无 calibration / exclusion 评估价值
- 工具支持：`scripts/summarize_confidence_calibration_inputs.py` 持续监控 `data_gap_report.calibration_ready` 状态
- 完成标志：`calibration_ready=true` 且 `missing_dimensions=[]`

### 阶段 2 —— 规则评估（只读）

- 目标：用真实数据验证 §5 候选映射的实际表现
- 方法：写一个新的只读评估工具（或扩展现有 calibration_inputs），按 §8 指标计算每个候选规则的 false exclusion rate / missed exclusion rate / net benefit
- **不修改任何主链代码**
- 输出：每个候选规则的"是否值得 soft / hard / 永不启用"判定 + 阈值建议
- 完成标志：候选规则表通过 §8 目标的子集明确通过 / 不通过

### 阶段 3 —— anti-false-exclusion 保护层接入设计

- 目标：决定 §4 中四个候选模块（anti_false_exclusion_audit / big_up_contradiction_card / big_down_tail_warning / exclusion_reliability_review）哪些接入主链、如何接入
- 方法：与阶段 2 数据并行评估，看哪个保护层在历史样本上能正确捕获误杀
- **仍是设计文档**，不实施
- 完成标志：保护层接入方案文档进 main

### 阶段 4 —— soft 试运行

- 目标：让 `_build_exclusion_system` 根据通过阶段 2 验证的 soft 规则，**仅**生成 `exclusion_level="soft"`，**不**启用 hard
- 范围：改 adapter `_build_exclusion_system` 的 required 字段输出（动 contract）；新增针对 soft 规则的测试
- **forced_exclusion 保持 False；anti_false_exclusion_triggered 保持 False；hard 不启用**
- 持续监控 §8 指标，看 soft 实际表现是否与阶段 2 评估一致
- 完成标志：soft 规则在生产中稳定运行 N 周（具体值由阶段 2 数据决定），且监控指标无显著恶化

### 阶段 5 —— hard 候选

- 目标：让通过阶段 2 + 阶段 4 双重验证的规则进入 hard
- 必须同时满足：
  - 阶段 3 的保护层已接入主链
  - §8 全部目标达标
  - 复合证据规则定义清晰（不是单一 extras 信号）
- **forced_exclusion 仍保持 False**
- 完成标志：hard 在生产中稳定运行，false exclusion 报警频率 ≤ 阈值

### 阶段 6 —— forced_exclusion

- 目标：仅在 §3.3 列出的 4 类场景下使用
- **必须单独立项**，不和阶段 5 的策略 hard 规则混用
- 触发条件极保守：例如 contract validator 失败 + 已知数据破坏 + backtest 显示 100% 失败
- 完成标志：forced 在生产中触发频率极低且每一次触发都被人工复核

## 10. 严守边界

> 这是 Step 2 全程的不变量。

- ❌ **本文档不是实现** —— 不改任何代码，不新增任何测试
- ❌ **不接 v1 stub 三件套**（`risk_model.py` / `contradiction_engine.py` / `confidence_engine.py`）
- ❌ **不接离线 audit 模块到主链**（`big_up_contradiction_card` / `exclusion_reliability_review` / `big_down_tail_warning` / `anti_false_exclusion_audit`）
- ❌ 不接 longbridge / broker / paper_trade / 真实交易 / 模拟盘 API
- ❌ **不改变 04 required 字段**（`exclusion_level=none` / `forced_exclusion=False` / `anti_false_exclusion_triggered=False` / 空 list）
- ❌ **不改变 07 no_trade 策略**（与 exclusion 升级正交，永远 `trade_action=no_trade`）
- ❌ **不允许凭直觉启用 soft / hard** —— 任何升级必须通过 §9 的阶段 1 / 阶段 2 双重验证
- ❌ 不动 `predict.py` / `run_predict` / 4 个 builder / adapter / contract validator / `prediction_store` / DB schema / UI / 6 个 read-only 工具

## 11. 下一步建议

按 Step 2F checkpoint §7 的优先级，本文档落地后可选：

| 候选 | 范围 | 优先级 |
|---|---|---|
| **Step 2G-3** —— 写 Step 2G checkpoint，串联 2G-1 / 2G-2 | 仿 2B / 2C / 2D / 2E / 2F checkpoint 模式，纯 markdown handoff 文档 | 高（与本文档同时存档可让 Step 2 全程进入完全收口状态） |
| **Step 2F-4** —— 真实历史回放 / outcome pair 数据生成方案设计 | 设计文档（仿本文档模式），定义如何积累 ≥90 个真实 pair；不实施 | 中（为本文档 §9 阶段 1 铺路） |
| **DB hygiene** —— 清理 `2099-xx-xx` 合成 validation 记录 + `avgo_agent.db.backup_step_2c_2_6` | 单独确认任务；写 ad-hoc 删除 / 归档脚本，不进仓库 | 中（避免合成数据长期混在真实数据里污染未来诊断输出） |
| **Step 3+** —— 真规则启用 | 必须等 Step 2F-4 数据 + Step 2G 阶段 2 评估通过 | **低**（不应在数据缺口下启动） |

### 11.1 Step 3+ 启动的最小前提（与本文档 §9 阶段 1-3 等价）

- 真实 (contract × outcome) pair ≥ 90，且分布跨 confidence_level / soft_signal / path_risk 三档
- 阶段 2 评估通过：每个候选规则的 false exclusion rate / net benefit 达标
- 阶段 3 保护层方案进 main
- 本文档 §6 红线条目无任何违反
