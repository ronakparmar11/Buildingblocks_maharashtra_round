import { AlertTriangle, ArrowRight, Map, Merge, Search, ShieldCheck, TextSelect, TrendingUp } from "lucide-react";
import { Link } from "react-router-dom";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useOverview } from "../api/hooks";
import { EmptyState, ErrorState, Skeleton } from "../components/ui";
import { CHART } from "../lib/chartColors";
import { useWorkspace, workspaceDetails } from "../context/workspace";
import { t } from "../lib/vocab";

const inr = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});
const icons = { retrieve: Search, extract: TextSelect, plan: Map, check: ShieldCheck, synthesize: Merge };
const severityStyles: Record<string, { dot: string; bg: string }> = {
  high: { dot: "bg-warning", bg: "bg-warning-tint" },
  medium: { dot: "bg-caution", bg: "bg-caution-tint" },
  low: { dot: "bg-graphite", bg: "bg-rule-soft" },
};
const words = (value: string) =>
  value.replaceAll("_", " ").replace(/^./, (letter) => letter.toUpperCase());

function HorizontalBars({
  rows,
  kind,
}: {
  rows: { name: string; count: number; pct: number }[] | { feature: string; text: string; count: number }[];
  kind: "steps" | "reasons";
}) {
  const maximum = Math.max(1, ...rows.map((row) => row.count));
  return (
    <div className="mt-4 space-y-2">
      {rows.map((row, index) => {
        const key = "name" in row ? row.name : row.feature;
        const label = "name" in row ? words(row.name) : row.text;
        const Icon = "name" in row ? icons[row.name as keyof typeof icons] ?? Map : null;
        const pct = (row.count / maximum) * 100;
        return (
          <Link
            key={key}
            to={`/conversations?outcome=fail&${kind === "steps" ? "cause_name" : "reason"}=${encodeURIComponent(key)}`}
            className="group grid grid-cols-[minmax(130px,1fr)_minmax(90px,1.1fr)_42px] items-center gap-3 rounded-node px-3 py-2.5 text-sm transition-colors hover:bg-rule-soft/60"
          >
            <span className="flex min-w-0 items-center gap-2.5 truncate">
              {Icon && <Icon className="h-4 w-4 shrink-0 text-graphite transition-colors group-hover:text-orange" />}
              <span className="truncate font-medium">{label}</span>
            </span>
            <span className="h-2 overflow-hidden rounded-chip bg-rule-soft">
              <span
                className={`block h-full rounded-chip transition-all ${index === 0 ? "bg-orange" : "bg-graphite"}`}
                style={{ width: `${pct}%` }}
              />
            </span>
            <span className="text-right font-mono text-xs text-graphite">{row.count}</span>
          </Link>
        );
      })}
    </div>
  );
}

const kpiAccents = ["border-l-orange", "border-l-warning", "border-l-caution", "border-l-advisory", "border-l-warning"];

