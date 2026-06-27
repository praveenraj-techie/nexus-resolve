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
from .tools import PROJECT_ROOT


def load_project_env() -> None:
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip().lstrip("\ufeff")
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


load_project_env()


class PlanOutput(BaseModel):
    summary: str
    target_resources: list[str]
    action_preview: str
    estimated_effect: str
    safeguards: list[str]
    approval_required: bool
    uses_dry_run: bool
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


class RcaMetricOutput(BaseModel):
    label: str
    value: str


class RcaOutput(BaseModel):
    root_cause: str
    actions_taken: list[str]
    validation: str
    business_impact: str
    follow_up: list[str]
    metrics: list[RcaMetricOutput]


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
        self.last_response_source = "fallback"

    async def create_evidence_summary(
        self,
        ticket: IncidentTicket,
        sop: EvidenceItem,
        history: list[EvidenceItem],
        state: dict[str, Any],
    ) -> EvidenceSummary:
        if self.mode == "live" and not self.api_key:
            self.last_notice = "OpenAI API key is not configured, using validated fallback response"
        if self.mode == "live" and self.api_key:
            try:
                result = await asyncio.to_thread(
                    self._create_evidence_summary_live, ticket, sop, history, state
                )
                self.last_response_source = "openai"
                return result
            except Exception:
                self.last_notice = (
                    "OpenAI unavailable, using validated fallback response"
                )
        self.last_response_source = "fallback"
        return self._fallback_evidence_summary(ticket, sop, history, state)

    async def create_plan(
        self,
        ticket: IncidentTicket,
        sop: EvidenceItem,
        history: list[EvidenceItem],
        state: dict[str, Any],
    ) -> RemediationPlan:
        if self.mode == "live" and not self.api_key:
            self.last_notice = "OpenAI API key is not configured, using validated fallback response"
        if self.mode == "live" and self.api_key:
            try:
                result = await asyncio.to_thread(
                    self._create_plan_live, ticket, sop, history, state
                )
                self.last_response_source = "openai"
                return result
            except Exception:
                self.last_notice = (
                    "OpenAI unavailable, using validated fallback response"
                )
        self.last_response_source = "fallback"
        return self._fallback_plan(state)

    async def create_approval_summary(
        self, plan: RemediationPlan, checks: list[PolicyCheck]
    ) -> ApprovalSummary:
        if self.mode == "live" and not self.api_key:
            self.last_notice = "OpenAI API key is not configured, using validated fallback response"
        if self.mode == "live" and self.api_key:
            try:
                result = await asyncio.to_thread(
                    self._create_approval_summary_live, plan, checks
                )
                self.last_response_source = "openai"
                return result
            except Exception:
                self.last_notice = (
                    "OpenAI unavailable, using validated fallback response"
                )
        self.last_response_source = "fallback"
        return self._fallback_approval_summary(plan)

    async def create_rca(
        self, before: dict[str, Any], after: dict[str, Any]
    ) -> RcaSummary:
        if self.mode == "live" and not self.api_key:
            self.last_notice = "OpenAI API key is not configured, using validated fallback response"
        if self.mode == "live" and self.api_key:
            try:
                result = await asyncio.to_thread(self._create_rca_live, before, after)
                self.last_response_source = "openai"
                return result
            except Exception:
                self.last_notice = (
                    "OpenAI unavailable, using validated fallback response"
                )
        self.last_response_source = "fallback"
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
                        "Write a fresh, operator-facing explanation for this "
                        "specific incident. Do not copy the plan template or "
                        "fallback phrasing verbatim. Mention the incident signal, "
                        "the unsafe precedent, and why the SOP-governed path is safe."
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
                        "The outcome is a safe, approval-gated, mock-only remediation "
                        "plan. Write a fresh operator-ready plan for this exact "
                        "scenario; do not copy the plan template verbatim. Keep the "
                        "action mock-only and include measurable validation."
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
            target_resources=parsed.target_resources,
            action_preview=parsed.action_preview,
            estimated_effect=parsed.estimated_effect,
            safeguards=parsed.safeguards,
            approval_required=parsed.approval_required,
            uses_dry_run=parsed.uses_dry_run,
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
                        "that execution is blocked until approval. Explain the "
                        "specific target, expected effect, and reason approval is "
                        "safe for this incident."
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
                        "facts only. Write a fresh audit-ready RCA for this exact "
                        "incident, with root cause, actions taken, validation, "
                        "business impact, follow-up, and measurable metrics. Do not "
                        "copy the fallback RCA wording verbatim."
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
        payload["metrics"] = {metric.label: metric.value for metric in parsed.metrics}
        return RcaSummary.model_validate(payload)

    def _fallback_evidence_summary(
        self,
        ticket: IncidentTicket,
        sop: EvidenceItem,
        history: list[EvidenceItem],
        state: dict[str, Any],
    ) -> EvidenceSummary:
        if "evidence_summary" in state:
            return EvidenceSummary.model_validate(state["evidence_summary"])

        unsafe = [item.id for item in history if not item.metadata.get("safe")]
        escalations = [
            item.id for item in history if item.metadata.get("outcome") == "escalated"
        ]
        safe_count = len(history) - len(unsafe) - len(escalations)
        return EvidenceSummary(
            outcome=f"Proceed with SOP-governed mock remediation for {ticket.title}.",
            sop_controls=list(sop.metadata.get("controls", [])),
            safe_precedent_count=safe_count,
            unsafe_precedent_ids=unsafe,
            escalation_precedent_ids=escalations,
            governance_note=(
                f"SOP beats history: {unsafe[0]} is visible as a warning, "
                "not copied into the remediation plan."
                if unsafe
                else "SOP controls drive the remediation plan."
            ),
        )

    def _fallback_plan(self, state: dict[str, Any]) -> RemediationPlan:
        if "plan_template" in state:
            return RemediationPlan.model_validate(state["plan_template"])

        return RemediationPlan(
            summary="Run a scenario-approved mock remediation.",
            target_resources=["synthetic-resource"],
            action_preview="Mock action only.",
            estimated_effect="Scenario validation should improve.",
            safeguards=["Mock-only execution.", "Human approval required."],
            approval_required=True,
            uses_dry_run=True,
            mock_only=True,
            validation_steps=["Validate scenario metrics after mock execution."],
        )

    def _fallback_approval_summary(self, plan: RemediationPlan) -> ApprovalSummary:
        target = ", ".join(plan.target_resources)
        return ApprovalSummary(
            decision_required=True,
            operator_message=(
                f"Approve mock-only remediation for {target}."
            ),
            expected_safe_effect=(
                f"{plan.estimated_effect} Post-remediation validation is required."
            ),
            blocked_until_approved=True,
            replay_side_effects_disabled=True,
        )
