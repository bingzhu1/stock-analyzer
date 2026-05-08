# 13记录：Post-fix Regression / Boundary Review

> 本记录是 **Step 13 回归与边界复核**：Step 12 全部边界修复（11A–11G + 11E
> 的 X1–X5）入 main 后的统一验证。
>
> 本轮**只做回归检查 + 写报告**：未改业务代码、未新增功能、未删文件、
> 未移动文件、未写 DB、未跑 replay / real validation、未 commit / push、
> 未默认迁移 `run_predict` 到 V2、未接 UI / app.py / command bar /
> contract_replay_writer、未启动 Step 14 cleanup、未进入 3R-5 / 3R-6、
> 未顺手碰其他 RISK。

---

## 1. Step 13 目的

Step 13 是 Step 12 全部边界修复后的**回归与边界复核**：

- **不**是新功能
- **不**是 cleanup（cleanup 属 Step 14）
- **不**是 3R-5 / 3R-6（被 §9 显式禁止）
- **不**是 replay / real validation 全量
- 是 **focused / predict-related / full pytest** 三层回归 +
  **active caller / artifact / default-path** 静态与运行时 spot-check

签收条件：所有命令 0 errors + 所有 boundary 不变量满足。

---

## 2. 当前 main 状态

| 项 | 状态 |
|---|---|
| main 最新 commit | **`3ecf78c docs(contract): record 12e x5 predict legacy wrapper split completion checkpoint`** |
| 06 / 07A–E / 08 / 09 / 10 / 11A–11H | ✅ 全部入 main |
| 12A / 12B / 12C-A / 12D / 12C-B / 12F / 12G | ✅ 全部入 main |
| 12E-X1 / X2 / X3 / X4-A / X4-B / X4-C / X5 | ✅ 全部入 main |
| `run_predict` 默认路径仍 legacy（`v2_payload` 缺省 = `None`） | ✅ 锁定 |
| `v2_payload` / bridge 仍 explicit opt-in | ✅ 锁定 |
| Step 14 cleanup | ⏳ 尚未开始（不在 Step 13 范畴） |
| 3R-5 / 3R-6 | ❌ 显式禁止进入 |

12E 范畴内已合并的最近 8 个 boundary commit：

```
3ecf78c docs(contract): record 12e x5 predict legacy wrapper split completion checkpoint
c125f91 feat(boundary): RISK-8 add isolated v2_payload-to-legacy bridge          # X4-C
89de6a6 fix(boundary): RISK-8 wire v2_payload opt-in adapter into run_predict    # X4-B
03dfbda feat(boundary): add v2-to-predict legacy compatibility adapter           # X4-A
e80e905 fix(boundary): RISK-8 wire summary from final_report                     # X3
e666943 fix(boundary): RISK-8 wire final_confidence from confidence_result       # X2
689183f docs(boundary): mark predict.py as legacy wrapper                        # X1
2ee315c fix(boundary): RISK-10 lock promotion modules offline-only               # 12G
```

---

## 3. 回归命令与结果

### 3.1 git status（pre-test）

```
$ git status
On branch claude/optimistic-gauss-b20a8e
Your branch is up to date with 'origin/main'.

Untracked files:
        logs/prediction_log.jsonl

nothing added to commit but untracked files present (use "git add" to track)
```

✅ 仅一个 standing untracked artifact (`logs/prediction_log.jsonl`)，未被 staged。

### 3.2 Focused boundary tests（14 个文件）

