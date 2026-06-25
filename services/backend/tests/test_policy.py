from app.models import RemediationPlan
from app.policy import policy_check


def test_unsafe_script_is_blocked_without_age_filter_and_whatif():
    plan = RemediationPlan(
        summary="Unsafe all-log deletion.",
        target_paths=["C:\\App\\Logs"],
        estimated_reclaim_gb=20,
        age_filter_days=0,
        powershell="Get-ChildItem 'C:\\App\\Logs' -Recurse | Remove-Item",
        approval_required=True,
        uses_whatif=False,
        mock_only=False,
        validation_steps=[],
    )

    checks = policy_check(plan, enforce_approval=True)
    blocked = {check.name for check in checks if check.status == "blocked"}

    assert "Age filter" in blocked
    assert "Dry-run guard" in blocked
    assert "Validation steps" in blocked
    assert "Mock-only execution" in blocked


def test_protected_path_is_blocked():
    plan = RemediationPlan(
        summary="Unsafe protected path.",
        target_paths=["C:\\Windows\\System32"],
        estimated_reclaim_gb=5,
        age_filter_days=7,
        powershell="Remove-Item 'C:\\Windows\\System32\\*.log' -WhatIf",
        approval_required=True,
        approval_granted=True,
        uses_whatif=True,
        mock_only=True,
        validation_steps=["Check free space."],
    )

    checks = policy_check(plan, enforce_approval=True)

    assert any(
        check.name == "Protected paths" and check.status == "blocked"
        for check in checks
    )

