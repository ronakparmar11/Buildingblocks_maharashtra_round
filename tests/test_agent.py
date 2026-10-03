from pathlib import Path
from typing import Any

import pytest
from sqlmodel import Session, SQLModel, create_engine

from blackbox.agent.agent import NIMBU_PREAMBLE, run_agent
from blackbox.agent.scoring import exact_match, f1, is_pass, normalize_answer
from blackbox.corpus.retriever import Retriever
from blackbox.llm.fake import FakeLLM
from blackbox.sdk.cassette import Cassette
from blackbox.sdk.context import ExecutionContext
from blackbox.sdk.tracer import Tracer
from blackbox.store.models import Task
from blackbox.store.repo import get_steps, upsert_task


class QueryRetriever(Retriever):
    def __init__(self) -> None:
        self.queries: list[str] = []

    def search(self, query: str, k: int = 3) -> list[dict[str, Any]]:
        self.queries.append(query)
        return [
            {
                "pid": f"p{len(self.queries)}",
                "title": query,
                "text": f"Evidence for {query}",
                "score": 1.0,
            }
        ][:k]


@pytest.fixture
def session(tmp_path: Path) -> Session:
    engine = create_engine(f"sqlite:///{tmp_path / 'agent.db'}")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session


def _task(task_id: str, question: str, answer: str, qtype: str) -> Task:
    return Task(
        task_id=task_id,
        question=question,
        gold_answer=answer,
        qtype=qtype,
        level="easy",
        split="test",
        gold_titles=[],
        distractor_pids=[],
    )


def _run(
    session: Session,
    task: Task,
    script: dict[str, dict[str, Any]],
    run_id: str,
) -> tuple[FakeLLM, QueryRetriever]:
    upsert_task(session, task)
    fake = FakeLLM(script)
    retriever = QueryRetriever()
    tracer = Tracer(session, Cassette(session), llm=fake)
    ctx = ExecutionContext(
        run_id=run_id,
        task=task,
        origin="clean",
        tracer=tracer,
        retriever=retriever,
    )
    run_agent(task, ctx)
    return fake, retriever


def test_nimbu_preamble_is_added_to_every_llm_prompt_only_for_nimbu(
    session: Session,
) -> None:
    script = {
        "[PLAN]": {
            "type": "bridge",
            "subquestions": [{"id": "q1", "text": "Policy?", "deps": []}],
        },
        "Policy?": {
            "answer": "7 days",
            "evidence_pid": "p1",
            "evidence_sentence": "Return within 7 days.",
        },
        "[CHECK]": {"supported": True, "reason": "direct"},
        "[SYNTHESIZE]": {"answer": "7 days"},
    }
    nimbu = _task("nimbu-prompt", "Return window?", "7 days", "bridge")
    nimbu.workspace = "nimbu"
    hotpot = _task("hotpot-prompt", "Return window?", "7 days", "bridge")

    _run(session, nimbu, script, "nimbu-prompt-run")
    _run(session, hotpot, script, "hotpot-prompt-run")

    nimbu_prompts = [
        step.input["prompt"]
        for step in get_steps(session, "nimbu-prompt-run")
        if step.type == "llm"
    ]
    hotpot_prompts = [
        step.input["prompt"]
        for step in get_steps(session, "hotpot-prompt-run")
        if step.type == "llm"
    ]
    assert nimbu_prompts and all(
        prompt.startswith(NIMBU_PREAMBLE) for prompt in nimbu_prompts
    )
    assert hotpot_prompts and all(
        NIMBU_PREAMBLE not in prompt for prompt in hotpot_prompts
    )


