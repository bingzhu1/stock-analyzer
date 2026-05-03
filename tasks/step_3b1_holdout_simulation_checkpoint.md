# Step 3B-1 — Holdout Simulation Checkpoint

> 状态：Step 3B 设计的 4×4 lookup table + R4/Q3 downgrade 规则在 cross-window holdout 上**FAIL**：6 项通过标准只过 2 项（direction unchanged + coverage），核心的 monotonicity / R4 触发 / probability calibration / robustness 全部失败。**不进 Step 3B-2 sidecar schema design**。失败根因是**样本稀疏**（250/16=平均 15/cell；只有 4/16 cells 有 ≥10 paired）+ lookup table cell 在 W1↔W2 间不可迁移；regime 信号本身（pos20 单调 bias -36→+47）依然成立，但 4 桶离散化让连续信号被噪声主导。**推荐 Option A：Step 3A-4 第三窗口扩样本到 ~380 records**，再重试 holdout。
> 本文件只写文档，不改代码，不写 DB，不 commit，不 push。

## 1. 当前完成状态

| 子步 | 主题 | 状态 |
|---|---|---|
| Step 3B | regime-aware calibration design doc | ✅ commit `bf7b9dc` |
| fix(docs) | final test cutoff 2006 → 2026-01-01 | ✅ commit `25d1410` |
| **Step 3B-1** | **holdout simulation（read-only 4×4 + 2×2 + R4/Q3）** | ✅ FAIL（本文件 checkpoint） |
| Step 3B-2 / 3B-3 / 3B-4 | sidecar schema / simulator / contract extras 暴露 | **暂缓**（待 holdout 通过） |
| Step 3A-4 | 第三时间窗口 replay 扩样本（推荐） | 待开 |
| Step 3C | 升 05 顶层 score 字段 | **冻结，最末位** |
| Step 2G | exclusion soft → hard 重审（独立路径） | 视后续；当前建议**取消或重新设计** |

## 2. 数据基线

| 字段 | 值 |
|---|---|
| `valid_payloads` | 250 |
| `paired_outcomes` | 193 |
| `calibration_ready` | True |
| `missing_dimensions` | `[]` |
| Window2 | 2023-08-07 → 2024-01-26（120 records） |
| Window1 | 2024-01-29 → 2024-08-02（130 records） |
| 测试基线 | 2233 passed / 0 failed / 10 skipped（与上一轮 main 一致） |

本轮 0 代码 / 0 测试 / 0 DB / 0 schema 改动。

## 3. Method B：Window2 design / Window1 holdout

### 3.1 W2 拟合的 4×4 lookup table（稀疏）

| psr × pos20 | low (≤0.38) | mid (0.38–0.62] | high_mid (0.62–0.82] | high (>0.82) |
|---|---|---|---|---|
| **strong_bear** (psr ≤ -2) | 14p / 0.500 / cell / **med** | 2p / row 0.438 / **low** | 0p / row / **low** | 0p / row / **low** |
| **weak_bear** (psr -2..0] | 4p / row 0.692 / **high** | 5p / row / **high** | 3p / row / **high** | 1p / row / **high** |
| **weak_bull** (psr 0..2] | 6p / row 0.581 / **med** | 7p / row / **med** | 8p / row / **med** | 10p / 0.600 / **high** |
| **strong_bull** (psr > +2) | 2p / row 0.515 / **med** | 8p / row / **med** | 4p / row / **med** | 19p / 0.474 / **med** |

**关键事实**：
- 16 cells 中只有 **4 cells** 有 `paired ≥ 10`（粗体）；
- 其余 12 cells fallback 到 row baseline；
- `weak_bear` 整行只有 13 paired（4+5+3+1），row baseline 0.692 是小样本噪声，被推广到 4 个稀疏 cell；
- 这 4 个 cell 全部被分类为 `cal_conf=high`，**这是 calibrated_high bucket 的主要来源**。

### 3.2 W1 original 与 calibrated 对比

**W1 original confidence_level**（无 calibration）
| bucket | n | paired | correct | wrong | accuracy |
|---|---|---|---|---|---|
| high | 53 | 51 | 22 | 29 | **0.431** |
| medium | 30 | 29 | 12 | 17 | 0.414 |
| low | 47 | 20 | 10 | 10 | 0.500 |

