# Step 3R-3.3F-D — Continuous Smoothing v2 Real Validation Result Checkpoint

> 本文是 **checkpoint markdown** —— 不改代码、不写 DB、不重跑 replay / validation、不 commit / push、不接 trading API、不启 hard / forced、不改 required、不触碰 2026 final-test range、不 add `logs/regime_validation/` / W4 / smoke output / `logs/prediction_log.jsonl`、不处理 DB backup / stash / `.claude/worktrees/`、不调 v1 / v2 任一 threshold / SEED / coefficient / 工程默认、不 retry / 不 sweep / 不 auto-promotion、不进 3R-5 / 3R-6。

## 1. 当前完成状态

| 项 | 状态 | 来源 |
|---|---|---|
| v1 real W1-W4 validation single run + result checkpoint | ✅ 已 merge | output `logs/regime_validation/continuous_smoothing_v1_real_w1_w4_20260507_065417/`；commit `75f0ad5` |
| v1 postmortem report | ✅ 已 merge | commit `fc44bcf` |
| v2 candidate design + checkpoint + implementation + checkpoint | ✅ 已 merge | commits `b16fce9` / `7eda5b4` / `ce8b81e` / `95ded24` |
| v2 execution path design + checkpoint + implementation + checkpoint | ✅ 已 merge | commits `18a41d8` / `fe76252` / `9192a5a` / `0a753c2` |
| **v2 single real W1-W4 validation run** | ✅ **已完成（一次）** | exit_code=0；output `logs/regime_validation/continuous_smoothing_v2_real_w1_w4_20260507_091823/` |
| 4 个 v2 output 文件全部生成 | ✅ | replay_validation_records.json / regime_validation_report.json / regime_validation_summary.md / run_manifest.json |
| `avgo_agent.db` mtime / size unchanged | ✅ | DB guard 通过 |
| `data/market_data.db` mtime / size unchanged | ✅ | DB guard 通过 |
| `avgo_agent.db.backup_*` count unchanged（7 → 7） | ✅ | backup guard 通过 |
| `run_manifest.final_test_touched = false` | ✅ | 2026 范围未触碰 |
| `report.final_test_refusal = false` | ✅ | 6 层 hard stop 全部生效 |
| **v2 candidate 当前版本未通过** | ❌ **report_status=fail（legal fail outcome）** | W1 false_exclusion_rate=1.0；7 gate 全 fail |
| **本 checkpoint** —— 固化真实 v2 run 结果（run metadata / records / per-window / report / gate / DB / final-test / v1 baseline comparison / legal-fail interpretation / no-go / 下一步） | ⏳ **本文**（未 commit） | — |

> **不**改代码、**不**调参、**不**重跑；本 checkpoint 仅为结果归档 + v1 baseline comparison。

## 2. run metadata

| 项 | 值 |
|---|---|
| `main` 最新 commit | `0a753c2`（`docs(contract): Step 3R-3.3F-C v2 execution path implementation checkpoint`） |
| run timestamp | `20260507_091823` |
| `output_dir` | `logs/regime_validation/continuous_smoothing_v2_real_w1_w4_20260507_091823/` |
| invoking script | `scripts/run_real_continuous_smoothing_validation_execute_v2.py`（commit `9192a5a`） |
| explicit opt-in flag | `--run-once-real-validation-v2` |
| `candidate_name` | `continuous_smoothing_v2`（v2 lock；v1 candidate 永久封禁） |
| `candidate_threshold` | `0.60`（v2 first-run lock；语义 `P̂(prediction wrong)`，与 v1 数值同但语义不同） |
| `final_test_cutoff` | `"2026-01-01"`（lock；非 cutoff → exit 2） |
| exit_code | **0** |
| stdout | `real_validation_execution_summary_v2.v1` JSON |
| invocation | `PYTHONPATH=. python3 scripts/run_real_continuous_smoothing_validation_execute_v2.py --run-once-real-validation-v2 --db-path avgo_agent.db --w4-jsonl logs/historical_training/three_system_w4_2024_08_2025_12/three_system_replay_results.jsonl --w4-manifest logs/historical_training/three_system_w4_2024_08_2025_12/validation_ready_manifest.json --avgo-csv data/AVGO.csv --nvda-csv data/NVDA.csv --soxx-csv data/SOXX.csv --qqq-csv data/QQQ.csv --candidate-threshold 0.60 --final-test-cutoff 2026-01-01 --output-dir <output_dir>` |

