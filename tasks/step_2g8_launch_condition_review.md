# Step 2G-8 — Launch Condition Review

> **Launch condition review document, not implementation.** 本文档审查
> Step 2G-8 实施任务（升级 04 required `anti_false_exclusion_triggered=True`
> / 启用 hard exclusion / 启用 forced exclusion）当前是否有资格启动。
> 基于 Step 2G-7C aggregate dashboard 的真实数据 + 6 项 hard gate 当前
> 状态做 go / no-go 判断，明确**允许启动**和**禁止启动**的子任务清单。
>
> 本轮**不动任何代码**：不改 `predict.py` / `run_predict` /
> `scanner.py` / `prediction_store.py` / `app.py` / `ui/*` /
> `services/*` / 任何 builder / DB schema 中的任何一处。

## 1. 背景

- **Step 2G-7C** aggregate dashboard checkpoint（commit `b9ed364`）
  已**冻结** hard gate 6 项当前状态：**2 pass / 4 fail**
- **Step 2G-8** **不是**自动进入 implementation —— Step 2G 设计文档
  §6 红线明确：任何 04 required 升级 / hard 启用 / forced 启用必须
  **6 项 gate 全部通过 + anti-false-exclusion 保护层接入 + Step 3
  calibration 重启 holdout 通过**
- 必须**先审查 6 项 gate**，识别哪些 fail 可独立解决、哪些需更大
  样本 / Step 3 calibration 重启
- Step 2G-7C aggregate baseline：
  - R4 paired=34 / correct=11 / wrong=23 / fer=0.3235 / nb=+0.0219 /
    holdout=FAIL
  - residual paired=47 / correct=23 / acc=0.489 / nb=−0.001 / holdout=FAIL
  - hard_exclusion_allowed = false（六重锁定）

## 2. 当前 hard gate 状态

| # | gate | status | current value | required value |
|---|---|---|---|---|
| 1 | `total_paired_ge_90` | **pass** | 286 | ≥ 90 |
| 2 | `candidate_paired_ge_30` | **pass** | R4=34 | ≥ 30 |
| 3 | `false_exclusion_rate_lte_0_10` | **fail** | **0.3235** | ≤ 0.10 |
| 4 | `net_benefit_gte_0_05` | **fail** | **+0.0219** | ≥ +0.05 |
| 5 | `protection_layer_connected` | **fail** | false（4 模块全离线）| true |
| 6 | `cross_window_holdout_pass` | **fail** | FAIL（Step 3A-4 / 3B-1）| PASS |

**结论摘要**：2 项样本量 gate pass，4 项质量 / 保护层 / 跨窗口
gate fail。

## 3. Gate 1 / 2：样本量是否足够

- **`total_paired_ge_90`**：✅ pass（286 ≥ 90）—— 充足
- **`candidate_paired_ge_30`**：✅ pass（R4=34 ≥ 30）—— **勉强够**

**评估**：
- 总 paired 充足，calibration_ready=true
- R4 candidate paired (34) 仅刚过阈值 4 条；这是统计意义上的最低
  样本量，**不足以**支持 04 / 05 / 07 required 字段升级（升级会改
  `_build_exclusion_system` 的 5 个 stub 字段，影响所有未来 prediction
  ——决策影响范围远大于 34 条 historical 样本能支撑的统计置信度）
- residual paired (47) 略好但仍偏少
- **结论**：样本量**不是当前主 blocker**，但**也不是强支持** ——
  如果其他 4 项 gate 都通过，34 条仍偏小；任何 hard / required 升级
  应等到至少 50-60 条 R4 paired

## 4. Gate 3：`false_exclusion_rate` gap

- **当前**：0.3235（R4 correct=11 / paired=34）
- **目标**：≤ 0.10
- **gap 量化**：要达到 fer ≤ 0.10，给定 paired=34，需 `correct ≤ 3`
  （3/34 ≈ 0.088）；当前 correct=11，**多出 8 个误杀样本**
- **替代路径**：保持 correct=11 不变，需扩大 wrong 样本到 paired ≥
  110（即 76 条额外 wrong R4 样本）—— 现实中 R4 触发频率低，等到
  paired=110 需要约 380 × (110/34) ≈ 1230 条新 replay；按当前
  Step 2F-4d-2 130-pair window 的速度，约**3-4 个 130 window**
  数据补全后才可能自然达到

**这不是小幅优化能解决的**：
- 不能简单"调阈值"——R4 阈值 5.0 / 0.62 已是数据驱动选定，
  收紧条件会让 paired 急剧下降到 < 30，反而 fail Gate 2
- 必须靠**二级过滤 / 保护层识别 survival cases**：把那 11 个
  correct 样本与 23 个 wrong 样本区分开
