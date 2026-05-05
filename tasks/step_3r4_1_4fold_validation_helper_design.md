# Step 3R-4.1 — 4-Fold Validation Helper Design

> **设计文档（4-fold validation helper design），不实现，不改代码，不写 DB，不运行 replay。**
> 本文档**冻结** Step 3R-4.1 的：W4 manifest 启动 gate、helper 公共 API、
> 输入 record 最小 schema、6 metric 计算公式、7 gate threshold 落地、
> worst-window 决胜规则、10 no-go rules → `gate_status` 映射、
> `regime_validation_report.v1` 输出 schema、与 Step 3R-2 helper /
> Step 2G-8D W4 输出 / hard / required 边界的衔接关系。
>
> 本轮**不动任何代码**：不改 `predict.py` / `run_predict` /
> `scanner.py` / `prediction_store.py` / `app.py` / 任何 `ui/*` /
> `services/*` / `scripts/*` / 任何 builder / DB schema / 任何 test
> 中的任何一处。
>
> **本文不实现 helper、不跑 replay、不写 DB、不调网络、不接 trading
> API**；只在 markdown 层冻结 helper 设计，给后续 3R-4.2 read-only
> validation helper implementation 提供边界。

---

## 1. 背景

- **Step 3R-4** cross-window validation protocol design + checkpoint
  已完成并进入 main（commits `a58aad4` / `abe3ba2`）—— 设计了 6
  metric、7 gate threshold、10 no-go rule、leave-one-window-out
  3-fold（W4 启用后扩 4-fold）、`regime_validation_report.v1` schema
- **Step 2G-8D** extend replay coverage 系列（design / checkpoint /
  audit / 8D.1A patch + checkpoint / 8D.2 smoke + checkpoint / 8D.3
  full W4 / 8D.4 W4 checkpoint）已收官（commits `170617c` ... `4bdd782`）
- **W4 已生成**：`logs/historical_training/three_system_w4_2024_08_2025_12/`，
  paired_outcomes=353，`final_test_touched=false`，`status=ok`
- 现在**可以从 3-fold 升级为 4-fold**，但 Step 3R-4 design §10 / §13
  / 3R-4 checkpoint §13 强制：在 helper 落地之前**必须**先纯 markdown
  设计（即本文）
- **本文只设计 helper，不实现**；任何 candidate 是否通过 4-fold 仍
  由未来 3R-4.2 helper 跑出 `regime_validation_report.v1` 报告决定

---

## 2. 当前数据窗口

| window | date range | source |
|---|---|---|
| **W1** | **2023-01-03 → 2023-08-31** | main DB / existing replay (`replay_AVGO_*`) — paired ~ 130 |
| **W2** | **2023-09-01 → 2024-02-29** | main DB / existing replay — paired ~ 100（含 2024-02 shock 月） |
| **W3** | **2024-03-01 → 2024-08-02** | main DB / existing replay — paired ~ 56 |
| **W4** | **2024-08-03 → 2025-12-31** | **W4 replay output dir**（`logs/historical_training/three_system_w4_2024_08_2025_12/`，353 paired，本地 untracked） |
| **final test** | **2026-01-01 onward** | **forbidden**（永久封禁） |

合计 v1 paired ≈ **286**（W1+W2+W3）；4-fold 启用后总 paired ≈ **639**
（W1+W2+W3+W4）。

| 项 | 说明 |
|---|---|
| W1 / W2 / W3 来源 | main DB（`avgo_agent.db`）或 existing `three_system_1005/` 输出（取决于 helper wrapper 选择；helper 本身只读 record list） |
| W4 来源 | `three_system_w4_2024_08_2025_12/` jsonl + summary（**本地 untracked**；helper 必须显式接受 W4 records 路径或预先组装的 record list） |
| W4 是否进 main | **❌ 暂不**（与 8D.4 §6.3 一致；本设计不强制改变这一点） |
| 2026 final test | **永久封禁**；G1 + G2 + 本 helper 启动 gate 三重 hard stop |

---

## 3. W4 manifest gate（启动前必读）

**4-fold helper 启动前必须读取 W4 manifest，并验证以下 6 项；任一失败
→ helper 不运行，`overall_status="error"` + `final_test_refusal` 字段
反映原因 + 整份报告作废。**

