# Step 3R-3.3C-C — Real Validation Execution Design

## 1. 背景
- Step 3R-3.3 4-fold validation run design + checkpoint 已 merge（commits `8a24295` / `2535467`）。
- Step 3R-3.3A dry-run validation orchestrator 已 merge（commit `32f196a`）；checkpoint `9fbd9b5`。
- Step 3R-3.3B limited-record smoke + checkpoint 已 merge（commit `d299247`）。
- Step 3R-3.3C real W1-W4 validation run design + checkpoint 已 merge（commits `226e354` / `d2773aa`）。
- Step 3R-3.3C-A W1-W3 source audit checkpoint 已 merge（commit `1280060`）。
- Step 3R-3.3C-B real validation input wrapper（implementation + checkpoint）已 merge（commits `23da6c9` / `a51ead8`）。
- Step 3R-3.3C-B1 prepare-only real input smoke checkpoint 已 merge（commit `bcf5eda`）。
- B1 smoke 已确认真实输入数量：W1-W3 = 286 / W4 = 353 / **total = 639**；DB 未变；warnings = []；w4_manifest_status = ok；output 未生成。
- 现在准备**设计** real validation execution（首个会真正驱动 candidate / adapter / helper 跑出 `regime_validation_report.v1` 的步骤）。
- 本文**只设计**，不实施、不执行：不改代码、不写 DB、不实际读 csv 行（仅引用文件路径）、不跑 validation。

## 2. execution 目标
- 使用 B1 已确认的 **639 真实 rows**（W1-W3 = 286 from `avgo_agent.db`，W4 = 353 from W4 jsonl）。
- 为每条 row 生成 `regime_labels.v1`（通过 real `regime_label_provider`，封装 3R-2 builder + 本地 csv DataFrame）。
- 为每条 row 生成 `continuous_smoothing_candidate.v1`（通过 3R-3.1 candidate generator）。
- 通过 3R-4.3A adapter 生成 `replay_validation_records.v1`。
- 通过 3R-4.2 helper 生成 `regime_validation_report.v1`。
- 写本地 4 文件 output 到独立 timestamp 目录（`logs/regime_validation/...`）。
- **不**写 DB。
- **不**进 main（output 全部 untracked）。
- **不**触碰 2026 final-test range。
- **不**自动启 hard / forced / `_PROTECTION_LAYER_CONNECTED`。
- **不**自动改 04 / 05 / 07 required。
- **不**作为 production gate；report `pass` 仅意味着 eligible for design review。

## 3. execution pipeline（8 步）

| # | 步骤 | 责任 |
|---|---|---|
| 1 | **DB fingerprints (before)** | wrapper 计算 `avgo_agent.db` + `data/market_data.db`（若存在）+ `avgo_agent.db.backup_*` 计数；持久化到 run_log / 内存供步骤 6 比对 |
| 2 | **build input bundle** | 复用 `build_real_validation_inputs(...)`（commit `23da6c9`）：DB W1-W3 reader + W4 jsonl loader + W4 manifest loader；产生 `real_validation_input_bundle.v1`（与 B1 smoke 一致） |
| 3 | **build real `regime_label_provider`** | 调 Step 3R-3.3C-C-B 实现的 real provider；初始化时一次性加载 `data/AVGO.csv` / `data/NVDA.csv` / `data/SOXX.csv` / `data/QQQ.csv` 为 DataFrame；返回 callable `(as_of_date, row) -> regime_labels.v1` |
| 4 | **run dry-run orchestrator** | 调 `run_continuous_smoothing_validation(...)`（commit `32f196a`）：传入 bundle 的合并 rows + real provider + bundle 的 W4 manifest dict + `candidate_threshold = 0.60` + `output_dir` + `write_outputs=True` |
| 5 | **write 4 output files** | orchestrator 在 `output_dir` 写：`replay_validation_records.json` / `regime_validation_report.json` / `regime_validation_summary.md` / `run_manifest.json`；`output_dir` 必须不存在（已存在 → orchestrator 抛 `FileExistsError`，与 3R-3.3A 一致） |
| 6 | **DB fingerprints (after)** | wrapper 再次计算同三组指纹；调 `assert_db_unchanged(...)`；任一变化 → run invalid，结果不可信 |
| 7 | **validate output schemas** | 校验 4 文件 schema：`real_validation_input_bundle.v1` / `replay_validation_records.v1` / `regime_validation_report.v1` / `regime_validation_run_manifest.v1` 字段齐 |
| 8 | **summarize report_status** | 读 report `overall_status` / `worst_window` / `gate_status` / `fail_reason`；写 result checkpoint；**不**根据结果调任何参数；**不**自动启 hard / 改 required；**不**自动进入 3R-5 / 3R-6 |

