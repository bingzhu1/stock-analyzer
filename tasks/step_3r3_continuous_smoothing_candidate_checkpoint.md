# Step 3R-3 — Continuous Smoothing Candidate Checkpoint

> **状态固化文档（continuous smoothing candidate checkpoint），不实现，不改代码，不写 DB，不运行 replay。**
> 本文档**冻结** Step 3R-3 design（commit `65fe411`）的：candidate
> sigmoid shape、9 raw_features 输入、`continuous_smoothing_candidate.v1`
> 输出 schema、risk_bucket 草案、validation record mapping、与 R4 /
> hard / required / 2026 final test range 的衔接边界、validation plan
> 子步骤、禁止事项。
>
> 本轮**不动任何代码**：不改 `predict.py` / `run_predict` /
> `scanner.py` / `prediction_store.py` / `app.py` / 任何 `ui/*` /
> `services/*`（含 `services/regime_labels_builder.py` /
> `services/regime_validation_helper.py`）/ `scripts/*` / 任何 builder /
> DB schema / 任何 test 中的任何一处。
>
> **本文不实现 candidate generator、不选系数、不选 candidate_threshold、
> 不跑 validation、不读 W4 results、不写 DB、不接 trading API**；只在
> markdown 层固化 candidate 状态，作为后续 Step 3R-3.1 read-only
> candidate generator implementation / Step 3R-4.3 adapter 的强制 gate。

---

## 1. 当前完成状态

- **Step 3 calibration restart launch review** 已完成并进入 main
  （commit `b8c781d`）
- **Step 3R-0** restart scope checkpoint 已完成并进入 main（commit
  `1b7288e`）
- **Step 3R-1** regime label design + checkpoint 已完成并进入 main
  （commits `a8df93a` / `8d4fe8f`）
- **Step 3R-2** read-only regime labels builder + checkpoint 已完成并
  进入 main（commits `e2a681b` / `db7618b`）
- **Step 3R-4** cross-window validation protocol design + checkpoint
  已完成并进入 main（commits `a58aad4` / `abe3ba2`）
- **Step 2G-8D** extend replay coverage 系列已收官（commits `170617c`
  ... `4bdd782`）；W4 paired_outcomes=353 / `final_test_touched=false`
- **Step 3R-4.1** 4-fold validation helper design + checkpoint 已完成
  并进入 main（commits `8e27254` / `295ccdd`）
- **Step 3R-4.2** read-only validation helper + checkpoint 已完成并
  进入 main（commits `c669c2f` / `5e58fee`）
- **Step 3R-3** continuous smoothing candidate design 已完成并进入 main
  （commit `65fe411`）
- 本 checkpoint **固定**：
  - candidate sigmoid shape + 5 系数方向
  - 9 raw_features 输入（来自 3R-1 `regime_labels.v1`）+ v1 不引入清单
  - `continuous_smoothing_candidate.v1` 10 字段 + 8 不允许字段
  - risk_bucket 4 桶草案 + 5 项强约束
  - validation record mapping 8 字段 + 6 项强约束
  - 与 R4 / hard / required / 2026 边界
  - validation plan 子步骤
- **Step 3R-3.1 read-only candidate generator implementation 仍未启动**：
  本 checkpoint 是 3R-3.1 之前的强制 gate

---

## 2. 当前 main 状态

- main 最新 commit：**`65fe411`**
- commit message：`docs(contract): Step 3R-3 continuous smoothing candidate design`
- 上游：`origin/main` 已同步
- 测试基线：**2722 passed / 0 failed / 10 skipped / 26 warnings /
  94 subtests**（与 commit `c669c2f` 一致；本 checkpoint 阶段无代码
  改动 → 基线不变）

本步骤新增文件（已 merge 到 main）：

| 路径 | 类型 | 说明 |
|---|---|---|
| `tasks/step_3r3_continuous_smoothing_candidate_design.md` | 新增 | 16 节、450 行；candidate sigmoid shape + 9 raw_features + `continuous_smoothing_candidate.v1` schema + validation plan |

