import { ChevronLeft, ChevronRight, Search, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useRuns } from "../api/hooks";
import {
  Button,
  EmptyState,
  ErrorState,
  OutcomeChip,
  RunTypeLabel,
  ScoreMeter,
  Skeleton,
  StepKey,
} from "../components/ui";
import { t } from "../lib/vocab";

const PAGE_SIZE = 50;
const options = {
  outcome: [
    ["", "Outcome"],
    ["fail", "Failed"],
    ["pass", "Passed"],
    ["error", "Error"],
  ],
  origin: [
    ["", "Type"],
    ["fault", "Injected failure"],
    ["organic", "Natural failure"],
    ["clean", "Clean"],
    ["replay", "Replay"],
    ["repair", "Fix attempt"],
  ],
  split: [
    ["", "Split"],
    ["test", "Test"],
    ["train", "Train"],
  ],
  category: [
    ["", "Category"],
    ["refunds", "Refunds"],
    ["returns", "Returns"],
    ["shipping", "Shipping"],
    ["payments", "Payments"],
  ],
  fault_type: [
    ["", "Injected failure type"],
    ["distractor_retrieval", "Distractor retrieval"],
    ["wrong_extraction", "Wrong extraction"],
  ],
} as const;

function relativeTime(value: string) {
  const seconds = Math.max(
    1,
    Math.floor((Date.now() - new Date(value).getTime()) / 1000),
  );
  if (seconds < 60) return `${seconds} sec ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} hr ago`;
  return `${Math.floor(seconds / 86400)} days ago`;
}

