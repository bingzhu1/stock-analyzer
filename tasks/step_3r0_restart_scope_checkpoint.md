# Step 3R-0 — Restart Scope Checkpoint

> **状态固化文档（Step 3R restart scope checkpoint），不实现，不改代码。**
> 本文档**冻结** Step 3R 全程的：范围、子步骤顺序、允许 / 禁止启动
> 任务清单、2026 final test 永久封禁、与 Step 2G 的边界关系、成功
> 标准。
>
> 本轮**不动任何代码**：不改 `predict.py` / `run_predict` /
> `scanner.py` / `prediction_store.py` / `app.py` / 任何 `ui/*` /
> `services/*` / 任何 builder / DB schema / 任何 test 中的任何一处。
>
> **本文不写公式、不实现 calibration / simulator / label，不改
> hard gate、不升级 04 / 05 / 07 required**。

---

## 1. 当前完成状态

- **Step 2G 系列**完整链条已完成并进入 main（截至 commit `e0ce108`）：
  - soft metadata simulator / Predict / Review display / Review
    attribution / anti-false-exclusion display / Step 2G-7C dashboard
    aggregate / Step 2G-8A.x protection diagnostics 三层 sidecar /
    Step 2G-8B narrower R4 NO-GO / Step 2G-8C holdout gap NO-GO
- **Step 3 calibration restart launch review** 已完成并进入 main
  （commit `b8c781d`）
- **Step 3R 正式启动**，但仅限 **scope / design / validation
  protocol** 阶段；**不**实现 formula / simulator / sidecar
  integration
- 本 checkpoint **固定** Step 3R 全程边界，作为后续所有 3R-x 子步
  必须遵守的硬约束

---

## 2. 当前 main 状态

- main 最新 commit：**`b8c781d`**
- commit message：`docs(contract): Step 3 calibration restart launch review`
- 上游：`origin/main` 已同步
- 测试基线：**2604 passed / 0 failed / 10 skipped**（与 Step 2G-8A.3
  / 2G-8B / 2G-8C 终点一致；本步骤无代码改动，无回归）

本步骤新增文件（已 merge 到 main）：

| 路径 | 类型 | 说明 |
|---|---|---|
| `tasks/step_3_restart_calibration_launch_review.md` | 已进 main | 13 节、382 行；Step 3R-x 8 步路线 + 12 项硬禁止 + 7 项成功标准 |

本 checkpoint 文档（即本文件）尚未 commit；本轮只写文档、不 commit /
push。

---

## 3. 为什么需要 Step 3R

| # | 证据 | 来源 |
|---|---|---|
| 1 | 旧 4×4 lookup holdout 在 250 records 上 W1↔W2 双向 FAIL（6 项标准只过 2 项） | Step 3B-1 checkpoint |
| 2 | 第三窗口扩样本到 380 records / 286 paired 后 Method A 改善但 Method B 仍崩 | Step 3A-4 checkpoint |
| 3 | R4 narrower candidate **NO-GO**（42/42 切片 0 个同时满足 paired ≥ 30 / fer ≤ 0.10 / nb ≥ +0.05） | Step 2G-8B checkpoint |
| 4 | R4 H1/H2 FER gap +0.18 由 **regime shift + 2024-02 单月异常 + R4 regime-agnostic** 三层叠加驱动 | Step 2G-8C checkpoint |
| 5 | Step 2G 三层 sidecar（soft / display / protection diagnostics）已完整落地，但 hard_gate 仍 2 pass / 4 fail | Step 2G-7C / 2G-8A.3 dashboard aggregate |
| 6 | Step 2G 范围内**无法**修 calibration（修 R4 触发条件 / 升级 required / 启 hard 全部超出 Step 2G 边界） | Step 2G-8C §9 |

→ Step 2G 只能 display / diagnostics，**不能修 calibration**；
旧 4×4 lookup 已经**双重失败**；必须重新设计 regime-aware
calibration 框架。这就是 Step 3R 存在的理由。

---

## 4. Step 3R 总目标

Step 3R 的最终目标（如果全部 8 步通过）：

1. **regime-aware calibration**：在不同 market regime 下应用不同的
   calibration 曲线（不是离散桶查询表）
2. **regime-aware exclusion**：让 R4-类候选在 sustained bull regime
   下静默，在 ranging / weak-momentum regime 下保持灵敏
3. **cross-window validation**：W1 / W2 / W3（+ 未来 W4）多窗口 +
   leave-one-window-out；不依赖单一 holdout
