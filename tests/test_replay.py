from pathlib import Path
from typing import Any

import pytest
from sqlmodel import Session, SQLModel, create_engine

from blackbox.agent.agent import run_agent
from blackbox.corpus.retriever import Retriever
from blackbox.llm.fake import FakeLLM
from blackbox.replay.compare import _compare
from blackbox.replay.engine import _replay
from blackbox.replay.graph import _blast_radius
from blackbox.sdk.cassette import Cassette
from blackbox.sdk.context import ExecutionContext, Override
from blackbox.sdk.tracer import Tracer
from blackbox.store.models import Run, Task
from blackbox.store.repo import get_steps, upsert_task


class ReplayRetriever(Retriever):
    def search(self, query: str, k: int = 3) -> list[dict[str, Any]]:
        return [
            {
                "pid": query,
                "title": query,
                "text": f"Evidence for {query}",
                "score": 1.0,
            }
        ][:k]


@pytest.fixture
def session(tmp_path: Path) -> Session:
    engine = create_engine(f"sqlite:///{tmp_path / 'replay.db'}")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session


def _task(task_id: str, qtype: str) -> Task:
    return Task(
        task_id=task_id,
        question=f"{qtype.title()} question?",
        gold_answer="final",
        qtype=qtype,
        level="easy",
        split="test",
        gold_titles=[],
        distractor_pids=[],
    )


def _script(qtype: str) -> dict[str, dict[str, Any]]:
    second_deps = [] if qtype == "comparison" else ["q1"]
    second_text = "Second fact?" if qtype == "comparison" else "Where was {q1} born?"
    return {
        "[PLAN]": {
            "type": qtype,
            "subquestions": [
                {"id": "q1", "text": "First fact?", "deps": []},
                {"id": "q2", "text": second_text, "deps": second_deps},
            ],
        },
        "Changed evidence": {
            "answer": "changed",
            "evidence_pid": "changed",
            "evidence_sentence": "Changed evidence",
        },
        "First fact?": {
            "answer": "one",
            "evidence_pid": "one",
            "evidence_sentence": "Evidence",
        },
        "Second fact?": {
            "answer": "two",
            "evidence_pid": "two",
            "evidence_sentence": "Evidence",
        },
        "Evidence for Where was one born?": {
            "answer": "place-one",
            "evidence_pid": "place-one",
            "evidence_sentence": "Evidence",
        },
        "Evidence for Where was changed born?": {
            "answer": "place-changed",
            "evidence_pid": "place-changed",
            "evidence_sentence": "Evidence",
        },
        "[CHECK]\nDecide whether": {"supported": True, "reason": "direct"},
        "[SYNTHESIZE]": {"answer": "final"},
    }


def _clean_run(
    session: Session,
    task: Task,
    script: dict[str, dict[str, Any]],
    retriever: Retriever,
) -> str:
    task = upsert_task(session, task)
    tracer = Tracer(session, Cassette(session), llm=FakeLLM(script))
    run = run_agent(
        task,
        ExecutionContext(
            run_id=f"{task.task_id}-clean",
            task=task,
            origin="clean",
            tracer=tracer,
            retriever=retriever,
        ),
    )
    return run.run_id


def test_comparison_override_reexecutes_one_branch_and_synthesis(
    session: Session,
) -> None:
    task = _task("comparison-replay", "comparison")
    script = _script("comparison")
    retriever = ReplayRetriever()
    source_id = _clean_run(session, task, script, retriever)

    replay = _replay(
        session,
        source_id,
        FakeLLM(script),
        retriever,
        overrides={
            "q1/retrieve#0": Override(
                kind="set_output",
                output={
                    "passages": [
                        {
                            "pid": "changed",
                            "title": "changed",
                            "text": "Changed evidence",
                            "score": 1.0,
                        }
                    ]
                },
            )
        },
    )
    steps = {step.step_key: step for step in get_steps(session, replay.run_id)}

    assert replay.n_reused == 4
    assert replay.n_executed == 4
    assert all(
        steps[key].reused
        for key in ("plan", "q2/retrieve#0", "q2/extract#0", "q2/check#0")
    )
    assert all(
        not steps[key].reused
        for key in ("q1/retrieve#0", "q1/extract#0", "q1/check#0", "synthesize")
    )
    assert _blast_radius(get_steps(session, source_id), "q1/retrieve#0") == [
        "q1/extract#0",
        "q1/check#0",
        "synthesize",
    ]


def test_bridge_override_reexecutes_dependent_branch(session: Session) -> None:
    task = _task("bridge-replay", "bridge")
    script = _script("bridge")
    retriever = ReplayRetriever()
    source_id = _clean_run(session, task, script, retriever)

    replay = _replay(
        session,
        source_id,
        FakeLLM(script),
        retriever,
        overrides={
            "q1/extract#0": Override(
                kind="set_output",
                output={"answer": "changed", "evidence_pid": "changed"},
            )
        },
    )
    steps = {step.step_key: step for step in get_steps(session, replay.run_id)}

    assert all(
        not steps[key].reused for key in ("q2/retrieve#0", "q2/extract#0", "q2/check#0")
    )
    assert replay.n_reused == 2
    assert replay.n_executed == 6


def test_noop_replay_reuses_every_step(session: Session) -> None:
    task = _task("noop-replay", "comparison")
    script = _script("comparison")
    retriever = ReplayRetriever()
    source_id = _clean_run(session, task, script, retriever)

    replay = _replay(session, source_id, FakeLLM(script), retriever)

    assert replay.n_reused == replay.n_steps == 8
    assert replay.n_executed == 0
    assert replay.parent_run_id == source_id
    assert replay.replay_spec == {"overrides": {}, "freeze_before_idx": None}


def test_compare_reports_first_changed_step(session: Session) -> None:
    task = _task("compare-replay", "comparison")
    script = _script("comparison")
    retriever = ReplayRetriever()
    source_id = _clean_run(session, task, script, retriever)
    source_run = session.get(Run, source_id)
    assert source_run is not None
    replay = _replay(
        session,
        source_id,
        FakeLLM(script),
        retriever,
        overrides={
            "q1/extract#0": Override(kind="set_output", output={"answer": "changed"})
        },
    )

    comparison = _compare(session, source_run, replay)

    assert comparison["first_divergence"] == "q1/extract#0"
    assert (
        next(row for row in comparison["rows"] if row["step_key"] == "q1/extract#0")[
            "status"
        ]
        == "changed"
    )
