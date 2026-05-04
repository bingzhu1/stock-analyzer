# Step 2G-8A.1 — Protection Layer Diagnostics Helper Checkpoint

> **状态固化文档（read-only sidecar helper checkpoint），不实现，不改代码。**
> 本文档**冻结** `protection_layer_diagnostics.v1` helper 的行为、
> 输出 schema、四个 connection flag 不变量、两个 guard 行为、与
> Step 2G-7C dashboard / Gate 5 的隔离约束、与 Step 2G-8A.2 / 2G-8A.3
> / 2G-8B 的衔接边界。
>
> 本轮**不动任何代码**：不改 `predict.py` / `run_predict` /
> `scanner.py` / `prediction_store.py` / `app.py` / 任何 `ui/*` /
> `services/*`（包含 `services/protection_layer_diagnostics.py`）/
> 任何 builder / DB schema 中的任何一处。

---

## 1. 当前完成状态

- **Step 2G-8** launch condition review 已完成（结论：NO-GO，hard gate
  4/6 fail）
- **Step 2G-8A** protection-layer connection design 已完成并进入 main
  （commit `b4c1919`）
- **Step 2G-8A** checkpoint 已完成并进入 main（commit `8c56696`）
- **Step 2G-8A.1** read-only protection diagnostics helper 已实现并
  进入 main（commit `cdbb13a`）
- 本 checkpoint **固定** `protection_layer_diagnostics.v1` helper 的
  实现边界、输出 schema、4 个 connection flag 强不变量
- Step 2G-8A.1 是**实现层 sidecar helper**，但本 checkpoint **只是**
  状态归档；不实现、不改代码、不写 DB

---

## 2. 当前 main 状态

- main 最新 commit：**`cdbb13a`**
- commit message：`feat(diagnostics): add protection layer diagnostics sidecar helper`
- 上游：`origin/main` 已同步
- full pytest：**2560 passed / 0 failed / 10 skipped / 26 warnings /
  89 subtests**（基线 2521 → 2560，+39 净增；零回归）

本步骤新增 / 修改文件（已 merge 到 main）：

| 路径 | 类型 | 说明 |
|---|---|---|
| `services/protection_layer_diagnostics.py` | 新增 | helper 实现（pure function） |
| `tests/test_protection_layer_diagnostics.py` | 新增 | 39 focused tests + 24 subtests |
| `tasks/step_1_contract_pipeline_summary.md` | 修改 | 新增 §33 |

本 checkpoint 文档（即本文件）尚未 commit；本轮只写文档、不 commit /
push。

---

## 3. helper API

模块：`services/protection_layer_diagnostics.py`

### 3.1 主公共函数

```python
build_protection_layer_diagnostics(
    anti_false_exclusion_summary: dict | None = None,
    *,
    soft_metadata: dict | None = None,
) -> dict
```

- **read-only**：不读 DB / CSV / 文件
- **pure function**：无 side-effect；不修改输入；同输入恒同输出
- **不写 DB**：不调用 `prediction_store` / `outcome_store` /
  `review_store` / 任何持久化层
- **不调用 dashboard service**：不调用
  `services.anti_false_exclusion_dashboard.summarize_anti_false_exclusion_dashboard`
  —— 调用方（caller）自己决定喂什么 dict
- **不调用 prediction_store** / `regime_diagnostics_dashboard` /
  `confidence_engine` / `contradiction_engine` / `risk_model`
- **不接网络**：未 import `yfinance` / `requests`
- **不接 trading**：未 import `longbridge` / `broker` / `paper_trade`
- **isolation 测试用 `ast.walk` 锁定**这一边界

### 3.2 便捷 wrapper

```python
build_protection_layer_diagnostics_from_dashboard(summary: dict) -> dict
```

- thin wrapper：`build_protection_layer_diagnostics(anti_false_exclusion_summary=summary)`
- 不重新查询 DB / 不重跑 dashboard service / 不递归调 helper
- 同样满足 §3.1 的全部隔离约束

---

## 4. 输出 schema

`protection_layer_diagnostics.v1`（已冻结）：

