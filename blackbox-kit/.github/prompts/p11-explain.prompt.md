---
description: "P11 — SHAP explanations rendered as evidence-backed reasons"
mode: agent
---
Read [Model & Eval](../../docs/06-MODEL-AND-EVAL.md) section "Explanations".

## Task
1. `blackbox/model/explain.py`: `explain(run_id, ranking, top_n_steps=3, top_n_reasons=3)` using `shap.TreeExplainer(model.booster_)`; for each top step take the largest positive contributions; render via a template registry (one template per feature, with the fallback) filled with real values and **evidence snippets from the step** (answer, query, titles, check reason, sub-answers). Each reason: `{feature, text, evidence, contribution}`.
2. Integrate into `diagnose()` so predictions store reasons.
3. Every feature in `feature_list.json` must have a template (add a test that asserts coverage).
4. CLI `bb diagnose RUN_ID` prints ranking + reasons with rich formatting.
5. Tests with a tiny trained model on synthetic data.

## Acceptance
`make test` passes. Show `bb diagnose` output for 3 real failed test runs (one retrieval, one extraction, one synthesis culprit) and check the reasons read naturally.