4. **sidecar-first simulator**：所有 calibration / exclusion 输出
   先在 `extras.regime_aware_calibration_diagnostics.v1` 节点
5. **解释**：什么时候"over-bullish"是真风险（应触发 R4 / 降低
   confidence），什么时候被 bull regime 救活（应静默 R4 / 保持
   confidence）

**Step 3R 不是**：
- 旧 4×4 lookup 重做
- 直接写 calibration formula
- 直接进入 hard / required / decision pipeline
- 替代 Step 2G display / diagnostics

---

## 5. 明确不做什么

| # | 不做 | 理由 |
|---|---|---|
| 1 | 不重做旧 4×4 lookup | Step 3B-1 / 3A-4 双重 FAIL |
| 2 | 不直接写 formula | 必须先过 Step 3R-1 / 3R-4 设计 |
| 3 | 不直接写 simulator | 必须先过 Step 3R-5 设计 |
| 4 | 不启 `hard` / `hard_exclusion_allowed` | 与 Step 2G-8 launch review NO-GO 一致 |
| 5 | 不启 `forced_exclusion` / `anti_false_exclusion_triggered` | 同上 |
| 6 | 不升级 04 / 05 / 07 required | 与 Step 2G 全程边界冲突 |
| 7 | 不写 DB / 不改 DB schema | Step 3R 全程 sidecar；不持久化 |
| 8 | 不用 2026 final test | 永久封禁；偷看 = 自毁验证集 |
| 9 | 不接 trading API / `longbridge` / `broker` / `paper_trade` | Mission 定位 = research agent |
| 10 | 不让 `_PROTECTION_LAYER_CONNECTED` 翻 True | 与 Step 2G-8A v1 强不变量冲突 |
| 11 | 不让 `protection_layer_connected_for_gate` 翻 True | 同上 |
| 12 | 不改 `final_direction` / `final_projection` / `simulated_trade` / `no_trade` / `confidence_system` | Step 2G 全程"不改主推演方向"边界 |
| 13 | 不改 `_build_exclusion_system` / `run_predict` / `scanner` 主链 | 与 Step 2G "sidecar-only" 边界一致 |
| 14 | 不调用 `yfinance` / `requests` / 任何网络 | read-only 限制 |

---

## 6. Step 3R 子步骤冻结

| step | name | scope | code? | 依赖 |
|---|---|---|---|---|
| **3R-0** | restart scope checkpoint | 固定全程边界（本文档） | ❌ | Step 3 launch review |
| **3R-1** | regime label design | label 候选筛选 + schema 冻结；纯 markdown | ❌ | 3R-0 |
| **3R-2** | read-only regime diagnostics | 新增 `services/regime_label_diagnostics.py` pure helper + tests + dashboard 字段；**不**改 `_is_r4_record` / 主链 | ⚠️ read-only helper | 3R-1 |
| **3R-3** | continuous smoothing candidate | 用 logistic / kernel / spline 替代 4×4 lookup；read-only simulator design | ⚠️ read-only simulator | 3R-2 |
| **3R-4** | cross-window validation protocol | 3+ 窗口 + leave-one-out + 6 metric；纯 markdown | ❌ | 3R-1（可与 3R-2 / 3R-3 并行） |
| **3R-5** | calibration formula design | formula shape 冻结；仍**不**实现 | ❌ | 3R-1 / 3R-3 / 3R-4 |
| **3R-6** | read-only simulator | 实现 3R-5 设计的 formula 作为 pure function；不接主链；不写 DB | ⚠️ read-only simulator | 3R-5 |
| **3R-7** | sidecar integration（conditional） | 仅在 3R-6 通过 cross-window validation 后；输出接入 `extras.regime_aware_calibration_diagnostics.v1`；仍 display-only | ⚠️ read-only sidecar | 3R-6 PASS |

**强制 gate**：每个 3R-x → 3R-(x+1) 之间必须先通过 launch review；
任何一步不过 → 整个 Step 3R 进入 NO-GO，**Step 2G display 路线为
系统最终形态**。

---

## 7. 当前允许启动的任务

