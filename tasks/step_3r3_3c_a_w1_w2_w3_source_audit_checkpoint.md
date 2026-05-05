# Step 3R-3.3C-A — W1/W2/W3 Source Audit Checkpoint

## 1. 当前完成状态
- Step 3R-3.3 4-fold validation run **design** 已完成并进入 main（commit `8a24295`）。
- Step 3R-3.3 4-fold validation run **checkpoint** 已完成并进入 main（commit `2535467`）。
- Step 3R-3.3A dry-run validation orchestrator 已完成并进入 main（commit `32f196a`）；checkpoint `9fbd9b5`。
- Step 3R-3.3B limited-record smoke + checkpoint 已完成并进入 main（commit `d299247`）。
- Step 3R-3.3C real W1-W4 validation run **design** 已完成并进入 main（commit `226e354`）。
- Step 3R-3.3C real W1-W4 validation run **checkpoint** 已完成并进入 main（commit `d2773aa`）。
- 本轮完成 **Step 3R-3.3C-A W1/W2/W3 source audit**（read-only）。
- 本 checkpoint 用于固化：候选 source 清单 / 各 source 统计 / DB verdict / schema mapping / final-test guard / 是否允许 real run / no-go。
- **real W1-W4 validation 仍未运行。**
- **wrapper（Step 3R-3.3C-B）仍未实现。**
- 本轮**未** commit / push；**未**改代码；**未**写 DB；**未**跑 validation。

## 2. 审查 source 清单
本轮 read-only 审查的候选 source：

| # | 路径 / 名称 | 类型 |
|---|---|---|
| 1 | `logs/historical_training/three_system_1005/` | jsonl + csv（three_system_replay schema） |
| 2 | `avgo_agent.db` `prediction_log` + `outcome_log` join | sqlite（read-only） |
| 3 | `logs/historical_training/03_fresh_replay/` | csv（pred_*/review_* schema） |
| 4 | `logs/historical_training/exclusion_action_validation_2e/` | summary json（rollup） |
| 5 | `logs/historical_training/exclusion_action_validation_2e_v2/` | summary json（rollup） |

W4（`logs/historical_training/three_system_w4_2024_08_2025_12/`）只作为 **schema reference**，不在本 audit 范围内重新审查（已在 8D.3 / 3R-3.3 中冻结：353 paired，schema 含 `as_of_date` / `prediction_for_date` / `direction_correct(bool)` / `actual_state` / `actual_close_change` / `final_direction`）。

## 3. source 统计表

| # | source | exists | total rows | W1 (2023-01-03→2023-08-31) | W2 (2023-09-01→2024-02-29) | W3 (2024-03-01→2024-08-02) | schema aligns w/ W4 | 2026 touched | verdict |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `three_system_1005/three_system_replay_results.jsonl` | ✅ | 5 | **0** | **0** | **0** | ✓ 同 W4 | ❌ **全部 5 行在 2026-04-21~27**（final-test 区间） | **UNUSABLE** |
| 2 | `avgo_agent.db` `prediction_log` ⨝ `outcome_log` | ✅ | 383 total / **288 paired** | **110 paired** | **93 paired** | **83 paired** | ✓（需 wrapper 轻量映射；详见 §7） | W1-W3 区间内 **0** 行；外围 2 行 paired 在 ≥2026-01-01（被 cutoff 过滤） | **USABLE**（W1-W3 首选 source） |
| 3 | `03_fresh_replay/predictions.csv` + `reviews.csv` | ✅ | 1006 / 1005 | **0** | **0** | **0** | ❌ schema 完全不同（`pred_01_date` ... `forced_predicted_state`；reviews 用 `prediction_date`/`actual_date`，无 `direction_correct` 字段） | ✗（覆盖 2016-07-01 → 2020-06-30） | **UNUSABLE** |
| 4 | `exclusion_action_validation_2e/exclusion_action_validation_summary.json` | ✅ | rollup only | n/a | n/a | n/a | ❌ 是聚合 stats（`overall.total_exclusion_actions=725`），原始 jsonl 路径指向 sibling worktree（`.claude/worktrees/beautiful-mcclintock-1dcda2/`，不在当前 repo） | n/a | **UNUSABLE** |
| 5 | `exclusion_action_validation_2e_v2/false_exclusion_validation_summary.json` | ✅ | rollup only | n/a | n/a | n/a | ❌ 同上（`false_total=165`；source CSV 在 `.claude/worktrees/eloquent-stonebraker-e0cd86/`） | n/a | **UNUSABLE** |

