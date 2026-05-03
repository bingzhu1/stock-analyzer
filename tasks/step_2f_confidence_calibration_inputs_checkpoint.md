# Step 2F — Confidence Calibration Inputs Checkpoint

> 状态：Step 2F-1 ~ 2F-3 已全部完成。Step 2F-2 是唯一产生 commit 的子步（`7500b5b`）；2F-1 / 2F-3 是只读诊断 / 实跑验证，不产生代码改动。本文件是进入 Step 2G（exclusion 规则设计）/ Step 2F-4（真实历史回放）/ Step 3（真 calibration 接入）之前的 handoff 快照。
> 只写文档，不改任何业务代码。

## 1. 当前完成状态

| 子步 | 主题 | commit | 关键产出 |
|---|---|---|---|
| 2F-1 | 只读诊断 confidence calibration 的数据基础 | —（无代码改动） | 报告：`prediction_log` 5 行 / valid contract 2 / 含 05 extras 1 / `outcome_log` 3 行 / 可 join 到 valid contract 的 outcome **0**。**核心结论：当前 0 个 (contract × outcome) pair，calibration 不可启动。** 同步设计了 calibration_inputs 工具的输入字段、`data_gap_report` 4 维启发式、`_MIN_RECOMMENDED_PAIRS = 90` 阈值 |
| 2F-2 | 新增 read-only calibration inputs 工具 | `7500b5b feat(contract): add read-only confidence calibration inputs diagnostic` | 三件套：`services/contract_calibration_inputs.py` + `scripts/summarize_confidence_calibration_inputs.py` + `tests/test_contract_calibration_inputs.py`（31 case）；测试基线 2063 → 2094（+31） |
| 2F-3 | 实跑工具，确认 `calibration_ready=false` | —（无代码改动；只读 sqlite） | 主项目 DB 上跑 AVGO + ALL filter，输出与 2F-1 诊断完全一致：`paired_outcomes=0` / `calibration_ready=false` / 4 类 `missing_dimensions` 全部触发 |

## 2. 当前 main 状态

- **main 最新 commit：** `7500b5b feat(contract): add read-only confidence calibration inputs diagnostic`
- **测试基线：** **2094 passed / 0 failed / 10 skipped / 65 subtests**（从 Step 2E 末尾的 2063 累积 +31）
- **新增文件（Step 2F-2，已进 main）：**
  - [`services/contract_calibration_inputs.py`](../services/contract_calibration_inputs.py) — service：`summarize_confidence_calibration_inputs()` + `_MIN_RECOMMENDED_PAIRS = 90` 阈值常量
  - [`scripts/summarize_confidence_calibration_inputs.py`](../scripts/summarize_confidence_calibration_inputs.py) — CLI wrapper（`--db / --limit / --symbol`）
  - [`tests/test_contract_calibration_inputs.py`](../tests/test_contract_calibration_inputs.py) — 31 case，12 测试组

## 3. calibration inputs 工具能力

```python
def summarize_confidence_calibration_inputs(
    db_path: str | Path | None = None,
    limit: int = 50,
    symbol: str | None = "AVGO",
) -> dict[str, Any]: ...
```

- **CLI：** `python3 scripts/summarize_confidence_calibration_inputs.py [--db PATH] [--limit N] [--symbol AVGO|ALL|<TICKER>]`，stdout JSON 输出（`ensure_ascii=False, indent=2`）
- **完全只读：** 仅 `SELECT`（含 `outcome_log` 子查询，按 `captured_at DESC, rowid DESC` 取最新 outcome），不调用 `init_db`，不 `INSERT` / `UPDATE`
- **三级回退状态：** `ok` / `no_records` / `no_valid_payloads` / `error`
- **DB 关联：** `prediction_log.id = outcome_log.prediction_id` 的 LEFT-JOIN-via-correlated-subquery（与 `contract_outcome_correlation` 同模式）
- **复用既有 helper：** `_resolve_db_path / _resolve_limit / _resolve_symbol` 与 dashboard / correlate 完全同口径
- **不替代 5 个现有 read-only 工具：** inspector / trend / diff / correlation / extras_dashboard 一行未改

