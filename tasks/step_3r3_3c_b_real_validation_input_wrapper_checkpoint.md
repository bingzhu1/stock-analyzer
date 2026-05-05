# Step 3R-3.3C-B — Real Validation Input Wrapper Checkpoint

## 1. 当前完成状态
- Step 3R-3.3 4-fold validation run design + checkpoint 已 merge（commits `8a24295` / `2535467`）。
- Step 3R-3.3A dry-run validation orchestrator 已 merge（commit `32f196a`）；checkpoint `9fbd9b5`。
- Step 3R-3.3B limited-record smoke + checkpoint 已 merge（commit `d299247`）。
- Step 3R-3.3C real W1-W4 validation run design + checkpoint 已 merge（commits `226e354` / `d2773aa`）。
- Step 3R-3.3C-A W1-W3 source audit checkpoint 已 merge（commit `1280060`）。
- Step 3R-3.3C-B real W1-W4 validation **input wrapper implementation** 已完成并进入 main（commit `23da6c9`）。
- 本 checkpoint 用于固化：
  - wrapper public helpers（8 个）
  - DB read-only loader 行为 + filter
  - W4 jsonl loader 行为
  - W4 manifest loader 行为
  - DB fingerprint guard
  - prepare-inputs-only CLI dry guard
  - no real validation execution
  - 32 wrapper tests + 72 regression + 2857 full pytest 测试基线
  - 当前限制 + 允许下一步 + 禁止事项 + 边界
- **real W1-W4 validation 仍未运行。**
- **prepare-only real input smoke（Step 3R-3.3C-B1）仍未跑。**
- **real `regime_label_provider`（Step 3R-3.3C-C 范围）仍未实现。**
- 本轮**未** commit / push；**未**改代码；**未**写 DB；**未**跑 real validation。

## 2. 当前 main 状态
- main 最新 commit：`23da6c9`
- commit message：`feat(diagnostics): add real W1-W4 validation input wrapper`
- 上游：`origin/main` 已同步。
- full pytest：**2857 passed / 0 failed / 10 skipped / 26 warnings / 94 subtests**。
- 本步骤新增 / 修改文件（已 merge 到 main）：
  - `scripts/run_real_continuous_smoothing_validation.py`（新增；430 行；wrapper 公共 API + CLI）
  - `tests/test_run_real_continuous_smoothing_validation.py`（新增；32 focused tests，7 类）
  - `tasks/step_1_contract_pipeline_summary.md`（修改；新增 §42，11 小节）

| 项 | 是否触碰 |
|---|---|
| 改 production 主链（`predict.py` / `run_predict` / `scanner.py` / `prediction_store.py` / `app.py`） | ❌ 否 |
| 改 service / candidate / adapter / helper / labels builder | ❌ 否 |
| 写 DB | ❌ 否（wrapper 只用 `sqlite3.connect(file:..?mode=ro, uri=True)`） |
| 改 DB schema | ❌ 否 |
| 跑 replay | ❌ 否 |
| 跑 real validation | ❌ 否（CLI 只允许 `--prepare-inputs-only`，且 build_real_validation_inputs 不调用 orchestrator） |
| 接 yfinance / 网络 | ❌ 否 |
| 接 trading API | ❌ 否 |
| 触碰 2026 final-test | ❌ 否 |
| 启 hard / forced / `_PROTECTION_LAYER_CONNECTED` | ❌ 否 |
| 改 04 / 05 / 07 required | ❌ 否 |

## 3. Public helpers

| API | 责任 |
|---|---|
| `get_db_fingerprint(db_path)` | 返回 `{path, exists, mtime_ns, size_bytes}` |
| `assert_db_unchanged(before, after)` | mtime_ns / size_bytes 任一变化 → `RuntimeError` |
| `load_w1_w3_rows_from_db(db_path, *, final_test_cutoff="2026-01-01", symbol="AVGO")` | sqlite3 read-only loader；returns adapter-shaped rows |
| `load_w4_rows_from_jsonl(jsonl_path, *, final_test_cutoff="2026-01-01")` | 逐行读 jsonl；deepcopy 并 tag `source="w4_jsonl"` |
| `load_w4_manifest(path)` | 读 JSON 文件；非 dict raise `ValueError`；不做 schema 校验 |
| `build_static_regime_label_provider(*, regime_labels_template)` | mock-friendly callable factory；`provider(as_of_date, row)` 返回 deepcopy 模板，仅 set `as_of_date` / `data_cutoff_date` |
| `build_real_validation_inputs(*, db_path, w4_jsonl_path, w4_manifest_path, final_test_cutoff="2026-01-01", symbol="AVGO")` | 装配 `real_validation_input_bundle.v1`；**不**调用 orchestrator |
| `main(argv=None) -> int` | CLI entry；只支持 `--prepare-inputs-only` |

