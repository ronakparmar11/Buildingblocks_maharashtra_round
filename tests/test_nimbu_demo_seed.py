from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from blackbox.store.models import Incident, Prediction, Run, Step, Task
from blackbox.workspaces.nimbu.demo_seed import seed_nimbu_demo_data


def test_nimbu_demo_seed_is_complete_and_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from blackbox.store import db

    engine = create_engine(f"sqlite:///{tmp_path / 'nimbu-demo.db'}")
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(db, "engine", engine)
    with Session(engine) as session:
        session.add_all(
            Task(
                task_id=f"task-{category}",
                workspace="nimbu",
                category=category,
                question=f"Example {category} question",
                gold_answer=f"Correct {category} answer",
                qtype="lookup",
                level="medium",
                split="test",
                gold_titles=[f"{category.title()} policy"],
                distractor_pids=[],
            )
            for category in ("refunds", "shipping", "returns", "payments")
        )
        session.commit()

    first = seed_nimbu_demo_data(run_count=24)
    second = seed_nimbu_demo_data(run_count=24)

    assert first.created_runs == 24
    assert first.created_incidents == 4
    assert second.created_runs == 0
    assert second.created_incidents == 0
    with Session(engine) as session:
        runs = list(session.exec(select(Run)).all())
        assert len(runs) == 24
        assert sum(run.outcome == "pass" for run in runs) == 20
        assert sum(run.outcome == "fail" for run in runs) == 4
        assert len(session.exec(select(Step)).all()) == 120
        assert len(session.exec(select(Prediction)).all()) == 4
        incidents = list(session.exec(select(Incident)).all())
        assert len(incidents) == 4
        assert sum(incident.n_runs for incident in incidents) == 4