# Step 3R-4.1 — 4-Fold Validation Helper Design Checkpoint

> **状态固化文档（4-fold validation helper design checkpoint），不实现，不改代码，不写 DB，不运行 replay。**
> 本文档**冻结** Step 3R-4.1 design（commit `8e27254`）的：helper 公共
> API、W4 manifest 启动 gate、`regime_validation_report.v1` 输出 schema、
> 6 metric、7 gate threshold、worst-window 决胜规则、与 Step 3R-2
> helper / Step 2G-8D W4 输出 / hard / required / 2026 final test 边界
> 的衔接关系。
>
> 本轮**不动任何代码**：不改 `predict.py` / `run_predict` /
> `scanner.py` / `prediction_store.py` / `app.py` / 任何 `ui/*` /
> `services/*` / `scripts/*` / 任何 builder / DB schema / 任何 test
> 中的任何一处。
>
> **本文不实现 helper、不跑 replay、不写 DB、不接 trading API**；只
> 在 markdown 层固化 helper 设计状态，作为后续 3R-4.2 read-only
> validation helper implementation 的强制 gate。

---

## 1. 当前完成状态

- **Step 3 calibration restart launch review** 已完成并进入 main
  （commit `b8c781d`）
- **Step 3R-0** restart scope checkpoint 已完成并进入 main（commit
  `1b7288e`）
- **Step 3R-1** regime label design + checkpoint 已完成并进入 main
  （commits `a8df93a` / `8d4fe8f`）
- **Step 3R-4** cross-window validation protocol design + checkpoint
  已完成并进入 main（commits `a58aad4` / `abe3ba2`）
- **Step 3R-2** read-only regime labels builder + checkpoint 已完成并
  进入 main（commits `e2a681b` / `db7618b`）
- **Step 2G-8D** extend replay coverage 系列已收官（design / checkpoint
  / audit / 8D.1A patch + checkpoint / 8D.2 smoke + checkpoint / 8D.3
  full W4 / 8D.4 W4 checkpoint，commits `170617c` ... `4bdd782`）
- **Step 3R-4.1** 4-fold validation helper design 已完成并进入 main
  （commit `8e27254`）
- 本 checkpoint **固定**：
  - `build_regime_validation_report(...)` 公共 API + 7 参数
  - W4 manifest 启动 gate 6 项
  - 4-fold / 3-fold 退化路径
  - `regime_validation_report.v1` schema 14 项必备字段
  - 6 metric 计算公式 + edge case
  - 7 gate threshold（与 3R-4 protocol 完全对齐）
  - worst-window 决胜规则 + 5 级优先级
  - 10 no-go rules → `gate_status` 映射 + `overall_status` 决策表
  - 与 Step 3R-2 / Step 2G-8D / hard / required 边界
- **Step 3R-4.2 read-only validation helper implementation 仍未启动**：
  本 checkpoint 是 3R-4.2 之前的强制 gate

---

## 2. 当前 main 状态

- main 最新 commit：**`8e27254`**
- commit message：`docs(contract): Step 3R-4.1 4-fold validation helper design`
- 上游：`origin/main` 已同步
- 测试基线：**2689 passed / 0 failed / 10 skipped / 26 warnings /
  94 subtests**（与 commit `36e76c9` 一致；本 checkpoint 阶段无代码
  改动 → 基线不变）

本步骤新增文件（已 merge 到 main）：

| 路径 | 类型 | 说明 |
|---|---|---|
| `tasks/step_3r4_1_4fold_validation_helper_design.md` | 新增 | 17 节、585 行；helper API + W4 gate + 6 metric + 7 gate + output schema + 10 no-go 映射 |

本 checkpoint 文档（即本文件）尚未 commit；本轮只写文档、**不**
commit / push。

