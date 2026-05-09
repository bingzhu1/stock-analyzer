# 16E记录：Core Chain Refactor Plan

> 本记录是 **Step 16E：核心链重构执行计划**。1.0 canonical / 16A
> blueprint / 16B inventory / 16C target dataflow & contract decision /
> 16D isolation & quarantine plan 已全部入 main（main 最新 commit
> `694450e`）。本轮把 16C / 16D 决策**翻译为**第一批可执行 PR：
> PR-1 ~ PR-6。
>
> 本轮**只**写执行计划：未改业务代码、未新增测试、未删除文件、
> 未移动文件、未修改 `.gitignore`、未处理 handoff、未处理 logs /
> DB backup / `.claude/worktrees/`、未跑 replay / validation /
> historical evaluation、未写 DB / 未改 DB schema、未默认迁移
> `run_predict` 到 V2、未接 trading、未输出 buy / sell / hold /
> hard / forced / required、未进入 3R-5 / 3R-6、未 commit / 未 push。
>
> 唯一 deliverable：本文件。

---

## 1. Step 16E 目的

把 16C target dataflow + standard schema 决策 + 16D isolation /
quarantine 计划，**翻译为**第一批可执行 PR 的清单：

- 每个 PR 给出：**目标 / 范围 / 文件清单 / 测试 / 验收标准 / 回滚策略**
- 每个 PR **单独 commit、单独 revert、单独 regression**
- 顺序遵循"最小风险先行"：先消除"软边界"（PR-1/2/3），再新建主入口
  MVP（PR-4），再写迁移计划（PR-5），最后挂 deprecation marker（PR-6）

> **本文件性质**：执行计划（impl plan），不是设计（design）也不是 impl 本身。
> 设计在 16C；isolation 政策在 16D；本计划落地从 16F 起。

---

## 2. 当前前置条件

| 项 | 状态 |
|---|---|
| 1.0 canonical principles 已入 main | ✅ commit `5c209bb` |
| 16A architecture reset blueprint 已入 main | ✅ commit `9b98ad5` |
| 16B module standup ownership inventory 已入 main | ✅ commit `bdd1314` |
| 16C target dataflow & contract decision 已入 main | ✅ commit `b05d7c8` |
| 16D isolation / quarantine plan 已入 main | ✅ commit `694450e` |
| Step 12 boundary fixes / 13 regression / 14 cleanup / 15 signoff | ✅ 全部入 main |
| main 最新 commit | `694450e` |
| worktree 唯一 deliberate untracked | `.claude/handoffs/task_089_post_pr_cleanup.md` |
| 战略阶段 | 从 isolation plan（16D）→ refactor PR plan（16E 本轮）|
| 3R-5 / 3R-6 | ❌ 仍然不允许进入（1.0 §12 / 16A §18） |

---

## 3. 第一批 PR 总顺序

| 序号 | 名称 | 性质 | 风险 | 依赖 |
|---|---|---|---|---|
| **PR-1** | `peer_alignment` 抽公共模块 | 代码（新增 + import 调整） | L | — |
| **PR-2** | `main_projection` 去 `exclusion_result` 形参 | 代码（删形参 + caller 调整） | L | PR-1 |
| **PR-3** | `confidence` key 对齐 | 代码（schema 兼容层） | M | PR-2 |
| **PR-4** | `architecture_orchestrator` MVP | 代码（新建模块） | M | PR-3 |
| **PR-5** | UI / evaluation payload migration plan | 文档 | L | PR-4 |
| **PR-6** | Bridge deprecation markers | 代码（**仅 docstring**） | L | PR-4 |

**说明**：

- PR-1 / 2 / 3 都是 **最小软边界修复**：消除"反向 import"、"形参守护"、
  "key 不齐"三个 16B 已识别的结构性问题，**不**触动 orchestrator。
- PR-4 才**新建**未来主入口 `services/architecture_orchestrator.py`，
  以 MVP 形式存在；**不**替换 `predict.py`、**不**接 UI、**不**接 trading。
- PR-5 是**迁移计划文档**，不直接迁 UI / evaluation / replay。
- PR-6 **只加 deprecation marker**（docstring），不删除任何 Bridge 模块、
  不改任何业务行为。

> **顺序硬约束**：PR-2 必须在 PR-1 后；PR-3 必须在 PR-2 后；PR-4 必须
> 在 PR-3 后。PR-5 / PR-6 在 PR-4 后任意顺序，但 PR-6 推荐在 PR-5 之后
> （因为 deprecation marker 内容会引用 PR-5 的迁移计划）。

