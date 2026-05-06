# Step 3R-3.3F — Continuous Smoothing v2 Candidate Design

> 本文是 **design only** —— 不改代码、不写 DB、不重跑 replay / validation、不 commit / push、不接 trading API、不启 hard / forced、不改 required、不触碰 2026 final-test range、不 add `logs/regime_validation/` / W4 / smoke output / `logs/prediction_log.jsonl`、不处理 DB backup / stash / `.claude/worktrees/`、不调 v1 `candidate_threshold` / SEED coefficients / 6 metric / 7 gate threshold、不实现 v2、不给 v2 任何具体新数值参数 / 新阈 / 新 feature 公式、不进 3R-5 / 3R-6 / 不自动 promotion。

## 1. 背景

| 项 | 状态 | 来源 |
|---|---|---|
| v1 real W1-W4 validation single run | ✅ 已运行（一次） | `logs/regime_validation/continuous_smoothing_v1_real_w1_w4_20260507_065417/` |
| v1 result checkpoint | ✅ 已 merge | commit `75f0ad5` |
| v1 postmortem report | ✅ 已 merge | commit `fc44bcf` |
| v2 launch review design + checkpoint | ✅ 已 merge | commits `4fd1278` / `7c1a0e5` |
| launch review `recommended_next_step` | `proceed_to_continuous_smoothing_v2_design` | launch review checkpoint §12 |
| **本文**（continuous_smoothing v2 candidate **design only**；不实现 v2、不给具体数值参数） | ⏳ design 中（未 commit） | — |
| v2 design checkpoint | ❌ 尚未启动 | — |
| v2 implementation | ❌ 尚未实现 | — |

本文位置：

- 已 merge 链：v1 result checkpoint → postmortem report → v2 launch review design → v2 launch review design checkpoint → **本 v2 candidate design** → v2 design checkpoint → v2 impl + tests → v2 single real run → v2 result checkpoint → 重新判断。
- 本文范围：**纯 markdown design**，定方向 / schema / feature families / abstain mode / risk_score 语义 / validation plan / pass criteria / no-go；**不**给具体公式 / 系数 / 阈值 / 校准曲线 / 网络结构。

## 2. v1 baseline recap

| 字段 | 值 |
|---|---|
| `candidate_name` | `continuous_smoothing_v1` |
| source run | `logs/regime_validation/continuous_smoothing_v1_real_w1_w4_20260507_065417/` |
| `candidate_threshold` | `0.60`（v1 seed lock；CLI 拒非 0.60；本文**不**改） |
| `final_test_cutoff` | `"2026-01-01"`（仍锁；本文**不**改） |
| `records_loaded` | 639（W1-W3 DB=286 + W4 jsonl=353） |
| `records_adapted` | 526（639 − 113 skipped；113 全部 `record_skipped:missing_or_invalid_direction_correct:<date>`） |
| `report_status` | `fail` |
| `overall_status` | `fail` |
| `worst_window` | **W1** |
| W1 `false_exclusion_rate` | **1.0000** |
| 4 window false_exclusion_rate | W1=1.00 / W2=0.52 / W3=0.50 / W4=0.54（**全部** > 0.10） |
| 4 window survival_case_preservation | **全部 0.0** |
| 7 gate 状态 | 全部 fail |
| `final_test_touched` | `false` |
| DB / market_data.db / backup count | unchanged |
| **结论** | **v1 not eligible**（legal fail；不是 pipeline error） |

## 3. v2 design goal

| 目标 | 状态 |
|---|---|
| **不**再把 strong survivor 误判成 exclusion risk | ✅ 核心目标 |
| risk_score 跨 window 更可比（解决 H1） | ✅ 核心目标 |
| 保留 **sidecar / read-only / non-production** | ✅ 与 v1 一致 |
| 输出 candidate risk；**不直接**改 final prediction | ✅ 与 v1 一致；adapter / helper 仍是唯一消费方 |
| 支持 future validation by 3R-4.2 helper | ✅ 必须；helper 接口不动 |
| **不**写 DB / **不**触碰 2026 final-test range | ✅ 永久 invariant |
| **不**自动启 hard / Gate 5 / Gate 6 / `_PROTECTION_LAYER_CONNECTED` | ✅ 永久 invariant |

