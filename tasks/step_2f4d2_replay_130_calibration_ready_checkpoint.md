# Step 2F-4d-2 — 130-Pair Replay Calibration-Ready Checkpoint

> 状态：4d 系列全部落地。本地 DB 完成 130-pair peer-aware replay，`calibration_ready` 第一次翻 `True`，`missing_dimensions` 清空。这是 Step 2F 系列自启动以来第一个让 calibration 工具不再报缺口的快照。
> 本文件只写文档，不改代码，不写 DB，不 commit，不 push。

## 1. 当前完成状态

| 子步 | 主题 | 状态 |
|---|---|---|
| Step 2F-4d-1 | 90 / 120 / 130 / 2023-10-01 起 dry-run planning（只读） | ✅ |
| Step 2F-4d-2-prereq-1 | replay writer duplicate guard | ✅ commit `19800ac` |
| Step 2F-4d-2-prereq-2 | replay writer hard cap 30 → 130 | ✅ commit `7d685a6` |
| Step 2F-4d-2-prereq-2b | CLI `--help` 跟随 live `_LIMIT_HARD_CAP` | ✅ commit `f26387b` |
| **Step 2F-4d-2** | **130-pair dry-run + `--write` → calibration_ready=true** | ✅（本文件 checkpoint） |

## 2. 当前 main 状态

- **main 最新 commit：** `f26387b fix(contract): wire run_contract_replay CLI help to live hard cap`
- **测试基线：** **2233 passed / 0 failed / 10 skipped**（与 prereq-2b commit 时一致；本步骤无代码改动）
- **关键文件（已进 main）：**
  - [services/contract_replay_writer.py](../services/contract_replay_writer.py) — peer-aware writer + duplicate guard + hard cap 130
  - [scripts/run_contract_replay.py](../scripts/run_contract_replay.py) — CLI（默认 dry-run；`--limit` 默认 30，help 跟随 cap）
  - [services/contract_calibration_inputs.py](../services/contract_calibration_inputs.py) — calibration 输入聚合（`calibration_ready` 判定来源）
  - [scripts/summarize_confidence_calibration_inputs.py](../scripts/summarize_confidence_calibration_inputs.py) — read-only 诊断
  - [scripts/dashboard_contract_extras.py](../scripts/dashboard_contract_extras.py) — read-only contract 字段汇总
  - [scripts/correlate_contract_outcomes.py](../scripts/correlate_contract_outcomes.py) — read-only direction / confidence accuracy 表

## 3. 写入前 baseline

| 字段 | 值 |
|---|---|
| `prediction_log` total | 33 |
| `outcome_log` total | 33 |
| `replay_AVGO_%` predictions | 30 |
| `replay_AVGO_%` outcomes (join) | 30 |
| 2099 predictions | 0 |
| **`paired_outcomes`** | **22** |
| **`calibration_ready`** | **False** |
| **`missing_dimensions`** | **`["insufficient pairs: have 22, recommend ≥ 90"]`** |

30 条 baseline = Step 2F-4c-3-rewrite 写入的 peer-aware replay（commit chain `d5d05af` → `aba2e7a`）。

## 4. Dry-run 130 结果

| 字段 | 值 |
|---|---|
| `status` | `ok` |
| `dry_run` | `True` |
| `requested_limit` | `130` |
| `candidate_pair_count` | `130` |
| `would_write_count` | `130` |
| `written_prediction_count` | `0` |
| `written_outcome_count` | `0` |
| `first_pair` | `as_of=2024-01-29, prediction_for=2024-01-30` |
| `last_pair` | `as_of=2024-08-02, prediction_for=2024-08-05` |
| `planner_result.anti_lookahead_check.all_pairs_satisfy_d_lt_d_plus_1` | `True` |
| `planner_result.anti_lookahead_check.last_available_date` | `2024-08-05` |
| notes | 含 `"writer hard cap on limit is 130"`（f-string 跟随常量） |

## 5. 备份