---

## 4. PR-1：`peer_alignment` 抽公共模块

### 4.1 目标

- 新建 `services/peer_alignment.py`
- 从 `services/exclusion_layer.py` 迁出 `build_peer_alignment` 函数
- `services/main_projection_layer.py` 与 `services/exclusion_layer.py`
  都从 `services/peer_alignment.py` import
- **行为零变化**（byte-equivalent 输出 / semantic-equivalent 输出）
- 解决 16B §5.5 / 16C §3.3 / 16D §6 识别的"Projection 反向 import
  Exclusion 模块"边界违规

### 4.2 范围（文件清单）

**新增**：

- `services/peer_alignment.py`（**新文件**；从
  `services/exclusion_layer.py:64-134` 完整搬迁
  `build_peer_alignment` + 必要的私有 helper `_normalize_features` /
  `_safe_float` / `_pick_float` / `_as_dict`，或在 PR-1 内部决定 helper
  归属：是迁到 `peer_alignment.py` 还是抽到第三个共享 module）

**修改**：

- `services/exclusion_layer.py`：
  - 删除本地 `build_peer_alignment` 定义（[exclusion_layer.py:64](services/exclusion_layer.py:64)）
  - 改为 `from services.peer_alignment import build_peer_alignment`
  - 内部 `exclude_big_up` / `exclude_big_down` / `run_exclusion_layer` 的
    `build_peer_alignment(...)` 调用保持不变
- `services/main_projection_layer.py`：
  - 改 `from services.exclusion_layer import build_peer_alignment`
    （[main_projection_layer.py:18](services/main_projection_layer.py:18)）
  - 改为 `from services.peer_alignment import build_peer_alignment`
- `services/projection_chain_contract.py`：
  - 检查是否有间接引用；如有同步迁移

**新增 tests**（PR-1 内随同提交）：

- `tests/test_peer_alignment.py`：覆盖
  - 5 输入 case（all bullish / all bearish / mixed / missing peer / unknown）
  - 输出 schema 与原 `services.exclusion_layer.build_peer_alignment`
    **byte-equivalent**（直接做对比断言）
- `tests/test_peer_alignment_import_boundary.py`：负面 import 测试
  - 断言 `services.main_projection_layer` 模块不再 import
    `services.exclusion_layer`（AST grep）
  - 断言 `services.exclusion_layer` 模块不再定义 `build_peer_alignment`

### 4.3 不做的事

- ❌ 不改 `build_peer_alignment` 内部逻辑（包括打分阈值 / 输出 key /
  reasons 文案）
- ❌ 不改 `services/exclusion_layer.run_exclusion_layer` 输出 schema
- ❌ 不改 `services/main_projection_layer.build_main_projection_layer`
  输出 schema
- ❌ 不改 `services/projection_chain_contract.py` 的 feature helpers
- ❌ 不动 V2 / home_terminal / projection_orchestrator
- ❌ 不动 UI

### 4.4 验收标准

| # | 指标 | 期望 |
|---|---|---|
| 1 | 输出 byte-equivalent | `services.peer_alignment.build_peer_alignment(features)` 与 PR-1 前的 `services.exclusion_layer.build_peer_alignment(features)` 在 5 个 input case 上**字典级 deep-equal** |
| 2 | `main_projection_layer` 不再 import `exclusion_layer` | grep `from services.exclusion_layer` / `import services.exclusion_layer` 在 main_projection_layer.py 中**返回空** |
| 3 | `exclusion_layer` 不再拥有 `build_peer_alignment` 业务定义 | grep `^def build_peer_alignment` 在 exclusion_layer.py 中**返回空** |
| 4 | `exclusion_layer.run_exclusion_layer` 输出 byte-equivalent | 5 个 case 上与 PR-1 前**字典级 deep-equal** |
| 5 | `main_projection_layer.build_main_projection_layer` 输出 byte-equivalent | 5 个 case 上与 PR-1 前**字典级 deep-equal** |
| 6 | `pytest -q` | passed 数 ≥ 当前 baseline + 新增测试数；0 failed / 0 errors |
| 7 | 14–15 file focused boundary suite（13 §3.2 / 15 §3.3） | 全 green |
| 8 | `bash scripts/check.sh` | All compile checks passed |

### 4.5 回滚策略

- **单独 commit**：3 个文件 + 2 个新测试一起 commit
- **回滚命令**：`git revert <PR-1 commit hash>`，应该能干净回滚（peer_alignment.py
  被恢复成"删除文件"，其它两个 import 改回旧形式）
