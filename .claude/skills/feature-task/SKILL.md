---
name: feature-task
description: Execute a scoped implementation task for the AVGO stock analyzer with minimal repo-local changes.
---

先读取：
- @.claude/PROJECT_STATUS.md
- @.claude/TASK_TEMPLATE.md
- @.claude/CHECKLIST.md

工作原则：
- 先读相关文件，再给出 plan
- 优先最小改动
- 不覆盖已有内容，除非明确冲突
- 仅在当前仓库内操作
- 不做无关重构

输出顺序：
1. plan
2. changed files
3. implementation summary
4. validation steps
5. risks / follow-ups
