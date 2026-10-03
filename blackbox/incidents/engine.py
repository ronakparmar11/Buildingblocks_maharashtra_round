from __future__ import annotations

import json
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlmodel import Session, select

from blackbox.config import get_settings
from blackbox.model.predict import diagnose
from blackbox.sdk.context import Override
from blackbox.store.db import get_session, init_db
from blackbox.store.models import (
    Incident,
    IncidentEvent,
    NotificationRule,
    Prediction,
    Run,
    Step,
    Task,
)

Diagnosis = dict[str, Any]
ReplayFn = Callable[..., Run]

PATTERNS = {
    "retrieve": "answer not found in the help article",
    "extract": "answer not found in the help article",
    "synthesize": "final reply doesn't match the facts found",
    "plan": "plan missed part of the question",
}


def _ranking(diagnosis: Diagnosis) -> dict[str, Any]:
    ranking = diagnosis.get("ranking", [])
    if not isinstance(ranking, list) or not ranking:
        raise ValueError("Diagnosis has no ranked steps")
    top = ranking[0]
    if not isinstance(top, dict):
        raise TypeError("Diagnosis rank 1 is invalid")
    return top


def _top_reason_feature(top: dict[str, Any]) -> str:
    reasons = top.get("reasons", [])
    if isinstance(reasons, list) and reasons and isinstance(reasons[0], dict):
        return str(reasons[0].get("feature", "unknown"))
    return "unknown"


def _step_for_top(session: Session, run_id: str, top: dict[str, Any]) -> Step:
    step = session.exec(
        select(Step).where(
            Step.run_id == run_id,
            Step.step_key == str(top.get("step_key", "")),
        )
    ).first()
    if step is None:
        raise ValueError(f"Diagnosis step not found for run: {run_id}")
    return step


def group_key(run: Run, diagnosis: Diagnosis, session: Session) -> tuple[str, ...]:
    task = session.get(Task, run.task_id)
    if task is None:
        raise ValueError(f"Task not found for run: {run.run_id}")
    top = _ranking(diagnosis)
    step = _step_for_top(session, run.run_id, top)
    return (
        run.workspace,
        task.category or "uncategorized",
        step.name,
        _top_reason_feature(top),
    )


def _is_archived_retrieval(step: Step) -> bool:
    passages = step.output.get("passages", [])
    return bool(
        isinstance(passages, list)
        and passages
        and isinstance(passages[0], dict)
        and passages[0].get("status") == "archived"
    )


def _title(category: str, step: Step) -> str:
    pattern = (
        "search returned an archived policy"
        if step.name == "retrieve" and _is_archived_retrieval(step)
        else PATTERNS.get(step.name, "agent step did not match the policy")
    )
    return f"{category.capitalize()} questions answered wrong — {pattern}"


def _cost_per_wrong_answer(session: Session, workspace: str) -> int:
    settings_row = session.exec(
        select(NotificationRule).where(
            NotificationRule.workspace == workspace,
            NotificationRule.kind == "settings",
        )
    ).first()
    if settings_row is not None:
        value = settings_row.params.get("cost_per_wrong_answer_inr")
        if isinstance(value, int) and value >= 0:
            return value
    return get_settings().COST_PER_WRONG_ANSWER_INR


def _severity(n_runs: int, est_cost_inr: int) -> str:
    if n_runs >= 10 or est_cost_inr >= 5_000:
        return "high"
    if n_runs >= 3:
        return "medium"
    return "low"


def _event(
    session: Session,
    incident_id: str,
    kind: str,
    text: str,
    meta: dict[str, Any] | None = None,
) -> None:
    session.add(
        IncidentEvent(
            incident_id=incident_id,
            kind=kind,
            text=text,
            meta=meta or {},
        )
    )


def _stored_diagnosis(session: Session, run_id: str) -> Diagnosis | None:
    predictions = list(
        session.exec(
            select(Prediction)
            .where(Prediction.run_id == run_id)
            .order_by(Prediction.rank)
        ).all()
    )
    if not predictions:
        return None
    return {
        "ranking": [
            {
                "step_key": prediction.step_key,
                "score": prediction.score,
                "rank": prediction.rank,
                "reasons": prediction.reasons,
            }
            for prediction in predictions
        ]
    }


