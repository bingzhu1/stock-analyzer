# Step 2G-7 — Anti-False-Exclusion Display / Design

> **设计文档（anti-false-exclusion display design），不是实现。**
> 本文档**冻结**未来 anti-false-exclusion 显示层的目标、ground truth
> 来源、5 个候选保护信号、display sidecar schema、UI 显示位置、文案
> 边界、与 04 / 05 / 07 required 字段的硬隔离、与 hard gate 的强制
> 阻断关系、未来实现路径与成功标准。
>
> 本轮**不动任何代码**：不改 `predict.py` / `run_predict` /
> `scanner.py` / `prediction_store.py` / `app.py` / `ui/*` /
> `services/*` / 任何 builder / DB schema 中的任何一处。

## 1. 背景

- **Step 2G-3** soft / hard exclusion re-review（commit `8e837a7`）：
  R4 是 over-bullish risk 的最尖锐信号，但 `false_exclusion_rate=0.3235`
  远超 0.10 hard gate；**R4 不能 hard**
- **Step 2G-5** simulator（commit `947f1c9`）+ checkpoint：生成
  `soft_metadata.v1` JSON
- **Step 2G-6A** renderer + **Step 2G-6B** Predict display hook +
  **Step 2G-6B.6/6B.7** baseline cache + scan_result regime_features：
  Predict 页面**真实显示**完整 R4 / residual card
- **Step 2G-6C** Review 页面接入（commit `2616a72`）+ checkpoint：
  4 象限归因规则在 UI 落地
  - wrong + metadata → `possible_attribution`
  - **correct + metadata → `triggered_but_not_error`**（**误杀风险样本**）
  - wrong + no metadata → `no_attribution`
  - correct + no metadata → `no_metadata`
- **Step 2G-7** 的目标**不是启用 hard**，而是**设计未来避免误杀的
  保护层显示** —— 把 `correct + metadata triggered` 这个 ground truth
  显示出来，让消费者一眼看到"如果 hard 排除，会同时杀掉这些正确
  样本"的事实。

## 2. 为什么需要 anti-false-exclusion

R4 真实数据（main DB / 380 replay / 286 paired）：

| 指标 | 值 |
|---|---|
| R4 paired | **34** |
| R4 correct | **11** |
| R4 wrong | 23 |
| R4 accuracy | **0.324** |
| R4 false_exclusion_rate（= correct/paired） | **0.3235** |
| Hard gate（`false_exclusion_rate ≤ 0.10`）| **fail（超阈值 3.2 倍）** |

**关键观察**：
- R4 accuracy 低（32.4%）→ "看起来"应该排除
- 但 false_exclusion_rate 高（32.4%）→ 排除会同时**误杀 11 个正确样本**
- 这两个数字**几乎相等**是巧合 —— 因为 R4 的 `predicted_bullish_rate=1.0`，
  所以 correct = "实际上涨" = "actual_up_count"，而 false_exclusion_rate
  恰好就是 accuracy

**`correct + metadata triggered` 是保护层最重要的样本**：
- 没有这些样本，hard gate 评估会变成"只看 wrong"的过拟合
- Step 2G-6C 已经把这 11 个样本的归因区块化（`triggered_but_not_error`）
- Step 2G-7 要把"如果硬化排除，会损失多少 correct"这件事**显式
  量化展示**

**不能只看 wrong + metadata**：
- 如果只优化"减少 wrong"，会鼓励过度排除
- 任何排除规则都必须同时考虑误杀代价
- 这是 Step 2G 设计文档 §6 红线"任何单一信号永远不能直接 hard"
  的更细粒度表达

## 3. 当前 hard gate 状态

按 Step 2G-3 §10 / Step 2G-4.5 §10.1.6 / Step 2G-6B.3 checkpoint
§12 的 hard gate 表：

| 检查项 | 当前 | 通过 |
|---|---|---|
| 总 (contract × outcome) pair ≥ 90 | **286** | ✅ |
| 至少一个候选触发样本 ≥ 30 | R4=34 / pos20×high=79 等多个 | ✅ |
| 至少一个候选 `false_exclusion_rate ≤ 0.10` | 最低 R4=**0.3235** | ❌ |
| 至少一个候选 `net_benefit ≥ +0.05` | 最高 R4=**+0.0219** | ❌ |
| `anti_false_exclusion` 至少一个保护层模块接主链 | 0 / 4 | ❌ |
| 跨窗口 holdout 通过 | Step 3A-4 / 3B-1 holdout **FAIL** | ❌ |

