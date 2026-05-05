# Step 3R-4.2 — Regime Validation Helper Checkpoint

> **状态固化文档（regime validation helper checkpoint），不实现，不改代码，不写 DB，不运行 replay。**
> 本文档**冻结** Step 3R-4.2 helper（commit `c669c2f`）的：公共 API、
> `regime_validation_report.v1` schema 14 项必备字段、W4 manifest 启动
> gate 8 项、6 metric / 7 gate threshold、worst-window 决胜规则、LOWO
> 折叠、R4-like fail acceptance、33 focused tests + 2722 全量 pytest
> 基线、与 Step 3R-2 helper / hard / required / 2026 final test 边界。
>
> 本轮**不动任何代码**：不改 `predict.py` / `run_predict` /
> `scanner.py` / `prediction_store.py` / `app.py` / 任何 `ui/*` /
> `services/*`（含 `services/regime_validation_helper.py` /
> `services/regime_labels_builder.py`）/ `scripts/*` / 任何 builder /
> DB schema / 任何 test 中的任何一处。
>
> **本文不实施 candidate / smoothing / formula、不跑 replay、不写 DB、
> 不接 trading API**；只在 markdown 层固化 helper 状态，作为后续 3R-3
> smoothing design / 3R-4.3 real replay adapter 的强制 gate。

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
- **Step 2G-8D** extend replay coverage 系列已收官（commits `170617c`
  ... `4bdd782`）；W4 paired_outcomes=353 / `final_test_touched=false`
- **Step 3R-4.1** 4-fold validation helper design + checkpoint 已完成
  并进入 main（commits `8e27254` / `295ccdd`）
- **Step 3R-4.2** read-only validation helper 已完成并进入 main
  （commit `c669c2f`）—— Step 3R 系列**评分层第一个动代码步**
- 本 checkpoint **固定**：
  - `build_regime_validation_report(...)` 公共 API + 7 参数 + 12 项 read-only 约束
  - `regime_validation_report.v1` schema 14 项必备字段（含 3 值 `overall_status`，无 `partial`）
  - W4 manifest 启动 gate 8 项
  - 6 metric 计算公式 + 7 gate threshold（与 3R-4 protocol 完全对齐）
  - worst-window 决胜 5 级优先级 + LOWO 4 fold
  - R4-like fail acceptance（实测 worst_window=W2）
  - 33 focused tests + 2722 全量 pytest 基线
  - 与 Step 3R-2 / hard / required / 2026 final test 边界
- **Step 3R-3 smoothing candidate design 仍未启动**：本 checkpoint 是
  3R-3 之前的强制 gate

---

## 2. 当前 main 状态

- main 最新 commit：**`c669c2f`**
- commit message：`feat(diagnostics): add regime validation helper`
- 上游：`origin/main` 已同步
- 测试基线：**2722 passed / 0 failed / 10 skipped / 26 warnings /
  94 subtests**（与 commit `c669c2f` 实测一致；Step 2G-8D.1A 终点 2689
  → Step 3R-4.2 终点 2722，+33 净增；2689 基线零回归）

本步骤新增 / 修改文件（已 merge 到 main）：

| 路径 | 类型 | 说明 |
|---|---|---|
| `services/regime_validation_helper.py` | 新增 | pure read-only helper（619 行）；W4 manifest gate + 6 metric + 7 gate + worst-window + LOWO + `regime_validation_report.v1` 输出 |
| `tests/test_regime_validation_helper.py` | 新增 | 33 focused tests（schema / manifest gate / metrics / overall_status / worst-window / safety / isolation / acceptance：R4-like fail + pooled-pass-but-worst-fail）|
| `tasks/step_1_contract_pipeline_summary.md` | 修改 | 新增 §38 |

本 checkpoint 文档（即本文件）尚未 commit；本轮只写文档、**不**
commit / push。

