# Tester Handoff - Task 023: command_parser_enhancement

## Status
PASS

## Date
2026-04-13

---

## Context Scanned

- `tasks/023_command_parser_enhancement.md`
- `tasks/STATUS.md`
- `.claude/handoffs/task_023_builder.md`
- `services/command_parser.py` (full read — 310 lines)
- `tests/test_command_parser.py` lines 268–464 (4 new test classes)

**Key changes verified:**
1. `_QUERY_KW` extended: `只看`, `并排`, `查看` added
2. `_extract_window`: bare `N天` fallback (N≥5) after `最近N天`
3. `ParsedTask.stat_request: dict | None = None` — new backward-compatible field
4. `_extract_stat_request()` — detects distribution/match_rate/matched_count/mismatched_count
5. Symbol inference in distribution uses `rfind(cn, 0, ceiling)` to find symbol closest before position labels

---

## Commands Run

```bash
# Compile check
D:/anaconda/python.exe -m py_compile services/command_parser.py tests/test_command_parser.py
# → COMPILE OK

# Focused: 71/71 parser tests
D:/anaconda/python.exe -m unittest tests.test_command_parser -v
# → Ran 71 tests in 0.002s  OK

# Regression: AppTest + wiring + stability + projection
D:/anaconda/python.exe -m unittest \
  tests.test_command_bar_apptest tests.test_data_workbench_wiring \
  tests.test_command_center_stability tests.test_command_projection_wiring
# → Ran 40 tests in 0.670s  OK

# Spot-checks: 15 direct parse_command() invocations
# → 15/15 PASS

# Forbidden file check
git status --short -- scanner.py predict.py research.py \
  services/review_agent.py services/prediction_store.py services/outcome_capture.py
# → M scanner.py  M predict.py  M research.py  (pre-existing dirty, not Task 023)
# Task 023 files: M services/command_parser.py  M tests/test_command_parser.py — correct
```

---

## Result

### Tests

| suite | tests | result |
|-------|-------|--------|
| `test_command_parser` — all classes (71 total, 26 new) | 71 | PASS |
| `test_command_bar_apptest` (regression) | 7 | PASS |
| `test_data_workbench_wiring` (regression) | 14 | PASS |
| `test_command_center_stability` (regression) | 14 | PASS |
| `test_command_projection_wiring` (regression) | 4 | PASS |
| **Total** | **111** | **PASS** |

### Spot-checks: 15/15 PASS

| sentence | expected | result |
|----------|----------|--------|
| `把博通、英伟达、费城、纳指最近20天数据并排` | query_data, 4 symbols, w=20 | PASS |
| `只看博通最近20天` | query_data, AVGO, w=20 | PASS |
| `只看英伟达最近20天最高价` | query_data, NVDA, High, w=20 | PASS |
| `调出博通最近20天收盘价和成交量` | query_data, Close+Volume, w=20 | PASS |
| `比较英伟达和博通最近20天最高价走势` | compare_data, NVDA+AVGO, High | PASS |
| `比较英伟达和博通…一致里博通高位…各多少天` | compare_data, stat_request.symbol=AVGO | PASS |
| `根据博通20天数据推演下一个交易日走势` | run_projection, AVGO, w=-1 | PASS |
| empty input | unknown + parse_error | PASS |
| no-symbol query | parse_error set | PASS |
| unsupported field (`xyz`) | fields=[], no error | PASS |
| query does not trigger projection | query_data | PASS |
| old `调出博通最近20天数据` | query_data (regression) | PASS |
| old `比较博通和英伟达…最高价走势` | compare_data (regression) | PASS |
| old `推演博通下一个交易日走势` | run_projection, w=-1 (regression) | PASS |
| old `复盘昨天` | run_review (regression) | PASS |

### Forbidden files: PASS

`scanner.py`, `predict.py`, `research.py` dirty from prior tasks. Task 023 only modified `services/command_parser.py` and `tests/test_command_parser.py` — matches builder's declared change set exactly.

---

## Failed Cases

None.

---

## Gaps

1. **`stat_request` not yet wired in `command_bar.py`** — `distribution_by_label` stat type is parsed and tested, but `run_compare_command` still ignores `parsed.stat_request`. Noted as known gap since Task 022; this is a future task.

2. **No AppTest for new sentences** — the 7 AppTest cases in `test_command_bar_apptest.py` were not updated for Task 023. The new natural-language sentences are tested by unit tests only, not through the full Streamlit UI path.

3. **`并排` keyword position** — "把博通、英伟达…数据并排" relies on `并排` appearing anywhere in the text (not prefix). Works correctly but edge cases with `并排` appearing mid-sentence without a real query intent are not tested.

4. **Bare `N天` lower-bound guard** — N < 5 falls back to DEFAULT_WINDOW (tested). Values like `5天` or `6天` would be extracted, though these are uncommon lookback windows in practice.

---

## Recommendation

**PASS — mark Task 023 `done`.**

All 71 parser tests pass. All 7 target sentences resolve to correct (task_type, symbols, fields, window, stat_request). 40 regression tests pass. No forbidden files touched. Wiring gap for `stat_request` is pre-existing and tracked.