- **失败响应**：任一验收标准失败 → 立即停止；不补 fix commit；revert 后
  root-cause 重做

---

## 5. PR-2：`main_projection` 去 `exclusion_result` 形参

### 5.1 目标

- `services/main_projection_layer.py` 的 `build_main_projection_layer`
  与 `run_main_projection_layer` **删除** `exclusion_result` 形参
- 删除 [main_projection_layer.py:298](services/main_projection_layer.py:298)
  `del exclusion_result` 软边界守护
- 全部 caller 同步更新（不再传 `exclusion_result`）
- 对应 boundary tests 同步更新（断言 signature）
- **行为零变化**

### 5.2 范围（文件清单）

**修改**：

- `services/main_projection_layer.py`：
  - `build_main_projection_layer(...)` 签名删除 `exclusion_result` 参数
    （[main_projection_layer.py:286](services/main_projection_layer.py:286)）
  - `run_main_projection_layer(...)` 签名删除 `exclusion_result` 参数
    （[main_projection_layer.py:367-385](services/main_projection_layer.py:367)）
  - 删除 `del exclusion_result` 守护
  - docstring 同步更新（删除"deprecated and ignored"段落，改为"
    not part of the API"）
- caller 调用点全清单（PR-2 必须**全量修复**，不能留下"传了被删形参"
  的失败 site）：
  - `services/home_terminal_orchestrator.py:151-155`
    （`build_main_projection_layer(...)` 调用，**当前未传** `exclusion_result`，
    无需改；但要 spot-check 确认）
  - `services/projection_orchestrator_v2.py`（V2 链 standardized
    chain；当前调用 `build_main_projection_layer(...)` 时也未传
    `exclusion_result`，但要 spot-check 确认）
  - tests 中所有调用点（grep `build_main_projection_layer` /
    `run_main_projection_layer` 全 repo）

**修改 tests**：

- `tests/test_projection_exclusion_decoupling_boundary.py` 等 boundary
  suite：把"`build_main_projection_layer` 接受但忽略 `exclusion_result`"
  的断言改为"`build_main_projection_layer` 不接受 `exclusion_result`
  形参（`TypeError` on call）"
- 任何当前显式传 `exclusion_result=...` 的测试调用点：删 kwarg

### 5.3 不做的事

- ❌ 不改 `build_main_projection_layer` 内部计算逻辑
- ❌ 不改输出 schema
- ❌ 不动 V2 / home_terminal 编排顺序
- ❌ 不动 exclusion_layer
- ❌ 不动 confidence_evaluator

### 5.4 验收标准

| # | 指标 | 期望 |
|---|---|---|
| 1 | signature 不接受 `exclusion_result` | `inspect.signature(build_main_projection_layer)` 中**不**含 `exclusion_result` 参数 |
| 2 | 调用 `build_main_projection_layer(..., exclusion_result=...)` 抛 `TypeError` | 新增 boundary test 断言 |
| 3 | 输出 byte-equivalent | 5 个 case 上与 PR-2 前**字典级 deep-equal** |
| 4 | 现有 boundary tests（07A / 11A / 12A 系列）继续 green | full passed |
| 5 | `pytest -q` | passed 数与 PR-1 后 baseline 一致（除新增 boundary 断言数）；0 failed |
| 6 | `bash scripts/check.sh` | All compile checks passed |

### 5.5 回滚策略

- **单独 commit**：1 个 services 文件 + N 个 tests 一起 commit
- **回滚命令**：`git revert <PR-2 commit hash>`
- **失败响应**：同 PR-1

---

## 6. PR-3：`confidence` key 对齐

### 6.1 目标

- `services/confidence_evaluator.py` 能读取 **standard projection /
  exclusion schema**（07A / 07B 草案命名）
- 同时**兼容** 当前 interim schema（`predicted_top1.state` /
  `triggered_rule`），通过显式映射函数（不是猜测）
- `architecture_orchestrator`（PR-4）出现后，逐步只用 standard schema
- 让 `agreement_status` 不再因 key mismatch 恒为 `unknown`；只在
  **真实缺字段**时才 `unknown`
- **不改写** `projection_result` / `exclusion_result`（07C §5 不变）
- 调用方在 home_terminal / V2 显式传 `calibration_context={"ready": False}`
  作为 explicit fallback（**不**允许 silent default）

### 6.2 范围（文件清单）

**修改**：

