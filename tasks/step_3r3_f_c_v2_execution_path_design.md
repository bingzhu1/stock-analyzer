# Step 3R-3.3F-C — V2 Execution Path Design

> 本文是 **design only** —— 不改代码、不写 DB、不重跑 replay / validation、不 commit / push、不接 trading API、不启 hard / forced、不改 required、不触碰 2026 final-test range、不 add `logs/regime_validation/` / W4 / smoke output / `logs/prediction_log.jsonl`、不处理 DB backup / stash / `.claude/worktrees/`、不调 v1 `candidate_threshold` / SEED coefficients / 6 metric / 7 gate threshold、不实现脚本、不改 v1 orchestrator / v1 execution glue / adapter / helper、不 monkey patch、不跑 v1 冒充 v2、不进 3R-5 / 3R-6 / 不自动 promotion。

## 1. 背景

| 项 | 状态 | 来源 |
|---|---|---|
| v1 real W1-W4 validation single run + result checkpoint | ✅ 已 merge | output `logs/regime_validation/continuous_smoothing_v1_real_w1_w4_20260507_065417/`；commit `75f0ad5` |
| v1 postmortem report | ✅ 已 merge | commit `fc44bcf` |
| v2 launch review design + checkpoint | ✅ 已 merge | commits `4fd1278` / `7c1a0e5` |
| v2 candidate design + checkpoint | ✅ 已 merge | commits `b16fce9` / `7eda5b4` |
| v2 implementation + checkpoint | ✅ 已 merge | commits `ce8b81e` / `95ded24` |
| **v2 single real validation pre-flight**（attempted） | ❌ **STOP**，blocker 命中 | 本步骤前一轮 |
| 停止原因 | `scripts/run_continuous_smoothing_validation.py:45-46` 硬 `import build_continuous_smoothing_candidate`（v1）；orchestrator 无 candidate-factory 注入参数 | 文件证据 |
| **本文**（v2 execution path **design only**；不实现脚本、不跑 validation） | ⏳ design 中（未 commit） | — |

本文位置：

- 已 merge 链：v2 implementation checkpoint（`95ded24`）→ pre-flight STOP（无 commit；只是报告）→ **本 design** → design checkpoint → v2 execution path implementation + tests + checkpoint → v2 single real run（用户单独触发）→ v2 result checkpoint + v1 baseline comparison。
- 本文范围：**纯 markdown design**，不写脚本、不读真实 csv / DB、不修改 v1 / adapter / helper / wrapper / provider / glue / candidate v2 任一已 merge 模块。

## 2. blocker summary

### 2.1 主 blocker：orchestrator 硬 import v1

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

直接 implication：

- `run_continuous_smoothing_validation(...)` 公共 API **没有** candidate factory 参数；每行 row 进来都被 v1 硬调用。
- `scripts/run_real_continuous_smoothing_validation_execute.py` 只是把 row + provider + manifest 喂进 orchestrator，无法绕过 v1 candidate。

### 2.2 次级 blocker：execution glue threshold lock 0.60

`scripts/run_real_continuous_smoothing_validation_execute.py` `validate_execution_args(...)` 锁 `--candidate-threshold == 0.60`，非 0.60 → exit 2。即使 orchestrator 接受 v2，glue 也只接受 0.60。

> 注：v2 design 把 `risk_score = P̂(prediction wrong)` 锚定为 calibrated probability。`0.60` = "60% 置信此 prediction 会错才触发"，与 v1 share 数值但**语义不同**。这不是阻碍 v2 跑，但需要在 v2 glue 文档中明确"v2 的 0.60 阈值不是 v1 阈值"。

### 2.3 不能用的"hack"路径（与本设计冲突）

| Hack 方式 | 为什么不可 |
|---|---|
| 修改 v1 orchestrator 加 factory 参数 | 改已 merge 模块；本文明确禁止 |
| monkey-patch `build_continuous_smoothing_candidate` | 运行时改行为；与"不要临时 hack"冲突；不进 merge 链；不可复现 |
| 跑 v1 然后改 candidate_name 字符串 | 等价"跑 v1 冒充 v2"；明确禁止 |
| `regime_label_provider` 返回伪 candidate 骗过 orchestrator | 输出 schema 不对（labels vs candidate）；改语义 |
| 在 v2 模块中 import v1 orchestrator 然后 hot-reload candidate | 仍需修改 v1 模块或在运行时 patch；不可 |

