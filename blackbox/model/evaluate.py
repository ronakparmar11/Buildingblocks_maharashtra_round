from __future__ import annotations

import json
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sqlmodel import select

from blackbox.config import get_settings
from blackbox.faults.library import FAULT_TYPES
from blackbox.features.extract import build_dataset
from blackbox.llm.base import LLMClient
from blackbox.llm.gemini import GeminiLLM
from blackbox.llm.groq import GroqLLM
from blackbox.model.baselines import (
    heuristic_scores,
    judge_ranking,
    last_step_scores,
    random_scores,
)
from blackbox.model.predict import load_model
from blackbox.model.train import (
    fault_types_from_settings,
    prepare_features,
    ranking_metrics,
    train_model,
)
from blackbox.repair.repair import repair as repair_run
from blackbox.sdk.cassette import Cassette
from blackbox.store.db import get_session
from blackbox.store.models import Label, Run, Step, Task
from blackbox.store.repo import get_predictions


def _groups(metadata: pd.DataFrame) -> list[int]:
    return metadata.groupby("run_id", sort=False).size().astype(int).tolist()


def _evaluate_scores(
    scores: Sequence[float], labels: pd.Series, groups: Sequence[int], features: pd.DataFrame
) -> dict[str, float]:
    return ranking_metrics(scores, labels, groups, features["idx"].astype(int).tolist())


def _model_metrics(
    features: pd.DataFrame,
    labels: pd.Series,
    groups: Sequence[int],
    *,
    suffix: str = "",
    feature_latency_ms: float = 0.0,
) -> dict[str, float]:
    if features.empty:
        return {
            "top_1": 0.0,
            "top_3": 0.0,
            "mrr": 0.0,
            "mean_idx_error": 0.0,
            "n_runs": 0.0,
            "latency_ms": 0.0,
        }
    model, feature_list, metadata = load_model(suffix)
    started = time.perf_counter()
    scores = model.predict(
        prepare_features(features, feature_list, metadata.get("categories", {}))
    )
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    metrics = _evaluate_scores(scores, labels, groups, features)
    metrics["latency_ms"] = (
        elapsed_ms / len(groups) + feature_latency_ms if groups else 0.0
    )
    return metrics


def _baseline_rows(
    set_name: str,
    features: pd.DataFrame,
    labels: pd.Series,
    groups: Sequence[int],
    feature_latency_ms: float,
) -> list[dict[str, Any]]:
    if not groups:
        return []
    random_results = [
        _evaluate_scores(random_scores(groups, seed), labels, groups, features)
        for seed in range(20)
    ]
    random_average = {
        key: float(np.mean([item[key] for item in random_results]))
        for key in random_results[0]
    }
    candidates = {
        "Model": _model_metrics(
            features, labels, groups, feature_latency_ms=feature_latency_ms
        ),
        "Random (20 seeds)": random_average,
        "Last step": _evaluate_scores(last_step_scores(features), labels, groups, features),
        "Heuristic": _evaluate_scores(heuristic_scores(features), labels, groups, features),
    }
    return [{"set": set_name, "method": name, **metrics} for name, metrics in candidates.items()]


def _judge_client() -> LLMClient:
    settings = get_settings()
    if settings.LLM_PROVIDER == "gemini":
        return GeminiLLM()
    if settings.LLM_PROVIDER == "groq":
        return GroqLLM()
    raise ValueError("LLM-as-judge requires LLM_PROVIDER=gemini or groq")