```json
{
  "schema_version": "protection_layer_diagnostics.v1",
  "diagnostic_connected": true,
  "hard_gate_connected": false,
  "required_field_connected": false,
  "protection_layer_connected_for_gate": false,
  "guards": [
    {
      "name": "holdout_stability_guard",
      "status": "blocking",
      "reason": "holdout_status_FAIL",
      "evidence": {"holdout_status": "FAIL"},
      "message": "跨窗口验证未通过，当前只允许复盘提示。"
    },
    {
      "name": "net_benefit_guard",
      "status": "blocking",
      "reason": "net_benefit_below_gate",
      "evidence": {"net_benefit": 0.0219, "threshold": 0.05},
      "message": "净收益不足，当前只允许复盘提示。"
    }
  ],
  "summary": {
    "hard_upgrade_blocked": true,
    "display_only": true,
    "blocking_guard_count": 2,
    "required_next_step": "narrower_candidate_research"
  },
  "warnings": []
}
```

shape 不变量（schema-level 测试锁定）：
- 顶层必备 key：`schema_version` / 4 个 connection flag /
  `guards` / `summary` / `warnings`
- `summary` 必备 key：`hard_upgrade_blocked` / `display_only` /
  `blocking_guard_count` / `required_next_step`
- 每个 `guard` 必备 key：`name` / `status` / `reason` / `evidence` /
  `message`；`status="blocking"` 仅枚举值

---

## 5. 四个 connection flags（v1 强不变量）

| flag | v1 取值 | 含义 |
|---|---|---|
| `diagnostic_connected` | **总是 `true`** | sidecar diagnostics 已生成；UI 可读取此节点 |
| `hard_gate_connected` | **总是 `false`** | 没有进入 hard decision pipeline；`run_predict` / `scanner` 不读 |
| `required_field_connected` | **总是 `false`** | 没有写 04 required 字段；schema 无升级 |
| `protection_layer_connected_for_gate` | **总是 `false`** | Step 2G-7C dashboard Gate 5 仍 fail |

**反误读（最重要的边界）**：
- `diagnostic_connected = true` **不等于** Gate 5 pass
- `diagnostic_connected = true` **不等于** hard 升级被允许
- `diagnostic_connected = true` **只代表**：sidecar 节点存在，UI
  可以拿到这个 dict 来渲染"保护层诊断详情"
- 未来若有读者把"sidecar 接入"误解读为"决策链接入"，schema 测试
  与本 checkpoint **同时**起到反误读作用

---

## 6. 两个 guard 行为

### 6.1 `holdout_stability_guard`

| 项 | 值 |
|---|---|
| 触发 | candidate 或 R4 `holdout_status == "FAIL"` |
| 不触发 | `"PASS"` / `"UNKNOWN"` / `""` / `None` |
| `status` | `"blocking"` |
| `reason` | `"holdout_status_FAIL"` |
| `evidence` | `{"holdout_status": "FAIL"}` |
| `message` | `"跨窗口验证未通过，当前只允许复盘提示。"` |

**严格相等**：仅字面量字符串 `"FAIL"` 才触发；缺数据走 §7
`missing_metrics` warning 路径，**不**虚假 blocking。

### 6.2 `net_benefit_guard`

| 项 | 值 |
|---|---|
| 触发 | R4 `net_benefit < 0.05` |
| 不触发 | `net_benefit >= 0.05`（含 `== 0.05` 边界） |
| 不触发 | 非数字 / `None` / `bool` |
| `status` | `"blocking"` |
| `reason` | `"net_benefit_below_gate"` |
| `evidence` | `{"net_benefit": <float>, "threshold": 0.05}` |
| `message` | `"净收益不足，当前只允许复盘提示。"` |

**阈值与 hard-gate 一致**：`>=` 边界与 Step 2G-3 / 2G-4.5 / 2G-7C
`net_benefit_gte_0_05` 完全一致；`bool` 不算数字（与 AFX / dashboard
`_is_real_number` 一致）。

### 6.3 message 文案锁定

两条 message **均不出现** Step 2G-7A AFX 19-token forbidden 列表
中的任何 token（`禁止交易` / `hard exclusion` / `force close` /
`阻止下单` / `强制平仓` / `卖出信号` / `做空信号` / `否决主推演` /
`推翻主推演` / ` hard ` / ` forced ` / `排除` / 等）。
`ForbiddenCopyTests` × 2 锁定。

---

## 7. missing metrics 行为

### 7.1 触发路径

- 没传 `anti_false_exclusion_summary` 也没传 `soft_metadata`
- 传了但都是空 dict / 非 dict（`None` / 字符串 / 数字 / list / bool /
  …）
- 传了 dict 但既无 `soft_metadata_summary.r4_overextension` 也无
  signals 中的 `r4_overextension`
- R4 节点存在但 `holdout_status` 与 `net_benefit` 都不可读

