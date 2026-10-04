from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import inspect
from sqlmodel import select

from blackbox.corpus.nimbu import build_nimbu_corpus
from blackbox.store import db
from blackbox.store.db import get_session, init_db
from blackbox.store.models import (
    Fault,
    Incident,
    IncidentEvent,
    Label,
    Prediction,
    Run,
    Step,
    Task,
)

DEMO_RUN_COUNT = 80


@dataclass(frozen=True)
class DemoSeedResult:
    created_runs: int
    created_incidents: int


INCIDENTS = (
    {
        "incident_id": "inc_refunds_archived",
        "title": "Refund questions answered wrong - search returned an archived policy",
        "category": "refunds",
        "cause_step_name": "retrieve",
        "cause_feature": "archived_policy",
        "severity": "high",
        "status": "open",
        "owner": "",
        "est_cost_inr": 6300,
        "step_key": "q1/retrieve#0",
        "reason": "An archived help article ranked above the current refund policy.",
    },
    {
        "incident_id": "inc_shipping_fee",
        "title": "Shipping fee answers wrong - pincode rule was missed",
        "category": "shipping",
        "cause_step_name": "extract",
        "cause_feature": "missing_exception",
        "severity": "medium",
        "status": "investigating",
        "owner": "Meera",
        "est_cost_inr": 2700,
        "step_key": "q1/extract#0",
        "reason": "The extraction omitted a location-specific shipping exception.",
    },
    {
        "incident_id": "inc_damage_exchange",
        "title": "Damaged item questions answered wrong - exception was omitted",
        "category": "returns",
        "cause_step_name": "synthesize",
        "cause_feature": "answer_support",
        "severity": "medium",
        "status": "open",
        "owner": "",
        "est_cost_inr": 1800,
        "step_key": "synthesize",
        "reason": "The final reply omitted the damaged-item exchange exception.",
    },
    {
        "incident_id": "inc_cod",
        "title": "Cash on delivery questions answered wrong - location check failed",
        "category": "payments",
        "cause_step_name": "check",
        "cause_feature": "location_check",
        "severity": "low",
        "status": "fix_verified",
        "owner": "Arjun",
        "est_cost_inr": 1350,
        "step_key": "check",
        "reason": "The validation step did not enforce the COD pincode rule.",
    },
)


def _tasks() -> list[Task]:
    with get_session() as session:
        tasks = list(
            session.exec(
                select(Task)
                .where(Task.workspace == "nimbu")
                .order_by(Task.task_id)
            ).all()
        )
    if tasks:
        return tasks
    build_nimbu_corpus()
    with get_session() as session:
        return list(
            session.exec(
                select(Task)
                .where(Task.workspace == "nimbu")
                .order_by(Task.task_id)
            ).all()
        )


def _task_for_incident(
    tasks: list[Task], category: str, fallback_index: int
) -> Task:
    matching = [task for task in tasks if task.category == category]
    return matching[fallback_index % len(matching)] if matching else tasks[fallback_index % len(tasks)]


def _steps(run: Run, task: Task, failed: bool) -> list[Step]:
    answer = "30 days" if failed else task.gold_answer
    policy_status = "archived" if failed else "current"
    definitions = (
        ("plan", "plan", [], "Identify the policy and applicable exceptions."),
        (
            "q1/retrieve#0",
            "retrieve",
            ["plan"],
            f"{task.gold_titles[0] if task.gold_titles else 'Support policy'} ({policy_status})",
        ),
        ("q1/extract#0", "extract", ["q1/retrieve#0"], answer),
        ("synthesize", "synthesize", ["q1/extract#0"], answer),
        ("check", "check", ["synthesize"], "unsupported" if failed else "supported"),
    )
    return [
        Step(
            step_id=f"{run.run_id}-step-{index}",
            run_id=run.run_id,
            step_key=step_key,
            idx=index,
            name=name,
            type="retrieval" if name == "retrieve" else "reasoning",
            node_id=step_key.split("/")[0],
            attempt=0,
            deps=deps,
            input={"question": task.question},
            input_hash=f"{run.run_id}-input-{index}",
            output={"text": output_text, "status": policy_status},
            output_hash=f"{run.run_id}-output-{index}",
            output_text=output_text,
            latency_ms=45 + index * 17,
            tokens_in=28 + index * 6,
            tokens_out=12 + index * 4,
            model="demo-fixture" if name in {"plan", "synthesize"} else None,
            cache_hit=index == 1 and not failed,
            reused=False,
            overridden=False,
            state_snapshot={"workspace": "nimbu", "demo": True},
            error=None,
            meta={"fixture": "nimbu-demo"},
        )
        for index, (step_key, name, deps, output_text) in enumerate(definitions)
    ]


