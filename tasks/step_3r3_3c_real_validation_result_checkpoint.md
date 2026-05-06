# Step 3R-3.3C — Real Validation Result Checkpoint

> 本文是 **checkpoint markdown** —— 不改代码、不写 DB、不重跑 replay / validation、不 commit / push、不接 trading API、不启 hard / forced、不改 required、不触碰 2026 final-test range、不 add `logs/regime_validation/` / W4 / smoke output / `logs/prediction_log.jsonl`、不处理 DB backup / stash / `.claude/worktrees/`。

## 1. 当前完成状态

| 项 | 状态 | 来源 |
|---|---|---|
| Step 3R-3.3C-C-C execution glue design + checkpoint | ✅ 已 merge | commits `0bf9151` / `90c0b4e` |
| Step 3R-3.3C-C-C execution glue implementation + checkpoint | ✅ 已 merge | commits `7812b10` / `35c97d0` |
| **single real W1-W4 validation run** | ✅ **已完成（一次）** | execution glue exit_code=0 |
| 4 个 output 文件全部生成 | ✅ | `logs/regime_validation/continuous_smoothing_v1_real_w1_w4_20260507_065417/` |
| `avgo_agent.db` mtime / size unchanged | ✅ | DB guard 验证通过 |
| `data/market_data.db` mtime / size unchanged | ✅ | DB guard 验证通过 |
| `avgo_agent.db.backup_*` count unchanged（7 → 7） | ✅ | backup guard 验证通过 |
| `run_manifest.final_test_touched = false` | ✅ | 2026 final-test range 未触碰 |
| `report.final_test_refusal = false` | ✅ | 6 层 hard stop 全部生效 |
| **candidate `continuous_smoothing_v1` 当前版本未通过** | ❌ **report_status=fail（legal fail outcome）** | W1 false_exclusion_rate=1.0 触顶 |
| **本 checkpoint** —— 固化真实 run 结果（run metadata / records / per-window / report / gate / DB / final-test / legal-fail interpretation / no-go / 下一步） | ⏳ **本文**（未 commit） | — |

> **不**改代码、**不**调参、**不**重跑；本 checkpoint 仅为结果归档。

## 2. run metadata

| 项 | 值 |
|---|---|
| `main` 最新 commit | `35c97d0`（`docs(contract): Step 3R-3.3C-C-C execution glue implementation checkpoint`） |
| run timestamp | `20260507_065417`（`YYYYMMDD_HHMMSS`） |
| `output_dir` | `logs/regime_validation/continuous_smoothing_v1_real_w1_w4_20260507_065417/` |
| invoking script | `scripts/run_real_continuous_smoothing_validation_execute.py`（commit `7812b10`） |
| `candidate_name` | `continuous_smoothing_v1` |
| `candidate_threshold` | `0.60`（v1 seed lock；CLI 拒非 0.60） |
| `final_test_cutoff` | `"2026-01-01"`（lock；CLI 拒其它） |
| `--run-once-real-validation` | ✅ explicit opt-in |
| exit_code | **0** |
| stdout | `real_validation_execution_summary.v1` JSON |
| invocation | `PYTHONPATH=. python3 scripts/run_real_continuous_smoothing_validation_execute.py --run-once-real-validation --db-path avgo_agent.db --w4-jsonl logs/historical_training/three_system_w4_2024_08_2025_12/three_system_replay_results.jsonl --w4-manifest logs/historical_training/three_system_w4_2024_08_2025_12/validation_ready_manifest.json --avgo-csv data/AVGO.csv --nvda-csv data/NVDA.csv --soxx-csv data/SOXX.csv --qqq-csv data/QQQ.csv --candidate-threshold 0.60 --final-test-cutoff 2026-01-01 --output-dir <output_dir>` |

## 3. output files

| 文件 | 大小 | schema |
|---|---|---|
| `replay_validation_records.json` | 782,858 bytes | `replay_validation_records.v1` |
| `regime_validation_report.json` | 3,315 bytes | `regime_validation_report.v1` |
| `regime_validation_summary.md` | 630 bytes | human-readable |
| `run_manifest.json` | 8,608 bytes | `regime_validation_run_manifest.v1` |

处置规则：

- ✅ `output_dir` 保持 **untracked**（`logs/regime_validation/` 已 gitignore）。
- ❌ raw json **不**进 main；本 checkpoint 只复制关键 summary 字段。
- ✅ `regime_validation_summary.md` 内容已抽取进本 checkpoint §4 / §7 / §9。
- ❌ 不 commit `output_dir` 任何子文件；不 `git add`；不修改。
- ✅ 可删除 / 可重跑（新 timestamp = 新目录）；本次 run 留作 v1 fail baseline。

