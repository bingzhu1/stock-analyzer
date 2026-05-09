# 16I记录：Core Chain Rebuild Execution Plan

> 本记录是 **Step 16I：核心链路重建执行计划**。1.0 canonical / 16A
> blueprint / 16B inventory / 16C target dataflow & contract decision /
> 16D isolation & quarantine plan / 16E core chain refactor plan /
> 16F no-patching principle / 16G full module decomposition standup /
> 16H repository clearing decision table 已全部入 main（main 最新 commit
> `cc4e9ca`）。本轮在 16G + 16H 基础上**重新设计**第一批核心链路重建
> 代码 PR；**不**自动沿用 16E PR-1/2/3/4。
>
> 本轮**只**写执行计划：未改业务代码、未新增测试、未删除文件、
> 未移动文件、未修改 `.gitignore`、未处理 handoff、未处理 logs /
> DB backup / `.claude/worktrees/`、**未处理 `avgo_agent.db`**、
> 未跑 replay / validation / historical evaluation、未写 DB / 未改
> DB schema、未默认迁移 `run_predict` 到 V2、未接 trading、未输出
> buy / sell / hold / hard / forced / required、未进入 3R-5 / 3R-6、
> 未启动 peer_alignment PR、未做任何局部 patch、未 commit / 未 push。
>
> 唯一 deliverable：本文件。

---

## 1. Step 16I 目的

把 16G 全仓库拆解 + 16H 清场决策表**翻译为**第一批核心链路重建代码 PR。

**16I 的核心约束**：

> **不能自动沿用 16E PR-1/2/3/4**。
>
> 16E 是在 16B 第一版 inventory 之上写的；现在 16G / 16H 已经更彻底，
> 16I 必须**重新评估**：
>
> - 哪些 16E PR **保留**
> - 哪些 16E PR **重排**
> - 哪些 16E PR **新增前置**
> - 哪些 16E PR **推迟**
> - 哪些 16E PR **删除**
>
> 任何"按 16E 顺序立即开 PR-1"的提议**默认 reject**（与 16F §8 一致）。

**本文件性质**：执行计划（impl plan），不是 design 也不是 impl 本身。
设计在 16C（数据流 + schema）；隔离 / 决策在 16D / 16H；落地从 17A 起。

---

## 2. 当前前置条件

| 项 | 状态 |
|---|---|
| 1.0 canonical principles | ✅ commit `5c209bb` |
| 16A architecture reset blueprint | ✅ commit `9b98ad5` |
| 16B module standup ownership inventory | ✅ commit `bdd1314` |
| 16C target dataflow & contract decision | ✅ commit `b05d7c8` |
| 16D isolation / quarantine plan | ✅ commit `694450e` |
| 16E core chain refactor plan | ✅ commit `932d243` |
| 16F architecture reset no-patching principle | ✅ commit `6cfaa9b` |
| 16G full module decomposition standup | ✅ commit `ba6bc7d` |
| 16H repository clearing decision table | ✅ commit `cc4e9ca` |
| Step 12–15 boundary fixes / regression / cleanup / signoff | ✅ 全部入 main |
| main 最新 commit | `cc4e9ca` |
| worktree 唯一 deliberate untracked | `.claude/handoffs/task_089_post_pr_cleanup.md` |
| 战略阶段 | 从清场决策（16H）→ 重建 PR 计划（16I 本轮） |
| 3R-5 / 3R-6 | ❌ 仍然不允许进入 |
| 第一个代码 PR | ❌ 必须等 16I 出新 PR 顺序后才能起步 |
| `avgo_agent.db` | local-only ignored（16H §5 校正完成；本轮**不**处理） |
| 16H DELETE_NOW 集合 | **空** |
| Bridge 退出条件 | 0/6 完全满足 |
| 16G UNKNOWN 数 | 10 |

**当前代码 baseline**（本轮 readonly check 确认）：

- `services/exclusion_layer.py:64` 仍含 `def build_peer_alignment(...)`
- `services/main_projection_layer.py:18` 仍 `from services.exclusion_layer import build_peer_alignment`
- `services/confidence_evaluator.py:163-172` 仍读 `most_likely_state` /
  `ranked_states` / `most_unlikely_state` / `ranked_unlikely_states`
  （main_projection / exclusion 实际未输出这些 key）
- 上一轮 PR-1 work 已在 16F §5 后完整 discard；worktree 干净

---

## 3. 16E PR 列表复审

逐项判断：

