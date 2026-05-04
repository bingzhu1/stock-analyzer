# Step 3A-4 — Third Window Replay Checkpoint

> 状态：Step 3B-1 holdout FAIL 后按推荐扩第三窗口（2023-01-03 → 2023-07-11）。第三窗口 130 records 干净写入：0 dup / 0 skip / `status=ok`。整体 250 → **380 records / 193 → 286 paired**。Holdout 重跑双向：**Method A（W3 design → W1+W2）大幅改善**（calibrated_high acc 0.333 → **0.611**，R4/Q3 真触发了 4+4 次）；但 **Method B（W1+W2 design → W3）仍崩**（calibrated_high bucket 完全为空）。**Step 3B-1 FAIL 状态不解除**，更新为 *partial improvement but still FAIL*。pos20 单调 bias 跨 380 records 验证稳健（-36 → +5 → +36 → +53）—— **regime feature 是真的，但 4×4 lookup table 不是合适承载方式**。建议**暂停 Step 3 calibration 系列**，转 Step 2G / dashboard 升级。
> 本文件只写文档，不改代码，不写 DB，不 commit，不 push。

## 1. 当前完成状态

| 子步 | 主题 | 状态 |
|---|---|---|
| Step 3B-1 holdout FAIL | 4×4 lookup 在 250 records 上 holdout 失败 | ✅ commit `522a1eb` |
| Step 3A-4 dry-run planning | 第三窗口 candidate / overlap 评估（read-only） | ✅ |
| Step 3A-4 write | 备份 + dry-run + `--write 130` + 验证 + holdout 重跑 | ✅（上一轮） |
| **Step 3A-4 checkpoint** | **本文件：固定 380/286 baseline + holdout 重跑结果 + Step 3 暂停决定** | ✅ |
| Step 3B-2 / 3B-3 / 3B-4 / 3C | sidecar / simulator / 顶层 score 暴露 | **冻结**（FAIL 不解除） |
| Step 2G / dashboard | exclusion 重审 / 工具升级 | 推荐转向（独立路径） |

## 2. 当前 main 状态

- **main 最新 commit：** `522a1eb docs(contract): Step 3B-1 holdout simulation FAIL`
- **测试基线：** **2233 passed / 0 failed / 10 skipped**（与 3B-1 commit 时一致；本轮无代码 / 测试 / schema 改动）
- 本轮 0 代码 / 0 测试 / 0 DB schema 改动；**有** DB 写入（130 新 prediction + 130 新 outcome）

## 3. 写入前 baseline

| 字段 | 值 |
|---|---|
| `prediction_log` total | 253 |
| `outcome_log` total | 253 |
| `replay_AVGO_%` predictions | 250 |
| `replay_AVGO_%` outcomes (join) | 250 |
| `paired_outcomes` | 193 |
| `calibration_ready` | True |
| `analysis_date` 范围 | 2023-08-07 → 2024-08-02 |
| `confidence_level_summary` | high 51p (0.431) / medium 29p (0.414) / low 20p (0.500) |

## 4. 第三窗口 dry-run

CLI: `python3 scripts/run_contract_replay.py --symbol AVGO --start 2023-01-01 --limit 130`

| 字段 | 值 |
|---|---|
| `status` | `ok` |
| `dry_run` | True |
| `candidate_pair_count` | **130** |
| `would_write_count` | **130** |
| `written_prediction_count / outcome_count` | 0 / 0 |
| `first_pair` | `as_of=2023-01-03, prediction_for=2023-01-04` |
| `last_pair` | `as_of=2023-07-11, prediction_for=2023-07-12` |
| `anti_lookahead_check.all_pairs_satisfy_d_lt_d_plus_1` | `True` |
| `last_available_date` | `2023-07-12` |
| 与现有 250 baseline 重叠 | **0**（无 dup） |
| 预计 new write | **130** |

## 5. 备份

