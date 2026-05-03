# Step 3A — Confidence Calibration Diagnostics Checkpoint

> 状态：Step 2F 已经把 `calibration_ready` 推到 `True`、`paired_outcomes=100`，本步骤是第一次真正用这 130 条 replay 做置信 / peer / soft_signal 的预测力诊断。结论：**`calibration_ready=true` 只代表数据量够，不代表可以直接动 confidence 公式 / 写 score 字段**；当前数据揭示 confidence、peer、soft_signal 三个信号都呈"方向反了"特征，必须先做 Step 3A-2 阅码归因，才决定 3B 是否启动。
> 本文件只写文档，不改代码，不写 DB，不 commit，不 push。

## 1. 当前完成状态

| 子步 | 主题 | 状态 |
|---|---|---|
| Step 2F-4d-2 | 130-pair replay → `calibration_ready=true` | ✅ commit `603128f` |
| **Step 3A** | **confidence calibration diagnostics（只读分析 130 条）** | ✅（本文件 checkpoint） |
| Step 3A-2 | peer & confidence 反向归因（只读阅码） | 待开 |
| Step 3A-3 | 如果定位到 sign error，小修 + 重跑 | 视 3A-2 结论 |
| Step 3B | calibration formula 设计 | 暂缓，待 3A-2 / 3A-3 |
| Step 3C | 写入 05 score 字段 | 暂缓，最末位 |

## 2. 当前数据基线

| 字段 | 值 |
|---|---|
| `valid_payloads` | 130 |
| `paired_outcomes` | 100 |
| `pending_outcomes` | 30 |
| `calibration_ready` | True |
| `missing_dimensions` | `[]` |
| `analysis_date` 范围 | 2024-01-29 → 2024-08-02 |
| `prediction_for_date` 范围 | 2024-01-30 → 2024-08-05 |

> 数据来源：Step 2F-4c-3-rewrite 的 30 条 + Step 2F-4d-2 真写入的 100 条 = 130 条 peer-aware replay，duplicate guard 守住无重复。

## 3. Overall accuracy

| 字段 | 值 |
|---|---|
| total samples | 130 |
| paired (correct + wrong) | **100** |
| correct | **44** |
| wrong | **56** |
| pending（30 条 flat / 中性） | 30 |
| **overall accuracy** | **0.440** |

**0.440 < 0.500（随机）**。100 条样本下，单次 binomial 0.500 ± 0.05 的 95% CI 约为 [0.40, 0.60]，所以 0.440 不是统计上"显著低于随机"，但**离 random 太近**，远低于"模型有 edge"应有的水平。

## 4. confidence_level 诊断

| level | samples | paired | correct | wrong | pending | **accuracy** |
|---|---|---|---|---|---|---|
| **high** | 53 | 51 | 22 | 29 | 2 | **0.431** |
| medium | 30 | 29 | 12 | 17 | 1 | 0.414 |
| **low** | 47 | 20 | 10 | 10 | 27 | **0.500** |

**结论：**
- `confidence_level` **没有正向预测力**；high / medium / low 三档 accuracy 几乎在 0.41–0.50 区间内噪声重合。
- **high 没有明显优于 low**，反而 low (0.500) 略高于 high (0.431) —— 与"高置信应该更准"的直觉相反。
- low 的 27 pending（中性 → 平盘 → 不计入 paired）说明 low 大部分都是"无方向"判定；20 paired 样本量较小，accuracy 0.500 解读应保守。
- **不能直接用 `confidence_level` 当 calibration score 的输入维度。** 当前不存在"high → 高 score / low → 低 score"的简单线性映射依据。

## 5. primary_score_raw 诊断

| bucket | samples | paired | accuracy | avg_psr |
|---|---|---|---|---|
| ≤ -2 | 22 | 21 | 0.476 | -2.83 |
| (-2, -1] | 11 | 10 | 0.300 | -1.61 |
| (-1, 0] | 21 | 5 | 0.400 | -0.38 |
| (0, 1] | 20 | 10 | 0.500 | +0.60 |
| **(1, 2]** | 29 | 27 | **0.370** | +1.61 |
| > 2 | 27 | 27 | 0.519 | +3.13 |