### 7.2 输出形态

| 字段 | 值 |
|---|---|
| `diagnostic_connected` | **`true`**（不变） |
| `hard_gate_connected` | `false`（不变） |
| `required_field_connected` | `false`（不变） |
| `protection_layer_connected_for_gate` | `false`（不变） |
| `guards` | `[]`（empty list） |
| `summary.hard_upgrade_blocked` | **`true`**（不变） |
| `summary.display_only` | **`true`**（不变） |
| `summary.blocking_guard_count` | `0` |
| `summary.required_next_step` | `"narrower_candidate_research"`（不变） |
| `warnings` | 含 `"missing_metrics"` |

**核心原则**：缺数据 ≠ guard blocking；但缺数据下四个 connection
flag 与两个 summary 不变量**仍**保持 v1 锁定值，只通过
`warnings` 透传缺数据信号。

---

## 8. from_dashboard helper

```python
build_protection_layer_diagnostics_from_dashboard(summary: dict) -> dict
```

### 8.1 行为契约

- 从 `summary["soft_metadata_summary"]["r4_overextension"]` 读取：
  - `holdout_status`
  - `net_benefit`
- 容错：当 `summary["soft_metadata_summary"]` 不存在或非 dict 时，
  fallback 到 `summary["r4_overextension"]`（bare candidate map）
- **不**重新计算 DB
- **不**调用 `summarize_anti_false_exclusion_dashboard`
- **不**调用 `build_soft_metadata_baseline`
- 纯 dict 转换 → `build_protection_layer_diagnostics(anti_false_exclusion_summary=summary)`
- 输入是垃圾（`"not a dict"` / `123` / `None` / `[]` / …）→ 走
  §7 missing metrics 路径，仍返回完整 schema

### 8.2 与 dashboard 的解耦

- dashboard 是 **caller**：dashboard 调 helper，helper **不**反向调
  dashboard
- 两者是**单向数据流**，不形成循环依赖
- 8A.3 未来若把 helper 接入 dashboard aggregate JSON，是 dashboard
  作为 caller 喂 dict 给 helper —— 仍由 dashboard 决定何时调用

---

## 9. Gate 5 状态

**Gate 5 `protection_layer_connected` 仍 fail（未改变）。**

- `services/anti_false_exclusion_dashboard.py` 第 44 行：
  ```python
  _PROTECTION_LAYER_CONNECTED = False
  ```
  **本步骤未改动**；Step 2G-8A.1 helper 不修改这一常量
- `summarize_anti_false_exclusion_dashboard()` 输出的
  `hard_gate_status.protection_layer_connected` 仍为 `"fail"`
- `hard_exclusion_allowed` 仍为 `False`（依赖 6 项 gate 全 pass，而
  Gate 5 永远 fail）
- `primary_blocker` 仍由优先级（fer → nb → holdout → protection_layer）
  决定，与 Step 2G-7C 一致

| Gate | 状态（未变） |
|---|---|
| `total_paired_ge_90` | PASS |
| `candidate_paired_ge_30` | PASS |
| `false_exclusion_rate_lte_0_10` | FAIL（R4 fer = 0.3235） |
| `net_benefit_gte_0_05` | FAIL（nb = +0.0219） |
| **`protection_layer_connected`** | **FAIL（仍 fail）** |
| `cross_window_holdout_pass` | FAIL |

**helper 只是 sidecar**：
- 不读、不写、不影响 `_PROTECTION_LAYER_CONNECTED` 常量
- 不进入 hard decision pipeline
- `protection_layer_connected_for_gate = false` 是 helper schema 内
  的强不变量，与 Step 2G-7C dashboard 的 `protection_layer_connected`
  fail 状态**字面对应**

---

## 10. 测试覆盖

### 10.1 测试结果

| 命令 | 结果 |
|---|---|
| `pytest tests/test_protection_layer_diagnostics.py -q` | **39 passed**（+24 subtests） |
| `pytest tests/test_anti_false_exclusion_dashboard.py tests/test_anti_false_exclusion_display.py -q` | **70 passed** |
| `pytest -q`（全量） | **2560 passed / 10 skipped / 0 failed / 26 warnings / 89 subtests** |

测试基线累积：**Step 2G-7C 起点 2521 → Step 2G-8A.1 终点 2560**
（+39 净增；现有 2521 基线零回归）。

### 10.2 测试矩阵（`tests/test_protection_layer_diagnostics.py`）