- 新备份：**`avgo_agent.db.backup_pre_3a4_20260504_023331`** — **7.6M**
- 既有 backup 全部保留：
  - `avgo_agent.db.backup_pre_2099_hygiene_20260503_160409` (1.7M)
  - `avgo_agent.db.backup_pre_replay_30_20260503_162636` (1.7M)
  - `avgo_agent.db.backup_pre_4c3_rewrite_20260503_235604` (2.4M)
  - `avgo_agent.db.backup_pre_replay_130_20260504_003707` (2.4M)
  - `avgo_agent.db.backup_pre_3a3_20260504_013453` (4.7M)
  - `avgo_agent.db.backup_step_2c_2_6` (1.6M)
- DB / backup 文件不进入 git。

## 6. `--write` 结果

| 字段 | 值 |
|---|---|
| `status` | **`ok`**（无 partial，无 skip） |
| `dry_run` | False |
| `candidate_pair_count` | 130 |
| `attempted_write_count` | 130 |
| **`written_prediction_count`** | **130** |
| **`written_outcome_count`** | **130** |
| `skipped_pairs` | **0** |
| skip reasons | 无 dup / 无 insufficient_history / 无 no_outcome_data |
| 第一个新增 | `as_of=2023-01-03, prediction_for=2023-01-04` |
| 最后一个新增 | `as_of=2023-07-11, prediction_for=2023-07-12` |

writer notes 自报：
- "dry_run=False: wrote 130 prediction/outcome pair(s); skipped 0"
- "all writes went through save_prediction / save_outcome — no raw INSERT was used"
- "peer cutoff: NVDA / SOXX / QQQ relative-strength computed with Date <= D from coded_data; missing peers degrade to 'unavailable'"
- "duplicate guard: pairs whose snapshot_id already exists in prediction_log are skipped with reason='snapshot_id_already_exists' (no run_predict / save_prediction / save_outcome invoked)"

## 7. 写入后 DB 验证

| 字段 | 值 | 期望 |
|---|---|---|
| `prediction_log` total | **383** | ✅ |
| `outcome_log` total | **383** | ✅ |
| `replay_AVGO_%` predictions | **380** | ✅ |
| `replay_AVGO_%` outcomes (join) | **380** | ✅ |
| `replay_AVGO_%` rows with `contract_payload_json` | **380 / 380** | ✅ |
| **duplicate `snapshot_id`** | **0** | ✅（duplicate guard 守住） |
| 2099 predictions | 0 | ✅ |
| `analysis_date` 范围 | **2023-01-03 → 2024-08-02** | ✅ 跨 ~19 个月 |
| `prediction_for_date` 范围 | **2023-01-04 → 2024-08-05** | ✅ |
| `outcome.captured_at` 范围 | **2023-01-04T16:00:00 → 2024-08-05T16:00:00** | ✅ 全 16:00 |
| `calibration_ready` | **True** | ✅ |
| `paired_outcomes` | **286** | 193 → 286，+93 |
| `missing_dimensions` | `[]` | ✅ |

## 8. 三件套工具输出（POST-WRITE）

### 8.1 `summarize_confidence_calibration_inputs --limit 450 --symbol AVGO`
- `valid_payloads = 380`
- `records_with_confidence_extras = 380`
- **`paired_outcomes = 286`**（193 → 286，+93）
- `pending_outcomes = 94`
- `calibration_ready = True`
- `missing_dimensions = []`
- `confidence_level_summary`：
  - **high**: samples 153, paired 141, accuracy **0.447**
  - **medium**: samples 87, paired 84, accuracy **0.524**
  - **low**: samples 140, paired 61, accuracy **0.525**（79 pending，多在中性桶）
- `primary_score_raw_summary`：count=380, min=-4.25, max=4.25, **mean=+0.589**

### 8.2 `dashboard_contract_extras`
- `valid_payloads = 380`
- `peer_path_risk_direction`: lower 132 / higher 131 / unchanged 117（保持真实分布）
- `soft_signal`: none 197 / high_path_risk 99 / peer_weaken 84
- `path_risk_level`: low 135 / high 158 / medium 87
- `peer_adjusted_confidence`: high 153 / low 140 / medium 87