| 16E PR | 16E 内容 | 16I 决策 | 理由 |
|---|---|---|---|
| **PR-1** | peer_alignment 抽公共模块 | **保留**（重命名 PR-C；**重排**到 PR-B 之后） | 方向正确（16C §3.3 / §7.5 决定的反向 import 修复）；但必须先有 standard payload skeleton（PR-B），否则 peer_alignment 的"输出形状"无法被未来 architecture_orchestrator 引用 |
| **PR-2** | main_projection 去 exclusion_result 形参 | **保留**（重命名 PR-D） | 16C §3.3 / 16D §6.2 已锁；byte-equivalent；依赖 PR-C（peer_alignment 已经迁出，main_projection 已经可以独立编译） |
| **PR-3** | confidence key 对齐 | **保留**（重命名 PR-E）；**逻辑收紧**：必须读 standard schema 优先 + interim schema 兼容（exclude_big_up→大涨 / exclude_big_down→大跌）+ 显式 `calibration_context={"ready": False}` | 16E PR-3 定义已对；16I 把"standard schema 优先"显式落到 PR-E 的 acceptance criteria，而不是模糊"key 对齐" |
| **PR-4** | architecture_orchestrator MVP | **保留**（重命名 PR-F）；**重排**到 B/C/D/E 之后 | 16C §4 已决定它是未来唯一主入口；MVP 形式存在；不接 UI / replay；必须等 standard payload skeleton + 三系统 schema 对齐之后 |
| **PR-5** | UI / evaluation payload migration plan | **保留**（重命名 PR-H）；plan-only，不改 UI 代码 | 16C §8 / §9 已锁；本身是文档 PR；依赖 PR-F 上线 |
| **PR-6** | Bridge deprecation markers | **保留**（重命名 PR-G）；只加 docstring，不改逻辑 | 16D §5 / §6 已锁；docstring-only PR；依赖 PR-F（marker 内容引用 future architecture_orchestrator） |
| — | （新增） | **PR-A**：Remaining UNKNOWN Deep Audit（**可选 / 可推迟**） | 16G 留 10 项 UNKNOWN；本轮 §5 判断**不阻塞**第一批核心链路 PR；可作为并行 / 可选 prep |
| — | （新增） | **PR-B**：standard_projection_payload.v1 contract skeleton（**新增前置**） | 16C §5 已决定 schema；但 16E 没有把 schema skeleton 单独立项；16I 显式把它提到 PR-C 之前作为"新架构地基"。详见 §6 |
| — | 之前隐含的 17A | **保留**为"PR-B/C/D/E/F/G/H 实施完毕后才进入" | — |

**总结**：

- **保留** 6 项（16E 全部 PR）→ 重命名为 PR-C/D/E/F/G/H
- **重排** 1 项（16E PR-1 不再是首位；PR-B skeleton 先行）
- **新增前置** 2 项（PR-A 可选 + PR-B 必需地基）
- **推迟** 0 项
- **删除** 0 项
- **逻辑收紧** 1 项（PR-E 显式落 standard schema 优先）

---

## 4. 16I 重新排序后的第一批 PR 总览

> **顺序硬约束**：每个 PR **单独 commit、单独 revert、单独 regression**；
> 不混合；不顺手做未授权改动。

| 序号 | 名称 | 性质 | 依赖 | 风险 | 16E 对应 |
|---|---|---|---|---|---|
| **PR-A**（可选 / 可推迟） | Remaining UNKNOWN Deep Audit / Final Classification | 文档 | — | L | （新增） |
| **PR-B** | `standard_projection_payload.v1` contract skeleton | 代码（新增 schema + validator + tests） | — | L | （新增前置） |
| **PR-C** | `peer_alignment` 抽公共模块 | 代码（新增 + import 调整） | PR-B | L | 16E PR-1 |
| **PR-D** | `main_projection` 去 `exclusion_result` 形参 | 代码（删形参 + caller 调整） | PR-C | L | 16E PR-2 |
| **PR-E** | confidence key 对齐 + 显式 calibration_context | 代码（schema adapter） | PR-D | M | 16E PR-3（逻辑收紧） |
| **PR-F** | `architecture_orchestrator` MVP | 代码（新建模块） | PR-B/C/D/E | M | 16E PR-4 |
| **PR-G** | Bridge deprecation markers | 代码（**仅 docstring**） | PR-F | L | 16E PR-6 |
| **PR-H** | UI / evaluation payload migration plan | 文档 | PR-F | L | 16E PR-5 |

**判断要点**：

