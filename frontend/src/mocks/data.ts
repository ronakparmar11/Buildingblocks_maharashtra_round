import type {
  DiagnosisResponse,
  EvalResponse,
  FleetResponse,
  Json,
  RunDetailResponse,
  RunSummary,
  StepRecord,
  TaskRecord,
} from "../api/types";

const now = Date.now();
export const tasks: TaskRecord[] = [
  {
    task_id: "task_scott",
    question: "Were Scott Derrickson and Ed Wood of the same nationality?",
    gold_answer: "yes",
    qtype: "comparison",
    level: "medium",
    split: "test",
    gold_titles: ["Scott Derrickson", "Ed Wood"],
    distractor_pids: ["p_british"],
  },
  {
    task_id: "task_film",
    question: "In which country was the director of The Fall born?",
    gold_answer: "India",
    qtype: "bridge",
    level: "hard",
    split: "test",
    gold_titles: ["The Fall", "Tarsem Singh"],
    distractor_pids: ["p_wrong_director"],
  },
  {
    task_id: "task_natural",
    question: "Were Greta Gerwig and Noah Baumbach born in the same country?",
    gold_answer: "yes",
    qtype: "comparison",
    level: "easy",
    split: "test",
    gold_titles: ["Greta Gerwig", "Noah Baumbach"],
    distractor_pids: [],
  },
];

