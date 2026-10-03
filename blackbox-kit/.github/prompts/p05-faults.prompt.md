---
description: "P05 — Fault injection library (6 realistic fault types)"
mode: agent
---
Read [Agent & Faults](../../docs/04-AGENT-AND-FAULTS.md) section "Fault library", the `register_fault` registry in `blackbox/sdk/tracer.py`, and the `fault` table in [Data Model](../../docs/03-DATA-MODEL.md).

## Task
1. `blackbox/faults/library.py`: implement the 6 faults as registered input/output transforms: `PLAN_CORRUPT`, `BAD_QUERY`, `DISTRACTOR_RETRIEVAL`, `TRUNCATED_CONTEXT`, `WRONG_EXTRACTION`, `HALLUCINATED_SYNTHESIS`. Each transform receives `(value, task, fault_params, rng)` and returns the modified value plus the params actually used (e.g. which distractor pid). Outputs must stay valid against the step contract and look natural — no marker strings.
2. `blackbox/faults/targets.py`: `applicable_targets(clean_run) -> list[(fault_type, step_key)]` from a clean run's steps (e.g. BAD_QUERY only on retrieve steps that have upstream node deps; WRONG_EXTRACTION on extract steps; etc.).
3. `blackbox/faults/inject.py`: `run_with_fault(task, fault_type, step_key, seed) -> Run` = run the agent with an `Override(kind="fault", ...)` at that key, `origin="fault"`; save the `fault` row.
4. CLI: `bb faults list-targets --task-id X`, `bb faults inject --task-id X --type T --step KEY`.
5. Tests (FakeLLM): each fault changes exactly the targeted step, keeps JSON valid, writes the fault row, and the cassette holds the raw pre-fault response. Test that no transform output contains words like "fault", "corrupt", "injected".

## Acceptance
- `make test` passes.
- With a real key, inject each fault type on 3 passing tasks and print a table: fault type, outcome. Expect a mix of pass and fail — that's fine.
