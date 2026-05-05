# Step 2G-8D.1 — Replay Script Audit

> **只读审查文档（replay script audit），不实现，不改代码，不写 DB，不运行 replay。**
> 本文档审查 `scripts/run_1005_three_system_replay.py` + 直接依赖
> （`services/historical_replay_training.py` /
> `services/outcome_capture.py` /
> `services/replay_record_wiring.py` /
> `services/three_system_replay_audit.py` /
> `services/projection_three_systems_renderer.py`）能否安全支持
> Step 2G-8D 锁定的 W4 = 2024-08-03 → 2025-12-31 replay；列出
> blocker / non-blocker 缺口与最小补丁建议。
>
> 本轮**不动任何代码**：不改 `predict.py` / `run_predict` /
> `scanner.py` / `prediction_store.py` / `app.py` / 任何 `ui/*` /
> `services/*` / 任何 builder / DB schema / 任何 test 中的任何一处。
>
> **本文不实现 patch、不跑 replay、不写 DB、不调 yfinance、不接
> trading API**；只在 markdown 层冻结 audit 结论，给后续 8D.1A
> minimal patch / 8D.2 tiny smoke / 8D.3 full W4 提供边界。

---

## 1. 当前完成状态

- **Step 2G-8D** extend replay coverage design + checkpoint 已完成并
  进入 main（commits `170617c` / `5eb725b`）
- **W4 范围已冻结**：start = 2024-08-03，end = 2025-12-31，
  `final_test_cutoff = 2026-01-01`
- **实施顺序已冻结**：8D checkpoint → 8D.1 audit（**本步骤**）→
  8D.2 tiny smoke → 8D.3 full W4 → 8D.4 W4 checkpoint → 3R-4.1
- **本步骤目标**：判断当前 replay script 能否（按现状或最小补丁后）
  安全进入 8D.2 tiny smoke
- **本步骤产物**：仅本 audit markdown；**不**改代码、**不**跑 replay、
  **不**写 DB、**不**调网络

---

## 2. 当前 main 状态

- main 最新 commit：**`5eb725b`**
- commit message：`docs(contract): Step 2G-8D extend replay coverage checkpoint`
- 上游：`origin/main` 已同步
- 测试基线：**2642 passed / 0 failed / 10 skipped / 26 warnings /
  94 subtests**（与 Step 3R-2 终点 commit `e2a681b` / `db7618b` 一致；
  本步骤无代码改动，无回归）

| 项 | 是否触碰 |
|---|---|
| 改代码 | ❌ 否 |
| 写 DB | ❌ 否 |
| 跑 replay | ❌ 否 |
| 接 yfinance / 网络 | ❌ 否 |
| 接 trading API | ❌ 否 |
| 触碰 2026 final test | ❌ 否 |
| 改 design / checkpoint / 3R-4 protocol | ❌ 否 |

---

## 3. 审查对象

只读读取的文件（路径相对仓库根；行数为审查时实测）：

| 路径 | 角色 |
|---|---|
| `scripts/run_1005_three_system_replay.py` | replay 入口 script；含 CLI / output writer / 可选 DB save |
| `services/historical_replay_training.py` | `run_historical_replay_for_date` / batch；3 步 chain：projection → outcome → review |
| `services/outcome_capture.py` | `capture_actual_outcome`；**直接调 yfinance** 拉 T+1 outcome |
| `services/replay_record_wiring.py` | `save_replay_batch_projection_records`；**仅在 `--save-records` 时调用**；写 sqlite |
| `services/three_system_replay_audit.py` | summary / per-case CSV row builders；纯 read-only |
| `services/projection_three_systems_renderer.py` | snapshot → three-system shape；纯 read-only |
| `tasks/step_2g8d_extend_replay_coverage_design.md` | W4 设计参考 |
| `tasks/step_2g8d_extend_replay_coverage_checkpoint.md` | W4 checkpoint 参考 |

未读 / 未深挖（read-only audit 不需要）：
`services/projection_orchestrator_v2.py` 全树、`services/prediction_store.py` 全树、
`scripts/save_projection_records_smoke.py` 全树。**这些都是间接依赖**，
本 audit 不修改。

---

## 4. 当前 script 能力

### 4.1 CLI 参数

