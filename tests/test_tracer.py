from pathlib import Path
from typing import Any

import pytest
from sqlmodel import Session, SQLModel, create_engine

from blackbox.llm.fake import FakeLLM
from blackbox.sdk.cassette import Cassette, CassetteMissError
from blackbox.sdk.context import ExecutionContext, Override
from blackbox.sdk.tracer import Tracer, register_fault
from blackbox.store.models import Task
from blackbox.store.repo import get_run, get_steps, upsert_task


def _task() -> Task:
    return Task(
        task_id="toy",
        question="toy question",
        gold_answer="answer",
        qtype="comparison",
        level="easy",
        split="test",
        gold_titles=[],
        distractor_pids=[],
    )


def _context(run_id: str, **kwargs: Any) -> ExecutionContext:
    return ExecutionContext(
        run_id=run_id,
        task=_task(),
        origin=kwargs.pop("origin", "clean"),
        state_snapshot=lambda: {"run": run_id},
        **kwargs,
    )


def _run_toy(tracer: Tracer, ctx: ExecutionContext) -> list[dict[str, Any]]:
    with tracer.run_scope(ctx):
        first = tracer.step(
            key="first",
            name="plan",
            type="llm",
            node_id="root",
            attempt=0,
            deps=[],
            input={"prompt": "FIRST"},
            fn=tracer.llm_call,
            output_text_fn=lambda output: output["value"],
        )
        second = tracer.step(
            key="second",
            name="synthesize",
            type="llm",
            node_id="root",
            attempt=0,
            deps=["first"],
            input={"prompt": f"SECOND {first['value']}"},
            fn=tracer.llm_call,
            output_text_fn=lambda output: output["value"],
        )
        independent = tracer.step(
            key="independent",
            name="extract",
            type="llm",
            node_id="q1",
            attempt=0,
            deps=[],
            input={"prompt": "INDEPENDENT"},
            fn=tracer.llm_call,
            output_text_fn=lambda output: output["value"],
        )
    return [first, second, independent]


@pytest.fixture
def session(tmp_path: Path) -> Session:
    engine = create_engine(f"sqlite:///{tmp_path / 'tracer.db'}")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db_session:
        upsert_task(db_session, _task())
        yield db_session


@pytest.fixture
def fake() -> FakeLLM:
    return FakeLLM(
        {
            "FIRST": {"value": "one"},
            "SECOND one": {"value": "two"},
            "SECOND corrupt": {"value": "corrupt downstream"},
            "SECOND changed": {"value": "changed downstream"},
            "INDEPENDENT": {"value": "independent"},
        }
    )


def _tracer(session: Session, fake: FakeLLM, demo_mode: bool = False) -> Tracer:
    return Tracer(session, Cassette(session, demo_mode=demo_mode), llm=fake)


def test_records_steps_and_second_identical_run_hits_cassette(
    session: Session, fake: FakeLLM
) -> None:
    tracer = _tracer(session, fake)
    _run_toy(tracer, _context("recorded"))
    _run_toy(tracer, _context("identical"))

    first_steps = get_steps(session, "recorded")
    second_steps = get_steps(session, "identical")
    assert [step.idx for step in first_steps] == [0, 1, 2]
    assert all(not step.cache_hit for step in first_steps)
    assert all(step.cache_hit for step in second_steps)
    assert all(step.input_hash and step.output_hash for step in first_steps)
    assert get_run(session, "recorded").n_steps == 3  # type: ignore[union-attr]
    assert get_run(session, "identical").tokens_total == 0  # type: ignore[union-attr]


def test_noop_replay_reuses_every_step_without_tokens(
    session: Session, fake: FakeLLM
) -> None:
    tracer = _tracer(session, fake)
    _run_toy(tracer, _context("source"))
    _run_toy(
        tracer,
        _context("replay", origin="replay", source_run_id="source"),
    )

    run = get_run(session, "replay")
    assert run is not None
    assert (run.n_reused, run.n_executed, run.tokens_total) == (3, 0, 0)
    assert all(step.reused for step in get_steps(session, "replay"))


