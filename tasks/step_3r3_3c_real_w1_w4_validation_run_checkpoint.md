# Step 3R-3.3C — Real W1-W4 Validation Run Checkpoint

## 1. 当前完成状态
- Step 3R-3.3 4-fold validation run design 已完成并进入 main（commit `8a24295`）。
- Step 3R-3.3 4-fold validation run checkpoint 已完成并进入 main（commit `2535467`）。
- Step 3R-3.3A dry-run validation orchestrator 已完成并进入 main（commit `32f196a`）；checkpoint `9fbd9b5`。
- Step 3R-3.3B limited-record smoke 已通过并 checkpoint 进入 main（commit `d299247`）。
- Step 3R-3.3C real W1-W4 validation run **design** 已完成并进入 main（commit `226e354`）。
- 本 checkpoint 用于固定 real run 的：
  - 前置条件（含 W1/W2/W3 source audit gate）
  - candidate_threshold v1 seed = 0.60（不扫 / 不学 / 不反推）
  - output 目录 + 4 文件
  - DB guard
  - 6 层 final test guard
  - acceptance + no-go rules
  - 与 hard / required / 2026 / 3R-5 / 3R-6 的边界
- **real W1-W4 validation 仍未执行。**
- W1 / W2 / W3 source audit（Step 3R-3.3C-A）仍未执行。
- real run wrapper / execution（Step 3R-3.3C-B / 3R-3.3C-C）仍未启动。

## 2. 当前 main 状态
- main 最新 commit：`226e354`
- commit message：`docs(contract): Step 3R-3.3C real W1-W4 validation run design`
- 上游：`origin/main` 已同步。
- 本步骤新增文件（已 merge 到 main）：
  - `tasks/step_3r3_3c_real_w1_w4_validation_run_design.md`（16 节、303 行；real run source / output / cutoff / DB guard / acceptance / no-go / 实施顺序）
- 本 checkpoint 文档（即本文件）尚未 commit；本轮只写文档、**不** commit / push。

