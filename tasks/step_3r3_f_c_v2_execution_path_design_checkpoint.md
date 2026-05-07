# Step 3R-3.3F-C — V2 Execution Path Design Checkpoint

> 本文是 **checkpoint markdown** —— 不改代码、不写 DB、不重跑 replay / validation、不 commit / push、不接 trading API、不启 hard / forced、不改 required、不触碰 2026 final-test range、不 add `logs/regime_validation/` / W4 / smoke output / `logs/prediction_log.jsonl`、不处理 DB backup / stash / `.claude/worktrees/`、不改 v1 orchestrator / v1 execution glue / adapter / helper / wrapper / real provider / candidate v1 / candidate v2、不实现 v2 execution path、不 monkey patch、不跑 v1 冒充 v2、不进 3R-5 / 3R-6 / 不自动 promotion。

## 1. 当前完成状态

| 项 | 状态 | 来源 |
|---|---|---|
| v1 real W1-W4 validation single run + result checkpoint | ✅ 已 merge | output `logs/regime_validation/continuous_smoothing_v1_real_w1_w4_20260507_065417/`；commit `75f0ad5` |
| v1 postmortem report | ✅ 已 merge | commit `fc44bcf` |
| v2 launch review design + checkpoint | ✅ 已 merge | commits `4fd1278` / `7c1a0e5` |
| v2 candidate design + checkpoint | ✅ 已 merge | commits `b16fce9` / `7eda5b4` |
| v2 implementation + checkpoint | ✅ 已 merge | commits `ce8b81e` / `95ded24` |
| **v2 single real validation pre-flight** | ❌ **STOP**，blocker 命中 | 无 commit；只是报告 |
| Step 3R-3.3F-C **v2 execution path design**（14 节、409 行） | ✅ **已 merge** | commit `18a41d8` |
| **本 checkpoint** —— 固定 blocker / proposed files / v2 orchestrator design / v2 glue design / threshold semantics / adapter compatibility / CLI / tests plan / validation run plan / no-go / 允许下一步 / 边界 | ⏳ **本文**（未 commit） | — |
| v2 execution path implementation（4 个新文件） | ❌ 尚未启动 | — |
| v2 single real validation run / v2 result checkpoint / v1 baseline comparison | ❌ 尚未启动 | — |

> v2 candidate 已实现并 merge；v2 execution path 尚未实现 → v2 real validation 尚不能跑；本 checkpoint 只固化 v2 execution path design 状态。

## 2. 当前 main 状态

- `main` 最新 commit：`18a41d8`
- commit message：`docs(contract): Step 3R-3.3F-C v2 execution path design`
- 上游：`origin/main` 已同步（push 完成 `95ded24..18a41d8  main -> main`）
- 本步骤已 merge 文件：

| 路径 | 类型 | 行数 |
|---|---|---|
| `tasks/step_3r3_f_c_v2_execution_path_design.md` | 新增 | 409（v2 execution path design 边界） |

测试基线：本步骤纯文档；测试基线维持 commit `ce8b81e` 时的 **2937 / 0 failed / 10 skipped**。

| 项 | 是否触碰 |
|---|---|
| 改代码 | ❌ 否 |
| 改 v1 orchestrator / v1 execution glue / adapter / helper / wrapper / real provider / candidate v1 / candidate v2 / labels builder | ❌ 否 |
| 改 DB schema / 写 DB | ❌ 否 |
| 跑 replay / 重跑 real validation / 跑 prepare-only smoke | ❌ 否 |
| 调 v1 `candidate_threshold` / SEED coefficients | ❌ 否 |
| 调 6 metric / 7 gate threshold | ❌ 否 |
| 接 yfinance / 网络 / trading API | ❌ 否 |
| 触碰 2026 final-test range | ❌ 否 |
| add `logs/regime_validation/` / W4 / smoke / DB backup / `agent_loop.py` / `.claude/worktrees/` / `logs/prediction_log.jsonl` | ❌ 否 |
| 进 3R-5 formula / 3R-6 simulator | ❌ 否 |
| 启 hard / forced / `_PROTECTION_LAYER_CONNECTED` | ❌ 否 |
| 实现 v2 execution path / 新增 4 个文件 | ❌ 否 |
| monkey patch | ❌ 否 |