- `services/confidence_evaluator.py`：
  - 在 `_compute_agreement` 之上加**显式 schema adapter**：
    - 优先读 `proj.most_likely_state` / `proj.ranked_states`（标准 schema）
    - 若为 None 则读 `proj.predicted_top1.state` /
      `[proj.predicted_top1.state, proj.predicted_top2.state]`（interim）
    - 优先读 `excl.most_unlikely_state` /
      `excl.ranked_unlikely_states`（标准 schema）
    - 若为 None 则按显式映射（**不是 LLM**）：
      - `triggered_rule == "exclude_big_up"` → `most_unlikely_state = "大涨"`
      - `triggered_rule == "exclude_big_down"` → `most_unlikely_state = "大跌"`
      - 其它 → `most_unlikely_state = None`
  - 该映射用 `services/projection_chain_contract.excluded_state_from_result`
    已有逻辑（已存在），**不重复实现**
  - `_FORBIDDEN_FIELDS` / `non_mutation_confirmations` 不变
- `services/home_terminal_orchestrator.py:169-174`：
  - `build_confidence_result(...)` 调用追加 `calibration_context={"ready": False}`
- `services/projection_orchestrator_v2.py:585-590`：
  - 同上追加 `calibration_context={"ready": False}`

**新增 tests**：

- `tests/test_confidence_evaluator_schema_compat.py`：
  - 输入 standard schema → agreement 正确（aligned / partial / strong / unknown 四种）
  - 输入 interim schema（`predicted_top1.state` + `triggered_rule`）→ agreement 正确
  - 输入混合（部分 standard + 部分 interim）→ agreement 正确
  - 输入完全缺字段 → agreement = `unknown`，并在 `confidence_reasoning` 中
    含明确"key missing"短语
- 现有 `tests/test_confidence_evaluator.py` / `test_confidence_result_wiring_boundary.py`：
  - 增加 explicit `calibration_context={"ready": False}` 案例的 reasoning
    断言（不再 silent unknown，必须有明确短语）

### 6.3 不做的事

- ❌ 不改 `_FORBIDDEN_FIELDS`
- ❌ 不引入 calibration table（calibration 接入是另一个独立 PR）
- ❌ 不改 `combined_confidence` 算法
- ❌ 不动 `final_decision.py`
- ❌ 不修改 main_projection / exclusion 的输出 schema（schema 对齐 07A/07B
  是 PR-4 / 后续 PR 的事）
- ❌ 不读 future outcome / 2026 holdout

### 6.4 验收标准

| # | 指标 | 期望 |
|---|---|---|
| 1 | standard schema → agreement 正确 | 4 case（aligned / partial / strong / unknown）全部命中 |
| 2 | interim schema → agreement 正确 | 4 case 全部命中（exclude_big_up → 大涨 / exclude_big_down → 大跌 映射） |
| 3 | 混合 schema → agreement 正确 | 不抛错；按 standard 优先 |
| 4 | 完全缺字段 → agreement = unknown | reasoning 含"key missing"或等价中文短语 |
| 5 | `unknown` 不再因为 key mismatch 频繁出现 | home_terminal / V2 调用追加 `calibration_context={"ready": False}` 后，confidence level 仍是 `unknown`（calibration 未接入），但 reasoning 中明确"calibration not wired"而非"key mismatch" |
| 6 | `non_mutation_confirmations` 不变 | `projection_result_mutated == False` / `exclusion_result_mutated == False` |
| 7 | 现有 11C / 12C boundary tests 全 green | full passed |
| 8 | `pytest -q` | passed 数 ≥ baseline + 新增；0 failed |
| 9 | `bash scripts/check.sh` | All compile checks passed |

### 6.5 回滚策略

- **单独 commit**：1 个 confidence_evaluator + 2 个 caller + N 个 tests
- **回滚命令**：`git revert <PR-3 commit hash>`
- **失败响应**：同前

---

## 7. PR-4：`architecture_orchestrator` MVP

### 7.1 目标

- **新建** `services/architecture_orchestrator.py`
- 产出 `standard_projection_payload.v1` **skeleton**（schema 顶层完整，
  字段值可以来自现有 main_projection / exclusion / confidence_evaluator /
  final_decision 实现）
- 串联：Feature → Projection / Exclusion（并行）→ Confidence → Final Report
- **不**默认接 UI / replay / evaluation
- **不**替换 `predict.py`
- **不**跑 trading
- **不**写 DB
- 仅暴露 `build_standard_projection_payload(...)` 函数 + 一个 lightweight
  test harness 入口

### 7.2 范围（文件清单）

