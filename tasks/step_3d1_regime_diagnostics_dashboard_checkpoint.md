# Step 3D-1 — Read-Only Regime Diagnostics Dashboard Checkpoint

## 1. 当前完成状态

- Step 3 calibration 系列（Step 3A → 3B → 3B-1 holdout → 3A-4 third-window
  replay）已在 Step 3A-4 之后**暂停**。
- 暂停原因：Step 3B 4×4 `pos20 × peer_diff` lookup table 在 holdout
  上**部分改善但仍 FAIL**。pos20 作为 regime feature 仍被确认有用，但
  4×4 lookup 不稳定（见 `tasks/step_3b1_holdout_simulation.md` /
  `tasks/step_3a4_third_window_replay_checkpoint.md`），Step 3B-2 / 3C
  暂时冻结。
- Step 3D-1 的目标不是"重启 calibration"，而是把 Step 3B-0 / 3B / 3B-1 /
  3A-4 整套 regime feature 诊断**工具化**，让 Step 2G exclusion 重审、
  dashboard 展示、calibration 复盘和每次 replay 之后的 sanity check
  都能复用同一份证据生成路径。
- Step 3D-1 已实现、测试通过、合入 main，并落定为后续 Step 2G / 3D-2
  的依赖。

## 2. 当前 main 状态

- main 最新 commit：`19533ad` —
  `feat(diagnostics): add read-only regime diagnostics dashboard`
- 测试基线：**2254 passed / 0 failed / 10 skipped / 26 warnings /
  65 subtests passed**（约 9.6s）
- 本步骤新增 / 修改文件（4）：
  - 新增 [`services/regime_diagnostics_dashboard.py`](../services/regime_diagnostics_dashboard.py)
  - 新增 [`scripts/regime_diagnostics_dashboard.py`](../scripts/regime_diagnostics_dashboard.py)
  - 新增 [`tests/test_regime_diagnostics_dashboard.py`](../tests/test_regime_diagnostics_dashboard.py)
  - 修改 [`tasks/step_1_contract_pipeline_summary.md`](step_1_contract_pipeline_summary.md)（新增 §24）
- 未触碰：`predict.py` / `run_predict` / `scanner.py` /
  `prediction_store.py` / DB schema / `confidence_engine.py` /
  exclusion 硬软规则 / 04 / 05 / 07 顶层字段。

## 3. 工具定位

- **Read-only diagnostics tool**，不是 calibration 引擎、不是 confidence
  评分写入器、不是 04/05/07 contract 升级。
- 严格只读：
  - `SELECT` only（不调用 `init_db` / `INSERT` / `UPDATE` / `DELETE`）
  - 不写任何文件（CLI 仅 stdout）
  - `coded_data/<SYMBOL>_coded.csv` 只读
- 不修改：`predict.py` / `scanner.py` / `prediction_store.py`
- 不实现 calibration formula；`confidence_system` 4 个 0.0 score 字段
  不变。
- 不升级 04 (`exclusion_system`) / 05 (`confidence_system`) /
  07 (`simulated_trade`) 顶层字段。
- 不接 trading API（不 import `yfinance` / `requests` / `longbridge` /
  `broker` / `paper_trade`，由测试 grep 锁定）。
- 用于：
  1. Step 2G exclusion 重审（hard / soft 边界证据）
  2. Dashboard 展示（regime bias 可视化数据来源）
  3. Calibration 复盘（每次 lookup 实验后的 bias 残差检查）
  4. Replay 后 sanity check（30 / 130 / 380 三档 replay 之后一键检查
     是否引入意外 regime 偏移）

## 4. Service API

```python
summarize_regime_diagnostics_dashboard(
    db_path: str | Path | None = None,
    symbol: str = "AVGO",
    limit: int = 450,
    *,
    coded_data_dir: str | Path | None = None,  # keyword-only, 测试注入
) -> dict
```

输入 coercion：
- `db_path=None` → 回退 `services.prediction_store.DB_PATH`
- `symbol` 非 str / 空 → "AVGO"
- `limit` 非正 int / bool → 回退 `_DEFAULT_LIMIT = 450`
- `coded_data_dir=None` → 回退 `Path.cwd() / "coded_data"`

输出 dict 顶层 key（status="ok" 时）：