## 4. DB loader behavior
- 连接：`sqlite3.connect(f"file:{abs_path}?mode=ro", uri=True)`（强制只读）。
- 单条 SQL JOIN：`outcome_log.prediction_id = prediction_log.id`。
- filters（一次 SQL 完成）：
  - `prediction_log.symbol = ?`（默认 `'AVGO'`）
  - `outcome_log.direction_correct IS NOT NULL`
  - `prediction_log.analysis_date >= '2023-01-03'`
  - `prediction_log.analysis_date <= '2024-08-02'`（W1 起 → W3 末）
  - `prediction_log.analysis_date < final_test_cutoff`
  - `prediction_log.prediction_for_date < final_test_cutoff`
  - `prediction_log.prediction_for_date > prediction_log.analysis_date`（anti-lookahead）
- ORDER BY `prediction_log.analysis_date, prediction_log.prediction_for_date`。
- mapping（per row）：
  - `as_of_date` ← `prediction_log.analysis_date`（rename）
  - `prediction_for_date` ← `prediction_log.prediction_for_date`（direct）
  - `direction_correct` ← `bool(outcome_log.direction_correct)`（INT 0/1 → bool）
  - `actual_close_change` ← `float(outcome_log.actual_close_change)` 或 `None`
  - `ready` ← wrapper-side default `True`
  - `source` ← `"avgo_agent.db"`
- **不**映射 `actual_state`（adapter `_actual_direction` 在 `actual_state` 缺失时 fallback 到 `actual_close_change`）。
- **不**映射 `final_direction`（adapter 不读；DB `final_bias` 值集与 W4 不同，避免误用）。
- **不**读 `predict_result_json` / `research_result_json` / `scan_result_json`（防止 future-leaking 字段反喂 candidate）。
- **不**写 DB；**不**执行 INSERT / UPDATE / DELETE / DDL。

## 5. W4 loader behavior
- 输入：jsonl 文件路径。
- 逐行 `json.loads`。
- 跳过空行（strip 后为空）。
- 跳过非 dict 行。
- 跳过 `as_of_date >= cutoff`（final-test 区间）。
- 跳过 `prediction_for_date >= cutoff`。
- 原字段 deepcopy 保留（`actual_state` / `direction_correct` / `final_direction` / 全部 W4 schema 字段不被 wrapper 修改）。
- 添加 `source = "w4_jsonl"`。
- **不**修改原 jsonl 文件。
- **不**读取 W4 manifest（manifest 由 `load_w4_manifest` 单独读）。

## 6. W4 manifest loader
- 输入：manifest JSON 文件路径。
- `json.load` → dict。
- 非 dict（如 JSON array / number / string）→ `ValueError`。
- **不**做 8 项 schema 校验（与 `w4_replay_manifest.v1` 一致的 schema 检查交给 adapter / helper 内置 W4 manifest gate）。
- **不**修改文件。

## 7. DB guard
- `get_db_fingerprint(db_path)` 输出 4 字段：
  - `path` (str)：原始路径
  - `exists` (bool)：文件是否存在
  - `mtime_ns` (int | None)：修改时间纳秒（不存在 → `None`）
  - `size_bytes` (int | None)：字节数（不存在 → `None`）
- `assert_db_unchanged(before, after)`：
  - `mtime_ns` 不一致 → `RuntimeError("db_modified:mtime_ns_changed:...")`
  - `size_bytes` 不一致 → `RuntimeError("db_modified:size_bytes_changed:...")`
  - `path` / `exists` 字段不参与对比（仅供调试展示）
- 测试覆盖：
  - 文件不存在 → `exists=False` + `mtime_ns/size_bytes` 为 `None`
  - 等指纹 pass / mtime 变化 raise / size 变化 raise
  - DB loader 调用前后 fingerprint 一致（`test_does_not_modify_db`）
  - `build_real_validation_inputs` 调用前后 fingerprint 一致
  - CLI `--prepare-inputs-only` 二次调用后 fingerprint 一致

