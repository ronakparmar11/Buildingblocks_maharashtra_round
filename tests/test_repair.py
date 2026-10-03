from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from sqlmodel import Session, SQLModel, create_engine

from blackbox.agent.agent import run_agent
from blackbox.corpus.retriever import Retriever
from blackbox.llm.fake import FakeLLM
from blackbox.repair.repair import _repair
from blackbox.repair.strategies import CURRENT_ARTICLES_ONLY
from blackbox.replay.engine import _replay
from blackbox.sdk.cassette import Cassette
from blackbox.sdk.context import ExecutionContext
from blackbox.sdk.tracer import Tracer
from blackbox.store.models import Prediction, Task
from blackbox.store.repo import get_steps, upsert_task


class WideningRetriever(Retriever):
    def search(
        self, query: str, k: int = 3, exclude_archived: bool = False
    ) -> list[dict[str, Any]]:
        passages = [
            {
                "pid": f"bad-{index}",
                "title": f"Bad {index}",
                "text": "Bad evidence",
                "score": 1.0 - index / 10,
                "status": "archived",
            }
            for index in range(5)
        ]
        passages.append(
            {
                "pid": "correct",
                "title": "Correct",
                "text": "Correct evidence",
                "score": 0.5,
                "status": "current",
            }
        )
        if exclude_archived:
            passages = [passage for passage in passages if passage["status"] == "current"]
        return passages[:k]

    def search_titles(self, entity: str, k: int = 3) -> list[dict[str, Any]]:
        return self.search(entity, k=3)


def test_repair_widens_retrieval_and_stops_after_first_success(tmp_path: Path) -> None:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'repair.db'}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    task = Task(
        task_id="repair-widen",
        workspace="nimbu",
        question="What is the answer?",
        gold_answer="correct",
        qtype="bridge",
        level="easy",
        split="test",
        gold_titles=[],
        distractor_pids=[],
    )
    script = {
        "[PLAN]": {
            "type": "bridge",
            "subquestions": [
                {"id": "q1", "text": "Find Correct Entity", "deps": []}
            ],
        },
        "Correct evidence": {
            "answer": "correct",
            "evidence_pid": "correct",
            "evidence_sentence": "Correct evidence",
        },
        "Bad evidence": {
            "answer": "wrong",
            "evidence_pid": "bad-0",
            "evidence_sentence": "Bad evidence",
        },
        "[CHECK]\nDecide whether the answer": {
            "supported": True,
            "reason": "direct",
        },
        'Subanswers: {"q1":"correct"}': {"answer": "correct"},
        "[SYNTHESIZE]": {"answer": "wrong"},
    }
    llm = FakeLLM(script)
    retriever = WideningRetriever()
    with Session(engine) as session:
        persisted_task = upsert_task(session, task)
        source_run = run_agent(
            persisted_task,
            ExecutionContext(
                run_id="failed-source",
                task=persisted_task,
                origin="clean",
                tracer=Tracer(session, Cassette(session), llm=llm),
                retriever=retriever,
            ),
        )
        steps = get_steps(session, source_run.run_id)
        retrieve_step = next(step for step in steps if step.name == "retrieve")
        synthesize_step = next(step for step in steps if step.name == "synthesize")
        session.add_all(
            [
                Prediction(
                    run_id=source_run.run_id,
                    step_key=retrieve_step.step_key,
                    score=1.0,
                    rank=1,
                    model_version="test",
                    reasons=[],
                ),
                Prediction(
                    run_id=source_run.run_id,
                    step_key=synthesize_step.step_key,
                    score=0.5,
                    rank=2,
                    model_version="test",
                    reasons=[],
                ),
            ]
        )
        session.commit()

        @contextmanager
        def replay_session() -> Iterator[Session]:
            with Session(engine) as worker_session:
                yield worker_session

        def replay_fn(source_run_id: str, **kwargs: Any):  # type: ignore[no-untyped-def]
            with replay_session() as worker_session:
                return _replay(
                    worker_session,
                    source_run_id,
                    llm,
                    retriever,
                    **kwargs,
                )

        result = _repair(
            session,
            source_run.run_id,
            replay_fn,
            rewrite_query_fn=lambda _step: (_ for _ in ()).throw(
                RuntimeError("query service unavailable")
            ),
            top_k=2,
            max_workers=2,
        )

    assert source_run.outcome == "fail"
    assert result.repaired
    assert result.winning_step_key == retrieve_step.step_key
    assert result.attempts[0].strategy == CURRENT_ARTICLES_ONLY
    assert result.attempts[0].outcome == "pass"
    assert len(result.attempts) == 3
    assert {attempt.step_key for attempt in result.attempts} == {
        retrieve_step.step_key
    }