## 3. output files

| 文件 | 大小 | schema |
|---|---|---|
| `replay_validation_records.json` | 1,198,292 bytes | `replay_validation_records.v1` |
| `regime_validation_report.json` | 3,329 bytes | `regime_validation_report.v1` |
| `regime_validation_summary.md` | 622 bytes | human-readable |
| `run_manifest.json` | 8,608 bytes | `regime_validation_run_manifest.v1` |

处置规则：

- ✅ `output_dir` 保持 **untracked**（`logs/regime_validation/` 已 gitignore）
- ❌ raw json **不**进 main；本 checkpoint 只复制关键 summary 字段
- ✅ `regime_validation_summary.md` 内容已抽取进本 checkpoint §7
- ❌ 不 commit `output_dir` 任何子文件；不 `git add`；不修改
- ✅ 可删除 / 可重跑（新 timestamp = 新目录）；本次 run 留作 v2 fail baseline

## 4. run_manifest summary

| 字段 | 值 |
|---|---|
| stdout summary `schema_version` | `real_validation_execution_summary_v2.v1` |
| run_manifest `schema_version` | `regime_validation_run_manifest.v1`（与 v1 共享，protocol 层） |
| `candidate_name` | `continuous_smoothing_v2`（lock） |
| `candidate_threshold` | `0.60` |
| `fold_count` | `4` |
| `windows` | `["W1", "W2", "W3", "W4"]` |
| `final_test_cutoff` | `"2026-01-01"` |
| `final_test_touched` | **`false`** |
| `w4_manifest_status` | `"ok"` |
| `records_loaded` | `639` |
| `records_adapted` | `526` |
| `report_status` | `"fail"` |
| `warnings_count` | `114`（113 × `record_skipped` + 1 × `w4_manifest_not_required`） |

skipped 解释：

- 113 条 `record_skipped:missing_or_invalid_direction_correct:<date>`（W4 jsonl 中尚无 paired outcome 的近端 row；与 v1 同源；非系统错误）
- 1 条 `w4_manifest_not_required`（helper 阶段 require=False 标识；非错误）

## 5. records summary

| 项 | 值 | 来源 |
|---|---|---|
| `records_loaded` | **639** | wrapper 装配的 input bundle（与 v1 同 input） |
| ↳ W1-W3 DB rows | 286 | wrapper `load_w1_w3_rows_from_db(...)` |
| ↳ W4 jsonl rows | 353 | wrapper `load_w4_rows_from_jsonl(...)`（filtered for cutoff） |
| `records_adapted` | **526** | adapter `build_replay_validation_records(...)` 输出 |
| ↳ 差额 113 = skipped | 113 × `record_skipped:missing_or_invalid_direction_correct` | adapter outcome enforce |
| W1 / W2 / W3 / W4 全部有 records | ✅ | `110 / 93 / 83 / 240` |

## 6. per-window distribution

| window | total_records | `candidate_triggered=True` | `candidate_triggered=False` | trigger_rate |
|---|---|---|---|---|
| W1 | 110 | **1** | 109 | **0.91%** |
| W2 | 93 | 13 | 80 | 13.98% |
| W3 | 83 | 5 | 78 | 6.02% |
| W4 | 240 | 78 | 162 | 32.50% |
| **Total** | **526** | **97** | **429** | **18.44%** |

观察：

- v2 在 W1 触发**仅 1 条**（vs v1 的 2 条），统计稳定性更差（min_sample fail 更严重）
- v2 总 trigger 97 < v1 总 trigger 136（−29%）；abstain mode + 不同 family 让 trigger 更克制
- W4 仍是触发最多的 window；trigger rate 从 v1 的 44.6% 降到 32.5%

## 7. report summary

| 字段 | 值 |
|---|---|
| `schema_version` | `regime_validation_report.v1` |
| `candidate_name` | `continuous_smoothing_v2` |
| `candidate_kind` | `smoothing` |
| `overall_status` | **`fail`** |
| `report_status`（manifest 透传） | `fail` |
| `worst_window` | **`W1`** |
| `final_test_refusal` | **`false`** |
| `gate_status` | 7 gate 全部 present |

`regime_validation_summary.md` 原文：

