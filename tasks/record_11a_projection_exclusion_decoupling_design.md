# 11A记录：Projection / Exclusion Decoupling Design

> 本设计针对 Step 09 / Step 10 中标记为 **HIGH_RISK** 的 RISK-1 + RISK-6。
>
> 本轮**只写设计**：未改代码、未新增测试、未删文件、未移动文件、未写 DB、
> 未跑 validation、未 commit / push、未进入 Step 12、未进入 3R-5 / 3R-6、
> 未新增 candidate、未复活 continuous_smoothing、未实际修任何 RISK。

---

## 1. 设计目的

让 **projection system 不再读取 exclusion_result，不再被否定系统改写**。

修复后的目标状态：

- `services/main_projection_layer.py` 的 `build_main_projection_layer()` 不接受
  `exclusion_result`、不调用 `_apply_exclusion`、**不**读取 exclusion 任何字段。
- `services/projection_orchestrator_v2.py` 与
  `services/home_terminal_orchestrator.py` 的判断装配链中，
  exclusion_result 与 projection_result **并列保留**，**不互相输入**。
- 用户可见展示链路（projection_three_systems_renderer / consistency_layer / UI）
  仍能并列展示 exclusion 与 projection；冲突由 confidence 系统评价（07C）。

本设计只产出**设计**，Step 12 才允许实施 +commit。

---

## 2. 当前违规路径

### 2.1 RISK-1 path（V2 主链路）

```
services/projection_orchestrator_v2.py:109
    exclusion_result = run_exclusion_layer(feature_payload)
services/projection_orchestrator_v2.py:110-115
    main_projection = build_main_projection_layer(
        current_20day_features=feature_payload,
        exclusion_result=exclusion_result,           ← 违规：projection 接收 exclusion
        historical_match_result=historical_match_result,
        peer_alignment=_as_dict(exclusion_result.get("peer_alignment")),
        symbol=symbol,
    )

services/main_projection_layer.py:362
    scores = _apply_exclusion(scores, _as_dict(exclusion_result), reasons)

services/main_projection_layer.py:255-274 _apply_exclusion(...)
    if triggered_rule == "exclude_big_up":
        adjusted["大涨"] = 0.0
        reasons.append("排除层已给出'明天不太可能大涨'，主推演层禁止将大涨排为 Top1。")
    elif triggered_rule == "exclude_big_down":
        adjusted["大跌"] = 0.0
        reasons.append("排除层已给出'明天不太可能大跌'，主推演层禁止将大跌排为 Top1。")
```

### 2.2 RISK-6 path（home terminal 入口）

```
services/home_terminal_orchestrator.py:22
    from services.exclusion_layer import run_exclusion_layer

services/home_terminal_orchestrator.py:145
    exclusion_result = run_exclusion_layer(feature_payload)

services/home_terminal_orchestrator.py:146-152
    main_projection = build_main_projection_layer(
        current_20day_features=feature_payload,
        exclusion_result=exclusion_result,           ← 违规：与 RISK-1 完全相同模式
        historical_match_result=historical_match_result,
        peer_alignment=as_dict(exclusion_result.get("peer_alignment")),
        symbol="AVGO",
    )

→ 触发 main_projection_layer.py:362 _apply_exclusion → 大涨 / 大跌 被置 0
```

### 2.3 二级隐式耦合（同一文件内）

```
services/main_projection_layer.py:13
    from services.exclusion_layer import build_peer_alignment    ← peer_alignment 计算
                                                                   被 import；技术上属于
                                                                   "市场特征衍生"而非
                                                                   exclusion 输出，但 import
                                                                   关系会让"projection
                                                                   不依赖 exclusion module"
                                                                   测试无法写得太严

services/main_projection_layer.py:316-317
    peer_payload = _as_dict(_as_dict(exclusion_result).get("peer_alignment"))
                                                                ← 第二个 leak：
                                                                   即使移除 _apply_exclusion，
                                                                   peer_alignment 仍从
                                                                   exclusion_result 取
```

