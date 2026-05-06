# Step 3R-3.3C-C-C — Execution Glue Design Checkpoint

> 本文是 **checkpoint markdown** —— 不改代码、不写 DB、不跑 replay、不跑 validation、不 commit / push、不接 trading API、不启 hard / forced、不改 required、不触碰 2026 final-test range、不 add `logs/regime_validation/` / W4 / smoke output / `logs/prediction_log.jsonl`、不处理 DB backup / stash / `.claude/worktrees/`。

## 1. 当前完成状态

| 组件 | 状态 | 来源 |
|---|---|---|
| real input wrapper（`build_real_validation_inputs(...)` + DB / W4 jsonl loader + DB fingerprint guard） | ✅ 已 merge | `scripts/run_real_continuous_smoothing_validation.py`（commit `23da6c9`） |
| Step 3R-3.3C-B real wrapper checkpoint | ✅ 已 merge | commit `a51ead8` |
| Step 3R-3.3C-B1 prepare-only smoke checkpoint（W1-W3=286 + W4=353，total=639） | ✅ 已 merge | commit `bcf5eda` |
| Step 3R-3.3C-C real validation execution **design** | ✅ 已 merge | commit `9720e0a` |
| Step 3R-3.3C-C real validation execution design checkpoint | ✅ 已 merge | commit `b1d82ee` |
| Step 3R-3.3C-C-A market data source audit checkpoint | ✅ 已 merge | commit `4282058` |
| real `regime_label_provider` 实现（`build_real_regime_label_provider(...)`） | ✅ 已 merge | `services/real_regime_label_provider.py`（commit `65f8352`） |
| Step 3R-3.3C-C-B real regime label provider checkpoint | ✅ 已 merge | commit `7f4d9b8` |
| dry-run orchestrator（`run_continuous_smoothing_validation(...)`） | ✅ 已 merge | `scripts/run_continuous_smoothing_validation.py`（Step 3R-3.3A） |
| candidate 生成器（`build_continuous_smoothing_candidate(...)`） | ✅ 已 merge | `services/continuous_smoothing_candidate.py`（Step 3R-3.1） |
| replay validation record adapter | ✅ 已 merge | `services/replay_validation_record_adapter.py`（Step 3R-4.3A） |
| regime validation helper | ✅ 已 merge | `services/regime_validation_helper.py`（Step 3R-4.2） |
| **Step 3R-3.3C-C-C execution glue design**（17 节、549 行） | ✅ **已 merge** | commit `0bf9151` |
| **本 checkpoint**（固定 glue 目标 / CLI / execution flow / DB guard / final-test guard / output policy / acceptance / no-go / 允许下一步 / 禁止事项 / 边界） | ⏳ **本文**（未 commit） | — |
| Step 3R-3.3C-C-C execution glue **implementation**（新增脚本 + focused tests） | ❌ 未启动 | — |
| **single real validation run** | ❌ 未运行 | — |
| Step 3R-3.3C real validation **result checkpoint** | ❌ 未启动 | — |

> **real W1-W4 validation 仍未运行**；execution glue script 仍未实现；本文只固化 design 状态。

## 2. 当前 main 状态

- `main` 最新 commit：`0bf9151`
- commit message：`docs(contract): Step 3R-3.3C-C-C execution glue design`
- 上游：`origin/main` 已同步（push 完成 `7f4d9b8..0bf9151  main -> main`）
- 本步骤已 merge 文件：
  - `tasks/step_3r3_3c_c_c_execution_glue_design.md`（17 节、549 行；execution glue design 边界）
- 本 checkpoint 文档（即本文件）尚未 commit；本轮只写文档、**不** commit / push。
- full pytest 基线维持 commit `65f8352` 时的 **2877 / 0 failed / 10 skipped**（本轮纯文档）。

| 项 | 是否触碰 |
|---|---|
| 改代码 | ❌ 否 |
| 改 service / candidate / adapter / helper / orchestrator / wrapper / provider | ❌ 否 |
| 改 DB schema | ❌ 否 |
| 写 DB | ❌ 否 |
| 跑 replay | ❌ 否 |
| 跑 real validation | ❌ 否 |
| 跑 prepare-only smoke | ❌ 否 |
| 创建 regime_validation report output | ❌ 否 |
| 接 yfinance / 网络 | ❌ 否 |
| 接 trading API | ❌ 否 |
| 触碰 2026 final-test range | ❌ 否 |
| add `logs/regime_validation/` / W4 / smoke / DB backup / `agent_loop.py` / `.claude/worktrees/` | ❌ 否 |

## 3. glue 目标

execution glue 是 v1 real W1-W4 validation 的 **唯一 one-shot 装配点**，串联已 merge 的 6 个组件按既定顺序运行**一次**真实 validation：

