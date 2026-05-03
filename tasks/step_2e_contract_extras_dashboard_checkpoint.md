# Step 2E — Contract Extras Dashboard Checkpoint

> 状态：Step 2E-1 ~ 2E-4 已全部完成。Step 2E-2 是唯一产生 commit 的子步（`524552b`）；2E-1 / 2E-3 / 2E-4 是只读诊断 / 实跑验证，不产生代码改动。本文件是进入 Step 2F（confidence calibration 只读诊断）之前的 handoff 快照。
> 只写文档，不改任何业务代码。

## 1. 当前完成状态

| 子步 | 主题 | commit | 关键产出 |
|---|---|---|---|
| 2E-1 | 只读诊断现有 4 个工具是否覆盖 04 / 05 / 07 extras | —（无代码改动） | 报告：4 个工具的 `DIFF_PATHS` / `GROUP_PATHS` 都是 2-tuple `(section, field)` 路径，**无法**深入 `extras.*` 三层嵌套；inspector 摘要也不暴露 extras。新工具的输出形状 + 字段集 + MISSING 桶语义就此设计 |
| 2E-2 | 新增 dashboard service / CLI / tests | `524552b feat(contract): add read-only contract extras dashboard tool` | 新增 3 文件 + §16 文档；30 case + 14 个 `DISTRIBUTION_PATHS` 字段；测试基线 2033 → 2063（+30） |
| 2E-3 | 主项目 DB 实跑验证 Step 2C-2.6 旧 prediction（仅 04 extras） | —（无代码改动；只读 sqlite） | dashboard 正确把 05 / 07 段缺失识别为 `MISSING` 桶；端到端验证"contract validity ≠ extras 完整性"的设计意图 |
| 2E-4 | 写入新 Step 2E-4 prediction，验证 04 / 05 / 07 extras 全量落库 | —（无代码改动；本地 DB 写一条合成 prediction） | 通过 `run_predict → save_prediction` 真路径生成 `2fe9eef2-...`；dashboard 显示三段 extras 完整 + 旧 prediction 仍以 MISSING 桶可见 |

## 2. 当前 main 状态

- **main 最新 commit：** `524552b feat(contract): add read-only contract extras dashboard tool`
- **测试基线：** **2063 passed / 0 failed / 10 skipped / 65 subtests**（从 Step 2D 末尾的 2033 累积 +30）
- **新增文件（Step 2E-2，已进 main）：**
  - [`services/contract_payload_extras_dashboard.py`](../services/contract_payload_extras_dashboard.py) — service：`summarize_contract_extras_dashboard()` + `DISTRIBUTION_PATHS` 14 字段
  - [`scripts/dashboard_contract_extras.py`](../scripts/dashboard_contract_extras.py) — CLI wrapper（`--db / --limit / --symbol`）
  - [`tests/test_contract_payload_extras_dashboard.py`](../tests/test_contract_payload_extras_dashboard.py) — 30 case，10 测试组

## 3. dashboard 工具能力

```python
def summarize_contract_extras_dashboard(
    db_path: str | Path | None = None,
    limit: int = 20,
    symbol: str | None = "AVGO",
) -> dict[str, Any]: ...
```

- **CLI：** `python3 scripts/dashboard_contract_extras.py [--db PATH] [--limit N] [--symbol AVGO|ALL|<TICKER>]`，stdout JSON 输出（`ensure_ascii=False, indent=2`）
- **完全只读：** 仅 `SELECT`，不调用 `init_db`，不 `INSERT` / `UPDATE`
- **三级回退状态：** `ok` / `no_records` / `no_valid_payloads` / `error`
- **复用现有 4 工具的 helper 模式（独立重写，不跨工具 import）：** `_resolve_db_path` / `_resolve_limit` / `_resolve_symbol` 与 `contract_outcome_correlation` 完全同口径
- **不替代 4 个现有 read-only 工具：** inspector / trend / diff / correlation 的 `DIFF_PATHS` / `GROUP_PATHS` 一行未改；它们仍负责 2-tuple 顶层字段维度，dashboard 专门负责三层 `extras.*` 维度
- **不改 schema、不改 contract validator、不改 adapter、不改 builder、不改 `predict.py` / `run_predict` / UI / `prediction_store`**

