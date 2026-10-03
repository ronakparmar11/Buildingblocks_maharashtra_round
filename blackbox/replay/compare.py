from difflib import ndiff
from typing import Any, Literal, TypedDict

from sqlalchemy.orm import object_session
from sqlmodel import Session

from blackbox.store.db import get_session
from blackbox.store.models import Run, Step
from blackbox.store.repo import get_steps


class ComparisonRow(TypedDict):
    step_key: str
    status: Literal["same", "changed", "only_a", "only_b"]
    a_step: dict[str, Any] | None
    b_step: dict[str, Any] | None
    text_diff: list[str]
    json_diff: dict[str, list[str]]


class TraceComparison(TypedDict):
    a: dict[str, Any]
    b: dict[str, Any]
    first_divergence: str | None
    rows: list[ComparisonRow]
    summary: dict[str, Any]


def _json_diff(a: Any, b: Any, path: str = "$") -> dict[str, list[str]]:
    added: list[str] = []
    removed: list[str] = []
    changed: list[str] = []
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(a.keys() - b.keys()):
            removed.append(f"{path}.{key}")
        for key in sorted(b.keys() - a.keys()):
            added.append(f"{path}.{key}")
        for key in sorted(a.keys() & b.keys()):
            child = _json_diff(a[key], b[key], f"{path}.{key}")
            added.extend(child["added"])
            removed.extend(child["removed"])
            changed.extend(child["changed"])
    elif a != b:
        changed.append(path)
    return {"added": added, "removed": removed, "changed": changed}


def _step_data(step: Step | None) -> dict[str, Any] | None:
    return step.model_dump(mode="json") if step is not None else None


def _compare(session: Session, run_a: Run, run_b: Run) -> TraceComparison:
    steps_a = get_steps(session, run_a.run_id)
    steps_b = get_steps(session, run_b.run_id)
    by_key_a = {step.step_key: step for step in steps_a}
    by_key_b = {step.step_key: step for step in steps_b}
    order = sorted(
        by_key_a.keys() | by_key_b.keys(),
        key=lambda key: (
            min(
                by_key_a[key].idx if key in by_key_a else 10**9,
                by_key_b[key].idx if key in by_key_b else 10**9,
            ),
            key,
        ),
    )
    rows: list[ComparisonRow] = []
    for key in order:
        step_a = by_key_a.get(key)
        step_b = by_key_b.get(key)
        if step_a is None:
            status: Literal["same", "changed", "only_a", "only_b"] = "only_b"
        elif step_b is None:
            status = "only_a"
        elif step_a.output_hash == step_b.output_hash:
            status = "same"
        else:
            status = "changed"
        rows.append(
            ComparisonRow(
                step_key=key,
                status=status,
                a_step=_step_data(step_a),
                b_step=_step_data(step_b),
                text_diff=(
                    list(ndiff(step_a.output_text.split(), step_b.output_text.split()))
                    if status == "changed" and step_a is not None and step_b is not None
                    else []
                ),
                json_diff=(
                    _json_diff(step_a.output, step_b.output)
                    if status == "changed" and step_a is not None and step_b is not None
                    else {"added": [], "removed": [], "changed": []}
                ),
            )
        )
    first_divergence = next(
        (row["step_key"] for row in rows if row["status"] != "same"), None
    )
    return TraceComparison(
        a=run_a.model_dump(mode="json"),
        b=run_b.model_dump(mode="json"),
        first_divergence=first_divergence,
        rows=rows,
        summary={
            "outcome": f"{run_a.outcome} -> {run_b.outcome}",
            "n_reused": run_b.n_reused if run_b.parent_run_id == run_a.run_id else None,
            "n_executed": run_b.n_executed
            if run_b.parent_run_id == run_a.run_id
            else None,
        },
    )


def compare(run_a: Run, run_b: Run) -> TraceComparison:
    bound_session = object_session(run_a) or object_session(run_b)
    if bound_session is not None:
        return _compare(bound_session, run_a, run_b)  # type: ignore[arg-type]
    with get_session() as session:
        return _compare(session, run_a, run_b)
