import random
from collections.abc import Callable
from typing import Any
from uuid import uuid4

from sqlmodel import Session, select

from blackbox.agent.agent import run_agent
from blackbox.config import get_settings
from blackbox.corpus.retriever import Retriever, get_retriever
from blackbox.faults.inject import _execute_fault
from blackbox.faults.library import (
    BAD_QUERY,
    DISTRACTOR_RETRIEVAL,
    HALLUCINATED_SYNTHESIS,
    PLAN_CORRUPT,
    WRONG_EXTRACTION,
)
from blackbox.faults.targets import applicable_targets, latest_clean_run
from blackbox.incidents.engine import on_run_finished
from blackbox.llm.base import LLMClient
from blackbox.llm.gemini import GeminiLLM
from blackbox.llm.groq import GroqLLM
from blackbox.sdk.cassette import Cassette
from blackbox.sdk.context import ExecutionContext
from blackbox.sdk.tracer import Tracer
from blackbox.store.db import get_session, init_db
from blackbox.store.models import Incident, NotificationLog, Run, Task

ProgressFn = Callable[[dict[str, int]], None]
FAULT_WEIGHTS = {
    DISTRACTOR_RETRIEVAL: 0.5,
    WRONG_EXTRACTION: 0.2,
    PLAN_CORRUPT: 0.1,
    HALLUCINATED_SYNTHESIS: 0.1,
    BAD_QUERY: 0.1,
}


def _llm_client() -> LLMClient:
    settings = get_settings()
    if settings.LLM_PROVIDER == "gemini":
        return GeminiLLM()
    if settings.LLM_PROVIDER == "groq":
        return GroqLLM()
    raise ValueError("Simulator requires LLM_PROVIDER=gemini or groq")


def _run_clean(
    session: Session,
    task: Task,
    llm: LLMClient,
    retriever: Retriever,
    origin: str,
) -> Run:
    return run_agent(
        task,
        ExecutionContext(
            run_id=uuid4().hex,
            task=task,
            origin=origin,
            demo_mode=bool(get_settings().BLACKBOX_DEMO_MODE),
            tracer=Tracer(session, Cassette(session), llm=llm),
            retriever=retriever,
        ),
    )


def _weighted_target(
    clean_run: Run, randomizer: random.Random
) -> tuple[str, str] | None:
    targets = applicable_targets(clean_run)
    weighted = [
        (fault_type, step_key, FAULT_WEIGHTS[fault_type])
        for fault_type, step_key in targets
        if fault_type in FAULT_WEIGHTS
    ]
    if not weighted:
        return None
    chosen = randomizer.choices(
        weighted, weights=[item[2] for item in weighted], k=1
    )[0]
    return chosen[0], chosen[1]


def run_simulation(
    workspace: str = "nimbu",
    n: int = 30,
    failure_rate: float = 0.35,
    seed: int = 7,
    *,
    progress_fn: ProgressFn | None = None,
    llm: LLMClient | None = None,
    retriever: Retriever | None = None,
) -> dict[str, int]:
    if n < 1:
        raise ValueError("n must be at least 1")
    if not 0.0 <= failure_rate <= 1.0:
        raise ValueError("failure_rate must be between 0 and 1")
    init_db()
    llm = llm or _llm_client()
    retriever = retriever or get_retriever(workspace)
    randomizer = random.Random(seed)
    counters = {"sent": 0, "wrong": 0, "incidents_opened": 0, "emails_queued": 0}
    with get_session() as session:
        tasks = list(
            session.exec(
                select(Task).where(Task.workspace == workspace).order_by(Task.task_id)
            ).all()
        )
        if not tasks:
            raise ValueError(f"No tasks found for workspace: {workspace}")
        initial_incidents = len(
            session.exec(select(Incident).where(Incident.workspace == workspace)).all()
        )
        initial_emails = len(
            session.exec(
                select(NotificationLog).where(
                    NotificationLog.workspace == workspace,
                    NotificationLog.status == "queued",
                )
            ).all()
        )

        for _ in range(n):
            task = randomizer.choice(tasks)
            run: Run
            if randomizer.random() < failure_rate:
                clean_run = latest_clean_run(session, task.task_id)
                if clean_run is None:
                    clean_run = _run_clean(session, task, llm, retriever, "clean")
                target = (
                    _weighted_target(clean_run, randomizer)
                    if clean_run.outcome == "pass"
                    else None
                )
                if target is not None:
                    fault_type, step_key = target
                    run = _execute_fault(
                        session,
                        task,
                        fault_type,
                        step_key,
                        seed=randomizer.randrange(1_000_000),
                        llm=llm,
                        retriever=retriever,
                        origin="simulated",
                    )
                else:
                    run = _run_clean(session, task, llm, retriever, "simulated")
            else:
                run = _run_clean(session, task, llm, retriever, "simulated")
            counters["sent"] += 1
            if run.outcome == "fail":
                counters["wrong"] += 1
            on_run_finished(run)
            if progress_fn is not None:
                progress_fn(dict(counters))

        counters["incidents_opened"] = len(
            session.exec(select(Incident).where(Incident.workspace == workspace)).all()
        ) - initial_incidents
        counters["emails_queued"] = len(
            session.exec(
                select(NotificationLog).where(
                    NotificationLog.workspace == workspace,
                    NotificationLog.status == "queued",
                )
            ).all()
        ) - initial_emails
    return counters


def simulation_job(**kwargs: Any) -> dict[str, int]:
    return run_simulation(**kwargs)