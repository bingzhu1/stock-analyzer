# 11G记录：Promotion Offline-only Documentation Lock Design

> 本设计针对 Step 09 / Step 10 中标记为 **LOW_RISK** 的 RISK-10。
>
> 本轮**只写设计**：未改代码、未新增测试、未删文件、未移动文件、未写 DB、
> 未跑 validation、未 commit / push、未进入 Step 12、未进入 3R-5 / 3R-6、
> 未新增 candidate、未复活 continuous_smoothing、未实际修改 promotion 模块、
> 未顺手碰 RISK-1 / RISK-2 / RISK-3 / RISK-7 / RISK-8 / RISK-9。

---

## 1. 设计目的

把 **promotion** 相关模块**预防性**锁定为 offline-only research /
calibration / validation 工具，防止未来某个 PR 误把 `execution_enabled=True`
或类似 flag 翻开后让 promotion 输出进入在线推演 / 否定 / 置信度 / final
report / trading / UI 路径。

修复后的目标：

- promotion 模块**永久** offline-only
- doc-lock：模块顶部 docstring 显式标注 `OFFLINE_ONLY`
- 输出 schema 加 safety fields（`mode`、`online_safe`、`may_affect_*`、
  `requires_human_review`）
- contract test 锁定：app.py / ui/ / projection / exclusion / confidence /
  final_decision 路径**禁止 import** promotion 模块
- promotion 模块**禁止输出** `production_promotion: true` /
  `_PROTECTION_LAYER_CONNECTED: true` / `hard_exclusion: true` /
  `forced_exclusion: true` / `required_decision: true` / `trading_action` /
  buy / sell / hold

本设计**只**产出设计文档，Step 12 才实施 + commit。

---

## 2. 当前风险

### 2.1 RISK-10 是预防性风险，不是已存活违规

Step 09 / Step 10 已确认：

- **当前状态 CLEAN**：promotion 模块没有违反 contract 的 active 行为；
  `services/promotion_execution_bridge.py:15` 的 `execution_enabled: False`
  是默认值；唯一 active caller 是 `services/avgo_1000day_training.py`（offline
  训练，不属在线判断）
- **风险点**：promotion 模块**结构上**已经具备"可启用 → 接 active path"的
  接口（`execution_enabled` 字段、promote_candidate / keep_active_observe /
  hold_back / do_not_promote 等分类决策）；如果未来某个 PR 在 caller 端
  传 `execution_enabled=True`、并且把输出接入 final_decision /
  projection_orchestrator_v2，就会立即变成 production_promotion 风险

### 2.2 与其他 RISK 的差异

| 维度 | RISK-1 / RISK-2 / RISK-6 / RISK-8 / RISK-9 | RISK-10 |
|---|---|---|
| 当前是否已违规 | ✅ 已存数月违规（HIGH） | ❌ 当前 CLEAN |
| 修复目标 | 改代码消除违规 | **预防性 doc-lock + import test** |
| 实施成本 | 高（涉及 active path 改造） | 低（doc + test）|
| Step 12 commit 体量 | 大 | 小（~50–100 行 docstring + ~150 行 test） |

### 2.3 为何仍需在 Step 12 修复

- 06–07D 契约已固定；任何未来误开都会**立即**违规
- 不加 contract test，Step 12+ 之后的开发者可能不读 09/10/11G 文档就改
  promotion caller
- doc-lock 是最便宜的契约执行手段

---

## 3. 违反风险对应的 contract

| contract | 章节 | 风险点 |
|---|---|---|
| 06 三系统独立原则 | §6 三系统正确关系 / §7 第 6 条 "final report 改写任一系统结果" | 如果 promotion 启用并接 active path，会让规则池升级直接改写在线判断 |
| 07A 推演 contract | §3.2 禁止读取 hard / forced / required decision / §5 禁止输出 hard / forced / required / production_promotion | promotion 输出不得作为 projection 输入 |
| 07B 否定 contract | §3.2 / §5 同上 | promotion 输出不得作为 exclusion 输入 |
| 07C 置信度 contract | §11 禁止数据流 `confidence_result → hard / forced decision` | promotion 不得触发 confidence-driven hard / forced |
| 07D final report contract | §5 禁止 `production_promotion` / `_PROTECTION_LAYER_CONNECTED` / `hard_exclusion` / `forced_exclusion` / `required_decision` / `trading_action` / §11 禁止 `final_report → trading_action` | promotion 输出不得回流到 final_report |
| 09 module inventory | RISK-10 LOW_RISK | doc-lock 是修复手段 |
| 10 §6 FIX_REQUIRED RISK-10 | "documentation-lock 为 offline-only" | 11G 范畴 |