> 即使删了 `_apply_exclusion`，line 316-317 的 fallback 仍构成"projection 读取
> exclusion_result"。Step 12 必须**同时**消除这两处。

### 2.4 app.py 调用链（确认 RISK-6 是 active path）

`grep "home_terminal_orchestrator"` 显示 `app.py` 与
`services/home_terminal_orchestrator.py` 是仅有的 active 引用点；前者通过后者
调起整条违规链路。

### 2.5 现有测试对违规行为的依赖

- `tests/test_main_projection_layer.py:28-30, 64-66, 100`：显式注入
  `exclusion_result={"excluded": True, "triggered_rule": "exclude_big_up"|"exclude_big_down"}`
  并断言 `大涨` / `大跌` 概率被压制。
- 这些测试**直接编码了违规行为**。Step 12 必须重写为 contract enforcement test。

---

## 3. 违反的 contract

| contract | 章节 | 违规点 |
|---|---|---|
| 06 三系统独立原则 | §3 推演定义 / §6 三系统正确关系 / §7 第 1 条 | 推演 / 否定平行独立；推演不读否定结果 |
| 07A | §3.2 禁止读取（exclusion_result）/ §5 禁止输出 / §6 推演与否定边界 / §10 禁止数据流（exclusion_result → projection_system） | projection 接收 exclusion 入参并写入 score 0 |
| 07B | §6 否定与推演边界（"不允许任何一方覆盖另一方"） | 否定 candidate 经 projection score 改写形成事实改写 |
| 07D | §6 final report 与推演边界 / §11 final_report → projection_system 禁流 | 即使经 final 层"展示"，回路仍闭合 |

---

## 4. 修复目标

修复后必须满足：

1. `build_main_projection_layer` 不再接收 `exclusion_result` 入参
   （实施可选：**移除参数** 或 **保留参数但 deprecate 并 ignore**；推荐移除）
2. `main_projection_layer.py` 内部**不再** `import` 任何 `services.exclusion_layer`
   的"非市场特征"符号（`run_exclusion_layer` / `build_peer_alignment` 都需要被审视；
   后者目前仍可保留，因为它的输入是市场特征，但需要重新评估 §5.6 节）
3. `main_projection_layer.py` 内部**不再** fallback 读取 `exclusion_result.peer_alignment`
   （§2.3 的 line 316-317 必须改）
4. `_apply_exclusion()` 函数被**禁用**（删除调用）或**完全移除**
5. `projection_orchestrator_v2.py:110-115` 调用 `build_main_projection_layer`
   时**不**传 `exclusion_result`、**不**从 exclusion_result 取 peer_alignment
6. `home_terminal_orchestrator.py:146-152` 同上
7. `exclusion_result` 仍由 `run_exclusion_layer(feature_payload)` 独立生成、
   独立保留在 orchestrator 输出的并列字段（`exclusion_result` / `projection_three_systems.negative_system`）
8. `services/consistency_layer.py` 仍可同时读 projection_result 与 exclusion_result
   做**冲突标注**（07D §6/§7 允许"标注"，禁止"改写"）；本次设计**不**改 consistency_layer
9. UI / `projection_three_systems_renderer.py` 的展示行为对外**等价**：
   仍展示"如果否定系统说大涨不可能"的标注，但不再修改推演的概率分布
10. 兼容性：保留 `predicted_top1` / `predicted_top2` / `state_probabilities` 字段
    schema 不变（Step 12 不破 UI 契约）

---

## 5. 最小代码修改设计

> 本节**只描述设计**，Step 12 才实施。

### 5.1 修改 `services/main_projection_layer.py`

- 在 `build_main_projection_layer()` 签名中，将 `exclusion_result` 标为
  **deprecated 且 ignored**（推荐写法：保留参数但函数体内部不再使用，
  并在 docstring 写明 "Deprecated: exclusion_result is no longer consumed."），
  或**直接移除**该参数。
  - **推荐**：保留参数但 ignored，**不实际使用**。这样可以：
    - 保持 call site 兼容性（最小 blast radius）
    - 让 contract test 直接断言"传入 exclusion_result 不影响 score"
    - 待 Step 14 cleanup 时再彻底移除参数（与 caller 同步）