| 测试类 | 数量 | 覆盖点 |
|---|---|---|
| `OutputSchemaTests` | 4 | 顶层 key / `schema_version` / `summary` 必备字段 / guard 字段 |
| `HoldoutStabilityGuardTests` | 4 | FAIL 触发 / PASS 不触发 / `UNKNOWN` `""` `None` 不触发 / soft_metadata 路径触发 |
| `NetBenefitGuardTests` | 4 | `<0.05` 触发 / `==0.05` 不触发 / `>0.05` 不触发 / soft_metadata 路径触发 |
| `MissingMetricsTests` | 5 | 无输入 → warning / 空 dashboard → warning / 无 R4 → warning / 垃圾 payload graceful / 缺数据下 connection flag 仍锁定 |
| `ConnectionFlagInvariantTests` | 4 | 6 个 scenario × 4 个 flag → 各自常量锁定 |
| `SummaryInvariantTests` | 4 | `hard_upgrade_blocked` / `display_only` / `blocking_guard_count` / `required_next_step` 锁定 |
| `InputImmutabilityTests` | 3 | dashboard / soft_metadata / 双输入 input 不被原地修改 |
| `FromDashboardTests` | 3 | 默认提取 / 全 pass 路径 `guards=[]` / 垃圾输入 graceful |
| `FinalTestRangeWarningTests` | 3 | dashboard / soft_metadata warning 透传 / 去重 |
| `CrossSourceTests` | 2 | dashboard 字段优先 / 缺字段时 soft_metadata fallback |
| `IsolationTests` | 1 | `ast.walk` 锁定禁 import |
| `ForbiddenCopyTests` | 2 | 默认路径 / soft_metadata 路径下 message 不含 19 forbidden token |

### 10.3 关键 isolation 锁定

`ast.walk` 测试锁定模块未 import：
- `yfinance` / `requests`
- `longbridge` / `broker` / `paper_trade`
- `sqlite3`
- `services.prediction_store`
- `services.confidence_engine` / `services.contradiction_engine` /
  `services.risk_model`
- `services.soft_metadata_simulator`
- `services.anti_false_exclusion_dashboard`
- `predict` / `scanner`

---

## 11. 与 04 / 05 / 07 required 字段关系

helper **只**是 `extras` / sidecar-only 输出；**不**影响任何 04 / 05
/ 07 schema：

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

**`protection_layer_diagnostics` 是 extras / sidecar-only**：
- 不进入 04 / 05 / 07 任何 required 字段
- 不进入 `contract_payload_json`（除非未来 8A.3 主动接入，且仍是
  optional / sidecar）
- 不持久化到任何表
- 仅在内存中由 caller 构造、由 UI / dashboard 渲染

---

## 12. 与 Step 2G-8A.2 的关系

Step 2G-8A.2 = Predict / Review **UI 子节集成**：

### 12.1 8A.2 可以做的

- 在 `ui/anti_false_exclusion_display.py` 之外 / 之下作为
  **"保护层诊断详情"子节** 渲染 helper 输出
- 在 Predict 页面 anti-false expander 内显示 guards 列表 + summary
- 在 Review 页面把 `triggered_but_not_error` 象限 累计与
  `blocking_guard_count` 关联显示
- 文案严格继承本 checkpoint 的 §6.3 forbidden 列表

### 12.2 8A.2 必须遵守

- **仍**只能 `display_only`（与 helper schema 一致）
- **不能**让 Step 2G-7C dashboard `protection_layer_connected`
  自动变 pass
- **不能**改 `hard_exclusion_allowed`（仍 `False`）
- **不能**改 `status` / `recommended_action` 任何 AFX 字段
- **不能**写 04 `anti_false_exclusion_triggered`
- **不能**改 04 / 05 / 07 任何 required 字段

### 12.3 UI 文案要点

UI 文案要**强调**（与 Step 2G-8A 设计 §8.4 / checkpoint §9.4 一致）：
- "诊断已生成"
- "不等于自动升级"
- "当前仍只允许复盘提示"
- "保护层仍未进入决策链"
- "净收益不足"
- "跨窗口验证未通过"
- "不改变主推演方向"
- "不构成交易指令"
- "仅供复盘参考"

---

## 13. 当前限制

helper 已落地，但仍有边界限制（v1 范围内）：