补充：
- `|psr| ≥ 2` 整体（50 paired）= **0.480**
- `|psr| < 1` 整体（13 paired）= 0.462

**结论：**
- **`primary_score_raw` 非单调**。极端正端 (>2: 0.519) 与极端负端 (≤-2: 0.476) 略好，但中间桶 (-2,-1]=0.300 / (1,2]=0.370 erratic。
- "极端信念 vs 弱信念"差距只有 ~2 ppts（0.480 vs 0.462）—— **score 强度本身几乎不带信息量**。
- **不能直接把 `primary_score_raw` 当线性 calibration 输入**（即"score 越大命中率越高"的假设在这 130 条上不成立）。

## 6. peer 信号诊断

### 6.1 peer_confirm_count（confidence_system.extras）
| pcc | samples | paired | accuracy |
|---|---|---|---|
| 0 | 60 | 32 | **0.531** |
| 1 | 24 | 24 | 0.458 |
| **2** | 25 | 23 | **0.348** |
| 3 | 21 | 21 | 0.381 |

### 6.2 peer_oppose_count
| poc | samples | paired | accuracy |
|---|---|---|---|
| 0 | 71 | 47 | 0.426 |
| 1 | 33 | 32 | 0.406 |
| **2** | 12 | 11 | **0.727** |
| 3 | 14 | 10 | 0.300 |

### 6.3 net peer signal
| 状态 | paired | accuracy |
|---|---|---|
| confirm > oppose | 53 | **0.377** |
| confirm = oppose | 18 | 0.556 |
| confirm < oppose | 29 | 0.483 |

### 6.4 peer_path_risk_direction（exclusion_system.extras）
| direction | paired | accuracy |
|---|---|---|
| higher | 32 | 0.500 |
| unchanged | 24 | 0.500 |
| **lower** | 44 | **0.364** |

### 6.5 high-confidence 子集内 peer 对比
high paired 51 条：correct 22 / wrong 29
- avg `peer_confirm_count`：correct **+1.909** / wrong **+2.138** ← **wrong 的 peer 确认更多**
- avg `peer_oppose_count`：correct +0.318 / wrong +0.414

**结论：**
- **peer 信号方向疑似反了**：
  1. `peer_confirm_count` 越高 → accuracy 越低（0 → 0.531；2/3 → 0.348/0.381）
  2. `confirm > oppose`（理论上"peers 同意"应该更准）→ 0.377（最差）；`confirm < oppose` → 0.483（反而更高）
  3. `peer_path_risk_direction = lower`（理论上"peer 路径风险下降"应该更安全）→ 0.364（最差）
  4. high-confidence 内部，wrong 的 avg pcc (2.138) > correct 的 (1.909)
- 这种系统性反向有三种可能（**Step 3A-2 阅码才能定位**）：
  - (i) **regime 现象**：AVGO + 它的 peer (NVDA/SOXX/QQQ) 在 2024-02..2024-07 真实就是反向走的；
  - (ii) **sign error**：`predict.apply_peer_adjustment` 或 `confidence_engine` 把 peer agreement 减号当加号；
  - (iii) **语义错配**：`peer_confirm_count` 实际数的是"和 raw score 同号" / "和 final_direction 一致" / 别的，跟字面"peer 确认预测方向"不是同一件事。
- **不能直接把 peer confirm count 当加分项**；3A-2 之前不能假设 peer 是正向信号。

## 7. soft_signal / path_risk 诊断

### 7.1 soft_signal（exclusion_system.extras）
| signal | paired | accuracy |
|---|---|---|
| **none** | 67 | **0.403** |
| high_path_risk | 12 | 0.500 |
| peer_weaken | 21 | 0.524 |

### 7.2 path_risk_level（exclusion_system.extras）
| level | paired | accuracy |
|---|---|---|
| low | 45 | 0.422 |
| medium | 30 | 0.433 |
| high | 25 | 0.480 |

**结论：**
- **`soft_signal` 当前不像 warning**：none (0.403) 最差，触发 `peer_weaken` (0.524) / `high_path_risk` (0.500) 反而更准 —— 这跟"软警告应该提示风险（更可能错）"完全相反。
- **如果把 `soft_signal != none` 直接硬化为 exclusion，会排除更准的子集** —— 这等于反向操作。Step 2G exclusion soft → hard 升级的前置假设需要重新评估。
- `path_risk_level` 三档差距 < 6 ppts，但方向也反（low 最差、high 最好）；high 那档有 27 pending，与 `soft_signal=high_path_risk` 大量重叠。

