# Step 3 — Calibration Restart Launch Review

> **设计文档（calibration restart launch review），不是实现。**
> 本文档**冻结** Step 3 重启的范围、目标、新路线（Step 3R-x）、
> 新 validation 原则、与 Step 2G 的边界关系、允许 / 禁止启动的任务、
> 成功标准。
>
> 本轮**不动任何代码**：不改 `predict.py` / `run_predict` /
> `scanner.py` / `prediction_store.py` / `app.py` / 任何 `ui/*` /
> `services/*` / 任何 builder / DB schema / 任何 test 中的任何一处。
>
> **本文不写公式、不实现 calibration、不改 hard gate、不升级 04 /
> 05 / 07 required**。

---

## 1. 背景

Step 3 的当前状态是**双重失败 + Step 2G 系列已经把所有 sidecar
途径走完**：

| 节点 | 状态 | commit |
|---|---|---|
| Step 3A-2 peer / confidence inversion attribution | ✅ 已完成 | — |
| Step 3A-3 second window replay | ✅ 已完成 | — |
| Step 3A-4 third window replay | ⚠️ **partial FAIL** | `522a1eb` 后补 |
| Step 3B regime-aware calibration design | ✅ 设计冻结 | — |
| Step 3B-0 regime split diagnostics | ✅ 已完成 | — |
| **Step 3B-1 holdout simulation** | **❌ FAIL（2/6 通过）** | — |
| Step 3B-2 / 3B-3 / 3B-4 / 3C | ⚠️ **冻结**（FAIL 未解除） | — |
| Step 3D-1 read-only regime diagnostics dashboard | ✅ 已完成 | — |
| **Step 2G 完整链条**（soft / display / AFX / protection / dashboard / R4 narrower / holdout gap） | ✅ 全部完成 | 截至 `e0ce108` |
| Step 2G-8B narrower R4 candidate | **NO-GO**（commit `c9b4725` / `e2f68c6`） | — |
| Step 2G-8C holdout gap analysis | **regime-shift NO-GO**（commit `395ca77` / `e0ce108`） | — |

**核心失败链条**：
- Step 3B-1：在 W1↔W2 双向 holdout 上，4×4 lookup 6 项标准只过 2 项
  （direction unchanged + coverage），核心 monotonicity / R4 触发 /
  probability calibration / robustness 全 FAIL
- Step 3A-4：扩第三窗口 250 → 380 records / 193 → 286 paired 后，
  Method A 改善（calibrated_high acc 0.333 → 0.611），但 Method B
  仍崩（high bucket 完全为空）→ **partial FAIL，不解除**
- Step 2G-8B：narrower R4 hard candidate **NO-GO**（42 个候选切片
  0 个同时满足 paired ≥ 30 / fer ≤ 0.10 / nb ≥ +0.05）
- Step 2G-8C：R4 first_half FER 0.24 vs second_half 0.41，gap +0.18
  由 **regime shift** + **2024-02 单月异常** + **R4 regime-agnostic**
  叠加驱动 —— **结构性 NO-GO**

**Step 2G 已经把所有 sidecar 维度走完**：
- soft metadata simulator（v1）
- Predict / Review display
- Review attribution（Step 2G-6C `triggered_but_not_error` 象限）
- anti-false-exclusion display.v1（5 protective findings）
- Step 2G-7C dashboard aggregate（含 6-gate hard status）
- Step 2G-8A.x protection diagnostics（helper / UI / dashboard
  aggregate / 4 connection flags / 2 guards）
- Step 2G-8B / 8C 已正式给出"R4 narrower + holdout 都无法在 Step 2G
  内解决"的归因结论

→ **Step 3 必须重启**，但**不能**重做 Step 3B 的 4×4 lookup 路线，
也**不能**直接用 Step 2G 的 sidecar 升级到 hard。本文设计 Step 3
重启的范围、新路线、validation 原则。

---

## 2. 当前证据链