### 8.3 `correlate_contract_outcomes`
- `valid_contracts = 380, paired = 286, pending = 94`
- `final_direction`：
  - **偏多** 200 (acc **0.500**) / 偏空 102 (acc **0.457**) / 中性 78 (全 pending)
- `confidence_level`（同 8.1）
- `final_five_state`：小涨 113 (0.509) / 震荡 208 (0.460) / 小跌 59 (0.500)

## 9. Holdout rerun 结果

> 三段时间窗口：
> - **W3** = 2023-01-03 → 2023-07-11 (130 records，本步骤新写)
> - **W2** = 2023-08-07 → 2024-01-26 (120 records，Step 3A-3 写入)
> - **W1** = 2024-01-29 → 2024-08-02 (130 records，Step 2F-4d-2 写入)

### 9.1 Method A：W3 design (130) → W1+W2 holdout (250)

**W3 fitted lookup**（baseline acc 0.473）：
- 4 cells `paired ≥ 10`；最强 cell `weak_bull × high_mid` = 16p / acc 0.625 → `cal=high`
- 唯一 calibrated_high cell：`weak_bull × high_mid`

**W1+W2 ORIGINAL**（无 calibration）：
| bucket | n | paired | accuracy |
|---|---|---|---|
| high | 114 | 106 | 0.472 |
| medium | 52 | 50 | 0.460 |
| low | 84 | 37 | 0.595 |

**W1+W2 CALIBRATED**：
| bucket | n | paired | accuracy |
|---|---|---|---|
| **high** | **18** | **18** | **0.611** ← 比 Step 3B-1 时 0.333 大幅改善 |
| medium | 59 | 59 | 0.458 |
| low | 116 | 116 | 0.491 |

- **R4 downgraded: 4**（vs Step 3B-1 时 0）
- **Q3 downgraded: 4**（vs Step 3B-1 时 0）
- Coverage: 100% (193/193 paired records assigned)

**结论**：相比 Step 3B-1 明显改善 —— calibrated_high 提升 27.8 ppts；R4/Q3 规则真的触发了；high > low > medium（low 与 medium 微反，但 high 显著领先）。

### 9.2 Method B：W1+W2 design (250) → W3 holdout (130)

**W1+W2 fitted lookup**（baseline acc 0.492）：
- **6 cells `paired ≥ 10`** 但**所有 cells acc 都 < 0.60**
- → **0 个 cell 进 high** → calibrated_high bucket 完全空

**W3 ORIGINAL**：
| bucket | n | paired | accuracy |
|---|---|---|---|
| high | 39 | 35 | **0.371** ← W3 也是 high < medium 反向 |
| medium | 35 | 34 | 0.618 |
| low | 56 | 24 | 0.417 |

**W3 CALIBRATED**：
| bucket | n | paired | accuracy |
|---|---|---|---|
| **high** | **0** | — | **n/a (空)** ❌ |
| medium | 75 | 75 | 0.453 |
| low | 18 | 18 | 0.556 |

- R4 downgraded: 0；Q3 downgraded: 0
- Coverage: 100%

**结论**：仍崩 —— calibrated_high 完全消失；W3 holdout 上 medium < low（partial inversion 仍存）。Method B 与 Step 3B-1 时同样的失败模式。

## 10. Combined diagnostics（380 records）

### 10.1 `avgo_pos_20d` quartile bias（regime feature 验证）

| 分位 | 边界 | n | paired | acc | pred_bull | actual_up | **bias** |
|---|---|---|---|---|---|---|---|
| Q1 | ≤ 0.43 | 96 | 75 | 0.453 | 0.23 | 0.59 | **-0.36** |
| Q2 | (0.43, 0.63] | 95 | 59 | 0.542 | 0.61 | 0.56 | +0.05 |
| Q3 | (0.63, 0.82] | 95 | 69 | 0.551 | 0.84 | 0.48 | **+0.36** |
| Q4 | > 0.82 | 94 | 83 | 0.422 | 0.98 | 0.45 | **+0.53** |