def assign_incident(
    run_id: str,
    diagnosis: Diagnosis | None = None,
    *,
    session: Session | None = None,
) -> Incident:
    if session is None:
        init_db()
        with get_session() as managed_session:
            return assign_incident(run_id, diagnosis, session=managed_session)

    run = session.get(Run, run_id)
    if run is None:
        raise ValueError(f"Unknown run id: {run_id}")
    diagnosis = diagnosis or _stored_diagnosis(session, run_id)
    if diagnosis is None:
        diagnosis = diagnose(run_id)
    task = session.get(Task, run.task_id)
    if task is None:
        raise ValueError(f"Task not found for run: {run_id}")
    top = _ranking(diagnosis)
    step = _step_for_top(session, run_id, top)
    key_tuple = group_key(run, diagnosis, session)
    key = json.dumps(key_tuple, separators=(",", ":"))
    now = datetime.now(UTC)
    incident = session.exec(
        select(Incident)
        .where(
            Incident.workspace == run.workspace,
            Incident.group_key == key,
            Incident.status.in_(("open", "investigating", "fix_verified", "reopened")),
            Incident.last_seen >= now - timedelta(days=7),
        )
        .order_by(Incident.last_seen.desc())
    ).first()
    score = float(top.get("score", 0.0))
    if incident is None:
        incident = Incident(
            workspace=run.workspace,
            group_key=key,
            title=_title(task.category or "Support", step),
            category=task.category or "uncategorized",
            cause_step_name=step.name,
            cause_feature=_top_reason_feature(top),
            severity="low",
            status="open",
            owner="",
            est_cost_inr=_cost_per_wrong_answer(session, run.workspace),
            n_runs=1,
            representative_run_id=run.run_id,
            first_seen=now,
            last_seen=now,
        )
        session.add(incident)
        session.flush()
        _event(session, incident.incident_id, "opened", "Incident opened.")
    else:
        incident.n_runs += 1
        incident.last_seen = now
        _event(
            session,
            incident.incident_id,
            "conversation_added",
            "Conversation added to this incident.",
            {"run_id": run.run_id},
        )
        representative = _stored_diagnosis(session, incident.representative_run_id)
        representative_score = (
            float(_ranking(representative).get("score", 0.0))
            if representative is not None
            else -1.0
        )
        if score > representative_score:
            incident.representative_run_id = run.run_id

    incident.est_cost_inr = incident.n_runs * _cost_per_wrong_answer(
        session, run.workspace
    )
    incident.severity = _severity(incident.n_runs, incident.est_cost_inr)
    run.incident_id = incident.incident_id
    session.add_all((incident, run))
    session.commit()
    session.refresh(incident)
    return incident


def explain_incident(incident: Incident, session: Session | None = None) -> str:
    if session is None:
        with get_session() as managed_session:
            stored = managed_session.get(Incident, incident.incident_id)
            if stored is None:
                raise ValueError(f"Unknown incident id: {incident.incident_id}")
            return explain_incident(stored, managed_session)
    run = session.get(Run, incident.representative_run_id)
    if run is None:
        raise ValueError("Representative conversation is missing")
    task = session.get(Task, run.task_id)
    if task is None:
        raise ValueError("Representative support question is missing")
    step = session.exec(
        select(Step).where(
            Step.run_id == run.run_id, Step.name == incident.cause_step_name
        )
    ).first()
    article_note = ""
    if step is not None and _is_archived_retrieval(step):
        top_article = step.output["passages"][0]
        article_note = f" The search used archived article ‘{top_article['title']}’."
    return (
        f"Customer asked “{task.question}” and received “{run.final_answer or ''}” "
        f"instead of “{task.gold_answer}”. The likely cause was "
        f"{incident.cause_step_name}.{article_note}"
    )


ALLOWED_TRANSITIONS = {
    "open": {"investigating", "resolved"},
    "reopened": {"investigating", "resolved"},
    "investigating": {"fix_verified", "resolved"},
    "fix_verified": {"resolved"},
    "resolved": {"reopened"},
}


