---
description: "F04 — Replay tab, steps-this-affects preview, replay result, Try fixes drawer"
mode: agent
---
Read [Frontend design spec](../../docs/11-FRONTEND-DESIGN.md) sections 4 and 8 carefully. Reuse `JsonEditor`, `Drawer`, `StatChip`, `ExecutionRoute` (`highlight` prop), and the mock jobs in `src/mocks/handlers.ts`.

## Goal
Make replay and try-fixes work end to end with mocks — this is the core of the live demo.

## Tasks
1. **Replay tab** (8.1): explanation text, JSON editor prefilled with the step output (B612 Mono, line numbers, 14 lines, resizable), debounced validation message, Reset, "Steps this affects: N of M" from `useBlastRadius`, "Show on graph" toggle (affected nodes get caution outline, others fade to 40% with "will be reused" tooltip), "Regenerate this step" and "Replay from this step" buttons with disabled/loading states. While running, affected nodes pulse gently.
2. **Replay result panel** (8.2): pass / still-failing variants with exact copy, three stat chips, "Open replay" and "Compare with original" actions.
3. **Try fixes drawer** (8.3): 480px right drawer with backdrop; numbered list of top-3 likely causes in rank order; attempts stream in as the job progresses (spinner → check/cross, outcome word, stat chips, Compare link); plain-language strategy names from section 8.3; success panel or the "No fix worked" state with "Edit a step manually" (closes drawer, opens the Replay tab on rank 1). Esc closes; focus is trapped inside while open and returns to the trigger on close.
4. Wire the header's "Try fixes" button to open the drawer.

## Acceptance
- Hero run 1: edit `q1/retrieve#0`, preview shows 4 of 8 affected with q2 branch faded; replay returns "Fixed. 4 steps re-run, 4 reused, … tokens saved."; "Open replay" shows dashed reused nodes.
- Try fixes on hero run 1 streams three attempts and ends with "Fix found: wider search (k=6) on q1/retrieve#0."
- Invalid JSON disables replay and shows the line-specific error.
- `npm run build` passes.