| 目标 | 要求 |
|---|---|
| 输入装配 | `build_real_validation_inputs(db_path, w4_jsonl_path, w4_manifest_path, final_test_cutoff)` → `real_validation_input_bundle.v1`（W1-W3=286 + W4=353，total=639 rows + W4 manifest dict + DB fingerprint） |
| provider 构造 | `build_real_regime_label_provider(avgo_csv_path, nvda_csv_path, soxx_csv_path, qqq_csv_path, final_test_cutoff)` → closure provider（4 csv 一次性 `pandas.read_csv` 加载） |
| 调用 orchestrator | `run_continuous_smoothing_validation(replay_rows=bundle["w1_w3_rows"]+bundle["w4_rows"], regime_label_provider=provider, w4_manifest=bundle["w4_manifest"], candidate_threshold=0.60, candidate_name="continuous_smoothing_v1", final_test_cutoff="2026-01-01", output_dir=<TS>, write_outputs=True)` |
| threshold | 显式 `candidate_threshold=0.60`（v1 seed） —— **不**扫、**不**调、**不**反推、**不**靠默认值 |
| 输出 | 4 文件本地 untracked：`replay_validation_records.json` / `regime_validation_report.json` / `regime_validation_summary.md` / `run_manifest.json` |
| DB | **不写**（read-only orchestrator + read-only provider + DB fingerprint before / after） |
| main | **不进** —— output_dir 在 `logs/regime_validation/`，全部 untracked |
| 2026 final-test range | **不触碰** —— wrapper 过滤 + provider refusal + orchestrator filter + adapter / helper / report 6 层 final-test guard |

execution glue **不是生产主链**；它是 diagnostic harness。通过 **explicit opt-in** flag 防止误触发：默认行为是 refuse + exit 2。

## 4. proposed script

| 项 | 内容 |
|---|---|
| 文件路径 | `scripts/run_real_continuous_smoothing_validation_execute.py` |
| 是否在本 checkpoint 新增 | ❌ 否（design + checkpoint only） |
| 何时新增 | 后续 Step 3R-3.3C-C-C **implementation** 步骤 |
| 是否生产主链 | ❌ 否 —— one-shot diagnostic wrapper |
| 是否默认拒绝执行 | ✅ 是 —— 必须显式 `--run-once-real-validation` |
| 是否允许覆盖 output | ❌ 否 —— output_dir 不存在；不提供 `--allow-overwrite` |
| 是否暴露 importable `main()` 给生产 | ❌ 否 —— 仅 CLI |
| 与现有 `scripts/run_real_continuous_smoothing_validation.py` 关系 | 不合并；wrapper 仅做 prepare-inputs；execute 是另一只脚本，避免 prepare-only 模式被绕过 |
| 与现有 `scripts/run_continuous_smoothing_validation.py` 关系 | 不合并；orchestrator 是 library；CLI 入口仅打印 refusal |

## 5. CLI design

### 5.1 完整参数表

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `--run-once-real-validation` | flag | ✅ | `False` | 不传 → exit 2 + refusal message。脚本唯一 opt-in。 |
| `--db-path` | str | ✅ | `avgo_agent.db` | sqlite W1-W3 来源；wrapper 内部 `mode=ro` URI |
| `--w4-jsonl` | str | ✅ | `logs/historical_training/three_system_w4_2024_08_2025_12/three_system_replay_results.jsonl` | W4 replay rows |
| `--w4-manifest` | str | ✅ | `logs/historical_training/three_system_w4_2024_08_2025_12/validation_ready_manifest.json` | W4 manifest dict |
| `--avgo-csv` | str | ✅ | `data/AVGO.csv` | provider 数据源 |
| `--nvda-csv` | str | ✅ | `data/NVDA.csv` | provider 数据源 |
| `--soxx-csv` | str | ✅ | `data/SOXX.csv` | provider 数据源 |
| `--qqq-csv` | str | ✅ | `data/QQQ.csv` | provider 数据源 |
| `--candidate-threshold` | float | ✅ | `0.60` | 显式 0.60；任何其它值 → refuse + exit 2 |
| `--final-test-cutoff` | str | ✅ | `2026-01-01` | 任何 ≠ `"2026-01-01"` 的 cutoff → refuse + exit 2 |
| `--output-dir` | str | ✅ | `logs/regime_validation/continuous_smoothing_v1_real_w1_w4_<TS>` | 必须不存在；`<TS>` = `YYYYMMDD_HHMMSS` |

### 5.2 拒绝执行行为

| 情况 | 行为 |
|---|---|
| `--run-once-real-validation` 缺失 | stderr 输出 refusal + `return 2` |
| `--run-once-real-validation` 出现，但任一必填参数缺失 | stderr 输出缺失参数列表 + `return 2` |
| `--candidate-threshold != 0.60` | stderr 输出 threshold lock + `return 2` |
| `--final-test-cutoff != "2026-01-01"` | stderr 输出 cutoff lock + `return 2` |
| `--output-dir` 已存在（dir 或 file） | stderr 输出 + `return 2` |
| 任一 4 csv 不存在 / 任一字段缺 | provider 工厂抛 `FileNotFoundError` / `ValueError`；脚本 catch + `return 2` |
| 任一 W1-W3 / W4 路径不存在 / W4 manifest 解析 fail | wrapper 抛；脚本 catch + `return 2` |

