---
description: "P01 — Data model and storage layer (frozen schema)"
mode: agent
---
Read [Data Model](../../docs/03-DATA-MODEL.md) carefully. It is a frozen contract — implement it exactly.

## Task
1. `blackbox/store/models.py`: SQLModel tables `Task`, `Run`, `Fault`, `Step`, `Label`, `Prediction`, `Cassette` with exactly the columns, types, keys and indexes in the doc. JSON columns via `sa_column=Column(JSON)`.
2. `blackbox/store/db.py`: engine from settings (`DB_PATH`, create parent dir), `init_db()`, `get_session()` context manager, SQLite pragmas `journal_mode=WAL` and `synchronous=NORMAL` (bulk generation writes a lot).
3. `blackbox/store/repo.py`: repository functions — `upsert_task`, `get_task`, `list_tasks(split=None, qtype=None)`, `create_run`, `finish_run`, `add_step`, `get_run`, `get_steps(run_id)` (ordered by idx), `list_runs(filters, limit, offset)`, `save_fault`, `get_fault`, `save_label`, `get_label`, `save_predictions`, `get_predictions`.
4. `blackbox/store/hashing.py`: `canonical_json(obj)` and `sha256_json(obj)` per the rule in copilot-instructions.
5. `blackbox/api/fixtures/sample_run.json`: a realistic fixture of one failed comparison-question run with ~10 steps (plan, two branches with retrieve/extract/check, one retry with reformulate on q1, synthesize), using the example in the Data Model doc as a starting point. Include `edges` derived from deps and a `label`.
6. `bb db init` and `bb db stats` (counts per table) CLI commands.
7. Tests in `tests/test_store.py` using a temp DB: create task/run/steps, read back ordered steps, hashing stability (same dict, different key order → same hash).

## Acceptance
- `make test` passes. `bb db init && bb db stats` works.
- The fixture validates against the models (add a test that loads it).
