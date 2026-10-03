---
description: "P04 — Plan-execute agent (real execution DAG) instrumented with the tracer, plus scoring"
mode: agent
---
Read [Agent & Faults](../../docs/04-AGENT-AND-FAULTS.md) fully, [Architecture](../../docs/02-ARCHITECTURE.md) decisions D1–D4, and the existing `blackbox/sdk/tracer.py`.

## Task
1. `blackbox/agent/prompts.py`: concise prompts for `plan`, `extract`, `check`, `reformulate`, `synthesize`, each demanding a strict JSON object matching the step contracts table. Include 1 short example in the plan prompt for each question type. Max 3 subquestions. Bridge subquestions use `{q1}` placeholders.
2. `blackbox/agent/agent.py`: `run_agent(task, ctx) -> Run` implementing plan → topological execution of subquestions (ties by node id) with retrieve → extract → check, retry via reformulate up to attempt 2, then synthesize. **Every step goes through `tracer.step`** with the exact step keys `{node}/{name}#{attempt}`, `plan`, `synthesize`, and with correct `deps` as listed in the doc. Maintain the state snapshot (`plan`, `subanswers`, `attempts`, `final`). Each step provides an `output_text_fn` producing a short human-readable summary.
   - Placeholder filling must be deterministic; if a placeholder's node has no answer, fill with an empty string (don't crash).
   - Invalid plan JSON: fall back to a single subquestion equal to the question.
   - Catch step exceptions → step.error set, run outcome `error`.
3. `blackbox/agent/scoring.py`: HotpotQA `normalize_answer`, `exact_match`, `f1`; `is_pass(pred, gold)` = EM or F1 ≥ 0.6.
4. CLI: `bb run clean --task-id X` (prints the step table with rich), `bb run clean --all --limit N` (resumable: skip tasks that already have a clean run), and `bb run show RUN_ID`.
5. Tests with FakeLLM scripting a comparison question and a bridge question: check step keys, deps (q1 and q2 independent in comparison; q2/retrieve depends on q1/extract in bridge), a retry path when check returns unsupported, scoring correctness.

## Acceptance
- `make test` passes.
- With a real key: `bb run clean --all --limit 20` works; report pass rate and avg steps per run. Target ≥ 50% pass; if lower, inspect failures and tighten prompts before moving on.
- Running the same task twice: second run is 100% cassette hits.