```
$ pytest \
    tests/test_projection_exclusion_decoupling_boundary.py \
    tests/test_final_decision_aggregator_purification_boundary.py \
    tests/test_confidence_evaluator.py \
    tests/test_confidence_result_wiring_boundary.py \
    tests/test_cutoff_guard.py \
    tests/test_memory_feedback_cutoff_guard_boundary.py \
    tests/test_ai_summary_boundary.py \
    tests/test_promotion_offline_only_boundary.py \
    tests/test_predict_legacy_wrapper_boundary.py \
    tests/test_predict_x2_confidence_wiring_boundary.py \
    tests/test_predict_x3_summary_wiring_boundary.py \
    tests/test_predict_legacy_adapter.py \
    tests/test_predict_x4b_v2_payload_opt_in_boundary.py \
    tests/test_predict_legacy_v2_bridge.py \
    -q
=> 265 passed in 1.22s
```

✅ **265 / 265 passed**。所有 11A / 11B / 11C / 11D / 11E / 11F / 11G boundary
contract test 全绿。

### 3.3 Predict-related tests

```
$ pytest \
    tests/test_predict.py \
    tests/test_run_predict_contract_alignment.py \
    tests/test_confidence_system_contract_fields.py \
    tests/test_exclusion_system_contract_fields.py \
    tests/test_final_projection_contract_fields.py \
    tests/test_peer_adjustment_contract_fields.py \
    tests/test_primary_projection_contract_fields.py \
    tests/test_simulated_trade_contract_fields.py \
    -q
=> 156 passed, 39 subtests passed in 0.83s
```

✅ **156 / 156 passed**（含 39 subtests）。`run_predict` 全 schema / contract
检查全绿。

### 3.4 Full pytest

```
$ pytest -q
=> 3252 passed, 10 skipped, 26 warnings, 94 subtests passed in 12.54s
```

✅ **3252 / 3252 passed, 10 skipped, 0 failed**（warnings 全部来自 ai_*
parser 的预期 OPENAI_API_KEY 未配置 / non-JSON response 测试用例，不是 regression
信号）。

### 3.5 `scripts/check.sh`

```
$ bash scripts/check.sh
All compile checks passed.
```

✅ `app.py` / `scanner.py` / `predict.py` / `encoder.py` / `matcher.py` /
`feature_builder.py` / `data_fetcher.py` 以及 8 个 services / 3 个 ui 模块
全部 `python3 -m py_compile` 通过。

### 3.6 测试总数对比（baseline 演进）

| 阶段 | full pytest passed |
|---|---|
| Step 12A 启动前 | 2998 |
| 12A → 12G 入 main 后 | ≈3160 |
| 12E-X1 → X3 入 main 后 | ≈3185 |
| 12E-X4-A 入 main 后 | ≈3200 |
| 12E-X4-B 入 main 后 | 3218 |
| 12E-X4-C 入 main 后 | 3252 |
| **Step 13（current）** | **3252** |

12E-X5 仅新增 design checkpoint 文档（`tasks/record_12e_x5_*.md`），未改代码，
未新增测试，所以测试总数与 12E-X4-C 一致 = 3252。

---

## 4. Boundary review 结果

按 11H §10 / §7 完成标准逐条复核。所有项**通过**。