| # | 检查 | 期望值 | 失败行为 |
|---|---|---|---|
| 1 | `schema_version` | `"w4_replay_manifest.v1"` | helper 拒跑；warning `w4_manifest_schema_mismatch` |
| 2 | `final_test_touched` | **`false`** | helper 拒跑；warning `w4_final_test_touched_true_report_void`；这是**最关键**的 hard gate |
| 3 | `status` | `"ok"` | helper 拒跑；warning `w4_manifest_status_not_ok` |
| 4 | `paired_outcomes` | **`>= 20`**（与 §8 `minimum_window_sample_size ≥ 20` 一致） | helper 拒跑；warning `w4_paired_below_minimum` |
| 5 | `replay_window.start` | `"2024-08-03"` | helper 拒跑；warning `w4_replay_window_start_mismatch` |
| 5b | `replay_window.end` | `"2025-12-31"` | helper 拒跑；warning `w4_replay_window_end_mismatch` |
| 6 | `final_test_cutoff` | `"2026-01-01"` | helper 拒跑；warning `w4_final_test_cutoff_mismatch` |

### 3.1 启动 gate 实现位置

| 位置 | 实现方式 |
|---|---|
| helper 入口 | `_validate_w4_manifest(path)` → 抛 `ValueError` 或返回 `(ok, warnings)` |
| 任一失败 | helper 立即返回 `regime_validation_report.v1`（`overall_status="error"`，`final_test_refusal=True`，`warnings` 含失败原因），**不**继续计算 metrics |
| 4-fold vs 3-fold 切换 | manifest gate 通过 → `fold_count=4`；不通过且 `require_w4_manifest=False` → 退化为 `fold_count=3`（W1+W2+W3 only） |

### 3.2 退化路径

| 场景 | 行为 |
|---|---|
| `require_w4_manifest=True`（默认） + W4 manifest fail | helper 拒跑；`overall_status="error"` |
| `require_w4_manifest=False` + W4 manifest fail | helper 仅跑 3-fold；`fold_count=3`；warning `degraded_to_3fold_w4_unavailable` |
| `require_w4_manifest=True` + W4 manifest pass | 4-fold；`fold_count=4` |
| `require_w4_manifest=True` + 缺 manifest 文件 | helper 拒跑；与第一种等价 |

→ 默认 `require_w4_manifest=True`；只有 caller 明确接受降级才能跑
3-fold（与 3R-4 §3 / §4.1 conditional 4-fold 一致）。

---

## 4. helper 目标

| 输入 | 输出 |
|---|---|
| candidate records（list of dict；已完成 replay / review 的只读 records） | `regime_validation_report.v1`（dict） |

### 4.1 helper 责任

| 责任 | 是否 |
|---|---|
| 按 W1 / W2 / W3 / W4 分窗 records | ✅ 是 |
| 计算 per-window metrics（6 metric 全 6 项） | ✅ 是 |
| 计算 pooled metrics（仅参考，不作 gate） | ✅ 是 |
| 找 worst_window | ✅ 是 |
| 输出 `regime_validation_report.v1` | ✅ 是 |
| 验证 W4 manifest（启动 gate） | ✅ 是 |
| 验证 record 字段完整 | ✅ 是 |
| **跑 replay** | **❌ 否**（输入是已完成 records） |
| **生成 predictions** | **❌ 否** |
| **读 DB**（除非 wrapper 显式提供 records） | **❌ 否**（helper 本身不连 DB） |
| **写 DB** | **❌ 否** |
| **写 main 决策**（`hard` / `forced` / `required`） | **❌ 否** |
| **宣称 production pass** | **❌ 否**（report 只产出 gate 决策；production wiring 不在本 helper 范围） |
| **改 3R-4 protocol thresholds** | **❌ 否**（helper 应用 protocol，不调阈值） |
| **优化 / 学习 thresholds** | **❌ 否** |
| **接 yfinance / 网络 / trading** | **❌ 否** |
| **触碰 2026 final test** | **❌ 否**（启动 gate + record-level cutoff 双重 hard stop） |

---

## 5. public API 草案

```python
def build_regime_validation_report(
    records,
    *,
    candidate_name: str,
    candidate_kind: str = "smoothing | formula | label_assignment",
    windows: dict | None = None,
    final_test_cutoff: str = "2026-01-01",
    require_w4_manifest: bool = True,
    w4_manifest_path: str | None = None,
) -> dict:
    """Build a `regime_validation_report.v1` for one candidate over all windows.

    Pure read-only:
      - does NOT run replay / projection / outcome capture
      - does NOT read DB / network / yfinance
      - does NOT write DB / files (caller writes report if needed)
      - does NOT modify input records
      - does NOT change Step 3R-4 protocol thresholds
    """
```

