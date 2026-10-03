---
description: "P12 — Auto-repair: generate fix candidates for predicted culprits and replay them in parallel"
mode: agent
---
Read [Replay spec](../../docs/05-REPLAY-BISECT-REPAIR.md) section "Auto-repair".

## Task
1. `blackbox/repair/strategies.py`: per step name, strategy functions returning an `Override(kind="regenerate", params=...)` (temperature/sample_idx, prompt_variant, k, query from LLM reformulation, title-entity retrieval). Prompt variants live in `blackbox/agent/prompts.py` and are selected by `params["prompt_variant"]`; make the agent's step functions honor these params.
2. `blackbox/repair/repair.py`: `repair(run_id, top_k=3, max_workers=4) -> RepairResult` — for predicted steps in rank order, run all candidates for that step concurrently via `replay(origin="repair")`; stop at the first step with a passing candidate; return attempts with outcome and reuse stats.
3. Evaluation hook: `bb eval --repair` runs repair on test-set failures (cap 100) and adds `repair` metrics to `eval.json`: success @top-1 and @top-3, avg candidates, avg % reused.
4. CLI `bb repair RUN_ID`.
5. Tests (FakeLLM): a run whose culprit retrieve step is repaired by the widen-k strategy; repair stops after first success.

## Acceptance
`make test` passes; `bb repair` on 5 real failed runs prints attempts and reuse stats.
