# Step 3R-3.3C-C-A — Market Data Source Audit Checkpoint

## 1. 当前完成状态
- Step 3R-3.3C real validation execution design 已 merge（commit `9720e0a`）。
- Step 3R-3.3C-C real validation execution design checkpoint 已 merge（commit `b1d82ee`）。
- 本轮完成 **Step 3R-3.3C-C-A market data source audit**：
  - read-only 审查 4 个本地 CSV：`data/AVGO.csv` / `data/NVDA.csv` / `data/SOXX.csv` / `data/QQQ.csv`
  - 字段 / 行数 / 日期范围 / 2026 行计数 / 重复 / 空值 / 单调性 全部统计
  - 结论：**4 个 CSV verdict = USABLE**
- 本 checkpoint 用于固化：audit table / coverage verdict / schema verdict / data quality / provider implications / no-go / 边界。
- **real W1-W4 validation 仍未运行。**
- **Step 3R-3.3C-C-B real `regime_label_provider` implementation 仍未启动。**
- **Step 3R-3.3C-C-C execution glue + single real run 仍未启动。**
- 本轮**未** commit / push；**未**改代码；**未**写 DB；**未**修改 csv。

## 2. audit source
| # | 路径 | 类型 |
|---|---|---|
| 1 | `data/AVGO.csv` | OHLC + Adj Close + Volume（yfinance-style） |
| 2 | `data/NVDA.csv` | 同上 |
| 3 | `data/SOXX.csv` | 同上 |
| 4 | `data/QQQ.csv` | 同上 |

审查窗口对照：
- W1 起点 = 2023-01-03（regime_labels 60-day market_trend window 反推前置 ≈ 2022-10-08）
- W2 起点 = 2023-09-01
- W3 起点 = 2024-03-01
- W4 起点 = 2024-08-03
- W4 终点 = 2025-12-31
- final_test_cutoff = 2026-01-01（永久封禁）

## 3. audit table

| symbol | exists | rows | min_date | max_date | required_columns | volume_present | post_2026_rows | duplicate_dates | null_close | monotonic | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **AVGO** | ✅ | 2505 | 2016-05-18 | 2026-05-05 | ✅（Date / Open / High / Low / Close） | ✅ | 85 | 0 | 0 | ✅ | **USABLE** |
| **NVDA** | ✅ | 2505 | 2016-05-18 | 2026-05-05 | ✅ | ✅ | 85 | 0 | 0 | ✅ | **USABLE** |
| **SOXX** | ✅ | 2505 | 2016-05-18 | 2026-05-05 | ✅ | ✅ | 85 | 0 | 0 | ✅ | **USABLE** |
| **QQQ** | ✅ | 2505 | 2016-05-18 | 2026-05-05 | ✅ | ✅ | 85 | 0 | 0 | ✅ | **USABLE** |

完整字段（4 个 csv 一致）：`Date` / `Open` / `High` / `Low` / `Close` / `Adj Close` / `Volume`（yfinance 默认导出格式）。

四个 csv 行数完全一致（2505），日期范围完全一致（2016-05-18 ~ 2026-05-05），post-2026 行计数也完全一致（85），表明这是一组对齐的市场数据。

## 4. coverage verdict
- **W1 起点 60 day pre-history**：4 个 csv 的 `min_date = 2016-05-18`，远早于 2022-10-08。✅ 充裕。
- **W4 终点**：4 个 csv 的 `max_date = 2026-05-05`，远晚于 2025-12-31。✅ 完全覆盖。
- **post-2026 行**：每个 csv 含 **85 行 `Date >= 2026-01-01`**，落在 final-test 区间。**不视为违规**：
  - `services/regime_labels_builder.py` 使用 `Date <= as_of_date` 的 anti-lookahead 模式（已锁定，line 84-100）；当 `as_of_date < 2026-01-01` 时，post-2026 行不会被消费。
  - builder 同时强制 `as_of_date >= final_test_cutoff` → `final_test_refusal=True`（已锁定，line 78-82）。
  - 但 real provider **必须**保证传入 builder 的 `as_of_date < 2026-01-01`，且**不**主动读取 post-2026 行做派生运算。