### 5.1 参数说明

| 参数 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `records` | list[dict] | required | 已完成 replay / review 的 record list；详见 §6 |
| `candidate_name` | str | required | candidate 标识（例：`"r4_baseline"` / `"r4_narrower_v0"` / `"continuous_smoothing_v1"`） |
| `candidate_kind` | enum str | `"smoothing"` | candidate 类型（与 `regime_validation_report.v1` schema 字段一致） |
| `windows` | dict \| None | None → 默认 §2 | 显式 window 边界 override；用于测试或未来扩展 |
| `final_test_cutoff` | str (ISO) | `"2026-01-01"` | hard cutoff；与 8D.1A `--final-test-cutoff` 一致 |
| `require_w4_manifest` | bool | **True** | True = 4-fold 强制；False 允许 3-fold 退化（不推荐） |
| `w4_manifest_path` | str \| None | None | W4 manifest JSON 路径；None + `require_w4_manifest=True` → helper 拒跑 |

### 5.2 边界

- helper **不**负责跑 replay
- helper **不**负责生成 predictions
- helper **不**读 DB（除非未来 wrapper 明确提供 records）
- helper **不**写 DB
- helper **不**改 input records（与 3R-2 `InputImmutabilityTests` 一致）
- helper **不**接网络 / yfinance / trading API
- helper **不**触碰 2026（启动 gate + record-level filter 双重 stop）

---

## 6. 输入 records schema

helper 接受 list of dict，每条 record 表示一次 replay 的 candidate
触发判断 + 实际结果。最小字段：

| 字段 | 类型 | 必备 | 说明 |
|---|---|---|---|
| `analysis_date` | str (ISO) | ✅ | T；用于分窗 |
| `prediction_for_date` | str (ISO) | ✅ | T+1；用于 cutoff 检查 |
| `candidate_triggered` | bool | ✅ | candidate 是否触发（即 candidate "exclusion" 是否会 fire） |
| `prediction_correct` | bool \| None | ✅ | candidate 触发的预测是否方向正确（`direction_correct=1`）；`None` = 未配 outcome |
| `actual_direction` | str | optional | 实际方向（"up"/"down"/"flat"），用于 future debug |
| `baseline_correct` | bool \| None | ✅ | 在 candidate **不**触发的反事实下，baseline 预测是否正确 |
| `exclusion_would_block` | bool | ✅ | candidate 触发后是否会 block 这条预测（fully-bullish exclusion → block 多头） |
| `survival_case` | bool | ✅ | candidate 触发**且**预测正确（即 should-not-have-been-blocked 案例） |
| `label_pos20_regime` | str | optional | 来自 Step 3R-2 helper；用于 optional grouping，不参与 metric |
| `label_avgo_minus_soxx_20d_regime` | str | optional | 同上 |
| `label_peer_momentum_regime` | str | optional | 同上 |
| `label_market_trend_regime` | str | optional | 同上 |
| `label_monthly_context_regime` | str | optional | 同上 |

### 6.1 缺字段处理

| 场景 | 行为 |
|---|---|
| 缺必备字段 | record 整条 skip；warning `record_skipped: missing field <name>` 入 `warnings` list |
| `analysis_date` 不在任一 window 范围 | record 整条 skip；warning `record_skipped: out_of_window` |
| `analysis_date` 或 `prediction_for_date` `>= final_test_cutoff` | **拒读**；helper 整体 abort + `final_test_refusal=True` + `overall_status="error"`；与 3R-4 §3.3 / §4.2 / §9 no-go #4/#8 一致 |
| `prediction_correct=None`（未配 outcome） | record skip in metric 计算；不计入 paired |

### 6.2 不允许

- ❌ helper 不读 record 中任何 `outcome_*` / `direction_correct` 之外的字段做 future leak（与 3R-1 §7 / 3R-2 §7 anti-lookahead 一致）
- ❌ helper 不允许 caller 注入 `analysis_date >= 2026-01-01` 的 record（启动 gate + record-level filter）
- ❌ helper 不允许 caller 注入 `outcome` 在 candidate 决策时已知的 record（这是 caller 责任，但 helper 通过 record schema 强制 outcome 字段不进 candidate decision 输入）