| 项 | 是否触碰 |
|---|---|
| 改代码 | ❌ 否 |
| 写 DB | ❌ 否 |
| 跑 replay | ❌ 否 |
| 改 services/regime_validation_helper.py | ❌ 否（已 merge 在 commit `c669c2f`） |
| 改 services/regime_labels_builder.py | ❌ 否 |
| 改 DB schema | ❌ 否 |
| 接 yfinance / 网络 | ❌ 否 |
| 接 trading API | ❌ 否 |
| 触碰 2026 final test | ❌ 否 |

---

## 3. Public API

```python
build_regime_validation_report(
    records,
    *,
    candidate_name: str,
    candidate_kind: str = "label_assignment",
    windows: dict | None = None,
    final_test_cutoff: str = "2026-01-01",
    require_w4_manifest: bool = True,
    w4_manifest_path: str | None = None,
) -> dict
```

| 项 | 值 |
|---|---|
| 类型 | **pure read-only helper** |
| 是否读 DB | ❌ 否 |
| 是否写 DB | ❌ 否 |
| 是否跑 replay | ❌ 否 |
| 是否改 input records | ❌ 否（深拷贝测试锁定） |
| 是否接网络 | ❌ 否（`ast.walk` 锁定） |
| 是否接 trading API | ❌ 否（`ast.walk` 锁定） |
| 是否 import `prediction_store` / `scanner` / `predict` / `yfinance` / `requests` / `streamlit` / `longbridge` / `broker` / `paper_trade` / `sqlite3` / 等 16 项 | ❌ 否（`ast.walk` 锁定） |
| 是否暴露 threshold 参数 | ❌ 否（API 不允许 override 阈值） |
| 是否优化 / 学习 thresholds | ❌ 否 |
| 是否触碰 2026 | ❌ 否（manifest gate + record-level cutoff 双重 hard stop） |
| 是否宣称 production permission | ❌ 否（report `pass` 仅供 design review） |

---

## 4. `regime_validation_report.v1` schema

helper 输出 14 项必备字段：

| 字段 | 不变量 |
|---|---|
| `schema_version` | 总是 `"regime_validation_report.v1"` |
| `candidate_name` | string；caller 必填 |
| `candidate_kind` | enum；caller 提供（默认 `"label_assignment"`） |
| `fold_count` | `3` 或 `4`（整数） |
| `windows` | W1/W2/W3/W4 entry；含 `start` / `end` / `paired` |
| `per_window_metrics` | 每个 held-out window 6 metric 全 present |
| `pooled_metrics` | dict；仅参考，不进 gate |
| `worst_window` | string；W1/W2/W3/W4 中的一个 |
| `worst_window_metrics` | dict；6 metric |
| `cross_window_variance` | dict；至少含 `false_exclusion_rate` 字段 |
| `leave_one_window_out` | 4 fold 时 4 entry（3 fold 时 3 entry） |
| `gate_status` | 7 项（6 metric + `no_single_window_collapse`） |
| `overall_status` | **`"pass"` / `"fail"` / `"error"`**（**不允许 `"partial"`**） |
| `final_test_refusal` | bool；`true` → 报告作废 |
| `data_cutoff_used` | `"2026-01-01"`（≤ 2025-12-31 硬不变量） |

`warnings` 字段也总 present（list of string；可空）。

### 4.1 schema 不变量

| 不变量 | 说明 |
|---|---|
| `overall_status` 三值 | helper 不输出 `"partial"`；测试 `OutputSchemaTests::test_overall_status_only_three_values` 锁定 |
| 14 字段全 present | 测试 `OutputSchemaTests::test_output_keys_present` 锁定 |
| `data_cutoff_used` 硬不变量 | 测试 `SafetyTests::test_data_cutoff_used_is_2026_01_01` 锁定 |

---

## 5. W4 manifest gate

启动前**必须**通过 8 项检查：

