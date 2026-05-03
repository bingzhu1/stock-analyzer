# Step 3A-2 — Peer & Confidence Inversion Attribution Checkpoint

> 状态：Step 3A 发现的"confidence / peer / soft_signal 三个反向"经过 Step 3A-2 的只读阅码 + 数据切片归因，**确认不是 sign error / 不是 writer↔predict 语义错配 / 不是测试覆盖空白**。最可能根因：底层 `primary_score_raw` 是 momentum-following 启发式，在 AVGO 2024-Feb-Aug 这段 mean-reversion regime 里方向性失效；peer signal 在这种 regime 下被 momentum-trap 同步带偏；soft_signal 设计上只是 metadata flag，不应升级为 hard exclusion。
> **直接进 Step 3B formula design 不合适**；建议先做 Step 3A-3 用第二个时间窗口扩样本验证。
> 本文件只写文档，不改代码，不写 DB，不 commit，不 push。

## 1. 当前完成状态

| 子步 | 主题 | 状态 |
|---|---|---|
| Step 3A | confidence calibration diagnostics（只读 130 条） | ✅ commit `b1dcfcd` |
| **Step 3A-2** | **peer & confidence 反向归因（只读阅码 + 数据切片）** | ✅（本文件 checkpoint） |
| Step 3A-3 | 换时间窗口扩样本验证（只读，新写 130 pair） | 待开 |
| Step 3B | calibration formula design | **暂缓**（待 3A-3 结论） |
| Step 3C | 写入 05 score 字段 | 暂缓 |

## 2. 当前数据和测试基线

| 字段 | 值 |
|---|---|
| `valid_payloads` | 130 |
| `paired_outcomes` | 100 |
| `calibration_ready` | True |
| 全量测试 | **2233 passed / 0 failed / 10 skipped / 65 subtests** |
| targeted（peer + confidence + exclusion + replay writer） | **164 passed / 17 subtests** |

本轮 0 代码改动 / 0 测试改动 / 0 DB 写入。

## 3. `peer_adjustment` 阅码结论

[predict.py:621-767](../predict.py)

### 3.1 `_peer_layer_vote` 真值表

| `primary_bias` | `relative_strength` | vote |
|---|---|---|
| bullish | **stronger** | **confirm** |
| bullish | weaker | oppose |
| bearish | **weaker** | **confirm** |
| bearish | stronger | oppose |
| any | neutral / unavailable | mixed / unavailable |

`_combine_peer_votes`：合并 5d + same_day 两层，confirm 与 oppose 共存 → mixed；任一是 unavailable 不影响另一层判定。

### 3.2 主流程

- `confirm_count >= 2` → `adjustment_direction = "reinforce"` → `_raise_confidence(primary_confidence)` + `_adjust_path_risk` → `risk_direction = "lower"`
- `oppose_count >= 2` → `adjustment_direction = "weaken"` → `_lower_confidence(primary_confidence)` + `risk_direction = "higher"`；如果 `primary_confidence == "low"` → `adjusted_bias = "neutral"`
- 其他 → `adjustment_direction = "neutral"`，无调整
- `confirm_count` / `oppose_count` 是相对于 **primary_bias** 计数（不是 final_bias）

### 3.3 contract 03 字段映射

- `_peer_signal_from_vote`: confirm → reinforce / oppose → weaken / mixed → neutral / unavailable → unknown
- `_peer_alignment_from_counts`: confirm≥3 & oppose=0 → all_reinforce / oppose≥3 & confirm=0 → all_weaken / 都=0 → insufficient / 其他 → mixed
- `_peer_adjustment_label`: reinforce → upgrade / weaken → downgrade / neutral_primary → flip_to_neutral / neutral → hold

✅ **没有 sign error。** 语义自洽：peer 与 primary_bias 同向 → confirm；逆向 → oppose。

## 4. writer / scanner / predict 语义一致

| 模块 | 函数 / 行号 | 计算 |
|---|---|---|
| [scanner.py:118](../scanner.py) `_classify_rs` | `diff = avgo_ret - peer_ret`；> +0.5pp → "stronger"；< -0.5pp → "weaker"；else "neutral" | margin = `_RS_MARGIN * 100 = 0.5pp` |
| [services/contract_replay_writer.py:219](../services/contract_replay_writer.py) `_classify_relative_strength` | 同上 | `_RS_MARGIN_PP = 0.5` |