本 checkpoint 文档（即本文件）尚未 commit；本轮只写文档、**不**
commit / push。

| 项 | 是否触碰 |
|---|---|
| 改代码 | ❌ 否 |
| 写 DB | ❌ 否 |
| 跑 replay | ❌ 否 |
| 改 services/* / scripts/* / tests/* | ❌ 否 |
| 改 DB schema | ❌ 否 |
| 接 yfinance / 网络 | ❌ 否 |
| 接 trading API | ❌ 否 |
| 触碰 2026 final test | ❌ 否 |

---

## 3. Candidate shape

```
risk_score = sigmoid(
    a * pos20
  + b * avgo_minus_soxx_20d
  - c * peer_5d_aligned_pct
  - d * market_trend_strength
  + e * monthly_shock
)
```

| 项 | 方向 | 解释 |
|---|---|---|
| `+ a * pos20` | 正向 | pos20 越高（接近 20-day 高点），bullish overextension 风险越高 |
| `+ b * avgo_minus_soxx_20d` | 正向 | AVGO 跑赢 SOXX 越多，relative-strength 拉伸越大，mean-reversion 风险越高 |
| `- c * peer_5d_aligned_pct` | 负向 | peer 同向越强（NVDA / SOXX / QQQ 5d 共同上涨），sustained-momentum 越确认，**风险下降** |
| `- d * market_trend_strength` | 负向 | sustained bull regime 越强（QQQ slope > 0 + 低 drawdown），**风险下降**（与 Step 2G-8C 教训一致） |
| `+ e * monthly_shock` | 正向 | shock month / breakout month 不确定性高，风险加成 |

`risk_score ∈ [0, 1]`（sigmoid 输出域）。

---

## 4. 明确未选择的东西

| # | 未选择 | 解封步骤 |
|---|---|---|
| 1 | 系数 `a` / `b` / `c` / `d` / `e` | Step 3R-3.1 实施时锁定（一次只锁一个 variant） |
| 2 | `candidate_threshold` | Step 3R-3.3 4-fold validation 后；不允许用 4-fold 数据反推 |
| 3 | `risk_bucket` final thresholds（0.35 / 0.60 / 0.80） | 同 1；调阈值必须经 launch review |
| 4 | `market_trend_strength` 段阈值（0.015 / 0.05 / 0.10） | 同 1 |
| 5 | 4-fold validation 跑动 | Step 3R-3.3 |
| 6 | 读 W4 results | Step 3R-4.3 adapter 实施时（与 W4 manifest gate 一致） |
| 7 | 进入 production decision | 永远不在 candidate 层；wiring 必须经 launch review |
| 8 | 产生 formula | Step 3R-5（必须先过 3R-3.3 + 3R-4.2 helper acceptance） |

---

## 5. 输入特征

均来自 Step 3R-1 `regime_labels.v1` raw_features（**v1 不引入新字段**）：

| 特征 | 单位 |
|---|---|
| `pos20` | decimal `[0, 1]` |
| `avgo_minus_soxx_20d` | decimal fraction |
| `peer_confirm_count` | int 0..3 |
| `peer_5d_aligned_pct` | decimal `[0, 1]` |
| `qqq_60d_slope_per_month` | decimal/月 |
| `qqq_60d_drawdown` | decimal `[0, 1]` |
| `soxx_60d_slope_per_month` | decimal/月 |
| `monthly_return_pct` | decimal |
| `monthly_max_abs_daily_return` | decimal |

### 5.1 v1 不引入

| 不引入 | 理由 |
|---|---|
| earnings calendar 字段 | 已通过 `monthly_context_regime` 的 `earnings_month` bucket 间接表达 |
| 2026 data | 永久封禁；`final_test_cutoff` hard stop |
| outcome leakage 字段（`actual_*` / `direction_correct` / `review_*`） | 与 3R-1 §7 / 3R-2 §7 anti-lookahead 8 项不变量一致 |
| scan / match / encoder 内部字段 | 与 Step 2G "sidecar-only" 边界一致 |
| production wiring 字段（`hard` / `forced_exclusion` / required） | 永远不在 candidate 层 |

---

## 6. output schema

```json
{
  "schema_version": "continuous_smoothing_candidate.v1",
  "as_of_date": "YYYY-MM-DD",
  "data_cutoff_date": "YYYY-MM-DD",
  "candidate_name": "continuous_smoothing_v1",
  "risk_score": 0.42,
  "adjustment_score": 0.58,
  "risk_bucket": "low | medium | high | extreme",
  "features_used": {
    "pos20": 0.81,
    "avgo_minus_soxx_20d": 0.077,
    "peer_5d_aligned_pct": 0.40,
    "market_trend_strength": 0.6,
    "monthly_shock": 0.0
  },
  "warnings": [],
  "final_test_refusal": false
}
```

### 6.1 不允许字段

| 禁止字段 | 理由 |
|---|---|
| `gate_status` | candidate 是数据层；validation 由 3R-4.2 helper 产出 `regime_validation_report.v1` |
| `validation_passed` | 同上 |
| `overall_status` | 同上 |
| `hard_*`（`hard_exclusion_allowed` / `hard_gate_status` 等） | candidate 永不直接驱动 hard 路径 |
| `simulated_trade` | 与 v1 / 3R-0 / 3R-4 一致 |
| `no_trade` | 同上 |
| `final_direction` | 同上 |
| `final_projection` | 同上 |

### 6.2 schema 不变量

| 字段 | 不变量 |
|---|---|
| `schema_version` | 总是 `"continuous_smoothing_candidate.v1"` |
| `as_of_date` | ISO 8601；**`< final_test_cutoff`** 硬不变量 |
| `data_cutoff_date` | `== as_of_date` |
| `candidate_name` | string；v1 = `"continuous_smoothing_v1"` |
| `risk_score` | float ∈ [0, 1]；sigmoid 输出域 |
| `adjustment_score` | float ∈ [0, 1] |
| `risk_bucket` | enum：`low / medium / high / extreme` |
| `features_used` | dict |
| `warnings` | list of string；可空 |
| `final_test_refusal` | bool；`as_of_date >= 2026-01-01` 强制 `True` |

---

## 7. risk_bucket 状态

| bucket | 范围 |
|---|---|
| `low` | `risk_score < 0.35` |
| `medium` | `0.35 <= risk_score < 0.60` |
| `high` | `0.60 <= risk_score < 0.80` |
| `extreme` | `risk_score >= 0.80` |

### 7.1 强约束

| 强约束 | 状态 |
|---|---|
| **bucket 只是 display / diagnostics** | ✅ |
| **bucket 不是 hard exclusion 信号** | ✅ |
| **thresholds 未验证** | ✅ |
| **不能用来做 production decision** | ✅ |
| 不进入 4-fold gate 决策（gate 只看 metrics） | ✅ |
| 不允许用 W4 / final test 数据反推 | ✅ |

---

## 8. validation record mapping

为了把 candidate 输出**喂给** Step 3R-4.2 helper（接受 `records`
list），未来 Step 3R-4.3 adapter 需要把 candidate output + 现有 replay
records 组装成如下字段：

| 字段 | 来源 |
|---|---|
| `analysis_date` | replay record 中的 `analysis_date`（即 candidate 的 `as_of_date`） |
| `candidate_triggered` | `risk_score >= candidate_threshold` |
| `exclusion_would_block` | `candidate_triggered`（v1） |
| `survival_case` | `candidate_triggered ∧ prediction_correct` |
| `baseline_correct` | replay record 中 `direction_correct == 1` |
| `prediction_correct` | replay record 中 `direction_correct == 1` |
| `prediction_for_date` | replay record 中 `prediction_for_date` |
| `labels / raw_features` | optional（可作 grouping diagnostics） |

### 8.1 强约束

| 强约束 | 状态 |
|---|---|
| **`candidate_threshold` 未定** | ✅；本 checkpoint 不锁；3R-3.3 实测后由 launch review 决定 |
| **必须通过 3R-4.2 helper** | ✅；任何 candidate variant 必须出独立 `regime_validation_report.v1` |
| **不允许只看 pooled result** | ✅；与 3R-4.2 §8.3 worst-window 决胜一致 |
| **不允许把 `candidate_threshold` 学成 4 × 4 cell 边界** | ✅；shape 必须连续 |
| **adapter 不允许读 outcome 在 candidate decision 时已知的字段做 future leak** | ✅；anti-lookahead |
| **adapter 不允许读 2026 行** | ✅；与 helper 启动 gate 一致 |

---

## 9. 与 R4 的关系

| 维度 | R4 | continuous smoothing candidate |
|---|---|---|
| 形态 | 离散 soft metadata risk signal | 连续 sigmoid 在 9 raw_feature 上 |
| 是否 hard | ❌ | ❌ |
| 是否含 regime guard | ❌ | ✅（`market_trend_strength` 作为 sigmoid 输入） |
| 是否解 H1/H2 gap | ❌（Step 2G-8C 已证 R4 regime-agnostic） | **目标尝试**：通过 `- d * market_trend_strength` 让 sustained bull regime 期间 risk_score 系统性下降 |

### 9.1 强约束

| 强约束 | 状态 |
|---|---|
| **smoothing candidate 不是 R4 的硬化** | ✅ |
| **是连续特征版本，缓解 bucket cliff** | ✅ |
| **必须用 3R-4.2 验证是否改善 R4 fail** | ✅；这是 candidate eligibility 的第一个 acceptance |
| **如果不能改善，仍 fail** | ✅；helper `overall_status="fail"` → candidate 报废 |
| **R4 fail acceptance 仍是 sanity baseline** | ✅；3R-4.2 §9 R4-like fixture 已锁定 |
| **R4 hard 实施仍 NO-GO** | ✅；与 Step 2G-8 / 8B / 8C 三重 NO-GO 一致 |

---

## 10. 与 hard / required 的关系

| 维度 | continuous smoothing candidate |
|---|---|
| **`risk_score >= threshold` 是否自动启 `hard`** | **❌ 否** |
| **是否自动改 04 / 05 / 07 required** | **❌ 否** |
| **candidate `pass` 唯一允许的下游** | **进入下一步 design review** |
| **是否让 Gate 5 / Gate 6 自动 pass** | **❌ 否** |
| **是否驱动 `_PROTECTION_LAYER_CONNECTED` 翻 True** | **❌ 否** |
| **是否驱动 `hard_exclusion_allowed` / `primary_blocker` 派生** | **❌ 否** |
| **是否写 `simulated_trade` / `no_trade` / `final_direction` / `final_projection`** | **❌ 否** |
| **production wiring** | 永远独立 step；必须经 launch review |

---

## 11. 允许下一步

| # | 候选 | 状态 |
|---|---|---|
| 1 | **Step 3R-3.1 read-only candidate generator design / implementation** | **✅ 允许**（在本 checkpoint 进入 main 后启动）；新增 `services/continuous_smoothing_candidate.py`（命名待定）；纯 read-only；与 3R-2 helper 同等 isolation；focused tests |
| 2 | **Step 3R-4.3 real replay record adapter design / implementation** | **✅ 允许**（与 3R-3.1 解耦可并行）；把 W1/W2/W3 + W4 jsonl + candidate output 组装成 helper 接受的 records list |
| 3 | **Step 3R-3.3 4-fold validation run** | **必须等 3R-3.1 + 3R-4.3 完成**；用 helper 跑出 `regime_validation_report.v1` |
| 4 | **Step 3R-5 formula design** | **❌ 仍不允许**（必须先过 3R-3.3 实测 acceptance） |
| 5 | **Step 3R-6 read-only simulator** | **❌ 仍不允许**（必须先过 3R-5 design） |
| 6 | candidate `pass` 自动启 hard / Gate 5 / Gate 6 | **❌ 永远不允许**（与 §10 一致） |

---

## 12. 禁止事项

| # | 禁止 | 理由 |
|---|---|---|
| 1 | **不选系数**（`a` / `b` / `c` / `d` / `e`） | shape only；3R-3.1 实施时锁定 |
| 2 | **不选 `candidate_threshold`** | 3R-3.3 实测后；不允许用 4-fold 数据反推 |
| 3 | **不选 `risk_bucket` final thresholds** | 同上 |
| 4 | **不选 `market_trend_strength` 段阈值** | 同上 |
| 5 | **不跑 validation** | 3R-3.3 才跑 |
| 6 | **不读 W4 results** | adapter 由 3R-4.3 实施 |
| 7 | **不写 DB** | candidate 是 read-only artifact |
| 8 | **不改 production decision**（`final_direction` / `final_projection` / `simulated_trade` / `no_trade` / `confidence_system`） | 与 v1 / 3R-0 / 3R-4 一致 |
| 9 | **不启 hard / forced / anti_false_exclusion_triggered** | 三重 NO-GO（2G-8 / 8B / 8C） |
| 10 | **不改 04 / 05 / 07 required** | Step 2G 全程边界 |
| 11 | **不触碰 2026** | 永久封禁；hard stop |
| 12 | **不接 trading**（`longbridge` / `broker` / `paper_trade`） | 永不 |
| 13 | **不接 yfinance / 网络** | candidate 只读 caller-injected 数据 |
| 14 | **不让 `_PROTECTION_LAYER_CONNECTED` 翻 True** | 与 v1 / 3R-0 / 3R-4 一致 |
| 15 | **不让 `hard_gate_status.protection_layer_connected` 自动 pass** | 同上 |
| 16 | **不改 `hard_exclusion_allowed` / `primary_blocker` 派生** | 同上 |
| 17 | **不改 3R-4 protocol thresholds** | 阈值调整必须经 launch review |
| 18 | **不改 3R-2 helper 行为** | 仅 read-only 调用其输出 |
| 19 | **不改 3R-4.2 helper 行为** | 仅 read-only 调用其评分 |
| 20 | **不预选 candidate variants** | 一次只 commit 一个 variant；每个 variant 独立 4-fold |
| 21 | **不引入 hidden lookup table** | shape 必须连续 |
| 22 | **不让 candidate output 包含 `gate_status` / `validation_passed` / `overall_status`** | candidate 是数据层 |
| 23 | **不触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*`** | 历史防护 |

---

## 13. 下一步建议

按推荐优先级：

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **commit 本 checkpoint** | 把 §1-14 candidate 状态固化到 main | **本轮 / 下一轮** |
| 2 | **Step 3R-3.1 read-only candidate generator implementation** | 新增 `services/continuous_smoothing_candidate.py`（命名待定）；纯 read-only；与 3R-2 helper 同等 isolation；focused tests | **高**（commit 本 checkpoint 后启动） |
| 3 | **Step 3R-4.3 real replay record adapter design / implementation** | 把 W1/W2/W3 + W4 jsonl + candidate output 组装成 helper 接受的 records list；纯 wrapper / adapter | 中（与 3R-3.1 解耦可并行） |
| 4 | **Step 3R-3.3 4-fold validation run** | 用 3R-3.1 + 3R-4.3 + 3R-4.2 出 `regime_validation_report.v1`；R4 fail acceptance 复检 | 中（前两步完成后） |
| 5 | **不推荐**直接 Step 3R-5 formula design | 必须先过 3R-3.3 实测 + 4-fold acceptance | **❌** |
| 6 | **不推荐** Step 3R-6 read-only simulator | 必须先过 3R-5 design | **❌** |
| 7 | **不推荐**让 candidate `pass` 自动启 hard / Gate 5 / Gate 6 | 与 §10 一致 | **❌** |
| 8 | **不推荐** R4 hard implementation | 三重 NO-GO 已锁定 | **❌** |
| 9 | **不推荐** 升级 04 required | Step 2G 全程边界 | **❌** |
| 10 | **不推荐** 触碰 2026 final test range | 永久封禁 | **❌** |
| 11 | **不推荐**让 `_PROTECTION_LAYER_CONNECTED` 翻 True | 与 v1 / 3R-0 / 3R-4 一致 | **❌** |
| 12 | **不推荐**用 W4 / final test 数据反推 candidate / threshold 系数 | 阈值调整必须经 launch review | **❌** |
| 13 | **不推荐**预选多个 candidate variant | 一次只 commit 一个 variant | **❌** |

**关键判断**：
- 顺序 = 本 checkpoint → **3R-3.1 generator + 3R-4.3 adapter**（解耦
  可并行）→ 3R-3.3 validation run → 3R-5 formula → 3R-6 simulator →
  3R-7 sidecar
- 任何一步 fail → 整 candidate 报废，回到 design 层重新设计

---

## 14. 严守边界

本文是**纯 checkpoint markdown**：

- ❌ 没改任何代码（`services/*` / `ui/*` / `tests/*` / `scripts/*` 全部未触碰）
- ❌ 没改 DB schema
- ❌ 没写 DB
- ❌ 没运行 replay
- ❌ 没改 `run_predict` / `predict.py` / `scanner.py` /
  `prediction_store.py` / `app.py`
- ❌ 没改 `services/regime_features_builder.py` /
  `services/regime_labels_builder.py` /
  `services/regime_validation_helper.py` /
  `services/regime_diagnostics_dashboard.py` /
  `services/anti_false_exclusion_dashboard.py` /
  `services/soft_metadata_simulator.py` /
  `services/protection_layer_diagnostics.py` /
  `services/historical_replay_training.py` /
  `services/three_system_replay_audit.py` /
  `services/replay_record_wiring.py` /
  `services/projection_three_systems_renderer.py` /
  `services/outcome_capture.py` /
  `ui/protection_layer_diagnostics_renderer.py` / 任何 ui 模块 /
  任何 builder
- ❌ 没改 `scripts/run_1005_three_system_replay.py` 或任何 replay 脚本
- ❌ 没改 04 / 05 / 07 任何 required 字段
- ❌ 没启用 `hard` / `forced_exclusion` /
  `anti_false_exclusion_triggered`
- ❌ 没接 `yfinance` / `requests` / 任何网络
- ❌ 没接 trading API / `longbridge` / `broker` / `paper_trade`
- ❌ 没让 `_PROTECTION_LAYER_CONNECTED` 翻 True
- ❌ 没让 `hard_gate_status.protection_layer_connected` 自动 pass
- ❌ 没改 `hard_exclusion_allowed` / `primary_blocker` 派生
- ❌ 没触碰 2026-01-01 之后 final test range
- ❌ 没改 Step 3R-4 protocol thresholds（6 metric / 7 gate / 10 no-go）
- ❌ 没改 Step 3R-2 helper 行为
- ❌ 没改 Step 3R-4.1 design / checkpoint
- ❌ 没改 Step 3R-4.2 helper 行为 / checkpoint
- ❌ 没改 Step 3R-3 design（已 merge 在 commit `65fe411`，本 checkpoint 不动）
- ❌ 没改 Step 2G-8D / 8D.1A / 8D.2 / 8D.3 / 8D.4 文档或代码
- ❌ 没把 W4 / smoke 输出 commit 进 main
- ❌ 没读 W4 results（adapter 由 3R-4.3 实施）
- ❌ 没选 candidate 系数 / `candidate_threshold` / `market_trend_strength` 阈值 / `risk_bucket` 阈值
- ❌ 没运行 `pytest`（本轮纯文档；测试基线维持 commit `65fe411` 时
  的 2722 / 0 failed / 10 skipped）
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` /
  `avgo_agent.db.backup_*`
- ✅ 只新增 1 份 markdown checkpoint 文档（本文件）
