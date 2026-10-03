# 06 — Diagnosis Model, Explanations, Evaluation

## Problem framing

Unit = a step inside a **failed** run. Label = 1 for the verified culprit step, 0 for all other steps in that run. Task = **rank steps within a run** (query = run). Model = `lightgbm.LGBMRanker(objective="lambdarank")`.

Successful runs are not training rows; they provide **reference statistics** ("what normal looks like") for z-score features. Reference stats are computed from **train-split successful runs only** and saved to `artifacts/feature_stats.json`.

## Anti-leakage rules (non-negotiable)

1. No feature may read the `fault` table, `label` table, `origin`, `overridden`, or anything from replays of the run.
2. Train/test split is by `task_id` (from `task.split`). A test task never appears in training.
3. Contrastive features may only reference successful runs of **other, train-split** tasks.
4. Features must be computable for a brand-new live run with no extra LLM calls.

## Features (~28)

Computed in `blackbox/features/extract.py` → one pandas row per step. Non-applicable features are `NaN` (LightGBM handles them).

**Structural**
- `name` (categorical), `type` (categorical)
- `idx`, `rel_pos` = idx / (n_steps − 1), `n_steps`
- `dag_depth` (longest path from `plan` via deps)
- `n_children`, `n_descendants` (via deps graph)
- `is_ancestor_of_final` (path to `synthesize`)
- `attempt`, `node_retries` (max attempt on this node)
- `node_feeds_other` (this node's answer is a dep of another node)

**Size / cost** (z-scored per `name` against reference stats)
- `latency_z`, `tokens_out_z`, `output_len_z`

**Retrieval** (retrieve steps)
- `top1_score`, `mean_score`, `score_gap` (top1 − top2), `top1_score_z`
- `query_title_overlap` (token Jaccard between query and retrieved titles)
- `n_unique_titles`, `passage_len_mean_z`

**Grounding** (extract steps)
- `answer_in_passages` (normalized exact substring, 0/1)
- `answer_fuzzy` (max rapidfuzz `partial_ratio` / 100 over passages)
- `evidence_in_passages` (evidence sentence found in its cited passage, 0/1)

**Check signals**
- `checked_unsupported` (a check on this step's node said unsupported)
- For a check step itself: `check_supported` (0/1)

**Synthesis** (synthesize step)
- `final_in_subanswers` (max fuzzy match of final answer against sub-answers)
- `yesno_mismatch` (question is a yes/no comparison but answer isn't yes/no, or vice versa)

**Plan** (plan step)
- `n_subq`, `plan_has_dep` (any subquestion with deps)
- `subq_question_sim` (mean cosine between subquestions and the question)
- `plan_title_mention` (fraction of subquestions that mention an entity from the question)

**Semantic**
- `io_cosine` (MiniLM cosine between input summary and `output_text`)
- `output_question_cosine`

**Propagation**
- `output_consumed` (this step's answer/query text appears in some downstream step input, 0/1)

**Contrastive (optional, cut if behind)**
- `neighbor_divergence` = 1 − cosine(`output_text`, same-`step_key` output in the most similar successful train run of a *different* task, by question embedding)

Cache MiniLM embeddings of `output_text` per step_id in `data/step_emb.npy` to keep feature extraction fast.

## Training

```python
LGBMRanker(objective="lambdarank", n_estimators=400, learning_rate=0.05,
           num_leaves=31, min_child_samples=5, subsample=0.8, colsample_bytree=0.8,
           random_state=42)
```
- Training rows: verified-label fault runs, train-split tasks, fault types not in `HOLDOUT_FAULTS`.
- `group` = number of steps per run, rows sorted by run.
- 5-fold `GroupKFold` by task_id on the training set for a CV number.
- Save `artifacts/model.txt`, `artifacts/feature_list.json`, `artifacts/model_meta.json` (version, date, train counts).

## Baselines

| baseline | rule |
|---|---|
| Random | uniform random rank (average over 20 seeds) |
| Last step | rank by idx descending |
| Heuristic | first step with any red flag: `answer_in_passages==0`, `checked_unsupported==1`, `top1_score_z < −1`, `yesno_mismatch==1`; then by idx |
| LLM-as-judge | Gemini gets a compact trace (step_key, name, input/output truncated to 300 chars) and returns a ranked list of 3 step_keys as JSON. Run on at most 120 test runs to control cost. |

## Evaluation protocol

Test sets (all on **test-split tasks**):
- **A — seen faults:** fault types used in training.
- **B — held-out faults:** `HOLDOUT_FAULTS`.
- **C — organic:** counterfactual-labeled natural failures.
- **LOFO:** for each fault type t, train on the other 5 (train tasks), test on t (test tasks).

Metrics per test set and per fault type:
- **Top-1**, **Top-3** accuracy, **MRR**
- **Mean index error** = |predicted idx − true idx| for top-1
- **Diagnosis latency** (ms per run, features + predict)

Replay and repair metrics (on test failures):
- **Avg % steps reused** per replay vs. full re-run, **avg tokens saved**
- **Bisect cost**: avg replays per label vs. N (linear scan)
- **Auto-repair success** @top-1 and @top-3 predicted steps, avg candidates tried

Outputs: `artifacts/eval.json` (consumed by the API/UI) and `artifacts/eval.md` (pasted into README).

## Explanations

- `shap.TreeExplainer(model.booster_)` → per-step contributions.
- For each of the top-3 ranked steps, take the 3 features with the largest **positive** contributions and render them through templates in `blackbox/model/explain.py`, with real evidence from the step, e.g.:

| feature | template |
|---|---|
| `answer_in_passages` = 0 | Extracted answer "{answer}" does not appear in any retrieved passage. |
| `top1_score_z` low | Best retrieval score {top1_score:.2f} is far below normal ({ref_mean:.2f} in successful runs). |
| `checked_unsupported` = 1 | The check step flagged this answer as unsupported: "{check_reason}". |
| `query_title_overlap` low | Query "{query}" doesn't match any retrieved titles ({titles}). |
| `final_in_subanswers` low | Final answer "{final}" doesn't match any sub-answer ({subanswers}). |
| `yesno_mismatch` = 1 | Yes/no question answered with "{final}". |
| `n_descendants` high | {n_descendants} downstream steps consumed this output. |

Every feature in the list needs a template; fallback: "{feature} = {value} (typical: {ref_mean})". Reasons are stored in `prediction.reasons`.
