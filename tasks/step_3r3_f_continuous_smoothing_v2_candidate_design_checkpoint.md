# Step 3R-3.3F — Continuous Smoothing v2 Candidate Design Checkpoint

> 本文是 **checkpoint markdown** —— 不改代码、不写 DB、不重跑 replay / validation、不 commit / push、不接 trading API、不启 hard / forced、不改 required、不触碰 2026 final-test range、不 add `logs/regime_validation/` / W4 / smoke output / `logs/prediction_log.jsonl`、不处理 DB backup / stash / `.claude/worktrees/`、不调 v1 `candidate_threshold` / SEED coefficients / 6 metric / 7 gate threshold、不实现 v2、不给 v2 任何具体新数值参数 / 新阈 / 新 feature 公式 / 新 calibration 曲线、不进 3R-5 / 3R-6 / 不自动 promotion。

## 1. 当前完成状态

| 项 | 状态 | 来源 |
|---|---|---|
| v1 real W1-W4 validation single run + result checkpoint | ✅ 已 merge | output `logs/regime_validation/continuous_smoothing_v1_real_w1_w4_20260507_065417/`；commit `75f0ad5` |
| v1 postmortem design + checkpoint + report | ✅ 已 merge | commits `289f97b` / `c5bf686` / `fc44bcf` |
| Step 3R-3.3E v2 launch review design + checkpoint | ✅ 已 merge | commits `4fd1278` / `7c1a0e5` |
| Step 3R-3.3F **v2 candidate design**（14 节、415 行） | ✅ **已 merge** | commit `b16fce9` |
| **本 checkpoint** —— 固定 v2 design goal / key shift / feature families（8 family）/ schema（`continuous_smoothing_candidate_v2.v1`）/ abstain mode / risk_score 语义 / validation plan / pass criteria / no-go / 允许下一步 | ⏳ **本文**（未 commit） | — |
| v2 implementation | ❌ 尚未启动（不在本 checkpoint 范围） | — |
| v2 single real run / v2 result checkpoint | ❌ 尚未启动 | — |

> v1 fail 已固定为 baseline；v2 尚未实现 / 尚未 validation；本 checkpoint 只固化 v2 design 状态。

## 2. 当前 main 状态

- `main` 最新 commit：`b16fce9`
- commit message：`docs(contract): Step 3R-3.3F continuous smoothing v2 candidate design`
- 上游：`origin/main` 已同步（push 完成 `7c1a0e5..b16fce9  main -> main`）
- 本步骤已 merge 文件：

| 路径 | 类型 | 行数 |
|---|---|---|
| `tasks/step_3r3_f_continuous_smoothing_v2_candidate_design.md` | 新增 | 415（v2 candidate design 边界） |

测试基线：本步骤纯文档；测试基线维持 commit `7812b10` 时的 **2905 / 0 failed / 10 skipped**。

| 项 | 是否触碰 |
|---|---|
| 改代码 | ❌ 否 |
| 改 service / candidate（v1）/ adapter / helper / orchestrator / wrapper / provider / glue | ❌ 否 |
| 改 DB schema / 写 DB | ❌ 否 |
| 跑 replay / 重跑 real validation / 跑 prepare-only smoke | ❌ 否 |
| 调 v1 `candidate_threshold` / SEED coefficients | ❌ 否 |
| 调 6 metric / 7 gate threshold | ❌ 否 |
| 给 v2 任何具体新参数 / 新阈 / 新公式 / 新 calibration 曲线 | ❌ 否 |
| 实现 v2 | ❌ 否 |
| 接 yfinance / 网络 / trading API | ❌ 否 |
| 触碰 2026 final-test range | ❌ 否 |
| add `logs/regime_validation/` / W4 / smoke / DB backup / `agent_loop.py` / `.claude/worktrees/` / `logs/prediction_log.jsonl` | ❌ 否 |
| 进 3R-5 formula / 3R-6 simulator | ❌ 否 |
| 启 hard / forced / `_PROTECTION_LAYER_CONNECTED` | ❌ 否 |

## 3. v1 baseline recap