- 新备份：**`avgo_agent.db.backup_pre_replay_130_20260504_003707`** — 2.4M
- 既有 backup 全部保留：
  - `avgo_agent.db.backup_pre_2099_hygiene_20260503_160409`（1.7M）
  - `avgo_agent.db.backup_pre_replay_30_20260503_162636`（1.7M）
  - `avgo_agent.db.backup_pre_4c3_rewrite_20260503_235604`（2.4M）
  - `avgo_agent.db.backup_step_2c_2_6`（1.6M）
- 本 checkpoint **不提交** DB 文件 / backup 文件 / `logs/prediction_log.jsonl`。

## 6. `--write 130` 结果

| 字段 | 值 | 期望 |
|---|---|---|
| `status` | **`partial`** | partial（混合写入 + dup-skip） |
| `dry_run` | `False` | ✓ |
| `requested_limit` | `130` | ✓ |
| `candidate_pair_count` | `130` | ✓ |
| `attempted_write_count` | `130` | ✓ |
| **`written_prediction_count`** | **`100`** | 130 − 30 dup ✓ |
| **`written_outcome_count`** | **`100`** | ✓ |
| `skipped_pairs` total | `30` | ✓ |
| **唯一 skip reason** | **`snapshot_id_already_exists: 30`** | duplicate guard 命中所有旧 30 条 ✓ |
| 第一个新增 pair | `as_of=2024-03-12, prediction_for=2024-03-13`（旧 30 条之后下一交易日） | ✓ |
| 最后一个新增 pair | `as_of=2024-08-02, prediction_for=2024-08-05` | ✓ |

writer notes 自报：
- "dry_run=False: wrote 100 prediction/outcome pair(s); skipped 30"
- "all writes went through save_prediction / save_outcome — no raw INSERT was used"
- "peer cutoff: NVDA / SOXX / QQQ relative-strength computed with Date <= D from coded_data; missing peers degrade to 'unavailable'"
- "duplicate guard: pairs whose snapshot_id already exists in prediction_log are skipped with reason='snapshot_id_already_exists' (no run_predict / save_prediction / save_outcome invoked)"

## 7. 写入后 DB 验证

| 字段 | 值 | 期望 |
|---|---|---|
| `prediction_log` total | **133** | 33 + 100 = 133 ✓ |
| `outcome_log` total | **133** | ✓ |
| `replay_AVGO_%` predictions | **130** | 30 + 100 = 130 ✓ |
| `replay_AVGO_%` outcomes (join) | **130** | ✓ |
| `replay_AVGO_%` rows with `contract_payload_json` | **130 / 130** | ✓ |
| **duplicate `snapshot_id` 行数** | **`0`** | duplicate guard 守住 ✓ |
| 2099 predictions | `0` | ✓ |
| `analysis_date` 范围 | `2024-01-29 → 2024-08-02` | 旧 + 新 连续 |
| `prediction_for_date` 范围 | `2024-01-30 → 2024-08-05` | ✓ |
| `outcome.captured_at` 范围 | `2024-01-30T16:00:00 → 2024-08-05T16:00:00` | 全部 16:00:00，`captured_at_override` 工作 ✓ |

## 8. `calibration_inputs` 输出

| 字段 | 值 |
|---|---|
| `status` | `ok` |
| `valid_payloads` | `130` |
| `records_with_confidence_extras` | `130` |
| **`paired_outcomes` / `contract_outcome_pairs`** | **`100`**（22 → 100，+78） |
| `pending_outcomes` | `30` |
| `minimum_recommended_pairs` | `90` |
| **`calibration_ready`** | **`True`** 🎯 |
| **`missing_dimensions`** | **`[]`** 🎯 |

`confidence_level_summary`：
- `medium`: samples 30, correct 12, wrong 17, pending 1, **accuracy 0.414**
- `high`:   samples 53, correct 22, wrong 29, pending 2, **accuracy 0.431**
- `low`:    samples 47, correct 10, wrong 10, pending 27, **accuracy 0.500**

