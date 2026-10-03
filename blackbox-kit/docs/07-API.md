# 07 — API (FastAPI)

Base URL `http://localhost:8000/api`. JSON everywhere. CORS open for `http://localhost:5173`. Pydantic response models live in `blackbox/api/schemas.py`. If `BLACKBOX_MOCK_API=1`, every endpoint serves fixtures from `blackbox/api/fixtures/` so the frontend can be built before the backend is ready.

## Runs

`GET /runs?outcome=fail&origin=fault&split=test&fault_type=&q=&limit=50&offset=0`
→ `{items: [RunSummary], total}`
`RunSummary = {run_id, task_id, question, origin, outcome, score_f1, n_steps, created_at, predicted_culprit: {step_key, score} | null, parent_run_id}`

`GET /runs/{run_id}`
→ `{run, task, steps: [Step], edges: [{source, target}], fault: Fault | null, label: Label | null}`
`fault` and `label` are returned for the UI's "ground truth" toggle only; they are never used by the model.

`GET /runs/{run_id}/diagnosis`
→ `{run_id, model_version, latency_ms, ranking: [{step_key, score, rank, reasons: [{feature, text, evidence, contribution}]}]}`
Computes and caches into `prediction` if missing.

## Replay and repair

`POST /runs/{run_id}/replay`
```json
{"overrides": {"q1/retrieve#0": {"kind": "set_output", "output": {...}}},
 "freeze_before_idx": null}
```
→ `{run: RunSummary, stats: {n_reused, n_executed, tokens_saved, tokens_total, latency_ms}, compare_url}`

`GET /runs/{run_id}/blast-radius?step_key=q1/retrieve%230` → `{step_key, affected: [step_key]}`

`POST /runs/{run_id}/repair` body `{top_k: 3}`
→ `{attempts: [{step_key, strategy, run_id, outcome, n_executed, n_reused, tokens_total}], repaired: bool, winning_run_id}`
Long-running: also available as `POST /runs/{run_id}/repair/jobs` → `{job_id}` and `GET /jobs/{job_id}` → `{status, progress, result}` (polling every 700 ms is fine; WebSockets are a stretch).

## Compare

`GET /compare?a={run_id}&b={run_id}`
→ `{a: RunSummary, b: RunSummary, first_divergence: step_key | null, rows: [{step_key, status, a_step, b_step, text_diff}]}`

## Evaluation and fleet

`GET /eval` → contents of `artifacts/eval.json`
`GET /fleet?split=test` → `{by_step_name: [{name, count, pct}], by_reason: [{feature, text, count}], by_fault_type: [...], total_failed}`

## Live lab

`GET /tasks?split=test&q=` → task list for the picker
`GET /tasks/{task_id}/fault-targets` → `{targets: [{fault_type, step_key}]}` (from the task's clean run)
`POST /live/run` body `{task_id, fault: {fault_type, step_key} | null}` → `{run_id}`
(For a custom question without gold answer, `outcome` is `unknown`; demo uses dataset tasks.)

## Health

`GET /health` → `{status: "ok", demo_mode, model_version, n_runs}`
