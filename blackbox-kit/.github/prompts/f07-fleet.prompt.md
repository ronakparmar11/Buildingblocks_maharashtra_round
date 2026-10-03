---
description: "F07 — Fleet page"
mode: agent
---
Read [Frontend design spec](../../docs/11-FRONTEND-DESIGN.md) section 11. Data from `useFleet` (mocks for now).

## Tasks
1. Generated headline sentence as the hero (`text-2xl`, heading style) from the largest bucket, plus the "Across N failed runs" line.
2. "Where failures start": horizontal bars by likely-cause step name with icons, sorted descending, top bar orange, others ink, percentage labels, counts on hover.
3. "Most common reasons": same bar style using reason text.
4. "By injected failure type": small table.
5. Clicking any bar navigates to the Runs page with the matching filters in the URL.
6. Loading, empty ("No failed runs yet. Generate runs to see patterns."), and error states.

## Acceptance
- Clicking the retrieve bar opens Runs filtered to failed runs whose likely cause is a retrieve step.
- `npm run build` passes.
