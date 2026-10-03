import numpy as np
import pandas as pd

from blackbox.model.train import ranking_metrics, train_ranker


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