## 8. final_direction / final_five_state 诊断

### 8.1 final_direction
| direction | samples | paired | accuracy |
|---|---|---|---|
| 偏多 | 66 | 64 | 0.453 |
| 偏空 | 38 | 36 | 0.417 |
| 中性 | 26 | 0 | n/a（全 pending） |

### 8.2 final_five_state
| state | samples | paired | accuracy |
|---|---|---|---|
| 小涨 | 35 | 34 | 0.500 |
| 震荡 | 68 | 41 | 0.439 |
| **小跌** | 27 | 25 | **0.360** |

**结论：**
- 偏多 (0.453) / 偏空 (0.417) 两个方向都 < 0.5；偏空略差。
- **小跌 0.360（25 paired）是最弱细分桶**，需后续单独研究：是不是 AVGO 跌时跌穿小跌边界（→ 实际是大跌），还是预测时机系统性错。
- 中性 26 条全 pending（中性 → 平盘 outcome → `direction_correct` 为 None），与 30 pending 之中的 26 条重合；剩 4 个 pending 来自方向 ≠ 中性但 outcome 平盘。

## 9. 补充诊断（direction bias + monthly）

### 9.1 direction bias
- **预测偏多率**：64 / 100 paired = **64%**
- **实际 up 率**（D+1 close 相对 D close）：50 / 100 paired = **50%**（恰好对半）
- → **预测器系统性偏多 14 个百分点**

按 binomial 估算，单是 14 ppts 的方向偏置就能把"基线 0.5 命中"拉到 ~0.43-0.44；与实测 overall 0.440 高度一致。换句话说：**当前 0.440 的 accuracy 主要由方向偏置（不是 confidence/peer 信号本身）解释**。

### 9.2 monthly accuracy
| 月份 | samples | paired | accuracy |
|---|---|---|---|
| 2024-01 | 3 | 1 | 0.000（样本太少） |
| 2024-02 | 20 | 16 | **0.562** |
| **2024-03** | 20 | 15 | **0.333** |
| **2024-04** | 22 | 19 | **0.316** |
| 2024-05 | 22 | 13 | 0.385 |
| **2024-06** | 19 | 15 | **0.600** |
| 2024-07 | 22 | 19 | 0.421 |
| 2024-08 | 2 | 2 | 1.000（样本太少） |

**3-5 月是模型明显失败窗口**（accuracy 0.316-0.385）；2 月与 6 月相对 OK（0.562 / 0.600）。结合 §9.1 的方向偏置，这段时间 AVGO 出现回调 / 区间震荡 → 偏多预测被惩罚得更严重。

## 10. 关键结论

1. ✅ **`calibration_ready=true` 不等于可以写 calibration formula**。这个标志只代表 paired 数量够（≥ 90），不代表 confidence / peer / soft_signal 这些 calibration 输入维度本身有效。
2. ❌ **`confidence_level` 当前没有预测力**：high (0.431) / medium (0.414) / low (0.500) 三档 accuracy 几乎重合，方向甚至略反。
3. ❌ **peer 信号当前方向反了**：pcc 越高、confirm > oppose、peer_path_risk = lower 都对应**更低** accuracy，与字面语义相反。
4. ❌ **`soft_signal` 当前不像 warning**：触发 peer_weaken / high_path_risk 的子集反而更准。
5. ⚠️ **predictor 系统性偏多 14 ppts**：这是 0.440 整体 accuracy 的主要驱动因素，**单靠 calibration 公式无法修**（需要 `predict.py` / `scanner.py` 层介入，但本项目硬规则禁止 LLM 改硬规则层）。
6. 🚦 **Step 3B formula design 暂缓**。在确认 §6 / §7 是 regime 现象 vs sign error vs 语义错配之前，任何 calibration 公式都可能"把反向信号正向放大"。
7. 🚦 **必须先做 Step 3A-2 peer & confidence 反向归因**（read-only 阅码），把这 4 个反向问题归类清楚。

## 11. 下一步建议

