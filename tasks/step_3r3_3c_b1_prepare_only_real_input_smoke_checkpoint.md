# Step 3R-3.3C-B1 — Prepare-Only Real Input Smoke Checkpoint

## 1. 当前完成状态
- Step 3R-3.3C real W1-W4 validation run design + checkpoint 已 merge（commits `226e354` / `d2773aa`）。
- Step 3R-3.3C-A W1-W3 source audit checkpoint 已 merge（commit `1280060`）。
- Step 3R-3.3C-B real W1-W4 validation input wrapper（implementation + checkpoint）已 merge（commits `23da6c9` / `a51ead8`）。
- 本轮完成 **Step 3R-3.3C-B1 prepare-only real input smoke**：
  - 使用真实 `avgo_agent.db`（read-only）
  - 使用真实 W4 jsonl（`logs/historical_training/three_system_w4_2024_08_2025_12/three_system_replay_results.jsonl`）
  - 使用真实 W4 manifest（`logs/historical_training/three_system_w4_2024_08_2025_12/validation_ready_manifest.json`）
  - 调用 wrapper CLI `--prepare-inputs-only`
  - 只输出 stdout JSON summary（10 字段）
  - **未**跑 validation
  - **未**创建 report output
  - **未**写 DB
- 本 checkpoint 用于固化：smoke 命令 / stdout summary / row count 对账 / acceptance 13 项 / DB 三重 fingerprint 前后一致 / output 文件未变 / final-test guard / 当前仍未做 / 允许下一步 / 禁止事项 / 边界。
- **real W1-W4 validation 仍未执行。**
- **real `regime_label_provider` 仍未实现。**
- **real `regime_validation_report.v1` 仍未产出。**

## 2. 当前 main 状态
- main 最新 commit：`a51ead8`
- commit message：`docs(contract): Step 3R-3.3C-B real validation input wrapper checkpoint`
- 上游：`origin/main` 已同步。
- 本轮没有 commit；没有 push。
- 本轮没有代码改动；没有改 DB schema；没有改 production 主链。
- full pytest 基线维持 commit `23da6c9` 时的 **2857 / 0 failed / 10 skipped**（本轮纯 runtime + 文档；未运行 pytest）。

| 项 | 是否触碰 |
|---|---|
| 改代码 | ❌ 否 |
| 改 service / candidate / adapter / helper / orchestrator / wrapper | ❌ 否 |
| 改 DB schema | ❌ 否 |
| 写 DB | ❌ 否 |
| 跑 replay | ❌ 否 |
| 跑 real validation | ❌ 否 |
| 创建 regime_validation report output | ❌ 否 |
| 接 yfinance / 网络 | ❌ 否 |
| 接 trading API | ❌ 否 |
| 触碰 2026 final-test range | ❌ 否 |

## 3. smoke 命令
```bash
python3 scripts/run_real_continuous_smoothing_validation.py \
  --prepare-inputs-only \
  --db-path avgo_agent.db \
  --w4-jsonl logs/historical_training/three_system_w4_2024_08_2025_12/three_system_replay_results.jsonl \
  --w4-manifest logs/historical_training/three_system_w4_2024_08_2025_12/validation_ready_manifest.json \
  --final-test-cutoff 2026-01-01
```
执行环境：repository 根目录（`/Users/may/Desktop/stock-analyzer-main/`），main 分支当前 commit `a51ead8`。

退出码：**0**。

## 4. stdout JSON summary
```json
{
  "schema_version": "real_validation_input_bundle.v1",
  "db_path": "avgo_agent.db",
  "db_fingerprint": {
    "path": "avgo_agent.db",
    "exists": true,
    "mtime_ns": 1777833249653954308,
    "size_bytes": 11206656
  },
  "w1_w3_row_count": 286,
  "w4_jsonl_path": "logs/historical_training/three_system_w4_2024_08_2025_12/three_system_replay_results.jsonl",
  "w4_row_count": 353,
  "w4_manifest_path": "logs/historical_training/three_system_w4_2024_08_2025_12/validation_ready_manifest.json",
  "w4_manifest_status": "ok",
  "final_test_cutoff": "2026-01-01",
  "warnings": []
}
```

