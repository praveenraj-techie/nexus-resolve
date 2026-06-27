from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


PolicyStatus = Literal["pass", "blocked", "requires_approval"]
RunStatus = Literal[
    "created",
    "running",
    "waiting_approval",
    "waiting_closure",
    "observing",
    "closed",
    "rejected",
    "blocked",
    "escalated",
    "failed",
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_run_id() -> str:
    return f"run-{uuid4().hex[:12]}"


class IncidentTicket(BaseModel):
    scenario_id: str = "disk-space"
    team: str = "Windows Infra"
    incident_id: str
    priority: str
    title: str
    business_service: str
    affected_ci: str
    environment: str = "synthetic"
    symptoms: list[str] = Field(default_factory=list)
    metric_snapshot: dict[str, Any] = Field(default_factory=dict)
    current_state: str = ""
    requested_outcome: str


class EvidenceItem(BaseModel):
    id: str
    type: Literal["sop", "history", "state", "warning"]
    title: str
    summary: str
    source: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceSummary(BaseModel):
    outcome: str
    sop_controls: list[str]
    safe_precedent_count: int
    unsafe_precedent_ids: list[str]
    escalation_precedent_ids: list[str]
    governance_note: str


class PolicyCheck(BaseModel):
    name: str
    status: PolicyStatus
    message: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class RemediationPlan(BaseModel):
    summary: str
    target_resources: list[str]
    action_preview: str
    estimated_effect: str
    safeguards: list[str] = Field(default_factory=list)
    approval_required: bool = True
    approval_granted: bool = False
    uses_dry_run: bool = True
    mock_only: bool = True
    validation_steps: list[str] = Field(default_factory=list)
    escalation_condition: str = "Escalate if validation remains below threshold."


class ApprovalSummary(BaseModel):
    decision_required: bool
    operator_message: str
    expected_safe_effect: str
    blocked_until_approved: bool
    replay_side_effects_disabled: bool = True


class RunEvent(BaseModel):
    run_id: str
    sequence: int
    timestamp: datetime
    type: str
    title: str
    message: str
    payload: dict[str, Any] | None = None


class RcaSummary(BaseModel):
    root_cause: str
    actions_taken: list[str]
    validation: str
    business_impact: str
    follow_up: list[str]
    metrics: dict[str, Any] = Field(default_factory=dict)


class RunSnapshot(BaseModel):
    run_id: str
    status: RunStatus
    events: list[RunEvent]
    approval_record: dict[str, Any] | None = None
    plan: RemediationPlan | None = None
    evidence_summary: EvidenceSummary | None = None
    approval_summary: ApprovalSummary | None = None
    policy_checks: list[PolicyCheck] = Field(default_factory=list)
    rca: RcaSummary | None = None