**W1 calibrated**（apply W2 lookup + R4/Q3 rules）
| bucket | n | paired | correct | wrong | accuracy |
|---|---|---|---|---|---|
| high | 24 | 24 | 8 | 16 | **0.333** ❌ |
| medium | 68 | 68 | 32 | 36 | 0.471 |
| low | 8 | 8 | 4 | 4 | 0.500 |

### 3.3 结论
- ❌ Calibrated `high` accuracy（0.333）**比 original high (0.431) 更差**
- ❌ Monotonicity 仍失败：calibrated high (0.333) < calibrated medium (0.471) < calibrated low (0.500)
- ❌ Coverage：calibrated_high 从 51 paired → 24 paired（损失 53%）
- ✅ Direction 100% unchanged
- 整体：W2 → W1 holdout **未通过**

## 4. Method A：Window1 design / Window2 holdout

### 4.1 W1 拟合的 4×4 lookup table
- **0 个 cell 被分类为 `cal_conf=high`**：W1 整体 acc 0.440，所有 cells（含 fallback）都 < 0.60 阈值
- 全表只有 medium / low 两档（部分 cell `acc < 0.45` → low）

### 4.2 W2 original 与 calibrated 对比

**W2 original confidence_level**
| bucket | paired | accuracy |
|---|---|---|
| high | 55 | 0.509 |
| medium | 21 | 0.524 |
| low | 17 | 0.706 |

**W2 calibrated**
| bucket | paired | accuracy |
|---|---|---|
| **high** | **0** | **n/a（被剥夺）** ❌ |
| medium | 57 | 0.491 |
| low | 36 | 0.639 |

### 4.3 结论
- ❌ **High bucket 完全消失**：W2 原本 55 个 high paired (acc 0.509) 全部降级到 medium/low
- ❌ Calibration 破坏了原本工作的子集（W2 original 0.509 → calibrated medium 0.491）
- ✅ Direction 100% unchanged
- 整体：W1 → W2 holdout **崩盘**

## 5. 2×2 collapsed fallback（最后挽救尝试）

axis collapse：`psr_sign ∈ {neg, pos}` × `pos2 ∈ {low (≤0.62), high (>0.62)}`

### 5.1 Method B 2×2（W2 design / W1 holdout）

W2 fitted 2×2：
| psr_sign × pos2 | paired | acc | cal_conf |
|---|---|---|---|
| neg × low | 25 | 0.520 | medium |
| neg × high | 4 | 0.750 | high（小样本） |
| pos × low | 23 | 0.609 | **high** |
| pos × high | 41 | 0.512 | medium |

W1 calibrated 2×2：
| bucket | paired | accuracy |
|---|---|---|
| high | 19 | **0.474** |
| medium | 81 | 0.432 |

- 微弱 monotonicity（high 0.474 vs medium 0.432，+4 ppts）
- 但 high 从 51 → 19 paired，损失 60% 覆盖率
- 这个 high 来自 W2 cell `psr=pos × pos=low` (W2 fitted 0.609) → W1 实测 0.474，**不可重复**

### 5.2 Method A 2×2（W1 design / W2 holdout）

W2 calibrated 2×2：
| bucket | paired | accuracy |
|---|---|---|
| high | 4 | 0.750（小样本） |
| medium | 41 | 0.512 |
| low | 48 | **0.562** |

- low (0.562) > medium (0.512) → **partial inversion 仍存**
- high 仅 4 paired，统计意义不足

### 5.3 结论
2×2 也不足以支持进入 Step 3B-2：双向都无法稳定 monotonicity / coverage 二者兼得。

## 6. R4 / Q3 downgrade 规则实际效果

| 指标 | Method B (W1 holdout) | Method A (W2 holdout) |
|---|---|---|
| R4 candidates paired | 12 | 9 |
| R4 candidate accuracy | 0.417 | 0.333 |
| Q3 high-conf candidates paired | 10 | 6 |
| Q3 candidate accuracy | **0.200** | 0.333 |
| **R4 downgraded by lookup** | **0** | **0** |
| **Q3 downgraded by lookup** | **0** | **0** |

