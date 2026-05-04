# Step 3R-1 — Regime Label Design

> **设计文档（regime label design），不实现，不改代码。**
> 本文档**冻结** Step 3R-1 的 v1 label set、各 label 的定义 / 输入
> 字段 / bucket 阈值候选 / 风险、`regime_labels.v1` schema、
> anti-lookahead / cutoff 规则、与现有 `regime_features_builder.py`
> + Step 2G diagnostics 的边界关系。
>
> 本轮**不动任何代码**：不改 `predict.py` / `run_predict` /
> `scanner.py` / `prediction_store.py` / `app.py` / 任何 `ui/*` /
> `services/*`（含 `services/regime_features_builder.py`）/ 任何
> builder / DB schema / 任何 test 中的任何一处。
>
> **本文不实现 label / formula / helper**；只在 markdown 层冻结
> schema 与阈值候选，给后续 3R-2 diagnostics / 3R-3 smoothing /
> 3R-4 validation 提供稳定输入。

---

## 1. 背景

- **Step 3R-0** restart scope checkpoint 已冻结全程边界（commit
  `1b7288e`）：8 步路线 + 14 项硬禁止 + 9 项成功标准 + 2026 final
  test 永久封禁
- **Step 3R-1** 是 8 步路线的第 2 步：在 markdown 层选定 v1 label
  set + schema，**不**动代码
- **目标输出**：`regime_labels.v1` schema 草案 + 5 个 v1 label 的
  bucket 设计 + anti-lookahead 协议 + 与 Step 2G / 3D-1 现有
  diagnostics 的衔接边界
- **不实现 formula、不写 helper、不改 builder、不进入 3R-2 之前的
  动代码阶段**

---

## 2. 为什么需要 regime label

| # | 证据（来源 step） | 含义 |
|---|---|---|
| 1 | Step 2G-8C：R4 H1 fer 0.24 vs H2 fer 0.41，gap +0.18 | R4 触发条件在不同 regime 下命中率差距巨大 |
| 2 | Step 2G-8C §6：H2 期间 7/34 records 是 pos20 ≥ 0.90 cluster | "高位反转" 假设在 sustained bull regime 下系统性失效 |
| 3 | Step 2G-8C §6.2：2024-02 单月 fer 0.75（4 records / 3 correct） | NVDA earnings + AVGO ATH 突破月让 R4 误杀放大 |
| 4 | Step 3B-1 / 3A-4：4×4 lookup 双重 FAIL | 单一 pos20 quartile 不够；离散桶不可跨窗迁移 |
| 5 | Step 2G-8B：42 个 narrower R4 candidate 全 NO-GO | 单维 narrower 不能解决；需要**正交的 regime 维度** |

**label 要回答的核心问题**：
- 当前是不是 **sustained bull regime**？（H2 高 fer 主因）
- 当前**overextension 是否真的危险**？（H1 低 fer / H2 高 fer 的根因）
- **peer momentum** 当前是 confirm 还是 weak？（R4 触发条件中的 OR
  分支区分）
- **monthly / earnings shock** 当前是否在场？（2024-02 单月效应的来源）

→ 这些问题需要**多维 regime label**，而不是单一 pos20 quartile。

---

## 3. 候选 label 清单

8 个候选，按数据可得性 + 可解释性排序：

### 3.1 `pos20_regime`

| 项 | 值 |
|---|---|
| **definition** | AVGO 在最近 20 个交易日 high / low 区间内的相对位置 |
| **input fields** | `coded_data/AVGO_coded.csv` 的 `Date` / `Adj Close`（已存在） |
| **bucket values** | `low` / `mid` / `high` / `extreme` |
| **why useful** | Step 3B-0 已验证 pos20 单调 bias（−36 → +47）；R4 触发的核心阈值（0.62）也是 pos20 |
| **risk / failure mode** | 单一 pos20 已被 4×4 lookup 双重 FAIL 证明不够；必须与其它维度组合 |
| **v1 是否保留** | ✅ **是**（最稳的连续信号；现有 `_compute_pos20` 直接可复用） |

### 3.2 `avgo_minus_soxx_20d_regime`