- 删除函数内对 `_apply_exclusion(scores, _as_dict(exclusion_result), reasons)` 的调用
  （line 362）
- 保留 `_apply_exclusion` 函数定义本身**或**删除（推荐删除）；如保留则必须确保
  没有任何调用点
- 修改 line 316-317 的 peer_alignment fallback：
  - 不再从 `exclusion_result.get("peer_alignment")` 取
  - 直接 `peer_payload = build_peer_alignment(normalized)`（line 318 的 third-tier
    fallback 上提为唯一 fallback）
- `import` 行（line 13）`from services.exclusion_layer import build_peer_alignment`
  保留，但需在文档注释中明确：**这是市场特征派生函数，不是 exclusion 输出**；
  Step 12 时考虑是否把 `build_peer_alignment` 物理迁移到一个共享的
  `services/peer_alignment_features.py` 中以彻底切断 import 关系
  （**Step 12 不必强制做**；本轮仅记录建议）

### 5.2 修改 `services/projection_orchestrator_v2.py`

- line 109：`exclusion_result = run_exclusion_layer(feature_payload)` **保留**
  （exclusion 仍是独立子系统，要独立产出结果挂在 orchestrator 输出里）
- line 110-115：调用 `build_main_projection_layer` 时
  - **移除** `exclusion_result=exclusion_result` 参数（或改为传 `None`）
  - **移除** `peer_alignment=_as_dict(exclusion_result.get("peer_alignment"))`
    参数；改为不传（让 main_projection_layer 用 `build_peer_alignment(normalized)`
    自行计算）；或传 `peer_alignment=build_peer_alignment(feature_payload)` 显式传入
  - 保留 `current_20day_features` / `historical_match_result` / `symbol`
- 保留 line 117 之后的 `build_consistency_layer(...)` 调用：consistency_layer
  仍读 `exclusion_result` + `main_projection`，但只做**冲突标注**，不改写 main_projection
  （07D §6 / §7 允许）
- 保留 orchestrator 顶层输出中的 `exclusion_result` 字段（独立挂出）

### 5.3 修改 `services/home_terminal_orchestrator.py`

- line 22：`from services.exclusion_layer import run_exclusion_layer` **保留**
  （home_terminal 仍是聚合入口，需要独立调起 exclusion 子系统）
- line 145：`exclusion_result = run_exclusion_layer(feature_payload)` **保留**
- line 146-152：调用 `build_main_projection_layer` 时
  - **移除** `exclusion_result=exclusion_result`
  - **移除** `peer_alignment=as_dict(exclusion_result.get("peer_alignment"))`；
    改为不传或显式传 `build_peer_alignment(feature_payload)`
- 保留 line 153-158 `build_consistency_layer(...)` 调用：与 V2 同理
- 保留 line 173-183 `build_unified_projection_payload(... exclusion_result=...)`：
  顶层并列保留 exclusion 字段，给 UI 用

### 5.4 不动其他模块

- `services/exclusion_layer.py` **不动**：它是 ACTIVE_EXCLUSION 唯一合规入口
- `services/consistency_layer.py` **不动**：它是 aggregator 的合法位置（仅标注冲突）
- `services/projection_three_systems_renderer.py` **不动**：read-only reshape，
  CLEAN
- `app.py` **不动**：调用契约不破
- `ui/predict_tab.py` 等 **不动**：UI 字段 schema 不变

### 5.5 修改原则总结

- **删 4 行调用点**（main_projection_layer:362 一行 + projection_orchestrator_v2 一行 + home_terminal_orchestrator 一行 + main_projection_layer:316-317 改写一行）
- **删（或废弃）一个函数**：`_apply_exclusion`
- **不**改公开 schema
- **不**改 UI
- **不**改 consistency_layer（它的"标注"行为本就合规）
- **不**改 exclusion_layer

