# Step 3R-3.3C-C-B — Real Regime Label Provider Checkpoint

## 1. 当前完成状态

- Step 3R-3.3C-C-A market data source audit 已完成。
- Step 3R-3.3C-C-B real `regime_label_provider` 已实现并进入 `main`。
- 本 checkpoint 固定：
  - provider public API
  - CSV loader behavior
  - `build_regime_labels` builder wiring
  - `final_test_cutoff` 行为
  - 测试覆盖
- real validation **仍未运行**。
- execution glue **仍未实现**。
- 本轮 checkpoint 只写文档：不改代码、不写 DB、不运行 validation、不 commit / push。

## 2. 当前 main 状态

- `main` 最新 commit：`65f8352`
- commit message：`feat(diagnostics): add real regime label provider`
- full pytest：**2877 passed / 0 failed / 10 skipped**
- 本步骤新增 / 修改：
  - `services/real_regime_label_provider.py`（新增）
  - `tests/test_real_regime_label_provider.py`（新增）
  - `tasks/step_1_contract_pipeline_summary.md`（§43 新增）

## 3. Public API

```python
build_real_regime_label_provider(
    *,
    avgo_csv_path: str = "data/AVGO.csv",
    nvda_csv_path: str = "data/NVDA.csv",
    soxx_csv_path: str = "data/SOXX.csv",
    qqq_csv_path: str = "data/QQQ.csv",
    final_test_cutoff: str = "2026-01-01",
) -> Callable[..., dict]

provider(as_of_date: str, row: dict | None = None) -> dict
```

说明：
- `row` 参数只为 orchestrator 兼容存在。
- provider 内部 **立即丢弃 row**。
- **不**从 `row` 读取 prediction / outcome / W4 jsonl 字段。
- provider 输出 schema 由 `build_regime_labels` 决定，调用方拿到的是 builder 已包装好的 regime label dict。

## 4. CSV loader behavior

- 读取 4 个本地 CSV：`AVGO`、`NVDA`、`SOXX`、`QQQ`。
- 缺文件 → `FileNotFoundError`。
- 缺 `Date` / `Open` / `High` / `Low` / `Close` 列 → `ValueError`。
- `Date` 解析为 `datetime`。
- 按 `Date` 升序排序。
- duplicate `Date` → `ValueError`。
- **不**预先删除 2026 行。
- 依赖 builder 的 anti-lookahead + `final_test_cutoff` 控制时间窗。

## 5. `build_regime_labels` wiring

- `avgo_df` = AVGO CSV
- `peer_dfs` = `{NVDA, SOXX, QQQ}`
- `market_dfs` = `{QQQ, SOXX}`
- `as_of_date` = provider 输入的 `as_of_date`
- `final_test_cutoff` = factory 输入的 `final_test_cutoff`
- **不**重写 builder 逻辑。
- **不**旁路 builder。
- **不**使用 W4 jsonl 的 `pos20 percentage`。
- 全部 regime label 推断由 builder 完成；provider 只做数据准备 + 调用。

## 6. `final_test` behavior

- `provider("2025-12-31")` → `final_test_refusal=False`
- `provider("2026-01-01")` → `final_test_refusal=True`
- post-2026 CSV 行可以存在，但不会被 `as_of_date < cutoff` 的查询消费。
- **不能**用 2026 数据生成 2025 以前的 label。
- final test cutoff 由 factory 显式传入，provider 不会硬编码绕过。

## 7. Isolation / forbidden imports

provider 严格隔离，**不**得引入：
- `yfinance`
- `requests` / `urllib` / 任何 network call
- `sqlite3` / `prediction_store`
- trading / `longbridge` / broker / `paper_trade`
- orchestrator 模块
- validation helper 模块
- 任何 hard / forced / required 分发字段
- 任何 threshold sweep 字符串

provider **不**得读取 W4 future-leak 字段：
- `actual_close_change`
- `actual_state`
- `direction_correct`
- `five_state_projection`
- `predict_result_json`
- `research_result_json`
- `scan_result_json`

## 8. 测试覆盖

- `tests/test_real_regime_label_provider.py`：**20 passed**
- `tests/test_regime_labels_builder.py` + `tests/test_run_real_continuous_smoothing_validation.py`：**70 passed**（合计）
- full pytest：**2877 passed / 0 failed / 10 skipped**

覆盖范围：
- CSV success / missing file / missing column / duplicate Date
- `schema_version = regime_labels.v1`
- `as_of_date` 正确传给 builder
- `row` 被忽略
- `2025-12-31` → not refusal
- `2026-01-01` → refusal
- 多次调用之间无状态 mutation
- forbidden imports 检查
- 无 future leak 字段
- 无 threshold sweep 字符串

## 9. 当前限制

- provider 已完成，但 **尚未接入** real validation execution。
- execution glue **仍未实现**。
- real validation **仍未运行**。
- **没有**生成真实 `regime_validation_report`。
- **没有**证明 candidate pass / fail。
- provider 只能在被 execution glue 调用时才会真正参与 validation。

## 10. 允许下一步

- Step 3R-3.3C-C-C execution glue **design / implementation** 可以启动。
- execution glue 必须串联：
  - `build_real_validation_inputs`
  - `build_real_regime_label_provider`
  - `run_continuous_smoothing_validation`
- 必须 **DB guard before / after**。
- 必须 output **untracked**。
- 仍 **不得**扫 threshold。
- 仍 **不得**自动启 hard。

## 11. 禁止事项

- **不**直接进入 3R-5 formula。
- **不**直接进入 3R-6 simulator。
- **不**扫 threshold。
- **不**调 SEED。
- **不**写 DB。
- **不**接 trading。
- **不**触碰 2026 final test range。
- **不** commit validation output。
- **不**让 report pass 自动启 hard。

## 12. 下一步建议

1. commit 本 checkpoint。
2. Step 3R-3.3C-C-C execution glue **design**。
3. execution glue **implementation**。
4. **single** real validation run。
5. result checkpoint。

## 13. 严守边界

- 本文只是 checkpoint。
- **没**改代码。
- **没**写 DB。
- **没**跑 validation。
- **没**启 hard / forced。
- **没**改 required。
- **没**接 trading。
- **没**触碰 2026 final test range。
