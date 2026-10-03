from uuid import uuid4

from sqlmodel import Session

from blackbox.agent.agent import run_agent
from blackbox.config import get_settings
from blackbox.corpus.retriever import Retriever, get_retriever
from blackbox.llm.base import LLMClient
from blackbox.llm.gemini import GeminiLLM
from blackbox.llm.groq import GroqLLM
from blackbox.sdk.cassette import Cassette
from blackbox.sdk.context import ExecutionContext, Override
from blackbox.sdk.tracer import Tracer
from blackbox.store.db import get_session, init_db
from blackbox.store.models import Run
from blackbox.store.repo import get_run, get_task


def _llm_client() -> LLMClient:
    settings = get_settings()
    if settings.LLM_PROVIDER == "gemini":
        return GeminiLLM()
    if settings.LLM_PROVIDER == "groq":
        return GroqLLM()
    raise ValueError("LLM_PROVIDER=fake is only supported in tests")


def _replay(
    session: Session,
    source_run_id: str,
    llm: LLMClient,
    retriever: Retriever,
    overrides: dict[str, Override] | None = None,
    freeze_before_idx: int | None = None,
    origin: str = "replay",
) -> Run:
    source_run = get_run(session, source_run_id)
    if source_run is None:
        raise ValueError(f"Unknown source run id: {source_run_id}")
    task = get_task(session, source_run.task_id)
    if task is None:
        raise ValueError(f"Task not found for source run: {source_run.task_id}")

    tracer = Tracer(session, Cassette(session), llm=llm)
    context = ExecutionContext(
        run_id=uuid4().hex,
        task=task,
        origin=origin,
        source_run_id=source_run.run_id,
        overrides=dict(overrides or {}),
        freeze_before_idx=freeze_before_idx,
        demo_mode=bool(get_settings().BLACKBOX_DEMO_MODE),
        tracer=tracer,
        retriever=retriever,
    )
    return run_agent(task, context)


def replay(
    source_run_id: str,
    overrides: dict[str, Override] | None = None,
    freeze_before_idx: int | None = None,
    origin: str = "replay",
) -> Run:
    init_db()
    with get_session() as session:
        source_run = get_run(session, source_run_id)
        if source_run is None:
            raise ValueError(f"Unknown source run id: {source_run_id}")
        return _replay(
            session,
            source_run_id,
            _llm_client(),
            get_retriever(source_run.workspace),
            overrides,
            freeze_before_idx,
            origin,
        )