| 参数 | 默认值 | 说明 |
|---|---|---|
| `--symbol` | `AVGO` | ticker；可改 |
| `--num-cases` | **`1005`** | **取 yfinance 拉到的最后 N+1 个 trading day 配对** |
| `--lookback-days` | `20` | projection 的回看窗 |
| `--output-dir` | `logs/historical_training/three_system_1005/` | 输出目录；**可改** |
| `--save-records` | **`False`** | 是否额外写 sqlite；**默认关** |
| `--db-path` | `data/market_data.db` | **仅在 `--save-records` 开启时**用；**不是** `avgo_agent.db` |

### 4.2 能力对比表

| 能力 | 现状 | 与 8D 设计契合度 |
|---|---|---|
| **自定义 start_date** | **❌ 否**（只有 `--num-cases`） | **✗ 缺** |
| **自定义 end_date** | **❌ 否**（隐式取 yfinance 最后一个 trading day） | **✗ 缺** |
| **自定义 output_dir** | ✅ 是（`--output-dir`） | ✓ |
| **dry-run / smoke** | **半支持**：`--num-cases 50` 可缩小到 50 case，但仍是"最后 50 day"，不能是"任意 5 day 区间" | ✗ 不能精确 smoke window |
| **写 main DB**（`avgo_agent.db`） | **❌ 否**（永远不写 main DB） | ✓ |
| **写其它 DB**（`data/market_data.db`） | **可选**：`--save-records` 开启时写 | ⚠ 需保证默认 OFF |
| **写 logs** | ✅ 写 `output_dir`；不写 `logs/prediction_log.jsonl`（main DB 路径） | ✓ |
| **覆盖旧输出** | ✅ 同 `output_dir` 同名文件**会覆盖**（W4 用独立目录可避） | ⚠ 必须独立目录 |
| **生成 manifest** | **❌ 否**（无 `validation_ready_manifest.json` 写入） | **✗ 缺** |
| **生成 regime_labels_snapshot** | **❌ 否**（不调 `services.regime_labels_builder.build_regime_labels`） | **✗ 缺** |
| **`final_test_cutoff` 参数** | **❌ 否**（无 2026 hard stop） | **✗ 缺** |
| **`predictions.csv` / `reviews.csv` 输出** | **❌ 否**（输出是 `three_system_replay_results.jsonl` + 6 个其它 CSV + summary.md / .json） | ⚠ 文件命名不一致；可在 design 接受层面接受 |
| **anti-lookahead 不变量** | ✅ 是（`historical_replay_training.py` 严格 3 步 chain：projection → outcome → review；projection 不见 outcome） | ✓ |

### 4.3 现有输出文件清单（默认 1005 模式）

写入 `output_dir/` 的文件：

| 文件 | 类型 |
|---|---|
| `three_system_replay_results.jsonl` | per-case 详细结构 |
| `three_system_replay_summary.md` | summary markdown |
| `three_system_replay_summary.json` | summary JSON |
| `negative_system_stats.csv` | per-case |
| `record_02_projection_stats.csv` | per-case |
| `confidence_evaluator_stats.csv` | per-case |
| `error_cases.csv` | filter |
| `false_exclusion_cases.csv` | filter |
| `high_confidence_wrong_cases.csv` | filter |

**与 8D 设计 §4.2 期望的差异**：

| 8D 设计建议输出 | 当前 script 是否生成 |
|---|---|
| `predictions.csv` | ❌ 不直接生成；语义最接近是 `record_02_projection_stats.csv` + `confidence_evaluator_stats.csv` |
| `reviews.csv` | ❌ 不直接生成；语义最接近是 `negative_system_stats.csv` + `false_exclusion_cases.csv` |
| `summary.md` | ⚠ 命名不同：实际是 `three_system_replay_summary.md` |
| `regime_labels_snapshot.csv` | **❌ 完全缺**；不调 `regime_labels_builder` |
| `validation_ready_manifest.json` | **❌ 完全缺** |

---

## 5. W4 安全性检查

逐项审查 W4 = 2024-08-03 → 2025-12-31：

### 5.1 能否设定 start=2024-08-03 / end=2025-12-31

