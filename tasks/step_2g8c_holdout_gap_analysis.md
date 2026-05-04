# Step 2G-8C — Holdout Gap Analysis

> **只读分析文档（read-only research）。**
> 本文档对 Step 2G-8B research（commit `c9b4725`）发现的 R4 跨窗口
> 缺口（first_half FER ≈ 0.24 vs second_half FER ≈ 0.41，gap ≈ +0.18）
> 做归因分析：**这个缺口主要由什么样本结构差异驱动？是否存在
> 简单的 narrower 条件能在两个窗口同时收敛 FER？Gate 6
> `cross_window_holdout_pass` 是否在 Step 2G 范围内可解？**
>
> **结论：NO-GO** — gap 主要由 H2 期间的"sustained bull regime + high-
> pos20 cluster"驱动；这是 regime-shift 而非样本量或单一阈值问题；
> Gate 6 在 Step 2G 范围内**不可解**，必须等 Step 3 calibration 重启
> （regime-aware exclusion）或 Step 2G-8D 扩展数据。
>
> 本文不改任何代码、不改 DB、不写 DB、不接网络 / trading API、不
> 触碰 04 / 05 / 07 required 字段、不让 hard / forced 升级、不触碰
> 2026-01-01 之后 final test range。

---

## 1. 背景

Step 2G-8B research（commit `c9b4725`）跑了 42 个 narrower R4 候选
切片，全部 **NO-GO**。但其中一个开放问题：

> first_half FER ≈ 0.24，second_half FER ≈ 0.41，gap ≈ +0.18
> → R4 行为有 regime / window dependency；
> 下一步应做 Step 2G-8C holdout gap analysis。

本文回答 4 个问题：

1. **缺口在结构层面是什么样子？**（H1 vs H2 各维度分布对比）
2. **缺口的 top 3 suspected drivers 是什么？**
3. **能不能用 narrower 条件在 H1 + H2 同时收敛 FER？**（counterfactual）
4. **Gate 6 `cross_window_holdout_pass` 是否在 Step 2G 范围内可解？**

---

## 2. R4 holdout gap baseline（复现）

| 切片 | date range | paired | correct | wrong | FER | NB |
|---|---|---:|---:|---:|---:|---:|
| **first_half** | 2023-01-06 → 2023-11-07 | 17 | 4 | 13 | **0.2353** | +0.0158 |
| **second_half** | 2023-12-15 → 2024-07-08 | 17 | 7 | 10 | **0.4118** | +0.0047 |
| gap (H2 − H1) | — | — | +3 | −3 | **+0.1765** | −0.0111 |

**FER 口径**：R4 是 fully-bullish exclusion candidate，
`false_exclusion_rate = correct / paired` —— 因为如果 hard 排除 R4，
会"误杀"这些原本预测正确的多头判断。这个口径与 Step 2G-7C / 2G-8 /
Step 2G-8B 完全一致。

**关键观察**：H2 paired 不变（17）但 correct 几乎翻倍（4→7），FER
从 0.24 跳到 0.41 —— 不是样本量问题，是 R4 的"误杀基础"在 H2 上
明显增加。

---

## 3. 数据与方法

- 数据：`/Users/may/Desktop/stock-analyzer-main/avgo_agent.db`（380
  条 `replay_AVGO_*` 行 / 286 paired / 2023-01-04 → 2024-08-05 区间）
  + `coded_data/{AVGO,SOXX}_coded.csv`
- R4 触发判断：`regime_diagnostics_dashboard._is_r4_record`（与 Step
  2G-8B 完全一致）
- 切片定义：按 `analysis_date` 升序，前 17 条 = first_half，后 17
  条 = second_half（与 Step 2G-8B "holdout window split" 一致）
- 公式：FER = `correct / paired`；NB = counterfactual（与
  `soft_metadata_simulator._net_benefit_from_dashboard` 一致）；
  baseline = 286 paired × `confidence_level ∈ {high, medium, low}`
- **不**触碰 2026-01-01 之后 final test range（DB 中也无该区间数据）
- 全部 read-only：SELECT-only SQL + read-only CSV + inline Python

---

## 4. first_half vs second_half 对比

### 4.1 pos20 分布（**最显著的结构差异**）

| 桶 | H1 | H2 |
|---|---:|---:|
| ≤ 0.70 | 4 | 3 |
| 0.70 - 0.80 | 3 | 4 |
| 0.80 - 0.90 | 8 | 3 |
| **≥ 0.90** | **2** | **7** |

