# Step 3R-3.3C-C-C — Execution Glue Design

> 本文是 **design only** —— 不改代码、不写 DB、不跑 replay、不跑 validation、不 commit / push、不接 trading API、不启 hard / forced、不改 required、不触碰 2026 final-test range、不 add `logs/regime_validation/` / W4 / smoke output / `logs/prediction_log.jsonl`、不处理 DB backup / stash / `.claude/worktrees/`。

## 1. 背景

| 组件 | 状态 | 来源 |
|---|---|---|
| real input wrapper（`build_real_validation_inputs(...)` + DB / W4 jsonl loader + DB fingerprint guard） | ✅ 已完成 | `scripts/run_real_continuous_smoothing_validation.py`（commit `23da6c9`） |
| real `regime_label_provider`（`build_real_regime_label_provider(...)`） | ✅ 已完成 | `services/real_regime_label_provider.py`（commit `65f8352`） |
| dry-run orchestrator（`run_continuous_smoothing_validation(...)`） | ✅ 已完成 | `scripts/run_continuous_smoothing_validation.py`（Step 3R-3.3A） |
| candidate 生成器（`build_continuous_smoothing_candidate(...)`） | ✅ 已完成 | `services/continuous_smoothing_candidate.py`（Step 3R-3.1） |
| replay validation record adapter | ✅ 已完成 | `services/replay_validation_record_adapter.py`（Step 3R-4.3A） |
| regime validation helper | ✅ 已完成 | `services/regime_validation_helper.py`（Step 3R-4.2） |
| W1-W3 (286) + W4 (353) = 639 真实输入 | ✅ 已确认 | Step 3R-3.3C-B1 prepare-only smoke checkpoint |
| 4 csv market data audit | ✅ 已通过 | Step 3R-3.3C-C-A market data source audit checkpoint（commit `4282058`） |
| **execution glue（串联 wrapper + provider + orchestrator 的 one-shot 脚本）** | ❌ **未实现** | 本文设计 |

本步骤的位置：

- 已 merge：`9720e0a` design / `b1d82ee` checkpoint（C-C） → `4282058` audit checkpoint（C-C-A） → `65f8352` provider impl / `7f4d9b8` provider checkpoint（C-C-B）。
- 本文：**3R-3.3C-C-C execution glue design**，仅 markdown，不动代码。
- 后续顺序：本文 commit → 本文 checkpoint → glue implementation + focused tests + checkpoint → single real validation run → result checkpoint → 3R-5 launch review。

> **本文只设计 execution glue 脚本的 CLI、execution flow、guard、output policy、acceptance、no-go、与 3R-5 / 3R-6 的隔离。本文不实现脚本，不新增任何 `.py` 文件。**

## 2. glue 目标

execution glue 是 v1 real W1-W4 validation 的 **唯一 one-shot 装配点**。它把已 merge 的 6 个组件按既定顺序串联，运行**一次**真实 validation：

| 目标 | 要求 |
|---|---|
| 输入装配 | 调 `build_real_validation_inputs(db_path, w4_jsonl_path, w4_manifest_path, final_test_cutoff)` 得到 `real_validation_input_bundle.v1`（639 rows + W4 manifest dict + DB fingerprint） |
| provider 构造 | 调 `build_real_regime_label_provider(avgo_csv_path, nvda_csv_path, soxx_csv_path, qqq_csv_path, final_test_cutoff)` 得到 closure provider |
| 调用 orchestrator | `run_continuous_smoothing_validation(replay_rows=bundle.w1_w3_rows + bundle.w4_rows, regime_label_provider=provider, w4_manifest=bundle.w4_manifest, candidate_threshold=0.60, candidate_name="continuous_smoothing_v1", final_test_cutoff="2026-01-01", output_dir=<TS>, write_outputs=True)` |
| threshold | 显式 `candidate_threshold=0.60`（v1 seed） —— **不**扫、**不**调、**不**反推、**不**靠默认值 |
| 输出 | 4 文件本地 untracked：`replay_validation_records.json` / `regime_validation_report.json` / `regime_validation_summary.md` / `run_manifest.json` |
| DB | **不写**（read-only orchestrator + read-only provider + DB fingerprint before / after） |
| main | **不进** —— output_dir 在 `logs/regime_validation/`，全部 untracked |
| 2026 | **不触碰** —— wrapper 已过滤 + provider refusal + orchestrator filter + adapter / helper / report 6 层 final-test guard |