| 项 | 答案 |
|---|---|
| 直接 CLI 设定 | **❌ 否**（无 `--start-date` / `--end-date`） |
| 间接通过 `--num-cases` | **可勉强**：今天 (2026-05-05) 起回退到 2024-08-03 ≈ 440 trading day；用 `--num-cases ≈ 440` 能拉到一部分 W4，但**会同时拉 2026 数据**（因 `_load_avgo_trading_days` 用 `period="10y"` + `dates[-N:]` 切尾） |
| **结论** | **必须打 patch 才能安全 W4**：加 `--start-date` / `--end-date` 显式过滤 |

### 5.2 是否会读取 2026 数据

| 数据流 | 是否会读 2026 |
|---|---|
| `_load_avgo_trading_days(period="10y")` | **会**：返回到今天（2026-05-05）的所有 trading day |
| `_build_date_pairs(days, num_cases=N)` | 切尾：`days[-(N+1):]` —— 当 `N` 足够大覆盖 2026 时，**会包含 2026 行** |
| `outcome_capture.capture_actual_outcome(symbol, prediction_for_date)` | **会**调 yfinance；如果 `prediction_for_date` 在 2026 → **会读 2026** |
| **结论** | **现状有越界风险**；必须在 query / loop **起点**预先过滤 `<= 2025-12-31` |

### 5.3 T+1 outcome 是否可能跨到 2026

| 边界 | 风险 |
|---|---|
| `as_of_date = 2025-12-31`（W4 上限） | **prediction_for_date 通常是 next trading day = 2026-01-02**（2026-01-01 是元旦休市） |
| `outcome_capture` 调 yfinance | **会拉 2026-01-02 的数据**（落入 final test 窗口） |
| **结论** | **必须 hard stop**：`as_of_date = 2025-12-31` 这一对的 T+1 outcome **不得读取**；即必须把 W4 paired 上界拉到 `prediction_for_date <= 2025-12-31`，意味着 `as_of_date` 实际上限是**最后一个 prediction_for_date 仍 ≤ 2025-12-31 的 trading day**（约 2025-12-30） |

### 5.4 是否会把结果写入 main DB

| 写法 | 是否触发 |
|---|---|
| 默认（`--save-records` 不开） | **❌ 不写任何 DB** |
| `--save-records` 开 + `--db-path data/market_data.db`（默认） | 写 `data/market_data.db`，**不是** `avgo_agent.db` |
| `--save-records` 开 + 用户**手动**传 `--db-path /Users/may/Desktop/stock-analyzer-main/avgo_agent.db` | **会写 main DB** —— **危险路径**，但需要用户主动指定 |
| **结论** | **W4 必须显式不传 `--save-records`**；强约束需要 patch（参见 §7） |

### 5.5 是否会覆盖 three_system_1005

| 项 | 风险 |
|---|---|
| 默认 `--output-dir = logs/historical_training/three_system_1005/` | 默认会覆盖 |
| 8D 设计 §4 推荐 `logs/historical_training/three_system_w4_2024_08_2025_12/` | **必须显式传**新目录 |
| **结论** | **不会自动覆盖**，但必须 W4 调用方显式传新 `--output-dir`；否则 1005 baseline 被覆盖 |

### 5.6 是否会使用 production prediction_store

| 项 | 答案 |
|---|---|
| `prediction_store.py` 调用 | 只在 `replay_record_wiring.py` 路径中（即 `--save-records` 开） |
| **结论** | **默认 OFF 时不调 prediction_store**；W4 调用必须保证 `--save-records=False` |

### 5.7 是否会触碰 logs/prediction_log.jsonl

| 项 | 答案 |
|---|---|
| `logs/prediction_log.jsonl` 路径 | **本 script 不写**；`logs/prediction_log.jsonl` 是 production `predict.py` 的 append 路径 |
| **结论** | ✅ 不触碰 |

### 5.8 是否调用 yfinance / 网络

