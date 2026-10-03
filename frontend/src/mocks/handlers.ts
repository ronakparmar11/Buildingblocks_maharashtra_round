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
  RecipientCreate,
  RecipientResponse,
  ReplayResponse,
  RunDetailResponse,
  RunListResponse,
  TaskRecord,
} from "../api/types";
import {
  incidents,
  nimbuOverview,
  nimbuRuns,
  notifications,
  recipients,
  rules,
  workspaces,
} from "./business";
import { evaluation } from "./eval";
import { fleet } from "./fleet";
import { getMockDetail, getMockDiagnosis, runs } from "./generator";
import { tasks } from "./hero-runs";

const jobs = new Map<string, { started: number; type: "repair" | "simulate" | "verify" }>();
const wait = () =>
  new Promise((resolve) => setTimeout(resolve, 250 + Math.random() * 350));
const summary = (id: string) =>
  runs.find((run) => run.run_id === id) ?? runs[0];
const refundMessages = [
  "can i return my lamp after two weeks?",
  "refund abhi tak account mein nahi aaya",
  "what is the return window for a bedsheet?",
  "can I send this vase back after 10 days?",
  "how many days for prepaid refund please",
  "the app says my refund is approved, when will it arrive?",
  "is the 30-day return policy still valid?",
];
export async function mockRequest<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  void body;
  await wait();
  const url = new URL(path, "http://mock");
  const pathname = url.pathname.replace(/^\/api/, "");
  const workspace = url.searchParams.get("workspace") ?? "hotpot";
  if (pathname === "/workspaces") return workspaces as T;
  if (pathname === "/overview")
    return (workspace === "nimbu"
      ? nimbuOverview
      : {
          headline: "No open incidents.",
          kpis: { conversations: runs.length, wrong: 8, failure_rate: 0.0625, open_incidents: 0, estimated_cost_inr: 0 },
          daily: nimbuOverview.daily.map((item) => ({ ...item, conversations: 18, wrong: 1, rate: 1 / 18 })),
          open_incidents: [],
          by_step_name: fleet.by_step_name,
          by_reason: fleet.by_reason,
          threshold: 0.2,
        }) as T;
  if (pathname === "/incidents" && method === "GET") {
    let items = workspace === "nimbu" ? [...incidents] : [];
    for (const key of ["status", "severity", "category"] as const) {
      const value = url.searchParams.get(key);
      if (value) items = items.filter((item) => item[key] === value);
    }
    return { items, total: items.length } as T;
  }
  const incidentMatch = pathname.match(/^\/incidents\/([^/]+)$/);
  if (incidentMatch && method === "GET") {
    const incident = incidents.find((item) => item.incident_id === incidentMatch[1]) ?? incidents[0];
    const related = nimbuRuns.filter((item) => item.outcome === "fail").slice(0, incident.n_runs);
    return {
      incident,
      explanation: "Customers asking about refunds are receiving the archived 30-day policy instead of the current 7-day policy.",
      representative_run: related[0],
      reasons: [
        { feature: "archived_policy", text: "An archived help article ranked first.", evidence: "Return policy (2024) — archived", contribution: 0.62 },
        { feature: "answer_support", text: "The reply contradicts the current policy.", evidence: "30 days instead of 7 days", contribution: 0.24 },
      ],
      runs: related.map((run, index) => ({ ...run, question: refundMessages[index % refundMessages.length], customer_message: refundMessages[index % refundMessages.length], agent_reply: "Yes, you can return it within 30 days.", correct_answer: "Returns are accepted within 7 days of delivery." })),
      events: [
        { event_id: "event_1", incident_id: incident.incident_id, kind: "opened", text: "Incident opened.", created_at: incident.first_seen, meta: {} },
        { event_id: "event_2", incident_id: incident.incident_id, kind: "notified", text: "Notification sent to support-ai@nimbu.local.", created_at: incident.last_seen, meta: { notification_id: "mail_1" } },
      ],
      notifications: notifications.filter((item) => item.incident_id === incident.incident_id),
    } as T;
  }
  if (incidentMatch && method === "PATCH") {
    const incident = incidents.find((item) => item.incident_id === incidentMatch[1]) ?? incidents[0];
    Object.assign(incident, body);
    return incident as T;
  }
  if (/^\/incidents\/[^/]+\/notify$/.test(pathname))
    return { notification_id: `mail_${Date.now()}` } as T;
  if (/^\/incidents\/[^/]+\/verify-fix$/.test(pathname)) {
    const id = `job_${Date.now()}`;
    jobs.set(id, { started: Date.now(), type: "verify" });
    return { job_id: id } as T;
  }
  if (pathname === "/notifications/status")
    return { configured: true, host: "localhost", port: 1025, connected: true, sender: "Black Box <alerts@blackbox.local>", last_error: null, demo_mode_blocked: false } as T;
  if (pathname === "/notifications/test" && method === "POST") return { status: "sent", error: null } as T;
  if (pathname === "/notifications" && method === "GET") return { items: workspace === "nimbu" ? notifications : [] } as T;
  const previewMatch = pathname.match(/^\/notifications\/([^/]+)\/preview$/);
  if (previewMatch) {
    const item = notifications.find((entry) => entry.notification_id === previewMatch[1]) ?? notifications[0];
    return { subject: item.subject, html: `<h1>${item.subject}</h1><p>Nimbu Living support notification.</p>`, text: `${item.subject}\n\nNimbu Living support notification.` } as T;
  }
  if (pathname === "/notifications/digest" && method === "POST") {
    const notificationId = `mail_${Date.now()}`;
    notifications.unshift({ notification_id: notificationId, workspace, rule_kind: "daily_digest", incident_id: null, recipients: recipients.filter((item) => item.active).map((item) => item.email), subject: "Daily summary for Nimbu Living support: 4 open incidents, ₹12,150 estimated cost", status: "queued", error: null, created_at: new Date().toISOString(), sent_at: null });
    return { notification_id: notificationId } as T;
  }
  if (pathname === "/recipients" && method === "GET") return (workspace === "nimbu" ? recipients : []) as T;
  if (pathname === "/recipients" && method === "POST") {
    const request = body as RecipientCreate;
    const item: RecipientResponse = {
      recipient_id: `recipient_${Date.now()}`,
      name: request.name,
      email: request.email,
      workspace: request.workspace ?? "nimbu",
      active: request.active ?? true,
      rules: request.rules ?? [],
    };
    recipients.push(item);
    return item as T;
  }
  const recipientMatch = pathname.match(/^\/recipients\/([^/]+)$/);
  if (recipientMatch && method === "PATCH") {
    const item = recipients.find((entry) => entry.recipient_id === recipientMatch[1])!;
    Object.assign(item, body);
    return item as T;
  }
  if (recipientMatch && method === "DELETE") {
    const index = recipients.findIndex((entry) => entry.recipient_id === recipientMatch[1]);
    if (index >= 0) recipients.splice(index, 1);
    return undefined as T;
  }
  if (pathname === "/rules" && method === "GET") return (workspace === "nimbu" ? rules : []) as T;
  const ruleMatch = pathname.match(/^\/rules\/([^/]+)$/);
  if (ruleMatch && method === "PUT") {
    const item = rules.find((entry) => entry.rule_id === ruleMatch[1])!;
    Object.assign(item, body);
    return item as T;
  }
  if (pathname === "/settings/business" && method === "GET") return { cost_per_wrong_answer_inr: 450 } as T;
  if (pathname === "/settings/business" && method === "PUT") return body as T;
  if (pathname === "/simulate" && method === "POST") {
    const id = `simulation_${Date.now()}`;
    jobs.set(id, { started: Date.now(), type: "simulate" });
    return { job_id: id } as T;
  }
  if (pathname === "/health")
    return {
      status: "ok",
      demo_mode: true,
      model_version: "ranker-v3",
      n_runs: workspace === "nimbu" ? nimbuRuns.length : runs.length,
    } as T & HealthResponse;
  if (pathname === "/runs" && method === "GET") {
    let filtered = workspace === "nimbu" ? [...nimbuRuns] : [...runs];
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
    return getMockDiagnosis(diagnosisMatch[1]) as T & DiagnosisResponse;
  const blastMatch = pathname.match(/^\/runs\/([^/]+)\/blast-radius$/);
  if (blastMatch) {
    const detail = getMockDetail(blastMatch[1]);
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
    jobs.set(id, { started: Date.now(), type: "repair" });
    return { job_id: id } as T & JobCreatedResponse;
  }
  const jobMatch = pathname.match(/^\/jobs\/(.+)$/);
  if (jobMatch) {
    const job = jobs.get(jobMatch[1]) ?? { started: Date.now(), type: "repair" as const };
    const elapsed = Date.now() - job.started;
    const progress = Math.min(1, elapsed / 2700);
    if (job.type === "simulate")
      return {
        status: progress >= 1 ? "completed" : "running",
        progress,
        result: {
          sent: Math.round(progress * 30),
          failed: Math.round(progress * 11),
          incidents_opened: progress > 0.55 ? 1 : 0,
          emails_sent: progress > 0.7 ? 1 : 0,
        },
      } as T & JobResponse;
    if (job.type === "verify")
      return {
        status: progress >= 1 ? "completed" : "running",
        progress,
        result: {
          n_total: 14,
          n_passed: progress >= 1 ? 12 : Math.floor(progress * 12),
          run_ids: nimbuRuns.slice(0, 14).map((run) => run.run_id),
          tokens_saved: progress >= 1 ? 18420 : Math.floor(progress * 18420),
        },
      } as T & JobResponse;
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
        strategy: "current_only",
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
  if (runMatch) {
    if (workspace === "nimbu") {
      const summary = nimbuRuns.find((item) => item.run_id === runMatch[1]) ?? nimbuRuns[0];
      const base = getMockDetail("r_natural_fail");
      return {
        ...base,
        run: { ...base.run, run_id: summary.run_id, task_id: summary.task_id, origin: summary.origin, final_answer: summary.outcome === "fail" ? "Yes, you can return it within 30 days." : "Returns are accepted within 7 days of delivery.", outcome: summary.outcome, score_f1: summary.score_f1, n_steps: summary.n_steps, created_at: summary.created_at },
        task: { ...base.task, task_id: summary.task_id, question: summary.question, gold_answer: "Returns are accepted within 7 days of delivery.", gold_titles: ["Return policy"] },
        steps: base.steps.map((step) => {
          if (step.name === "retrieve") return { ...step, output: { passages: [{ pid: "a_returns_current", title: "Return policy", text: "Returns are accepted within 7 days of delivery.", status: "current", score: 0.94 }] }, output_text: "Return policy" };
          if (step.name === "extract") return { ...step, output: { answer: "30 days" }, output_text: "30 days" };
          if (step.name === "check") return { ...step, output: { verdict: "unsupported" }, output_text: "unsupported" };
          if (step.name === "synthesize") return { ...step, output: { answer: "Yes, you can return it within 30 days." }, output_text: "Yes, you can return it within 30 days." };
          if (step.name === "plan") return { ...step, output: { subquestions: [{ id: "q1", text: "What is the current return window?" }, { id: "q2", text: "Does the product have a special exception?" }] }, output_text: "return window and exceptions" };
          return step;
        }),
      } as T & RunDetailResponse;
    }
    return getMockDetail(runMatch[1]) as T & RunDetailResponse;
  }
  if (pathname === "/compare") {
    const a = url.searchParams.get("a") ?? "r_scott_fail";
    const b = url.searchParams.get("b") ?? "r_scott_fixed";
    const ad = getMockDetail(a);
    const bd = getMockDetail(b);
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
  if (pathname === "/fleet")
    return (workspace === "nimbu"
      ? { by_step_name: nimbuOverview.by_step_name, by_reason: nimbuOverview.by_reason, by_fault_type: [], total_failed: nimbuOverview.kpis.wrong }
      : fleet) as T & FleetResponse;
  if (pathname === "/tasks")
    return (workspace === "nimbu"
      ? nimbuRuns.slice(0, 40).map((run) => ({ task_id: run.task_id, question: run.question, gold_answer: "Returns are accepted within 7 days of delivery.", qtype: "lookup", level: "medium", split: "test", gold_titles: ["Return policy"], distractor_pids: [] }))
      : tasks) as T & TaskRecord[];
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
