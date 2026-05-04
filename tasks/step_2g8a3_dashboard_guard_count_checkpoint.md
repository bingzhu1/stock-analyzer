# Step 2G-8A.3 — Dashboard Guard Count Integration Checkpoint

> **状态固化文档（dashboard guard count integration checkpoint），不实现，不改代码。**
> 本文档**冻结** `summarize_anti_false_exclusion_dashboard()` 输出新增
> 顶层字段 `protection_layer_diagnostics` 的 aggregate shape、四个
> connection flag 不变量、`guard_summary` 计数语义、Gate 5 仍 fail
> 的隔离约束、hard gate 6 项 2 pass / 4 fail 现状、与 Step 2G-8B / 2G-8+
> 的衔接边界。
>
> 本轮**不动任何代码**：不改 `predict.py` / `run_predict` /
> `scanner.py` / `prediction_store.py` / `app.py` / 任何 `ui/*` /
> `services/*`（含 `services/anti_false_exclusion_dashboard.py` /
> `services/protection_layer_diagnostics.py` /
> `ui/protection_layer_diagnostics_renderer.py`）/ 任何 builder /
> DB schema 中的任何一处。

---

## 1. 当前完成状态

- **Step 2G-8** launch condition review 已完成（结论：NO-GO，hard gate
  4/6 fail）
- **Step 2G-8A** protection-layer connection design + checkpoint 已
  完成并进入 main（commits `b4c1919` / `8c56696`）
- **Step 2G-8A.1** read-only protection diagnostics helper + checkpoint
  已完成并进入 main（commits `cdbb13a` / `b43fd9d`）
- **Step 2G-8A.2** Predict / Review UI integration + checkpoint 已
  完成并进入 main（commits `0eb589c` / `f24df37`）
- **Step 2G-8A.3** dashboard guard count integration 已完成并进入 main
  （commit `d1cce03`）
- 本 checkpoint **固定**：
  - `summarize_anti_false_exclusion_dashboard()` 顶层 14 个字段
    （13 旧 + 1 新增 `protection_layer_diagnostics`）
  - aggregate shape 中 4 个 connection flag、`guard_summary` 计数、
    `hard_upgrade_blocked` / `display_only` 不变量
  - happy / no_records / error / 全 pass / 缺数据 5 个 scenario 下的
    安全行为
  - Gate 5 仍 fail（`_PROTECTION_LAYER_CONNECTED = False` 未改）的
    隔离约束
- Step 2G-8A.3 是 **aggregate sidecar 集成**，但本 checkpoint **只是**
  状态归档；不实现、不改代码、不写 DB

---

## 2. 当前 main 状态

- main 最新 commit：**`d1cce03`**
- commit message：`feat(diagnostics): add protection layer guard counts to dashboard aggregate`
- 上游：`origin/main` 已同步
- full pytest：**2604 passed / 0 failed / 10 skipped / 26 warnings /
  94 subtests**（基线 2591 → 2604，+13 净增；零回归）

本步骤新增 / 修改文件（已 merge 到 main）：

| 路径 | 类型 | 说明 |
|---|---|---|
| `services/anti_false_exclusion_dashboard.py` | 修改 | import + `_aggregate_protection_layer_diagnostics()` 私有纯函数 + happy / error 两条返回路径写入新字段 |
| `tests/test_anti_false_exclusion_dashboard.py` | 修改 | `ProtectionLayerDiagnosticsAggregateTests` × 11 + `ProtectionLayerDiagnosticsAggregateIsolationTests` × 1 |
| `tasks/step_1_contract_pipeline_summary.md` | 修改 | 新增 §35 |

本 checkpoint 文档（即本文件）尚未 commit；本轮只写文档、不 commit /
push。

---

## 3. aggregate 新字段

`summarize_anti_false_exclusion_dashboard()` 返回 dict 顶层从 13 个
字段变 14 个，新增的 `protection_layer_diagnostics`：