execution glue **不是生产主链**。它是 diagnostic harness。它通过 **explicit opt-in** flag 防止误触发：默认行为是 refuse + exit 2。

## 3. proposed script

### 3.1 文件路径

```
scripts/run_real_continuous_smoothing_validation_execute.py
```

### 3.2 关键约束

| 项 | 说明 |
|---|---|
| 本文是否新增脚本 | ❌ 否（design only） |
| 何时新增 | 后续 Step 3R-3.3C-C-C **implementation** 步骤 |
| 是否生产主链 | ❌ 否 —— one-shot diagnostic wrapper |
| 是否默认拒绝执行 | ✅ 是 —— 必须显式 `--run-once-real-validation` |
| 是否允许覆盖 output | ❌ 否 —— output_dir 不存在；不提供 `--allow-overwrite` |
| 是否与现有 `scripts/run_real_continuous_smoothing_validation.py` 合并 | ❌ 否 —— wrapper 仅做 input prepare；execute 是另一只脚本，避免 prepare-only 模式被绕过 |
| 是否引入 CLI 之外的入口 | ❌ 否 —— 不暴露 importable `main()` 给生产 |
| 是否在 unit test 中跑 real run | ❌ 否 —— focused tests 用 fixture / 小 csv / mock，不读真实 4 csv，不跑 639 rows |

### 3.3 命名与文件分工对比

| 脚本 | 角色 | 是否在本文新增 |
|---|---|---|
| `scripts/run_real_continuous_smoothing_validation.py` | **prepare-inputs-only** wrapper（已 merge） | ❌ 不动 |
| `scripts/run_continuous_smoothing_validation.py` | dry-run orchestrator library（已 merge；CLI 入口仅打印拒绝信息） | ❌ 不动 |
| `scripts/run_real_continuous_smoothing_validation_execute.py` | **one-shot real run** glue（本文设计；后续 implementation 才新增） | ⏳ 设计中 |

## 4. CLI design

### 4.1 完整参数表

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `--run-once-real-validation` | flag | ✅ | `False` | 不传 → exit 2 + refusal message。这是脚本唯一的 opt-in。 |
| `--db-path` | str | ✅ | `avgo_agent.db` | sqlite W1-W3 来源；wrapper 内部用 `mode=ro` URI 打开 |
| `--w4-jsonl` | str | ✅ | `logs/historical_training/three_system_w4_2024_08_2025_12/three_system_replay_results.jsonl` | W4 replay rows |
| `--w4-manifest` | str | ✅ | `logs/historical_training/three_system_w4_2024_08_2025_12/validation_ready_manifest.json` | W4 manifest dict |
| `--avgo-csv` | str | ✅ | `data/AVGO.csv` | provider 数据源 |
| `--nvda-csv` | str | ✅ | `data/NVDA.csv` | provider 数据源 |
| `--soxx-csv` | str | ✅ | `data/SOXX.csv` | provider 数据源 |
| `--qqq-csv` | str | ✅ | `data/QQQ.csv` | provider 数据源 |
| `--candidate-threshold` | float | ✅ | `0.60` | 显式传 0.60；任何其它值 → refuse + exit 2（threshold 锁定见 §9） |
| `--final-test-cutoff` | str | ✅ | `2026-01-01` | 任何 `>= "2026-01-01"` 之外的 cutoff → refuse + exit 2 |
| `--output-dir` | str | ✅ | `logs/regime_validation/continuous_smoothing_v1_real_w1_w4_<TS>` | output_dir 必须不存在；`<TS>` 由调用方或脚本启动时生成（`YYYYMMDD_HHMMSS`） |

> 设计备注：`--candidate-threshold` 与 `--final-test-cutoff` 默认值与 v1 锁定一致；保留为 CLI 参数仅为审计可视性。脚本对这两个参数 **lock-check**：值不等于 v1 锁定值 → exit 2。

### 4.2 拒绝执行行为

