from __future__ import annotations

import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import partial
from typing import Any

from google.genai.errors import APIError as GoogleAPIError
from openai import OpenAIError
from sqlmodel import Session

from blackbox.agent.prompts import rewrite_query_prompt
from blackbox.config import get_settings
from blackbox.llm.base import LLMClient
from blackbox.model.predict import diagnose
from blackbox.repair.strategies import RepairCandidate, candidates_for_step
from blackbox.replay.engine import _llm_client, replay
from blackbox.sdk.cassette import Cassette, Usage
from blackbox.store.db import get_session, init_db
from blackbox.store.models import Run, Step
from blackbox.store.repo import get_predictions, get_run, get_steps

ReplayFn = Callable[..., Run]
RewriteQueryFn = Callable[[Step], str | None]

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RepairAttempt:
    step_key: str
    strategy: str
    run_id: str
    outcome: str
    n_executed: int
    n_reused: int
    tokens_total: int
    pct_reused: float


@dataclass(frozen=True)
class RepairResult:
    run_id: str
    attempts: list[RepairAttempt]
    repaired: bool
    winning_run_id: str | None
    winning_step_key: str | None


def _attempt(
    replay_fn: ReplayFn,
    source_run_id: str,
    step_key: str,
    candidate: RepairCandidate,
) -> RepairAttempt:
    run = replay_fn(
        source_run_id,
        overrides={step_key: candidate.override},
        origin="repair",
    )
    return RepairAttempt(
        step_key=step_key,
        strategy=candidate.display_name,
        run_id=run.run_id,
        outcome=run.outcome,
        n_executed=run.n_executed,
        n_reused=run.n_reused,
        tokens_total=run.tokens_total,
        pct_reused=run.n_reused / run.n_steps if run.n_steps else 0.0,
    )


def _repair(
    session: Session,
    run_id: str,
    replay_fn: ReplayFn,
    *,
    rewrite_query_fn: RewriteQueryFn | None = None,
    top_k: int = 3,
    max_workers: int = 4,
) -> RepairResult:
    source_run = get_run(session, run_id)
    if source_run is None:
        raise ValueError(f"Unknown run id: {run_id}")
    if source_run.outcome == "pass":
        raise ValueError(f"Run already passes: {run_id}")
    predictions = get_predictions(session, run_id)[:top_k]
    if not predictions:
        raise ValueError(f"Run has no predictions: {run_id}")
    steps = {step.step_key: step for step in get_steps(session, run_id)}
    attempts: list[RepairAttempt] = []

    for prediction in predictions:
        step = steps.get(prediction.step_key)
        if step is None:
            continue
        rewritten_query = None
        if step.name == "retrieve" and rewrite_query_fn is not None:
            try:
                rewritten_query = rewrite_query_fn(step)
            except RuntimeError as error:
                logger.warning(
                    "Could not generate a rewritten query for %s: %s",
                    step.step_key,
                    error,
                )
        candidates = candidates_for_step(
            step,
            workspace=source_run.workspace,
            rewritten_query=rewritten_query,
        )
        if not candidates:
            continue
        workers = max(1, min(max_workers, len(candidates)))
        step_key = step.step_key
        with ThreadPoolExecutor(max_workers=workers) as executor:
            step_attempts = list(
                executor.map(
                    partial(_attempt, replay_fn, run_id, step_key),
                    candidates,
                )
            )
        attempts.extend(step_attempts)
        winner = next(
            (attempt for attempt in step_attempts if attempt.outcome == "pass"), None
        )
        if winner is not None:
            return RepairResult(
                run_id=run_id,
                attempts=attempts,
                repaired=True,
                winning_run_id=winner.run_id,
                winning_step_key=step.step_key,
            )

    return RepairResult(
        run_id=run_id,
        attempts=attempts,
        repaired=False,
        winning_run_id=None,
        winning_step_key=None,
    )


def _rewrite_query(step: Step, llm: LLMClient) -> str | None:
    query = str(step.input.get("query", ""))
    subquestion = str(step.input.get("subquestion", query))
    prompt = rewrite_query_prompt(subquestion, query)
    settings = get_settings()
    try:
        with get_session() as session:
            response, _, _ = Cassette(session).get_or_call(
                kind="llm",
                model=settings.LLM_MODEL,
                payload={"prompt": prompt, "purpose": "repair_query"},
                temperature=0.0,
                sample_idx=0,
                call_fn=lambda: _call_query_llm(llm, prompt),
            )
    except (GoogleAPIError, OpenAIError) as error:
        raise RuntimeError("query rewrite provider unavailable") from error
    rewritten = response.get("query")
    return str(rewritten) if rewritten else None


def _call_query_llm(llm: LLMClient, prompt: str) -> tuple[dict[str, Any], Usage]:
    response = llm.complete_json(prompt, temperature=0.0)
    return response.json, {
        "tokens_in": response.tokens_in,
        "tokens_out": response.tokens_out,
        "model": response.model,
    }


def repair(run_id: str, top_k: int = 3, max_workers: int = 4) -> RepairResult:
    init_db()
    with get_session() as session:
        if not get_predictions(session, run_id):
            if get_run(session, run_id) is None:
                raise ValueError(f"Unknown run id: {run_id}")
            diagnose(run_id)
    llm = _llm_client()
    with get_session() as session:
        return _repair(
            session,
            run_id,
            replay,
            rewrite_query_fn=lambda step: _rewrite_query(step, llm),
            top_k=top_k,
            max_workers=max_workers,
        )