def _judge_rows(
    metadata: pd.DataFrame,
    labels: pd.Series,
    features: pd.DataFrame,
    limit: int,
) -> list[dict[str, Any]]:
    if limit <= 0 or metadata.empty:
        return []
    selected_run_ids = metadata["run_id"].drop_duplicates().iloc[:limit].tolist()
    client = _judge_client()
    scores = np.full(len(metadata), -4.0)
    selected_mask = metadata["run_id"].isin(selected_run_ids)
    with get_session() as session:
        cassette = Cassette(session)
        for run_id in selected_run_ids:
            steps = list(
                session.exec(
                    select(Step).where(Step.run_id == run_id).order_by(Step.idx)
                ).all()
            )
            ranking = judge_ranking(steps, client, cassette)
            score_by_key = {step_key: 3.0 - rank for rank, step_key in enumerate(ranking)}
            run_rows = metadata.index[metadata["run_id"] == run_id]
            for row_index in run_rows:
                scores[row_index] = score_by_key.get(
                    str(metadata.at[row_index, "step_key"]), -1.0
                )
    selected_metadata = metadata.loc[selected_mask].reset_index(drop=True)
    selected_features = features.loc[selected_mask].reset_index(drop=True)
    metrics = _evaluate_scores(
        scores[selected_mask.to_numpy()],
        labels.loc[selected_mask].reset_index(drop=True),
        _groups(selected_metadata),
        selected_features,
    )
    return [{"set": "all", "method": "LLM-as-judge", **metrics}]