## 8. CLI dry guard
| 行为 | 状态 |
|---|---|
| `argv=[]`（无任何 flag） → exit code 2 + stderr 提示 `--prepare-inputs-only` | ✅ |
| `--prepare-inputs-only` 但缺 `--db-path` / `--w4-jsonl` / `--w4-manifest` → exit code 2 + stderr 列出缺失项 | ✅ |
| `--prepare-inputs-only` + 三路径全到位 → exit code 0 + stdout JSON summary | ✅ |
| **没有** `--run-real-validation` flag | ✅；real execution 不在本轮范围 |
| CLI 不创建任何文件（不写 logs / output_dir） | ✅；只 stdout |
| CLI 不修改 DB | ✅（test_prepare_only_succeeds 中二次执行验证 fingerprint 不变） |
| CLI 不调用 dry-run orchestrator | ✅（`build_real_validation_inputs` 不 import / 不 reference `scripts.run_continuous_smoothing_validation`） |

stdout JSON summary 字段：
- `schema_version` = `"real_validation_input_bundle.v1"`
- `db_path`
- `db_fingerprint`
- `w1_w3_row_count`
- `w4_jsonl_path`
- `w4_row_count`
- `w4_manifest_path`
- `w4_manifest_status`（`"ok"` / `"error"`，surface check）
- `final_test_cutoff`
- `warnings`（list[str]）

## 9. no real validation run
- wrapper **不**导入 `scripts.run_continuous_smoothing_validation`。
- wrapper **不**导入 / 调用 `services.regime_validation_helper` 直接执行 helper。
- wrapper **不**调用 `services.replay_validation_record_adapter.build_replay_validation_records`。
- wrapper **不**调用 `services.continuous_smoothing_candidate.build_continuous_smoothing_candidate`。
- `build_real_validation_inputs` 返回的 bundle **不**含 orchestrator 输出键：
  - 不含 `records_loaded`
  - 不含 `records_adapted`
  - 不含 `report_status`
  - 不含 `regime_validation_report`
  - 不含 `replay_validation_records`
  - 不含 `run_manifest`
- bundle 只含 input + fingerprint + surface w4_manifest_status + warnings。
- real execution 推迟到 Step 3R-3.3C-C，必须独立 launch review。
- isolation 静态测试（`ast.walk` + 字符串）锁定上述边界。

## 10. 测试覆盖
| 命令 | 结果 |
|---|---|
| `pytest tests/test_run_real_continuous_smoothing_validation.py -q` | **32 passed** |
| `pytest tests/test_run_continuous_smoothing_validation.py tests/test_replay_validation_record_adapter.py -q` | **72 passed**（零回归） |
| `pytest -q`（全量） | **2857 passed / 10 skipped / 0 failed / 26 warnings / 94 subtests** |

测试基线累积：Step 3R-3.3A 终点 2825 → Step 3R-3.3C-B 终点 **2857**（+32 净增；2825 基线零回归）。

32 wrapper tests 7 类覆盖：
| 测试类 | 数量 | 覆盖点 |
|---|---|---|
| `FingerprintTests` | 2 | 文件不存在 / 文件存在 |
| `AssertDbUnchangedTests` | 3 | 等指纹 pass / mtime 变化 raise / size 变化 raise |
| `LoadW1W3RowsFromDbTests` | 6 | 仅 W1-W3 AVGO paired / 字段齐 / int→bool / DB 不变 / 2026 过滤 / lookahead 过滤 |
| `LoadW4RowsFromJsonlTests` | 4 | 2026 过滤 / source 标签 / 原字段保留 / 空行容忍 |
| `LoadW4ManifestTests` | 2 | 正常 dict / 非对象 raise |
| `StaticRegimeLabelProviderTests` | 2 | regime_labels.v1 shape / template 不被 mutate |
| `BuildRealValidationInputsTests` | 5 | bundle shape / DB+W4 合并 / 不调 orchestrator / DB 不变 / w4_manifest_status warnings |
| `CliTests` | 3 | 无 flag exit nonzero / 缺 args exit nonzero / prepare-only 成功 + DB 不变 |
| `IsolationTests` | 5 | 23 项 forbidden import 锁定 / hard / required 字符串锁定 / threshold sweep 字符串锁定 / 不调 orchestrator / sqlite3 仅 read-only 模式 |

