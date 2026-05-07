# Step 3R-3.3F-C — V2 Execution Path Implementation Checkpoint

> 本文是 **checkpoint markdown** —— 不改代码、不写 DB、不重跑 replay / validation、不 commit / push、不接 trading API、不启 hard / forced、不改 required、不触碰 2026 final-test range、不 add `logs/regime_validation/` / W4 / smoke output / `logs/prediction_log.jsonl`、不处理 DB backup / stash / `.claude/worktrees/`、不调 v1 `candidate_threshold` / SEED coefficients / 6 metric / 7 gate threshold、不改 v1 / adapter / helper / 任一已 merge 测试、不进 3R-5 / 3R-6、不自动 promotion、不 monkey-patch、不跑 v1 冒充 v2。

## 1. 当前完成状态

| 项 | 状态 | 来源 |
|---|---|---|
| v1 real W1-W4 validation single run + result checkpoint | ✅ 已 merge | output `logs/regime_validation/continuous_smoothing_v1_real_w1_w4_20260507_065417/`；commit `75f0ad5` |
| v1 postmortem report | ✅ 已 merge | commit `fc44bcf` |
| v2 launch review design + checkpoint | ✅ 已 merge | commits `4fd1278` / `7c1a0e5` |
| v2 candidate design + checkpoint | ✅ 已 merge | commits `b16fce9` / `7eda5b4` |
| v2 implementation + checkpoint | ✅ 已 merge | commits `ce8b81e` / `95ded24` |
| v2 single real validation pre-flight | ❌ STOP，blocker 命中 | 无 commit；只是报告 |
| v2 execution path design + checkpoint | ✅ 已 merge | commits `18a41d8` / `fe76252` |
| **v2 execution path implementation**（v2 orchestrator + v2 glue + 2 个 focused tests + §46 contract summary） | ✅ **已 merge** | commit `9192a5a` |
| **本 checkpoint** —— 固定 v2 orchestrator path / API / v2 glue path / API / candidate wiring / adapter compatibility / CLI lock / DB guard / no-v1-import proof / no-real-validation proof / tests / 当前限制 / 允许下一步 / 禁止事项 / 边界 | ⏳ **本文**（未 commit） | — |
| v2 single real validation run / v2 result checkpoint / v1 baseline comparison | ❌ 尚未启动 | — |

> v2 execution path 已 merge；v2 real validation 仍未运行；本 checkpoint 只固化 implementation 状态。

## 2. 当前 main 状态

- `main` 最新 commit：`9192a5a`
- commit message：`feat(diagnostics): add v2 execution path`
- 上游：`origin/main` 已同步（push 完成 `fe76252..9192a5a  main -> main`）
- 本步骤已 merge 文件：

| 路径 | 类型 | 行数 |
|---|---|---|
| `scripts/run_continuous_smoothing_validation_v2.py` | 新增 v2 orchestrator | 366 |
| `scripts/run_real_continuous_smoothing_validation_execute_v2.py` | 新增 v2 execution glue | 340 |
| `tests/test_run_continuous_smoothing_validation_v2.py` | 新增 v2 orchestrator focused tests | 474 |
| `tests/test_run_real_continuous_smoothing_validation_execute_v2.py` | 新增 v2 glue focused tests | 874 |
| `tasks/step_1_contract_pipeline_summary.md` | 修改 | +182（追加 §46） |

测试基线：

| 命令 | 结果 |
|---|---|
| `pytest tests/test_run_continuous_smoothing_validation_v2.py -q` | **18 passed** |
| `pytest tests/test_run_real_continuous_smoothing_validation_execute_v2.py -q` | **31 passed** |
| `pytest tests/test_continuous_smoothing_candidate_v2.py -q` | **32 passed** |
| `pytest tests/test_run_continuous_smoothing_validation.py tests/test_run_real_continuous_smoothing_validation_execute.py -q` | **52 passed**（v1 零回归） |
| `pytest -q`（全量） | **2986 passed / 10 skipped / 0 failed / 26 warnings / 94 subtests** |

测试基线累积：Step 3R-3.3F-A 终点 **2937** → Step 3R-3.3F-C 终点 **2986**（+49 净增；2937 基线零回归）。