| 字段 | 值 |
|---|---|
| `candidate_name` | `continuous_smoothing_v1` |
| source run | `logs/regime_validation/continuous_smoothing_v1_real_w1_w4_20260507_065417/` |
| `candidate_threshold` | `0.60`（v1 lock；本文**不**改） |
| `final_test_cutoff` | `"2026-01-01"`（仍锁；本文**不**改） |
| `records_loaded` | 639（W1-W3 DB=286 + W4 jsonl=353） |
| `records_adapted` | 526（639 − 113 skipped；113 全部 `record_skipped:missing_or_invalid_direction_correct:<date>`） |
| `report_status` | `fail` |
| `overall_status` | `fail` |
| `worst_window` | **W1** |
| W1 `false_exclusion_rate` | **1.0000**（gate 阈 0.10 的 10×） |
| 4 window false_exclusion_rate | W1=1.00 / W2=0.52 / W3=0.50 / W4=0.54（**全部** > 0.10） |
| 4 window survival_case_preservation | **全部 0.0** |
| 7 gate 状态 | 全部 fail |
| `final_test_touched` | `false` |
| DB / market_data.db / backup count | unchanged（7 → 7） |
| **结论** | **v1 not eligible**（legal fail；不是 pipeline error） |

## 4. key design shift（v1 → v2）

| 维度 | v1（已固定 baseline） | v2（本文设计目标） |
|---|---|---|
| risk_score 语义 | "overheat-style"：pos20 高 + AVGO outperform → 高 risk → 应排除 | "false-exclusion-risk-aware"：score 锚定到 prediction 是否会错 |
| signal 锚 | design seed prior（H3 极性可能颠倒，未对齐 outcome） | outcome 对齐（先验 / 文献 / 工程判断映射 P(prediction wrong) → score；**不**从 v1 fail baseline 拟合） |
| strong survivor 处理 | 当 overheat 排除 | 必须显式 **trend_continuation_protection** family；strong survivor 不进 high bucket |
| 跨 window 一致性 | 同 score 在 W1 和 W4 含义不同（H1） | **regime_stability** + **calibration_context** 让 score 跨 window 含义可比 |
| 触发样本下限 | 无 candidate-level guard（H5） | **trigger_support / sample_support** + **abstain mode** |
| feature 极性审计 | 5 系数 design seed，未 audit | 每个 family 必须自审"在哪个 regime 下指向 exclusion / 在哪个 regime 下指向 protection" |
| `monthly_shock` 必要性 | 保留（中位 0.0；稀疏；信号低） | **必须重新审计**：保留 / 重写 / 删除三选一 |
| `market_trend_strength` 语义 | "trend 强 → 风险低"（系数 -0.7）；W1 trend=1 仍不足以消减 | **必须重写**为"保护强趋势 continuation"语义 |
| candidate 是否下结论 | 无（仅输出 risk + bucket） | 仍**无**（gate_status / validation_passed / overall_status 由 helper 计算；与 v1 一致） |

> **v2 不是 v1 微调**：v2 是**新模块**（独立 `services/continuous_smoothing_candidate_v2.py`），**不** import v1、**不**复制 v1 SEED 作为起点。

## 5. v2 design goal

| 目标 | 状态 |
|---|---|
| **不**再把 strong survivor 误判成 exclusion risk | ✅ 核心目标 |
| risk_score 跨 window 更可比（解决 H1） | ✅ 核心目标 |
| 保留 **sidecar / read-only / non-production** | ✅ 与 v1 一致 |
| 输出 candidate risk；**不直接**改 final prediction | ✅ 与 v1 一致；adapter / helper 是唯一消费方 |
| 支持 future validation by 3R-4.2 helper | ✅ 必须；helper 接口不动 |
| **不**写 DB / **不**触碰 2026 final-test range | ✅ 永久 invariant |
| **不**自动启 hard / Gate 5 / Gate 6 / `_PROTECTION_LAYER_CONNECTED` | ✅ 永久 invariant |

## 6. feature families（8 个；只固定 family，不给参数）

