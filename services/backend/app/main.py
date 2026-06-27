from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .models import IncidentTicket, utc_now
from .orchestrator import RunManager
from .policy import policy_check
from .models import RemediationPlan
from .scenario_catalog import get_replay_path
from .tools import get_incident_for_scenario, get_scenario_summaries


class IncidentStartRequest(BaseModel):
    scenario_id: str = "disk-space"
    ticket: IncidentTicket | None = None


class ApprovalRequest(BaseModel):
    operator: str = "Demo Operator"
    role: str = "Incident Approver"
    reason: str = "Approved mock-only remediation after policy review."


app = FastAPI(title="NEXUS-RESOLVE API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = RunManager(event_delay_seconds=1.4)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "nexus-resolve"}


@app.get("/api/scenarios")
def scenarios():
    return {"scenarios": get_scenario_summaries()}


@app.get("/api/connectors/servicenow/mock-ticket/{scenario_id}")
def servicenow_mock_ticket(scenario_id: str):
    try:
        ticket = get_incident_for_scenario(scenario_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Scenario not found") from None
    return {
        "connector": "servicenow-mock",
        "synthetic_only": True,
        "record": {
            "number": ticket.incident_id,
            "short_description": ticket.title,
            "priority": ticket.priority,
            "assignment_group": ticket.team,
            "cmdb_ci": ticket.affected_ci,
            "business_service": ticket.business_service,
            "state": "New",
            "requested_outcome": ticket.requested_outcome,
        },
    }


@app.post("/api/incidents")
async def create_incident(request: IncidentStartRequest | None = None) -> dict[str, str]:
    request = request or IncidentStartRequest()
    try:
        ticket = request.ticket or get_incident_for_scenario(request.scenario_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Scenario not found") from None
    session = await manager.start_run(ticket, scenario_id=ticket.scenario_id)
    return {"run_id": session.run_id, "status": session.status}


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    session = manager.get_session(run_id)
    if not session:
        raise HTTPException(status_code=404, detail="Run not found")
    return session.snapshot()


@app.post("/api/runs/{run_id}/approve")
def approve_run(run_id: str, request: ApprovalRequest | None = None):
    try:
        approval = request or ApprovalRequest()
        return manager.approve(
            run_id,
            {
                **approval.model_dump(),
                "recorded_at": utc_now().isoformat(),
            },
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found") from None


@app.post("/api/runs/{run_id}/reject")
def reject_run(run_id: str):
    try:
        return manager.reject(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found") from None


@app.post("/api/runs/{run_id}/close")
def close_run(run_id: str):
    try:
        return manager.close_incident(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found") from None


@app.post("/api/runs/{run_id}/observe")
def observe_run(run_id: str):
    try:
        return manager.observe_incident(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found") from None


@app.get("/api/replay/{scenario_id}")
def replay_scenario(scenario_id: str):
    try:
        path = get_replay_path(scenario_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Scenario not found") from None
    events = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return {"events": events}


@app.get("/api/runs/{run_id}/audit-packet")
def audit_packet(run_id: str):
    session = manager.get_session(run_id)
    if not session:
        raise HTTPException(status_code=404, detail="Run not found")

    snapshot = session.snapshot().model_dump(mode="json")
    normalized = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
    audit_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return {
        "run_id": run_id,
        "generated_at": utc_now().isoformat(),
        "audit_hash": f"sha256:{audit_hash}",
        "safety": {
            "synthetic_only": True,
            "mock_only": True,
            "approval_required": True,
            "real_execution_disabled": True,
        },
        "packet": snapshot,
    }


@app.get("/api/policy/demo-block")
def policy_demo_block():
    unsafe_plan = RemediationPlan(
        summary="Unsafe protected-resource cleanup demo.",
        target_resources=["C:\\Windows\\System32"],
        action_preview="Remove-Item 'C:\\Windows\\System32\\*.log' -Recurse -Force",
        estimated_effect="Unknown effect.",
        safeguards=[],
        approval_required=False,
        uses_dry_run=False,
        mock_only=False,
        validation_steps=[],
    )
    return {"checks": policy_check(unsafe_plan, enforce_approval=True)}


@app.websocket("/ws/runs/{run_id}")
async def run_websocket(websocket: WebSocket, run_id: str):
    await websocket.accept()
    session = manager.get_session(run_id)
    if not session:
        await websocket.send_json({"type": "error", "message": "Run not found"})
        await websocket.close(code=1008)
        return

    queue = session.stream.subscribe()
    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event.model_dump(mode="json"))
    except WebSocketDisconnect:
        session.stream.unsubscribe(queue)
