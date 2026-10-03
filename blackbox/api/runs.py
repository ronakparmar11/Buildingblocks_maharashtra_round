from fastapi import APIRouter, HTTPException, Query
from sqlmodel import col, select

from blackbox.api.common import (
    edges_for_steps,
    fixture_run_summary,
    load_fixture,
    mock_mode,
    run_summary,
)
from blackbox.api.schemas import (
    DiagnosisResponse,
    RunDetailResponse,
    RunListResponse,
)
from blackbox.store.db import get_session
from blackbox.store.models import Prediction, Run, Task
from blackbox.store.repo import get_fault, get_label, get_predictions, get_steps

router = APIRouter()


@router.get("/runs", response_model=RunListResponse)
def list_run_records(
    outcome: str | None = None,
    origin: str | None = None,
    split: str | None = None,
    fault_type: str | None = None,
    q: str = "",
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> RunListResponse:
    if mock_mode():
        sample = load_fixture("sample_run.json")
        matches = (
            (outcome is None or outcome == sample["run"]["outcome"])
            and (origin is None or origin == sample["run"]["origin"])
            and (split is None or split == sample["task"]["split"])
            and (fault_type is None or fault_type == sample["fault"]["fault_type"])
            and (not q or q.casefold() in sample["task"]["question"].casefold())
        )
        items = [fixture_run_summary()] if matches and offset == 0 else []
        return RunListResponse(items=items[:limit], total=int(matches))

    with get_session() as session:
        runs = list(session.exec(select(Run).order_by(col(Run.created_at).desc())).all())
        matched: list[Run] = []
        for run in runs:
            task = session.get(Task, run.task_id)
            fault = get_fault(session, run.run_id)
            if task is None:
                continue
            if outcome is not None and run.outcome != outcome:
                continue
            if origin is not None and run.origin != origin:
                continue
            if split is not None and task.split != split:
                continue
            if fault_type is not None and (
                fault is None or fault.fault_type != fault_type
            ):
                continue
            if q and q.casefold() not in task.question.casefold():
                continue
            matched.append(run)
        return RunListResponse(
            items=[run_summary(session, run) for run in matched[offset : offset + limit]],
            total=len(matched),
        )


@router.get("/runs/{run_id}", response_model=RunDetailResponse)
def get_run_detail(run_id: str) -> RunDetailResponse:
    if mock_mode():
        sample = load_fixture("sample_run.json")
        if run_id != sample["run"]["run_id"]:
            raise HTTPException(status_code=404, detail="Run not found")
        return RunDetailResponse.model_validate(sample)

    with get_session() as session:
        run = session.get(Run, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        task = session.get(Task, run.task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        steps = get_steps(session, run_id)
        return RunDetailResponse(
            run=run,
            task=task,
            steps=steps,
            edges=edges_for_steps(steps),
            fault=get_fault(session, run_id),
            label=get_label(session, run_id),
        )


@router.get("/runs/{run_id}/diagnosis", response_model=DiagnosisResponse)
def get_diagnosis(run_id: str) -> DiagnosisResponse:
    if mock_mode():
        sample = load_fixture("sample_run.json")
        if run_id != sample["run"]["run_id"]:
            raise HTTPException(status_code=404, detail="Run not found")
        return DiagnosisResponse.model_validate(
            load_fixture("mock_api.json")["diagnosis"]
        )

    with get_session() as session:
        if session.get(Run, run_id) is None:
            raise HTTPException(status_code=404, detail="Run not found")
        predictions = get_predictions(session, run_id)
        if predictions:
            return _cached_diagnosis(run_id, predictions)
    from blackbox.model.predict import diagnose

    try:
        return DiagnosisResponse.model_validate(diagnose(run_id))
    except (OSError, ValueError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


def _cached_diagnosis(
    run_id: str, predictions: list[Prediction]
) -> DiagnosisResponse:
    return DiagnosisResponse(
        run_id=run_id,
        model_version=predictions[0].model_version,
        latency_ms=0.0,
        ranking=[
            {
                "step_key": prediction.step_key,
                "score": prediction.score,
                "rank": prediction.rank,
                "reasons": prediction.reasons,
            }
            for prediction in predictions
        ],
    )