## 4. dashboard 展示内容

### 4.1 `latest_snapshot`（最新 valid payload 的决策摘要 + 三段 extras）

| 字段 | 来源 |
|---|---|
| `prediction_id` / `prediction_for_date` | `prediction_log` row |
| `final_direction` / `probability_bucket` | `payload["final_projection"]` |
| `confidence_level` | `payload["confidence_system"]` |
| `trade_action` | `payload["simulated_trade"]` |
| `exclusion_system_extras` | `payload["exclusion_system"]["extras"]`（缺则 `null`） |
| `confidence_system_extras` | `payload["confidence_system"]["extras"]`（缺则 `null`） |
| `simulated_trade_extras` | `payload["simulated_trade"]["extras"]`（缺则 `null`） |

最新 = `created_at DESC, rowid DESC` 排序后第一条 **valid** payload；invalid 自动跳过（`tests/test_contract_payload_extras_dashboard.py::test_latest_snapshot_skips_invalid_to_pick_next` 锁住）。

### 4.2 `extras_distributions`（14 字段桶分布）

| Section | 字段 |
|---|---|
| 04 `exclusion_system.extras` | `soft_signal` / `path_risk_level` / `peer_path_risk_direction` / `conflicting_factors_count` |
| 05 `confidence_system.extras` | `primary_confidence_raw` / `peer_adjusted_confidence` / `final_confidence` / `probability_bucket` / `path_risk_level` / `soft_signal` |
| 07 `simulated_trade.extras` | `trade_engine_enabled` / `has_key_price_levels` / `final_direction` / `soft_signal` |

每字段产出 `dict[bucket_key, count]`；bucket key 规则见 §5。

**故意不统计：** `extras.conflicting_factors`（list 桶爆）/ `extras.peer_path_risk_reasons`（同上）/ `extras.primary_score_raw`（连续 float，分布无意义；放 `latest_snapshot` 即可）/ `extras.total_confidence`（同上）/ `extras.peer_confirm_count` / `peer_oppose_count`（int 但小空间，留给 Step 2F）。

## 5. MISSING 桶语义

`_bucket_key()` 三步规则：
- `None` → `"NULL"`
- `True` → `"True"` / `False` → `"False"`（bool 优先 int 检查）
- 其他 → `str(value)`

**MISSING 桶**由 `_accumulate_distribution` 在两种情况下注入（不在 `_bucket_key` 内）：
1. `payload[section]` 不是 dict 或缺整段 `extras`（**老 payload，Step 2C-2 之前的预测**）
2. `payload[section]["extras"]` 是 dict 但缺该字段

**老 payload 缺 extras 不算 invalid**——payload 仍 contract-valid，进入 `valid_payloads` 计数，但分布里显式标 `MISSING`。这与 `skipped_records` 严格区分：

| skipped_records reason | 含义 |
|---|---|
| `missing_contract_payload` | `contract_payload_json` 列为 NULL 或空（Step 1E migration 之前写入） |
| `invalid_json` | JSON parse 失败 |
| `validation_failed` | `validate_projection_output(payload)` 返回非空错误列表 |

**MISSING 桶在 Step 2E-3 / 2E-4 实跑中得到端到端验证。** 主项目 DB 同时存在：
- Step 2C-2.6 旧 prediction（`0e7e37a6-...`）：只有 04 段 extras，05 / 07 段缺 extras 子 dict
- Step 2E-4 新 prediction（`2fe9eef2-...`）：04 / 05 / 07 三段 extras 完整

