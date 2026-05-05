# Step 3R-3.3A — Dry-Run Validation Orchestrator Checkpoint

## 1. 当前完成状态

- Step 3R-3.3 design 已完成（`tasks/step_3r3_3_4fold_validation_run_design.md`）。
- Step 3R-3.3 checkpoint 已完成（`tasks/step_3r3_3_4fold_validation_run_checkpoint.md`）。
- Step 3R-3.3A dry-run continuous smoothing validation orchestrator 已完成并进入 main。
- 本 checkpoint 的作用是固定以下边界：
  - public API 签名
  - output schema (`continuous_smoothing_validation_run.v1`)
  - write behavior（默认 dry-run、显式 opt-in 才写文件）
  - candidate threshold policy（first-run seed 0.60、不 sweep）
  - 测试覆盖范围
- Step 3R-3.3B limited-record smoke 尚未启动；本步骤不触发任何真实 validation run。

## 2. 当前 main 状态

- main 最新 commit：`32f196a`
- commit message：`feat(diagnostics): add continuous smoothing validation orchestrator`
- full pytest：2825 passed / 0 failed / 10 skipped
- 本步骤新增 / 修改文件：
  - `scripts/run_continuous_smoothing_validation.py`（新增）
  - `tests/test_run_continuous_smoothing_validation.py`（新增）
  - `tasks/step_1_contract_pipeline_summary.md`（更新 §41）

## 3. Public API

```python
run_continuous_smoothing_validation(
    replay_rows,
    *,
    regime_label_provider,
    w4_manifest,
    candidate_threshold=0.60,
    candidate_name="continuous_smoothing_v1",
    final_test_cutoff="2026-01-01",
    output_dir=None,
    write_outputs=False,
) -> dict
```

性质：

- pure read-only orchestrator
- caller 注入 `replay_rows`（in-memory 列表）
- caller 注入 `regime_label_provider`（callable）
- caller 注入 `w4_manifest`（in-memory dict）
- 默认不写文件（dry-run）
- 不读 DB、不写 DB
- 不跑 replay
- 不读真实 W4 jsonl 或 W4 manifest 文件
- 不接网络、不接 trading API
- 不内嵌任何硬编码路径

## 4. Output schema

`continuous_smoothing_validation_run.v1` 字段：

- `schema_version`：固定 `continuous_smoothing_validation_run.v1`
- `candidate_name`：来自参数（默认 `continuous_smoothing_v1`）
- `candidate_threshold`：实际使用的阈值（默认 `0.60`）
- `records_loaded`：输入 `replay_rows` 数量
- `records_adapted`：跳过 final-test 行后实际进入 adapter 的数量
- `report_status`：来自 helper 的 regime validation report 状态字段
- `replay_validation_records`：adapter 输出的逐行 validation records
- `regime_validation_report`：helper 输出的 regime validation report
- `run_manifest`：本次 run 的元信息（candidate name / threshold / cutoff / counts / write flags）
- `warnings`：累积的非致命告警列表

## 5. Orchestration flow

1. 接收 in-memory `replay_rows`
2. 对每行读取 `analysis_date`
3. final-test rows 在 candidate 生成前直接跳过（按 `final_test_cutoff`）
4. 调用 `regime_label_provider` 取 regime label
5. 调用 `build_continuous_smoothing_candidate` 生成 candidate
6. 把 candidate 附加到行 copy 上（输入 `replay_rows` 不被原地修改）
7. 调用 `build_replay_validation_records` 得到 adapter 输出
8. 调用 `build_regime_validation_report` 得到 regime helper 输出
9. 组装 `run_manifest`
10. 仅当 `write_outputs=True` 时，写 4 个文件到 caller 指定的 `output_dir`

## 6. write_outputs behavior

- 默认 `write_outputs=False` → 不写任何文件
- `write_outputs=True` 必须显式提供 `output_dir`
- 若 `output_dir` 已存在 → 抛出 `FileExistsError`，不覆盖
- 写入恰好 4 个文件，全部位于 `output_dir` 内：
  - `replay_validation_records.json`
  - `regime_validation_report.json`
  - `regime_validation_summary.md`
  - `run_manifest.json`
