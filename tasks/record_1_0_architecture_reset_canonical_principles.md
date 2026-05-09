# 1.0记录：Architecture Reset Canonical Principles

> 本记录是 **AVGO Stock Analyzer 项目 1.0 阶段的最高准则**。
>
> 它整合 06 / 07A / 07B / 07C / 07D / 07E 三系统契约 + 13 / 15 boundary
> regression / cleanup signoff + 16A Architecture Reset Blueprint + 用户
> 已认可的"轻装上阵"战略方向，作为**后续所有开发的 canonical source of truth**。
>
> 旧的 0.x / 01–07 / 06–07 / 11–15 记录**保留**为 historical source。
> 任何冲突情况下，**以本 1.0记录为准**。
>
> 本轮**只**写文档：未改业务代码、未新增测试、未删除旧 records、未移动
> 旧 records、未处理 logs / DB backup / `.claude/worktrees/`、未跑 replay /
> validation、未写 DB / 未改 DB schema、未默认迁移 `run_predict` 到 V2、
> 未接 trading、未输出 buy / sell / hold、未输出 hard / forced / required、
> 未进入 3R-5 / 3R-6、未 commit / 未 push。
>
> 唯一 deliverable：本文件。

---

## 1. 1.0记录的目的

本文件做四件事：

1. **整合**：把 06 三系统独立原则、07A–07E 三系统 + final report 契约、
   13 / 15 boundary regression / cleanup 状态、16A Architecture Reset
   Blueprint，统一为一份精简的最高准则。
2. **canonical**：本文件是后续所有开发（设计、PR、code review、launch
   review）的判断依据。
3. **historical source 保留**：旧 0.x / 01–07 / 11–15 / 16A 全部保留；
   它们是**历史出处**，不是最高准则。任一旧 record 与本文件冲突时，
   **以 1.0 为准**；冲突点必须**显式记录**，不允许悄悄绕过。
4. **下一轮入口**：本文件不再讨论"如何修哪个 bug"。它只回答"未来系统
   长什么样、哪些事不允许做"。具体落地（module inventory、schema
   决策、隔离计划、PR 拆分）由后续 Step 16B / 16C / 16D / 16E / 16F
   完成。

---

## 2. 当前总战略

系统进入 **Architecture Reset** 阶段。

> **不再继续小修小补。**

正式架构采用：

- **1 个主干** — AVGO Trading Research System
- **9 个正式分支**：
  1. Data Layer
  2. Feature Layer
  3. Projection System
  4. Exclusion System
  5. Confidence System
  6. Final Report Layer
  7. Review & Learning Layer
  8. Evaluation Layer
  9. UI / Presentation Layer
- **1 个临时迁移区** — Temporary Migration Bridge（**不属于**正式架构，
  有明确退出条件，见 §10）

正式架构图（文字版）：

```
            外部市场数据 / 历史数据 / 事件数据
                          │
                          ▼
                  Branch 1  Data Layer
                          │
                          ▼
                  Branch 2  Feature Layer
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
 Branch 3 Projection  Branch 4 Exclusion  Branch 5 Confidence
   (最可能)             (最不可能)         (二者各自可信度)
        │                 │                 │
        └────────┬────────┴────────┬────────┘
                 ▼                 ▼
           Branch 6  Final Report Layer
            （仅 aggregate / 不 mutate）
                 │
        ┌────────┴────────┐
        ▼                 ▼
 Branch 7 Review &     Branch 8 Evaluation
 Learning（事后）       （signal-level 评估）
        │                 │
        └────────┬────────┘
                 ▼
        Branch 9  UI / Presentation
            （只展示，不重算）
```

**Temporary Migration Bridge** 不在主架构图上；它是迁移期的旁路兼容层，
退出条件满足后整体解散。

---

## 3. 为什么从 0.x 升级到 1.0

继续小修小补已经无法回答"系统胜率是多少"。当前真实状态（13 / 15 / 16A
已记录）：

1. **三套链路并存**
   - 旧链：`predict.run_predict` → `build_primary_projection` →
     `apply_peer_adjustment` → `build_final_projection`
   - V2 链：`services/projection_orchestrator_v2.run_projection_v2`
     内部仍**回调** `predict.run_predict`
   - 主页链：`services/home_terminal_orchestrator.build_home_terminal_orchestrator_result`
     是 app.py 主页用的独立链
2. **predict.py 仍承担旧核心逻辑**
   - 旧 `build_primary_projection` / `apply_peer_adjustment` /
     `build_final_projection` 仍然存在；UI 主入口仍是 `run_predict`
3. **UI 仍读旧字段**
   - `final_bias` / `final_confidence` / `primary_projection` /
     `final_projection` 在 `ui/predict_tab.py` 主面板仍是事实显示来源
4. **confidence_evaluator 字段不对齐，容易 unknown**
   - `_compute_agreement` 期望 `most_likely_state` / `ranked_states` /
     `most_unlikely_state` / `ranked_unlikely_states`
   - 实际 `main_projection` 输出 `predicted_top1.state`、`exclusion_layer`
     输出 `triggered_rule`
   - calibration_context 在 home_terminal / v2 路径**均未传**
   - 结果：agreement / level 长期 `unknown`