```
# Continuous Smoothing v2 Validation Run Summary

- candidate_name: continuous_smoothing_v2
- candidate_threshold: 0.6
- fold_count: 4
- final_test_cutoff: 2026-01-01
- final_test_touched: False
- w4_manifest_status: ok
- records_loaded: 639
- records_adapted: 526
- report_status: fail
- overall_status: fail
- worst_window: W1
- fail_reason: minimum_window_sample_size,false_exclusion_rate,net_benefit,accuracy_delta_vs_baseline,cross_window_variance,survival_case_preservation,no_single_window_collapse at W1: false_exclusion_rate=1.0000_above_0.1

_v2 read-only diagnostic; pass does not grant production permission._
```

## 8. gate_status summary

| gate | status |
|---|---|
| `minimum_window_sample_size` | **fail** |
| `false_exclusion_rate` | **fail** |
| `net_benefit` | **fail** |
| `accuracy_delta_vs_baseline` | **fail** |
| `cross_window_variance` | **fail** |
| `survival_case_preservation` | **fail** |
| `no_single_window_collapse` | **fail** |

7/7 fail。helper 在 worst_window=W1 上的连锁结果：W1 触发**仅 1 条**已不满足 `minimum_window_sample_size`，且这 1 条是 survivor → false_exclusion_rate=1/1=1.0 触顶；其余 5 gate 在 W1 上同样不达阈，accumulated 成 7 全 fail。

## 9. v1 baseline comparison

| metric | v1 | v2 | conclusion |
|---|---|---|---|
| `overall_status` | `fail` | `fail` | **no improvement** |
| `report_status` | `fail` | `fail` | **no improvement** |
| `worst_window` | `W1` | `W1` | **no improvement** |
| `final_test_touched` | `false` | `false` | same（both safe） |
| `records_loaded` | 639 | 639 | same input（wrapper 共用） |
| `records_adapted` | 526 | 526 | same adapted count |
| triggered total | 136 | **97** | v2 more conservative（−29%） |
| trigger rate（total） | 25.9% | **18.4%** | v2 lower |
| W1 `false_exclusion_rate` | **1.0000** | **1.0000** | **no improvement**（W1 触发 1/1 仍是 survivor） |
| `survival_case_preservation`（all windows） | 0.0 / 0.0 / 0.0 / 0.0 | 0.0 / 0.0 / 0.0 / 0.0 | **no improvement**（结构性问题持平） |
| gate status | 7 fail | 7 fail | **no improvement** |
| schema_version（execution summary） | `real_validation_execution_summary.v1` | `real_validation_execution_summary_v2.v1` | v2 独立 schema |
| `candidate_name` | `continuous_smoothing_v1` | `continuous_smoothing_v2` | v2 独立 candidate |

## 10. per-window false_exclusion comparison

| window | v1 | v2 | change |
|---|---|---|---|
| W1 | 1.0000 | **1.0000** | flat |
| W2 | 0.5217 | 0.5385 | **worse by +1.7pp** |
| W3 | 0.5000 | 0.6000 | **worse by +10pp** |
| W4 | 0.5421 | 0.5641 | **worse by +2.2pp** |

观察：

- W1 持平触顶（1.0）；v1 / v2 在 W1 触发的 row 都是 survivor
- W2 / W3 / W4 v2 反而**略差**（v2 触发更少但触发的 row 中 survivor 比例更高）
- v2 没有解决"触发即误排 survivor"的结构问题

## 11. per-window net_benefit comparison

| window | v1 | v2 | change |
|---|---|---|---|
| W1 | -0.0096 | -0.0048 | slightly better, **still negative** |
| W2 | +0.0088 | +0.0016 | **worse**（v2 W2 几乎不挣钱） |
| W3 | -0.0040 | -0.0114 | **worse** |
| W4 | -0.0539 | -0.0429 | slightly better, **still negative** |

观察：

- W1 / W4 v2 net_benefit 略好但仍负（trigger 减少自然导致 negative benefit 体量缩小）
- W2 / W3 v2 反而更差
- 没有任何 window 实现 net_benefit > +0.05（helper gate 阈值）

## 12. legal fail interpretation

per design / impl checkpoint，本次 v2 结果**是 legal fail outcome**：