| 项 | 是否触碰 |
|---|---|
| 改代码 | ❌ 否 |
| 写 DB | ❌ 否 |
| 跑 replay | ❌ 否 |
| 跑 validation | ❌ 否 |
| 改 services/* / scripts/* / tests/* | ❌ 否 |
| 改 DB schema | ❌ 否 |
| 接 yfinance / 网络 | ❌ 否 |
| 接 trading API | ❌ 否 |
| 触碰 2026 final test | ❌ 否 |

## 3. real run 目标
- 使用真实 W1 / W2 / W3 / W4 replay rows 跑一次 4-fold validation。
- 通过现有 `run_continuous_smoothing_validation(...)` 公共 API（已在 3R-3.3A 落地、3R-3.3B smoke 验证）。
- 生成：
  - `replay_validation_records.v1`（adapter 输出）
  - `regime_validation_report.v1`（helper 输出）
  - `regime_validation_run_manifest.v1`（orchestrator 输出）
  - 人读 summary markdown
- 输出本地 4 文件 report 到独立 timestamp 目录。
- **不**写 DB。
- **不**进 main（output 全部 untracked）。
- **不**证明 candidate 可进 production；**不**自动启 hard / 改 required。
- **不**触碰 2026 final test range。

## 4. W1 / W2 / W3 source audit gate（real run 前置条件）

### 4.1 audit 必须证明的字段对齐
real run 前必须先做 **read-only** source audit（Step 3R-3.3C-A），逐 window 确认：
- 每条 row 有 `as_of_date`（str）
- 每条 row 有 `prediction_for_date`（str）
- 每条 row 有 `direction_correct`（或可推导出的等价 paired 字段）
- 每条 row 有 `ready=true` 或等价 paired 状态
- 每条 row 严格 **< `"2026-01-01"`**
- 每个 fold（W1 / W2 / W3）paired 样本量满足 helper `minimum_window_sample_size` gate（与 3R-4.2 helper 锁定阈值一致；W4 由 manifest 已保证）
- W1 / W2 / W3 row schema 与 W4 jsonl row schema 对齐（核心字段：`as_of_date` / `prediction_for_date` / `final_direction` / `direction_correct` / `ready`）
- **无 lookahead**：`prediction_for_date > as_of_date` 必须恒成立；不允许使用 future-leaking 字段（`pos20` / `five_state_projection`）反喂 candidate

### 4.2 候选 source（仅作 audit 入口，不修改任何文件）
| # | 候选 | 路径 / 来源 | 已知信息 |
|---|---|---|---|
| 1 | `three_system_1005` 复用 | `logs/historical_training/three_system_1005/three_system_replay_results.jsonl` | schema 与 W4 同；summary 显示 `total_cases=5`，**单独不够**覆盖 W1+W2+W3 |
| 2 | DB replay-tagged predictions | `avgo_agent.db` `prediction_log` + `outcome_log` join，过滤 replay-source rows | **只读**；不写 DB；字段对齐需要 audit |
| 3 | `03_fresh_replay` | `logs/historical_training/03_fresh_replay/` | schema / 日期范围未确认 |
| 4 | `exclusion_action_validation_2e` / `..._v2` | `logs/historical_training/exclusion_action_validation_2e*/` | 与 exclusion validation 关联；是否 paired outcome 待 audit |
| 5 | 重跑 W1 / W2 / W3 replay | 类似 8D.3 W4 流程 | **不在本 checkpoint 范围**；audit 失败时另行 launch review |

### 4.3 audit 行为约束（强约束）
- 仅 read-only 字段抽样 + 日期范围统计 + paired count 统计。
- **不**写 DB。
- **不**改代码。
- **不**新增 / 修改 jsonl。
- **不**触碰 2026 行（一旦发现 `as_of_date >= "2026-01-01"` 立即 stop 并报告）。
- 输出 **markdown audit checkpoint**：`tasks/step_3r3_3c_a_w1_w2_w3_source_audit_checkpoint.md`。
- audit 不通过 → real run 永久 abort，回到设计层重新选 source。

## 5. threshold policy
| 项 | 值 |
|---|---|
| `candidate_threshold` | `0.60`（v1 design seed） |
| 是否 optimized | ❌ 否 |
| 是否允许扫 threshold | ❌ 否 |
| 是否允许学 threshold | ❌ 否 |
| 是否允许用 validation 结果反推 threshold | ❌ 否 |
| first run fail 时是否调参 | ❌ 否 |
| 6 metric / 7 gate threshold | ❌ 不动（3R-4 protocol 锁定） |
| SEED coefficients（3R-3.1 模块常量） | ❌ 不动 |
| 任何 sweep 触发方式 | 单独 launch review；不在 3R-3.3C 范围 |

caller 必须**显式**传入 `candidate_threshold`；不允许 silent default override。

## 6. output_dir
```
logs/regime_validation/continuous_smoothing_v1_real_w1_w4_YYYYMMDD_HHMMSS/
```
`YYYYMMDD_HHMMSS` 由 wrapper 启动时生成。

### 6.1 输出 4 文件
- `replay_validation_records.json`
- `regime_validation_report.json`
- `regime_validation_summary.md`
- `run_manifest.json`

### 6.2 处置规则
| 项 | 状态 |
|---|---|
| `output_dir` 必须不存在（已存在 → orchestrator 抛 `FileExistsError`） | ✅ |
| **不**进 main；本地 untracked | ✅ |
| **不**覆盖旧输出 | ✅ |
| **不**写 DB | ✅ |
| **不**覆盖 W4 outputs（W4 是不可变 baseline） | ✅ |
| **不**写入 `logs/prediction_log.jsonl` | ✅ |
| **不** `git add` `logs/regime_validation/` 任何子目录 | ✅ |
| 可删除 / 可重跑（新 timestamp = 新目录） | ✅ |

## 7. DB guard
run **前** / **后** 记录：
- `avgo_agent.db` mtime + size
- `data/market_data.db` mtime + size（若存在）
- `avgo_agent.db.backup_*` 文件计数

任一变化：
- run invalid
- report 不可信
- 必须停止后续步骤
- 不允许把结果作为后续设计依据

禁止 import / 使用：
- `services.prediction_store`
- `sqlite3` 写入路径（read-only join 在 audit 中允许）
- `services.outcome_capture` 写入路径
- `yfinance` / `requests` / 任何网络
- `predict` / `scanner` / `streamlit`
- `longbridge` / `broker` / `paper_trade`

DB guard 由 wrapper（Step 3R-3.3C-B）实现；orchestrator 本身不读 DB。

## 8. final test guard（6 层 hard stop）
- `final_test_cutoff = "2026-01-01"`（硬编码，不可变）

| # | 层 | 条件 |
|---|---|---|
| 1 | wrapper / orchestrator row filter | row `as_of_date >= "2026-01-01"` 或 `prediction_for_date >= "2026-01-01"` → skip / abort |
| 2 | W4 manifest gate（adapter） | `final_test_touched=true` → run abort |
| 3 | W4 manifest gate（helper） | 同 8 项检查双重校验 |
| 4 | `regime_labels.v1.final_test_refusal=true` propagate | 3R-2 builder |
| 5 | `continuous_smoothing_candidate.v1.final_test_refusal=true` propagate | 3R-3.1 candidate |
| 6 | `regime_validation_report.v1.final_test_refusal=true` | 3R-4.2 helper |

补充：
- run_manifest `final_test_touched` must be `false`。
- run_manifest `final_test_cutoff` must be `"2026-01-01"`。
- report `final_test_refusal` must be `false`。
- 任一为 true → run `report_status="error"` + result invalid，**不**允许进入下一步。

## 9. acceptance criteria
**first real run 不要求 pass。** `report_status` 可以 `pass` / `fail` / `error`，但必须**有可解释的原因**。

acceptance 是 plumbing 级别 + 数据完整性级别（11 项）：

| # | 标准 |
|---|---|
| 1 | pipeline completes（exit code 0；无未捕获异常） |
| 2 | report schema valid（`regime_validation_report.v1` 字段齐） |
| 3 | records schema valid（`replay_validation_records.v1` 字段齐） |
| 4 | run_manifest schema valid（`regime_validation_run_manifest.v1` 字段齐） |
| 5 | `records_loaded > 0` |
| 6 | `records_adapted > 0` |
| 7 | W1 / W2 / W3 / W4 **均**有 records（per-window 计数 > 0） |
| 8 | `final_test_touched = false` |
| 9 | DB **未变**（mtime / size / backup count 全等） |
| 10 | output_dir untracked（git status 无 tracked modified） |
| 11 | 没有 threshold sweep / 没有 hard / 没有 required 改动 |

### 9.1 first run 可能 fail 的合法理由
- 某 window FER > 0.10
- 某 fold cross_window_variance > 0.10
- 某 fold paired < `minimum_window_sample_size`
- 某 window survival_preservation < 0.80
- net_benefit < +0.05
- accuracy_delta_vs_baseline 不达标

→ fail **不**等于 caller / orchestrator bug；fail **不**触发调参；fail 走回 candidate / threshold design review。

## 10. no-go rules（11 项）
任一项触发 → run abort + `report_status="error"`：

| # | 条件 |
|---|---|
| 1 | W1 / W2 / W3 source unknown / 未通过 §4 audit |
| 2 | W4 manifest missing / parse 失败 / `final_test_touched=true` |
| 3 | DB modified（mtime / size / backup count 任一变化） |
| 4 | 2026 touched（任一 row `as_of_date / prediction_for_date >= "2026-01-01"`） |
| 5 | threshold swept（含运行时 silent override） |
| 6 | SEED coefficients changed |
| 7 | `records_adapted = 0`（adapter 输出空） |
| 8 | 任一 fold（W1 / W2 / W3 / W4）records 计数为 0 |
| 9 | `output_dir` 已存在 |
| 10 | report schema missing 必备字段 |
| 11 | hard / forced / required 任一被改 |

## 11. 与 3R-5 / 3R-6 的关系
- 即使 real report `overall_status="pass"` → **不**自动进入 3R-5 formula。
- pass 唯一允许的下游：进入 **design review** 讨论 3R-5 formula scope。
- fail **不**触发调参；fail 唯一允许的下游：回 candidate / threshold design 重新设计。
- 3R-5 / 3R-6 仍需**单独** launch review；3R-3.3C 不构成 implicit 授权。
- 不允许把 first real report 摘要直接当作 production gate。
- 不允许 report `pass` 自动启 hard / Gate 5 / Gate 6 / `_PROTECTION_LAYER_CONNECTED`。

## 12. 允许下一步
| # | 候选 | 状态 |
|---|---|---|
| 1 | **Step 3R-3.3C-A W1/W2/W3 source audit** | ✅ 允许（在本 checkpoint 进入 main 后启动）；纯 read-only |
| 2 | audit 必须输出 markdown checkpoint（`tasks/step_3r3_3c_a_w1_w2_w3_source_audit_checkpoint.md`） | ✅ |
| 3 | audit 通过前**不允许** real run wrapper 实施 | ✅ |
| 4 | audit 通过前**不允许** real run execution | ✅ |
| 5 | audit 不允许写 DB / 改代码 / 改 jsonl / 触碰 2026 | ✅ |
| 6 | candidate / adapter / helper / orchestrator / labels builder 现有行为 | ❌ 不改（仅只读调用） |
| 7 | hard / required upgrade / Gate 5 / Gate 6 / `_PROTECTION_LAYER_CONNECTED` | ❌ 永久封禁 |

## 13. 禁止事项
| # | 禁止 | 理由 |
|---|---|---|
| 1 | **不**跑 real validation before §4 source audit | 防止口径错配 / lookahead |
| 2 | **不**扫 threshold | 与 §5 一致 |
| 3 | **不**调 SEED coefficients | 模块常量；变更必须 launch review |
| 4 | **不**调 6 metric / 7 gate threshold | 3R-4 protocol 锁定 |
| 5 | **不**写 DB | 全程 read-only |
| 6 | **不**覆盖 W4 outputs | W4 是不可变 baseline |
| 7 | **不**启 hard / forced / `anti_false_exclusion_triggered` | 三重 NO-GO |
| 8 | **不**改 04 / 05 / 07 required | Step 2G 全程边界 |
| 9 | **不**触碰 2026 final test range | 6 层 hard stop |
| 10 | **不**接 trading（`longbridge` / `broker` / `paper_trade`） | 永久封禁 |
| 11 | **不**让 `_PROTECTION_LAYER_CONNECTED` 翻 True | 与 v1 / 3R-0 / 3R-4 一致 |
| 12 | **不**让 `hard_gate_status.protection_layer_connected` 自动 pass | 同上 |
| 13 | **不**改 `hard_exclusion_allowed` / `primary_blocker` 派生 | 同上 |
| 14 | **不** commit validation outputs | 与 3R-3.3 §6.2 一致 |
| 15 | **不**直接进入 formula（3R-5）/ simulator（3R-6） | 必须先过 result checkpoint |
| 16 | **不** import `services.prediction_store` / `sqlite3` 写路径 / `yfinance` / `requests` / `predict` / `scanner` / `streamlit` 在 wrapper 任一层 | DB / 网络 / production isolation |
| 17 | **不**调 `regime_label_provider` 把 future-leaking 字段（`pos20` / `five_state_projection` 等）喂入 candidate | anti-lookahead |
| 18 | **不**在 first real run fail 时调任何参数 | 与 §9.1 / §11 一致 |
| 19 | **不**触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*` | 历史防护 |
| 20 | **不**把 `logs/regime_validation/` 任何子目录 `git add` | 与 §6.2 一致 |

