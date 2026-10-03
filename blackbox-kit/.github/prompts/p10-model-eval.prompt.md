---
description: "P10 — LambdaRank model, baselines, full evaluation protocol"
mode: agent
---
Read [Model & Eval](../../docs/06-MODEL-AND-EVAL.md) sections "Training", "Baselines", "Evaluation protocol".

## Task
1. `blackbox/model/train.py`: train `LGBMRanker` with the given params on train-split, verified, non-holdout fault runs; categorical handling for `name`/`type`; GroupKFold(5) CV by task with Top-1/MRR; save artifacts (`model.txt`, `feature_list.json`, `model_meta.json`).
2. `blackbox/model/predict.py`: `diagnose(run_id) -> ranking` (features + predict + rank), timing in ms; writes `prediction` rows (reasons filled later by P11).
3. `blackbox/model/baselines.py`: random (20 seeds), last-step, heuristic, LLM-as-judge (compact trace prompt → JSON list of 3 step_keys; cassette-cached; cap via `--judge-limit`, default 120).
4. `blackbox/model/evaluate.py`: test sets A (seen), B (held-out), C (organic), LOFO (6 trainings). Metrics: Top-1, Top-3, MRR, mean idx error, diagnosis latency; per fault type. Replay metrics from replay runs in DB: avg % reused, avg tokens saved; bisect avg replays vs. avg steps. Leave a hook for auto-repair metrics (P12 fills it).
5. Write `artifacts/eval.json` (structured for the UI: `{kpis, tables: {baselines, lofo, per_fault}, replay, bisect, repair}`) and `artifacts/eval.md` (markdown tables for README).
6. CLI: `bb train`, `bb eval [--judge-limit N] [--no-lofo]`, `bb diagnose RUN_ID`.
7. Tests on a synthetic feature table where the culprit has a planted signal: model Top-1 > 0.8; metrics functions correct on hand-computed examples.

## Acceptance
`make test` passes. `bb train && bb eval --judge-limit 30` produces both artifacts. Print the headline table in the terminal. If the model doesn't beat the heuristic baseline on set A, inspect feature importance and report findings before changing anything.