---

## 7. 6 metrics 计算

继承 Step 3R-4 §5 / 3R-4 checkpoint §5 的 6 metric。helper 对每个
held-out window **单独**计算（不允许只 pool）。

### 7.1 `accuracy_delta_vs_baseline`

| 项 | 值 |
|---|---|
| **denominator** | window 内 paired records 数（`prediction_correct in {True, False}`）|
| **formula** | `(candidate触发后整体 acc) − (baseline acc)` <br> 即：在 window 内，「`exclusion_would_block=True` 的 record 全部按 baseline_correct 算；`exclusion_would_block=False` 的 record 按 prediction_correct 算」 减去 「全部按 baseline_correct 算」 |
| **edge case：denom = 0** | 返回 `None`；warning `acc_delta_skipped: zero_paired` |
| **gate threshold** | `>= +0.02` |

### 7.2 `false_exclusion_rate`

| 项 | 值 |
|---|---|
| **denominator** | window 内 `candidate_triggered=True` 且 `prediction_correct in {True, False}` 的 record 数 |
| **numerator** | window 内 `candidate_triggered=True` 且 `prediction_correct=True` 的 record 数（与 Step 2G-7C 一致：fer = correct / paired，"误杀"= 排除原本预测正确的判断） |
| **formula** | `correct / paired`（fully-bullish 候选语义） |
| **edge case：denom = 0** | 返回 `None`；warning `fer_skipped: zero_triggered`；同时触发 §8 `minimum_window_sample_size` no-go |
| **gate threshold** | `<= 0.10`（per-fold held-out window，**worst-window 决胜**） |

### 7.3 `net_benefit`

| 项 | 值 |
|---|---|
| **denominator** | window 内 paired records 数 |
| **formula** | counterfactual：在 held-out window 上剔除 candidate 触发样本后整体 acc 提升幅度（与 `services/soft_metadata_simulator._net_benefit_from_dashboard` 一致） |
| **edge case：denom = 0** | 返回 `None`；warning `nb_skipped: zero_paired` |
| **gate threshold** | `>= +0.05` |

### 7.4 `survival_case_preservation`

| 项 | 值 |
|---|---|
| **denominator** | window 内 `survival_case=True` 的 record 数（即 candidate 触发**且**预测正确） |
| **numerator** | window 内 `survival_case=True` 且能被 sidecar 明确呈现的 record 数（即在 helper 输入 record 层面，`survival_case=True` 的 record 默认全部"明确呈现"，所以默认 numerator = denominator；除非 caller 显式标记 `survival_silenced=True` 字段） |
| **formula** | `numerator / denominator` |
| **edge case：denom = 0** | 返回 `None`（无 survival case 时跳过；不应触发 fail）；warning `survival_skipped: zero_survival_cases` |
| **gate threshold** | `>= 0.80` |

### 7.5 `cross_window_variance`

| 项 | 值 |
|---|---|
| **denominator** | n/a（这是跨 fold 极差） |
| **formula** | `max(per_window_fer) − min(per_window_fer)`（仅在所有 held-out window 都有 fer 值时计算；任一窗 fer = None → 该 metric = None + warning） |
| **edge case** | 至少 2 个窗有有效 fer 才能计算极差；少于 2 个 → `None` |
| **gate threshold** | `<= 0.10`（跨 fold 极差） |

### 7.6 `minimum_window_sample_size`

| 项 | 值 |
|---|---|
| **denominator** | n/a（这是 per-window 触发样本数最小值） |
| **formula** | `min(per_window_paired_when_triggered)` <br> 即：每个 held-out window 中 `candidate_triggered=True ∧ prediction_correct in {True, False}` 的 record 数最小值 |
| **edge case** | 至少 1 个窗有有效 paired 才能计算 |
| **gate threshold** | `>= 20` per-fold held-out window |

---

## 8. 7 gate thresholds

继承 Step 3R-4 §6 / 3R-4 checkpoint §6。helper **应用** protocol，
**不**调阈值。

