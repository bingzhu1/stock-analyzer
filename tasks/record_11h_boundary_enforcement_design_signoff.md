# 11H记录：Boundary Enforcement Design Sign-off

> 本记录是 Step 11A–11G 七份 boundary enforcement design 的**总签收文档**。
>
> 本轮**只做签收**：未改代码、未新增设计、未新增测试、未删文件、未移动文件、
> 未写 DB、未跑 replay / validation、未 commit / push、未启动 Step 12、未进入
> 3R-5 / 3R-6、未新增 candidate、未复活 continuous_smoothing。

---

## 1. Sign-off 目的

Step 11A–11G 七份边界修复设计已**全部 commit 入 main**。本记录：

- **不**新增设计
- **不**改代码
- **不**修改 11A–11G 任一份设计
- **不**启动 Step 12 implementation

只做总签收，固定 Step 12 implementation 的：

- **顺序**（哪份先做，哪份后做）
- **依赖**（哪份必须先于哪份）
- **commit 粒度**（commit-per-fix）
- **每个 fix 的最低完成标准**
- **禁止混合事项**
- **Step 12 不应处理的对象**
- **Step 13 回归要求 / Step 14 前置条件**
- **3R-5 / 3R-6 进入条件**

签收后允许的下一步是：**启动 Step 12-A**（按 §4 / §13 启动条件）。

---

## 2. 已完成设计清单

| step | risk | design doc | status | purpose |
|---|---|---|---|---|
| 11A | RISK-1 + RISK-6 | [tasks/record_11a_projection_exclusion_decoupling_design.md](tasks/record_11a_projection_exclusion_decoupling_design.md) | ✅ in main (`cdc0f6c`) | projection / exclusion decoupling：让 main_projection_layer 不接 exclusion_result；同步处理 V2 与 home_terminal_orchestrator 两条 active path |
| 11B | RISK-2 | [tasks/record_11b_final_decision_aggregator_purification_design.md](tasks/record_11b_final_decision_aggregator_purification_design.md) | ✅ in main (`b5236b8`) | final_decision aggregator purification：禁止翻 direction、禁止重算 confidence、禁止 apply preflight；改为纯 aggregate + source attribution + non_mutation_confirmations |
| 11C | RISK-3 | [tasks/record_11c_confidence_evaluator_separation_design.md](tasks/record_11c_confidence_evaluator_separation_design.md) | ✅ in main (`6f1671d`) | confidence evaluator separation：新增 services/confidence_evaluator.py；阶段 A standalone + 阶段 B 接入 V2/final_decision/renderer |
| 11D | RISK-7 | [tasks/record_11d_memory_feedback_cutoff_guard_design.md](tasks/record_11d_memory_feedback_cutoff_guard_design.md) | ✅ in main (`1bc6449`) | memory feedback cutoff guard：新增 services/cutoff_guard.py；为 memory_feedback / projection_memory_briefing / projection_rule_preflight / pre_prediction_briefing / review_analyzer 加 target_date filter |
| 11E | RISK-8 | [tasks/record_11e_predict_py_split_design.md](tasks/record_11e_predict_py_split_design.md) | ✅ in main (`e32372a`) | predict.py legacy wrapper split：predict.py 退化为 wrapper；多阶段（A/B/C/D/E）；最后做，影响面最大（9+ active importers） |
| 11F | RISK-9 | [tasks/record_11f_ai_summary_source_attribution_design.md](tasks/record_11f_ai_summary_source_attribution_design.md) | ✅ in main (`3a0fe94`) | AI summary source attribution + opt-in gate：默认关闭；强制 source attribution；post-check 禁止词；非 final_report |
| 11G | RISK-10 | [tasks/record_11g_promotion_offline_only_documentation_lock_design.md](tasks/record_11g_promotion_offline_only_documentation_lock_design.md) | ✅ in main (`ea4ab9a`) | promotion offline-only documentation lock：预防性 doc-lock + safety fields + import-guard tests；不改业务逻辑 |

依赖与 risk 来源：[tasks/record_06_three_system_independence_principle.md](tasks/record_06_three_system_independence_principle.md)、[tasks/record_07a_projection_system_contract.md](tasks/record_07a_projection_system_contract.md)、[tasks/record_07b_exclusion_system_contract.md](tasks/record_07b_exclusion_system_contract.md)、[tasks/record_07c_confidence_system_contract.md](tasks/record_07c_confidence_system_contract.md)、[tasks/record_07d_final_report_aggregator_contract.md](tasks/record_07d_final_report_aggregator_contract.md)、[tasks/record_07e_three_system_contract_consistency_review.md](tasks/record_07e_three_system_contract_consistency_review.md)、[tasks/record_08_three_system_architecture_diagnosis.md](tasks/record_08_three_system_architecture_diagnosis.md)、[tasks/record_09_module_inventory_detail.md](tasks/record_09_module_inventory_detail.md)、[tasks/record_10_keep_freeze_quarantine_cleanup_plan.md](tasks/record_10_keep_freeze_quarantine_cleanup_plan.md)。

