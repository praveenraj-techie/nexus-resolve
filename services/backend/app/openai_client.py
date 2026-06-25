from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from pydantic import BaseModel

from .models import (
    ApprovalSummary,
    EvidenceItem,
    EvidenceSummary,
    IncidentTicket,
    PolicyCheck,
    RemediationPlan,
    RcaSummary,
)
from .rca import fallback_rca
from .tools import PROJECT_ROOT, estimate_reclaimable_space

try:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")
except Exception:
    pass


class PlanOutput(BaseModel):
    summary: str
    target_paths: list[str]
    estimated_reclaim_gb: float
    age_filter_days: int
    powershell: str
    approval_required: bool
    uses_whatif: bool
    mock_only: bool
    validation_steps: list[str]
    escalation_condition: str


class EvidenceSummaryOutput(BaseModel):
    outcome: str
    sop_controls: list[str]
    safe_precedent_count: int
    unsafe_precedent_ids: list[str]
    escalation_precedent_ids: list[str]
    governance_note: str


class ApprovalSummaryOutput(BaseModel):
    decision_required: bool
    operator_message: str
    expected_safe_effect: str
    blocked_until_approved: bool
    replay_side_effects_disabled: bool


class RcaMetricsOutput(BaseModel):
    reclaimed_gb: float
    before_free_gb: float
    after_free_gb: float
    mttr_minutes: int
    manual_steps_avoided: int
    audit_completeness_percent: int


class RcaOutput(BaseModel):
    root_cause: str
    actions_taken: list[str]
    validation: str
    business_impact: str
    follow_up: list[str]
    metrics: RcaMetricsOutput


class NexusOpenAIClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        mode: str | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-5.5")
        self.mode = mode or os.getenv("APP_MODE", "mock")
        self.last_notice: str | None = None

    async def create_evidence_summary(
        self,
        ticket: IncidentTicket,
        sop: EvidenceItem,
        history: list[EvidenceItem],
        state: dict[str, Any],
    ) -> EvidenceSummary:
        if self.mode == "live" and self.api_key:
            try:
                return await asyncio.to_thread(
                    self._create_evidence_summary_live, ticket, sop, history, state
                )
            except Exception:
                self.last_notice = (
                    "OpenAI unavailable, using validated fallback response"
                )
        return self._fallback_evidence_summary(history)

    async def create_plan(
        self,
        ticket: IncidentTicket,
        sop: EvidenceItem,
        history: list[EvidenceItem],
        state: dict[str, Any],
    ) -> RemediationPlan:
        if self.mode == "live" and self.api_key:
            try:
                return await asyncio.to_thread(
                    self._create_plan_live, ticket, sop, history, state
                )
            except Exception:
                self.last_notice = (
                    "OpenAI unavailable, using validated fallback response"
                )
        return self._fallback_plan(state)

    async def create_approval_summary(
        self, plan: RemediationPlan, checks: list[PolicyCheck]
    ) -> ApprovalSummary:
        if self.mode == "live" and self.api_key:
            try:
                return await asyncio.to_thread(
                    self._create_approval_summary_live, plan, checks
                )
            except Exception:
                self.last_notice = (
                    "OpenAI unavailable, using validated fallback response"
                )
        return self._fallback_approval_summary(plan)

    async def create_rca(
        self, before: dict[str, Any], after: dict[str, Any]
    ) -> RcaSummary:
        if self.mode == "live" and self.api_key:
            try:
                return await asyncio.to_thread(self._create_rca_live, before, after)
            except Exception:
                self.last_notice = (
                    "OpenAI unavailable, using validated fallback response"
                )
        return fallback_rca(before, after)

    def _create_evidence_summary_live(
        self,
        ticket: IncidentTicket,
        sop: EvidenceItem,
        history: list[EvidenceItem],
        state: dict[str, Any],
    ) -> EvidenceSummary:
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)
        response = client.responses.parse(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Return an evidence summary as structured JSON. "
                        "Use supplied facts only. SOP outranks history. "
                        "Be concise and outcome-first."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "ticket": ticket.model_dump(),
                            "sop": sop.model_dump(),
                            "history": [item.model_dump() for item in history],
                            "state": state,
                        }
                    ),
                },
            ],
            text_format=EvidenceSummaryOutput,
            reasoning={"effort": "low"},
            text={"verbosity": "low"},
        )
        return EvidenceSummary.model_validate(response.output_parsed.model_dump())

    def _create_plan_live(
        self,
        ticket: IncidentTicket,
        sop: EvidenceItem,
        history: list[EvidenceItem],
        state: dict[str, Any],
    ) -> RemediationPlan:
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)
        response = client.responses.parse(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "You produce JSON only through structured outputs. "
                        "Use supplied facts only. SOP outranks historical tickets. "
                        "The outcome is a safe, approval-gated, mock-only remediation plan."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "ticket": ticket.model_dump(),
                            "sop": sop.model_dump(),
                            "history": [item.model_dump() for item in history],
                            "state": state,
                        }
                    ),
                },
            ],
            text_format=PlanOutput,
            reasoning={"effort": "low"},
            text={"verbosity": "low"},
        )
        parsed = response.output_parsed
        return RemediationPlan(
            summary=parsed.summary,
            target_paths=parsed.target_paths,
            estimated_reclaim_gb=parsed.estimated_reclaim_gb,
            age_filter_days=parsed.age_filter_days,
            powershell=parsed.powershell,
            approval_required=parsed.approval_required,
            uses_whatif=parsed.uses_whatif,
            mock_only=parsed.mock_only,
            validation_steps=parsed.validation_steps,
            escalation_condition=parsed.escalation_condition,
        )

    def _create_approval_summary_live(
        self, plan: RemediationPlan, checks: list[PolicyCheck]
    ) -> ApprovalSummary:
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)
        response = client.responses.parse(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Return an approval summary as structured JSON. "
                        "Use supplied facts only. The operator must understand "
                        "that execution is blocked until approval."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "plan": plan.model_dump(),
                            "policy_checks": [check.model_dump() for check in checks],
                        }
                    ),
                },
            ],
            text_format=ApprovalSummaryOutput,
            reasoning={"effort": "low"},
            text={"verbosity": "low"},
        )
        return ApprovalSummary.model_validate(response.output_parsed.model_dump())

    def _create_rca_live(
        self, before: dict[str, Any], after: dict[str, Any]
    ) -> RcaSummary:
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)
        response = client.responses.parse(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Return an RCA summary as structured JSON. Use supplied "
                        "facts only. Keep it concise and audit-ready."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps({"before": before, "after": after}),
                },
            ],
            text_format=RcaOutput,
            reasoning={"effort": "low"},
            text={"verbosity": "low"},
        )
        parsed = response.output_parsed
        payload = parsed.model_dump()
        payload["metrics"] = parsed.metrics.model_dump()
        return RcaSummary.model_validate(payload)

    def _fallback_evidence_summary(
        self, history: list[EvidenceItem]
    ) -> EvidenceSummary:
        unsafe = [item.id for item in history if not item.metadata.get("safe")]
        escalations = [
            item.id for item in history if item.metadata.get("outcome") == "escalated"
        ]
        safe_count = len(history) - len(unsafe) - len(escalations)
        return EvidenceSummary(
            outcome=(
                "Proceed with SOP-governed app log cleanup planning while excluding "
                "unsafe historical precedent."
            ),
            sop_controls=[
                "Delete only application logs older than 7 days.",
                "Never touch protected paths or active logs.",
                "Estimate reclaimed space before action.",
                "Require human approval.",
                "Validate free space after remediation.",
                "Escalate if free space remains below 15%.",
            ],
            safe_precedent_count=safe_count,
            unsafe_precedent_ids=unsafe,
            escalation_precedent_ids=escalations,
            governance_note=(
                "SOP beats history: HIST-2026-0037 is visible as a warning, "
                "not copied into the remediation plan."
            ),
        )

    def _fallback_plan(self, state: dict[str, Any]) -> RemediationPlan:
        estimate = estimate_reclaimable_space(state)
        return RemediationPlan(
            summary=(
                "Clean approved application logs older than 7 days from C:\\App\\Logs "
                "using a mock-only, approval-gated flow."
            ),
            target_paths=["C:\\App\\Logs"],
            estimated_reclaim_gb=estimate,
            age_filter_days=7,
            powershell=(
                "Get-ChildItem 'C:\\App\\Logs' -File -Recurse | "
                "Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) } | "
                "Remove-Item -WhatIf"
            ),
            approval_required=True,
            uses_whatif=True,
            mock_only=True,
            validation_steps=[
                "Compare C: free GB before and after mock execution.",
                "Confirm free space is at least 15% of capacity.",
                "Confirm no active logs or protected paths were touched.",
            ],
        )

    def _fallback_approval_summary(self, plan: RemediationPlan) -> ApprovalSummary:
        target = ", ".join(plan.target_paths)
        return ApprovalSummary(
            decision_required=True,
            operator_message=(
                f"Approve mock-only cleanup for {target} using a "
                f"{plan.age_filter_days}-day age filter and WhatIf review."
            ),
            expected_safe_effect=(
                f"Expected reclaim is {plan.estimated_reclaim_gb:g} GB before "
                "post-remediation validation."
            ),
            blocked_until_approved=True,
            replay_side_effects_disabled=True,
        )