### 5.3 不提供的 flag

为避免 acceptance / final-test guard 被绕开，**不提供**：

- `--allow-overwrite`
- `--threshold-sweep`
- `--ignore-final-test-cutoff`
- `--skip-db-guard`
- `--write-db`
- `--connect-protection-layer`
- `--enable-hard`
- `--enable-forced`
- `--allow-network`
- `--allow-yfinance`
- `--silent-default-threshold`
- 任何允许 silent override 的 flag

## 6. execution flow（10 步）

| # | 步骤 | 责任 | 失败行为 |
|---|---|---|---|
| 1 | **preflight print（only）** | print 当前 commit hash、`git status -uno`、Python version、`pandas` 版本 —— **只打印，不读 / 不改 / 不强制 clean tree**；用作 result checkpoint 的 audit 元数据 | print；不影响后续步骤 |
| 2 | **DB fingerprint (before)** | 调 `get_db_fingerprint(db_path)`；若 `data/market_data.db` 存在则对其也算一份；两份独立保存 | 异常 → exit 2 |
| 3 | **backup count (before)** | `pathlib.Path("avgo_agent.db.backup_*")` glob 计数；保存 `count_before` | 异常 → exit 2 |
| 4 | **build input bundle** | `bundle = build_real_validation_inputs(db_path=..., w4_jsonl_path=..., w4_manifest_path=..., final_test_cutoff="2026-01-01", symbol="AVGO")` | 抛异常 → exit 2 |
| 5 | **build real provider** | `provider = build_real_regime_label_provider(avgo_csv_path=..., nvda_csv_path=..., soxx_csv_path=..., qqq_csv_path=..., final_test_cutoff="2026-01-01")` | 抛 `FileNotFoundError` / `ValueError` → exit 2 |
| 6 | **call orchestrator** | `result = run_continuous_smoothing_validation(replay_rows=bundle["w1_w3_rows"]+bundle["w4_rows"], regime_label_provider=provider, w4_manifest=bundle["w4_manifest"], candidate_threshold=0.60, candidate_name="continuous_smoothing_v1", final_test_cutoff="2026-01-01", output_dir=<output_dir>, write_outputs=True)` | 抛异常 → exit 2 |
| 7 | **validate 4 output files** | 验证 `output_dir` 下存在：`replay_validation_records.json` / `regime_validation_report.json` / `regime_validation_summary.md` / `run_manifest.json`；任一缺 → exit 2 + 错误信息 | 缺失 → exit 2 |
| 8 | **DB fingerprint (after) + assert** | 再次 `get_db_fingerprint(db_path)`；`assert_db_unchanged(before, after)`；对 `data/market_data.db` 同步比较；任一 mismatch → exit 2（hard stop） | mismatch → exit 2 |
| 9 | **backup count (after)** | 再次 glob；`count_after != count_before` → exit 2 | mismatch → exit 2 |
| 10 | **print final summary** | print：commit hash / records_loaded / records_adapted / per-window 计数 / `report_status` / `worst_window` / `gate_status` / `final_test_touched` / DB fingerprint diff / backup diff / output_dir 路径 / 4 文件大小；**只 print，不写 DB、不写额外文件** | n/a |

注意：

- 步骤 6 内部已经在 orchestrator 中执行 final-test filter；execution glue **不重复**这层逻辑。
- 步骤 7 / 8 的顺序：先验文件存在，再验 DB unchanged。任一失败 → run invalid。
- 整个 flow 不写 DB；orchestrator 通过 candidate / adapter / helper 调用，全部已锁 read-only。
- 不**自动**进入 result checkpoint 写入；result checkpoint 是后续步骤，由人工触发。

## 7. in-memory data flow

```
                ┌──────────────────────────────┐
DB (W1-W3) ───► │ build_real_validation_inputs │
W4 jsonl    ──► │   (read-only loader,         │
W4 manifest ──► │    final-test filter)        │
                └──────────────┬───────────────┘
                               │
                               ▼
                  bundle: real_validation_input_bundle.v1
                  - w1_w3_rows (286)
                  - w4_rows    (353)
                  - w4_manifest dict
                  - db_fingerprint, final_test_cutoff
                               │
                               ▼
4 OHLC csv ───► build_real_regime_label_provider
                               │
                               ▼
                  provider: Callable[[as_of_date, row?], regime_labels.v1]
                               │
                               ▼
       ┌──────────────────────────────────────────┐
       │ run_continuous_smoothing_validation(...) │
       └──────────────────────────────────────────┘
        │
        │ for each row in (w1_w3_rows + w4_rows):
        │   - extract analysis_date
        │   - if analysis_date >= cutoff → skip + final_test_touched=True
        │   - else: provider(analysis_date) → regime_labels.v1
        │           → build_continuous_smoothing_candidate(...)
        │           → enriched row (+ candidate, labels.labels)
        │
        ▼
  enriched_rows (≤ 639)
        │
        ▼
  build_replay_validation_records(..., w4_manifest=bundle.w4_manifest)
        │
        ▼
  records_payload: replay_validation_records.v1
        │
        ▼
  build_regime_validation_report(...)
        │
        ▼
  report: regime_validation_report.v1
        │
        ▼
  run_manifest: regime_validation_run_manifest.v1
        │
        ▼
  4 output files (untracked):
    replay_validation_records.json
    regime_validation_report.json
    regime_validation_summary.md
    run_manifest.json
```

