---
description: "P98 — Review the codebase against the PS and the PRD compliance matrix"
mode: agent
---
Read [PRD](../../docs/01-PRD.md) (compliance matrix and success criteria) and [Model & Eval](../../docs/06-MODEL-AND-EVAL.md) anti-leakage rules.

Do NOT change code in this task. Produce a review:

1. For each PS feature in the compliance matrix: where it's implemented (files/functions), how a judge sees it in the UI, and a status (done / partial / missing).
2. Leakage audit: search the feature and model code for any use of fault, label, origin, overridden, reused, gold answer, or test-split tasks in training. Report every hit with file and line.
3. Determinism audit: any LLM or tool call that bypasses the cassette.
4. Demo-mode audit: any code path in the Live Lab flow that could hit the network.
5. Numbers check: README and slide numbers vs. `artifacts/eval.json`.
6. A prioritized fix list (max 10 items) with effort estimates, most demo-critical first.