- PR-A 是**可选**（§5）：10 项 UNKNOWN 不阻塞 PR-B/C/D/E/F；可与主链
  并行或推迟到 17A 之后
- PR-B 是**新架构地基**（§6）：所有后续 PR 都需要 reference 标准 schema
- PR-C 是 16F §5 重新评估后的"第一个代码 PR"候选；16I 决定把 PR-B 排在
  它之前
- PR-D / PR-E / PR-F 形成一条直线依赖
- PR-G / PR-H 在 PR-F 之后，可并行

---

## 5. 是否需要先做 UNKNOWN Deep Audit

> **判断：PR-A 不必排第一；可推迟，也可作为 16J 起的并行 prep**。

| UNKNOWN 模块 | 是否阻塞 PR-B/C/D/E/F | 理由 |
|---|---|---|
| `services/active_rule_pool.py` | ❌ 不阻塞 | 与 promotion 共享命名空间；归位 B5/B7/B8 不影响主链 schema |
| `services/active_rule_pool_calibration.py` | ❌ 不阻塞 | confidence calibration 数据准备；PR-E 阶段 calibration_context 用 `{"ready": False}` 即可 |
| `services/active_rule_pool_drift.py` | ❌ 不阻塞 | 同上 |
| `services/active_rule_pool_export.py` | ❌ 不阻塞 | export 是 B7/B8 输出层 |
| `services/active_rule_pool_validation.py` | ❌ 不阻塞 | B8 validation 工具 |
| `services/projection_output_adapter.py` | ❌ 不阻塞 | docstring "not yet wired"；16H 已决定 DEEP_AUDIT_REQUIRED；不进 PR-B/C/D/E/F 任一调用链 |
| `services/primary_bias_diagnosis.py` | ❌ 不阻塞 | 诊断模块；不进主链路 |
| `services/inspect_analysis.py` | ❌ 不阻塞 | UI tool；不进主链路 |
| `services/five_state_margin_policy.py` | ❌ 不阻塞 | B3 内部候选；可在 PR-F architecture_orchestrator 之后再决定是否并入 |
| `research.py`（root） | ❌ 不阻塞 | root research entry；不进主链路 |

**结论**：

- 10 项 UNKNOWN **不阻塞** PR-B/C/D/E/F 的实施
- PR-A 可作为 **可选 / 并行** 文档轮（16J 候选）
- 推荐顺序：先做 PR-B；PR-A 在 PR-B 之后或并行启动；PR-A 输出会反哺
  16I §10 PR-F 设计中"是否合并某些 LEGACY chain step 到 architecture_orchestrator"
- **不**作为首位 PR；强制要求 PR-A 排第一会延误核心链路

---

## 6. standard_projection_payload.v1 是否应先落 contract skeleton

> **判断：是。PR-B 必须排在第一位代码 PR 的位置**。

### 6.1 为什么需要 PR-B 先行

1. **16C §5 已决定** `standard_projection_payload.v1` 是未来唯一标准
   payload；但**没有任何代码**实现这一 schema。如果不先落 skeleton：
   - PR-C peer_alignment 抽出后无法被 schema 引用；后续 PR-F 又要重新
     回写 schema reference
   - PR-E confidence key 对齐时缺少标准 schema 描述，"standard schema
     优先"无文档可参照
   - PR-F architecture_orchestrator MVP 必须现场定义 schema → 又是
     一次大改（违反 16F 单 PR 单职责）
2. **新架构地基**，不是小修小补：
   - 不是修一行 / 改一个 import / 删一个形参
   - 是给整个 §3 数据流的"输出 shape"建立 single source of truth
   - 服务于 1.0 §6.7（"final report 不重新预测"）+ 16C §5 决定
3. **风险极低**：
   - 仅新增 1 个 schema/validator 模块 + 1 个 test
   - 不改任何现有业务代码
   - 不引入任何新依赖

### 6.2 PR-B 的最小 deliverable

**新增**：