5. **直接跑准确率 / 胜率会混淆评估对象**
   - 同一日的 prediction 在三条链上字段不同、语义不同；
     不先统一系统入口与模块归属，evaluation 数字无法解释
6. **旧 raw data / logs / DB backup / replay output 堆积，造成认知污染**
   - 7 个 DB backup（已 14K ignore，本地保留）
   - 4 套 untracked replay / regime validation 子目录（已 14K ignore）
   - 26 个 `.claude/worktrees/`（已 14K ignore）
   - 历史 evaluation 输出散落在 `logs/historical_training/` 多目录
   - tracked log evidence 与 untracked raw output 边界不清

所以 1.0 的目标顺序是：

> **先定架构，再模块站队，再清场，再逐层重建。**

任何"先跑一跑胜率试试"、"先把这条链改通"、"顺手清个目录"都属于
0.x 模式的延续，**1.0 阶段禁止**。

---

## 4. 0.x / 01–07 原记录读取情况

> **重要前提**：项目里实际不存在 `record_0_1` / `record_0_2` / ... /
> `record_0_7` 命名的 numeric 0.x records；也不存在 `record_01`–`record_05`。
> 用户对话中提到的"0.1–0.7 / 01–07 相关原始记录"应理解为**项目早期
> tasks/任务定义 + 06 起的契约 record 序列**。本节只列**实际读取到**
> 的 record 文件，**不**编造 missing 文件的内容。

| ref | file | found | status / note |
|---|---|---:|---|
| 0.1–0.7 numeric records | `tasks/record_0_1*.md` ... `tasks/record_0_7*.md` | ❌ | **missing** — 项目无此命名族；引用按 `inferred from project conversation and user-confirmed direction` 处理 |
| 01–05 numeric records | `tasks/record_01*.md` ... `tasks/record_05*.md` | ❌ | **missing** — 项目无此命名族；早期任务定义见 `tasks/001_*.md` ... `tasks/010_*.md`（task-level 定义，**不是** architecture record） |
| 06 三系统独立原则 | `tasks/record_06_three_system_independence_principle.md` | ✅ | read（见 §11 引用） |
| 07A 推演契约 | `tasks/record_07a_projection_system_contract.md` | ✅ | read |
| 07B 否定契约 | `tasks/record_07b_exclusion_system_contract.md` | ✅ | read |
| 07C 置信度契约 | `tasks/record_07c_confidence_system_contract.md` | ✅ | read |
| 07D final report 契约 | `tasks/record_07d_final_report_aggregator_contract.md` | ✅ | read |
| 07E 三契约一致性 review | `tasks/record_07e_three_system_contract_consistency_review.md` | ✅ | read（结论：PASS_WITH_MINOR_CLARIFICATIONS） |
| 08 architecture diagnosis | `tasks/record_08_three_system_architecture_diagnosis.md` | ✅ | exists（按命名推断；本轮未重新通读） |
| 09 module inventory detail | `tasks/record_09_module_inventory_detail.md` | ✅ | exists（按命名推断） |
| 10 keep/freeze/quarantine/cleanup plan | `tasks/record_10_keep_freeze_quarantine_cleanup_plan.md` | ✅ | exists |
| 11A–11H boundary enforcement design | `tasks/record_11a_*.md` ... `tasks/record_11h_*.md` | ✅ | exists（11h 为 signoff） |
| 12E X5 predict legacy wrapper split | `tasks/record_12e_x5_*_completion_checkpoint.md` | ✅ | exists |
| 13 post-fix regression boundary review | `tasks/record_13_post_fix_regression_boundary_review.md` | ✅ | read |
| 14A–14M cleanup series | `tasks/record_14a_*.md` ... `tasks/record_14m_*.md` | ✅ | exists |
| 15 cleanup regression final signoff | `tasks/record_15_cleanup_regression_final_status_signoff.md` | ✅ | read |
| 16A architecture reset blueprint | `tasks/record_16a_architecture_reset_blueprint.md` | ⚠️ | exists as **untracked** in current worktree（本次会话上一轮已写） |

> **结论**：1.0 canonical principles 是基于 06 / 07A–07E + 13 / 15 + 16A
> blueprint + 用户认可的"轻装上阵 / 九分支架构"战略方向**直接派生**的；
> 0.1–0.7 / 01–05 的命名族不存在，**不构成**本文件的 historical source
> 缺口（项目早期决策由 task 001–010 + record_06 起承担）。

---

## 5. 保留原则（与 1.0 不冲突，整体保留）

以下原则在 0.x / 01–07 / 11–15 / 16A 中已经写明，1.0 **整体保留**：

1. **三系统独立原则**（来自 06）
   - 推演 / 否定 / 置信度三系统**互相独立**，不读取（推演不读否定 /
     否定不读推演）、不改写
   - 任意系统输出**不得回流**到另一系统的输入
2. **主推演系统只回答"最可能"**（07A）
3. **否定系统只回答"最不可能"**（07B）
4. **置信度系统只评价，不改写**（07C）
5. **Final Report 只能汇总和展示，不能 mutate / 不引入新判断**（07D）
   - `combined_user_summary` 中任一句话必须能在三系统输出找到对应来源
