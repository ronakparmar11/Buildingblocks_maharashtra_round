from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlmodel import Session, select

from blackbox.config import get_settings
from blackbox.notify.templates import RenderedEmail, render_email
from blackbox.notify.worker import NotificationWorker, worker
from blackbox.store.db import get_session
from blackbox.store.models import (
    Incident,
    NotificationLog,
    NotificationRule,
    Recipient,
    Run,
    Step,
    Task,
)

DEFAULT_RULES: dict[str, tuple[bool, dict[str, Any]]] = {
    "incident_opened": (True, {}),
    "incident_escalated": (True, {}),
    "failure_rate": (True, {"threshold": 0.2, "min_runs": 10}),
    "fix_verified": (True, {}),
    "incident_resolved": (False, {}),
    "daily_digest": (True, {}),
}


def seed_notification_settings(workspace: str, session: Session) -> None:
    existing = {
        rule.kind
        for rule in session.exec(
            select(NotificationRule).where(NotificationRule.workspace == workspace)
        ).all()
    }
    for kind, (enabled, params) in DEFAULT_RULES.items():
        if kind not in existing:
            session.add(
                NotificationRule(
                    workspace=workspace,
                    kind=kind,
                    enabled=enabled,
                    params=params,
                )
            )
    settings = get_settings()
    recipient = session.exec(
        select(Recipient).where(
            Recipient.workspace == workspace,
            Recipient.email == settings.NOTIFY_DEFAULT_EMAIL,
        )
    ).first()
    if settings.NOTIFY_DEFAULT_EMAIL and recipient is None:
        session.add(
            Recipient(
                name="Support AI team",
                email=settings.NOTIFY_DEFAULT_EMAIL,
                workspace=workspace,
                active=True,
                rules=list(DEFAULT_RULES),
            )
        )
    session.commit()


def _incident_context(session: Session, incident: Incident) -> dict[str, Any]:
    run = session.get(Run, incident.representative_run_id)
    task = session.get(Task, run.task_id) if run is not None else None
    step = (
        session.exec(
            select(Step).where(
                Step.run_id == run.run_id,
                Step.name == incident.cause_step_name,
            )
        ).first()
        if run is not None
        else None
    )
    evidence = ""
    if step is not None:
        passages = step.output.get("passages", [])
        if isinstance(passages, list) and passages and isinstance(passages[0], dict):
            article = passages[0]
            archived = (
                ", which is archived" if article.get("status") == "archived" else ""
            )
            evidence = f"Top article was ‘{article.get('title', '')}’{archived}"
    verify = incident.verify_result or {}
    settings = get_settings()
    return {
        "workspace_name": "Nimbu Living support",
        "category": incident.category,
        "n_runs": incident.n_runs,
        "severity": incident.severity,
        "estimated_cost": incident.est_cost_inr,
        "summary": (
            f"{incident.n_runs} customers got a wrong answer about "
            f"{incident.category} since {incident.first_seen:%H:%M}."
        ),
        "question": task.question if task is not None else "",
        "wrong_answer": run.final_answer if run is not None else "",
        "correct_answer": task.gold_answer if task is not None else "",
        "cause": {
            "retrieve": "Searching the help center",
            "extract": "Reading the help article",
            "synthesize": "Writing the final reply",
            "plan": "Planning the answer",
        }.get(incident.cause_step_name, incident.cause_step_name),
        "reason": incident.title.split("—", 1)[-1].strip(),
        "evidence": evidence,
        "n_passed": verify.get("n_passed", 0),
        "n_total": verify.get("n_total", incident.n_runs),
        "incident_url": f"{settings.APP_BASE_URL}/incidents/{incident.incident_id}",
        "conversation_url": (
            f"{settings.APP_BASE_URL}/conversations/{run.run_id}"
            if run is not None
            else ""
        ),
    }


def _failure_rate_context(
    session: Session, workspace: str, rule: NotificationRule
) -> dict[str, Any] | None:
    since = datetime.now(UTC) - timedelta(hours=1)
    runs = list(
        session.exec(
            select(Run).where(
                Run.workspace == workspace,
                Run.origin.in_(("live", "simulated")),
                Run.created_at >= since,
            )
        ).all()
    )
    minimum = int(rule.params.get("min_runs", 10))
    threshold = float(rule.params.get("threshold", 0.2))
    rate = sum(run.outcome == "fail" for run in runs) / len(runs) if runs else 0.0
    if len(runs) < minimum or rate <= threshold:
        return None
    return {
        "workspace_name": "Nimbu Living support",
        "failure_rate": rate,
        "threshold": threshold,
        "summary": (
            f"{sum(run.outcome == 'fail' for run in runs)} of {len(runs)} "
            "conversations failed in the last hour."
        ),
    }


def _digest_context(session: Session, workspace: str) -> dict[str, Any]:
    incidents = list(
        session.exec(
            select(Incident).where(
                Incident.workspace == workspace,
                Incident.status != "resolved",
            )
        ).all()
    )
    return {
        "workspace_name": "Nimbu Living support",
        "open_incidents": len(incidents),
        "estimated_cost": sum(item.est_cost_inr for item in incidents),
        "summary": f"There are {len(incidents)} open incidents requiring attention.",
    }


def _log_throttled(
    session: Session,
    workspace: str,
    event: str,
    incident_id: str | None,
    recipients: list[str],
    rendered: RenderedEmail,
) -> None:
    session.add(
        NotificationLog(
            workspace=workspace,
            rule_kind=event,
            incident_id=incident_id,
            recipients=recipients,
            subject=rendered.subject,
            html=rendered.html,
            text=rendered.text,
            status="throttled",
        )
    )
    session.commit()


def evaluate_rules(
    event: str,
    workspace: str,
    incident: Incident | None = None,
    *,
    notification_worker: NotificationWorker = worker,
) -> NotificationLog | None:
    with get_session() as session:
        seed_notification_settings(workspace, session)
        rule = session.exec(
            select(NotificationRule).where(
                NotificationRule.workspace == workspace,
                NotificationRule.kind == event,
            )
        ).first()
        if rule is None or not rule.enabled:
            return None
        recipients = [
            recipient.email
            for recipient in session.exec(
                select(Recipient).where(
                    Recipient.workspace == workspace,
                    Recipient.active.is_(True),
                )
            ).all()
            if event in recipient.rules
        ]
        if not recipients:
            return None
        if event == "failure_rate":
            context = _failure_rate_context(session, workspace, rule)
            if context is None:
                return None
        elif event == "daily_digest":
            context = _digest_context(session, workspace)
        elif incident is not None:
            context = _incident_context(session, incident)
        else:
            return None
        rendered = render_email(event, context)
        incident_id = incident.incident_id if incident is not None else None
        cutoff = datetime.now(UTC) - timedelta(
            minutes=get_settings().NOTIFY_THROTTLE_MINUTES
        )
        recent = session.exec(
            select(func.count())
            .select_from(NotificationLog)
            .where(
                NotificationLog.workspace == workspace,
                NotificationLog.rule_kind == event,
                NotificationLog.incident_id == incident_id,
                NotificationLog.status.in_(("queued", "sent")),
                NotificationLog.created_at >= cutoff,
            )
        ).one()
        if recent:
            _log_throttled(
                session, workspace, event, incident_id, recipients, rendered
            )
            return None
    return notification_worker.enqueue(
        workspace, event, recipients, rendered, incident_id=incident_id
    )