dashboard 正确把两者混合呈现，让用户能看到字段化的版本演进，而**不是**把老记录错误地丢弃或污染分布。

## 6. 实跑验证结果

### 6.1 新 prediction（Step 2E-4 写入）

- **prediction_id：** `2fe9eef2-dd44-4196-bf66-141b8c2cd8f6`
- **prediction_for_date：** `2099-12-30`（**本地验证标记**，与 Step 2C-2.6 的 `2099-12-31` 区分）
- **snapshot_id：** `step_2e_4_full_extras_validation`
- **写入路径：** 通过现有 `run_predict(scan, research_result=None) → save_prediction(...)` 真路径，未手工传 `contract_payload`，未手工 `INSERT/UPDATE`

### 6.2 三段 extras 真实落库（latest_snapshot 摘要）

**04 `exclusion_system_extras`**：
- `soft_signal = "peer_weaken"`（三 peer 全 weaker → confirm_count=0 / oppose_count=3 → conflicting_factors 含 `"peer_confirmation=weaken"`）
- `path_risk_level = "medium"`
- `peer_path_risk_direction = "higher"`
- `peer_path_risk_reasons = ["3 peers oppose primary direction"]`
- `conflicting_factors_count = 2`

**05 `confidence_system_extras`**：
- `primary_score_raw = 4.25`（**unbounded raw bias-vote 累加**：gap_up + high_go + expanding + bullish_trend + positive_return + up_days_majority = 1.0+1.0+0.5+1.0+0.5+0.25 = 4.25）
- `primary_confidence_raw = "high"`
- `peer_confirm_count = 0` / `peer_oppose_count = 3`
- `peer_adjusted_confidence = "medium"`
- `final_confidence = "medium"`
- `probability_bucket = "55–70%"`
- `path_risk_level = "medium"`
- `soft_signal = "peer_weaken"`

**07 `simulated_trade_extras`**（required 字段保 pinned，extras 9 键全到位）：
- `final_direction = "偏多"`
- `final_five_state = "小涨"`
- `probability_bucket = "55–70%"`
- `confidence_level = "medium"`
- `total_confidence = 0.5`
- `path_risk_level = "medium"`
- `soft_signal = "peer_weaken"`
- `has_key_price_levels = false`（**Step 2D-1 诊断预测准确**：`key_price_levels` 全链路硬编码 `{}`）
- `trade_engine_enabled = false`（设计常量）

### 6.3 三段 soft_signal 同口径独立派生验证

四处的 `soft_signal` 全部一致 = `"peer_weaken"`：
- `predict_result.conflicting_factors` 含 `"peer_confirmation=weaken"`（peer 层产出）
- `latest_snapshot.exclusion_system_extras.soft_signal == "peer_weaken"`（adapter 04 段独立派生）
- `latest_snapshot.confidence_system_extras.soft_signal == "peer_weaken"`（adapter 05 段独立派生）
- `latest_snapshot.simulated_trade_extras.soft_signal == "peer_weaken"`（adapter 07 段独立派生）

证明 §12 / §13 / §14 严守边界承诺的"三段独立重派生，不跨段读 sibling extras"在真实数据上是等价输出——下游消费者可以信任三段口径一致。

### 6.4 AVGO 与 ALL filter 对比

输出完全一致——主项目 DB 里没有非-AVGO 预测，`symbol_filter` 标签从 `"AVGO"` 变 `"ALL"`，但扫描结果 / `latest_snapshot` / `extras_distributions` 都相同（5 records，2 valid，新 prediction `2fe9eef2-...` 仍是最新）。

### 6.5 `extras_distributions` 混合分布

完美呈现版本演进史（每字段都有 valid 真值 + 老 prediction 的 `MISSING`）：

