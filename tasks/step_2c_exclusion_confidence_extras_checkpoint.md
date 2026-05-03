# Step 2C — Exclusion / Confidence Extras Checkpoint

> 状态：Step 2C-1 ~ 2C-3b 已全部进 main。本文件是进入 Step 2D 之前的 handoff 快照。
> 只写文档，不改任何业务代码。

## 1. 当前完成状态

| 子步 | 主题 | commit | 关键产出 |
|---|---|---|---|
| 2C-1 | 只读诊断 04 `exclusion_system` 来源 | —（无代码改动） | 报告 adapter 04 段全 stub、`predict_result` 已有 `conflicting_factors / path_risk / peer_path_risk_adjustment` 风险信号、v1 stub 三件套（`risk_model.py` / `contradiction_engine.py` / `confidence_engine.py`）整仓库零 import、`big_up_contradiction_card` / `exclusion_reliability_review` / `big_down_tail_warning` / `anti_false_exclusion_audit` 是 UI 或离线产物 |
| 2C-2 | 04 `exclusion_system.extras` 暴露 raw risk signals | `8f689a2 feat(contract): expose risk signals via exclusion_system extras` | 5 个 contract required 字段保持 stub；新增 `extras` 6 键（`conflicting_factors_count / conflicting_factors / path_risk_level / peer_path_risk_direction / peer_path_risk_reasons / soft_signal`）；`tests/test_exclusion_system_contract_fields.py` 18 case + 3 subtests |
| 2C-2.5 | 实跑 contract CLI 工具验证（只读，不改代码） | —（无代码改动） | 报告主项目 DB 旧 schema、worktree DB 空，`extras` 在合成 round-trip 中通过；trend / correlate 不覆盖 `extras.*`（与 Step 1J/1I 设计一致） |
| 2C-2.6 | 主项目 DB `contract_payload_json` 落库验证 | —（无代码改动；备份 + migration + 一条本地 prediction） | 触发 `init_db()` ALTER 加列；通过 `run_predict → save_prediction` 真路径写入 `prediction_id=0e7e37a6-...`；`inspect / trend / correlate` 三工具全部 status=ok 看到新记录；从 sqlite `json.loads(contract_payload_json)` 读出完整 `exclusion_system.extras`，`soft_signal == "peer_weaken"` |
| 2C-3a | 只读诊断 05 `confidence_system` 来源 | —（无代码改动） | 报告 4 score 字段 + event_score 全 stub，3 真值字段（`confidence_level / total_confidence / confidence_reason`）已映射；`primary_projection.score` 是 unbounded raw bias-vote（≈ ±4.25），归一化属 calibration 决策；`confidence_engine.py` 31 行单纯函数，整仓库零 import |
| 2C-3b | 05 `confidence_system.extras` 暴露 raw score-like signals | `c188725 feat(contract): expose score signals via confidence_system extras` | 4 score 字段保持 0.0 / event_score 保持 None / 3 真值字段保持原映射；新增 `extras` 10 键；`tests/test_confidence_system_contract_fields.py` 33 case + 14 subtests |

## 2. 当前 main 状态

- **main 最新 commit：** `c188725 feat(contract): expose score signals via confidence_system extras`
- **测试基线：** **2003 passed / 0 failed / 10 skipped / 43 subtests**（从 Step 2B 末尾的 1950 累积 +53：1969 → 2003）
- **新增 / 更新的测试文件：**
  - `tests/test_exclusion_system_contract_fields.py`（2C-2 新增）
  - `tests/test_confidence_system_contract_fields.py`（2C-3b 新增）
  - `tests/test_projection_output_adapter.py`（2C-2 / 2C-3b 各新增 1 case，挂在 `ExclusionAndConfidenceMappingTests` 下）

## 3. 04 `exclusion_system` 当前状态

### 3.1 contract required 字段（全部 stub，永不动）

| 字段 | 当前值 | 类型 |
|---|---|---|
| `exclusion_level` | `"none"` | enum 必须 ∈ {none, soft, hard} |
| `exclusion_sources` | `[]` | list |
| `exclusion_reasons` | `[]` | list |
| `forced_exclusion` | `False` | bool |
| `anti_false_exclusion_triggered` | `False` | bool |

