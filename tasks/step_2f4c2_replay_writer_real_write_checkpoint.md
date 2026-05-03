# Step 2F-4c-2 — Replay Writer Real-Write Checkpoint

> 状态：Step 2F-4 系列（plan → 4a planner → 4b writer skeleton → 4b-verify → 4c-prereq → 4c-1 limit cap collapse → hygiene-1 → hygiene-2 → 4c-2 real-write upgrade → dry-run verify → 30-pair real write）已全部完成。Step 2F-4c-2 是这条链上**第一个**改了 DB 真实数据的子步——把 `paired_outcomes` 从 0 推到 22。本文件是进入 Step 2F-4c-3（peer 历史 cutoff）/ Step 3 真 calibration 之前的 handoff 快照。
> 本轮只写文档，不改代码，不 commit，不 push。

## 1. Step 2F-4 全子步清单

| 子步 | 主题 | commit | 改动类型 |
|---|---|---|---|
| 2F-4 plan | 真实回放 / outcome pair 数据方案设计文档 | `e9b44e2 docs(contract): freeze real replay outcome pair data plan` | 纯文档 |
| 2F-4a | dry-run planner（只读 csv → (D, D+1) 候选对） | `4c89d98 feat(contract): add dry-run replay planner` | 新增 service + tests |
| 2F-4b | dry-run writer skeleton（无 DB 写入，仅 plan 通过） | `b0ba05a feat(contract): add dry-run replay writer skeleton` | 新增 service + tests + CLI 骨架 |
| 2F-4b-verify | dry-run 实跑确认 0 写入 | —（只读 stdout） | 验证；零代码改动 |
| 2F-4c-prereq | `save_prediction` / `save_outcome` 加 `analysis_date_override` / `captured_at_override` kw-only | `5dbd9ac feat(prediction_store): add optional replay timestamp overrides` | prediction_store + tests |
| 2F-4c-1 | hard cap 50 → 30（real-write 安全收紧）；写路径仍 `not_implemented_for_write` | （并入 4c-2） | 常量 + tests |
| 2F-4c-hygiene-1 | 只读审计 2099 合成行的 FK 反引用（确认 0 引用） | —（只读 sqlite） | 验证；零代码改动 |
| 2F-4c-hygiene-2 | DELETE 2 条 2099 合成行（FK 反序：review → outcome → prediction） | —（直接 sqlite，不入 commit） | DB 清理；无代码改动 |
| **2F-4c-2** | **writer real-write upgrade（本步）** | **`4a66228 feat(contract): replay writer real-write upgrade`** | **service + tests** |
| 2F-4c-2 dry-run verify | `--write` 不带时实跑确认 30 candidates / 0 written | —（只读 stdout） | 验证；零代码改动 |
| 2F-4c-2 write-30 | `--write` 实跑写 30 个 replay pair | —（DB 写入；无 commit） | DB 真写入；无代码改动 |

## 2. 当前 main 状态

- **main 最新 commit：** `4a66228 feat(contract): replay writer real-write upgrade`
- **测试基线：** **2171 passed / 0 failed / 10 skipped**（从 Step 2G 末尾 2094 起累积 +77，覆盖 planner / writer skeleton / prediction_store overrides / writer real-write 整链）
- **新增/修改文件（已进 main）：**
  - [`services/contract_replay_planner.py`](../services/contract_replay_planner.py) — stdlib-only 候选对生成
  - [`services/contract_replay_writer.py`](../services/contract_replay_writer.py) — `run_contract_replay()` real-write 模式 + dry_run 默认；`_LIMIT_HARD_CAP = 30`、`_MIN_HISTORY_ROWS = 20`
  - [`services/prediction_store.py`](../services/prediction_store.py) — `save_prediction(analysis_date_override=...)` / `save_outcome(captured_at_override=...)` kw-only
  - [`scripts/run_contract_replay.py`](../scripts/run_contract_replay.py) — CLI（默认 dry-run，`--write` 触发真写入）
  - `tests/test_contract_replay_planner.py` / `tests/test_contract_replay_writer.py` / `tests/test_prediction_store.py` 增量

## 3. 30-pair 真写入结果

> Backup before write：`avgo_agent.db.backup_pre_replay_30_20260503_162636`（1.7M，未提交）