非目标（本文明确 out-of-scope）：

| 非目标 | 状态 |
|---|---|
| 改 v1 `candidate_threshold` / SEED | ❌ 永久禁止 |
| 改 6 metric / 7 gate threshold | ❌ 3R-4 protocol 锁定 |
| 改 adapter / helper / orchestrator / wrapper / provider / glue | ❌ 永久禁止 |
| 改 production main path（predict / scanner / streamlit / app / prediction_store / outcome_capture） | ❌ 永久禁止 |
| 推动 v2 自动 promotion 或解锁 3R-5 / 3R-6 | ❌ 永远不 |

## 4. key design shift from v1

| 维度 | v1（已固定 baseline） | v2（本文设计目标） |
|---|---|---|
| risk_score 语义 | "overheat-style"：pos20 高 + AVGO outperform → 高 risk → 应排除 | "false-exclusion-risk-aware"：score 锚定到 prediction 是否会错；high score = 此 row 的 prediction 真的更可能错；trigger = exclude 是合理的 |
| 信号锚 | 设计稿 prior（H3 极性可能颠倒，未对齐 outcome） | outcome 对齐（不是从 v1 baseline 拟合，而是从先验 / 文献 / 工程判断映射 P(prediction wrong) 到 score） |
| 强势 survivor 处理 | 直接当 overheat 排除 | 必须显式 **trend_continuation_protection** family（§5），让 strong survivor 不进入 high bucket |
| 跨 window 一致性 | 同 score 在 W1 和 W4 含义不同（H1） | 必须显式 **regime_stability** + **calibration_context**（§5），让 score 跨 window 含义可比 |
| 触发样本下限 | 无 candidate-level guard（H5） | 必须显式 **trigger_support / sample_support**（§5）+ **abstain mode**（§7），低支持度直接 abstain |
| feature 极性审计 | 5 系数 design seed，未 audit | 每个 family 必须**自审**：在哪个 regime 下指向 exclusion，在哪个 regime 下指向 protection；不允许"单方向系数 → 全局适用"假设 |
| 输出"通过 / 失败"判断 | 无（candidate 只输出 risk + bucket） | 仍**无**（gate_status / validation_passed / overall_status 由 helper 计算；candidate 不下结论；与 v1 一致） |
| `monthly_shock` 必要性 | 保留（中位 0.0 across all windows；稀疏二值；信号低） | **必须重新审计**：保留 / 重写 / 删除三选一；本文不选 |
| `market_trend_strength` 语义 | "trend 强 → 风险低"（系数 -0.7）；W1 trend=1 仍不足以消减 pos20 推高的 risk | **必须重写**为"保护强趋势 continuation"语义；本文不写公式 |

> **v2 不是 v1 微调**：v2 是**新模块**（独立 `services/continuous_smoothing_candidate_v2.py`），**不** import v1，**不**复制 v1 SEED 作为起点。

## 5. feature families（8 family；只列 family，不给参数）

每个 family：用途 + 针对 v1 failure 的关系；**不**给具体公式 / 系数 / 阈值 / 分位 / 校准曲线。

### 5.1 trend_continuation_protection

| 项 | 内容 |
|---|---|
| 用途 | 识别"强势 + 趋势确立 + 历史 base rate 高"的 row，给 score 一个**减项**或直接进入 abstain |
| 针对 v1 failure | H3：v1 把 pos20 高 + AVGO outperform 当 overheat；W1 case 1 / case 2 的 actual_direction 全是 up，是 strong survivor，不应 exclude |
| 信号方向 | regime trend 强 + 个股 outperform → **降低**最终 score 或直接 abstain |
| 数据来源 | 仅本地 csv（AVGO/NVDA/SOXX/QQQ）+ regime_labels 已派生字段；不接网络 |

