import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from blackbox.config import Settings
from blackbox.model import explain as explain_module
from blackbox.model import predict
from blackbox.model.explain import FEATURE_TEMPLATES, explain
from blackbox.model.train import prepare_features, ranking_metrics, train_ranker
from blackbox.store.models import Prediction, Run, Step, Task


def _step(step_key: str, idx: int, answer: str) -> Step:
    return Step(
        step_id=f"step-{idx}",
        run_id="synthetic-run",
        step_key=step_key,
        idx=idx,
        name="extract",
        type="llm",
        node_id=f"q{idx}",
        attempt=0,
        deps=[],
        input={"passage_pid": f"p{idx}"},
        input_hash=f"input-{idx}",
        output={"answer": answer},
        output_hash=f"output-{idx}",
        output_text=answer,
        latency_ms=10,
        tokens_in=5,
        tokens_out=2,
        cache_hit=False,
        reused=False,
        overridden=False,
        state_snapshot={"subanswers": {f"q{idx}": answer}},
        meta={},
    )


def test_every_saved_feature_has_an_explanation_template() -> None:
    feature_path = Path(__file__).parents[1] / "artifacts" / "feature_list.json"
    feature_list = json.loads(feature_path.read_text(encoding="utf-8"))

    assert set(feature_list) <= FEATURE_TEMPLATES.keys()


def test_ranking_metrics_match_hand_computed_example() -> None:
    metrics = ranking_metrics(
        scores=[0.9, 0.1, 0.8, 0.7, 0.6],
        labels=[1, 0, 0, 1, 0],
        groups=[2, 3],
        indices=[0, 1, 0, 1, 2],
    )

    assert metrics["top_1"] == 0.5
    assert metrics["top_3"] == 1.0
    assert metrics["mrr"] == 0.75
    assert metrics["mean_idx_error"] == 0.5


def test_ranker_finds_planted_culprit_signal() -> None:
    rng = np.random.default_rng(42)
    rows: list[dict[str, object]] = []
    labels: list[int] = []
    groups = [5] * 60
    for _ in groups:
        culprit = int(rng.integers(0, 5))
        for index in range(5):
            rows.append(
                {
                    "name": "extract" if index % 2 else "retrieve",
                    "type": "llm" if index % 2 else "tool",
                    "idx": index,
                    "planted_signal": 10.0 if index == culprit else 0.0,
                    "noise": float(rng.normal()),
                }
            )
            labels.append(int(index == culprit))
    features = pd.DataFrame(rows)
    target = pd.Series(labels)

    model, categories = train_ranker(
        features.iloc[:250].reset_index(drop=True), target.iloc[:250].reset_index(drop=True), groups[:50]
    )
    from blackbox.model.train import prepare_features

    scores = model.predict(prepare_features(features.iloc[250:], categories=categories))
    metrics = ranking_metrics(scores, target.iloc[250:], groups[50:])

    assert metrics["top_1"] > 0.8


def test_explain_uses_positive_shap_contribution_and_step_evidence() -> None:
    training_features = pd.DataFrame(
        {"answer_in_passages": [value for _ in range(30) for value in (0.0, 1.0)]}
    )
    labels = pd.Series([value for _ in range(30) for value in (1, 0)])
    model, _ = train_ranker(
        training_features,
        labels,
        [2] * 30,
        params={
            "objective": "lambdarank",
            "n_estimators": 20,
            "num_leaves": 4,
            "min_child_samples": 1,
            "random_state": 42,
            "verbosity": -1,
        },
    )
    features = pd.DataFrame({"answer_in_passages": [0.0, 1.0]})
    prepared = prepare_features(features)
    scores = model.predict(prepared)
    steps = [_step("q1/extract#0", 0, "Mars"), _step("q2/extract#0", 1, "Earth")]
    order = np.argsort(-scores)
    ranking = [
        {
            "step_key": steps[index].step_key,
            "idx": steps[index].idx,
            "score": float(scores[index]),
            "rank": rank,
        }
        for rank, index in enumerate(order, start=1)
    ]

    explained = explain(
        "synthetic-run",
        ranking,
        model=model,
        features=prepared,
        steps=steps,
        feature_list=list(features.columns),
        reference_stats={},
    )

    assert explained[0]["step_key"] == "q1/extract#0"
    assert explained[0]["reasons"][0]["feature"] == "answer_in_passages"
    assert "likely cause" in explained[0]["reasons"][0]["text"]
    assert "Mars" in explained[0]["reasons"][0]["evidence"]
    assert explained[0]["reasons"][0]["contribution"] > 0
    assert explained[1]["reasons"] == []


