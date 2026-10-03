---
description: "P13 — FastAPI backend with mock mode"
mode: agent
---
Read [API spec](../../docs/07-API.md) fully and [Data Model](../../docs/03-DATA-MODEL.md).

## Task
1. `blackbox/api/schemas.py`: pydantic response models for every response in the spec.
2. `blackbox/api/app.py` + routers (`runs.py`, `replay.py`, `compare.py`, `eval.py`, `fleet.py`, `lab.py`, `health.py`) implementing every endpoint. CORS for `http://localhost:5173`.
3. **Mock mode:** if `BLACKBOX_MOCK_API=1`, every endpoint returns data built from `blackbox/api/fixtures/` (create additional fixtures as needed: a replay of the sample run with reuse stats, a diagnosis with reasons, a compare result, an eval.json with plausible numbers, fleet aggregates). Mock and real responses must have identical shapes — add a test that validates fixtures against the response models.
4. Real mode wires to repo, `diagnose`, `replay`, `blast_radius`, `compare`, `repair`, evaluation artifacts, and agent/fault functions.
5. Background jobs: an in-process job registry (`dict[job_id, JobState]` + thread pool) for repair and live runs; `GET /jobs/{id}` for polling.
6. `make api` starts uvicorn with reload.
7. Tests with FastAPI `TestClient` in mock mode for every endpoint, plus a real-mode test against a temp DB seeded with a FakeLLM run.

## Acceptance
`make test` passes. `BLACKBOX_MOCK_API=1 make api` and open `http://localhost:8000/docs` — every endpoint returns fixture data.