要点：

- bundle 由 wrapper 装配；execution glue **不**重新读取 DB / W4 jsonl。
- provider 的 `row` 参数被 real provider **deliberately ignored**（`services/real_regime_label_provider.py:108`）。`row` 中的 W4 future-leak 字段（`pos20` / `five_state_projection` / `predict_result_json` / `direction_correct` / `actual_state` / `actual_close_change`）**不**被消费。
- candidate / adapter / helper 全部在 `run_continuous_smoothing_validation` 内调用；execution glue **不**重新调用。
- 没有 sqlite 写、没有 file overwrite、没有 logs append（除 4 output files 之外）。

## 8. DB guard

> 真实 run 的最重要 invariant：DB **byte-for-byte 不变**。

### 8.1 三组 fingerprint

| # | 对象 | 来源 |
|---|---|---|
| 1 | `avgo_agent.db` mtime_ns + size_bytes | `get_db_fingerprint(args.db_path)`（已 merge） |
| 2 | `data/market_data.db` mtime_ns + size_bytes（若存在） | `get_db_fingerprint("data/market_data.db")` —— optional |
| 3 | `avgo_agent.db.backup_*` glob count | `len(list(Path(".").glob("avgo_agent.db.backup_*")))` |

### 8.2 检查时机

- **Before** （execution flow §6 step 2 / step 3）
- **After** （execution flow §6 step 8 / step 9）

### 8.3 失败行为

| 变化 | 行为 |
|---|---|
| `avgo_agent.db` mtime_ns 变化 | `RuntimeError("db_modified:mtime_ns_changed:...")` → exit 2 |
| `avgo_agent.db` size_bytes 变化 | `RuntimeError("db_modified:size_bytes_changed:...")` → exit 2 |
| `data/market_data.db` mtime_ns / size_bytes 变化 | execution glue 自抛 → exit 2 |
| backup count 变化 | execution glue 自抛 → exit 2 |
| 任一 fingerprint 异常 | exit 2 |

### 8.4 forbidden imports（execution glue + provider 共同遵守）

| 类别 | 模块 |
|---|---|
| DB 写 | `services.prediction_store`（写路径） |
| 结果写 | `services.outcome_capture`（写路径） |
| 网络 | `yfinance` / `requests` / `urllib` / `urllib3` / 任何 HTTP 客户端 |
| production 链 | `predict` / `scanner` / `streamlit` / `app` |
| trading | `longbridge` / `broker` / `paper_trade` / 任何 trading API |
| sqlite 写 | `sqlite3.connect(...)`（写路径） |

### 8.5 调用边界

- execution glue 自身 **不**直接 `import sqlite3`；DB 仅通过 wrapper 接触。
- wrapper `_open_readonly` 使用 `mode=ro` URI（`scripts/run_real_continuous_smoothing_validation.py:123`）—— 唯一允许的 sqlite 入口。
- provider **不**接 DB —— 仅 4 csv（已 audit）。
- orchestrator / candidate / adapter / helper **不**接 DB（已 isolation tested）。

任一层试图绕过 → run invalid + 后续 result checkpoint 必须记录违规。

## 9. final-test guard

cutoff = `"2026-01-01"`（**硬编码 lock**；CLI 默认值；非默认值 → exit 2）。

### 9.1 6 层 hard stop

| # | 层 | 责任 | 来源 |
|---|---|---|---|
| 1 | wrapper DB SQL filter | `analysis_date < cutoff` AND `prediction_for_date < cutoff` AND `prediction_for_date > analysis_date` | `scripts/run_real_continuous_smoothing_validation.py:163-178` |
| 2 | wrapper W4 jsonl filter | `as_of_date < cutoff` AND `prediction_for_date < cutoff` | `scripts/run_real_continuous_smoothing_validation.py:226-230` |
| 3 | orchestrator row filter | `analysis_date >= cutoff` → skip + `final_test_touched=True` | `scripts/run_continuous_smoothing_validation.py:236-241` |
| 4 | provider refusal | `as_of_date >= cutoff` → builder 返回 `final_test_refusal=True` + 全部 unknown labels | `services/real_regime_label_provider.py:104-117` + builder |
| 5 | candidate refusal | `continuous_smoothing_candidate.v1.final_test_refusal=true` 透传 | `services/continuous_smoothing_candidate.py` |
| 6 | adapter / helper / report refusal | `replay_validation_records.v1.final_test_refusal` / `regime_validation_report.v1.final_test_refusal` | `services/replay_validation_record_adapter.py` + `services/regime_validation_helper.py` |