| # | gate | threshold | 范围 |
|---|---|---|---|
| 1 | `minimum_window_sample_size` | **`>= 20`** | per-fold held-out window |
| 2 | `false_exclusion_rate` | **`<= 0.10`** | per-fold held-out window，**worst-window 决胜** |
| 3 | `net_benefit` | **`>= +0.05`** | per-fold held-out window |
| 4 | `cross_window_variance` | **`<= 0.10`** | 跨 fold 极差 |
| 5 | **`no_single_window_collapse`** | 任一 window **不能** `fer >= 0.20` OR `nb <= 0` | 兜底守卫 |
| 6 | `survival_case_preservation` | **`>= 0.80`** | per-fold held-out window |
| 7 | `accuracy_delta_vs_baseline` | **`>= +0.02`** | per-fold held-out window |

### 8.1 阈值不可调

| 项 | 强制 |
|---|---|
| helper 不允许 caller 在调用时 override 阈值 | ✅（`build_regime_validation_report` API 不暴露 threshold 参数） |
| 阈值变更必须经 launch review | ✅（在 protocol 层修改，不在 helper 层） |
| helper 不读 2026 数据调阈值 | ✅（启动 gate + record-level cutoff） |

---

## 9. worst-window rule

| 规则 | 实施 |
|---|---|
| **pooled pass 但 worst-window fail = overall fail** | helper 必须在 `gate_status` 中**仅依据 worst-window 决策**；pooled metrics 写入 `pooled_metrics` 字段但**不**进 `gate_status` |
| **worst-window 选择优先级**（per-fold） | 1) 任一 fold 的 held-out window `fer > 0.10` → 该 window 即 worst <br> 2) 任一 fold 的 held-out window `nb < +0.05` → 该 window 即 worst <br> 3) 任一 fold 的 `paired < 20` → 该 window 即 worst（且触发 minimum_window no-go） <br> 4) 任一 fold 的 `survival_case_preservation < 0.80` → 该 window 即 worst <br> 5) 否则按 `fer` 最大者 → worst |
| **不能只汇总 overall** | helper 必须 emit `per_window_metrics` 全 6 项；任何只在 pooled 上看好的 candidate 必然被 worst-window 击穿 |

### 9.1 worst-window 字段

| 字段 | 说明 |
|---|---|
| `worst_window` | string；W1/W2/W3/W4 中的一个 |
| `worst_window_metrics` | dict；该 window 的 6 metric 实际值 |
| `worst_window_reason` | string；触发"最差"的具体 metric（例：`"false_exclusion_rate=0.1052_above_0.10"`） |

---

## 10. no-go implementation logic

把 Step 3R-4 §9 / 3R-4 checkpoint §7 的 10 no-go rules 转成 `gate_status`：

| # | no-go 条件 | gate_status 体现 | overall_status 影响 |
|---|---|---|---|
| 1 | 任一 held-out window 样本数 `< 20` | `gate_status.minimum_window_sample_size = "fail"` | `fail` |
| 2 | 任一 held-out window `fer > 0.20` | `gate_status.no_single_window_collapse = "fail"` | `fail` |
| 3 | pooled pass 但 worst-window fail | `gate_status` 任一字段 = `"fail"`（按 worst-window） | `fail` |
| 4 | candidate 需要 2026 数据才能 pass | `final_test_refusal = True` + warning | `error`（报告作废） |
| 5 | candidate 牺牲 survival cases（preservation `< 0.80`） | `gate_status.survival_case_preservation = "fail"` | `fail` |
| 6 | 任一 fold 的 `cross_window_variance > 0.10` | `gate_status.cross_window_variance = "fail"` | `fail` |
| 7 | candidate 在 train 阶段读取了该 fold 的 held-out window 数据 | warning `heldout_leakage_suspected`；helper 假设 caller 责任，能力检测仅做 heuristic flag | `fail`（如能检出） |
| 8 | candidate 触碰 2026-01-01 之后任何数据 | `final_test_refusal = True` + warning `record_with_2026_date_seen` | `error`（报告作废） |
| 9 | `accuracy_delta_vs_baseline < 0` | `gate_status.accuracy_delta_vs_baseline = "fail"` | `fail` |
| 10 | report 缺失 §11 任意必备字段 | helper 不应触发（输出由 helper 自身生成）；但若 caller 自定义 hook 篡改 → warning `report_field_missing` + `overall_status="error"` |

### 10.1 overall_status 决策表

