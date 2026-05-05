# Step 3R-3.3C — Real W1-W4 Validation Run Design

## 1. 背景
- Step 3R-3.3 4-fold validation run design 已完成并进入 main（commit `8a24295`）。
- Step 3R-3.3 4-fold validation run checkpoint 已完成并进入 main（commit `2535467`）。
- Step 3R-3.3A dry-run validation orchestrator 已完成并进入 main（commit `32f196a`）；checkpoint 已 merge（commit `9fbd9b5`）。
- Step 3R-3.3B limited-record smoke 已通过（8 行 in-memory fixture，4 文件落盘 `logs/regime_validation/continuous_smoothing_v1_limited_smoke_20260505_231620/`，DB 不变，final_test_touched=false）；checkpoint 已 merge（commit `d299247`）。
- 三层（candidate / adapter / helper）+ orchestrator 的 plumbing 全部就绪。
- 现在准备**设计** real W1-W4 validation run（首个使用真实 replay rows 的执行）。
- 本文**只设计**，不执行：不改代码、不写 DB、不读 W4 jsonl 行（除 §4 抽样字段确认）、不跑 validation。

## 2. real run 目标
- 使用真实 W1 / W2 / W3 / W4 replay rows 跑一次 4-fold validation。
- 通过现有 `run_continuous_smoothing_validation(...)` 公共 API。
- 实际经历：load → enrich (regime_labels + candidate) → adapt → validate → write outputs。
- 生成本地 4 文件：
  - `replay_validation_records.json`（`replay_validation_records.v1`）
  - `regime_validation_report.json`（`regime_validation_report.v1`）
  - `regime_validation_summary.md`
  - `run_manifest.json`（`regime_validation_run_manifest.v1`）
- **不写 DB**。
- **不进 main**（output 全部 untracked）。
- **不触碰 2026** 区间。
- **不证明** candidate pass；**不**作为 production permission。
- **不**驱动 hard / forced / required / `_PROTECTION_LAYER_CONNECTED` 派生。

## 3. 数据来源设计

| 角色 | source | 状态 |
|---|---|---|
| **W4 replay rows** | `logs/historical_training/three_system_w4_2024_08_2025_12/three_system_replay_results.jsonl` | ✅ 已就绪（353 paired，2024-08-03 → 2025-12-31，本地 untracked） |
| **W4 manifest** | `logs/historical_training/three_system_w4_2024_08_2025_12/validation_ready_manifest.json` | ✅ schema=`w4_replay_manifest.v1`，`status="ok"`，`final_test_touched=false`，`records_generated=353`，`paired_outcomes=353` |
| **W1 source（2023-01-03 → 2023-08-31）** | **未确认 / 必须 audit** | ⚠️ 候选见 §4 |
| **W2 source（2023-09-01 → 2024-02-29）** | **未确认 / 必须 audit** | ⚠️ 候选见 §4 |
| **W3 source（2024-03-01 → 2024-08-02）** | **未确认 / 必须 audit** | ⚠️ 候选见 §4 |
| **regime labels source** | 3R-2 `build_regime_labels(...)` + 本地 csv / `data/*` | ✅ 接口已就绪；caller 提供 DataFrame |
| **`final_test_cutoff`** | `"2026-01-01"`（与全链一致） | ✅ |

### 3.1 强约束
- 若 W1 / W2 / W3 source **任一**不确定 → real run **不能启动**，必须先做 §4 source audit（Step 3R-3.3C-A）。
- 不允许把 W1 / W2 / W3 用不同口径拼成 paired rows；schema 必须与 W4 一致（`as_of_date` / `prediction_for_date` / `direction_correct` / `final_direction` 等核心字段对齐）。
- 不允许调 yfinance / requests / 任何网络获取 paired outcome；只接受**已落地**的 jsonl / DB 行。
- 不允许重新跑 replay 来生成 W1 / W2 / W3。

## 4. W1 / W2 / W3 source audit plan（Step 3R-3.3C-A 前置 gate）