### 9.2 run_manifest 与 report 字段约束

- `run_manifest.final_test_cutoff` **必须** = `"2026-01-01"`
- `run_manifest.final_test_touched` **必须** = `false`
- `report.final_test_refusal` **必须** = `false`
- 任一为 `true` → run invalid

### 9.3 execution glue 自身义务

- execution glue **不**自行 enrich row（不增 / 不改字段）。
- execution glue **不**对 cutoff 做 silent override —— `--final-test-cutoff != "2026-01-01"` → exit 2。
- execution glue **不**消费 csv 中 `Date >= cutoff` 行（builder anti-lookahead 自动过滤）。
- 即便 csv 含 2026 行，也不会被强制读取；额外保险：execution glue 在 print 阶段记录 `csv 中 >= cutoff 行计数（only meta；不消费）`。

## 10. threshold policy

| 项 | 值 | 说明 |
|---|---|---|
| `candidate_threshold` | `0.60` | v1 design seed；锁定 |
| 是否 optimized | ❌ 否 | 未学；未 sweep |
| 是否允许扫 threshold | ❌ 否 | one-shot fixed；任何 sweep flag → 不实现 |
| 是否允许 retry with 不同 value | ❌ 否 | 单次 run；fail / pass 都不重试 |
| 是否 fail 时调参 | ❌ 否 | fail → 回 candidate / threshold design 重设 |
| 是否 pass 时启 production | ❌ 否 | pass 仅允许 review；不自动启 hard / Gate 5 / Gate 6 |
| SEED coefficients（continuous_smoothing v1 模块常量） | ❌ 不动 | 仅常量；不通过 CLI / env override |
| 6 metric / 7 gate threshold | ❌ 不动 | 3R-4 protocol 锁定 |
| 任何 sweep 触发方式 | ❌ 不实现 | 单独 launch review；不在 3R-3.3C-C-C 范围 |

execution glue 必须**显式**传 `candidate_threshold=0.60`；不允许 silent default override。

## 11. output policy

### 11.1 output_dir 规则

| 项 | 状态 |
|---|---|
| `output_dir` 必须**不存在** | ✅ —— orchestrator 抛 `FileExistsError` |
| 不提供 `--allow-overwrite` | ✅ —— 设计上不存在 |
| 不**进 main**（git 不 add） | ✅ —— 全部 untracked |
| 不覆盖 W4 outputs（`logs/historical_training/three_system_w4_2024_08_2025_12/`） | ✅ |
| 不覆盖 B 阶段 smoke 目录 | ✅ —— smoke timestamp 不同 |
| 不写入 `logs/prediction_log.jsonl` | ✅ |
| 不 `git add` `logs/regime_validation/` 任何子目录 | ✅ |
| 可删除 / 可重跑 | ✅ —— 新 timestamp = 新目录；不复用旧目录 |

### 11.2 4 文件清单

```
logs/regime_validation/continuous_smoothing_v1_real_w1_w4_<TS>/
├── replay_validation_records.json          # replay_validation_records.v1
├── regime_validation_report.json           # regime_validation_report.v1
├── regime_validation_summary.md            # human-readable
└── run_manifest.json                       # regime_validation_run_manifest.v1
```

### 11.3 文件内容来源

| 文件 | 来源 | schema |
|---|---|---|
| `replay_validation_records.json` | adapter `build_replay_validation_records(...)` 输出 | `replay_validation_records.v1`（8 字段） |
| `regime_validation_report.json` | helper `build_regime_validation_report(...)` 输出 | `regime_validation_report.v1`（14 字段） |
| `regime_validation_summary.md` | orchestrator `_render_summary_md(...)` 渲染 | human readable；非 schema |
| `run_manifest.json` | orchestrator `_build_run_manifest(...)` 装配 | `regime_validation_run_manifest.v1`（12 字段） |

> 4 文件的写入由 orchestrator `_write_outputs_files(...)` 在 `output_dir.mkdir(parents=True, exist_ok=False)` 后完成（`scripts/run_continuous_smoothing_validation.py:170-196`）。execution glue **不重写**这部分。

### 11.4 处置规则

- raw output **留在本地**，untracked。
- result checkpoint 可**复制 `regime_validation_summary.md`** 内容到 markdown checkpoint；不直接 commit raw json。
- 任何把 `logs/regime_validation/<TS>/` 加入 git → 立即 revert + 在 result checkpoint 中记录违规。
- output 是否长期保留留待后续决策；不在本步骤范围。

## 12. acceptance criteria

> **first run 不要求 `report_status="pass"`**。acceptance 是 plumbing + 数据完整性级别。

### 12.1 必须满足（13 项）

