# Step 3R-4 — Cross-Window Validation Protocol Checkpoint

> **状态固化文档（cross-window validation protocol checkpoint），不实现，不改代码。**
> 本文档**冻结** Step 3R-4 design（commit `a58aad4`）的：3-fold v1
> 协议（W1/W2/W3 + 可选 4-fold W4）、6 个 validation metric、7 项
> gate threshold、10 项 no-go rule、`regime_validation_report.v1`
> 输出 schema、与 Step 3R-2 helper / Step 2G-8D 的衔接边界。
>
> 本轮**不动任何代码**：不改 `predict.py` / `run_predict` /
> `scanner.py` / `prediction_store.py` / `app.py` / 任何 `ui/*` /
> `services/*` / 任何 builder / DB schema / 任何 test 中的任何一处。
>
> **本文不实现验证工具、不写 helper、不实施 protocol**；只在
> markdown 层固化协议状态，作为后续 3R-2 / 3R-3 / 3R-5 / 3R-6 / 3R-7
> 的强制 gate。

---

## 1. 当前完成状态

- **Step 3R-0** restart scope checkpoint 已完成并进入 main（commit
  `1b7288e`）
- **Step 3R-1** regime label design + checkpoint 已完成并进入 main
  （commits `a8df93a` / `8d4fe8f`）
- **Step 3R-4** cross-window validation protocol design 已完成并进入
  main（commit `a58aad4`）
- 本 checkpoint **固定** Step 3R-4 协议的：
  - 3 个 v1 必备 window（W1 / W2 / W3）+ 1 个可选 W4
  - 2026-01-01 永久封禁
  - 3-fold leave-one-window-out 折叠（W4 启用后扩为 4-fold）
  - 6 个 validation metric
  - 7 项 gate threshold
  - 10 项 no-go rule
  - `regime_validation_report.v1` schema 9 项不变量
- **强制 gate**：**Step 3R-2 helper 必须等本 checkpoint 进 main 后
  才能启动**

---

## 2. 当前 main 状态

- main 最新 commit：**`a58aad4`**
- commit message：`docs(contract): Step 3R-4 cross-window validation protocol design`
- 上游：`origin/main` 已同步
- 测试基线：**2604 passed / 0 failed / 10 skipped**（与 Step 3R-1
  / Step 3 launch review / Step 2G-8C 终点一致；本步骤无代码改动，
  无回归）

本步骤新增文件（已 merge 到 main）：

| 路径 | 类型 | 说明 |
|---|---|---|
| `tasks/step_3r4_cross_window_validation_protocol_design.md` | 已进 main | 15 节、474 行；3-fold + 6 metric + 7 gate + 10 no-go + `regime_validation_report.v1` schema |

本 checkpoint 文档（即本文件）尚未 commit；本轮只写文档、不 commit /
push。

---

## 3. validation windows

| window | date range | paired (估) | status |
|---|---|---:|---|
| **W1** | 2023-01-03 → 2023-08-31 | ~ 130 | **v1 required** |
| **W2** | 2023-09-01 → 2024-02-29 | ~ 100（含 2024-02 shock 月） | **v1 required** |
| **W3** | 2024-03-01 → 2024-08-02 | ~ 56 | **v1 required** |
| **W4** | 2024-08-03 → 2025-12-31 | tbd | **optional**（仅在 Step 2G-8D extend replay coverage 完成后启用） |
| **final test** | **2026-01-01 → ∞** | — | **permanently forbidden** |

合计 v1 baseline ≈ 286 paired（与 Step 2G-7C / 8B / 8C / 3R-4
design 完全一致）。

---

## 4. validation protocol

3-fold leave-one-window-out（v1）：

| fold | train | validate（held-out） |
|---|---|---|
| F1 | W2 + W3 | **W1** |
| F2 | W1 + W3 | **W2** |
| F3 | W1 + W2 | **W3** |

W4 启用后扩为 4-fold（每个 window 都做一次 held-out）。