### Step 3A-2：peer & confidence 反向归因（只读阅码，无代码改动）
**任务清单：**
1. 读 [services/predict.py](../services/predict.py) `apply_peer_adjustment`：
   - `peer_confirm_count` / `peer_oppose_count` 在源代码层面**到底统计的是什么**？
     - 是"peer 同向 final_direction"？
     - "peer 同号 raw score"？
     - "peer 自身呈 stronger"？
     - 别的？
   - 把语义写到 3A-2 checkpoint 里。
2. 读 [services/confidence_engine.py](../services/confidence_engine.py)（如存在；或 `predict.py` 里的 confidence 段）：
   - `primary_score_raw` → `primary_confidence_raw` 的阈值
   - `peer_adjusted_confidence` 怎么从 `primary_confidence_raw` + peer 信号合成
   - `final_confidence` 是否还有别的修饰
   - 找出可能的 sign 错误位（peer 加分 / 减分的代数符号、是否漏取负号）
3. 读 `peer_path_risk_direction` / `soft_signal` 的生成逻辑（应该在 `exclusion` 链路）：
   - 这两个字段触发条件
   - 它们是否被反向 mapping 到 contract extras
4. **不改任何代码**，输出归因报告：
   - (i) regime 现象 / (ii) sign error / (iii) 语义错配 / (iv) 多因素并存
   - 每个反向问题分别归类
5. 如果归类含 (ii)：列出具体行号 + 修复方案 + 预期 130 条 replay 重跑后 accuracy 应该回到的范围。

### Step 3A-3：基于 3A-2 的最小修复（仅当 3A-2 定位到 sign error）
- 单点修代码（最多几行）
- 加单元测试锁定符号
- 重跑 130 条 replay
- 看 accuracy / confidence_level 排序 / peer 单调性是否恢复
- 如果恢复 → 进 Step 3B；如果未恢复 → 重新归因

### Step 3B：calibration formula design（推迟到 3A-2 / 3A-3 之后）
- 在 confidence / peer / soft_signal 语义确认后再设计；
- 不直接改 `confidence_engine`；先在 contract `extras` 加 `confidence.score: float` 候选字段；
- 用 130 条 replay 做 dry-run 对照，再决定是否升 03 / 05 顶层。

### Step 3C：写入 05 score 字段（最末位）
- 仅在 3B 公式落地、dry-run 验证 monotonic 之后；
- 不改 03 顶层；
- 不打开 `simulated_trade.trade_engine_enabled`。

### Step 2G exclusion soft / hard（独立路径，并行可行）
- 受本步影响：§7 显示 `soft_signal != none` 子集**比 none 更准**，所以**暂时不要把 soft_signal 直接 hard 化为 exclusion**；
- Step 2G 设计需要重新评估"什么样的 signal 才适合做 hard exclude"；
- 如果 3A-2 把 peer 反向问题定位为 sign error 并修复，soft_signal 的语义可能也跟着回归正常，再评估 2G。

## 12. 严守边界（本轮已遵守）

- ❌ 没改任何代码（`services/` / `scripts/` / `tests/` 0 字节变化）
- ❌ 没新增测试
- ❌ 没 commit / push
- ❌ 没写 DB
- ❌ 没改 DB schema
- ❌ 没改 [confidence_engine.py](../services/confidence_engine.py) / [risk_model.py](../services/risk_model.py) / [contradiction_engine.py](../services/contradiction_engine.py)
- ❌ 没改 [predict.py](../services/predict.py) / [scanner.py](../services/scanner.py) / [prediction_store.py](../services/prediction_store.py) / adapter / validator
- ❌ 没升级 contract 04（exclusion required）/ 05（score）/ 07（simulated_trade required）顶层字段
- ❌ 没把 `soft_signal != none` 升级为 hard exclusion
- ❌ 没接 yfinance / 网络
- ❌ 没接 trading API / longbridge / broker / paper_trade
- ❌ 没生成新脚本进仓库（所有诊断走 inline `python3 << PY`，无 csv / 中间文件落盘）
- ❌ 没触碰 stash / .claude/worktrees/ / logs/prediction_log.jsonl
- ✅ 仅 sqlite SELECT + json 解析 + 三个现有 read-only 工具（calibration_inputs / dashboard / correlation）+ 新 docs 1 份