- **W1-W4 区间内日期连续性**：未对每个交易日做缺失检查（W4 jsonl 已 paired 353 行覆盖 2024-08-03 ~ 2025-12-31，B1 smoke 已确认 row count 与 manifest 一致；DB 上 W1-W3 也已 286 paired，与 audit 一致）。

## 5. schema verdict
- 4 个 csv 字段完全一致：`Date` / `Open` / `High` / `Low` / `Close` / `Adj Close` / `Volume`。
- `Date` / `Open` / `High` / `Low` / `Close` 全齐（builder 必备）。
- `Volume` present（builder 不强依赖，但 `pos20` 计算用 `High` / `Low` 不需要 Volume；保留无副作用）。
- `Adj Close` present（builder 不读；保留无副作用）。
- **不需要** column normalization / column rename。
- 可直接以 pandas DataFrame 形式注入 `services.regime_labels_builder.build_regime_labels(avgo_df, peer_dfs={"NVDA": nvda_df, "SOXX": soxx_df}, market_dfs={"QQQ": qqq_df, "SOXX": soxx_df}, as_of_date=...)`。
- 注：builder 期望的 `peer_dfs` / `market_dfs` 键命名以 ticker 大写为准（与 `_PEER_TICKERS_FOR_MOMENTUM = ("NVDA", "SOXX", "QQQ")` 一致）。

## 6. data quality notes
| 项 | 状态 |
|---|---|
| `null_dates` | **0**（4 个 csv 均为 0） |
| `null_close` | **0**（4 个 csv 均为 0） |
| `duplicate_dates` | **0**（4 个 csv 均为 0） |
| `monotonic`（Date 单调递增） | ✅（4 个 csv 均通过） |
| 行数对齐 | 4 个 csv 全 2505 行 |
| 日期范围对齐 | 4 个 csv 全 2016-05-18 ~ 2026-05-05 |
| post-2026 行计数 | 4 个 csv 全 85（同步覆盖到 2026-05-05） |

无任何 schema / 数据质量警告。无需 provider 内置 row-level guard（builder 现有 anti-lookahead + cutoff 已足够）。

## 7. provider implications
real `regime_label_provider`（Step 3R-3.3C-C-B 实施）行为约束：

| # | 必须 | 状态 |
|---|---|---|
| 1 | 一次性 `pandas.read_csv` 4 个 csv（init 时） | ✅（避免 per-row 反复读 csv） |
| 2 | parse `Date` 列为 datetime / Timestamp | ✅（builder 用 `df["Date"] == target_ts` 形式） |
| 3 | `sort_values("Date")` 保险（即使已 monotonic） | 推荐（防止某次 csv 被外部工具改顺序） |
| 4 | filter `Date <= as_of_date` | ✅（builder 内置 `_last_idx_le` / `_row_at`） |
| 5 | filter `Date < final_test_cutoff` | builder 已对 `as_of_date >= cutoff` 触发 final_test_refusal；row-level 过滤可由 provider 在 enrich 前做轻量保险 |
| 6 | **不**接 yfinance / requests / 任何网络 | ✅ |
| 7 | **不**用 W4 jsonl `pos20` / `five_state_projection` / `final_direction` / `direction_correct` / `actual_state` / `actual_close_change` 反喂 candidate | ✅（anti-lookahead） |
| 8 | **不**写 DB / **不**缓存到 DB | ✅ |
| 9 | **不**写 `logs/regime_validation/` 之外路径 | ✅ |
| 10 | 任一 csv 缺失 / 字段不全 → `FileNotFoundError` / `ValueError` fail-fast | ✅ |
| 11 | row `as_of_date` 在 csv 中找不到 → builder 返回 unknown labels + warning（adapter 阶段 row 因 candidate 缺失被 skip） | ✅ |
| 12 | 输出 `regime_labels.v1` schema valid | ✅（builder 已锁定） |