---

## 3. 总体签收结论

> **READY_FOR_STEP_12_WITH_ORDERED_FIXES**

理由：

- 设计链**完整**：06 → 07A/B/C/D → 07E → 08 → 09 → 10 → 11A → 11B → 11C → 11D → 11E → 11F → 11G 全部入 main。
- 每个**已识别 RISK** 都有对应设计：HIGH（RISK-1/2/6/8/9）+ MEDIUM（RISK-3/7）+ LOW（RISK-10）共 8 项 risk → 7 份设计文档（RISK-1 + RISK-6 共用 11A）。
- 跨设计**无契约冲突**（07E 已 sign-off + 11A–11G 各自 §"与其他 11x 关系" 已对齐）。
- 可以**进入 Step 12**，但必须按 §4 顺序、§6 commit-per-fix、§5 依赖矩阵、§8 禁止混合执行。
- **不**允许一次性大重构。
- **不**允许 cleanup 与 boundary fix 混 commit。
- **不**允许跳过 Step 12 直接做 Step 14。
- **不**允许在 Step 12 / Step 13 完成前进入 3R-5 / 3R-6。

---

## 4. Step 12 推荐实施顺序

> **最终顺序固定如下**。每个步骤独立 commit，按顺序执行。

### 4.1 12A — RISK-1 + RISK-6 projection / exclusion decoupling

- **来源**：11A
- **原因**：active path 最高优先级；projection 不能吃 exclusion；两条 active path（V2 + home_terminal）必须同步解耦
- **commit 建议**：`fix(boundary): RISK-1+6 decouple projection from exclusion`
- **影响文件**：`services/main_projection_layer.py` / `services/projection_orchestrator_v2.py` / `services/home_terminal_orchestrator.py` + 改写 `tests/test_main_projection_layer.py` 旧断言

### 4.2 12B — RISK-2 final_decision aggregator purification

- **来源**：11B
- **原因**：aggregator 不能改写 direction、不能重算 confidence、不能 apply preflight；为 12C-B 铺好 `confidence_result=None` 入参
- **commit 建议**：`fix(boundary): RISK-2 purify final decision aggregator`
- **影响文件**：`services/final_decision.py` + 改写 `tests/test_final_decision.py`

### 4.3 12C-A — RISK-3 standalone confidence_evaluator

- **来源**：11C 阶段 A
- **原因**：先新增独立 confidence engine，**不**接主链，降低风险；为 12C-B 与 12E-C 提供 confidence_result 来源
- **commit 建议**：`feat(boundary): add standalone confidence evaluator`
- **影响文件**：新增 `services/confidence_evaluator.py` + 新增 `tests/test_confidence_evaluator.py`

### 4.4 12D — RISK-7 memory feedback cutoff guard

- **来源**：11D
- **原因**：防 future leakage；可为 11C / online calibration 共用 cutoff helper（可在 12C-B 之前完成，也可独立做）
- **commit 建议**：`fix(boundary): RISK-7 add memory feedback cutoff guard`
- **影响文件**：新增 `services/cutoff_guard.py` + 修 `services/memory_feedback.py` / `projection_memory_briefing.py` / `projection_rule_preflight.py` / `pre_prediction_briefing.py` / `review_analyzer.py` / `projection_orchestrator_preflight.py` / `projection_preflight.py` + 新增 `tests/test_cutoff_guard.py`

### 4.5 12C-B — RISK-3 wire confidence_result

- **来源**：11C 阶段 B
- **原因**：等 12B 和 12C-A 完成后，再把 `confidence_result` 接入 orchestrator / final_decision / renderer；让 final_confidence 显示真实 level
- **commit 建议**：`fix(boundary): wire confidence result into final report path`
- **影响文件**：`services/projection_orchestrator_v2.py` / `services/final_decision.py`（把 `confidence_result=None` 替换为真实传入）/ `services/projection_three_systems_renderer.py`（confidence_evaluator 段改 read-only display）

### 4.6 12F — RISK-9 AI summary gate

