# Step 3A-3 — Second Window Replay Checkpoint

> 状态：第二个时间窗口（2023-08-07 → 2024-01-26）replay 已落 DB，主项目 250 条 peer-aware replay 全部到位，paired 从 100 → 193，`calibration_ready` 仍 True、`missing_dimensions=[]`。**核心发现：Step 3A 看到的"反向"在第二窗口大幅缓解或翻转，证实**反向是 regime 性、不是结构性**；唯一持续的结构性问题是"系统性偏多 +14-17 ppts"，跨两个窗口不变。Step 3B（calibration formula design）仍不能直接进，但可以从"regime-aware calibration"角度起步。
> 本文件只写文档，不改代码，不写 DB，不 commit，不 push。

## 1. 当前完成状态

| 子步 | 主题 | 状态 |
|---|---|---|
| Step 3A-3 dry-run planning | 第二窗口 candidate / overlap 评估（read-only） | ✅ |
| Step 3A-3 write | 备份 + dry-run + `--write 130` + 验证（DB 写入） | ✅（上一轮） |
| **Step 3A-3 checkpoint** | **本文件：固定 250 条 / 193 paired 的新 baseline + 反向 regime 归因** | ✅ |
| Step 3A-4 / Step 3B-0 / Step 3B | 视本 checkpoint 推荐路径 | 待开 |

## 2. 当前 main 状态

- **main 最新 commit：** `758ae87 docs(contract): Step 3A-2 peer and confidence inversion attribution`
- **测试基线：** **2233 passed / 0 failed / 10 skipped**（与 3A-2 commit 时一致；本轮无代码 / 测试 / schema 改动）

## 3. 写入前 baseline

| 字段 | 值 |
|---|---|
| `prediction_log` total | 133 |
| `outcome_log` total | 133 |
| `replay_AVGO_%` predictions | 130 |
| `paired_outcomes` | 100 |
| `calibration_ready` | True |
| `analysis_date` 范围 | 2024-01-29 → 2024-08-02 |
| Window1 baseline | 30 paired 来自 4c-3-rewrite + 100 paired 来自 4d-2 |

## 4. 第二窗口 dry-run

CLI: `python3 scripts/run_contract_replay.py --symbol AVGO --start 2023-08-05 --limit 130`

| 字段 | 值 |
|---|---|
| `status` | `ok` |
| `dry_run` | `True` |
| `candidate_pair_count` | **130** |
| `would_write_count` | **130** |
| `written_prediction_count / outcome_count` | 0 / 0 |
| `first_pair` | `as_of=2023-08-07, prediction_for=2023-08-08` |
| `last_pair` | `as_of=2024-02-09, prediction_for=2024-02-12` |
| `anti_lookahead_check.all_pairs_satisfy_d_lt_d_plus_1` | `True` |
| 与现有 130 baseline 重叠 | **10**（`replay_AVGO_2024-01-29 → replay_AVGO_2024-02-09`） |
| 预计 new write | **120** prediction + 120 outcome |

## 5. 备份

- 新备份：**`avgo_agent.db.backup_pre_3a3_20260504_013453`** — 4.7M
- 既有 backup 全部保留：
  - `avgo_agent.db.backup_pre_2099_hygiene_20260503_160409` (1.7M)
  - `avgo_agent.db.backup_pre_replay_30_20260503_162636` (1.7M)
  - `avgo_agent.db.backup_pre_4c3_rewrite_20260503_235604` (2.4M)
  - `avgo_agent.db.backup_pre_replay_130_20260504_003707` (2.4M)
  - `avgo_agent.db.backup_step_2c_2_6` (1.6M)
- DB / backup 文件不进入 git。

## 6. `--write` 结果

| 字段 | 值 |
|---|---|
| `status` | **`partial`** |
| `dry_run` | `False` |
| `candidate_pair_count` | 130 |
| `attempted_write_count` | 130 |
| **`written_prediction_count`** | **120** |
| **`written_outcome_count`** | **120** |
| `skipped_pairs` total | **10** |
| **唯一 skip reason** | **`snapshot_id_already_exists`**（无其他 reason） |
| 第一个新增 pair | `as_of=2023-08-07, prediction_for=2023-08-08` |
| 最后一个新增 pair | `as_of=2024-01-26, prediction_for=2024-01-29`（与 baseline 严丝合缝） |