## 3. blocker summary

### 3.1 主 blocker

```text
scripts/run_continuous_smoothing_validation.py:45-46
    from services.continuous_smoothing_candidate import (
        build_continuous_smoothing_candidate,
    )
scripts/run_continuous_smoothing_validation.py:97
    candidate = build_continuous_smoothing_candidate(
        labels,
        as_of_date=analysis_date,
        final_test_cutoff=final_test_cutoff,
    )
```

- v1 orchestrator **硬 import** v1 candidate
- `run_continuous_smoothing_validation(...)` 公共 API **没有** candidate-factory 参数
- `scripts/run_real_continuous_smoothing_validation_execute.py`（v1 glue）只能调到 v1 orchestrator → 直接跑会执行 v1，不是 v2

### 3.2 次级 blocker（threshold lock 0.60）

- `scripts/run_real_continuous_smoothing_validation_execute.py` `validate_execution_args(...)` 锁 `--candidate-threshold == 0.60`
- v2 first run 仍可使用 0.60 但**语义不同**（见 §7）；不阻碍 run，但需要 docstring + checkpoint 明确

### 3.3 不能用的 hack 路径

| Hack 方式 | 为什么不可 |
|---|---|
| 修改 v1 orchestrator 加 factory 参数 | 改已 merge 模块 |
| monkey-patch `build_continuous_smoothing_candidate` | 运行时改行为；不进 merge 链；不可复现 |
| 跑 v1 然后改 candidate_name 字符串 | 等价"跑 v1 冒充 v2" |
| `regime_label_provider` 返回伪 candidate 骗 orchestrator | 改语义；输出 schema 错 |
| v2 模块 import v1 orchestrator + hot-reload | 仍需 patch v1；不可 |

## 4. proposed files

后续 Step 3R-3.3F-C **implementation** 步骤新增（**本 checkpoint 不新增**）：

| # | 路径 | 类型 | 估算行数 |
|---|---|---|---|
| 1 | `scripts/run_continuous_smoothing_validation_v2.py` | 新增 v2 orchestrator | ~300 |
| 2 | `scripts/run_real_continuous_smoothing_validation_execute_v2.py` | 新增 v2 execution glue | ~350 |
| 3 | `tests/test_run_continuous_smoothing_validation_v2.py` | 新增 v2 orchestrator focused tests | ~600 |
| 4 | `tests/test_run_real_continuous_smoothing_validation_execute_v2.py` | 新增 v2 glue focused tests | ~700 |

约束：

- ❌ **不**改 v1 `scripts/run_continuous_smoothing_validation.py` / `run_real_continuous_smoothing_validation.py`（wrapper） / `run_real_continuous_smoothing_validation_execute.py`
- ❌ **不**改 adapter / helper / wrapper / real provider / candidate v1 / candidate v2 / labels builder
- ❌ **不**改任何已 merge 测试
- ❌ **不**让 v2 orchestrator import v1 orchestrator / v1 candidate / v1 glue 任一公共 API

## 5. v2 orchestrator design

| 项 | 状态 |
|---|---|
| 文件 | `scripts/run_continuous_smoothing_validation_v2.py` |
| 是否独立模块 | ✅（**不** import v1 orchestrator / v1 candidate / v1 glue） |
| 是否复用 adapter / helper / wrapper / real provider | ✅（这些是 protocol 层；3R-4 锁定；多消费方共享） |
| 是否生产主链 / streamlit / trading | ❌ 否（与 v1 一致；diagnostic library） |

**唯一三处差异 vs v1 orchestrator**：

| # | 差异 | v1 | v2 |
|---|---|---|---|
| 1 | 候选 import | `from services.continuous_smoothing_candidate import build_continuous_smoothing_candidate` | `from services.continuous_smoothing_candidate_v2 import build_continuous_smoothing_candidate_v2` |
| 2 | candidate 调用 | `build_continuous_smoothing_candidate(labels, as_of_date=..., final_test_cutoff=...)` | `build_continuous_smoothing_candidate_v2(labels, as_of_date=..., final_test_cutoff=...)`（API 完全兼容） |
| 3 | adapter / helper / run_manifest 中的 `candidate_name` | `"continuous_smoothing_v1"` | `"continuous_smoothing_v2"` |

