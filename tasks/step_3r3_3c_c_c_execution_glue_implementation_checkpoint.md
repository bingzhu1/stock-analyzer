# Step 3R-3.3C-C-C — Execution Glue Implementation Checkpoint

> 本文是 **checkpoint markdown** —— 不改代码、不写 DB、不跑 replay、不跑 validation、不 commit / push、不接 trading API、不启 hard / forced、不改 required、不触碰 2026 final-test range、不 add `logs/regime_validation/` / W4 / smoke output / `logs/prediction_log.jsonl`、不处理 DB backup / stash / `.claude/worktrees/`。

## 1. 当前完成状态

| 组件 | 状态 | 来源 |
|---|---|---|
| real input wrapper（`build_real_validation_inputs(...)` + DB / W4 jsonl loader + DB fingerprint guard） | ✅ 已 merge | `scripts/run_real_continuous_smoothing_validation.py`（commit `23da6c9`） |
| real `regime_label_provider` 实现（`build_real_regime_label_provider(...)`） | ✅ 已 merge | `services/real_regime_label_provider.py`（commit `65f8352`） |
| dry-run orchestrator（`run_continuous_smoothing_validation(...)`） | ✅ 已 merge | `scripts/run_continuous_smoothing_validation.py`（Step 3R-3.3A） |
| candidate 生成器（`build_continuous_smoothing_candidate(...)`） | ✅ 已 merge | `services/continuous_smoothing_candidate.py`（Step 3R-3.1） |
| replay validation record adapter | ✅ 已 merge | `services/replay_validation_record_adapter.py`（Step 3R-4.3A） |
| regime validation helper | ✅ 已 merge | `services/regime_validation_helper.py`（Step 3R-4.2） |
| Step 3R-3.3C-C-C **execution glue design**（17 节、549 行） | ✅ 已 merge | commit `0bf9151` |
| Step 3R-3.3C-C-C **execution glue design checkpoint**（18 节、548 行） | ✅ 已 merge | commit `90c0b4e` |
| Step 3R-3.3C-C-C **execution glue implementation**（脚本 + 28 focused tests + §44 contract summary） | ✅ **已 merge** | commit `7812b10` |
| **本 checkpoint**（固定 script / CLI lock / DB guard / output verification / summary schema / tests / 限制 / 允许下一步 / 禁止事项 / 边界） | ⏳ **本文**（未 commit） | — |
| **single real validation run** | ❌ 未运行 | — |
| Step 3R-3.3C real validation **result checkpoint** | ❌ 未启动 | — |

> **real W1-W4 validation 仍未运行**；real `output_dir` 仍未创建；candidate pass / fail 仍未知；first real run 仍需用户单独指令。

## 2. 当前 main 状态

- `main` 最新 commit：`7812b10`
- commit message：`feat(diagnostics): add real validation execution glue`
- 上游：`origin/main` 已同步（push 完成 `90c0b4e..7812b10  main -> main`）
- 本步骤已 merge 文件：

| 路径 | 类型 | 行数 |
|---|---|---|
| `scripts/run_real_continuous_smoothing_validation_execute.py` | 新增 | 354 |
| `tests/test_run_real_continuous_smoothing_validation_execute.py` | 新增 | 871 |
| `tasks/step_1_contract_pipeline_summary.md` | 修改 | +181（追加 §44） |

测试基线：

| 命令 | 结果 |
|---|---|
| `pytest tests/test_run_real_continuous_smoothing_validation_execute.py -q` | **28 passed** |
| `pytest tests/test_run_real_continuous_smoothing_validation_execute.py tests/test_run_real_continuous_smoothing_validation.py tests/test_real_regime_label_provider.py tests/test_run_continuous_smoothing_validation.py -q` | **104 passed**（零回归） |
| `pytest -q`（全量） | **2905 passed / 10 skipped / 0 failed / 26 warnings / 94 subtests** |

测试基线累积：Step 3R-3.3C-C-B 终点 **2877** → Step 3R-3.3C-C-C 终点 **2905**（+28 净增；2877 基线零回归）。

