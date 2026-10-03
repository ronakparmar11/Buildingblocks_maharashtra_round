# 🟧 Black Box — a flight recorder for AI agents

> Traces show you what happened. **Black Box tells you why — and proves it.**

Built for **Bit N Build 2026** (GDG On Campus, Fr. CRCE) · AI/ML Problem Statement 2.

An AI agent runs a dozen steps and gets the answer wrong. One step was responsible. Black Box learns to find it from execution traces, proves the diagnosis by counterfactual replay, explains it with evidence from the trace, and repairs the run by re-executing only the steps the fix actually affects.

![Run Detail](../docs/img/run-detail.png)

## What makes it different

- **Counterfactual blame.** A step is the cause only if changing it flips the outcome. We prove that with bisect replay (≈ log₂N replays per failure) and train only on verified labels.
- **Dependency-aware replay.** The agent is a real execution DAG. Changing a step re-executes only steps whose inputs changed; everything else is reused from the recording.
- **Generalizes beyond what it was trained on.** Tested on fault types never seen in training and on natural failures the agent produced on its own.
- **Auto-repair.** Fix candidates for the top suspects are replayed in parallel from the checkpoint.

## Results

<!-- Replace with artifacts/eval.md -->
| Test set | Model Top-1 | Model Top-3 | LLM-as-judge Top-1 | Heuristic Top-1 | Last-step Top-1 |
|---|---|---|---|---|---|
| Seen fault types | __ | __ | __ | __ | __ |
| Held-out fault types | __ | __ | __ | __ | __ |
| Organic failures | __ | __ | __ | __ | __ |

- Diagnosis latency: __ ms/run (vs. __ s for LLM-as-judge)
- Replay: __% of steps reused on average, __ tokens saved per replay
- Labeling: __ replays per failure on average vs. __ steps per run
- Auto-repair success: __% @top-1, __% @top-3

## How it works

```mermaid
flowchart LR
  A[Agent run] -->|@step SDK| T[Tracer + cassette] --> DB[(Traces)]
  F[Fault injector] -.-> T
  DB --> B[Bisect replay] --> L[Verified culprit labels]
  L --> M[LightGBM LambdaRank] --> X[SHAP reasons]
  M --> R[Auto-repair] -->|dependency-aware replay| A
  DB & M & X --> UI[UI: graph · replay · compare · eval · fleet]
```

1. **Capture** — every step (plan, retrieve, extract, check, reformulate, synthesize) is recorded with inputs, outputs, dependencies, state, latency, and tokens.
2. **Break** — six realistic fault types are injected into a plan-execute QA agent over HotpotQA.
3. **Prove** — bisect replay finds the step whose correction flips the run to pass.
4. **Learn** — a ranker learns, from ~28 leakage-free step features, to predict that step instantly.
5. **Explain** — SHAP contributions become plain-language reasons quoting the trace.
6. **Fix** — candidate fixes replay from the checkpoint, reusing all unaffected steps.

## Problem statement coverage

| PS feature | Where |
|---|---|
| Execution Data | `blackbox/sdk/tracer.py`, run browser |
| Failure Diagnosis | `blackbox/model/`, Run Detail ranking |
| Failure Explanation | `blackbox/model/explain.py`, "Why" panel |
| Checkpointed Replay | `blackbox/replay/engine.py`, Replay tab |
| Alternative Execution | `blackbox/repair/`, Auto-repair drawer |
| Model Evaluation | `blackbox/model/evaluate.py`, Evaluation page |
| Trace Comparison | `blackbox/replay/compare.py`, Compare page |

## Quickstart

```bash
cp .env.example .env          # add GEMINI_API_KEY
make install
bb db init && bb corpus build
bb generate all --limit-tasks 50
bb train && bb eval
make api    # :8000
make web    # :5173
```

Offline demo: `BLACKBOX_DEMO_MODE=1 make demo`

## Tech

Python · FastAPI · SQLite/SQLModel · Gemini · sentence-transformers · LightGBM · SHAP · React · TypeScript · React Flow · Recharts · Tailwind

## Team

<!-- names and roles -->