```json
{
  "protection_layer_diagnostics": {
    "schema_version": "protection_layer_diagnostics.v1",
    "diagnostic_connected": true,
    "hard_gate_connected": false,
    "required_field_connected": false,
    "protection_layer_connected_for_gate": false,
    "guard_summary": {
      "total_guard_count": 2,
      "blocking_guard_count": 2,
      "blocking_reasons": {
        "holdout_status_FAIL": 1,
        "net_benefit_below_gate": 1
      },
      "guard_names": [
        "holdout_stability_guard",
        "net_benefit_guard"
      ]
    },
    "hard_upgrade_blocked": true,
    "display_only": true
  }
}
```

shape 不变量（schema-level 测试锁定）：
- `schema_version` 总是 `"protection_layer_diagnostics.v1"`（与 helper
  一致）
- 4 个 connection flag 取值固定：`diagnostic_connected = true` /
  其余三 false
- `guard_summary.total_guard_count` 与 `guard_names` 长度一致
- `guard_summary.blocking_guard_count` 与 `blocking_reasons` 计数总和
  一致
- `hard_upgrade_blocked` / `display_only` 永远 `true`（v1）

字段是**只读 sidecar**：
- 不参与 `hard_gate_status` 任何 gate 的判断
- 不参与 `hard_exclusion_allowed` 派生
- 不参与 `primary_blocker` 选择
- 不写 DB / 不写 contract / 不写 required

---

## 4. guard count 结果（默认 baseline）

| 字段 | 取值 |
|---|---|
| `total_guard_count` | 2 |
| `blocking_guard_count` | 2 |
| `blocking_reasons.holdout_status_FAIL` | 1 |
| `blocking_reasons.net_benefit_below_gate` | 1 |
| `guard_names` | `["holdout_stability_guard", "net_benefit_guard"]` |

派生逻辑（来自 `_aggregate_protection_layer_diagnostics`）：

| 字段 | 派生 |
|---|---|
| `total_guard_count` | `len(guard_names)` |
| `blocking_guard_count` | `count(g["status"] == "blocking")` |
| `blocking_reasons` | `Counter(g["reason"] for g in guards if g["status"] == "blocking")` |
| `guard_names` | `[g["name"] for g in guards]`（按 helper 输出顺序） |

**强调**：
- 这是 **sidecar 统计**，仅用于 dashboard / CLI 聚合视图
- **不**参与 hard gate pass / fail 判断
- **不**改变 `hard_exclusion_allowed`（仍依赖 6 项 gate 全 pass）
- 即使 `total_guard_count = 0`（理论上两 baseline 全 pass），
  `protection_layer_connected_for_gate` 仍为 `false`，
  `hard_upgrade_blocked` 仍为 `true`，Gate 5 仍 fail

---

## 5. no_records / error / empty 情况

| scenario | 触发 | guard_summary 行为 | 4 个 connection flag |
|---|---|---|---|
| 默认 baseline | R4 holdout=FAIL + nb=+0.0219 | total=2 / blocking=2 / 两 reason 各 1 | 锁定 |
| holdout PASS | 仅 nb < 0.05 | total=1 / blocking=1 / 仅 `net_benefit_below_gate=1` | 锁定 |
| 双 pass | holdout=PASS + nb≥0.05 | total=0 / blocking=0 / `blocking_reasons={}` / `guard_names=[]` | 锁定 |
| no_records | r4_overextension=None | total=0 / blocking=0 / counts 全 0 | 锁定 |
| error path | `build_soft_metadata_baseline` 抛异常 | total=0 / blocking=0 / counts 全 0 | 锁定 |

无论哪个 scenario：
- `diagnostic_connected = true`（永远）
- `hard_gate_connected = false`（永远）
- `required_field_connected = false`（永远）
- `protection_layer_connected_for_gate = false`（永远）
- `hard_upgrade_blocked = true`（永远）
- `display_only = true`（永远）

**核心原则**：缺数据 / error 都**不**虚假 blocking；但缺数据 / error
下四个 connection flag 与两个 summary 不变量**仍**保持 v1 锁定值。
downstream 读者可以无脑 `dict.get("protection_layer_diagnostics")` ——
该字段在 happy / no_records / error 三条路径都存在。

---

## 6. Gate 5 状态

**Gate 5 `protection_layer_connected` 仍 fail（未改变）。**