### 5.2 peer_confirmation_strength

| 项 | 内容 |
|---|---|
| 用途 | 识别"peer 同步 + 持续确认"的强势上下文；区别于 v1 单一 `peer_5d_aligned_pct` 的二值-like 行为 |
| 针对 v1 failure | H4：W1 中 peer_5d_aligned_pct = 0 occurs 的样本 damping 失效；新 family 应处理 peer 确认的多个时间尺度 / 强度而非单一 5d 同步 |
| 信号方向 | peer 强确认 + 多尺度一致 → **降低** score 或 abstain |
| 数据来源 | 仅本地 csv |

### 5.3 overextension_without_confirmation

| 项 | 内容 |
|---|---|
| 用途 | 识别"价格已经高 + 但 peer / 趋势没确认"的真正 overextension |
| 针对 v1 failure | H2 / H3：v1 把 outperform 全部当 overheat；v2 应只在**没有 peer / 趋势确认**时才考虑"过度延伸"信号 |
| 信号方向 | 高位 + 无确认 → **提高** score（即 candidate 倾向 exclude） |
| 数据来源 | 仅本地 csv + regime_labels |

### 5.4 reversal_pressure

| 项 | 内容 |
|---|---|
| 用途 | 识别真正的 reversal 信号（如 momentum 转负 / volatility spike / sector divergence） |
| 针对 v1 failure | H2：v1 没有 reversal-specific 信号，依赖 pos20 + outperform 间接推断 |
| 信号方向 | reversal pressure 强 → **提高** score |
| 数据来源 | 仅本地 csv |

### 5.5 regime_stability

| 项 | 内容 |
|---|---|
| 用途 | 描述当前 regime 的稳定 / 转折状态；用作其他 family 的**门控**或**权重调整** |
| 针对 v1 failure | H1：v1 把不同 regime 视作同一 score 空间；v2 通过 regime_stability 让 score 跨 regime 含义可比 |
| 信号方向 | regime 稳定 → 其他 family 信号更可信；regime 不稳定 → trigger_support / abstain 倾向更高 |
| 数据来源 | regime_labels（pos20_regime / market_trend_regime / monthly_context_regime） |

### 5.6 monthly_shock_context

| 项 | 内容 |
|---|---|
| 用途 | 把 v1 的 `monthly_shock`（中位 0.000；稀疏二值）替换为**有上下文**的 shock 描述 |
| 针对 v1 failure | H4 + Q6：v1 monthly_shock 信号低；v2 必须**审计**保留 / 重写 / 删除三选一 |
| 信号方向 | shock 真实出现 + 与 trend 不一致 → 谨慎触发；shock 出现但 trend 持续 → 不一定 exclude |
| 数据来源 | 仅本地 csv |
| 重要 | 本文**不**预先决定保留还是删除 |

### 5.7 trigger_support / sample_support

| 项 | 内容 |
|---|---|
| 用途 | candidate 自评信号支持度：在当前 regime 下是否有足够 evidence 给出 exclusion 判断 |
| 针对 v1 failure | H5：v1 在 W1 触发 2 条直接 helper min_sample fail；v2 应在 candidate 内部就识别"信号不足"并 abstain |
| 信号方向 | support 不足 → **abstain**（不 trigger，不 block，不影响 helper / adapter trigger 计数） |
| 数据来源 | regime_labels + window-level support 估计；具体方法不预先选 |

### 5.8 calibration_context

| 项 | 内容 |
|---|---|
| 用途 | 提供给 risk_score 的 calibration 输入 —— 让 score 数值跨 window / 跨 regime 含义一致 |
| 针对 v1 failure | H1 / H5：v1 risk_score 跨 window 不可比 |
| 信号方向 | calibration 把 raw composite score 映射到 0~1 区间，且**含义稳定** = "P(prediction will be wrong | features)" 的近似 |
| 数据来源 | 必须**先验 / 文献 / 工程判断**，**不**从 v1 fail baseline 拟合 |
| 重要 | 本文**不**选具体 calibration 方法（isotonic / Platt / 分位 / 其它三选一以上） |