| # | family | 用途 | 关联 hypothesis |
|---|---|---|---|
| 1 | **trend_continuation_protection** | 识别强势 + 趋势确立 + 历史 base rate 高的 row → 降 score 或 abstain | H3（避免误杀 strong survivor） |
| 2 | **peer_confirmation_strength** | peer 同步 + 多尺度持续确认；替代 v1 单一 5d 二值 | H4（damping 失效） |
| 3 | **overextension_without_confirmation** | 高位**且**没 peer / 趋势确认 → 提 score | H2 / H3（v1 把 outperform 全当 overheat） |
| 4 | **reversal_pressure** | 真正 reversal 信号（momentum 转负 / volatility spike / sector divergence） | H2（v1 缺 reversal-specific 信号） |
| 5 | **regime_stability** | regime 稳定 / 转折状态；用作其他 family 门控 | H1（跨 regime 可比） |
| 6 | **monthly_shock_context** | v1 monthly_shock 替换：保留 / 重写 / 删除三选一 | H4 + Q6 |
| 7 | **trigger_support / sample_support** | candidate 自评信号支持度 → 驱动 abstain | H5（min trigger support guard） |
| 8 | **calibration_context** | 把合成 raw_score 映射到 0~1 = `P̂(prediction wrong)`；先验 / 工程判断；**不**从 v1 fail 拟合 | H1 / H5（calibration） |

| 锁定项 | 状态 |
|---|---|
| 本 checkpoint 只固定 family | ✅ |
| 给具体公式 / 系数 / 阈值 / 分位 / 校准曲线 | ❌ 否 |
| implementation 阶段也**不得**从 v1 fail 直接反推具体参数 | ✅ 永久禁止 |

## 7. output schema

`continuous_smoothing_candidate_v2.v1`（**新 schema**；不复用 v1 的 `continuous_smoothing_candidate.v1`）。

### 7.1 必填字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `schema_version` | str | `"continuous_smoothing_candidate_v2.v1"` |
| `as_of_date` | str | row 的 analysis_date |
| `data_cutoff_date` | str | 同 as_of_date（builder anti-lookahead） |
| `candidate_name` | str | `"continuous_smoothing_v2"`（lock） |
| `risk_score` | float \| None | 0~1（None 当 abstain / 缺数据）；含义见 §9 |
| `risk_bucket` | str | one of `{abstain, low, medium, high, extreme}` |
| `abstain_reason` | str \| None | 当 abstain 时非空字符串 |
| `trigger_support` | float \| None | 0~1 self-reported 信号支持度 |
| `features_used` | dict | 8 family raw + processed value |
| `warnings` | list[str] | candidate 内部 warning |
| `final_test_refusal` | bool | `as_of_date >= "2026-01-01"` → true + abstain + risk_score=None |

### 7.2 禁止字段

| 禁止字段 | 理由 |
|---|---|
| `gate_status` / `validation_passed` / `overall_status` | helper 职责；candidate 不下结论 |
| `hard_*` / `forced_exclusion` / `anti_false_exclusion_triggered` | hard / forced / required 永久封禁 |
| `final_direction` / `final_projection` | candidate 不影响 final prediction |
| `simulated_trade` / `no_trade` | 不接 trading |
| `_PROTECTION_LAYER_CONNECTED` | 永久封禁 |
| `predict_result_json` / `research_result_json` / `scan_result_json` | 不消费 DB raw payload |
| `actual_close_change` / `actual_state` / `direction_correct` / `pos20`（作为输入字段而非派生 feature 名）/ `five_state_projection` | 不消费 outcome / W4 future-leak |

## 8. abstain mode

### 8.1 触发条件

| 条件 | abstain_reason |
|---|---|
| `trigger_support` < candidate-internal 阈（具体值在 implementation 决定） | `"insufficient_trigger_support"` |
| 任一关键 feature family 计算失败 / NaN / 缺 OHLC 数据 | `"missing_features"` |
| `as_of_date >= final_test_cutoff` | `"final_test_refusal"`（`final_test_refusal=true`） |
| regime_labels 不可用 / unknown regime | `"regime_label_unavailable"` |

### 8.2 abstain ≠ pass / no_trade / hold / sell