def _per_fault(
    features: pd.DataFrame, labels: pd.Series, metadata: pd.DataFrame
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for fault_type in metadata["fault_type"].drop_duplicates():
        run_ids = metadata.loc[metadata["fault_type"] == fault_type, "run_id"].unique()
        mask = metadata["run_id"].isin(run_ids)
        subset_metadata = metadata.loc[mask]
        metrics = _model_metrics(
            features.loc[mask].reset_index(drop=True),
            labels.loc[mask].reset_index(drop=True),
            _groups(subset_metadata),
        )
        rows.append({"fault_type": fault_type, **metrics})
    return rows


def _replay_and_bisect_metrics() -> tuple[dict[str, float], dict[str, float]]:
    with get_session() as session:
        replay_runs = list(
            session.exec(
                select(Run)
                .join(Task, Task.task_id == Run.task_id)
                .where(Run.origin == "replay", Task.split == "test")
            ).all()
        )
        labels = list(
            session.exec(
                select(Label, Run)
                .join(Run, Run.run_id == Label.run_id)
                .join(Task, Task.task_id == Run.task_id)
                .where(Task.split == "test")
            ).all()
        )
    replay = {
        "avg_pct_reused": float(np.mean([run.n_reused / run.n_steps for run in replay_runs if run.n_steps])) if replay_runs else 0.0,
        "avg_tokens_saved": float(np.mean([run.tokens_saved for run in replay_runs])) if replay_runs else 0.0,
        "n_replays": float(len(replay_runs)),
    }
    bisect = {
        "avg_replays": float(np.mean([label.n_replays for label, _ in labels])) if labels else 0.0,
        "avg_steps": float(np.mean([run.n_steps for _, run in labels])) if labels else 0.0,
        "n_labels": float(len(labels)),
    }
    return replay, bisect


def _repair_metrics(limit: int = 100) -> dict[str, float]:
    capped_limit = max(0, min(limit, 100))
    with get_session() as session:
        run_ids = list(
            session.exec(
                select(Run.run_id)
                .join(Task, Task.task_id == Run.task_id)
                .join(Label, Label.run_id == Run.run_id)
                .where(
                    Run.outcome == "fail",
                    Run.origin.in_(("clean", "fault", "organic")),
                    Task.split == "test",
                )
                .order_by(Run.created_at)
                .limit(capped_limit)
            ).all()
        )
    results = [repair_run(run_id, top_k=3) for run_id in run_ids]
    top_1_successes = 0
    top_3_successes = 0
    reused: list[float] = []
    with get_session() as session:
        for result in results:
            rank_by_step = {
                prediction.step_key: prediction.rank
                for prediction in get_predictions(session, result.run_id)
            }
            winning_rank = rank_by_step.get(result.winning_step_key or "")
            top_1_successes += winning_rank == 1
            top_3_successes += winning_rank is not None and winning_rank <= 3
            reused.extend(attempt.pct_reused for attempt in result.attempts)
    count = len(results)
    return {
        "success_top_1": top_1_successes / count if count else 0.0,
        "success_top_3": top_3_successes / count if count else 0.0,
        "avg_candidates": float(
            np.mean([len(result.attempts) for result in results])
        )
        if results
        else 0.0,
        "avg_pct_reused": float(np.mean(reused)) if reused else 0.0,
        "n_runs": float(count),
    }


def _markdown_table(rows: list[dict[str, Any]], columns: Sequence[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    body = [
        "| "
        + " | ".join(
            f"{row.get(column, 0):.3f}" if isinstance(row.get(column), float) else str(row.get(column, ""))
            for column in columns
        )
        + " |"
        for row in rows
    ]
    return "\n".join([header, separator, *body])


def evaluate(
    *, judge_limit: int = 120, lofo: bool = True, repair: bool = False
) -> dict[str, Any]:
    holdouts = set(fault_types_from_settings())
    feature_started = time.perf_counter()
    features, labels, _, metadata = build_dataset("test", include_organic=True)
    feature_elapsed_ms = (time.perf_counter() - feature_started) * 1000.0
    total_runs = metadata["run_id"].nunique() if not metadata.empty else 0
    feature_latency_ms = feature_elapsed_ms / total_runs if total_runs else 0.0
    seen_mask = ~metadata["fault_type"].isin(holdouts | {"organic"})
    held_mask = metadata["fault_type"].isin(holdouts)
    organic_mask = metadata["fault_type"].eq("organic")
    sets = {"A": seen_mask, "B": held_mask, "C": organic_mask}
    baseline_rows: list[dict[str, Any]] = []
    for name, mask in sets.items():
        selected_metadata = metadata.loc[mask]
        baseline_rows.extend(
            _baseline_rows(
                name,
                features.loc[mask].reset_index(drop=True),
                labels.loc[mask].reset_index(drop=True),
                _groups(selected_metadata),
                feature_latency_ms,
            )
        )
    baseline_rows.extend(_judge_rows(metadata, labels, features, judge_limit))
    per_fault = _per_fault(features, labels, metadata) if not metadata.empty else []
    lofo_rows: list[dict[str, Any]] = []
    if lofo:
        for fault_type in FAULT_TYPES:
            mask = metadata["fault_type"].eq(fault_type)
            subset_metadata = metadata.loc[mask]
            if subset_metadata.empty:
                lofo_rows.append(
                    {"fault_type": fault_type, "n_runs": 0.0, "status": "no_test_runs"}
                )
                continue
            suffix = f"lofo_{fault_type.lower()}"
            try:
                train_model(excluded_fault_types=[fault_type], artifact_suffix=suffix)
            except ValueError as error:
                lofo_rows.append(
                    {
                        "fault_type": fault_type,
                        "n_runs": float(subset_metadata["run_id"].nunique()),
                        "status": str(error),
                    }
                )
                continue
            metrics = _model_metrics(
                features.loc[mask].reset_index(drop=True),
                labels.loc[mask].reset_index(drop=True),
                _groups(subset_metadata),
                suffix=suffix,
                feature_latency_ms=feature_latency_ms,
            )
            lofo_rows.append({"fault_type": fault_type, **metrics})
    replay, bisect = _replay_and_bisect_metrics()
    model_a = next(
        (row for row in baseline_rows if row["set"] == "A" and row["method"] == "Model"),
        {},
    )
    result = {
        "kpis": {
            "top_1": model_a.get("top_1", 0.0),
            "top_3": model_a.get("top_3", 0.0),
            "mrr": model_a.get("mrr", 0.0),
            "latency_ms": model_a.get("latency_ms", 0.0),
        },
        "tables": {"baselines": baseline_rows, "lofo": lofo_rows, "per_fault": per_fault},
        "replay": replay,
        "bisect": bisect,
        "repair": _repair_metrics() if repair else {"status": "not_run"},
    }
    artifact_dir = Path(get_settings().ARTIFACTS_DIR)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "eval.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    markdown = "# Model evaluation\n\n## Baselines\n\n" + _markdown_table(
        baseline_rows, ("set", "method", "top_1", "top_3", "mrr", "mean_idx_error", "n_runs")
    )
    (artifact_dir / "eval.md").write_text(markdown + "\n", encoding="utf-8")
    return result