- **来源**：11F
- **原因**：LLM summary 需要 opt-in + source attribution + post-check；**不**影响 core projection path
- **commit 建议**：`fix(boundary): RISK-9 gate AI summary with source attribution`
- **影响文件**：`services/ai_summary.py`（5 个 builder 加 gate / source attribution / post-check / 返回 dict + `*_text` 兼容 wrapper）+ 新增 `tests/test_ai_summary_boundary.py`

### 4.7 12G — RISK-10 promotion offline-only lock

- **来源**：11G
- **原因**：预防性 LOW 风险；doc-lock + import/path tests；**不**影响 active path
- **commit 建议**：`fix(boundary): RISK-10 lock promotion modules offline-only`
- **影响文件**：`services/active_rule_pool_promotion.py` / `services/promotion_adoption_gate.py` / `services/promotion_execution_bridge.py`（加 OFFLINE_ONLY docstring + safety fields）+ 新增 `tests/test_promotion_offline_only_boundary.py`

### 4.8 12E — RISK-8 predict.py legacy wrapper split

- **来源**：11E
- **原因**：影响面最大（9+ active importers）；**必须**最后处理；可拆多 commit；不能早于 12A / 12B / 12C-A / 12C-B
- **commit 建议**：`fix(boundary): RISK-8 split predict legacy wrapper boundaries`
- **拆分（推荐 X1–X5）**：
  - `[X1] test(boundary): add predict.py legacy wrapper baseline tests` (RISK-8 step A)
  - `[X2] docs(boundary): mark predict.py as legacy wrapper` (RISK-8 step B)
  - `[X3] fix(boundary): RISK-8 wire final_confidence from confidence_result` (step C，前置 12C-A)
  - `[X4] fix(boundary): RISK-8 wire summary from final_report` (step D，前置 12B)
  - `[X5] fix(boundary): RISK-8 delegate predict.py core to V2 path` (step E，前置 12A + 12B + 12C-B；可拆 X5a/X5b/X5c)
- **影响文件**：`predict.py`（保留 schema；行为委托 V2）+ 新增 `tests/test_predict_legacy_wrapper_boundary.py`
- **说明**：predict.py **不应早于** 12A / 12B / 12C-A / 12C-B；如必须拆，使用 11E 的 X1–X5 小步策略。

### 4.9 顺序总览

```
12A → 12B → 12C-A → 12D → 12C-B → 12F → 12G → 12E (X1→X2→X3→X4→X5)
```

最少 8 个 commit；含 12E 拆分则最多 12 个 commit。

---

## 5. 前置依赖矩阵

| implementation | depends_on | why |
|---|---|---|
| **12A**（RISK-1+6） | — | 起点 |
| **12B**（RISK-2） | — 弱：推荐 12A 先做（让 V2 path clean），但**不强依赖** | 12B 修的是 final_decision 内部逻辑，与 main_projection 解耦正交 |
| **12C-A**（RISK-3 阶段 A） | — | standalone module；不接主链；可独立做 |
| **12D**（RISK-7） | 推荐先于 12C-B（共享 cutoff helper 给 confidence_evaluator） | filter_records_by_cutoff helper 由 11D 提供，11C confidence_evaluator 可直接复用 |
| **12C-B**（RISK-3 阶段 B） | **12B + 12C-A**（强依赖） | 11C §11.2：B 阶段必须在 11B 修复完成 + standalone evaluator 可用之后 |
| **12F**（RISK-9） | — 弱：推荐 12B 后（让 final_report.combined_user_summary 已纯化）+ 12C-A（让 confidence_result schema 可用） | ai_summary 不接主链；可独立做；但其 source_attribution 依赖 V2 字段稳定 |
| **12G**（RISK-10） | — | 独立；最低风险；可放最后 |
| **12E-A**（RISK-8 阶段 A：test baseline） | — | 先写 failing test |
| **12E-B**（RISK-8 阶段 B：legacy 标注） | 12E-A | 仅文档级；不改逻辑 |
| **12E-C**（RISK-8 阶段 C：wire confidence） | **12E-B + 12C-A**（强依赖） | 11E §9：predict.py 改读 confidence_result 必须有 standalone evaluator |
| **12E-D**（RISK-8 阶段 D：wire summary） | **12E-C + 12B**（强依赖） | 11E §9：summary 来自 final_report.combined_user_summary，必须在 11B 纯化后 |
| **12E-E**（RISK-8 阶段 E：delegate V2） | **12E-D + 12A + 12B + 12C-B**（强依赖） | 11E §9：委托 V2 必须在 V2 path 干净（11A）+ aggregator 干净（11B）+ confidence wire 完成（11C-B）之后 |
| **3R-5 / 3R-6** | **Step 12 全部 + Step 13 回归通过 + Step 14 cleanup 通过 + 另开 launch review** | 不允许提前；详见 §12 |