| 项 | 是否触碰 |
|---|---|
| 改 v1 orchestrator / v1 glue / v1 candidate / candidate v2 / adapter / helper / wrapper / real provider / labels builder | ❌ 否 |
| 改 v1 测试 / v2 candidate 测试 / 任何已 merge 测试 | ❌ 否 |
| 改 DB schema / 写 DB | ❌ 否 |
| 跑 replay / 重跑 real validation / 跑 prepare-only smoke | ❌ 否 |
| 接 yfinance / 网络 / trading API | ❌ 否 |
| 触碰 2026 final-test range | ❌ 否 |
| add `logs/regime_validation/` / W4 / smoke / DB backup / `agent_loop.py` / `.claude/worktrees/` / `logs/prediction_log.jsonl` | ❌ 否 |
| 进 3R-5 formula / 3R-6 simulator | ❌ 否 |
| 启 hard / forced / `_PROTECTION_LAYER_CONNECTED` | ❌ 否 |
| import v1 candidate / v1 orchestrator / v1 glue | ❌ 否（永久封禁；ast + 字符串扫双锁） |
| monkey-patch / 跑 v1 冒充 v2 | ❌ 否 |

## 3. v2 orchestrator path / API

```
scripts/run_continuous_smoothing_validation_v2.py
```

公共 API：

```python
run_continuous_smoothing_validation_v2(
    replay_rows: list[dict],
    *,
    regime_label_provider: Callable[[str, dict], dict],
    w4_manifest: dict,
    candidate_threshold: float = 0.60,
    candidate_name: str = "continuous_smoothing_v2",
    final_test_cutoff: str = "2026-01-01",
    output_dir: str | Path | None = None,
    write_outputs: bool = False,
) -> dict
```

模块常量：

| 常量 | 值 |
|---|---|
| `RUN_SCHEMA_VERSION` | `"continuous_smoothing_validation_run_v2.v1"` |
| `RUN_MANIFEST_SCHEMA_VERSION` | `"regime_validation_run_manifest.v1"`（与 v1 共享，protocol 层） |
| `DEFAULT_CANDIDATE_NAME` | `"continuous_smoothing_v2"` |
| `DEFAULT_CANDIDATE_THRESHOLD` | `0.60`（v2 first-run lock；语义切换由 v2 candidate design §8 锁定） |
| `DEFAULT_FINAL_TEST_CUTOFF` | `"2026-01-01"` |

| 项 | 状态 |
|---|---|
| 是否独立模块 | ✅ |
| 是否 import v1 orchestrator / v1 candidate / v1 glue | ❌ 永久封禁 |
| 是否复用 adapter / helper | ✅（protocol 层；3R-4 锁定） |
| candidate 在 row 中的 attach key | `enriched["candidate"]`（与 v1 同；adapter 兼容） |

## 4. v2 execution glue path / API

```
scripts/run_real_continuous_smoothing_validation_execute_v2.py
```

公共 helpers：

| 函数 | 说明 |
|---|---|
| `get_backup_count(pattern="avgo_agent.db.backup_*") -> int` | glob cwd 计数 |
| `assert_backup_count_unchanged(before: int, after: int) -> None` | mismatch → `RuntimeError("db_backup_count_changed:before=...,after=...")` |
| `validate_execution_args_v2(args) -> None` | run_once_v2 / threshold / cutoff / output_dir / 必填 path 全 lock；mismatch → `ValueError(...)` |
| `build_execution_summary_v2(...) -> dict` | `real_validation_execution_summary_v2.v1`（12 字段） |
| `run_real_validation_execution_v2(args) -> dict` | 完整 11 步 execution flow；调 v2 orchestrator |
| `main(argv=None) -> int` | CLI 入口；refusal → exit 2；happy → JSON summary + exit 0 |

模块常量：

| 常量 | 值 |
|---|---|
| `SUMMARY_SCHEMA_VERSION` | `"real_validation_execution_summary_v2.v1"` |
| `LOCKED_CANDIDATE_THRESHOLD` | `0.60` |
| `LOCKED_FINAL_TEST_CUTOFF` | `"2026-01-01"` |
| `LOCKED_CANDIDATE_NAME` | `"continuous_smoothing_v2"` |
| `EXPECTED_OUTPUT_FILES` | `("replay_validation_records.json", "regime_validation_report.json", "regime_validation_summary.md", "run_manifest.json")` |

