# Step 3R-3.3F-A — Continuous Smoothing v2 Implementation Checkpoint

> 本文是 **checkpoint markdown** —— 不改代码、不写 DB、不重跑 replay / validation、不 commit / push、不接 trading API、不启 hard / forced、不改 required、不触碰 2026 final-test range、不 add `logs/regime_validation/` / W4 / smoke output / `logs/prediction_log.jsonl`、不处理 DB backup / stash / `.claude/worktrees/`、不调 v1 `candidate_threshold` / SEED coefficients / 6 metric / 7 gate threshold、不改 v1 / adapter / helper / 任一已 merge 测试、不进 3R-5 / 3R-6、不自动 promotion。

## 1. 当前完成状态

| 项 | 状态 | 来源 |
|---|---|---|
| v1 real W1-W4 validation single run + result checkpoint | ✅ 已 merge | output `logs/regime_validation/continuous_smoothing_v1_real_w1_w4_20260507_065417/`；commit `75f0ad5` |
| v1 postmortem design + checkpoint + report | ✅ 已 merge | commits `289f97b` / `c5bf686` / `fc44bcf` |
| v2 launch review design + checkpoint | ✅ 已 merge | commits `4fd1278` / `7c1a0e5` |
| v2 candidate design + checkpoint | ✅ 已 merge | commits `b16fce9` / `7eda5b4` |
| **v2 implementation**（独立模块 + 32 focused tests + §45 contract summary） | ✅ **已 merge** | commit `ce8b81e` |
| **本 checkpoint** —— 固定 v2 module / API / schema / risk_score 语义 / 8 family / abstain / final_test_refusal / isolation / tests / 当前限制 / 允许下一步 / 禁止事项 / 边界 | ⏳ **本文**（未 commit） | — |
| v2 single real validation run / v2 result checkpoint / v1 baseline comparison | ❌ 尚未启动 | — |

> v1 fail 已固定为 baseline；v2 实现已进入 main；v2 real validation 尚未运行；本 checkpoint 只固化 v2 implementation 状态。

## 2. 当前 main 状态

- `main` 最新 commit：`ce8b81e`
- commit message：`feat(diagnostics): add continuous smoothing v2 candidate`
- 上游：`origin/main` 已同步（push 完成 `7eda5b4..ce8b81e  main -> main`）
- 本步骤已 merge 文件：

| 路径 | 类型 | 行数 |
|---|---|---|
| `services/continuous_smoothing_candidate_v2.py` | 新增 | 508 |
| `tests/test_continuous_smoothing_candidate_v2.py` | 新增 | 571（32 focused tests） |
| `tasks/step_1_contract_pipeline_summary.md` | 修改 | +159（追加 §45） |

测试基线：

| 命令 | 结果 |
|---|---|
| `pytest tests/test_continuous_smoothing_candidate_v2.py -q` | **32 passed** |
| `pytest tests/test_continuous_smoothing_candidate_v2.py tests/test_continuous_smoothing_candidate.py tests/test_regime_validation_helper.py -q` | **96 passed**（零回归） |
| `pytest -q`（全量） | **2937 passed / 10 skipped / 0 failed / 26 warnings / 94 subtests** |

测试基线累积：Step 3R-3.3C-C-C 终点 **2905** → Step 3R-3.3F-A 终点 **2937**（+32 净增；2905 基线零回归）。

| 项 | 是否触碰 |
|---|---|
| 改 v1 service / adapter / helper / orchestrator / wrapper / provider / glue | ❌ 否 |
| 改 v1 测试 / 任何已 merge 测试 | ❌ 否 |
| 改 DB schema / 写 DB | ❌ 否 |
| 跑 replay / 跑 real validation / 跑 prepare-only smoke | ❌ 否 |
| 调 v1 `candidate_threshold` / SEED coefficients | ❌ 否 |
| 调 6 metric / 7 gate threshold | ❌ 否 |
| 接 yfinance / 网络 / trading API | ❌ 否 |
| 触碰 2026 final-test range | ❌ 否 |
| add `logs/regime_validation/` / W4 / smoke / DB backup / `agent_loop.py` / `.claude/worktrees/` / `logs/prediction_log.jsonl` | ❌ 否 |
| 进 3R-5 formula / 3R-6 simulator | ❌ 否 |
| 启 hard / forced / `_PROTECTION_LAYER_CONNECTED` | ❌ 否 |
| import v1 candidate（`services.continuous_smoothing_candidate`） | ❌ 否（永久封禁；ast + 字符串扫双锁） |

