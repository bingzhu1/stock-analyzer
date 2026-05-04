# Step 2G-8A — Protection-Layer Connection Design

> **设计文档（protection-layer connection design），不是实现。**
> 本文档**冻结** Gate 5（`protection_layer_connected`）以 sidecar
> diagnostics 形式接入的方案选择、guard 候选清单、display schema、
> UI 接入位置、文案边界、与 anti_false_exclusion_display.v1 的关系、
> 与 hard gate 的隔离约束、与 Step 2G-8B / 2G-8C / Step 2G-8+ 的衔接。
>
> 本轮**不动任何代码**：不改 `predict.py` / `run_predict` /
> `scanner.py` / `prediction_store.py` / `app.py` / `ui/*` /
> `services/*` / 任何 builder / DB schema 中的任何一处。

## 1. 背景

- **Step 2G-8 launch condition review**（commit `7cc18ae`）已结论：
  - **full implementation NO-GO**（4 项 hard gate fail；hard /
    required 升级仍永远禁止）
  - **Gate 5 `protection_layer_connected`** 是**唯一可独立解耦**的
    blocker（其他 3 项与 Step 3 calibration 重启 / R4 二级过滤研究
    强耦合）
- 本文档（Step 2G-8A）**只设计** protection layer 如何以
  **sidecar diagnostics** 形式接入：
  - **不**启 hard
  - **不**写 04 required
  - **不**让 Gate 5 自动变 pass —— 即使本设计实施后，gate 仍由
    Step 2G-7C dashboard 评估，**diagnostic-connected ≠ gate-pass**

## 2. 当前 Gate 5 状态

- `protection_layer_connected = false`（v1 hard-coded 直到 Step 2G-8+
  真接入决策链）
- 这是 4 个 fail gate 之一（其余 3 个：fer / nb / holdout）
- **即使** Step 2G-8A 实施后让 Gate 5 变成 "diagnostic-connected"，
  hard gate 仍会显示 fail —— 因为：
  - "diagnostic" 接入 ≠ "decision pipeline" 接入
  - 真 pass 需要保护层**真的参与** hard 决策（拒绝某些 hard 触发），
    而不只是显示 diagnostics
  - 真 pass 还需要测试证明该保护层会阻止误杀样本
- **本设计明确**：Step 2G-8A 不让 Gate 5 自动 pass；hard 仍永远禁止

## 3. 候选保护模块 / 方向

不再依赖 `anti_false_exclusion_audit` /
`big_up_contradiction_card` / `big_down_tail_warning` /
`exclusion_reliability_review` 这 4 个**离线 audit 模块**接入主链
（接它们需要改 `_build_exclusion_system` / 主流程，违反 Step 2G
全程"不改 builder"边界）。改用**4 个新的轻量 guard 方向**，每个都
基于现有 baseline 数据计算，**不**依赖任何离线 audit 模块：

| # | guard name | 触发条件 | 目标 |
|---|---|---|---|
| 1 | `r4_survival_pattern_filter` | 用 `correct + R4 triggered` 样本（Step 2G-6C 的 `triggered_but_not_error` 象限）寻找 survival pattern；当某个 R4 子条件下 survival rate > 50% 时标记 | 识别哪些 R4 不该被排除（即使将来 hard 启用） |
| 2 | `r4_secondary_confirmation_filter` | R4 + 额外弱势确认（如 `peer_path_risk_direction=lower` + `confidence_high`）才升级风险等级 | 缩小 candidate，降低 fer 同时保留 nb |
| 3 | `holdout_stability_guard` | `holdout_status == "FAIL"` → 阻止任何 hard / required 升级 | 把 holdout fail 显式接入保护层 sidecar |
| 4 | `net_benefit_guard` | `net_benefit < +0.05` → 阻止任何 hard / required 升级 | 把收益不足显式接入保护层 sidecar |

## 4. 推荐优先模块

