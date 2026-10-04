import { Check, ChevronDown, LockKeyhole, Mail, UserRound } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useIncident, useJob, useNotifyIncident, usePatchIncident, useVerifyIncident } from "../api/hooks";
import type { IncidentEventRecord, IncidentPatchRequest } from "../api/types";
import EmailPreviewDrawer from "../components/EmailPreviewDrawer";
import ReasonList from "../components/ReasonList";
import TryFixes from "../components/TryFixes";
import { Button, ErrorState, Popover, Skeleton, StatChip, Toast } from "../components/ui";

const inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });
const statusTransitions: Record<string, IncidentPatchRequest["status"][]> = {
  open: ["investigating", "resolved"],
  reopened: ["investigating", "resolved"],
  investigating: ["fix_verified", "resolved"],
  fix_verified: ["resolved"],
  resolved: ["reopened"],
};
const causeNames: Record<string, string> = {
  retrieve: "Searching the help center",
  extract: "Reading the relevant policy",
  synthesize: "Writing the agent reply",
  check: "Checking the reply against policy",
};

function Severity({ value }: { value: string }) {
  const color = value === "high" ? "bg-warning" : value === "medium" ? "bg-caution" : "bg-graphite";
  return <span className="inline-flex items-center gap-2 capitalize"><span className={`h-2 w-2 rounded-full ${color}`} />{value}</span>;
}

function ConfirmDialog({
  title,
  children,
  confirmLabel,
  pending,
  onCancel,
  onConfirm,
}: {
  title: string;
  children: React.ReactNode;
  confirmLabel: string;
  pending?: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/35 p-4" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
      <div className="w-full max-w-md rounded-panel border border-rule bg-panel p-6 shadow-popover">
        <h2 id="confirm-title" className="heading text-lg">{title}</h2>
        <div className="mt-3 text-sm text-graphite">{children}</div>
        <div className="mt-6 flex justify-end gap-2"><Button onClick={onCancel}>Cancel</Button><Button variant="ink" loading={pending} onClick={onConfirm}>{confirmLabel}</Button></div>
      </div>
    </div>
  );
}

function StepNumber({ number, state }: { number: number; state: "done" | "active" | "locked" }) {
  return (
    <span className={`grid h-7 w-7 shrink-0 place-items-center rounded-full border text-xs ${state === "done" ? "border-normal bg-normal-tint text-normal" : state === "active" ? "border-ink-btn bg-ink-btn text-white" : "border-rule text-graphite"}`}>
      {state === "done" ? <Check className="h-4 w-4" /> : state === "locked" ? <LockKeyhole className="h-3.5 w-3.5" /> : number}
    </span>
  );
}

