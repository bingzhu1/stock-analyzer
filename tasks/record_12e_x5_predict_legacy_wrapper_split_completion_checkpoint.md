# 12E-X5记录：predict.py Legacy Wrapper Split Completion Checkpoint

> 本记录是 **Step 12E 的收尾 checkpoint**。
>
> 本轮**只写 checkpoint 文档**：未改代码、未新增测试、未删文件、未移动文件、
> 未写 DB、未跑 replay / validation、未 commit / push、未默认迁移 run_predict
> 到 V2、未接 UI / app.py / command bar / contract_replay_writer、未进入 Step 13
> 实施、未启动 Step 14 cleanup、未进入 3R-5 / 3R-6、未顺手碰其他 RISK。

---

## 1. checkpoint 目的

本记录是 Step 12E 五阶段（X1 / X2 / X3 / X4-A / X4-B / X4-C）的**收尾签收
checkpoint**，作用：

- **不**新增设计、**不**改代码、**不**做 cleanup
- 用于**确认** `predict.py` legacy wrapper split 当前完成状态
- 为 **Step 13 regression / post-fix review** 设定边界与建议
- 为 **Step 14 cleanup / quarantine** 列出仍未做的债务与前置条件

签收对象：

- `predict.py` 已退化为 legacy compatibility wrapper
- `services/predict_legacy_adapter.py`（X4-A）
- `services/predict_legacy_v2_bridge.py`（X4-C）
- 6 份 boundary contract test 文件（X1–X4-C）

签收**不替代** Step 13；签收只确认 12E 的合规边界并冻结 12E 范畴。

---

## 2. 当前 main 状态

| 项 | 状态 |
|---|---|
| main 最新 commit | **`c125f91 feat(boundary): RISK-8 add isolated v2_payload-to-legacy bridge`** |
| 06 / 07A–E / 08 / 09 / 10 / 11A–11H | ✅ 全部入 main |
| 12A（RISK-1+6）/ 12B（RISK-2）/ 12C-A / 12D / 12C-B / 12F / 12G | ✅ 全部入 main |
| 12E-X1 / X2 / X3 / X4-A / X4-B / X4-C | ✅ 全部入 main |
| 12E-X5（本 checkpoint） | ⏳ 本文件 commit 后入 main |
| `run_predict` 默认路径仍未切 V2 | ✅ 锁定 |
| `v2_payload` 是 explicit opt-in（默认 None） | ✅ 锁定 |
| isolated bridge `predict_legacy_v2_bridge` 不接 active path | ✅ 锁定 |
| `pytest -q` baseline | **3252 passed / 10 skipped / 0 failed**（X4-C 入 main 后） |

12E 范畴内**已合并**的 commit 序列：

```
689183f docs(boundary): mark predict.py as legacy wrapper                       # X1
e666943 fix(boundary): RISK-8 wire final_confidence from confidence_result      # X2
e80e905 fix(boundary): RISK-8 wire summary from final_report                    # X3
03dfbda feat(boundary): add v2-to-predict legacy compatibility adapter          # X4-A
89de6a6 fix(boundary): RISK-8 wire v2_payload opt-in adapter into run_predict   # X4-B
c125f91 feat(boundary): RISK-8 add isolated v2_payload-to-legacy bridge         # X4-C
```

12E 范畴**未做**的事（属 Step 13 / Step 14）：

- 默认切 `run_predict` 到 V2
- 删除 v1 helper（`_summarize` / `_confidence_from_score` / `_raise_confidence` / `_lower_confidence` / `_normalize_confidence` / `_path_risk_from_confidence` 等）
- inner `primary_projection` / `peer_adjustment` / `final_projection` block 迁移
- 任何 cleanup（root dead stubs / DB backups / logs / `.claude/worktrees/`）

---

## 3. 12E-X1 完成状态（legacy wrapper 标记 + metadata foundation）

入 main commit：`689183f docs(boundary): mark predict.py as legacy wrapper`

固化的事实：

