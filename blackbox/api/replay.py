from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import asdict, dataclass
from threading import Lock
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from blackbox.api.common import (
    fixture_run_summary,
    load_fixture,
    mock_mode,
    run_summary,
)
from blackbox.api.schemas import (
    BlastRadiusResponse,
    JobCreatedResponse,
    JobResponse,
    RepairRequest,
    RepairResponse,
    ReplayRequest,
    ReplayResponse,
    ReplayStats,
)
from blackbox.sdk.context import Override
from blackbox.store.db import get_session
from blackbox.store.models import Run

router = APIRouter()


def _require_workspace(run_id: str, workspace: str) -> None:
    if mock_mode():
        sample = load_fixture("sample_run.json")
        if workspace != "hotpot" or run_id != sample["run"]["run_id"]:
            raise HTTPException(status_code=404, detail="Run not found")
        return
    with get_session() as session:
        run = session.get(Run, run_id)
        if run is None or run.workspace != workspace:
            raise HTTPException(status_code=404, detail="Run not found")


@dataclass
class JobState:
    status: str = "queued"
    progress: float = 0.0
    result: dict[str, Any] | None = None


_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="blackbox-api")
_jobs: dict[str, JobState] = {}
_futures: dict[str, Future[dict[str, Any]]] = {}
_jobs_lock = Lock()


def submit_job(
    operation: Callable[[], dict[str, Any]], *, job_id: str | None = None
) -> str:
    job_id = job_id or uuid4().hex
    with _jobs_lock:
        _jobs[job_id] = JobState()

    def execute() -> dict[str, Any]:
        with _jobs_lock:
            _jobs[job_id] = JobState(status="running", progress=0.1)
        try:
            result = operation()
        except Exception as error:
            with _jobs_lock:
                _jobs[job_id] = JobState(
                    status="failed", progress=1.0, result={"error": str(error)}
                )
            raise
        with _jobs_lock:
            _jobs[job_id] = JobState(
                status="completed", progress=1.0, result=result
            )
        return result

    _futures[job_id] = _executor.submit(execute)
    return job_id


def wait_for_job(job_id: str) -> dict[str, Any]:
    return _futures[job_id].result()


def update_job(job_id: str, progress: float, result: dict[str, Any]) -> None:
    with _jobs_lock:
        state = _jobs.get(job_id)
        if state is None or state.status not in {"queued", "running"}:
            return
        _jobs[job_id] = JobState(
            status="running",
            progress=max(0.0, min(progress, 0.99)),
            result=result,
        )


@router.post("/runs/{run_id}/replay", response_model=ReplayResponse)
def replay_run(
    run_id: str, request: ReplayRequest, workspace: str = "hotpot"
) -> ReplayResponse:
    _require_workspace(run_id, workspace)
    if mock_mode():
        sample = load_fixture("sample_run.json")
        if run_id != sample["run"]["run_id"]:
            raise HTTPException(status_code=404, detail="Run not found")
        replay_data = load_fixture("mock_api.json")["replay"]
        return ReplayResponse(
            run=fixture_run_summary(
                {
                    "run_id": replay_data["run_id"],
                    "origin": "replay",
                    "parent_run_id": run_id,
                    "outcome": replay_data["outcome"],
                    "score_f1": replay_data["score_f1"],
                }
            ),
            stats=ReplayStats(
                n_reused=replay_data["n_reused"],
                n_executed=replay_data["n_executed"],
                tokens_saved=replay_data["tokens_saved"],
                tokens_total=replay_data["tokens_total"],
                latency_ms=replay_data["latency_ms"],
            ),
            compare_url=f"/api/compare?a={run_id}&b={replay_data['run_id']}",
        )

    from blackbox.replay.engine import replay

    overrides = {
        key: Override(**value.model_dump()) for key, value in request.overrides.items()
    }
    try:
        replayed = replay(run_id, overrides, request.freeze_before_idx)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    with get_session() as session:
        stored = session.get(Run, replayed.run_id)
        if stored is None:
            raise HTTPException(status_code=500, detail="Replay was not persisted")
        return ReplayResponse(
            run=run_summary(session, stored),
            stats=ReplayStats(
                n_reused=stored.n_reused,
                n_executed=stored.n_executed,
                tokens_saved=stored.tokens_saved,
                tokens_total=stored.tokens_total,
                latency_ms=stored.latency_ms,
            ),
            compare_url=f"/api/compare?a={run_id}&b={stored.run_id}",
        )


@router.get("/runs/{run_id}/blast-radius", response_model=BlastRadiusResponse)
def get_blast_radius(
    run_id: str, step_key: str, workspace: str = "hotpot"
) -> BlastRadiusResponse:
    _require_workspace(run_id, workspace)
    if mock_mode():
        sample = load_fixture("sample_run.json")
        keys = [step["step_key"] for step in sample["steps"]]
        if run_id != sample["run"]["run_id"] or step_key not in keys:
            raise HTTPException(status_code=404, detail="Run or step not found")
        start = keys.index(step_key)
        return BlastRadiusResponse(step_key=step_key, affected=keys[start + 1 :])
    from blackbox.replay.graph import blast_radius

    try:
        return BlastRadiusResponse(
            step_key=step_key, affected=blast_radius(run_id, step_key)
        )
    except (KeyError, ValueError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


def _repair_payload(run_id: str, top_k: int) -> dict[str, Any]:
    if mock_mode():
        return dict(load_fixture("mock_api.json")["repair"])
    from blackbox.repair.repair import repair

    result = repair(run_id, top_k=top_k)
    return {
        "attempts": [asdict(attempt) for attempt in result.attempts],
        "repaired": result.repaired,
        "winning_run_id": result.winning_run_id,
    }


@router.post("/runs/{run_id}/repair", response_model=RepairResponse)
def repair_run(
    run_id: str, request: RepairRequest, workspace: str = "hotpot"
) -> RepairResponse:
    _require_workspace(run_id, workspace)
    try:
        return RepairResponse.model_validate(_repair_payload(run_id, request.top_k))
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/runs/{run_id}/repair/jobs", response_model=JobCreatedResponse)
def repair_run_job(
    run_id: str, request: RepairRequest, workspace: str = "hotpot"
) -> JobCreatedResponse:
    _require_workspace(run_id, workspace)
    return JobCreatedResponse(
        job_id=submit_job(lambda: _repair_payload(run_id, request.top_k))
    )


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, workspace: str = "hotpot") -> JobResponse:
    del workspace
    with _jobs_lock:
        state = _jobs.get(job_id)
        if state is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return JobResponse.model_validate(asdict(state))