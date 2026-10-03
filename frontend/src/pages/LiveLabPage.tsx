import { t } from "../lib/vocab";
import { Check, LoaderCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  useDiagnosis,
  useFaultTargets,
  useJob,
  useLiveRun,
  useRepairJob,
  useRun,
  useTasks,
} from "../api/hooks";
import type { RepairAttemptResponse } from "../api/types";
import ExecutionRoute from "../components/ExecutionRoute";
import FdrTape from "../components/FdrTape";
import TrafficSimulator from "../components/TrafficSimulator";
import { useWorkspace } from "../context/workspace";
import {
  Button,
  Combobox,
  EmptyState,
  ErrorState,
  OutcomeChip,
  SegmentedControl,
  Skeleton,
  StatChip,
} from "../components/ui";

const failureNames: Record<string, string> = {
  current_only: "Search current articles only",
  distractor_retrieval: "Distractor retrieval",
  wrong_extraction: "Wrong extraction",
  PLAN_CORRUPT: "Plan corruption",
  BAD_QUERY: "Bad query",
  DISTRACTOR_RETRIEVAL: "Distractor retrieval",
  TRUNCATED_CONTEXT: "Truncated context",
  WRONG_EXTRACTION: "Wrong extraction",
  HALLUCINATED_SYNTHESIS: "Hallucinated synthesis",
};
const businessFailureNames: Record<string, string> = {
  distractor_retrieval: "Search returns an archived article",
  DISTRACTOR_RETRIEVAL: "Search returns an archived article",
  wrong_extraction: "Reads the wrong number from the article",
  WRONG_EXTRACTION: "Reads the wrong number from the article",
  HALLUCINATED_SYNTHESIS: "Final reply contradicts the facts",
};
const StepNumber = ({
  number,
  state,
}: {
  number: number;
  state: "waiting" | "active" | "done";
}) => (
  <span
    className={`grid h-8 w-8 shrink-0 place-items-center rounded-full border text-sm font-medium ${state === "active" ? "border-orange bg-orange text-white" : state === "done" ? "border-normal bg-normal text-white" : "border-rule text-graphite"}`}
  >
    {state === "done" ? <Check className="h-4 w-4" /> : number}
  </span>
);
export default function LiveLabPage() {
  const { workspace } = useWorkspace();
  const [mode, setMode] = useState("One conversation");
  const tasks = useTasks();
  const [taskId, setTaskId] = useState("");
  const [failure, setFailure] = useState("");
  const [target, setTarget] = useState("");
  const live = useLiveRun();
  const [runId, setRunId] = useState<string>();
  const run = useRun(runId);
  const diagnosis = useDiagnosis(runId, Boolean(runId));
  const targets = useFaultTargets(taskId);
  const [reveal, setReveal] = useState(-1);
  const [fixJob, setFixJob] = useState<string>();
  const repair = useRepairJob();
  const job = useJob(fixJob);
  const [startedFixes, setStartedFixes] = useState(false);
  useEffect(() => {
    if (!run.data || reveal >= run.data.steps.length - 1) return;
    const timer = window.setInterval(
      () => setReveal((value) => value + 1),
      500,
    );
    return () => window.clearInterval(timer);
  }, [run.data, reveal]);
  useEffect(() => {
    setTarget(
      targets.data?.targets.find((item) => item.fault_type === failure)
        ?.step_key ?? "",
    );
  }, [failure, targets.data]);
  const start = () => {
    if (!taskId) return;
    live.mutate(
      {
        task_id: taskId,
        fault:
          failure && target ? { fault_type: failure, step_key: target } : null,
      },
      {
        onSuccess: (data) => {
          setRunId(data.run_id);
          setReveal(-1);
        },
      },
    );
  };
  const reset = () => {
    setRunId(undefined);
    setReveal(-1);
    setFixJob(undefined);
    setStartedFixes(false);
    live.reset();
  };
  const runDone = Boolean(run.data && reveal >= run.data.steps.length - 1);
  const ranking = runDone ? (diagnosis.data?.ranking ?? []) : [];
  const jobResult = job.data?.result as unknown as {
    repaired?: boolean;
    winning_run_id?: string | null;
    attempts?: RepairAttemptResponse[];
  } | null;
  const attempts = jobResult?.attempts ?? [];
  const completed = job.data?.status === "completed";
  const failed = job.data?.status === "failed";
  const settled = completed || failed;
  const repaired = completed && Boolean(jobResult?.repaired);
  if (tasks.isLoading)
    return <div className="space-y-5 p-6"><Skeleton className="h-8 w-36"/><div className="grid grid-cols-2 gap-6"><Skeleton className="h-40"/><Skeleton className="h-40"/></div></div>;
  if (tasks.isError) return <ErrorState onRetry={() => tasks.refetch()} />;
  if (!tasks.data?.length && mode === "One conversation")
    return <EmptyState title="No prepared demo questions are available." />;
  return (
    <div className="mx-auto max-w-[1500px] px-6 py-8 text-md">
      <h1 className="heading text-xl">Live lab</h1>
      {workspace === "nimbu" && (
        <div className="mt-5">
          <SegmentedControl options={["One conversation", "Simulate traffic"]} value={mode} onChange={setMode} />
        </div>
      )}
      {workspace === "nimbu" && mode === "Simulate traffic" ? (
        <TrafficSimulator />
      ) : (
      <>
      <div className="mt-6 grid grid-cols-2 gap-6 max-[900px]:grid-cols-1">
        <section className="flex gap-4 border-b border-rule bg-panel p-5">
          <StepNumber number={1} state={runId ? "done" : "active"} />
          <div className="min-w-0 flex-1">
            <h2 className="heading text-lg">Pick a {t("task")}</h2>
            <p className="mb-3 text-sm text-graphite">Prepared for demo</p>
            {workspace === "nimbu" && (
              <div className="mb-3 flex flex-wrap gap-2">
                {(tasks.data ?? []).slice(0, 3).map((task) => (
                  <button key={task.task_id} onClick={() => setTaskId(task.task_id)} className="max-w-full truncate rounded-chip border border-rule bg-panel px-3 py-1.5 text-left text-xs text-advisory">
                    {task.question}
                  </button>
                ))}
              </div>
            )}
            <Combobox
              value={taskId}
              onChange={setTaskId}
              placeholder={`Search ${t("task")}s…`}
              options={(tasks.data ?? []).map((task) => ({
                value: task.task_id,
                label: task.question,
              }))}
            />
          </div>
        </section>
        <section className="flex gap-4 border-b border-rule bg-panel p-5">
          <StepNumber
            number={2}
            state={runId ? "done" : taskId ? "active" : "waiting"}
          />
          <div className="min-w-0 flex-1">
            <h2 className="heading text-lg">
              Break something{" "}
              <span className="font-normal text-graphite">(optional)</span>
            </h2>
            <div className="mt-4 grid grid-cols-2 gap-3">
              <select
                aria-label="Failure type"
                value={failure}
                onChange={(event) => setFailure(event.target.value)}
                className="h-11 rounded-control border border-rule bg-panel px-3"
              >
                <option value="">No failure</option>
                {[
                  ...new Set(
                    (targets.data?.targets ?? []).map(
                      (item) => item.fault_type,
                    ),
                  ),
                ].map((value) => (
                  <option key={value} value={value}>
                    {(workspace === "nimbu" ? businessFailureNames[value] : undefined) ?? failureNames[value] ?? value}
                  </option>
                ))}
              </select>
              <select
                aria-label="Target step"
                disabled={!failure}
                value={target}
                onChange={(event) => setTarget(event.target.value)}
                className="h-11 rounded-control border border-rule bg-panel px-3 disabled:opacity-50"
              >
                <option value="">Target step</option>
                {(targets.data?.targets ?? [])
                  .filter((item) => item.fault_type === failure)
                  .map((item) => (
                    <option key={item.step_key}>{item.step_key}</option>
                  ))}
              </select>
            </div>
          </div>
        </section>
      </div>
      <div className="mt-5 flex justify-end gap-3">
        {runId && (
          <Button size="lg" onClick={reset}>
            Run again
          </Button>
        )}
        <Button
          size="lg"
          variant="orange"
          disabled={!taskId || Boolean(runId)}
          loading={live.isPending}
          onClick={start}
        >
          Run the agent
        </Button>
      </div>
      {run.isError && (
        <div className="mt-5">
          <ErrorState onRetry={() => run.refetch()} />
        </div>
      )}
      {run.data && (
        <section className="mt-6 border-y border-rule bg-panel">
          <div className="flex flex-wrap items-center gap-4 p-5">
            <h2 className="heading mr-auto max-w-4xl text-xl">
              {run.data.task.question}
            </h2>
            {runDone && (
              <>
                <span className="text-graphite">Expected</span>
                <strong>{run.data.task.gold_answer}</strong>
                <span className="text-graphite">Got</span>
                <strong className="text-3xl text-warning">
                  {run.data.run.final_answer}
                </strong>
                <OutcomeChip outcome={run.data.run.outcome} />
              </>
            )}
          </div>
          <div className="h-[360px]">
            <ExecutionRoute
              steps={run.data.steps}
              edges={run.data.edges}
              ranking={ranking}
              revealUpTo={reveal}
            />
          </div>
          <FdrTape steps={run.data.steps} ranking={ranking} />
        </section>
      )}
      {runDone && ranking[0] && (
        <section className="mt-6 flex gap-4 border-b border-rule bg-panel p-5">
          <StepNumber number={3} state={startedFixes ? "done" : "active"} />
          <div className="flex-1">
            <p className="heading text-lg">
              Most likely cause:{" "}
              <span className="font-mono text-orange">
                {ranking[0].step_key}
              </span>
            </p>
            <p className="mt-2 max-w-3xl">{ranking[0].reasons[0]?.text}</p>
            <Button
              className="mt-4"
              variant="ink"
              loading={repair.isPending}
              disabled={startedFixes}
              onClick={() => {
                setStartedFixes(true);
                repair.mutate(
                  { id: runId!, top_k: 3 },
                  { onSuccess: (data) => setFixJob(data.job_id) },
                );
              }}
            >
              Try fixes
            </Button>
          </div>
        </section>
      )}
      {runDone && diagnosis.isError && (
        <section className="mt-6 flex gap-4 border-b border-rule bg-panel p-5">
          <StepNumber number={3} state="active" />
          <div>
            <h2 className="heading text-lg">Couldn’t find the cause</h2>
            <p className="mt-2 text-sm text-graphite">
              The API could not diagnose this run. Open the full run for its
              recorded steps, or try again after the model is ready.
            </p>
          </div>
        </section>
      )}
      {startedFixes && (
        <section className="mt-4 flex gap-4 border-b border-rule bg-panel p-5">
          <StepNumber number={4} state={settled ? "done" : "active"} />
          <div className="flex-1">
            <h2 className="heading text-lg">
              {failed
                ? "Fix attempt failed"
                : repaired
                  ? "Fix found"
                  : completed
                    ? "No fix found"
                    : "Trying fixes"}
            </h2>
            <div className="mt-3 space-y-2">
              {attempts.map((attempt) => (
                <div
                  key={attempt.run_id}
                  className="flex flex-wrap items-center gap-3 text-sm"
                >
                  <span
                    className={
                      attempt.outcome === "pass"
                        ? "text-normal"
                        : "text-warning"
                    }
                  >
                    {attempt.outcome === "pass" ? "Passed" : "Failed"}
                  </span>
                  <span>
                    {failureNames[attempt.strategy] ??
                      attempt.strategy.replaceAll("_", " ")}
                  </span>
                  <StatChip>{attempt.n_executed} re-run</StatChip>
                  <StatChip>{attempt.n_reused} reused</StatChip>
                </div>
              ))}
              {!settled && (
                <p className="flex items-center gap-2 text-graphite">
                  <LoaderCircle className="h-4 w-4 animate-spin" />
                  Trying the top likely causes…
                </p>
              )}
            </div>
            {failed && (
              <p className="mt-4 text-sm text-graphite">
                The repair job stopped before it could finish. Try again after
                the API is ready.
              </p>
            )}
            {repaired && jobResult?.winning_run_id && (
              <div className="mt-4 flex gap-3">
                <Link
                  to={`/compare?a=${runId}&b=${jobResult.winning_run_id}`}
                >
                  <Button variant="ink">Compare</Button>
                </Link>
                <Link
                  to={`/conversations/${runId}`}
                  className="self-center text-sm text-advisory"
                >
                  Open full {t("run")}
                </Link>
              </div>
            )}
          </div>
        </section>
      )}
      {runId && !startedFixes && (
        <div className="mt-4 text-right">
          <Link to={`/conversations/${runId}`} className="text-sm text-advisory">
            Open full {t("run")}
          </Link>
        </div>
      )}
      </>
      )}
    </div>
  );
}
