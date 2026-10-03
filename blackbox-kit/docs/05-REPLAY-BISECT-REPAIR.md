# 05 — Replay Engine, Counterfactual Labeling, Auto-Repair

## The execution context

Every agent run executes inside an `ExecutionContext`:

```python
@dataclass
class Override:
    kind: Literal["set_output", "regenerate", "fault"]
    output: dict | None = None          # set_output
    params: dict = field(default_factory=dict)  # regenerate: temperature, sample_idx, prompt_variant, k ...
    fault_type: str | None = None       # fault
    fault_params: dict = field(default_factory=dict)

@dataclass
class ExecutionContext:
    run_id: str
    task: Task
    origin: str
    source_run_id: str | None = None          # replay source
    overrides: dict[str, Override] = {}       # step_key -> Override
    freeze_before_idx: int | None = None      # bisect: reuse only source steps with idx < this
    demo_mode: bool = False
```

## The `step()` decision rule

`tracer.step(key, name, type, deps, input, fn)` where `fn(input, params) -> (output, usage)`:

1. **Override present for `key`:**
   - `set_output` → output = given output; `overridden=True`.
   - `regenerate` → call `fn` with `params` (cassette key includes temperature + sample_idx, so a resample is a new key); `overridden=True`.
   - `fault` → if input fault: transform input, then call `fn`; if output fault: call `fn`, store raw response in cassette, then transform output. `overridden=True`.
2. **Else, reuse check** (only when `source_run_id` is set): find the source step with the same `key`. Reuse its output (`reused=True`, zero tokens, zero latency) if **all** hold:
   - the source step exists,
   - `hash(current input)` equals `source.input_hash` **or** `source.meta["pre_override_input_hash"]` (input faults change a step's input after it's computed; the tracer stores the pre-fault hash in `meta` so a replay with unchanged upstream still reproduces the recorded faulted step),
   - `freeze_before_idx is None` **or** `source.idx < freeze_before_idx` (in bisect mode, source steps at or after the freeze point are always re-executed, never reused).
   - Note: reused steps carry over the source's (possibly faulted) output. That is intended — replay reproduces the recorded world unless told otherwise.
3. **Else execute** `fn` through the cassette (`cache_hit` recorded).

Because reuse requires an identical input hash, any change propagates exactly to the steps whose inputs it changes, and nothing else. Declared `deps` are used for the graph view and the "predicted blast radius" shown before a replay.

### Replay stats

For every replay run: `n_reused`, `n_executed`, `tokens_saved` (sum of source tokens of reused steps), `tokens_total`. These numbers go on the demo screen.

## Public replay API

```python
def replay(source_run_id: str, overrides: dict[str, Override] | None = None,
           freeze_before_idx: int | None = None, origin: str = "replay") -> Run
def blast_radius(source_run_id: str, step_key: str) -> list[str]   # transitive dependents via deps
```

## Labeling injected failures: bisect

For a fault run R that failed, with N steps in execution order:

- `f(k)` = `replay(R, freeze_before_idx=k)`: steps with idx < k reused from R, steps ≥ k re-executed at temperature 0 (cassette returns clean pre-fault outputs; overrides are NOT re-applied).
- Expect `f(0)` = pass (equivalent to the clean run) and `f(N)` = fail (R itself). If `f(0)` fails, discard (not a fault-caused failure).
- Binary search for the smallest k with `f(k)` = fail → culprit = step at idx k−1. ~log2(N) replays.
- **Verify:** `replay(R, overrides={culprit: Override("regenerate")})` must pass → `verified=True`.
- Record `matches_injection = (culprit == fault.step_key)`. Mismatches are interesting (e.g. a fault in retrieve that only matters because extract trusted it); keep them but report the rate.

Store `label(method="bisect", confidence=1.0 if verified else 0.5, n_replays=...)`. Training uses verified labels only.

## Labeling organic failures: counterfactual resampling

Organic failures have no injected fault, and re-execution at temperature 0 just reproduces the failure. Instead, for each **llm** step s in the failed run:

- Run 3 replays with `overrides={s: Override("regenerate", params={"temperature": 0.8, "sample_idx": i})}`, everything downstream at temperature 0.
- `flip_rate(s)` = fraction of replays that pass.
- Culprit = argmax flip_rate (ties → earliest step). Accept if flip_rate ≥ 2/3, else mark run "unlabelable".

Retrieval steps are deterministic; an organic retrieval problem shows up as blame on the upstream llm step that produced the query (plan or reformulate). Cap cost: at most 60 organic runs.

## Auto-repair

Given a failed run and the model's top-k predicted steps (k=3), generate fix candidates per step by name:

| step name | candidate strategies |
|---|---|
| plan | resample (temp 0.8); plan with explicit `qtype` hint prompt variant |
| retrieve | LLM query reformulation; widen to k=6; title-entity search (passages whose title fuzzily matches an entity in the subquestion) |
| extract | resample; "quote the supporting sentence first, then answer" prompt variant |
| check | resample |
| reformulate | resample |
| synthesize | resample; "use only these sub-answers" strict prompt variant |

Each candidate = one `replay()` with a `regenerate` override carrying the strategy params. Run candidates concurrently (thread pool, max 4). Return candidates with outcome, n_executed, n_reused, tokens. Repair stops at the first predicted step that yields a passing candidate.

**Honesty note for judges:** pass/fail during evaluation uses the gold answer as an oracle. In production you'd use the check step, a validator, or user feedback as the success signal. Say this before they ask.

## Trace comparison

`compare(run_a, run_b)` aligns steps by `step_key`:
- status per key: `same` (equal output_hash), `changed`, `only_a`, `only_b`
- `first_divergence`: lowest-idx key that isn't `same`
- per changed step: text diff of `output_text` and a JSON diff of `output`
- summary: outcome a → b, steps reused/executed if b is a replay of a