## 4. run_manifest summary

| 字段 | 值 |
|---|---|
| `schema_version` | `regime_validation_run_manifest.v1` |
| `candidate_name` | `continuous_smoothing_v1` |
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

- 113 条 `record_skipped:missing_or_invalid_direction_correct:<date>`，全部来自 W4 jsonl 中**尚无 paired outcome 的近端 row**（recent dates 中 outcome 还未填）。
- 1 条 `w4_manifest_not_required` 来自 helper 阶段（adapter 已经 enforce W4 manifest，helper 这一段 require=False，标识告知；非错误）。
- 这 113 条不是系统错误；是 W4 jsonl 输入缺 outcome 的预期 behavior，warning 字符串可解释，不影响 schema validity。

## 5. records_loaded / records_adapted

| 项 | 值 | 来源 |
|---|---|---|
| `records_loaded` | **639** | wrapper 装配的 input bundle（与 Step 3R-3.3C-B1 prepare-only smoke total 一致） |
| ↳ W1-W3 DB rows | 286 | `scripts/run_real_continuous_smoothing_validation.py` `load_w1_w3_rows_from_db(...)` |
| ↳ W4 jsonl rows | 353 | `load_w4_rows_from_jsonl(...)`（filtered for cutoff） |
| `records_adapted` | **526** | adapter `build_replay_validation_records(...)` 输出 records 计数 |
| ↳ 差额 113 = 全部 skipped | 113 × `record_skipped:missing_or_invalid_direction_correct:<date>` | adapter G2-like outcome enforce |
| `records_adapted > 0` | ✅ | acceptance §11 第 4 条 |
| W1 / W2 / W3 / W4 全部有 records | ✅ | acceptance §11 第 5 条 |

## 6. per-window distribution

| window | total records | `candidate_triggered=True` | `candidate_triggered=False` |
|---|---|---|---|
| W1 | 110 | 2 | 108 |
| W2 | 93 | 23 | 70 |
| W3 | 83 | 4 | 79 |
| W4 | 240 | 107 | 133 |
| **Total** | **526** | **136** | **390** |

观察：

- W1 触发样本极少（2 条），落在 helper `GATE_MIN_WINDOW_SAMPLE = 20` 之下 → `minimum_window_sample_size` gate 直接 fail。
- W3 触发样本同样少（4 条），同理 fail。
- W2 / W4 触发样本相对充裕（23 / 107），但 W1 已经触顶 false_exclusion_rate=1.0 决定了 worst_window。
- 所有 4 fold 都被 candidate 处理过，没有 fold 缺失或被跳过；fold 缺失类 no-go（design §13 第 16 条）未触发。

## 7. report summary

| 字段 | 值 |
|---|---|
| `schema_version` | `regime_validation_report.v1` |
| `candidate_name` | `continuous_smoothing_v1` |
| `candidate_kind` | `smoothing` |
| `overall_status` | **`fail`** |
| `report_status`（manifest 透传） | `fail` |
| `worst_window` | **`W1`** |
| `final_test_refusal` | **`false`** |
| `gate_status` | 7 gate 全部 present |

`regime_validation_summary.md` 原文（已抽取，本 checkpoint 完整复述以便归档）：