**结论**（与 Step 2G-3 / 6B.3 一致）：
- ❌ **hard 禁止**（`false_exclusion_rate` / `net_benefit` 任何候选都
  达不到；保护层未接；holdout fail）
- ❌ **`forced_exclusion` 禁止**（hard 都没启用，forced 没有落地基础）
- ❌ **04 required 字段继续 stub**（`exclusion_level=none` /
  `exclusion_sources=[]` / `exclusion_reasons=[]` / `forced_exclusion=False` /
  `anti_false_exclusion_triggered=False`）
- Step 2G-7 的工作是**显示**这些 fail 项，让消费者看到"为什么不能
  hard"，**不是**让 hard 启动

## 4. 保护层目标

anti-false-exclusion **不是**为了否定更多，而是为了：

| 目标 | 说明 |
|---|---|
| ✅ **识别 soft risk 中可能被误杀的样本** | `correct + metadata triggered` = "结构幸存"样本；统计 + 显示 |
| ✅ **显示 "risk triggered but survived"** | UI 把 11/34 = 32% 这件事说清楚（已在 Step 2G-6C 4 象限实现，本步把累计统计补全）|
| ✅ **阻止未来把 soft signal 直接 hard 化** | sidecar `hard_exclusion_allowed=False` + UI 显示 "当前不允许强制否定" + `primary_reason` 说明哪一项 fail |
| ✅ **作为 hard gate 前置诊断** | 列出当前 fail 的 gate 项 + `required_next_step` 给出"还差什么" |
| ✅ **给 review / dashboard 提供反例样本** | 累积 survived case + false_exclusion_risk 列表，供 Step 2G-7C dashboard 消费 |

## 5. Ground truth 来源

Ground truth 来自 Step 2G-6C Review 4 象限：

| 象限 | metadata triggered | prediction outcome | anti-false-exclusion 用途 |
|---|---|---|---|
| `possible_attribution` | ✅ | wrong | exclusion candidate sample（"该 metadata 触发时确实更容易错"）|
| `triggered_but_not_error` | ✅ | correct | **anti-false-exclusion positive sample**（"如果 hard 排除，会损失这些正确预测"）|
| `no_attribution` | ❌ | wrong | risk model missed sample（其他 dimension 错误，不归因到 metadata）|
| `no_metadata` | ❌ | correct | neutral baseline（不参与 exclusion 评估）|

**重点**：
- `correct + metadata` 是 anti-false-exclusion **positive sample**
- `wrong + metadata` 是 exclusion **candidate sample**
- **两者要同时看** —— 任何评估都必须计算两者的 ratio：如果 hard 排除
  candidate，会同时杀掉多少 positive？这就是 `false_exclusion_rate`
- Step 2G-7A display helper 应**累计统计**两者，让 dashboard 显示
  "metadata triggered N 次，其中 correct M 次（survival rate=M/N）"

## 6. 候选保护信号设计

提出 **5 个保护信号**（用户 / dashboard 消费者关心的诊断维度）：

### 6.1 `r4_survival_case`

| 字段 | 内容 |
|---|---|
| `condition` | metadata `r4_overextension` triggered AND prediction correct |
| `meaning` | R4 触发但实际没错，未来**不能直接 hard** |
| `severity` | `informational`（仅记录，不告警） |
| `display` | "风险触发但本次结构幸存" |
| `data source` | Step 2G-6C `triggered_but_not_error` 象限累计 |

### 6.2 `r4_false_exclusion_risk`

| 字段 | 内容 |
|---|---|
| `condition` | R4 historical `false_exclusion_rate > 0.10` |
| `meaning` | 该信号**本身误杀率过高**；hard gate 不通过 |
| `severity` | `medium`（block hard） |
| `display` | "当前不允许强制否定（误杀率 32.4% > 10%）" |
| `data source` | Step 2G-5 simulator baseline `false_exclusion_rate` |