---

## 4. promotion cluster 定义

### 4.1 现有文件清单

| path | current role | active_or_offline | risk | recommended_lock |
|---|---|---|---|---|
| `services/active_rule_pool_promotion.py` (386 行) | 从规则池 calibration 结果产出 promotion policy report；输出 `kind: "active_rule_pool_promotion_report"` + 4 类决策（promote_candidate / keep_active_observe / hold_back / do_not_promote） | offline | LOW | doc-lock + safety fields + import test |
| `services/promotion_adoption_gate.py` (375 行) | 从 promotion 输出产出 conservative production adoption handoff；输出 `kind: "promotion_adoption_handoff"` + 4 类决策（production_candidate / keep_in_execution_bridge / hold_for_more_evidence / not_ready_for_adoption） | offline | LOW | doc-lock + safety fields + import test |
| `services/promotion_execution_bridge.py` (242 行) | 从 promotion + adoption gate 输出产出 execution-ready bridge artifact；输出 `kind: "promotion_execution_bridge"` + `execution_enabled: False`（默认）+ promotable / held_back / execution_bridge rules | offline | LOW（最关键 —— `execution_enabled` flag 是潜在启用入口） | doc-lock + safety fields + import test + **assert execution_enabled==False** test |
| `tests/test_active_rule_pool_promotion.py` | 测试 promotion report | test infra | — | 无需改动 |
| `tests/test_promotion_adoption_gate.py` | 测试 adoption gate | test infra | — | 无需改动 |
| `tests/test_promotion_execution_bridge.py` | 测试 execution bridge | test infra | — | 11G 加 contract enforcement test 时**新增独立**测试文件，不混入这里 |
| `scripts/*promotion*.py` | not found（grep 结果空） | — | — | — |
| `services/anti_false_exclusion_dashboard.py` 含 `production_promotion` / `_PROTECTION_LAYER_CONNECTED` 字符串 | grep 命中；具体语义需 Step 12 spot-check 是否为 dashboard 显示用（不构成主动设值）；不属 promotion 模块自身 | offline / display | UNKNOWN | Step 12 spot-check 后再决定是否纳入 11G test 范围 |

### 4.2 active importers（grep 结果）

只有 1 个 active service import promotion 模块：

- `services/avgo_1000day_training.py`（offline 训练）

**无**任何 `app.py` / `ui/` / `services/projection_*` /
`services/exclusion_*` / `services/main_projection_layer.py` /
`services/final_decision.py` / `services/confidence_evaluator.py`（11C 待建）
import promotion 模块。

### 4.3 production_promotion / _PROTECTION_LAYER_CONNECTED 字符串出现地

`grep "production_promotion\|promotion_gate\|_PROTECTION_LAYER_CONNECTED"` 命中：

- `services/anti_false_exclusion_dashboard.py`（1 处；显示用 vs 主动设值待 Step 12 详查）
- 多个 `tests/test_continuous_smoothing*` / `tests/test_regime_*` /
  `tests/test_protection_layer_diagnostics*` / `tests/test_replay_*` 等
  ——大部分是**断言不存在**的 contract test 痕迹（即测试 forbidden output 的
  存在）
- `services/protection_layer_diagnostics.py:18-23`（11G 不动；RISK-5 已 spec-lock，
  detected hard_gate / required_field / protection_layer_connected_for_gate
  全部 always False）

> Step 12 修 RISK-10 时**不**改 anti_false_exclusion_dashboard.py 与
> protection_layer_diagnostics.py（属 RISK-5 范畴，已 CLEAN）。