| # | 检查 | 期望值 |
|---|---|---|
| 1 | manifest path 必须可读 | 文件存在；测试 `test_missing_path_returns_error_when_required` |
| 2 | JSON parse 成功 | helper 在 parse 异常时返回 `error`（`OSError` / `JSONDecodeError`） |
| 3 | `schema_version` | `"w4_replay_manifest.v1"`；测试 `test_schema_version_mismatch_returns_error` |
| 4 | **`final_test_touched`** | **`false`**；测试 `test_final_test_touched_true_returns_error` |
| 5 | `status` | `"ok"`；测试 `test_status_not_ok_returns_error` |
| 6 | `paired_outcomes` | `>= 20`；测试 `test_paired_below_minimum_returns_error` |
| 7 | `replay_window.start / end` | `"2024-08-03"` / `"2025-12-31"`；测试 `test_wrong_w4_start_returns_error` / `test_wrong_w4_end_returns_error` |
| 8 | `final_test_cutoff` | `"2026-01-01"`；测试 `test_cutoff_mismatch_returns_error` |

### 5.1 任一失败的统一处理

| 字段 | 值 |
|---|---|
| `overall_status` | **`"error"`** |
| `final_test_refusal` | **`true`**（仅当 `final_test_touched=true`）；其它失败为 `false` |
| helper | **拒跑**（不进入 metric 计算） |
| `warnings` | 含具体失败原因（例 `w4_paired_below_minimum` / `w4_final_test_touched_true_report_void`） |

`require_w4_manifest=False`（caller 显式接受降级）→ 跳过 gate + emit
`w4_manifest_not_required` informational warning。

---

## 6. 6 metrics

| # | metric | 用途 |
|---|---|---|
| 1 | `accuracy_delta_vs_baseline` | candidate 触发后整体 acc 提升幅度；防整体精度反降 |
| 2 | `false_exclusion_rate` | candidate 触发样本中 `prediction_correct=True` 比率；控制误杀；与 Step 2G-7C hard gate 对齐 |
| 3 | `net_benefit` | counterfactual：剔除触发样本后整体 acc 提升幅度 |
| 4 | `survival_case_preservation` | survival case（触发**且**预测正确）能在 sidecar 中明确呈现的比率；vacuous 1.0 当无 survival cases |
| 5 | `cross_window_variance` | candidate 在所有 held-out window 上 fer 的极差（max − min） |
| 6 | `minimum_window_sample_size` | per-fold held-out window 中 candidate 触发的 paired 样本数最小值 |

formula / denominator / edge case 详见 commit `c669c2f` 的
`services/regime_validation_helper.py` `_per_window_compute` /
`_cross_window_variance` / `_select_worst_window`。

---

## 7. 7 gate thresholds

固定阈值（与 Step 3R-4 §6 / 3R-4 checkpoint §6 完全对齐；helper 不
暴露阈值参数；阈值变更必须经 launch review）：

| metric | gate threshold | 范围 |
|---|---|---|
| `minimum_window_sample_size` | **`>= 20`** | per-fold held-out window |
| `false_exclusion_rate` | **`<= 0.10`** | per-fold held-out window，**worst-window 决胜** |
| `net_benefit` | **`>= +0.05`** | per-fold held-out window |
| `cross_window_variance` | **`<= 0.10`** | 跨 fold 极差 |
| **`no_single_window_collapse`** | 任一 window **不能** `fer >= 0.20` OR `nb <= 0` | 兜底守卫 |
| `survival_case_preservation` | **`>= 0.80`** | per-fold held-out window |
| `accuracy_delta_vs_baseline` | **`>= +0.02`** | per-fold held-out window |

---

## 8. worst-window / LOWO

### 8.1 worst-window 决胜（5 级优先级）

| 优先级 | 选择规则 |
|---|---|
| 1 | 任一 window `fer > 0.10` → 该 fer 最大者为 worst |
| 2 | 任一 window `nb < +0.05` → 该 nb 最小者为 worst |
| 3 | 任一 window `paired < 20` → 该 paired 最小者为 worst |
| 4 | 任一 window `survival_preservation < 0.80` → 最低者为 worst |
| 5 | 否则 fer 最高者；全无 metric → lexical 第一窗 |