const step = (
  runId: string,
  idx: number,
  stepKey: string,
  name: string,
  deps: string[],
  outputText: string,
  output: Record<string, Json> = { value: outputText },
): StepRecord => ({
  step_id: `${runId}_${idx}`,
  run_id: runId,
  step_key: stepKey,
  idx,
  name,
  type: name === "retrieve" ? "retrieval" : "llm",
  node_id: stepKey.includes("/") ? stepKey.split("/")[0] : "root",
  attempt: Number(stepKey.match(/#(\d+)/)?.[1] ?? 0),
  deps,
  input: { prompt: `Complete ${stepKey}` },
  input_hash: `in_${idx}`,
  output,
  output_hash: `out_${idx}`,
  output_text: outputText,
  latency_ms: 180 + idx * 23,
  tokens_in: 210 + idx * 12,
  tokens_out: 48 + idx * 4,
  model: "gemini-2.0-flash",
  cache_hit: true,
  reused: false,
  overridden: false,
  state_snapshot: {
    plan: { type: "comparison" },
    subanswers: idx > 2 ? { q1: outputText } : {},
    attempts: { q1: 0 },
    final: null,
  },
  error: null,
  meta: {},
});

const makeSteps = (runId: string, bad = true): StepRecord[] => [
  step(runId, 0, "plan", "plan", [], "comparison: q1, q2", {
    type: "comparison",
    subquestions: [
      { id: "q1", text: "What is Scott Derrickson's nationality?", deps: [] },
      { id: "q2", text: "What is Ed Wood's nationality?", deps: [] },
    ],
  }),
  step(
    runId,
    1,
    "q1/retrieve#0",
    "retrieve",
    ["plan"],
    bad
      ? "3 passages: British film, Scott Derrickson"
      : "6 passages: Scott Derrickson, Ed Wood",
    {
      passages: [
        {
          pid: bad ? "p_british" : "p_scott",
          title: bad ? "British film" : "Scott Derrickson",
          text: bad
            ? "A British film was directed by Scott Derrickson."
            : "Scott Derrickson is an American filmmaker.",
          score: bad ? 0.31 : 0.86,
        },
      ],
    },
  ),
  step(
    runId,
    2,
    "q1/extract#0",
    "extract",
    ["q1/retrieve#0"],
    bad ? "British" : "American",
    {
      answer: bad ? "British" : "American",
      evidence_pid: bad ? "p_british" : "p_scott",
      evidence_sentence: bad
        ? "A British film was directed by Scott Derrickson."
        : "Scott Derrickson is an American filmmaker.",
    },
  ),
  step(runId, 3, "q1/check#0", "check", ["q1/extract#0"], "supported", {
    supported: true,
  }),
  step(runId, 4, "q2/retrieve#0", "retrieve", ["plan"], "3 passages: Ed Wood", {
    passages: [
      {
        pid: "p_wood",
        title: "Ed Wood",
        text: "Edward D. Wood Jr. was an American filmmaker.",
        score: 0.91,
      },
    ],
  }),
  step(runId, 5, "q2/extract#0", "extract", ["q2/retrieve#0"], "American", {
    answer: "American",
    evidence_pid: "p_wood",
    evidence_sentence: "Edward D. Wood Jr. was an American filmmaker.",
  }),
  step(runId, 6, "q2/check#0", "check", ["q2/extract#0"], "supported", {
    supported: true,
  }),
  step(
    runId,
    7,
    "synthesize",
    "synthesize",
    ["q1/check#0", "q2/check#0"],
    bad ? "no" : "yes",
    { answer: bad ? "no" : "yes" },
  ),
];

const detail = (
  runId: string,
  outcome: "fail" | "pass",
  bad: boolean,
  parent: string | null = null,
): RunDetailResponse => {
  const steps = makeSteps(runId, bad).map((item, index) => ({
    ...item,
    reused: parent !== null && index < 4,
  }));
  return {
    run: {
      run_id: runId,
      task_id: "task_scott",
      origin: parent ? "replay" : bad ? "fault" : "clean",
      parent_run_id: parent,
      final_answer: bad ? "no" : "yes",
      outcome,
      score_f1: outcome === "pass" ? 1 : 0,
      n_steps: 8,
      n_reused: parent ? 4 : 0,
      n_executed: parent ? 4 : 8,
      tokens_total: parent ? 1450 : 3412,
      tokens_saved: parent ? 1962 : 0,
      latency_ms: parent ? 2100 : 4200,
      created_at: new Date(now - 240000).toISOString(),
      replay_spec: parent ? { source: parent } : null,
    },
    task: tasks[0],
    steps,
    edges: steps.flatMap((item) =>
      item.deps.map((source) => ({ source, target: item.step_key })),
    ),
    fault: bad
      ? {
          run_id: runId,
          fault_type: "distractor_retrieval",
          step_key: "q1/retrieve#0",
          params: { pid: "p_british" },
        }
      : null,
    label: bad
      ? {
          run_id: runId,
          culprit_step_key: "q1/retrieve#0",
          method: "bisect",
          verified: true,
          confidence: 1,
          n_replays: 3,
          matches_injection: true,
        }
      : null,
  };
};

const customDetail = (
  runId: string,
  task: TaskRecord,
  steps: StepRecord[],
  origin: string,
  finalAnswer: string,
  faultStep: string | null,
  culpritStep: string,
): RunDetailResponse => ({
  run: {
    run_id: runId,
    task_id: task.task_id,
    origin,
    parent_run_id: null,
    final_answer: finalAnswer,
    outcome: "fail",
    score_f1: 0,
    n_steps: steps.length,
    n_reused: 0,
    n_executed: steps.length,
    tokens_total: 3260,
    tokens_saved: 0,
    latency_ms: 3980,
    created_at: new Date(now - 360000).toISOString(),
    replay_spec: null,
  },
  task,
  steps,
  edges: steps.flatMap((item) =>
    item.deps.map((source) => ({ source, target: item.step_key })),
  ),
  fault: faultStep
    ? {
        run_id: runId,
        fault_type: "wrong_extraction",
        step_key: faultStep,
        params: { answer: "David Fincher" },
      }
    : null,
  label: {
    run_id: runId,
    culprit_step_key: culpritStep,
    method: faultStep ? "bisect" : "counterfactual",
    verified: true,
    confidence: faultStep ? 1 : 0.83,
    n_replays: 4,
    matches_injection: faultStep ? faultStep === culpritStep : null,
  },
});

const filmSteps = (runId: string): StepRecord[] => [
  step(runId, 0, "plan", "plan", [], "bridge: film → director → birthplace", {
    type: "bridge",
    subquestions: [
      { id: "q1", text: "Who directed The Fall?", deps: [] },
      {
        id: "q2",
        text: "In which country was that director born?",
        deps: ["q1"],
      },
    ],
  }),
  step(
    runId,
    1,
    "q1/retrieve#0",
    "retrieve",
    ["plan"],
    "3 passages: The Fall, Tarsem Singh",
    {
      passages: [
        {
          pid: "p_fall",
          title: "The Fall",
          text: "The Fall is a 2006 film directed by Tarsem Singh.",
          score: 0.9,
        },
      ],
    },
  ),
  step(
    runId,
    2,
    "q1/extract#0",
    "extract",
    ["q1/retrieve#0"],
    "David Fincher",
    {
      answer: "David Fincher",
      evidence_pid: "p_fall",
      evidence_sentence: "The Fall is a 2006 film directed by Tarsem Singh.",
    },
  ),
  step(runId, 3, "q1/check#0", "check", ["q1/extract#0"], "unsupported", {
    supported: false,
    reason: "David Fincher is absent from the evidence.",
  }),
  step(
    runId,
    4,
    "q2/retrieve#0",
    "retrieve",
    ["q1/extract#0"],
    "3 passages: David Fincher",
    {
      passages: [
        {
          pid: "p_fincher",
          title: "David Fincher",
          text: "David Fincher was born in Denver, Colorado, United States.",
          score: 0.88,
        },
      ],
    },
  ),
  step(
    runId,
    5,
    "q2/extract#0",
    "extract",
    ["q2/retrieve#0"],
    "United States",
    {
      answer: "United States",
      evidence_pid: "p_fincher",
      evidence_sentence: "David Fincher was born in Denver, Colorado.",
    },
  ),
  step(runId, 6, "q2/check#0", "check", ["q2/extract#0"], "supported", {
    supported: true,
  }),
  step(
    runId,
    7,
    "synthesize",
    "synthesize",
    ["q1/check#0", "q2/check#0"],
    "United States",
    { answer: "United States" },
  ),
];

const naturalSteps = (runId: string): StepRecord[] => [
  step(runId, 0, "plan", "plan", [], "comparison: q1, q2", {
    type: "comparison",
    subquestions: [
      { id: "q1", text: "Where was Greta Gerwig born?", deps: [] },
      { id: "q2", text: "Where was Noah Baumbach born?", deps: [] },
    ],
  }),
  step(
    runId,
    1,
    "q1/retrieve#0",
    "retrieve",
    ["plan"],
    "3 passages: Greta Gerwig",
    {
      passages: [
        {
          pid: "p_gerwig",
          title: "Greta Gerwig",
          text: "Greta Gerwig was born in Sacramento, California, United States.",
          score: 0.93,
        },
      ],
    },
  ),
  step(runId, 2, "q1/extract#0", "extract", ["q1/retrieve#0"], "American", {
    answer: "American",
    evidence_sentence: "Born in California, United States.",
  }),
  step(runId, 3, "q1/check#0", "check", ["q1/extract#0"], "supported", {
    supported: true,
  }),
  step(
    runId,
    4,
    "q2/retrieve#0",
    "retrieve",
    ["plan"],
    "3 passages: Noah Baumbach",
    {
      passages: [
        {
          pid: "p_baumbach",
          title: "Noah Baumbach",
          text: "Noah Baumbach was born in Brooklyn, New York, United States.",
          score: 0.91,
        },
      ],
    },
  ),
  step(runId, 5, "q2/extract#0", "extract", ["q2/retrieve#0"], "American", {
    answer: "American",
    evidence_sentence: "Born in New York, United States.",
  }),
  step(runId, 6, "q2/check#0", "check", ["q2/extract#0"], "supported", {
    supported: true,
  }),
  step(
    runId,
    7,
    "synthesize",
    "synthesize",
    ["q1/check#0", "q2/check#0"],
    "no",
    { answer: "no", rationale: "The birth cities are different." },
  ),
];

export const details: Record<string, RunDetailResponse> = {
  r_scott_fail: detail("r_scott_fail", "fail", true),
  r_scott_fixed: detail("r_scott_fixed", "pass", false, "r_scott_fail"),
  r_film_fail: customDetail(
    "r_film_fail",
    tasks[1],
    filmSteps("r_film_fail"),
    "fault",
    "United States",
    "q1/extract#0",
    "q1/extract#0",
  ),
  r_natural_fail: customDetail(
    "r_natural_fail",
    tasks[2],
    naturalSteps("r_natural_fail"),
    "organic",
    "no",
    null,
    "synthesize",
  ),
};
export const diagnoses: Record<string, DiagnosisResponse> = {
  r_scott_fail: {
    run_id: "r_scott_fail",
    model_version: "ranker-v3",
    latency_ms: 1.2,
    ranking: [
      {
        step_key: "q1/retrieve#0",
        score: 0.91,
        rank: 1,
        reasons: [
          {
            feature: "retrieval_support",
            text: "The answer is not supported by the retrieved text.",
            evidence: "“American” not found in 3 retrieved passages",
            contribution: 0.48,
          },
          {
            feature: "retrieval_score",
            text: "The strongest passage score is unusually low.",
            evidence: "Top score 0.31; typical score 0.78",
            contribution: 0.29,
          },
          {
            feature: "downstream_change",
            text: "Fixing this step would change four later steps.",
            evidence: "q1/extract#0 through synthesize",
            contribution: 0.14,
          },
        ],
      },
      {
        step_key: "q1/extract#0",
        score: 0.64,
        rank: 2,
        reasons: [
          {
            feature: "unsupported_answer",
            text: "The extracted nationality describes the film, not the person.",
            evidence: "British film ≠ British director",
            contribution: 0.38,
          },
        ],
      },
      {
        step_key: "synthesize",
        score: 0.22,
        rank: 3,
        reasons: [
          {
            feature: "answer_conflict",
            text: "The final answer follows the conflicting sub-answers.",
            evidence: "British vs American → no",
            contribution: 0.18,
          },
        ],
      },
    ],
  },
  r_film_fail: {
    run_id: "r_film_fail",
    model_version: "ranker-v3",
    latency_ms: 1.4,
    ranking: [
      {
        step_key: "q1/extract#0",
        score: 0.94,
        rank: 1,
        reasons: [
          {
            feature: "evidence_mismatch",
            text: "The extracted director contradicts the evidence sentence.",
            evidence:
              "Evidence says “directed by Tarsem Singh”; output says “David Fincher”",
            contribution: 0.52,
          },
          {
            feature: "check_failure",
            text: "The next check marked this answer unsupported.",
            evidence: "David Fincher is absent from the evidence",
            contribution: 0.27,
          },
          {
            feature: "downstream_dependency",
            text: "The second search used this incorrect person.",
            evidence: "q2/retrieve#0 searched for David Fincher",
            contribution: 0.15,
          },
        ],
      },
      {
        step_key: "q2/retrieve#0",
        score: 0.61,
        rank: 2,
        reasons: [
          {
            feature: "wrong_entity",
            text: "Retrieval followed the wrong bridge entity.",
            evidence: "Searched David Fincher instead of Tarsem Singh",
            contribution: 0.35,
          },
        ],
      },
      {
        step_key: "synthesize",
        score: 0.28,
        rank: 3,
        reasons: [
          {
            feature: "wrong_chain",
            text: "The final answer uses the incorrect bridge chain.",
            evidence: "United States came from the wrong director",
            contribution: 0.2,
          },
        ],
      },
    ],
  },
  r_natural_fail: {
    run_id: "r_natural_fail",
    model_version: "ranker-v3",
    latency_ms: 1.1,
    ranking: [
      {
        step_key: "synthesize",
        score: 0.93,
        rank: 1,
        reasons: [
          {
            feature: "subanswer_conflict",
            text: "The final answer doesn't match any sub-answer.",
            evidence: "American + American should produce “yes”, not “no”",
            contribution: 0.55,
          },
          {
            feature: "unsupported_rationale",
            text: "The rationale compares cities instead of countries.",
            evidence: "Sacramento and Brooklyn are both in the United States",
            contribution: 0.24,
          },
          {
            feature: "upstream_agreement",
            text: "Both checked sub-answers agree and are supported.",
            evidence: "q1: American; q2: American",
            contribution: 0.14,
          },
        ],
      },
      {
        step_key: "q2/extract#0",
        score: 0.19,
        rank: 2,
        reasons: [
          {
            feature: "normal_step",
            text: "This answer is supported by its passage.",
            evidence: "Born in New York, United States",
            contribution: 0.08,
          },
        ],
      },
      {
        step_key: "q1/extract#0",
        score: 0.17,
        rank: 3,
        reasons: [
          {
            feature: "normal_step",
            text: "This answer is supported by its passage.",
            evidence: "Born in California, United States",
            contribution: 0.07,
          },
        ],
      },
    ],
  },
};

const templates = [
  tasks[0].question,
  tasks[1].question,
  tasks[2].question,
  "Was the author of Dune born before the author of Foundation?",
  "What city is home to the university attended by the inventor?",
  "Did both films win the same award?",
  "Which actor was born earlier?",
  "What language is spoken where the painter was born?",
  "Are both musicians from Canada?",
  "Which river crosses the capital?",
  "Who directed the adaptation of the novel?",
  "Was the stadium built before the museum?",
  "What country hosted the tournament winner?",
  "Did the two scientists share a field?",
  "Which newspaper began publication first?",
];
let seed = 918273;
const random = () => {
  seed |= 0;
  seed = (seed + 0x6d2b79f5) | 0;
  let value = Math.imul(seed ^ (seed >>> 15), 1 | seed);
  value = (value + Math.imul(value ^ (value >>> 7), 61 | value)) ^ value;
  return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
};
export const runs: RunSummary[] = Array.from({ length: 300 }, (_, index) => {
  const failed = random() < 0.61;
  const origins = ["clean", "fault", "organic", "replay", "repair"];
  const origin = origins[Math.floor(random() * origins.length)];
  const culprit = ["retrieve", "extract", "plan", "check", "synthesize"][
    Math.floor(random() * 5)
  ];
  return {
    run_id: `r_gen_${String(index).padStart(3, "0")}`,
    task_id: `task_${index % 15}`,
    question: templates[index % templates.length],
    origin,
    outcome: failed ? "fail" : "pass",
    score_f1: failed ? 0 : 1,
    n_steps: 6 + Math.floor(random() * 11),
    created_at: new Date(now - index * 487000).toISOString(),
    predicted_culprit: failed
      ? {
          step_key:
            culprit === "plan" || culprit === "synthesize"
              ? culprit
              : `q1/${culprit}#0`,
          score: 0.48 + random() * 0.5,
        }
      : null,
    parent_run_id:
      origin === "replay" || origin === "repair" ? "r_scott_fail" : null,
  };
});
runs.unshift(
  {
    run_id: "r_scott_fail",
    task_id: "task_scott",
    question: tasks[0].question,
    origin: "fault",
    outcome: "fail",
    score_f1: 0,
    n_steps: 8,
    created_at: details.r_scott_fail.run.created_at,
    predicted_culprit: { step_key: "q1/retrieve#0", score: 0.91 },
    parent_run_id: null,
  },
  {
    run_id: "r_scott_fixed",
    task_id: "task_scott",
    question: tasks[0].question,
    origin: "replay",
    outcome: "pass",
    score_f1: 1,
    n_steps: 8,
    created_at: new Date(now - 120000).toISOString(),
    predicted_culprit: null,
    parent_run_id: "r_scott_fail",
  },
  {
    run_id: "r_film_fail",
    task_id: tasks[1].task_id,
    question: tasks[1].question,
    origin: "fault",
    outcome: "fail",
    score_f1: 0,
    n_steps: 8,
    created_at: details.r_film_fail.run.created_at,
    predicted_culprit: { step_key: "q1/extract#0", score: 0.94 },
    parent_run_id: null,
  },
  {
    run_id: "r_natural_fail",
    task_id: tasks[2].task_id,
    question: tasks[2].question,
    origin: "organic",
    outcome: "fail",
    score_f1: 0,
    n_steps: 8,
    created_at: details.r_natural_fail.run.created_at,
    predicted_culprit: { step_key: "synthesize", score: 0.93 },
    parent_run_id: null,
  },
);

export function getMockDetail(runId: string): RunDetailResponse {
  if (details[runId]) return details[runId];
  const summary = runs.find((item) => item.run_id === runId) ?? runs[0];
  const failed = summary.outcome === "fail";
  const generated = detail(summary.run_id, failed ? "fail" : "pass", failed);
  const task: TaskRecord = {
    ...generated.task,
    task_id: summary.task_id,
    question: summary.question,
    gold_answer: failed ? "expected answer" : generated.task.gold_answer,
  };
  return {
    ...generated,
    run: {
      ...generated.run,
      task_id: summary.task_id,
      origin: summary.origin,
      parent_run_id: summary.parent_run_id,
      outcome: summary.outcome,
      score_f1: summary.score_f1,
      n_steps: summary.n_steps,
      created_at: summary.created_at,
    },
    task,
    fault: null,
    label: summary.predicted_culprit
      ? {
          run_id: summary.run_id,
          culprit_step_key: summary.predicted_culprit.step_key,
          method: "counterfactual",
          verified: true,
          confidence: 0.81,
          n_replays: 4,
          matches_injection: null,
        }
      : null,
  };
}

export function getMockDiagnosis(runId: string): DiagnosisResponse {
  if (diagnoses[runId]) return diagnoses[runId];
  const summary = runs.find((item) => item.run_id === runId);
  if (!summary?.predicted_culprit)
    return {
      run_id: runId,
      model_version: "ranker-v3",
      latency_ms: 1.2,
      ranking: [],
    };
  return {
    run_id: runId,
    model_version: "ranker-v3",
    latency_ms: 1.2,
    ranking: [
      {
        step_key: summary.predicted_culprit.step_key,
        score: summary.predicted_culprit.score,
        rank: 1,
        reasons: [
          {
            feature: "trace_anomaly",
            text: "This step differs most from successful runs.",
            evidence: "Its trace features are outside the normal range",
            contribution: 0.46,
          },
          {
            feature: "downstream_effect",
            text: "Later answers depend on this output.",
            evidence: "The dependency route continues to synthesize",
            contribution: 0.25,
          },
          {
            feature: "counterfactual_gain",
            text: "Changing this step is most likely to change the outcome.",
            evidence: "Counterfactual replay improved the answer",
            contribution: 0.17,
          },
        ],
      },
    ],
  };
}
export const evaluation: EvalResponse = {
  test_questions: 120,
  headline: {
    top1_seen: 0.84,
    top1_heldout: 0.71,
    top1_natural: 0.63,
    reused: 0.76,
    latency_ms: 1.2,
  },
  baselines: [
    { name: "Black Box", top1: 0.84, top3: 0.94 },
    { name: "LLM reading the trace", top1: 0.62, top3: 0.79 },
    { name: "Heuristic", top1: 0.48, top3: 0.65 },
    { name: "Last step", top1: 0.29, top3: 0.42 },
    { name: "Random", top1: 0.12, top3: 0.31 },
  ],
  lofo: [
    { name: "Distractor retrieval", top1: 0.74, top3: 0.91, mrr: 0.82 },
    { name: "Wrong extraction", top1: 0.69, top3: 0.86, mrr: 0.77 },
    { name: "Unsupported answer", top1: 0.67, top3: 0.84, mrr: 0.75 },
    { name: "Broken plan", top1: 0.73, top3: 0.89, mrr: 0.8 },
  ],
  by_fault: [
    { name: "Distractor retrieval", accuracy: 0.88, heldout: false },
    { name: "Wrong extraction", accuracy: 0.82, heldout: false },
    { name: "Unsupported answer", accuracy: 0.71, heldout: true },
    { name: "Broken plan", accuracy: 0.68, heldout: true },
  ],
  proof_cost: { bisect: 3.6, linear: 11.2, verified: 0.92 },
  fixes: { top1: 0.58, top3: 0.74 },
};
export const fleet: FleetResponse = {
  total_failed: 612,
  by_step_name: [
    { name: "retrieve", count: 251, pct: 0.41 },
    { name: "extract", count: 135, pct: 0.22 },
    { name: "plan", count: 92, pct: 0.15 },
    { name: "synthesize", count: 80, pct: 0.13 },
    { name: "check", count: 54, pct: 0.09 },
  ],
  by_reason: [
    {
      feature: "retrieval_support",
      text: "Answer not in retrieved text",
      count: 190,
    },
    {
      feature: "retrieval_score",
      text: "Retrieval score far below typical",
      count: 147,
    },
    {
      feature: "unsupported",
      text: "Check flagged unsupported answer",
      count: 104,
    },
  ],
  by_fault_type: [
    { fault_type: "distractor_retrieval", count: 180, pct: 0.29 },
    { fault_type: "wrong_extraction", count: 132, pct: 0.22 },
  ],
};
