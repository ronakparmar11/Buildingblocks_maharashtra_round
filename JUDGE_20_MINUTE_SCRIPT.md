# Black Box: 20-Minute Judge Presentation

## Before You Present

Open these pages in separate tabs:

1. `/judge-demo?ws=nimbu`
2. `/?ws=nimbu`
3. `/incidents/inc_refunds_archived?ws=nimbu`
4. `/conversations/nimbu_demo_001?ws=nimbu`

Keep the terminal closed unless a judge asks for implementation proof. If needed, show:

```bash
.venv/bin/python -m pytest -q
```

Current verified result: **84 tests passed**.

Do not present the mock Evaluation-page percentage as a measured model result. The current generated evaluation artifact has `n=0` because provider quota was exhausted. The honest explanation is included below.

---

## 0:00-1:00 - Open With the Failure

**On screen:** Golden Demo, showing the customer question and wrong answer.

**Say:**

"Good morning, judges.

An AI agent can complete eleven steps correctly and still give the customer the wrong answer on step twelve.

Here, the customer asks whether Scott Derrickson and Ed Wood have the same nationality. The agent retrieves the evidence, extracts that both are American, and then answers 'no.'

The wrong answer is obvious. The difficult question is: where did the failure actually begin?

Today, teams open a trace viewer, scroll through thousands of tokens, and ask an engineer to guess. That is slow, expensive, and it does not prove causality.

We built **Black Box**, a flight recorder for AI agents.

Traces tell you what happened. Black Box tells you why, proves it, and tests the fix."

**Pause for two seconds.**

"Our core principle is simple: a step is not guilty because it looks suspicious. A step is guilty only if changing that step changes the final outcome."

---

## 1:00-3:00 - Explain the Real Business Problem

**On screen:** Nimbu Living Overview.

**Say:**

"To make this concrete, we modeled Nimbu Living, an Indian direct-to-consumer home and kitchen brand.

Its support agent answers questions about returns, refunds, COD, shipping, warranties, and loyalty points. The knowledge base contains current policies, but it also contains archived policies, just like a real company wiki.

The current return policy is seven days. An archived article says thirty days. If retrieval selects the old article, the bot confidently gives a wrong answer. That can create a refund dispute, a human escalation, a chargeback, or a one-star review.

This is not only a chatbot-quality problem. It is an operations problem.

The support team needs answers to five questions:

1. Which conversations are failing?
2. Are they part of the same underlying incident?
3. Which exact agent step caused the failure?
4. What is the smallest fix?
5. Does that fix work across every affected conversation?

Black Box handles that complete loop: capture, detect, diagnose, explain, repair, verify, and notify."

**Point to the Overview KPIs and incidents.**

"Instead of making the team inspect isolated conversations, Black Box groups failures by workspace, category, likely cause step, and reason pattern. Fourteen refund failures become one incident: 'search returned an archived policy.' The team sees severity, affected conversations, estimated business cost, ownership, and status in one place."

---

## 3:00-5:00 - Show What Is Different

**On screen:** Keep Overview visible or use one simple architecture slide.

**Say:**

"There are excellent products for observing LLM applications. LangSmith, Langfuse, and OpenTelemetry can record traces.

Black Box starts where trace collection ends.

It adds four capabilities.

First, **causal diagnosis**. We do not simply mark the last step or ask another LLM to read the entire trace. We use counterfactual replay to verify which step changes the outcome.

Second, **dependency-aware replay**. When one branch changes, we re-execute only its downstream dependants. Unaffected work is reused from the recording.

Third, **learned localization**. Verified causal labels train a lightweight ranking model to identify likely culprit steps in milliseconds, without replaying every production failure.

Fourth, **verified repair**. We try targeted fixes from a checkpoint, preserve the original run, and report exactly how many affected cases pass.

So tracing is an input to Black Box. Diagnosis and verified recovery are the product."

---

## 5:00-7:30 - Explain the Architecture

**Say:**

"Let me walk through the architecture from left to right.

The agent is a plan-and-execute workflow. It plans subquestions, retrieves documents, extracts candidate answers, checks grounding, optionally reformulates, and synthesizes the final answer.

Every step passes through our tracer SDK. A step has a stable key, declared dependencies, a typed input, an output, latency, token usage, and content hashes.

The trace is stored in SQLModel tables, backed by Neon Postgres in the deployed configuration and SQLite as a local fallback. LLM and tool responses are stored in a content-addressed cassette. That makes the offline demo deterministic and prevents Wi-Fi or provider quota from killing the presentation.

The replay engine re-runs the agent program. Before executing each step, it compares the current input hash with the recorded input hash. If they match and there is no override, the recorded output is reused at zero model cost. If an upstream change alters the input, that step executes again. Change propagation is therefore automatic rather than hard-coded.

The replay engine feeds two systems. During data preparation, the counterfactual labeler proves culprit steps. During operation, the repair engine tests candidate fixes.

Verified labels become step-level features. A LightGBM LambdaRank model ranks the steps within each failed run. SHAP contributions are converted into plain-language reasons and grounded with exact trace evidence.