| 字段 | 分布 | 解读 |
|---|---|---|
| `exclusion_system.extras.soft_signal` | `{"peer_weaken": 2}` | 两条 valid 都触发 peer_weaken |
| `confidence_system.extras.final_confidence` | `{"medium": 1, "MISSING": 1}` | 1 条新 + 1 条 Step 2C-3b 之前 |
| `confidence_system.extras.primary_confidence_raw` | `{"high": 1, "MISSING": 1}` | 同上 |
| `simulated_trade.extras.trade_engine_enabled` | `{"False": 1, "MISSING": 1}` | 1 条新（Step 2D-2 之后）+ 1 条旧 |
| `simulated_trade.extras.has_key_price_levels` | `{"False": 1, "MISSING": 1}` | 同上 |

## 7. 没有改的东西

严格未触碰（Step 2E 全程）：

- ❌ `predict.py` 任何决策逻辑
- ❌ `run_predict` 主入口（签名 / 子步骤调用顺序 / unavailable 分支触发条件全部不变）
- ❌ 4 个 builder（`build_primary_projection` / `apply_peer_adjustment` / `build_final_projection` / `_apply_research_adjustment`）
- ❌ `services/projection_output_adapter.py`（adapter）
- ❌ `services/projection_output_contract.py`（validator）
- ❌ `services/prediction_store.py`（save 旁路 + DB schema）
- ❌ **现有 4 个 read-only 工具：** `contract_payload_inspector` / `contract_payload_trend` / `contract_payload_diff` / `contract_outcome_correlation` 一行未改；`DIFF_PATHS` / `GROUP_PATHS` 也未改
- ❌ DB schema（Step 2C-2.6 已通过 `init_db()` ALTER 加 `contract_payload_json` 列；本轮不动）
- ❌ `risk_model.py` / `contradiction_engine.py` / `confidence_engine.py` 三个 v1 stub
- ❌ `big_up_contradiction_card` / `exclusion_reliability_review` / `big_down_tail_warning` / `anti_false_exclusion_audit` 四个 UI / 离线模块
- ❌ UI（`ui/predict_tab.py` 等）
- ❌ scanner / matcher / 数据层
- ❌ **longbridge / broker / paper_trade / 真实交易 / 模拟盘 API**
- ❌ 长桥 / 新闻 / 财报数据接入
- ❌ stash / `.claude/worktrees/` / `logs/prediction_log.jsonl`
- ❌ **没 commit / 没 push 实跑验证产生的数据：** Step 2E-3 / 2E-4 在主项目 DB 里写了 1 条新 prediction（`2fe9eef2-...`），但 `avgo_agent.db` 不在 git 跟踪范围；备份文件 `avgo_agent.db.backup_step_2c_2_6` 也仅 untracked

## 8. 下一步 Step 2F 建议

> **强烈建议：只读诊断，不实施 calibration。**

### 8.1 Step 2F 推荐范围

- **入口：** 读已落库 `contract_payload_json`（主项目 DB 现已有 2 条 valid prediction，Step 2F 启动时可继续按 2C-2.6 / 2E-4 模式扩充样本），分析这些字段与 outcome 的相关性：
  - `confidence_system.extras.primary_score_raw`（**连续 float**，dashboard 故意不展开；Step 2F 的核心研究对象）
  - `confidence_system.extras.peer_confirm_count` / `peer_oppose_count`（int 0–3）
  - `confidence_system.confidence_level`（high / medium / low，三档）
  - `confidence_system.total_confidence`（0.25 / 0.50 / 0.75，三档）
  - `outcome_log.direction_correct`（来自 outcome capture）
- **产出：** 一份诊断 markdown，描述：
  - `primary_score_raw` 在历史 prediction_log 上的实际分布（直方图、min/max/mean）
  - 与 outcome 的相关性（`primary_score_raw` 越高，hit rate 是否越高？）
  - `confidence_level` 三档与 outcome 的命中率分布
  - 归一化函数候选（tanh / clip / 分桶 / sigmoid）的可行性
  - 阈值建议（如 `score > 2.0` 是否对应 `confidence_level == "high"` 在历史上是 hit rate ≥ 70%）