| evidence（来源 step） | conclusion |
|---|---|
| Step 3A-2 peer/confidence inversion | simple confidence baseline 对 R4 不可靠 |
| Step 3B-0 pos20 bipolar bias（−36 → +47） | regime 信号是真的，但 simple calibration 不够 |
| Step 3B-1 4×4 lookup holdout FAIL（2/6） | 离散 lookup 在 250 records 不稳，cell 不可跨窗迁移 |
| Step 3A-4 第三窗口扩到 380 records 仍 partial FAIL | 数据增加（130 records）改善但**不**直接解决 lookup 问题 |
| Step 3D-1 read-only regime diagnostics | regime feature（pos20 / diff / R4 signature）可被 read-only 暴露，但 4×4 离散化不是合适承载方式 |
| Step 2G-8B R4 narrower candidate NO-GO（42/42） | 不能靠 R4 切小通过 hard gate 三项门槛 |
| Step 2G-8C R4 H1/H2 gap +0.18 | regime-aware 必须引入；R4 触发条件本身缺 regime guard |
| Step 2G-7C dashboard 6-gate 仍 2 pass / 4 fail | hard exclusion 在 2023-2024 数据上系统性 NO-GO |
| 2026-01-01 之后 final test cutoff | 不能用 final test 调参 / 偷看 |

**结论**：
- 离散 lookup 路线已经**双重失败**
- 单纯加数据**不**能解决 regime sensitivity
- soft / display / sidecar 已经**全部走完**
- 需要**新的、连续的、regime-aware**的 calibration 框架

---

## 3. Step 3 restart 的目标

**Step 3 重启不是重启旧 4×4 lookup**。

### 3.1 是什么

Step 3 重启 = 重新设计 **regime-aware calibration / exclusion 框架**，
回答以下 4 个核心问题：

1. **什么时候 bullish overextension 真危险？**
   （在 ranging market / weak peer momentum / earnings vacuum 期间）
2. **什么时候被 bull regime 救活？**
   （在 sustained uptrend / strong peer confirmation / 重大 earnings
   shock 月）
3. **confidence 应如何被 regime 修正？**
   （high in bull regime ≠ high in ranging regime；需要 regime-aware
   downgrade / upgrade map）
4. **exclusion 何时只能 soft？**
   （永远；hard 只在 launch review 重新通过 6 gate 后才考虑）

### 3.2 不是什么

- **不**重做 simple calibration（已 FAIL）
- **不**重做原 4×4 lookup（双重 FAIL）
- **不**写离散桶规则（regime 信号是连续的）
- **不**直接写 calibration formula（先做 label / diagnostics / scope）
- **不**升级 04 / 05 / 07 required 字段
- **不**碰 2026 final test
- **不**把 R4 hard 化（与 Step 2G-8 launch review NO-GO 一致）
- **不**让 Gate 5 `protection_layer_connected` 自动 pass
- **不**改 `_PROTECTION_LAYER_CONNECTED` 常量

---

## 4. 不重做什么

| # | 不做 | 理由 |
|---|---|---|
| 1 | simple calibration | Step 3A 已证 inversion 仍存 |
| 2 | 4×4 lookup | Step 3B-1 / 3A-4 双重 FAIL |
| 3 | 直接写 calibration formula | 无 label / 无 validation protocol，公式必失败 |
| 4 | 升级 04 / 05 / 07 required | 与 Step 2G 全程边界冲突 |
| 5 | 触碰 2026-01-01 之后 final test | 永久封禁；偷看 = 自毁验证集 |
| 6 | 把 R4 hard 化 | Step 2G-8 launch review NO-GO + 2G-8B / 8C 加强证据 |
| 7 | 启用 `hard_exclusion_allowed` / `forced_exclusion` | 同上 |
| 8 | 让 `protection_layer_connected_for_gate` 翻 True | 与 Step 2G-8A v1 强不变量冲突 |

---

## 5. 推荐 Step 3 新路线（Step 3R-x 系列）