| 项 | 值 |
|---|---|
| **definition** | AVGO 与 SOXX 在最近 20 个交易日的累计回报差 |
| **input fields** | `AVGO_coded.csv` + `SOXX_coded.csv` 的 `Adj Close`（已存在） |
| **bucket values** | `underperform` / `neutral` / `outperform` / `extreme_outperform` |
| **why useful** | R4 触发的核心阈值（5%）；与 pos20 正交（绝对位置 vs 相对力度） |
| **risk / failure mode** | 极值阈值（如 ≥ +12%）样本稀疏；H2 max 20.6% 是 outlier |
| **v1 是否保留** | ✅ **是**（与 pos20 正交；R4 已用） |

### 3.3 `market_trend_regime`

| 项 | 值 |
|---|---|
| **definition** | 大盘（QQQ）/ 半导体板块（SOXX）的整体趋势状态 |
| **input fields** | `QQQ_coded.csv`（**当前缺**） + `SOXX_coded.csv` 的 60 / 120 日 rolling slope / drawdown |
| **bucket values** | `weak_market` / `neutral_market` / `bull_market` / `sustained_bull_market` |
| **why useful** | 直接对应 Step 2G-8C 发现的 H1（震荡）vs H2（多头主升浪）；解释 R4 在不同 regime 下命中率差距 |
| **risk / failure mode** | 需要新增 QQQ coded csv；阈值（"sustained" 多久）需要 cross-window 验证；hindsight 风险（容易回头看才标） |
| **v1 是否保留** | ✅ **是**（解 H1/H2 gap 的关键维度） |

### 3.4 `ai_bull_regime_flag`

| 项 | 值 |
|---|---|
| **definition** | NVDA + SOXX 是否处于持续 N 月强势（2 值） |
| **input fields** | NVDA + SOXX 60 / 120 日 cumulative return + drawdown |
| **bucket values** | `false` / `true`（二值） |
| **why useful** | 直接对应 H2 期间 NVDA / AVGO AI rally；最直白的 regime 标签 |
| **risk / failure mode** | 二值过粗，丢失连续信号；hindsight bias（"AI bull" 概念在 2024 之后才广为人知）；与 `market_trend_regime` 高度相关 |
| **v1 是否保留** | ⚠️ **暂缓**（被 `market_trend_regime` 涵盖；二值过粗；先用连续 trend 维度） |

### 3.5 `peer_momentum_regime`

| 项 | 值 |
|---|---|
| **definition** | 同业（NVDA / SOXX / QQQ）与 AVGO 的同向连续天数 / confirmation 强度 |
| **input fields** | NVDA + SOXX + AVGO 短窗（5 / 10 日）相关性 / 同向计数 + Step 2G 已有的 `peer_confirm_count` 字段 |
| **bucket values** | `weak` / `mixed` / `confirmed` / `overheated` |
| **why useful** | R4 触发条件中的 OR 分支（confidence_high ∨ primary_score_raw > 2）背后就是 peer momentum；Step 2G-8C §5 显示 peer_adjustment / peer_confirm_count 在 H1/H2 几乎一致 → **当前 peer 信号粒度太粗**，需要更细的 momentum 维度 |
| **risk / failure mode** | 与 R4 触发条件部分耦合（避免双计入）；需要明确"confirmed" vs "overheated" 的阈值 |
| **v1 是否保留** | ✅ **是**（与 pos20 / diff 正交；细化 R4 OR 分支） |

### 3.6 `volatility_range_regime`

| 项 | 值 |
|---|---|
| **definition** | AVGO 短窗（10 日）日度收益的标准差 / range compression 程度 |
| **input fields** | `AVGO_coded.csv` 的 `Adj Close` + 10 日 rolling stdev / max−min range |
| **bucket values** | `compressed` / `normal` / `expanded` / `extreme` |
| **why useful** | 区分爆发前夕（compression）vs 已经爆发（expansion）；Step 2G 未覆盖 |
| **risk / failure mode** | 与 `pos20_regime` / `market_trend_regime` 部分相关；阈值难定 |
| **v1 是否保留** | ⚠️ **暂缓**（先看 v1 4 个 label 是否够；后续可作为 3R-1.5 扩展） |

### 3.7 `earnings_or_shock_flag`