export default function OverviewPage() {
  const { workspace } = useWorkspace();
  const overview = useOverview();
  if (overview.isLoading)
    return (
      <div className="mx-auto max-w-[1440px] space-y-5 px-6 py-7">
        <Skeleton className="h-16 w-2/3" />
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">{Array.from({ length: 5 }, (_, i) => <Skeleton key={i} className="h-24" />)}</div>
        <div className="grid grid-cols-2 gap-6"><Skeleton className="h-72" /><Skeleton className="h-72" /></div>
      </div>
    );
  if (overview.isError) return <ErrorState onRetry={() => overview.refetch()} />;
  const data = overview.data;
  if (!data?.kpis.conversations)
    return (
      <div className="mx-auto max-w-[1440px] px-4 py-6 sm:px-6">
        <h1 className="heading text-xl">{workspaceDetails[workspace].name}</h1>
        <EmptyState
          title="No conversations yet. Run a simulation to see how Black Box catches wrong answers."
          action={
            <Link
              to="/lab"
              className="inline-flex h-9 items-center justify-center rounded-control bg-orange px-4 text-sm font-medium text-white transition-colors hover:bg-[#e54600]"
            >
              Run a simulation
            </Link>
          }
        />
      </div>
    );
  const chartData = data.daily.map((item) => ({
    ...item,
    label: new Date(`${item.date}T00:00:00`).toLocaleDateString("en-IN", { weekday: "short" }),
    percentage: item.rate * 100,
  }));
  const kpis = [
    { value: data.kpis.conversations.toLocaleString("en-IN"), label: `${t("runs")} this week` },
    { value: `${(data.kpis.failure_rate * 100).toFixed(1)}%`, label: "answered wrong this week" },
    { value: inr.format(data.kpis.estimated_cost_inr), label: "estimated cost of wrong answers" },
    { value: String(data.kpis.open_incidents), label: "open incidents" },
    { value: String(data.kpis.wrong), label: workspace === "nimbu" ? "wrong agent replies" : "wrong final answers" },
  ];
  return (
    <div className="mx-auto max-w-[1440px] px-4 py-6 sm:px-6">
      {/* ─── Header ─── */}
      <div className="mb-6">
        <h1 className="heading text-2xl">{workspaceDetails[workspace].name}</h1>
        <p className="mt-1 text-md text-graphite">{data.headline}</p>
      </div>

      {/* ─── KPI cards ─── */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5 sm:gap-4">
        {kpis.map((item, i) => (
          <div
            key={item.label}
            className={`rounded-panel border border-rule ${kpiAccents[i]} border-l-[3px] bg-panel p-4 sm:p-5 ${i === 0 ? "col-span-2 sm:col-span-1" : ""}`}
          >
            <strong className="block font-mono text-2xl leading-none text-ink">
              {/[%₹]/.test(item.value)
                ? item.value.split(/(%|₹)/).map((part, j) =>
                    part === "%" || part === "₹"
                      ? <span key={j} className="font-sans text-lg text-graphite">{part}</span>
                      : <span key={j}>{part}</span>
                  )
                : item.value}
            </strong>
            <p className="mt-1.5 text-sm leading-snug text-graphite">{item.label}</p>
          </div>
        ))}
      </div>

      {/* ─── Chart + Incidents ─── */}
      <div className="mt-6 grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
        <section className="rounded-panel border border-rule bg-panel p-5 sm:p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <span className="grid h-8 w-8 place-items-center rounded-control bg-orange-tint text-orange"><TrendingUp className="h-4 w-4" /></span>
              <h2 className="heading text-lg">Wrong answers per day</h2>
            </div>
            <span className="rounded-chip bg-rule-soft px-2.5 py-1 text-xs text-graphite">Last 7 days</span>
          </div>
          <div className="mt-4 h-[200px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
                <CartesianGrid vertical={false} stroke={CHART.rule} />
                <XAxis dataKey="label" axisLine={false} tickLine={false} tick={{ fill: CHART.graphite, fontSize: 12 }} />
                <YAxis tickFormatter={(value) => `${value}%`} axisLine={false} tickLine={false} tick={{ fill: CHART.graphite, fontSize: 12 }} />
                <Tooltip
                  formatter={(value) => [`${Number(value).toFixed(1)}%`, "Answered wrong"]}
                  contentStyle={{ borderRadius: 8, border: `1px solid ${CHART.rule}`, backgroundColor: CHART.panel, color: CHART.ink, boxShadow: "0 4px 12px rgba(20,32,43,.1)" }}
                />
                <ReferenceLine y={data.threshold * 100} stroke={CHART.caution} strokeDasharray="5 4" label={{ value: "Alert threshold", fill: CHART.graphite, fontSize: 11, position: "insideTopRight" }} />
                <Line type="monotone" dataKey="percentage" stroke={CHART.orange} strokeWidth={2.5} dot={{ r: 3, fill: CHART.orange, strokeWidth: 2, stroke: CHART.panel }} activeDot={{ r: 5, strokeWidth: 2, stroke: CHART.panel }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>

        <section className="rounded-panel border border-rule bg-panel p-5 sm:p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <span className="grid h-8 w-8 place-items-center rounded-control bg-warning-tint text-warning"><AlertTriangle className="h-4 w-4" /></span>
              <h2 className="heading text-lg">Open incidents</h2>
            </div>
            <Link to="/incidents" className="inline-flex items-center gap-1 text-xs font-medium text-advisory transition-colors hover:text-ink">View all <ArrowRight className="h-3 w-3" /></Link>
          </div>
          <div className="mt-4 space-y-1">
            {data.open_incidents.length ? (
              data.open_incidents.slice(0, 4).map((incident) => (
                <Link
                  key={incident.incident_id}
                  to={`/incidents/${incident.incident_id}`}
                  className="group grid min-h-12 grid-cols-[auto_1fr_auto] items-center gap-3 rounded-node px-3 py-2.5 text-sm transition-colors hover:bg-paper"
                >
                  <span className={`inline-flex items-center gap-2 rounded-chip px-2 py-0.5 text-xs font-medium capitalize ${severityStyles[incident.severity].bg}`}>
                    <span className={`h-1.5 w-1.5 rounded-full ${severityStyles[incident.severity].dot}`} />
                    {incident.severity}
                  </span>
                  <span className="truncate font-medium transition-colors group-hover:text-orange" title={incident.title}>{incident.title}</span>
                  <span className="flex gap-3 whitespace-nowrap font-mono text-xs text-graphite">
                    <span>{incident.n_runs} {t("runs")}</span>
                    <span>{inr.format(incident.est_cost_inr)}</span>
                  </span>
                </Link>
              ))
            ) : (
              <div className="flex min-h-32 flex-col items-center justify-center gap-2 text-sm text-graphite">
                <ShieldCheck className="h-5 w-5 text-normal" />
                No open incidents
              </div>
            )}
          </div>
        </section>
      </div>

      {/* ─── Breakdowns ─── */}
      <div className="mt-6 grid gap-5 lg:grid-cols-2">
        <section className="rounded-panel border border-rule bg-panel p-5 sm:p-6">
          <h2 className="heading text-lg">Where failures start</h2>
          {data.by_step_name.length ? (
            <HorizontalBars rows={data.by_step_name} kind="steps" />
          ) : (
            <p className="mt-4 text-sm text-graphite">No failures in this period.</p>
          )}
        </section>
        <section className="rounded-panel border border-rule bg-panel p-5 sm:p-6">
          <h2 className="heading text-lg">Most common reasons</h2>
          {data.by_reason.length ? (
            <HorizontalBars rows={data.by_reason} kind="reasons" />
          ) : (
            <p className="mt-4 text-sm text-graphite">No failure reasons to report.</p>
          )}
        </section>
      </div>
    </div>
  );
}