### 失败原因
- lookup table 已经把 R4 / Q3 命中的 cells 分到 medium/low；
- 没有 `high → medium` 的 transition 给规则下手；
- **R4 / Q3 rule 在当前 lookup 实现下完全冗余**；
- 这是设计层面的耦合错误：lookup 强势 + rule 缺位 → 规则的 "downgrade overconfident high" 意图被 lookup 用 "directly demote to medium" 抢先满足。

> 注：Q3 实测 acc 0.200（只 10 paired）与 Step 3B-0 全数据 0.263（19 paired）方向一致，**Q3 high-conf 失败信号是真的**，只是规则架构没机会触发。

## 7. 通过标准判定（按 Step 3B 设计 §13）

| # | 标准 | 目标 | Method B | Method A | 总判 |
|---|---|---|---|---|---|
| 1 | calibrated bucket monotonicity | high ≥ medium ≥ low | high 0.333 < med 0.471 < low 0.500 | high 不存在 | ❌ FAIL |
| 2 | R4 子集 up_acc ≥ 0.45 | 0.45 | R4 没触发（0 downgraded） | R4 没触发 | ❌ FAIL（no trigger） |
| 3 | probability calibration deviation | mean dev ≤ 0.10 | cal_high 0.333 vs W2 fit 0.692 → dev 0.36 | high bucket 空 → 不可计算 | ❌ FAIL |
| 4 | direction 100% unchanged | 100% | ✅ | ✅ | ✅ PASS |
| 5 | coverage ≥ 80% paired records | 80% | 100% | 100% | ✅ PASS |
| 6 | holdout robustness 双向都不崩 | 不崩 | high acc 比 baseline 还差 | high bucket 完全消失 | ❌ FAIL |

**总结**：**2 / 6 PASS，4 / 6 FAIL → Step 3B-1 overall = FAIL** ❌

## 8. 失败根因

| 根因 | 证据 |
|---|---|
| **样本稀疏** | 250 records / 16 cells = 平均 15/cell；只有 4/16 cells 有 paired ≥ 10 |
| **Lookup table 不可迁移** | W2 best cell（psr=pos × pos=low → 0.609）在 W1 实测 0.474；window-specific 行为没有推广性 |
| **离散化丢失 monotonic 结构** | pos20 是连续信号（bias -36 → +47 单调），4 桶离散后小样本噪声主导 |
| **Lookup 与规则耦合错误** | lookup 把 R4/Q3 命中的 cell 提前分到 medium/low，规则没有 transition 可触发；R4/Q3 rule 本应在"lookup 仍标 high"的子集上做 downgrade |
| **2×2 collapse 也不解决** | high bucket 要么覆盖崩（19/51）要么样本崩（4 paired） |

> Step 3B-0 找到的 regime feature（pos20）**信号本身依然成立**（4 quartile bias 单调），但 4×4 / 2×2 离散 lookup 都不是**正确的承载形式**。

## 9. 是否进入 Step 3B-2

❌ **不建议进入 Step 3B-2 sidecar schema design**。理由：
1. lookup table 第一版已被 holdout 否决，schema 设计无依据；
2. Step 3B 设计 §9.4 明确"任一指标不达标 → 不进 Step 3B-2"，本步骤 4/6 失败；
3. **05 score 字段继续保持 `0.0` / `event_score=None`**（Step 3A-2 / 3B 已确认是 by design）；
4. **不能实现 calibration formula**（4×4 lookup 不可重复，参数化方法需要写 Python module 超 Step 3 当前范围）；
5. Step 3B-3 / 3B-4 / 3C 全部冻结，待样本扩展或方法换轨后重启。

## 10. 下一步建议