下游消费者按"没有否定"理解永远正确——本轮没有任何路径会让 required 字段动起来。

### 3.2 `extras` 字段（Step 2C-2 新增）

| extras 键 | 来源 | 类型防御 |
|---|---|---|
| `conflicting_factors_count` | `len(predict["conflicting_factors"])` | 非 list → 0 |
| `conflicting_factors` | `predict["conflicting_factors"]` 副本 | 非 list → `[]` |
| `path_risk_level` | `predict["path_risk"]` | 缺失 → `"unknown"` |
| `peer_path_risk_direction` | `predict["peer_path_risk_adjustment"]["risk_direction"]` | 非 dict / 缺失 → `"unknown"` |
| `peer_path_risk_reasons` | `predict["peer_path_risk_adjustment"]["reasons"]` 副本 | 非 list → `[]` |
| `soft_signal` | 启发式：`"peer_weaken"` / `"high_path_risk"` / `"none"` | 仅观察、永不反向影响 required |

`soft_signal` 决策树：
- `"peer_confirmation=weaken" in conflicting_factors` → `"peer_weaken"`
- 否则 `path_risk_level == "high"` → `"high_path_risk"`
- 否则 → `"none"`

### 3.3 严守边界（Step 2C-2 没做的事）

- ❌ `extras` 只是观察 metadata，下游不应据 `soft_signal` 做"是否预测"判断
- ❌ `soft_signal` 永不反向修改 `exclusion_level`
- ❌ 没有 `forced_exclusion=True` 的真实触发条件
- ❌ 没接 `big_up_contradiction_card` / `exclusion_reliability_review` / `big_down_tail_warning` / `anti_false_exclusion_audit` 这四个离线 / UI 模块到主链

## 4. 05 `confidence_system` 当前状态

### 4.1 contract required 字段（混合：3 真值 + 4 score stub + 1 None stub）

| 字段 | 当前值 / 来源 | 类别 |
|---|---|---|
| `confidence_level` | `_normalize_confidence(predict["final_confidence"])` | **真值映射** |
| `total_confidence` | `_CONFIDENCE_TO_TOTAL[level]`（high→0.75 / medium→0.50 / low→0.25） | **真值映射** |
| `confidence_reason` | `predict["prediction_summary"]` | **真值映射** |
| `historical_score` | `0.0` | stub（永不动） |
| `structure_score` | `0.0` | stub（永不动） |
| `peer_score` | `0.0` | stub（永不动） |
| `exclusion_penalty` | `0.0` | stub（永不动） |
| `event_score` | `None` | stub（永不动） |

### 4.2 `extras` 字段（Step 2C-3b 新增）

| extras 键 | 来源 | 类型防御 |
|---|---|---|
| `primary_score_raw` | `predict["primary_projection"]["score"]`（**未归一化** raw bias-vote） | 不可转 float → `None` |
| `primary_confidence_raw` | `primary.primary_confidence_raw` 优先，回退 `primary.final_confidence` | 非合法枚举 → `"unknown"` |
| `peer_confirm_count` | `peer_adjustment.confirm_count`（0–3） | 缺失或不可转 → 0 |
| `peer_oppose_count` | `peer_adjustment.oppose_count`（0–3） | 同上 |
| `peer_adjusted_confidence` | `peer_adjustment.adjusted_confidence` | 非合法 → `"unknown"` |
| `final_confidence` | `predict["final_confidence"]` | 非合法 → `"unknown"`（**与 required `confidence_level` 不同：required coerce 成 `"low"`，extras 保留 `"unknown"` 让原始问题可见**） |
| `probability_bucket` | `predict["final_projection"]["probability_bucket"]` | 非合法 → `"unknown"` |
| `conflicting_factors_count` | `len(predict["conflicting_factors"])` | 非 list → 0 |
| `path_risk_level` | `predict["path_risk"]` | 非 low/medium/high → `"unknown"` |
| `soft_signal` | 与 04 段同决策树**独立重派生** | 不读 sibling section's extras |

### 4.3 严守边界（Step 2C-3b 没做的事）