**新增**：

- `services/architecture_orchestrator.py`（**新文件**）：
  - public API：`build_standard_projection_payload(*, symbol, target_date_str, coded_df, target_row, target_ctx, peer_loader=None) -> dict`
  - 内部步骤（顺序）：
    1. 调 `services.projection_chain_contract.build_feature_payload_from_recent_window`
       构造 `feature_payload`（含 `peer_alignment`，PR-1 已迁出）
    2. 并行：调 `services.main_projection_layer.build_main_projection_layer`
       产 `projection_result`；调 `services.exclusion_layer.run_exclusion_layer`
       产 `exclusion_result`
    3. 调 `services.confidence_evaluator.build_confidence_result(...,
       calibration_context={"ready": False})` 产 `confidence_result`
    4. 调 `services.final_decision.build_final_decision(...)` 包装为
       `final_report`（schema 转译可以 PR-4 内做最小翻译；完整对齐 07D §9 留待后续 PR）
    5. 组装 `standard_projection_payload.v1`：
       ```python
       {
         "schema_version": "standard_projection_payload.v1",
         "metadata": {...},                     # symbol/target/produced_at/orchestrator_version/data_window_days/non_mutation_confirmations
         "feature_payload": feature_payload,
         "projection_result": projection_result,
         "exclusion_result": exclusion_result,
         "confidence_result": confidence_result,
         "final_report": final_report_dict,
         "review_stub": {},                     # Branch 7 占位
         "evaluation_stub": {},                 # Branch 8 占位
         "compatibility_metadata": {            # Bridge only
           "legacy_predict_result": None,       # MVP 不填；后续 PR 决定
           "deprecation_status": "stable_for_internal_use",
         },
       }
       ```

**新增 tests**：

- `tests/test_architecture_orchestrator_mvp.py`：
  - `build_standard_projection_payload(...)` 在 fixture coded_df 上产出
    schema-validated payload
  - 顶层包含 9 个字段：`schema_version` / `metadata` / `feature_payload` /
    `projection_result` / `exclusion_result` / `confidence_result` /
    `final_report` / `review_stub` / `evaluation_stub` / `compatibility_metadata`
  - `metadata.non_mutation_confirmations` 全 `False`
  - `metadata.data_window_days` 当前 MVP 为 `20`（标 `"legacy_window"` 子 flag），
    并在 `compatibility_metadata.deprecation_status` 中说明 15d 迁移待办
- `tests/test_architecture_orchestrator_import_boundary.py`：负面 import
  - 断言 `services.architecture_orchestrator` 不 import `predict`
  - 断言 `services.architecture_orchestrator` 不 import
    `services.projection_orchestrator`
  - 断言 `services.architecture_orchestrator` 不 import
    `services.projection_orchestrator_v2`
  - 断言 `services.architecture_orchestrator` 不 import
    `services.predict_legacy_adapter` / `services.predict_legacy_v2_bridge`

### 7.3 不做的事

- ❌ 不改 `predict.py`（不接入 architecture_orchestrator）
- ❌ 不改 `ui/predict_tab.py`（UI 仍走旧链）
- ❌ 不改 `services/contract_replay_writer.py`（replay 仍走旧链）
- ❌ 不改 `services/home_terminal_orchestrator.py` 内部实现（仍是
  app.py 主页路径）
- ❌ 不改 V2 orchestrator
- ❌ 不接 calibration table
- ❌ 不产生 legacy `PredictResult`
- ❌ 不输出 trading / hard / forced / required
- ❌ 不写 DB / 不改 schema
- ❌ 不在主 schema 中加 `simulated_trade` / 任何 trading 字段
- ❌ 不切 15d 窗口（标 legacy；待独立 PR）
- ❌ 不合并 `consistency_layer`（PR-4 仍可调用现有 `final_decision` 包装）

### 7.4 验收标准

| # | 指标 | 期望 |
|---|---|---|
| 1 | `architecture_orchestrator.py` 不 import `predict` / `projection_orchestrator` / `projection_orchestrator_v2` / `predict_legacy_adapter` / `predict_legacy_v2_bridge` | 负面 import test 全部通过 |
| 2 | `build_standard_projection_payload(...)` 输出 9 个顶层字段 | schema test 通过 |
| 3 | 输出**不**含 legacy `PredictResult` 字段（`final_bias` / `final_confidence` / `primary_projection` / `peer_adjustment` / `final_projection` / `path_risk` / `peer_path_risk_adjustment`） | 负面字段 test 通过 |
| 4 | 输出**不**含 trading / hard / forced / required / `simulated_trade` 字段 | 负面字段 test 通过 |
| 5 | `metadata.non_mutation_confirmations` 全 `False` | schema test 通过 |
| 6 | `metadata.schema_version == "standard_projection_payload.v1"` | schema test 通过 |
| 7 | focused tests green（PR-4 新增 + 现有 11C / 12C / 14E hygiene 等） | full passed |
| 8 | `pytest -q` | passed 数 ≥ baseline + 新增；0 failed |
| 9 | `bash scripts/check.sh` | All compile checks passed |

