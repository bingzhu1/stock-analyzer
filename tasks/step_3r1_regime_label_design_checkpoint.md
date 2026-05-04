# Step 3R-1 — Regime Label Design Checkpoint

> **状态固化文档（regime label design checkpoint），不实现，不改代码。**
> 本文档**冻结** Step 3R-1 design（commit `a8df93a`）的 v1 label set
> （5 个）、`regime_labels.v1` schema、bucket 阈值候选状态（待 3R-4
> 验证）、8 项 anti-lookahead 不变量、3 个暂缓 label、与现有
> `regime_features_builder` + Step 2G diagnostics 的边界关系。
>
> 本轮**不动任何代码**：不改 `predict.py` / `run_predict` /
> `scanner.py` / `prediction_store.py` / `app.py` / 任何 `ui/*` /
> `services/*`（含 `services/regime_features_builder.py` /
> `services/regime_diagnostics_dashboard.py` /
> `services/anti_false_exclusion_dashboard.py` /
> `services/protection_layer_diagnostics.py` /
> `ui/protection_layer_diagnostics_renderer.py`）/ 任何 builder /
> DB schema / 任何 test 中的任何一处。

---

## 1. 当前完成状态

- **Step 3 calibration restart launch review** 已完成并进入 main
  （commit `b8c781d`）
- **Step 3R-0** restart scope checkpoint 已完成并进入 main（commit
  `1b7288e`）—— 8 步路线 + 14 项硬禁止 + 9 项成功标准 + 2026 final
  test 永久封禁
- **Step 3R-1** regime label design 已完成并进入 main（commit
  `a8df93a`）
- 本 checkpoint **固定**：
  - v1 label set 5 个（最终选定）
  - 3 个暂缓 label（含暂缓理由）
  - `regime_labels.v1` schema（含 7 项不变量）
  - bucket 阈值**候选**状态（待 3R-4 验证）
  - 8 项 anti-lookahead 不变量
  - 与 `regime_features_builder.py` + Step 2G diagnostics 的边界
- Step 3R-1 是 8 步路线的第 2 步；本 checkpoint **只是**状态归档；
  不实现 label / formula / helper

---

## 2. 当前 main 状态

- main 最新 commit：**`a8df93a`**
- commit message：`docs(contract): Step 3R-1 regime label design`
- 上游：`origin/main` 已同步
- 测试基线：**2604 passed / 0 failed / 10 skipped**（与 Step 2G-8C
  / 3R-0 / Step 3 launch review 终点一致；本步骤无代码改动，无回归）

本步骤新增文件（已 merge 到 main）：

| 路径 | 类型 | 说明 |
|---|---|---|
| `tasks/step_3r1_regime_label_design.md` | 已进 main | 13 节、436 行；v1 label set + schema + 阈值候选 + anti-lookahead |

本 checkpoint 文档（即本文件）尚未 commit；本轮只写文档、不 commit /
push。

---

## 3. v1 label set

5 个（最终选定，少而稳）：

| # | label | purpose | keep reason |
|---|---|---|---|
| 1 | **`pos20_regime`** | 位置高低（low / mid / high / extreme） | 已有数据（`_compute_pos20`）；解释 overextension；R4 触发 0.62 阈值的来源 |
| 2 | **`avgo_minus_soxx_20d_regime`** | 相对 SOXX 强弱（underperform / neutral / outperform / extreme_outperform） | 已有数据（`_compute_nday_return`）；解释 peer-relative overextension；R4 触发 5% 阈值的来源 |
| 3 | **`peer_momentum_regime`** | 同行确认强度（weak / mixed / confirmed / overheated） | 区分孤立上涨 vs 同行共振；细化 R4 OR 分支（confidence_high ∨ primary_score_raw > 2）背后的 peer momentum 维度 |
| 4 | **`market_trend_regime`** | 市场趋势状态（weak / neutral / bull / sustained_bull） | 解释 sustained AI bull regime；直接对应 Step 2G-8C 发现的 H1（震荡）vs H2（多头主升）gap |
| 5 | **`monthly_context_regime`** | 月度环境（normal / earnings / breakout / shock） | 解释 2024-02 这类单月异常；不依赖 earnings calendar（用价格 spike + 月份 derive） |

