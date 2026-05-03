# Step 2F-4 — Real Replay / Outcome Pair Data Plan

> **方案文档，不是实现。** 本文档冻结未来积累真实 (contract × outcome) pair 的数据生成方案：目标、anti-lookahead 原则、阶段化范围、输出 schema、与现有工具的关系、最小实施候选、DB 卫生、成功标准、不做清单。
> Step 2F 已确认当前 `paired_outcomes = 0`；Step 2G 设计文档要求 `≥ 90` 真实 pair 才能考虑 calibration / exclusion 启用。本文档把"这 90 对怎么来、怎么不出错、怎么验证"写死下来，作为未来 Step 2F-4a/4b/4c/4d 实施前的 spec。
> 写文档不动代码：本轮不改 `predict.py` / adapter / contract validator / 6 个 read-only 工具 / DB schema 中的任何一处。

## 1. 背景

### 1.1 当前状态（截至 main `faadf01`）

- **Step 2F-3 实跑结论：** 主项目 DB 中 `paired_outcomes = 0`；3 条带 outcome 的 prediction 都缺 `contract_payload_json`，2 条带 contract 的 prediction（`0e7e37a6-...` / `2fe9eef2-...`）是合成验证记录（`prediction_for_date=2099-xx-xx`），无 outcome
- **Step 2G 设计要求：** `_MIN_RECOMMENDED_PAIRS = 90`；`soft_signal` / `path_risk` / `confidence_level` 三档各 ≥ 30 样本；**禁止合成 outcome**
- **Step 2 全程严守：** `predict.py` / `run_predict` / 4 个 builder / adapter / contract validator / `prediction_store` / DB schema 一行未改；6 个 read-only 工具的字段集一行未改

### 1.2 当前 2099 synthetic validation records

主项目 DB 里 2 条 `prediction_for_date=2099-xx-xx` 的合成记录：

| pid | snapshot_id | pred_date | 用途 |
|---|---|---|---|
| `0e7e37a6-...` | `step_2c_2_6_local_validation` | 2099-12-31 | 验证 contract_payload_json 落库 |
| `2fe9eef2-...` | `step_2e_4_full_extras_validation` | 2099-12-30 | 验证 04/05/07 extras 全量落库 |

**只用于工具验证，绝不能用于 calibration / exclusion 规则评估。** 它们的 outcome 永远不会触发（2099 未来日期），且 scan / predict 完全合成。

### 1.3 下一步核心不是改规则

是积累真实 (contract × outcome) pair。规则设计已冻结（Step 2G-2）；工具已就位（Step 2E-2 dashboard、Step 2F-2 calibration_inputs）；唯一缺的是数据。

## 2. 目标

### 2.1 单次生成动作

每个历史交易日 D：

1. 用 **`<= D`** 的数据生成 `prediction for D+1`
2. 通过 `services/prediction_store.save_prediction(...)` 真路径保存（自动旁路生成 `contract_payload_json`）
3. 用 D+1 的真实 OHLCV 数据，通过 `save_outcome(...)` 真路径生成 `outcome_log` 行
4. 形成一对真实 prediction × outcome

### 2.2 累积目标

| 阶段 | 目标 pair 数 | 用途 |
|---|---|---|
| 第一里程碑 | **≥ 90** | Step 2G-2 设计文档 §7 最低要求；解锁 `_MIN_RECOMMENDED_PAIRS` 阈值；可启动规则评估阶段 |
| 第二里程碑 | ≥ 300 | 跨档位覆盖更稳定；calibration 函数选型有依据 |
| 第三里程碑 | ≥ 1000 | 跨市场 regime 评估；hard exclusion 阈值校准 |

### 2.3 覆盖要求（与 Step 2G-2 §6 对齐）

- 跨 `confidence_level` 三档（high / medium / low）各 ≥ 30 样本
- 跨 `soft_signal` 三档（none / peer_weaken / high_path_risk）各 ≥ 30 样本
- 跨 `path_risk_level` 三档（low / medium / high）各 ≥ 30 样本
- 跨 `peer_confirm_count` / `peer_oppose_count` 多档（不能全坍缩到一点）
- `outcome.direction_correct` 同时含 `correct` / `wrong` 两类分布

## 3. 严格 anti-lookahead 原则

> **本节是数据完整性的红线。** 任何违反都会让积累的 pair 失去 calibration 价值。

### 3.1 时间分界