| Step | 范围 | 是否动代码 | 优先级 |
|---|---|---|---|
| **Step 3R-1** regime label design | 8 候选 label 筛选（pos20 quartile / pos20 continuous / avgo_minus_soxx_20d bucket / market trend window / ai_bull_regime_flag / monthly_earnings_shock_flag / peer_momentum_confirmation / volatility_compression）+ schema 冻结 | ❌ markdown | **高** |
| **Step 3R-4** cross-window validation protocol design | W1 / W2 / W3 三窗口 + leave-one-window-out + 6 metric + 通过标准 | ❌ markdown | **高**（可与 3R-1 并行） |
| **Step 2G-8D** extend replay coverage（2024-08 → 2025-12） | 数据层；**不**触碰 2026-01-01；为 Step 3R-4 W4 准备 | ⚠️ replay 写 DB（在 Step 2G-8D 自己范围内允许） | **高**（与 Step 3R 解耦可并行） |
| **Step 3R-2** read-only regime diagnostics（**仅在 3R-1 完成后**） | 新增 `services/regime_label_diagnostics.py` pure helper + tests + dashboard 字段 | ⚠️ read-only helper | 中（顺接 3R-1） |

**节奏建议**：
- 先 3R-1 + 3R-4（两份纯 markdown，可并行）
- 完成后 3R-2（首个动代码步骤，仅 read-only helper）
- Step 2G-8D 与 3R-1 / 3R-4 并行，互不阻塞

---

## 8. 当前禁止启动的任务

| # | 禁止 | 理由 |
|---|---|---|
| 1 | **Step 3R-5** formula design 早于 3R-1 + 3R-4 | 没有 label / validation 协议，formula 必失败 |
| 2 | **Step 3R-6** simulator 早于 3R-5 design | 没有公式形状，simulator 无依据 |
| 3 | **Step 3R-7** sidecar integration 早于 3R-6 通过 cross-window validation | 跳过 validation 重蹈 Step 3B-1 覆辙 |
| 4 | hard exclusion implementation | Step 2G-8 / 8B / 8C 三重 NO-GO |
| 5 | forced exclusion implementation | 同上 |
| 6 | 04 / 05 / 07 required 字段升级 | 与 Step 2G 全程边界冲突 |
| 7 | live trading / broker 接入 | Mission 定位冲突 |
| 8 | DB schema migration | Step 3R 全程 sidecar |
| 9 | 用 2026 final test 数据调参 / "看一眼 2026 再回头改公式" | 永久封禁 |
| 10 | 让 `_PROTECTION_LAYER_CONNECTED` 翻 True | 与 Step 2G-8A v1 强不变量冲突 |
| 11 | 让 `hard_gate_status.protection_layer_connected` 自动 pass | 同上 |
| 12 | 改 `_build_exclusion_system` / `run_predict` / `scanner` 主链 | Step 2G "sidecar-only" 边界 |
| 13 | 跳过 cross-window validation 直接 sidecar | 重蹈 Step 3B-1 覆辙 |
| 14 | 跳过本 checkpoint 直接进入 3R-2 / 3R-3 等动代码步骤 | 必须先有 3R-1 label schema |

---

## 9. 2026 final test cutoff

**永久封禁**：

- 2026-01-01 之后的所有数据是**最终测试集**
- Step 3R 全程**只能**使用 2025-12-31 之前数据完成 design /
  validation
- **任何**"看一眼 2026 再回头改公式" / "拿 2026 验证 Step 3R-x" /
  "在 2026 数据上 fine-tune label" 等行为**立即**触发任务中止
- Step 2G-8D extend replay coverage 的扩展上限是 **2025-12-31**；
  **不**得越过
- final test 的使用时机：**只**在系统**完整完成**（Step 3R-7 通过 +
  Step 2G 全部稳定 + 至少 6 项 launch review 通过）后**一次性**
  评估，且评估结果**不得回流**到 calibration / label / formula
- 这条规则不会因为"快接近通过"而放松

---

## 10. 与 Step 2G 的关系

| 维度 | 关系 |
|---|---|
| Step 2G display / diagnostics 体系 | **保留不动**（soft_metadata.v1 / anti_false_exclusion_display.v1 / protection_layer_diagnostics.v1 / Step 2G-7C dashboard aggregate） |
| Step 2G-7C dashboard 6-gate | Step 3R 输出**不**改变其判定逻辑；6-gate 仍由 baseline / R4 / holdout 决定 |
| `hard_exclusion_allowed` | 永远 `False`；Step 3R 不解封 |
| `protection_layer_connected_for_gate` | 永远 `False`；Step 3R 不解封 |
| `_PROTECTION_LAYER_CONNECTED` 常量 | 永远 `False`；Step 3R 不改 |
| 04 / 05 / 07 required schema | 永远不升级；Step 3R 不动 |
| Step 2G AFX 5 protective findings | **作为输入证据**喂给 Step 3R-2 regime diagnostics（per-prediction 维度） |
| Step 2G-8A protection guard 2 项 | **作为 cross-window 监控指标**喂给 Step 3R-4 validation protocol（baseline 维度） |
| Step 3R 输出（如果通过） | **作为 sidecar** 接入 `extras.regime_aware_calibration_diagnostics.v1`；与 Step 2G AFX / 8A 并列；不进 hard / required |
| Step 3R 任意阶段不通过 | 整个 Step 3R 进 NO-GO，**Step 2G display 路线为系统最终形态** |