### 5.6 关于 `build_peer_alignment` import 的判断

- `services/main_projection_layer.py:13` `from services.exclusion_layer import build_peer_alignment`
- `build_peer_alignment` 的输入是**市场特征**（pos20 / vol_ratio20 / shadow_ratio /
  ret 等），输出是 peer 同行结构信号。
- 它**物理上**位于 `services/exclusion_layer.py`，但**逻辑上**是 07A §3.1
  白名单中"NVDA / SOXX / QQQ 同行确认"的衍生函数，属于推演侧白名单输入。
- 风险：未来 contract enforcement test 写"projection 不能 import exclusion_layer
  任何符号"时，会误伤这个合法 import。
- 设计选择：
  - **本次保留**：测试条件细化为"projection 不能从 exclusion_layer 读取
    exclusion_result 字段、不能调用 run_exclusion_layer"，而不是禁止整个 module 的 import。
  - **未来可选**（Step 14 cleanup 阶段）：物理迁移 `build_peer_alignment` 到
    `services/peer_alignment_features.py`，彻底解耦 import 关系。

---

## 6. 输出结构设计

修复后的 orchestrator 输出（V2 与 home_terminal 一致）：

```jsonc
{
  "kind": "projection_v2_raw" | "home_terminal_orchestrator_result",
  "symbol": "AVGO",
  "ready": true,

  // 推演结果（独立 raw，不被 exclusion 改写）
  "main_projection": {
    "predicted_top1": {"state": "...", "probability": 0.xx},
    "predicted_top2": {"state": "...", "probability": 0.xx},
    "state_probabilities": {
      "大涨": 0.xx,
      "小涨": 0.xx,
      "震荡": 0.xx,
      "小跌": 0.xx,
      "大跌": 0.xx
    },
    "rationale": ["..."],
    "warnings": [],
    "peer_alignment": {...},     // 来自 build_peer_alignment(features)，不来自 exclusion_result
    "feature_snapshot": {...}
  },

  // 否定结果（独立 raw，不影响 main_projection）
  "exclusion_result": {
    "excluded": false | true,
    "triggered_rule": "...",
    "reasons": [...],
    "kill_risk": "...",
    "peer_alignment": {...},     // exclusion_layer 自己计算的版本（与 main_projection.peer_alignment 可能相同来源）
    "feature_snapshot": {...}
  },

  // consistency 仅做冲突标注（不改写）
  "consistency": {
    "conflict_reasons": [...],
    "step_status": {...},
    "warnings": [...]
  },

  // 其他装配（preflight / final_decision / three_systems / narrative 等保留原样）
  ...
}
```

**禁止**的反模式：

```jsonc
// ❌ 不允许
{
  "main_projection": {
    "scores_after_exclusion": {...},          // 暗藏 exclusion 改写
    "raw_scores_before_exclusion": {...}      // 即使分两份留，仍说明 projection
                                              // 在做"应用 exclusion"，违规
  }
}

// ❌ 不允许
{
  "main_projection": {
    "state_probabilities": {
      "大涨": 0.0      // 0.0 是"被 _apply_exclusion 置 0"的结果
    }
  }
}
```

---

## 7. 兼容性风险

### 7.1 测试层

| 测试 | 当前依赖 | Step 12 处理 |
|---|---|---|
| `tests/test_main_projection_layer.py:28-30, 64-66, 100` | 注入 `exclusion_result.triggered_rule == exclude_big_up/down` 并断言 大涨/大跌 概率被压制 | **必须改写**为 contract enforcement test：断言"传入 exclusion_result 不改变 main_projection 输出"（参考 §8.1） |
| 其他依赖 `_apply_exclusion` 或断言 score=0 的测试 | grep 验证 | Step 12 实施前先 grep |
| `tests/test_projection_orchestrator_v2.py` | 可能断言 `peer_alignment` 来自 exclusion_result | 改为允许任意来源，只断言字段存在 |
| `tests/test_home_terminal_orchestrator.py`（如存在） | 同上 | 同上 |
| `tests/test_consistency_layer.py`（如存在） | consistency 仍读 exclusion_result + main_projection — **不变** | 保留 |

