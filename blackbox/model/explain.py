from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd

from blackbox.features.reference import ReferenceStats
from blackbox.store.models import Step

FALLBACK_TEMPLATE = "An unusual {feature} value is a likely cause."

FEATURE_TEMPLATES: dict[str, str] = {
    "name": "The learned risk for this step kind is a likely cause.",
    "type": "The learned risk for this execution type is a likely cause.",
    "idx": "This step's position in the run is a likely cause.",
    "rel_pos": "This step's relative position in the run is a likely cause.",
    "n_steps": "The run length at this step is a likely cause.",
    "dag_depth": "This step's dependency depth is a likely cause.",
    "n_children": "The number of direct consumers is a likely cause.",
    "n_descendants": "The number of downstream consumers is a likely cause.",
    "is_ancestor_of_final": "This step feeding the final answer is a likely cause.",
    "attempt": "This retry attempt is a likely cause.",
    "node_retries": "The number of attempts on this node is a likely cause.",
    "node_feeds_other": "This node feeding another subquestion is a likely cause.",
    "latency_z": "Unusual step latency is a likely cause.",
    "tokens_out_z": "Unusual output token usage is a likely cause.",
    "output_len_z": "Unusual output length is a likely cause.",
    "top1_score": "Retrieval confidence is a likely cause.",
    "mean_score": "Average retrieval confidence is a likely cause.",
    "score_gap": "The retrieval score margin is a likely cause.",
    "top1_score_z": "Retrieval confidence far from successful runs is a likely cause.",
    "query_title_overlap": "Poor query and title alignment is a likely cause.",
    "n_unique_titles": "The retrieved title diversity is a likely cause.",
    "passage_len_mean_z": "Unusual retrieved passage length is a likely cause.",
    "answer_in_passages": "Missing passage grounding is a likely cause.",
    "answer_fuzzy": "Weak answer and passage similarity is a likely cause.",
    "evidence_in_passages": "Missing cited evidence in the passage is a likely cause.",
    "checked_unsupported": "A downstream unsupported check is a likely cause.",
    "check_supported": "The check result is a likely cause.",
    "final_in_subanswers": "Poor final answer agreement with sub-answers is a likely cause.",
    "yesno_mismatch": "A yes or no format mismatch is a likely cause.",
    "n_subq": "The number of planned subquestions is a likely cause.",
    "plan_has_dep": "The plan's dependency structure is a likely cause.",
    "subq_question_sim": "Weak subquestion alignment with the question is a likely cause.",
    "plan_title_mention": "Weak entity coverage in the plan is a likely cause.",
    "io_cosine": "Weak input and output semantic alignment is a likely cause.",
    "output_question_cosine": "Weak output and question semantic alignment is a likely cause.",
    "output_consumed": "This output being consumed downstream is a likely cause.",
}

_REFERENCE_METRICS = {
    "latency_z": "latency",
    "tokens_out_z": "tokens_out",
    "output_len_z": "output_len",
    "top1_score_z": "top1_score",
    "passage_len_mean_z": "passage_len",
}


def _short(value: object, limit: int = 180) -> str:
    text = str(value).replace("\n", " ").strip()
    return text if len(text) <= limit else f"{text[: limit - 3]}..."


