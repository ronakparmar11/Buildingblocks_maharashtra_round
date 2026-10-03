---
description: "B01 — Nimbu support agent, archived-aware repair strategy, Nimbu data generation, cross-domain test set D"
mode: agent
---
Read [Business edition](../../docs/12-BUSINESS-EDITION.md) sections 3.4, 3.5, 9, and the existing agent, faults, repair, datagen, and evaluation code.

## Tasks
1. **Workspace-aware agent**: `run_agent(task, ctx)` uses `Retriever.for_workspace(task.workspace)` and adds the Nimbu system preamble to every LLM prompt when `workspace == "nimbu"`. Step keys, deps, and contracts unchanged. Runs inherit `workspace` from the task.
2. **Faults for Nimbu**: `DISTRACTOR_RETRIEVAL` uses the task's `distractor_aids` (archived/near-duplicate articles) as the swapped-in passages. Other faults work unchanged.
3. **Repair strategy** "Search current articles only" for retrieve steps (`exclude_archived=True`), with that exact display name. Put it first in the retrieve strategy order for the nimbu workspace.
4. **Data generation**: `bb generate all --workspace nimbu` runs clean runs, faults, and bisect labels for Nimbu tasks (resumable, same pipeline).
5. **Cross-domain evaluation (test set D)**: the model trained on HotpotQA (no retraining) is evaluated on Nimbu verified labels; add baselines; optional calibration with per-workspace reference stats from successful Nimbu runs only. Add set D to `artifacts/eval.json` (`tables.baselines` gains a `support` test set key, KPIs gain `top1_support`) and `eval.md`.
6. Tests with FakeLLM: preamble present only for nimbu; distractor fault uses distractor_aids; current-only strategy excludes archived passages.

## Rules
Don't change the HotpotQA training set or retrain on Nimbu data. Don't delete data. Tests offline.

## Acceptance
- `bb run clean --task-id <a nimbu task>` shows a sensible support answer.
- `bb generate all --workspace nimbu` completes (≈40 tasks), then `bb eval` reports set D.
- `bb repair` on a failed Nimbu distractor run finds "Search current articles only" as a working fix.
