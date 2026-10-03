import json
from pathlib import Path
from random import Random
from typing import Any

import pytest
from sqlalchemy import inspect
from sqlmodel import Session, SQLModel, create_engine

from blackbox.agent.agent import run_agent
from blackbox.corpus.retriever import Retriever
from blackbox.faults.inject import _distractors, _execute_fault
from blackbox.faults.library import (
    BAD_QUERY,
    DISTRACTOR_RETRIEVAL,
    HALLUCINATED_SYNTHESIS,
    PLAN_CORRUPT,
    TRUNCATED_CONTEXT,
    WRONG_EXTRACTION,
    corrupt_plan,
    hallucinated_synthesis,
)
from blackbox.faults.targets import applicable_targets
from blackbox.llm.fake import FakeLLM
from blackbox.sdk.cassette import Cassette
from blackbox.sdk.context import ExecutionContext
from blackbox.sdk.tracer import Tracer
from blackbox.store.hashing import sha256_json
from blackbox.store.models import Cassette as CassetteRow
from blackbox.store.models import Run, Task
from blackbox.store.repo import get_fault, get_steps, upsert_task


class FaultRetriever(Retriever):
    def __init__(self) -> None:
        self.distractors = {
            "d1": {
                "pid": "d1",
                "title": "Harbor Master",
                "text": "The harbor master worked in Dover. The office opened in 1902.",
            },
            "d2": {
                "pid": "d2",
                "title": "Northwind Club",
                "text": "Northwind Club plays in Bergen. It was founded in 1931.",
            },
        }

    def search(self, query: str, k: int = 3) -> list[dict[str, Any]]:
        if "Who wrote" in query:
            passages = [
                {
                    "pid": "g1",
                    "title": "Gold Author",
                    "text": "Ada wrote Alpha. The book appeared in 1843.",
                    "score": 0.9,
                },
                {
                    "pid": "o1",
                    "title": "Other Person",
                    "text": "Grace worked on compilers. She served in the Navy.",
                    "score": 0.7,
                },
            ]
        else:
            passages = [
                {
                    "pid": "g2",
                    "title": "Gold Place",
                    "text": "Ada was born in Paris. Paris is in France.",
                    "score": 0.95,
                },
                {
                    "pid": "o2",
                    "title": "Other Place",
                    "text": "Lyon lies in France. It is southeast of Paris.",
                    "score": 0.6,
                },
            ]
        return passages[:k]

    def get_passage(self, pid: str) -> dict[str, str] | None:
        return self.distractors.get(pid)


@pytest.fixture
def session(tmp_path: Path) -> Session:
    engine = create_engine(f"sqlite:///{tmp_path / 'faults.db'}")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session


def _task() -> Task:
    return Task(
        task_id="bridge-fault-host",
        question="Where was the author of Alpha born?",
        gold_answer="Paris",
        qtype="bridge",
        level="easy",
        split="test",
        gold_titles=["Gold Author", "Gold Place"],
        distractor_pids=["d1", "d2"],
    )


def _script() -> dict[str, dict[str, Any]]:
    return {
        "[PLAN]\nDecompose the question": {
            "type": "bridge",
            "subquestions": [
                {"id": "q1", "text": "Who wrote Alpha?", "deps": []},
                {"id": "q2", "text": "Where was {q1} born?", "deps": ["q1"]},
            ],
        },
        "Who wrote Alpha?": {
            "answer": "Ada",
            "evidence_pid": "g1",
            "evidence_sentence": "Ada wrote Alpha.",
        },
        "Where was {q1} born?": {
            "answer": "Paris",
            "evidence_pid": "g2",
            "evidence_sentence": "Ada was born in Paris.",
        },
        "Where was Harbor Master born?": {
            "answer": "Dover",
            "evidence_pid": "d1",
            "evidence_sentence": "The harbor master worked in Dover.",
        },
        "Where was Northwind Club born?": {
            "answer": "Bergen",
            "evidence_pid": "d2",
            "evidence_sentence": "Northwind Club plays in Bergen.",
        },
        "[CHECK]": {"supported": True, "reason": "directly stated"},
        "[SYNTHESIZE]": {"answer": "Paris"},
    }