- `predict.py` 模块 docstring 含 **`LEGACY_COMPATIBILITY_WRAPPER`** 标识
- 模块新增常量：
  - `PREDICT_LEGACY_WRAPPER_KIND = "legacy_predict_wrapper"`
  - `PREDICT_LEGACY_WRAPPER_VERSION = "predict_legacy_wrapper.v1"`
- `run_predict(...)` 输出 dict 新增：
  - `wrapper_kind == "legacy_predict_wrapper"`
  - `wrapper_version == "predict_legacy_wrapper.v1"`
  - `legacy_compatibility == True`
  - `source_mapping`（X1 foundation：`compat_final_bias` / `compat_final_confidence` / `compat_prediction_summary` / `compat_primary_direction` / `compat_peer_adjustment` / `compat_path_risk` 等 6 个 foundation 键）
  - `deprecation_notes`（非空 list，含 "legacy" 关键字）
- 未改变核心业务逻辑（`build_primary_projection` / `apply_peer_adjustment` /
  `build_final_projection` / `_summarize` / 等 v1 helper 函数体保持不变）
- 未删除任何旧字段（9+ active importer 调用契约维持）
- 静态导入约束：`predict.py` 不 import `services.continuous_smoothing*`、不
  import promotion 三模块、不 import `services.ai_summary`

被以下 contract enforcement test 锁定：[tests/test_predict_legacy_wrapper_boundary.py](tests/test_predict_legacy_wrapper_boundary.py)（332 行）。

---

## 4. 12E-X2 完成状态（final_confidence 顶层兼容字段 from confidence_result）

入 main commit：`e666943 fix(boundary): RISK-8 wire final_confidence from confidence_result`

固化的事实：

- 顶层兼容字段 `final_confidence` / `confidence` 现在从
  `confidence_result.combined_confidence.level` 派生
- 缺 `confidence_result` 时输出 **`"unknown"`**（不再 fallback 到旧 v1
  heuristic 生成顶层 final_confidence）
- 提供了 `_extract_compat_confidence(confidence_result) -> str` helper（顶层
  使用）
- `source_mapping["compat_final_confidence"]` 标注真实出处
- 未改变 `final_direction` / `final_bias` 顶层取值
- 未改变 `prediction_summary` / `summary` 顶层取值
- 未改变 inner `primary_projection` / `peer_adjustment` / `final_projection`
  block 的旧 schema（仍是 X1 之前的 v1 形状；X4 / X5 才迁移）
- v1 helper 函数体仍在（`_confidence_from_score` 等仍存在；inner block 仍读它，
  但顶层不再读）
- 不调用 LLM、不写 DB、不读 future 数据

被以下 contract enforcement test 锁定：[tests/test_predict_x2_confidence_wiring_boundary.py](tests/test_predict_x2_confidence_wiring_boundary.py)（396 行）。

---

## 5. 12E-X3 完成状态（prediction_summary 顶层兼容字段 from final_report）

入 main commit：`e80e905 fix(boundary): RISK-8 wire summary from final_report`

固化的事实：

- 顶层兼容字段 `prediction_summary` / `summary` 现在优先从
  `final_report.combined_user_summary` 派生
- 缺 `final_report` 或 `combined_user_summary` 非空字符串时，degrades 到 v1
  legacy `_summarize(...)` 输出（不引入新判断、不调 LLM）
- 提供了 `_extract_compat_summary(final_report, legacy_summary) -> tuple[str, str]`
  helper，返回 `(text, source_label)`
- `source_mapping["compat_prediction_summary"]` 标注真实出处（`final_report` /
  `legacy_summary` 二选一）
- 未改变 `final_direction` / `final_confidence` / projection 字段
- wrapper 不调用 LLM、不写 DB、不读 future 数据
- 未删除 `_summarize(...)` 函数（仍作为 fallback；Step 14 才决定是否完全清理）

被以下 contract enforcement test 锁定：[tests/test_predict_x3_summary_wiring_boundary.py](tests/test_predict_x3_summary_wiring_boundary.py)（441 行）。