## 11. 当前限制
- 还没用真实 `avgo_agent.db` + 真实 W4 paths 做 prepare-only 实测（CLI 只在 temp fixture 上 smoke 过）。
- 还没跑 real W1-W4 validation。
- 还没实现 real `regime_label_provider`（封装 3R-2 builder + 本地 csv DataFrame 加载）。
- `build_static_regime_label_provider` 仅作 mock / dry path 占位；不接 market data。
- 还没产出 real `regime_validation_report.v1`。
- 还没扫 candidate_threshold（永久封禁；仅作记录）。
- 还没把任何 validation output 进 main（永久封禁；仅作记录）。

## 12. 允许下一步
| # | 候选 | 状态 |
|---|---|---|
| 1 | **Step 3R-3.3C-B1 prepare-only real input smoke** | ✅ 允许（在本 checkpoint 进入 main 后启动） |
| 2 | smoke 范围 | 调用 wrapper CLI `--prepare-inputs-only`，输入真实 `avgo_agent.db` + 真实 W4 jsonl + 真实 W4 manifest |
| 3 | smoke 期望输出 | stdout 一份 JSON summary（含 db_fingerprint / w1_w3_row_count / w4_row_count / w4_manifest_status / warnings） |
| 4 | smoke acceptance | exit code 0；DB fingerprint 前后一致；不创建任何文件；row counts 与 audit 数字一致（W1=110 / W2=93 / W3=83 → 合计 286；W4 ≤ 353） |
| 5 | smoke 仍**不**跑 validation | ✅ |
| 6 | smoke 仍**不**写 DB | ✅ |
| 7 | smoke output **不**进 main（仅作 checkpoint 引用） | ✅ |
| 8 | wrapper / candidate / adapter / helper / orchestrator / labels builder 现有行为 | ❌ 不改（仅只读调用） |
| 9 | hard / required upgrade / Gate 5 / Gate 6 / `_PROTECTION_LAYER_CONNECTED` | ❌ 永久封禁 |

