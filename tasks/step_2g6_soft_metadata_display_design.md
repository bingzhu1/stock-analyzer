# Step 2G-6 — Soft Metadata Dashboard / Review Display Design

> **设计文档（display design），不是实现。** 本文档**冻结** dashboard /
> review 如何消费 Step 2G-5 simulator 输出的 `soft_metadata.v1` JSON，
> 包括显示位置、文案约束（**强制**列出禁止 / 推荐用语）、card 字段、
> R4 / residual 文案模板、review 归因规则、empty state、debug view、
> UI safety checks 与 contract required 字段的硬隔离。
>
> 本轮**不动任何代码**：不改 `predict.py` / `scanner.py` /
> `prediction_store.py` / `app.py` / `ui/*` / 任何 builder /
> `soft_metadata_simulator.py` / `regime_diagnostics_dashboard.py` /
> contract validator / DB schema 中的任何一处。

## 1. 背景

- **Step 2G-3** 用 380 replay / 286 paired 完成 soft / hard exclusion
  re-review（commit `8e837a7`）：旧 `soft_signal` 三类被反驳，
  R4 是唯一 over-bullish metadata 候选。
- **Step 2G-4** soft metadata layer design 冻结（commit `607ccc0`）。
- **Step 2G-4.5** schema review 把 8 条 schema-level blocker 固化为
  `soft_metadata.v1`（commit `18936f2`）。
- **Step 2G-5** read-only sidecar simulator 实现（commit `947f1c9`）+
  checkpoint（commit `b7675b1`）：simulator 输出 `soft_metadata.v1` JSON，
  R4 + residual 两个 active candidates 已就位、`hard_exclusion_allowed`
  恒为 `False`。
- **Step 2G-6**（本文）：把 simulator 的 JSON **设计**成 dashboard
  card + review 归因维度，明确 UI 文案约束、显示位置、安全测试要求。
- **本文档不是实现**。没有 commit 代码、没有改 UI、没有 DB 写入、
  没有新增测试。Step 2G-6 实现拆为后续 2G-6A / 6B / 6C / 6D（详见
  §13）。

## 2. 显示目标

- 让用户看到 **over-bullish metadata** —— 即"这次预测的高位偏多
  结构在历史样本里命中率较低"的事实。
- 帮助解释**为什么某些高位看多容易失败** —— 用 R4 / residual 的
  `accuracy` / `bias_gap` / `false_exclusion_rate` 把"系统倾向"量化。
- 帮助 review 归因 —— 当 prediction 错误且 metadata 触发，
  metadata 是**候选**归因维度（不是 definitive cause）。
- **不**改变预测结果（`final_direction` / `final_five_state` /
  `final_one_sentence` 等显示路径不变）。
- **不**改变交易建议（`simulated_trade.trade_action = "no_trade"` /
  `trade_direction = "none"` / `suggested_position_size = "0%"` 仍是
  唯一显示）。
- **不**让用户误读成 hard exclusion / forced exclusion / 禁止交易
  信号 / 卖出信号。

## 3. 严格文案边界

> 本节是 UI 实施时的**硬性测试**依据。Step 2G-6D UI tests 必须
> grep 渲染输出，禁止下列字符串出现。

### 3.1 UI **禁止**使用的词（任何上下文）

- 禁止交易
- 强制否定
- 必须不做
- hard exclusion
- forced exclusion
- 自动拦截
- no_trade（**不**直接显示给终端用户；07 段策略 UI 已用别的中文文案）
- 卖出信号
- 做空信号
- 看空信号 / bearish signal（metadata 是 over-bullish 风险提示，**不是**反向方向信号）
- 否决主推演 / 推翻主推演
- 强制平仓 / force close
- 阻止下单 / block order

### 3.2 UI **推荐**使用的词

- 过热提示
- 偏多过度风险
- 仅供复盘参考
- 不改变主推演方向
- 不构成交易指令
- 历史样本中该结构容易高估上涨概率
- 结构性偏多风险提示
- 复核建议（review-only）
- 信号性提示（informational signal）

### 3.3 文案模板共同规则

- 每个 card 必须显式包含至少 1 句"不改变主推演方向"或"不构成交易
  指令"
