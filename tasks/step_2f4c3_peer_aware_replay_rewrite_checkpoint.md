# Step 2F-4c-3 — Peer-Aware Replay Rewrite Checkpoint

> 状态：Step 2F-4c-3（peer historical cutoff）已进 main，并且本地 DB 中那批 4c-2 阶段写入的 30 条 peer-collapsed replay 数据已经被删除并用 peer-aware writer 重写。peer 维度坍缩问题就此解除；`calibration_ready` 仍为 false，但唯一原因已收窄为 pair 数不足。
> 本文件只写文档，不改代码，不写 DB，不 commit，不 push。

## 1. 当前完成状态

| 子步 | 主题 | 已完成 | 改动类型 |
|---|---|---|---|
| **Step 2F-4c-3** | peer historical cutoff 上 main（NVDA/SOXX/QQQ 在 D 点的 RS 计算只看 `Date <= D` 的历史，缺失 peer 降级为 `unavailable`） | ✅ commit `d5d05af` 已进 main | service + tests |
| **Step 2F-4c-3-verify** | 只读验证 4c-3 上线后旧 30 条仍是 4c-3 之前的坍缩态 | ✅ | 验证；零代码改动 |
| **Step 2F-4c-3-rewrite** | 备份 → 删除旧 30 条 → 用 peer-aware writer 重写同样 30 条 → 校验新分布 | ✅（本轮） | DB 真写入；无代码改动 |

## 2. 当前 main 状态

- **main 最新 commit：** `d5d05af feat(contract): peer historical cutoff for replay writer`
- **测试基线：** **2213 passed / 0 failed / 10 skipped**（与 4c-3 commit 时一致；rewrite 没动代码、没改测试）
- **关键文件（已进 main）：**
  - [services/contract_replay_writer.py](services/contract_replay_writer.py) — peer historical cutoff 的写入路径
  - [tests/test_contract_replay_writer.py](tests/test_contract_replay_writer.py) — peer cutoff 单测
  - [tasks/step_1_contract_pipeline_summary.md](tasks/step_1_contract_pipeline_summary.md) — Step 1 pipeline 主线总结

## 3. DB 重写过程

> 备份文件：`avgo_agent.db.backup_pre_4c3_rewrite_20260503_235604`（2.4M，未提交，未删除任何旧备份）

### 3.1 删除前 SELECT
| 字段 | 值 | 期望 |
|---|---|---|
| `prediction_log` total | 33 | 33 ✅ |
| `outcome_log` total | 33 | 33 ✅ |
| `replay_AVGO_%` predictions | 30 | 30 ✅ |
| `replay_AVGO_%` outcomes (join) | 30 | 30 ✅ |
| `2099%` predictions | 0 | 0 ✅ |
| `review_log` join replay | 0 | — |
| `deterministic_review_log` join replay | 0 | — |

### 3.2 DELETE 影响行数（单事务，FK 反序）
| 表 | 删除行数 |
|---|---|
| `review_log` | 0 |
| `deterministic_review_log` | 0 |
| `outcome_log` | **30** |
| `prediction_log` | **30** |

### 3.3 删除后状态
| 字段 | 值 |
|---|---|
| `prediction_log` total | 3 |
| `outcome_log` total | 3 |
| `replay_AVGO_%` predictions | 0 |
| `2099%` predictions | 0 |
| `review_log` total | 3（保留） |
| `deterministic_review_log` total | 132（保留） |

### 3.4 重写后状态（CLI: `--symbol AVGO --start 2024-01-29 --limit 30 --write`）
| 字段 | 值 | 期望 |
|---|---|---|
| `prediction_log` total | 33 | 33 ✅ |
| `outcome_log` total | 33 | 33 ✅ |
| `replay_AVGO_%` predictions | 30 | 30 ✅ |
| `replay_AVGO_%` outcomes (join) | 30 | 30 ✅ |
| `replay_AVGO_%` rows with `contract_payload_json` | 30 / 30 | 30 ✅ |

writer notes 自报：
- "all writes went through `save_prediction` / `save_outcome` — no raw INSERT was used"
- "peer cutoff: NVDA / SOXX / QQQ relative-strength computed with `Date <= D` from coded_data; missing peers degrade to 'unavailable'"

## 4. 时间语义保持正确

| 字段 | 值 | 与 4c-2 write-30 一致 |
|---|---|---|
| `analysis_date` min/max | `2024-01-29` / `2024-03-11` | ✅ |
| `outcome_log.captured_at` min/max | `2024-01-30T16:00:00` / `2024-03-12T16:00:00` | ✅ |

- `analysis_date_override` / `captured_at_override`（4c-prereq 引入）仍按 D / D+1 16:00 注入，没有退化为 wall-clock。
- 边界与 4c-2 write-30 完全一致 → 后续 calibration 工具的 pair 计数延续性不被打断。

## 5. Peer 字段从坍缩到真实分布

> 重写前是 peer-collapsed（4c-3 上线之前 4c-2 写的那批），重写后是 peer-aware（4c-3 writer）。

### 旧分布（4c-3 前 / 已删除）
| 字段 | 分布 |
|---|---|
| `peer_confirmation_adjustment.nvda_signal` | `unknown × 30` |
| `peer_confirmation_adjustment.soxx_signal` | `unknown × 30` |
| `peer_confirmation_adjustment.qqq_signal` | `unknown × 30` |
| `peer_confirmation_adjustment.peer_alignment` | `insufficient × 30` |
| `confidence_system.extras.peer_confirm_count` | `0 × 30` |
| `confidence_system.extras.peer_oppose_count` | `0 × 30` |
| `exclusion_system.extras.peer_path_risk_direction` | `unchanged × 30` |