| # | invariant | 验证方式 | 结果 |
|---|---|---|---|
| 1 | projection 不读 `exclusion_result`（11A） | `tests/test_projection_exclusion_decoupling_boundary.py` 全绿 | ✅ |
| 2 | exclusion_result 独立存在；不被回写 projection | 11A boundary tests + 11B `non_mutation_confirmations.exclusion_result_mutated == False` | ✅ |
| 3 | `final_decision` aggregator 不改写 `final_direction`（11B） | `tests/test_final_decision_aggregator_purification_boundary.py` 全绿 | ✅ |
| 4 | `final_decision` aggregator 不重算 `final_confidence`（11B） | 11B boundary tests + `final_confidence` source attribution lookup | ✅ |
| 5 | `confidence_result` 由独立 evaluator 生成（11C-A） | `tests/test_confidence_evaluator.py` 全绿 | ✅ |
| 6 | `confidence_result` 接入 V2 path / final_decision / renderer（11C-B） | `tests/test_confidence_result_wiring_boundary.py` 全绿 | ✅ |
| 7 | confidence_evaluator 段是 read-only display | 11C-B boundary tests | ✅ |
| 8 | memory feedback / preflight 等 cutoff guard 生效（11D） | `tests/test_cutoff_guard.py` + `tests/test_memory_feedback_cutoff_guard_boundary.py` 全绿 | ✅ |
| 9 | `ai_summary` 默认 disabled（11F） | `tests/test_ai_summary_boundary.py` 全绿（`enable_ai_summary=False` → status `"disabled"`） | ✅ |
| 10 | `ai_summary` source attribution / post-check 生效 | 11F boundary tests（`refused_missing_sources` / `refused_policy_violation` / `llm_unavailable` 三状态） | ✅ |
| 11 | promotion 三模块 OFFLINE_ONLY（11G） | `tests/test_promotion_offline_only_boundary.py` 全绿 | ✅ |
| 12 | promotion 输出含 6 safety fields | 11G boundary tests | ✅ |
| 13 | promotion 不被 active path import | 11G boundary tests + §5 active-caller static review | ✅ |
| 14 | `predict.py` 是 legacy compatibility wrapper（11E-X1） | `tests/test_predict_legacy_wrapper_boundary.py` 全绿；`wrapper_kind == "legacy_predict_wrapper"` | ✅ |
| 15 | `predict.py` 顶层 `final_confidence` 来自 confidence_result（11E-X2） | `tests/test_predict_x2_confidence_wiring_boundary.py` 全绿；缺 → `"unknown"` | ✅ |
| 16 | `predict.py` 顶层 `prediction_summary` 来自 final_report.combined_user_summary（11E-X3） | `tests/test_predict_x3_summary_wiring_boundary.py` 全绿 | ✅ |
| 17 | `services/predict_legacy_adapter.py` 是 standalone pure mapping（11E-X4-A） | `tests/test_predict_legacy_adapter.py` 全绿 | ✅ |
| 18 | `run_predict(..., v2_payload=None)` byte-identical 与 X3 baseline（11E-X4-B） | `tests/test_predict_x4b_v2_payload_opt_in_boundary.py` 全绿 + 运行时 spot-check（§5） | ✅ |
| 19 | `v2_payload` 是 explicit opt-in；非 dict 不崩溃 | X4-B boundary tests | ✅ |
| 20 | `services/predict_legacy_v2_bridge.py` 是 isolated helper（11E-X4-C） | `tests/test_predict_legacy_v2_bridge.py` 全绿（34 tests） | ✅ |
| 21 | bridge 不接 UI / app.py / command bar / replay writer | X4-C `ActiveCallerStaticImportTests` 全绿 + §5 grep | ✅ |
| 22 | `predict.py` 模块级**不** import V2 orchestrator / promotion / continuous_smoothing / ai_summary | X4-C `PredictRunPredictDefaultStaticReaffirmTests`（4 tests）+ §5 grep | ✅ |
| 23 | active path **不** import frozen `continuous_smoothing*` | §5 grep | ✅ |
| 24 | 输出**不**含 trading / hard / forced / required / production_promotion / `_PROTECTION_LAYER_CONNECTED` / `*_mutation` / `modified_*` / `corrected_*` | 11B / 11E / 11F / 11G boundary tests + adapter forbidden_fields 防御 | ✅ |
| 25 | confidence_evaluator / final_decision / ai_summary / 各 wrapper 输出含 `non_mutation_confirmations` / `source_attribution` / `cutoff_guard`（按归属） | 各对应 boundary tests 全绿 | ✅ |

**结论：25 / 25 invariants 通过**。Step 12 全部 boundary 修复落地无回归。

---

## 5. Active caller static review

通过 grep + AST 静态扫描验证以下文件**未**违反 12E 边界：