### 5.1 推荐顺序（再次锁定）

`12A → 12B → 12C-A → 12D → 12C-B → 12F → 12G → 12E (X1–X5)`

理由：

- 12A 起点（最高优先级，影响 V2 path 干净度）
- 12B 与 12A 正交，但放第二（让 V2 path 更干净）
- 12C-A standalone（无依赖；为 12C-B/12E-C 铺路）
- 12D 提供 helper（为 12C-B 铺路）
- 12C-B 接入（前置 12B + 12C-A 完成）
- 12F 独立 LLM 改造（不接主链；推荐放主链稳定后）
- 12G 预防性 doc-lock（放最稳后）
- 12E 最后做（影响面最大；必须等 12A/12B/12C-A/12C-B 全部完成）

---

## 6. Commit-per-fix 原则

每个 RISK **必须**单独 commit。

### 6.1 强约束

- **不**允许一个 commit 同时修多个 RISK
- **不**允许把 RISK-1 与 RISK-2 合并到一个 commit
- **不**允许把 RISK-1 与 RISK-6 拆到不同 commit（两者**必须**同一个 commit 同步解耦，11A §10 已规定）
- **不**允许把 11C-A 与 11C-B 合并到一个 commit
- **不**允许把 11E 任意两阶段合并到一个 commit（除非 11E-A 内部 test setup 已合并，阶段 B/C/D/E 必须独立）

### 6.2 fix commit 不允许混入

- 删除 dead code（属 Step 14 cleanup）
- 删除 untracked 文件（属 Step 14）
- 处理 logs/regime_validation/（不在任何 Step 范畴内本轮处理）
- 处理 DB backup（不在本轮范畴）
- 改 DB schema（不在本轮范畴）
- 修改 raw output（不在本轮范畴）
- 处理 .claude/worktrees/（不在本轮范畴）
- 处理 stash（不在本轮范畴）

### 6.3 推荐 commit 粒度

```
[12A]   1 commit
[12B]   1 commit
[12C-A] 1 commit
[12D]   1 commit
[12C-B] 1 commit
[12F]   1 commit
[12G]   1 commit
[12E]   建议拆 5 个 commit（X1/X2/X3/X4/X5），X5 可再拆 X5a/X5b/X5c
```

最少 8 个 commit；含 12E 拆分则最多 12 个 commit。

### 6.4 每个 commit 必须

- 通过 focused test：`pytest tests/<对应测试文件>`
- 通过全量 pytest：`pytest tests/`
- commit message 遵循约定格式
- 附上 contract enforcement test（11A–11G 各设计的 §"contract enforcement tests" 章）

### 6.5 不允许

- ❌ `git commit --amend` 已 push 的 fix commit
- ❌ `git rebase -i` 重写已 push 的 fix commit
- ❌ 在 fix commit 内"借机"做小 cleanup
- ❌ 一个 commit 修多 RISK + 多个无关文件

---

## 7. Step 12 每个 fix 的最低完成标准

### 7.1 12A（RISK-1 + RISK-6）

- ✅ projection scores **不**因 `exclusion_result` 改变（同样 features 输入下，`state_probabilities` 完全相等）
- ✅ `services/projection_orchestrator_v2.py` **不**传 `exclusion_result=` 给 `build_main_projection_layer`
- ✅ `services/home_terminal_orchestrator.py` **不**传 `exclusion_result=` 给 `build_main_projection_layer`
- ✅ `services/main_projection_layer.py` 的 `_apply_exclusion()` 调用被删除
- ✅ peer_alignment fallback **不**从 `exclusion_result.peer_alignment` 取
- ✅ contract enforcement tests pass（11A §8 列出的 7 项）
- ✅ 改写后的旧 `tests/test_main_projection_layer.py` 通过
- ✅ 全量 pytest 全绿

### 7.2 12B（RISK-2）

- ✅ `final_direction` **不**被 override（== `primary_direction`）
- ✅ confidence **不**在 final_decision 内重算（== `confidence_result.combined_confidence.level` 或 `"unknown"`）
- ✅ preflight 是 **display-only**（`preflight_influence.applied_effects == []` 永远）
- ✅ 输出含 `non_mutation_confirmations`（6 个 false 字段）
- ✅ 输出含 `source_attribution`
- ✅ 输出**不**含禁止字段（trading / hard / forced / required / production_promotion / `_PROTECTION_LAYER_CONNECTED`）
- ✅ contract enforcement tests pass（11B §9 列出的 9 项）
- ✅ 全量 pytest 全绿