- 候选思路：peer_path_risk_direction × R4 子切片 / 上一日波动 ×
  R4 / market regime 的更精细 lookup —— 这些都需要**read-only
  研究**先做（Step 2G-8B）

## 5. Gate 4：`net_benefit` gap

- **当前**：+0.0219
- **目标**：≥ +0.05
- **gap**：约 +0.0281（需多出 +2.81 pp 整体 accuracy 提升）
- **关键约束**：residual `net_benefit = −0.001`（**负值**）→ 扩大
  R4 范围（用 residual 替代 R4）会让整体 accuracy **不升反降**
- **结论**：不能靠"放宽"R4 → 必须**收窄**到更精细子切片，让
  排除后的 `correct_when_excluded` 数字下降快于 `paired_when_excluded`

**与 Gate 3 同源**：解决 Gate 3 的二级过滤设计很可能同时缩小 Gate 4
gap —— 移除 8 个误杀样本意味着：
- correct 从 11 → 3
- paired 从 34 → 26
- accuracy 从 0.324 → 0.115（excluded 全是 wrong）
- 在 baseline_paired=286 / baseline_correct≈140 下，post-exclusion
  paired=260 / correct=137 / accuracy=0.527
- net_benefit ≈ 0.527 − 0.490（baseline）= +0.037 —— 仍不够 0.05
  但接近

→ **Gate 3 + Gate 4 必须协同**，不能独立解决；属于同一组研究任务

## 6. Gate 5：`protection_layer_connected`

- **当前**：false（4 个保护层模块全离线）
- **4 个模块**：
  - `services/anti_false_exclusion_audit.py` —— 离线 audit
  - `services/big_up_contradiction_card.py` —— 仅 UI / `ui/big_up_contradiction_card.py`
  - `services/big_down_tail_warning.py` —— 离线告警
  - `services/exclusion_reliability_review.py` —— 仅 UI / `ui/exclusion_reliability_review.py`
- **这是可独立推进的 blocker** —— 与 Gate 3 / 4 / 6 完全解耦：
  接入"保护层接入设计"不需要等 R4 fer 改善 / Step 3 calibration 重启
- **可启动一个低风险子任务**：Step 2G-8A protection-layer connection
  design
  - **纯文档** spec
  - 决定 4 个候选模块挑哪个接入、接入时机（Pre-decision / post-
    decision audit）、接入后写入哪个字段
  - **只能 display / diagnostics**：接入位置不能写 04 required 字段
  - 实施实现等到 Gate 3 / 4 / 6 也有缩小路径后再启动

**结论**：可以**设计**（Step 2G-8A 纯文档）；**不可启用 hard**
（即使 Gate 5 单独 pass，Gate 3 / 4 / 6 仍 fail）

## 7. Gate 6：`cross_window_holdout`

- **当前**：FAIL（Step 3A-4 third-window replay holdout 还是 partial
  fail；Step 3B-1 lookup holdout 直接 fail）
- **根因**：Step 3A-4 checkpoint / Step 3B-1 checkpoint 已说明 ——
  R4 / pos20 regime feature 在 in-sample 表现 over-bullish bias，
  但 holdout window 上**bias 方向不稳定**（有时反向）
- **不能在 2G 内单独解决**：
  - 2G-7C aggregate 仅显示 holdout=FAIL；不改 calibration
  - 任何让 holdout pass 的努力都是 **Step 3 calibration / regime-aware
    logic 重启**范围（Step 3B-2 / 3C 已被冻结）
  - 即使做更细的 Gate 3 / 4 二级过滤设计，也只能在 in-sample 上验证；
    holdout 验证仍需要 cross-window replay
- **结论**：这是 blocking hard 的**最高等级 gate** —— 在 Step 3
  calibration 系列重启之前**无法独立解决**

## 8. Blocker 分类

| blocker | can solve inside 2G? | gap 大小 | recommended action |
|---|---|---|---|
| **Gate 3** false_exclusion_rate too high | **partly**（设计研究层面）| 大（需移除 8 个 correct 样本，或 76 条额外 wrong）| Step 2G-8B narrower R4 candidate research（**只读诊断**；不改 hard）|
| **Gate 4** net_benefit insufficient | **partly**（与 Gate 3 同源）| 中（+0.0281）| 同 Gate 3 —— 同一组研究任务 |
| **Gate 5** protection layer not connected | **yes**（独立可解耦） | spec 设计成本低 | Step 2G-8A protection-layer connection design（**纯文档**）|
| **Gate 6** holdout FAIL | **no / mostly no** | 极大（需 Step 3 重启）| **wait for Step 3 calibration restart 或更大 cross-window 数据**；可启动 Step 2G-8C holdout gap analysis（只读对比）做诊断，但不解决 |

## 9. 是否值得启动 Step 2G-8 implementation