### 8.2 严守边界（Step 2F 全程）

- ❌ **不实现 calibration 函数**——Step 2F 是诊断，不是落地
- ❌ **不让 4 个 0.0 score 字段（`historical_score / structure_score / peer_score / exclusion_penalty`）升真值**——这是 Step 2 后续阶段的事
- ❌ **不让 `event_score` 从 None 升真值**
- ❌ 不接 `confidence_engine.py` v1 stub（31 行单纯函数；入参 `top1_margin / is_tail` 在 `predict_result` 里完全没有，接 = 给 stub 喂 stub）
- ❌ 不接 `risk_model.py` / `contradiction_engine.py`
- ❌ 不接 `big_up_contradiction_card` / `exclusion_reliability_review` / `big_down_tail_warning` / `anti_false_exclusion_audit`
- ❌ 不接 longbridge / broker / paper_trade / 真实交易 / 模拟盘 API
- ❌ 不改 `predict.py` / `run_predict` / 4 个 builder / adapter / contract validator / UI / `prediction_store`

### 8.3 数据基础设施已就绪

Step 2E-2 / 2E-4 验证后，Step 2F 直接可用的 query 路径：

```bash
# 看分布（dashboard 已统计的字段）
python3 scripts/dashboard_contract_extras.py --limit 100 --symbol AVGO

# 看连续值（dashboard 故意不展开的，需要直读 sqlite）
sqlite3 avgo_agent.db
> SELECT contract_payload_json FROM prediction_log
   WHERE contract_payload_json IS NOT NULL
   ORDER BY created_at DESC LIMIT 100;
# Python: json.loads(...) 提取 confidence_system.extras.primary_score_raw

# correlation 工具看老分桶维度（已有，Step 1J 字段）
python3 scripts/correlate_contract_outcomes.py --symbol AVGO --limit 100
```

Step 2F 可能需要一个**新的诊断脚本**（仿 dashboard 模式但聚焦"连续 float ↔ outcome"维度），或者直接 ad-hoc Python 分析；具体由 Step 2F-1 诊断步骤决定。

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
| **Step 2C-2.5 / 2C-2.6** | DB contract_payload_json 落库验证 | —（无代码；本地 DB 写一条） |
| **Step 2C-3a** | confidence_system 只读诊断 | —（无代码） |
| **Step 2C-3b** | confidence_system.extras 暴露 raw score-like signals | `c188725` |
| **Step 2C Summary** | exclusion / confidence extras checkpoint | `1f9f8fa` |
| **Step 2D-1** | simulated_trade 只读诊断 | —（无代码） |
| **Step 2D-2** | simulated_trade.extras 暴露 trade-relevant signals | `f125d45` |
| **Step 2D Summary** | simulated_trade extras checkpoint | `4468f73` |
| **Step 2E-1** | dashboard 只读诊断 | —（无代码） |
| **Step 2E-2** | Contract Extras Dashboard 三件套（service / CLI / tests） | `524552b` |
| **Step 2E-3 / 2E-4** | 主项目 DB 实跑验证 + 写新 prediction 验证 04/05/07 落库 | —（无代码；本地 DB 写一条） |
| **Step 2E Summary** | 本文件 | (pending commit) |

**测试基线累积：** Step 2 起点 1883 → 2063（+180）；0 failed；10 skipped 全程不变。

**核心不变量：** `predict.py` / `run_predict` / 4 个 builder / contract validator / UI / `prediction_store` / DB schema / 4 个现有 read-only 工具（inspector / trend / diff / correlation）/ `DIFF_PATHS` / `GROUP_PATHS` / 三个 v1 stub trio / 4 个离线 / UI 模块 / 任何 trading API 在 Step 2 全程一行未改 / 一行未引入。