- "stronger" = **AVGO 比 peer 更强**（diff = AVGO - peer > 0.5pp）
- "weaker" = **AVGO 比 peer 更弱**
- 5d return（`_get_nday_return` / `_compute_nday_return_at`）单位都是百分点
- same_day C_move（`_get_same_day_move` / `_compute_same_day_move_at`）单位都是百分点
- predict.py 在 `apply_peer_adjustment` 里按同一语义消费 `vs_nvda` / `vs_soxx` / `vs_qqq`

✅ **没有 writer → predict 语义错配。**

## 5. confidence 派生结论

[predict.py:507-611](../predict.py)

```
score = volume_state(±0.5) + trend_state(±1.0)
      + close_return(±0.5) + day_count_majority(±0.25)
↓ _bias_from_score
bullish (score > 0.5) | bearish (score < -0.5) | neutral
↓ _confidence_from_score
high (|score| ≥ 2) | medium (|score| ≥ 1) | low
↓ apply_peer_adjustment（peer 可 ±1 档调整）
adjusted_confidence
↓ adapter (services/projection_output_adapter.py)
contract.confidence_system.confidence_level
```

[services/projection_output_adapter.py:437-441](../services/projection_output_adapter.py) 显式硬编码：
```python
"historical_score": 0.0,
"structure_score": 0.0,
"peer_score": 0.0,
"exclusion_penalty": 0.0,
"event_score": None,
```

✅ **05 required score 字段仍是 0.0 / `event_score=None` 是 by design**（Step 2C-3b 把它们留作 stub 待 Step 3C）。
✅ **当前 `confidence_level` 是启发式标签**（`abs(primary_score_raw)` 阈值），**不是 calibrated score**。
✅ replay 路径里 `peer_adjusted_confidence == final_confidence == contract.confidence_level`（130 条记录 0 mismatch）。

## 6. soft_signal 结论

[services/projection_output_adapter.py:335-343](../services/projection_output_adapter.py)

优先级：
1. `conflicting_factors` 含 `"peer_confirmation=weaken"`（即 `peer.adjustment_direction == "weaken"`）→ `peer_weaken`
2. else `path_risk_level == "high"` → `high_path_risk`
3. else → `none`

`peer_confirmation=weaken` 的来源是 [predict.py:898-902](../predict.py)：当 peer `oppose_count >= 2` 时被加进 `conflicting_factors`。

✅ **soft_signal 设计本意是 metadata flag**，不是 hard exclusion 触发器；adapter docstring 明确"never feeds back into the contract-required fields"。
✅ **当前数据下 `soft_signal != none` 反而更准**（peer_weaken 0.524 / high_path_risk 0.500 vs none 0.403）—— 所以 Step 2G "soft → hard exclusion 升级"应**暂缓 / 重新设计**，按现状直接硬化会排除掉**比 baseline 更准**的子集。

## 7. 数据切片核心发现

### 7.1 peer_adjustment label × accuracy（最关键）
| label | n | paired | accuracy |
|---|---|---|---|
| **upgrade**（peers reinforce primary） | 46 | 44 | **0.364** ← 最差 |
| hold | 36 | 35 | 0.486 |
| **downgrade**（peers oppose primary） | 26 | 21 | **0.524** ← 最好 |
| flip_to_neutral | 22 | 0 | n/a（全 pending） |

### 7.2 单 peer signal × accuracy
| peer | reinforce paired/acc | weaken paired/acc | neutral paired/acc |
|---|---|---|---|
| NVDA | 33 / **0.394** | 42 / 0.452 | 25 / 0.480 |
| **SOXX** | 46 / **0.370** | 22 / 0.409 | 32 / **0.562** |
| QQQ | 54 / **0.389** | 20 / 0.500 | 26 / 0.500 |

三个 peer 的 reinforce 桶都是 acc 最低；**SOXX 反向最强**（reinforce 0.370 vs neutral 0.562，差 19 ppts）。SOXX 是半导体行业 ETF，与 AVGO 高度耦合。

### 7.3 peer_confirm_count × accuracy
| pcc | paired | accuracy |
|---|---|---|
| 0 | 32 | **0.531** |
| 1 | 24 | 0.458 |
| **2** | 23 | **0.348** |
| 3 | 21 | 0.381 |