### 3.1 DB 行数前后对比

| 表 | 前 | 后 | 增量 |
|---|---|---|---|
| `prediction_log` | 3 | **33** | +30 |
| `outcome_log` | 3 | **33** | +30 |
| `prediction_log` 含 `contract_payload_json` 行 | 1 | **31** | +30（每条 replay 都自带 contract） |

> "前"是 hygiene-2 之后基线（5→3 / 5→3 已经清掉两条 2099 合成行）。

### 3.2 30 条 replay 行 `direction_correct` 分布

| `direction_correct` | rows | 备注 |
|---|---|---|
| 1（correct） | **12** | 主推演方向与 D+1 收盘变化同号且 \|change\| ≥ 0.001 |
| 0（wrong） | **10** | 反向且 \|change\| ≥ 0.001 |
| NULL（None） | **8** | \|change\| < `_FLAT_THRESHOLD = 0.001`，无法判定方向 |
| **合计** | **30** | 全部成对（read-outcome-first 半对保护生效） |

- `paired_outcomes` 从 0 → **22**（12 correct + 10 wrong；NULL 不计入"已配对"）
- 8 条 flat（≈ 27%）反映了 AVGO 这段窗口收盘日变化窄幅；与 `_FLAT_THRESHOLD` 的设计一致

### 3.3 snapshot_id 命名

- 全部 30 条 prediction 用 `snapshot_id LIKE 'replay_AVGO_%'`（具体为 `replay_AVGO_<analysis_date>`）
- 与既有 3 条非 replay 行（`step_2c_2_6_local_validation` / `step_2e_4_full_extras_validation` 已被 hygiene-2 清掉，剩下的都是手动验证产物）正交，rollback 边界清晰

## 4. 时间语义验证

| 字段 | min | max |
|---|---|---|
| `prediction_log.analysis_date`（D） | **2024-01-29** | **2024-03-11** |
| `outcome_log.captured_at`（D+1 收盘 16:00 ET 锚定） | **2024-01-30T16:00:00** | **2024-03-12T16:00:00** |

- `analysis_date_override=D` 与 `captured_at_override=D+1T16:00:00` 一一配对，未出现错配 / 翻转
- `now()` 默认行为不受影响（既有 3 条非 replay 行的 `created_at` / `captured_at` 仍为真实当下时间）
- 反对照：`coded_data/AVGO_coded.csv` 起始 2024-01-02；起步 20 行 history 之前的 D 全部被 `_MIN_HISTORY_ROWS=20` 过滤掉，所以 D=2024-01-29 是首个可写日，与设计一致

## 5. 三个只读工具实跑输出

### 5.1 `summarize_confidence_calibration_inputs` (limit=50, symbol=AVGO)

| 字段 | 值 |
|---|---|
| `paired_outcomes` | **22**（12 correct + 10 wrong） |
| `pending_outcomes` | **8**（flat / NULL direction_correct） |
| `valid_payloads` | **30**（全部 replay 行含 contract） |
| `invalid_payloads` | **0**（hygiene-2 清掉了仅有的 2 条 2099 行） |
| `data_gap_report.calibration_ready` | **false** |
| `data_gap_report.contract_outcome_pairs` | **22** |
| `data_gap_report.minimum_recommended_pairs` | 90 |
| `data_gap_report.missing_dimensions` | 仍触发 4 维（pairs < 90 / confidence 三桶覆盖不足 / peer_confirm 覆盖不足 / soft_signal 多样性不足） |
| `confidence_level_summary` | 主要在 medium 桶；分母覆盖小 |
| `primary_score_raw_summary.count` | 30 个真实数值（而非之前的 1 个） |

### 5.2 `summarize_contract_extras_dashboard`（dashboard）

- `total_records=30` / `with_extras=30`
- `final_direction` 分布从单值打开，`five_state_label` 同步铺开
- `peer_signal` / `peer_confirm_count` / `path_risk_level` 仍**几乎单值**——peer cutoff 还没接入，replay 读的是当下时点的 peer 数据（**这是 2F-4c-3 要解决的事**）

### 5.3 `analyze_contract_outcome_correlation`