**明确结论**：

- ❌ **不建议**启动 hard / required implementation —— Gate 3 / 4 / 6
  全部 fail，Gate 5 单项 pass 也不够
- ❌ **不建议**写 04 required `anti_false_exclusion_triggered=True` —— v1
  spec 强约束保护层接入是前提
- ❌ **不建议**改 04 `exclusion_level` / `exclusion_sources` /
  `exclusion_reasons` / `forced_exclusion` 任何 stub 字段
- ❌ **不建议**改 05 `confidence_system` 4 个 score 字段 / `event_score`
  /  `confidence_level` 等
- ❌ **不建议**改 07 `simulated_trade` / `no_trade` 策略边界
- ✅ **可以启动** Step 2G-8A design-only 子任务（保护层接入设计；
  纯文档；不实施）
- ✅ **可以启动** Step 2G-8B / 2G-8C read-only research / diagnostics
  子任务（narrower candidate / holdout gap analysis；不改 contract）
- 目标：**保护层接入设计 + 二级过滤研究**，**不是** hard 启用

## 10. 允许启动的子任务

| # | 子任务 | 范围 | 性质 |
|---|---|---|---|
| 1 | **Step 2G-8A** protection-layer connection design | 纯文档；4 个候选模块挑一个写接入设计；接入位置只能 `extras.protection_layer_status`（仿 Step 2G-7C dashboard 的 sidecar 模式）；不改 04 required；不改 `_build_exclusion_system` | **设计**（无代码改动）|
| 2 | **Step 2G-8B** narrower R4 candidate research | 只读诊断；用现有 read-only 工具（regime_diagnostics_dashboard / contract_calibration_inputs）+ ad-hoc sqlite 找能降低 fer 的二级条件（peer_path × R4 / 上日波动 × R4 / market regime × R4）；输出"哪个二级 split 能让 R4 fer < 0.10 且 paired ≥ 30"的判定 | **read-only research**（无代码改动）|
| 3 | **Step 2G-8C** holdout gap analysis | 只读；对比 in-sample window vs Step 3A-4 third-window replay 的 R4 表现；量化"holdout bias 方向反转的发生频率与触发条件"；输出"holdout fail 是否能在不重启 Step 3 calibration 的前提下缩小"判定 | **read-only diagnostics**（无代码改动）|
| 4 | **Step 2G-7D** review_log free-text design（可选）| 纯文档；设计 4 象限归因 + 5 finding 写入 `review_log.confidence_note` / `watch_for_next_time` free-text；**不改** required；让 review 历史可查询累计 metadata + finding | **设计**（无代码改动）|

## 11. 禁止启动的任务

下列任务**不允许**启动（与 Step 2G 设计文档红线 + 本 review 结论
一致）：

- ❌ hard exclusion implementation（任何形式）
- ❌ forced_exclusion implementation
- ❌ `anti_false_exclusion_triggered=True` required 字段写入
- ❌ 04 `exclusion_system` 5 个 required 字段升级（exclusion_level
  / exclusion_sources / exclusion_reasons / forced_exclusion /
  anti_false_exclusion_triggered）
- ❌ 05 `confidence_system` required 字段改写（4 个 score 字段 /
  `event_score` / `confidence_level` / `total_confidence` /
  `confidence_reason`）
- ❌ 07 `simulated_trade` / `no_trade` 策略边界改写（trade_action
  / trade_direction / 三个 condition 字段 / suggested_position_size /
  trade_engine_enabled）
- ❌ save-time DB enrichment（Step 2G-6B.1 候选 C；写 DB / migration
  成本高，已暂不推荐）
- ❌ trading API integration / `longbridge` / `broker` /
  `paper_trade` 接入
- ❌ 让任何 sidecar / display 写入 04 required 字段
- ❌ Step 3B-2 / 3C calibration formula 实施（Step 3 calibration 系列
  仍冻结）

## 12. 2026 final test cutoff

- 本 review **不**使用 2026-01-01 之后的数据
- 当前 6 项 gate 评估全部基于 2023-01-03 → 2024-08-02 replay window
  （`metrics_window.analysis_date_max="2024-08-02"`）
- **2026 之后仍是最终测试集** —— 任何让 gate pass 的努力**不得**
  跨过 cutoff 看 final test 数据
- Step 2G-8B narrower candidate research 必须遵守同样 cutoff
- 即使将来 R4 fer 在 final test window 上看似更低，也**不**能据此
  启动 hard —— hard gate 评估必须基于 cutoff 之前数据

## 13. 最终结论