| 调用点 | 是否需要网络 |
|---|---|
| `_load_avgo_trading_days(symbol, minimum_days)` | **是**：`yf.Ticker(symbol).history(period="10y")` |
| `services.outcome_capture.capture_actual_outcome` | **是**：`yf.Ticker(symbol).history(start=..., end=...)` |
| `services.projection_orchestrator_v2.run_projection_v2` | 可能（projection v2 链上是否调网络在本 audit 范围外；`coded_data/*` 大概率是本地 csv，但 projection chain 内部如有 yfinance 调用需 8D.1 追加深挖） |
| **结论** | **当前 1005 replay 在事实上调网络**（与 8D design §4.3 / §10 称"与现有 1005 replay 一致 offline"的论断**不一致**——这是 audit 关键发现） |

> **关键 audit 发现**：8D design §4.3 / §10 / 8D checkpoint §5
> 假设 1005 replay 是 "offline" —— 实际上 `_load_avgo_trading_days`
> 与 `outcome_capture.capture_actual_outcome` **都直接调 yfinance**。
> 这并**不破坏 W4 的 final test 安全性**（只要 cutoff 起点过滤
> 到 ≤ 2025-12-31），但要诚实记录："offline" 在 1005 script 实际
> 含义是"no broker / no automation / no live trading"，**不是**"no
> network"。design / checkpoint 中"用本地 csv"的描述需要在 8D.4 W4
> checkpoint 阶段更正或在 8D.1A patch 中切换为本地 csv 数据源。

---

## 6. 缺口清单

### 6.1 Blocker（必须在 8D.2 tiny smoke 前修）

| # | 缺口 | 后果 |
|---|---|---|
| **B1** | 无 `--start-date` / `--end-date` | 无法精确锁定 W4 范围；只能拉"最后 N day"，会带 2026 |
| **B2** | 无 `--final-test-cutoff` 参数 / **起点 hard stop** | 当 `_load_avgo_trading_days` 返回到 2026-05-05 时，**date list 含 2026 行**；不在起点过滤 → 越界风险 |
| **B3** | T+1 outcome 边界保护缺失 | `prediction_for_date` 在 2026 时**会**调 yfinance 读 2026 outcome；必须 skip |
| **B4** | 无 manifest writer（`w4_replay_manifest.v1`） | 无法证明 `final_test_touched=false`；无法供 3R-4 4-fold validation |
| **B5** | `--save-records` 在 W4 必须强制 False | 现状默认 OFF 但**没有 hard guard**：如果用户误传 `--db-path /Users/.../avgo_agent.db --save-records` → 写 main DB |

### 6.2 Non-blocker（可在 full W4 前修；smoke 可跳过）

| # | 缺口 | 后果 |
|---|---|---|
| **N1** | 不调 `regime_labels_builder` 生成 `regime_labels_snapshot.csv` | smoke / W4 完成后 4-fold validation 可在 8D.4 / 3R-4.1 阶段独立 batch 调用 helper 补 snapshot |
| **N2** | 输出文件名与 8D 设计不一致（`three_system_replay_summary.md` vs `summary.md`；无 `predictions.csv` / `reviews.csv`） | 8D.4 W4 checkpoint 可在 design 接受层面修正命名映射；或 8D.1A 加 alias / symlink；或 8D.4 写一层 view CSV |
| **N3** | 默认 `--num-cases=1005` 与"最后 N day"语义；与 W4 显式范围语义有歧义 | 8D.1A 加 `--start-date` / `--end-date` 后，`--num-cases` 改为 fallback / mutually-exclusive |
| **N4** | `_load_avgo_trading_days(period="10y")` 网络拉取每次都到今天 | 8D.1A 可改用 `coded_data/AVGO_coded.csv`（如果可用） |

### 6.3 Nice-to-have（可延后）

| # | 想要 | 后果 |
|---|---|---|
| **NH1** | dry-run mode：只打印 date pair list，不跑 projection | smoke 前更安心 |
| **NH2** | 进度条（tqdm）替换当前 `_log` 文本进度 | UX |
| **NH3** | 把 `output_dir` 已存在文件作为"resume" 而非覆盖 | UX |
| **NH4** | manifest 中追加 git commit hash + run timestamp | 可追溯性 |

---

## 7. 推荐最小改造（Step 2G-8D.1A）

> **本步骤只写建议；不改代码。** 实际 patch 由后续 8D.1A 步骤实施。

最小补丁（最小动作面，**仅**为支持 W4 + final test cutoff + manifest）：

### 7.1 新增 CLI 参数