明确推荐**第一版只做 #3 + #4**：

| 决策 | 理由 |
|---|---|
| **优先 `holdout_stability_guard` + `net_benefit_guard`** | 数据已就位（Step 2G-7C aggregate baseline 已暴露 `holdout_status` / `net_benefit`）；不需要新模型；不需要猜 survival pattern；最低实施风险；可直接解释"为什么 hard 不能开" |
| **`r4_survival_pattern_filter` 留给 Step 2G-8B** | survival pattern 探索需要 ad-hoc sqlite 研究 + 候选切片对比，属 narrower R4 candidate research 范畴 |
| **`r4_secondary_confirmation_filter` 留给 Step 2G-8B** | 同上；与 narrower candidate 研究同源 |

→ Step 2G-8A v1 只交付 **2 个 guard**（`holdout_stability_guard` +
`net_benefit_guard`），都是**纯数据驱动 + 无需新模型**。

## 5. sidecar schema 草案（`protection_layer_diagnostics.v1`）

```python
exclusion_system.extras.protection_layer_diagnostics = {
    "schema_version": "protection_layer_diagnostics.v1",
    "diagnostic_connected": True,                       # 仅 sidecar
    "hard_gate_connected": False,                       # 永远 False（v1）
    "required_field_connected": False,                  # 永远 False（v1）
    "protection_layer_connected_for_gate": False,       # 永远 False（v1；Step 2G-7C gate 仍 fail）
    "guards": [
        {
            "name": "holdout_stability_guard",
            "status": "blocking",                       # "blocking" | "ok"
            "reason": "holdout_status_FAIL",
            "evidence": {"holdout_status": "FAIL"},
            "message": "跨窗口验证未通过，当前不能自动升级。",
        },
        {
            "name": "net_benefit_guard",
            "status": "blocking",
            "reason": "net_benefit_below_gate",
            "evidence": {
                "net_benefit": 0.0219,
                "threshold": 0.05,
            },
            "message": "净收益不足，当前不能自动升级。",
        },
        # ... 0..N guards (extensible to filter / pattern guards in
        # Step 2G-8B)
    ],
    "summary": {
        "hard_upgrade_blocked": True,                   # ALL guards considered
        "display_only": True,                            # sidecar 仍是 display-only
        "blocking_guard_count": 2,
        "required_next_step": "narrower_candidate_research",
    },
}
```

强约束（spec 层面）：

- ✅ `diagnostic_connected = True` —— sidecar 已接入
- ❌ `hard_gate_connected = False` —— 永远 False（v1 spec 强约束）
- ❌ `required_field_connected = False` —— 永远 False（v1）
- ❌ `protection_layer_connected_for_gate = False` —— 永远 False
  （v1；Step 2G-7C dashboard 的 Gate 5 仍 fail）
- ✅ `summary.hard_upgrade_blocked = True` —— 任何 guard `status =
  "blocking"` 时都为 True
- ✅ `summary.display_only = True` —— 永远 True（v1）
- 任何字段写入失败 → 整段 sidecar 省略，**不**部分填

**让 Gate 5 真正 pass 是另一件事**：必须 Step 2G-8+ 重新做 launch
review，证明：
1. 保护层**真**参与 hard decision pipeline（不只是显示）
2. 测试**证明**该保护层在历史样本上阻止了误杀
3. 跨窗口 holdout 验证**通过**
4. Step 2G-8 launch condition review 重新跑且 6 项 gate 全部 pass

## 6. 与 `anti_false_exclusion_display.v1` 的关系

`protection_layer_diagnostics.v1` 是 **sidecar 同级**，但**不替代**
`anti_false_exclusion_display.v1`：

