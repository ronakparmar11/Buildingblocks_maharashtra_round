---
description: "P08 — Bulk data generation pipeline (resumable, rate-limited, concurrent)"
mode: agent
---
Read [Agent & Faults](../../docs/04-AGENT-AND-FAULTS.md) "Clean-run filter" and "Generation plan", and [Build Plan](../../docs/09-BUILD-PLAN.md) "Data generation budget".

## Task
1. `blackbox/datagen/pipeline.py` with stages, each idempotent and resumable:
   - `clean`: one clean run per task (skip existing).
   - `faults`: for each task whose clean run passed, pick up to 2 applicable targets per fault type (seeded) and run them (skip if a fault run for that (task, type, step_key) exists).
   - `label`: bisect-label all failed fault runs.
   - `organic`: counterfactual-label up to 60 failed clean runs.
2. Concurrency: a `ThreadPoolExecutor(MAX_CONCURRENCY)` over tasks; the shared rate limiter from P02 protects the API; each worker uses its own DB session. SQLite WAL must handle concurrent writes — serialize writes through a lock if needed.
3. Robustness: a failing task logs and continues; Ctrl-C stops cleanly; rerunning continues where it stopped.
4. `bb generate all|clean|faults|label|organic [--limit-tasks N]` plus `bb generate status` printing: tasks, clean pass rate, fault runs by type, failure rate by type, labels (verified, matches_injection), organic labels, cassette hit rate, total tokens.
5. Write `artifacts/datagen_report.json` with the status numbers (used later by the eval page).

## Acceptance
- `bb generate all --limit-tasks 10` completes end-to-end on a real key and `bb generate status` looks sane.
- Interrupt mid-run, rerun, no duplicates.
- Then start the full run in the background (`nohup bb generate all > gen.log 2>&1 &`) and keep it going.