| 参数 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `--start-date` | str (ISO) | None | 显式起点；与 `--num-cases` 互斥；起点过滤 |
| `--end-date` | str (ISO) | None | 显式终点；与 `--num-cases` 互斥；起点过滤 |
| `--final-test-cutoff` | str (ISO) | `"2026-01-01"` | hard stop；任何 `as_of_date >= cutoff` 或 `prediction_for_date >= cutoff` → skip |
| `--tiny-smoke` | flag | False | 起 smoke 模式：要求 `--start-date` + `--end-date` 必须都给；输出独立目录 |
| `--write-manifest` | flag | True (新默认) | 是否写 `validation_ready_manifest.json` |
| `--no-network-trading-days` | flag | False (默认沿用 yfinance) | 切到本地 csv（如 `coded_data/AVGO_coded.csv`）；**可选项** |

### 7.2 新增 hard guard（不可绕过）

| guard | 触发条件 | 行为 |
|---|---|---|
| **G1 cutoff at start** | `as_of_date_list = [d for d in available_dates if d < final_test_cutoff]`；起点过滤；**不允许"跑到 2026 再过滤"** | 起点过滤；任何越界 row 永不进入主循环 |
| **G2 prediction_for_date cutoff** | `if prediction_for_date >= final_test_cutoff: skip + warning` | T+1 边界 skip；不调 outcome fetcher |
| **G3 `--save-records` × W4 互斥** | 当 `--start-date >= "2024-08-03"` 时，`--save-records` 必须为 False | hard error；不允许 W4 写 DB |
| **G4 output_dir 防覆盖** | 当 W4 模式（`--start-date >= "2024-08-03"`）时，`--output-dir` 不能等于 `logs/historical_training/three_system_1005/` | hard error；防止覆盖 1005 baseline |
| **G5 manifest writer** | 写 `validation_ready_manifest.json`：`schema_version` / `replay_window` / `final_test_cutoff` / `final_test_touched=False` / `records_generated` / `paired_outcomes` / `status` / `warnings` | 一律写；status 默认 `"ok"`；任何 G1 / G2 越界 → `final_test_touched=True` + `status="error"` + 报告作废 |

### 7.3 不动的部分

| 部分 | 理由 |
|---|---|
| `services/historical_replay_training.py` | 已严格 3 步 chain（projection → outcome → review）；anti-lookahead 已正确；不动 |
| `services/outcome_capture.py` | yfinance 调用是 production 路径；不动；只在 W4 主循环**起点过滤** + G2 在 outcome fetch 前 skip |
| `services/replay_record_wiring.py` | 仅在 `--save-records` 时调；W4 G3 强制 OFF |
| `services/three_system_replay_audit.py` / `services/projection_three_systems_renderer.py` | read-only；不动 |
| `services/regime_labels_builder.py`（3R-2 helper） | **可在 8D.1A 内被 read-only 调用**生成 `regime_labels_snapshot.csv`；不改 helper 本身（helper 已 isolation 锁定） |

### 7.4 patch 边界

- 总改动面：**只**在 `scripts/run_1005_three_system_replay.py`（或新增 `scripts/run_w4_three_system_replay.py` thin wrapper）中加 ~ 60-100 行
- 不改 `services/*` 任何文件
- 不改 DB schema
- 不接 trading API
- 不写 main DB
- 不升级 04 / 05 / 07 required
- 不改 3R-4 protocol thresholds
- 不改 3R-2 helper 行为

---

## 8. 8D.2 tiny smoke 是否可以启动

### 8.1 现状直接启动？

**❌ NO**。理由：

1. 现状 `run_1005_three_system_replay.py` 没有 `--start-date` / `--end-date`，
   smoke window `2024-08-05 → 2024-08-09` 无法精确锁定
2. 没有 `--final-test-cutoff` hard stop；即使 smoke 5 day 不会越界，
   也无法在 manifest 中证明 cutoff 已生效
3. 没有 manifest writer；smoke 产物无法供 8D.4 / 3R-4.1 验证
4. `_load_avgo_trading_days(period="10y")` 仍会拉 yfinance 全 10 年，
   2024-08 范围包含在内，但 trim 逻辑是 `dates[-N:]` —— 强行用
   `--num-cases ≈ 5` 会拿到**最后 5 day**（2026 范围），**不是**
   smoke 期望的 2024-08

