from types import SimpleNamespace

from sqlmodel import Session, SQLModel, create_engine
from typer.testing import CliRunner

from blackbox import cli
from blackbox.store.models import Task
from blackbox.store.repo import upsert_task


def test_prewarm_runs_complete_demo_path(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    engine = create_engine(
        f"sqlite:///{tmp_path / 'prewarm.db'}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        upsert_task(
            session,
            Task(
                task_id="demo-task",
                question="Demo question?",
                gold_answer="answer",
                qtype="bridge",
                level="easy",
                split="test",
                gold_titles=[],
                distractor_pids=[],
            ),
        )

    calls: list[str] = []
    monkeypatch.setattr(cli, "init_db", lambda: None)
    monkeypatch.setattr(cli, "get_session", lambda: Session(engine))
    monkeypatch.setattr(cli, "_llm_client", lambda: object())
    monkeypatch.setattr(
        cli,
        "_execute_clean",
        lambda *_args: SimpleNamespace(outcome="pass"),
    )

    def run_fault(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        calls.append("fault")
        return SimpleNamespace(run_id="fault-run", outcome="fail")

    def diagnose(_run_id):  # type: ignore[no-untyped-def]
        calls.append("diagnose")
        return {"ranking": [{"step_key": "q1/extract#0"}]}

    attempt = SimpleNamespace(run_id="repair-run")

    def repair(_run_id, top_k):  # type: ignore[no-untyped-def]
        calls.append(f"repair-{top_k}")
        return SimpleNamespace(attempts=[attempt], repaired=True)

    runs = {
        "fault-run": SimpleNamespace(run_id="fault-run"),
        "repair-run": SimpleNamespace(run_id="repair-run"),
    }
    monkeypatch.setattr(cli, "run_with_fault", run_fault)
    monkeypatch.setattr(cli, "diagnose", diagnose)
    monkeypatch.setattr(cli, "repair_run", repair)
    monkeypatch.setattr(cli, "get_run", lambda _session, run_id: runs.get(run_id))
    monkeypatch.setattr(
        cli, "compare_runs", lambda *_args: calls.append("compare")
    )

    result = CliRunner().invoke(
        cli.app,
        [
            "prewarm",
            "--tasks",
            "demo-task",
            "--faults",
            "WRONG_EXTRACTION@q1/extract#0",
        ],
    )

    assert result.exit_code == 0, result.output
    assert calls == ["fault", "diagnose", "repair-3", "compare"]
    assert "top-1=q1/extract#0" in result.output
    assert "repaired" in result.output


def test_prewarm_requires_one_fault_per_task() -> None:
    result = CliRunner().invoke(
        cli.app,
        [
            "prewarm",
            "--tasks",
            "task-1,task-2",
            "--faults",
            "WRONG_EXTRACTION@q1/extract#0",
        ],
    )

    assert result.exit_code == 2
    assert "same number of items" in result.output