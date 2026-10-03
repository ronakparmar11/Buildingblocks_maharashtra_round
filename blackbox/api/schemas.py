from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")


class CulpritScore(APIModel):
    step_key: str
    score: float


class RunSummary(APIModel):
    run_id: str
    task_id: str
    question: str
    origin: str
    outcome: str
    score_f1: float
    n_steps: int
    created_at: datetime
    predicted_culprit: CulpritScore | None
    parent_run_id: str | None


class RunListResponse(APIModel):
    items: list[RunSummary]
    total: int


class RunRecord(APIModel):
    run_id: str
    task_id: str
    origin: str
    parent_run_id: str | None
    final_answer: str | None
    outcome: str
    score_f1: float
    n_steps: int
    n_reused: int
    n_executed: int
    tokens_total: int
    tokens_saved: int
    latency_ms: int
    created_at: datetime
    replay_spec: dict[str, Any] | None


class TaskRecord(APIModel):
    task_id: str
    question: str
    gold_answer: str
    qtype: str
    level: str
    split: str
    gold_titles: list[str]
    distractor_pids: list[str]


class StepRecord(APIModel):
    step_id: str
    run_id: str
    step_key: str
    idx: int
    name: str
    type: str
    node_id: str
    attempt: int
    deps: list[str]
    input: dict[str, Any]
    input_hash: str
    output: dict[str, Any]
    output_hash: str
    output_text: str
    latency_ms: int
    tokens_in: int
    tokens_out: int
    model: str | None
    cache_hit: bool
    reused: bool
    overridden: bool
    state_snapshot: dict[str, Any]
    error: str | None
    meta: dict[str, Any]


class Edge(APIModel):
    source: str
    target: str


class FaultRecord(APIModel):
    run_id: str
    fault_type: str
    step_key: str
    params: dict[str, Any]


class LabelRecord(APIModel):
    run_id: str
    culprit_step_key: str
    method: str
    verified: bool
    confidence: float
    n_replays: int
    matches_injection: bool | None


class RunDetailResponse(APIModel):
    run: RunRecord
    task: TaskRecord
    steps: list[StepRecord]
    edges: list[Edge]
    fault: FaultRecord | None
    label: LabelRecord | None


class DiagnosisReason(APIModel):
    feature: str
    text: str
    evidence: str
    contribution: float


class DiagnosisItem(APIModel):
    step_key: str
    score: float
    rank: int
    reasons: list[DiagnosisReason]


class DiagnosisResponse(APIModel):
    run_id: str
    model_version: str
    latency_ms: float
    ranking: list[DiagnosisItem]


class OverrideRequest(APIModel):
    kind: Literal["set_output", "regenerate"]
    output: dict[str, Any] | None = None
    params: dict[str, Any] = Field(default_factory=dict)


class ReplayRequest(APIModel):
    overrides: dict[str, OverrideRequest] = Field(default_factory=dict)
    freeze_before_idx: int | None = None


class ReplayStats(APIModel):
    n_reused: int
    n_executed: int
    tokens_saved: int
    tokens_total: int
    latency_ms: int


class ReplayResponse(APIModel):
    run: RunSummary
    stats: ReplayStats
    compare_url: str


class BlastRadiusResponse(APIModel):
    step_key: str
    affected: list[str]


class RepairRequest(APIModel):
    top_k: int = Field(default=3, ge=1)


class RepairAttemptResponse(APIModel):
    step_key: str
    strategy: str
    run_id: str
    outcome: str
    n_executed: int
    n_reused: int
    tokens_total: int


class RepairResponse(APIModel):
    attempts: list[RepairAttemptResponse]
    repaired: bool
    winning_run_id: str | None


class JobCreatedResponse(APIModel):
    job_id: str


class JobResponse(APIModel):
    status: Literal["queued", "running", "completed", "failed"]
    progress: float = Field(ge=0.0, le=1.0)
    result: dict[str, Any] | None


class CompareRow(APIModel):
    step_key: str
    status: Literal["same", "changed", "only_a", "only_b"]
    a_step: StepRecord | None
    b_step: StepRecord | None
    text_diff: list[str]


class CompareResponse(APIModel):
    a: RunSummary
    b: RunSummary
    first_divergence: str | None
    rows: list[CompareRow]


class EvalResponse(RootModel[dict[str, Any]]):
    pass


class FleetStepCount(APIModel):
    name: str
    count: int
    pct: float


class FleetReasonCount(APIModel):
    feature: str
    text: str
    count: int


class FleetFaultCount(APIModel):
    fault_type: str
    count: int
    pct: float


class FleetResponse(APIModel):
    by_step_name: list[FleetStepCount]
    by_reason: list[FleetReasonCount]
    by_fault_type: list[FleetFaultCount]
    total_failed: int


class TaskListResponse(RootModel[list[TaskRecord]]):
    pass


class FaultTargetResponse(APIModel):
    fault_type: str
    step_key: str


class FaultTargetsResponse(APIModel):
    targets: list[FaultTargetResponse]


class LiveFaultRequest(APIModel):
    fault_type: str
    step_key: str


class LiveRunRequest(APIModel):
    task_id: str
    fault: LiveFaultRequest | None = None


class LiveRunResponse(APIModel):
    run_id: str


class HealthResponse(APIModel):
    status: Literal["ok"]
    demo_mode: bool
    model_version: str
    n_runs: int