| 项 | 值 |
|---|---|
| **definition** | 当前是否处于 AVGO / NVDA earnings window（前后 5 个交易日）或重大 shock 月 |
| **input fields** | earnings calendar（**当前缺**） + 价格 spike 检测 |
| **bucket values** | `none` / `earnings_window` / `shock_window` / `earnings_x_shock` |
| **why useful** | 直接对应 Step 2G-8C 发现的 2024-02 NVDA earnings 单月异常（fer 0.75） |
| **risk / failure mode** | 当前**没有**earnings calendar 数据；需要外部数据；shock 检测 hindsight 风险高 |
| **v1 是否保留** | ⚠️ **暂缓**（数据缺；与 `market_trend_regime` 部分覆盖；先靠 trend regime + monthly context 的组合代替） |

### 3.8 `monthly_context_regime`

| 项 | 值 |
|---|---|
| **definition** | 月度上下文（normal / earnings month / breakout month / shock month），从价格 + 月份计算 |
| **input fields** | analysis_date 月份 + 同月 AVGO / SOXX rolling 价格 spike + ATH 突破检测 |
| **bucket values** | `normal` / `earnings_month` / `breakout_month` / `shock_month` |
| **why useful** | 解释 2024-02 单月异常；不依赖 earnings calendar（用价格 spike + 月份 derive） |
| **risk / failure mode** | "breakout_month" / "shock_month" 阈值需要 cross-window 验证；hindsight bias（事后才知道哪个月是 breakout） |
| **v1 是否保留** | ⚠️ **二选一**（与 `ai_bull_regime_flag` 二选一；本文推荐**保留** `monthly_context_regime` 暂缓 `ai_bull_regime_flag` —— 见 §4） |

---

## 4. v1 label set 推荐

**v1 只保留 5 个 label**，原则：少而稳，每个都可由现有数据 read-only
计算：

| # | label | 数据可得性 | 与其它 label 正交性 | 解 H1/H2 gap 的能力 | v1 |
|---|---|---|---|---|---|
| 1 | `pos20_regime` | ✅ 已有 | 中（与 R4 触发部分耦合） | 中 | ✅ |
| 2 | `avgo_minus_soxx_20d_regime` | ✅ 已有 | 中（与 R4 触发部分耦合） | 中 | ✅ |
| 3 | `peer_momentum_regime` | ⚠️ 需新增计算（短窗同向） | **高** | 中-高 | ✅ |
| 4 | `market_trend_regime` | ⚠️ **需新增 QQQ coded csv** | **高** | **最高** | ✅ |
| 5 | `monthly_context_regime` | ✅ 由 analysis_date + 价格 derive | 中-高 | 高（解 2024-02 单月） | ✅ |
| 6 | `ai_bull_regime_flag` | ⚠️ 与 #4 重叠 | 与 #4 高度相关 | 高（但二值过粗） | ❌ 暂缓 |
| 7 | `volatility_range_regime` | ✅ 已有 | 与 #1 / #4 部分相关 | 低 | ❌ 暂缓 |
| 8 | `earnings_or_shock_flag` | ❌ **缺 earnings calendar** | 高 | 中-高（但被 #5 部分覆盖） | ❌ 暂缓 |

### 4.1 `monthly_context_regime` vs `ai_bull_regime_flag` 二选一的理由

- 两者都解 H2 / 2024-02 异常，但**重叠**严重
- **保留 `monthly_context_regime`**：因为它是**连续可计算**的（每月都有
  context，不只是 "AI bull / not"），并且 derive 方式（价格 spike + ATH
  突破）**不引入 hindsight 概念词**（不需要"AI bull" 这种事后归类）
- **暂缓 `ai_bull_regime_flag`**：二值过粗，且"AI bull" 这个 label 名
  本身带 hindsight bias（2024 之后才被广泛使用）；功能上由
  `market_trend_regime = sustained_bull_market` 涵盖

### 4.2 v1 = 5 个 label 的覆盖矩阵

| 维度 | 哪个 label 覆盖 |
|---|---|
| 绝对位置（高 / 低） | `pos20_regime` |
| 相对力度（vs SOXX） | `avgo_minus_soxx_20d_regime` |
| 同业确认强度 | `peer_momentum_regime` |
| 大盘 / 板块趋势状态 | `market_trend_regime` |
| 月度上下文（earnings / breakout / shock） | `monthly_context_regime` |
| 已被涵盖（不单独 label）| AI bull → 隐含在 `market_trend_regime` |
| 暂缓的 | `volatility_range_regime` / `earnings_or_shock_flag` |

---

## 5. 每个 v1 label 的 bucket 设计（design thresholds）