def _passages(step: Step, steps_by_key: dict[str, Step]) -> list[dict[str, Any]]:
    pending = [step.step_key]
    visited: set[str] = set()
    retrievals: list[Step] = []
    while pending:
        step_key = pending.pop()
        if step_key in visited or step_key not in steps_by_key:
            continue
        visited.add(step_key)
        candidate = steps_by_key[step_key]
        if candidate.name == "retrieve":
            retrievals.append(candidate)
        pending.extend(candidate.deps)
    if not retrievals:
        return []
    raw = max(retrievals, key=lambda item: item.idx).output.get("passages", [])
    return [item for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []


def _check_reasons(step: Step, steps: Sequence[Step]) -> list[str]:
    reasons: list[str] = []
    for candidate in steps:
        supported = candidate.output.get("supported", candidate.output.get("valid"))
        if candidate.name == "check" and candidate.node_id == step.node_id and supported is False:
            reason = candidate.output.get("reason", candidate.output_text)
            if reason:
                reasons.append(_short(reason))
    return reasons


def _reference_mean(
    feature: str, step: Step, reference_stats: ReferenceStats
) -> float | None:
    metric = _REFERENCE_METRICS.get(feature)
    value = reference_stats.get(step.name, {}).get(metric or "", {}).get("mean")
    return float(value) if isinstance(value, (int, float)) else None


def _evidence(
    feature: str,
    value: object,
    step: Step,
    steps: Sequence[Step],
    reference_stats: ReferenceStats,
) -> str:
    passages = _passages(step, {item.step_key: item for item in steps})
    titles = [_short(item.get("title", ""), 80) for item in passages if item.get("title")]
    scores = [float(item["score"]) for item in passages if isinstance(item.get("score"), (int, float))]
    answer = step.output.get("answer", step.output_text)
    if feature in {"top1_score", "mean_score", "score_gap", "top1_score_z"}:
        evidence = f"Scores: {scores or 'none'}"
    elif feature == "query_title_overlap":
        evidence = f"Query: {_short(step.input.get('query', ''))}; titles: {titles or 'none'}"
    elif feature in {"n_unique_titles", "passage_len_mean_z"}:
        evidence = f"Titles: {titles or 'none'}"
    elif feature in {"answer_in_passages", "answer_fuzzy", "evidence_in_passages"}:
        evidence = f"Answer: {_short(answer)}; titles: {titles or 'none'}"
    elif feature == "checked_unsupported":
        evidence = f"Check reason: {', '.join(_check_reasons(step, steps)) or 'none'}"
    elif feature == "check_supported":
        evidence = f"Check result: {_short(step.output)}"
    elif feature in {"final_in_subanswers", "yesno_mismatch"}:
        evidence = (
            f"Final answer: {_short(answer)}; "
            f"sub-answers: {_short(step.input.get('subanswers', {}))}"
        )
    elif feature in {"n_subq", "plan_has_dep", "subq_question_sim", "plan_title_mention"}:
        evidence = f"Plan: {_short(step.output.get('subquestions', step.output))}"
    elif feature == "n_descendants":
        evidence = f"Downstream steps: {_short(value)}"
    else:
        evidence = f"{feature}: {_short(value)}; output: {_short(step.output_text)}"
    reference_mean = _reference_mean(feature, step, reference_stats)
    if reference_mean is not None:
        evidence += f"; successful-run mean: {reference_mean:.2f}"
    return evidence


def _shap_values(
    model: lgb.Booster | lgb.LGBMRanker, features: pd.DataFrame
) -> np.ndarray:
    import shap

    booster = model.booster_ if isinstance(model, lgb.LGBMRanker) else model
    values = shap.TreeExplainer(booster).shap_values(features)
    if isinstance(values, list):
        values = values[-1]
    return np.asarray(values, dtype=float)


def explain(
    run_id: str,
    ranking: Sequence[dict[str, Any]],
    top_n_steps: int = 3,
    top_n_reasons: int = 3,
    *,
    model: lgb.Booster | lgb.LGBMRanker | None = None,
    features: pd.DataFrame | None = None,
    steps: Sequence[Step] | None = None,
    feature_list: Sequence[str] | None = None,
    reference_stats: ReferenceStats | None = None,
) -> list[dict[str, Any]]:
    """Attach positive SHAP reasons to the highest-ranked steps in a run."""
    provided = (model, features, steps, feature_list, reference_stats)
    if all(item is None for item in provided):
        from sqlmodel import select

        from blackbox.config import get_settings
        from blackbox.features.extract import features_for_run
        from blackbox.features.reference import load_reference_stats
        from blackbox.model.predict import load_model
        from blackbox.model.train import prepare_features
        from blackbox.store.db import get_session, init_db
        from blackbox.store.models import Run, Task

        init_db()
        settings = get_settings()
        model, loaded_features, metadata = load_model()
        feature_list = loaded_features
        with get_session() as session:
            run = session.get(Run, run_id)
            if run is None:
                raise ValueError(f"Unknown run id: {run_id}")
            task = session.get(Task, run.task_id)
            if task is None:
                raise ValueError(f"Unknown task id: {run.task_id}")
            steps = list(
                session.exec(
                    select(Step).where(Step.run_id == run_id).order_by(Step.idx)
                ).all()
            )
        reference_stats = load_reference_stats()
        raw_features = features_for_run(
            run, steps, reference_stats, question=task.question, settings=settings
        )
        features = prepare_features(
            raw_features, feature_list, metadata.get("categories", {})
        )
    elif any(item is None for item in provided):
        raise ValueError("Explanation inputs must be provided together")

    assert model is not None
    assert features is not None
    assert steps is not None
    assert feature_list is not None
    assert reference_stats is not None
    contributions = _shap_values(model, features)
    row_by_key = {step.step_key: index for index, step in enumerate(steps)}
    step_by_key = {step.step_key: step for step in steps}
    explained = [dict(item, reasons=[]) for item in ranking]
    for item in explained[:top_n_steps]:
        step_key = str(item["step_key"])
        row_index = row_by_key[step_key]
        positive: list[tuple[str, float]] = []
        for index, contribution in enumerate(contributions[row_index]):
            feature = feature_list[index]
            value = features.iloc[row_index][feature]
            if contribution > 0 and not pd.isna(value):
                positive.append((feature, float(contribution)))
        positive.sort(key=lambda pair: pair[1], reverse=True)
        step = step_by_key[step_key]
        for feature, contribution in positive[:top_n_reasons]:
            value = features.iloc[row_index][feature]
            template = FEATURE_TEMPLATES.get(feature, FALLBACK_TEMPLATE)
            item["reasons"].append(
                {
                    "feature": feature,
                    "text": template.format(feature=feature),
                    "evidence": _evidence(
                        feature, value, step, steps, reference_stats
                    ),
                    "contribution": contribution,
                }
            )
    return explained