def test_explain_skips_positive_contributions_for_non_applicable_features(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    step = _step("q1/retrieve#0", 0, "One passage").model_copy(
        update={
            "name": "retrieve",
            "type": "retrieval",
            "input": {"query": "Mars atmosphere"},
            "output": {
                "passages": [
                    {
                        "title": "Atmosphere of Mars",
                        "text": "Mars has a thin atmosphere.",
                        "score": 0.72,
                    }
                ]
            },
        }
    )
    features = pd.DataFrame(
        {"top1_score": [0.72], "final_in_subanswers": [np.nan]}
    )
    monkeypatch.setattr(
        explain_module,
        "_shap_values",
        lambda _model, _features: np.asarray([[0.4, 1.2]]),
    )

    explained = explain(
        "synthetic-run",
        [{"step_key": step.step_key, "idx": 0, "score": 1.0, "rank": 1}],
        model=object(),  # type: ignore[arg-type]
        features=features,
        steps=[step],
        feature_list=list(features.columns),
        reference_stats={},
    )

    assert [reason["feature"] for reason in explained[0]["reasons"]] == [
        "top1_score"
    ]


def test_diagnose_persists_explanations_in_temporary_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    training_features = pd.DataFrame(
        {"answer_in_passages": [value for _ in range(30) for value in (0.0, 1.0)]}
    )
    labels = pd.Series([value for _ in range(30) for value in (1, 0)])
    model, _ = train_ranker(
        training_features,
        labels,
        [2] * 30,
        params={
            "objective": "lambdarank",
            "n_estimators": 20,
            "num_leaves": 4,
            "min_child_samples": 1,
            "random_state": 42,
            "verbosity": -1,
        },
    )
    engine = create_engine(f"sqlite:///{tmp_path / 'model.db'}")
    SQLModel.metadata.create_all(engine)
    task = Task(
        task_id="synthetic-task",
        question="Which answer is grounded?",
        gold_answer="Earth",
        qtype="bridge",
        level="easy",
        split="test",
        gold_titles=[],
        distractor_pids=[],
    )
    run = Run(
        run_id="synthetic-run",
        task_id=task.task_id,
        origin="clean",
        outcome="fail",
        score_f1=0.0,
        n_steps=2,
        n_reused=0,
        n_executed=2,
        tokens_total=14,
        tokens_saved=0,
        latency_ms=20,
    )
    run_id = run.run_id
    steps = [_step("q1/extract#0", 0, "Mars"), _step("q2/extract#0", 1, "Earth")]
    with Session(engine) as session:
        session.add(task)
        session.add(run)
        session.add_all(steps)
        session.commit()

    @contextmanager
    def sessions() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    feature_frame = pd.DataFrame({"answer_in_passages": [0.0, 1.0]})
    monkeypatch.setattr(predict, "init_db", lambda: None)
    monkeypatch.setattr(predict, "get_session", sessions)
    monkeypatch.setattr(
        predict,
        "get_settings",
        lambda: Settings(
            DB_PATH=str(tmp_path / "model.db"),
            DATA_DIR=str(tmp_path / "data"),
            ARTIFACTS_DIR=str(tmp_path / "artifacts"),
        ),
    )
    monkeypatch.setattr(
        predict,
        "load_model",
        lambda: (
            model.booster_,
            ["answer_in_passages"],
            {"version": "test-model", "categories": {}},
        ),
    )
    monkeypatch.setattr(predict, "load_reference_stats", lambda _path: {})
    monkeypatch.setattr(
        predict,
        "features_for_run",
        lambda *_args, **_kwargs: feature_frame,
    )

    result = predict.diagnose(run_id)

    with Session(engine) as session:
        predictions = list(
            session.exec(
                select(Prediction)
                .where(Prediction.run_id == run_id)
                .order_by(Prediction.rank)
            ).all()
        )
    assert result["model_version"] == "test-model"
    assert predictions[0].reasons == result["ranking"][0]["reasons"]
    assert predictions[0].reasons[0]["feature"] == "answer_in_passages"