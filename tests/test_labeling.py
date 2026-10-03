from pathlib import Path
from typing import Any

import pytest
from sqlmodel import Session, SQLModel, create_engine

from blackbox.agent.agent import run_agent
from blackbox.corpus.retriever import Retriever
from blackbox.faults.inject import _execute_fault
from blackbox.faults.library import WRONG_EXTRACTION
from blackbox.labeling.bisect import _label_fault_run
from blackbox.labeling.counterfactual import _label_organic_run
from blackbox.llm.base import LLMResponse
from blackbox.llm.fake import FakeLLM
from blackbox.replay.engine import _replay
from blackbox.sdk.cassette import Cassette
from blackbox.sdk.context import ExecutionContext
from blackbox.sdk.tracer import Tracer
from blackbox.store.models import Run, Task
from blackbox.store.repo import get_steps, upsert_task


class LabelRetriever(Retriever):
    def search(self, query: str, k: int = 3) -> list[dict[str, Any]]:
        if "Who wrote" in query:
            passages = [
                {
                    "pid": "ada",
                    "title": "Ada",
                    "text": "Ada wrote Alpha.",
                    "score": 1.0,
                },
                {
                    "pid": "other",
                    "title": "Other Person",
                    "text": "Another writer published Beta.",
                    "score": 0.5,
                },
            ]
        else:
            passages = [
                {
                    "pid": "paris",
                    "title": "Paris",
                    "text": "Ada was born in Paris.",
                    "score": 1.0,
                }
            ]
        return passages[:k]


class SampledFakeLLM(FakeLLM):
    def complete_json(
        self, prompt: str, temperature: float, sample_idx: int = 0
    ) -> LLMResponse:
        if (
            temperature == 0.8
            and "Subquestion: Who wrote Alpha?\nPassages:" in prompt
        ):
            answer = "Ada" if sample_idx < 2 else "Other Person"
            return LLMResponse(
                text=answer,
                json={
                    "answer": answer,
                    "evidence_pid": answer,
                    "evidence_sentence": answer,
                },
                tokens_in=1,
                tokens_out=1,
                model=self.model,
            )
        return super().complete_json(prompt, temperature, sample_idx)


@pytest.fixture
def session(tmp_path: Path) -> Session:
    engine = create_engine(f"sqlite:///{tmp_path / 'labeling.db'}")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session


def _task(task_id: str) -> Task:
    return Task(
        task_id=task_id,
        question="Where was the author of Alpha born?",
        gold_answer="Paris",
        qtype="bridge",
        level="easy",
        split="test",
        gold_titles=[],
        distractor_pids=[],
    )


def _script(q1_answer: str = "Ada", causal_synthesis: bool = True) -> dict[str, Any]:
    script: dict[str, Any] = {
        "[PLAN]\nDecompose the question": {
            "type": "bridge",
            "subquestions": [
                {"id": "q1", "text": "Who wrote Alpha?", "deps": []},
                {
                    "id": "q2",
                    "text": "Where was {q1} born?",
                    "deps": ["q1"],
                },
            ],
        },
        "Subquestion: Who wrote Alpha?\nPassages:": {
            "answer": q1_answer,
            "evidence_pid": "ada",
            "evidence_sentence": "Ada wrote Alpha.",
        },
        "Subquestion: Where was {q1} born?\nPassages:": {
            "answer": "Paris",
            "evidence_pid": "paris",
            "evidence_sentence": "Ada was born in Paris.",
        },
        "[CHECK]": {"supported": True, "reason": "direct"},
        "[SYNTHESIZE]": {"answer": "Paris"},
    }
    if causal_synthesis:
        script['Subanswers: {"q1":"Other Person"'] = {"answer": "London"}
    return script


def _run(
    session: Session, task: Task, llm: FakeLLM, retriever: LabelRetriever, run_id: str
) -> Run:
    tracer = Tracer(session, Cassette(session), llm=llm)
    return run_agent(
        task,
        ExecutionContext(
            run_id=run_id,
            task=task,
            origin="clean",
            tracer=tracer,
            retriever=retriever,
        ),
    )


def test_bisect_finds_third_step_and_verifies(session: Session) -> None:
    task = upsert_task(session, _task("bisect"))
    retriever = LabelRetriever()
    script = _script()
    assert _run(session, task, FakeLLM(script), retriever, "clean").outcome == "pass"
    fault_run = _execute_fault(
        session,
        task,
        WRONG_EXTRACTION,
        "q1/extract#0",
        seed=7,
        llm=FakeLLM(script),
        retriever=retriever,
    )
    assert fault_run.outcome == "fail"
    assert len(get_steps(session, fault_run.run_id)) == 8

    def replay_fn(source_run_id: str, **kwargs: Any) -> Run:
        return _replay(
            session,
            source_run_id,
            FakeLLM(script),
            retriever,
            **kwargs,
        )

    label = _label_fault_run(session, fault_run.run_id, replay_fn)

    assert label is not None
    assert label.culprit_step_key == "q1/extract#0"
    assert label.verified is True
    assert label.matches_injection is True
    assert label.n_replays <= 4


def test_fault_that_does_not_cause_failure_is_skipped(session: Session) -> None:
    task = upsert_task(session, _task("harmless"))
    retriever = LabelRetriever()
    script = _script(causal_synthesis=False)
    assert _run(session, task, FakeLLM(script), retriever, "clean").outcome == "pass"
    fault_run = _execute_fault(
        session,
        task,
        WRONG_EXTRACTION,
        "q1/extract#0",
        seed=7,
        llm=FakeLLM(script),
        retriever=retriever,
    )

    assert fault_run.outcome == "pass"
    assert _label_fault_run(session, fault_run.run_id, pytest.fail) is None


def test_organic_resampling_labels_second_indexed_step(session: Session) -> None:
    task = upsert_task(session, _task("organic"))
    retriever = LabelRetriever()
    script = _script(q1_answer="Other Person")
    source_run = _run(
        session, task, SampledFakeLLM(script), retriever, "organic-source"
    )
    assert source_run.outcome == "fail"

    def replay_fn(source_run_id: str, **kwargs: Any) -> Run:
        return _replay(
            session,
            source_run_id,
            SampledFakeLLM(script),
            retriever,
            **kwargs,
        )

    label = _label_organic_run(session, source_run.run_id, replay_fn)

    assert label is not None
    assert label.culprit_step_key == "q1/extract#0"
    assert label.confidence == pytest.approx(2 / 3)
    assert label.verified is True