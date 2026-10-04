from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine, func, select

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