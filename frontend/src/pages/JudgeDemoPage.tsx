import { Check, Cpu, Play, RotateCcw, ShieldCheck, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "../api/client";
import type { GoldenDemoResponse } from "../api/types";
import { ErrorState, OutcomeChip, Skeleton, StepKey } from "../components/ui";

export default function JudgeDemoPage() {
  const demo = useQuery({ queryKey: ["golden-demo"], queryFn: () => apiGet<GoldenDemoResponse>("/demo/golden"), staleTime: Infinity });
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [playing, setPlaying] = useState(false);
  const [visibleSteps, setVisibleSteps] = useState(0);

  useEffect(() => {
    if (!playing || !demo.data) return;
    if (visibleSteps >= demo.data.run.steps.length) {
      setPlaying(false);
      setSelectedKey(demo.data.diagnosis.ranking[0]?.step_key ?? null);
      return;
    }
    const timer = window.setTimeout(() => setVisibleSteps((value) => value + 1), 115);
    return () => window.clearTimeout(timer);
  }, [demo.data, playing, visibleSteps]);

  if (demo.isLoading) return <div className="space-y-4 p-6"><Skeleton className="h-10 w-2/3" /><Skeleton className="h-[520px] w-full" /></div>;
  if (demo.isError || !demo.data) return <ErrorState onRetry={() => demo.refetch()} />;

  const { run, diagnosis, repair } = demo.data;
  const culprit = diagnosis.ranking[0];
  const fix = repair.attempts[0];
  const selected = run.steps.find((step) => step.step_key === selectedKey) ?? run.steps[0];
  const revealed = visibleSteps > 0 ? visibleSteps : run.steps.length;
  const play = () => {
    setSelectedKey(null);
    setVisibleSteps(1);
    setPlaying(true);
  };

  return (
    <div className="min-h-[calc(100vh-56px)] bg-paper">
      <header className="border-b border-rule bg-panel px-4 py-7 sm:px-6">
        <div className="mx-auto max-w-[1440px]">
          <div className="flex flex-wrap items-start justify-between gap-5">
            <div className="max-w-4xl">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-chip bg-orange-tint px-2.5 py-1 text-xs font-medium text-orange">Golden demo</span>
                <span className="inline-flex items-center gap-1.5 text-xs text-normal"><ShieldCheck className="h-3.5 w-3.5" /> Recorded evidence, zero provider calls</span>
              </div>
              <h1 className="heading mt-4 text-2xl sm:text-3xl">From a wrong answer to a verified one-step fix</h1>
              <p className="mt-3 max-w-3xl text-sm text-graphite">This investigation is saved with the product. It stays available even when external model quota or network access does not.</p>
            </div>
            <button onClick={play} disabled={playing} className="inline-flex h-10 items-center gap-2 rounded-control bg-orange px-4 text-sm font-medium text-white disabled:opacity-60">
              {playing ? <RotateCcw className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              {playing ? "Replaying trace" : "Replay the story"}
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1440px] px-4 py-6 sm:px-6">
        <section className="grid border border-rule bg-panel lg:grid-cols-[1.3fr_0.7fr]">
          <div className="border-b border-rule p-5 lg:border-b-0 lg:border-r lg:p-7">
            <p className="text-xs text-graphite">Customer question</p>
            <h2 className="heading mt-2 max-w-3xl text-xl">{run.task.question}</h2>
            <div className="mt-6 grid gap-4 sm:grid-cols-2">
              <div className="border-l-2 border-warning pl-4"><p className="text-xs text-graphite">AI answered</p><p className="mt-1 text-lg font-semibold text-warning">{run.run.final_answer}</p></div>
              <div className="border-l-2 border-normal pl-4"><p className="text-xs text-graphite">Expected answer</p><p className="mt-1 text-lg font-semibold text-normal">{run.task.gold_answer}</p></div>
            </div>
          </div>
          <dl className="grid grid-cols-2 divide-x divide-y divide-rule">
            <div className="p-5"><dt className="text-xs text-graphite">Outcome</dt><dd className="mt-2"><OutcomeChip outcome={run.run.outcome} /></dd></div>
            <div className="p-5"><dt className="text-xs text-graphite">Trace</dt><dd className="mt-2 font-mono text-lg">{run.steps.length} steps</dd></div>
            <div className="p-5"><dt className="text-xs text-graphite">Culprit confidence</dt><dd className="mt-2 font-mono text-lg">{Math.round(culprit.score * 100)}%</dd></div>
            <div className="p-5"><dt className="text-xs text-graphite">Diagnosis time</dt><dd className="mt-2 font-mono text-lg">{diagnosis.latency_ms.toFixed(1)} ms</dd></div>
          </dl>
        </section>

        <section className="mt-6 border border-rule bg-panel">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-rule px-5 py-4">
            <div><p className="heading text-lg">Recorded execution trace</p><p className="text-xs text-graphite">Select any step to inspect its captured output.</p></div>
            <span className="font-mono text-xs text-graphite">{revealed}/{run.steps.length} visible</span>
          </div>
          <div className="overflow-x-auto p-5">
            <div className="flex min-w-max items-center">
              {run.steps.map((step, index) => (
                <div key={step.step_key} className={`flex items-center ${index >= revealed ? "opacity-15" : "opacity-100"}`}>
                  {index > 0 && <span className="h-px w-5 bg-rule sm:w-8" />}
                  <button onClick={() => setSelectedKey(step.step_key)} className={`w-28 rounded-node border px-3 py-3 text-left ${selected.step_key === step.step_key ? "border-orange bg-orange-tint" : step.step_key === culprit.step_key ? "border-caution bg-caution-tint" : "border-rule bg-white"}`}>
                    <span className="block truncate text-xs font-medium">{step.name}</span>
                    <span className="mt-1 block font-mono text-[10px] text-graphite">#{String(index + 1).padStart(2, "0")}</span>
                  </button>
                </div>
              ))}
            </div>
          </div>
          <div className="grid border-t border-rule lg:grid-cols-[0.8fr_1.2fr]">
            <div className="border-b border-rule p-5 lg:border-b-0 lg:border-r">
              <p className="text-xs text-graphite">Selected step</p>
              <div className="mt-2"><StepKey value={selected.step_key} /></div>
              <p className="mt-4 text-xs text-graphite">Latency</p><p className="font-mono text-sm">{selected.latency_ms} ms</p>
            </div>
            <div className="min-w-0 p-5">
              <p className="text-xs text-graphite">Captured output</p>
              <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap break-words font-mono text-xs leading-5 text-ink">{selected.output_text || JSON.stringify(selected.output, null, 2)}</pre>
            </div>
          </div>
        </section>

        <section className="mt-6 grid gap-px overflow-hidden border border-rule bg-rule lg:grid-cols-3">
          <div className="bg-panel p-6"><Sparkles className="h-5 w-5 text-caution" /><p className="heading mt-4 text-lg">1. Cause isolated</p><div className="mt-3"><StepKey value={culprit.step_key} /></div><p className="mt-3 text-sm text-graphite">{culprit.reasons[0]?.text}</p><p className="mt-3 border-l-2 border-caution pl-3 font-mono text-xs">{culprit.reasons[0]?.evidence}</p></div>
          <div className="bg-panel p-6"><Cpu className="h-5 w-5 text-advisory" /><p className="heading mt-4 text-lg">2. Minimal repair</p><p className="mt-3 text-sm font-medium">{fix.strategy}</p><p className="mt-3 text-sm text-graphite">Only the failed synthesis step ran again. The trusted upstream evidence was reused.</p><p className="mt-4 font-mono text-xs">{fix.n_reused} reused · {fix.n_executed} executed</p></div>
          <div className="bg-panel p-6"><Check className="h-5 w-5 text-normal" /><p className="heading mt-4 text-lg">3. Fix verified</p><p className="mt-3 text-sm font-medium text-normal">Correct answer restored</p><p className="mt-3 text-sm text-graphite">The recorded repair passed while spending only {fix.tokens_total} tokens.</p><span className="mt-4 inline-flex rounded-chip bg-normal-tint px-2.5 py-1 text-xs font-medium text-normal">Verified pass</span></div>
        </section>
      </main>
    </div>
  );
}