输出包含 4 个核心区块：

| 区块 | 内容 |
|---|---|
| `records` | 每条 valid contract payload 一条 + outcome 标签（`correct` / `wrong` / `pending`），含 11 个 calibration-related 字段 |
| `confidence_level_summary` | high/medium/low 三桶 × `samples / correct / wrong / pending / accuracy`；分母 0 → `accuracy=null` |
| `primary_score_raw_summary` | 只对 real number 算 `count / min / max / mean`；过滤 None 与 bool（`isinstance(True, int) == True` 的 Python 陷阱已防御）|
| `data_gap_report` | `calibration_ready` bool + `contract_outcome_pairs` int + `minimum_recommended_pairs=90` + `missing_dimensions` 4 维启发式列表 |

## 4. 当前 DB 实跑结果（Step 2F-3）

### 4.1 DB 整体状态

| 指标 | 值 |
|---|---|
| `prediction_log` 总数 | 5 |
| 带 `contract_payload_json` 的 valid payload | **2** |
| `records_with_confidence_extras` | **1** |
| `outcome_log` 总数 | 3 |
| **`paired_outcomes`（valid contract × outcome）** | **0** ⚠️ |
| `pending_outcomes` | 2 |
| `invalid_payloads` | 3（全部 `missing_contract_payload`） |

### 4.2 records 列表

| pid | snapshot | has_confidence_extras | primary_score_raw | final_confidence | direction_correct |
|---|---|---|---|---|---|
| `2fe9eef2-...` | step_2e_4_full_extras_validation | **true** | **4.25** | medium | pending |
| `0e7e37a6-...` | step_2c_2_6_local_validation | **false** | null | null | pending |

- `2fe9eef2-...`（Step 2E-4 写入，Step 2C-3b 之后）→ 三段 extras 完整；`primary_score_raw=4.25` 是 unbounded raw bias-vote 累加的满负荷得分（gap_up + high_go + expanding + bullish_trend + positive_return + up_days_majority = 1.0+1.0+0.5+1.0+0.5+0.25）
- `0e7e37a6-...`（Step 2C-2.6 写入，Step 2C-3b 之前）→ 仅有 04 extras，05 段缺整个 extras 子 dict，所有 calibration-related 字段为 null
- 两条都 `direction_correct=pending`（DB 里 0 对 valid contract × outcome）

### 4.3 confidence_level_summary

```json
{ "medium": {"samples": 2, "correct": 0, "wrong": 0, "pending": 2, "accuracy": null} }
```

仅 medium 一桶（两条 valid 都是 medium），全部 pending，`accuracy=null`。

### 4.4 primary_score_raw_summary

```json
{ "count": 1, "min": 4.25, "max": 4.25, "mean": 4.25 }
```

只有一个真实数值（来自 `2fe9eef2-...`）；分布意义有限。`0e7e37a6-...` 因为 `primary_score_raw=null` 被自动过滤出 min/max/mean 计算。

### 4.5 data_gap_report

```json
{
  "calibration_ready": false,
  "contract_outcome_pairs": 0,
  "minimum_recommended_pairs": 90,
  "missing_dimensions": [
    "no paired outcomes for valid contract payloads",
    "insufficient high/medium/low coverage",
    "insufficient peer_confirm_count coverage",
    "insufficient soft_signal coverage"
  ]
}
```

**4 类启发式缺口全部触发：**
1. 0 对 valid contract × outcome
2. 仅 medium 一档（high / low 缺）
3. 唯一可分析样本 `peer_confirm_count=0`，无 distinct 值变化
4. 唯一可分析样本 `soft_signal=peer_weaken`，无 distinct 值变化

AVGO 与 ALL filter 输出完全一致（DB 中无非-AVGO prediction）。

## 5. 为什么当前不能 calibration

> 这一节是 Step 2F 系列最重要的事实记录——避免下游消费者误以为"有 extras 字段就能做 calibration"。

### 5.1 有 extras ≠ 有 outcome