- prediction for D+1 **只能**使用 **`<= D`** 的数据
- outcome **只能**在 D+1 当天或之后读取
- D 与 D+1 之间的所有未来信息禁止泄露

### 3.2 具体禁止行为

- ❌ 不能用 D+1 的 peer 数据反向修正 D 的 prediction（如"NVDA 在 D+1 收跌，所以 AVGO 在 D 应该看空"）
- ❌ 不能用 D+1 收盘后的财报 / 新闻 / 事件影响 D 的 prediction
- ❌ 不能用全量历史训练后的"知识"污染 D 的 prediction（除非该训练只用 `<= D` 的数据）
- ❌ 不能用 ML 模型在跨 D 边界训练 / 推理（如果未来引入 ML）
- ❌ 不能用未来 sector / index 信息修正 D 的 scan_result

### 3.3 必须显式记录的字段

每条 replay prediction 必须包含：

- `data_cutoff_date = D`（数据截断日，硬性记录使用了 `<= D` 的数据）
- `replay_source = "historical_replay"`（区分真 replay 与生产 prediction）
- `analysis_date = D`（与现有 `prediction_log.analysis_date` 字段语义一致）
- `prediction_for_date = D+1`

### 3.4 对现有 `services/prediction_store.save_prediction` 的影响

当前签名：
```python
save_prediction(symbol, prediction_for_date, scan_result, research_result, predict_result, snapshot_id="—", *, contract_payload=...)
```

`analysis_date` 在内部用 `datetime.now().date().isoformat()` 自动设置（[prediction_store.py:259](services/prediction_store.py:259) 附近）——**这对 replay 是错的**：replay 时 `analysis_date` 应当是 D，不是 `now`。

**Step 2F-4a 必须诊断**：
- 现有 `save_prediction` 是否已支持外部传入 `analysis_date`
- 如果不支持，应当怎么处理（候选：通过 `snapshot_id` 编码 D，或 §10 不做清单允许的"只读不动 store"妥协方案，或独立提议 `save_prediction_replay(...)` 而不修改主路径）

**任何一种方案都不应在 Step 2F-4 实施前先改 `save_prediction`**——必须先有 Step 2F-4a 诊断。

## 4. 数据范围建议（阶段化）

按风险递增 + 覆盖递增分四阶段：

### 4.1 Phase A — 最近 120 个交易日（快速验证工具链）

- **目标：** 验证 replay 工具链端到端能跑通；不追求 calibration 数量
- **范围：** 120 ≈ 6 个月，单一 regime
- **预期 pair 数：** ~120（每日 1 对）
- **验收：** dashboard / calibration_inputs 工具能读出 04/05/07 extras 完整 + 部分 outcome 已 paired；至少 1 个 `direction_correct=correct` 与 1 个 `direction_correct=wrong` 出现
- **风险：** 单一 regime 覆盖窄，不能直接做 calibration

### 4.2 Phase B — 最近 300 个交易日（初步 calibration）

- **目标：** 解锁 `_MIN_RECOMMENDED_PAIRS = 90` 阈值；初步看 confidence_level 三档命中率
- **范围：** 300 ≈ 14 个月，可能含 1 次 regime 切换
- **预期 pair 数：** ~300
- **验收：** `data_gap_report.calibration_ready = true`；`confidence_level_summary` 三档都有 ≥ 30 paired sample；至少 2 档 `soft_signal` 出现
- **风险：** 中度，可能初步规则评估的阈值在跨 regime 时不稳定

### 4.3 Phase C — 最近 1000 个交易日（稳定评估）

- **目标：** Step 2G 阶段 2（规则评估）的主样本；hard exclusion 阈值校准
- **范围：** 1000 ≈ 4 年，多个 regime
- **预期 pair 数：** ~1000
- **验收：** `false_exclusion_rate / missed_exclusion_rate / net_benefit` 在子样本上稳定；hard 候选规则可以淘汰
- **风险：** 较低，但需要更多算力 / 数据完整性 / yfinance 历史数据可达性

### 4.4 Phase D — 分市场 regime 回放（验证规则跨周期稳定性）

- **目标：** 检查 calibration / exclusion 规则在不同 regime 下的稳定性
- **候选 regime：**
  - 2020：COVID 急跌 + V 型反转
  - 2022：连续加息熊市
  - 2024：AI 驱动的科技股集中拉升
  - 2025：（视市场状况）
- **预期 pair 数：** 每 regime ~250 trading days
- **验收：** 同一规则在多个 regime 上的 net_benefit 一致；hard exclusion 不会在某个 regime 系统性误杀
- **风险：** 高（regime 选择主观，需明确依据）

