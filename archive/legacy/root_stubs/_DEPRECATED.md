# Quarantined root v1 stubs

**These files are quarantined root-level v1 stubs. They are NOT active modules.**

Step 14B audit (commit `3808677`) confirmed **zero active imports** across the
entire repository. Step 14C decision (commit `c5dca5f`) selected
**Option B (quarantine to `archive/legacy/root_stubs/`)** over `git rm`. Step 14D
implementation `git mv`-ed the three files into this directory unchanged.

## Files

| file | step_1a purpose | active owner after Step 12 boundary fixes |
|---|---|---|
| `confidence_engine.py` | v1 stub: `evaluate_confidence(base_confidence, top1_margin, is_tail, has_conflict) -> str` (line-by-line down-weighting to "medium") | [`services/confidence_evaluator.py`](../../../services/confidence_evaluator.py) (Step 11C-A standalone evaluator) |
| `contradiction_engine.py` | v1 stub: `contradiction_score(prediction, signals) -> int` (+1 per `macro_bearish` / `volume_drop` / `nvda_down` / `overbought`) | `final_decision.decision_factors` / `confidence_evaluator` conflicting evidence channels (Step 11B / 11C) |
| `risk_model.py` | v1 stub: `calculate_risk_score(confidence, contradiction_count, volatility) -> float` (linear blend) | [`services/final_decision.py`](../../../services/final_decision.py) `risk_level` display + final report risk disclosure (Step 11B) |

## Hard rules

- **Do not import** these files. Step 12 boundary fixes routed all responsibilities
  to the active owners listed above. Re-importing them would re-introduce v1
  judgment paths that 11A–11G + 11E split out.
- **Do not add `__init__.py`** to `archive/`, `archive/legacy/`, or
  `archive/legacy/root_stubs/`. Adding it would turn this quarantine area into
  an importable package and silently re-enable the dead code.
- **Do not modify** these files. They are kept byte-identical to their
  pre-quarantine state for audit / rollback readability.
- **Do not move** `archive/legacy/root_stubs/` itself. The path is referenced
  from `tasks/record_14c_root_stubs_quarantine_delete_decision.md` and the
  cleanup commit history.
- **Do not edit** the 9 negative-import tests' `forbidden_modules` sets that
  list `"confidence_engine"` / `"contradiction_engine"` / `"risk_model"`.
  Those strings are permanent defenses; even after quarantine, any module that
  tries to import these names will be rejected at test time.

## Why kept (instead of `git rm`)

1. First-batch cleanup convention: audit → quarantine → stability window →
   delete. Step 14C §4 picked Option B to establish this template.
2. Historical docs (`tasks/record_08`, `record_10`, `record_12e_x5`,
   `step_2d_*`, `step_2f_*`, `record_14a`, `record_14b`, `record_14c`)
   reference these files by path. Keeping the bytes here makes those references
   directly readable without `git log -- <file>` archeology.
3. `git mv` rollback is a reverse `git mv`; `git rm` rollback requires
   `git revert` and is more disruptive on rebases / cherry-picks.

## Future deletion

Future deletion may be considered **only** after:

- Step 14E (test fixture hygiene plan), 14F (local artifact handling plan),
  and 14G (other cleanup commits) all land.
- A Step 13-style regression batch is re-run and stays green.
- A stability window of at least 4 weeks elapses without any need to consult
  these files.
- A separate, explicit user-approved `chore(cleanup): delete archive/legacy/root_stubs/<file>`
  commit per file is opened.

Until those gates are met, these files remain quarantined under this directory.