---

## 4. 暂缓 label

3 个（v1 不收）：

| # | label | 暂缓理由 |
|---|---|---|
| 1 | `ai_bull_regime_flag` | **hindsight bias**："AI bull" 这个名词在 2024 之后才被广泛使用，作为 label 名容易事后归类；与 `market_trend_regime = sustained_bull_market` **高度重叠**；二值过粗丢失连续信号 |
| 2 | `volatility_range_regime` | 暂时不是首要变量；与 `pos20_regime` / `market_trend_regime` 部分相关；先看 v1 5 个是否够；可作为未来 3R-1.5 扩展 |
| 3 | `earnings_or_shock_flag` | 当前 **earnings calendar 数据不足**；功能上由 `monthly_context_regime.earnings_month` 启发式（按月份）部分覆盖；待外部数据补全后再考虑 |

---

## 5. bucket thresholds 当前状态

| 维度 | 状态 |
|---|---|
| Step 3R-1 design §5 列出的所有 bucket 阈值 | **design candidates** |
| 是否最终公式？ | ❌ **不是** |
| 是否 production rule？ | ❌ **不是** |
| 是否可直接进入 helper 实施？ | ❌ **不是** |
| 必须在何处验证？ | **Step 3R-4 cross-window validation protocol** |
| 未验证前是否可接入 3R-2 helper？ | ❌ **不可** |
| 未验证前是否可接入 3R-3 smoothing？ | ❌ **不可** |
| 未验证前是否可接入 3R-5 formula？ | ❌ **不可** |

**核心约束**：所有阈值候选**必须**在 Step 3R-4 协议（3+ 窗口 +
leave-one-window-out + 6 metric）下验证；任何阈值在某窗口偏离 ≥ 5%
必须重新设计而不是调阈值。**未验证前任何 helper / simulator / formula
实施都被硬禁止**。

---

## 6. regime_labels.v1 schema

```json
{
  "schema_version": "regime_labels.v1",
  "as_of_date": "YYYY-MM-DD",
  "data_cutoff_date": "YYYY-MM-DD",
  "labels": {
    "pos20_regime": "low | mid | high | extreme",
    "avgo_minus_soxx_20d_regime": "underperform | neutral | outperform | extreme_outperform",
    "peer_momentum_regime": "weak | mixed | confirmed | overheated",
    "market_trend_regime": "weak_market | neutral_market | bull_market | sustained_bull_market",
    "monthly_context_regime": "normal | earnings_month | breakout_month | shock_month"
  },
  "raw_features": {
    "pos20": "float | null",
    "avgo_minus_soxx_20d": "float | null",
    "peer_confirm_count": "int | null",
    "peer_5d_aligned_pct": "float | null",
    "qqq_60d_slope_per_month": "float | null",
    "qqq_60d_drawdown": "float | null",
    "soxx_60d_slope_per_month": "float | null",
    "monthly_return_pct": "float | null",
    "monthly_max_abs_daily_return": "float | null"
  },
  "warnings": [],
  "final_test_refusal": false
}
```

### 6.1 schema 不变量（继承 Step 3R-1 design §6.1）

| 字段 | 必备 | 不变量 |
|---|---|---|
| `schema_version` | ✅ | 总是 `"regime_labels.v1"` |
| `as_of_date` | ✅ | ISO 8601 日期 |
| `data_cutoff_date` | ✅ | `≤ as_of_date`（anti-lookahead 关键） |
| `labels` | ✅ | 5 个 label key 全部 present；缺失 → `null` + warning |
| `raw_features` | ✅ | 9 个 raw feature key 全部 present；缺失 → `null` |
| `warnings` | ✅ | list of string；可空 |
| `final_test_refusal` | ✅ | bool；`as_of_date ≥ 2026-01-01` 时强制 `True` |