`records_with_confidence_extras=1` 但 `paired_outcomes=0`。dashboard（Step 2E-2）的字段桶分布会给"有数据"的视觉错觉；calibration_inputs 工具补全这个盲区，明确说"有 extras 字段值不等于有 (输入 × outcome) pair"。

### 5.2 有 primary_score_raw ≠ 能得到 structure_score

`primary_score_raw=4.25` 是 unbounded raw bias-vote 累加（理论范围 ±0~±4.25），**不是**置信度——它是"AVGO 自身 bullish 信号强度"的累加。把它归一化进 `structure_score` 是 **calibration 决策**（tanh / clip / sigmoid / 分桶任选其一），需要：
- 真实历史样本的 score 分布（看是否需要截断尾部、归一化函数选型）
- 与 outcome 的相关性（决定阈值——score > X 对应 hit rate ≥ Y%）
- 跨 confidence_level / soft_signal / peer 计数的稳定性测试

**当前 0 个 (contract × outcome) pair，所有这些都做不了。** 强行归一只是凭直觉定参——**比保持 stub 还差**（stub 至少诚实地表达"未启用"）。

### 5.3 没有 contract × outcome pair，无法评估 hit rate

`confidence_level_summary` 全部 `pending`，`accuracy=null`。**这是诚实的"无数据"，不是"hit rate 0%"**——后者会被错误解读为"模型完全不准"。

### 5.4 三档 confidence 覆盖不足

仅 medium 一档。calibration 需要 high / medium / low 三档各至少 ~30 样本（经验阈值），才能判断"high confidence 是否真的更准"——这是任何置信度 calibration 的核心问题。

### 5.5 peer_confirm_count / soft_signal 分布不足

唯一可分析样本两个值都坍缩到一个点（`peer_confirm_count=0`，`soft_signal=peer_weaken`）。无法判断 peer 一致性或风险信号是否对 calibration 有调整作用。

### 5.6 当前 2 条 contract prediction 是 synthetic validation，不是真实回测样本

- `0e7e37a6-...`：snapshot `step_2c_2_6_local_validation`，`prediction_for_date=2099-12-31`
- `2fe9eef2-...`：snapshot `step_2e_4_full_extras_validation`，`prediction_for_date=2099-12-30`

合成日期意味着 outcome 永远不会触发；它们是工具验证用例，**不是 calibration 输入样本**。

### 5.7 不能用合成 outcome 伪造 calibration

如果手工给两条 prediction 塞 `direction_correct=1`，工具会立刻输出 `paired_outcomes=2 / accuracy=1.0`，但这个数字**没有任何意义**——它来自合成扫盘的合成 outcome，跟模型对真实市场的预测能力毫无关系。**不要做。** 这是 Step 2F 严守边界的关键之一。

## 6. 仍保持不变的字段

严格未触碰（Step 2F 全程）：

- ❌ `confidence_system.historical_score = 0.0`
- ❌ `confidence_system.structure_score = 0.0`
- ❌ `confidence_system.peer_score = 0.0`
- ❌ `confidence_system.exclusion_penalty = 0.0`
- ❌ `confidence_system.event_score = None`
- ❌ `confidence_engine.py` 整仓库零 import（25-31 行的 v1 stub，入参 `top1_margin / is_tail` 在 `predict_result` 里完全没有，接 = 给 stub 喂 stub）
- ❌ **`primary_score_raw` 仍只是 raw bias-vote，不是 calibrated score**——工具只 dump min/max/mean，不做任何 transform

## 7. 下一步建议

> **强烈建议：不要马上实现 calibration 函数；不要马上补合成 outcome。**

### 7.1 候选下一步（互不冲突，按优先级排序）

