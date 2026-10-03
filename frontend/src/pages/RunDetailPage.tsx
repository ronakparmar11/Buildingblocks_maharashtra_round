import { Check, Copy, Flag } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { useDiagnosis, useRun } from "../api/hooks";
import ExecutionRoute from "../components/ExecutionRoute";
import FdrTape from "../components/FdrTape";
import Inspector from "../components/Inspector";
import {
  Button,
  ErrorState,
  OutcomeChip,
  RunTypeLabel,
  Skeleton,
  StatChip,
} from "../components/ui";

export default function RunDetailPage() {
  const { id } = useParams();
  const location = useLocation();
  const run = useRun(id);
  const diagnosis = useDiagnosis(id);
  const [diagnosed, setDiagnosed] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);
  const [revealCount, setRevealCount] = useState(0);
  const [groundTruth, setGroundTruth] = useState(false);
  const frame = useRef(0);
  const play = () => {
    if (!diagnosis.data || !run.data) return;
    const reduced = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    setDiagnosed(true);
    if (reduced) {
      setRevealCount(run.data.steps.length);
      setSelected(diagnosis.data.ranking[0]?.step_key ?? null);
      return;
    }
    const start = performance.now();
    const length = run.data.steps.length;
    const tick = (time: number) => {
      const progress = Math.min(1, (time - start) / 1100);
      setRevealCount(Math.ceil(progress * length));
      if (progress < 1) frame.current = requestAnimationFrame(tick);
      else setSelected(diagnosis.data?.ranking[0]?.step_key ?? null);
    };
    frame.current = requestAnimationFrame(tick);
  };
  useEffect(() => () => cancelAnimationFrame(frame.current), []);
  if (run.isLoading)
    return (
      <div className="space-y-4 p-6">
        <Skeleton className="h-8 w-3/5" />
        <Skeleton className="h-12 w-full" />
        <div className="grid h-[520px] grid-cols-[220px_1fr_400px] gap-px bg-rule">
          <Skeleton className="h-full" />
          <div className="bg-paper" />
          <Skeleton className="h-full" />
        </div>
      </div>
    );
  if (run.isError || !run.data)
    return <ErrorState onRetry={() => run.refetch()} />;
  const data = run.data;
  const ranking = diagnosed ? (diagnosis.data?.ranking ?? []) : [];
  const top = diagnosis.data?.ranking[0];
  const back = location.state?.from ?? "/";
  return (
    <div className="min-h-[calc(100vh-56px)] bg-paper">
      <header className="border-b border-rule bg-panel px-6 py-5">
        <div className="mx-auto max-w-[1600px]">
          <Link to={back} className="text-sm text-advisory">
            ← Runs
          </Link>
          <div className="mt-3 flex flex-wrap items-end justify-between gap-4">
            <div className="min-w-0 flex-1">
              <h1 className="heading max-w-5xl text-xl min-[1600px]:text-3xl">
                {data.task.question}
              </h1>
              <div className="mt-3 flex flex-wrap items-center gap-3 text-sm">
                <span className="text-graphite">Expected</span>
                <strong>{data.task.gold_answer}</strong>
                <span className="text-graphite">Got</span>
                <strong
                  className={data.run.outcome === "fail" ? "text-warning" : ""}
                >
                  {data.run.final_answer ?? "—"}
                </strong>
                <OutcomeChip outcome={data.run.outcome} />
                <span className="font-mono">
                  F1 {data.run.score_f1.toFixed(2)}
                </span>
                <RunTypeLabel origin={data.run.origin} />
              </div>
              {data.run.parent_run_id && (
                <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
                  <Link
                    to={`/runs/${data.run.parent_run_id}`}
                    className="font-mono text-advisory"
                  >
                    Replay of {data.run.parent_run_id}
                  </Link>
                  <StatChip>{data.run.n_executed} re-run</StatChip>
                  <StatChip>{data.run.n_reused} reused</StatChip>
                  <StatChip>
                    {data.run.tokens_saved.toLocaleString()} tokens saved
                  </StatChip>
                </div>
              )}
            </div>
            <div className="flex flex-wrap justify-end gap-2">
              {data.run.parent_run_id && <Button>Compare with original</Button>}
              {data.run.outcome === "fail" && (
                <Button disabled={!diagnosed}>Try fixes</Button>
              )}
              {diagnosed ? (
                <Button variant="quiet">
                  Diagnosed in {diagnosis.data?.latency_ms.toFixed(1)} ms
                </Button>
              ) : (
                <Button
                  variant="orange"
                  onClick={play}
                  loading={diagnosis.isLoading}
                >
                  Find the cause
                </Button>
              )}
            </div>
          </div>
        </div>
      </header>
      <div className="mx-auto grid max-w-[1600px] grid-cols-[220px_minmax(0,1fr)_400px] grid-rows-[minmax(420px,calc(100vh-300px))_96px] max-[1200px]:grid-cols-[minmax(0,1fr)_400px] max-[900px]:grid-cols-1 max-[900px]:grid-rows-[430px_auto_96px]">
        <aside className="border-r border-rule bg-panel p-5 max-[1200px]:hidden">
          <h2 className="heading mb-5 text-lg">Run facts</h2>
          <dl className="space-y-4">
            {[
              ["Steps", data.run.n_steps],
              ["Tokens spent", data.run.tokens_total.toLocaleString()],
              ["Duration", `${(data.run.latency_ms / 1000).toFixed(1)} s`],
              ["Model", data.steps.find((step) => step.model)?.model ?? "—"],
              ["Created", new Date(data.run.created_at).toLocaleString()],
            ].map(([label, value]) => (
              <div key={String(label)}>
                <dt className="text-xs text-graphite">{label}</dt>
                <dd className="font-mono text-sm">{value}</dd>
              </div>
            ))}
            <div>
              <dt className="text-xs text-graphite">Run ID</dt>
              <dd className="flex items-center gap-2 font-mono text-xs">
                {data.run.run_id}
                <button
                  aria-label="Copy run ID"
                  onClick={() => navigator.clipboard.writeText(data.run.run_id)}
                >
                  <Copy className="h-3.5 w-3.5" />
                </button>
              </dd>
            </div>
          </dl>
          <label className="mt-8 flex items-center justify-between gap-3 border-t border-rule pt-5 text-sm">
            <span>Show ground truth</span>
            <input
              type="checkbox"
              checked={groundTruth}
              onChange={(event) => setGroundTruth(event.target.checked)}
              className="h-4 w-4 accent-advisory"
            />
          </label>
          <p className="mt-2 text-xs text-graphite">
            Hidden by default so you see the model's answer first.
          </p>
          {groundTruth && (
            <div className="mt-4 space-y-2 text-xs">
              <p className="flex gap-2">
                <Flag className="h-3.5 w-3.5" />
                Injected here: {data.fault?.fault_type.replaceAll("_", " ")}
              </p>
              <p className="flex gap-2">
                <Check className="h-3.5 w-3.5" />
                Proven cause
              </p>
            </div>
          )}
        </aside>
        <section className="min-w-0">
          <ExecutionRoute
            steps={data.steps}
            edges={data.edges}
            ranking={ranking.slice(0, revealCount)}
            selectedKey={hovered ?? selected}
            onSelect={setSelected}
            groundTruth={
              groundTruth
                ? {
                    injected: data.fault?.step_key,
                    proven: data.label?.culprit_step_key,
                  }
                : undefined
            }
          />
        </section>
        <Inspector
          runId={data.run.run_id}
          step={data.steps.find((step) => step.step_key === selected)}
          ranking={ranking}
          onSelect={setSelected}
        />
        <div className="col-span-3 max-[1200px]:col-span-2 max-[900px]:col-span-1">
          <FdrTape
            steps={data.steps}
            ranking={ranking}
            selectedKey={selected}
            hoverKey={hovered}
            onHover={setHovered}
            onSelect={setSelected}
            revealCount={revealCount}
          />
        </div>
      </div>
    </div>
  );
}