- `services/anti_false_exclusion_dashboard.py:44` 第 44 行：
  ```python
  _PROTECTION_LAYER_CONNECTED = False
  ```
  **本步骤未改动**；Step 2G-8A.3 dashboard 集成不修改这一常量
- `summarize_anti_false_exclusion_dashboard()` 输出的
  `hard_gate_status.protection_layer_connected` 仍为 `"fail"`
- `hard_exclusion_allowed` 仍为 `False`
- `protection_layer_diagnostics.protection_layer_connected_for_gate`
  仍为 `false`（aggregate 字段内的 v1 强不变量）
- 即使 `diagnostic_connected = true`，**不代表** Gate 5 pass

测试 `ProtectionLayerDiagnosticsAggregateTests::test_module_constant_unchanged`
对常量值用 `assertFalse(_PROTECTION_LAYER_CONNECTED)` 锁定。

---

## 7. hard gate 6 项状态

| Gate | 状态（未变） | 数据 |
|---|---|---|
| `total_paired_ge_90` | **PASS** | paired_total = 286 ≥ 90 |
| `candidate_paired_ge_30` | **PASS** | R4 paired = 34 ≥ 30 |
| `false_exclusion_rate_lte_0_10` | FAIL | R4 fer = 0.3235 > 0.10 |
| `net_benefit_gte_0_05` | FAIL | R4 nb = +0.0219 < +0.05 |
| **`protection_layer_connected`** | **FAIL（仍 fail）** | `_PROTECTION_LAYER_CONNECTED = False` |
| `cross_window_holdout_pass` | FAIL | holdout_status = "FAIL" |

**结论**：**2 pass / 4 fail**（与 Step 2G-7C / 8 / 8A.1 / 8A.2 完全
一致）。

`hard_exclusion_allowed = all(v == "pass" for v in gate_status.values())`
→ 仍为 `False`。`primary_blocker` 仍按优先级（fer → nb → holdout →
protection_layer）选择，本 baseline 下 = `false_exclusion_rate_too_high`
（Step 2G-7C `PrimaryBlockerTests` 锁定）。

---

## 8. 测试覆盖

### 8.1 测试结果

| 命令 | 结果 |
|---|---|
| `pytest tests/test_anti_false_exclusion_dashboard.py -q` | **48 passed**（35 baseline + 13 新增） |
| `pytest tests/test_protection_layer_diagnostics.py -q` | **39 passed**（+24 subtests） |
| `pytest -q`（全量） | **2604 passed / 10 skipped / 0 failed / 26 warnings / 94 subtests** |

测试基线累积：**Step 2G-8A.2 终点 2591 → Step 2G-8A.3 终点 2604**
（+13 净增；现有 2591 基线零回归）。

### 8.2 测试矩阵（新增 13 cases）

`tests/test_anti_false_exclusion_dashboard.py`：

| 测试 | 覆盖点 |
|---|---|
| `test_field_present_in_default_summary` | `protection_layer_diagnostics` 字段存在 / `schema_version` 锁定 |
| `test_four_connection_flags_locked` | 4 个 flag 取值锁定 |
| `test_guard_summary_counts_two_guards_for_default_baseline` | 默认 baseline 触发两 guard，`guard_names` 完整 |
| `test_blocking_reasons_contain_both_default_reasons` | `blocking_reasons` 含两 reason 各 1 次 |
| `test_summary_top_level_invariants` | `hard_upgrade_blocked` / `display_only` 锁定 |
| `test_hard_gate_status_still_fail` | Gate 5 仍 fail |
| `test_hard_exclusion_allowed_still_false` | `hard_exclusion_allowed` 仍 false |
| `test_holdout_pass_only_net_benefit_guard` | holdout PASS → 仅 net_benefit guard，flag 仍锁定 |
| `test_both_r4_pass_zero_guards_but_invariants_intact` | 全 pass → 0 guard，不变量保持，Gate 5 仍 fail |
| `test_no_records_path_safe_zero_counts` | no_records → 字段存在，counts=0，flag 锁定 |
| `test_baseline_load_error_path_includes_safe_field` | error path → 字段存在，counts=0，flag 锁定 |
| `test_module_constant_unchanged` | `_PROTECTION_LAYER_CONNECTED = False` 未改 |
| `test_module_imports_helper_only`（isolation） | `ast.walk` 锁定未 import 禁用模块 |

