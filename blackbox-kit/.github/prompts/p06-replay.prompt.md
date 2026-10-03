---
description: "P06 — Replay engine: dependency-aware re-execution, blast radius, compare"
mode: agent
---
Read [Replay spec](../../docs/05-REPLAY-BISECT-REPAIR.md) sections "Public replay API", "Replay stats", "Trace comparison", and the existing tracer.

## Task
1. `blackbox/replay/engine.py`: `replay(source_run_id, overrides=None, freeze_before_idx=None, origin="replay") -> Run`. Loads the task and source run, builds the `ExecutionContext` (source_run_id, overrides, freeze point), re-runs `run_agent`, stores `replay_spec` and `parent_run_id`. Overrides are NOT inherited from the source run's fault — a replay reuses recorded outputs, which already contain any fault effects.
2. `blackbox/replay/graph.py`: build a networkx-free DAG from `deps` (dict adjacency); `descendants(step_key)`; `blast_radius(run_id, step_key)`; `dag_depth`; helpers reused by features later.
3. `blackbox/replay/compare.py`: `compare(run_a, run_b)` per the spec: aligned rows by step_key with status, first divergence, word-level text diff of `output_text` (difflib), JSON diff summary of `output`.
4. CLI: `bb replay RUN_ID [--set KEY=path/to/output.json] [--regen KEY] [--freeze K]` printing reuse stats; `bb compare A B`.
5. Tests (FakeLLM): 
   - comparison question: overriding `q1/retrieve#0` re-executes q1's extract/check and synthesize but **reuses all q2 steps**; stats match.
   - bridge question: overriding `q1/extract#0` re-executes q2's branch.
   - no-op replay reuses 100%.
   - compare reports the right first divergence.

## Acceptance
`make test` passes. With real data: replay a fault run with `--regen` on the faulted step and show the reuse stats line — this is a demo screenshot, make the output pretty.