- `services/standard_projection_payload.py`（**新文件**）：
  - `SCHEMA_VERSION = "standard_projection_payload.v1"` 常量
  - `STANDARD_PAYLOAD_SECTIONS` 元组：9 个顶层 key
    （`schema_version` / `metadata` / `feature_payload` /
    `projection_result` / `exclusion_result` / `confidence_result` /
    `final_report` / `review_stub` / `evaluation_stub` /
    `compatibility_metadata`，与 16C §5.2 一致）
  - `validate_standard_projection_payload(payload: dict) -> list[str]`
    纯函数 validator（参考 `services/projection_output_contract.py` 体例）：
    - 不抛异常；返回 error 列表
    - 不读外部资源
    - 不引入 LLM / DB / 网络
  - 各字段最小 shape 检查（类型 + 必填）；**不**检查内部业务字段
    （那是 PR-F 之后的事）
  - 模块顶部 docstring 显式声明：
    - 与 16C §5 / 1.0 §8 / 07A–07D 草案对齐
    - 内部各 section schema_version：
      `projection_system_result.v1` / `exclusion_system_result.v1` /
      `confidence_system_result.v1` / `final_report_aggregator_result.v1`
    - **不**包含 trading / hard / forced / required / `simulated_trade` /
      legacy `PredictResult` 字段（由 validator 显式 reject）

**新增 tests**：

- `tests/test_standard_projection_payload_contract.py`：
  - 9 顶层字段全部出现时 `validate_*` 返回 `[]`
  - 缺字段 / 错类型 / 包含禁字段时返回明确 error
  - schema_version 字符串完全匹配 `standard_projection_payload.v1`
  - 负面：legacy `PredictResult` 字段（`final_bias` / `final_confidence` /
    `primary_projection` / `final_projection` 等）出现在顶层时 reject
  - 负面：`simulated_trade` / `trading_action` / `buy` / `sell` / `hold` /
    `hard_exclusion` / `forced_exclusion` / `required_decision` 出现时 reject

**不做的事**：

- ❌ 不动 `services/projection_output_contract.py`（外部 8 段 validator 保留）
- ❌ 不接入 architecture_orchestrator（那是 PR-F）
- ❌ 不让任何 active path import 这个 validator（PR-F 之后才接入）
- ❌ 不替换 main_projection / exclusion / confidence_evaluator 现有输出 schema

### 6.3 PR-B 验收

| # | 指标 | 期望 |
|---|---|---|
| 1 | `services/standard_projection_payload.py` 不 import 任何业务模块 | 仅 `from __future__ import annotations` + `from typing import ...` |
| 2 | validator 是纯函数；不抛异常；不修改输入 | tests 覆盖 |
| 3 | 9 顶层字段、各 schema_version 字符串、禁字段集合**与 16C §5 / §6 一致** | manual review + tests |
| 4 | 全 pytest 通过 | 数字 ≥ Step 15 baseline 3256 + PR-B 新增 |
| 5 | `bash scripts/check.sh` 通过 | All compile checks passed |

---

## 7. PR-C peer_alignment 重新定位

### 7.1 为什么 PR-C 不是小修小补

- **它属于 Branch 2 Feature Layer**（1.0 §8 / 16A §6 / 16C §3 / 16D §4.2 / 16G §6.2）
- **它服务于 §3 数据流核心约束**："Projection 与 Exclusion 并行读
  Feature Payload；二者互不读"
- **它消除一个跨层反向依赖**：当前 `services/main_projection_layer.py:18`
  反向 import `services/exclusion_layer.build_peer_alignment` —— 这是
  16B §5.5 / 16C §3.3 / 16G §6.3 / 16H §11.2 全部识别的结构性违规
- **它不是"发现一个 import 问题就 patch"**：peer_alignment 抽出是 1.0 /
  16A 既定的核心架构动作，不是局部 patch。本轮在 16I 中再次确认
  其架构性（与 16F §8 一致 — 16E PR 列表保留方向）

### 7.2 PR-C 范围（与 16E §4 / 16D §10 一致；本轮重新确认）

**新增**：`services/peer_alignment.py`
（含 `build_peer_alignment` + 私有 helpers `_as_dict` / `_safe_float` /
`_pick_float` / `_normalize_features` 的独立副本；不引入 projection /
exclusion / confidence / final_decision 依赖）

**修改**：

- `services/exclusion_layer.py`：删本地 `def build_peer_alignment`，加
  `from services.peer_alignment import build_peer_alignment`
- `services/main_projection_layer.py`：把 import 来源从 `services.exclusion_layer`
  改为 `services.peer_alignment`

**新增 tests**：`tests/test_peer_alignment_boundary.py`
（5 case byte-equivalent + import boundary 负面测试 + 信号验证）

### 7.3 PR-C 不允许的事

- ❌ 不改 `build_peer_alignment` 内部逻辑
- ❌ 不改 main_projection / exclusion 输出 schema（schema 对齐 07A/07B 是后续 PR）
- ❌ 不顺带改 main_projection / exclusion 业务逻辑（即使发现 bug 也不改；记录到 16I-2 / 17B 候选）
- ❌ 不动 V2 / home_terminal / projection_orchestrator
- ❌ 不动 UI