| 项 | 是否触碰 |
|---|---|
| 改 service / candidate / adapter / helper / orchestrator / wrapper / provider | ❌ 否 |
| 改 DB schema | ❌ 否 |
| 写 DB | ❌ 否 |
| 跑 replay | ❌ 否 |
| 跑 real validation | ❌ 否 |
| 创建 regime_validation report output | ❌ 否 |
| 接 yfinance / 网络 | ❌ 否 |
| 接 trading API | ❌ 否 |
| 触碰 2026 final-test range | ❌ 否 |
| add `logs/regime_validation/` / W4 / smoke / DB backup / `agent_loop.py` / `.claude/worktrees/` / `logs/prediction_log.jsonl` | ❌ 否 |

## 3. script path

```
scripts/run_real_continuous_smoothing_validation_execute.py
```

定位：

| 项 | 状态 |
|---|---|
| one-shot diagnostic execution wrapper | ✅ |
| **不**是生产主链 | ✅（仅 CLI 入口；无 importable 给 production） |
| **不**是 Streamlit 路径 | ✅（不 import streamlit） |
| **不**是 trading 路径 | ✅（不 import longbridge / broker / paper_trade） |
| 必须显式 invoke | ✅（必须 `--run-once-real-validation`） |
| 默认行为是 refuse + exit 2 | ✅ |

## 4. public helpers

| 函数 | 签名 | 行为 |
|---|---|---|
| `get_backup_count` | `(pattern: str = "avgo_agent.db.backup_*") -> int` | 仅 glob cwd 计数；不读文件内容 |
| `assert_backup_count_unchanged` | `(before: int, after: int) -> None` | mismatch → `RuntimeError("db_backup_count_changed:before=...,after=...")` |
| `validate_execution_args` | `(args: argparse.Namespace) -> None` | run_once / threshold / cutoff / output_dir / 必填 path 全部 lock；mismatch → `ValueError(...)` 带稳定前缀 |
| `build_execution_summary` | kwargs-only → `dict` | 装配 `real_validation_execution_summary.v1`（12 字段） |
| `run_real_validation_execution` | `(args) -> dict` | 完整 10 步 execution flow；mock 友好 |
| `main` | `(argv=None) -> int` | CLI 入口；refusal → `return 2`；happy path → JSON summary + `return 0` |

模块常量：

- `SUMMARY_SCHEMA_VERSION = "real_validation_execution_summary.v1"`
- `LOCKED_CANDIDATE_THRESHOLD = 0.60`
- `LOCKED_FINAL_TEST_CUTOFF = "2026-01-01"`
- `LOCKED_CANDIDATE_NAME = "continuous_smoothing_v1"`
- `DEFAULT_BACKUP_PATTERN = "avgo_agent.db.backup_*"`
- `DEFAULT_MARKET_DATA_DB_PATH = "data/market_data.db"`
- `EXPECTED_OUTPUT_FILES = ("replay_validation_records.json", "regime_validation_report.json", "regime_validation_summary.md", "run_manifest.json")`

## 5. CLI lock

| 参数 | 默认 | lock 行为 |
|---|---|---|
| `--run-once-real-validation` | flag，默认 False | 不传 → `refuse_to_run:missing_explicit_opt_in:--run-once-real-validation is required` + exit 2 |
| `--candidate-threshold` | `0.60` | ≠ 0.60 → `refuse_to_run:candidate_threshold_locked:expected=0.6,got=...` + exit 2 |
| `--final-test-cutoff` | `"2026-01-01"` | ≠ `"2026-01-01"` → `refuse_to_run:final_test_cutoff_locked:expected="2026-01-01",got=...` + exit 2 |
| `--output-dir` | 必填 | 已存在 → `refuse_to_run:output_dir_exists:... must not exist; refuse to overwrite` + exit 2 |
| `--db-path` / `--w4-jsonl` / `--w4-manifest` / `--avgo-csv` / `--nvda-csv` / `--soxx-csv` / `--qqq-csv` / `--output-dir` | 必填 | 缺任一 → `refuse_to_run:missing_required_args:...` + exit 2 |

