from collections.abc import Iterator
from pathlib import Path
from threading import Event
from typing import Any, ClassVar

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from blackbox.api import business
from blackbox.api.app import app
from blackbox.api.replay import wait_for_job
from blackbox.config import get_settings
from blackbox.notify import rules as notification_rules
from blackbox.store.models import Incident, Prediction, Run, Step, Task


class FakeMailer:
    sent: ClassVar[list[tuple[list[str], Any]]] = []

    def send(self, recipients: list[str], rendered: Any) -> None:
        self.sent.append((recipients, rendered))


@pytest.fixture
def business_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    from blackbox.store import db

    engine = create_engine(
        f"sqlite:///{tmp_path / 'business-api.db'}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(db, "engine", engine)
    monkeypatch.setenv("BLACKBOX_MOCK_API", "0")
    monkeypatch.setenv("SMTP_PASSWORD", "api-secret")
    get_settings.cache_clear()
    FakeMailer.sent.clear()
    notification_rules.worker.mailer = FakeMailer()  # type: ignore[assignment]

    task = Task(
        task_id="nimbu-api-task",
        workspace="nimbu",
        category="returns",
        question="How long can I return an item?",
        gold_answer="7 days",
        qtype="lookup",
        level="easy",
        split="test",
        gold_titles=["Return policy"],
        distractor_pids=[],
    )
    run = Run(
        run_id="nimbu-api-run",
        task_id=task.task_id,
        workspace="nimbu",
        incident_id="nimbu-incident",
        origin="simulated",
        final_answer="30 days",
        outcome="fail",
        score_f1=0.0,
        n_steps=1,
        n_reused=0,
        n_executed=1,
        tokens_total=12,
        tokens_saved=0,
        latency_ms=8,
    )
    incident = Incident(
        incident_id="nimbu-incident",
        workspace="nimbu",
        group_key="returns-retrieve",
        title="Returns questions answered wrong",
        category="returns",
        cause_step_name="retrieve",
        cause_feature="query_title_overlap",
        severity="medium",
        status="open",
        owner="",
        est_cost_inr=450,
        n_runs=1,
        representative_run_id=run.run_id,
    )
    step = Step(
        run_id=run.run_id,
        step_key="q1/retrieve#0",
        idx=0,
        name="retrieve",
        type="retrieval",
        node_id="q1",
        attempt=0,
        deps=[],
        input={},
        input_hash="input",
        output={"passages": []},
        output_hash="output",
        output_text="Return policy",
        latency_ms=1,
        tokens_in=0,
        tokens_out=0,
        cache_hit=False,
        reused=False,
        overridden=False,
        state_snapshot={},
        meta={},
    )
    prediction = Prediction(
        run_id=run.run_id,
        step_key=step.step_key,
        score=0.9,
        rank=1,
        model_version="test",
        reasons=[
            {
                "feature": "query_title_overlap",
                "text": "Search matched the wrong policy.",
                "evidence": "Return policy",
                "contribution": 1.0,
            }
        ],
    )
    with Session(engine) as session:
        session.add_all((task, run, incident, step, prediction))
        session.commit()

    class StatusMailer:
        def __init__(self, _settings: object) -> None:
            pass

        def check_connection(self) -> tuple[bool, str]:
            return False, "login failed for api-secret"

    monkeypatch.setattr(business, "Mailer", StatusMailer)
    with TestClient(app) as client:
        yield client
    get_settings.cache_clear()


def test_overview_incident_detail_and_patch(business_client: TestClient) -> None:
    overview = business_client.get("/api/overview?workspace=nimbu")
    assert overview.status_code == 200
    assert overview.json()["kpis"]["conversations"] == 1
    assert overview.json()["kpis"]["wrong"] == 1

    listed = business_client.get("/api/incidents?workspace=nimbu")
    assert listed.json()["total"] == 1
    detail = business_client.get("/api/incidents/nimbu-incident")
    assert detail.status_code == 200
    assert detail.json()["runs"][0] == {
        **detail.json()["runs"][0],
        "customer_message": "How long can I return an item?",
        "agent_reply": "30 days",
        "correct_answer": "7 days",
    }
    patched = business_client.patch(
        "/api/incidents/nimbu-incident",
        json={"status": "investigating", "owner": "Asha", "note": "Reviewing"},
    )
    assert patched.status_code == 200
    assert patched.json()["status"] == "investigating"
    assert patched.json()["owner"] == "Asha"
    invalid = business_client.patch(
        "/api/incidents/nimbu-incident",
        json={"status": "reopened", "owner": "Should not persist"},
    )
    assert invalid.status_code == 422
    detail_after_rejection = business_client.get("/api/incidents/nimbu-incident")
    assert detail_after_rejection.json()["incident"]["owner"] == "Asha"


def test_conversation_category_and_incident_link(business_client: TestClient) -> None:
    matching = business_client.get("/api/runs?workspace=nimbu&category=returns")
    assert matching.status_code == 200
    assert matching.json()["total"] == 1

    excluded = business_client.get("/api/runs?workspace=nimbu&category=shipping")
    assert excluded.status_code == 200
    assert excluded.json()["total"] == 0

    detail = business_client.get("/api/runs/nimbu-api-run?workspace=nimbu")
    assert detail.status_code == 200
    assert detail.json()["run"]["incident_id"] == "nimbu-incident"

def test_notifications_recipients_rules_and_settings(
    business_client: TestClient,
) -> None:
    status_response = business_client.get("/api/notifications/status")
    assert status_response.status_code == 200
    assert "api-secret" not in status_response.text
    assert status_response.json()["last_error"] == "login failed for ***"

    assert business_client.post(
        "/api/recipients", json={"name": "Bad", "email": "not-an-email"}
    ).status_code == 422
    created = business_client.post(
        "/api/recipients",
        json={
            "name": "Operations",
            "email": "ops@example.com",
            "workspace": "nimbu",
            "rules": ["incident_opened"],
        },
    )
    assert created.status_code == 201
    recipient_id = created.json()["recipient_id"]
    assert business_client.patch(
        f"/api/recipients/{recipient_id}", json={"active": False}
    ).json()["active"] is False

    rules = business_client.get("/api/rules?workspace=nimbu").json()
    opened = next(rule for rule in rules if rule["kind"] == "incident_opened")
    updated = business_client.put(
        f"/api/rules/{opened['rule_id']}",
        json={"enabled": True, "params": {"priority": "high"}},
    )
    assert updated.json()["params"] == {"priority": "high"}
    assert business_client.put(
        "/api/settings/business?workspace=nimbu",
        json={"cost_per_wrong_answer_inr": 700},
    ).json() == {"cost_per_wrong_answer_inr": 700}

    sent = business_client.post(
        "/api/notifications/test", json={"to": "ops@example.com"}
    )
    assert sent.json() == {"status": "sent", "error": None}
    assert FakeMailer.sent[0][0] == ["ops@example.com"]
    assert business_client.delete(f"/api/recipients/{recipient_id}").status_code == 204


def test_simulate_job_exposes_in_flight_progress(
    business_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    progress_reported = Event()
    release = Event()

    def fake_simulation(**kwargs: Any) -> dict[str, int]:
        kwargs["progress_fn"](
            {"sent": 2, "wrong": 1, "incidents_opened": 0, "emails_queued": 0}
        )
        progress_reported.set()
        assert release.wait(timeout=2)
        return {"sent": 4, "wrong": 2, "incidents_opened": 1, "emails_queued": 1}

    monkeypatch.setattr(business, "run_simulation", fake_simulation)
    response = business_client.post(
        "/api/simulate",
        json={"workspace": "nimbu", "n": 4, "failure_rate": 0.5, "seed": 9},
    )
    job_id = response.json()["job_id"]
    assert progress_reported.wait(timeout=2)
    running = business_client.get(f"/api/jobs/{job_id}").json()
    assert running["status"] == "running"
    assert running["progress"] == 0.5
    assert running["result"]["failed"] == 1
    release.set()
    wait_for_job(job_id)
    completed = business_client.get(f"/api/jobs/{job_id}").json()
    assert completed["status"] == "completed"
    assert completed["result"]["incidents_opened"] == 1