## 5. row count 对账
| 来源 | 数值 | 说明 |
|---|---|---|
| W1-W3 (smoke) | **286** | wrapper DB read-only loader 输出（一次 SQL JOIN + filter） |
| W1 (audit) | 110 | Step 3R-3.3C-A 已锁 |
| W2 (audit) | 93 | Step 3R-3.3C-A 已锁 |
| W3 (audit) | 83 | Step 3R-3.3C-A 已锁 |
| 110 + 93 + 83 | 286 | **完全一致**，DB filter 没有错配 |
| W4 (smoke) | **353** | wrapper jsonl loader 输出 |
| W4 manifest `paired_outcomes` | 353 | 与 wrapper 输出**完全一致** |
| W4 manifest `records_generated` | 353 | 与 wrapper 输出**完全一致** |
| total candidate input rows | **639** | W1-W3 286 + W4 353 |

records 尚未 adapted（adapter 仍未运行），records_loaded / records_adapted / report_status 等 orchestrator 字段**不存在**于本轮 bundle。bundle 仅是 input 装配产物，不是 validation 报告。

## 6. acceptance 验证
| # | 标准 | 实测 | 状态 |
|---|---|---|---|
| 1 | exit code = 0 | 0 | ✅ |
| 2 | stdout 是 valid JSON | parse 通过 | ✅ |
| 3 | summary 含 9 必备字段 + warnings | 全部 present | ✅ |
| 4 | `w1_w3_row_count` 与 audit 一致 | 286 | ✅ |
| 5 | `w4_row_count` 与 manifest 一致 | 353 | ✅ |
| 6 | `w4_manifest_status` = `"ok"` | `"ok"` | ✅ |
| 7 | `final_test_cutoff` = `"2026-01-01"` | `"2026-01-01"` | ✅ |
| 8 | 不创建任何 new output 文件 | regime_validation/ 列表前后一致 | ✅ |
| 9 | `avgo_agent.db` mtime/size 不变 | 1777833249 / 11206656 前后一致 | ✅ |
| 10 | `data/market_data.db` mtime/size 不变 | 1777392167 / 13127680 前后一致 | ✅ |
| 11 | DB backup count 不变 | 7 → 7 | ✅ |
| 12 | git status tracked clean | tracked clean | ✅ |
| 13 | 不触碰 2026 | warnings=[] 无 cutoff filter 触发；row counts 与 audit 完全一致 | ✅ |

## 7. DB before / after
| 项 | before | after | diff |
|---|---|---|---|
| `avgo_agent.db` mtime（秒精度） | 1777833249 | 1777833249 | 0 |
| `avgo_agent.db` size（bytes） | 11206656 | 11206656 | 0 |
| `data/market_data.db` mtime（秒精度） | 1777392167 | 1777392167 | 0 |
| `data/market_data.db` size（bytes） | 13127680 | 13127680 | 0 |
| `avgo_agent.db.backup_*` 文件计数 | 7 | 7 | 0 |

说明：
- `db_fingerprint.mtime_ns = 1777833249653954308`（纳秒精度）≈ `1777833249`（秒精度），二者一致。
- DB 未修改（一次 sqlite3 read-only JOIN + close，无写）。
- `data/market_data.db` 未被 wrapper 触碰（不在 wrapper 读取范围）。
- 7 个 `avgo_agent.db.backup_*` 仍是审查前的同 7 个文件，未新增。

## 8. output 文件验证
- `logs/regime_validation/` 列表前后一致：仍只含 1 个旧目录 `continuous_smoothing_v1_limited_smoke_20260505_231620/`（Step 3R-3.3B 旧 smoke）。
- 没有创建：
  - `replay_validation_records.json`
  - `regime_validation_report.json`
  - `regime_validation_summary.md`
  - `run_manifest.json`
- CLI 只向 stdout 输出 JSON；未写文件系统。
- 没有创建任何新的 `logs/historical_training/*` 子目录。
- 没有写 `logs/prediction_log.jsonl`（已是环境产物，本轮未触碰）。

## 9. final-test guard
- `final_test_cutoff = "2026-01-01"`（CLI args 显式传入；与全链 cutoff 一致）。
- `warnings = []`（无任何 cutoff filter 触发的告警）。
- 没有 2026 cutoff 触发：
  - W1-W3 区间（2023-01-03 ~ 2024-08-02）天然落在 cutoff 之前
  - W4 区间（2024-08-03 ~ 2025-12-31）天然落在 cutoff 之前
  - DB SQL filter 已强制 `analysis_date < cutoff` 且 `prediction_for_date < cutoff`（即使 DB 中存在 retrospective 2026 行也会被过滤）
  - W4 jsonl loader 已强制 cutoff（与 audit 锁定一致）