| key | 类型 | 说明 |
|---|---|---|
| `status` | `"ok"` / `"no_records"` / `"error"` | 错误经此 surface，不 raise |
| `symbol` | str | 标准化后的 symbol filter（用于 `replay_<SYMBOL>_%` LIKE） |
| `records_scanned` | int | DB 命中行数（`replay_<SYMBOL>_%` 匹配） |
| `valid_payloads` | int | 成功解析 contract_payload_json 的行数 |
| `paired_outcomes` | int | `direction_correct ∈ {0,1}` 的行数 |
| `pending_outcomes` | int | `direction_correct IS NULL` 的行数 |
| `calibration_ready` | bool | `paired_outcomes ≥ _MIN_RECOMMENDED_PAIRS (=90)` |
| `time_range` | dict | `{analysis_date_min, analysis_date_max}` |
| `pos20_quartile_bias` | list | Q1..Q4 共 4 桶；每桶含 `bucket / boundary / samples / paired / correct / wrong / pending / accuracy / predicted_bullish_rate / actual_up_rate / bias_gap` |
| `r4_signature` | dict | `samples / paired / correct / wrong / pending / accuracy / predicted_bullish_rate / actual_up_rate / bias_gap / high_confidence_count / downgrade_candidate_count / thresholds` |
| `confidence_by_regime` | dict | `overall (high/medium/low) / by_pos20_quartile (level × Q1..Q4) / explicit_slices (pos20_gt_0_62_high, pos20_gt_0_75_high)` |
| `peer_adjustment_summary` | dict | `by_peer_adjustment (upgrade/hold/downgrade) / by_peer_confirm_count ("0"/"1"/"2"/"3")` |
| `soft_signal_summary` | dict | `none / high_path_risk / peer_weaken` 各自 bucket |
| `monthly_accuracy` | list | `[{month: "YYYY-MM", samples, paired, correct, wrong, pending, accuracy, predicted_bullish_rate, actual_up_rate, bias_gap}]` 按月升序 |
| `high_confidence_failure_slices` | list | 5 个固定 slice：`confidence_high / pos20_q3_and_high / pos20_q4_and_high / r4_signature / bullish_high_pos20_gt_0_62` |
| `warnings` | list[str] | 数据降级、pos20 跳过原因、payload skip 计数 |

R4 signature 阈值（与 Step 3B 设计一致，frozen）：
- `avgo_minus_soxx_20d > 5`（pp，AVGO 20 日收益减 SOXX 20 日收益）
- `pos20 > 0.62`
- `final_direction == "偏多"`
- `confidence_level == "high"` 或 `primary_score_raw > 2`

`pos20` 定义：`(Close_D − rolling_low_20) / (rolling_high_20 − rolling_low_20)`，
`rolling_low/high` 的窗口为以 D 为终点的 20 个交易日。
`flat_band`（high == low）/ `insufficient_history`（不足 20 日）/
`missing_date` / `missing_ohlc` 全部跳过并归入 warning 计数。

## 5. CLI 用法

```
python3 scripts/regime_diagnostics_dashboard.py
python3 scripts/regime_diagnostics_dashboard.py --symbol AVGO --limit 450
python3 scripts/regime_diagnostics_dashboard.py --db avgo_agent.db --symbol AVGO --limit 450
python3 scripts/regime_diagnostics_dashboard.py --coded-data-dir /custom/coded_data
```

输出：stdout JSON，`ensure_ascii=False, indent=2`。
退出码：argparse 失败时非 0；service 内部错误经 `status=error` 表面化，
退出码仍为 0（与其他 read-only 诊断 CLI 一致）。

## 6. 测试覆盖

- 文件：[`tests/test_regime_diagnostics_dashboard.py`](../tests/test_regime_diagnostics_dashboard.py)
- 总数：**21 passed in ~0.21s**（unittest）
- 全部用 `tempfile.TemporaryDirectory()` 隔离 DB + tmp `coded_data/` 目录，
  从不读主项目 DB 或主 CSV。
- 覆盖矩阵：

| # | 测试类 / 名 | 验证点 |
|---|---|---|
| 1 | `NoRecordsTests` × 2 | 空 DB / 仅 live 行 → `status=no_records`；replay LIKE 是唯一过滤条件 |
| 2 | `InvalidPayloadTests` | 损坏 JSON 跳过且写 warning，不 crash |
| 3 | `PendingOutcomeTests` | pending 计入 `pending_outcomes` 与 slice `pending`，**不计入 accuracy 分母** |
| 4 | `Pos20ComputationTests` × 2 | 单样本时 quartile 输出 `[]` + warning；CSV 历史 < 20 日时 skip_reason=`insufficient_history` |
| 5 | `Pos20QuartileShapeTests` | 4 桶 shape 完整、key 齐全、按 Q1..Q4 顺序 |
| 6 | `R4SignatureTests` | 强动量场景命中 + downgrade_candidate_count + thresholds 锁定 |
| 7 | `ConfidenceByRegimeTests` | `overall.high/medium/low` 都 emit；`explicit_slices.pos20_gt_0_62_high` 存在 |
| 8 | `PeerAdjustmentSummaryTests` | upgrade/hold/downgrade 三 label + `0..3` 四档 confirm count |
| 9 | `SoftSignalSummaryTests` | none/high_path_risk/peer_weaken 三类 |
| 10 | `MonthlyAccuracyTests` | 按 YYYY-MM 升序聚合，accuracy 计算正确 |
| 11 | `HighConfidenceFailureSlicesTests` | 5 个固定 slice 顺序与命名锁定 |
| 12 | `ReadOnlyTests` | 调用前后 `prediction_log` / `outcome_log` row count + 行内容完全相同 |
| 13 | `ErrorPathTests` × 2 | DB 不可读 → `status=error`；空文件 DB → `error` 或 `no_records`，不 raise |
| 14 | `CliSmokeTests` | `subprocess.run` CLI，stdout 是合法 JSON，14 个顶层 key 齐全 |
| 15 | `NoNetworkImportTests` | grep service 源码：无 `yfinance` / `requests` / `longbridge` / `broker` / `paper_trade` |
| 16 | `CalibrationReadyTests` × 2 | `paired<90` → `calibration_ready=False`；常量 `_MIN_RECOMMENDED_PAIRS=90` 锁定 |
| 17 | `SymbolFilterTests` | NVDA replay 行不会出现在 `symbol=AVGO` 结果里（`replay_<SYMBOL>_%` 严格） |