### 2.4 不算 blocker 的次级观察（adapter / helper 已天然兼容 v2）

| 检查 | 状态 |
|---|---|
| `services/replay_validation_record_adapter.py:179-202` `_candidate_state(...)` | 是 **threshold-on-`risk_score`**；v2 `risk_bucket="abstain"` → `risk_score=None` → `candidate_unavailable` warning + `candidate_triggered=False` ✅ |
| v2 `final_test_refusal=True` → adapter `candidate_final_test_refusal` warning + `candidate_triggered=False` | ✅ |
| v2 `risk_score >= threshold` → `candidate_triggered=True` | ✅（与 v1 同源逻辑；adapter 不区分 v1/v2） |
| `services/regime_validation_helper.py` | 仅看 records；不知 v1/v2 | ✅ |
| → adapter / helper / wrapper / provider / labels builder / candidate v1 / candidate v2 | ✅ **不需改** |

## 3. design goal

| 目标 | 状态 |
|---|---|
| 新增 v2 专用 **orchestrator**（独立模块） | ✅ 核心目标 |
| 新增 v2 专用 **real execution glue**（独立模块） | ✅ 核心目标 |
| **不**改 v1 orchestrator (`scripts/run_continuous_smoothing_validation.py`) | ✅ 永久 invariant |
| **不**改 v1 execution glue (`scripts/run_real_continuous_smoothing_validation_execute.py`) | ✅ 永久 invariant |
| **不**改 adapter / helper（3R-4 protocol 锁定） | ✅ 永久 invariant |
| **不**改 wrapper (`scripts/run_real_continuous_smoothing_validation.py`) / real provider (`services/real_regime_label_provider.py`) | ✅ |
| **不**改 candidate v1 / candidate v2 / labels builder | ✅ |
| **不**改任何已 merge 测试 | ✅ |
| v2 path 可**独立**测试（mock heavy fns；不跑 639 rows；不读真实 4 csv / W4 jsonl） | ✅ |
| real validation 仍需用户**单独指令**触发 | ✅ 强制 |
| **不**写 DB / **不**触碰 2026 final-test range | ✅ 永久 invariant |
| **不**自动启 hard / Gate 5 / Gate 6 / `_PROTECTION_LAYER_CONNECTED` | ✅ 永久 invariant |
| v2 fail / pass 都**不**自动 promotion | ✅ 永久 invariant |

## 4. proposed files

后续 Step 3R-3.3F-C implementation 步骤新增（**本 design 不新增**）：

| # | 路径 | 类型 | 估算行数 |
|---|---|---|---|
| 1 | `scripts/run_continuous_smoothing_validation_v2.py` | 新增 v2 orchestrator | ~300（镜像 v1） |
| 2 | `scripts/run_real_continuous_smoothing_validation_execute_v2.py` | 新增 v2 execution glue | ~350（镜像 v1） |
| 3 | `tests/test_run_continuous_smoothing_validation_v2.py` | 新增 v2 orchestrator focused tests | ~600（mock candidate factory；不跑真实 639 rows） |
| 4 | `tests/test_run_real_continuous_smoothing_validation_execute_v2.py` | 新增 v2 glue focused tests | ~700（mock heavy fns） |

说明：

- ❌ 本 design **不**新增这 4 个文件
- ❌ 本 design **不**给具体行号 / 具体代码片段（避免与未来 implementation 不一致）
- ✅ 本 design **只**冻结 contract：API 形态、CLI、内部调用链、isolation 锁

## 5. v2 orchestrator design

### 5.1 定位

| 项 | 状态 |
|---|---|
| 文件 | `scripts/run_continuous_smoothing_validation_v2.py` |
| 是否生产主链 | ❌ 否（与 v1 一致；diagnostic library） |
| 是否 read-only | ✅ |
| 是否独立模块 | ✅（**不** import v1 orchestrator；可与 v1 共用 adapter / helper / wrapper / provider 这些 protocol 层） |
| 是否 import v1 candidate | ❌ **永久禁止**（与 candidate v2 isolation 一致） |

