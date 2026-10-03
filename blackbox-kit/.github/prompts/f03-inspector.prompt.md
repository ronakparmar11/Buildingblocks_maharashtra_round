---
description: "F03 — Run detail inspector: Why, I/O, State tabs"
mode: agent
---
Read [Frontend design spec](../../docs/11-FRONTEND-DESIGN.md) sections 4 and 7.6. Reuse existing components (`Tabs`, `JsonViewer`, `PassageCard`, `StepKey`, `Popover`).

## Goal
Build the inspector panel in the right column of Run detail with the Why, I/O, and State tabs. (Replay tab is F04 — add the tab with a placeholder.)

## Tasks
1. Inspector header: step key (B612 Mono `text-lg`), step type with icon, and "Most likely cause" (orange) or "Rank 2/3" (caution) with score.
2. Tabs (underline style): Why, I/O, State, Replay. Default to Why for ranked steps, I/O otherwise. Remember the last chosen tab while switching steps.
3. **Why tab:** summary sentence ("This step is the most likely cause. Fixing it would change N later steps." — N from blast radius), up to 3 reason blocks (reason sentence `text-md`, evidence quote block with left border, thin relative contribution bar), "How this score is calculated" popover, and the not-ranked message with links to top suspects.
4. **I/O tab:** collapsible Input/Output with `JsonViewer` (collapsible keys, wrap strings, clamp long strings to 4 lines with "Show more"), copy buttons; retrieval steps show passages as `PassageCard`s with a "Raw JSON" switch; meta row (latency, tokens in/out, model, "From recording"/"Re-run"/"Cached").
5. **State tab:** plan as a numbered list of sub-questions, sub-answers table, attempts, final answer.
6. Empty inspector (nothing selected): short prompt "Select a step on the route or the tape to inspect it." with a button "Show most likely cause" when a diagnosis exists.
7. Below 900px wide, render the inspector as a bottom sheet.

## Acceptance
- On hero run 1, selecting `q1/retrieve#0` shows three readable reasons with evidence; selecting `plan` shows the not-ranked message.
- Retrieval passages render as cards; long passages clamp and expand.
- Keyboard: Tab through tabs and controls with visible focus.
- `npm run build` passes.