### 6.3 `soft_metadata_holdout_fail`

| 字段 | 内容 |
|---|---|
| `condition` | `holdout_status == "FAIL"`（Step 3A-4 / 3B-1 跨窗口 holdout）|
| `meaning` | 该 metadata 未通过跨窗口稳定性验证 |
| `severity` | `medium`（block hard） |
| `display` | "仅复盘参考（跨窗口 holdout 失败）" |
| `data source` | Step 2G-5 simulator baseline `holdout_status`（固定 `"FAIL"` 直到 Step 3 calibration 重启）|

### 6.4 `net_benefit_insufficient`

| 字段 | 内容 |
|---|---|
| `condition` | `net_benefit < +0.05` |
| `meaning` | 强制排除净收益不足（即使排除全部 wrong，整体 accuracy 提升不够）|
| `severity` | `medium`（block hard） |
| `display` | "不满足 hard gate（净收益 +2.2% < 5%）" |
| `data source` | Step 2G-5 simulator baseline `net_benefit` |

### 6.5 `missing_protection_layer`

| 字段 | 内容 |
|---|---|
| `condition` | 4 个 anti-false-exclusion 候选模块（`anti_false_exclusion_audit` / `big_up_contradiction_card` / `big_down_tail_warning` / `exclusion_reliability_review`）**全部未接主链** |
| `meaning` | 没有保护层前**不能** hard |
| `severity` | `high`（system-level block）|
| `display` | "保护层未接入（4 个候选模块全离线）" |
| `data source` | 静态状态；Step 2G-7C dashboard 可显示哪些模块离线 |

## 7. Display schema 草案（sidecar; soft_metadata 同级）

```python
exclusion_system.extras.anti_false_exclusion_display = {
    "schema_version": "anti_false_exclusion_display.v1",
    "status": "blocked",                                # "blocked" | "open"（未来若 gate 通过）
    "hard_exclusion_allowed": False,                    # 永远 False（v1 spec 强约束）
    "primary_reason": "false_exclusion_rate_too_high",  # enum：定位最关键的 fail 项
    "protective_findings": [
        {
            "name": "r4_false_exclusion_risk",
            "severity": "medium",                       # "informational" | "medium" | "high"
            "evidence": {
                "false_exclusion_rate": 0.3235,
                "threshold": 0.10,
                "correct_when_triggered": 11,
                "paired": 34,
            },
            "message": "R4 触发时仍有较多正确样本，当前不能强制否定。",
        },
        {
            "name": "r4_survival_case",
            "severity": "informational",
            "evidence": {
                "survived_count": 11,
                "total_triggered_count": 34,
                "survival_rate": 0.3235,
            },
            "message": "本次/累计：风险触发但本次结构幸存。",
        },
        # ... 0..N entries; one per protective signal
    ],
    "recommended_action": "review_only",                # 永远 "review_only"；不出现 exclude/hard/forced
    "required_next_step": "collect_more_review_outcomes",  # enum：还差什么才能 hard
    "warnings": [str, ...],                             # final_test_range_refusal 等
}
```

强约束（spec 层面）：

- ❌ **不**进 04 / 05 / 07 任何 required 字段
- ❌ **不**改 `exclusion_level`（继续 `"none"`）
- ❌ **不**改 `forced_exclusion`（继续 `False`）
- ❌ **不**改 `anti_false_exclusion_triggered`（继续 `False` —— 这个
  字段是**完全独立**的 04 required 字段，与本 sidecar **不同名**；
  本 sidecar 是**显示层 diagnostic**，required 字段是**未来真接入
  保护层后才用**）
- ✅ `hard_exclusion_allowed` **永远** `False`（与 `soft_metadata.v1`
  双重锁定）
- ✅ sidecar **同级**于 `soft_metadata`（都在 `extras`）
- ✅ 任何字段写入失败 → 整段 sidecar 省略，**不**部分填

## 8. UI 显示位置

### 8.1 Predict 页面

- **位置**：在 soft metadata card 的**展开（expandable）区域**显示
  "为什么不能 hard"
