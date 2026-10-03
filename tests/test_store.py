import json
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from blackbox.store.db import _create_engine, _normalize_database_url
from blackbox.store.hashing import sha256_json
from blackbox.store.models import Label, Run, Step, Task
from blackbox.store.repo import add_step, create_run, get_run, get_steps, upsert_task


def _task() -> Task:
    return Task(
        task_id="task-1",
        question="Were both people American?",
        gold_answer="yes",
        qtype="comparison",
        level="medium",
        split="test",
        gold_titles=["Person One", "Person Two"],
        distractor_pids=["distractor-1"],
    )


def _run() -> Run:
    return Run(
        run_id="run-1",
        task_id="task-1",
        origin="clean",
        parent_run_id=None,
        final_answer=None,
        outcome="fail",
        score_f1=0.0,
        n_steps=2,
        n_reused=0,
        n_executed=2,
        tokens_total=20,
        tokens_saved=0,
        latency_ms=100,
        replay_spec=None,
    )


def _step(idx: int) -> Step:
    input_data = {"prompt": f"step {idx}"}
    output_data = {"value": idx}
    return Step(
        step_id=f"step-{idx}",
        run_id="run-1",
        step_key="plan" if idx == 0 else "synthesize",
        idx=idx,
        name="plan" if idx == 0 else "synthesize",
        type="llm",
        node_id="root",
        attempt=0,
        deps=[] if idx == 0 else ["plan"],
        input=input_data,
        input_hash=sha256_json(input_data),
        output=output_data,
        output_hash=sha256_json(output_data),
        output_text=str(idx),
        latency_ms=50,
        tokens_in=5,
        tokens_out=5,
        model="fake",
        cache_hit=False,
        reused=False,
        overridden=False,
        state_snapshot={"plan": {}, "subanswers": {}, "attempts": {}, "final": None},
        error=None,
        meta={},
    )


def test_store_round_trip_orders_steps(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        upsert_task(session, _task())
        create_run(session, _run())
        add_step(session, _step(1))
        add_step(session, _step(0))

        assert get_run(session, "run-1") is not None
        assert [step.idx for step in get_steps(session, "run-1")] == [0, 1]


def test_hashing_is_stable_across_dict_key_order() -> None:
    first = {"alpha": 1, "nested": {"beta": 2, "gamma": [3, 4]}}
    second = {"nested": {"gamma": [3, 4], "beta": 2}, "alpha": 1}

    assert sha256_json(first) == sha256_json(second)


def test_postgres_url_selects_psycopg_driver() -> None:
    database_url = "postgresql://user:password@example.com/database"

    assert _normalize_database_url(database_url).startswith("postgresql+psycopg://")
    postgres_engine = _create_engine(database_url)
    try:
        assert postgres_engine.url.drivername == "postgresql+psycopg"
    finally:
        postgres_engine.dispose()


def test_sample_fixture_validates_against_models() -> None:
    fixture_path = (
        Path(__file__).parents[1] / "blackbox" / "api" / "fixtures" / "sample_run.json"
    )
    fixture = json.loads(fixture_path.read_text())

    task = Task.model_validate(fixture["task"])
    run = Run.model_validate(fixture["run"])
    steps = [Step.model_validate(step) for step in fixture["steps"]]
    label = Label.model_validate(fixture["label"])

    expected_edges = {
        (dependency, step.step_key) for step in steps for dependency in step.deps
    }
    actual_edges = {(edge["source"], edge["target"]) for edge in fixture["edges"]}

    assert task.task_id == run.task_id
    assert run.n_steps == len(steps)
    assert label.run_id == run.run_id
    assert expected_edges == actual_edges
    assert all(step.input_hash == sha256_json(step.input) for step in steps)
    assert all(step.output_hash == sha256_json(step.output) for step in steps)