- 任何数字（accuracy / bias_gap / false_exclusion_rate）旁必须有
  解释性短语，不能只显示数字
- severity 文案颜色：`low` 用中性灰 / 蓝；`medium` 用警示黄 / 琥珀色
  —— **禁止**红色（红色用户会下意识联想"危险 / 禁止"）

## 4. Dashboard 显示位置

至少两个位置 —— Predict 页面 + Review 页面 —— 互不替代。

### 4.1 Predict 页面

**位置**（自上而下）：

```
┌─────────────────────────────────────┐
│ scan_result / current_structure     │
├─────────────────────────────────────┤
│ avgo_primary_projection             │
├─────────────────────────────────────┤
│ peer_confirmation_adjustment         │
├─────────────────────────────────────┤
│ confidence_system summary            │
├─────────────────────────────────────┤
│ exclusion_system summary             │
├─────────────────────────────────────┤
│ final_projection                     │
├─────────────────────────────────────┤
│ ✦ soft_metadata sidecar (本设计)    │  ← 这里
├─────────────────────────────────────┤
│ simulated_trade ("not trading")     │
└─────────────────────────────────────┘
```

**为什么放在 final_projection 之后、simulated_trade 之前**：

- 在 `final_projection` **之后** —— 让用户先看完主推演方向，再看
  metadata；避免 metadata 抢了主推演的视觉焦点
- 在 `simulated_trade` **之前** —— 让 metadata 与 "not trading"
  策略边界**视觉相邻**，强化"metadata 不构成交易指令"的语义；
  如果实施时发现这样会让 metadata 文案与 `no_trade_reason` 文案
  混淆，可放在 `simulated_trade` **之后**，但**必须**显式标注
  "本卡片为复盘 metadata，不是交易指令"

**显示行为**：

| 条件 | 显示 |
|---|---|
| `signals` 非空 | 展开 compact card（详见 §5）；标题"结构性偏多风险提示" |
| `signals` 空且 `summary.warnings` 非空 | 折叠成一行 dev hint："未触发 metadata（warnings: <count>）" |
| `signals` 空且无 warnings | **隐藏**（不显示空 card；避免用户每次预测都看到"未触发"提示而疲劳） |
| 任何输入下 | 永远不显示 `hard_exclusion_allowed=true`、永远不显示 §3.1 禁止文案 |

### 4.2 Review 页面

**位置**：

```
┌─────────────────────────────────────┐
│ prediction_for_date / 实际结果       │
├─────────────────────────────────────┤
│ predicted vs actual diff             │
├─────────────────────────────────────┤
│ error_category / root_cause（已有）  │
├─────────────────────────────────────┤
│ ✦ soft_metadata attribution (本设计)│  ← 这里
├─────────────────────────────────────┤
│ confidence_note / watch_for_next_time│
└─────────────────────────────────────┘
```

**用途**：

- prediction **错误** + metadata 触发 → metadata 是**候选**归因
  维度（详见 §8）
- prediction **正确** + metadata 触发 → 显示"该结构历史命中率低，
  本次属于幸存"（**不**把 metadata 当错误解释）
- prediction **错误** + 无 metadata → **不**强行归因到 metadata
- metadata 永远是 *possible attribution*，**不是** *definitive cause*

## 5. Card 内容设计

每个 `signals[i]` 渲染成一张 card。**完整字段**清单：