| 情况 | 行为 |
|---|---|
| `--run-once-real-validation` 缺失 | stderr 输出 refusal + `return 2` |
| `--run-once-real-validation` 出现，但任一必填参数缺失 | stderr 输出缺失参数列表 + `return 2` |
| `--candidate-threshold != 0.60` | stderr 输出 threshold lock + `return 2` |
| `--final-test-cutoff != "2026-01-01"` | stderr 输出 cutoff lock + `return 2` |
| `--output-dir` 已存在（dir 或 file） | stderr 输出 + `return 2` —— **不**提供 `--allow-overwrite` |
| 任一 4 csv 不存在 / 任一字段缺 | provider 工厂抛 `FileNotFoundError` / `ValueError`；脚本 catch + `return 2` |
| 任一 W1-W3 / W4 路径不存在 / W4 manifest 解析 fail | wrapper 抛；脚本 catch + `return 2` |

### 4.3 不提供的 flag

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

## 5. execution flow

execution glue 必须**严格按 10 步执行**。任何步骤异常 → run abort + invalid。

| # | 步骤 | 责任 | 失败行为 |
|---|---|---|---|
| 1 | **git / environment preflight (print only)** | print 当前 commit hash、`git status -uno`、Python version、`pandas` 版本、`pytz`(若需) —— **只打印，不读 / 不改 / 不强制 clean tree**；用作 result checkpoint 的 audit 元数据 | 全部 print；不影响后续步骤 |
| 2 | **DB fingerprint (before)** | 调 `get_db_fingerprint(db_path)`；若 `data/market_data.db` 存在则对其也算一份；**两份各自独立**保存 | 异常 → exit 2 |
| 3 | **backup count (before)** | 用 `pathlib.Path("avgo_agent.db.backup_*")` glob 计数；保存 `count_before` | 异常 → exit 2 |
| 4 | **build input bundle** | `bundle = build_real_validation_inputs(db_path=..., w4_jsonl_path=..., w4_manifest_path=..., final_test_cutoff="2026-01-01", symbol="AVGO")` | 抛异常 → exit 2 |
| 5 | **build real provider** | `provider = build_real_regime_label_provider(avgo_csv_path=..., nvda_csv_path=..., soxx_csv_path=..., qqq_csv_path=..., final_test_cutoff="2026-01-01")` | 抛 `FileNotFoundError` / `ValueError` → exit 2 |
| 6 | **call orchestrator** | `result = run_continuous_smoothing_validation(replay_rows=bundle["w1_w3_rows"] + bundle["w4_rows"], regime_label_provider=provider, w4_manifest=bundle["w4_manifest"], candidate_threshold=0.60, candidate_name="continuous_smoothing_v1", final_test_cutoff="2026-01-01", output_dir=<output_dir>, write_outputs=True)` | 抛异常 → exit 2 |
| 7 | **validate 4 output files** | 验证 `output_dir` 下存在：`replay_validation_records.json` / `regime_validation_report.json` / `regime_validation_summary.md` / `run_manifest.json`；任一缺失 → exit 2 + 错误信息 | 缺失 → exit 2 |
| 8 | **DB fingerprint (after) + assert** | 再次 `get_db_fingerprint(db_path)`；`assert_db_unchanged(before, after)`；对 `data/market_data.db` 同步比较；任一 mismatch → exit 2（**这是 hard stop**） | mismatch → exit 2 |
| 9 | **backup count (after)** | 再次 glob `avgo_agent.db.backup_*` 计数；`count_after != count_before` → exit 2 | mismatch → exit 2 |
| 10 | **print final summary** | print：commit hash / records_loaded / records_adapted / per-window 计数 / `report_status` / `worst_window` / `gate_status` / `final_test_touched` / DB fingerprint diff / backup diff / output_dir 路径 / 4 文件大小；**只 print，不写 DB、不写额外文件** | n/a |

注意：

- 步骤 6 内部已经在 orchestrator 中执行 final-test filter（参见 §8）；execution glue **不重复**这层逻辑。
- 步骤 7 / 8 的顺序：先验文件存在，再验 DB unchanged。任一失败 → run invalid。
- 整个 flow 不写 DB；orchestrator 通过 candidate / adapter / helper 调用，全部已锁 read-only（参见 isolation tests）。
- 不**自动**进入 result checkpoint 写入；result checkpoint 是后续步骤，由人工触发。