### 7.4 PR-C 验收

与 16E §4.4 一致：5 case byte-equivalent / `main_projection_layer` 不再
import `exclusion_layer` / `exclusion_layer` 不再含本地 def / focused +
full pytest + check.sh 全绿。

---

## 8. PR-D main_projection 去 `exclusion_result` 形参

### 8.1 目的

删除 `services/main_projection_layer.py:286 / 367` 两个公共函数
`build_main_projection_layer` / `run_main_projection_layer` 的
`exclusion_result` 形参 + `del exclusion_result` 软边界。
彻底关闭 16B §5.5 / 16C §3.3 / 16G §6.3 / 16H §6 列出的"形参守门"
违规（07A §3.2 禁止 projection 读 exclusion）。

### 8.2 范围

**修改**：

- `services/main_projection_layer.py`：
  - `build_main_projection_layer` 签名删除 `exclusion_result`（[main_projection_layer.py:286](services/main_projection_layer.py:286)）
  - `run_main_projection_layer` 签名删除 `exclusion_result`（[main_projection_layer.py:367](services/main_projection_layer.py:367)）
  - 删除 `del exclusion_result`（[main_projection_layer.py:298](services/main_projection_layer.py:298)）
  - docstring 同步更新（删除"deprecated and ignored"，改为"not part of the API"）
- caller 全清单（PR-D 必须**全量修复**）：
  - `services/home_terminal_orchestrator.py:151-155`（spot-check：当前未传 exclusion_result）
  - `services/projection_orchestrator_v2.py`（spot-check：当前未传）
  - tests grep `build_main_projection_layer` / `run_main_projection_layer`
    全 repo

**修改 tests**：

- `tests/test_projection_exclusion_decoupling_boundary.py` 等：把"接受
  但忽略"的断言改为"不接受（`TypeError` on call）"
- 任何当前显式传 `exclusion_result=...` 的测试 kwarg：删除

### 8.3 07A / 11A 边界关系

- **07A §3.2 / §10**：projection 系统不读 exclusion_result —— 形参删除
  后从 API 层面物理保证
- **11A boundary contract**：当前由 `del exclusion_result` 守护；PR-D
  把守护从"运行期 del"升级为"API 不接受"

### 8.4 PR-D 不允许的事

- ❌ 不改 `build_main_projection_layer` 内部计算逻辑
- ❌ 不改输出 schema
- ❌ 不动 V2 / home_terminal 编排顺序
- ❌ 不动 exclusion_layer

### 8.5 PR-D 验收

与 16E §5.4 一致：signature 不接受 `exclusion_result`；显式传 kwarg →
`TypeError`；输出 byte-equivalent；现有 boundary tests 全绿；full pytest
通过。

### 8.6 PR-D 回滚

单独 commit；`git revert <PR-D commit hash>`；失败立即停止。

---

## 9. PR-E confidence key 对齐 + 显式 calibration_context

### 9.1 目的

让 `services/confidence_evaluator.py` 在生产链路上可以**真正**计算
`agreement_status`（当前因 key 不齐而恒为 `unknown`）。

### 9.2 严格要求

- **standard schema 优先**（07A / 07B / 16C §6 命名）：
  - `proj.most_likely_state` / `proj.ranked_states`
  - `excl.most_unlikely_state` / `excl.ranked_unlikely_states`
- **interim schema 兼容**（main_projection / exclusion 当前实际输出）：
  - 若 standard key 缺，回退读 `proj.predicted_top1.state` /
    `[proj.predicted_top1.state, proj.predicted_top2.state]`
  - 若 standard key 缺，按显式映射（**不是 LLM**）回退：
    - `excl.triggered_rule == "exclude_big_up"` → `most_unlikely_state = "大涨"`
    - `excl.triggered_rule == "exclude_big_down"` → `most_unlikely_state = "大跌"`
    - 其它 → `most_unlikely_state = None`
  - 此映射用 `services/projection_chain_contract.excluded_state_from_result`
    现有逻辑（已存在；不重复实现）
- **calibration_context 显式 `{"ready": False}`**：
  - `services/home_terminal_orchestrator.py:169-174` 调用 `build_confidence_result`
    时追加 `calibration_context={"ready": False}`
  - `services/projection_orchestrator_v2.py:585-590` 同上追加
  - **不允许 silent default**；必须 explicit fallback
- **不改写 projection / exclusion**：
  - `_FORBIDDEN_FIELDS` / `non_mutation_confirmations` 不变
  - 07C §5 / §6 / §7 boundary 不变