辅助验证（DB join sanity check）：
- W1 / W2 / W3 各 `prediction_for_date <= analysis_date` count = **0**（无 lookahead）。
- W1 / W2 / W3 各 `actual_close_change IS NOT NULL` count = **110 / 93 / 83**（与 paired count 完全一致）。
- DB 全表 `symbol='AVGO'` count = 383 / 383（仅 AVGO 单标的）。
- DB `created_at` 最早 = 2026-04-23，最晚 = 2026-05-04（retrospective replay-tagged 生成）。

## 4. DB source verdict
- **`avgo_agent.db` `prediction_log` ⨝ `outcome_log`** 是 W1 / W2 / W3 的**首选** source。
- **不需要**重跑 W1-W3 replay。
- 需要 wrapper（Step 3R-3.3C-B）做以下轻量映射（仅 read-only 转换，不修改 DB）：
  - `prediction_log.analysis_date` → row `as_of_date`（rename）
  - `prediction_log.prediction_for_date` → row `prediction_for_date`（direct）
  - `outcome_log.direction_correct` (INTEGER 0/1) → row `direction_correct` (bool)（`bool(int_value)`）
  - `outcome_log.actual_close_change` → row `actual_close_change`（direct）
  - `actual_state`：DB 无该列；adapter `_actual_direction` 在 `actual_state` 缺失时 fallback 到 `actual_close_change`，故可保留缺失（或由 wrapper 在严格模式下从 `actual_close_change` 推导）
  - `ready`：DB 无等价字段；wrapper 在 `direction_correct IS NOT NULL` 的 join 行上默认设 `True`
- 不允许 wrapper 写 DB。
- 不允许 wrapper import `services.prediction_store` / `sqlite3` 写路径 / `services.outcome_capture` 写路径。
- 允许 wrapper 用 `sqlite3` **read-only**（`uri=True` + `mode=ro` 或等价 readonly 模式）做 join 加载。

## 5. W1 / W2 / W3 sample sufficiency
- W1 paired = **110** ≥ helper `GATE_MIN_WINDOW_SAMPLE = 20`（`services/regime_validation_helper.py:57`） ✅
- W2 paired = **93** ≥ 20 ✅
- W3 paired = **83** ≥ 20 ✅

注意：
- helper 的 `minimum_window_sample_size` metric 实际计算的是 **blocked count**（candidate_triggered=True 的行），不是 paired total（参见 `services/regime_validation_helper.py:170`）。
- 因此 paired ≥ 20 仅是**必要前提**，不是充分条件；最终 gate 是否通过依赖 candidate at threshold 0.60 在每 window 触发的 blocked rows 数量。
- first real run 不要求 pass，故即使 helper gate fail 也不视为 wrapper 缺陷（与 3R-3.3 §10.1 / 3R-3.3C §9.1 一致）。

## 6. 2026 / final-test guard
- W1 / W2 / W3 区间内（`2023-01-03` ~ `2024-08-02`）DB paired count = 286；其中 `as_of_date >= 2026-01-01` 或 `prediction_for_date >= 2026-01-01` 的 = **0** ✅
- DB 全表（含 W4 之外的 retrospective predictions）`predictions_post_2026 = 3`，`paired_post_2026 = 2` —— 全部在 W1-W3 / W4 窗口之外，**会被 wrapper / orchestrator / adapter 三重 cutoff filter**。
- W4 jsonl post-2026 = 0（与 8D.3 已锁结果一致）。
- `three_system_1005` 全部 5 行 `as_of_date` 在 2026-04-21 ~ 2026-04-27 区间，是其 UNUSABLE 的根本原因之一（另一根本原因：W1/W2/W3 各 0 行）。
- final-test cutoff = `"2026-01-01"` 仍由 6 层 hard stop（design §9 / checkpoint §8）保证；本审查不修改任何 cutoff 行为。

## 7. Schema alignment（W4 jsonl ⇄ DB mapping）

