# 03 — Data Model (FROZEN CONTRACT after P01)

All persistence is SQLite at `data/blackbox.db` via SQLModel. JSON fields are stored as JSON columns. IDs are UUID4 hex strings unless noted.

## Step keys

A step key uniquely identifies a step's *role* in an execution, stable across runs of the same task:

```
plan
q1/retrieve#0      q1/extract#0      q1/check#0
q1/reformulate#1   q1/retrieve#1     q1/extract#1   q1/check#1
q2/retrieve#0 ...
synthesize
```

Format: `{node_id}/{name}#{attempt}` for sub-question steps; bare `plan` and `synthesize` for root steps. `node_id` comes from the plan (`q1`, `q2`, `q3`). `attempt` starts at 0 and increments on each retry loop.

## Tables

### `task`
| column | type | notes |
|---|---|---|
| task_id | str PK | HotpotQA `id` |
| question | str | |
| gold_answer | str | |
| qtype | str | `bridge` \| `comparison` |
| level | str | `easy` \| `medium` \| `hard` |
| split | str | `train` \| `test` (assigned once, by task) |
| gold_titles | JSON list[str] | supporting-fact titles |
| distractor_pids | JSON list[str] | passage ids of this question's distractors |

### `run`
| column | type | notes |
|---|---|---|
| run_id | str PK | |
| task_id | str FK | |
| origin | str | `clean` \| `fault` \| `organic` \| `replay` \| `repair` \| `bisect` \| `live` |
| parent_run_id | str? | source run for replay/repair/bisect runs |
| final_answer | str? | |
| outcome | str | `pass` \| `fail` \| `error` |
| score_f1 | float | |
| n_steps | int | |
| n_reused | int | steps served from source run (replays only) |
| n_executed | int | steps actually executed |
| tokens_total | int | tokens actually spent in this run |
| tokens_saved | int | tokens of reused steps (replays only) |
| latency_ms | int | |
| created_at | datetime | |
| replay_spec | JSON? | overrides / freeze point used (replays only) |

### `fault` (HIDDEN — never used as a model feature)
| column | type | notes |
|---|---|---|
| run_id | str PK FK | |
| fault_type | str | see doc 04 |
| step_key | str | where it was injected |
| params | JSON | e.g. which distractor pid was swapped in |

### `step`
| column | type | notes |
|---|---|---|
| step_id | str PK | |
| run_id | str FK, indexed | |
| step_key | str, indexed | |
| idx | int | execution order, 0-based |
| name | str | `plan` \| `retrieve` \| `extract` \| `check` \| `reformulate` \| `synthesize` |
| type | str | `llm` \| `tool` \| `retrieval` |
| node_id | str | `root` for plan/synthesize |
| attempt | int | |
| deps | JSON list[str] | step_keys whose outputs this step consumed |
| input | JSON | structured input (for llm steps includes `prompt`) |
| input_hash | str | sha256 of canonical JSON of `input` |
| output | JSON | structured output (post-fault if a fault applied) |
| output_hash | str | |
| output_text | str | short human-readable summary used by UI and features |
| latency_ms | int | |
| tokens_in | int | |
| tokens_out | int | |
| model | str? | |
| cache_hit | bool | served by cassette |
| reused | bool | served from source run during replay |
| overridden | bool | output set by an override (manual edit, fault, repair) |
| state_snapshot | JSON | agent state *after* this step: plan, sub-answers so far |
| error | str? | |
| meta | JSON | e.g. retrieval scores, prompt variant, temperature |

### `label`
| column | type | notes |
|---|---|---|
| run_id | str PK FK | |
| culprit_step_key | str | |
| method | str | `bisect` \| `counterfactual` |
| verified | bool | single-step regeneration flips fail→pass |
| confidence | float | 1.0 for verified bisect; flip rate for counterfactual |
| n_replays | int | replays spent labeling |
| matches_injection | bool? | culprit == injected step (fault runs only) |

### `prediction`
| column | type | notes |
|---|---|---|
| run_id | str FK | composite PK with step_key |
| step_key | str | |
| score | float | ranker score |
| rank | int | 1 = most likely culprit |
| model_version | str | |
| reasons | JSON | list of `{feature, text, evidence, contribution}` (top 3, filled for rank ≤ 3) |

### `cassette`
| column | type | notes |
|---|---|---|
| key | str PK | sha256 of `{kind, model, payload, temperature, sample_idx}` |
| kind | str | `llm` \| `tool` |
| response | JSON | raw response (pre-fault) |
| tokens_in | int | |
| tokens_out | int | |
| created_at | datetime | |

## Example run (fixture for frontend/API mocks)

```json
{
  "run": {"run_id": "r_demo", "task_id": "5a8b57f25542995d1e6f1371",
          "origin": "fault", "final_answer": "no", "outcome": "fail",
          "score_f1": 0.0, "n_steps": 8},
  "task": {"question": "Were Scott Derrickson and Ed Wood of the same nationality?",
           "gold_answer": "yes", "qtype": "comparison"},
  "steps": [
    {"step_key": "plan", "idx": 0, "name": "plan", "type": "llm", "deps": [],
     "output": {"type": "comparison", "subquestions": [
        {"id": "q1", "text": "What is Scott Derrickson's nationality?", "deps": []},
        {"id": "q2", "text": "What is Ed Wood's nationality?", "deps": []}]},
     "output_text": "comparison: q1, q2"},
    {"step_key": "q1/retrieve#0", "idx": 1, "name": "retrieve", "type": "retrieval",
     "deps": ["plan"], "output": {"passages": [{"pid": "p_12", "title": "Scott Derrickson",
     "text": "Scott Derrickson is an American director...", "score": 0.71}]},
     "output_text": "3 passages: Scott Derrickson, ..."},
    {"step_key": "q1/extract#0", "idx": 2, "name": "extract", "type": "llm",
     "deps": ["q1/retrieve#0"], "output": {"answer": "American", "evidence_pid": "p_12",
     "evidence_sentence": "Scott Derrickson is an American director..."},
     "output_text": "American"}
  ]
}
```

## Agent state snapshot shape

```json
{"plan": {...}, "subanswers": {"q1": "American"}, "attempts": {"q1": 0}, "final": null}
```