## 5. 输出数据要求

### 5.1 prediction_log 行（每条 replay prediction）

| 字段 | 必填 | 取值 |
|---|---|---|
| `id` | ✓ | uuid4（与现有 `save_prediction` 一致）|
| `symbol` | ✓ | "AVGO"（多 ticker 情况留待 Step 2F-4 之外） |
| `analysis_date` | ✓ | **D（不是 now）** —— 这是 anti-lookahead 关键字段 |
| `prediction_for_date` | ✓ | **D+1** |
| `snapshot_id` | ✓ | `replay_<phase>_<D>`（如 `replay_phaseA_2024-01-15`），便于按 phase / 日期检索 |
| `scan_result_json` | ✓ | 仅含 `<= D` 数据的 scan 输出 |
| `research_result_json` | 可选 | 若 replay 不接 research，留 NULL |
| `predict_result_json` | ✓ | `run_predict(scan_result, research_result, symbol)` 的真出口 |
| `contract_payload_json` | ✓ | `save_prediction` 自动旁路生成（不手工传） |
| `created_at` | ✓ | 实际写入时间（生产时间，可保留 now）|
| `final_bias` / `final_confidence` | ✓ | 由 `predict_result` 自动派生 |
| `status` | ✓ | "saved" |

**新增可选字段（Step 2F-4 设计阶段冻结，是否扩列由 4a 诊断决定）：**

- `data_cutoff_date`：与 `analysis_date = D` 等价，可省（避免 schema 改动）
- `replay_source`：编码进 `snapshot_id` 前缀，避免扩 schema

### 5.2 outcome_log 行（每条对应 outcome）

| 字段 | 必填 | 取值 |
|---|---|---|
| `id` | ✓ | uuid4 |
| `prediction_id` | ✓ | 对应 prediction_log.id |
| `prediction_for_date` | ✓ | D+1 |
| `actual_open` / `actual_high` / `actual_low` / `actual_close` | ✓ | D+1 真实 OHLCV，**只读 D+1 当天及之后数据** |
| `actual_prev_close` | ✓ | D 收盘 |
| `actual_open_change` / `actual_close_change` | ✓ | 计算字段，由 actual_close vs actual_prev_close 派生 |
| `direction_correct` | ✓ | 0 / 1 —— 由 predict.final_bias 与实际方向比对得出 |
| `scenario_match` | 可选 | 现有 schema 字段；若 replay 不评估 scenario 留 NULL |
| `captured_at` | ✓ | 实际写入时间 |

**新增可选字段（同 5.1 处理）：**

- `outcome_date`：与 `prediction_for_date` 等价，可省
- `source = "replay"`：通过 `prediction.snapshot_id` 前缀间接表达，避免 schema 改动

### 5.3 关键约束

- ❌ **不能手工塞 `direction_correct`**——必须由实际 D+1 OHLCV 与 predict.final_bias 自动派生
- ❌ **不能跳过 contract_payload_json**——必须走 `save_prediction` 自动旁路
- ❌ **不能用合成 OHLCV**——必须使用真实数据源（yfinance / 缓存的真数据）
- ❌ **不能跨 D 边界获取数据**——D 的 prediction 不能看 D+1 的 peer / sector 数据

## 6. 与现有工具的关系

> **复用，不另建私有格式。** 这是 Step 2F-4 与 Step 2 全程模式一致的核心原则。

| 现有工具 | replay 阶段使用 |
|---|---|
| `services/prediction_store.save_prediction(...)` | 写 prediction_log + 自动旁路 contract_payload_json（Step 1E）|
| `services/prediction_store.save_outcome(...)` | 写 outcome_log（已存在；Step 2F-4a 需诊断签名） |
| `services/projection_output_adapter.adapt_projection_output(...)` | save_prediction 内部调用，自动生成 contract_payload |
| `services/contract_payload_extras_dashboard.summarize_contract_extras_dashboard(...)` | replay 后看 04/05/07 extras 分布 |
| `services/contract_calibration_inputs.summarize_confidence_calibration_inputs(...)` | replay 后看 paired_outcomes / data_gap_report |
| `services/contract_outcome_correlation.correlate_outcomes_with_contract(...)` | replay 后看 final_direction / confidence_level 分桶命中率 |
| `services/contract_payload_inspector / trend / diff` | replay 单条 / 趋势 / 增量 diff |