| 项 | 状态 |
|---|---|
| 是否独立模块 | ✅ |
| 是否 import v1 glue / v1 orchestrator / v1 candidate | ❌ 永久封禁 |
| 是否复用 wrapper（`build_real_validation_inputs`） | ✅（与 candidate 无关） |
| 是否复用 real provider（`build_real_regime_label_provider`） | ✅ |
| 是否复用 `get_db_fingerprint` / `assert_db_unchanged` | ✅（generic DB guard） |
| 是否直接 `import sqlite3` | ❌ 否（DB 仅通过 wrapper `mode=ro` URI） |

## 5. v2 candidate wiring

| 项 | 状态 |
|---|---|
| v2 orchestrator import candidate v2 | `from services.continuous_smoothing_candidate_v2 import build_continuous_smoothing_candidate_v2` |
| per-row 调用 | `build_continuous_smoothing_candidate_v2(labels, as_of_date=analysis_date, final_test_cutoff=...)` |
| `candidate_name` 默认 | `"continuous_smoothing_v2"` |
| enriched row attach | `enriched["candidate"] = candidate`（与 v1 同 key；adapter `_candidate_state` 接口兼容） |
| 是否 import v1 candidate | ❌ 永久封禁 |
| 是否 import v1 orchestrator | ❌ 永久封禁 |
| 是否 import v1 glue | ❌ 永久封禁 |
| spy 测试断言 | v2 candidate 真实被调；v1 candidate 从未触达 |

## 6. adapter / helper compatibility

`services/replay_validation_record_adapter.py` `_candidate_state(...)` 是 threshold-on-`risk_score`（**未改**）：

| v2 candidate 输出 | adapter 行为 |
|---|---|
| `risk_bucket="abstain"` + `risk_score=None` | warning `candidate_unavailable` + `candidate_triggered=False` |
| `final_test_refusal=True` | warning `candidate_final_test_refusal` + `candidate_triggered=False` |
| `risk_score >= threshold` | `candidate_triggered=True` |
| `risk_score < threshold` | `candidate_triggered=False` |

`services/regime_validation_helper.py` 只看 records；不知 v1/v2；`candidate_name` 由 caller 透传（**未改**）。

| 是否需要改 adapter / helper | ❌ 否 |
|---|---|
| 是否需要新 v2-specific adapter / helper | ❌ 否 |
| 是否需要新 protocol schema | ❌ 否（adapter / helper / run_manifest schemas 与 candidate-level 无关） |

## 7. CLI lock

| 参数 | 默认 | lock 行为 |
|---|---|---|
| `--run-once-real-validation-v2` | flag，默认 False | 不传 → exit 2 `refuse_to_run:missing_explicit_opt_in:--run-once-real-validation-v2 is required` |
| `--candidate-threshold` | `0.60` | ≠ 0.60 → exit 2 `refuse_to_run:candidate_threshold_locked:expected=0.6,got=...` |
| `--final-test-cutoff` | `"2026-01-01"` | ≠ `"2026-01-01"` → exit 2 `refuse_to_run:final_test_cutoff_locked:expected="2026-01-01",got=...` |
| `--output-dir` | 必填 | 已存在 → exit 2 `refuse_to_run:output_dir_exists:... must not exist; refuse to overwrite` |
| `--db-path` / `--w4-jsonl` / `--w4-manifest` / `--avgo-csv` / `--nvda-csv` / `--soxx-csv` / `--qqq-csv` / `--output-dir` | 必填 | 缺任一 → exit 2 `refuse_to_run:missing_required_args:...` |

**v1 flag rejection**：parser `allow_abbrev=False`；argparse 默认接受 `--run-once-real-validation` 作为 `--run-once-real-validation-v2` 的 prefix 缩写 silently 接受 → v2 parser 显式 disable，v1 flag 现在被 argparse SystemExit 拒绝。

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

## 8. DB / output guard

### 8.1 三组 fingerprint

| # | 对象 | 来源 |
|---|---|---|
| 1 | `avgo_agent.db` mtime_ns + size_bytes | `get_db_fingerprint(args.db_path)`（wrapper 提供） |
| 2 | `data/market_data.db` mtime_ns + size_bytes（若存在） | 同上（额外 fingerprint） |
| 3 | `avgo_agent.db.backup_*` glob count | `get_backup_count(...)`（v2 glue 自实现） |

### 8.2 检查时机