---

## 5. Offline-only 允许用途

修复后 promotion 模块**允许**用于：

- ✅ **离线回测后分析**：1000 天训练、historical replay 的事后规则池演化
- ✅ **calibration report**：rule_calibration_decision == "retain" 等评估
- ✅ **rule promotion research**：哪些规则在哪些 regime 下表现稳定
- ✅ **candidate evaluation report**：promote_candidate / keep_active_observe /
  hold_back / do_not_promote 分类
- ✅ **human review checklist**：production_candidate 给人工 review 看，不
  自动 onboard
- ✅ **contract diagnostic report**：作为 Step 13 regression 的 evidence
- ✅ **historical experiment summary**：固化为 docs / offline logs / review
  report 中的引用

这些用途的输出**仅**进入 `docs/` / 离线 `logs/` / human review report，不进入
在线判断。

---

## 6. Online 禁止用途

修复后 promotion 输出**禁止**影响以下任一字段：

| 字段路径 | 系统 |
|---|---|
| `projection_result` 任一字段 | projection (07A) |
| `most_likely_state` / `ranked_states` / `state_scores` | projection |
| `exclusion_result` 任一字段 | exclusion (07B) |
| `most_unlikely_state` / `ranked_unlikely_states` / `state_impossibility_scores` | exclusion |
| `confidence_result` 任一字段 | confidence (07C) |
| `projection_confidence` / `exclusion_confidence` / `combined_confidence` | confidence |
| `final_report` / `final_direction` / `final_confidence` / `combined_user_summary` | final report (07D) |
| `trading_action` / `buy` / `sell` / `hold` / `simulated_trade` / `no_trade` | 不属任一系统 |
| `hard_exclusion` / `forced_exclusion` / `required_decision` | 全契约禁止 |
| `production_promotion` / `_PROTECTION_LAYER_CONNECTED` | 07D §5 显式禁止 |

任一回写 / 触发 / 间接驱动 → 视为违反 contract。

---

## 7. Documentation lock 设计

### 7.1 Module-level docstring

Step 12 在 3 个 promotion 模块顶部加统一 docstring 标注：

```python
"""<original module title>

OFFLINE_ONLY:
This module is for research / calibration / validation only.
It must NOT be imported by online projection, exclusion, confidence,
final report, UI, trading, or production promotion paths.

Allowed callers:
- offline training pipelines (e.g. services/avgo_1000day_training.py)
- offline scripts under scripts/
- test files under tests/

Forbidden callers (enforced by tests/test_promotion_offline_only_boundary.py):
- app.py
- ui/*
- services/projection_*  (any projection-side module)
- services/exclusion_layer.py / services/anti_false_exclusion_*
- services/confidence_evaluator.py (when 11C lands)
- services/final_decision.py
- services/main_projection_layer.py
- services/projection_orchestrator_v2.py
- services/home_terminal_orchestrator.py

Output safety contract:
- output dict MUST include {"mode": "offline_only", "online_safe": False, ...}
- output dict MUST NOT include trading_action / buy / sell / hold /
  hard_exclusion / forced_exclusion / required_decision /
  production_promotion / _PROTECTION_LAYER_CONNECTED.
- execution_enabled flag (in promotion_execution_bridge) MUST default to False
  and MUST NOT be set True by any active caller.

See:
- tasks/record_06_three_system_independence_principle.md
- tasks/record_07d_final_report_aggregator_contract.md
- tasks/record_11g_promotion_offline_only_documentation_lock_design.md
"""
```

### 7.2 Doc-lock 原则

- doc-lock 是**边界声明**，不改变功能（行为不变）
- contract test（§13）会读取 docstring 验证 `OFFLINE_ONLY` 关键字存在
- 未来开发者修改 promotion 模块时，doc-lock 是**第一道警告**

---

## 8. Import guard / path test 设计

Step 12 加 `tests/test_promotion_offline_only_boundary.py`，包含以下静态扫描
测试：

