# AVGO Stock Analyzer

## Mission
这个项目的目标是把现有工具升级成 AVGO research agent，不是普通 dashboard。

## Current phase
当前只做第一版 research loop：
prediction log / outcome capture / review generation

## Hard rules
1. 不要让 LLM 决定股票方向
2. scanner / matcher / encoder 属于硬规则层，优先保留
3. 本轮 app.py 只允许最小改动
4. 新逻辑优先放 services/ 或 ui/
5. 所有 AI 输出必须结构化
6. 改完必须运行统一检查脚本

## Required reading
- `.claude/PROJECT_STATUS.md`
- `.claude/CHECKLIST.md`
- `tasks/STATUS.md` — 当前所有 task 状态
- 对应 `tasks/{NNN}_{name}.md` — 当前 task 的 goal / scope / requirements
- builder follow-up: `.claude/handoffs/task_{NNN}_reviewer.md` + `.claude/handoffs/task_{NNN}_tester.md`（如存在）
- reviewer: `.claude/handoffs/task_{NNN}_builder.md`
- tester: `.claude/handoffs/task_{NNN}_builder.md`

## Handoff system
每轮结束后，把结果写入 `.claude/handoffs/task_{NNN}_{role}.md`。
命名和格式规则见 `.claude/handoffs/README.md`。
任何 agent 改变 task 状态时，都需要更新 `tasks/STATUS.md` 中的 status 字段和 notes。

## Task source of truth
正式 task 只放在 `tasks/`。
不要再创建 `.claude/tasks/`；历史 task 已归档到 `.claude/legacy_tasks/`，只在追溯旧编号冲突时参考。

## Required output
- plan
- changed files
- implementation summary
- validation steps
- risks / follow-ups
