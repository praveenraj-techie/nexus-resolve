from __future__ import annotations

from typing import Any

from .models import RcaSummary


def fallback_rca(before: dict[str, Any], after: dict[str, Any]) -> RcaSummary:
    before_drive = before["drives"]["C:"]
    after_drive = after["drives"]["C:"]
    reclaimed = after_drive["free_gb"] - before_drive["free_gb"]
    return RcaSummary(
        root_cause="Application log retention exceeded expected synthetic volume.",
        actions_taken=[
            "Retrieved SOP-WIN-DISK-001.",
            "Excluded unsafe historical precedent that deleted active logs.",
            "Generated age-filtered PowerShell with a WhatIf guard.",
            "Captured human approval before mock remediation.",
            "Validated disk free space after mock cleanup.",
        ],
        validation=(
            f"C: improved from {before_drive['used_percent']}% used to "
            f"{after_drive['used_percent']}% used, with {after_drive['free_gb']} GB free."
        ),
        business_impact="Internal Claims Portal remained healthy during the synthetic flow.",
        follow_up=[
            "Tune application log rotation.",
            "Add automated pre-checks for old log accumulation.",
            "Route insufficient cleanup outcomes to infrastructure expansion.",
        ],
        metrics={
            "reclaimed_gb": reclaimed,
            "before_free_gb": before_drive["free_gb"],
            "after_free_gb": after_drive["free_gb"],
            "mttr_minutes": 8,
            "manual_steps_avoided": 6,
            "audit_completeness_percent": 100,
        },
    )