### 3.1 in-memory 流转
```
B1 wrapper (real DB + W4) ─┐
                           ├─► build_real_validation_inputs → bundle (639 rows)
real provider (3R-2)  ─────┘
                           │
                           ▼
                  run_continuous_smoothing_validation
                           │
                           ▼
              4 output files in output_dir (untracked)
                           │
                           ▼
              DB fingerprints rechecked → result checkpoint
```

## 4. real `regime_label_provider` design

### 4.1 接口
```python
def build_real_regime_label_provider(
    *,
    avgo_csv_path: str = "data/AVGO.csv",
    nvda_csv_path: str = "data/NVDA.csv",
    soxx_csv_path: str = "data/SOXX.csv",
    qqq_csv_path: str = "data/QQQ.csv",
    final_test_cutoff: str = "2026-01-01",
) -> Callable[[str, dict], dict]
```

返回 callable `provider(as_of_date, row) -> regime_labels.v1`。

### 4.2 行为
- 初始化时一次性 `pandas.read_csv` 4 个文件 → DataFrame；保留在 closure。
- 每个 DataFrame 必须含 `Date` 列；schema 与 `services/regime_labels_builder.py` 期望一致（`Date` / `High` / `Low` / `Close` / `Open` / `Volume`）。
- 调 `services.regime_labels_builder.build_regime_labels(avgo_df, peer_dfs={"NVDA": ..., "SOXX": ...}, market_dfs={"QQQ": ..., "SOXX": ...}, as_of_date=as_of_date, final_test_cutoff=final_test_cutoff)`。
- builder 内部已经强制 anti-lookahead（仅消费 `Date <= as_of_date` 的行），无需 wrapper 再过滤。
- builder 内部已经强制 final-test cutoff（`as_of_date >= cutoff` → `final_test_refusal=True` + 全 unknown）。

### 4.3 强约束
- **必须**用 `services.regime_labels_builder.build_regime_labels`；不允许重新实现 / 旁路 / 替换。
- **必须**只用 `Date <= as_of_date` 的行（builder 内置；wrapper 不做额外过滤）。
- **必须不**使用 W4 jsonl 中的 `pos20` / `five_state_projection` / `final_direction` / `direction_correct` / `actual_state` 等 future-leaking 或 outcome-leaking 字段反喂 candidate。
- **必须不**接 yfinance / requests / urllib / 任何网络。
- **必须不**通过 `services.prediction_store` / `services.outcome_capture` / DB 加载。
- **必须不**写 DB。
- **必须不**缓存到 DB / 写到 `logs/regime_validation/` 之外路径。
- 如果某 row `as_of_date` 在 csv 中找不到 → builder 返回 unknown labels + warning；row 在 adapter 阶段会因 candidate 缺失被 skip。
- 如果 csv 文件**任一**缺失 → provider 工厂应直接 raise `FileNotFoundError`（fail-fast，不静默）。
- provider 不读取 `predict_result_json` / `research_result_json` / `scan_result_json`。

### 4.4 mock-friendly 与 real provider 关系
- 现有 `build_static_regime_label_provider`（Step 3R-3.3C-B）保留为 fixture / dry-path 工具。
- real provider 是新增 helper（Step 3R-3.3C-C-B 范围），不替换 static 版本。
- 两者签名兼容：均返回 `Callable[[str, dict], dict]`。

## 5. market data source audit need
real provider 实施前必须先做**只读 audit**（Step 3R-3.3C-C-A）确认：