### 7.3 12C-A（RISK-3 阶段 A）

- ✅ `services/confidence_evaluator.py` 存在并 export `build_confidence_result(...)`
- ✅ schema 严格符合 07C §9 草案 / 11C §6
- ✅ **不** mutate `projection_result` / `exclusion_result`（deepcopy 对比通过）
- ✅ **不**读 future outcome（target_date cutoff guard 生效）
- ✅ **不**调 LLM（无 `from services.openai_client import` 引用）
- ✅ **不**写 DB（仅 SELECT，如需）
- ✅ 缺 `calibration_context` 时降级为 `unknown`，**不**fallback heuristic
- ✅ contract enforcement tests pass（11C §12.1 列出的 14 项）
- ✅ 全量 pytest 全绿

### 7.4 12D（RISK-7）

- ✅ `services/cutoff_guard.py` 存在并 export `filter_records_by_cutoff(...)`
- ✅ future records（date > target_date）被 SKIP
- ✅ missing audit_date 被 SKIP
- ✅ unparseable date 被 SKIP
- ✅ **不**fallback 到全量 records
- ✅ memory_feedback / projection_memory_briefing / projection_rule_preflight / pre_prediction_briefing / review_analyzer 输出含 `cutoff_guard` 段
- ✅ contract enforcement tests pass（11D §11 列出的 16 项）
- ✅ 全量 pytest 全绿

### 7.5 12C-B（RISK-3 阶段 B）

- ✅ `services/projection_orchestrator_v2.py` 顶层输出含 `confidence_result` 字段
- ✅ `services/final_decision.py` 接受真实传入的 `confidence_result`，并把 `combined_confidence.level` 派生到 `final_confidence`
- ✅ `services/projection_three_systems_renderer.py` 的 confidence_evaluator 段改为 **read-only display**，从 `confidence_result` 派生（不再自算 conflict / overall）
- ✅ contract enforcement tests pass（11C §12.2 列出的 3 项）
- ✅ 全量 pytest 全绿

### 7.6 12F（RISK-9）

- ✅ `enable_ai_summary=False` 默认（disabled by default）
- ✅ 缺 source attribution → `status="refused_missing_sources"`
- ✅ post-check 阻断 trading / hard / forced / 新判断（禁止词命中 → `status="refused_policy_violation"`）
- ✅ 缺 OPENAI_API_KEY → `status="llm_unavailable"`
- ✅ 输出含 `non_judgment_confirmation`（5 个 false 字段）
- ✅ 输出含 `sentences[]` + `source_attribution[]`
- ✅ **不**含禁止字段（trading / hard / forced / required / production_promotion）
- ✅ `*_text` 兼容 wrapper 保留 3 个 caller 字符串契约
- ✅ contract enforcement tests pass（11F §13.1 列出的 21 项）
- ✅ 全量 pytest 全绿

### 7.7 12G（RISK-10）

- ✅ 3 个 promotion 模块 docstring 含 `OFFLINE_ONLY` 关键字
- ✅ active path import-guard tests pass（app / ui / projection / exclusion / confidence / final_report / predict 都不 import promotion）
- ✅ promotion 输出含 6 个 safety fields（`mode: "offline_only"` / `online_safe: False` / 4 个 `may_affect_*: False` / `requires_human_review: True`）
- ✅ promotion 输出**不**含禁止字段（hard_exclusion / forced_exclusion / required_decision / trading_action / production_promotion / `_PROTECTION_LAYER_CONNECTED` / modified_*）
- ✅ `promotion_execution_bridge` 默认 `execution_enabled == False`
- ✅ contract enforcement tests pass（11G §13.1 列出的 22 项）
- ✅ 全量 pytest 全绿

### 7.8 12E（RISK-8）