**这是 design-time 阈值候选，不实现，待 Step 3R-4 cross-window
validation 验证。**

### 5.1 `pos20_regime`

| bucket | 阈值 | 备注 |
|---|---|---|
| `low` | `pos20 < 0.35` | 显著低位 |
| `mid` | `0.35 ≤ pos20 < 0.65` | 中位 |
| `high` | `0.65 ≤ pos20 < 0.85` | 高位（含 R4 触发 0.62 阈值上方） |
| `extreme` | `pos20 ≥ 0.85` | 接近 20 日新高（与 Step 2G-8C 发现的 ≥ 0.90 cluster 部分重合） |

### 5.2 `avgo_minus_soxx_20d_regime`

| bucket | 阈值 | 备注 |
|---|---|---|
| `underperform` | `< −0.05` | 跑输 SOXX |
| `neutral` | `−0.05 ≤ x < +0.05` | 跟齐 SOXX |
| `outperform` | `+0.05 ≤ x < +0.12` | R4 触发的核心区间（≥ 0.05） |
| `extreme_outperform` | `≥ +0.12` | 极端跑赢（与 Step 2G-8C 发现的 ≥ 10% / ≥ 12% 阈值实验对齐） |

### 5.3 `peer_momentum_regime`

| bucket | 阈值草案 | 备注 |
|---|---|---|
| `weak` | NVDA / SOXX 5 日同向 < 50% AND `peer_confirm_count` ≤ 1 | 同业弱确认 |
| `mixed` | 50% ≤ 同向 < 70% OR `peer_confirm_count` = 2 | 同业混合 |
| `confirmed` | 同向 ≥ 70% AND `peer_confirm_count` ≥ 2 | 同业一致 |
| `overheated` | 同向 ≥ 85% AND NVDA + SOXX 5 日累计 ≥ +5% | 同业全面过热（H2 期间常态） |

### 5.4 `market_trend_regime`

| bucket | 阈值草案 | 备注 |
|---|---|---|
| `weak_market` | QQQ 60 日 slope < 0 AND drawdown > 5% | 大盘走弱 |
| `neutral_market` | QQQ 60 日 slope ∈ [−0.5%, +0.5%/月] | 大盘震荡 |
| `bull_market` | QQQ 60 日 slope > +0.5%/月 AND drawdown ≤ 5% | 标准多头 |
| `sustained_bull_market` | QQQ 60 日 slope > +1%/月 AND drawdown ≤ 3% AND 持续 ≥ 3 个月 | sustained AI bull rally（解 H2 fer 高） |

### 5.5 `monthly_context_regime`

| bucket | 阈值草案 | 备注 |
|---|---|---|
| `normal` | 当月 AVGO 单月收益 ∈ [−5%, +10%] AND 无 ATH 突破 | 常规月份 |
| `earnings_month` | analysis_date 落在 AVGO 公布财报的月份（**3 / 6 / 9 / 12 月**作为 v1 启发，待 cross-window 验证） | 财报月（不依赖 earnings calendar） |
| `breakout_month` | 当月 AVGO 单月收益 > +10% AND 突破前 60 日最高 | 主升月 |
| `shock_month` | 当月 AVGO 单月 abs 收益 > +15% OR 单日 abs 收益 > 5% 且 SOXX 同向 | 重大 shock 月（如 2024-02） |

**所有阈值都是 v1 候选**，必须在 Step 3R-4 cross-window validation
中验证；任何阈值不通过 → 回到 3R-1 重新设计。

---

## 6. v1 schema 草案

```json
{
  "schema_version": "regime_labels.v1",
  "as_of_date": "2024-08-02",
  "data_cutoff_date": "2024-08-02",
  "labels": {
    "pos20_regime": "high",
    "avgo_minus_soxx_20d_regime": "outperform",
    "peer_momentum_regime": "confirmed",
    "market_trend_regime": "sustained_bull_market",
    "monthly_context_regime": "normal"
  },
  "raw_features": {
    "pos20": 0.838,
    "avgo_minus_soxx_20d": 0.077,
    "peer_confirm_count": 3,
    "peer_5d_aligned_pct": 0.78,
    "qqq_60d_slope_per_month": 0.018,
    "qqq_60d_drawdown": 0.022,
    "soxx_60d_slope_per_month": 0.022,
    "monthly_return_pct": 0.045,
    "monthly_max_abs_daily_return": 0.031
  },
  "warnings": [],
  "final_test_refusal": false
}
```

