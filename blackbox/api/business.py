from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlmodel import col, select

from blackbox.api.common import run_summary
from blackbox.api.replay import submit_job, update_job
from blackbox.api.schemas import (
    BusinessSettingsRequest,
    BusinessSettingsResponse,
    DailyMetric,
    FleetReasonCount,
    FleetStepCount,
    IncidentDetailResponse,
    IncidentListResponse,
    IncidentPatchRequest,
    IncidentRunSummary,
    IncidentSummary,
    JobCreatedResponse,
    NotificationIdResponse,
    NotificationListResponse,
    NotificationPreviewResponse,
    NotificationStatusResponse,
    NotificationTestRequest,
    NotificationTestResponse,
    OverviewKpis,
    OverviewResponse,
    RecipientCreate,
    RecipientResponse,
    RecipientUpdate,
    RuleResponse,
    RuleUpdate,
    SimulateRequest,
    VerifyFixRequest,
    WorkspaceSummary,
)
from blackbox.config import get_settings
from blackbox.incidents.engine import (
    ALLOWED_TRANSITIONS,
    explain_incident,
    transition_status,
    verify_fix,
)
from blackbox.incidents.simulate import run_simulation
from blackbox.notify.mailer import Mailer
from blackbox.notify.rules import evaluate_rules, seed_notification_settings
from blackbox.notify.templates import render_email
from blackbox.notify.worker import worker as notification_worker
from blackbox.store.db import get_session
from blackbox.store.models import (
    Incident,
    IncidentEvent,
    NotificationLog,
    NotificationRule,
    Prediction,
    Recipient,
    Run,
    Step,
    Task,
)

router = APIRouter()

WORKSPACES = {
    "hotpot": ("HotpotQA", "Public multi-hop question answering benchmark."),
    "nimbu": ("Nimbu Living support", "Customer support for an Indian home and kitchen store."),
}


def _incident_or_404(incident_id: str, workspace: str) -> Incident:
    with get_session() as session:
        incident = session.get(Incident, incident_id)
        if incident is None or incident.workspace != workspace:
            raise HTTPException(status_code=404, detail="Incident not found")
        session.expunge(incident)
        return incident


def _incident_summary(incident: Incident) -> IncidentSummary:
    return IncidentSummary.model_validate(incident)


@router.get("/workspaces", response_model=list[WorkspaceSummary])
def get_workspaces() -> list[WorkspaceSummary]:
    with get_session() as session:
        counts = Counter(session.exec(select(Run.workspace)).all())
    return [
        WorkspaceSummary(
            id=workspace,
            name=name,
            description=description,
            n_runs=counts[workspace],
        )
        for workspace, (name, description) in WORKSPACES.items()
    ]


@router.get("/overview", response_model=OverviewResponse)
def get_overview(workspace: str = "hotpot") -> OverviewResponse:
    since = datetime.now(UTC) - timedelta(days=6)
    with get_session() as session:
        runs = list(
            session.exec(
                select(Run).where(
                    Run.workspace == workspace,
                    Run.created_at >= since.replace(hour=0, minute=0, second=0),
                )
            ).all()
        )
        incidents = list(
            session.exec(
                select(Incident)
                .where(
                    Incident.workspace == workspace,
                    Incident.status != "resolved",
                )
                .order_by(col(Incident.last_seen).desc())
            ).all()
        )
        run_ids = {run.run_id for run in runs if run.outcome == "fail"}
        predictions = list(
            session.exec(
                select(Prediction).where(
                    Prediction.run_id.in_(run_ids), Prediction.rank == 1
                )
            ).all()
        ) if run_ids else []
        steps = {
            (step.run_id, step.step_key): step
            for step in session.exec(select(Step)).all()
            if step.run_id in run_ids
        }
        rule = session.exec(
            select(NotificationRule).where(
                NotificationRule.workspace == workspace,
                NotificationRule.kind == "failure_rate",
            )
        ).first()

    by_date = Counter(run.created_at.date() for run in runs)
    wrong_by_date = Counter(
        run.created_at.date() for run in runs if run.outcome == "fail"
    )
    daily: list[DailyMetric] = []
    for days_ago in range(6, -1, -1):
        current = datetime.now(UTC).date() - timedelta(days=days_ago)
        conversations = by_date[current]
        wrong = wrong_by_date[current]
        daily.append(
            DailyMetric(
                date=current.isoformat(),
                conversations=conversations,
                wrong=wrong,
                rate=wrong / conversations if conversations else 0.0,
            )
        )
    step_counts = Counter(
        steps[(item.run_id, item.step_key)].name
        for item in predictions
        if (item.run_id, item.step_key) in steps
    )
    reason_counts = Counter(
        (str(reason.get("feature", "")), str(reason.get("text", "")))
        for item in predictions
        for reason in item.reasons
    )
    wrong = sum(run.outcome == "fail" for run in runs)
    threshold = float(rule.params.get("threshold", 0.2)) if rule else 0.2
    rate = wrong / len(runs) if runs else 0.0
    return OverviewResponse(
        headline=(
            "Support quality needs attention" if rate > threshold else "Support quality is healthy"
        ),
        kpis=OverviewKpis(
            conversations=len(runs),
            wrong=wrong,
            failure_rate=rate,
            open_incidents=len(incidents),
            estimated_cost_inr=sum(item.est_cost_inr for item in incidents),
        ),
        daily=daily,
        open_incidents=[_incident_summary(item) for item in incidents],
        by_step_name=[
            FleetStepCount(
                name=name,
                count=count,
                pct=count / wrong if wrong else 0.0,
            )
            for name, count in step_counts.most_common()
        ],
        by_reason=[
            FleetReasonCount(feature=feature, text=text, count=count)
            for (feature, text), count in reason_counts.most_common()
        ],
        threshold=threshold,
    )