### 4.1 必须确认的字段对齐
audit 必须证明 W1 / W2 / W3 候选 source 的每条 row 至少含：
- `as_of_date`（str，2023-2025 区间，**< 2026-01-01**）
- `prediction_for_date`（str，**< 2026-01-01**）
- `final_direction`（与 W4 同口径，例如 `偏多 / 偏空 / 震荡 / 中性`）
- `direction_correct` 或可推导出 paired outcome 的等价字段
- `ready=true`（与 W4 一致）
- 不含 `error` / `failed` 标记

### 4.2 候选 source 清单
按优先级评估（仅 audit，不修改）：

| # | 候选 | 路径 / 来源 | 已知信息 |
|---|---|---|---|
| 1 | `three_system_1005` 复用 | `logs/historical_training/three_system_1005/three_system_replay_results.jsonl` | schema 与 W4 同（`three_system_replay_results`），但 summary 显示 `total_cases=5`；样本量不足，**单独**不够 W1+W2+W3 |
| 2 | DB replay-tagged predictions | `avgo_agent.db` `prediction_log` + `outcome_log` join，过滤 replay-source rows | 字段对齐需要 audit；不允许写 DB；只读取，不修改 |
| 3 | `03_fresh_replay` | `logs/historical_training/03_fresh_replay/` | 未确认 schema / 日期范围 |
| 4 | `exclusion_action_validation_2e` / `exclusion_action_validation_2e_v2` | `logs/historical_training/exclusion_action_validation_2e*/` | 与 exclusion validation 关联，未确认是否 paired outcome |
| 5 | 重跑 W1 / W2 / W3 replay | 类似 8D.3 W4 流程 | **不在本设计范围**；若 audit 失败需另行 launch review |

### 4.3 audit 行为约束
- audit 仅做**只读**字段抽样 + 日期范围统计 + paired count 统计。
- audit **不**写 DB。
- audit **不**改代码。
- audit **不**新增字段 / 不修改 jsonl。
- audit **不**触碰 2026 行（`as_of_date >= 2026-01-01` 立刻 stop 并报告）。
- audit 必须**逐 window** 给出：源路径、记录数、paired_outcomes 数、日期范围、字段缺失、warnings。
- audit 输出**只**作 markdown checkpoint（`tasks/step_3r3_3c_a_w1_w2_w3_source_audit_checkpoint.md`）。
- audit 不通过 → real run 永久 abort，回到设计层重新选 source。

### 4.4 audit 通过条件
- W1 / W2 / W3 各自 paired_outcomes ≥ 协议下限（与 W4 helper 的 `minimum_window_sample_size` gate 一致；具体阈值已在 3R-4.2 helper 锁定）。
- 每条 row schema 与 W4 对齐。
- 没有 2026 行。
- 没有 lookahead（`prediction_for_date <= as_of_date` 必须为 false）。
- 全部满足 → 才允许进入 Step 3R-3.3C-B（real run wrapper）。

## 5. candidate_threshold policy
- `candidate_threshold = 0.60`（design seed，与 3R-3.3 / 3R-3.3A / 3R-3.3B 一致）。
- **不**扫 threshold（任何 sweep 必须独立 launch review）。
- **不**调 SEED coefficients（3R-3.1 模块常量）。
- **不**根据 real run 结果反推 threshold。
- **不**根据 real run 结果调 6 metric / 7 gate threshold。
- 若 first real run fail → **不**调参，按 §10.1 / §13 走回 design 层。
- 若 first real run pass → **不**自动启 hard / 不改 required；仅 eligible for design review。
- caller 必须显式传入 `candidate_threshold`；不允许默认 silent fallback override。

## 6. regime labels source
- 每条 row 在 enrich 阶段调 `build_regime_labels(avgo_df, peer_dfs, market_dfs, as_of_date=row["as_of_date"])`（3R-2 builder）。
- `as_of_date` 严格用该 row 的 `as_of_date`；**不**读取 future rows / **不**用未来数据计算 label。
- 输入 DataFrame 全部来自**本地** csv / `data/*`；**不**调 yfinance / requests。
- **不**用 W4 jsonl 中的 `pos20 percentage` / `five_state_projection` / 任何 future-leaking 字段直接喂 candidate；candidate 只接 `regime_labels.v1`。
- 若某 row 无法生成合法 `regime_labels.v1`（缺数据、refusal、异常）→ row skip + warning，不 abort 整个 run。
- 若 `regime_labels.v1.final_test_refusal=true` → row skip + `final_test_touched=true` 标记触发。
- regime label 由 caller 注入的 `regime_label_provider` callable 提供；orchestrator 不内嵌任何 builder 调用路径。

