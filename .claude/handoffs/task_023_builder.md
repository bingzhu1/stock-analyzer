# Task 023 Builder Handoff — command_parser_enhancement

## Context scanned
- `tasks/023_command_parser_enhancement.md` — goal, 7 target sentences, scope
- `services/command_parser.py` — existing MVP parser
- `tests/test_command_parser.py` — existing 45 tests
- `tasks/STATUS.md` — confirmed 022 done before starting

## Changed files
- `services/command_parser.py` — enhanced parser
- `tests/test_command_parser.py` — 26 new tests (4 new classes)
- `tasks/STATUS.md` — added 023 to canonical mapping and status table

## Implementation

### command_parser.py changes
1. **New query keywords** — added `只看`, `并排`, `查看` to `_QUERY_KW` tuple; enables "只看博通最近20天", "把…并排", "查看…数据" to resolve as `query_data`
2. **Bare N天 window fallback** — added second regex fallback in `_extract_window`: `(\d+)天` with `N >= 5` guard, so "根据博通20天数据推演" extracts window=20
3. **`stat_request` field on ParsedTask** — new `stat_request: dict | None = None` dataclass field (default None, backward-compatible)
4. **`_extract_stat_request()` function** — detects 4 stat patterns:
   - `各多少天` → `{"type": "distribution_by_label", "symbol": ..., "field": "PosLabel"}`
   - `一致率` → `{"type": "match_rate"}`
   - `不一致天数` → `{"type": "mismatched_count"}`
   - `一致天数` → `{"type": "matched_count"}`
5. **Symbol inference fix** — distribution_by_label uses `rfind(cn, 0, ceiling)` where `ceiling = min(position of 高位/中位/低位)`. This correctly picks the symbol whose last occurrence precedes the position labels (e.g. "一致里博通高位" → AVGO even when NVDA appeared earlier in the sentence).

### test_command_parser.py additions
- `NaturalLanguageSentenceTests` (7 tests) — one per target sentence from task spec
- `StatRequestExtractionTests` (9 tests) — distribution, match_rate, matched_count, mismatched_count, None cases, symbol inference
- `WindowExtensionTests` (5 tests) — bare N天 extraction, priority ordering
- `NewQueryKeywordTests` (5 tests) — 只看, 并排, 查看 trigger query_data

## Validation
```
python -m unittest tests.test_command_parser -v
# Ran 71 tests in 0.002s — OK

python -m unittest discover -s tests -p "test_*.py"
# Ran 293 tests — 2 failures + 1 error, all pre-existing:
#   test_executor_replies_to_unsupported_without_analysis  (pre-existing, noted in PROJECT_STATUS.md)
#   test_save_and_get_outcome  (task 001 blocked, pre-existing)
#   test_chat_help_request_returns_schema_help  (pre-existing)
# No new failures introduced.

python -m py_compile services/command_parser.py  # OK
```

## Remaining risks
- `distribution_by_label` stat type is parsed but not yet wired into command execution (command_bar.py still ignores `stat_request`). Tracked as known gap from task 022.
- Parser is rule-based; novel phrasings outside the keyword/alias tables will fall through to `unknown`.
- `stat_request` symbol inference requires the symbol to appear in the sentence; pure positional inference (e.g. "一致里高位") falls back to first extracted symbol.
