# Task 06S-H1 — Hard-Rule Layer Audit (Recovered Branch)

- **Date:** 2026-04-27
- **Branch audited:** `recover/experimental-replay-work`
- **Files audited:** `data_fetcher.py`, `feature_builder.py`, `encoder.py`, `services/data_query.py`
- **Mode:** read-only diff inspection + focused tests; **no code changes, no commits, no stash drop, no replay**

## TL;DR

| File | Nature of change | Hard-rule breaking? |
|---|---|---|
| `data_fetcher.py` | Pure ADDITIVE — adds Adj Close to fetch / cleaning; backwards-compatible | ❌ No |
| `feature_builder.py` | ADDITIVE for raw features (O_gap / H_up / L_down / C_move / V_ratio bytewise unchanged); adds new `PrevAdjClose`, `C_adj` columns | ❌ No |
| `encoder.py` | ⚠️ **C_code semantics changed when `C_adj` is present** — uses dividend-adjusted return instead of raw close-to-open (gated on data availability with raw fallback) | ⚠️ **Yes (deliberate, gated, tested)** |
| `services/data_query.py` | ⚠️ `_enrich` uses Adj Close for return / position computations when present (auto-gated, no opt-in flag) | ⚠️ **Behavior change** for queries on dividend-bearing data |

**Bottom line: this is a coherent, deliberate "dual-price-track" feature, not random drift. It does change one of the five 5-digit code positions (the C position) on dividend-bearing days, but the change is gated on data availability and old CSVs continue to produce the original C_code. 72 / 72 focused tests pass. It is not destructive, but it is a hard-rule extension that requires explicit acknowledgment and should ship as its own atomic foundation PR before any other recovered PR.**

---

## 一、Diff overview (`git diff --stat`)

```
 data_fetcher.py        | 16 +++++++++++++---
 encoder.py             | 21 ++++++++++++++++-----
 feature_builder.py     | 31 ++++++++++++++++++++++++++-----
 services/data_query.py |  6 ++++--
 4 files changed, 59 insertions(+), 15 deletions(-)
```

Net change is small (~74 lines combined) — manageable for review. All four files share the same theme: **introducing an "Adj Close" track in parallel to the raw price track**, with the raw track preserved bytewise and the adjusted track gated on `Adj Close` being present in source CSVs.

Key tokens located in the diff:
- `KEEP_COLUMNS` — extended in `data_fetcher.py`
- `Adj Close` — introduced as canonical column name across all 4 files
- `PrevClose` — kept on raw `Close` (unchanged)
- `PrevAdjClose` — new column, sourced from adjusted close shifted by 1
- `C_adj` — new column, equals `(Adj Close − PrevAdjClose) / PrevAdjClose`
- `C_move` — kept on raw OC % (unchanged)
- `V_ratio` — unchanged
- `O_gap` — **explicitly preserved** as `(Open − PrevClose) / PrevClose`, now with a code comment "always raw price"
- `target_date` — **not touched** (no diff hits in `services/data_query.py` for that helper)
- `tail(window)` — no occurrences in the diff
- `rolling` — only `Volume.shift(1).rolling(20).mean()`, identical to original
- `shift` — all `.shift(1)`, **no `.shift(-1)` or any forward shift**
- `lookahead` — no introduction; backward-only shifts preserved

---

## 二、Per-file analysis

### 1. `data_fetcher.py` — ADDITIVE, fully backwards-compatible

**What changed**
- `KEEP_COLUMNS` adds `"Adj Close"` (placed between `"Close"` and `"Volume"`).
- New name-normalization block in `clean_price_data` to canonicalize yfinance variants (`"adj close"` / `"adjclose"` / `"adj_close"` → `"Adj Close"`).
- `pd.to_numeric` loop now also coerces `"Adj Close"`.
- Final return is `cleaned[[col for col in KEEP_COLUMNS if col in cleaned.columns]]` — graceful when Adj Close is absent.

**Answers to required questions**
| Question | Answer |
|---|---|
| Only adds Adj Close? | ✅ Yes |
| Changes download range? | ❌ No |
| Changes Open / High / Low / Close / Volume raw columns? | ❌ No (raw OHLCV identical) |
| Affects old CSV compatibility? | ❌ No (return list filters to columns that exist) |