- `final_test_touched` 不在 bundle schema 中（这是 orchestrator 字段，不是 input bundle 字段）。
- 真实 validation 仍未运行；任何 `regime_validation_report.v1.final_test_refusal` 字段尚未产生。

## 10. 当前仍未做
- 未跑 real W1-W4 validation。
- 未生成 `replay_validation_records.v1`。
- 未生成 `regime_validation_report.v1`。
- 未生成 `regime_validation_run_manifest.v1`（real run 版本）。
- 未实现 real `regime_label_provider`（封装 3R-2 builder + 本地 csv DataFrame 加载）。
- 未写 real `output_dir`（`logs/regime_validation/continuous_smoothing_v1_real_w1_w4_<TS>/`）。
- 未判断 candidate pass / fail。
- 未跑 threshold scan（永久封禁；仅作记录）。
- 未调 SEED coefficients（永久封禁；仅作记录）。
- 未启 hard / forced / `_PROTECTION_LAYER_CONNECTED`（永久封禁）。

## 11. 允许下一步
| # | 候选 | 状态 |
|---|---|---|
| 1 | **Step 3R-3.3C-C real validation execution design** | ✅ 允许（在本 checkpoint 进入 main 后启动） |
| 2 | 必须先设计 real `regime_label_provider`（封装 3R-2 builder + 本地 csv loader；不接 yfinance；不读 future-leaking 字段） | ✅ |
| 3 | 必须定义真实 `output_dir`（`logs/regime_validation/continuous_smoothing_v1_real_w1_w4_<TS>/`） | ✅ |
| 4 | 必须复用 wrapper 的 DB guard（run 前 / 后双 fingerprint） | ✅ |
| 5 | 必须**不**写 DB | ✅ |
| 6 | 仍**不**得扫 threshold | ✅ |
| 7 | 仍**不**得自动启 hard / Gate 5 / Gate 6 | ✅ |
| 8 | 必须保证 6 层 final-test guard 全部生效 | ✅ |
| 9 | 必须保证 R4-like fixture acceptance test 仍 pass | ✅ |
| 10 | wrapper / candidate / adapter / helper / orchestrator / labels builder 现有行为 | ❌ 不改（仅只读调用） |