### 6.1 schema 不变量

| 字段 | 必备 | 不变量 |
|---|---|---|
| `schema_version` | ✅ | 总是 `"regime_labels.v1"` |
| `as_of_date` | ✅ | ISO 8601 日期；与调用方传入一致 |
| `data_cutoff_date` | ✅ | `≤ as_of_date`；anti-lookahead 关键字段 |
| `labels` | ✅ | 5 个 label 必须全部 present；缺失字段 → `null` + warning |
| `raw_features` | ✅ | 9 个 raw feature 必须全部 present；缺失 → `null` |
| `warnings` | ✅ | list of string；可空 |
| `final_test_refusal` | ✅ | bool；`as_of_date ≥ 2026-01-01` 时必须 `True` |

### 6.2 设计选择

- **labels 与 raw_features 分离**：让 sidecar 渲染只关心 labels；
  让 simulator 同时拿 labels + raw_features
- **`schema_version` 显式锁定**："v1"；后续扩展走 v1.1 / v2
- **`final_test_refusal` 显式字段**：让任何 downstream 一眼看到
  "本条记录不可用"，无需解析 warnings
- **没有任何字段写到 04 / 05 / 07 required**：与 Step 3R-0 边界一致

---

## 7. anti-lookahead / cutoff 规则

| # | 规则 | 强度 |
|---|---|---|
| 1 | `data_cutoff_date ≤ as_of_date` | **硬不变量**（违反 → 整个 label set 报废） |
| 2 | **不读** `outcome_log`（`actual_close` / `direction_correct` / `actual_close_change`） | 硬不变量（看 outcome 即破坏 anti-lookahead） |
| 3 | **不读** prediction result（`predict_result_json` 中的 `final_direction` / `final_projection` / `final_confidence`）| 硬不变量（label 是 input，predict 是 output；不能反过来） |
| 4 | **不读** review result（`review_log`） | 同 #2 |
| 5 | **不读** 2026-01-01 之后任何数据 | **永久封禁**；`as_of_date ≥ 2026-01-01` → `final_test_refusal = True` 且 labels 全 `null` |
| 6 | replay 中**每一天只能用当天以前数据**：60 / 120 日窗口必须满足 `window_end_date ≤ as_of_date` | 硬不变量（与现有 `_compute_pos20` / `_compute_nday_return` 一致） |
| 7 | earnings_month / breakout_month / shock_month **derive 自当月已发生数据**，不能"今天看到下旬要 breakout 就提前标" | 硬不变量；shock 阈值在 cross-window 验证时按 strict-causal 模拟 |
| 8 | `peer_5d_aligned_pct` 用 **过去** 5 个交易日，**不**含 `as_of_date` 当日（避免 same-day data leak） | 硬不变量 |

---

## 8. 与现有 `regime_features_builder.py` 的关系

| 维度 | 现状 | Step 3R-1 设计 | Step 3R-2 实施时 |
|---|---|---|---|
| `services/regime_features_builder.py` | 输出 `{pos20, avgo_minus_soxx_20d, warnings, final_test_refusal_via_warnings}` | **本文不改** | 仍**不**改；纯函数保持原样 |
| `pos20` / `avgo_minus_soxx_20d` 计算 | `_compute_pos20` / `_compute_nday_return` 已存在 | **本文复用**（直接喂给 `pos20_regime` / `avgo_minus_soxx_20d_regime`） | 在新 helper 中调用 |
| 新 label（peer_momentum / market_trend / monthly_context） | **不存在** | **本文设计 schema + bucket** | Step 3R-2 新增 `services/regime_labels_builder.py` 实现 |
| `regime_labels_builder` 返回 schema | — | `regime_labels.v1`（§6） | 由调用方 inject coded data + outcome-blind input |
| 与 `soft_metadata.v1` 的关系 | soft_metadata 输出每条 prediction 的 R4 / residual signal | `regime_labels.v1` 是**正交维度**（per-day regime context，不是 per-prediction signal） | 两者并列；不替代 |

**核心约束**：Step 3R-1 / 3R-2 **不**改 `regime_features_builder.py`；
新 helper（`regime_labels_builder.py`）是**新增模块**，调用现有
`_compute_pos20` / `_compute_nday_return` 等私有函数（或通过新增公共
导出），但**不修改**它们的契约。