### 9.3 测试要求

- `tests/test_confidence_evaluator_schema_compat.py`（**新增**）：
  - standard schema → agreement 4 case 全部命中
  - interim schema → agreement 4 case 全部命中（含 exclude_big_up / down 映射）
  - 混合 schema → standard 优先
  - 完全缺字段 → `agreement = unknown`，reasoning 含明确"key missing"
- 现有 `tests/test_confidence_evaluator.py` / `test_confidence_result_wiring_boundary.py`：
  - 增加 explicit `calibration_context={"ready": False}` reasoning 断言
  - 验证 `unknown` 不再因 key mismatch 频发；calibration 未接入仍 unknown，
    但 reasoning 含"calibration not wired"而非"key mismatch"

### 9.4 PR-E 不允许的事

- ❌ 不改 `_FORBIDDEN_FIELDS`
- ❌ 不引入 calibration table（calibration 接入是后续独立 PR）
- ❌ 不改 `combined_confidence` 算法
- ❌ 不动 `final_decision.py` / main_projection / exclusion 的输出 schema
- ❌ 不读 future outcome / 2026 holdout

### 9.5 PR-E 验收

与 16E §6.4 一致：4 schema case 全部命中 + reasoning 明确 + 现有 11C / 12C
boundary 全绿 + full pytest 通过。

---

## 10. PR-F architecture_orchestrator MVP

### 10.1 目的

落地 **未来唯一主入口** `services/architecture_orchestrator.py`（16C §4 决定）的 MVP。

### 10.2 范围

**新增**：`services/architecture_orchestrator.py`
- public API：`build_standard_projection_payload(*, symbol, target_date_str, coded_df, target_row, target_ctx, peer_loader=None) -> dict`
- 内部步骤（16C §3 数据流）：
  1. `feature_payload` 构造（调 `services.projection_chain_contract.build_feature_payload_from_recent_window`，含 `peer_alignment`）
  2. **并行**：`projection_result` （调 `services.main_projection_layer.build_main_projection_layer`）+ `exclusion_result`（调 `services.exclusion_layer.run_exclusion_layer`）
  3. `confidence_result`（调 `services.confidence_evaluator.build_confidence_result(..., calibration_context={"ready": False})`）
  4. `final_report`（调 `services.final_decision.build_final_decision(...)`，最小翻译）
  5. 组装 `standard_projection_payload.v1`（依据 PR-B 的 `STANDARD_PAYLOAD_SECTIONS`）
  6. **PR-B validator 自检**：在返回前调 `validate_standard_projection_payload(payload)`，断言为 `[]`

**新增 tests**：`tests/test_architecture_orchestrator_mvp.py`
- schema-validated 输出
- 顶层 9 字段全部存在
- `metadata.non_mutation_confirmations` 全 `False`
- `metadata.data_window_days = 20`（标 `legacy_window`，待 16C 15d 迁移）
- 负面 import 测试：**不**import `predict` / `projection_orchestrator` /
  `projection_orchestrator_v2` / `predict_legacy_adapter` /
  `predict_legacy_v2_bridge`
- 输出**不**含 legacy `PredictResult` 字段
- 输出**不**含 trading / hard / forced / required / `simulated_trade`

### 10.3 必须等 PR-B/C/D/E 完成的理由

| 依赖 | 原因 |
|---|---|
| PR-B | 需要 `STANDARD_PAYLOAD_SECTIONS` + `validate_standard_projection_payload` 自检 |
| PR-C | 需要 `services/peer_alignment.py` 作为 Branch 2 资产；否则 architecture_orchestrator 必须从 exclusion_layer 反向 import |
| PR-D | 需要 `build_main_projection_layer` 的最终 signature（无 `exclusion_result`） |
| PR-E | 需要 confidence_evaluator 在 standard / interim 双 schema 下都能算 agreement |

### 10.4 PR-F 不允许的事（与 16E §7.3 一致）

- ❌ 不改 `predict.py` / `ui/predict_tab.py` / `services/contract_replay_writer.py` /
  `home_terminal_orchestrator.py` 内部实现 / V2 orchestrator
- ❌ 不接 calibration table
- ❌ 不产生 legacy PredictResult
- ❌ 不输出 trading / hard / forced / required / `simulated_trade`
- ❌ 不写 DB / 不改 schema
- ❌ 不切 15d 窗口
- ❌ 不合并 `consistency_layer`（保留为 LEGACY_ACTIVE_DEPENDENCY；后续独立 PR）