| Option | 推荐度 | 描述 | 风险 / 工作量 |
|---|---|---|---|
| **A. Step 3A-4 第三窗口扩样本** | ⭐⭐⭐⭐ **推荐** | 写第三窗口 130 records；250 → ~380 records；4×4 cells 平均 ~24/cell；2×2 cells 平均 ~95/cell；重跑 Step 3B-1 | 低（duplicate guard / cap=130 / CLI 都已就位） |
| B. 改用连续平滑公式 / logistic-like calibration | ⭐⭐ | 不离散化，用 score / pos20 / a-s 三个连续 feature 拟合 | 需要写 Python module，超 Step 3 当前 docs-only 范围 |
| C. 暂停 Step 3，转 Step 2G 重审 / dashboard 升级 | ⭐⭐ | 与 calibration 正交；与 Step 3 系列没有依赖 | 不解决 calibration 主问题 |

### A 的执行建议（**推荐**）

**第三窗口 start_date 选择**：
- **优选**：`--start 2023-01-01 --limit 130` —— 与现有 W2（2023-08-07 起）有有限重叠（约 5-10 个交易日 dup-skip），新写约 120-125 records；不引入完全陌生的 regime（仍是 2023 上半年的 AVGO）
- **备选**：`--start 2022-08-01 --limit 130` —— 完全无重叠，引入 2022 后半年（含 tech 跌后修复期）；可能引入新 regime 但样本质量不确定
- **不推荐**：`--start 2022-01-01` 或更早 —— 2022 是 tech 大跌年，AVGO 同期波动大；引入 bear regime 会让 calibration 更难拟合

**执行流程**（与 Step 3A-3 同节奏）：
1. 备份 DB（`avgo_agent.db.backup_pre_3a4_<ts>`）
2. dry-run：`python3 scripts/run_contract_replay.py --symbol AVGO --start 2023-01-01 --limit 130`，确认 candidate_pair_count / overlap 数
3. 真写：上一条 + `--write`
4. 验证 DB 行数（253 → ~370）+ duplicate snapshot_id = 0 + 时间窗口连续
5. 跑三件套工具（calibration_inputs / dashboard / correlation）记录新 baseline
6. **重跑 Step 3B-1 holdout 双向**（W1+W2 design / W3 holdout，以及 W3 design / W1+W2 holdout）
7. 如果重跑 holdout 通过 → 进 Step 3B-2；否则继续等数据 / 改方法

## 11. 2026 final test cutoff 状态

- ✅ Step 3B design doc 已修正（commit `25d1410`）：
  - 标题 §11："2006-01-01" → "2026-01-01"；
  - Final test range 描述：删除"2008/2018/2020/2022 等历史 regime"，改为"2026-01-01 之后的真实运行 prediction → outcome 对照（forward-looking）"；
  - Validation windows 范围：2024-08-06..2025-12-31 + 2023-08-07 之前的有限历史段；
  - 强化禁触表述："绝对不要"、"先看一眼 2026 再回头改公式"也明确禁止；
- ✅ `grep "2006" tasks/step_3b_*` 现在 0 命中。
- 本 checkpoint 继续严格遵守：
  - 不使用 2026-01-01 之后的 prediction → outcome 数据做调参 / 抽样 / sanity check；
  - 当前 2023-2024 replay 仍属于 development / validation diagnostics；
  - **Step 3A-4 第三窗口建议起点 2023-01-01 或 2022-08-01，远早于 2026-01-01，不会触碰 final test range**。

## 12. 严守边界（本轮已遵守）

- ❌ 没改任何代码（`predict.py` / `services/*.py` / `scripts/*.py` / `tests/*.py` / `scanner.py` / confidence_engine 0 字节变化）
- ❌ 没新增测试
- ❌ 没 commit / push
- ❌ 没写 DB
- ❌ 没改 DB schema
- ❌ 没实现 calibration formula（仅 inline `python3 << PY` 模拟，未落盘）
- ❌ 没升级 contract 04 / 05 / 07 顶层字段
- ❌ 没写 Python module / 没建 service
- ❌ 没保存 csv / 新脚本进仓库
- ❌ 没接 yfinance / 网络
- ❌ 没接 trading API / longbridge / broker / paper_trade
- ❌ 没用 2026-01-01 之后的 final test range 做任何分析
- ❌ 没触碰 stash / .claude/worktrees/ / logs/prediction_log.jsonl
- ✅ 仅新增 1 个 markdown checkpoint