**Verdict**: ✅ Safe additive change. Old CSVs still load identically. New CSVs additionally carry an `Adj Close` column.

---

### 2. `feature_builder.py` — ADDITIVE for raw features, NEW columns for adj track

**What changed**
- `BASE_COLUMNS` now `["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]`.
- New `_REQUIRED_BASE = ["Date", "Open", "High", "Low", "Close", "Volume"]` — Adj Close is **optional**.
- `FEATURE_COLUMNS` adds `"PrevAdjClose"` and `"C_adj"`.
- `load_price_csv`: missing-column check uses `_REQUIRED_BASE`; reads only base columns that exist.
- `build_features` adds:
  ```python
  has_adj = "Adj Close" in result.columns and result["Adj Close"].notna().any()
  adj_close_series = result["Adj Close"] if has_adj else result["Close"]
  result["PrevAdjClose"] = adj_close_series.shift(1)
  result["C_adj"] = (adj_close_series - result["PrevAdjClose"]) / result["PrevAdjClose"]
  ```
  Returns `available_base + FEATURE_COLUMNS`.

**Critical observation**: the raw OHLC features are byte-identical to before:
```python
result["O_gap"]  = (result["Open"] - result["PrevClose"]) / result["PrevClose"]   # raw
result["H_up"]   = (result["High"] - result["Open"])  / result["Open"]            # raw
result["L_down"] = (result["Open"] - result["Low"])   / result["Open"]            # raw
result["C_move"] = (result["Close"] - result["Open"]) / result["Open"]            # raw
result["V_ratio"] = result["Volume"] / result["MA20_Volume"]                       # raw
```
A code comment explicitly notes "O_gap: always raw price (Open vs prev raw Close)". `PrevClose` continues to use raw `Close`.

**Answers to required questions**
| Question | Answer |
|---|---|
| Only retains / passes Adj Close? | Mostly — also computes derived `PrevAdjClose` and `C_adj` (new columns) |
| Changes O_gap calculation? | ❌ No — still `(Open − PrevClose) / PrevClose` on raw |
| O_gap still based on previous **raw** Close? | ✅ Yes — `PrevClose = result["Close"].shift(1)` (raw) |
| `PrevAdjClose` mixed in? | ❌ No — `PrevAdjClose` is computed but NOT used by O_gap or any raw feature |
| Changes rolling features? | ❌ No — `Volume.shift(1).rolling(20).mean()` identical to original |
| Lookahead? | ❌ No — only `.shift(1)` (backward), nowhere is `.shift(-1)` or any tail-of-future used |

**Verdict**: ✅ Safe extension. Original 5 features unchanged. New parallel `C_adj` track added without disturbing raw track.

---

### 3. `encoder.py` — ⚠️ C_code semantics CHANGE (gated, deliberate)

**What changed**
- New `_OPTIONAL_COLUMNS = ["Adj Close", "PrevAdjClose", "C_adj"]`.
- `load_feature_csv`: includes optional columns when present, coerces them to numeric.
- **Critical encode change** in `encode_dataframe`:
  ```python
  # Use C_adj (dividend-adjusted daily return) when available; fall back to C_move
  c_source = result["C_adj"] if "C_adj" in result.columns else result["C_move"]
  result["C_code"] = c_source.apply(encode_c_move).astype("Int64")
  ```
- O_code, H_code, L_code, V_code unchanged.
- Date stringification wrapped with `hasattr(result["Date"], "dt")` for robustness — semantic-neutral.
- Return now appends present optional columns alongside `REQUIRED_COLUMNS + CODE_COLUMNS`.

**Answers to required questions**
| Question | Answer |
|---|---|
| Changes 5-digit code definition? | ⚠️ **Yes — for the C position only.** C_code is now derived from `C_adj` (adjusted return) when available, falling back to `C_move` (raw return) otherwise. The other 4 positions (O, H, L, V) are unchanged. |
| O / H / L / C / V five-digit positions still under old rule? | O, H, L, V: ✅ unchanged. C: ⚠️ gated change. |
| Only retains Adj Close / new columns? | ❌ No — actively uses `C_adj` to compute C_code |
| Changes thresholds (`encode_o_gap`, `encode_h_up`, `encode_l_down`, `encode_c_move`, `encode_v_ratio`)? | ❌ No — same threshold functions, same bin boundaries; only the **input series** to `encode_c_move` changes |

