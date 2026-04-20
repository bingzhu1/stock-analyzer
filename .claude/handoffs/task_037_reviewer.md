# Task 037 Reviewer Handoff - ai_intent_parser_fallback_mvp

## Status
PASS

## Date
2026-04-20

## findings

1. Rule-first / AI-second boundary is present and narrow. `services/ai_intent_parser.py` keeps deterministic parsing as the first layer, only triggers AI on unknown-intent or unresolved OHLCV/all-data cases, and safely degrades to the rule result on API failure, bad JSON, unsupported intents, or malformed shapes.
2. The structured-output contract is implemented and validated. Supported intents are constrained to `query`, `compare`, `stats`, `projection`, and `ai_explain`; result validation rejects unsupported intent/operation/confidence values and unstable list/scalar shapes before merge.
3. The requested validation surface is present in `tests/test_ai_intent_parser.py`: all-data/OHLCV resolution, stats, compare, projection, ai_explain, and multiple safe-degradation paths are covered.
4. Validation gap for this review pass: I did not execute the tests in this environment, so this is a code-review pass rather than a runtime-confirmed tester pass.

## severity

- review outcome: pass to tester
- remaining risk: low, limited to runtime verification rather than design or scope issues

## why it matters

Task 037's purpose is to improve understanding-layer robustness without letting AI bypass the existing parser/router safety rails. The current implementation appears to honor that contract: AI is constrained to structured parsing, fallback entry conditions are limited, and the merge path preserves rule-parsed values where already available.

## suggested fix

- No code fix required from reviewer.
- Next agent should run the focused test suite and, if green, add tester handoff and mark Task 037 done.

## merge recommendation

recommendation: move Task 037 to `in-test`.

## Required actions for next agent
- Run focused validation for `tests/test_ai_intent_parser.py` and any directly related parser/planner regressions.
- If tests pass, write `.claude/handoffs/task_037_tester.md` and update `tasks/STATUS.md` to `done`.
- If tests fail, keep Task 037 at `in-test` or move back to `blocked` with concrete failing cases.