### 7.4 confidence 链路一致性（130 条）
- `primary_confidence_raw` → `peer_adjusted_confidence` 变化 **38 次**：
  - medium → low 14
  - medium → high 10
  - high → medium 8
  - low → medium 6
  - net 效果 = **-4**（peer 净倾向降 confidence，**不是** confidence 偏高的来源）
- `peer_adjusted_confidence == final_confidence`：**0** mismatch（research adjustment 在 replay 路径不触发）
- `final_confidence == contract.confidence_level`：**0** mismatch（adapter 只 normalize）

### 7.5 regime
- 2024-04 high confidence wrong rate **78%**（7 wrong / 2 correct）
- 2024-05 high confidence wrong rate **71%**（5 wrong / 2 correct）
- 2024-06 反向：high confidence wrong rate **29%**（2 wrong / 5 correct）
- `peer_path_risk_direction = lower` 集中在 4 月（9）+ 7 月（12）= 21 / 44 = **48%**

## 8. 根因判断

### 8.1 peer 反向
✅ **regime 现象 + `final_direction` 系统性偏多 bias 的叠加**。

不是：
- ❌ sign error（4 个 quadrant 都有测试覆盖：`test_all_peers_stronger_under_bullish_primary_yields_all_reinforce` / `test_all_peers_weaker_under_bullish_primary_yields_all_weaken` / `test_adjusted_direction_mirrors_adjusted_bias`（bearish + stronger）/ `test_bearish_peers_reinforce_bearish_primary`（bearish + weaker））
- ❌ writer / predict 语义错配（margin / 单位 / `_classify_rs` 都同口径）
- ❌ 测试 gap
- ❌ 样本量问题（46 paired 的 upgrade 桶 acc 0.364 是稳定信号）

是：
- ✅ AVGO 2024-Feb-Aug 期间，"AVGO 跑赢 peer"（peer reinforce）大概率发生在 AVGO 短期超买时段 → 次日 mean reversion → 与 momentum-following 预测相反
- ✅ SOXX（半导体 ETF）反向最强 —— 与 AVGO 同行业耦合最深，这种"AVGO 跑赢 SOXX"信号噪声最大
- ✅ pcc=2 的预测偏多率（65%）vs 实际涨率（43%），22 ppts 反差是 regime 特征，不是 peer 计算错

### 8.2 confidence 反向
✅ **`primary_score_raw` 的 momentum-following bias 在 mean-reversion regime 里失效**。

不是：
- ❌ 分桶逻辑错（`_confidence_from_score` 用 `abs(score)`，对称）
- ❌ peer 把 confidence 调坏（peer 净效果 -4，向 conservative 倾）
- ❌ adapter 重算（`fc → cl` 0 mismatch）

是：
- ✅ score 公式（`volume_state` / `trend_state` / `close_return` / `up_days`）全是 momentum-following 加项，没有 mean reversion 项
- ✅ AVGO 2024-Feb-Aug 趋势上行 → 多个 momentum 信号同时 fire → score > 2 → high confidence → 但下一日反弹/回调 → wrong
- ✅ 4-5 月 high wrong rate 71-78% 与 score 公式假设的"momentum 持续"完全相反

### 8.3 soft_signal 反向
✅ **soft_signal 是 metadata flag，不是 warning；它正确地标出了"模型自己不太确定的 case"**。

不是：
- ❌ 触发条件错
- ❌ 命名错
- ❌ 实现错

是：
- ✅ `soft_signal=none`（70 条）= 模型"很有把握"且 path_risk 不是 high → 在这个 regime 是过度自信偏多陷阱
- ✅ `soft_signal=peer_weaken`（26 条）/ `high_path_risk`（34 条）= 模型已自下调 confidence → 这些 case 反而更接近 random 0.5

## 9. 是否进入 Step 3B

❌ **不建议直接进 Step 3B formula design。** 原因：

1. **calibration 公式不能修方向性错误**。calibration 是把 raw score 映射成概率；如果 raw signals 方向就反了，公式只能让"高概率预测"= 53% 改成"低概率预测"= 47%，**不能把 0.36 acc 翻成 0.6 acc**。
2. **底层 score 公式属于 CLAUDE.md 硬规则层**：
   > Hard rule 1: "不要让 LLM 决定股票方向"
   > Hard rule 2: "scanner / matcher / encoder 属于硬规则层，优先保留"

   →本项目明确禁止改 scanner / encoder；score 公式在 predict.py 里是核心方向决定逻辑，本步骤无权动它。