| 判定 | 状态 |
|---|---|
| pipeline error？ | ❌ 否 —— exit 0 / 4 文件齐 / schema valid / DB unchanged |
| schema bug？ | ❌ 否 —— `regime_validation_report.v1` / `replay_validation_records.v1` / `regime_validation_run_manifest.v1` / `real_validation_execution_summary_v2.v1` 全部字段齐 |
| IO 错误？ | ❌ 否 —— 4 文件成功落地 |
| DB guard 失败？ | ❌ 否 —— 三组 fingerprint 全 unchanged |
| final-test guard 失败？ | ❌ 否 —— `final_test_touched=false` / `final_test_refusal=false` / 6 层 hard stop 全部生效 |
| forbidden import？ | ❌ 否 —— v2 isolation tests + ast 锁定双锁 |
| v1 冒充 v2？ | ❌ 否 —— summary `candidate_name="continuous_smoothing_v2"`；schema `real_validation_execution_summary_v2.v1`；spy 测试已锁 |
| **fail 含义** | candidate `continuous_smoothing_v2` 在 v2 工程默认 + 真实 W1-W4 数据上**仍不 eligible**；W1 false_exclusion 触顶；survival_case_preservation 全 0.0 结构问题未解决 |

按 design / impl checkpoint 的明确规则：

- ❌ **不**根据本次结果直接调 v2 阈值 / 工程默认 / family 公式
- ❌ **不**调 v1 任何参数
- ❌ **不**调 6 metric / 7 gate threshold（3R-4 protocol 锁定）
- ❌ **不**自动 retry
- ❌ **不**自动 sweep
- ❌ **不**把 fail 当系统故障 / 不重写代码
- ❌ **不**自动启 hard / Gate 5 / Gate 6 / `_PROTECTION_LAYER_CONNECTED`
- ❌ **不**自动进入 3R-5 / 3R-6
- ✅ 把 v2 fail 与 v1 fail 一起作为 baseline 留存，等待**新一轮 candidate / risk_score direction / exclusion target redesign**

## 13. final-test guard verification

| 检查 | 状态 |
|---|---|
| `run_manifest.final_test_touched = false` | ✅ |
| `report.final_test_refusal = false` | ✅ |
| `final_test_cutoff = "2026-01-01"` | ✅ |
| 6 层 hard stop（wrapper DB filter / wrapper W4 jsonl filter / orchestrator row filter / provider refusal / candidate refusal / adapter+helper+report refusal） | ✅ 全部生效 |
| 任一 row `as_of_date >= cutoff` 被消费 | ❌ 没有 |
| 任一 row `prediction_for_date >= cutoff` 被消费 | ❌ 没有 |
| 2026-01-01 之后 final-test range 是否被读取 | ❌ 没有 |

## 14. DB / market_data / backup verification

| object | before | after | unchanged |
|---|---|---|---|
| `avgo_agent.db` mtime_ns | `1777833249.653954308` | `1777833249.653954308` | ✅ |
| `avgo_agent.db` size_bytes | `11,206,656` | `11,206,656` | ✅ |
| `data/market_data.db` mtime_ns | `1777392167.547992024` | `1777392167.547992024` | ✅ |
| `data/market_data.db` size_bytes | `13,127,680` | `13,127,680` | ✅ |
| `avgo_agent.db.backup_*` count | `7` | `7` | ✅ |

`avgo_agent.db.backup_*` 文件清单（7 个，未变；与 v1 result checkpoint §12 同）：

- `avgo_agent.db.backup_pre_2099_hygiene_20260503_160409`
- `avgo_agent.db.backup_pre_3a3_20260504_013453`
- `avgo_agent.db.backup_pre_3a4_20260504_023331`
- `avgo_agent.db.backup_pre_4c3_rewrite_20260503_235604`
- `avgo_agent.db.backup_pre_replay_130_20260504_003707`
- `avgo_agent.db.backup_pre_replay_30_20260503_162636`
- `avgo_agent.db.backup_step_2c_2_6`

## 15. acceptance checklist（13 项）