**禁止：** 不另建 `replay_log` 表，不另建私有 JSON 格式，不绕过 `save_prediction` 自动旁路。**任何 replay 写入产生的 prediction 必须能被 6 个现有 read-only 工具直接消费。**

## 7. 需要先诊断的现有代码（Step 2F-4a 范围）

> 本文档**只列**清单；具体诊断在 Step 2F-4a 完成。

### 7.1 已有 replay / training 代码

- 仓库根目录是否有 `agent_loop.py`（在 main untracked 里看到过）的 replay 路径
- `logs/historical_training/three_system_1005/` 目录暗示曾有 historical training 数据，需查源代码
- `scripts/run_1005_three_system_replay.py`（Step 2D-1 grep 命中过）的 replay 模式与本文档目标的吻合度

### 7.2 outcome capture 函数

- `services/prediction_store.save_outcome(...)` 签名是否支持外部传入 `captured_at`
- 是否有 `compute_direction_correct(predict, actual_ohlcv)` 类似函数可复用
- outcome 计算路径是否已在测试中验证

### 7.3 数据源历史可达性

- yfinance 是否能稳定取 `<= D` 的 AVGO / NVDA / SOXX / QQQ 历史数据
- 是否有缓存层避免重复网络请求
- 缓存文件是否能被 D 截断（`tests/feedback_tests_no_live_network.md` 已记录"测试不能跑真网络"——replay 工具如果跑真 yfinance，应当只在脚本中允许，**不进测试**）

### 7.4 scanner 的历史窗口能力

- 现有 scanner 是否支持只看 `<= D` 数据
- `_recent_20_summary` 等函数是否能被截断
- peer 数据 NVDA / SOXX / QQQ 是否能按 D 截断（关键 anti-lookahead 检查点）

### 7.5 run_predict 的 cutoff 兼容性

- `run_predict(scan_result, research_result, symbol)` 是否纯函数（只看入参，不读全局 / 文件 / 网络）
- 现有 4 个 builder（primary / peer / final / research）是否纯函数
- 如果不是，哪些路径有 hidden lookahead 风险

### 7.6 prediction_store.save_prediction 的 analysis_date 处理

- 是否硬编码 `now()`（已知是）
- 是否有 backdoor / 测试钩子允许传入历史 D
- 改动它的最小代价是什么（vs 提议 `save_prediction_replay(...)` 不动主路径）

## 8. 最小实施方案候选

> 三个候选 Option，按风险递增。

### 8.1 Option A — 只设计，不写脚本（本文档）

- **范围：** 本文档（`tasks/step_2f4_real_replay_outcome_pair_plan.md`）
- **产出：** 方案 spec，0 行代码
- **风险：** 0
- **完成标志：** 本文档进 main
- **不足：** 没有可执行的下一步；replay 仍需要 4a-4d 实施

### 8.2 Option B — 先写 dry-run replay planner

- **范围：** 一个**只读** `services/contract_replay_planner.py` + `scripts/plan_contract_replay.py`，**不写 DB**
- **公共 API（草拟）：**
  ```python
  def plan_contract_replay(
      symbol: str = "AVGO",
      start_date: str | None = None,
      end_date: str | None = None,
      limit: int = 30,
  ) -> dict:
      """Read-only: enumerate trading days [start, end] and report
      what (D, D+1) pairs WOULD be generated, without writing the DB.
      Returns {trading_days, candidate_pairs, skipped_days_with_reasons,
      estimated_pair_count}."""
  ```
- **CLI：** `--symbol / --start / --end / --limit`
- **输出：** JSON 列表"如果跑真 replay，会生成哪些 (D, D+1) pair；哪些日子被跳过（如非交易日 / 数据缺失）"
- **风险：** 极低，只读不写
- **价值：** 让"我们要跑多大规模"可见；让"哪些日子拿不到 D 或 D+1 数据"提前暴露
- **完成标志：** dry-run planner 跑出 90 / 300 / 1000 三档预估 pair 数

### 8.3 Option C — 写 replay writer

- **范围：** `services/contract_replay_writer.py` + `scripts/run_contract_replay.py`，**真正写 prediction_log + outcome_log**
- **强制约束：**
  - **`--dry-run` 默认 ON**（必须显式 `--no-dry-run` 才真正写入）
  - `--limit N`（默认 30，渐进扩大）
  - `--start / --end`（必填）
  - `--symbol`（默认 AVGO）
  - `snapshot_id` 必须以 `replay_` 前缀（便于后续过滤）
  - **不能覆盖已存在的 prediction**（按 `(symbol, prediction_for_date, snapshot_id)` 检查）
  - **不能处理 `prediction_for_date LIKE '2099-%'` 的合成记录**
  - **必须先小规模验证：** 30-day → 90-pair → 300-pair → 1000-pair 顺序，每一档完成后跑 `summarize_confidence_calibration_inputs` 验证