不存在的 flag（argparse 自动 SystemExit）：

- `--allow-overwrite`
- `--threshold-sweep`
- `--skip-db-guard`
- `--write-db`
- `--enable-hard`
- `--enable-forced`
- `--allow-network`
- `--ignore-final-test-cutoff`
- `--connect-protection-layer`

## 6. execution flow（11 步）

| # | 步骤 | 责任 | 失败行为 |
|---|---|---|---|
| 1 | **validate_execution_args(args)** | run_once / threshold / cutoff / output_dir / 必填 path 全部 lock | `ValueError(...)` → CLI catch + exit 2 |
| 2 | **DB fingerprint (before)** | `db_fp_before = get_db_fingerprint(args.db_path)` | 异常 → exit 2 |
| 3 | **market_data.db fingerprint (before)** | `market_fp_before = get_db_fingerprint("data/market_data.db") if exists` | 异常 → exit 2 |
| 4 | **backup count (before)** | `backup_before = get_backup_count("avgo_agent.db.backup_*")` | 异常 → exit 2 |
| 5 | **build input bundle** | `bundle = build_real_validation_inputs(db_path=..., w4_jsonl_path=..., w4_manifest_path=..., final_test_cutoff="2026-01-01")` | 抛异常 → exit 2 |
| 6 | **build real provider** | `provider = build_real_regime_label_provider(avgo_csv_path=..., nvda_csv_path=..., soxx_csv_path=..., qqq_csv_path=..., final_test_cutoff="2026-01-01")` | 抛 `FileNotFoundError` / `ValueError` → exit 2 |
| 7 | **call orchestrator** | `result = run_continuous_smoothing_validation(replay_rows=bundle["w1_w3_rows"]+bundle["w4_rows"], regime_label_provider=provider, w4_manifest=bundle["w4_manifest"], candidate_threshold=0.60, candidate_name="continuous_smoothing_v1", final_test_cutoff="2026-01-01", output_dir=args.output_dir, write_outputs=True)` | 抛异常 → exit 2 |
| 8 | **verify 4 output files** | `_verify_output_files(args.output_dir)` | 缺任一 → `RuntimeError("output_files_missing:[...] in <dir>")` → exit 2 |
| 9 | **DB fingerprint (after) + assert** | `db_fp_after = get_db_fingerprint(args.db_path)`；`assert_db_unchanged(db_fp_before, db_fp_after)`；market_data.db 同步比较 | mismatch → `RuntimeError("db_modified:...")` → exit 2 |
| 10 | **backup count (after) + assert** | `backup_after = get_backup_count(...)`；`assert_backup_count_unchanged(backup_before, backup_after)` | mismatch → `RuntimeError("db_backup_count_changed:...")` → exit 2 |
| 11 | **return summary** | `build_execution_summary(...)` → `real_validation_execution_summary.v1`（12 字段）；CLI 写 stdout JSON + `return 0` | n/a |

> 与 design / design checkpoint 的 10 步对齐；本 implementation 把 step 9 / 10 在代码中拆成两个 assert 调用，整体不变。

## 7. DB guard

### 7.1 三组 fingerprint

| # | 对象 | 来源 |
|---|---|---|
| 1 | `avgo_agent.db` mtime_ns + size_bytes | `get_db_fingerprint(args.db_path)`（wrapper 提供，commit `23da6c9`） |
| 2 | `data/market_data.db` mtime_ns + size_bytes（若存在） | 同上（额外 fingerprint） |
| 3 | `avgo_agent.db.backup_*` glob count | `get_backup_count(...)`（execution glue 自实现） |

### 7.2 检查时机

- **Before**：execution flow §6 step 2 / step 3 / step 4
- **After**：execution flow §6 step 9 / step 10

### 7.3 失败行为

| 变化 | 行为 |
|---|---|
| `avgo_agent.db` mtime_ns 变化 | `assert_db_unchanged` raises `RuntimeError("db_modified:mtime_ns_changed:...")` |
| `avgo_agent.db` size_bytes 变化 | `assert_db_unchanged` raises `RuntimeError("db_modified:size_bytes_changed:...")` |
| `data/market_data.db` mtime_ns / size_bytes 变化（若存在） | 同上 |
| `avgo_agent.db.backup_*` count 变化 | `assert_backup_count_unchanged` raises `RuntimeError("db_backup_count_changed:before=...,after=...")` |