| audit 项 | 期望 |
|---|---|
| `data/AVGO.csv` 存在 | ✅ |
| `data/NVDA.csv` 存在 | ✅ |
| `data/SOXX.csv` 存在 | ✅ |
| `data/QQQ.csv` 存在 | ✅ |
| 每个 csv 含 `Date` / `Open` / `High` / `Low` / `Close` 列 | ✅ |
| 日期覆盖 `2023-01-03 - 60 trading days` ~ `2025-12-31`（足够 60-day market_trend window） | ✅ |
| 不含 ≥ `2026-01-01` 行（不会被强制读取，但 audit 也应记录） | （审查项） |
| 与 W4 jsonl 数据是否一致（spot check） | （审查项） |

**重要前置约束**：
- 当前**已知** `data/AVGO.csv` / `data/NVDA.csv` / `data/SOXX.csv` / `data/QQQ.csv` 在 main 工作树存在（B1 prepare-only smoke 阶段未涉及，仅作存在性确认）。
- 若 audit 发现任一 csv 缺失或字段不全 → real validation execution **永久 abort**，必须先补 csv 或重设计 provider。
- **不允许**实时下载 yfinance；**不允许**读 2026 行；**不允许**用其他 ticker 替代。

## 6. output_dir
设计：
```
logs/regime_validation/continuous_smoothing_v1_real_w1_w4_YYYYMMDD_HHMMSS/
```
`YYYYMMDD_HHMMSS` 由 execution glue 启动时生成（与 3R-3.3 §6 / 3R-3.3B smoke 一致）。

### 6.1 输出 4 文件
- `replay_validation_records.json`（`replay_validation_records.v1`）
- `regime_validation_report.json`（`regime_validation_report.v1`）
- `regime_validation_summary.md`（人读）
- `run_manifest.json`（`regime_validation_run_manifest.v1`）

### 6.2 处置规则
| 项 | 状态 |
|---|---|
| `output_dir` 必须**不存在**（已存在 → orchestrator 抛 `FileExistsError`） | ✅ |
| **不**进 main；本地 untracked | ✅ |
| **不**覆盖旧输出（timestamp 后缀确保独立） | ✅ |
| **不**写 DB | ✅ |
| **不**覆盖 W4 outputs（`logs/historical_training/three_system_w4_2024_08_2025_12/`） | ✅ |
| **不**覆盖 B1 smoke 旧目录 | ✅ |
| **不**写入 `logs/prediction_log.jsonl` | ✅ |
| **不** `git add` `logs/regime_validation/` 任何子目录 | ✅ |
| 可删除 / 可重跑（新 timestamp = 新目录） | ✅ |

## 7. DB guard
- run **前**记录：
  - `avgo_agent.db` mtime_ns + size_bytes（通过 `get_db_fingerprint`）
  - `data/market_data.db` mtime_ns + size_bytes（若存在）
  - `avgo_agent.db.backup_*` 文件计数（os.listdir + glob）
- run **后**再次记录上述三项。
- 调 `assert_db_unchanged(before, after)` 比较 mtime_ns + size_bytes（已实现于 wrapper，commit `23da6c9`）。
- 任一变化 → run invalid，**不**允许把结果作为后续设计依据：
  - mtime / size 变化
  - 新 `avgo_agent.db.backup_*` 出现
  - market_data.db mtime / size 变化
- DB guard 由 execution glue（Step 3R-3.3C-C-B）实现；orchestrator / candidate / adapter / helper / real provider 各层均 read-only（已锁定 isolation tests）。
- **禁止 import**（execution glue / real provider 任一层）：
  - `services.prediction_store`
  - `services.outcome_capture`（写路径）
  - `sqlite3` 写路径（real provider 完全不用 sqlite3）
  - `yfinance` / `requests` / `urllib3` / 任何 HTTP 客户端
  - `predict` / `scanner` / `streamlit` / `app`
  - `longbridge` / `broker` / `paper_trade` / 任何 trading API
- `sqlite3` `mode=ro` URI 读取**仅允许**在 wrapper 的 W1-W3 loader（已实现）；real provider / execution glue 不再单独连 DB。

