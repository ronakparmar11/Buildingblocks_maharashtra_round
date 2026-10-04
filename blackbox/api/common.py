import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlmodel import Session

from blackbox.api.schemas import RunSummary
from blackbox.config import get_settings
from blackbox.store.models import Prediction, Run, Step, Task
from blackbox.store.repo import get_predictions, get_task

FIXTURE_DIR = Path(__file__).with_name("fixtures")
RUN_SUMMARY_FIELDS = {
    "run_id",
    "task_id",
    "origin",
    "outcome",
    "score_f1",
    "n_steps",
    "created_at",
    "parent_run_id",
}


def mock_mode() -> bool:
    return bool(get_settings().BLACKBOX_MOCK_API)


@lru_cache
def load_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def fixture_run_summary(run_data: dict[str, Any] | None = None) -> RunSummary:
    sample = load_fixture("sample_run.json")
    run = dict(sample["run"])
    if run_data:
        run.update(run_data)
    diagnosis = load_fixture("mock_api.json")["diagnosis"]
    top = diagnosis["ranking"][0]
    return RunSummary(
        **{key: run[key] for key in RUN_SUMMARY_FIELDS},
        question=sample["task"]["question"],
        predicted_culprit={"step_key": top["step_key"], "score": top["score"]},
    )


def run_summary(
    session: Session,
    run: Run,
    task: Task | None = None,
    predictions: list[Prediction] | None = None,
) -> RunSummary:
    task = task or get_task(session, run.task_id)
    if task is None:
        raise ValueError(f"Task not found for run: {run.run_id}")
    predictions = (
        predictions
        if predictions is not None
        else get_predictions(session, run.run_id)
    )
    culprit = None
    if predictions:
        culprit = {
            "step_key": predictions[0].step_key,
            "score": predictions[0].score,
        }
    return RunSummary(
        **{
            key: value
            for key, value in run.model_dump().items()
            if key in RUN_SUMMARY_FIELDS
        },
        question=task.question,
        predicted_culprit=culprit,
    )


def edges_for_steps(steps: list[Step] | list[dict[str, Any]]) -> list[dict[str, str]]:
    edges: list[dict[str, str]] = []
    for step in steps:
        target = step.step_key if isinstance(step, Step) else str(step["step_key"])
        dependencies = step.deps if isinstance(step, Step) else step.get("deps", [])
        edges.extend(
            {"source": str(source), "target": target} for source in dependencies
        )
    return edges