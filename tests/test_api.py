import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from blackbox.agent.agent import run_agent
from blackbox.api import app
from blackbox.api.common import load_fixture
from blackbox.api.schemas import (
    DiagnosisResponse,
    EvalResponse,
    FleetResponse,
    RepairResponse,
    RunDetailResponse,
)
from blackbox.config import get_settings
from blackbox.corpus.retriever import Retriever
from blackbox.llm.fake import FakeLLM
from blackbox.sdk.cassette import Cassette
from blackbox.sdk.context import ExecutionContext
from blackbox.sdk.tracer import Tracer
from blackbox.store.models import Prediction, Task
from blackbox.store.repo import get_steps, upsert_task

RUN_ID = "r_demo_failed_comparison"
TASK_ID = "5a8b57f25542995d1e6f1371"


class FixtureRetriever(Retriever):
    def search(self, query: str, k: int = 3) -> list[dict[str, Any]]:
        return [
            {
                "pid": "p-test",
                "title": "Test evidence",
                "text": f"Evidence for {query}",
                "score": 1.0,
            }
        ][:k]


@pytest.fixture
def mock_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("BLACKBOX_MOCK_API", "1")
    get_settings.cache_clear()
    with TestClient(app) as client:
        yield client
    get_settings.cache_clear()


def test_mock_fixtures_validate_against_response_models() -> None:
    sample = load_fixture("sample_run.json")
    fixture = load_fixture("mock_api.json")

    RunDetailResponse.model_validate(sample)
    DiagnosisResponse.model_validate(fixture["diagnosis"])
    RepairResponse.model_validate(fixture["repair"])
    EvalResponse.model_validate(fixture["eval"])
    FleetResponse.model_validate(fixture["fleet"])
    assert fixture["repair"]["attempts"][0]["strategy"] == (
        "Use only the sub-answers"
    )


def test_evaluation_prefers_workspace_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from blackbox.api.eval import get_evaluation

    (tmp_path / "eval.json").write_text(
        json.dumps({"test_questions": 0}), encoding="utf-8"
    )
    (tmp_path / "eval_nimbu.json").write_text(
        json.dumps({"test_questions": 14}), encoding="utf-8"
    )
    monkeypatch.setenv("BLACKBOX_MOCK_API", "0")
    monkeypatch.setenv("ARTIFACTS_DIR", str(tmp_path))
    get_settings.cache_clear()

    assert get_evaluation("nimbu").root["test_questions"] == 14
    assert get_evaluation("hotpot").root["test_questions"] == 0

    get_settings.cache_clear()


def test_every_mock_endpoint(mock_client: TestClient) -> None:
    requests = [
        ("get", "/api/runs", None),
        ("get", f"/api/runs/{RUN_ID}", None),
        ("get", f"/api/runs/{RUN_ID}/diagnosis", None),
        (
            "post",
            f"/api/runs/{RUN_ID}/replay",
            {
                "overrides": {
                    "synthesize": {
                        "kind": "set_output",
                        "output": {"answer": "yes"},
                    }
                }
            },
        ),
        ("get", f"/api/runs/{RUN_ID}/blast-radius?step_key=plan", None),
        ("post", f"/api/runs/{RUN_ID}/repair", {"top_k": 3}),
        ("get", f"/api/compare?a={RUN_ID}&b=r_demo_replay", None),
        ("get", "/api/eval", None),
        ("get", "/api/fleet?split=test", None),
        ("get", "/api/tasks?split=test", None),
        ("get", f"/api/tasks/{TASK_ID}/fault-targets", None),
        ("post", "/api/live/run", {"task_id": TASK_ID, "fault": None}),
        ("get", "/api/health", None),
    ]
    for method, path, body in requests:
        caller = getattr(mock_client, method)
        response = caller(path, json=body) if body is not None else caller(path)
        assert response.status_code == 200, (path, response.text)

    job_id = mock_client.post(
        f"/api/runs/{RUN_ID}/repair/jobs", json={"top_k": 3}
    ).json()["job_id"]
    job_response = mock_client.get(f"/api/jobs/{job_id}")
    assert job_response.status_code == 200
    assert job_response.json()["status"] in {"queued", "running", "completed"}

    live = mock_client.post(
        "/api/live/run", json={"task_id": TASK_ID, "fault": None}
    ).json()
    assert mock_client.get(f"/api/jobs/{live['run_id']}").status_code == 200


def test_cors_allows_frontend_origin(mock_client: TestClient) -> None:
    response = mock_client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "http://localhost:5173"
    )