## 7. 真 DB smoke 结果

main DB（`avgo_agent.db`，`replay_AVGO_%` = 380）一次性运行结果：

| 指标 | 值 |
|---|---|
| `records_scanned` | 380 |
| `valid_payloads` | 380 |
| `paired_outcomes` | 286 |
| `pending_outcomes` | 94 |
| `calibration_ready` | true |
| `time_range` | 2023-01-03 → 2024-08-02 |

pos20 quartile bias：

| bucket | boundary | samples | paired | accuracy | predicted_bullish_rate | actual_up_rate | bias_gap |
|---|---|---|---|---|---|---|---|
| Q1 | `<= 0.4275` | 95 | 75 | 45.3% | 22.7% | 58.7% | **−0.36** |
| Q2 | `(0.4275, 0.6310]` | 95 | 58 | 53.4% | 60.3% | 55.2% | +0.05 |
| Q3 | `(0.6310, 0.8198]` | 95 | 69 | 56.5% | 85.5% | 47.8% | +0.38 |
| Q4 | `> 0.8198` | 95 | 84 | 41.7% | 96.4% | 45.2% | **+0.51** |

R4 signature：

| 指标 | 值 |
|---|---|
| samples | 36 |
| paired | 34 |
| correct / wrong / pending | 11 / 23 / 2 |
| accuracy | **32.4%** |
| predicted_bullish_rate | 100.0% |
| actual_up_rate | 32.4% |
| bias_gap | **+0.68** |
| high_confidence_count | 34 |
| downgrade_candidate_count | 22 |

解释：
- R4 这一组**直接量化了 Step 3B-1 lookup FAIL 背后的核心 bias**：
  规则层在"AVGO 强于 SOXX、pos20 高位、high confidence"的 36 个历史日里
  **全部判 `偏多`**，但实际只有约三分之一真涨；下方 actual_up_rate ≈
  系统看多基线（Q1 actual_up_rate 58.7% 反而比 Q4 的 45.2% 更高），
  说明 pos20 高位本身并不天然预示更高的实际上涨概率。
- pos20 Q1 / Q4 两端的 `bias_gap` **方向相反**（−0.36 vs +0.51）—— 这是
  双极 bias，不是单调过度自信，恰好解释了为什么 4×4 lookup 在 holdout
  上不稳定：Q1 / Q4 各自需要相反方向的 calibration，且样本量随时间分布
  并不均匀。

## 8. 为什么这个工具重要

- 在 Step 3B-0 / 3B / 3B-1 / 3A-4 之前，regime 分析全部依赖 ad-hoc SQL
  + inline python（每次 reviewer 都要重写 join 和聚合，结果难以复核）。
- 现在 `summarize_regime_diagnostics_dashboard()` 是一份可复用、可
  diff、可自动化的证据生成路径。每次 replay 之后可以**一键**检查：
  - pos20 是否仍然存在双极 regime bias（Q1 / Q4 两端 `bias_gap` 反向）
  - R4 是否仍是高风险 slice（`accuracy` / `bias_gap` / `downgrade_candidate_count`）
  - high-confidence-failure 是否仍集中在 pos20 高位 + 偏多组合
  - `soft_signal=peer_weaken` / `=high_path_risk` 是否真的对 accuracy 有
    负向区分度（如果没有，soft signal 的语义需要重审）
  - `peer_adjustment` 是否仍存在反向问题（upgrade 反而 accuracy 更低？）
- 它让 Step 2G / dashboard / 后续 calibration 复盘**不再凭感觉设计**：
  所有 exclusion 阈值与 dashboard 切片都能引用同一份 JSON 输出。