abstain **不是**：
- ❌ 不是 candidate 通过 / pass
- ❌ 不是 production 层的 `no_trade`
- ❌ 不是 helper gate pass
- ❌ 不是 hold position / sell 信号

abstain **是**：
- ✅ candidate 拒绝在低支持度场景下下 exclusion 判断
- ✅ adapter 视为 `candidate_triggered=False`（与"低 risk"在 adapter 表面一致；但 candidate 自身保留 audit reason）
- ✅ 让 helper 不把这些 row 计入 false_exclusion / survival 计算 → 防 W1 那种 2 条 trigger 直接 collapse

### 8.3 阈值锁定

- 本 checkpoint **不**给 `trigger_support` 阈值
- 本 checkpoint **不**给 abstain 比例上限 / 下限
- 这些值由 v2 implementation 阶段决定

## 9. risk_score interpretation（**已明确固定**）

> **`risk_score = P̂(prediction will be wrong | features)`**

| 含义 | 说明 |
|---|---|
| 高 score | candidate 越确信"如果不 exclude 这条 prediction，它将会错" |
| 高 score + prediction actually correct | = false exclusion（candidate 错）|
| 低 score（abstain / low / medium） | candidate 不 exclude；helper false_exclusion 分母自然降低或被 abstain 排除 |
| 与 adapter mapping 对齐 | `risk_bucket ∈ {high, extreme}` → `candidate_triggered=True`；`abstain` → `candidate_triggered=False`；adapter / helper **不动** |
| 不允许 implementation 翻方向 | ✅ —— 任何 implementation 必须遵守此语义 |
| calibration 来源 | 先验 / 文献 / 工程判断；**不**从 v1 fail baseline 拟合 |

## 10. validation plan（7 步）

| # | 步骤 | 范围 |
|---|---|---|
| 1 | **v2 design checkpoint**（即本文） | 状态归档 |
| 2 | **v2 implementation**：新增 `services/continuous_smoothing_candidate_v2.py`（独立模块；**不** import v1；**不**复制 v1 SEED） | 8 family + abstain mode + risk_score 语义 + schema §7 |
| 3 | **focused tests**：新增 `tests/test_continuous_smoothing_candidate_v2.py`：unit + isolation + schema + abstain | full pytest 零回归 |
| 4 | **adapter compatibility check**（不改 adapter） | 验证 `risk_bucket ∈ {high, extreme}` 视 trigger，`abstain` 视 not-triggered；如需 adapter 扩展 → 独立 design |
| 5 | **single real W1-W4 validation run**（一次） | execution glue（如需新 v2 glue 则独立 design + impl + tests）；同 cutoff `2026-01-01`；output_dir 新 timestamp |
| 6 | **v2 result checkpoint** | 同 v1 result checkpoint 风格 + v1 baseline comparison |
| 7 | **v1 baseline comparison**（在 result checkpoint 内） | per-window false_exclusion_rate / survival_case_preservation / trigger rate / cross_window_variance / gate_status 量化对比 |

> 任一步 fail → 回 design；**不**自动进入下一步；**不** retry-until-pass。

## 11. v2 success criteria

v2 不能仅"比 v1 好一点"——必须满足：

| # | 标准 | 量化 |
|---|---|---|
| 1 | W1 `false_exclusion_rate` **低于 v1** 的 1.0 | 至少 ≤ helper 阈 0.10 |
| 2 | 4 个 window false_exclusion_rate 全 < v1 对应值 | 全部 ≤ 0.10 |
| 3 | 4 个 window `survival_case_preservation` 全部 > v1 的 0.0 | review 接受具体阈 |
| 4 | cross-window trigger rate 不极端失衡 | 不出现 1 : 24 量级；helper `cross_window_variance` gate pass |
| 5 | `worst_window` 不 collapse | worst_window false_exclusion_rate ≤ 0.10 |
| 6 | `final_test_touched = false`；`final_test_refusal = false` | 6 层 hard stop 仍生效 |
| 7 | DB / market_data.db / backup count unchanged | byte-for-byte |
| 8 | 7 gates 全 pass 或 review-approved waiver | 任一 fail 必须有解释 |
| 9 | output 4 文件 untracked + **不 commit raw** | 与 v1 同 |
| 10 | result checkpoint 含 v1 baseline comparison 表 | 量化对比 |
| 11 | **不** threshold sweep；**不**自动 promotion；**不**自动启 hard / Gate 5 / Gate 6 / `_PROTECTION_LAYER_CONNECTED` / 3R-5 / 3R-6 | 即便全 pass 也仅允许进入 review |

