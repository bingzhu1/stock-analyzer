# 18Z记录：Legacy Bridge Active Import Graph & Archive Readiness Table

> 本记录是 **Step 18Z：清离前置盘点**——第三批（18T ~ 18Y）全部入 main
> 之后的最后一刀。本轮回答："如果下一批要开始 Bridge 清离 / archive，
> 当前事实是什么；哪些模块还**绝对**不能删；下一批还差哪些前置条件。"
>
> 本轮**只**写盘点 / readiness table：未改业务代码、未新增测试、未删除
> 文件、未移动文件、未 archive、未修改 `.gitignore`、未处理 handoff、
> 未处理 logs / DB backup / `.claude/worktrees/`、**未处理
> `avgo_agent.db`**、未跑 replay / validation / historical evaluation /
> holdout / calibration、未写 DB / 未改 DB schema、未默认迁移
> `run_predict` 到 V2、未接 trading、未输出 buy / sell / hold / hard /
> forced / required、未进入 3R-5 / 3R-6、未启动任何代码 PR、未实现
> architecture_orchestrator wire-in、未删 Bridge、未迁 Predict tab、
> 未 commit / 未 push。
>
> 唯一 deliverable：本文件。
>
> **本记录优先级**：与 17D ~ 17M / 18A / 18J / 18S 同级。冲突仲裁路径
> 与 1.0 §14 / 17D §13 / 18S §15 一致：旧 records 若与 18Z 在 Bridge
> 清离前置范畴冲突，**以 18Z 为准**。

---

## 1. Step 18Z 目的

把 16H Repository Clearing Decision Table 中"`MIGRATE_CALLER_FIRST →
DELETE_LATER`"的 13 个 LEGACY_ACTIVE_DEPENDENCY 模块、加上第二 / 第三
批落地的 contract validators / adapters / skeleton / helper，整合成
**一份事实表**：

- 每个模块当前是 active / bridge / legacy / inspect-only / standalone
  helper 哪一种
- 每个模块有哪些 active caller / importer
- 每个模块产出 / 消费哪些 legacy field 或 standard field
- 是否已有 standard replacement，replacement 是否已接 active path
- archive readiness：是 `KEEP_*` / `NO_*`（不能删）还是
  `MAYBE_*`（待证据）
- 阻塞下一批清离的 blockers
- 触发清离的下一个 PR 候选

**本轮只回答事实**，**不**执行：

- ❌ 不删任何文件
- ❌ 不移动任何文件
- ❌ 不 archive
- ❌ 不改 Bridge
- ❌ 不改 predict.py / orchestrator / UI / DB
- ❌ 不跑 replay / holdout / calibration

**本文件性质**：archive readiness table（事实表 + 决策建议），不是
design 也不是 impl。

---

## 2. 当前前置条件

| 项 | 状态 |
|---|---|
| 1.0 canonical principles | ✅ commit `5c209bb` |
| 16A architecture reset blueprint | ✅ commit `9b98ad5` |
| 16B / 16C / 16D / 16E / 16F / 16G / 16H / 16I | ✅ 全部入 main |
| 17A / 17B / 17C / 17D / 17E ~ 17M | ✅ 全部入 main |
| 18A First Batch Selection | ✅ commit `30c7ac0` |
| 18B ~ 18I 第一批 8 contract validators | ✅ 全部入 main |
| 18J Second Batch Selection | ✅ commit `9182d0b` |
| 18K ~ 18R 第二批 8 producer adapter / Confidence schema 修复 / Final Report 加固 / Inspect tab 第一刀 / Review warning-only | ✅ 全部入 main |
| 18S Third Batch Selection | ✅ commit `a49aa90` |
| 18T PR-EVAL-2 (2026 holdout boundary tests) | ✅ commit `734972f` |
| 18U PR-DATA-1 (data_fetcher Data Layer boundary tests) | ✅ commit `0c90e74` |
| 18V PR-ARCH-1 (architecture_orchestrator skeleton) | ✅ commit `5c95135` |
| 18W PR-FINAL-4 (warning_cards schema) | ✅ commit `3acd427` |
| 18X PR-REVIEW-3 (briefing read-only boundary tests) | ✅ commit `8909ce1` |
| 18Y PR-UI-3 (Inspect tab diff/trend/extras display) | ✅ commit `29afe7e` |
| main 最新 commit | `29afe7e` |
| 第三批完成度 | **6/7**（本 18Z 是最后一刀） |
| full pytest baseline（18Y 入 main 后） | **4253 passed, 10 skipped, 0 failed, 26 warnings, 3012 subtests passed** |
| worktree 唯一 deliberate untracked | `.claude/handoffs/task_089_post_pr_cleanup.md` |
| 战略阶段 | 第三批 6/7 → **PR-CLEAR-1 archive readiness 盘点（18Z 本轮）** |
| 3R-5 / 3R-6 | ❌ 仍然不允许进入 |
| 第四批 PR | ❌ 必须等 18Z 入 main + 用户单独确认后才能启动 |

**关键事实**（截至 18Y 入 main）：

- ✅ Evaluation holdout 边界已锁（PR-EVAL-2）
- ✅ Data Layer 边界已起步（PR-DATA-1）
- ✅ `architecture_orchestrator` skeleton 已落地，但 `status="skeleton_only"`
  / `active_path_connected=False`（PR-ARCH-1）
- ✅ `warning_card.v1` schema 已落地，但**未接** active path（PR-FINAL-4）
- ✅ Review briefing read-only boundary 已锁（PR-REVIEW-3）
- ✅ Inspect tab 已展示 standard payload status / diff / trend / extras
  四个 readonly section（PR-UI-2 + PR-UI-3）
- ❌ active path 仍是 `app.py → home_terminal_orchestrator → predict.run_predict`
  并依赖 `predict_legacy_adapter` 兼容层
- ❌ Predict tab / Home tab / History tab 仍读 `final_bias` /
  `final_confidence`
- ❌ `main_projection_layer` 仍输出 `predicted_top1` / `predicted_top2`
- ❌ `exclusion_layer` 仍输出 `triggered_rules` / `triggered_rule` /
  `excluded`
- ❌ `final_decision` 仍输出 `final_report_aggregator_result.v1`，
  非 `final_report_result.v1`

---

## 3. 当前 active path 总览

> 以下是基于 18Y 入 main 后 **`grep / rg` 验证过的** 真实 import 关系。
> 任何"下一步是否可以删 X"的判断都必须以本节为准。

### 3.1 顶层 entrypoint

| Entrypoint | 角色 | 关键 import | 备注 |
|---|---|---|---|
| `app.py` | Streamlit 主入口 | `from services.home_terminal_orchestrator import build_home_terminal_orchestrator_result`（line 86）+ `from ui.predict_tab import render_predict_tab`（line 89） | hard rule 3 锁定；最小改动 |
| `ui/predict_tab.py` | Predict 主 tab | `from predict import run_predict`（line 10）+ 大量 `services.*` | UI active path 的核心 caller |
| `predict.py` | Bridge / legacy result builder | `from services.predict_legacy_adapter import adapt_v2_payload_to_predict_legacy`（line 44）+ 多处 `from services.projection_entrypoint import _degraded_projection_three_systems`（lines 1322 / 1332 / 1346） | 未来要 thin-wrap 的 bridge |
| `services/home_terminal_orchestrator.py` | Home terminal flow | active；被 `app.py` 直接 import | 仍 active；未替换 |

### 3.2 Projection 链 import 关系

```
app.py
 └→ services.home_terminal_orchestrator       # active
