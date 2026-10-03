---
description: "B00 — Schema v2 migration, workspaces, Nimbu Living help-center seed data, per-workspace retrieval"
mode: agent
---
Read [Business edition](../../docs/12-BUSINESS-EDITION.md) sections 1, 2, 3, 5 fully, plus [Data model](../../docs/03-DATA-MODEL.md) and the existing code in `blackbox/store/` and `blackbox/corpus/`.

## Tasks
1. **Schema v2** exactly as section 5: new columns on `task` and `run`, new tables `incident`, `incident_event`, `recipient`, `notification_rule`, `notification_log`. Add them to the SQLModel models.
2. **`bb db migrate`**: upgrades an existing `data/blackbox.db` in place (ALTER TABLE ADD COLUMN, CREATE TABLE IF NOT EXISTS), backfills `workspace='hotpot'`, is idempotent, and prints what it changed. Make a backup copy `data/blackbox.backup-<timestamp>.db` before migrating.
3. **Workspaces registry** `blackbox/workspaces/registry.py`: `nimbu` and `hotpot` with display names and descriptions from section 2.
4. **Seed data** — author by hand, carefully:
   - `blackbox/workspaces/nimbu/articles.json`: ~40 articles. Every current article must match the "current policy facts" table exactly. Include the ~8 archived articles listed (contradicting current policy, realistic dates) and 3–4 near-duplicate current articles. Natural help-center writing, 3–8 sentences each.
   - `blackbox/workspaces/nimbu/questions.json`: ~40 questions (≈15 lookup, 15 bridge, 10 comparison) in natural, slightly informal Indian English, with short gold spans, category, qtype, gold_aids, distractor_aids.
   - A test `tests/test_nimbu_seed.py` that checks: every gold answer is supported by at least one *current* gold article (substring or normalized match), every aid referenced exists, no two current articles contradict a key fact in the facts table (check a list of key strings like "7 days", "₹999", "₹10,000").
5. **Per-workspace retrieval**: `Retriever.for_workspace(ws)` with indexes in `data/{ws}/`. Passage meta carries `status`, `updated`, `category`. Migrate existing HotpotQA files into `data/hotpot/` (keep a fallback to old paths). Add `search(query, k, exclude_archived=False)`.
6. **CLI**: `bb corpus build --workspace nimbu` (loads seed → passages → embeddings → upserts tasks with workspace, category, 70/30 split), and `bb corpus search --workspace nimbu "return window"`.

## Rules
- Additions only; don't rename or remove existing fields. Tests use temporary databases.
- Don't run bb generate. Never delete data/blackbox.db.

## Acceptance
- `make test` passes, including the seed consistency test.
- `bb db migrate` on the real DB succeeds and is safe to run twice.
- `bb corpus build --workspace nimbu` works; `bb corpus search --workspace nimbu "how many days to return"` returns both the current and the archived return articles near the top.