### 8.2 LOWO 折叠

helper 输出 `leave_one_window_out` dict，4-fold 时 4 entry，例：

```
{
  "F_train_W2_W3_W4_validate_W1": "pass|fail",
  "F_train_W1_W3_W4_validate_W2": "pass|fail",
  "F_train_W1_W2_W4_validate_W3": "pass|fail",
  "F_train_W1_W2_W3_validate_W4": "pass|fail"
}
```

每个 fold 的 pass/fail 直接基于该 held-out window 的 per_window_metrics
是否满足 7 gate（与 overall worst-window 决胜规则一致）。

### 8.3 强制规则

| 规则 | 实施 |
|---|---|
| **pooled pass 但 worst-window fail = overall fail** | 测试 `AcceptanceTests::test_pooled_pass_but_worst_window_fail` 锁定 |
| **不允许只看 pooled result** | helper 必须 emit `per_window_metrics` 全 6 项；`gate_status` 不依据 pooled |

---

## 9. R4 fail acceptance

| 字段 | 实测值 |
|---|---|
| fixture | `_make_r4_like_records()`（`tests/test_regime_validation_helper.py`） |
| W1 FER | **≈ 0.20**（25 triggered，5 correct） |
| W2 FER | **≈ 0.40**（25 triggered，10 correct）— 触发 `no_single_window_collapse`（>= 0.20） |
| W3 FER | **≈ 0.16**（25 triggered，4 correct） |
| W4 FER | **≈ 0.32**（25 triggered，8 correct） |
| `overall_status` | **`"fail"`** |
| `worst_window` | **`"W2"`**（fer 最高） |
| failure gates | ⊇ `{false_exclusion_rate, no_single_window_collapse, cross_window_variance}` |

### 9.1 含义

| 含义 | 是否 |
|---|---|
| **证明 helper 能阻止旧 R4 在 4-fold 下误通过** | **✅ 是**（acceptance test `test_r4_like_fixture_fails_4fold_validation`） |
| **证明 worst-window 决胜规则有效** | **✅ 是**（worst_window=W2 与 fer 最高者一致） |
| **证明 R4 在生产中应该被排除** | **❌ 否**（fixture 是合成数据；真实 R4 跨窗口数据需 3R-4.3 real adapter） |
| **构成 production decision** | **❌ 否**（report 仅供 design review；wiring 必须经 launch review） |
| **可以据此调阈值** | **❌ 否**（与 §7 / §11 一致） |

---

## 10. 测试覆盖

### 10.1 测试结果（commit `c669c2f` 实测）

| 命令 | 结果 |
|---|---|
| `pytest tests/test_regime_validation_helper.py -q` | **33 passed** |
| `pytest tests/test_regime_labels_builder.py -q` | **38 passed**（零回归） |
| `pytest -q`（全量） | **2722 passed / 10 skipped / 0 failed / 26 warnings / 94 subtests** |

测试基线累积：**Step 2G-8D.1A 终点 2689 → Step 3R-4.2 终点 2722**
（+33 净增；2689 基线零回归）。

### 10.2 测试矩阵（33 cases）

| 测试类 | 数量 | 覆盖点 |
|---|---|---|
| `OutputSchemaTests` | 4 | 14 字段全 present / 默认 W1-W4 / fold_count=4 / overall_status 三值约束 |
| `W4ManifestGateTests` | 10 | valid manifest / final_test_touched=true / wrong start / wrong end / paired<20 / status≠ok / schema mismatch / cutoff mismatch / 缺 path / require=False informational |
| `MetricsFormulaTests` | 6 | FER / NB / survival / variance / collapse / sample size 边界 |
| `OverallStatusTests` | 4 | gate fail → fail / 全 pass → pass / 无 partial / worst-window=W2 |
| `SafetyTests` | 5 | 2026 refusal / cutoff boundary / 缺字段 skip+warning / input immutability / `data_cutoff_used` 锁定 |
| `IsolationTests` | 2 | `ast.walk` 锁定 16 项 forbidden module；字符串锁定无 hard / forced / `_PROTECTION_LAYER_CONNECTED` / `simulated_trade` / `no_trade` / `final_direction` / `final_projection` |
| `AcceptanceTests` | 2 | R4-like fixture fail + pooled-pass-but-worst-fail |