任一异常 → execution glue 抛出，CLI catch 后输出 stderr `execution_failed:RuntimeError:<msg>` + `return 2`。

### 7.4 sqlite 隔离

- execution glue **不**直接 `import sqlite3`（isolation test `test_no_direct_sqlite3_import` 锁定）。
- execution glue **不**通过 `from sqlite3 import ...`（同上）。
- DB 接触**仅**通过 `scripts.run_real_continuous_smoothing_validation`（wrapper），后者使用 `sqlite3.connect(uri, uri=True)` + `mode=ro` URI（`scripts/run_real_continuous_smoothing_validation.py:123`）。
- provider **不**接 DB —— 仅本地 4 csv（已 audit）。
- orchestrator / candidate / adapter / helper **不**接 DB（已 isolation tested）。

## 8. output file verification

### 8.1 4 文件清单

```
logs/regime_validation/continuous_smoothing_v1_real_w1_w4_<TS>/
├── replay_validation_records.json          # replay_validation_records.v1
├── regime_validation_report.json           # regime_validation_report.v1
├── regime_validation_summary.md            # human-readable
└── run_manifest.json                       # regime_validation_run_manifest.v1
```

### 8.2 verify 逻辑

`_verify_output_files(output_dir)`：

- `output_dir` 必须 `is_dir()`，否则 `RuntimeError("output_dir_missing_after_run:<dir>")`。
- 4 文件 (`EXPECTED_OUTPUT_FILES`) 全部 exist；缺任一 → `RuntimeError("output_files_missing:[...] in <dir>")`。
- 返回 `list(EXPECTED_OUTPUT_FILES)` 给 `build_execution_summary`。

### 8.3 output_dir 约束

| 项 | 状态 |
|---|---|
| `output_dir` 必须**不存在** | ✅ —— `validate_execution_args` 提前拒（exit 2）+ orchestrator `_write_outputs_files(...)` 内部 `FileExistsError` 二重保险 |
| 不提供 `--allow-overwrite` | ✅ —— argparse 中不存在该 flag |
| 不进 main（git 不 add） | ✅ —— output 全 untracked；`logs/regime_validation/` 已 gitignore |
| 不覆盖 W4 outputs | ✅ —— output_dir 在 `logs/regime_validation/`，与 `logs/historical_training/three_system_w4_2024_08_2025_12/` 不交集 |
| 不写入 `logs/prediction_log.jsonl` | ✅ |
| 不 `git add` `logs/regime_validation/` | ✅ |
| 可删除 / 可重跑（新 timestamp = 新目录） | ✅ |

## 9. summary schema

`real_validation_execution_summary.v1`（12 字段）：

| 字段 | 类型 | 说明 |
|---|---|---|
| `schema_version` | str | `"real_validation_execution_summary.v1"` |
| `candidate_name` | str | `"continuous_smoothing_v1"`（lock） |
| `candidate_threshold` | float | `0.60`（lock） |
| `final_test_cutoff` | str | `"2026-01-01"`（lock） |
| `output_dir` | str | CLI 传入路径 |
| `records_loaded` | int | orchestrator 透传（≤ 639） |
| `records_adapted` | int | adapter 输出 records 计数 |
| `report_status` | str | `"pass"` / `"fail"` / `"error"` |
| `final_test_touched` | bool | run_manifest.final_test_touched 透传 |
| `db_unchanged` | bool | 抵达此处即 True（变化已抛） |
| `backup_count_unchanged` | bool | 抵达此处即 True（变化已抛） |
| `output_files` | list[str] | `list(EXPECTED_OUTPUT_FILES)` |

## 10. tests / no real run

