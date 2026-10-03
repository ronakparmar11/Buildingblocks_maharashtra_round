from typing import Any

from sqlmodel import Session, col, delete, select

from blackbox.store.models import Fault, Label, Prediction, Run, Step, Task


def upsert_task(session: Session, task: Task) -> Task:
    stored = session.merge(task)
    session.commit()
    session.refresh(stored)
    return stored


def get_task(session: Session, task_id: str) -> Task | None:
    return session.get(Task, task_id)


def list_tasks(
    session: Session, split: str | None = None, qtype: str | None = None
) -> list[Task]:
    statement = select(Task)
    if split is not None:
        statement = statement.where(Task.split == split)
    if qtype is not None:
        statement = statement.where(Task.qtype == qtype)
    return list(session.exec(statement.order_by(Task.task_id)).all())


def create_run(session: Session, run: Run) -> Run:
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def finish_run(session: Session, run_id: str, **updates: Any) -> Run:
    run = session.get(Run, run_id)
    if run is None:
        raise ValueError(f"Run not found: {run_id}")

    fields = set(Run.model_fields)
    unknown = set(updates) - fields
    if unknown:
        raise ValueError(f"Unknown run fields: {', '.join(sorted(unknown))}")
    for field, value in updates.items():
        setattr(run, field, value)

    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def add_step(session: Session, step: Step) -> Step:
    session.add(step)
    session.commit()
    session.refresh(step)
    return step


def get_run(session: Session, run_id: str) -> Run | None:
    return session.get(Run, run_id)


def get_steps(session: Session, run_id: str) -> list[Step]:
    statement = select(Step).where(Step.run_id == run_id).order_by(Step.idx)
    return list(session.exec(statement).all())


def list_runs(
    session: Session,
    filters: dict[str, Any] | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Run]:
    statement = select(Run)
    for field, value in (filters or {}).items():
        if field not in Run.model_fields:
            raise ValueError(f"Unknown run filter: {field}")
        statement = statement.where(getattr(Run, field) == value)
    statement = (
        statement.order_by(col(Run.created_at).desc()).offset(offset).limit(limit)
    )
    return list(session.exec(statement).all())


def save_fault(session: Session, fault: Fault) -> Fault:
    stored = session.merge(fault)
    session.commit()
    session.refresh(stored)
    return stored


def get_fault(session: Session, run_id: str) -> Fault | None:
    return session.get(Fault, run_id)


def save_label(session: Session, label: Label) -> Label:
    stored = session.merge(label)
    session.commit()
    session.refresh(stored)
    return stored


def get_label(session: Session, run_id: str) -> Label | None:
    return session.get(Label, run_id)


def save_predictions(
    session: Session, run_id: str, predictions: list[Prediction]
) -> list[Prediction]:
    if any(prediction.run_id != run_id for prediction in predictions):
        raise ValueError("All predictions must belong to the requested run")
    session.exec(delete(Prediction).where(Prediction.run_id == run_id))
    session.add_all(predictions)
    session.commit()
    for prediction in predictions:
        session.refresh(prediction)
    return predictions


def get_predictions(session: Session, run_id: str) -> list[Prediction]:
    statement = (
        select(Prediction).where(Prediction.run_id == run_id).order_by(Prediction.rank)
    )
    return list(session.exec(statement).all())