| 候选 step | 范围 | 风险 | 优先级 |
|---|---|---|---|
| **Step 2G** —— exclusion soft/hard 规则设计文档 | 写一份"在什么条件下 `exclusion_level` 应当升 `soft`/`hard`"的设计文档，引用 2C-1 诊断里的 `big_up_contradiction_card` / `exclusion_reliability_review` 等已有信号 + 数据缺口。**纯设计，不动代码** | 低 | 高（与 calibration 数据状态无关，可立即启动） |
| **Step 2F-4** —— 真实历史回放 / outcome pair 数据生成方案设计 | 写一份"如何积累真实 (contract × outcome) pair"的方案文档：数据源（哪个交易日范围）/ 触发路径（必须走 `run_predict` 真路径）/ outcome capture 触发条件 / 数据卫生（不能合成 `2099-xx-xx`）/ 估算所需时间。**纯方案，不实现** | 低 | 中（为 Step 3 真 calibration 铺路） |
| **DB hygiene cleanup** | 清理主项目 DB 里两条 `prediction_for_date=2099-xx-xx` 的合成 validation 记录（`0e7e37a6-...` / `2fe9eef2-...`）+ 备份文件 `avgo_agent.db.backup_step_2c_2_6`。**单独确认任务**——这是数据卫生问题，不是工程问题，需要明确决定是否处理 | 极低 | 中（合成数据长期混在真实数据里会污染未来 Step 2F-4 / Step 3 的诊断输出） |
| **Step 3** —— 真 calibration 接入 | 用真实 (contract × outcome) pair 实现归一化函数：`structure_score = f(primary_score_raw)`、`peer_score = g(confirm/oppose)` 等；让 4 个 0.0 score 字段升真值；可能接 `confidence_engine.py` 或重写 | 高 | **低（必须等数据足量，不能在 0 pair / 90 推荐 之下启动）** |

### 7.2 严守边界（与 Step 2 全程一致 + Step 2F 数据特殊约束）

- ❌ **不实现 calibration 函数** —— Step 2F 是诊断 / 工具，不是落地
- ❌ **不让 4 个 0.0 score 字段（`historical_score / structure_score / peer_score / exclusion_penalty`）升真值**
- ❌ **不让 `event_score` 从 None 升真值**
- ❌ **不补合成 outcome 来"激活"calibration_inputs 工具的非 pending 路径**——会造成下游误读
- ❌ 不接 `confidence_engine.py`（入参不可得）
- ❌ 不接 `risk_model.py` / `contradiction_engine.py`
- ❌ 不接 `big_up_contradiction_card` / `exclusion_reliability_review` / `big_down_tail_warning` / `anti_false_exclusion_audit`
- ❌ 不接 longbridge / broker / paper_trade / 真实交易 / 模拟盘 API
- ❌ 不改 `predict.py` / `run_predict` / 4 个 builder / adapter / contract validator / UI / `prediction_store` / DB schema

### 7.3 真 calibration 启动的最小前提（Step 3 立项条件）

- (contract × outcome) pair 数 ≥ **90**（_MIN_RECOMMENDED_PAIRS）
- 三档 confidence（high / medium / low）各至少有几十个 paired sample
- `peer_confirm_count` / `soft_signal` 至少 2 个 distinct 值（不能全坍缩到一点）
- 来源是真实回测 / 真实运行积累，**不是合成数据**
- `data_gap_report.calibration_ready` 自动变 `true`，且 `missing_dimensions` 为空 / 仅剩与可接受性相关的非阻塞项

## 8. 没有改的东西

严格未触碰（Step 2F 全程）：

