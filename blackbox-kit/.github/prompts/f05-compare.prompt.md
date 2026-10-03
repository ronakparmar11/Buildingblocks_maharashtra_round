---
description: "F05 — Compare page"
mode: agent
---
Read [Frontend design spec](../../docs/11-FRONTEND-DESIGN.md) section 9. Reuse `ExecutionRoute` (`compact` mode), `OutcomeChip`, `WordDiff`, `StepKey`.

## Goal
Build `/compare?a=&b=`.

## Tasks
1. Back link to run B (or A if B missing), title "Compare runs".
2. Two outcome cards (run ID, outcome chip, "Got …") with a plain ink connecting line; generated summary sentence ("First difference at q1/retrieve#0. 4 steps changed, 13 identical.").
3. Compact non-interactive route of run B (180px, no grid): changed nodes caution, identical nodes ghost, first difference with an orange marker.
4. Table: Step, Status chip, Original summary, Replay summary. "All steps / Changed only" segmented control (default Changed only when > 8 rows).
5. Expandable changed rows with an inline word diff (deletions: warning text, `#F9DEE2` background, strikethrough; insertions: normal text on normal-tint), plus "Show JSON diff" for a side-by-side JSON view. First-difference row expanded by default with a 3px orange left border.
6. States: missing query params ("Pick two runs to compare. Open a replay and choose Compare with original."), loading, error.

## Acceptance
- From hero run 1's replay → "Compare with original" lands here with first difference `q1/retrieve#0` and the extract answer diff "British" → "American".
- `npm run build` passes.
