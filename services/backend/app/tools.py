from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import EvidenceItem, IncidentTicket, PolicyCheck, RemediationPlan


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_ROOT = PROJECT_ROOT / "data"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def get_default_incident() -> IncidentTicket:
    return IncidentTicket.model_validate(
        read_json(DATA_ROOT / "synthetic/incidents/disk-space-p4.json")
    )


def get_initial_state() -> dict[str, Any]:
    return read_json(DATA_ROOT / "synthetic/mock-state/windows-fleet.initial.json")


def get_expected_after_state() -> dict[str, Any]:
    return read_json(DATA_ROOT / "synthetic/mock-state/windows-fleet.after-disk.json")


def retrieve_sop(ticket: IncidentTicket) -> EvidenceItem:
    sop_path = DATA_ROOT / "synthetic/sops/SOP-WIN-DISK-001.md"
    sop_text = sop_path.read_text(encoding="utf-8")
    return EvidenceItem(
        id="SOP-WIN-DISK-001",
        type="sop",
        title="Windows Application Log Disk Remediation SOP",
        summary=(
            "Delete only application logs older than 7 days, avoid protected "
            "paths, require approval, and validate free space."
        ),
        source=str(sop_path.relative_to(PROJECT_ROOT)),
        metadata={
            "ticket": ticket.incident_id,
            "content": sop_text,
            "protected_paths": [
                "C:\\Windows",
                "C:\\Windows\\System32",
                "C:\\Program Files",
                "C:\\Users",
            ],
        },
    )


def retrieve_similar_tickets(ticket: IncidentTicket) -> list[EvidenceItem]:
    ticket_path = DATA_ROOT / "synthetic/tickets/historical-ticket-pack.jsonl"
    rows = read_jsonl(ticket_path)
    evidence: list[EvidenceItem] = []
    for row in rows:
        evidence.append(
            EvidenceItem(
                id=row["ticket_id"],
                type="history",
                title=row["summary"],
                summary=row["notes"],
                source=str(ticket_path.relative_to(PROJECT_ROOT)),
                metadata={
                    **row,
                    "matched_ci": row.get("ci") == ticket.affected_ci,
                },
            )
        )
    return evidence


def estimate_reclaimable_space(state: dict[str, Any]) -> float:
    return float(
        sum(
            candidate.get("old_log_gb", 0)
            for candidate in state.get("cleanup_candidates", [])
            if candidate.get("safe_to_remove")
        )
    )


def validate_result(before: dict[str, Any], after: dict[str, Any]) -> PolicyCheck:
    before_drive = before["drives"]["C:"]
    after_drive = after["drives"]["C:"]
    total_gb = after_drive["total_gb"]
    free_percent = (after_drive["free_gb"] / total_gb) * 100
    if free_percent < 15:
        return PolicyCheck(
            name="Free-space validation",
            status="blocked",
            message="Free space remains below the 15% escalation threshold.",
            evidence={
                "before_free_gb": before_drive["free_gb"],
                "after_free_gb": after_drive["free_gb"],
                "free_percent": round(free_percent, 2),
            },
        )
    return PolicyCheck(
        name="Free-space validation",
        status="pass",
        message="Free space is above the 15% threshold after mock remediation.",
        evidence={
            "before_free_gb": before_drive["free_gb"],
            "after_free_gb": after_drive["free_gb"],
            "free_percent": round(free_percent, 2),
        },
    )


def policy_check(
    plan: RemediationPlan, *, enforce_approval: bool = False
) -> list[PolicyCheck]:
    from .policy import policy_check as run_policy_check

    return run_policy_check(plan, enforce_approval=enforce_approval)


def mock_execute(plan: RemediationPlan, state: dict[str, Any]) -> dict[str, Any]:
    from .mock_execute import mock_execute as run_mock_execute

    return run_mock_execute(plan, state)