公共 API 草案（不实现）：

```python
def run_continuous_smoothing_validation_v2(
    replay_rows: list[dict],
    *,
    regime_label_provider: Callable,
    w4_manifest: dict,
    candidate_threshold: float = 0.60,
    candidate_name: str = "continuous_smoothing_v2",  # lock
    final_test_cutoff: str = "2026-01-01",
    output_dir: str | Path | None = None,
    write_outputs: bool = False,
) -> dict
```

## 6. v2 execution glue design

| 项 | 状态 |
|---|---|
| 文件 | `scripts/run_real_continuous_smoothing_validation_execute_v2.py` |
| 是否独立模块 | ✅（**不** import v1 glue） |
| 是否复用 wrapper（`build_real_validation_inputs`） | ✅（与 candidate 无关） |
| 是否复用 real provider（`build_real_regime_label_provider`） | ✅ |
| 是否复用 `get_db_fingerprint` / `assert_db_unchanged` | ✅（generic DB guard） |
| DB / market_data / backup 三组 fingerprint guard | ✅ 与 v1 一致 |
| output_dir | `logs/regime_validation/continuous_smoothing_v2_real_w1_w4_<TS>/` |
| summary schema | `real_validation_execution_summary_v2.v1`（**新 schema**；与 v1 `real_validation_execution_summary.v1` 不冲突） |

execution flow（11 步）：

| # | 步骤 | v1 vs v2 差异 |
|---|---|---|
| 1 | validate args | v2 锁 `--run-once-real-validation-v2` flag（与 v1 名字**故意不同**） |
| 2 | DB fingerprint before | 同 v1 |
| 3 | market_data.db fingerprint before | 同 v1 |
| 4 | backup count before | 同 v1 |
| 5 | `build_real_validation_inputs(...)` | 同 v1（wrapper 复用） |
| 6 | `build_real_regime_label_provider(...)` | 同 v1（real provider 复用） |
| 7 | call orchestrator + write_outputs | **`run_continuous_smoothing_validation_v2(...)`**（替换 v1） |
| 8 | verify 4 output files | 同 v1（4 文件名 + schema 不变） |
| 9 | DB fingerprint after + assert | 同 v1 |
| 10 | backup count after + assert | 同 v1 |
| 11 | return summary | summary schema = `real_validation_execution_summary_v2.v1`；`candidate_name="continuous_smoothing_v2"` |

## 7. threshold semantics

| 项 | v1 | v2 |
|---|---|---|
| `--candidate-threshold` 默认 | `0.60`（lock） | `0.60`（**first run lock**；非 0.60 → exit 2） |
| 数值是否相同 | 是 | 是（happen-to-share；语义不同） |
| 语义 | "overheat-style risk score" 高于 0.60 → exclude | **"calibrated `P̂(prediction wrong)`" 高于 0.60 → exclude** |
| 是否 sweep | ❌ | ❌（永久禁止） |
| 是否调参 | ❌ | ❌（first run 不能从 v1 fail baseline 反推） |
| 是否 retry-until-pass | ❌ | ❌ |
| 文档要求 | v1 result checkpoint 已固定 | **v2 glue 必须在 docstring + checkpoint 明确**：v2 的 0.60 不是 v1 阈值；语义切换由 v2 candidate design 锁定 |

## 8. adapter / helper compatibility

| v2 candidate 输出 | adapter 行为 | 是否需改 |
|---|---|---|
| `risk_bucket="abstain"` + `risk_score=None` | `_candidate_state` warning `candidate_unavailable` + `candidate_triggered=False` | ❌ |
| `final_test_refusal=True` | warning `candidate_final_test_refusal` + `candidate_triggered=False`；records `final_test_refusal=True` | ❌ |
| `risk_score >= threshold` | `candidate_triggered=True` | ❌ |
| `risk_score < threshold` | `candidate_triggered=False` | ❌ |
| `risk_score=None`（缺数据 / abstain） | `candidate_unavailable` + `candidate_triggered=False` | ❌ |

helper 只看 records；不知 v1/v2；`candidate_name` 由 caller 传入。

| 是否需要改 adapter | ❌ 否 |
|---|---|
| 是否需要改 helper | ❌ 否 |
| 是否需要新 v2-specific adapter / helper | ❌ 否 |
| 是否需要新 schema | ❌ 否（adapter / helper / run_manifest schemas 与 candidate-level 无关） |