| 字段 | 来源（simulator JSON） | 是否默认显示 |
|---|---|---|
| `display_label` | `signals[i].display_label` | ✅ 默认 |
| `severity` badge | `signals[i].severity`（`"low"` / `"medium"`）| ✅ 默认 |
| accuracy | `signals[i].historical_metrics_in_sample.accuracy` | ✅ 默认 |
| bias_gap | `signals[i].historical_metrics_in_sample.bias_gap` | ✅ 默认 |
| "不改变主推演方向" 文案 | 静态 | ✅ 默认（强约束） |
| `raw_features.avgo_minus_soxx_20d` | `signals[i].raw_features` | 折叠（expandable） |
| `raw_features.pos20` | 同上 | 折叠 |
| `trigger_context.final_direction` | `signals[i].trigger_context` | 折叠 |
| `trigger_context.confidence_level` | 同上 | 折叠 |
| `trigger_context.primary_score_raw` | 同上 | 折叠 |
| `trigger_context.peer_subtype` | 同上 | 折叠 |
| `trigger_context.matched_or_branch` | 同上 | 折叠 |
| `historical_metrics_in_sample.samples` / `paired` | 同上 | 折叠 |
| `historical_metrics_in_sample.false_exclusion_rate` | 同上 | 折叠（用于 §6 / §7 解释） |
| `historical_metrics_in_sample.net_benefit` | 同上 | 折叠 |
| `holdout_status` | `signals[i].holdout_status`（固定 `"FAIL"`）| 折叠 |
| `recommended_action` | `signals[i].recommended_action`（固定 `"review_only"`）| ✅ 默认（用 §3.2 推荐文案显示） |
| `hard_forbidden_primary_reason` | 同上 | 折叠（用于 §6 / §7 解释） |
| `hard_forbidden_breakdown` | 同上 | 折叠 |

**默认视图**（最简）：
- `display_label`
- `severity` badge
- accuracy + bias_gap
- "不改变主推演方向 / 仅供复盘参考"
- "展开详情" 链接

**展开视图**：
- 所有 `raw_features` / `trigger_context` / 完整 `historical_metrics_in_sample` /
  `hard_forbidden_breakdown`

## 6. R4 文案设计

针对 `name == "r4_overextension"`：

### 6.1 推荐中文文案（默认视图）

> "**结构性偏多风险提示**（中等强度）
>
> 历史上，AVGO 在短期明显跑赢 SOXX 且处于 20 日区间高位时，系统
> 容易继续判偏多，但实际次日上涨比例偏低。
>
> 历史命中率：32.4% / 历史看多次数 vs 实际上涨差：+0.676
>
> 这个信号**仅提示结构性偏多风险，不改变主推演方向**，也**不构成
> 交易指令**。"

### 6.2 显示数值（默认视图）

| 指标 | 值 | UI 显示 |
|---|---|---|
| `historical_metrics_in_sample.accuracy` | 0.324 | "历史命中率：32.4%" |
| `historical_metrics_in_sample.bias_gap` | +0.676 | "看多 vs 实际上涨差：+0.676（系统在该结构下倾向高估上涨）" |

### 6.3 展开视图（"为什么不能 hard"）

显示折叠区块，标题"为什么不强制否定？"：

| 指标 | 值 | UI 解释 |
|---|---|---|
| `false_exclusion_rate` | 0.3235 | "若强制排除该结构，将同时漏掉 32% 仍真涨的样本（gate ≤ 0.10）—— 误杀率过高" |
| `net_benefit` | +0.0219 | "若强制排除，整体准确率仅提升 +2.2%（gate ≥ +5%）—— 收益不够" |
| `holdout_status` | `"FAIL"` | "跨窗口 holdout 测试已 FAIL（Step 3A-4 / 3B-1）—— 该结构在样本外不稳定" |
| `hard_forbidden_breakdown` | list | 逐条原文显示 |

### 6.4 解释（设计层面）

- `accuracy` 低（32.4%）说明 R4 这个结构**常错**
- `false_exclusion_rate` 高（0.3235）说明**不能 hard 排除**（会误杀
  11/34 真涨）
- `net_benefit` 不够（+0.0219）说明**不能强制否定**（收益不到 hard
  gate 一半）
- 三项指标的 UI 显示必须**同时**呈现 —— 任何一项缺失都会让用户
  误解为"既然命中率这么低，就应该排除"

## 7. Residual 文案设计

针对 `name == "bullish_high_pos20_residual"`：

### 7.1 推荐中文文案（默认视图）

> "**结构性偏多上下文提示**（低-中强度）
>
> 高位偏多结构存在一定过热风险，但本残差信号（剔除 R4 后）的
> 命中率接近随机，主要用于提示上下文，**不应作为否定依据**。
>
> 历史命中率：48.9% / 看多 vs 实际上涨差：+0.511
>
> 这个信号**仅提示上下文，不改变主推演方向**，也**不构成交易
> 指令**。"

### 7.2 显示数值（默认视图）

| 指标 | 值 | UI 显示 |
|---|---|---|
| `accuracy` | 0.489 | "历史命中率：48.9%（接近随机基线）" |
| `bias_gap` | +0.511 | "看多 vs 实际上涨差：+0.511" |

