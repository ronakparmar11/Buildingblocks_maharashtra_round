import { ArrowRight, Check, Cpu, Play, RotateCcw, ShieldCheck, Sparkles } from "lucide-react";
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
      {/* ─── Header ─── */}
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
            <button onClick={play} disabled={playing} className="inline-flex h-10 items-center gap-2 rounded-control bg-orange px-5 text-sm font-medium text-white shadow-[0_1px_3px_rgba(255,79,0,.3)] transition-all hover:bg-[#e54600] hover:shadow-[0_2px_8px_rgba(255,79,0,.35)] disabled:opacity-60 disabled:shadow-none">
              {playing ? <RotateCcw className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              {playing ? "Replaying trace" : "Replay the story"}
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1440px] px-4 py-6 sm:px-6">
        {/* ─── Question + answers ─── */}
        <section className="rounded-panel border border-rule bg-panel">
          <div className="grid lg:grid-cols-[1.3fr_0.7fr]">
            <div className="border-b border-rule p-5 lg:border-b-0 lg:border-r lg:p-7">
              <p className="font-mono text-[11px] uppercase tracking-wide text-graphite">Customer question</p>
              <h2 className="heading mt-3 max-w-3xl text-xl">{run.task.question}</h2>
              <div className="mt-6 grid gap-4 sm:grid-cols-2">
                <div className="rounded-node border border-warning/20 bg-warning-tint p-4">
                  <p className="text-[11px] font-medium uppercase tracking-wide text-warning/70">AI answered</p>
                  <p className="mt-2 text-lg font-semibold text-warning">{run.run.final_answer}</p>
                </div>
                <div className="rounded-node border border-normal/20 bg-normal-tint p-4">
                  <p className="text-[11px] font-medium uppercase tracking-wide text-normal/70">Expected answer</p>
                  <p className="mt-2 text-lg font-semibold text-normal">{run.task.gold_answer}</p>
                </div>
              </div>
            </div>
            <dl className="grid grid-cols-2">
              {[
                { label: "Outcome", content: <OutcomeChip outcome={run.run.outcome} /> },
                { label: "Trace", content: <span className="font-mono text-xl font-bold">{run.steps.length} <span className="text-sm font-normal text-graphite">steps</span></span> },
                { label: "Culprit confidence", content: <span className="font-mono text-xl font-bold text-orange">{Math.round(culprit.score * 100)}%</span> },
                { label: "Diagnosis time", content: <span className="font-mono text-xl font-bold">{diagnosis.latency_ms.toFixed(1)} <span className="text-sm font-normal text-graphite">ms</span></span> },
              ].map(({ label, content }, i) => (
                <div key={label} className={`flex flex-col justify-center p-5 ${i < 2 ? "border-b border-rule" : ""} ${i % 2 === 0 ? "border-r border-rule" : ""}`}>
                  <dt className="font-mono text-[11px] uppercase tracking-wide text-graphite">{label}</dt>
                  <dd className="mt-2">{content}</dd>
                </div>
              ))}
            </dl>
          </div>
        </section>

        {/* ─── Execution trace ─── */}
        <section className="mt-6 rounded-panel border border-rule bg-panel">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-rule px-5 py-4">
            <div>
              <p className="heading text-lg">Recorded execution trace</p>
              <p className="mt-0.5 text-xs text-graphite">Select any step to inspect its captured output.</p>
            </div>
            <span className="rounded-chip bg-rule-soft px-3 py-1 font-mono text-xs text-graphite">{revealed}/{run.steps.length} visible</span>
          </div>
          <div className="overflow-x-auto p-5">
            <div className="flex min-w-max items-center">
              {run.steps.map((step, index) => (
                <div key={step.step_key} className={`flex items-center transition-opacity duration-200 ${index >= revealed ? "opacity-15" : "opacity-100"}`}>
                  {index > 0 && <span className="flex items-center"><span className="h-px w-5 bg-rule-soft sm:w-8" /><ArrowRight className="h-3 w-3 text-rule" /><span className="h-px w-1 bg-rule-soft sm:w-2" /></span>}
                  <button
                    onClick={() => setSelectedKey(step.step_key)}
                    className={`w-28 rounded-node border-2 px-3 py-3 text-left transition-all ${
                      selected.step_key === step.step_key
                        ? "border-orange bg-orange-tint shadow-[0_0_0_3px_rgba(255,79,0,.12)]"
                        : step.step_key === culprit.step_key
                          ? "border-caution bg-caution-tint"
                          : "border-rule bg-panel hover:border-graphite/40 hover:shadow-sm"
                    }`}
                  >
                    <span className="block truncate text-xs font-medium">{step.name}</span>
                    <span className="mt-1 block font-mono text-[10px] text-graphite">#{String(index + 1).padStart(2, "0")}</span>
                  </button>
                </div>
              ))}
            </div>
          </div>
          <div className="grid border-t border-rule lg:grid-cols-[0.8fr_1.2fr]">
            <div className="border-b border-rule bg-paper/50 p-5 lg:border-b-0 lg:border-r">
              <p className="font-mono text-[11px] uppercase tracking-wide text-graphite">Selected step</p>
              <div className="mt-2"><StepKey value={selected.step_key} copy /></div>
              <div className="mt-4 flex items-baseline gap-2">
                <p className="font-mono text-[11px] uppercase tracking-wide text-graphite">Latency</p>
                <p className="font-mono text-sm font-medium">{selected.latency_ms} ms</p>
              </div>
            </div>
            <div className="min-w-0 p-5">
              <p className="font-mono text-[11px] uppercase tracking-wide text-graphite">Captured output</p>
              <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap break-words rounded-node border border-rule bg-paper p-3 font-mono text-xs leading-5 text-ink">{selected.output_text || JSON.stringify(selected.output, null, 2)}</pre>
            </div>
          </div>
        </section>

        {/* ─── 3-step summary ─── */}
        <section className="mt-6 grid gap-4 lg:grid-cols-3">
          <article className="group relative overflow-hidden rounded-panel border border-rule bg-panel p-6 transition-colors hover:border-caution/30">
            <span className="absolute left-0 top-0 h-full w-[3px] rounded-r bg-caution" />
            <div className="flex items-center gap-3">
              <span className="grid h-9 w-9 place-items-center rounded-control bg-caution-tint text-caution"><Sparkles className="h-4.5 w-4.5" /></span>
              <p className="heading text-lg">1. Cause isolated</p>
            </div>
            <div className="mt-4"><StepKey value={culprit.step_key} copy /></div>
            <p className="mt-3 text-sm leading-relaxed text-graphite">{culprit.reasons[0]?.text}</p>
            <p className="mt-3 rounded-node border border-caution/15 bg-caution-tint/50 px-3 py-2 font-mono text-xs leading-relaxed">{culprit.reasons[0]?.evidence}</p>
          </article>
          <article className="group relative overflow-hidden rounded-panel border border-rule bg-panel p-6 transition-colors hover:border-advisory/30">
            <span className="absolute left-0 top-0 h-full w-[3px] rounded-r bg-advisory" />
            <div className="flex items-center gap-3">
              <span className="grid h-9 w-9 place-items-center rounded-control bg-advisory-tint text-advisory"><Cpu className="h-4.5 w-4.5" /></span>
              <p className="heading text-lg">2. Minimal repair</p>
            </div>
            <p className="mt-4 text-sm font-medium">{fix.strategy}</p>
            <p className="mt-3 text-sm leading-relaxed text-graphite">Only the failed synthesis step ran again. The trusted upstream evidence was reused.</p>
            <div className="mt-4 flex gap-3">
              <span className="rounded-chip bg-rule-soft px-2.5 py-1 font-mono text-xs">{fix.n_reused} reused</span>
              <span className="rounded-chip bg-rule-soft px-2.5 py-1 font-mono text-xs">{fix.n_executed} executed</span>
            </div>
          </article>
          <article className="group relative overflow-hidden rounded-panel border border-rule bg-panel p-6 transition-colors hover:border-normal/30">
            <span className="absolute left-0 top-0 h-full w-[3px] rounded-r bg-normal" />
            <div className="flex items-center gap-3">
              <span className="grid h-9 w-9 place-items-center rounded-control bg-normal-tint text-normal"><Check className="h-4.5 w-4.5" /></span>
              <p className="heading text-lg">3. Fix verified</p>
            </div>
            <p className="mt-4 text-sm font-medium text-normal">Correct answer restored</p>
            <p className="mt-3 text-sm leading-relaxed text-graphite">The recorded repair passed while spending only {fix.tokens_total} tokens.</p>
            <span className="mt-4 inline-flex items-center gap-1.5 rounded-chip bg-normal-tint px-3 py-1.5 text-xs font-medium text-normal"><Check className="h-3 w-3" /> Verified pass</span>
          </article>
        </section>
      </main>
    </div>
  );
}