## 7. output directory
设计：
```
logs/regime_validation/continuous_smoothing_v1_real_w1_w4_YYYYMMDD_HHMMSS/
```
`YYYYMMDD_HHMMSS` 由 wrapper 启动时生成（与 3R-3.3 §6 一致）。

### 7.1 输出 4 文件
- `replay_validation_records.json`
- `regime_validation_report.json`
- `regime_validation_summary.md`
- `run_manifest.json`

### 7.2 处置规则
- **不**进 main（与 8D.4 / 3R-3.3 / 3R-3.3B 一致；本地 untracked）。
- **不**覆盖旧输出：timestamp 后缀确保独立目录；同名目录已存在 → orchestrator 抛 `FileExistsError` abort（行为与 3R-3.3A 一致）。
- **不**写 DB。
- **不**覆盖 W4 outputs（W4 是不可变 baseline，仅只读）。
- **不**写入 `logs/prediction_log.jsonl`。
- **不**`git add`：`logs/regime_validation/` 整体保持 untracked。
- 可删除 / 可重跑（新 timestamp = 新目录）。
- `output_dir` 必须**不存在**才允许写入。

## 8. DB guard
- run 启动**前**记录：
  - `avgo_agent.db` mtime + size
  - `data/market_data.db` mtime + size（若存在）
  - `avgo_agent.db.backup_*` 文件计数
- run 结束**后**再次记录上述三项。
- 任一变化 → run 整体 invalid，结果**不允许**作为后续设计依据：
  - mtime / size 变化
  - 出现新的 `avgo_agent.db.backup_*`
  - market_data.db mtime / size 变化
- DB guard 由 wrapper（Step 3R-3.3C-B）实现；orchestrator 本身不读 DB。
- `services.prediction_store` / `sqlite3` / `services.outcome_capture` 在整个 run 中**禁止 import**（与 3R-3.3A `禁止 import` 列表一致）。

## 9. final test guard（与 3R-3.3 §9 6 层一致）
cutoff = `"2026-01-01"`（硬编码不可变）。任一项触发 → run `report_status="error"` + `final_test_touched=true`：

| # | 检查 | 来源 |
|---|---|---|
| 1 | row `as_of_date >= "2026-01-01"` 或 `prediction_for_date >= "2026-01-01"` | wrapper + orchestrator + adapter G2 |
| 2 | W4 manifest `final_test_touched=true` | adapter + helper 双重 |
| 3 | `regime_labels.v1.final_test_refusal=true` | 3R-2 builder |
| 4 | `continuous_smoothing_candidate.v1.final_test_refusal=true` | 3R-3.1 candidate |
| 5 | `replay_validation_records.v1.final_test_refusal=true` | 3R-4.3A adapter |
| 6 | `regime_validation_report.v1.final_test_refusal=true` | 3R-4.2 helper |

补充：
- run_manifest `final_test_touched` must be `false`。
- run_manifest `final_test_cutoff` must be `"2026-01-01"`。
- report `final_test_refusal` must be `false`。
- 任一为 true → result invalid，**不**允许进入下一步（包括 result checkpoint 之外的任何下游）。

## 10. expected output / acceptance
**first real run 不要求 pass**（与 3R-3.3 §10 一致）。`report_status` 可以 `pass` / `fail` / `error`。

### 10.1 acceptance 是 plumbing 级别 + 数据完整性级别（11 项）
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
| 10 | output_dir untracked（`git status` 无 tracked modified） |
| 11 | 没有 threshold sweep / 没有 hard / 没有 required 改动 |