| `gate_status` 7 项 | `final_test_refusal` | `overall_status` |
|---|---|---|
| 全部 `"pass"` | `false` | **`"pass"`** |
| 任一 `"fail"` | `false` | **`"fail"`** |
| 任一 `"fail"` | `true` | **`"error"`**（cutoff 触碰优先；报告作废） |
| 全部 `"pass"` | `true` | **`"error"`**（不应发生；helper 抛 sanity warning） |

**不允许 `"partial"`**：与 3R-4 §12.1 schema 不变量一致。

---

## 11. output schema

```json
{
  "schema_version": "regime_validation_report.v1",
  "candidate_name": "r4_baseline",
  "candidate_kind": "smoothing | formula | label_assignment",
  "fold_count": 4,
  "windows": {
    "W1": {"start": "2023-01-03", "end": "2023-08-31", "paired": 130},
    "W2": {"start": "2023-09-01", "end": "2024-02-29", "paired": 100},
    "W3": {"start": "2024-03-01", "end": "2024-08-02", "paired": 56},
    "W4": {"start": "2024-08-03", "end": "2025-12-31", "paired": 353}
  },
  "per_window_metrics": {
    "W1": {
      "minimum_window_sample_size": 28,
      "false_exclusion_rate": 0.0857,
      "net_benefit": 0.0512,
      "accuracy_delta_vs_baseline": 0.0421,
      "survival_case_preservation": 0.85,
      "triggered_paired": 28
    },
    "W2": {"...": "..."},
    "W3": {"...": "..."},
    "W4": {"...": "..."}
  },
  "pooled_metrics": {
    "false_exclusion_rate": 0.0921,
    "net_benefit": 0.0498,
    "accuracy_delta_vs_baseline": 0.0395
  },
  "worst_window": "W2",
  "worst_window_metrics": {"...": "..."},
  "worst_window_reason": "false_exclusion_rate=0.1052_above_0.10",
  "cross_window_variance": {
    "false_exclusion_rate": 0.0512,
    "net_benefit": 0.0123
  },
  "leave_one_window_out": {
    "F1_train_W2_W3_W4_validate_W1": "pass",
    "F2_train_W1_W3_W4_validate_W2": "fail",
    "F3_train_W1_W2_W4_validate_W3": "pass",
    "F4_train_W1_W2_W3_validate_W4": "pass"
  },
  "gate_status": {
    "minimum_window_sample_size": "pass",
    "false_exclusion_rate": "fail",
    "net_benefit": "pass",
    "accuracy_delta_vs_baseline": "pass",
    "cross_window_variance": "pass",
    "survival_case_preservation": "pass",
    "no_single_window_collapse": "pass"
  },
  "overall_status": "fail",
  "fail_reason": "false_exclusion_rate at W2 = 0.1052 > 0.10 gate",
  "final_test_refusal": false,
  "data_cutoff_used": "2025-12-31",
  "warnings": []
}
```

### 11.1 必备字段（缺即 `overall_status="error"`）

| 字段 | 不变量 |
|---|---|
| `schema_version` | 总是 `"regime_validation_report.v1"` |
| `candidate_name` | string（caller 必填） |
| `candidate_kind` | enum（caller 必填） |
| `fold_count` | `3` 或 `4`（整数） |
| `windows` | W1 / W2 / W3 必备；4-fold 时 W4 也必备；3-fold 时 W4 = `null` |
| `per_window_metrics` | 每个 held-out window 6 metric 全 present |
| `worst_window` | 字符串；W1/W2/W3/W4 中的一个 |
| `worst_window_metrics` | dict；6 metric |
| `cross_window_variance` | dict；至少 `false_exclusion_rate` 字段 |
| `leave_one_window_out` | 4 fold 时 4 entry；3 fold 时 3 entry |
| `gate_status` | 7 项（6 metric + `no_single_window_collapse`）|
| `overall_status` | `"pass"` / `"fail"` / `"error"`（不允许 `"partial"`） |
| `final_test_refusal` | bool；`true` → 报告作废 |
| `data_cutoff_used` | `<= 2025-12-31`；硬不变量 |
| `warnings` | list of string |

---

## 12. 与 Step 3R-2 的关系

