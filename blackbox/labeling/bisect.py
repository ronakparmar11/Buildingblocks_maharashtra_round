import logging
from collections.abc import Callable

from sqlmodel import Session

from blackbox.replay.engine import replay
from blackbox.sdk.context import Override
from blackbox.store.db import get_session, init_db
from blackbox.store.models import Label, Run
from blackbox.store.repo import get_fault, get_label, get_run, get_steps, save_label

logger = logging.getLogger(__name__)

ReplayFn = Callable[..., Run]


def _label_fault_run(
    session: Session, run_id: str, replay_fn: ReplayFn
) -> Label | None:
    source_run = get_run(session, run_id)
    if source_run is None:
        raise ValueError(f"Unknown run id: {run_id}")
    if source_run.outcome != "fail" or get_label(session, run_id) is not None:
        return None

    steps = get_steps(session, run_id)
    if not steps:
        logger.info("Discarding fault run %s: no recorded steps", run_id)
        return None

    outcomes: dict[int, bool] = {len(steps): True}
    n_replays = 0

    def fails(freeze_before_idx: int) -> bool:
        nonlocal n_replays
        if freeze_before_idx not in outcomes:
            replay_run = replay_fn(
                run_id,
                freeze_before_idx=freeze_before_idx,
                origin="bisect",
            )
            outcomes[freeze_before_idx] = replay_run.outcome == "fail"
            n_replays += 1
        return outcomes[freeze_before_idx]

    if fails(0):
        logger.info("Discarding fault run %s: f(0) still fails", run_id)
        return None

    passing_idx = 0
    failing_idx = len(steps)
    while failing_idx - passing_idx > 1:
        midpoint = (passing_idx + failing_idx) // 2
        if fails(midpoint):
            failing_idx = midpoint
        else:
            passing_idx = midpoint

    culprit = steps[failing_idx - 1]
    verification = replay_fn(
        run_id,
        overrides={culprit.step_key: Override("regenerate")},
        origin="bisect",
    )
    verified = verification.outcome == "pass"
    fault = get_fault(session, run_id)
    return save_label(
        session,
        Label(
            run_id=run_id,
            culprit_step_key=culprit.step_key,
            method="bisect",
            verified=verified,
            confidence=1.0 if verified else 0.5,
            n_replays=n_replays,
            matches_injection=(
                culprit.step_key == fault.step_key if fault is not None else None
            ),
        ),
    )


def label_fault_run(run_id: str) -> Label | None:
    init_db()
    with get_session() as session:
        return _label_fault_run(session, run_id, replay)