### 7.5 回滚策略

- **单独 commit**：1 个新 services 文件 + 2 个新 tests
- **回滚命令**：`git revert <PR-4 commit hash>`，干净删除
  `services/architecture_orchestrator.py` 与 2 个 test 文件
- **失败响应**：同前

---

## 8. PR-5：UI / evaluation payload migration plan

### 8.1 目标

- **只写计划文档**：`tasks/record_16e_pr5_ui_evaluation_migration_plan.md`
- 明确 UI 如何从 `final_bias` / `final_confidence` 迁到
  `final_report.projection_section / confidence_section / etc.`
- 明确 evaluation 只读 `standard_projection_payload.v1`
- 明确 replay / `services/contract_replay_writer.py` 如何切到
  `architecture_orchestrator`
- **不**改 UI 代码
- **不**跑 evaluation
- **不**迁移 replay

### 8.2 范围

**新增**：

- `tasks/record_16e_pr5_ui_evaluation_migration_plan.md`（**新文件**）

**不修改**：

- 任何 `.py` 文件
- 任何 tests

### 8.3 文档内容大纲

PR-5 文档至少包含：

1. **UI 字段映射表**：
   - `final_bias` → `final_report.projection_section.most_likely_state` →
     direction（中文映射）
   - `final_confidence` → `final_report.confidence_section.combined_confidence.level`
   - `primary_projection` → `final_report.projection_section`
   - `final_projection` → `final_report`（整段）
   - `path_risk` → 标注为 deprecated；不进 standard payload
   - `peer_adjustment` → 拆解：peer 信号 → `feature_payload.peer_alignment`；调整语义被 1.0 §6 / §8 否决，不进 standard payload
2. **UI tab 迁移顺序**：
   - 先迁低风险 tab（read-only display）：`history_tab` / `inspect_tab`
   - 中风险 tab：`home_tab` / `review_tab`
   - 最后迁主入口 tab：`predict_tab`（Bridge 退出条件 #1）
3. **evaluation 迁移顺序**：
   - 先迁离线 dashboard：`contract_payload_*`
   - 再迁 replay 写入：`contract_replay_writer.py`（Bridge 退出条件 #2）
   - 最后迁 e2e：`scripts/run_e2e_loop.py`
4. **回滚 plan**：每个 UI / evaluation 子 PR 独立 commit；可 git revert
5. **依赖**：所有 UI / evaluation 子 PR 都依赖 PR-4（`architecture_orchestrator` MVP）已合

### 8.4 不做的事

- ❌ 不改任何 UI 代码
- ❌ 不迁移 evaluation
- ❌ 不动 replay

### 8.5 验收标准

| # | 指标 | 期望 |
|---|---|---|
| 1 | 仅新增 1 个 doc 文件 | `git status --short` 显示 `?? tasks/record_16e_pr5_ui_evaluation_migration_plan.md` |
| 2 | doc 包含上述 5 项内容 | manual review |
| 3 | 不需要 `pytest`（doc-only） | 跳过 |

### 8.6 回滚策略

- 单独 commit；`git revert` 删 doc

---

## 9. PR-6：Bridge deprecation markers

### 9.1 目标

- 给以下模块加 **clearly marked deprecation / migration bridge docstring**：
  - `predict.py`
  - `services/predict_legacy_adapter.py`
  - `services/predict_legacy_v2_bridge.py`
  - `services/projection_orchestrator.py`
  - `services/projection_orchestrator_v2.py`
  - `services/home_terminal_orchestrator.py`
  - `services/predict_summary.py`
  - `services/consistency_layer.py`
  - `services/peer_adjustment.py`
  - `services/primary_20day_analysis.py`
  - `services/historical_probability.py`
  - `services/projection_entrypoint.py`
  - `services/projection_v2_adapter.py`
- **不改行为**
- **不删除文件**
- **不移动文件**

### 9.2 范围（文件清单）