H2 的 pos20 ≥ 0.90 cluster 比 H1 多 **3.5 倍**（7 vs 2）。
mean / median：H1 = 0.7963 / 0.8361，H2 = 0.8295 / 0.8761。

### 4.2 avgo_minus_soxx_20d 分布

| 统计 | H1 | H2 |
|---|---:|---:|
| n | 17 | 17 |
| mean | 9.25 | 10.19 |
| median | 7.62 | 7.72 |
| pmin / pmax | 5.22 / 16.49 | 5.40 / 20.61 |
| pstdev | 3.81 | 5.07 |

H2 的极值更高（max 20.6 vs H1 16.5），方差更大；中位数几乎一样。

### 4.3 confidence_level

| level | H1 | H2 |
|---|---:|---:|
| high | 17 | 15 |
| medium | 0 | 2 |

H1 全部 high；H2 含 2 个 medium。差异微小。

### 4.4 peer_adjustment

| adj | H1 | H2 |
|---|---:|---:|
| upgrade | 12 | 12 |
| hold | 5 | 3 |
| downgrade | 0 | 2 |

H2 出现 2 个 downgrade；H1 全无。差异微小。

### 4.5 peer_confirm_count

| count | H1 | H2 |
|---|---:|---:|
| 0 | 1 | 3 |
| 1 | 4 | 2 |
| 2 | 4 | 7 |
| 3 | 8 | 5 |

H2 偏向中等 confirm 数（2），H1 偏向 3-confirm。

### 4.6 primary_score_raw

| 统计 | H1 | H2 |
|---|---:|---:|
| n | 17 | 17 |
| mean | 2.76 | 2.69 |
| median | 2.25 | 2.25 |
| pstdev | 0.96 | 0.78 |

几乎一样；H1 略高、方差略大。

### 4.7 soft_signal

| signal | H1 | H2 |
|---|---:|---:|
| none | 17 | 15 |
| peer_weaken | 0 | 2 |

H2 含 2 个 peer_weaken；H1 全 none。差异微小。

### 4.8 monthly distribution + per-month FER

| half | month | paired | correct | FER |
|---|---|---:|---:|---:|
| H1 | 2023-01 | 1 | 0 | 0.00 |
| H1 | 2023-03 | 3 | 0 | 0.00 |
| H1 | 2023-05 | 4 | 1 | 0.25 |
| H1 | 2023-06 | 3 | 0 | 0.00 |
| H1 | 2023-07 | 2 | 2 | **1.00** |
| H1 | 2023-10 | 3 | 0 | 0.00 |
| H1 | 2023-11 | 1 | 1 | **1.00** |
| H2 | 2023-12 | 4 | 1 | 0.25 |
| H2 | 2024-01 | 1 | 1 | **1.00** |
| H2 | **2024-02** | **4** | **3** | **0.75** |
| H2 | 2024-04 | 3 | 0 | 0.00 |
| H2 | 2024-06 | 2 | 1 | 0.50 |
| H2 | 2024-07 | 3 | 1 | 0.33 |

H2 的 4 个月份（12 / 1 / 2 / 6 / 7）全部 FER ≥ 0.25；H1 只有 2 个
（5 月 0.25 / 7 月 1.00 / 11 月 1.00），其余四个月份 FER = 0.00。

---

## 5. 结构差异分析

H2 相比 H1 的结构变化**集中在两个维度**：

1. **pos20 高点 cluster**：H2 的 pos20 ≥ 0.90 数量是 H1 的 3.5 倍（7
   vs 2）。这意味着 H2 期间 AVGO 多次触发 R4 时已经处于 20-day 接近
   最高点 —— 历史上"高位反转"假设在 2024 NVDA / AI 持续行情下被
   多次反例打脸（详见 §6.1）
2. **2024-02 月效应**：H2 单月（2024-02，4 records，FER 0.75）贡献
   ≈ 0.06 FER 单独把 H2 从 0.35 推到 0.41 —— Feb 2024 是 NVDA earnings
   后 AVGO ATH 突破月

其它维度（confidence / peer / soft_signal / primary_score_raw / diff
中位数）H1 与 H2 几乎相同。

---

## 6. Top 3 suspected gap drivers

### 6.1 #1 — H2 sustained bull regime + high-pos20 cluster（最显著）

