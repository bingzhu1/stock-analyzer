# Task 06R — System Audit + Safe Cleanup

- **Date:** 2026-04-27
- **Worktree:** `.claude/worktrees/sad-antonelli-49e876`
- **Branch:** `claude/sad-antonelli-49e876`
- **Status:** done (audit + safe cleanup landed; no git add / commit performed)

## Goal
对当前 AVGO projection 系统做一次全面体检，并安全清理明确的垃圾文件；产出审计报告。

## Allowed this round
- 只读审计；
- 清理明确安全的垃圾文件（仅 `__pycache__/` × 5 + `.pytest_cache/`）；
- 生成系统审计报告。

## Forbidden this round (all respected)
- 改预测规则；
- 改 production 逻辑；
- 删除 replay 正式产物；
- 删除任务报告；
- 删除核心数据；
- 删除测试；
- 重跑 full replay；
- 做 production cutover；
- 自动 `git add` / `commit`；
- 创建本轮发现缺失的 replay 目录或合成 artifacts；
- 修改 `.gitignore`（即便发现条目缺失/重复也只记 follow-up）。

---

## 一、Git 状态审计

### Tracked modifications (3 files, +86 lines)

| File | Source |
|------|--------|
| `services/projection_entrypoint.py` | Task 06Q (additive +76 lines) |
| `tasks/STATUS.md` | Task 06Q (mapping + row) |
| `tests/test_projection_entrypoint.py` | Task 06Q (strict-eq update for new field) |

### Untracked paths (5, all from Task 06Q)
- `.claude/handoffs/` — directory + `task_06Q_builder.md`
- `services/projection_three_systems_renderer.py`
- `tasks/06Q_projection_output_three_systems.md`
- `tests/test_projection_entrypoint_three_systems.py`
- `tests/test_projection_three_systems_renderer.py`

### Verdict
工作树 100% 由 Task 06Q 拥有，无遗留脏改、无意外触碰禁区文件、无 stray scratch 文件。Git diff 与未追踪清单一致。

---

## 二、核心健康检查

| Check | Command | Exit | Result |
|---|---|---|---|
| Services compile | `python3 -m py_compile services/*.py` | 0 | All `services/*.py` clean |
| Scripts compile | `python3 -m py_compile scripts/*.py` | 0 | Only `scripts/run_e2e_loop.py` exists; clean |
| Project check | `bash scripts/check.sh` | 0 | "All compile checks passed." |

### Note
`scripts/check.sh` 只 hard-list 了 19 个文件，未自动覆盖新增 service 模块（如 `projection_three_systems_renderer.py`、`projection_orchestrator_v2.py`、`final_decision.py`）。这些新模块在 wildcard `services/*.py` py_compile 中均通过，但 `check.sh` 不会自动识别新增。**Follow-up #1**：考虑改成 `find services -name '*.py' -exec python3 -m py_compile {} +` 以避免新模块漏检。

---

## 二补充、关键测试

| # | Test file | Status | Result |
|---|---|---|---|
| 1 | `tests/test_experimental_rule_r7.py` | ❌ NOT FOUND | 文件不存在 |
| 2 | `tests/test_projection_three_systems_renderer.py` | ✅ | 17 passed in 0.02s |
| 3 | `tests/test_projection_entrypoint_three_systems.py` | ✅ | 4 passed in 0.68s |
| 4 | `tests/test_projection_review_closed_loop.py` | ✅ | 57 passed in 0.07s |
| 5 | `tests/test_projection_orchestrator_v2.py` | ✅ | 12 passed in 0.41s |

**Aggregate (4 of 5 found): 90 tests pass, 0 fail.**

### ⚠ Audit finding A — `test_experimental_rule_r7.py` missing
- 文件不存在；
- `grep -rln "R7C_K1\|experimental_rule\|R7C\|r7c_k1" tests/ services/` 无任何命中；
- 但 `.claude/CLAUDE.md` 列了 "不要改 R7C_K1 逻辑" 作为 hard rule。

**Implication：当前仓库没有 R7C_K1 / experimental_rule 的代码或测试，CLAUDE.md 的对应 hard rule 在本仓库内没有实际落地物可保护。** 已写入下方 risk / human-confirmation list，本轮不创建文件、不创建测试。

---

## 三、核心产物完整性检查

### Required directories — **ALL MISSING**

| Required path | Exists? |
|---|:---:|
| `logs/historical_training/06H_full_1005day_replay_baseline/` | ❌ |
| `logs/historical_training/06J_r7_experimental_replay/` | ❌ |
| `logs/historical_training/06J3_r7c_experimental_replay/` | ❌ |
| `logs/historical_training/06L_k1_bullish_exhaustion_replay/` | ❌ |
| `logs/historical_training/06M_r7c_k1_combined_replay/` | ❌ |

### Verifications
- `logs/` 整个目录在 worktree 根下不存在；
- `find . -type d -iname "*historical_training*" -not -path "./.git/*"` 返回 0 hits；
- 文件名匹配 `06H*`、`06J*`、`06L*`、`06M*` 全部 0 hits；
- `grep -rln "06H_full_1005day\|06J_r7_experimental\|06J3_r7c\|06L_k1\|06M_r7c_k1\|historical_training" --include="*.py" --include="*.md" --include="*.json"` 0 hits；
- 唯一相关代码资产是 `services/historical_replay_training.py` + 其测试，但未与 `logs/historical_training/` 建立写入路径。