def transition_status(
    incident_id: str, status: str, *, session: Session | None = None
) -> Incident:
    if session is None:
        with get_session() as managed_session:
            return transition_status(incident_id, status, session=managed_session)
    incident = session.get(Incident, incident_id)
    if incident is None:
        raise ValueError(f"Unknown incident id: {incident_id}")
    if status not in ALLOWED_TRANSITIONS.get(incident.status, set()):
        raise ValueError(f"Cannot change incident from {incident.status} to {status}")
    incident.status = status
    incident.resolved_at = datetime.now(UTC) if status == "resolved" else None
    kind = "reopened" if status == "reopened" else "status_changed"
    _event(session, incident_id, kind, f"Status changed to {status}.")
    session.add(incident)
    session.commit()
    session.refresh(incident)
    return incident


def _override_from_spec(raw: dict[str, Any]) -> Override:
    return Override(
        kind=raw["kind"],
        output=raw.get("output"),
        params=dict(raw.get("params", {})),
        fault_type=raw.get("fault_type"),
        fault_params=dict(raw.get("fault_params", {})),
    )


def verify_fix(
    incident_id: str,
    repair_run_id: str,
    *,
    replay_fn: ReplayFn | None = None,
) -> dict[str, Any]:
    from blackbox.replay.engine import replay

    replay_fn = replay_fn or replay
    with get_session() as session:
        incident = session.get(Incident, incident_id)
        repair_run = session.get(Run, repair_run_id)
        if incident is None or repair_run is None:
            raise ValueError("Incident or repair run not found")
        overrides = (repair_run.replay_spec or {}).get("overrides", {})
        if not isinstance(overrides, dict) or not overrides:
            raise ValueError("Repair run has no winning strategy override")
        source_key, raw_override = next(iter(overrides.items()))
        if not isinstance(raw_override, dict):
            raise TypeError("Repair override is invalid")
        source_step = session.exec(
            select(Step).where(
                Step.run_id == repair_run.run_id, Step.step_key == source_key
            )
        ).first()
        if source_step is None:
            raise ValueError("Repair step is missing")
        affected_ids = list(
            session.exec(
                select(Run.run_id).where(
                    Run.incident_id == incident_id,
                    Run.outcome == "fail",
                )
            ).all()
        )
        targets: list[tuple[str, str]] = []
        for run_id in affected_ids:
            target = session.exec(
                select(Step)
                .where(Step.run_id == run_id, Step.name == source_step.name)
                .order_by(Step.idx)
            ).first()
            if target is not None:
                targets.append((run_id, target.step_key))
        _event(
            session,
            incident_id,
            "fix_tried",
            f"Verifying fix on {len(targets)} conversations.",
        )
        session.commit()

    def apply(target: tuple[str, str]) -> Run:
        run_id, step_key = target
        return replay_fn(
            run_id,
            overrides={step_key: _override_from_spec(raw_override)},
            origin="repair",
        )

    with ThreadPoolExecutor(max_workers=min(4, max(1, len(targets)))) as executor:
        replay_runs = list(executor.map(apply, targets))
    n_passed = sum(run.outcome == "pass" for run in replay_runs)
    result = {
        "n_total": len(replay_runs),
        "n_passed": n_passed,
        "run_ids": [run.run_id for run in replay_runs],
        "tokens_saved": sum(run.tokens_saved for run in replay_runs),
    }
    with get_session() as session:
        incident = session.get(Incident, incident_id)
        assert incident is not None
        incident.verified_strategy = raw_override
        incident.verify_result = result
        if replay_runs and n_passed / len(replay_runs) >= 0.8:
            incident.status = "fix_verified"
            _event(
                session,
                incident_id,
                "fix_verified",
                f"Fix verified on {n_passed} of {len(replay_runs)} conversations.",
            )
        session.add(incident)
        session.commit()
    return result


def on_run_finished(
    run: Run,
    *,
    diagnose_fn: Callable[[str], Diagnosis] = diagnose,
    assign_fn: Callable[..., Incident] = assign_incident,
) -> Incident | None:
    if run.origin not in {"live", "simulated"} or run.workspace == "hotpot":
        return None
    if run.outcome != "fail":
        return None
    diagnosis = diagnose_fn(run.run_id)
    incident = assign_fn(run.run_id, diagnosis)
    from blackbox.notify.rules import evaluate_rules

    evaluate_rules(incident)
    return incident