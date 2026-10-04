import {
  AlertTriangle, Check, Database, Headphones, LoaderCircle, Mic, MicOff,
  Play, RotateCcw, ShieldCheck, Volume2, Workflow,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import {
  useDiagnosis, useFaultTargets, useJob, useLiveRun, useRepairJob, useRun,
  useTasks,
} from "../api/hooks";
import type { RepairAttemptResponse, TaskRecord } from "../api/types";
import { Button, ErrorState, OutcomeChip, Skeleton, StepKey } from "../components/ui";
import { useWorkspace, workspaceDetails } from "../context/workspace";

type SpeechEvent = { results: ArrayLike<{ 0: { transcript: string } }> };
type SpeechRecognizer = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: SpeechEvent) => void) | null;
  onend: (() => void) | null;
  onerror: (() => void) | null;
  start: () => void;
  stop: () => void;
};
type SpeechRecognizerConstructor = new () => SpeechRecognizer;
type SpeechWindow = typeof window & {
  SpeechRecognition?: SpeechRecognizerConstructor;
  webkitSpeechRecognition?: SpeechRecognizerConstructor;
};

const tokenize = (value: string) => new Set(value.toLowerCase().match(/[a-z0-9₹]+/g) ?? []);

function closestTask(transcript: string, tasks: TaskRecord[]) {
  const spoken = tokenize(transcript);
  return tasks.reduce<{ task: TaskRecord; score: number } | null>((best, task) => {
    const words = tokenize(task.question);
    const overlap = [...spoken].filter((word) => words.has(word)).length;
    const score = overlap / Math.max(new Set([...spoken, ...words]).size, 1);
    return !best || score > best.score ? { task, score } : best;
  }, null);
}

function speak(text?: string | null) {
  if (!text) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 0.94;
  window.speechSynthesis.speak(utterance);
}

function Waveform({ active, success = false }: { active: boolean; success?: boolean }) {
  const bars = [14, 25, 38, 20, 46, 31, 18, 40, 27, 45, 22, 34, 16, 29, 41, 24, 35, 19, 30, 13];
  return <div className="flex h-12 items-center gap-1" aria-hidden="true">
    {bars.map((height, index) => <span key={index} className={`w-1 rounded-full ${success ? "bg-normal" : "bg-orange"} ${active ? "animate-pulse" : "opacity-35"}`} style={{ height, animationDelay: `${index * 45}ms` }} />)}
  </div>;
}