**协议要求**：
- **不允许只看 pooled result**：pooled metric 仅参考；gate 决策**不**
  由 pooled 触发
- **worst-window 决胜**：fold 中最差的 held-out window metric 决定
  candidate 整体 pass / fail
- **train 不偷看 validate**：每个 fold 的 train 阶段**不**得读取
  该 fold 的 held-out window 数据
- **anti-lookahead**：与 Step 3R-1 §7 8 项不变量一致；strict-causal
  monthly context derive
- **不依赖 2026 数据**：每个 fold train + validate 数据严格 ≤
  2025-12-31

---

## 5. 6 metrics

| # | metric | 用途 |
|---|---|---|
| 1 | `accuracy_delta_vs_baseline` | candidate 触发后整体 acc 提升幅度；防整体精度反降 |
| 2 | `false_exclusion_rate` | candidate 触发样本中 `direction_correct = 1` 比率；控制误杀；与 Step 2G-7C hard gate 对齐 |
| 3 | `net_benefit` | counterfactual：剔除触发样本后 base_acc 提升；与 Step 2G-7C hard gate 对齐 |
| 4 | `survival_case_preservation` | survival case（触发但预测正确）能在 sidecar 中明确呈现的比率；继承 Step 2G-6C / 7A 的 survival 语义 |
| 5 | `cross_window_variance` | candidate 在所有 held-out window 上 fer 的极差（max − min）；直接对应 Step 2G-8C R4 H1/H2 gap +0.18 |
| 6 | `minimum_window_sample_size` | per-fold held-out window 中 candidate 触发的 paired 样本数最小值；防 Step 2G-8B paired ≤ 11 噪声 pass |

---

## 6. gate thresholds

| metric | gate threshold | 范围 |
|---|---|---|
| `minimum_window_sample_size` | **≥ 20** | per-fold held-out window |
| `false_exclusion_rate` | **≤ 0.10** | per-fold held-out window，worst-window 决胜 |
| `net_benefit` | **≥ +0.05** | per-fold held-out window |
| `cross_window_variance` | **≤ 0.10** | 跨 fold 极差 |
| **`no single-window collapse`** | 任一 window **不能** fer ≥ 0.20 OR nb ≤ 0 | 兜底守卫 |
| `survival_case_preservation` | **≥ 0.80** | per-fold held-out window |
| `accuracy_delta_vs_baseline` | **≥ +0.02** | per-fold held-out window |

阈值可在**未来 checkpoint** 调整，**经过 launch review**；**不得**
用 2026 数据调（任何"看一眼 2026 再回头改"立即触发任务中止）。

---

## 7. 10 no-go rules

任意一条触发 → candidate 整体不通过：

| # | no-go 条件 |
|---|---|
| 1 | 任一 held-out window 样本数 < **20** |
| 2 | 任一 held-out window `false_exclusion_rate` > **0.20** |
| 3 | pooled pass 但 worst-window fail |
| 4 | candidate 需要 **2026** 数据才能 pass |
| 5 | `survival_case_preservation` < **0.80** |
| 6 | 任一 fold `cross_window_variance` > **0.10** |
| 7 | train 阶段读取了该 fold 的 held-out window 数据 |
| 8 | 触碰 **2026-01-01** 之后任何数据 |
| 9 | `accuracy_delta_vs_baseline` < **0**（剔除后整体精度反降） |
| 10 | validation report 缺失 §8 任意必备字段 |

**触发 no-go = candidate 报废**；不允许"差一点没过" 蒙混进入下一步。

---

## 8. `regime_validation_report.v1` schema