仅修改 13 个文件**顶部 docstring**（每个文件加约 10–20 行
deprecation 注释；模块级常量可选 `_BRIDGE_KIND` / `_DEPRECATION_STATUS`，
**不**改业务逻辑 / 不改 import / 不改函数签名）。

每条 docstring 必须含：

- **Status label**（与 16B / 16D 对齐）：`TEMP_MIGRATION_BRIDGE` 或
  `LEGACY_ACTIVE_DEPENDENCY`
- **Reason**：1.0 / 16C / 16D 决策的引用
- **Exit condition**：来自 1.0 §10 / 16C §11 的具体阶段（Phase X）
- **Future action**：archive / merge / refactor 中的哪一个；预计 Phase
- **Cross-reference**：链接到 `tasks/record_16d_isolation_quarantine_plan.md`
  对应章节

### 9.3 不做的事

- ❌ 不改任何函数 / 类签名
- ❌ 不改任何 import
- ❌ 不改任何业务逻辑
- ❌ 不删除任何代码
- ❌ 不引入新模块
- ❌ 不改 tests

### 9.4 验收标准

| # | 指标 | 期望 |
|---|---|---|
| 1 | 13 个文件的 docstring 全部含 deprecation marker | manual review + grep `TEMP_MIGRATION_BRIDGE` / `LEGACY_ACTIVE_DEPENDENCY` |
| 2 | 业务行为完全不变 | full pytest 数字与 PR-6 前**完全一致**（passed / skipped / failed / warnings / subtests） |
| 3 | 没有 .py 函数 / 类被改 | `git diff --stat` 仅显示行数 = docstring 行数；没有 import / def / class 修改 |
| 4 | `bash scripts/check.sh` | All compile checks passed |

### 9.5 回滚策略

- 单独 commit；`git revert` 干净回滚（仅 docstring 还原）

---

## 10. 测试策略

### 10.1 每个**代码** PR（PR-1 / 2 / 3 / 4 / 6）必须

| 层级 | 命令 | gate |
|---|---|---|
| Focused boundary | `pytest tests/test_projection_exclusion_decoupling_boundary.py tests/test_final_decision_aggregator_purification_boundary.py tests/test_confidence_evaluator.py tests/test_confidence_result_wiring_boundary.py tests/test_cutoff_guard.py tests/test_memory_feedback_cutoff_guard_boundary.py tests/test_ai_summary_boundary.py tests/test_promotion_offline_only_boundary.py tests/test_predict_legacy_wrapper_boundary.py tests/test_predict_x2_confidence_wiring_boundary.py tests/test_predict_x3_summary_wiring_boundary.py tests/test_predict_legacy_adapter.py tests/test_predict_x4b_v2_payload_opt_in_boundary.py tests/test_predict_legacy_v2_bridge.py tests/test_app_analysis_context_fixture_hygiene.py -q` | 0 failed / 0 errors |
| Related module | `pytest tests/test_<changed_module>*.py -q` | 0 failed / 0 errors |
| Full pytest | `pytest -q` | passed 数 ≥ baseline + 新增；0 failed |
| `scripts/check.sh` | `bash scripts/check.sh` | All compile checks passed |
| Negative import grep | 自定义 grep 命令断言 import 边界 | 命中条数为期望值 |

### 10.2 每个**文档** PR（PR-5 + 全部 16x docs）

- **不需要** pytest
- 但必须：
  - `git status` clean
  - 仅 intended doc staged
  - `git diff --cached --name-status` 输出仅 `A tasks/record_16x_*.md`

### 10.3 baseline 数字

- Step 15 §3.1 已签收：full pytest **3256 passed, 10 skipped, 0 failed,
  26 warnings, 94 subtests**
- 每个 PR 必须以 Step 15 baseline 为起点；新增测试数明确累加到 passed
- 任何 warnings / subtests 数变化必须**显式说明**

### 10.4 失败响应

- **任一**测试失败 → **立即停止**
- **不**用 `--no-verify` 绕过 hook
- **不** force push
- root-cause 后**重做** PR；**不**补 fix commit

---

## 11. 回滚策略