H2 期间 7 条 pos20 ≥ 0.90 的 R4 触发记录：

| date | pos20 | diff | confidence | peer | outcome |
|---|---:|---:|---|---|---|
| 2023-12-15 | 0.918 | 6.54 | high | upgrade | **correct** |
| 2023-12-18 | 0.981 | 7.20 | high | upgrade | wrong |
| 2023-12-21 | 0.901 | 5.69 | high | hold | wrong |
| 2023-12-26 | 0.920 | 6.44 | medium | downgrade | wrong |
| 2024-02-08 | 0.904 | 7.33 | high | hold | **correct** |
| 2024-06-14 | 0.973 | 13.06 | high | upgrade | **correct** |
| 2024-06-17 | 0.974 | 18.90 | high | upgrade | wrong |

H2 高位 cluster 中 3/7 = 0.43 是 correct（即 R4 误杀）。

H1 同一桶只有 2 条，0/2 = 0.00 全 wrong（即 R4 正确触发）。

**结构性解释**：R4 假设"AVGO 相对 SOXX 大幅跑赢 + 已在高位 → 大概率
回调"。这一假设在 2023 H1（震荡市 + 周期反转）成立，但在 2023-12 →
2024 上半年（NVDA earnings 引领的 AI 持续多头主升浪 + AVGO 一连串
ATH 突破）频繁失败。

### 6.2 #2 — 2024-02 单月异常（NVDA earnings + AVGO ATH 突破）

| date | pos20 | diff | outcome |
|---|---:|---:|---|
| 2024-02-02 | 0.752 | 6.02 | **correct** |
| 2024-02-05 | 0.822 | 6.89 | wrong |
| 2024-02-07 | 0.876 | 7.72 | **correct** |
| 2024-02-08 | 0.904 | 7.33 | **correct** |

2024-02 月（4 records，3 correct，FER 0.75）单月贡献 ≈ 0.06 absolute
FER（即把 H2 从 ~0.35 推到 ~0.41）。

去除 2024-02 后 H2 FER 缩到 0.31，gap 从 +0.18 缩到 +0.07（详见 §7
CF6）。

### 6.3 #3 — H1 vs H2 季度构成（2023 震荡 vs 2024 多头主升）

- H1：2023-01 → 2023-11，期间 AVGO 经历 3 次明显回调（2023-03 /
  2023-05 / 2023-10），R4 假设大体成立 → FER 多月 = 0.00
- H2：2023-12 → 2024-07，期间 AVGO 几乎单边上涨（仅 2024-04 一次
  小回调，那个月 FER = 0.00）→ R4 假设频繁失败

季度构成本身不是"原因"，但它放大了 #1 与 #2：H2 的 sustained bull
regime 同时让 pos20 cluster 在高位、让月度 FER 普遍 ≥ 0.25。

---

## 7. 反事实切片结果

| # | 切片 | H1 fer | H2 fer | gap | 含义 |
|---|---|---:|---:|---:|---|
| CF1 | confidence=high | 0.235 (4/17) | 0.400 (6/15) | **+0.165** | 控制 confidence 后 gap 几乎不变 |
| CF2 | peer=upgrade | 0.167 (2/12) | 0.333 (4/12) | **+0.167** | 控制 peer=upgrade 后 gap 不变 |
| CF3 | peer ≠ downgrade | 0.235 (4/17) | 0.400 (6/15) | **+0.165** | 控制 peer 后 gap 不变 |
| CF4 | soft_signal=none | 0.235 (4/17) | 0.400 (6/15) | **+0.165** | 控制 soft 后 gap 不变 |
| CF5 | **pos20 ∈ [0.70, 0.90]** | 0.273 (3/11) | 0.286 (2/7) | **+0.013** | **控制 pos20 中段 → gap 几乎消失** |
| CF6 | H2 minus 2024-02 | 0.235 (4/17) | 0.308 (4/13) | **+0.072** | 去掉 2024-02 单月让 gap 缩到 0.07 |
| CF7 | H1 minus 2023-07/11；H2 minus 2024-02 | 0.071 (1/14) | 0.308 (4/13) | +0.236 | cherry-pick H1 outliers 反而拉大 gap |
| CF8 | pos20 ≤ 0.85 | 0.167 (2/12) | 0.375 (3/8) | **+0.208** | 限到 H1 pos20 风格 → gap 反而更大 |
| CF9 | **pos20 ≥ 0.90** | 0.000 (0/2) | 0.429 (3/7) | **+0.429** | **H2 高位 cluster 是主要 gap 源** |
| CF10 | peer_confirm ≥ 2 | 0.167 (2/12) | 0.333 (4/12) | +0.167 | 控制 confirm 后 gap 不变 |