| 检查项 | 命令 | 结果 |
|---|---|---|
| `v2_payload=` 是否被 active callers 传入 | `grep -n "v2_payload=" app.py ui/*.py services/projection_orchestrator.py services/contract_replay_writer.py scripts/run_e2e_loop.py` | ✅ none found |
| `services.predict_legacy_v2_bridge` 是否被 active callers import | `grep -rn "predict_legacy_v2_bridge" app.py ui/ services/projection_orchestrator.py services/contract_replay_writer.py scripts/run_e2e_loop.py` | ✅ none found |
| `continuous_smoothing` 是否被 active path import | `grep -rn "continuous_smoothing" app.py ui/ services/projection_orchestrator.py services/projection_orchestrator_v2.py services/contract_replay_writer.py services/main_projection_layer.py services/final_decision.py services/confidence_evaluator.py scripts/run_e2e_loop.py predict.py` | ✅ none found |
| promotion 三模块是否被 active path import | `grep -rEn "services\.(active_rule_pool_promotion\|promotion_adoption_gate\|promotion_execution_bridge)" app.py ui/ services/projection_orchestrator.py services/projection_orchestrator_v2.py services/contract_replay_writer.py services/main_projection_layer.py services/final_decision.py services/confidence_evaluator.py services/ai_summary.py predict.py` | ✅ none found |

被验证的 active callers（共 13 个文件）：

- `app.py`
- `ui/predict_tab.py` / `ui/command_bar.py` / `ui/history_tab.py` /
  `ui/home_tab.py` / `ui/scan_tab.py` / `ui/research_tab.py` /
  `ui/review_tab.py` / `ui/inspect_tab.py` / `ui/research_tab.py`（含全部 9 个 ui tabs）
- `services/projection_orchestrator.py`（旧 V1 orchestrator，仍 in main，仅 V2 内部 import + tests）
- `services/contract_replay_writer.py`（offline replay 写入；未传 v2_payload）
- `scripts/run_e2e_loop.py`（live e2e；未传 v2_payload）

### 5.1 `predict.py` default-path 运行时 spot-check

```python
import importlib, predict as p
importlib.reload(p)

# default：不传 v2_payload 也不传 None
r1 = p.run_predict(None, research_result=None, symbol='AVGO')
# wrapper_kind          = legacy_predict_wrapper
# legacy_compatibility  = True
# v2_adapter_used in r? = False     ← 未触发 adapter
# final_bias            = unavailable
# final_confidence      = unknown   ← X2 contract（缺 confidence_result → unknown）

# v2_payload=None：与默认相同
r2 = p.run_predict(None, research_result=None, symbol='AVGO', v2_payload=None)
# v2_adapter_used in r? = False     ← 仍未触发

# v2_payload=<dict>：opt-in 路径
r3 = p.run_predict(None, research_result=None, symbol='AVGO', v2_payload={
    'final_decision': {'final_direction': '偏多'},
    'confidence_result': {'combined_confidence': {'level': 'medium'}},
    'final_report': {'combined_user_summary': 'spot-check summary'},
})
# v2_adapter_used  = True           ← X4-B 标记
# final_bias       = 偏多            ← 来自 final_decision.final_direction
# final_confidence = medium          ← 来自 confidence_result.combined_confidence.level
# prediction_summary[:30] = "spot-check summary"
# v2_adapter_result.adapter_kind = v2_to_predict_legacy_adapter
```

✅ 默认路径无 `v2_adapter_used`；显式 dict opt-in 才出现 `v2_adapter_used = True`
+ adapter overlay。

### 5.2 `bridge` 运行时 spot-check