**Replay-comparability impact**
- For days with no dividend / split, `C_adj == C_move` exactly; **C_code identical**.
- For days carrying a dividend or split, `C_adj ≠ C_move`; **C_code can differ by ±1 bucket** depending on whether the adjustment crosses a threshold.
- For CSVs without Adj Close (legacy data), behavior reverts to the original C_move path — **byte-identical** to pre-change encoding.

The tests confirm this exact design: `tests/test_dual_price_track.py` opens with the AVGO 2026-04-23 reference where `Close == Adj Close` because that day had no dividend or split, so the dual-track produces identical outputs. The two columns are designed to **diverge only on dividend / split days**.

**Verdict**: ⚠️ **Hard-rule extension, not hard-rule break.** Deliberate, documented, tested, gated, backwards-compatible. Does change the 5-digit code's C position on dividend-bearing days — needs explicit acknowledgment.

---

### 4. `services/data_query.py` — ⚠️ Auto-gated query behavior change

**What changed**
- `_CSV_FIELDS` adds `"Adj Close"` to the recognized field set.
- `_enrich` switches `close = df["Close"]` to `close = df["Adj Close"] if "Adj Close" in df.columns else df["Close"]`.

**Answers to required questions**
| Question | Answer |
|---|---|
| Only `target_date` / field helper? | ❌ No — modifies `_enrich`'s price source for derivations |
| Affects default OHLCV query? | Raw OHLCV columns surfaced as-is, but **derived** values inside `_enrich` (returns, position, etc.) now switch to Adj Close when present |
| Changes default UI data? | ⚠️ **Yes, transitively** — any UI that reads enriched returns / position via `data_query` will see adjusted values on rows where Adj Close exists. |
| Related to 06E walk-forward fix? | Not visibly — diff has no walk-forward markers; this looks like part of the dual-price-track feature, not 06E |

**Verdict**: ⚠️ Auto-gated behavior change. Old data paths still work, but UI outputs computed via `_enrich` will silently shift to Adj Close-based when CSVs include the column. Should be flagged in the PR description that downstream display values may shift on dividend-bearing days.

---

## 三、Focused tests — all green

```
tests/test_dual_price_track.py            ┐
tests/test_historical_training_no_lookahead.py  ├ 55 passed in 1.14s
tests/test_matcher_v2.py                  ┘
tests/test_data_query.py                  → 17 passed in 0.63s
                                            ─────────────────
                                            72 / 72 passed
```

`tests/test_dual_price_track.py` is the dedicated coverage for this feature. Its file-header comment documents the AVGO 2026-04-23 anchor case where adjusted and raw close are equal (because no dividend / split that day) and explicitly explains the divergence rule on dividend / split days. This is a strong signal that the change is intentional, designed, and tested — not accidental drift.

`tests/test_historical_training_no_lookahead.py` passing is the lookahead guard. No future leak introduced.

---

## 四、Cross-cutting verdict

| Question | Answer |
|---|---|
| Changes 5-digit code? | ⚠️ Yes — C position only; gated on `C_adj` presence; raw fallback preserves legacy behavior |
| Changes O_gap semantics? | ❌ No — still raw `(Open − PrevClose) / PrevClose` |
| Introduces lookahead? | ❌ No — all shifts are `.shift(1)` (backward-only); rolling stays `Volume.shift(1).rolling(20).mean()` |
| Affects replay comparability? | ⚠️ Conditional. Existing replays built from legacy CSVs (no Adj Close) are byte-identical. Future replays built from CSVs with Adj Close will diverge on dividend / split days. **Cross-track comparison for dividend-bearing symbols is no longer apples-to-apples.** |
| Can enter a future PR? | ✅ Yes — but must be its OWN foundation PR, not bundled |
| Should be split into a separate PR? | ✅ **Yes — strongly recommend a dedicated `PR-0: dual-price-track foundation`** containing exactly these 4 files + `tests/test_dual_price_track.py` + the 2026-04-23 reference comment |
| Recommend reverting any of the 4? | ❌ No — none of the changes are destructive or accidental. All are coherent parts of the dual-price-track feature. |