**关键发现**：
- **CF1 / CF3 / CF4 / CF10** 全部维持 ~0.165 gap → 单维度（confidence /
  peer / soft / confirm）不能解释
- **CF5**（pos20 ∈ 中段）gap 缩到 +0.013 → pos20 是 gap 的主要载体
- **CF9**（pos20 ≥ 0.90）gap 放大到 +0.43 → 高位 cluster 行为差异
  巨大
- **CF6**（去 2024-02）gap 缩到 +0.07 → 单月也贡献显著
- **CF7** 显示 cherry-pick 不能掩盖结构性差异

→ **gap 的两个核心载体**：（A）pos20 ≥ 0.90 H2 cluster；（B）2024-02
单月。

---

## 8. Gate 6 `cross_window_holdout_pass` 判断

### 8.1 仍 fail？

**仍 FAIL**。当前 dashboard 输出：

```python
hard_gate_status["cross_window_holdout_pass"] = "fail"
holdout_status = "FAIL"
```

### 8.2 fail 的主要原因

不是单一原因，而是**结构性 + regime 组合**：

| 候选原因 | 是否成立 | 证据 |
|---|---|---|
| 样本量小 | **部分** | 17 / 17 切分本身样本量小，但即使翻倍，下面的 regime 问题仍在 |
| **regime shift** | **是（主因）** | H2 = sustained AI bull rally；R4 mean-reversion 假设在 H2 系统性失效（CF9 显示 pos20 ≥ 0.90 cluster H2 fer = 0.43） |
| **candidate 本身不稳定** | **是** | R4 触发条件（pos20 + diff + bullish + high-conf）本身 regime-agnostic，没有内置 regime guard |
| 单月异常 | 部分 | 2024-02 单月贡献 ~0.06 FER，去掉后 gap 仍 +0.07（仍未达 holdout pass） |
| 数据时窗错位 | 部分 | first_half 截到 2023-11，second_half 从 2023-12 开始；窗口边界恰好落在 AI rally 起点附近，加剧对比 |

### 8.3 Step 2G 范围内可解吗？

**不可解**。理由：

1. 修 Gate 6 需要在 R4 内嵌一个 **regime filter**（如"宽基行情趋势 ↑
   + AVGO ATH 突破"时**不**触发 R4）—— 但这违反 Step 2G 的"不改
   `_build_exclusion_system` 主链 / 不升级 04 required"边界
2. 修 Gate 6 也可以通过**换候选**（绕开 R4），但 Step 2G-8B 已显示
   42 个 R4 切片 NO-GO；只能等 Step 2G-8E 探索 R1 / R2 / R3 / R5
3. 修 Gate 6 还可以等**更多数据**（2024-08 → 2025-12 replay），让
   每个 half 涨到 ~70+ paired，gap 平均化掉 —— 但这是 Step 2G-8D
   范围，不是 Step 2G 主线

### 8.4 必须等 Step 3 calibration 重启 / more replay data？

**两个都需要，Step 3 calibration 优先级更高**：

- **Step 2G-8D extend replay coverage** 解决"样本量小 + 两个 half
  各自 17 paired 太少"问题，但**不**解决 regime sensitivity 问题
- **Step 3 calibration 重启** 才能引入 regime-aware exclusion 阈值
  （不同 regime 用不同 fer / nb 门槛，或 R4 触发条件含 regime guard）

→ 这两步**互补**：8D 提供更大数据池，3 calibration 提供 regime-aware
框架。Gate 6 只在两者都到位后才有 pass 的可能。

---

## 9. GO / NO-GO 结论