export default function IncidentDetailPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const detail = useIncident(id);
  const patch = usePatchIncident(id);
  const notify = useNotifyIncident(id);
  const verify = useVerifyIncident(id);
  const [fixesOpen, setFixesOpen] = useState(false);
  const [repairRunId, setRepairRunId] = useState<string>();
  const [jobId, setJobId] = useState<string>();
  const verifyJob = useJob(jobId);
  const [status, setStatus] = useState<string>();
  const [owner, setOwner] = useState("");
  const [confirm, setConfirm] = useState<"notify" | "resolve" | null>(null);
  const [note, setNote] = useState("");
  const [toast, setToast] = useState<string>();
  const [previewId, setPreviewId] = useState<string>();
  const [localEvents, setLocalEvents] = useState<IncidentEventRecord[]>([]);
  const fixRecorded = useRef(false);
  const verificationRecorded = useRef(false);

  const addEvent = useCallback((kind: string, text: string, meta: IncidentEventRecord["meta"] = {}) => {
    setLocalEvents((current) => [...current, { event_id: `local_${Date.now()}_${current.length}`, incident_id: id, kind, text, created_at: new Date().toISOString(), meta }]);
  }, [id]);
  const handleFixFound = useCallback((runId: string) => {
    setRepairRunId(runId);
    if (!fixRecorded.current) {
      fixRecorded.current = true;
      addEvent("fix_tried", "Fix tried: Search current articles only passed.");
    }
  }, [addEvent]);

  const verifyResult = verifyJob.data?.result as unknown as { n_total?: number; n_passed?: number; tokens_saved?: number } | null;
  const verificationDone = verifyJob.data?.status === "completed" && Boolean(verifyResult?.n_total);
  useEffect(() => {
    if (verificationDone && !verificationRecorded.current) {
      verificationRecorded.current = true;
      setStatus("fix_verified");
      addEvent("fix_verified", `Fix verified on ${verifyResult?.n_passed} of ${verifyResult?.n_total} conversations.`);
    }
  }, [addEvent, verificationDone, verifyResult?.n_passed, verifyResult?.n_total]);

  if (detail.isLoading) return <div className="mx-auto max-w-[1440px] space-y-5 px-6 py-8"><Skeleton className="h-8 w-2/3" /><Skeleton className="h-20" /><Skeleton className="h-96" /></div>;
  if (detail.isError || !detail.data) return <ErrorState onRetry={() => detail.refetch()} />;
  const data = detail.data;
  const incident = data.incident;
  const currentStatus = status ?? incident.status;
  const representativeId = data.representative_run?.run_id ?? data.runs[0]?.run_id;
  const ranking = [{ step_key: `q1/${incident.cause_step_name}#0`, score: 0.91, rank: 1, reasons: data.reasons }];
  const events = [...data.events, ...localEvents].sort((a, b) => a.created_at.localeCompare(b.created_at));
  const startVerification = async () => {
    if (!repairRunId) return;
    const result = await verify.mutateAsync({ repair_run_id: repairRunId });
    setJobId(result.job_id);
  };
  const updateStatus = async (next: IncidentPatchRequest["status"], updateNote?: string) => {
    if (!next) return;
    await patch.mutateAsync({ status: next, note: updateNote || undefined });
    setStatus(next);
    addEvent(next === "resolved" ? "resolved" : "status_changed", next === "resolved" ? "Incident resolved." : `Status changed to ${next.replace("_", " ")}.`);
  };
  const sendNotification = async () => {
    const result = await notify.mutateAsync();
    addEvent("notified", "Emailed 2 people about this incident.", { notification_id: result.notification_id });
    setConfirm(null);
    setToast("Emailed 2 people about this incident.");
  };
  const assign = async () => {
    await patch.mutateAsync({ owner: owner.trim() });
    addEvent("owner_changed", `Assigned to ${owner.trim()}.`);
    setToast(`Assigned to ${owner.trim()}.`);
  };

  return (
    <div className="mx-auto max-w-[1440px] px-4 py-7 sm:px-6">
      <Link to="/incidents" className="text-sm text-advisory">← Incidents</Link>
      <div className="mt-3 border-b border-rule pb-6">
        <h1 className="heading max-w-5xl text-2xl">{incident.title}</h1>
        <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-graphite">
          <Severity value={incident.severity} />
          <span><strong className="font-mono text-ink">{incident.n_runs}</strong> conversations</span>
          <span title="Average cost of a refund dispute or human escalation. Change it in Settings."><strong className="font-mono text-ink">{inr.format(incident.est_cost_inr)}</strong> estimated</span>
          <span>Open since {new Date(incident.first_seen).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</span>
          <span>Owner: <strong className="text-ink">{owner || incident.owner || "—"}</strong></span>
        </div>
        <div className="mt-5 flex flex-wrap gap-2">
          <Button onClick={() => setConfirm("notify")}><Mail className="h-4 w-4" />Notify team</Button>
          <Popover trigger={<Button><UserRound className="h-4 w-4" />Assign</Button>}>
            <div className="space-y-3">
              <label className="block text-xs text-graphite">Owner name<input autoFocus value={owner} onChange={(event) => setOwner(event.target.value)} className="mt-1 h-9 w-full rounded-control border border-rule px-3 text-sm text-ink" /></label>
              <Button variant="ink" disabled={!owner.trim()} loading={patch.isPending} onClick={assign}>Assign incident</Button>
            </div>
          </Popover>
          <Popover trigger={<Button>Status: <span className="capitalize">{currentStatus.replace("_", " ")}</span><ChevronDown className="h-4 w-4" /></Button>}>
            <div className="space-y-1">
              {(statusTransitions[currentStatus] ?? []).map((next) => <button key={next} onClick={() => next === "resolved" ? setConfirm("resolve") : updateStatus(next)} className="block w-full rounded-control px-3 py-2 text-left text-sm capitalize hover:bg-rule-soft">{next?.replace("_", " ")}</button>)}
            </div>
          </Popover>
        </div>
      </div>

      <div className="grid border-b border-rule lg:grid-cols-[minmax(0,1fr)_360px]">
        <div className="lg:border-r lg:border-rule">
          <section className="border-b border-rule py-6 lg:pr-8">
            <h2 className="heading text-lg">What's going wrong</h2>
            <p className="mt-3 max-w-3xl text-md leading-7">{data.explanation}</p>
            <p className="mt-5 text-sm"><strong>Likely cause:</strong> {causeNames[incident.cause_step_name] ?? incident.cause_step_name}</p>
            <div className="mt-4 max-w-2xl"><ReasonList reasons={data.reasons} limit={2} /></div>
          </section>
          <section className="py-6 lg:pr-8">
            <h2 className="heading text-lg">Fix</h2>
            <ol className="mt-5 space-y-3">
              <li className="flex items-center gap-3 border-b border-rule-soft pb-4"><StepNumber number={1} state={repairRunId ? "done" : "active"} /><div className="min-w-0 flex-1"><strong>Try fixes on the example conversation</strong>{repairRunId && <p className="mt-1 text-sm text-normal">Search current articles only passed.</p>}</div><Button variant={repairRunId ? "secondary" : "ink"} disabled={!representativeId} onClick={() => setFixesOpen(true)}>{repairRunId ? "View fix" : "Try fixes"}</Button></li>
              <li className="flex items-center gap-3 border-b border-rule-soft pb-4"><StepNumber number={2} state={verificationDone ? "done" : repairRunId ? "active" : "locked"} /><div className="min-w-0 flex-1"><strong>Verify on all {incident.n_runs} conversations</strong>{verifyJob.isFetching && !verificationDone && <p className="mt-1 text-sm text-graphite">Verifying {Math.max(1, Math.ceil((verifyJob.data?.progress ?? 0) * incident.n_runs))} of {incident.n_runs}…</p>}{verificationDone && <div className="mt-1"><p className="text-sm text-normal">Fix verified on {verifyResult?.n_passed} of {verifyResult?.n_total} conversations. {(verifyResult?.n_total ?? 0) - (verifyResult?.n_passed ?? 0)} still fail — open them to investigate.</p><div className="mt-2 flex gap-2"><StatChip>{verifyResult?.n_passed} passed</StatChip><StatChip>{verifyResult?.tokens_saved?.toLocaleString()} tokens saved</StatChip></div></div>}</div><Button disabled={!repairRunId || Boolean(jobId)} loading={verify.isPending || (Boolean(jobId) && !verificationDone)} onClick={startVerification}>Verify all</Button></li>
              <li className="flex items-center gap-3"><StepNumber number={3} state={currentStatus === "resolved" ? "done" : verificationDone ? "active" : "locked"} /><div className="flex-1"><strong>Resolve</strong><p className="mt-1 text-sm text-graphite">Close the incident after the bulk check passes.</p></div><Button variant="ink" disabled={!verificationDone || currentStatus === "resolved"} onClick={() => setConfirm("resolve")}>Resolve</Button></li>
            </ol>
          </section>
        </div>
        <aside className="py-6 lg:pl-7">
          <h2 className="heading text-lg">Timeline</h2>
          <ol className="mt-5 space-y-5 border-l border-rule pl-5">
            {events.map((event) => {
              const notificationId = typeof event.meta.notification_id === "string" ? event.meta.notification_id : undefined;
              return <li key={event.event_id} className="relative text-sm before:absolute before:-left-[24px] before:top-1.5 before:h-2 before:w-2 before:rounded-full before:bg-graphite"><time className="font-mono text-xs text-graphite">{new Date(event.created_at).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</time>{notificationId ? <button onClick={() => setPreviewId(notificationId)} className="mt-1 block text-left text-advisory">{event.text}</button> : <p className="mt-1">{event.text}</p>}</li>;
            })}
          </ol>
        </aside>
      </div>

      <section className="py-6">
        <h2 className="heading text-lg">Affected conversations</h2>
        <div className="mt-4 overflow-x-auto rounded-panel border border-rule bg-panel">
          <table className="w-full min-w-[900px] table-fixed text-left text-sm">
            <thead><tr className="h-10 border-b border-rule bg-paper text-xs text-graphite"><th className="px-4 font-medium">Customer message</th><th className="px-3 font-medium">Agent reply</th><th className="px-3 font-medium">Correct answer</th><th className="w-44 px-4 font-medium">Likely cause</th></tr></thead>
            <tbody>{data.runs.map((run) => <tr key={run.run_id} tabIndex={0} onClick={() => navigate(`/conversations/${run.run_id}`, { state: { from: `/incidents/${id}` } })} onKeyDown={(event) => event.key === "Enter" && navigate(`/conversations/${run.run_id}`, { state: { from: `/incidents/${id}` } })} className="h-16 cursor-pointer border-b border-rule-soft outline-none hover:bg-rule-soft/60 focus:bg-rule-soft/60"><td className="truncate px-4 font-medium" title={run.customer_message}>{run.customer_message}</td><td className="truncate px-3 text-warning" title={run.agent_reply}>{run.agent_reply}</td><td className="truncate px-3" title={run.correct_answer}>{run.correct_answer}</td><td className="px-4"><span className="rounded-chip bg-caution-tint px-2.5 py-1 font-mono text-xs">{incident.cause_step_name} {run.predicted_culprit?.score.toFixed(2)}</span></td></tr>)}</tbody>
          </table>
        </div>
      </section>

      {representativeId && <TryFixes open={fixesOpen} onClose={() => setFixesOpen(false)} runId={representativeId} ranking={ranking} onEdit={() => setFixesOpen(false)} onFixFound={handleFixFound} />}
      <EmailPreviewDrawer notificationId={previewId} onClose={() => setPreviewId(undefined)} />
      {confirm === "notify" && <ConfirmDialog title="Notify the team?" confirmLabel="Send incident email" pending={notify.isPending} onCancel={() => setConfirm(null)} onConfirm={sendNotification}><p>This sends the incident email now, bypassing the notification throttle.</p></ConfirmDialog>}
      {confirm === "resolve" && <ConfirmDialog title="Resolve this incident?" confirmLabel="Resolve incident" pending={patch.isPending} onCancel={() => setConfirm(null)} onConfirm={async () => { await updateStatus("resolved", note); setConfirm(null); setToast("Incident resolved."); }}><p>Resolve after the fix has been checked across affected conversations.</p><label className="mt-4 block text-xs">Resolution note (optional)<textarea value={note} onChange={(event) => setNote(event.target.value)} rows={3} className="mt-1 w-full resize-none rounded-control border border-rule bg-panel p-3 text-sm text-ink" /></label></ConfirmDialog>}
      {toast && <div className="fixed bottom-5 right-5 z-50"><Toast message={toast} onClose={() => setToast(undefined)} /></div>}
    </div>
  );
}