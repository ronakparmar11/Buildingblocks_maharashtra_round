import { ChevronDown, ChevronRight } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useCompare } from "../api/hooks";
import { t } from "../lib/vocab";
import ExecutionRoute from "../components/ExecutionRoute";
import {
  EmptyState,
  ErrorState,
  JsonViewer,
  OutcomeChip,
  SegmentedControl,
  Skeleton,
  StepKey,
  WordDiff,
} from "../components/ui";

export default function ComparePage() {
  const [params] = useSearchParams();
  const a = params.get("a") ?? "";
  const b = params.get("b") ?? "";
  const comparison = useCompare(a, b);
  const [mode, setMode] = useState("All steps");
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [json, setJson] = useState<Set<string>>(new Set());
  useEffect(() => {
    if (comparison.data && comparison.data.rows.length > 8)
      setMode("Changed only");
  }, [comparison.data]);
  if (!a || !b)
    return (
      <div className="mx-auto max-w-3xl px-6 py-16 text-center">
        <h1 className="heading text-xl">Compare {t("runs")}</h1>
        <p className="mt-4 text-graphite">
          Pick two {t("runs")} to compare. Open a replay and choose Compare with
          original.
        </p>
      </div>
    );
  if (comparison.isLoading)
    return (
      <div className="space-y-5 p-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-2 gap-8">
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
        </div>
        <Skeleton className="h-48" />
        <Skeleton className="h-80" />
      </div>
    );
  if (comparison.isError || !comparison.data)
    return <ErrorState onRetry={() => comparison.refetch()} />;
  const data = comparison.data;
  if (!data.rows.length)
    return <EmptyState title={`These ${t("runs")} have no steps to compare.`} />;
  const changed = data.rows.filter((row) => row.status !== "same").length;
  const same = data.rows.length - changed;
  const shown =
    mode === "Changed only"
      ? data.rows.filter((row) => row.status !== "same")
      : data.rows;
  const steps = data.rows.flatMap((row) => (row.b_step ? [row.b_step] : []));
  const edges = steps.flatMap((step) =>
    step.deps.map((source) => ({ source, target: step.step_key })),
  );
  const statuses = Object.fromEntries(
    data.rows.map((row) => [
      row.step_key,
      row.step_key === data.first_divergence
        ? "first"
        : row.status === "same"
          ? "same"
          : "changed",
    ]),
  ) as Record<string, "first" | "same" | "changed">;
  const toggle = (
    key: string,
    setter: (next: Set<string>) => void,
    current: Set<string>,
  ) => {
    const next = new Set(current);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    setter(next);
  };
  return (
    <div className="mx-auto max-w-[1600px] px-6 py-8">
      <Link to={`/conversations/${b || a}`} className="text-sm text-advisory">
        ← Back to {t("run")}
      </Link>
      <h1 className="heading mt-3 text-xl">Compare {t("runs")}</h1>
      <div className="mt-5 grid grid-cols-[1fr_56px_1fr] items-center max-[640px]:grid-cols-1">
        <div className="rounded-panel border border-rule bg-panel p-5">
          <p className="break-all font-mono text-xs text-graphite">
            Original {data.a.run_id}
          </p>
          <div className="mt-3 flex items-center gap-3">
            <OutcomeChip outcome={data.a.outcome} />
            <span>{data.a.n_steps} steps</span>
          </div>
        </div>
        <div className="h-px bg-ink max-[640px]:my-2" />
        <div className="rounded-panel border border-rule bg-panel p-5">
          <p className="break-all font-mono text-xs text-graphite">
            Replay {data.b.run_id}
          </p>
          <div className="mt-3 flex items-center gap-3">
            <OutcomeChip outcome={data.b.outcome} />
            <span>{data.b.n_steps} steps</span>
          </div>
        </div>
      </div>
      <p className="mt-4 text-md">
        {data.first_divergence
          ? `First difference at ${data.first_divergence}. `
          : ""}
        {changed} steps changed, {same} identical.
      </p>
      <div className="mt-5 h-[180px] overflow-hidden border-y border-rule">
        <ExecutionRoute
          steps={steps}
          edges={edges}
          compact
          statuses={statuses}
        />
      </div>
      <div className="mt-6 flex justify-end">
        <SegmentedControl
          options={["All steps", "Changed only"]}
          value={mode}
          onChange={setMode}
        />
      </div>
      <div className="mt-3 overflow-x-auto rounded-panel border border-rule bg-panel">
        <table className="w-full table-fixed text-left">
          <thead>
            <tr className="border-b border-rule bg-paper text-xs text-graphite">
              <th className="w-64 px-4 py-3 font-medium">Step</th>
              <th className="w-36 px-3 font-medium">Status</th>
              <th className="px-3 font-medium">Original</th>
              <th className="px-3 font-medium">Replay</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((row) => {
              const open =
                expanded.has(row.step_key) ||
                row.step_key === data.first_divergence;
              const canOpen = row.status !== "same";
              return (
                <tr
                  key={row.step_key}
                  className={`border-b border-rule-soft ${row.step_key === data.first_divergence ? "border-l-[3px] border-l-orange" : ""}`}
                >
                  <td colSpan={4} className="p-0">
                    <button
                      disabled={!canOpen}
                      onClick={() =>
                        toggle(row.step_key, setExpanded, expanded)
                      }
                      className="grid w-full grid-cols-[256px_144px_1fr_1fr] items-center text-left"
                    >
                      <span className="flex items-center gap-2 px-4 py-3">
                        {canOpen ? (
                          open ? (
                            <ChevronDown className="h-4 w-4" />
                          ) : (
                            <ChevronRight className="h-4 w-4" />
                          )
                        ) : (
                          <span className="w-4" />
                        )}
                        <StepKey value={row.step_key} />
                      </span>
                      <span className="px-3">
                        <span
                          className={`rounded-chip px-2 py-1 text-xs ${row.status === "changed" ? "bg-caution-tint text-caution" : "bg-rule-soft text-graphite"}`}
                        >
                          {row.status === "same"
                            ? "Identical"
                            : row.status === "changed"
                              ? "Changed"
                              : row.status === "only_a"
                                ? "Only in original"
                                : "Only in replay"}
                        </span>
                      </span>
                      <span className="truncate px-3 text-sm">
                        {row.a_step?.output_text ?? "—"}
                      </span>
                      <span className="truncate px-3 text-sm">
                        {row.b_step?.output_text ?? "—"}
                      </span>
                    </button>
                    {open && canOpen && (
                      <div className="border-t border-rule-soft bg-paper px-8 py-4">
                        <WordDiff parts={row.text_diff} />
                        <button
                          className="mt-3 text-xs text-advisory"
                          onClick={() => toggle(row.step_key, setJson, json)}
                        >
                          {json.has(row.step_key)
                            ? "Hide JSON diff"
                            : "Show JSON diff"}
                        </button>
                        {json.has(row.step_key) && (
                          <div className="mt-3 grid grid-cols-2 gap-3">
                            <JsonViewer value={row.a_step?.output} />
                            <JsonViewer value={row.b_step?.output} />
                          </div>
                        )}
                      </div>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