| 问题 | 结论 | 理由 |
|---|---|---|
| Step 2G-8C 是否解除 Gate 6 fail？ | **NO** | 本研究只是归因诊断；不改代码；Gate 6 仍 fail |
| 是否建议继续 R4 hard path？ | **NO-GO** | R4 在 H2 期间 fer = 0.41 + pos20 ≥ 0.90 cluster fer = 0.43；regime-agnostic 假设系统性失效 |
| 是否建议 Step 2G-8D extend replay coverage？ | **conditional GO** | 必要但不充分；解样本量不解 regime sensitivity |
| 是否建议 Step 3 calibration 重启？ | **GO**（高优先级） | 唯一能引入 regime-aware exclusion 阈值的路径 |
| 是否建议 hard / forced / required upgrade？ | **NO-GO** | 与 Step 2G-8 launch review / 8A 系列 / 8B 一致 |
| 是否建议 Step 2G-8E other R candidates？ | **conditional GO** | 探索性；R4 不是唯一候选，但需先有 regime-aware 框架 |

---

## 10. 下一步建议

按推荐优先级：

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **本文 commit + checkpoint** | 把 holdout gap 归因 + Gate 6 结构性 fail 证据归档进 main | **本轮** |
| 2 | **Step 3 calibration 重启**（regime-aware） | 引入 regime detector + 不同 regime 的 exclusion 阈值；让 R4 在 sustained bull regime 下静默 | **最高**（解决 gap 根因） |
| 3 | **Step 2G-8D** extend replay coverage（2024-08 → 2025-12） | 不触碰 2026-01-01 final test；让 R4 paired 涨到 ~70+；让 holdout split 平均化 | **高**（数据层补强） |
| 4 | **Step 2G-8E** 替换候选 R-series | 离开 R4，研究 R1 / R2 / R3 / R5；前提是 #2 / #3 至少完成一个 | 中 |
| 5 | **不推荐** Step 2G-8B.1 / 任何 narrower R4 hard 实施 | 数据层 NO-GO + regime-shift NO-GO 双重约束 | **❌** |
| 6 | **不推荐** 让 `_PROTECTION_LAYER_CONNECTED` 翻 True | 与 Step 2G-8A 系列 sidecar-only 边界冲突 | **❌** |
| 7 | **不推荐** 升级 04 required `anti_false_exclusion_triggered` | 与 Step 2G-8 launch review NO-GO 一致 | **❌** |

**强制约束**（继承 Step 2G-8A 设计 §13 / 8A.x checkpoint / 8B
checkpoint）：
- 不改 04 / 05 / 07 required 字段
- 不改 `run_predict` 主链
- 不写 DB
- 不出现 19 forbidden words / 16 forbidden words / 8 forbidden words
- `hard_exclusion_allowed` 永远 `False`
- `protection_layer_connected_for_gate` 永远 `False`（v1）

---

## 11. 严守边界

本文是**纯 read-only 研究文档**：

- ❌ 没改任何代码（`services/*` / `ui/*` / `tests/*` 全部未触碰）
- ❌ 没改 DB schema
- ❌ 没写 DB（只 SELECT）
- ❌ 没改 `run_predict` / `predict.py` / `scanner.py` /
  `prediction_store.py` / `app.py`
- ❌ 没改 `services/regime_diagnostics_dashboard.py` /
  `services/anti_false_exclusion_dashboard.py` /
  `services/soft_metadata_simulator.py` /
  `services/protection_layer_diagnostics.py` /
  `ui/protection_layer_diagnostics_renderer.py` / 任何 ui 模块 /
  任何 builder
- ❌ 没改 04 / 05 / 07 任何 required 字段
- ❌ 没启用 `hard` / `forced_exclusion` /
  `anti_false_exclusion_triggered`
- ❌ 没接 `yfinance` / `requests` / 任何网络
- ❌ 没接 trading API / `longbridge` / `broker` / `paper_trade`
- ❌ 没让 `_PROTECTION_LAYER_CONNECTED` 翻 True
- ❌ 没让 `hard_gate_status.protection_layer_connected` 自动 pass
- ❌ 没改 `hard_exclusion_allowed` / `primary_blocker` 派生
- ❌ 没触碰 2026-01-01 之后 final test range（DB 中也无该区间数据）
- ❌ 没运行 replay / 没新写 replay 行
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` /
  `avgo_agent.db.backup_*`
- ❌ 没运行 `pytest`（本轮纯研究；测试基线维持 commit `c9b4725` 时
  的 2604 / 0 failed / 10 skipped）
- ✅ 只跑 read-only Python 调用 + read-only SQLite SELECT
- ✅ 数字与 Step 2G-7C / 2G-8 / 2G-8A.x / 2G-8B checkpoint 完全一致
- ✅ 只新增 1 份 markdown 研究文档（本文件）