- ✅ predict.py docstring 含 "legacy compatibility wrapper" 标注
- ✅ 输出 dict 含 `kind: "legacy_predict_wrapper"`
- ✅ 输出 dict 含 `source_mapping`（compat_final_bias / compat_final_confidence / compat_prediction_summary 等）
- ✅ 输出 dict 含 `deprecation_notes`（非空 list）
- ✅ 输出 dict 含 `non_mutation_confirmations`（5 个 false 字段）
- ✅ predict.py **不**重算 confidence（缺 confidence_result 时 `final_confidence == "unknown"`）
- ✅ predict.py **不**因 exclusion_result 改写 projection
- ✅ predict.py **不**含禁止字段（trading / hard / forced / required）
- ✅ predict.py 不 import `services.continuous_smoothing*`
- ✅ re-entry guard 仍存在（防 V1↔V2 互调递归）
- ✅ 9+ active importer 调用契约**不破**（schema 兼容）
- ✅ contract enforcement tests pass（11E §11.1 列出的 13 项）
- ✅ 全量 pytest 全绿

---

## 8. 不允许混合事项

以下事项 **绝对禁止**进入 Step 12 任一 fix commit：

| 不允许混合 | 理由 |
|---|---|
| boundary fix + cleanup | 违反 commit-per-fix；cleanup 留 Step 14 |
| boundary fix + log cleanup | 同上；logs/regime_validation 等留 Step 14 |
| boundary fix + DB schema 变更 | 不在本轮范畴；属另一次 design |
| boundary fix + replay / validation 大输出生成 | 不在本轮范畴；focused test 即可 |
| boundary fix + 3R-5 / 3R-6 启动 | 必须 Step 12 + Step 13 + Step 14 全部完成后另开 launch review |
| boundary fix + 新增 candidate（projection / exclusion / confidence 任一类） | 违反 06 § / 07A–C / 08–10 |
| boundary fix + continuous_smoothing 复活 | 违反 06 §8 / 07B §11 / 07C §12 / 07D §12 |
| boundary fix + trading integration | 违反 07D §5 / §11；本轮无 trading 范畴 |
| boundary fix + large rewrite | 违反 commit-per-fix 最小行数原则 |
| Step 12 中处理 .claude/worktrees | 不在本轮范畴；按 hard rules 不处理 |
| Step 12 中处理 stash | 同上 |
| Step 12 中删除 / 移动**任何**文件 | 属 Step 14；fix commit **只**改文件内容 |
| Step 12 中跨 fix 共享逻辑（除 11D cutoff_guard helper 被 11C-A 引用） | 唯一允许的共享是 11D → 11C，由 11D §14 / 11C §7.3 显式认可 |
| Step 12 中 `git commit --amend` / `git rebase -i` 已 push commit | 违反 commit-per-fix 可回滚原则 |

---

## 9. Step 12 不应处理的对象

以下对象**不**在 Step 12 范畴；留给 Step 14 cleanup / quarantine：

| 对象 | 当前 untracked 状态 | 处理时机 |
|---|---|---|
| `logs/regime_validation/` | untracked | Step 14（需 backup retention policy） |
| `logs/historical_training/three_system_*` | untracked | Step 14 |
| `avgo_agent.db.backup_*`（7 个） | untracked | Step 14（需 backup retention policy） |
| `.claude/worktrees/`（含本 worktree） | untracked | 按 hard rules 不处理；worktree 生命周期自然清理 |
| `agent_loop.py` untracked | untracked | Step 14（决定入库或删除） |
| continuous_smoothing v1/v2 模块 + 配套 scripts/tests + 文档 | tracked but FROZEN_DIAGNOSTIC | **永久保留**为 baseline；不删 |
| 根级 v1 stub（`confidence_engine.py` / `contradiction_engine.py` / `risk_model.py`） | tracked，无 active import | Step 14（CLEANUP_LATER） |
| 旧 V1 `services/projection_orchestrator.py` | tracked，仅 V2 自身 import + tests | Step 14（QUARANTINE_LATER） |
| 旧 smoke output / W4 output | untracked | Step 14 |
| `.claude/handoffs/task_089_post_pr_cleanup.md` | untracked 旧 handoff | Step 14 |
| `.claude/legacy_tasks/` | tracked 归档 | Step 14（评估是否压缩归并） |
| `records/` 仓库根目录 | tracked，与 tasks/ 体系疑似重复 | Step 14（spot-check） |

> Step 12 实施期间，以上对象**全部不动**。Step 13 回归时仅作 baseline 对比；Step 14 才统一处理。

---

## 10. Step 13 回归检查要求

Step 12 全部或阶段性完成后，进入 Step 13 应检查：

### 10.1 测试

- ✅ 全量 `pytest tests/` 全绿
- ✅ `scripts/check.sh` 执行通过（如可运行）
- ✅ 每个 RISK 对应的 contract enforcement tests 全部通过
- ✅ 改写后的旧 tests 全部通过
- ✅ focused test 与全量 test 同时通过