### 7.3 展开视图（"为什么绝对不能 hard"）

显示折叠区块，标题"为什么不强制否定？"：

| 指标 | 值 | UI 解释 |
|---|---|---|
| `net_benefit` | **−0.001**（**负值**！）| "若强制排除该结构，整体准确率不升反**降** 0.1% —— 比保持现状还差" |
| `false_exclusion_rate` | 0.489 | "若强制排除，将漏掉 49% 仍真涨的样本（gate ≤ 0.10）—— 误杀率极高" |
| `holdout_status` | `"FAIL"` | 同 R4 |

### 7.4 解释（设计层面）

- `bias_gap` 高但 `accuracy` 接近随机基线 —— 这是"高位偏多
  上下文容易高估"的证据，但**不是**"高位偏多必然错"的证据
- `net_benefit` 为**负值**（−0.001）—— 这是 residual 比 R4 更
  严格的红线：**强制排除会让整体表现下降**，所以**绝对**不能 hard
- residual 的 UI 文案必须比 R4 更弱（低-中强度，而非中强度）——
  避免让用户把 residual 误解为与 R4 同等危险

## 8. Review 归因规则

按 prediction outcome × metadata 触发的 4 种组合：

| outcome | metadata 触发？ | UI 行为 | 标记 |
|---|---|---|---|
| **wrong** | ✅ R4 触发 | 显示 "可能归因维度：高位跑赢同行后偏多过热" | `possible_attribution = "over_bullish_after_relative_outperformance"` |
| **wrong** | ✅ residual 触发 | 显示 "可能归因维度：高位偏多过热（非 R4）" | `possible_attribution = "over_bullish_high_position"` |
| **wrong** | ❌ 无 metadata | **不**强行归因到 metadata；保持现有 `error_category` / `root_cause` 不变 | （无 metadata-related tag）|
| **correct** | ✅ 任意 | 显示 "metadata 已触发但本次预测正确（结构幸存）" | `risk_metadata_triggered_but_not_error` |
| **pending** | ✅ 任意 | 不归因（outcome 未到）；显示 metadata 但不写 attribution | （仅显示，不归因）|

### 8.1 关键约束

- `possible_attribution` / `risk_metadata_triggered_but_not_error` 是
  **review 内部标记**，**不**写入 `predict_result_json` /
  `contract_payload_json` / 04 / 05 / 07 任何 required 字段
- 这些标记可以写入 `review_log.confidence_note` /
  `review_log.watch_for_next_time` 这两个 free-text 字段（与 Step 2G-4
  §12.3 一致）
- **不**应让 review 的 `error_category`（已有 enum）直接绑定到
  metadata signal name —— 前者是 review 的语义分类，后者是触发条件
- "correct + 触发"案例 UI 文案必须避免暗示"系统应该改变判断"
  （因为本次它**对了**）；显示重点是"该结构历史命中率低，本次属
  幸存"

### 8.2 metadata 永远是 possible attribution，不是 definitive cause

- 任何"definitive cause" / "确定原因" / "根本原因" 文案**不应**
  绑定到 metadata signal —— 这些归因维度需要更强证据（跨窗口
  holdout、anti-false-exclusion 保护层、Step 3 calibration 重启
  通过等），当前阶段**全部不满足**
- review UI 的归因区块标题必须用"**可能**归因维度" / "候选归因
  维度"，禁止用"根本原因" / "确定原因"

## 9. Empty state

`signals == []` 的情况：

| 场景 | UI 行为 |
|---|---|
| Predict 页面、`signals=[]`、无 warnings | **隐藏**整个 card（不显示空状态文案，避免视觉疲劳）|
| Predict 页面、`signals=[]`、有 warnings（如 missing baseline）| 折叠成单行 dev hint："未触发 metadata（warnings: <count>）"；点击展开显示 warnings 详情 |
| Review 页面、`signals=[]` | 显示一行："本次未触发 soft metadata"（review 页面不像 predict 页面那样高频，可以显示）|
| 任何场景 | `summary.max_severity == "none"` / `hard_exclusion_allowed=false` 仍可在 debug 展开项显示 |

