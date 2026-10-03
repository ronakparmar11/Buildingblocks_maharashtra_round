from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

from blackbox.config import Settings, get_settings
from blackbox.features.extract import build_dataset

CATEGORICAL_FEATURES = ("name", "type")
MODEL_VERSION = "p10-lambdarank-v1"
RANKER_PARAMS: dict[str, Any] = {
    "objective": "lambdarank",
    "n_estimators": 400,
    "learning_rate": 0.05,
    "num_leaves": 31,
    "min_child_samples": 5,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "random_state": 42,
    "verbosity": -1,
}


def fault_types_from_settings(settings: Settings | None = None) -> list[str]:
    raw = (settings or get_settings()).HOLDOUT_FAULTS
    return [item.strip() for item in raw.split(",") if item.strip()]


def categorical_values(frame: pd.DataFrame) -> dict[str, list[str]]:
    return {
        column: sorted(frame[column].dropna().astype(str).unique().tolist())
        for column in CATEGORICAL_FEATURES
        if column in frame
    }


def prepare_features(
    frame: pd.DataFrame,
    feature_list: Sequence[str] | None = None,
    categories: dict[str, list[str]] | None = None,
) -> pd.DataFrame:
    prepared = frame.loc[:, list(feature_list) if feature_list is not None else frame.columns].copy()
    categories = categories or categorical_values(prepared)
    for column in CATEGORICAL_FEATURES:
        if column in prepared:
            prepared[column] = pd.Categorical(
                prepared[column].astype(str), categories=categories.get(column, [])
            )
    return prepared


def _run_slices(groups: Sequence[int]) -> list[slice]:
    slices: list[slice] = []
    start = 0
    for size in groups:
        slices.append(slice(start, start + int(size)))
        start += int(size)
    return slices


def ranking_metrics(
    scores: Sequence[float],
    labels: Sequence[int],
    groups: Sequence[int],
    indices: Sequence[int] | None = None,
) -> dict[str, float]:
    score_array = np.asarray(scores, dtype=float)
    label_array = np.asarray(labels, dtype=int)
    index_array = (
        np.asarray(indices, dtype=int)
        if indices is not None
        else np.concatenate([np.arange(size) for size in groups])
    )
    ranks: list[int] = []
    index_errors: list[int] = []
    for run_slice in _run_slices(groups):
        run_labels = label_array[run_slice]
        positives = np.flatnonzero(run_labels == 1)
        if len(positives) != 1:
            continue
        order = np.argsort(-score_array[run_slice], kind="stable")
        true_position = int(positives[0])
        rank = int(np.flatnonzero(order == true_position)[0]) + 1
        ranks.append(rank)
        predicted_position = int(order[0])
        run_indices = index_array[run_slice]
        index_errors.append(
            abs(int(run_indices[predicted_position]) - int(run_indices[true_position]))
        )
    if not ranks:
        return {"top_1": 0.0, "top_3": 0.0, "mrr": 0.0, "mean_idx_error": 0.0, "n_runs": 0.0}
    return {
        "top_1": float(np.mean(np.asarray(ranks) == 1)),
        "top_3": float(np.mean(np.asarray(ranks) <= 3)),
        "mrr": float(np.mean([1.0 / rank for rank in ranks])),
        "mean_idx_error": float(np.mean(index_errors)),
        "n_runs": float(len(ranks)),
    }


def train_ranker(
    features: pd.DataFrame,
    labels: pd.Series,
    groups: Sequence[int],
    *,
    params: dict[str, Any] | None = None,
    categories: dict[str, list[str]] | None = None,
) -> tuple[lgb.LGBMRanker, dict[str, list[str]]]:
    if features.empty or not groups:
        raise ValueError("No training rows found")
    learned_categories = categories or categorical_values(features)
    prepared = prepare_features(features, categories=learned_categories)
    model = lgb.LGBMRanker(**(params or RANKER_PARAMS))
    model.fit(
        prepared,
        labels,
        group=list(groups),
        categorical_feature=[name for name in CATEGORICAL_FEATURES if name in prepared],
    )
    return model, learned_categories


