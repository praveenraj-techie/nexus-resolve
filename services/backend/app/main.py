from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .models import IncidentTicket
from .orchestrator import RunManager
from .policy import policy_check
from .models import RemediationPlan
from .tools import DATA_ROOT, get_default_incident


app = FastAPI(title="NEXUS-RESOLVE API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = RunManager()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "nexus-resolve"}


@app.post("/api/incidents")
async def create_incident(ticket: IncidentTicket | None = None) -> dict[str, str]:
    session = await manager.start_run(ticket or get_default_incident())
    return {"run_id": session.run_id, "status": session.status}


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    session = manager.get_session(run_id)
    if not session:
        raise HTTPException(status_code=404, detail="Run not found")
    return session.snapshot()


@app.post("/api/runs/{run_id}/approve")
def approve_run(run_id: str):
    try:
        return manager.approve(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found") from None


@app.post("/api/runs/{run_id}/reject")
def reject_run(run_id: str):
    try:
        return manager.reject(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found") from None


@app.get("/api/replay/disk-space")
def replay_disk_space():
    path = Path(DATA_ROOT) / "replay/disk-space-run.events.jsonl"
    events = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return {"events": events}


@app.get("/api/policy/demo-block")
def policy_demo_block():
    unsafe_plan = RemediationPlan(
        summary="Unsafe protected-path cleanup demo.",
        target_paths=["C:\\Windows\\System32"],
        estimated_reclaim_gb=10,
        age_filter_days=0,
        powershell="Remove-Item 'C:\\Windows\\System32\\*.log' -Recurse -Force",
        approval_required=False,
        uses_whatif=False,
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