| W4 jsonl row 字段 | DB 来源 | conversion / 说明 |
|---|---|---|
| `as_of_date` (str) | `prediction_log.analysis_date` (TEXT) | rename |
| `prediction_for_date` (str) | `prediction_log.prediction_for_date` (TEXT) | direct |
| `direction_correct` (bool) | `outcome_log.direction_correct` (INTEGER 0/1) | `bool(int_value)`（adapter 严格 require bool） |
| `actual_close_change` (float) | `outcome_log.actual_close_change` (REAL) | direct |
| `actual_state` (str, optional) | DB 无直接列 | adapter `_actual_direction` 在 actual_state 缺失时 fallback 到 actual_close_change；wrapper 可省略 |
| `final_direction` (str, optional) | `prediction_log.final_bias` (TEXT；值集 `bullish/bearish/neutral`，**不同于 W4 的 `偏多/偏空/震荡/中性`**) | adapter 不直接读 `final_direction`；diagnostics-only，不必映射 |
| `ready` (bool, optional) | 无等价列 | wrapper-side default `True`（仅在已 join `direction_correct IS NOT NULL` 的行上） |
| join key | `outcome_log.prediction_id = prediction_log.id` | join filter `direction_correct IS NOT NULL` |
| symbol filter | `prediction_log.symbol = 'AVGO'` | 当前 DB 全部 383 行均为 AVGO；filter 仍保留以防未来扩展 |

强约束：
- wrapper **不**读 `prediction_log.predict_result_json` / `research_result_json` / `scan_result_json` 来反推 candidate（防止 lookahead 通过 future-leaking 字段）。
- wrapper **不**调用 `services.continuous_smoothing_candidate` 之外的任何 candidate path（candidate 仅由 orchestrator 通过 3R-3.1 接口生成）。
- wrapper **不**把 `outcome_log` 中除 `direction_correct` / `actual_close_change` 之外的字段反喂 candidate。

## 8. DB integrity
- 整个 audit 使用 `sqlite3 -readonly` 模式查询；从未发出 INSERT / UPDATE / DELETE / DDL。
- `avgo_agent.db` mtime / size audit 前后不变：
  - mtime: `1777833249`
  - size: `11206656` bytes
- 没有新增 `avgo_agent.db.backup_*` 文件（仍是历史 7 个备份）。
- 无 tracked modified file（`git status` 工作树干净）。
- `data/market_data.db` 未被 audit 触碰（不在本审查范围）。
- `logs/prediction_log.jsonl` 未被读取或写入。

## 9. 是否允许 real run
- **❌ 不允许直接 real run。**
- ✅ 允许进入 **Step 3R-3.3C-B real run wrapper implementation**（在本 checkpoint 进入 main 后启动）。
- wrapper 必须满足：
  - read-only sqlite loader（uri/mode=ro）
  - W1/W2/W3 ⇄ DB schema mapping（per §7）
  - W4 jsonl + W4 manifest dict 加载器（jsonl 文件 IO + json 解析）
  - DB guard：run 前/后记录 `avgo_agent.db` mtime+size、`data/market_data.db` mtime+size、`avgo_agent.db.backup_*` 计数；任一变化 → run invalid（与 3R-3.3C design §8 / checkpoint §7 一致）
  - `regime_label_provider` 实现（封装 3R-2 builder + 本地 csv DataFrame，不接 yfinance）
  - focused tests（mock-based；仍**不**跑 real validation）
  - 不暴露 SEED / gate threshold / sweep 接口
  - 不 import `services.prediction_store` / `services.outcome_capture` / `yfinance` / `requests` / `predict` / `scanner` / `streamlit` / trading APIs
- wrapper 进 main + checkpoint 后，才允许 **Step 3R-3.3C-C real execution**（单次本地跑）。

## 10. no-go
本审查锁定的禁用项：

