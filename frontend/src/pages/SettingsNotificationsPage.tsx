import { ExternalLink, Mail, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { NavLink } from "react-router-dom";
import {
  useBusinessSettings,
  useCreateRecipient,
  useDeleteRecipient,
  useNotificationStatus,
  useNotifications,
  useRecipients,
  useRules,
  useSendDigest,
  useTestNotification,
  useUpdateBusinessSettings,
  useUpdateRecipient,
  useUpdateRule,
} from "../api/hooks";
import type { Json, RecipientResponse, RuleResponse } from "../api/types";
import EmailPreviewDrawer from "../components/EmailPreviewDrawer";
import { Button, ErrorState, Skeleton } from "../components/ui";
import { useWorkspace } from "../context/workspace";

const subscriptions = [
  ["incident_opened", "New incident"],
  ["incident_escalated", "High severity"],
  ["failure_rate", "Failure rate"],
  ["fix_verified", "Fix verified"],
  ["incident_resolved", "Resolved"],
  ["daily_digest", "Daily summary"],
] as const;
const ruleLabels: Record<string, string> = Object.fromEntries(subscriptions);
const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function statusStyle(status: string) {
  if (status === "sent") return "bg-normal-tint text-normal";
  if (status === "failed") return "bg-[#F9DEE2] text-warning";
  if (status === "queued") return "bg-caution-tint text-ink";
  return "bg-rule-soft text-graphite";
}

export default function SettingsNotificationsPage() {
  const { workspace } = useWorkspace();
  const server = useNotificationStatus();
  const recipients = useRecipients();
  const rules = useRules();
  const settings = useBusinessSettings();
  const notifications = useNotifications();
  const testEmail = useTestNotification();
  const createRecipient = useCreateRecipient();
  const updateRecipient = useUpdateRecipient();
  const deleteRecipient = useDeleteRecipient();
  const updateRule = useUpdateRule();
  const updateSettings = useUpdateBusinessSettings();
  const sendDigest = useSendDigest();
  const [testAddress, setTestAddress] = useState("");
  const [testResult, setTestResult] = useState<string>();
  const [newName, setNewName] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [addError, setAddError] = useState<string>();
  const [adding, setAdding] = useState(false);
  const [removeTarget, setRemoveTarget] = useState<RecipientResponse>();
  const [saved, setSaved] = useState<string>();
  const [digestResult, setDigestResult] = useState<string>();
  const [previewId, setPreviewId] = useState<string>();
  const loading = server.isLoading || recipients.isLoading || rules.isLoading || settings.isLoading || notifications.isLoading;
  const failed = server.isError || recipients.isError || rules.isError || settings.isError || notifications.isError;
  const defaultAddress = testAddress || recipients.data?.[0]?.email || "";

  const markSaved = (section: string) => {
    setSaved(section);
    window.setTimeout(() => setSaved((current) => current === section ? undefined : current), 1800);
  };
  const sendTest = async () => {
    if (!emailPattern.test(defaultAddress)) {
      setTestResult("Enter a valid email address.");
      return;
    }
    const result = await testEmail.mutateAsync({ to: defaultAddress });
    setTestResult(result.status === "sent" ? `Test email sent to ${defaultAddress}. Check your inbox (Mailpit: localhost:8025).` : `Test email failed: ${result.error ?? "check the mail server"}.`);
  };
  const addRecipient = async () => {
    if (!newName.trim()) return setAddError("Enter a recipient name.");
    if (!emailPattern.test(newEmail)) return setAddError("Enter a valid email address.");
    await createRecipient.mutateAsync({ name: newName.trim(), email: newEmail, workspace, active: true, rules: subscriptions.map(([kind]) => kind) });
    await recipients.refetch();
    setNewName(""); setNewEmail(""); setAddError(undefined); setAdding(false);
  };
  const toggleSubscription = async (recipient: RecipientResponse, kind: string, checked: boolean) => {
    const next = checked ? [...new Set([...recipient.rules, kind])] : recipient.rules.filter((item) => item !== kind);
    await updateRecipient.mutateAsync({ id: recipient.recipient_id, body: { rules: next } });
    await recipients.refetch();
    markSaved("recipients");
  };
  const saveRule = async (rule: RuleResponse, enabled = rule.enabled, params: Record<string, Json> = rule.params) => {
    await updateRule.mutateAsync({ id: rule.rule_id, body: { enabled, params } });
    await rules.refetch();
    markSaved("rules");
  };

  return (
    <div className="mx-auto grid max-w-[1440px] md:grid-cols-[190px_minmax(0,1fr)]">
      <aside className="border-b border-rule px-4 py-7 md:min-h-[calc(100vh-56px)] md:border-b-0 md:border-r md:px-6">
        <h1 className="heading text-lg">Settings</h1>
        <nav className="mt-5"><NavLink to="/settings/notifications" className="block border-l-2 border-ink py-2 pl-3 text-sm font-medium">Notifications</NavLink></nav>
      </aside>
      <div className="min-w-0 px-4 py-7 sm:px-7 lg:px-10">
        <div className="mb-7"><h2 className="heading text-2xl">Notifications</h2><p className="mt-1 text-sm text-graphite">Choose who hears about failures and when.</p></div>
        {failed ? <ErrorState onRetry={() => { server.refetch(); recipients.refetch(); rules.refetch(); settings.refetch(); notifications.refetch(); }} /> : loading ? <div className="space-y-5"><Skeleton className="h-32" /><Skeleton className="h-56" /><Skeleton className="h-64" /></div> : <>
          <section className="border-y border-rule py-6">
            <div className="flex flex-wrap items-start justify-between gap-4"><div><h3 className="heading text-lg">Mail server</h3><p className="mt-3 flex items-center gap-2 text-sm"><span className={`h-2 w-2 rounded-full ${server.data?.connected ? "bg-normal" : "bg-warning"}`} />{server.data?.connected ? `Connected to ${server.data.host}:${server.data.port}${server.data.host === "localhost" ? " (Mailpit)" : ""}` : `Can't reach the mail server at ${server.data?.host}:${server.data?.port}. Start Mailpit or update SMTP settings in .env.`}</p><p className="mt-2 text-sm text-graphite">Sender: {server.data?.sender}</p><p className="mt-1 text-xs text-graphite">Change these settings in the <code>.env</code> file on the server.</p></div>{server.data?.host === "localhost" && <a href="http://localhost:8025" target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-sm text-advisory">Open Mailpit inbox <ExternalLink className="h-3.5 w-3.5" /></a>}</div>
            <div className="mt-5 flex max-w-xl flex-wrap gap-2"><input aria-label="Test email address" value={testAddress} onChange={(event) => setTestAddress(event.target.value)} placeholder={recipients.data?.[0]?.email ?? "name@example.com"} className="h-9 min-w-64 flex-1 rounded-control border border-rule bg-panel px-3 text-sm" /><Button loading={testEmail.isPending} onClick={sendTest}><Mail className="h-4 w-4" />Send test email</Button></div>
            {testResult && <p className={`mt-3 text-sm ${testResult.includes("failed") || testResult.startsWith("Enter") ? "text-warning" : "text-normal"}`}>{testResult}</p>}
          </section>

          <section className="py-6 border-b border-rule">
            <div className="flex items-center justify-between"><h3 className="heading text-lg">Recipients</h3>{saved === "recipients" && <span className="text-xs text-normal">Saved</span>}</div>
            <div className="mt-4 overflow-x-auto"><table className="w-full min-w-[920px] text-left text-sm"><thead><tr className="h-10 border-y border-rule bg-paper text-xs text-graphite"><th className="px-3 font-medium">Name</th><th className="px-3 font-medium">Email</th>{subscriptions.map(([kind, label]) => <th key={kind} className="w-24 px-2 text-center font-medium">{label}</th>)}<th className="w-12" /></tr></thead><tbody>{recipients.data?.map((recipient) => <tr key={recipient.recipient_id} className="h-14 border-b border-rule-soft"><td className="px-3 font-medium">{recipient.name}</td><td className="px-3">{recipient.email}</td>{subscriptions.map(([kind, label]) => <td key={kind} className="px-2 text-center"><input aria-label={`${label} for ${recipient.name}`} type="checkbox" checked={recipient.rules.includes(kind)} disabled={updateRecipient.isPending} onChange={(event) => toggleSubscription(recipient, kind, event.target.checked)} className="h-4 w-4 accent-orange" /></td>)}<td><button aria-label={`Remove ${recipient.name}`} onClick={() => setRemoveTarget(recipient)} className="p-2 text-graphite hover:text-warning"><Trash2 className="h-4 w-4" /></button></td></tr>)}</tbody></table></div>
            {adding ? <div className="mt-4 flex flex-wrap items-start gap-2"><input aria-label="Recipient name" value={newName} onChange={(event) => setNewName(event.target.value)} placeholder="Name" className="h-9 rounded-control border border-rule px-3 text-sm" /><div><input aria-label="Recipient email" value={newEmail} onChange={(event) => setNewEmail(event.target.value)} placeholder="name@example.com" className="h-9 rounded-control border border-rule px-3 text-sm" />{addError && <p className="mt-1 text-xs text-warning">{addError}</p>}</div><Button variant="ink" loading={createRecipient.isPending} onClick={addRecipient}>Add</Button><Button onClick={() => { setAdding(false); setAddError(undefined); }}>Cancel</Button></div> : <Button className="mt-4" onClick={() => setAdding(true)}><Plus className="h-4 w-4" />Add recipient</Button>}
          </section>

          <section className="py-6 border-b border-rule">
            <div className="flex items-center justify-between"><h3 className="heading text-lg">Rules</h3>{saved === "rules" && <span className="text-xs text-normal">Saved</span>}</div>
            <div className="mt-4 divide-y divide-rule-soft border-y border-rule">{rules.data?.map((rule) => <div key={rule.rule_id} className="flex min-h-14 flex-wrap items-center gap-3 py-3"><label className="flex min-w-56 flex-1 items-center gap-3"><input type="checkbox" checked={rule.enabled} onChange={(event) => saveRule(rule, event.target.checked)} className="h-4 w-4 accent-orange" /><span className="font-medium">{ruleLabels[rule.kind] ?? rule.kind}</span></label>{rule.kind === "failure_rate" && <><label className="text-xs text-graphite">Above <input aria-label="Failure rate threshold" type="number" min="1" max="100" defaultValue={Number(rule.params.threshold ?? 0.2) * 100} onBlur={(event) => saveRule(rule, rule.enabled, { ...rule.params, threshold: Number(event.target.value) / 100 })} className="mx-1 h-8 w-16 rounded-control border border-rule px-2 font-mono text-ink" />%</label><label className="text-xs text-graphite">at least <input aria-label="Minimum conversations" type="number" min="1" defaultValue={Number(rule.params.min_runs ?? 10)} onBlur={(event) => saveRule(rule, rule.enabled, { ...rule.params, min_runs: Number(event.target.value) })} className="mx-1 h-8 w-16 rounded-control border border-rule px-2 font-mono text-ink" /> conversations/hour</label></>}{rule.kind === "daily_digest" && <label className="text-xs text-graphite">At <input aria-label="Daily summary time" type="time" defaultValue={String(rule.params.time ?? "09:00")} onBlur={(event) => saveRule(rule, rule.enabled, { ...rule.params, time: event.target.value })} className="ml-1 h-8 rounded-control border border-rule px-2 font-mono text-ink" /></label>}</div>)}</div>
            <div className="mt-4 flex flex-wrap items-center gap-3"><label className="text-sm">Cost per wrong answer ₹ <input aria-label="Cost per wrong answer" type="number" min="0" defaultValue={settings.data?.cost_per_wrong_answer_inr} onBlur={async (event) => { await updateSettings.mutateAsync({ cost_per_wrong_answer_inr: Number(event.target.value) }); markSaved("rules"); }} className="h-8 w-24 rounded-control border border-rule px-2 font-mono" /></label><span className="text-xs text-graphite">Used for estimates</span><Button className="ml-auto" loading={sendDigest.isPending} onClick={async () => { await sendDigest.mutateAsync(); setDigestResult("Daily summary queued."); await notifications.refetch(); }}>Send summary now</Button></div>{digestResult && <p className="mt-2 text-right text-xs text-normal">{digestResult}</p>}
          </section>

          <section className="py-6">
            <h3 className="heading text-lg">Sent emails</h3>
            <div className="mt-4 overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><thead><tr className="h-10 border-y border-rule bg-paper text-xs text-graphite"><th className="w-36 px-3 font-medium">Time</th><th className="px-3 font-medium">Subject</th><th className="w-56 px-3 font-medium">Recipients</th><th className="w-28 px-3 font-medium">Status</th><th className="w-24 px-3" /></tr></thead><tbody>{notifications.data?.items.map((item) => <tr key={item.notification_id} className="h-14 border-b border-rule-soft"><td className="px-3 font-mono text-xs text-graphite">{new Date(item.created_at).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</td><td className="truncate px-3 font-medium" title={item.subject}>{item.subject}</td><td className="truncate px-3" title={item.recipients.join(", ")}>{item.recipients.join(", ")}</td><td className="px-3"><span className={`rounded-chip px-2.5 py-1 text-xs capitalize ${statusStyle(item.status)}`}>{item.status}</span></td><td className="px-3"><button onClick={() => setPreviewId(item.notification_id)} className="text-sm text-advisory">Preview</button></td></tr>)}</tbody></table></div>
          </section>
        </>}
      </div>
      <EmailPreviewDrawer notificationId={previewId} onClose={() => setPreviewId(undefined)} />
      {removeTarget && <div className="fixed inset-0 z-50 grid place-items-center bg-ink/35 p-4" role="dialog" aria-modal="true" aria-label="Remove recipient"><div className="w-full max-w-md rounded-panel border border-rule bg-panel p-6 shadow-popover"><h2 className="heading text-lg">Remove {removeTarget.name}?</h2><p className="mt-3 text-sm text-graphite">They will stop receiving every Black Box notification.</p><div className="mt-6 flex justify-end gap-2"><Button onClick={() => setRemoveTarget(undefined)}>Cancel</Button><Button variant="ink" loading={deleteRecipient.isPending} onClick={async () => { await deleteRecipient.mutateAsync(removeTarget.recipient_id); setRemoveTarget(undefined); await recipients.refetch(); }}>Remove</Button></div></div></div>}
    </div>
  );
}