# Step 2G-8A — Protection-Layer Connection Design Checkpoint

本文是 Step 2G-8A 的状态固化文档。
**只 checkpoint，不实现，不改代码，不写 DB，不启 hard / forced，不接 trading。**

---

## 1. 当前完成状态

- Step 2G-8 launch condition review 已完成（结论：NO-GO，hard gate 4/6 fail）
- Step 2G-8A protection-layer connection design 已完成并进入 main
- 本 checkpoint 固定 Step 2G-8A 的 **sidecar-only 连接边界**
- Step 2G-8A 不是实现，是设计；本 checkpoint 不是实现，是状态归档

---

## 2. 当前 main 状态

- main 最新 commit: **`b4c1919`**
- commit message: `docs(contract): Step 2G-8A protection-layer connection design`
- 本步骤新增文件:
  - `tasks/step_2g8a_protection_layer_connection_design.md`
- 本轮 checkpoint 只记录状态，不实现 helper、不修改 UI、不写 sidecar

---

## 3. 8A 的核心定位

- 8A **不是 hard implementation**
- 8A **不是 required 字段升级**
- 8A 只设计 protection layer diagnostics **如何接入**
- 接入对象限定为：
  - `exclusion_system.extras.soft_metadata` 子节点
  - Predict / Review 的 anti-false-exclusion 展开器
  - 后续 dashboard 的诊断聚合
- **接入对象 = sidecar / extras / display diagnostics**
- **接入对象 ≠ hard decision pipeline**
- **Gate 5 不因为 8A 设计完成而 pass**

---

## 4. 推荐保护模块（v1 范围）

第一版优先做以下两个 guard：

### 4.1 holdout_stability_guard
- 触发条件：`holdout_status == "FAIL"`
- 行为：阻止任何 hard 升级（仅以 sidecar 标记表达，不动决策链）
- 数据依赖：已存在（Step 3B-1 holdout simulation 已沉淀）
- 不需要新模型

### 4.2 net_benefit_guard
- 触发条件：`net_benefit < +0.05`
- 行为：阻止任何 hard 升级（仅以 sidecar 标记表达）
- 数据依赖：已存在（Step 3A 已计算）
- 直接对应 hard gate "net_benefit_gte_0_05" 的 fail 原因

### 4.3 v1 不做的
- `r4_survival_pattern_filter` — 留给 Step 2G-8B（narrower candidate research）
- `r4_secondary_confirmation_filter` — 同上

**理由**：v1 只选最低风险、数据已就绪、不需要新模型的 guard，避免在 Gate 5 仍 fail 的状态下引入新的实现复杂度。

---

## 5. sidecar schema 冻结

`protection_layer_diagnostics.v1`:

```json
{
  "schema_version": "protection_layer_diagnostics.v1",
  "diagnostic_connected": true,
  "hard_gate_connected": false,
  "required_field_connected": false,
  "protection_layer_connected_for_gate": false,
  "guards": [
    {
      "name": "holdout_stability_guard",
      "status": "blocking",
      "reason": "holdout_status_FAIL",
      "evidence": {"holdout_status": "FAIL"},
      "message": "跨窗口验证未通过，当前不能自动升级。"
    },
    {
      "name": "net_benefit_guard",
      "status": "blocking",
      "reason": "net_benefit_below_gate",
      "evidence": {"net_benefit": 0.0219, "threshold": 0.05},
      "message": "净收益不足，当前不能自动升级。"
    }
  ],
  "summary": {
    "hard_upgrade_blocked": true,
    "display_only": true,
    "required_next_step": "narrower_candidate_research"
  }
}
```

**强不变量**：
- `hard_gate_connected` 永远 `false`
- `required_field_connected` 永远 `false`
- `protection_layer_connected_for_gate` 永远 `false`
- `summary.display_only` 永远 `true`
- `summary.hard_upgrade_blocked` 在 v1 永远 `true`（任一 guard blocking 即 true）

---

## 6. 四个 connection flag 的含义

| flag | v1 取值 | 含义 |
|---|---|---|
| `diagnostic_connected` | `true` | sidecar / display diagnostics 已接入；UI 可读到此节点 |
| `hard_gate_connected` | `false` | 没有进入 hard decision pipeline；run_predict / scanner 不读 |
| `required_field_connected` | `false` | 没有写 04 required 字段；schema 无升级 |
| `protection_layer_connected_for_gate` | `false` | hard gate 第 5 项 `protection_layer_connected` 仍 fail |

**反误读强调**：
- `diagnostic_connected = true` **不等于** Gate 5 pass
- `diagnostic_connected = true` **不等于** hard 升级被允许
- `diagnostic_connected = true` **只代表** "诊断信息可在 UI 中展示"
- 这一约束写入 schema 是为了防止未来读者把"sidecar 接入"误解读为"决策链接入"

---

## 7. 与 hard gate 的关系

8A 设计完成 / 实现之后，hard gate 状态保持：

| Gate | 状态 |
|---|---|
| total_paired_ge_90 | PASS |
| candidate_paired_ge_30 | PASS |
| false_exclusion_rate_lte_0_10 | FAIL (R4 fer = 0.3235) |
| net_benefit_gte_0_05 | FAIL (nb = +0.0219) |
| **protection_layer_connected** | **FAIL（仍 fail）** |
| cross_window_holdout_pass | FAIL |

**Gate 5 仍 fail 的理由**：
- sidecar diagnostics ≠ 真实决策链连接
- 没有任何 hard decision 路径在读 `protection_layer_diagnostics.v1`
- 没有测试证明 protection layer 在线上能阻止误杀
- 没有 holdout 验证 protection layer 的实际行为
- 因此 Gate 5 在 Step 2G-7C dashboard 中仍判 fail