- 不在 `output_dir` 之外创建任何文件
- 没有默认 logs 路径、没有内嵌 fallback 路径

## 7. candidate_threshold policy

- 默认值 `0.60`（first-run seed）
- 仅作为 design seed，不构成最终阈值结论
- caller 可显式 override
- 本步骤不做 threshold sweep
- 本步骤不做任何在线学习 / 自适应调整
- 不允许从 validation result 反推阈值
- 非法阈值由下游 adapter 的现有 `ValueError` 处理；orchestrator 不做额外 silent coerce

## 8. Final test guard

- final-test rows 在 candidate 生成前就被跳过
- `regime_label_provider` 的 `final_test_refusal` 信号会被透传到 manifest / report
- candidate 自身的 `final_test_refusal` 仍由 candidate 层负责
- adapter 的 final-test guard 仍然生效
- helper 在 report 中反映 `final_test_refusal` 状态
- 任何形态下都不允许使用 2026 年（含）数据生成 candidate

## 9. No real validation run

- 所有 tests 仅使用 in-memory fixtures
- 不读 W4 full jsonl
- 不读 W4 manifest 文件
- 不接 W1/W2/W3 真实 source
- 不生成 production-grade validation report
- 本步骤明确是 dry-run orchestrator，不是 real validation run

## 10. 测试覆盖

测试结果：

- `tests/test_run_continuous_smoothing_validation.py`：24 passed
- `tests/test_replay_validation_record_adapter.py`：48 passed
- `tests/test_regime_validation_helper.py`：33 passed
- `tests/test_continuous_smoothing_candidate.py`：31 passed
- full pytest：2825 passed / 0 failed / 10 skipped

orchestrator 覆盖维度：

- output schema 正确性
- candidate 正确 attach 到 row copy
- adapter 调用路径
- helper 调用路径
- 输入 `replay_rows` 不被原地修改（input immutability）
- final-test row skip
- threshold 透传到 candidate 与 manifest
- `write_outputs=False` 不写文件
- `write_outputs=True` 写恰好 4 个文件
- `output_dir` 已存在时抛 `FileExistsError`
- `run_manifest` 字段完备
- 不允许出现禁用 import（DB / network / trading）
- 不允许硬编码 W4 路径
- 不允许内置 threshold sweep

## 11. 当前限制

- 还没有读取真实 W4 jsonl
- 还没有真实 W1/W2/W3 source 接入
- 还没有 limited-record smoke run（3R-3.3B）
- 还没有 real W1-W4 validation report（3R-3.3C）
- 还没有 result checkpoint（3R-3.3 result）

## 12. 允许的下一步

- Step 3R-3.3B：limited-record smoke
  - 使用小型 local fixture / 限定 rows
  - smoke 输出目录保持 untracked
  - 不允许直接进入 full real W1-W4 run
- Step 3R-3.3C：real W1-W4 validation run（必须等 3R-3.3B smoke 通过）
- Step 3R-3.3 result checkpoint（在真实 run 完成后落地）

## 13. 禁止事项

- 不写 DB
- 不跑 replay
- 不做 threshold sweep
- 不调 SEED
- 不启 hard / forced 模式
- 不改 required 字段集
- 不接 trading API
- 不触碰 2026 年 final test range
- 不 commit validation outputs
- 不直接跳进 formula（3R-5）/ simulator（3R-6）

## 14. 下一步建议

推荐顺序：

1. commit 本 checkpoint 文档（独立 commit，不夹带代码改动）
2. Step 3R-3.3B limited-record smoke design / run
3. Step 3R-3.3B checkpoint
4. Step 3R-3.3C real W1-W4 validation run
5. Step 3R-3.3 result checkpoint

不推荐：

- 直接进入 3R-5 formula
- 直接进入 3R-6 simulator
- 直接启 hard / forced

## 15. 严守边界

- 本文只是 checkpoint 文档
- 没改代码
- 没写 DB
- 没跑 validation
- 没启 hard / forced
- 没改 required 字段
- 没接 trading
- 没触碰 2026 final test range