---

## 6. 12E-X4-A 完成状态（standalone V2-to-legacy adapter）

入 main commit：`03dfbda feat(boundary): add v2-to-predict legacy compatibility adapter`

固化的事实：

- 新增 [`services/predict_legacy_adapter.py`](services/predict_legacy_adapter.py)（640 行；14 个顶级 def / 类）
- 公共 API：`adapt_v2_payload_to_predict_legacy(v2_payload, *, fallback_legacy_payload=None) -> dict`
- 常量：
  - `ADAPTER_KIND = "v2_to_predict_legacy_adapter"`
  - `ADAPTER_VERSION = "v2_to_predict_legacy_adapter.v1"`
- adapter 是 **standalone pure mapping function**：
  - 不调用 `run_predict`
  - 不调用 V2 orchestrator（`run_projection_v2` / `projection_orchestrator_v2`）
  - 不调用 `final_decision` / `confidence_evaluator` / LLM
  - 不读 DB、不读文件、不写任何 I/O
  - 不 mutate `v2_payload` / `fallback_legacy_payload`
- 输出 schema 含：
  - `adapter_kind` / `adapter_version` / `source`
  - `legacy_fields`（18 个 key）
  - `source_mapping`（18 entries：`legacy_field` / `source_path` /
    `fallback_used` / `notes`）
  - `warnings`
  - `non_mutation_confirmations`
- 防御性清理 forbidden 字段（trading / hard / forced / mutation surfaces）

被以下 contract enforcement test 锁定：[tests/test_predict_legacy_adapter.py](tests/test_predict_legacy_adapter.py)（760 行）。

---

## 7. 12E-X4-B 完成状态（run_predict 显式 v2_payload opt-in）

入 main commit：`89de6a6 fix(boundary): RISK-8 wire v2_payload opt-in adapter into run_predict`

固化的事实：

- `run_predict(...)` 新增可选 kwarg：`v2_payload: dict | None = None`
- `_missing_scan_result(...)` 同步新增 `v2_payload` kwarg（透传给 overlay 助手）
- 默认 `v2_payload=None`：legacy 路径完全不变（X3 baseline byte-for-byte 保留）
- `v2_payload=<dict>`：调用 `_apply_v2_legacy_adapter_overlay(...)` 显式调用
  adapter overlay 18 个 allowlist 字段：
  - `final_bias` / `direction`
  - `final_confidence` / `confidence`
  - `prediction_summary` / `summary`
  - `primary_projection` / `peer_adjustment` / `final_projection` /
    `path_risk`
  - `supporting_factors` / `conflicting_factors`
  - `scan_bias` / `open_tendency` / `close_tendency`
  - `pred_open` / `pred_path` / `pred_close`
- `v2_payload` 非 dict（字符串 / list / int / bool）：不崩溃、不 overlay，标记
  `v2_adapter_used=False` 并加 warning
- `v2_payload=dict`：标记 `v2_adapter_used=True` 并附带 `v2_adapter_result`
  metadata（不含 bulk legacy_fields，已 merge 到顶层）
- run_predict 顶层不调用 V2 orchestrator
- run_predict 顶层不构造 v2_payload
- run_predict 模块级仍不 import `services.projection_orchestrator_v2`
  （`_build_projection_three_systems_attachment` 内部的 lazy import 仍存在，
  受 Task 104 re-entry guard 保护，X4-B 静态检查改为 AST top-level only）

被以下 contract enforcement test 锁定：[tests/test_predict_x4b_v2_payload_opt_in_boundary.py](tests/test_predict_x4b_v2_payload_opt_in_boundary.py)（576 行）。

---

## 8. 12E-X4-C 完成状态（isolated bridge）

入 main commit：`c125f91 feat(boundary): RISK-8 add isolated v2_payload-to-legacy bridge`

固化的事实：

