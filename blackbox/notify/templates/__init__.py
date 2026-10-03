from dataclasses import dataclass
from html import escape
from typing import Any


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    text: str
    html: str


def format_inr(value: int) -> str:
    digits = str(abs(value))
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups: list[str] = []
        while head:
            groups.append(head[-2:])
            head = head[:-2]
        digits = f"{','.join(reversed(groups))},{tail}"
    return f"{'-' if value < 0 else ''}₹{digits}"


def _base_title(context: dict[str, Any]) -> str:
    return f"{str(context.get('category', 'support')).lower()} questions answered wrong"


def _subject(kind: str, context: dict[str, Any]) -> str:
    title = _base_title(context)
    n_runs = int(context.get("n_runs", 0))
    if kind == "incident_opened":
        return f"New incident: {title} ({n_runs} conversations)"
    if kind == "incident_escalated":
        return f"Incident is now high severity: {title}"
    if kind == "failure_rate":
        rate = float(context.get("failure_rate", 0.0))
        threshold = float(context.get("threshold", 0.2))
        return (
            f"Support agent failure rate is {rate:.0%} in the last hour "
            f"(threshold {threshold:.0%})"
        )
    if kind == "fix_verified":
        passed = int(context.get("n_passed", 0))
        total = int(context.get("n_total", n_runs))
        return f"Fix verified on {passed} of {total} conversations: {title}"
    if kind == "incident_resolved":
        return f"Resolved: {title}"
    if kind == "daily_digest":
        return (
            "Daily summary for Nimbu Living support: "
            f"{int(context.get('open_incidents', 0))} open incidents, "
            f"{format_inr(int(context.get('estimated_cost', 0)))} estimated cost"
        )
    if kind == "test":
        return "Test email from Black Box"
    raise ValueError(f"Unknown notification kind: {kind}")


def render_email(kind: str, context: dict[str, Any]) -> RenderedEmail:
    subject = _subject(kind, context)
    workspace = str(context.get("workspace_name", "Nimbu Living support"))
    summary = str(context.get("summary", "Black Box notification delivery is working."))
    question = str(context.get("question", ""))
    wrong_answer = str(context.get("wrong_answer", ""))
    correct_answer = str(context.get("correct_answer", ""))
    cause = str(context.get("cause", ""))
    reason = str(context.get("reason", ""))
    evidence = str(context.get("evidence", ""))
    severity = str(context.get("severity", "low"))
    estimated_cost = format_inr(int(context.get("estimated_cost", 0)))
    incident_url = str(context.get("incident_url", ""))
    conversation_url = str(context.get("conversation_url", ""))
    details = "\n".join(
        line
        for line in (
            summary,
            f"Customer message: {question}" if question else "",
            f"Agent reply: {wrong_answer}" if wrong_answer else "",
            f"Correct answer per policy: {correct_answer}" if correct_answer else "",
            f"Likely cause: {cause}. {reason}" if cause else "",
            f"Evidence: {evidence}" if evidence else "",
            f"Estimated cost: {estimated_cost}" if context.get("estimated_cost") else "",
            f"Open incident: {incident_url}" if incident_url else "",
            f"View the example conversation: {conversation_url}" if conversation_url else "",
            (
                "You get this email because you're subscribed to "
                f"{kind.replace('_', ' ')} for {workspace}. Change this in "
                "Black Box → Settings → Notifications."
            ),
        )
        if line
    )
    severity_color = {"high": "#C8223A", "medium": "#D48A00"}.get(
        severity, "#5B6873"
    )
    button = (
        '<table role="presentation" cellspacing="0" cellpadding="0"><tr><td '
        'style="background:#FF4F00;border-radius:6px;padding:12px 18px">'
        f'<a href="{escape(incident_url)}" style="color:#FFFFFF;text-decoration:none;'
        'font-weight:bold">Open incident</a></td></tr></table>'
        if incident_url
        else ""
    )
    html = f"""<!doctype html>
<html><body style="margin:0;background:#EEF1F2;color:#14202B;font-family:Arial,Helvetica,sans-serif">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#EEF1F2"><tr><td align="center" style="padding:24px">
<table role="presentation" width="600" cellspacing="0" cellpadding="0" style="max-width:600px;width:100%;background:#FFFFFF;border:1px solid #C9D2D8">
<tr><td style="padding:24px;border-bottom:1px solid #C9D2D8"><span style="display:inline-block;width:12px;height:12px;background:#FF4F00;margin-right:8px"></span><strong>Black Box</strong></td></tr>
<tr><td style="padding:24px"><h1 style="font-size:22px;margin:0 0 16px">{escape(subject)}</h1>
<p style="color:#5B6873"><span style="color:{severity_color}">●</span> {escape(severity)}</p>
<p>{escape(summary)}</p>
{f'<p><strong>Customer message</strong><br>{escape(question)}</p>' if question else ''}
{f'<p><strong>Agent reply</strong><br>{escape(wrong_answer)}</p>' if wrong_answer else ''}
{f'<p><strong>Correct answer per policy</strong><br>{escape(correct_answer)}</p>' if correct_answer else ''}
{f'<p><strong>Likely cause</strong><br>{escape(cause)}. {escape(reason)}</p>' if cause else ''}
{f'<blockquote style="border-left:3px solid #C9D2D8;margin:16px 0;padding:8px 12px">{escape(evidence)}</blockquote>' if evidence else ''}
{f'<p><strong>{estimated_cost} estimated cost</strong></p>' if context.get('estimated_cost') else ''}
{button}
{f'<p><a href="{escape(conversation_url)}">View the example conversation</a></p>' if conversation_url else ''}
</td></tr><tr><td style="padding:18px 24px;color:#5B6873;border-top:1px solid #C9D2D8;font-size:12px">You get this email because you're subscribed to {escape(kind.replace('_', ' '))} for {escape(workspace)}. Change this in Black Box → Settings → Notifications.</td></tr>
</table></td></tr></table></body></html>"""
    return RenderedEmail(subject=subject, text=details, html=html)