# Task 024 Reviewer Handoff — advanced_stats_output

## Context scanned
- `tasks/024_advanced_stats_output.md` — goal, scope, implementation shape
- `tasks/STATUS.md` — confirmed 023 done before 024 started
- `.claude/handoffs/task_024_builder.md` — 5 changed files, implementation details
- `services/stats_engine.py` — full content reviewed (new `position_distribution`)
- `ui/command_bar.py` — full content reviewed (wiring + render changes)
- `tests/test_stats_engine.py` — full content reviewed (9 new PositionDistributionTests)
- `tests/test_data_workbench_wiring.py` — full content reviewed (8 new RunCompareStatRequestTests)
- `services/multi_symbol_view.py` — verified `{sym}_{field}` column naming convention

## Findings

### F1 — `total_matched` in position_distribution ≠ stats["matched"] when some dates lack PosLabel [LOW]
- **Why it matters**: `position_distribution` sets `total_matched = high + mid + low` (only labeled days). If any matched dates are absent from `aligned_df` after the left merge (or have NaN PosLabel), `total_matched < stats["matched"]`. The UI caption says "共 N 天" using `pos_dist["total_matched"]`, while the stats row shows a different "方向一致" count. Users could see two different numbers for what appears to be the same value.
- **In practice**: `_enrich` always populates PosLabel per builder and Task 022 context, so the mismatch is unlikely with real data. But it's untested.
- **Suggested fix**: Add a debug assertion or at minimum use `stats["matched"]` as the denominator in the caption, showing labeled/total (e.g., "共 N/M 天有位置标签"). Low urgency.

### F2 — `comparison_df["match"] == True` instead of boolean filter [LOW]
- **Why it matters**: `comparison_df["match"] == True` works correctly for boolean dtype but is slightly unidiomatic for pandas. `comparison_df["match"]` alone (or `.astype(bool)`) is more conventional and immune to nullable boolean types.
- **Suggested fix**: `matched = comparison_df[comparison_df["match"]]`. Cosmetic only.

### F3 — No AppTest for position distribution render path [LOW]
- **Why it matters**: `_render_compare_result`'s new 4-column stats row and position distribution block are only reachable through Streamlit rendering. The new metrics and `st.caption` calls cannot be covered by the unit test suite.
- **Builder noted**: Explicitly flagged. Acceptable for MVP.
- **Suggested fix**: Add a `test_command_bar_apptest.py` case for a compare command with stat_request in a future task.

### F4 — PosLabel field flow through `load_symbol_data` not integration-tested [LOW]
- **Why it matters**: `run_compare_command` adds "PosLabel" to `view_fields` and passes it to `build_aligned_view` → `load_symbol_data`. Whether real coded_data CSVs expose PosLabel through the loader's `fields` filter is not covered by any test (only mocked via `_fake_loader_with_pos`). If the loader silently drops unknown fields, `aligned_df` won't have `{symbol}_PosLabel` and `position_distribution` will fall back to Pos30.
- **Builder noted**: Explicitly flagged as known risk.
- **Suggested fix**: Verify with a spot-check against a real coded_data CSV. Low urgency given PosLabel is always present in `_enrich` output.

### F5 — Task file `## Status` not updated [LOW]
- **Why it matters**: `tasks/024_advanced_stats_output.md` still has no status update from the builder (recurring pattern from tasks 011, 021, 022).
- **Suggested fix**: Tester should set status to `done` on completion.

## Verified correct
- Scope boundary clean: only `stats_engine.py`, `command_bar.py`, and tests changed. No parser, no projection, no scanner/predict/encoder files touched. ✓
- `position_distribution` label-source priority: PosLabel first, Pos30 fallback. ✓
- Bucketing: `≥67→高位`, `34–66→中位`, `≤33→低位` matches task spec. Boundary values 67 and 33 covered by `test_pos30_boundary_values`. ✓
- Invariant `高位 + 中位 + 低位 = total_matched` tested explicitly. ✓
- Unmatched rows excluded (left-merged on `matched` dates only). ✓
- `run_compare_command` adds "PosLabel" to view_fields only when `stat_request.type == "distribution_by_label"` — plain compare commands unaffected. ✓
- `position_dist = None` when no stat_request; `_render_compare_result` only shows distribution block when `pos_dist is not None and total_matched > 0`. ✓
- `test_stat_request_wrong_type_no_position_dist` — non-distribution stat types don't trigger dist block. ✓
- Stats row expanded from 3 to 4 columns (added 不一致 count) — in scope, addresses Task 022 reviewer's noted gap. ✓
- Task 022/023 capabilities unaffected: 310 total tests, same 3 pre-existing failures, 0 new regressions. ✓
- `build_aligned_view` confirmed to produce `{sym}_{field}` columns (e.g., `AVGO_PosLabel`) matching what `position_distribution` looks for. ✓

## Merge recommendation

**MERGE** — no HIGH or MEDIUM findings. Core feature (compare summary + position distribution) correctly implemented and tested. Label source priority matches spec. Invariant enforced by construction. No forbidden files touched. No scope creep. Known gaps (AppTest render coverage, real-data integration) are acceptable for MVP and explicitly acknowledged.