@router.get("/incidents", response_model=IncidentListResponse)
def list_incidents(
    workspace: str = "hotpot",
    status_filter: str | None = Query(default=None, alias="status"),
    severity: str | None = None,
    category: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> IncidentListResponse:
    with get_session() as session:
        statement = select(Incident).where(Incident.workspace == workspace)
        if status_filter is not None:
            statement = statement.where(Incident.status == status_filter)
        if severity is not None:
            statement = statement.where(Incident.severity == severity)
        if category is not None:
            statement = statement.where(Incident.category == category)
        incidents = list(
            session.exec(statement.order_by(col(Incident.last_seen).desc())).all()
        )
    return IncidentListResponse(
        items=[_incident_summary(item) for item in incidents[offset : offset + limit]],
        total=len(incidents),
    )


@router.get("/incidents/{incident_id}", response_model=IncidentDetailResponse)
def get_incident(
    incident_id: str, workspace: str = "hotpot"
) -> IncidentDetailResponse:
    with get_session() as session:
        incident = session.get(Incident, incident_id)
        if incident is None or incident.workspace != workspace:
            raise HTTPException(status_code=404, detail="Incident not found")
        representative = session.get(Run, incident.representative_run_id)
        predictions = list(
            session.exec(
                select(Prediction)
                .where(Prediction.run_id == incident.representative_run_id)
                .order_by(Prediction.rank)
            ).all()
        )
        runs = list(
            session.exec(
                select(Run)
                .where(Run.incident_id == incident_id)
                .order_by(col(Run.created_at).desc())
            ).all()
        )
        run_items: list[IncidentRunSummary] = []
        for run in runs:
            task = session.get(Task, run.task_id)
            if task is None:
                continue
            run_items.append(
                IncidentRunSummary(
                    **run_summary(session, run).model_dump(),
                    customer_message=task.question,
                    agent_reply=run.final_answer or "",
                    correct_answer=task.gold_answer,
                )
            )
        events = list(
            session.exec(
                select(IncidentEvent)
                .where(IncidentEvent.incident_id == incident_id)
                .order_by(IncidentEvent.created_at)
            ).all()
        )
        notifications = list(
            session.exec(
                select(NotificationLog)
                .where(NotificationLog.incident_id == incident_id)
                .order_by(col(NotificationLog.created_at).desc())
            ).all()
        )
        explanation = explain_incident(incident, session)
        representative_summary = (
            run_summary(session, representative) if representative is not None else None
        )
    return IncidentDetailResponse(
        incident=_incident_summary(incident),
        explanation=explanation,
        representative_run=representative_summary,
        reasons=[
            reason
            for prediction in predictions
            if prediction.rank == 1
            for reason in prediction.reasons
        ],
        runs=run_items,
        events=events,
        notifications=notifications,
    )


@router.patch("/incidents/{incident_id}", response_model=IncidentSummary)
def patch_incident(
    incident_id: str, request: IncidentPatchRequest, workspace: str = "hotpot"
) -> IncidentSummary:
    with get_session() as session:
        incident = session.get(Incident, incident_id)
        if incident is None or incident.workspace != workspace:
            raise HTTPException(status_code=404, detail="Incident not found")
        if (
            request.status is not None
            and request.status != incident.status
            and request.status not in ALLOWED_TRANSITIONS.get(incident.status, set())
        ):
            raise HTTPException(
                status_code=422,
                detail=f"Cannot change incident from {incident.status} to {request.status}",
            )
        if request.owner is not None and request.owner != incident.owner:
            incident.owner = request.owner
            session.add(
                IncidentEvent(
                    incident_id=incident_id,
                    kind="owner_changed",
                    text=f"Owner changed to {request.owner or 'unassigned'}.",
                )
            )
        if request.note:
            session.add(
                IncidentEvent(
                    incident_id=incident_id,
                    kind="note",
                    text=request.note,
                )
            )
        session.add(incident)
        session.commit()
        if request.status is not None and request.status != incident.status:
            try:
                incident = transition_status(
                    incident_id, request.status, session=session
                )
            except ValueError as error:
                raise HTTPException(status_code=422, detail=str(error)) from error
        else:
            session.refresh(incident)
        return _incident_summary(incident)


@router.post(
    "/incidents/{incident_id}/verify-fix", response_model=JobCreatedResponse
)
def verify_incident_fix(
    incident_id: str, request: VerifyFixRequest, workspace: str = "hotpot"
) -> JobCreatedResponse:
    _incident_or_404(incident_id, workspace)
    return JobCreatedResponse(
        job_id=submit_job(
            lambda: verify_fix(incident_id, request.repair_run_id)
        )
    )


@router.post(
    "/incidents/{incident_id}/notify", response_model=NotificationIdResponse
)
def notify_incident(
    incident_id: str, workspace: str = "hotpot"
) -> NotificationIdResponse:
    incident = _incident_or_404(incident_id, workspace)
    row = evaluate_rules("incident_opened", incident.workspace, incident)
    if row is None:
        raise HTTPException(
            status_code=409,
            detail="Notification disabled, has no recipients, or is throttled",
        )
    return NotificationIdResponse(notification_id=row.notification_id)


@router.get("/notifications/status", response_model=NotificationStatusResponse)
def get_notification_status() -> NotificationStatusResponse:
    settings = get_settings()
    connected, error = Mailer(settings).check_connection()
    if error and settings.SMTP_PASSWORD:
        error = error.replace(settings.SMTP_PASSWORD, "***")
    remote = settings.SMTP_HOST not in {"localhost", "127.0.0.1", "::1"}
    return NotificationStatusResponse(
        configured=bool(settings.SMTP_HOST and settings.SMTP_FROM),
        host=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        connected=connected,
        sender=settings.SMTP_FROM,
        last_error=error,
        demo_mode_blocked=bool(settings.BLACKBOX_DEMO_MODE and remote),
    )


@router.post("/notifications/test", response_model=NotificationTestResponse)
def send_test_notification(
    request: NotificationTestRequest,
) -> NotificationTestResponse:
    rendered = render_email("test", {"workspace_name": "Nimbu Living support"})
    row = notification_worker.enqueue("nimbu", "test", [request.to], rendered)
    notification_worker.wait()
    with get_session() as session:
        stored = session.get(NotificationLog, row.notification_id)
        assert stored is not None
        return NotificationTestResponse(status=stored.status, error=stored.error)


@router.get("/recipients", response_model=list[RecipientResponse])
def list_recipients(workspace: str = "nimbu") -> list[RecipientResponse]:
    with get_session() as session:
        seed_notification_settings(workspace, session)
        return [
            RecipientResponse.model_validate(item)
            for item in session.exec(
                select(Recipient)
                .where(Recipient.workspace == workspace)
                .order_by(Recipient.name)
            ).all()
        ]


@router.post(
    "/recipients", response_model=RecipientResponse, status_code=status.HTTP_201_CREATED
)
def create_recipient(request: RecipientCreate) -> RecipientResponse:
    with get_session() as session:
        existing = session.exec(
            select(Recipient).where(
                Recipient.workspace == request.workspace,
                Recipient.email == request.email,
            )
        ).first()
        if existing is not None:
            raise HTTPException(status_code=409, detail="Recipient already exists")
        recipient = Recipient(**request.model_dump())
        session.add(recipient)
        session.commit()
        session.refresh(recipient)
        return RecipientResponse.model_validate(recipient)


@router.patch("/recipients/{recipient_id}", response_model=RecipientResponse)
def update_recipient(
    recipient_id: str, request: RecipientUpdate
) -> RecipientResponse:
    with get_session() as session:
        recipient = session.get(Recipient, recipient_id)
        if recipient is None:
            raise HTTPException(status_code=404, detail="Recipient not found")
        for field, value in request.model_dump(exclude_unset=True).items():
            setattr(recipient, field, value)
        session.add(recipient)
        session.commit()
        session.refresh(recipient)
        return RecipientResponse.model_validate(recipient)


@router.delete("/recipients/{recipient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipient(recipient_id: str) -> Response:
    with get_session() as session:
        recipient = session.get(Recipient, recipient_id)
        if recipient is None:
            raise HTTPException(status_code=404, detail="Recipient not found")
        session.delete(recipient)
        session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/rules", response_model=list[RuleResponse])
def list_rules(workspace: str = "nimbu") -> list[RuleResponse]:
    with get_session() as session:
        seed_notification_settings(workspace, session)
        return [
            RuleResponse.model_validate(item)
            for item in session.exec(
                select(NotificationRule)
                .where(
                    NotificationRule.workspace == workspace,
                    NotificationRule.kind != "settings",
                )
                .order_by(NotificationRule.kind)
            ).all()
        ]


@router.put("/rules/{rule_id}", response_model=RuleResponse)
def update_rule(rule_id: str, request: RuleUpdate) -> RuleResponse:
    with get_session() as session:
        rule = session.get(NotificationRule, rule_id)
        if rule is None or rule.kind == "settings":
            raise HTTPException(status_code=404, detail="Rule not found")
        rule.enabled = request.enabled
        rule.params = request.params
        session.add(rule)
        session.commit()
        session.refresh(rule)
        return RuleResponse.model_validate(rule)


@router.get("/settings/business", response_model=BusinessSettingsResponse)
def get_business_settings(workspace: str = "nimbu") -> BusinessSettingsResponse:
    with get_session() as session:
        rule = session.exec(
            select(NotificationRule).where(
                NotificationRule.workspace == workspace,
                NotificationRule.kind == "settings",
            )
        ).first()
    value = (
        rule.params.get("cost_per_wrong_answer_inr")
        if rule is not None
        else get_settings().COST_PER_WRONG_ANSWER_INR
    )
    return BusinessSettingsResponse(cost_per_wrong_answer_inr=int(value))


@router.put("/settings/business", response_model=BusinessSettingsResponse)
def update_business_settings(
    request: BusinessSettingsRequest, workspace: str = "nimbu"
) -> BusinessSettingsResponse:
    with get_session() as session:
        rule = session.exec(
            select(NotificationRule).where(
                NotificationRule.workspace == workspace,
                NotificationRule.kind == "settings",
            )
        ).first()
        if rule is None:
            rule = NotificationRule(
                workspace=workspace,
                kind="settings",
                enabled=True,
            )
        rule.params = {
            "cost_per_wrong_answer_inr": request.cost_per_wrong_answer_inr
        }
        session.add(rule)
        session.commit()
    return BusinessSettingsResponse(
        cost_per_wrong_answer_inr=request.cost_per_wrong_answer_inr
    )


@router.get("/notifications", response_model=NotificationListResponse)
def list_notifications(
    workspace: str = "nimbu", limit: int = Query(default=50, ge=1, le=500)
) -> NotificationListResponse:
    with get_session() as session:
        rows = list(
            session.exec(
                select(NotificationLog)
                .where(NotificationLog.workspace == workspace)
                .order_by(col(NotificationLog.created_at).desc())
                .limit(limit)
            ).all()
        )
    return NotificationListResponse(items=rows)


@router.get(
    "/notifications/{notification_id}/preview",
    response_model=NotificationPreviewResponse,
)
def preview_notification(notification_id: str) -> NotificationPreviewResponse:
    with get_session() as session:
        row = session.get(NotificationLog, notification_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Notification not found")
        return NotificationPreviewResponse(
            subject=row.subject,
            html=row.html,
            text=row.text,
        )


@router.post("/notifications/digest", response_model=NotificationIdResponse)
def send_digest(workspace: str = "nimbu") -> NotificationIdResponse:
    row = evaluate_rules("daily_digest", workspace)
    if row is None:
        raise HTTPException(
            status_code=409,
            detail="Digest disabled, has no recipients, or is throttled",
        )
    return NotificationIdResponse(notification_id=row.notification_id)


@router.post("/simulate", response_model=JobCreatedResponse)
def simulate(request: SimulateRequest) -> JobCreatedResponse:
    job_id = uuid4().hex

    def progress(counters: dict[str, int]) -> None:
        update_job(
            job_id,
            min(counters["sent"] / request.n, 0.99),
            {
                "sent": counters["sent"],
                "failed": counters["wrong"],
                "incidents_opened": counters["incidents_opened"],
                "emails_sent": counters["emails_queued"],
            },
        )

    def operation() -> dict[str, Any]:
        result = run_simulation(
            workspace=request.workspace,
            n=request.n,
            failure_rate=request.failure_rate,
            seed=request.seed,
            progress_fn=progress,
        )
        return {
            "sent": result["sent"],
            "failed": result["wrong"],
            "incidents_opened": result["incidents_opened"],
            "emails_sent": result["emails_queued"],
        }

    submit_job(operation, job_id=job_id)
    return JobCreatedResponse(job_id=job_id)