- 新增 [`services/predict_legacy_v2_bridge.py`](services/predict_legacy_v2_bridge.py)（105 行；1 个顶级 def）
- 公共 API：`build_legacy_prediction_from_v2_payload(*, v2_payload, fallback_legacy_payload=None, symbol="AVGO") -> dict`
- 常量：
  - `BRIDGE_KIND = "predict_legacy_v2_bridge"`
  - `BRIDGE_VERSION = "predict_legacy_v2_bridge.v1"`
- 行为：
  - `v2_payload=None` / 非 dict → 调 `run_predict(None, …)` 不传 `v2_payload=`
    kwarg（即默认 legacy 路径），并附 warning
  - `v2_payload=dict` → 调 `run_predict(None, …, v2_payload=<dict>)` 走 X4-B
    opt-in path
- 模块级**不**导入 `predict.py`（lazy 在 helper 内部 import）
- 模块级**不**导入：`projection_orchestrator_v2` / `ai_summary` / promotion
  三模块 / `continuous_smoothing` / `app` / `ui.*` / `streamlit` / `sqlite3` /
  `prediction_store`
- active callers（`app.py` / `ui/predict_tab.py` / `ui/command_bar.py` /
  `ui/history_tab.py` / `ui/home_tab.py` / `ui/scan_tab.py` /
  `ui/research_tab.py` / `ui/review_tab.py` / `ui/inspect_tab.py` /
  `services/projection_orchestrator.py` /
  `services/contract_replay_writer.py` / `scripts/run_e2e_loop.py`）：
  - 不 import `services.predict_legacy_v2_bridge`
  - 不传 `v2_payload=` 给 `run_predict`
- bridge 不写 DB、不调 LLM、不读 future 数据
- bridge 不 mutate 输入

被以下 contract enforcement test 锁定：[tests/test_predict_legacy_v2_bridge.py](tests/test_predict_legacy_v2_bridge.py)（691 行；34 测试用例）。

---

## 9. 当前 predict.py 准确定位

`predict.py` 现在的定位是：

> **legacy compatibility wrapper / backward-compatible shell**。

更具体：

- **不再**被视为长期核心架构。core projection / confidence / aggregator 已分别
  落到 `services/main_projection_layer.py` / `services/confidence_evaluator.py`
  / `services/final_decision.py`（11A / 11B / 11C 修复后的版本）
- 仍**保留** `run_predict(...)` 入口，用于兼容 9+ active importer：
  - `ui/predict_tab.py`、`ui/history_tab.py`
  - `scripts/summarize_confidence_calibration_inputs.py`、`scripts/run_e2e_loop.py`
  - `services/projection_orchestrator.py`、`services/projection_review_closed_loop.py`
  - `services/review_agent.py`、`services/log_store.py`
  - `services/contract_replay_writer.py`
- **默认仍走 legacy path**（避免破坏 UI / scripts / tests）
- 新 V2 接入只通过 **explicit opt-in**：
  - `run_predict(..., v2_payload=<dict>)`（X4-B）
  - 或 `services.predict_legacy_v2_bridge.build_legacy_prediction_from_v2_payload(v2_payload=<dict>)`（X4-C）
- `wrapper_kind` / `wrapper_version` / `source_mapping` / `deprecation_notes`
  / `non_mutation_confirmations` 已显式声明在每次调用的输出中

文件规模：1519 行 / 45 个顶级 def 或 class。Step 12E 期间未删除任何函数定义（保留
v1 helper 作为 inner block 的 fallback 实现，Step 14 cleanup 才决定移除）。

---

## 10. 当前仍未做的事情（Step 12E 显式不做）

按 11H §4.8 / §8 的禁止混合原则，以下事项**未在 12E 完成**，需要后续阶段处理：

1. ❌ 未默认切换 `run_predict` 到 V2（默认 `v2_payload=None`，走 legacy）
2. ❌ 未删除任何 v1 helper 函数定义（`_summarize` / `_confidence_from_score` /
   `_raise_confidence` / `_lower_confidence` / `_normalize_confidence` /
   `_path_risk_from_confidence` / 等）