---

## 五、Recommendations

### 5.1 Land as a dedicated foundation PR (PR-0) before any other recovered PR

Suggested scope of PR-0:
- `data_fetcher.py` (additive)
- `feature_builder.py` (additive for raw, new adj columns)
- `encoder.py` (gated C_code change)
- `services/data_query.py` (auto-gated query change)
- `tests/test_dual_price_track.py` (the dedicated coverage)
- a 1-line addition to `tasks/STATUS.md` for the dual-price-track task entry

PR-0 must call out, in the description, the two semantic changes:
1. C_code position now reflects dividend-adjusted return on days where `C_adj` is present.
2. `services/data_query._enrich` now uses Adj Close for derived returns / position when present.

### 5.2 Sequence after PR-0

Once PR-0 lands, the previously proposed PRs from 06S can proceed:
- PR-A (Task 03 / 3A-3C5 / 2E exclusion-accuracy chain)
- PR-B (Task 04A-04E2 research scripts) — deferred to H6 logs decision
- PR-C (Contradiction-card / big-up / big-down)
- PR-D (Cache + macro + earnings + regime + direction-threshold)
- PR-E (UI revision)

The reason PR-0 is foundational: every subsequent PR's tests and replay outputs were generated against data that has Adj Close, so they implicitly depend on the dual-price-track being in place.

### 5.3 Do NOT revert any of the four files

None of the changes are bugs or accidents. All are part of a coherent feature. The right action is **acknowledge + PR-0 + descriptive PR body**, not revert.

### 5.4 What to confirm with the human before filing PR-0

1. Is the dual-price-track an intentional feature? (Tests + comments strongly suggest yes; needs explicit confirmation.)
2. Is the C_code semantic change on dividend days acceptable, given that it changes the 5-digit code on those days?
3. Is the silent shift in `services/data_query._enrich` acceptable, or should it be made an explicit opt-in flag?

---

## 六、Builder Report

| | |
|---|---|
| `data_fetcher.py` | Pure ADDITIVE; backwards-compatible. **Not** hard-rule breaking. |
| `feature_builder.py` | ADDITIVE for raw features; new `PrevAdjClose` + `C_adj` columns. **Not** hard-rule breaking. No lookahead. |
| `encoder.py` | C_code now uses `C_adj` when available, falling back to `C_move`. **Hard-rule extension**, not break. Other 4 code positions unchanged. |
| `services/data_query.py` | `_enrich` auto-switches to Adj Close when present. **Behavior change** for downstream queries on dividend-bearing rows. |
| Hard-rule breaking? | **No catastrophic break.** Yes, the 5-digit code's C position differs on dividend / split days when Adj Close is present — but this is gated, deliberate, and tested. Treat as a hard-rule **extension** that needs explicit acknowledgment. |
| Tests | 72 / 72 passed across `test_dual_price_track`, `test_historical_training_no_lookahead`, `test_matcher_v2`, `test_data_query`. |
| Replay comparability | Existing replays unaffected (legacy CSVs hit fallback path). Future replays with Adj Close will differ from legacy on dividend / split days. |
| Lookahead introduced? | No. |
| Recommend revert? | No. |
| Recommend split PR? | Yes — dedicated PR-0 foundation containing these 4 files + dual-price-track tests, before PR-A through PR-E. |

### Single biggest thing for the human to decide
**Is the C_code semantic change on dividend / split days acceptable?** If yes → file PR-0 with the description spelling out the two gated changes, then proceed with PR-A→E. If no → stash these 4 files separately, file PR-A→E without them, and decide later whether to graft Adj Close onto a different code position or reject the dual-price-track design entirely.

### Sign-off
- Read-only audit only;
- No `git add` / `commit` / `push` / `stash drop`;
- No code modification (these 4 files are exactly as recovered from `stash@{0}`);
- No full replay rerun;
- Report path: `tasks/06S_H1_hard_rule_layer_audit.md`.
