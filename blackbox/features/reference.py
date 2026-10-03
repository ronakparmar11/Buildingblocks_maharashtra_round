from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

import numpy as np
from sqlmodel import Session, select

from blackbox.config import Settings, get_settings
from blackbox.store.db import get_session, init_db
from blackbox.store.models import Run, Step, Task

MetricStats = dict[str, float]
ReferenceStats = dict[str, dict[str, MetricStats]]


def _passages(step: Step) -> list[dict[str, object]]:
    raw_passages = step.output.get("passages", [])
    if not isinstance(raw_passages, list):
        return []
    return [passage for passage in raw_passages if isinstance(passage, dict)]


def _metric_values(step: Step) -> dict[str, float]:
    values = {
        "latency": float(step.latency_ms),
        "tokens_out": float(step.tokens_out),
        "output_len": float(len(step.output_text)),
    }
    passages = _passages(step)
    scores = [
        float(passage["score"])
        for passage in passages
        if isinstance(passage.get("score"), (int, float))
    ]
    lengths = [
        len(str(passage.get("text", "")))
        for passage in passages
        if passage.get("text") is not None
    ]
    if scores:
        values["top1_score"] = scores[0]
    if lengths:
        values["passage_len"] = float(np.mean(lengths))
    return values


def reference_stats_from_steps(steps: Iterable[Step]) -> ReferenceStats:
    values_by_name: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for step in steps:
        for metric, value in _metric_values(step).items():
            values_by_name[step.name][metric].append(value)

    return {
        name: {
            metric: {
                "mean": float(np.mean(values)),
                "std": float(np.std(values)),
            }
            for metric, values in sorted(metrics.items())
        }
        for name, metrics in sorted(values_by_name.items())
    }


def compute_reference_stats(session: Session | None = None) -> ReferenceStats:
    if session is None:
        init_db()
        with get_session() as db_session:
            return compute_reference_stats(db_session)

    statement = (
        select(Step)
        .join(Run, Run.run_id == Step.run_id)
        .join(Task, Task.task_id == Run.task_id)
        .where(Run.origin == "clean", Run.outcome == "pass", Task.split == "train")
        .order_by(Step.name, Step.step_id)
    )
    return reference_stats_from_steps(session.exec(statement).all())


def save_reference_stats(
    stats: ReferenceStats,
    path: Path | None = None,
    settings: Settings | None = None,
) -> Path:
    settings = settings or get_settings()
    path = path or Path(settings.ARTIFACTS_DIR) / "feature_stats.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(stats, indent=2, sort_keys=True), encoding="utf-8")
    return path


def load_reference_stats(
    path: Path | None = None, settings: Settings | None = None
) -> ReferenceStats:
    settings = settings or get_settings()
    path = path or Path(settings.ARTIFACTS_DIR) / "feature_stats.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise TypeError("Reference stats must be a JSON object")
    return raw