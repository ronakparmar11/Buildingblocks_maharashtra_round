from collections import Counter

from fastapi import APIRouter
from sqlmodel import select

from blackbox.api.common import load_fixture, mock_mode
from blackbox.api.schemas import FleetResponse
from blackbox.store.db import get_session
from blackbox.store.models import Fault, Prediction, Run, Step, Task

router = APIRouter()


@router.get("/fleet", response_model=FleetResponse)
def get_fleet(split: str = "test") -> FleetResponse:
    if mock_mode():
        return FleetResponse.model_validate(load_fixture("mock_api.json")["fleet"])

    with get_session() as session:
        tasks = {
            task.task_id
            for task in session.exec(select(Task).where(Task.split == split)).all()
        }
        failed = [
            run
            for run in session.exec(select(Run).where(Run.outcome == "fail")).all()
            if run.task_id in tasks
        ]
        run_ids = {run.run_id for run in failed}
        predictions = [
            prediction
            for prediction in session.exec(select(Prediction)).all()
            if prediction.run_id in run_ids
        ]
        steps = {
            (step.run_id, step.step_key): step
            for step in session.exec(select(Step)).all()
            if step.run_id in run_ids
        }
        top_predictions = [item for item in predictions if item.rank == 1]
        step_counts = Counter(
            steps[(item.run_id, item.step_key)].name
            for item in top_predictions
            if (item.run_id, item.step_key) in steps
        )
        reason_counts = Counter(
            (str(reason.get("feature", "")), str(reason.get("text", "")))
            for item in top_predictions
            for reason in item.reasons
        )
        faults = [
            fault
            for fault in session.exec(select(Fault)).all()
            if fault.run_id in run_ids
        ]
        fault_counts = Counter(fault.fault_type for fault in faults)
        total = len(failed)
        return FleetResponse(
            by_step_name=[
                {"name": name, "count": count, "pct": count / total if total else 0.0}
                for name, count in step_counts.most_common()
            ],
            by_reason=[
                {"feature": feature, "text": text, "count": count}
                for (feature, text), count in reason_counts.most_common()
            ],
            by_fault_type=[
                {
                    "fault_type": fault_type,
                    "count": count,
                    "pct": count / total if total else 0.0,
                }
                for fault_type, count in fault_counts.most_common()
            ],
            total_failed=total,
        )