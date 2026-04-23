# 完成前检查

## 实施前
- [ ] 读过 `.claude/CLAUDE.md`, `PROJECT_STATUS.md`, `CHECKLIST.md`
- [ ] 读过 `tasks/STATUS.md`
- [ ] 读过对应 `tasks/{NNN}_{name}.md`
- [ ] builder follow-up 读过 `.claude/handoffs/task_{NNN}_reviewer.md` + `.claude/handoffs/task_{NNN}_tester.md`（如存在）
- [ ] reviewer/tester 读过 `.claude/handoffs/task_{NNN}_builder.md`

## 实施中
- [ ] 没改 task scope 里的 Forbidden 文件
- [ ] 如果改了 Forbidden 文件，是否在当前 task 补开 scope 变更说明？

## 实施后
- [ ] `bash scripts/check.sh` 通过
- [ ] 所有改动文件 `python -m py_compile` 通过
- [ ] 新增/受影响的测试全部通过
- [ ] 手动验证关键路径（如有 UI 变化）

## 输出
- [ ] plan
- [ ] changed files（列出文件 + 一句话说明改了什么）
- [ ] implementation summary
- [ ] validation steps
- [ ] risks / follow-ups

## 收尾
- [ ] 写 `.claude/handoffs/task_{NNN}_{role}.md`
- [ ] 如果 task 状态或 notes 改变，更新 `tasks/STATUS.md`