### 10.3 关键覆盖点

- ✅ **schema** — `OutputSchemaTests` × 4
- ✅ **default windows** — `test_default_windows_are_w1_w4`
- ✅ **W4 manifest gate** — `W4ManifestGateTests` × 10
- ✅ **metrics formula** — `MetricsFormulaTests` × 6
- ✅ **gates** — `MetricsFormulaTests` + `OverallStatusTests`
- ✅ **worst-window** — `test_worst_window_priority_picks_highest_fer`
- ✅ **overall status** — `OverallStatusTests` × 4
- ✅ **final_test records skip / refusal** — `test_record_with_2026_date_triggers_refusal` / `test_record_at_cutoff_boundary_refused`
- ✅ **input immutability** — `test_input_records_not_mutated`
- ✅ **no forbidden imports** — `IsolationTests::test_module_does_not_import_forbidden`
- ✅ **R4-like fail** — `test_r4_like_fixture_fails_4fold_validation`
- ✅ **pooled pass but worst-window fail** — `test_pooled_pass_but_worst_window_fail`

---

## 11. 与 Step 3R-2 的关系

| 维度 | Step 3R-2 helper（已 merge `e2a681b` / `db7618b`） | Step 3R-4.2 helper（本步骤） |
|---|---|---|
| 功能层 | **数据层**（生成 `regime_labels.v1`） | **评分层**（基于 records + protocol 输出 `regime_validation_report.v1`） |
| 输入 | DataFrame（OHLC + peer + market） | record list（已完成 replay / review） |
| 是否优化 thresholds | ❌ 否 | ❌ 否（应用 protocol） |
| 是否宣称 candidate pass / fail | ❌ 否（labels 不决定 pass/fail） | ✅ 是（`overall_status`） |
| pass / fail 来源 | n/a | metrics / gates |
| 关系 | 3R-2 提供 labels；本 helper **可选**读取 labels 作为 grouping diagnostics（不参与 gate 决策） |
| 是否依赖对方 | 本 helper **不**强制依赖 3R-2；labels 字段 optional |

→ **labels 不决定 pass/fail；pass/fail 只能来自 metrics / gates**。

---

## 12. 与 hard / required 的关系

| 维度 | 本 helper |
|---|---|
| **report `overall_status="pass"` 是否自动启 `hard`** | **❌ 否** |
| **是否自动改 `required`**（04 / 05 / 07） | **❌ 否** |
| **report `overall_status="fail"` 是否自动改主链** | **❌ 否** |
| **是否让 Gate 5 / Gate 6 自动 pass** | **❌ 否** |
| **是否驱动 `_PROTECTION_LAYER_CONNECTED` 翻 True** | **❌ 否**（字符串静态测试锁定） |
| **是否驱动 `hard_exclusion_allowed` / `primary_blocker` 派生** | **❌ 否**（字符串静态测试锁定） |
| **是否写 `simulated_trade` / `no_trade` / `final_direction` / `final_projection`** | **❌ 否**（字符串静态测试锁定） |
| **report `overall_status="pass"` 唯一允许的下游** | **进入下一步 design review** |

→ helper 的全部用途是产出**结构化判断**；production wiring 永远是
独立 step，且必须经 launch review。

---

## 13. 当前限制