| 项 | 是否触碰 |
|---|---|
| 改代码 | ❌ 否 |
| 写 DB | ❌ 否 |
| 跑 replay | ❌ 否 |
| 改 services/* / scripts/* / tests/* | ❌ 否 |
| 改 DB schema | ❌ 否 |
| 接 yfinance / 网络 | ❌ 否 |
| 接 trading API | ❌ 否 |
| 触碰 2026 final test | ❌ 否 |

---

## 3. helper API

```python
build_regime_validation_report(
    records,
    *,
    candidate_name: str,
    candidate_kind: str = "smoothing | formula | label_assignment",
    windows: dict | None = None,
    final_test_cutoff: str = "2026-01-01",
    require_w4_manifest: bool = True,
    w4_manifest_path: str | None = None,
) -> dict
```

| 项 | 值 |
|---|---|
| 类型 | **pure read-only helper** |
| 是否跑 replay | ❌ 否（输入是已完成 records） |
| 是否生成 predictions | ❌ 否 |
| 是否读 DB | ❌ 否（除非 wrapper 明确提供 records） |
| 是否写 DB | ❌ 否 |
| 是否改 records | ❌ 否 |
| 是否改 protocol thresholds | ❌ 否（应用 protocol，不调阈值） |
| 是否暴露 threshold 参数 | ❌ 否（API 不允许 override 阈值） |
| 是否接 yfinance / 网络 | ❌ 否 |
| 是否接 trading API | ❌ 否 |
| 是否宣称 production pass | ❌ 否（report 仅供 design review；wiring 由独立 step 决定） |
| 是否触碰 2026 | ❌ 否（启动 gate + record-level cutoff 双重 hard stop） |

### 3.1 7 参数

| 参数 | 默认 | 说明 |
|---|---|---|
| `records` | required | 已完成 replay / review 的只读 record list |
| `candidate_name` | required | candidate 标识 |
| `candidate_kind` | `"smoothing"` | enum：`"smoothing"` / `"formula"` / `"label_assignment"` |
| `windows` | None → 默认 §5 | 显式 window 边界 override |
| `final_test_cutoff` | `"2026-01-01"` | hard cutoff |
| `require_w4_manifest` | **True** | True = 4-fold 强制；False 允许 3-fold 退化（不推荐） |
| `w4_manifest_path` | None | W4 manifest JSON 路径；None + `require_w4_manifest=True` → helper 拒跑 |

---

## 4. W4 manifest gate

helper 启动前**必须**读取 W4 manifest 并验证以下 6 项；任一失败 →
`overall_status="error"` + helper 拒跑 + report 作废。

| # | 检查 | 期望值 |
|---|---|---|
| 1 | `schema_version` | `"w4_replay_manifest.v1"` |
| 2 | **`final_test_touched`** | **`false`**（最关键） |
| 3 | `status` | `"ok"` |
| 4 | `paired_outcomes` | **`>= 20`**（与 §7 `minimum_window_sample_size` 一致） |
| 5 | `replay_window.start` / `replay_window.end` | `"2024-08-03"` / `"2025-12-31"` |
| 6 | `final_test_cutoff` | `"2026-01-01"` |

### 4.1 任一失败的统一处理

| 字段 | 值 |
|---|---|
| `overall_status` | **`"error"`** |
| helper | **拒跑**（不进入 metric 计算） |
| `final_test_refusal` | 视失败原因；`final_test_touched=true` → `true` |
| report | **作废** |
| warnings | 含失败原因（例 `w4_paired_below_minimum`、`w4_final_test_touched_true_report_void`） |

### 4.2 4-fold / 3-fold 退化路径

| 场景 | 行为 |
|---|---|
| `require_w4_manifest=True`（默认） + W4 manifest fail | helper 拒跑；`overall_status="error"` |
| `require_w4_manifest=False` + W4 manifest fail | helper 仅跑 3-fold；`fold_count=3`；warning `degraded_to_3fold_w4_unavailable` |
| `require_w4_manifest=True` + W4 manifest pass | 4-fold；`fold_count=4` |
| 缺 W4 manifest 文件 + `require_w4_manifest=True` | helper 拒跑 |

→ 默认强制 4-fold；只有 caller 明确接受降级才能跑 3-fold。

---

## 5. windows

| window | date range | 来源 |
|---|---|---|
| **W1** | **2023-01-03 → 2023-08-31** | main DB / existing replay；paired ~ 130 |
| **W2** | **2023-09-01 → 2024-02-29** | main DB / existing replay；paired ~ 100（含 2024-02 shock 月） |
| **W3** | **2024-03-01 → 2024-08-02** | main DB / existing replay；paired ~ 56 |
| **W4** | **2024-08-03 → 2025-12-31** | W4 replay output dir（`logs/historical_training/three_system_w4_2024_08_2025_12/`，353 paired，本地 untracked） |
| **final test** | **2026-01-01 onward** | **forbidden**（永久封禁） |

合计 v1 paired ≈ **286**（W1+W2+W3）；4-fold 启用后总 paired ≈ **639**。

---

## 6. 6 metrics

| # | metric | 用途 |
|---|---|---|
| 1 | `accuracy_delta_vs_baseline` | candidate 触发后整体 acc 提升幅度；防整体精度反降 |
| 2 | `false_exclusion_rate` | candidate 触发样本中 `direction_correct=1` 比率；控制误杀；与 Step 2G-7C hard gate 对齐 |
| 3 | `net_benefit` | counterfactual：剔除触发样本后 base_acc 提升；与 Step 2G-7C hard gate 对齐 |
| 4 | `survival_case_preservation` | survival case（触发但预测正确）能在 sidecar 中明确呈现的比率 |
| 5 | `cross_window_variance` | candidate 在所有 held-out window 上 fer 的极差 |
| 6 | `minimum_window_sample_size` | per-fold held-out window 触发的 paired 样本数最小值 |

每个 metric 在 design §7 已锁定 formula / denominator / edge case。

---

## 7. 7 gates

| metric | gate threshold | 范围 |
|---|---|---|
| `minimum_window_sample_size` | **`>= 20`** | per-fold held-out window |
| `false_exclusion_rate` | **`<= 0.10`** | per-fold held-out window，**worst-window 决胜** |
| `net_benefit` | **`>= +0.05`** | per-fold held-out window |
| `cross_window_variance` | **`<= 0.10`** | 跨 fold 极差 |
| **`no_single_window_collapse`** | 任一 window **不能** `fer >= 0.20` OR `nb <= 0` | 兜底守卫 |
| `survival_case_preservation` | **`>= 0.80`** | per-fold held-out window |
| `accuracy_delta_vs_baseline` | **`>= +0.02`** | per-fold held-out window |

### 7.1 阈值不可调

- helper API **不**暴露 threshold 参数
- 阈值变更必须经 launch review；不在 helper 层
- 不读 2026 数据调阈值（启动 gate + record-level cutoff 双重 stop）
- 与 Step 3R-4 §6 / 3R-4 checkpoint §6 完全对齐

---

## 8. worst-window rule

| 规则 | 实施 |
|---|---|
| **pooled pass 但 worst-window fail = overall fail** | helper 必须仅依据 worst-window 决策；pooled metrics 写入 `pooled_metrics` 字段但**不**进 `gate_status` |
| **worst-window 选择优先级** | 1) FER `> 0.10` <br> 2) NB `< +0.05` <br> 3) sample `< 20` <br> 4) survival `< 0.80` <br> 5) 否则 fer 最大者 |
| **不允许只看 pooled result** | helper 必须 emit `per_window_metrics` 全 6 项 |
| **emit 字段** | `worst_window` / `worst_window_metrics` / `worst_window_reason` |

---

## 9. output schema

```json
{
  "schema_version": "regime_validation_report.v1",
  "candidate_name": "...",
  "candidate_kind": "smoothing | formula | label_assignment",
  "fold_count": 4,
  "windows": {
    "W1": {"start": "2023-01-03", "end": "2023-08-31", "paired": 130},
    "W2": {"start": "2023-09-01", "end": "2024-02-29", "paired": 100},
    "W3": {"start": "2024-03-01", "end": "2024-08-02", "paired": 56},
    "W4": {"start": "2024-08-03", "end": "2025-12-31", "paired": 353}
  },
  "per_window_metrics": {"W1": {...}, "W2": {...}, "W3": {...}, "W4": {...}},
  "pooled_metrics": {...},
  "worst_window": "...",
  "worst_window_metrics": {...},
  "worst_window_reason": "...",
  "cross_window_variance": {...},
  "leave_one_window_out": {
    "F1_train_W2_W3_W4_validate_W1": "pass|fail",
    "F2_train_W1_W3_W4_validate_W2": "pass|fail",
    "F3_train_W1_W2_W4_validate_W3": "pass|fail",
    "F4_train_W1_W2_W3_validate_W4": "pass|fail"
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
  "overall_status": "pass|fail|error",
  "fail_reason": "...",
  "final_test_refusal": false,
  "data_cutoff_used": "2025-12-31",
  "warnings": []
}
```

### 9.1 14 必备字段

| 字段 | 不变量 |
|---|---|
| `schema_version` | 总是 `"regime_validation_report.v1"` |
| `candidate_name` | string；caller 必填 |
| `candidate_kind` | enum；caller 必填 |
| `fold_count` | `3` 或 `4`（整数） |
| `windows` | W1/W2/W3 必备；4-fold 时 W4 也必备 |
| `per_window_metrics` | 每个 held-out window 6 metric 全 present |
| `worst_window` | string |
| `worst_window_metrics` | dict；6 metric |
| `cross_window_variance` | dict |
| `leave_one_window_out` | 4 fold 时 4 entry |
| `gate_status` | 7 项（6 metric + `no_single_window_collapse`） |
| `overall_status` | `"pass"` / `"fail"` / `"error"`（**不允许 `"partial"`**） |
| `final_test_refusal` | bool；`true` → 报告作废 |
| `data_cutoff_used` | `<= 2025-12-31`；硬不变量 |

`warnings` 是 list of string，可为空。

---

## 10. 与 Step 3R-2 的关系

| 维度 | Step 3R-2 helper（已 merge `e2a681b` / `db7618b`） | Step 3R-4.1 validation helper（本设计） |
|---|---|---|
| 功能层 | **数据层**（生成 `regime_labels.v1`） | **评分层**（基于 records + protocol 输出 `regime_validation_report.v1`） |
| 是否优化 thresholds | ❌ 否 | ❌ 否（应用 protocol） |
| 是否宣称 candidate pass / fail | ❌ 否（labels 不决定 pass/fail） | ✅ 是（`overall_status`） |
| pass / fail 来源 | n/a | metrics / gates |
| 关系 | 3R-2 提供 labels；本 helper **可选**读取 labels 作为 grouping diagnostics（不参与 gate 决策） |

→ **labels 不决定 pass/fail；pass/fail 只能来自 metrics / gates**。

---

## 11. 与 hard / required 的关系

| 维度 | 本 helper |
|---|---|
| **report `overall_status="pass"` 是否自动启 `hard`** | **❌ 否** |
| **是否自动改 `required`**（04 / 05 / 07） | **❌ 否** |
| **是否让 Gate 5 / Gate 6 自动 pass** | **❌ 否** |
| **是否驱动 `_PROTECTION_LAYER_CONNECTED` 翻 True** | **❌ 否** |
| **是否驱动 `hard_exclusion_allowed` / `primary_blocker` 派生** | **❌ 否** |
| **是否写 `simulated_trade` / `no_trade` / `confidence_system`** | **❌ 否** |
| **report `overall_status="pass"` 唯一允许的下游** | **进入下一步 design review** |

→ helper 的全部用途是产出**结构化判断**；production wiring 永远是
独立 step，且必须经 launch review。

---

## 12. 允许下一步

| # | 候选 | 状态 |
|---|---|---|
| 1 | **Step 3R-4.2 read-only validation helper implementation** | **✅ 允许**（在本 checkpoint 进入 main 后启动）；新增 `services/regime_validation_helper.py` + tests + W4 manifest gate；纯 read-only；与 3R-2 helper 同等 isolation |
| 2 | 用 helper 复现 R4 fail | **✅ 允许**（3R-4.2 实施后；即在 helper 实施时第一个 acceptance test） |
| 3 | **Step 3R-3 smoothing candidate design** | **❌ 仍不允许**（必须先过 3R-4.2 实施 + 实测 R4 fail 复现） |
| 4 | **Step 3R-5 formula design** | **❌ 仍不允许**（必须先过 3R-3 + 3R-4.2 helper 在 4-fold 协议下出报告） |
| 5 | **Step 3R-6 read-only simulator** | **❌ 仍不允许**（必须先过 3R-5） |
| 6 | helper pass 自动启 hard / required / Gate 5 / Gate 6 | **❌ 永远不允许**（与 §11 一致） |

---

## 13. 禁止事项

| # | 禁止 | 理由 |
|---|---|---|
| 1 | **不写 DB** | helper 是纯函数；输入 records，输出 dict |
| 2 | **不读 DB**（除非未来 wrapper 明确提供 records） | helper 本身不连 DB |
| 3 | **不跑 replay** | 输入是已完成 records |
| 4 | **不接 trading**（`longbridge` / `broker` / `paper_trade`） | 永不；静态 import 锁定（实施时） |
| 5 | **不启 hard / forced / anti_false_exclusion_triggered** | 与 v1 / 3R-0 / 3R-4 一致 |
| 6 | **不改 04 / 05 / 07 required** | Step 2G 全程边界 |
| 7 | **不触碰 2026** | 启动 gate + record-level cutoff 双重 hard stop |
| 8 | **不把 pass 当 production permission** | report `pass` 仅允许进入 design review |
| 9 | **不让 `_PROTECTION_LAYER_CONNECTED` 翻 True** | 与 v1 / 3R-0 / 3R-4 一致 |
| 10 | **不让 `hard_gate_status.protection_layer_connected` 自动 pass** | 同上 |
| 11 | **不改 `hard_exclusion_allowed` / `primary_blocker` 派生** | 同上 |
| 12 | **不改 3R-4 protocol thresholds** | 阈值调整必须经 launch review |
| 13 | **不改 3R-2 helper 行为** | helper 已 merge；本 helper 仅 read-only 调用 |
| 14 | **不让 helper API 暴露 threshold 参数** | 阈值不可调 |
| 15 | **不优化 / 学习 thresholds** | 与 §7.1 一致 |
| 16 | **不读 record 中 outcome 在 candidate decision 时已知的字段做 future leak** | anti-lookahead |
| 17 | **不让 W4 输出 commit 进 main** | 与 8D.4 §6.3 一致 |
| 18 | **不接 yfinance / requests / 任何网络** | 同 §3 |
| 19 | **不触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` / `avgo_agent.db.backup_*`** | 历史防护 |

---

## 14. 下一步建议

按推荐优先级：

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **commit 本 checkpoint** | 把 §1-15 4-fold helper 设计状态固化到 main | **本轮 / 下一轮** |
| 2 | **Step 3R-4.2 read-only validation helper implementation** | 新增 `services/regime_validation_helper.py` + tests + W4 manifest gate；纯 read-only；与 3R-2 helper 同等 isolation；首个 4-fold 动代码步 | **高**（commit 本 checkpoint 后立刻启动） |
| 3 | **用 helper 复现 R4 fail** | 在 3R-4.2 实施时作为第一个 acceptance test：用 R4 当前候选（fer=0.3235 / nb=+0.0219）跑 helper，期望 `overall_status="fail"` | 中（与 3R-4.2 实施合并） |
| 4 | **Step 3R-3 smoothing candidate design** | 仅在 3R-4.2 helper 实施 + R4 fail 复现 后启动 | 中 |
| 5 | **不推荐**直接 3R-3 / 3R-5 / 3R-6 | 必须先过 3R-4.2 + 复现 | **❌** |
| 6 | **不推荐**让 helper 读 / 写 DB / 接网络 / trading | 与 §13 一致 | **❌** |
| 7 | **不推荐**让 `overall_status="pass"` 自动启 hard / Gate 5 / Gate 6 | 与 §11 一致 | **❌** |
| 8 | **不推荐** 升级 04 required | Step 2G 全程边界 | **❌** |
| 9 | **不推荐** 触碰 2026 final test range | 永久封禁 | **❌** |
| 10 | **不推荐** R4 hard implementation | 三重 NO-GO 已锁定 | **❌** |
| 11 | **不推荐**让 `_PROTECTION_LAYER_CONNECTED` 翻 True | 与 v1 / 3R-0 / 3R-4 一致 | **❌** |
| 12 | **不推荐** 直接 formula / simulator | 必须先过 3R-4.2 + 3R-3 | **❌** |

**关键判断**：
- 顺序 = 本 checkpoint → **3R-4.2 helper 实施**（首个动代码步）→
  用 helper 复现 R4 fail → 3R-3 smoothing design → 3R-5 formula design
  → 3R-6 simulator → 3R-7 sidecar
- Step 3R-4.1 与 Step 3R-2 helper / Step 2G-8D W4 输出**解耦但有依赖**：
  本 helper 在 4-fold 模式下**强制依赖** W4 manifest 通过 §4 gate

---

## 15. 严守边界

本文是**纯 checkpoint markdown**：

- ❌ 没改任何代码（`services/*` / `ui/*` / `tests/*` / `scripts/*` 全部未触碰）
- ❌ 没改 DB schema
- ❌ 没写 DB
- ❌ 没运行 replay
- ❌ 没改 `run_predict` / `predict.py` / `scanner.py` /
  `prediction_store.py` / `app.py`
- ❌ 没改 `services/regime_features_builder.py` /
  `services/regime_labels_builder.py` /
  `services/regime_diagnostics_dashboard.py` /
  `services/anti_false_exclusion_dashboard.py` /
  `services/soft_metadata_simulator.py` /
  `services/protection_layer_diagnostics.py` /
  `services/historical_replay_training.py` /
  `services/three_system_replay_audit.py` /
  `services/replay_record_wiring.py` /
  `services/projection_three_systems_renderer.py` /
  `services/outcome_capture.py` /
  `ui/protection_layer_diagnostics_renderer.py` / 任何 ui 模块 /
  任何 builder
- ❌ 没改 `scripts/run_1005_three_system_replay.py` 或任何 replay 脚本
- ❌ 没改 04 / 05 / 07 任何 required 字段
- ❌ 没启用 `hard` / `forced_exclusion` /
  `anti_false_exclusion_triggered`
- ❌ 没接 `yfinance` / `requests` / 任何网络
- ❌ 没接 trading API / `longbridge` / `broker` / `paper_trade`
- ❌ 没让 `_PROTECTION_LAYER_CONNECTED` 翻 True
- ❌ 没让 `hard_gate_status.protection_layer_connected` 自动 pass
- ❌ 没改 `hard_exclusion_allowed` / `primary_blocker` 派生
- ❌ 没触碰 2026-01-01 之后 final test range
- ❌ 没改 Step 3R-4 protocol thresholds（6 metric / 7 gate / 10 no-go）
- ❌ 没改 Step 3R-2 helper 行为
- ❌ 没改 Step 2G-8D design / checkpoint / audit / 8D.1A patch / 8D.1A
  checkpoint / 8D.2 smoke / 8D.2 checkpoint / 8D.3 / 8D.4
- ❌ 没改 Step 3R-4.1 design（已 merge 在 commit `8e27254`，本 checkpoint 不动）
- ❌ 没把 W4 输出 commit 进 main
- ❌ 没把 smoke 输出 commit 进 main
- ❌ 没运行 `pytest`（本轮纯文档；测试基线维持 commit `8e27254` 时
  的 2689 / 0 failed / 10 skipped）
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` /
  `avgo_agent.db.backup_*`
- ✅ 只新增 1 份 markdown checkpoint 文档（本文件）