| 规则 | 说明 |
|---|---|
| **每个 PR 单独 commit** | 不混入 cleanup / .gitignore / STATUS.md / hard rule 修改 |
| **不 amend 已 push commit** | 已 push 的 commit 一律新建 commit 修复；不 force push |
| **失败用 `git revert`** | 不用 `reset --hard` 抹历史 |
| **不混合多个 PR** | PR-1 commit 不带 PR-2 改动 |
| **不同 PR 不共享 unstaged changes** | 切 PR 之前 `git status` 必须 clean |
| **delete 前 archive** | PR-1 ~ PR-6 全部**不**含 `git rm`；任何文件删除留待 17A |
| **rollback 窗口** | 每个 PR 合并到 main 后 ≥ 1 周作为回滚窗口；archive 后 4 周内允许从 archive 恢复 |
| **boundary test 失败立即停止** | 任何 boundary 失败视为 contract 违规，不绕过 |
| **regression 数字必须可比对** | 每个 PR 写明 baseline 与 PR 后的 passed / skipped / failed / warnings / subtests，与 Step 15 §3.1 / 上一份 PR signoff 对比 |

---

## 12. 不允许事项

本轮 + 后续 PR-1 ~ PR-6 严守：

- ❌ 不直接删除 `predict.py`
- ❌ 不直接删除 `services/projection_orchestrator.py`
- ❌ 不直接迁移 UI（属 PR-5 之后的子 PR）
- ❌ 不直接迁移 `run_predict` 默认路径到 V2（hard rule 1）
- ❌ 不跑 final holdout（2026-01-01 之后窗口永久保留）
- ❌ 不输出 trading action / hard / forced / required
- ❌ 不进入 3R-5 / 3R-6（1.0 §12 / 16A §18）
- ❌ 不复活 `continuous_smoothing*` / `archive/legacy/root_stubs/*` / promotion 三模块
- ❌ 不修改 `.gitignore`
- ❌ 不处理 handoff
- ❌ 不处理 logs / DB backup / `.claude/worktrees/`
- ❌ 不写 DB / 不改 DB schema
- ❌ 不借 16E 计划顺手改实现（16E 是 plan，落地从 16F 起）
- ❌ 不在 PR-1 ~ PR-6 任一 PR 内同时做"删 / 重命名 / 移动文件"

---

## 13. 推荐下一步

**首选**：

> **Step 16F / PR-1：`peer_alignment` 抽公共模块**

理由：

- PR-1 是**最小风险**的代码 PR：只新建 1 个文件 + 2 个 import 改动 + 行为
  零变化
- 完成后立即解决 `services/main_projection_layer.py:18` 反向 import 这个
  16B / 16C / 16D 已识别的结构性违规
- 为 PR-2 / 3 / 4 铺路（PR-2 才能干净删 `exclusion_result` 形参；
  PR-4 才能干净构造 standard payload）

**不推荐**：

- 不推荐跳过 PR-1 直接进 PR-4（依赖关系会卡住）
- 不推荐借 16F 做 PR-2 / PR-3 内容（必须**单独** PR）
- 不推荐借任一步解锁 3R-5 / 3R-6（1.0 §12 7 项前提必须全部满足）

---

## 14. 严守边界

本轮 Step 16E **只**写 core chain refactor plan：

- ❌ 未改业务代码（无 `.py` 文件被修改）
- ❌ 未新增测试（`tests/` 字节不变）
- ❌ 未删除文件
- ❌ 未移动文件
- ❌ 未修改 `.gitignore`
- ❌ 未处理 handoff（`.claude/handoffs/task_089_post_pr_cleanup.md` 字节
  不变；与 14L A2 / 14M / 15 §2 一致）
- ❌ 未处理 logs / DB backup / `.claude/worktrees/`
- ❌ 未跑 replay / validation / historical evaluation
- ❌ 未写 DB / 未改 DB schema
- ❌ 未默认迁移 `run_predict` 到 V2
- ❌ 未接 trading
- ❌ 未输出 buy / sell / hold / hard / forced / required
- ❌ 未启用任何 candidate / 未复活 `continuous_smoothing`
- ❌ 未触碰 RISK-1 / RISK-2 / RISK-3 / RISK-7 / RISK-8 / RISK-9 / RISK-10
- ❌ 未进入 3R-5 / 3R-6
- ❌ 未 commit / 未 push（按本轮指令）

唯一新增文件：[tasks/record_16e_core_chain_refactor_plan.md](tasks/record_16e_core_chain_refactor_plan.md)（本文件）。

后续修改路径：任何对 §3 PR 总顺序 / §4 PR-1 / §5 PR-2 / §6 PR-3 /
§7 PR-4 / §8 PR-5 / §9 PR-6 / §10 测试策略 / §11 回滚策略 / §12 禁止
事项 / §13 下一步的调整，都必须**显式更新本文件**；同时检查是否需要
同步更新 1.0 / 16A / 16B / 16C / 16D。