把"calibration restart"拆成 8 个**循序渐进**的子步骤，每一步都是**只读 /
设计 / sidecar**，**前一步未通过不进下一步**：

| Step | 范围 | 输出 | 是否动代码？ |
|---|---|---|---|
| **Step 3R-0** restart scope design | 把本文 launch review 收尾成 scope checkpoint；正式冻结 Step 3R 全程边界（不 hard / 不 required / 不 final test / sidecar-first） | `tasks/step_3r0_restart_scope_checkpoint.md` | ❌ 仅 markdown |
| **Step 3R-1** regime label design | 设计候选 regime label 的 schema：pos20 quartile / diff bucket / market trend window / AI bull regime flag / monthly shock flag / peer momentum confirmation / volatility compression。**只设计，不实现** | `tasks/step_3r1_regime_label_design.md` | ❌ 仅 markdown |
| **Step 3R-2** regime-aware R4/R-series diagnostics | 在 read-only diagnostics dashboard 中**新增**（不替换）regime label 切片视图：每个 regime label 下的 R4 / R-series fer / nb / paired 分布。所有 label 由 caller 注入；helper 是纯函数 | 新增 `services/regime_label_diagnostics.py` + tests + dashboard 字段；**不**改 `_is_r4_record` / `_build_exclusion_system` | ⚠️ **新增 read-only helper** |
| **Step 3R-3** continuous smoothing candidate | 用 logistic / kernel / spline 在连续 regime feature（pos20 / diff）上拟合一个**平滑曲线**替代 4×4 lookup；只读 simulator | 新增 `services/regime_smoothed_calibration.py`（pure function） + 测试 | ⚠️ **新增 read-only simulator** |
| **Step 3R-4** cross-window validation protocol | 设计**多窗口 holdout** 协议：W1 / W2 / W3 三窗口 + leave-one-window-out + cross-validation；明确"通过"标准 | `tasks/step_3r4_validation_protocol_design.md` | ❌ 仅 markdown |
| **Step 3R-5** calibration formula design | 在 3R-4 协议下，先在**设计文档**层冻结 formula shape（continuous / regime-aware / sidecar-only）；仍**不**实现 | `tasks/step_3r5_calibration_formula_design.md` | ❌ 仅 markdown |
| **Step 3R-6** read-only simulator | 实现 3R-5 设计的 formula 作为**纯函数 simulator**；不接 main pipeline；不写 DB | 新增 `services/regime_aware_calibration_simulator.py` + tests | ⚠️ **新增 read-only simulator** |
| **Step 3R-7** sidecar integration（仅 conditional） | 仅在 3R-6 通过 cross-window validation 后，将 simulator 输出接入 `extras.regime_aware_calibration_diagnostics.v1` sidecar；**仍 display-only**；不进 hard / required | 新增 dashboard / UI 字段；**不**升级 required；**不**改 hard | ⚠️ **read-only sidecar** |

**强制 gate**：每个 Step 3R-x 必须先通过 launch review，再进入下一步。
任何一步不过 → 整个 Step 3R 进入 NO-GO，Step 2G display 路线为最终
形态。

---

## 6. Regime label 初步设计（候选清单）

**只设计，不实现，不写公式**。Step 3R-1 应在以下候选中筛选 + 冻结
schema：

| # | label 候选 | 数据源 | 类型 | 为什么 |
|---|---|---|---|---|
| 1 | `pos20_quartile` | coded_data CSV | 离散（4 桶） | 已有 Step 3B 验证 monotonic bias |
| 2 | `pos20_continuous` | coded_data CSV | 连续 | 替代离散桶 |
| 3 | `avgo_minus_soxx_20d_bucket` | coded_data CSV | 连续 / 桶 | R4 的核心阈值变量 |
| 4 | `market_trend_window` | rolling SOXX / QQQ trend | 离散（uptrend / sideways / downtrend） | 解释 H1（震荡）vs H2（多头主升）gap |
| 5 | `ai_bull_regime_flag` | NVDA / SOXX 连续 N 月强势 | 二值 | 直接对应 Step 2G-8C 发现的 H2 gap |
| 6 | `monthly_earnings_shock_flag` | earnings calendar + 价格 | 二值 | 解释 2024-02 单月异常 |
| 7 | `peer_momentum_confirmation` | NVDA / SOXX 与 AVGO 同向连续 N 日 | 离散（strong / weak / mixed） | regime-aware confidence 修正基础 |
| 8 | `volatility_compression` | rolling stdev / range | 连续 | 区分爆发前夕 vs 平稳期 |