| 项 | 状态 |
|---|---|
| `build_real_validation_inputs` mocked | ✅ —— `mock.patch.object(glue, "build_real_validation_inputs", side_effect=fake_inputs)` |
| `build_real_regime_label_provider` mocked | ✅ —— mock.patch.object + closure-only fake provider |
| `run_continuous_smoothing_validation` mocked | ✅ —— side_effect 写 4 fixture 文件到受控 tmp |
| 测试**不**读真实 4 csv | ✅ —— provider factory 本身被 mock，不进入 `_load_market_csv` |
| 测试**不**读真实 W4 jsonl | ✅ —— wrapper 被 mock，不进入 `load_w4_rows_from_jsonl` |
| 测试**不**跑 639 rows | ✅ —— mock 返回 `_bundle()` 仅 1 W1-W3 + 1 W4 = 2 rows |
| 测试**不**连真实 `avgo_agent.db` | ✅ —— fixture sqlite 文件在 `tmpdir / "avgo_agent.db"` 写 byte |
| 测试**不**触碰真实 backup 文件 | ✅ —— `os.chdir(tempfile.TemporaryDirectory())` 后 glob，受控 cwd |
| 测试**不**触碰真实 `data/market_data.db` | ✅ —— market_data 测试同样在受控 cwd 下伪造 |
| 测试**不** import production / trading / network 模块 | ✅ —— ast.walk + 字符串扫均通过 |

## 11. 测试覆盖

### 11.1 测试结果

| 命令 | 结果 |
|---|---|
| `pytest tests/test_run_real_continuous_smoothing_validation_execute.py -q` | **28 passed** |
| `pytest tests/test_run_real_continuous_smoothing_validation_execute.py tests/test_run_real_continuous_smoothing_validation.py tests/test_real_regime_label_provider.py tests/test_run_continuous_smoothing_validation.py -q` | **104 passed**（零回归） |
| `pytest -q`（全量） | **2905 passed / 10 skipped / 0 failed / 26 warnings / 94 subtests** |

测试基线累积：Step 3R-3.3C-C-B 终点 **2877** → Step 3R-3.3C-C-C 终点 **2905**（+28 净增；2877 基线零回归）。

### 11.2 覆盖矩阵（28 tests / 7 类）

| 测试类 | 数量 | 覆盖点 |
|---|---|---|
| `GetBackupCountTests` | 1 | glob cwd backup 计数 / 无关 backup 文件不匹配 |
| `AssertBackupCountUnchangedTests` | 2 | equal pass / mismatch raises |
| `ValidateExecutionArgsTests` | 7 | run_once flag 缺失 / threshold>lock / threshold<lock / cutoff != "2026-01-01"（3 例） / output_dir 已存在 / 缺必填 path（subTest 8 attrs） / happy path 不抛 |
| `BuildExecutionSummaryTests` | 1 | summary 12 字段 + schema_version + lock 透传 + output_files 列表 |
| `RunRealValidationExecutionHappyPathTests` | 2 | mocked 完整路径 + 4 文件 verify + summary 字段 + orchestrator kwargs lock 透传 + replay rows 拼接；输出文件缺 → RuntimeError |
| `GuardMismatchTests` | 4 | DB size mismatch / DB mtime mismatch / backup count mismatch / market_data.db mismatch（受控 cwd） |
| `CliTests` | 6 | 缺 run-once → exit 2 / threshold ≠ 0.60 → exit 2 / cutoff ≠ 2026-01-01 → exit 2 / output_dir 已存在 → exit 2 / forbidden flags（7 个）argparse SystemExit / mocked happy path → exit 0 + JSON summary |
| `IsolationTests` | 5 | 21 项 forbidden import / 没有直接 sqlite3 import / hard-required-trading 字符串 / threshold-sweep + override-flag 字符串 / lock 常量必须存在 |

### 11.3 isolation 锁定

| 锁定项 | 数量 |
|---|---|
| forbidden imports（ast.walk） | 21 |
| sqlite3 直接 import 字符串扫 | 2 (`import sqlite3`, `from sqlite3`) |
| hard / required / trading 字符串扫 | 11 |
| threshold-sweep + override-flag 字符串扫 | 16 |
| 锁常量字符串扫 | 2 (`LOCKED_CANDIDATE_THRESHOLD = 0.60`, `LOCKED_FINAL_TEST_CUTOFF = "2026-01-01"`) |