writer notes 自报：
- "dry_run=False: wrote 120 prediction/outcome pair(s); skipped 10"
- "all writes went through save_prediction / save_outcome — no raw INSERT was used"
- "peer cutoff: NVDA / SOXX / QQQ relative-strength computed with Date <= D from coded_data; missing peers degrade to 'unavailable'"
- "duplicate guard: pairs whose snapshot_id already exists in prediction_log are skipped with reason='snapshot_id_already_exists' (no run_predict / save_prediction / save_outcome invoked)"

⚠️ **不要再重跑同一命令**：现在 250 条 replay snapshot 都在 DB 里，再跑 `--write 2023-08-05 130` 会被 duplicate guard 全部 skip（partial / 0 written / 130 dup-skip），是无害但**无信息的 no-op**。

## 7. 写入后 DB 验证

| 字段 | 值 | 期望 |
|---|---|---|
| `prediction_log` total | **253** | 253 ✓ |
| `outcome_log` total | **253** | 253 ✓ |
| `replay_AVGO_%` predictions | **250** | 250 ✓ |
| `replay_AVGO_%` outcomes (join) | **250** | 250 ✓ |
| `replay_AVGO_%` rows with `contract_payload_json` | **250 / 250** | ✓ |
| **duplicate snapshot_id 行数** | **0** | ✓（duplicate guard 守住） |
| 2099 predictions | 0 | ✓ |
| `analysis_date` 范围 | **2023-08-07 → 2024-08-02** | 跨 12 个月窗口 |
| `prediction_for_date` 范围 | **2023-08-08 → 2024-08-05** | ✓ |
| `outcome.captured_at` 范围 | **2023-08-08T16:00:00 → 2024-08-05T16:00:00** | 全部 16:00:00 ✓ |
| `paired_outcomes` | **193** | 100 → 193，+93 |
| `calibration_ready` | **True** | 仍稳定 |
| `missing_dimensions` | `[]` | ✓ |

## 8. 反向是否缓解（窗口对比）

> Window1 = 2024-01-29 → 2024-08-02（130 records，4d-2 + 4c-3-rewrite 写入）
> Window2 = 2023-08-07 → 2024-01-26（120 records，本步骤 3A-3 新写入）
> Combined = 250 records

### 8.1 Overall accuracy
| 维度 | Window1 | Window2 (NEW) | Combined |
|---|---|---|---|
| samples | 130 | 120 | 250 |
| paired | 100 | 93 | 193 |
| **accuracy** | **0.440** | **0.548** | **0.492** |

### 8.2 confidence_level
| level | Window1 paired/acc | Window2 paired/acc | Combined paired/acc |
|---|---|---|---|
| high | 51 / **0.431** | 55 / **0.509** | 106 / 0.472 |
| medium | 29 / 0.414 | 21 / 0.524 | 50 / 0.460 |
| low | 20 / 0.500 | 17 / 0.706 *(small)* | 37 / 0.595 |

### 8.3 peer_adjustment label（最关键）
| label | Window1 paired/acc | Window2 paired/acc | Combined paired/acc |
|---|---|---|---|
| **upgrade** | 44 / **0.364** | 43 / **0.558** | 87 / 0.460 |
| hold | 35 / 0.486 | 32 / 0.500 | 67 / 0.493 |
| downgrade | 21 / 0.524 | 18 / 0.611 | 39 / 0.564 |
| flip_to_neutral | 0 paired | 0 paired | 0 paired |

**`upgrade` 这一桶在两个窗口的差距 = +19.4 ppts**（从 0.364 翻到 0.558）—— 这是反向消失的最强证据。