## 6. candidate output schema

设计 v2 输出 schema：`continuous_smoothing_candidate_v2.v1`。

### 6.1 字段表

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `schema_version` | str | ✅ | `"continuous_smoothing_candidate_v2.v1"`（**不**复用 v1 的 `continuous_smoothing_candidate.v1`，避免 schema 歧义） |
| `as_of_date` | str | ✅ | row 的 analysis_date（与 v1 同义） |
| `data_cutoff_date` | str | ✅ | 同 `as_of_date`（builder anti-lookahead；与 v1 同义） |
| `candidate_name` | str | ✅ | `"continuous_smoothing_v2"`（lock；adapter / helper 透传） |
| `risk_score` | float \| None | ✅ | 0~1（`None` 当 abstain / 缺数据）；含义见 §8 |
| `risk_bucket` | str | ✅ | one of `{abstain, low, medium, high, extreme}`（v1 是 `low/medium/high/extreme`；v2 增加 `abstain`） |
| `abstain_reason` | str \| None | ✅ | 当 `risk_bucket == "abstain"` 时为非空字符串（如 `"insufficient_trigger_support"` / `"missing_features"` / `"final_test_refusal"`）；否则 `None` |
| `trigger_support` | float \| None | ✅ | 0~1 self-reported 信号支持度；用于 abstain 判定（具体阈本文不选） |
| `features_used` | dict | ✅ | 8 family 的 raw + processed value（结构留给 v2 implementation 决定）；保留 audit 价值 |
| `warnings` | list[str] | ✅ | candidate 内部 warning（不替代 helper warnings） |
| `final_test_refusal` | bool | ✅ | `as_of_date >= "2026-01-01"` → `true` + `risk_bucket="abstain"` + `risk_score=None` |

### 6.2 v2 输出**禁止**字段（防止越位）

| 禁止字段 | 理由 |
|---|---|
| `gate_status` | 由 helper 计算；candidate 不下 gate 结论 |
| `validation_passed` / `overall_status` | 同上 |
| `hard_gate_status` / `hard_exclusion_allowed` / `primary_blocker` | hard / forced / required 永久封禁 |
| `forced_exclusion` / `anti_false_exclusion_triggered` | 同上 |
| `final_direction` / `final_projection` | candidate 不影响 final prediction |
| `simulated_trade` / `no_trade` | 不接 trading |
| `_PROTECTION_LAYER_CONNECTED` | 永久封禁 |
| `predict_result_json` / `research_result_json` / `scan_result_json` | 不消费 DB raw payload |
| `actual_close_change` / `actual_state` / `direction_correct` / `pos20` / `five_state_projection` | 不消费 outcome / W4 future-leak 字段 |

### 6.3 schema 兼容性

- adapter `build_replay_validation_records(...)` 在 v1 schema 上工作；v2 schema **必须**让 adapter 把 `risk_bucket ∈ {high, extreme}` 视为 `candidate_triggered=True`（与 v1 一致），把 `risk_bucket == "abstain"` 视为 `candidate_triggered=False`（不计 trigger，不计 block）。
- 是否需要扩展 adapter 接受新字段（如 `abstain_reason`）由 **v2 implementation 阶段**判断；本设计只声明 contract：`risk_bucket="abstain"` 在 adapter 中等同 not triggered。
- helper（`build_regime_validation_report(...)`）**不动**。

## 7. abstain mode

### 7.1 触发条件

`risk_bucket = "abstain"` 当：

| 条件 | abstain_reason |
|---|---|
| `trigger_support` < candidate-internal 阈（具体值在 v2 implementation 决定） | `"insufficient_trigger_support"` |
| 任一关键 feature family 计算失败 / NaN / 缺 OHLC 数据 | `"missing_features"` |
| `as_of_date >= final_test_cutoff` | `"final_test_refusal"`（`final_test_refusal=true`）|
| regime_labels 不可用 / unknown regime | `"regime_label_unavailable"` |