---

## 9. 与 Step 2G diagnostics 的关系

| Step 2G 模块 | 与 Step 3R-1 关系 | 备注 |
|---|---|---|
| `services/soft_metadata_simulator.py`（v1）| 上游 evidence | soft_metadata.v1 的 signals[] / R4 trigger context 是 per-prediction；regime_labels.v1 是 per-day。两者并列，不替代 |
| `ui/anti_false_exclusion_display.py`（AFX v1）| 不动 | AFX 5 个 protective findings 仍在原节点；regime_labels 不取代它们 |
| `services/protection_layer_diagnostics.py`（8A.1）| 不动 | 2 个 baseline-level guard 仍由 dashboard 喂；regime_labels 是新维度 |
| `ui/protection_layer_diagnostics_renderer.py`（8A.2）| 不动 | 不动；规避 forbidden token 标准继承 |
| `services/anti_false_exclusion_dashboard.py`（8A.3 aggregate）| 未来 3R-2 可在该文件**新增**字段 | 仅 read-only sidecar；不改 hard_gate_status；不改 hard_exclusion_allowed |
| Step 2G-7C dashboard 6-gate | 不解封 | regime_labels 不参与 gate 判定 |
| 04 / 05 / 07 required | 不升级 | regime_labels 仅 sidecar |
| `hard_exclusion_allowed` | 永远 False | regime_labels 不解封 |

---

## 10. label 风险和防误用

| # | 风险 | 防控 |
|---|---|---|
| 1 | **过拟合**：label 太多导致小样本切片噪声 | v1 限制 5 个 label；任何新增需走 launch review |
| 2 | **hindsight bias**：`ai_bull_regime_flag` / `breakout_month` / `shock_month` 在事后才好定义 | 暂缓 `ai_bull_regime_flag`；其它"事件型" label 必须 strict-causal（只用当天以前数据 derive） |
| 3 | **earnings calendar 缺失**：`earnings_or_shock_flag` 当前无可靠输入 | 暂缓；v1 用 `monthly_context_regime` 的"earnings_month"启发式（按月份）替代 |
| 4 | **label 之间相关性**：如 `pos20_regime=extreme` 几乎总是 `avgo_minus_soxx_20d_regime=outperform`+ | 在 Step 3R-2 diagnostics 中输出 label 联合分布，由 3R-4 协议决定是否合并 |
| 5 | **bucket 阈值偷看**：阈值在 H1+H2 上"调到刚好" → cross-window 失败 | 阈值候选由 3R-1 设计层冻结；3R-4 在 W1/W2/W3 三窗口分别验证；任何阈值在某窗口偏离 ≥ 5% 必须重新设计 |
| 6 | **label 当 hard 用**：未来有人把 label 喂给 `_build_exclusion_system` | 强约束在 Step 3R-0 / 3R-1 文档；helper 实现时 import-isolation 测试锁定 |
| 7 | **2026 偷看** | `final_test_refusal` 字段 + `as_of_date ≥ 2026-01-01` 强制 refusal；helper 实现时 unit test 锁定 |

**总原则**：v1 必须**少而稳**；所有阈值在 Step 3R-4 validation 中
被验证；任何 label 在某窗口大幅偏离 → 必须重新设计而不是调阈值。

---

## 11. 成功标准

Step 3R-1 通过的标准：

| # | 标准 | 验证方法 |
|---|---|---|
| 1 | v1 label set **不超过 5 个** | 本文 §4：5 个 |
| 2 | 每个 label 可由历史数据 **read-only** 计算 | 本文 §3：每个 label 的 input fields 已列；`pos20` / `diff` 现有；`market_trend` 需 QQQ csv，可补；`monthly_context` 由 analysis_date + 价格 derive；`peer_momentum` 由短窗同向 derive |
| 3 | **anti-lookahead** 明确 | 本文 §7：8 条规则 |
| 4 | `regime_labels.v1` schema 稳定 | 本文 §6：schema + 7 项不变量 |
| 5 | 可供 Step 3R-2 diagnostics helper 使用 | helper 接口设计在 3R-2 文档；本文只确保 schema 完整 |
| 6 | **不触碰 final test** | `as_of_date ≥ 2026-01-01` → `final_test_refusal = True`；硬不变量 |
| 7 | 与现有 `regime_features_builder.py` 兼容 | 本文 §8：复用 `_compute_pos20` / `_compute_nday_return`，不改契约 |
| 8 | 与 Step 2G diagnostics 边界清楚 | 本文 §9：5 项关系矩阵 |
| 9 | 风险有防控 | 本文 §10：7 项风险 + 防控 |

