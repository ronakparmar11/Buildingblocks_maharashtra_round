import { ExternalLink, LoaderCircle } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { useJob, useSimulate } from "../api/hooks";
import { Button, StatChip } from "./ui";

export default function TrafficSimulator() {
  const [count, setCount] = useState(30);
  const [wrongShare, setWrongShare] = useState(35);
  const [jobId, setJobId] = useState<string>();
  const simulate = useSimulate();
  const job = useJob(jobId);
  const result = job.data?.result as unknown as {
    sent?: number;
    failed?: number;
    incidents_opened?: number;
    emails_sent?: number;
  } | null;
  const running = Boolean(jobId) && !["completed", "failed"].includes(job.data?.status ?? "");
  const start = async () => {
    const created = await simulate.mutateAsync({ n: count, failure_rate: wrongShare / 100 });
    setJobId(created.job_id);
  };
  return (
    <section className="mt-6 border-y border-rule bg-panel px-5 py-6">
      <div className="max-w-3xl">
        <h2 className="heading text-xl">Simulate traffic</h2>
        <p className="mt-1 text-sm text-graphite">Send realistic support messages through the agent and watch failures group into incidents.</p>
        <div className="mt-5 flex flex-wrap items-end gap-3">
          <label className="text-sm">Send<input aria-label="Message count" type="number" min="1" max="200" value={count} disabled={running} onChange={(event) => setCount(Number(event.target.value))} className="mx-2 h-10 w-20 rounded-control border border-rule px-3 font-mono" />customer messages</label>
          <label className="text-sm">with about<input aria-label="Wrong answer share" type="number" min="0" max="100" value={wrongShare} disabled={running} onChange={(event) => setWrongShare(Number(event.target.value))} className="mx-2 h-10 w-20 rounded-control border border-rule px-3 font-mono" />% going wrong</label>
          <Button variant="orange" size="lg" loading={simulate.isPending} disabled={running || count < 1 || wrongShare < 0 || wrongShare > 100} onClick={start}>{job.data?.status === "completed" ? "Run again" : "Start simulation"}</Button>
        </div>
      </div>
      {jobId && (
        <div className="mt-7 border-t border-rule pt-6">
          <div className="grid grid-cols-2 gap-px bg-rule sm:grid-cols-4">
            {[
              [result?.sent ?? 0, "sent"],
              [result?.failed ?? 0, "answered wrong"],
              [result?.incidents_opened ?? 0, "incidents opened"],
              [result?.emails_sent ?? 0, "emails sent"],
            ].map(([value, label]) => <div key={label} className="bg-panel p-4"><strong className="font-mono text-2xl">{value}</strong><p className="mt-1 text-xs text-graphite">{label}</p></div>)}
          </div>
          <div className="mt-4 h-1.5 bg-rule-soft"><div className="h-full bg-orange transition-[width] duration-300" style={{ width: `${Math.round((job.data?.progress ?? 0) * 100)}%` }} /></div>
          <div className="mt-4 flex flex-wrap items-center gap-3 text-sm">
            {running && <span className="flex items-center gap-2 text-graphite"><LoaderCircle className="h-4 w-4 animate-spin" />Sending customer messages…</span>}
            {job.data?.status === "completed" && <StatChip>{result?.sent} messages completed</StatChip>}
            {(result?.incidents_opened ?? 0) > 0 && <Link to="/incidents/inc_refunds_archived" className="text-advisory">Open new refund incident</Link>}
            <a href="http://localhost:8025" target="_blank" rel="noreferrer" className="ml-auto inline-flex items-center gap-1 text-advisory">Open Mailpit inbox <ExternalLink className="h-3.5 w-3.5" /></a>
            <Link to="/" className="text-advisory">Open Overview</Link>
          </div>
        </div>
      )}
    </section>
  );
}