---

## 7. anti-lookahead 不变量

| # | 规则 | 强度 |
|---|---|---|
| 1 | `data_cutoff_date ≤ as_of_date` | **硬不变量**（违反 → 整个 label set 报废） |
| 2 | **不读** `outcome_log`（`actual_close` / `direction_correct` / `actual_close_change`） | 硬不变量 |
| 3 | **不读** prediction result（`predict_result_json` 中的 `final_direction` / `final_projection` / `final_confidence`）| 硬不变量（label 是 input，predict 是 output；不能反过来） |
| 4 | **不读** review result（`review_log`） | 硬不变量 |
| 5 | **不读** 2026-01-01 之后任何数据；`as_of_date ≥ 2026-01-01` → `final_test_refusal = True` 且 labels 全 `null` | **永久封禁** |
| 6 | replay 中**每一天只能用当天以前数据**；60 / 120 日窗口必须满足 `window_end_date ≤ as_of_date` | 硬不变量 |
| 7 | earnings_month / breakout_month / shock_month **derive 自当月已发生数据**，不能事后回标 | 硬不变量 |
| 8 | `peer_5d_aligned_pct` 用**过去** 5 个交易日，**不**含 `as_of_date` 当日 | 硬不变量 |

**额外强约束**：
- **不得用未来窗口调整 label** —— 任何 cross-window validation 不通过
  时**只能**回到 3R-1 重新设计 label 维度，**不能**调阈值蒙混过关
- **不得看 final test 再回调阈值** —— 触发 = 任务中止 + 验证集污染

---

## 8. 与现有 `regime_features_builder.py` 的关系

| 维度 | 现状 | Step 3R-1 / 本 checkpoint | 未来 3R-2 实施 |
|---|---|---|---|
| `services/regime_features_builder.py` | 输出 `{pos20, avgo_minus_soxx_20d, warnings}` + `final_test_range_refusal` warning | **不改** | 仍**不**改；纯函数保持原样 |
| `_compute_pos20` / `_compute_nday_return` | 已有私有函数 | **不改** | Step 3R-2 新 helper 复用（不修改其契约） |
| 新 label（peer_momentum / market_trend / monthly_context）| **不存在** | 仅在 markdown 层设计 | Step 3R-2 新增 `services/regime_labels_builder.py` 实施 |
| Step 2G `soft_metadata.v1` pipeline | 仍走 `regime_features_builder` → `soft_metadata_simulator` | **不破坏** | regime_labels 是**新增正交维度**，并列存在 |

---

## 9. 与 Step 2G 的关系

| Step 2G 模块 | 与 Step 3R-1 关系 |
|---|---|
| `services/soft_metadata_simulator.py` | **保留为 evidence**（per-prediction 维度）；regime_labels.v1 是 per-day 维度，并列不替代 |
| `ui/anti_false_exclusion_display.py` | 不动；AFX 5 项 protective findings 保持 |
| `services/protection_layer_diagnostics.py` | 不动；2 项 baseline-level guard 保持 |
| `ui/protection_layer_diagnostics_renderer.py` | 不动；19/16/8 token forbidden lockdown 继承到未来 regime sidecar |
| `services/anti_false_exclusion_dashboard.py` | 未来 3R-2 可在该文件**新增 read-only sidecar 字段**；**不**改 `hard_gate_status` / `hard_exclusion_allowed` / `_PROTECTION_LAYER_CONNECTED` |
| Step 2G-7C dashboard 6-gate | **不解封**；regime_labels 不参与 gate 判定 |
| 04 / 05 / 07 required | **不升级**；regime_labels 仅 sidecar |
| `hard_exclusion_allowed` | **永远 False**；regime_labels 不解封 |
| Gate 5 / Gate 6 | **永远 fail**（v1）；regime_labels 不让 Gate 5 / Gate 6 自动 pass |

---

## 10. 成功标准

Step 3R-1 通过的标准（继承 design §11 + 本 checkpoint 加强）：