## 8. no-go rules
任意一项触发 → real validation execution **永久 abort**：

| # | 条件 |
|---|---|
| 1 | 4 个 csv 任一缺失 |
| 2 | 任一 csv 缺 `Date` / `Open` / `High` / `Low` / `Close` 列 |
| 3 | 任一 csv `min_date > 2022-10-08`（pre-W1 history 不足） |
| 4 | 任一 csv `max_date < 2025-12-31`（W4 coverage 不足） |
| 5 | provider 试图调 yfinance / requests / 任何网络 |
| 6 | provider 在 builder 之外读取 / 派生 post-2026 行 |
| 7 | provider 写 DB |
| 8 | provider 缓存到 `avgo_agent.db` / 任何 sqlite |
| 9 | provider 在初始化时不 fail-fast（缺 csv 静默继续） |
| 10 | provider 用 W4 future-leaking 字段反喂 candidate |
| 11 | provider 触碰 `services.prediction_store` / `services.outcome_capture` / `predict` / `scanner` / `streamlit` / `longbridge` / `broker` / `paper_trade` |

## 9. 是否允许下一步
| # | 候选 | 状态 |
|---|---|---|
| 1 | **Step 3R-3.3C-C-A audit checkpoint commit + merge to main** | ✅ 允许（独立 commit） |
| 2 | **Step 3R-3.3C-C-B real `regime_label_provider` implementation** | ✅ 允许（在 audit checkpoint 进入 main 后启动）；4 个 csv 全部 USABLE，无 PARTIAL，无 UNUSABLE |
| 3 | **Step 3R-3.3C-C-B checkpoint** | 紧接其后 |
| 4 | **Step 3R-3.3C-C-C execution glue + single real run** | 中（C-C-B 进 main 后） |
| 5 | **Step 3R-3.3C result checkpoint** | 中（C-C-C 完成后） |
| 6 | wrapper / candidate / adapter / helper / orchestrator / labels builder 现有行为 | ❌ 不改（仅只读调用） |
| 7 | hard / required upgrade / Gate 5 / Gate 6 / `_PROTECTION_LAYER_CONNECTED` | ❌ 永久封禁 |
| 8 | 直接 Step 3R-5 / 3R-6 | ❌ 永久封禁 |

## 10. 严守边界
本文是**纯 audit checkpoint markdown**：

- ❌ 没改任何代码（`services/*` / `ui/*` / `tests/*` / `scripts/*` 全部未触碰）
- ❌ 没改 DB schema
- ❌ 没写 DB（仅 read csv，未碰 sqlite）
- ❌ 没运行 replay
- ❌ 没运行 real validation
- ❌ 没修改任何 csv 文件（仅 read-only 字段统计）
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
- ❌ 没触碰 2026-01-01 之后 final-test range（仅记录 post-2026 行计数，未派生 / 未读取这些行）
- ❌ 没改 Step 3R-4 protocol thresholds（6 metric / 7 gate / 10 no-go）
- ❌ 没改 Step 3R-2 helper / 3R-3.1 candidate / 3R-4.2 helper / 3R-4.3A adapter 行为
- ❌ 没改 Step 3R-3.3 / 3R-3.3A / 3R-3.3B / 3R-3.3C / 3R-3.3C-A / 3R-3.3C-B / 3R-3.3C-B1 / 3R-3.3C-C 已 merge 文档 / 实施
- ❌ 没改 Step 2G-8D / 8D.1A / 8D.2 / 8D.3 / 8D.4 文档或代码
- ❌ 没把 W4 / smoke / `logs/regime_validation/` / `logs/prediction_log.jsonl` / DB backup / `agent_loop.py` / `.claude/worktrees/` 任一 commit 进 main
- ❌ 没运行 `pytest`（本轮纯 read-only audit + 文档；测试基线维持 commit `23da6c9` 时的 2857 / 0 failed / 10 skipped）
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*`
- ✅ 只新增 1 份 markdown audit checkpoint 文档（本文件）