**Step 3R-1 不实现这些 label**；只在文档层：
- 选择哪些 label 进入 v1
- 各 label 的输入边界（数据源 / 时窗 / 范围）
- 各 label 的离散化 / 连续阈值候选
- 与 Step 2G 现有 metadata（`soft_metadata.signals[]` / R4 trigger
  context）的兼容性
- **明确禁止**：使用 2026-01-01 之后数据；任何 live data 调参

**Step 3R-2 才允许**实现 read-only diagnostics（仍是 sidecar，不进
主链）。

---

## 7. 新 validation 原则

Step 3B-1 / 3A-4 失败的核心教训：**双窗 holdout 不够 robust**。
Step 3R-4 必须采用**多窗口 + leave-one-out**协议：

### 7.1 时窗划分

| 窗口 | 起止 | 说明 |
|---|---|---|
| W1 | 2023-01-03 → 2023-?? | 震荡 + 周期反转期；与 Step 3A-3 second window replay 一致 |
| W2 | 2023-12-?? → 2024 早期 | AI bull rally 起点；含 2024-02 NVDA-earnings shock |
| W3 | 2024 中后期 | sustained uptrend；与 Step 3A-4 third window replay 一致 |
| W4 | 2025-01 → 2025-12 | **未来扩展窗口**（前提：Step 2G-8D extend replay coverage 完成；不触碰 2026-01-01 之后） |
| **不可触碰** | **2026-01-01 → ∞** | **final test set；永久封禁** |

### 7.2 协议要求

| # | 要求 |
|---|---|
| 1 | **至少 3 窗口**（W1 + W2 + W3）才允许做 holdout；4 窗口（含 W4）后才允许 leave-one-window-out |
| 2 | **双向 holdout**：每个窗口都要做"design"和"holdout"两个角色 |
| 3 | **多 metric**：FER / NB / monotonicity / coverage / direction unchanged / robustness 至少 6 项 |
| 4 | **regime label 必须 cross-window stable**：每个 label 在 W1/W2/W3 上都有 ≥ 10 paired samples，且 fer/nb 不能爆炸 |
| 5 | **任何步骤都不能用 final test data 调参**；validation 在 ≤ 2025-12-31 数据上完成 |
| 6 | **通过的标准**：6 项中至少 5 项 PASS（Step 3B-1 仅 2/6 PASS 是失败基线） |
| 7 | **失败 = 不进下一步**；先回到 3R-1 / 3R-2 改 label，或回到 3R-3 改 smoothing |

### 7.3 与 Step 2G-8D 的关系

Step 2G-8D extend replay coverage（2024-08 → 2025-12）是 Step 3R-4
的**前提条件**：
- 没有 W4 数据 → leave-one-window-out 不可信
- W3 单窗口 holdout 已被 Step 3A-4 证明 partial-FAIL
- Step 3R-4 必须在 W4 完成后才能进入 final validation

**Step 3R-0 ~ Step 3R-3 不依赖 W4**；可在当前 380 records / 286 paired
上启动。

---

## 8. 与 Step 2G 的关系

### 8.1 Step 2G 仍保留为 display / diagnostics

Step 2G 已建成的 sidecar 体系（soft_metadata.v1 /
anti_false_exclusion_display.v1 / protection_layer_diagnostics.v1
/ Step 2G-7C dashboard aggregate）**继续保留**，**不**因 Step 3 重启
而拆除。