### 5.2 与 v1 orchestrator 的差异（**唯一三处**）

| # | 差异 | v1 | v2 |
|---|---|---|---|
| 1 | 候选 import | `from services.continuous_smoothing_candidate import build_continuous_smoothing_candidate` | `from services.continuous_smoothing_candidate_v2 import build_continuous_smoothing_candidate_v2` |
| 2 | candidate 调用 | `build_continuous_smoothing_candidate(labels, as_of_date=..., final_test_cutoff=...)` | `build_continuous_smoothing_candidate_v2(labels, as_of_date=..., final_test_cutoff=...)`（API 完全兼容） |
| 3 | adapter / helper / run_manifest 中的 `candidate_name` | `"continuous_smoothing_v1"` | `"continuous_smoothing_v2"` |

### 5.3 不变的部分（**绝大部分**）

- enriched row 结构（adapter 接受的 `row.candidate` 必须是 v2 输出 schema —— `continuous_smoothing_candidate_v2.v1`，包含 `risk_score` / `risk_bucket` / `final_test_refusal`）
- final-test cutoff 参数 `"2026-01-01"`（同 v1）
- adapter / helper 接口（**不**改）
- output 4 文件结构 + schema（与 v1 同；schemas 是 protocol 层）
- write_outputs flag / output_dir refusal-on-exists 行为
- `regime_label_provider` 接口（不变）
- `w4_manifest` 接口（不变）
- final_test_touched / report_status 计算逻辑（不变）

### 5.4 公共 API 草案（不实现）

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
) -> dict:
    ...