3. ❌ 未删除任何 legacy 字段
4. ❌ 未迁移 inner `primary_projection` / `peer_adjustment` /
   `final_projection` block（仍保持 v1 形状；顶层兼容字段已切到 V2 来源，inner
   block 未切）
5. ❌ 未清理 `_summarize` / v1 confidence helper dead-code 路径
6. ❌ 未处理 `tests/fixtures/app_analysis_context_fixture.py` 永久 monkeypatch
   `predict.run_predict` 的 hygiene issue（Step 12E-X1 起所有 boundary test 用
   `_fresh_predict_module()` + `importlib.reload(predict)` 防御此问题；fixture
   本身未修）
7. ❌ 未做 Step 14 cleanup / quarantine（root v1 stubs / 旧 V1 orchestrator /
   continuous_smoothing v1+v2 frozen diagnostic / 等）
8. ❌ 未进入 3R-5 / 3R-6
9. ❌ 未接 trading
10. ❌ 未跑 replay / validation 全量
11. ❌ 未改 active caller 接 `v2_payload`（`contract_replay_writer` /
    `ui/predict_tab` / `app.py` / `command_bar` 全部不传）
12. ❌ 未扩展 `source_mapping` 进一步标注 inner block 出处

---

## 11. remaining legacy debt

按当前 main 状态，predict 链路上仍存在的 legacy 债务：

| # | 债务项 | 归属阶段 |
|---|---|---|
| 1 | `predict.py` 1519 行内仍包含 v1 projection / summary / confidence helper 函数定义（dead 或半 dead path） | Step 14 cleanup |
| 2 | inner `primary_projection` / `peer_adjustment` / `final_projection` block 仍保留 legacy shape | Step 14 / 后续大重构 |
| 3 | `run_predict` 默认路径未切 V2 | 后续大重构（不在 11E 范畴） |
| 4 | `source_mapping` 仍有部分条目带 `pending` / future migration notes | Step 14 / 大重构 |
| 5 | 9+ existing active importer 仍依赖 `run_predict` 的 v1 schema | Step 14 + 各 importer 单独迁移 |
| 6 | `tests/fixtures/app_analysis_context_fixture.py` 永久 monkeypatch 不 restore | Step 14 cleanup（可独立 commit） |
| 7 | root v1 dead stubs（`confidence_engine.py` / `contradiction_engine.py` / `risk_model.py`） | Step 14 cleanup |
| 8 | 旧 V1 `services/projection_orchestrator.py` 仍存在（仅 V2 自身 import + tests） | Step 14 quarantine |
| 9 | `continuous_smoothing` v1+v2 frozen diagnostic（保留为 baseline，不删） | Step 14 决策（默认保留） |
| 10 | 旧 logs（`logs/regime_validation/` / `logs/historical_training/three_system_*`） | Step 14 |
| 11 | DB backup（`avgo_agent.db.backup_*`，7 个） | Step 14 |
| 12 | 旧 handoff（`.claude/handoffs/task_089_post_pr_cleanup.md`） | Step 14 |
| 13 | `.claude/worktrees/` | 按 hard rules 不主动处理（worktree 生命周期自然清理） |
| 14 | `.claude/legacy_tasks/` | Step 14 决策（评估是否压缩归并） |

> Step 12E **不**处理上述任何一项。Step 13 regression 也**不**处理。Step 14
> 才允许 cleanup，且每项**独立 PR / commit**（11H §11 / §6.2 锁定）。

---

## 12. 为什么现在不默认迁移 V2

**显式不迁移**的理由：

1. **active importer 多**：9+ 个 active 调用点直接读 v1 schema 字段
   （`final_bias` / `final_confidence` / `prediction_summary` /
   `primary_projection` / `peer_adjustment` / `final_projection`），任何默认
   迁移都会一次性改变所有 importer 的取值集