6. **复盘只能事后学习，不能当次改答案**（06 + 07A §3.2 + 07B §3.2 +
   07C §3.3）
7. **Evaluation 只评估 signal，不做交易**（16A Branch 8）
8. **2026-01-01 之后保留为 final holdout**（07A §3.2 / 07B §3.2 /
   07C §3.2 / 07D §3.2）
9. **未来主系统标准窗口 = 15 trading days**（07A §3.1 / §9）
   - 当前 20d 实现暂为 legacy / compatibility，需在 16C 之后迁移
10. **volume / turnover 是股票分析关键输入**
    - Data / Feature 层必须保留 volume / turnover 字段；不可在 cleanup
      / refactor 中以"简化"为由移除
11. **主仓库必须轻装上阵**
    - active repo surface 只放正式架构内的代码 + 必要文档 + 必要 fixture
12. **旧 raw logs / DB backups / replay outputs 不长期堆在 repo**
    - 已通过 14K `.gitignore` 6 行 pattern 实现 active 隔离；下一阶段
      （16D 之后）按用户单独确认决定 MOVE / DELETE
13. **历史价值保留为 summary / manifest / archive**
    - 已结案的 evaluation 输出、historical replay 报告，必要时保留
      markdown summary 进 repo；raw `.csv` / `.json` / `.jsonl` /
      `_run.log` 留本地或 archive
14. **continuous_smoothing v1 / v2 永久 FROZEN_DIAGNOSTIC**
    - 06 §8 / 07B §11 / 07C §12 / 07D §12 已锁
15. **promotion 三模块永久 OFFLINE_ONLY**
    - 11G + 13 §4 / §5 + 15 §6 已锁；不进任何 active path
16. **CLAUDE.md hard rules 全部保留**：
    - 不让 LLM 决定股票方向
    - scanner / matcher / encoder 是硬规则层，优先保留
    - app.py 只允许最小改动
    - 新逻辑优先放 services/ 或 ui/
    - 所有 AI 输出必须结构化
    - 改完必须运行统一检查脚本

---

## 6. 废止原则（1.0 起明确禁止）

以下旧做法在 1.0 起**明确废止**。任何 PR / design / launch review 涉及以下
事项之一时，**默认 reject**，除非显式更新本文件：

1. **继续小修小补**（在三套并行链路上做局部修补）
2. **多条主链长期并行**
   - 旧链 / V2 链 / home_terminal 链不能再"长期共存"；16C / 16E 之后
     必须收敛到单一主链 + 1 个临时 Bridge
3. **适配层作为正式架构层**
   - `services/predict_legacy_adapter.py` /
     `services/predict_legacy_v2_bridge.py` 等只能作为
     `TEMP_MIGRATION_BRIDGE`，**不**进 9 分支正式架构
4. **predict.py 作为核心大脑**
   - 1.0 起 `predict.py` 是 Bridge 内的 legacy wrapper；不再扩展、不再
     新增功能；最终随 Bridge 退出条件满足而解散
5. **Final Report 重新裁判结果**
   - Final Report 不得改写 `most_likely_state` / `most_unlikely_state` /
     `confidence_*`；不得引入新判断
6. **Confidence 改写 Projection / Exclusion**
   - 07C §5 / §6 / §7 已锁；1.0 重申
7. **Exclusion 读取 Projection final result**
   - 07B §3.2 / §6 / §10 已锁；1.0 重申
8. **Projection 读取 exclusion_result**
   - 07A §3.2 / §6 / §10 已锁；1.0 重申
   - 注：当前 `services/main_projection_layer.py` 仍 import
     `build_peer_alignment` from `services/exclusion_layer.py`，且形参
     仍接受 `exclusion_result`（靠 `del` 守边界）。这是 16C / 16E 必须
     修掉的结构性违规
9. **旧 raw logs / DB backup / replay output 长期堆在主仓库**
10. **unclear legacy module indefinitely kept**（不打标签 / 不写退出条件）
11. **直接跑胜率而不先统一评估对象**
12. **3R-5 / 3R-6 由 cleanup 或 signoff 自动解锁**
    - 13 §9 / 15 §8 已锁；1.0 重申
    - 必须**单独** launch review，含 dry-run / shadow comparison /
      risk assessment / rollback plan / 用户显式确认
13. **复盘层成为第四个预测系统**
    - Branch 7 Review & Learning 是错题本，不是预测者；不允许 review
      逻辑直接修改当次 `projection_result` / `exclusion_result` /
      `confidence_result` / `final_report`
14. **UI 层参与判断**
    - Branch 9 只展示；不重算 confidence、不改 final report、不根据
      展示需要改字段含义；任何展示文本必须在 final_report / review /
      evaluation 中找到出处
15. **借 cleanup / regression / signoff 顺手做未授权动作**
    - 13 §10 / 14A §10 / 14J §10 / 14L §7 / 15 §11 已锁；1.0 重申
16. **复活已 quarantine 的 v1 stubs**
    - `archive/legacy/root_stubs/confidence_engine.py` /
      `contradiction_engine.py` / `risk_model.py` 已含 `_DEPRECATED.md`，
      不得再 import