| # | 标准 | 实际 | 状态 |
|---|---|---|---|
| 1 | exit 0 或受控 exit 2 + 明确 stderr | exit 0；stdout JSON v2 summary | ✅ |
| 2 | output_dir 4 文件全 exist + 非空 | 全 exist；总 ≈ 1.2 MB | ✅ |
| 3 | `records_loaded ≈ 639` | `639`（精确匹配） | ✅ |
| 4 | `records_adapted > 0` | `526` | ✅ |
| 5 | W1 / W2 / W3 / W4 均有 records | `110 / 93 / 83 / 240` | ✅ |
| 6 | `regime_validation_report.v1` schema valid | ✅ | ✅ |
| 7 | `replay_validation_records.v1` schema valid | ✅ | ✅ |
| 8 | `regime_validation_run_manifest.v1` schema valid | ✅ | ✅ |
| 9 | `final_test_touched = false`；`final_test_refusal = false` | 两者均 false | ✅ |
| 10 | DB / market_data.db / backup count 全 unchanged | 三组 fingerprint 全等 | ✅ |
| 11 | `output_dir` + 内 4 文件全部 untracked | `logs/regime_validation/` gitignore；零 tracked modified | ✅ |
| 12 | `worst_window` populated；`gate_status` 7 gate 全 present | `W1`；7 gate 全 present | ✅ |
| 13 | 没 threshold sweep / 没启 hard / 没改 required / 没接 trading / 没接 yfinance | 全部成立 | ✅ |

> 13/13 acceptance pass —— **plumbing 与数据完整性级别全部通过**；`report_status=fail` 是 candidate-level 结论，不影响 plumbing acceptance。

## 16. no-go after this result

| # | no-go |
|---|---|
| 1 | **不**进入 Step 3R-5 formula |
| 2 | **不**进入 Step 3R-6 simulator |
| 3 | **不**启 hard / forced / `anti_false_exclusion_triggered` |
| 4 | **不**让 `_PROTECTION_LAYER_CONNECTED` 翻 True |
| 5 | **不**改 04 / 05 / 07 任何 required |
| 6 | **不**改 v1 / v2 任一 `candidate_threshold`（仍锁 0.60） |
| 7 | **不**调 v2 工程默认（trigger_support 阈 / bucket 边界 / family 公式） |
| 8 | **不**调 v1 SEED coefficients |
| 9 | **不**调 6 metric / 7 gate threshold（3R-4 protocol 锁定） |
| 10 | **不**根据这一次 v2 fail 直接调任何参数 |
| 11 | **不** retry-until-pass（v2 single real run fail → 回 design，不重跑） |
| 12 | **不** sweep（execution glue v2 不实现 sweep flag） |
| 13 | **不** commit raw output（4 json 文件留在 `logs/regime_validation/<TS>/` untracked） |
| 14 | **不**触碰 2026 final-test range |
| 15 | **不**接 trading（`longbridge` / `broker` / `paper_trade`）/ yfinance / 任何网络 |
| 16 | **不**修改 wrapper / candidate v1 / candidate v2 / adapter / helper / orchestrator v1 / orchestrator v2 / glue v1 / glue v2 任一已 merge 模块 |
| 17 | **不**改任何已 merge 测试 |
| 18 | **不**重跑 W1-W3 replay |
| 19 | **不**用 v1 / v2 baseline 数据反推参数 |
| 20 | **不** auto promotion / **不**让 v2 fail 触发 retry |

## 17. recommended next step

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **commit 本 v2 result checkpoint** | 把 §1-18 真实 run 结果 + v1 baseline comparison 固化到 main | 本轮 / 下一轮 |
| 2 | **v2 failure postmortem / comparison review**（design only，独立流程） | 分析为什么 v2 更保守但 `survival_case_preservation` 仍全 0.0；为什么 v2 在 W2 / W3 / W4 false_exclusion 反而更差；不动代码、只写 design markdown | 高 |
| 3 | **核心问题审查**（design only） | （a）v2 risk_score 方向是否真的反映 P̂(prediction wrong)？为什么 high score 触发的全是 survivor？（b）"触发即排除"是否仍是合理 actuator semantic？是否需要重新定义 exclusion target（如把 trigger 从"exclude prediction"改成"hold off / wait"）？（c）trigger_support 阈值（0.5）是否过低？（d）feature family 是否过度依赖 regime 描述特征 | 高 |
| 4 | **如果 review 判 v2 仍可救** | continuous_smoothing v3 launch review（独立流程；不能从 v1/v2 fail 数据反推） | 中（review 之后） |
| 5 | **如果 review 判 candidate 方向有结构问题** | abandon continuous_smoothing 方向，回 candidate layer 重新设计（不限 smoothing） | 中（review 之后） |
| 6 | 保留 v1 + v2 fail baseline | 两次 fail 都留作未来 candidate 对照基线；新 candidate 必须 strictly 优于两者 + 独立验证 | 低 |
| 7 | **不推荐**直接 Step 3R-5 formula | 必须先过新 candidate review | ❌ |
| 8 | **不推荐** Step 3R-6 simulator | 必须先过 3R-5 review | ❌ |
| 9 | **不推荐**让 v2 fail 触发 threshold sweep / SEED 调整 / family 改公式 | 阈值 / 参数变更必须经独立 launch review；不能从 fail 反推 | ❌ |
| 10 | **不推荐**升级 04 required | Step 2G 全程边界 | ❌ |
| 11 | **不推荐**触碰 2026 final-test range | 永久封禁 | ❌ |
| 12 | **不推荐**让 `_PROTECTION_LAYER_CONNECTED` 翻 True | 与 v1 / 3R-0 / 3R-4 一致 | ❌ |
| 13 | **不推荐**重跑 W1-W3 replay | DB 已足够（audit 已锁定） | ❌ |
| 14 | **不推荐**用 v1 / v2 fail 数据反推任何具体新参数 | 阈值变更必须经 launch review | ❌ |