## 8. final test guard（6 层 hard stop）
cutoff = `"2026-01-01"`（硬编码，不可变）。任一项触发 → run `report_status="error"` + run invalid：

| # | 检查 | 来源 |
|---|---|---|
| 1 | row `as_of_date >= cutoff` 或 `prediction_for_date >= cutoff` | wrapper DB SQL filter + wrapper W4 jsonl filter + orchestrator row filter + adapter G2 |
| 2 | W4 manifest `final_test_touched=true` | adapter + helper 双重 |
| 3 | `regime_labels.v1.final_test_refusal=true` | 3R-2 builder（real provider 透传） |
| 4 | `continuous_smoothing_candidate.v1.final_test_refusal=true` | 3R-3.1 candidate |
| 5 | `replay_validation_records.v1.final_test_refusal=true` | 3R-4.3A adapter |
| 6 | `regime_validation_report.v1.final_test_refusal=true` | 3R-4.2 helper |

补充：
- run_manifest `final_test_touched` must be `false`。
- run_manifest `final_test_cutoff` must be `"2026-01-01"`。
- report `final_test_refusal` must be `false`。
- market data csv 中 `Date >= cutoff` 行不会被强制读取，但 builder 已锁定 anti-lookahead；额外保险：execution glue 在 row enrich 阶段对 `as_of_date >= cutoff` 提前 skip + `final_test_touched=true`。
- 任一为 true → run abort，不允许进入下一步。

## 9. threshold policy
- `candidate_threshold = 0.60`（v1 design seed；与 3R-3.3 / 3R-3.3A / 3R-3.3B / 3R-3.3C 全链一致）。
- **不**扫 threshold（任何 sweep 必须独立 launch review）。
- **不**调 SEED coefficients（3R-3.1 模块常量）。
- **不**调 6 metric / 7 gate threshold（3R-4 protocol 锁定）。
- **不**根据 real run 结果反推 threshold。
- 若 first real run fail → **不**调参，按 §11 走回 design 层。
- 若 first real run pass → **不**自动启 hard / 不改 required；仅 eligible for design review。
- execution glue 必须**显式**传入 `candidate_threshold`；不允许默认 silent fallback override。

## 10. acceptance criteria
**first real run 不要求 pass。** `report_status` 可以 `pass` / `fail` / `error`，但必须**有可解释的原因**。

acceptance 是 plumbing 级别 + 数据完整性级别（13 项）：

| # | 标准 |
|---|---|
| 1 | output_dir 4 文件全部 exist |
| 2 | `records_loaded = 639`（与 B1 smoke total 一致）或低于 639 但有明确 skip warning（如 csv 中找不到 `as_of_date`） |
| 3 | `records_adapted > 0` |
| 4 | W1 / W2 / W3 / W4 **均**有 records（per-window 计数 > 0） |
| 5 | `regime_validation_report.v1` schema valid（14 字段齐） |
| 6 | `replay_validation_records.v1` schema valid（8 字段齐） |
| 7 | `regime_validation_run_manifest.v1` schema valid（12 字段齐） |
| 8 | `final_test_touched = false` |
| 9 | DB **未变**（mtime / size / backup count 全等） |
| 10 | output_dir untracked（git 无 tracked modified） |
| 11 | `worst_window` populated（W1-W4 之一） |
| 12 | `gate_status` populated（7 gate 全 present） |
| 13 | 没有 threshold sweep / 没有 hard / 没有 required 改动 |

## 11. legal fail outcomes
`report_status = "fail"` 是合法可接受的（与 3R-3.3 §10.1 一致）。可能 fail 的合法理由：

| 理由 | 是否合法 | 备注 |
|---|---|---|
| 某 fold `minimum_window_sample_size < 20`（candidate_triggered count 低） | ✅ | helper `GATE_MIN_WINDOW_SAMPLE = 20`；blocked count 取决于 candidate at threshold 0.60 触发频率 |
| 某 window `false_exclusion_rate > 0.10` | ✅ | candidate 在该 regime 误排不达预期 |
| 某 window `survival_case_preservation < 0.80` | ✅ | candidate 误伤 survival cases |
| `net_benefit < +0.05` | ✅ | candidate 未给出净收益 |
| `accuracy_delta_vs_baseline` 不达标 | ✅ | candidate 不优于 baseline |
| `cross_window_variance > 0.10` | ✅ | candidate 跨 window 行为不稳定 |
| `no_single_window_collapse` fail | ✅ | 单 window 出现严重崩溃 |

