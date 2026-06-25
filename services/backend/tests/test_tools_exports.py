from app.models import RemediationPlan
from app.tools import get_initial_state, mock_execute, policy_check


def test_tools_module_exposes_policy_check_and_mock_execute():
    plan = RemediationPlan(
        summary="Safe app log cleanup.",
        target_paths=["C:\\App\\Logs"],
        estimated_reclaim_gb=24,
        age_filter_days=7,
        powershell=(
            "Get-ChildItem 'C:\\App\\Logs' -File -Recurse | "
            "Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) } | "
            "Remove-Item -WhatIf"
        ),
        approval_required=True,
        approval_granted=True,
        uses_whatif=True,
        mock_only=True,
        validation_steps=["Check C: free space."],
    )

    checks = policy_check(plan, enforce_approval=True)
    after = mock_execute(plan, get_initial_state())

    assert all(check.status == "pass" for check in checks)
    assert after["drives"]["C:"]["free_gb"] == 44

