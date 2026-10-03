---
description: "P03 — HotpotQA corpus, task split, embeddings, retrieval"
mode: agent
---
Read [Agent & Faults](../../docs/04-AGENT-AND-FAULTS.md) section "Dataset" and [Data Model](../../docs/03-DATA-MODEL.md) table `task`.

## Task
1. First, load one HotpotQA distractor validation example with `datasets` and print its keys and nested structure. Adapt the loader to the actual field layout (`context` and `supporting_facts` are columnar dicts in the HF version).
2. `blackbox/corpus/hotpot.py`: sample `N_TASKS` questions (half bridge, half comparison, seed from settings); build passages (`pid = "p_" + sha1(title)[:10]`, text = joined sentences, dedupe by title); for each task store `gold_titles` and `distractor_pids`; assign `split` 70/30 stratified by qtype; upsert into `task`. Write `data/passages.jsonl`.
3. `blackbox/corpus/embed.py`: embed `title + ". " + text` with `all-MiniLM-L6-v2` (normalize), save `data/embeddings.npy` and `data/pid_index.json`. Provide `embed_texts(list[str]) -> np.ndarray` with an in-process model cache (reused later by features).
4. `blackbox/corpus/retriever.py`: `Retriever.search(query, k=3) -> list[{pid,title,text,score}]` via cosine with numpy; `get_passage(pid)`; `search_titles(entity, k)` using rapidfuzz on titles (needed by auto-repair later). Load lazily, singleton.
5. CLI: `bb corpus build` (idempotent; skips if files exist unless `--force`) and `bb corpus search "query"` for manual checks.
6. Tests with a 5-passage in-memory corpus and a stub embedder (no model download in tests).

## Acceptance
- `bb corpus build` completes; `bb db stats` shows N_TASKS tasks with a ~70/30 split.
- `bb corpus search "Scott Derrickson nationality"` returns sensible titles.
- `make test` passes offline.