## 9. CLI design

v2 execution glue CLI（implementation 才落地；本 checkpoint 仅声明 contract）：

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `--run-once-real-validation-v2` | flag | ✅ | False | 不传 → exit 2 + refusal `missing_explicit_opt_in:--run-once-real-validation-v2 is required`（与 v1 flag 名**故意不同**） |
| `--db-path` | str | ✅ | — | 同 v1 |
| `--w4-jsonl` | str | ✅ | — | 同 v1 |
| `--w4-manifest` | str | ✅ | — | 同 v1 |
| `--avgo-csv` / `--nvda-csv` / `--soxx-csv` / `--qqq-csv` | str | ✅ | — | 同 v1 |
| `--candidate-threshold` | float | ✅ | `0.60` | first run lock；非 0.60 → exit 2 |
| `--final-test-cutoff` | str | ✅ | `"2026-01-01"` | lock；非 cutoff → exit 2 |
| `--output-dir` | str | ✅ | — | 必须不存在；建议 `logs/regime_validation/continuous_smoothing_v2_real_w1_w4_<TS>` |

不存在的 flag（与 v1 一致；argparse 自动 SystemExit）：

- `--allow-overwrite`
- `--threshold-sweep`
- `--skip-db-guard`
- `--write-db`
- `--enable-hard`
- `--enable-forced`
- `--allow-network`
- `--ignore-final-test-cutoff`
- `--connect-protection-layer`

## 10. tests plan

### 10.1 v2 orchestrator focused tests（`tests/test_run_continuous_smoothing_validation_v2.py`）

镜像 v1 orchestrator tests，唯一差异：测试调 v2 orchestrator + mock v2 candidate factory（或调真实 v2 candidate；设计阶段不强制）。

| 测试领域 | 范围 |
|---|---|
| top-level run dict + run_manifest schema | 同 v1 |
| candidate v2 被调用 | mock 或注入；**不**跑真实 v2 candidate 在 639 rows 上 |
| adapter records produced + records_adapted matches | 同 v1 |
| 输入 rows + manifest 不被 mutate | 同 v1 |
| final-test row skipped（cutoff） | 同 v1 |
| `regime_label_provider` final_test_refusal propagates | 同 v1 |
| `candidate_threshold` 透传 adapter | 同 v1 |
| 无 threshold sweep（字符串 + AST） | 同 v1 |
| `write_outputs` 行为 + 4 文件命名 | 同 v1 |
| 已存在 output_dir → `FileExistsError` | 同 v1 |
| `report_status` 镜像 helper 状态 | 同 v1 |
| isolation：**不** import v1 orchestrator / v1 candidate / v1 glue | ast.walk + 字符串扫双锁 |
| isolation：DB / yfinance / streamlit / trading / prediction_store / hard / forced / required / final_direction | 同 v1 |

### 10.2 v2 execution glue focused tests（`tests/test_run_real_continuous_smoothing_validation_execute_v2.py`）

镜像 v1 glue tests；调用关系替换为 v2。

| 测试领域 | 范围 |
|---|---|
| `get_backup_count` / `assert_backup_count_unchanged` | 同 v1 |
| `validate_execution_args` lock | 缺 `--run-once-real-validation-v2` → exit 2；threshold ≠ 0.60 → exit 2；cutoff ≠ "2026-01-01" → exit 2；output_dir 已存在 → exit 2；缺必填 path → exit 2 |
| `build_execution_summary` shape | `schema_version="real_validation_execution_summary_v2.v1"`；`candidate_name="continuous_smoothing_v2"`；12 字段 |
| happy path（mocked） | mock heavy fns；orchestrator side-effect 写 4 fixture 文件 |
| 4 output files verify / 缺一 → RuntimeError | 同 v1 |
| DB / market_data / backup mismatch raises | 同 v1（受控 cwd） |
| CLI happy path（mocked） → exit 0 + JSON summary | 同 v1 |
| forbidden flags（argparse SystemExit） | 同 v1 |
| isolation：**不** import v1 orchestrator / v1 glue / v1 candidate | ast.walk + 字符串扫 |
| isolation：forbidden imports / 字符串扫（hard / forced / required / trading / sweep / `_PROTECTION_LAYER_CONNECTED`） | 同 v1 |