### 7.2 abstain 与 not-triggered 的区分

| 状态 | 含义 | 在 adapter 中的表现 |
|---|---|---|
| `risk_bucket = "low"` 或 `"medium"` | candidate 有 enough evidence，但**判定 prediction 不会错** → 不 trigger | `candidate_triggered=False`（v1 同义） |
| `risk_bucket = "abstain"` | candidate **没有 enough evidence** → 拒绝下结论 | `candidate_triggered=False`（与"低 risk"在 adapter 表面一致；但 candidate 自身保留 audit reason） |
| `risk_bucket = "high"` 或 `"extreme"` | candidate 判定 prediction 更可能错 | `candidate_triggered=True`（v1 同义） |

### 7.3 abstain ≠ pass / no_trade

abstain **不是**：
- ❌ 不是 candidate 通过 / pass
- ❌ 不是 production 层的 `no_trade`
- ❌ 不是 helper gate pass
- ❌ 不是"hold position"或"sell"信号

abstain **是**：
- ✅ candidate 拒绝在低支持度场景下下 exclusion 判断
- ✅ 让 helper 不把这些 row 计入 false_exclusion / survival 计算（避免 W1 那种 2 条 trigger 直接 collapse）
- ✅ 保留 audit 字段 `abstain_reason` 供 postmortem / 后续 v3 review

### 7.4 abstain 的 trade-off（设计层 awareness）

| trade-off | 说明 |
|---|---|
| 过度 abstain | 可能让 v2 在低支持度 regime 失去**任何**评估，等价于"不做 candidate" |
| 不足 abstain | W1-style 2 条 trigger 全错 collapse 可能复现 |
| 平衡点 | 由 launch review 在 implementation 阶段决定；本文不选阈值 |

## 8. risk_score interpretation

### 8.1 v2 语义（明确固定）

> **v2 risk_score 是 calibrated false-exclusion-risk-aware exclusion score**：
>
> **`risk_score = P̂(prediction will be wrong | features)`**
>
> 即：score 越高 → candidate 越确信 "如果不 exclude 这条 prediction，它将会错"。trigger = exclude 该 prediction 是合理的；高 score 下 trigger 不容易导致 false_exclusion。

### 8.2 与 adapter 的语义对齐（不需改 adapter）

adapter 把 `candidate_triggered=True` + `survival_case=False` 视为正确 exclusion；`candidate_triggered=True` + `survival_case=True` 视为 false exclusion。v2 的 risk_score 直接作用在这条因果链上：

- 高 score（≥ trigger threshold）→ candidate 想 exclude → 如果 ground truth 是 wrong prediction → 正确 exclusion ✅
- 高 score → exclude → 如果 ground truth 是 correct prediction → false exclusion ❌（candidate 错）
- 低 score（abstain / low / medium）→ candidate 不 exclude → false_exclusion 计算分母自然降低（或被 abstain 排除）

### 8.3 v1 vs v2 语义对照

| 维度 | v1 | v2 |
|---|---|---|
| score 语义 | "overheat-style risk"（heuristic） | "calibrated P(prediction wrong)" |
| 锚 | design seed prior（未对齐 outcome） | 先验 / 文献 / 工程判断（**不**从 v1 fail baseline 拟合） |
| 跨 window 可比 | ❌（H1） | ✅（设计目标；通过 §5.5 regime_stability + §5.8 calibration_context 实现） |
| trigger 后果 | adapter 计为 trigger / block | 同 v1（adapter 不动） |
| false_exclusion 含义 | 高 score row 实际是 survivor | 高 score row 实际预测正确（即 candidate 把 P(wrong) 算高了，但 prediction 实际对） |

