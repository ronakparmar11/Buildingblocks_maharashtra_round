import { diffWords } from "diff";
import type {
  BlastRadiusResponse,
  CompareResponse,
  DiagnosisResponse,
  FleetResponse,
  HealthResponse,
  JobCreatedResponse,
  JobResponse,
  LiveRunResponse,
  ReplayRequest,
  ReplayResponse,
  RunDetailResponse,
  RunListResponse,
  TaskRecord,
} from "../api/types";
import { details, diagnoses, evaluation, fleet, runs, tasks } from "./data";

const jobs = new Map<string, number>();
const wait = () =>
  new Promise((resolve) => setTimeout(resolve, 250 + Math.random() * 350));
const summary = (id: string) =>
  runs.find((run) => run.run_id === id) ?? runs[0];
export async function mockRequest<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  await wait();
  const url = new URL(path, "http://mock");
  const pathname = url.pathname.replace(/^\/api/, "");
  if (pathname === "/health")
    return {
      status: "ok",
      demo_mode: true,
      model_version: "ranker-v3",
      n_runs: runs.length,
    } as T & HealthResponse;
  if (pathname === "/runs" && method === "GET") {
    let filtered = [...runs];
    const outcome = url.searchParams.get("outcome");
    const origin = url.searchParams.get("origin");
    const q = url.searchParams.get("q")?.toLowerCase();
    const causeName = url.searchParams.get("cause_name");
    if (outcome) filtered = filtered.filter((run) => run.outcome === outcome);
    if (origin) filtered = filtered.filter((run) => run.origin === origin);
    if (q)
      filtered = filtered.filter((run) =>
        run.question.toLowerCase().includes(q),
      );
    if (causeName)
      filtered = filtered.filter((run) =>
        run.predicted_culprit?.step_key.includes(causeName),
      );
    const offset = Number(url.searchParams.get("offset") ?? 0);
    const limit = Number(url.searchParams.get("limit") ?? 50);
    return {
      items: filtered.slice(offset, offset + limit),
      total: filtered.length,
    } as T & RunListResponse;
  }
  const diagnosisMatch = pathname.match(/^\/runs\/([^/]+)\/diagnosis$/);
  if (diagnosisMatch)
    return (diagnoses[diagnosisMatch[1]] ?? {
      run_id: diagnosisMatch[1],
      model_version: "ranker-v3",
      latency_ms: 1.2,
      ranking: [],
    }) as T & DiagnosisResponse;
  const blastMatch = pathname.match(/^\/runs\/([^/]+)\/blast-radius$/);
  if (blastMatch) {
    const detail = details[blastMatch[1]] ?? details.r_scott_fail;
    const key = url.searchParams.get("step_key") ?? detail.steps[0].step_key;
    const affected = new Set([key]);
    let changed = true;
    while (changed) {
      changed = false;
      detail.steps.forEach((item) => {
        if (
          !affected.has(item.step_key) &&
          item.deps.some((dep) => affected.has(dep))
        ) {
          affected.add(item.step_key);
          changed = true;
        }
      });
    }
    return { step_key: key, affected: [...affected] } as T &
      BlastRadiusResponse;
  }
  const replayMatch = pathname.match(/^\/runs\/([^/]+)\/replay$/);
  if (replayMatch && method === "POST")
    return {
      run: summary("r_scott_fixed"),
      stats: {
        n_reused: 4,
        n_executed: 4,
        tokens_saved: 1962,
        tokens_total: 1450,
        latency_ms: 2100,
      },
      compare_url: `/compare?a=${replayMatch[1]}&b=r_scott_fixed`,
    } as T & ReplayResponse;
  const repairMatch = pathname.match(/^\/runs\/([^/]+)\/repair\/jobs$/);
  if (repairMatch) {
    const id = `job_${Date.now()}`;
    jobs.set(id, Date.now());
    return { job_id: id } as T & JobCreatedResponse;
  }
  const jobMatch = pathname.match(/^\/jobs\/(.+)$/);
  if (jobMatch) {
    const elapsed = Date.now() - (jobs.get(jobMatch[1]) ?? Date.now());
    const progress = Math.min(1, elapsed / 2700);
    const all = [
      {
        step_key: "q1/retrieve#0",
        strategy: "rewrite_query",
        run_id: "r_attempt_1",
        outcome: "fail",
        n_executed: 4,
        n_reused: 4,
        tokens_total: 1400,
      },
      {
        step_key: "q1/retrieve#0",
        strategy: "entity_search",
        run_id: "r_attempt_2",
        outcome: "fail",
        n_executed: 4,
        n_reused: 4,
        tokens_total: 1420,
      },
      {
        step_key: "q1/retrieve#0",
        strategy: "widen_search",
        run_id: "r_scott_fixed",
        outcome: "pass",
        n_executed: 4,
        n_reused: 4,
        tokens_total: 1450,
      },
    ];
    const count = Math.min(3, Math.floor(elapsed / 900));
    return {
      status: progress >= 1 ? "completed" : "running",
      progress,
      result: {
        repaired: progress >= 1,
        winning_run_id: progress >= 1 ? "r_scott_fixed" : null,
        attempts: all.slice(0, count),
      },
    } as T & JobResponse;
  }
  const runMatch = pathname.match(/^\/runs\/([^/]+)$/);
  if (runMatch)
    return (details[runMatch[1]] ?? details.r_scott_fail) as T &
      RunDetailResponse;
  if (pathname === "/compare") {
    const a = url.searchParams.get("a") ?? "r_scott_fail";
    const b = url.searchParams.get("b") ?? "r_scott_fixed";
    const ad = details[a] ?? details.r_scott_fail;
    const bd = details[b] ?? details.r_scott_fixed;
    const keys = [
      ...new Set([
        ...ad.steps.map((item) => item.step_key),
        ...bd.steps.map((item) => item.step_key),
      ]),
    ];
    const rows = keys.map((key) => {
      const aStep = ad.steps.find((item) => item.step_key === key) ?? null;
      const bStep = bd.steps.find((item) => item.step_key === key) ?? null;
      const status = !aStep
        ? "only_b"
        : !bStep
          ? "only_a"
          : aStep.output_text === bStep.output_text
            ? "same"
            : "changed";
      return {
        step_key: key,
        status,
        a_step: aStep,
        b_step: bStep,
        text_diff: diffWords(
          aStep?.output_text ?? "",
          bStep?.output_text ?? "",
        ).map(
          (part) =>
            `${part.added ? "+" : part.removed ? "-" : " "}${part.value}`,
        ),
      };
    });
    return {
      a: summary(a),
      b: summary(b),
      first_divergence:
        rows.find((row) => row.status !== "same")?.step_key ?? null,
      rows,
    } as T & CompareResponse;
  }
  if (pathname === "/eval") return evaluation as T;
  if (pathname === "/fleet") return fleet as T & FleetResponse;
  if (pathname === "/tasks") return tasks as T & TaskRecord[];
  if (/^\/tasks\/[^/]+\/fault-targets$/.test(pathname))
    return {
      targets: [
        { fault_type: "distractor_retrieval", step_key: "q1/retrieve#0" },
        { fault_type: "wrong_extraction", step_key: "q1/extract#0" },
      ],
    } as T;
  if (pathname === "/live/run" && method === "POST")
    return { run_id: "r_scott_fail" } as T & LiveRunResponse;
  throw Object.assign(new Error(`No mock handler for ${method} ${pathname}`), {
    status: 404,
  });
}