## 3. module path

```
services/continuous_smoothing_candidate_v2.py
```

定位：

| 项 | 状态 |
|---|---|
| **independent** v2 candidate module | ✅（不 import v1） |
| **sidecar only** | ✅（不进 production main path / Streamlit / trading） |
| **read-only** | ✅（不连 DB / 网络 / 不 mutate input） |
| **non-production** | ✅（仅 diagnostic helper） |
| 不复制 v1 SEED_COEFFICIENTS | ✅（v2 没有 seed_coefficients 字段） |
| 不修改 adapter / helper / orchestrator / wrapper / provider / glue | ✅（adapter 视 `risk_bucket ∈ {high, extreme}` → triggered；abstain → not-triggered，与 v1 一致） |

## 4. public API

```python
build_continuous_smoothing_candidate_v2(
    regime_labels: dict,
    *,
    as_of_date: str | None = None,
    final_test_cutoff: str = "2026-01-01",
) -> dict
```

模块常量：

| 常量 | 值 |
|---|---|
| `SCHEMA_VERSION` | `"continuous_smoothing_candidate_v2.v1"` |
| `CANDIDATE_NAME` | `"continuous_smoothing_v2"` |
| `DEFAULT_FINAL_TEST_CUTOFF` | `"2026-01-01"` |
| `FEATURE_FAMILY_KEYS` | 8 个 family（见 §7） |
| `ALLOWED_RISK_BUCKETS` | `frozenset({"abstain", "low", "medium", "high", "extreme"})` |

## 5. output schema

`continuous_smoothing_candidate_v2.v1`（11 必填字段）：

| 字段 | 类型 | 说明 |
|---|---|---|
| `schema_version` | str | `"continuous_smoothing_candidate_v2.v1"` |
| `as_of_date` | str | row analysis_date |
| `data_cutoff_date` | str | 同 as_of_date（builder anti-lookahead） |
| `candidate_name` | str | `"continuous_smoothing_v2"`（lock） |
| `risk_score` | float \| None | 0~1（abstain 时 None）；含义见 §6 |
| `risk_bucket` | str | one of `{abstain, low, medium, high, extreme}` |
| `abstain_reason` | str \| None | 当 abstain 时非空字符串（5 reason，见 §8） |
| `trigger_support` | float \| None | 0~1 = 已 finite 输入的比例 |
| `features_used` | dict | 8 family keys + `raw_inputs` audit |
| `warnings` | list[str] | candidate 内部 warning |
| `final_test_refusal` | bool | `as_of_date >= cutoff` 或 `regime_labels.final_test_refusal=True` 时 true |

risk_bucket 允许值：

| bucket | 含义 |
|---|---|
| `abstain` | candidate 拒绝下结论（low support / 缺数据 / final-test refusal） |
| `low` | risk_score < 0.33 |
| `medium` | 0.33 ≤ risk_score < 0.55 |
| `high` | 0.55 ≤ risk_score < 0.75 |
| `extreme` | risk_score ≥ 0.75 |

> bucket 边界 `0.33 / 0.55 / 0.75` 是 v2 工程默认；与 v1 `0.35 / 0.60 / 0.80` 不同；calibration_context 明确 `fitted_to_v1_baseline=false` / `fitted_to_outcome_data=false`。

## 6. risk_score semantics（**已锁定**）

> **`risk_score = P̂(prediction will be wrong | features)`**

| 含义 | 说明 |
|---|---|
| 高 score | candidate 越确信"如果不 exclude 这条 prediction，它将会错" |
| 高 score + prediction 实际正确 | = **false exclusion**（candidate 错） |
| 低 score（abstain / low / medium） | candidate 不 exclude；helper false_exclusion 分母自然降低或被 abstain 排除 |
| risk_score **不是** | overheat-risk / buy / sell / hold / validation pass / fail / final_direction / final_projection |
| adapter 映射 | `risk_bucket ∈ {high, extreme}` → `candidate_triggered=True`；`{abstain, low, medium}` → `candidate_triggered=False`；adapter / helper **不动** |
| calibration 来源 | 先验 + 工程判断；**不**从 v1 fail baseline 拟合 |

