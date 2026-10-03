import { Map, Merge, Search, ShieldCheck, TextSelect } from "lucide-react";
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
import { EmptyState, ErrorState, KpiRow, Skeleton } from "../components/ui";
import { useWorkspace, workspaceDetails } from "../context/workspace";
import { t } from "../lib/vocab";

const inr = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});
const icons = { retrieve: Search, extract: TextSelect, plan: Map, check: ShieldCheck, synthesize: Merge };
const severityStyles: Record<string, string> = {
  high: "bg-warning",
  medium: "bg-caution",
  low: "bg-graphite",
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
    <div className="mt-4 space-y-3">
      {rows.map((row, index) => {
        const key = "name" in row ? row.name : row.feature;
        const label = "name" in row ? words(row.name) : row.text;
        const Icon = "name" in row ? icons[row.name as keyof typeof icons] ?? Map : null;
        return (
          <Link
            key={key}
            to={`/conversations?outcome=fail&${kind === "steps" ? "cause_name" : "reason"}=${encodeURIComponent(key)}`}
            className="grid grid-cols-[minmax(130px,1fr)_minmax(90px,1.1fr)_42px] items-center gap-3 text-sm"
          >
            <span className="flex min-w-0 items-center gap-2 truncate">
              {Icon && <Icon className="h-4 w-4 shrink-0 text-graphite" />}
              <span className="truncate">{label}</span>
            </span>
            <span className="h-3 bg-rule-soft">
              <span
                className={`block h-full ${index === 0 ? "bg-orange" : "bg-ink"}`}
                style={{ width: `${(row.count / maximum) * 100}%` }}
              />
            </span>
            <span className="text-right font-mono text-xs">{row.count}</span>
          </Link>
        );
      })}
    </div>
  );
}

export default function OverviewPage() {
  const { workspace } = useWorkspace();
  const overview = useOverview();
  if (overview.isLoading)
    return (
      <div className="mx-auto max-w-[1440px] space-y-5 px-6 py-7">
        <Skeleton className="h-16 w-2/3" />
        <Skeleton className="h-24" />
        <div className="grid grid-cols-2 gap-6"><Skeleton className="h-64" /><Skeleton className="h-64" /></div>
      </div>
    );
  if (overview.isError) return <ErrorState onRetry={() => overview.refetch()} />;
  const data = overview.data;
  if (!data?.kpis.conversations)
    return <EmptyState title="No conversations yet. Run the traffic simulator from Live lab to see how Black Box catches wrong answers." />;
  const chartData = data.daily.map((item) => ({
    ...item,
    label: new Date(`${item.date}T00:00:00`).toLocaleDateString("en-IN", { weekday: "short" }),
    percentage: item.rate * 100,
  }));
  return (
    <div className="mx-auto max-w-[1440px] px-4 py-6 sm:px-6">
      <div className="mb-5">
        <h1 className="heading text-xl">{workspaceDetails[workspace].name}</h1>
        <p className="heading mt-1 text-lg text-graphite">{data.headline}</p>
      </div>
      <KpiRow
        items={[
          { value: data.kpis.conversations.toLocaleString("en-IN"), label: `${t("runs")} this week` },
          { value: `${(data.kpis.failure_rate * 100).toFixed(1)}%`, label: "answered wrong this week" },
          { value: inr.format(data.kpis.estimated_cost_inr), label: "estimated cost of wrong answers" },
          { value: String(data.kpis.open_incidents), label: "open incidents" },
          { value: String(data.kpis.wrong), label: workspace === "nimbu" ? "wrong agent replies" : "wrong final answers" },
        ]}
      />
      <div className="grid border-b border-rule lg:grid-cols-[1.08fr_0.92fr]">
        <section className="min-h-[252px] border-rule px-1 py-5 lg:border-r lg:pr-6">
          <div className="flex items-baseline justify-between">
            <h2 className="heading text-lg">Wrong answers per day</h2>
            <span className="text-xs text-graphite">Last 7 days</span>
          </div>
          <div className="mt-3 h-[190px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
                <CartesianGrid vertical={false} stroke="#DFE5E8" />
                <XAxis dataKey="label" axisLine={false} tickLine={false} tick={{ fill: "#5B6873", fontSize: 12 }} />
                <YAxis tickFormatter={(value) => `${value}%`} axisLine={false} tickLine={false} tick={{ fill: "#5B6873", fontSize: 12 }} />
                <Tooltip formatter={(value) => [`${Number(value).toFixed(1)}%`, "Answered wrong"]} />
                <ReferenceLine y={data.threshold * 100} stroke="#D48A00" strokeDasharray="5 4" label={{ value: "Alert threshold", fill: "#5B6873", fontSize: 11, position: "insideTopRight" }} />
                <Line type="monotone" dataKey="percentage" stroke="#FF4F00" strokeWidth={2.5} dot={{ r: 3, fill: "#FF4F00" }} activeDot={{ r: 5 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>
        <section className="min-h-[252px] py-5 lg:pl-6">
          <div className="flex items-baseline justify-between">
            <h2 className="heading text-lg">Open incidents</h2>
            <Link to="/incidents" className="text-xs text-advisory">View all</Link>
          </div>
          <div className="mt-3 divide-y divide-rule-soft border-y border-rule">
            {data.open_incidents.slice(0, 4).map((incident) => (
              <Link
                key={incident.incident_id}
                to={`/incidents/${incident.incident_id}`}
                className="grid min-h-12 grid-cols-[78px_1fr_auto] items-center gap-3 py-2 text-sm"
              >
                <span className="flex items-center gap-2 capitalize">
                  <span className={`h-2 w-2 rounded-full ${severityStyles[incident.severity]}`} />
                  {incident.severity}
                </span>
                <span className="truncate font-medium" title={incident.title}>{incident.title}</span>
                <span className="flex gap-3 whitespace-nowrap font-mono text-xs text-graphite">
                  <span>{incident.n_runs} {t("runs")}</span>
                  <span>{inr.format(incident.est_cost_inr)}</span>
                </span>
              </Link>
            ))}
          </div>
        </section>
      </div>
      <div className="grid gap-8 py-6 lg:grid-cols-2">
        <section>
          <h2 className="heading text-lg">Where failures start</h2>
          <HorizontalBars rows={data.by_step_name} kind="steps" />
        </section>
        <section>
          <h2 className="heading text-lg">Most common reasons</h2>
          <HorizontalBars rows={data.by_reason} kind="reasons" />
        </section>
      </div>
    </div>
  );
}