17. **复活 continuous_smoothing 作为 active candidate**

---

## 7. 1.0 Canonical System Goal

**系统目标**：

> 构建一个围绕 AVGO 的 **trading research system**，**不是**自动交易
> 执行系统。

**系统要能**：

- 查数据（Data Layer）
- 加工特征（Feature Layer）
- 做结构判断（Projection 输出最可能）
- 做反向判断（Exclusion 输出最不可能）
- 做可信度评价（Confidence 评价二者）
- 三系统推演结果汇总展示（Final Report）
- 复盘纠错 / 形成 lesson（Review & Learning）
- 做历史评估（Evaluation：signal win-rate）
- 辅助研究决策（UI 展示）

**系统不能**：

- 自动交易
- 输出 hard / forced / required
- 直接输出 buy / sell / hold
- 让 LLM 直接决定股票方向（CLAUDE.md hard rule 1）
- 绕过 launch review 进入 3R-5 / 3R-6
- 自动 production_promotion
- 自动 default migrate `run_predict` 到 V2

---

## 8. 九分支正式架构

> 每个分支只列**职责 / 输入 / 输出 / 禁止**四项。模块归属（候选模块、
> 当前风险）见 16A 蓝图 §5–§13；每个模块的最终标签由 16B Module
> Stand-up / Ownership Inventory 给出。本节只定**契约级**边界。

### Branch 1：Data Layer

**职责**：

- 读取 AVGO / NVDA / SOXX / QQQ 行情数据（OHLCV）
- 读取历史行情 / 历史五状态样本
- 读取成交量 / 成交额（**volume / turnover 必须保留**）
- 读取事件 / 财报 / 新闻上下文（如已有 collector）

**输入**：外部数据源（yfinance / 本地 CSV / DB）。

**输出**：raw OHLCV / panel / 历史样本表。**不**含任何 projection /
exclusion / confidence / final_report 字段。

**禁止**：

- 不预测
- 不否定
- 不生成置信度
- 不输出最终结论
- 不读取下游系统输出
- 不读取 future outcome（在线 inference 路径）

---

### Branch 2：Feature Layer

**职责**：

- 把原始数据转成统一 feature payload
- 生成 **15 日窗口**特征（未来标准；当前 20d 为 legacy / compatibility）
- 生成 ret1 / ret3 / ret5 / ret10
- 生成价格位置（pos）、成交量比、成交额、K 线特征（shadow_ratio）
- 生成 peer feature（NVDA / SOXX / QQQ ret1 + peer_alignment）
- 生成历史相似样本特征
- 生成 regime label（如有）

**输入**：Branch 1 Data Layer 的原始 OHLCV / panel / 历史样本。

**输出**：`feature_payload`（dict / typed dict），统一字段名 `snake_case`，
缺失语义用 `null` 不用 `0`。

**禁止**：

- 不预测、不否定、不生成置信度
- 不读取 projection / exclusion / confidence / final_report / review 输出
- 不依赖任意系统输出回灌

**1.0 重要约束**：

> `peer_alignment` 是 **Feature Layer 的资产**，**不是 Exclusion 的资产**。
> 当前 `build_peer_alignment` 住在 `services/exclusion_layer.py`，
> 16C / 16D 之后必须迁出到 Feature Layer，让 Projection / Exclusion
> 都从 Feature Layer import。

---

### Branch 3：Projection System

**职责**：

> 只回答"**最可能发生什么**"。

**输入**（白名单，依据 07A §3.1）：

- AVGO 自身行情 / 近 15 日结构（来自 Branch 2 Feature Layer）
- 五状态历史样本
- 历史相似结构
- NVDA / SOXX / QQQ peer 信号（来自 Feature Layer，**不**经 Exclusion）
- 成交量 / 成交额 / 位置 / 趋势 / 反转
- regime label

**输出**（07A §9 草案，schema_version `projection_system_result.v1`）：
`most_likely_state` / `ranked_states` / `state_probabilities`（或 scores）/
`primary_reasoning` / `key_supporting_signals` / `key_risk_signals` /
`uncertainty_notes` / `raw_evidence_refs`。

**禁止**（07A §3.2 / §5 / §10）：

- 不读取 `exclusion_result` / `confidence_result` / `final_report`
- 不输出 `most_unlikely_state` / `confidence_score` / `confidence_level` /
  `final_confidence` / hard / forced / required / trading / simulated_trade
- 不读取 future outcome / 2026 final-test range

---

### Branch 4：Exclusion System

**职责**：

> 只回答"**最不可能发生什么**"。

**输入**（白名单，依据 07B §3.1）：

- AVGO 自身行情 / 近 15 日结构
- 五状态历史样本中"最少发生"的状态
- 历史 rare-event pattern
- NVDA / SOXX / QQQ peer 非确认信号（来自 Feature Layer）
- 成交量 / 成交额 / 位置 / 趋势 / 反转
- regime label