| 测试 | 验证内容 |
|---|---|
| `test_app_does_not_import_promotion_modules` | grep `app.py` 不含 `from services.active_rule_pool_promotion` / `from services.promotion_adoption_gate` / `from services.promotion_execution_bridge` |
| `test_ui_does_not_import_promotion_modules` | grep `ui/*.py` 不含上述 import |
| `test_active_projection_does_not_import_promotion_modules` | grep `services/projection_*.py` / `services/main_projection_layer.py` / `services/primary_*.py` / `services/peer_adjustment.py` / `services/historical_probability.py` 不含上述 import |
| `test_exclusion_does_not_import_promotion_modules` | grep `services/exclusion_layer.py` / `services/anti_false_exclusion_*.py` / `services/big_up_contradiction_card.py` / `services/big_down_tail_warning.py` 不含上述 import |
| `test_confidence_does_not_import_promotion_modules` | grep `confidence_engine.py` / `services/contract_calibration_inputs.py` / `services/active_rule_pool_calibration.py` / `services/exclusion_reliability_review.py` / `services/projection_three_systems_renderer.py` / `services/confidence_evaluator.py`（11C 接入后存在）不含上述 import |
| `test_final_report_does_not_import_promotion_modules` | grep `services/final_decision.py` / `services/projection_entrypoint.py` / `services/projection_three_systems_renderer.py` / `services/projection_narrative_renderer.py` / `services/predict_summary.py` / `services/ai_summary.py` 不含上述 import |
| `test_predict_py_does_not_import_promotion_modules` | grep `predict.py` 不含上述 import（与 11E predict.py legacy wrapper 配合） |
| `test_promotion_modules_do_not_import_trading_api` | grep `services/active_rule_pool_promotion.py` / `services/promotion_adoption_gate.py` / `services/promotion_execution_bridge.py` 不含 LongBridge / 任何 trading SDK / `from services.openai_client` |
| `test_promotion_modules_do_not_import_active_projection` | promotion 模块不应**反向**依赖 active projection / exclusion / confidence / final_decision（避免循环回流） |

实现策略：用 `pathlib` + 简单字符串扫描；不要求 AST 解析。

---

## 9. Output schema lock 设计

### 9.1 修复后 promotion 模块输出必须包含

```python
{
    "kind": "<existing kind>",
    "ready": <existing>,

    # ── 既有业务字段（保留） ──
    "total_rules": ...,
    "decision_counts": {...},
    ...

    # ── 新增 safety fields（11G 新增） ──
    "mode": "offline_only",
    "online_safe": False,
    "may_affect_active_prediction": False,
    "may_affect_active_exclusion": False,
    "may_affect_active_confidence": False,
    "may_affect_final_report": False,
    "may_affect_trading": False,
    "requires_human_review": True,

    # ── 既有 ──
    "summary": "...",
    "warnings": [...]
}
```

### 9.2 禁止字段（程序级 + test 强制）

```jsonc
// ❌ 不允许
{
  "production_promotion": true,
  "_PROTECTION_LAYER_CONNECTED": true,
  "hard_exclusion": true,
  "forced_exclusion": true,
  "required_decision": true,
  "trading_action": "...",
  "buy": ..., "sell": ..., "hold": ...,
  "simulated_trade": {...},
  "no_trade": true,
  "final_report_mutation": {...},
  "modified_projection": {...},
  "modified_exclusion": {...},
  "modified_confidence": {...}
}
```

### 9.3 `execution_enabled` 特别处理

`services/promotion_execution_bridge.py:15` 当前默认 `execution_enabled: False`。
Step 12 加测试：

- `test_promotion_execution_bridge_default_execution_enabled_is_false`：
  断言 `_empty_report()` 与默认 caller 路径下 `execution_enabled == False`
- `test_promotion_execution_bridge_documentation_forbids_active_caller`：
  静态扫描 docstring 含 "MUST NOT be set True by any active caller" 类约束

如果未来某个 PR 想启用 execution，必须**显式**修改本 11G 文档 + Step 14
cleanup 后的独立 launch review，**不**通过简单改 default 实现。

---

## 10. 与 3R-5 / 3R-6 的关系

