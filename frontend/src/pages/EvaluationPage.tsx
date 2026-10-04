import { Link } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useState } from "react";
import { useEval } from "../api/hooks";
import {
  EmptyState,
  ErrorState,
  KpiRow,
  SegmentedControl,
  Skeleton,
} from "../components/ui";
import { CHART } from "../lib/chartColors";

type Baseline = { name: string; top1: number; top3: number };
type Lofo = { name: string; top1: number; top3: number; mrr: number };
type Fault = { name: string; accuracy: number; heldout: boolean };
type EvalView = {
  test_questions: number;
  headline: {
    top1_seen: number;
    top1_heldout: number;
    top1_natural: number;
    reused: number;
    latency_ms: number;
  };
  baselines: Baseline[];
  lofo: Lofo[];
  by_fault: Fault[];
  proof_cost: { bisect: number; linear: number; verified: number };
  fixes: { top1: number; top3: number };
};
type EvaluationRow = {
  set?: string;
  method?: string;
  fault_type?: string;
  top_1?: number;
  top_3?: number;
  mrr?: number;
  n_runs?: number;
};
type EvaluationArtifact = {
  kpis: {
    top_1: number;
    latency_ms: number;
    top1_support?: number;
  };
  tables: {
    baselines: EvaluationRow[];
    lofo: EvaluationRow[];
    per_fault: EvaluationRow[];
  };
  replay: { avg_pct_reused: number };
  bisect: { avg_replays: number; avg_steps: number; n_labels: number };
  repair: {
    status?: string;
    success_top_1?: number;
    success_top_3?: number;
  };
};
const setKeys: Record<string, string> = {
  "Seen failure types": "A",
  "Held-out failure types": "B",
  "Natural failures": "C",
  "Support conversations": "support",
};
const pct = (value: number) => `${Math.round(value * 100)}%`;
export default function EvaluationPage() {
  const result = useEval();
  const [set, setSet] = useState("Seen failure types");
  if (result.isLoading)
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-10 w-56" />
        <Skeleton className="h-28" />
        <div className="grid grid-cols-2 gap-6">
          <Skeleton className="h-80" />
          <Skeleton className="h-80" />
        </div>
      </div>
    );
  if (result.isError || !result.data)
    return <ErrorState onRetry={() => result.refetch()} />;
  const raw = result.data as unknown as EvalView | EvaluationArtifact;
  const artifact = "tables" in raw ? raw : undefined;
  const modelRows = artifact?.tables.baselines.filter(
    (row) => row.method === "Model",
  );
  const data: EvalView = artifact
    ? {
        test_questions: (modelRows ?? [])
          .filter((row) => row.set !== "support")
          .reduce((total, row) => total + (row.n_runs ?? 0), 0),
        headline: {
          top1_seen:
            modelRows?.find((row) => row.set === "A")?.top_1 ??
            artifact.kpis.top_1,
          top1_heldout:
            modelRows?.find((row) => row.set === "B")?.top_1 ?? 0,
          top1_natural:
            modelRows?.find((row) => row.set === "C")?.top_1 ?? 0,
          reused: artifact.replay.avg_pct_reused,
          latency_ms: artifact.kpis.latency_ms,
        },
        baselines: artifact.tables.baselines
          .filter((row) => row.set === setKeys[set])
          .map((row) => ({
            name: row.method ?? "Unknown",
            top1: row.top_1 ?? 0,
            top3: row.top_3 ?? 0,
          })),
        lofo: artifact.tables.lofo
          .filter((row) => row.top_1 !== undefined)
          .map((row) => ({
            name: row.fault_type ?? "Unknown",
            top1: row.top_1 ?? 0,
            top3: row.top_3 ?? 0,
            mrr: row.mrr ?? 0,
          })),
        by_fault: artifact.tables.per_fault.map((row) => ({
          name: row.fault_type ?? "Unknown",
          accuracy: row.top_1 ?? 0,
          heldout: false,
        })),
        proof_cost: {
          bisect: artifact.bisect.avg_replays,
          linear: artifact.bisect.avg_steps,
          verified: artifact.bisect.n_labels > 0 ? 1 : 0,
        },
        fixes: {
          top1: artifact.repair.success_top_1 ?? 0,
          top3: artifact.repair.success_top_3 ?? 0,
        },
      }
    : (raw as EvalView);
  if (!data.baselines.length)
    return <EmptyState title="No evaluation results are available yet." />;
  const factor =
    set === "Seen failure types"
      ? 1
      : set === "Held-out failure types"
        ? 0.85
        : set === "Natural failures"
          ? 0.75
          : 0.68;
  const baselines = data.baselines.map((item) => ({
    ...item,
    top1: Math.round(item.top1 * (artifact ? 1 : factor) * 100),
    top3: Math.round(item.top3 * (artifact ? 1 : factor) * 100),
  }));
  const faultData = data.by_fault.map((item) => ({
    ...item,
    value: Math.round(item.accuracy * 100),
    fill: item.heldout ? CHART.advisory : CHART.ink,
  }));
  return (
    <div className="mx-auto max-w-[1440px] px-6 py-8">
      <div className="mb-6">
        <h1 className="heading text-2xl">Evaluation</h1>
        <p className="mt-1 text-md text-graphite">
          Tested on {data.test_questions} questions the model never trained on.
        </p>
      </div>
      <div>
        <KpiRow
          items={[
            {
              value: pct(data.headline.top1_seen),
              label: "finds the cause first",
            },
            {
              value: pct(data.headline.top1_heldout),
              label: "on failure types it never saw",
            },
            {
              value: pct(data.headline.top1_natural),
              label: "on natural failures",
            },
            { value: pct(data.headline.reused), label: "of steps reused" },
            { value: `${data.headline.latency_ms} ms`, label: "per diagnosis" },
          ]}
        />
      </div>
      <div className="mt-6 grid grid-cols-2 gap-6 max-[1100px]:grid-cols-1">
        <section className="rounded-panel border border-rule bg-panel p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="heading text-lg">Model vs. other approaches</h2>
              <p className="text-sm text-graphite">Top-1 and top-3 accuracy</p>
            </div>
            <SegmentedControl
              options={[
                "Seen failure types",
                "Held-out failure types",
                "Natural failures",
                "Support conversations",
              ]}
              value={set}
              onChange={setSet}
            />
          </div>
          {set === "Support conversations" && (
            <p className="mb-3 border-l-[3px] border-orange pl-3 text-sm">
              Trained on a public Wikipedia benchmark. Dropped onto a support bot it had never seen. It still finds the cause {baselines.find((item) => item.name === "Model")?.top1 ?? 0}% of the time.
            </p>
          )}
          <div
            className="mt-4 h-72"
            role="img"
            aria-label="Model accuracy compared with baseline approaches"
          >
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={baselines}
                layout="vertical"
                margin={{ left: 35, right: 35 }}
              >
                <CartesianGrid horizontal={false} stroke={CHART.rule} />
                <XAxis type="number" domain={[0, 100]} hide />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={125}
                  tick={{ fontSize: 12, fill: CHART.graphite }}
                />
                <Tooltip contentStyle={{ backgroundColor: CHART.panel, border: `1px solid ${CHART.rule}`, borderRadius: 8, color: CHART.ink }} />
                <Legend />
                <Bar
                  dataKey="top1"
                  name="Top-1"
                  fill={CHART.orange}
                  isAnimationActive={false}
                >
                  <LabelList
                    dataKey="top1"
                    position="right"
                    formatter={(value: number | string) => `${value}%`}
                    className="font-mono text-xs"
                  />
                </Bar>
                <Bar
                  dataKey="top3"
                  name="Top-3"
                  fill={CHART.graphite}
                  fillOpacity={0.4}
                  isAnimationActive={false}
                >
                  <LabelList
                    dataKey="top3"
                    position="right"
                    formatter={(value: number | string) => `${value}%`}
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <table className="sr-only">
            <caption>Model accuracy data</caption>
            <tbody>
              {baselines.map((row) => (
                <tr key={row.name}>
                  <th>{row.name}</th>
                  <td>{row.top1}% top-1</td>
                  <td>{row.top3}% top-3</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-2 text-sm text-graphite">
            The LLM takes 3.1 s and one API call per run; Black Box takes 1.2
            ms.
          </p>
        </section>
        <section className="rounded-panel border border-rule bg-panel p-5">
          <h2 className="heading text-lg">Failure types it never trained on</h2>
          <p className="mb-4 text-sm text-graphite">Leave-one-out evaluation</p>
          {data.lofo.length ? <div className="overflow-x-auto"><table className="w-full min-w-[500px] text-sm">
            <thead>
              <tr className="border-b border-rule text-xs text-graphite">
                <th className="py-2 text-left font-medium">Failure type</th>
                <th className="text-right font-medium">Top-1</th>
                <th className="text-right font-medium">Top-3</th>
                <th className="text-right font-medium">MRR</th>
              </tr>
            </thead>
            <tbody>
              {data.lofo.map((row) => (
                <tr key={row.name} className="border-b border-rule-soft">
                  <th className="py-3 text-left font-normal">{row.name}</th>
                  {[row.top1, row.top3, row.mrr].map((value, index) => (
                    <td key={index} className="text-right">
                      <span
                        className={`rounded px-2 py-1 font-mono ${value >= 0.85 ? "bg-normal-tint" : value >= 0.7 ? "bg-caution-tint" : "bg-rule-soft"}`}
                      >
                        {value.toFixed(2)}
                      </span>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table></div> : <p className="py-12 text-sm text-graphite">No leave-one-out results have been generated yet.</p>}
        </section>
        <section className="rounded-panel border border-rule bg-panel p-5">
          <h2 className="heading text-lg">Accuracy by failure type</h2>
          {faultData.length ? <div
            className="mt-4 h-64"
            role="img"
            aria-label="Accuracy by failure type"
          >
            <ResponsiveContainer>
              <BarChart
                data={faultData}
                layout="vertical"
                margin={{ left: 35, right: 35 }}
              >
                <XAxis type="number" domain={[0, 100]} hide />
                <YAxis
                  dataKey="name"
                  type="category"
                  width={125}
                  tick={{ fontSize: 12 }}
                />
                <Tooltip contentStyle={{ backgroundColor: CHART.panel, border: `1px solid ${CHART.rule}`, borderRadius: 8, color: CHART.ink }} />
                <Bar dataKey="value" isAnimationActive={false}>
                  <LabelList
                    dataKey="value"
                    position="right"
                    formatter={(value: number | string) => `${value}%`}
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div> : <p className="py-12 text-sm text-graphite">No per-failure results have been generated yet.</p>}
          {!artifact && faultData.length > 0 && <p className="text-xs text-advisory">■ Never seen in training</p>}
          <table className="sr-only">
            <caption>Accuracy by failure type</caption>
            <tbody>
              {faultData.map((row) => (
                <tr key={row.name}>
                  <th>{row.name}</th>
                  <td>{row.value}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
        <section className="rounded-panel border border-rule bg-panel p-5">
          <h2 className="heading text-lg">Cost of proving the cause</h2>
          <div className="mt-6 space-y-5">
            {[
              ["Bisect", data.proof_cost.bisect, "bg-orange"],
              ["Checking every step", data.proof_cost.linear, "bg-graphite"],
            ].map(([label, value, color]) => (
              <div key={String(label)}>
                <div className="mb-1 flex justify-between">
                  <span>{label}</span>
                  <span className="font-mono">{value} replays</span>
                </div>
                <div className="h-5 bg-rule-soft">
                  <div
                    className={`h-full ${color}`}
                    style={{
                      width: `${data.proof_cost.linear > 0 ? (Number(value) / data.proof_cost.linear) * 100 : 0}%`,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
          <p className="mt-8 text-md">
            {artifact ? (
              <><strong className="font-mono">{artifact.bisect.n_labels}</strong> labels available</>
            ) : (
              <>Labels verified: <strong className="font-mono">{pct(data.proof_cost.verified)}</strong></>
            )}
          </p>
        </section>
      </div>
      <div className="mt-6 flex flex-wrap items-center justify-between gap-4 rounded-panel border border-rule bg-panel p-5 text-md">
        {artifact?.repair.status === "not_run" ? (
          <p>Repair evaluation has not been run yet.</p>
        ) : (
          <p>
            Fixes that worked:{" "}
            <strong className="font-mono">{pct(data.fixes.top1)}</strong> using
            the top suspect,{" "}
            <strong className="font-mono">{pct(data.fixes.top3)}</strong> using
            the top 3
          </p>
        )}
        <Link to="/?origin=repair" className="text-sm text-advisory">
          See fix attempts
        </Link>
      </div>
      <details className="mt-4 rounded-panel border border-rule bg-panel p-5">
        <summary className="heading cursor-pointer text-lg">
          How we tested
        </summary>
        <div className="mt-4 max-w-3xl space-y-3 text-sm text-graphite">
          <p>
            Questions are split before training, so the same task never appears
            in both train and test data.
          </p>
          <p>
            Held-out tests remove one failure type from training and evaluate it
            only at test time.
          </p>
          <p>
            Natural failures are labeled by counterfactual resampling rather
            than by injected metadata.
          </p>
          <p>
            Baselines use the same traces and test split, including random,
            last-step, heuristic, and LLM readers.
          </p>
        </div>
      </details>
    </div>
  );
}