### 7.2 UI / 用户可见行为

- 旧行为：当 exclusion `triggered_rule == "exclude_big_up"` 时，UI 看到的
  Top1 不会是大涨（因为 score 被置 0）。
- 新行为：UI 看到的 Top1 仍由 projection 自身的市场特征决定；exclusion 的
  "最不可能"独立挂在 `exclusion_result` / 三系统并列展示中；冲突由 confidence
  系统评价 / consistency_layer 标注。
- **可能的 UX 差异**：用户原本"看到大涨被否定后，main projection 自动避开"
  的行为消失。新行为是"main projection 还是大涨，但 exclusion 同时标注'大涨
  最不可能'"。这是**契约要求的显式冲突展示**，而不是 bug。
- Step 12 实施时如果 UI 出现不期望的视觉反差，**不**回退；改善 UI 显式
  标注冲突（这是 07D 设计本意）。

### 7.3 summary / narrative 层

- `services/projection_narrative_renderer.py` / `services/predict_summary.py` /
  `services/projection_three_systems_renderer.py` 现读 `predicted_top1` /
  `state_probabilities`；这些字段 schema 不变，但取值会变（不再被 exclusion
  改写）。
- 如发现 narrative 文本里写"由于排除层 X 已禁止大涨，主推演降级为震荡"，
  Step 12 需同步改写文本生成逻辑（不要再说"由于 exclusion，所以…"）。

### 7.4 prediction_log

- `services/projection_chain_contract.build_prediction_log_record(...)` 接收
  `exclusion_result` 与 `main_projection`；写入并列日志字段。
- Schema 不变；仅日志中 `main_projection.state_probabilities` 取值不再带
  exclusion-induced zero。**不**清理历史 log（Step 14 才做）。

### 7.5 deprecated 字段保留

- 不引入新的 deprecated display-only 字段。Step 12 修复后输出本就是干净的
  并列结构；展示侧已有 `exclusion_result` 字段供 UI 使用。

---

## 8. Contract enforcement tests 设计

> 本节**只描述测试设计**，Step 12 才新增 / 修改测试代码。

### 8.1 必须新增 / 修改的测试

| 测试名（建议） | 验证内容 |
|---|---|
| `test_projection_layer_does_not_apply_exclusion` | 同一 `current_20day_features` 输入下，分别传入 `exclusion_result=None` / `exclusion_result={"excluded": True, "triggered_rule": "exclude_big_up"}` / `exclusion_result={"excluded": True, "triggered_rule": "exclude_big_down"}`，断言三次返回的 `state_probabilities` **完全相等**（key by key float equal） |
| `test_projection_layer_does_not_import_run_exclusion_layer` | 静态扫描 `services/main_projection_layer.py`，断言**没有** `from services.exclusion_layer import run_exclusion_layer` 或调用 `run_exclusion_layer(...)` |
| `test_projection_orchestrator_v2_keeps_projection_independent` | mock `run_exclusion_layer` 返回不同 `triggered_rule`，断言 `run_projection_v2(...)` 的 `main_projection.state_probabilities` 不随 mock 变化；并断言顶层输出包含**独立**的 `exclusion_result` 字段 |
| `test_home_terminal_orchestrator_keeps_projection_independent` | 同上，但针对 `build_home_terminal_orchestrator_result(...)` |
| `test_exclusion_result_not_used_as_projection_input` | 静态扫描 `build_main_projection_layer` 的调用点（projection_orchestrator_v2 + home_terminal_orchestrator），断言**没有** `exclusion_result=...` 关键字传入；同时 grep `main_projection_layer.py` 确认函数体不读 `exclusion_result` 字段 |
| `test_main_projection_peer_alignment_does_not_come_from_exclusion_result` | 断言 `main_projection_layer` 内部 peer_alignment fallback 链中不再包含 `exclusion_result.get("peer_alignment")` |
| `test_consistency_layer_still_reports_conflict` | 保留 / 加强现有 consistency_layer 测试：当 `main_projection.predicted_top1.state == "大涨"` 且 `exclusion_result.triggered_rule == "exclude_big_up"`，consistency 应**标注**冲突，但**不**修改 main_projection |

