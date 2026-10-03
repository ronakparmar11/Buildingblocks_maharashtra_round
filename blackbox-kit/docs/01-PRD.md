# 01 — Product Requirements: Black Box

## One-liner

**Black Box is a flight recorder for AI agents: it learns to pinpoint the step that caused a failure, proves it by counterfactual replay, and repairs the run by re-executing only what the change actually affects.**

Tagline for the pitch: *"Traces show you what happened. Black Box tells you why — and proves it."*

## The problem (from the PS)

Agents execute long graphs of model calls, tool calls, retrieval, and state changes. One wrong intermediate decision can sink a run of many correct steps. Traces show what happened, but finding the responsible step across thousands of runs is manual and slow.

## Our USP (four things no other team will have together)

1. **Counterfactual blame.** A step is "the cause" only if changing it flips the outcome. We prove this with bisect replay, so our training labels are *causal*, not assumed from where a fault was injected.
2. **Dependency-aware replay.** The agent is a real execution *graph* (plan → parallel/sequential sub-questions → synthesis). When a step changes, we re-execute only steps whose inputs actually changed and reuse everything else. This is the literal reading of "without unnecessarily repeating unaffected parts".
3. **Synthetic-to-organic generalization.** The model trains only on injected faults, then is tested on (a) fault types held out entirely and (b) *natural* failures the agent produced on its own, labeled by counterfactual resampling.
4. **Auto-repair.** For the top predicted culprits, Black Box generates candidate fixes and replays them in parallel from the checkpoint. "Proposed fixes can be tested" — and we report the repair success rate.

## Goals

| ID | Goal | Measured by |
|---|---|---|
| G1 | Capture full, replayable execution history | 1,000+ stored runs; any run can be replayed from any step |
| G2 | Trained model localizes failure-causing steps | Top-1 / Top-3 / MRR beating 4 baselines incl. LLM-as-judge |
| G3 | Generalize beyond training failures | Held-out fault types + leave-one-fault-out table + organic failures |
| G4 | Explain each diagnosis with trace evidence | Top-3 human-readable reasons with actual snippets per prediction |
| G5 | Test fixes cheaply | % of steps reused and tokens saved per replay |
| G6 | Propose working fixes | Auto-repair success rate at top-1 and top-3 |
| G7 | Compare executions | Aligned diff with first divergence highlighted |

## Non-goals (say no fast)

- Supporting arbitrary third-party agent frameworks. We instrument our own agent with a small SDK; a LangGraph/OTel adapter is a "future work" slide.
- Training deep models. LightGBM is the right tool: fast, explainable, strong on tabular features.
- User accounts, auth, multi-tenancy.
- Fancy prompt engineering of the agent. The agent should be decent, not perfect — natural failures are useful.

## PS compliance matrix (this goes on a slide)

| PS feature | Our implementation | Evidence shown to judges |
|---|---|---|
| Execution Data | `@step` tracer SDK records inputs, outputs, deps, state, latency, tokens for every step; SQLite store | 1,000+ runs, schema slide, run browser |
| Failure Diagnosis | LightGBM LambdaRank over ~28 step features, trained on bisect-verified culprit labels | Results table vs. baselines |
| Failure Explanation | SHAP contributions → templated reasons with real snippets from the trace | "Why" panel on culprit step |
| Checkpointed Replay | Deterministic re-execution with recorded-output reuse from any step | Replay from any node in the graph |
| Alternative Execution | Manual edit-and-replay + auto-generated fix candidates replayed in parallel | Auto-repair success rate, live demo |
| Model Evaluation | Seen-fault / held-out-fault / leave-one-fault-out / organic test sets, split by task | Evaluation page + report |
| Trace Comparison | Step-key alignment, per-step text diff, first-divergence banner, graph highlighting | Compare view |
| "Thousands of executions" | Fleet view clustering failures by culprit step and reason | Fleet page |
| "Without unnecessarily repeating unaffected parts" | Input-hash reuse + dependency graph | "Re-ran 4 of 17 steps, reused 13, saved N tokens" |

## Success criteria for demo day

- Live loop in under 90 seconds: fault-injected question fails → culprit highlighted with reasons → auto-repair → passes, with reuse stats on screen.
- Results slide with real numbers, baselines, and a held-out generalization result.
- Everything works in demo mode with no network.
