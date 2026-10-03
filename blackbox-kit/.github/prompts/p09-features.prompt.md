---
description: "P09 — Step feature extraction (leakage-free)"
mode: agent
---
Read [Model & Eval](../../docs/06-MODEL-AND-EVAL.md) sections "Anti-leakage rules" and "Features" completely. Leakage rules are non-negotiable.

## Task
1. `blackbox/features/reference.py`: compute reference stats (per step `name`: mean/std of latency, tokens_out, output_len, top1_score, passage_len) from **successful clean runs of train-split tasks only**; save/load `artifacts/feature_stats.json`.
2. `blackbox/features/extract.py`: `features_for_run(run, steps, stats) -> pd.DataFrame` (one row per step, columns per the doc, `NaN` where not applicable), using DAG helpers from `blackbox/replay/graph.py` and `embed_texts` from the corpus module (cache step embeddings in `data/step_emb.npy` + index json). It must only use the run's own steps, the task question (not the gold answer!), and reference stats.
3. `build_dataset(split, fault_types=None, include_organic=False) -> (X, y, groups, meta)`: rows from labeled failed runs, sorted by run, `y=1` for the culprit; `meta` has run_id, step_key, task_id, fault_type (for evaluation slicing only — never a column of X).
4. A guard: `assert_no_leakage(X)` that fails if any column name matches a forbidden list (`fault`, `label`, `origin`, `overridden`, `reused`, `gold`).
5. CLI `bb features build` writes `artifacts/features_{split}.parquet` and prints shape + positive rate.
6. Tests on the P01 fixture: correct row count, grounding features detect an extracted answer missing from passages, DAG features correct, leakage guard works.

## Acceptance
`make test` passes. Feature build on current data runs in under a minute for 1,000 runs.

Note: until real data exists, develop against the fixture and a handful of real runs.