| 维度 | `anti_false_exclusion_display.v1`（Step 2G-7A）| `protection_layer_diagnostics.v1`（本文档）|
|---|---|---|
| 关注点 | "为什么不能 hard"（5 个 protective findings）| "保护层 guard 的 blocking 状态" |
| 数据来源 | soft_metadata.v1 + prediction_correct | baseline metrics + holdout_status + net_benefit |
| 输出粒度 | per-prediction（在 Predict / Review expander 显示）| per-baseline（dashboard aggregate 视图）|
| `hard_exclusion_allowed` | 永远 False（v1）| 同 |
| UI 位置 | Predict / Review per-prediction expander | Predict / Review expander **的子节** + dashboard tab |

**关系**：
- `anti_false_exclusion_display` 显示 **5 个 protective findings**
  （per-prediction）
- `protection_layer_diagnostics` 在 anti-false expander 之下作为
  **"保护层诊断详情"子节** 显示 **2 个 blocking guards**
  （per-baseline）
- 两者**同时**显示让用户看到完整保护证据链：
  per-prediction R4 evidence + baseline-level guard blocking
- **不**写 04 required；**不**改 `hard_exclusion_allowed`（仍 False）

## 7. 与 hard gate 的关系

| 关系 | 说明 |
|---|---|
| Step 2G-8A 完成后 hard gate 仍 **2 pass / 4 fail** | 与本设计前完全一致 |
| 即使未来只接入 diagnostic sidecar，**不算** Gate 5 pass | "diagnostic-connected" ≠ "decision-pipeline-connected" |
| Gate 5 pass 需要的真实条件 | 1) 保护层参与真实 hard decision pipeline（拒绝某些 hard 触发）；2) 测试证明会阻止误杀；3) 跨窗口 holdout 验证；4) 另立 Step 2G-8+ review |
| 当前不满足 | 4 项硬条件全部不满足；本设计**不**改变 hard 状态 |

**核心约束**：本文档**只**是 sidecar diagnostics 设计，**不**让
Step 2G-7C aggregate dashboard 的 Gate 5 自动变 pass。任何让 Gate 5
pass 的尝试都属于 Step 2G-8+ launch review 范围（前提是先做完
Step 2G-8B narrower candidate / 2G-8C holdout gap analysis）。

## 8. UI 显示设计

### 8.1 Predict 页面

- **位置**：在 anti-false expander "为什么这里只做提示"内，或
  作为新增 sub-section "保护层诊断详情"
- **内容**：渲染 `guards` 列表（2 个 blocking guard）+
  `summary.required_next_step`
- **默认折叠**（继承 anti-false expander 的折叠状态）
- **不**新增独立顶级区块（避免 dashboard 噪声）

### 8.2 Review 页面

- **位置**：在 Review 的 "保护层诊断" expander 之下作为子节
- **额外内容**：把 `triggered_but_not_error` 象限累计与 `guards`
  的 `blocking_guard_count` 关联显示，让用户看到"survival case
  存在 + guards blocking → 当前不能 hard"
- 仍**不**写 `review_log` 任何 required 字段

### 8.3 Dashboard

- **位置**：Step 2G-7C aggregate JSON 的新增字段，或一个独立的
  `dashboard.protection_layer_diagnostics` 区
- **内容**：`guards` 列表 + `blocking_guard_count` 累计 + `summary`
- **不**让 Step 2G-7C dashboard 的 `hard_gate_status.protection_layer_connected`
  自动变 pass

### 8.4 文案

- "诊断已接入"
- "不等于 hard gate 通过"
- "当前仍只允许复盘提示"
- "保护层仍未进入决策链"
- "净收益不足"
- "跨窗口验证未通过"

## 9. 文案边界

**禁止**（与 Step 2G-6 / 6A / 7A 一致）：
- 禁止交易 / 强制否定 / 必须不做
- hard exclusion / forced exclusion / `" hard "` / `" forced "`
- 自动拦截 / no_trade
- 卖出信号 / 做空信号 / 看空信号
- 否决主推演 / 推翻主推演
- 强制平仓 / force close
- 阻止下单 / block order
- "排除"（standalone）