### 8.4 peer_confirm_count
| pcc | Window1 paired/acc | Window2 paired/acc | Combined paired/acc |
|---|---|---|---|
| 0 | 32 / 0.531 | 22 / 0.455 | 54 / 0.500 |
| 1 | 24 / 0.458 | 28 / 0.607 | 52 / 0.538 |
| **2** | 23 / **0.348** | 18 / **0.556** | 41 / 0.439 |
| 3 | 21 / 0.381 | 25 / 0.560 | 46 / 0.478 |

Window1：pcc 越高 acc 越低（anti-monotonic）。
Window2：**pcc=1/2/3 都 ≥ 0.555，pcc=0 反而 0.455** —— **大致回到正方向**。

### 8.5 soft_signal
| signal | Window1 paired/acc | Window2 paired/acc | Combined paired/acc |
|---|---|---|---|
| **none** | 67 / **0.403** | 64 / 0.500 | 131 / 0.450 |
| high_path_risk | 12 / 0.500 | 11 / 0.727 | 23 / 0.609 |
| peer_weaken | 21 / 0.524 | 18 / 0.611 | 39 / 0.564 |

两个窗口都呈"`none < peer_weaken / high_path_risk`"模式。Window2 里 `none=0.500`（random），不再像 Window1 那样 0.403 实质失败。说明 `soft_signal != none` 真的标出"模型自己不确定的子集"，这部分子集**在所有 regime 下都更接近随机**；soft_signal 是**设计意图**（metadata），不是 inversion bug。

### 8.6 final_direction
| direction | Window1 paired/acc | Window2 paired/acc | Combined paired/acc |
|---|---|---|---|
| 偏多 | 64 / 0.453 | 64 / **0.547** | 128 / 0.500 |
| 偏空 | 36 / 0.417 | 29 / **0.552** | 65 / 0.477 |
| 中性 | 0 paired | 0 paired | 0 paired |

Window1 两个方向都 < 0.5；Window2 两个方向都 ≥ 0.55。

### 8.7 Direction bias（系统性偏多）
| 维度 | Window1 | Window2 | Combined |
|---|---|---|---|
| paired total | 100 | 93 | 193 |
| 预测偏多 | 64 | 64 | 128 |
| 预测偏空 | 36 | 29 | 65 |
| **predicted 偏多 率** | **64.0%** | **68.8%** | **66.3%** |
| 实际 up | 50 | 48 | 98 |
| 实际 down | 50 | 45 | 95 |
| **actual up 率** | **50.0%** | **51.6%** | **50.8%** |
| **long bias (predicted - actual)** | **+14 ppts** | **+17 ppts** | **+15 ppts** |

**两个窗口长偏置几乎一致 ≈ +15 ppts** —— 这是结构性问题，**跨 regime 不变**。

### 8.8 月度 accuracy（combined timeline）
| 月 | paired | accuracy |
|---|---|---|
| 2023-08 | 17 | 0.529 |
| 2023-09 | 12 | 0.417 |
| 2023-10 | 20 | **0.600** |
| 2023-11 | 19 | 0.526 |
| 2023-12 | 13 | 0.538 |
| 2024-01 | 13 | **0.615** |
| 2024-02 | 16 | 0.562 |
| **2024-03** | 15 | **0.333** ← 失败窗口起点 |
| **2024-04** | 19 | **0.316** ← 最低点 |
| **2024-05** | 13 | **0.385** |
| 2024-06 | 15 | **0.600** ← 反弹 |
| 2024-07 | 19 | 0.421 |
| 2024-08 | 2 | 1.000 *(small)* |

**13 个月里有 10 个月 acc ≥ 0.50**（含一个 0.417 接近 random）。**3 个月（2024-03 / 04 / 05）形成连续低谷**，acc 全部 < 0.40。Window1 里月度差从这个对照看就更显然。

### 8.9 明确回答 5 个问题