### 10.2 first real run 可能 fail 的合法理由（与 3R-3.3 §10.1 一致）
- 某 window FER > 0.10
- 某 fold cross_window_variance > 0.10
- 某 fold paired < `minimum_window_sample_size`
- 某 window survival_preservation < 0.80
- net_benefit < +0.05
- accuracy_delta_vs_baseline 不达标

→ fail **不**触发调参；fail **不**意味着 caller / orchestrator bug；fail 走回 candidate / threshold design review。

## 11. no-go rules（11 项；任一触发 → run abort）
| # | 条件 |
|---|---|
| 1 | W1 / W2 / W3 source 未通过 §4 audit |
| 2 | W4 manifest 缺失 / parse 失败 / `final_test_touched=true` |
| 3 | DB 在 run 期间被修改（mtime / size / backup count 任一变化） |
| 4 | 任一 row `as_of_date >= "2026-01-01"` 或 `prediction_for_date >= "2026-01-01"` |
| 5 | 任意一处发生 threshold sweep / SEED 调整 / metric 调整 |
| 6 | `records_adapted = 0`（adapter 输出空） |
| 7 | 任一 fold（W1 / W2 / W3 / W4）records 计数为 0 |
| 8 | `output_dir` 已存在（不允许覆盖） |
| 9 | report schema 缺必备字段 |
| 10 | 任一处启 hard / forced / 改 required / 改 04-05-07 required 字段 |
| 11 | 任一层 import 了禁用 module（`services.prediction_store` / `sqlite3` / `yfinance` / `requests` / `longbridge` / `broker` / `paper_trade` / `predict` / `scanner` / `streamlit`） |

## 12. run command design（仅设计，不执行）

### 12.1 未来调用示意（仅作设计参考）
```bash
python3 scripts/run_real_continuous_smoothing_validation.py \
  --candidate-threshold 0.60 \
  --w4-jsonl logs/historical_training/three_system_w4_2024_08_2025_12/three_system_replay_results.jsonl \
  --w4-manifest logs/historical_training/three_system_w4_2024_08_2025_12/validation_ready_manifest.json \
  --w1-source <TBD by audit> \
  --w2-source <TBD by audit> \
  --w3-source <TBD by audit> \
  --output-dir logs/regime_validation/continuous_smoothing_v1_real_w1_w4_<TS>
```

### 12.2 wrapper 责任（Step 3R-3.3C-B 实施范围）
- 解析 CLI args（含 W4 jsonl / W4 manifest / W1-W3 sources / threshold / output_dir / cutoff）。
- 加载 W4 manifest 文件 → dict（注意：现有 orchestrator 不读文件，wrapper 必须加载并注入）。
- 逐 window 加载 jsonl 行 → in-memory `replay_rows`。
- 构造 `regime_label_provider` callable（封装 3R-2 builder + 本地 csv DataFrame 加载）。
- DB guard：run 前 / 后记录 mtime / size / backup count，diff 写入 wrapper-side log。
- 调用 `run_continuous_smoothing_validation(...)` 公共 API。
- 不暴露 SEED / gate threshold override。
- 不暴露 sweep 接口。

### 12.3 现状缺口
- 当前 `scripts/run_continuous_smoothing_validation.py` **不**提供 CLI。
- 当前公共 API 接受 in-memory `replay_rows` + in-memory `w4_manifest` dict。
- 真实 run 需要：
  - **wrapper script** 负责 jsonl/manifest 文件 IO + DataFrame 准备 + DB guard
  - **`regime_label_provider` 实现**（封装 3R-2 builder）
- 这两块**不在本 design 范围**；交给 Step 3R-3.3C-B implementation 设计 + 实施。
- 本设计仅冻结：source / output / cutoff / DB guard / acceptance / no-go 边界。

## 13. 与 3R-5 / 3R-6 的关系
- 即使 real report `overall_status="pass"` → **不**自动进 formula（3R-5）。
- 即使 real report `overall_status="pass"` → **不**自动进 simulator（3R-6）。
- pass 唯一允许的下游：进入 design review 讨论 3R-5 formula scope。
- fail **不**触发调参；fail 唯一允许的下游：回 candidate / threshold design 重新设计。
- 3R-5 / 3R-6 仍需**单独** launch review；3R-3.3C 不构成 implicit 授权。
- 不允许把 first real report 摘要直接当作 production gate。

