from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import lightgbm as lgb
from sqlmodel import select

from blackbox.config import get_settings
from blackbox.features.extract import features_for_run
from blackbox.features.reference import load_reference_stats
from blackbox.model.train import prepare_features
from blackbox.store.db import get_session, init_db
from blackbox.store.models import Prediction, Run, Step, Task


def load_model(suffix: str = "") -> tuple[lgb.Booster, list[str], dict[str, Any]]:
    artifact_dir = Path(get_settings().ARTIFACTS_DIR)
    infix = f"_{suffix}" if suffix else ""
    model = lgb.Booster(model_file=str(artifact_dir / f"model{infix}.txt"))
    feature_list = json.loads(
        (artifact_dir / f"feature_list{infix}.json").read_text(encoding="utf-8")
    )
    metadata = json.loads(
        (artifact_dir / f"model_meta{infix}.json").read_text(encoding="utf-8")
    )
    return model, [str(item) for item in feature_list], metadata


def diagnose(run_id: str, *, persist: bool = True) -> dict[str, Any]:
    started = time.perf_counter()
    init_db()
    settings = get_settings()
    model, feature_list, model_meta = load_model()
    with get_session() as session:
        run = session.get(Run, run_id)
        if run is None:
            raise ValueError(f"Unknown run id: {run_id}")
        task = session.get(Task, run.task_id)
        if task is None:
            raise ValueError(f"Unknown task id: {run.task_id}")
        steps = list(
            session.exec(select(Step).where(Step.run_id == run_id).order_by(Step.idx)).all()
        )
        stats = load_reference_stats(Path(settings.ARTIFACTS_DIR) / "feature_stats.json")
        features = features_for_run(
            run, steps, stats, question=task.question, settings=settings
        )
        prepared = prepare_features(
            features, feature_list, model_meta.get("categories", {})
        )
        scores = model.predict(prepared)
        order = sorted(range(len(steps)), key=lambda index: (-float(scores[index]), steps[index].idx))
        ranking = [
            {
                "step_key": steps[index].step_key,
                "idx": steps[index].idx,
                "score": float(scores[index]),
                "rank": rank,
            }
            for rank, index in enumerate(order, start=1)
        ]
        if persist:
            existing = list(session.exec(select(Prediction).where(Prediction.run_id == run_id)).all())
            for row in existing:
                session.delete(row)
            for item in ranking:
                session.add(
                    Prediction(
                        run_id=run_id,
                        step_key=str(item["step_key"]),
                        score=float(item["score"]),
                        rank=int(item["rank"]),
                        model_version=str(model_meta["version"]),
                        reasons=[],
                    )
                )
            session.commit()
    return {
        "run_id": run_id,
        "ranking": ranking,
        "latency_ms": (time.perf_counter() - started) * 1000.0,
    }