| # | 标准 | 验证 |
|---|---|---|
| 1 | v1 label set **≤ 5 个** | ✅ 5 个（本文 §3） |
| 2 | schema 稳定 | ✅ `regime_labels.v1` + 7 项不变量（本文 §6） |
| 3 | 每个 label 可由历史数据**只读**计算 | ✅ 9 个 raw_features 来源已列；3 个新 label 设计可由现有数据 + 新增 QQQ csv derive |
| 4 | anti-lookahead 明确 | ✅ 8 项硬不变量（本文 §7） |
| 5 | 2026 final test 不触碰 | ✅ `final_test_refusal = True` 强制；硬不变量 |
| 6 | 可供 Step 3R-4 validation 使用 | ✅ schema + label set + 阈值候选已冻结 |
| 7 | 与现有 `regime_features_builder` 兼容 | ✅ 复用 `_compute_pos20` / `_compute_nday_return`，不改契约（本文 §8）|
| 8 | 与 Step 2G diagnostics 边界清楚 | ✅ 9 项关系矩阵（本文 §9） |
| 9 | 风险防控明确 | ✅ Step 3R-1 design §10 列了 7 项风险 + 防控 |

---

## 11. 下一步建议

按推荐优先级：

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **Step 3R-4** cross-window validation protocol design | 3+ 窗口 + leave-one-window-out + 6 metric；本文 §5 阈值候选必须在 3R-4 协议下被验证；纯 markdown | **本轮 / 下一轮** |
| 2 | **Step 2G-8D** extend replay coverage（2024-08 → 2025-12，**不**触碰 2026） | 数据层；为 Step 3R-4 W4 准备；与 Step 3R 解耦可并行 | **高** |
| 3 | **Step 3R-2** read-only regime label diagnostics helper | 新增 `services/regime_labels_builder.py` + tests + dashboard 字段；**仅在 3R-4 protocol 完成后**启动 | 中（首个动代码步） |
| 4 | **不推荐**直接实现 calibration formula | 必须先过 3R-4 / 3R-5 | **❌** |
| 5 | **不推荐**直接实现 simulator | 必须先过 3R-5 design | **❌** |
| 6 | **不推荐** R4 hard implementation | Step 2G-8 / 8B / 8C 三重 NO-GO | **❌** |
| 7 | **不推荐** 让 `_PROTECTION_LAYER_CONNECTED` 翻 True / Gate 5 / Gate 6 自动 pass | 与 Step 2G-8A v1 / Step 3R-0 一致 | **❌** |
| 8 | **不推荐** 升级 04 required schema | Step 2G 全程边界 | **❌** |
| 9 | **不推荐** 触碰 2026 final test range | 永久封禁 | **❌** |

**关键判断**：
- Step 3R-2（首个动代码步）**必须**等 Step 3R-4 protocol 完成后启动
- 顺序：本 checkpoint → 3R-4 protocol design → 3R-4 checkpoint → 3R-2
- 在 3R-4 protocol 之前进入 3R-2 helper 实施 = 重蹈 Step 3B-1 覆辙
- Step 2G-8D 与上述顺序**解耦可并行**

---

## 12. 严守边界

本文是**纯 checkpoint markdown**：

- ❌ 没改任何代码（`services/*` / `ui/*` / `tests/*` 全部未触碰）
- ❌ 没改 DB schema
- ❌ 没写 DB
- ❌ 没改 `run_predict` / `predict.py` / `scanner.py` /
  `prediction_store.py` / `app.py`
- ❌ 没改 `services/regime_features_builder.py` /
  `services/regime_diagnostics_dashboard.py` /
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
- ❌ 没触碰 2026-01-01 之后 final test range
- ❌ 没运行 replay / 没新写 replay 行
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` /
  `avgo_agent.db.backup_*`
- ❌ 没运行 `pytest`（本轮纯文档；测试基线维持 commit `a8df93a` 时
  的 2604 / 0 failed / 10 skipped）
- ✅ 只新增 1 份 markdown checkpoint 文档（本文件）