### 8.2 Step 3R 不能绕过 Step 2G hard gate

| 边界 | 说明 |
|---|---|
| Step 2G-7C dashboard 6-gate | Step 3R 输出**不**改变其判定逻辑；6-gate 仍由 baseline / R4 / holdout 决定 |
| `hard_exclusion_allowed` 永远 False | Step 3R 不解封 |
| `protection_layer_connected_for_gate` 永远 False | Step 3R 不解封 |
| 04 / 05 / 07 required schema | Step 3R 不升级 |
| `_PROTECTION_LAYER_CONNECTED = False` | Step 3R 不改 |

### 8.3 Step 3R 输出的归宿

如果 Step 3R 全部通过：
- 输出**作为 sidecar** 接入 `extras.regime_aware_calibration_diagnostics.v1`
- 不进入 hard decision
- 不写 04 required
- Predict / Review UI 子节渲染（与 Step 2G-7A AFX / 2G-8A 保护层
  并列）
- Step 2G-7C dashboard aggregate 新增字段（与 8A.3 节奏一致）

如果 Step 3R 任意阶段不通过：
- 整个 Step 3R 进入 NO-GO
- Step 2G display 路线为系统最终形态
- 进入"等更多 replay 数据 / 等 final test"模式

### 8.4 Step 2G 的 AFX / protection diagnostics 可作为输入证据

- AFX 5 个 protective findings → 可被 Step 3R-2 regime diagnostics
  作为证据维度（per-prediction）
- Protection diagnostics 2 个 guard → 可被 Step 3R-4 validation
  protocol 作为 cross-window 监控指标
- 但**不是** Step 3R 的硬决策输入

---

## 9. 允许启动的任务

| Step | 范围 | 是否动代码 |
|---|---|---|
| **Step 3R-0** restart scope checkpoint | 把本文 launch review 内容固化进 checkpoint；冻结全程边界 | ❌ markdown |
| **Step 3R-1** regime label design | §6 候选 label 筛选 + 冻结 schema | ❌ markdown |
| **Step 3R-2** read-only regime diagnostics | 新增 `services/regime_label_diagnostics.py`（pure function）+ tests + dashboard 字段 | ⚠️ read-only helper |
| **Step 3R-4** validation protocol design | §7 三窗口协议 + 通过标准；先不依赖 W4 | ❌ markdown |

**节奏建议**：
- 先 3R-0 + 3R-1 + 3R-4（三份纯 markdown），完成 launch review →
  scope checkpoint → label design → validation protocol design
- 再 3R-2（首个动代码的步骤；纯 read-only helper）
- 期间 Step 2G-8D extend replay coverage **可并行启动**（与 Step 3R
  解耦；为 Step 3R-4 提供 W4 数据）

---

## 10. 禁止启动的任务

**硬禁止**（违反任意一项 → 立刻停止）：

| # | 禁止 | 理由 |
|---|---|---|
| 1 | hard exclusion implementation | Step 2G-8 / 8B / 8C 全部 NO-GO |
| 2 | forced exclusion implementation | 同上 |
| 3 | required 字段升级（04 / 05 / 07） | 与 Step 2G 全程边界冲突 |
| 4 | live trading / broker 接入 | 与 mission 定位（research agent）冲突 |
| 5 | calibration formula implementation | 必须先过 Step 3R-5 design |
| 6 | DB schema migration | Step 3R 全程 sidecar；不持久化 |
| 7 | 使用 2026 final test 数据调参 | 永久封禁；偷看 = 自毁 final test |
| 8 | 让 `_PROTECTION_LAYER_CONNECTED` 翻 True | 与 Step 2G-8A v1 强不变量冲突 |
| 9 | 让 `hard_gate_status.protection_layer_connected` 自动 pass | 同上 |
| 10 | 改 `final_direction` / `final_projection` / `simulated_trade` / `no_trade` | Step 2G 全程"不改主推演方向"边界 |
| 11 | 改 `_build_exclusion_system` / `run_predict` / `scanner` 主链 | 与 Step 2G "sidecar-only" 边界一致 |
| 12 | 跳过 cross-window validation 直接 sidecar | Step 3B-1 / 3A-4 已证 lookup 在单窗 holdout 上 FAIL |