```python
from services.predict_legacy_v2_bridge import build_legacy_prediction_from_v2_payload

# bridge None: legacy baseline + warning
r1 = build_legacy_prediction_from_v2_payload(v2_payload=None)
# bridge_kind         = predict_legacy_v2_bridge
# v2_adapter_used in? = False
# warning recorded    = True   ← bridge 在 v2_adapter_warnings 里加了 warning

# bridge dict: 走 X4-B opt-in
r2 = build_legacy_prediction_from_v2_payload(v2_payload={
    'final_decision': {'final_direction': '偏多'},
    'confidence_result': {'combined_confidence': {'level': 'high'}},
})
# bridge_kind        = predict_legacy_v2_bridge
# bridge_version     = predict_legacy_v2_bridge.v1
# v2_adapter_used    = True
# final_bias         = 偏多
# final_confidence   = high
```

✅ bridge 默认 None → legacy baseline + warning；dict → 走 X4-B 路径，符合预期。

---

## 6. Git / artifact hygiene

| 项 | 状态 |
|---|---|
| `logs/prediction_log.jsonl` | ⏳ untracked（保持，不 stage） |
| `logs/regime_validation/` | ⏳ untracked，不在工作分支 staged 列表 |
| `logs/historical_training/three_system_*` | ⏳ untracked，不在工作分支 staged 列表 |
| `avgo_agent.db.backup_*`（7 个） | ⏳ untracked，不在工作分支 staged 列表 |
| `.claude/worktrees/` | ⏳ untracked / 不主动处理（hard rules） |
| `.claude/handoffs/task_089_post_pr_cleanup.md` | ⏳ untracked，不在工作分支 staged 列表 |
| `agent_loop.py` | ⏳ untracked，不在工作分支 staged 列表 |
| raw replay / validation output | ❌ 未生成、未 commit |
| DB schema | ❌ 未改 |

✅ 当前 worktree branch (`claude/optimistic-gauss-b20a8e`) 唯一未追踪文件是
`logs/prediction_log.jsonl`，所有 12A–12E-X5 commit 均**未**包含 raw output /
logs / DB backup / `.claude/worktrees/` / stash。Step 12 的 commit-per-fix +
不允许混合 cleanup 原则（11H §6 / §8）已严守。

---

## 7. 未解决事项（属 Step 14 / 后续阶段）

按 12E-X5 §10 / §11 锁定的债务，逐项 Step 13 不处理：

1. ❌ `predict.py` 仍包含 v1 helper / inner block（`_summarize` /
   `_confidence_from_score` / `_raise_confidence` / `_lower_confidence` /
   `_normalize_confidence` / `_path_risk_from_confidence` / `_apply_research_adjustment`
   旧分支）→ Step 14 cleanup
2. ❌ default `run_predict` 未切 V2（保持 legacy；任何切换属架构级 launch review）
3. ❌ 旧 logs（`logs/regime_validation/` / `logs/historical_training/three_system_*`）
   未清 → Step 14
4. ❌ DB backups（`avgo_agent.db.backup_*`，7 个）未清 → Step 14
5. ❌ root v1 dead stubs（`confidence_engine.py` / `contradiction_engine.py` /
   `risk_model.py`）未清 → Step 14
6. ❌ `tests/fixtures/app_analysis_context_fixture.py` 永久 monkeypatch 未 restore
   的 hygiene issue → Step 14（boundary tests 用 `_fresh_predict_module()` 防御）
7. ❌ `continuous_smoothing` v1+v2 frozen diagnostic（保留为 baseline；默认**不**清理）
8. ❌ 旧 V1 `services/projection_orchestrator.py` quarantine 决策 → Step 14
9. ❌ `.claude/legacy_tasks/` 是否压缩归并 → Step 14
10. ❌ Step 14 cleanup 整体尚未开始（每项独立 PR / commit）

---

## 8. 是否允许进入 Step 14

> **YES — allowed to plan Step 14 cleanup / quarantine.**

理由：

- ✅ §3 三层回归全部通过（focused 265 / predict-related 156 / full 3252，0 failed）
- ✅ §4 25 项 boundary invariants 全部通过
- ✅ §5 active caller static review 全部通过
- ✅ §6 artifact hygiene 干净
- ✅ 11H §11 前置条件满足（Step 12 全部入 main + Step 13 regression 通过）