FastAPI exposes the data and actions. React, TypeScript, TanStack Query, React Flow, and Recharts provide the investigation interface."

**Add:**

"We deliberately used a plan-and-execute DAG rather than a fully connected ReAct scratchpad. Independent branches are genuinely independent, so dependency-aware replay produces real savings instead of merely claiming them."

---

## 7:30-10:00 - Explain How Black Box Proves the Cause

**On screen:** Golden Demo trace.

**Say:**

"The most important technical idea is counterfactual blame.

Suppose a failed run has twelve steps. We define a replay boundary. Steps before the boundary are frozen from the failed recording; steps after it are regenerated from clean, deterministic inputs.

If regenerating from the beginning passes, but freezing the complete failed run still fails, there is a transition point. Binary search finds the earliest boundary where failure returns. For a twelve-step trace, this requires roughly logarithmic rather than linear replay attempts.

Then we perform a final verification: regenerate only the suspected culprit. If the final outcome flips from fail to pass, the label is verified. If it does not flip, we do not pretend the diagnosis is proven.

For naturally occurring failures, where there is no injected fault, we counterfactually resample each LLM step three times. A step is accepted only when at least two of three interventions flip the outcome. The confidence records that flip rate.

This distinction matters. The place where a fault was injected is not always the same as the step that became causally responsible for the bad answer. We train only from the proven intervention result, not from hidden fault metadata."

**Point at the selected culprit card.**

"In this recorded example, Black Box ranks synthesis as the cause with 94% confidence. The evidence is direct: the subanswers both say American, while the final answer says no. Diagnosis took 18.4 milliseconds."

---

## 10:00-12:00 - Explain the ML Without Hype

**Say:**

"Once counterfactual replay has generated trusted labels, diagnosis becomes a ranking problem: among all steps in this run, rank the responsible step first.

We extract 36 features in five broad groups.

Structural features describe the DAG: position, depth, descendants, retries, and whether a step feeds the final answer.

Operational features capture abnormal latency, token count, and output length relative to clean steps of the same type.

Retrieval features capture top score, score gap, query-title overlap, unique documents, and passage length.

Grounding features ask whether the extracted answer and evidence exist in the retrieved passages and whether downstream checks marked them unsupported.

Consistency features detect disagreement between subanswers and the final response, including yes/no mismatches.

We chose LightGBM LambdaRank because the dataset is tabular, the target is ranking within a run, training is fast on a laptop, inference is cheap, and SHAP can explain each score.

We enforce leakage prevention. Features cannot read fault type, labels, run origin, override flags, reuse flags, or gold answers. Reference statistics come only from successful clean runs in the training split. Splits are by task ID, so the same question cannot appear in both training and test data.

The intended evaluation has four views: seen fault types, held-out fault types, organic failures, and cross-domain Nimbu support failures. Baselines include random ranking, choosing the last step, a hand-built heuristic, and an LLM judge reading the trace."

---

## 12:00-15:00 - Run the Golden Demo

**On screen:** `/judge-demo?ws=nimbu`.

**Say while clicking:**

"Now I will show the full loop on recorded evidence, with zero provider calls.

The agent answered 'no'; the expected answer is 'yes.' We have the complete twelve-step execution trace. I can inspect any captured input or output rather than relying on a generated summary."

**Click one retrieve step, then one extract step, then synthesis.**

"The retrieval and extraction steps contain consistent evidence. The divergence appears at synthesis.

Black Box reports the cause, the human-readable reason, and the exact conflicting values: final answer 'no'; subanswers 'American' and 'American.'"

**Point to Minimal Repair.**

"The selected repair strategy is 'use only the subanswers.' This is not a blind prompt rewrite and it is not applied directly to production. It creates a new replay run.

Only the failed synthesis step executes again. Eleven trusted upstream steps are reused. The repaired run passes using 171 tokens.

This is the unit of value: not merely a plausible explanation, but a minimal intervention followed by a verified outcome."

**Pause.**

"The original run remains immutable. The source trace, repaired trace, first divergence, changed output, reused steps, and cost are all auditable."

---

## 15:00-17:00 - Show the Business Incident Workflow

**On screen:** Refund incident detail.

**Say:**

"A production team does not want to repeat that investigation fourteen times. This incident groups refund conversations with the same causal signature.

The representative customer received the archived thirty-day return policy instead of the current seven-day policy. Black Box identifies retrieval as the likely cause and shows the archived article as evidence.

The business-specific repair is intentionally conservative: 'search current articles only.' We test it first on the representative conversation.

After it passes, Black Box can apply the same strategy to every affected conversation through isolated replays. The incident records how many pass, which cases still fail, and the total tokens saved through reuse. It reaches 'fix verified' only when the configured acceptance threshold is met.

That is important: twelve of fourteen passing is not described as fourteen of fourteen. The remaining two stay visible for further investigation.

The timeline records when the incident opened, when the team was notified, which fix was tried, the verification result, ownership changes, and resolution."

**Open the notification preview if available.**

"Notification is part of the operational loop. Black Box sends a multipart email through SMTP with the example conversation, likely cause, trace evidence, severity, estimated cost, and a link back to the incident. Sending is asynchronous, retried, throttled, and fully logged. Demo mode blocks remote SMTP while allowing local Mailpit, so presentation data cannot accidentally email a real customer."

