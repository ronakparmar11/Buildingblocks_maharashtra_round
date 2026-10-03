import type {
  IncidentSummary,
  NotificationSummary,
  OverviewResponse,
  RecipientResponse,
  RuleResponse,
  RunSummary,
  WorkspaceSummary,
} from "../api/types";

const now = Date.now();
const iso = (hoursAgo: number) => new Date(now - hoursAgo * 3_600_000).toISOString();
const day = (daysAgo: number) => new Date(now - daysAgo * 86_400_000).toISOString().slice(0, 10);
const messages = [
  "can i return my lamp after two weeks?",
  "refund abhi tak account mein nahi aaya",
  "is delivery free to Pune for this kadai?",
  "I received the wrong colour, what should I do?",
  "can you change delivery address after dispatch?",
  "my mixer jar arrived cracked",
  "COD available for pincodes in Guwahati?",
  "how many days for prepaid refund please",
];

export const nimbuRuns: RunSummary[] = Array.from({ length: 200 }, (_, index) => {
  const failed = index % 15 === 0;
  return {
    run_id: `nimbu_${String(index + 1).padStart(3, "0")}`,
    task_id: `nq_${String((index % 40) + 1).padStart(3, "0")}`,
    question: messages[index % messages.length],
    origin: index % 4 === 0 ? "simulated" : "live",
    outcome: failed ? "fail" : "pass",
    score_f1: failed ? 0.08 : 0.96,
    n_steps: 7,
    created_at: iso(index * 0.82),
    predicted_culprit: failed ? { step_key: "q1/retrieve#0", score: 0.91 } : null,
    parent_run_id: null,
  };
});

export const incidents: IncidentSummary[] = [
  { incident_id: "inc_refunds_archived", title: "Refund questions answered wrong — search returned an archived policy", severity: "high", status: "open", n_runs: 14, est_cost_inr: 6300, category: "refunds", cause_step_name: "retrieve", first_seen: iso(31), last_seen: iso(0.4), owner: "" },
  { incident_id: "inc_shipping_fee", title: "Shipping fee answers wrong — pincode rule was missed", severity: "medium", status: "investigating", n_runs: 6, est_cost_inr: 2700, category: "shipping", cause_step_name: "extract", first_seen: iso(24), last_seen: iso(2), owner: "Meera" },
  { incident_id: "inc_damage_exchange", title: "Damaged item questions answered wrong — exception was omitted", severity: "medium", status: "open", n_runs: 4, est_cost_inr: 1800, category: "returns", cause_step_name: "synthesize", first_seen: iso(18), last_seen: iso(4), owner: "" },
  { incident_id: "inc_cod", title: "Cash on delivery questions answered wrong — location check failed", severity: "low", status: "fix_verified", n_runs: 3, est_cost_inr: 1350, category: "payments", cause_step_name: "check", first_seen: iso(12), last_seen: iso(6), owner: "Arjun" },
];

const dailyConversations = [24, 27, 29, 31, 30, 28, 31];
const dailyWrong = [1, 2, 3, 2, 2, 1, 3];

export const nimbuOverview: OverviewResponse = {
  headline: "4 open incidents. Refund questions are failing most.",
  kpis: { conversations: 200, wrong: 14, failure_rate: 0.07, open_incidents: 4, estimated_cost_inr: 12150 },
  daily: dailyConversations.map((conversations, index) => ({ date: day(6 - index), conversations, wrong: dailyWrong[index], rate: dailyWrong[index] / conversations })),
  open_incidents: incidents,
  by_step_name: [
    { name: "retrieve", count: 14, pct: 0.52 },
    { name: "extract", count: 6, pct: 0.22 },
    { name: "synthesize", count: 4, pct: 0.15 },
    { name: "check", count: 3, pct: 0.11 },
  ],
  by_reason: [
    { feature: "archived_policy", text: "An archived help article ranked first", count: 14 },
    { feature: "answer_support", text: "The reply was not supported by policy", count: 7 },
    { feature: "missing_exception", text: "A policy exception was missed", count: 4 },
  ],
  threshold: 0.2,
};

export const workspaces: WorkspaceSummary[] = [
  { id: "nimbu", name: "Nimbu Living support", description: "Customer support agent and help center", n_runs: 200 },
  { id: "hotpot", name: "Benchmark (HotpotQA)", description: "Public benchmark and training workspace", n_runs: 128 },
];

export const notifications: NotificationSummary[] = [
  { notification_id: "mail_1", workspace: "nimbu", rule_kind: "incident_opened", incident_id: incidents[0].incident_id, recipients: ["support-ai@nimbu.local"], subject: "New incident: refund questions answered wrong (14 conversations)", status: "sent", error: null, created_at: iso(0.3), sent_at: iso(0.3) },
  { notification_id: "mail_2", workspace: "nimbu", rule_kind: "daily_digest", incident_id: null, recipients: ["support-ai@nimbu.local"], subject: "Daily summary for Nimbu Living support: 4 open incidents, ₹12,150 estimated cost", status: "sent", error: null, created_at: iso(8), sent_at: iso(8) },
];

export const recipients: RecipientResponse[] = [
  { recipient_id: "recipient_1", name: "Support AI team", email: "support-ai@nimbu.local", workspace: "nimbu", active: true, rules: ["incident_opened", "incident_escalated", "failure_rate", "fix_verified", "daily_digest"] },
];

export const rules: RuleResponse[] = [
  { rule_id: "rule_opened", workspace: "nimbu", kind: "incident_opened", enabled: true, params: {} },
  { rule_id: "rule_escalated", workspace: "nimbu", kind: "incident_escalated", enabled: true, params: {} },
  { rule_id: "rule_failure", workspace: "nimbu", kind: "failure_rate", enabled: true, params: { threshold: 0.2, min_runs: 10 } },
  { rule_id: "rule_fix", workspace: "nimbu", kind: "fix_verified", enabled: true, params: {} },
  { rule_id: "rule_resolved", workspace: "nimbu", kind: "incident_resolved", enabled: false, params: {} },
  { rule_id: "rule_digest", workspace: "nimbu", kind: "daily_digest", enabled: true, params: {} },
];