- **Before**：execution flow step 2 / 3 / 4
- **After**：execution flow step 9 / 10

### 8.3 失败行为

| 变化 | 行为 |
|---|---|
| `avgo_agent.db` mtime_ns 变化 | `assert_db_unchanged` raises `RuntimeError("db_modified:mtime_ns_changed:...")` |
| `avgo_agent.db` size_bytes 变化 | `assert_db_unchanged` raises `RuntimeError("db_modified:size_bytes_changed:...")` |
| `data/market_data.db` mtime_ns / size_bytes 变化（若存在） | 同上 |
| `avgo_agent.db.backup_*` count 变化 | `assert_backup_count_unchanged` raises `RuntimeError("db_backup_count_changed:before=...,after=...")` |

任一异常 → v2 glue 抛出，CLI catch 后输出 stderr `execution_failed:RuntimeError:<msg>` + `return 2`。

### 8.4 output guard

- `output_dir` 必须**不存在**（CLI lock 提前拒；v2 orchestrator `_write_outputs_files_v2(...)` 内部 `FileExistsError` 二重保险）
- 4 文件全部 exist；缺任一 → `RuntimeError("output_files_missing:[...] in <dir>")`
- output 全部 untracked（`logs/regime_validation/` 已 gitignore）
- 不 commit raw output

## 9. no-v1-import proof

### 9.1 ast.walk 锁定（v2 orchestrator + v2 glue 双锁）

forbidden imports（不出现在 `import` / `from ... import`）：

| 模块 | 类别 |
|---|---|
| `services.continuous_smoothing_candidate` | v1 candidate（永久封禁） |
| `scripts.run_continuous_smoothing_validation` | v1 orchestrator（永久封禁） |
| `scripts.run_real_continuous_smoothing_validation_execute` | v1 glue（永久封禁） |

### 9.2 字符串扫

不出现在模块文本：

- `from services.continuous_smoothing_candidate import`
- `from scripts.run_continuous_smoothing_validation import`
- `from scripts.run_real_continuous_smoothing_validation_execute import`

### 9.3 spy / runtime 测试

| 测试 | 断言 |
|---|---|
| `CandidateFactoryWiringTests.test_v2_candidate_called_not_v1` | 2 rows → 2 v2 candidate calls；从未触达 v1 candidate |
| `CandidateFactoryWiringTests.test_candidate_attached_under_adapter_readable_key` | `row["candidate"]["schema_version"] == "continuous_smoothing_candidate_v2.v1"`；`row["candidate"]["candidate_name"] == "continuous_smoothing_v2"` |
| `RunRealValidationExecutionV2HappyPathTests.test_run_real_validation_execution_v2_calls_v2_orchestrator` | `run_continuous_smoothing_validation_v2` mock call_count=1；`candidate_name="continuous_smoothing_v2"` 透传 |
| `RunRealValidationExecutionV2HappyPathTests.test_happy_path_returns_v2_summary_and_writes_4_files` | summary `schema_version="real_validation_execution_summary_v2.v1"`；`candidate_name="continuous_smoothing_v2"` |
| `CliV2Tests.test_v1_flag_not_recognized` | `--run-once-real-validation`（v1 flag）→ argparse SystemExit |

| 是否 monkey-patch | ❌ 否 |
|---|---|
| 是否跑 v1 冒充 v2 | ❌ 否 |
| 是否使用 v1 schema 假冒 v2 | ❌ 否（v2 输出明确 `schema_version` v2） |

## 10. no-real-validation proof

### 10.1 测试 mock 三层

| heavy fn | mock 方式 |
|---|---|
| `build_real_validation_inputs(...)` | `mock.patch.object(glue_v2, "build_real_validation_inputs", side_effect=fake_inputs)` |
| `build_real_regime_label_provider(...)` | `mock.patch.object(glue_v2, "build_real_regime_label_provider", side_effect=fake_provider_factory)` |
| `run_continuous_smoothing_validation_v2(...)` | `mock.patch.object(glue_v2, "run_continuous_smoothing_validation_v2", side_effect=fake_run)`；`fake_run` 在受控 tmp 写 4 fixture 文件 |

### 10.2 测试**不**做的事