## 6. in-memory data flow

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
        │           → build_continuous_smoothing_candidate(...) → candidate
        │           → enriched row with candidate (+ labels.labels)
        │
        ▼
  enriched_rows (≤ 639)
        │
        ▼
  build_replay_validation_records(enriched_rows, candidate_threshold=0.60,
                                  candidate_name=..., final_test_cutoff=...,
                                  require_w4_manifest=True,
                                  w4_manifest=bundle.w4_manifest)
        │
        ▼
  records_payload: replay_validation_records.v1
        │
        ▼
  build_regime_validation_report(records_payload.records,
                                 candidate_name=..., candidate_kind="smoothing",
                                 final_test_cutoff=...,
                                 require_w4_manifest=False, w4_manifest_path=None)
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
- provider 的 `row` 参数被 real provider **deliberately ignored**（见 `services/real_regime_label_provider.py:108`）。`row` 中的 W4 future-leak 字段（`pos20` / `five_state_projection` / `predict_result_json` / `direction_correct` / `actual_state` / `actual_close_change`）**不**被消费。
- candidate / adapter / helper 全部在 `run_continuous_smoothing_validation` 内调用；execution glue **不**重新调用。
- 没有 sqlite 写、没有 file overwrite、没有 logs append（除 4 output files 之外）。

## 7. DB guard

> 这是 **真实 run 的最重要 invariant**：DB 必须 byte-for-byte 不变。

### 7.1 fingerprint 来源

execution glue 维护 **三组 fingerprint**：

| # | 对象 | 来源 |
|---|---|---|
| 1 | `avgo_agent.db` mtime_ns + size_bytes | `get_db_fingerprint(args.db_path)`（已 merge） |
| 2 | `data/market_data.db` mtime_ns + size_bytes（若存在） | `get_db_fingerprint("data/market_data.db")` —— optional；不存在则记录 `exists=False` |
| 3 | `avgo_agent.db.backup_*` glob count | `len(list(Path(".").glob("avgo_agent.db.backup_*")))` |

### 7.2 检查时机

- **Before** （execution flow §5 step 2 / step 3）
- **After** （execution flow §5 step 8 / step 9）

### 7.3 失败行为

| 变化 | 行为 |
|---|---|
| `avgo_agent.db` mtime_ns 变化 | `RuntimeError("db_modified:mtime_ns_changed:...")` → exit 2 |
| `avgo_agent.db` size_bytes 变化 | `RuntimeError("db_modified:size_bytes_changed:...")` → exit 2 |
| `data/market_data.db` mtime_ns / size_bytes 变化 | execution glue 自抛 → exit 2 |
| backup count 变化 | execution glue 自抛 → exit 2 |
| 任一 fingerprint 异常（FS race / permission） | exit 2 |

### 7.4 forbidden imports（execution glue + provider 共同遵守）

| 类别 | 模块 |
|---|---|
| DB 写 | `services.prediction_store`（写路径） |
| 结果写 | `services.outcome_capture`（写路径） |
| 网络 | `yfinance` / `requests` / `urllib` / `urllib3` / 任何 HTTP 客户端 |
| production 链 | `predict` / `scanner` / `streamlit` / `app` |
| trading | `longbridge` / `broker` / `paper_trade` / 任何 trading API |
| sqlite 写 | `sqlite3.connect(...)`（写路径；wrapper 已用 `mode=ro` URI） |

> wrapper 的 `_open_readonly` 使用 `mode=ro` URI，是 **唯一允许的** sqlite 入口（见 `scripts/run_real_continuous_smoothing_validation.py:123`）。

### 7.5 调用边界

- execution glue 自身：**不**直接 `import sqlite3`；DB 仅通过 wrapper 接触。
- provider：**不**接 DB —— 仅 4 csv（已 audit）。
- orchestrator：**不**接 DB（已 isolation tested）。
- candidate / adapter / helper：**不**接 DB（已 isolation tested）。

任一层试图绕过这一边界 → run invalid + 后续 result checkpoint 必须记录违规。

## 8. final-test guard

cutoff = `"2026-01-01"`（**硬编码 lock**；CLI 默认值；非默认值 → exit 2）。

### 8.1 6 层 hard stop

