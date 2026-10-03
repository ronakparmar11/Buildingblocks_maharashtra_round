---
description: "P15 — Replay editor, blast radius, auto-repair drawer, Compare page"
mode: agent
---
Read [UI spec](../../docs/08-UI.md) sections "Run Detail" (Replay tab), "Replay result", "Auto-repair panel", "Compare".

## Task
1. Inspector **Replay** tab: JSON textarea prefilled with the step output, live JSON validation, "Show blast radius" (calls blast-radius endpoint; highlights affected nodes in the graph, dims the rest), "Replay from here" → POST replay → result card: outcome change, "Re-executed X · Reused Y · Saved Z tokens", buttons Open run / Compare.
2. In replay runs, the graph renders reused nodes ghosted and executed nodes solid, with a legend.
3. **Auto-repair drawer:** start job, poll, list attempts as they complete (step_key · strategy · outcome · executed/reused), highlight the winner with a Compare button.
4. **Compare page** `/compare?a=&b=`: banner (outcome A → B, first divergence), mini graph of B with changed nodes highlighted, aligned table with status chips, expandable rows with an inline word diff (npm `diff`, green insertions / red deletions).
5. "Compare with parent" button on replay/repair runs.

## Acceptance
Full loop works in mock mode: open failed run → edit a step → replay → result card → compare page shows the diff. Then test against the real API. `npm run build` passes.