---

## 17:00-18:30 - Explain Reliability and Engineering Depth

**Say:**

"Several engineering decisions make this more than a UI prototype.

We implement six realistic fault families: corrupted plans, bad queries, distractor retrieval, truncated context, wrong extraction, and hallucinated synthesis. Faults use the same override mechanism as replay and repair; there is no separate toy agent path.

The data generator is resumable and rate-limited. Model calls are abstracted across providers. Temperature-zero calls are cassette-backed. Every replay stores reuse and token-saving statistics.

The backend has 84 passing tests covering tracing, faults, replay, bisect labels, features, model behavior, repair, incidents, notifications, migrations, authentication, and API contracts.

The application supports workspace isolation, schema migrations, recipient and notification rules, incident lifecycle validation, a traffic simulator, and both local and Neon-backed persistence.

No GPU is required. The complete system runs on a laptop."

---

## 18:30-19:15 - Address the Evaluation Honestly

**Say exactly:**

"I want to be precise about one limitation.

Our final live data-generation run exhausted the configured Gemini daily quota after twenty requests. The checked-in evaluation artifact therefore contains zero evaluable test runs. That means the accuracy metrics are **unavailable**, not zero percent.

I will not present a mock percentage as a scientific result.

What is verified today is the complete evaluation pipeline, serialized model artifacts, deterministic golden evidence, the business workflow, and 84 passing backend tests. With provider quota restored, the next command resumes generation and evaluates the predefined seen, held-out, organic, and support splits without changing the methodology.

For a hackathon, we chose reproducibility and honesty over manufacturing a number."

---

## 19:15-20:00 - Close With the Vision

**On screen:** Golden Demo showing Cause isolated, Minimal repair, Fix verified.

**Say:**

"Black Box changes how teams operate AI agents.

Without it, a wrong answer becomes a long manual investigation and an untested prompt patch.

With it, the failure becomes a trace, the trace becomes a causal diagnosis, the diagnosis becomes a minimal replay, and the replay becomes verified evidence that a fix works across the incident.

Our next step is an OpenTelemetry GenAI adapter so existing agents can send traces without adopting our agent implementation, followed by CI regression gates that replay known incidents before a prompt or model change is deployed.

The long-term goal is simple: every production AI decision should be explainable, reproducible, and repairable.

Traces show you what happened.

**Black Box tells you why, proves it, and fixes it.**

Thank you."

---

## High-Probability Judge Questions

### Is this just LangSmith or Langfuse?

"Those products are strong trace and observability platforms. Black Box consumes trace-like data, but its core output is a counterfactually verified culprit and a tested repair. Recording is our input; causal localization and recovery are our differentiator."

### Why not ask an LLM to inspect the trace?

"That is a valid baseline and is included in our evaluation design. It requires another large-model call for every failure, can be inconsistent, and gives a plausible opinion rather than intervention evidence. Our learned ranker runs locally in milliseconds, and replay tests whether its diagnosis actually repairs the outcome."

### How can replay succeed without a gold answer in production?

"Gold answers are the evaluation oracle. In production, the verifier can be the agent's deterministic check, a schema or policy validator, a unit test, human approval, or later customer feedback. Black Box separates replay from the choice of acceptance oracle."

### Are synthetic faults realistic?

"Synthetic faults provide controlled experiments and exact fault coverage, but we do not train from injection metadata. Bisect proves the causal step independently. The design also labels natural failures through counterfactual resampling and reserves held-out fault types and a separate support domain for evaluation."

### What if several steps jointly cause the failure?

"The current model ranks the first repairable causal boundary and can expose multiple high-scoring suspects. Independent repair candidates are tested separately. Multi-step interaction attribution is a known extension; we would add pairwise interventions when no single-step replay flips the outcome."

### Why LightGBM instead of a transformer?

"The current problem is grouped ranking over a modest amount of structured data. LambdaRank matches that objective, trains quickly, runs cheaply, and produces faithful feature contributions. A sequence model becomes appropriate after collecting substantially more diverse production traces."

### How does this integrate with another agent?

"The integration contract is a stable step key, dependencies, input, output, and optional token metadata. Today that is our tracer SDK. The next adapter maps OpenTelemetry GenAI spans into the same schema, so LangGraph or custom agents can use the diagnosis and replay layers."

### Is the repair automatically deployed?

"No. A repair creates a separate replay run, never mutates the source, and is reviewed before deployment. Black Box verifies evidence for a fix; it does not silently change production behavior."

### What is actually live versus seeded?

"The causal engine, API, persistence, replay, incidents, notifications, and tests are implemented. The Nimbu company and its 80 historical conversations are seeded, fictional demo data. The golden demo is intentionally recorded and deterministic. The current aggregate evaluation numbers are unavailable because the provider quota stopped generation."

### What would you build next?

"First, restore provider capacity and publish the predefined evaluation. Second, ship the OpenTelemetry adapter. Third, add CI regression replay and multi-step causal interventions. Fourth, connect incident cost to real support and refund systems rather than a configured estimate."