3. **本数据集是单 symbol 单时间窗口**（AVGO 2024-Feb-Aug, 100 paired）—— 直接设计 formula 会**对单一 regime overfit**。验证之前不能上 formula。
4. Step 3A-3 不需要改任何公式或代码，只需要扩样本，**风险最低**且**信息收益最高**。

## 10. 下一步建议

### Step 3A-3：换时间窗口扩样本验证（只读 + 新 replay 写入，不改公式）

**目标**：观察 7.1 / 7.2 / 7.5 的反向特征是否在第二个时间窗口也出现。

**前置（已就位）**：
- duplicate guard ✅（commit `19800ac`）
- hard cap = 130 ✅（commit `7d685a6`）
- CLI help 跟随 cap ✅（commit `f26387b`）
- coded_data 历史从 2016 起（4d-1 dry-run 验过 `--start 2023-10-01 --limit 120` 跑得通）

**推荐执行参数**：
```
--symbol AVGO
--start 2023-08-05
--limit 130
--write
```
（与现有 130 条 baseline `--start 2024-01-29` 不重叠；2023-08-05 起可写出约 2023-08-04 → 2024-01-26 的窗口，duplicate guard 自动跳过任何已存在 snapshot_id。预期写入约 100-130 新 prediction。）

**强制流程**：
1. 备份：`cp avgo_agent.db avgo_agent.db.backup_pre_3a3_<ts>`
2. dry-run：`python3 scripts/run_contract_replay.py --symbol AVGO --start 2023-08-05 --limit 130`
3. 真写：上一条加 `--write`
4. 重跑诊断（同 Step 3A 的 inline `python3 << PY` 脚本，按月分窗口）
5. **不要合并两个窗口的样本做总平均**；分别分析。

**判据**：
- 如果第二窗口也出现：upgrade < downgrade、SOXX reinforce 最低、月度有失败窗口、predicted 偏多率显著 > 50% → **结构性问题**，Step 3B 仍然不能启动，需要改公式（但这超出 Step 3 范围）；
- 如果第二窗口**没有**这些反向：→ **AVGO 2024-Feb-Aug 是 regime 特殊**，可以谨慎进 Step 3B，但 formula 必须做 cross-window holdout 验证；
- 如果第二窗口反向方向不同（比如 confidence 反而正向）：→ **regime-dependent**，formula 必须显式建模 regime（这超出当前范围）。

### Step 3B / Step 3C / Step 2G

- **Step 3B**：暂缓，等 3A-3。
- **Step 3C**：暂缓，最末位。
- **Step 2G `soft → hard exclusion` 升级**：建议**取消或重新设计**。当前数据下 `soft_signal != none` 反而更准，硬化它会排除掉比 baseline 更准的子集。**这不是 3A-3 能直接验证的**；应作为独立路径在 3A-3 后另起 review。

## 11. 严守边界（本轮已遵守）

- ❌ 没改任何代码（`predict.py` / `scanner.py` / `services/*.py` / `tests/*.py` 0 字节变化）
- ❌ 没新增测试
- ❌ 没 commit / push
- ❌ 没写 DB
- ❌ 没改 DB schema
- ❌ 没改 [predict.py](../predict.py) / [scanner.py](../scanner.py) / [services/peer_adjustment.py](../services/peer_adjustment.py) / [services/projection_output_adapter.py](../services/projection_output_adapter.py) / [services/contract_replay_writer.py](../services/contract_replay_writer.py)
- ❌ 没升级 contract 04（exclusion required）/ 05（confidence score）/ 07（simulated_trade required）顶层字段
- ❌ 没升级 `soft_signal != none` 为 hard exclusion
- ❌ 没接 yfinance / 网络
- ❌ 没接 trading API / longbridge / broker / paper_trade
- ❌ 没生成新脚本进仓库（所有诊断 inline `python3 << PY`，无 csv / 中间文件）
- ❌ 没触碰 stash / .claude/worktrees/ / logs/prediction_log.jsonl
- ✅ 仅 read + grep + sqlite SELECT + json 解析 + pytest + 现有工具 + 新 docs 1 份