```json
{
  "schema_version": "regime_validation_report.v1",
  "windows": {
    "W1": {"start": "2023-01-03", "end": "2023-08-31", "paired": 130},
    "W2": {"start": "2023-09-01", "end": "2024-02-29", "paired": 100},
    "W3": {"start": "2024-03-01", "end": "2024-08-02", "paired": 56},
    "W4": null
  },
  "candidate_name": "...",
  "candidate_kind": "smoothing | formula | label_assignment",
  "fold_count": 3,
  "per_window_metrics": {
    "W1": {...},
    "W2": {...},
    "W3": {...}
  },
  "pooled_metrics": {...},
  "worst_window": "W2",
  "worst_window_metrics": {...},
  "cross_window_variance": {...},
  "leave_one_window_out": {
    "F1_train_W2_W3_validate_W1": "pass|fail",
    "F2_train_W1_W3_validate_W2": "pass|fail",
    "F3_train_W1_W2_validate_W3": "pass|fail"
  },
  "gate_status": {
    "minimum_window_sample_size": "pass|fail",
    "false_exclusion_rate": "pass|fail",
    "net_benefit": "pass|fail",
    "accuracy_delta_vs_baseline": "pass|fail",
    "cross_window_variance": "pass|fail",
    "survival_case_preservation": "pass|fail",
    "no_single_window_collapse": "pass|fail"
  },
  "overall_status": "pass|fail",
  "fail_reason": "...",
  "final_test_refusal": false,
  "data_cutoff_used": "2024-08-02",
  "warnings": []
}
```

### 8.1 9 项不变量

| 字段 | 不变量 |
|---|---|
| `schema_version` | 总是 `"regime_validation_report.v1"` |
| `windows` | W1 / W2 / W3 必须 present；W4 可为 null |
| `fold_count` | `3` 或 `4`（整数） |
| `per_window_metrics` | 每个 held-out window 6 metric 全 present |
| `worst_window_metrics` | 永远基于实际最差 fold 的 held-out window |
| `gate_status` | 7 项全部 `"pass"` 才能 `overall_status = "pass"` |
| `overall_status` | `"pass"` / `"fail"` 二选一；**不允许** `"partial"` |
| `final_test_refusal` | bool；`True` → 整个报告作废 |
| `data_cutoff_used` | ≤ `2025-12-31`；硬不变量 |

---

## 9. 与 Step 3R-2 的关系

| 维度 | Step 3R-2（read-only regime label diagnostics helper） |
|---|---|
| 启动条件 | **必须等本 checkpoint 进入 main 后**才能启动 |
| 输出 | 每个 `as_of_date` 的 `regime_labels.v1` + per-label per-window read-only diagnostics |
| 是否优化 thresholds | **❌ 否**；只**应用** Step 3R-1 design 的阈值候选 |
| 是否宣称 pass / fail | **❌ 否**；3R-2 只产出原始数据 |
| pass / fail 由谁宣称 | 由本协议下的 future validation tool（未来 3R-3 / 3R-6 实施时）输出 `regime_validation_report.v1` |
| 与本协议关系 | 3R-2 是**数据层**，本协议是**评分层**；解耦 |
| 是否被禁触碰本协议阈值 | **是**；3R-2 helper 不得修改 §6 阈值 |

---

## 10. 与 Step 2G-8D 的关系

| 维度 | Step 2G-8D extend replay coverage |
|---|---|
| 范围 | 把 replay 跑到 2024-08-03 → **2025-12-31**，扩充 paired 样本 |
| 是否触碰 2026 | **❌ 否**；2025-12-31 上限严格 |
| 与本协议关系 | 提供 W4 候选数据；启用 W4 后协议扩为 4-fold |
| 是否阻塞 v1 协议 | **❌ 否**；3-fold（W1+W2+W3）即可启动 |
| 是否阻塞 3R-2 启动 | **❌ 否**；3R-2 不依赖 W4 |
| 优先级 | 与本协议 / 3R-2 **解耦可并行**；3-fold v1 锁定后再扩 4-fold 增强结论 |

---

## 11. 当前禁止事项

