---
description: "P16 — Evaluation and Fleet insights pages"
mode: agent
---
Read [UI spec](../../docs/08-UI.md) sections "Evaluation" and "Fleet insights", and the `eval.json` structure produced in P10/P12.

## Task
1. `/eval`: KPI cards; grouped bar chart (Recharts) of model vs. baselines for Top-1 and Top-3 per test set; LOFO table; per-fault-type bars; replay savings (bisect replays vs. linear scan, reused % distribution); auto-repair metrics; a short "How we evaluated" note (split by task, held-out types, organic labels by counterfactual resampling). Highlight the model's bars in orange, baselines grey.
2. `/fleet`: headline sentence computed from data ("41% of failures originate in retrieval"); bar charts by culprit step name and top reason; clicking a bar navigates to the Runs page with filters applied.
3. Both pages must look good on a 1366×768 projector at 125% zoom — check spacing and font sizes.

## Acceptance
Pages render from mock data and from real `artifacts/eval.json`. `npm run build` passes.
