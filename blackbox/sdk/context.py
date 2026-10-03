from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Literal

from blackbox.store.models import Task


def _empty_snapshot() -> dict[str, Any]:
    return {}


@dataclass
class Override:
    kind: Literal["set_output", "regenerate", "fault"]
    output: dict[str, Any] | None = None
    params: dict[str, Any] = field(default_factory=dict)
    fault_type: str | None = None
    fault_params: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionContext:
    run_id: str
    task: Task
    origin: str
    source_run_id: str | None = None
    overrides: dict[str, Override] = field(default_factory=dict)
    freeze_before_idx: int | None = None
    demo_mode: bool = False
    state_snapshot: Callable[[], dict[str, Any]] = _empty_snapshot


current_context: ContextVar[ExecutionContext | None] = ContextVar(
    "blackbox_execution_context", default=None
)