| # | 标准 |
|---|---|
| 1 | 脚本以 exit 0 结束 **或** exit 2 + 明确 stderr 信息 |
| 2 | 若 exit 0：`output_dir` 存在；4 文件全 exist + 非空 |
| 3 | `records_loaded ≈ 639`（与 B1 prepare-only smoke total 一致）或低于 639 但有明确 skip warning |
| 4 | `records_adapted > 0` |
| 5 | W1 / W2 / W3 / W4 **均**有 records（per-window count > 0） |
| 6 | `regime_validation_report.v1` schema valid（14 字段齐） |
| 7 | `replay_validation_records.v1` schema valid（8 字段齐） |
| 8 | `regime_validation_run_manifest.v1` schema valid（12 字段齐） |
| 9 | `run_manifest.final_test_touched = false`；`report.final_test_refusal = false` |
| 10 | DB fingerprint **未变**（`avgo_agent.db` mtime_ns + size_bytes 全等）；`data/market_data.db`（若存在）也未变；`avgo_agent.db.backup_*` count 未变 |
| 11 | `output_dir` 与其内 4 文件全部 untracked |
| 12 | `worst_window` 在 W1/W2/W3/W4 之一；`gate_status` 7 gate 全 present |
| 13 | 没 threshold sweep / 没启 hard / 没改 required / 没接 trading / 没接 yfinance |

### 12.2 不要求

| 项 | 是否要求 |
|---|---|
| `report_status = "pass"` | ❌ 不要求 |
| 6 metric 全 pass | ❌ 不要求 |
| 7 gate 全 pass | ❌ 不要求 |
| candidate 通过 launch review | ❌ 不要求 |
| 自动启 3R-5 / 3R-6 | ❌ 永久禁止 |

## 13. legal fail outcomes

`report_status = "fail"` **是合法可接受的**；fail **不**触发调参 / 不触发 retry。可能 fail 的合法理由：

| 理由 | 是否合法 | 备注 |
|---|---|---|
| 某 fold `minimum_window_sample_size < 20`（candidate_triggered 计数低） | ✅ | helper `GATE_MIN_WINDOW_SAMPLE = 20` |
| 某 window `false_exclusion_rate > 0.10` | ✅ | candidate 在该 regime 误排不达预期 |
| 某 window `survival_case_preservation < 0.80` | ✅ | candidate 误伤 survival cases |
| `net_benefit < +0.05` | ✅ | candidate 未给出净收益 |
| `accuracy_delta_vs_baseline` 不达标 | ✅ | candidate 不优于 baseline |
| `cross_window_variance > 0.10` | ✅ | candidate 跨 window 行为不稳定 |
| `no_single_window_collapse` fail | ✅ | 单 window 严重崩溃 |

→ fail **不等于** wrapper / provider / orchestrator / candidate / adapter / helper bug；fail **不**触发：

- threshold 调整
- SEED 调整
- 7 gate threshold 调整
- 6 metric threshold 调整
- 自动 retry
- 自动启 3R-5 / 3R-6

错误（`error`）专门留给 schema / IO / final-test guard / DB guard 失败：

- 4 输出文件缺失 / schema 字段缺
- IO 异常
- DB fingerprint mismatch
- backup count 变化
- final_test_touched=true
- threshold lock 被绕过

pass 仅允许 **review**；不自动 promotion。

## 14. no-go rules

任意一项触发 → run abort + `report_status="error"` + result invalid + 不进入 result checkpoint：

| # | 条件 |
|---|---|
| 1 | 任一 input 文件缺失：`avgo_agent.db` / W4 jsonl / W4 manifest |
| 2 | 任一 market data csv 缺失：`data/AVGO.csv` / `NVDA.csv` / `SOXX.csv` / `QQQ.csv` |
| 3 | 任一 csv 字段不全（缺 `Date` / `Open` / `High` / `Low` / `Close`） |
| 4 | `output_dir` 已存在（dir 或 file） |
| 5 | DB fingerprint 在 run 期间变化（mtime_ns 或 size_bytes） |
| 6 | `avgo_agent.db.backup_*` count 在 run 期间变化 |
| 7 | `data/market_data.db` mtime_ns 或 size_bytes 在 run 期间变化（若存在） |
| 8 | 任一 row `as_of_date >= cutoff` 或 `prediction_for_date >= cutoff` 在 enrich 阶段被消费 |
| 9 | `run_manifest.final_test_touched = true` 或 `report.final_test_refusal = true` |
| 10 | `--candidate-threshold != 0.60` |
| 11 | `--final-test-cutoff != "2026-01-01"` |
| 12 | provider / glue / orchestrator 任一层 import forbidden module |
| 13 | provider / glue / orchestrator 任一层试图调 yfinance / requests / 任何 HTTP / 任何 trading API |
| 14 | hard / forced / required 任一被改 |
| 15 | report 任一 schema 字段缺（14 / 8 / 12 字段未满足） |
| 16 | 任一 fold（W1 / W2 / W3 / W4）records 为 0 且无明确 skip 解释 |
| 17 | execution glue 试图触发 `_PROTECTION_LAYER_CONNECTED` / Gate 5 / Gate 6 自动 pass |