### 10.5 PR-F 验收

与 16E §7.4 一致 + PR-B validator 自检通过 + 负面 import / 字段 tests 全绿。

---

## 11. PR-G Bridge deprecation markers

### 11.1 目的

给 13 个 Bridge / LEGACY_ACTIVE_DEPENDENCY 模块加 **clearly marked
deprecation / migration bridge docstring**（16D §10 / 16E §9 已锁）。

### 11.2 范围（修改 13 个文件**顶部 docstring** + 可选 `_BRIDGE_KIND` 常量）

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

每条 docstring 必须含：

- Status label（`TEMP_MIGRATION_BRIDGE` / `LEGACY_ACTIVE_DEPENDENCY`）
- Reason（引用 1.0 / 16C / 16D / 16H 决策）
- Exit condition（来自 16C §11 / 16H §6 / §7 的具体 Phase）
- Future action（archive / merge / refactor）
- Cross-reference（链接到 `tasks/record_16h_*.md` 对应章节）

### 11.3 不允许的事

- ❌ 不改任何函数 / 类签名
- ❌ 不改任何 import
- ❌ 不改任何业务逻辑
- ❌ 不删除任何代码
- ❌ 不引入新模块
- ❌ 不改 tests

### 11.4 PR-G 验收

与 16E §9.4 一致：13 文件 docstring 全部含 marker + 业务行为完全不变
（full pytest 数字与 PR-G 前完全一致）+ `git diff --stat` 仅 docstring 行数。

---

## 12. PR-H UI / evaluation payload migration plan

### 12.1 目的（与 16E §8 / 16C §8 / §9 一致）

**只写计划文档** `tasks/record_17a_pr_h_ui_evaluation_migration_plan.md`：

- UI 字段映射表：`final_bias` → `final_report.projection_section.most_likely_state` 等
- UI tab 迁移顺序：低风险 tab（history / inspect）先 → 中风险（home / review）→ 主入口（predict_tab，Bridge #1）
- evaluation 迁移顺序：离线 dashboard 先 → replay 写入（Bridge #2）→ e2e
- 每个 UI / evaluation 子 PR 独立 commit；可 git revert
- 依赖：所有 UI / evaluation 子 PR 都依赖 PR-F MVP 已合

### 12.2 不做的事

- ❌ 不改任何 UI 代码
- ❌ 不迁移 evaluation
- ❌ 不动 replay

### 12.3 验收

仅 1 个 doc 文件 untracked → staged → committed；无代码改动；不需要 pytest。

---

## 13. 每个 PR 的测试策略

### 13.1 每个**代码** PR（PR-B / C / D / E / F / G）必须

| 层级 | 命令 | gate |
|---|---|---|
| Focused boundary | `python3 -m pytest tests/test_*_boundary.py -q`（14–15 file，13 §3.2 / 15 §3.3） | 0 failed / 0 errors |
| Related module | `python3 -m pytest tests/test_<changed_module>*.py -q` | 0 failed / 0 errors |
| Full pytest | `python3 -m pytest -q` | passed 数 ≥ baseline + 新增；0 failed |
| `scripts/check.sh` | `bash scripts/check.sh` | All compile checks passed |
| Negative import grep | grep 命令断言 import 边界 | 命中条数为期望值 |

### 13.2 每个**文档** PR（PR-A / PR-H + 后续 16J+ docs）

- **不需要** pytest
- `git status` clean，仅 intended doc staged
- `git diff --cached --name-status` 输出仅 `A tasks/record_*.md`

### 13.3 baseline

- Step 15 §3.1 已签收：full pytest **3256 passed, 10 skipped, 0 failed,
  26 warnings, 94 subtests**
- 每个 PR 必须以 Step 15 baseline 为起点；新增测试数明确累加到 passed
- warnings / subtests 数变化必须**显式说明**

### 13.4 失败响应

- **任一**测试失败 → **立即停止**
- **不**用 `--no-verify` 绕过 hook
- **不** force push
- root-cause 后**重做** PR；**不**补 fix commit

---

## 14. 每个 PR 的回滚策略