| # | 禁止 | 理由 |
|---|---|---|
| 1 | 不直接进 **Step 3R-5** formula design | 必须先过 3R-2 helper + 3R-3 smoothing 在本协议下出报告 |
| 2 | 不直接进 **Step 3R-6** read-only simulator | 必须先过 3R-5 design |
| 3 | 不直接进 **Step 3R-7** sidecar integration | 必须先过 3R-6 在本协议下 cross-window pass |
| 4 | 不启 `hard` / `forced_exclusion` / `anti_false_exclusion_triggered` | Step 2G-8 / 8B / 8C 三重 NO-GO |
| 5 | 不升级 04 / 05 / 07 required | Step 2G 全程边界 |
| 6 | 不让 `_PROTECTION_LAYER_CONNECTED` 翻 True | Step 2G-8A v1 强不变量 |
| 7 | 不让 `hard_gate_status.protection_layer_connected` 自动 pass | 同上 |
| 8 | 不用 2026-01-01 之后 final test 数据 | 永久封禁 |
| 9 | 不改 `_build_exclusion_system` / `run_predict` / `scanner` 主链 | Step 2G "sidecar-only" 边界 |
| 10 | 不调本协议 §6 阈值（除非走 launch review） | 本 checkpoint 锁定 |

---

## 12. 下一步建议

按推荐优先级：

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **Step 3R-2** read-only regime label diagnostics helper | 新增 `services/regime_labels_builder.py` + tests + dashboard 字段；**首个动代码步**；本 checkpoint 进 main 后启动 | **本轮 / 下一轮** |
| 2 | **Step 2G-8D** extend replay coverage（2024-08 → 2025-12） | 数据层；为 W4 准备；与 Step 3R 解耦可并行；不触碰 2026 | **高** |
| 3 | **Step 3R-4.1** validation helper design（later） | 在 3R-2 / 3R-3 出原始数据后，设计在本协议下产出 `regime_validation_report.v1` 的 helper；纯 markdown 先行 | 中（3R-2 / 3R-3 完成后） |
| 4 | **不推荐**直接 3R-5 formula design | 必须先过 3R-2 / 3R-3 在本协议下出报告 | **❌** |
| 5 | **不推荐**直接 3R-6 read-only simulator | 必须先过 3R-5 design | **❌** |
| 6 | **不推荐** R4 hard implementation | Step 2G-8 / 8B / 8C 三重 NO-GO | **❌** |
| 7 | **不推荐**让 `_PROTECTION_LAYER_CONNECTED` 翻 True / Gate 5 / Gate 6 自动 pass | 与 Step 2G-8A v1 / Step 3R-0 一致 | **❌** |
| 8 | **不推荐**升级 04 required schema | Step 2G 全程边界 | **❌** |
| 9 | **不推荐**触碰 2026 final test range | 永久封禁 | **❌** |

**关键判断**：
- 顺序 = 本 checkpoint → 3R-2 helper（首个动代码步）→ 3R-3 smoothing
  → 3R-5 formula design → 3R-6 simulator → 3R-7 sidecar
- 任意一步在本协议下 fail → 整个 Step 3R 进入 NO-GO，Step 2G display
  路线为系统最终形态
- Step 2G-8D 与上述顺序**解耦可并行**

---

## 13. 严守边界

本文是**纯 checkpoint markdown**：

- ❌ 没改任何代码（`services/*` / `ui/*` / `tests/*` 全部未触碰）
- ❌ 没改 DB schema
- ❌ 没写 DB
- ❌ 没改 `run_predict` / `predict.py` / `scanner.py` /
  `prediction_store.py` / `app.py`
- ❌ 没改 `services/regime_features_builder.py` /
  `services/regime_diagnostics_dashboard.py` /
  `services/anti_false_exclusion_dashboard.py` /
  `services/soft_metadata_simulator.py` /
  `services/protection_layer_diagnostics.py` /
  `ui/protection_layer_diagnostics_renderer.py` / 任何 ui 模块 /
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
- ❌ 没运行 `pytest`（本轮纯文档；测试基线维持 commit `a58aad4` 时
  的 2604 / 0 failed / 10 skipped）
- ✅ 只新增 1 份 markdown checkpoint 文档（本文件）