### 10.2 契约对齐

- ✅ 06 三系统独立原则对齐（推演 / 否定 / 置信度互不读、互不改写）
- ✅ 07A–07D 四份 contract 字段 schema 对齐（`*_result.v1` 系列）
- ✅ 07E 一致性矩阵闭合
- ✅ 11A–11G 各设计的 §"输出结构设计" 字段全部出现在实际输出中

### 10.3 行为验证

- ✅ V2 active path 输出含并列字段：`projection_v2_raw.main_projection` + `exclusion_result` + `confidence_result` + `final_decision` + `projection_three_systems`
- ✅ 输出含 `non_mutation_confirmations`（11B / 11C / 11E / 11F / 11G 各处）
- ✅ 输出含 `cutoff_guard`（11D 各处）
- ✅ 输出含 `source_attribution` / `source_mapping`（11B / 11E / 11F）
- ✅ 输出**不**含禁止字段（hard / forced / required / trading / production_promotion / `_PROTECTION_LAYER_CONNECTED`）
- ✅ ai_summary 默认 `status: "disabled"`；caller 显式 opt-in 后才生成

### 10.4 边界验证

- ✅ active path **不** import frozen diagnostic（continuous_smoothing v1/v2）
- ✅ active path **不** import promotion modules（除 offline 训练）
- ✅ ai_summary **不**回写 final_report / 三系统
- ✅ confidence_evaluator **不**修改 projection / exclusion
- ✅ memory feedback / preflight 路径**不**含 future leakage

### 10.5 UI / Smoke

- ✅ `app.py` Streamlit 启动正常
- ✅ `predict_tab` / `home_tab` / `history_tab` / `review_tab` 渲染不崩
- ✅ predict tab 显示的 `final_confidence` 在 12C-B 完成后取值合理（不长期 unknown）
- ✅ ai_summary disabled 时 UI 友好降级（不崩）

### 10.6 不允许在 Step 13 做

- ❌ 解锁 3R-5 / 3R-6
- ❌ 启用 promotion_execution_bridge
- ❌ 提交 raw output 到 git
- ❌ 修复发现的"小问题"借机 cleanup

---

## 11. Step 14 cleanup 前置条件

> **只有** Step 12 全部 fixes + Step 13 regression 全部通过后，**才能**进入 Step 14。

Step 14 才处理：

- quarantine 候选（旧 V1 orchestrator / soft_metadata_injection / review cluster / automation_wrapper）
- 根级 v1 dead stubs（confidence_engine.py / contradiction_engine.py / risk_model.py）
- 11A–11G fix commit 中保留的 dead code（`_apply_exclusion` / `_apply_preflight_influence` / `_confidence_from_score` / `_summarize` / 旧 prompt 常量等）
- 旧 logs（logs/regime_validation/ / logs/historical_training/three_system_*）
- DB backup（avgo_agent.db.backup_*）
- 旧 handoff（.claude/handoffs/task_089_post_pr_cleanup.md）
- .claude/worktrees/（按 hard rules 不主动处理；worktree 生命周期自然清理）
- frozen diagnostic（continuous_smoothing v1/v2）—— 仅在 policy 允许时才 cleanup；默认**保留**
- `records/` 与 `tasks/` 是否归并

> Step 14 每项 cleanup **独立 PR**；不混合。

---

## 12. 是否允许进入 3R-5 / 3R-6

> **NO.**

理由：

1. **Step 12 尚未实现**（11A–11G 是设计，未落地代码）
2. **Step 13 尚未回归**
3. **contract enforcement** 尚未落地（无 contract test 锁定）
4. **cleanup 尚未做**（dead code 仍存在，会干扰新阶段判断）
5. **不能在边界未修前开启新阶段**（六个月 boundary 违规仍在 main 上）

进入 3R-5 / 3R-6 的**严格前置条件**：

- ✅ Step 12 全部 8（最小）/ 12（含 11E 拆分）个 commit 入 main
- ✅ Step 13 全部回归通过（§10）
- ✅ Step 14 cleanup / quarantine 至少**关键项**完成（v1 dead stubs / dead code 删除 / 不再有 active path 含违规）
- ✅ **另开** launch review 文档（不在 06–11H 范畴；属 12+ 阶段独立 PR）
- ✅ **显式更新** 06 / 07A–D contract（如需要新增 candidate 类型 / 改 schema）
- ✅ **不**借 cleanup 之机偷偷启用 candidate / promotion

任何**借口**（"只是改一行" / "测试已通过" / "影响小"）都**不**构成跳过前置条件的理由。