| 维度 | Step 3R-2 helper（已 merge `e2a681b` / `db7618b`） | Step 3R-4.1 validation helper（本设计） |
|---|---|---|
| 功能层 | **数据层**（生成 `regime_labels.v1`） | **评分层**（基于 records + protocol 输出 `regime_validation_report.v1`） |
| 输入 | DataFrame（OHLC + peer + market）| record list（已完成 replay / review） |
| 是否优化 thresholds | ❌ 否 | ❌ 否（应用 protocol） |
| 是否宣称 candidate pass / fail | ❌ 否（labels 不决定 pass/fail） | ✅ 是（`overall_status`） |
| 关系 | 3R-2 提供 labels；本 helper **可选**读取 labels 作为 grouping（但不参与 gate 决策） |
| 是否依赖对方 | 本 helper **不**强制依赖 3R-2；labels 字段 optional |
| 是否被对方依赖 | 3R-2 不依赖本 helper |

→ **labels 不决定 pass/fail；pass/fail 来自 metrics / gates**。

### 12.1 labels 在 helper 中的可选用途

| 用途 | 是否决定 pass/fail |
|---|---|
| 用 `label_pos20_regime` / `label_market_trend_regime` 等切片做 per-bucket fer 分布展示 | **❌ 否**（只作 read-only diagnostics 输出在 `warnings` 或扩展字段中） |
| 触发 candidate 时使用 labels 作为 candidate 触发条件的一部分（这是 candidate 设计层，不是 helper 层） | helper 不参与 |

---

## 13. 与 W4 输出的关系

| 维度 | W4 output dir（`logs/historical_training/three_system_w4_2024_08_2025_12/`） |
|---|---|
| 是否进 main | **❌ 暂不**（与 8D.4 §6.3 一致；本设计不强制改变） |
| helper 是否可读取 W4 results jsonl | ✅ 可（caller 责任：从 `three_system_replay_results.jsonl` parse 成 helper 的 record list） |
| W4 manifest 必须通过 § 3 启动 gate | ✅ 是；4-fold 模式下 hard 强制 |
| W4 是否等于 final test | **❌ 否**；W4 = 2024-08-03 → 2025-12-31，final test = 2026-01-01 → ∞ |
| W4 是否是 validation window | ✅ 是（leave-one-window-out 4-fold 之一） |
| helper 是否写 W4 输出 | **❌ 否**（read-only；不修改任何已有 W4 文件） |
| caller 是否需要从 W4 派生 `candidate_triggered` / `prediction_correct` / `survival_case` 字段 | ✅ 是（caller wrapper 责任，本 helper 只接受组装好的 records） |

---

## 14. 与 hard / required 的关系

| 维度 | 本 helper |
|---|---|
| **report `overall_status="pass"` 是否自动启 `hard`** | **❌ 否** |
| **report `overall_status="pass"` 是否自动改 `required`**（04 / 05 / 07） | **❌ 否** |
| **report `overall_status="pass"` 是否让 Gate 5 / Gate 6 自动 pass** | **❌ 否** |
| **report `overall_status="pass"` 是否允许进入下一步 design review** | ✅ 是（这是 helper 的全部用途） |
| **report 是否驱动 `_PROTECTION_LAYER_CONNECTED` 翻 True** | **❌ 否** |
| **report 是否驱动 `hard_exclusion_allowed` / `primary_blocker` 派生** | **❌ 否** |
| **report 是否写 `simulated_trade` / `no_trade` / `confidence_system`** | **❌ 否** |
| **production wiring** | 本 helper 完全不参与；wiring 由独立后续 step 决定，且必须经过 launch review |

→ **report pass 不自动启 hard / 不改 required / 不让 Gate 5 / Gate 6
pass / 不让 `_PROTECTION_LAYER_CONNECTED` 翻 True**。helper 的全部
用途是在 cross-window protocol 下产出**结构化判断**，供 design review
作为决策输入。

---

## 15. 成功标准