2. **UI / scripts / replay / log_store 仍依赖 legacy shape**：默认迁移会让这些
   消费者立刻感知 V2 取值集差异，可能导致 UI 渲染崩溃 / 历史 prediction_log 字段
   语义不一致 / replay 写入与既有数据不匹配
3. **Step 13 regression 尚未做**：默认迁移属于**行为级**改动，必须先有完整
   regression baseline 才能评估副作用
4. **Step 14 cleanup 尚未做**：v1 helper 函数体仍存在；如果默认迁移后删除 v1
   helper，inner block fallback 路径会丢失
5. **默认迁移属于更大架构切换**：需要独立 launch review 文档（不在 06–11H 范畴；
   属 12+ 阶段独立 PR），并需要**显式更新** 06 / 07A–D contract（如改 schema）
6. **现在只允许 explicit opt-in**：X4-B / X4-C 已经提供两条 explicit V2 接入
   路径；任何想要 V2 行为的 caller 都可以选择显式 opt-in，**不**应被迫接受
   默认迁移

11E §13.3 / 11H §13 已经明确：fix commit 中**不**改 9+ active importer 的调用
契约，**不**做 large rewrite。默认迁移会同时违反这两条。

---

## 13. Step 13 regression 建议

Step 12E 全部入 main 后，**建议下一步进入 Step 13**（不是本轮做的，是给下一个
独立 session 的指引）。Step 13 应包含：

- ✅ 全量 `pytest -q` 全绿（baseline 锁定为 12E-X4-C 入 main 后的
  **3252 passed / 10 skipped / 0 failed**）
- ✅ focused boundary test batch：
  - 11A：`tests/test_main_projection_layer.py` / `tests/test_projection_exclusion_decoupling_boundary.py`
  - 11B：`tests/test_final_decision*.py` / `tests/test_final_decision_aggregator_purification_boundary.py`
  - 11C-A：`tests/test_confidence_evaluator.py`
  - 11C-B：`tests/test_confidence_result_wiring_boundary.py`
  - 11D：`tests/test_cutoff_guard.py` / `tests/test_memory_feedback_cutoff_guard_boundary.py`
  - 11F：`tests/test_ai_summary_boundary.py`
  - 11G：`tests/test_promotion_offline_only_boundary.py`
  - 11E：`tests/test_predict_legacy_wrapper_boundary.py` /
    `tests/test_predict_x2_confidence_wiring_boundary.py` /
    `tests/test_predict_x3_summary_wiring_boundary.py` /
    `tests/test_predict_legacy_adapter.py` /
    `tests/test_predict_x4b_v2_payload_opt_in_boundary.py` /
    `tests/test_predict_legacy_v2_bridge.py`
- ✅ `scripts/check.sh`（如可执行）
- ✅ `run_predict` default behavior spot-check（确认默认 `v2_payload=None`、
  `wrapper_kind == "legacy_predict_wrapper"`、`final_confidence` 可降级为
  `"unknown"`、`prediction_summary` 走 final_report 优先 / legacy 兜底）
- ✅ `v2_payload` opt-in behavior spot-check（用 `predict_legacy_v2_bridge` 或
  `run_predict(..., v2_payload=<dict>)` 验证 18 个 allowlist 字段被覆盖、
  `v2_adapter_used == True`、`v2_adapter_result` metadata 完整）
- ✅ `app` / UI smoke（如可启动）：predict_tab / home_tab / history_tab /
  review_tab 渲染不崩；UI 显示的 confidence 不长期 unknown（11C-B 已修）
- ✅ 静态确认无 active caller 传 `v2_payload`（重新跑
  `ActiveCallerStaticImportTests` 即可）
- ❌ 不解锁 3R-5 / 3R-6
- ❌ 不提交 raw output（replay / validation 输出）
- ❌ 不 add `logs/` / `avgo_agent.db.backup_*` / `.claude/worktrees/` /
  `.claude/handoffs/` 等到 git
- ❌ 不借机 cleanup（cleanup 属 Step 14）