### 8.3 关键 isolation 锁定

`ast.walk` 测试锁定 `services/anti_false_exclusion_dashboard.py`
未 import：
- `yfinance` / `requests`
- `longbridge` / `broker` / `paper_trade`
- `sqlite3`
- `services.prediction_store`
- `services.confidence_engine` / `services.contradiction_engine` /
  `services.risk_model`
- `predict` / `scanner`
- `ui.protection_layer_diagnostics_renderer`

允许：`services.protection_layer_diagnostics`（Step 2G-8A.3 新增；纯
helper，无 side-effect）。

---

## 9. 与 04 / 05 / 07 required 字段关系

dashboard 集成**只**调用现有 helper + 复用本来就构造好的
`soft_metadata_summary`；**不**影响任何 04 / 05 / 07 schema：

| 字段 | 状态 |
|---|---|
| `anti_false_exclusion_triggered` | **不**写（保持现状） |
| `exclusion_level` | **不**改 |
| `forced_exclusion` | **不**改 |
| `confidence_score` / `final_confidence` | **不**改 |
| `simulated_trade` | **不**改 |
| `no_trade` | **不**改 |
| `final_direction` / `final_projection` | **不**改 |
| `hard` 启用 | **不**启用 |
| `forced_exclusion` 启用 | **不**启用 |
| 04 `prediction_log` schema | **不**升级 |
| 05 `outcome_log` schema | **不**升级 |
| 07 `review_log` schema | **不**升级 |

**`protection_layer_diagnostics` 仍是 aggregate sidecar**：
- 不进入 04 / 05 / 07 任何 required 字段
- 不进入 `contract_payload_json`
- 不持久化到任何表
- 仅在 `summarize_anti_false_exclusion_dashboard()` 返回 dict 中存在

---

## 10. 与 Step 2G-8B 的关系

Step 2G-8A 系列已经完整完成 protection diagnostics 的 **三层 sidecar**：
- 8A.1：helper（pure function）
- 8A.2：Predict / Review UI 子节集成
- 8A.3：Step 2G-7C dashboard aggregate sidecar 集成

但这**只解决 Gate 5 的 display / diagnostic 维度**，并**不**真正
缩小其余 4 项 hard gate fail 的 gap：
- `false_exclusion_rate_lte_0_10` 仍 fail（R4 fer = 0.3235）
- `net_benefit_gte_0_05` 仍 fail（R4 nb = +0.0219）
- `protection_layer_connected` 仍 fail（v1 hard-coded）
- `cross_window_holdout_pass` 仍 fail（holdout = FAIL）

**下一步 8B 应研究 narrower R4 candidate**，目标：
- 找 R4 + 二级条件（e.g. `peer_path_risk_direction=lower` /
  `confidence_high` / `bias_gap≥0.5` 等）的子切片
- 在该子切片上**降低 false_exclusion_rate**（向 ≤ 0.10 收敛）
- 在该子切片上**收窄 net_benefit gap**（向 ≥ +0.05 收敛）
- 用 ad-hoc sqlite 只读查询 + Python 离线脚本完成研究
- **仍然只读**，不进 decision chain，不写 DB，不改 04 required

8B 不是实施层；8B 是**证据收集层**。8B 完成后才能在 Step 2G-8C
（holdout gap analysis）+ Step 2G-8+（new launch review）中讨论是否
真正解封 hard gate 的某些维度。

---

## 11. 当前限制

8A 系列已落地，但仍有边界限制（v1 范围内）：

| # | 限制 | 解封步骤 |
|---|---|---|
| 1 | **Gate 5 仍 fail**；`_PROTECTION_LAYER_CONNECTED = False` | Step 2G-8+ launch review（前提：8B / 8C 先完成 + protection layer 真接入 hard pipeline） |
| 2 | protection layer 仍未进入 decision pipeline | 同上 |
| 3 | dashboard 只是 JSON / CLI aggregate；**未接** Streamlit dashboard UI | （可选）Step 2G-7E / 8A.3-UI；非必须 |
| 4 | hard gate 仍 **2 pass / 4 fail** | Step 2G-8B（fer / nb gap）+ 2G-8C（holdout）+ 2G-8+ |
| 5 | hard implementation 仍 NO-GO | 同上 |
| 6 | aggregate 仅覆盖 2 个 guard；4 个候选模块（survival / secondary_confirm 等）未实施 | Step 2G-8B narrower R4 candidate research |
| 7 | aggregate 不持久化；每次 caller 即时构造 | （永远不解封；sidecar-only） |