### 9.1 final_test_range_refusal 的特殊处理

当 `summary.warnings` 包含 `"final_test_range_refusal"`（即 analysis_date
≥ 2026-01-01 触发 cutoff）：

- Predict 页面：显示一行明显的提示："本预测进入 final test
  保留区间，soft_metadata 已暂停（防止参数污染）"
- Review 页面：同上 + 链接到 [Step 2G-4.5 §13](step_2g4_5_soft_metadata_schema_review_checkpoint.md)
- **不**隐藏（与普通 empty 不同 —— 这条 warning 是有意义的状态
  说明，不是噪声）

## 10. Debug / developer view

提供 **expandable debug** 折叠区块，默认折叠（避免用户视觉负担），
展开后显示：

- 完整 `soft_metadata` JSON（pretty-printed）
- `schema_version`
- `metrics_source` / `metrics_window` / `metrics_computed_at`
- 每个 signal 的 `holdout_status`
- 每个 signal 的 `hard_forbidden_breakdown` 完整原文
- `summary.warnings` 完整列表
- 触发该 metadata 的 `regime_features`（pos20 + avgo_minus_soxx_20d）
  实测值
- baseline `db_snapshot_id`（v1 通常 `null`）

### 10.1 Debug view 的入口

- Predict 页面：card 右上角小齿轮图标 → 弹出 debug
- Review 页面：归因区块下方 "查看 metadata 原文" 链接

### 10.2 Debug view 的安全性

- Debug view 仍受 §3.1 文案约束 —— 即使是 raw JSON，UI 渲染层在
  显示前应 grep 检查文案中不包含禁止词（虽然 simulator JSON 本身
  设计上不会包含禁止词，但 grep 是防御性 check）

## 11. UI safety checks

> 本节是 Step 2G-6D UI 测试的**必测项**清单。

| # | 测试 |
|---|---|
| 11.1 | `summary.hard_exclusion_allowed == false` 时，UI 渲染输出**不包含** §3.1 禁止词（grep）|
| 11.2 | `signals` 非空时，UI 渲染输出中 `final_direction` / `final_five_state` / `final_one_sentence` 显示路径**不变**（snapshot diff 与无 metadata 场景一致）|
| 11.3 | `signals` 非空时，UI 渲染输出中 `simulated_trade.trade_action` / `trade_direction` / `suggested_position_size` 显示路径**不变** |
| 11.4 | `severity == "medium"` 时，UI **不**用红色显示；不出现 "危险" / "警告" / "danger" 文案 |
| 11.5 | `summary.warnings` 包含 `"final_test_range_refusal"` 时，UI **不**隐藏（按 §9.1）|
| 11.6 | `summary.warnings` 包含 `"missing_baseline"` 时，可作为 **developer warning** 在 debug view 显示，**不**作为用户层面的 risk 文案（避免误导）|
| 11.7 | Empty state（`signals=[]` 且无 warnings）在 Predict 页面**完全隐藏**（render 输出不含任何 metadata-related DOM）|
| 11.8 | review 页面 "correct + 触发" 案例的 UI 文案**不**包含"应该改变判断" / "should override" 等暗示 |
| 11.9 | Card 默认视图的 accuracy / bias_gap 数值**必须**带解释文字（不允许只显示裸数字）|
| 11.10 | severity badge 颜色：`low` 灰/蓝；`medium` 黄/琥珀色；**不允许**红色 |
| 11.11 | `display_label` 显示**不**被截断（即使在窄 viewport 下；折叠应折叠的是数值/详情，不是 label）|
| 11.12 | metadata UI 渲染**不**触发 `predict_result_json` / `contract_payload_json` / 04 / 05 / 07 required 字段的任何重写（snapshot 测试）|

## 12. 与 contract required 字段关系

