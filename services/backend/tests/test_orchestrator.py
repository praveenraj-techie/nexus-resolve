import asyncio

from app.openai_client import NexusOpenAIClient
from app.orchestrator import RunManager
from app.tools import get_default_incident


async def wait_for_status(session, status: str, timeout: float = 2.0):
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        if session.status == status:
            return
        await asyncio.sleep(0.01)
    raise AssertionError(f"Timed out waiting for status {status}; saw {session.status}")


def test_golden_disk_flow_completes_after_approval():
    async def scenario():
        manager = RunManager(openai_client=NexusOpenAIClient(mode="mock"))
        session = await manager.start_run(get_default_incident())
        await wait_for_status(session, "waiting_approval")

        manager.approve(session.run_id)
        await wait_for_status(session, "resolved")

        events = session.stream.events
        assert [event.sequence for event in events] == list(range(1, len(events) + 1))
        assert any(event.type == "policy.warning" for event in events)
        assert any(event.type == "evidence.summary" for event in events)
        assert any(event.type == "approval.summary" for event in events)
        assert any(event.type == "approval.requested" for event in events)
        assert any(event.type == "execution.mocked" for event in events)
        assert any(event.type == "rca.generated" for event in events)
        assert session.evidence_summary is not None
        assert session.approval_summary is not None
        assert session.rca is not None
        assert session.rca.metrics["after_free_gb"] == 44

    asyncio.run(scenario())


def test_rejection_ends_run_safely():
    async def scenario():
        manager = RunManager(openai_client=NexusOpenAIClient(mode="mock"))
        session = await manager.start_run(get_default_incident())
        await wait_for_status(session, "waiting_approval")

        manager.reject(session.run_id)
        await wait_for_status(session, "rejected")

        assert any(event.type == "approval.rejected" for event in session.stream.events)
        assert not any(event.type == "execution.mocked" for event in session.stream.events)

    asyncio.run(scenario())