## 9. 与 Step 3 calibration 的关系

- 本工具**不**解除 Step 3B-1 holdout FAIL 的状态。
- 不代表可以进入 Step 3B-2 / 3C；这两步仍然冻结。
- 不实现 calibration formula；不写入任何 confidence score。
- 只是把 diagnostics 产品化 —— 把 Step 3B-0 设计阶段的"我觉得 pos20
  应该是 regime feature"这种判断变成可重复运行、可 diff、可锁定的
  数值证据。
- Step 3 calibration 系列下一次重启的前置条件不变（仍需找到一个在
  holdout 上稳定 outperform baseline 的方案；本工具只负责量化 regime
  bias，不负责消除它）。

## 10. 与 Step 2G 的关系

Step 2G（soft / hard exclusion 重审）应该把本工具作为主要证据来源，
特别是以下四个判断：

- `soft_signal=peer_weaken` 的 paired accuracy / bias_gap 是否
  **显著低于** `soft_signal=none`？如果不是，这个 soft signal 的存在
  价值需要重审。
- `soft_signal=high_path_risk` 的 paired accuracy / bias_gap 是否
  **显著低于** `soft_signal=none`？同上判断。
- R4 是否更适合作为 **soft exclusion metadata**（让 dashboard 标红
  + 让 review 自动追问）而**不是** hard exclusion？目前 R4
  `downgrade_candidate_count = 22` / 36，若硬化成 hard exclusion 会同时
  屏蔽 11 个真正命中的 R4，损失太大。
- **不要直接把 `soft_signal != none` 硬化成 hard exclusion**；先用
  `soft_signal_summary` 的 paired accuracy 数据判断每个 soft 类别
  是否有信号价值。

## 11. 2026 final test cutoff

- 本工具当前消费的全部是 **2023-01-03 → 2024-08-02** 的 replay 数据，
  与 Step 2F-4d-2 落定的 130-pair window + Step 3A 系列 second / third
  window 完全一致。
- **未触碰 2026-01-01 之后的 final test range**（CLI / service 都不
  按时间过滤，但 DB 内本就没有 2026-01-01 之后的 replay 行，且 final
  test 数据也不会被 replay writer 写入此 DB 路径）。
- 后续不能用 2026-01-01 之后的数据反复调参 / 反复跑这个 dashboard
  来挑参数；2026-01-01 之后仍是**整个系统**完成后的最终测试集。
- 如果将来要把这个工具用到 final test，必须新增显式时间过滤参数 +
  显式 final-test 模式，避免无意中把 final test 数据混入调参样本。

## 12. 下一步建议

按推荐优先级：

1. **Step 2G — soft / hard exclusion re-review**（推荐**优先做这个**）。
   现在工具已经能支撑 exclusion 证据判断（`soft_signal_summary` /
   R4 / `high_confidence_failure_slices`），可以从"凭感觉"切到"凭
   `bias_gap` 与 paired accuracy"。预期产出：soft signal 三类是否各自
   有区分度的判定 + R4 是否值得作为 soft exclusion metadata。
2. **Step 3D-2 — dashboard UI / richer CLI**。把当前 JSON 输出渲染到
   Streamlit dashboard 的一个新 tab；或在 CLI 上增加 `--slice` /
   `--month` / `--export-csv` 选项。本步建议在 Step 2G 完成之后再做，
   以便 UI 设计时已经知道哪些切片真的有决策价值。
3. **Step 3 calibration 重启**。前置条件不变 —— 需要在 holdout 上
   稳定 outperform baseline 的方案；本工具不解除该前置条件。

## 13. 严守边界（本步骤）

- ❌ **没**写 DB（`SELECT` only；`init_db` 不调用；`INSERT` / `UPDATE` /
  `DELETE` 全无）
- ❌ **没**改 DB schema
- ❌ **没**改 `predict.py`
- ❌ **没**改 `scanner.py`
- ❌ **没**改 `prediction_store.py`
- ❌ **没**改 `confidence_engine.py` / `contradiction_engine.py` /
  `feature_builder.py`
- ❌ **没**实现 calibration formula
- ❌ **没**修改 `confidence_system` 4 个 0.0 score 字段或 `event_score`
- ❌ **没**升级 04 / 05 / 07 顶层字段
- ❌ **没** import `yfinance` / `requests` / `longbridge` / `broker` /
  `paper_trade`（grep 锁定）
- ❌ **没**接 trading API
- ❌ **没**触碰 2026-01-01 之后 final test range
- ❌ **没**运行 replay / **没**新写 replay 行
- ❌ **没**触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` /
  `avgo_agent.db.backup_*`
- ✅ 只新增 read-only 工具 + 1 份 doc + 1 个 §24 doc 段落