- 行数从 0 → **22**（直方图 / cell 计数终于有真数据）
- final_direction × direction_correct cell 不再全 0 / 全 NULL，但单元格分母仍小（n≤22 量级）
- 趋势性结论**未达统计意义**——这是 2F-4d / Step 3 的工作

## 6. 关键发现

1. **0-pair 阻塞解除**——这是 Step 2G-1 §3.1 列的第一条阻塞理由，至此**首次有真实 (contract × outcome) 数据**。calibration_inputs / dashboard / correlation 三个工具的输出都从"全 null / 全 pending"转向"有分布"。
2. **`calibration_ready` 仍为 false**——`paired_outcomes=22 < _MIN_RECOMMENDED_PAIRS=90`；同时三类覆盖不足继续触发。这是预期行为，**不是 bug**。Step 2F-4d 的扩量 / Step 3 真 calibration 才是 ready=true 的前提。
3. **27% flat 占比**——`_FLAT_THRESHOLD=0.001` 在 AVGO 这段窗口拒判 8/30。如果未来扩到长窗口或多 ticker，flat 占比可能下降；当前不动这个阈值。
4. **小样本警告**——任何 n=22 量级的桶级分组（confidence_level × direction_correct 等）都是**只看分布、不下结论**的状态。所有现存的 trend / correlation 工具都正确表达了这一点（accuracy=null / 分母 < 阈值标注）。
5. **peer 字段坍缩**——`peer_signal` / `peer_confirm_count` / `path_risk_level` 在 30 条 replay 行内几乎全单值。原因是 writer 的 historical scan 读的是 D 时刻的 AVGO OHLCV，但 peer 数据（NVDA/SOXX/QQQ）走的是当下时点路径，没有按 D cutoff 过滤。**这是 2F-4c-3 的核心目标。**

## 7. 严格约束

本步（含 dry-run-verify / write-30）严守：

- 不改 `predict.py` / `run_predict()` / 4 个 builder（primary / peer / final / simulated_trade）
- 不改 `services/contract_adapter.py` / `services/contract_validator.py`
- 不改 `services/scanner.py` / `services/peer_matcher.py` / `services/encoder.py`
- 不调用 yfinance / 任何网络
- 不动 v1 stub（`services/risk_model.py` / `services/contradiction_engine.py` / `services/confidence_engine.py`）
- 不动 5 个既有只读工具（inspector / trend / diff / correlation / dashboard / calibration_inputs）—— 一行未改
- 不引入 `forced_exclusion=True`，不改 `exclusion_level` 三档语义
- 不改 `_FLAT_THRESHOLD = 0.001`
- `_LIMIT_HARD_CAP=30`：本轮**不**放宽这个常量（90-pair 路线见 §8 Option B）
- 不写 `app.py` / `ui/` / dashboard tab

## 8. Next steps：Option A vs Option B

下一步在两条路径里二选一。两条都不阻塞，但**先做 A**。

### Option A — Step 2F-4c-3 peer 历史 cutoff（**推荐**）

- **目标：** 让 historical scan 在 D 时刻读 NVDA / SOXX / QQQ 的 `<= D` 切片，使 peer_signal / peer_confirm_count / path_risk_level 在 30 条 replay 行里**真正分散**
- **改动：** `services/contract_replay_writer.py::_build_historical_scan_at` 注入按 D cutoff 过滤的 peer OHLCV reader；新增 `coded_data/<PEER>_coded.csv` 的解析 helper
- **不改：** scanner / peer_matcher 一行；预测主链零改动；只是换"传给 scan 的数据"
- **预期：** dashboard 的 peer 字段重新出分布；correlation 终于有 peer cell；calibration_inputs 的 `peer_confirm_count` 维度可以脱掉 missing 标签
- **风险：** 低；纯历史数据切片，无新依赖；现有 30 条 replay 行的 peer 字段会**变化**——所以应在 A 落地后**重写**这 30 条（snapshot_id 仍 `replay_AVGO_%`，DELETE → 重 write）
- **预计 commit 数：** 1（service + tests）

### Option B — Step 2F-4d 90-pair 扩量