---

## 12. 下一步建议

按推荐优先级：

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **Step 2G-8A.3 checkpoint**（本文档） | 冻结 aggregate 新字段 + guard_summary + Gate 5 仍 fail | **本轮** |
| 2 | **Step 2G-8B** narrower R4 candidate research | 只读 ad-hoc sqlite 研究 survival pattern / secondary confirmation；为 fer / nb gap 找证据；**不**接决策链 | **高**（8A 系列完成后的自然延续；为 Gate 3 / 4 找解 fail 路径） |
| 3 | **Step 2G-7E**（可选）dashboard Streamlit UI integration | 把 Step 2G-7C aggregate（含 8A.3 新字段）渲染到 Streamlit dashboard tab | 中（让用户在 UI 中也看见 sidecar；非必须） |
| 4 | **Step 2G-8C** holdout gap analysis | 只读对比 in-sample vs holdout；为 Gate 6 找诊断 | 中-低（与 Step 3 calibration 重启耦合） |
| 5 | **不推荐** 直接实施 hard gate / required 升级 | 4 项 gate fail；Step 2G-8 launch review 已 NO-GO | — |
| 6 | **不推荐** 让 `_PROTECTION_LAYER_CONNECTED` 翻 True | sidecar ≠ decision pipeline；必须 Step 2G-8+ launch review 重新评估 | — |
| 7 | **不推荐** 改 `_build_exclusion_system` / `run_predict` / `prediction_store` 主链 | 当前 sidecar + UI display + Review attribution + protection display + dashboard aggregate 已是最大可行边界 | — |

**强制约束**（继承 8A 设计 §13 / 8A.1 / 8A.2 checkpoint）：
Step 2G-8B / 2G-8C 实施时仍要遵守：
- 不改 04 / 05 / 07 required 字段
- 不改 `run_predict` 主链
- 不写 DB
- 不出现 19 forbidden words（AFX 内部）/ 16 forbidden words（页面级）
  / 8 forbidden words（protection sidecar 内部）
- `hard_exclusion_allowed` 永远 `False`
- `protection_layer_connected_for_gate` 永远 `False`（v1）

---

## 13. 严守边界

本文是**纯 checkpoint 文档**：

- ❌ 没改任何代码（含 `services/anti_false_exclusion_dashboard.py` /
  `services/protection_layer_diagnostics.py` /
  `ui/protection_layer_diagnostics_renderer.py` /
  `ui/predict_tab.py`）
- ❌ 没改 DB schema
- ❌ 没写 DB
- ❌ 没改 `run_predict` / `predict.py` / `scanner.py` /
  `prediction_store.py` / `app.py`
- ❌ 没改 `services/anti_false_exclusion_dashboard.py` /
  `services/soft_metadata_simulator.py` / 任何 ui 模块 /
  任何 builder
- ❌ 没改 04 / 05 / 07 任何 required 字段
- ❌ 没启用 `hard` / `forced_exclusion` /
  `anti_false_exclusion_triggered`
- ❌ 没接 `yfinance` / `requests` / 任何网络
- ❌ 没接 trading API / `longbridge` / `broker` / `paper_trade`
- ❌ 没让 `_PROTECTION_LAYER_CONNECTED` 翻 True
- ❌ 没让 `hard_gate_status.protection_layer_connected` 自动 pass
- ❌ 没改 `hard_exclusion_allowed` / `primary_blocker` 派生
- ❌ 没触碰 2026-01-01 之后 final test range
- ❌ 没运行 replay / 没新写 replay 行
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` /
  `avgo_agent.db.backup_*`
- ❌ 没运行 `pytest`（本轮纯文档；测试结果引用 commit `d1cce03`
  的实测数据）
- ✅ 只新增 1 份 markdown checkpoint 文档（本文件）