**推荐**：
- 诊断已接入
- 不等于自动升级
- 当前仍只允许复盘提示
- 保护层仍未进入决策链
- 净收益不足
- 跨窗口验证未通过
- 不改变主推演方向
- 不构成交易指令
- 仅供复盘参考

测试锁定：未来 Step 2G-8A 实施时，`protection_layer_diagnostics`
渲染输出必须 grep 上述 19 个 forbidden tokens 全部不出现（与
Step 2G-7A AFX markdown 同标准）。

## 10. 成功标准

未来若实施 Step 2G-8A.1 helper / 2G-8A.2 UI / 2G-8A.3 dashboard
integration 必须满足：

| # | 标准 |
|---|---|
| 1 | `protection_layer_diagnostics.v1` 输出形状稳定（与 §5 schema 一致）|
| 2 | `diagnostic_connected = True`（v1 spec 强约束）|
| 3 | `hard_gate_connected = False`（v1 永远 False）|
| 4 | `required_field_connected = False`（v1 永远 False）|
| 5 | `protection_layer_connected_for_gate = False`（v1 永远 False；Step 2G-7C dashboard Gate 5 仍 fail）|
| 6 | `summary.hard_upgrade_blocked = True` 当任意 guard `status="blocking"` |
| 7 | `summary.display_only = True`（v1 永远 True）|
| 8 | `hard_exclusion_allowed` 在 anti_false_exclusion_display / soft_metadata / Step 2G-7C dashboard 中**仍** False |
| 9 | 04 / 05 / 07 required 字段 byte-stable（snapshot 测试锁定）|
| 10 | forbidden words 不出现在渲染 markdown（grep 锁定）|
| 11 | 现有测试基线（2521 / 0 failed / 10 skipped）不变 —— Step 2G-8A 新增测试是净增 |

## 11. 不做什么

- ❌ **不**让 Step 2G-7C dashboard `hard_gate_status.protection_layer_connected`
  自动变 pass
- ❌ **不**写 04 `anti_false_exclusion_triggered=True` required 字段
- ❌ **不**启用 `hard` / `forced_exclusion`
- ❌ **不**改 04 / 05 / 07 任何 required 字段
- ❌ **不**写 DB
- ❌ **不**保存 `protection_layer_diagnostics` 到 `prediction_log` /
  `outcome_log` / `review_log`
- ❌ **不**接 trading API / `longbridge` / `broker` / `paper_trade`
- ❌ **不**接 `yfinance` / `requests` / 任何网络
- ❌ **不**接 4 个离线 audit 模块（`anti_false_exclusion_audit` /
  `big_up_contradiction_card` / `big_down_tail_warning` /
  `exclusion_reliability_review`）到主链 —— 它们仍是离线 audit /
  UI；本设计**不**接入它们，改用 2 个轻量 guard
- ❌ **不**实施 `r4_survival_pattern_filter` /
  `r4_secondary_confirmation_filter` —— 留给 Step 2G-8B narrower
  candidate research

## 12. 2026 final test cutoff

- 本设计**不**使用 2026-01-01 之后的数据
- 当前 baseline 数据（holdout_status / net_benefit）来自
  2023-01-03 → 2024-08-02 replay window
- 2026 之后仍是**整个系统**完成后的最终测试集
- **不**为通过 Gate 5 偷看 final test data
- 即使 Step 2G-8A 实施后 holdout / nb 数字看似改善，也**不**意味
  Gate 5 自动 pass —— 必须 Step 2G-8+ launch review

## 13. 下一步建议

按推荐优先级：

