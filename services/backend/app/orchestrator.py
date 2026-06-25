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
)
from .openai_client import NexusOpenAIClient
from .policy import has_blocking_check, policy_check
from .tools import (
    DATA_ROOT,
    get_default_incident,
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
    done_future: asyncio.Future[None] | None = None
    evidence_summary: EvidenceSummary | None = None
    approval_summary: ApprovalSummary | None = None
    plan: RemediationPlan | None = None
    policy_checks: list[PolicyCheck] = field(default_factory=list)
    rca: RcaSummary | None = None

    def snapshot(self) -> RunSnapshot:
        return RunSnapshot(
            run_id=self.run_id,
            status=self.status,
            events=self.stream.events,
            plan=self.plan,
            evidence_summary=self.evidence_summary,
            approval_summary=self.approval_summary,
            policy_checks=self.policy_checks,
            rca=self.rca,
        )


class RunManager:
    def __init__(self, openai_client: NexusOpenAIClient | None = None) -> None:
        self.openai_client = openai_client or NexusOpenAIClient()
        self.sessions: dict[str, RunSession] = {}

    async def start_run(self, ticket: IncidentTicket | None = None) -> RunSession:
        run_id = new_run_id()
        loop = asyncio.get_running_loop()
        session = RunSession(
            run_id=run_id,
            stream=EventStream(run_id),
            approval_future=loop.create_future(),
            done_future=loop.create_future(),
        )
        self.sessions[run_id] = session
        asyncio.create_task(self._execute(session, ticket or get_default_incident()))
        return session

    def get_session(self, run_id: str) -> RunSession | None:
        return self.sessions.get(run_id)

    def approve(self, run_id: str) -> RunSnapshot:
        session = self._require_session(run_id)
        if session.approval_future and not session.approval_future.done():
            session.approval_future.set_result(True)
        return session.snapshot()

    def reject(self, run_id: str) -> RunSnapshot:
        session = self._require_session(run_id)
        if session.approval_future and not session.approval_future.done():
            session.approval_future.set_result(False)
        return session.snapshot()

    def _require_session(self, run_id: str) -> RunSession:
        session = self.sessions.get(run_id)
        if not session:
            raise KeyError(f"Unknown run_id: {run_id}")
        return session

    async def _execute(self, session: RunSession, ticket: IncidentTicket) -> None:
        try:
            await self._run_workflow(session, ticket)
        except Exception as exc:
            session.status = "failed"
            await session.stream.emit(
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
        await session.stream.emit(
            "ticket.received",
            "Synthetic P4 ticket received",
            (
                f"{ticket.incident_id} reports C: drive at "
                f"{ticket.metric_snapshot.get('used_percent')}% on {ticket.affected_ci}."
            ),
            {
                "incident_id": ticket.incident_id,
                "priority": ticket.priority,
                "ci": ticket.affected_ci,
                "service": ticket.business_service,
            },
        )

        sop = retrieve_sop(ticket)
        await session.stream.emit(
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
        await session.stream.emit(
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

        if unsafe:
            await session.stream.emit(
                "policy.warning",
                "SOP beats history",
                "Unsafe history deleted active logs, but SOP allows old app logs only.",
                {"blocked_precedent": unsafe[0].model_dump(mode="json")},
            )

        before_state = get_initial_state()
        session.evidence_summary = await self.openai_client.create_evidence_summary(
            ticket, sop, history, before_state
        )
        await self._emit_openai_notice_if_needed(session)
        await session.stream.emit(
            "evidence.summary",
            "Evidence summary structured",
            session.evidence_summary.outcome,
            session.evidence_summary.model_dump(mode="json"),
        )

        session.plan = await self.openai_client.create_plan(
            ticket, sop, history, before_state
        )
        await self._emit_openai_notice_if_needed(session)

        await session.stream.emit(
            "plan.generated",
            "Safe remediation plan generated",
            session.plan.summary,
            session.plan.model_dump(mode="json"),
        )

        session.policy_checks = policy_check(session.plan, enforce_approval=False)
        await session.stream.emit(
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
            await session.stream.emit(
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
        await session.stream.emit(
            "approval.summary",
            "Approval package structured",
            session.approval_summary.operator_message,
            session.approval_summary.model_dump(mode="json"),
        )

        session.status = "waiting_approval"
        await session.stream.emit(
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
            await session.stream.emit(
                "approval.rejected",
                "Operator rejected remediation",
                "The run ended safely with no mock state change.",
                {"mock_execution_started": False},
            )
            return

        session.plan.approval_granted = True
        session.policy_checks = policy_check(session.plan, enforce_approval=True)
        await session.stream.emit(
            "approval.granted",
            "Operator approved remediation",
            "Human approval was recorded and policy was rechecked.",
            {"checks": [check.model_dump(mode="json") for check in session.policy_checks]},
        )

        if has_blocking_check(session.policy_checks):
            session.status = "blocked"
            await session.stream.emit(
                "policy.blocked",
                "Policy blocked remediation",
                "The final pre-execution policy check failed.",
                {"checks": [check.model_dump(mode="json") for check in session.policy_checks]},
            )
            return

        after_state = mock_execute(session.plan, before_state)
        validation = validate_result(before_state, after_state)
        await session.stream.emit(
            "execution.mocked",
            "Mock remediation executed",
            "Validated mock cleanup reclaimed disk space without touching protected paths.",
            {
                "before_free_gb": before_state["drives"]["C:"]["free_gb"],
                "after_free_gb": after_state["drives"]["C:"]["free_gb"],
                "reclaimed_gb": after_state["drives"]["C:"]["free_gb"]
                - before_state["drives"]["C:"]["free_gb"],
                "mock_only": True,
            },
        )

        await session.stream.emit(
            "validation.passed" if validation.status == "pass" else "validation.failed",
            "Disk validation passed" if validation.status == "pass" else "Disk validation failed",
            validation.message,
            validation.model_dump(mode="json"),
        )

        if validation.status != "pass":
            session.status = "escalated"
            return

        session.rca = await self.openai_client.create_rca(before_state, after_state)
        await self._emit_openai_notice_if_needed(session)
        await session.stream.emit(
            "rca.generated",
            "RCA and audit evidence generated",
            session.rca.root_cause,
            session.rca.model_dump(mode="json"),
        )

        session.status = "resolved"
        session.stream.export_jsonl(
            Path(DATA_ROOT) / "generated" / "runs" / f"{session.run_id}.events.jsonl"
        )

    async def _emit_openai_notice_if_needed(self, session: RunSession) -> None:
        if not self.openai_client.last_notice:
            return
        await session.stream.emit(
            "openai.fallback",
            "Validated fallback response used",
            self.openai_client.last_notice,
            {"model": self.openai_client.model},
        )
        self.openai_client.last_notice = None