## 12. 当前限制

| 限制 | 状态 |
|---|---|
| real validation 仍未运行 | ❌ 未跑 |
| real `output_dir` 仍未创建（`logs/regime_validation/continuous_smoothing_v1_real_w1_w4_<TS>/`） | ❌ 未存在 |
| real `regime_validation_report.json` / `replay_validation_records.json` / `regime_validation_summary.md` / `run_manifest.json` | ❌ 未生成 |
| candidate `continuous_smoothing_v1` pass / fail | ❓ 未知 |
| 7 gate `gate_status` / `worst_window` / `fail_reason` | ❓ 未知 |
| W1 / W2 / W3 / W4 per-window count | ❓ 未知（B1 prepare-only smoke 已确认 input rows: W1-W3=286 + W4=353；adapted 计数仍未知） |
| first real run 仍需用户单独指令 | ✅ 必须 |
| pass → 自动启 hard / Gate 5 / Gate 6 / 3R-5 / 3R-6 | ❌ 永久禁止 |
| fail → 自动调 threshold / SEED | ❌ 永久禁止 |

## 13. 允许下一步

| # | 候选 | 状态 |
|---|---|---|
| 1 | **single real validation run** | ✅ 允许（在用户**单独**确认指令下启动） |
| 2 | 必须使用 script 的 explicit flag `--run-once-real-validation` | ✅ |
| 3 | 必须传 `--candidate-threshold 0.60`（CLI lock 拒非 0.60） | ✅ |
| 4 | 必须传 `--final-test-cutoff 2026-01-01`（CLI lock 拒其它） | ✅ |
| 5 | `--output-dir` 必须**新 timestamp**（如 `logs/regime_validation/continuous_smoothing_v1_real_w1_w4_YYYYMMDD_HHMMSS/`），且**不存在** | ✅ |
| 6 | run 前后必须记录 DB fingerprint（`avgo_agent.db` + `data/market_data.db` 若存在 + backup count） | ✅（execution glue 自动） |
| 7 | output 4 文件**不** commit；保持 untracked | ✅ |
| 8 | run 完毕后必须写 **result checkpoint**（`tasks/step_3r3_3c_real_validation_result_checkpoint.md` 或同类命名） | ✅ |
| 9 | wrapper / candidate / adapter / helper / orchestrator / provider / labels builder / execution glue 现有行为 | ❌ 不改（仅只读调用） |
| 10 | hard / required upgrade / Gate 5 / Gate 6 / `_PROTECTION_LAYER_CONNECTED` | ❌ 永久封禁 |

## 14. 禁止事项