> v2 的"方向"由本文**明确固定为 §8.1** —— 不再由 implementation 阶段任意选取。任何后续 implementation 必须遵守这个语义；如果未来发现该语义下仍无法 ship，则属于 v3 launch review 的输入。

### 8.4 calibration target

calibration_context（§5.8）的目标：

- 把 8 个 family 的合成 raw_score 映射到 0~1 区间，且**含义稳定为** `P̂(prediction wrong)`
- **不**预先选具体 calibration 方法（isotonic / Platt / 分位 / 其它）；这是 implementation 阶段决定
- **不**从 v1 fail baseline 拟合（与 launch review §5 第 4 项一致）

## 9. threshold policy design

| 项 | 状态 |
|---|---|
| 本文是否选具体 v2 threshold | ❌ 否 |
| threshold 设计候选（仅方向） | global / regime-aware / abstain-aware（三选一或多）；本文**不**决定 |
| threshold 是否需要独立 validation | ✅ 是；任何 threshold 必须经 v2 single real run 验证 |
| 是否使用 v1 fail baseline 反推具体 threshold | ❌ 永久禁止 |
| 是否 sweep / grid search | ❌ 永久禁止 |
| 是否 retry-until-pass | ❌ 永久禁止 |
| threshold 选定时机 | v2 implementation 阶段（基于 §5 / §8 设计 + 先验 / 工程判断），**不**在本 design |

不动的 threshold（**v1 锁定**，v2 仍 honor）：

- v1 `candidate_threshold = 0.60`：v1 已 merge 模块仍按 0.60 工作；本文**不**改 v1
- helper 6 metric / 7 gate threshold：3R-4 protocol 锁定
- helper `GATE_MIN_WINDOW_SAMPLE = 20`：3R-4.2 helper 常量
- candidate v1 risk_bucket 阈：v1 模块常量

> v2 自有的 trigger threshold（v2-internal）**不影响** v1 锁定值。

## 10. validation plan

v2 必须**完整重走** 7 步流程（任一 fail → 回 design）：

| # | 步骤 | 范围 |
|---|---|---|
| 1 | **v2 design checkpoint**（独立 markdown） | 状态归档 + recommended_next_step 二选一 |
| 2 | **v2 implementation**：新增 `services/continuous_smoothing_candidate_v2.py`（独立模块；**不** import v1；**不**复制 v1 SEED） | 8 family + abstain mode + risk_score = `P̂(prediction wrong)` 语义 + schema §6 |
| 3 | **focused tests**：新增 `tests/test_continuous_smoothing_candidate_v2.py`：unit tests + isolation tests（forbidden imports / 字符串扫）+ schema tests + abstain mode tests | full pytest 零回归 |
| 4 | **adapter compatibility check**（不改 adapter） | 验证 adapter 把 `risk_bucket ∈ {high, extreme}` 视 trigger，把 `abstain` 视 not-triggered；如需 adapter 扩展 → 独立 design |
| 5 | **single real W1-W4 validation run**（一次） | 通过 execution glue（如需新 v2 glue 则独立 design + impl + tests）；同 cutoff `2026-01-01`；output_dir 新 timestamp（如 `logs/regime_validation/continuous_smoothing_v2_real_w1_w4_<TS>/`） |
| 6 | **v2 result checkpoint** | 同 v1 result checkpoint 风格 + **v1 baseline comparison**（量化对比表） |
| 7 | **v1 baseline comparison**（在 result checkpoint 内） | per-window false_exclusion_rate / survival_case_preservation / trigger rate / cross_window_variance / gate_status v1 vs v2 |

> 任一步 fail → 回 design；**不**自动进入下一步；**不** retry-until-pass。

## 11. v2 success criteria

v2 **不能仅"比 v1 好一点"** —— 必须满足以下硬阈：

