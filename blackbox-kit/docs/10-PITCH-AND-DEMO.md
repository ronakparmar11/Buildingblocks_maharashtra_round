# 10 — Pitch, Demo, and Judge Q&A

## 3-minute pitch script

**0:00–0:20 — Hook.**
"This agent ran 17 steps to answer a question, and got it wrong. Sixteen of those steps were fine. Which one wasn't? Today an engineer scrolls through the trace and guesses. Across thousands of runs, nobody does it at all."

**0:20–0:50 — Insight.**
"Black Box is a flight recorder for AI agents — painted orange, like the real ones. Our core idea is counterfactual blame: a step is guilty only if changing it flips the outcome. We prove that with bisect replay, use those proofs as training labels, and train a model that finds the culprit in a millisecond, without any replays."

**0:50–2:10 — Live demo (Live Lab).**
1. Pick a comparison question. Inject "distractor retrieval" into one branch. Run → **fails**.
2. Diagnosis appears: the retrieve step glows orange, rank #1, with reasons: "best retrieval score far below normal", "query doesn't match retrieved titles", "check flagged downstream answer as unsupported".
3. Click **Auto-repair**. Candidates run in parallel. One flips the run to **pass**.
4. Point at the graph: "Notice the other branch is greyed out — reused, not re-run. Re-executed 4 steps, reused 13, saved 6,000 tokens."
5. Open **Compare**: first divergence highlighted, word diff of the changed answer.

**2:10–2:45 — Results.**
"Trained on 4 fault types. On 2 types it has never seen, it still finds the culprit at X% top-1, versus Y% for an LLM reading the whole trace — at a fraction of the cost. And on real failures the agent made by itself, which we never trained on, it gets Z%."

**2:45–3:00 — Close.**
"Traces show you what happened. Black Box tells you why, proves it, and fixes it."

## Slide outline (8 slides max)

1. Title — Black Box, orange square, tagline
2. Problem — one failing trace, one red step, "which one?"
3. Insight — counterfactual blame, bisect diagram (log2 N replays)
4. Architecture — the diagram from doc 02
5. Live demo (switch to app)
6. Results — model vs. baselines table, held-out + organic numbers
7. Efficiency — dependency-aware replay: % reused, tokens saved; bisect vs. linear scan
8. PS compliance matrix + future work (OTel/LangGraph adapter, CI integration for agent regressions)

## Demo checklist (run 30 minutes before)

- [ ] `BLACKBOX_DEMO_MODE=1` set, Wi-Fi off, full demo flow works
- [ ] The 3 demo tasks are prewarmed: clean run, fault run, diagnosis, all repair candidates in cassette
- [ ] Browser zoom 110–125%, dark mode, notifications off
- [ ] Backup video on desktop and phone
- [ ] Copy of `data/blackbox.db` and `artifacts/` on a USB stick
- [ ] Results numbers on slide match `artifacts/eval.md`

## Judge Q&A bank

**"Isn't this just LangSmith / Langfuse?"**
They record and display traces. We learn to localize the cause, prove causality by counterfactual replay, and test fixes while reusing unaffected steps. Tracing is our input, not our product.

**"Your faults are synthetic. Does this work on real failures?"**
That's exactly why we built the organic test set: natural failures the agent made by itself, labeled by counterfactual resampling, never used in training. Number: Z%.

**"Why not just ask GPT/Gemini to find the bad step?"**
We did — it's one of our baselines. [cite numbers]. It's also an LLM call per diagnosis; ours is ~1 ms and explainable feature by feature.

**"How do you know your labels are correct?"**
Bisect, then verification: regenerating only the culprit step must flip the run to pass. We only train on verified labels. We also report how often the proven culprit differs from where the fault was injected — those cases show why causal labels beat injection labels.

**"What about leakage?"**
Split by task, held-out fault types, no feature reads fault metadata, contrastive features only reference other train tasks.

**"Is replay deterministic?"**
Temperature 0 plus a content-addressed cassette. Reuse requires an identical input hash, so a change propagates exactly as far as it actually changes inputs.

**"How does auto-repair know it succeeded in production, without a gold answer?"**
In evaluation we use the gold answer as an oracle. In production the success signal would be the agent's own check step, a task validator, or user feedback — the replay mechanism doesn't change.

**"Why LightGBM and not a neural network?"**
Ranking objective, ~1,000 runs of tabular features, trains in seconds, and SHAP gives exact explanations. A sequence model is a natural next step with more data.

**"Does this scale to other agents?"**
The SDK is a decorator plus stable step keys. Any agent where steps have identifiable roles works. An OpenTelemetry GenAI adapter is the obvious next step.

**"What's the cost of labeling?"**
Bisect needs ~log2(N) replays per failure and most of them are cache hits. [cite avg replays per label].