✅ **pos20 单调 bias swing 跨 380 records 仍存在**（-36 → +5 → +36 → +53）。Step 3B-0 在 250 records 上发现的 bias swing（-36 → +9 → +40 → +47）经第三窗口扩展后**更强**。**regime feature 是真的**。

### 10.2 `peer_adjustment` label
| label | paired | accuracy |
|---|---|---|
| **upgrade** | 120 | **0.450** |
| hold | 102 | 0.510 |
| downgrade | 64 | 0.516 |
| flip_to_neutral | 0 | n/a |

→ peer reinforce inversion **缩小但仍存在**（W1-only 时 0.364 vs 0.524 = -16ppts；现在 380 records 0.450 vs 0.516 = -7ppts）。

### 10.3 `peer_confirm_count`
| pcc | paired | accuracy |
|---|---|---|
| 0 | 87 | 0.517 |
| 1 | 79 | 0.506 |
| **2** | 56 | **0.446** |
| 3 | 64 | 0.453 |

→ pcc=0/1 ≈ 0.51，pcc≥2 ≈ 0.45，仍微弱反向。

### 10.4 Per-window overall
| Window | paired | accuracy | pred偏多/paired |
|---|---|---|---|
| W3 (2023-01..07) | 93 | **0.473** | 64/93 = 69% |
| W2 (2023-08..2024-01) | 93 | **0.548** | 64/93 = 69% |
| W1 (2024-01..08) | 100 | **0.440** | 64/100 = 64% |

→ 三窗口都呈"系统性偏多 64-69%"；**结构性 long bias 经三窗口确认**，不是单一窗口现象。

## 11. 是否解除 Step 3B-1 FAIL 状态

❌ **不解除**。

**6 项标准重新评估**：
| # | 标准 | Method A (W3 → W1+W2) | Method B (W1+W2 → W3) | Step 3B-1 时 |
|---|---|---|---|---|
| 1 | calibrated bucket monotonicity | partial（high 0.611 > low 0.491 > medium 0.458） | high 不存在 | ❌ |
| 2 | R4/Q3 触发 + 子集 acc ≥ 0.45 | ✅ 4+4 触发（vs 0+0） | 0 触发 | ❌ |
| 3 | probability calibration deviation | 部分改善（cal_high 0.611 vs W3-fit 0.625，dev 仅 0.014） | 不可测（high 空） | ❌ |
| 4 | direction unchanged | ✅ | ✅ | ✅ |
| 5 | coverage ≥ 80% | overall 100%；calibrated_high 仅 9% (18/193) | 100% | ✅ |
| 6 | holdout 双向 robustness | A 跑得动 | B 崩 | ❌ |

**通过 2.5 / 6**（vs Step 3B-1 时 2/6）：Method A 部分通过 1, 2, 3；Method B 仍崩 6 → 单方向 robustness 失败 ⇒ FAIL 不解除。

**Step 3B-2 / 3B-3 / 3B-4 / 3C 仍冻结**。

## 12. 下一步建议

### 推荐：**暂停 Step 3 calibration 系列，转 Step 2G / dashboard**

**理由**：
1. **样本量已达项目可控量级**（380 records / 286 paired）：Step 3A-3 / 3A-4 都已扩窗口；继续加（Step 3A-5）边际收益小；
2. **4×4 lookup 第三次扩样本仍 partial FAIL**：
   - Step 3B-1 (250 records): calibrated high 0.333；
   - Step 3A-4 Method A (380 records, W3 design): calibrated high 0.611（改善但 coverage 9%）；
   - Step 3A-4 Method B (380 records, W1+W2 design): calibrated high 不存在（仍崩）；
   - 双向 robustness 没解决，单向数据填充救不了；
3. **`pos20` regime feature 已验证稳健**（380 records 单调 bias），但 4×4 lookup 的离散化破坏了它的连续性；正确承载方式应是连续平滑公式（logistic / kernel），但**这需要写 Python module，超 Step 3 当前 docs-only 范围**；
4. **Step 2G exclusion 重审 / dashboard 升级**与 calibration 正交：
   - 不依赖更多 replay 数据；
   - 不依赖 Step 3 通过；
   - 价值更确定（Step 2G: 取消 / 重设计 soft → hard 升级路径；dashboard: surface regime feature 给运营查阅）；