ui/predict_tab.py
 └→ predict.run_predict                       # bridge
     └→ services.predict_legacy_adapter        # adapter (in-process)
     └→ services.projection_entrypoint
          └→ services.projection_v2_adapter
               └→ services.projection_orchestrator_v2.run_projection_v2
                    └→ services.projection_orchestrator
                         └→ services.projection_orchestrator_preflight
                         └→ from predict import run_predict  ← 循环依赖（V1 顶层 import predict）
                         └→ services.main_projection_layer    # 仍输出 legacy
                         └→ services.exclusion_layer          # 仍输出 legacy
                         └→ services.confidence_evaluator     # 已改为 standard-first / legacy-fallback
                         └→ services.final_decision           # 仍输出 final_report_aggregator_result.v1
services.tool_router
 └→ services.projection_entrypoint.run_projection_entrypoint
services.historical_replay_training
 └→ services.projection_orchestrator_v2.run_projection_v2
services.contract_replay_writer
 └→ from predict import run_predict
scripts/run_e2e_loop.py / scripts/save_projection_records_smoke.py
 └→ from predict import run_predict / projection_orchestrator_v2
```

### 3.3 architecture_orchestrator skeleton（18V / PR-ARCH-1）

- **Active path connected**：❌ 否（`status="skeleton_only"` /
  `active_path_connected=False`）
- **Importers**：仅 `tests/test_architecture_orchestrator_skeleton.py`
- **Forbidden actions** 已在 `FORBIDDEN_ACTIVE_PATH_ACTIONS` 锁定，
  含 `run_predict` / `call_main_projection_layer` /
  `call_exclusion_layer` / `call_confidence_evaluator` /
  `call_final_decision` / `call_review_orchestrator` /
  `call_projection_orchestrator` / `call_home_terminal_orchestrator` /
  `write_db` / `write_logs` / `run_replay` / `run_calibration` /
  `run_holdout` / `place_trade`
- 任何 wire-in 必须改 `ARCHITECTURE_ORCHESTRATOR_STATUS` 常量 + 用户
  单独确认（PR-ARCH-2 候选；本批不进入）

### 3.4 warning_cards helper（18W / PR-FINAL-4）

- **Active path connected**：❌ 否
- **Importers**：仅 `tests/test_warning_cards.py` /
  `tests/test_review_briefing_read_only_boundary.py`（forbidden-import 检查）
- 与 `final_report_result.v1.warning_cards` 字段兼容；下一步可由
  PR-FINAL-5 接入 final_decision passthrough（**本批不进入**）

### 3.5 Inspect tab read-only 4 sections（18Q + 18Y）

- **Active path connected**：✅ Inspect tab 已 wire `inspect_latest_contract_payload`
  / `diff_latest_contract_payloads` / `summarize_recent_contract_payloads` /
  `summarize_contract_extras_dashboard`，每个调用都在 `try/except` 内
- 这四个 backend helper 都是 **read-only DB SELECT**；对 active path
  无副作用

---

## 4. Legacy / Bridge 模块清单

> 每条记录列：current_role / layer / active_callers / importers /
> legacy_fields_produced_consumed / standard_replacement_status /
> can_archive_now / risk / next_required_PR

### 4.1 `predict.py`

| 字段 | 值 |
|---|---|
| Current role | Legacy result wrapper / Bridge to V2 via `predict_legacy_adapter` |
| Layer | Cross-layer (TEMP_MIGRATION_BRIDGE per 16H) |
| Active callers | `ui/predict_tab.py:10` / `services/projection_orchestrator.py:15` / `services/contract_replay_writer.py:83` / `scripts/run_e2e_loop.py` / `services/predict_legacy_v2_bridge.py:80` (lazy) |
| Imports | `services.predict_legacy_adapter` (top-level), `services.projection_entrypoint._degraded_projection_three_systems` (lazy) |
| Legacy fields produced | `final_bias` / `final_confidence` / `final_direction` / `final_prediction` / `final_projection` / `primary_projection` / `briefing_caution_*` markers |
| Standard replacement | ⏳ 部分：`final_report_result.v1` contract validator 已存在 (PR-FINAL-1)；adapter 未接 active path |
| Can archive now | ❌ NO_BRIDGE_STILL_REQUIRED |
| Risk if removed | **H**：UI Predict tab + replay + 多处 scripts 直接断 |
| Next required PR | PR-CLEAR-2 active import graph 工具化 → PR-FINAL-5 final_report_result adapter active path → PR-UI-7 Predict tab schema migration → 17D §10.1 bridge thin-wrap 设计 |

### 4.2 `services/projection_orchestrator.py`（V1）

| 字段 | 值 |
|---|---|
| Current role | Legacy V1 orchestrator；含顶层 `from predict import run_predict`（循环依赖） |
| Layer | Branch 3 / cross-layer (LEGACY_ACTIVE_DEPENDENCY) |
| Active callers | `services/projection_orchestrator_v2.py:16` (`from services.projection_orchestrator import build_projection_orchestrator_result`) |
| Imports | `predict.run_predict`（顶层；Task 14G §15 标记的循环）+ `services.projection_orchestrator_preflight` |
| Legacy fields produced | V1 legacy result shape (`predicted_top1` / `predicted_top2` / `final_bias` etc.) |
| Standard replacement | ⏳ `projection_result.v1` contract + adapter 已存在；active path 未切 |
| Can archive now | ❌ NO_BRIDGE_STILL_REQUIRED |
| Risk if removed | **H**：V2 仍依赖其 `build_projection_orchestrator_result`；删除会断 V2 → 断 UI → 断 replay |
| Next required PR | PR-PROJ-3+ 让 V2 不再依赖 V1 内部 helper；之后 PR-CLEAR-3 archive |

### 4.3 `services/projection_orchestrator_v2.py`

| 字段 | 值 |
|---|---|
| Current role | V2 projection 主 orchestrator；目前 active 主推路径 |
| Layer | Branch 3 (KEEP_ACTIVE / ASSEMBLY_ORCHESTRATION_LAYER per 17J §13) |
| Active callers | `services/projection_v2_adapter.py:12` / `services/historical_replay_training.py:101` / `scripts/save_projection_records_smoke.py:441` |
| Imports | `services.projection_orchestrator.build_projection_orchestrator_result`（V1 内部 helper） |
| Legacy fields produced | V2 raw payload；下游 adapter 转 legacy keys |
| Standard replacement | ⏳ `architecture_orchestrator` skeleton 已存在但未接 active path |
| Can archive now | ❌ KEEP_CORE（active 主链） |
| Risk if removed | **H**：直接断 active path |
| Next required PR | PR-ARCH-2+ architecture_orchestrator 接 active；之后 V2 才有可能 thin-wrap |

### 4.4 `services/projection_entrypoint.py`

| 字段 | 值 |
|---|---|
| Current role | Routing wrapper：`run_projection_entrypoint` / `_degraded_projection_three_systems` |
| Layer | Branch 3 / cross-layer routing |
| Active callers | `predict.py:1322 / 1332 / 1346`（degraded helper，lazy import）/ `services/tool_router.py:29` (`run_projection_entrypoint`) |
| Imports | `services.projection_orchestrator_v2.run_projection_v2` / `services.projection_v2_adapter.build_projection_entrypoint_result` |
| Legacy fields produced | Routing only；不直接产出 final-level 字段 |
| Standard replacement | ⏳ 待 architecture_orchestrator wire-in |
| Can archive now | ❌ NO_ACTIVE_CORE（degraded fallback 仍是 predict.py 必需路径） |
| Risk if removed | **H**：degraded fallback / tool_router 直接断 |
| Next required PR | 与 PR-ARCH-2+ 协同 |

### 4.5 `services/projection_v2_adapter.py`

| 字段 | 值 |
|---|---|
| Current role | V2 raw → entrypoint payload adapter |
| Layer | Branch 3 (TEMP_MIGRATION_BRIDGE) |
| Active callers | `services/projection_entrypoint.py:12` |
| Imports | `services.projection_orchestrator_v2.run_projection_v2` |
| Legacy fields produced | entrypoint payload（V2 → legacy schema bridge） |
| Standard replacement | ⏳ standard payload contract 已存在；adapter 未替换 |
| Can archive now | ❌ NO_BRIDGE_STILL_REQUIRED |
| Risk if removed | **H**：projection_entrypoint 直接断 |
| Next required PR | PR-PROJ-3+ active path 切 standard schema 后再 thin-wrap |

### 4.6 `services/predict_legacy_adapter.py`

| 字段 | 值 |
|---|---|
| Current role | V2 payload → predict legacy result overlay；11E X4-B 引入 |
| Layer | Cross-layer (TEMP_MIGRATION_BRIDGE) |
| Active callers | `predict.py:44`（顶层 import） |
| Imports | (内部细节略) |
| Legacy fields produced | overlay legacy compat keys（predict 期望的 final_bias / final_confidence 等） |
| Standard replacement | ⏳ 由 final_report_result.v1 adapter 接管；未接 active |
| Can archive now | ❌ NO_BRIDGE_STILL_REQUIRED |
| Risk if removed | **H**：predict.py 直接断 |
| Next required PR | PR-FINAL-5+ active path 切 |

### 4.7 `services/predict_legacy_v2_bridge.py`

| 字段 | 值 |
|---|---|
| Current role | Predict legacy ↔ V2 bridge helper |
| Layer | Cross-layer (TEMP_MIGRATION_BRIDGE) |
| Active callers | 主代码无（仅 lazy `from predict import run_predict`，line 80）；测试 + 13 §3 §4 引用 |
| Imports | predict.run_predict (lazy) |
| Legacy fields produced | bridge helper for V2 → legacy result |
| Standard replacement | ⏳ 待 architecture_orchestrator 接管 + final_report adapter |
| Can archive now | ❌ NO_BRIDGE_STILL_REQUIRED |
| Risk if removed | **M**：测试 + 数个回归路径用到 |
| Next required PR | 与 PR-FINAL-5+ 协同 |

### 4.8 `services/home_terminal_orchestrator.py`

| 字段 | 值 |
|---|---|
| Current role | Home terminal 主路径 orchestrator |
| Layer | Branch 6 / cross-layer (KEEP_ACTIVE) |
| Active callers | `app.py:86` (`build_home_terminal_orchestrator_result`) |
| Imports | (large) |
| Legacy fields produced | home tab payload（含 legacy final_bias / final_confidence） |
| Standard replacement | ⏳ 待 architecture_orchestrator 接管 |
| Can archive now | ❌ KEEP_CORE（active 主链） |
| Risk if removed | **H**：app.py 直接断 |
| Next required PR | PR-ARCH-2+ + PR-UI-* (Home tab schema migration) |

### 4.9 `services/main_projection_layer.py`

| 字段 | 值 |
|---|---|
| Current role | Branch 3 主推算子 |
| Layer | Branch 3 (KEEP_ACTIVE / CORE_PROJECTION) |
| Active callers | V1/V2 orchestrator 链路 |
| Legacy fields produced | `predicted_top1` / `predicted_top2`（line 331-359）+ `kind="main_projection_layer"` |
| Standard replacement | ⏳ `projection_result.v1` adapter 已存在 (`projection_result_adapter.py`)；active output 未直接改 standard |
| Can archive now | ❌ KEEP_CORE |
| Risk if removed | **H**：active 主推算子 |
| Next required PR | PR-PROJ-3 active output emit standard keys (alias，保留 legacy 兼容) |

### 4.10 `services/exclusion_layer.py`

| 字段 | 值 |
|---|---|
| Current role | Branch 4 主否定算子 |
| Layer | Branch 4 (KEEP_ACTIVE / CORE_EXCLUSION) |
| Active callers | V1/V2 orchestrator 链路 |
| Legacy fields produced | `triggered_rules` / `triggered_rule`（line 71-233）/ `excluded` / `action` |
| Standard replacement | ⏳ `exclusion_result.v1` adapter 已存在 (`exclusion_result_adapter.py`)；active output 未改 |
| Can archive now | ❌ KEEP_CORE |
| Risk if removed | **H**：active 主否定算子 |
| Next required PR | PR-EXCL-3 active output emit standard keys |

### 4.11 `services/confidence_evaluator.py`

| 字段 | 值 |
|---|---|
| Current role | Branch 5 主可信度算子；18N PR-CONF-2 后已能 standard-first / legacy-fallback 读 |
| Layer | Branch 5 (KEEP_ACTIVE / CORE_CONFIDENCE) |
| Active callers | V2 orchestrator / final_decision |
| Legacy fields produced | `combined_confidence` / `agreement_status` / `conflict_level` / `reliability_warnings` / `calibration_notes` |
| Standard replacement | ⏳ `confidence_result.v1` 已 read（PR-CONF-2）；output schema 未完全切 standard |
| Can archive now | ❌ KEEP_CORE |
| Risk if removed | **H** |
| Next required PR | PR-CONF-4（agreement_status enum 标准化 + medium 槽位） |

### 4.12 `services/final_decision.py`

| 字段 | 值 |
|---|---|
| Current role | 当前 final aggregator；输出 `final_report_aggregator_result.v1` shape；含 18P PR-FINAL-2 加固后的 non-mutation |
| Layer | Branch 6 (KEEP_ACTIVE) |
| Active callers | V2 orchestrator |
| Legacy fields produced | `final_direction` / `final_confidence` / `risk_level` / `warnings` (flat list[str]) / `decision_factors` etc. |
| Standard replacement | ⏳ `final_report_result.v1` validator + `warning_card.v1` helper 已存在；adapter 未接 |
| Can archive now | ❌ KEEP_CORE |
| Risk if removed | **H** |
| Next required PR | PR-FINAL-5 final_report_result adapter active wire；之后 PR-FINAL-6 / PR-UI-6 |

### 4.13 `ui/predict_tab.py`

| 字段 | 值 |
|---|---|
| Current role | Predict 主 tab；调 `run_predict` + 多处 `services.*` |
| Layer | Branch 9 UI (KEEP_ACTIVE) |
| Active callers | `app.py:89` |
| Legacy fields read | `final_bias` / `final_confidence` / `primary_projection` / `final_projection`（lines 273-704+） |
| Standard replacement | ⏳ `presentation_payload.v1` validator 已存在 (PR-UI-1)；active read 未切 |
| Can archive now | ❌ KEEP_CORE |
| Risk if removed | **H**：app.py 直接断 |
| Next required PR | PR-UI-7 Predict tab schema migration（**风险 H；永久暂缓本批**；必须等 PR-FINAL-5 + PR-ARCH-2+ + 更多 adapter active wiring） |

### 4.14 `ui/projection_v2_renderer.py`

| 字段 | 值 |
|---|---|
| Current role | V2 projection 详细渲染（被 predict tab / 其他 tab 调） |
| Layer | Branch 9 UI |
| Active callers | UI tab 内 |
| Legacy fields read | V2 raw payload；含 legacy 兼容键 |
| Standard replacement | ⏳ presentation_payload.v1 |
| Can archive now | ❌ KEEP_CORE |
| Risk if removed | **H** |
| Next required PR | PR-UI-* Predict tab 迁移之后 |

### 4.15 `services/projection_chain_contract.py`

| 字段 | 值 |
|---|---|
| Current role | Cross-layer projection chain helper |
| Layer | Cross-layer (CORE_HELPER per 17F §7.6 / 17G §6.3 / 17H §6.3) |
| Active callers | 多个 projection / final_decision 子模块 |
| Legacy fields produced | chain contract helper |
| Standard replacement | ⏳ 17J §13 PR-FINAL-5 拆分 plan |
| Can archive now | ❌ KEEP_CORE（active 跨层 helper） |
| Risk if removed | **H** |
| Next required PR | PR-FINAL-5 split plan |

### 4.16 `services/standard_projection_payload.py`

| 字段 | 值 |
|---|---|
| Current role | Standard payload skeleton (17A PR-B) |
| Layer | Branch 3 |
| Active callers | adapters / tests |
| Legacy fields produced | standard schema helpers |
| Standard replacement | ✅ 自身即 standard |
| Can archive now | ❌ KEEP_CORE（standard payload 基础） |
| Risk if removed | **H** |
| Next required PR | 保留 |

### 4.17 `services/consistency_layer.py`

| 字段 | 值 |
|---|---|
| Current role | Cross-layer consistency display layer (CONSISTENCY_LAYER) |
| Layer | Branch 6 / cross-layer |
| Active callers | V2 orchestrator / UI |
| Legacy fields produced | consistency display fields |
| Standard replacement | ⏳ 17F §6.8 / 17G §16.4 / 17H §15.3 / 17I §7 / 17J §13 PR-FINAL-3 freeze marker |
| Can archive now | ❌ KEEP_CORE |
| Risk if removed | **M** |
| Next required PR | PR-FINAL-3 freeze marker |

### 4.18 Inspect-only read-only contract tools（18Q + 18Y wired）

| Module | Current role | Importers (active) | Archive readiness |
|---|---|---|---|
| `services/contract_payload_inspector.py` | inspect latest contract payload | `ui/inspect_tab.py` (lazy, try/except) | KEEP_INSPECT_READONLY |
| `services/contract_payload_diff.py` | diff latest two | `ui/inspect_tab.py` (lazy, try/except) | KEEP_INSPECT_READONLY |
| `services/contract_payload_trend.py` | trend across N | `ui/inspect_tab.py` (lazy, try/except) | KEEP_INSPECT_READONLY |
| `services/contract_payload_extras_dashboard.py` | extras dashboard | `ui/inspect_tab.py` (lazy, try/except) | KEEP_INSPECT_READONLY |

四个 inspect tool 已成为 Inspect tab 的 standing display source。
**不能 archive**。

### 4.19 18A ~ 18W 落地的 contract validators / adapters / skeleton / helpers

| Module | Current role | Active path connected | Archive readiness |
|---|---|---|---|
| `services/feature_payload_contract.py` (PR-FEATURE-1) | shape validator | ❌ helper-only | KEEP（standard 基础） |
| `services/feature_payload_adapter.py` (PR-FEATURE-2) | producer adapter | ❌ helper-only | KEEP |
| `services/projection_result_contract.py` (PR-PROJ-1) | shape validator | ❌ helper-only | KEEP |
| `services/projection_result_adapter.py` (PR-PROJ-2) | legacy → standard adapter | ❌ helper-only | KEEP |
| `services/exclusion_result_contract.py` (PR-EXCL-1) | shape validator | ❌ helper-only | KEEP |
| `services/exclusion_result_adapter.py` (PR-EXCL-2) | legacy → standard adapter | ❌ helper-only | KEEP |
| `services/confidence_result_contract.py` (PR-CONF-1) | shape validator | ⚠️ partial（PR-CONF-2 让 active reader 读 standard schema） | KEEP |
| `services/final_report_result_contract.py` (PR-FINAL-1) | shape validator | ❌ helper-only | KEEP |
| `services/review_result_contract.py` (PR-REVIEW-1) | shape validator | ❌ helper-only | KEEP |
| `services/evaluation_result_contract.py` (PR-EVAL-1) | shape validator | ❌ helper-only | KEEP |
| `ui/presentation_payload_contract.py` (PR-UI-1) | UI shape validator | ❌ helper-only | KEEP |
| `services/architecture_orchestrator.py` (PR-ARCH-1) | ownership skeleton | ❌ skeleton_only | KEEP（locked by `ARCHITECTURE_ORCHESTRATOR_STATUS`） |
| `services/warning_cards.py` (PR-FINAL-4) | helper | ❌ helper-only | KEEP |

全部 **不能 archive**——它们是 standard active path 的"目标形状"，删了
就没法切。

---

## 5. Standard replacement status

### 5.1 已落地的 contract / helper 基础

| Schema / Helper | 来源 PR | 当前位置 | 接 active path? |
|---|---|---|---|
| `feature_payload.v1` | PR-FEATURE-1 / PR-FEATURE-2 | `services/feature_payload_contract.py` + `_adapter.py` | ❌ 否 |
| `projection_result.v1` | PR-PROJ-1 / PR-PROJ-2 | `services/projection_result_contract.py` + `_adapter.py` | ❌ 否 |
| `exclusion_result.v1` | PR-EXCL-1 / PR-EXCL-2 | `services/exclusion_result_contract.py` + `_adapter.py` | ❌ 否 |
| `confidence_result.v1` | PR-CONF-1 / PR-CONF-2 / PR-CONF-3 | `services/confidence_result_contract.py` + active `_compute_agreement` standard-first / legacy-fallback | ⚠️ 部分（reader 已切；emit 仍 legacy） |
| `final_report_result.v1` | PR-FINAL-1 | `services/final_report_result_contract.py` | ❌ 否 |
| `review_result.v1` | PR-REVIEW-1 | `services/review_result_contract.py` | ❌ 否 |
| `evaluation_result.v1` | PR-EVAL-1 | `services/evaluation_result_contract.py` | ❌ 否 |
| `presentation_payload.v1` | PR-UI-1 | `ui/presentation_payload_contract.py` | ❌ 否 |
| `warning_card.v1` | PR-FINAL-4 | `services/warning_cards.py` | ❌ 否 |
| `architecture_orchestrator.skeleton.v1` | PR-ARCH-1 | `services/architecture_orchestrator.py` | ❌ skeleton_only |
| 2026 holdout boundary tests | PR-EVAL-2 | `tests/test_evaluation_holdout_boundary.py` | ✅ enforced via tests |
| Data Layer boundary tests | PR-DATA-1 | `tests/test_data_fetcher_boundary.py` | ✅ enforced via tests |
| Review briefing read-only boundary tests | PR-REVIEW-3 | `tests/test_review_briefing_read_only_boundary.py` | ✅ enforced via tests |

### 5.2 关键事实

> **standard replacement 的存在不等于 active path 已切换。**

九个 contract validator + 五个 adapter / standard-first reader + 一个
skeleton + 一个 warning_card helper 已就位。但 active path：

- **emit** 端：projection / exclusion / final_decision 仍输出 legacy
  shape（兼容 + 兜底）
- **read** 端：UI Predict tab / Home tab / History tab 仍按 legacy
  字段渲染

→ 这是为什么本批（第三批）只能落"前置 + display-only + boundary
test"，而不能进入"Bridge 删除 / Predict tab 迁移"。

---

## 6. Archive readiness table

> 列：
> - `Module` — 相对 repo root
> - `Layer` — 九分支或 cross-layer
> - `Current role` — bridge / legacy / active / helper / inspect / skeleton
> - `Active caller status` — 是否仍被 active path 调用
> - `Standard replacement` — 是否已存在 + 是否已接 active
> - `Archive readiness` — `KEEP_*` / `NO_*` / `MAYBE_*` 之一
> - `Recommendation` — 18Z 给出的建议（**仅决策；本轮不执行**）
> - `Blockers` — 阻止 archive 的具体前置
> - `Next PR` — 推动 archive readiness 提升的下一个候选 PR

### 6.1 Archive readiness 标签定义

| 标签 | 含义 |
|---|---|
| `KEEP_CORE` | 正式架构内 active 主链；不可删 |
| `KEEP_INSPECT_READONLY` | Inspect / observability 工具；read-only DB SELECT；保留 |
| `KEEP_HELPER` | Standard contract / adapter / skeleton / helper；replacement 基础 |
| `NO_ACTIVE_CORE` | 仍是 active 路径的关键节点；删了就断 |
| `NO_BRIDGE_STILL_REQUIRED` | Bridge / adapter，仍被 active caller 依赖 |
| `NO_UI_STILL_READS` | UI 仍读 legacy fields |
| `NO_STANDARD_REPLACEMENT_NOT_WIRED` | standard replacement 已存在但未接 active；删除会破坏 active path |
| `MAYBE_QUARANTINE_AFTER_ACTIVE_GRAPH` | 可能 quarantine，但需要 PR-CLEAR-2 machine-readable import graph 证据 |
| `MAYBE_DOC_ONLY` | 仅文档候选；待 17J / 17K plan 结束后判断 |
| `DELETE_NOT_ALLOWED` | 用户单独锁定，永久不可删 |

### 6.2 Archive readiness 总表

| Module | Layer | Current role | Active caller status | Standard replacement | Archive readiness | Recommendation | Blockers | Next PR |
|---|---|---|---|---|---|---|---|---|
| `predict.py` | Cross-layer | Legacy result wrapper / Bridge | ✅ active（UI / scripts / V1 orchestrator） | ⏳ final_report_result.v1 (未接) | **NO_BRIDGE_STILL_REQUIRED** | **保留**；待 PR-FINAL-5 + PR-UI-7 后 thin-wrap | UI 仍读 legacy；scripts 仍调 run_predict；V1 orchestrator 顶层 import predict | PR-CLEAR-2 → PR-FINAL-5 → PR-UI-7 |
| `services/projection_orchestrator.py` (V1) | Branch 3 | Legacy V1 orchestrator | ✅ active（V2 仍引用其 build_projection_orchestrator_result） | ⏳ V2 orchestrator + architecture_orchestrator skeleton | **NO_BRIDGE_STILL_REQUIRED** | **保留**；待 V2 不再依赖其内部 helper | V2 仍 `from services.projection_orchestrator import build_projection_orchestrator_result` | PR-PROJ-3+ + PR-ARCH-2 |
| `services/projection_orchestrator_v2.py` | Branch 3 | V2 active orchestrator | ✅ active（projection_v2_adapter / replay / smoke）| ⏳ architecture_orchestrator skeleton 已存在但未接 | **KEEP_CORE** | **保留**；active 主链 | architecture_orchestrator 未 wire-in | PR-ARCH-2 |
| `services/projection_entrypoint.py` | Branch 3 / cross-layer | Routing wrapper / degraded fallback | ✅ active（predict / tool_router） | ⏳ architecture_orchestrator | **NO_ACTIVE_CORE** | **保留**；degraded fallback 关键 | predict 仍 lazy import _degraded_projection_three_systems | PR-ARCH-2 |
| `services/projection_v2_adapter.py` | Branch 3 | V2 raw → entrypoint adapter | ✅ active（projection_entrypoint） | ⏳ standard payload contract 未替换 | **NO_BRIDGE_STILL_REQUIRED** | **保留**；中间 bridge | projection_entrypoint 仍 import | PR-PROJ-3+ |
| `services/predict_legacy_adapter.py` | Cross-layer | V2 → predict legacy overlay | ✅ active（predict.py 顶层 import） | ⏳ final_report_result adapter | **NO_BRIDGE_STILL_REQUIRED** | **保留**；predict 兼容核心 | predict 仍依赖 overlay | PR-FINAL-5 |
| `services/predict_legacy_v2_bridge.py` | Cross-layer | predict ↔ V2 bridge helper | ⏳ 仅 lazy + tests + 13 §3-§4 引用 | ⏳ architecture_orchestrator | **NO_BRIDGE_STILL_REQUIRED** | **保留**；测试 / 数个回归路径 | 用例覆盖；archive 需先迁测试 | PR-FINAL-5+ |
| `services/home_terminal_orchestrator.py` | Branch 6 / cross-layer | Home 主路径 orchestrator | ✅ active（app.py 直接 import） | ⏳ architecture_orchestrator | **KEEP_CORE** | **保留**；app.py 入口必需 | app.py 顶层 import | PR-ARCH-2+ |
| `services/main_projection_layer.py` | Branch 3 | Branch 3 主推算子 | ✅ active | ⏳ projection_result_adapter (未接) | **KEEP_CORE** | **保留**；active 算子 | active output 仍 legacy keys | PR-PROJ-3 |
| `services/exclusion_layer.py` | Branch 4 | Branch 4 主否定算子 | ✅ active | ⏳ exclusion_result_adapter (未接) | **KEEP_CORE** | **保留**；active 算子 | active output 仍 legacy keys | PR-EXCL-3 |
| `services/confidence_evaluator.py` | Branch 5 | Branch 5 主可信度算子 | ✅ active；reader 已部分 standard | ⏳ confidence_result schema partial | **KEEP_CORE** | **保留**；active 算子 | output schema 未完全 standard | PR-CONF-4 |
| `services/final_decision.py` | Branch 6 | final aggregator | ✅ active | ⏳ final_report_result.v1 (未接) | **KEEP_CORE** | **保留**；active aggregator | warning_cards / final_report_result.v1 未接入 | PR-FINAL-5 |
| `services/projection_chain_contract.py` | Cross-layer | chain helper | ✅ active（多处 sub-module 用） | ⏳ 17J PR-FINAL-5 split | **KEEP_CORE** | **保留** | split plan 未完成 | PR-FINAL-5 split |
| `services/standard_projection_payload.py` | Branch 3 | standard payload skeleton (17A) | ✅ active（adapters / tests） | ✅ 自身即 standard | **KEEP_CORE** | **保留** | — | 保留 |
| `services/consistency_layer.py` | Branch 6 / cross-layer | consistency display | ✅ active（V2 / UI） | ⏳ 17J PR-FINAL-3 freeze marker | **KEEP_CORE** | **保留** | freeze marker 未加 | PR-FINAL-3 |
| `ui/predict_tab.py` | Branch 9 UI | Predict 主 tab | ✅ active（app.py） | ⏳ presentation_payload.v1 (未接) | **KEEP_CORE / NO_UI_STILL_READS** | **保留**；最敏感 UI；PR-UI-7 永久暂缓本批 | UI 仍读 final_bias / final_confidence 等 7+ legacy keys | PR-FINAL-5 → PR-UI-7（H 风险，等 final_report adapter） |
| `ui/projection_v2_renderer.py` | Branch 9 UI | V2 详细渲染 | ✅ active（UI tabs） | ⏳ presentation_payload.v1 | **KEEP_CORE / NO_UI_STILL_READS** | **保留** | UI legacy reads | PR-UI-* (after Predict tab) |
| `ui/home_tab.py` | Branch 9 UI | Home tab | ✅ active（app.py） | ⏳ presentation_payload.v1 | **KEEP_CORE / NO_UI_STILL_READS** | **保留** | UI legacy reads (final_bias / final_confidence at 107-108 / 371-375) | PR-UI-* |
| `ui/history_tab.py` | Branch 9 UI | History tab | ✅ active（app.py） | ⏳ presentation_payload.v1 | **KEEP_CORE / NO_UI_STILL_READS** | **保留** | UI legacy reads (final_bias / final_confidence at 158-333) | PR-UI-* |
| `ui/inspect_tab.py` | Branch 9 UI | Inspect tab；现有 4 read-only sections | ✅ active（app.py） | ✅ standard payload + 4 inspect helpers wired | **KEEP_CORE** | **保留** | — | 持续扩展 |
| `services/contract_payload_inspector.py` | Inspect / observability | inspect latest payload | ✅ active（Inspect tab） | ✅ self | **KEEP_INSPECT_READONLY** | **保留** | — | 保留 |
| `services/contract_payload_diff.py` | Inspect / observability | diff latest two | ✅ active（Inspect tab） | ✅ self | **KEEP_INSPECT_READONLY** | **保留** | — | 保留 |
| `services/contract_payload_trend.py` | Inspect / observability | trend across N | ✅ active（Inspect tab） | ✅ self | **KEEP_INSPECT_READONLY** | **保留** | — | 保留 |
| `services/contract_payload_extras_dashboard.py` | Inspect / observability | extras dashboard | ✅ active（Inspect tab） | ✅ self | **KEEP_INSPECT_READONLY** | **保留** | — | 保留 |
| `services/feature_payload_contract.py` | Branch 2 | shape validator | ❌ helper-only | ✅ self | **KEEP_HELPER** | **保留** | — | 持续扩展 |
| `services/feature_payload_adapter.py` | Branch 2 | producer adapter | ❌ helper-only | ✅ self | **KEEP_HELPER** | **保留** | — | PR-FEATURE-3+ |
| `services/projection_result_contract.py` | Branch 3 | shape validator | ❌ helper-only | ✅ self | **KEEP_HELPER** | **保留** | — | — |
| `services/projection_result_adapter.py` | Branch 3 | legacy → standard | ❌ helper-only | ✅ self | **KEEP_HELPER** | **保留** | — | PR-PROJ-3 wire active emit |
| `services/exclusion_result_contract.py` | Branch 4 | shape validator | ❌ helper-only | ✅ self | **KEEP_HELPER** | **保留** | — | — |
| `services/exclusion_result_adapter.py` | Branch 4 | legacy → standard | ❌ helper-only | ✅ self | **KEEP_HELPER** | **保留** | — | PR-EXCL-3 wire active emit |
| `services/confidence_result_contract.py` | Branch 5 | shape validator | ⚠️ active reader uses (PR-CONF-2) | ✅ self | **KEEP_HELPER** | **保留** | — | PR-CONF-4 |
| `services/final_report_result_contract.py` | Branch 6 | shape validator | ❌ helper-only | ✅ self | **KEEP_HELPER** | **保留** | — | PR-FINAL-5 wire adapter |
| `services/review_result_contract.py` | Branch 7 | shape validator | ❌ helper-only | ✅ self | **KEEP_HELPER** | **保留** | — | — |
| `services/evaluation_result_contract.py` | Branch 8 | shape validator | ❌ helper-only | ✅ self | **KEEP_HELPER** | **保留** | — | — |
| `ui/presentation_payload_contract.py` | Branch 9 | UI shape validator | ❌ helper-only | ✅ self | **KEEP_HELPER** | **保留** | — | PR-UI-7（when ready） |
| `services/architecture_orchestrator.py` | Cross-layer / TEMP_FUTURE_ORCHESTRATOR | skeleton (status="skeleton_only") | ❌ no active import | ✅ self | **KEEP_HELPER** | **保留** | wire-in 必须改 ARCHITECTURE_ORCHESTRATOR_STATUS + 用户确认 | PR-ARCH-2 |
| `services/warning_cards.py` | Branch 6 helper | warning_card.v1 | ❌ no active import | ✅ self | **KEEP_HELPER** | **保留** | 未接 final_decision | PR-FINAL-5 |

### 6.3 总表统计

- `KEEP_CORE`: 11 (active 主链 + standard payload skeleton + UI tabs + projection_chain_contract + consistency_layer)
- `KEEP_INSPECT_READONLY`: 4
- `KEEP_HELPER`: 12
- `NO_BRIDGE_STILL_REQUIRED`: 6 (predict / V1 orchestrator / projection_v2_adapter / predict_legacy_adapter / predict_legacy_v2_bridge / projection_entrypoint subset)
- `NO_ACTIVE_CORE`: 1 (projection_entrypoint，与 NO_BRIDGE 重叠列出)
- `NO_UI_STILL_READS`: 4 (predict_tab / projection_v2_renderer / home_tab / history_tab，与 KEEP_CORE 重叠列出)
- `NO_STANDARD_REPLACEMENT_NOT_WIRED`: 0（独立项；统计入上面 NO_*）
- `MAYBE_QUARANTINE_AFTER_ACTIVE_GRAPH`: 0（本轮无足够证据）
- `MAYBE_DOC_ONLY`: 0（同上）
- `DELETE_NOT_ALLOWED`: 0（无显式锁定项；但 1.0 §13 hard rule 永久禁止
  trading / promotion 类模块）

> **结论**：本轮 archive readiness table 中**没有任何模块**可以立即
> archive。所有候选都是 `KEEP_*` 或 `NO_*`。

---

## 7. 立即不能删的模块

> 本节是"红线"。下一批 PR 启动前，以下模块**永久**不可被任何代码 PR
> 删除 / archive / 重命名 / 大改。

### 7.1 红线模块

| Module | 原因 |
|---|---|
| `predict.py` | UI Predict tab + 多 scripts + V1 orchestrator 顶层 import；删除会断 UI / replay / regression |
| `ui/predict_tab.py` | app.py 顶层 import；Predict tab 是用户主 UI |
| `app.py` | Streamlit 主入口；hard rule 3 锁最小改动 |
| `services/home_terminal_orchestrator.py` | app.py 直接 import；Home flow 入口 |
| `services/projection_orchestrator_v2.py` | active V2 主路径 |
| `services/projection_orchestrator.py` (V1) | V2 仍依赖其 `build_projection_orchestrator_result` |
| `services/projection_entrypoint.py` | predict.py degraded fallback + tool_router 依赖 |
| `services/projection_v2_adapter.py` | projection_entrypoint 依赖 |
| `services/predict_legacy_adapter.py` | predict.py 顶层 import；legacy overlay 必需 |
| `services/main_projection_layer.py` | Branch 3 主推算子 |
| `services/exclusion_layer.py` | Branch 4 主否定算子 |
| `services/confidence_evaluator.py` | Branch 5 主可信度算子 |
| `services/final_decision.py` | Branch 6 主 aggregator |
| `services/standard_projection_payload.py` | standard payload 基础 |
| `services/projection_chain_contract.py` | 跨层 chain helper |
| `services/consistency_layer.py` | consistency display layer |
| `services/architecture_orchestrator.py` (skeleton) | ownership skeleton；wire-in 必须改 status 常量 + 用户确认 |
| `services/warning_cards.py` | warning_card.v1 helper；下一批 PR-FINAL-5 候选基础 |
| 全部 18A ~ 18W contract validators / adapters | standard 基础；replacement 目标形状 |
| `services/contract_payload_inspector.py` / `_diff.py` / `_trend.py` / `_extras_dashboard.py` | Inspect tab 已 wire；read-only 工具 |

### 7.2 红线非代码项

| 项 | 原因 |
|---|---|
| `avgo_agent.db` | local-only；已 `.gitignore`；hard rule 28 / 16H §5 校正禁止处理 |
| `logs/` | 本轮不处理；hard rule 18 / 27 |
| `.claude/handoffs/` | hard rule 22；deliberate untracked |
| `.claude/worktrees/` | hard rule 23 |
| DB / DB schema | hard rule 16-17；不写不改 |
| trading / broker / live_trade | 1.0 §13 hard rule；永久禁止 |

---

## 8. 可能进入 quarantine 候选，但本轮不动

> 本节列**有迹象但无足够证据**的候选。本轮 18Z **不**给出 archive
> 决策——证据需要 PR-CLEAR-2（machine-readable active import graph 工具
> + tests）才能补齐。

### 8.1 候选列表

| 候选 | 当前迹象 | 缺失证据 | 处理 PR |
|---|---|---|---|
| `services/projection_orchestrator.py` 内部仅被 V2 引用的辅助 helper（如非 `build_projection_orchestrator_result`） | rg 显示部分 helper 仅 V2 内部用；细节需要 AST scan | machine-readable import graph + active caller diff | PR-CLEAR-2 |
| `services/predict_legacy_v2_bridge.py` 内 lazy `from predict import run_predict` 路径 | 主代码无直接 caller，仅测试 / 13 §3-§4 引用 | 全仓 caller scan | PR-CLEAR-2 |
| `services/projection_v2_adapter.py` 内可能存在的死分支 / 死键 | 仅 projection_entrypoint 引用 | 函数级 caller 覆盖率 | PR-CLEAR-2 + PR-PROJ-3+ |
| 16H Repository Clearing Decision Table 中标 `ARCHIVE_IN_REPO`（reports / docs）的项 | 17/x 文档已记录 | 用户单独确认 + 17A+ archive PR window | 17A+ archive PR（另议） |
| 16H 中标 `MOVE_OUTSIDE_REPO`（raw artifact / DB backup）的项 | 已 `.gitignore`；操作位于本地 | 用户单独确认 | 用户操作 + 不进 repo |

### 8.2 为什么不直接列模块名

> **本轮的核心原则**：任何"可以 archive / 可以 quarantine"的判断必须
> 有 machine-readable 证据。当前 18Z 仅基于 `rg` / 人工分析；这是
> **必要但不充分**。把单个模块名列出"可以 quarantine"会被下一批 PR
> 当作授权——这是危险的。

→ 18Z 只列**类别**和缺失证据；具体模块名留给 PR-CLEAR-2 工具化扫描。

---

## 9. 下一批建议（**仅候选；不实现**）

> 第三批七刀完成（18T / 18U / 18V / 18W / 18X / 18Y / 18Z）。第四批
> 选择决定由 18AA 单独写。以下是**可能**候选，**不**自动批准。

| 候选 PR | 来源 | 所属层 | 性质 | 风险 |
|---|---|---|---|---|
| **PR-CLEAR-2** | 18Z 本文件 §8 | 跨层 / tools+tests | machine-readable active import graph script + AST-level caller scan + readiness table 自动化测试 | L |
| **PR-PROJ-3** | 17G §13 | Branch 3 | main_projection_layer active emit standard keys（额外 alias，保留 legacy） | L |
| **PR-EXCL-3** | 17H §14 | Branch 4 | exclusion_layer active emit standard keys（额外 alias） | L |
| **PR-FINAL-5** | 17J §13 | Branch 6 | final_report_result.v1 adapter / passthrough 接 active path（仍保留 final_report_aggregator_result.v1 兼容） | M |
| **PR-FINAL-3** | 17J §13 | Branch 6 | consistency_layer freeze marker | L |
| **PR-CONF-4** | 17I §13 | Branch 5 | agreement_status / conflict_level enum 标准化 + medium 槽位 | L |
| **PR-ARCH-2** | 18Z 本文件 + 17J §13 | 跨层 / TEMP_FUTURE_ORCHESTRATOR | architecture_orchestrator dry-run composition（**不接** active path；仅 plan / contract 扩展） | L |
| **PR-UI-4** | 17M §16 | Branch 9 UI | Inspect tab active import graph display（消费 PR-CLEAR-2 输出） | L |
| **PR-REVIEW-4** | 17K §17 | Branch 7 | review_store / memory_store lifecycle schema plan（doc only） | L |
| **PR-EVAL-3** | 17L §16 | Branch 8 | replay manifest standard helper + tests | L |

> **本批不推荐 / 永久暂缓**：
>
> - PR-UI-7 Predict tab 迁移（H 风险；必须等 PR-FINAL-5 + PR-ARCH-2+
>   + UI 渲染层准备好）
> - 任何 archive / delete / move 动作（必须先有 PR-CLEAR-2 证据 +
>   用户单独确认）
> - 任何 trading / broker / promotion / replay 真实运行
> - 解锁 3R-5 / 3R-6（1.0 §12 七项前提仍未全部满足）

---

## 10. 为什么不能马上删 Bridge

把第 §6 表 + §7 红线综合：

1. **UI 仍读 legacy fields**：`ui/predict_tab.py` / `ui/home_tab.py` /
   `ui/history_tab.py` 都还在直接读 `final_bias` / `final_confidence` /
   `primary_projection` / `final_projection`。删除 predict.py /
   predict_legacy_adapter / final_decision 中的 legacy 输出，UI 立刻
   炸。
2. **predict.py 是 active entrypoint**：`ui/predict_tab.py:10` /
   `services/projection_orchestrator.py:15` /
   `services/contract_replay_writer.py:83` /
   `scripts/run_e2e_loop.py:108` 五处 `from predict import run_predict`。
3. **projection / exclusion active output 仍 legacy**：
   `main_projection_layer.py:331-359` 仍输出 `predicted_top1` /
   `predicted_top2`；`exclusion_layer.py:71-233` 仍输出
   `triggered_rules` / `triggered_rule` / `excluded`。adapter 已存在
   但只在测试链使用。
4. **architecture_orchestrator skeleton 未接**：
   `ARCHITECTURE_ORCHESTRATOR_STATUS = "skeleton_only"` /
   `active_path_connected = False`。wire-in 是 PR-ARCH-2 的任务，
   且必须用户单独确认。
5. **final_report_result.v1 adapter 未接 active path**：
   `final_decision` 仍输出 `final_report_aggregator_result.v1`；
   warning_cards 已有 schema 但无 producer。
6. **replay / calibration / evaluation manifest 未完成**：
   PR-EVAL-3（replay manifest）/ PR-EVAL-4（calibration summary
   contract）/ PR-EVAL-7（active_rule_pool_calibration offline-only）
   全部未启动。
7. **没有 machine-readable import graph**：当前 readiness table 基于
   `rg` 人工分析；`PR-CLEAR-2` 必须先把这个工具化。
8. **用户未单独批准任何 archive 动作**。1.0 §12 / 17D §11 / 18A §14 /
   18J §15 / 18S §15 一致：所有 archive / delete 必须用户显式确认。

→ **结论**：第三批结束后，archive readiness 仍然是
**0 个模块可立即 archive**。任何"删 Bridge / archive legacy"动作必须
等以上 8 项前置全部满足 + 用户单独确认。

---

## 11. 为什么仍不能进入 3R-5 / 3R-6

1.0 §12 七项前提（重述）：

| # | 前提 | 状态 |
|---|---|---|
| 1 | 9 分支站队完成 | ✅ |
| 2 | 目标 schema 唯一化 | ⚠️ contract validators 已就位；active emit / read 仍混合 |
| 3 | 隔离 / quarantine 计划已落地 | ⚠️ 计划已落（16D / 16H）；执行未启 |
| 4 | 核心链 refactor 计划完成 | ✅（16E / 16I） |
| 5 | 第一批代码 PR 已合并并通过 regression | ✅（18B ~ 18Y / 8 + 8 + 6 = 22 个代码 PR + selection docs） |
| 6 | standard active path | ❌ 仍是 V1 + V2 + home_terminal 三套 + adapter only |
| 7 | evaluation guard | ⚠️ 边界测试已落（PR-EVAL-2）；replay manifest / calibration summary / active_rule_pool offline-only 未启 |
| 8 | replay manifest | ❌ |
| 9 | calibration summary | ❌ |
| 10 | UI / review lifecycle 边界 | ⚠️ Inspect tab + briefing warning-only + briefing read-only boundary 已落；review_store / memory lifecycle 未规划 |
| 11 | 用户单独确认 | ❌ 必须 user 显式 |

**还差**：第 2 / 3 / 6 / 7 / 8 / 9 / 10 / 11 项。

> **第三批仍不进入 3R-5 / 3R-6**。这是**永久原则**。
> `continuous_smoothing` / promotion / production promotion 等都属于
> 3R-5 / 3R-6 阶段；必须等以上前提全部满足 + 用户单独确认后才能解锁。
>
> 1.0 §12 / 13 §9 / 15 §8 / 16I §15 / 17D §11 / 18A §14 / 18J §15 /
> 18S §13 / 18Z §11 持续锁定。

---

## 12. 本轮不允许事项确认

**18Z 起，本轮（直到用户确认 18AA 启动之前）严格禁止**：

- ❌ 不改代码（无 `.py` 文件被修改；本轮 0 修改）
- ❌ 不新增测试（`tests/` 字节不变）
- ❌ 不删除文件
- ❌ 不移动文件
- ❌ 不 archive（不创建 `archive/` 目录、不 `git mv` legacy 模块）
- ❌ 不修改 `.gitignore`
- ❌ 不处理 `avgo_agent.db`（含 backup）
- ❌ 不处理 handoff
- ❌ 不处理 logs / DB backup / `.claude/worktrees/`
- ❌ 不写 DB / 不改 DB schema
- ❌ 不跑 replay / holdout / calibration
- ❌ 不实现 PR-CLEAR-2（留待 18AA / 18AB）
- ❌ 不实现 PR-PROJ-3 / PR-EXCL-3 / PR-FINAL-5 / PR-CONF-4 /
  PR-ARCH-2 / PR-UI-4 / PR-REVIEW-4 / PR-EVAL-3
- ❌ 不接 trading
- ❌ 不输出 buy / sell / hold / hard / forced / required
- ❌ 不污染 2026-01-01 之后 final holdout
- ❌ 不进入 3R-5 / 3R-6（永久原则；本轮再次重申）
- ❌ 不复活 `continuous_smoothing*` / `archive/legacy/root_stubs/*` /
  promotion 三模块
- ❌ 不借 18Z 顺手做代码改动（本轮全部 markdown 改动）

> 与 17D §11 / 17E ~ 17M §禁止事项 / 18A §14 / 18J §15 / 18S §15
> 一致；本轮再次锁定。

---

## 13. 推荐下一步

**推荐**：

> **Step 18AA / PR-CLEAR-2：machine-readable active import graph
> script + tests**

**理由**：

- 本 18Z 表明：当前 archive readiness 的所有判断都是基于 `rg` /
  人工分析。任何"可以删"或"可以 quarantine"的下一步都需要**机器可
  验证的证据**。
- PR-CLEAR-2 = 添加一个 `scripts/active_import_graph.py`（或
  `services/active_import_graph.py`）+ 对应 `tests/test_active_import_graph.py`
  AST-level 扫描每个候选模块的 active caller，输出结构化报告。
- 不接 active path；不动 Bridge；不动 archive；不动 UI / DB。
- 风险 L；与 18T / 18U / 18V / 18X / 18Y 同等级别（tests / boundary /
  read-only 工具）。
- 是 **PR-PROJ-3 / PR-EXCL-3 / PR-FINAL-5 / PR-ARCH-2 / 任何
  archive PR** 的前置——没有 machine-readable graph，下一批"删 / 改
  / 接"都没有验证基线。

**或者更稳的备选**：

> **Step 18AA：Fourth Layer-Based Implementation Batch Selection**
>
> 与 18A / 18J / 18S 一致——先写选择决定，**不**直接启动 PR。让用户
> 在 18AB 选择第一刀（CLEAR-2 vs PROJ-3 vs FINAL-5 vs ARCH-2 vs
> EVAL-3）。

→ 我推荐 **PR-CLEAR-2**（直接启动 implementation），原因是：

1. 18S 已经做过 selection 文档（第三批七刀）；第四批的 selection 文档
   会重复 60% 内容。
2. PR-CLEAR-2 是**所有第四批 PR 的共同前置**——无论第四批先做
   PROJ-3 还是 FINAL-5 还是 ARCH-2，都需要 machine-readable graph。
3. PR-CLEAR-2 风险 L；不接 active path；可独立回滚。

**前置条件**：

- 18Z 入 main
- 用户单独确认 18AA 启动

> **本轮 18Z 只给推荐**；**不**启动 18AA。

---

## 14. 严守边界

本轮 Step 18Z **只**写 Legacy Bridge Active Import Graph & Archive
Readiness Table：

- ❌ 未改代码（无 `.py` 文件被修改；`git diff --stat` 仅 markdown）
- ❌ 未新增测试（`tests/` 字节不变）
- ❌ 未删除文件
- ❌ 未移动文件
- ❌ 未 archive 任何模块
- ❌ 未修改 `.gitignore`
- ❌ 未处理 `avgo_agent.db`
- ❌ 未处理 handoff（worktree clean except deliberate keep；无新增
  deliberate untracked）
- ❌ 未处理 logs / DB backup / `.claude/worktrees/`
- ❌ 未跑 replay / validation / historical evaluation / holdout /
  calibration
- ❌ 未写 DB / 未改 DB schema
- ❌ 未默认迁移 `run_predict` 到 V2
- ❌ 未接 trading
- ❌ 未输出 buy / sell / hold / hard / forced / required
- ❌ 未启用任何 candidate / 未复活 `continuous_smoothing`
- ❌ 未触碰 RISK-1 / RISK-2 / RISK-3 / RISK-7 / RISK-8 / RISK-9 /
  RISK-10
- ❌ 未进入 3R-5 / 3R-6
- ❌ 未启动任何代码 PR（PR-CLEAR-2 候选要等 18AA）
- ❌ 未实现 architecture_orchestrator wire-in
- ❌ 未删 Bridge / 未 archive legacy
- ❌ 未迁 Predict tab
- ❌ 未做任何局部 patch
- ❌ 未 commit / 未 push（按本轮指令）

唯一新增文件：[tasks/record_18z_legacy_bridge_active_import_graph_archive_readiness.md](tasks/record_18z_legacy_bridge_active_import_graph_archive_readiness.md)（本文件）。

后续修改路径：任何对 §3 active path 总览 / §4 模块清单 / §5 standard
replacement / §6 archive readiness table / §7 红线 / §8 quarantine
候选 / §9 下一批候选 / §10 ~ §11 各暂缓理由 / §12 禁止事项 / §13
下一步推荐 的调整，都必须**显式更新本文件**；同时检查是否需要同步
更新 1.0 / 16H / 17D / 17E ~ 17M / 18A / 18J / 18S。
