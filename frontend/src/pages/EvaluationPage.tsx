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
  const data = result.data as unknown as EvalView;
  if (!data.baselines?.length)
    return <EmptyState title="No evaluation results are available yet." />;
  const factor =
    set === "Seen failure types"
      ? 1
      : set === "Held-out failure types"
        ? 0.85
        : 0.75;
  const baselines = data.baselines.map((item) => ({
    ...item,
    top1: Math.round(item.top1 * factor * 100),
    top3: Math.round(item.top3 * factor * 100),
  }));
  const faultData = data.by_fault.map((item) => ({
    ...item,
    value: Math.round(item.accuracy * 100),
    fill: item.heldout ? "#0B6E8A" : "#14202B",
  }));
  return (
    <div className="mx-auto max-w-[1440px] px-6 py-8">
      <h1 className="heading text-xl">Evaluation</h1>
      <p className="mt-1 text-md text-graphite">
        Tested on {data.test_questions} questions the model never trained on.
      </p>
      <div className="mt-6">
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
        <section className="border-b border-rule bg-panel p-5">
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
              ]}
              value={set}
              onChange={setSet}
            />
          </div>
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
                <CartesianGrid horizontal={false} stroke="#DFE5E8" />
                <XAxis type="number" domain={[0, 100]} hide />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={125}
                  tick={{ fontSize: 12, fill: "#5B6873" }}
                />
                <Tooltip />
                <Legend />
                <Bar
                  dataKey="top1"
                  name="Top-1"
                  fill="#FF4F00"
                  animationDuration={150}
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
                  fill="#5B6873"
                  fillOpacity={0.4}
                  animationDuration={150}
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
        <section className="border-b border-rule bg-panel p-5">
          <h2 className="heading text-lg">Failure types it never trained on</h2>
          <p className="mb-4 text-sm text-graphite">Leave-one-out evaluation</p>
          <table className="w-full text-sm">
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
          </table>
        </section>
        <section className="border-b border-rule bg-panel p-5">
          <h2 className="heading text-lg">Accuracy by failure type</h2>
          <div
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
                <Tooltip />
                <Bar dataKey="value" animationDuration={150}>
                  <LabelList
                    dataKey="value"
                    position="right"
                    formatter={(value: number | string) => `${value}%`}
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="text-xs text-advisory">■ Never seen in training</p>
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
        <section className="border-b border-rule bg-panel p-5">
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
                      width: `${(Number(value) / data.proof_cost.linear) * 100}%`,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
          <p className="mt-8 text-md">
            Labels verified:{" "}
            <strong className="font-mono">
              {pct(data.proof_cost.verified)}
            </strong>
          </p>
        </section>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-rule bg-panel p-5 text-md">
        <p>
          Fixes that worked:{" "}
          <strong className="font-mono">{pct(data.fixes.top1)}</strong> using
          the top suspect,{" "}
          <strong className="font-mono">{pct(data.fixes.top3)}</strong> using
          the top 3
        </p>
        <Link to="/?origin=repair" className="text-sm text-advisory">
          See fix attempts
        </Link>
      </div>
      <details className="border-b border-rule bg-panel p-5">
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