def test_failed_job_exposes_demo_recording_message(mock_client: TestClient) -> None:
    from blackbox.api.replay import submit_job, wait_for_job
    from blackbox.sdk.cassette import CassetteMissError

    message = (
        "This step isn't in the demo recording. Pick one of the prepared "
        "demo questions in Live lab."
    )

    def miss() -> dict[str, Any]:
        raise CassetteMissError(message)

    job_id = submit_job(miss)
    with pytest.raises(CassetteMissError, match=message):
        wait_for_job(job_id)
    response = mock_client.get(f"/api/jobs/{job_id}")

    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["result"] == {"error": message}


def test_diagnosis_feature_error_returns_422(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from contextlib import contextmanager

    from blackbox.api import runs as runs_api
    from blackbox.model import predict

    class StubSession:
        def get(self, _model: object, _run_id: str) -> object:
            return object()

    @contextmanager
    def session() -> Iterator[StubSession]:
        yield StubSession()

    monkeypatch.setattr(runs_api, "mock_mode", lambda: False)
    monkeypatch.setattr(runs_api, "get_session", session)
    monkeypatch.setattr(runs_api, "get_predictions", lambda *_args: [])
    monkeypatch.setattr(
        predict,
        "diagnose",
        lambda _run_id: (_ for _ in ()).throw(KeyError("missing features")),
    )

    with pytest.raises(HTTPException) as raised:
        runs_api.get_diagnosis("incomplete-run")

    assert raised.value.status_code == 422
    assert "missing features" in str(raised.value.detail)


def test_real_mode_uses_temp_database_seeded_with_fake_llm(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from blackbox.store import db

    engine = create_engine(
        f"sqlite:///{tmp_path / 'api.db'}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(db, "engine", engine)
    monkeypatch.setenv("BLACKBOX_MOCK_API", "0")
    monkeypatch.setenv("DEMO_AUTH_ENABLED", "0")
    monkeypatch.setenv("ARTIFACTS_DIR", str(tmp_path))
    get_settings.cache_clear()
    (tmp_path / "eval.json").write_text(
        json.dumps({"kpis": {}, "tables": {}}), encoding="utf-8"
    )
    (tmp_path / "model_meta.json").write_text(
        json.dumps({"version": "test-model"}), encoding="utf-8"
    )

    task = Task(
        task_id="api-real-task",
        question="What is the test answer?",
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
                {"id": "q1", "text": "Find the test answer", "deps": []}
            ],
        },
        "Find the test answer": {
            "answer": "wrong",
            "evidence_pid": "p-test",
            "evidence_sentence": "Evidence",
        },
        "[CHECK]": {"supported": True, "reason": "direct"},
        "[SYNTHESIZE]": {"answer": "wrong"},
    }
    with Session(engine) as session:
        stored_task = upsert_task(session, task)
        run = run_agent(
            stored_task,
            ExecutionContext(
                run_id="api-real-run",
                task=stored_task,
                origin="clean",
                tracer=Tracer(session, Cassette(session), llm=FakeLLM(script)),
                retriever=FixtureRetriever(),
            ),
        )
        culprit = next(
            step for step in get_steps(session, run.run_id) if step.name == "synthesize"
        )
        session.add(
            Prediction(
                run_id=run.run_id,
                step_key=culprit.step_key,
                score=0.9,
                rank=1,
                model_version="test-model",
                reasons=[],
            )
        )
        session.commit()
        seeded_run_id = run.run_id

    with TestClient(app) as client:
        assert client.get("/api/runs").json()["total"] == 1
        detail = client.get(f"/api/runs/{seeded_run_id}")
        assert detail.status_code == 200
        assert detail.json()["run"]["run_id"] == seeded_run_id
        diagnosis = client.get(f"/api/runs/{seeded_run_id}/diagnosis")
        assert diagnosis.json()["ranking"][0]["step_key"] == "synthesize"
        assert (
            client.get(f"/api/compare?a={seeded_run_id}&b={seeded_run_id}").status_code
            == 200
        )
        assert client.get("/api/eval").status_code == 200
        assert client.get("/api/fleet?split=test").json()["total_failed"] == 1
        assert client.get("/api/tasks?split=test").status_code == 200
        assert client.get(f"/api/tasks/{task.task_id}/fault-targets").status_code == 200
        health = client.get("/api/health").json()
        assert health["model_version"] == "test-model"
        assert health["n_runs"] == 1
    get_settings.cache_clear()