- **不**新增独立 section（避免 dashboard 噪声）
- **不**新增危险文案（按 §9 文案边界）
- 行为：
  - 默认折叠
  - 用户点开展开后，列出 `protective_findings` 5 个候选信号 +
    `primary_reason` + `required_next_step`
  - 显示 `r4_false_exclusion_risk.evidence`：误杀率 32.4% / 阈值
    10% / 相关 11/34 样本

### 8.2 Review 页面

- **位置**：在 metadata attribution band（Step 2G-6C 已有）**之下**
  追加一个独立但折叠的小 section：
  - "保护层诊断（read-only）"
- 内容：
  - `r4_survival_case`：本次是否属于 survival case + 累计 survival
    rate
  - `r4_false_exclusion_risk`：阻止 hard 化的当前理由
  - `missing_protection_layer`：4 个候选保护层模块离线状态
- 用途：解释为什么该 signal **不能硬化**；让用户看到完整证据链
  （归因 + 保护诊断双重显示）

### 8.3 Dashboard（Step 2G-7C 范围）

- **位置**：现有 dashboard 一个新 tab 或 sidebar 区
- 内容：
  - **累计统计**："metadata triggered N 次 / correct M 次 / survival
    rate=M/N / current period 区间"
  - **5 个保护信号的当前状态表**（block / informational / high
    severity 各几个）
  - **hard gate 6 项 fail / pass 一栏**
- 用户用途：一眼看到 "为什么 hard 仍然禁止"
- 实施延后到 Step 2G-7C（与 7A / 7B 解耦）

## 9. 文案边界

**禁止**（与 Step 2G-6 / 6A 16 forbidden words 一致 + 额外）：
- 禁止交易 / 强制否定 / 必须不做
- hard exclusion / forced exclusion / hard / forced
- 自动拦截 / no_trade
- 卖出信号 / 做空信号 / 看空信号
- 否决主推演 / 推翻主推演
- 强制平仓 / force close
- 阻止下单 / block order
- 排除（除非紧跟"率" / "代价"等修饰词，如"误杀率"）

**推荐**：
- 当前不允许强制否定
- 仅供复盘参考
- 风险触发但结构幸存
- 误杀风险较高
- 保护层未接入
- 不改变主推演方向
- 不构成交易指令
- 跨窗口 holdout 失败
- 不满足 hard gate
- 累计 N 次触发，M 次正确

文案约束保持与 Step 2G-6 §3 一致：renderer 自动 grep 锁定；本步
新增 display helper 也必须通过相同 grep 测试。

## 10. 与 04 / 05 / 07 required 字段关系

| 字段 / 位置 | Step 2G-7 行为 |
|---|---|
| 04 `exclusion_system.exclusion_level` | ❌ 不变（继续 `"none"`）|
| 04 `exclusion_system.exclusion_sources` / `exclusion_reasons` | ❌ 不变 |
| 04 `exclusion_system.forced_exclusion` | ❌ 不变（continue `False`） |
| 04 `exclusion_system.anti_false_exclusion_triggered` | ❌ 不变（continue `False`）—— **不同于本 sidecar**：required 字段需要真接入保护层 + hard gate 通过；本 sidecar 是 display-only diagnostic |
| 04 `exclusion_system.extras.anti_false_exclusion_display` | ✅ **新增 sidecar**（仅 spec；Step 2G-7A 实施）|
| 05 `confidence_system` 任何字段 | ❌ 不变 |
| 06 `final_projection.*` 任何字段 | ❌ 不变 |
| 07 `simulated_trade` 任何字段 | ❌ 不变 |
| `summary.hard_exclusion_allowed`（本 sidecar 内）| ✅ 永远 `False`（v1 强约束）|

如果未来要写 04 required `anti_false_exclusion_triggered=True`，
**必须** Step 2G-8+ 并满足：
1. Step 2G 设计文档 §8 hard gate **全部通过**（false_exclusion_rate
   ≤ 0.10 + net_benefit ≥ +0.05 + 跨窗口 holdout 通过）
2. 至少一个 anti-false-exclusion 保护层模块**真接入主链**（不只是
   display sidecar）
3. Step 3 calibration 重启的 holdout 评估通过（**当前 FAIL**）

## 11. 未来实现路径

