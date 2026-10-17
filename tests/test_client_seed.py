from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine, func, select

from blackbox.repair.repair import repair
from blackbox.replay.engine import replay
from blackbox.store.models import Incident, Prediction, Run, Step, Task
from blackbox.workspaces.seed import CLIENT_SCENARIOS, seed_demo_clients


def test_seed_demo_clients_is_complete_and_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from blackbox.store import db

    engine = create_engine(f"sqlite:///{tmp_path / 'clients.db'}")
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(db, "engine", engine)

    first = seed_demo_clients()
    second = seed_demo_clients()

    assert first == second == {
        "clients": 5,
        "tasks": 10,
        "runs": 90,
        "incidents": 10,
    }
    with Session(engine) as session:
        for workspace in CLIENT_SCENARIOS:
            assert session.exec(
                select(func.count()).select_from(Run).where(Run.workspace == workspace)
            ).one() == 18
            assert session.exec(
                select(func.count()).select_from(Incident).where(Incident.workspace == workspace)
            ).one() == 2
        assert session.exec(select(func.count()).select_from(Step)).one() == 90
        assert session.exec(select(func.count()).select_from(Prediction)).one() == 30
        assert session.exec(select(func.count()).select_from(Task)).one() == 10


def test_seeded_failure_repairs_without_a_live_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from blackbox.store import db

    engine = create_engine(f"sqlite:///{tmp_path / 'repair.db'}")
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(db, "engine", engine)
    seed_demo_clients()

    result = repair("demo-aavya-run-01")

    assert result.repaired
    assert result.winning_step_key == "support/retrieve#0"
    assert len(result.attempts) == 1
    with Session(engine) as session:
        repaired = session.get(Run, result.winning_run_id)
        assert repaired is not None
        assert repaired.origin == "repair"
        assert repaired.parent_run_id == "demo-aavya-run-01"
        assert repaired.outcome == "pass"
        assert repaired.final_answer == (
            "No, opened skincare products cannot be returned."
        )


def test_seeded_failure_replays_without_a_live_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from blackbox.store import db

    engine = create_engine(f"sqlite:///{tmp_path / 'replay.db'}")
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(db, "engine", engine)
    seed_demo_clients()

    replayed = replay("demo-aavya-run-01")

    assert replayed.origin == "replay"
    assert replayed.parent_run_id == "demo-aavya-run-01"
    assert replayed.outcome == "pass"
    assert replayed.final_answer == "No, opened skincare products cannot be returned."