### ⚠ Audit finding B — formal replay artifacts entirely absent
本仓库未承载 R7 / R7C / K1 / R7C_K1 实验回放轨道的任何正式产物。可能性：
- 它们存放在另一份 worktree / 另一台机器；
- 或本 clone 从未生成；
- 或 06H / 06J / 06J3 / 06L / 06M 的产出被外部归档。

按本轮 hard rule，不创建目录、不合成 artifacts、不重跑 replay。已写入下方 human-confirmation list。

---

## 四、垃圾文件扫描（cleanup 前）

| Pattern | Count | Total size | Tracked? | In `.gitignore`? |
|---|---:|---:|---|---|
| `__pycache__/` directories | 5 | ~1.8 MB | No | ✅ `__pycache__/` |
| `*.pyc` files | 97 (all 在 `__pycache__/` 内) | (含上) | No | ✅ `*.pyc` |
| `.DS_Store` files | 0 | — | n/a | ✅ (但条目重复声明 2 次) |
| `.pytest_cache/` | 1 (root) | 24 KB | No | ❌ **不在 `.gitignore`** |
| Empty directories | 0 | — | n/a | n/a |
| `*.tmp` | 0 | — | n/a | n/a |
| `*.bak` | 0 | — | n/a | n/a |

### Cache dir 明细
```
__pycache__/             252 KB
ui/__pycache__/          176 KB
tests/__pycache__/       276 KB
scripts/__pycache__/      16 KB
services/__pycache__/   1.1 MB
.pytest_cache/            24 KB
```

总计可回收约 **1.82 MB**。

---

## 五、安全清理执行 + 后置验证

### 实际执行命令
```bash
rm -rf ./__pycache__ ./ui/__pycache__ ./tests/__pycache__ ./scripts/__pycache__ ./services/__pycache__   # exit 0
rm -rf ./.pytest_cache                                                                                   # exit 0
```

### Post-cleanup verification

| Check | Result |
|---|---|
| `find . -type d -name "__pycache__"` | **0 hits**（曾 5） |
| `find . -type f -name "*.pyc"` | **0 files**（曾 97） |
| `find . -type d -name ".pytest_cache"` | **0 hits**（曾 1） |
| `git status --short` | **完全等同于清理前**：3 修改 + 5 未追踪，全部归属 Task 06Q |
| `bash scripts/check.sh` | **exit 0** — "All compile checks passed." |

### 没动到的东西（按 hard rule）
- 没有 `git add` / `git commit`；
- 没有改 `.gitignore`；
- 没有改 predict / scanner / matcher / encoder / feature_builder / final_decision / 规则层；
- 没有删任何 test、task、handoff、replay artifact、核心数据；
- 没有创建 `logs/` 目录或合成 replay 数据；
- 没有重跑 replay；
- 没有做 production cutover。

---

## 六、风险 / 人工确认清单（Human-Confirmation List）

按发现紧急程度排序：

### H1 · R7C_K1 hard rule has no in-repo enforcement
**事实**：CLAUDE.md 列 "不要改 R7C_K1 逻辑"，但 `tests/test_experimental_rule_r7.py` 不存在，`R7C_K1 / experimental_rule / R7C / r7c_k1` grep 无命中。  
**人工确认**：是否需要确认 R7C_K1 仍在 roadmap、是否需要补 enforcement test、还是更新 CLAUDE.md 移除该条 hard rule？

### H2 · Formal replay artifacts entirely absent in this worktree
**事实**：`logs/historical_training/` 不存在，06H / 06J / 06J3 / 06L / 06M 5 个 replay 目录全缺失，仓库内无任何引用。  
**人工确认**：这些产物是否应存在于本 worktree？若是，从哪里 sync 进来？若不是（外部归档），是否更新 PROJECT_STATUS.md 或某 README 标注其位置？

### H3 · `tests/test_projection_entrypoint.py` 内 2 个 live-network 测试残留
**事实**：`test_empty_state_calls_orchestrator_chain`、`test_returns_orchestrated_result_without_changing_meaning` 直调 `run_projection_entrypoint(symbol="avgo")` 不 mock `run_projection_v2`，离线必失败。Task 06Q 已标注，未修。  
**人工确认**：是否在 follow-up 任务中改成 mocked tests？memory `feedback_tests_no_live_network.md` 已记录。

---

## 七、Follow-ups（不在本轮处理）

1. 改 `scripts/check.sh` 用通配/递归扫描，避免新增 service 模块漏检。
2. 在 `.gitignore` 增加 `.pytest_cache/`；并去重 `.DS_Store` 条目。
3. （H1）补 `tests/test_experimental_rule_r7.py` 或更新 CLAUDE.md。
4. （H2）核实 06H / 06J / 06J3 / 06L / 06M replay 产物位置；如需要，写一个明确 `tasks/STATUS.md` 行说明它们外部归档。
5. （H3）把 `tests/test_projection_entrypoint.py` 的 2 个 live-network 测试改 mock。
6. 评估是否需要把 06Q 的 `projection_three_systems` 字段挂进 `ui/`（目前只有 contract，UI 未读）。

---

## 八、Sign-off

- 所有审计步骤按指令顺序完成；
- 清理仅限授权范围内的 5×`__pycache__` + `.pytest_cache`；
- 仓库健康（compile / focused tests）保持绿色；
- 无 `git add` / `commit`；
- 无禁区文件改动；
- 报告即本文件，路径：`tasks/06R_system_audit_safe_cleanup.md`。