| # | 禁止 | 理由 |
|---|---|---|
| 1 | **不**自动跑 real validation | 必须用户单独确认；本 checkpoint 不触发 run |
| 2 | **不**新增 `.py` 文件（在本 checkpoint 范围内） | 本步骤是 checkpoint only |
| 3 | **不**新增测试（在本 checkpoint 范围内） | 测试已在 implementation 步骤完成 |
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
| 22 | **不** import `services.prediction_store` / `services.outcome_capture` 写路径 / `yfinance` / `requests` / `predict` / `scanner` / `streamlit` 在 execution glue 任一层 | DB / 网络 / production isolation（21 项 ast.walk + 11 项字符串扫已锁定） |
| 23 | **不** `import sqlite3` 在 execution glue 自身 | wrapper `mode=ro` URI 是唯一允许的 sqlite 入口 |
| 24 | **不**让 execution glue 通过 future-leaking 字段（`pos20` / `five_state_projection` / `predict_result_json` / `direction_correct` / `actual_state` / `actual_close_change`）反喂 candidate | anti-lookahead；provider 已 ignore row |
| 25 | **不**在 first real run fail 时调任何参数 | 与 design §13 / checkpoint §13 一致 |
| 26 | **不**触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*` | 历史防护 |
| 27 | **不**重跑 W1-W3 replay | DB 已足够（audit 已锁定） |
| 28 | **不**用 first real run 数据反推 candidate_threshold | 阈值变更必须经 launch review |
| 29 | **不**修改 wrapper / provider / orchestrator / candidate / adapter / helper / execution glue 任一已 merge 模块 | 本步骤仅 checkpoint |

## 15. 下一步建议

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **commit 本 checkpoint** | 把 §1-16 implementation 状态 / script / CLI / DB guard / output verify / summary schema / tests / 限制 / 允许下一步 / 禁止事项固化到 main | 本轮 / 下一轮 |
| 2 | **single real validation run**（**用户单独确认指令触发**） | execution glue 一次跑：`scripts/run_real_continuous_smoothing_validation_execute.py --run-once-real-validation --db-path avgo_agent.db --w4-jsonl logs/historical_training/three_system_w4_2024_08_2025_12/three_system_replay_results.jsonl --w4-manifest logs/historical_training/three_system_w4_2024_08_2025_12/validation_ready_manifest.json --avgo-csv data/AVGO.csv --nvda-csv data/NVDA.csv --soxx-csv data/SOXX.csv --qqq-csv data/QQQ.csv --candidate-threshold 0.60 --final-test-cutoff 2026-01-01 --output-dir logs/regime_validation/continuous_smoothing_v1_real_w1_w4_<TS>` | 高（本 checkpoint 进 main 后；用户单独触发） |
| 3 | **Step 3R-3.3C real validation result checkpoint** | 摘要 / report_status / per-window / fail_reason / DB guard verification / output 4 文件结构（不 commit raw json，只 copy summary） | 中（real run 完成后） |
| 4 | 根据 result 决定是否进入 review；**不**直接进入 3R-5 / 3R-6 | pass 仅允许 review；fail 需回 candidate / threshold design 重设 | — |
| 5 | **不推荐**直接 Step 3R-5 formula | 必须先过 result checkpoint + launch review | ❌ |
| 6 | **不推荐** Step 3R-6 simulator | 必须先过 3R-5 design | ❌ |
| 7 | **不推荐**让 first real run pass 自动启 hard / Gate 5 / Gate 6 | 与 3R-3.3 §11 一致 | ❌ |
| 8 | **不推荐**升级 04 required | Step 2G 全程边界 | ❌ |
| 9 | **不推荐**触碰 2026 final-test range | 永久封禁 | ❌ |
| 10 | **不推荐**让 `_PROTECTION_LAYER_CONNECTED` 翻 True | 与 v1 / 3R-0 / 3R-4 一致 | ❌ |
| 11 | **不推荐**重跑 W1-W3 replay | DB 已足够 | ❌ |
| 12 | **不推荐**用 first real run 数据反推 candidate_threshold | 阈值变更必须经 launch review | ❌ |

**关键判断**：顺序 = 本 checkpoint → single real validation run（用户单独触发）→ result checkpoint → review 决定 → 3R-5 formula launch review → 3R-6 simulator。任何一步 fail → 整 candidate 报废，回到 design 层重新设计。

## 16. 严守边界

本文是**纯 checkpoint markdown**：

- ❌ 没改任何代码（`services/*` / `ui/*` / `tests/*` / `scripts/*` 全部未触碰）
- ❌ 没改 DB schema
- ❌ 没写 DB
- ❌ 没运行 replay
- ❌ 没运行 real validation
- ❌ 没运行 prepare-only smoke
- ❌ 没读 `data/AVGO.csv` / `NVDA.csv` / `SOXX.csv` / `QQQ.csv` 行
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
- ❌ 没把 W4 / smoke / `logs/regime_validation/` / `logs/prediction_log.jsonl` / DB backup / `agent_loop.py` / `.claude/worktrees/` 任一 commit 进 main
- ❌ 没创建任何新的 `logs/regime_validation/*` 子目录
- ❌ 没运行 `pytest`（本轮纯文档；测试基线维持 commit `7812b10` 时的 **2905 / 0 failed / 10 skipped**）
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*`
- ✅ 只新增 1 份 markdown checkpoint 文档（本文件）
