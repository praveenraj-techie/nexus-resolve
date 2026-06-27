from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .event_stream import EventStream
from .mock_execute import mock_execute
from .models import (
    ApprovalSummary,
    EvidenceSummary,
    IncidentTicket,
    PolicyCheck,
    RcaSummary,
    RemediationPlan,
    RunSnapshot,
    RunStatus,
    new_run_id,
    utc_now,
)
from .openai_client import NexusOpenAIClient
from .policy import has_blocking_check, policy_check
from .tools import (
    DATA_ROOT,
    get_incident_for_scenario,
    get_initial_state,
    retrieve_similar_tickets,
    retrieve_sop,
    validate_result,
)


@dataclass
class RunSession:
    run_id: str
    stream: EventStream
    status: RunStatus = "created"
    approval_future: asyncio.Future[bool] | None = None
    closure_future: asyncio.Future[str] | None = None
    done_future: asyncio.Future[None] | None = None
    evidence_summary: EvidenceSummary | None = None
    approval_summary: ApprovalSummary | None = None
    plan: RemediationPlan | None = None
    policy_checks: list[PolicyCheck] = field(default_factory=list)
    rca: RcaSummary | None = None
    approval_record: dict[str, Any] | None = None

    def snapshot(self) -> RunSnapshot:
        return RunSnapshot(
            run_id=self.run_id,
            status=self.status,
            events=self.stream.events,
            approval_record=self.approval_record,
            plan=self.plan,
            evidence_summary=self.evidence_summary,
            approval_summary=self.approval_summary,
            policy_checks=self.policy_checks,
            rca=self.rca,
        )