- ❌ `primary_score_raw` 未归一化，**绝对不能直接当 `structure_score`**——归一是 calibration 决策（tanh / clip / backtest 定标），不是字段填充
- ❌ `peer_confirm_count` / `peer_oppose_count` 不能直接当 `peer_score`——语义不清（0 票是"无数据"还是"完美中性"？需要 calibration 层定义）
- ❌ `event_score` 不会从 `research_result.catalyst_detected` 这种 bool 派生（bool ≠ score）
- ❌ `confidence_engine.py` v1 stub 仍未接入（31 行单纯函数；入参 `top1_margin / is_tail` 在 `predict_result` 里完全没有，接 = 给 stub 喂 stub）
- ❌ `risk_model.py` / `contradiction_engine.py` 也未接入

## 5. DB 落库验证（Step 2C-2.6 结果）

| 项 | 状态 |
|---|---|
| 主项目 DB 备份 | ✅ `/Users/may/Desktop/stock-analyzer-main/avgo_agent.db.backup_step_2c_2_6`（main 项目 untracked，**未入 git**） |
| Schema migration | ✅ 通过 `python -c "from services.prediction_store import init_db; init_db()"` 触发 ALTER；末尾增加 `, contract_payload_json TEXT` |
| 本地 prediction 写入 | ✅ `prediction_id=0e7e37a6-1607-48d6-8f80-e8bfca561a86`（`prediction_for_date=2099-12-31`、`snapshot_id="step_2c_2_6_local_validation"`，明确标记为本地验证记录） |
| 写入路径 | ✅ 通过 `run_predict(...) → save_prediction(...)` 真路径，未手工传 `contract_payload`，未手工 `INSERT/UPDATE` |
| `inspect` 工具 | ✅ status=ok，sections_present 列出 8 段 |
| `trend` / `correlate` 工具 | ✅ 自动跳过 3 条旧 prediction（`missing_contract_payload`），新记录进入分布统计 |
| `extras` sqlite 读出 | ✅ `json.loads(contract_payload_json)["exclusion_system"]["extras"]["soft_signal"] == "peer_weaken"` |
| 备份 / DB 文件入 git | ❌ 都未入（`avgo_agent.db` 不在仓库跟踪范围；备份文件 untracked 但不 add） |

**意义：** Step 2C-2 的 `extras` 不是只在测试里通过，而是**端到端经过 sqlite 持久化**仍能被任意只读消费者直接 `json.loads(...)` 取用。

## 6. 没有改的东西

严格未触碰（Step 2C 全程）：

- ❌ `predict.py` 任何决策逻辑
- ❌ `run_predict` 主入口（签名 / 子步骤调用顺序 / unavailable 分支触发条件全部不变）
- ❌ 4 个 builder（`build_primary_projection` / `apply_peer_adjustment` / `build_final_projection` / `_apply_research_adjustment`）
- ❌ `services/projection_output_contract.py`（validator）
- ❌ `services/prediction_store.py`（save 旁路）—— 注：Step 2C-2.6 触发了一次 `init_db()` 的 ALTER，但是**走现有 migration 代码**，**未改 schema 文件**
- ❌ Step 1 read-only 工具：`contract_payload_inspector` / `contract_payload_diff` / `contract_payload_trend` / `contract_outcome_correlation`（内部 `DIFF_PATHS` / `GROUP_PATHS` 故意不覆盖 `extras.*`）
- ❌ `risk_model.py` / `contradiction_engine.py` / `confidence_engine.py` 三个 v1 stub
- ❌ `big_up_contradiction_card` / `exclusion_reliability_review` / `big_down_tail_warning` / `anti_false_exclusion_audit` 四个 UI / 离线模块
- ❌ UI（`ui/predict_tab.py` 等）
- ❌ scanner / matcher / 数据层
- ❌ 长桥 / 新闻 / 财报数据接入
- ❌ stash / `.claude/worktrees/` / `logs/prediction_log.jsonl`

## 7. 当前 contract 段进度（8 段总览，更新版）