| # | 层 | 责任 | 来源 |
|---|---|---|---|
| 1 | wrapper DB SQL filter | `analysis_date < cutoff` AND `prediction_for_date < cutoff` AND `prediction_for_date > analysis_date` | `scripts/run_real_continuous_smoothing_validation.py:163-178` |
| 2 | wrapper W4 jsonl filter | `as_of_date < cutoff` AND `prediction_for_date < cutoff` | `scripts/run_real_continuous_smoothing_validation.py:226-230` |
| 3 | orchestrator row filter | `analysis_date >= cutoff` → skip + `final_test_touched=True` | `scripts/run_continuous_smoothing_validation.py:236-241` |
| 4 | provider refusal | `as_of_date >= cutoff` → builder 返回 `final_test_refusal=True` + 全部 unknown labels | `services/real_regime_label_provider.py:104-117` + builder |
| 5 | candidate refusal | `continuous_smoothing_candidate.v1.final_test_refusal=true` 透传 | `services/continuous_smoothing_candidate.py` |
| 6 | adapter / helper / report refusal | `replay_validation_records.v1.final_test_refusal` / `regime_validation_report.v1.final_test_refusal` | `services/replay_validation_record_adapter.py` + `services/regime_validation_helper.py` |

### 8.2 run_manifest 与 report 字段约束

- `run_manifest.final_test_cutoff` **必须** = `"2026-01-01"`
- `run_manifest.final_test_touched` **必须** = `false`
- `report.final_test_refusal` **必须** = `false`
- 任一为 `true` → run invalid，**不**作为后续 design 依据

### 8.3 execution glue 自身义务

- execution glue **不**自行 enrich row（不增 / 不改字段）。
- execution glue **不**对 cutoff 做 silent override —— `--final-test-cutoff != "2026-01-01"` → exit 2。
- execution glue **不**消费 csv 中 `Date >= cutoff` 行（builder 内部 anti-lookahead 自动过滤）。
- 即便 csv 含 2026 行，也不会被强制读取；额外保险：execution glue 在 print 阶段记录 `csv 中 >= cutoff 行计数（only meta；不消费）`。

## 9. threshold policy

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

## 10. output policy

### 10.1 output_dir 规则

| 项 | 状态 |
|---|---|
| `output_dir` 必须**不存在** | ✅ —— orchestrator 抛 `FileExistsError` |
| 不提供 `--allow-overwrite` | ✅ —— 设计上不存在 |
| 不**进 main**（git 不 add） | ✅ —— 全部 untracked；`logs/regime_validation/` 已 gitignore |
| 不覆盖 W4 outputs | ✅ —— `logs/historical_training/three_system_w4_2024_08_2025_12/` 不接触 |
| 不覆盖 B 阶段 smoke 目录 | ✅ —— smoke 目录 timestamp 不同 |
| 不写入 `logs/prediction_log.jsonl` | ✅ |
| 不 `git add` `logs/regime_validation/` 任何子目录 | ✅ |
| 可删除 / 可重跑 | ✅ —— 新 timestamp = 新目录；不复用旧目录 |

### 10.2 4 文件清单

```
logs/regime_validation/continuous_smoothing_v1_real_w1_w4_<TS>/
├── replay_validation_records.json          # replay_validation_records.v1
├── regime_validation_report.json           # regime_validation_report.v1
├── regime_validation_summary.md            # human-readable
└── run_manifest.json                       # regime_validation_run_manifest.v1
```

### 10.3 文件内容来源

| 文件 | 来源 | schema |
|---|---|---|
| `replay_validation_records.json` | adapter `build_replay_validation_records(...)` 输出 | `replay_validation_records.v1`（8 字段） |
| `regime_validation_report.json` | helper `build_regime_validation_report(...)` 输出 | `regime_validation_report.v1`（14 字段） |
| `regime_validation_summary.md` | orchestrator `_render_summary_md(...)` 渲染 | human readable；非 schema |
| `run_manifest.json` | orchestrator `_build_run_manifest(...)` 装配 | `regime_validation_run_manifest.v1`（12 字段） |

> 这 4 文件的写入由 orchestrator `_write_outputs_files(...)` 在 `output_dir.mkdir(parents=True, exist_ok=False)` 后完成（参见 `scripts/run_continuous_smoothing_validation.py:170-196`）。execution glue **不重写**这部分。

### 10.4 处置规则

- raw output 默认**留在本地**，untracked。
- result checkpoint 可**复制 `regime_validation_summary.md`** 内容到 markdown checkpoint；不直接 commit raw json。
- 任何把 `logs/regime_validation/<TS>/` 加入 git → 立即 revert + 在 result checkpoint 中记录违规。
- output 是否长期保留留待后续决策；不在本步骤范围。