```
# Continuous Smoothing Validation Run Summary

- candidate_name: continuous_smoothing_v1
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

_This run is a read-only diagnostic; pass does not grant production permission._
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

7/7 fail。这是 helper 在 worst_window=W1 上的连锁结果：W1 触发样本仅 2 条已不满足 `minimum_window_sample_size`，且 W1 false_exclusion_rate=1.0 直接触顶；其余 5 gate 在 W1 上同样不达阈，accumulated 成 7 全 fail。

## 9. primary failure reason

`fail_reason` 原文：

```
minimum_window_sample_size,false_exclusion_rate,net_benefit,accuracy_delta_vs_baseline,cross_window_variance,survival_case_preservation,no_single_window_collapse at W1: false_exclusion_rate=1.0000_above_0.1
```

解读：

| 观察 | 解释 |
|---|---|
| W1 是 `worst_window` | helper 选 worst-window-by-status；W1 已经 false_exclusion_rate=1.0，没有比它更糟的 fold |
| W1 总 records = 110 | 与 wrapper 装配的 W1-W3 DB rows 一致 |
| W1 `candidate_triggered=True` 只有 2 条 | candidate v1 在 W1 regime 上几乎不触发；2 条不足 helper `GATE_MIN_WINDOW_SAMPLE = 20` |
| W1 `false_exclusion_rate = 1.0` | W1 中所有 candidate-triggered 的 case 都是 survivor → candidate 的 exclusion 全错（误排率 100%）；touch helper `GATE_FALSE_EXCLUSION = 0.10` 的 10× |
| 引出连锁 fail | `net_benefit` / `accuracy_delta_vs_baseline` / `cross_window_variance` / `survival_case_preservation` / `no_single_window_collapse` 都在 W1 上不达阈 → accumulated 7 gate 全 fail |
| 结论 | **current SEED coefficients + threshold = 0.60 在 W1 真实 regime 上不 eligible**；不是 pipeline bug，不是 wrapper / provider / orchestrator / candidate / adapter / helper 任一层 bug |

## 10. legal fail interpretation

per design §11 / impl checkpoint §11，本次结果 **是 legal fail outcome**：

| 判定 | 状态 |
|---|---|
| pipeline error？ | ❌ 否 —— exit 0 / 4 文件齐 / schema valid / DB unchanged |
| schema bug？ | ❌ 否 —— `regime_validation_report.v1` / `replay_validation_records.v1` / `regime_validation_run_manifest.v1` 三套 schema 字段齐 |
| IO 错误？ | ❌ 否 —— 4 文件成功落地，大小正常 |
| DB guard 失败？ | ❌ 否 —— 三组 fingerprint 全 unchanged |
| final-test guard 失败？ | ❌ 否 —— `final_test_touched=false` / `final_test_refusal=false` / 6 层 hard stop 全部生效 |
| forbidden import？ | ❌ 否 —— execution glue isolation tests 已锁 21 项 import + 11 项字符串 |
| **fail 含义** | candidate `continuous_smoothing_v1` 在 v1 seed 0.60 + 真实 W1-W4 数据上**不 eligible** |

按 design / impl checkpoint 的明确规则：

- ❌ **不**根据本次结果直接调 `candidate_threshold`（v1 seed 0.60 锁定；阈值变更必须经独立 launch review）
- ❌ **不**调 SEED coefficients（continuous_smoothing v1 模块常量）
- ❌ **不**调 6 metric / 7 gate threshold（3R-4 protocol 锁定）
- ❌ **不**自动 retry
- ❌ **不**自动 sweep（执行 glue 不实现 sweep flag）
- ❌ **不**把 fail 当作系统故障 / 不重写代码 / 不修复任何 service
- ❌ **不**自动启 hard / Gate 5 / Gate 6 / `_PROTECTION_LAYER_CONNECTED`
- ❌ **不**自动进入 3R-5 formula / 3R-6 simulator
- ✅ 把这次 fail **作为 v1 baseline** 留存，等待 candidate / threshold v2 设计

## 11. final-test guard verification

| 检查 | 状态 |
|---|---|
| `run_manifest.final_test_touched = false` | ✅ |
| `report.final_test_refusal = false` | ✅ |
| `final_test_cutoff = "2026-01-01"` | ✅ |
| 6 层 hard stop（wrapper DB filter / wrapper W4 jsonl filter / orchestrator row filter / provider refusal / candidate refusal / adapter+helper+report refusal） | ✅ 全部生效 |
| 任一 row `as_of_date >= cutoff` 被消费 | ❌ 没有 |
| 任一 row `prediction_for_date >= cutoff` 被消费 | ❌ 没有 |
| 2026-01-01 之后 final-test range 是否被读取 | ❌ 没有 |

## 12. DB / market_data / backup verification

| object | before | after | unchanged |
|---|---|---|---|
| `avgo_agent.db` mtime_ns | `1777833249.653954308` | `1777833249.653954308` | ✅ |
| `avgo_agent.db` size_bytes | `11,206,656` | `11,206,656` | ✅ |
| `data/market_data.db` mtime_ns | `1777392167.547992024` | `1777392167.547992024` | ✅ |
| `data/market_data.db` size_bytes | `13,127,680` | `13,127,680` | ✅ |
| `avgo_agent.db.backup_*` count | `7` | `7` | ✅ |

`avgo_agent.db.backup_*` 文件清单（7 个，未变）：

- `avgo_agent.db.backup_pre_2099_hygiene_20260503_160409`
- `avgo_agent.db.backup_pre_3a3_20260504_013453`
- `avgo_agent.db.backup_pre_3a4_20260504_023331`
- `avgo_agent.db.backup_pre_4c3_rewrite_20260503_235604`
- `avgo_agent.db.backup_pre_replay_130_20260504_003707`
- `avgo_agent.db.backup_pre_replay_30_20260503_162636`
- `avgo_agent.db.backup_step_2c_2_6`

## 13. acceptance checklist（13 项）

| # | 标准 | 实际 | 状态 |
|---|---|---|---|
| 1 | 脚本以 exit 0 或受控 exit 2 + 明确 stderr 结束 | exit 0；stdout JSON summary | ✅ |
| 2 | output_dir 4 文件全 exist + 非空 | 全 exist；总 ≈ 794 KB | ✅ |
| 3 | `records_loaded ≈ 639`（与 B1 smoke total 一致） | `639`（精确匹配） | ✅ |
| 4 | `records_adapted > 0` | `526` | ✅ |
| 5 | W1 / W2 / W3 / W4 均有 records | `110 / 93 / 83 / 240` | ✅ |
| 6 | `regime_validation_report.v1` schema valid（14 字段齐） | ✅ | ✅ |
| 7 | `replay_validation_records.v1` schema valid（8 字段齐） | ✅ | ✅ |
| 8 | `regime_validation_run_manifest.v1` schema valid（12 字段齐） | ✅ | ✅ |
| 9 | `run_manifest.final_test_touched = false`；`report.final_test_refusal = false` | 两者均 `false` | ✅ |
| 10 | DB / market_data.db / backup count 全 unchanged | 三组 fingerprint 全等 | ✅ |
| 11 | `output_dir` 与其内 4 文件全部 untracked | `logs/regime_validation/` 已 gitignore；零 tracked modified | ✅ |
| 12 | `worst_window` populated；`gate_status` 7 gate 全 present | `W1`；7 gate 全 present | ✅ |
| 13 | 没 threshold sweep / 没启 hard / 没改 required / 没接 trading / 没接 yfinance | 全部成立（CLI lock + isolation tests + 静态扫描已锁定） | ✅ |

> 13/13 acceptance pass —— **plumbing 与数据完整性级别全部通过**；`report_status=fail` 是 candidate-level 结论，不影响 plumbing acceptance。

## 14. no-go after this result

任意一项触发 → 后续步骤 abort，回到 candidate / threshold design 重新设计：

| # | no-go |
|---|---|
| 1 | **不**进入 Step 3R-5 formula |
| 2 | **不**进入 Step 3R-6 simulator |
| 3 | **不**启 hard / forced / `anti_false_exclusion_triggered` |
| 4 | **不**让 `_PROTECTION_LAYER_CONNECTED` 翻 True |
| 5 | **不**改 04 / 05 / 07 任何 required |
| 6 | **不**改 `candidate_threshold`（0.60 锁定；阈值变更必须经独立 launch review） |
| 7 | **不**调 SEED coefficients（continuous_smoothing v1 模块常量） |
| 8 | **不**调 6 metric / 7 gate threshold（3R-4 protocol 锁定） |
| 9 | **不**根据这一次 fail 直接调任何参数 |
| 10 | **不**重跑直到得到 pass（不允许 retry-until-pass 反模式） |
| 11 | **不** sweep（execution glue 不实现 sweep flag；任何 sweep 必须经独立 launch review） |
| 12 | **不** commit raw output（4 json 文件留在 `logs/regime_validation/<TS>/` untracked） |
| 13 | **不**触碰 2026 final-test range |
| 14 | **不**接 trading（`longbridge` / `broker` / `paper_trade` 永久封禁） |
| 15 | **不**接 yfinance / requests / 任何网络 |
| 16 | **不**修改 wrapper / provider / orchestrator / candidate / adapter / helper / execution glue 任一已 merge 模块 |
| 17 | **不**重跑 W1-W3 replay |
| 18 | **不**用 first real run 数据反推 candidate_threshold |

## 15. recommended next step

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **commit 本 result checkpoint** | 把 §1-16 真实 run 结果固化到 main（独立 commit；message 形如 `docs(contract): Step 3R-3.3C real validation result checkpoint`） | 本轮 / 下一轮 |
| 2 | **candidate / threshold postmortem（design 阶段）** | 分析 W1 false_exclusion_rate=1.0 的 root cause：为什么 v1 SEED 在 W1 regime（2023-01 ~ 2023-08）上几乎不触发但触发的全错；不动代码、只写 design | 高 |
| 3 | **continuous_smoothing v2 设计**（独立 launch review） | v2 SEED + threshold policy + （可能）windowed-tuning 设计；必须经 launch review；不能从 v1 fail 数据反推 | 中（postmortem 之后） |
| 4 | **保留 v1 fail baseline** | 本次 `output_dir` 留在本地 untracked；可作为 v2 对照基线（v2 必须 strictly 优于 v1，且必须独立验证） | 低 |
| 5 | **不推荐**直接 Step 3R-5 formula | fail 阻止 promotion；必须先过 candidate v2 design + 独立 real run | ❌ |
| 6 | **不推荐** Step 3R-6 simulator | 必须先过 3R-5 design | ❌ |
| 7 | **不推荐**让 first real run fail 触发 threshold sweep | 阈值变更必须经独立 launch review | ❌ |
| 8 | **不推荐**让 first real run fail 触发 SEED 调整 | SEED coefficients 是 candidate v1 的固有定义；变更 = 新 candidate（v2） | ❌ |
| 9 | **不推荐**升级 04 required | Step 2G 全程边界 | ❌ |
| 10 | **不推荐**触碰 2026 final-test range | 永久封禁 | ❌ |
| 11 | **不推荐**让 `_PROTECTION_LAYER_CONNECTED` 翻 True | 与 v1 / 3R-0 / 3R-4 一致 | ❌ |
| 12 | **不推荐**重跑 W1-W3 replay | DB 已足够（audit 已锁定） | ❌ |
| 13 | **不推荐**用 first real run 数据反推 candidate_threshold | 阈值变更必须经 launch review | ❌ |

**关键判断**：顺序 = 本 result checkpoint → candidate / threshold postmortem（design only）→ continuous_smoothing v2 launch review → v2 design + checkpoint → v2 implementation + tests → v2 single real run → v2 result checkpoint → 3R-5 formula launch review → 3R-6 simulator。任何一步 fail → 回到 design 层重新设计，**不**自动进入下一步。

## 16. 严守边界

本文是**纯 checkpoint markdown**：

- ❌ 没改任何代码（`services/*` / `ui/*` / `tests/*` / `scripts/*` 全部未触碰）
- ❌ 没改 DB schema
- ❌ 没写 DB
- ❌ 没运行 replay
- ❌ 没**重新运行** real validation（本次记录的是 `20260507_065417` run；本 checkpoint 不再次触发 run）
- ❌ 没运行 prepare-only smoke
- ❌ 没改 `run_predict` / `predict.py` / `scanner.py` / `prediction_store.py` / `app.py`
- ❌ 没改 `services/regime_features_builder.py` / `services/regime_labels_builder.py` / `services/regime_validation_helper.py` / `services/continuous_smoothing_candidate.py` / `services/replay_validation_record_adapter.py` / `services/historical_replay_training.py` / `services/real_regime_label_provider.py` / 任何 ui 模块 / 任何 builder
- ❌ 没改 `scripts/run_continuous_smoothing_validation.py` / `scripts/run_real_continuous_smoothing_validation.py` / `scripts/run_real_continuous_smoothing_validation_execute.py`
- ❌ 没改 `tests/test_run_continuous_smoothing_validation.py` / `tests/test_run_real_continuous_smoothing_validation.py` / `tests/test_real_regime_label_provider.py` / `tests/test_run_real_continuous_smoothing_validation_execute.py`
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
- ❌ 没改 Step 3R-3.3 / 3R-3.3A / 3R-3.3B / 3R-3.3C / 3R-3.3C-A / 3R-3.3C-B / 3R-3.3C-B1 / 3R-3.3C-C / 3R-3.3C-C-A / 3R-3.3C-C-B / 3R-3.3C-C-C design / checkpoint / implementation 已 merge 文档 / 实施
- ❌ 没改 Step 2G-8D / 8D.1A / 8D.2 / 8D.3 / 8D.4 文档或代码
- ❌ 没把 `output_dir` / W4 / smoke / `logs/regime_validation/` / `logs/prediction_log.jsonl` / DB backup / `agent_loop.py` / `.claude/worktrees/` 任一 commit 进 main
- ❌ 没创建任何**新的** `logs/regime_validation/*` 子目录（`continuous_smoothing_v1_real_w1_w4_20260507_065417/` 是上一轮 run 已生成的，本 checkpoint 不再生成）
- ❌ 没运行 `pytest`（本轮纯文档；测试基线维持 commit `7812b10` 时的 **2905 / 0 failed / 10 skipped**）
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*`
- ✅ 只新增 1 份 markdown checkpoint 文档（本文件）