| 字段 / 位置 | 是否被 UI metadata 路径影响 |
|---|---|
| 04 `exclusion_system.exclusion_level` | ❌ 不影响（继续 `"none"`） |
| 04 `exclusion_system.exclusion_sources` / `exclusion_reasons` | ❌ 不影响（继续 `[]`） |
| 04 `exclusion_system.forced_exclusion` | ❌ 不影响（继续 `False`） |
| 04 `exclusion_system.anti_false_exclusion_triggered` | ❌ 不影响（继续 `False`） |
| 05 `confidence_system.historical_score` / `structure_score` / `peer_score` / `exclusion_penalty` | ❌ 不影响（继续 0.0） |
| 05 `confidence_system.event_score` | ❌ 不影响（继续 None） |
| 05 `confidence_system.confidence_level` / `total_confidence` / `confidence_reason` | ❌ 不影响（仍来自原 contract payload）|
| 07 `simulated_trade.trade_action` / `trade_direction` / 三个 condition 字段 / `suggested_position_size` / `no_trade_reason` | ❌ 不影响（继续策略边界值）|
| 07 `simulated_trade.extras.trade_engine_enabled` | ❌ 不影响（继续 `False`） |
| Predict 页面其他 UI（structure / primary projection / peer / final）| ❌ 不影响 |
| metadata sidecar 自身（`extras.soft_metadata`）| ✅ 仅消费此字段，不写入 |

### 12.1 强约束

- UI 只**消费** `exclusion_system.extras.soft_metadata`（或 simulator
  CLI 输出的 sidecar JSON）
- UI **不**写入任何 contract required 字段
- 任何 required 字段 UI 显示**仍来自原 contract payload** —— UI
  渲染顺序：先渲染 required 字段（来自 contract payload），再渲染
  metadata sidecar（来自 simulator）
- 任何 required 字段升级（`exclusion_level → soft / hard` 等）必须
  经过 Step 2G-8+ 流程 + Step 2G 设计文档 §8 hard gate 通过
  （**当前任何 candidate 都不满足**）

## 13. Future implementation path

| 步骤 | 范围 | 期望 commit |
|---|---|---|
| **Step 2G-6** | 本设计文档 | 1 个 markdown |
| **Step 2G-6A** | Small UI renderer function：新增 `ui/soft_metadata_card.py`（或在现有 ui 模块下加函数）；纯函数，输入 `soft_metadata` dict，输出 Streamlit / HTML render；**不**改任何 contract required；**不**改 `app.py` 主流程 | 1 个 ui 模块 + 1 个 test 文件 |
| **Step 2G-6B** | Predict 页面接入：在 `app.py` / `ui/predict_tab.py` 调用 §13.A 的 renderer；位置按 §4.1 | UI 改动（最小） |
| **Step 2G-6C** | Review 页面接入：归因维度按 §8 规则写入 `review_log.confidence_note` / `watch_for_next_time` | UI + review 写入逻辑（仅 free-text 字段）|
| **Step 2G-6D** | UI tests：覆盖 §11 全部 12 项 safety checks；用 Streamlit AppTest 框架（与现有 `tests/test_command_bar_apptest.py` / `tests/test_control_tab_apptest.py` 同模式）| 1 个 test 文件 |
| **Step 2G-7** | anti-false-exclusion display / design：4 个候选模块（`anti_false_exclusion_audit` / `big_up_contradiction_card` / `big_down_tail_warning` / `exclusion_reliability_review`）挑一个的 dashboard 显示设计；**仍是**设计文档 | 1 个 markdown |
| **Step 2G-8+** | 04 / 05 / 07 required 字段升级 | **当前禁止** —— 前提是 hard gate 全部通过 |

### 13.1 Step 2G-6A 接口建议（设计层面）

```python
def render_soft_metadata_card(
    soft_metadata: dict,
    *,
    mode: str = "compact",         # "compact" | "expanded" | "debug"
    surface: str = "predict",      # "predict" | "review"
) -> Any:                          # Streamlit element / HTML string
    """Pure renderer. No DB / network / contract write.
    Input: simulator's soft_metadata.v1 dict.
    Output: Streamlit container or HTML to be inserted into the page.
    """
```

强约束：
- renderer 必须是**纯函数**：不读 DB / 不读 CSV / 不接网络 / 不写
  任何 contract required 字段
- renderer 输入是 `soft_metadata.v1` dict，**不**接受 raw payload
  （后者由 simulator 处理）
- renderer 必须 grep 输出文案以确保不包含 §3.1 禁止词

### 13.2 Step 2G-6B / 6C 范围限制