def cross_validate(
    features: pd.DataFrame,
    labels: pd.Series,
    groups: Sequence[int],
    task_ids: Sequence[str],
) -> dict[str, float]:
    run_slices = _run_slices(groups)
    run_tasks = [str(task_ids[item.start]) for item in run_slices]
    unique_tasks = len(set(run_tasks))
    if unique_tasks < 2:
        return {"top_1": 0.0, "mrr": 0.0, "folds": 0.0}
    splitter = GroupKFold(n_splits=min(5, unique_tasks))
    fold_metrics: list[dict[str, float]] = []
    run_numbers = np.arange(len(groups))
    for train_runs, validation_runs in splitter.split(run_numbers, groups=run_tasks):
        train_rows = np.concatenate(
            [np.arange(run_slices[index].start, run_slices[index].stop) for index in train_runs]
        )
        validation_rows = np.concatenate(
            [np.arange(run_slices[index].start, run_slices[index].stop) for index in validation_runs]
        )
        train_groups = [groups[index] for index in train_runs]
        validation_groups = [groups[index] for index in validation_runs]
        categories = categorical_values(features.iloc[train_rows])
        model, _ = train_ranker(
            features.iloc[train_rows], labels.iloc[train_rows], train_groups, categories=categories
        )
        scores = model.predict(
            prepare_features(features.iloc[validation_rows], categories=categories)
        )
        fold_metrics.append(
            ranking_metrics(scores, labels.iloc[validation_rows], validation_groups)
        )
    return {
        "top_1": float(np.mean([item["top_1"] for item in fold_metrics])),
        "mrr": float(np.mean([item["mrr"] for item in fold_metrics])),
        "folds": float(len(fold_metrics)),
    }


def train_model(
    *,
    excluded_fault_types: Sequence[str] | None = None,
    artifact_suffix: str = "",
) -> dict[str, Any]:
    settings = get_settings()
    excluded = set(excluded_fault_types or fault_types_from_settings(settings))
    features, labels, groups, metadata = build_dataset("train")
    keep = ~metadata["fault_type"].isin(excluded)
    selected_runs = metadata.loc[keep, "run_id"].drop_duplicates().tolist()
    row_mask = metadata["run_id"].isin(selected_runs)
    features = features.loc[row_mask].reset_index(drop=True)
    labels = labels.loc[row_mask].reset_index(drop=True)
    metadata = metadata.loc[row_mask].reset_index(drop=True)
    groups = metadata.groupby("run_id", sort=False).size().astype(int).tolist()
    if not groups:
        raise ValueError("No verified, non-holdout training runs found")
    cv = cross_validate(features, labels, groups, metadata["task_id"].tolist())
    model, categories = train_ranker(features, labels, groups)
    artifact_dir = Path(settings.ARTIFACTS_DIR)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    suffix = f"_{artifact_suffix}" if artifact_suffix else ""
    model_path = artifact_dir / f"model{suffix}.txt"
    model.booster_.save_model(str(model_path))
    feature_list = features.columns.tolist()
    (artifact_dir / f"feature_list{suffix}.json").write_text(
        json.dumps(feature_list, indent=2), encoding="utf-8"
    )
    meta = {
        "version": MODEL_VERSION if not artifact_suffix else f"{MODEL_VERSION}-{artifact_suffix}",
        "created_at": datetime.now(UTC).isoformat(),
        "train_runs": len(groups),
        "train_rows": len(features),
        "train_tasks": metadata["task_id"].nunique(),
        "excluded_fault_types": sorted(excluded),
        "categories": categories,
        "cv": cv,
    }
    (artifact_dir / f"model_meta{suffix}.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )
    return meta