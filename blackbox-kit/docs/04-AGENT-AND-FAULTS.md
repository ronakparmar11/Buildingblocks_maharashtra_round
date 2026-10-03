# 04 — The Agent Under Test and the Fault Library

## Dataset: HotpotQA (distractor setting)

- Load with `datasets.load_dataset("hotpotqa/hotpot_qa", "distractor", split="validation")`. Print one example first and confirm field names (`id`, `question`, `answer`, `type`, `level`, `supporting_facts`, `context`) before writing the loader.
- Sample **300 questions**: 150 `bridge`, 150 `comparison`, seed 42.
- Each question ships with 10 paragraphs (2 gold + 8 distractors). The **corpus** is the union of all paragraphs from the sampled questions (~3,000 passages). Passage id = `p_` + sha1(title)[:10]. Dedupe by title.
- Embed `title + ". " + text` with `sentence-transformers/all-MiniLM-L6-v2`, L2-normalize, store as `data/embeddings.npy` + `data/passages.jsonl`. Retrieval = cosine top-k with numpy (no FAISS needed at this size).
- Assign `split` by task: 70% train / 30% test, stratified by `qtype`, seed 42.

## Agent: plan → execute DAG → synthesize

```
plan(question) ─► subquestions with deps (max 3)
for each subquestion in topological order:
    query = subquestion text with {qN} placeholders filled from earlier sub-answers
    retrieve(query, k=3)                        # retrieval step
    extract(subquestion, passages)              # llm step
    check(subquestion, answer, passages)        # llm step
    if not supported and attempt < 2:
        reformulate(subquestion, failed answer) # llm step → new query
        attempt += 1 and loop retrieve/extract/check
synthesize(question, subanswers)                # llm step
```

Execution is sequential in a deterministic order (topological, ties by node id), but dependencies are real: a comparison question's q1 and q2 branches are independent; a bridge question's q2 depends on q1's answer.

### Step contracts (all LLM steps return strict JSON)

| step | type | input | output | deps |
|---|---|---|---|---|
| plan | llm | `{question, prompt}` | `{type: "bridge"\|"comparison", subquestions: [{id, text, deps}]}` | — |
| retrieve | retrieval | `{query, k}` | `{passages: [{pid, title, text, score}]}` | `plan` + extract steps of dep nodes (final attempt) + `reformulate` if attempt>0 |
| extract | llm | `{subquestion, passages, prompt}` | `{answer, evidence_pid, evidence_sentence}` | its retrieve |
| check | llm | `{subquestion, answer, passages, prompt}` | `{supported: bool, reason}` | its retrieve + extract |
| reformulate | llm | `{subquestion, previous_query, previous_answer, prompt}` | `{query}` | previous check |
| synthesize | llm | `{question, subanswers, prompt}` | `{answer}` | final extract of every node |

Prompt rules: short, JSON-only response (`response_mime_type="application/json"` on Gemini), answers as short spans ("yes"/"no" for yes-no comparisons). Keep prompts in `blackbox/agent/prompts.py` as constants; the prompt text is part of the step input so it's hashed.

### Scoring

HotpotQA answer normalization (lowercase, strip punctuation, articles, extra whitespace). `pass` if exact match OR token F1 ≥ 0.6. Store `score_f1`.

### Clean-run filter

Run every task once (`origin=clean`, temperature 0). Tasks whose clean run passes become **fault hosts**. Tasks whose clean run fails become **organic failures** (labeled separately, see doc 05). Expect roughly 55–75% pass.

## Fault library (6 types)

Faults are tracer overrides (doc 05). An **output fault** transforms a step's real output after execution; an **input fault** transforms its input before execution. The raw pre-fault response is what goes in the cassette. Faults must be **realistic**: valid JSON, plausible content, no marker strings like "FAULT" or "corrupted".

| fault_type | target step | kind | transformation |
|---|---|---|---|
| `PLAN_CORRUPT` | `plan` | output | bridge: replace the `{q1}` placeholder in q2 with a distractor title (breaks the dependency); comparison: drop the last sub-question |
| `BAD_QUERY` | `qN/retrieve#0` with deps | input | replace the filled-in entity in the query with a distractor title from the same question |
| `DISTRACTOR_RETRIEVAL` | `qN/retrieve#k` | output | replace gold-title passages with this question's distractor passages, keeping the original scores in order |
| `TRUNCATED_CONTEXT` | `qN/retrieve#k` | output | cut each passage to its first sentence |
| `WRONG_EXTRACTION` | `qN/extract#k` | output | replace `answer` with a different entity: another passage's title or a capitalized span from the passages; keep `evidence_pid` |
| `HALLUCINATED_SYNTHESIS` | `synthesize` | output | replace answer with a sub-answer from the wrong node, or flip yes/no for comparison questions |

### Generation plan

For each fault host and each fault type, inject at up to 2 applicable positions (random, seed 42). ~200 hosts × 6 × ~1.6 ≈ 1,900 fault runs. Not every fault causes failure (the check/retry loop sometimes recovers — that's realism). Bisect verifies which runs truly failed because of the fault.

### Generalization splits

- **Held-out fault types (default):** `BAD_QUERY`, `WRONG_EXTRACTION` — never seen in training. Configurable via `HOLDOUT_FAULTS` in `.env`.
- **Leave-one-fault-out (LOFO):** 6 extra trainings, each holding out one type. Cheap with LightGBM, very convincing on a slide.
- **Organic:** natural failures of the agent, never used for training.
