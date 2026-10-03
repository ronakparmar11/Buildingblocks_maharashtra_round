import re

from sqlalchemy.orm import object_session
from sqlmodel import Session, select

from blackbox.faults.library import (
    BAD_QUERY,
    DISTRACTOR_RETRIEVAL,
    HALLUCINATED_SYNTHESIS,
    PLAN_CORRUPT,
    TRUNCATED_CONTEXT,
    WRONG_EXTRACTION,
)
from blackbox.store.db import get_session
from blackbox.store.models import Run, Step, Task

FaultTarget = tuple[str, str]


def latest_clean_run(session: Session, task_id: str) -> Run | None:
    statement = (
        select(Run)
        .where(Run.task_id == task_id, Run.origin == "clean", Run.outcome == "pass")
        .order_by(Run.created_at.desc())
    )
    return session.exec(statement).first()


def _load_run_data(clean_run: Run) -> tuple[Task, list[Step]]:
    session = object_session(clean_run)
    if session is not None:
        task = session.get(Task, clean_run.task_id)
        steps = list(
            session.scalars(
                select(Step).where(Step.run_id == clean_run.run_id).order_by(Step.idx)
            ).all()
        )
    else:
        with get_session() as fallback_session:
            task = fallback_session.get(Task, clean_run.task_id)
            steps = list(
                fallback_session.exec(
                    select(Step)
                    .where(Step.run_id == clean_run.run_id)
                    .order_by(Step.idx)
                ).all()
            )
    if task is None:
        raise ValueError(f"Task not found for clean run: {clean_run.task_id}")
    return task, steps


def _passages(step: Step) -> list[dict[str, object]]:
    raw_passages = step.output.get("passages", [])
    if not isinstance(raw_passages, list):
        return []
    return [passage for passage in raw_passages if isinstance(passage, dict)]


def applicable_targets(clean_run: Run) -> list[FaultTarget]:
    if clean_run.origin != "clean":
        raise ValueError("Fault targets require a clean run")

    task, steps = _load_run_data(clean_run)
    by_key = {step.step_key: step for step in steps}
    targets: list[FaultTarget] = []

    plan = next((step for step in steps if step.name == "plan"), None)
    if plan is not None:
        nodes = plan.output.get("subquestions", [])
        comparison_target = (
            plan.output.get("type") == "comparison"
            and isinstance(nodes, list)
            and len(nodes) > 1
        )
        bridge_target = (
            plan.output.get("type") == "bridge"
            and task.distractor_pids
            and isinstance(nodes, list)
            and any(
                isinstance(node, dict)
                and re.search(r"\{[^{}]+\}", str(node.get("text", "")))
                for node in nodes
            )
        )
        if comparison_target or bridge_target:
            targets.append((PLAN_CORRUPT, plan.step_key))

    for step in steps:
        if step.name == "retrieve":
            passages = _passages(step)
            has_node_dependency = any(
                "/extract#" in dependency for dependency in step.deps
            )
            if step.attempt == 0 and has_node_dependency and task.distractor_pids:
                targets.append((BAD_QUERY, step.step_key))
            if task.distractor_pids and any(
                passage.get("title") in task.gold_titles for passage in passages
            ):
                targets.append((DISTRACTOR_RETRIEVAL, step.step_key))
            if any(
                re.search(r"[.!?]\s+\S", str(passage.get("text", "")))
                for passage in passages
            ):
                targets.append((TRUNCATED_CONTEXT, step.step_key))

        if step.name == "extract":
            retrieve_key = f"{step.node_id}/retrieve#{step.attempt}"
            answer = str(step.output.get("answer", ""))
            alternatives = (
                [
                    str(passage.get("title", ""))
                    for passage in _passages(by_key[retrieve_key])
                    if str(passage.get("title", "")).casefold() != answer.casefold()
                ]
                if retrieve_key in by_key
                else []
            )
            if alternatives:
                targets.append((WRONG_EXTRACTION, step.step_key))

        if step.name == "synthesize":
            answer = str(step.output.get("answer", ""))
            subanswers = step.input.get("subanswers", {})
            has_wrong_subanswer = isinstance(subanswers, dict) and any(
                str(subanswer).casefold() != answer.casefold()
                for subanswer in subanswers.values()
            )
            if (
                task.qtype == "comparison" and answer.casefold() in {"yes", "no"}
            ) or has_wrong_subanswer:
                targets.append((HALLUCINATED_SYNTHESIS, step.step_key))

    return targets