implementation **不允许翻方向**；任何后续修改必须遵守此语义。

## 7. feature families

`features_used` 包含 8 family + `raw_inputs` audit：

| # | family | 方向 | 触发条件（工程默认）|
|---|---|---|---|
| 1 | `trend_continuation_protection` | 负（保护强势 survivor） | `qqq_slope > 0.012 ∧ soxx_slope > 0.012 ∧ qqq_drawdown < 0.05 ∧ avgo_minus_soxx_20d ≥ 0` → `-0.4`；次级 `-0.2`；否则 `0` |
| 2 | `peer_confirmation_strength` | 负 | `peer_5d_aligned_pct ≥ 0.75` → `-0.3`；`≥ 0.50` → `-0.15`；否则 `0` |
| 3 | `overextension_without_confirmation` | 正 | `(pos20 ≥ 0.65 ∨ avgo_minus_soxx_20d ≥ 0.025)` 且无 peer/trend 确认 → `0.25` 或 `0.5` |
| 4 | `reversal_pressure` | 正 | `qqq_drawdown ≥ 0.10` → `0.4`；负 slopes → `0.3`；中等 drawdown + AVGO underperform → `0.2` |
| 5 | `regime_stability` | 双向 | `monthly_max_abs ≥ 0.07` → `+0.2`；`< 0.03` → `-0.1` |
| 6 | `monthly_shock_context` | 正 | shock + drawdown combo → `0.3`；shock alone → `0.1` |
| 7 | `trigger_support` | float | 8 raw input 的 finite 比例；`< 0.5` → abstain |
| 8 | `calibration_context` | descriptor | `{method, anchored_via, fitted_to_v1_baseline=false, fitted_to_outcome_data=false, trigger_support_threshold, bucket_boundaries}` |

`risk_score = sigmoid(family[1..6] sum)`；7（trigger_support）控 abstain；8（calibration_context）是 descriptor。

| 锁定项 | 状态 |
|---|---|
| `features_used` 还包含 `raw_inputs` audit 字段 | ✅ |
| **没有** `seed_coefficients` 字段 | ✅ |
| **不**声称 optimized | ✅（测试断言无 `optimized_to_v1` / `validated_against_baseline` / `tuned_via_baseline` / `is_validated`） |
| `calibration_context.fitted_to_v1_baseline = false` | ✅ |
| `calibration_context.fitted_to_outcome_data = false` | ✅ |

## 8. abstain behavior

abstain 触发 5 reason：

| # | abstain_reason | 触发条件 | `final_test_refusal` |
|---|---|---|---|
| 1 | `final_test_range_refusal` | `as_of_date >= "2026-01-01"` | `true` |
| 2 | `final_test_range_refusal` | `regime_labels.final_test_refusal=True` 透传（warning 多一条 `regime_labels_final_test_refusal_propagated`） | `true` |
| 3 | `missing_raw_features` | `regime_labels.raw_features` 不是 dict | `false` |
| 4 | `low_trigger_support` | `trigger_support < 0.5`（即 8 raw input 中 finite 数 < 4） | `false` |
| 5 | `missing_as_of_date` | `as_of_date` 不是 str / 空字符串 | `false` |

abstain payload 通用属性：

| 属性 | 值 |
|---|---|
| `risk_score` | **`None`**（避免 adapter 误触发） |
| `risk_bucket` | `"abstain"` |
| `abstain_reason` | 非空字符串（5 之一） |
| adapter 映射 | `candidate_triggered=False`（与"低 risk"在 adapter 表面一致；但保留 audit reason） |
| abstain ≠ pass / no_trade / hold / sell | ✅（与 v2 design §7 一致） |
| `features_used` 仍含 8 family keys + `raw_inputs` | ✅（即便 abstain 也保留 audit） |

## 9. final_test_refusal behavior