> **明确**：promotion offline-only lock **不解锁** 3R-5 / 3R-6。

- 即使某个 offline promotion report 显示 `decision == "production_candidate"`，
  也**不**等于"该规则已通过 3R-5 / 3R-6 入场标准"
- 进入 3R-5 / 3R-6 必须：
  1. Step 12 boundary enforcement 全部完成（11A–11G + 各自 fix commit）
  2. Step 13 regression 通过
  3. Step 14 cleanup 完成
  4. **另开** launch review 文档（非本 11G 范畴）
  5. 显式更新 06 / 07A–D contract（如需要）
- 任何借 promotion 输出"绕过 3R-5 / 3R-6 launch review"的 PR，**默认 reject**

---

## 11. 与 cleanup / quarantine 的关系

> **明确**：RISK-10 **不是** cleanup。

- 11G 不删除任何 promotion 模块
- 11G 不移动任何 promotion 模块
- 11G 仅加 doc-lock + safety fields + import/path tests
- 如果未来确认 promotion cluster 完全无用（即使 offline 也不再产 report），
  由 Step 14 cleanup/quarantine 独立处理；属另一次提案

> **绝对禁止**：在 11G fix commit 中删除 promotion 模块（即使 grep 显示
> avgo_1000day_training 已不再 import）。

---

## 12. 最小代码修改设计

> 本节**只描述设计**，Step 12 才实施。

### 12.1 改动范围

| 文件 | 动作 |
|---|---|
| `services/active_rule_pool_promotion.py` | 加 `OFFLINE_ONLY` docstring + 输出加 safety fields |
| `services/promotion_adoption_gate.py` | 同上 |
| `services/promotion_execution_bridge.py` | 同上 + 文档显式标 `execution_enabled` 不允许 active caller 启用 |
| `tests/test_promotion_offline_only_boundary.py` | **新增**测试文件，含 §8 + §13 的所有 contract enforcement test |
| `tests/test_active_rule_pool_promotion.py` / `tests/test_promotion_adoption_gate.py` / `tests/test_promotion_execution_bridge.py` | **微修**：补充对新 safety fields 的 schema 断言 |
| 其他模块 | **不动** |

### 12.2 改造步骤

1. 先加 contract test（red baseline）
2. 加 docstring 到 3 个 promotion 模块
3. 在 `_empty_report()` 等输出 helper 中加 safety fields
4. 修改 builder function 在最终 return 时合入 safety fields
5. 改写 3 个既有 test 的 schema 断言（兼容新字段）

### 12.3 估计行数

- 3 个模块 × ~30 行 docstring + ~10 行 safety fields = **~120 行**
- 新 test 文件 ~150 行
- 既有 test 微改 ~30 行
- Step 12 single fix commit ~300 行

---

## 13. Contract enforcement tests 设计

> 本节**只描述测试设计**，Step 12 才新增测试代码。

### 13.1 必须新增的测试（`tests/test_promotion_offline_only_boundary.py`）

#### Doc-lock 类
- `test_active_rule_pool_promotion_marked_offline_only`：扫描模块 docstring 含 `OFFLINE_ONLY` 关键字 + "MUST NOT be imported by online" 类约束
- `test_promotion_adoption_gate_marked_offline_only`：同上
- `test_promotion_execution_bridge_marked_offline_only`：同上

#### Import-guard 类
- `test_app_does_not_import_promotion_modules`
- `test_ui_does_not_import_promotion_modules`
- `test_active_projection_does_not_import_promotion_modules`（projection_orchestrator_v2 / main_projection_layer / primary_20day_analysis / peer_adjustment / historical_probability / projection_entrypoint 等）
- `test_exclusion_does_not_import_promotion_modules`（exclusion_layer / anti_false_exclusion_audit / big_up_contradiction_card / big_down_tail_warning）
- `test_confidence_does_not_import_promotion_modules`（confidence_evaluator [11C 接入后存在] / contract_calibration_inputs / projection_three_systems_renderer / exclusion_reliability_review）
- `test_final_report_does_not_import_promotion_modules`（final_decision / projection_three_systems_renderer / projection_narrative_renderer / predict_summary / ai_summary）
- `test_predict_py_does_not_import_promotion_modules`
- `test_home_terminal_orchestrator_does_not_import_promotion_modules`
- `test_promotion_modules_do_not_import_trading_api`
- `test_promotion_modules_do_not_import_openai_client`
- `test_promotion_modules_do_not_import_active_projection`