def _clean_run(session: Session, task: Task, retriever: FaultRetriever) -> str:
    tracer = Tracer(session, Cassette(session), llm=FakeLLM(_script()))
    context = ExecutionContext(
        run_id="clean-host",
        task=task,
        origin="clean",
        tracer=tracer,
        retriever=retriever,
    )
    run = run_agent(task, context)
    assert run.outcome == "pass"
    return run.run_id


def test_each_fault_changes_target_and_persists_raw_response(session: Session) -> None:
    task = upsert_task(session, _task())
    retriever = FaultRetriever()
    clean_run_id = _clean_run(session, task, retriever)
    clean_steps = {step.step_key: step for step in get_steps(session, clean_run_id)}
    targets = {
        PLAN_CORRUPT: "plan",
        BAD_QUERY: "q2/retrieve#0",
        DISTRACTOR_RETRIEVAL: "q1/retrieve#0",
        TRUNCATED_CONTEXT: "q1/retrieve#0",
        WRONG_EXTRACTION: "q1/extract#0",
        HALLUCINATED_SYNTHESIS: "synthesize",
    }
    clean_run = session.get(Run, clean_run_id)
    assert clean_run is not None
    assert set(targets.items()).issubset(set(applicable_targets(clean_run)))

    for fault_type, step_key in targets.items():
        run = _execute_fault(
            session,
            task,
            fault_type,
            step_key,
            seed=7,
            llm=FakeLLM(_script()),
            retriever=retriever,
        )
        assert not inspect(run).expired_attributes
        fault_steps = get_steps(session, run.run_id)
        overridden = [step for step in fault_steps if step.overridden]
        assert [step.step_key for step in overridden] == [step_key]
        target = overridden[0]
        clean_target = clean_steps[step_key]
        changed_value = target.input if fault_type == BAD_QUERY else target.output
        clean_value = (
            clean_target.input if fault_type == BAD_QUERY else clean_target.output
        )
        assert changed_value != clean_value
        json.dumps(changed_value)
        serialized = json.dumps(changed_value).casefold()
        assert all(word not in serialized for word in ("fault", "corrupt", "injected"))

        fault = get_fault(session, run.run_id)
        assert fault is not None
        assert fault.params["seed"] == 7
        assert not ({"distractors", "alternatives", "subanswers"} & fault.params.keys())

        cassette_key = sha256_json(
            {
                "kind": "llm" if target.type == "llm" else "tool",
                "model": "fake",
                "payload": {"input": target.input, "params": {}},
                "temperature": 0.0,
                "sample_idx": 0,
            }
        )
        cassette_row = session.get(CassetteRow, cassette_key)
        assert cassette_row is not None
        if fault_type == BAD_QUERY:
            assert cassette_row.response == target.output
        else:
            assert cassette_row.response != target.output


def test_comparison_specific_fault_branches_are_valid() -> None:
    task = _task().model_copy(update={"qtype": "comparison"})
    plan = {
        "type": "comparison",
        "subquestions": [
            {"id": "q1", "text": "First?", "deps": []},
            {"id": "q2", "text": "Second?", "deps": []},
        ],
    }
    changed_plan, _ = corrupt_plan(plan, task, {"seed": 3}, Random(3))
    changed_answer, _ = hallucinated_synthesis(
        {"answer": "yes"}, task, {"seed": 3}, Random(3)
    )

    assert len(changed_plan["subquestions"]) == 1
    assert changed_answer == {"answer": "no"}


def test_nimbu_distractor_fault_uses_task_article_ids() -> None:
    task = _task().model_copy(
        update={"workspace": "nimbu", "distractor_pids": ["d2"]}
    )

    assert [passage["pid"] for passage in _distractors(task, FaultRetriever())] == [
        "d2"
    ]