- ❌ `predict.py` 任何决策逻辑
- ❌ `run_predict` 主入口（签名 / 子步骤调用顺序 / unavailable 分支触发条件全部不变）
- ❌ 4 个 builder（`build_primary_projection` / `apply_peer_adjustment` / `build_final_projection` / `_apply_research_adjustment`）
- ❌ `services/projection_output_adapter.py`（adapter）
- ❌ `services/projection_output_contract.py`（validator）
- ❌ `services/prediction_store.py`（save 旁路 + DB schema）
- ❌ **现有 5 个 read-only 工具：** `contract_payload_inspector` / `contract_payload_trend` / `contract_payload_diff` / `contract_outcome_correlation` / `contract_payload_extras_dashboard` 一行未改；`DIFF_PATHS` / `GROUP_PATHS` / `DISTRIBUTION_PATHS` 也未动
- ❌ DB schema（不调用 `init_db`，不 `ALTER`）
- ❌ `risk_model.py` / `contradiction_engine.py` / `confidence_engine.py` 三个 v1 stub（整仓库零 import 状态保持）
- ❌ `big_up_contradiction_card` / `exclusion_reliability_review` / `big_down_tail_warning` / `anti_false_exclusion_audit` 四个 UI / 离线模块
- ❌ UI（`ui/predict_tab.py` 等）
- ❌ scanner / matcher / 数据层
- ❌ **longbridge / broker / paper_trade / 真实交易 / 模拟盘 API**
- ❌ 长桥 / 新闻 / 财报数据接入
- ❌ stash / `.claude/worktrees/` / `logs/prediction_log.jsonl`
- ❌ **没在 git 跟踪范围内产生任何改动：** Step 2F-3 在主项目 DB 跑了两次 `SELECT`，没有 INSERT/UPDATE，`avgo_agent.db` 不在跟踪范围

## 9. Step 2 系列总览（截至本 checkpoint，更新版）

| 阶段 | 范围 | 进 main commit |
|---|---|---|
| **Step 2A** | run_predict 两步结构核验（只读诊断） | —（无代码） |
| **Step 2B-1** | contract alignment 安全网 + data_window drift 暴露 | `2ac41dd` |
| **Step 2B-2** | primary_projection 自发布 02 段 + data_window_days 联动 | `0fccc72` |
| **Step 2B-3** | peer_adjustment 自发布 03 段 | `9aca3f2` |
| **Step 2B-4** | final_projection 自发布 06 段 | `c2d1d34` |
| **Step 2B Summary** | 字段化 checkpoint | `9ae30de` |
| **Step 2C-1** | exclusion_system 只读诊断 | —（无代码） |
| **Step 2C-2** | exclusion_system.extras 暴露 raw risk signals | `8f689a2` |
| **Step 2C-2.5 / 2C-2.6** | DB contract_payload_json 落库验证 | —（无代码） |
| **Step 2C-3a** | confidence_system 只读诊断 | —（无代码） |
| **Step 2C-3b** | confidence_system.extras 暴露 raw score-like signals | `c188725` |
| **Step 2C Summary** | exclusion / confidence extras checkpoint | `1f9f8fa` |
| **Step 2D-1** | simulated_trade 只读诊断 | —（无代码） |
| **Step 2D-2** | simulated_trade.extras 暴露 trade-relevant signals | `f125d45` |
| **Step 2D Summary** | simulated_trade extras checkpoint | `4468f73` |
| **Step 2E-1** | dashboard 只读诊断 | —（无代码） |
| **Step 2E-2** | Contract Extras Dashboard 三件套 | `524552b` |
| **Step 2E-3 / 2E-4** | 主项目 DB 实跑 + 写新 prediction 验证 04/05/07 落库 | —（无代码） |
| **Step 2E Summary** | dashboard checkpoint | `ddb10e1` |
| **Step 2F-1** | confidence calibration 只读诊断 | —（无代码） |
| **Step 2F-2** | calibration_inputs 三件套（service / CLI / tests） | `7500b5b` |
| **Step 2F-3** | 主项目 DB 实跑验证 calibration_ready=false | —（无代码） |
| **Step 2F Summary** | 本文件 | (pending commit) |

**测试基线累积：** Step 2 起点 1883 → 2094（+211）；0 failed；10 skipped 全程不变。

**核心不变量：** `predict.py` / `run_predict` / 4 个 builder / contract validator / UI / `prediction_store` / DB schema / 5 个现有 read-only 工具（inspector / trend / diff / correlation / dashboard）/ `DIFF_PATHS` / `GROUP_PATHS` / `DISTRIBUTION_PATHS` / 三个 v1 stub trio / 4 个离线 / UI 模块 / 任何 trading API 在 Step 2 全程一行未改 / 一行未引入。**4 个 score 字段（`historical_score / structure_score / peer_score / exclusion_penalty`）全程 0.0；`event_score` 全程 None。**