### 8.2 改写 / 删除的旧测试

| 旧测试 | 处理 |
|---|---|
| `tests/test_main_projection_layer.py:28-30, 64-66`（exclude_big_up / exclude_big_down 压制测试） | **改写**为 §8.1 中 `test_projection_layer_does_not_apply_exclusion` 的反向断言（即"传入 exclude_big_up 不影响 score"） |
| `tests/test_main_projection_layer.py:100`（excluded=False 不影响） | **保留**或合并到新测试中 |

### 8.3 测试不允许的内容

- 测试**不**应断言"exclusion 一定能改变 projection"
- 测试**不**应允许 `_apply_exclusion` 函数继续存在（如保留则视为 dead code，
  Step 14 cleanup）
- 测试**不**应放过 `peer_alignment` 从 `exclusion_result` 取的 fallback

---

## 9. 不允许的修复方式

以下修复方式**不**符合 contract，Step 12 实施时**禁止**：

1. **不**允许把 `exclusion_result` 改名后继续传入 projection
   （例如改成 `negative_signals` 再喂进 `main_projection` 仍是同样违规）
2. **不**允许在 `main_projection_layer` 内部偷偷读取
   `services.exclusion_layer.run_exclusion_layer` 的输出
3. **不**允许由 `final_report` / `consistency_layer` / aggregator 回写
   `main_projection` 的字段
4. **不**允许把 `exclusion score` 融进 `projection score`（即使做加权而非置 0
   也违规）
5. **不**允许为了让旧测试通过而**删掉** `exclusion_result` 的产出（exclusion
   仍是独立子系统，必须保留）
6. **不**允许复活 `continuous_smoothing` 作为 candidate 替代 `_apply_exclusion`
7. **不**允许顺手改 `services/final_decision.py` / `confidence_evaluator` /
   `ai_summary.py`（保留给 Step 11B / 11C / 11F + Step 12 各自的 commit）
8. **不**允许 cleanup 与 boundary fix 混在一起（不允许同 commit 删除 dead
   code、删除旧测试目录、清理 untracked logs 等）
9. **不**允许 large rewrite：禁止借机重写 `main_projection_layer` 的整体结构
10. **不**允许在 fix commit 中改 DB schema、迁移数据、跑 replay
11. **不**允许把 `_apply_exclusion` 的逻辑搬到 `consistency_layer` 改写
    `main_projection`（consistency_layer 只能"标注"不能"改写"）

---

## 10. Step 12 实施顺序建议

> Step 12 才允许执行；本轮**不**实施。

### 推荐顺序（commit-per-fix 内部子步骤）

1. **新增 contract enforcement tests（failing）**
   - 加 §8.1 列出的新测试；验证它们当前 fail（红灯）
   - 此时旧测试 §8.2 仍 pass
   - `git status` 仅多 test 文件

2. **修改 `services/main_projection_layer.py`**
   - 删除 line 362 `_apply_exclusion(scores, ...)` 调用
   - 删除（或保留为 dead code，Step 14 再删）`_apply_exclusion` 函数定义
   - 修改 line 316-317：peer_alignment fallback 链改为 `build_peer_alignment(normalized)`
   - 在 docstring 与 `build_main_projection_layer` 函数注释中标注
     "Deprecated: exclusion_result 不再被使用"
   - run focused tests：`pytest tests/test_main_projection_layer.py`