- ❌ **不**读真实 4 csv（`data/AVGO.csv` / `NVDA.csv` / `SOXX.csv` / `QQQ.csv`）
- ❌ **不**读真实 W4 jsonl（`logs/historical_training/three_system_w4_2024_08_2025_12/three_system_replay_results.jsonl`）
- ❌ **不**跑 639 rows（W1-W3 DB=286 + W4=353）
- ❌ **不**连真实 `avgo_agent.db`（fixture sqlite 文件 + 受控 cwd）
- ❌ **不**触碰真实 `data/market_data.db`
- ❌ **不**触碰真实 `avgo_agent.db.backup_*`
- ❌ **不**真实运行 v2 W1-W4 validation
- ❌ **不** import v1 orchestrator / v1 candidate / v1 glue 任一公共 API
- ❌ **不**自动触发 single real run（real run 必须用户单独指令）

## 11. tests

### 11.1 测试结果

| 命令 | 结果 |
|---|---|
| `pytest tests/test_run_continuous_smoothing_validation_v2.py -q` | **18 passed** |
| `pytest tests/test_run_real_continuous_smoothing_validation_execute_v2.py -q` | **31 passed** |
| `pytest tests/test_continuous_smoothing_candidate_v2.py -q` | **32 passed** |
| `pytest tests/test_run_continuous_smoothing_validation.py tests/test_run_real_continuous_smoothing_validation_execute.py -q` | **52 passed**（v1 零回归） |
| `pytest -q`（全量） | **2986 passed / 10 skipped / 0 failed / 26 warnings / 94 subtests** |

### 11.2 v2 orchestrator focused tests 覆盖矩阵（18 tests）

| 测试类 | 数量 | 覆盖点 |
|---|---|---|
| `OutputSchemaTests` | 3 | top-level keys + run schema_version v2 / candidate_name 默认 v2 / threshold + cutoff 默认 |
| `CandidateFactoryWiringTests` | 2 | v2 candidate 真实被调（spy 计数）/ candidate 在 `row["candidate"]`（adapter 可读，schema v2） |
| `CutoffBehaviorTests` | 2 | final-test row skipped + touched / regime_labels final_test_refusal 透传 |
| `ThresholdPassthroughTests` | 2 | threshold 默认 / explicit 都透传 adapter |
| `WriteOutputsTests` | 4 | write=False 不写 / write=True 写 4 文件 / 已存在 output_dir → FileExistsError / write=True without output_dir → ValueError |
| `InputNotMutatedTests` | 1 | rows + manifest 不被 mutate |
| `IsolationTests` | 4 | 21 项 forbidden import（含 v1 三模块）/ 字符串扫 v1 ref / hard / required / trading / threshold sweep |

### 11.3 v2 glue focused tests 覆盖矩阵（31 tests）

| 测试类 | 数量 | 覆盖点 |
|---|---|---|
| `GetBackupCountTests` | 1 | glob cwd 计数 |
| `AssertBackupCountUnchangedTests` | 2 | equal / mismatch raises |
| `ValidateExecutionArgsV2Tests` | 7 | 缺 v2 flag / v1 flag attribute substitute / threshold ≠ 0.60（4 例）/ cutoff ≠ "2026-01-01"（3 例）/ output_dir 已存在 / 缺必填 path（subTest 8 attrs）/ happy path |
| `BuildExecutionSummaryV2Tests` | 1 | 12 字段 + schema v2 + lock 透传 |
| `RunRealValidationExecutionV2HappyPathTests` | 3 | mocked 完整路径 + 4 文件 verify + summary v2 + orchestrator 真实是 v2 / 缺 output 文件 raises |
| `GuardMismatchTests` | 4 | DB size mismatch / DB mtime mismatch / backup count mismatch / market_data.db mismatch |
| `CliV2Tests` | 7 | 缺 v2 flag → exit 2 / v1 flag → argparse SystemExit / threshold ≠ 0.60 / cutoff ≠ 2026-01-01 / output_dir 已存在 / 9 项 forbidden flag SystemExit / mocked happy → exit 0 + JSON v2 summary |
| `IsolationTests` | 6 | 27 项 forbidden import（含 v1 三模块）/ no v1 string ref / 不 直接 import sqlite3 / hard / required / trading 字符串 / threshold sweep + 9 项 override flag 字符串 / locked 常量必须存在 |

## 12. 当前限制

