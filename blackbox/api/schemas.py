from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel, field_validator


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
    incident_id: str | None = None


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


class GoldenDemoResponse(APIModel):
    run: RunDetailResponse
    diagnosis: DiagnosisResponse
    repair: RepairResponse


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


class WorkspaceSummary(APIModel):
    id: str
    name: str
    description: str
    n_runs: int


class IncidentSummary(APIModel):
    incident_id: str
    title: str
    severity: str
    status: str
    n_runs: int
    est_cost_inr: int
    category: str
    cause_step_name: str
    first_seen: datetime
    last_seen: datetime
    owner: str


class IncidentListResponse(APIModel):
    items: list[IncidentSummary]
    total: int


class DailyMetric(APIModel):
    date: str
    conversations: int
    wrong: int
    rate: float


class OverviewKpis(APIModel):
    conversations: int
    wrong: int
    failure_rate: float
    open_incidents: int
    estimated_cost_inr: int


class OverviewResponse(APIModel):
    headline: str
    kpis: OverviewKpis
    daily: list[DailyMetric]
    open_incidents: list[IncidentSummary]
    by_step_name: list[FleetStepCount]
    by_reason: list[FleetReasonCount]
    threshold: float


class IncidentEventRecord(APIModel):
    event_id: str
    incident_id: str
    kind: str
    text: str
    created_at: datetime
    meta: dict[str, Any]


class IncidentRunSummary(RunSummary):
    customer_message: str
    agent_reply: str
    correct_answer: str


class NotificationSummary(APIModel):
    notification_id: str
    workspace: str
    rule_kind: str
    incident_id: str | None
    recipients: list[str]
    subject: str
    status: str
    error: str | None
    created_at: datetime
    sent_at: datetime | None


class IncidentDetailResponse(APIModel):
    incident: IncidentSummary
    explanation: str
    representative_run: RunSummary | None
    reasons: list[DiagnosisReason]
    runs: list[IncidentRunSummary]
    events: list[IncidentEventRecord]
    notifications: list[NotificationSummary]


class IncidentPatchRequest(APIModel):
    status: Literal["open", "investigating", "fix_verified", "resolved", "reopened"] | None = None
    owner: str | None = None
    note: str | None = None


class VerifyFixRequest(APIModel):
    repair_run_id: str


class NotificationIdResponse(APIModel):
    notification_id: str


class NotificationStatusResponse(APIModel):
    configured: bool
    host: str
    port: int
    connected: bool
    sender: str
    last_error: str | None
    demo_mode_blocked: bool


def _validate_email(value: str) -> str:
    local, separator, domain = value.strip().rpartition("@")
    if not separator or not local or "." not in domain or domain.startswith("."):
        raise ValueError("Enter a valid email address")
    return value.strip()


def _validate_optional_email(value: str | None) -> str | None:
    return _validate_email(value) if value is not None else None


class NotificationTestRequest(APIModel):
    to: str

    _email = field_validator("to")(_validate_email)


class NotificationTestResponse(APIModel):
    status: str
    error: str | None


class RecipientCreate(APIModel):
    name: str
    email: str
    workspace: str = "nimbu"
    active: bool = True
    rules: list[str] = Field(default_factory=list)

    _email = field_validator("email")(_validate_email)


class RecipientUpdate(APIModel):
    name: str | None = None
    email: str | None = None
    active: bool | None = None
    rules: list[str] | None = None

    _email = field_validator("email")(_validate_optional_email)


class RecipientResponse(APIModel):
    recipient_id: str
    name: str
    email: str
    workspace: str
    active: bool
    rules: list[str]


class RuleUpdate(APIModel):
    enabled: bool
    params: dict[str, Any] = Field(default_factory=dict)


class RuleResponse(APIModel):
    rule_id: str
    workspace: str
    kind: str
    enabled: bool
    params: dict[str, Any]


class BusinessSettingsRequest(APIModel):
    cost_per_wrong_answer_inr: int = Field(ge=0)


class BusinessSettingsResponse(APIModel):
    cost_per_wrong_answer_inr: int


class NotificationListResponse(APIModel):
    items: list[NotificationSummary]


class NotificationPreviewResponse(APIModel):
    subject: str
    html: str
    text: str


class SimulateRequest(APIModel):
    workspace: str = "nimbu"
    n: int = Field(default=30, ge=1, le=500)
    failure_rate: float = Field(default=0.35, ge=0.0, le=1.0)
    seed: int = 7