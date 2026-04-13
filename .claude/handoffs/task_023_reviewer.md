# Task 023 Reviewer Handoff — command_parser_enhancement

## Context scanned
- `tasks/023_command_parser_enhancement.md` — 7 target sentences, scope
- `tasks/STATUS.md` — confirmed 023 in-review
- `.claude/handoffs/task_023_builder.md` — 3 changed files, implementation details
- `services/command_parser.py` — full content reviewed
- `tests/test_command_parser.py` — full content reviewed (71 tests, 26 new)

## Findings

### F1 — `stat_request` not wired into execution [LOW]
- **Why it matters**: `_extract_stat_request()` is called and the field is populated, but `command_bar.py` still ignores it. Users who enter "各多少天" sentences will get no visual output for the stat.
- **Suggested fix**: Tracked as known gap from task 022; wire `stat_request` into the workbench executor in a future task.
- **Builder noted**: Yes — explicitly flagged in builder handoff.

### F2 — `_extract_stat_request` called unconditionally for all task types [LOW]
- **Why it matters**: A `run_projection` or `run_review` command could theoretically set `stat_request`, which is semantically odd (though harmless — unused by any executor today).
- **Suggested fix**: Guard with `if task_type in ("query_data", "compare_data")` before calling `_extract_stat_request`. Low urgency while stat execution is not wired.

### F3 — Task file status still `todo`, no history entry [LOW]
- **Why it matters**: `tasks/023_command_parser_enhancement.md` still has `## Status: todo` — builder did not update it after implementation.
- **Suggested fix**: Tester or next agent should update the task file status to `done` on completion.

### F4 — `stat_request` uses untyped `dict` [LOW]
- **Why it matters**: No schema enforcement; callers must guess shape. As stat types grow, this becomes error-prone.
- **Suggested fix**: Define a `StatRequest` TypedDict with `type`, optional `symbol`, optional `field` keys. Low urgency for a rule-based parser.

### F5 — `不一致天数` / `一致天数` check order is correct but fragile [LOW]
- **Why it matters**: `不一致天数` must be checked before `一致天数` because the latter is a substring of the former. Currently ordered correctly, but the ordering dependency is implicit.
- **Suggested fix**: Add a comment noting the ordering constraint, or use `re.search(r"不一致天数")` to make it explicit.

## Verified correct
- All 7 target sentences parse to the expected (task_type, symbols, window, stat_request) combinations — verified against test_s1 through test_s7.
- `下一个交易日` wins over bare `20天` in window extraction (S7 test confirms priority).
- Symbol inference (`rfind` with ceiling) correctly resolves AVGO even when NVDA appears earlier in the sentence.
- No forbidden files touched (`app.py`, `scanner.py`, `encoder.py`, `predict.py`, `research.py` untouched).
- Backward compatibility confirmed: `stat_request` defaults to `None`; all 45 pre-existing tests unaffected.
- 71/71 parser tests pass; 293-test suite shows only 3 pre-existing failures (none new).

## Merge recommendation

**MERGE** — no HIGH or MEDIUM findings. All 7 target sentences handled correctly. Implementation is backward-compatible. Known gap (stat execution not wired) is appropriately tracked.