export default function VoiceLabPage() {
  const { workspace } = useWorkspace();
  const tasks = useTasks();
  const [transcript, setTranscript] = useState("");
  const [taskId, setTaskId] = useState("");
  const [listening, setListening] = useState(false);
  const [runId, setRunId] = useState<string>();
  const [selectedStep, setSelectedStep] = useState<string>();
  const [repairJobId, setRepairJobId] = useState<string>();
  const recognition = useRef<SpeechRecognizer | null>(null);

  const targets = useFaultTargets(taskId);
  const live = useLiveRun();
  const run = useRun(runId, true);
  const diagnosis = useDiagnosis(runId, Boolean(run.data && run.data.run.outcome !== "error"));
  const repair = useRepairJob();
  const repairJob = useJob(repairJobId);
  const repairResult = repairJob.data?.result as unknown as {
    repaired?: boolean;
    winning_run_id?: string | null;
    attempts?: RepairAttemptResponse[];
  } | null;
  const repairedRun = useRun(repairResult?.winning_run_id ?? undefined, true);

  const faultTarget = targets.data?.targets.find((target) => target.fault_type.toLowerCase().includes("distractor")) ?? targets.data?.targets[0];
  const culprit = diagnosis.data?.ranking[0];
  const selected = run.data?.steps.find((step) => step.step_key === selectedStep)
    ?? run.data?.steps.find((step) => step.step_key === culprit?.step_key)
    ?? run.data?.steps[0];
  const isRunning = live.isPending || Boolean(runId && !run.data && !run.isError);
  const repairing = repair.isPending || (Boolean(repairJobId) && !["completed", "failed"].includes(repairJob.data?.status ?? ""));
  const speechWindow = window as SpeechWindow;
  const recognitionSupported = Boolean(speechWindow.SpeechRecognition || speechWindow.webkitSpeechRecognition);
  const winningAttempt = repairResult?.attempts?.find((attempt) => attempt.run_id === repairResult.winning_run_id);

  useEffect(() => {
    if (!tasks.data?.length || taskId) return;
    const preferred = tasks.data.find((task) => /diwali|return|refund/i.test(task.question)) ?? tasks.data[0];
    setTaskId(preferred.task_id);
    setTranscript(preferred.question);
  }, [taskId, tasks.data]);

  useEffect(() => () => {
    recognition.current?.stop();
    window.speechSynthesis.cancel();
  }, []);

  const matchTranscript = (value: string) => {
    setTranscript(value);
    const match = closestTask(value, tasks.data ?? []);
    if (match) setTaskId(match.task.task_id);
  };

  const toggleListening = () => {
    if (listening) {
      recognition.current?.stop();
      setListening(false);
      return;
    }
    const Recognition = speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition;
    if (!Recognition) return;
    const instance = new Recognition();
    instance.continuous = false;
    instance.interimResults = false;
    instance.lang = "en-IN";
    instance.onresult = (event) => matchTranscript(event.results[0][0].transcript);
    instance.onend = () => setListening(false);
    instance.onerror = () => setListening(false);
    recognition.current = instance;
    setListening(true);
    instance.start();
  };

  const startInvestigation = () => {
    if (!taskId) return;
    setRunId(undefined);
    setSelectedStep(undefined);
    setRepairJobId(undefined);
    live.mutate({ task_id: taskId, fault: faultTarget ?? null }, {
      onSuccess: ({ run_id }) => setRunId(run_id),
    });
  };

  const reset = () => {
    setRunId(undefined);
    setSelectedStep(undefined);
    setRepairJobId(undefined);
    live.reset();
    window.speechSynthesis.cancel();
  };

  if (tasks.isLoading) return <div className="mx-auto max-w-[1440px] space-y-5 p-6"><Skeleton className="h-10 w-72" /><Skeleton className="h-[520px]" /></div>;
  if (tasks.isError) return <ErrorState onRetry={() => tasks.refetch()} />;

  return <div className="min-h-[calc(100vh-56px)] bg-paper">
    <header className="border-b border-rule bg-panel px-4 py-7 sm:px-6">
      <div className="mx-auto flex max-w-[1440px] flex-wrap items-start justify-between gap-5">
        <div className="max-w-3xl">
          <div className="flex flex-wrap items-center gap-2 text-xs font-medium text-advisory"><Headphones className="h-4 w-4" /> Voice failure intelligence <span className="inline-flex items-center gap-1.5 rounded-chip bg-normal-tint px-2 py-0.5 text-normal"><span className="h-1.5 w-1.5 animate-pulse rounded-full bg-normal" /> Live API pipeline</span></div>
          <h1 className="heading mt-3 text-2xl sm:text-3xl">Speak to the agent. Trace what it actually does.</h1>
          <p className="mt-2 max-w-2xl text-sm text-graphite">Voice is transcribed, matched to the active support catalog, executed by the real agent, diagnosed, and repaired through the same replay engine as production traffic.</p>
        </div>
        {runId && <Button onClick={reset}><RotateCcw className="h-4 w-4" /> New call</Button>}
      </div>
    </header>

    <main className="mx-auto max-w-[1440px] px-4 py-6 sm:px-6">
      <section className="grid overflow-hidden rounded-panel border border-rule bg-panel lg:grid-cols-[0.68fr_1.32fr]">
        <div className="border-b border-rule bg-ink p-5 text-white lg:border-b-0 lg:border-r lg:p-7">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3"><span className={`grid h-11 w-11 place-items-center rounded-full ${listening ? "bg-orange" : "bg-white/10"}`}><Mic className="h-5 w-5" /></span><div><p className="text-sm font-semibold">{workspaceDetails[workspace].name}</p><p className="text-xs text-white/55">Voice gateway · en-IN</p></div></div>
            <span className="flex items-center gap-2 text-xs text-white/70"><span className={`h-2 w-2 rounded-full ${isRunning ? "animate-pulse bg-orange" : "bg-normal"}`} />{isRunning ? "Agent running" : "Connected"}</span>
          </div>
          <div className="mt-10 flex min-h-36 items-center justify-center"><Waveform active={listening || isRunning} success={Boolean(repairedRun.data)} /></div>
          <div className="grid grid-cols-3 border-t border-white/10 pt-5 text-center"><div><strong className="block font-mono text-lg">{tasks.data?.length ?? 0}</strong><span className="text-[11px] text-white/45">Known intents</span></div><div><strong className="block font-mono text-lg">{run.data?.steps.length ?? "—"}</strong><span className="text-[11px] text-white/45">Trace steps</span></div><div><strong className="block font-mono text-lg">{run.data ? `${Math.round(run.data.run.latency_ms)}ms` : "—"}</strong><span className="text-[11px] text-white/45">Agent latency</span></div></div>
        </div>

        <div className="p-5 lg:p-7">
          <div className="flex flex-wrap items-center justify-between gap-2"><div><h2 className="heading text-lg">Customer utterance</h2><p className="text-xs text-graphite">Use the microphone or edit the transcript.</p></div><span className="inline-flex items-center gap-1.5 font-mono text-[11px] uppercase text-graphite"><Database className="h-3.5 w-3.5" /> {tasks.data?.length ?? 0} tasks loaded from API</span></div>
          <div className="mt-4 flex gap-2">
            <textarea value={transcript} onChange={(event) => matchTranscript(event.target.value)} disabled={Boolean(runId)} rows={3} className="min-w-0 flex-1 resize-none rounded-node border border-rule px-4 py-3 leading-6 focus:border-advisory disabled:opacity-70" placeholder="Ask a support question…" />
            <button onClick={toggleListening} disabled={!recognitionSupported || Boolean(runId)} title={recognitionSupported ? "Capture voice" : "Speech recognition is unavailable in this browser"} aria-label={listening ? "Stop listening" : "Start listening"} className={`grid w-12 shrink-0 place-items-center rounded-control border transition-colors ${listening ? "border-orange bg-orange text-white" : "border-rule bg-panel text-advisory hover:bg-advisory-tint"} disabled:cursor-not-allowed disabled:opacity-40`}>{listening ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}</button>
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-[1fr_auto] sm:items-end">
            <label className="text-xs text-graphite">Matched support intent<select value={taskId} onChange={(event) => { setTaskId(event.target.value); const task = tasks.data?.find((item) => item.task_id === event.target.value); if (task) setTranscript(task.question); }} disabled={Boolean(runId)} className="mt-1 block h-10 w-full rounded-control border border-rule px-3 text-sm text-ink">{(tasks.data ?? []).map((task) => <option key={task.task_id} value={task.task_id}>{task.question}</option>)}</select></label>
            <Button variant="orange" size="lg" onClick={startInvestigation} loading={isRunning} disabled={!taskId || Boolean(runId) || targets.isLoading}><Play className="h-4 w-4" /> Run voice investigation</Button>
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-rule pt-4 text-xs"><span className="text-graphite">Evaluation scenario</span>{faultTarget ? <><span className="rounded-chip bg-warning-tint px-2 py-1 font-medium text-warning">{faultTarget.fault_type.replaceAll("_", " ").toLowerCase()}</span><StepKey value={faultTarget.step_key} /></> : <span className="rounded-chip bg-normal-tint px-2 py-1 text-normal">clean production call</span>}</div>
        </div>
      </section>

      {(live.isError || run.isError) && <div className="mt-5"><ErrorState onRetry={startInvestigation} /></div>}

      {run.data && <section className="mt-6 rounded-panel border border-rule bg-panel">
        <div className="grid border-b border-rule lg:grid-cols-[1fr_auto]">
          <div className="p-5"><div className="flex flex-wrap items-center gap-2"><OutcomeChip outcome={run.data.run.outcome} /><span className="font-mono text-[11px] text-graphite">RUN {run.data.run.run_id.slice(0, 12)}</span></div><p className="mt-3 text-xs font-medium uppercase text-graphite">Agent spoke</p><p className={`mt-1 text-lg font-medium ${run.data.run.outcome === "fail" ? "text-warning" : "text-ink"}`}>{run.data.run.final_answer || "No answer produced"}</p><button onClick={() => speak(run.data?.run.final_answer)} className="mt-3 inline-flex items-center gap-1.5 text-xs font-medium text-advisory"><Volume2 className="h-4 w-4" /> Play response</button></div>
          <dl className="grid min-w-72 grid-cols-2 border-t border-rule lg:border-l lg:border-t-0"><div className="border-b border-r border-rule p-4"><dt className="text-[11px] text-graphite">Expected</dt><dd className="mt-1 font-medium">{run.data.task.gold_answer}</dd></div><div className="border-b border-rule p-4"><dt className="text-[11px] text-graphite">Tokens</dt><dd className="mt-1 font-mono font-medium">{run.data.run.tokens_total}</dd></div><div className="border-r border-rule p-4"><dt className="text-[11px] text-graphite">Executed</dt><dd className="mt-1 font-mono font-medium">{run.data.run.n_executed}</dd></div><div className="p-4"><dt className="text-[11px] text-graphite">Origin</dt><dd className="mt-1 font-medium">{run.data.run.origin}</dd></div></dl>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-rule px-5 py-4"><div><h2 className="heading text-lg">Real execution trace</h2><p className="text-xs text-graphite">Select a step to inspect its persisted output.</p></div>{diagnosis.isLoading && <span className="inline-flex items-center gap-2 text-xs text-orange"><LoaderCircle className="h-4 w-4 animate-spin" /> Ranking trace steps</span>}{culprit && <span className="inline-flex items-center gap-2 rounded-chip bg-warning-tint px-3 py-1 text-xs font-medium text-warning"><AlertTriangle className="h-3.5 w-3.5" /> Likely cause · {Math.round(culprit.score * 100)}%</span>}</div>
        <div className="overflow-x-auto p-5"><div className="flex min-w-max items-center gap-2">{run.data.steps.map((step, index) => { const isCulprit = step.step_key === culprit?.step_key; return <button key={step.step_id} onClick={() => setSelectedStep(step.step_key)} className={`min-h-24 w-36 rounded-node border-2 p-3 text-left transition-all ${isCulprit ? "border-warning bg-warning-tint" : selected?.step_key === step.step_key ? "border-advisory bg-advisory-tint" : "border-rule hover:border-graphite/40"}`}><span className="font-mono text-[10px] text-graphite">{String(index + 1).padStart(2, "0")}</span><strong className="mt-1 block truncate text-sm">{step.name}</strong><span className="mt-1 block truncate font-mono text-[10px] text-graphite">{step.step_key}</span>{step.reused && <span className="mt-2 block text-[10px] text-normal">reused</span>}</button>; })}</div></div>
        {selected && <div className="grid border-t border-rule lg:grid-cols-[0.38fr_0.62fr]"><div className="p-5 lg:border-r lg:border-rule"><p className="font-mono text-[11px] uppercase text-graphite">Selected step</p><div className="mt-2"><StepKey value={selected.step_key} copy /></div>{culprit?.step_key === selected.step_key && <p className="mt-3 text-sm text-warning">{culprit.reasons[0]?.text}</p>}</div><div className="min-w-0 p-5"><p className="font-mono text-[11px] uppercase text-graphite">Persisted output</p><pre className="mt-2 max-h-36 overflow-auto whitespace-pre-wrap break-words rounded-node bg-paper p-3 font-mono text-xs leading-5">{selected.output_text || JSON.stringify(selected.output, null, 2)}</pre></div></div>}
      </section>}

      {culprit && !repairResult?.repaired && <section className="mt-6 flex flex-wrap items-center gap-5 rounded-panel border border-rule bg-panel p-5"><span className="grid h-10 w-10 place-items-center rounded-control bg-warning-tint text-warning"><Workflow className="h-5 w-5" /></span><div className="min-w-0 flex-1"><p className="heading text-lg">Diagnosis produced by {diagnosis.data?.model_version}</p><p className="mt-1 text-sm text-graphite">{culprit.reasons[0]?.evidence || `Highest-ranked causal step: ${culprit.step_key}`}</p></div><Button variant="ink" size="lg" loading={repairing} onClick={() => repair.mutate({ id: runId!, top_k: 3 }, { onSuccess: ({ job_id }) => setRepairJobId(job_id) })}><ShieldCheck className="h-4 w-4" /> Repair with replay engine</Button></section>}

      {repairJob.data?.status === "failed" && <div className="mt-5"><ErrorState onRetry={() => setRepairJobId(undefined)} /></div>}

      {repairResult?.repaired && <section className="mt-6 grid overflow-hidden rounded-panel border border-normal/30 bg-panel lg:grid-cols-[1fr_0.48fr]">
        <div className="p-5 lg:p-7"><div className="flex items-center gap-2 text-normal"><Check className="h-5 w-5" /><span className="text-xs font-semibold uppercase">Backend-verified voice repair</span></div><h2 className="heading mt-3 text-xl">The replay now passes the evaluator.</h2><p className="mt-3 text-base leading-7">{repairedRun.data?.run.final_answer ?? "Loading the repaired response…"}</p><button disabled={!repairedRun.data} onClick={() => speak(repairedRun.data?.run.final_answer)} className="mt-4 inline-flex items-center gap-2 text-sm font-medium text-normal disabled:opacity-40"><Volume2 className="h-4 w-4" /> Hear repaired response</button></div>
        <div className="flex items-center justify-center border-t border-normal/20 bg-normal-tint p-6 lg:border-l lg:border-t-0"><div className="text-center"><Waveform active success /><p className="mt-3 font-mono text-2xl font-bold text-normal">{winningAttempt?.n_executed ?? "—"} steps</p><p className="text-xs text-normal">re-executed · {winningAttempt?.n_reused ?? "—"} reused</p></div></div>
      </section>}
    </main>
  </div>;
}