| # | 候选 | 范围 | 优先级 |
|---|---|---|---|
| 1 | **Step 2G-8A checkpoint**（本设计）| 冻结 sidecar schema + 2 guard 选择 + 与 hard gate 的隔离约束 | **高**（设计文档天然延续） |
| 2 | **Step 2G-8A.1** read-only protection diagnostics helper | 实现 `services/protection_layer_diagnostics.py`（pure function）+ tests；输入 baseline + soft_metadata，输出本文档 §5 schema；**不**写 DB | 中-高（实现层；零代码风险）|
| 3 | **Step 2G-8A.2** Predict / Review UI integration | anti-false expander 之下作为 sub-section；纯 UI 改动；不改 contract | 中（与 #2 同 step 完成最佳） |
| 4 | **Step 2G-8A.3** dashboard integration | 把 sidecar 加入 Step 2G-7C aggregate JSON | 中（增强 dashboard 完整性） |
| 5 | **Step 2G-8B** narrower R4 candidate research | 只读 ad-hoc sqlite 研究 survival pattern 与 secondary confirmation；为 Gate 3 / 4 缩小 gap 找证据 | 中（与 8A 解耦；可并行） |
| 6 | **Step 2G-8C** holdout gap analysis | 只读对比 in-sample vs holdout；为 Gate 6 找诊断 | 中-低（与 Step 3 calibration 重启耦合） |
| 7 | **不建议**直接实施 hard gate / required 升级 | 4 项 gate fail；Step 2G-8 launch review 已 NO-GO | — |
| 8 | **不建议**改 `run_predict` / `prediction_store` 主链 | 当前 sidecar + UI display + Review attribution + protection display + dashboard aggregate 已是最大可行边界 | — |

**强制约束**：Step 2G-8A.1 / 2G-8A.2 / 2G-8A.3 / 2G-8B / 2G-8C 实施
时仍要遵守：
- 不改 04 / 05 / 07 required 字段
- 不改 `run_predict` 主链
- 不写 DB
- 不出现 19 forbidden words（AFX 内部 / protection sidecar 内部）/
  16 forbidden words（页面级）
- `hard_exclusion_allowed` 永远 `False`
- `protection_layer_connected_for_gate` 永远 `False`（v1）

## 14. 严守边界

- ❌ 本文档**只是**设计 / spec
- ❌ 没改任何代码
- ❌ 没新增任何测试
- ❌ 没写 DB
- ❌ 没改 DB schema
- ❌ 没接 `yfinance` / `requests` / 任何网络
- ❌ 没接 trading API / `longbridge` / `broker` / `paper_trade`
- ❌ 没改 `predict.py` / `scanner.py` / `prediction_store.py`
- ❌ 没改 `projection_output_adapter.py` / `projection_output_contract.py`
- ❌ 没改 `regime_diagnostics_dashboard.py` / `soft_metadata_simulator.py` /
  `soft_metadata_renderer.py` / `soft_metadata_injection.py` /
  `regime_features_builder.py` / `soft_metadata_baseline_cache.py` /
  `anti_false_exclusion_display.py` / `anti_false_exclusion_dashboard.py` /
  `predict_tab.py` / `review_tab.py`
- ❌ 没改任何 builder（`_build_exclusion_system` /
  `_build_confidence_system` / `_build_simulated_trade` / 任何其他）
- ❌ 没改 `app.py` / 任何其他 `ui/*` 模块
- ❌ 没升级 04 / 05 / 07 任何 required 字段
- ❌ 没启用 `hard` / `forced_exclusion` /
  `anti_false_exclusion_triggered`
- ❌ 没接 4 个 anti-false-exclusion 离线模块到主链
- ❌ 没改 `final_projection` / `confidence_score` / `simulated_trade` /
  `no_trade`
- ❌ 没改 `review_log` 任何 required 字段
- ❌ 没让 Step 2G-7C dashboard Gate 5 自动 pass
- ❌ 没触碰 2026-01-01 之后 final test range
- ❌ 没运行 replay / 没新写 replay 行
- ❌ 没触碰 stash / `.claude/worktrees/` / `logs/prediction_log.jsonl` /
  `avgo_agent.db.backup_*`
- ✅ 只新增 1 份 markdown 设计文档（本文件）