## 11. acceptance criteria

> **first run 不要求 `report_status="pass"`**。acceptance 是 plumbing + 数据完整性级别。

### 11.1 必须满足（13 项）

| # | 标准 |
|---|---|
| 1 | 脚本以 exit 0 结束 **或**以受控错误（exit 2）+ 明确 stderr 信息结束 |
| 2 | 若 exit 0：`output_dir` 存在；4 文件全 exist + 非空 |
| 3 | `records_loaded ≈ 639`（与 B1 prepare-only smoke total 一致）或低于 639 但有明确 skip warning |
| 4 | `records_adapted > 0` |
| 5 | W1 / W2 / W3 / W4 **均**有 records（per-window count > 0） |
| 6 | `regime_validation_report.v1` schema valid（14 字段齐） |
| 7 | `replay_validation_records.v1` schema valid（8 字段齐） |
| 8 | `regime_validation_run_manifest.v1` schema valid（12 字段齐） |
| 9 | `run_manifest.final_test_touched = false`；`report.final_test_refusal = false` |
| 10 | DB fingerprint **未变**（`avgo_agent.db` mtime_ns + size_bytes 全等）；`data/market_data.db`（若存在）也未变；`avgo_agent.db.backup_*` count 未变 |
| 11 | `output_dir` 与其内 4 文件全部 untracked（`git status` 无 tracked modified） |
| 12 | `worst_window` 在 W1/W2/W3/W4 之一；`gate_status` 7 gate 全 present |
| 13 | 没 threshold sweep / 没启 hard / 没改 required / 没接 trading / 没接 yfinance |

### 11.2 不要求（明确说明）

| 项 | 是否要求 |
|---|---|
| `report_status = "pass"` | ❌ 不要求 |
| 6 metric 全 pass | ❌ 不要求 |
| 7 gate 全 pass | ❌ 不要求 |
| candidate 通过 launch review | ❌ 不要求 |
| 自动启 3R-5 / 3R-6 | ❌ 永久禁止 |

## 12. legal fail outcomes

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
- IO 异常（write / read fail）
- DB fingerprint mismatch
- backup count 变化
- final_test_touched=true
- threshold lock 被绕过

## 13. no-go rules

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
| 12 | provider / glue / orchestrator 任一层 import forbidden module（§7.4） |
| 13 | provider / glue / orchestrator 任一层试图调 yfinance / requests / 任何 HTTP / 任何 trading API |
| 14 | hard / forced / required 任一被改 |
| 15 | report 任一 schema 字段缺（14 / 8 / 12 字段未满足） |
| 16 | 任一 fold（W1 / W2 / W3 / W4）records 为 0 且无明确 skip 解释 |
| 17 | execution glue 试图触发 `_PROTECTION_LAYER_CONNECTED` / Gate 5 / Gate 6 自动 pass |

## 14. implementation plan

| # | 步骤 | 是否本文范围 |
|---|---|---|
| 1 | commit 本 design doc（仅 markdown） | ⏳ 下轮（本轮不 commit） |
| 2 | 写 design checkpoint：`tasks/step_3r3_3c_c_c_execution_glue_design_checkpoint.md` | ❌ 后续步骤 |
| 3 | implementation：新增 `scripts/run_real_continuous_smoothing_validation_execute.py` + focused tests | ❌ 后续步骤 |
| 4 | implementation checkpoint：`tasks/step_3r3_3c_c_c_execution_glue_implementation_checkpoint.md` | ❌ 后续步骤 |
| 5 | single real run（生成 4 文件本地 untracked） | ❌ 后续步骤 |
| 6 | result checkpoint：`tasks/step_3r3_3c_real_validation_result_checkpoint.md` | ❌ 后续步骤 |

> **本文不实现脚本、不写测试、不跑 validation、不 commit、不 push、不进入下游 step**。

implementation 测试覆盖（在后续步骤里写，**不在本文范围**）：

- mock provider + mock wrapper 验证 execution glue 装配顺序
- threshold lock 绕过 → exit 2
- final_test_cutoff lock 绕过 → exit 2
- output_dir 已存在 → exit 2
- DB fingerprint mismatch → exit 2
- backup count mismatch → exit 2
- 缺 `--run-once-real-validation` → exit 2
- forbidden imports（与 provider / wrapper / orchestrator isolation tests 风格一致）
- focused unit test **不**触碰真实 4 csv / 不跑 639 rows / 不读真实 DB