→ fail **不**等于 caller / orchestrator / wrapper / real provider / execution glue bug；fail **不**触发调参；fail 唯一允许的下游：回 candidate / threshold design 重新设计。fail 不影响 R4-like fixture acceptance test（始终 pass）。

## 12. no-go rules（13 项）
任意一项触发 → run abort + `report_status="error"` + result invalid：

| # | 条件 |
|---|---|
| 1 | 本地 market data 任一缺失（`data/AVGO.csv` / `NVDA.csv` / `SOXX.csv` / `QQQ.csv`） |
| 2 | 本地 csv 字段不全（缺 `Date` / `Open` / `High` / `Low` / `Close`） |
| 3 | provider 试图调 yfinance / requests / 任何网络 |
| 4 | provider 使用 future rows（builder anti-lookahead 失效，理论上不可能但 isolation test 锁定） |
| 5 | DB 在 run 期间被修改（mtime / size / backup count 任一变化） |
| 6 | 任一 row `as_of_date >= "2026-01-01"` 或 `prediction_for_date >= "2026-01-01"` 被 enrich |
| 7 | `output_dir` 已存在 |
| 8 | threshold swept（运行时 silent override） |
| 9 | SEED coefficients changed |
| 10 | report schema missing 必备字段 |
| 11 | hard / forced / required 任一被改 |
| 12 | 任一层 import 了 forbidden module |
| 13 | execution glue 调用 `_PROTECTION_LAYER_CONNECTED` 改写 / Gate 5 / Gate 6 自动 pass |

## 13. implementation sequence

| # | 子步骤 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **commit 本 design** | 把 §1-16 real validation execution 边界固化到 main | 本轮 / 下一轮 |
| 2 | **Step 3R-3.3C-C design checkpoint** | 状态归档 | 紧接其后 |
| 3 | **Step 3R-3.3C-C-A market data source audit** | 纯 read-only audit `data/AVGO.csv` / `NVDA.csv` / `SOXX.csv` / `QQQ.csv`：存在性 / 字段 / 日期范围 / 行数；产物 markdown audit checkpoint；**不**改代码 | 高（design + checkpoint 进 main 后） |
| 4 | **Step 3R-3.3C-C-B real `regime_label_provider` implementation** | 新增 `build_real_regime_label_provider(...)`（命名待定，可放 `scripts/run_real_continuous_smoothing_validation.py` 或新文件）+ focused tests（mock `pandas.read_csv` 或用 small csv fixture）；**不**跑 real validation；isolation tests 锁定 forbidden imports | 中（C-A 通过后） |
| 5 | **Step 3R-3.3C-C-C execution glue + single real run** | 串联 wrapper bundle + real provider + dry-run orchestrator；single run；output 本地 untracked；focused plumbing tests；DB guard 双 fingerprint | 中（C-B 进 main 后） |
| 6 | **Step 3R-3.3C result checkpoint** | 摘要 / report_status / per-window / fail_reason / DB guard verification 归档 | 中（C-C 完成后） |

## 14. 与 3R-5 / 3R-6 关系
- 即使 real report `overall_status="pass"` → **不**自动进入 3R-5 formula。
- 即使 real report `overall_status="pass"` → **不**自动进入 3R-6 simulator。
- pass 唯一允许的下游：进入 **design review** 讨论 3R-5 formula scope。
- fail **不**触发 threshold tuning / SEED 调整；fail 唯一允许的下游：回 candidate / threshold design 重新设计。
- 3R-5 / 3R-6 仍需**单独** launch review；3R-3.3C-C 不构成 implicit 授权。
- 不允许把 first real report 摘要直接当作 production gate。
- 不允许 report `pass` 自动启 hard / Gate 5 / Gate 6 / `_PROTECTION_LAYER_CONNECTED`。
- 不允许 report `pass` 自动改 04 / 05 / 07 required。