- 仅在 `ui/` 与 `app.py` 的**最小范围**内插入 renderer 调用
- **不**改 `predict.py` / `run_predict` 主流程
- **不**改 `contract_payload_json` 写入路径 —— renderer 调用时机
  **晚于** `save_prediction`，metadata 仅作为 UI 显示，不参与 DB
  写入

## 14. 不做什么

- ❌ 不实现 UI（renderer / Predict 接入 / Review 接入）—— 全部留给
  Step 2G-6A / 6B / 6C
- ❌ 不改 prediction logic / `predict.py` / `run_predict` / `scanner.py` /
  `prediction_store.py`
- ❌ 不改任何 builder（`_build_exclusion_system` /
  `_build_confidence_system` / `_build_simulated_trade` / 任何其他）
- ❌ 不改 `projection_output_adapter.py` / `projection_output_contract.py`
- ❌ 不改 `regime_diagnostics_dashboard.py` / `soft_metadata_simulator.py`
- ❌ 不写 DB / 不改 DB schema / 不调用 `init_db` / 不 `INSERT` /
  不 `UPDATE` / 不 `DELETE`
- ❌ 不接 broker / `longbridge` / `paper_trade` / 任何 trading API
- ❌ 不接 `yfinance` / `requests` / 任何网络
- ❌ 不把 metadata 作为交易建议（任何"trade_direction" 改写都禁止）
- ❌ 不把 R4 当 hard exclusion（任何 `exclusion_level` 改写都禁止）
- ❌ 不启用 `forced_exclusion` / `anti_false_exclusion_triggered`
- ❌ 不接 4 个 anti-false-exclusion 离线模块到主链
- ❌ 不使用 2026-01-01 之后的 final test range 调参 / 反复跑
- ❌ 不新增任何测试

## 15. 成功标准

未来若实施 Step 2G-6A / 6B / 6C / 6D 必须满足：

| # | 标准 |
|---|---|
| 1 | UI 明确显示 `recommended_action == "review_only"` 对应的 §3.2 推荐文案；不出现 §3.1 禁止文案（grep 锁定）|
| 2 | R4 数字（`accuracy`、`bias_gap`、`false_exclusion_rate`、`net_benefit`）显示与 simulator JSON 完全一致 |
| 3 | `false_exclusion_rate` 高 / `net_benefit` 不达 gate / `holdout_status=FAIL` 三项**同时**显示在 R4 / residual 的 "为什么不强制否定" 折叠区块 |
| 4 | Card 默认视图可隐藏（empty state）/ 可展开（详情 / debug）|
| 5 | UI 渲染**不影响**任何 contract required 字段（snapshot 测试与无 metadata 场景一致）|
| 6 | 测试覆盖 §11 全部 12 项 safety checks |
| 7 | 测试覆盖 empty state / R4 trigger / residual trigger / both warning / final_test_range_refusal / debug view 共 6 种典型场景 |
| 8 | Review 页面归因维度按 §8 4 种组合规则正确显示；`possible_attribution` 标记**仅**写入 `review_log.confidence_note` / `watch_for_next_time` |
| 9 | 现有测试基线（2302 / 0 failed / 10 skipped）不变 —— Step 2G-6A / 6B / 6C / 6D 的新增测试是净增 |
| 10 | dashboard 文案在用户调研 / review 反馈中**不**出现"以为这是禁止交易信号"的反馈 |

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
- ❌ 没改 `regime_diagnostics_dashboard.py` / `soft_metadata_simulator.py`
- ❌ 没改 `app.py` / `ui/*` / 任何 UI 代码
- ❌ 没改任何 builder（`_build_exclusion_system` /
  `_build_confidence_system` / `_build_simulated_trade` / 任何其他）
- ❌ 没升级 04 / 05 / 07 任何 required 字段
- ❌ 没启用 `hard` / `forced_exclusion` /
  `anti_false_exclusion_triggered`
- ❌ 没接 4 个 anti-false-exclusion 离线模块到主链
- ❌ 没改 `final_projection` / `confidence_score` / `simulated_trade` /
  `no_trade`
- ❌ 没触碰 2026-01-01 之后 final test range
- ❌ 没运行 replay / 没新写 replay 行
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` /
  `avgo_agent.db.backup_*`
- ✅ 只新增 1 份 markdown 设计文档（本文件）