| 项目 | 决策 |
|---|---|
| **Step 2G-8 full implementation**（启用 hard / forced / 升级 04 required）| **NO-GO** |
| **Step 2G-8A protection-layer connection design**（纯文档）| **GO**（独立可解耦的 blocker；低风险）|
| **Step 2G-8B narrower R4 candidate research**（只读）| **conditional GO**（值得研究，但不能据此启用 hard）|
| **Step 2G-8C holdout gap analysis**（只读）| **conditional GO**（诊断价值高，结果不能据此启用 hard）|
| **Step 2G-7D review_log free-text design**（可选 / 纯文档）| **conditional GO**（让 review 历史可查询；与 hard gate 解耦）|
| **hard / required upgrade** | **NO-GO**（4 项 gate fail；六重锁定不解除）|

**核心判断**：
- Step 2G-8 当前**不具备启动 implementation 的资格**
- 但可以做**3-4 个低风险的设计 / 研究子任务**为未来铺路
- 这些子任务**不**改变 hard gate 状态；hard 仍永远禁止
- 任何子任务的产出都**不**触发 04 / 05 / 07 required 字段升级

## 14. 下一步建议

按推荐优先级：

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **Step 2G-8A protection-layer connection design** | 纯文档；4 个候选保护层模块挑一个的接入方案；不改 required；不改 `_build_exclusion_system` | **高**（可独立解耦的 Gate 5；为未来 hard 启动铺路；零代码风险）|
| 2 | **Step 2G-8B narrower R4 candidate research** | 只读 ad-hoc sqlite + read-only 工具研究；找能降低 fer 的二级条件 | 中-高（与 Gate 3/4 同源；可能解锁 R4 子切片但不能直接启用 hard）|
| 3 | **Step 2G-8C holdout gap analysis** | 只读对比 in-sample vs holdout window；量化 bias 方向反转 | 中（让 Step 3 calibration 重启时有更精确的目标）|
| 4 | **Step 2G-7D review_log free-text design**（可选）| 让 review 历史可查询累计 metadata + finding；不改 required | 中（与 hard gate 解耦） |
| 5 | **Step 2G-7E dashboard UI integration**（可选 UX 增强）| 把 Step 2G-7C aggregate JSON 渲染到 Streamlit dashboard | 中-低 |
| 6 | **不建议**启动 Step 2G-8 hard implementation | 4 项 gate fail；本 review 已 NO-GO | — |
| 7 | **不建议**改 `run_predict` / `prediction_store` 主链 | 当前 sidecar + UI display + Review attribution + 保护层显示 + dashboard aggregate 已是最大可行边界 | — |

**强制约束**：Step 2G-8A / 2G-8B / 2G-8C / 2G-7D / 2G-7E 实施时仍要
遵守：
- 不改 04 / 05 / 07 required 字段
- 不改 `review_log` required 字段（free-text 字段写入需独立 design）
- 不改 `run_predict` 主链
- 不写 DB（除非另立 DB hygiene 任务）
- 不出现 16 forbidden words（页面级）/ 19 forbidden words（AFX 内部）
- `hard_exclusion_allowed` 永远 `False`

## 15. 严守边界

- ❌ 本文档**只是** launch condition review / decision document
- ❌ 没改任何代码
- ❌ 没新增任何测试
- ❌ 没写 DB
- ❌ 没改 DB schema
- ❌ 没接 `yfinance` / `requests` / 任何网络
- ❌ 没接 trading API / `longbridge` / `broker` / `paper_trade`
- ❌ 没改 `predict.py` / `scanner.py` / `prediction_store.py`
- ❌ 没改 `projection_output_adapter.py` / `projection_output_contract.py`
- ❌ 没改 `regime_diagnostics_dashboard.py` / `soft_metadata_simulator.py` /
  `soft_metadata_renderer.py` / `soft_metadata_injection.py` /
  `regime_features_builder.py` / `soft_metadata_baseline_cache.py` /
  `anti_false_exclusion_display.py` / `anti_false_exclusion_dashboard.py` /
  `predict_tab.py` / `review_tab.py`
- ❌ 没改任何 builder（`_build_exclusion_system` /
  `_build_confidence_system` / `_build_simulated_trade` / 任何其他）
- ❌ 没改 `app.py` / 任何其他 `ui/*` 模块
- ❌ 没升级 04 / 05 / 07 任何 required 字段
- ❌ 没启用 `hard` / `forced_exclusion` /
  `anti_false_exclusion_triggered`
- ❌ 没接 4 个 anti-false-exclusion 离线模块到主链
- ❌ 没改 `final_projection` / `confidence_score` / `simulated_trade` /
  `no_trade`
- ❌ 没改 `review_log` 任何 required 字段
- ❌ 没触碰 2026-01-01 之后 final test range
- ❌ 没运行 replay / 没新写 replay 行
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` /
  `avgo_agent.db.backup_*`
- ✅ 只新增 1 份 markdown launch condition review（本文件）