`primary_score_raw_summary`：
- `count = 130`
- `min = -4.25`
- `max = 4.0`
- `mean = 0.425`

## 9. `dashboard` 输出

| 字段 | 值 |
|---|---|
| `status` | `ok` |
| `records_scanned` | `133` |
| `valid_payloads` | `130` |
| `latest_snapshot.prediction_for_date` | `2024-08-05` |

`peer_path_risk_direction`：
- `higher: 37`
- `lower: 46`
- `unchanged: 47`

`soft_signal`（exclusion）：
- `none: 70`
- `high_path_risk: 34`
- `peer_weaken: 26`

`path_risk_level`：
- `high: 52`
- `medium: 31`
- `low: 47`

`peer_adjusted_confidence` / `final_confidence` / `probability_bucket`（三者同分布）：
- `medium: 30`
- `high: 53`
- `low: 47`

## 10. `correlation` 输出

| 字段 | 值 |
|---|---|
| `status` | `ok` |
| `valid_contracts` | `130` |
| `paired_outcomes` | `100` |
| `pending_outcomes` | `30` |

`final_direction`：
- `偏多`: samples 66, **accuracy 0.453**
- `偏空`: samples 38, **accuracy 0.417`
- `中性`: samples 26, all pending（`accuracy = null`）

`confidence_level`（与 §8 一致）：
- `medium`: accuracy **0.414**
- `high`:   accuracy **0.431**
- `low`:    accuracy **0.500**

`final_five_state`：
- `震荡`: samples 68, accuracy 0.439
- `小跌`: samples 27, accuracy 0.360
- `小涨`: samples 35, accuracy 0.500

## 11. 关键结论

- ✅ **`calibration_ready` 第一次变 `True`**（自 Step 2F 启动以来）；`missing_dimensions = []`，calibration 工具不再报缺口。
- ✅ **Step 2F 系列最大阻塞已解除**（peer 维度坍缩 + paired < 90 两个原本的 gap 都不复存在）。
- ⚠️ **这不等于可以马上动 confidence score**。三个独立信号都说"先诊断别动手"：
  1. `confidence_level` 三档 accuracy 都在 0.41–0.50 区间，离 random（0.5）非常近；
  2. **`high` accuracy (0.431) 不显著优于 `low` accuracy (0.500)**，`low` 反而最高，跟"高 confidence 应该更准"的直觉相反 —— 说明当前 confidence 评分**没有体现预测力**；
  3. `final_direction` 三档（偏多 / 偏空 / 中性）都 ≤ 0.453；`final_five_state` 三档都 ≤ 0.50 —— direction 判定本身也偏弱。
- ✅ **peer 维度仍稳定**：peer_path_risk_direction higher / lower / unchanged 三态接近 1:1.2:1.3 的比例（37 / 46 / 47），不是"全部坍缩到 unchanged"或"全部 higher"那种病态分布；soft_signal `peer_weaken` 也独立有 26 条。
- 🚦 **下一步应进入 Step 3 calibration *诊断*，不是 calibration *写入***。直接改 `confidence_engine` 或把 `simulated_trade.score` 从 `0.0` 改真值都是过早；应先用这 130 条做只读分析。
- 🚦 **exclusion soft/hard（Step 2G）仍需单独评估**，不能因为 calibration 这边 ready 就自动启用 hard exclusion；soft / hard 的判定逻辑跟 calibration 无依赖。

## 12. 严守边界（本轮已遵守）

- ❌ 没改任何代码（`services/` / `scripts/` / `tests/` 0 字节变化）
- ❌ 没新增测试
- ❌ 没 commit / push DB
- ❌ 没改 DB schema
- ❌ 没删除现有 30 条 replay（duplicate guard 自动识别为 dup 并保留）
- ❌ 没超过 `--limit 130`
- ❌ 没跑 300 / 1000
- ❌ 没接 yfinance / 网络
- ❌ 没接 trading API / longbridge / broker / paper_trade
- ❌ **没升级 contract 04（exclusion）required 字段**：`soft_signal` / `path_risk_level` / `peer_path_risk_direction` 仍属 `extras`，不是顶层 required；exclusion 仍是 *soft signal*，不主动 block 推演
- ❌ **没升级 contract 05（confidence）score 字段**：`primary_score_raw` / `final_confidence` 仍只在 `extras`，没有引入 `confidence.score: float` 这种顶层字段
- ❌ **07 `simulated_trade` 仍 `no_trade`**：`trade_engine_enabled = False` / `has_key_price_levels = False`，本步未触发任何 trade 字段升级

## 13. 下一步建议

> **强制顺序：诊断在前，规则在后。**

### Step 3A：calibration diagnostics（只读，无代码 / 不动 DB）
1. **`confidence_level` 是否有预测力？**
   - 当前 high (0.431) / medium (0.414) / low (0.500) — 检查这是不是统计噪声；30 / 53 / 47 样本数下置信区间多大？
   - low 全部 27 pending（中性），仅 20 paired，"low 0.500 准"很可能是小样本伪信号 —— 把 pending 拆开分析。
2. **`primary_score_raw` 与 `direction_correct` 是否相关？**
   - count=130, range -4.25 → 4.0, mean 0.425 — 把每个 pair 的 raw score 与 0/1/null 做 binning，看高分 vs 低分组的 hit rate 差。
3. **`peer_path_risk_direction` 是否影响命中率？**
   - higher (37) / lower (46) / unchanged (47) — 三组 direction_correct 分布是否不同；如果"peer 同向 / 逆向"对应不同 hit rate，说明 peer 是有信号的。
4. **`soft_signal` 是否有风险提示价值？**
   - none (70) / high_path_risk (34) / peer_weaken (26) — `high_path_risk` 那 34 条是不是真的更容易出错？如果是，soft → hard 升级有依据；如果不是，soft 也别推 hard。
5. **`final_direction` 哪些分桶最差？**
   - 偏多 0.453 / 偏空 0.417 — 偏空略差但样本少；细看分桶 × 五态交叉表（偏多+小涨 / 偏多+震荡 / 偏空+小跌 / 偏空+震荡）哪个最差。
6. **`final_five_state` 哪些最差？**
   - 小跌 0.360 是最低，27 条 → 是不是 AVGO 这段窗口跌时反而走平？这种是 timing 问题还是模型问题？

### Step 3B：calibration formula 设计（只读 + 写文档）
基于 3A 输出再决定：
- 是不是要重定义 `confidence_level` 边界（现在 medium=primary∈[55, 70], high≥70 之类）；
- 是不是要把 `peer_path_risk_direction` 接到 confidence 调整（4c-3 已经把 peer 信号注入 scan，但是否要接到 score 公式还没决定）；
- 是不是要把 `soft_signal` 升级为 hard exclusion（这个其实是 Step 2G 范围）。
- **本阶段不动代码**。

### Step 3C：小范围写入 score 字段（如果 3B 决定了）
- 先在 contract `extras` 里加新 `confidence.score: float` 字段，**不要**直接动 03 顶层；
- 加 dry-run 工具校对新 score 与旧 `primary_score_raw` 一致；
- 全量回放 130 条做对照；
- 之后再考虑升 03 / 05 顶层。

### Step 2G exclusion soft/hard（独立路径）
- 不依赖 Step 3；可以并行评估；
- 但 hard 升级前必须做对照实验（hard 后 hit rate 是否上升）。

### 不要做的事
- ❌ 直接把 `simulated_trade.score` 从 `0.0` 改真值
- ❌ 直接调 `confidence_engine` 的阈值
- ❌ 直接打开 `trade_engine_enabled`
- ❌ 用这 130 条数据外推到其他 symbol —— 当前 baseline 是 AVGO 单 symbol 的窄窗口
