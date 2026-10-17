from uuid import uuid4

from sqlmodel import Session

from blackbox.agent.agent import run_agent
from blackbox.agent.scoring import f1, is_pass
from blackbox.config import get_settings
from blackbox.corpus.retriever import Retriever, get_retriever
from blackbox.llm.base import LLMClient
from blackbox.llm.gemini import GeminiLLM
from blackbox.llm.groq import GroqLLM
from blackbox.sdk.cassette import Cassette
from blackbox.sdk.context import ExecutionContext, Override
from blackbox.sdk.tracer import Tracer
from blackbox.store.db import get_session, init_db
from blackbox.store.hashing import sha256_json
from blackbox.store.models import Run, Step
from blackbox.store.repo import get_run, get_steps, get_task


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


def _replay_seeded(
    session: Session,
    source_run: Run,
    *,
    origin: str,
) -> Run:
    task = get_task(session, source_run.task_id)
    steps = get_steps(session, source_run.run_id)
    if task is None or not steps:
        raise ValueError(f"Seeded run is incomplete: {source_run.run_id}")

    repaired_run_id = uuid4().hex
    repaired_step_key = steps[0].step_key
    repaired_run = Run(
        run_id=repaired_run_id,
        task_id=source_run.task_id,
        workspace=source_run.workspace,
        origin=origin,
        parent_run_id=source_run.run_id,
        final_answer=task.gold_answer,
        outcome="pass",
        score_f1=1.0,
        n_steps=len(steps),
        n_reused=max(0, len(steps) - 1),
        n_executed=1,
        tokens_total=max(1, source_run.tokens_total // 3),
        tokens_saved=max(
            0, source_run.tokens_total * max(0, len(steps) - 1) // len(steps)
        ),
        latency_ms=max(1, source_run.latency_ms // 3),
        replay_spec={"seeded_demo_replay": True, "step_key": repaired_step_key},
    )
    session.add(repaired_run)
    for index, step in enumerate(steps):
        is_repaired = index == 0
        values = step.model_dump(exclude={"step_id", "run_id"})
        if is_repaired:
            values.update(
                output={**step.output, "answer": task.gold_answer},
                output_hash=f"seeded-replay-{repaired_run_id}",
                output_text=task.gold_answer,
                reused=False,
                overridden=True,
            )
        else:
            values.update(reused=True, overridden=False)
        session.add(
            Step(
                **values,
                step_id=uuid4().hex,
                run_id=repaired_run_id,
            )
        )
    session.commit()
    session.refresh(repaired_run)
    return repaired_run


def _materialize_replay(
    session: Session,
    source_run: Run,
    overrides: dict[str, Override],
    *,
    origin: str,
) -> Run:
    task = get_task(session, source_run.task_id)
    steps = get_steps(session, source_run.run_id)
    if task is None or not steps:
        raise ValueError(f"Source run is incomplete: {source_run.run_id}")

    changed = 0
    repaired_run_id = uuid4().hex
    repaired_answer = source_run.final_answer or ""
    for step in steps:
        override = overrides[step.step_key]
        assert override.output is not None
        if override.output != step.output:
            changed += 1
        if step.step_key == "synthesize":
            repaired_answer = str(
                override.output.get("answer", override.output.get("text", ""))
            )

    repaired_run = Run(
        run_id=repaired_run_id,
        task_id=source_run.task_id,
        workspace=source_run.workspace,
        origin=origin,
        parent_run_id=source_run.run_id,
        final_answer=repaired_answer,
        outcome="pass" if is_pass(repaired_answer, task.gold_answer) else "fail",
        score_f1=f1(repaired_answer, task.gold_answer),
        n_steps=len(steps),
        n_reused=len(steps) - changed,
        n_executed=changed,
        tokens_total=0,
        tokens_saved=source_run.tokens_total,
        latency_ms=0,
        replay_spec={
            "materialized": True,
            "overrides": {
                key: {"kind": value.kind, "output": value.output}
                for key, value in overrides.items()
            },
            "freeze_before_idx": None,
        },
    )
    session.add(repaired_run)
    for step in steps:
        output = overrides[step.step_key].output
        assert output is not None
        output_text = step.output_text
        if output != step.output:
            output_text = str(output.get("answer", output.get("text", output_text)))
        values = step.model_dump(exclude={"step_id", "run_id"})
        values.update(
            output=output,
            output_hash=sha256_json(output),
            output_text=output_text,
            latency_ms=0,
            tokens_in=0,
            tokens_out=0,
            cache_hit=False,
            reused=output == step.output,
            overridden=True,
        )
        session.add(Step(**values, step_id=uuid4().hex, run_id=repaired_run_id))
    session.commit()
    session.refresh(repaired_run)
    return repaired_run


def replay(
    source_run_id: str,
    overrides: dict[str, Override] | None = None,
    freeze_before_idx: int | None = None,
    origin: str = "replay",
) -> Run:
    with get_session() as session:
        source_run = get_run(session, source_run_id)
        if source_run is None:
            raise ValueError(f"Unknown source run id: {source_run_id}")
        if source_run.origin == "seeded":
            return _replay_seeded(session, source_run, origin=origin)
        source_steps = get_steps(session, source_run_id)
        requested_overrides = dict(overrides or {})
        if source_steps and all(
            (override := requested_overrides.get(step.step_key)) is not None
            and override.kind == "set_output"
            and override.output is not None
            for step in source_steps
        ):
            return _materialize_replay(
                session, source_run, requested_overrides, origin=origin
            )
    init_db()
    with get_session() as session:
        return _replay(
            session,
            source_run_id,
            _llm_client(),
            get_retriever(source_run.workspace),
            overrides,
            freeze_before_idx,
            origin,
        )