| 限制 | 状态 |
|---|---|
| v2 real validation 仍未运行 | ❌ 未跑 |
| v2 `output_dir` 仍未创建（`logs/regime_validation/continuous_smoothing_v2_real_w1_w4_<TS>/`） | ❌ 未存在 |
| v2 `regime_validation_report.json` / `replay_validation_records.json` / `regime_validation_summary.md` / `run_manifest.json` | ❌ 未生成 |
| v2 是否优于 v1 baseline | ❓ 未知 |
| v1 vs v2 baseline comparison | ❓ 未生成 |
| v2 result checkpoint | ❌ 未启动 |
| v2 first real run 必须用户单独指令触发 | ✅ 强制 |
| v2 是否解锁 3R-5 / 3R-6 | ❌ 永远不（即便 v2 全 pass） |
| v2 是否自动 promotion / 自动启 hard | ❌ 永远不 |

## 13. 允许下一步

| # | 候选 | 状态 |
|---|---|---|
| 1 | **v2 single real validation run**（用户单独确认指令触发） | ✅ 允许（在本 checkpoint 进 main 后） |
| 2 | 必须使用 v2 glue：`scripts/run_real_continuous_smoothing_validation_execute_v2.py` | ✅ 强制 |
| 3 | 必须传 `--run-once-real-validation-v2`（v1 flag 不接受） | ✅ 强制 |
| 4 | 必须传 `--candidate-threshold 0.60`（v2 first-run lock；v2 语义） | ✅ 强制 |
| 5 | 必须传 `--final-test-cutoff 2026-01-01`（lock） | ✅ 强制 |
| 6 | 必须**新 timestamp output_dir**（如 `logs/regime_validation/continuous_smoothing_v2_real_w1_w4_YYYYMMDD_HHMMSS/`），且**不存在** | ✅ 强制 |
| 7 | 必须**不写 DB**；DB / market_data.db / backup count 三组 fingerprint 全 unchanged | ✅ |
| 8 | 必须**不 commit raw output**（4 文件保持 untracked） | ✅ |
| 9 | 必须写 **v2 result checkpoint** + **v1 baseline comparison**（量化对比表：per-window false_exclusion_rate / survival_case_preservation / trigger rate / cross_window_variance / gate_status v1 vs v2） | ✅ |
| 10 | wrapper / candidate v1 / candidate v2 / adapter / helper / orchestrator v1 / orchestrator v2 / glue v1 / glue v2 / labels builder / real provider 现有行为 | ❌ 不改（仅只读调用） |
| 11 | hard / required upgrade / Gate 5 / Gate 6 / `_PROTECTION_LAYER_CONNECTED` | ❌ 永久封禁 |
| 12 | 直接进入 Step 3R-5 / 3R-6 | ❌ 永久封禁 |

## 14. 禁止事项