| # | 限制 | 解封步骤 |
|---|---|---|
| 1 | helper **尚未接入** Predict / Review UI 渲染 | Step 2G-8A.2 |
| 2 | dashboard aggregate **尚未显示** `guard_total` / `guard_blocking_count` | Step 2G-8A.3 |
| 3 | `protection_layer_diagnostics` **不保存 DB**；每次 caller 即时构造 | （永远不解封；sidecar-only） |
| 4 | 保护层**仍未进入** decision pipeline | Step 2G-8+ launch review（前提是 8B / 8C 先完成） |
| 5 | hard gate 仍 **2 pass / 4 fail**（fer / nb / protection_layer / holdout） | 同上 |
| 6 | helper 仅覆盖 2 个 guard（holdout / net_benefit）；4 个候选模块（survival / secondary_confirm 等）**未实施** | Step 2G-8B narrower R4 candidate research |
| 7 | helper 不读 baseline；caller 自行喂数据 | （v1 强约束；纯函数） |

---

## 14. 下一步建议

按推荐优先级：

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **Step 2G-8A.1 checkpoint**（本文档） | 冻结 helper schema + 4 connection flag + 2 guard 行为 + Gate 5 仍 fail | **本轮** |
| 2 | **Step 2G-8A.2** Predict / Review UI integration | anti-false expander 之下作为 sub-section；纯 UI 改动；不改 contract；不改 04/05/07 required | **高**（与 8A.1 配套；让用户看见诊断信息） |
| 3 | **Step 2G-8A.3** dashboard integration | 把 sidecar 加入 Step 2G-7C aggregate JSON / 显示 guard 计数维度；Gate 5 仍 fail | 中（增强 dashboard 完整性） |
| 4 | **Step 2G-8B** narrower R4 candidate research | 只读 ad-hoc sqlite 研究 survival pattern / secondary confirmation；为 Gate 3 / 4 缩小 gap 找证据 | 中（与 8A 解耦；可并行） |
| 5 | **Step 2G-8C** holdout gap analysis | 只读对比 in-sample vs holdout；为 Gate 6 找诊断 | 中-低（与 Step 3 calibration 重启耦合） |
| 6 | **不推荐** 直接实施 hard gate / required 升级 | 4 项 gate fail；Step 2G-8 launch review 已 NO-GO | — |
| 7 | **不推荐** 让 Step 2G-7C dashboard `protection_layer_connected` 自动变 pass | sidecar ≠ decision pipeline；必须 Step 2G-8+ launch review | — |
| 8 | **不推荐** 改 `_build_exclusion_system` / `run_predict` / `prediction_store` 主链 | 当前 sidecar + UI display + Review attribution + protection display + dashboard aggregate 已是最大可行边界 | — |

**强制约束**（继承 Step 2G-8A 设计 §13 / checkpoint §12.2）：
Step 2G-8A.2 / 2G-8A.3 / 2G-8B / 2G-8C 实施时仍要遵守：
- 不改 04 / 05 / 07 required 字段
- 不改 `run_predict` 主链
- 不写 DB
- 不出现 19 forbidden words（AFX 内部 / protection sidecar 内部）/
  16 forbidden words（页面级）
- `hard_exclusion_allowed` 永远 `False`
- `protection_layer_connected_for_gate` 永远 `False`（v1）

---

## 15. 严守边界

本文是**纯 checkpoint 文档**：

- ❌ 没改任何代码（含 `services/protection_layer_diagnostics.py`）
- ❌ 没改 DB schema
- ❌ 没写 DB
- ❌ 没改 `run_predict` / `predict.py` / `scanner.py` /
  `prediction_store.py` / `app.py`
- ❌ 没改 `services/anti_false_exclusion_dashboard.py` /
  `ui/anti_false_exclusion_display.py` / `services/soft_metadata_simulator.py`
  / 任何已有 service / ui 模块 / 任何 builder
- ❌ 没改 04 / 05 / 07 任何 required 字段
- ❌ 没启用 `hard` / `forced_exclusion` /
  `anti_false_exclusion_triggered`
- ❌ 没接 `yfinance` / `requests` / 任何网络
- ❌ 没接 trading API / `longbridge` / `broker` / `paper_trade`
- ❌ 没让 Step 2G-7C dashboard `hard_gate_status.protection_layer_connected`
  自动 pass
- ❌ 没触碰 2026-01-01 之后 final test range
- ❌ 没运行 replay / 没新写 replay 行
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` /
  `avgo_agent.db.backup_*`
- ❌ 没运行 `pytest`（本轮纯文档；测试结果引用 commit `cdbb13a`
  的实测数据）
- ✅ 只新增 1 份 markdown checkpoint 文档（本文件）