| 检查 | 行为 |
|---|---|
| `as_of_date >= "2026-01-01"` | abstain + `final_test_refusal=true` + `abstain_reason="final_test_range_refusal"` + warning `"final_test_range_refusal"` |
| `regime_labels.final_test_refusal=True` 透传 | abstain + `final_test_refusal=true` + `abstain_reason="final_test_range_refusal"` + warning `"regime_labels_final_test_refusal_propagated"` |
| 输出 `risk_score` | `None`（拒绝下结论） |
| 输出 `risk_bucket` | `"abstain"` |
| `warnings` | 包含 refusal reason 字符串 |
| 6 层 hard stop | 与 v1 一致（cutoff 仍锁 2026-01-01；wrapper / orchestrator / provider / candidate / adapter / helper 全链路保留） |
| 2026 范围消费 | ❌ 不消费 |

## 10. isolation / forbidden imports

`test_no_forbidden_imports` 锁定 27 项 ast.walk import：

| 类别 | 模块 |
|---|---|
| 网络 | `yfinance` / `requests` / `urllib` / `urllib3` / `httpx` |
| trading | `longbridge` / `broker` / `paper_trade` |
| sqlite / DB 写 | `sqlite3` / `services.prediction_store` / `services.outcome_capture` |
| production engine | `services.confidence_engine` / `contradiction_engine` / `risk_model` / `soft_metadata_simulator` / `anti_false_exclusion_dashboard` / `regime_diagnostics_dashboard` / `protection_layer_diagnostics` / `historical_replay_training` |
| validation pipeline | `services.regime_validation_helper` / `replay_validation_record_adapter` / `real_regime_label_provider` / `regime_labels_builder` |
| **v1 candidate** | **`services.continuous_smoothing_candidate`（永久封禁）** |
| validation scripts | `scripts.run_continuous_smoothing_validation` / `run_real_continuous_smoothing_validation` / `run_real_continuous_smoothing_validation_execute` |
| production app | `predict` / `scanner` / `streamlit` / `ui.protection_layer_diagnostics_renderer` |

字符串扫（5 类）：

| 类别 | 项目 |
|---|---|
| no v1 string ref | `services.continuous_smoothing_candidate ` / `from services.continuous_smoothing_candidate import` |
| hard / required / trading | `hard_exclusion_allowed` / `forced_exclusion` / `anti_false_exclusion_triggered` / `_PROTECTION_LAYER_CONNECTED` / `simulated_trade` / `no_trade` / `final_direction` / `final_projection`（8 项） |
| validation pass/fail | `gate_status` / `validation_passed` / `overall_status` / `primary_blocker` / `hard_gate_status`（5 项） |
| threshold sweep / grid | `thresholds = [` / `for threshold in` / `for t in thresholds` / `candidate_thresholds` / `threshold_grid` / `optimize_threshold` / `sweep_threshold` / `grid_search`（8 项） |
| not-fitted-claim | `optimized_to_v1` / `validated_against_baseline` / `tuned_via_baseline` / `is_validated`（4 项；并断言 calibration_context 中 fitted flag = false） |
| W4 future-leak in output | `actual_close_change` / `actual_state` / `direction_correct` / `five_state_projection` / `predict_result_json` / `research_result_json` / `scan_result_json` 等不出现在输出字段 |

## 11. tests

### 11.1 测试结果

| 命令 | 结果 |
|---|---|
| `pytest tests/test_continuous_smoothing_candidate_v2.py -q` | **32 passed** |
| `pytest tests/test_continuous_smoothing_candidate_v2.py tests/test_continuous_smoothing_candidate.py tests/test_regime_validation_helper.py -q` | **96 passed**（零回归） |
| `pytest -q`（全量） | **2937 passed / 10 skipped / 0 failed / 26 warnings / 94 subtests** |

### 11.2 覆盖矩阵（32 tests / 9 类）