## 14. 下一步建议

按推荐优先级：

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **commit 本 checkpoint** | 把 §1-15 real run 边界 + audit gate 固化到 main | 本轮 / 下一轮 |
| 2 | **Step 3R-3.3C-A W1/W2/W3 source audit** | 纯 read-only audit；产物 `tasks/step_3r3_3c_a_w1_w2_w3_source_audit_checkpoint.md` | 高（本 checkpoint 进 main 后） |
| 3 | **Step 3R-3.3C-A audit checkpoint** | 状态归档（合并 audit 结果与决策） | 紧接其后 |
| 4 | **Step 3R-3.3C-B real run wrapper script** | wrapper 实现 + `regime_label_provider` 实现 + DB guard + focused tests；仍**不**跑 real run | 中（audit 通过后） |
| 5 | **Step 3R-3.3C-C real run execution** | 单次跑真实 W1-W4；output 本地 untracked | 中（wrapper 进 main 后） |
| 6 | **Step 3R-3.3C result checkpoint** | 摘要 / report_status / per-window / fail_reason 归档 | 中（execution 完成后） |
| 7 | **不推荐**直接 Step 3R-5 formula design | 必须先过 3R-3.3C 实测 acceptance | ❌ |
| 8 | **不推荐** Step 3R-6 read-only simulator | 必须先过 3R-5 design | ❌ |
| 9 | **不推荐**让 report `pass` 自动启 hard / Gate 5 / Gate 6 | 与 §11 一致 | ❌ |
| 10 | **不推荐**升级 04 required | Step 2G 全程边界 | ❌ |
| 11 | **不推荐**触碰 2026 final test range | 永久封禁 | ❌ |
| 12 | **不推荐**让 `_PROTECTION_LAYER_CONNECTED` 翻 True | 与 v1 / 3R-0 / 3R-4 一致 | ❌ |
| 13 | **不推荐**用 real run 数据反推 candidate_threshold | 阈值变更必须经 launch review | ❌ |