```

返回 dict shape 与 v1 同（`schema_version="continuous_smoothing_validation_run.v1"` 仍可复用，因为 schema 描述 run-level metadata，不是 candidate-level）。

> v1 / v2 orchestrator **不互相 import**；不要让 v2 调 v1 的私有 helper —— 镜像而非复用。

## 6. v2 execution glue design

### 6.1 定位

| 项 | 状态 |
|---|---|
| 文件 | `scripts/run_real_continuous_smoothing_validation_execute_v2.py` |
| 是否生产主链 | ❌ 否 |
| 是否 read-only | ✅ |
| 是否独立模块 | ✅（**不** import v1 execution glue） |

### 6.2 与 v1 glue 的关系

| 复用 | 镜像 / 替换 |
|---|---|
| ✅ 复用 `build_real_validation_inputs(...)`（wrapper；与 candidate 无关） | — |
| ✅ 复用 `build_real_regime_label_provider(...)`（real provider；与 candidate 无关） | — |
| ✅ 复用 `get_db_fingerprint` / `assert_db_unchanged`（generic DB guard） | — |
| ✅ 复用 backup count helper 名（在 v2 glue 内重新定义或 import；本 design 不强制） | — |
| ❌ **不** import / 调 v1 orchestrator | 改调 v2 orchestrator (§5) |
| ❌ **不** import v1 glue 的 `validate_execution_args` / `build_execution_summary` 等 | 在 v2 glue 内独立定义（lock semantic 在 v2 文档明确） |

### 6.3 execution flow（与 v1 glue 11 步对齐；唯一差异：第 7 步调 v2 orchestrator）

| # | 步骤 | v1 vs v2 差异 |
|---|---|---|
| 1 | validate args | v2 锁 `--run-once-real-validation-v2` flag（与 v1 不同名）；threshold / cutoff lock 同 v1 |
| 2 | DB fingerprint before | 同 v1 |
| 3 | market_data.db fingerprint before | 同 v1 |
| 4 | backup count before | 同 v1 |
| 5 | `build_real_validation_inputs(...)` | 同 v1（wrapper 复用） |
| 6 | `build_real_regime_label_provider(...)` | 同 v1（real provider 复用） |
| 7 | call orchestrator + write_outputs | **`run_continuous_smoothing_validation_v2(...)`**（替换 v1 orchestrator） |
| 8 | verify 4 output files | 同 v1（4 文件名相同；schema 相同） |
| 9 | DB fingerprint after + assert | 同 v1 |
| 10 | backup count after + assert | 同 v1 |
| 11 | return summary | summary `schema_version="real_validation_execution_summary_v2.v1"`（避免与 v1 summary 同 schema 引发歧义）；`candidate_name="continuous_smoothing_v2"` |

### 6.4 output_dir 命名

```
logs/regime_validation/continuous_smoothing_v2_real_w1_w4_<TS>/
```

`<TS>` = `YYYYMMDD_HHMMSS`；output_dir 必须不存在；orchestrator 内部 `_write_outputs_files(...)` 已经在 v1 实现（adapter 层无关），可被 v2 orchestrator 镜像复用语义（不 import v1 helper）。

> v2 output_dir 命名前缀 `continuous_smoothing_v2_*` 与 v1 `continuous_smoothing_v1_*` 在文件系统上**不冲突**；v2 跑完不会覆盖 v1 baseline。

## 7. threshold semantics

| 项 | v1 | v2 |
|---|---|---|
| `--candidate-threshold` 默认值 | `0.60`（lock；非 0.60 → exit 2） | `0.60`（**first run lock**；非 0.60 → exit 2） |
| 数值是否相同 | 是 | 是（happen-to-share 数值；语义不同） |
| 语义 | "overheat-style risk score" 高于 0.60 → exclude | **"calibrated P̂(prediction wrong)" 高于 0.60 → exclude** |
| 是否 sweep | ❌ | ❌（永久禁止） |
| 是否调参 | ❌ | ❌（first run 不能从 v1 fail baseline 反推） |
| 是否 retry | ❌ | ❌ |
| 文档要求 | v1 result checkpoint 已固定 | **v2 glue 必须在 docstring + checkpoint 明确**：v2 的 0.60 不是 v1 阈值；语义切换由 v2 candidate design 锁定（`risk_score = P̂(prediction wrong)`）|

> 目的：让 review reader 不会以为"v2 沿用 v1 threshold"。语义是新设计；数值碰巧相同是 first-run 默认。

## 8. adapter / helper compatibility

`services/replay_validation_record_adapter.py` 已天然兼容 v2（pre-flight 报告 §C 已确认）：

| v2 candidate 输出 | adapter 行为 |
|---|---|
| `risk_bucket="abstain"` + `risk_score=None` | `_candidate_state` warning `candidate_unavailable` + `candidate_triggered=False` |
| `final_test_refusal=True` | warning `candidate_final_test_refusal` + `candidate_triggered=False`；最终 records `final_test_refusal=True` |
| `risk_bucket ∈ {high, extreme}` 且 `risk_score >= threshold` | `candidate_triggered=True` |
| `risk_bucket ∈ {low, medium}` 且 `risk_score < threshold` | `candidate_triggered=False` |
| `risk_score=None`（缺数据） | `candidate_unavailable` + `candidate_triggered=False` |

`services/regime_validation_helper.py` 只看 records；不知 v1/v2；`candidate_name` 由 caller 传入。

| 是否需要改 adapter | ❌ 否 |
|---|---|
| 是否需要改 helper | ❌ 否 |
| 是否需要新 v2-specific adapter / helper | ❌ 否 |
| 是否需要新 schema | ❌ 否（adapter / helper / run_manifest schemas 与 candidate-level 无关） |

## 9. CLI design

v2 execution glue CLI 草案（v2 implementation 才落地；本 design 仅声明 contract）：

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `--run-once-real-validation-v2` | flag | ✅ | False | 不传 → exit 2 + refusal `missing_explicit_opt_in:--run-once-real-validation-v2 is required`（与 v1 flag 名**故意不同**：避免误用 v1 glue） |
| `--db-path` | str | ✅ | — | 同 v1 |
| `--w4-jsonl` | str | ✅ | — | 同 v1 |
| `--w4-manifest` | str | ✅ | — | 同 v1 |
| `--avgo-csv` / `--nvda-csv` / `--soxx-csv` / `--qqq-csv` | str | ✅ | — | 同 v1 |
| `--candidate-threshold` | float | ✅ | `0.60` | first run lock；非 0.60 → exit 2 |
| `--final-test-cutoff` | str | ✅ | `"2026-01-01"` | lock；非 cutoff → exit 2 |
| `--output-dir` | str | ✅ | — | 必须不存在；建议 `logs/regime_validation/continuous_smoothing_v2_real_w1_w4_<TS>` |

不存在的 flag（与 v1 glue 一致；argparse 自动 SystemExit）：

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

镜像 v1 orchestrator tests（`tests/test_run_continuous_smoothing_validation.py`）；唯一差异：测试调 v2 orchestrator + mock v2 candidate factory。

| 测试领域 | 范围 |
|---|---|
| top-level run dict + run_manifest schema | 同 v1 |
| candidate v2 被调用 / candidate attached to enriched rows | mock `build_continuous_smoothing_candidate_v2` 或注入小 fixture provider；**不**调真实 v2 candidate（也可调真实 v2 candidate 因为它是 pure read-only；选择留给 implementation） |
| adapter records produced + records_adapted matches | 同 v1 |
| 输入 rows + manifest 不被 mutate | 同 v1 |
| final-test row skipped（cutoff） | 同 v1 |
| `regime_label_provider` final_test_refusal propagates | 同 v1 |
| `candidate_threshold` 透传 adapter | 同 v1 |
| 无 threshold sweep | 字符串扫 + AST |
| `write_outputs` flag 行为 + 4 文件命名 | 同 v1 |
| 已存在 output_dir → `FileExistsError` | 同 v1 |
| `report_status` 镜像 helper 状态 | 同 v1 |
| isolation: **不** import v1 orchestrator / v1 candidate | ast.walk + 字符串扫双锁 |
| isolation: 同 v1 forbidden（DB / yfinance / streamlit / trading / prediction_store / hard / forced / required / final_direction / 等） | 标准列表 |

### 10.2 v2 execution glue focused tests（`tests/test_run_real_continuous_smoothing_validation_execute_v2.py`）

镜像 v1 glue tests（`tests/test_run_real_continuous_smoothing_validation_execute.py`）；调用关系替换为 v2。

| 测试领域 | 范围 |
|---|---|
| `get_backup_count` / `assert_backup_count_unchanged` | 同 v1 glue（可复用语义；本 design 不强制是否 import 还是镜像） |
| `validate_execution_args` lock | 缺 `--run-once-real-validation-v2` → exit 2；threshold ≠ 0.60 → exit 2；cutoff ≠ "2026-01-01" → exit 2；output_dir 已存在 → exit 2；缺必填 path → exit 2 |
| `build_execution_summary` shape | `schema_version="real_validation_execution_summary_v2.v1"`；`candidate_name="continuous_smoothing_v2"`；12 字段 |
| happy path（mocked） | mock `build_real_validation_inputs` / `build_real_regime_label_provider` / `run_continuous_smoothing_validation_v2`；orchestrator side-effect 写 4 fixture 文件到受控 tmp |
| 4 output files verify / 缺一 → RuntimeError | 同 v1 |
| DB / market_data / backup mismatch raises | 同 v1（受控 cwd） |
| CLI happy path（mocked） → exit 0 + JSON summary | 同 v1 |
| forbidden flags（argparse SystemExit） | 同 v1 |
| isolation: **不** import v1 orchestrator / v1 glue / v1 candidate | ast.walk + 字符串扫 |
| isolation: forbidden imports / 字符串扫（hard / forced / required / trading / sweep / `_PROTECTION_LAYER_CONNECTED`） | 同 v1 |

### 10.3 测试**不**做的事

- ❌ **不**读真实 4 csv（`data/AVGO.csv` / `NVDA.csv` / `SOXX.csv` / `QQQ.csv`）
- ❌ **不**读真实 W4 jsonl
- ❌ **不**跑 639 rows
- ❌ **不**连真实 `avgo_agent.db`（fixture sqlite 文件 + 受控 cwd）
- ❌ **不**触碰真实 `data/market_data.db`
- ❌ **不**触碰真实 `avgo_agent.db.backup_*`
- ❌ **不**真实运行 v2 validation
- ❌ **不** import v1 orchestrator / v1 candidate / v1 glue 任一公共 API

## 11. validation run plan

| # | 步骤 | 范围 |
|---|---|---|
| 1 | commit 本 design | 仅 markdown |
| 2 | v2 execution path **design checkpoint**（`tasks/step_3r3_f_c_v2_execution_path_design_checkpoint.md`） | 状态归档 |
| 3 | v2 execution path **implementation**（4 个新文件，§4） | merged 实现 + focused tests + full pytest 零回归 |
| 4 | v2 execution path **implementation checkpoint** | 状态归档 |
| 5 | **v2 single real validation run**（**用户单独指令触发**） | 同 cutoff `2026-01-01`；新 timestamp output_dir；同 DB / market_data / backup 三组 fingerprint 守护；4 文件 untracked；**不** commit raw json |
| 6 | **v2 result checkpoint** + **v1 baseline comparison** | per-window false_exclusion_rate / survival_case_preservation / trigger rate / cross_window_variance / gate_status v1 vs v2 |
| 7 | 根据 v2 result 决定下一步 review；**不**直接进 3R-5 / 3R-6；**不**自动 promotion | — |

> 本 design 范围只到第 1-2 步；3 之后是后续步骤。

## 12. no-go rules（20 项）

design + implementation + validation 全程 no-go：

| # | 条件 |
|---|---|
| 1 | 改 v1 `scripts/run_continuous_smoothing_validation.py`（v1 orchestrator） |
| 2 | 改 v1 `scripts/run_real_continuous_smoothing_validation_execute.py`（v1 execution glue） |
| 3 | 改 v1 `services/continuous_smoothing_candidate.py`（v1 candidate） |
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
| 19 | 在本 design 阶段实现 v2 execution path（包括新增 4 个文件） |
| 20 | 在本 design 阶段触发 v2 real validation run |

## 13. recommended_next_step

**`write_v2_execution_path_design_checkpoint`**

| 含义 | 状态 |
|---|---|
| 只允许进入 v2 execution path **design checkpoint**（独立 markdown） | ✅ |
| 允许直接进入 v2 execution path **implementation** | ❌ 否（必须先过 design checkpoint） |
| 允许直接进入 v2 **single real validation run** | ❌ 否（必须先过 implementation + checkpoint） |
| 允许直接进入 Step 3R-5 / 3R-6 | ❌ 否（必须先过 v2 result checkpoint + 新一轮 launch review） |
| 允许 v2 design 自动 promotion | ❌ 永远不 |
| 允许 v2 design 阶段提具体新阈值 / 新 calibration 曲线 | ❌ 永久禁止；具体参数 v2 candidate design 已锁（calibration_context not fitted） |

## 14. 严守边界

本文是**纯 design markdown**：

- ❌ 没改任何代码（`services/*` / `ui/*` / `tests/*` / `scripts/*` 全部未触碰）
- ❌ 没改 DB schema / 没写 DB
- ❌ 没运行 replay
- ❌ 没**重新运行** real validation（baseline 仍是 v1 `20260507_065417` run；v2 尚未跑）
- ❌ 没运行 prepare-only smoke
- ❌ 没读 v1 4 个 raw output json 任一字节
- ❌ 没修改 v1 4 个 raw output json
- ❌ 没改 `run_predict` / `predict.py` / `scanner.py` / `prediction_store.py` / `app.py`
- ❌ 没改 `services/regime_features_builder.py` / `regime_labels_builder.py` / `regime_validation_helper.py` / `continuous_smoothing_candidate.py`（v1）/ `continuous_smoothing_candidate_v2.py` / `replay_validation_record_adapter.py` / `historical_replay_training.py` / `real_regime_label_provider.py` / 任何 ui 模块 / 任何 builder
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
- ❌ 没改 Step 3R-3.3 / 3R-3.3A / 3R-3.3B / 3R-3.3C 系列 / 3R-3.3C-D / 3R-3.3E / 3R-3.3F design / checkpoint / 3R-3.3F-A 已 merge 文档 / 实施
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
- ✅ 只新增 1 份 markdown design 文档（本文件）