## 15. 禁止事项
| # | 禁止 | 理由 |
|---|---|---|
| 1 | **不**直接跑 real validation before §5 audit + §13 step 4 实施 | 防止 csv 缺失 / schema 错配 / lookahead |
| 2 | **不**接 yfinance / requests / 任何网络 | provider 仅本地 csv |
| 3 | **不**扫 threshold | 与 §9 一致 |
| 4 | **不**调 SEED coefficients | 模块常量；变更必须 launch review |
| 5 | **不**调 6 metric / 7 gate threshold | 3R-4 protocol 锁定 |
| 6 | **不**写 DB | 全程 read-only |
| 7 | **不**覆盖 W4 outputs | W4 不可变 baseline |
| 8 | **不**启 hard / forced / `anti_false_exclusion_triggered` | 三重 NO-GO |
| 9 | **不**改 04 / 05 / 07 required | Step 2G 全程边界 |
| 10 | **不**触碰 2026 final-test range | 6 层 hard stop |
| 11 | **不**接 trading（`longbridge` / `broker` / `paper_trade`） | 永久封禁 |
| 12 | **不**让 `_PROTECTION_LAYER_CONNECTED` 翻 True | 与 v1 / 3R-0 / 3R-4 一致 |
| 13 | **不**让 `hard_gate_status.protection_layer_connected` 自动 pass | 同上 |
| 14 | **不**改 `hard_exclusion_allowed` / `primary_blocker` 派生 | 同上 |
| 15 | **不**直接进入 formula（3R-5）/ simulator（3R-6） | 必须先过 result checkpoint |
| 16 | **不** commit validation outputs | `logs/regime_validation/` 全部 untracked |
| 17 | **不** import `services.prediction_store` / `services.outcome_capture` 写路径 / `yfinance` / `requests` / `predict` / `scanner` / `streamlit` 在 real provider / execution glue 任一层 | DB / 网络 / production isolation |
| 18 | **不**让 real provider 通过 future-leaking 字段（`pos20` / `five_state_projection` / `predict_result_json` / `direction_correct` / `actual_state` / `actual_close_change`）反喂 candidate | anti-lookahead |
| 19 | **不**在 first real run fail 时调任何参数 | 与 §10 / §11 一致 |
| 20 | **不**触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*` | 历史防护 |
| 21 | **不**重跑 W1-W3 replay | DB 已足够（audit 已锁定） |
| 22 | **不**用 first real run 数据反推 candidate_threshold | 阈值变更必须经 launch review |

## 16. 严守边界
本文是**纯 design markdown**：

- ❌ 没改任何代码（`services/*` / `ui/*` / `tests/*` / `scripts/*` 全部未触碰）
- ❌ 没改 DB schema
- ❌ 没写 DB
- ❌ 没运行 replay
- ❌ 没运行 real validation
- ❌ 没运行 prepare-only smoke（B1 已固化）
- ❌ 没读 `data/AVGO.csv` / `NVDA.csv` / `SOXX.csv` / `QQQ.csv` 行（仅引用文件路径）
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
- ❌ 没改 Step 3R-3.3 / 3R-3.3A / 3R-3.3B / 3R-3.3C / 3R-3.3C-A / 3R-3.3C-B / 3R-3.3C-B1 已 merge 文档 / 实施
- ❌ 没改 Step 2G-8D / 8D.1A / 8D.2 / 8D.3 / 8D.4 文档或代码
- ❌ 没把 W4 / smoke / `logs/regime_validation/` / `logs/prediction_log.jsonl` / DB backup / `agent_loop.py` / `.claude/worktrees/` 任一 commit 进 main
- ❌ 没创建任何新的 `logs/regime_validation/*` 子目录
- ❌ 没运行 `pytest`（本轮纯文档；测试基线维持 commit `23da6c9` 时的 2857 / 0 failed / 10 skipped）
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*`
- ✅ 只新增 1 份 markdown design 文档（本文件）