## 15. 与 3R-5 / 3R-6 关系

| 关系 | 状态 |
|---|---|
| first real run pass → 自动启 3R-5 formula | ❌ 永久禁止 |
| first real run pass → 自动启 3R-6 simulator | ❌ 永久禁止 |
| first real run pass → 允许 review 进入 3R-5 design | ✅ 允许（仅 review） |
| first real run fail → 进入 3R-5 / 3R-6 | ❌ 禁止；fail 阻止 promotion |
| 3R-5 / 3R-6 启动条件 | 必须先：本 design merge → checkpoint → glue impl + checkpoint → single real run → result checkpoint → launch review |
| 任何 formula / simulator 触发 | 必须经独立 launch review；不在本步骤范围 |

> **pass ≠ 通行证**。pass 仅证明 plumbing 通了；3R-5 / 3R-6 仍需独立设计 + 评审。

## 16. 禁止事项

| # | 禁止 | 理由 |
|---|---|---|
| 1 | **不**直接跑 real validation in this design step | 本步骤是 design only |
| 2 | **不**新增 `.py` 文件 | 本步骤是 design only |
| 3 | **不**新增测试 | implementation 才写测试 |
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
| 21 | **不** commit 本设计步骤的产物（除本 markdown 外） | 本轮不 commit / push |
| 22 | **不** import `services.prediction_store` / `services.outcome_capture` 写路径 / `yfinance` / `requests` / `predict` / `scanner` / `streamlit` 在 execution glue 任一层 | DB / 网络 / production isolation |
| 23 | **不**让 execution glue 通过 future-leaking 字段（`pos20` / `five_state_projection` / `predict_result_json` / `direction_correct` / `actual_state` / `actual_close_change`）反喂 candidate | anti-lookahead；provider 已 ignore row |
| 24 | **不**在 first real run fail 时调任何参数 | 与 §11 / §12 一致 |
| 25 | **不**触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*` | 历史防护 |
| 26 | **不**重跑 W1-W3 replay | DB 已足够（audit 已锁定） |
| 27 | **不**用 first real run 数据反推 candidate_threshold | 阈值变更必须经 launch review |
| 28 | **不**在脚本中提供 `--allow-overwrite` / `--threshold-sweep` / `--ignore-final-test-cutoff` / `--skip-db-guard` / `--write-db` / `--connect-protection-layer` / `--enable-hard` / `--enable-forced` / `--allow-network` 任一 flag | 设计上不存在 |
| 29 | **不**修改 wrapper / provider / orchestrator / candidate / adapter / helper 任一已 merge 模块 | 本步骤仅 design + 后续 implementation 也仅新增 1 脚本 |

## 17. 严守边界

本文是**纯 design markdown**：

- ❌ 没改任何代码（`services/*` / `ui/*` / `tests/*` / `scripts/*` 全部未触碰）
- ❌ 没改 DB schema
- ❌ 没写 DB
- ❌ 没运行 replay
- ❌ 没运行 real validation
- ❌ 没运行 prepare-only smoke
- ❌ 没读 `data/AVGO.csv` / `NVDA.csv` / `SOXX.csv` / `QQQ.csv` 行（仅引用文件路径）
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
- ❌ 没改 Step 3R-3.3 / 3R-3.3A / 3R-3.3B / 3R-3.3C / 3R-3.3C-A / 3R-3.3C-B / 3R-3.3C-B1 / 3R-3.3C-C / 3R-3.3C-C-A / 3R-3.3C-C-B 已 merge 文档 / 实施
- ❌ 没改 Step 2G-8D / 8D.1A / 8D.2 / 8D.3 / 8D.4 文档或代码
- ❌ 没把 W4 / smoke / `logs/regime_validation/` / `logs/prediction_log.jsonl` / DB backup / `agent_loop.py` / `.claude/worktrees/` 任一 commit 进 main
- ❌ 没创建任何新的 `logs/regime_validation/*` 子目录
- ❌ 没运行 `pytest`（本轮纯文档；测试基线维持 commit `65f8352` 时的 2877 / 0 failed / 10 skipped）
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*`
- ✅ 只新增 1 份 markdown design 文档（本文件）