| # | 标准 | 量化要求（与 launch review §8 一致） |
|---|---|---|
| 1 | W1 `false_exclusion_rate` **必须低于 v1** 的 `1.0` | 至少 ≤ helper 阈 0.10 |
| 2 | 4 个 window false_exclusion_rate 全部 **< v1 对应值** | W1<1.0, W2<0.52, W3<0.50, W4<0.54；且全部 ≤ 0.10 |
| 3 | 4 个 window `survival_case_preservation` **全部 > v1 的 0.0** | review 接受具体阈由 helper protocol 决定 |
| 4 | cross-window trigger rate 不极端失衡 | 不出现 1 : 24 量级差距；helper `cross_window_variance` gate pass |
| 5 | `worst_window` 不 collapse | worst_window false_exclusion_rate ≤ 0.10 |
| 6 | `final_test_touched = false`；`final_test_refusal = false` | 6 层 hard stop 仍生效 |
| 7 | DB / market_data.db / backup count **未变** | byte-for-byte 不变 |
| 8 | 7 gates 全部 pass **或** 对未通过的 gate 有 launch review 接受的 waiver | 任一 fail 必须有 review-approved 解释 |
| 9 | output 4 文件 schema valid + untracked + **不 commit raw** | 与 v1 同 |
| 10 | result checkpoint 含 v1 baseline comparison 表 | 量化对比（per-window + 跨 window + gate-by-gate） |
| 11 | **不** threshold sweep；**不**自动 promotion；**不**自动启 hard / Gate 5 / Gate 6 / `_PROTECTION_LAYER_CONNECTED` | 即便 1-10 全 pass，也仅允许进入 review |

## 12. no-go rules（20 项）

v2 design + impl + validation 全程 no-go（任意一项触发 → 立即停止）：

| # | 条件 |
|---|---|
| 1 | 调 v1 `candidate_threshold` |
| 2 | 调 v1 SEED coefficients |
| 3 | 复制 v1 SEED 作为起点 |
| 4 | 给 v2 任何具体新 threshold / 新 coefficient / 新 feature 公式（在本 design 阶段） |
| 5 | 实现 v2（在本 design 阶段） |
| 6 | 跑 validation |
| 7 | 进入 Step 3R-5 formula |
| 8 | 进入 Step 3R-6 simulator |
| 9 | 启 hard / forced / `anti_false_exclusion_triggered` |
| 10 | 让 `_PROTECTION_LAYER_CONNECTED` 翻 True |
| 11 | 改 04 / 05 / 07 required |
| 12 | 触碰 2026 final-test range |
| 13 | commit raw output |
| 14 | 接 yfinance / requests / 任何网络 / trading API |
| 15 | 改 v1 已 merge 模块（wrapper / provider / orchestrator / candidate / adapter / helper / glue） |
| 16 | 改任何已 merge 测试 |
| 17 | sweep / grid search / hyperparameter optimization |
| 18 | 用 v1 fail baseline 数据反推具体参数 |
| 19 | retry-until-pass |
| 20 | auto promotion / 自动解锁 3R-5 / 3R-6 |

## 13. recommended_next_step

**`write_v2_design_checkpoint`**

| 含义 | 状态 |
|---|---|
| 只允许进入 v2 **design checkpoint**（独立 markdown） | ✅ |
| 允许直接进入 v2 **implementation** | ❌ 否（必须先过 v2 design checkpoint） |
| 允许直接进入 v2 **single real validation run** | ❌ 否（必须先过 v2 impl + tests） |
| 允许直接进入 Step 3R-5 / 3R-6 | ❌ 否（必须先过 v2 result checkpoint + 新一轮 launch review） |
| 允许 v2 design 阶段决定 v2 是 abandoned | ✅（如果 design checkpoint 阶段判定本 design 不 ship-able，可改 recommended_next_step 为 abandon） |
| 允许 v2 design 阶段提具体新 threshold / 新 coefficient | ❌ 永久禁止；具体参数在 v2 implementation 阶段决定 |

## 14. 严守边界

本文是**纯 design markdown**：

