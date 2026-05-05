# Step 3R-3.3B — Limited-Record Smoke Checkpoint

## 1. 当前完成状态
- Step 3R-3.3A dry-run validation orchestrator 已完成。
- Step 3R-3.3B limited-record smoke 已运行成功。
- 本 checkpoint 用于固定 smoke 输入 / 输出 / 通过条件 / 边界。
- real W1-W4 validation 仍未运行。
- 本轮只写 checkpoint 文档，不改代码，不写 DB，不跑 full validation。

## 2. 当前 main 状态
- main 最新 commit：`9fbd9b5`
- commit message：`docs(contract): Step 3R-3.3A dry-run validation orchestrator checkpoint`
- 本轮没有改代码。
- 本轮没有写 DB。
- 本轮没有跑 full validation。
- 本轮没有 commit smoke output。
- 本轮没有 push。

## 3. smoke 目标
- 验证 public orchestrator 可端到端串联（load → adapt → validate → write outputs）。
- 验证 `write_outputs=True` 可以一次写出 4 个文件。
- 验证 W1 / W2 / W3 / W4 window assignment 在 fixture 上正确。
- 验证 `final_test_touched = false`。
- 验证 DB 不变。
- **不**验证 candidate 是否通过 gate。
- **不**作为 candidate pass 凭证。

## 4. smoke input
- 8 条 in-memory replay_rows。
- W1 / W2 / W3 / W4 各 2 条。
- 日期均落在 2023-2025（没有任何 2026 行）。
- `regime_label_provider` 使用固定合法 `regime_labels.v1` 映射。
- `w4_manifest` 使用 valid dict（schema 合法）。
- `candidate_threshold = 0.60`。
- `write_outputs = True`。

## 5. output_dir
```
logs/regime_validation/continuous_smoothing_v1_limited_smoke_20260505_231620/
```

边界：
- 是新建目录。
- 是 untracked，不进 main。
- 不覆盖任何旧输出。
- 仅作 plumbing 结果保存。

## 6. 输出文件
4 个文件：

| 文件 | 字节数 |
| --- | --- |
| `replay_validation_records.json` | 12024 |
| `regime_validation_report.json` | 2991 |
| `regime_validation_summary.md` | 591 |
| `run_manifest.json` | 694 |

全部位于 `output_dir` 下，全部 untracked。

## 7. run_manifest 摘要
- `schema_version = regime_validation_run_manifest.v1`
- `candidate_name = continuous_smoothing_v1`
- `candidate_threshold = 0.6`
- `fold_count = 4`
- `w4_manifest_status = ok`
- `final_test_cutoff = 2026-01-01`
- `final_test_touched = false`
- `records_loaded = 8`
- `records_adapted = 8`
- `report_status = fail`
- `warnings = 1`，内容：`w4_manifest_not_required`

## 8. replay_validation_records 摘要
- `schema = replay_validation_records.v1`
- `records = 8`
- `final_test_refusal = false`
- per-window：
  - W1 = 2
  - W2 = 2
  - W3 = 2
  - W4 = 2
- `candidate_threshold = 0.6`

## 9. regime_validation_report 摘要
- `schema = regime_validation_report.v1`
- `overall_status = fail`
- `worst_window = W1`
- `gate_status`：6 fail / 1 pass
- `survival_case_preservation` = pass
- fail 原因：
  - `minimum_window_sample_size`
  - `false_exclusion_rate`
  - `net_benefit`
  - `accuracy_delta_vs_baseline`
  - `cross_window_variance`
  - `no_single_window_collapse`
- `report_status = fail` **是预期结果**，因为 8 行 small fixture 远低于真实样本量门槛，本 smoke 只是为 plumbing 验证而非 candidate gate。

## 10. DB / git 验证
- `avgo_agent.db` before / after mtime + size 完全一致：
  - before: `(1777833249653954308, 11206656)`
  - after:  `(1777833249653954308, 11206656)`
- DB 未修改。
- `git status` 无 tracked modified file。
- `logs/regime_validation/` 全部 untracked。
- 未对 `logs/prediction_log.jsonl` 做任何写入。
- W4 / smoke output / prediction log 均未 `git add`。

## 11. final test guard
- `final_test_touched = false`。
- 所有 8 行均在 2023-2025 区间。
- 未触碰 2026。
- 未触发 `final_test_refusal`。
- 没有任何 2026 行进入 records。

## 12. 通过条件
全部满足：
- 4 个文件写出成功。
- `records_loaded > 0`。
- `records_adapted > 0`。
- W1 / W2 / W3 / W4 均被覆盖。
- `final_test_touched = false`。
- DB 未修改。
- git 无 tracked modified。
- output 保持 untracked。

## 13. 当前仍未做
- 未跑 real W1-W4 validation。
- 未读取真实 W4 full jsonl。
- 未接 W1 / W2 / W3 real source。
- 未证明 candidate pass。
- 未做 threshold scan。
- 未调 coefficients。
- 未写 DB。
- 未启 hard / forced。

## 14. 允许下一步
- Step 3R-3.3C real W1-W4 validation run design 可以启动。
- 但必须先设计：真实 source / output 路径 / cutoff 行为 / DB guard。
- **不得**在没有 design 的情况下直接跑 full real validation。
- Step 3R-5 / 3R-6 仍不允许进入。

## 15. 禁止事项
- 不写 DB。
- 不跑 replay。
- 不扫 threshold。
- 不调 SEED。
- 不启 hard / forced。
- 不改 required。
- 不接 trading。
- 不触碰 2026。
- 不 commit validation outputs。
- 不直接进入 formula / simulator。

## 16. 严守边界
- 本文只是 checkpoint。
- 没改代码。
- 没写 DB。
- 没跑 full validation。
- 没启 hard / forced。
- 没改 required。
- 没接 trading。
- 没触碰 2026 final test range。