---

## 12. 下一步建议

按推荐优先级：

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **Step 3R-1 checkpoint** | 把本文 v1 label set / schema 固化进 checkpoint；冻结 5 个 label + 阈值候选 + anti-lookahead | **本轮 / 下一轮** |
| 2 | **Step 3R-4** validation protocol design | 3+ 窗口 + leave-one-out + 6 metric；本文 §5 阈值候选必须在 3R-4 协议下被验证 | **高**（与 #1 并行；纯 markdown） |
| 3 | **Step 3R-2** read-only regime label diagnostics helper | 新增 `services/regime_labels_builder.py` + tests + dashboard 字段；调用现有 `_compute_pos20` / `_compute_nday_return`；**仅在 #1 / #2 完成后启动** | 中（首个动代码步） |
| 4 | **Step 2G-8D** extend replay coverage | 数据层；为 Step 3R-4 W4 准备；**不**触碰 2026 | **高**（与 Step 3R 解耦可并行） |
| 5 | **不推荐**直接实现 calibration formula | 必须先过 3R-1 / 3R-4 / 3R-5 | **❌** |
| 6 | **不推荐**直接实现 simulator | 必须先过 3R-5 design | **❌** |
| 7 | **不推荐** R4 hard implementation | Step 2G-8 / 8B / 8C 三重 NO-GO | **❌** |
| 8 | **不推荐** 让 `_PROTECTION_LAYER_CONNECTED` 翻 True / Gate 5 / Gate 6 自动 pass | 与 Step 2G-8A v1 / Step 3R-0 一致 | **❌** |
| 9 | **不推荐** 升级 04 required schema | Step 2G 全程边界 | **❌** |
| 10 | **不推荐** 触碰 2026 final test range | 永久封禁 | **❌** |

**关键判断**：
- v1 label set **数量 5 个、不贪多**是核心节流
- `monthly_context_regime` vs `ai_bull_regime_flag` 二选一选了前者，
  避免 hindsight 概念词 + 二值过粗
- 阈值候选**全部待验证**；3R-4 协议先于 3R-2 实施
- Step 3R-2 是 Step 3R 第一个**动代码**步骤；启动前必须有 3R-1
  checkpoint + 3R-4 validation protocol 双保险

---

## 13. 严守边界

本文是**纯 design markdown**：

- ❌ 没改任何代码（`services/*` / `ui/*` / `tests/*` 全部未触碰，
  含 `services/regime_features_builder.py` /
  `services/regime_diagnostics_dashboard.py` /
  `services/anti_false_exclusion_dashboard.py` /
  `services/soft_metadata_simulator.py` /
  `services/protection_layer_diagnostics.py` /
  `ui/protection_layer_diagnostics_renderer.py`）
- ❌ 没改 DB schema
- ❌ 没写 DB
- ❌ 没改 `run_predict` / `predict.py` / `scanner.py` /
  `prediction_store.py` / `app.py` / 任何 ui 模块 / 任何 builder
- ❌ 没改 04 / 05 / 07 任何 required 字段
- ❌ 没启用 `hard` / `forced_exclusion` /
  `anti_false_exclusion_triggered`
- ❌ 没接 `yfinance` / `requests` / 任何网络
- ❌ 没接 trading API / `longbridge` / `broker` / `paper_trade`
- ❌ 没让 `_PROTECTION_LAYER_CONNECTED` 翻 True
- ❌ 没让 `hard_gate_status.protection_layer_connected` 自动 pass
- ❌ 没改 `hard_exclusion_allowed` / `primary_blocker` 派生
- ❌ 没触碰 2026-01-01 之后 final test range
- ❌ 没运行 replay / 没新写 replay 行
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` /
  `avgo_agent.db.backup_*`
- ❌ 没运行 `pytest`（本轮纯文档；测试基线维持 commit `1b7288e` 时
  的 2604 / 0 failed / 10 skipped）
- ✅ 只新增 1 份 markdown design 文档（本文件）