---

## 11. 成功标准

未来 Step 3R-7（如果走到这一步）必须满足：

| # | 标准 | 验证 |
|---|---|---|
| 1 | **Step 3R-1 label schema 冻结** | 8 候选筛选完成；进入 3R-2 前 schema 不变 |
| 2 | **Step 3R-4 validation protocol 冻结** | 3+ 窗口 + leave-one-out + 6 metric 协议进入 3R-5 前不变 |
| 3 | **Step 3R-2 diagnostics 可复现 Step 2G regime evidence** | R4 / pos20 / diff bias 与 Step 2G-7C / 8B / 8C 完全一致 |
| 4 | **cross-window metric 改善** | fer / nb / monotonicity / coverage / direction unchanged / robustness 6 项至少 5 项 PASS（vs Step 3B-1 的 2/6） |
| 5 | **不牺牲 survival cases** | Step 2G-6C `triggered_but_not_error` 象限累计与 R4 survival count 在 sidecar 中仍可见 |
| 6 | **full pytest 0 failed** | 与现状 2604 / 0 failed / 10 skipped 持平或扩张 |
| 7 | **不碰 final test** | 2026-01-01 之后数据从未在 Step 3R 任何环节被读取 |
| 8 | **sidecar-first** | 所有输出在 `extras.*` 节点；不写 04 / 05 / 07 required |
| 9 | **每一步通过 launch review 才能进 formula** | Step 3R-x → 3R-(x+1) 的硬 gate |

---

## 12. 推荐下一步

按推荐优先级：

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **Step 3R-1** regime label design | 8 候选 label 筛选 + schema 冻结；纯 markdown | **本轮 / 下一轮** |
| 2 | **Step 3R-4** cross-window validation protocol design | 3+ 窗口 + leave-one-out + 6 metric；纯 markdown；可与 #1 并行 | **高** |
| 3 | **Step 2G-8D** extend replay coverage（2024-08 → 2025-12） | 数据层；为 Step 3R-4 提供 W4；**不**触碰 2026 | **高**（与 Step 3R 解耦可并行） |
| 4 | **Step 3R-2** read-only regime diagnostics | 新增 helper + tests + dashboard 字段；**仅在 3R-1 完成后**启动 | 中（顺接 3R-1） |
| 5 | **Step 3R-3** continuous smoothing candidate | read-only simulator design；**仅在 3R-2 完成后**启动 | 中 |
| 6 | **不推荐**直接实现 calibration formula | 必须先过 3R-1 / 3R-4 / 3R-5 | **❌** |
| 7 | **不推荐**直接实现 simulator | 必须先过 3R-5 design | **❌** |
| 8 | **不推荐** R4 hard implementation | Step 2G-8 / 8B / 8C 三重 NO-GO | **❌** |
| 9 | **不推荐**让 `_PROTECTION_LAYER_CONNECTED` 翻 True | 与 Step 2G-8A v1 / Step 3 launch review 一致 | **❌** |
| 10 | **不推荐**让 Gate 5 / Gate 6 自动 pass | 同上 | **❌** |
| 11 | **不推荐**升级 04 required schema | Step 2G 全程边界 | **❌** |
| 12 | **不推荐**触碰 2026 final test range | 永久封禁 | **❌** |

---

## 13. 严守边界

本文是**纯 checkpoint markdown**：

- ❌ 没改任何代码（`services/*` / `ui/*` / `tests/*` 全部未触碰）
- ❌ 没改 DB schema
- ❌ 没写 DB
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
- ❌ 没触碰 2026-01-01 之后 final test range
- ❌ 没运行 replay / 没新写 replay 行
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` /
  `avgo_agent.db.backup_*`
- ❌ 没运行 `pytest`（本轮纯文档；测试基线维持 commit `b8c781d` 时
  的 2604 / 0 failed / 10 skipped）
- ✅ 只新增 1 份 markdown checkpoint 文档（本文件）