**关键判断**：v2 没显著优于 v1（多数 metric 持平或略差；survival_case_preservation 全 0.0 结构问题未解决）。这是 v2 的 legal fail，**不是** pipeline 故障。下一步必须**回 candidate / threshold / feature design 层**重新设计 —— 但 redesign 是独立流程，不在本步骤范围；不能从 v2 fail 数据反推具体参数；**不**直接进 3R-5 / 3R-6；**不**自动 promotion。

## 18. 严守边界

本文是**纯 checkpoint markdown**：

- ❌ 没改任何代码（`services/*` / `ui/*` / `tests/*` / `scripts/*` 全部未触碰）
- ❌ 没改 DB schema / 没写 DB
- ❌ 没运行 replay
- ❌ 没**重新运行** real validation（本次记录的是 `20260507_091823` v2 run；本 checkpoint 不再次触发 run）
- ❌ 没运行 prepare-only smoke
- ❌ 没改 `run_predict` / `predict.py` / `scanner.py` / `prediction_store.py` / `app.py`
- ❌ 没改 `services/regime_features_builder.py` / `regime_labels_builder.py` / `regime_validation_helper.py` / `continuous_smoothing_candidate.py`（v1）/ `continuous_smoothing_candidate_v2.py` / `replay_validation_record_adapter.py` / `historical_replay_training.py` / `real_regime_label_provider.py` / 任何 ui 模块 / 任何 builder
- ❌ 没改 `scripts/run_continuous_smoothing_validation.py`（v1 orchestrator）/ `run_real_continuous_smoothing_validation.py`（wrapper）/ `run_real_continuous_smoothing_validation_execute.py`（v1 glue）/ `run_continuous_smoothing_validation_v2.py`（v2 orchestrator）/ `run_real_continuous_smoothing_validation_execute_v2.py`（v2 glue）
- ❌ 没改任何已 merge 测试（v1 / v2 candidate / v2 orchestrator / v2 glue 测试）
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
- ❌ 没改 Step 3R-3.3 / 3R-3.3A / 3R-3.3B / 3R-3.3C 系列 / 3R-3.3C-D / 3R-3.3E / 3R-3.3F / 3R-3.3F-A / 3R-3.3F-C 已 merge 文档 / 实施
- ❌ 没改 Step 2G-8D / 8D.1A / 8D.2 / 8D.3 / 8D.4 文档或代码
- ❌ 没把 `output_dir` / W4 / smoke / `logs/regime_validation/` / `logs/prediction_log.jsonl` / DB backup / `agent_loop.py` / `.claude/worktrees/` 任一 commit 进 main
- ❌ 没创建任何**新的** `logs/regime_validation/*` 子目录（`continuous_smoothing_v2_real_w1_w4_20260507_091823/` 是上一轮 run 已生成的，本 checkpoint 不再生成）
- ❌ 没运行 `pytest`（本轮纯文档；测试基线维持 commit `0a753c2` 时的 **2986 / 0 failed / 10 skipped**）
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*`
- ❌ 没调 v1 / v2 任一 threshold / SEED / coefficient / 工程默认
- ❌ 没用 v1 / v2 baseline 数据反推任何参数
- ❌ 没让 v2 fail 触发 retry / sweep / grid search
- ❌ 没让 v2 fail 自动 promotion / 自动解锁 3R-5 / 3R-6
- ❌ 没 monkey-patch
- ❌ 没跑 v1 冒充 v2
- ✅ 只新增 1 份 markdown checkpoint 文档（本文件）
