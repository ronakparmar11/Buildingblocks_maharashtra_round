---
description: "P00 — Bootstrap the Black Box repo (backend package, tooling, frontend scaffold)"
mode: agent
---
Read [PRD](../../docs/01-PRD.md) and [Architecture](../../docs/02-ARCHITECTURE.md) first.

## Task
Bootstrap the repository exactly per the layout in the Architecture doc.

1. `pyproject.toml` (Python 3.11, package `blackbox`, console script `bb = blackbox.cli:app`) with deps: fastapi, uvicorn[standard], sqlmodel, pydantic>=2, pydantic-settings, typer, rich, google-genai, openai, sentence-transformers, numpy, pandas, datasets, lightgbm, shap, scikit-learn, rapidfuzz, tenacity, httpx, pyarrow. Dev: pytest, ruff.
2. Create every package directory from the Architecture doc with an `__init__.py`.
3. `blackbox/config.py`: pydantic-settings `Settings` with: `LLM_PROVIDER` (gemini|groq|fake, default gemini), `LLM_MODEL` (default `gemini-flash-latest`), `GEMINI_API_KEY`, `GROQ_API_KEY`, `GROQ_MODEL`, `DB_PATH=data/blackbox.db`, `DATA_DIR=data`, `ARTIFACTS_DIR=artifacts`, `MAX_CONCURRENCY=4`, `RPM_LIMIT=30`, `HOLDOUT_FAULTS=BAD_QUERY,WRONG_EXTRACTION`, `N_TASKS=300`, `BLACKBOX_DEMO_MODE=0`, `BLACKBOX_MOCK_API=0`, `SEED=42`. Expose `get_settings()` cached.
4. `blackbox/cli.py`: Typer app with placeholder sub-commands: `corpus`, `run`, `faults`, `label`, `generate`, `features`, `train`, `eval`, `repair`, `prewarm` (each prints "not implemented yet").
5. `.env.example`, `.gitignore` (data/, artifacts/, .env, node_modules, __pycache__, .venv), `Makefile` with targets install, test, lint, fmt, api, web.
6. `tests/test_smoke.py` that imports the package and loads settings.
7. Frontend: scaffold `frontend/` with Vite React-TS. Add Tailwind, `@tanstack/react-query`, `react-router-dom`, `@xyflow/react`, `dagre`, `recharts`, `diff`. Configure the Vite dev proxy `/api` → `http://localhost:8000`. Put the color tokens and fonts from [UI spec](../../docs/08-UI.md) in the Tailwind config. Replace the default page with a placeholder "BLACK BOX" header in the brand style.

## Acceptance
- `make install && make test && make lint` pass.
- `bb --help` lists all sub-commands.
- `make web` shows the placeholder page.

Do not implement any business logic yet.