| 测试类 | 数量 | 覆盖点 |
|---|---|---|
| `OutputSchemaTests` | 5 | 11 必填字段 / schema_version / candidate_name / `risk_bucket ∈ ALLOWED_RISK_BUCKETS` / 8 family + raw_inputs / 21 项 forbidden 输出字段 |
| `RiskScoreRangeTests` | 5 | risk_score in (0, 1) / 4 个 bucket（low / medium / high / extreme）通过 fixture 可达 |
| `AbstainTests` | 7 | `as_of_date == cutoff` / `> cutoff` / `regime_labels.final_test_refusal` / 缺 raw_features / 低 trigger_support / 缺 as_of_date / abstain payload 仍含 8 family keys |
| `TriggerSupportTests` | 2 | 顶层 + features_used 一致 / 全输入 ⇒ 1.0 |
| `IsolationFromLeakTests` | 1 | outcome / W4 future-leak 字段（actual_close_change / direction_correct / actual_state / five_state_projection / predict_result_json / research_result_json / scan_result_json）注入后 → 输出不变 |
| `InputNotMutatedTests` | 1 | 多次调用后 `regime_labels` 字典不变 |
| `DeterminismTests` | 2 | same input ⇒ same output / calibration_context 声明 not fitted |
| `AsOfDateOverrideTests` | 2 | 显式 as_of_date 覆盖 label 字段 / minimal regime_labels fixture works |
| `IsolationTests` | 7 | 27 项 forbidden import / no v1 string ref / 8 hard-required-trading / 5 validation pass-fail / 8 threshold-sweep / 4 fitted-claim（含 calibration_context flag 断言） / cutoff 默认值 lock |

## 12. 当前限制

| 限制 | 状态 |
|---|---|
| v2 real validation 仍未运行 | ❌ 未跑 |
| v2 `output_dir` 仍未创建（`logs/regime_validation/continuous_smoothing_v2_real_w1_w4_<TS>/`） | ❌ 未存在 |
| v2 `regime_validation_report.json` / `replay_validation_records.json` / `regime_validation_summary.md` / `run_manifest.json` | ❌ 未生成 |
| v2 candidate 是否优于 v1 | ❓ 未知 |
| v1 vs v2 baseline comparison | ❓ 未生成 |
| v2 result checkpoint | ❌ 未启动 |
| first v2 real run 必须用户单独指令触发 | ✅ 强制 |
| v2 是否解锁 3R-5 / 3R-6 | ❌ 永远不（即便 v2 全 pass） |
| v2 是否自动 promotion / 自动启 hard | ❌ 永远不 |

## 13. 允许下一步

| # | 候选 | 状态 |
|---|---|---|
| 1 | **v2 single real validation run**（用户单独确认指令触发） | ✅ 允许（在本 checkpoint 进 main 后） |
| 2 | 必须使用**新 timestamp output_dir**（如 `logs/regime_validation/continuous_smoothing_v2_real_w1_w4_YYYYMMDD_HHMMSS/`） | ✅ 强制 |
| 3 | 必须**同 cutoff** `"2026-01-01"`；6 层 hard stop 全保留 | ✅ |
| 4 | 必须**不写 DB**；DB / market_data.db / backup count 三组 fingerprint 全 unchanged | ✅ |
| 5 | 必须**不 commit raw output**（4 文件保持 untracked） | ✅ |
| 6 | 必须写 **v2 result checkpoint** + **v1 baseline comparison**（量化对比表：per-window false_exclusion_rate / survival_case_preservation / trigger rate / cross_window_variance / gate_status v1 vs v2） | ✅ |
| 7 | 实现路径：复用现有 wrapper（`build_real_validation_inputs`）+ adapter / helper；execution glue 是否需要 v2 适配 → 由 user 决定（adapter / helper 已与 v2 兼容；可能直接复用 v1 glue 仅替换 candidate factory） | ✅ |
| 8 | wrapper / candidate v1 / adapter / helper / orchestrator / provider / glue / labels builder / candidate v2 现有行为 | ❌ 不改（仅只读调用） |
| 9 | hard / required upgrade / Gate 5 / Gate 6 / `_PROTECTION_LAYER_CONNECTED` | ❌ 永久封禁 |
| 10 | 直接进入 Step 3R-5 / 3R-6 | ❌ 永久封禁 |

## 14. 禁止事项