**输出**（07B §9 草案，schema_version `exclusion_system_result.v1`）：
`most_unlikely_state` / `ranked_unlikely_states` / `state_impossibility_scores` /
`primary_exclusion_reasoning` / `rare_event_evidence` /
`historical_non_occurrence_summary` / `peer_non_confirmation_summary` /
`key_exclusion_signals` / `key_counter_signals` / `uncertainty_notes` /
`raw_evidence_refs` / `false_exclusion_risk` / `triggered_rules`。

**禁止**（07B §3.2 / §5 / §10）：

- 不读取 `projection_result` / `most_likely_state` / `final_prediction` /
  `primary_direction` / `final_report` / `confidence_result`
- 不根据主推演结果"选择否定对象"
- 不输出 hard / forced / required / trading / simulated_trade

---

### Branch 5：Confidence System

**职责**：

> 只回答"**这次推演和否定可靠吗**"。

**输入**（白名单，依据 07C §3.1）：

- 原始市场数据 / 历史五状态分布
- 历史 projection accuracy / exclusion success / false_exclusion
- 历史样本量
- 当前 `projection_result`（**只读**）
- 当前 `exclusion_result`（**只读**）
- regime label
- offline calibration 权重 / 校准表（不允许 online future outcome 直接入参）

**输出**（07C §9 草案，schema_version `confidence_system_result.v1`）：
`projection_confidence` / `exclusion_confidence` / `agreement_status` /
`conflict_level` / `combined_confidence` / `confidence_reasoning` /
`reliability_warnings` / `sample_size_notes` / `calibration_notes` /
`raw_evidence_refs`。

**禁止**（07C §5 / §11）：

- 不改写 `projection_result` / `exclusion_result`
- 不输出 `most_likely_state` / `most_unlikely_state` / `modified_*` /
  hard / forced / required / trading / simulated_trade
- 不允许 `confidence_result → projection / exclusion` 回流
- 不读取 future outcome 进入在线 inference 路径

---

### Branch 6：Final Report Layer

**职责**：

- 汇总 projection / exclusion / confidence 三系统输出
- 生成标准报告（schema 固定）
- 展示冲突 / 风险 / 证据来源
- 生成人能读懂的 final report（`combined_user_summary`）

**明确**：

> Final Report **不是**第四个预测系统。
> Final Report **是**报告编辑器 / 标准输出生成器。
> `combined_user_summary` 必须可由"读三系统输出 + 排版规则"重新派生。

**输入**（07D §3.1）：

- `projection_result`（只读）
- `exclusion_result`（只读）
- `confidence_result`（只读）
- 三系统的 `raw_evidence_refs`
- display metadata / formatting rules / risk disclosure 模板文本

**输出**（07D §9 草案，schema_version `final_report_aggregator_result.v1`）：
`projection_section` / `exclusion_section` / `confidence_section` /
`agreement_or_conflict_section` / `combined_user_summary` /
`risk_disclosure` / `evidence_summary` / `raw_evidence_refs` /
`non_mutation_confirmations`。

**禁止**（07D §5 / §6 / §7 / §8 / §11）：

- 不重新预测、不修改 projection / exclusion / confidence
- 不输出 hard / forced / required / trading_action / production_promotion /
  `_PROTECTION_LAYER_CONNECTED` / `*_mutation` / `modified_*` /
  `corrected_*`
- 不允许 `final_report → projection / exclusion / confidence` 回流
- 不读取 future outcome 进入当次报告

---

### Branch 7：Review & Learning Layer

**职责**：

- 记录真实结果（outcome capture）
- 对答案（已结案 prediction snapshot vs 真实 outcome）
- 判断哪个系统错了（projection 错 / exclusion 错 / confidence 错估）
- 提炼 lesson（错题本）
- 下次预测前提供提醒（pre-prediction briefing）

**1.0 明确**（与 06 §6 / §7 / 07A §3.2 / 07B §3.2 / 07C §3.3 一致）：

> Review & Learning 是**错题本**，**不是**第四个预测系统。
> 它**只能事后复盘**，**不能当次改答案**。
>
> 已结案的真实结果可以进入 Review；当次预测路径**禁止**任何 future
> outcome 回流到 projection / exclusion / confidence / final_report。

**输入**：

- 历史 prediction snapshot（来自 prediction store）
- 已结案的真实 outcome
- 历史 review 记录

**输出**：

- review record（hit / miss / why）
- lesson / rule memory entry
- pre-prediction briefing（向"下次"预测**展示**告警）

**禁止**：

- 不在当次预测路径中读取未来结果
- 不直接改写 `projection_result` / `exclusion_result` / `confidence_result` /
  `final_report`
- 不强制覆盖结果
- 不输出交易动作
- 不成为"第四个预测系统"

> **1.0 修复目标**：当前 `predict.py` 内 `_apply_briefing_caution` 仍然
> 修改 `final_confidence`。这是 0.x 遗留；16E 必须把 caution 移到展示
> 层（在 Final Report Layer 标注，而不是 mutate confidence）。

---

### Branch 8：Evaluation Layer

**职责**：

- 评估 projection accuracy（命中率随 regime / 结构 / 样本量）
- 评估 exclusion success / false_exclusion rate
- 评估 confidence calibration（level / score 与真实命中率的一致性）
- 评估 agreement / conflict 在历史上的表现
- 评估 **signal win-rate**

**1.0 明确**：

