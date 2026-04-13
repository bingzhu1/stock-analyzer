# Task 024 Builder Handoff — advanced_stats_output

## Context scanned
- `tasks/024_advanced_stats_output.md` — goal, scope, implementation suggestions
- `tasks/STATUS.md` — confirmed 023 done
- `.claude/handoffs/task_023_builder.md` — confirmed gap: stat_request parsed but not wired
- `services/stats_engine.py`, `services/comparison_engine.py`, `services/multi_symbol_view.py`
- `ui/command_bar.py` — run_compare_command and _render_compare_result
- `tests/test_stats_engine.py`, `tests/test_data_workbench_wiring.py`

## Changed files
- `services/stats_engine.py` — added `position_distribution()`
- `ui/command_bar.py` — wired stat_request in `run_compare_command`; updated `_render_compare_result`
- `tests/test_stats_engine.py` — 9 new tests (`PositionDistributionTests`)
- `tests/test_data_workbench_wiring.py` — 8 new tests (`RunCompareStatRequestTests` + 1 in existing class)
- `tasks/STATUS.md` — added 024 to canonical mapping and status table

## Implementation

### stats_engine.py
New `position_distribution(comparison_df, aligned_df, symbol) -> dict`:
- Filters comparison_df to matched rows only
- Checks `{symbol}_PosLabel` first (string labels)
- Falls back to `{symbol}_Pos30` (bucketed: ≥67→高位, 34-66→中位, ≤33→低位)
- Returns `{"高位": n, "中位": m, "低位": k, "total_matched": n+m+k, "label_source": ...}`
- Invariant: high + mid + low = total_matched (by construction — only labeled rows counted)

### command_bar.py
`run_compare_command()` changes:
1. When `stat_request.type == "distribution_by_label"`, adds "PosLabel" to view_fields so it appears in aligned_df
2. After computing comparison + stats, calls `position_distribution(comp_df, aligned, dist_sym)`
3. Result dict now always contains `position_dist` (None when no stat_request) and `stat_symbol`

`_render_compare_result()` changes:
- Stats row expanded to 4 columns (added 不一致 count)
- Position distribution section rendered when `position_dist` is not None and has data:
  - Caption shows symbol + label_source + total_matched count
  - Three metric columns: 高位 / 中位 / 低位 天
  - Extra caption when label_source is "Pos30" explaining buckets

## Validation
```
python -m unittest tests.test_stats_engine tests.test_data_workbench_wiring -v
# Ran 42 tests in 0.131s — OK

python -m unittest discover -s tests -p "test_*.py"
# Ran 310 tests — same 3 pre-existing failures, no new regressions

python -m py_compile services/stats_engine.py ui/command_bar.py  # OK
```

## Remaining risks
- Position distribution display only appears when `stat_request` is set by the parser; a plain "比较...走势" without stat keywords will not trigger it (expected behavior).
- PosLabel fallback to Pos30 is tested in unit tests but not in integration with real coded_data CSVs — Pos30 fallback would only fire if PosLabel is missing from the data (unlikely given `_enrich` always computes it).
- No AppTest coverage for the new distribution render path (Streamlit metrics) — visual verification recommended.