## 14. 推荐实施顺序

| # | 子步骤 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **commit 本 design**（Step 3R-3.3C real W1-W4 validation run design） | 把 §1-16 边界固化到 main | 本轮 / 下一轮 |
| 2 | **Step 3R-3.3C checkpoint** | 状态归档（在 design 进 main 之后） | 紧接其后 |
| 3 | **Step 3R-3.3C-A W1/W2/W3 source audit** | 仅 read-only 扫描候选 source；产物 audit checkpoint markdown；不改代码 | 中（design + checkpoint 进 main 后） |
| 4 | **Step 3R-3.3C-B real run script / wrapper** | wrapper 实现 + `regime_label_provider` 实现 + DB guard；focused tests；不跑 real run | 中（audit 通过后） |
| 5 | **Step 3R-3.3C-C real run execution** | 单次跑真实 W1-W4；output 本地 untracked | 中（wrapper 进 main 后） |
| 6 | **Step 3R-3.3C result checkpoint** | 摘要 / report_status / per-window / fail_reason 归档 | 中（execution 完成后） |

## 15. 禁止事项

| # | 禁止 | 理由 |
|---|---|---|
| 1 | **不**跑 real validation before §4 source audit 通过 | 防止口径错配 / lookahead |
| 2 | **不**扫 threshold | 与 §5 一致 |
| 3 | **不**调 SEED coefficients | 模块常量；变更必须 launch review |
| 4 | **不**调 6 metric / 7 gate threshold | 3R-4 protocol 锁定 |
| 5 | **不**写 DB | 全程 read-only |
| 6 | **不**覆盖 W4 outputs | W4 不可变 baseline |
| 7 | **不**启 hard / forced / `anti_false_exclusion_triggered` | 三重 NO-GO |
| 8 | **不**改 04 / 05 / 07 required | Step 2G 全程边界 |
| 9 | **不**触碰 2026 final test range | 6 层 hard stop |
| 10 | **不**接 trading（`longbridge` / `broker` / `paper_trade`） | 永久封禁 |
| 11 | **不**让 `_PROTECTION_LAYER_CONNECTED` 翻 True | 与 v1 / 3R-0 / 3R-4 一致 |
| 12 | **不**让 `hard_gate_status.protection_layer_connected` 自动 pass | 同上 |
| 13 | **不**改 `hard_exclusion_allowed` / `primary_blocker` 派生 | 同上 |
| 14 | **不**直接进入 formula（3R-5）/ simulator（3R-6） | 必须先过 result checkpoint |
| 15 | **不** commit validation outputs（`logs/regime_validation/` 全部 untracked） | 与 3R-3.3 §6.2 / 8D.4 §6.3 一致 |
| 16 | **不** import `services.prediction_store` / `sqlite3` / `yfinance` / `requests` / `predict` / `scanner` / `streamlit` 在 wrapper 任一层 | DB / 网络 / production isolation |
| 17 | **不**调 `regime_label_provider` 把 future-leaking 字段（`pos20` / `five_state_projection` 等）喂入 candidate | anti-lookahead |
| 18 | **不**在 first real run fail 时调任何参数 | 与 §10.1 / §13 一致 |
| 19 | **不**触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*` | 历史防护 |
| 20 | **不**把 `logs/regime_validation/` 任何子目录 `git add` | 与 §7.2 一致 |

## 16. 严守边界
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
- ❌ 没改 Step 3R-3.3 / 3R-3.3A / 3R-3.3B 已 merge 的 design / checkpoint / 实施
- ❌ 没改 Step 2G-8D / 8D.1A / 8D.2 / 8D.3 / 8D.4 文档或代码
- ❌ 没把 W4 / smoke / validation 输出 commit 进 main
- ❌ 没读 W4 jsonl 行（除 §3-§4 抽样字段确认）
- ❌ 没选 / 优化 / 扫 candidate_threshold（v1 seed = 0.60 是 design 锁定）
- ❌ 没运行 `pytest`
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*`
- ✅ 只新增 1 份 markdown design 文档（本文件）