## 12. no-go rules（20 项）

| # | 条件 |
|---|---|
| 1 | 调 v1 `candidate_threshold` |
| 2 | 调 v1 SEED coefficients |
| 3 | 复制 v1 SEED 作为起点 |
| 4 | 给 v2 任何具体新 threshold / 新 coefficient / 新 feature 公式（在 design 阶段） |
| 5 | 实现 v2（在本 checkpoint 阶段） |
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

## 13. 允许下一步

| # | 候选 | 状态 |
|---|---|---|
| 1 | **Step 3R-3.3F-A v2 implementation**（在本 checkpoint 进 main 后启动） | ✅ 允许 |
| 2 | 必须新增独立模块：`services/continuous_smoothing_candidate_v2.py` | ✅ |
| 3 | **不** import v1（`services.continuous_smoothing_candidate`） | ✅ 强制 |
| 4 | **不**改 v1 任一已 merge 模块 / 测试 | ✅ 强制 |
| 5 | **不**改 adapter / helper 除非走 separate compatibility design | ✅ |
| 6 | tests 必须覆盖：schema valid / abstain（4 reason）/ final_test_refusal / forbidden imports / 字符串扫（hard / forced / required / trading / sweep） | ✅ |
| 7 | **不**跑 real validation（仅 unit / isolation / schema tests） | ✅ 强制 |
| 8 | **不**给 v2 具体 calibration 曲线 / threshold 数值在 design 阶段；具体参数在 implementation 阶段决定 | ✅ |
| 9 | implementation 完成后写 `tasks/step_3r3_3f_a_continuous_smoothing_v2_implementation_checkpoint.md`（命名待定） | ✅ |
| 10 | **不**自动进入 single real run；real run 必须用户单独指令触发 | ✅ |

> implementation 之后的顺序：v2 implementation + tests + checkpoint → 再 single real run（用户单独触发）→ v2 result checkpoint → v1 baseline comparison → 决定是否走新一轮 launch review 或 abandon。

## 14. 严守边界

本文是**纯 checkpoint markdown**：

- ❌ 没改任何代码（`services/*` / `ui/*` / `tests/*` / `scripts/*` 全部未触碰）
- ❌ 没改 DB schema / 没写 DB
- ❌ 没运行 replay
- ❌ 没**重新运行** real validation（baseline 仍是 v1 `20260507_065417` run）
- ❌ 没运行 prepare-only smoke
- ❌ 没读 v1 4 个 raw output json 任一字节
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
- ❌ 没改 Step 3R-3.3 / 3R-3.3A / 3R-3.3B / 3R-3.3C 系列 / 3R-3.3C-D / 3R-3.3E / 3R-3.3F design 已 merge 文档 / 实施
- ❌ 没改 Step 2G-8D / 8D.1A / 8D.2 / 8D.3 / 8D.4 文档或代码
- ❌ 没把 W4 / smoke / `logs/regime_validation/` / v1 raw output / `logs/prediction_log.jsonl` / DB backup / `agent_loop.py` / `.claude/worktrees/` 任一 commit 进 main
- ❌ 没创建任何新的 `logs/regime_validation/*` 子目录
- ❌ 没运行 `pytest`（本轮纯文档；测试基线维持 commit `7812b10` 时的 **2905 / 0 failed / 10 skipped**）
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*`
- ❌ 没用 v1 baseline 数据反推 v2 任何具体参数
- ❌ 没让 v1 fail 触发 retry / sweep / grid search
- ❌ 没让 v2 design 自动 promotion / 自动解锁 3R-5 / 3R-6
- ❌ 没实现 v2
- ✅ 只新增 1 份 markdown checkpoint 文档（本文件）