def test_set_output_executes_dependent_and_reuses_independent(
    session: Session, fake: FakeLLM
) -> None:
    tracer = _tracer(session, fake)
    _run_toy(tracer, _context("source"))
    ctx = _context(
        "edited",
        origin="replay",
        source_run_id="source",
        overrides={"first": Override("set_output", output={"value": "changed"})},
    )
    _run_toy(tracer, ctx)

    steps = {step.step_key: step for step in get_steps(session, "edited")}
    assert steps["first"].overridden
    assert not steps["second"].reused
    assert steps["independent"].reused


def test_freeze_reuses_only_steps_before_index(session: Session, fake: FakeLLM) -> None:
    tracer = _tracer(session, fake)
    _run_toy(tracer, _context("source"))
    _run_toy(
        tracer,
        _context(
            "frozen",
            origin="bisect",
            source_run_id="source",
            freeze_before_idx=1,
        ),
    )

    steps = get_steps(session, "frozen")
    assert [step.reused for step in steps] == [True, False, False]


def test_output_fault_caches_raw_and_regenerate_returns_clean(
    session: Session, fake: FakeLLM
) -> None:
    register_fault(
        "CORRUPT_OUTPUT",
        output_fn=lambda output, params: {"value": params["value"]},
    )
    tracer = _tracer(session, fake)
    fault_ctx = _context(
        "faulted",
        origin="fault",
        overrides={
            "first": Override(
                "fault",
                fault_type="CORRUPT_OUTPUT",
                fault_params={"value": "corrupt"},
            )
        },
    )
    _run_toy(tracer, fault_ctx)
    assert get_steps(session, "faulted")[0].output == {"value": "corrupt"}

    replay_ctx = _context(
        "regenerated",
        origin="replay",
        source_run_id="faulted",
        overrides={"first": Override("regenerate")},
    )
    outputs = _run_toy(tracer, replay_ctx)
    assert outputs[0] == {"value": "one"}
    assert get_steps(session, "regenerated")[0].cache_hit


def test_input_fault_noop_reuse_and_freeze_reexecutes(
    session: Session, fake: FakeLLM
) -> None:
    register_fault(
        "CHANGE_INPUT",
        input_fn=lambda input_data, params: {"prompt": params["prompt"]},
    )
    fake.script["FAULTY FIRST"] = {"value": "faulted"}
    fake.script["SECOND faulted"] = {"value": "faulted downstream"}
    tracer = _tracer(session, fake)
    fault_ctx = _context(
        "faulted",
        origin="fault",
        overrides={
            "first": Override(
                "fault",
                fault_type="CHANGE_INPUT",
                fault_params={"prompt": "FAULTY FIRST"},
            )
        },
    )
    _run_toy(tracer, fault_ctx)
    source_step = get_steps(session, "faulted")[0]
    assert source_step.meta["pre_override_input_hash"]

    _run_toy(
        tracer,
        _context("noop", origin="replay", source_run_id="faulted"),
    )
    assert get_steps(session, "noop")[0].reused

    _run_toy(
        tracer,
        _context(
            "frozen",
            origin="bisect",
            source_run_id="faulted",
            freeze_before_idx=0,
        ),
    )
    frozen_step = get_steps(session, "frozen")[0]
    assert not frozen_step.reused
    assert frozen_step.output == {"value": "one"}


def test_demo_mode_raises_on_cassette_miss(session: Session, fake: FakeLLM) -> None:
    tracer = _tracer(session, fake, demo_mode=True)
    message = (
        "This step isn't in the demo recording. Pick one of the prepared "
        "demo questions in Live lab."
    )
    with pytest.raises(CassetteMissError, match=message):
        _run_toy(tracer, _context("demo", demo_mode=True))

    step = get_steps(session, "demo")[0]
    run = get_run(session, "demo")
    assert step.step_key == "first"
    assert step.error is not None and "CassetteMissError" in step.error
    assert run is not None
    assert run.outcome == "error"
    assert run.n_steps == 1