- ❌ 没改任何代码（`services/*` / `ui/*` / `tests/*` / `scripts/*` 全部未触碰）
- ❌ 没改 DB schema / 没写 DB
- ❌ 没运行 replay
- ❌ 没**重新运行** real validation（baseline 仍是 v1 `20260507_065417` run）
- ❌ 没运行 prepare-only smoke
- ❌ 没读 v1 4 个 raw output json 任一字节（仅引用 path / 复述 result checkpoint + postmortem 已固化字段）
- ❌ 没修改 v1 4 个 raw output json
- ❌ 没改 `run_predict` / `predict.py` / `scanner.py` / `prediction_store.py` / `app.py`
- ❌ 没改 `services/regime_features_builder.py` / `services/regime_labels_builder.py` / `services/regime_validation_helper.py` / `services/continuous_smoothing_candidate.py`（v1） / `services/replay_validation_record_adapter.py` / `services/historical_replay_training.py` / `services/real_regime_label_provider.py` / 任何 ui 模块 / 任何 builder
- ❌ 没改 `scripts/run_continuous_smoothing_validation.py` / `scripts/run_real_continuous_smoothing_validation.py` / `scripts/run_real_continuous_smoothing_validation_execute.py`
- ❌ 没改 `tests/test_run_continuous_smoothing_validation.py` / `tests/test_run_real_continuous_smoothing_validation.py` / `tests/test_real_regime_label_provider.py` / `tests/test_run_real_continuous_smoothing_validation_execute.py` / 任何已 merge 测试
- ❌ 没新增 v2 任何代码 / 任何测试 / 任何脚本 / 任何 fixture
- ❌ 没改 v1 `candidate_threshold = 0.60`（仍锁）
- ❌ 没改 v1 SEED coefficients（仍锁）
- ❌ 没改 v1 6 metric / 7 gate threshold（3R-4 protocol 锁定）
- ❌ 没给 v2 任何具体新 threshold / 新 coefficient / 新 feature 公式 / 新 cutoff / 新 calibration 曲线
- ❌ 没改 04 / 05 / 07 任何 required 字段
- ❌ 没启用 `hard` / `forced_exclusion` / `anti_false_exclusion_triggered`
- ❌ 没接 `yfinance` / `requests` / 任何网络
- ❌ 没接 trading API / `longbridge` / `broker` / `paper_trade`
- ❌ 没让 `_PROTECTION_LAYER_CONNECTED` 翻 True
- ❌ 没让 `hard_gate_status.protection_layer_connected` 自动 pass
- ❌ 没改 `hard_exclusion_allowed` / `primary_blocker` 派生
- ❌ 没触碰 2026-01-01 之后 final-test range
- ❌ 没改 Step 3R-4 protocol thresholds（6 metric / 7 gate / 10 no-go）
- ❌ 没改 Step 3R-2 helper / 3R-3.1 candidate / 3R-4.2 helper / 3R-4.3A adapter 行为
- ❌ 没改 Step 3R-3.3 / 3R-3.3A / 3R-3.3B / 3R-3.3C 系列 / 3R-3.3C-D / 3R-3.3E 已 merge 文档 / 实施
- ❌ 没改 Step 2G-8D / 8D.1A / 8D.2 / 8D.3 / 8D.4 文档或代码
- ❌ 没把 W4 / smoke / `logs/regime_validation/` / v1 raw output / `logs/prediction_log.jsonl` / DB backup / `agent_loop.py` / `.claude/worktrees/` 任一 commit 进 main
- ❌ 没创建任何新的 `logs/regime_validation/*` 子目录
- ❌ 没运行 `pytest`（本轮纯文档；测试基线维持 commit `7812b10` 时的 **2905 / 0 failed / 10 skipped**）
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*`
- ❌ 没用 v1 baseline 数据反推 v2 任何具体参数
- ❌ 没让 v1 fail 触发 retry / sweep / grid search
- ❌ 没让 v2 design 自动 promotion / 自动解锁 3R-5 / 3R-6
- ❌ 没实现 v2
- ✅ 只新增 1 份 markdown design 文档（本文件）