| 步骤 | 范围 | 期望 commit |
|---|---|---|
| **Step 2G-7** | 本设计文档 | 1 个 markdown |
| **Step 2G-7A** | Read-only display helper：新增 `services/anti_false_exclusion_display.py`（pure function）+ tests；输入 baseline / metadata + Review 4 象限累计统计；输出本文档 §7 schema；**不**写 DB | 1 个 service / 1 个 test 文件 |
| **Step 2G-7B** | Renderer integration into Predict / Review expandable section：调 §11.A helper + 渲染 markdown；**不**改 `_build_exclusion_system`、**不**改 contract validator | UI 改动（Predict + Review 各 +~30 行）|
| **Step 2G-7C** | Dashboard aggregate diagnostics：新增 dashboard tab / sidebar 区域显示累计 metadata 触发 + survival rate + 5 保护信号状态 + hard gate 6 项；纯 UI 改动 | UI 改动 |
| **Step 2G-8+** | **只有** hard gate 通过后才讨论 04 required `anti_false_exclusion_triggered=True` 升级 | （前提不满足时不启动） |

强约束：
- Step 2G-7A helper **必须** read-only：纯函数；不读 DB / 不读 CSV /
  不接网络（所有数据来自 baseline + caller-injected累计统计）
- Step 2G-7B / 7C **不**改 `_build_exclusion_system`、**不**改
  `_build_confidence_system`、**不**改任何 04 / 05 / 07 required
  字段
- Step 2G-7C dashboard 显示**只**展示 sidecar JSON；不重新 query DB
- 任何 step 之间的失败回退路径：sidecar 缺失 → UI 显示原状（不
  crash）

## 12. 成功标准

未来若实施 Step 2G-7A / 7B / 7C 必须满足：

| # | 标准 |
|---|---|
| 1 | `hard_exclusion_allowed` 在所有 sidecar 输出中**永远** `False`（任何输入下；v1 spec 强约束） |
| 2 | 不出现 §9 的 forbidden words（grep 锁定，与 Step 2G-6 / 6A 共用 16 words 锁）|
| 3 | `correct + metadata triggered` 能被识别为 survival case 并出现在 `protective_findings` |
| 4 | `false_exclusion_rate` 显示清楚（数字 + 阈值 + correct/paired counts）|
| 5 | **不**写 DB（helper 模块无 `init_db` / `INSERT` / `UPDATE` /  `prediction_store.save_*`）|
| 6 | **不**改 04 / 05 / 07 任何 required 字段（snapshot 测试锁定）|
| 7 | AppTest 覆盖 Predict expandable / Review expandable 显示路径 |
| 8 | 现有测试基线（2448 / 0 failed / 10 skipped）不变 —— Step 2G-7A / 7B / 7C 新增测试是净增 |
| 9 | sidecar 与 `soft_metadata` 同级且互不干扰（`soft_metadata` 字段不被 anti-false-exclusion 覆盖）|
| 10 | `r4_survival_case.evidence` 数字与 Step 2G-6C `triggered_but_not_error` 累计统计一致 |

## 13. 2026 final test cutoff

- 本设计**只**基于 2023-2024 replay / Review 数据
- Step 2G-7A helper 必须**透传** `analysis_date` 给底层（与 Step
  2G-5 / 6B.3 / 6B.6 一致）；`analysis_date >= "2026-01-01"` 时：
  - sidecar `warnings` 含 `"final_test_range_refusal"`
  - `protective_findings` 仍可显示 baseline 来源数字（informational
    only）
- **不**用 2026-01-01 之后数据调参 / 反复跑
- 2026 之后仍是**整个系统**完成后的最终测试集

## 14. 不做什么

- ❌ **不**启用 `hard` exclusion
- ❌ **不**启用 `forced_exclusion=True`
- ❌ **不**启用 `anti_false_exclusion_triggered=True`（04 required 字段）
- ❌ **不**写 DB（display sidecar 是 informational；不持久化）
- ❌ **不**改 `prediction_store` / DB schema
- ❌ **不**改 `run_predict` / `predict.py`
- ❌ **不**改 `scanner.py`
- ❌ **不**升级 04 / 05 / 07 任何 required 字段
- ❌ **不**保存 `anti_false_exclusion_display` 到 `prediction_log` /
  `outcome_log` / `review_log`