---

## 11. 成功标准

未来 Step 3R-7（如果走到这一步）必须满足：

| # | 标准 | 来源 |
|---|---|---|
| 1 | **cross-window stable**：W1 / W2 / W3 / W4 上 fer / nb / monotonicity 全部不崩 | Step 3R-4 协议 |
| 2 | **FER / NB 改善**：相对 R4_full（fer 0.3235 / nb +0.0219）显著降低 fer + 提高 nb；具体阈值在 Step 3R-4 设计 | 继承 Step 2G-7C / 8B 阈值 |
| 3 | **不牺牲 survival cases**：R4 触发但 correct 的 survival cases 在 sidecar 中仍可见，不被静默 | Step 2G-6C / 7A 一致 |
| 4 | **不偷看 2026 final test** | 永久禁止 |
| 5 | **full pytest 0 failed** | 与现状 2604 / 0 failed / 10 skipped 持平或扩张 |
| 6 | **sidecar-first**：所有输出仍在 `extras.*` 节点；不写 04 / 05 / 07 required | Step 2G 全程边界 |
| 7 | **每一步通过 launch review 才能进 formula** | Step 3R-x → 3R-(x+1) 的硬 gate |

---

## 12. 推荐下一步

按优先级：

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **本文 commit + Step 3R-0 restart scope checkpoint** | 把 launch review 进 main，再写一份 scope checkpoint 把全程边界正式固化 | **本轮 / 下一轮** |
| 2 | **Step 3R-1** regime label design | §6 候选筛选 + schema 冻结；纯 markdown | **高** |
| 3 | **Step 3R-4** validation protocol design | §7 三窗口协议；纯 markdown；可与 #2 并行 | **高** |
| 4 | **Step 2G-8D** extend replay coverage（2024-08 → 2025-12，**不**触碰 2026） | 数据层；为 Step 3R-4 提供 W4 | **高**（与 Step 3R 解耦，可并行） |
| 5 | **Step 3R-2** read-only regime diagnostics（首个动代码步） | helper + tests + dashboard 字段 | 中（在 #2 / #3 通过后启动） |
| 6 | **Step 3R-3** continuous smoothing candidate | read-only simulator；纯函数 | 中 |
| 7 | **Step 2G-8E** other R-series candidates | 离开 R4 探索；前提是 Step 3R 至少进到 3R-2 | 中-低 |
| 8 | **不推荐** 直接实现 calibration formula | 跳过 Step 3R-1 / 3R-4 必失败 | **❌** |
| 9 | **不推荐** 直接实施 R4 hard | Step 2G-8 launch review + 8B / 8C 三重 NO-GO | **❌** |
| 10 | **不推荐** 让 Gate 5 / Gate 6 自动 pass | 与 Step 2G-8A v1 / 8C 一致 | **❌** |
| 11 | **不推荐** 升级 04 required schema | Step 2G 全程边界 | **❌** |

**关键判断**：
- Step 3 重启**不应**急于动代码
- Step 3R-0 / 3R-1 / 3R-4 **三份 markdown** 应该是首要交付物
- 在 markdown 设计冻结之前进入 helper 实现 = 重蹈 Step 3B-1 覆辙
- Step 2G-8D extend replay 是 Step 3R-4 的硬依赖，应**并行启动**

---

## 13. 严守边界

本文是**纯 launch review markdown**：

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
- ❌ 没运行 `pytest`（本轮纯文档；测试基线维持 commit `e0ce108` 时
  的 2604 / 0 failed / 10 skipped）
- ✅ 只新增 1 份 markdown launch review 文档（本文件）
