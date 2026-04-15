# AGENTS.md

## Purpose
This repository uses builder / reviewer / tester style workflows.  
When working in this repo, always prefer small, scoped, verifiable changes.

---

## General working style
1. Read first, change second.
2. Before editing code, scan the task file and the most relevant implementation files.
3. Keep changes minimal and within task scope.
4. Do not rewrite unrelated systems.
5. Prefer deterministic behavior over clever behavior.
6. Preserve existing product behavior unless the task explicitly changes it.

---

## Required workflow for coding tasks

### Phase 1 — Read and confirm
Before making any code changes, first read:
- the requested task file in `tasks/`
- `tasks/STATUS.md`
- the most relevant existing implementation files
- the most relevant existing tests
- recent handoffs if they are directly related

Then pause and summarize:
- which files were read
- what the task goal is
- what files are likely to change
- what the main risks are

Do **not** start coding before doing this.

### Phase 2 — Implement
When implementing:
- only change files directly relevant to the task
- do not expand scope without a strong reason
- avoid large refactors
- keep UI changes small unless explicitly requested
- keep scanner / predict / projection core logic unchanged unless the task explicitly targets them

### Phase 3 — Validate
After implementation:
- run focused validation first
- run broader checks only if appropriate
- prefer task-specific tests over unrelated full-suite churn
- report clearly what passed, what failed, and what is pre-existing

### Phase 4 — Handoff
Write a short handoff file when requested.  
Use this format unless the task says otherwise:
- context scanned
- changed files
- implementation
- validation
- remaining risks

---

## Scope discipline
Unless explicitly requested, do **not**:
- redesign the architecture
- rewrite core scanner logic
- rewrite core predict logic
- rewrite core projection logic
- do broad cleanup refactors
- rename files or move systems around
- silently change product semantics

When in doubt, choose the smaller change.

---

## Parser / planner / router rules
For command-center style tasks:
- rule-based parsing remains the first layer unless the task explicitly says otherwise
- AI should be a fallback, not the default, unless explicitly requested
- router logic should execute existing tools, not replace them
- avoid hidden magical behavior
- if a command is ambiguous, prefer safe fallback or a clear warning over guessing

---

## AI integration rules
When integrating AI:
- AI must not directly invent market facts
- AI must not replace deterministic core logic unless explicitly requested
- AI fallback should return structured output when possible
- invalid AI output must safely degrade
- never allow malformed AI output to break the main flow
- validate types and required fields before merging AI output into execution

---

## UI rules
For Streamlit UI work:
- avoid nested expanders
- avoid unstable placeholder switching when possible
- prefer stable `st.container()` section layouts
- use consistent section ordering
- do not mix unrelated result types in the same unstable render slot
- if raw output is needed, prefer a single folding section

---

## Data safety rules
When touching data pipelines:
- never generate fake market prices unless the task explicitly asks for synthetic test data
- preserve raw input semantics
- do not silently overwrite real data with placeholder values
- be especially careful around refresh / fetch / clean pipelines
- if a change can affect encoded historical results, call it out explicitly

---

## Testing rules
Always add or update focused tests when behavior changes.

Prefer:
- parser tests for parser changes
- router tests for routing changes
- UI/AppTest only for relevant UI behavior
- regression tests for previously broken cases

If broader unrelated tests fail:
- identify whether they are pre-existing
- do not claim they were fixed unless you fixed them
- do not hide failures

---

## Output style
When reporting results, keep it concise and structured.

Use:
- changed files
- implementation
- validation
- remaining risks

Do not add long essays unless requested.

---

## Good defaults
When not sure:
- read more before changing
- choose minimal diffs
- preserve existing behavior
- prefer explicit warnings over hidden guessing
- keep the repo easier to reason about after your change