| Section | 状态 | 说明 |
|---|---|---|
| 01 `current_structure` | 字段化 | adapter 从 scan + `primary_projection.lookback_days` 构造（Step 2B-2 联动） |
| 02 `avgo_primary_projection` | **字段化** | `build_primary_projection` self-publish（Step 2B-2） |
| 03 `peer_confirmation_adjustment` | **字段化** | `apply_peer_adjustment` self-publish（Step 2B-3，bias-aware 翻译） |
| 04 `exclusion_system` | ⚠️ required 仍占位 + `extras` 暴露真实风险信号 | required 5 字段全 stub；extras 6 键（Step 2C-2） |
| 05 `confidence_system` | ⚠️ 部分真值 + 4 score 仍占位 + `extras` 暴露 raw score-like 信号 | 3 真值 / 4 score stub / event_score None；extras 10 键（Step 2C-3b） |
| 06 `final_projection` | **字段化** | `build_final_projection` self-publish（Step 2B-4） |
| 07 `simulated_trade` | ❌ 全 stub | adapter 硬编码 `trade_action="no_trade"` 等；待模拟交易决策层 |
| 08 `review_payload` | 部分字段化（依赖 06） | adapter 从 final 字段派生；`prediction_id=""` 仍空 |

**已完成：** 02 / 03 / 06 三段由 builder 自发布；01 联动 02；04 / 05 在保持 required 字段语义不变的前提下用 `extras` 暴露 raw signals。

**仍未做：** 07 全 stub；08 的 `prediction_id` 仍空；04 的 required 字段（`exclusion_level / forced_exclusion / anti_false_exclusion_triggered`）尚未真字段化；05 的 4 个 score 字段（`historical_score / structure_score / peer_score / exclusion_penalty`）+ `event_score` 也尚未真字段化。

## 8. 下一步建议

> **强烈建议不要直接升级 `exclusion_level` 或 4 个 score。** 这些是策略 / calibration 决策，不是字段填充任务。先看以下任一方向：

| 候选 step | 范围 | 风险 |
|---|---|---|
| **Step 2D** —— 07 `simulated_trade` 同模式（`extras` + `no_trade_reason` 稳定化） | adapter `_build_simulated_trade` 加 `extras` 暴露 `final_direction` / `probability_bucket` / `path_risk` / `soft_signal`；`no_trade_reason` 从硬编码 stub 改成结构化文本（仍 `trade_action="no_trade"`） | 低，与 2C-2 / 2C-3b 模式严格对称 |
| **Step 2E** —— confidence calibration 只读诊断 | 只读分析：`primary_projection.score` 在历史 prediction_log 上的实际分布（用 sqlite 读已落库 contract_payload）、与 outcome 是否相关、tanh / sigmoid / 分桶 哪种归一更合适——不实现 | 极低，纯诊断报告 |
| **Step 2F** —— `exclusion_level` soft/hard 规则设计 | 写一份"在什么条件下 `exclusion_level` 应当升 soft / hard"的设计文档，引用 2C-1 诊断里的 `big_up_contradiction_card` / `exclusion_reliability_review` 等已有信号；**不实现，等 backtest** | 低，纯设计文档 |
| **Step 2G** —— contract dashboard 汇总 04 / 05 extras | 写一个只读 CLI 脚本（仿 `summarize_recent_contract_payloads.py`），专门 dump 最近 N 条 prediction 的 04 / 05 `extras.*` 分布 | 低，新工具不动主链 |

**推荐顺序：** 2D（最像 2B / 2C 字段化模式，工程性确定） → 2E（数据诊断，给 calibration 决策提供依据） → 2G（让 extras 真正"可被人类看到"，闭环验证）→ 2F（最大策略风险，需 2E 的 backtest 数据支持） → Step 2 真 calibration 接入（这才是 score 升真值的时机）。

**绝不在本轮 / 下一轮做的：**
- ❌ 把 `primary_projection.score` 直接归一化进 `structure_score`
- ❌ 把 `peer_confirm_count - peer_oppose_count` 当 `peer_score`
- ❌ 把 `soft_signal == "peer_weaken"` 升成 `exclusion_level == "soft"`
- ❌ 接 `confidence_engine.py` / `risk_model.py` / `contradiction_engine.py` 三个 v1 stub
- ❌ 改 `predict.py` / `run_predict`
- ❌ 接长桥 / 新闻 / 财报