| # | 标准 | 验证方式 |
|---|---|---|
| 1 | **能复现 R4 fail** | 用 R4 当前候选（fer=0.3235 / nb=+0.0219 / W1-W2 gap +0.18）跑本 helper，期望 `overall_status="fail"` + `worst_window` ∈ {W2 或 highest fer window} + `false_exclusion_rate` gate fail |
| 2 | **能处理 W1–W4** | 输入 records 横跨 4 windows 时，`fold_count=4` + `per_window_metrics` 4 entry + `leave_one_window_out` 4 fold |
| 3 | **能阻止 pooled pass / worst-window fail** | gate_status 仅依据 worst-window；pooled metrics 不进 gate_status |
| 4 | **不读 2026** | 启动 gate（W4 manifest `final_test_touched=false`）+ record-level filter（`analysis_date < cutoff`）双重 stop；任何 2026 record → `final_test_refusal=true` + `overall_status="error"` |
| 5 | **不写 DB** | helper 是纯函数；输入 records，输出 dict；caller 责任写盘 |
| 6 | **schema 稳定** | `regime_validation_report.v1` 不变量在 helper / report consumer 之间双向锁定 |
| 7 | **可供 3R-3 / 3R-5 / 3R-6 使用** | helper API 不依赖 candidate 的具体形式（smoothing / formula / label_assignment 都通过 record list 喂入） |
| 8 | **不优化 thresholds** | helper 不暴露 threshold 参数；调阈值必须经 launch review |
| 9 | **不接 trading API** | 静态 import 锁定（与 3R-2 helper isolation 类似） |
| 10 | **不写 main 决策**（hard / required / simulated_trade / no_trade） | 设计层禁止 + 实施时 unit test 锁定 |
| 11 | **report `overall_status="pass"` 不自动启 hard** | 与 §14 一致；wiring 永远是独立 step |
| 12 | **labels 不决定 pass/fail** | 与 §12 一致；gate_status 来源仅是 metrics |

---

## 16. 下一步建议

按推荐优先级：

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **commit 本 design** | 把 §1-17 4-fold helper 设计固化到 main | **本轮 / 下一轮** |
| 2 | **Step 3R-4.1 checkpoint** | 把本 design 状态归档；锁定 W4 manifest gate / API / metrics / output schema | **下一轮** |
| 3 | **Step 3R-4.2 read-only validation helper implementation** | 新增 `services/regime_validation_helper.py` + tests + W4 manifest gate；纯 read-only；与 3R-2 helper 同等 isolation；首个 4-fold 动代码步 | 中（在 3R-4.1 checkpoint 进 main 后启动） |
| 4 | **不推荐**直接 3R-3 smoothing candidate design | 必须先过 3R-4.2 helper 实施 + 实测 R4 fail 复现，再设计 smoothing | **❌** |
| 5 | **不推荐**直接 3R-5 formula design | 必须先过 3R-3 + 3R-4.1 helper 在 4-fold 协议下出报告 | **❌** |
| 6 | **不推荐**直接 3R-6 read-only simulator | 必须先过 3R-5 design | **❌** |
| 7 | **不推荐**让 helper 读 DB / 网络 / yfinance / trading API | 与 §4 / §15 一致 | **❌** |
| 8 | **不推荐**让 helper 写 DB / decisions / required | 与 §14 / §15 一致 | **❌** |
| 9 | **不推荐**让 helper `overall_status="pass"` 自动启 hard / Gate 5 / Gate 6 | 与 §14 一致 | **❌** |
| 10 | **不推荐** 升级 04 required | Step 2G 全程边界 | **❌** |
| 11 | **不推荐** 触碰 2026 final test range | 永久封禁 | **❌** |
| 12 | **不推荐** R4 hard implementation | 三重 NO-GO 已锁定 | **❌** |
| 13 | **不推荐**让 `_PROTECTION_LAYER_CONNECTED` 翻 True | 与 v1 / 3R-0 / 3R-4 一致 | **❌** |

**关键判断**：
- 顺序 = 本 design → 3R-4.1 checkpoint → **3R-4.2 helper 实施**（首个
  动代码步）→ 用 helper 复现 R4 fail → 3R-3 smoothing design → 3R-5
  formula design → 3R-6 simulator → 3R-7 sidecar
- Step 3R-4.1 与 Step 3R-2 helper / Step 2G-8D W4 输出**解耦但有依赖**：
  本 helper 在 4-fold 模式下**强制依赖** W4 manifest 通过 §3 gate；
  本 helper **可选依赖** 3R-2 labels 作为 diagnostics

---

## 17. 严守边界

本文是**纯 design markdown**：

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
- ❌ 没把 W4 输出 commit 进 main
- ❌ 没把 smoke 输出 commit 进 main
- ❌ 没运行 `pytest`（本轮纯文档；测试基线维持 commit `4bdd782` 时
  的 2689 / 0 failed / 10 skipped）
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` /
  `avgo_agent.db.backup_*`
- ✅ 只新增 1 份 markdown design 文档（本文件）