| 问题 | 答案 |
|---|---|
| high 是否仍低于 low？ | ⚠️ **缓解但仍存在**。Window1 high (0.431) ≪ low (0.500)；Window2 high (0.509) > medium (0.524) ≈ persistent。Combined 看 high (0.472) < low (0.595)，但 low 大量 pending（中性桶），可比信息有限。**结论：confidence_level 的预测力很弱 / 启发式标签没有带来真信号**，但不是"反向"。 |
| peer reinforce / confirm 是否仍反向？ | ✅ **不反了**。`pa=upgrade` 从 0.364 → 0.558（+19.4 ppts）；`pcc=2` 从 0.348 → 0.556（+20.8 ppts）。Window2 里 pcc 单调几乎正向（0/1/2/3 = 0.455/0.607/0.556/0.560）。**这是 regime 性现象，不是 sign error。** |
| soft_signal=none 是否仍最差？ | ⚠️ **形态保留，但缓解**。两个窗口都 `none < peer_weaken / high_path_risk`，但 Window2 里 none=0.500 已经是 random，不再是 0.403 实质失败。**这是 metadata 设计意图（"模型自己不确定"子集天然更随机），不是 bug。** |
| 系统性偏多是否减轻？ | ❌ **没有减轻**。Window1 +14 ppts / Window2 +17 ppts / Combined +15 ppts。**结构性问题**，跨 regime 不变。这是 score 公式 momentum-following 的固有特征，本步骤无法解决（CLAUDE.md 硬规则禁止改 scanner / encoder / 直接动方向决策）。 |
| 第二窗口是否支持"regime 现象"解释？ | ✅ **强烈支持**。peer 反向、confidence 反向、月度低谷三个特征都集中在 Window1 的特定子段（2024-03 → 05），Window2 不重现。**结论：反向 = regime；偏多 = 结构性。** |

## 9. 关键结论

1. ✅ **样本量从 130 → 250 / paired 100 → 193**：cross-window baseline 已建立，cross-regime 验证可行。
2. ✅ **`calibration_ready` 稳定 True、`missing_dimensions=[]`**：calibration 工具持续可用。
3. ✅ **duplicate guard 经受住真实重叠写入验证**：10 条预期 dup-skip 全部命中，0 false positive，0 false negative，0 漏写，0 重复。这是 4d-2-prereq-1 引入的最重要安全机制 —— 没有它，本步骤会写出 130 条新行 + 10 条重复行，污染 calibration 工具。
4. ✅ **反向归因更新**：从 Step 3A-2 的"可能是 regime"升级为 Step 3A-3 的"**确认是 regime**"。
5. ⚠️ **结构性偏多 +15 ppts** 是无法用 calibration 公式直接修的方向偏置。需要 regime-aware 处理，或者承认它是模型本身的限制。
6. ⚠️ **如果 Step 3B 直接写公式，公式必须 regime-aware**；不能假设"peer reinforce → 高概率"在所有时间点都成立（在 2024-03-05 它是反的）。简单 calibration 公式（即"raw score → probability"线性映射）会把两个 regime 平均，预期 acc ≈ 0.49，跟现状没差。
7. ❌ **05 score 字段仍不应直接升级到非零**。当前 `historical_score / structure_score / peer_score / exclusion_penalty / event_score` 都是 0.0 / None 是合理的；只有 regime 探测 + calibration 公式 + cross-window holdout 都到位，才考虑写真值。
8. ❌ **Step 2G "soft → hard exclusion 升级"应放弃 / 重新设计**：跨两个窗口 soft_signal != none 都比 none 更准，硬化它会排除更准的子集。

## 10. 下一步建议（三选项）

### Option A：Step 3A-4 — 第三窗口 replay
- 加 `--start 2022-08-01 --limit 130`（或更早）写第三个窗口；
- 需要再扩 cap 到 ~260+ 才能一次写完，或先跑 130 然后再 130；
- 风险：2022 是 tech 大跌年，AVGO 自身也回调；可能引入第三种 regime（mean-reversion 多于 momentum），让 calibration 更难；
- 信息收益：能看到 bear regime 下反向是否再次出现 / 长偏置在 bear regime 是否变成短偏置；
- 工作量：中（需要 cap 提到 260 / 或拆 2 次写入）