## 15. 允许下一步

| # | 候选 | 状态 |
|---|---|---|
| 1 | **Step 3R-3.3C-C-C execution glue implementation** —— 新增 `scripts/run_real_continuous_smoothing_validation_execute.py` + focused tests | ✅ 允许（在本 checkpoint 进 main 后启动） |
| 2 | implementation 必须新增 script + focused tests | ✅ |
| 3 | tests 必须 mock provider / 用 small fixture | ✅ |
| 4 | tests **不**允许跑 639 real rows | ❌ 禁止 |
| 5 | tests **不**允许接触真实 4 csv 全量数据 | ❌ 禁止 |
| 6 | implementation **不**允许自动运行 real validation | ❌ 禁止 |
| 7 | single real run 仍要单独用户指令 | ✅ 必须 |
| 8 | wrapper / candidate / adapter / helper / orchestrator / provider / labels builder 现有行为 | ❌ 不改（仅只读调用） |
| 9 | hard / required upgrade / Gate 5 / Gate 6 / `_PROTECTION_LAYER_CONNECTED` | ❌ 永久封禁 |
| 10 | implementation checkpoint：`tasks/step_3r3_3c_c_c_execution_glue_implementation_checkpoint.md`（命名待定，与历次 checkpoint 风格一致） | ✅ 允许（implementation 完成后） |
| 11 | single real validation run | ✅ 允许（implementation checkpoint 进 main 后；单独用户指令触发） |
| 12 | result checkpoint：`tasks/step_3r3_3c_real_validation_result_checkpoint.md` | ✅ 允许（real run 完成后） |

## 16. 禁止事项