> 这里的 win-rate 是 **signal win-rate**（推演 / 否定 / 综合方向是否对），
> **不是 trading win-rate**（不计真实交易盈亏）。
>
> Evaluation 是**只读批处理**：消费历史 prediction snapshot + 历史
> outcome，产出 metrics；**不**回灌当次预测，**不**自动改规则。

**输入**：

- 历史 prediction snapshot（projection / exclusion / confidence /
  final_report 全部已写入 store）
- 已结案的真实 outcome
- holdout 区间策略（**保留 2026-01-01 之后为 final holdout**）

**输出**：

- accuracy / calibration / agreement / win-rate 表
- regime-segmented metrics
- evaluation report

**禁止**：

- 不计算真实交易收益
- 不输出 buy / sell / hold
- 不污染 2026-01-01 之后 final holdout
- 不用 evaluation 结果当场改规则
  - "当场" = 在线 inference 路径
  - 离线 calibration 仍允许，但其结果以"权重 / 校准表"形式回到
    Confidence System，不沿其他路径回流

---

### Branch 9：UI / Presentation Layer

**职责**：

- 展示 final report（projection / exclusion / confidence 三段并列）
- 展示三系统冲突 / 一致标注
- 展示复盘结果 / lesson / pre-prediction briefing
- 展示 evaluation summary / dashboard

**输入**：

- `final_report`（来自 Branch 6，**只读**）
- `review record`（来自 Branch 7，只读）
- `evaluation report`（来自 Branch 8，只读）

**输出**：浏览器渲染（Streamlit / HTML / Markdown）。

**禁止**：

- 不生成预测
- 不重算 confidence
- 不改 final report
- 不根据展示需要改字段含义
- 任何展示文本必须可在 final_report / review / evaluation 中找到出处
- **CLAUDE.md hard rule 3**：app.py 只允许最小改动

---

## 9. 三系统独立原则在 1.0 中的位置

06 三系统独立原则 + 07A–07D 四份契约**整体保留并嵌入 1.0**：

- **数据流方向严格**（见 07E §9 矩阵）：
  - Data → Feature → {Projection, Exclusion, Confidence}（三者**互相
    不读**）→ Final Report → {Review, Evaluation} → UI
  - 任何反向流（如 Final Report → Projection）**禁止**
- **三系统两两之间禁修改**：projection ↛ exclusion，exclusion ↛
  projection，confidence ↛ projection / exclusion
- **Final Report 对三系统只读展示**，**不 mutate**
- **Confidence 对 projection / exclusion 只读评价**，**不 mutate**
- **冲突不是 bug，是契约下的合法状态**（07B §6）；处理方式：Final
  Report 标注，不改写

> 1.0 起：07E §10 列出的 wording polish 仍是 **可选 / 不阻塞**；如做
> 文档级 patch 必须**显式更新**本 1.0 文件 + 对应旧 record。

---

## 10. Temporary Migration Bridge canonical principles

**性质**：

> Temporary Migration Bridge **不属于** 9 分支正式架构。
> 它在正式架构图中**不出现**。
> 它是迁移期的旁路兼容层，存在仅为不让旧调用方崩溃。

**职责**：

- 兼容旧 UI / 旧 replay / 旧 tests
- 翻译字段（旧 `predict_result` ↔ 新 final_report / confidence_result /
  projection_result / exclusion_result）
- 保护迁移期系统不崩

**1.0 候选模块**（与 16A §14 一致）：

- `predict.py`（含 `run_predict` legacy wrapper / 旧
  `build_primary_projection` / `apply_peer_adjustment` /
  `build_final_projection` / `_summarize` / `_apply_briefing_caution` /
  `_apply_v2_legacy_adapter_overlay`）
- `services/predict_legacy_adapter.py`
- `services/predict_legacy_v2_bridge.py`
- legacy `PredictResult` typed dict 字段（`final_bias` / `final_confidence` /
  `confidence` / `primary_projection` / `peer_adjustment` /
  `final_projection` / `path_risk` / `peer_path_risk_adjustment`）
- `services/projection_orchestrator.py`（V1 orchestrator；正式架构内**不**进任何分支）

**禁止**：

- 不做新判断
- 不重新计算 confidence
- 不继续扩大旧字段依赖
- 不作为未来正式主链路
- 不接 trading / hard / forced / production_promotion

**退出条件**（**全部**满足后才能解散；与 16A §14 一致）：

1. UI 全部读新 final_report schema（不再用 `final_bias` / `final_confidence` /
   `primary_projection` / `final_projection` 旧字段）
2. replay 全部读新 evaluation schema
3. tests 不再依赖旧 `PredictResult`
4. `run_predict` 不再作为主入口
5. legacy adapter / bridge 在 active path 中无 import
6. `services/projection_orchestrator.py` 不再被新链路依赖

> 任一项不满足，Bridge 必须保持**可工作**且**可回滚**。

---

## 11. 轻装上阵 / 主仓库 hygiene canonical

1.0 起，主仓库 active surface **只**保留：