Step 13 的 regression 报告应记录 `pytest` summary、boundary test 全绿确认、
UI smoke 结论、以及任何被发现需要进入 Step 14 cleanup queue 的"小问题"。

---

## 14. Step 14 cleanup 前置条件

> **只有** Step 13 regression 全部通过后，**才**允许进入 Step 14。

Step 14 才能处理（每项**独立 PR / commit**）：

- root v1 dead stubs（`confidence_engine.py` / `contradiction_engine.py` /
  `risk_model.py`）
- predict.py / final_decision.py 内未被调用的 v1 helper（`_summarize` /
  `_confidence_from_score` / `_raise_confidence` / `_lower_confidence` /
  `_normalize_confidence` / `_path_risk_from_confidence` / `_apply_exclusion`
  / `_apply_preflight_influence` / `_apply_research_adjustment` 内不再 active
  的分支 等）
- 旧 logs（`logs/regime_validation/` / `logs/historical_training/three_system_*`）
- DB backup（`avgo_agent.db.backup_*`）
- 旧 handoff（`.claude/handoffs/task_089_post_pr_cleanup.md`）
- frozen diagnostic（`continuous_smoothing` v1/v2）—— 默认**保留**为 baseline；
  仅当 policy 允许时才 cleanup
- `.claude/worktrees/` —— 按 hard rules 不主动处理；worktree 生命周期自然清理
- 旧 V1 `services/projection_orchestrator.py` quarantine（仅 V2 自身 import +
  tests；待评估是否压缩为 thin shim 或继续保留）
- `tests/fixtures/app_analysis_context_fixture.py` 永久 monkeypatch 不 restore
  的 hygiene issue
- `records/` 与 `tasks/` 是否归并
- `.claude/legacy_tasks/` 是否压缩归并

Step 14 期间**不**允许：

- 启动 promotion_execution_bridge
- 启用 candidate（projection / exclusion / confidence 任一类）
- 复活 continuous_smoothing
- 默认切 `run_predict` 到 V2（仍属架构级 launch review 范畴，**不**在 Step 14）

---

## 15. 允许下一步

✅ **允许**：

- **Step 13 regression / post-fix review**（按 §13 建议执行）

❌ **不**允许：

- 默认切 `run_predict` 到 V2
- 进 Step 14 cleanup（必须先 Step 13 通过）
- 解锁 3R-5 / 3R-6
- 接 trading
- 启用 production_promotion
- 引入 hard / forced / required exclusion
- 把 replay / validation raw output commit 到 git
- 把 `logs/` / `avgo_agent.db.backup_*` / `.claude/worktrees/` add 到 git
- `--amend` / `rebase -i` 已 push 的 12E commit
- 在 12E 范畴内追加新 X 阶段（X1–X4-C 已完成；X5 = 本 checkpoint；不再扩展）

---

## 16. 严守边界

本轮**只写 checkpoint 文档**：

- 未改代码（`predict.py` / `services/predict_legacy_adapter.py` /
  `services/predict_legacy_v2_bridge.py` 全部 byte-identical 与 main `c125f91`）
- 未新增测试
- 未删文件
- 未移动文件
- 未写 DB
- 未改 DB schema
- 未跑 replay
- 未跑 validation
- 未处理 untracked / DB backup / stash / `.claude/worktrees/`
- 未默认迁移 `run_predict` 到 V2
- 未接 UI / app.py / command bar / contract_replay_writer
- 未启动 Step 13 实施
- 未启动 Step 14 cleanup
- 未进入 3R-5 / 3R-6
- 未新增任何 candidate
- 未复活 `continuous_smoothing`
- 未顺手碰 RISK-1 / RISK-2 / RISK-3 / RISK-7 / RISK-9 / RISK-10

本 checkpoint 的修改路径：任何对 §3–§8 完成事实、§9 定位、§10 / §11 债务清单、
§12 不迁移理由、§13 / §14 / §15 允许下一步的调整，都必须以**显式更新本文件**
的方式提出；同时检查是否需要同步更新 11E / 11H。
