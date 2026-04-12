# Handoff Files — 协作说明

## 用途
每个 agent 完成工作后，将结果写入固定 md 文件。
后续 agent 通过读取这些文件接力，不依赖对话历史。

---

## Source of truth

Canonical task 文件在 `tasks/` 目录，当前稳定编号如下：

| task_id | canonical task |
|---------|----------------|
| 001 | `tasks/001_prediction_store.md` |
| 002 | `tasks/002_outcome_capture.md` |
| 003 | `tasks/003_review_agent.md` |
| 004 | `tasks/004_research_loop_ui.md` |
| 005 | `tasks/005_task_system_cleanup.md` |
| 006 | `tasks/006_fix_task001_blockers.md` |

正式 task 只放在 `tasks/`。不要再创建 `.claude/tasks/`。

旧 task 文件已归档到 `.claude/legacy_tasks/`，只作历史参考；如果编号冲突，以 `tasks/STATUS.md` 和 `tasks/{NNN}_{name}.md` 为准。

---

## 命名规则

```markdown
task_{NNN}_{role}.md
```

- `NNN` — 三位数 task 编号（001, 002, …）
- `role` — `builder` | `reviewer` | `tester`

示例：
```markdown
task_001_builder.md
task_001_reviewer.md
task_001_tester.md
```

---

## 谁写 / 谁读

| agent | 写入 | 开始前读 |
|-------|------|---------|
| builder | `task_{NNN}_builder.md` | `tasks/{NNN}_{name}.md` |
| builder follow-up | `task_{NNN}_builder.md` | `tasks/{NNN}_{name}.md`, `task_{NNN}_reviewer.md`, `task_{NNN}_tester.md`（如存在） |
| reviewer | `task_{NNN}_reviewer.md` | `tasks/{NNN}_{name}.md`, `task_{NNN}_builder.md` |
| tester | `task_{NNN}_tester.md` | `tasks/{NNN}_{name}.md`, `task_{NNN}_builder.md` |

所有 agent 都需要读取并在状态变化时更新 `tasks/STATUS.md`。

---

## 每个文件必须包含

```markdown
## Status
PASS | NEEDS_FIXES | BLOCKED

## Date
YYYY-MM-DD

## What was done / found
(简短正文)

## Required actions for next agent
- 具体行动项（没有则写 None）
```

可直接复制这些模板：

- `TEMPLATE_builder.md`
- `TEMPLATE_reviewer.md`
- `TEMPLATE_tester.md`

---

## 何时更新 tasks/STATUS.md

- builder 完成实现 → 改 status 为 `in-review`
- reviewer 通过 → 改 status 为 `in-test`
- tester 通过 → 改 status 为 `done`
- 任何 agent 发现 blocker → 改 status 为 `blocked`，填 notes
- 只改文档说明、未改变 task 实际状态时，可以只更新 notes 或保持不变

---

## 每轮使用方式

1. 先在 `tasks/` 写清楚本轮 task，确认 scope、Allowed、Forbidden、Done when；不要在 `.claude/tasks/` 新建 task。
2. builder 先读 task；如果是 follow-up，再读 reviewer + tester handoff，然后写回 `task_{NNN}_builder.md`。
3. reviewer 读 task + builder handoff，然后写回 `task_{NNN}_reviewer.md`。
4. tester 读 task + builder handoff，然后写回 `task_{NNN}_tester.md`。
5. 每个 agent 在 task 状态发生变化时更新 `tasks/STATUS.md`。

---

## 示例文件位置

```text
.claude/handoffs/
  task_001_builder.md   <- task 001 的真实产出
  task_001_reviewer.md  <- task 001 的真实产出
  task_001_tester.md    <- task 001 的真实产出
```