| # | 禁止 | 理由 |
|---|---|---|
| 1 | **不**自动跑 validation | 必须用户单独确认；本 checkpoint 不触发 run |
| 2 | **不**新增 `.py` 文件（在本 checkpoint 范围内） | 本步骤是 checkpoint only |
| 3 | **不**新增测试（在本 checkpoint 范围内） | 测试已在 implementation 步骤完成 |
| 4 | **不**写 DB / **不**改 DB schema | 全程 read-only |
| 5 | **不**跑 v1 冒充 v2 | spy 测试 + ast 锁定双保险 |
| 6 | **不**改 v1 orchestrator / v1 glue / v1 candidate / candidate v2 / adapter / helper / wrapper / real provider / labels builder / 任何已 merge 测试 | 永久 freeze |
| 7 | **不** sweep / **不** grid search / **不** retry-until-pass | first run 不允许从 baseline 反推参数 |
| 8 | **不**调 v1 / v2 阈值或工程默认 | calibration_context 必须保持 not-fitted |
| 9 | **不**启 hard / forced / `anti_false_exclusion_triggered` / `_PROTECTION_LAYER_CONNECTED` | 永久封禁 |
| 10 | **不**改 04 / 05 / 07 required | Step 2G 全程边界 |
| 11 | **不**触碰 2026 final-test range | 6 层 hard stop 全保留 |
| 12 | **不**接 trading（`longbridge` / `broker` / `paper_trade`） | 永久封禁 |
| 13 | **不**接 yfinance / requests / urllib / 任何网络 | 永久封禁 |
| 14 | **不**直接进入 Step 3R-5 formula / 3R-6 simulator | 必须先过 v2 result checkpoint + 新一轮独立 launch review |
| 15 | **不** commit validation outputs | `logs/regime_validation/` 全部 untracked |
| 16 | **不** commit 本 checkpoint 之外的产物 | 本轮不 commit / push |
| 17 | **不** import v1 candidate / v1 orchestrator / v1 glue 任一模块 | ast + 字符串扫双锁 |
| 18 | **不** monkey-patch | 与"不要临时 hack"一致 |
| 19 | **不**让 v2 fail / pass 自动 promotion | 永久封禁 |
| 20 | **不**用 first v2 real run 数据反推参数 | 阈值 / coefficient 变更必须经独立 launch review |
| 21 | **不**触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*` | 历史防护 |

## 15. 下一步建议

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **commit 本 checkpoint** | 把 §1-16 implementation 状态固化到 main | 本轮 / 下一轮 |
| 2 | **v2 single real validation run**（**用户单独确认指令触发**） | 调 `scripts/run_real_continuous_smoothing_validation_execute_v2.py --run-once-real-validation-v2 ...`；新 timestamp output_dir；同 cutoff `2026-01-01`；DB / market_data / backup 三组 fingerprint 守护；output 4 文件本地 untracked | 高（本 checkpoint 进 main 后；用户单独触发） |
| 3 | **v2 result checkpoint** + **v1 baseline comparison** | 摘要 / report_status / per-window / fail_reason / DB guard verification / output 4 文件结构（不 commit raw json）/ v1 vs v2 量化对比表 | 中（v2 real run 完成后） |
| 4 | 根据 v2 result 决定是否进入新一轮 review；**不**直接进 3R-5 / 3R-6；**不**自动 promotion | v2 pass 仅允许 review；v2 fail 需回 candidate / threshold design 重设 | — |
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
- ❌ 没改 `services/regime_features_builder.py` / `regime_labels_builder.py` / `regime_validation_helper.py` / `continuous_smoothing_candidate.py`（v1） / `continuous_smoothing_candidate_v2.py` / `replay_validation_record_adapter.py` / `historical_replay_training.py` / `real_regime_label_provider.py` / 任何 ui 模块 / 任何 builder
- ❌ 没改 `scripts/run_continuous_smoothing_validation.py`（v1 orchestrator）/ `run_real_continuous_smoothing_validation.py`（wrapper）/ `run_real_continuous_smoothing_validation_execute.py`（v1 glue）
- ❌ 没改 `scripts/run_continuous_smoothing_validation_v2.py`（v2 orchestrator；本 checkpoint 不再改）/ `run_real_continuous_smoothing_validation_execute_v2.py`（v2 glue；本 checkpoint 不再改）
- ❌ 没改任一已 merge 测试（v1 / v2 candidate / v2 orchestrator / v2 glue 测试）
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
- ❌ 没改 Step 3R-3.3 / 3R-3.3A / 3R-3.3B / 3R-3.3C 系列 / 3R-3.3C-D / 3R-3.3E / 3R-3.3F design / checkpoint / 3R-3.3F-A / 3R-3.3F-C 已 merge 文档 / 实施
- ❌ 没改 Step 2G-8D / 8D.1A / 8D.2 / 8D.3 / 8D.4 文档或代码
- ❌ 没把 W4 / smoke / `logs/regime_validation/` / v1 raw output / `logs/prediction_log.jsonl` / DB backup / `agent_loop.py` / `.claude/worktrees/` 任一 commit 进 main
- ❌ 没创建任何**新的** `logs/regime_validation/*` 子目录
- ❌ 没运行 `pytest`（本轮纯文档；测试基线维持 commit `9192a5a` 时的 **2986 / 0 failed / 10 skipped**）
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*`
- ❌ 没调 v1 / v2 任一 threshold / SEED / coefficient / 工程默认
- ❌ 没用 v1 baseline 数据反推 v2 任何具体参数
- ❌ 没让 v1 fail / v2 implementation 触发 retry / sweep / grid search
- ❌ 没让 v2 implementation 自动 promotion / 自动解锁 3R-5 / 3R-6
- ❌ 没真实运行 v2 W1-W4 validation
- ❌ 没 monkey-patch
- ❌ 没跑 v1 冒充 v2
- ❌ 没让 v2 orchestrator import v1 任一模块
- ✅ 只新增 1 份 markdown checkpoint 文档（本文件）