#### Output safety 类
- `test_promotion_outputs_offline_only_safety_fields`：对 3 个 builder 各跑一次（mock 输入），断言输出 dict 含 `mode == "offline_only"` / `online_safe == False` / 5 个 `may_affect_*` 全 false / `requires_human_review == True`
- `test_promotion_outputs_no_hard_forced_required`：断言输出 dict 不含 `hard_exclusion` / `forced_exclusion` / `required_decision`
- `test_promotion_outputs_no_trading_action`：不含 `trading_action` / `buy` / `sell` / `hold` / `simulated_trade` / `no_trade`
- `test_promotion_does_not_set_protection_layer_connected`：不含 `_PROTECTION_LAYER_CONNECTED == True`
- `test_promotion_does_not_set_production_promotion`：不含 `production_promotion == True`
- `test_promotion_does_not_introduce_modified_or_overridden_fields`：不含 `modified_*` / `overridden_*` / `corrected_*`
- `test_promotion_execution_bridge_default_execution_enabled_is_false`：断言 `_empty_report()` 与默认 caller 路径下 `execution_enabled == False`
- `test_promotion_execution_bridge_documentation_forbids_active_caller`：扫描 docstring 含 "MUST NOT be set True by any active caller"

### 13.2 测试不允许的内容

- 测试**不**应允许 promotion 模块 doc-lock 缺失
- 测试**不**应允许 active path import promotion 模块
- 测试**不**应允许 promotion 输出含禁止字段
- 测试**不**应允许 `execution_enabled` 默认为 True

---

## 14. 不允许的修复方式

以下修复方式**不**符合 contract，Step 12 实施时**禁止**：

1. **不**允许删除 promotion 模块（保留 offline 工具）
2. **不**允许把 promotion 接入 active path
3. **不**允许把 promotion result 传给 projection / exclusion / confidence /
   final_report / trading
4. **不**允许启用 `production_promotion: True`
5. **不**允许设置 `_PROTECTION_LAYER_CONNECTED == True`
6. **不**允许 promotion 输出 `hard_exclusion` / `forced_exclusion` /
   `required_decision`
7. **不**允许 promotion 输出 `trading_action` / `buy` / `sell` / `hold`
8. **不**允许 promotion 模块 import LongBridge / 任何 trading SDK / openai_client
9. **不**允许在 11G fix commit 内顺手修 RISK-1 / RISK-2 / RISK-3 / RISK-7 /
   RISK-8 / RISK-9
10. **不**允许 cleanup 与 doc-lock 混 commit
11. **不**允许 large rewrite（仅 docstring + safety fields；不重构 builder
    内部逻辑）
12. **不**允许进入 3R-5 / 3R-6
13. **不**允许复活 continuous_smoothing 作为 "offline-promotion-friendly" 替身
14. **不**允许把 `execution_enabled` 默认改为 True
15. **不**允许通过新增 `bypass_offline_lock=True` / `unsafe_active_mode=True`
    等"逃生口"入参绕过 lock

---

## 15. Step 12 实施顺序建议

> Step 12 才允许执行；本轮**不**实施。

### 15.1 推荐顺序（commit-per-fix 内部子步骤）

1. **grep 复核 promotion 相关文件**
   - `find services/ scripts/ -name "*promotion*"`
   - `grep -rn "production_promotion\|promotion_gate\|_PROTECTION_LAYER_CONNECTED"`
   - 确认与 §4 一致；如有新文件，加入 §4

2. **新增 `tests/test_promotion_offline_only_boundary.py`（failing baseline）**
   - 加 §13.1 列出的 20+ 测试
   - 部分测试当前 fail（红灯）；部分 pass（已合规的部分，例如 active path
     当前已不 import promotion）