- ❌ **不**接 4 个 anti-false-exclusion **离线**模块
  (`anti_false_exclusion_audit` / `big_up_contradiction_card` /
  `big_down_tail_warning` / `exclusion_reliability_review`) 到主链
  —— 它们仍是离线 audit / UI；本 step 只**显示**离线状态，**不**
  接入
- ❌ **不**接 trading API / `longbridge` / `broker` / `paper_trade`
- ❌ **不**接 `yfinance` / `requests` / 任何网络
- ❌ **不**用 2026-01-01 之后 final test range 调参

## 15. 下一步建议

按推荐优先级：

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **Step 2G-7A** read-only display helper + tests | `services/anti_false_exclusion_display.py` 纯函数 + 单元测试覆盖 5 个 protective signal + 16 forbidden words + isolation；**不**改 04 / 05 / 07 / DB / run_predict | **高**（本设计文档天然延续；零风险）|
| 2 | **Step 2G-7B** Predict / Review expandable integration | 在 Predict 的 soft metadata card 展开区 + Review 的 attribution band 之下加 helper 调用；UI 改动；AppTest 覆盖 | 中（与 #1 同 step 完成最佳）|
| 3 | **Step 2G-7 checkpoint** | 先冻结本设计而不启动 7A —— 让设计有更多审议时间；checkpoint 后再启动 7A | 中（如果想分两次确认设计 → 先 checkpoint 再 7A） |
| 4 | **Step 2G-7C** dashboard aggregate diagnostics | 累计触发统计 / hard gate 6 项 fail-pass 表 / 5 保护信号状态；UI 改动 | 中-低（需要 7A / 7B 完成后）|
| 5 | **不建议**直接做 hard gate 升级（Step 2G-8+） | 6 项 gate 仍有 4 项 fail；本步显示层就位**不**改变 fail 状态 | — |
| 6 | **不建议**改 `run_predict` / `prediction_store` / 04 required | 当前 sidecar + UI display + Review attribution + 保护层显示已是最大可行边界 | — |

**强制约束**：Step 2G-7A / 7B / 7C 实施时仍要遵守：
- 不改 04 / 05 / 07 required 字段
- 不改 `run_predict` 主链
- 不写 DB
- 不出现 forbidden words
- `hard_exclusion_allowed` 永远 `False`

## 16. 严守边界

- ❌ 本文档**只是**设计 / spec
- ❌ 没改任何代码
- ❌ 没新增任何测试
- ❌ 没写 DB
- ❌ 没改 DB schema
- ❌ 没接 `yfinance` / `requests` / 任何网络
- ❌ 没接 trading API / `longbridge` / `broker` / `paper_trade`
- ❌ 没改 `predict.py` / `scanner.py` / `prediction_store.py`
- ❌ 没改 `projection_output_adapter.py` / `projection_output_contract.py`
- ❌ 没改 `regime_diagnostics_dashboard.py` / `soft_metadata_simulator.py` /
  `soft_metadata_renderer.py` / `soft_metadata_injection.py` /
  `regime_features_builder.py` / `soft_metadata_baseline_cache.py` /
  `predict_tab.py` / `review_tab.py`
- ❌ 没改任何 builder（`_build_exclusion_system` /
  `_build_confidence_system` / `_build_simulated_trade` / 任何其他）
- ❌ 没改 `app.py` / 任何其他 `ui/*` 模块
- ❌ 没升级 04 / 05 / 07 任何 required 字段
- ❌ 没启用 `hard` / `forced_exclusion` /
  `anti_false_exclusion_triggered`
- ❌ 没接 4 个 anti-false-exclusion 离线模块到主链
- ❌ 没改 `final_projection` / `confidence_score` / `simulated_trade` /
  `no_trade`
- ❌ 没改 `review_log` 任何 required 字段
- ❌ 没触碰 2026-01-01 之后 final test range
- ❌ 没运行 replay / 没新写 replay 行
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` /
  `avgo_agent.db.backup_*`
- ✅ 只新增 1 份 markdown 设计文档（本文件）