- **风险：** 中（真写 DB；anti-lookahead 必须严格执行；OHLCV 数据完整性）
- **价值：** 真实 calibration / exclusion 评估的数据基础
- **完成标志：** Phase B（≥ 300 pair）完成且 `data_gap_report.calibration_ready = true`

### 8.4 推荐顺序

**Option A → Option B → Option C 渐进。** 不允许跳过：

- 跳过 Option A：没有方案 spec，实施时容易绕过 anti-lookahead 红线
- 跳过 Option B：直接写 DB 风险大，且不知道目标日子可达性

## 9. DB hygiene 建议

> 本任务**不执行清理**。下面是建议的独立清理任务的 spec。

### 9.1 当前合成数据现状

| pid | snapshot_id | pred_date | 类型 |
|---|---|---|---|
| `0e7e37a6-...` | `step_2c_2_6_local_validation` | 2099-12-31 | 合成验证 |
| `2fe9eef2-...` | `step_2e_4_full_extras_validation` | 2099-12-30 | 合成验证 |

外加：`avgo_agent.db.backup_step_2c_2_6` 备份文件（在 main 项目 untracked，未入 git）

### 9.2 清理建议（独立任务）

- **清理前先备份 DB：** `cp avgo_agent.db avgo_agent.db.backup_pre_hygiene_<date>`
- **删除条件：** `WHERE prediction_for_date LIKE '2099-%'`（精确匹配合成日期前缀）
- **同步删除该 prediction_id 对应的 outcome_log 行**（虽然两条 2099 prediction 都没 outcome，但写脚本时应当 join 检查）
- **删除前 dry-run：** 先 SELECT 显示要删的行，确认后再 DELETE
- **保留 `avgo_agent.db.backup_step_2c_2_6`**：那是 Step 2C-2.6 之前的真备份，不删

### 9.3 清理时机

- **不在 Step 2F-4 任何子步执行**——本任务只做"真实 replay 数据生成方案"，不混入 hygiene
- **建议时机：** 在 Step 2F-4c（小规模 30-day replay writer）之前——确保新 replay 写入时不会与合成数据混淆
- **执行方式：** 单独 ad-hoc 脚本，不进仓库；或直接在 sqlite3 CLI 手工执行

## 10. 成功标准（第一里程碑：≥ 90 真实 pair）

| 指标 | 目标 |
|---|---|
| 总真实 (contract × outcome) pair | **≥ 90** |
| `summarize_confidence_calibration_inputs.paired_outcomes` | ≥ 90 |
| `summarize_confidence_calibration_inputs.data_gap_report.calibration_ready` | **`true`** |
| `data_gap_report.missing_dimensions` 中"no paired outcomes"消失 | ✓ |
| `confidence_level_summary` 三档（high/medium/low）至少各 ≥ 1 | ✓ |
| `soft_signal` 三档（none/peer_weaken/high_path_risk）至少各 ≥ 1 | ✓ |
| `path_risk_level` 三档（low/medium/high）至少各 ≥ 1 | ✓ |
| `outcome.direction_correct` 含 correct + wrong 两类 | ✓ |
| dashboard `extras_distributions` 多样化（不再坍缩到单点）| ✓ |
| **replay 数据 100% 不含 2099 合成记录** | ✓ |
| **replay 数据所有 prediction 都有真实 outcome** | ✓ |

> **第二、第三里程碑（300 / 1000 pair）成功标准在 Phase B / Phase C 启动时单独立项。**

## 11. 不做清单

> 与 Step 2 全程严守边界一致 + Step 2F-4 数据特殊约束。