### 8.2 patch 后启动条件

**conditional GO**：先完成 **Step 2G-8D.1A minimal replay script patch**
（§7.1 + §7.2 五项 guard），然后用以下参数启动 8D.2 tiny smoke：

```
python -m scripts.run_1005_three_system_replay \
  --start-date 2024-08-05 \
  --end-date 2024-08-09 \
  --final-test-cutoff 2026-01-01 \
  --tiny-smoke \
  --output-dir logs/historical_training/three_system_w4_smoke_2024_08_05_2024_08_09/ \
  --write-manifest \
  # 不传 --save-records
  # 不传 --db-path
```

期望产物：
- `logs/historical_training/three_system_w4_smoke_2024_08_05_2024_08_09/predictions.csv`（或对应 1005 命名）
- `logs/historical_training/three_system_w4_smoke_2024_08_05_2024_08_09/reviews.csv`（或对应）
- `logs/historical_training/three_system_w4_smoke_2024_08_05_2024_08_09/summary.md`
- `logs/historical_training/three_system_w4_smoke_2024_08_05_2024_08_09/regime_labels_snapshot.csv`（如 8D.1A 接入 helper）
- `logs/historical_training/three_system_w4_smoke_2024_08_05_2024_08_09/validation_ready_manifest.json`
- 期望 paired ≈ 4（5 trading day 配 4 对）

---

## 9. tiny smoke 建议

| 项 | 值 |
|---|---|
| **smoke window** | **2024-08-05 → 2024-08-09**（5 trading day；W4 起点附近，避开 2024-08-03/04 周末） |
| **output_dir** | `logs/historical_training/three_system_w4_smoke_2024_08_05_2024_08_09/` |
| **manifest status** | 启动时 `"planned"`；运行成功 → `"ok"`；任何 G1/G2/G3/G4 触发 → `"error"` + `final_test_touched=true` + 整 smoke 作废 |
| **不写 DB** | ✅ 强制；G3 阻断 |
| **不覆盖旧目录** | ✅ G4 阻断；新目录 |
| **是否进 main** | **❌ 否**（8D.2 smoke 产物不进 main；只在本地 / `.claude/scratch/` 验证；与 8D checkpoint §9 一致） |
| **预期 paired** | ~ 4（5 day 配 4 对） |
| **预期 runtime** | < 1 min（sequential；每对 1 ~ 2 sec replay） |
| **smoke 通过判据** | (a) manifest `final_test_touched=false`；(b) 4 对全部完成 / `ready=true`；(c) 输出目录 5 个文件齐；(d) 无 main DB 写入；(e) `regime_labels_snapshot.csv` 5 行 / 5 个 `as_of_date` |

---

## 10. 2026 cutoff 风险

### 10.1 当前是否存在越界风险

**是**（在没有 8D.1A patch 的情况下）：

| 风险点 | 当前行为 | 越界后果 |
|---|---|---|
| `_load_avgo_trading_days(period="10y")` | 拉到今天（2026-05-05）的全部 trading day | dates list **含 2026 行** |
| `_build_date_pairs(days, num_cases=N)` | `days[-(N+1):]` | 当 `N` 大到覆盖 2026 时，**会包含 2026 pair** |
| `outcome_capture.capture_actual_outcome(symbol, prediction_for_date)` | 直接 yfinance 拉 `prediction_for_date` 周围数据 | 如 `prediction_for_date >= 2026-01-01` → **直接读 final test 数据** |
| `--save-records` 偶发开启 | 写 sqlite | 越界 row 可能进 DB |

### 10.2 必须 hard stop 的位置

| 位置 | 实现方式 |
|---|---|
| **G1 起点过滤**（最高优先） | `as_of_date_list = [d for d in available_dates if d < final_test_cutoff]`（在 `_build_date_pairs` 之前，**不在主循环中**） |
| **G2 prediction_for_date 边界** | `if prediction_for_date >= final_test_cutoff: skip + warning + paired -1`（在 `outcome_capture` 调用**之前**） |
| **G3 `--save-records` × W4 互斥** | startup 时 hard error；不允许并存 |
| **G4 output_dir 防覆盖** | startup 时 hard error |
| **manifest writer** | 失败时写 `final_test_touched=true` + `status="error"` |