**但**同时强约束：

- ❌ Step 14 仍需**独立计划**，不得直接动手删除 / 移动文件
- 推荐先写 `tasks/record_14_cleanup_quarantine_plan.md`（file-by-file 列出
  cleanup 候选 + retention policy + 顺序 + 每项 commit 粒度）
- Step 14 每项**独立 PR / commit**（11H §6.3 / §11 锁定）
- Step 14 期间**不**允许借机启用 candidate / promotion / 复活 frozen diagnostic /
  默认切 V2

---

## 9. 是否允许进入 3R-5 / 3R-6

> **NO.**

理由（按 11H §12 严格前置条件）：

1. ❌ Step 14 cleanup 尚未完成（只完成 Step 12 + Step 13）
2. ❌ default V2 migration 尚未独立 launch review（仍属架构级切换；不在 Step 14）
3. ❌ 06 / 07A–D contract 未显式更新 / 新增 candidate（Step 14 也不允许暗增）
4. ❌ trading / hard / forced / production_promotion 仍**永久禁止**（07D §5 /
   §11 / 11G）
5. ❌ 进入 3R-5 / 3R-6 必须**另开 launch review** 文档（不在 06–11H 范畴；
   属 12+ 阶段独立 PR）

任何**借口**（"只是改一行" / "测试已通过" / "影响小"）都**不**构成跳过前置
条件的理由。

---

## 10. 推荐下一步

**推荐**：

> **Step 14 cleanup / quarantine planning**（先写计划文档，后逐项执行）

具体路径：

1. 新增 `tasks/record_14_cleanup_quarantine_plan.md`，内容包括：
   - file-by-file cleanup 候选清单（按 11H §9 / 12E-X5 §11）
   - 每项的归属（DELETE / QUARANTINE_LATER / FROZEN_KEEP / CLEANUP_LATER）
   - retention policy（DB backup / logs / `.claude/worktrees/` 各自策略）
   - 顺序与 commit 粒度
   - 每项的回滚方案
2. **不**在 Step 14 计划文档里直接执行任何 cleanup
3. **不**借 Step 14 之机启用 candidate / promotion / continuous_smoothing 复活

**不**推荐：

- 直接做 cleanup（必须先有计划文档）
- 跳过 Step 14 直接进 3R-5 / 3R-6
- 在 Step 13 结果文档里追加未经计划的 cleanup commit
- 启用 promotion_execution_bridge / 启用 candidate / 复活 continuous_smoothing /
  接 trading / 默认切 V2

---

## 11. 严守边界

本轮**只做 regression report + 静态 / 运行时 spot-check**：

- 未改业务代码（`predict.py` / `services/predict_legacy_adapter.py` /
  `services/predict_legacy_v2_bridge.py` / 全部 services / ui / scripts 文件
  byte-identical 与 main `3ecf78c`）
- 未新增功能 / 未新增测试
- 未删文件 / 未移动文件
- 未写 DB / 未改 DB schema
- 未跑 replay / real validation
- 未处理 untracked / DB backup / stash / `.claude/worktrees/`
- 未默认迁移 `run_predict` 到 V2
- 未接 UI / app.py / command bar / contract_replay_writer
- 未启动 Step 14 cleanup
- 未进入 3R-5 / 3R-6
- 未新增 candidate / 未复活 `continuous_smoothing`
- 未顺手碰 RISK-1 / RISK-2 / RISK-3 / RISK-7 / RISK-8 / RISK-9 / RISK-10

本 regression report 的修改路径：任何对 §3 测试结果、§4 boundary invariants、
§5 active caller static review、§6 artifact hygiene、§7 未解决事项、§8 / §9
进入 Step 14 / 3R-5 / 3R-6 决策的调整，都必须以**显式更新本文件**的方式提出；
同时检查是否需要同步更新 11H / 12E-X5。