- ❌ **不实现 calibration**（Step 3+ 范围）
- ❌ **不升级 `exclusion_level`**（Step 2G 设计文档 §9 阶段 4 之后）
- ❌ **不接 confidence_engine.py / risk_model.py / contradiction_engine.py**
- ❌ **不接 big_up_contradiction_card / exclusion_reliability_review / big_down_tail_warning / anti_false_exclusion_audit 到主链**
- ❌ **不接 longbridge / broker / paper_trade / 真实交易 / 模拟盘 API**
- ❌ **不使用 2099 synthetic records 做 calibration**
- ❌ **不伪造 outcome**（任何 `direction_correct` 都必须由真实 OHLCV 与 predict.final_bias 比对得出）
- ❌ **不手工 UPDATE prediction_log / outcome_log**（必须走 `save_prediction` / `save_outcome` 真路径）
- ❌ **不改 contract schema**（不增删 contract section / required field）
- ❌ **不改 04/05/07 required 字段语义**（`exclusion_level=none` / 4 score=0.0 / event_score=None / trade_action=no_trade 全程不动）
- ❌ **不绕过 `save_prediction` 自动旁路**（contract_payload_json 必须由 adapter 自动生成，不手工塞）
- ❌ **不用未来数据污染 D 的 prediction**（anti-lookahead 红线）
- ❌ **不在本文档执行任何代码改动 / DB 写入 / 测试新增**

## 12. 下一步建议

> 阶段化推进，每一步独立立项 + 独立 commit。

| 候选 step | 范围 | 风险 | 优先级 |
|---|---|---|---|
| **Step 2F-4a** —— 只读诊断现有 replay / outcome / scanner cutoff 代码 | 仿 Step 2C-1 / 2D-1 / 2E-1 / 2F-1 / 2G-1 模式：grep + Read 既有代码，输出诊断报告，列出 `save_prediction` 是否支持历史 `analysis_date` / yfinance 历史可达性 / scanner 是否能按 D 截断 / peer 数据 cutoff 等 7.1-7.6 各项 | 低（只读）| **高**（必须先于 4b/4c 完成） |
| **Step 2F-4b** —— dry-run replay planner（Option B） | 新增 `services/contract_replay_planner.py` + `scripts/plan_contract_replay.py` + 测试；只读不写；输出"会生成哪些 (D, D+1)" | 极低（只读）| 高 |
| **DB hygiene 清理** | 单独 ad-hoc 脚本，不进仓库；删除 2099 合成记录；先备份 | 极低 | 中（建议在 Step 2F-4c 之前） |
| **Step 2F-4c** —— 小规模 30-day replay writer（Option C 第一步） | 新增 `services/contract_replay_writer.py` + `scripts/run_contract_replay.py`；`--dry-run` 默认 ON；30-day 范围；写入 prediction_log + outcome_log | 中（真写 DB） | 中 |
| **Step 2F-4d** —— 90-pair replay（解锁 calibration_ready=true） | 用 4c 工具扩到 90 pair；验证 dashboard / calibration_inputs 输出符合 §10 成功标准 | 中（依赖 4c）| 中 |
| **Step 3+ —— 真 calibration / 真 exclusion 接入** | 需 4d 完成 + Step 2G 阶段 2 评估通过 + 阶段 3 保护层接入 | 高 | **低**（必须等所有前置完成）|
| **真模拟交易** | **必须另开阶段** | 极低（与 Step 2D-2 严守边界一致：07 段策略边界永久 pinned） | — |

### 12.1 强烈建议优先级

**Step 2F-4a 是当前最有价值的下一步。** 它是本文档 §7.1-7.6 的诊断入口；不做诊断直接做 4b 容易在不知道 `save_prediction` 是否支持历史日期的情况下绕过 §3 的 anti-lookahead 红线。

**Step 2F-4a 完成后**，根据诊断结果决定：
- 若 `save_prediction` 已支持历史 `analysis_date` → 直接做 4b
- 若不支持 → 4a 报告需要列出三个候选改动方案（修改 `save_prediction` / 新增 `save_prediction_replay` / 通过 `snapshot_id` 编码 D），由用户选

### 12.2 Step 2F-4 与 Step 2 系列的关系

| Step 2 阶段 | 解决的问题 |
|---|---|
| Step 2A-2B | run_predict 字段化 |
| Step 2C-2D | extras 暴露 raw signals |
| Step 2E | dashboard 工具 |
| Step 2F | calibration 工具 + 数据缺口诊断（结论：0 pair）|
| **Step 2F-4（本文档及子步）** | **方案文档 + 数据生成工具 + 真实 pair 累积** |
| Step 2G | exclusion 规则设计冻结 |
| Step 3+ | 真 calibration / 真 exclusion 接入（依赖 2F-4 真实数据）|

**Step 2F-4 是 Step 2 系列与 Step 3 之间的关键桥梁。** 本文档冻结方案；4a-4d 子步实施数据；之后 Step 3+ 才能基于真实数据启动。