- 9 分支正式架构内的代码模块
- Temporary Migration Bridge（带退出条件）
- KEEP_FROZEN_DIAGNOSTIC（带 `_DEPRECATED.md` / record 锚点）
- ARCHIVE（已 quarantine 至 `archive/legacy/...`）
- 必要的 fixture / config / docs（CLAUDE.md / tasks/ / handoff workflow）
- tracked log evidence（已结案、已写入 record 的 historical reference）

主仓库 active surface **不**保留：

- raw replay output / regime validation output（保留为本地或 archive，
  必要时仅留 markdown summary 进 repo）
- DB backup（`avgo_agent.db.backup_*`，14K 已 ignore；下一阶段决定 MOVE / DELETE）
- `.claude/worktrees/`（14K 已 ignore；harness 自动管理）
- 长期 untracked landmark（除 14L A2 / 14M / 15 §2 deliberate keep 之外）
- 跨多目录散落的 evaluation 输出（16C / 16D 之后统一 evaluation 输出
  存储位置 + schema）

历史价值的处理：

- summary / manifest / archive 形式保留（仅 markdown，不含 `.csv` /
  `.json` / `.jsonl` / `_run.log`）
- 必须有显式 record 锚点（不允许"匿名 archive"）

> 任何"在主仓库新建 raw output 目录"的提案，1.0 起默认 reject，
> 除非显式更新本文件。

---

## 12. Launch review gate（3R-5 / 3R-6）

> **1.0 起 3R-5 / 3R-6 仍然不能直接开启。**

进入 3R-5 / 3R-6 必须**全部**满足：

1. 9 分支站队完成（Step 16B 输出）
2. 目标 schema 唯一化（Step 16C 输出）
3. 隔离 / quarantine 计划已落地（Step 16D 输出）
4. 核心链 refactor 计划完成（Step 16E 输出）
5. 第一批代码 PR（Step 16F 起）已合并并通过 regression
6. 用户 manually 确认开启（不允许由 cleanup / signoff / regression 自动
   解锁，13 §9 / 15 §8 / 16A §18 一致）
7. 单独写 launch review doc，含：
   - dry-run / shadow comparison metrics
   - 显式风险评估（regime-edge / contradiction / exclusion edge cases）
   - 默认切换 rollback plan
   - 用户**单独**显式确认

**永久禁止**：

- trading 自动化
- hard / forced / required decision 接 LLM 输出
- production promotion 自动放行
- default V2 migration without independent launch review
- 重新引入 root level v1 stubs（已 quarantine）
- 重新引入 root level `agent_loop.py`
- 一次 commit 同时改业务 + `.gitignore` + `tasks/STATUS.md` hard rules
- 借任一阶段（cleanup / regression / signoff / blueprint）顺手解锁
  3R-5 / 3R-6

---

## 13. Cross-cutting hard rules（CLAUDE.md 锚定）

1.0 整体继承 `.claude/CLAUDE.md` 已锁定的项目级 hard rules：

| # | rule | 1.0 重申要点 |
|---|---|---|
| 1 | 不让 LLM 决定股票方向 | 三系统所有方向输出由硬规则 + 历史样本 + 校准表派生；LLM 只在 narrative / summary 中复述已派生结论 |
| 2 | scanner / matcher / encoder 是硬规则层，优先保留 | 1.0 起 scanner / matcher / encoder 数据读取部分归 Branch 1，特征推导部分归 Branch 2，结构判断部分归 Branch 3；**不**作为 candidate 替换目标 |
| 3 | app.py 只允许最小改动 | 1.0 起 app.py 仅作为 Branch 9 入口；任何业务逻辑不进 app.py |
| 4 | 新逻辑优先放 services/ 或 ui/ | 1.0 沿用 |
| 5 | 所有 AI 输出必须结构化 | 1.0 沿用；结构化 ≠ 自动 promotion |
| 6 | 改完必须运行统一检查脚本 | `scripts/check.sh` 仍是基础合规 gate |

---

## 14. 1.0 与现有 records 的关系

1.0 是 **canonical**；旧 records 是 **historical source**。

**冲突仲裁规则**：

- 任意旧 record 与 1.0 冲突 → **以 1.0 为准**
- 冲突点必须**显式记录**在本文件后续修订版中
- **不允许**在不更新 1.0 的情况下绕过 1.0 写 / 跑 / 改任何东西
- **不允许**修改旧 records 的字节（旧 records byte-frozen，禁止 retro-edit；
  与 15 §6 一致）

**与 16A 蓝图的关系**：

- 16A 是**蓝图**（架构详细图 + 模块初步站队 + 风险列表）
- 1.0 是**最高准则**（canonical principles + cross-cutting rules）
- 1.0 引用 16A 的具体落地（候选模块、当前风险），但 1.0 自身**不**
  替代 16B / 16C / 16D / 16E 的输出
- 16A 与 1.0 冲突时，**以 1.0 为准**；16A 内的具体细节（如某模块
  候选标签）不视为 canonical（仍由 16B 决定）

**与 06 / 07A–07E 的关系**：

- 06 / 07A–07E 是 **三系统 + final report** 的契约级 historical source
- 1.0 §5 / §8 / §9 整体保留这些契约
- 07E §10 列出的 wording polish 不阻塞 1.0；如做 patch 必须**显式更新**
  本 1.0 + 对应旧 record