| # | 限制 | 解封步骤 |
|---|---|---|
| 1 | **helper 还没接真实 W4 jsonl parser** | Step 3R-4.3（可选；real replay record adapter design / implementation） |
| 2 | **当前 R4 fail 是 fixture acceptance，不是 full W4 production report** | Step 3R-4.3 或独立 wrapper script 把 W4 jsonl + W1/W2/W3 数据组装成 `records` 输入 |
| 3 | **还没有 dashboard UI** | Step 3R-7（仅 conditional；与 sidecar integration 配对） |
| 4 | **还没有 smoothing candidate** | Step 3R-3 continuous smoothing candidate design（纯 markdown 先行） |
| 5 | **还没有 formula** | Step 3R-5（必须先过 3R-3 + 3R-4.3 实测） |
| 6 | **还没有 simulator** | Step 3R-6（必须先过 3R-5 design） |
| 7 | **labels 未接入 helper diagnostics** | 可选扩展；optional record 字段已 reserve |

---

## 14. 下一步建议

按推荐优先级：

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **commit 本 checkpoint** | 把 §1-15 helper 实施状态固化到 main | **本轮 / 下一轮** |
| 2 | **Step 3R-3 continuous smoothing candidate design** | 用 logistic / kernel / spline 替代 4×4 lookup；read-only candidate design；纯 markdown 先行；产出 candidate 后通过 3R-4.2 helper 出报告 | **高**（commit 本 checkpoint 后即可启动） |
| 3 | **Step 3R-4.3 real replay record adapter design / implementation** | 可选；把现有 W1/W2/W3 + W4 jsonl 组装成 helper 接受的 record list；纯 wrapper / adapter；不改 services/regime_validation_helper.py | 中（与 3R-3 解耦可并行） |
| 4 | **不推荐**直接 Step 3R-5 formula design | 必须先过 3R-3 candidate + 3R-4.2 helper 在 4-fold 协议下出报告 | **❌** |
| 5 | **不推荐** Step 3R-6 read-only simulator | 必须先过 3R-5 design | **❌** |
| 6 | **不推荐**让 helper 读 / 写 DB / 接网络 / trading | 与 §3 一致 | **❌** |
| 7 | **不推荐**让 `overall_status="pass"` 自动启 hard / Gate 5 / Gate 6 | 与 §12 一致 | **❌** |
| 8 | **不推荐** 升级 04 required | Step 2G 全程边界 | **❌** |
| 9 | **不推荐** 触碰 2026 final test range | 永久封禁；manifest gate + record-level cutoff 双重 hard stop | **❌** |
| 10 | **不推荐** R4 hard implementation | 三重 NO-GO 已锁定 | **❌** |
| 11 | **不推荐**让 `_PROTECTION_LAYER_CONNECTED` 翻 True | 与 v1 / 3R-0 / 3R-4 一致 | **❌** |
| 12 | **不推荐** 改 helper threshold 阈值 | 调阈值必须经 launch review | **❌** |

**关键判断**：
- 顺序 = 本 checkpoint → **3R-3 design**（纯 markdown）→ optional
  3R-4.3 adapter → 3R-5 formula → 3R-6 simulator → 3R-7 sidecar
- Step 3R-4.2 与 Step 3R-2 helper / Step 2G-8D W4 输出**解耦但有依赖**：
  helper 在 4-fold 模式下**强制依赖** W4 manifest 通过 §5 gate；helper
  **可选依赖** 3R-2 labels 作为 diagnostics

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
  `services/regime_validation_helper.py`（已 merge 在 commit `c669c2f`） /
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
- ❌ 没改 Step 2G-8D / 8D.1A / 8D.2 / 8D.3 / 8D.4 文档或代码
- ❌ 没改 Step 3R-4.1 design / checkpoint
- ❌ 没改 Step 3R-4.2 helper（已 merge 在 commit `c669c2f`，本 checkpoint 不动）
- ❌ 没把 W4 / smoke 输出 commit 进 main
- ❌ 没运行 `pytest`（本轮纯文档；测试基线维持 commit `c669c2f` 时
  的 2722 / 0 failed / 10 skipped）
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` /
  `avgo_agent.db.backup_*`
- ✅ 只新增 1 份 markdown checkpoint 文档（本文件）