| # | no-go |
|---|---|
| 1 | 不用 `three_system_1005` 作 W1/W2/W3 source（5 行全部在 2026 final-test 区间） |
| 2 | 不用 `03_fresh_replay` 作 W1/W2/W3 source（schema 不一致 + 日期 2016-2020） |
| 3 | 不用 `exclusion_action_validation_2e` rollup 作 W1/W2/W3 source（无 paired rows，原始数据不在本 repo） |
| 4 | 不用 `exclusion_action_validation_2e_v2` rollup 作 W1/W2/W3 source（同上） |
| 5 | 不重跑 W1 / W2 / W3 replay（不在本步骤范围；如需必须另行 launch review） |
| 6 | 不直接 real validation（必须先过 wrapper 实施 + checkpoint） |
| 7 | 不写 DB（read-only audit；wrapper 也必须 read-only） |
| 8 | 不触碰 2026 final-test 区间（6 层 hard stop 保留） |
| 9 | 不扫 threshold（v1 seed 0.60 锁定） |
| 10 | 不调 SEED coefficients（3R-3.1 模块常量） |
| 11 | 不启 hard / forced / `anti_false_exclusion_triggered` |
| 12 | 不改 04 / 05 / 07 required |
| 13 | 不让 `_PROTECTION_LAYER_CONNECTED` 翻 True |
| 14 | 不接 trading（`longbridge` / `broker` / `paper_trade`） |
| 15 | 不 commit `logs/regime_validation/` 任何子目录 |
| 16 | 不 commit DB backup / `agent_loop.py` / `.claude/worktrees/` / `logs/prediction_log.jsonl` |
| 17 | 不让 wrapper 通过 `predict_result_json` 反推 candidate（防 future-leak） |
| 18 | 不修改 helper minimum window gate / `GATE_MIN_WINDOW_SAMPLE` / 任何 protocol threshold |

## 11. 下一步建议

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **commit 本 audit checkpoint** | 把 §1-12 W1-W3 source 决策固化到 main | 本轮 / 下一轮 |
| 2 | **Step 3R-3.3C-B real run wrapper implementation** | 新增 wrapper 脚本（命名待定）+ DB read-only loader + schema mapping + DB guard + `regime_label_provider` + mock-based focused tests；仍**不**跑 real run | 高（本 checkpoint 进 main 后） |
| 3 | **Step 3R-3.3C-B wrapper checkpoint** | 状态归档（wrapper 进 main 后） | 紧接其后 |
| 4 | **Step 3R-3.3C-C real run execution** | 单次本地跑真实 W1-W4；output 本地 untracked | 中（wrapper checkpoint 进 main 后） |
| 5 | **Step 3R-3.3C result checkpoint** | 摘要 / report_status / per-window / fail_reason 归档 | 中（execution 完成后） |
| 6 | **不推荐**直接 Step 3R-5 formula design | 必须先过 result checkpoint | ❌ |
| 7 | **不推荐** Step 3R-6 simulator | 必须先过 3R-5 design | ❌ |
| 8 | **不推荐**让 report `pass` 自动启 hard / Gate 5 / Gate 6 | 与 3R-3.3 §11 一致 | ❌ |
| 9 | **不推荐**升级 04 required | Step 2G 全程边界 | ❌ |
| 10 | **不推荐**触碰 2026 final-test range | 永久封禁 | ❌ |
| 11 | **不推荐**让 `_PROTECTION_LAYER_CONNECTED` 翻 True | 与 v1 / 3R-0 / 3R-4 一致 | ❌ |
| 12 | **不推荐**重跑 W1-W3 replay | DB 已足够；如需另行 launch review | ❌ |
| 13 | **不推荐**用 first real run 数据反推 candidate_threshold | 阈值变更必须经 launch review | ❌ |

## 12. 严守边界
本文是**纯 audit checkpoint markdown**：

- ❌ 没改任何代码（`services/*` / `ui/*` / `tests/*` / `scripts/*` 全部未触碰）
- ❌ 没改 DB schema
- ❌ 没写 DB（全程 sqlite3 readonly）
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
- ❌ 没触碰 2026-01-01 之后 final-test range
- ❌ 没改 Step 3R-4 protocol thresholds（6 metric / 7 gate / 10 no-go）
- ❌ 没改 Step 3R-2 helper / 3R-3.1 candidate / 3R-4.2 helper / 3R-4.3A adapter 行为
- ❌ 没改 Step 3R-3.3 / 3R-3.3A / 3R-3.3B / 3R-3.3C 已 merge 的 design / checkpoint / 实施
- ❌ 没改 Step 2G-8D / 8D.1A / 8D.2 / 8D.3 / 8D.4 文档或代码
- ❌ 没把 W4 / smoke / validation 输出 commit 进 main
- ❌ 没新增任何 csv / jsonl / DB 文件
- ❌ 没运行 `pytest`
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*`
- ✅ 只新增 1 份 markdown audit checkpoint 文档（本文件）
