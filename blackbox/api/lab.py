from uuid import uuid4

from fastapi import APIRouter, HTTPException

from blackbox.api.common import load_fixture, mock_mode
from blackbox.api.replay import submit_job
from blackbox.api.schemas import (
    FaultTargetsResponse,
    LiveRunRequest,
    LiveRunResponse,
    TaskListResponse,
)
from blackbox.config import get_settings
from blackbox.store.db import get_session
from blackbox.store.models import Task
from blackbox.store.repo import list_tasks

router = APIRouter()


@router.get("/tasks", response_model=TaskListResponse)
def get_tasks(split: str = "test", q: str = "") -> TaskListResponse:
    if mock_mode():
        task = load_fixture("sample_run.json")["task"]
        items = (
            [task]
            if split == task["split"]
            and q.casefold() in task["question"].casefold()
            else []
        )
        return TaskListResponse(items)
    with get_session() as session:
        tasks = list_tasks(session, split=split)
        if q:
            tasks = [
                task for task in tasks if q.casefold() in task.question.casefold()
            ]
        return TaskListResponse.model_validate(tasks)


@router.get("/tasks/{task_id}/fault-targets", response_model=FaultTargetsResponse)
def get_fault_targets(task_id: str) -> FaultTargetsResponse:
    if mock_mode():
        sample = load_fixture("sample_run.json")
        if task_id != sample["task"]["task_id"]:
            raise HTTPException(status_code=404, detail="Task not found")
        return FaultTargetsResponse(
            targets=[
                {
                    "fault_type": sample["fault"]["fault_type"],
                    "step_key": sample["fault"]["step_key"],
                },
                {
                    "fault_type": "DISTRACTOR_RETRIEVAL",
                    "step_key": "q1/retrieve#0",
                },
            ]
        )
    from blackbox.faults.targets import applicable_targets, latest_clean_run

    with get_session() as session:
        if session.get(Task, task_id) is None:
            raise HTTPException(status_code=404, detail="Task not found")
        clean_run = latest_clean_run(session, task_id)
        if clean_run is None:
            return FaultTargetsResponse(targets=[])
        return FaultTargetsResponse(
            targets=[
                {"fault_type": fault_type, "step_key": step_key}
                for fault_type, step_key in applicable_targets(clean_run)
            ]
        )


@router.post("/live/run", response_model=LiveRunResponse)
def start_live_run(request: LiveRunRequest) -> LiveRunResponse:
    if mock_mode():
        run_id = "r_demo_live"
        submit_job(lambda: {"run_id": run_id}, job_id=run_id)
        return LiveRunResponse(run_id=run_id)

    with get_session() as session:
        task = session.get(Task, request.task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")

    if request.fault is None:
        run_id = uuid4().hex
        submit_job(lambda: _run_clean(request.task_id, run_id), job_id=run_id)
        return LiveRunResponse(run_id=run_id)

    run_id = uuid4().hex
    submit_job(
        lambda: _run_fault(
            request.task_id,
            request.fault.fault_type,
            request.fault.step_key,
            run_id,
        ),
        job_id=run_id,
    )
    return LiveRunResponse(run_id=run_id)


def _run_fault(
    task_id: str, fault_type: str, step_key: str, run_id: str
) -> dict[str, str]:
    from blackbox.faults.inject import run_with_fault

    with get_session() as session:
        task = session.get(Task, task_id)
        if task is None:
            raise ValueError(f"Unknown task id: {task_id}")
        run_with_fault(
            task,
            fault_type,
            step_key,
            get_settings().SEED,
            run_id,
        )
    return {"run_id": run_id}


def _run_clean(task_id: str, run_id: str) -> dict[str, str]:
    from blackbox.agent.agent import run_agent
    from blackbox.corpus.retriever import get_retriever
    from blackbox.replay.engine import _llm_client
    from blackbox.sdk.cassette import Cassette
    from blackbox.sdk.context import ExecutionContext
    from blackbox.sdk.tracer import Tracer

    with get_session() as session:
        task = session.get(Task, task_id)
        if task is None:
            raise ValueError(f"Unknown task id: {task_id}")
        context = ExecutionContext(
            run_id=run_id,
            task=task,
            origin="live",
            demo_mode=bool(get_settings().BLACKBOX_DEMO_MODE),
            tracer=Tracer(session, Cassette(session), llm=_llm_client()),
            retriever=get_retriever(),
        )
        run_agent(task, context)
        return {"run_id": run_id}