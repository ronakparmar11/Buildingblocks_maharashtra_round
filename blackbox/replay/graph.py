from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from blackbox.store.db import get_session, init_db
from blackbox.store.models import Step
from blackbox.store.repo import get_run, get_steps


@dataclass(frozen=True)
class DAG:
    children: dict[str, tuple[str, ...]]
    parents: dict[str, tuple[str, ...]]

    def descendants(self, step_key: str) -> set[str]:
        if step_key not in self.children:
            raise KeyError(step_key)
        found: set[str] = set()
        pending = list(self.children[step_key])
        while pending:
            child = pending.pop()
            if child in found:
                continue
            found.add(child)
            pending.extend(self.children[child])
        return found


def build_dag(deps: Mapping[str, Iterable[str]]) -> DAG:
    nodes = set(deps)
    nodes.update(dependency for values in deps.values() for dependency in values)
    parents = {node: tuple(deps.get(node, ())) for node in nodes}
    children_lists = {node: [] for node in nodes}
    for child, dependencies in parents.items():
        for parent in dependencies:
            children_lists[parent].append(child)
    children = {node: tuple(sorted(values)) for node, values in children_lists.items()}
    dag = DAG(children=children, parents=parents)
    for node in nodes:
        dag_depth(dag, node)
    return dag


def dag_from_steps(steps: Iterable[Step]) -> DAG:
    return build_dag({step.step_key: step.deps for step in steps})


def descendants(dag: DAG, step_key: str) -> set[str]:
    return dag.descendants(step_key)


def dag_depth(dag: DAG, step_key: str) -> int:
    if step_key not in dag.parents:
        raise KeyError(step_key)

    def depth(node: str, visiting: set[str]) -> int:
        if node in visiting:
            raise ValueError("Step dependencies contain a cycle")
        parents = dag.parents[node]
        if not parents:
            return 0
        return 1 + max(depth(parent, visiting | {node}) for parent in parents)

    return depth(step_key, set())


def _blast_radius(steps: list[Step], step_key: str) -> list[str]:
    by_key = {step.step_key: step for step in steps}
    affected = dag_from_steps(steps).descendants(step_key)
    return [
        step.step_key
        for step in steps
        if step.step_key in affected and step.step_key in by_key
    ]


def blast_radius(run_id: str, step_key: str) -> list[str]:
    init_db()
    with get_session() as session:
        if get_run(session, run_id) is None:
            raise ValueError(f"Unknown run id: {run_id}")
        return _blast_radius(get_steps(session, run_id), step_key)
