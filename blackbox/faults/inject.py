from typing import Any
from uuid import uuid4

from sqlmodel import Session

from blackbox.agent.agent import run_agent
from blackbox.config import get_settings
from blackbox.corpus.retriever import Retriever, get_retriever
from blackbox.faults.library import (
    BAD_QUERY,
    DISTRACTOR_RETRIEVAL,
    FAULT_TYPES,
    HALLUCINATED_SYNTHESIS,
    PLAN_CORRUPT,
    WRONG_EXTRACTION,
)
from blackbox.faults.targets import applicable_targets, latest_clean_run
from blackbox.llm.base import LLMClient
from blackbox.llm.gemini import GeminiLLM
from blackbox.llm.groq import GroqLLM
from blackbox.sdk.cassette import Cassette
from blackbox.sdk.context import ExecutionContext, Override
from blackbox.sdk.tracer import Tracer
from blackbox.store.db import get_session, init_db
from blackbox.store.models import Fault, Run, Step, Task
from blackbox.store.repo import get_steps, save_fault


def _llm_client() -> LLMClient:
    settings = get_settings()
    if settings.LLM_PROVIDER == "gemini":
        return GeminiLLM()
    if settings.LLM_PROVIDER == "groq":
        return GroqLLM()
    raise ValueError("LLM_PROVIDER=fake is only supported in tests")


def _distractors(task: Task, retriever: Retriever) -> list[dict[str, str]]:
    return [
        passage
        for pid in task.distractor_pids
        if (passage := retriever.get_passage(pid)) is not None
    ]


def _fault_params(
    task: Task,
    fault_type: str,
    target: Step,
    clean_steps: list[Step],
    retriever: Retriever,
    seed: int,
) -> dict[str, Any]:
    params: dict[str, Any] = {"seed": seed}
    by_key = {step.step_key: step for step in clean_steps}
    if fault_type in {PLAN_CORRUPT, BAD_QUERY, DISTRACTOR_RETRIEVAL}:
        params["distractors"] = _distractors(task, retriever)
    if fault_type == BAD_QUERY:
        extract_dependency = next(
            (dependency for dependency in target.deps if "/extract#" in dependency),
            None,
        )
        if extract_dependency is not None and extract_dependency in by_key:
            params["entity"] = str(by_key[extract_dependency].output.get("answer", ""))
    if fault_type == WRONG_EXTRACTION:
        retrieve_key = f"{target.node_id}/retrieve#{target.attempt}"
        retrieve = by_key.get(retrieve_key)
        if retrieve is not None:
            params["alternatives"] = [
                str(passage.get("title", ""))
                for passage in retrieve.output.get("passages", [])
                if isinstance(passage, dict) and passage.get("title")
            ]
    if fault_type == HALLUCINATED_SYNTHESIS:
        params["subanswers"] = target.input.get("subanswers", {})
    return params


def _execute_fault(
    session: Session,
    task: Task,
    fault_type: str,
    step_key: str,
    seed: int,
    llm: LLMClient,
    retriever: Retriever,
    run_id: str | None = None,
) -> Run:
    if fault_type not in FAULT_TYPES:
        raise ValueError(f"Unknown fault type: {fault_type}")
    clean_run = latest_clean_run(session, task.task_id)
    if clean_run is None:
        raise ValueError(f"Task has no passing clean run: {task.task_id}")
    if (fault_type, step_key) not in applicable_targets(clean_run):
        raise ValueError(f"Fault {fault_type} is not applicable to {step_key}")

    clean_steps = get_steps(session, clean_run.run_id)
    target = next(step for step in clean_steps if step.step_key == step_key)
    fault_params = _fault_params(task, fault_type, target, clean_steps, retriever, seed)
    tracer = Tracer(session, Cassette(session), llm=llm)
    context = ExecutionContext(
        run_id=run_id or uuid4().hex,
        task=task,
        origin="fault",
        overrides={
            step_key: Override(
                kind="fault",
                fault_type=fault_type,
                fault_params=fault_params,
            )
        },
        demo_mode=bool(get_settings().BLACKBOX_DEMO_MODE),
        tracer=tracer,
        retriever=retriever,
    )
    run = run_agent(task, context)
    save_fault(
        session,
        Fault(
            run_id=run.run_id,
            fault_type=fault_type,
            step_key=step_key,
            params=dict(context.overrides[step_key].fault_params),
        ),
    )
    session.refresh(run)
    return run


def run_with_fault(
    task: Task,
    fault_type: str,
    step_key: str,
    seed: int,
    run_id: str | None = None,
) -> Run:
    init_db()
    with get_session() as session:
        stored_task = session.get(Task, task.task_id)
        if stored_task is None:
            raise ValueError(f"Unknown task id: {task.task_id}")
        return _execute_fault(
            session,
            stored_task,
            fault_type,
            step_key,
            seed,
            _llm_client(),
            get_retriever(stored_task.workspace),
            run_id,
        )