- **目标：** 把 `paired_outcomes` 从 22 推到 ≥90，让 `calibration_ready=true`（前提：触发 90 阈值）
- **改动：** 放宽 `_LIMIT_HARD_CAP=30`，准备多 ticker / 长窗口的 coded csv，处理 batch 失败 / 中断恢复
- **不改：** writer 内核逻辑
- **风险：** 中；写量大、批次半失败需要专门的恢复策略；如果跳过 A 直接做 B，30 + 60 条新 replay 的 peer 字段全部坍缩，calibration_ready 即便变 true，证据质量仍差
- **预计 commit 数：** 2~3（cap 放宽 / batch 协议 / 大量 DB 写入）

### 推荐顺序

**A → B → Step 3 真 calibration**。Option A 是 Option B 的"质量前置条件"；先把 30 条 replay 的 peer 信号打开，再扩量。Option B 之后才轮得到 Step 3 在 ≥90 pair + peer 覆盖 + soft_signal 多样性 + anti-false-exclusion 保护层基础上启动真规则。

## 9. Rollback 策略

如果发现 30 条 replay 数据需要回滚（例如准备进 Option A 重写），有两条路径：

### 9.1 SQL 删除（轻量；推荐 Option A 之前）

```sql
-- FK 反序：review → outcome → prediction
DELETE FROM deterministic_review_log
 WHERE prediction_id IN (SELECT id FROM prediction_log WHERE snapshot_id LIKE 'replay_AVGO_%');
DELETE FROM review_log
 WHERE prediction_id IN (SELECT id FROM prediction_log WHERE snapshot_id LIKE 'replay_AVGO_%');
DELETE FROM outcome_log
 WHERE prediction_id IN (SELECT id FROM prediction_log WHERE snapshot_id LIKE 'replay_AVGO_%');
DELETE FROM prediction_log
 WHERE snapshot_id LIKE 'replay_AVGO_%';
```

执行前**先**做 backup（`cp avgo_agent.db avgo_agent.db.backup_pre_replay_rollback_<ts>`）。

### 9.2 文件级回滚（重量级；保险）

`cp avgo_agent.db.backup_pre_replay_30_20260503_162636 avgo_agent.db` 整张表回到 hygiene-2 之后基线（3 / 3）。

### 9.3 不要做的事

- 不要 `DELETE FROM prediction_log` 不带 snapshot_id 谓词——会删掉手动验证行
- 不要直接编辑 .db 文件（用 sqlite3 CLI 或 Python sqlite3）
- 不要在 backup 之前回滚

## 10. Step 2 系列状态更新

| Step | 子步 | 状态 | 主要 commit |
|---|---|---|---|
| 2A | 设计冻结 | done | `step_2a_*` 文档（无代码） |
| 2B | projection fieldization 02/03/06 | done | `0fccc72` / `9aca3f2` / `c2d1d34` |
| 2C | 04 / 05 extras | done | `8f689a2` / `c188725` |
| 2D | 07 simulated_trade extras | done | `f125d45` |
| 2E | dashboard 工具 + extras 收口 | done | `524552b` / `ddb10e1` |
| 2F-1~3 | calibration_inputs + 0-pair 诊断 | done | `7500b5b` / `5ab64bf` |
| 2F-4 plan | 真实回放方案 | done | `e9b44e2` |
| 2F-4a | planner | done | `4c89d98` |
| 2F-4b | writer skeleton | done | `b0ba05a` |
| 2F-4c-prereq | timestamp overrides | done | `5dbd9ac` |
| **2F-4c-2** | **real-write upgrade + 30-pair 实写入** | **done（本步）** | **`4a66228`** |
| 2F-4c-3 | peer 历史 cutoff（Option A） | **next** | — |
| 2F-4d | 90-pair 扩量（Option B） | pending | — |
| 2G-1~2 | exclusion soft/hard 设计冻结 | done | `9d55a80` / `faadf01` |
| Step 3 | 真 calibration / 真 exclusion | blocked on 2F-4c-3 + 2F-4d | — |

> **核心进度信号：** Step 2F-4 系列把"contract pipeline 有数据"从理论变成事实。Step 2 系列在 Option A 落地后即可全部结案；Step 3 之前唯一的硬阻塞是数据规模 + peer 覆盖。

---

**生成于：** 2026-05-03（Step 2F-4c-2 收尾）
**作者：** Claude Code（对话内 builder）
**类型：** handoff snapshot；**不**是新需求规格