class RunManager:
    def __init__(
        self,
        openai_client: NexusOpenAIClient | None = None,
        event_delay_seconds: float = 0.0,
    ) -> None:
        self.openai_client = openai_client or NexusOpenAIClient()
        self.event_delay_seconds = event_delay_seconds
        self.sessions: dict[str, RunSession] = {}

    async def start_run(
        self, ticket: IncidentTicket | None = None, scenario_id: str = "disk-space"
    ) -> RunSession:
        run_id = new_run_id()
        loop = asyncio.get_running_loop()
        session = RunSession(
            run_id=run_id,
            stream=EventStream(run_id),
            approval_future=loop.create_future(),
            closure_future=loop.create_future(),
            done_future=loop.create_future(),
        )
        self.sessions[run_id] = session
        selected_ticket = ticket or get_incident_for_scenario(scenario_id)
        asyncio.create_task(self._execute(session, selected_ticket))
        return session

    def get_session(self, run_id: str) -> RunSession | None:
        return self.sessions.get(run_id)

    def approve(
        self, run_id: str, approval_record: dict[str, Any] | None = None
    ) -> RunSnapshot:
        session = self._require_session(run_id)
        if session.approval_future and not session.approval_future.done():
            session.approval_record = approval_record or {
                "operator": "Demo Operator",
                "role": "Incident Approver",
                "reason": "Approved mock-only remediation after policy review.",
                "recorded_at": utc_now().isoformat(),
            }
            session.approval_future.set_result(True)
        return session.snapshot()

    def reject(self, run_id: str) -> RunSnapshot:
        session = self._require_session(run_id)
        if session.approval_future and not session.approval_future.done():
            session.approval_future.set_result(False)
        return session.snapshot()

    def close_incident(self, run_id: str) -> RunSnapshot:
        session = self._require_session(run_id)
        if session.closure_future and not session.closure_future.done():
            session.closure_future.set_result("close")
        return session.snapshot()

    def observe_incident(self, run_id: str) -> RunSnapshot:
        session = self._require_session(run_id)
        if session.closure_future and not session.closure_future.done():
            session.closure_future.set_result("observe")
        return session.snapshot()

    def _require_session(self, run_id: str) -> RunSession:
        session = self.sessions.get(run_id)
        if not session:
            raise KeyError(f"Unknown run_id: {run_id}")
        return session

    async def _emit(
        self,
        session: RunSession,
        event_type: str,
        title: str,
        message: str,
        payload: dict[str, Any],
    ) -> None:
        await session.stream.emit(event_type, title, message, payload)
        if self.event_delay_seconds > 0:
            await asyncio.sleep(self.event_delay_seconds)

    def _ai_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        source = self.openai_client.last_response_source
        return {
            **payload,
            "ai_source": source,
            "model": self.openai_client.model,
            "generated_by": (
                "OpenAI Responses API"
                if source == "openai"
                else "Deterministic fallback"
            ),
        }

    async def _execute(self, session: RunSession, ticket: IncidentTicket) -> None:
        try:
            await self._run_workflow(session, ticket)
        except Exception as exc:
            session.status = "failed"
            await self._emit(
                session,
                "run.failed",
                "Run failed safely",
                "The workflow stopped without executing remediation.",
                {"error": str(exc)},
            )
        finally:
            if session.done_future and not session.done_future.done():
                session.done_future.set_result(None)

    async def _run_workflow(
        self, session: RunSession, ticket: IncidentTicket
    ) -> None:
        session.status = "running"
        await self._emit(
            session,
            "ticket.received",
            f"{ticket.team} alert received",
            f"{ticket.incident_id} reports {ticket.title} on {ticket.affected_ci}.",
            {
                "scenario_id": ticket.scenario_id,
                "team": ticket.team,
                "alert_type": ticket.metric_snapshot.get("alert_type", ticket.title),
                "incident_id": ticket.incident_id,
                "priority": ticket.priority,
                "ci": ticket.affected_ci,
                "service": ticket.business_service,
                "current_state": ticket.current_state,
                "requested_outcome": ticket.requested_outcome,
            },
        )

        sop = retrieve_sop(ticket)
        await self._emit(
            session,
            "evidence.sop",
            "SOP retrieved",
            sop.summary,
            sop.model_dump(mode="json"),
        )

        history = retrieve_similar_tickets(ticket)
        unsafe = [item for item in history if not item.metadata.get("safe")]
        escalations = [
            item for item in history if item.metadata.get("outcome") == "escalated"
        ]
        await self._emit(
            session,
            "evidence.history",
            "Historical tickets compared",
            f"{len(history)} similar tickets found; {len(unsafe)} unsafe precedent flagged.",
            {
                "safe_examples": len(history) - len(unsafe) - len(escalations),
                "unsafe_examples": len(unsafe),
                "escalations": len(escalations),
                "unsafe_ticket": unsafe[0].id if unsafe else None,
                "items": [item.model_dump(mode="json") for item in history],
            },
        )

        before_state = get_initial_state(ticket)

        if unsafe:
            await self._emit(
                session,
                "policy.warning",
                "SOP beats history",
                before_state["scenario"].get(
                    "unsafe_message", "Unsafe history is blocked by SOP controls."
                ),
                {"blocked_precedent": unsafe[0].model_dump(mode="json")},
            )

        session.evidence_summary = await self.openai_client.create_evidence_summary(
            ticket, sop, history, before_state
        )
        await self._emit_openai_notice_if_needed(session)
        await self._emit(
            session,
            "evidence.summary",
            "OpenAI evidence summary structured"
            if self.openai_client.last_response_source == "openai"
            else "Evidence summary structured",
            session.evidence_summary.outcome,
            self._ai_payload(session.evidence_summary.model_dump(mode="json")),
        )

        session.plan = await self.openai_client.create_plan(
            ticket, sop, history, before_state
        )
        await self._emit_openai_notice_if_needed(session)

        await self._emit(
            session,
            "plan.generated",
            "OpenAI remediation plan generated"
            if self.openai_client.last_response_source == "openai"
            else "Safe remediation plan generated",
            session.plan.summary,
            self._ai_payload(session.plan.model_dump(mode="json")),
        )

        session.policy_checks = policy_check(session.plan, enforce_approval=False)
        await self._emit(
            session,
            "policy.checked",
            "Policy gate passed with approval hold",
            "Policy allows planning but requires human approval before mock execution.",
            {"checks": [check.model_dump(mode="json") for check in session.policy_checks]},
        )

        non_approval_blockers = [
            check
            for check in session.policy_checks
            if check.status == "blocked" and check.name != "Human approval"
        ]
        if non_approval_blockers:
            session.status = "blocked"
            await self._emit(
                session,
                "policy.blocked",
                "Policy blocked remediation",
                "The remediation plan failed safety checks.",
                {"checks": [check.model_dump(mode="json") for check in session.policy_checks]},
            )
            return

        session.approval_summary = await self.openai_client.create_approval_summary(
            session.plan, session.policy_checks
        )
        await self._emit_openai_notice_if_needed(session)
        await self._emit(
            session,
            "approval.summary",
            "OpenAI approval package structured"
            if self.openai_client.last_response_source == "openai"
            else "Approval package structured",
            session.approval_summary.operator_message,
            self._ai_payload(session.approval_summary.model_dump(mode="json")),
        )

        session.status = "waiting_approval"
        await self._emit(
            session,
            "approval.requested",
            "Human approval required",
            "Operator review is required before mock remediation can continue.",
            {
                "plan": session.plan.model_dump(mode="json"),
                "approval_summary": session.approval_summary.model_dump(mode="json"),
            },
        )

        approved = await session.approval_future
        if not approved:
            session.status = "rejected"
            await self._emit(
                session,
                "approval.rejected",
                "Operator rejected remediation",
                "The run ended safely with no mock state change.",
                {"mock_execution_started": False},
            )
            return

        session.plan.approval_granted = True
        session.policy_checks = policy_check(session.plan, enforce_approval=True)
        await self._emit(
            session,
            "approval.granted",
            "Operator approved remediation",
            "Human approval was recorded and policy was rechecked.",
            {
                "approval_record": session.approval_record,
                "checks": [check.model_dump(mode="json") for check in session.policy_checks],
            },
        )

        if has_blocking_check(session.policy_checks):
            session.status = "blocked"
            await self._emit(
                session,
                "policy.blocked",
                "Policy blocked remediation",
                "The final pre-execution policy check failed.",
                {"checks": [check.model_dump(mode="json") for check in session.policy_checks]},
            )
            return

        after_state = mock_execute(session.plan, before_state)
        validation = validate_result(before_state, after_state)
        execution = after_state.get("execution", {})
        await self._emit(
            session,
            "execution.mocked",
            execution.get("title", "Mock remediation executed"),
            execution.get("message", "Validated mock remediation completed safely."),
            execution.get("payload", {"mock_only": True}),
        )

        await self._emit(
            session,
            "validation.passed" if validation.status == "pass" else "validation.failed",
            (
                "Scenario validation passed"
                if validation.status == "pass"
                else "Scenario validation failed"
            ),
            validation.message,
            validation.model_dump(mode="json"),
        )

        if validation.status != "pass":
            session.status = "escalated"
            return

        session.rca = await self.openai_client.create_rca(before_state, after_state)
        await self._emit_openai_notice_if_needed(session)
        await self._emit(
            session,
            "rca.generated",
            "OpenAI RCA and audit evidence generated"
            if self.openai_client.last_response_source == "openai"
            else "RCA and audit evidence generated",
            session.rca.root_cause,
            self._ai_payload(session.rca.model_dump(mode="json")),
        )

        session.status = "waiting_closure"
        await self._emit(
            session,
            "closure.requested",
            "Closure decision required",
            (
                "Remediation is validated. Operator can close the incident now "
                "or keep it under observation before closure."
            ),
            {
                "incident_id": ticket.incident_id,
                "options": [
                    {
                        "id": "close",
                        "label": "Approve closure",
                        "message": "Close the incident with RCA and audit evidence attached.",
                    },
                    {
                        "id": "observe",
                        "label": "Observe first",
                        "message": "Keep the incident under observation, recheck metrics, then close.",
                    },
                ],
            },
        )

        decision = await session.closure_future
        if decision == "observe":
            session.status = "observing"
            await self._emit(
                session,
                "observation.started",
                "Observation window started",
                "Synthetic observation is running before final incident closure.",
                {"duration_seconds": 60, "mock_duration_ms": 1200},
            )
            await asyncio.sleep(1.2)
            await self._emit(
                session,
                "observation.completed",
                "Observation check passed",
                "Recovery metrics remained healthy through the observation window.",
                {"validation": validation.model_dump(mode="json")},
            )

        session.status = "closed"
        await self._emit(
            session,
            "incident.closed",
            "Incident closed",
            f"{ticket.incident_id} was closed with RCA, evidence, and validation attached.",
            {
                "incident_id": ticket.incident_id,
                "closure_code": "Resolved by approved mock remediation",
                "final_status": "closed",
            },
        )
        session.stream.export_jsonl(
            Path(DATA_ROOT) / "generated" / "runs" / f"{session.run_id}.events.jsonl"
        )

    async def _emit_openai_notice_if_needed(self, session: RunSession) -> None:
        if not self.openai_client.last_notice:
            return
        await self._emit(
            session,
            "openai.fallback",
            "Validated fallback response used",
            self.openai_client.last_notice,
            {"model": self.openai_client.model},
        )
        self.openai_client.last_notice = None