**让 Gate 5 未来真正 pass 的必要条件**（不在 Step 2G-8A 范围内）：
1. protection layer 参与真实 hard decision pipeline（不是 sidecar）
2. 有测试证明 protection layer 会阻止误杀
3. 有 holdout 验证 protection layer 的真实行为
4. 另立 Step 2G-8+ 的 gate review，重新跑 hard gate 评估
5. 必须在 2026-01-01 之前的数据上完成验证（不得偷看 final test set）

**当前不满足**。

---

## 8. 与 anti_false_exclusion_display.v1 的关系

- `protection_layer_diagnostics.v1` 是 `anti_false_exclusion_display.v1` 的**补充**，不是替代
- 现有 5 个 protective findings（误杀率高 / 净收益低 / holdout fail / 候选稀薄 / R4 fer 高）保留不动
- protection_layer_diagnostics 在 Predict / Review 的 anti-false expander 中作为**子节**显示，标题"保护层诊断详情"
- **不改变** `hard_exclusion_allowed = false`
- **不改变** `status = blocked`
- **不改变** anti-false-exclusion 五项 finding 的语义
- AFX 显示器的 19 个 forbidden tokens 标准继承到 protection_layer_diagnostics 的展示文案

---

## 9. UI 显示建议

### 9.1 Predict 页面
- 在 `anti_false_exclusion_display` 展开器下方，新增子节"保护层诊断详情"
- 显示 guards 列表 + summary
- 显示 4 个 connection flag 的状态（明确标注 sidecar-only）
- 不替换现有 5 项 protective finding

### 9.2 Review 页面
- 在保护层诊断子节中显示 `triggered_but_not_error` 与 guard 的对应关系
- 4 象限归因（possible_attribution / triggered_but_not_error / no_attribution / no_metadata）保留
- guard 信息属于"复盘提示"，不属于"hard 决策"

### 9.3 Dashboard（Step 2G-7C 后续）
- 8A.3 可增加：
  - `guard_total` 计数
  - `guard_blocking_count` 计数
  - 各 `blocking_reason` 分布
- 仍不让 Gate 5 自动 pass

### 9.4 文案规范
允许使用的描述：
- "诊断已接入"
- "不等于自动升级"
- "当前仍只允许复盘提示"
- "保护层仍未进入决策链"
- "跨窗口验证未通过，当前不能自动升级"
- "净收益不足，当前不能自动升级"

**禁止用词**继承 AFX 19 token lockdown：
- 16 个 renderer tokens（warning / alert / 警报 / 警告 / 强烈建议 / ...）
- 3 个 AFX-only tokens（` hard ` / ` forced ` / `排除`）

---

## 10. 仍然禁止的事

- ❌ 不让 Gate 5 pass
- ❌ 不写 `anti_false_exclusion_triggered = True`
- ❌ 不启用 hard / forced 升级路径
- ❌ 不改 04 / 05 / 07 required 字段
- ❌ 不写 DB（无新表、无 schema 改动、无 backup）
- ❌ 不保存 diagnostics 到持久层（仅内存计算 + sidecar 显示）
- ❌ 不接 trading API
- ❌ 不让 scanner / run_predict 读 protection_layer_diagnostics
- ❌ 不让 hard exclusion 行为依赖 guard 结果

---

## 11. 2026 final test cutoff

- 8A 设计 **不使用 2026-01-01 之后数据**
- 2026-01-01 之后仍是**最终测试集**，对所有 Step 2G-8 系列封锁
- 不得为让 Gate 5 pass 而偷看 final test data
- holdout_stability_guard / net_benefit_guard 的 evidence 全部来自 Step 3A / 3B 已沉淀的 in-window 数据
- final test cutoff 在 8A.1 / 8A.2 / 8A.3 实现阶段必须继续严守

---

## 12. 下一步建议

### 12.1 推荐
1. **Step 2G-8A.1 — read-only protection diagnostics helper**
   - 实现 `protection_layer_diagnostics.v1` 的纯函数生成器
   - 仍 sidecar only（写入 `extras.soft_metadata.protection_layer_diagnostics`）
   - 不让 Gate 5 pass
   - 不写 DB
   - 仅 caller-injected 输入，无内部 DB 读取

2. **Step 2G-8A.2 — Predict / Review UI 子节集成**
   - 在 anti-false expander 中新增"保护层诊断详情"子节
   - 严格继承 19 token lockdown
   - 不改变 status / 不改变 hard_exclusion_allowed

3. **Step 2G-8A.3 — dashboard 接入**
   - 在 Step 2G-7C 聚合 dashboard 中新增 guard 计数维度
   - Gate 5 判断逻辑保持不变（仍 fail）

4. **Step 2G-8B — narrower R4 candidate research**
   - 只读诊断
   - 寻找能降低 R4 fer 的二级条件
   - 不接决策链

### 12.2 不推荐
- ❌ 不推荐 hard implementation（不要让 protection layer 真正进入 decision pipeline）
- ❌ 不推荐升级 04 required schema
- ❌ 不推荐让 Gate 5 自动 pass

---

## 13. 严守边界

本文是**纯 checkpoint 文档**：

- ✅ 没改代码
- ✅ 没写 DB
- ✅ 没启 hard / forced
- ✅ 没改 04 / 05 / 07 required
- ✅ 没接 trading
- ✅ 没触碰 2026 final test range
- ✅ 没让 Gate 5 pass
- ✅ 没创建任何 sidecar / helper / UI 实现

**Step 2G-8A 系列定位**：design + checkpoint，不实现。