| # | 禁止 | 理由 |
|---|---|---|
| 1 | **不**自动跑 validation | 必须用户单独确认；本 checkpoint 不触发 run |
| 2 | **不**新增 `.py` 文件（在本 checkpoint 范围内） | 本步骤是 checkpoint only |
| 3 | **不**新增测试（在本 checkpoint 范围内） | 测试已在 implementation 步骤完成 |
| 4 | **不**写 DB / **不**改 DB schema | 全程 read-only |
| 5 | **不** sweep / **不** grid search / **不** retry-until-pass | v2 也不允许从 first real run 反推参数 |
| 6 | **不**调 v1 `candidate_threshold` / SEED coefficients | v1 永久 freeze |
| 7 | **不**调 v2 工程默认（trigger_support 阈 / bucket 边界）基于 v1 fail baseline | calibration_context 必须保持 not-fitted |
| 8 | **不**改 v1 `services/continuous_smoothing_candidate.py` 任一字符 | 永久 freeze |
| 9 | **不**改 adapter / helper / orchestrator / wrapper / provider / glue / labels builder / 任何已 merge 测试 | 永久 freeze |
| 10 | **不**启 hard / forced / `anti_false_exclusion_triggered` / `_PROTECTION_LAYER_CONNECTED` | 三重 NO-GO |
| 11 | **不**改 04 / 05 / 07 required | Step 2G 全程边界 |
| 12 | **不**触碰 2026 final-test range；cutoff 仍锁 `"2026-01-01"` | 6 层 hard stop |
| 13 | **不**接 trading（`longbridge` / `broker` / `paper_trade`） | 永久封禁 |
| 14 | **不**接 yfinance / requests / urllib / 任何网络 | 永久封禁 |
| 15 | **不**直接进入 Step 3R-5 formula / 3R-6 simulator | 必须先过 v2 result checkpoint + 新一轮独立 launch review |
| 16 | **不** commit validation outputs | `logs/regime_validation/` 全部 untracked |
| 17 | **不** commit 本 checkpoint 之外的产物 | 本轮不 commit / push |
| 18 | **不** import v1（`services.continuous_smoothing_candidate`） | 永久封禁；ast + 字符串扫双锁 |
| 19 | **不**让 v2 fail / pass 自动 promotion | 永久封禁 |
| 20 | **不**用 first v2 real run 数据反推参数 | 阈值 / coefficient 变更必须经独立 launch review |
| 21 | **不**触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*` | 历史防护 |

## 15. 下一步建议

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **commit 本 checkpoint** | 把 §1-16 implementation 状态固化到 main | 本轮 / 下一轮 |
| 2 | **v2 single real validation run**（**用户单独确认指令触发**） | 复用 wrapper + 切换到 `build_continuous_smoothing_candidate_v2`；新 timestamp output_dir；同 cutoff `2026-01-01`；DB / market_data / backup 三组 fingerprint 守护；output 4 文件本地 untracked | 高（本 checkpoint 进 main 后；用户单独触发） |
| 3 | **v2 result checkpoint** + **v1 baseline comparison** | 摘要 / report_status / per-window / fail_reason / DB guard verification / output 4 文件结构（不 commit raw json）/ v1 vs v2 量化对比表 | 中（v2 real run 完成后） |
| 4 | 根据 v2 result 决定是否进入新一轮 review；**不**直接进入 3R-5 / 3R-6 | v2 pass 仅允许 review；v2 fail 需回 candidate / threshold design 重设（同 v1 routing） | — |
| 5 | **不推荐**直接 Step 3R-5 formula | 必须先过 v2 result checkpoint + 新一轮 launch review | ❌ |
| 6 | **不推荐** Step 3R-6 simulator | 必须先过 3R-5 launch review | ❌ |
| 7 | **不推荐**让 v2 first real run pass 自动启 hard / Gate 5 / Gate 6 | 与 3R-3.3 §11 一致 | ❌ |
| 8 | **不推荐**升级 04 required | Step 2G 全程边界 | ❌ |
| 9 | **不推荐**触碰 2026 final-test range | 永久封禁 | ❌ |
| 10 | **不推荐**让 `_PROTECTION_LAYER_CONNECTED` 翻 True | 与 v1 / 3R-0 / 3R-4 一致 | ❌ |
| 11 | **不推荐**重跑 W1-W3 replay | DB 已足够 | ❌ |
| 12 | **不推荐**用 v2 first real run 数据反推 v2 任何具体参数 | 阈值变更必须经 launch review | ❌ |

**关键判断**：顺序 = 本 checkpoint → v2 single real run（用户单独触发）→ v2 result checkpoint + v1 baseline comparison → review 决定 → 新一轮 3R-5 launch review（仅 v2 pass 路径）→ 3R-6 simulator。任何一步 fail → 回到 design 层重新设计，**不**自动进入下一步。

## 16. 严守边界

本文是**纯 checkpoint markdown**：

- ❌ 没改任何代码（`services/*` / `ui/*` / `tests/*` / `scripts/*` 全部未触碰）
- ❌ 没改 DB schema / 没写 DB
- ❌ 没运行 replay
- ❌ 没**重新运行** real validation（baseline 仍是 v1 `20260507_065417` run；v2 实现已 merge 但未跑 real run）
- ❌ 没运行 prepare-only smoke
- ❌ 没读 v1 4 个 raw output json 任一字节
- ❌ 没修改 v1 4 个 raw output json
- ❌ 没改 `run_predict` / `predict.py` / `scanner.py` / `prediction_store.py` / `app.py`
- ❌ 没改 `services/regime_features_builder.py` / `regime_labels_builder.py` / `regime_validation_helper.py` / `continuous_smoothing_candidate.py`（v1） / `continuous_smoothing_candidate_v2.py`（本步骤已 merge；本 checkpoint 不再改） / `replay_validation_record_adapter.py` / `historical_replay_training.py` / `real_regime_label_provider.py` / 任何 ui 模块 / 任何 builder
- ❌ 没改 `scripts/run_continuous_smoothing_validation.py` / `run_real_continuous_smoothing_validation.py` / `run_real_continuous_smoothing_validation_execute.py`
- ❌ 没改 `tests/test_run_continuous_smoothing_validation.py` / `test_run_real_continuous_smoothing_validation.py` / `test_real_regime_label_provider.py` / `test_run_real_continuous_smoothing_validation_execute.py` / `test_continuous_smoothing_candidate.py` / `test_continuous_smoothing_candidate_v2.py`（本步骤已 merge；本 checkpoint 不再改） / 任何已 merge 测试
- ❌ 没改 04 / 05 / 07 任何 required 字段
- ❌ 没启用 `hard` / `forced_exclusion` / `anti_false_exclusion_triggered`
- ❌ 没接 `yfinance` / `requests` / 任何网络
- ❌ 没接 trading API / `longbridge` / `broker` / `paper_trade`
- ❌ 没让 `_PROTECTION_LAYER_CONNECTED` 翻 True
- ❌ 没让 `hard_gate_status.protection_layer_connected` 自动 pass
- ❌ 没改 `hard_exclusion_allowed` / `primary_blocker` 派生
- ❌ 没触碰 2026-01-01 之后 final-test range
- ❌ 没改 Step 3R-4 protocol thresholds（6 metric / 7 gate / 10 no-go）
- ❌ 没改 Step 3R-2 helper / 3R-3.1 candidate（v1）/ 3R-4.2 helper / 3R-4.3A adapter 行为
- ❌ 没改 Step 3R-3.3 / 3R-3.3A / 3R-3.3B / 3R-3.3C 系列 / 3R-3.3C-D / 3R-3.3E / 3R-3.3F design / checkpoint / 3R-3.3F-A 已 merge 文档 / 实施
- ❌ 没改 Step 2G-8D / 8D.1A / 8D.2 / 8D.3 / 8D.4 文档或代码
- ❌ 没把 W4 / smoke / `logs/regime_validation/` / v1 raw output / `logs/prediction_log.jsonl` / DB backup / `agent_loop.py` / `.claude/worktrees/` 任一 commit 进 main
- ❌ 没创建任何**新的** `logs/regime_validation/*` 子目录
- ❌ 没运行 `pytest`（本轮纯文档；测试基线维持 commit `ce8b81e` 时的 **2937 / 0 failed / 10 skipped**）
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*`
- ❌ 没调 v1 `candidate_threshold` / SEED coefficients
- ❌ 没调 v2 工程默认（trigger_support 阈 / bucket 边界）
- ❌ 没用 v1 baseline 数据反推 v2 任何具体参数
- ❌ 没让 v1 fail / v2 implementation 触发 retry / sweep / grid search
- ❌ 没让 v2 implementation 自动 promotion / 自动解锁 3R-5 / 3R-6
- ❌ 没真实运行 v2 W1-W4 validation
- ✅ 只新增 1 份 markdown checkpoint 文档（本文件）