| # | 禁止 | 理由 |
|---|---|---|
| 1 | **不**直接跑 real validation | 必须先过 implementation + checkpoint |
| 2 | **不**新增 `.py` 文件（在本 checkpoint 范围内） | 本步骤是 checkpoint only |
| 3 | **不**新增测试（在本 checkpoint 范围内） | implementation 才写测试 |
| 4 | **不**写 DB | 全程 read-only |
| 5 | **不**改 DB schema | 全程 read-only |
| 6 | **不**跑 replay | replay 已在 W4 阶段冻结 |
| 7 | **不**跑 prepare-only smoke | B1 已固化 |
| 8 | **不**接 yfinance / requests / 任何网络 | provider 仅本地 csv |
| 9 | **不**扫 threshold | v1 seed 0.60 锁定 |
| 10 | **不**调 SEED coefficients | 模块常量 |
| 11 | **不**调 6 metric / 7 gate threshold | 3R-4 protocol 锁定 |
| 12 | **不**启 hard / forced / `anti_false_exclusion_triggered` | 三重 NO-GO |
| 13 | **不**改 04 / 05 / 07 required | Step 2G 全程边界 |
| 14 | **不**触碰 2026 final-test range | 6 层 hard stop |
| 15 | **不**接 trading（`longbridge` / `broker` / `paper_trade`） | 永久封禁 |
| 16 | **不**让 `_PROTECTION_LAYER_CONNECTED` 翻 True | 与 v1 / 3R-0 / 3R-4 一致 |
| 17 | **不**让 `hard_gate_status.protection_layer_connected` 自动 pass | 同上 |
| 18 | **不**改 `hard_exclusion_allowed` / `primary_blocker` 派生 | 同上 |
| 19 | **不**直接进入 formula（3R-5）/ simulator（3R-6） | 必须先过 result checkpoint + launch review |
| 20 | **不** commit validation outputs | `logs/regime_validation/` 全部 untracked |
| 21 | **不** commit 本 checkpoint 之外的产物 | 本轮不 commit / push |
| 22 | **不** import `services.prediction_store` / `services.outcome_capture` 写路径 / `yfinance` / `requests` / `predict` / `scanner` / `streamlit` 在 execution glue 任一层 | DB / 网络 / production isolation |
| 23 | **不**让 execution glue 通过 future-leaking 字段（`pos20` / `five_state_projection` / `predict_result_json` / `direction_correct` / `actual_state` / `actual_close_change`）反喂 candidate | anti-lookahead |
| 24 | **不**在 first real run fail 时调任何参数 | 与 §12 / §13 一致 |
| 25 | **不**触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*` | 历史防护 |
| 26 | **不**重跑 W1-W3 replay | DB 已足够（audit 已锁定） |
| 27 | **不**用 first real run 数据反推 candidate_threshold | 阈值变更必须经 launch review |
| 28 | **不**在脚本中提供 `--allow-overwrite` / `--threshold-sweep` / `--ignore-final-test-cutoff` / `--skip-db-guard` / `--write-db` / `--connect-protection-layer` / `--enable-hard` / `--enable-forced` / `--allow-network` 任一 flag | 设计上不存在 |
| 29 | **不**修改 wrapper / provider / orchestrator / candidate / adapter / helper 任一已 merge 模块 | 本步骤仅 checkpoint + 后续 implementation 也仅新增 1 脚本 |

## 17. 下一步建议

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **commit 本 checkpoint** | 把 §1-18 design 状态 / glue 目标 / CLI / execution flow / DB guard / final-test guard / output policy / acceptance / no-go / 允许下一步 / 禁止事项固化到 main | 本轮 / 下一轮 |
| 2 | **Step 3R-3.3C-C-C execution glue implementation** | 新增 `scripts/run_real_continuous_smoothing_validation_execute.py` + focused tests（mock provider / lock 校验 / DB guard mismatch / forbidden imports；**不**碰真实 4 csv / 不跑 639 rows） | 高（本 checkpoint 进 main 后） |
| 3 | **Step 3R-3.3C-C-C implementation checkpoint** | 状态归档 | 紧接其后 |
| 4 | **single real validation run**（用户单独指令触发） | execution glue 一次跑 + 4 文件本地 untracked + DB guard 双 fingerprint | 中（implementation checkpoint 进 main 后） |
| 5 | **Step 3R-3.3C result checkpoint** | 摘要 / report_status / per-window / fail_reason / DB guard verification 归档 | 中（real run 完成后） |
| 6 | **不推荐**直接 Step 3R-5 formula | 必须先过 result checkpoint + launch review | ❌ |
| 7 | **不推荐** Step 3R-6 simulator | 必须先过 3R-5 design | ❌ |
| 8 | **不推荐**让 first real run pass 自动启 hard / Gate 5 / Gate 6 | 与 3R-3.3 §11 一致 | ❌ |
| 9 | **不推荐**升级 04 required | Step 2G 全程边界 | ❌ |
| 10 | **不推荐**触碰 2026 final-test range | 永久封禁 | ❌ |
| 11 | **不推荐**让 `_PROTECTION_LAYER_CONNECTED` 翻 True | 与 v1 / 3R-0 / 3R-4 一致 | ❌ |
| 12 | **不推荐**重跑 W1-W3 replay | DB 已足够 | ❌ |
| 13 | **不推荐**用 first real run 数据反推 candidate_threshold | 阈值变更必须经 launch review | ❌ |

**关键判断**：顺序 = 本 checkpoint → C-C-C implementation + tests + checkpoint → single real validation run → result checkpoint → 3R-5 formula launch review → 3R-6 simulator。任何一步 fail → 整 candidate 报废，回到 design 层重新设计。

## 18. 严守边界

本文是**纯 checkpoint markdown**：

- ❌ 没改任何代码（`services/*` / `ui/*` / `tests/*` / `scripts/*` 全部未触碰）
- ❌ 没改 DB schema
- ❌ 没写 DB
- ❌ 没运行 replay
- ❌ 没运行 real validation
- ❌ 没运行 prepare-only smoke（B1 已固化）
- ❌ 没读 `data/AVGO.csv` / `NVDA.csv` / `SOXX.csv` / `QQQ.csv` 行（仅引用文件路径；audit 在 C-C-A 已固化）
- ❌ 没改 `run_predict` / `predict.py` / `scanner.py` / `prediction_store.py` / `app.py`
- ❌ 没改 `services/regime_features_builder.py` / `services/regime_labels_builder.py` / `services/regime_validation_helper.py` / `services/continuous_smoothing_candidate.py` / `services/replay_validation_record_adapter.py` / `services/historical_replay_training.py` / `services/real_regime_label_provider.py` / 任何 ui 模块 / 任何 builder
- ❌ 没改 `scripts/run_continuous_smoothing_validation.py` 或 `scripts/run_real_continuous_smoothing_validation.py`
- ❌ 没改 `tests/test_run_continuous_smoothing_validation.py` 或 `tests/test_run_real_continuous_smoothing_validation.py` 或 `tests/test_real_regime_label_provider.py`
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
- ❌ 没改 Step 3R-3.3 / 3R-3.3A / 3R-3.3B / 3R-3.3C / 3R-3.3C-A / 3R-3.3C-B / 3R-3.3C-B1 / 3R-3.3C-C / 3R-3.3C-C-A / 3R-3.3C-C-B / 3R-3.3C-C-C design 已 merge 文档 / 实施
- ❌ 没改 Step 2G-8D / 8D.1A / 8D.2 / 8D.3 / 8D.4 文档或代码
- ❌ 没把 W4 / smoke / `logs/regime_validation/` / `logs/prediction_log.jsonl` / DB backup / `agent_loop.py` / `.claude/worktrees/` 任一 commit 进 main
- ❌ 没创建任何新的 `logs/regime_validation/*` 子目录
- ❌ 没运行 `pytest`（本轮纯文档；测试基线维持 commit `65f8352` 时的 2877 / 0 failed / 10 skipped）
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*`
- ✅ 只新增 1 份 markdown checkpoint 文档（本文件）