| 规则 | 说明 |
|---|---|
| 单独 commit | 不混入 cleanup / .gitignore / STATUS.md / hard rule 修改 |
| 不 amend 已 push commit | 一律新建 commit 修复；不 force push |
| 失败用 `git revert` | 不用 `reset --hard` 抹历史 |
| 不混合多个 PR | PR-B 不带 PR-C 改动 |
| 不共享 unstaged changes | 切 PR 之前 `git status` 必须 clean |
| 不 delete active dependency | PR-B/C/D/E/F/G 全部**不**含 `git rm` |
| archive / delete 另开独立 pass | 17A 之后或更晚 |
| rollback 窗口 | 每个 PR 合并到 main 后 ≥ 1 周；archive 后 4 周 |
| boundary test 失败立即停止 | 任何 boundary 失败视为 contract 违规，不绕过 |
| regression 数字必须可比对 | 每个 PR 写明 baseline / PR 后的 passed / skipped / failed / warnings / subtests |

---

## 15. 不允许事项

本轮 + PR-A ~ PR-H 全部严守：

- ❌ 不直接删除 `predict.py`
- ❌ 不直接删除 `services/projection_orchestrator.py`
- ❌ 不直接迁移 UI（属 PR-H 之后的子 PR）
- ❌ 不直接迁移 `run_predict` 默认路径到 V2（hard rule 1）
- ❌ 不直接跑 final holdout（2026-01-01 之后窗口永久保留）
- ❌ 不输出 trading action / hard / forced / required
- ❌ 不进入 3R-5 / 3R-6（1.0 §12 / 16A §18 / 16C §13 / 16F §9 / 16G §16 / 16H §15 锁定）
- ❌ 不复活 `continuous_smoothing*` / `archive/legacy/root_stubs/*` / promotion 三模块
- ❌ 不修改 `.gitignore`
- ❌ 不处理 `avgo_agent.db`（16H §5 校正后无需处理）
- ❌ 不处理 handoff
- ❌ 不处理 logs / DB backup / `.claude/worktrees/`
- ❌ 不写 DB / 不改 DB schema
- ❌ 不借 16I 计划顺手改实现（16I 是 plan，落地从 17A 起）
- ❌ 不在 PR-B ~ PR-H 任一 PR 内同时做"删 / 重命名 / 移动文件"

---

## 16. 推荐下一步

> **首选**：**Step 17A / PR-B：`standard_projection_payload.v1` contract skeleton**

理由：

- 16I 已锁 PR 顺序：PR-B 是新架构地基（§6）
- PR-B 是**最小风险代码 PR**：仅新增 1 个 schema/validator + 1 个 test；
  不动任何业务逻辑；零回归
- 完成后立即解锁 PR-C/D/E/F 的"标准 schema 引用"
- 与 16F §8 一致：16E PR 列表方向正确，但执行节奏由 16I 重排
- PR-A（UNKNOWN deep audit）**可推迟**或并行（§5）；不阻塞主链

**次选**（与首选可并行）：

> **Step 16J / PR-A：Remaining UNKNOWN Deep Audit / Final Classification**

仅当用户希望先关闭 10 项 UNKNOWN，再开始第一批代码 PR；适合在主链
PR 进行期间作为并行 prep。

**不推荐**：

- 不推荐借 16I 做代码改动
- 不推荐跳过 PR-B 直接进 PR-C / D / E / F（依赖关系会卡住）
- 不推荐借任一步解锁 3R-5 / 3R-6（1.0 §12 7 项前提仍未全部满足）

> **明确：本轮 16I 推荐的下一步只有一个 — PR-B**。

---

## 17. 严守边界

本轮 Step 16I **只**写 core chain rebuild execution plan：

- ❌ 未改业务代码（无 `.py` 文件被修改）
- ❌ 未新增测试（`tests/` 字节不变）
- ❌ 未删除文件
- ❌ 未移动文件
- ❌ 未修改 `.gitignore`
- ❌ 未处理 `avgo_agent.db`（16H §5 校正后无需处理）
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
- ❌ 未启动 peer_alignment PR / 未做任何局部 patch
- ❌ 未 commit / 未 push（按本轮指令）

唯一新增文件：[tasks/record_16i_core_chain_rebuild_execution_plan.md](tasks/record_16i_core_chain_rebuild_execution_plan.md)（本文件）。

后续修改路径：任何对 §3 16E PR 复审 / §4 新 PR 总览 / §5 UNKNOWN deep
audit 必要性 / §6 PR-B contract skeleton / §7 PR-C / §8 PR-D / §9 PR-E /
§10 PR-F / §11 PR-G / §12 PR-H / §13 测试策略 / §14 回滚策略 / §15
禁止事项 / §16 下一步 的调整，都必须**显式更新本文件**；同时检查是否
需要同步更新 1.0 / 16A / 16B / 16C / 16D / 16E / 16F / 16G / 16H。
