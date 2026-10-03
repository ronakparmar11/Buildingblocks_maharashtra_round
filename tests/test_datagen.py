import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine, func, select

from blackbox.datagen import pipeline
from blackbox.faults.library import PLAN_CORRUPT, WRONG_EXTRACTION
from blackbox.store.models import Fault, Label, Run, Task


def _task(task_id: str) -> Task:
    return Task(
        task_id=task_id,
        question=f"Question {task_id}",
        gold_answer="answer",
        qtype="bridge",
        level="easy",
        split="train",
        gold_titles=[],
        distractor_pids=[],
    )


def _run(task_id: str, origin: str, outcome: str) -> Run:
    return Run(
        task_id=task_id,
        origin=origin,
        outcome=outcome,
        score_f1=1.0 if outcome == "pass" else 0.0,
        n_steps=1,
        n_reused=0,
        n_executed=1,
        tokens_total=2,
        tokens_saved=0,
        latency_ms=1,
    )


def _patch_database(monkeypatch: Any, engine: Engine) -> None:
    @contextmanager
    def sessions() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    monkeypatch.setattr(pipeline, "get_session", sessions)
    monkeypatch.setattr(pipeline, "init_db", lambda: None)


def test_all_stages_are_resumable_and_write_report(
    tmp_path: Path, monkeypatch: Any
) -> None:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'datagen.db'}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all([_task("host"), _task("organic")])
        session.commit()

    _patch_database(monkeypatch, engine)
    settings = SimpleNamespace(
        MAX_CONCURRENCY=2,
        SEED=42,
        ARTIFACTS_DIR=str(tmp_path / "artifacts"),
    )
    monkeypatch.setattr(pipeline, "get_settings", lambda: settings)

    def execute_clean(
        session: Session, task: Task, llm: Any, retriever: Any
    ) -> Run:
        del llm, retriever
        run = _run(task.task_id, "clean", "pass" if task.task_id == "host" else "fail")
        session.add(run)
        session.commit()
        session.refresh(run)
        return run

    def execute_fault(
        session: Session,
        task: Task,
        fault_type: str,
        step_key: str,
        seed: int,
        llm: Any,
        retriever: Any,
    ) -> Run:
        del seed, llm, retriever
        run = _run(task.task_id, "fault", "fail")
        session.add(run)
        session.commit()
        session.add(
            Fault(
                run_id=run.run_id,
                fault_type=fault_type,
                step_key=step_key,
                params={},
            )
        )
        session.commit()
        session.refresh(run)
        return run

    def label_fault(session: Session, run_id: str, replay_fn: Any) -> Label:
        del replay_fn
        label = Label(
            run_id=run_id,
            culprit_step_key="step",
            method="bisect",
            verified=True,
            confidence=1.0,
            n_replays=1,
            matches_injection=True,
        )
        session.add(label)
        session.commit()
        return label

    def label_organic(session: Session, run_id: str, replay_fn: Any) -> Label:
        del replay_fn
        label = Label(
            run_id=run_id,
            culprit_step_key="step",
            method="counterfactual",
            verified=True,
            confidence=1.0,
            n_replays=3,
        )
        session.add(label)
        session.commit()
        return label

    monkeypatch.setattr(pipeline, "_execute_clean", execute_clean)
    monkeypatch.setattr(pipeline, "_execute_fault", execute_fault)
    monkeypatch.setattr(
        pipeline,
        "applicable_targets",
        lambda clean_run: [
            (WRONG_EXTRACTION, "extract-1"),
            (WRONG_EXTRACTION, "extract-2"),
            (WRONG_EXTRACTION, "extract-3"),
            (PLAN_CORRUPT, "plan"),
        ],
    )
    monkeypatch.setattr(pipeline, "_label_fault_run", label_fault)
    monkeypatch.setattr(pipeline, "_label_organic_run", label_organic)

    generator = pipeline.DataGenerationPipeline(llm=object(), retriever=object())
    generator.run("all")
    generator.run("all")

    with Session(engine) as session:
        assert session.exec(select(func.count()).select_from(Run)).one() == 5
        assert session.exec(select(func.count()).select_from(Fault)).one() == 3
        assert session.exec(select(func.count()).select_from(Label)).one() == 4

    report_path = tmp_path / "artifacts" / "datagen_report.json"
    report = json.loads(report_path.read_text())
    assert report["clean"] == {"pass_rate": 0.5, "passed": 1, "runs": 2}
    assert report["faults"][WRONG_EXTRACTION]["runs"] == 2
    assert report["faults"][PLAN_CORRUPT]["runs"] == 1
    assert report["labels"]["verified"] == 3
    assert report["organic_labels"] == 1


def test_task_failure_logs_and_other_tasks_continue(
    tmp_path: Path, monkeypatch: Any
) -> None:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'continue.db'}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all([_task("bad"), _task("good")])
        session.commit()

    _patch_database(monkeypatch, engine)
    monkeypatch.setattr(
        pipeline,
        "get_settings",
        lambda: SimpleNamespace(
            MAX_CONCURRENCY=2,
            SEED=42,
            ARTIFACTS_DIR=str(tmp_path / "artifacts"),
        ),
    )

    def execute_clean(
        session: Session, task: Task, llm: Any, retriever: Any
    ) -> Run:
        del llm, retriever
        if task.task_id == "bad":
            raise RuntimeError("expected failure")
        run = _run(task.task_id, "clean", "pass")
        session.add(run)
        session.commit()
        return run

    monkeypatch.setattr(pipeline, "_execute_clean", execute_clean)
    pipeline.DataGenerationPipeline(llm=object(), retriever=object()).run("clean")

    with Session(engine) as session:
        runs = list(session.exec(select(Run)).all())
    assert [run.task_id for run in runs] == ["good"]