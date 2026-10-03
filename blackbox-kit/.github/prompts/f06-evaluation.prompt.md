---
description: "F06 — Evaluation page"
mode: agent
---
Read [Frontend design spec](../../docs/11-FRONTEND-DESIGN.md) section 10. Use Recharts. Data from `useEval` (mocks for now).

## Goal
Build `/eval` so a judge understands in 10 seconds that the model works and beats the alternatives.

## Tasks
1. Title "Evaluation" and the one-line subtitle with the number of test questions.
2. `KpiRow`: five large B612 Mono numbers with plain-language captions, separated by vertical rules (not cards).
3. "Model vs. other approaches": grouped horizontal bars (top-1 solid, top-3 at 40% opacity), Black Box in orange, baselines graphite, value labels at bar ends, segmented control for Seen / Held-out / Natural, and the cost comparison sentence underneath.
4. Leave-one-out table with plain failure-type names and the subtle heat shading behind numbers.
5. Accuracy by failure type: horizontal bars, held-out types in advisory with a "Never seen in training" legend.
6. Cost of proving the cause: bisect vs checking every step, plus "Labels verified: N%".
7. Fixes row with the two numbers and a link to Runs filtered to fix attempts.
8. "How we tested" collapsible (closed by default) with four short paragraphs.
9. Layout: two-column grid for charts on wide screens, single column below 1100px. Charts must have accessible titles and a visually hidden data table fallback.

## Acceptance
- Readable at 1366×768 / 125% zoom from across a room: numbers large, labels not overlapping.
- Switching test sets animates bars only in response to the click (150 ms).
- `npm run build` passes.