### 10.3 T+1 outcome 如何处理

| 场景 | 处理 |
|---|---|
| `as_of_date = 2025-12-31` 且 `prediction_for_date = 2026-01-02` | **G2 skip**：不调 `outcome_capture`；不计入 paired；warning 记录于 manifest |
| `as_of_date = 2025-12-30` 且 `prediction_for_date = 2025-12-31` | ✅ 正常 replay；**最后一个有效 pair** |
| `as_of_date = 2025-12-31` 且 `prediction_for_date = 2025-12-31`（理论上不应该） | G1 起点过滤已 skip `as_of_date == 2025-12-31` 的"超末日"对；安全 |
| `as_of_date < 2024-08-03`（W4 范围外） | startup 时被 `--start-date` 过滤；不进入 |

实际 W4 paired 上界 ≈ 2024-08-05 → 2025-12-30（约 350 trading day）减去 2 ~ 5 个边界
skip → 实际可用 paired 估 ~ 340-345 个 prediction-outcome 对（取决于 calendar）。

### 10.4 manifest 如何证明 final_test_touched=false

| 字段 | 值 / 验证 |
|---|---|
| `final_test_cutoff` | 必须 `"2026-01-01"`；硬编码 |
| `final_test_touched` | 必须 `false`；任何 G1 / G2 触发越界 → `true` + `status="error"` |
| `replay_window.start` | 必须 `"2024-08-03"`；与 G1 起点过滤一致 |
| `replay_window.end` | 必须 `"2025-12-31"`；与 G1 起点过滤一致 |
| `records_generated` | int；写入 manifest 时实际 row 数 |
| `paired_outcomes` | int；G2 skip 后实际配对数 |
| `warnings` | list；记录所有 G2 skip 的 `prediction_for_date` |
| `status` | `"ok"` 仅当无 G1/G2/G3/G4 触发 |

---

## 11. GO / NO-GO

| 子步骤 | GO / conditional GO / NO-GO | 理由 |
|---|---|---|
| **8D.2 tiny smoke**（无 patch） | **❌ NO-GO** | 缺 `--start-date` / `--end-date` / cutoff guard / manifest writer |
| **8D.2 tiny smoke**（patch 后） | **✅ conditional GO** | 必须先完成 8D.1A minimal patch（§7.1 + §7.2 五项 guard） |
| **8D.3 full W4 replay**（无 patch） | **❌ NO-GO** | 同上 + 越界风险更大（~ 350 day） |
| **8D.3 full W4 replay**（patch 后 + smoke 通过后） | **✅ conditional GO** | 必须 8D.1A → 8D.2 → 8D.3 顺序 |
| **8D.3 full W4 replay**（直接跳 smoke） | **❌ NO-GO** | 8D checkpoint §9 强制规则：必须先 audit + smoke |
| **是否需要 patch** | **✅ YES**（8D.1A） | §6.1 五项 blocker 全部需要 patch |
| **hard / forced / required upgrade** | **❌ NO-GO** | 与 Step 2G-8 / 8A / 8B / 8C / 3R-0 / 3R-4 一致；本 audit 不解封 |
| **`_PROTECTION_LAYER_CONNECTED` 翻 True** | **❌ NO-GO** | 与 v1 一致 |
| **04 / 05 / 07 required upgrade** | **❌ NO-GO** | Step 2G 全程边界 |
| **触碰 2026 final test** | **❌ NO-GO** | 永久封禁 |

---

## 12. 下一步建议