export default function RunsPage() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const [search, setSearch] = useState(params.get("q") ?? "");
  const [focused, setFocused] = useState(-1);
  const rowRefs = useRef<(HTMLTableRowElement | null)[]>([]);
  const page = Math.max(1, Number(params.get("page") ?? 1));
  const apiParams = new URLSearchParams(params);
  apiParams.delete("page");
  apiParams.set("limit", String(PAGE_SIZE));
  apiParams.set("offset", String((page - 1) * PAGE_SIZE));
  const runs = useRuns(apiParams.toString());
  const active = ["q", "outcome", "origin", "split", "fault_type", "cause_name", "reason"].some((key) => params.has(key));

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const next = new URLSearchParams(params);
      if (search) next.set("q", search);
      else next.delete("q");
      next.delete("page");
      if (next.toString() !== params.toString())
        setParams(next, { replace: true });
    }, 250);
    return () => window.clearTimeout(timer);
  }, [search, params, setParams]);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if ((event.target as HTMLElement).matches("input, select, textarea"))
        return;
      const count = runs.data?.items.length ?? 0;
      if (event.key === "j" && count) {
        event.preventDefault();
        setFocused((value) => Math.min(count - 1, value + 1));
      }
      if (event.key === "k" && count) {
        event.preventDefault();
        setFocused((value) => Math.max(0, value - 1));
      }
      if (event.key === "Enter" && focused >= 0 && runs.data?.items[focused])
        navigate(`/conversations/${runs.data.items[focused].run_id}`);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [focused, navigate, runs.data]);
  useEffect(() => {
    if (focused >= 0) rowRefs.current[focused]?.focus();
  }, [focused]);

  const setFilter = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    next.delete("page");
    setParams(next);
  };
  const clear = () => {
    setSearch("");
    setParams({});
  };
  const total = runs.data?.total ?? 0;
  const start = total ? (page - 1) * PAGE_SIZE + 1 : 0;
  const end = Math.min(page * PAGE_SIZE, total);

  return (
    <div className="mx-auto max-w-[1440px] px-4 py-8 sm:px-6">
      <div className="mb-5 flex items-end justify-between">
        <h1 className="heading text-xl capitalize">{t("runs")}</h1>
        <span className="text-sm text-graphite">
          {total.toLocaleString()} {t("runs")}
        </span>
      </div>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <label className="relative min-w-56 flex-1 sm:max-w-sm">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-graphite" />
          <input
            aria-label={`Search ${t("question")}s`}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder={`Search ${t("question")}s…`}
            className="h-9 w-full rounded-control border border-rule bg-panel pl-9 pr-8"
          />
          {search && (
            <button
              aria-label="Clear search"
              onClick={() => setSearch("")}
              className="absolute right-2 top-2"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </label>
        {Object.entries(options).map(([key, values]) => (
          <select
            key={key}
            aria-label={values[0][1]}
            value={params.get(key) ?? ""}
            onChange={(event) => setFilter(key, event.target.value)}
            className={`h-9 max-w-48 rounded-chip border px-3 text-sm ${params.has(key) ? "border-advisory bg-panel text-ink" : "border-rule bg-panel text-graphite"}`}
          >
            {values.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        ))}
        {params.get("cause_name") && <span className="inline-flex h-9 items-center gap-2 rounded-chip border border-advisory bg-panel px-3 text-sm">Likely cause: {params.get("cause_name")}<button aria-label="Clear likely cause filter" onClick={() => setFilter("cause_name", "")}><X className="h-3 w-3"/></button></span>}
        {params.get("reason") && <span className="inline-flex h-9 items-center gap-2 rounded-chip border border-advisory bg-panel px-3 text-sm">Reason: {params.get("reason")}<button aria-label="Clear reason filter" onClick={() => setFilter("reason", "")}><X className="h-3 w-3"/></button></span>}
        {active && (
          <button onClick={clear} className="px-2 text-sm text-advisory">
            Clear
          </button>
        )}
      </div>
      <div className="overflow-hidden rounded-panel border border-rule bg-panel">
        <div className="divide-y divide-rule-soft md:hidden">
          {runs.isLoading
            ? Array.from({ length: 5 }, (_, index) => (
                <div key={index} className="space-y-3 p-4">
                  <div className="flex justify-between">
                    <Skeleton className="h-6 w-20" />
                    <Skeleton className="h-4 w-16" />
                  </div>
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-3 w-2/3" />
                </div>
              ))
            : runs.data?.items.map((run) => (
                <button
                  key={run.run_id}
                  type="button"
                  onClick={() => navigate(`/conversations/${run.run_id}`)}
                  className="block w-full p-4 text-left hover:bg-rule-soft/60 focus:bg-rule-soft/60"
                >
                  <span className="flex items-center justify-between gap-3">
                    <OutcomeChip outcome={run.outcome} />
                    <span
                      className="text-xs text-graphite"
                      title={new Date(run.created_at).toLocaleString()}
                    >
                      {relativeTime(run.created_at)}
                    </span>
                  </span>
                  <span className="mt-3 line-clamp-2 block text-sm font-medium">
                    {run.question}
                  </span>
                  <span className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-graphite">
                    <RunTypeLabel origin={run.origin} />
                    <span>{run.n_steps} steps</span>
                    {run.predicted_culprit && (
                      <span className="flex min-w-0 items-center gap-1.5">
                        <span>Likely cause</span>
                        <StepKey value={run.predicted_culprit.step_key} />
                      </span>
                    )}
                  </span>
                </button>
              ))}
        </div>
        <div className="hidden overflow-x-auto md:block">
          <table className="w-full table-fixed border-collapse text-left">
            <thead>
              <tr className="h-10 border-b border-rule bg-paper text-xs text-graphite">
                <th className="w-28 px-4 font-medium">Outcome</th>
                <th className="px-3 font-medium capitalize">{t("question")}</th>
                <th className="w-20 px-3 text-right font-medium">Steps</th>
                <th className="w-64 px-3 font-medium">Likely cause</th>
                <th className="w-28 px-4 font-medium">When</th>
              </tr>
            </thead>
            <tbody>
              {runs.isLoading
                ? Array.from({ length: 10 }, (_, index) => (
                    <tr
                      key={index}
                      className="h-[61px] border-b border-rule-soft"
                    >
                      <td className="px-4">
                        <Skeleton className="h-6 w-20" />
                      </td>
                      <td className="px-3">
                        <Skeleton className="h-4 w-3/4" />
                        <Skeleton className="mt-1 h-3 w-28" />
                      </td>
                      <td className="px-3">
                        <Skeleton className="ml-auto h-4 w-8" />
                      </td>
                      <td className="px-3">
                        <Skeleton className="h-6 w-48" />
                      </td>
                      <td className="px-4">
                        <Skeleton className="h-4 w-16" />
                      </td>
                    </tr>
                  ))
                : runs.data?.items.map((run, index) => (
                    <tr
                      key={run.run_id}
                      ref={(node) => {
                        rowRefs.current[index] = node;
                      }}
                      tabIndex={0}
                      onFocus={() => setFocused(index)}
                      onClick={() => navigate(`/conversations/${run.run_id}`)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter")
                          navigate(`/conversations/${run.run_id}`);
                      }}
                      className="h-[61px] cursor-pointer border-b border-rule-soft outline-none hover:bg-rule-soft/60 focus:bg-rule-soft/60"
                    >
                      <td className="px-4">
                        <OutcomeChip outcome={run.outcome} />
                      </td>
                      <td className="min-w-0 px-3">
                        <p
                          title={run.question}
                          className="truncate text-sm font-medium"
                        >
                          {run.question}
                        </p>
                        <div className="mt-0.5 flex gap-1 text-xs">
                          <RunTypeLabel origin={run.origin} />
                          {run.parent_run_id && (
                            <>
                              <span className="text-graphite">of</span>
                              <Link
                                to={`/conversations/${run.parent_run_id}`}
                                onClick={(event) => event.stopPropagation()}
                                className="font-mono text-advisory"
                              >
                                {run.parent_run_id.slice(0, 10)}…
                              </Link>
                            </>
                          )}
                        </div>
                      </td>
                      <td className="px-3 text-right font-mono text-sm">
                        {run.n_steps}
                      </td>
                      <td className="px-3">
                        {run.predicted_culprit ? (
                          <div className="flex items-center gap-2">
                            <StepKey value={run.predicted_culprit.step_key} />
                            <ScoreMeter score={run.predicted_culprit.score} />
                          </div>
                        ) : (
                          <span className="text-graphite">—</span>
                        )}
                      </td>
                      <td
                        className="px-4 text-xs text-graphite"
                        title={new Date(run.created_at).toLocaleString()}
                      >
                        {relativeTime(run.created_at)}
                      </td>
                    </tr>
                  ))}
            </tbody>
          </table>
        </div>
        {runs.isError ? (
          <ErrorState onRetry={() => runs.refetch()} />
        ) : !runs.isLoading && !runs.data?.items.length ? (
          <EmptyState
            title={
              active
                ? `No ${t("runs")} match these filters.`
                : `No ${t("runs")} yet.`
            }
            action={
              active ? (
                <Button onClick={clear}>Clear filters</Button>
              ) : (
                <Button variant="orange" onClick={() => navigate("/lab")}>
                  Run a {t("run")}
                </Button>
              )
            }
          />
        ) : (
          <div className="flex h-14 items-center justify-between border-t border-rule px-4 text-sm text-graphite">
            <span>
              Showing {start.toLocaleString()}–{end.toLocaleString()} of{" "}
              {total.toLocaleString()}
            </span>
            <div className="flex gap-2">
              <Button
                size="sm"
                disabled={page === 1}
                onClick={() => setFilter("page", String(page - 1))}
              >
                <ChevronLeft className="h-4 w-4" />
                Prev
              </Button>
              <Button
                size="sm"
                disabled={end >= total}
                onClick={() => setFilter("page", String(page + 1))}
              >
                Next
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