### 10.3 测试**不**做的事

- ❌ 不读真实 4 csv（`data/AVGO.csv` / `NVDA.csv` / `SOXX.csv` / `QQQ.csv`）
- ❌ 不读真实 W4 jsonl
- ❌ 不跑 639 rows
- ❌ 不连真实 `avgo_agent.db`
- ❌ 不触碰真实 `data/market_data.db` / `avgo_agent.db.backup_*`
- ❌ 不真实运行 v2 validation
- ❌ 不 import v1 orchestrator / v1 candidate / v1 glue 任一公共 API

## 11. validation run plan

| # | 步骤 | 范围 |
|---|---|---|
| 1 | commit 本 checkpoint | 仅 markdown |
| 2 | v2 execution path **implementation**（4 个新文件，§4） | merged 实现 + focused tests + full pytest 零回归 |
| 3 | v2 execution path **implementation checkpoint** | 状态归档 |
| 4 | **v2 single real validation run**（**用户单独指令触发**） | 同 cutoff `2026-01-01`；新 timestamp output_dir；DB / market_data / backup 三组 fingerprint 守护；4 文件 untracked；**不** commit raw json |
| 5 | **v2 result checkpoint** + **v1 baseline comparison** | per-window false_exclusion_rate / survival_case_preservation / trigger rate / cross_window_variance / gate_status v1 vs v2 |
| 6 | 根据 v2 result 决定下一步 review；**不**直接进 3R-5 / 3R-6；**不**自动 promotion | — |

> 本 checkpoint 范围只到第 1 步；2 之后是后续步骤。

## 12. no-go rules（20 项）

| # | 条件 |
|---|---|
| 1 | 改 v1 `scripts/run_continuous_smoothing_validation.py` |
| 2 | 改 v1 `scripts/run_real_continuous_smoothing_validation_execute.py` |
| 3 | 改 v1 `services/continuous_smoothing_candidate.py` |
| 4 | 改 adapter / helper / wrapper / real provider / labels builder / candidate v2 任一已 merge 模块 |
| 5 | 改任何已 merge 测试 |
| 6 | monkey-patch `build_continuous_smoothing_candidate`（v1） |
| 7 | 跑 v1 然后改 candidate_name 字符串冒充 v2 |
| 8 | 让 v2 orchestrator import v1 orchestrator / v1 candidate / v1 glue |
| 9 | sweep / grid search / hyperparameter optimization |
| 10 | retry-until-pass |
| 11 | 用 v1 fail baseline 数据反推 v2 任何具体参数 |
| 12 | 进入 Step 3R-5 formula |
| 13 | 进入 Step 3R-6 simulator |
| 14 | 让 v2 pass 自动 promotion / 自动启 hard / Gate 5 / Gate 6 / `_PROTECTION_LAYER_CONNECTED` |
| 15 | 改 04 / 05 / 07 required |
| 16 | 触碰 2026 final-test range |
| 17 | commit raw output（v1 或 v2 的 `logs/regime_validation/<TS>/`） |
| 18 | 接 yfinance / requests / 任何网络 / trading API |
| 19 | 在本 checkpoint 阶段实现 v2 execution path（包括新增 4 个文件） |
| 20 | 在本 checkpoint 阶段触发 v2 real validation run |

## 13. 允许下一步

| # | 候选 | 状态 |
|---|---|---|
| 1 | **Step 3R-3.3F-C implementation**（在本 checkpoint 进 main 后启动） | ✅ 允许 |
| 2 | 只允许新增 §4 列出的 4 个文件 | ✅ 强制 |
| 3 | **不**改任何已有 v1 文件（v1 orchestrator / v1 glue / v1 candidate / wrapper / real provider / adapter / helper / labels builder / candidate v2 / 任何已 merge 测试） | ✅ 强制 |
| 4 | **不** monkey-patch / **不**跑 v1 冒充 v2 | ✅ 强制 |
| 5 | implementation 必须包含 focused tests + full pytest 零回归 | ✅ 强制 |
| 6 | tests **不**读真实 4 csv / W4 jsonl / DB / backup；**不**跑 639 rows；**不** import v1 任一公共 API | ✅ 强制 |
| 7 | implementation 完成后必须写 `tasks/step_3r3_f_c_v2_execution_path_implementation_checkpoint.md`（命名待定） | ✅ |
| 8 | **不**自动进入 single real run；real run 必须用户单独指令触发 | ✅ 强制 |
| 9 | hard / required upgrade / Gate 5 / Gate 6 / `_PROTECTION_LAYER_CONNECTED` | ❌ 永久封禁 |
| 10 | 直接进入 Step 3R-5 / 3R-6 | ❌ 永久封禁 |

