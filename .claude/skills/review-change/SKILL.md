---
name: review-change
description: Review AVGO code changes for bugs, regressions, assumptions, and validation gaps.
---

先读取：
- @.claude/PROJECT_STATUS.md
- @.claude/CHECKLIST.md

审查重点：
- 功能正确性和回归风险
- 边界条件与错误处理
- 数据或指标计算是否合理
- 命名、结构、可维护性
- 验证是否充分

输出顺序：
1. findings
2. why it matters
3. suggested fix
4. validation gaps