### 新分布（4c-3 后 / 当前 DB）
| 字段 | 分布 |
|---|---|
| `peer_confirmation_adjustment.nvda_signal` | `weaken: 19 / neutral: 10 / reinforce: 1` |
| `peer_confirmation_adjustment.soxx_signal` | `neutral: 11 / reinforce: 11 / weaken: 8` |
| `peer_confirmation_adjustment.qqq_signal` | `reinforce: 13 / neutral: 11 / weaken: 6` |
| `peer_confirmation_adjustment.peer_alignment` | `mixed: 17 / insufficient: 7 / all_weaken: 5 / all_reinforce: 1` |
| `confidence_system.extras.peer_confirm_count` | `0: 14 / 1: 8 / 2: 7 / 3: 1` |
| `confidence_system.extras.peer_oppose_count` | `0: 11 / 1: 10 / 3: 5 / 2: 4` |
| `exclusion_system.extras.peer_path_risk_direction` | `higher: 13 / unchanged: 9 / lower: 8` |

明确：
- `fully_collapsed = false`
- 7 / 7 peer fields 都出现真实分布
- peer historical cutoff 在写入路径上**确实**生效

## 6. 工具输出变化

### 6.1 `dashboard_contract_extras.py --limit 50 --symbol AVGO`
- `status = ok`
- `records_scanned = 33`, `valid_payloads = 30`, `invalid_payloads = 3`（3 条非 replay 的旧真实 prediction，缺 contract_payload_json，与 rewrite 无关）
- `extras_distributions.exclusion_system.extras.peer_path_risk_direction = unchanged: 9 / lower: 8 / higher: 13`
- `extras_distributions.confidence_system.extras.peer_adjusted_confidence = medium: 10 / high: 10 / low: 10`

### 6.2 `summarize_confidence_calibration_inputs.py --limit 50 --symbol AVGO`
- `status = ok`
- `data_gap_report.calibration_ready = false`
- `data_gap_report.contract_outcome_pairs = 22`
- `data_gap_report.minimum_recommended_pairs = 90`
- `data_gap_report.missing_dimensions =`
  - `["insufficient pairs: have 22, recommend ≥ 90"]`
  - **`"insufficient peer_confirm_count coverage"` 已消失** ✅
- `confidence_level_summary`：
  - medium: samples 10, accuracy 0.556（5/4/1）
  - high:   samples 10, accuracy 0.556（5/4/1）
  - low:    samples 10, accuracy 0.500（2/2/6）
- `primary_score_raw_summary`：count = 30, min = -2.75, max = 4.0, mean = 1.475

### 6.3 `correlate_contract_outcomes.py --symbol AVGO --limit 50`
- `status = ok`
- `valid_contracts = 30`, `paired_outcomes = 22`, `pending_outcomes = 8`
- `group_accuracy.final_projection.final_direction`：
  - 偏多: samples 21, accuracy 0.55
  - 偏空: samples 3, accuracy 0.50
  - 中性: samples 6, all pending（accuracy = null）

## 7. 关键结论

- **peer 维度坍缩问题已解决** —— 7 / 7 peer 字段都出现真实分布，`missing_dimensions` 不再报 peer coverage。
- **`calibration_ready` 仍为 false**，但原因已经收窄为单一项："insufficient pairs: have 22, recommend ≥ 90"。
- **下一步不需要再修 peer 坍缩**；不要再回头改 4c 系列 writer 路径。
- **下一步应考虑扩充 pair 数到 ≥ 90**（4c-4 / 4d）；扩量前必须先 dry-run 确认 plan、备份 DB、小心执行。
- **当前 30 条 peer-aware replay 是 baseline**，可作为后续扩量后做比对（同一 30-pair 子区间的 confidence_level / direction accuracy 应该和现在一致）。

## 8. 严守边界（本轮已遵守）

- ❌ 没改任何代码（`services/` / `scripts/` / `tests/` 0 字节变化）
- ❌ 没新增测试
- ❌ 没 commit / push（仓库 staging 区干净）
- ❌ 没改 DB schema
- ❌ 没跑 90 / 300 pair；limit 仍是 30
- ❌ 没扩大 limit
- ❌ 没接 yfinance / 网络
- ❌ 没接 trading API
- ❌ 没删除非 `replay_AVGO_%` 数据（3 条旧真实 prediction 完整保留）
- ❌ 没删除任何备份文件（4 个 backup 全部保留）

## 9. 下一步建议

- **Step 2F-4c-4 / 4d（90-pair replay 前置）**：
  1. 先做 dry-run scope 设计：是同一 symbol 顺延更长 `--start`，还是引入额外 symbol（NVDA / SOXX / QQQ 自身 replay）？
  2. 写出 90-pair 的预期 plan 文档；不动 writer 代码。
- **执行 90-pair 写入前的强制流程**：
  1. 备份 DB（命名 `avgo_agent.db.backup_pre_replay_90_<ts>`，与现有 backup 同款命名风格）
  2. 先 dry-run 一次确认 plan 行数 = 90，且 `anti_lookahead_check` pass
  3. 真写一次 `--write`，确认 `written_prediction_count = 90 / written_outcome_count = 90 / skipped = 0`
- **90-pair 必须使用同款 peer-aware writer**（即当前 main `services/contract_replay_writer.py`），不要新拉路径。
- **90-pair 后再跑 `summarize_confidence_calibration_inputs`**，目标 `paired_outcomes ≥ 90`（或至少接近 90，留出 flat / 中性 pending 余量）。
- **Step 3 calibration / exclusion 仍不能启动**，直到：
  1. `calibration_ready = true`（pair 数达标）
  2. Step 2G exclusion soft/hard 评估通过
- 这两个前置任意一个未达成都不开 Step 3。
