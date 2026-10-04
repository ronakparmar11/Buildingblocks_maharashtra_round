import { useNavigate, useSearchParams } from "react-router-dom";
import { useIncidents } from "../api/hooks";
import type { IncidentSummary } from "../api/types";
import { Button, EmptyState, ErrorState, Select, Skeleton } from "../components/ui";

const inr = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

function relativeTime(value: string) {
  const hours = Math.max(0, Math.round((Date.now() - new Date(value).getTime()) / 3_600_000));
  if (hours < 1) return "Just now";
  if (hours === 1) return "1 hour ago";
  if (hours < 24) return `${hours} hours ago`;
  return `${Math.round(hours / 24)} days ago`;
}

function Severity({ value }: { value: string }) {
  const color = value === "high" ? "bg-warning" : value === "medium" ? "bg-caution" : "bg-graphite";
  return (
    <span className="inline-flex items-center gap-2 capitalize">
      <span className={`h-2 w-2 rounded-full ${color}`} />
      {value}
    </span>
  );
}

function Status({ value }: { value: string }) {
  const normal = value === "fix_verified" || value === "resolved";
  return (
    <span className={`rounded-chip px-2.5 py-1 text-xs capitalize ${normal ? "bg-normal-tint text-normal" : "bg-rule-soft text-graphite"}`}>
      {value.replace("_", " ")}
    </span>
  );
}

export default function IncidentsPage() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const status = params.get("status") ?? "active";
  const query = new URLSearchParams();
  for (const key of ["severity", "category"])
    if (params.get(key)) query.set(key, params.get(key)!);
  if (!["active", "all"].includes(status)) query.set("status", status);
  const incidents = useIncidents(query.toString());
  const items = (incidents.data?.items ?? []).filter((item) =>
    status === "active" ? ["open", "investigating"].includes(item.status) : true,
  );
  const setFilter = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next);
  };
  const hasFilters =
    params.has("severity") ||
    params.has("category") ||
    (params.has("status") && status !== "active");
  const hasOtherStatuses = Boolean(incidents.data?.items.length);
  const showAll = () => setParams({ status: "all" });
  return (
    <div className="mx-auto max-w-[1440px] px-4 py-8 sm:px-6">
      <div className="mb-6 flex items-end justify-between">
        <div>
          <h1 className="heading text-2xl">Incidents</h1>
          <p className="mt-1 text-sm text-graphite">Handle a shared failure once, not conversation by conversation.</p>
        </div>
        <span className="rounded-chip bg-rule-soft px-2.5 py-1 text-xs text-graphite">{items.length} shown</span>
      </div>
      <div className="mb-4 flex flex-wrap gap-2">
        <Select
          aria-label="Status"
          value={status}
          onChange={(value) => setFilter("status", value)}
          placeholder="Status"
          options={[
            { value: "active", label: "Open and investigating" },
            { value: "all", label: "All statuses" },
            { value: "open", label: "Open" },
            { value: "investigating", label: "Investigating" },
            { value: "fix_verified", label: "Fix verified" },
            { value: "resolved", label: "Resolved" },
          ]}
        />
        <Select
          aria-label="Severity"
          value={params.get("severity") ?? ""}
          onChange={(value) => setFilter("severity", value)}
          placeholder="All severities"
          options={[
            { value: "", label: "All severities" },
            { value: "high", label: "High" },
            { value: "medium", label: "Medium" },
            { value: "low", label: "Low" },
          ]}
        />
        <Select
          aria-label="Category"
          value={params.get("category") ?? ""}
          onChange={(value) => setFilter("category", value)}
          placeholder="All categories"
          options={[
            { value: "", label: "All categories" },
            { value: "refunds", label: "Refunds" },
            { value: "returns", label: "Returns" },
            { value: "shipping", label: "Shipping" },
            { value: "payments", label: "Payments" },
          ]}
        />
      </div>
      {incidents.isError ? (
        <ErrorState onRetry={() => incidents.refetch()} />
      ) : !incidents.isLoading && !items.length ? (
        <EmptyState
          title={
            hasFilters
              ? "No incidents match these filters."
              : hasOtherStatuses
                ? "No open incidents."
                : "No incidents yet. Wrong answers will be grouped here as they happen."
          }
          action={
            hasFilters || hasOtherStatuses ? (
              <Button onClick={showAll}>Show all incidents</Button>
            ) : (
              <Button variant="orange" onClick={() => navigate("/lab")}>
                Run a simulation
              </Button>
            )
          }
        />
      ) : (
        <div className="overflow-hidden rounded-panel border border-rule bg-panel">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[980px] table-fixed border-collapse text-left">
              <thead>
                <tr className="h-10 border-b border-rule bg-paper text-xs text-graphite">
                  <th className="w-28 px-4 font-medium">Severity</th><th className="px-3 font-medium">Title</th><th className="w-28 px-3 text-right font-medium">Conversations</th><th className="w-32 px-3 text-right font-medium">Estimated cost</th><th className="w-32 px-3 font-medium">Status</th><th className="w-32 px-3 font-medium">Last seen</th><th className="w-28 px-4 font-medium">Owner</th>
                </tr>
              </thead>
              <tbody>
                {incidents.isLoading
                  ? Array.from({ length: 4 }, (_, index) => <tr key={index} className="h-16 border-b border-rule-soft"><td colSpan={7} className="px-4"><Skeleton className="h-5 w-full" /></td></tr>)
                  : items.map((incident: IncidentSummary) => (
                    <tr key={incident.incident_id} tabIndex={0} onClick={() => navigate(`/incidents/${incident.incident_id}`)} onKeyDown={(event) => event.key === "Enter" && navigate(`/incidents/${incident.incident_id}`)} className="h-16 cursor-pointer border-b border-rule-soft outline-none hover:bg-rule-soft/60 focus:bg-rule-soft/60">
                      <td className="px-4 text-sm"><Severity value={incident.severity} /></td>
                      <td className="truncate px-3 text-sm font-medium" title={incident.title}>{incident.title}</td>
                      <td className="px-3 text-right font-mono text-sm">{incident.n_runs}</td>
                      <td className="px-3 text-right font-mono text-sm">{inr.format(incident.est_cost_inr)}</td>
                      <td className="px-3"><Status value={incident.status} /></td>
                      <td className="px-3 text-sm text-graphite">{relativeTime(incident.last_seen)}</td>
                      <td className="px-4 text-sm">{incident.owner || "—"}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}