按推荐优先级：

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **commit 本 audit** | 把 §1-13 audit 状态固化到 main | **本轮 / 下一轮** |
| 2 | **Step 2G-8D.1A minimal replay script patch** | 仅 `scripts/run_1005_three_system_replay.py`（或新 thin wrapper）；加 `--start-date` / `--end-date` / `--final-test-cutoff` / `--tiny-smoke` / `--write-manifest` + 5 项 hard guard + manifest writer + 可选接 `regime_labels_builder`；改动面小（~60-100 行）；不改 `services/*` | **高**（commit audit 后立刻启动） |
| 3 | **Step 2G-8D.2 tiny smoke window**（2024-08-05 → 2024-08-09，5 day） | 在 8D.1A patch 通过后启动；smoke 产物不进 main；本地 / `.claude/scratch/` 验证 | 中（8D.1A 之后） |
| 4 | **Step 2G-8D.3 full W4 replay**（2024-08-03 → 2025-12-31） | only after 8D.1A + 8D.2 通过；产物进 main（仅 csv / json / md） | 中（8D.2 之后） |
| 5 | **Step 2G-8D.4 W4 checkpoint** | 把 W4 final paired count / `final_test_touched=false` / 输出目录归档 | 中（8D.3 之后） |
| 6 | **Step 3R-4.1 4-fold validation helper design** | 纯 markdown 先行；产出 `regime_validation_report.v1` | 低（W4 完成后；与 3R-3 candidate 配对启动） |
| 7 | **不推荐**直接跑 full W4 | 必须先 audit + smoke | **❌** |
| 8 | **不推荐** 让 W4 自动让 candidate pass | W4 仅作 cross-window validation 数据 | **❌** |
| 9 | **不推荐** 升级 04 required | Step 2G 全程边界 | **❌** |
| 10 | **不推荐** 触碰 2026 final test | 永久封禁 | **❌** |
| 11 | **不推荐** 让 `_PROTECTION_LAYER_CONNECTED` 翻 True / Gate 5 / Gate 6 自动 pass | 与 v1 / 3R-0 / 3R-4 一致 | **❌** |

**关键判断**：
- 顺序 = 本 audit → 8D.1A patch → 8D.2 smoke → 8D.3 full → 8D.4
  checkpoint → 3R-4.1 design
- 任何一步失败 → 回到本 audit 重新审查
- 任何"跳过 8D.1A 直接 smoke"或"跳过 smoke 直接 full"都视为 NO-GO

---

## 13. 严守边界

本文是**纯 audit markdown**：

- ❌ 没改任何代码（`services/*` / `ui/*` / `tests/*` / `scripts/*` 全部未触碰）
- ❌ 没改 DB schema
- ❌ 没写 DB
- ❌ 没运行 replay
- ❌ 没改 `run_predict` / `predict.py` / `scanner.py` /
  `prediction_store.py` / `app.py`
- ❌ 没改 `services/regime_features_builder.py` /
  `services/regime_labels_builder.py` /
  `services/regime_diagnostics_dashboard.py` /
  `services/anti_false_exclusion_dashboard.py` /
  `services/soft_metadata_simulator.py` /
  `services/protection_layer_diagnostics.py` /
  `services/historical_replay_training.py` /
  `services/three_system_replay_audit.py` /
  `services/replay_record_wiring.py` /
  `services/projection_three_systems_renderer.py` /
  `services/outcome_capture.py` /
  `ui/protection_layer_diagnostics_renderer.py` / 任何 ui 模块 /
  任何 builder
- ❌ 没改 `scripts/run_1005_three_system_replay.py` 或任何 replay 脚本
- ❌ 没改 04 / 05 / 07 任何 required 字段
- ❌ 没启用 `hard` / `forced_exclusion` /
  `anti_false_exclusion_triggered`
- ❌ 没接 `yfinance` / `requests` / 任何网络
- ❌ 没接 trading API / `longbridge` / `broker` / `paper_trade`
- ❌ 没让 `_PROTECTION_LAYER_CONNECTED` 翻 True
- ❌ 没让 `hard_gate_status.protection_layer_connected` 自动 pass
- ❌ 没改 `hard_exclusion_allowed` / `primary_blocker` 派生
- ❌ 没触碰 2026-01-01 之后 final test range
- ❌ 没运行 replay / 没新写 replay 行
- ❌ 没改 Step 3R-4 protocol thresholds（6 metric / 7 gate / 10 no-go）
- ❌ 没改 Step 3R-2 helper 行为
- ❌ 没改 Step 2G-8D design / checkpoint
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` /
  `avgo_agent.db.backup_*`
- ❌ 没运行 `pytest`（本轮纯文档；测试基线维持 commit `5eb725b` 时
  的 2642 / 0 failed / 10 skipped）
- ✅ 只新增 1 份 markdown audit 文档（本文件）