3. **加 `OFFLINE_ONLY` docstring**
   - `services/active_rule_pool_promotion.py`
   - `services/promotion_adoption_gate.py`
   - `services/promotion_execution_bridge.py`
   - 跑 doc-lock 类测试转绿

4. **加 safety fields**
   - 修改 3 个模块的 `_empty_report()` 与 builder return 字典，加 6 个
     `mode` / `online_safe` / `may_affect_*` / `requires_human_review` 字段
   - 跑 output safety 类测试转绿

5. **微修既有 promotion test**
   - `tests/test_active_rule_pool_promotion.py` / `tests/test_promotion_adoption_gate.py`
     / `tests/test_promotion_execution_bridge.py` 的 schema 断言加新字段
   - 跑既有 promotion test 转绿

6. **跑全量 pytest**
   - 期待无回归

7. **手动 spot-check**
   - 确认 `services/avgo_1000day_training.py` 仍可调 promotion；输出含新 safety
     fields

8. **独立 commit**
   - commit message：`fix(boundary): RISK-10 lock promotion modules offline-only`
   - 单 commit；**不**混合任何 cleanup / 不顺手改 RISK-1/2/3/7/8/9

### 15.2 不允许 inside Step 12 commit 的内容

- **不**改 `services/avgo_1000day_training.py`（仅唯一 active offline caller，保持现状）
- **不**改 `services/anti_false_exclusion_dashboard.py` / `protection_layer_diagnostics.py`（属 RISK-5 范畴，已 CLEAN）
- **不**改 `_empty_report()` 内的业务字段（`kind` / `ready` / `decision_counts` / `rules` / `summary` / `warnings` 全保留）
- **不**重构 promotion 内部 logic
- **不**改其他 RISK 涉及模块

---

## 16. 回滚策略

### 16.1 失败模式

如果在 Step 12 实施过程中：

- import-guard 测试因 `services/avgo_1000day_training.py` 仍调 promotion 而被
  误判（实际是合法 offline caller）
- 既有 promotion test 因 schema 加字段而失败（兼容性问题）
- 某个 dashboard / display 模块意外 import promotion（应在 Step 12 之前已 audit
  清楚）

### 16.2 回滚原则

> **不**回退到无 doc-lock / 无 safety fields 的旧实现。

正确的回滚序列：

1. 保留 doc-lock + safety fields（核心契约要求）
2. 调整 import-guard 测试范围：把 `services/avgo_1000day_training.py` 加入
   **allowed offline callers** 白名单（test fixture 中显式列出）
3. 微调既有 promotion test 的兼容性断言；**不**移除新 safety fields
4. 不允许把 `production_promotion` / `_PROTECTION_LAYER_CONNECTED` 等禁止字段
   恢复到输出
5. 不允许悄悄把 `execution_enabled` 默认翻为 True

### 16.3 不允许的"回滚捷径"

- **不**允许悄悄删除 doc-lock 关键字（如改 `OFFLINE_ONLY` → `INFO`）
- **不**允许测试中 substring 检测改成"宽松"模糊匹配
- **不**允许给 promotion 模块加 `bypass_offline_lock=True` 入参
- **不**允许 `git commit --amend` 隐藏违规

---

## 17. 严守边界

本轮**只是设计**：

- 未改代码
- 未新增测试
- 未删文件
- 未移动文件
- 未写 DB
- 未改 DB schema
- 未跑 replay
- 未跑 validation
- 未处理 untracked / DB backup / stash / .claude/worktrees/
- 未进入 3R-5 / 3R-6
- 未新增任何 candidate
- 未复活 continuous_smoothing
- 未实际修改 promotion 模块（保留给 Step 12）
- 未触碰 RISK-1 / RISK-2 / RISK-3 / RISK-7 / RISK-8 / RISK-9
  （各自 11A / 11B / 11C / 11D / 11E / 11F 设计）

本设计的修改路径：任何对 §4 promotion cluster、§7 doc-lock 文本、§8 import
guard 范围、§9 schema fields、§13 测试设计、§15 实施顺序的调整，都必须以
**显式更新本文件**的方式提出。
