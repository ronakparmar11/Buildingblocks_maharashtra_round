---
description: "P07 — Counterfactual labeling: bisect for injected faults, resampling for organic failures"
mode: agent
---
Read [Replay spec](../../docs/05-REPLAY-BISECT-REPAIR.md) sections "Labeling injected failures: bisect" and "Labeling organic failures", and the `label` table in [Data Model](../../docs/03-DATA-MODEL.md).

## Task
1. `blackbox/labeling/bisect.py`: `label_fault_run(run_id) -> Label | None`:
   - skip if the run passed or a label exists;
   - `f(0)`: if it fails, discard (store nothing, log reason);
   - binary search smallest k with `f(k)` failing using `replay(..., freeze_before_idx=k, origin="bisect")`; memoize f(k) results;
   - culprit = step at idx k−1 of the source run;
   - verify with `replay(overrides={culprit: Override("regenerate")})` → `verified`;
   - `matches_injection`, `n_replays`, `confidence` (1.0 verified, 0.5 otherwise).
2. `blackbox/labeling/counterfactual.py`: `label_organic_run(run_id, n_samples=3, threshold=2/3)` per the spec; only llm steps are candidates; ties → earliest; below threshold → store nothing and log "unlabelable".
3. CLI: `bb label faults [--limit N]` and `bb label organic [--limit 60]`, both resumable, with a rich progress bar and a final summary: labeled, verified %, matches_injection %, avg replays per label vs. avg steps (this ratio is a pitch number).
4. Tests (FakeLLM) on a scripted run where the fault at step 3 of 8 causes failure: bisect finds step 3 in ≤ 4 replays and verification passes; a fault that doesn't cause failure is skipped; a scripted organic failure where resampling step 2 flips the outcome gets labeled step 2.

## Acceptance
`make test` passes. On real data, `bb label faults --limit 20` prints the summary.
