from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
from sqlmodel import Session, SQLModel, create_engine

from blackbox.incidents import engine as incident_engine
from blackbox.incidents.engine import (
    assign_incident,
    explain_incident,
    on_run_finished,
    verify_fix,
)
from blackbox.store.models import (
    Incident,
    NotificationRule,
    Prediction,
    Run,
    Step,
    Task,
)


def _run(run_id: str, task_id: str, *, origin: str = "simulated") -> Run:
    return Run(
        run_id=run_id,
        task_id=task_id,
        workspace="nimbu",
        origin=origin,
        final_answer="30 days",
        outcome="fail",
        score_f1=0.0,
        n_steps=1,
        n_reused=0,
        n_executed=1,
        tokens_total=10,
        tokens_saved=0,
        latency_ms=10,
    )


def _step(run_id: str, step_id: str | None = None) -> Step:
    return Step(
        step_id=step_id or f"step-{run_id}",
        run_id=run_id,
        step_key="q1/retrieve#0",
        idx=0,
        name="retrieve",
        type="retrieval",
        node_id="q1",
        attempt=0,
        deps=[],
        input={"query": "return window", "k": 3},
        input_hash="input",
        output={
            "passages": [
                {
                    "pid": "p_a_returns_2024",
                    "title": "Return policy (2024)",
                    "text": "Returns were allowed for 30 days.",
                    "status": "archived",
                    "score": 0.9,
                }
            ]
        },
        output_hash="output",
        output_text="Return policy (2024)",
        latency_ms=1,
        tokens_in=0,
        tokens_out=0,
        model="retriever",
        cache_hit=False,
        reused=False,
        overridden=False,
        state_snapshot={},
        meta={},
    )


def _prediction(run_id: str, score: float) -> Prediction:
    return Prediction(
        run_id=run_id,
        step_key="q1/retrieve#0",
        score=score,
        rank=1,
        model_version="test",
        reasons=[
            {
                "feature": "query_title_overlap",
                "text": "Search matched an old title.",
                "evidence": "Return policy (2024)",
                "contribution": 1.0,
            }
        ],
    )


@pytest.fixture
def session(tmp_path: Path) -> Iterator[Session]:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'incidents.db'}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session


def _seed_failure(session: Session, run_id: str, score: float) -> Run:
    task = Task(
        task_id=f"task-{run_id}",
        workspace="nimbu",
        category="returns",
        question="How long can I return this?",
        gold_answer="7 days",
        qtype="lookup",
        level="medium",
        split="test",
        gold_titles=["Return policy"],
        distractor_pids=["p_a_returns_2024"],
    )
    run = _run(run_id, task.task_id)
    session.add_all((task, run, _step(run_id), _prediction(run_id, score)))
    session.commit()
    return run


def test_same_pattern_groups_and_detects_archived_policy(session: Session) -> None:
    _seed_failure(session, "run-1", 0.7)
    _seed_failure(session, "run-2", 0.9)

    first = assign_incident("run-1", session=session)
    second = assign_incident("run-2", session=session)

    assert first.incident_id == second.incident_id
    assert second.n_runs == 2
    assert second.severity == "low"
    assert second.representative_run_id == "run-2"
    assert second.title == (
        "Returns questions answered wrong — search returned an archived policy"
    )
    explanation = explain_incident(second, session)
    assert "30 days" in explanation
    assert "7 days" in explanation
    assert "archived article ‘Return policy (2024)’" in explanation


def test_cost_override_can_raise_severity_to_high(session: Session) -> None:
    session.add(
        NotificationRule(
            workspace="nimbu",
            kind="settings",
            enabled=True,
            params={"cost_per_wrong_answer_inr": 3_000},
        )
    )
    session.commit()
    _seed_failure(session, "cost-1", 0.7)
    _seed_failure(session, "cost-2", 0.8)

    assign_incident("cost-1", session=session)
    incident = assign_incident("cost-2", session=session)

    assert incident.est_cost_inr == 6_000
    assert incident.severity == "high"


def test_verify_fix_applies_override_to_every_affected_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'verify.db'}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)

    @contextmanager
    def sessions() -> Iterator[Session]:
        with Session(engine) as db_session:
            yield db_session

    with Session(engine) as db_session:
        _seed_failure(db_session, "affected-1", 0.7)
        _seed_failure(db_session, "affected-2", 0.8)
        incident = assign_incident("affected-1", session=db_session)
        assign_incident("affected-2", session=db_session)
        repair_run = _run("repair-1", "task-affected-1", origin="repair")
        repair_run.outcome = "pass"
        repair_run.replay_spec = {
            "overrides": {
                "q1/retrieve#0": {
                    "kind": "regenerate",
                    "params": {"exclude_archived": True},
                    "fault_type": None,
                    "fault_params": {},
                }
            }
        }
        db_session.add_all((repair_run, _step("repair-1", "step-repair")))
        db_session.commit()
        incident_id = incident.incident_id

    monkeypatch.setattr(incident_engine, "get_session", sessions)
    calls: list[tuple[str, dict[str, Any]]] = []

    def replay_fn(run_id: str, **kwargs: Any) -> Run:
        calls.append((run_id, kwargs))
        result = _run(f"verified-{run_id}", f"task-{run_id}", origin="repair")
        result.outcome = "pass"
        result.tokens_saved = 12
        return result

    result = verify_fix(incident_id, "repair-1", replay_fn=replay_fn)

    assert result["n_total"] == 2
    assert result["n_passed"] == 2
    assert result["tokens_saved"] == 24
    assert {run_id for run_id, _ in calls} == {"affected-1", "affected-2"}
    assert all(
        call["overrides"]["q1/retrieve#0"].params == {"exclude_archived": True}
        for _, call in calls
    )
    with Session(engine) as db_session:
        stored = db_session.get(Incident, incident_id)
        assert stored is not None
        assert stored.status == "fix_verified"


@pytest.mark.parametrize("origin", ["bisect", "replay", "repair", "clean"])
def test_hook_ignores_non_production_origins(origin: str) -> None:
    run = _run("ignored", "task-ignored", origin=origin)

    def unexpected(_: str) -> dict[str, Any]:
        raise AssertionError("diagnosis should not run")

    assert on_run_finished(run, diagnose_fn=unexpected) is None