def seed_nimbu_demo_data(run_count: int = DEMO_RUN_COUNT) -> DemoSeedResult:
    if not inspect(db.engine).has_table("run"):
        init_db()

    now = datetime.now(UTC)
    created_runs = 0
    failed_by_incident: dict[str, list[Run]] = defaultdict(list)

    with get_session() as session:
        demo_run_ids = {f"nimbu_demo_{index:03d}" for index in range(1, run_count + 1)}
        existing_runs = {
            run.run_id: run
            for run in session.exec(
                select(Run).where(Run.run_id.in_(demo_run_ids))
            ).all()
        }
        demo_incident_ids = {
            str(incident["incident_id"]) for incident in INCIDENTS
        }
        existing_incident_ids = set(
            session.exec(
                select(Incident.incident_id).where(
                    Incident.incident_id.in_(demo_incident_ids)
                )
            ).all()
        )
        if len(existing_runs) == run_count and existing_incident_ids == demo_incident_ids:
            return DemoSeedResult(created_runs=0, created_incidents=0)

        tasks = _tasks() if len(existing_runs) < run_count else []
        if len(existing_runs) < run_count and not tasks:
            raise RuntimeError("Nimbu tasks could not be loaded")

        for index in range(1, run_count + 1):
            run_id = f"nimbu_demo_{index:03d}"
            existing = existing_runs.get(run_id)
            if existing is not None:
                if existing.incident_id:
                    failed_by_incident[existing.incident_id].append(existing)
                continue

            failed = (index - 1) % 6 == 0
            incident = INCIDENTS[((index - 1) // 6) % len(INCIDENTS)] if failed else None
            task = (
                _task_for_incident(tasks, str(incident["category"]), index)
                if incident
                else tasks[(index - 1) % len(tasks)]
            )
            run = Run(
                run_id=run_id,
                task_id=task.task_id,
                workspace="nimbu",
                incident_id=str(incident["incident_id"]) if incident else None,
                origin="simulated" if index % 4 == 0 else "live",
                parent_run_id=None,
                final_answer=(
                    "This request is covered for 30 days."
                    if failed
                    else task.gold_answer
                ),
                outcome="fail" if failed else "pass",
                score_f1=0.08 if failed else 0.96,
                n_steps=5,
                n_reused=0,
                n_executed=5,
                tokens_total=318 + index,
                tokens_saved=42 if index % 5 == 0 else 0,
                latency_ms=620 + index * 3,
                created_at=now - timedelta(hours=index * 1.8),
                replay_spec=None,
            )
            session.add(run)
            session.flush()
            session.add_all(_steps(run, task, failed))
            if incident:
                failed_by_incident[str(incident["incident_id"])].append(run)
                session.add(
                    Fault(
                        run_id=run_id,
                        fault_type="historical_support_failure",
                        step_key=str(incident["step_key"]),
                        params={"fixture": "nimbu-demo"},
                    )
                )
                session.add(
                    Label(
                        run_id=run_id,
                        culprit_step_key=str(incident["step_key"]),
                        method="verified_replay",
                        verified=True,
                        confidence=0.92,
                        n_replays=3,
                        matches_injection=True,
                    )
                )
                session.add(
                    Prediction(
                        run_id=run_id,
                        step_key=str(incident["step_key"]),
                        score=0.91,
                        rank=1,
                        model_version="nimbu-demo-v1",
                        reasons=[
                            {
                                "feature": incident["cause_feature"],
                                "text": incident["reason"],
                                "evidence": task.question,
                                "contribution": 0.64,
                            }
                        ],
                    )
                )
            created_runs += 1

        created_incidents = 0
        for incident_data in INCIDENTS:
            incident_id = str(incident_data["incident_id"])
            related_runs = failed_by_incident[incident_id]
            if not related_runs or incident_id in existing_incident_ids:
                continue
            related_runs.sort(key=lambda run: run.created_at)
            session.add(
                Incident(
                    incident_id=incident_id,
                    workspace="nimbu",
                    group_key=f"{incident_data['category']}-{incident_data['cause_step_name']}",
                    title=str(incident_data["title"]),
                    category=str(incident_data["category"]),
                    cause_step_name=str(incident_data["cause_step_name"]),
                    cause_feature=str(incident_data["cause_feature"]),
                    severity=str(incident_data["severity"]),
                    status=str(incident_data["status"]),
                    owner=str(incident_data["owner"]),
                    est_cost_inr=int(incident_data["est_cost_inr"]),
                    n_runs=len(related_runs),
                    representative_run_id=related_runs[-1].run_id,
                    first_seen=related_runs[0].created_at,
                    last_seen=related_runs[-1].created_at,
                )
            )
            session.flush()
            session.add(
                IncidentEvent(
                    event_id=f"{incident_id}-detected",
                    incident_id=incident_id,
                    kind="opened",
                    text="Black Box grouped matching failed support conversations.",
                    created_at=related_runs[-1].created_at,
                    meta={"fixture": "nimbu-demo"},
                )
            )
            created_incidents += 1

        session.commit()

    return DemoSeedResult(
        created_runs=created_runs,
        created_incidents=created_incidents,
    )