def test_comparison_has_independent_branches_and_second_run_hits_cassette(
    session: Session,
) -> None:
    task = _task("comparison", "Compare root?", "Alpha", "comparison")
    script = {
        "Question: Compare root?": {
            "type": "comparison",
            "subquestions": [
                {"id": "q2", "text": "Second fact?", "deps": []},
                {"id": "q1", "text": "First fact?", "deps": []},
            ],
        },
        "First fact?": {
            "answer": "one",
            "evidence_pid": "p1",
            "evidence_sentence": "Evidence",
        },
        "Second fact?": {
            "answer": "two",
            "evidence_pid": "p2",
            "evidence_sentence": "Evidence",
        },
        "[CHECK]\nDecide whether the answer": {
            "supported": True,
            "reason": "direct",
        },
        "[SYNTHESIZE]": {"answer": "Alpha"},
    }
    fake, _ = _run(session, task, script, "comparison-1")
    second_fake, _ = _run(session, task, script, "comparison-2")

    steps = {step.step_key: step for step in get_steps(session, "comparison-1")}
    assert list(steps) == [
        "plan",
        "q1/retrieve#0",
        "q1/extract#0",
        "q1/check#0",
        "q2/retrieve#0",
        "q2/extract#0",
        "q2/check#0",
        "synthesize",
    ]
    assert steps["q1/retrieve#0"].deps == ["plan"]
    assert steps["q2/retrieve#0"].deps == ["plan"]
    assert steps["synthesize"].deps == ["q1/extract#0", "q2/extract#0"]
    assert fake.calls == 6
    assert second_fake.calls == 0
    assert all(step.cache_hit for step in get_steps(session, "comparison-2"))


def test_bridge_fills_placeholder_and_retries_unsupported_answer(
    session: Session,
) -> None:
    task = _task("bridge", "Bridge root?", "Paris", "bridge")
    script = {
        "Question: Bridge root?": {
            "type": "bridge",
            "subquestions": [
                {"id": "q1", "text": "Who wrote Alpha?", "deps": []},
                {"id": "q2", "text": "Where was {q1} born?", "deps": ["q1"]},
            ],
        },
        "Who wrote Alpha?": {
            "answer": "Ada",
            "evidence_pid": "p1",
            "evidence_sentence": "Evidence",
        },
        "Where was Ada born?": {
            "answer": "wrong",
            "evidence_pid": "p2",
            "evidence_sentence": "Evidence",
        },
        "Ada birthplace": {
            "answer": "Paris",
            "evidence_pid": "p3",
            "evidence_sentence": "Evidence",
        },
        'Answer: wrong\nPassages: [{"pid":"p2"': {
            "supported": False,
            "reason": "not in passage",
        },
        "[CHECK]\nDecide whether the answer": {
            "supported": True,
            "reason": "direct",
        },
        "[REFORMULATE]\nWrite a better retrieval query": {
            "query": "Ada birthplace"
        },
        "[SYNTHESIZE]": {"answer": "Paris"},
    }
    _, retriever = _run(session, task, script, "bridge-1")

    steps = {step.step_key: step for step in get_steps(session, "bridge-1")}
    assert retriever.queries == ["Who wrote Alpha?", "Where was Ada born?", "Ada birthplace"]
    assert steps["q2/retrieve#0"].deps == ["plan", "q1/extract#0"]
    assert steps["q2/reformulate#0"].deps == ["q2/check#0"]
    assert steps["q2/retrieve#1"].deps == [
        "plan",
        "q1/extract#0",
        "q2/reformulate#0",
    ]
    assert steps["synthesize"].deps == ["q1/extract#0", "q2/extract#1"]


def test_hotpot_scoring() -> None:
    assert normalize_answer(" The, Eiffel Tower! ") == "eiffel tower"
    assert exact_match("An answer", "answer")
    assert f1("red blue green", "red blue") == pytest.approx(0.8)
    assert is_pass("red blue green", "red blue")
    assert not is_pass("red", "blue")


def test_invalid_plan_falls_back_to_original_question(session: Session) -> None:
    task = _task("fallback", "Original question?", "answer", "bridge")
    script = {
        "Question: Original question?": {"unexpected": "shape"},
        "Original question?": {
            "answer": "answer",
            "evidence_pid": "p1",
            "evidence_sentence": "Evidence",
        },
        "[CHECK]\nDecide whether the answer": {
            "supported": True,
            "reason": "direct",
        },
        "[SYNTHESIZE]": {"answer": "answer"},
    }
    _, retriever = _run(session, task, script, "fallback-1")

    assert retriever.queries == ["Original question?"]
    steps = get_steps(session, "fallback-1")
    assert [step.step_key for step in steps] == [
        "plan",
        "q1/retrieve#0",
        "q1/extract#0",
        "q1/check#0",
        "synthesize",
    ]