## 13. 禁止事项
| # | 禁止 | 理由 |
|---|---|---|
| 1 | **不**跑 real validation | 必须先过 prepare-only smoke + 3R-3.3C-C design |
| 2 | **不**写 DB | wrapper 全程 read-only |
| 3 | **不**扫 threshold | v1 seed 0.60 锁定 |
| 4 | **不**调 SEED coefficients | 模块常量 |
| 5 | **不**调 6 metric / 7 gate threshold | 3R-4 protocol 锁定 |
| 6 | **不**启 hard / forced / `anti_false_exclusion_triggered` | 三重 NO-GO |
| 7 | **不**改 04 / 05 / 07 required | Step 2G 全程边界 |
| 8 | **不**接 trading（`longbridge` / `broker` / `paper_trade`） | 永久封禁 |
| 9 | **不**触碰 2026 final-test range | 6 层 hard stop |
| 10 | **不** commit validation outputs | 与 3R-3.3 §6.2 一致 |
| 11 | **不**直接进入 formula（3R-5）/ simulator（3R-6） | 必须先过 result checkpoint |
| 12 | **不**让 `_PROTECTION_LAYER_CONNECTED` 翻 True | 与 v1 / 3R-0 / 3R-4 一致 |
| 13 | **不**让 `hard_gate_status.protection_layer_connected` 自动 pass | 同上 |
| 14 | **不**改 `hard_exclusion_allowed` / `primary_blocker` 派生 | 同上 |
| 15 | **不**让 wrapper 通过 `predict_result_json` 反推 candidate | anti-lookahead |
| 16 | **不**让 wrapper import `services.prediction_store` / `services.outcome_capture` 写路径 / `yfinance` / `requests` / `predict` / `scanner` / `streamlit` | DB / 网络 / production isolation（`ast.walk` 锁定） |
| 17 | **不**让 wrapper import `scripts.run_continuous_smoothing_validation` | 防止 implicit real run（静态字符串 + `ast.walk` 锁定） |
| 18 | **不**触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*` | 历史防护 |
| 19 | **不**把 `logs/regime_validation/` 任何子目录 `git add` | 与 3R-3.3 §6.2 一致 |
| 20 | **不**在 first real run fail 时调任何参数 | 与 3R-3.3 §10.1 一致 |

## 14. 下一步建议

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **commit 本 checkpoint** | 把 §1-15 wrapper 边界 + 测试基线 + 限制固化到 main | 本轮 / 下一轮 |
| 2 | **Step 3R-3.3C-B1 prepare-only real input smoke** | 用真实 `avgo_agent.db` + W4 paths 跑 wrapper CLI；只输出 summary；不跑 validation；不写 DB | 高（本 checkpoint 进 main 后） |
| 3 | **Step 3R-3.3C-B1 checkpoint** | 状态归档（smoke 摘要 + DB 指纹 + row counts 与 audit 对比） | 紧接其后 |
| 4 | **Step 3R-3.3C-C real validation execution design** | 设计 real `regime_label_provider` + real run wrapper；不跑 | 中（B1 通过后） |
| 5 | **Step 3R-3.3C-C execution + result checkpoint** | 单次本地跑真实 W1-W4；output 本地 untracked；摘要归档 | 中（C-design 通过后） |
| 6 | **不推荐**直接 Step 3R-5 formula | 必须先过 result checkpoint | ❌ |
| 7 | **不推荐** Step 3R-6 simulator | 必须先过 3R-5 design | ❌ |
| 8 | **不推荐**让 first real run pass 自动启 hard / Gate 5 / Gate 6 | 与 3R-3.3 §11 一致 | ❌ |
| 9 | **不推荐**升级 04 required | Step 2G 全程边界 | ❌ |
| 10 | **不推荐**触碰 2026 final-test range | 永久封禁 | ❌ |
| 11 | **不推荐**让 `_PROTECTION_LAYER_CONNECTED` 翻 True | 与 v1 / 3R-0 / 3R-4 一致 | ❌ |
| 12 | **不推荐**重跑 W1-W3 replay | DB 已足够（audit 已锁定） | ❌ |
| 13 | **不推荐**用 first real run 数据反推 candidate_threshold | 阈值变更必须经 launch review | ❌ |

**关键判断**：顺序 = 本 checkpoint → **3R-3.3C-B1 real input smoke**（首个用真实 paths 触摸 wrapper 的步）→ B1 checkpoint → 3R-3.3C-C design + execution → result checkpoint → 3R-5 formula → 3R-6 simulator。任何一步 fail → 整 candidate 报废，回到 design 层重新设计。

## 15. 严守边界
本文是**纯 checkpoint markdown**：

- ❌ 没改任何代码（`services/*` / `ui/*` / `tests/*` / `scripts/*` 全部未触碰）
- ❌ 没改 DB schema
- ❌ 没写 DB
- ❌ 没运行 replay
- ❌ 没运行 real validation
- ❌ 没运行 prepare-only smoke
- ❌ 没改 `run_predict` / `predict.py` / `scanner.py` / `prediction_store.py` / `app.py`
- ❌ 没改 `services/regime_features_builder.py` / `services/regime_labels_builder.py` / `services/regime_validation_helper.py` / `services/continuous_smoothing_candidate.py` / `services/replay_validation_record_adapter.py` / `services/historical_replay_training.py` / 任何 ui 模块 / 任何 builder
- ❌ 没改 `scripts/run_continuous_smoothing_validation.py` 或 `scripts/run_real_continuous_smoothing_validation.py`（已 merge 在 commit `23da6c9`）
- ❌ 没改 `tests/test_run_continuous_smoothing_validation.py` 或 `tests/test_run_real_continuous_smoothing_validation.py`（已 merge 在 commit `23da6c9`）
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
- ❌ 没改 Step 3R-3.3 / 3R-3.3A / 3R-3.3B / 3R-3.3C / 3R-3.3C-A / 3R-3.3C-B 已 merge 文档
- ❌ 没改 Step 2G-8D / 8D.1A / 8D.2 / 8D.3 / 8D.4 文档或代码
- ❌ 没把 W4 / smoke / `logs/regime_validation/` / `logs/prediction_log.jsonl` / DB backup / `agent_loop.py` / `.claude/worktrees/` 任一 commit 进 main
- ❌ 没运行 `pytest`（本轮纯文档；测试基线维持 commit `23da6c9` 时的 2857 / 0 failed / 10 skipped）
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*`
- ✅ 只新增 1 份 markdown checkpoint 文档（本文件）