3. **修改 `services/projection_orchestrator_v2.py`**
   - line 110-115：移除 `exclusion_result=...` 与 `peer_alignment=...` 关键字
   - run focused tests：`pytest tests/test_projection_orchestrator_v2.py
     tests/test_projection_entrypoint*.py`

4. **修改 `services/home_terminal_orchestrator.py`**
   - line 146-152：同上
   - run focused tests：`pytest tests/test_home_terminal_orchestrator.py`
     （如存在）

5. **改写 §8.2 旧测试**
   - 把"断言大涨被压制"改写为"断言传入 exclusion_result 不改变 score"
   - run `pytest tests/test_main_projection_layer.py`

6. **跑全量 pytest**
   - `pytest tests/` 全量
   - 跑 `scripts/check.sh`（如存在）
   - 修一切因新边界产生的 narrative/UI 文本测试（最小改动）

7. **手动 spot-check UI**
   - 启动 Streamlit，验证 predict_tab / home_tab 仍能渲染
   - 验证 exclusion_result 仍在三系统并列段中可见

8. **独立 commit**
   - commit message：`fix(boundary): RISK-1+6 decouple projection from exclusion`
   - 单 commit；不混合任何 cleanup

### 不允许 inside Step 12 commit 的内容

- **不**删 `services/projection_orchestrator.py` 旧 V1 文件（quarantine 留 Step 14）
- **不**删 `services/_apply_exclusion` 函数本体（如保留为 dead code，Step 14 cleanup）
- **不**清 logs / DB backup / untracked
- **不**改 confidence / final_decision / ai_summary（保留各自 fix commit）
- **不**修 `services/projection_three_systems_renderer.py` schema（保留 RISK-3 设计）

---

## 11. 回滚策略

### 11.1 失败模式

如果在 Step 12 实施过程中：

- UI 出现**渲染错误**（例如 predict_tab 期待某个 score=0）
- narrative / summary 文本测试**大面积失败**（依赖"由于 exclusion 所以…"句式）
- 大量 prediction_log 测试断言**预期的压制**

### 11.2 回滚原则

> **不**回退 projection 吃 exclusion 的旧逻辑。

正确的回滚序列：

1. 回到 boundary fix 之前的 commit（`git revert <fix-commit>`）
2. 重新做最小修复：保留 main_projection 的 raw 输出
3. 把展示层调整为**并列**展示（在 UI / narrative 里同时显示
   "main projection: 大涨"+"exclusion: 大涨最不可能"）
4. 必要时在输出中保留**display-only** 字段（例如 `displayed_top1`），
   但**必须**显式标注：
   - 字段名前缀含 `display_*`
   - 字段 docstring 写明"非 projection 系统输出"
   - schema_version 不变
5. 任何回滚动作**仍不**允许 _apply_exclusion 重新生效

### 11.3 不允许的"回滚捷径"

- **不**允许悄悄恢复 `exclusion_result` 入参
- **不**允许把 exclusion-induced score=0 的逻辑迁移到 final_decision / consistency_layer
- **不**允许跳过 Step 11A 设计直接回到旧实现
- **不**允许在 fix commit 上做 `git commit --amend` 隐藏违规行为；必须
  显式 revert

---

## 12. 严守边界

本轮**只是设计**：

- 未改代码
- 未新增测试
- 未删文件
- 未移动文件
- 未写 DB
- 未改 DB schema
- 未跑 replay
- 未跑 validation
- 未处理 untracked / DB backup / stash / .claude/worktrees/
- 未进入 3R-5 / 3R-6
- 未新增任何 candidate
- 未复活 continuous_smoothing
- 未实际修复 RISK-1 / RISK-6（保留给 Step 12）
- 未触碰 RISK-2 / RISK-3 / RISK-7 / RISK-8 / RISK-9 / RISK-10（各自 11B–11G 设计）

本设计的修改路径：任何对 §4 修复目标、§5 最小代码修改、§8 测试设计、
§10 Step 12 实施顺序的调整，都必须以**显式更新本文件**的方式提出。