5. **Step 3B 设计 §11 明确禁止反复抽样调参**：已经做 3 轮 holdout 重试，再继续就是 development data 过拟合；
6. **2026-01-01 之后的 final test range 仍未触碰** ✓（W3 起点 2023-01-03 远早于 cutoff）—— 暂停 Step 3 不影响 final test set 干净度。

### 不推荐的下一步
| Option | 不推荐理由 |
|---|---|
| 第四个时间窗口（如 2022-08..12） | 边际效用低（M_B 第三次仍崩说明结构问题）；2022 大跌 regime 可能让 lookup 更不稳 |
| 改架构到 logistic / kernel | 需要写 module + tests，超 Step 3 当前 docs-only 边界；待将来另起 step |
| 继续 4×4 lookup + 调阈值（如 high cutoff 0.55 而非 0.60） | 工程 hack；放低标准不可持续；Step 3B 设计 §13 明确反对 |
| 直接进 Step 3B-2 sidecar schema | FAIL 不解除，schema 设计无依据 |

### Step 2G / dashboard 任务清单（参考）

**Step 2G 重审**（独立路径）：
- 当前 `soft_signal != none` 在 380 records 上比 `none` 更准（这一现象 Step 3A-2 / 3A-3 / 3A-4 都重现）；
- 不应把 `soft_signal != none` 升级为 hard exclusion；
- Step 2G 应**取消"soft → hard 升级"**这条路径，或重新设计触发条件（不依赖 soft_signal）。

**Dashboard 升级**（独立路径）：
- 把 pos20 quartile bias / R4 触发率 / 月度 accuracy 等 regime metrics surface 到 read-only 工具；
- 让运营能在 contract pipeline 之外查看 regime feature 表现，但不动 `predict.py` / `confidence_engine`；
- 工作量小（只读脚本，参考 `dashboard_contract_extras.py` 风格）。

## 13. 2026 final test cutoff

- ✅ 本轮第三窗口 **2023-01-03 → 2023-07-11**，远早于 **2026-01-01**；
- ✅ 整个 380 records replay range（2023-01-03 → 2024-08-02）完全落在 development range 内；
- ✅ 未触碰 final test range（2026-01-01 之后）；
- ✅ Validation windows（2024-08-06..2025-12-31 + 2023-01-02 之前的有限段）也未动用；
- 本 checkpoint 继续遵守：**2026-01-01 之后作为系统全部完成后的最终测试集，不用于开发期 design / calibration / tuning / sanity check**；
- Step 2G / dashboard 暂停推荐路径同样**不会触碰** final test range。

## 14. 严守边界（本轮已遵守）

- ❌ 没改任何代码（`predict.py` / `services/*.py` / `scripts/*.py` / `tests/*.py` / `scanner.py` / confidence_engine 0 字节变化）
- ❌ 没新增测试
- ❌ 没 commit / push
- ❌ 没改 DB schema
- ❌ 没删除现有 250 条 baseline replay
- ❌ 没超过 `--limit 130`
- ❌ 没接 yfinance / 网络
- ❌ 没接 trading API / longbridge / broker / paper_trade
- ❌ 没升级 contract 04 / 05 / 07 顶层字段
- ❌ 没把 `soft_signal != none` 升级为 hard exclusion
- ❌ 没触碰 stash / .claude/worktrees/ / logs/prediction_log.jsonl
- ❌ 没 add 任何 `avgo_agent.db.backup_*` 文件
- ❌ 没触碰 2026-01-01 之后 final test range（W3 起点 2023-01-03 远早于 cutoff）
- ✅ 备份在前；dry-run 在前；`--write` 显式触发；写入 130 / 0 skip；DB 边界正确扩展；三件套工具 + holdout 双向验证 + combined regime diagnostics 都已跑过
- ✅ 仅新增 1 个 markdown checkpoint