---

## 13. Step 12 启动条件

允许启动 **Step 12-A（RISK-1+6）** 的条件：

| 启动条件 | 状态 |
|---|---|
| 06 三系统独立原则已 commit 入 main | ✅ `0979d93` |
| 07A/B/C/D 四份 contract 已 commit 入 main | ✅ `909d5f2` |
| 07E 一致性 review 已 commit 入 main | ✅ `a0956f3` |
| 08 architecture diagnosis 已 commit 入 main | ✅ `1186aa7` |
| 09 module inventory 已 commit 入 main | ✅ `a3facbd` |
| 10 cleanup plan 已 commit 入 main | ✅ `c5737e2` |
| 11A–11G 七份子设计已 commit 入 main | ✅ `cdc0f6c` / `b5236b8` / `6f1671d` / `1bc6449` / `e32372a` / `3a0fe94` / `ea4ab9a` |
| **11H sign-off 已 commit 入 main** | ⏳ 待本文件 commit |
| main 仓库 `pytest tests/` baseline 全绿 | ⏳ Step 12 启动前 spot-check |
| `scripts/check.sh` 当前可执行 | ⏳ 同上 |
| V2 active path 端到端 smoke 通过 | ⏳ 同上 |
| UI（Streamlit predict_tab / home_tab）端到端可渲染 | ⏳ 同上 |
| Step 12 实施环境就绪（worktree 干净） | ⏳ 同上 |

### 13.1 启动 12A 时必须

- ✅ 显式声明"只修 12A，不顺手修其他 RISK"
- ✅ 先写 §11A §8 列出的 7 个 failing contract test（red baseline）
- ✅ 实施修复（修 main_projection_layer + projection_orchestrator_v2 + home_terminal_orchestrator + 改写旧测试）
- ✅ focused tests + 全量 pytest 全绿
- ✅ 手动 UI spot-check
- ✅ 单独 commit：`fix(boundary): RISK-1+6 decouple projection from exclusion`
- ✅ 不处理 logs / DB backup / worktrees / stash / 任何 untracked

### 13.2 启动 12A 时不允许

- ❌ 顺手修 RISK-2 / 3 / 6（注：RISK-6 与 RISK-1 在**同一 commit**，**不算**顺手修）/ 7 / 8 / 9 / 10
- ❌ 删除任何文件
- ❌ 处理任何 untracked
- ❌ 改 DB schema
- ❌ 跑大规模 replay
- ❌ 进 3R-5 / 3R-6
- ❌ 启用 promotion / 复活 continuous_smoothing
- ❌ 一次性写完 12A–12H 所有 commit

---

## 14. 严守边界

本轮**只是 sign-off**：

- 未改代码
- 未新增设计
- 未新增测试
- 未删文件
- 未移动文件
- 未写 DB
- 未改 DB schema
- 未跑 replay
- 未跑 validation
- 未处理 untracked / DB backup / stash / .claude/worktrees/
- 未启动 Step 12 实施
- 未进入 3R-5 / 3R-6
- 未新增任何 candidate
- 未复活 continuous_smoothing
- 未修改 11A–11G 任一份设计

本签收的修改路径：任何对 §3 总评、§4 推荐顺序、§5 依赖矩阵、§6 commit 粒度、§7 完成标准、§8 禁止混合、§10 回归要求、§12 / §13 启动条件的调整，都必须以**显式更新本文件**的方式提出；同时检查是否需要同步更新 11A–11G。

---

## 15. Sign-off 决议

依据 §2 文档清单 + §3 总评 + §4 顺序 + §5 依赖 + §6 commit 原则 + §7 完成标准 + §8 禁止混合 + §9 不处理对象 + §10 回归要求 + §11 cleanup 前置 + §12 / §13 启动条件，本签收**正式确认**：

> **Step 11A–11G 七份 boundary enforcement design 已完整入库 main。
> 跨设计无契约冲突，依赖图闭合，最低完成标准明确，禁止混合事项固定。**
>
> **可以在 11H 入库后启动 Step 12-A（RISK-1+6 projection / exclusion decoupling）。**
>
> **Step 12 必须按 §4 顺序、§6 commit-per-fix、§5 依赖矩阵、§7 完成标准、§8 禁止混合执行。**
>
> **Step 12 完成后按 §10 回归 → Step 13 → §11 前置 → Step 14 cleanup。**
>
> **3R-5 / 3R-6 必须在 Step 12 + Step 13 + Step 14 关键项完成、且另开 launch review 之后才考虑。**