## 12. 禁止事项
| # | 禁止 | 理由 |
|---|---|---|
| 1 | **不**直接进入 Step 3R-5 formula design | 必须先过 3R-3.3C-C result checkpoint |
| 2 | **不**直接进入 Step 3R-6 simulator | 必须先过 3R-5 design |
| 3 | **不**扫 threshold | v1 seed 0.60 锁定；任何 sweep 必须独立 launch review |
| 4 | **不**调 SEED coefficients | 3R-3.1 模块常量 |
| 5 | **不**调 6 metric / 7 gate threshold | 3R-4 protocol 锁定 |
| 6 | **不**写 DB | 全程 read-only |
| 7 | **不**接 trading（`longbridge` / `broker` / `paper_trade`） | 永久封禁 |
| 8 | **不**触碰 2026 final-test range | 6 层 hard stop 保留 |
| 9 | **不** commit validation outputs | `logs/regime_validation/` 全部 untracked |
| 10 | **不**让 report `pass` 自动启 hard / Gate 5 / Gate 6 | 与 3R-3.3 §11 一致 |
| 11 | **不**让 `_PROTECTION_LAYER_CONNECTED` 翻 True | 与 v1 / 3R-0 / 3R-4 一致 |
| 12 | **不**改 04 / 05 / 07 required | Step 2G 全程边界 |
| 13 | **不**改 `hard_exclusion_allowed` / `primary_blocker` 派生 | 同上 |
| 14 | **不**让 `regime_label_provider` 通过 future-leaking 字段（`pos20` / `five_state_projection` / `predict_result_json`）反喂 candidate | anti-lookahead |
| 15 | **不** import `services.prediction_store` / `services.outcome_capture` 写路径 / `yfinance` / `requests` / `predict` / `scanner` / `streamlit` 在 real provider / wrapper / orchestrator 任一层 | DB / 网络 / production isolation |
| 16 | **不**用 first real run 数据反推 candidate_threshold | 阈值变更必须经 launch review |
| 17 | **不**触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*` | 历史防护 |
| 18 | **不**重跑 W1-W3 replay | DB 已足够（audit 已锁定） |

## 13. 下一步建议

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **commit 本 checkpoint** | 把 §1-14 smoke 结果 + 对账 + 边界固化到 main | 本轮 / 下一轮 |
| 2 | **Step 3R-3.3C-C real validation execution design** | 设计 real `regime_label_provider` + real run wrapper / glue + output_dir + DB guard 流程 | 高（本 checkpoint 进 main 后） |
| 3 | **Step 3R-3.3C-C design checkpoint** | 状态归档 | 紧接其后 |
| 4 | **Step 3R-3.3C-C-A real `regime_label_provider` implementation** | 封装 3R-2 builder + 本地 csv DataFrame 加载（`data/*` / 已有 csv）；focused tests；不接 yfinance；不跑 validation | 中（design + checkpoint 进 main 后） |
| 5 | **Step 3R-3.3C-C-B real validation execution glue** | 把 wrapper 的 input bundle + real provider + dry-run orchestrator 串起来；focused tests 仍**不**跑 real run；只验证 plumbing | 中（C-A 进 main 后） |
| 6 | **Step 3R-3.3C-C-C single real validation run** | 单次本地跑真实 W1-W4；输出本地 untracked；不进 main | 中（C-B 进 main 后） |
| 7 | **Step 3R-3.3C result checkpoint** | 摘要 / report_status / per-window / fail_reason 归档 | 中（C-C 完成后） |
| 8 | **不推荐**直接 Step 3R-5 formula design | 必须先过 result checkpoint | ❌ |
| 9 | **不推荐** Step 3R-6 simulator | 必须先过 3R-5 design | ❌ |
| 10 | **不推荐**让 first real run pass 自动启 hard / Gate 5 / Gate 6 | 与 3R-3.3 §11 一致 | ❌ |
| 11 | **不推荐**升级 04 required | Step 2G 全程边界 | ❌ |
| 12 | **不推荐**触碰 2026 final-test range | 永久封禁 | ❌ |
| 13 | **不推荐**让 `_PROTECTION_LAYER_CONNECTED` 翻 True | 与 v1 / 3R-0 / 3R-4 一致 | ❌ |
| 14 | **不推荐**用 first real run 数据反推 candidate_threshold | 阈值变更必须经 launch review | ❌ |
| 15 | **不推荐**重跑 W1-W3 replay | DB 已足够（audit 已锁定） | ❌ |

**关键判断**：顺序 = 本 checkpoint → **3R-3.3C-C design** → C-A real provider → C-B execution glue → C-C single real run → result checkpoint → 3R-5 formula → 3R-6 simulator。任何一步 fail → 整 candidate 报废，回到 design 层重新设计。

## 14. 严守边界
本文是**纯 checkpoint markdown**：

- ❌ 没改任何代码（`services/*` / `ui/*` / `tests/*` / `scripts/*` 全部未触碰）
- ❌ 没改 DB schema
- ❌ 没写 DB（runtime 只用 sqlite3 `mode=ro` URI；fingerprint 前后一致）
- ❌ 没运行 replay
- ❌ 没运行 real validation
- ❌ 没生成 `replay_validation_records.v1` / `regime_validation_report.v1` / `regime_validation_run_manifest.v1` 任一
- ❌ 没改 `run_predict` / `predict.py` / `scanner.py` / `prediction_store.py` / `app.py`
- ❌ 没改 `services/regime_features_builder.py` / `services/regime_labels_builder.py` / `services/regime_validation_helper.py` / `services/continuous_smoothing_candidate.py` / `services/replay_validation_record_adapter.py` / `services/historical_replay_training.py` / 任何 ui 模块 / 任何 builder
- ❌ 没改 `scripts/run_continuous_smoothing_validation.py` 或 `scripts/run_real_continuous_smoothing_validation.py`
- ❌ 没改 `tests/test_run_continuous_smoothing_validation.py` 或 `tests/test_run_real_continuous_smoothing_validation.py`
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
- ❌ 没改 Step 3R-3.3 / 3R-3.3A / 3R-3.3B / 3R-3.3C / 3R-3.3C-A / 3R-3.3C-B 已 merge 文档 / 实施
- ❌ 没改 Step 2G-8D / 8D.1A / 8D.2 / 8D.3 / 8D.4 文档或代码
- ❌ 没把 W4 / smoke / `logs/regime_validation/` / `logs/prediction_log.jsonl` / DB backup / `agent_loop.py` / `.claude/worktrees/` 任一 commit 进 main
- ❌ 没创建任何新的 `logs/regime_validation/*` 子目录
- ❌ 没运行 `pytest`（本轮纯 runtime smoke + 文档；测试基线维持 commit `23da6c9` 时的 2857 / 0 failed / 10 skipped）
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*`
- ✅ 只新增 1 份 markdown checkpoint 文档（本文件）
