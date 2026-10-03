from __future__ import annotations

import json
import re
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from rapidfuzz.fuzz import partial_ratio
from sqlalchemy import or_
from sqlmodel import Session, select

from blackbox.agent.scoring import normalize_answer
from blackbox.config import Settings, get_settings
from blackbox.corpus.embed import embed_texts
from blackbox.features.reference import (
    ReferenceStats,
    compute_reference_stats,
    save_reference_stats,
)
from blackbox.replay.graph import dag_depth, dag_from_steps
from blackbox.store.db import get_session, init_db
from blackbox.store.models import Fault, Label, Run, Step, Task

FORBIDDEN_COLUMNS = ("fault", "label", "origin", "overridden", "reused", "gold")
YES_NO_WORDS = {"yes", "no"}
YES_NO_STARTS = {
    "are",
    "can",
    "could",
    "did",
    "do",
    "does",
    "has",
    "have",
    "is",
    "was",
    "were",
    "will",
    "would",
}
QUESTION_WORDS = YES_NO_STARTS | {
    "how",
    "what",
    "when",
    "where",
    "which",
    "who",
    "whose",
    "why",
}


def _nan() -> float:
    return float("nan")


def _dicts(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _passages(step: Step) -> list[dict[str, Any]]:
    return _dicts(step.output.get("passages"))


def _normalize(text: object) -> str:
    return normalize_answer(str(text or ""))


def _fuzzy(first: object, second: object) -> float:
    left, right = _normalize(first), _normalize(second)
    if not left or not right:
        return 0.0
    return float(partial_ratio(left, right)) / 100.0


def _tokens(text: object) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", str(text).lower()))


def _jaccard(first: object, second: object) -> float:
    left, right = _tokens(first), _tokens(second)
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def _z_score(stats: ReferenceStats, name: str, metric: str, value: float) -> float:
    metric_stats = stats.get(name, {}).get(metric)
    if metric_stats is None:
        return _nan()
    std = metric_stats.get("std", 0.0)
    if std == 0:
        return 0.0
    return (value - metric_stats["mean"]) / std


def _canonical_input(step: Step) -> str:
    summary = {key: value for key, value in step.input.items() if key != "prompt"}
    if not summary:
        summary = step.input
    return json.dumps(summary, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _load_embedding_cache(
    settings: Settings,
) -> tuple[dict[str, int], np.ndarray | None]:
    data_dir = Path(settings.DATA_DIR)
    index_path = data_dir / "step_emb_index.json"
    embeddings_path = data_dir / "step_emb.npy"
    if not index_path.exists() or not embeddings_path.exists():
        return {}, None
    raw_index = json.loads(index_path.read_text(encoding="utf-8"))
    if not isinstance(raw_index, dict):
        return {}, None
    embeddings = np.load(embeddings_path)
    index = {str(key): int(value) for key, value in raw_index.items()}
    if any(position < 0 or position >= len(embeddings) for position in index.values()):
        return {}, None
    return index, embeddings


def _semantic_vectors(
    steps: Sequence[Step], transient_texts: Sequence[str], settings: Settings
) -> tuple[dict[str, np.ndarray], list[np.ndarray]]:
    index, cached = _load_embedding_cache(settings)
    missing = [step for step in steps if step.step_id not in index]
    texts = [step.output_text for step in missing] + list(transient_texts)
    generated = embed_texts(texts) if texts else np.empty((0, 0), dtype=np.float32)

    output_vectors: dict[str, np.ndarray] = {}
    if cached is not None:
        output_vectors.update(
            {step.step_id: cached[index[step.step_id]] for step in steps if step.step_id in index}
        )
    for position, step in enumerate(missing):
        output_vectors[step.step_id] = generated[position]

    if missing:
        new_vectors = generated[: len(missing)]
        combined = new_vectors if cached is None else np.vstack((cached, new_vectors))
        start = 0 if cached is None else len(cached)
        for offset, step in enumerate(missing):
            index[step.step_id] = start + offset
        data_dir = Path(settings.DATA_DIR)
        data_dir.mkdir(parents=True, exist_ok=True)
        np.save(data_dir / "step_emb.npy", combined)
        (data_dir / "step_emb_index.json").write_text(
            json.dumps(index, sort_keys=True), encoding="utf-8"
        )

    transient_start = len(missing)
    transient = [generated[transient_start + idx] for idx in range(len(transient_texts))]
    return output_vectors, transient


def _cosine(first: np.ndarray, second: np.ndarray) -> float:
    denominator = float(np.linalg.norm(first) * np.linalg.norm(second))
    return float(np.dot(first, second) / denominator) if denominator else 0.0


def _question_for_run(run: Run, steps: Sequence[Step]) -> str:
    for step in steps:
        question = step.input.get("question")
        if isinstance(question, str) and question:
            return question
    with get_session() as session:
        task = session.get(Task, run.task_id)
        if task is None:
            raise ValueError(f"Task not found for run: {run.run_id}")
        return task.question


def _retrieval_passages(
    step: Step, by_key: dict[str, Step], ancestors: Iterable[str]
) -> list[dict[str, Any]]:
    direct = _passages(step)
    if direct:
        return direct
    retrievals = [
        by_key[key]
        for key in ancestors
        if key in by_key and by_key[key].name == "retrieve"
    ]
    if not retrievals:
        return []
    return _passages(max(retrievals, key=lambda candidate: candidate.idx))


def _ancestors(step_key: str, by_key: dict[str, Step]) -> set[str]:
    found: set[str] = set()
    pending = list(by_key[step_key].deps)
    while pending:
        key = pending.pop()
        if key in found or key not in by_key:
            continue
        found.add(key)
        pending.extend(by_key[key].deps)
    return found


def _bool_output(step: Step) -> bool | None:
    for key in ("supported", "valid"):
        value = step.output.get(key)
        if isinstance(value, bool):
            return value
    return None


def _is_yes_no_question(question: str) -> bool:
    words = re.findall(r"[a-z]+", question.lower())
    return bool(words and words[0] in YES_NO_STARTS)


def _is_yes_no_answer(answer: object) -> bool:
    return _normalize(answer) in YES_NO_WORDS


def _question_entities(question: str) -> set[str]:
    words = re.findall(r"[A-Za-z0-9]+", question)
    entities = {
        word.lower()
        for word in words
        if word[0].isupper() and word.lower() not in QUESTION_WORDS
    }
    if entities:
        return entities
    return _tokens(question) - QUESTION_WORDS


def features_for_run(
    run: Run,
    steps: Sequence[Step],
    stats: ReferenceStats,
    *,
    question: str | None = None,
    settings: Settings | None = None,
) -> pd.DataFrame:
    if not steps:
        return pd.DataFrame()
    settings = settings or get_settings()
    ordered = sorted(steps, key=lambda step: step.idx)
    question = question or _question_for_run(run, ordered)
    by_key = {step.step_key: step for step in ordered}
    dag = dag_from_steps(ordered)
    ancestors_by_key = {step.step_key: _ancestors(step.step_key, by_key) for step in ordered}
    descendants_by_key = {
        step.step_key: dag.descendants(step.step_key) for step in ordered
    }
    synth_keys = {step.step_key for step in ordered if step.name == "synthesize"}
    max_attempt = {
        node_id: max(candidate.attempt for candidate in ordered if candidate.node_id == node_id)
        for node_id in {step.node_id for step in ordered}
    }

    plan = next((step for step in ordered if step.name == "plan"), None)
    subquestions = _dicts(plan.output.get("subquestions")) if plan else []
    feeding_nodes = {
        str(dependency)
        for subquestion in subquestions
        for dependency in (
            subquestion.get("deps") if isinstance(subquestion.get("deps"), list) else []
        )
    }
    question_entities = _question_entities(question)
    semantic_texts = [_canonical_input(step) for step in ordered]
    semantic_texts.append(question)
    semantic_texts.extend(str(item.get("text", "")) for item in subquestions)
    output_vectors, transient = _semantic_vectors(ordered, semantic_texts, settings)
    input_vectors = transient[: len(ordered)]
    question_vector = transient[len(ordered)]
    subquestion_vectors = transient[len(ordered) + 1 :]

    check_results = {
        step.step_key: _bool_output(step) for step in ordered if step.name == "check"
    }
    rows: list[dict[str, Any]] = []
    for position, step in enumerate(ordered):
        descendants = descendants_by_key[step.step_key]
        passages = _retrieval_passages(
            step, by_key, ancestors_by_key[step.step_key]
        )
        scores = [
            float(passage["score"])
            for passage in passages
            if isinstance(passage.get("score"), (int, float))
        ]
        passage_texts = [str(passage.get("text", "")) for passage in passages]
        top1_score = scores[0] if scores else _nan()
        passage_len_mean = (
            float(np.mean([len(text) for text in passage_texts]))
            if passage_texts
            else _nan()
        )
        output = step.output
        answer = output.get("answer", step.output_text)
        evidence_pid = output.get("evidence_pid")
        cited_passage = next(
            (passage for passage in passages if passage.get("pid") == evidence_pid), None
        )
        checked_unsupported = any(
            check_results.get(key) is False
            for key in descendants
            if key in check_results
            and (step.step_key in ancestors_by_key[key] or by_key[key].node_id == step.node_id)
        )
        downstream_inputs = " ".join(
            _canonical_input(by_key[key]) for key in descendants if key in by_key
        )
        query = str(step.input.get("query", ""))
        titles = [str(passage.get("title", "")) for passage in passages]
        row: dict[str, Any] = {
            "name": step.name,
            "type": step.type,
            "idx": step.idx,
            "rel_pos": step.idx / (len(ordered) - 1) if len(ordered) > 1 else 0.0,
            "n_steps": len(ordered),
            "dag_depth": dag_depth(dag, step.step_key),
            "n_children": len(dag.children[step.step_key]),
            "n_descendants": len(descendants),
            "is_ancestor_of_final": int(bool(descendants & synth_keys)),
            "attempt": step.attempt,
            "node_retries": max_attempt[step.node_id],
            "node_feeds_other": int(step.node_id in feeding_nodes),
            "latency_z": _z_score(stats, step.name, "latency", float(step.latency_ms)),
            "tokens_out_z": _z_score(
                stats, step.name, "tokens_out", float(step.tokens_out)
            ),
            "output_len_z": _z_score(
                stats, step.name, "output_len", float(len(step.output_text))
            ),
            "top1_score": top1_score if step.name == "retrieve" else _nan(),
            "mean_score": float(np.mean(scores)) if step.name == "retrieve" and scores else _nan(),
            "score_gap": (
                scores[0] - scores[1]
                if step.name == "retrieve" and len(scores) > 1
                else _nan()
            ),
            "top1_score_z": (
                _z_score(stats, step.name, "top1_score", top1_score)
                if step.name == "retrieve" and scores
                else _nan()
            ),
            "query_title_overlap": (
                _jaccard(query, " ".join(titles)) if step.name == "retrieve" else _nan()
            ),
            "n_unique_titles": (
                len({title for title in titles if title}) if step.name == "retrieve" else _nan()
            ),
            "passage_len_mean_z": (
                _z_score(stats, step.name, "passage_len", passage_len_mean)
                if step.name == "retrieve" and passage_texts
                else _nan()
            ),
            "answer_in_passages": (
                int(bool(_normalize(answer)) and any(_normalize(answer) in _normalize(text) for text in passage_texts))
                if step.name == "extract"
                else _nan()
            ),
            "answer_fuzzy": (
                max((_fuzzy(answer, text) for text in passage_texts), default=0.0)
                if step.name == "extract"
                else _nan()
            ),
            "evidence_in_passages": (
                int(
                    cited_passage is not None
                    and bool(_normalize(output.get("evidence_sentence")))
                    and _normalize(output.get("evidence_sentence"))
                    in _normalize(cited_passage.get("text", ""))
                )
                if step.name == "extract"
                else _nan()
            ),
            "checked_unsupported": int(checked_unsupported),
            "check_supported": (
                int(check_results[step.step_key])
                if step.name == "check" and check_results[step.step_key] is not None
                else _nan()
            ),
            "final_in_subanswers": (
                max(
                    (_fuzzy(answer, value) for value in step.input.get("subanswers", {}).values()),
                    default=0.0,
                )
                if step.name == "synthesize"
                and isinstance(step.input.get("subanswers"), dict)
                else _nan()
            ),
            "yesno_mismatch": (
                int(_is_yes_no_question(question) != _is_yes_no_answer(answer))
                if step.name == "synthesize"
                else _nan()
            ),
            "n_subq": len(subquestions) if step.name == "plan" else _nan(),
            "plan_has_dep": (
                int(any(bool(item.get("deps")) for item in subquestions))
                if step.name == "plan"
                else _nan()
            ),
            "subq_question_sim": (
                float(np.mean([_cosine(vector, question_vector) for vector in subquestion_vectors]))
                if step.name == "plan" and subquestion_vectors
                else _nan()
            ),
            "plan_title_mention": (
                float(
                    np.mean(
                        [
                            bool(_tokens(item.get("text")) & _tokens(question))
                            and bool(
                                _tokens(item.get("text")) & question_entities
                            )
                            for item in subquestions
                        ]
                    )
                )
                if step.name == "plan" and subquestions
                else _nan()
            ),
            "io_cosine": _cosine(input_vectors[position], output_vectors[step.step_id]),
            "output_question_cosine": _cosine(
                output_vectors[step.step_id], question_vector
            ),
            "output_consumed": int(
                bool(_normalize(step.output_text))
                and _normalize(step.output_text) in _normalize(downstream_inputs)
            ),
        }
        rows.append(row)
    return pd.DataFrame(rows)


def assert_no_leakage(frame: pd.DataFrame) -> None:
    leaking = [
        column
        for column in frame.columns
        if any(forbidden in str(column).lower() for forbidden in FORBIDDEN_COLUMNS)
    ]
    if leaking:
        raise ValueError(f"Forbidden feature columns: {', '.join(map(str, leaking))}")


def _dataset_rows(
    session: Session,
    split: str,
    fault_types: Sequence[str] | None,
    include_organic: bool,
    workspace: str,
) -> list[tuple[Run, Label, Task, Fault | None]]:
    statement = (
        select(Run, Label, Task, Fault)
        .join(Label, Label.run_id == Run.run_id)
        .join(Task, Task.task_id == Run.task_id)
        .outerjoin(Fault, Fault.run_id == Run.run_id)
        .where(
            Run.outcome == "fail",
            Run.workspace == workspace,
            Label.verified.is_(True),
            Task.split == split,
        )
    )
    if include_organic and fault_types:
        statement = statement.where(
            or_(Fault.run_id.is_(None), Fault.fault_type.in_(fault_types))
        )
    elif include_organic:
        statement = statement.where(
            or_(Fault.run_id.is_not(None), Run.origin == "clean")
        )
    elif fault_types:
        statement = statement.where(Fault.fault_type.in_(fault_types))
    else:
        statement = statement.where(Fault.run_id.is_not(None))
    return list(session.exec(statement.order_by(Run.run_id)).all())


def build_dataset(
    split: str,
    fault_types: Sequence[str] | None = None,
    include_organic: bool = False,
    workspace: str = "hotpot",
) -> tuple[pd.DataFrame, pd.Series, list[int], pd.DataFrame]:
    init_db()
    settings = get_settings()
    with get_session() as session:
        stats_name = (
            "feature_stats.json"
            if workspace == "hotpot"
            else f"feature_stats_{workspace}.json"
        )
        stats_path = Path(settings.ARTIFACTS_DIR) / stats_name
        stats = compute_reference_stats(session, workspace=workspace)
        save_reference_stats(stats, stats_path, settings)

        frames: list[pd.DataFrame] = []
        labels: list[int] = []
        groups: list[int] = []
        metadata: list[dict[str, str]] = []
        for run, label, task, fault in _dataset_rows(
            session, split, fault_types, include_organic, workspace
        ):
            steps = list(
                session.exec(
                    select(Step).where(Step.run_id == run.run_id).order_by(Step.idx)
                ).all()
            )
            frame = features_for_run(
                run, steps, stats, question=task.question, settings=settings
            )
            frames.append(frame)
            groups.append(len(frame))
            labels.extend(
                int(step.step_key == label.culprit_step_key) for step in steps
            )
            fault_type = fault.fault_type if fault is not None else "organic"
            metadata.extend(
                {
                    "run_id": run.run_id,
                    "step_key": step.step_key,
                    "task_id": task.task_id,
                    "fault_type": fault_type,
                }
                for step in steps
            )

    features = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    assert_no_leakage(features)
    return (
        features,
        pd.Series(labels, name="label", dtype="int64"),
        groups,
        pd.DataFrame(metadata, columns=["run_id", "step_key", "task_id", "fault_type"]),
    )