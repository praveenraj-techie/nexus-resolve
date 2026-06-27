import asyncio

from app.openai_client import NexusOpenAIClient
from app.policy import policy_check
from app.tools import (
    get_default_incident,
    get_initial_state,
    retrieve_similar_tickets,
    retrieve_sop,
)


def test_mock_client_returns_evidence_plan_approval_and_rca_summaries():
    async def scenario():
        client = NexusOpenAIClient(mode="mock")
        ticket = get_default_incident()
        sop = retrieve_sop(ticket)
        history = retrieve_similar_tickets(ticket)
        state = get_initial_state()

        evidence = await client.create_evidence_summary(ticket, sop, history, state)
        plan = await client.create_plan(ticket, sop, history, state)
        checks = policy_check(plan, enforce_approval=False)
        approval = await client.create_approval_summary(plan, checks)

        assert len(evidence.unsafe_precedent_ids) == 1
        assert evidence.unsafe_precedent_ids[0].startswith("HIST-DISK")
        assert "SOP beats history" in evidence.governance_note
        assert plan.target_resources == ["APP-WIN-042:C:\\App\\Logs"]
        assert plan.mock_only is True
        assert approval.decision_required is True
        assert approval.blocked_until_approved is True

    asyncio.run(scenario())


def test_live_client_falls_back_when_openai_call_fails():
    async def scenario():
        client = NexusOpenAIClient(mode="live", api_key="invalid-test-key")
        client._create_plan_live = lambda *args: (_ for _ in ()).throw(  # type: ignore[method-assign]
            RuntimeError("simulated outage")
        )
        ticket = get_default_incident()
        sop = retrieve_sop(ticket)
        history = retrieve_similar_tickets(ticket)
        state = get_initial_state()

        plan = await client.create_plan(ticket, sop, history, state)

        assert plan.target_resources == ["APP-WIN-042:C:\\App\\Logs"]
        assert client.last_notice == "OpenAI unavailable, using validated fallback response"

    asyncio.run(scenario())