**与 13 / 15 的关系**：

- 13 是 12E boundary fixes 的 regression signoff；15 是 14 cleanup 的
  signoff
- 1.0 接受这两份 signoff 的事实状态：
  - 12E X1..X5 已永久封禁 trading / hard / forced / promotion / mutation 表面
  - 14 cleanup 已完成；root v1 stubs 已 quarantine；`.gitignore` 6 行
    pattern 已生效
- 13 / 15 不与 1.0 冲突；1.0 不撤销 13 / 15 的 invariants

---

## 15. 后续执行路线

1.0 **不**直接落地代码。具体落地由后续 Step 完成：

| Step | 内容 | 性质 |
|---|---|---|
| **1.0**（本轮） | Architecture Reset Canonical Principles | 文档（最高准则） |
| **16A**（已 untracked） | Architecture Reset Blueprint | 文档（架构详图 + 模块初步站队） |
| **16B** | Module Stand-up / Ownership Inventory | 文档（每个模块逐一站队） |
| **16C** | Target Dataflow & Contract Decision | 文档（最终 schema 唯一化） |
| **16D** | Isolation / Quarantine Plan | 文档（Bridge 模块边界 + frozen marker） |
| **16E** | Core Chain Refactor Plan | 文档（PR 拆分 / 顺序 / 回滚） |
| **16F** | 第一个代码 PR（按 16E） | 代码 |

**明确**：

> 战略上大改。
> 执行上小步。
> 每一步都要可回滚。

每步**单独**走 plan → builder → reviewer → tester；**不**借任一步顺手
解锁 3R-5 / 3R-6、trading、default V2、promotion、`continuous_smoothing`
复活。

---

## 16. 1.0 维护规则

1.0 是 living document，但维护门槛**严格**：

1. **修改路径**：任何对 §2 / §5 / §6 / §7 / §8 / §9 / §10 / §11 /
   §12 / §13 / §14 的修改，必须**显式编辑本文件**，并在新版尾部加
   `## Revision history` 区段（首次修订时新增）。
2. **冲突解决**：旧 records 与 1.0 冲突时，**优先**修订 1.0（如需要），
   再宣告冲突点；**禁止**通过修改旧 records 的字节"消除"冲突。
3. **新分支 / 新原则的添加**：必须先有用户认可，再有 design record
   （如 16x 系列），最后才反映到 1.0；不允许 1.0 单方面新增分支。
4. **删除分支 / 削弱原则**：禁止。任何"删除"必须以新版 1.x / 2.0 形式
   显式提出，老版 1.0 保留为 historical source。
5. **PR 描述要求**：所有进入 active surface 的 PR 必须在描述中显式
   声明"compliant with 1.0 §X / §Y"或"explicit deviation from 1.0 §X
   (reason: ...)"；reviewer 必须依照 1.0 判断。
6. **launch review 要求**：所有 launch review doc 必须 cross-reference
   1.0 §12 的 7 项前提条件 + §13 的 cross-cutting hard rules。
7. **不允许"先改一改让它过 1.0"的妥协式重构**（07D §15 / 07E §12 一致）。

---

## 17. 严守边界

本轮 1.0 **只**写 canonical principles：

- ❌ 未改业务代码（无 `.py` 文件被修改）
- ❌ 未新增测试（`tests/` 字节不变）
- ❌ 未删除旧 records
- ❌ 未移动旧 records
- ❌ 未处理 logs / DB backup / `.claude/worktrees/`
- ❌ 未跑 replay / validation
- ❌ 未写 DB / 未改 DB schema
- ❌ 未默认迁移 `run_predict` 到 V2
- ❌ 未接 trading
- ❌ 未输出 buy / sell / hold
- ❌ 未输出 hard / forced / required
- ❌ 未启用任何 candidate / 未复活 `continuous_smoothing`
- ❌ 未触碰 RISK-1 / RISK-2 / RISK-3 / RISK-7 / RISK-8 / RISK-9 / RISK-10
- ❌ 未进入 3R-5 / 3R-6
- ❌ 未 commit / 未 push（按本轮指令）

唯一新增文件：[tasks/record_1_0_architecture_reset_canonical_principles.md](tasks/record_1_0_architecture_reset_canonical_principles.md)（本文件）。

后续修改路径：见 §16 维护规则。

---

## 18. 推荐下一步

**推荐**：

> **Step 16B：Module Stand-up / Ownership Inventory**

理由：

- 1.0（最高准则）+ 16A（架构详图）已就位
- 下一步必须**让所有关键模块逐一站队**，给出每个模块的 target branch /
  active caller / 与 07A–07D 契约对照下的合规度 / 风险 / 处置建议
- 16C / 16D / 16E 必须建立在 16B 输出之上；不能直接进
- 16F 第一个代码 PR 必须建立在 16E 输出之上；不能直接进

**不推荐**：

- 不推荐直接进 16C / 16D / 16E（必须先有完整 Module Inventory）
- 不推荐借 16B 顺手做代码改动（16F 才是第一个代码 PR）
- 不推荐借任一步解锁 3R-5 / 3R-6（§12 7 项前提必须全部满足）
