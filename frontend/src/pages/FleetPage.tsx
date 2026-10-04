import { Map, Merge, Search, ShieldCheck, TextSelect } from "lucide-react";
import { Link } from "react-router-dom";
import { useFleet } from "../api/hooks";
import { EmptyState, ErrorState, Skeleton } from "../components/ui";

const icons = {
  retrieve: Search,
  extract: TextSelect,
  plan: Map,
  check: ShieldCheck,
  synthesize: Merge,
};
const words = (value: string) =>
  value.replaceAll("_", " ").replace(/^./, (letter) => letter.toUpperCase());
export default function FleetPage() {
  const fleet = useFleet();
  if (fleet.isLoading)
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-14 w-2/3" />
        <div className="grid grid-cols-2 gap-8">
          <Skeleton className="h-80" />
          <Skeleton className="h-80" />
        </div>
      </div>
    );
  if (fleet.isError) return <ErrorState onRetry={() => fleet.refetch()} />;
  if (!fleet.data?.total_failed)
    return (
      <EmptyState title="No failed runs yet. Generate runs to see patterns." />
    );
  const data = fleet.data;
  const top = data.by_step_name[0];
  return (
    <div className="mx-auto max-w-[1200px] px-6 py-10">
      <h1 className="heading text-xl">Fleet</h1>
      <p className="heading mt-5 text-2xl">
        {Math.round(top.pct * 100)}% of failures start in {top.name}.
      </p>
      <p className="mt-1 text-md text-graphite">
        Across {data.total_failed.toLocaleString()} failed runs in the test set.
      </p>
      <div className="mt-8 grid grid-cols-2 gap-10 max-[900px]:grid-cols-1">
        <section>
          <h2 className="heading text-lg">Where failures start</h2>
          <div className="mt-5 space-y-4">
            {data.by_step_name.map((row, index) => {
              const Icon = icons[row.name as keyof typeof icons] ?? Map;
              return (
                <Link
                  key={row.name}
                  to={`/?outcome=fail&cause_name=${encodeURIComponent(row.name)}`}
                  title={`${row.count} failed runs`}
                  className="grid grid-cols-[120px_1fr_48px] items-center gap-3"
                >
                  <span className="flex items-center gap-2">
                    <Icon className="h-4 w-4" />
                    {row.name}
                  </span>
                  <span className="h-5 bg-rule-soft">
                    <span
                      className={`block h-full ${index === 0 ? "bg-orange" : "bg-graphite"}`}
                      style={{ width: `${(row.pct / top.pct) * 100}%` }}
                    />
                  </span>
                  <span className="text-right font-mono text-xs">
                    {Math.round(row.pct * 100)}%
                  </span>
                </Link>
              );
            })}
          </div>
        </section>
        <section>
          <h2 className="heading text-lg">Most common reasons</h2>
          <div className="mt-5 space-y-4">
            {data.by_reason.map((row, index) => (
              <Link
                key={row.feature}
                to={`/?outcome=fail&reason=${encodeURIComponent(row.feature)}`}
                title={`${row.count} failed runs`}
                className="grid grid-cols-[minmax(150px,1fr)_120px_44px] items-center gap-3"
              >
                <span className="truncate">{row.text}</span>
                <span className="h-5 bg-rule-soft">
                  <span
                    className={`block h-full ${index === 0 ? "bg-orange" : "bg-graphite"}`}
                    style={{
                      width: `${(row.count / data.by_reason[0].count) * 100}%`,
                    }}
                  />
                </span>
                <span className="text-right font-mono text-xs">
                  {Math.round((row.count / data.total_failed) * 100)}%
                </span>
              </Link>
            ))}
          </div>
        </section>
      </div>
      <section className="mt-10 border-t border-rule pt-6">
        <h2 className="heading text-lg">By injected failure type</h2>
        <table className="mt-4 w-full max-w-2xl text-sm">
          <thead>
            <tr className="border-b border-rule text-xs text-graphite">
              <th className="py-2 text-left font-medium">
                Injected failure type
              </th>
              <th className="text-right font-medium">Runs</th>
              <th className="text-right font-medium">Share</th>
            </tr>
          </thead>
          <tbody>
            {data.by_fault_type.map((row) => (
              <tr key={row.fault_type} className="border-b border-rule-soft">
                <th className="py-3 text-left font-normal">
                  <Link
                    to={`/?outcome=fail&fault_type=${row.fault_type}`}
                    className="text-advisory"
                  >
                    {words(row.fault_type)}
                  </Link>
                </th>
                <td className="text-right font-mono">{row.count}</td>
                <td className="text-right font-mono">
                  {Math.round(row.pct * 100)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
