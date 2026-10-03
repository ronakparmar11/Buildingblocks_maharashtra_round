import {
  Copy,
  Map,
  Merge,
  RefreshCw,
  Search,
  ShieldCheck,
  TextSelect,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useBlastRadius, useReplay } from "../api/hooks";
import type { DiagnosisItem, StepRecord } from "../api/types";
import {
  Button,
  JsonEditor,
  JsonViewer,
  PassageCard,
  Popover,
  ScoreMeter,
  StatChip,
  Tabs,
} from "./ui";
import { t } from "../lib/vocab";
import ReasonList from "./ReasonList";

const icons = {
  plan: Map,
  retrieve: Search,
  extract: TextSelect,
  check: ShieldCheck,
  reformulate: RefreshCw,
  synthesize: Merge,
};
export default function Inspector({
  runId,
  step,
  ranking,
  totalSteps,
  onSelect,
  onHighlight,
  replaySignal = 0,
}: {
  runId: string;
  step?: StepRecord;
  ranking: DiagnosisItem[];
  totalSteps: number;
  onSelect: (key: string) => void;
  onHighlight?: (keys?: string[]) => void;
  replaySignal?: number;
}) {
  const [tab, setTab] = useState("I/O");
  const [raw, setRaw] = useState(false);
  const [editor, setEditor] = useState("");
  const [valid, setValid] = useState(true);
  const [preview, setPreview] = useState(false);
  const userChoseTab = useRef(false);
  const item = ranking.find((rank) => rank.step_key === step?.step_key);
  const blast = useBlastRadius(runId, step?.step_key);
  const replay = useReplay(runId);
  const resetReplay = replay.reset;
  useEffect(() => {
    if (!userChoseTab.current) setTab(item ? "Why" : "I/O");
  }, [item, step?.step_key]);
  useEffect(() => {
    setEditor(JSON.stringify(step?.output ?? {}, null, 2));
    resetReplay();
    setPreview(false);
    onHighlight?.();
  }, [step?.step_key, step?.output, resetReplay, onHighlight]);
  useEffect(() => {
    if (replaySignal) {
      setTab("Replay");
      userChoseTab.current = true;
    }
  }, [replaySignal]);
  if (!step)
    return (
      <aside className="border-l border-rule bg-panel p-5 max-[900px]:fixed max-[900px]:inset-x-0 max-[900px]:bottom-0 max-[900px]:z-30 max-[900px]:max-h-[55vh] max-[900px]:border-l-0 max-[900px]:border-t max-[900px]:shadow-popover">
        <h2 className="heading text-lg">Inspector</h2>
        <p className="mt-3 text-sm text-graphite">
          Select a step on the route or the tape to inspect it.
        </p>
        {ranking[0] && (
          <Button
            className="mt-4"
            onClick={() => onSelect(ranking[0].step_key)}
          >
            Show most likely cause
          </Button>
        )}
      </aside>
    );
  const Icon = icons[step.name as keyof typeof icons] ?? Map;
  const state = step.state_snapshot as Record<string, unknown>;
  const plan = state.plan as
    { subquestions?: { id: string; text: string }[] } | undefined;
  const subanswers = (state.subanswers ?? {}) as Record<string, string>;
  const attempts = (state.attempts ?? {}) as Record<string, number>;
  const passages = Array.isArray(step.output.passages)
    ? (step.output.passages as unknown as {
        title: string;
        text: string;
        score: number;
      }[])
    : [];
  return (
    <aside className="overflow-auto border-l border-rule bg-panel max-[900px]:fixed max-[900px]:inset-x-0 max-[900px]:bottom-0 max-[900px]:z-30 max-[900px]:max-h-[60vh] max-[900px]:border-l-0 max-[900px]:border-t max-[900px]:shadow-popover">
      <div className="p-5 pb-0">
        <h2 className="truncate font-mono text-lg">{step.step_key}</h2>
        <div className="mt-1 flex items-center gap-2 text-xs text-graphite">
          <Icon className="h-4 w-4" />
          <span>{step.name}</span>
          {item && (
            <span className={item.rank === 1 ? "text-orange" : "text-caution"}>
              {item.rank === 1 ? "Most likely cause" : `Rank ${item.rank}`}
            </span>
          )}
          {item && <ScoreMeter score={item.score} />}
        </div>
      </div>
      <div className="mt-4">
        <Tabs
          tabs={["Why", "I/O", "State", "Replay"]}
          active={tab}
          onChange={(next) => {
            userChoseTab.current = true;
            setTab(next);
          }}
        />
      </div>
      <div className="p-5">
        {tab === "Why" &&
          (item ? (
            <div>
              <p className="text-md">
                This step is the{" "}
                {item.rank === 1
                  ? "most likely cause"
                  : `rank ${item.rank} likely cause`}
                . Fixing it would change{" "}
                {Math.max(0, (blast.data?.affected.length ?? 1) - 1)} later
                steps.
              </p>
              <div className="mt-5">
                <ReasonList reasons={item.reasons} />
              </div>
              <Popover
                trigger={
                  <button className="mt-6 text-sm text-advisory">
                    How this score is calculated
                  </button>
                }
              >
                The ranker combines trace features such as retrieval support,
                consistency, and downstream effects. Scores are normalized
                within this {t("run")}.
              </Popover>
            </div>
          ) : (
            <div>
              <p className="text-sm text-graphite">
                This step looks normal. Top suspects:
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                {ranking.slice(0, 3).map((rank) => (
                  <button
                    key={rank.step_key}
                    onClick={() => onSelect(rank.step_key)}
                    className="font-mono text-xs text-advisory"
                  >
                    {rank.step_key}
                  </button>
                ))}
              </div>
            </div>
          ))}
        {tab === "I/O" && (
          <div className="space-y-4">
            <details open>
              <summary className="cursor-pointer font-medium">Input</summary>
              <button
                aria-label="Copy input"
                className="my-2 flex items-center gap-1 text-xs text-advisory"
                onClick={() =>
                  navigator.clipboard.writeText(
                    JSON.stringify(step.input, null, 2),
                  )
                }
              >
                <Copy className="h-3 w-3" />
                Copy
              </button>
              <JsonViewer value={step.input} />
            </details>
            <details open>
              <summary className="cursor-pointer font-medium">Output</summary>
              <div className="my-2 flex items-center justify-between">
                <button
                  aria-label="Copy output"
                  className="flex items-center gap-1 text-xs text-advisory"
                  onClick={() =>
                    navigator.clipboard.writeText(
                      JSON.stringify(step.output, null, 2),
                    )
                  }
                >
                  <Copy className="h-3 w-3" />
                  Copy
                </button>
                {passages.length > 0 && (
                  <label className="text-xs">
                    <input
                      type="checkbox"
                      checked={raw}
                      onChange={(event) => setRaw(event.target.checked)}
                      className="mr-2"
                    />
                    Raw JSON
                  </label>
                )}
              </div>
              {passages.length && !raw ? (
                <div className="space-y-2">
                  {passages.map((passage, index) => (
                    <PassageCard key={index} passage={passage} />
                  ))}
                </div>
              ) : (
                <JsonViewer value={step.output} />
              )}
            </details>
            <div className="flex flex-wrap gap-x-3 gap-y-1 border-t border-rule pt-3 font-mono text-xs text-graphite">
              <span>{step.latency_ms} ms</span>
              <span>{step.tokens_in} in</span>
              <span>{step.tokens_out} out</span>
              <span>{step.model ?? "No model"}</span>
              <span>
                {step.reused
                  ? "Reused"
                  : step.cache_hit
                    ? "From recording"
                    : "Re-run"}
              </span>
            </div>
          </div>
        )}
        {tab === "State" && (
          <div className="space-y-5">
            <section>
              <h3 className="heading mb-2">Plan</h3>
              {plan?.subquestions?.length ? (
                <ol className="list-decimal space-y-2 pl-5">
                  {plan.subquestions.map((question) => (
                    <li key={question.id}>{question.text}</li>
                  ))}
                </ol>
              ) : (
                <p className="text-sm text-graphite">No plan recorded yet.</p>
              )}
            </section>
            <section>
              <h3 className="heading mb-2">Sub-answers</h3>
              <table className="w-full text-sm">
                <tbody>
                  {Object.entries(subanswers).map(([key, value]) => (
                    <tr key={key} className="border-b border-rule-soft">
                      <th className="py-2 text-left font-mono font-normal">
                        {key}
                      </th>
                      <td className="py-2 text-right">{value}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
            <section>
              <h3 className="heading mb-2">Attempts</h3>
              <div className="flex flex-wrap gap-2">
                {Object.entries(attempts).map(([key, value]) => (
                  <span key={key} className="font-mono text-xs">
                    {key}: {value}
                  </span>
                ))}
              </div>
            </section>
            <section>
              <h3 className="heading mb-2 capitalize">{t("finalAnswer")}</h3>
              <p>{String(state.final ?? "Not set")}</p>
            </section>
          </div>
        )}
        {tab === "Replay" && (
          <div>
            <p className="mb-4 text-sm text-graphite">
              Change the output of {step.step_key}, then replay. Steps that
              don't depend on it are reused from the recording.
            </p>
            <JsonEditor
              value={editor}
              onChange={(value, isValid) => {
                setEditor(value);
                setValid(isValid);
              }}
            />
            <div className="mt-2 flex justify-end">
              <button
                className="text-xs text-advisory"
                onClick={() => {
                  setEditor(JSON.stringify(step.output, null, 2));
                  setValid(true);
                }}
              >
                Reset
              </button>
            </div>
            <div className="my-5 flex items-center justify-between border-y border-rule py-3">
              <span className="text-sm">
                Steps this affects:{" "}
                <strong>
                  {blast.data?.affected.length ?? "—"} of {totalSteps}
                </strong>
              </span>
              <button
                className="text-sm text-advisory"
                onClick={() => {
                  const next = !preview;
                  setPreview(next);
                  onHighlight?.(next ? blast.data?.affected : undefined);
                }}
              >
                {preview ? "Hide on graph" : "Show on graph"}
              </button>
            </div>
            {replay.data ? (
              <div
                className={`rounded-panel p-4 ${replay.data.run.outcome === "pass" ? "bg-normal-tint" : "bg-caution-tint"}`}
              >
                <p className="font-medium">
                  {replay.data.run.outcome === "pass"
                    ? `Fixed. ${replay.data.stats.n_executed} steps re-run, ${replay.data.stats.n_reused} reused, ${replay.data.stats.tokens_saved.toLocaleString()} tokens saved.`
                    : `Still failing. ${replay.data.stats.n_executed} steps re-run, ${replay.data.stats.n_reused} reused. Try another change or try fixes.`}
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <StatChip>{replay.data.stats.n_executed} re-run</StatChip>
                  <StatChip>{replay.data.stats.n_reused} reused</StatChip>
                  <StatChip>
                    {replay.data.stats.tokens_saved.toLocaleString()} tokens
                    saved
                  </StatChip>
                </div>
                <div className="mt-4 flex gap-2">
                  <a href={`/conversations/${replay.data.run.run_id}`}>
                    <Button variant="ink">Open replay</Button>
                  </a>
                  <a
                    href={`/compare?a=${runId}&b=${replay.data.run.run_id}`}
                  >
                    <Button>Compare with original</Button>
                  </a>
                </div>
              </div>
            ) : (
              <div className="flex flex-wrap justify-end gap-2">
                <Button
                  disabled={!valid}
                  loading={replay.isPending}
                  onClick={() =>
                    replay.mutate({
                      overrides: {
                        [step.step_key]: { kind: "regenerate", params: {} },
                      },
                      freeze_before_idx: null,
                    })
                  }
                >
                  Regenerate this step
                </Button>
                <Button
                  variant="ink"
                  disabled={!valid}
                  loading={replay.isPending}
                  onClick={() =>
                    replay.mutate({
                      overrides: {
                        [step.step_key]: {
                          kind: "set_output",
                          output: JSON.parse(editor),
                        },
                      },
                      freeze_before_idx: null,
                    })
                  }
                >
                  Replay from this step
                </Button>
              </div>
            )}
          </div>
        )}
      </div>
    </aside>
  );
}
