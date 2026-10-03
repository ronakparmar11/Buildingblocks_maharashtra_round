from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def _uuid4_hex() -> str:
    return uuid4().hex


def _utc_now() -> datetime:
    return datetime.now(UTC)


class Task(SQLModel, table=True):
    task_id: str = Field(primary_key=True)
    question: str
    gold_answer: str
    qtype: str
    level: str
    split: str
    gold_titles: list[str] = Field(sa_column=Column(JSON, nullable=False))
    distractor_pids: list[str] = Field(sa_column=Column(JSON, nullable=False))


class Run(SQLModel, table=True):
    run_id: str = Field(default_factory=_uuid4_hex, primary_key=True)
    task_id: str = Field(foreign_key="task.task_id")
    origin: str
    parent_run_id: str | None = None
    final_answer: str | None = None
    outcome: str
    score_f1: float
    n_steps: int
    n_reused: int
    n_executed: int
    tokens_total: int
    tokens_saved: int
    latency_ms: int
    created_at: datetime = Field(default_factory=_utc_now)
    replay_spec: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSON, nullable=True)
    )


class Fault(SQLModel, table=True):
    run_id: str = Field(primary_key=True, foreign_key="run.run_id")
    fault_type: str
    step_key: str
    params: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))


class Step(SQLModel, table=True):
    step_id: str = Field(default_factory=_uuid4_hex, primary_key=True)
    run_id: str = Field(foreign_key="run.run_id", index=True)
    step_key: str = Field(index=True)
    idx: int
    name: str
    type: str
    node_id: str
    attempt: int
    deps: list[str] = Field(sa_column=Column(JSON, nullable=False))
    input: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))
    input_hash: str
    output: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))
    output_hash: str
    output_text: str
    latency_ms: int
    tokens_in: int
    tokens_out: int
    model: str | None = None
    cache_hit: bool
    reused: bool
    overridden: bool
    state_snapshot: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))
    error: str | None = None
    meta: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))


class Label(SQLModel, table=True):
    run_id: str = Field(primary_key=True, foreign_key="run.run_id")
    culprit_step_key: str
    method: str
    verified: bool
    confidence: float
    n_replays: int
    matches_injection: bool | None = None


class Prediction(SQLModel, table=True):
    run_id: str = Field(primary_key=True, foreign_key="run.run_id")
    step_key: str = Field(primary_key=True)
    score: float
    rank: int
    model_version: str
    reasons: list[dict[str, Any]] = Field(sa_column=Column(JSON, nullable=False))


class Cassette(SQLModel, table=True):
    key: str = Field(primary_key=True)
    kind: str
    response: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))
    tokens_in: int
    tokens_out: int
    created_at: datetime = Field(default_factory=_utc_now)
