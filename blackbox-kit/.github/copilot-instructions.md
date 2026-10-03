# Copilot instructions — Black Box

You are working on **Black Box**, a hackathon project: an AI-powered debugger that learns from agent execution traces to localize the failure-causing step, proves it with counterfactual replay, and repairs runs while reusing unaffected steps.

## Source of truth

The specs in `docs/` are authoritative. Before writing code for a component, read the relevant doc:
- Product & scope: `docs/01-PRD.md`
- Architecture & package layout: `docs/02-ARCHITECTURE.md`
- **Schema (frozen contract): `docs/03-DATA-MODEL.md`** — never add, rename, or remove fields without being explicitly told to.
- Agent & faults: `docs/04-AGENT-AND-FAULTS.md`
- Replay, labeling, repair: `docs/05-REPLAY-BISECT-REPAIR.md`
- Model & evaluation: `docs/06-MODEL-AND-EVAL.md`
- API: `docs/07-API.md` · UI: `docs/08-UI.md`

If the docs and the request conflict, say so and ask instead of guessing.

## Engineering rules

- Python 3.11, full type hints, pydantic v2, SQLModel, small pure functions. Format/lint with ruff.
- Keep modules in the package paths defined in `docs/02-ARCHITECTURE.md`. Don't create parallel structures.
- **Never make real LLM or network calls in tests.** Use `FakeLLM` (deterministic, scripted responses) and tiny in-memory fixtures. Tests must run offline in seconds.
- **Determinism:** all LLM calls go through the cassette; default temperature 0; resampling uses `sample_idx` in the cache key.
- **Leakage:** feature code must never read `fault`, `label`, `run.origin`, `step.overridden`, or replay runs. Splits are by `task_id`.
- Canonical JSON hashing: `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)` → sha256.
- All config via `blackbox/config.py` (pydantic-settings, reads `.env`). No hard-coded keys or paths.
- Long jobs (data generation, labeling) must be **resumable** and idempotent: skip work already in the DB.
- Log with `logging` (rich handler for CLI), not print.
- Frontend: React + TypeScript + Vite + Tailwind + TanStack Query + React Flow (`@xyflow/react`) + Recharts. API types in `frontend/src/api/types.ts` must mirror `docs/07-API.md`. Follow the visual identity in `docs/08-UI.md`.

## Workflow rules

- Make the smallest change that satisfies the task. Don't refactor unrelated files.
- After changes, run the relevant commands (`make test`, `make lint`, or the acceptance commands given in the prompt) and fix failures before reporting done.
- End every task with: files changed, commands run and their results, and anything left undone.

## Commands

- `make install` — backend deps (uv or pip) + frontend deps
- `make test` — pytest
- `make lint` — ruff check + format check
- `make api` — uvicorn on :8000
- `make web` — vite dev server on :5173
- `bb --help` — CLI (Typer): corpus, run, faults, label, generate, features, train, eval, repair, prewarm