**关键判断**：顺序 = 本 checkpoint → **3R-3.3C-A audit**（首个 read-only 数据探查步）→ audit checkpoint → 3R-3.3C-B wrapper 实施 → 3R-3.3C-C execution → 3R-3.3C result checkpoint → 3R-5 formula → 3R-6 simulator。任何一步 fail → 整 candidate 报废，回到 design 层重新设计。

## 15. 严守边界
本文是**纯 checkpoint markdown**：

- ❌ 没改任何代码（`services/*` / `ui/*` / `tests/*` / `scripts/*` 全部未触碰）
- ❌ 没改 DB schema
- ❌ 没写 DB
- ❌ 没运行 replay
- ❌ 没运行 validation
- ❌ 没改 `run_predict` / `predict.py` / `scanner.py` / `prediction_store.py` / `app.py`
- ❌ 没改 `services/regime_features_builder.py` / `services/regime_labels_builder.py` / `services/regime_validation_helper.py` / `services/continuous_smoothing_candidate.py` / `services/replay_validation_record_adapter.py` / `services/historical_replay_training.py` / 任何 ui 模块 / 任何 builder
- ❌ 没改 `scripts/run_continuous_smoothing_validation.py` 或任何 replay / validation 脚本
- ❌ 没改 04 / 05 / 07 任何 required 字段
- ❌ 没启用 `hard` / `forced_exclusion` / `anti_false_exclusion_triggered`
- ❌ 没接 `yfinance` / `requests` / 任何网络
- ❌ 没接 trading API / `longbridge` / `broker` / `paper_trade`
- ❌ 没让 `_PROTECTION_LAYER_CONNECTED` 翻 True
- ❌ 没让 `hard_gate_status.protection_layer_connected` 自动 pass
- ❌ 没改 `hard_exclusion_allowed` / `primary_blocker` 派生
- ❌ 没触碰 2026-01-01 之后 final test range
- ❌ 没改 Step 3R-4 protocol thresholds（6 metric / 7 gate / 10 no-go）
- ❌ 没改 Step 3R-2 helper / 3R-3.1 candidate / 3R-4.2 helper / 3R-4.3A adapter 行为
- ❌ 没改 Step 3R-3.3 / 3R-3.3A / 3R-3.3B / 3R-3.3C 已 merge 的 design / checkpoint / 实施
- ❌ 没改 Step 2G-8D / 8D.1A / 8D.2 / 8D.3 / 8D.4 文档或代码
- ❌ 没把 W4 / smoke / validation 输出 commit 进 main
- ❌ 没读 W4 jsonl 行（除 design / checkpoint 中已记录的字段确认）
- ❌ 没选 / 优化 / 扫 candidate_threshold（v1 seed = 0.60 是 design 锁定）
- ❌ 没运行 `pytest`
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*`
- ✅ 只新增 1 份 markdown checkpoint 文档（本文件）