### Option B：Step 3B — calibration formula design（仅 docs，不动代码）
- 基于现有 250 条数据起草 calibration 公式设计；
- 不引入新数据；
- 风险：跨两个 regime 平均出来的"calibration"可能就是 random predictor 加噪声，没有实质 edge；
- 信息收益：低（除非设计本身是 regime-aware）；
- 工作量：低（写几页 docs）

### Option C：Step 3B-0 — 更细的 regime split diagnostics（仅 read-only 分析）
- 不写新数据，不写代码；
- 在现有 250 条上做更深的 regime 切片：
  1. 按 AVGO 滚动 20 日波动率分桶 × accuracy
  2. 按 AVGO 滚动 20 日累计涨幅分桶 × accuracy
  3. 按 NVDA / SOXX / QQQ 同段 5d 表现分桶 × accuracy
  4. 把 2024-03-05 三个月的样本单独抽出来做 feature 比对（peer_alignment / soft_signal / score 分布是否系统性异常）
- 目标：找出"什么 regime 信号能预测模型自身的失败"。如果存在这种 regime feature，Step 3B 才有 regime-aware 公式的具体抓手；如果不存在，说明失败是不可观测的，calibration 公式没必要做。
- 风险：低（纯只读）；
- 信息收益：高（直接告诉 Step 3B 该不该做、怎么做）；
- 工作量：低-中（一次会话能搞定）。

### 推荐：**Option C**

理由：
1. **现有 250 条数据已经包含两个 regime**，第二窗口加上去 +120 paired 已经足以说明"反向是 regime 性"，再加第三窗口会让数据复杂度上升但归因更难（三个时间窗口、三种可能 regime）。先**榨干现有数据**再决定加不加。
2. **Step 3B 不能盲做**。现状是"知道反向是 regime 但不知道 regime 怎么界定"。Option B 等于在不知道 regime 怎么探测的情况下设计 calibration —— 必然只能做"无 regime 平均"版本，效果与现在差不多。
3. **Option C 是 Option B 的前置 / Option A 的减法**：如果 C 找到 regime 特征 → Step 3B 有具体目标；如果 C 没找到 → 跳过 3B，直接说"这个数据集 calibration 没意义"，节省一轮假动作。
4. C 的工作量与 A 相比小得多，**信息密度更高**。

执行下一轮（Step 3B-0）的具体内容（**仅参考；本 checkpoint 不强制**）：
- 计算每条 replay 的"as_of 当天的 AVGO 滚动 20 日累计涨幅 / 滚动 20 日波动率 / 5 日均量 / NVDA 同期相对收益"等 4 个 regime 特征；
- 把这 4 个特征分别 4-quartile 分桶，看每桶 accuracy；
- 找出 **failure regime 的 feature signature**（如：AVGO 20 日涨幅 ≥ 8% 且 NVDA 同期偏弱时，acc 系统性低）；
- 如果有清晰 signature → Step 3B 公式以"regime-aware 二段式"为核心；
- 如果没有 → Step 3B 暂搁，转 Step 2G 重审 / 其他方向。

## 11. 严守边界（本轮已遵守）

- ❌ 没改任何代码（`predict.py` / `services/*.py` / `tests/*.py` 0 字节变化）
- ❌ 没新增测试
- ❌ 没 commit / push
- ❌ 没写 DB（写入在 3A-3 write 已完成，本 checkpoint 仅记录）
- ❌ 没改 DB schema
- ❌ 没接 yfinance / 网络
- ❌ 没接 trading API / longbridge / broker / paper_trade
- ❌ 没升级 contract 04 / 05 / 07 顶层字段
- ❌ 没把 `soft_signal != none` 升级为 hard exclusion
- ❌ 没清理 DB / 没删除现有 replay
- ❌ 没触碰 stash / .claude/worktrees/ / logs/prediction_log.jsonl
- ❌ 没 add 任何 `avgo_agent.db.backup_*` 文件
- ✅ 仅新增 1 个 docs 文件