## 14. 严守边界

本文是**纯 checkpoint markdown**：

- ❌ 没改任何代码（`services/*` / `ui/*` / `tests/*` / `scripts/*` 全部未触碰）
- ❌ 没改 DB schema / 没写 DB
- ❌ 没运行 replay
- ❌ 没**重新运行** real validation（baseline 仍是 v1 `20260507_065417` run；v2 尚未跑）
- ❌ 没运行 prepare-only smoke
- ❌ 没读 v1 4 个 raw output json 任一字节
- ❌ 没修改 v1 4 个 raw output json
- ❌ 没改 `run_predict` / `predict.py` / `scanner.py` / `prediction_store.py` / `app.py`
- ❌ 没改 `services/regime_features_builder.py` / `regime_labels_builder.py` / `regime_validation_helper.py` / `continuous_smoothing_candidate.py`（v1） / `continuous_smoothing_candidate_v2.py` / `replay_validation_record_adapter.py` / `historical_replay_training.py` / `real_regime_label_provider.py` / 任何 ui 模块 / 任何 builder
- ❌ 没改 `scripts/run_continuous_smoothing_validation.py`（v1 orchestrator）/ `run_real_continuous_smoothing_validation.py`（wrapper）/ `run_real_continuous_smoothing_validation_execute.py`（v1 glue）
- ❌ 没新增 v2 orchestrator / v2 execution glue / v2 任何测试任一 `.py` 文件
- ❌ 没改 v1 / v2 任一已 merge 测试
- ❌ 没改 04 / 05 / 07 任何 required 字段
- ❌ 没启用 `hard` / `forced_exclusion` / `anti_false_exclusion_triggered`
- ❌ 没接 `yfinance` / `requests` / 任何网络
- ❌ 没接 trading API / `longbridge` / `broker` / `paper_trade`
- ❌ 没让 `_PROTECTION_LAYER_CONNECTED` 翻 True
- ❌ 没让 `hard_gate_status.protection_layer_connected` 自动 pass
- ❌ 没改 `hard_exclusion_allowed` / `primary_blocker` 派生
- ❌ 没触碰 2026-01-01 之后 final-test range
- ❌ 没改 Step 3R-4 protocol thresholds（6 metric / 7 gate / 10 no-go）
- ❌ 没改 Step 3R-3.3 / 3R-3.3A / 3R-3.3B / 3R-3.3C 系列 / 3R-3.3C-D / 3R-3.3E / 3R-3.3F design / checkpoint / 3R-3.3F-A / 3R-3.3F-C design 已 merge 文档 / 实施
- ❌ 没改 Step 2G-8D / 8D.1A / 8D.2 / 8D.3 / 8D.4 文档或代码
- ❌ 没把 W4 / smoke / `logs/regime_validation/` / v1 raw output / `logs/prediction_log.jsonl` / DB backup / `agent_loop.py` / `.claude/worktrees/` 任一 commit 进 main
- ❌ 没创建任何**新的** `logs/regime_validation/*` 子目录
- ❌ 没运行 `pytest`（本轮纯文档；测试基线维持 commit `ce8b81e` 时的 **2937 / 0 failed / 10 skipped**）
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*`
- ❌ 没 monkey-patch
- ❌ 没让 v2 orchestrator import v1 orchestrator / v1 candidate / v1 glue
- ❌ 没跑 v1 冒充 v2
- ❌ 没用 v1 baseline 数据反推 v2 具体参数
- ❌ 没让 design 自动 promotion / 自动解锁 3R-5 / 3R-6
- ❌ 没实现 v2 execution path
- ❌ 没真实运行 v2 W1-W4 validation
- ✅ 只新增 1 份 markdown checkpoint 文档（本文件）
