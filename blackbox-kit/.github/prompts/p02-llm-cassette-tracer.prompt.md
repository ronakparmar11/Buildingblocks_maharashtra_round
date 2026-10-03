---
description: "P02 — LLM client, cassette cache, and tracer SDK with replay-aware step()"
mode: agent
---
Read [Architecture](../../docs/02-ARCHITECTURE.md) (decisions D3–D6, D9), [Data Model](../../docs/03-DATA-MODEL.md), and [Replay spec](../../docs/05-REPLAY-BISECT-REPAIR.md) sections "The execution context" and "The step() decision rule". This is the most important module in the project — be precise.

## Task
1. `blackbox/llm/base.py`: `LLMResponse(text, json, tokens_in, tokens_out, model)`, `LLMClient` protocol `complete_json(prompt: str, temperature: float, sample_idx: int = 0) -> LLMResponse`.
2. Providers:
   - `gemini.py` using `google-genai` (`genai.Client`, `client.models.generate_content` with `GenerateContentConfig(temperature=..., response_mime_type="application/json")`; tokens from `usage_metadata`). Verify the SDK API against the installed version before coding.
   - `groq.py` via the `openai` SDK with `base_url="https://api.groq.com/openai/v1"` and `response_format={"type":"json_object"}`.
   - `fake.py`: `FakeLLM` returning scripted JSON by matching a substring of the prompt (dict of `marker -> response`), with deterministic fake token counts. Used by all tests.
   - Retries with `tenacity` (exponential backoff on 429/5xx), a simple token-bucket rate limiter from `RPM_LIMIT`, and robust JSON parsing (strip code fences; one repair retry asking for valid JSON).
3. `blackbox/sdk/cassette.py`: `Cassette.get_or_call(kind, model, payload, temperature, sample_idx, call_fn)` keyed by sha256 of canonical JSON of those fields, stored in the `cassette` table. Returns `(response, usage, cache_hit)`. In demo mode a miss raises `CassetteMissError` instead of calling.
4. `blackbox/sdk/context.py`: `Override` and `ExecutionContext` dataclasses exactly as in doc 05. Use a `contextvars.ContextVar` for the current context.
5. `blackbox/sdk/tracer.py`: `Tracer.step(key, name, type, node_id, attempt, deps, input, fn, output_text_fn)` implementing the decision rule exactly:
   - override (`set_output` / `regenerate` / `fault`, with input- and output-fault hooks resolved via a registry that P05 will populate — define `register_fault(fault_type, input_fn=None, output_fn=None)` now),
   - reuse from source run when key exists, the current input hash matches the source step's `input_hash` or its `meta["pre_override_input_hash"]`, and the freeze rule allows (for input faults, store the pre-fault input hash in `meta["pre_override_input_hash"]`),
   - else execute through the cassette.
   It writes the `Step` row (input_hash, output_hash, latency, tokens, cache_hit, reused, overridden, state_snapshot from a callable on the context, meta). Accumulate run-level stats: n_steps, n_reused, n_executed, tokens_total, tokens_saved.
   - Also provide `run_scope(ctx)` context manager that creates the `Run` row at start and finalizes it at the end.
6. Tests (`tests/test_tracer.py`, FakeLLM only):
   - record a 3-step toy program; rows correct; second identical run hits cassette.
   - replay with no overrides → all steps reused, 0 tokens.
   - replay with `set_output` on step 1 → step 1 overridden, step 2 (depends on 1) executed, an independent step reused.
   - `freeze_before_idx=1` → step 0 reused, steps ≥1 executed.
   - output fault stores the **raw** response in cassette; `regenerate` at temp 0 then returns the clean output.
   - an input fault is reproduced by a no-op replay (pre-override hash reuse), but not when the step is at/after a freeze point.
   - demo mode raises on cassette miss.

## Acceptance
`make test` passes with all the cases above. Print a summary of the decision rule as implemented.
