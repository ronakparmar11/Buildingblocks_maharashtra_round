import logging
from collections.abc import Callable

from sqlmodel import Session

from blackbox.replay.engine import replay
from blackbox.sdk.context import Override
from blackbox.store.db import get_session, init_db
from blackbox.store.models import Label, Run
from blackbox.store.repo import get_label, get_run, get_steps, save_label

logger = logging.getLogger(__name__)

ReplayFn = Callable[..., Run]


def _label_organic_run(
    session: Session,
    run_id: str,
    replay_fn: ReplayFn,
    n_samples: int = 3,
    threshold: float = 2 / 3,
) -> Label | None:
    if n_samples < 1:
        raise ValueError("n_samples must be at least 1")
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be between 0 and 1")

    source_run = get_run(session, run_id)
    if source_run is None:
        raise ValueError(f"Unknown run id: {run_id}")
    if source_run.outcome != "fail" or get_label(session, run_id) is not None:
        return None

    candidates = [step for step in get_steps(session, run_id) if step.type == "llm"]
    best_step_key: str | None = None
    best_flip_rate = -1.0
    n_replays = 0
    for step in candidates:
        flips = 0
        for sample_idx in range(n_samples):
            replay_run = replay_fn(
                run_id,
                overrides={
                    step.step_key: Override(
                        "regenerate",
                        params={"temperature": 0.8, "sample_idx": sample_idx},
                    )
                },
                origin="counterfactual",
            )
            n_replays += 1
            flips += replay_run.outcome == "pass"
        flip_rate = flips / n_samples
        if flip_rate > best_flip_rate:
            best_step_key = step.step_key
            best_flip_rate = flip_rate

    if best_step_key is None or best_flip_rate < threshold:
        logger.info("Organic run %s is unlabelable", run_id)
        return None

    return save_label(
        session,
        Label(
            run_id=run_id,
            culprit_step_key=best_step_key,
            method="counterfactual",
            verified=True,
            confidence=best_flip_rate,
            n_replays=n_replays,
            matches_injection=None,
        ),
    )


def label_organic_run(
    run_id: str, n_samples: int = 3, threshold: float = 2 / 3
) -> Label | None:
    init_db()
    with get_session() as session:
        return _label_organic_run(session, run_id, replay, n_samples, threshold)